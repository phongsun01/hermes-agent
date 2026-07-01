import json
import sys
import os
import datetime
import sqlite3
import pandas as pd

# Thêm thư mục scripts/xsmb vào path để import
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_xsmb_path = os.path.abspath(os.path.join(current_dir, "..", "scripts", "xsmb"))
if scripts_xsmb_path not in sys.path:
    sys.path.insert(0, scripts_xsmb_path)

import xsmb_db
import xsmb_fetcher
import pascal_mc

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
        "Thực hiện dự đoán cầu Pascal kết hợp mô phỏng Monte Carlo dựa trên dữ liệu lịch sử N ngày gần nhất (mặc định 30 ngày)."
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

def get_xsmb_tool(date: str = None, limit_days: int = None) -> str:
    # Đảm bảo database đã được khởi tạo
    xsmb_db.init_db()
    
    # 1. Truy vấn nhiều ngày để làm thống kê
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
            return json.dumps({"success": False, "error": f"Lỗi truy vấn danh sách: {e}"}, ensure_ascii=False)
            
    # 2. Truy vấn một ngày duy nhất
    if not date:
        date = datetime.datetime.now().strftime("%d-%m-%Y")
        
    date = date.replace("/", "-")
    
    try:
        res = xsmb_db.get_result(date)
        if res:
            return json.dumps({"success": True, "results": res}, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi đọc DB: {e}")
        
    try:
        res = xsmb_fetcher.fetch_and_save_daily(date)
        if res:
            return json.dumps({"success": True, "results": res}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Lỗi tải trực tiếp từ web: {e}"}, ensure_ascii=False)
        
    return json.dumps({"success": False, "error": f"Không tìm thấy kết quả XSMB cho ngày {date}."}, ensure_ascii=False)


def predict_xsmb_tool(last_days: int = 30) -> str:
    xsmb_db.init_db()
    
    if last_days is None:
        last_days = 30
        
    try:
        conn = sqlite3.connect(xsmb_db.DB_PATH)
        df_raw = pd.read_sql_query("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at ASC", conn)
        conn.close()
        
        if len(df_raw) == 0:
            return json.dumps({"success": False, "error": "Database trống!"}, ensure_ascii=False)
            
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
        
        pascal_num, top_mc = pascal_mc.monte_carlo_with_pascal(df_processed, last_days=last_days)
        
        results = {
            "success": True,
            "last_days": last_days,
            "pascal_prediction": pascal_num,
            "top_monte_carlo": [
                {"number": f"{num:02d}", "probability": f"{count / 20000 * 100:.2f}%"}
                for num, count in top_mc[:10]
            ]
        }
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Lỗi dự đoán: {e}"}, ensure_ascii=False)


# --- Đăng ký Tool với hệ thống ---
from tools.registry import registry

registry.register(
    name="get_xsmb",
    toolset="xsmb",
    schema=XSMB_SCHEMA,
    handler=lambda args, **kw: get_xsmb_tool(
        date=args.get("date"),
        limit_days=args.get("limit_days")
    ),
    check_fn=lambda: True,
    emoji="🎫"
)

registry.register(
    name="predict_xsmb",
    toolset="xsmb",
    schema=PREDICT_XSMB_SCHEMA,
    handler=lambda args, **kw: predict_xsmb_tool(
        last_days=args.get("last_days", 30)
    ),
    check_fn=lambda: True,
    emoji="🔮"
)
