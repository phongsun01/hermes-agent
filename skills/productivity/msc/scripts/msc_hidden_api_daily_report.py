#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import subprocess

SCRIPT = str(Path(__file__).resolve().parent / "msc_hidden_api_counts.py")


def run_one(token: str, noti: str, date: str, cookie: str = '') -> int:
    cmd = ['python3', SCRIPT, '--noti', noti, '--date', date]
    env = os.environ.copy()
    if token:
        env['MSC_SESSION_TOKEN'] = token
        env['MSC_TOKEN'] = token
    if cookie:
        env['MSC_COOKIE'] = cookie
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or f'cmd failed {p.returncode}')
    data = json.loads(p.stdout.strip())
    return int(data['total'])


def main():
    ap = argparse.ArgumentParser(description='MSC hidden API daily KHLCNT/TBMT report')
    ap.add_argument('--token', default='')
    ap.add_argument('--cookie', default='')
    args = ap.parse_args()

    token = args.token or os.environ.get('MSC_SESSION_TOKEN') or os.environ.get('MSC_TOKEN') or ''
    cookie = args.cookie or os.environ.get('MSC_COOKIE') or ''

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
