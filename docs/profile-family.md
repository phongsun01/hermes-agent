# Tài liệu Hướng dẫn Profile Family & Cấu hình Zalo Group

Tài liệu này ghi chép chi tiết cách quản lý profile `family` trong hệ thống Hermes Agent, cùng các hướng dẫn cấu hình chi tiết để chạy song song tài khoản cá nhân và nhóm Zalo.

---

## 1. Cách tạo Profile `family`

Profile `family` được tạo ra nhằm xử lý các tác vụ dành riêng cho các thành viên trong gia đình mà không ảnh hưởng tới lịch sử hay tính cách (SOUL) của profile mặc định.

### Câu lệnh khởi tạo trên Windows:
```powershell
# Đặt biến môi trường HERMES_HOME về thư mục dữ liệu chung và khởi tạo profile
$env:HERMES_HOME="C:\Users\Desktop\.hermes"
py D:\Antigravity\Hermes\hermes_cli\main.py profile create family
```

### Cách đồng bộ API Key & Model từ Profile Default:
Vì profile được tạo mới tinh không kế thừa cấu hình cũ (để giữ nguyên cấu trúc thư mục sạch), chúng ta đã sao chép cấu hình mô hình và khóa kết nối (API keys) từ thư mục gốc của profile mặc định:
```powershell
# Sao chép file cấu hình YAML và biến môi trường .env
Copy-Item -Path "C:\Users\Desktop\.hermes\config.yaml" -Destination "C:\Users\Desktop\.hermes\profiles\family\config.yaml" -Force
Copy-Item -Path "C:\Users\Desktop\.hermes\.env" -Destination "C:\Users\Desktop\.hermes\profiles\family\.env" -Force
```

---

## 2. Danh sách các đường dẫn quan trọng

* **Thư mục dữ liệu Profile mặc định (`default`)**: 
  `C:\Users\Desktop\.hermes\`
* **Thư mục chứa các Profile phụ**: 
  `C:\Users\Desktop\.hermes\profiles\`
* **Thư mục dữ liệu riêng của Profile `family`**: 
  `C:\Users\Desktop\.hermes\profiles\family\`
* **Tệp cấu hình của `family`**: 
  `C:\Users\Desktop\.hermes\profiles\family\config.yaml`
* **Tệp API Key của `family`**: 
  `C:\Users\Desktop\.hermes\profiles\family\.env`
* **Tệp tính cách (SOUL) của `family`**: 
  `C:\Users\Desktop\.hermes\profiles\family\SOUL.md` *(Bạn có thể chỉnh sửa tệp này để cá nhân hóa chỉ dẫn của trợ lý gia đình)*

---

## 3. Cách chat thử với Profile `family`

Do CLI chạy trên Windows Host không được đăng ký biến toàn cục tự động, bạn cần sử dụng đường dẫn tuyệt đối của Python để tương tác:

### Lệnh chạy trực tiếp từ PowerShell:
```powershell
$env:HERMES_HOME="C:\Users\Desktop\.hermes"; py D:\Antigravity\Hermes\hermes_cli\main.py -p family chat
```

### Thiết lập Alias phím tắt trong PowerShell (Tiện lợi hơn):
Chạy các dòng sau trong cửa sổ PowerShell hiện tại để tạo lệnh gõ nhanh:
```powershell
# Tạo phím tắt cho lệnh chính hermes
function hermes { py D:\Antigravity\Hermes\hermes_cli\main.py $args }

# Tạo phím tắt riêng cho profile family
function family { 
    $env:HERMES_HOME="C:\Users\Desktop\.hermes"
    py D:\Antigravity\Hermes\hermes_cli\main.py -p family $args 
}
```
Sau khi khai báo, bạn chỉ cần gõ lệnh sau để bắt đầu chat:
```powershell
family chat
```

---

## 4. Cách cấu hình Profile Nhóm Zalo

Nếu muốn sử dụng profile `family` chuyên trách việc phản hồi tự động trong các **Nhóm Zalo gia đình**, bạn có thể cấu hình cơ chế lọc tin nhắn để tránh xung đột với các hoạt động cá nhân của profile `default`.

Chỉnh sửa tệp môi trường của từng profile:

### Cấu hình cho Profile Cá nhân (`default`)
*(Chỉ chat 1-1 với bạn, bỏ qua toàn bộ nhóm)*
Sửa tệp `C:\Users\Desktop\.hermes\.env` và cấu hình:
```env
ZALO_GROUP_MODE=off
ZALO_ALLOWED_USERS=2825656851207986406   # ID Zalo cá nhân của bạn
ZALO_ALLOWED_THREADS=2825656851207986406 # Chỉ hoạt động tại khung chat riêng của bạn
```

### Cấu hình cho Profile Gia đình (`family`)
*(Chỉ phản hồi khi được tag tên trong các nhóm gia đình cụ thể)*
Sửa tệp `C:\Users\Desktop\.hermes\profiles\family\.env` và cấu hình:
```env
ZALO_GROUP_MODE=mention                  # Chỉ trả lời khi được nhắc tên (@bot)
ZALO_ALLOWED_USERS=                      # Để trống để cho phép mọi thành viên trong nhóm gọi bot
ZALO_ALLOWED_THREADS=ID_NHOM_1,ID_NHOM_2 # Điền danh sách ID nhóm gia đình (phân cách bằng dấu phẩy)
```

### Khởi chạy song song 2 Gateway:
```powershell
# Khởi chạy Zalo gateway cho cá nhân (default)
$env:HERMES_HOME="C:\Users\Desktop\.hermes"; py D:\Antigravity\Hermes\hermes_cli\main.py gateway start

# Khởi chạy Zalo gateway cho gia đình (family)
$env:HERMES_HOME="C:\Users\Desktop\.hermes"; py D:\Antigravity\Hermes\hermes_cli\main.py -p family gateway start
```

---

## 5. Cách lấy ID nhóm Zalo (Thread ID)

Để lấy được ID chính xác của nhóm chat Zalo và đưa vào bộ lọc `ZALO_ALLOWED_THREADS`, bạn có hai phương án:

### Phương án A: Xem từ Log hệ thống (Khuyên dùng)
1. Thêm biến môi trường ghi nhận log ID vào tệp cấu hình `.env` của profile:
   ```env
   ZALO_LOG_IDS=true
   ```
2. Khởi động lại Zalo gateway.
3. Vào nhóm Zalo cần lấy ID, gửi một tin nhắn bất kỳ (hoặc tag bot).
4. Xem lịch sử log:
   * Nếu chạy trực tiếp trên máy host: Mở tệp log tại `C:\Users\Desktop\.hermes\logs\agent.log`.
   * Nếu chạy qua Docker container: Chạy lệnh `docker logs hermes --tail 50`.
5. Tìm dòng ghi nhận tin nhắn đến có cấu trúc:
   ```text
   Zalo inbound: uid=2825656851207986406 name='Nguyen Van A' threadId=58291048571029381 type=group
   ```
   Dãy số tại mục **`threadId`** (`58291048571029381`) chính là ID nhóm bạn cần tìm.

### Phương án B: Hỏi trực tiếp Bot Zalo
Nếu bot đã được thêm vào nhóm và đang ở chế độ hoạt động (`ZALO_GROUP_MODE=mention` hoặc `all` và chưa chặn thread):
1. Tag bot trong nhóm chat và gửi tin nhắn: 
   > *"@Bot ơi, ID của nhóm chat này là bao nhiêu?"* hoặc *"Hãy in ra metadata thread_id của phòng chat này từ ngữ cảnh hệ thống."*
2. Bot sẽ tự động trích xuất biến `chat_id` từ dữ liệu đầu vào của adapter và phản hồi lại ID chính xác cho bạn.

---

## 6. Nhật ký xử lý sự cố thực tế & Khắc phục lỗi

Trong quá trình khởi chạy thực tế, một số lỗi cấu hình và hệ thống tệp tin đã phát sinh và được khắc phục như sau:

### Lỗi 1: Không kết nối được Zalo, chỉ hiển thị kết nối `api_server`
* **Nguyên nhân**: Do profile `family` được tạo mới tinh không kế thừa các plugin tùy chỉnh. Plugin Zalo (`zalo-platform`) nằm trong thư mục `plugins/` của profile mặc định không tự động sao chép sang profile mới.
* **Cách xử lý**: Tạo thư mục `plugins` và sao chép thủ công plugin `zalo` từ profile mặc định sang:
  ```powershell
  New-Item -ItemType Directory -Path "C:\Users\Desktop\.hermes\profiles\family\plugins" -Force
  Copy-Item -Recurse -Path "C:\Users\Desktop\.hermes\plugins\zalo" -Destination "C:\Users\Desktop\.hermes\profiles\family\plugins\zalo" -Force
  ```

### Lỗi 2: Container Docker khởi động lại liên tục (SIGTERM Loop) do kẹt lock log
* **Nguyên nhân**: Khi thực hiện khởi động lại (restart) container Docker trên môi trường Windows Host mount thư mục, tiến trình s6-log cũ giữ khóa tệp tin `lock` bị chết lâm sàng. Windows giữ tệp tin ở trạng thái "chờ xóa" (delete-pending), khiến tiến trình s6-log mới khởi động báo lỗi: `s6-log: fatal: unable to open .../lock: No such file or directory`.
* **Cách xử lý**:
  1. Tạm dừng các container đang mount thư mục (bao gồm cả Dashboard vì nó dùng chung dữ liệu):
     ```powershell
     docker stop hermes-dashboard hermes
     ```
  2. Đổi tên thư mục log cũ để giải phóng lock kẹt của Windows (hệ thống s6 sẽ tự tạo lại thư mục mới sạch sẽ):
     ```powershell
     Rename-Item -Path "C:\Users\Desktop\.hermes\logs\gateways\default" -NewName "default-old" -Force
     Rename-Item -Path "C:\Users\Desktop\.hermes\logs\gateways\family" -NewName "family-old" -Force
     ```
  3. Khởi chạy lại các container:
     ```powershell
     docker start hermes hermes-dashboard lightrag
     ```
* **Kết quả**: Gateway khởi động trơn tru, nhận diện đầy đủ cả 2 profile và kết nối Zalo thành công.

