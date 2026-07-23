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

## ⚙️ Plugin cung cấp tool

2 tool Hermes (`get_xsmb`, `predict_xsmb`) được cung cấp bởi **plugin xsmb** tại `/opt/data/plugins/xsmb/`. Plugin cần được load khi Hermes gateway khởi động — nếu tools không xuất hiện, gateway cần được restart.

**Dependencies:** pandas, numpy — đã cài trong venv Hermes (`/opt/hermes/.venv/`). Nếu thiếu, chạy: `uv pip install pandas`.

## 🔧 Tool có sẵn (ưu tiên dùng tool thay browser)

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
   - `top_cdm`: Top 10 cặp số + Expected count theo mô hình Bayesian CDM (arXiv:2403.12836)
2. Trình bày đầy đủ cả 3 kết quả dự báo (Cầu Pascal, Top 10 Monte Carlo và Top 10 Bayesian CDM) rõ ràng để người dùng đối chiếu.

## Chuyển đổi ngày
- **Hôm nay / homnay** → Ngày hiện tại giờ VN (UTC+7)
- **Hôm qua / homqua** → Ngày hôm qua
- **15-06-2026 / 15/06/2026 / 15062026** → `15-06-2026`
- **15/6** (khuyết năm) → `15-06-{năm hiện tại}`

## Dự phòng (khi tool không available)

### 1. Script xsmb_fetcher.py
Nếu tool chưa được load (gateway chưa restart), dùng script có sẵn:
```bash
# Kết quả mới nhất
python3 /opt/data/skills/xs/scripts/xsmb_fetcher.py

# Ngày cụ thể (ghi chú: chỉ fetch được kết quả mới nhất từ xskt.com.vn)
python3 /opt/data/skills/xs/scripts/xsmb_fetcher.py --date 30-06-2026
```
Script dùng **urllib** + parse HTML từ xskt.com.vn — luôn chạy được, không cần browser.

### 2. Browser (khi cần dữ liệu nhiều ngày)

Nếu tool báo lỗi, dùng browser vào: **https://xsmb.vn/xsmb.html**

1. `browser_navigate(url="https://xsmb.vn/xsmb.html")`
2. Đọc kết quả từ snapshot — trang hiển thị bảng đầy đủ 27 dãy

## Lưu ý trình bày
- XSMB quay lúc **18h10-18h30** hàng ngày. Trước giờ đó kết quả hôm nay chưa có.
- Trình bày kết quả qua Zalo: **không dùng markdown**, xuống dòng bằng \n, dùng emoji cho trực quan.
- Luôn ghi rõ ngày kết quả để tránh nhầm lẫn.

## Cấu trúc Báo cáo Định kỳ (Cron Job 18h35)

Báo cáo gửi tự động qua Zalo lúc 18h35 hàng ngày được định dạng theo cấu trúc cố định sau để đảm bảo tính nhất quán qua các ngày:

```text
========================================
🎰 KQXSMB - {ngày/tháng/năm}
========================================
(1) 📋 KẾT QUẢ XSMB:
  - 👑 Đặc biệt: {gdb}
  - 🥇 Giải Nhất: {g1}
  - 🥈 Giải Nhì:  {g2}
  - 🥉 Giải Ba:   {g3}
  - Giải Tư:   {g4}
  - Giải Năm:  {g5}
  - Giải Sáu:  {g6}
  - Giải Bảy:  {g7}

(2) 🎯 LÔ TÔ ĐÃ VỀ:
  {danh_sách_lô_tô}

(3) 🔮 DỰ ĐOÁN PASCAL (NGÀY MAI):
  Cặp số gợi ý: {cặp_số}

(4) 🎲 DỰ ĐOÁN MONTE CARLO (NGÀY MAI - TOP 5):
  {danh_sách_top_5_lô_tô}

(5) 📊 DỰ ĐOÁN BAYESIAN CDM (NGÀY MAI - TOP 5):
  {danh_sách_top_5_lô_tô}

(6) 📈 ĐÁNH GIÁ ĐỘ CHÍNH XÁC SOI CẦU HÔM NAY:
  - Cầu Pascal hôm qua gợi ý: {TRÚNG 🎉/Trượt ❌} ({số})
  - Top 10 Monte Carlo: Trúng {số}/10 số ({danh_sách_số_trúng})
  - Top 10 Bayesian CDM: Trúng {số}/10 số ({danh_sách_số_trúng})

(7) 💾 TÌNH TRẠNG CẬP NHẬT DATABASE:
  - 🗄️ CSDL: xsmb_results.db
  - 📅 Tổng số ngày dữ liệu: {tổng_số_ngày}
  - ⚡ Trạng thái: Đã cập nhật lúc {giờ_cập_nhật}
========================================
```

## 🚨 Pitfalls & Troubleshooting

### Tool không hoạt động dù plugin đã có
- **Nguyên nhân:** Hermes gateway cần restart để load plugin mới.
- **Fix:** E có thể dùng script `xsmb_fetcher.py` hoặc browser tool để lấy dữ liệu tạm thời.

### get_xsmb báo lỗi "Không tìm thấy kết quả"
- Ngày chưa quay (trước 18h10) hoặc ngày đó XSMB không quay.
- DB chưa có dữ liệu — tool sẽ tự fetch từ xskt.com.vn.

### ⚠️ Trình bày /xs soilo thiếu phần CDM
- JSON từ `predict_xsmb` luôn có **3 key**: `pascal_prediction`, `top_monte_carlo`, `top_cdm`.
- **Bắt buộc** hiển thị đủ cả 3: Cầu Pascal → Monte Carlo → Bayesian CDM.
- Không được chỉ hiển thị Pascal + Monte Carlo rồi bỏ qua CDM — người dùng sẽ yêu cầu đọc lại skill và bổ sung.
- Mẹo: đọc `top_cdm` và `cdm_alpha_0` từ JSON, expected_count càng cao càng đáng chú ý.

### predict_xsmb lỗi pandas
- Plugin dùng pandas. Nếu chưa cài: `uv pip install pandas`
- Phải dùng `/opt/hermes/.venv/bin/python3`, không dùng `python3` (system python không có pandas).

### Cron script path phải relative
- Cron tool yêu cầu script path **relative** đến `~/.hermes/scripts/` (không dùng absolute path).
- Copy script vào thư mục đó trước khi tạo cron.
- Schedule cron 5-field (`35 18 * * *`) được interpret theo **giờ VN (+07)**, không phải UTC.

### Database chưa có dữ liệu
- Plugin fetch tự động khi gọi `get_xsmb` lần đầu.
- Có thể init thủ công: `cd /opt/data/plugins/xsmb && /opt/hermes/.venv/bin/python3 xsmb_init.py`
- DB được đặt tại: `/opt/data/plugins/xsmb/xsmb_results.db`

## Cron / Tự động hóa
Cron job `XSMB hôm nay` (job_id: 8dfb5caeb2f9) chạy **18:35 VN** hàng ngày:
1. Fetch KQXSMB từ xskt.com.vn bằng Plugin `get_xsmb`
2. Lưu vào SQLite database
3. Gửi thông báo kết quả về Zalo

Script cron: `~/.hermes/scripts/xsmb_cron.py` (no_agent mode — stdout gửi thẳng về user)
Xem trạng thái: `cronjob(action='list')`

## Tham khảo
- `references/data-sources.md` — danh sách nguồn dữ liệu XSMB đã kiểm tra
- `references/plugin-architecture.md` — kiến trúc plugin Hermes, cách đăng ký tool, xử lý dependencies
