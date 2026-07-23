---
name: cc
description: Hệ thống tương tác xử lý công văn Quảng Ninh. Hỗ trợ /cc list, /cc list today, /cc end <số> [lý do], /cc end all, /cc tai <số>, /cc duthao <số>, /cc tomtat <số>, /cc hieudinh <số>, /cc sualoi <đường_dẫn_file>, /cc vbdi <từ_khóa>, /cc help. Hoặc nói tự nhiên "kết thúc giúp anh văn bản số 2534", "hiệu đính công văn 1234", "soát lỗi file này", "tìm văn bản đi số 188".
version: 2.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [congvan, quangninh, cc, congchuc]
    category: productivity
---

# Kỹ năng Quản lý Công văn (/cc)

Khi người dùng gọi slash command `/cc` kèm theo các lệnh phụ (hoặc đưa ra yêu cầu xử lý công văn bằng ngôn ngữ tự nhiên), hãy phân tích yêu cầu và thực hiện chính xác các hướng dẫn dưới đây.

LƯU Ý BẮT BUỘC: Bạn CHỈ ĐƯỢC CHẠY các lệnh sau đây bằng tool thực thi command và thông báo ngắn gọn kết quả cho người dùng, tuyệt đối không tự bịa thông tin. Môi trường của bạn là Linux (Docker), hãy dùng đường dẫn TUYỆT ĐỐI bắt đầu bằng `/opt/data`. (Các script ĐÃ TỒN TẠI ở thư mục `/opt/data/skills/cc/scripts/`).

## Bảng Lệnh Nhanh (Slash Commands)

| Lệnh / Yêu cầu | Mô tả & Lệnh chạy thực tế |
|---|---|
| `/cc list` | Liệt kê VB mới (`skills/cc/scripts/congvan_status.py list --status new`) |
| `/cc list today` | Liệt kê VB cập nhật hôm nay (lọc kết quả từ `skills/cc/scripts/congvan_status.py list`) |
| `/cc end <số>` | Kết thúc 1 VB (`skills/cc/scripts/congchuc_action.py kethuc <số>`) |
| `/cc end all` | Kết thúc toàn bộ VB chưa xử lý (gộp batch xử lý trong 1 phiên trình duyệt) |
| `/cc tai <số>` | Tải file đính kèm (`skills/cc/scripts/congchuc_scrape.py --download-only <số>`) |
| `/cc duthao <số>` | Tạo bản nháp dự thảo chuẩn NĐ30 (`skills/cc/scripts/congchuc_draft.py --so-den <số> --zalo`) |
| `/cc tomtat <số>` | Đọc và tóm tắt nội dung (`congchuc_summarize.py --so-den <số>`) |
| `/cc hieudinh <số>` | Soát lỗi chính tả & tối ưu văn phong VB đến (`skills/cc/scripts/congchuc_editor.py --so-den <số> --zalo`) |
| `/cc sualoi <đường_dẫn>` | Soát lỗi chính tả & tối ưu văn phong từ file Word (`skills/cc/scripts/congchuc_editor.py --file-path <đường_dẫn> --zalo`) |
| `/cc vbdi <từ_khóa>` | Tìm kiếm văn bản đi theo từ khóa (`skills/cc/scripts/congchuc_vbdi_search.py <từ_khóa>`) |
| `/cc theodoi <số>` | Theo dõi 1 văn bản đi và báo cáo khi quét thấy (`cc_router theodoi <số>`) |
| `/cc help` | In ra danh sách hướng dẫn lệnh cho người dùng |

---

## 1. Slash Commands

### Quy tắc định dạng chung cho danh sách (`/cc list`, `/cc list today`)
- BẮT BUỘC sử dụng danh sách có đánh số thứ tự rõ ràng dạng `1. `, `2. ` (không dùng các icon chung chung như `📄`).
- Định dạng in đậm bằng dấu sao kép `**` cho mã số văn bản (ví dụ: `**#2534**`) và tên đơn vị gửi để Zalo Bridge có thể hiển thị in đậm tương ứng.
- Dùng emoji sinh động và giữ khoảng cách dòng thoáng đãng, dễ đọc.

### 1.1 Lệnh `/cc list` (Liệt kê các văn bản mới)
- **Hành động**: Chạy lệnh: `uv run python /opt/data/skills/cc/scripts/congvan_status.py list --status new`
- **Trả lời**: Liệt kê ĐẦY ĐỦ TẤT CẢ các văn bản trả về từ lệnh (BẮT BUỘC hiển thị đủ toàn bộ số lượng VB nhận được, tuyệt đối KHÔNG tự ý cắt bớt hay giới hạn xuống 10 VB). Đảm bảo tổng số VB trong báo cáo khớp chính xác với số lượng thực tế trong kết quả lệnh.

### 1.2 Lệnh `/cc list today` (Liệt kê văn bản hôm nay)
- **Hành động**: Chạy lệnh: `uv run python /opt/data/skills/cc/scripts/congvan_status.py list`
  Từ kết quả trả về, dùng kỹ năng của bạn để **chỉ lọc ra và hiển thị** các văn bản có ngày cập nhật trùng với ngày hôm nay.
- **Trả lời**: Liệt kê kết quả lọc được theo *Quy tắc định dạng chung*.

### 1.3 Lệnh `/cc end <số_vb> [lý do]` (Kết thúc văn bản)
- **Hành động**: 
  1. Đọc `vbden_state.json` kiểm tra trạng thái. Nếu đã `status: "done"` → báo user và bỏ qua (tiết kiệm thời gian).
  2. Nếu chưa done, chạy: `HERMES_HOME=/tmp uv run python /opt/data/skills/cc/scripts/congchuc_action.py kethuc <số_vb> [lý do]` (nếu không có lý do, bỏ trống).
  3. **Post-run state sync (bắt buộc)**: Sau khi script báo ✅ thành công, chạy: `uv run python /opt/data/skills/cc/scripts/congvan_status.py done <số_vb>`. (Nếu báo "Không tìm thấy văn bản trên grid" thì coi như đã xong, vẫn chạy lệnh sync này).
- **Trả lời**: Báo tiến trình đang chạy (mất 10-15s) rồi báo kết quả.

### 1.4 Lệnh `/cc end all` (Kết thúc toàn bộ văn bản chưa xử lý)
- **Hành động**: 
  1. Chạy `congvan_status.py list --status new` để lấy toàn bộ các `<số_vb>` đang `new`.
  2. Đọc `vbden_state.json` loại bỏ các VB đã `done`.
  3. **Yêu cầu xác nhận:** Hiển thị danh sách và hỏi: *"Có X văn bản chưa xử lý (...), bạn có chắc chắn muốn kết thúc tất cả không?"*
  4. NẾU đồng ý: Gộp tất cả các số VB cách nhau bằng dấu phẩy và chạy **1 LỆNH BATCH DUY NHẤT**:
     `uv run python /opt/data/skills/cc/scripts/congchuc_action.py kethuc <số_1>,<số_2>,<số_3> [lý do]`
     (Việc này xử lý toàn bộ các VB trong cùng 1 phiên trình duyệt, nhanh gấp 6 lần).
- **Trả lời**: Báo "Đang tiến hành kết thúc hàng loạt N văn bản trong 1 phiên..." và trả về báo cáo tổng kết.

### 1.5 Lệnh `/cc tai <số_vb>` (Tải đính kèm của văn bản)
- **Hành động**: Chạy lệnh: `uv run python /opt/data/skills/cc/scripts/congchuc_scrape.py --download-only <số_vb>`
- **Trước khi chạy**: Thông báo _"Đang tải file đính kèm cho VB #<số_vb>... (~20-30s)"_.
- **Trả lời**: Liệt kê các file đã tải (tên + dung lượng). Nếu lỗi, thông báo từ stderr.

### 1.6 Lệnh `/cc duthao <số_vb>` (Dự thảo văn bản)
- **Hành động**: Chạy lệnh: `uv run python /opt/data/skills/cc/scripts/congchuc_draft.py --so-den <số_vb> --zalo` (Bỏ `--zalo` nếu user không muốn gửi qua Zalo).
- **Trả lời**: Thông báo "Đang tạo dự thảo..." và báo kết quả sau khi hoàn tất.

### 1.7 Lệnh `/cc tomtat <số_vb>` (Tóm tắt văn bản)
- **Hành động**: Chạy lệnh: `uv run python /opt/data/skills/cc/scripts/congchuc_summarize.py --so-den <số_vb>`
- **Lưu ý**: Script tự xử lý mọi thứ (tải file nếu chưa có, đọc PDF/DOCX, đưa cho LLM).
- **Trước khi chạy**: Thông báo "Đang tóm tắt VB #<số_vb>..." (có thể mất 30–120s nếu script phải tự động tải file đính kèm trước).
- **Trả lời**: Trả về kết quả tóm tắt. Nếu script in lỗi có chứa chuỗi "Lỗi khi gọi AI tóm tắt" hoặc "vui lòng đợi cronjob", tự đọc file bằng code Python (xem `troubleshooting.md`) rồi tự tóm tắt.

### 1.8 Lệnh `/cc hieudinh <số_vb>` hoặc `/cc sualoi <đường_dẫn_file>` (Soát lỗi & Hiệu đính)
- **Hành động**: Chạy lệnh: `uv run python /opt/data/skills/cc/scripts/congchuc_editor.py --so-den <số_vb> --zalo` hoặc `uv run python /opt/data/skills/cc/scripts/congchuc_editor.py --file-path <đường_dẫn_file> --zalo`.
- **Trả lời**: Thông báo "Đang soát lỗi và hiệu đính văn bản..." và báo cáo kết quả sau khi tạo xong 2 file Word đối chiếu (Bản Chuẩn hóa và Bản Tối ưu).

### 1.9 Lệnh `/cc vbdi <từ_khóa>` (Tìm kiếm văn bản đi)
- **Hành động**: Chạy lệnh: `uv run python /opt/data/skills/cc/scripts/congchuc_vbdi_search.py <từ_khóa>`
- **Trả lời**: Báo tiến trình tìm kiếm, sau đó trả về danh sách kết quả tìm thấy theo định dạng danh sách có đánh số, in đậm số ký hiệu và có trích yếu + đơn vị soạn thảo.

### 1.10 Lệnh `/cc help` (Hướng dẫn sử dụng)
- **Hành động**: Trả lời ngay lập tức.
- **Trả lời**: Hiển thị bảng tổng hợp danh sách các lệnh ở trên.

---

## 2. Quy trình thủ công (Manual Workflows)

### 2.1 Soạn văn bản góp ý
Khi người dùng yêu cầu "soạn góp ý" dựa trên nội dung văn bản đến:
1. Xác định danh nghĩa đơn vị (hỏi nếu chưa rõ).
2. Đọc file đính kèm hoặc tóm tắt trước nội dung.
3. Soạn nội dung góp ý dạng Markdown ở `/tmp/` cho người dùng duyệt.
4. Nếu yêu cầu xuất Word, dùng python-docx (xem `references/soan-congvan-word.md`). Tham khảo mẫu: `templates/gopy-template.md`.
*KHÔNG chạy tự động. Luôn cho người dùng xem và xác nhận trước khi xuất file.*

### 2.2 Viết bài giới thiệu / quảng cáo CC Skill
Khi được yêu cầu viết bài quảng cáo, mời đồng nghiệp dùng:
- Tham khảo bài mẫu đã duyệt tại: `references/gioi-thieu-cc-skill.md`.
- **Mấu chốt:** AI Pro (Gemini Pro/OpenAI), Zalo (thông báo) / Telegram (nhận file), quét tự động (tùy chỉnh tần suất), chốt văn bản Thông báo tự động, phân biệt rõ các lệnh `/cc list`, `/cc end`, `/cc tomtat`.

---

## Xử lý Lỗi & Tham khảo Kỹ thuật
Khi bạn gặp lỗi hệ thống, Chromium crash, EPIPE, timeout với Telerik RadDatePicker, permission denied, hoặc lỗi state file bị mất đồng bộ, **BẮT BUỘC ĐỌC** tài liệu tham khảo chi tiết tại:
👉 `references/troubleshooting.md`