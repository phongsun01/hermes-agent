# Plan: Vietlott 6/45 Skill (`/vl`)

## ✅ Kết quả nghiên cứu minhngoc.net.vn

**Kết luận: CÓ THỂ scrape tự động bằng Python thuần (không cần Playwright).**

### Cơ chế lấy dữ liệu

| Loại | URL | Kết quả |
|---|---|---|
| **Trang theo ngày (STATIC)** | `https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45/DD-MM-YYYY.html` | ✅ Kết quả nhúng trực tiếp trong HTML |
| Trang chính + live | `...mega-6x45.html` | Kết quả load qua JS (không parse được bằng curl) |
| API live server | `server-liveXX.minhngoc.net.vn/xstt/vietlott/vietlott.php` | ❌ 404 |
| Status endpoint | `/ajax/status_tinh.php?tinhid=mega-6x45` | Trả về HTML text (waiting notice), không chứa số |

### HTML Pattern đã xác nhận

```html
<!-- Ví dụ: kỳ #01572 ngày 07/10/2026 → 10, 14, 36, 37, 41, 43 -->
<ul class="result-number">
  <li><div class="finnish1 bool">10</div></li>
  <li><div class="finnish2 bool">14</div></li>
  <li><div class="finnish3 bool">36</div></li>
  <li><div class="finnish4 bool">37</div></li>
  <li><div class="finnish5 bool">41</div></li>
  <li><div class="finnish6 bool">43</div></li>
</ul>
```

Regex parse: `class="finnish\d bool">(\d+)<` → 6 số, đã sắp xếp tăng dần.
Kỳ vé: `id="DT6X45_KY_VE">#01572` → dùng để điền cột `ky`.

### Lịch quay: Thứ 4, Thứ 6, Chủ nhật — ~3 kỳ/tuần

---

## Cấu trúc thư mục

```
skills/vietlott/
├── SKILL.md
├── scripts/
│   ├── vietlott645.py         ← chuyển từ docs-project/vietlott/
│   └── vl_fetch.py            ← crawler mới: fetch theo ngày từ minhngoc
└── references/
    ├── data-sources.md        ← xác nhận endpoint, HTML pattern, cron schedule
    └── research-notes.md      ← tóm tắt 0806.4595 và 2403.12836
```

---

## `vl_fetch.py` — Thiết kế crawler

```python
# python vl_fetch.py [--date DD-MM-YYYY]   # lấy 1 ngày
# python vl_fetch.py --range 50             # crawl 50 kỳ gần nhất từ hôm nay
# Output: CSV chuẩn dùng cho vietlott645.py (cột: ngay,n1..n6,ky)
```

Logic:
1. Nếu `--date`: fetch URL `mega-6x45/DD-MM-YYYY.html`, parse regex, in CSV.
2. Nếu `--range N`: tính ngược các ngày quay (Thứ 4/6/CN) từ hôm nay, fetch tuần tự với delay 0.5s.
3. Retry tự động 2 lần nếu timeout.

---

## `SKILL.md` — Nội dung (thiết kế)

### Các lệnh `/vl`
| Lệnh | Mô tả |
|---|---|
| `/vl` hoặc `/vl today` | Lấy kết quả kỳ gần nhất + in kỳ, ngày, 6 số |
| `/vl odds` | Bảng xác suất trúng 0–6 số (không cần dữ liệu) |
| `/vl stats [N]` | Fetch N kỳ → chi-square + Q test |
| `/vl backtest [N]` | Fetch N kỳ → walk-forward 3 chiến lược |
| `/vl pick [hot\|cold\|random]` | Sinh bộ số tham khảo kèm disclaimer |

### Luồng fetch tự động
1. Gọi `vl_fetch.py --date DD-MM-YYYY` để lấy kết quả 1 kỳ.
2. Gọi `vl_fetch.py --range N` để tích lũy lịch sử vào `draws.csv`.
3. Pipe vào `vietlott645.py stats draws.csv` hoặc `backtest`.

---

## Các bước thực hiện

- [x] Nghiên cứu minhngoc.net.vn — xác nhận scrape được
- [ ] Tạo thư mục `skills/vietlott/scripts/` và `references/`
- [ ] Chép `vietlott645.py` vào `skills/vietlott/scripts/`
- [ ] Viết `vl_fetch.py` (crawler HTML thuần Python)
- [ ] Viết `SKILL.md` hoàn chỉnh
- [ ] Viết `references/data-sources.md`
- [ ] Viết `references/research-notes.md`
- [ ] Lưu plan vào `docs-project/vietlott/plan.md`
- [ ] Đồng bộ sang `C:\Users\Desktop\.hermes\skills\vietlott\`
- [ ] Git commit & push
