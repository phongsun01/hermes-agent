---
name: vietlott-645
description: Phân tích Vietlott Mega 6/45 — kiểm định tính ngẫu nhiên, backtest các chiến lược "dự đoán", xác suất trúng (siêu bội) và sinh bộ số. Dùng khi người dùng hỏi kết quả, tần suất, xác suất hoặc "dự đoán" Vietlott 6/45.
---

# Vietlott 6/45

Nguồn dữ liệu: https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html
(`.../winning-number-645` chỉ là cache 2020 với 8 kỳ; `645.html` chặn bot — cần người dùng dán bảng kết quả hoặc cung cấp endpoint AJAX.)

## Nguyên tắc trả lời
- Các kỳ quay độc lập; không có phương pháp dự đoán đã được chứng minh. Nói rõ điều này.
- "Dự đoán" = bộ số tham khảo + xác suất thật (jackpot 1/8.145.060). Không hứa lợi nhuận.

## Quy trình
1. Dữ liệu: người dùng dán bảng kết quả (dòng `dd/mm/yyyy 00642 020817233041`) vào `raw.txt`
   → `python vietlott645.py parse raw.txt > draws.csv` (sắp cũ → mới).
2. `stats draws.csv` — (a) chi-square tần suất đã hiệu chỉnh; (b) kiểm định thống kê thứ tự Q (Monte Carlo + CLT). Cảnh báo nếu < 100 kỳ.
3. `backtest draws.csv` — walk-forward: hot / cold / random có trùng nhiều hơn kỳ vọng 0,8 số/kỳ không (z-test).
4. `odds` — bảng xác suất trúng 0–6 số. `pick` — sinh bộ số.

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
