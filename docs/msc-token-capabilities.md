# 🔑 MSC Token — Bạn có thể làm gì & Gợi ý tính năng mới

## Tổng quan Token

`MSC_SESSION_TOKEN` (và tùy chọn `MSC_COOKIE`) cho phép Hermes giao tiếp với **14+ hidden API endpoints** trên hệ thống Mua Sắm Công quốc gia (`muasamcong.mpi.gov.vn`). Dưới đây là bản đồ toàn bộ năng lực hiện có và gợi ý tính năng mới.

---

## 📊 Những gì Token hiện tại ĐANG LÀM ĐƯỢC

### A. Đã triển khai & hoạt động

| # | Tính năng | API Endpoint | Script |
|---|-----------|-------------|--------|
| 1 | **Tìm kiếm TBMT** (Thông báo mời thầu) theo đơn vị | `/services/smart/search` | `msc_hidden_api_list.py` |
| 2 | **Tìm kiếm KHLCNT** (Kế hoạch lựa chọn nhà thầu) | `/services/smart/search` | `msc_hidden_api_list.py` |
| 3 | **Xem chi tiết TBMT** (Tab 1: Mời thầu) | `/bid-po-bido-notify-contractor-view/get-by-id` | `msc_tbmt_detail.py` |
| 4 | **Xem biên bản mở thầu** (Tab 2) | `/ldtkqmt/bid-notification-p/notify` + `/roundmng` + `/bid-open` + `/lot-open` | `msc_tbmt_detail.py` |
| 5 | **Xem kết quả LCNT** (Tab 3) | `/contractor-input-result/get` | `msc_tbmt_detail.py` |
| 6 | **Xem chi tiết KHLCNT** | `/bid-po-bidp-plan-project-view/get-by-id` | `msc_khlcnt_detail.py` |
| 7 | **Tra cứu giá trúng thầu** (7 tab: Hàng hóa, Thiết bị VTYT, Thuốc Generic/Biệt dược/Dược liệu...) | `/services/smart/search_prc` | `msc_bid_pricing_search.py` |
| 8 | **Lookup mã IB** (Thông báo mời thầu) | `/services/smart/search` | `msc_ib_lookup.py` |
| 9 | **Lookup mã PL** (Kế hoạch) | `/services/smart/search` | `msc_pl_lookup.py` |
| 10 | **Đếm KHLCNT/TBMT theo ngày** | `/services/smart/search` | `msc_hidden_api_counts.py` |
| 11 | **Báo cáo hàng ngày** (so sánh hôm nay vs hôm qua) | aggregation | `msc_hidden_api_daily_report.py` |
| 12 | **Quản lý Watchlist** (thêm/xóa/liệt kê đơn vị theo dõi) | SQLite local | `msc_watchlist_manage.py` |
| 13 | **Resolve đơn vị** (tìm mã đơn vị bằng tên) | `/um/lookup-orgInfo` | `msc_unit_resolve.py` |
| 14 | **Watchlist Cron** (tự động quét TBMT mới + push Telegram/Zalo 18h hàng ngày) | aggregation | `msc_watchlist_publish_telegram.py` |
| 15 | **Export TBMT/KHLCNT → Markdown** | aggregation | `msc_expt_tbmt.py`, `msc_exp_khlcnt.py` |
| 16 | **Inline Menu Telegram** (`/mscmenu`) | — | `telegram_menu_bridge.py` |

---

## 💡 GỢI Ý TÍNH NĂNG MỚI

### 🔴 Mức độ: Rất hữu dụng — Nên làm ngay

#### 1. 📈 **Theo dõi Deadline & Cảnh báo sắp hết hạn**
> **Vấn đề**: Bạn theo dõi 30+ đơn vị nhưng không biết TBMT nào sắp hết hạn nộp HSDT.
>
> **Giải pháp**: Tạo cron job quét `bidCloseDate` của các TBMT đang mở từ watchlist. Nếu deadline < 48h → push cảnh báo Telegram/Zalo ngay.
>
> **Cần làm**:
> - Script mới: `msc_deadline_alert.py`
> - Thêm cron entry (ví dụ: chạy 8h sáng hàng ngày)
> - Dữ liệu đã có sẵn trong response `bidCloseDate` / `closingDate`

#### 2. 📊 **So sánh giá trúng thầu (Price Benchmarking)**
> **Vấn đề**: Khi chuẩn bị dự thầu, cần biết giá trúng thầu lịch sử của 1 mặt hàng.
>
> **Giải pháp**: Mở rộng `msc_bid_pricing_search.py` để:
> - Tìm 1 mặt hàng → lấy top 20 kết quả giá trúng
> - Tính: giá trung bình, giá thấp nhất, giá cao nhất, xu hướng (tăng/giảm theo thời gian)
> - Gợi ý "khoảng giá an toàn" để đấu thầu
>
> **Cần làm**:
> - Script mới: `msc_price_benchmark.py`
> - Tích hợp `/mscmenu` → nút "📊 So sánh giá"

#### 3. 🔔 **Thông báo TBMT mới theo ngành/lĩnh vực**
> **Vấn đề**: Bạn chỉ theo dõi theo đơn vị. Nhưng đôi khi cần biết "hôm nay có TBMT nào về thiết bị y tế không?" mà không cần biết đơn vị cụ thể.
>
> **Giải pháp**: Tạo keyword-based watchlist — cron quét TBMT toàn quốc theo từ khóa (ví dụ: "siêu âm", "máy X-quang", "nội thất văn phòng").
>
> **Cần làm**:
> - Bảng DB mới: `watchlist_keywords` (keyword, tab, created_at)
> - Script: `msc_keyword_watch.py`
> - Cron: chạy cùng lúc với watchlist đơn vị

---

### 🟡 Mức độ: Hữu dụng — Nên cân nhắc

#### 4. 📋 **Tự động tạo bảng so sánh đối thủ**
> **Vấn đề**: Khi xem kết quả LCNT (Tab 3), bạn thấy danh sách nhà thầu trúng. Nhưng muốn biết nhà thầu nào hay trúng ở lĩnh vực mình?
>
> **Giải pháp**: Từ dữ liệu KQLCNT đã có (endpoint `/contractor-input-result/get`):
> - Thu thập lịch sử trúng thầu của 1 nhà thầu
> - So sánh: mình thua ở gói nào, thua bao nhiêu %, nhà thầu trúng là ai
> - Tạo "hồ sơ đối thủ" (competitor profile)
>
> **Cần làm**:
> - Script: `msc_competitor_analysis.py`
> - Dùng search API với tên nhà thầu → aggregate kết quả

#### 5. 📑 **Export Excel/CSV cho hồ sơ dự thầu**
> **Vấn đề**: Hiện tại export ra Markdown. Nhưng khi làm hồ sơ thầu cần dữ liệu ở Excel.
>
> **Giải pháp**: Tạo export pipeline: TBMT detail → Excel/CSV với:
> - Sheet 1: Thông tin chung (bên mời thầu, hình thức, thời gian)
> - Sheet 2: Danh sách gói thầu (tên, giá dự toán, nguồn vốn)
> - Sheet 3: Lịch sử giá trúng thầu (từ price search)
>
> **Cần làm**:
> - Thêm `openpyxl` dependency
> - Script: `msc_export_excel.py`
> - Tích hợp `/mscmenu` → nút "📥 Export Excel"

#### 6. 📆 **Lịch đấu thầu (Bid Calendar)**
> **Vấn đề**: Quản lý nhiều gói thầu cùng lúc, dễ quên deadline.
>
> **Giải pháp**: Tạo Bid Calendar view:
> - Quét watchlist → lấy tất cả TBMT đang mở
> - Sắp xếp theo `bidCloseDate`
> - Format dạng lịch: tuần này → tuần sau → tháng sau
> - Sync với Google Calendar (dùng API đã có trong TKB)
>
> **Cần làm**:
> - Script: `msc_bid_calendar.py`
> - Tích hợp Google Calendar API (reuse từ TKB skill)

---

### 🟢 Mức độ: Nâng cao — Triển khai khi sẵn sàng

#### 7. 🤖 **AI Phân tích Hồ sơ mời thầu (HSMT)**
> **Vấn đề**: Tải HSMT (PDF/Word) về nhưng phải đọc thủ công 50-100 trang.
>
> **Giải pháp**: Upload HSMT → Hermes AI đọc và tóm tắt:
> - Điều kiện tham gia (năng lực, kinh nghiệm tương tự)
> - Tiêu chuẩn đánh giá (giá, kỹ thuật, bao nhiêu %)
> - Danh mục hàng hóa/vật tư yêu cầu
> - Các điểm bất thường / rủi ro ("có hạn chế nhà thầu?")
>
> **Cần làm**:
> - Tool: `msc_hsmt_analyzer` (dùng LLM đọc PDF)
> - Integration với file upload Telegram

#### 8. 🔗 **Kết nối GrafosAI-Autofill Extension** (đã có đề xuất)
> Tự động trích xuất dữ liệu → điền form trên trang MSC.
> Xem chi tiết tại [msc-autofill-proposal.md](file:///d:/Antigravity/Hermes/docs/msc-autofill-proposal.md).

#### 9. 📊 **Dashboard thống kê thị trường đấu thầu**
> **Vấn đề**: Muốn nắm bức tranh tổng quan thị trường.
>
> **Giải pháp**: Tạo report tuần/tháng:
> - Tổng số KHLCNT/TBMT cả nước
> - Top 10 đơn vị đăng nhiều TBMT nhất
> - Phân bổ theo lĩnh vực (Hàng hóa / Xây lắp / Tư vấn)
> - Xu hướng số lượng TBMT theo tháng (tăng/giảm)
>
> **Cần làm**:
> - Script: `msc_market_report.py`
> - Cron: chạy cuối tuần
> - Dùng API counts + search đã có

#### 10. 🏥 **Chuyên sâu ngành Y tế — Theo dõi thuốc & vật tư**
> **Vấn đề**: Bạn có 7 tab tra cứu giá thuốc/vật tư (Generic, Biệt dược gốc, Dược liệu, Vị thuốc...) nhưng chưa tận dụng hết.
>
> **Giải pháp**: Tạo tool "MSC Pharma Watch":
> - Theo dõi biến động giá 1 loại thuốc qua các kỳ đấu thầu
> - Alert khi giá trúng thầu bất thường (cao/thấp so với trung bình)
> - So sánh giá trúng thầu cùng hoạt chất giữa các tỉnh
>
> **Cần làm**:
> - Script: `msc_pharma_watch.py`
> - Database: lưu lịch sử giá theo thời gian

---

## 🗺️ Bản đồ API Endpoints đã khám phá

```
muasamcong.mpi.gov.vn
├── /o/egp-portal-contractor-selection-v2/services/
│   ├── smart/search                          ← Tìm TBMT, KHLCNT, IB, PL
│   ├── expose/lcnt/
│   │   ├── bid-po-bido-notify-contractor-view/get-by-id  ← Chi tiết TBMT
│   │   └── bid-po-bidp-plan-project-view/get-by-id       ← Chi tiết KHLCNT
│   ├── exposeldtkqmt/bid-notification-p/notify            ← Biên bản mở thầu
│   ├── expose/ldtkqmt/bid-notification-p/
│   │   ├── roundmng                          ← Vòng đấu thầu
│   │   ├── bid-open                          ← Mở thầu
│   │   ├── lot-open                          ← Mở lot
│   │   └── lotOpenDetail                     ← Chi tiết lot
│   ├── expose/contractor-input-result/
│   │   ├── get                               ← Kết quả LCNT
│   │   └── get-by-bid-id                     ← KQLCNT theo bid
│   └── lcnt/bid-po-bidp-plan-project-view/
│       └── get-bidp-plan-detail-by-id        ← Chi tiết gói trong KHLCNT
├── /o/egp-portal-personal-page/services/
│   └── smart/search_prc                      ← Tra cứu giá trúng thầu (7 tabs)
└── /o/egp-portal-bid-solicitor-approved/services/
    └── um/lookup-orgInfo                     ← Tra đơn vị (không cần token)
```

---

## ⚡ Đề xuất triển khai nhanh (Quick Wins)

Nếu bạn muốn bắt tay ngay, đây là 3 tính năng **dễ nhất** vì dữ liệu đã có sẵn:

| Ưu tiên | Tính năng | Effort | Giá trị |
|---------|-----------|--------|---------|
| ⭐⭐⭐ | Deadline Alert (hết hạn < 48h) | ~2h | Không bỏ lỡ cơ hội thầu |
| ⭐⭐⭐ | Price Benchmark (so sánh giá) | ~3h | Ra quyết định giá chính xác hơn |
| ⭐⭐ | Keyword Watch (theo dõi theo từ khóa) | ~3h | Mở rộng tầm quan sát |
