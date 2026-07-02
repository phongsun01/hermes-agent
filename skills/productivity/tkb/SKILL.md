---
name: tkb
description: "Quản lý Thời khóa biểu (TKB) gia đình từ Google Sheet hoặc Notion."
version: 1.0.0
author: Nous Research
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Timetable, Schedule, TKB, Productivity, Family]
    config:
      - key: tkb.google_sheet_url
        description: Link Google Sheet chứa thời khóa biểu gia đình (đã chia sẻ xem công khai)
        default: ""
      - key: tkb.notion_database_id
        description: ID Notion Database chứa thời khóa biểu
        default: ""
      - key: tkb.notion_token
        description: Token Notion API
        default: ""
      - key: tkb.timezone
        description: Múi giờ sử dụng để tính toán ngày hôm nay
        default: "Asia/Ho_Chi_Minh"
---

# Thời khóa biểu (TKB) Gia đình

Skill này cho phép Hermes tự động truy vấn và trình bày thời khóa biểu của các thành viên trong gia đình bạn từ Google Sheets hoặc Notion Database.

## Các lệnh hỗ trợ

Khi người dùng chạy lệnh slash, Hermes sẽ gọi tool `get_tkb` để lấy lịch trình:

1. **/tkb today** (hoặc gõ `/tkb` không tham số):
   - Truy vấn lịch trình của hôm nay.
   - Gọi `get_tkb(query_type="today")`.
   - Trình bày một cách thân thiện và ấm áp lịch trình ngày hôm nay của từng thành viên trong gia đình. Nhắc nhở các việc quan trọng (ví dụ mang giày, mang mũ...).

2. **/tkb tomorrow**:
   - Truy vấn lịch trình của ngày mai.
   - Gọi `get_tkb(query_type="tomorrow")`.
   - Trình bày một cách thân thiện lịch trình ngày mai để chuẩn bị trước.

3. **/tkb week**:
   - Truy vấn lịch trình cho toàn bộ tuần này.
   - Gọi `get_tkb(query_type="week")`.
   - Gom nhóm lịch trình theo từng ngày (Thứ 2 -> Chủ Nhật) và hiển thị danh sách các việc cần làm rõ ràng.

4. **/tkb month**:
   - Truy vấn lịch trình đặc biệt của tháng hiện tại.
   - Gọi `get_tkb(query_type="month")`.
   - **Lưu ý**: Lệnh này chỉ hiển thị lịch lặp lại hàng tháng, hàng quý và các sự kiện một lần trong tháng này (không lặp lại lịch hàng tuần 4-5 lần để tránh quá tải tin nhắn).

## Hướng dẫn cho Agent (Hermes)

- Khi người dùng chạy lệnh thời khóa biểu, hãy luôn gọi tool `get_tkb` trước tiên với `query_type` phù hợp.
- Trình bày kết quả bằng tiếng Việt, định dạng Markdown đẹp mắt (sử dụng bảng hoặc danh sách bullet point phân tách rõ ràng theo từng thành viên như Bống, Bi, Bố, Mẹ...).
- Sử dụng giọng điệu gia đình ấm áp, vui vẻ và chu đáo. Nhấn mạnh vào thời gian, địa điểm và phần "Ghi chú" nếu có.
- Nếu tool trả về lỗi liên quan đến Google Sheet (ví dụ không tải được CSV), hãy hiển thị hướng dẫn chi tiết cách cấu hình quyền xem cho bảng tính.
