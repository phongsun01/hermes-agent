---
name: boc-tach-pdf
description: >
  Số hóa toàn diện file PDF scan dài thành DOCX trung thực — giữ nguyên font chữ, lùi dòng,
  khoảng cách dòng, ảnh minh họa gốc. Hỗ trợ: render ảnh ở DPI tối đa gốc, tiền xử lý ảnh
  2 tầng (autocontrast/deskew), OCR Vision đa luồng, merge Markdown checkpoint, phân tích
  format tự động, xuất DOCX chuẩn layout qua Pandoc, cắt/chèn ảnh minh họa bằng PIL,
  xuất Excel tùy chọn.
  Kích hoạt khi user đề cập 'bóc tách pdf', 'ocr pdf', 'số hóa tài liệu', 'scan ra word';
  yêu cầu 'chuyển file scan này ra docx', 'trích xuất nội dung pdf';
  nói 'đọc file scan', 'pdf sang markdown';
  trong tình huống có file PDF scan dài cần chuyển thành văn bản có format.
  KHÔNG dùng cho ghép/tách trang PDF thông thường (→ xu-ly-van-phong).
  Dùng cho MỌI yêu cầu số hóa PDF scan — kể cả khi user chỉ quăng file PDF và nói
  'chuyển cái này ra word giúm tôi'.
---

# Quy trình Số hóa PDF Scan Toàn diện (v3)

## Khi nào kích hoạt

Skill này được dùng khi user có file PDF (đặc biệt PDF scan dài) và cần:
- Trích xuất nội dung thành Markdown
- Chuyển đổi thành DOCX giữ nguyên format gốc
- Bóc tách dữ liệu bảng biểu
- Số hóa tài liệu scan

Pipeline xử lý 5 module, chia thành Module Lõi (tự động) và Module Tùy chọn (hỏi user).

---

## BƯỚC 0 — Kiểm tra Dependencies (CHẠY 1 LẦN ĐẦU)

Agent chạy script kiểm tra:
```
python <skill_dir>/scripts/check_deps.py
```

- Nếu thiếu core → chạy `pip install PyMuPDF Pillow python-docx pypandoc-binary`
- Nếu thiếu optional → cảnh báo nhẹ, không chặn pipeline

---

## MODULE LÕI — Chạy tự động, KHÔNG hỏi user

### Bước 1: Render PDF → Ảnh HD

Agent chạy:
```
python <skill_dir>/scripts/core_pdf_to_images.py <đường_dẫn_pdf>
```

Script tự phát hiện DPI gốc (cap 600), tạo cây thư mục `[tên]_processing/` với 3 thư mục con (`01.input/`, `02.process/`, `03.output/`), render ảnh vào `01.input/`, lưu đường dẫn PDF gốc vào `02.process/source.txt`.

### Bước 1.5: Tiền xử lý ảnh (Preprocessing)

Agent chạy:
```
python <skill_dir>/scripts/preprocess_images.py <thư_mục_processing>
```

Tầng 1 (Pillow) chạy mặc định: autocontrast + sharpen nhẹ. An toàn, không làm hỏng ảnh tốt.

### Bước 2: AI Vision OCR Song Song

Agent đọc ảnh từ `01.input/` bằng `view_file` **đồng thời 3-5 file/batch**. Bỏ qua ảnh đã có file `.md` trong `02.process/` (checkpoint).

Với mỗi ảnh, Agent trích xuất nội dung thành Markdown và lưu vào `02.process/<tên_ảnh>.png.md`.

**Quy tắc OCR — Phân tích bố cục và trình bày:**

Agent KHÔNG chỉ đọc chữ — phải PHÂN TÍCH bố cục trình bày của trang ảnh để trích xuất markdown có format gần đúng nhất. Cụ thể:

**1. Nhận diện font chữ:**
- **Font serif** (có chân, nét thanh-đậm, ví dụ Times New Roman): Phổ biến nhất trong VB hành chính Việt Nam. Ghi chú `<!-- font: serif -->` ở đầu file MD nếu nhận ra.
- **Font sans-serif** (không chân, nét đều, ví dụ Arial/Helvetica): Thường gặp trong tài liệu kỹ thuật, slide. Ghi `<!-- font: sans-serif -->`.
- **Font thư pháp/handwriting** (chữ viết tay, cursive): Hiếm, ghi `<!-- font: handwriting -->`.
- **Cỡ chữ tương đối**: Phân biệt ít nhất 3 tầng — lớn (tiêu đề), vừa (heading), nhỏ (body). Ghi chú trang 1 dùng cỡ nào.
- **Đồng nhất/trộn font**: Nếu trang trộn nhiều font → ghi chú font chính (body) và font phụ (heading/caption).

**2. Phân tích căn lề (alignment):**
- Dòng nằm giữa trang → dùng HTML: `<center>Nội dung</center>` hoặc heading `## TIÊU ĐỀ`
- Dòng thụt lề đầu → đây là body text thông thường (không cần markup đặc biệt)
- Dòng nằm bên phải → dùng HTML: `<div style="text-align: right">Nội dung</div>`

**3. Nhận diện kiểu chữ:**
- Chữ **đậm** (bold, nét to hơn hẳn) → `**nội dung**`
- Chữ *nghiêng* (italic) → `*nội dung*`
- Chữ **đậm nghiêng** → `***nội dung***`
- Chữ IN HOA (heading, tiêu đề) → giữ nguyên IN HOA + `**IN HOA**` nếu bold
- Chữ gạch chân thực sự (underline liền trên chữ) → `<u>nội dung</u>` (ít dùng)
- **⚠️ PHÂN BIỆT:** Đường kẻ ngắn DƯỚI dòng chữ (cách 1 khoảng) là **đường phân cách** (separator line), KHÔNG phải gạch chân. Ví dụ: đường kẻ dưới "THÀNH PHỐ HẢI PHÒNG" hay "Độc lập - Tự do - Hạnh phúc" trong VB NĐ 30 → KHÔNG đánh dấu `<u>`, chỉ ghi chú `<!-- separator line -->` nếu cần.

**4. Phân cấp heading:**
- Cỡ chữ LỚN NHẤT, bold, căn giữa → `## TIÊU ĐỀ` (heading 2)
- Cỡ chữ vừa, bold, IN HOA → `### PHẦN HEADING` (heading 3)
- Cỡ chữ body, bold → `**Heading nhỏ:**` (inline bold)
- KHÔNG dùng `# Heading 1` (dành cho Pandoc metadata)

**5. Bố cục 2 cột (header VB hành chính):**
- Nếu thấy 2 khối text nằm song song (trái-phải) trên cùng dòng → trích xuất lần lượt, TÁCH RIÊNG mỗi khối thành 1 paragraph:
  ```
  **ỦY BAN NHÂN DÂN**
  **THÀNH PHỐ HẢI PHÒNG**
  <!-- separator line -->

  **CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM**
  **Độc lập - Tự do - Hạnh phúc**
  <!-- separator line -->

  Số: 19/TTr-UBND

  *Hải Phòng, ngày 25 tháng 3 năm 2021*
  ```
- KHÔNG gộp cơ quan + quốc hiệu thành 1 dòng
- Đường kẻ ngắn DƯỚI "THÀNH PHỐ..." và "Độc lập..." là **separator line** (đường phân cách), KHÔNG phải underline

**6. Bảng biểu:**
- Bảng → Markdown table (`| col | col |`)
- Header bảng (dòng đầu, thường bold) → để nguyên text, không thêm `**`
- Nếu bảng quá rộng (nhiều cột) → vẫn trích xuất đầy đủ, mỗi cột 1 pipe

**7. Bullet list và đánh số:**
- Dấu gạch ngang/chấm đầu dòng → `- nội dung`
- Đánh số 1. 2. 3. → `1. nội dung`
- Đánh số La Mã I. II. III. → `### I. TIÊU ĐỀ` (nếu bold IN HOA)
- Ký tự a) b) c) → `a) nội dung` (giữ nguyên)

**8. Ảnh minh họa / biểu đồ:**
- Nếu có ảnh/hình/biểu đồ/sơ đồ → ghi `[Hình minh họa: mô tả ngắn]` tại vị trí tương ứng
- Nếu có chú thích ảnh → ghi `*Hình X.X: Chú thích*`

**9. Đường kẻ / separator:**
- Đường kẻ ngang dài ngăn cách phần → `---`
- Đường kẻ ngắn (~3-4cm) dưới tên cơ quan / tiêu ngữ (NĐ 30) → `<!-- separator line -->` (script xử lý tự động, KHÔNG đánh dấu underline)

**10. Quy tắc chất lượng:**
- Nếu ảnh quá mờ → ghi `[Không đọc được]`
- Nếu có ký tự đặc biệt (×, °, ², ≤...) → giữ nguyên Unicode, KHÔNG thay bằng ASCII
- Nếu có số liệu trong bảng → đảm bảo đúng 100%, không ước lượng

**11. Số trang in trên giấy gốc:**
- Tài liệu scan thường có số trang in sẵn (ví dụ: `2`, `3`, `15`) nằm đầu hoặc cuối trang, đứng đơn độc.
- **KHÔNG trích xuất** số trang đơn độc này vào Markdown. Bỏ qua hoàn toàn.
- Cách nhận diện: con số đứng một mình trên 1 dòng, không nằm trong câu/đoạn/bảng nào, thường nằm ở header/footer của trang scan.
- Lý do: Nếu OCR số trang, chúng sẽ xuất hiện như đoạn văn thừa trong DOCX cuối cùng. Pipeline có xử lý xóa tự động nhưng phòng ngừa từ bước OCR là tốt nhất.

**Nếu OCR ra rỗng hoặc gibberish (ảnh quá kém):**
```
python <skill_dir>/scripts/preprocess_images.py <thư_mục_processing> --enhance
```
Kích hoạt Tầng 2 (OpenCV: deskew + denoise), rồi retry OCR.

### Bước 3: Merge MD

Khi 100% ảnh đã có MD trong `02.process/`, Agent chạy:
```
python <skill_dir>/scripts/core_merge_md.py <thư_mục_processing>
```

Kết quả: `03.output/MERGED.md` với page separator `<!-- page: N -->`.

**TỚI ĐÂY MODULE LÕI KẾT THÚC.** Agent thông báo kết quả cho user.

---

## MODULE TÙY CHỌN — Hỏi user trước khi chạy

Agent gợi ý: *"Anh có muốn xuất DOCX đúng format gốc không?"*

### Nếu CÓ → Chạy 4 bước:

**Bước 4a: Phân tích Format + Nhận diện loại VB**
```
python <skill_dir>/scripts/analyze_format.py <thư_mục_processing>
```
→ `02.process/format_spec.json` chứa:
- **`doc_type`**: `"hanh_chinh_nd30"` hoặc `"van_ban_dai"` — tự động phát hiện từ nội dung OCR
- **`page_orientations`**: dict các trang landscape (ví dụ `{27: "landscape", 28: "landscape"}`)
- Font, margin, spacing, vị trí ảnh

**Agent cần kiểm tra kết quả:** Sau khi script chạy xong, Agent nhìn lại 2-3 trang ảnh đầu (`01.input/page_001.png`, `page_002.png`) để **xác nhận loại VB** có đúng không. Nếu không khớp, Agent tự điều chỉnh `doc_type` trong `format_spec.json`.

**Quy tắc format theo loại VB:**
- **`hanh_chinh_nd30`**: Đen trắng thuần. Font Times New Roman 13pt. Margin trang dọc NĐ 30 (T20 B20 L30 R20 mm). Đặc biệt áp dụng checklist kiểm soát định dạng sau:
  - **Bảng Header 2 cột**: Không viền (w:tblBorders="nil"). Cột 1 (Cơ quan) căn giữa. Cột 2: "CỘNG HÒA..." căn giữa chữ đậm. Cột 1 dưới: Số ký hiệu căn giữa. Cột 2 dưới: Địa danh, ngày tháng căn lề phải, in nghiêng. Khóa cứng độ rộng bảng (`w:tblLayout="fixed"`). Thêm đường kẻ ngang nhỏ phía dưới cơ quan và quốc hiệu.
  - **Kính gửi**: Căn giữa (CENTER), font thường (không đậm, không nghiêng), cách đoạn dưới (`space_after=12pt`).
  - **Heading (I, II...)**: Chữ đậm, thụt lề đầu dòng (`first_line_indent`), xoá dấu hai chấm (`:`) ở cuối.
  - **List Items (Bullet points)**: Thay thế hoàn toàn sang dấu gạch ngang (`-`), áp dụng thụt lề đầu dòng (`first_line_indent`) giống hệt đoạn văn bản thường.
- **`van_ban_dai`**: Có thể dùng color heading. Font và spacing đo từ PDF gốc hoặc mặc định.

**Bước 4b: Trích xuất Ảnh minh họa**
```
python <skill_dir>/scripts/extract_images.py <thư_mục_processing>
```
→ Ảnh trích xuất lưu vào `01.input/`, metadata lưu vào `02.process/image_map.json`

**Bước 4c: Tạo Reference Template**
```
python <skill_dir>/scripts/generate_reference.py <thư_mục_processing>
```
→ `02.process/reference.docx` — tự động phân nhánh theo `doc_type`

**Bước 5: Xuất DOCX**
```
python <skill_dir>/scripts/export_docx.py <thư_mục_processing>
```
→ `03.output/[tên_tài_liệu_gốc].docx` + `03.output/[tên_tài_liệu_gốc].md`

Tên file đầu ra tự động lấy từ tên thư mục processing (bỏ hậu tố `_processing`).

Script tự động gọi 5 layer: 
1. **Layer 0 — Pandoc**: Convert MD → DOCX thô (temp0.docx)
2. **Layer 1 — Layout**: Áp dụng landscape/portrait theo `format_spec.json`, xóa `[PAGE_MARKER_N]` và số trang OCR thừa liền kề
3. **Layer 2 — Structure**: Tái cấu trúc bảng header NĐ 30 (tách cột gộp, dựng bảng 2 cột không viền)
4. **Layer 3 — Block**: Format paragraph (indent, spacing, alignment) và table (border, width)
5. **Layer 4 — Typography**: Font, complex script tiếng Việt, xử lý bold/italic tag residuals

**Bước 6: Xác nhận và Dọn dẹp (Cleanup)**
Sau khi xuất DOCX, Agent **LUÔN HỎI** người dùng: *"Anh vui lòng mở file kiểm tra. Nếu đã ưng ý, báo lại tôi để tôi dọn dẹp các file rác trung gian nhé."*
Nếu người dùng đồng ý:
```
python <skill_dir>/scripts/cleanup.py <thư_mục_processing>
```
→ Xóa `01.input/` và `02.process/`.
→ Chỉ giữ lại thư mục `03.output/` chứa 2 file: `[tên].docx` và `[tên].md`.

### Nếu muốn EXCEL:
```
python <skill_dir>/scripts/optional_export_xlsx.py <đường_dẫn_MERGED_md>
```

---

## Ghi Nhớ Cho AI Agent

1. **Concurrent Tools:** Gọi nhiều `view_file` cùng lúc (3-5 ảnh/batch) để tăng tốc OCR.
2. **Checkpointing:** Luôn lưu từng trang lẻ vào `02.process/`. Bỏ qua ảnh đã có MD.
3. **Phản hồi ngắn:** "Đang OCR batch 1 (trang 1-5)...", "Đang preprocessing...". Không lặp lại nội dung.
4. **`<skill_dir>`** là thư mục chứa SKILL.md này. Agent tự xác định đường dẫn tuyệt đối.
5. **Fallback chain:** Nếu bất kỳ bước nào lỗi → đọc output lỗi → thử fallback → báo user nếu vẫn lỗi.
6. **Xác nhận loại VB:** Sau `analyze_format.py`, luôn nhìn ảnh trang 1-2 để xác nhận `doc_type`. VB hành chính (header NĐ 30, Kính gửi, Nơi nhận) → đen trắng. VB dài (thuyết minh, nghiên cứu) → có thể tùy biến.
7. **Trang ngang:** Kiểm tra `page_orientations` trong format_spec.json. Nếu có → export_docx.py tự chèn section break landscape. Agent chỉ cần đảm bảo bảng trong MD đủ cột.

---

## Bài Học Thực Chiến (Lessons Learned)

Các lỗi đã gặp trong quá trình chạy thực tế và cách xử lý. **Agent BẮT BUỘC đọc mục này** trước khi debug bất kỳ lỗi nào trong pipeline.

### 1. Biến thể dấu tiếng Việt trong Regex (Vietnamese Accent Variants)

**Triệu chứng:** `02_structure.py` báo `"Không đủ thông tin header NĐ 30"` dù ảnh scan rõ ràng có header chuẩn.

**Nguyên nhân gốc:** Tiếng Việt có nhiều cách mã hóa Unicode cho cùng một ký tự có dấu. Ví dụ:
- `UỶ` (U+0055 U+1EF6) — "Y" mang dấu hỏi tổ hợp, khác với `ỦY` (U+1EE6 U+0059) — "U" mang dấu hỏi
- `HOÀ` vs `HÒA` — dấu huyền trên "O" vs trên "A"

**Quy tắc:** Regex nhận diện tiếng Việt PHẢI cover mọi biến thể tổ hợp/tiền tổ hợp. Ví dụ:
- ❌ `[UỦ]Y\s*BAN` — bỏ sót `UỶ BAN`
- ✅ `[UỦ][YỶÝỲỸ]?\s*BAN` — cover tất cả biến thể

### 2. Pandoc gộp cột thành 1 dòng (Merged Columns)

**Triệu chứng:** Header VB hành chính (cột trái: cơ quan, cột phải: quốc hiệu) bị Pandoc gộp thành 1 paragraph duy nhất, cách nhau bằng khoảng trắng đôi.

**Ví dụ thực tế:**
```
Paragraph 2: 'UỶ BAN NHÂN DÂN THÀNH PHỐ HẢI PHÒNG  Số: 19/TTr-UBND'
Paragraph 3: 'CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM Độc lập - Tự do - Hạnh phúc  Hải Phòng, ngày 25 tháng 3 năm 2021'
```

**Giải pháp:** `02_structure.py` phải tách paragraph bằng `re.split(r'\s{2,}', text)` trước khi match regex từng segment. Mỗi segment được kiểm tra độc lập cho các trường header.

### 3. Ký tự `\n` literal trong python-docx

**Triệu chứng:** File DOCX hiển thị chữ `\n` thay vì xuống dòng trong bảng header.

**Nguyên nhân gốc:** Code dùng `p.add_run("\\n")` (escaped backslash-n = 2 ký tự `\` và `n`) thay vì `p.add_run("\n")` (soft newline thực sự).

**Quy tắc khi sửa code python-docx:**
- Xuống dòng mềm (soft break) trong cùng 1 paragraph: `p.add_run("\n")` — Python string literal, KHÔNG escape.
- Nếu muốn paragraph mới: tạo paragraph mới bằng `cell.add_paragraph()`, KHÔNG dùng `\n`.

### 4. Số trang OCR thừa trong DOCX

**Triệu chứng:** File DOCX chứa các đoạn văn chỉ có 1 con số (`2`, `3`, ..., `28`) xen kẽ giữa nội dung chính.

**Nguyên nhân gốc:** OCR quét được số trang in trên giấy gốc và trích xuất chúng thành đoạn văn MD đơn độc. Bước merge giữ nguyên, Pandoc convert sang DOCX, nhưng `01_layout.py` chỉ xóa `[PAGE_MARKER_N]` mà không xóa đoạn số trang liền kề.

**Giải pháp 2 tầng:**
- **Tầng 1 (Phòng ngừa - OCR):** Agent KHÔNG trích xuất số trang đơn độc khi OCR (xem Quy tắc 11).
- **Tầng 2 (Xử lý - Layout):** `01_layout.py` sau khi tìm `[PAGE_MARKER_N]`, kiểm tra đoạn không rỗng tiếp theo — nếu nội dung đúng bằng `str(N)` → xóa luôn đoạn đó.
