# Soạn công văn / văn bản hành chính ra file Word (.docx)

## Khi nào cần
- Người dùng yêu cầu soạn công văn, tờ trình, báo cáo, góp ý... và xuất ra file Word
- Dùng cho văn bản hành chính Việt Nam có thể in ấn, đóng dấu, trình ký

## Quy trình 2 bước

### Bước 1: Soạn nội dung dạng Markdown (để dễ chỉnh sửa)
- Viết nội dung ra file `.md` ở `/tmp/` (vì 9p mount không cho ghi vào `/opt/data/`)
- Trình bày rõ các phần: tiêu đề, kính gửi, nội dung chính, nơi nhận, chữ ký
- Cho người dùng xem duyệt trước, chỉnh sửa nếu cần

### Bước 2: Xuất ra Word (.docx) bằng python-docx

**Cài đặt (nếu chưa có):**
```bash
uv pip install python-docx
```

**Cấu trúc file Word cho văn bản hành chính Việt Nam:**
- Font: Times New Roman, cỡ 13 (tương đương 13pt)
- Canh lề: trên 2cm, dưới 2cm, trái 2.5-3cm, phải 2cm
- Giãn dòng: 1.3-1.5 lines
- Header: tên cơ quan (in đậm, căn giữa), số công văn
- Phần "CỘNG HOÀ... Độc lập..." căn phải, in đậm, có gạch ngang phân cách
- Địa danh + ngày tháng: căn phải
- Kính gửi: căn trái
- Nội dung: căn trái, first-line indent nếu cần
- Nơi nhận: căn trái, có bullet
- Chữ ký: căn phải, KT. GIÁM ĐỐC / THỦ TRƯỞNG (in đậm), bỏ trống chỗ ký tên

## Mẫu code python-docx cơ bản

```python
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# Page setup
for section in doc.sections:
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.0)

# Font mặc định
style = doc.styles['Normal']
font = style.font
font.name = 'Times New Roman'
font.size = Pt(13)
style.paragraph_format.line_spacing = 1.3
```

**Các pattern căn bản cho paragraph:**
```python
# Căn giữa
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Nội dung')
run.bold = True
run.font.size = Pt(13)
run.font.name = 'Times New Roman'

# Căn phải
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

# Căn trái (mặc định)
p = doc.add_paragraph()
```

## Lưu ý
- Luôn tạo file ở `/tmp/` do 9p mount permission issue — sau đó hỏi người dùng cách gửi
- Có thể gửi file qua Zalo nếu có tool gửi file (Hermes Gateway hỗ trợ)
- Để trống số công văn, ngày tháng, chữ ký — người dùng tự điền sau khi tải về
- Số hiệu văn bản để dạng: `Số:    /<ĐƠN VỊ>-<PHÒNG>` (có khoảng trống để điền sau)
