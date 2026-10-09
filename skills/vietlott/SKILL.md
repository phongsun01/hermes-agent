---
name: vietlott
description: "Phân tích Vietlott Mega 6/45 — xem kết quả, kiểm định tính ngẫu nhiên, backtest chiến lược 'hot/cold/random', xác suất trúng và sinh bộ số tham khảo. Kích hoạt khi người dùng hỏi về Vietlott 6/45."
version: "1.0.0"
---

# Vietlott Mega 6/45

Skill phân tích Vietlott 6/45 dựa trên dữ liệu lịch sử từ minhngoc.net.vn.

> ⚠️ **Nguyên tắc bắt buộc**: Các kỳ quay độc lập — không có phương pháp dự đoán đã được chứng minh. Jackpot: 1/8.145.060. Kỳ vọng mỗi vé luôn âm. Nói rõ điều này khi trả lời.

## Các lệnh hỗ trợ

1. `/vl` hoặc `/vl today` — Kết quả kỳ gần nhất
2. `/vl <DD-MM-YYYY>` — Kết quả ngày cụ thể
3. `/vl odds` — Bảng xác suất trúng 0–6 số
4. `/vl stats [N]` — Kiểm định tính ngẫu nhiên trên N kỳ gần nhất (mặc định 50)
5. `/vl backtest [N]` — Backtest chiến lược hot/cold/random trên N kỳ
6. `/vl pick [hot|cold|random]` — Sinh bộ số tham khảo

## Script có sẵn

Tất cả scripts tại `/opt/data/skills/vietlott/scripts/`:

| Script | Mô tả |
|---|---|
| `vl_fetch.py` | Crawler lấy kết quả từ minhngoc.net.vn (stdlib thuần, không cần requests) |
| `vietlott645.py` | Kiểm định thống kê + backtest + sinh số |

## Luồng xử lý từng lệnh

### `/vl` hoặc `/vl today`
```bash
# Tính ngày quay gần nhất (Thứ 4/6/CN), fetch trang ngày đó
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vl_fetch.py --date <DD-MM-YYYY>
```
Trình bày: Kỳ #XXXXX | Ngày DD/MM/YYYY | **6 số** | Jackpot hiện tại (nếu có).

### `/vl <date>`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vl_fetch.py --date <DD-MM-YYYY>
```

### `/vl odds`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py odds
```
Không cần dữ liệu lịch sử. Trả về bảng P(k/6 số trúng).

### `/vl stats [N]`
```bash
# Bước 1: Fetch N kỳ gần nhất
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vl_fetch.py --range <N> --csv
# → tạo file draws.csv trong thư mục hiện tại

# Bước 2: Chạy kiểm định
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py stats draws.csv
```
Kết quả gồm 2 kiểm định:
- **Chi-square tần suất đã hiệu chỉnh**: X²·(N-1)/(N-K) ~ χ²(44). p < 0.05 → nghi vấn lệch.
- **Thống kê thứ tự Q** (arXiv:0806.4595): Q ~ χ²(6) — kiểm định phân phối vị trí số. p < 0.01 → kiểm toán nhà cái.

⚠️ Cần ≥ 100 kỳ để kết quả kiểm định đáng tin. Cảnh báo tự động nếu < 100.

### `/vl backtest [N]`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vl_fetch.py --range <N> --csv
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py backtest draws.csv
```
Kết quả: z-test mỗi chiến lược (hot/cold/random). p < 0.01 mới có ý nghĩa (dùng ngưỡng Bonferroni).

### `/vl pick [mode]`
```bash
# Cần có draws.csv để dùng hot/cold
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py pick --mode hot --csv draws.csv
# Hoặc ngẫu nhiên hoàn toàn (không cần dữ liệu)
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py pick --mode random
```
Luôn in: *"Mọi bộ số đều có xác suất jackpot 1/8.145.060. EV mỗi vé < 0."*

## Chuyển đổi ngày quay

Mega 6/45 quay **Thứ 4, Thứ 6, Chủ nhật** lúc **18:05**.
- "hôm nay" → lấy ngày hiện tại (UTC+7), nếu chưa 18:05 thì lấy kỳ trước đó
- "hôm qua" → ngày hôm qua
- "07/10/2026" / "07-10-2026" → `07-10-2026`

## Lưu ý trình bày

- Trả lời qua Zalo: không dùng markdown, dùng emoji cho trực quan.
- Luôn ghi rõ số kỳ (#XXXXX) và ngày để tránh nhầm.
- Không hứa hẹn lợi nhuận, không nói "dự đoán chính xác".

## 🚨 Pitfalls

### Ngày chưa có kết quả
- Trang `DD-MM-YYYY.html` tồn tại nhưng HTML không chứa `<div class="finnishN bool">` → kết quả chưa được công bố (chưa quay hoặc đang chờ).
- Fix: lấy kỳ gần nhất trước ngày đó.

### Ngày không phải ngày quay
- `vl_fetch.py --range N` tự động chỉ lấy đúng Thứ 4/6/CN.
- Khi dùng `--date` cho ngày không phải ngày quay → trang 404 hoặc không có số.

### Cần ≥ 80 kỳ để backtest có nghĩa
- Script tự exit với thông báo rõ nếu dữ liệu quá ít.

## Tham khảo

- `references/data-sources.md` — nguồn dữ liệu, HTML pattern, endpoint đã xác nhận
- `references/research-notes.md` — tóm tắt hai bài arXiv làm cơ sở thống kê
