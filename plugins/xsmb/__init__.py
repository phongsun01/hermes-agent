import json
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
import datetime

# Thêm thư mục hiện tại của plugin vào sys.path để import các module local
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import xsmb_db
import xsmb_fetcher
import pascal_mc
import xsmb_cdm

# Cập nhật lại đường dẫn DB để luôn ghi vào thư mục plugin trên máy/container
xsmb_db.DB_PATH = os.path.join(current_dir, "xsmb_results.db")

XSMB_SCHEMA = {
    "name": "get_xsmb",
    "description": (
        "Truy vấn kết quả xổ số miền Bắc (XSMB). Có thể lấy kết quả theo ngày cụ thể (định dạng dd-mm-yyyy), "
        "hoặc lấy danh sách kết quả của N ngày gần nhất từ database phục vụ mục đích thống kê lô tô."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Ngày muốn lấy kết quả, định dạng dd-mm-yyyy. Ví dụ: 15-06-2026. Nếu bỏ trống sẽ lấy ngày hôm nay."
            },
            "limit_days": {
                "type": "integer",
                "description": "Số lượng ngày gần nhất muốn lấy từ cơ sở dữ liệu để làm thống kê (ví dụ: 30)."
            }
        },
        "required": []
    }
}

PREDICT_XSMB_SCHEMA = {
    "name": "predict_xsmb",
    "description": (
        "Thực hiện dự đoán cầu Pascal kết hợp mô phỏng Monte Carlo và mô hình Bayesian Compound-Dirichlet-Multinomial (CDM) dựa trên dữ liệu lịch sử N ngày gần nhất (mặc định 30 ngày)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "last_days": {
                "type": "integer",
                "description": "Số lượng ngày gần nhất để làm mẫu thống kê (ví dụ: 30, 60, 90). Mặc định là 30 ngày.",
                "default": 30
            }
        },
        "required": []
    }
}

def get_xsmb(args: dict, **kwargs) -> str:
    date = args.get("date")
    limit_days = args.get("limit_days")
    
    xsmb_db.init_db()
    
    if limit_days is not None:
        try:
            conn = sqlite3.connect(xsmb_db.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at DESC LIMIT ?", (limit_days,))
            rows = cursor.fetchall()
            conn.close()
            
            results_list = []
            for r in rows:
                results_list.append({
                    "Ngay": r[0],
                    "GDB": r[1],
                    "G1": r[2],
                    "G2": r[3],
                    "G3": r[4],
                    "G4": r[5],
                    "G5": r[6],
                    "G7": r[8]
                })
            return json.dumps({"success": True, "results": results_list}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": f"Loi truy van danh sach: {e}"}, ensure_ascii=False)
            
    if not date:
        date = datetime.datetime.now().strftime("%d-%m-%Y")
        
    date = date.replace("/", "-")
    
    try:
        res = xsmb_db.get_result(date)
        if res:
            return json.dumps({"success": True, "results": res}, ensure_ascii=False)
    except Exception as e:
        pass
        
    try:
        res = xsmb_fetcher.fetch_and_save_daily(date)
        if res:
            return json.dumps({"success": True, "results": res}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Loi tai truc tiep tu web: {e}"}, ensure_ascii=False)
        
    return json.dumps({"success": False, "error": f"Khong tim thay ket qua XSMB cho ngay {date}."}, ensure_ascii=False)


def predict_xsmb(args: dict, **kwargs) -> str:
    last_days = args.get("last_days", 30)
    if last_days is None:
        last_days = 30
        
    xsmb_db.init_db()
    
    try:
        conn = sqlite3.connect(xsmb_db.DB_PATH)
        df_raw = pd.read_sql_query("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at ASC", conn)
        conn.close()
        
        if len(df_raw) == 0:
            return json.dumps({"success": False, "error": "Database trong!"}, ensure_ascii=False)
            
        processed_rows = []
        for _, row in df_raw.iterrows():
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
        
        # 1. Tính Monte Carlo & Pascal
        pascal_num, top_mc = pascal_mc.monte_carlo_with_pascal(df_processed, last_days=last_days)
        
        # 2. Tính CDM (Bayesian)
        expected_counts, alpha_0 = xsmb_cdm.cdm_prediction(xsmb_db.DB_PATH, last_days=last_days)
        top_cdm = np.argsort(expected_counts)[-10:][::-1]
        
        results = {
            "success": True,
            "last_days": last_days,
            "pascal_prediction": pascal_num,
            "top_monte_carlo": [
                {"number": f"{num:02d}", "probability": f"{count / 20000 * 100:.2f}%"}
                for num, count in top_mc[:10]
            ],
            "top_cdm": [
                {"number": f"{num:02d}", "expected_count": f"{expected_counts[num]:.4f}"}
                for num in top_cdm
            ],
            "cdm_alpha_0": f"{alpha_0:.4f}"
        }
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Loi du doan: {e}"}, ensure_ascii=False)


def register(ctx):
    ctx.register_tool(
        name="get_xsmb",
        toolset="xsmb",
        schema=XSMB_SCHEMA,
        handler=get_xsmb
    )
    ctx.register_tool(
        name="predict_xsmb",
        toolset="xsmb",
        schema=PREDICT_XSMB_SCHEMA,
        handler=predict_xsmb
    )
