# Xử lý lỗi & Lưu ý kỹ thuật (CC Skill)

Đây là tài liệu tham khảo kỹ thuật cho kỹ năng Quản lý Công văn (CC). Khi gặp lỗi trong quá trình thực thi các lệnh `/cc`, hãy tham chiếu tài liệu này.

## 1. Môi trường & Quyền thực thi

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

**Lưu ý chung:**
- Các script ở `/opt/data/scripts/congchuc/` thuộc quyền root (không sửa được từ user hermes). Cron jobs dùng relative path → resolve đến `~/./scripts/congchuc/` (hermes-owned, có thể ghi).
- **Workflow maintain script:** Copy từ `/opt/data/scripts/congchuc/` sang `~/./scripts/congchuc/`, patch bản copy, cron tự động pick up (không cần update cron job nếu relative path đã đúng).

## 2. Vấn đề State file split (Rất quan trọng)
Có HAI state file `vbden_state.json` được dùng song song:
- **State chính** (đọc bởi `congvan_status.py` để trả lời `/cc list`): `/opt/data/cron/cong-van-den/vbden_state.json` — cập nhật bởi cron job và lệnh `congvan_status.py done/read/wip`.
- **State /tmp** (ghi bởi `congchuc_action.py` với `HERMES_HOME=/tmp`): `/tmp/cong-van-den/cron/cong-van-den/vbden_state.json` — chỉ chứa log action script.

**Hệ quả:** Sau `/cc end` state chính KHÔNG tự động sync. Bắt buộc chạy thêm `congvan_status.py done <số_vb>` sau action. Nếu bỏ qua, VB vẫn hiển thị `[new]` dù đã kết thúc trên cổng.

**Giải thích lỗi thường gặp:**
- **Script báo ✅ nhưng status vẫn `[new]`**: Nguyên nhân = state file split. Luôn kiểm tra trên grid portal thay vì chỉ dựa vào state local.
- **"Không tìm thấy trên grid" (khi retry `/cc end`)**: Đây là tín hiệu THÀNH CÔNG — VB đã được xử lý, không còn trên tab Chưa xử lý. Chỉ cần sync state là xong. Nếu xảy ra ở lần chạy ĐẦU → lỗi thật (cần kiểm tra grid filter / phân trang).
- **VB không tìm thấy ngay lần chạy đầu**: Có thể do grid phân trang — script chỉ duyệt 15 trang đầu. Hoặc grid có bộ lọc đang hiển thị tab khác.
- Lệnh chạy mất 10-15s vì phải mở trình duyệt. Socket timeout có thể xảy ra nếu mạng chậm → tự động retry lần 2 nếu fail.

## 3. Telerik RadDatePicker hidden input (page.fill timeout)
Các grid trên congchuc.quangninh.gov.vn (ví dụ: tabid=1121 Văn bản đi) dùng Telerik RadDatePicker. Input date (`<input id="..._dateInput">`) bị **hidden** (display:none / visibility:hidden) — Playwright `page.fill()` hay `page.type()` sẽ timeout vì "element is not visible".

**Cách fix (Dùng JS evaluate):**
Dùng `page.evaluate()` set value bằng JavaScript và trigger change event thay vì Playwright fill:
```python
page.evaluate(f"""
    var el = document.getElementById('..._dateInput');
    if (el) {{
        el.value = '{date_str}';
        var evt = document.createEvent('HTMLEvents');
        evt.initEvent('change', true, true);
        el.dispatchEvent(evt);
    }}
""")
```
*Script gốc `congchuc_vbdi_scrape.py` mắc lỗi này. Bản fix đã deploy ở `~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py` và cron job đã trỏ sang script fix. Bất kỳ input Telerik nào bị hidden đều cần dùng JS evaluate.*

## 4. Lỗi Chromium crash / EPIPE trong Docker
Khi chạy Playwright trong Docker, Chromium có thể crash với lỗi `write EPIPE` (broken pipe). Nguyên nhân thường gặp:
1. Shared memory `/dev/shm` nhỏ — thêm `--disable-dev-shm-usage`
2. GPU không khả dụng — thêm `--disable-gpu`
3. Zombie Chromium process từ lần chạy trước

**Fix:** Luôn thêm các arg này khi launch Chromium:
```python
browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
```
Nếu vẫn EPIPE: `rm -f .playwright_storage.json` để force fresh login (storage state cũ có thể corrupted).

## 5. Cron quét văn bản đi & Định dạng Zalo
Cron "Quet cong van di" chạy `congchuc/congchuc_vbdi_scrape.py` với tham số `no_agent=true`. Script này quét lọc theo ngày phát hành 2 ngày gần nhất.
Cron jobs no_agent output trực tiếp stdout → Zalo. Để tin nhắn dễ đọc, dùng `**bold**` markdown cho các trường quan trọng:

| Trường | Ví dụ |
|---|---|
| Số đến | `**#2534**` |
| Số ký hiệu | `**1383/TTKSBT**` |
| Tên đơn vị gửi/soạn thảo | `**Sở Y tế**` |
| Số VB cũ khi cảnh báo trùng | `**#2403**` |

Cập nhật cron (nếu dùng relative path): `cronjob action=update job_id=d7f9e2c1a4b6 script=congchuc/congchuc_vbdi_scrape_fixed.py`
