# Hướng dẫn tích hợp Telegram và Chạy giao diện TUI cho Hermes

Tài liệu này hướng dẫn cách kết nối Hermes Agent với Telegram và cách thiết lập môi trường để chạy giao diện TUI (Terminal User Interface) trên Windows.

---

## 1. Tích hợp Telegram Bot

Để kết nối Hermes Agent với Telegram, bạn cần thực hiện các bước sau:

### Bước 1: Lấy thông tin từ Telegram
1. Nhắn tin cho **@BotFather** trên Telegram, gửi lệnh `/newbot` và làm theo hướng dẫn để tạo bot. Sau đó, sao chép **API Token**.
2. Nhắn tin cho **@userinfobot** để lấy **User ID** (số định danh) của bạn.

### Bước 2: Cấu hình Hermes
Mở file cấu hình môi trường tại đường dẫn: `C:\Users\Desktop\.hermes\.env` (hoặc `%USERPROFILE%\.hermes\.env`).

Thêm hoặc cập nhật các biến sau với thông tin của bạn:
```env
TELEGRAM_BOT_TOKEN=8799237321:AAH0pAZzJAmlJE7sn6fq1p1i94YyYKTPpQo
TELEGRAM_ALLOWED_USERS=5511250191
```

### Bước 3: Áp dụng thay đổi
Nếu bạn đang chạy Hermes qua Docker, hãy khởi động lại service gateway:
```powershell
docker compose restart gateway
```

---

## 2. Cách chạy giao diện TUI (Terminal User Interface)

Giao diện TUI cung cấp trải nghiệm tương tác hiện đại và trực quan ngay trong cửa sổ dòng lệnh.

### Cách 1: Sử dụng Command Prompt (CMD) - Khuyên dùng trên Windows
Mở CMD và chạy các lệnh sau theo thứ tự:
```cmd
# Di chuyển vào thư mục dự án
cd /d D:\Antigravity\Hermes

# Tạo môi trường ảo (nếu chưa có)
py -m venv .venv

# Kích hoạt môi trường ảo
.venv\Scripts\activate.bat

# Cài đặt Hermes ở chế độ editable (chỉ cần làm lần đầu)
pip install -e .

# Chạy giao diện TUI
hermes --tui
```

### Cách 2: Sử dụng PowerShell
Nếu PowerShell chặn việc chạy script kích hoạt, hãy thực hiện các bước sau:

1. **Cho phép chạy script** (chỉ cần thực hiện một lần duy nhất):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **Cài đặt và khởi chạy**:
   ```powershell
   cd D:\Antigravity\Hermes
   py -m venv .venv
   .\.venv\Scripts\activate
   pip install -e .
   hermes --tui
   ```

---

## Các lưu ý quan trọng:
* **Terminal**: Giao diện TUI hiển thị tốt nhất trên **Windows Terminal** (tải từ Microsoft Store). CMD hoặc PowerShell mặc định có thể không hiển thị đúng màu sắc và emoji.
* **Lệnh điều khiển**: Trong TUI, bạn có thể gõ `/` để xem danh sách các lệnh nhanh (slash commands).
* **Thoát**: Nhấn `Ctrl + C` hoặc gõ `/exit` để thoát khỏi Hermes.

---

## 3. Các lỗi thường gặp trên Windows và cách xử lý

Trong quá trình cài đặt và chạy Hermes trên Windows, bạn có thể gặp một số lỗi đặc thù sau đây (đã được xử lý trong mã nguồn):

### Lỗi `'chmod' is not recognized`
Lỗi này xảy ra khi hệ thống cố gắng chạy lệnh cấp quyền của Linux trên Windows.
*   **Nguyên nhân**: Script build trong `ui-tui/package.json` chứa lệnh Linux.
*   **Cách xử lý**: Đã được loại bỏ trong file `package.json`. Nếu bạn tự sửa, hãy xóa phần `&& chmod +x dist/entry.js` trong dòng `build`.

### Lỗi `AttributeError: module 'signal' has no attribute 'SIGPIPE'`
Đây là lỗi phổ biến nhất khi chạy TUI trên Windows do sự khác biệt về cách quản lý tín hiệu (signals) của hệ điều hành.
*   **Nguyên nhân**: Python trên Windows không hỗ trợ các tín hiệu `SIGPIPE` hoặc `SIGHUP`.
*   **Cách xử lý**: Mã nguồn trong `tui_gateway/entry.py` đã được cập nhật để kiểm tra `hasattr(signal, "SIGPIPE")` trước khi sử dụng.

### Lỗi `TUI build failed`
Nếu quá trình build TUI thất bại, hãy đảm bảo bạn đã cài đặt **Node.js** và chạy `npm install` trong thư mục `ui-tui`.

---

## 4. Các mẹo cấu hình Docker & Telegram nâng cao

### Kết nối với AI Server chạy trên máy chủ (Host)
Nếu bạn chạy các service như **9Router**, **Ollama**, hoặc **vLLM** trực tiếp trên Windows (không phải trong Docker) và muốn Hermes (trong Docker) kết nối tới:
*   **Sai**: `http://127.0.0.1:20128/v1` hoặc `localhost` (Docker sẽ tự hiểu là kết nối bên trong chính nó).
*   **Đúng**: `http://host.docker.internal:20128/v1`.
*   **Địa chỉ này** giúp Docker container "nhìn thấy" các dịch vụ đang chạy trên máy tính Windows của bạn.

### Thiết lập Home Channel thủ công cho Telegram
Home Channel là nơi Hermes gửi các kết quả chạy tự động (cron) hoặc thông báo hệ thống. Thay vì dùng lệnh `/sethome`, bạn có thể cấu hình cứng trong `.env`:
1. Tìm User ID của bạn (qua `@userinfobot`).
2. Mở file `.env` và thêm:
   ```env
   TELEGRAM_HOME_CHANNEL=your_user_id
   ```

### Cách Restart Gateway nhanh
Mỗi khi sửa file `.env` hoặc `config.yaml`, bạn phải restart để áp dụng:
```powershell
docker compose restart gateway
```
Lệnh này sẽ khởi động lại dịch vụ gateway mà không làm ảnh hưởng đến các dịch vụ khác (như dashboard).

