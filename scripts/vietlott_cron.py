#!/opt/hermes/.venv/bin/python3
"""vietlott_cron.py - Cron job tự động cập nhật và xuất báo cáo Vietlott Mega 6/45.
Chạy lúc 18:45 VN Thứ 4, Thứ 6, Chủ nhật (sau giờ quay 18:05-18:25).
Dùng cho Hermes Cron (no_agent=True), stdout được gửi trực tiếp về Zalo.
"""
import sys
import subprocess
from pathlib import Path

# Đảm bảo UTF-8 cho stdout
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

VENV_PYTHON = "/opt/hermes/.venv/bin/python3"
SCRIPT_DIR = Path("/opt/data/skills/vietlott/scripts")
VL_FETCH = SCRIPT_DIR / "vl_fetch.py"
VL_REPORT = SCRIPT_DIR / "vl_report.py"

def main():
    # 1. Chạy cập nhật kết quả mới nhất vào draws.csv
    try:
        subprocess.run(
            [VENV_PYTHON, str(VL_FETCH), "--update"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60
        )
    except Exception as e:
        print(f"⚠️ Cảnh báo lỗi cập nhật crawler: {e}", file=sys.stderr)

    # 2. Tạo báo cáo chuẩn 5 mục và in ra stdout (sẽ được gửi tới Zalo)
    try:
        res = subprocess.run(
            [VENV_PYTHON, str(VL_REPORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=30
        )
        if res.stdout:
            print(res.stdout.strip())
        else:
            print("⚠️ Báo cáo không có nội dung.", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ Lỗi sinh báo cáo Vietlott: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
