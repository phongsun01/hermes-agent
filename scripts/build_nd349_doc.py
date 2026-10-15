import re
from pathlib import Path

raw_file = Path(r"D:\Antigravity\law-wiki-bidding-v2\raw\nd-349.md")
text = raw_file.read_text(encoding="utf-8")

arts = re.findall(r"\*\*Điều\s+(\d+)\.\s+([^\*]+)\*\*\s*\n\s*(.*?)(?=\*\*Điều\s+\d+\.|\Z)", text, flags=re.DOTALL)

out_doc = []
out_doc.append("""---
type: document
category: subordinate-legislation
doc_type: nghị-định
code: "349/2026/NĐ-CP"
title: "Nghị định sửa đổi, bổ sung một số điều của các Nghị định quy định chi tiết một số điều và biện pháp thi hành Luật Đấu thầu về lựa chọn nhà thầu"
implements: "[[luat-dau-thau-2023]]"
amends: ["[[documents/nd-214-2025|Nghị định 214/2025/NĐ-CP]]", "Nghị định 32/2019/NĐ-CP"]
issued_by: "Chính phủ"
issued_date: 2026-09-09
effective_date: 2026-09-09
status: active
total_articles: 28
tags: [nghị-định, nd-349-2026, sửa-đổi-nd-214, lựa-chọn-nhà-thầu, chỉ-định-thầu]
---

# Nghị định 349/2026/NĐ-CP

**Thuộc:** [[luat-dau-thau-2023]]  
**Văn bản sửa đổi:** [[documents/nd-214-2025|Nghị định 214/2025/NĐ-CP]], Nghị định 32/2019/NĐ-CP  
**Ngày ban hành:** 09/09/2026 | **Ngày hiệu lực:** 09/09/2026  

---

## Tóm tắt nội dung đổi mới quan trọng

Nghị định 349/2026/NĐ-CP là văn bản sửa đổi, bổ sung quy mô lớn đối với Nghị định 214/2025/NĐ-CP với nhiều điểm đột phá:
1. **Nâng mạnh hạn mức chỉ định thầu (Điều 4 - sửa Điều 78 NĐ 214):**
   - Mua sắm thường xuyên không hình thành dự án: lên **01 tỷ đồng** (trước đây 500 triệu đồng).
   - Gói thầu dịch vụ tư vấn thuộc dự án: lên **03 tỷ đồng** (trước đây 800 triệu đồng).
   - Gói thầu dịch vụ phi tư vấn, hàng hóa, xây lắp, hỗn hợp thuộc dự án: lên **05 tỷ đồng** (trước đây 02 tỷ đồng).
2. **Mở rộng các trường hợp chỉ định thầu cấp bách & đặc thù (Điều 4, Điều 5, Điều 6):**
   - Bổ sung trường hợp đấu thầu không thành công: không có nhà thầu nộp HSDT hoặc tất cả HSDT không đáp ứng (điểm e1 khoản 2 Điều 78).
   - Mở rộng phạm vi chuyển đổi số, cơ sở dữ liệu dùng chung, giải phóng mặt bằng tái định cư.
   - Cho phép chỉ định thầu mua sắm thanh lý, phá sản, sàn giao dịch hàng hóa.
3. **Tháo gỡ yêu cầu chứng chỉ nghiệp vụ và tổ chuyên gia (Điều 2 - sửa Điều 21 NĐ 214):**
   - Gói thầu KHCN, đổi mới sáng tạo, dự toán mua sắm không hình thành dự án không bắt buộc có chứng chỉ nghiệp vụ chuyên môn đấu thầu (trừ tư vấn độc lập).
   - Huy động chuyên gia chuyên ngành không bắt buộc có chứng chỉ nghiệp vụ đấu thầu.
4. **Cơ chế thu thập báo giá linh hoạt (Điều 1 - sửa Điều 18 NĐ 214):**
   - Quy định cụ thể cách tính giá trung bình (được loại trừ báo giá lệch quá 30%).
   - Miễn trừ trách nhiệm cho chủ đầu tư khi đơn vị cung cấp báo giá vi phạm cạnh tranh/nâng khống giá nếu chủ đầu tư đã tuân thủ đúng quy trình công khai, minh bạch.
5. **Đơn giản hóa thủ tục chỉ định thầu thông thường và rút gọn (Điều 5, Điều 6):**
   - Chủ đầu tư không bắt buộc thẩm định hồ sơ yêu cầu và kết quả lựa chọn nhà thầu.

---

## Mục lục các Điều sửa đổi

### Chương I: Sửa đổi, bổ sung Nghị định 214/2025/NĐ-CP
- **Điều 1:** Sửa đổi điểm d khoản 2 Điều 18 (Xác định giá gói thầu & thu thập báo giá)
- **Điều 2:** Sửa đổi khoản 2, bổ sung khoản 2a Điều 21 (Điều kiện năng lực tổ chuyên gia, tổ thẩm định)
- **Điều 3:** Sửa đổi khoản 2 Điều 35 (Cập nhật tiến độ hợp đồng & nhà thầu phụ trên mạng)
- **Điều 4:** Sửa đổi Điều 78 (Các trường hợp chỉ định thầu & hạn mức chỉ định thầu)
- **Điều 5:** Sửa đổi Điều 79 (Quy trình chỉ định thầu thông thường)
- **Điều 6:** Sửa đổi Điều 80 (Quy trình chỉ định thầu rút gọn)
- **Điều 7:** Sửa đổi khoản 4 Điều 84 (Các gói thầu lựa chọn nhà thầu trường hợp đặc biệt)
- **Điều 8:** Sửa đổi Điều 85 (Quy trình lựa chọn nhà thầu trường hợp đặc biệt)
- **Điều 9:** Sửa đổi Điều 98 (Hạn mức chào giá trực tuyến & mua sắm trực tuyến)
- **Điều 10:** Sửa đổi Điều 106 (Điều kiện đặt hàng sản phẩm, dịch vụ công ích)
- **Điều 11:** Sửa đổi Điều 109 (Lựa chọn đơn vị cung cấp sản phẩm dịch vụ công)
- **Điều 12:** Sửa đổi khoản 2 Điều 117 (Hợp đồng trọn gói)
- **Điều 13:** Sửa đổi Điều 131 (Giám sát hoạt động đấu thầu)
- **Điều 14:** Sửa đổi Điều 132 (Xử lý vi phạm trong đấu thầu)
- **Điều 15:** Sửa đổi Điều 138 (Thẩm quyền giải quyết kiến nghị)
- **Điều 16:** Sửa đổi Điều 140 (Xử lý tình huống trong đấu thầu)
- **Điều 17:** Sửa đổi khoản 2 Điều 141 (Phân cấp phê duyệt kế hoạch & xử lý tình huống)
- **Điều 18:** Bổ sung điểm đ khoản 1 Điều 146 (Cơ sở dữ liệu giá trong đấu thầu)
- **Điều 19:** Thay thế, bãi bỏ một số cụm từ

### Chương II: Sửa đổi Nghị định 32/2019/NĐ-CP (Sản phẩm, dịch vụ công)
- **Điều 20 - 26:** Sửa đổi các quy định về giao nhiệm vụ, đặt hàng dịch vụ công và đơn giá đặt hàng

### Chương III: Điều khoản thi hành
- **Điều 27:** Điều khoản chuyển tiếp
- **Điều 28:** Hiệu lực thi hành (từ 09/09/2026)

---

## Nội dung chi tiết các Điều của Nghị định 349/2026/NĐ-CP
""")

for num, title, body in arts:
    body_clean = body.strip()
    out_doc.append(f"### Điều {num}. {title.strip()}\n\n{body_clean}\n")

out_path = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\documents\nd-349-2026.md")
out_path.write_text("\n".join(out_doc), encoding="utf-8")
print(f"Successfully created {out_path} with {len(out_doc)} sections!")
