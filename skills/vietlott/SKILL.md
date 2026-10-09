---
name: vietlott
description: "Phân tích Vietlott Mega 6/45 — xem kết quả, kiểm định tính ngẫu nhiên, backtest chiến lược 'hot/cold/random', xác suất trúng và sinh bộ số tham khảo. Kích hoạt khi người dùng hỏi về Vietlott 6/45 hoặc dùng lệnh /vl."
version: "1.1.0"
---

# Vietlott Mega 6/45

Skill phân tích Vietlott 6/45 dựa trên dữ liệu lịch sử từ minhngoc.net.vn, có cơ chế cache và cập nhật tự động.

> ⚠️ **Nguyên tắc bắt buộc**: Các kỳ quay độc lập — không có phương pháp dự đoán nào đánh bại được ngẫu nhiên. Xác suất Jackpot là 1/8.145.060. Kỳ vọng mỗi vé luôn âm ($EV < 0$). Luôn nói rõ điều này khi trả lời.

## Các lệnh hỗ trợ

1. `/vl` hoặc `/vl today` — Kết quả kỳ gần nhất (tự động xét trước/sau 18:30)
2. `/vl <DD-MM-YYYY>` — Kết quả ngày cụ thể
3. `/vl odds` — Bảng xác suất trúng 0–6 số (phân phối siêu bội)
4. `/vl stats [N]` — Kiểm định tính ngẫu nhiên trên N kỳ gần nhất (mặc định 300 kỳ từ cache `draws.csv`)
5. `/vl backtest [N]` — Backtest chiến lược hot/cold/random trên N kỳ (mặc định 300 kỳ)
6. `/vl pick [hot|cold|random]` — Sinh bộ số tham khảo (dùng cache nếu có)
7. `/vl update` — Cập nhật các kỳ quay mới vào cache `draws.csv`

## Script có sẵn

Tất cả scripts tại `/opt/data/skills/vietlott/scripts/`:

| Script | Mô tả |
|---|---|
| `vl_fetch.py` | Crawler lấy kết quả từ minhngoc.net.vn; hỗ trợ `--update`, `--range`, `--backfill`, `--out` (stdlib thuần) |
| `vl_report.py` | Tạo báo cáo kết quả hoàn chỉnh theo template có đánh số mục dành cho cron / tin nhắn |
| `vietlott645.py` | Kiểm định thống kê (Chi-square hiệu chỉnh + Q-stat arXiv:0806.4595) + backtest walk-forward + sinh số |
| `draws.csv` | File cache dữ liệu lịch sử các kỳ quay (ngay, n1..n6, ky) theo thứ tự tăng dần |

## Luồng xử lý từng lệnh

### `/vl` hoặc `/vl today`
Xuất báo cáo kết quả đầy đủ theo mẫu chuẩn có đánh số:
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vl_report.py
```
*Tự động lấy kỳ mới nhất: nếu trước 18:30 của ngày quay thì lấy kỳ trước đó, không bị lỗi dữ liệu rỗng.*

### `/vl <date>`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vl_fetch.py --date <DD-MM-YYYY>
```

### `/vl odds`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py odds
```

### `/vl stats [N]`
Đọc trực tiếp từ file cache `draws.csv` (không cào lại mạng, mặc định $N=300$):
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py stats -n <N>
```
Kết quả gồm 2 kiểm định:
- **Chi-square tần suất đã hiệu chỉnh**: $X^2 \cdot (N-1)/(N-K) \sim \chi^2(44)$. $p < 0.05 \rightarrow$ nghi vấn lệch tần suất.
- **Thống kê thứ tự Q** ([arXiv:0806.4595](file:///D:/Antigravity/Hermes/skills/vietlott/references/research-notes.md)): $Q \sim \chi^2(6)$ — kiểm định phân phối vị trí các số đã sắp xếp. $p < 0.01 \rightarrow$ kiểm toán tính công bằng của nhà đài.

### `/vl backtest [N]`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py backtest -n <N>
```
Mô phỏng walk-forward đánh giá z-score và p-value cho các chiến lược: `random`, `hot` (tần suất / CDM), `cold`. Dùng ngưỡng Bonferroni ($p < 0.01$) để tránh kết luận sai do data dredging.

### `/vl pick [mode]`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vietlott645.py pick --mode [hot|cold|random] -n 1
```

### `/vl update`
```bash
/opt/hermes/.venv/bin/python3 /opt/data/skills/vietlott/scripts/vl_fetch.py --update
```

## Lịch quay & Cron tự động

- Mega 6/45 quay **Thứ 4, Thứ 6, Chủ nhật** lúc **18:05**.
- Cron tự động cập nhật: cấu hình chạy `vl_fetch.py --update` lúc **18:45 Thứ 4/6/CN**.

## Tham khảo

- `references/data-sources.md` — nguồn dữ liệu, URL pattern, HTML structure
- `references/research-notes.md` — phân tích cơ sở toán học của 2 bài báo arXiv:0806.4595 và arXiv:2403.12836
- `references/test_fixtures.py` — unit test parser đối chiếu với fixture kỳ 00642 và 01572
