---
name: vietlott
description: Phân tích Vietlott Mega 6/45 — kiểm định tính ngẫu nhiên, backtest các chiến lược "dự đoán", xác suất trúng (siêu bội), tính kỳ vọng EV và sinh bộ số. Dùng khi người dùng hỏi kết quả, tần suất, xác suất, giá trị kỳ vọng hoặc "dự đoán" Vietlott 6/45.
---

# Vietlott 6/45

Nguồn dữ liệu: https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45.html
Trang kết quả theo ngày: `.../mega-6x45/DD-MM-YYYY.html` (HTML tĩnh).

## Nguyên tắc trả lời
- Các kỳ quay độc lập; không có phương pháp dự đoán đã được chứng minh. Nói rõ điều này.
- "Dự đoán" = bộ số tham khảo + xác suất thật (jackpot 1/8.145.060). Không hứa lợi nhuận.

## Quy trình
1. **Dữ liệu (crawler)**: 
   - `python vl_fetch.py --backfill 400` (lấy 400 kỳ gần nhất gộp vào `draws.csv`).
   - `python vl_fetch.py --update` (chỉ lấy các kỳ mới sau kỳ cuối trong cache, chạy sau 18:45 T4/T6/CN).
   - `python vl_fetch.py --enrich` (bổ sung jackpot + số giải cho các kỳ đã có nhưng thiếu cột).
   - `python vl_fetch.py --check` (kiểm tra tính liên tục, thiếu kỳ, ngày và tỷ lệ giải Ba/Nhì nghi vấn).
   - `python vl_fetch.py --dump DD-MM-YYYY` (lưu HTML thô để debug nếu parser gặp lỗi).
   - Định dạng `draws.csv`: `ngay,n1..n6,ky,jackpot,w_jackpot,w_nhat,w_nhi,w_ba` (cũ -> mới). File cũ 8 cột vẫn tự động tương thích.
2. `python vietlott645.py stats [draws.csv] [-n 300]` — (a) chi-square tần suất đã hiệu chỉnh; (b) kiểm định thống kê thứ tự Q (Monte Carlo + CLT). Cảnh báo nếu < 100 kỳ.
3. `python vietlott645.py backtest [draws.csv] [-n 300]` — walk-forward: hot / cold / random có trùng nhiều hơn kỳ vọng 0,8 số/kỳ không (z-test), xuất bảng thống kê các hạng giải đạt được.
4. `python vietlott645.py ev [--jackpot-ty 30] [--lam 0.5 | --tickets 4e6 | --csv draws.csv] [--no-tax]` — tính giá trị kỳ vọng (EV) mỗi vé 10.000đ theo jackpot:
   - Giải phụ cố định ≈ 1.370đ/vé;
   - Jackpot chia đều cho (1+X) người trúng, $X \sim \text{Poisson}(\lambda)$;
   - Thuế TNCN 10% phần > 10 triệu tính trên phần mỗi người nhận;
   - Với `--csv`: ước lượng số vé bán từ số giải (MLE Poisson trên giải 3–6) và hồi quy $\ln(\text{vé}) = a + b \cdot \ln(\text{jackpot})$ để dự đoán $\lambda$ cho jackpot kỳ tới kèm dải P10–P90. Kèm jackpot hòa vốn. Báo rõ số tiền kỳ vọng mất trên mỗi vé.
5. `python vietlott645.py odds` — bảng xác suất trúng 0–6 số. `pick` — sinh bộ số tham khảo.
6. `python vl_report.py` — tạo báo cáo tổng hợp 5 mục chuẩn format (kết quả, giải thưởng, thống kê Q, đánh giá dự đoán kỳ trước, gợi ý kỳ tới).

Lưu ý `ev`: $\lambda$ ước lượng từ số giải bị thiên lệch khi bộ số quay ra được nhiều người chọn; mức giải/thuế đặt ở `PRIZE`/`TAX_*` trong `vietlott645.py`, đối chiếu theo thể lệ hiện hành.

## Cơ sở nghiên cứu (arXiv)
**0806.4595 — Coronel-Brizio, Hernández-Montoya, Rapallo, Scalas.** Dưới giả thuyết công bằng, số thứ i trong bộ đã sắp xếp có kỳ vọng (N+1)i/(k+1) và hiệp phương sai i(k−j+1)(N+1)(N−k)/((k+1)²(k+2)). Thống kê Q = m(ȳ−μ)'V⁻¹(ȳ−μ) ~ χ²(k). Áp dụng cho Mexico/Ý: một số giai đoạn bị bác bỏ (p≈0,006 và <10⁻⁵), nghĩa là kiểm định dùng để *kiểm toán nhà cái*, không phải để dự đoán. Script đã kiểm tra khớp ma trận V⁻¹ trong bài (28/585, −14/585).

**2403.12836 — Nkomozake (preprint, 7 KB, chưa phản biện).** Mô hình CDM: dự đoán = M(αⱼ+nⱼ)/Σ(αⱼ+nⱼ). Với α ước lượng bằng MLE hoặc method of moments (αⱼ ∝ nⱼ), thứ hạng này **giống hệt xếp hạng theo tần suất** (= chiến lược "hot"). Vấn đề của bài:
- Không có baseline ngẫu nhiên. Với 6/52, một vé ngẫu nhiên trùng ≥2 số cứ ~7–8 kỳ một lần; bài báo cáo "12 kỳ" cho 2 số — không tốt hơn ngẫu nhiên.
- 5 và 6 số trùng không quan sát được trong 21 năm; các con số "104 năm / 104.167 năm" là ngoại suy.
- Pick-3: ~9 lần trúng/5.844 kỳ; ngẫu nhiên kỳ vọng ≈5,8 (không có ý nghĩa thống kê). Chiến lược "3-strategy" là nhân đôi cược kiểu martingale; EV mỗi vé $1 trả $500 với xác suất 1/1000 vẫn là −$0,50, không đổi theo cách phân bổ.
- Phương pháp "main diagonal" phụ thuộc thứ tự dòng, không có cơ sở thống kê.
Kết luận: không dùng bài này làm căn cứ dự đoán; dùng `backtest` để tự kiểm.

## Sửa lỗi so với bản trước
Chi-square tần suất bản cũ so với ngưỡng df=44 là quá dễ dãi: bốc không hoàn lại nên X² thô có kỳ vọng N−K=39. Bản mới dùng X²·(N−1)/(N−K) ~ χ²(44).
