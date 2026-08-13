"""
extract_images.py — Trích xuất ảnh minh họa từ PDF gốc.
Ưu tiên: extract ảnh nhúng gốc (chất lượng 100%).
Fallback: crop từ page render bằng PIL.

Usage:
    python extract_images.py <thư_mục_processing>
"""
import fitz
import json
import sys
import os
from pathlib import Path


def extract_embedded_images(doc, images_dir, min_size=50):
    """Trích xuất ảnh nhúng (embedded) từ PDF — chất lượng gốc 100%."""
    image_map = []
    seen_xrefs = set()

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        img_list = page.get_images(full=True)

        img_count = 0
        for img in img_list:
            xref = img[0]

            # Tránh trùng lặp (cùng 1 ảnh xuất hiện nhiều trang)
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                img_info = doc.extract_image(xref)
                w = img_info["width"]
                h = img_info["height"]

                # Bỏ qua ảnh quá nhỏ (icon, dot)
                if w < min_size or h < min_size:
                    continue

                ext = img_info.get("ext", "png")
                img_bytes = img_info["image"]

                filename = f"img_p{page_idx + 1}_{img_count}.{ext}"
                filepath = images_dir / filename

                with open(str(filepath), "wb") as f:
                    f.write(img_bytes)

                # Lấy bbox trên trang
                try:
                    bbox = page.get_image_bbox(img)
                    bbox_list = [round(x, 1) for x in bbox]
                    width_pt = round(bbox.width, 1)
                    height_pt = round(bbox.height, 1)
                except Exception:
                    bbox_list = [0, 0, w, h]
                    width_pt = w
                    height_pt = h

                image_map.append({
                    "filename": filename,
                    "page": page_idx + 1,
                    "bbox": bbox_list,
                    "width_pt": width_pt,
                    "height_pt": height_pt,
                    "width_px": w,
                    "height_px": h,
                    "method": "extract"
                })

                img_count += 1

            except Exception as e:
                print(f"  [WARN] Không extract được ảnh xref={xref} trang {page_idx + 1}: {e}")
                continue

    return image_map


def crop_from_render(processing_dir, images_dir, format_spec_images, min_size=50):
    """Fallback: crop ảnh từ page render bằng PIL (khi không có ảnh nhúng)."""
    from PIL import Image

    input_dir = Path(processing_dir) / "input"
    image_map = []

    for img_info in format_spec_images:
        page_num = img_info["page"]
        bbox = img_info["bbox"]

        # Tìm file ảnh render tương ứng
        render_file = input_dir / f"page_{page_num:03d}.png"
        if not render_file.exists():
            print(f"  [WARN] Không tìm thấy render page {page_num}")
            continue

        try:
            render_img = Image.open(str(render_file))
            rw, rh = render_img.size

            # Chuyển bbox từ pt sang pixel (ước lượng dựa trên render size)
            # PDF page thường 595x842 pt (A4)
            # Render ở DPI cao → phải scale bbox
            # Giả sử render tỷ lệ đều
            original_pdf_width_pt = img_info.get("page_width_pt", 595)
            scale = rw / original_pdf_width_pt if original_pdf_width_pt > 0 else 1

            crop_box = (
                int(bbox[0] * scale),
                int(bbox[1] * scale),
                int(bbox[2] * scale),
                int(bbox[3] * scale)
            )

            # Đảm bảo crop box hợp lệ
            crop_box = (
                max(0, crop_box[0]),
                max(0, crop_box[1]),
                min(rw, crop_box[2]),
                min(rh, crop_box[3])
            )

            crop_w = crop_box[2] - crop_box[0]
            crop_h = crop_box[3] - crop_box[1]

            if crop_w < min_size or crop_h < min_size:
                continue

            cropped = render_img.crop(crop_box)
            filename = f"img_p{page_num}_crop.png"
            filepath = images_dir / filename
            cropped.save(str(filepath))

            image_map.append({
                "filename": filename,
                "page": page_num,
                "bbox": [round(x, 1) for x in bbox],
                "width_pt": round(bbox[2] - bbox[0], 1),
                "height_pt": round(bbox[3] - bbox[1], 1),
                "width_px": crop_w,
                "height_px": crop_h,
                "method": "crop"
            })

        except Exception as e:
            print(f"  [WARN] Crop lỗi trang {page_num}: {e}")
            continue

    return image_map


def extract_images(processing_dir):
    processing_dir = Path(processing_dir)
    input_dir = processing_dir / "01.input"
    process_dir = processing_dir / "02.process"
    input_dir.mkdir(parents=True, exist_ok=True)
    # Đọc đường dẫn PDF gốc từ source.txt
    source_txt = process_dir / "source.txt"
    if source_txt.exists():
        with open(str(source_txt), "r", encoding="utf-8") as f:
            original_pdf = Path(f.read().strip())
    else:
        dir_name = processing_dir.name
        if dir_name.endswith("_processing"):
            pdf_name = dir_name[:-len("_processing")] + ".pdf"
            original_pdf = processing_dir.parent / pdf_name
        else:
            original_pdf = None

    if original_pdf is None or not original_pdf.exists():
        print(f"[FAIL] Không tìm thấy PDF gốc. Kiểm tra source.txt hoặc đặt file PDF cùng thư mục.")
        return None

    doc = fitz.open(str(original_pdf))

    # Ưu tiên: extract ảnh nhúng
    print("[INFO] Thử trích xuất ảnh nhúng (embedded)...")
    image_map = extract_embedded_images(doc, input_dir)

    if image_map:
        print(f"[OK] Trích xuất {len(image_map)} ảnh nhúng.")
    else:
        print("[INFO] Không có ảnh nhúng. Thử crop từ render...")

        # Đọc format_spec để lấy vị trí ảnh
        spec_path = process_dir / "format_spec.json"
        if spec_path.exists():
            with open(str(spec_path), "r", encoding="utf-8") as f:
                spec = json.load(f)
            if spec.get("images"):
                image_map = crop_from_render(
                    processing_dir, input_dir, spec["images"]
                )
                print(f"[OK] Crop {len(image_map)} ảnh từ render.")
            else:
                print("[INFO] Không phát hiện vùng ảnh nào trong tài liệu.")
        else:
            print("[WARN] Chưa có format_spec.json. Chạy analyze_format.py trước.")

    doc.close()

    # Lưu image_map.json vào 02.process
    map_path = process_dir / "image_map.json"
    with open(str(map_path), "w", encoding="utf-8") as f:
        json.dump(image_map, f, ensure_ascii=False, indent=2)

    print(f"[OK] Image map: {map_path}")
    print(f"[OK] Tổng: {len(image_map)} ảnh minh họa.")
    return str(map_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python extract_images.py <thư_mục_processing>")
        sys.exit(1)

    result = extract_images(sys.argv[1])
    if result is None:
        sys.exit(1)
