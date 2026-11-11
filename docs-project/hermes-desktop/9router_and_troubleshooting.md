# Cấu hình Kết nối 9router & Khắc phục Lỗi (Cheat Sheet)

## 1. Thông số kết nối

```yaml
# Đường dẫn file cấu hình: C:\Users\Desktop\AppData\Local\hermes\config.yaml

model:
  default: 9router-combo
  provider: custom
  base_url: http://127.0.0.1:20128/v1
  api_mode: chat_completions
  api_key: sk-52322c0dd90d1c8a-2iry8g-ebb67c15

custom_providers:
  - name: Local (localhost:20128)
    base_url: http://127.0.0.1:20128/v1
    api_key: sk-52322c0dd90d1c8a-2iry8g-ebb67c15
    model: 9router-combo
```

Và trong file `C:\Users\Desktop\AppData\Local\hermes\.env`:
```bash
CUSTOM_API_KEY=sk-52322c0dd90d1c8a-2iry8g-ebb67c15
```

---

## 2. Kiểm tra nhanh bằng dòng lệnh

### Kiểm tra 9router còn sống không:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:20128/v1/models" -Headers @{ Authorization = "Bearer sk-52322c0dd90d1c8a-2iry8g-ebb67c15" }
```

### Kiểm tra Gateway & Test Chat:
```powershell
hermes gateway ensure
hermes chat -q "chào bạn"
```

### Khởi động lại Gateway nếu thay đổi cấu hình:
```powershell
hermes gateway restart
```

---

## 3. Đồng bộ nhanh Skills/Plugins khi có cập nhật trong Docker

```powershell
robocopy "C:\Users\Desktop\.hermes\skills" "C:\Users\Desktop\AppData\Local\hermes\skills" /E /XC /XN /XO /NP /R:1 /W:1 /XD .git
robocopy "C:\Users\Desktop\.hermes\plugins" "C:\Users\Desktop\AppData\Local\hermes\plugins" /E /XC /XN /XO /NP /R:1 /W:1 /XD .git __pycache__
```

