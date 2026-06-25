# Plan: Hệ thống tự động theo dõi & xử lý công văn — congchuc.quangninh.gov.vn

> **Trạng thái:** Đang phát triển | **Cập nhật:** 2026-06-22 15:00 ICT
> **Nền tảng:** Hermes Agent (gateway + cron scheduler + Zalo delivery)

---

## Mục tiêu

Xây dựng hệ thống tự động:
1. **Quét** công văn đến định kỳ từ cổng công chức Quảng Ninh
2. **Thông báo** qua Zalo khi có văn bản mới
3. **Đọc nội dung** chi tiết từng văn bản
4. **Dự thảo** văn bản trả lời dạng `.docx`
5. **Quản lý** hạn xử lý, phân loại, xuất báo cáo

---

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Gateway (Docker)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Cron    │  │  Zalo    │  │  Agent   │  │ REST API   │  │
│  │ Scheduler│  │ Platform │  │ (LLM)    │  │ /api/jobs  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │              │         │
│  ┌────▼──────────────▼─────────────▼──────────────▼──────┐  │
│  │              Job Orchestration                        │  │
│  │  • no-agent mode (script trực tiếp)                   │  │
│  │  • agent mode (LLM-driven)                            │  │
│  │  • script → agent pipeline                            │  │
│  └────────────────────┬──────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼──────────────────────────────────┐  │
│  │              Data Layer (~/.hermes/cron/)             │  │
│  │  • cong-van-den/vbden_state.json  (VB đến seen IDs + attachments)  │  │
│  │  • cong-van-den/pending/          (VB chờ xử lý)                   │  │
│  │  • cong-van-den/drafts/           (.docx dự thảo)                  │  │
│  │  • cong-van-den/attachments/      (file đính kèm theo Số đến)      │  │
│  │  • cong-van-den/exports/          (.xlsx báo cáo)                  │  │
│  │  • cong-van-di/vbdidi_state.json  (VB đi seen IDs)   │  │
│  │  • output/{job_id}/               (cron output)      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              congchuc.quangninh.gov.vn                      │
│  • SSO Login → Password warning → Unit selection            │
│  • ASP.NET postback (ViewState, RadGrid)                    │
│  • Tab 1126: Công văn đến (list + đơn vị filter)            │
│  • Tab 1121: Công văn đi (VBDi_TimKiem grid)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Checklist tính năng

### ✅ Đã triển khai

| # | Tính năng | Trạng thái | Ghi chú |
|---|---|---|---|
| F1 | **Quét công văn đến định kỳ** | ✅ Hoàn thành | Script `congchuc/congchuc_scrape.py`, no-agent mode |
| F2 | **Chọn đơn vị tự động** | ✅ Hoàn thành | `CONGVAN_UNIT` trong `.env` (ID hoặc tên) |
| F3 | **Lọc văn bản mới** | ✅ Hoàn thành | State file `vbden_state.json`, so sánh IDs |
| F4 | **Thông báo qua Zalo** | ✅ Hoàn thành | Cron deliver: `zalo`, silent khi không có VB mới |
| F5 | **Schedule giờ hành chính** | ✅ Hoàn thành | `0 1-10 * * 1-5` UTC (= 8h-17h VN, T2-T6) |
| F6 | **ASP.NET compatibility** | ✅ Hoàn thành | ViewState, form fields, password warning, RadGrid parsing |
| F7 | **Filter theo đơn vị** | ✅ Hoàn thành | `CONGVAN_UNIT` trong `.env` (ID hoặc tên) |
| F8 | **Playwright cho pagination** | ✅ Đã triển khai | Click `.rgPageNext` + AJAX wait, lấy 20 docs / 4 trang |
| F10 | **Hạn xử lý** | ⏸️ Tạm dừng | Cột tồn tại (td[12]) nhưng server luôn trả empty |
| F11 | **Phân loại hỏa tốc/khẩn** | ✅ Đã triển khai | Keyword detection trong trích yếu + số KH |
| F18 | **Theo dõi trạng thái xử lý** | ✅ Đã triển khai | `done`/`wip`/`read`/`note`/`status`/`list` qua Zalo |
| F14 | **Theo dõi công văn đi** | ✅ Đã triển khai | Script `congchuc/congchuc_vbdi_scrape.py`, cron `d7f9e2c1a4b6` 8h+15h VN |
| F21 | **Phân trang RadGrid** | ✅ Đã triển khai | Giải pháp Playwright page-by-page click (xem F8) |
| F16a | **Tải file đính kèm** | ✅ Đã triển khai | Nút "Tải tất cả file" trên grid → ZIP → giải nén, 1 click = all files |
| F13 | **Export Excel** | ✅ Đã triển khai | `congchuc_report.py --excel`, 17h thứ 6 hàng tuần |
| F19 | **Báo cáo thống kê định kỳ** | ✅ Đã triển khai | `congchuc_report.py --weekly`, 17h thứ 6 qua Zalo |

### 🚧 Đang phát triển

*Không có*

### 📌 Sẽ triển khai

| # | Tính năng | Ưu tiên | Độ khó | Ghi chú |
|---|---|---|---|---|
| F12 | **Đa đơn vị** | ✅ Đã triển khai | `CONGVAN_UNIT=2256,226,Sản nhi` — loop từng unit, gộp kết quả |
| F15 | **Task auto-create** | Trung bình | Trung bình | Tự tạo kanban/todo khi có VB hỏa tốc |
| F16b | **Onyx RAG ingest** | Thấp | Cao | Ingest nội dung file đính kèm vào Onyx RAG để query |
| F17 | **Dashboard web** | Thấp | Trung bình | Trang web hiển thị danh sách, filter, search, thống kê |
| F20 | **Tự động chuyển/kết thúc văn bản từ xa** | 🚧 Đang phát triển | Playwright tương tác chọn Chuyển/Kết thúc từ tin nhắn Zalo, Tự động kết thúc nếu Vai trò là "Thông báo" / "Để biết" |
| F20a | **Phát hiện VB trùng/thay thế** | ✅ Đã triển khai | Index `so_ky_hieu`, detect từ khóa trong `trich_yeu`, ghi chú state |

---

## Chi tiết từng tính năng

### F1 — Quét công văn đến định kỳ

**Trạng thái:** ✅ Hoàn thành

**Cách hoạt động:**
- Cron job `202d81764afb` chạy `congchuc/congchuc_scrape.py` ở `no-agent` mode
- Schedule: `0 1-10 * * 1-5` UTC (= 8h-17h VN, T2-T6)
- Script login → chọn đơn vị → parse RadGrid → so sánh state → output VB mới

**File liên quan:**
- Script: `~/.hermes/scripts/congchuc/congchuc_scrape.py`
- State: `~/.hermes/cron/cong-van-den/vbden_state.json`
- Output: `~/.hermes/cron/output/202d81764afb/`
- Deploy: `D:\Antigravity\Hermes\scripts\congchuc\deploy_congchuc.ps1`

**Config `.env`:**
```ini
CONGVAN_USER=nguyenhuyphong
CONGVAN_PASS=comeon12
CONGVAN_URL=https://congchuc.quangninh.gov.vn/Default.aspx?tabid=1126
CONGVAN_UNIT=2256
CONGVAN_DOWNLOAD_ATTACHMENTS=1   # Bật tải file đính kèm
```

---

### F2 — Chọn đơn vị tự động

**Trạng thái:** ✅ Hoàn thành

**Cách hoạt động:**
- Sau login, script GET `tabid=56` → parse dropdown `dnn_banner_ddlChonDonVi`
- POST với `__EVENTTARGET=dnn$banner$ddlChonDonVi` + value = ID đơn vị
- Navigate lại `tabid=1126` để lấy documents theo đơn vị đã chọn

**Config:**
- `CONGVAN_UNIT=2256` → dùng ID trực tiếp
- `CONGVAN_UNIT=Sản nhi` → match substring với label
- Để trống → bỏ qua bước chọn đơn vị

---

### F3 — Lọc văn bản mới

**Trạng thái:** ✅ Hoàn thành

**Cách hoạt động:**
- State file lưu `seen_ids` (danh sách IDs đã thấy)
- Mỗi lần chạy: so sánh IDs hiện tại với `seen_ids`
- Chỉ output các VB có ID chưa xuất hiện trong state
- Cập nhật state sau mỗi lần chạy

---

### F4 — Thông báo qua Zalo

**Trạng thái:** ✅ Hoàn thành

**Cách hoạt động:**
- Cron job `deliver: zalo` → Hermes delivery gửi tin nhắn qua Zalo
- Có VB mới → gửi danh sách chi tiết (Số đến, Số, Tác giả, Trích yếu)
- Không có VB mới → silent (không spam)

**Output mẫu:**
```
📋 CÓ VĂN BẢN MỚI - 2026-06-17 09:18:43
Phát hiện 4 văn bản đến ngày 17/06/2026:

1. Số đến: 2348 | Số: 274/KH-UBND
   Tác giả: Ủy ban nhân dân tỉnh Quảng Ninh
   Trích yếu: KH Triển khai Chiến lược phát triển...

👉 Xem chi tiết: https://congchuc.quangninh.gov.vn/Default.aspx?tabid=1126
```

---

### F5 — Schedule giờ hành chính

**Trạng thái:** ✅ Hoàn thành

- Mặc định: `0 1-10 * * 1-5` UTC (= 8h-17h VN, T2-T6)
- Có thể đổi: `hermes cron edit 202d81764afb --schedule "every 30m"`

---

### F6 — ASP.NET compatibility

**Trạng thái:** ✅ Hoàn thành

Script xử lý đầy đủ:
- SSO Login (`/SSO/Login.aspx`) với `IDToken1`/`IDToken2`
- Password warning page (click "Tiếp tục")
- ASP.NET hidden fields: `__VIEWSTATE`, `__EVENTVALIDATION`, `__VIEWSTATEGENERATOR`
- Telerik RadGrid parsing: `rgRow` + `rgAltRow`, 11 cột
- Unit selection postback: `dnn$banner$ddlChonDonVi`
- Cookie management: `http.cookiejar.CookieJar`

---

### F7 — Filter theo đơn vị

**Trạng thái:** ✅ Hoàn thành

**Cách hoạt động:**
- `CONGVAN_UNIT` trong `.env` hỗ trợ 2 format:
  - ID số: `CONGVAN_UNIT=2256` → dùng trực tiếp làm dropdown value
  - Tên substring: `CONGVAN_UNIT=Sản nhi` → match với label
- Script tự động chọn đơn vị sau login, parse docs theo đơn vị đã chọn

---

### F8 — Playwright cho pagination & 17-column parsing

**Trạng thái:** ✅ Đã triển khai | Playwright dùng cho pagination (không phải để lấy 17 cột)

**Phát hiện quan trọng:** Playwright (browser thật) và urllib (HTTP thuần) đều nhận được HTML **12 cột** từ server — không phải do JS rendering. Browser F12 hiển thị 17 cột nhưng HTTP response chỉ có 12. Các cột bị thiếu (`do_khan`, `han_xl`, `nguoi_gui`, `but_phe`) được Telerik RadGrid render từ client-side data.

**Vai trò của Playwright trong hệ thống hiện tại:**

| Mục đích | Playwright | urllib |
|---|---|---|
| Login SSO | ✅ `page.evaluate()` OpenAM | ✅ POST form |
| Unit select | ✅ `select_option()` | ✅ POST event |
| **Pagination** | **✅ Click `.rgPageNext` + AJAX wait** | ❌ Không thể (RadAjaxManager) |
| Parse 12 cột gốc | ✅ | ✅ (giống hệt) |
| Độ khẩn (td[11]) | ✅ `lblDoKhan` có data | ✅ keyword detect |
| Hạn xử lý (td[12]) | ✅ Cột tồn tại **nhưng empty** | ✅ Cột tồn tại **nhưng empty** |

**17 cột trong browser F12 — dữ liệu thực tế (2026-06-18):**
- `td[11] = lblDoKhan`: có dữ liệu ("Hỏa tốc", "Khẩn", "Thường") — ✅ lấy được qua HTTP
- `td[12] = HanXuLy`: **luôn empty** (`<span style="display:block"></span>`) — server không populate deadline
- `td[13] = nguoi_gui`: chỉ hiện trong F12 snapshot, không có trong HTTP response
- `but_phe` / "Thông tin xử lý": lấy được qua `showToolTip` attribute trong raw HTML

**Kết luận:**
- Playwright **cần thiết cho pagination** (lấy all 20 docs thay vì 10)
- Playwright **không giúp lấy thêm cột** ngoài 12 cột đã có
- Hạn xử lý **trống** — không phải lỗi parse, server không có data
- Script có fallback: ưu tiên Playwright, nếu không available → urllib (chỉ page 1)

**Install:**
- Playwright Python package baked vào Docker image (local wheel build)
- Chromium browser installed via `npx playwright install chromium --only-shell` tại build time

---

### F9 — Dự thảo văn bản trả lời (.docx)

**Trạng thái:** 🚧 Thiết lập kế hoạch chi tiết | **Cập nhật:** 2026-06-22 ICT

Chi tiết kế hoạch tích hợp LLM, bộ Skill Văn phòng và hệ thống Onyx RAG (được triển khai tại `http://localhost:3000`) để tự động tạo dự thảo văn bản trả lời chuẩn hành chính NĐ 30 đã được tách sang tài liệu riêng.

👉 **[Xem chi tiết kế hoạch F9 tại đây](file:///d:/Antigravity/Hermes/docs/f9-du-thao-van-ban.md)**

---

### F10 — Theo dõi hạn xử lý

**Trạng thái:** ⏸️ Tạm dừng | **Kết luận:** Server không lưu hạn xử lý cho VB đến ở đơn vị này

**Đã xác minh (2026-06-18):**
- Grid `grdVBDenChoXuLy` có cột `HanXuLy` ở `td[12]` (index 12 trong 17 cột)
- Cột này **luôn empty** cho tất cả VB: `<span style="display:block"></span>` — span rỗng, không text
- Kiểm tra qua cả Playwright (browser thật) và urllib đều cho kết quả giống nhau
- Không phải vấn đề parse hay JS rendering — server đơn giản không trả data cho field này

**Giải thích khả năng:**
- Hạn xử lý có thể do người dùng nhập thủ công cho từng VB (không phải field mặc định)
- Hoặc hạn xử lý chỉ hiển thị khi VB được gán cho đơn vị có quyền xem hạn
- Hoặc field này chỉ dùng cho tab "Công văn đi" hoặc một chức năng khác

**Không cần debug thêm — chuyển hướng:**
- Có thể bỏ qua hoàn toàn (hạn xử lý không available)
- Hoặc implement reminder date do người dùng set thủ công qua Zalo command
- Hoặc nếu có API riêng cho hạn xử lý, cần user cung cấp endpoint

---

### F11 — Phân loại hỏa tốc/khẩn

**Trạng thái:** ✅ Đã triển khai | **Phương pháp:** Keyword detection trên `trich_yeu` + `so_ky_hieu` (không phải từ `lblDoKhan` cột)

**Cách hoạt động:**
1. Script scan `trich_yeu` + `so_ky_hieu` với keyword list:
   - `Cực Khẩn`, `Hỏa tốc hẹn giờ`, `Hỏa tốc`, `Thượng khẩn`, `Khẩn`, `Gấp`, `Tốc ký`
2. Strip parentheses để bắt "(Hỏa tốc)"
3. Nếu phát hiện → VB được đánh dấu urgent, hiển thị ở section riêng đầu báo cáo

**Lưu ý:** `lblDoKhan` (td[11]) có dữ liệu thật ("Hỏa tốc", "Khẩn", "Thường") nhưng không dùng làm primary vì trong 12-col HTTP response không parse được field này. Keyword detection hiện tại đủ bao phủ mọi trường hợp.

**Config:**
```ini
CONGVAN_URGENT_KEYWORDS=Hỏa tốc,Khẩn,Thượng khẩn,Gấp,Cực Khẩn
```

---

### F12 — Đa đơn vị

**Trạng thái:** ✅ Đã triển khai | **Cập nhật:** 2026-06-22 15:30 ICT

**Cách hoạt động:**
- `CONGVAN_UNIT` hỗ trợ list IDs hoặc tên cách nhau bằng dấu phẩy:
  ```ini
  CONGVAN_UNIT=2256,226,Sản nhi
  ```
- Script login 1 lần → loop qua từng unit: chọn unit → navigate → paginate → collect docs
- `seen_so_den` global set ngăn trùng lặp giữa các đơn vị
- Output: `📋 X VB đến mới (2256, 226, Sản nhi)`

**Thay đổi:**
- `UNITS` list: mỗi entry là ID số (dùng `select_option`) hoặc substring tên (match với option text)
- `pw_get_documents()`: refactor unit select + collect vào `_select_unit_and_collect()`, gọi cho từng unit
- Urllib fallback: loop `select_unit()` cho từng unit
- Attachment download: dùng unit đầu tiên để login context

---

### F13 — Export Excel

**Trạng thái:** ✅ Đã triển khai | **Cập nhật:** 2026-06-22 15:00 ICT

**Cách hoạt động:**
- Cron job `b2c3d4e5f6a7` chạy `congchuc_report_excel.sh` (wrapper → `congchuc_report.py --excel`)
- Schedule: `5 10 * * 5` (17h05 VN thứ 6 hàng tuần)
- Script đọc `vbden_state.json` → xuất `.xlsx` với 13 columns:
  STT, Số đến, Ngày VB, Ngày đến, Số/Ký hiệu, Tác giả, Trích yếu, Độ khẩn, Trạng thái, Cập nhật, Ghi chú, Bút phê, File đính kèm
- File lưu tại `~/.hermes/cron/cong-van-den/exports/cong-van-den_YYYY-WW.xlsx`
- Style: header xanh đậm chữ trắng, auto-filter, freeze panes, done VBs in nghiêng xám
- Kết quả gửi qua Zalo kèm đường dẫn

**Thư viện:** `openpyxl` (đã cài qua `uv`)

---

### F14 — Theo dõi công văn đi

**Trạng thái:** ✅ Hoàn thành | **Ưu tiên:** Trung bình | **Độ khó:** Thấp

**Chi tiết kỹ thuật:**
- `tabid=1121` — RadGrid `VBDi_TimKiem_grdDanhSach`, 10 cột, 847 records / 85 pages
- VanBanDiID hidden column (không hiển thị trên UI, parse từ html)
- Search button `btnSearch` (RadButton, JS click) — nhưng grid load data mặc định, ko cần click
- Script mới: `congchuc/congchuc_vbdi_scrape.py` (dùng chung login flow với VB đến)
- **Date filter**: lọc 2 ngày gần nhất (Ngày PH từ hôm qua → hôm nay) để tránh quét 85 pages
- State file riêng: `cong-van-di/vbdidi_state.json`
- Cron job `d7f9e2c1a4b6` schedule: `0 1,8 * * 1-5` (= 8h + 15h VN, T2-T6)

**Lưu ý:**
- Unit filter (`ddlChonDonVi`) là global banner-level — ảnh hưởng cả tab 1126 và 1121
- Nội dung quá dài → Zalo adapter không gửi được; cần giới hạn output hoặc fallback. Hiện tại chỉ gửi kết quả rút gọn
- 10 cột VB đi: Số hiệu, Trích yếu, Loại VB (hidden id), Ngày phát hành, Người soạn, Đơn vị soạn, Trạng thái (always empty), Trích yếu 2 (duplicate), file đính kèm (always empty), VanBanDiID (hidden)

---

### F15 — Task auto-create

**Trạng thái:** 📌 Sẽ triển khai | **Ưu tiên:** Trung bình | **Độ khó:** Trung bình

**Kế hoạch:**
1. Khi phát hiện VB mới (đặc biệt hỏa tốc):
   - Tự tạo task trong Hermes kanban hoặc todo
   - Gán priority dựa trên loại VB
   - Ghi chú VB gốc để user biết
2. Lưu ý: hạn xử lý (F10) không available từ server → deadline sẽ do user set thủ công qua Zalo (`note <id> hạn 25/06`) hoặc gán mặc định N ngày từ ngày đến

---

### F16a — Tải file đính kèm (Attachment download)

**Trạng thái:** ✅ Đã triển khai | **Cập nhật:** 2026-06-22 12:32 ICT

**Cách hoạt động (v2 — ZIP download):**
- Kích hoạt qua env var `CONGVAN_DOWNLOAD_ATTACHMENTS=1`
- Script mở Playwright session → login → tìm VB trong grid chính `tabid=1126`
- **Mỗi dòng trên grid có nút "Tải tất cả file"** (`input[type="image"][title="Tải tất cả file"]`): click → server trả về 1 file ZIP chứa tất cả file đính kèm của VB đó
- **Không cần vào trang chi tiết** — xử lý ngay trên grid chính

**Cơ chế download:**
- Nút `ImageButton1` (ASP.NET `input[type="image"]`) gửi form postback → server tạo ZIP động → Playwright capture download event
- ZIP filename: `SYT_VP.zip` (generic, không theo tên VB)
- File được giải nén vào `attachments/<so_den>/`, mỗi file ghi nhận riêng trong state
- **Đã thử nghiệm**: VB 2432 (4 files) — 1 click = 4 files ~4.3MB

**So sánh với v1 (cũ — per-file through detail page):**
| Tiêu chí | v1 (cũ, detail page) | v2 (hiện tại, grid) |
|---|---|---|
| Số click/VB | N files → vào detail + N clicks btnTai | 1 click → ZIP |
| Giới hạn server | 1 download/page-visit | 1 ZIP = tất cả files |
| Page navigation | VB link → detail → back → next file | Grid → click ZIP → done |
| Thời gian/VB | ~30s (detail page loading) | ~15s (grid + ZIP download) |

**Chi tiết kỹ thuật:**
- Mỗi VB xử lý trên 1 tab trình duyệt riêng (tránh xung đột page state)
- File lưu tại `attachments/<so_den>/` (relative to state dir)
- State entry: `documents[so_den].attachments[]` — mỗi entry có `filename`, `display_name`, `size`, `path`, `downloaded_at`
- Sau khi complete → đánh dấu `attachments_complete: true` → không tải lại
- Giới hạn 10 VB/lần chạy (`[:MAX_ATTACHMENT_DOCS]`)
- Script cũng lưu chi tiết VB vào `state.documents` (so_ky_hieu, tac_gia, trich_yeu, ...)

**Kết quả:**
| VB | Files downloaded | Trạng thái |
|---|---|---|
| 2362 | 1/1 (997KB PDF) | ✅ Complete |
| 2355 | 1/1 (527KB PDF) | ✅ Complete |
| 2432 | 4/4 (734KB + 491KB + 2.9MB + 672KB) | ✅ Complete |

### F16b — Onyx RAG ingest (file → searchable content)

**Trạng thái:** 📌 Sẽ triển khai | **Ưu tiên:** Thấp | **Độ khó:** Cao

**Kế hoạch:**
1. Parse PDF → text (PyMuPDF), DOCX → text (python-docx)
2. Upload parsed content vào Onyx qua API `/onyx-api/ingestion`
3. Cho phép query nội dung văn bản đính kèm khi draft văn bản trả lời

**Tại sao cần ingest:** Tải về nhưng không làm gì với file = lãng phí. Ingest vào Onyx cho phép:
- Query nội dung VB đính kèm khi draft văn bản trả lời
- Search full-text qua tất cả attachments
- RAG context phong phú hơn khi LLM cần reference

---

### F17 — Dashboard web

**Trạng thái:** 📌 Sẽ triển khai | **Ưu tiên:** Thấp | **Độ khó:** Trung bình

**Kế hoạch:**
1. Trang web đơn giản (Flask/FastAPI) đọc data từ state files
2. Features:
   - Danh sách VB (table, sortable)
   - Filter theo đơn vị, ngày, loại
   - Search theo trích yếu, số văn bản
   - Thống kê: tổng VB, theo đơn vị, theo tháng
   - Xem/download draft .docx
   - Xem/download attachments
   - Update trạng thái VB (new/read/in_progress/done/overdue)
3. Route: `http://localhost:9119/cong-van` (tích hợp vào Hermes dashboard)

---

### F18 — Theo dõi trạng thái xử lý ⭐

**Trạng thái:** ✅ Đã triển khai (Docker rebuild #2: 2026-06-18 14:00 ICT)

**Triển khai:**
- Script: `~/.hermes/scripts/congchuc/congvan_status.py`
- State file: `~/.hermes/cron/cong-van-den/vbden_state.json` (migrated sang format mới)

**Commands hỗ trợ:**
| Command | Mô tả | Ví dụ |
|---|---|---|
| `done <id>` | Đánh dấu đã xử lý xong | `done 2348` |
| `wip <id>` | Đang xử lý (work in progress) | `wip 2348` |
| `read <id>` | Đã đọc, chưa xử lý | `read 2348` |
| `note <id> <text>` | Thêm ghi chú | `note 2348 Chờ phản hồi từ Sở Y tế` |
| `status <id>` | Xem trạng thái hiện tại | `status 2348` |
| `list [--status <s>]` | Danh sách VB (optionally filter) | `list --status done` |

**State format mới:**
```json
{
  "documents": {
    "2348": {
      "so_den": "2348",
      "so_ky_hieu": "274/KH-UBND",
      "tac_gia": "UBND tỉnh Quảng Ninh",
      "trich_yeu": "KH Triển khai Chiến lược...",
      "status": "done",
      "status_updated_at": "2026-06-17 15:30:00",
      "note": ""
    }
  },
  "seen_ids": ["2348", "..."],
  "last_check": "2026-06-17 15:11:52",
  "last_count": 10
}
```

**Gateway handler:** Active — intercepts plain text commands trước khi forward đến agent tại `gateway/run.py:8556`.

**Còn lại:**
- [ ] Dashboard hiển thị progress bar

---

### F19 — Báo cáo thống kê định kỳ

**Trạng thái:** ✅ Đã triển khai | **Cập nhật:** 2026-06-22 15:00 ICT

**Cách hoạt động:**
- Cron job `a1b2c3d4e5f6` chạy `congchuc_report_weekly.sh` (wrapper → `congchuc_report.py --weekly`)
- Schedule: `0 10 * * 5` (17h VN thứ 6 hàng tuần)
- Báo cáo gồm:
  - Tổng VB theo dõi
  - Số VB mới trong kỳ
  - Breakdown theo trạng thái (done/wip/read/new/overdue) + %
  - Số VB khẩn
  - 5 VB chưa xử lý gần nhất
- Gửi trực tiếp qua Zalo (no-agent mode, stdout = delivery payload)

**Output mẫu:**
```
📊 Báo cáo tuần 15/06-22/06/2026
────────────────────────────────
📋 Tổng VB theo dõi: 47
🆕 Mới trong kỳ: 3
✅ Đã xử lý (done): 41 (87%)
⏳ Đang xử lý: 4
🔥 Văn bản khẩn: 7

📌 VB chưa xử lý (new):
  🔴 #2454 274/KH-UBND: KH Triển khai Chiến lược...
```

---

### F20 — Tự động chuyển/kết thúc văn bản từ xa & Auto-Finish

**Trạng thái:** 🚧 Đang phát triển | **Cập nhật:** 2026-06-23 ICT

Chi tiết kế hoạch tích hợp tương tác Playwright để tự động thực hiện các hành động xử lý văn bản "Chuyển" hoặc "Kết thúc" từ xa qua tin nhắn đã được ghi nhận riêng.
Ngoài ra bổ sung cơ chế quét "Vai trò" đối với văn bản mới và kết thúc hàng loạt nếu "Vai trò" chỉ là "Thông báo" hoặc "Để biết".

👉 **[Xem chi tiết kế hoạch F20 tại đây](file:///d:/Antigravity/Hermes/docs/f20-tu-dong-chuyen-ket-thuc.md)**

---

### F20a — Phát hiện VB trùng lặp / VB thay thế

**Trạng thái:** ✅ Đã triển khai | **Cập nhật:** 2026-06-22 16:00 ICT

**Cách hoạt động:**
- Sau khi parse VB mới, build index `so_ky_hieu → so_den` từ state documents
- Với mỗi VB mới: nếu `so_ky_hieu` đã tồn tại trong index → phát hiện trùng
- Kiểm tra `trich_yeu` có chứa từ khóa: `thay thế`, `đính chính`, `bổ sung`, `hủy bỏ`, `sửa đổi`
- Nếu có từ khóa → đánh dấu là `related` (liên quan), ghi chú vào state
- Nếu không có từ khóa → đánh dấu là `duplicate` (cảnh báo trùng số)

**Output mẫu:**
```
🔄 VB 123/QĐ-UBND (#2454) — liên quan #2401 (thay thế, bổ sung)
⚠️ VB 456/CT-UBND (#2453) — trùng số với #2387

📋 3 VB đến mới (2256)
```

**State tracking:** Khi phát hiện liên quan, ghi tự động vào `note` field:
```json
{
  "2454": {
    "so_ky_hieu": "123/QĐ-UBND",
    "note": "[Liên quan đến #2401, từ khóa: thay thế, bổ sung] "
  }
}
```

---

### F21 — Phân trang RadGrid (lấy tất cả VB chứ không chỉ page 1)

**Trạng thái:** ✅ Hoàn thành — Playwright page-by-page click + AJAX wait | **Đã triển khai**

**Vấn đề:**
- Telerik RadGrid mặc định hiển thị **10 mẫu tin/trang**
- Grid `grdVBDenChoXuLy` có **19 records, PageCount=2, PageSize=10** (xác nhận qua JavaScript JSON init: `VirtualItemCount:19, PageCount:2`)
- Cron script urllib-only chỉ lấy được page 1 (10 docs) dù page 2 còn 9 docs nữa

**Đã thử — tất cả đều thất bại với HTTP thuần:**

| Phương án | Kết quả | Chi tiết |
|---|---|---|
| Normal POST: `__EVENTTARGET=...$ctl07` (page 2) | 10 docs y hệt page 1 | `so_dens: ['2377','2362',...]` giống 100% |
| Normal POST: `...$ctl10` (Trang sau) | 10 docs y hệt page 1 | same |
| Normal POST: `...$ctl11` (Trang cuối) | 10 docs y hệt page 1 | same |
| Normal POST: `FireCommand:Page,2` | 10 docs y hệt page 1 | same |
| Normal POST: `FireCommand:PageSize,50` | 10 docs y hệt page 1 | pagesize không đổi |
| AJAX POST: `__ASYNCPOST=true` + headers (page 2) | Redirect với lỗi | Server reject: `pageRedirect||error=An unexpected error has occurred` |
| AJAX POST: `__ASYNCPOST=true` + FireCommand | Redirect với lỗi | same |

**Nguyên nhân gốc rễ:**

RadGrid `grdVBDenChoXuLy` được khởi tạo **client-side** qua JavaScript `$create(Telerik.Web.UI.RadGrid, ...)`:
```json
$create(Telerik.Web.UI.RadGrid, {
    "ClientID":"dnn_ctr5725_VBDen_SoVanBan_grdVBDenChoXuLy",
    "_currentPageIndex":0,
    "VirtualItemCount":19,
    "PageCount":2,
    "PageSize":10,
    ...
})
```

Cơ chế pagination:
1. User click page 2 → trình duyệt gọi `javascript:__doPostBack('...$ctl07','')`
2. **RadAjaxManager client-side JS intercepts** `__doPostBack` và chuyển thành AJAX request
3. Server nhận request với `__ASYNCPOST=true`, xử lý qua ASP.NET ScriptManager partial rendering
4. Server trả về **delta response** (pipe-delimited partial HTML) — không phải full HTML

Khi gửi POST thuần (không `__ASYNCPOST`):
- RadGrid server-side không process event vì grid state được quản lý qua AJAX pipeline
- Server luôn render page 1 mặc định

Khi gửi POST với `__ASYNCPOST=true` (giả lập AJAX):
- ASP.NET ScriptManager phát hiện ViewState + async postback không hợp lệ
- Trả về `pageRedirect` với error — forced full page reload

**Kết luận: HTTP thuần KHÔNG THỂ navigate page của RadGrid này.**
- ViewState không thể tái sử dụng cho page 2 (đã verify với 3 targets khác nhau)
- RadAjaxManager + ScriptManager yêu cầu browser JavaScript engine
- Giải pháp duy nhất: **Playwright** (hoặc Selenium) để chạy JS thật

**Giải pháp — Playwright page-by-page click:**

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    
    # Login: OpenAM SSO dùng IDToken1/IDToken2
    page.goto(LOGIN_URL, wait_until="networkidle")
    page.evaluate(f"""
        document.getElementById('IDToken1').value = '{USERNAME}';
        document.getElementById('IDToken2').value = '{PASSWORD}';
        document.getElementById('btnLogin').click();
    """)
    page.wait_for_timeout(3000)
    
    # Unit select
    page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="networkidle")
    page.select_option("select[id$=ddlChonDonVi]", TARGET_UNIT_ID)
    page.wait_for_load_state("networkidle")
    
    # Docs page + pagination
    page.goto(DOCS_URL, wait_until="networkidle")
    try:
        page.wait_for_selector(".rgLoadingDiv", state="hidden", timeout=10000)
    except: pass
    
    all_docs = []
    seen = set()
    while True:
        html = page.content()
        docs = extract_documents(html)
        for d in docs:
            key = d.get("so_den", "")
            if key and key not in seen:
                seen.add(key)
                all_docs.append(d)
        
        next_btn = page.query_selector(".rgPageNext:not(.rgDisabled)")
        if not next_btn:
            break
        next_btn.click()
        page.wait_for_timeout(2000)
        try:
            page.wait_for_selector(".rgLoadingDiv", state="hidden", timeout=10000)
        except: pass
        page.wait_for_load_state("networkidle", timeout=15000)
```

**Tại sao PageSize→50 không work?**

RadGrid `$create(Telerik.Web.UI.RadGrid, ...)` client-side init có `PageSize:10` cứng. Khi gọi `$find(combo).set_value('50')`, RadComboBox thay đổi giá trị dropdown nhưng **không trigger server-side postback**. RadGrid chỉ đổi PageSize khi người dùng click vào dropdown và chọn option → gây `selectedIndexChanged` event → postback. Playwright's `select_option()` không trigger Telerik ComboBox event chain (`rcbItem` click).

**Tại sao page-by-page click work?**

`.rgPageNext` là `<a>` tag gọi `javascript:__doPostBack(...)`. RadAjaxManager intercepts __doPostBack → chuyển thành AJAX request. Trong Playwright (browser thật), JS engine xử lý → server nhận AJAX đúng format → trả delta response → grid cập nhật HTML. Đây là lý do chỉ có browser engine mới work được.

**Kết quả hiện tại:**
- Script `congchuc/congchuc_scrape.py` dùng Playwright cho full flow (login + unit select + pagination)
- Playwright baked into Docker image (build-time install qua local wheel + `--extra playwright`)
- Fallback về urllib nếu Playwright không available (import error guard)
- Lấy được **20 docs / 4 trang** (toàn bộ VB đến của đơn vị)
- Output Zalo-friendly plain text giữ nguyên format

---

## Roadmap đề xuất

### Phase 1 — Hoàn thiện core (tuần này)
- [x] F7: Filter theo đơn vị (CONGVAN_UNIT trong .env)
- [x] F5: Schedule giờ hành chính (0 1-10 * * 1-5 UTC = 8h-17h VN)
- [x] Output plain text cho Zalo (không dùng markdown table)
- [x] F11: Phân loại hỏa tốc/khẩn — keyword detection
- [x] F18: Status tracking — script hoàn thành, gateway handler viết xong
- [x] URL đúng: tabid=1126 (đã sửa cả .env, script, doc)
- [x] "Bút phê" / "Thông tin xử lý" xác nhận lấy được qua showToolTip trong urllib

### Phase 2 — Pagination & Status ✅
- [x] **F21: Phân trang** — Playwright click `.rgPageNext` + wait AJAX (20 docs, 4 trang)
- [x] **F18: Gateway handler rebuild** — Docker rebuild #2 hoàn tất, status commands active qua Zalo
- [x] **F8: 17 cột** — xác nhận Độ khẩn parse đúng (td[11]=lblDoKhan có "Hỏa tốc", "Khẩn", "Thường")
- [x] **F10: Hạn xử lý** — Cột tồn tại (td[12]) nhưng **luôn empty**; server không lưu deadline cho VB đến
- [x] **Sửa hardcode** — Loại bỏ credentials mặc định, cấu hình động base URL từ `CONGVAN_URL`, và chuyển các đường dẫn file trạng thái/env sang sử dụng `HERMES_HOME` (trong cả 2 script quét văn bản đến/đi).

### Phase 3 — Mở rộng ✅
- [x] F12: Đa đơn vị
- [x] F13: Export Excel
- [x] F14: Theo dõi công văn đi
- [x] F19: Báo cáo thống kê tuần/tháng qua Zalo

### Phase 4 — UI & attachments (tuần 5-6)
- [x] F16a: Attachment download — đã triển khai (còn multi-file catch-up dần)
- [ ] F16b: Ingest nội dung attachment vào **Onyx RAG**
- [ ] F17: Dashboard web (có update trạng thái VB)
- [ ] F20: Tự động chuyển/kết thúc văn bản từ xa
- [x] F20a: Phát hiện VB trùng/thay thế

---

## ⚠️ Lưu ý bảo mật

- **Credentials trong `.env`**: `CONGVAN_PASS` để plain text — OK cho local, nhưng nếu expose REST API (`/api/jobs`) cần đảm bảo `.env` không bao giờ được serve qua endpoint.
- **API_SERVER_KEY**: Không commit, dùng biến môi trường hoặc vault.
- **Session cookies**: Playwright cần giữ login state — lưu cookie jar an toàn, rotate định kỳ.

---

## Phụ lục

### Cấu trúc thư mục

```
~/.hermes/
├── .env                              # Secrets (CONGVAN_USER, CONGVAN_PASS, ...)
├── scripts/                          # Deployed from D:\Antigravity\Hermes\scripts\
│   └── congchuc/                     # Scripts quét + trạng thái
│       ├── congchuc_scrape.py        # Script scrape VB đến
│       ├── congchuc_vbdi_scrape.py   # Script scrape VB đi
│       ├── congvan_status.py         # Trạng thái xử lý (done/wip/read/note/status/list)
│       ├── congchuc_report.py        # Export Excel + báo cáo thống kê
│       ├── congchuc_report_weekly.sh # Wrapper cho --weekly
│       └── congchuc_report_excel.sh  # Wrapper cho --excel
├── cron/
│   ├── jobs.json                     # Cron job definitions
│   ├── cong-van-den/
│   │   ├── vbden_state.json          # State: seen IDs + documents + attachments list
│   │   ├── attachments/              # Downloaded files theo Số đến/
│   │   └── exports/                  # Excel exports (tuần)
│   ├── cong-van-di/
│   │   └── vbdidi_state.json         # State: seen VanBanDiIDs, last check
│   └── output/
│       ├── 202d81764afb/             # VB đến cron output
│       │   └── 2026-06-17_09-18-43.md
│       └── d7f9e2c1a4b6/             # VB đi cron output
├── skills/
│   └── cong-van/
│       └── SKILL.md                  # Skill reference (optional)
```

### Cron job hiện tại

| ID | Tên | Schedule (UTC) | Giờ VN | Script |
|----|-----|----------------|--------|--------|
| `202d81764afb` | Quét công văn đến | `0 8-17 * * 1-5` | 8h-17h T2-T6 | `congchuc_scrape.py` |
| `d7f9e2c1a4b6` | Quét văn bản đi | `0 8,15 * * 1-5` | 8h, 15h T2-T6 | `congchuc_vbdi_scrape.py` |
| `a1b2c3d4e5f6` | Báo cáo tuần CV đến | `0 10 * * 5` | 17h thứ 6 | `congchuc_report_weekly.sh` |
| `b2c3d4e5f6a7` | Export Excel CV đến | `5 10 * * 5` | 17h05 thứ 6 | `congchuc_report_excel.sh` |

### Commands hữu ích

```bash
# Kiểm tra cron
hermes cron list

# Chạy thử job
hermes cron run 202d81764afb

# Xem log
hermes logs --follow --cron

# Sửa schedule
hermes cron edit 202d81764afb --schedule "every 30m"

# Trigger qua REST API
curl -X POST http://localhost:8642/api/jobs/202d81764afb/run \
  -H "Authorization: Bearer $API_SERVER_KEY"
```
