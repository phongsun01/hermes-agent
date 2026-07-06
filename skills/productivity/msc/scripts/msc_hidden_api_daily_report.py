#!/usr/bin/env python3
import argparse
import json
import subprocess

SCRIPT = 'scripts/msc_hidden_api_counts.py'


def run_one(token: str, noti: str, date: str, cookie: str = '') -> int:
    cmd = ['python3', SCRIPT, '--token', token, '--noti', noti, '--date', date]
    if cookie:
        cmd += ['--cookie', cookie]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or f'cmd failed {p.returncode}')
    data = json.loads(p.stdout.strip())
    return int(data['total'])


def main():
    ap = argparse.ArgumentParser(description='MSC hidden API daily KHLCNT/TBMT report')
    ap.add_argument('--token', required=True)
    ap.add_argument('--cookie', default='')
    args = ap.parse_args()

    kh_y = run_one(args.token, 'khlcnt', 'yesterday', args.cookie)
    kh_t = run_one(args.token, 'khlcnt', 'today', args.cookie)
    tb_y = run_one(args.token, 'tbmt', 'yesterday', args.cookie)
    tb_t = run_one(args.token, 'tbmt', 'today', args.cookie)

    print(f'1.1 KHLCNT hôm trước: {kh_y}')
    print(f'1.2 KHLCNT hôm nay: {kh_t}')
    print(f'1.3 Chênh lệch KHLCNT: {kh_t-kh_y:+d}')
    print(f'2.1 TBMT hôm trước: {tb_y}')
    print(f'2.2 TBMT hôm nay: {tb_t}')
    print(f'2.3 Chênh lệch TBMT: {tb_t-tb_y:+d}')


if __name__ == '__main__':
    main()
