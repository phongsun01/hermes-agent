# Hướng dẫn Backup & Restore Sessions Antigravity (và cấu hình Hermes)

> **Mục đích:** Hướng dẫn chi tiết cách sao lưu toàn bộ lịch sử các phiên chat (sessions), bộ nhớ (brain), artifacts của Antigravity và cấu hình Hermes trước khi cài lại hệ điều hành Windows, cũng như cách khôi phục sau khi cài đặt.

---

## 📌 1. Tổng quan vị trí lưu trữ dữ liệu

Khi sử dụng Antigravity và Hermes trên Windows, dữ liệu phân chia như sau:

| Thành phần | Vị trí mặc định trên Windows | Mô tả |
|---|---|---|
| **Antigravity Sessions** | `C:\Users\<User>\.gemini\antigravity-ide\conversations\` | Chứa các file `.db` (SQLite) và `.pb` (Protobuf) ghi lại lịch sử tất cả các phiên hội thoại. |
| **Antigravity Brain** | `C:\Users\<User>\.gemini\antigravity-ide\brain\` | Chứa logs, checkpoints, artifacts, scratch scripts của từng session. |
| **Antigravity Customizations** | `C:\Users\<User>\.gemini\config\` | Rules, skills tùy biến toàn cục của Antigravity. |
| **Hermes Configuration** | `C:\Users\<User>\.hermes\` | Toàn bộ cấu hình `config.yaml`, session Zalo/Telegram, cron tasks, SQLite databases của Hermes. |
| **Mã nguồn dự án** | `D:\Antigravity\Hermes` | Nằm trên ổ **D:** nên không bị ảnh hưởng khi format phân vùng ổ C. |

---

## 💾 2. Hướng dẫn Sao lưu (Backup) trước khi cài lại Windows

Toàn bộ dữ liệu được sao lưu vào thư mục: **`D:\Antigravity_Backup`**

### Cách 1: Chạy lệnh PowerShell tự động (Khuyến nghị)

Mở **PowerShell** trên Windows và chạy khối lệnh sau:

```powershell
# 1. Đường dẫn nguồn và đích
$backupDir = "D:\Antigravity_Backup"
$idePath = "$env:USERPROFILE\.gemini\antigravity-ide"
$geminiConfig = "$env:USERPROFILE\.gemini\config"
$hermesDir = "$env:USERPROFILE\.hermes"

# 2. Tạo thư mục đích trên ổ D
New-Item -ItemType Directory -Force -Path "$backupDir\antigravity-ide" | Out-Null

# 3. Sao lưu conversations (toàn bộ phiên hội thoại)
Write-Host "--> Đang sao lưu Antigravity Conversations..." -ForegroundColor Cyan
robocopy "$idePath\conversations" "$backupDir\antigravity-ide\conversations" /E /R:1 /W:1 /NP

# 4. Sao lưu brain (loại trừ các file video/log tạm thời không cần thiết nếu muốn gọn nhẹ)
Write-Host "--> Đang sao lưu Antigravity Brain (artifacts, checkpoints, logs)..." -ForegroundColor Cyan
robocopy "$idePath\brain" "$backupDir\antigravity-ide\brain" /E /R:1 /W:1 /NP

# 5. Sao lưu config tùy biến của Antigravity (nếu có)
if (Test-Path $geminiConfig) {
    Write-Host "--> Đang sao lưu Antigravity Config..." -ForegroundColor Cyan
    robocopy $geminiConfig "$backupDir\gemini_config" /E /R:1 /W:1 /NP
}

# 6. Sao lưu cấu hình Hermes (~/.hermes)
if (Test-Path $hermesDir) {
    Write-Host "--> Đang sao lưu Hermes config & state..." -ForegroundColor Cyan
    # Loại trừ thư mục cache và tmp để tiết kiệm dung lượng
    robocopy $hermesDir "$backupDir\.hermes" /E /XD cache tmp "logs\gateways" /R:1 /W:1 /NP
}

Write-Host "`n✅ ĐÃ HOÀN TẤT SAO LƯU SANG: $backupDir" -ForegroundColor Green
```

---

## 🔄 3. Hướng dẫn Khôi phục (Restore) sau khi cài lại Windows

Sau khi bạn đã cài lại Windows và cài đặt lại Antigravity:

### Bước 1: Tắt hoàn toàn ứng dụng Antigravity
Đảm bảo Antigravity IDE không đang mở hoặc chạy ngầm dưới taskbar.

### Bước 2: Chạy script khôi phục bằng PowerShell

Mở **PowerShell** và chạy đoạn lệnh sau:

```powershell
# 1. Định nghĩa đường dẫn
$backupDir = "D:\Antigravity_Backup"
$targetIde = "$env:USERPROFILE\.gemini\antigravity-ide"
$targetGeminiConfig = "$env:USERPROFILE\.gemini\config"
$targetHermes = "$env:USERPROFILE\.hermes"

# 2. Tạo sẵn thư mục đích
New-Item -ItemType Directory -Force -Path "$targetIde\conversations" | Out-Null
New-Item -ItemType Directory -Force -Path "$targetIde\brain" | Out-Null

# 3. Khôi phục Conversations và Brain của Antigravity
Write-Host "--> Đang khôi phục Antigravity Conversations..." -ForegroundColor Cyan
robocopy "$backupDir\antigravity-ide\conversations" "$targetIde\conversations" /E /R:1 /W:1 /NP

Write-Host "--> Đang khôi phục Antigravity Brain..." -ForegroundColor Cyan
robocopy "$backupDir\antigravity-ide\brain" "$targetIde\brain" /E /R:1 /W:1 /NP

# 4. Khôi phục Antigravity config (nếu có)
if (Test-Path "$backupDir\gemini_config") {
    Write-Host "--> Đang khôi phục Gemini Config..." -ForegroundColor Cyan
    robocopy "$backupDir\gemini_config" $targetGeminiConfig /E /R:1 /W:1 /NP
}

# 5. Khôi phục Hermes config
if (Test-Path "$backupDir\.hermes") {
    Write-Host "--> Đang khôi phục Hermes data..." -ForegroundColor Cyan
    robocopy "$backupDir\.hermes" $targetHermes /E /R:1 /W:1 /NP
}

Write-Host "`n🎉 KHÔI PHỤC HOÀN TẤT!" -ForegroundColor Green
```

### Bước 3: Mở lại Antigravity
1. Mở Antigravity lên.
2. Chọn **Open Folder** và trỏ đúng vào thư mục workspace cũ: `D:\Antigravity\Hermes`.
3. Thanh bên (sidebar) của Antigravity sẽ tự động nhận diện và nạp lại toàn bộ lịch sử các phiên chat cũ trước đây.

---

## ⚠️ 4. Các lưu ý quan trọng

1. **Không format nhầm ổ D:** Trong quá trình cài đặt lại Windows (qua USB cài đặt), hãy chọn đúng phân vùng ổ **C:** (phân vùng hệ thống cũ) để format hoặc ghi đè, **tuyệt đối không xóa/format phân vùng ổ D:**.
2. **Quyền hạn file:** Sau khi cài lại Win, nếu gặp lỗi không ghi được file trên ổ D, bạn chỉ cần mở PowerShell as Administrator và gán lại quyền sở hữu:
   ```powershell
   takeown /F "D:\Antigravity" /R /D Y
   icacls "D:\Antigravity" /grant "$($env:USERNAME):(OI)(CI)F" /T
   ```
3. **Môi trường Docker:** Sau khi cài lại Windows, bạn chỉ cần cài đặt Docker Desktop, sau đó mở thư mục `D:\Antigravity\Hermes` và chạy `docker compose up -d`, các container Hermes, Dashboard, Zalo Bridge sẽ tự động hoạt động trở lại mà không mất dữ liệu.
