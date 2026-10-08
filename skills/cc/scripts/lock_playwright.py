#!/usr/bin/env python3
import os
import sys
import time
import fcntl
import contextlib

# Đường dẫn lock cố định: ưu tiên thư mục state thực tế (/opt/data/cron/cong-van-den),
# nếu không có thì fallback về ~/.hermes hoặc /tmp.
# KHÔNG phụ thuộc vào việc người dùng hay script truyền HERMES_HOME=/tmp để tránh phân mảnh file lock.
_default_cron_dir = "/opt/data/cron/cong-van-den"
if os.path.exists(_default_cron_dir) and os.access(_default_cron_dir, os.W_OK):
    PLAYWRIGHT_LOCK_FILE = os.path.join(_default_cron_dir, ".playwright.lock")
else:
    _hermes_home = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))
    _cron_dir = os.path.join(_hermes_home, 'cron', 'cong-van-den')
    if os.path.exists(_cron_dir) or os.path.exists(_hermes_home):
        PLAYWRIGHT_LOCK_FILE = os.path.join(_cron_dir, '.playwright.lock')
    else:
        PLAYWRIGHT_LOCK_FILE = "/tmp/cc-playwright.lock"

@contextlib.contextmanager
def lock_playwright_session(timeout=60, poll_interval=1):
    os.makedirs(os.path.dirname(PLAYWRIGHT_LOCK_FILE), exist_ok=True)
    lock_file = open(PLAYWRIGHT_LOCK_FILE, 'w')
    start = time.time()
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (BlockingIOError, OSError):
                if time.time() - start > timeout:
                    raise TimeoutError(
                        f'Cong cong chuc dang ban xu ly tac vu khac (cho qua {timeout}s). Vui long thu lai sau.'
                    )
                time.sleep(poll_interval)
        yield
    finally:
        if acquired:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        lock_file.close()

@contextlib.contextmanager
def launch_browser_locked(playwright, headless=True, args=None, timeout=60):
    if args is None:
        args = ['--no-sandbox']
    with lock_playwright_session(timeout=timeout):
        browser = playwright.chromium.launch(headless=headless, args=args)
        try:
            yield browser
        finally:
            try:
                browser.close()
            except Exception:
                pass