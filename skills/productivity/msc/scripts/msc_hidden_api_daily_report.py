#!/usr/bin/env python3
import argparse
import json
import subprocess

from pathlib import Path
import os

SCRIPT = str(Path(__file__).parent / 'msc_hidden_api_counts.py')


def run_one(token: str, noti: str, date: str, cookie: str = '') -> int:
    if token:
        os.environ["MSC_SESSION_TOKEN"] = token
    if cookie:
        os.environ["MSC_COOKIE"] = cookie
    cmd = ['python3', SCRIPT, '--noti', noti, '--date', date]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or f'cmd failed {p.returncode}')
    data = json.loads(p.stdout.strip())
    return int(data['total'])


def main():
    ap = argparse.ArgumentParser(description='MSC hidden API daily KHLCNT/TBMT report')
    ap.add_argument('--token', default='', help="MSC API bearer token")
    ap.add_argument('--cookie', default='', help="MSC Cookie")
    args = ap.parse_args()

    token = args.token or os.environ.get("MSC_SESSION_TOKEN") or os.environ.get("MSC_BEARER_TOKEN") or ""
    cookie = args.cookie or os.environ.get("MSC_COOKIE") or ""

    # Try loading from .env if still empty (backward compatibility)
    if not token or not cookie:
        paths = [
            Path(__file__).parent / ".env",
            Path(__file__).parent.parent / ".env",
            Path.home() / ".hermes" / ".env",
        ]
        for p in paths:
            if p.exists():
                try:
                    for raw in p.read_text(encoding="utf-8").splitlines():
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        if k == "MSC_SESSION_TOKEN" and not token:
                            token = v.strip().strip('"').strip("'")
                        elif k == "MSC_COOKIE" and not cookie:
                            cookie = v.strip().strip('"').strip("'")
                except Exception:
                    pass

    if not token:
        print(json.dumps({"status": "error", "message": "Missing MSC API token. Configure in env or .env file."}, ensure_ascii=False))
        return

    kh_y = run_one(token, 'khlcnt', 'yesterday', cookie)
    kh_t = run_one(token, 'khlcnt', 'today', cookie)
    tb_y = run_one(token, 'tbmt', 'yesterday', cookie)
    tb_t = run_one(token, 'tbmt', 'today', cookie)

    print(f'1.1 KHLCNT hôm trước: {kh_y}')
    print(f'1.2 KHLCNT hôm nay: {kh_t}')
    print(f'1.3 Chênh lệch KHLCNT: {kh_t-kh_y:+d}')
    print(f'2.1 TBMT hôm trước: {tb_y}')
    print(f'2.2 TBMT hôm nay: {tb_t}')
    print(f'2.3 Chênh lệch TBMT: {tb_t-tb_y:+d}')


if __name__ == '__main__':
    main()
