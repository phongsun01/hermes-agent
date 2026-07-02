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

---

## 🛠️ 4. Nhật ký Sửa lỗi (Troubleshooting & Debugging)

Trong quá trình triển khai thực tế trên môi trường Docker của Zalo Bot, một số lỗi cấu hình và kẹt cache đã được phát hiện và xử lý:

### Lỗi 1: Zalo Bot không nhìn thấy tool `get_tkb`
* **Triệu chứng:** Bot Zalo nhận diện được Skill TKB nhưng báo rằng không tìm thấy tool `get_tkb` trên hệ thống và tự đề xuất viết script python để thay thế.
* **Nguyên nhân:** File `config.yaml` của môi trường Zalo giới hạn danh sách các công cụ được phép chạy (`platform_toolsets.zalo`). Do toolset `tkb` chưa được khai báo tại đây, Agent chạy trên Zalo bị ẩn đi tool `get_tkb`.
* **Cách sửa:** Thêm `- tkb` vào cấu hình platform trong `config.yaml`:
  ```yaml
  platform_toolsets:
    zalo:
      - hermes-cli
      - xsmb
      - tkb # Cấp quyền cho Zalo chạy tool get_tkb
  ```

### Lỗi 2: Gateway cũ chạy ngầm giữ cache bộ nhớ
* **Triệu chứng:** Dù đã sửa file Python trên host và chạy lệnh restart docker container, Zalo Bot vẫn hoạt động theo code cũ và báo thiếu tool.
* **Nguyên nhân:** Docker container chạy hệ quản trị tiến trình `s6-supervisor`. Lệnh `docker restart` đôi khi không kill sạch được các background gateway instance cũ đang giữ khóa lock hoặc cache bộ nhớ (ví dụ: PID 157).
* **Cách sửa:** Chạy trực tiếp lệnh khởi động lại tiến trình gateway bên trong container:
  ```bash
  docker exec hermes hermes gateway restart
  ```

### Lỗi 3: Kẹt lịch sử hội thoại cũ (Conversation Context)
* **Triệu chứng:** Khi đổi code và phân quyền xong, bot vẫn báo thiếu tool.
* **Nguyên nhân:** Lịch sử hội thoại trong cơ sở dữ liệu `state.db` của phiên chat hiện tại đang lưu giữ câu trả lời trước đó (rằng không có tool). Do đó, Agent tiếp tục suy luận dựa trên ngữ cảnh lỗi cũ.
* **Cách sửa:**
  1. Gửi lệnh `@Hermes /new` hoặc `@Hermes /clear` vào khung chat Zalo để làm mới phiên chat.
  2. (Nếu cần cưỡng chế xóa từ database): Chạy lệnh Python kết nối SQLite để đóng các session Zalo đang hoạt động:
     ```python
     UPDATE sessions SET ended_at = ?, end_reason = 'manual_reset' WHERE source = 'zalo' AND ended_at IS NULL
     ```

