# Tài Liệu Hướng Dẫn Tích Hợp Tool & Skill XSMB

Tài liệu này mô tả cấu trúc và tác dụng của các tệp tin liên quan đến tính năng Xem và Thống kê Xổ số Miền Bắc (XSMB) trên Hermes Agent.

---

## 📂 Sơ Đồ Cấu Trúc Các File Liên Quan

```
hermes-agent/
├── tools/
│   └── xsmb_tool.py             # [NEW] Đăng ký Core Tool `get_xsmb` và `predict_xsmb` với Agent
├── toolsets.py                  # [MODIFY] Thêm các tool xsmb vào bộ công cụ cốt lõi
├── scripts/
│   └── xsmb/
│       ├── xsmb_db.py           # [NEW] Quản lý SQLite DB kết quả xổ số
│       ├── xsmb_fetcher.py      # [NEW] Crawl dữ liệu và parse từ Web
│       ├── xsmb_init.py         # [NEW] Khởi tạo dữ liệu lịch sử (tháng 6/2026)
│       ├── pascal_mc.py         # [NEW] Tính cầu Pascal & giả lập Monte Carlo
│       ├── xsmb_lstm_pascal.py  # [NEW] Mạng LSTM lai kết hợp tính năng cầu Pascal
│       └── xsmb_results.db      # [NEW] Cơ sở dữ liệu SQLite lưu trữ kết quả xổ số
└── docs/
    └── xsmb-tool-skill-documentation.md  # [NEW] Tài liệu hướng dẫn này

~/.hermes/ (User Profile)
└── skills/
    └── xs/
        └── SKILL.md             # [NEW] Định hình lệnh gạch chéo `/xs` và lô tô
```

---

## 🔍 Mô Tả Chi Tiết Tác Dụng Từng File

### 1. Phần Core Tool (Mã nguồn Hermes Core)

#### 🔹 [tools/xsmb_tool.py](file:///d:/Antigravity/Hermes/tools/xsmb_tool.py)
*   **Tác dụng:** Đăng ký công cụ `get_xsmb` và `predict_xsmb` vào hệ thống thông qua `registry.register()`.
*   **Chức năng:** 
    *   `get_xsmb`: Nhận các tham số `date` (ngày cụ thể) và `limit_days` (lấy nhiều ngày để làm thống kê). Gọi hàm trong thư viện `scripts/xsmb` để lấy dữ liệu tương ứng trả về cho LLM.
    *   `predict_xsmb`: Nhận tham số `last_days` (số ngày làm mẫu). Gọi trực tiếp thuật toán trong `pascal_mc.py` để tính toán và trả về kết quả dự đoán dạng JSON.

#### 🔹 [toolsets.py](file:///d:/Antigravity/Hermes/toolsets.py) (Chỉnh sửa)
*   **Tác dụng:** Thêm `"get_xsmb"` và `"predict_xsmb"` vào biến `_HERMES_CORE_TOOLS`.
*   **Chức năng:** Đảm bảo cả hai công cụ luôn được kích hoạt mặc định trên mọi giao diện (Zalo, Telegram, CLI...).

---

### 2. Phần Nghiệp Vụ & Lưu Trữ (Thư mục scripts/xsmb)

#### 🔹 [scripts/xsmb/xsmb_db.py](file:///d:/Antigravity/Hermes/scripts/xsmb/xsmb_db.py)
*   **Tác dụng:** Quản lý cơ sở dữ liệu SQLite lưu kết quả xổ số.
*   **Chức năng:** Khởi tạo bảng `xsmb` và cung cấp các hàm lưu kết quả (`save_result`), đọc kết quả (`get_result`).

#### 🔹 [scripts/xsmb/xsmb_fetcher.py](file:///d:/Antigravity/Hermes/scripts/xsmb/xsmb_fetcher.py)
*   **Tác dụng:** Thu thập và chuẩn hóa dữ liệu.
*   **Chức năng:** Gửi HTTP request đến trang `xskt.com.vn` lấy mã nguồn HTML, dùng Regex bóc tách 8 giải xổ số (Đặc biệt đến Giải 7), sau đó lưu vào SQLite DB qua `xsmb_db.py`.

#### 🔹 [scripts/xsmb/xsmb_init.py](file:///d:/Antigravity/Hermes/scripts/xsmb/xsmb_init.py)
*   **Tác dụng:** Tạo dữ liệu lịch sử ban đầu.
*   **Chức năng:** Tự động chạy vòng lặp từ ngày `01-06-2026` đến `30-06-2026` để nạp dữ liệu lịch sử 30 ngày vào SQLite.

#### 🔹 [scripts/xsmb/xsmb_results.db](file:///d:/Antigravity/Hermes/scripts/xsmb/xsmb_results.db)
*   **Tác dụng:** Lưu trữ dữ liệu.
*   **Chức năng:** File SQLite chứa toàn bộ kết quả XSMB.

#### 🔹 [scripts/xsmb/pascal_mc.py](file:///d:/Antigravity/Hermes/scripts/xsmb/pascal_mc.py)
*   **Tác dụng:** Dự đoán cầu Pascal kết hợp với mô phỏng Monte Carlo dựa trên phân phối thực tế.
*   **Chức năng:** Đọc dữ liệu từ SQLite DB, dựng DataFrame mô phỏng các cột kết quả, tính toán cầu Pascal cho kỳ quay gần nhất, đồng thời chạy 20,000 lượt giả lập Monte Carlo dựa trên trọng số phân phối của 30 ngày trước đó để đưa ra top 10 con số có xác suất xuất hiện cao nhất.

#### 🔹 [scripts/xsmb/xsmb_lstm_pascal.py](file:///d:/Antigravity/Hermes/scripts/xsmb/xsmb_lstm_pascal.py)
*   **Tác dụng:** Mô hình học sâu LSTM lai kết hợp tính năng cầu Pascal làm đầu vào.
*   **Chức năng:** Thiết kế dữ liệu chuỗi thời gian đầu vào 200 chiều (100 chiều presence vector thực tế + 100 chiều one-hot vector đại diện cho kết quả cầu Pascal ngày hôm đó). Mạng LSTM học mối tương quan sâu giữa cầu Pascal và kết quả thực tế qua thời gian để dự báo xác suất của 100 cặp số cho ngày kế tiếp.

---

### 3. Phần Định Hình Kịch Bản Hành Vi (User Skills)

#### 🔹 [C:\Users\Desktop\.hermes\skills\xs\SKILL.md](file:///C:/Users/Desktop/.hermes/skills/xs/SKILL.md)
*   **Tác dụng:** Định nghĩa lệnh `/xs` và hướng dẫn Agent hoạt động.
*   **Chức năng:** 
    *   Khai báo mô tả của slash command trên giao diện chat Zalo.
    *   Hướng dẫn LLM cách chuyển đổi linh hoạt định dạng ngày từ ngôn ngữ tự nhiên thành `dd-mm-yyyy` để gọi Tool.
    *   Cung cấp thuật toán phân tích xác suất lô tô (cách đếm 2 số cuối, lọc top 5 lô ra nhiều nhất/ít nhất) để LLM thực hiện phân tích mỗi khi nhận lệnh `/xs lo <số ngày>`.
