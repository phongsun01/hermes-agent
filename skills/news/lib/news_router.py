#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Fix Windows console encoding issues when routed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Paths
HERMES_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_NEWS_DIR = HERMES_ROOT / "scripts" / "news"

def run_script(script_name, args=[]):
    script_path = SCRIPTS_NEWS_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    if res.returncode == 0:
        return res.stdout.strip()
    else:
        return f"⚠️ Lỗi thực thi {script_name}: {res.stderr.strip()}"

def main():
    if len(sys.argv) < 2:
        print("Cú pháp: news_router.py <lệnh> [đối số]")
        return
        
    # Get raw command string
    full_arg = " ".join(sys.argv[1:])
    parts = full_arg.split()
    if not parts:
        return
        
    cmd = parts[0].strip().lower()
    args = parts[1:]
    
    # Strip slash commands if parsed as full text
    if cmd.startswith("/news"):
        if len(parts) > 1:
            cmd = parts[1].strip().lower()
            args = parts[2:]
        else:
            cmd = "menu"
            args = []
    elif cmd.startswith("/"):
        cmd = cmd[1:]
        
    if cmd == "vang":
        print(run_script("gia_hang_hoa_sang.py", ["--section", "vang"]))
    elif cmd == "xang":
        print(run_script("gia_hang_hoa_sang.py", ["--section", "xang"]))
    elif cmd == "tygia":
        print(run_script("gia_hang_hoa_sang.py", ["--section", "tygia"]))
    elif cmd == "thoitiet":
        loc = " ".join(args) if args else "Quảng Ninh"
        print(run_script("weather_quangninh.py", ["--location", loc, "--mode", "weather"]))
    elif cmd == "trieucuong":
        loc = " ".join(args) if args else "Quảng Ninh"
        print(run_script("weather_quangninh.py", ["--location", loc, "--mode", "tide"]))
    elif cmd == "amlich":
        date_str = args[0] if args else ""
        if not date_str:
            from datetime import datetime
            date_str = datetime.now().strftime("%d/%m/%Y")
        print(run_script("lunar_convert.py", ["--solar", date_str]))
    elif cmd == "tintuc":
        topic = " ".join(args) if args else "tin tức thông thường"
        print(run_script("zalo_morning_brief.py", ["--mode", "news", "--topic", topic]))
    elif cmd == "today":
        print(run_script("zalo_morning_brief.py", ["--mode", "today"]))
    elif cmd in ("menu", "newsmenu"):
        # Text fallback of menu
        print("📰 BẢN TIN SÁNG HERMES\n"
              "Các lệnh có sẵn:\n"
              "• `/news vang` - Xem giá vàng\n"
              "• `/news xang` - Xem giá xăng\n"
              "• `/news tygia` - Xem tỷ giá ngoại tệ\n"
              "• `/news thoitiet [location]` - Xem thời tiết\n"
              "• `/news trieucuong [location]` - Xem triều cường\n"
              "• `/news amlich [date]` - Xem âm lịch\n"
              "• `/news tintuc [topic]` - Xem tin tức RSS\n"
              "• `/news today` - Xem ngày này năm xưa")
    else:
        print(f"⚠️ Lệnh phụ '{cmd}' không hợp lệ hoặc chưa được hỗ trợ.")

if __name__ == "__main__":
    main()
