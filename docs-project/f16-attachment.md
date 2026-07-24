Dựa vào plan hiện tại, F16 đang khá sơ sài — chỉ có 5 bước ở mức high-level. Để tôi phân tích chi tiết những gì cần làm thực tế:

---

## F16 — Attachment Download + Onyx Ingest

### Bước 1 — Lấy link attachment từ trang chi tiết VB

Trang chi tiết VB (URL dạng `...?fileId=xxx&tabid=yyy`) thường có link tải file ở dạng:
```html
<a href="/DesktopModules/.../Download.aspx?fileId=123">TênFile.pdf</a>
```
hoặc POST trigger qua JavaScript. Cần Playwright để:
```python
page.goto(detail_url)
links = page.query_selector_all("a[href*='Download'], a[href*='.pdf'], a[href*='.doc']")
```

Lưu ý: một VB có thể có **nhiều file đính kèm** (VB chính + phụ lục).

---

### Bước 2 — Download file

Có 2 trường hợp:

**Case A — Link GET đơn giản:**
```python
response = session.get(download_url, cookies=playwright_cookies)
with open(filepath, "wb") as f:
    f.write(response.content)
```

**Case B — POST request hoặc redirect qua ASP.NET handler:**
```python
# Playwright handle luôn cho chắc
with page.expect_download() as download_info:
    page.click("a[href*='Download']")
download = download_info.value
download.save_as(filepath)
```

Playwright `expect_download()` là cách an toàn nhất vì không cần biết cơ chế download của server.

---

### Bước 3 — Tổ chức file

```
~/.hermes/cron/cong-van-den/attachments/
├── 2348/
│   ├── 274-KH-UBND_chinh.pdf
│   └── 274-KH-UBND_phu-luc.docx
├── 2340/
│   └── 1292-TTKSBT.pdf
```

State file cần thêm field:
```json
"2348": {
  ...,
  "attachments": [
    {"filename": "274-KH-UBND_chinh.pdf", "path": "attachments/2348/...", "ingested": true},
    {"filename": "274-KH-UBND_phu-luc.docx", "path": "attachments/2348/...", "ingested": false}
  ]
}
```

---

### Bước 4 — Ingest vào Onyx

```python
import requests

def ingest_to_onyx(filepath, metadata):
    with open(filepath, "rb") as f:
        requests.post(
            "http://localhost:8080/api/admin/connector/file/ingest",
            headers={"Authorization": f"Bearer {ONYX_API_KEY}"},
            files={"file": f},
            data={
                "doc_set_name": "cong-van-den",
                "metadata": json.dumps({
                    "so_den": metadata["so_den"],
                    "so_ky_hieu": metadata["so_ky_hieu"],
                    "tac_gia": metadata["tac_gia"],
                    "ngay_den": metadata["ngay_den"],
                })
            }
        )
```

Cần kiểm tra lại Onyx API endpoint thực tế — có thể là `/api/connector/file` tùy version.

---

### Bước 5 — Idempotency / tránh re-download

Dùng field `ingested: true/false` trong state để skip file đã xử lý. Quan trọng vì cron chạy mỗi giờ:

```python
if doc.get("attachments"):
    for att in doc["attachments"]:
        if not att["ingested"]:
            ingest_to_onyx(att["path"], doc)
            att["ingested"] = True
save_state(state)
```

---

### Phần dễ bị bỏ sót

**Error handling cho file bị xóa/hết hạn trên server** — VB cũ có thể link attachment đã bị xóa → cần `try/except` và đánh dấu `"download_failed": true` trong state thay vì crash.

**Giới hạn size** — nên set cap, ví dụ skip file > 50MB:
```python
CONGVAN_MAX_ATTACHMENT_MB=50
```

**File .doc (Word 97-2003)** — Onyx ingest `.docx` tốt nhưng `.doc` cũ có thể cần convert trước bằng `libreoffice --headless --convert-to docx`.

---

### Độ phức tạp thực tế

Cao hơn plan hiện tại đang ghi ("Cao"). Phần khó nhất không phải download mà là **xác định đúng link attachment** vì DotNetNuke (nền tảng của trang) có nhiều cách serve file khác nhau tùy module. Nên dùng Playwright `expect_download()` cho toàn bộ flow thay vì httpx thuần.