---
name: kisordoc
description: "Sinh văn bản Word hồ sơ mua sắm/đấu thầu qua KisorDoc. Hỗ trợ: /kisordoc gen <option> <gói thầu> <template...>, /kisordoc list, /kisordoc templates, /kisordoc jobs, /kisordoc help. Trigger tự nhiên: sinh văn bản, tạo hồ sơ thầu, tạo tài liệu gói thầu, chạy kisordoc, xuất word hồ sơ."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [kisordoc, word, mailmerge, goithau, vanban, procurement, muasam, hosonam]
    category: productivity
---

# Kỹ năng KisorDoc — Sinh văn bản hồ sơ đấu thầu (/kisordoc)

Khi người dùng yêu cầu sinh văn bản, tạo hồ sơ thầu, xuất Word cho gói mua sắm, hoặc gọi `/kisordoc`, hãy thực hiện đúng các hướng dẫn dưới đây.

**LƯU Ý BẮT BUỘC**: Chỉ được chạy lệnh qua tool thực thi shell (`terminal`). Tuyệt đối không tự bịa kết quả. Script nằm tại `/opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py`.

---

## Môi trường & URL

Script gọi KisorDoc FastAPI đang chạy trên **Windows host**:

- **Mặc định (Hermes trong Docker):** `KISORDOC_API_URL=http://host.docker.internal:8000`
- **Nếu chạy CLI Windows native:** `KISORDOC_API_URL=http://localhost:8000`
- **Kiểm tra API còn sống:** `curl -s http://host.docker.internal:8000/` → trả `{"status":"ok",...}`

Nếu gặp lỗi kết nối: báo user "KisorDoc chưa chạy — hãy mở runner.py trên Windows trước."

---

## Các lệnh

### 1. `/kisordoc list` — Xem quy trình & gói thầu

**Bước 1** — Lấy danh sách quy trình:
```bash
uv run python /opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py list-options
```

**Bước 2** — Nếu user muốn xem gói thầu của một quy trình (ví dụ Opt1):
```bash
uv run python /opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py list-packages --option Opt1
```

> ⚠️ **Lưu ý data shape:** `list-packages` trả về `id` = ID thuần (ví dụ `MS26-01`), không phải label đầy đủ. Label đầy đủ (`01. MS26-01 - Tên gói thầu`) chỉ hiển thị trên Gradio UI. Khi generate, dùng `id` này.

**Trả lời:** Format gọn, đánh số thứ tự, in đậm tên quy trình/gói thầu bằng `**`.

---

### 2. `/kisordoc templates <option>` — Xem template của quy trình

```bash
uv run python /opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py list-templates --option <option>
```

Ví dụ: `list-templates --option Opt1`

**Trả lời:** Liệt kê danh sách tên template (không extension). Đây chính là giá trị truyền vào `--templates` khi generate.

---

### 3. `/kisordoc gen <option> <gói_thầu> <template...>` — Sinh văn bản

Đây là lệnh chính. Chạy và **tự poll** đến khi xong (không cần user chờ thủ công).

```bash
uv run python /opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py generate \
    --option <option> \
    --package "<package_id_hoặc_label>" \
    --templates <tên_template_1> <tên_template_2> ...
    [--dry-run]
    [--config-row-range "<dải>"]
```

**Ví dụ thực tế:**
```bash
uv run python /opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py generate \
    --option Opt1 \
    --package "MS26-01" \
    --templates "Bao gia" "BB HDMS" "QD phe duyet KH mua sam"
```

**Luồng thực hiện bắt buộc:**

1. **Thông báo trước** cho user: *"Đang sinh văn bản — option=Opt1, gói=MS26-01, templates=[...]. Quá trình có thể mất 30–120s..."*
2. **Chạy lệnh** — script tự poll, in log tiến độ ra stderr theo thời gian thực
3. **Đọc JSON stdout** — trường `succeeded`, `failed`, `files[]`, `download_url`
4. **Trả lời** theo format dưới đây

**Format trả lời khi thành công:**
```
✅ Hoàn thành sinh văn bản!
- **Gói thầu:** MS26-01
- **Quy trình:** Opt1
- **Thành công:** X/Y file
- **Thời gian:** Zs

📄 Các file đã tạo:
1. **BaoCao.docx** — ✅ OK
2. **TuTrinh.docx** — ✅ OK

📂 File lưu tại: {ProjectPath}/3. Files/{option}/{package}/
```

**Format trả lời khi có file lỗi:**
```
⚠️ Hoàn thành nhưng có lỗi:
- Thành công: X/Y
- Lỗi: Z file — <tên file>: <error message từ result.files[].error>
```

**Tham số `--config-row-range`:** Dùng khi gói thầu có nhiều nhà thầu (nhiều dòng config). Ví dụ `"2-5"` chỉ sinh cho dòng 2 đến 5. Nếu user không đề cập → bỏ qua tham số này.

**Tham số `--dry-run`:** Kiểm tra template/data mà không tạo file thật. Dùng khi user muốn xác nhận trước khi chạy thật.

---

### 4. `/kisordoc jobs` — Xem lịch sử job gần đây

```bash
uv run python /opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py list-jobs --limit 10
```

**Trả lời:** Liệt kê job theo thứ tự mới nhất, hiển thị: job_id (8 ký tự đầu), option, package, status (done/failed/running), thời gian tạo.

---

### 5. `/kisordoc help` — Hướng dẫn

Không cần chạy script. Trả lời tóm tắt các lệnh:
- `/kisordoc list` — xem quy trình & gói thầu
- `/kisordoc templates <option>` — xem template của quy trình
- `/kisordoc gen <option> <gói> <template...>` — sinh văn bản Word
- `/kisordoc jobs` — lịch sử job gần đây
- `/kisordoc help` — hướng dẫn này

---

## Xử lý lỗi thường gặp

### Lỗi kết nối API
```
Không kết nối được KisorDoc API tại http://host.docker.internal:8000
```
→ Báo user: "KisorDoc (runner.py) chưa chạy trên Windows. Hãy mở terminal Windows và chạy `python runner.py` trong thư mục KisorDoc."

### Package không tìm thấy (HTTP 400)
```
HTTP 400 POST /generate: Không resolve được package: ...
```
→ ID gói thầu sai. Chạy `list-packages --option <option>` để xem danh sách ID đúng, rồi thử lại.

### Template không tồn tại
Kết quả trả `failed: N` với `error: "Template ... không tồn tại"`.
→ Chạy `list-templates --option <option>` để xem tên template chính xác. Tên template **phân biệt hoa/thường và dấu cách**.

### Job timeout (>300s)
```
Timeout sau 300s — job <id> vẫn chưa hoàn thành
```
→ Có thể KisorDoc đang bị treo hoặc gói thầu có quá nhiều template. Báo user kiểm tra cửa sổ KisorDoc trên Windows.

### `uv run` không tìm thấy module
→ Đảm bảo `kisordoc_client.py` chỉ dùng stdlib (không import ngoài). File hiện tại đã dùng thuần `urllib`, `json`, `argparse` — không cần cài thêm package.

---

## Quy tắc bắt buộc

- **`uv run python`** — không dùng `python` trần vì môi trường Hermes dùng uv venv
- **Đường dẫn tuyệt đối** — luôn dùng `/opt/data/skills/productivity/kisordoc/scripts/kisordoc_client.py`
- **Không tự bịa kết quả** — nếu script lỗi hoặc KisorDoc không chạy, báo rõ lỗi từ stderr/stdout
- **Thông báo trước khi chạy** `generate` — lệnh có thể mất 30–120s
- **Đọc `files[]` trong kết quả** — không chỉ đọc `succeeded/failed` count, phải liệt kê từng file cho user biết file nào OK, file nào lỗi
