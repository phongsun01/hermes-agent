import urllib.request
import ssl
import re
import datetime
import sys
import os
import xsmb_db

ssl_ctx = ssl._create_unverified_context()

def fetch_html(date_str):
    """Tải mã HTML của ngày cụ thể từ trang xskt.com.vn."""
    url = f"https://xskt.com.vn/xsmb/ngay-{date_str}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as r:
            return r.read().decode('utf-8')
    except Exception as e:
        print(f"Loi ket noi tai ket qua ngay {date_str}: {e}")
        return None

def parse_xsmb(html):
    """Phân tích cú pháp HTML để trích xuất các giải."""
    if not html:
        return None
    
    results = {}
    
    # Tìm bảng kết quả
    table_match = re.search(r'<table[^>]+class="result"[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table_match:
        table_match = re.search(r'<table[^>]+id="MB0"[^>]*>(.*?)</table>', html, re.DOTALL)
        
    if not table_match:
        return None
        
    table_html = table_match.group(1)
    
    # Giải Đặc biệt
    db_match = re.search(r'ĐB</td><td><em>(\d+)</em>', table_html)
    if db_match:
        results['GDB'] = db_match.group(1).strip()
    else:
        return None
    
    # Giải 1 đến Giải 7
    for i in range(1, 8):
        pattern = rf'G{i}</td><td[^>]*><p>(.*?)</p>'
        g_match = re.search(pattern, table_html, re.DOTALL)
        if g_match:
            text = g_match.group(1)
            text = text.replace('<br>', ' ').replace('<br/>', ' ').replace('\n', ' ')
            text = ' '.join(text.split())
            results[f'G{i}'] = text
        else:
            results[f'G{i}'] = ""
            
    return results

def fetch_and_save_daily(date_str=None):
    """Hàm lấy kết quả và lưu cho ngày cụ thể (mặc định hôm nay)."""
    if not date_str:
        date_str = datetime.datetime.now().strftime("%d-%m-%Y")
        
    # Khởi tạo db nếu chưa có
    xsmb_db.init_db()
    
    print(f"Bat dau lay ket qua XSMB ngay {date_str}...")
    html = fetch_html(date_str)
    results = parse_xsmb(html)
    
    if results:
        success = xsmb_db.save_result(date_str, results)
        if success:
            print(f"--- KET QUA XSMB NGAY {date_str} ---")
            print(f"Dac Biet : {results.get('GDB')}")
            print(f"Giai Nhat: {results.get('G1')}")
            print(f"Giai Nhi : {results.get('G2')}")
            print(f"Giai Ba  : {results.get('G3')}")
            print(f"Giai Tu  : {results.get('G4')}")
            print(f"Giai Nam : {results.get('G5')}")
            print(f"Giai Sau : {results.get('G6')}")
            print(f"Giai Bay : {results.get('G7')}")
            print("---------------------------------")
            return results
        else:
            print(f"Loi luu tru ket qua ngay {date_str}")
    else:
        print(f"Khong the lay ket qua hoac chua co ket qua cho ngay {date_str}.")
    return None

if __name__ == '__main__':
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_and_save_daily(target_date)
