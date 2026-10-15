from pathlib import Path

# 1. Cập nhật documents/nd-214-2025.md
nd214_hub = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\documents\nd-214-2025.md")
hub_text = nd214_hub.read_text(encoding="utf-8")

if "amended_by:" not in hub_text:
    hub_text = hub_text.replace(
        "status: active",
        "status: amended\namended_by: [\"[[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP]]\"]"
    )
    notice = "\n> [!IMPORTANT]\n> **Nghị định 214/2025/NĐ-CP đã được sửa đổi, bổ sung bởi [[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP]] ngày 09/09/2026** (sửa đổi các quy định về thu thập báo giá, tổ chuyên gia, hạn mức chỉ định thầu, quy trình rút gọn, hợp đồng, xử lý tình huống,...).\n"
    hub_text = hub_text.replace("## Mục lục chương", notice + "\n## Mục lục chương")
    nd214_hub.write_text(hub_text, encoding="utf-8")
    print("✓ Đã cập nhật nd-214-2025.md")

# 2. Cập nhật chuong-05.md của nd-214
ch5 = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\documents\nd-214-2025\chuong-05.md")
ch5_text = ch5.read_text(encoding="utf-8")

notice_dieu78 = "\n> [!NOTE]\n> **Lưu ý sửa đổi từ 09/09/2026 bởi [[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP (Điều 4)]]:**\n> - **Nâng hạn mức chỉ định thầu (khoản 4):** Dự toán mua sắm không hình thành dự án: lên **01 tỷ đồng** (cũ 500tr); Gói thầu tư vấn thuộc dự án: lên **03 tỷ đồng** (cũ 800tr); Gói thầu phi tư vấn, hàng hóa, xây lắp, hỗn hợp thuộc dự án: lên **05 tỷ đồng** (cũ 02 tỷ).\n> - Bổ sung điểm e1 khoản 2: Cho phép chỉ định thầu khi đấu thầu không có nhà thầu tham dự hoặc tất cả không đáp ứng.\n> - Mở rộng chỉ định thầu chuyển đổi số, CSDL quốc gia (điểm d khoản 3), giải phóng mặt bằng tái định cư (điểm c khoản 5), mua sắm thanh lý/phá sản/sàn giao dịch (điểm i, k khoản 5).\n\n"

if "Nghị định 349/2026/NĐ-CP" not in ch5_text:
    ch5_text = ch5_text.replace("**Điều 78. Các trường hợp chỉ định thầu**", "**Điều 78. Các trường hợp chỉ định thầu**\n" + notice_dieu78)
    
    notice_dieu79_80 = "\n> [!NOTE]\n> **Lưu ý sửa đổi từ 09/09/2026 bởi [[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP (Điều 5, 6)]]:**\n> - Chủ đầu tư không bắt buộc thẩm định hồ sơ yêu cầu và kết quả lựa chọn nhà thầu đối với chỉ định thầu thông thường.\n> - Quy định rõ chỉ định thầu rút gọn áp dụng cho trường hợp đấu thầu không thành công (điểm e1 khoản 2 Điều 78).\n\n"
    ch5_text = ch5_text.replace("**Điều 79. Quy trình chỉ định thầu thông thường**", "**Điều 79. Quy trình chỉ định thầu thông thường**\n" + notice_dieu79_80)
    ch5.write_text(ch5_text, encoding="utf-8")
    print("✓ Đã cập nhật chuong-05.md của NĐ 214")

# 3. Cập nhật chuong-01.md của nd-214
ch1 = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\documents\nd-214-2025\chuong-01.md")
ch1_text = ch1.read_text(encoding="utf-8")

notice_dieu18_21 = "\n> [!NOTE]\n> **Lưu ý sửa đổi từ 09/09/2026 bởi [[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP (Điều 1)]]:**\n> - Điểm d khoản 2 Điều 18: Đăng tải yêu cầu báo giá trên Hệ thống mạng đấu thầu quốc gia tối thiểu 03 ngày làm việc; cho phép lấy giá trung bình và loại trừ các báo giá chênh lệch > 30% giá trung bình. Miễn trừ trách nhiệm cho chủ đầu tư nếu đã thực hiện đúng quy trình công khai, minh bạch.\n\n"
notice_dieu21 = "\n> [!NOTE]\n> **Lưu ý sửa đổi từ 09/09/2026 bởi [[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP (Điều 2)]]:**\n> - Khoản 2, 2a Điều 21: Gói thầu KHCN, đổi mới sáng tạo, dự toán mua sắm không hình thành dự án hoặc chuyên gia chuyên ngành huy động thêm không bắt buộc phải có chứng chỉ nghiệp vụ chuyên môn về đấu thầu.\n\n"

if "Nghị định 349/2026/NĐ-CP" not in ch1_text:
    ch1_text = ch1_text.replace("**Điều 18. Xác định giá gói thầu**", "**Điều 18. Xác định giá gói thầu**\n" + notice_dieu18_21)
    ch1_text = ch1_text.replace("**Điều 21. Điều kiện năng lực, kinh nghiệm đối với tổ chuyên gia, tổ thẩm định**", "**Điều 21. Điều kiện năng lực, kinh nghiệm đối với tổ chuyên gia, tổ thẩm định**\n" + notice_dieu21)
    ch1.write_text(ch1_text, encoding="utf-8")
    print("✓ Đã cập nhật chuong-01.md của NĐ 214")

# 4. Cập nhật wiki/articles/dieu-23-chi-dinh-thau.md
art23 = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\articles\dieu-23-chi-dinh-thau.md")
art23_text = art23.read_text(encoding="utf-8")
if "nd-349-2026" not in art23_text:
    art23_text = art23_text.replace(
        "- [[nd-214-2025]] - Tổng quan nghị định hướng dẫn Luật Đấu thầu",
        "- [[nd-214-2025]] - Tổng quan nghị định hướng dẫn Luật Đấu thầu\n- [[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP]] - Nghị định sửa đổi NĐ 214 (nâng hạn mức chỉ định thầu lên 1 tỷ, 3 tỷ, 5 tỷ)"
    )
    art23.write_text(art23_text, encoding="utf-8")
    print("✓ Đã cập nhật dieu-23-chi-dinh-thau.md")

# 5. Cập nhật syntheses/thuc-tien-chi-dinh-thau-va-chi-dinh-rut-gon.md
syn_cđt = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\syntheses\thuc-tien-chi-dinh-thau-va-chi-dinh-rut-gon.md")
syn_text = syn_cđt.read_text(encoding="utf-8")
if "nd-349-2026" not in syn_text:
    syn_text = syn_text.replace(
        "[[nd-24-2024]], [[nd-214-2025]]",
        "[[nd-24-2024]], [[nd-214-2025]], [[documents/nd-349-2026|Nghị định 349/2026/NĐ-CP]]"
    )
    syn_text = syn_text.replace(
        "Hạn mức chỉ định thầu đối với gói thầu tư vấn (500tr), xây lắp/hàng hóa (1 tỷ)",
        "Hạn mức chỉ định thầu mới theo NĐ 349/2026: mua sắm không hình thành dự án (1 tỷ), tư vấn dự án (3 tỷ), xây lắp/hàng hóa/phi tư vấn dự án (5 tỷ)"
    )
    syn_cđt.write_text(syn_text, encoding="utf-8")
    print("✓ Đã cập nhật syntheses chỉ định thầu")

# 6. Cập nhật INDEX.md
idx_path = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\INDEX.md")
idx_text = idx_path.read_text(encoding="utf-8")
if "nd-349-2026" not in idx_text:
    doc_block = "- [[documents/nd-214-2025|nd-214-2025]] - Nghị định 214/2025/NĐ-CP (chi tiết Luật Đấu thầu)\n- [[documents/nd-349-2026|nd-349-2026]] - Nghị định 349/2026/NĐ-CP (sửa đổi, bổ sung NĐ 214/2025)\n- [[documents/tt-79-2025|tt-79-2025]] - Thông tư 79/2025/TT-BTC\n- [[documents/tt-80-2025|tt-80-2025]] - Thông tư 80/2025/TT-BTC\n"
    idx_text = idx_text.replace("## Documents\n\n_(Sẽ được tạo sau Tier 2)_", "## Documents\n\n" + doc_block)
    idx_path.write_text(idx_text, encoding="utf-8")
    print("✓ Đã cập nhật INDEX.md")

# 7. Cập nhật LOG.md
log_path = Path(r"D:\Antigravity\law-wiki-bidding-v2\wiki\LOG.md")
log_text = log_path.read_text(encoding="utf-8")
log_entry = """## 2026-09-14 - Ingest Nghị định 349/2026/NĐ-CP sửa đổi NĐ 214 (COMPLETE)

**Date:** 2026-09-14  
**Source:** `raw/nd-349.md`  
**Output:**
- Tạo tài liệu hub và nội dung chi tiết: `wiki/documents/nd-349-2026.md` (28 điều)
- Cập nhật ghi chú sửa đổi tại `wiki/documents/nd-214-2025.md`, `chuong-01.md`, `chuong-05.md`
- Cập nhật liên kết văn bản hướng dẫn tại `wiki/articles/dieu-23-chi-dinh-thau.md`
- Cập nhật cẩm nang `wiki/syntheses/thuc-tien-chi-dinh-thau-va-chi-dinh-rut-gon.md` với hạn mức mới (1 tỷ, 3 tỷ, 5 tỷ)
- Cập nhật mục lục `wiki/INDEX.md`

---

"""
log_path.write_text(log_entry + log_text, encoding="utf-8")
print("✓ Đã cập nhật LOG.md")
