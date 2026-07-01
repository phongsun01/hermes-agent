"""
generate_reference.py — Tạo reference.docx template từ format_spec.json.
v3: Phân nhánh NĐ 30 (đen trắng, chuẩn hành chính) vs VB dài (tùy biến).

Usage:
    python generate_reference.py <thư_mục_processing>
"""
import json
import sys
import os
from pathlib import Path

from docx import Document
from docx.shared import Pt, Mm, Cm
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_LINE_SPACING, WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml


def pt_to_mm(pt_val):
    """Chuyển điểm (point) sang mm."""
    return pt_val * 25.4 / 72


def set_font_all(style, font_name='Times New Roman'):
    """Set font on both run properties and eastAsia/cs."""
    style.font.name = font_name
    rpr = style.element.find(qn('w:rPr'))
    if rpr is None:
        rpr = parse_xml(f'<w:rPr {nsdecls("w")}/>')
        style.element.append(rpr)
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = parse_xml(f'<w:rFonts {nsdecls("w")}/>')
        rpr.insert(0, rfonts)
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rfonts.set(qn(attr), font_name)


def generate_nd30_reference(doc, spec):
    """Tạo reference.docx theo chuẩn NĐ 30/2020 — đen trắng, nghiêm túc."""
    body_font = spec.get("body_font", "Times New Roman")
    body_size = spec.get("body_font_size", 13.0)
    line_spacing = spec.get("line_spacing", 1.5)
    indent_pt = spec.get("first_line_indent_pt", 28)

    # --- Margins NĐ 30: T20 B20 L30 R20 ---
    for section in doc.sections:
        section.top_margin = Mm(20)
        section.bottom_margin = Mm(20)
        section.left_margin = Mm(30)
        section.right_margin = Mm(20)
        section.page_width = Mm(210)
        section.page_height = Mm(297)

    # --- Normal: body text NĐ 30 ---
    style_normal = doc.styles["Normal"]
    set_font_all(style_normal, body_font)
    style_normal.font.size = Pt(body_size)
    style_normal.font.bold = False
    style_normal.font.color.rgb = None  # Đen mặc định
    pf = style_normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing = line_spacing
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)
    if indent_pt > 5:
        pf.first_line_indent = Pt(indent_pt)

    # --- Body Text ---
    try:
        style_body = doc.styles["Body Text"]
    except KeyError:
        style_body = doc.styles.add_style("Body Text", WD_STYLE_TYPE.PARAGRAPH)
    set_font_all(style_body, body_font)
    style_body.font.size = Pt(body_size)
    style_body.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    style_body.paragraph_format.line_spacing = line_spacing
    if indent_pt > 5:
        style_body.paragraph_format.first_line_indent = Pt(indent_pt)

    # --- Heading Styles (NĐ 30: cùng font, cùng size, phân cấp bằng bold/IN HOA) ---
    for level in range(1, 4):
        style_name = f"Heading {level}"
        try:
            style_h = doc.styles[style_name]
        except KeyError:
            continue

        set_font_all(style_h, body_font)
        style_h.font.size = Pt(body_size)  # Cùng cỡ body
        style_h.font.bold = True
        style_h.font.color.rgb = None  # Đen, không màu
        style_h.paragraph_format.space_before = Pt(6)
        style_h.paragraph_format.space_after = Pt(6)
        style_h.paragraph_format.first_line_indent = Pt(0)
        style_h.paragraph_format.line_spacing = line_spacing

        if level == 1:
            # H1: IN HOA bold, justify left
            style_h.paragraph_format.space_before = Pt(12)
            style_h.paragraph_format.space_after = Pt(6)
        elif level == 2:
            style_h.paragraph_format.space_before = Pt(6)
            style_h.paragraph_format.space_after = Pt(3)

    print(f"  [NĐ 30] Margin: T20 B20 L30 R20 mm")
    print(f"  [NĐ 30] Font: {body_font} {body_size}pt, đen thuần")
    print(f"  [NĐ 30] Heading: bold, cùng cỡ body, không màu")


def generate_vanban_dai_reference(doc, spec):
    """Tạo reference.docx cho văn bản dài (logic v2 cũ)."""
    body_font = spec.get("body_font", "Times New Roman")
    body_size = spec.get("body_font_size", 13.0)
    heading_size = spec.get("heading_font_size", 15.0)
    line_spacing = spec.get("line_spacing", 1.5)
    indent_pt = spec.get("first_line_indent_pt", 36)
    margins = spec.get("margins_pt", {})

    # Kiểm tra font subset → fallback
    if "+" in body_font:
        print(f"  [INFO] Font '{body_font}' là subset. Fallback → Times New Roman")
        body_font = "Times New Roman"

    # --- Margins ---
    for section in doc.sections:
        section.top_margin = Mm(pt_to_mm(margins.get("top", 57)))
        section.bottom_margin = Mm(pt_to_mm(margins.get("bottom", 57)))
        section.left_margin = Mm(pt_to_mm(margins.get("left", 85)))
        section.right_margin = Mm(pt_to_mm(margins.get("right", 57)))

        page_w = spec.get("page_width_pt", 595)
        page_h = spec.get("page_height_pt", 842)
        section.page_width = Mm(pt_to_mm(page_w))
        section.page_height = Mm(pt_to_mm(page_h))

    # --- Normal ---
    style_normal = doc.styles["Normal"]
    set_font_all(style_normal, body_font)
    style_normal.font.size = Pt(body_size)
    pf = style_normal.paragraph_format
    pf.line_spacing = line_spacing
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)
    if indent_pt > 5:
        pf.first_line_indent = Pt(indent_pt)

    # --- Body Text ---
    try:
        style_body = doc.styles["Body Text"]
    except KeyError:
        style_body = doc.styles.add_style("Body Text", WD_STYLE_TYPE.PARAGRAPH)
    set_font_all(style_body, body_font)
    style_body.font.size = Pt(body_size)
    style_body.paragraph_format.line_spacing = line_spacing
    if indent_pt > 5:
        style_body.paragraph_format.first_line_indent = Pt(indent_pt)

    # --- Heading Styles ---
    for level in range(1, 4):
        style_name = f"Heading {level}"
        try:
            style_h = doc.styles[style_name]
        except KeyError:
            continue

        size_offset = (3 - level) * 1
        set_font_all(style_h, body_font)
        style_h.font.size = Pt(heading_size + size_offset)
        style_h.font.bold = True
        style_h.paragraph_format.space_before = Pt(12)
        style_h.paragraph_format.space_after = Pt(6)
        style_h.paragraph_format.first_line_indent = Pt(0)


def generate_reference(processing_dir):
    processing_dir = Path(processing_dir)
    process_dir = processing_dir / "02.process"
    spec_path = process_dir / "format_spec.json"

    if not spec_path.exists():
        print(f"[FAIL] Không tìm thấy format_spec.json tại {process_dir}")
        print("       Chạy analyze_format.py trước.")
        return None

    with open(str(spec_path), "r", encoding="utf-8") as f:
        spec = json.load(f)

    doc = Document()
    doc_type = spec.get("doc_type", "van_ban_dai")

    print(f"[INFO] Loại văn bản: {doc_type}")

    # === Phân nhánh theo loại văn bản ===
    if doc_type == "hanh_chinh_nd30":
        generate_nd30_reference(doc, spec)
    else:
        generate_vanban_dai_reference(doc, spec)

    # Thêm một đoạn text mẫu (Pandoc cần có nội dung để nhận styles)
    doc.add_paragraph("Reference document for Pandoc.", style="Normal")

    # Lưu file
    ref_path = process_dir / "reference.docx"
    doc.save(str(ref_path))

    body_font = spec.get("body_font", "Times New Roman")
    body_size = spec.get("body_font_size", 13.0)
    heading_size = spec.get("heading_font_size", 15.0)
    line_spacing = spec.get("line_spacing", 1.5)
    indent_pt = spec.get("first_line_indent_pt", 28)
    margins = spec.get("margins_pt", {})

    print(f"\n[OK] Đã tạo reference.docx ({doc_type}):")
    print(f"  Font: {body_font} {body_size}pt")
    print(f"  Heading: {heading_size}pt")
    print(f"  Line spacing: {line_spacing}")
    print(f"  Indent: {indent_pt}pt")
    print(f"  Margins: T={margins.get('top', 57):.0f} B={margins.get('bottom', 57):.0f} "
          f"L={margins.get('left', 85):.0f} R={margins.get('right', 57):.0f} (pt)")
    print(f"[OK] Lưu tại: {ref_path}")
    return str(ref_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python generate_reference.py <thư_mục_processing>")
        sys.exit(1)

    result = generate_reference(sys.argv[1])
    if result is None:
        sys.exit(1)
