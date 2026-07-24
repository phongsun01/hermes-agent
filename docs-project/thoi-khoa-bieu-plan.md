Kế hoạch - Skill & Tool Thời khóa biểu (TKB) cho Hermes
Chúng ta sẽ triển khai hệ thống Thời khóa biểu (TKB) cho Hermes giúp bạn và các thành viên trong gia đình theo dõi lịch trình hàng ngày, hàng tuần và hàng tháng. Dữ liệu thời khóa biểu có thể được cấu hình để đọc từ Google Sheets (dưới dạng xuất CSV) hoặc Notion Database.

Yêu cầu người dùng xem xét (User Review Required)
IMPORTANT

Cấu hình Google Sheet: Để dùng Google Sheets, bạn cần chia sẻ bảng tính ở chế độ "Bất kỳ ai có liên kết đều có thể xem" (Anyone with link can view) và cung cấp URL của bảng tính.
Cấu hình Notion: Để dùng Notion, bạn cần cung cấp Notion Integration Token và Notion Database ID (và chia sẻ database đó với tích hợp Notion của bạn).
Cấu hình hệ thống: Chúng ta sẽ thêm các khóa cấu hình vào file config.yaml dưới mục tkb (ví dụ: tkb.google_sheet_url, tkb.notion_database_id, tkb.notion_token, v.v.).
Cấu trúc Bảng Thời khóa biểu mẫu (Google Sheets / Notion)
Để Hermes đọc dữ liệu chính xác, bảng dữ liệu của bạn nên có các cột sau:

Thứ / Ngày	Thời gian	Thành viên	Hoạt động / Công việc	Lặp lại	Ghi chú
Thứ 2	07:30 - 08:00	Bố	Đưa con đi học	Hàng tuần	Tránh đường tắc
Thứ 2	08:30 - 11:30	Mẹ	Họp giao ban đầu tuần	Hàng tuần	Trực tuyến
2026-07-06	19:30 - 21:00	Cả nhà	Đi ăn tối cùng ông bà	Một lần	Đặt bàn trước
Ngày 5	09:00 - 10:00	Bố	Thanh toán tiền điện nước	Hàng tháng	Qua ứng dụng ngân hàng
Đầu quý	Cả ngày	Cả nhà	Bảo dưỡng định kỳ xe ô tô	Hàng quý	Lần tiếp theo: đầu tháng 7
Quy tắc ghi cho các tác vụ lặp lại (Thứ / Ngày & Lặp lại):
Lặp lại Hàng tuần:
Cột Thứ / Ngày: Ghi thứ trong tuần (ví dụ: Thứ 2, Thứ 3, ..., Chủ Nhật).
Cột Lặp lại: Ghi Hàng tuần.
Lặp lại Hàng tháng:
Cột Thứ / Ngày: Ghi số ngày cụ thể (ví dụ: Ngày 5, Ngày 15, Ngày 30, hoặc chỉ cần số 5, 15).
Cột Lặp lại: Ghi Hàng tháng. Hermes sẽ tự động báo việc này khi đến ngày đó trong bất kỳ tháng nào.
Lặp lại Hàng quý:
Cột Thứ / Ngày: Ghi mốc thời gian trong quý (ví dụ: Đầu quý, Cuối quý, Ngày 1, Ngày 15).
Cột Lặp lại: Ghi Hàng quý. Hermes sẽ tự động tính toán các mốc đầu quý (Tháng 1, 4, 7, 10) để báo lịch.
Một lần:
Cột Thứ / Ngày: Ghi ngày cụ thể dạng YYYY-MM-DD (ví dụ: 2026-07-06).
Cột Lặp lại: Để trống hoặc ghi Một lần.
Thời gian: Khoảng thời gian cụ thể (ví dụ: 08:00, 14:00 - 16:00) hoặc Cả ngày.
Thành viên: Tên người thực hiện (để Hermes có thể báo riêng cho từng người hoặc cả nhà).
Hoạt động / Công việc: Nội dung chi tiết cần làm.
Ghi chú: Thông tin bổ sung (không bắt buộc).
Các thay đổi đề xuất
1. Công cụ lõi (Core Tool)
Chúng ta sẽ triển khai một tool core mang tên get_tkb trong file tools/tkb_tool.py để truy xuất và định dạng dữ liệu lịch trình. Điều này giúp việc chạy tool an toàn trên tất cả các nền tảng (Zalo, Telegram, CLI) mà không cần quyền chạy lệnh terminal trực tiếp.

[NEW] 
tkb_tool.py
Lấy lịch trình từ Google Sheets (qua URL xuất CSV) hoặc Notion Database (qua HTTP API).
Hỗ trợ lọc theo ngày/thứ (hôm nay, tuần này, tháng này).
Nhận diện các thứ trong tuần bằng cả tiếng Việt (Thứ 2, Thứ 3, ..., Chủ Nhật) và tiếng Anh (Monday, Tuesday, v.v.).
Đăng ký tool get_tkb trong toolset "tkb".
[MODIFY] 
toolsets.py
Đăng ký toolset "tkb" vào danh sách _HERMES_CORE_TOOLS để tự động kích hoạt cho agent.
2. Cấu hình và Schema
[MODIFY] 
hermes_cli/config.py
Định nghĩa các khóa cấu hình cho mục tkb trong DEFAULT_CONFIG với giá trị mặc định là trống để hệ thống nhận diện và tự động gộp cấu hình.
3. Định nghĩa Skill
[NEW] 
SKILL.md
Định nghĩa skill frontmatter với name tkb và mô tả tiếng Việt.
Khai báo các biến cấu hình để tự động tiêm vào ngữ cảnh của skill.
Hướng dẫn agent cách sử dụng tool get_tkb để lấy lịch trình và trình bày cho người dùng một cách sinh động, ấm áp theo phong cách gia đình.
Hướng dẫn chi tiết cách xử lý khi người dùng chạy các lệnh slash /tkb today, /tkb week, /tkb month.
4. Hướng dẫn thiết lập tự động báo cáo (Cron)
Chúng ta sẽ cung cấp câu lệnh để bạn thiết lập:

Báo cáo hàng ngày: Chạy /tkb today mỗi sáng (ví dụ: 07:00).
Báo cáo hàng tuần: Chạy /tkb week vào mỗi sáng Thứ Hai đầu tuần.
Kế hoạch kiểm thử (Verification Plan)
Kiểm thử tự động (Automated Tests)
Viết unit test cho tools/tkb_tool.py kiểm tra logic tải và lọc dữ liệu.
Kiểm thử thủ công (Manual Verification)
Chạy hermes với cấu hình mặc định (default profile).
Gõ thử các lệnh /tkb today, /tkb week, /tkb month và kiểm tra kết quả hiển thị.