"""
Giai đoạn 1 — Login thủ công để tạo persistent browser profile.

Chạy script này khi:
  - Lần đầu setup.
  - Hoặc khi session server-side đã hết hạn hẳn (msc_get_tokens.py báo lỗi 401/403
    liên tục dù profile vẫn còn cookie).

Chạy bằng: uv run python msc_login_setup.py

Sau khi chạy xong, thư mục PROFILE_DIR sẽ chứa cookies/localStorage đã đăng nhập,
để msc_get_tokens.py tái sử dụng ở chế độ headless.
"""

import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright

# Force stdout/stderr to use UTF-8 encoding on Windows to prevent UnicodeEncodeError
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

PROFILE_DIR = Path.home() / ".hermes" / "msc_profile"
LOGIN_URL = "https://muasamcong.mpi.gov.vn"


def main() -> int:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # launch_persistent_context tự lưu cookies/localStorage vào PROFILE_DIR
        # liên tục trong suốt phiên làm việc, không cần gọi storage_state() riêng.
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,  # headful để bạn tự nhập tài khoản/OTP
            channel="chrome",  # Sử dụng trình duyệt Chrome thật của hệ điều hành
            ignore_default_args=["--enable-automation"],  # Bỏ cờ automation để tránh bị reCAPTCHA chặn
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.goto(LOGIN_URL)

        print(f"Profile dir: {PROFILE_DIR}")
        print("Đăng nhập thủ công vào Mua Sắm Công trong cửa sổ Chromium vừa mở.")
        print("Sau khi đăng nhập THÀNH CÔNG (thấy trang dashboard/portal sau login),")
        input("nhấn Enter tại đây để lưu profile và đóng trình duyệt... ")

        # Chốt lại: kiểm tra nhanh có cookie phiên hay chưa trước khi đóng
        cookies = context.cookies()
        session_cookie_names = [c["name"] for c in cookies]
        print(f"Đã lưu {len(cookies)} cookie(s): {session_cookie_names}")

        context.close()

    print("✅ Xong. Profile đã sẵn sàng cho msc_get_tokens.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
