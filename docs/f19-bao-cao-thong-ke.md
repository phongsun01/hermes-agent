# F19 — Báo cáo thống kê định kỳ công văn đến

> **Trạng thái:** ✅ Đã triển khai | **Cập nhật:** 2026-06-22 16:00 ICT
> **Script:** `scripts/congchuc/congchuc_report.py`
> **Cron:** `a1b2c3d4e5f6` (báo cáo tuần), `b2c3d4e5f6a7` (export Excel)

---

## 1. Mục tiêu

- Tự động tổng hợp số liệu xử lý công văn đến định kỳ (tuần/tháng)
- Gửi báo cáo trực tiếp qua Zalo cho người dùng
- Hỗ trợ export Excel để lưu trữ và báo cáo offline

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Cron Scheduler (Hermes gateway)              │
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────────┐  │
│  │ a1b2c3d4e5f6         │  │ b2c3d4e5f6a7            │  │
│  │ 17h thứ 6 (VN)       │  │ 17h05 thứ 6 (VN)        │  │
│  │ congchuc_report.py   │  │ congchuc_report.py      │  │
│  │ --weekly             │  │ --excel                 │  │
│  │ no_agent + deliver   │  │ no_agent + deliver      │  │
│  └──────────┬───────────┘  └──────────┬───────────────┘  │
│             │                         │                   │
└─────────────┼─────────────────────────┼───────────────────┘
              │                         │
              ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    stdout → Zalo         │  │    stdout → Zalo         │
│  (báo cáo text)          │  │  (xác nhận + path file)  │
│                          │  │                          │
│  Output:                 │  │  Output:                 │
│  📊 Báo cáo tuần ...     │  │  ✅ Đã xuất Excel: ...   │
│  📋 Tổng VB: 47          │  │                          │
│  ✅ Đã xử lý: 41 (87%)   │  │  File lưu tại:           │
│  🔥 VB khẩn: 7           │  │  exports/cong-van-den_  │
│  📌 Chưa xử lý: ...      │  │   2026-W26.xlsx          │
└──────────────────────────┘  └──────────────────────────┘
```

### Data source

- **State file:** `/opt/data/cron/cong-van-den/vbden_state.json`
- Documents dict: lưu chi tiết từng VB (kể từ bản update `first_seen`)
- Status tracking: `done`/`wip`/`read`/`new` (từ `congvan_status.py`)
- Seen IDs: tổng số VB đã từng phát hiện

---

## 3. Current implementation

### Script: `congchuc_report.py`

| Mode | Flag | Output | Cron |
|------|------|--------|------|
| Báo cáo tuần | `--weekly` | Text → Zalo | `a1b2c3d4e5f6` |
| Báo cáo tháng | `--monthly` | Text → stdout | Chưa có cron |
| Export Excel | `--excel` | `.xlsx` file + confirm | `b2c3d4e5f6a7` |

### weekly report structure

```
📊 Báo cáo tuần 15/06-22/06/2026
────────────────────────────────
📋 Tổng VB theo dõi: 44
🆕 Mới trong kỳ: 3
✅ Đã xử lý (done): 41 (87%)
⏳ Đang xử lý: 4
👁️ Đã đọc: 2
🔥 Văn bản khẩn: 7
🔗 https://congchuc.quangninh.gov.vn/Default.aspx?tabid=1126

📌 VB chưa xử lý (new):
  🔴 #2454 274/KH-UBND: KH Triển khai Chiến lược...
    #2405 1292/TTKSBT-TTGDSK: Công văn giải trình...
```

### Excel export columns (13 columns)

| # | Column | Source |
|---|--------|--------|
| 1 | STT | Auto |
| 2 | Số đến | `doc.so_den` |
| 3 | Ngày VB | `doc.ngay_vb` |
| 4 | Ngày đến | `doc.ngay_den` |
| 5 | Số/Ký hiệu | `doc.so_ky_hieu` |
| 6 | Tác giả | `doc.tac_gia` |
| 7 | Trích yếu | `doc.trich_yeu` |
| 8 | Độ khẩn | `get_urgency(doc)` |
| 9 | Trạng thái | `doc.status` |
| 10 | Cập nhật | `doc.status_updated_at` |
| 11 | Ghi chú | `doc.note` |
| 12 | Bút phê | `doc.but_phe` |
| 13 | File đính kèm | `state.documents[id].attachments[].display_name` |

### Excel features

- Header: xanh đậm (`#4472C4`), chữ trắng, bold
- Auto-filter trên toàn bộ columns
- Freeze panes: dòng header luôn visible
- VB `done`: in nghiêng, màu xám (`#808080`)
- Wrap text cho cell dài
- Filename: `cong-van-den_YYYY-WW.xlsx` (theo ISO week)

---

## 4. Cron jobs

### Weekly report (`a1b2c3d4e5f6`)

```json
{
  "id": "a1b2c3d4e5f6",
  "name": "Bao cao tuan cong van den",
  "schedule": "0 10 * * 5",
  "schedule_display": "0 10 * * 5 (17h VN thu 6)",
  "script": "congchuc/congchuc_report_weekly.sh",
  "no_agent": true,
  "deliver": "zalo"
}
```

→ `17h thứ 6 hàng tuần` (giờ VN)

### Excel export (`b2c3d4e5f6a7`)

```json
{
  "id": "b2c3d4e5f6a7",
  "name": "Export Excel cong van den",
  "schedule": "5 10 * * 5",
  "schedule_display": "5 10 * * 5 (17h05 VN thu 6)",
  "script": "congchuc/congchuc_report_excel.sh",
  "no_agent": true,
  "deliver": "zalo"
}
```

→ `17h05 thứ 6 hàng tuần` (sau báo cáo 5 phút)

---

## 5. Deployment

```bash
# Deploy scripts
docker cp .../congchuc_report.py hermes:/opt/data/scripts/congchuc/
docker cp .../congchuc_report_weekly.sh hermes:/opt/data/scripts/congchuc/
docker cp .../congchuc_report_excel.sh hermes:/opt/data/scripts/congchuc/

# Ensure openpyxl
docker exec hermes uv pip install openpyxl
```

---

## 6. Known issues & gaps

### 🟡 Đã biết

| # | Vấn đề | Tác động | Fix plan |
|---|--------|----------|----------|
| 1 | `first_seen` không có cho VB cũ (trước khi update state save) | weekly/monthly "Mới trong kỳ" = 0 cho historical data | Tự động fix khi VB mới xuất hiện; không retroactive |
| 2 | `--monthly` chưa có cron job | Chỉ chạy manual | Thêm cron job `0 1 * *` (08h01 VN ngày 1 hàng tháng) |
| 3 | Excel export không phân biệt được unit | Nếu multi-unit, Excel gộp tất cả không tag unit | TODO: thêm column "Đơn vị" |
| 4 | Weekly report luôn chạy kể cả khi không có VB mới trong tuần | Trống "📌 VB chưa xử lý" section nếu tất cả đã done | Vẫn OK — useful để confirm mọi thứ đã xong |
| 5 | Overdue detection chưa có | `overdue` count luôn 0 | Cần thêm cron job scan `status_updated_at` > N ngày |

### 🔴 Cần cải thiện

1. **Overdue auto-detect:**
   - Thêm cron job `congchuc_report.py --check-overdue`
   - Scan VB `status=new` hoặc `read` quá 7 ngày (configurable)
   - Tự set `status=overdue` + gửi Zalo cảnh báo

2. **Multi-unit support trong Excel:**
   - State hiện không track unit cho mỗi VB
   - Cần thêm field `unit` hoặc dựa vào `tac_gia` để phân loại
   - Giải pháp: thêm column "Đơn vị" trong Excel, có thể để trống nếu single-unit

3. **Monthly cron:**
   - Thêm wrapper `congchuc_report_monthly.sh`
   - Cron job schedule `0 1 * *` (08h01 VN ngày 1)
   - Thêm vào `deploy_congchuc.ps1`

4. **Report gửi kèm Excel:**
   - Khi `--excel` chạy, gửi đường dẫn file + summary ngắn
   - Hoặc gửi Excel qua Zalo (nếu adapter hỗ trợ file attachment)

---

## 7. Testing

```bash
# Manual test
docker exec hermes python3 /opt/data/scripts/congchuc/congchuc_report.py --weekly
docker exec hermes python3 /opt/data/scripts/congchuc/congchuc_report.py --monthly
docker exec hermes python3 /opt/data/scripts/congchuc/congchuc_report.py --excel

# Wrapper scripts
docker exec hermes /opt/data/scripts/congchuc/congchuc_report_weekly.sh
docker exec hermes /opt/data/scripts/congchuc/congchuc_report_excel.sh

# Check output Excel
docker exec hermes ls -la /opt/data/cron/cong-van-den/exports/
```

---

## 8. Future enhancements

| Tính năng | Priority | Complexity | Notes |
|-----------|----------|------------|-------|
| Overdue auto-detect | Medium | Medium | Scan + auto status update |
| Monthly cron job | Medium | Low | Wrapper + cron entry |
| Excel multi-unit column | Medium | Low | Cần state field mới |
| Excel conditional formatting | Low | Low | Color rows by status |
| Trend chart (weekly VB count) | Low | Medium | Cross-period comparison |
| Zalo attachment delivery | Low | High | Phụ thuộc Zalo adapter capability |
| Dashboard web embed | Low | Medium | Reuse `--excel` data |
| Report custom schedule | Low | Low | `.env` config `CONGVAN_REPORT_SCHEDULE` |
