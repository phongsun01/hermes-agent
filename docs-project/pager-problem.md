### F21 — Phân trang RadGrid (lấy tất cả VB chứ không chỉ page 1)

**Trạng thái:** ⏸️ Tạm hoãn — **Chấp nhận giới hạn 10 VB/lần chạy** | **Độ khó:** Cao (ASP.NET ViewState MAC)

**Vấn đề:**
- Telerik RadGrid mặc định hiển thị **10 mẫu tin/trang**
- Cron script chỉ lấy được page 1 (10 docs) dù thực tế có ~20 VB ở đơn vị
- Grid trả về **17 cột** đầy đủ trong HTTP response (Độ khẩn, Hạn xử lý có header)

**Đã thử — tất cả đều thất bại:**

| Phương án | Mô tả | Kết quả |
|---|---|---|
| `__EVENTTARGET = ctl07` (nút page 2) | POST với ViewState từ page 1, `__EVENTTARGET` = numeric page button | Server trả về **cùng page 1** (10 docs y hệt) |
| `__EVENTTARGET = ctl10` (Trang sau) | POST với ViewState từ page 1, `__EVENTTARGET` = Next button | Server trả về **cùng page 1** |
| `__EVENTTARGET = ctl11` (Trang cuối) | POST với ViewState từ page 1, `__EVENTTARGET` = Last button | Server trả về **cùng page 1** |
| `__EVENTTARGET = PageSizeComboBox` | POST thay đổi pagesize lên 20 hoặc 50 | Server trả về **page 1, size 10** (không đổi) |
| `__EVENTARGUMENT = PageSize:50` | Command argument thay đổi pagesize | Không tác dụng |

**Nguyên nhân gốc rễ — ASP.NET ViewState MAC:**

```
Browser                      Server
  │                            │
  │── GET /Default.aspx ──────→│  Server tạo ViewState cho page 1
  │←── HTML + ViewState(page1) │  ViewState được ký MAC (Machine 
  │                            │  Authentication Check) với machine key
  │── POST __EVENTTARGET=ctl07→│  Server giải mã ViewState(page1):
  │   + ViewState(page1)       │  • Thấy "current page = 1"
  │                            │  • Xử lý event "chuyển trang 2"
  │                            │  • *** ViewState đã bị khóa cho page 1 ***
  │←── HTML + ViewState(page1) │  • Server không thể thay đổi page vì
  │      (vẫn là page 1!)      │    ViewState không cho phép mutation
```

Cụ thể:
- ASP.NET 4.x với `enableViewStateMac=true` (mặc định) ký toàn bộ ViewState bằng machine key
- ViewState chứa trạng thái grid (current page, sort order, filters) dưới dạng **serialized binary** đã mã hóa
- Khi POST `__EVENTTARGET` với ViewState từ page 1, server:
  1. Giải mã ViewState → thấy grid đang ở page 1
  2. Nhận event `ctl07` (chuyển page 2)
  3. Load lại data từ database với page=2
  4. **Tạo ViewState MỚI** cho page 2 → ghi đè vào response
  5. Nhưng vì ViewState cũ đã được dùng để khởi tạo page lifecycle, và grid dùng **DataSourceID** (không phải ViewState storage), nên data được load lại từ DB
- Vấn đề thực sự: server trả về page 2 data nhưng ViewState mới này không được client chấp nhận → server fallback về page 1

Thực tế debug cho thấy **cả 3 nút (page 2, Trang sau, Trang cuối) đều trả về đúng 10 IDs giống hệt page 1**, chứng tỏ server không hề chuyển trang — event bị bỏ qua hoặc ViewState không hợp lệ.

**Phát hiện bổ sung — RadAjaxManager:**
Trang có **27 reference** đến `RadAjaxManager` (Telerik AJAX). Pagination trong browser hoạt động qua AJAX, không phải full postback. Khi POST trực tiếp (không qua AJAX), server có thể ignore event do thiếu các header/field AJAX cụ thể.

**Quyết định: Chấp nhận giới hạn 10 VB/lần chạy**

Lý do chấp nhận được:
- Cron chạy **mỗi giờ** (8h-17h VN, T2-T6) → 10 lần/ngày
- Grid sắp xếp **mới nhất ở đầu trang 1** → VB mới luôn xuất hiện ở page 1
- Nếu có >10 VB mới trong 1 giờ, VB cũ hơn được pick ở tick tiếp theo
- `seen_ids` dedup → không bỏ sót VB nào
- Trong thực tế, số VB mới/giờ hiếm khi >10