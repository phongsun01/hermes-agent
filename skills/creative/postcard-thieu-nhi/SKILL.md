---
name: postcard-thieu-nhi
description: "Tạo postcard chữ buổi tối cho thiếu nhi — dành cho nhóm Zalo gia đình. Kết hợp câu chuyện/ẩn dụ + 5-7 câu đố vui, gửi qua cron 21h."
version: 1.0.0
author: Lala Tran
platforms: [linux, macos, windows]
---

# Postcard Thiếu Nhi — Daily Bedtime Messages for Kids

Kỹ thuật tạo nội dung postcard buổi tối cho thiếu nhi (lớp 2-5) gửi qua Zalo group. Phù hợp với gia đình có 2 con ở hai độ tuổi khác nhau.

## Khi nào dùng

- User yêu cầu setup nội dung hàng ngày cho các bạn nhỏ
- User muốn câu chuyện/ẩn dụ + câu đố gửi buổi tối
- Cần tạo cron job với nội dung phù hợp cho thiếu nhi

## Nguyên tắc Content

### NỘI DUNG CHÍNH (20-30 dòng, một mạch xuyên suốt)

1. **Mở đầu ấm áp** — gọi tên các con, dùng emoji 🌙⭐
2. **Phần chính** — dài 15-20 dòng, có thể:
   - Kể chuyện ngụ ngôn (sóc, thỏ, gấu, rùa, chim, tre...)
   - Dùng ẩn dụ thiên nhiên (cây tre vươn mình, cánh diều, dòng sông, ngọn núi)
   - Viết như lá thư tâm tình, giàu cảm xúc
   - Có chiều sâu, chạm vào cảm xúc và suy nghĩ
3. **Cầu nối sang câu đố** — "Câu đố nè:" hoặc tương tự
4. **5-7 câu đố vui** — đa dạng thể loại
5. **Kết thúc** — chúc ngủ ngon + chữ ký "❤️ Lala"

### CẤM TUYỆT ĐỐI
- ❌ Chia nội dung riêng cho từng bạn ("còn Bống thì...") — VIẾT CHUNG một mạch
- ❌ Nhắc đến công việc, lập trình, hệ thống công chức
- ❌ Viết tin nhắn không có dấu (Tin nhắn văn bản gửi đi bắt buộc phải là tiếng Việt có dấu đầy đủ, chuẩn xác)
- ❌ Nội dung ngắn/quá sơ sài

### ĐỊNH DẠNG TIN NHẮN
- Sử dụng markdown cơ bản để in đậm tiêu đề hoặc các từ khóa quan trọng (dùng cặp dấu sao `*chữ in đậm*` hoặc `**chữ in đậm**` để Zalo hiển thị in đậm).

### 5-7 CÂU ĐỐ VUI (luôn ở cuối)

Không tự nghĩ ra câu đố. Agent bắt buộc phải chạy lệnh sau để lấy ngẫu nhiên 5-7 câu đố thực tế từ kho câu đố của skill `dovui`:
```bash
python skills/creative/dovui/lib/dovui_tool.py random 5
```
Dựa trên kết quả JSON nhận được:
- Đưa danh sách các câu hỏi (`question`) vào cuối postcard.
- Tuyệt đối không hiển thị câu trả lời (`answer`) trong tin nhắn gửi đi.
- Gợi ý: Có thể lưu đáp án của hôm nay để gửi kèm trong phần đầu của postcard ngày mai.

### CHỦ ĐỀ THEO NGÀY

| Ngày | Chủ đề | Style gợi ý |
|------|--------|-------------|
| Thứ 2 | GIAO TIẾP — lời hay, cảm ơn, xin lỗi | Kể chuyện |
| Thứ 3 | CUỘC SỐNG — biết ơn, trân trọng | Postcard ý nghĩa |
| Thứ 4 | MƠ ƯỚC — dám mơ, kiên trì | Ẩn dụ thiên nhiên |
| Thứ 5 | GIAO TIẾP BẠN BÈ — chia sẻ, đoàn kết | Kể chuyện + đố |
| Thứ 6 | BÀI HỌC NHỎ — triết lý nhẹ nhàng | Ngụ ngôn |
| Thứ 7 | SÁNG TẠO & KHÁM PHÁ | Postcard khám phá |
| CN | GIA ĐÌNH & YÊU THƯƠNG | Ấm áp, tình cảm |

### Các bước thiết lập cron

1. Xác định: giờ gửi (thường 21h), nhóm đích, tên job
2. Viết prompt self-contained (cron job không có context chat cũ)
3. Trong prompt: mô tả rõ persona (Lala Tran), tone giọng, format, quy tắc
4. Test bằng cronjob(action='run') hoặc đợi lần chạy đầu

## Hình ảnh ẩn dụ yêu thích

(dựa trên feedback thực tế từ người dùng — chị Huế Tồ)

- **🌿 Cây tre vươn mình** — ẩn dụ về trưởng thành, vượt thử thách. "Phải vươn thì mới cao được. Những tầng lá rậm chính là bài tập giúp mình cứng cáp hơn."
- **🪁 Cánh diều** — ước mơ, bay cao, nuôi dưỡng khát vọng
- **🌊 Dòng sông ra biển** — hành trình trưởng thành
- **🌱 Cây non đón nắng** — mỗi ngày một lớn
- **🏔️ Ngọn núi** — thử thách cần vượt qua

## Pitfalls

- **Không chia riêng từng bạn** — chị Huế Tồ không thích style "còn Bi béo thì... còn Bống thì...". Viết chung một mạch.
- **Không gửi tin thật khi test** — luôn dùng cronjob(action='run') để test, không gửi trực tiếp vào group
- **Cron prompt phải self-contained** — không dựa vào context chat vì cron chạy session riêng
- **Định dạng Zalo** — Dùng `*in đậm*` hoặc `**in đậm**` để làm nổi bật từ khóa. Tin nhắn gửi đi bắt buộc phải là tiếng Việt có dấu đầy đủ.
- **Ảnh Pillow** — Nếu vẽ chữ lên ảnh Pillow gặp lỗi hiển thị tiếng Việt có dấu, hãy vẽ chữ không dấu hoặc chữ tiếng Anh ngắn gọn, nhưng tuyệt đối không viết không dấu ở tin nhắn chat.
- **Model rate limit (HTTP 429)** — Cron có thể fail với `RuntimeError: HTTP 429: ... Invalid JSON response`. Thường gặp với OpenRouter free tier. Fix:
  - Đổi model override cho cron job: `cronjob action=update job_id=... model={provider:..., model:...}`
  - Dùng model rẻ/ổn định (Gemini, GPT-4o mini) cho cron định kỳ.
  - Test trước bằng `cronjob(action='run')` vào buổi chiều để phát hiện sớm trước 21h.
  - Nếu lỗi transient, chạy lại cron job thủ công sau 30-60s.
