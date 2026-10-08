---
name: cc
description: Quản lý công văn đến/đi trên cổng congchuc.quangninh.gov.vn (Quảng Ninh) - xem danh sách VB mới, kết thúc hoặc chuyển xử lý, tải đính kèm, tóm tắt, soạn dự thảo, hiệu đính chính tả/văn phong, tìm văn bản đi, theo dõi văn bản đi. Dùng khi người dùng gõ /cc (list, list web, end, end all, tai, tomtat, duthao, hieudinh, sualoi, vbdi, theodoi, help) HOẶC nói tự nhiên như "kết thúc giúp anh văn bản số 2534", "có công văn mới không", "tóm tắt VB 2497", "tải file đính kèm văn bản 2490", "soạn dự thảo trả lời", "soát lỗi file này", "tìm văn bản đi số 188" - kể cả khi người dùng không nhắc tới "cc" hay "công chức".
version: 2.1.0
author: Hermes Agent
metadata:
  hermes:
    tags: [congvan, quangninh, cc, congchuc]
    category: productivity
---

# Kỹ năng Quản lý Công văn (/cc)

## Nguyên tắc chạy lệnh

- Chỉ chạy các lệnh có trong tài liệu này, bằng tool thực thi command, rồi báo ngắn gọn kết quả thật từ stdout/stderr. Không suy đoán hay bịa số liệu: đây là dữ liệu hành chính, sai một số văn bản là gây hậu quả thật.
- Môi trường Linux (Docker). Dùng đường dẫn tuyệt đối; script nằm ở `/opt/data/skills/cc/scripts/`. Mọi script Python chạy bằng `uv run python` (không dùng `python` trần vì thiếu package).
- Các thao tác ghi lên cổng (`end`, `end all`, chuyển xử lý) không hoàn tác được. Chỉ chạy khi người dùng yêu cầu rõ ràng, và dựa vào kết quả script để báo, không tự đánh dấu "done" khi script lỗi.
- Lệnh chạy lâu hơn ~10s thì báo trước thời gian dự kiến để người dùng không tưởng bot bị treo.

## Bảng lệnh nhanh

| Lệnh | Chạy (đều bắt đầu bằng `uv run python /opt/data/skills/cc/scripts/`) |
|---|---|
| `/cc list` | `congvan_status.py list --status new` (đọc cache local) |
| `/cc list web` | `congvan_status.py list --status new --web` (quét trực tiếp web, cooldown 30s) |
| `/cc list --page <N>` | `congvan_status.py list --status new --page <N>` |
| `/cc list today` | xem 1.2 |
| `/cc end <số> [lý do]` | xem 1.3 |
| `/cc end all` | xem 1.4 |
| `/cc tai <số>` | `congchuc_scrape.py --download-only <số>` |
| `/cc tomtat <số>` | `congchuc_summarize.py --so-den <số>` |
| `/cc duthao <số>` | `congchuc_draft.py --so-den <số> --zalo` |
| `/cc hieudinh <số>` | `congchuc_editor.py --so-den <số> --zalo` |
| `/cc sualoi <đường_dẫn>` | `congchuc_editor.py --file-path <đường_dẫn> --zalo` |
| `/cc vbdi <từ_khóa>` | `congchuc_vbdi_search.py <từ_khóa>` |
| `/cc theodoi <số>` | `uv run python /opt/data/skills/cc/lib/cc_router.py "v1\|cc\|run\|theodoi\|<số>"` |
| `/cc help` | trả lời ngay bằng bảng này |

Bỏ `--zalo` ở `duthao`/`hieudinh`/`sualoi` nếu người dùng không muốn gửi file qua Zalo.

---

## 1. Chi tiết từng lệnh

### Định dạng danh sách (áp dụng cho `list`, `list web`, `list today`, `vbdi`)
- Đánh số `1. `, `2. `; in đậm mã VB và đơn vị gửi (`**#2534**`) vì cầu Zalo chuyển `**` thành chữ đậm.
- Dùng emoji vừa phải, để dòng trống giữa các mục cho dễ đọc.
- Hiển thị đủ toàn bộ VB của trang hiện tại, không tự cắt bớt. Nếu kết quả có gợi ý `--page`, nhắc người dùng gõ `/cc list --page <N+1>` để xem tiếp.

### 1.1 `/cc list`, `/cc list web`, `/cc list --page <N>`
- `list` chỉ đọc cache `vbden_state.json`, không truy cập web. Nếu người dùng nghi ngờ danh sách thiếu so với web thì chuyển sang `list web`.
- `list web` mất ~20-30s: báo trước _"⏳ Đang kết nối trực tiếp cổng công chức để quét đồng bộ (~20-30s)..."_ rồi mới chạy. Script có cooldown 30s; nếu in thông báo "vừa đồng bộ lúc ..." thì chuyển nguyên văn cho người dùng, không chạy lại.
- Nếu script không nhận cờ `--web`/`--page` (in "Unknown command" hoặc không có output), nghĩa là tính năng chưa được triển khai trên máy này: nói thẳng với người dùng và trả danh sách từ `list --status new`.

### 1.2 `/cc list today`
Output của `list` hiện không có cột ngày, nên không lọc "hôm nay" đáng tin cậy được. Chạy `list --status new`, trả danh sách và nói rõ là chưa lọc theo ngày. Không đoán ngày từ nội dung trích yếu.

### 1.3 `/cc end <số> [lý do]`
1. Kiểm tra trạng thái: `uv run python /opt/data/skills/cc/scripts/congvan_status.py status <số>`. Nếu đã `done` thì báo người dùng và dừng.
2. Báo "Đang kết thúc VB #<số> (~15-30s)...", rồi chạy:
   `uv run python /opt/data/skills/cc/scripts/congchuc_action.py kethuc <số> [lý do]`
3. Nếu script báo ✅: `congchuc_action.py` đã tự động xác minh trên grid và cập nhật state chính thành `done`.
4. Nếu script báo ❌: chuyển nguyên văn lỗi cho người dùng, không tự ý sửa state. Riêng lỗi "Không tìm thấy văn bản ... trên danh sách grid": VB có thể đã được xử lý trên web, nằm ngoài 15 trang đầu, hoặc thuộc đơn vị khác. Hỏi người dùng có muốn đánh dấu `done` cục bộ không, chỉ làm khi họ xác nhận:
   `uv run python /opt/data/skills/cc/scripts/congvan_status.py done <số>`

### 1.4 `/cc end all`
1. Chạy `congvan_status.py list --status new` để lấy các VB đang `new` (bỏ VB đã `done`). Nếu danh sách chia nhiều trang, lấy hết các trang.
2. Hiển thị danh sách và hỏi: _"Có X văn bản chưa xử lý (...), bạn chắc chắn muốn kết thúc tất cả?"_. Chỉ tiếp tục khi người dùng đồng ý.
3. Gộp các số bằng dấu phẩy và chạy MỘT lệnh batch (cùng 1 phiên trình duyệt, nhanh hơn; ước tính ~10s/VB):
   `uv run python /opt/data/skills/cc/scripts/congchuc_action.py kethuc <số_1>,<số_2>,<số_3> [lý do]`
4. Script đã có bước xác minh trên grid sau từng VB trước khi lưu `done`. Đọc output để biết VB nào thành công (dòng `✅ #<số>`) và VB nào thất bại (mục "Thất bại").
   - Nếu script chạy ở môi trường chuẩn: state đã tự động cập nhật cho từng VB thành công.
   - Nếu chạy trong môi trường có ghi đè biến môi trường state: chỉ đồng bộ state cho các VB có `✅ #<số>`:
     ```bash
     for vb in <các số thành công>; do
       uv run python /opt/data/skills/cc/scripts/congvan_status.py done "$vb"
     done
     ```
   Không đồng bộ VB thất bại; báo riêng danh sách và lý do cho người dùng.

### 1.5 `/cc tai <số>`
Báo _"Đang tải file đính kèm VB #<số> (~20-30s)..."_, chạy lệnh trong bảng. File lưu ở `/opt/data/cron/cong-van-den/attachments/<số>/`. Trả về tên file và dung lượng; nếu lỗi thì nêu nội dung stderr.

### 1.6 `/cc tomtat <số>`
- Script tự tải đính kèm nếu chưa có, đọc PDF/DOCX rồi gọi LLM, nên có thể mất 30-120s. Báo trước _"Đang tóm tắt VB #<số>..."_.
- Nếu output chứa "Lỗi khi gọi AI tóm tắt" hoặc "vui lòng đợi cronjob", đọc file đính kèm bằng code Python (xem `references/tomtat-detail.md`) rồi tự tóm tắt.
- Giới hạn định dạng: file `.doc` (Word cũ) không đọc được do thiếu công cụ, nhờ người dùng chuyển sang `.docx`/PDF; PDF scan không có lớp chữ thì cần OCR (ví dụ tesseract) hoặc người dùng gửi nội dung.

### 1.7 `/cc duthao`, `/cc hieudinh`, `/cc sualoi`
Báo đang xử lý, chạy lệnh trong bảng. `duthao` tạo dự thảo chuẩn NĐ30. `hieudinh`/`sualoi` tạo 2 file Word đối chiếu (Bản chuẩn hóa và Bản tối ưu); báo kết quả sau khi tạo xong.

### 1.8 `/cc vbdi <từ_khóa>`
Báo đang tìm, chạy lệnh, trả danh sách theo định dạng chung kèm số ký hiệu, trích yếu và đơn vị soạn thảo.

### 1.9 `/cc theodoi <số>`
Lệnh gọi router theo định dạng callback ở bảng trên; nó ghi văn bản vào danh sách theo dõi và cron quét văn bản đi sẽ báo khi thấy. Chuyển nguyên văn kết quả router cho người dùng.

### 1.10 Chuyển xử lý (nâng cao, chưa có slash command)
Chỉ khi người dùng yêu cầu rõ ràng "chuyển VB <số> cho <đơn vị>": xác nhận lại đơn vị nhận trước khi chạy:
`uv run python /opt/data/skills/cc/scripts/congchuc_action.py chuyen <số> "<đơn_vị_nhận> [bút phê]"`
(token đầu tiên là đơn vị nhận, phần còn lại là bút phê). Nếu ✅ thì đồng bộ `congvan_status.py wip <số>` (chuyển xử lý là `wip`, không phải `done`).

---

## 2. Quy trình thủ công

- **Soạn văn bản góp ý**: xác định danh nghĩa đơn vị (hỏi nếu chưa rõ), đọc hoặc tóm tắt VB gốc, soạn Markdown ở `/tmp/` cho người dùng duyệt (mẫu `templates/gopy-template.md`). Chỉ xuất Word (python-docx, xem `references/soan-congvan-word.md`) sau khi người dùng xác nhận nội dung.
- **Viết bài giới thiệu CC Skill**: dùng bài đã duyệt ở `references/gioi-thieu-cc-skill.md` làm gốc; giữ các điểm chốt trong đó.

---

## 3. Khi gặp lỗi

Đọc các tài liệu tham chiếu trong `references/` trước khi thử cách khác:

| Triệu chứng | Tài liệu tham chiếu |
|---|---|
| Login thất bại, mật khẩu yếu | `references/kethuc-playwright-pitfalls.md` (§1, §1b) |
| Playwright tranh chấp, Chromium crash, `write EPIPE` | `references/kethuc-playwright-pitfalls.md` (§2) |
| Timeout khi chạy Playwright | `references/kethuc-playwright-pitfalls.md` (§3) |
| Không tìm thấy văn bản trên grid | `references/kethuc-playwright-pitfalls.md` (§4) |
| Tóm tắt sai/thiếu, `congvan_detail.py` hiện nhầm VB | `references/tomtat-detail.md` |
| Quét văn bản đi lỗi | `references/vbdi-scrape-fix.md`, `references/congchuc-scrape-reference.md` |

**EPIPE & Tranh chấp phiên**: Thường do nhiều tiến trình Playwright hoặc OpenAM SSO session contention. Toàn bộ các script runtime hiện đã được đồng bộ qua lock tập trung `launch_browser_locked` (file lock cố định tại `/opt/data/cron/cong-van-den/.playwright.lock`). Nếu vẫn gặp sự cố, kiểm tra xem có tiến trình nào treo không, chờ ~30s rồi thử lại; nếu cần thì xóa `.playwright_storage.json` để đăng nhập lại. Tuyệt đối không dùng `congvan_status.py done` để "vượt" lỗi: VB trên cổng vẫn chưa xử lý nhưng bot sẽ báo sai là đã xong.