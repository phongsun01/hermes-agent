"""
core_merge_md.py — Hợp nhất các file MD riêng lẻ thành MERGED.md.
Hỗ trợ cả văn bản thuần (prose) và bảng (table).
Thêm page separator <!-- page: N --> để truy vết nguồn.

Usage:
    python core_merge_md.py <thư_mục_processing>
"""
import os
import sys
import glob
import re
from pathlib import Path


def merge_md(processing_dir):
    process_dir = os.path.join(processing_dir, "02.process")
    output_dir = os.path.join(processing_dir, "03.output")

    if not os.path.exists(process_dir):
        print(f"[FAIL] Không tìm thấy thư mục 02.process: {process_dir}")
        return None

    # Tìm tất cả file MD, sắp xếp theo số trang
    md_files = sorted(glob.glob(os.path.join(process_dir, "page_*.png.md")))
    if not md_files:
        print("[FAIL] Không tìm thấy file .md nào trong 02.process/")
        return None

    os.makedirs(output_dir, exist_ok=True)
    merged_md_path = os.path.join(processing_dir, "02.process", "MERGED.md")

    merged_lines = []
    skipped = 0

    for fpath in md_files:
        fname = os.path.basename(fpath)

        # Trích xuất số trang từ tên file (page_001.png.md → 1)
        match = re.search(r"page_(\d+)", fname)
        page_num = int(match.group(1)) if match else "?"

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except (UnicodeDecodeError, IOError) as e:
            print(f"  [WARN] Bỏ qua {fname} — lỗi đọc file: {e}")
            skipped += 1
            continue

        if not content:
            print(f"  [WARN] Bỏ qua {fname} — file rỗng")
            skipped += 1
            continue

        # Thêm page separator
        merged_lines.append(f"\n<!-- page: {page_num} -->\n")
        merged_lines.append(content)

    # Ghi file
    final_content = "\n\n".join(merged_lines).strip()
    with open(merged_md_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    total = len(md_files)
    merged = total - skipped
    print(f"[OK] Đã hợp nhất {merged}/{total} file MD.")
    if skipped:
        print(f"  [WARN] Bỏ qua {skipped} file lỗi/rỗng.")
    print(f"[OK] File kết quả: {merged_md_path}")
    return merged_md_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python core_merge_md.py <thư_mục_processing>")
        sys.exit(1)

    result = merge_md(sys.argv[1])
    if result is None:
        sys.exit(1)
