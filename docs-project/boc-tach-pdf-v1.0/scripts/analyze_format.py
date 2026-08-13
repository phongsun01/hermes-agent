"""
analyze_format.py — Phân tích format PDF gốc → format_spec.json.
v3: Thêm nhận diện loại văn bản (NĐ 30 / VB dài) + phát hiện page orientation.

Usage:
    python analyze_format.py <thư_mục_processing>
"""
import fitz
import json
import sys
import os
import re
import glob
from pathlib import Path
from collections import Counter


def is_scanned_page(page, threshold=40):
    """Kiểm tra trang có phải scan thuần (không text layer) không."""
    text = page.get_text("text").strip()
    return len(text) < threshold


def detect_doc_type(processing_dir):
    """Phát hiện loại văn bản từ nội dung OCR trong process/*.md.
    
    Returns:
        str: "hanh_chinh_nd30" | "van_ban_dai"
    """
    process_dir = Path(processing_dir) / "02.process"
    if not process_dir.exists():
        return "van_ban_dai"
    
    # Chỉ cần đọc 3-5 trang đầu để phát hiện
    md_files = sorted(process_dir.glob("*.md"))[:5]
    combined_text = ""
    for md_file in md_files:
        try:
            with open(str(md_file), "r", encoding="utf-8") as f:
                combined_text += f.read() + "\n"
        except Exception:
            continue
    
    if not combined_text:
        return "van_ban_dai"
    
    # Pattern nhận diện VB hành chính NĐ 30
    nd30_patterns = [
        r"CỘNG\s+H[OÒ]A?\s+X[AÃ]\s+H[OỘ]I\s+CH[UỦ]\s+NGH[IĨ]A\s+VI[EỆ]T\s+NAM",
        r"Đ[oộ]c\s+l[aậ]p\s*[-–—]\s*T[uự]\s+do\s*[-–—]\s*H[aạ]nh\s+ph[uú]c",
        r"[UỦ]Y?\s*BAN\s+NH[AÂ]N\s+D[AÂ]N",
        r"S[oố]\s*:\s*\d+\s*/",
        r"K[ií]nh\s+g[uử]i\s*:",
        r"T[OỜ]\s+TR[IÌ]NH",
        r"QUYẾT\s+ĐỊNH",
        r"CÔNG\s+VĂN",
        r"THÔNG\s+BÁO",
        r"BÁO\s+CÁO",
        r"KẾ\s+HOẠCH",
        r"BIÊN\s+BẢN",
        r"N[oơ]i\s+nh[aậ]n\s*:",
    ]
    
    match_count = 0
    for pattern in nd30_patterns:
        if re.search(pattern, combined_text, re.IGNORECASE):
            match_count += 1
    
    # Cần ít nhất 3 pattern match để xác nhận NĐ 30
    if match_count >= 3:
        return "hanh_chinh_nd30"
    
    return "van_ban_dai"


def detect_page_orientations(doc):
    """Phát hiện page orientation dựa vào kích thước mỗi trang.
    
    Returns:
        dict: {page_num: "landscape"} — chỉ ghi các trang landscape.
              Trang portrait không ghi (mặc định).
    """
    orientations = {}
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        rect = page.rect
        # Nếu width > height → landscape
        if rect.width > rect.height:
            orientations[page_idx + 1] = "landscape"
    return orientations


def get_nd30_defaults():
    """Trả về format spec mặc định theo chuẩn NĐ 30/2020."""
    return {
        "body_font": "Times New Roman",
        "body_font_size": 13.0,
        "heading_font_size": 13.0,  # NĐ 30: heading cùng cỡ body, phân cấp bằng bold/IN HOA
        "margins_pt": {
            "top": 57,      # 20mm
            "bottom": 57,   # 20mm
            "left": 85,     # 30mm
            "right": 57     # 20mm
        },
        "first_line_indent_pt": 28,  # ~1cm
        "line_spacing": 1.5,
        "text_color": "000000",  # Đen thuần
    }


def analyze_with_text_layer(doc):
    """Nhánh A: PDF có text layer — trích xuất chính xác."""
    fonts_counter = Counter()
    font_sizes = []
    all_x0 = []
    all_y_gaps = []
    headings = []
    images_info = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]

        # Trích xuất text blocks
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # Text block
                for line in block.get("lines", []):
                    prev_span_bottom = None
                    for span in line.get("spans", []):
                        font_name = span.get("font", "Unknown")
                        font_size = round(span.get("size", 12), 1)
                        flags = span.get("flags", 0)
                        text = span.get("text", "").strip()
                        bbox = span.get("bbox", [0, 0, 0, 0])

                        if text:
                            fonts_counter[(font_name, font_size)] += len(text)
                            font_sizes.append(font_size)
                            all_x0.append(bbox[0])

                            # Phát hiện heading: font size lớn hoặc bold
                            is_bold = bool(flags & 2**4)
                            if len(text) > 3:
                                headings.append({
                                    "text": text[:80],
                                    "page": page_idx + 1,
                                    "font_size": font_size,
                                    "bold": is_bold,
                                    "font": font_name
                                })

                    # Tính line spacing
                    line_bbox = line.get("bbox", [0, 0, 0, 0])
                    if prev_span_bottom is not None:
                        gap = line_bbox[1] - prev_span_bottom
                        if 0 < gap < 50:
                            all_y_gaps.append(gap)
                    prev_span_bottom = line_bbox[3]

            elif block["type"] == 1:  # Image block
                bbox = block.get("bbox", [0, 0, 0, 0])
                images_info.append({
                    "page": page_idx + 1,
                    "bbox": [round(x, 1) for x in bbox],
                    "width_pt": round(bbox[2] - bbox[0], 1),
                    "height_pt": round(bbox[3] - bbox[1], 1)
                })

    # Phân tích kết quả
    # Font chính = font dùng nhiều ký tự nhất
    if fonts_counter:
        body_font = fonts_counter.most_common(1)[0][0]
        body_font_name = body_font[0]
        body_font_size = body_font[1]
    else:
        body_font_name = "Times New Roman"
        body_font_size = 13.0

    # Heading font = font size lớn nhất (khác body)
    heading_candidates = [h for h in headings if h["font_size"] > body_font_size + 1]
    heading_font_size = max((h["font_size"] for h in heading_candidates), default=body_font_size + 2)

    # Margin từ min x0
    left_margin_pt = min(all_x0) if all_x0 else 85  # ~30mm
    page_rect = doc[0].rect
    right_margin_pt = page_rect.width - max(all_x0) if all_x0 else 57  # ~20mm
    top_margin_pt = 57  # Ước lượng mặc định ~20mm
    bottom_margin_pt = 57

    # First-line indent
    if len(all_x0) > 10:
        sorted_x0 = sorted(all_x0)
        # Indent = khoảng cách phổ biến thứ 2 trừ phổ biến nhất
        x0_counter = Counter([round(x, 0) for x in all_x0])
        common_x0 = x0_counter.most_common(2)
        if len(common_x0) >= 2:
            indent_pt = abs(common_x0[0][0] - common_x0[1][0])
        else:
            indent_pt = 36  # ~12.7mm mặc định
    else:
        indent_pt = 36

    # Line spacing
    if font_sizes and all_y_gaps:
        avg_font = sum(font_sizes) / len(font_sizes)
        avg_gap = sum(all_y_gaps) / len(all_y_gaps)
        line_spacing = round((avg_gap + avg_font) / avg_font, 1) if avg_font > 0 else 1.5
    else:
        line_spacing = 1.5

    return {
        "source": "text_layer",
        "body_font": body_font_name,
        "body_font_size": body_font_size,
        "heading_font_size": heading_font_size,
        "margins_pt": {
            "top": round(top_margin_pt, 1),
            "bottom": round(bottom_margin_pt, 1),
            "left": round(left_margin_pt, 1),
            "right": round(right_margin_pt, 1)
        },
        "first_line_indent_pt": round(indent_pt, 1),
        "line_spacing": min(max(line_spacing, 1.0), 3.0),
        "page_width_pt": round(page_rect.width, 1),
        "page_height_pt": round(page_rect.height, 1),
        "images": images_info,
        "headings_sample": heading_candidates[:10]
    }


def analyze_scan_estimate(doc):
    """Nhánh B: PDF scan thuần — ước lượng từ ảnh nhúng + default."""
    images_info = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        img_list = page.get_images(full=True)
        for img_idx, img in enumerate(img_list):
            xref = img[0]
            try:
                bbox = page.get_image_bbox(img)
                if not bbox.is_empty:
                    images_info.append({
                        "page": page_idx + 1,
                        "bbox": [round(x, 1) for x in bbox],
                        "width_pt": round(bbox.width, 1),
                        "height_pt": round(bbox.height, 1)
                    })
            except Exception:
                continue

    page_rect = doc[0].rect

    return {
        "source": "scan_estimate",
        "body_font": "Times New Roman",
        "body_font_size": 13.0,
        "heading_font_size": 15.0,
        "margins_pt": {
            "top": 57,    # ~20mm
            "bottom": 57,
            "left": 85,   # ~30mm
            "right": 57
        },
        "first_line_indent_pt": 36,  # ~12.7mm
        "line_spacing": 1.5,
        "page_width_pt": round(page_rect.width, 1),
        "page_height_pt": round(page_rect.height, 1),
        "images": images_info,
        "headings_sample": []
    }


def analyze_format(processing_dir):
    processing_dir = Path(processing_dir)
    process_dir = processing_dir / "02.process"
    process_dir.mkdir(parents=True, exist_ok=True)
    # Đọc đường dẫn PDF gốc từ source.txt
    source_txt = processing_dir / "02.process" / "source.txt"
    if source_txt.exists():
        with open(str(source_txt), "r", encoding="utf-8") as f:
            original_pdf = Path(f.read().strip())
    else:
        # Fallback: tìm file PDF cùng tên trong thư mục cha
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

    # === 1. Phát hiện loại PDF (scan vs text layer) ===
    scanned_pages = sum(1 for i in range(min(5, len(doc))) if is_scanned_page(doc[i]))
    total_check = min(5, len(doc))
    is_scan = scanned_pages > total_check / 2

    if is_scan:
        print(f"[INFO] Phát hiện: PDF scan thuần ({scanned_pages}/{total_check} trang không có text)")
        print(f"[INFO] Sử dụng giá trị ước lượng mặc định.")
        result = analyze_scan_estimate(doc)
    else:
        print(f"[INFO] Phát hiện: PDF có text layer ({total_check - scanned_pages}/{total_check} trang có text)")
        print(f"[INFO] Trích xuất font, margin, spacing từ text layer.")
        result = analyze_with_text_layer(doc)

    # === 2. Phát hiện loại văn bản (NĐ 30 hay VB dài) ===
    doc_type = detect_doc_type(processing_dir)
    result["doc_type"] = doc_type
    print(f"\n[INFO] Loại văn bản: {doc_type}")

    if doc_type == "hanh_chinh_nd30":
        print(f"[INFO] Áp dụng tiêu chuẩn NĐ 30/2020:")
        nd30 = get_nd30_defaults()
        result["body_font"] = nd30["body_font"]
        result["body_font_size"] = nd30["body_font_size"]
        result["heading_font_size"] = nd30["heading_font_size"]
        result["margins_pt"] = nd30["margins_pt"]
        result["first_line_indent_pt"] = nd30["first_line_indent_pt"]
        result["line_spacing"] = nd30["line_spacing"]
        result["text_color"] = nd30["text_color"]
        print(f"  Font: {nd30['body_font']} {nd30['body_font_size']}pt")
        print(f"  Margin: T20 B20 L30 R20 (mm)")
        print(f"  Line spacing: {nd30['line_spacing']}")
        print(f"  Color: đen thuần (#{nd30['text_color']})")

    # === 3. Phát hiện page orientation ===
    orientations = detect_page_orientations(doc)
    result["page_orientations"] = orientations

    if orientations:
        landscape_pages = sorted(orientations.keys())
        print(f"\n[INFO] Trang landscape: {landscape_pages}")
    else:
        print(f"\n[INFO] Tất cả trang đều portrait.")

    doc.close()

    # === 4. Lưu format_spec.json ===
    spec_path = process_dir / "format_spec.json"
    with open(str(spec_path), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Format spec:")
    print(f"  Doc type: {result['doc_type']}")
    print(f"  Font: {result['body_font']} {result['body_font_size']}pt")
    print(f"  Heading: {result['heading_font_size']}pt")
    print(f"  Line spacing: {result['line_spacing']}")
    print(f"  Indent: {result['first_line_indent_pt']}pt")
    print(f"  Ảnh minh họa: {len(result['images'])} vùng")
    print(f"  Nguồn: {result['source']}")
    print(f"[OK] Lưu tại: {spec_path}")
    return str(spec_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python analyze_format.py <thư_mục_processing>")
        sys.exit(1)

    result = analyze_format(sys.argv[1])
    if result is None:
        sys.exit(1)
