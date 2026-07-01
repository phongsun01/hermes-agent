---
name: cc
description: Hệ thống tương tác xử lý công văn Quảng Ninh. Hỗ trợ /cc list, /cc list today, /cc end &lt;số&gt; [lý do], /cc end all, /cc tai &lt;số&gt;, /cc duthao &lt;số&gt;, /cc tomtat &lt;số&gt;, /cc help.
version: 1.9.0
author: Hermes Agent
metadata:
  hermes:
    tags: [congvan, quangninh, cc, congchuc]
    category: productivity
---

# Kỹ năng Quản lý Công văn (/cc)

Khi người dùng gọi slash command `/cc` kèm theo các lệnh phụ, hãy phân tích yêu cầu và thực hiện chính xác các hướng dẫn dưới đây.

LƯU Ý BẮT BUỘC: Bạn CHỈ ĐƯỢC CHẠY các lệnh sau đây bằng tool thực thi command (như `terminal` hoặc công cụ shell bạn có) và thông báo ngắn gọn kết quả cho người dùng, tuyệt đối không tự bịa thông tin. Môi trường của bạn là Linux (Docker), hãy dùng đường dẫn TUYỆT ĐỐI bắt đầu bằng `/opt/data`. (Các script ĐÃ TỒN TẠI ở thư mục `/opt/data/scripts/congchuc/`).

## Hướng dẫn xử lý các Lệnh phụ:

### 1. Lệnh `/cc list` (Liệt kê các văn bản mới)
- **Hành động**: Chạy đoạn script lấy các văn bản mới:
  `uv run python /opt/data/scripts/congchuc/congvan_status.py list --status new`
- **Trả lời**: Liệt kê kết quả đọc được cho user một cách gọn gàng.
  **QUY TẮC ĐỊNH DẠNG BẮT BUỘC:**
  1. Sử dụng danh sách có đánh số thứ tự rõ ràng dạng `1. `, `2. ` (không dùng các icon chung chung như `📄` để thay thế số thứ tự).
  2. Định dạng in đậm bằng dấu sao kép `**` cho mã số văn bản (ví dụ: `**#2534**`) và tên đơn vị gửi để Zalo Bridge có thể hiển thị in đậm tương ứng.
  3. Dùng emoji sinh động và giữ khoảng cách dòng thoáng đãng, dễ đọc.

### 2. Lệnh `/cc list today` (Liệt kê văn bản hôm nay)
- **Hành động**: Bạn hãy chạy script Python:
  `uv run python /opt/data/scripts/congchuc/congvan_status.py list`
  Sau đó từ kết quả trả về, dùng kỹ năng lập luận của bạn để **chỉ lọc ra và hiển thị** các văn bản có ngày cập nhật trùng với ngày hôm nay.
- **Trả lời**: Hiển thị danh sách kết quả cho người dùng.
  *Áp dụng cùng quy tắc định dạng bắt buộc ở mục 1 (in đậm số VB bằng `**`, đánh số thứ tự `1. `, `2. `).*

### 3. Lệnh `/cc end <số_vb> [lý do]` (Kết thúc văn bản)
- **Hành động**: 
  1. **Pre-check:** Đọc `vbden_state.json` kiểm tra trạng thái. Nếu đã `status: "done"` → báo user và bỏ qua (tiết kiệm ~15-30s không chạy Playwright vô ích).
  2. Nếu chưa done, chạy kết thúc trên cổng:
     `HERMES_HOME=/tmp uv run python /opt/data/scripts/congchuc/congchuc_action.py kethuc <số_vb> [lý do]`
     Trong đó `[lý do]` là tuỳ chọn — nếu không có, script dùng mặc định "Đã hoàn thành xử lý."
  3. **Post-run state sync (bắt buộc)**: Sau khi script báo ✅ thành công, chạy:
     `uv run python /opt/data/scripts/congchuc/congvan_status.py done <số_vb>`
     Vì script action ghi trạng thái vào state file trong `/tmp/`, còn `congvan_status.py` đọc từ state file chính. Bỏ qua bước này → VB vẫn hiển thị `[new]` dù đã kết thúc trên cổng.
- **Trả lời**: Thông báo lại tiến trình (lệnh này sẽ chạy mất khoảng 10-15s để vào web bấm kết thúc). Trả lại thông báo kết quả cuối cùng từ script (thành công hay thất bại).
- **Lưu ý nếu gặp "Không tìm thấy"**: Khi retry và gặp "Không tìm thấy văn bản trên grid" → đó là tín hiệu THÀNH CÔNG (VB đã được xử lý, không còn trên tab Chưa xử lý). Vẫn chạy `congvan_status.py done <số_vb>` và báo user là done.

### 4. Lệnh `/cc end all` (Kết thúc toàn bộ văn bản chưa xử lý)
- **Hành động**: 
  1. Đầu tiên, chạy `uv run python /opt/data/scripts/congchuc/congvan_status.py list --status new`
  2. Phân tích kết quả để tìm ra TẤT CẢ các `<số_vb>` đang ở trạng thái `new`.
  3. **Pre-filter:** Đọc `vbden_state.json`, loại bỏ các VB đã có `status: "done"` khỏi danh sách (tránh chạy Playwright vô ích).
  4. **Yêu cầu xác nhận (Safeguard):** Trước khi bắt đầu vòng lặp thực hiện kết thúc trên web, hãy hiển thị danh sách các số văn bản tìm được và hỏi xác nhận từ người dùng: *"Có X văn bản chưa xử lý (danh sách: <số_1>, <số_2>,...), bạn có chắc chắn muốn kết thúc tất cả không?"*
  5. Chỉ thực hiện khi người dùng trả lời đồng ý/xác nhận. Nếu đồng ý, lặp qua và chạy `HERMES_HOME=/tmp uv run python /opt/data/scripts/congchuc/congchuc_action.py kethuc <số_vb>` cho từng số đến.
  6. **Post-run verify + state sync**: Sau khi vòng lặp Playwright kết thúc (hoặc timeout), chạy `uv run python /opt/data/scripts/congchuc/congvan_status.py list --status new` để kiểm tra. Với mỗi VB từ danh sách gốc không còn trong kết quả → chạy `congvan_status.py done <số_vb>` để đồng bộ state. Với VB vẫn còn trong kết quả → cần retry action.
- **Trả lời**: Thông báo tiến trình cho người dùng, do lệnh chạy trình duyệt khá chậm (khoảng 10-15s / văn bản) nên bạn có thể nhắn tin "Đang tiến hành kết thúc N văn bản..." trước, sau đó chờ và thông báo kết quả.

### 5. Lệnh `/cc tai <số_vb>` (Tải đính kèm của văn bản)
- **Hành động**: Gọi hàm tải file đính kèm trực tiếp (không phải chờ cron):
  `uv run python /opt/data/scripts/congchuc/congchuc_scrape.py --download-only <số_vb>`
  Script sẽ login Playwright, tìm VB trên grid, click "Tải tất cả file", giải nén ZIP và lưu file vào `attachments/<số_vb>/`. Lệnh này mất khoảng 20-30s.
- **Trước khi chạy**, thông báo ngay: _"Đang tải file đính kèm cho VB #<số_vb>... (~20-30s)"_
- **Trả lời**: Sau khi lệnh kết thúc, liệt kê các file đã tải (tên + dung lượng). Nếu thất bại, thông báo lỗi từ stderr.
  

### 6. Lệnh `/cc duthao <số_vb>` (Dự thảo văn bản)
- **Hành động**: Chạy lệnh tạo dự thảo bằng Python:
  `uv run python /opt/data/scripts/congchuc/congchuc_draft.py --so-den <số_vb> --zalo`
  *(Mặc định thêm tham số `--zalo` để tự động gửi file `.docx` dự thảo sang Zalo chat sau khi tạo xong. Nếu người dùng không muốn gửi Zalo, có thể chạy bỏ `--zalo` đi).*
- **Trả lời**: Trả lời người dùng là "Đang tiến hành tạo dự thảo cho văn bản <số_vb> và sẽ gửi trực tiếp qua Zalo sau khi hoàn tất...". Lệnh này sẽ mất khoảng 15-30s. Sau khi chạy xong, thông báo kết quả.

### 7. Lệnh `/cc tomtat <số_vb>` (Tóm tắt văn bản)
- **Hành động**: Chạy script tóm tắt đầy đủ:
  `uv run python /opt/data/skills/cc/scripts/congchuc_summarize.py --so-den <số_vb>`
  
  Script tự động thực hiện toàn bộ pipeline:
  1. Lấy metadata (số CV, tác giả, trích yếu, trạng thái) từ `vbden_state.json`
  2. Kiểm tra `attachments/<số_vb>/` có file không:
     - **Có file** → đọc nội dung PDF (pymupdf) / DOCX (python-docx)
     - **Không có file** → tự động tải về qua `congchuc_scrape.py --download-only` (~20-30s), rồi đọc
  3. Feed nội dung file vào LLM → tóm tắt theo cấu trúc: Mục đích, Nội dung, Deadline, Đơn vị thực hiện, Đề xuất xử lý

- **Trước khi chạy**: Thông báo "Đang tóm tắt VB #<số_vb>..." vì có thể mất 30-60s nếu phải tải file trước.
- **Trả lời**: Trả về kết quả tóm tắt từ LLM. Nếu file là ảnh scan (không đọc được text), thông báo rõ cho người dùng.
- **Lưu ý**: Script này **không cần** gọi `congchuc_summarize.py` rồi `congvan_status.py` riêng — tất cả được tích hợp trong 1 lần chạy.
- **LLM không phản hồi**: Nếu script báo "⚠️ LLM không phản hồi", có thể tự đọc file thủ công và tóm tắt bằng khả năng của Hermes:
  ```bash
  # Đọc DOCX
  uv run python -c "from docx import Document; d=Document('/opt/data/cron/cong-van-den/attachments/<số_vb>/*.docx'); print('\n'.join(p.text for p in d.paragraphs if p.text.strip()))"
  # Đọc PDF  
  uv run python -c "import fitz; doc=fitz.open('/opt/data/cron/cong-van-den/attachments/<số_vb>/*.pdf'); [print(doc[i].get_text()) for i in range(doc.page_count)]; doc.close()"
  ```
  Sau đó phân tích và tóm tắt thủ công cho sếp.


### 8. Soạn văn bản góp ý (workflow — không phải slash command)

Khi người dùng yêu cầu "soạn góp ý" dựa trên nội dung văn bản đến:
- **Bước 1**: Xác định danh nghĩa đơn vị (hỏi nếu chưa rõ)
- **Bước 2**: Đọc file PDF đính kèm bằng `uv run python` với `fitz` (hoặc dùng `congchuc_summarize.py` trước để có overview)
- **Bước 3**: Soạn nội dung góp ý dạng Markdown ở `/tmp/`, cho người dùng xem duyệt
- **Bước 4**: Nếu người dùng yêu cầu xuất Word, dùng python-docx (tham khảo `references/soan-congvan-word.md`)
- **Tham khảo mẫu**: `templates/gopy-template.md`

*Lưu ý:* Không chạy script tự động — workflow thủ công có sự duyệt của người dùng. Luôn hỏi ý kiến trước khi xuất file.

### 9. Lệnh `/cc help` (Hướng dẫn sử dụng)
- **Hành động**: Không cần chạy lệnh nào cả. 
- **Trả lời**: Hiển thị tóm tắt ngắn gọn danh sách các lệnh `/cc` (list, list today, end, end all, tai, duthao, tomtat) cho người dùng.

### 10. Viết bài giới thiệu / quảng cáo CC Skill
Khi người dùng yêu cầu "viết bài giới thiệu" hoặc "quảng cáo" để mời đồng nghiệp dùng:
- **Tham khảo** file `references/gioi-thieu-cc-skill.md` — đây là bản đã được sếp duyệt qua nhiều vòng refine.
- Các điểm mấu chốt khi viết:
  1. AI Pro = **Gemini Pro hoặc OpenAI** (không ghi GPT-4o — sếp đã sửa)
  2. Zalo phổ biến hơn cho thông báo nhanh, Telegram hỗ trợ gửi file tốt hơn
  3. Tần suất quét tùy chỉnh được (mặc định mỗi giờ, có thể 5 phút/lần nhưng tốn phí AI hơn)
  4. Tự động kết thúc VB dạng Thông báo/Để biết
  5. Chi phí cài đặt: "1 bữa bia"
  6. Phân biệt rõ các lệnh: `/cc end` (kết thúc 1 VB), `/cc end all` (kết thúc hàng loạt), `/cc tomtat` (tóm tắt), `/cc tai` (tải file đính kèm), `/cc duthao` (soạn dự thảo)

## Lưu ý & Xử lý lỗi thường gặp

### uv run bắt buộc cho tất cả script Python
Môi trường Hermes Agent dùng uv venv, các package (openai, playwright, python-docx, fitz...) chỉ có trong uv. **Tất cả script Python** đều phải gọi với `uv run python`, kể cả `congvan_status.py` và `congchuc_draft.py`. Không dùng `python` trần.

### 9p mount & quyền ghi
Thư mục `/opt/data/` là 9p mount từ Windows (Docker Desktop + WSL), chủ sở hữu root, user hermes không thể tạo thư mục con hoặc ghi file vào các thư mục chưa tồn tại trong `/opt/data/`. Khi script cố gắng tạo thư mục (attachments, screenshots, logs) sẽ gặp `Permission denied`.

**Lưu ý về quyền ghi:**
- `/opt/data/cron/cong-van-den/attachments/` → 777 ✅ (ghi được trực tiếp)
- `/opt/data/cron/cong-van-den/action_logs/last_result.txt` → thuộc root, ❌ không ghi được

**Cách 1 — `congchuc_scrape.py` (`/cc tai`)**: Thư mục attachments đã có quyền 777, nên **không cần** set `HERMES_HOME`:
```bash
uv run python /opt/data/scripts/congchuc/congchuc_scrape.py --download-only <số_vb>
```
File đính kèm lưu tại `/opt/data/cron/cong-van-den/attachments/<số_vb>/`.

**Cách 2 — `congchuc_action.py` (`/cc end`)**: Vẫn **cần** `HERMES_HOME=/tmp` vì script ghi vào `action_logs/last_result.txt` (thuộc root):
```bash
HERMES_HOME=/tmp uv run python /opt/data/scripts/congchuc/congchuc_action.py kethuc <số_vb> [lý do]
```
Screenshot và log lưu tại `/tmp/cron/cong-van-den/attachments/<số_vb>/` và `/tmp/cron/cong-van-den/action_logs/`.

### Lưu ý Telerik date picker (hidden input)
Một số trang (tabid=1121 Văn bản đi) dùng Telerik RadDatePicker — input date thực tế bị **hidden**, `page.fill()` sẽ timeout vì element không visible.
**Cách fix:** Dùng `page.evaluate()` set value bằng JavaScript thay vì `page.fill()`:
```python
page.evaluate(f"""
    var el = document.getElementById('..._dateInput');
    if (el) {{ el.value = '{date_str}'; var e = new Event('change'); el.dispatchEvent(e); }}
""")
```
Script gốc `congchuc_vbdi_scrape.py` mắc lỗi này. Bản fix đã deploy ở `~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py` và cron job đã trỏ sang script fix.

### Vấn đề state file split (quan trọng)
Có HAI state file `vbden_state.json` được dùng song song:
- **State chính** (đọc bởi `congvan_status.py` để trả lời `/cc list`): `/opt/data/cron/cong-van-den/vbden_state.json` — cập nhật bởi cron job và lệnh `congvan_status.py done/read/wip`.
- **State /tmp** (ghi bởi `congchuc_action.py` với `HERMES_HOME=/tmp`): `/tmp/cong-van-den/cron/cong-van-den/vbden_state.json` — chỉ chứa log action script.

**Hệ quả:** Sau `/cc end` state chính KHÔNG tự động sync. Bắt buộc chạy thêm `congvan_status.py done <số_vb>` sau action. Nếu bỏ qua, VB vẫn hiển thị `[new]` dù đã kết thúc trên cổng.

### Giải thích lỗi thường gặp
- **Script báo ✅ nhưng status vẫn `[new]`**: Nguyên nhân = state file split. Luôn kiểm tra trên grid portal thay vì chỉ dựa vào state local.
- **"Không tìm thấy trên grid" (khi retry `/cc end`)**: Đây là tín hiệu THÀNH CÔNG — VB đã được xử lý, không còn trên tab Chưa xử lý. Chỉ cần sync state là xong. Nếu xảy ra ở lần chạy ĐẦU → lỗi thật (cần kiểm tra grid filter / phân trang).
- **VB không tìm thấy ngay lần chạy đầu**: Có thể do grid phân trang — script chỉ duyệt 15 trang đầu. Hoặc grid có bộ lọc đang hiển thị tab khác.

### Telerik RadDatePicker hidden input — `page.fill()` timeout
Các grid trên congchuc.quangninh.gov.vn dùng Telerik RadControls. Input date (`<input id="..._dateInput">`) bị **hidden** — Playwright `page.fill()` sẽ timeout vì "element is not visible".

**Fix:** Dùng `page.evaluate()` set value bằng JavaScript + trigger change event:
```python
page.evaluate(f"""
    var el = document.getElementById('..._dateInput');
    el.value = '{date_value}';
    var evt = document.createEvent('HTMLEvents');
    evt.initEvent('change', true, true);
    el.dispatchEvent(evt);
""")
```
Không dùng `page.fill()`, `page.locator().fill()`, hay `page.type()` cho các input date của Telerik.

**Bài học rộng hơn:** Bất kỳ input nào trong Telerik RadGrid/RadDatePicker mà bị hidden (display:none / visibility:hidden) → dùng JS evaluate thay vì Playwright fill.

### Cron quét văn bản đi — script và lỗi thường gặp
Cron "Quet cong van di" (job `d7f9e2c1a4b6`) chạy `congchuc/congchuc_vbdi_scrape.py` với tham số `no_agent=true`. Script này quét tabid=1121 (Văn bản đi), lọc theo ngày phát hành 2 ngày gần nhất.

**Lỗi phổ biến:** `page.fill()` timeout do input date hidden (xem mục Telerik ở trên). Script gốc silent catch exception → retry hết lượt → trả về rỗng → cron báo `error` dù không có output lỗi rõ.

**Script fix đã deploy:**
```bash
# Đặt tại ~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py
# Fix: page.evaluate() thay page.fill(), thêm --disable-dev-shm-usage --disable-gpu
```
Chứa đầy đủ logic gốc + JS evaluate cho date input + Chromium args bổ sung để ổn định trong Docker.

**Cập nhật cron khi deploy script fix:**
```bash
# Cần copy script vào ~/./scripts/congchuc/ (relative path yêu cầu của cron)
cp <path_to_fixed> ~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py
# Sau đó update cron
cronjob action=update job_id=d7f9e2c1a4b6 script=congchuc/congchuc_vbdi_scrape_fixed.py
```

### Chromium crash / EPIPE trong Docker
Khi chạy Playwright trong Docker, Chromium có thể crash với lỗi `write EPIPE` (broken pipe). Nguyên nhân thường gặp:
1. Shared memory `/dev/shm` nhỏ — thêm `--disable-dev-shm-usage`
2. GPU không khả dụng — thêm `--disable-gpu`
3. Zombie Chromium process từ lần chạy trước

**Fix:** Luôn thêm các arg này khi launch Chromium:
```python
browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
```
Nếu vẫn EPIPE: `rm -f .playwright_storage.json` để force fresh login (storage state cũ có thể corrupted).

### Định dạng output cron notification (bôi đậm)

Cron jobs no_agent (`congchuc_scrape.py` cho VB đến, `congchuc_vbdi_scrape.py` cho VB đi) output trực tiếp stdout → Zalo. Để tin nhắn dễ đọc, dùng `**bold**` markdown cho các trường quan trọng trong script:

| Trường | Ví dụ |
|---|---|
| Số đến | `**#2534**` |
| Số ký hiệu | `**1383/TTKSBT**` |
| Tên đơn vị gửi/soạn thảo | `**Sở Y tế**` |
| Số VB cũ khi cảnh báo trùng | `**#2403**` |

Các script này nằm ở `~/./scripts/congchuc/` (hermes-owned) — cron jobs dùng relative path `congchuc/congchuc_scrape.py` resolve đến đó. Muốn chỉnh format output thì sửa trực tiếp ở đây.

### Quan trọng
- Các script ở `/opt/data/scripts/congchuc/` thuộc quyền root (không sửa được từ user hermes). Cron jobs dùng relative path → resolve đến `~/./scripts/congchuc/` (hermes-owned, có thể ghi).
- **Workflow maintain script:** Copy từ `/opt/data/scripts/congchuc/` sang `~/./scripts/congchuc/`, patch bản copy, cron tự động pick up (không cần update cron job nếu relative path đã đúng).
- Chạy lệnh mất 10-15s vì phải mở trình duyệt, login, tìm văn bản rồi thao tác
- Socket timeout có thể xảy ra nếu network chậm — retry lần 2 nếu fail