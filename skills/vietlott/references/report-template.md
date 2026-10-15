# Template Thông Báo Kết Quả Vietlott Mega 6/45

Template báo cáo chuẩn dành cho Cron Job `vl_update_cron` gửi qua Zalo/Messaging hoặc khi người dùng gọi `/vl` / `/vl today`.
Báo cáo có đánh số mục từ 1 đến 5 rõ ràng, định dạng trực quan, tương thích hiển thị tốt trên thiết bị di động.

---

## Mẫu Tin Nhắn Chuẩn (Đánh Số Mục 1 → 5)

```text
🎰 KẾT QUẢ VIETLOTT MEGA 6/45 — KỲ #{ky:05d} ({ngay})

1. BỘ SỐ TRÚNG THƯỞNG:
   👉 {n1:02d} - {n2:02d} - {n3:02d} - {n4:02d} - {n5:02d} - {n6:02d}

2. THÔNG TIN GIẢI THƯỞNG:
   🏆 Jackpot: {jackpot} đ ({jackpot_status})
   🥇 Giải Nhất (5 số): {g1_winners} giải (10.000.000 đ)
   🥈 Giải Nhì  (4 số): {g2_winners} giải (300.000 đ)
   🥉 Giải Ba   (3 số): {g3_winners} giải (30.000 đ)

3. THỐNG KÊ NHANH ({m} KỲ GẦN NHẤT):
   🔥 Top số nóng: {hot_numbers}
   ❄️ Top số lạnh: {cold_numbers}
   ⚖️ Kiểm định ngẫu nhiên Q (arXiv:0806.4595): p = {p_q:.3f} ({q_verdict})

4. ĐÁNH GIÁ DỰ ĐOÁN KỲ NÀY:
   (Đối chiếu bộ số gợi ý kỳ trước #{prev_ky:05d} với kết quả hôm nay)
   - Vé Hot (Tần suất): {hot_eval}
   - Vé Cold (Lạnh):    {cold_eval}
   - Vé Random:         {rand_eval}

5. BỘ SỐ THAM KHẢO KỲ TIẾP THEO (KỲ #{next_ky:05d}):
   🎯 Vé Hot (Tần suất cao): [{pick_hot}]
   🎯 Vé Cold (Ít xuất hiện): [{pick_cold}]
   🎲 Vé Random:              [{pick_rand}]

⚠️ LƯU Ý: Mọi bộ số đều có xác suất Jackpot 1/8.145.060. Kỳ vọng mỗi vé âm (EV < 0). Chúc bạn may mắn!
```

---

## Chi Tiết Các Trường Dữ Liệu

1. **Tiêu đề & Kỳ quay**:
   - `#{ky:05d}`: Số kỳ quay 5 chữ số (ví dụ `#01574`).
   - `{ngay}`: Ngày quay định dạng `DD/MM/YYYY`.

2. **Mục 1 — Bộ số trúng thưởng**:
   - 6 quả bóng số xếp theo thứ tự tăng dần, định dạng 2 chữ số cách nhau bằng dấu gạch ngang (`-`).

3. **Mục 2 — Thông tin giải thưởng**:
   - `{jackpot}`: Giá trị Jackpot tích lũy bằng đồng (ví dụ `17.917.606.500`). Dùng dấu chấm phân tách hàng nghìn chuẩn tiếng Việt.
   - `{jackpot_status}`: Nếu có người trúng thì ghi `"ĐÃ NỔ (X người trúng)"`, nếu chưa trúng thì ghi `"CHƯA NỔ - Tích lũy tiếp"`.
   - `{g1_winners}`, `{g2_winners}`, `{g3_winners}`: Số lượng giải nhất, nhì, ba tương ứng (được định dạng dấu chấm phân tách nghìn như `1.566`, `24.656`).

4. **Mục 3 — Thống kê & Kiểm định**:
   - `{m}`: Số lượng kỳ phân tích (mặc định lấy theo cache `draws.csv`, ví dụ 150 hoặc 300 kỳ).
   - `{hot_numbers}`: 5 số xuất hiện nhiều nhất và số lần xuất hiện `XX(k)`.
   - `{cold_numbers}`: 5 số xuất hiện ít nhất `XX(k)`.
   - `p_q`: p-value của thống kê thứ tự $Q$ (theo bài báo Coronel-Brizio et al. arXiv:0806.4595).
   - `{q_verdict}`: Nếu $m \ge 100$: `"Chuẩn ngẫu nhiên"` ($p \ge 0.01$) hoặc `"Cần theo dõi"` ($p < 0.01$). Nếu $m < 100$: `"Cần ≥100 kỳ để kết luận tin cậy"`.

5. **Mục 4 — Đánh giá dự đoán kỳ này**:
   - Tra cứu kỳ quay liền trước thực tế từ cache (không trừ 1 số học để tránh lỗi khi có kỳ hoãn/bỏ kỳ).
   - Đối chiếu số lượng số trùng khớp của 3 loại vé:
     - Vé Hot (Tần suất): Top 6 số tần suất cao nhất tính đến trước kỳ quay.
     - Vé Cold: Top 6 số tần suất thấp nhất tính đến trước kỳ quay.
     - Vé Random: Sinh bằng `random.Random(seed=prev_ky)` khớp 100% với vé đã gợi ý ở mục 5 của kỳ trước.

6. **Mục 5 — Bộ số tham khảo kỳ tiếp theo**:
   - `{next_ky:05d}`: Số kỳ tiếp theo.
   - 1 bộ số theo xếp hạng tần suất xuất hiện cao nhất (Hot top-6).
   - 1 bộ số theo tần suất xuất hiện thấp nhất (Cold bottom-6).
   - 1 bộ số ngẫu nhiên thuần túy sinh bằng `seed=next_ky` (Random) để kỳ sau có thể đánh giá và kiểm chứng minh bạch.
   - Luôn kèm lời cảnh báo EV < 0 và xác suất cố định $1 / 8.145.060$.

