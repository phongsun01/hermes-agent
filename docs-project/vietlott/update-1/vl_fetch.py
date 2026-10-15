#!/usr/bin/env python3
"""vl_fetch.py - Lấy kết quả + bảng giải Vietlott Mega 6/45 từ minhngoc.net.vn (chỉ dùng stdlib).

Lệnh:
  python vl_fetch.py                      # kỳ gần nhất (in ra màn hình)
  python vl_fetch.py --date 07-10-2026    # 1 ngày DD-MM-YYYY (thêm --save để gộp vào file)
  python vl_fetch.py --dump 07-10-2026    # lưu HTML thô ra minhngoc_07-10-2026.html để debug parser
  python vl_fetch.py --backfill 400       # lấy thêm 400 kỳ gần nhất chưa có, gộp vào draws.csv
  python vl_fetch.py --update             # chỉ lấy các kỳ MỚI sau kỳ cuối trong draws.csv
  python vl_fetch.py --enrich             # bổ sung jackpot + số giải cho các kỳ đã có nhưng thiếu
  python vl_fetch.py --check              # kiểm tra draws.csv: trùng/thiếu kỳ, ngày, bảng giải bất thường
  Tùy chọn: --out draws.csv (mặc định), --delay 0.5

draws.csv: ngay,n1..n6,ky,jackpot,w_jackpot,w_nhat,w_nhi,w_ba   (cũ -> mới)
  jackpot  = giá trị jackpot (đồng) hiển thị trên trang kỳ đó
  w_*      = số giải trúng của Jackpot / Nhất / Nhì / Ba
File cũ (8 cột) vẫn đọc được; luôn GỘP và loại trùng theo số kỳ, không bao giờ ghi đè mất lịch sử.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser

BASE_URL = "https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Referer": "https://www.minhngoc.net.vn/",
    "Accept-Language": "vi-VN,vi;q=0.9",
}
DRAW_WEEKDAYS = {2, 4, 6}            # Thứ 4, Thứ 6, Chủ nhật
VN_TZ = timezone(timedelta(hours=7))
CUTOFF = (18, 45)                    # quay ~18:00, kết quả lên web sau ~18:30
MAX_CONSEC_MISS = 12                 # ~4 tuần liền không có dữ liệu => dừng
PRIZE_KEYS = ("jackpot", "wj", "w1", "w2", "w3")
HEADER = (["ngay"] + [f"n{i}" for i in range(1, 7)] + ["ky"]
          + ["jackpot", "w_jackpot", "w_nhat", "w_nhi", "w_ba"])
FIXED = {"w1": 10_000_000, "w2": 300_000, "w3": 30_000}  # mức giải Nhất/Nhì/Ba - dùng làm mốc định vị
RATIO_OK = (8, 30)                   # w_ba / w_nhi kỳ vọng ~16,4; ngoài khoảng này nghi đọc sai bảng

RE_NUMS = re.compile(r'class="finnish\d\s+bool"[^>]*>\s*(\d+)\s*<')
RE_KY = re.compile(r'id="DT6X45_KY_VE"[^>]*>\s*#?(\d+)')
RE_NUMTOK = re.compile(r"^\d[\d.,\s]*(d|dong|vnd)?$")

_prize_fail = 0


# ---------- mạng ----------
def fetch_html(url: str, retries: int = 2) -> str | None:
    """Trả về HTML, hoặc None nếu 404 (ngày không quay). Lỗi mạng khác -> raise sau khi retry."""
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("cp1252", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == retries:
                raise
        time.sleep(1.5 * (attempt + 1))
    return None


# ---------- parse bảng giải ----------
class _Tokens(HTMLParser):
    """Gom các đoạn text (bỏ script/style) theo thứ tự xuất hiện."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            s = " ".join(data.split())
            if s:
                self.out.append(s)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _digits(tok: str) -> int:
    return int(re.sub(r"\D", "", tok))


def _prize_from_tokens(toks: list[str]) -> dict | None:
    """Định vị theo NHÃN (Jackpot / Giải nhất / nhì / ba), không phụ thuộc class CSS.
    Với Nhất/Nhì/Ba: neo vào mức giải cố định, số giải là số ngay trước nó.
    Với Jackpot: hai số cuối giữa nhãn Jackpot và nhãn Giải nhất = (số giải, giá trị)."""
    f = [_fold(t) for t in toks]

    def find(label, start=0):
        for i in range(start, len(f)):
            if len(f[i]) <= 30 and f[i].startswith(label):
                return i
        return -1

    i1 = find("giai nhat")
    if i1 < 0:
        return None
    ij = max((i for i in range(i1) if f[i].startswith("jackpot") and len(f[i]) <= 30), default=-1)
    i2 = find("giai nhi", i1 + 1)
    i3 = find("giai ba", i2 + 1) if i2 >= 0 else -1
    if ij < 0 or i2 < 0 or i3 < 0:
        return None

    def nums(a, b):
        return [_digits(t) for t, ft in zip(toks[a:b], f[a:b]) if RE_NUMTOK.match(ft)]

    jn = nums(ij + 1, i1)
    if len(jn) < 2:
        return None
    wj, jackpot = jn[-2], jn[-1]
    if wj > jackpot:                 # phòng trường hợp cột bị đảo thứ tự
        wj, jackpot = jackpot, wj
    if jackpot < 1_000_000_000 or wj > 1000:  # số người trúng jackpot không thể lớn thế -> nghi đọc nhầm cột
        return None
    out = {"jackpot": jackpot, "wj": wj}
    for key, a, b in (("w1", i1 + 1, i2), ("w2", i2 + 1, i3), ("w3", i3 + 1, i3 + 9)):
        n = nums(a, b)
        v = FIXED[key]
        if v not in n or n.index(v) == 0:
            return None
        out[key] = n[n.index(v) - 1]
    return out


def parse_prizes(html: str) -> dict | None:
    """None nếu không đọc được bảng giải (không raise). Thử từ chỗ có id kỳ vé, rồi toàn trang."""
    pos = html.find("DT6X45_KY_VE")
    chunks = (html[pos:], html) if pos >= 0 else (html,)
    for chunk in chunks:
        try:
            p = _Tokens()
            p.feed(chunk)
            r = _prize_from_tokens(p.out)
        except Exception:
            r = None
        if r:
            return r
    return None


# ---------- parse + kiểm tra ----------
def parse_draw(html: str, d: date) -> dict | None:
    """None nếu trang chưa có kết quả. ValueError nếu dữ liệu có nhưng không hợp lệ."""
    global _prize_fail
    nums = [int(x) for x in RE_NUMS.findall(html)][:6]
    ky_m = RE_KY.search(html)
    if len(nums) < 6 or not ky_m:
        return None
    if len(set(nums)) != 6 or not all(1 <= n <= 45 for n in nums):
        raise ValueError(f"bộ số không hợp lệ {nums}")
    row = {"ngay": d.strftime("%d/%m/%Y"), "nums": sorted(nums), "ky": int(ky_m.group(1))}
    prizes = parse_prizes(html)
    if prizes is None:
        _prize_fail += 1
        if _prize_fail <= 3:
            print(f"[CẢNH BÁO] {row['ngay']}: không đọc được bảng giải "
                  f"(dùng --dump {d.strftime('%d-%m-%Y')} rồi gửi file HTML để chỉnh parser)", file=sys.stderr)
    row.update(prizes or {k: None for k in PRIZE_KEYS})
    return row


def fetch_date(d: date) -> dict | None:
    html = fetch_html(f"{BASE_URL}/{d.strftime('%d-%m-%Y')}.html")
    return parse_draw(html, d) if html else None


# ---------- lịch quay ----------
def now_vn() -> datetime:
    return datetime.now(VN_TZ)


def latest_draw_day(now: datetime) -> date:
    """Ngày quay gần nhất ĐÃ có kết quả (hôm nay chỉ tính sau giờ CUTOFF)."""
    d = now.date()
    if not (d.weekday() in DRAW_WEEKDAYS and (now.hour, now.minute) >= CUTOFF):
        d -= timedelta(days=1)
    while d.weekday() not in DRAW_WEEKDAYS:
        d -= timedelta(days=1)
    return d


def draw_days_desc(start: date, max_days: int):
    d = start
    for _ in range(max_days):
        if d.weekday() in DRAW_WEEKDAYS:
            yield d
        d -= timedelta(days=1)


# ---------- CSV (gộp, loại trùng, ghi nguyên tử) ----------
def _opt_int(r: list[str], i: int):
    try:
        return int(r[i])
    except (ValueError, IndexError):
        return None


def read_rows(path: str) -> dict[int, dict]:
    rows: dict[int, dict] = {}
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.reader(f):
            try:
                nums = [int(x) for x in r[1:7]]
                ky = int(r[7])
            except (ValueError, IndexError):
                continue  # header / dòng hỏng
            row = {"ngay": r[0], "nums": sorted(nums), "ky": ky}
            for j, k in enumerate(PRIZE_KEYS):
                row[k] = _opt_int(r, 8 + j)
            rows[ky] = row
    return rows


def write_rows(path: str, rows: dict[int, dict]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        for ky in sorted(rows):
            r = rows[ky]
            w.writerow([r["ngay"]] + r["nums"] + [ky]
                       + ["" if r.get(k) is None else r[k] for k in PRIZE_KEYS])
    os.replace(tmp, path)


def _ratio_bad(r: dict) -> bool:
    w2, w3 = r.get("w2"), r.get("w3")
    return bool(w2 and w3 is not None and w2 >= 100 and not RATIO_OK[0] <= w3 / w2 <= RATIO_OK[1])


def problems(rows: dict[int, dict]) -> list[str]:
    out = []
    kys = sorted(rows)
    if not kys:
        return ["file rỗng"]
    missing = sorted(set(range(kys[0], kys[-1] + 1)) - set(kys))
    if missing:
        out.append(f"thiếu {len(missing)} kỳ: {missing[:15]}{' ...' if len(missing) > 15 else ''}")
    prev = None
    for ky in kys:
        d = datetime.strptime(rows[ky]["ngay"], "%d/%m/%Y").date()
        if prev and d <= prev:
            out.append(f"kỳ {ky}: ngày {rows[ky]['ngay']} không tăng so với kỳ trước (nghi trang trả lại kết quả cũ)")
        prev = d
    nop = [ky for ky in kys if rows[ky].get("jackpot") is None]
    if nop:
        out.append(f"{len(nop)} kỳ chưa có jackpot/số giải (chạy --enrich): {nop[:8]}{' ...' if len(nop) > 8 else ''}")
    bad = [ky for ky in kys if _ratio_bad(rows[ky])]
    if bad:
        out.append(f"{len(bad)} kỳ có tỷ lệ giải Ba/Nhì ngoài {RATIO_OK} (nghi đọc sai bảng giải): {bad[:8]}")
    return out


# ---------- crawl ----------
def crawl(days, rows: dict[int, dict], out: str, want: int | None, delay: float) -> int:
    have_dates = {r["ngay"] for r in rows.values()}
    new = miss = 0
    try:
        for d in days:
            if want is not None and new >= want:
                break
            label = d.strftime("%d/%m/%Y")
            if label in have_dates:
                continue
            try:
                r = fetch_date(d)
            except (ValueError, OSError) as e:
                print(f"[LỖI] {label}: {e}", file=sys.stderr)
                r = None
            time.sleep(delay)
            if r is None:
                miss += 1
                print(f"[--] {label} không có kết quả", file=sys.stderr)
                if miss >= MAX_CONSEC_MISS:
                    print("Dừng: nhiều ngày liên tiếp không có dữ liệu.", file=sys.stderr)
                    break
                continue
            miss = 0
            if r["ky"] in rows:  # trang trả lại kỳ đã có (thường là redirect về kết quả mới nhất)
                print(f"[!!] {label}: kỳ #{r['ky']} đã có, bỏ qua", file=sys.stderr)
                continue
            rows[r["ky"]] = r
            new += 1
            jp = f" jackpot {r['jackpot']:,}".replace(",", ".") if r.get("jackpot") else ""
            print(f"[{new}] {label} kỳ #{r['ky']:05d}: {r['nums']}{jp}", file=sys.stderr)
            if new % 50 == 0:
                write_rows(out, rows)  # lưu định kỳ, Ctrl-C không mất dữ liệu
    finally:
        if new:
            write_rows(out, rows)
    return new


def enrich(rows: dict[int, dict], out: str, delay: float) -> int:
    """Tải lại các kỳ thiếu jackpot/số giải và điền vào (không đổi số quay)."""
    todo = sorted((r for r in rows.values() if r.get("jackpot") is None), key=lambda r: -r["ky"])
    done = 0
    try:
        for i, r in enumerate(todo, 1):
            d = datetime.strptime(r["ngay"], "%d/%m/%Y").date()
            try:
                new = fetch_date(d)
            except (ValueError, OSError) as e:
                print(f"[LỖI] {r['ngay']}: {e}", file=sys.stderr)
                continue
            time.sleep(delay)
            if not new or new["ky"] != r["ky"] or new["nums"] != r["nums"]:
                print(f"[!!] {r['ngay']}: trang không khớp kỳ #{r['ky']}, bỏ qua", file=sys.stderr)
                continue
            if new.get("jackpot") is None:
                continue
            r.update({k: new[k] for k in PRIZE_KEYS})
            done += 1
            print(f"[{i}/{len(todo)}] kỳ #{r['ky']:05d} bổ sung bảng giải", file=sys.stderr)
            if done % 50 == 0:
                write_rows(out, rows)
    finally:
        if done:
            write_rows(out, rows)
    return done


def report(rows: dict[int, dict]) -> None:
    ps = problems(rows)
    print(f"Tổng {len(rows)} kỳ. " + ("Dữ liệu nhất quán." if not ps else "CẢNH BÁO:"), file=sys.stderr)
    for p in ps:
        print(" -", p, file=sys.stderr)


# ---------- lệnh ----------
def parse_date_arg(s: str) -> date:
    try:
        dd, mm, yy = (int(x) for x in s.split("-"))
        return date(yy, mm, dd)
    except ValueError:
        sys.exit("Định dạng ngày không hợp lệ. Dùng DD-MM-YYYY")


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")  # tránh vỡ tiếng Việt trên Windows
    ap = argparse.ArgumentParser(description="Fetch Vietlott Mega 6/45 từ minhngoc.net.vn")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--date", metavar="DD-MM-YYYY")
    g.add_argument("--dump", metavar="DD-MM-YYYY", help="lưu HTML thô để debug parser")
    g.add_argument("--backfill", "--range", type=int, metavar="N", dest="backfill",
                   help="lấy thêm N kỳ gần nhất chưa có (--range là tên cũ)")
    g.add_argument("--update", action="store_true", help="lấy các kỳ mới sau kỳ cuối trong file")
    g.add_argument("--enrich", action="store_true", help="bổ sung jackpot/số giải cho kỳ đã có nhưng thiếu")
    g.add_argument("--check", action="store_true", help="kiểm tra tính nhất quán của file")
    ap.add_argument("--out", default="draws.csv")
    ap.add_argument("--save", action="store_true", help="với --date: gộp kết quả vào --out")
    ap.add_argument("--delay", type=float, default=0.5)
    a = ap.parse_args()

    if a.check:
        report(read_rows(a.out))
        return

    if a.dump:
        d = parse_date_arg(a.dump)
        try:
            html = fetch_html(f"{BASE_URL}/{d.strftime('%d-%m-%Y')}.html")
        except OSError as e:
            sys.exit(f"Không lấy được dữ liệu: {e}")
        if not html:
            sys.exit("Trang không tồn tại (404).")
        fn = f"minhngoc_{d.strftime('%d-%m-%Y')}.html"
        with open(fn, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Đã lưu {fn} ({len(html):,} ký tự). Parse thử: {parse_draw(html, d)}", file=sys.stderr)
        return

    if a.enrich:
        rows = read_rows(a.out)
        if not rows:
            sys.exit(f"{a.out} chưa có dữ liệu.")
        n = enrich(rows, a.out, a.delay)
        print(f"Đã bổ sung {n} kỳ.", file=sys.stderr)
        report(rows)
        return

    if a.update:
        rows = read_rows(a.out)
        if not rows:
            sys.exit(f"{a.out} chưa có dữ liệu. Chạy --backfill N trước (khuyến nghị N >= 300).")
        last = datetime.strptime(rows[max(rows)]["ngay"], "%d/%m/%Y").date()
        end = latest_draw_day(now_vn())
        days = [last + timedelta(days=i) for i in range(1, (end - last).days + 1)
                if (last + timedelta(days=i)).weekday() in DRAW_WEEKDAYS]
        n = crawl(days, rows, a.out, None, a.delay)
        print(f"Đã thêm {n} kỳ mới.", file=sys.stderr)
        report(rows)
        return

    if a.backfill:
        rows = read_rows(a.out)
        start = latest_draw_day(now_vn())
        n = crawl(draw_days_desc(start, a.backfill * 3 + 60), rows, a.out, a.backfill, a.delay)
        print(f"Đã thêm {n} kỳ.", file=sys.stderr)
        report(rows)
        return

    # --date hoặc mặc định: in ra màn hình
    try:
        if a.date:
            r = fetch_date(parse_date_arg(a.date))
        else:
            r = None
            for d in draw_days_desc(latest_draw_day(now_vn()), 10):
                r = fetch_date(d)
                if r:
                    break
    except (OSError, ValueError) as e:
        sys.exit(f"Không lấy được dữ liệu: {e}")
    if not r:
        sys.exit("Không tìm thấy kết quả.")
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(HEADER)
    w.writerow([r["ngay"]] + r["nums"] + [r["ky"]] + ["" if r.get(k) is None else r[k] for k in PRIZE_KEYS])
    if a.save:
        rows = read_rows(a.out)
        rows[r["ky"]] = r
        write_rows(a.out, rows)


if __name__ == "__main__":
    main()
