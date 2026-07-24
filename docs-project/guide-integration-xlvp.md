# Hướng dẫn Tích hợp Thư viện xlvp (OfficeCLI) vào Skill

Tài liệu này hướng dẫn cách sử dụng thư viện `xlvp` (gói Python wrapper cho OfficeCLI) để chuyển đổi các văn bản Markdown thành tệp Word DOCX chuẩn Nghị định 30/2020/NĐ-CP của Chính phủ.

---

## 1. Cấu trúc thư mục của gói xlvp

Thư viện `xlvp` được phân phối tại `/opt/xlvp` trong container, bao gồm:
* `xlvp/client.py`: Lớp `XLVPClient` chính để điều khiển OfficeCLI bằng Batch Mode.
* `xlvp/standards/nd30.json`: Tệp định nghĩa các quy chuẩn twips (lề trang, cỡ chữ, khoảng cách đoạn, bảng header, căn chỉnh danh sách,...).

---

## 2. Cách sử dụng trong mã nguồn Python

### 2.1 Import và Khởi tạo Client

Để sử dụng trong một script Python chạy trong container Hermes, hãy thêm `/opt/xlvp` vào `sys.path` trước khi thực hiện import:

```python
import sys
import os

# Thêm path tới thư viện xlvp
XLVP_PATH = os.environ.get("XLVP_PATH", "/opt/xlvp")
if XLVP_PATH not in sys.path:
    sys.path.insert(0, XLVP_PATH)

from xlvp import XLVPClient

client = XLVPClient()
```

### 2.2 Chuyển đổi Markdown sang DOCX

Hàm `convert_markdown_to_docx(md_path, docx_path)` tự động:
1. Đọc tệp Markdown.
2. Bóc tách phần YAML frontmatter (nếu có cấu hình `nd30_header: true`).
3. Khởi tạo văn bản Word mới thông qua `officecli`.
4. Thiết lập căn lề trang (Top/Bottom/Left/Right) theo quy chuẩn Nghị định 30.
5. Tạo bảng ẩn 2 cột không viền ở phần Header (Cơ quan ban hành & Quốc hiệu - Tiêu ngữ).
6. Duyệt và chuyển đổi các phần thân văn bản (Paragraphs, List items có hanging indent, Heading căn giữa, Bảng dữ liệu).
7. Tự động chèn ký hiệu kết thúc `./.` ở cuối văn bản.
8. Tạo bảng ẩn 2 cột không viền ở cuối văn bản cho mục Nơi nhận & Chữ ký người có thẩm quyền.

**Cú pháp gọi:**
```python
md_file = "/path/to/draft.md"
docx_file = "/path/to/draft.docx"

try:
    client.convert_markdown_to_docx(md_file, docx_file)
    print(f"Thành công: {docx_file}")
except Exception as e:
    print(f"Lỗi chuyển đổi: {e}")
```

---

## 3. Cấu trúc Frontmatter Markdown chuẩn Nghị định 30

Để `xlvp` tự động tạo Header và Footer đúng chuẩn, tệp Markdown nguồn cần có cấu trúc frontmatter như sau:

```markdown
---
nd30_header: true
org_parent: "ỦY BAN NHÂN DÂN TỈNH QUẢNG NINH"
org_name: "SỞ THÔNG TIN VÀ TRUYỀN THÔNG"
so_ky_hieu: "Số:      /STTTT-VP"
date: "Quảng Ninh, ngày      tháng      năm 202..."
---

Kính gửi: Ủy ban nhân dân tỉnh Quảng Ninh.

Nội dung văn bản trả lời bắt đầu từ đây...
- Dòng liệt kê 1
- Dòng liệt kê 2 (tự động căn hanging indent 1.25cm - 1.75cm)

**Nơi nhận:**
- Như trên;
- Lưu: VT, VP.

**GIÁM ĐỐC**
*(Ký, ghi rõ họ tên)*
```

---

## 4. Cơ chế Fallback an toàn (Khuyên dùng)

Luôn triển khai cơ chế dự phòng (fallback) để bảo đảm hệ thống hoạt động liên tục ngay cả khi môi trường thiếu thư viện `xlvp` hoặc nhị phân `officecli` bị lỗi:

```python
def convert_to_docx(md_path, docx_path):
    # Cách 1: Thử dùng xlvp
    try:
        from xlvp import XLVPClient
        client = XLVPClient()
        client.convert_markdown_to_docx(md_path, docx_path)
        return True
    except Exception as e:
        print(f"[WARN] xlvp failed: {e}. Falling back to legacy.", file=sys.stderr)
        
    # Cách 2: Chạy script convert dự phòng
    try:
        # Code hoặc subprocess gọi script cũ ở đây...
        return True
    except Exception as e:
        print(f"[ERROR] All converters failed: {e}", file=sys.stderr)
        return False
```
