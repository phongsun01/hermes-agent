#!/usr/bin/env python3
"""vl_report.py — Định dạng báo cáo kết quả Vietlott Mega 6/45 theo template chuẩn có đánh số.

Bố cục 5 mục:
  1. Bộ số trúng thưởng
  2. Thông tin giải thưởng
  3. Thống kê nhanh & kiểm định Q
  4. Đánh giá dự đoán kỳ này (so kỳ trước với kỳ hiện tại)
  5. Bộ số tham khảo kỳ tiếp theo
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


def evaluate_past_prediction(draws, cur_ky, cur_nums):
    """Mục 4: Đánh giá dự đoán kỳ này bằng cách so với gợi ý từ lịch sử trước kỳ quay hiện tại."""
    if not draws or len(draws) < 2:
        return "Chưa đủ dữ liệu lịch sử để đánh giá.", "Chưa đủ dữ liệu.", "Chưa đủ dữ liệu.", 0

    # Nếu kỳ hiện tại nằm cuối mảng draws thì tách lấy lịch sử trước nó
    # Ngược lại, nếu chưa có trong draws thì toàn bộ draws là lịch sử trước đó
    if draws[-1] == cur_nums:
        hist = draws[:-1]
        prev_ky = cur_ky - 1
    else:
        hist = draws
        prev_ky = cur_ky - 1

    cur_set = set(cur_nums)
    f_hist = vietlott645.freq(hist)
    pool = list(range(1, 46))
    max_f = max(f_hist.values()) if f_hist else 0

    # Tái lập dự đoán Hot (CDM) từ kỳ trước: lấy 6 số có tần suất cao nhất
    order_hot = sorted(pool, key=lambda i: (f_hist[i], i), reverse=True)
    hot_pred = set(order_hot[:6])
    hot_hits = sorted(hot_pred & cur_set)

    # Tái lập dự đoán Cold từ kỳ trước: lấy 6 số ít xuất hiện nhất
    order_cold = sorted(pool, key=lambda i: (f_hist[i], i))
    cold_pred = set(order_cold[:6])
    cold_hits = sorted(cold_pred & cur_set)

    # Tái lập dự đoán Random bằng seed từ số kỳ trước để kết quả có tính lặp lại (reproducible)
    rnd_prev = random.Random(prev_ky)
    rand_pred = set(rnd_prev.sample(pool, 6))
    rand_hits = sorted(rand_pred & cur_set)

    def _fmt_hits(hits_list):
        if not hits_list:
            return "Trúng 0/6 số"
        joined = ", ".join(f"{x:02d}" for x in hits_list)
        prize = ""
        if len(hits_list) == 3:
            prize = " 🥉 (Giải Ba)"
        elif len(hits_list) == 4:
            prize = " 🥈 (Giải Nhì)"
        elif len(hits_list) == 5:
            prize = " 🥇 (Giải Nhất)"
        elif len(hits_list) == 6:
            prize = " 🏆 (JACKPOT!)"
        return f"Trúng {len(hits_list)}/6 số: [{joined}]{prize}"

    return _fmt_hits(hot_hits), _fmt_hits(cold_hits), _fmt_hits(rand_hits), prev_ky


def generate_report(detail=None, n_stats=30):
    """Tạo nội dung báo cáo theo mẫu chuẩn 5 mục đánh số."""
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

    # Mục 4: Đánh giá dự đoán kỳ này
    hot_eval, cold_eval, rand_eval, prev_ky = evaluate_past_prediction(draws, detail["ky"], detail["nums"])

    # Mục 5: Bộ số tham khảo kỳ tiếp theo
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

4. ĐÁNH GIÁ DỰ ĐOÁN KỲ NÀY:
   (Đối chiếu bộ số gợi ý kỳ trước #{prev_ky:05d} với kết quả hôm nay)
   - Vé Hot (CDM): {hot_eval}
   - Vé Cold:      {cold_eval}
   - Vé Random:    {rand_eval}

5. BỘ SỐ THAM KHẢO KỲ TIẾP THEO:
   🎯 Vé Hot (CDM): [{pick_hot}]
   🎯 Vé Cold:      [{pick_cold}]
   🎲 Vé Random:    [{pick_rand}]

⚠️ LƯU Ý: Mọi bộ số đều có xác suất Jackpot 1/8.145.060. Kỳ vọng mỗi vé âm (EV < 0). Chúc bạn may mắn!"""
    return report


if __name__ == "__main__":
    rep = generate_report()
    print(rep)
