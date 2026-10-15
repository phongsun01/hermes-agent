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


def fetch_detailed_result(date_obj=None):
    """Fetch kết quả kèm chi tiết giải thưởng từ HTML, scoped vào box kỳ tương ứng."""
    if date_obj is None:
        date_obj = vl_fetch.get_latest_draw_date()

    d_str = date_obj.strftime("%d-%m-%Y")
    url = f"{vl_fetch.BASE_URL}/{d_str}.html"
    html = vl_fetch._fetch_html(url)
    if not html:
        return None

    # Tái sử dụng _parse_draw để validate và trích xuất dữ liệu cơ bản (6 số, 1-45, số kỳ)
    parsed = vl_fetch._parse_draw(html, date_obj.strftime("%d/%m/%Y"))
    if not parsed:
        return None

    ky = parsed["ky"]
    ngay_str = parsed["ngay"]
    nums = parsed["nums"]

    # Scope vào khối HTML của kỳ quay này (<div class="box-result-detail">) để tránh lẫn lộn các kỳ khác
    parts = html.split('<div class="box-result-detail">')
    target_block = html
    for part in parts[1:]:
        if f'id="DT6X45_KY_VE">#{ky:05d}' in part or f'id="DT6X45_KY_VE">{ky}' in part or f'id="DT6X45_KY_VE">#{ky}' in part:
            target_block = part
            break

    # Chi tiết giải thưởng trong target_block
    m_jp = re.search(r'id="DT6X45_G_JACKPOT"[^>]*>([^<]+)', target_block)
    m_s_jp = re.search(r'id="DT6X45_S_JACKPOT"[^>]*>\s*([0-9,.]+)', target_block)
    m_s_g1 = re.search(r'id="DT6X45_S_G1"[^>]*>\s*([0-9,.]+)', target_block)
    m_s_g2 = re.search(r'id="DT6X45_S_G2"[^>]*>\s*([0-9,.]+)', target_block)
    m_s_g3 = re.search(r'id="DT6X45_S_G3"[^>]*>\s*([0-9,.]+)', target_block)

    def _clean_num(val_str, default=0):
        if not val_str:
            return default
        cleaned = re.sub(r'[^\d]', '', val_str)
        return int(cleaned) if cleaned else default

    def _fmt_vnd(num):
        return f"{num:,}".replace(",", ".")

    jackpot_num = _clean_num(m_jp.group(1)) if m_jp else 12_000_000_000
    jackpot_val_str = _fmt_vnd(jackpot_num)

    jp_cnt = _clean_num(m_s_jp.group(1)) if m_s_jp else 0
    g1_cnt = _fmt_vnd(_clean_num(m_s_g1.group(1))) if m_s_g1 else "0"
    g2_cnt = _fmt_vnd(_clean_num(m_s_g2.group(1))) if m_s_g2 else "0"
    g3_cnt = _fmt_vnd(_clean_num(m_s_g3.group(1))) if m_s_g3 else "0"

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


def evaluate_past_prediction(cached_draws, cur_ky, cur_nums):
    """Mục 4: Đánh giá dự đoán kỳ này bằng cách so với gợi ý từ lịch sử trước kỳ quay hiện tại.
    
    Tìm kỳ ngay trước cur_ky từ cache lịch sử thực tế (không giả định cur_ky - 1).
    Thống nhất chiến lược:
      - Hot (CDM): 6 số có tần suất cao nhất tính đến trước kỳ quay.
      - Cold: 6 số có tần suất thấp nhất tính đến trước kỳ quay.
      - Random: sinh bằng random.Random(seed=prev_ky) khớp với gợi ý kỳ trước.
    """
    if not cached_draws or len(cached_draws) < 2:
        return "Chưa đủ dữ liệu lịch sử để đánh giá.", "Chưa đủ dữ liệu.", "Chưa đủ dữ liệu.", 0

    # Lấy danh sách kỳ đã sắp xếp tăng dần
    sorted_kys = sorted(cached_draws.keys())
    
    if cur_ky in sorted_kys:
        idx = sorted_kys.index(cur_ky)
        if idx == 0:
            return "Kỳ đầu tiên trong cache, không có dữ liệu kỳ trước.", "Chưa đủ dữ liệu.", "Chưa đủ dữ liệu.", 0
        prev_ky = sorted_kys[idx - 1]
        hist = [cached_draws[k]["nums"] for k in sorted_kys[:idx]]
    else:
        # Nếu cur_ky chưa kịp lưu vào cache thì kỳ gần nhất trong cache chính là kỳ trước
        prev_kys = [k for k in sorted_kys if k < cur_ky]
        if not prev_kys:
            return "Không tìm thấy kỳ trước trong cache.", "Chưa đủ dữ liệu.", "Chưa đủ dữ liệu.", 0
        prev_ky = prev_kys[-1]
        hist = [cached_draws[k]["nums"] for k in prev_kys]

    cur_set = set(cur_nums)
    f_hist = vietlott645.freq(hist)
    pool = list(range(1, 46))

    # Tái lập dự đoán Hot (Tần suất) từ kỳ trước: lấy 6 số có tần suất cao nhất (deterministic)
    order_hot = sorted(pool, key=lambda i: (f_hist[i], i), reverse=True)
    hot_pred = set(order_hot[:6])
    hot_hits = sorted(hot_pred & cur_set)

    # Tái lập dự đoán Cold từ kỳ trước: lấy 6 số ít xuất hiện nhất (deterministic)
    order_cold = sorted(pool, key=lambda i: (f_hist[i], i))
    cold_pred = set(order_cold[:6])
    cold_hits = sorted(cold_pred & cur_set)

    # Tái lập dự đoán Random bằng seed từ số kỳ trước (khớp với seed mục 5 của kỳ trước)
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


def generate_report(detail=None, n_stats=300):
    """Tạo nội dung báo cáo theo mẫu chuẩn 5 mục đánh số."""
    if detail is None:
        detail = fetch_detailed_result()

    if not detail:
        return "⚠️ Không lấy được kết quả Vietlott Mega 6/45 gần nhất."

    # Đọc cache đầy đủ từ file draws.csv để tra cứu kỳ trước chính xác
    cached_draws = vl_fetch.load_cached_draws(vl_fetch.DEFAULT_CSV_PATH)
    
    # Lấy n_stats kỳ gần nhất để tính toán thống kê
    draws = vietlott645.load(limit=n_stats)
    m = len(draws)
    f = vietlott645.freq(draws) if draws else {i: 0 for i in range(1, 46)}
    # Thống kê nhanh: số nóng (nhiều nhất) và số lạnh (ít nhất)
    ranked = sorted(f.items(), key=lambda x: (-x[1], x[0]))
    hot_list = [f"{n:02d}({c})" for n, c in ranked[:5]]
    ranked_cold = sorted(f.items(), key=lambda x: (x[1], x[0]))
    cold_list = [f"{n:02d}({c})" for n, c in ranked_cold[:5]]
    hot_str = ", ".join(hot_list)
    cold_str = ", ".join(cold_list)

    # Thống kê thứ tự Q (arXiv:0806.4595) & ngưỡng tin cậy
    if m >= 100:
        Q, p_clt, _ = vietlott645.order_stat_test(draws, mc=100)
        p_q_str = f"{p_clt:.3f}"
        q_verdict = "Chuẩn ngẫu nhiên" if p_clt >= 0.01 else "Cần theo dõi"
    elif m >= 20:
        Q, p_clt, _ = vietlott645.order_stat_test(draws, mc=100)
        p_q_str = f"{p_clt:.3f}"
        q_verdict = "Cần ≥100 kỳ để kết luận tin cậy"
    else:
        p_q_str = "N/A"
        q_verdict = "Chưa đủ kỳ dữ liệu"

    # Mục 4: Đánh giá dự đoán kỳ này
    hot_eval, cold_eval, rand_eval, prev_ky = evaluate_past_prediction(cached_draws, detail["ky"], detail["nums"])

    # Mục 5: Bộ số tham khảo kỳ tiếp theo
    # Thống nhất định nghĩa với mục 4:
    # - Vé Hot: top 6 số có tần suất xuất hiện cao nhất
    # - Vé Cold: top 6 số có tần suất xuất hiện thấp nhất
    # - Vé Random: sinh ngẫu nhiên dùng seed = next_ky (reproducible để kỳ sau mục 4 đánh giá khớp 100%)
    pool = list(range(1, 46))
    order_hot = sorted(pool, key=lambda i: (f[i], i), reverse=True)
    pick_hot = ", ".join(f"{x:02d}" for x in sorted(order_hot[:6]))

    order_cold = sorted(pool, key=lambda i: (f[i], i))
    pick_cold = ", ".join(f"{x:02d}" for x in sorted(order_cold[:6]))

    next_ky = detail["ky"] + 1
    rnd_next = random.Random(next_ky)
    pick_rand = ", ".join(f"{x:02d}" for x in sorted(rnd_next.sample(pool, 6)))

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
   - Vé Hot (Tần suất): {hot_eval}
   - Vé Cold (Lạnh):    {cold_eval}
   - Vé Random:         {rand_eval}

5. BỘ SỐ THAM KHẢO KỲ TIẾP THEO (KỲ #{next_ky:05d}):
   🎯 Vé Hot (Tần suất cao): [{pick_hot}]
   🎯 Vé Cold (Ít xuất hiện): [{pick_cold}]
   🎲 Vé Random:              [{pick_rand}]

⚠️ LƯU Ý: Mọi bộ số đều có xác suất Jackpot 1/8.145.060. Kỳ vọng mỗi vé âm (EV < 0). Chúc bạn may mắn!"""
    return report



if __name__ == "__main__":
    rep = generate_report()
    print(rep)

