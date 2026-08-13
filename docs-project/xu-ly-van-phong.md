# Skill Xử lý Văn phòng — xu-ly-van-phong-v1.0

Tài liệu này tổng hợp thông tin hướng dẫn và cấu trúc của bộ skill xử lý văn phòng (`xu-ly-van-phong`) được tải về tại thư mục [xu-ly-van-phong-v1.0](file:///d:/Antigravity/Hermes/docs/xu-ly-van-phong-v1.0).

---

## 1. Giới thiệu chung
Bộ skill cung cấp hệ thống quy chuẩn trình bày tài liệu nhất quán (Word, Excel, Slide, PDF) giúp AI Agent tạo ra các đầu ra văn bản, bảng tính, slide chất lượng cao, đồng nhất, hạn chế các lỗi định dạng hoặc font chữ ngẫu nhiên.

### Công thức thiết kế Composable:
```
Output = Cấu trúc (bắt buộc) × Phối màu (tùy chọn)
```
*Mặc định mọi văn bản xuất ra đen trắng chuẩn. Khi cần trình bày đẹp, gắn thêm bộ phối màu.*

---

## 2. Kiến trúc 4 tầng của bộ Skill

### Tầng 1 — Kỹ năng phổ quát (`resources/`)
Cách dùng tool, thư viện và quy trình kỹ thuật cho từng loại file:
- **`resources/docx.md`**: Tạo/sửa DOCX bằng python-docx hoặc docx-js.
- **`resources/xlsx.md`**: Tạo/sửa Excel bằng openpyxl (nguyên tắc: Live Formula, không hardcode).
- **`resources/pptx.md`**: Tạo/sửa Slide bằng pptxgenjs (nguyên tắc: không slide thuần text).
- **`resources/pdf.md`**: Xử lý PDF cục bộ (phân biệt PDF digital vs PDF scan).
- **`resources/office-xml.md`**: Kỹ thuật Unpack/Pack XML (giữ nguyên format file mẫu, chỉ thay đổi nội dung).
- **`resources/convert.md`**: Pipeline chuyển đổi: MD→DOCX, PDF→DOCX, DOCX→PDF.

### Tầng 2 — Tiêu chuẩn trình bày (`standards/`)
Bao gồm cấu trúc mặc định và các bộ phối màu (skin):
- **Cấu trúc (`standards/structure/`)**:
  - `docx-page-setup.md`: Khổ giấy, margin, line spacing.
  - `docx-typography.md`: Font family, cỡ chữ, weight.
  - `docx-heading-numbering.md`: Hệ 5 cấp (văn bản ngắn) và 9 cấp (văn bản dài).
  - `docx-list-bullet.md`: Bullet, numbered list, indent.
  - `docx-table.md`: 5 mẫu bảng (lộ trình, traffic light, zebra, matrix, số liệu).
  - `docx-cover-page.md`: Trang bìa văn bản ngắn vs dài.
  - `docx-header-footer.md`: Header/footer, đánh số trang, header 2 cột NĐ 30.
  - `docx-caption-reference.md`: Caption bảng/hình, trích dẫn nguồn.
  - `docx-special-blocks.md`: Code block, callout, divider, signature, công thức.
  - `xlsx-structure.md`: Bố cục bảng tính (multi-sheet, phân cấp row, column width, dòng tổng).
  - `pptx-structure.md`: Bố cục slide (layout patterns, font pairing, phân cấp thông tin).
- **Phối màu (`standards/color/`)** (tùy chọn):
  - `docx-formal-navy.md` (Trang trọng): Dành cho đề xuất cấp chiến lược, tập đoàn.
  - `docx-modern-blue.md` (Hiện đại): Dành cho startup, SME.
  - `docx-editorial-burgundy.md` (Editorial): Dành cho review, phản biện.
  - `docx-technical-multicolor.md` (Kỹ thuật): Heading phân cấp bằng màu.
  - `xlsx-palettes.md`: 3 bộ XLSX (Dark, Green, Blue + Traffic Light).
  - `pptx-palettes.md`: 10 bộ phối màu slide.
- **Quy chuẩn hành chính (`standards/nd30.md`)**:
  - Quy chuẩn quốc gia về văn bản hành chính Việt Nam theo Nghị định 30/2020/NĐ-CP (bao gồm cả cấu trúc lẫn định dạng).

### Tầng 3 — Tự động hóa (`scripts/`)
- `scripts/office/`: Toolkit XML (unpack, pack, clone_text, validate, soffice, helpers).
- `scripts/convert/`: `convert_md_to_docx.py`, `convert_pdf_to_docx.py`.
- `scripts/format/`: `format_docx.py` (post-process DOCX sau Pandoc).

### Tầng 4 — Mẫu khung & Ví dụ (`templates/` & `examples/`)
- `templates/docx-hanh-chinh-*.md`: 9 mẫu VB hành chính NĐ 30 (công văn, quyết định, tờ trình...).
- `templates/docx-de-xuat-*.md`: Mẫu đề xuất/báo cáo.
- `examples/docx-bao-cao-formal-navy.docx`: Đầu ra mẫu palette Formal Navy.
- `examples/docx-cong-van-nd30.docx`: Đầu ra mẫu chuẩn NĐ 30.
- `examples/xlsx-bao-cao-tien-do.xlsx`: Excel mẫu Corporate Green.

---

## 3. Quy tắc ứng xử và cấm kỵ

1. **Về định dạng:** Luôn đọc `standards/` trước khi tạo file. Không tự ý chọn font, cỡ chữ, spacing ngẫu nhiên.
2. **Về Excel:** Mọi ô tính toán phải sử dụng công thức sống (`Live Formula`), không hardcode kết quả tính toán.
3. **Về Slide:** Không chấp nhận slide chỉ có text trắng nền trắng.
4. **Về bảo mật:** Không upload PDF/tài liệu lên các dịch vụ đám mây công cộng để xử lý.
5. **Về Word hành chính:** Không trộn lẫn format NĐ 30 với format đề xuất doanh nghiệp.
6. **Về python-docx:** Không dùng python-docx trực tiếp khi cần giữ format file mẫu phức tạp — thay vào đó dùng kỹ thuật `Unpack/Pack XML`.
