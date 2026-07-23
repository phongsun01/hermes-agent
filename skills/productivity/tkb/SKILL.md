---
name: tkb
description: "Quản lý Thời khóa biểu (TKB) gia đình — Google Sheet + local overlay."
version: 1.2.0
author: Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Timetable, Schedule, TKB, Productivity, Family]
---

# Thời khóa biểu (TKB) Gia đình

Truy vấn và quản lý thời khóa biểu các thành viên trong gia đình. Dữ liệu được hợp nhất từ hai nguồn:
1. **Google Sheet** (CSV export, read-only) — lịch gốc
2. **Local overlay** (`tkb_local.json`) — các mục bổ sung không nằm trong sheet

## Scripts & Files

| File | Vai trò |
|------|---------|
| `/opt/data/scripts/tkb/tkb_query.py` | Script chính: đọc sheet + merge local, trả JSON |
| `/opt/data/scripts/tkb/tkb_deliver.py` | Script delivery cho Zalo (no_agent=true): output plain text, format thân thiện, luôn có output dù count=0 |
| `/opt/data/scripts/tkb/tkb_local.json` | Local overlay entries (thêm/sửa thủ công hoặc qua agent) |
| `/opt/data/scripts/tkb/tkb_deliver_tomorrow.sh` | Wrapper `.sh` cho cron tối — gọi `tkb_deliver.py tomorrow` |
| `/opt/data/scripts/tkb/tkb_deliver_week.sh` | Wrapper `.sh` cho cron tuần — gọi `tkb_deliver.py week` |

Google Sheet URL được hardcode trong `tkb_query.py` — đổi tại biến `SHEET_URL`.

## Các lệnh

Khi người dùng gõ `/tkb`, chạy script tương ứng:

```bash
uv run python /opt/data/scripts/tkb/tkb_query.py today
uv run python /opt/data/scripts/tkb/tkb_query.py tomorrow
uv run python /opt/data/scripts/tkb/tkb_query.py week
uv run python /opt/data/scripts/tkb/tkb_query.py month
```

Script trả về JSON với `day`, `count`, `schedule` (mảng string). Agent parse JSON và trình bày đẹp.

## Local Overlay (`tkb_local.json`)

Khi chưa có Google OAuth để ghi trực tiếp vào sheet, dùng file local overlay. Cấu trúc:

```json
{
  "local_entries": [
    {
      "thu": "Thứ 4",
      "thu_index": 2,
      "thoi_gian": "17:30 - 18:30",
      "thanh_vien": "Bi",
      "hoat_dong": "Học tiếng Anh",
      "dia_diem": "Scots",
      "lap_lai": "Hàng tuần",
      "ghi_chu": "Mang cặp"
    }
  ]
}
```

`thu_index` = 0 (Thứ 2) → 6 (Chủ nhật). Các entries được thêm vào cuối mảng sheet rows.

### Thêm mục mới qua agent

Khi user yêu cầu thêm lịch:
1. Xác định `thu`, `thoi_gian`, `thanh_vien`, `hoat_dong`, `dia_diem`, `lap_lai`, `ghi_chu`
2. Map `thu` → `thu_index` (Thứ 2=0, Thứ 3=1, ..., Chủ nhật=6)
3. Đọc file `/opt/data/scripts/tkb/tkb_local.json` hiện tại
4. Append entries mới vào mảng `local_entries`
5. Ghi file
6. Chạy `uv run python /opt/data/scripts/tkb/tkb_query.py week` để verify

### Xoá mục

Đọc `tkb_local.json`, tìm entry cần xoá theo `thu` + `thoi_gian` + `thanh_vien`, xoá khỏi mảng, ghi lại.

## Cron Delivery (no_agent = true)

Các cron TKB gửi vào Zalo nhóm "Bi bống house" dùng **no_agent=true + script** để đảm bảo delivery 100% (không phụ thuộc agent quyết định có gửi hay không). Script output được deliver thẳng qua Zalo adapter.

| Cron | Giờ VN | Script arg | Ví dụ output |
|------|:------:|------------|-------------|
| 🌅 Sáng (hôm nay) | **06:00 hằng ngày** | `today` | `[TKB] Lich hom nay - Thứ 3 ... Hom nay khong co lich.` |
| 🌙 Tối (ngày mai) | **21:00 hằng ngày** | `tomorrow` | `[TKB] Lich ngay mai - Thứ 4 ...` |
| 📅 Tuần | **07:00 Thứ 2** | `week` | `[TKB] Lich ca tuan ...` |

### Cách dùng

```bash
# Chạy thử delivery:
uv run python /opt/data/scripts/tkb/tkb_deliver.py today
uv run python /opt/data/scripts/tkb/tkb_deliver.py tomorrow
uv run python /opt/data/scripts/tkb/tkb_deliver.py week
```

### ⚠️ Pitfall: agent-driven cron không deliver khi count=0

Trước đây cron TKB dùng agent-driven (mặc định) với skills=["tkb"] + prompt="/tkb today". Khi count=0, agent có thể không gửi tin nhắn → nhóm không thấy gì. **Các cron script-based khác (tập thể dục, thời tiết, giá xăng) đều dùng no_agent=true và hoạt động ổn định.**

### ⚠️ Pitfall QUAN TRỌNG: script field không support arguments

Hermes cron scheduler xử lý `script` field như một **đường dẫn file thuần túy**, KHÔNG tách tham số dòng lệnh. Nếu viết:

```json
"script": "tkb/tkb_deliver.py tomorrow"
```

→ scheduler coi cả cụm là tên file (có dấu cách), `_run_job_script()` trả `(False, "Script not found")` → **last_status = "error"** dù fallback vẫn gửi được message (non-empty stdout).

**Cách fix đúng:** Tạo wrapper `.sh` script riêng cho mỗi chế độ, set `script` trỏ tới file `.sh` (không kèm arguments):

```bash
#!/bin/bash
# tkb_deliver_tomorrow.sh
cd "$(dirname "$0")"
uv run python tkb_deliver.py tomorrow
```

```bash
#!/bin/bash
# tkb_deliver_week.sh
cd "$(dirname "$0")"
uv run python tkb_deliver.py week
```

**Kiểm tra:** `_run_job_script` capture cả stdout + stderr, trả `(False, ...)` nếu `returncode != 0` hoặc timeout. Với `.sh`, scheduler dùng `/bin/bash`; với `.py` dùng `sys.executable`. Luôn chạy thử wrapper trước khi gán vào cron: `bash path/to/wrapper.sh && echo OK`. 

## Hướng dẫn cho Agent

1. Khi user gõ `/tkb`, `tkb today`, `tkb tomorrow`, `tkb week`, `tkb month` → chạy script tương ứng qua `terminal()`, parse JSON output
2. Trình bày bằng tiếng Việt, giọng ấm áp kiểu gia đình. Dùng emoji phù hợp (👦👧⏰📅)
3. **Khi trả lời trên Zalo: dùng plain text, KHÔNG dùng markdown (Zalo không render markdown).** Bỏ ** ** và _ _ nếu có.
4. Nhấn mạnh giờ, địa điểm, ghi chú quan trọng (mang giày, laptop, cặp...)
5. Nếu `count=0`: thông báo hôm nay không có lịch
6. Khi user yêu cầu **thêm lịch mới** → không thể ghi vào Google Sheet (chưa có OAuth) → dùng local overlay pattern như trên
7. Sau khi thêm/xoá: luôn chạy `tkb_query.py week` để verify dữ liệu đúng
8. Khi cần tạo/cập nhật cron TKB delivery → dùng `tkb_deliver.py` với no_agent=true, không dùng agent-driven pattern (dễ fail delivery)
