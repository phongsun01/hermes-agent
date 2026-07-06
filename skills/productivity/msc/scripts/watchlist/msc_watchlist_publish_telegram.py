#!/usr/bin/env python3
"""Publish MSC watchlist report to Telegram (bot2) with fixed short template + attached .md file.

Hard-fix goal: avoid LLM drift/forget after gateway restart by moving formatting/sending into deterministic script.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

SKILL_ROOT = Path(__file__).parent.parent.parent  # scripts/watchlist/publish_telegram.py -> msc/
WS2 = SKILL_ROOT
LATEST_SCRIPT = SKILL_ROOT / 'scripts/watchlist/msc_watchlist_latest_tbmt.py'
OUT_DIR = SKILL_ROOT / 'reports/msc_tbmt'

KEYWORDS = [
    'thiết bị y tế', 'x-quang', 'x quang', 'siêu âm', 'dsa', 'nội soi', 'ct', 'mri',
    'máy thở', 'xét nghiệm', 'pcr', 'monitor', 'bơm truyền', 'hóa chất', 'vật tư',
]


@dataclass
class Row:
    unit: str
    unit_id: str
    notify_no: str
    public_date: Optional[datetime]
    name: str
    source_field: str
    has_data: bool = True
    error: str = ''


def _parse_dt(s: str) -> Optional[datetime]:
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
    except Exception:
        return None


def _load_latest(n: int) -> List[Dict[str, Any]]:
    p = subprocess.run(
        ['/opt/homebrew/bin/python3', str(LATEST_SCRIPT), '-n', str(n)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if p.returncode != 0:
        raise RuntimeError(f'latest_tbmt_failed: {p.stderr.strip() or p.stdout.strip()}')
    try:
        data = json.loads((p.stdout or '[]').strip() or '[]')
    except Exception as e:
        raise RuntimeError(f'latest_tbmt_json_error: {e}')
    if not isinstance(data, list):
        raise RuntimeError('latest_tbmt_unexpected_output')
    return data


def _to_rows(items: List[Dict[str, Any]]) -> List[Row]:
    rows: List[Row] = []
    for it in items:
        has_data = not bool(it.get('error')) and bool(it.get('notifyNo'))
        rows.append(Row(
            unit=str(it.get('unit') or '').strip(),
            unit_id=str(it.get('id') or '').strip(),
            notify_no=str(it.get('notifyNo') or '').strip(),
            public_date=_parse_dt(str(it.get('publicDate') or '')),
            name=str(it.get('name') or '').strip(),
            source_field=str(it.get('sourceField') or '').strip(),
            has_data=has_data,
            error=json.dumps(it.get('error'), ensure_ascii=False) if it.get('error') else '',
        ))
    return rows


def _is_today(dt: Optional[datetime], today: datetime, has_data: bool = True) -> bool:
    return bool(has_data and dt and dt.date() == today.date())


def _is_yesterday(dt: Optional[datetime], today: datetime, has_data: bool = True) -> bool:
    return bool(has_data and dt and dt.date() == (today.date() - timedelta(days=1)))


def _pick_breakings(today_rows: List[Row]) -> List[Row]:
    candidates = [r for r in today_rows if r.has_data]
    if not candidates:
        return []

    # Breaking news = all rows matching med-device keyword set, newest first.
    hits: List[Row] = []
    for r in candidates:
        name_l = (r.name or '').lower()
        if any(k in name_l for k in KEYWORDS):
            hits.append(r)

    return sorted(hits, key=lambda r: (r.public_date or datetime.min), reverse=True)


def _short_message(rows: List[Row], filename: str) -> str:
    now = datetime.now()
    today_rows = [r for r in rows if _is_today(r.public_date, now, r.has_data)]
    yesterday_rows = [r for r in rows if _is_yesterday(r.public_date, now, r.has_data)]
    no_data_rows = [r for r in rows if not r.has_data]

    lines: List[str] = []
    lines.append('📊 **WATCHLIST MSC**')
    lines.append('')
    lines.append('1️⃣ **Tổng quan**')
    lines.append(f'- Tổng đơn vị watchlist: **{len(rows)}**')
    lines.append(f'- Hôm qua: **{len(yesterday_rows)}**')
    lines.append(f'- Hôm nay: **{len(today_rows)}**')
    lines.append(f'- Đơn vị chưa có dữ liệu: **{len(no_data_rows)}**')
    lines.append('')
    lines.append('2️⃣ Theo đơn vị (Tên | Hôm qua | Hôm nay)')
    lines.append('')
    for i, r in enumerate(rows, 1):
        y = 1 if _is_yesterday(r.public_date, now, r.has_data) else 0
        t = 1 if _is_today(r.public_date, now, r.has_data) else 0
        unit = (r.unit or '').strip()
        lines.append(f'{i}. {unit} | {y} | {t}')

    breakings = _pick_breakings(today_rows)
    lines.append('')
    lines.append('3️⃣ **🔥 Breaking news**')
    if breakings:
        for idx, b in enumerate(breakings, 1):
            lines.append(f'{idx}. {b.unit} vừa đăng TBMT số **{b.notify_no}**')
            lines.append(f'   - Gói thầu: **{b.name}**')
    else:
        lines.append('- Chưa có bản ghi nổi bật trong ngày.')

    lines.append('')
    lines.append('4️⃣ **📎 File chi tiết**')
    lines.append(f'- {filename}')
    return '\n'.join(lines)


def _detail_markdown(rows: List[Row], filename: str) -> str:
    now_s = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with_data = sum(1 for r in rows if r.has_data)
    without_data = len(rows) - with_data
    lines: List[str] = [
        '# Báo cáo MSC Watchlist TBMT',
        '',
        f'- Thời điểm tạo: {now_s}',
        f'- File: `{filename}`',
        f'- Tổng đơn vị watchlist: {len(rows)}',
        f'- Số đơn vị có dữ liệu: {with_data}',
        f'- Số đơn vị chưa có dữ liệu: {without_data}',
        '',
        '## Danh sách latest TBMT theo đơn vị',
        '',
        '| # | Đơn vị | Mã đơn vị | Hôm qua | Hôm nay | Số TBMT | PublicDate | Trường lọc | Tên gói thầu | Trạng thái |',
        '|---|---|---|---:|---:|---|---|---|---|---|',
    ]
    now = datetime.now()
    for i, r in enumerate(rows, 1):
        y = 1 if _is_yesterday(r.public_date, now, r.has_data) else 0
        t = 1 if _is_today(r.public_date, now, r.has_data) else 0
        pd = r.public_date.strftime('%Y-%m-%d %H:%M:%S') if r.public_date else ''
        name = (r.name or '').replace('|', '\\|')
        status = 'ok' if r.has_data else 'no_data'
        lines.append(f'| {i} | {r.unit} | {r.unit_id} | {y} | {t} | {r.notify_no} | {pd} | {r.source_field} | {name} | {status} |')
    lines.append('')
    lines.append('---')
    lines.append('Nguồn: scripts/msc_watchlist_latest_tbmt.py (dual-field fallback procuringEntityCode/investorCode).')
    return '\n'.join(lines)


def _extract_json(raw: str) -> Dict[str, Any]:
    s = (raw or '').strip()
    i = s.rfind('{')
    while i >= 0:
        chunk = s[i:]
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        i = s.rfind('{', 0, i)
    raise ValueError(f'no_json_found: {s}')


def _normalize_send_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    # openclaw message send --json may return either {ok,messageId,...}
    # or wrapper shape {action, payload:{ok,messageId,...}}
    if 'payload' in obj and isinstance(obj.get('payload'), dict):
        return obj['payload']
    return obj


def _send_text(account: str, target: str, message: str) -> str:
    p = subprocess.run(
        ['openclaw', 'message', 'send', '--channel', 'telegram', '--account', account, '--target', target, '--message', message, '--json'],
        capture_output=True,
        text=True,
        timeout=120,
    )
    raw = ((p.stdout or '') + '\n' + (p.stderr or '')).strip()
    if p.returncode != 0:
        raise RuntimeError(f'send_text_failed: {raw}')
    try:
        obj = _normalize_send_result(_extract_json(raw))
    except Exception:
        raise RuntimeError(f'send_text_parse_failed: {raw}')
    if not obj.get('ok'):
        raise RuntimeError(f'send_text_not_ok: {obj}')
    return str(obj.get('messageId') or '')


def _send_file(account: str, target: str, path: Path, caption: str) -> str:
    p = subprocess.run(
        ['openclaw', 'message', 'send', '--channel', 'telegram', '--account', account, '--target', target, '--media', str(path), '--message', caption, '--json'],
        capture_output=True,
        text=True,
        timeout=120,
    )
    raw = ((p.stdout or '') + '\n' + (p.stderr or '')).strip()
    if p.returncode != 0:
        raise RuntimeError(f'send_file_failed: {raw}')
    try:
        obj = _normalize_send_result(_extract_json(raw))
    except Exception:
        raise RuntimeError(f'send_file_parse_failed: {raw}')
    if not obj.get('ok'):
        raise RuntimeError(f'send_file_not_ok: {obj}')
    return str(obj.get('messageId') or '')


def _normalize_artifact_ts(raw: str | None) -> str:
    if raw:
        s = raw.strip().replace(' ', '_').replace(':', '-')
        if s:
            return s
    # default: slot minute fixed to 00 to keep cross-channel stable in same hour slot
    return datetime.now().strftime('%Y-%m-%d_%H-00')


def main() -> int:
    ap = argparse.ArgumentParser(description='Publish MSC watchlist short report + md file to Telegram.')
    ap.add_argument('--n', type=int, default=999, help='Max units to fetch (default: 999 = all)')
    ap.add_argument('--account', default='', help='Openclaw bot account (empty = use hermes cron deliver)')
    ap.add_argument('--target', default='5511250191')
    ap.add_argument('--artifact-ts', default='', help='Artifact timestamp key, e.g. 2026-03-23_18-00')
    ap.add_argument('--send', action='store_true', help='Actually send to Telegram')
    ns = ap.parse_args()

    items = _load_latest(ns.n)
    rows = _to_rows(items)
    if not rows:
        raise SystemExit('SENT_FAIL no_rows')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art_ts = _normalize_artifact_ts(ns.artifact_ts)
    filename = f"msc_tbmt_{art_ts}.md"
    detail_path = OUT_DIR / filename
    detail_path.write_text(_detail_markdown(rows, filename), encoding='utf-8')

    short = _short_message(rows, filename)

    sidecar = {
        'ok': True,
        'artifact_ts': art_ts,
        'filename': filename,
        'detail_path': str(detail_path),
        'short': short,
        'rows': [
            {
                'unit': r.unit,
                'id': r.unit_id,
                'notifyNo': r.notify_no,
                'publicDate': r.public_date.strftime('%Y-%m-%dT%H:%M:%S') if r.public_date else '',
                'name': r.name,
                'sourceField': r.source_field,
                'hasData': r.has_data,
            }
            for r in rows
        ],
        'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
    }
    sidecar_path = OUT_DIR / f"msc_tbmt_{art_ts}.json"
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding='utf-8')

    if not ns.send:
        print(json.dumps({'ok': True, 'mode': 'preview', 'artifact_ts': art_ts, 'filename': filename, 'short': short, 'sidecar': str(sidecar_path)}, ensure_ascii=False, indent=2))
        return 0

    # Output for hermes send_message tool (via cron or direct call)
    # Format: short text + MEDIA:<path> for file attachment
    print(short)
    print(f"\nMEDIA:{detail_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
