#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
os.environ['PYTHONUTF8'] = '1'
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Patch subprocess.run to replace 'python3' with sys.executable and safely handle text decoding for cross-platform compatibility
_orig_run = subprocess.run
def _patched_run(args, *args_pos, **kwargs):
    if isinstance(args, list) and args and args[0] == 'python3':
        args = [sys.executable] + args[1:]
    text_mode = kwargs.pop('text', None) or kwargs.pop('universal_newlines', None) or ('encoding' in kwargs)
    kwargs.pop('encoding', None)
    if text_mode:
        res = _orig_run(args, *args_pos, **kwargs)
        if isinstance(res.stdout, bytes):
            res.stdout = res.stdout.decode('utf-8', errors='replace')
        if isinstance(res.stderr, bytes):
            res.stderr = res.stderr.decode('utf-8', errors='replace')
        return res
    return _orig_run(args, *args_pos, **kwargs)
subprocess.run = _patched_run

SKILL_ROOT = Path(__file__).parent.parent  # msc/lib/msc_mvp_router.py -> msc/
if str(SKILL_ROOT / 'lib') not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT / 'lib'))

from msc_tool.router import route_query
from msc_tool.dispatcher import dispatch
from msc_tool.renderer import render_markdown
from msc_tool.schema import ErrorInfo, MscSchema, QueryParams
from inline_menu_payload import _build_inline_menu_payload

SCRIPTS_DIR = SKILL_ROOT / 'scripts'
SLASH_CMD_RE = re.compile(r"^(?:@\w+\s+)?/(tbmt|kh|msc|fl|exp|msc_status|menu)(?:@\w+)?\b\s*(.*)$", re.IGNORECASE)

TAB_MAP = {
    'hanghoa': 'hang_hoa',
    'thietbi': 'thiet_bi_vat_tu_y_te',
    'generic': 'thuoc_generic',
    'bietduoc': 'thuoc_biet_duoc_goc',
    'thuocduoclieu': 'thuoc_duoc_lieu',
    'duoclieu': 'duoc_lieu',
    'vithuoc': 'vi_thuoc_co_truyen',
}

# OpenClaw paths removed - MSC skill standalone


_DOTENV_CACHE: dict[str, str] | None = None


def _load_dotenv() -> dict[str, str]:
    global _DOTENV_CACHE
    if _DOTENV_CACHE is not None:
        return _DOTENV_CACHE
    # Try multiple .env locations
    env_paths = [
        SKILL_ROOT / '.env',
        SKILL_ROOT.parent / '.env',
        Path.home() / '.hermes' / '.env',
    ]
    out: dict[str, str] = {}
    for env_path in env_paths:
        if env_path.exists():
            for raw in env_path.read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
            break
    _DOTENV_CACHE = out
    return out


def _get_env(*names: str, default: str = '') -> str:
    dot = _load_dotenv()
    for n in names:
        val = os.environ.get(n)
        if val:
            return val
        val2 = dot.get(n)
        if val2:
            return val2
    return default


def now_iso() -> str:
    return datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds')


def _run_json(cmd: list[str]) -> dict:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or 'script_error')
    return json.loads(cp.stdout)


def _msc_token() -> str:
    return _get_env('BOT2_MSC_TOKEN', 'MSC_TOKEN', 'MUASAMCONG_TOKEN', 'MSC_SESSION_TOKEN', default='')


def _msc_cookie() -> str:
    return _get_env('BOT2_MSC_COOKIE', 'MSC_COOKIE', 'MUASAMCONG_COOKIE', default='')


def _extract_file_from_obj(obj) -> tuple[str, str]:
    if isinstance(obj, dict):
        doc = obj.get('document')
        if isinstance(doc, dict) and doc.get('file_id'):
            return str(doc.get('file_id')), str(doc.get('file_name') or '')
        audio = obj.get('audio')
        if isinstance(audio, dict) and audio.get('file_id'):
            return str(audio.get('file_id')), str(audio.get('file_name') or '')
        video = obj.get('video')
        if isinstance(video, dict) and video.get('file_id'):
            return str(video.get('file_id')), str(video.get('file_name') or '')
        voice = obj.get('voice')
        if isinstance(voice, dict) and voice.get('file_id'):
            return str(voice.get('file_id')), 'voice.ogg'
        photo = obj.get('photo')
        if isinstance(photo, list) and photo:
            best = photo[-1]
            if isinstance(best, dict) and best.get('file_id'):
                return str(best.get('file_id')), 'photo.jpg'
        for v in obj.values():
            fid, fn = _extract_file_from_obj(v)
            if fid:
                return fid, fn
    elif isinstance(obj, list):
        for it in obj:
            fid, fn = _extract_file_from_obj(it)
            if fid:
                return fid, fn
    return '', ''


def _hydrate_reply_payload_env() -> None:
    if os.environ.get('REPLY_PAYLOAD_JSON') or os.environ.get('BOT2_REPLY_PAYLOAD_JSON'):
        return
    candidates = [
        'OPENCLAW_EVENT_JSON',
        'OPENCLAW_MESSAGE_JSON',
        'OPENCLAW_INBOUND_JSON',
        'MESSAGE_JSON',
        'INBOUND_MESSAGE_JSON',
        'TELEGRAM_MESSAGE_JSON',
    ]
    for k in candidates:
        raw = os.environ.get(k, '')
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        for rk in ['reply_to_message', 'replyToMessage', 'reply_to', 'repliedMessage']:
            part = obj.get(rk)
            if isinstance(part, dict):
                os.environ['REPLY_PAYLOAD_JSON'] = json.dumps({'reply_to_message': part}, ensure_ascii=False)
                # backward compatibility
                os.environ.setdefault('BOT2_REPLY_PAYLOAD_JSON', os.environ['REPLY_PAYLOAD_JSON'])
                fid, fn = _extract_file_from_obj(part)
                if fid and (not os.environ.get('REPLY_FILE_ID')):
                    os.environ['REPLY_FILE_ID'] = fid
                if fn and (not os.environ.get('REPLY_FILE_NAME')):
                    os.environ['REPLY_FILE_NAME'] = fn
                if fid and (not os.environ.get('BOT2_REPLY_FILE_ID')):
                    os.environ['BOT2_REPLY_FILE_ID'] = fid
                if fn and (not os.environ.get('BOT2_REPLY_FILE_NAME')):
                    os.environ['BOT2_REPLY_FILE_NAME'] = fn
                return


def _extract_reply_file_from_context() -> tuple[str, str]:
    candidates = [
        'REPLY_PAYLOAD_JSON',
        'BOT2_REPLY_PAYLOAD_JSON',
        'OPENCLAW_EVENT_JSON',
        'OPENCLAW_MESSAGE_JSON',
        'OPENCLAW_INBOUND_JSON',
        'MESSAGE_JSON',
        'INBOUND_MESSAGE_JSON',
        'TELEGRAM_MESSAGE_JSON',
    ]
    for k in candidates:
        raw = os.environ.get(k, '')
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        for key in ['reply_to_message', 'replyToMessage', 'reply_to', 'repliedMessage', 'message']:
            part = obj.get(key) if isinstance(obj, dict) else None
            if part is None:
                continue
            fid, fn = _extract_file_from_obj(part)
            if fid:
                return fid, fn
        fid, fn = _extract_file_from_obj(obj)
        if fid:
            return fid, fn

    for k, v in os.environ.items():
        ku = k.upper()
        if 'REPLY' in ku and 'FILE_ID' in ku and v:
            fn = os.environ.get(k.replace('FILE_ID', 'FILE_NAME'), '')
            return v, fn
    return '', ''


def _extract_runtime_actor_context() -> tuple[str, str, str]:
    """Best-effort derive (author_id, source_thread_id, source_channel) from inbound env."""
    candidates = [
        'OPENCLAW_EVENT_JSON',
        'OPENCLAW_MESSAGE_JSON',
        'OPENCLAW_INBOUND_JSON',
        'MESSAGE_JSON',
        'INBOUND_MESSAGE_JSON',
        'TELEGRAM_MESSAGE_JSON',
    ]
    for k in candidates:
        raw = os.environ.get(k, '')
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue

        sender = str(obj.get('sender_id') or obj.get('senderId') or '').strip()
        if not sender:
            s2 = obj.get('sender')
            if isinstance(s2, dict):
                sender = str(s2.get('id') or s2.get('uid') or '').strip()
        if not sender:
            frm = obj.get('from')
            if isinstance(frm, dict):
                sender = str(frm.get('id') or '').strip()

        thread = str(obj.get('thread_id') or obj.get('threadId') or '').strip()
        if not thread:
            t2 = obj.get('thread')
            if isinstance(t2, dict):
                thread = str(t2.get('id') or '').strip()
        if not thread:
            chat = obj.get('chat')
            if isinstance(chat, dict):
                thread = str(chat.get('id') or '').strip()
        if not thread:
            msg = obj.get('message')
            if isinstance(msg, dict):
                ch = msg.get('chat')
                if isinstance(ch, dict):
                    thread = str(ch.get('id') or '').strip()
        if not thread:
            cq = obj.get('callback_query') or obj.get('callbackQuery')
            if isinstance(cq, dict):
                m2 = cq.get('message')
                if isinstance(m2, dict):
                    ch2 = m2.get('chat')
                    if isinstance(ch2, dict):
                        thread = str(ch2.get('id') or '').strip()
        if not thread:
            msg = obj.get('message')
            if isinstance(msg, dict):
                ch = msg.get('chat')
                if isinstance(ch, dict):
                    thread = str(ch.get('id') or '').strip()
        if not thread:
            cq = obj.get('callback_query') or obj.get('callbackQuery')
            if isinstance(cq, dict):
                m2 = cq.get('message')
                if isinstance(m2, dict):
                    ch2 = m2.get('chat')
                    if isinstance(ch2, dict):
                        thread = str(ch2.get('id') or '').strip()

        channel = str(obj.get('channel') or '').strip().lower()
        if not channel:
            if 'TELEGRAM' in k:
                channel = 'telegram'
            elif 'ZALO' in k:
                channel = 'zalo'
            else:
                channel = 'telegram'

        if thread:
            return sender or 'default-user', thread, channel

    sender = _get_env('SB_AUTHOR_ID', 'OPENCLAW_SENDER_ID', 'SENDER_ID', default='default-user')
    thread = _get_env(
        'SB_SOURCE_THREAD_ID',
        'OPENCLAW_THREAD_ID',
        'THREAD_ID',
        'OPENCLAW_CHAT_ID',
        'CHAT_ID',
        'TARGET',
        default=''
    )
    channel = _get_env('SB_SOURCE_CHANNEL', 'OPENCLAW_CHANNEL', default='telegram')
    return sender, thread, channel


    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'reply_markup': json.dumps(reply_markup, ensure_ascii=False),
    }).encode('utf-8')

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode('utf-8', errors='ignore')
        obj = json.loads(body)
        return bool(obj.get('ok')), obj
    except Exception as e:
        return False, {'error': str(e)[:300]}


def _safe_run_json(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or '').strip()
    err = (p.stderr or '').strip()
    if p.returncode != 0:
        return {
            'status': 'error',
            'error': {
                'code': 'script_failed',
                'message': (err or out or 'script_failed')[:400],
            }
        }
    try:
        return json.loads(out) if out else {'ok': True}
    except Exception:
        return {'status': 'ok', 'result': {'raw_output': out}}


def _deterministic_hit(key: str, percent: int) -> bool:
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    h = hashlib.sha256(key.encode('utf-8')).hexdigest()
    bucket = int(h[:8], 16) % 100
    return bucket < percent


def _legacy_dispatch(text: str) -> MscSchema:
    q = route_query(text)
    token = _msc_token()
    cookie = _msc_cookie()

    if q.intent == 'lookup_pl' and q.code:
        if not token:
            return MscSchema(
                query_type='pl',
                query_params=QueryParams(code=q.code),
                source='muasamcong_hidden_api',
                script_used='msc_pl_lookup.py',
                fetched_at=now_iso(),
                total_count=0,
                records=[],
                error=ErrorInfo('login_error', 'lỗi login'),
            )
        data = _run_json(['python3', str(SCRIPTS_DIR / 'msc_pl_lookup.py'), '--pl', q.code, '--token', token] + (['--cookie', cookie] if cookie else []))
        ok = data.get('status') == 'ok'
        rows = [data.get('result', data)] if ok else []
        return MscSchema(
            query_type='pl',
            query_params=QueryParams(code=q.code),
            source='muasamcong_hidden_api',
            script_used='msc_pl_lookup.py',
            fetched_at=now_iso(),
            total_count=len(rows),
            records=rows,
            error=None if rows else ErrorInfo('not_found', 'sai số PL'),
        )

    if q.intent == 'lookup_ib' and q.code:
        cmd = ['python3', str(SCRIPTS_DIR / 'msc_ib_lookup.py'), q.code]
        if token:
            cmd += ['--token', token]
        if cookie:
            cmd += ['--cookie', cookie]
        data = _run_json(cmd)
        ok = data.get('status') == 'ok'
        rows = [data.get('result', data)] if ok else []
        return MscSchema(
            query_type='ib',
            query_params=QueryParams(code=q.code),
            source='muasamcong_hidden_api',
            script_used='msc_ib_lookup.py',
            fetched_at=now_iso(),
            total_count=len(rows),
            records=rows,
            error=None if rows else ErrorInfo('not_found', 'sai số IB'),
        )

    if q.intent == 'list_tbmt' and q.unit:
        n = q.n or 5
        data = _run_json(['python3', str(SCRIPTS_DIR / 'msc_tbmt_precise.py'), q.unit, '-n', str(n)])
        rows = data.get('rows', [])
        return MscSchema(
            query_type='tbmt',
            query_params=QueryParams(unit=q.unit, n=n),
            source='muasamcong_hidden_api',
            script_used='msc_tbmt_precise.py',
            fetched_at=now_iso(),
            total_count=data.get('total', len(rows)),
            records=rows,
            error=None if rows else ErrorInfo('not_found', 'Không có kết quả'),
        )

    if q.intent == 'list_kh' and q.unit:
        n = q.n or 5
        data = _run_json(['python3', str(SCRIPTS_DIR / 'msc_kh_precise.py'), q.unit, '-n', str(n)])
        rows = data.get('rows', [])
        return MscSchema(
            query_type='kh',
            query_params=QueryParams(unit=q.unit, n=n),
            source='muasamcong_hidden_api',
            script_used='msc_kh_precise.py',
            fetched_at=now_iso(),
            total_count=data.get('total', len(rows)),
            records=rows,
            error=None if rows else ErrorInfo('not_found', 'Không có kết quả'),
        )

    return MscSchema(
        query_type='tbmt',
        query_params=QueryParams(unit=q.unit, n=q.n),
        source='muasamcong_hidden_api',
        script_used='legacy-router',
        fetched_at=now_iso(),
        total_count=0,
        records=[],
        error=ErrorInfo('ambiguous_unit', 'Bạn muốn tra KHLCNT hay TBMT?'),
    )


def _normalize_incoming_command_text(raw_text: str) -> str:
    s = (raw_text or '').strip()
    if not s:
        return s

    # Accept multiple callback forms:
    # - "callback_data: v1|..."
    # - raw token: "v1|..."
    # - JSON object containing callback_query.data
    payload = ''

    m_cb = re.match(r'^callback_data\s*:\s*(.+)$', s, flags=re.IGNORECASE)
    if m_cb:
        payload = m_cb.group(1).strip()
    elif re.match(r'^v1\|[^|]+\|[^|]+\|.+$', s):
        payload = s
    elif s.startswith('{'):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                cq = obj.get('callback_query') or obj.get('callbackQuery') or {}
                if isinstance(cq, dict):
                    payload = (cq.get('data') or '').strip()
                if not payload:
                    payload = (obj.get('callback_data') or obj.get('callbackData') or '').strip()
        except Exception:
            payload = ''

    if payload:
        if payload.startswith('/'):
            return payload

        parts = payload.split('|')
        if len(parts) >= 4 and parts[0] == 'v1':
            module, action, arg = parts[1], parts[2], parts[3]

            # open submenu by callback
            if action == 'open':
                if module == 'menu' and arg == 'root':
                    return '/menu'
                if module == 'msc' and arg in {'main', 'watch', 'lookup', 'export'}:
                    return f'/menu msc_{arg}' if arg != 'main' else '/menu msc'
                if module == 'doc' and arg in {'main', 'ingest', 'nb', 'summary'}:
                    return f'/menu doc_{arg}' if arg != 'main' else '/menu doc'
                if module == 'research' and arg == 'main':
                    return '/menu research'
                if module == 'skills' and arg == 'main':
                    return '/menu skills'
                if module == 'todo' and arg == 'main':
                    return '/menu todo'
                if module == 'help' and arg == 'main':
                    return '/menu help'

            # direct run commands by callback
            if action == 'run':
                if module == 'msc' and arg == 'status':
                    return '/msc_status'
                if module == 'msc' and arg == 'fl_list':
                    return '/fl list'
                if module == 'doc' and arg == 'nb_ls':
                    return '/nb ls'
                if module == 'research' and arg in {'tpl_quick', 'tpl_standard', 'tpl_publication', 'tpl_oneliner'}:
                    return f'/menu research_{arg}'
                if module == 'skills' and arg == 'lint':
                    return '/skills lint'
                if module == 'skills' and arg == 'simulate_sample':
                    return '/skills simulate --skill-id vn-fx-rate --tool web_fetch --channel zalo --remote 0 --owner 0'
                if module == 'skills' and arg == 'help':
                    return '/skills help'
                if module == 'todo' and arg == 'todo':
                    return '/todo'
                if module == 'todo' and arg == 'task':
                    return '/task'
                if module == 'todo' and arg == 'done':
                    return '/done'
                if module == 'todo' and arg == 'save':
                    return '/save'
                if module == 'todo' and arg == 'note':
                    return '/note'
                if module == 'doc' and arg in {'ingest_help', 'ingest_new_nb_help', 'nb_use_help', 'nb_alias_help', 'sum_help', 'detail_help'}:
                    return f'/menu doc_{arg}'

            # ask-flow placeholders
            if action == 'ask' and module == 'flow':
                if arg == 'exp_ib':
                    return '/menu ask_exp_ib'
                if arg == 'exp_pl':
                    return '/menu ask_exp_pl'
                if arg == 'fl_add':
                    return '/menu ask_fl_add'
                if arg == 'tbmt':
                    return '/menu ask_tbmt'
                if arg == 'kh':
                    return '/menu ask_kh'

    # Normalize reply-keyboard labels to commands
    label_map = {
        '1️⃣ mua sắm công': '/menu 1',
        '2️⃣ tài liệu ai': '/menu 2',
        '3️⃣ nghiên cứu': '/menu 3',
        '4️⃣ skills policy': '/menu 4',
        '5️⃣ trợ giúp': '/menu 5',
        '✅ todoist': '/menu todo',
        '📝 tóm tắt': '/menu doc 3',
        '🔍 skills lint': '/skills lint',
        '🧪 simulate mẫu': '/menu skills 2',
    }
    k = s.strip().lower()
    if k in label_map:
        return label_map[k]

    # Decorated reply-keyboard labels (slash + icon/text) -> canonical command
    raw = s.strip()
    decorated_prefixes = [
        ('/menu 1 ', '/menu 1'),
        ('/menu 2 ', '/menu 2'),
        ('/menu 3 ', '/menu 3'),
        ('/menu 4 ', '/menu 4'),
        ('/menu 5 ', '/menu 5'),
        ('/menu todo ', '/menu todo'),
        ('/menu doc 3 ', '/menu doc 3'),
    ]
    for pref, cmd in decorated_prefixes:
        if raw.lower().startswith(pref.lower()):
            return cmd

    return s


def _run_direct_command(raw_text: str) -> dict | None:
    _hydrate_reply_payload_env()
    normalized = _normalize_incoming_command_text(raw_text)
    m = SLASH_CMD_RE.match(normalized.strip())
    if not m:
        return None

    cmd = m.group(1).lower()
    args = (m.group(2) or '').strip()
    token = _msc_token()
    cookie = _msc_cookie()

    if cmd == 'menu':
        try:
            mparts = shlex.split(args)
        except Exception:
            mparts = (args or '').split()

        # Numbered shortcuts
        # Root: /menu 1..5
        if len(mparts) >= 1 and re.fullmatch(r'\d+', mparts[0] or ''):
            root_pick = int(mparts[0])
            level = {
                1: 'msc',
                2: 'doc',
                3: 'research',
                4: 'skills',
                5: 'help',
            }.get(root_pick, 'root')
        # Submenu picks: /menu <group> <n>
        elif len(mparts) >= 2 and re.fullmatch(r'\d+', mparts[1] or ''):
            group = (mparts[0] or '').strip().lower()
            pick = int(mparts[1])

            if group in {'msc', 'msc_main'}:
                if pick == 1:
                    level = 'msc_watch'
                elif pick == 2:
                    level = 'msc_lookup'
                elif pick == 3:
                    level = 'msc_export'
                elif pick == 4:
                    return _run_direct_command('/msc_status')
                else:
                    level = 'msc'
            elif group in {'doc', 'doc_main'}:
                if pick == 1:
                    level = 'doc_ingest'
                elif pick == 2:
                    level = 'doc_nb'
                elif pick == 3:
                    level = 'doc_summary'
                else:
                    level = 'doc'
            elif group in {'research', 'research_main'}:
                if pick == 1:
                    level = 'research_tpl_quick'
                elif pick == 2:
                    level = 'research_tpl_standard'
                elif pick == 3:
                    level = 'research_tpl_publication'
                elif pick == 4:
                    level = 'research_tpl_oneliner'
                else:
                    level = 'research'
            elif group in {'skills', 'skills_main'}:
                if pick == 1:
                    return _run_direct_command('/skills lint')
                if pick == 2:
                    return _run_direct_command('/skills simulate --skill-id vn-fx-rate --tool web_fetch --channel zalo --remote 0 --owner 0')
                if pick == 3:
                    return _run_direct_command('/skills help')
                level = 'skills'
            elif group in {'todo', 'todo_main'}:
                if pick == 1:
                    return _run_direct_command('/todo')
                if pick == 2:
                    return _run_direct_command('/task')
                if pick == 3:
                    return _run_direct_command('/done')
                if pick == 4:
                    return _run_direct_command('/save')
                if pick == 5:
                    return _run_direct_command('/note')
                level = 'todo'
            else:
                level = (mparts[0] or 'root').strip().lower()
        else:
            level = (args or 'root').strip().lower()

        # help/ask pages (text-only guidance for parameter input)
        if level in {'help'}:
            return {
                'status': 'ok',
                'command': 'menu',
                'result': {
                    'text': '❓ Trợ giúp nhanh\n- MSC: /tbmt /kh /fl /exp /msc_status\n- Todoist: /todo /task /done /save /note\n- Tóm tắt: /sum /detail\n- Tài liệu AI: /ingest /nb\n- Nghiên cứu: chọn mẫu prompt ở menu.',
                    'buttons': [[{'text': '⬅️ Quay lại', 'callback_data': 'v1|menu|open|root'}]],
                    'meta': {'menu_level': 'help'},
                }
            }

        if level in {'research_tpl_quick'}:
            txt = '⚡ QUICK\nTopic: ...\nAudience: ...\nLanguage: vi\nMode: quick\nOutput: brief'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Nghiên cứu', 'callback_data': 'v1|research|open|main'}]], 'meta': {'menu_level': 'research_tpl_quick'}}}

        if level in {'research_tpl_standard'}:
            txt = '🧩 STANDARD\nTopic: ...\nAudience: ...\nLanguage: vi\nMode: standard\nOutput: memo'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Nghiên cứu', 'callback_data': 'v1|research|open|main'}]], 'meta': {'menu_level': 'research_tpl_standard'}}}

        if level in {'research_tpl_publication'}:
            txt = '🏛️ PUBLICATION\nTopic: ...\nAudience: ...\nLanguage: vi\nMode: publication\nOutput: report'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Nghiên cứu', 'callback_data': 'v1|research|open|main'}]], 'meta': {'menu_level': 'research_tpl_publication'}}}

        if level in {'research_tpl_oneliner'}:
            txt = '📎 Mẫu 1 dòng\nNghiên cứu sâu chủ đề: <topic>; audience: <audience>; language: vi; mode: standard; output: memo.'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Nghiên cứu', 'callback_data': 'v1|research|open|main'}]], 'meta': {'menu_level': 'research_tpl_oneliner'}}}

        if level in {'doc_ingest_help'}:
            txt = '📎 Ingest\n- Reply vào file rồi gõ: /ingest\n- Hoặc: /ingest --file <path> --nb <id|alias> --title "..."'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Tài liệu AI', 'callback_data': 'v1|doc|open|main'}]], 'meta': {'menu_level': 'doc_ingest_help'}}}

        if level in {'doc_ingest_new_nb_help'}:
            txt = '📎 Ingest + tạo notebook mới\n/ingest --new-nb "Tên notebook"\n(hoặc reply file rồi /ingest --new-nb)'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Tài liệu AI', 'callback_data': 'v1|doc|open|main'}]], 'meta': {'menu_level': 'doc_ingest_new_nb_help'}}}

        if level in {'doc_nb_use_help'}:
            txt = '📚 Chọn notebook mặc định\n/nb use <alias|notebook_id>'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại NotebookLM', 'callback_data': 'v1|doc|open|nb'}]], 'meta': {'menu_level': 'doc_nb_use_help'}}}

        if level in {'doc_nb_alias_help'}:
            txt = '📚 Quản lý alias\n/nb add <alias> <notebook_id>\n/nb rm <alias>\n/nb ls'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại NotebookLM', 'callback_data': 'v1|doc|open|nb'}]], 'meta': {'menu_level': 'doc_nb_alias_help'}}}

        if level in {'doc_summary'}:
            txt = '📝 Tóm tắt nội dung\n1) ✍️ Tóm tắt nhanh (/sum)\n2) 📚 Tóm tắt chi tiết (/detail)\n\nGõ nhanh: /menu doc 3'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '✍️ Tóm tắt nhanh', 'callback_data': 'v1|doc|run|sum_help'}, {'text': '📚 Tóm tắt chi tiết', 'callback_data': 'v1|doc|run|detail_help'}], [{'text': '⬅️ Quay lại Tài liệu AI', 'callback_data': 'v1|doc|open|main'}]], 'meta': {'menu_level': 'doc_summary'}}}

        if level in {'doc_sum_help'}:
            txt = '✍️ Tóm tắt nhanh\nDùng: /sum <link|text>'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Summary', 'callback_data': 'v1|doc|open|summary'}]], 'meta': {'menu_level': 'doc_sum_help'}}}

        if level in {'doc_detail_help'}:
            txt = '📚 Tóm tắt chi tiết\nDùng: /detail <link|text>'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Summary', 'callback_data': 'v1|doc|open|summary'}]], 'meta': {'menu_level': 'doc_detail_help'}}}

        if level in {'ask_exp_ib'}:
            txt = '🧾 Nhập mã IB theo cú pháp:\n/exp IBxxxxxxxx'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Export', 'callback_data': 'v1|msc|open|export'}]], 'meta': {'menu_level': 'ask_exp_ib'}}}

        if level in {'ask_exp_pl'}:
            txt = '🧾 Nhập mã PL theo cú pháp:\n/exp PLxxxxxxxx'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Export', 'callback_data': 'v1|msc|open|export'}]], 'meta': {'menu_level': 'ask_exp_pl'}}}

        if level in {'ask_fl_add'}:
            txt = '📋 Follow đơn vị:\n/fl <tên đơn vị|vn...>'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Watchlist', 'callback_data': 'v1|msc|open|watch'}]], 'meta': {'menu_level': 'ask_fl_add'}}}

        if level in {'ask_tbmt'}:
            txt = '🔎 Tra cứu TBMT:\n/tbmt <số lượng> <tên đơn vị|vn...|IB...>'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Tra cứu', 'callback_data': 'v1|msc|open|lookup'}]], 'meta': {'menu_level': 'ask_tbmt'}}}

        if level in {'ask_kh'}:
            txt = '🔎 Tra cứu KHLCNT:\n/kh <số lượng> <tên đơn vị|vn...|PL...>'
            return {'status': 'ok', 'command': 'menu', 'result': {'text': txt, 'buttons': [[{'text': '⬅️ Quay lại Tra cứu', 'callback_data': 'v1|msc|open|lookup'}]], 'meta': {'menu_level': 'ask_kh'}}}

        level_map = {
            'root': 'root',
            'main': 'root',
            'msc': 'msc_main',
            'msc_main': 'msc_main',
            'msc_watch': 'msc_watch',
            'msc_lookup': 'msc_lookup',
            'msc_export': 'msc_export',
            'doc': 'doc_main',
            'doc_main': 'doc_main',
            'doc_ingest': 'doc_ingest',
            'doc_nb': 'doc_nb',
            'doc_summary': 'doc_summary',
            'research': 'research_main',
            'research_main': 'research_main',
            'skills': 'skills_main',
            'skills_main': 'skills_main',
            'todo': 'todo_main',
            'todo_main': 'todo_main',
        }
        menu_payload = _build_inline_menu_payload(level_map.get(level, 'root'))
        return {
            'status': 'ok',
            'command': 'menu',
            'result': {
                'text': menu_payload.get('text', ''),
                'buttons': menu_payload.get('buttons', []),
                'meta': menu_payload.get('meta', {}),
            }
        }

    if cmd in ('skills', 'skill'):
        try:
            parts = shlex.split(args)
        except Exception:
            parts = args.split()

        if not parts:
            parts = ['help']

        sub = (parts[0] or 'help').lower()

        if sub in {'help', 'h', '?'}:
            return {
                'status': 'ok',
                'command': 'skills',
                'result': {
                    'usage': [
                        '/skill list',
                        '/skills list',
                        '/skills lint',
                        '/skills lint --format table',
                        '/skills simulate --skill-id <id> --tool <tool> [--channel telegram|zalo] [--remote 0|1] [--owner 0|1]',
                        '/skills precheck',
                        '/skills precheck notify',
                        '/skills dashboard',
                        '/skills dashboard today',
                        '/skills dashboard rebuild',
                        '/skills cite --text "..." [--min-coverage 0.8] [--hard]',
                    ]
                }
            }

        if sub == 'list':
            scope = (parts[1] if len(parts) > 1 else 'bot2').strip().lower()
            if scope in {'learning', 'learn', 'claude-learning', 'research'}:
                list_dir = SKILLS_DIR_LEARNING
                scope_label = 'learning-claude'
            elif scope in {'bot2', 'default', 'catalog', 'skills'}:
                list_dir = SKILLS_DIR_BOT2
                scope_label = 'bot2'
            else:
                return {
                    'status': 'error',
                    'command': 'skills',
                    'sub_action': 'list',
                    'error': {
                        'code': 'invalid_args',
                        'message': 'Usage: /skill list [learning]'
                    }
                }

            p = subprocess.run([
                'python3', str(SKILLS_LIST_SCRIPT),
                '--dir', str(list_dir),
            ], capture_output=True, text=True)
            out = (p.stdout or '').strip()
            err = (p.stderr or '').strip()
            try:
                payload = json.loads(out) if out else {'ok': False, 'error': 'empty_output'}
            except Exception:
                payload = {'ok': False, 'error': 'list_invalid_json', 'raw': out[:400], 'stderr': err[:400]}

            # Add compact text preview for chat UX
            if payload.get('ok') and isinstance(payload.get('items'), list):
                lines = [f"📚 Skills ({scope_label}) — {payload.get('count', 0)} items:"]
                for i, it in enumerate(payload['items'], 1):
                    sid = it.get('id', '')
                    sname = it.get('name', '')
                    ver = it.get('version', '')
                    risk = it.get('risk_level', '')
                    lines.append(f"{i}) {sid} — {sname} (v{ver}, risk:{risk})")
                payload['preview_text'] = "\n".join(lines)
                payload['scope'] = scope_label
                payload['dir'] = str(list_dir)

            return {
                'status': ('ok' if payload.get('ok') else 'error'),
                'command': 'skills',
                'sub_action': 'list',
                'result': payload,
                'meta': {'exit_code': p.returncode, 'scope': scope_label}
            }

        if sub == 'lint':
            fmt = 'json'
            if '--format' in parts:
                try:
                    idx = parts.index('--format')
                    fmt = (parts[idx + 1] if idx + 1 < len(parts) else 'json').strip().lower()
                except Exception:
                    fmt = 'json'
            if fmt not in ('json', 'table'):
                fmt = 'json'

            cmdline = [
                'python3', str(SKILLS_LINT_SCRIPT),
                '--dir', str(SKILLS_DIR_LEARNING),
                '--format', fmt,
            ]
            p = subprocess.run(cmdline, capture_output=True, text=True)
            out = (p.stdout or '').strip()
            err = (p.stderr or '').strip()

            if fmt == 'json':
                try:
                    payload = json.loads(out) if out else {}
                except Exception:
                    payload = {'ok': False, 'error': 'lint_invalid_json', 'raw': out[:400]}
                status = 'ok' if payload.get('ok') else 'error'
                if p.returncode != 0 and payload.get('ok') is True:
                    status = 'error'
                return {
                    'status': status,
                    'command': 'skills',
                    'sub_action': 'lint',
                    'result': payload,
                    'meta': {'exit_code': p.returncode}
                }

            # table mode
            return {
                'status': ('ok' if p.returncode == 0 else 'error'),
                'command': 'skills',
                'sub_action': 'lint',
                'result': {
                    'output': out,
                    'stderr': err,
                    'format': 'table',
                },
                'meta': {'exit_code': p.returncode}
            }


        if sub in {'cite', 'citation', 'citation-gate'}:
            def _flag(name: str, default: str = '') -> str:
                if name in parts:
                    i = parts.index(name)
                    if i + 1 < len(parts):
                        return parts[i + 1]
                return default

            text = _flag('--text')
            text_file = _flag('--text-file')
            min_cov = _flag('--min-coverage', '0.8')
            hard = ('--hard' in parts)

            if not text and not text_file:
                return {
                    'status': 'error',
                    'command': 'skills',
                    'sub_action': 'cite',
                    'error': {
                        'code': 'invalid_args',
                        'message': 'Usage: /skills cite --text "..." [--min-coverage 0.8] [--hard]'
                    }
                }

            cmdline = ['python3', str(CITATION_GATE_SCRIPT)]
            if text:
                cmdline += ['--text', text]
            if text_file:
                cmdline += ['--text-file', text_file]
            cmdline += ['--min-coverage', min_cov]
            if hard:
                cmdline += ['--hard']

            p = subprocess.run(cmdline, capture_output=True, text=True)
            out = (p.stdout or '').strip()
            err = (p.stderr or '').strip()
            try:
                payload = json.loads(out) if out else {'ok': False, 'error': 'empty_output'}
            except Exception:
                payload = {'ok': False, 'error': 'citation_invalid_json', 'raw': out[:400], 'stderr': err[:400]}

            status = 'ok' if payload.get('ok') else 'error'
            if payload.get('ok'):
                m = payload.get('metrics') or {}
                verdict = str(payload.get('verdict') or '').lower()
                header = f"🧪 Citation Gate: {verdict.upper()} ({payload.get('reason_code','')})"
                compact = [
                    header,
                    f"- claims: {m.get('claims', 0)} | cited: {m.get('cited_claims', 0)} | uncited: {m.get('uncited_claims', 0)}",
                    f"- coverage: {m.get('coverage_rate', 0)} (min={m.get('min_coverage', min_cov)})",
                ]
                unc = payload.get('uncited_samples') or []
                if unc:
                    first = str((unc[0] or {}).get('text') or '').strip()
                    if len(first) > 160:
                        first = first[:157] + '...'
                    compact.append(f"- uncited#1: {first}")
                acts = payload.get('actions') or []
                if acts:
                    compact.append(f"- action: {acts[0]}")
                payload['preview_text'] = "\n".join(compact)

            return {
                'status': status,
                'command': 'skills',
                'sub_action': 'cite',
                'result': payload,
                'meta': {'exit_code': p.returncode}
            }


        if sub == 'dashboard':
            mode = (parts[1] if len(parts) > 1 else 'week').strip().lower()

            def _safe_read(path: Path) -> str:
                try:
                    return path.read_text(encoding='utf-8').strip()
                except Exception:
                    return ''

            def _render_weekly() -> dict:
                raw = _safe_read(SKILLS_WEEKLY_DASHBOARD)
                if not raw:
                    return {
                        'status': 'error',
                        'command': 'skills',
                        'sub_action': 'dashboard',
                        'error': {
                            'code': 'dashboard_missing',
                            'message': 'Chưa có dashboard tuần. Chạy build: python3 /Users/xitrum/.openclaw/workspace/scripts/skills/build_precheck_weekly_dashboard.py'
                        }
                    }
                lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
                compact = []
                for ln in lines:
                    if ln.startswith('# '):
                        compact.append('📊 ' + ln[2:].strip())
                    else:
                        compact.append(ln)
                    if len(compact) >= 18:
                        break
                text = '\n'.join(compact)
                if len(text) > 1800:
                    text = text[:1797] + '...'
                return {
                    'status': 'ok',
                    'command': 'skills',
                    'sub_action': 'dashboard',
                    'result': {
                        'output': text,
                        'source': str(SKILLS_WEEKLY_DASHBOARD),
                        'mode': 'weekly',
                    }
                }

            if mode in {'rebuild', 'refresh', 'r'}:
                p = subprocess.run(['python3', str(SKILLS_DASHBOARD_BUILD_SCRIPT)], capture_output=True, text=True)
                out = (p.stdout or '').strip()
                err = (p.stderr or '').strip()
                weekly = _render_weekly()
                if weekly.get('status') != 'ok':
                    return weekly
                if p.returncode != 0:
                    return {
                        'status': 'error',
                        'command': 'skills',
                        'sub_action': 'dashboard',
                        'error': {
                            'code': 'dashboard_rebuild_failed',
                            'message': (err or out or 'build_failed')[:400]
                        },
                        'meta': {'exit_code': p.returncode}
                    }
                result = weekly.get('result') or {}
                result['output'] = '🔄 Dashboard rebuilt\n' + str(result.get('output') or '')
                result['build_output'] = out[:300]
                weekly['result'] = result
                weekly['meta'] = {'exit_code': p.returncode, 'mode': 'rebuild'}
                return weekly

            if mode in {'week', 'weekly', 'w'}:
                return _render_weekly()

            if mode in {'today', 'daily', 'd'}:
                import json as _json
                from datetime import datetime as _dt
                fp = SKILLS_HISTORY_DIR / f"precheck-{_dt.now().strftime('%Y-%m-%d')}.jsonl"
                if not fp.exists():
                    return {
                        'status': 'ok',
                        'command': 'skills',
                        'sub_action': 'dashboard',
                        'result': {
                            'output': '📊 Skills dashboard (today)\nChưa có run hôm nay.',
                            'mode': 'today',
                            'source': str(fp),
                        }
                    }
                rows = []
                try:
                    for ln in fp.read_text(encoding='utf-8').splitlines():
                        ln = ln.strip()
                        if not ln:
                            continue
                        rows.append(_json.loads(ln))
                except Exception:
                    rows = []
                total = len(rows)
                ok_n = sum(1 for r in rows if r.get('ok') is True)
                fail_n = total - ok_n
                last = rows[-1] if rows else {}
                reason = str(last.get('reason') or 'N/A')
                text = (
                    f"📊 Skills dashboard (today)\n"
                    f"- Runs: {total} | OK: {ok_n} | FAIL: {fail_n}\n"
                    f"- Last reason: {reason}\n"
                    f"- Source: {fp}"
                )
                return {
                    'status': 'ok',
                    'command': 'skills',
                    'sub_action': 'dashboard',
                    'result': {
                        'output': text,
                        'mode': 'today',
                        'source': str(fp),
                    }
                }

            return {
                'status': 'error',
                'command': 'skills',
                'sub_action': 'dashboard',
                'error': {
                    'code': 'invalid_args',
                    'message': 'Usage: /skills dashboard [week|today|rebuild]'
                }
            }

        if sub == 'precheck':
            mode = (parts[1] if len(parts) > 1 else '').strip().lower()
            notify_only_on_fail = (mode == 'notify')

            p = subprocess.run([
                'bash', str(PRE_ENFORCE_CHECK_SCRIPT),
            ], capture_output=True, text=True)
            out = (p.stdout or '').strip()
            err = (p.stderr or '').strip()

            # /skills precheck notify: pass => caller may keep silent; fail => return error as usual
            if notify_only_on_fail and p.returncode == 0:
                return {
                    'status': 'ok',
                    'command': 'skills',
                    'sub_action': 'precheck',
                    'result': {
                        'silent': True,
                        'no_reply': True,
                        'output': out,
                        'stderr': err,
                        'artifacts': {
                            'lint': '/Users/xitrum/.openclaw/workspace/research/claude-learning/skill-lint-simulator-v1/examples/lint-strict.learning.with-baseline.json',
                            'sim': '/Users/xitrum/.openclaw/workspace/research/claude-learning/skill-lint-simulator-v1/examples/policy-sim.batch.sample.json'
                        }
                    },
                    'meta': {'exit_code': p.returncode, 'mode': 'notify'}
                }

            return {
                'status': ('ok' if p.returncode == 0 else 'error'),
                'command': 'skills',
                'sub_action': 'precheck',
                'result': {
                    'silent': False,
                    'no_reply': False,
                    'output': out,
                    'stderr': err,
                    'artifacts': {
                        'lint': '/Users/xitrum/.openclaw/workspace/research/claude-learning/skill-lint-simulator-v1/examples/lint-strict.learning.with-baseline.json',
                        'sim': '/Users/xitrum/.openclaw/workspace/research/claude-learning/skill-lint-simulator-v1/examples/policy-sim.batch.sample.json'
                    }
                },
                'meta': {'exit_code': p.returncode, 'mode': (mode or 'default')}
            }

        if sub == 'simulate':
            # simple parser for known flags
            def _flag(name: str, default: str = '') -> str:
                if name in parts:
                    i = parts.index(name)
                    if i + 1 < len(parts):
                        return parts[i + 1]
                return default

            skill_id = _flag('--skill-id')
            tool = _flag('--tool')
            channel = _flag('--channel', 'telegram')
            remote = _flag('--remote', '0')
            owner = _flag('--owner', '0')

            if not skill_id or not tool:
                return {
                    'status': 'error',
                    'command': 'skills',
                    'sub_action': 'simulate',
                    'error': {
                        'code': 'invalid_args',
                        'message': 'Usage: /skills simulate --skill-id <id> --tool <tool> [--channel telegram|zalo] [--remote 0|1] [--owner 0|1]'
                    }
                }

            cmdline = [
                'python3', str(POLICY_SIM_SCRIPT),
                '--skills-dir', str(SKILLS_DIR_LEARNING),
                '--skill-id', skill_id,
                '--tool', tool,
                '--channel', channel,
                '--remote', remote,
                '--owner', owner,
            ]
            p = subprocess.run(cmdline, capture_output=True, text=True)
            out = (p.stdout or '').strip()
            err = (p.stderr or '').strip()
            try:
                payload = json.loads(out) if out else {'ok': False, 'error': 'empty_output'}
            except Exception:
                payload = {'ok': False, 'error': 'simulate_invalid_json', 'raw': out[:400], 'stderr': err[:400]}

            return {
                'status': ('ok' if payload.get('ok') else 'error'),
                'command': 'skills',
                'sub_action': 'simulate',
                'result': payload,
                'meta': {'exit_code': p.returncode}
            }

        return {
            'status': 'error',
            'command': 'skills',
            'error': {'code': 'invalid_args', 'message': 'Unknown subcommand. Dùng /skills help'}
        }

    if cmd == 'msc':
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return {
                'status': 'error',
                'command': 'msc',
                'error': {'code': 'invalid_args', 'message': 'Usage: /msc <tab> <từ khóa> hoặc /msc <tab> "kw1", "kw2";"kw3"'},
            }

        tab_in = parts[0].lower()
        raw_keywords = parts[1].strip()
        tab = TAB_MAP.get(tab_in)
        if not tab:
            return {
                'status': 'error',
                'command': 'msc',
                'error': {'code': 'invalid_tab', 'message': 'tab không hợp lệ'},
                'valid_tabs': sorted(TAB_MAP.keys()),
            }

        # Parse batch keywords split by comma/semicolon, while respecting optional quotes.
        # Examples:
        #   /msc thietbi may tho, x quang; monitor
        #   /msc thietbi "máy thở", "x-quang"; "monitor"
        chunks = []
        buf = []
        quote = None
        for ch in raw_keywords:
            if ch in ('"', "'"):
                if quote is None:
                    quote = ch
                elif quote == ch:
                    quote = None
                else:
                    buf.append(ch)
                continue
            if quote is None and ch in (',', ';'):
                token = ''.join(buf).strip()
                if token:
                    chunks.append(token)
                buf = []
            else:
                buf.append(ch)
        token = ''.join(buf).strip()
        if token:
            chunks.append(token)

        # No delimiter -> keep backward-compatible single keyword behavior.
        if not chunks:
            chunks = [raw_keywords]

        # Normalize + dedup + remove surrounding quotes if any
        normalized = []
        seen_kw = set()
        for kw in chunks:
            x = (kw or '').strip().strip('"').strip("'").strip()
            if not x:
                continue
            k = x.lower()
            if k in seen_kw:
                continue
            seen_kw.add(k)
            normalized.append(x)

        if not normalized:
            return {
                'status': 'error',
                'command': 'msc',
                'error': {'code': 'invalid_args', 'message': 'Thiếu từ khóa tìm kiếm'},
            }

        # Single keyword path (backward-compatible)
        if len(normalized) == 1:
            keyword = normalized[0]
            data = _run_json([
                'python3', str(SCRIPTS_DIR / 'msc_bid_pricing_search.py'),
                '--tab', tab,
                '--keyword', keyword,
                '--page-size', '20',
            ] + (['--cookie', cookie] if cookie else []))
            return {'status': 'ok', 'command': 'msc', 'result': data}

        # Batch path
        items = []
        success = 0
        for keyword in normalized:
            data = _run_json([
                'python3', str(SCRIPTS_DIR / 'msc_bid_pricing_search.py'),
                '--tab', tab,
                '--keyword', keyword,
                '--page-size', '20',
            ] + (['--cookie', cookie] if cookie else []))

            st = (data or {}).get('status') if isinstance(data, dict) else None
            # count extracted from simplified result when available
            try:
                total = int(((data or {}).get('result') or {}).get('total', 0))
            except Exception:
                total = 0
            if st not in ('error', 'login_error'):
                success += 1
            items.append({
                'keyword': keyword,
                'status': st or 'ok',
                'total': total,
                'result': data,
            })

        return {
            'status': ('ok' if success == len(items) else ('partial' if success > 0 else 'error')),
            'command': 'msc',
            'detected_type': 'batch',
            'result': {
                'mode': 'batch',
                'tab': tab_in,
                'total_input': len(normalized),
                'success': success,
                'failed': len(normalized) - success,
                'top_limit': 20,
                'items': items,
            },
        }

    # /fl removed - now handled by msc-watchlist skill

    if cmd == 'msc_status':
        if not token:
            return {
                'status': 'error',
                'command': cmd,
                'error': {'code': 'login_error', 'message': 'lỗi login'},
                'result': {
                    'token_present': False,
                    'cookie_present': bool(cookie),
                    'login_ok': False,
                },
            }
        try:
            probe = _run_json([
                'python3', str(SCRIPTS_DIR / 'msc_hidden_api_counts.py'),
                '--token', token,
                '--noti', 'tbmt',
                '--date', 'today',
            ] + (['--cookie', cookie] if cookie else []))
            total = int(probe.get('total', 0)) if isinstance(probe, dict) else 0
            return {
                'status': 'ok',
                'command': cmd,
                'result': {
                    'token_present': True,
                    'cookie_present': bool(cookie),
                    'login_ok': True,
                    'probe': 'tbmt_today_count',
                    'total': total,
                },
            }
        except Exception as e:
            return {
                'status': 'error',
                'command': cmd,
                'error': {'code': 'login_error', 'message': 'lỗi login'},
                'result': {
                    'token_present': True,
                    'cookie_present': bool(cookie),
                    'login_ok': False,
                    'reason': str(e)[:200],
                },
            }

    if cmd == 'exp':
        raw = (args or '').strip()
        if not raw:
            return {
                'status': 'error',
                'command': cmd,
                'error': {'code': 'invalid_code', 'message': 'Usage: /exp <PL...|IB...> [PL...|IB...] [--continue-on-invalid] (hỗ trợ batch)'},
            }

        parts_raw = [p.strip() for p in re.split(r'[\s,;/]+', raw) if p.strip()]
        continue_on_invalid = False
        parts = []
        for p in parts_raw:
            pl = p.lower()
            if pl in ('--continue-on-invalid', '--coi', '--ignore-invalid'):
                continue_on_invalid = True
                continue
            parts.append(p.upper())

        seen = set()
        codes = []
        for p in parts:
            if p in seen:
                continue
            seen.add(p)
            codes.append(p)

        invalid = [c for c in codes if not (c.startswith('PL') or c.startswith('IB'))]
        valid_codes = [c for c in codes if c.startswith('PL') or c.startswith('IB')]

        if invalid and (not continue_on_invalid):
            return {
                'status': 'error',
                'command': cmd,
                'error': {
                    'code': 'invalid_code',
                    'message': 'Mã phải bắt đầu bằng PL hoặc IB (thêm --continue-on-invalid để bỏ qua mã sai)',
                    'invalid_items': invalid,
                },
            }

        if continue_on_invalid and not valid_codes:
            return {
                'status': 'error',
                'command': cmd,
                'error': {
                    'code': 'invalid_code',
                    'message': 'Không có mã hợp lệ PL/IB để chạy batch',
                    'invalid_items': invalid,
                },
            }

        if not token:
            return {
                'status': 'error',
                'command': cmd,
                'error': {'code': 'login_error', 'message': 'lỗi login'},
            }

        run_codes = valid_codes if continue_on_invalid else codes

        # Backward-compatible single export behavior.
        if len(run_codes) == 1:
            code = run_codes[0]
            data = _run_json([
                'python3', str(SCRIPTS_DIR / 'msc_exp_unified.py'),
                '--code', code,
                '--token', token,
            ] + (['--cookie', cookie] if cookie else []))
            return {
                'status': 'ok',
                'command': cmd,
                'detected_type': ('khlcnt' if code.startswith('PL') else 'tbmt'),
                'result': data,
            }

        # Batch export: each PL/IB -> one .md file (if success)
        items = []
        success = 0
        for code in run_codes:
            data = _run_json([
                'python3', str(SCRIPTS_DIR / 'msc_exp_unified.py'),
                '--code', code,
                '--token', token,
            ] + (['--cookie', cookie] if cookie else []))
            st = (data or {}).get('status') if isinstance(data, dict) else 'error'
            ok = isinstance(data, dict) and bool(data.get('file')) and st not in ('login_error', 'invalid_code', 'invalid_pl', 'invalid_ib', 'not_found', 'error')
            if ok:
                success += 1
            items.append({
                'code': code,
                'detected_type': ('khlcnt' if code.startswith('PL') else 'tbmt'),
                'status': st,
                'file': (data.get('file') if isinstance(data, dict) else None),
                'message': (data.get('message') if isinstance(data, dict) else None),
                'result': data,
            })

        # Append invalid items as skipped when continue-on-invalid mode is enabled.
        if continue_on_invalid and invalid:
            for code in invalid:
                items.append({
                    'code': code,
                    'detected_type': 'unknown',
                    'status': 'skipped_invalid',
                    'file': None,
                    'message': 'Bỏ qua do mã không hợp lệ (continue-on-invalid)',
                    'result': {'status': 'skipped_invalid'},
                })

        failed = len([x for x in items if x.get('status') not in ('ok', 'partial', 'skipped_invalid')])
        skipped = len([x for x in items if x.get('status') == 'skipped_invalid'])
        top_status = 'ok' if success > 0 else ('partial' if skipped > 0 else 'error')
        return {
            'status': top_status,
            'command': cmd,
            'detected_type': 'batch',
            'result': {
                'mode': 'batch',
                'continue_on_invalid': continue_on_invalid,
                'total_input': len(codes),
                'total_executed': len(run_codes),
                'success': success,
                'failed': failed,
                'skipped_invalid': skipped,
                'invalid_items': invalid,
                'items': items,
            },
        }

def main() -> None:
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='MSC MVP router for Telegram bot2 canary')
    ap.add_argument('text', help='Raw user query, e.g. /tbmt 5 benh vien bach mai')
    ap.add_argument('--canary-percent', type=int, default=None, help='Override canary percent 0..100')
    ap.add_argument('--seed-key', default='', help='Stable key for deterministic sampling (user/thread/message)')
    ap.add_argument('--markdown', action='store_true', help='Render markdown report from selected path result')
    args = ap.parse_args()

    text_norm = args.text.strip().lower()
    if re.match(r'^(?:@\w+\s+)?/expt(?:@\w+)?\b', text_norm):
        print(json.dumps({
            'status': 'error',
            'selected_path': 'direct-script',
            'query': args.text,
            'command': 'expt',
            'error': {'code': 'deprecated_command', 'message': 'Lệnh /expt đã bị bỏ. Dùng /exp <PL...|IB...>'},
        }, ensure_ascii=False, indent=2))
        return

    direct = _run_direct_command(args.text)
    if direct is not None:
        print(json.dumps({
            'status': direct.get('status', 'ok'),
            'selected_path': 'direct-script',
            'query': args.text,
            **direct,
        }, ensure_ascii=False, indent=2))
        return

    env_pct = int(os.environ.get('BOT2_MSC_CANARY_PERCENT', '0') or 0)
    pct = max(0, min(100, args.canary_percent if args.canary_percent is not None else env_pct))

    route = route_query(args.text)
    is_candidate = route.intent in {'list_tbmt', 'list_kh'} and bool(route.unit)
    seed = args.seed_key.strip() or f"{args.text.strip().lower()}|{route.intent}|{route.unit or ''}|{route.n or ''}"
    hit = is_candidate and _deterministic_hit(seed, pct)

    if hit:
        schema = dispatch(route)
        selected = 'canary'
    else:
        schema = _legacy_dispatch(args.text)
        selected = 'legacy'

    md_path = None
    if args.markdown:
        md_path = str(render_markdown(schema))

    out = {
        'status': 'ok' if not schema.error else 'error',
        'selected_path': selected,
        'canary_percent': pct,
        'canary_hit': hit,
        'candidate_for_canary': is_candidate,
        'routed_intent': route.intent,
        'query': args.text,
        'result': schema.to_json(),
        'markdown_path': md_path,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()