# 📋 TEMPLATE BÁO CÁO CRON JOB HERMES

> File mẫu chuẩn (`template`) quy định cấu trúc và cách trình bày thống nhất cho tất cả các thông báo, báo cáo tự động do Hermes gửi qua kênh chat (Zalo, Telegram, Slack, Webhook...) từ các tác vụ Cron Job.

---

## 🎯 QUY TẮC BẮT BUỘC (CORE RULES)

1. **Đánh số thứ tự rõ ràng (`1.`, `2.`, `3.`...)**: Mọi danh sách mục tiêu, đầu việc, văn bản, tin tức hoặc kết quả bắt buộc phải được đánh số thứ tự để dễ tra cứu, phản hồi và giao việc.
2. **Tiêu đề định danh thống nhất**: Luôn có Header gồm icon chủ đề + Tên tác vụ + Ngày giờ thực thi (Giờ VN - UTC+7).
3. **Phần tóm tắt / Chỉ số tổng quan (Overview Metric)**: Đặt ngay đầu báo cáo (Ví dụ: `📊 Tổng số: X mục | Khẩn: Y | Hoàn thành: Z`).
4. **Cấu trúc từng mục chi tiết**:
   - Số thứ tự + Mã định danh / Tiêu đề chính (In đậm) + Nhãn trạng thái/Tag
   - Dòng mô tả nội dung chính / Tóm tắt thực tế (2–3 dòng ngắn gọn, súc tích)
   - Thông tin bổ sung / Hành động cần xử lý (nếu có)
5. **Đường dẫn tra cứu / Phụ lục**: Đặt ở cuối tin nhắn (`🔗 Link xem chi tiết...`).
6. **Độ dài & Định dạng tối ưu cho Mobile (Zalo/Telegram)**:
   - Dùng emoji trực quan, không dùng bảng markdown phức tạp vì dễ vỡ giao diện điện thoại.
   - Nội dung cô đọng dưới 4.000 ký tự (tránh bị hệ thống cắt ngắn).
   - Nếu không có dữ liệu mới phát sinh trong kỳ quét: Trả về chính xác `[SILENT]` (để hệ thống bỏ qua không spam tin rác).

---

## 📐 MẪU CẤU TRÚC CHUẨN (STANDARD MARKDOWN SKELETON)

```markdown
{ICON_CHỦ_ĐỀ} [BÁO CÁO] {TÊN_TÁC_VỤ_CRON}
📅 Thời gian: {HH:mm - DD/MM/YYYY} | 🎯 Kỳ/Mã: #{MÃ_HOẶC_ID}
───────────────────────────────────────
📊 TỔNG QUAN: {X} mục mới | {Y} mục ưu tiên/cần xử lý

{DANH_SÁCH_CHI_TIẾT_CÓ_ĐÁNH_SỐ}:
1. 🔴 [{MÃ_HOẶC_LOẠI}] {TIÊU_ĐỀ_MỤC_1}
   - Tóm tắt: {Nội dung chính tóm tắt ngắn gọn}
   - Trạng thái/Thời hạn: {Hạn chót hoặc ghi chú xử lý}

2. 🟡 [{MÃ_HOẶC_LOẠI}] {TIÊU_ĐỀ_MỤC_2}
   - Tóm tắt: {Nội dung chính tóm tắt ngắn gọn}
   - Trạng thái/Thời hạn: {Hạn chót hoặc ghi chú xử lý}

3. 🟢 [{MÃ_HOẶC_LOẠI}] {TIÊU_ĐỀ_MỤC_3}
   - Tóm tắt: {Nội dung chính tóm tắt ngắn gọn}
   - Trạng thái/Thời hạn: {Hạn chót hoặc ghi chú xử lý}

───────────────────────────────────────
💡 ĐỀ XUẤT / LƯU Ý HÀNH ĐỘNG:
- {Hành động cần làm hoặc lưu ý quan trọng nhất trong ngày}

🔗 Tra cứu chi tiết: {ĐƯỜNG_DẪN_LINK_NẾU_CÓ}
```

---

## 📂 CÁC VÍ DỤ ÁP DỤNG THỰC TẾ

### 1. Mẫu quét Công văn / Văn bản điều hành (Công chức)
```markdown
📋 [CÔNG CHỨC] QUÉT CÔNG VĂN ĐẾN MỚI
📅 Thời gian: 17:00 - 09/10/2026 | Sổ: 2256, 226
───────────────────────────────────────
📊 TỔNG QUAN: 3 văn bản mới (1 hỏa tốc, 2 thông thường)

1. 🔴 [HỎA TỐC] #4303 | 6903/SYT-VP
   - Trích yếu: Hưởng ứng và phổ cập bộ nhận diện Ngày Chuyển đổi số quốc gia năm 2026.
   - Cơ quan: Sở Y tế.
   - Yêu cầu: Phổ biến trước 17h ngày 10/10/2026.

2. 🟢 #4305 | 2282A/KH-TTKSBT ✅ (Tự động hoàn thành)
   - Trích yếu: Kế hoạch Chăm sóc sức khỏe Người cao tuổi năm 2026.
   - Cơ quan: TT Kiểm soát bệnh tật tỉnh Quảng Ninh.
   - Phân loại: Kế hoạch chuyên môn y tế.

3. 🟢 #4302 | 85-KH/ĐU ✅ (Tự động hoàn thành)
   - Trích yếu: Triển khai Quy định số 211-QĐ/TW về quản lý hồ sơ cán bộ.
   - Cơ quan: Đảng ủy Sở Y tế.

🔗 Tra cứu phần mềm: https://congchuc.quangninh.gov.vn
```

### 2. Mẫu điểm tin / Nghiên cứu khoa học hàng ngày (arXiv, AI, Tech)
```markdown
🔬 [ĐIỂM TIN] NGHIÊN CỨU KHOA HỌC MỖI NGÀY
📅 Thời gian: 14:00 - 09/10/2026 | Lĩnh vực: AI Agents & Khoa học
───────────────────────────────────────
📊 CHỦ ĐỀ CHỌN LỌC: Đánh giá năng lực xây dựng mô hình khí hậu của AI Agents

1. 📑 Tên bài báo: SciExam for ENSO: Can AI Agents Build Climate Models?
   - Tác giả: Yinling Zhang, Langchen Liu, Dongbin Xiu et al. (07/10/2026)

2. 💡 Tóm tắt nội dung chính:
   - Bài báo giới thiệu khung đánh giá mới SciExam nhằm thử thách tác nhân AI tự lập trình, xử lý dữ liệu và thiết lập mô hình dự báo hiện tượng El Niño (ENSO).
   - Đánh giá khả năng của AI trong quy trình khám phá khoa học thực thụ thay vì chỉ giải trắc nghiệm lý thuyết.

3. ✨ Ý nghĩa thực tiễn:
   - Đẩy nhanh tốc độ mô phỏng dự báo thời tiết, thiên tai và biến đổi khí hậu.
   - Bước tiến quan trọng chuyển đổi AI từ "trợ lý tóm tắt" thành "nhà nghiên cứu độc lập".

🔗 Abstract: https://arxiv.org/abs/2610.10513
📥 PDF: https://arxiv.org/pdf/2610.10513
```

### 3. Mẫu phân tích / Cập nhật kết quả Xổ số & Thống kê (Vietlott / XSMB)
```markdown
🎲 [VIETLOTT] KẾT QUẢ & PHÂN TÍCH MEGA 6/45
📅 Kỳ quay: #01572 | Ngày: 07/10/2026
───────────────────────────────────────
🎯 BỘ SỐ TRÚNG THƯỞNG: 10 - 14 - 36 - 37 - 41 - 43
💰 Jackpot hiện tại: ~86.148.921.500 đ

📊 PHÂN TÍCH THỐNG KÊ (30 kỳ gần nhất):
1. Top số Nóng (về nhiều): 15 (9 lần), 27 (9 lần), 03 (7 lần), 36 (7 lần).
2. Top số Lạnh (ít về): 05 (0 lần), 42 (0 lần), 08 (1 lần), 32 (1 lần).
3. Kiểm toán ngẫu nhiên (arXiv:0806.4595):
   - Thống kê thứ tự Q = 3.66 (df=6, p = 0.723 > 0.05).
   - Dữ liệu hoàn toàn ngẫu nhiên và công bằng.

🎰 BỘ SỐ THAM KHẢO KỲ TỚI:
1. Vé 1 (Hot/CDM): [01, 15, 22, 28, 31, 34]
2. Vé 2 (Cold/Đảo): [01, 06, 16, 23, 25, 35]
3. Vé 3 (Ngẫu nhiên): [15, 18, 26, 27, 36, 44]

⚠️ Lưu ý: Xác suất trúng Jackpot là 1/8.145.060. EV mỗi vé < 0.
```

### 4. Mẫu Thời khóa biểu / Lịch trình công việc gia đình
```markdown
📅 [LỊCH TRÌNH] THỜI KHÓA BIỂU GIA ĐÌNH HÔM NAY
📅 Thứ 6, Ngày 09/10/2026 (29/08 Âm lịch)
───────────────────────────────────────
📊 TỔNG CỘNG: 4 sự kiện chính trong ngày

1. ⏰ 07:00 - 11:30 | 👦 Bi: Học chính khóa (Trường Văn Lang)
   - Môn: GDTC (nhớ mang giầy thể thao), Mỹ thuật, Toán, Tiếng Việt.

2. ⏰ 14:00 - 16:30 | 👦 Bi: Học buổi chiều (Trường Văn Lang)
   - Môn: Tiếng Việt, Lịch sử - Địa lý, Hoạt động trải nghiệm.

3. ⏰ 17:30 - 19:00 | 👦 Bi: Học Tiếng Anh tại Scots
   - Chuẩn bị: Sách vở Scots, mang cặp đi học.

4. ⏰ 17:30 - 19:00 | 👧 Bống: Học Tiếng Anh tại Scots
   - Chuẩn bị: Sách vở Scots, mang cặp đi học.

Chúc cả nhà một ngày học tập và làm việc thật vui vẻ! ❤️
```

---

## 🛠️ HƯỚNG DẪN KHI VIẾT PROMPT CHO CRON JOB TRONG `jobs.json`

Khi tạo hoặc sửa prompt của cron job trong `jobs.json`, hãy gắn chỉ dẫn tuân thủ template như sau:

```text
Trình bày kết quả theo đúng cấu trúc tại cron/CRON_REPORT_TEMPLATE.md:
- Có icon tiêu đề + Ngày giờ thực hiện
- Có chỉ số tổng quan ở dòng đầu
- Toàn bộ các mục kết quả phải ĐƯỢC ĐÁNH SỐ THỨ TỰ (1., 2., 3...)
- Trình bày ngắn gọn, rõ ràng, tối ưu cho giao diện Zalo/Mobile
- Nếu không có dữ liệu mới cần báo, chỉ trả về duy nhất marker "[SILENT]"
```
