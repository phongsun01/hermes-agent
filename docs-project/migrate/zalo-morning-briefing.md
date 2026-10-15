# Hướng dẫn di trú Hệ thống Zalo Morning Briefing & Agent Utilities

Tài liệu này hướng dẫn chi tiết về tác dụng của từng file liên quan đến tính năng gửi bản tin sáng (thời tiết, âm lịch, giá xăng, giá vàng, tỷ giá, tin tức) trên kênh Zalo (`zalo-agent`) và cách đóng gói để chuyển sang máy khác.

---

## 1. Danh sách và Tác dụng của các File liên quan

Để di trú tính năng này, bạn cần chuyển các file nằm trong thư mục gốc `.openclaw` sau:

### A. Bản tin Sáng & Âm lịch
* **[generate_zalo_morning_brief.py](file:///Users/xitrum/.openclaw/workspace/scripts/zalo/generate_zalo_morning_brief.py)**
  * *Tác dụng:* Script chính thu thập tin tức từ các RSS feeds trong nước (VnExpress, Tuổi Trẻ, Thanh Niên...) và quốc tế (Google News AI, Politics, Economy). Nó kết xuất kết quả dự báo thời tiết, giá xăng, ngày âm lịch, đố vui và ghi ra file kết quả để gửi đi.
* **[lunar_convert.py](file:///Users/xitrum/.openclaw/workspace/scripts/lunar_convert.py)**
  * *Tác dụng:* Thư viện chuyển đổi ngày dương lịch sang âm lịch Việt Nam, phục vụ việc hiển thị ngày âm lịch trong bản tin.

### B. Các Script Thu thập Dữ liệu (Dưới dạng API nội bộ)
* **[fetch_weather_zalo.py](file:///Users/xitrum/.openclaw/workspace/scripts/zalo-agent/fetch_weather_zalo.py)**
  * *Tác dụng:* Gọi API thời tiết (ưu tiên Open-Meteo, fallback wttr.in) để lấy thông tin thời tiết chuẩn theo địa điểm yêu cầu (ví dụ: Hạ Long, Hà Nội).
* **[fetch_vn_market_rates.py](file:///Users/xitrum/.openclaw/workspace/scripts/zalo-agent/fetch_vn_market_rates.py)**
  * *Tác dụng:* Lấy dữ liệu tỷ giá USD/VND (từ Vietcombank, FreeForex, Open Exchange Rates) và giá vàng SJC Việt Nam.
* **[fetch_vn_fuel_prices.py](file:///Users/xitrum/.openclaw/workspace/scripts/zalo-agent/fetch_vn_fuel_prices.py)**
  * *Tác dụng:* Thu thập giá bán lẻ xăng dầu Việt Nam (xăng RON 95, E5, dầu DO).

### C. Bộ điều phối & Dữ liệu Cấu hình
* **[zalo_codefirst_dispatch.py](file:///Users/xitrum/.openclaw/workspace/scripts/zalo-agent/zalo_codefirst_dispatch.py)**
  * *Tác dụng:* Bộ phân tích cú pháp tin nhắn đến. Khi người dùng nhắn các yêu cầu tra cứu nhanh như "thời tiết", "giá vàng", "giá xăng", file này sẽ điều phối chạy các script thu thập dữ liệu tương ứng ở trên và trả kết quả về cho chatbot Zalo.
* **[commemorative-days-vi.json](file:///Users/xitrum/.openclaw/workspace-zalo-agent/data/commemorative-days-vi.json)**
  * *Tác dụng:* Chứa danh sách các ngày lễ và kỷ niệm quan trọng tại Việt Nam để hiển thị tự động trên bản tin sáng.

---

## 2. Hướng dẫn đóng gói (Packaging)

Để đóng gói toàn bộ các file trên thành một tệp nén duy nhất (`zalo_brief_migration.tar.gz`) giữ nguyên cấu trúc thư mục, bạn có thể thực hiện lệnh sau trong terminal tại máy nguồn:

```bash
cd /Users/xitrum/.openclaw && tar -czvf workspace/zalo_brief_migration.tar.gz \
  workspace/scripts/zalo/generate_zalo_morning_brief.py \
  workspace/scripts/lunar_convert.py \
  workspace/scripts/zalo-agent/fetch_weather_zalo.py \
  workspace/scripts/zalo-agent/fetch_vn_market_rates.py \
  workspace/scripts/zalo-agent/fetch_vn_fuel_prices.py \
  workspace/scripts/zalo-agent/zalo_codefirst_dispatch.py \
  workspace-zalo-agent/data/commemorative-days-vi.json
```

Tệp tin đóng gói sẽ được lưu tại: [zalo_brief_migration.tar.gz](file:///Users/xitrum/.openclaw/workspace/zalo_brief_migration.tar.gz)

---

## 3. Hướng dẫn triển khai ở Máy mới (Deployment)

1. Sao chép file `zalo_brief_migration.tar.gz` sang máy mới.
2. Di chuyển file nén vào thư mục `.openclaw` của người dùng trên máy mới (ví dụ `~/.openclaw`).
3. Giải nén bằng lệnh:
   ```bash
   tar -xzvf zalo_brief_migration.tar.gz
   ```
4. Đảm bảo các thư viện python cần thiết đã được cài đặt trong môi trường chạy của OpenClaw trên máy mới (hầu hết các script đều sử dụng thư viện chuẩn của Python như `urllib`, `xml`, `json` nên không cần cài đặt thêm thư viện ngoài).
