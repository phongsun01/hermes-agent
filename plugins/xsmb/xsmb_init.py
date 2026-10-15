import datetime
import time
import xsmb_db
import xsmb_fetcher

def initialize_june_2026():
    """Khởi tạo dữ liệu XSMB từ ngày 01/06/2026 đến 30/06/2026."""
    # 1. Khởi tạo database
    xsmb_db.init_db()
    
    start_date = datetime.date(2026, 6, 1)
    end_date = datetime.date(2026, 6, 30)
    
    current_date = start_date
    delta = datetime.timedelta(days=1)
    
    success_count = 0
    fail_count = 0
    
    print(f"Bat dau tai du lieu lich su tu {start_date.strftime('%d/%m/%Y')} den {end_date.strftime('%d/%m/%Y')}...")
    
    while current_date <= end_date:
        date_str = current_date.strftime("%d-%m-%Y")
        
        # Thử lấy và lưu kết quả
        try:
            res = xsmb_fetcher.fetch_and_save_daily(date_str)
            if res:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"Loi khong xac dinh khi lay du lieu ngay {date_str}: {e}")
            fail_count += 1
            
        # Tăng ngày và nghỉ 1 giây để tránh spam server
        current_date += delta
        time.sleep(1.0)
        
    print("\n=========================================")
    print("HOAN THANH QUA TRINH KHOI TAO LICH SU THANG 6/2026")
    print(f"Thanh cong: {success_count}/{success_count + fail_count} ngay.")
    print("=========================================")

if __name__ == '__main__':
    initialize_june_2026()
