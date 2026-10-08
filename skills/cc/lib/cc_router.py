#!/usr/bin/env python3
import sys
import json
import subprocess
import os
from pathlib import Path

# Enable UTF-8 encoding for Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_ROOT = Path(__file__).parent.parent
from inline_menu_payload import _build_inline_menu_payload

def _run_script(cmd: list) -> str:
    """Run a script and return its stdout or stderr."""
    try:
        # Run uv run python ... inside /opt/data
        # Note: we need to use relative or absolute path appropriately
        # Because we run inside Docker or WSL, we will just use subprocess.run
        # We need to prepend 'uv', 'run', 'python'
        full_cmd = ["uv", "run", "python"] + cmd
        result = subprocess.run(
            full_cmd, 
            capture_output=True, 
            text=True, 
            timeout=45
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"❌ Lỗi ({result.returncode}):\n{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "⏱️ Lỗi: Quá thời gian xử lý (45s)."
    except Exception as e:
        return f"❌ Lỗi hệ thống: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": {"message": "Thiếu callback data"}}))
        return

    data = sys.argv[1]
    
    # Expected format: v1|cc|<action>|<args...>
    parts = data.split("|")
    if len(parts) < 3:
        print(json.dumps({"error": {"message": "Invalid callback data"}}))
        return

    action_type = parts[2] # 'open' or 'run'
    
    if action_type == 'open':
        level = parts[3] if len(parts) > 3 else 'root'
        payload_data = {}
        
        if level == 'select_doc':
            # Get list of new documents
            out = _run_script(["/opt/data/skills/cc/scripts/congvan_status.py", "list", "--status", "new"])
            docs = []
            if out and not out.startswith("❌") and not out.startswith("⏱️"):
                for line in out.splitlines():
                    # Parse `#2649 [new]...`
                    if line.strip().startswith('#'):
                        doc_id = line.strip().split()[0][1:]
                        docs.append(doc_id)
            payload_data['docs'] = docs
            
        elif level == 'doc':
            payload_data['doc_id'] = parts[4] if len(parts) > 4 else '0'
            
        payload = _build_inline_menu_payload(level, payload_data)
        
        print(json.dumps({
            "status": "ok",
            "command": "ccmenu",
            "result": {
                "text": payload.get("text", "Không có nội dung"),
                "buttons": payload.get("buttons", []),
                "meta": payload.get("meta", {})
            }
        }, ensure_ascii=False))
        
    elif action_type == 'run':
        command = parts[3] if len(parts) > 3 else ''
        arg = parts[4] if len(parts) > 4 else ''
        
        out = ""
        if command == 'list':
            out = _run_script(["/opt/data/skills/cc/scripts/congvan_status.py", "list", "--status", "new"])
        elif command == 'list_today':
            # Lọc theo hôm nay
            raw_out = _run_script(["/opt/data/skills/cc/scripts/congvan_status.py", "list"])
            # Thêm logic lọc nếu cần, tạm thời trả về output gốc
            out = raw_out
        elif command == 'end_all':
            out = "Đã yêu cầu kết thúc toàn bộ (Tính năng cần xác nhận, vui lòng gõ /cc end all)"
        elif command == 'help':
            out = "Vui lòng gõ lệnh /cc help để xem hướng dẫn chi tiết."
        elif command == 'tai':
            out = _run_script(["/opt/data/skills/cc/scripts/congchuc_scrape.py", "--download-only", arg])
        elif command == 'tomtat':
            out = _run_script(["/opt/data/skills/cc/scripts/congchuc_summarize.py", "--so-den", arg])
        elif command == 'duthao':
            out = _run_script(["/opt/data/skills/cc/scripts/congchuc_draft.py", "--so-den", arg])
        elif command in ['theodoi', 'watch']:
            import datetime
            watch_dir = os.path.join(os.environ.get("HERMES_HOME", "/opt/data"), "cron", "cong-van-di")
            watch_file = os.path.join(watch_dir, "vbdi_watch.json")
            os.makedirs(watch_dir, exist_ok=True)
            
            # Read existing
            watch_data = {"watching": []}
            if os.path.exists(watch_file):
                try:
                    with open(watch_file, "r", encoding="utf-8") as f:
                        watch_data = json.load(f)
                except: pass
            
            watching = watch_data.get("watching", [])
            # Check duplicate
            exists = any(str(item.get("so")).strip() == arg.strip() for item in watching)
            if exists:
                out = f"⚠️ Số văn bản đi/từ khóa '{arg}' đã nằm trong danh sách theo dõi trước đó."
            else:
                watching.append({
                    "so": arg.strip(),
                    "added_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                watch_data["watching"] = watching
                try:
                    with open(watch_file, "w", encoding="utf-8") as f:
                        json.dump(watch_data, f, indent=2, ensure_ascii=False)
                    out = f"✅ Đã thêm số/từ khóa '{arg}' vào danh sách theo dõi văn bản đi. Hệ thống sẽ báo ngay khi quét thấy."
                except Exception as e:
                    out = f"❌ Lỗi ghi danh sách theo dõi: {str(e)}"
        elif command == 'help_theodoi':
            out = "📝 **Hướng dẫn Theo dõi Văn bản đi**\n\nVui lòng gõ cú pháp lệnh sau trên ô chat:\n👉 `/cc theodoi <số_ký_hiệu_hoặc_từ_khóa>`\n\nVí dụ: `/cc theodoi 188` (hoặc `/cc watch 188`). Hệ thống sẽ tự động giám sát văn bản đi và thông báo ngay khi quét thấy."
        elif command == 'end':
            env = os.environ.copy()
            env["HERMES_HOME"] = "/tmp"
            
            try:
                res = subprocess.run(
                    ["uv", "run", "python", "/opt/data/skills/cc/scripts/congchuc_action.py", "kethuc", arg],
                    capture_output=True, text=True, timeout=45, env=env
                )
                if res.returncode == 0:
                    out = res.stdout.strip()
                    # post run state sync
                    subprocess.run(["uv", "run", "python", "/opt/data/skills/cc/scripts/congvan_status.py", "done", arg], capture_output=True, timeout=10)
                else:
                    out = f"❌ Lỗi ({res.returncode}):\n{res.stderr.strip()}"
            except Exception as e:
                out = f"❌ Lỗi: {str(e)}"
        
        print(json.dumps({
            "status": "ok",
            "command": command,
            "result": {
                "text": out if out else "Hoàn thành.",
                "buttons": [] # No buttons means we just display text
            }
        }, ensure_ascii=False))

if __name__ == '__main__':
    main()
