"""
core_pdf_to_images.py — Render PDF thành ảnh chất lượng cao.
Tự phát hiện DPI gốc của ảnh nhúng. Có memory protection cho file lớn.

Usage:
    python core_pdf_to_images.py <đường_dẫn_file_pdf> [--dpi N]
"""
import fitz  # PyMuPDF
import sys
import os
import shutil
import argparse
from pathlib import Path


def detect_native_dpi(doc, max_pages_to_scan=3):
    """Tính DPI gốc của ảnh nhúng trong PDF scan.
    Quét vài trang đầu, lấy DPI cao nhất tìm thấy.
    """
    detected_dpi = 0
    for page_idx in range(min(max_pages_to_scan, len(doc))):
        page = doc[page_idx]
        images = page.get_images(full=True)
        for img in images:
            xref = img[0]
            try:
                bbox = page.get_image_bbox(img)
                if bbox.is_empty or bbox.width <= 0 or bbox.height <= 0:
                    continue
                img_info = doc.extract_image(xref)
                w = img_info["width"]
                h = img_info["height"]
                dpi_x = (w / bbox.width) * 72
                dpi_y = (h / bbox.height) * 72
                detected_dpi = max(detected_dpi, dpi_x, dpi_y)
            except Exception:
                continue
    return detected_dpi


def setup_and_render(pdf_path, forced_dpi=None):
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        print(f"[FAIL] Không tìm thấy file: {pdf_path}")
        return None

    # Khởi tạo cây thư mục
    base_dir = pdf_path.parent / f"{pdf_path.stem}_processing"
    input_dir = base_dir / "01.input"
    process_dir = base_dir / "02.process"
    output_dir = base_dir / "03.output"

    for d in [input_dir, process_dir, output_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Lưu đường dẫn PDF gốc để các script khác tham chiếu
    source_txt = process_dir / "source.txt"
    if not source_txt.exists():
        with open(str(source_txt), "w", encoding="utf-8") as f:
            f.write(str(pdf_path))

    print(f"[INFO] Cây thư mục: {base_dir}")

    # Mở PDF
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"[FAIL] Không mở được PDF: {e}")
        return None

    total_pages = len(doc)
    page_size = doc[0].rect if total_pages > 0 else None

    # Xác định DPI
    if forced_dpi:
        render_dpi = min(forced_dpi, 600)
        dpi_source = f"override ({forced_dpi} → cap {render_dpi})"
    else:
        native_dpi = detect_native_dpi(doc)
        if native_dpi > 100:
            render_dpi = min(int(native_dpi), 600)
            dpi_source = f"native ({int(native_dpi)} → cap {render_dpi})"
        else:
            render_dpi = 300
            dpi_source = "fallback (300 — không phát hiện ảnh nhúng)"

    # Metadata
    print(f"[INFO] Số trang: {total_pages}")
    if page_size:
        print(f"[INFO] Kích thước trang: {page_size.width:.0f} x {page_size.height:.0f} pt")
    print(f"[INFO] DPI render: {render_dpi} ({dpi_source})")

    # Render từng trang
    zoom = render_dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    batch_size = 50  # Memory protection: shrink cache mỗi batch

    image_paths = []
    for i in range(total_pages):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        output_file = input_dir / f"page_{i+1:03d}.png"
        pix.save(str(output_file))
        image_paths.append(str(output_file))

        # Memory protection: shrink cache mỗi batch
        if (i + 1) % batch_size == 0:
            fitz.TOOLS.store_shrink(100)
            print(f"  ... đã render {i+1}/{total_pages} trang")

    doc.close()
    fitz.TOOLS.store_shrink(100)  # Clean up cuối

    print(f"\n[OK] Đã render {len(image_paths)} ảnh tại: {input_dir}")
    print(f"[OK] Thư mục process (lưu MD): {process_dir}")
    print(f"[OK] Thư mục output: {output_dir}")
    print(f"[OK] DPI: {render_dpi}")
    return str(base_dir)


def main():
    parser = argparse.ArgumentParser(description="Render PDF thành ảnh chất lượng cao")
    parser.add_argument("pdf_path", help="Đường dẫn file PDF")
    parser.add_argument("--dpi", type=int, default=None,
                        help="Override DPI (mặc định: tự phát hiện, cap 600)")
    args = parser.parse_args()

    result = setup_and_render(args.pdf_path, forced_dpi=args.dpi)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
