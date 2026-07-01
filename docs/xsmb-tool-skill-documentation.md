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

---

## 🐳 4. Cấu Hình Đặc Thù Trong Môi Trường Docker (Cập nhật 01/07/2026)

### ⚠️ Vấn đề giới hạn Mount của Container
Trong môi trường chạy thực tế:
*   Mã nguồn phát triển ở `D:\Antigravity\Hermes` **không** được mount trực tiếp vào container Docker.
*   Container `hermes` chỉ mount duy nhất thư mục cá nhân: `C:\Users\Desktop\.hermes` -> `/opt/data` bên trong container.
*   Do đó, các chỉnh sửa trực tiếp vào mã nguồn Core Tool hoặc `toolsets.py` của dự án sẽ **không** được phản ánh lên Zalo Bot chạy trong Docker.

### 💡 Giải pháp: Đóng gói Custom Plugin
Để vượt qua giới hạn trên, toàn bộ code backend của xổ số đã được đóng gói thành một **Custom Plugin** đặt trong thư mục được mount của user profile:
*   **Đường dẫn plugin:** [C:\Users\Desktop\.hermes\plugins\xsmb](file:///C:/Users/Desktop/.hermes/plugins/xsmb)

#### Cấu trúc file của Plugin:
```
C:\Users\Desktop\.hermes\plugins\xsmb/
├── plugin.yaml          # Định nghĩa plugin và khai báo các tool `get_xsmb` & `predict_xsmb`
├── __init__.py          # Đăng ký các hàm xử lý của tool vào registry của Agent tại thời điểm boot
├── xsmb_db.py           # Quản lý SQLite DB kết quả xổ số (DB_PATH trỏ về thư mục plugin)
├── xsmb_fetcher.py      # Tải và parse kết quả xổ số từ Web
├── pascal_mc.py         # Dự đoán cầu Pascal và Monte Carlo
├── xsmb_lstm_pascal.py  # Dự đoán học sâu LSTM + Pascal
└── xsmb_results.db      # Cơ sở dữ liệu SQLite chứa kết quả đã cào
```

#### Cách hoạt động:
Khi container `hermes` khởi động lại, nó sẽ tự động quét thư mục `/opt/data/plugins/xsmb` (tương ứng với `C:\Users\Desktop\.hermes\plugins\xsmb`), đọc file `plugin.yaml`, chạy file `__init__.py` để đăng ký các tool `get_xsmb` và `predict_xsmb` vào hệ thống một cách độc lập mà không cần can thiệp hay sửa đổi bất kỳ file Core nào trong mã nguồn gốc.

---

## 🐛 5. Nhật Ký Sửa Lỗi (01/07/2026)

Sau khi khởi động lại container, Zalo bot vẫn báo "tool `get_xsmb` chưa có". Quá trình debug đã xác định được **3 tầng lỗi xếp chồng** cần giải quyết theo thứ tự:

---

### Lỗi 1: Plugin chưa được kích hoạt

**Triệu chứng:** `hermes plugins list` hiển thị plugin `xsmb` ở trạng thái `not enabled`.

**Nguyên nhân:** Hermes plugin theo cơ chế **opt-in** — plugin mới được thêm vào sẽ mặc định ở trạng thái tắt, kể cả khi code đã có trong thư mục.

**Cách sửa:**
```bash
docker exec hermes hermes plugins enable xsmb
docker restart hermes
```

---

### Lỗi 2: Thiếu thư viện Python trong venv của container

**Triệu chứng:** Sau khi kích hoạt plugin, log hiện:
```
Failed to load plugin 'xsmb': No module named 'pandas'
```

**Nguyên nhân:** Plugin `xsmb` dùng `pandas`, `numpy`, `torch` — nhưng môi trường Python ảo của container (`/opt/hermes/.venv`) là một môi trường cô lập riêng, **không chia sẻ** các thư viện đã cài trên máy thật.

**Cách sửa:** Dùng `uv` (trình quản lý gói có sẵn trong container) để cài đặt trực tiếp vào venv của container:
```bash
docker exec hermes uv pip install pandas numpy torch \
  --extra-index-url https://download.pytorch.org/whl/cpu
```

> ⚠️ **Lưu ý quan trọng:** Các thư viện cài bằng `uv pip install` trực tiếp vào container sẽ **bị mất** mỗi khi image Docker được build lại. Để cố định, cần thêm vào `Dockerfile` hoặc dùng volume mount riêng cho site-packages.

---

### Lỗi 3: Platform Zalo không được gán toolset `xsmb`

**Triệu chứng:** Sau khi plugin load OK (kiểm tra bằng `python -c "import model_tools; ..."` trả về `True`), Zalo bot vẫn báo tool chưa có. Hỏi bot xem tool gì có sẵn → không thấy `get_xsmb`.

**Nguyên nhân (gốc rễ):** Trong `~/.hermes/config.yaml` có phần `platform_toolsets` định nghĩa **riêng biệt** danh sách toolset cho từng platform. Platform `zalo` không được liệt kê trong phần này nên nhận toolset mặc định — vốn không bao gồm `xsmb`.

**Cách sửa:** Thêm mục `zalo` vào `platform_toolsets` trong `~/.hermes/config.yaml`:
```yaml
platform_toolsets:
  cli:
  - hermes-cli
  telegram:
  - hermes-telegram
  # ... các platform khác ...
  zalo:        # <-- Thêm mục này
  - hermes-cli
  - xsmb
```
Sau đó `docker restart hermes`.

---

### Lỗi 4 (Phụ): SKILL.md hướng dẫn sai

**Triệu chứng:** Dù tool đã được đăng ký, bot vẫn báo cáo "tool chưa có" và đề xuất dùng browser thay thế.

**Nguyên nhân:** File `SKILL.md` cũ có dòng `⚠️ Quan trọng: Skill này... các tool đó **chưa được triển khai**`. Bot đọc hướng dẫn này và tin theo, bỏ qua tool thực tế trong registry.

**Cách sửa:** Xóa dòng cảnh báo sai, cập nhật SKILL.md thành v2.0 hướng dẫn bot:
- Gọi trực tiếp `get_xsmb({...})` với cú pháp tham số rõ ràng
- Gọi trực tiếp `predict_xsmb({...})` với tham số `last_days`
- Chỉ dùng browser làm dự phòng khi tool báo lỗi

---

### Tóm tắt danh sách file cần kiểm tra khi tích hợp tool mới cho Zalo bot

| File / Nơi kiểm tra | Nội dung cần xác nhận |
|---|---|
| `docker exec hermes hermes plugins list` | Plugin ở trạng thái `enabled` |
| `docker exec hermes uv pip list` | Các thư viện Python cần thiết đã cài |
| `~/.hermes/config.yaml` → `platform_toolsets.zalo` | Toolset của plugin đã được gán cho platform `zalo` |
| `~/.hermes/skills/<skill>/SKILL.md` | Không có cảnh báo "tool chưa có", hướng dẫn gọi tool đúng cú pháp |


