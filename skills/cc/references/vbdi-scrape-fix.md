# Văn bản đi Scraper — Fix Telerik Date Input Hidden

## Vấn đề

Script `congchuc_vbdi_scrape.py` (cron "Quet cong van di", job `d7f9e2c1a4b6`) 
dùng `page.fill()` để nhập ngày tìm kiếm vào Telerik RadDatePicker. 
Input thật (`<input id="..._dateInput">`) bị CSS hidden → Playwright `.fill()` 
timeout với lỗi "element is not visible".

## Triệu chứng

- Cron job báo `last_status: error` dù script chạy không exception
- Không có output VB đi mới dù có VB trong khoảng ngày
- Chạy thủ công thấy log: `[INFO] No documents found for date range ...`

## Root cause

Exception bị silent catch trong `pw_get_documents()`:
```python
except Exception as e:
    last_error = str(e)
    continue  # chạy vòng lặp retry
```
Sau 2 retry đều fail vì cùng lý do → `return []`.

## Fix

Thay `page.fill()` bằng `page.evaluate()` để set value + trigger change event:

```python
page.evaluate(f"""
    (function() {{
        var dtFrom = document.getElementById('dnn_ctr4744_VBDi_TimKiem_dtpNgayPhatHanhTu_dateInput');
        if (dtFrom) {{
            dtFrom.value = '{two_days_ago}';
            var evt = document.createEvent('HTMLEvents');
            evt.initEvent('change', true, true);
            dtFrom.dispatchEvent(evt);
        }}
        var dtTo = document.getElementById('dnn_ctr4744_VBDi_TimKiem_dtpNgayPhatHanhDen_dateInput');
        if (dtTo) {{
            dtTo.value = '{today_str}';
            var evt = document.createEvent('HTMLEvents');
            evt.initEvent('change', true, true);
            dtTo.dispatchEvent(evt);
        }}
        var btn = document.getElementById('dnn_ctr4744_VBDi_TimKiem_btnSearch');
        if (btn) btn.click();
    }})();
""")
```

## Deploy

Script fix đặt tại: `~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py`

Cron job đã cập nhật trỏ tới script này.

## Chromium args cho Docker

Thêm 3 arg bắt buộc khi launch:
```python
browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
```

## Verify

```bash
uv run python ~/./scripts/congchuc/congchuc_vbdi_scrape_fixed.py
```
Nếu có VB đi mới → stdout có danh sách. Nếu không → silent (exit 0).
