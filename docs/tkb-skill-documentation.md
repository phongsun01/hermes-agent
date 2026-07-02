# Hướng dẫn sử dụng & Tài liệu kỹ thuật Skill Thời khóa biểu (TKB)

Tài liệu này ghi lại các chức năng, hướng dẫn sử dụng, cấu hình và danh sách các file liên quan đến Skill **Thời khóa biểu (TKB) Gia đình** trong hệ thống Hermes Agent.

---

## 📅 1. Giới thiệu chức năng

Hệ thống TKB cho phép Hermes đọc và quản lý thời khóa biểu của từng thành viên trong gia đình từ một bảng dữ liệu trực tuyến (Google Sheets hoặc Notion Database).
- **Lọc theo ngữ cảnh**: Hệ thống tự động lọc và gom nhóm các sự kiện theo ngày hoặc theo thành viên gia đình (ví dụ: Bống, Bi, Bố, Mẹ, Cả nhà).
- **Hỗ trợ đa dạng tần suất lặp**:
  - Hàng tuần (Thứ 2 đến Chủ Nhật).
  - Hàng tháng (Theo số ngày cụ thể, ví dụ: Ngày 5, Ngày 15).
  - Hàng quý (Mốc đầu quý, cuối quý, hoặc ngày cụ thể trong các tháng của quý).
  - Một lần (Ngày cụ thể định dạng YYYY-MM-DD hoặc DD-MM-YYYY).
- **Tự động báo cáo (Cron)**: Tích hợp sẵn việc tự động nhắc lịch hàng ngày (2 lần) và báo lịch tuần vào mỗi sáng Thứ Hai đầu tuần.

---

## 🛠️ 2. Các file liên quan trong Source Code

Hệ thống được phát triển tích hợp sâu vào Hermes thông qua các file sau:

1. **Công cụ lõi (Core Tool)**:
   - [tools/tkb_tool.py](file:///d:/Antigravity/Hermes/tools/tkb_tool.py): Nơi thực hiện toàn bộ logic kết nối API (Google Sheets CSV, Notion API), parser phân tích cột "Thứ / Ngày", hàm lọc dữ liệu theo ngày/tuần/tháng, và hàm đăng ký cron tự động.
2. **Khai báo Toolset**:
   - [toolsets.py](file:///d:/Antigravity/Hermes/toolsets.py): Đăng ký công cụ `"get_tkb"` vào danh sách công cụ lõi `_HERMES_CORE_TOOLS` để đảm bảo Agent có thể truy cập trên mọi nền tảng chat.
3. **Cấu hình mặc định**:
   - [hermes_cli/config.py](file:///d:/Antigravity/Hermes/hermes_cli/config.py): Khai báo cấu trúc cài đặt mặc định cho `tkb` trong `DEFAULT_CONFIG`.
4. **Hook Khởi động**:
   - [tools/skills_sync.py](file:///d:/Antigravity/Hermes/tools/skills_sync.py): Thực hiện gọi hàm `auto_register_tkb_cron()` để tự động đăng ký/cập nhật cron jobs khi CLI/Gateway khởi động.
5. **Skill Hướng dẫn cho AI**:
   - [skills/productivity/tkb/SKILL.md](file:///d:/Antigravity/Hermes/skills/productivity/tkb/SKILL.md): Chứa hướng dẫn cấu hình chi tiết và các prompt hệ thống để điều hướng AI trả lời ấm áp, rõ ràng.
6. **Kiểm thử tự động**:
   - [tests/tools/test_tkb_tool.py](file:///d:/Antigravity/Hermes/tests/tools/test_tkb_tool.py): Chứa 7 testcase kiểm thử logic parser và bộ lọc thời gian.

---

## ⚙️ 3. Cấu hình & Sử dụng

### Cấu hình trong `config.yaml`
Bạn có thể cấu hình các thông số sau trong file `~/.hermes/config.yaml`:

```yaml
tkb:
  google_sheet_url: "LINK_GOOGLE_SHEET_CỦA_BẠN"  # Link xem công khai
  timezone: "Asia/Ho_Chi_Minh"                   # Múi giờ Việt Nam
  cron:
    enabled: true
    daily_morning_report: "06:00"                # Giờ báo lịch hôm nay
    daily_evening_report: "21:00"                # Giờ báo trước lịch ngày mai
    weekly_report: "Mon 07:00"                   # Báo lịch tuần sáng Thứ Hai
    deliver: "zalo"                              # Nền tảng nhận thông báo (zalo, telegram, local)
```

### Các lệnh tương tác trực tiếp
- `/tkb today` (hoặc `/tkb`): Báo cáo công việc của hôm nay.
- `/tkb tomorrow`: Báo trước lịch trình ngày mai.
- `/tkb week`: Xem toàn bộ lịch học tập/làm việc trong tuần này.
- `/tkb month`: Xem các sự kiện đặc biệt của tháng này (lịch lặp lại hàng tháng, hàng quý và sự kiện một lần, loại bỏ lịch tuần để tránh trùng lặp thông tin).
