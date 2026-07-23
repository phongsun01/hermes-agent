import sqlite3
import pandas as pd
import numpy as np
from collections import Counter
import os

def pascal_prediction(db: int, g1: int):
    """Tính cầu Pascal"""
    s = str(db).zfill(5) + str(g1).zfill(5)
    digits = [int(c) for c in s]
    steps = []
    while len(digits) > 2:
        steps.append(digits[:])
        new_digits = [ (digits[i] + digits[i+1]) % 10 for i in range(len(digits)-1) ]
        digits = new_digits
    return f"{digits[0]}{digits[1]}", steps

def monte_carlo_with_pascal(df, last_days=30, simulations=20000):
    recent = df.tail(last_days)
    
    # 1. Pascal từ kỳ gần nhất
    latest_db = int(recent.iloc[-1]['special']) if 'special' in recent.columns else int(recent.iloc[-1].iloc[1])
    latest_g1 = int(recent.iloc[-1].iloc[2])  # Giả sử cột thứ 2 là G1
    pascal_num, _ = pascal_prediction(latest_db, latest_g1)
    pascal_int = int(pascal_num)
    
    # 2. Phân phối từ 30 ngày
    all_2digits = []
    for col in recent.columns[1:]:
        series = pd.to_numeric(recent[col].astype(str).str.zfill(5).str[-2:], errors='coerce')
        all_2digits.extend(series.dropna().astype(int).tolist())
    
    freq = Counter(all_2digits)
    numbers = np.arange(100)
    weights = np.array([freq.get(n, 1) for n in numbers], dtype=float)
    weights = weights / weights.sum()
    
    # 3. Monte Carlo simulation
    simulated = np.random.choice(numbers, size=simulations, p=weights)
    sim_freq = Counter(simulated)
    
    # 4. Kết hợp: Ưu tiên Pascal + top MC
    top_mc = sim_freq.most_common(15)
    
    print(f"Pascal tu ky gan nhat: {pascal_num}")
    print("Top 10 Monte Carlo (dua tren 30 ngay):")
    for num, count in top_mc[:10]:
        prob = count / simulations * 100
        mark = " <- Pascal match!" if num == pascal_int else ""
        print(f"  {num:02d}: {prob:.2f}%{mark}")
    
    return pascal_num, top_mc

def run_prediction():
    db_path = os.path.join(os.path.dirname(__file__), "xsmb_results.db")
    if not os.path.exists(db_path):
        print(f"Database khong ton tai tai {db_path}!")
        return
        
    conn = sqlite3.connect(db_path)
    df_raw = pd.read_sql_query("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at ASC", conn)
    conn.close()
    
    if len(df_raw) == 0:
        print("Database rong!")
        return
        
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
    
    print(f"Da load {len(df_processed)} ngay du lieu tu SQLite.")
    pascal, top = monte_carlo_with_pascal(df_processed)

if __name__ == '__main__':
    run_prediction()
