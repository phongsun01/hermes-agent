# Đề xuất tích hợp tính năng Tự động điền Form (Autofill) trên Mua Sắm Công

Tài liệu này đề xuất phương án và các bước chuẩn bị để tích hợp công cụ tự động điền form (autofill) của extension [GrafosAI-Autofill](https://github.com/phongsun01/GrafosAI-Autofill) với **Hermes Agent**.

---

## 💡 1. Phân tích giải pháp kết nối

Hệ thống mạng đấu thầu quốc gia (Mua Sắm Công) yêu cầu chứng thư số (USB Token / Chữ ký số công cộng) và chạy trong môi trường trình duyệt thực tế của người dùng. Do đó, việc dùng Hermes chạy ngầm (headless browser như Puppeteer/Playwright) để submit form trực tiếp là rất khó khăn và rủi ro.

Giải pháp tối ưu nhất là **kết hợp sức mạnh của cả hai bên**:
- **Hermes Agent (Backend/AI)**: Đọc hồ sơ thầu, xử lý file dự thầu (PDF, Excel), trích xuất các thông tin cần thiết (tên hàng, đơn giá, thông số kỹ thuật, thông tin doanh nghiệp) và chuyển đổi thành cấu trúc JSON chuẩn hóa.
- **GrafosAI-Autofill Extension (Frontend/Browser)**: Lấy dữ liệu JSON từ Hermes và tự động điền (autofill) vào các trường input tương ứng trên giao diện trang Mua Sắm Công khi người dùng đang mở trang đó trên máy cá nhân.

Chúng ta có 2 phương án kết nối chính:

| Phương án | Cách thức hoạt động | Ưu điểm | Nhược điểm |
| :--- | :--- | :--- | :--- |
| **Phương án 1: Local HTTP API (Khuyến nghị)** | Hermes (hoặc một plugin phụ) chạy một server cục bộ siêu nhẹ (ví dụ Flask/FastAPI tại `http://localhost:8000`). Extension khi click sẽ tự động gọi API này để lấy dữ liệu autofill mới nhất mà Hermes vừa trích xuất. | Trải nghiệm 1-click mượt mà, không cần copy-paste thủ công. | Cần cấu hình CORS cho extension và người dùng phải chạy local server. |
| **Phương án 2: Clipboard / Copy-Paste Payload** | Hermes trích xuất dữ liệu xong sẽ in ra một đoạn JSON chuẩn và tự động copy vào Clipboard (hoặc người dùng bấm copy). Trên extension có nút "Import JSON" để dán vào và tự động điền. | Rất dễ triển khai, không cần mở cổng port hay chạy server phụ, bảo mật cao. | Thêm 1 thao tác copy-paste thủ công của người dùng. |

---

## 📋 2. Những việc cần chuẩn bị

### Về phía Extension (GrafosAI-Autofill):
1. **Định nghĩa JSON Schema chuẩn**: Xác định chính xác cấu trúc dữ liệu đầu vào cho các form trên Mua Sắm Công (ví dụ: form Đăng ký thông tin nhà thầu, form Nhập đơn giá chi tiết TBMT, form KHLCNT).
2. **Xây dựng API Client / Nhận dữ liệu**:
   - *Nếu theo PA1*: Thêm tính năng fetch từ `http://localhost:8000/api/msc/autofill`.
   - *Nếu theo PA2*: Thêm ô nhập liệu JSON (Textarea) hoặc tự động đọc từ clipboard khi người dùng nhấn nút "Paste & Fill".
3. **Selector Mapping**: Đảm bảo các hàm tìm kiếm selector (`document.querySelector`) trên trang Mua Sắm Công hoạt động ổn định và chính xác với cấu trúc DOM hiện tại của trang.

### Về phía Hermes Agent:
1. **Tạo MSC Autofill Tool**: Xây dựng một công cụ mới (ví dụ: `extract_msc_form_data`) có nhiệm vụ đọc tài liệu đầu vào (PDF/Word/Excel do người dùng tải lên) và dùng LLM để trích xuất ra đúng định dạng JSON Schema mà Extension yêu cầu.
2. **Cấu hình Local Endpoint (nếu dùng PA1)**: Mở rộng plugin web server của Hermes hoặc tạo một micro-service chạy ngầm trên máy để lưu trữ tạm thời (cache) dữ liệu form vừa trích xuất.

---

## 🛠️ 3. Các bước triển khai chi tiết

### Bước 1: Thống nhất cấu trúc dữ liệu (Data Contract)
Hai bên cần thống nhất một file JSON mẫu đại diện cho form. Ví dụ mẫu cho form nhập thông số kỹ thuật/đơn giá:
```json
{
  "form_type": "web_dauthau_tbmt_detail",
  "items": [
    {
      "item_no": 1,
      "name": "Máy tính xách tay Dell Latitude",
      "specification": "CPU Intel Core i7, RAM 16GB, SSD 512GB",
      "unit": "Cái",
      "quantity": 10,
      "unit_price": 25000000
    }
  ]
}
```

### Bước 2: Nâng cấp GrafosAI-Autofill Extension
- Viết hàm `autofillForm(jsonData)` nhận cấu trúc trên, duyệt qua từng item và điền vào các bảng grid/trường nhập liệu trên trang Mua Sắm Công.
- Thêm giao diện popup/options cho phép chọn nguồn dữ liệu: "Lấy từ Hermes Local" hoặc "Dán mã JSON".

### Bước 3: Phát triển Skill & Tool trên Hermes
- Tạo file `skills/productivity/msc/lib/msc_tool/autofill_extractor.py` thực hiện đọc file đính kèm bằng các thư viện sẵn có của Hermes (pdfplumber, openpyxl).
- Dùng LLM với Prompt chuyên biệt để chuyển thông tin thô thành cấu trúc JSON đã thống nhất ở Bước 1.
- Lưu trữ kết quả này vào cơ sở dữ liệu tạm thời hoặc clipboard.

---

## 🎯 4. Kết quả mong muốn (User Experience)

1. **Bước 1 (Đưa dữ liệu cho AI)**: Người dùng tải lên file quyết định phê duyệt dự án/dự toán (PDF/Excel) vào khung chat Hermes và gõ:
   > `/msc trich-xuat-form`
2. **Bước 2 (AI xử lý)**: Hermes phân tích file, hiển thị bảng xem trước (preview) của dữ liệu đã trích xuất để người dùng kiểm tra và xác nhận.
3. **Bước 3 (Tự động điền)**:
   - Người dùng mở trang nhập liệu tương ứng trên trang Mua Sắm Công.
   - Nhấp vào biểu tượng Extension **GrafosAI-Autofill** trên trình duyệt và bấm **"Autofill từ Hermes"** (hoặc dán JSON).
   - Toàn bộ dữ liệu (có thể lên tới hàng trăm dòng thầu) được tự động điền vào form chỉ trong vài giây với độ chính xác tuyệt đối, tránh hoàn toàn việc nhập liệu thủ công sai sót.
