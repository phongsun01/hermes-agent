# Kế hoạch & Kết quả tích hợp: Gửi Video qua Zalo & Cinecode cho Hermes Agent

> **Tài liệu tham chiếu:** `docs-project/zalo-integration/`  
> **Thời gian cập nhật:** 11/11/2026  
> **Trạng thái:** Giai đoạn 1 & 2 đã HOÀN THÀNH THÀNH CÔNG (Tested & Verified)

---

## 1. Kết quả thực thi Giai đoạn 1 & Giai đoạn 2

### Giai đoạn 1: Nâng cấp Core Bridge & Adapter Zalo (`hermes-zalo-plugin`)
- [x] **1.1. Nâng giới hạn Payload trên Bridge (`server.js`):**
  - Đã nâng `express.json({ limit: "50mb" })` thay vì `2mb`. Khắc phục triệt để lỗi `413 Payload Too Large` khi gửi video/ảnh kích thước lớn qua Base64.
- [x] **1.2. Chẩn đoán cơ chế gửi tin nhắn Zalo Web:**
  - **Phát hiện quan trọng:** Giao thức Zalo Web không cho phép gửi tin nhắn đính kèm/upload tệp tin tới chính User ID của mình (`toid == ownId`), điều này kích hoạt lỗi `114: Tham số không hợp lệ`. 
  - Khi gửi tới một User/Friend ID hợp lệ (ví dụ: `2825656851207986406`) hoặc Group ID, hàm `uploadAttachment` tự động xử lý chia chunk (chunk size: 3 MB) và hoàn tất upload lên CDN của Zalo hoàn toàn chính xác.
- [x] **1.3. Khởi động lại và kiểm tra Bridge:**
  - Bridge đã được khởi động lại thành công với cấu hình mới (`bootId: c4c2d0db-4465-4aa7-9a34-52dd1c89c86a`, trạng thái `READY`, SQLite đã kết nối).

### Giai đoạn 2: Kiểm thử gửi Video thực tế
- [x] **2.1. Test gửi video mẫu `the-last-walk-10s.mp4` (3.2 MB) qua đường dẫn Local (`path`):**
  - **Kết quả:** `success: true`
  - Message ID: `8475898619001`
  - Attachment ID: `8475898675701`
- [x] **2.2. Test gửi video mẫu qua `Base64` (xác thực `50mb` payload limit):**
  - **Kết quả:** `success: true`
  - Message ID: `8475899153530`
  - Attachment ID: `8475899212766`
- [x] **2.3. Tương thích Hermes Adapter (`~/.hermes/plugins/zalo/adapter.py`):**
  - Hàm `send_video()` trong adapter tự động gọi `send_document()` và gửi qua endpoint `/send-attachment`, cả hai phương thức local path lẫn base64 hiện tại đều đã hoạt động trơn tru.

---

## 2. Kế hoạch tiếp theo: Giai đoạn 3 (Xây dựng Cinecode Skill)

### Mục tiêu:
Biến [sarpstar/cinecode](https://github.com/sarpstar/cinecode) thành một Hermes Skill chính thức (`optional-skills/creative/cinecode/`), cho phép người dùng ra lệnh tạo video từ Zalo (hoặc bất kỳ gateway chat nào) và nhận lại file video MP4 hoàn chỉnh.

### Chi tiết các bước thực hiện:
1. **Thiết kế Skill Directory:**
   ```
   optional-skills/creative/cinecode/
   ├── SKILL.md
   ├── scripts/
   │   └── render_video.py
   └── references/
   ```
2. **Tuân thủ Tiêu chuẩn Skill của Hermes:**
   - `description` ≤ 60 ký tự, kết thúc bằng dấu chấm: `Render AI-generated code-based videos to MP4 format.`
   - Tham chiếu native tools (`terminal`, `read_file`, `write_file`).
   - Đặt trong `optional-skills/` do phụ thuộc vào render engine/ffmpeg.
3. **Đóng gói Script điều khiển:**
   - `render_video.py` nhận prompt hoặc kịch bản, chạy pipeline cinecode để xuất MP4 ra output folder.
4. **Kiểm thử E2E:**
   - User chat trên Zalo -> Hermes Agent kích hoạt Cinecode render video -> Hermes gọi `send_video(chat_id, video_path)` gửi video ngược lại Zalo.
