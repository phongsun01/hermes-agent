#!/usr/bin/env python3
"""
msc-watchlist skill bridge
Handles /fl commands for watchlist management
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent.parent  # scripts/watchlist/bridge.py -> msc/
SCRIPTS_DIR = SKILL_ROOT / 'scripts/watchlist'
MANAGE_SCRIPT = str(SCRIPTS_DIR / 'msc_watchlist_manage.py')
EXPORT_SCRIPT = str(SCRIPTS_DIR / 'msc_watchlist_export.py')
PREFETCH_SCRIPT = str(SCRIPTS_DIR / 'msc_watchlist_prefetch.py')
LATEST_SCRIPT = str(SCRIPTS_DIR / 'msc_watchlist_latest_tbmt.py')
PUBLISH_TELEGRAM_SCRIPT = str(SCRIPTS_DIR / 'msc_watchlist_publish_telegram.py')
PUBLISH_ZALO_SCRIPT = str(SCRIPTS_DIR / 'msc_watchlist_publish_zalo.py')


def run_cmd(cmd, timeout=60):
    """Run command and return (ok, stdout, stderr)"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.returncode == 0, p.stdout.strip(), p.stderr.strip())
    except subprocess.TimeoutExpired:
        return (False, "", "timeout")
    except Exception as e:
        return (False, "", str(e))


def format_list_output(stdout):
    """Parse and format watchlist list output"""
    try:
        data = json.loads(stdout)
        status = str(data.get("status") or "").lower()
        if status not in {"ok", "success"}:
            return f"❌ Lỗi: {data.get('error', status or 'unknown')}"

        units = data.get("units", [])
        if not units:
            return "📋 Watchlist trống"

        lines = [f"📋 Watchlist ({len(units)} units):"]
        for i, u in enumerate(units, 1):
            uid = u.get("id", "")
            name = u.get("name", uid)
            lines.append(f"{i}. {uid} - {name}")
        return "\n".join(lines)
    except Exception:
        return stdout or "✅ Hoàn thành"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-json", required=True, help="Event JSON string")
    ap.add_argument("--command", required=True, help="Command text")
    args = ap.parse_args()

    try:
        event = json.loads(args.event_json)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"invalid_event_json:{e}"}))
        return 1

    command_text = (args.command or "").strip()
    parts = command_text.split()
    
    if len(parts) < 2:
        print(json.dumps({"ok": True, "reply_text": "⚠️ Cú pháp: /fl <list|add|remove|export|prefetch|latest|publish>"}))
        return 0

    action = parts[1].lower()
    known_actions = {"list", "add", "remove", "export", "prefetch", "latest", "publish"}

    # Backward compatibility: legacy "/fl <unit_id>" => resolve name + add
    if action not in known_actions and len(parts) == 2:
        unit_id = parts[1]
        
        # Try to resolve unit name from MSC
        resolve_script = "scripts/msc_unit_resolve.py"
        ok_resolve, out_resolve, _ = run_cmd(["python3", resolve_script, unit_id], timeout=10)
        
        unit_name = unit_id  # fallback
        if ok_resolve:
            try:
                import json as json_lib
                resolve_data = json_lib.loads(out_resolve)
                if resolve_data.get("status") == "ok" and resolve_data.get("unit"):
                    unit_name = resolve_data["unit"].get("name", unit_id)
            except Exception:
                pass
        
        cmd = ["python3", MANAGE_SCRIPT, "add", "--id", unit_id, "--name", unit_name]
        ok, out, err = run_cmd(cmd)
        if ok:
            print(json.dumps({"ok": True, "reply_text": f"✅ Đã thêm {unit_id} - {unit_name} vào watchlist"}))
            return 0
        print(json.dumps({"ok": False, "error": err or out or "legacy_add_failed"}))
        return 1
    
    # /fl list
    if action == "list":
        ok, out, err = run_cmd(["python3", MANAGE_SCRIPT, "list"])
        if ok:
            reply = format_list_output(out)
            print(json.dumps({"ok": True, "reply_text": reply}))
            return 0
        print(json.dumps({"ok": False, "error": err or out or "list_failed"}))
        return 1
    
    # /fl add <id> [name]
    if action == "add":
        if len(parts) < 3:
            print(json.dumps({"ok": True, "reply_text": "⚠️ Cú pháp: /fl add <id> [name]"}))
            return 0
        
        unit_id = parts[2]
        name = " ".join(parts[3:]) if len(parts) > 3 else unit_id
        
        cmd = ["python3", MANAGE_SCRIPT, "add", "--id", unit_id, "--name", name]
        ok, out, err = run_cmd(cmd)
        if ok:
            print(json.dumps({"ok": True, "reply_text": f"✅ Đã thêm {unit_id} - {name} vào watchlist"}))
            return 0
        print(json.dumps({"ok": False, "error": err or out or "add_failed"}))
        return 1
    
    # /fl remove <id>
    if action == "remove":
        if len(parts) < 3:
            print(json.dumps({"ok": True, "reply_text": "⚠️ Cú pháp: /fl remove <id>"}))
            return 0
        
        unit_id = parts[2]
        cmd = ["python3", MANAGE_SCRIPT, "remove", "--id", unit_id]
        ok, out, err = run_cmd(cmd)
        if ok:
            print(json.dumps({"ok": True, "reply_text": f"✅ Đã xóa {unit_id} khỏi watchlist"}))
            return 0
        print(json.dumps({"ok": False, "error": err or out or "remove_failed"}))
        return 1
    
    # /fl export [--ids-only|--prompt]
    if action == "export":
        cmd = ["python3", EXPORT_SCRIPT]
        if "--ids-only" in parts:
            cmd.append("--ids-only")
        elif "--prompt" in parts:
            cmd.append("--prompt")
        
        ok, out, err = run_cmd(cmd)
        if ok:
            print(json.dumps({"ok": True, "reply_text": out or "✅ Export hoàn thành"}))
            return 0
        print(json.dumps({"ok": False, "error": err or out or "export_failed"}))
        return 1
    
    # /fl prefetch
    if action == "prefetch":
        ok, out, err = run_cmd(["python3", PREFETCH_SCRIPT], timeout=300)
        if ok:
            print(json.dumps({"ok": True, "reply_text": "✅ Prefetch cache hoàn thành"}))
            return 0
        print(json.dumps({"ok": False, "error": err or out or "prefetch_failed"}))
        return 1
    
    # /fl latest [n]
    if action == "latest":
        n = parts[2] if len(parts) > 2 else "5"
        cmd = ["python3", LATEST_SCRIPT, "-n", n]
        ok, out, err = run_cmd(cmd, timeout=120)
        if ok:
            print(json.dumps({"ok": True, "reply_text": out or "✅ Latest TBMT hoàn thành"}))
            return 0
        print(json.dumps({"ok": False, "error": err or out or "latest_failed"}))
        return 1
    
    # /fl publish telegram|zalo
    if action == "publish":
        if len(parts) < 3:
            print(json.dumps({"ok": True, "reply_text": "⚠️ Cú pháp: /fl publish <telegram|zalo>"}))
            return 0
        
        target = parts[2].lower()
        if target == "telegram":
            cmd = ["python3", PUBLISH_TELEGRAM_SCRIPT, "--n", "999"]
            ok, out, err = run_cmd(cmd, timeout=120)
            if ok:
                print(json.dumps({"ok": True, "reply_text": "📤 Đã publish watchlist update lên Telegram"}))
                return 0
            print(json.dumps({"ok": False, "error": err or out or "publish_telegram_failed"}))
            return 1
        
        elif target == "zalo":
            cmd = ["python3", PUBLISH_ZALO_SCRIPT, "--n", "999"]
            ok, out, err = run_cmd(cmd, timeout=120)
            if ok:
                print(json.dumps({"ok": True, "reply_text": "📤 Đã publish watchlist update lên Zalo"}))
                return 0
            print(json.dumps({"ok": False, "error": err or out or "publish_zalo_failed"}))
            return 1
        
        else:
            print(json.dumps({"ok": True, "reply_text": "⚠️ Target phải là telegram hoặc zalo"}))
            return 0
    
    print(json.dumps({"ok": False, "error": f"unknown_action:{action}"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
