# Kế hoạch Triển khai Skill `obs` - Tích hợp Obsidian (Second Brain) cho Hermes Agent

Tài liệu này lưu trữ kế hoạch và thiết kế chi tiết cho Skill `obs` nhằm kết nối an toàn kho dữ liệu Obsidian (Second Brain) cục bộ với Hermes Agent.

---

## 1. Cơ chế Bảo mật (Security Guardrails)
* **Cô lập môi trường (Sandbox):** Kích hoạt `terminal.home_mode: profile` trong tệp cấu hình profile để tránh các tiến trình con truy cập vào thư mục gốc `HOME` của người dùng hệ điều hành.
* **Hạn chế đường dẫn (CWD):** Giới hạn hoạt động mặc định của terminal con trong phạm vi thư mục Obsidian Vault và các thư mục tạm.

---

## 2. Giao diện Lệnh (Slash Commands /obs)
* `/obs search <query>`: Tìm kiếm ghi chú sử dụng ripgrep cục bộ.
* `/obs view <tên ghi chú>`: Đọc và hiển thị nội dung tệp tin ở chế độ chỉ đọc.
* `/obs append <tên ghi chú>`: Chèn thêm thông tin vào cuối tệp tin kèm mốc thời gian (an toàn, không ảnh hưởng dữ liệu cũ).
* `/obs write <tên ghi chú>`: Ghi đè tệp tin an toàn (bắt buộc tạo backup và kiểm tra tính toàn vẹn trước khi ghi).
* `/obs check-expiry`: Quét và phát hiện các giấy tờ sắp hết hạn trong Obsidian Vault.

---

## 3. Cơ chế Ghi đè An toàn (Safe Write)
Khi ghi đè tệp với `/obs write`, tiến trình sẽ:
1. Tạo một bản sao lưu (backup) của tệp gốc tại `.obsidian/hermes-backups/`.
2. Kiểm tra tính toàn vẹn: Nếu dung lượng mới giảm đột ngột (dưới 50% số dòng so với tệp cũ), hệ thống sẽ yêu cầu người dùng xác nhận rõ ràng trước khi lưu.

---

## 4. Cơ chế Nhắc nhở Tự động (Natural-language Cron)
Sử dụng tính năng nhắc nhở tự nhiên `/schedule` của Hermes để đăng ký lịch quét định kỳ.
Ví dụ: *"Quét tệp 'Giấy tờ cá nhân.md' trong Obsidian vào mùng 1 hàng tháng để nhắc đổi căn cước sắp hết hạn qua Zalo."*

---

## 5. Cấu trúc Triển khai
Các tệp tin sẽ được tạo tại:
* `skills/obs/SKILL.md`: Định nghĩa kỹ năng và các lệnh slash cho Hermes.
* `skills/obs/scripts/safe_write.py`: Xử lý ghi đè và sao lưu tệp.
* `skills/obs/scripts/check_expiry.py`: Xử lý quét hạn dùng giấy tờ từ YAML Frontmatter.

Kết quả Triển khai Kỹ năng obs & Menu Tương tác obsmenu
Tôi đã tích hợp thành công giao diện nút bấm tương tác (Inline Keyboard Menu) cho Skill obs thông qua lệnh mới /obsmenu.

Các tệp tin đã cập nhật & triển khai mới
Đăng ký lệnh CLI / Gateway:
Cập nhật: 
hermes_cli/commands.py
 (Đăng ký lệnh obsmenu cho danh mục "Tools & Skills").
Triển khai Menu tương tác trên Telegram Gateway:
Cập nhật: 
gateway/platforms/telegram.py
:
Chặn lệnh (Intercept): Chặn lệnh /obsmenu để hiển thị menu tương tác Obsidian gồm các nút: Tìm kiếm ghi chú, Quét hạn giấy tờ, Xem personal.md, và Refresh.
Xử lý Callback (hx:obs:...): Khi người dùng click nút, gateway sẽ tự chạy các script Python tương ứng (check_expiry.py, đọc file, hoặc list file) dưới nền và chỉnh sửa cập nhật nội dung tin nhắn tương ứng một cách mượt mà.
Obsidian Vault Note:
Cập nhật: 
personal.md
 (Ghi nhận thông tin CCCD của mọi người kèm GPLX của sếp Phong).
Hướng dẫn sử dụng nhanh trên Telegram / Zalo
Gõ lệnh: /obsmenu
Hệ thống sẽ hiển thị menu:
text

🧠 OBSIDIAN SECOND BRAIN
Chọn chức năng quản lý tri thức và giấy tờ bên dưới:
[🔍 Tìm kiếm ghi chú]
[📅 Quét hạn giấy tờ]
[📄 Xem tệp personal.md]
[🔄 Refresh / Menu chính]
Bấm [📅 Quét hạn giấy tờ] -> Menu tự động đổi thành kết quả kiểm tra thời hạn (CCCD/GPLX) ngay lập tức.