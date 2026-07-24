# Troubleshooting — CC Skill

Tài liệu này chứa nguyên nhân gốc và cách fix cho các lỗi thường gặp khi vận hành skill `/cc`. Đọc mục tương ứng khi gặp lỗi — không cần đọc toàn bộ file cho mỗi lần chạy.

## 1. State file split — script báo ✅ nhưng `/cc list` vẫn hiện `[new]`

Có HAI state file `vbden_state.json` dùng song song:
- **State chính** (đọc bởi `congvan_status.py` để trả lời `/cc list`): `/opt/data/cron/cong-van-den/vbden_state.json` — cập nhật bởi cron job và lệnh `congvan_status.py done/read/wip`.
- **State /tmp** (ghi bởi `congchuc_action.py` khi chạy với `HERMES_HOME=/tmp`): `/tmp/cong-van-den/cron/cong-van-den/vbden_state.json` — chỉ chứa log của action script.

**Hệ quả:** sau `/cc end`, state chính KHÔNG tự động đồng bộ. Bắt buộc chạy thêm `congvan_status.py done <số_vb>` sau khi action thành công — bỏ qua bước này thì VB vẫn hiện `[new]` dù đã kết thúc trên cổng thật.

**"Không tìm thấy trên grid" khi retry `/cc end`**: đây là tín hiệu THÀNH CÔNG, không phải lỗi — VB đã được xử lý và không còn trên tab Chưa xử lý. Chỉ cần sync state là xong. Ngoại lệ: nếu điều này xảy ra ở **lần chạy đầu tiên** (chưa từng end trước đó) thì là lỗi thật — cần kiểm tra grid filter hoặc phân trang (script chỉ duyệt 15 trang đầu).

## 2. Quyền ghi & 9p mount (`Permission denied`)

`/opt/data/` là 9p mount từ Windows (Docker Desktop + WSL), chủ sở hữu là `root`. User `hermes` không thể tạo thư mục con hoặc ghi file vào thư mục chưa tồn tại trong `/opt/data/`.

| Đường dẫn | Quyền |
|---|---|
| `/opt/data/cron/cong-van-den/attachments/` | 777 ✅ ghi được trực tiếp |
| `/opt/data/cron/cong-van-den/action_logs/last_result.txt` | thuộc root ❌ không ghi được |

**`congchuc_scrape.py` (`/cc tai`)**: thư mục attachments đã 777 → **không cần** set `HERMES_HOME`:
```bash
uv run python /opt/data/scripts/congchuc/congchuc_scrape.py --download-only <số_vb>
```
File lưu tại `/opt/data/cron/cong-van-den/attachments/<số_vb>/`.

**`congchuc_action.py` (`/cc end`)**: vẫn **cần** `HERMES_HOME=/tmp` vì script ghi vào `action_logs/last_result.txt` (thuộc root):
```bash
HERMES_HOME=/tmp uv run python /opt/data/scripts/congchuc/congchuc_action.py kethuc <số_vb> [lý do]
```
Screenshot và log khi đó lưu tại `/tmp/cron/cong-van-den/attachments/<số_vb>/` và `/tmp/cron/cong-van-den/action_logs/`.

## 3. Telerik RadDatePicker — `page.fill()` timeout

Một số trang trên congchuc.quangninh.gov.vn (ví dụ tabid=1121 Văn bản đi) dùng Telerik RadControls. Input ngày (`<input id="..._dateInput">`) bị **hidden** (`display:none`/`visibility:hidden`) — `page.fill()`, `page.locator().fill()`, hay `page.type()` sẽ timeout vì element không visible.

**Cách fix**: dùng `page.evaluate()` set value bằng JavaScript rồi tự trigger `change` event:
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

**Bài học rộng hơn**: bất kỳ input nào trong Telerik RadGrid/RadDatePicker bị hidden → luôn dùng JS evaluate thay vì Playwright fill.

Script gốc `congchuc_vbdi_scrape.py` từng mắc lỗi này. Bản fix đã deploy ở `~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py`, và cron job đã trỏ sang script fix này.

## 4. Cron "Quet cong van di" báo lỗi

Cron `d7f9e2c1a4b6` chạy `congchuc/congchuc_vbdi_scrape.py` (`no_agent=true`), quét tabid=1121 (Văn bản đi), lọc theo ngày phát hành 2 ngày gần nhất.

**Lỗi phổ biến**: `page.fill()` timeout do input ngày bị hidden (xem mục 3). Script gốc silent-catch exception → retry hết lượt → trả về rỗng → cron báo `error` dù stdout không có lỗi rõ ràng.

**Script fix đã deploy** tại `~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py` — chứa đầy đủ logic gốc + JS evaluate cho date input + thêm Chromium args ổn định (xem mục 5).

**Cập nhật cron khi deploy bản fix**:
```bash
cp <path_to_fixed> ~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py
cronjob action=update job_id=d7f9e2c1a4b6 script=congchuc/congchuc_vbdi_scrape_fixed.py
```

## 5. Chromium crash / `write EPIPE` trong Docker

Nguyên nhân thường gặp:
1. Shared memory `/dev/shm` nhỏ.
2. GPU không khả dụng trong container.
3. Zombie Chromium process còn sót từ lần chạy trước.

**Fix**: luôn thêm các arg này khi launch Chromium:
```python
browser = p.chromium.launch(
    headless=True,
    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
)
```
Nếu vẫn EPIPE sau khi thêm args: `rm -f .playwright_storage.json` để force fresh login (storage state cũ có thể bị corrupt).

## 6. Sửa script trong `/opt/data/scripts/congchuc/`

Thư mục này thuộc quyền `root` — user `hermes` không sửa trực tiếp được. Cron jobs dùng **relative path** nên resolve đến `~/./scripts/congchuc/` (thuộc quyền `hermes`, ghi được).

**Workflow maintain script**:
1. Copy từ `/opt/data/scripts/congchuc/<script>.py` sang `~/./scripts/congchuc/<script>.py`.
2. Patch bản copy.
3. Cron tự động pick up bản patch — không cần update cron job nếu relative path đã đúng sẵn.

## 7. LLM không phản hồi khi chạy `/cc tomtat`

Nếu script báo "⚠️ LLM không phản hồi", tự đọc file thủ công rồi tóm tắt bằng khả năng của Hermes:

```bash
# Đọc DOCX
uv run python -c "from docx import Document; d=Document('/opt/data/cron/cong-van-den/attachments/<số_vb>/*.docx'); print('\n'.join(p.text for p in d.paragraphs if p.text.strip()))"

# Đọc PDF
uv run python -c "import fitz; doc=fitz.open('/opt/data/cron/cong-van-den/attachments/<số_vb>/*.pdf'); [print(doc[i].get_text()) for i in range(doc.page_count)]; doc.close()"
```

## 8. Định dạng output cron notification (bôi đậm)

Cron jobs `no_agent` (`congchuc_scrape.py` cho VB đến, `congchuc_vbdi_scrape.py` cho VB đi) output trực tiếp stdout → Zalo. Dùng `**bold**` markdown cho các trường quan trọng:

| Trường | Ví dụ |
|---|---|
| Số đến | `**#2534**` |
| Số ký hiệu | `**1383/TTKSBT**` |
| Tên đơn vị gửi/soạn thảo | `**Sở Y tế**` |
| Số VB cũ khi cảnh báo trùng | `**#2403**` |

Các script này nằm ở `~/./scripts/congchuc/` (hermes-owned) — cron jobs dùng relative path `congchuc/congchuc_scrape.py` resolve đến đó. Muốn chỉnh format output thì sửa trực tiếp ở đây.

## Ghi chú chung

- Chạy lệnh mất 10-15s là bình thường vì phải mở trình duyệt, login, tìm văn bản rồi thao tác.
- Socket timeout có thể xảy ra nếu network chậm — retry lần 2 nếu fail.
