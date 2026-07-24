---
name: cc
description: Hệ thống tương tác quản lý công văn đến/đi tại Quảng Ninh qua Hermes Agent. Kích hoạt khi người dùng gõ slash command `/cc` (list, list today, end <số> [lý do], end all, tai <số>, duthao <số>, tomtat <số>, help), VÀ CŨNG kích hoạt khi họ diễn đạt cùng ý bằng ngôn ngữ tự nhiên mà không gõ đúng cú pháp — ví dụ "có văn bản mới nào không", "kết thúc giúp anh văn bản số 2534", "tóm tắt công văn 2534 xem nội dung gì", "tải file đính kèm của văn bản đó", "soạn dự thảo cho công văn này", "viết bài giới thiệu để mời đồng nghiệp dùng CC skill". Luôn dùng skill này thay vì tự suy đoán khi câu hỏi liên quan tới công văn/công chức Quảng Ninh.
version: 2.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [congvan, quangninh, cc, congchuc]
    category: productivity
---

# Kỹ năng Quản lý Công văn (/cc)

Khi người dùng gọi `/cc` kèm lệnh phụ — hoặc diễn đạt cùng ý định bằng lời thường — hãy thực hiện đúng hướng dẫn dưới đây.

**Nguyên tắc nền tảng:** Mọi số liệu (danh sách văn bản, trạng thái, nội dung) BẮT BUỘC phải lấy từ việc chạy script thực tế bằng tool thực thi command (`terminal`/shell), không được tự bịa. Môi trường là Linux (Docker); luôn dùng đường dẫn tuyệt đối bắt đầu bằng `/opt/data`. Các script đã tồn tại sẵn ở `/opt/data/scripts/congchuc/` — không cần tạo mới.

## Bảng lệnh nhanh

| Lệnh | Việc làm | Thời gian |
|---|---|---|
| `/cc list` | Liệt kê văn bản mới (status `new`) | ~vài giây |
| `/cc list today` | Liệt kê văn bản cập nhật hôm nay | ~vài giây |
| `/cc end <số> [lý do]` | Kết thúc 1 văn bản trên cổng | ~10-15s |
| `/cc end all` | Kết thúc toàn bộ văn bản `new` (cần xác nhận) | ~10-15s/VB |
| `/cc tai <số>` | Tải file đính kèm | ~20-30s |
| `/cc duthao <số>` | Soạn dự thảo `.docx`, gửi qua Zalo | ~15-30s |
| `/cc tomtat <số>` | Tóm tắt nội dung văn bản | ~30-60s |
| `/cc help` | Hiển thị hướng dẫn | tức thì |

**Quy tắc bắt buộc dùng chung** cho mọi script Python: luôn gọi bằng `uv run python` (không dùng `python` trần) — môi trường Hermes Agent chạy trong `uv venv`, các package (`openai`, `playwright`, `python-docx`, `fitz`...) chỉ có ở đó.

## Hướng dẫn xử lý từng lệnh

### 1. `/cc list` — Liệt kê văn bản mới
Chạy: `uv run python /opt/data/scripts/congchuc/congvan_status.py list --status new`

Trình bày kết quả theo quy tắc định dạng dưới đây (áp dụng cho cả lệnh `list` và `list today`):
1. Danh sách đánh số `1. `, `2. ` (không dùng icon thay số thứ tự).
2. In đậm mã số văn bản bằng `**` (ví dụ `**#2534**`) và tên đơn vị gửi — để Zalo Bridge hiển thị in đậm đúng.
3. Dùng emoji sinh động, giãn dòng thoáng để dễ đọc trên Zalo/Telegram.

### 2. `/cc list today` — Liệt kê văn bản hôm nay
Chạy: `uv run python /opt/data/scripts/congchuc/congvan_status.py list` (không filter), sau đó tự lọc ra các văn bản có ngày cập nhật = hôm nay từ kết quả trả về. Trình bày theo cùng quy tắc định dạng ở mục 1.

### 3. `/cc end <số_vb> [lý do]` — Kết thúc văn bản
1. **Pre-check**: đọc `vbden_state.json`. Nếu đã `status: "done"` → báo user và dừng (tránh chạy Playwright ~15-30s không cần thiết).
2. Nếu chưa done, chạy:
   `HERMES_HOME=/tmp uv run python /opt/data/scripts/congchuc/congchuc_action.py kethuc <số_vb> [lý do]`
   (`[lý do]` tuỳ chọn, mặc định "Đã hoàn thành xử lý.")
3. **Đồng bộ state (bắt buộc)** — sau khi script báo ✅, chạy tiếp:
   `uv run python /opt/data/scripts/congchuc/congvan_status.py done <số_vb>`
   Lý do: `congchuc_action.py` ghi state vào `/tmp/`, còn `congvan_status.py` đọc từ state file chính ở `/opt/data/`. Bỏ qua bước này → VB vẫn hiện `[new]` dù đã xử lý xong trên cổng (xem `references/troubleshooting.md` mục "state file split").
4. Nếu retry và gặp "Không tìm thấy văn bản trên grid" → đây là tín hiệu **thành công** (VB đã xử lý, không còn ở tab Chưa xử lý). Vẫn chạy bước 3 để đồng bộ và báo user là done.
5. Trả lời: báo tiến trình (lệnh chạy ~10-15s vì phải mở web bấm kết thúc), sau đó trả kết quả cuối từ script.

### 4. `/cc end all` — Kết thúc toàn bộ văn bản chưa xử lý
1. Chạy `uv run python /opt/data/scripts/congchuc/congvan_status.py list --status new` để lấy toàn bộ `<số_vb>` đang `new`.
2. **Pre-filter**: đọc `vbden_state.json`, loại các VB đã `status: "done"` khỏi danh sách.
3. **Xác nhận trước khi chạy (bắt buộc)**: hiển thị danh sách số VB tìm được và hỏi: *"Có X văn bản chưa xử lý (danh sách: <số_1>, <số_2>,...), bạn có chắc chắn muốn kết thúc tất cả không?"* — chỉ tiếp tục khi user đồng ý.
4. Lặp qua từng số, chạy `HERMES_HOME=/tmp uv run python /opt/data/scripts/congchuc/congchuc_action.py kethuc <số_vb>`.
5. **Verify + đồng bộ state**: sau vòng lặp, chạy lại `congvan_status.py list --status new` — VB nào không còn trong kết quả thì chạy `congvan_status.py done <số_vb>`; VB nào vẫn còn thì cần retry.
6. Trả lời: báo "Đang tiến hành kết thúc N văn bản..." trước (vì chạy trình duyệt khá chậm, ~10-15s/VB), rồi báo kết quả sau khi xong.

### 5. `/cc tai <số_vb>` — Tải file đính kèm
Báo ngay: *"Đang tải file đính kèm cho VB #<số_vb>... (~20-30s)"*, sau đó chạy:
`uv run python /opt/data/scripts/congchuc/congchuc_scrape.py --download-only <số_vb>`
Script login Playwright, tìm VB trên grid, bấm "Tải tất cả file", giải nén ZIP, lưu vào `attachments/<số_vb>/`. Sau khi xong, liệt kê file đã tải (tên + dung lượng); nếu lỗi thì báo lỗi từ stderr.

### 6. `/cc duthao <số_vb>` — Soạn dự thảo văn bản
Báo *"Đang tiến hành tạo dự thảo cho văn bản <số_vb> và sẽ gửi trực tiếp qua Zalo sau khi hoàn tất..."* (~15-30s), rồi chạy:
`uv run python /opt/data/scripts/congchuc/congchuc_draft.py --so-den <số_vb> --zalo`
`--zalo` mặc định bật để tự gửi `.docx` qua Zalo sau khi tạo — bỏ tham số này nếu user không muốn gửi Zalo.

### 7. `/cc tomtat <số_vb>` — Tóm tắt văn bản
Báo *"Đang tóm tắt VB #<số_vb>..."* (có thể mất 30-60s nếu phải tải file trước), rồi chạy:
`uv run python /opt/data/skills/cc/scripts/congchuc_summarize.py --so-den <số_vb>`

Script tự chạy toàn bộ pipeline (không cần gọi thêm lệnh nào khác):
1. Lấy metadata (số CV, tác giả, trích yếu, trạng thái) từ `vbden_state.json`.
2. Kiểm tra `attachments/<số_vb>/`: có file → đọc PDF (`pymupdf`)/DOCX (`python-docx`); không có → tự tải qua `congchuc_scrape.py --download-only` rồi đọc.
3. Feed nội dung vào LLM → tóm tắt theo cấu trúc: Mục đích, Nội dung, Deadline, Đơn vị thực hiện, Đề xuất xử lý.

Nếu file là ảnh scan không đọc được text, báo rõ cho user. Nếu script báo "⚠️ LLM không phản hồi", tự đọc file thủ công bằng lệnh ở `references/troubleshooting.md` (mục "LLM không phản hồi") rồi tóm tắt bằng khả năng của Hermes.

### 8. Soạn văn bản góp ý (workflow thủ công, không phải slash command)
Khi user yêu cầu "soạn góp ý" dựa trên văn bản đến:
1. Xác định danh nghĩa đơn vị (hỏi nếu chưa rõ).
2. Đọc file PDF đính kèm bằng `uv run python` + `fitz` (hoặc chạy `congchuc_summarize.py` trước để có overview).
3. Soạn nội dung góp ý dạng Markdown ở `/tmp/`, cho user xem duyệt.
4. Nếu user muốn xuất Word, dùng `python-docx` — tham khảo `references/soan-congvan-word.md`.
5. Tham khảo mẫu ở `templates/gopy-template.md`.

Đây là workflow thủ công có sự duyệt của người dùng — không chạy script tự động, luôn hỏi ý kiến trước khi xuất file.

### 9. `/cc help`
Không cần chạy script. Hiển thị tóm tắt ngắn gọn các lệnh `/cc` (list, list today, end, end all, tai, duthao, tomtat) từ bảng lệnh nhanh ở trên.

### 10. Viết bài giới thiệu / quảng cáo CC Skill
Khi user yêu cầu viết bài mời đồng nghiệp dùng skill:
- Tham khảo `references/gioi-thieu-cc-skill.md` — bản đã được sếp duyệt qua nhiều vòng refine.
- Điểm mấu chốt cần giữ đúng:
  1. AI Pro = **Gemini Pro hoặc OpenAI** (không ghi GPT-4o).
  2. Zalo phổ biến hơn cho thông báo nhanh; Telegram gửi file tốt hơn.
  3. Tần suất quét tùy chỉnh được (mặc định mỗi giờ, có thể 5 phút/lần nhưng tốn phí AI hơn).
  4. Tự động kết thúc VB dạng Thông báo/Để biết.
  5. Chi phí cài đặt: "1 bữa bia".
  6. Phân biệt rõ các lệnh: `/cc end` (1 VB), `/cc end all` (hàng loạt), `/cc tomtat`, `/cc tai`, `/cc duthao`.

## Khi gặp lỗi hoặc cần debug

Đọc `references/troubleshooting.md` khi gặp các tình huống sau — đừng tự đoán, file này chứa nguyên nhân gốc và cách fix đã được xác nhận:
- Script báo ✅ nhưng `/cc list` vẫn hiện `[new]`
- Lỗi ghi file / `Permission denied` trong `/opt/data`
- Playwright timeout khi thao tác với ô ngày tháng (Telerik date picker)
- Chromium crash / `write EPIPE` trong Docker
- Cron "Quet cong van di" báo lỗi
- Muốn sửa script trong `/opt/data/scripts/congchuc/` (thuộc quyền root)
