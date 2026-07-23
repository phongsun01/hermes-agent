import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "xsmb_results.db")

def init_db():
    """Khởi tạo cơ sở dữ liệu SQLite và bảng chứa kết quả xổ số."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS xsmb (
        ngay TEXT PRIMARY KEY,
        gdb TEXT,
        g1 TEXT,
        g2 TEXT,
        g3 TEXT,
        g4 TEXT,
        g5 TEXT,
        g6 TEXT,
        g7 TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
    print(f"Khoi tao database thanh cong tai: {DB_PATH}")

def save_result(ngay, results):
    """
    Lưu kết quả xổ số của một ngày vào database.
    results: dict chứa các trường GDB, G1, G2, ..., G7
    """
    if not results:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT OR REPLACE INTO xsmb (ngay, gdb, g1, g2, g3, g4, g5, g6, g7)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ngay,
            results.get("GDB"),
            results.get("G1"),
            results.get("G2"),
            results.get("G3"),
            results.get("G4"),
            results.get("G5"),
            results.get("G6"),
            results.get("G7")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Loi khi luu du lieu ngay {ngay}: {e}")
        return False
    finally:
        conn.close()

def get_result(ngay):
    """Lấy kết quả xổ số của một ngày."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb WHERE ngay = ?", (ngay,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "Ngay": ngay,
            "GDB": row[0],
            "G1": row[1],
            "G2": row[2],
            "G3": row[3],
            "G4": row[4],
            "G5": row[5],
            "G6": row[6],
            "G7": row[7]
        }
    return None
