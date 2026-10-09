#!/usr/bin/env python3
"""vl_report.py — Định dạng báo cáo kết quả Vietlott Mega 6/45 theo template chuẩn có đánh số.

Dùng cho:
- Cron job `vl_update_cron` gửi kết quả tự động qua Zalo.
- CLI / người dùng gọi `/vl report` hoặc `/vl`.
"""
import math
import random
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# Đảm bảo UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import vietlott645
import vl_fetch

TEMPLATE_PATH = SCRIPT_DIR.parent / "references" / "report-template.md"


def fetch_detailed_result(date_obj=None):
    """Fetch kết quả kèm chi tiết giải thưởng từ HTML."""
    if date_obj is None:
        date_obj = vl_fetch.get_latest_draw_date()

    d_str = date_obj.strftime("%d-%m-%Y")
    url = f"{vl_fetch.BASE_URL}/{d_str}.html"
    html = vl_fetch._fetch_html(url)
    if not html:
        return None

    nums_raw = re.findall(r'class="finnish\d\s+bool"[^>]*>(\d+)<', html)
    if len(nums_raw) < 6:
        return None

    ky_match = re.search(r'id="DT6X45_KY_VE">#?(\d+)', html)
    ky = int(ky_match.group(1)) if ky_match else 0
    ngay_match = re.search(r'Ng&agrave;y quay thưởng\s+(\d{2}/\d{2}/\d{4})', html)
    ngay_str = ngay_match.group(1) if ngay_match else date_obj.strftime("%d/%m/%Y")

    nums = sorted(int(x) for x in nums_raw[:6])

    # Chi tiết giải thưởng
    m_jp = re.search(r'id="DT6X45_G_JACKPOT"[^>]*>([^<]+)', html)
    m_s_jp = re.search(r'id="DT6X45_S_JACKPOT"[^>]*>\s*([0-9,.]+)', html)
    m_s_g1 = re.search(r'id="DT6X45_S_G1"[^>]*>\s*([0-9,.]+)', html)
    m_s_g2 = re.search(r'id="DT6X45_S_G2"[^>]*>\s*([0-9,.]+)', html)
    m_s_g3 = re.search(r'id="DT6X45_S_G3"[^>]*>\s*([0-9,.]+)', html)

    jackpot_val = m_jp.group(1).strip() if m_jp else "12.000.000.000"
    # Format dấu chấm phân cách hàng nghìn cho đẹp
    jackpot_val = jackpot_val.replace(",", ".")
    if not jackpot_val.endswith("đ") and not jackpot_val.endswith(" đồng"):
        jackpot_val_str = jackpot_val
    else:
        jackpot_val_str = re.sub(r'[^\d.]', '', jackpot_val)

    jp_cnt = int(m_s_jp.group(1).replace(",", "").replace(".", "")) if m_s_jp else 0
    g1_cnt = m_s_g1.group(1).strip() if m_s_g1 else "0"
    g2_cnt = m_s_g2.group(1).strip() if m_s_g2 else "0"
    g3_cnt = m_s_g3.group(1).strip() if m_s_g3 else "0"

    return {
        "ky": ky,
        "ngay": ngay_str,
        "nums": nums,
        "jackpot": jackpot_val_str,
        "jackpot_winners": jp_cnt,
        "g1_winners": g1_cnt,
        "g2_winners": g2_cnt,
        "g3_winners": g3_cnt,
    }


def generate_report(detail=None, n_stats=30):
    """Tạo nội dung báo cáo theo mẫu chuẩn có đánh số mục."""
    if detail is None:
        detail = fetch_detailed_result()

    if not detail:
        return "⚠️ Không lấy được kết quả Vietlott Mega 6/45 gần nhất."

    # Lấy cache lịch sử để tính thống kê
    draws = vietlott645.load(limit=n_stats)
    m = len(draws)
    f = vietlott645.freq(draws) if draws else {i: 0 for i in range(1, 46)}
    ranked = sorted(f.items(), key=lambda x: (-x[1], x[0]))

    hot_list = [f"{n:02d}({c})" for n, c in ranked[:5]]
    cold_list = [f"{n:02d}({c})" for n, c in ranked[-5:]]
    hot_str = ", ".join(hot_list)
    cold_str = ", ".join(cold_list)

    # Thống kê thứ tự Q
    if m >= 20:
        Q, p_clt, _ = vietlott645.order_stat_test(draws, mc=100)
        p_q_str = f"{p_clt:.3f}"
        q_verdict = "Chuẩn ngẫu nhiên" if p_clt >= 0.01 else "Cần theo dõi"
    else:
        p_q_str = "N/A"
        q_verdict = "Chưa đủ kỳ dữ liệu"

    # Bộ số tham khảo
    pool = list(range(1, 46))
    max_f = max(f.values()) if f else 0
    w_hot = [f[i] + 1 for i in pool]
    w_cold = [max_f - f[i] + 1 for i in pool]

    def _sample(weights):
        s = set()
        while len(s) < 6:
            s.add(random.choices(pool, weights)[0])
        return ", ".join(f"{x:02d}" for x in sorted(s))

    pick_hot = _sample(w_hot)
    pick_cold = _sample(w_cold)
    pick_rand = ", ".join(f"{x:02d}" for x in sorted(random.sample(pool, 6)))

    jp_status = f"ĐÃ NỔ ({detail['jackpot_winners']} người trúng)" if detail['jackpot_winners'] > 0 else "CHƯA NỔ - Tích lũy tiếp"
    nums_formatted = " - ".join(f"{x:02d}" for x in detail["nums"])

    report = f"""🎰 KẾT QUẢ VIETLOTT MEGA 6/45 — KỲ #{detail['ky']:05d} ({detail['ngay']})

1. BỘ SỐ TRÚNG THƯỞNG:
   👉 {nums_formatted}

2. THÔNG TIN GIẢI THƯỞNG:
   🏆 Jackpot: {detail['jackpot']} đ ({jp_status})
   🥇 Giải Nhất (5 số): {detail['g1_winners']} giải (10.000.000 đ)
   🥈 Giải Nhì  (4 số): {detail['g2_winners']} giải (300.000 đ)
   🥉 Giải Ba   (3 số): {detail['g3_winners']} giải (30.000 đ)

3. THỐNG KÊ NHANH ({m} KỲ GẦN NHẤT):
   🔥 Top số nóng: {hot_str}
   ❄️ Top số lạnh: {cold_str}
   ⚖️ Kiểm định ngẫu nhiên Q (arXiv:0806.4595): p = {p_q_str} ({q_verdict})

4. BỘ SỐ THAM KHẢO KỲ TIẾP THEO:
   🎯 Vé Hot (CDM): [{pick_hot}]
   🎯 Vé Cold:      [{pick_cold}]
   🎲 Vé Random:    [{pick_rand}]

⚠️ LƯU Ý: Mọi bộ số đều có xác suất Jackpot 1/8.145.060. Kỳ vọng mỗi vé âm (EV < 0). Chúc bạn may mắn!"""
    return report


if __name__ == "__main__":
    rep = generate_report()
    print(rep)
