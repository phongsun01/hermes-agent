---
name: news
description: "Morning briefings: weather, tides, lunar calendar, gold prices, currency rates, news feeds, and historical anniversaries."
version: 1.0.0
author: Antigravity
license: MIT
---

# News — Trợ lý Bản tin sáng & Tổng hợp tin tức hàng ngày Việt Nam

Kỹ năng tổng hợp thông tin ngày mới bao gồm thời tiết, triều cường, ngoại tệ, giá xăng dầu, giá vàng, âm lịch, ngày kỷ niệm lịch sử và tin tức RSS.

## Lệnh hỗ trợ (Slash Commands)

- `/newsmenu` — Hiển thị Menu bản tin sáng dạng nút bấm trực quan (Telegram/Zalo).
- `/news vang` — Xem giá vàng miếng SJC và vàng nhẫn 9999 mới nhất.
- `/news xang` — Xem giá xăng dầu Petrolimex hôm nay.
- `/news tygia` — Xem tỷ giá ngoại tệ Vietcombank (USD, EUR...).
- `/news thoitiet [tên_tỉnh]` — Xem dự báo thời tiết hôm nay của tỉnh/thành (mặc định: Quảng Ninh).
- `/news trieucuong [tên_tỉnh]` — Xem thông tin triều cường (mặc định: Quảng Ninh - trích xuất tại Cẩm Phả).
- `/news amlich [dd/MM/yyyy]` — Chuyển đổi Dương lịch sang Âm lịch Việt Nam (mặc định: hôm nay).
- `/news tintuc [chủ đề]` — Điểm tin tức cập nhật 24h qua RSS (mặc định: tin tức thông thường).
- `/news today` — Xem các ngày kỷ niệm và sự kiện lịch sử của Việt Nam và Thế giới trong ngày này.

## Cách hoạt động

Kỹ năng này hoạt động bằng cách gọi bộ định tuyến Python chạy trực tiếp các script cào dữ liệu trong `scripts/news/`.

```bash
python skills/news/lib/news_router.py "vang"
python skills/news/lib/news_router.py "thoitiet Ha Noi"
```
