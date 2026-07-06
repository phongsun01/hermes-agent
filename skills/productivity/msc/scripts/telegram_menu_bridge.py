#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from typing import Any

ROUTER = "scripts/msc_mvp_router.py"


def _run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _get_in(obj: dict[str, Any], path: list[str]) -> Any:
    cur: Any = obj
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _extract_chat_id(event: dict[str, Any]) -> str:
    # Flat fields
    for k in ("threadId", "thread_id", "chat_id", "target", "peerId"):
        v = event.get(k)
        if v:
            return str(v)

    # Common Telegram webhook/update shapes
    candidate_paths = [
        ["chat", "id"],
        ["message", "chat", "id"],
        ["callback_query", "message", "chat", "id"],
        ["callbackQuery", "message", "chat", "id"],
        ["edited_message", "chat", "id"],
        ["channel_post", "chat", "id"],
    ]
    for p in candidate_paths:
        v = _get_in(event, p)
        if v is not None and str(v).strip():
            return str(v)

    return ""


def _extract_account_id(event: dict[str, Any]) -> str:
    for k in ("accountId", "account_id"):
        v = event.get(k)
        if v:
            return str(v)
    return "bot2"


def _load_event_fallback() -> dict[str, Any]:
    # Try common runtime env payloads when --event-json is absent/invalid
    keys = [
        "OPENCLAW_EVENT_JSON",
        "OPENCLAW_MESSAGE_JSON",
        "OPENCLAW_INBOUND_JSON",
        "MESSAGE_JSON",
        "INBOUND_MESSAGE_JSON",
        "TELEGRAM_MESSAGE_JSON",
    ]
    for k in keys:
        raw = (os.environ.get(k) or "").strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return {}




def _compact_precheck_fail(output: str, max_len: int = 500) -> str:
    raw = ' '.join((output or '').split())
    if not raw:
        return '🚨 Skills precheck FAIL'

    def _kv(name: str) -> str:
        pat = re.compile(re.escape(name) + r'=(".*?"|\S+)')
        m = pat.search(raw)
        if not m:
            return ''
        v = m.group(1).strip()
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1]
        return v

    if 'PRECHECK_FAIL' not in raw:
        msg = f"🚨 Skills precheck FAIL | {raw}"
        return msg[:max_len]

    reason = _kv('reason') or 'UNKNOWN'
    lint_err = _kv('lint_err') or '?'
    sim_err = _kv('sim_err') or '?'
    last3 = _kv('recent_last3') or 'none'
    hist = _kv('reason_hist') or 'none'
    runbook = _kv('runbook')
    if '/' in runbook:
        runbook = runbook.rsplit('/', 1)[-1]

    compact_reason = reason
    if reason == 'CITATION_UNDER_COVERAGE_CANARY':
        compact_reason = 'CITATION_UNDER_COV'

    track = 'OTHER'
    if reason.startswith('SIM_'):
        track = 'SIM'
    elif reason.startswith('CITATION_'):
        track = 'CITATION'
    elif reason.startswith('LINT_'):
        track = 'LINT'
    elif reason.startswith('MEMORY_VERIFY_'):
        track = 'MEMORY'

    msg = (
        f"🚨 Skills precheck FAIL | track:{track} reason:{compact_reason} | lint_err:{lint_err} sim_err:{sim_err} "
        f"| last3:{last3} | hist:{hist}"
    )
    if runbook:
        msg += f" | runbook:{runbook}"

    return msg[:max_len]


def _render_router_payload(payload: dict[str, Any]) -> tuple[str, list[list[dict[str, str]]], bool]:
    """Return (text, buttons, no_reply)."""
    status = str((payload or {}).get('status') or 'ok').lower()
    command = str((payload or {}).get('command') or '')
    sub_action = str((payload or {}).get('sub_action') or '')
    result = (payload or {}).get('result')
    if not isinstance(result, dict):
        result = {}

    # Silent/no-reply mode (used by /skills precheck notify)
    if bool(result.get('no_reply')) or bool(result.get('silent')):
        return '', [], True

    # Menu payload keeps original rich buttons
    if command == 'menu':
        text = str(result.get('text') or '📌 Menu')
        buttons = result.get('buttons') or []
        return text, buttons, False

    # Skills precheck: compact operational message
    if command == 'skills' and sub_action == 'precheck':
        out = str(result.get('output') or '').strip()
        if status == 'ok':
            text = f"✅ Skills precheck OK\n{out}" if out else '✅ Skills precheck OK'
            return text[:1800], [], False

        # A3: fail alert optimized for mobile readability (<=500 chars)
        text = _compact_precheck_fail(out, max_len=500)
        return text, [], False

    # Generic fallback for non-menu command bridge
    if status != 'ok':
        err = (payload or {}).get('error') or {}
        emsg = ''
        if isinstance(err, dict):
            emsg = str(err.get('message') or err.get('code') or '').strip()
        text = f"❌ {command or 'command'} {sub_action or ''}".strip()
        if emsg:
            text += f"\n{emsg}"
        return text[:1800], [], False

    if isinstance(result.get('preview_text'), str) and result.get('preview_text').strip():
        return result.get('preview_text').strip()[:1800], [], False
    if isinstance(result.get('output'), str) and result.get('output').strip():
        return result.get('output').strip()[:1800], [], False
    if isinstance(result.get('usage'), list) and result.get('usage'):
        lines = ['📘 Usage:'] + [str(x) for x in result.get('usage', [])]
        return '\n'.join(lines)[:1800], [], False

    return f"✅ {command or 'ok'} {sub_action or ''}".strip()[:1800], [], False

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--command", required=True)
    ap.add_argument("--event-json", default="")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    event: dict[str, Any] = {}
    raw_event = (ns.event_json or "").strip()
    if raw_event:
        try:
            obj = json.loads(raw_event)
            if not isinstance(obj, dict):
                raise ValueError("event_json_not_object")
            event = obj
        except Exception:
            # tolerate bad CLI payload and fallback to env context
            event = _load_event_fallback()
            if not event:
                print(json.dumps({"ok": False, "error": "invalid_event_json (không đọc được event context)"}, ensure_ascii=False))
                return 1
    else:
        event = _load_event_fallback()
        if not event:
            print(json.dumps({"ok": False, "error": "missing_event_context"}, ensure_ascii=False))
            return 1

    rc, out, err = _run(["python3", ROUTER, ns.command])
    if rc != 0:
        print(json.dumps({"ok": False, "error": err or out or "router_failed"}, ensure_ascii=False))
        return 1

    try:
        payload = json.loads(out)
    except Exception:
        print(json.dumps({"ok": False, "error": "router_invalid_json", "raw": out[:400]}, ensure_ascii=False))
        return 1

    text, buttons, no_reply = _render_router_payload(payload)

    if no_reply:
        print(json.dumps({"ok": True, "skipped": True, "reason": "no_reply", "router": payload}, ensure_ascii=False))
        return 0

    chat_id = _extract_chat_id(event)
    account_id = _extract_account_id(event)
    if not chat_id:
        print(json.dumps({"ok": False, "error": "missing_chat_id_in_event"}, ensure_ascii=False))
        return 1

    send_cmd = [
        "openclaw", "message", "send",
        "--channel", "telegram",
        "--account", account_id,
        "--target", chat_id,
        "--message", text,
        "--buttons", json.dumps(buttons, ensure_ascii=False),
        "--json",
    ]
    if ns.dry_run:
        send_cmd.insert(-1, "--dry-run")
    rc2, out2, err2 = _run(send_cmd)
    if rc2 != 0:
        print(json.dumps({"ok": False, "error": err2 or out2 or "send_failed", "router": payload}, ensure_ascii=False))
        return 1

    try:
        sent = json.loads(out2) if out2 else {"ok": True}
    except Exception:
        sent = {"ok": True, "raw": out2}

    print(json.dumps({"ok": True, "sent": sent, "router": payload}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
