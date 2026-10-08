# Bài giới thiệu CC Skill (dùng để quảng cáo)

*Được refine từ phiên 2026-06-30 — các lưu ý của sếp đã được tích hợp.*

---

**🤖 TRỢ LÝ CÔNG VĂN TỰ ĐỘNG — CC SKILL**

**Tích hợp với cổng congchuc.quangninh.gov.vn** — xử lý văn bản ngay trên Zalo/Telegram.

---

📨 **Tự động quét & thông báo** VB đến, VB đi mới — tùy chỉnh tần suất (mặc định mỗi giờ, có thể 5 phút/lần nhưng tốn phí AI hơn)

✅ **Kết thúc văn bản**: `/cc end <số>` hoặc kết thúc hàng loạt `/cc end all`
🤖 **Tự động kết thúc** các văn bản dạng Thông báo/Để biết — không cần thao tác tay
📄 **Tóm tắt nội dung**: `/cc tomtat <số>` — AI tóm gọn mục đích, deadline, đề xuất xử lý
📎 **Tải file đính kèm**: `/cc tai <số>` — PDF/DOCX tự động
✍️ **Soạn dự thảo góp ý**: `/cc duthao <số>` — xuất file Word gửi qua Zalo
🏷️ **Phân loại khẩn/thường**, gắn tag, phát hiện trùng lặp VB
🔔 **Nhắc lịch họp**, kiểm tra quá hạn xử lý

---

📲 **Nền tảng hỗ trợ:**
- Zalo: phổ biến, tiện nhận thông báo nhanh
- Telegram: gửi file tốt hơn, log dài không bị giới hạn

⚙️ **Cấu hình tối thiểu:**
- Windows 10/11 (có WSL2)
- RAM ≥ 8GB (khuyến nghị 16GB)
- 1 tài khoản AI Pro (Gemini Pro hoặc OpenAI) — ~600-800K/tháng
- Chạy 24/7 qua Docker, auto khởi động cùng máy

📦 **Hệ thống chạy nền liên tục:**
- Cài qua Docker trên Windows (Docker Desktop + WSL2)
- Cron job quét tự động, gửi thông báo trực tiếp
- Máy tính để bàn chạy 24/7 là đủ — không cần VPS
- Tiết kiệm ~80% thời gian xử lý công văn hàng ngày

🍺 **Chi phí cài đặt:**
- 1 bữa bia — cài xong dùng được ngay

---

👨‍💻 *Build by Nguyễn Huy Phong — Bệnh viện Sản-Nhi Quảng Ninh*
📲 *Hỗ trợ Zalo + Telegram*
