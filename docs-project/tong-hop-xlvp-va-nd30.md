# Tổng hợp Kiến trúc và Pipeline Tích hợp Bộ Công cụ Xử lý Văn phòng (XLVP)

Tài liệu này hợp nhất thông tin từ các tài liệu quy hoạch, kiến trúc và kế hoạch tích hợp của bộ công cụ **XLVP** vào hệ thống **Hermes Agent**. Mục tiêu là mang lại cái nhìn toàn cảnh về cách Hermes xử lý các tác vụ văn phòng (Word, Excel, Slide) chuẩn mực.

---

## 1. Tổng quan về Bộ công cụ XLVP

Bộ skill Xử lý Văn phòng (được đặt tại `D:\Antigravity\xlvp`) là tập hợp các công cụ chuyên dụng (OfficeCLI lõi C#, các script Node.js, thư viện Python) giúp Agent tạo và hiệu đính tài liệu chuyên nghiệp.

**Triết lý thiết kế Composable:**
> `Output = Cấu trúc (bắt buộc) × Phối màu (tùy chọn)`

Mặc định, văn bản hành chính xuất ra sẽ tuân thủ tuyệt đối chuẩn Đen/Trắng của Nghị định 30/2020/NĐ-CP. Khi cần trình bày slide, báo cáo doanh nghiệp, hệ thống sẽ gắn thêm các bộ phối màu (Brand Kits).

### Kiến trúc 4 tầng của XLVP:
1. **Tầng Kỹ năng phổ quát (`resources/`)**: Tài liệu kỹ thuật thao tác XML, cách xử lý PDF, DOCX, XLSX.
2. **Tầng Tiêu chuẩn trình bày (`standards/`)**: Chứa định nghĩa cấu trúc (margin, font, list, table) dạng JSON (Single Source of Truth) và các bộ màu (Formal Navy, Modern Blue...).
3. **Tầng Tự động hóa (`scripts/`)**: Script chuyển đổi Markdown sang Word, trích xuất dữ liệu, kiểm tra lỗi.
4. **Tầng Mẫu khung (`templates/` & `examples/`)**: Mẫu văn bản chuẩn NĐ 30, mẫu slide, báo cáo tài chính.

---

## 2. Các Tính năng Tích hợp Chính

Hệ thống XLVP hiện đang cung cấp 2 tính năng chủ lực thông qua Agent (`skills/cc`):

### 2.1 Tính năng Dự thảo Văn bản (`/cc duthao <số>`)
Biến đổi một yêu cầu tạo nháp văn bản thành một file Word chuẩn NĐ 30.
- **Pipeline:**
  1. Trích xuất thông tin văn bản đến từ trạng thái và file đính kèm.
  2. Truy vấn cơ sở tri thức (LightRAG) lấy các quy định pháp luật liên quan.
  3. Dựng Frontmatter xác định cơ quan ban hành dựa trên `unit_id`.
  4. Gọi LLM sinh nội dung dự thảo.
  5. Hậu xử lý (Tự động thêm Nơi nhận, Chức danh).
  6. **Kết xuất file:** Gọi script Node.js (`generate_nd30_docx.js`) hoặc OfficeCLI (qua wrapper Python `xlvp-py`) để render file `.docx`. Có cơ chế fallback dùng `python-docx` (đóng dấu watermark) nếu engine chính lỗi.
  7. Gửi tự động qua Zalo.

### 2.2 Tính năng Soát lỗi & Hiệu đính (`/cc hieudinh <số>` / `/cc sualoi <đường_dẫn>`)
Dựa trên bộ công cụ `nd30-sualoi`.
- **Pipeline:**
  1. **Trích xuất:** Dùng Node.js (`extract_docx.js`) để bóc tách file Word gốc thành JSON chi tiết.
  2. **Hiệu đính LLM:** Đọc JSON, sửa lỗi chính tả và nâng cấp văn phong hành chính.
  3. **Xuất 2 phiên bản đối chiếu:**
     - **Bản Chuẩn hóa:** Chỉ sửa lỗi chính tả, giữ nguyên cấu trúc (tô đỏ chữ được sửa).
     - **Bản Tối ưu:** Viết lại toàn bộ câu từ sao cho mạch lạc, pháp lý hơn (tô đỏ đoạn viết lại).
  4. Trả file về cho người dùng qua giao diện Zalo/Telegram.

### 2.3 Tính năng Bóc tách PDF (`boc-tach-pdf`)
Toàn bộ mã nguồn bóc tách PDF đã được quy hoạch tập trung về `xlvp` nhằm quản lý tập trung và giải phóng cấu hình volume mount.
- Giúp trích xuất nội dung từ các file PDF (cả PDF digital và PDF scan) sang text/markdown.
- Hỗ trợ pipeline xử lý công văn đến, giúp Agent có thể tự động đọc hiểu các quyết định, chỉ thị dạng PDF từ cổng thông tin làm đầu vào cho tính năng dự thảo.

### 2.4 Tính năng Làm sạch & Chuẩn hóa Excel (`/cc donxls <đường_dẫn>`)
Dựa trên sub-skill `clean-data-xls` tích hợp sẵn trong XLVP.
- Hỗ trợ tự động quét file `.xlsx` và phát hiện, sửa 9 loại lỗi dữ liệu phổ biến (khoảng trắng thừa, kiểu chữ lộn xộn, số bị định dạng text, lỗi ngày tháng tiếng Việt...).
- Tự động chuẩn hóa văn bản, chuẩn hóa họ tên người Việt (giữ nguyên thanh điệu) và xuất ra file Excel đã được làm sạch.
- Tích hợp liền mạch qua cơ chế dynamic skill routing, xử lý tự động 100% bằng cờ `--yes` (chế độ bot) để tránh treo hệ thống.

---

## 3. Kiến trúc Hệ thống & Triển khai Docker

Việc tích hợp XLVP vào Hermes Agent yêu cầu sự phối hợp chặt chẽ giữa môi trường Host (Windows) và Container (Linux).

### Cấu trúc Môi trường
- Toàn bộ mã nguồn `D:\Antigravity\xlvp` được mount trực tiếp vào Docker tại `/opt/xlvp`. Các sub-skill như `nd30-document-drafter`, `nd30-sualoi`, `clean-data-xls` nằm gọn trong này.
- **Vấn đề Quyền truy cập:** Để tránh lỗi permission do bind-mount NTFS, binary của OfficeCLI bản Linux được `COPY` trực tiếp trong quá trình build `Dockerfile` và cấp quyền execute (`chmod +x`).

### Lựa chọn Chế độ Thực thi (Batch Mode)
Hệ thống sử dụng **Batch Mode** của OfficeCLI (truyền chuỗi lệnh JSON) cho luồng cron ngầm thay vì Resident Mode (mở liên tục). Việc này:
- Phù hợp với tính tất định (deterministic) của cron job.
- Loại bỏ rủi ro tranh chấp tiến trình khi có nhiều văn bản được xử lý đồng thời.
- Đảm bảo tính nguyên vẹn: nếu lỗi giữa chừng, thao tác sẽ bị hủy thay vì lưu file hỏng.

### Ánh xạ Đường dẫn (Path Translation)
Do Docker xử lý file tại `/opt/data/...` nhưng Zalo API cần đường dẫn thực tế trên Windows (`C:\...`), hệ thống tích hợp sẵn cơ chế tự động chuyển đổi thông qua biến môi trường `ZALO_HOST_HERMES_HOME`.

---

## 4. Các Quy tắc Kỹ thuật Bắt buộc

1. **Quản lý Font chữ:** Môi trường Docker Linux bắt buộc phải cài đặt các gói font metric-compatible như `fonts-liberation` hoặc `ttf-mscorefonts-installer` để bộ render HTML/PDF nhận diện đúng Times New Roman, giúp văn bản không bị vỡ lề.
2. **Tuân thủ NĐ 30 tuyệt đối:** Khi người dùng không yêu cầu định dạng tự do, cấm sử dụng các format phá cách. Văn bản phải được bọc trong các bảng ẩn, căn lề chuẩn xác theo file config JSON.
3. **Excel Live Formula:** Mọi tính toán trong Excel (nếu sinh qua Agent) phải dùng công thức sống, không được hardcode kết quả tính tĩnh.
4. **Không tự ý sửa định dạng:** Sử dụng kỹ thuật unpack/pack XML hoặc truyền file JSON để thay đổi text, không dùng `python-docx` bừa bãi làm hỏng các header/footer đặc thù.
5. **Ghim phiên bản:** Chạy lệnh `officecli config autoUpdate false` trong Container để ghim cố định cấu trúc hệ thống, tránh update ngầm gây gãy vỡ pipeline dự thảo.

---

## 5. Hướng dẫn Tích hợp Code (Python Wrapper)

Để sử dụng wrapper `xlvp-py` điều khiển OfficeCLI (hoặc script Node.js) tạo file Word chuẩn NĐ 30 từ code Python:

### 5.1 Khởi tạo Client và Gọi hàm
```python
import sys, os
XLVP_PATH = os.environ.get("XLVP_PATH", "/opt/xlvp")
if XLVP_PATH not in sys.path:
    sys.path.insert(0, XLVP_PATH)

from xlvp import XLVPClient
client = XLVPClient()

# Sử dụng cơ chế Fallback an toàn
try:
    client.convert_markdown_to_docx("/path/draft.md", "/path/draft.docx")
except Exception as e:
    print(f"[WARN] XLVP lỗi: {e}. Kích hoạt fallback legacy (python-docx)...")
```

### 5.2 Cấu trúc Frontmatter Markdown chuẩn
Để công cụ tự động tạo bảng Quốc hiệu, Tiêu ngữ, Nơi nhận và Chữ ký đúng vị trí, file Markdown sinh ra từ LLM cần có format:
```markdown
---
nd30_header: true
org_parent: "ỦY BAN NHÂN DÂN TỈNH QUẢNG NINH"
org_name: "SỞ THÔNG TIN VÀ TRUYỀN THÔNG"
so_ky_hieu: "Số:      /STTTT-VP"
date: "Quảng Ninh, ngày      tháng      năm 202..."
---

Kính gửi: Ủy ban nhân dân tỉnh Quảng Ninh.

Nội dung văn bản...
- Dòng liệt kê (tự động căn hanging indent 1.25cm - 1.75cm)

**Nơi nhận:**
- Như trên;
- Lưu: VT, VP.

**GIÁM ĐỐC**
*(Ký, ghi rõ họ tên)*
```
