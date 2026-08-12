# Hướng dẫn Sao lưu & Khôi phục Hermes Agent (Docker on Windows)

> [!IMPORTANT]
> Tài liệu này áp dụng chiến lược **Sao lưu Tối ưu**: Chỉ sao lưu **dữ liệu người dùng** (config, sessions, keys, skills), tuyệt đối **KHÔNG** sao lưu Docker image (2.62GB không cần thiết vì có thể build lại từ source code). Điều này giúp dung lượng backup chỉ vài chục MB.

## 1. Kiến trúc lưu trữ của Hermes Agent

Hermes Agent Docker có 2 phần cần quan tâm:

| Thành phần | Vị trí trên Windows Host | Mô tả |
|---|---|---|
| **User Data Volume** | `C:\Users\<User>\.hermes\` | Config, session, API keys, skills, memories |
| **Source Code & Compose** | `D:\Antigravity\Hermes\` | Dockerfile, docker-compose.yml, source code |
| **Docker Image** | Docker Desktop internal | 2.62GB image — **không cần backup**, build lại được |

Chiến lược backup tối ưu chỉ cần backup **2 thứ đầu tiên**.

---

## 2. Quy trình Sao lưu (Backup)

Chuẩn bị thư mục backup: `D:\Antigravity\Hermes-backup`. Mở PowerShell và thực hiện các bước sau:

### Bước 2.1: Tạo thư mục Backup theo ngày

```powershell
$Date = Get-Date -Format "yyyy-MM-dd"
$BackupDir = "D:\Antigravity\Hermes-backup\$Date"
New-Item -ItemType Directory -Force -Path $BackupDir
```

### Bước 2.2: Dừng containers trước khi backup (khuyến nghị)

Dừng containers để đảm bảo dữ liệu nhất quán (không bị ghi dở giữa chừng):

```powershell
cd D:\Antigravity\Hermes
docker compose down
```

> [!NOTE]
> Nếu không muốn downtime, có thể backup khi đang chạy — rủi ro rất thấp vì Hermes dùng SQLite (atomic writes).

### Bước 2.3: Sao lưu User Data (`.hermes` directory)

Đây là phần quan trọng nhất — chứa toàn bộ API keys, config, sessions và skills.

```powershell
$Date = Get-Date -Format "yyyy-MM-dd"
$BackupDir = "D:\Antigravity\Hermes-backup\$Date"

Compress-Archive -Path "$env:USERPROFILE\.hermes" `
  -DestinationPath "$BackupDir\hermes-userdata.zip" `
  -Force

Write-Host "✅ User data backed up to: $BackupDir\hermes-userdata.zip"
```

**Nội dung bên trong `.hermes\`:**
- `.env` — API keys của tất cả LLM providers và tools
- `config.yaml` — Toàn bộ cấu hình Hermes
- `sessions/` — Lịch sử hội thoại (SQLite DB)
- `skills/` — Custom skills đã cài
- `memories/` — Long-term memories
- `plans/` — Plans đã tạo
- `SOUL.md` — System prompt / personality

### Bước 2.4: Sao lưu Source Code & Docker Compose Config

```powershell
Compress-Archive -Path "D:\Antigravity\Hermes" `
  -DestinationPath "$BackupDir\hermes-source.zip" `
  -Force

Write-Host "✅ Source code backed up to: $BackupDir\hermes-source.zip"
```

> [!NOTE]
> Nếu repo đã được push lên GitHub, bước này là tùy chọn. Quan trọng nhất là `docker-compose.yml` đã được chỉnh sửa cho Windows.

### Bước 2.5: Khởi động lại containers

```powershell
cd D:\Antigravity\Hermes
docker compose up -d
```

### ✅ Kết quả Backup

Trong thư mục `D:\Antigravity\Hermes-backup\<date>` bạn sẽ có:
- `hermes-userdata.zip` — Vài chục MB (tùy lượng sessions/skills)
- `hermes-source.zip` — Vài chục MB (source code + node_modules bị loại trừ bởi .dockerignore)

**Tổng dung lượng: ~50-200 MB** thay vì 2.62GB nếu backup cả image.

---

## 3. Quy trình Khôi phục (Restore) — Khi sang máy mới hoặc cài lại Windows

### Bước 3.1: Chuẩn bị môi trường

1. Cài đặt **Git**, **WSL2** (`wsl --install`) và **Docker Desktop**
2. Khởi động Docker Desktop, đảm bảo engine đang chạy

### Bước 3.2: Khôi phục Source Code

```powershell
# Giải nén source code về vị trí cũ
Expand-Archive -Path "D:\Antigravity\Hermes-backup\<date>\hermes-source.zip" `
  -DestinationPath "D:\Antigravity\" `
  -Force
```

Hoặc nếu dùng Git:

```powershell
cd D:\Antigravity
git clone <your-hermes-repo-url> Hermes
```

### Bước 3.3: Khôi phục User Data

```powershell
$BackupDir = "D:\Antigravity\Hermes-backup\<date>"

# Giải nén user data về đúng vị trí
Expand-Archive -Path "$BackupDir\hermes-userdata.zip" `
  -DestinationPath "$env:USERPROFILE\" `
  -Force

Write-Host "✅ User data restored to: $env:USERPROFILE\.hermes"
```

### Bước 3.4: Build lại Docker Image

```powershell
cd D:\Antigravity\Hermes

# Fix line endings (cần thiết trên Windows)
py -c "
f='docker/entrypoint.sh'
content = open(f, 'rb').read().replace(b'\r\n', b'\n')
open(f, 'wb').write(content)
print('Line endings fixed.')
"

# Build image (mất 15-30 phút lần đầu)
docker compose build
```

### Bước 3.5: Khởi động hệ thống

```powershell
docker compose up -d
```

Truy cập dashboard tại: **http://localhost:9119**

> [!TIP]
> API keys trong `.env` được restore tự động từ bước 3.3, nên Hermes sẽ hoạt động ngay mà không cần cấu hình lại.

---

## 4. Backup nhanh bằng Script (1 lệnh)

Lưu script sau thành `D:\Antigravity\Hermes-backup\backup.ps1`:

```powershell
# backup.ps1 — Hermes Agent Backup Script
# Usage: .\backup.ps1

param(
    [string]$BackupRoot = "D:\Antigravity\Hermes-backup",
    [string]$HermesDir  = "D:\Antigravity\Hermes"
)

$Date      = Get-Date -Format "yyyy-MM-dd_HHmm"
$BackupDir = "$BackupRoot\$Date"

Write-Host "📦 Hermes Agent Backup — $Date" -ForegroundColor Cyan
Write-Host "   Target: $BackupDir"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

# Dừng containers
Write-Host "`n⏸  Stopping containers..." -ForegroundColor Yellow
Push-Location $HermesDir
docker compose down

# Backup user data
Write-Host "`n💾 Backing up user data (.hermes)..." -ForegroundColor Yellow
Compress-Archive -Path "$env:USERPROFILE\.hermes" `
  -DestinationPath "$BackupDir\hermes-userdata.zip" -Force

# Backup compose config
Write-Host "`n📄 Backing up docker-compose.yml..." -ForegroundColor Yellow
Copy-Item "$HermesDir\docker-compose.yml" "$BackupDir\docker-compose.yml"

# Restart containers
Write-Host "`n▶  Starting containers..." -ForegroundColor Yellow
docker compose up -d
Pop-Location

# Summary
$Size = (Get-ChildItem $BackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "`n✅ Backup complete! Size: $([math]::Round($Size, 1)) MB" -ForegroundColor Green
Write-Host "   Location: $BackupDir"
```

Chạy backup: `cd D:\Antigravity\Hermes-backup; .\backup.ps1`

---

## 5. Tóm tắt nhanh

| Thao tác | Lệnh |
|---|---|
| **Backup nhanh** | `cd D:\Antigravity\Hermes-backup; .\backup.ps1` |
| **Restore user data** | `Expand-Archive hermes-userdata.zip -Dest $env:USERPROFILE\` |
| **Restore & start** | `docker compose build && docker compose up -d` |
| **Truy cập dashboard** | http://localhost:9119 |

> [!TIP]
> Nên chạy backup sau mỗi lần thay đổi cấu hình quan trọng hoặc trước khi nâng cấp Hermes lên version mới.
