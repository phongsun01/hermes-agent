import sys
import shutil
from pathlib import Path

def run_cleanup(processing_dir_path):
    processing_dir = Path(processing_dir_path)
    output_dir = processing_dir / "03.output"
    
    # Tìm file docx và md trong 03.output
    docx_files = list(output_dir.glob("*.docx"))
    md_files = list(output_dir.glob("*.md"))
    
    if not docx_files or not md_files:
        print("[WARN] Chưa có file DOCX hoặc MD trong 03.output/, không thể dọn dẹp an toàn.")
        return False
        
    print(f"[INFO] Đang dọn dẹp thư mục {processing_dir.name}...")
    
    # Xóa các thư mục trung gian
    for sub in ["01.input", "02.process"]:
        d = processing_dir / sub
        if d.exists() and d.is_dir():
            shutil.rmtree(d)
            print(f"  - Đã xóa thư mục {sub}/ và các file đệm")
    
    # Liệt kê file cuối cùng còn lại
    remaining = list(output_dir.iterdir())
    remaining_names = [f.name for f in remaining]
    
    print(f"[OK] Đã dọn dẹp xong.")
    print(f"  Thư mục 03.output/ chứa: {', '.join(remaining_names)}")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python cleanup.py <processing_dir>")
        sys.exit(1)
        
    run_cleanup(sys.argv[1])
