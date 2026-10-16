# Template Thông Báo Kết Quả Xổ Số Miền Bắc (XSMB)

Template chuẩn dành cho cả 2 Cron Job báo kết quả XSMB lúc **18:35 VN** hàng ngày:
1. **Cron cá nhân (`8dfb5caeb2f9`)**: chế độ `no_agent: true` (script xuất trực tiếp theo cấu trúc template).
2. **Cron nhóm Zalo AI (`0a0d86219ede`)**: chế độ LLM Agent (AI định dạng và trình bày thống nhất theo template).

---

## Mẫu Tin Nhắn Chuẩn Gửi Zalo / Messaging

```text
🎰 KẾT QUẢ XỔ SỐ MIỀN BẮC — NGÀY {ngay}

1. BẢNG KẾT QUẢ CHI TIẾT:
🏆 ĐB: {gdb}
🥇 G1:  {g1}
🥈 G2:  {g2}
🥉 G3:  {g3}
🏅 G4:  {g4}
🏅 G5:  {g5}
🏅 G6:  {g6}
🏅 G7:  {g7}

2. DANH SÁCH LÔ TÔ (2 SỐ CUỐI):
👉 {loto_list}

3. ĐÁNH GIÁ ĐỘ CHÍNH XÁC SOI CẦU HÔM NAY:
(Đối chiếu các phương pháp dự báo ngày hôm qua với kết quả thực tế hôm nay)
- Cầu Pascal hôm qua ({pascal_pred}): {pascal_status}
- Top 10 Monte Carlo: Trúng {mc_hit_count}/10 số {mc_hit_details}
- Top 10 Bayesian CDM: Trúng {cdm_hit_count}/10 số {cdm_hit_details}

4. DỰ BÁO THAM KHẢO KỲ TIẾP THEO:
🎯 Cầu Pascal: {next_pascal}
🔮 Top Monte Carlo (30 ngày): {next_top_mc}
📊 Top Bayesian CDM: {next_top_cdm}

⚠️ LƯU Ý: Kết quả quay số hoàn toàn ngẫu nhiên. Mọi dự báo dựa trên thống kê xác suất chỉ mang tính chất tham khảo giải trí!
```

---

## Ví Dụ Thực Tế Minh Họa

```text
🎰 KẾT QUẢ XỔ SỐ MIỀN BẮC — NGÀY 15/10/2026

1. BẢNG KẾT QUẢ CHI TIẾT:
🏆 ĐB: 62066
🥇 G1:  87176
🥈 G2:  93642 - 37409
🥉 G3:  28087 - 24887 - 58423 - 25269 - 33005 - 45004
🏅 G4:  5904 - 5771 - 6928 - 7981
🏅 G5:  0866 - 7772 - 6093 - 9746 - 0853 - 3967
🏅 G6:  287 - 162 - 312
🏅 G7:  96 - 27 - 58 - 91

2. DANH SÁCH LÔ TÔ (2 SỐ CUỐI):
👉 04 - 05 - 09 - 12 - 23 - 27 - 28 - 42 - 46 - 53 - 58 - 62 - 66 - 67 - 69 - 71 - 72 - 76 - 81 - 87 - 91 - 93 - 96

3. ĐÁNH GIÁ ĐỘ CHÍNH XÁC SOI CẦU HÔM NAY:
(Đối chiếu các phương pháp dự báo ngày hôm qua với kết quả thực tế hôm nay)
- Cầu Pascal hôm qua (33): Trượt (33)
- Top 10 Monte Carlo: Trúng 2/10 số (Trúng: 69 - 76)
- Top 10 Bayesian CDM: Trúng 2/10 số (Trúng: 69 - 76)

4. DỰ BÁO THAM KHẢO KỲ TIẾP THEO:
🎯 Cầu Pascal: 08
🔮 Top Monte Carlo (30 ngày): 52, 92, 80, 69, 76, 13, 55, 83, 84, 06
📊 Top Bayesian CDM: 52, 69, 92, 76, 80, 55, 13, 83, 84, 06

⚠️ LƯU Ý: Kết quả quay số hoàn toàn ngẫu nhiên. Mọi dự báo dựa trên thống kê xác suất chỉ mang tính chất tham khảo giải trí!
```

---

## Chi Tiết Các Trường Dữ Liệu

1. **Tiêu đề**:
   - `{ngay}`: Ngày quay định dạng `DD/MM/YYYY`.

2. **Mục 1 — Bảng kết quả chi tiết**:
   - Thể hiện rõ 27 giải truyền thống từ ĐB đến G7, các số trong cùng một giải cách nhau bởi dấu cách hoặc dấu gạch ngang (`-`).

3. **Mục 2 — Danh sách lô tô**:
   - Lọc lấy 2 số cuối của toàn bộ 27 giải, loại bỏ trùng lặp và sắp xếp theo thứ tự tăng dần từ bé đến lớn.

4. **Mục 3 — Đánh giá độ chính xác**:
   - Kiểm định khách quan tỷ lệ trúng của 3 phương pháp đã dự báo ở kỳ trước (Pascal, mô phỏng Monte Carlo, mô hình phân phối Dirichlet-Multinomial Bayesian CDM).

5. **Mục 4 — Dự báo tham khảo**:
   - Cung cấp bộ số tham khảo cho kỳ quay tiếp theo dựa trên dữ liệu lịch sử N ngày gần nhất.
