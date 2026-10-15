# Nguồn dữ liệu Vietlott Mega 6/45

## Nguồn chính: minhngoc.net.vn (đã xác nhận hoạt động)

### URL theo ngày (static HTML — KHÔNG cần JavaScript)

```
https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45/DD-MM-YYYY.html
```

**Ví dụ:** `https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45/07-10-2026.html`

### HTML pattern kết quả (xác nhận ngày 07/10/2026, kỳ #1572)

```html
<ul class="result-number">
  <li><div class="finnish1 bool">10</div></li>
  <li><div class="finnish2 bool">14</div></li>
  <li><div class="finnish3 bool">36</div></li>
  <li><div class="finnish4 bool">37</div></li>
  <li><div class="finnish5 bool">41</div></li>
  <li><div class="finnish6 bool">43</div></li>
</ul>
```

Regex: `class="finnish\d\s+bool"[^>]*>(\d+)<` → 6 số theo thứ tự tăng dần

Số kỳ: `id="DT6X45_KY_VE">#01572` — Regex: `id="DT6X45_KY_VE">#?(\d+)`

### Lịch quay

| Thứ | Weekday Python | Giờ quay |
|---|---|---|
| Thứ 4 (Wed) | 2 | 18:05 |
| Thứ 6 (Fri) | 4 | 18:05 |
| Chủ nhật (Sun) | 6 | 18:05 |

### Status hiện tại (09/10/2026)

- `vl_fetch.py --date 07-10-2026` → thành công, trả về CSV đúng
- Delay khuyến nghị: 0.5s giữa các request khi crawl nhiều kỳ

---

## Nguồn thay thế (không tự động được)

### vietlott.vn (nguồn gốc)
- `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html` — chặn bot, cần Playwright
- `https://vietlott.vn/vi/trung-thuong/winning-number-645` — cache cũ, chỉ có ~8 kỳ năm 2020

---

## Lý do KHÔNG dùng live data endpoint

Trang chính `mega-6x45.html` load kết quả trực tiếp qua AJAX JavaScript:
- `strUrl = "/xstt/vietlott/vietlott.php"` trên `server-liveXX.minhngoc.net.vn`
- Tất cả `server-liveXX.minhngoc.net.vn/xstt/vietlott/vietlott.php` → **404** khi không có JS context
- `js_m4.js` endpoint trả `kqxs.vlt={run:0,...}` — chỉ chứa trạng thái live, không có số kết quả

→ Giải pháp: dùng trang HTML static theo ngày (đã xác nhận ổn định).
