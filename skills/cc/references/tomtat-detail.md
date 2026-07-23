# Chi tiết lấy thông tin văn bản (tomtat)

## Ba phương pháp lấy chi tiết văn bản

### Phương pháp 1: State file (ưu tiên)
Dùng `congvan_status.py status <số_vb>` — đọc từ state file local.
- ✅ Nhanh, không cần login web
- ✅ Không bị giới hạn pagination (tìm được văn bản cũ)
- ✅ Hoạt động cả khi web bị lỗi
- ❌ Chỉ có: Số CV, Tác giả, Trích yếu, Trạng thái, Cập nhật
- ❌ Trích yếu có thể bị cắt ngắn (xem phần Vấn đề đã biết)
- ❌ Không có nội dung chi tiết hay file đính kèm

### Phương pháp 2: Playwright web scraping (khi cần thêm chi tiết)
Dùng Playwright login + tìm dòng trên grid.
- ✅ Có thể lấy thêm thông tin từ form chi tiết
- ❌ Chậm (10-15s login + tìm kiếm)
- ❌ Chỉ tìm được văn bản còn hiển thị trên grid (có pagination, tối đa 15 trang)
- ❌ Bị 9p mount permission issue khi ghi screenshot/log
- ❌ Có thể parse sai văn bản (xem phần Vấn đề đã biết)
- ⚠️ Văn bản cũ (VD: 2330 từ 22/06) có thể không còn trên grid → fallback về phương pháp 1

### Phương pháp 3: Đọc file thủ công (khi LLM trong script không phản hồi)
Script `congchuc_summarize.py` gọi LLM local qua OpenAI-compatible API. Đôi khi LLM không phản hồi (lỗi kết nối, timeout, model busy). Khi đó:

1. Kiểm tra file đính kèm đã có chưa:
   - Xem state: `"attachments_complete": true` trong `vbden_state.json`
   - Hoặc kiểm tra thư mục: `ls /opt/data/cron/cong-van-den/attachments/<số_vb>/`
2. Đọc nội dung file thủ công:
   ```bash
   # DOCX
   uv run python -c "from docx import Document; d=Document('/opt/data/cron/cong-van-den/attachments/<số_vb>/*.docx'); print('\n'.join(p.text for p in d.paragraphs if p.text.strip()))"
   # PDF
   uv run python -c "import fitz; doc=fitz.open('/opt/data/cron/cong-van-den/attachments/<số_vb>/*.pdf'); [print(doc[i].get_text()) for i in range(doc.page_count)]; doc.close()"
   ```
3. Dùng khả năng của Hermes để phân tích và tóm tắt theo cấu trúc: Mục đích, Nội dung, Deadline, Đơn vị thực hiện, Đề xuất xử lý.

## Vấn đề đã biết

### 1. Trích yếu bị cắt ngắn
Khi dùng `congvan_status.py status <số_vb>` hoặc `congchuc_summarize.py`, trường `trich_yeu` có thể bị cắt ngắn (VD: hiện "mặt t" thay vì "mặt trời mái nhà giai đoạn 2026-2030").

**Khắc phục**: Đọc trực tiếp từ file `vbden_state.json` để lấy trích yếu đầy đủ. Dùng grep hoặc đọc entry tương ứng:
```bash
grep -A5 '"so_den": "<số_vb>"' /opt/data/cron/cong-van-den/vbden_state.json
```
Hoặc đọc file state với read_file tool.

### 2. `congvan_detail.py` parse sai văn bản
Script `congvan_detail.py` đôi khi hiển thị nhầm thông tin của văn bản khác (VD: hiện #2506 khi request #2490). Nguyên nhân có thể do Playwright scroll/parse bị lệch hàng trên grid.

**Khắc phục tạm thời**: Dùng state file (phương pháp 1) để lấy thông tin chính xác.

## Lưu ý khi dùng Playwright cho tomtat
Nếu cần dùng Playwright để lấy thêm chi tiết từ web:
1. Copy script mẫu ra `/tmp/` (vì không ghi được vào thư mục scripts do 9p mount)
2. Patch đường dẫn screenshot thành `/tmp/congchuc_screenshots/`
3. Dùng `uv run python` (playwright nằm trong uv, không phải system python)
4. Nếu không tìm thấy văn bản → fallback về state file
