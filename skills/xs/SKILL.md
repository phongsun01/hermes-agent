---
name: xs
description: "Xem và thống kê kết quả xổ số miền Bắc (XSMB) hàng ngày và phân tích lô tô lịch sử"
version: "2.0.0"
---

# Hướng dẫn Kỹ năng Xổ số Miền Bắc (XSMB)

Kỹ năng này giúp xem kết quả xổ số miền Bắc và thực hiện thống kê tần suất lô tô.

## Các lệnh hỗ trợ
1. `/xs homnay` hoặc `/xs` — Xem KQXSMB mới nhất
2. `/xs <date>` — Xem kết quả ngày cụ thể
3. `/xs lo <số ngày>` — Thống kê tần suất lô tô trong N ngày gần nhất
4. `/xs soilo <số ngày>` — Soi cầu Pascal + Monte Carlo (mặc định 30 ngày)

## 🔧 Tool có sẵn (ưu tiên dùng tool thay browser)

Hệ thống có **2 tool Hermes** đã được đăng ký và sẵn sàng sử dụng:

### `get_xsmb` — Lấy kết quả XSMB
- Tham số `date` (string, tùy chọn): ngày cần xem, định dạng `dd-mm-yyyy`. Để trống = lấy hôm nay.
- Tham số `limit_days` (integer, tùy chọn): lấy N ngày gần nhất từ database.

**Ví dụ gọi:**
- Xem hôm nay: `get_xsmb({})` hoặc `get_xsmb({"date": "01-07-2026"})`
- Xem ngày cụ thể: `get_xsmb({"date": "30-06-2026"})`
- Lấy 30 ngày gần nhất: `get_xsmb({"limit_days": 30})`

### `predict_xsmb` — Soi cầu Pascal + Monte Carlo
- Tham số `last_days` (integer, tùy chọn): số ngày lịch sử để phân tích. Mặc định 30.

**Ví dụ gọi:**
- Soi cầu 30 ngày: `predict_xsmb({})` hoặc `predict_xsmb({"last_days": 30})`
- Soi cầu 60 ngày: `predict_xsmb({"last_days": 60})`

## Luồng xử lý từng lệnh

### `/xs` hoặc `/xs homnay`
1. Gọi `get_xsmb({})` → nhận về JSON kết quả
2. Trình bày đầy đủ các giải từ GĐB đến G7 theo dạng text dễ đọc

### `/xs <date>`
1. Chuyển đổi date sang định dạng `dd-mm-yyyy` (xem bảng bên dưới)
2. Gọi `get_xsmb({"date": "<dd-mm-yyyy>"})` → nhận về kết quả ngày đó
3. Nếu không có trong database, tool sẽ tự động tải từ web

### `/xs lo <số ngày>`
1. Gọi `get_xsmb({"limit_days": <số ngày>})` → nhận về danh sách kết quả
2. Từ JSON trả về, lấy **2 số cuối** của tất cả 27 dãy số mỗi ngày
3. Đếm tần suất các cặp 00→99
4. Tổng hợp: Top 5 cặp nhiều nhất / ít nhất, đầu số mạnh/yếu

### `/xs soilo <số ngày>`
1. Gọi `predict_xsmb({"last_days": <số ngày>})` → nhận về JSON với:
   - `pascal_prediction`: cặp Pascal tính từ kỳ gần nhất
   - `top_monte_carlo`: Top 10 cặp số + xác suất %
2. Trình bày kết quả rõ ràng

## Chuyển đổi ngày
- **Hôm nay / homnay** → Ngày hiện tại giờ VN (UTC+7)
- **Hôm qua / homqua** → Ngày hôm qua
- **15-06-2026 / 15/06/2026 / 15062026** → `15-06-2026`
- **15/6** (khuyết năm) → `15-06-{năm hiện tại}`

## Dự phòng bằng Browser (khi tool gặp lỗi)

Nếu tool báo lỗi, dùng browser vào: **https://xsmb.vn/xsmb.html**

1. `browser_navigate(url="https://xsmb.vn/xsmb.html")`
2. Đọc kết quả từ snapshot — trang hiển thị bảng đầy đủ 27 dãy

## Lưu ý trình bày
- XSMB quay lúc **18h10-18h30** hàng ngày. Trước giờ đó kết quả hôm nay chưa có.
- Trình bày kết quả qua Zalo: **không dùng markdown**, xuống dòng bằng \n, dùng emoji cho trực quan.
- Luôn ghi rõ ngày kết quả để tránh nhầm lẫn.

## Tham khảo
- `references/data-sources.md` — danh sách nguồn dữ liệu XSMB đã kiểm tra
