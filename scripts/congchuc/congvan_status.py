#!/usr/bin/env python3
"""
Congvan status tracking — update/query VB status via Zalo replies.

Commands:
  done <so_den>       — Mark as done
  wip <so_den>        — Work in progress
  read <so_den>       — Mark as read
  note <so_den> <text> — Add note
  status <so_den>     — Query current status
  list [--status <s>] — List VBs (optionally filter by status)

State file: ~/.hermes/cron/cong-van-den/vbden_state.json
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import os
import re
import datetime

STATE_FILE = os.path.join(
    os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")),
    "cron", "cong-van-den", "vbden_state.json"
)

VALID_STATUSES = {"new", "read", "wip", "done", "overdue"}


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen_ids": [], "last_check": None, "last_count": 0}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def migrate_state(state):
    if "documents" in state:
        return state
    if "seen_ids" in state:
        state["documents"] = {}
        for doc_id in state.get("seen_ids", []):
            state["documents"][str(doc_id)] = {
                "so_den": str(doc_id),
                "so_ky_hieu": "",
                "tac_gia": "",
                "trich_yeu": "",
                "status": "new",
                "status_updated_at": None,
                "note": "",
            }
    return state


def update_status(state, so_den, new_status, note=None):
    state = migrate_state(state)
    docs = state.get("documents", {})
    if so_den not in docs:
        return False, f"Không tìm thấy văn bản số {so_den}"
    if new_status is not None and new_status not in VALID_STATUSES:
        return False, f"Trạng thái không hợp lệ: {new_status} (chấp nhận: {', '.join(sorted(VALID_STATUSES))})"
    if new_status is not None:
        docs[so_den]["status"] = new_status
    docs[so_den]["status_updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if note is not None:
        docs[so_den]["note"] = note
    state["documents"] = docs
    save_state(state)
    action = f"→ {new_status}" if new_status else "cập nhật ghi chú"
    return True, f"Đã cập nhật VB #{so_den} {action}"


def get_status(state, so_den):
    state = migrate_state(state)
    docs = state.get("documents", {})
    if so_den not in docs:
        return f"Không tìm thấy văn bản số {so_den}"
    doc = docs[so_den]
    lines = [
        f"VB #{so_den}",
        f"  Số công văn: {doc.get('so_ky_hieu', 'N/A')}",
        f"  Tác giả: {doc.get('tac_gia', 'N/A')}",
        f"  Trích yếu: {doc.get('trich_yeu', 'N/A')[:100]}",
        f"  Trạng thái: {doc.get('status', 'new')}",
        f"  Cập nhật: {doc.get('status_updated_at', 'N/A')}",
    ]
    if doc.get("note"):
        lines.append(f"  Ghi chú: {doc['note']}")
    return "\n".join(lines)


def list_documents(state, status_filter=None):
    state = migrate_state(state)
    docs = state.get("documents", {})
    if not docs:
        return "Không có văn bản nào trong hệ thống."
    filtered = docs
    if status_filter:
        filtered = {k: v for k, v in docs.items() if v.get("status") == status_filter}
    if not filtered:
        return f"Không có VB nào với trạng thái '{status_filter}'."
    sorted_docs = sorted(filtered.values(), key=lambda d: d.get("status_updated_at", "0") or "0", reverse=True)
    lines = [f"Tổng: {len(sorted_docs)} VB"]
    for doc in sorted_docs[:20]:  # Limit output
        so_den = doc.get("so_den", "?")
        status = doc.get("status", "new")
        tac_gia = doc.get("tac_gia", "?")[:30]
        trich_yeu = doc.get("trich_yeu", "")[:60]
        lines.append(f"  #{so_den} [{status}] {tac_gia}: {trich_yeu}")
    if len(sorted_docs) > 20:
        lines.append(f"  ... và {len(sorted_docs) - 20} VB khác")
    return "\n".join(lines)


def process_command(text):
    """Parse and execute a status command. Returns response string."""
    text = text.strip()

    # done <so_den>
    m = re.match(r"^done\s+(\d+)$", text, re.IGNORECASE)
    if m:
        state = load_state()
        ok, msg = update_status(state, m.group(1), "done")
        return msg

    # wip <so_den>
    m = re.match(r"^wip\s+(\d+)$", text, re.IGNORECASE)
    if m:
        state = load_state()
        ok, msg = update_status(state, m.group(1), "wip")
        return msg

    # read <so_den>
    m = re.match(r"^read\s+(\d+)$", text, re.IGNORECASE)
    if m:
        state = load_state()
        ok, msg = update_status(state, m.group(1), "read")
        return msg

    # note <so_den> <text>
    m = re.match(r"^note\s+(\d+)\s+(.+)$", text, re.IGNORECASE)
    if m:
        state = load_state()
        ok, msg = update_status(state, m.group(1), None, note=m.group(2))
        return msg

    # status <so_den>
    m = re.match(r"^status\s+(\d+)$", text, re.IGNORECASE)
    if m:
        state = load_state()
        return get_status(state, m.group(1))

    # list [--status <s>]
    m = re.match(r"^list(?:\s+--status\s+(\w+))?$", text, re.IGNORECASE)
    if m:
        state = load_state()
        return list_documents(state, status_filter=m.group(1))

    return None  # Not a status command


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: congvan_status.py <command>")
        print("Commands: done <id>, wip <id>, read <id>, note <id> <text>, status <id>, list [--status <s>]")
        sys.exit(1)
    text = " ".join(sys.argv[1:])
    result = process_command(text)
    if result:
        print(result)
    else:
        print(f"Unknown command: {text}")
        sys.exit(1)
