# Ghi chú nghiên cứu — Cơ sở thống kê

## Bài 1: arXiv:0806.4595 — Kiểm định tính công bằng (Coronel-Brizio et al.)

**Kết quả dùng được:** Kiểm định thống kê thứ tự Q để kiểm toán tính công bằng của nhà xổ số.

**Lý thuyết cốt lõi:**
Dưới giả thuyết công bằng H₀, số thứ i trong bộ đã sắp xếp Y(i) có:
- Kỳ vọng: μᵢ = (N+1)·i/(K+1)
- Hiệp phương sai: Cov(Y(i), Y(j)) = min(i,j)·(K−max(i,j)+1)·(N+1)·(N−K) / ((K+1)²·(K+2))

Thống kê kiểm định: **Q = m·(ȳ−μ)ᵀ·V⁻¹·(ȳ−μ) ~ χ²(K)**

Với Mega 6/45: N=45, K=6 → V⁻¹ có phần tử 28/585 (đường chéo) và −14/585 (ngoài đường chéo).

**Kết quả áp dụng (Mexico/Ý):** Một số giai đoạn bị bác bỏ H₀ (p≈0.006 và <10⁻⁵), chứng minh công cụ có khả năng phát hiện gian lận. Dữ liệu lành mạnh thường có p lớn.

**⚠️ Giới hạn:** Kiểm định này dùng để **kiểm toán nhà cái**, KHÔNG phải dự đoán số. p nhỏ = nhà xổ không công bằng; p lớn = không có bằng chứng lệch (không phải bằng chứng có thể dự đoán).

**Script đã kiểm tra:** `vietlott645.py` implement đúng V⁻¹, cả path CLT và Monte Carlo.

---

## Bài 2: arXiv:2403.12836 — Mô hình CDM (Nkomozake, preprint)

**Không dùng làm căn cứ dự đoán** vì các vấn đề nghiêm trọng:

1. **CDM = tần suất:** Với α ước lượng bằng MLE (αⱼ ∝ nⱼ), thứ hạng CDM **giống hệt xếp hạng theo tần suất** (chiến lược "hot"). Không có thông tin bổ sung.

2. **Không có baseline ngẫu nhiên:** Với 6/52, một vé ngẫu nhiên trùng ≥2 số mỗi ~7–8 kỳ. Bài báo cáo "12 kỳ trúng 2 số" mà không so sánh với random → kết quả không có ý nghĩa thống kê.

3. **Ngoại suy không hợp lệ:** "5 và 6 số trùng" không quan sát được trong 21 năm; con số "104 năm" là ngoại suy toán học không có cơ sở thực nghiệm.

4. **Martingale ngụy trang:** "3-strategy" = nhân đôi cược sau mỗi kỳ thua. EV mỗi vé $1 vẫn là −$0.50 bất kể chiến lược phân bổ.

5. **Preprint chưa phản biện**, 7KB — chưa được tạp chí peer-reviewed chấp nhận.

**Kết luận:** Dùng `backtest` của script để tự kiểm; không trích dẫn bài này với người dùng.

---

## Tóm tắt thực hành

| Công cụ | Có giá trị | Mục đích |
|---|---|---|
| Chi-square tần suất (hiệu chỉnh) | ✅ | Phát hiện bias lớn trong dữ liệu |
| Thống kê Q (0806.4595) | ✅ | Kiểm toán nhà xổ số |
| Backtest walk-forward | ✅ | Tự kiểm chiến lược hot/cold trước khi dùng |
| CDM dự đoán (2403.12836) | ❌ | Tương đương đếm tần suất, không hơn |
| Bất kỳ "hệ thống" nào | ❌ | EV âm, không thể thắng dài hạn |
