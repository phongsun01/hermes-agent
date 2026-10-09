#!/usr/bin/env python3
"""vl_fetch.py — Lấy kết quả Vietlott Mega 6/45 từ minhngoc.net.vn.

Lệnh:
  python vl_fetch.py                        # kỳ hôm nay / kỳ gần nhất
  python vl_fetch.py --date 07-10-2026      # kỳ theo ngày DD-MM-YYYY
  python vl_fetch.py --range 30             # 30 kỳ gần nhất (crawl tuần tự)
  python vl_fetch.py --range 30 --csv       # ghi ra file draws.csv

Output: CSV (ngay,n1,n2,n3,n4,n5,n6,ky) — dùng trực tiếp với vietlott645.py
Không cần thư viện ngoài. Chỉ dùng stdlib: urllib, re, datetime, time.
"""
import argparse
import csv
import re
import sys
import time
import urllib.request
from datetime import date, timedelta

BASE_URL = "https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Referer": "https://www.minhngoc.net.vn/",
    "Accept-Language": "vi-VN,vi;q=0.9",
}

# Mega 6/45 quay vào Thứ 4 (Wed=2), Thứ 6 (Fri=4), Chủ nhật (Sun=6)
DRAW_WEEKDAYS = {2, 4, 6}


def _fetch_html(url: str, retries: int = 2) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
                # minhngoc dùng windows-1252 hoặc utf-8, thử cả hai
                for enc in ("utf-8", "windows-1252", "latin-1"):
                    try:
                        return raw.decode(enc)
                    except UnicodeDecodeError:
                        continue
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(1.5)
    return ""


def _parse_draw(html: str, draw_date: str) -> dict | None:
    """Parse 6 số và số kỳ từ HTML trang kết quả theo ngày."""
    # 6 số chính: <div class="finnishN bool">DD</div>
    nums = re.findall(r'class="finnish\d\s+bool"[^>]*>(\d+)<', html)
    if len(nums) < 6:
        return None
    # Số kỳ: <span id="DT6X45_KY_VE">#01572</span>
    ky_match = re.search(r'id="DT6X45_KY_VE">#?(\d+)', html)
    ky = int(ky_match.group(1)) if ky_match else 0
    return {"ngay": draw_date, "nums": sorted(int(n) for n in nums[:6]), "ky": ky}


def fetch_date(d: date) -> dict | None:
    url = f"{BASE_URL}/{d.strftime('%d-%m-%Y')}.html"
    try:
        html = _fetch_html(url)
        return _parse_draw(html, d.strftime("%d/%m/%Y"))
    except Exception as e:
        print(f"[WARN] {d} — {e}", file=sys.stderr)
        return None


def draw_dates_before(start: date, count: int) -> list[date]:
    """Tạo danh sách ngày quay thưởng gần nhất (từ start về trước)."""
    result = []
    d = start
    while len(result) < count:
        if d.weekday() in DRAW_WEEKDAYS:
            result.append(d)
        d -= timedelta(days=1)
    return result


def write_csv(draws: list[dict], out=None):
    w = csv.writer(out or sys.stdout)
    w.writerow(["ngay"] + [f"n{i}" for i in range(1, 7)] + ["ky"])
    for draw in draws:
        w.writerow([draw["ngay"]] + draw["nums"] + [draw["ky"]])


def cmd_single(d: date):
    result = fetch_date(d)
    if result:
        write_csv([result])
    else:
        print(f"Không tìm thấy kết quả cho {d.strftime('%d/%m/%Y')}", file=sys.stderr)
        sys.exit(1)


def cmd_range(n: int, to_csv: bool):
    today = date.today()
    dates = draw_dates_before(today, n)
    draws = []
    for i, d in enumerate(dates):
        result = fetch_date(d)
        if result:
            draws.append(result)
            print(f"[{i+1}/{n}] {result['ngay']} kỳ #{result['ky']:05d}: {result['nums']}", file=sys.stderr)
        else:
            print(f"[{i+1}/{n}] {d} — không có dữ liệu", file=sys.stderr)
        if i < len(dates) - 1:
            time.sleep(0.5)  # lịch sự với server

    # Sắp xếp cũ → mới (theo số kỳ tăng dần)
    draws.sort(key=lambda r: r["ky"] or 0)

    if to_csv:
        with open("draws.csv", "w", newline="", encoding="utf-8") as f:
            write_csv(draws, f)
        print(f"Đã ghi {len(draws)} kỳ vào draws.csv", file=sys.stderr)
    else:
        write_csv(draws)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch Vietlott Mega 6/45 từ minhngoc.net.vn")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--date", metavar="DD-MM-YYYY", help="Lấy kết quả ngày cụ thể")
    group.add_argument("--range", type=int, metavar="N", dest="n_draws",
                       help="Crawl N kỳ gần nhất (mặc định 30)")
    ap.add_argument("--csv", action="store_true", help="Ghi ra file draws.csv thay vì stdout")
    args = ap.parse_args()

    if args.date:
        try:
            d = date(*reversed([int(x) for x in args.date.split("-")]))  # DD-MM-YYYY
        except ValueError:
            print("Định dạng ngày không hợp lệ. Dùng DD-MM-YYYY", file=sys.stderr)
            sys.exit(1)
        cmd_single(d)
    else:
        n = args.n_draws or 30
        cmd_range(n, args.csv)
