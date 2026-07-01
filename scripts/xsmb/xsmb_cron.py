#!/opt/hermes/.venv/bin/python3
"""xsmb_cron.py — Cron job: fetch KQXSMB hôm nay, lưu DB, thông báo

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

# Thêm plugin path để import
PLUGIN_DIR = "/opt/data/plugins/xsmb"
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import xsmb_fetcher
import xsmb_db
import pascal_mc

# Dùng venv python có pandas
VENV_PYTHON = "/opt/hermes/.venv/bin/python3"

# Cập nhật lại đường dẫn DB của plugin
xsmb_db.DB_PATH = os.path.join(PLUGIN_DIR, "xsmb_results.db")

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
            return "⚠️ Can it nhat 2 ngay du lieu de danh gia."
            
        # Tìm xem ngày hôm nay nằm ở index nào
        today_idx = df_raw[df_raw['ngay'] == today_str].index
        if len(today_idx) == 0:
            return f"⚠️ Khong tim thay ngay {today_str} trong CSDL de danh gia."
            
        idx = today_idx[0]
        if idx == 0:
            return "⚠️ Khong co ngay lien truoc de doi chieu du bao."
            
        # Lấy lịch sử đến ngày hôm qua
        df_history = df_raw.iloc[:idx]
        
        # Tiền xử lý dữ liệu lịch sử để nạp vào Monte Carlo
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
            return "⚠️ Du lieu lich su khong hop le de doi chieu."
            
        col_names = ['date', 'special', 'g1'] + [f'num{i}' for i in range(2, 27)]
        df_processed = pd.DataFrame(processed_rows, columns=col_names)
        
        # Chạy thuật toán soi cầu ngày hôm qua
        pascal_num, top_mc = pascal_mc.monte_carlo_with_pascal(df_processed, last_days=30)
        pascal_val = int(pascal_num)
        
        # Đối chiếu kết quả hôm nay
        pascal_hit = pascal_val in today_lotos
        
        mc_hits = []
        for num, count in top_mc[:10]:
            if num in today_lotos:
                mc_hits.append(num)
                
        # Trình bày báo cáo
        report = []
        report.append("-" * 40)
        report.append("📊 DANH GIA DO CHINH XAC SOI CAU HOM NAY:")
        
        # 1. Cầu Pascal
        status_pascal = f"TRUNG ({pascal_val:02d})" if pascal_hit else f"Truot ({pascal_val:02d})"
        report.append(f"  - Cau Pascal hom qua goi y: {status_pascal}")
        
        # 2. Monte Carlo
        mc_hits_str = " - ".join(f"{n:02d}" for n in sorted(mc_hits)) if mc_hits else "Khong trung so nao"
        report.append(f"  - Top 10 Monte Carlo: Trung {len(mc_hits)}/10 so")
        if mc_hits:
            report.append(f"    👉 Chi tiet so trung: {mc_hits_str}")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"⚠️ Loi danh gia do chinh xac: {e}"

def main():
    today = now_vn().strftime("%d-%m-%Y")
    today_display = now_vn().strftime("%d/%m/%Y")
    
    # 1. Fetch + lưu DB bằng plugin
    result = None
    try:
        xsmb_db.init_db()
        
        # Thử fetch từ xskt.com.vn
        data = xsmb_fetcher.fetch_and_save_daily(today)
        if data:
            result = data
            print(f"✅ Da cap nhat DB: {today_display}")
        else:
            # Dự phòng: Lấy ngày cuối cùng có sẵn trong DB để test đánh giá nếu hôm nay chưa quay
            conn = sqlite3.connect(xsmb_db.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT ngay FROM xsmb ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                today = row[0]
                result = xsmb_db.get_result(today)
                today_display = today.replace("-", "/")
                print(f"ℹ️ Lay ngay gan nhat trong DB de chay test danh gia: {today_display}")
            else:
                print(f"⚠️  Chua co ket qua cho ngay {today_display}")
    except Exception as e:
        print(f"❌ Loi fetch DB: {e}", file=sys.stderr)
    
    # 2. Nếu fetch được, in thông báo kết quả và chạy đánh giá
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
        
        print("=" * 40)
        print(f"🎰 KQXSMB - {today_display}")
        print("=" * 40)
        print(f"🏆 DB: {gdb}")
        print(f"🥇 G1:  {g1}")
        print(f"🥈 G2:  {g2}")
        print(f"🥉 G3:  {g3}")
        print(f"🏅 G4:  {g4}")
        print(f"🏅 G5:  {g5}")
        print(f"🏅 G6:  {g6}")
        print(f"🏅 G7:  {g7}")
        print("-" * 40)
        print(f"🎯 Lo to: {loto_str}")
        
        # Chạy đánh giá độ chính xác đối chiếu với hôm qua
        eval_report = evaluate_today_accuracy(today, unique_lotos)
        print(eval_report)
        print("=" * 40)
    else:
        print(f"🕐 Hom nay {today_display} chua co ket qua.")
        print("XSMB quay luc 18h10-18h30 hang ngay.")

if __name__ == "__main__":
    main()
