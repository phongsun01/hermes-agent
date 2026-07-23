#!/opt/hermes/.venv/bin/python3
"""xsmb_cron.py — Cron job: fetch KQXSMB hôm nay, lưu DB, thông báo theo template cố định

Chạy lúc 18:35 VN (11:35 UTC) hàng ngày sau khi có kết quả XSMB (18:10-18:30).

Dùng: python3 /opt/data/scripts/xsmb_cron.py
Với no_agent=True, stdout được gửi thẳng về Zalo.
"""

import sys
import os
import json
import datetime
import sqlite3
import pandas as pd
import numpy as np
import contextlib

# Thêm plugin path để import
PLUGIN_DIR = "/opt/data/plugins/xsmb"
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import xsmb_fetcher
import xsmb_db
import pascal_mc
import xsmb_cdm

# Dùng venv python có pandas
VENV_PYTHON = "/opt/hermes/.venv/bin/python3"

# Cập nhật lại đường dẫn DB của plugin
xsmb_db.DB_PATH = os.path.join(PLUGIN_DIR, "xsmb_results.db")

@contextlib.contextmanager
def suppress_stdout():
    """Tạm thời chặn các bản in debug ra stdout của các module bên thứ ba"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

def now_vn():
    """Trả về datetime hiện tại giờ VN (UTC+7)"""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))

def evaluate_today_accuracy(today_str, today_lotos):
    """
    Tái lập dự báo từ ngày hôm trước và so sánh với kết quả thực tế hôm nay (today_lotos).
    """
    try:
        conn = sqlite3.connect(xsmb_db.DB_PATH)
        df_raw = pd.read_sql_query("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at ASC", conn)
        conn.close()
        
        if len(df_raw) < 2:
            return "  - Can it nhat 2 ngay du lieu de danh gia."
            
        today_idx = df_raw[df_raw['ngay'] == today_str].index
        if len(today_idx) == 0:
            return f"  - Khong tim thay ngay {today_str} trong CSDL de danh gia."
            
        idx = today_idx[0]
        if idx == 0:
            return "  - Khong co ngay lien truoc de doi chieu du bao."
            
        # Lấy lịch sử đến ngày hôm qua
        df_history = df_raw.iloc[:idx]
        
        processed_rows = []
        for _, row in df_history.iterrows():
            numbers = []
            numbers.extend(row['gdb'].split())
            numbers.extend(row['g1'].split())
            numbers.extend(row['g2'].split())
            numbers.extend(row['g3'].split())
            numbers.extend(row['g4'].split())
            numbers.extend(row['g5'].split())
            numbers.extend(row['g6'].split())
            numbers.extend(row['g7'].split())
            if len(numbers) == 27:
                processed_rows.append([row['ngay']] + [int(num) for num in numbers])
                
        if len(processed_rows) == 0:
            return "  - Du lieu lich su khong hop le de doi chieu."
            
        col_names = ['date', 'special', 'g1'] + [f'num{i}' for i in range(2, 27)]
        df_processed = pd.DataFrame(processed_rows, columns=col_names)
        
        # Chạy dự đoán hôm qua với stdout được tắt đi
        with suppress_stdout():
            # 1. Dự đoán hôm qua theo Monte Carlo + Pascal
            pascal_num_res, top_mc = pascal_mc.monte_carlo_with_pascal(df_processed, last_days=30)
            pascal_val = int(pascal_num_res[0] if isinstance(pascal_num_res, tuple) else pascal_num_res)
            
            # 2. Dự đoán hôm qua theo CDM
            n_days = len(df_processed)
            X = np.zeros((n_days, 100), dtype=np.float32)
            for i, row in df_processed.iterrows():
                for col in ['special', 'g1'] + [f'num{k}' for k in range(2, 27)]:
                    val = int(row[col]) % 100
                    X[i, val] += 1.0
            alpha, alpha_0 = xsmb_cdm.estimate_dirichlet_multinomial(X)
            n_j = np.sum(X, axis=0)
            sum_n = np.sum(n_j)
            M = 27
            expected_counts = M * (alpha + n_j) / (alpha_0 + sum_n)
            top_cdm = np.argsort(expected_counts)[-10:][::-1]
        
        # Đối chiếu kết quả hôm nay
        pascal_hit = pascal_val in today_lotos
        
        mc_hits = []
        for num, count in top_mc[:10]:
            if num in today_lotos:
                mc_hits.append(num)
                
        cdm_hits = []
        for num in top_cdm:
            if num in today_lotos:
                cdm_hits.append(num)
                
        report = []
        # 1. Cầu Pascal
        status_pascal = f"TRÚNG 🎉 ({pascal_val:02d})" if pascal_hit else f"Trượt ❌ ({pascal_val:02d})"
        report.append(f"  - Cầu Pascal hôm qua gợi ý: {status_pascal}")
        
        # 2. Monte Carlo
        mc_hits_str = " - ".join(f"{n:02d}" for n in sorted(mc_hits)) if mc_hits else "Không trúng"
        report.append(f"  - Top 10 Monte Carlo: Trúng {len(mc_hits)}/10 số ({mc_hits_str})")
            
        # 3. CDM (Bayesian)
        cdm_hits_str = " - ".join(f"{n:02d}" for n in sorted(cdm_hits)) if cdm_hits else "Không trúng"
        report.append(f"  - Top 10 Bayesian CDM: Trúng {len(cdm_hits)}/10 số ({cdm_hits_str})")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"  - Loi danh gia do chinh xac: {e}"

def main():
    today = now_vn().strftime("%d-%m-%Y")
    today_display = now_vn().strftime("%d/%m/%Y")
    
    # 1. Fetch + lưu DB bằng plugin
    result = None
    try:
        xsmb_db.init_db()
        with suppress_stdout():
            data = xsmb_fetcher.fetch_and_save_daily(today)
        if data:
            result = data
        else:
            # Dự phòng: Lấy ngày cuối cùng có sẵn trong DB để test nếu hôm nay chưa có
            conn = sqlite3.connect(xsmb_db.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT ngay FROM xsmb ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                today = row[0]
                result = xsmb_db.get_result(today)
                today_display = today.replace("-", "/")
    except Exception as e:
        print(f"Loi cào du lieu DB: {e}", file=sys.stderr)
    
    # 2. Trình bày kết quả theo cấu trúc mẫu cố định
    if result:
        gdb = result.get("GDB", "?????")
        g1 = result.get("G1", "?????")
        g2 = result.get("G2", "")
        g3 = result.get("G3", "")
        g4 = result.get("G4", "")
        g5 = result.get("G5", "")
        g6 = result.get("G6", "")
        g7 = result.get("G7", "")
        
        # Trích loto 2 số cuối
        all_nums = []
        for key in ["GDB", "G1", "G2", "G3", "G4", "G5", "G6", "G7"]:
            val = result.get(key, "")
            parts = val.split()
            for p in parts:
                if len(p) >= 2:
                    all_nums.append(int(p[-2:]))
        
        unique_lotos = sorted(set(all_nums))
        loto_str = " - ".join(f"{n:02d}" for n in unique_lotos)
        
        # Chạy dự báo cho ngày mai với stdout được tắt đi
        with suppress_stdout():
            # 1. Cầu Pascal ngày mai
            try:
                tomorrow_pascal_res = pascal_mc.pascal_prediction(int(gdb.split()[0]), int(g1.split()[0]))
                tomorrow_pascal = tomorrow_pascal_res[0] if isinstance(tomorrow_pascal_res, tuple) else tomorrow_pascal_res
            except Exception:
                tomorrow_pascal = "??"
                
            try:
                conn = sqlite3.connect(xsmb_db.DB_PATH)
                df_tomorrow_raw = pd.read_sql_query("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at ASC", conn)
                total_days_in_db = len(df_tomorrow_raw)
                conn.close()
                
                processed_rows = []
                for _, row in df_tomorrow_raw.iterrows():
                    numbers = []
                    numbers.extend(row['gdb'].split())
                    numbers.extend(row['g1'].split())
                    numbers.extend(row['g2'].split())
                    numbers.extend(row['g3'].split())
                    numbers.extend(row['g4'].split())
                    numbers.extend(row['g5'].split())
                    numbers.extend(row['g6'].split())
                    numbers.extend(row['g7'].split())
                    if len(numbers) == 27:
                        processed_rows.append([row['ngay']] + [int(num) for num in numbers])
                
                col_names = ['date', 'special', 'g1'] + [f'num{i}' for i in range(2, 27)]
                df_processed = pd.DataFrame(processed_rows, columns=col_names)
                
                _, top_mc = pascal_mc.monte_carlo_with_pascal(df_processed, last_days=30)
                
                expected_counts, alpha_0 = xsmb_cdm.cdm_prediction(xsmb_db.DB_PATH, last_days=30)
                top_cdm = np.argsort(expected_counts)[-10:][::-1]
                
                tomorrow_mc_str = " - ".join(f"{num:02d}" for num, count in top_mc[:5])
                tomorrow_cdm_str = " - ".join(f"{num:02d}" for num in top_cdm[:5])
            except Exception as e:
                tomorrow_mc_str = f"Loi tinh MC: {e}"
                tomorrow_cdm_str = f"Loi tinh CDM: {e}"
                total_days_in_db = 0

        # Đánh giá độ chính xác hôm nay
        eval_report = evaluate_today_accuracy(today, unique_lotos)
        
        current_time_str = now_vn().strftime("%H:%M:%S %d/%m/%Y")
        
        # Báo cáo theo mẫu cố định
        print("=" * 40)
        print(f"🎰 KQXSMB - {today_display}")
        print("=" * 40)
        print("(1) 📋 KẾT QUẢ XSMB:")
        print(f"  - 👑 Đặc biệt: {gdb}")
        print(f"  - 🥇 Giải Nhất: {g1}")
        print(f"  - 🥈 Giải Nhì:  {g2}")
        print(f"  - 🥉 Giải Ba:   {g3}")
        print(f"  - Giải Tư:   {g4}")
        print(f"  - Giải Năm:  {g5}")
        print(f"  - Giải Sáu:  {g6}")
        print(f"  - Giải Bảy:  {g7}")
        print()
        print("(2) 🎯 LÔ TÔ ĐÃ VỀ:")
        print(f"  {loto_str}")
        print()
        print("(3) 🔮 DỰ ĐOÁN PASCAL (NGÀY MAI):")
        print(f"  Cặp số gợi ý: {tomorrow_pascal}")
        print()
        print("(4) 🎲 DỰ ĐOÁN MONTE CARLO (NGÀY MAI - TOP 5):")
        print(f"  {tomorrow_mc_str}")
        print()
        print("(5) 📊 DỰ ĐOÁN BAYESIAN CDM (NGÀY MAI - TOP 5):")
        print(f"  {tomorrow_cdm_str}")
        print()
        print("(6) 📈 ĐÁNH GIÁ ĐỘ CHÍNH XÁC SOI CẦU HÔM NAY:")
        print(eval_report)
        print()
        print("(7) 💾 TÌNH TRẠNG CẬP NHẬT DATABASE:")
        print("  - 🗄️ CSDL: xsmb_results.db")
        print(f"  - 📅 Tổng số ngày dữ liệu: {total_days_in_db}")
        print(f"  - ⚡ Trạng thái: Đã cập nhật lúc {current_time_str}")
        print("=" * 40)
    else:
        print(f"🕐 Hom nay {today_display} chua co ket qua.")
        print("XSMB quay luc 18h10-18h30 hang ngay.")

if __name__ == "__main__":
    main()
