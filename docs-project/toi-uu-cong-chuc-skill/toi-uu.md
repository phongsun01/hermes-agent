Bây giờ tách phần troubleshooting (đã gộp 2 đoạn Telerik trùng nhau) ra file reference riêng:Những gì mình đã tối ưu (từ 235 dòng 1 file → 118 dòng SKILL.md + 124 dòng reference riêng):

1. **Tách troubleshooting ra `references/troubleshooting.md`** — phần này chiếm gần nửa file gốc nhưng chỉ cần dùng khi gặp lỗi, không cần load vào context mỗi lần chạy `/cc list`. SKILL.md giờ chỉ trỏ tới file này khi cần (progressive disclosure).

2. **Gộp 2 đoạn Telerik RadDatePicker trùng lặp** (dòng 146-155 và 169-184 bản gốc) thành 1 mục duy nhất, đầy đủ hơn.

3. **Rút gọn quy tắc định dạng** — mục 1 và 2 (list/list today) trước đây lặp lại y hệt 3 quy tắc format, giờ nêu 1 lần và tham chiếu chéo.

4. **Thêm bảng lệnh nhanh** ở đầu file để tra cứu nhanh mà không phải đọc hết 10 mục.

5. **Cải thiện `description` trong frontmatter** — thêm các câu tự nhiên không đúng cú pháp slash command (vd "kết thúc giúp anh văn bản số 2534") để tăng khả năng skill được kích hoạt đúng ngay cả khi user không gõ `/cc` chuẩn.

6. **Tách rõ "slash command" vs "workflow thủ công"** (mục 8, 10 vốn không phải lệnh `/cc`) để tránh nhầm lẫn khi đọc.

Nội dung kỹ thuật, script path, logic xử lý giữ nguyên 100% — không có gì bị mất, chỉ tổ chức lại.

Nếu bạn muốn, mình có thể chạy vài test case thực tế (vd giả lập `/cc end 2534`, `/cc tomtat 2534`) để kiểm tra skill mới hoạt động đúng trước khi bạn deploy chính thức — bạn có muốn làm bước đó không?