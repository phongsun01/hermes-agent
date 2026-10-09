#!/usr/bin/env python3
"""vl_fetch.py — Lấy và đồng bộ kết quả Vietlott Mega 6/45 từ minhngoc.net.vn.

Lệnh:
  python vl_fetch.py                        # kỳ mới nhất (tự xét trước/sau 18:30)
  python vl_fetch.py --date DD-MM-YYYY      # kỳ theo ngày cụ thể
  python vl_fetch.py --range N              # crawl đủ N kỳ lịch sử
  python vl_fetch.py --update               # chỉ lấy các kỳ mới cập nhật nối vào cache
  python vl_fetch.py --backfill             # backfill toàn bộ lịch sử từ kỳ 1 đến nay
  python vl_fetch.py --out FILE             # chỉ định file CSV đầu ra (tránh lỗi font trên Windows)

Output: CSV (ngay,n1,n2,n3,n4,n5,n6,ky) theo thứ tự thời gian tăng dần (cũ -> mới).
Không cần thư viện bên ngoài. Chỉ dùng stdlib.
"""
import argparse
import csv
import io
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

# Đảm bảo stdout luôn dùng UTF-8 trên mọi nền tảng (đặc biệt là Windows PowerShell / CMD)
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

BASE_URL = "https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.minhngoc.net.vn/",
    "Accept-Language": "vi-VN,vi;q=0.9",
}

# Mega 6/45 quay vào Thứ 4 (Wed=2), Thứ 6 (Fri=4), Chủ nhật (Sun=6)
DRAW_WEEKDAYS = {2, 4, 6}

# Thư mục chứa script và vị trí mặc định của draws.csv
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = SCRIPT_DIR / "draws.csv"


def _fetch_html(url: str, retries: int = 2) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read()
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


def _parse_draw(html: str, target_date_str: str) -> dict | None:
    """Parse và validate dữ liệu một kỳ quay từ HTML.
    
    Quy tắc kiểm tra dữ liệu:
    1. Phải đủ 6 số.
    2. Mỗi số nằm trong khoảng 1–45.
    3. 6 số không được trùng nhau.
    4. Số kỳ phải là số nguyên dương hợp lệ.
    """
    nums_raw = re.findall(r'class="finnish\d\s+bool"[^>]*>(\d+)<', html)
    if len(nums_raw) < 6:
        return None
    
    try:
        nums = [int(n) for n in nums_raw[:6]]
    except ValueError:
        return None

    # Kiểm tra tính toàn vẹn: 6 số phân biệt từ 1..45
    if len(set(nums)) != 6 or any(n < 1 or n > 45 for n in nums):
        return None

    # Số kỳ: <span id="DT6X45_KY_VE">#01572</span>
    ky_match = re.search(r'id="DT6X45_KY_VE">#?(\d+)', html)
    if not ky_match:
        return None
    ky = int(ky_match.group(1))
    if ky <= 0:
        return None

    return {
        "ngay": target_date_str,
        "nums": sorted(nums),
        "ky": ky
    }


def fetch_date(d: date) -> dict | None:
    """Fetch kết quả của một ngày nhất định."""
    d_str = d.strftime("%d-%m-%Y")
    url = f"{BASE_URL}/{d_str}.html"
    try:
        html = _fetch_html(url)
        return _parse_draw(html, d.strftime("%d/%m/%Y"))
    except Exception as e:
        print(f"[WARN] {d_str} — {e}", file=sys.stderr)
        return None


def get_latest_draw_date(now: datetime | None = None) -> date:
    """Tính ngày quay gần nhất dựa trên lịch và giờ quay.
    
    Mega 6/45 quay Thứ 4, Thứ 6, Chủ nhật lúc 18:05.
    Nếu gọi trước 18:30 của ngày quay thì lấy kỳ trước đó để tránh đọc dữ liệu cũ/chưa cập nhật.
    """
    if now is None:
        now = datetime.now()
    
    cur_date = now.date()
    
    # Nếu hôm nay là ngày quay nhưng chưa đến 18:30 -> lùi lại 1 ngày rồi tìm kỳ quay trước
    if cur_date.weekday() in DRAW_WEEKDAYS:
        if now.hour < 18 or (now.hour == 18 and now.minute < 30):
            cur_date -= timedelta(days=1)
    else:
        # Hôm nay không phải ngày quay
        cur_date -= timedelta(days=1)
        
    while cur_date.weekday() not in DRAW_WEEKDAYS:
        cur_date -= timedelta(days=1)
        
    return cur_date


def load_cached_draws(csv_path: Path) -> dict[int, dict]:
    """Đọc cache từ CSV hiện có, trả về dict {ky: {ngay, nums, ky}}."""
    draws = {}
    if not csv_path.exists():
        return draws
    
    try:
        with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 8:
                    continue
                try:
                    ngay = row[0]
                    nums = sorted(int(x) for x in row[1:7])
                    ky = int(row[7])
                    if len(nums) == 6 and all(1 <= n <= 45 for n in nums) and ky > 0:
                        draws[ky] = {"ngay": ngay, "nums": nums, "ky": ky}
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        print(f"[WARN] Lỗi đọc cache {csv_path}: {e}", file=sys.stderr)
        
    return draws


def save_draws_to_csv(draws_dict: dict[int, dict], csv_path: Path):
    """Ghi toàn bộ draws ra file CSV theo thứ tự kỳ tăng dần (cũ -> mới)."""
    sorted_draws = sorted(draws_dict.values(), key=lambda r: r["ky"])
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ngay"] + [f"n{i}" for i in range(1, 7)] + ["ky"])
        for d in sorted_draws:
            w.writerow([d["ngay"]] + d["nums"] + [d["ky"]])


def validate_continuity(draws_dict: dict[int, dict]):
    """Kiểm tra tính liên tục của các số kỳ."""
    if not draws_dict:
        return
    kys = sorted(draws_dict.keys())
    missing = []
    for prev, cur in zip(kys[:-1], kys[1:]):
        if cur != prev + 1:
            missing.extend(range(prev + 1, cur))
    if missing:
        print(f"[CẢNH BÁO] Phát hiện {len(missing)} kỳ bị thiếu trong chuỗi liên tục: {missing[:10]}{'...' if len(missing) > 10 else ''}", file=sys.stderr)
    else:
        print(f"[OK] Dữ liệu liên tục từ kỳ #{kys[0]:05d} đến #{kys[-1]:05d} ({len(kys)} kỳ).", file=sys.stderr)


def cmd_single(d: date):
    res = fetch_date(d)
    if res:
        w = csv.writer(sys.stdout)
        w.writerow(["ngay"] + [f"n{i}" for i in range(1, 7)] + ["ky"])
        w.writerow([res["ngay"]] + res["nums"] + [res["ky"]])
    else:
        print(f"Không tìm thấy kết quả hợp lệ cho ngày {d.strftime('%d/%m/%Y')}", file=sys.stderr)
        sys.exit(1)


def cmd_range(n: int, out_path: Path | None):
    """Crawl lùi theo lịch Thứ 4/6/CN, dừng khi đủ N kỳ thực tế."""
    d = get_latest_draw_date()
    collected = {}
    attempts = 0
    max_attempts = n * 3  # phòng ngừa ngày nghỉ lễ, gián đoạn
    
    print(f"Bắt đầu crawl {n} kỳ từ ngày {d.strftime('%d/%m/%Y')} về trước...", file=sys.stderr)
    
    while len(collected) < n and attempts < max_attempts:
        if d.weekday() in DRAW_WEEKDAYS:
            res = fetch_date(d)
            if res:
                collected[res["ky"]] = res
                print(f"[{len(collected)}/{n}] {res['ngay']} kỳ #{res['ky']:05d}: {res['nums']}", file=sys.stderr)
            time.sleep(0.4)
        d -= timedelta(days=1)
        attempts += 1
        
    validate_continuity(collected)
    target_file = out_path or DEFAULT_CSV_PATH
    save_draws_to_csv(collected, target_file)
    print(f"Đã lưu {len(collected)} kỳ vào: {target_file}", file=sys.stderr)


def cmd_update(csv_path: Path):
    """Chỉ lấy các kỳ mới chưa có trong cache CSV."""
    cached = load_cached_draws(csv_path)
    latest_known_ky = max(cached.keys()) if cached else 0
    print(f"Cache hiện có {len(cached)} kỳ. Kỳ cao nhất: #{latest_known_ky:05d}", file=sys.stderr)
    
    cur_date = get_latest_draw_date()
    new_draws = {}
    
    while True:
        if cur_date.weekday() in DRAW_WEEKDAYS:
            res = fetch_date(cur_date)
            if res:
                if res["ky"] <= latest_known_ky:
                    # Đã chạm tới mốc đã có trong cache
                    break
                new_draws[res["ky"]] = res
                print(f"[MỚI] {res['ngay']} kỳ #{res['ky']:05d}: {res['nums']}", file=sys.stderr)
            time.sleep(0.4)
        cur_date -= timedelta(days=1)
        # Giới hạn an toàn lùi tối đa 30 ngày nếu không khớp
        if (datetime.now().date() - cur_date).days > 45:
            break
            
    if new_draws:
        cached.update(new_draws)
        validate_continuity(cached)
        save_draws_to_csv(cached, csv_path)
        print(f"Đã cập nhật thêm {len(new_draws)} kỳ mới. Tổng cộng: {len(cached)} kỳ.", file=sys.stderr)
    else:
        print("Dữ liệu đã ở trạng thái mới nhất, không có kỳ mới.", file=sys.stderr)


def cmd_backfill(csv_path: Path):
    """Backfill toàn bộ lịch sử Vietlott Mega 6/45 từ trước đến nay."""
    cached = load_cached_draws(csv_path)
    print(f"Bắt đầu backfill... (Hiện có {len(cached)} kỳ trong cache)", file=sys.stderr)
    
    # Ngày bắt đầu của Vietlott Mega 6/45: 20/07/2016 (kỳ 00001)
    start_history = date(2016, 7, 20)
    cur_date = get_latest_draw_date()
    
    added_count = 0
    while cur_date >= start_history:
        if cur_date.weekday() in DRAW_WEEKDAYS:
            res = fetch_date(cur_date)
            if res:
                ky = res["ky"]
                if ky not in cached:
                    cached[ky] = res
                    added_count += 1
                    if added_count % 20 == 0:
                        print(f"Đã cào {added_count} kỳ... Gần nhất: #{ky:05d} ({res['ngay']})", file=sys.stderr)
                        save_draws_to_csv(cached, csv_path)  # Lưu định kỳ
            time.sleep(0.4)  # Lịch sự với server
        cur_date -= timedelta(days=1)
        
    validate_continuity(cached)
    save_draws_to_csv(cached, csv_path)
    print(f"Hoàn thành backfill! Tổng cộng: {len(cached)} kỳ trong {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch và đồng bộ Vietlott Mega 6/45 từ minhngoc.net.vn")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--date", metavar="DD-MM-YYYY", help="Lấy kết quả ngày cụ thể (hoặc hôm nay nếu 18:30+)")
    group.add_argument("--range", type=int, metavar="N", dest="n_draws",
                       help="Crawl đủ N kỳ gần nhất (mặc định 300 nếu không có cache)")
    group.add_argument("--update", action="store_true", help="Chỉ fetch các kỳ mới nối vào cache draws.csv")
    group.add_argument("--backfill", action="store_true", help="Backfill toàn bộ lịch sử từ kỳ 1 đến nay")
    ap.add_argument("--out", type=str, help="Đường dẫn file CSV xuất ra (mặc định draws.csv cạnh script)")
    ap.add_argument("--csv", action="store_true", help="Cờ tương thích (ghi vào draws.csv mặc định)")
    args = ap.parse_args()

    out_file = Path(args.out) if args.out else DEFAULT_CSV_PATH

    if args.date:
        try:
            d = date(*reversed([int(x) for x in args.date.split("-")]))  # DD-MM-YYYY
        except ValueError:
            print("Định dạng ngày không hợp lệ. Dùng DD-MM-YYYY", file=sys.stderr)
            sys.exit(1)
        cmd_single(d)
    elif args.update:
        cmd_update(out_file)
    elif args.backfill:
        cmd_backfill(out_file)
    elif args.n_draws:
        cmd_range(args.n_draws, out_file)
    else:
        # Mặc định gọi không đối số: lấy kỳ mới nhất hợp lệ
        latest_date = get_latest_draw_date()
        cmd_single(latest_date)
