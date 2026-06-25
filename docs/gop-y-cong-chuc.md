Để đọc file còn lại trước:Đã đọc toàn bộ 3 file. Đây là review chi tiết:

---

## Tổng quan

Code chất lượng tốt cho scraping ASP.NET/Telerik — xử lý đúng SSO flow, fallback logic hợp lý, attachment download qua ZIP rất thực tế. Có vài vấn đề cần fix.

---

## 🔴 Bug nghiêm trọng

**1. `congchuc_scrape.py` — `seen_ids` bị overwrite thay vì merge (dòng 686)**

```python
# Hiện tại — SAI: chỉ lưu IDs của lần chạy hiện tại
state['seen_ids'] = current_ids

# Đúng: phải union với seen trước đó
state['seen_ids'] = list(set(state.get('seen_ids', [])) | set(current_ids))
```

Hệ quả: nếu một VB biến mất khỏi page 1 rồi quay lại (server sort thay đổi), nó sẽ bị thông báo lại như VB mới.

**2. `congchuc_scrape.py` — Login inject credential trực tiếp vào `page.evaluate()` (dòng 548-552)**

```python
# Hiện tại — XSS injection risk nếu PASSWORD có ký tự đặc biệt
page.evaluate(f"""
    document.getElementById('IDToken1').value = '{USERNAME}';
    document.getElementById('IDToken2').value = '{PASSWORD}';
""")

# Đúng: dùng fill() hoặc truyền qua JS argument
page.fill("#IDToken1", USERNAME)
page.fill("#IDToken2", PASSWORD)
page.click("#btnLogin")
```

Nếu `PASSWORD` chứa `'` hoặc `\` thì JS syntax error, login fail silently.

**3. `congchuc_scrape.py` — `extract_documents()` bị code duplicate hoàn toàn (dòng 379–476)**

`rgRow` và `rgAltRow` parse bằng 2 block code y hệt nhau (~90 dòng). Nên gộp:

```python
trs = re.findall(
    r'<tr[^>]*class="\s*rg(?:Alt)?Row\s*"[^>]*>(.*?)</tr>',
    html, re.DOTALL
)
# parse 1 lần duy nhất
```

---

## 🟡 Vấn đề cần chú ý

**4. `congchuc_scrape.py` — `html_unescape()` có entries trùng lặp (dòng 82–98)**

`&#224;` (à) và `&#225;` (á) bị replace 3 lần. Dòng 98 đã có generic handler `re.sub(r'&#(\d+);', ...)` — các dòng hardcode phía trên là thừa hoàn toàn. Nên xóa hết, chỉ giữ:

```python
def html_unescape(s):
    s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    s = s.replace('&quot;', '"').replace('&apos;', "'")
    s = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), s)
    s = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), s)
    return s
```

**5. `congchuc_scrape.py` — `download_attachments_for_docs()` login lại từ đầu (dòng 795)**

Playwright đã login trong `pw_get_documents()`, nhưng `download_attachments_for_docs()` lại login lần nữa — 2 Playwright session riêng biệt, tốn thêm ~10–15 giây và 1 session OpenAM. Nên truyền cookies hoặc reuse context:

```python
# Option A: truyền storage_state từ pw_get_documents()
storage = context.storage_state()  # sau khi login xong
# Truyền vào download function
browser.new_context(storage_state=storage)

# Option B: gộp cả 2 flow vào 1 Playwright session duy nhất
```

**6. `congchuc_vbdi_scrape.py` — Date filter inject qua `page.evaluate()` không safe (dòng 119–124)**

Tương tự bug #2 — nếu format ngày thay đổi hoặc có ký tự lạ thì JS break. Dùng `page.fill()` thay thế.

**7. `congchuc_vbdi_scrape.py` — `extract_documents()` không dedup trước khi return (dòng 58–76)**

Rows từ `rgRow` và `rgAltRow` có thể bị đếm 2 lần nếu regex overlap. File `congchuc_scrape.py` có hàm `dedup_documents()` riêng — nên gọi nó trong `congchuc_vbdi_scrape.py` luôn.

**8. `congvan_status.py` — `list` hiện không sort theo `status_updated_at`**

Hiện sort theo `so_den` descending — hợp lý cho VB đến. Nhưng khi filter `list --status wip`, người dùng thường muốn xem VB nào được update gần nhất lên đầu:

```python
key=lambda d: d.get("status_updated_at") or "0000"
```

---

## 🟢 Góp ý nhỏ

**9. `congchuc_scrape.py` — Magic number `[:10]` trong attachment loop (dòng 829)**

```python
for idx, doc in enumerate(new_docs[:10]):
```

Nên đưa ra config:
```python
MAX_ATTACHMENT_DOCS = int(os.environ.get("CONGVAN_MAX_ATTACHMENT_DOCS", "10"))
```

**10. `congvan_status.py` — `migrate_state()` chạy mỗi lần gọi, không có guard**

Không có vấn đề về correctness nhưng nên thêm guard để tránh chạy thừa:

```python
if "documents" in state:
    return state  # đã migrate rồi
```

---

## Tóm tắt ưu tiên fix

| # | File | Mức | Vấn đề |
|---|---|---|---|
| 1 | `scrape.py` | 🔴 | `seen_ids` overwrite thay vì merge |
| 2 | `scrape.py` | 🔴 | Credential trong `page.evaluate()` — dùng `fill()` |
| 3 | `scrape.py` | 🟡 | Code duplicate `rgRow`/`rgAltRow` |
| 4 | `scrape.py` | 🟡 | `html_unescape()` entries thừa |
| 5 | `scrape.py` | 🟡 | Double login trong attachment flow |
| 6 | `vbdi_scrape.py` | 🔴 | Date inject không safe |
| 7 | `vbdi_scrape.py` | 🟡 | Thiếu dedup |
| 8 | `status.py` | 🟢 | Sort trong `list --status` |