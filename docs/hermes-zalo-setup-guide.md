# Hermes Agent + Zalo Plugin — Cài đặt, Cấu hình & Khắc phục lỗi

> **Ngày:** 2026-06-08
> **Môi trường:** Windows 11 + Docker Desktop
> **Workspace:** `D:\Antigravity\Hermes-fresh`

---

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────┐
│  Windows Host                                               │
│                                                             │
│  ┌──────────────────┐    HTTP/SSE     ┌──────────────────┐  │
│  │  Zalo Bridge     │◄───────────────►│  hermes-zalo-    │  │
│  │  (Node.js)       │  port 8787      │  plugin          │  │
│  │  server.js       │                 │  (zca-js)        │  │
│  └────────┬─────────┘                 └──────────────────┘  │
│           │                                                  │
│           │  (bridge URL: http://127.0.0.1:8787)            │
└───────────┼──────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│  Docker Container (hermes-agent:latest)                     │
│                                                             │
│  ┌──────────────────┐    HTTP/SSE     ┌──────────────────┐  │
│  │  Hermes Gateway  │◄───────────────►│  Zalo Adapter    │  │
│  │  (Python)        │  host.docker.   │  (plugin)        │  │
│  │                  │  internal:8787  │                  │  │
│  └────────┬─────────┘                 └──────────────────┘  │
│           │                                                  │
│           ├──► Telegram Bot (polling)                       │
│           └──► API Server (port 8642)                       │
└─────────────────────────────────────────────────────────────┘
```

**Luồng dữ liệu:**
- **Zalo inbound:** Zalo → zca-js → SSE → `http://host.docker.internal:8787/events` → Hermes Gateway → AI
- **Zalo outbound:** AI → Hermes Gateway → REST POST → `http://host.docker.internal:8787/send` → zca-js → Zalo
- **Telegram inbound/outbound:** Trực tiếp qua Telegram Bot API (polling)

---

## 2. Cài đặt Hermes Agent

### 2.1. Clone source code

```powershell
# Xóa thư mục cũ (nếu còn)
Remove-Item -Recurse -Force "D:\Antigravity\Hermes" -ErrorAction SilentlyContinue

# Clone bản mới nhất từ NousResearch
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git "D:\Antigravity\Hermes-fresh"
```

### 2.2. Fix CRLF trong Docker files (lỗi s6-overlay)

Windows git clone tạo file với CRLF (`\r\n`), s6-overlay trong Docker cần Unix LF (`\n`).

```powershell
# Fix file type trong s6-rc.d
Get-ChildItem "D:\Antigravity\Hermes-fresh\docker\s6-rc.d" -Recurse -Include "type","run","finish" |
  ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)
    $fixed = $content -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($_.FullName, $fixed, [System.Text.UTF8Encoding]::new($false))
  }

# Fix cont-init.d scripts
Get-ChildItem "D:\Antigravity\Hermes-fresh\docker\cont-init.d" -File |
  ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)
    $fixed = $content -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($_.FullName, $fixed, [System.Text.UTF8Encoding]::new($false))
  }

# Fix stage2-hook.sh
$hook = "D:\Antigravity\Hermes-fresh\docker\stage2-hook.sh"
$content = [System.IO.File]::ReadAllText($hook)
$fixed = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($hook, $fixed, [System.Text.UTF8Encoding]::new($false))
```

### 2.3. Build Docker image

```powershell
Set-Location "D:\Antigravity\Hermes-fresh"
docker build -t hermes-agent:latest .
```

### 2.4. Cấu hình docker-compose.yml

Copy từ backup hoặc tạo mới:

```yaml
services:
  gateway:
    build: .
    image: hermes-agent
    container_name: hermes
    restart: unless-stopped
    ports:
      - "8642:8642"
    volumes:
      - ~/.hermes:/opt/data
    environment:
      - HERMES_UID=${HERMES_UID:-10000}
      - HERMES_GID=${HERMES_GID:-10000}
      - API_SERVER_HOST=0.0.0.0
      - API_SERVER_KEY=zalo-hermes-secret-key-123456
      - HERMES_GATEWAY_BOOTSTRAP_STATE=running
    command: ["gateway", "run"]

  dashboard:
    image: hermes-agent
    container_name: hermes-dashboard
    restart: unless-stopped
    depends_on:
      - gateway
    ports:
      - "9119:9119"
    volumes:
      - ~/.hermes:/opt/data
    environment:
      - HERMES_UID=${HERMES_UID:-10000}
      - HERMES_GID=${HERMES_GID:-10000}
    command: ["dashboard", "--host", "0.0.0.0", "--port", "9119", "--no-open", "--insecure"]
```

### 2.5. Cấu hình .env + docker-compose.yml

> **⚠️ Quan trọng:** Docker volume mount từ Windows host có thể không sync file `.env` đúng cách (mất newline). 
> Giải pháp tin cậy: đặt env vars trực tiếp trong `docker-compose.yml`.

**File `.env`** (`%USERPROFILE%\.hermes\.env`):
```env
# TELEGRAM
TELEGRAM_BOT_TOKEN=8799237321:AAH0pAZzJAmlJE7sn6fq1p1i94YyYKTPpQo
TELEGRAM_ALLOWED_USERS=5511250191
TELEGRAM_HOME_CHANNEL=5511250191

# GATEWAY
GATEWAY_ALLOW_ALL_USERS=true
```

**File `docker-compose.yml`** — thêm Zalo env vars:
```yaml
    environment:
      - HERMES_UID=${HERMES_UID:-10000}
      - HERMES_GID=${HERMES_GID:-10000}
      - API_SERVER_HOST=0.0.0.0
      - API_SERVER_KEY=zalo-hermes-secret-key-123456
      - HERMES_GATEWAY_BOOTSTRAP_STATE=running
      # Zalo plugin env vars (đặt trực tiếp ở đây để tránh lỗi .env mount)
      - ZALO_PLUGIN_URL=http://host.docker.internal:8787
      - ZALO_ALLOWED_USERS=2825656851207986406
      - ZALO_GROUP_MODE=off
      - ZALO_ALLOWED_ACTION_GROUPS=read,send,interact
      - ZALO_ALLOW_DESTRUCTIVE=false
      - ZALO_HOME_CHANNEL=2825656851207986406
      - ZALO_LOG_IDS=true
```

### 2.6. Cấu hình config.yaml — LLM Provider

File: `%USERPROFILE%\.hermes\config.yaml`

```yaml
model:
  default: hermes-combo
  provider: custom
  base_url: http://host.docker.internal:20128/v1

providers:
  custom:
    api_key: 'sk-52322c0dd90d1c8a-2iry8g-ebb67c15'
    base_url: 'http://host.docker.internal:20128/v1'
```

> **⚠️ Lỗi thường gặp:**
> - `providers.custom.base_url` khác với `model.base_url` → provider dùng URL sai → HTTP 401
> - Dùng `https://api.opencode.ai/zen/v1` thay vì `http://host.docker.internal:20128/v1` → API key không được nhận

### 2.7. Khởi động

```powershell
Set-Location "D:\Antigravity\Hermes-fresh"
docker compose up -d
```

---

## 3. Cài đặt hermes-zalo-plugin

### 3.1. Clone + cài dependencies

```powershell
git clone --depth 1 https://github.com/cuongdev/hermes-zalo-plugin.git "D:\Antigravity\hermes-zalo-plugin"
cd D:\Antigravity\hermes-zalo-plugin
npm install
```

### 3.2. Cấu hình Zalo plugin

Plugin đã có sẵn adapter tại `hermes-plugin/adapter.py`. Copy vào Hermes:

```powershell
# Plugin tự động được phát hiện khi gateway start
# File plugin nằm tại: D:\Antigravity\hermes-zalo-plugin\hermes-plugin\
#   ├── adapter.py
#   ├── plugin.yaml
#   └── __init__.py

# Copy vào ~/.hermes/plugins/zalo/
Copy-Item -Recurse "D:\Antigravity\hermes-zalo-plugin\hermes-plugin\*" "$env:USERPROFILE\.hermes\plugins\zalo\" -Force
```

### 3.3. Start Zalo Bridge

```powershell
cd D:\Antigravity\hermes-zalo-plugin
node server.js
```

Bridge sẽ:
1. Load credentials cũ (nếu có) → auto-login
2. Nếu không có → tạo QR login → chờ scan

### 3.5. Patch auto-relogin cho bridge

Mặc định bridge không tự relogin khi session chết (code=1006). Patch `server.js`:

```javascript
// Thay dòng này trong server.js:
// client.on("session_dead", (d) => pushEvent("session_dead", d));

// Bằng:
client.on("session_dead", (d) => {
  pushEvent("session_dead", d);
  console.log("[bridge] session dead — auto-relogin triggered");
  client.relogin({ forceQR: false })
    .then((r) => console.log("[bridge] auto-relogin complete via", r.method))
    .catch((e) => console.error("[bridge] auto-relogin failed:", e && e.message ? e.message : e));
});
```

### 3.6. QR Login (lần đầu hoặc session hết hạn)

**Trên Windows host:**
```
http://127.0.0.1:8787/qr.png    # Xem ảnh QR
http://127.0.0.1:8787/health    # Kiểm tra trạng thái
```

**Trong Docker container:**
```
http://host.docker.internal:8787/qr.png
http://host.docker.internal:8787/health
```

> **⚠️ Lưu ý:** `host.docker.internal` chỉ hoạt động BÊN TRONG container. Trên Windows host, dùng `127.0.0.1`.

**Các bước scan QR:**
1. Mở `http://127.0.0.1:8787/qr.png` trong trình duyệt
2. Mở Zalo trên điện thoại → `+` → `Quét mã QR`
3. Quét QR → xác nhận trên điện thoại
4. Kiểm tra: `http://127.0.0.1:8787/health` → `"loggedIn": true`

### 3.5. Policy phân quyền Zalo

Cấu hình qua `.env`:

| Biến | Giá trị | Ý nghĩa |
|------|---------|---------|
| `ZALO_ALLOWED_USERS` | `2825656851207986406` | Chỉ user này nhắn được bot |
| `ZALO_ALLOWED_THREADS` | (trống) | Không giới hạn nhóm |
| `ZALO_GROUP_MODE` | `off` | Không reply trong nhóm |
| `ZALO_ALLOWED_ACTION_GROUPS` | `read,send,interact` | Bot chỉ đọc/gửi/tương tác |
| `ZALO_ALLOW_DESTRUCTIVE` | `false` | Không xóa/giải tán nhóm |
| `ZALO_HOME_CHANNEL` | `2825656851207986406` | Tin hệ thống gửi về user này |

Kiểm tra policy:
```powershell
curl http://127.0.0.1:8787/policy
```

---

## 4. Khắc phục lỗi thường gặp

### 4.1. Lỗi: `s6-rc-compile: fatal: invalid .../type`

**Nguyên nhân:** File `docker/s6-rc.d/*/type` có CRLF (`\r\n`), s6-overlay cần LF (`\n`).

**Fix:** Xem mục 2.2 — chạy script fix CRLF trước khi build.

### 4.2. Lỗi: `✗ zalo failed to connect — Cannot connect to host 127.0.0.1:8787`

**Nguyên nhân:** Container không reach được `127.0.0.1:8787` (đó là localhost của container, không phải host).

**Fix:** Đổi `ZALO_PLUGIN_URL` trong `.env`:
```env
ZALO_PLUGIN_URL=http://host.docker.internal:8787
```
Sau đó: `docker compose down && docker compose up -d`

### 4.3. Lỗi: `Platform 'Zalo' requirements not met (pip install aiohttp)`

**Nguyên nhân:** `aiohttp` chưa có trong Python venv của container.

**Fix:**
```powershell
docker exec hermes uv pip install aiohttp
docker restart hermes
```

### 4.4. Lỗi: `No user allowlists configured. All unauthorized users will be denied.`

**Nguyên nhân:** Thiếu `GATEWAY_ALLOW_ALL_USERS=true` trong `.env`.

**Fix:** Thêm vào `.env`:
```env
GATEWAY_ALLOW_ALL_USERS=true
```

### 4.5. Lỗi: `Provider authentication failed (HTTP 401)`

**Nguyên nhân:** `providers.custom.base_url` trong `config.yaml` sai, hoặc API key không khớp.

**Fix:** Đảm bảo `providers.custom.base_url` trùng với `model.base_url`:
```yaml
model:
  base_url: http://host.docker.internal:20128/v1
providers:
  custom:
    api_key: 'sk-52322c0dd90d1c8a-2iry8g-ebb67c15'
    base_url: 'http://host.docker.internal:20128/v1'
```

### 4.6. Lỗi: Zalo session dead (code=1006)

**Nguyên nhân:** Zalo bridge bị disconnect (network, QR hết hạn, login từ thiết bị khác).

**Fix:**
```powershell
# 1. Shutdown bridge cũ
curl -X POST http://127.0.0.1:8787/shutdown

# 2. Start lại
cd D:\Antigravity\hermes-zalo-plugin
node server.js

# 3. Nếu cần QR mới
curl -X POST http://127.0.0.1:8787/relogin

# 4. Kiểm tra
curl http://127.0.0.1:8787/health
```

### 4.7. Lỗi: `.env` bị mất newline, các biến dính vào nhau

**Nguyên nhân:** Copy/paste hoặc script PowerShell viết file không đúng format.

**Triệu chứng:** `docker exec hermes sh -c 'echo $TELEGRAM_BOT_TOKEN'` trả về rỗng.

**Fix:** Viết lại file `.env` bằng tay, đảm bảo mỗi biến trên 1 dòng riêng:
```env
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_ALLOWED_USERS=yyy
ZALO_PLUGIN_URL=http://host.docker.internal:8787
```

### 4.8. Lỗi: Gateway restart liên tục (SIGTERM loop)

**Nguyên nhân:** s6-overlay supervision restart gateway khi nó exit code 1.

**Giải pháp:** Đây là behavior bình thường của s6-overlay. Gateway tự restart và reconnect. Không cần fix.

---

## 5. URL reference

| URL | Dùng ở đâu | Mục đích |
|-----|------------|----------|
| `http://127.0.0.1:8787/health` | Windows host | Kiểm tra bridge Zalo |
| `http://127.0.0.1:8787/qr.png` | Windows host | Xem QR để scan |
| `http://127.0.0.1:8787/relogin` | Windows host | Trigger QR login mới |
| `http://127.0.0.1:8787/policy` | Windows host | Xem policy phân quyền |
| `http://host.docker.internal:8787/health` | Trong container | Kiểm tra bridge từ container |
| `http://host.docker.internal:8787/qr.png` | Trong container | Xem QR từ container |
| `http://localhost:8642` | Windows host | API server của Hermes |
| `http://localhost:9119` | Windows host | Dashboard web UI |

---

## 6. Kiểm tra trạng thái

```powershell
# Kiểm tra container
docker ps --filter "name=hermes"

# Kiểm tra logs
docker logs hermes --tail 50

# Kiểm tra gateway log chi tiết
docker exec hermes tail -30 /opt/data/logs/gateway.log

# Kiểm tra bridge Zalo
curl http://127.0.0.1:8787/health

# Kiểm tra env vars trong container
docker exec hermes sh -c 'echo "ZALO_PLUGIN_URL=$ZALO_PLUGIN_URL"'
docker exec hermes sh -c 'echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"'
```

---

## 7. Restart toàn bộ hệ thống

```powershell
# 1. Dừng containers
docker compose down

# 2. Restart Zalo bridge
Get-Process -Name node | Where-Object { $_.Path -like "*hermes-zalo*" } | Stop-Process -Force
cd D:\Antigravity\hermes-zalo-plugin
node server.js

# 3. Start lại containers
cd D:\Antigravity\Hermes-fresh
docker compose up -d

# 4. Kiểm tra
Start-Sleep 20
docker exec hermes tail -20 /opt/data/logs/gateway.log
```

---

## 8. Checklist hoàn tất

- [ ] Hermes source cloned + CRLF fixed
- [ ] Docker image built (`hermes-agent:latest`)
- [ ] `docker-compose.yml` configured
- [ ] `.env` configured (Telegram + Zalo + Gateway)
- [ ] `config.yaml` configured (LLM provider + base_url)
- [ ] hermes-zalo-plugin cloned + npm install
- [ ] Zalo bridge running + QR scanned
- [ ] Gateway running with 2 platforms (Telegram + Zalo)
- [ ] Telegram bot responding ✅
- [ ] Zalo bot responding ✅
