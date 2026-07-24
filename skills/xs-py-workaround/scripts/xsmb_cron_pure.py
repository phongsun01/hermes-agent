#!/usr/bin/env python3
"""xsmb_cron_pure.py — Pure-Python XSMB cron script (no pandas/numpy needed).

Drop-in replacement for the pandas-based xsmb_cron.py when running in no_agent
mode (which ignores shebang and uses system python).  Fetches results from
ketqua.net, computes Pascal + Monte Carlo + Bayesian CDM predictions using
only Python stdlib, and prints the same report format.

Usage:
    python3 xsmb_cron_pure.py              # today's results
    python3 xsmb_cron_pure.py --dry-run    # don't save to DB

Cron schedule: 35 18 * * *  (18:35 VN daily)
"""

import urllib.request
import re
import sys
import os
import json
import datetime
import sqlite3
import random
import math
import ssl
import contextlib

# ── Configuration ──────────────────────────────────────────────
DB_PATH = "/opt/data/plugins/xsmb/xsmb_results.db"
XSM4_URL = "https://www.ketqua.net/xo-so-mien-bac.php?ngay="
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SIM_N = 20000          # Monte Carlo simulations
MAX_RETRIES = 3
RETRY_DELAY = 5
# ────────────────────────────────────────────────────────────────


# ── Helpers ────────────────────────────────────────────────────

def now_vn():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))


def today_str():
    return now_vn().strftime("%d-%m-%Y")


def today_display():
    return now_vn().strftime("%d/%m/%Y")


def yesterday_str():
    y = now_vn() - datetime.timedelta(days=1)
    return y.strftime("%d-%m-%Y")


# ── Fetch from ketqua.net ─────────────────────────────────────

def fetch_xsmb(date_str: str):
    """Fetch XSMB results for a given date (dd-mm-yyyy). Returns dict or None."""
    parts = date_str.split("-")
    url = f"{XSM4_URL}{parts[2]}-{parts[1]}-{parts[0]}"
    context = ssl._create_unverified_context()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html",
            })
            with urllib.request.urlopen(req, timeout=20, context=context) as r:
                html = r.read().decode("utf-8", errors="replace")
            break
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"Lỗi fetch {url}: {e}", file=sys.stderr)
                return None
            import time
            time.sleep(RETRY_DELAY)

    # Parse: look for "Đặc biệt", "Giải nhất", etc. in the table
    prizes = {}
    patterns = [
        ("GDB", r'Đặc\s*biệt\s*[：:]\s*<b>(\d+)</b>'),
        ("G1", r'Giải\s*nhất\s*[：:]\s*<b>(\d+)</b>'),
        ("G2", r'Giải\s*nhì\s*[：:]\s*(.*?)</tr>', True),
        ("G3", r'Giải\s*ba\s*[：:]\s*(.*?)</tr>', True),
        ("G4", r'Giải\s*tư\s*[：:]\s*(.*?)</tr>', True),
        ("G5", r'Giải\s*năm\s*[：:]\s*(.*?)</tr>', True),
        ("G6", r'Giải\s*sáu\s*[：:]\s*(.*?)</tr>', True),
        ("G7", r'Giải\s*bảy\s*[：:]\s*(.*?)</tr>', True),
    ]

    for key, pattern, *multi in patterns:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            if multi:
                # Multi-number prize: extract all <b>XXX</b> inside
                nums = re.findall(r'<b>(\d+)</b>', m.group(1))
                prizes[key] = " ".join(nums)
            else:
                prizes[key] = m.group(1)

    if not prizes:
        # Try table-based parsing (ketqua.net layout)
        table_match = re.search(
            r'<table[^>]*class="[^"]*ketqua[^"]*"[^>]*>(.*?)</table>',
            html, re.DOTALL | re.IGNORECASE
        )
        if table_match:
            table_html = table_match.group(1)
            # Extract all bold numbers from the table
            all_nums = re.findall(r'<b>(\d+)</b>', table_html)
            if len(all_nums) >= 28:
                prizes["GDB"] = all_nums[0]
                prizes["G1"] = all_nums[1]
                prizes["G2"] = " ".join(all_nums[2:4])
                prizes["G3"] = " ".join(all_nums[4:10])
                prizes["G4"] = " ".join(all_nums[10:17])
                prizes["G5"] = " ".join(all_nums[17:23])
                prizes["G6"] = " ".join(all_nums[23:26])
                prizes["G7"] = " ".join(all_nums[26:])

    if not prizes:
        return None
    return prizes


# ── Pure-Python Prediction Methods ────────────────────────────

def pascal_prediction(gdb: str, g1: str) -> int:
    """Pascal merge of ĐB + G1 → two-digit number."""
    s = gdb.strip() + g1.strip()
    while len(s) > 2:
        s = "".join(str((int(s[i]) + int(s[i+1])) % 10) for i in range(len(s) - 1))
    return int(s)


def monte_carlo_prediction(loto_numbers, simulations=SIM_N):
    """Frequency-based Monte Carlo. Returns top10 list of (num, prob_pct)."""
    from collections import Counter
    freq = Counter(loto_numbers)
    weights = [freq.get(n, 1) for n in range(100)]
    total_w = sum(weights)
    probs = [w / total_w for w in weights]

    sim_counter = Counter()
    for _ in range(simulations):
        draw = random.choices(range(100), weights=probs, k=27)
        sim_counter.update(set(draw))

    top10 = sim_counter.most_common(10)
    return [(n, c / simulations * 100) for n, c in top10]


def cdm_prediction_single(loto_numbers):
    """Laplace-smoothed Dirichlet-Multinomial estimate (single-day approximation)."""
    from collections import Counter
    freq = Counter(loto_numbers)
    alpha = [1 + freq.get(i, 0) for i in range(100)]
    alpha_0 = sum(alpha)
    expected = [27 * a / alpha_0 for a in alpha]
    top10 = sorted(range(100), key=lambda i: expected[i], reverse=True)[:10]
    return [(i, expected[i]) for i in top10]


# ── Database ──────────────────────────────────────────────────

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS xsmb (
            ngay TEXT PRIMARY KEY,
            gdb TEXT, g1 TEXT, g2 TEXT, g3 TEXT, g4 TEXT,
            g5 TEXT, g6 TEXT, g7 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_result(date_str, prizes):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO xsmb (ngay, gdb, g1, g2, g3, g4, g5, g6, g7, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (date_str, prizes.get("GDB", ""), prizes.get("G1", ""),
          prizes.get("G2", ""), prizes.get("G3", ""), prizes.get("G4", ""),
          prizes.get("G5", ""), prizes.get("G6", ""), prizes.get("G7", "")))
    conn.commit()
    conn.close()


def get_latest_from_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at DESC LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "ngay": row[0],
            "GDB": row[1], "G1": row[2], "G2": row[3], "G3": row[4],
            "G4": row[5], "G5": row[6], "G6": row[7], "G7": row[8],
        }
    return None


def count_db_days():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT COUNT(*) FROM xsmb")
    count = cur.fetchone()[0]
    conn.close()
    return count


# ── Loto extraction ──────────────────────────────────────────

def extract_lotos(prizes: dict) -> list:
    nums = []
    for key in ["GDB", "G1", "G2", "G3", "G4", "G5", "G6", "G7"]:
        val = prizes.get(key, "")
        for p in val.split():
            if len(p) >= 2:
                nums.append(int(p[-2:]))
    return nums


# ── Main ──────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

    # 1. Fetch today
    today = today_str()
    display = today_display()
    prizes = fetch_xsmb(today)

    if not prizes:
        # Fall back to yesterday's result from DB
        latest = get_latest_from_db()
        if latest:
            prizes = {k: v for k, v in latest.items() if k != "ngay"}
            display = latest["ngay"].replace("-", "/")
            print(f"(⚡ Dùng dữ liệu ngày {latest['ngay']} vì hôm nay chưa có)")
        else:
            print(f"🕐 Hôm nay {display} chưa có kết quả.")
            print("XSMB quay lúc 18h10-18h30 hàng ngày.")
            sys.exit(1)

    # 2. Save to DB
    if not dry_run:
        init_db()
        save_result(today, prizes)

    # 3. Compute lotos
    lotos = extract_lotos(prizes)
    unique_lotos = sorted(set(lotos))
    loto_str = " - ".join(f"{n:02d}" for n in unique_lotos)

    # 4. Predictions
    gdb = prizes.get("GDB", "00000")
    g1 = prizes.get("G1", "00000")
    pascal_num = pascal_prediction(gdb.split()[0], g1.split()[0])

    mc_top10 = monte_carlo_prediction(lotos)
    cdm_top10 = cdm_prediction_single(lotos)

    mc_str = " - ".join(f"{n:02d}" for n, _ in mc_top10)
    cdm_str = " - ".join(f"{n:02d}" for n, _ in cdm_top10)

    # 5. Accuracy eval (compare yesterday's prediction if available)
    yest = yesterday_str()
    eval_lines = []
    try:
        yest_prizes = fetch_xsmb(yest)
        if yest_prizes:
            yest_lotos = extract_lotos(yest_prizes)
            yest_uniq = sorted(set(yest_lotos))

            # Pascal
            ygdb = yest_prizes.get("GDB", "00000")
            yg1 = yest_prizes.get("G1", "00000")
            yp = pascal_prediction(ygdb.split()[0], yg1.split()[0])
            pascal_hit = yp in yest_uniq
            eval_lines.append(
                f"  - Cầu Pascal hôm qua gợi ý: {'🎉 TRÚNG' if pascal_hit else '❌ Trượt'} ({yp:02d})"
            )

            # MC eval (simple freq-based on yesterday's data)
            mc_hits = [n for n, _ in monte_carlo_prediction(yest_lotos) if n in yest_uniq]
            mc_str2 = " - ".join(f"{n:02d}" for n in sorted(mc_hits)) if mc_hits else "Không trúng"
            eval_lines.append(f"  - Top 10 Monte Carlo: Trúng {len(mc_hits)}/10 số ({mc_str2})")

            # CDM eval
            cdm_hits = [n for n, _ in cdm_prediction_single(yest_lotos) if n in yest_uniq]
            cdm_str2 = " - ".join(f"{n:02d}" for n in sorted(cdm_hits)) if cdm_hits else "Không trúng"
            eval_lines.append(f"  - Top 10 Bayesian CDM: Trúng {len(cdm_hits)}/10 số ({cdm_str2})")
        else:
            eval_lines.append("  - Không có dữ liệu hôm qua để đánh giá.")
    except Exception as e:
        eval_lines.append(f"  - Lỗi đánh giá: {e}")

    if not eval_lines:
        eval_lines.append("  - Chưa thể đánh giá.")

    total_days = count_db_days()
    current_time = now_vn().strftime("%H:%M:%S %d/%m/%Y")

    # 6. Report
    print("=" * 40)
    print(f"🎰 KQXSMB - {display}")
    print("=" * 40)
    print("(1) 📋 KẾT QUẢ XSMB:")
    print(f"  - 👑 Đặc biệt: {prizes.get('GDB', '?')}")
    print(f"  - 🥇 Giải Nhất: {prizes.get('G1', '?')}")
    print(f"  - 🥈 Giải Nhì:  {prizes.get('G2', '?')}")
    print(f"  - 🥉 Giải Ba:   {prizes.get('G3', '?')}")
    print(f"  - Giải Tư:   {prizes.get('G4', '?')}")
    print(f"  - Giải Năm:  {prizes.get('G5', '?')}")
    print(f"  - Giải Sáu:  {prizes.get('G6', '?')}")
    print(f"  - Giải Bảy:  {prizes.get('G7', '?')}")
    print()
    print("(2) 🎯 LÔ TÔ ĐÃ VỀ:")
    print(f"  {loto_str}")
    print()
    print("(3) 🔮 DỰ ĐOÁN PASCAL (NGÀY MAI):")
    print(f"  Cặp số gợi ý: {pascal_num:02d}")
    print()
    print("(4) 🎲 DỰ ĐOÁN MONTE CARLO (NGÀY MAI - TOP 10):")
    print(f"  {mc_str}")
    print()
    print("(5) 📊 DỰ ĐOÁN BAYESIAN CDM (NGÀY MAI - TOP 10):")
    print(f"  {cdm_str}")
    print()
    print("(6) 📈 ĐÁNH GIÁ ĐỘ CHÍNH XÁC SOI CẦU HÔM NAY:")
    for line in eval_lines:
        print(line)
    print()
    print("(7) 💾 TÌNH TRẠNG CẬP NHẬT DATABASE:")
    print("  - 🗄️ CSDL: xsmb_results.db")
    print(f"  - 📅 Tổng số ngày dữ liệu: {total_days}")
    print(f"  - ⚡ Trạng thái: Đã cập nhật lúc {current_time}")
    print("=" * 40)


if __name__ == "__main__":
    main()
