# Hermes Agent — Docker on Windows: Sự cố & cách khắc phục

> Ghi lại các lỗi gặp phải và cách sửa khi cài đặt `hermes-agent` lên Docker Desktop for Windows.
> Build date: 2026-05-05

---

## 1. Lỗi `entrypoint.sh: No such file or directory`

### Triệu chứng

Container khởi động xong nhưng exit ngay lập tức với log:

```
[FATAL tini (7)] exec /opt/hermes/docker/entrypoint.sh failed: No such file or directory
```

### Nguyên nhân

File `docker/entrypoint.sh` trong repo bị Git on Windows lưu với line endings kiểu CRLF (`\r\n`).
Khi Docker copy file vào container Linux, shebang `#!/bin/bash\r` bị Linux kernel từ chối
vì có ký tự `\r` thừa, dẫn đến file bị coi là không thực thi được.

### Cách sửa

Chuyển toàn bộ file từ CRLF sang LF trước khi build lại image:

```powershell
# Chạy trên Windows (PowerShell)
py -c "
f='d:/Antigravity/Hermes/docker/entrypoint.sh'
content = open(f, 'rb').read().replace(b'\r\n', b'\n')
open(f, 'wb').write(content)
"
```

Sau đó build lại:

```powershell
docker compose build
docker compose up -d
```

### Phòng ngừa lâu dài

Thêm vào `.gitattributes` của repo (đã có sẵn, cần kiểm tra):

```
docker/entrypoint.sh text eol=lf
```

Hoặc cấu hình Git toàn cục:

```bash
git config --global core.autocrlf input
```

---

## 2. Dashboard không truy cập được tại `http://localhost:9119`

### Triệu chứng

Container `hermes-dashboard` đang chạy (status `Up`) nhưng trình duyệt không kết nối được
tới `http://localhost:9119`.

### Nguyên nhân

File `docker-compose.yml` gốc dùng `network_mode: host` và bind dashboard vào `127.0.0.1:9119`:

```yaml
network_mode: host
command: ["dashboard", "--host", "127.0.0.1", "--no-open"]
```

Trên **Linux**, `network_mode: host` chia sẻ network stack của host → hoạt động bình thường.

Trên **Docker Desktop for Windows**, container chạy bên trong một Linux VM ẩn. `network_mode: host`
chỉ expose port ra VM đó, **không** forward về Windows host. Kết quả là port 9119 hoàn toàn
không thể truy cập từ Windows.

### Cách sửa

Sửa `docker-compose.yml`, bỏ `network_mode: host` khỏi cả hai service và dùng port mapping
tường minh cho dashboard, đồng thời đổi bind address thành `0.0.0.0`:

```yaml
services:
  gateway:
    image: hermes-agent
    container_name: hermes
    restart: unless-stopped
    # Bỏ: network_mode: host
    volumes:
      - ~/.hermes:/opt/data
    environment:
      - HERMES_UID=${HERMES_UID:-10000}
      - HERMES_GID=${HERMES_GID:-10000}
    command: ["gateway", "run"]

  dashboard:
    image: hermes-agent
    container_name: hermes-dashboard
    restart: unless-stopped
    depends_on:
      - gateway
    ports:
      - "9119:9119"          # ← port mapping tường minh
    volumes:
      - ~/.hermes:/opt/data
    environment:
      - HERMES_UID=${HERMES_UID:-10000}
      - HERMES_GID=${HERMES_GID:-10000}
    command: ["dashboard", "--host", "0.0.0.0", "--port", "9119", "--no-open", "--insecure"]
    #                         ↑ bind 0.0.0.0              ↑ --insecure bắt buộc khi không dùng 127.0.0.1
```

Khởi động lại:

```powershell
docker compose down
docker compose up -d
```

Truy cập dashboard tại: **http://localhost:9119**

### Lưu ý bảo mật

Flag `--insecure` cho phép dashboard bind ra ngoài `127.0.0.1`. Dashboard lưu trữ API keys
nên **không nên** expose ra LAN/internet mà không có reverse proxy + authentication ở phía trước.
Với môi trường local / dev thì hoàn toàn ổn.

---

## 3. Build bị gián đoạn khi đổi mạng (EOF error)

### Triệu chứng

Khi đổi mạng trong lúc đang `docker compose build`, quá trình download layer bị ngắt:

```
failed to solve: failed to compute cache key: short read: expected 67780708 bytes but got 47004352: unexpected EOF
```

### Nguyên nhân

Kết nối mạng thay đổi khiến TCP stream đến Docker registry bị đứt giữa chừng.
Layer bị lưu ở trạng thái incomplete / corrupt trong Docker build cache.

### Cách sửa

Đơn giản là chạy lại lệnh build — Docker sẽ tự bỏ qua các layer đã cache thành công
và chỉ tải lại phần bị lỗi:

```powershell
docker compose build
```

---

## 4. Lỗi `COPY docker/wheels /tmp/wheels: not found` khi build image

### Triệu chứng

Khi chạy `docker compose build` để cập nhật Hermes, build bị lỗi ở step copy wheels:

```
COPY docker/wheels /tmp/wheels: not found
```

### Nguyên nhân

Trong `Dockerfile` có dòng cấu hình copy thư mục `docker/wheels` để cài đặt playwright offline/local:
`COPY docker/wheels /tmp/wheels`
Thư mục này không nằm trong Git tracking (thường bị bỏ qua hoặc chỉ có trên môi trường build của CI/CD). Khi tải code mới về và build trực tiếp trên máy Windows host, Docker Engine không tìm thấy thư mục `docker/wheels` ở local nên báo lỗi.

### Cách sửa

Tạo một thư mục rỗng `docker/wheels` ở máy host để Docker copy thành công (khi chạy `uv pip` cài playwright, nếu thư mục này rỗng thì uv tự động tải trực tiếp từ PyPI):

```powershell
# Tạo thư mục rỗng trên Windows (PowerShell)
mkdir d:/Antigravity/Hermes/docker/wheels
```

Sau đó chạy lại lệnh build:

```powershell
docker compose build
```

---

## 5. Lỗi `env file .env.lightrag not found` khi khởi động dịch vụ

### Triệu chứng

Khi chạy lệnh `docker compose up -d` để khởi động lại dịch vụ sau khi cập nhật, Docker Compose báo lỗi và dừng:

```
env file D:\Antigravity\Hermes\.env.lightrag not found: CreateFile D:\Antigravity\Hermes\.env.lightrag: The system cannot find the file specified.
```

### Nguyên nhân

Dịch vụ `lightrag` trong `docker-compose.yml` được cấu hình sử dụng file biến môi trường `.env.lightrag`:
```yaml
    env_file:
      - .env.lightrag
```
Vì file `.env.lightrag` chứa API key và cấu hình nhạy cảm nên nó bị bỏ qua trong Git (`.gitignore`). Khi chúng ta checkout/reset nhánh code hoặc pull bản mới, file này không có sẵn trên máy làm Docker Compose không khởi động được bất cứ service nào.

### Cách sửa

Khôi phục lại file `.env.lightrag`. Nếu container `lightrag` cũ vẫn đang chạy, bạn có thể kiểm tra cấu hình cũ của nó bằng lệnh:

```powershell
docker inspect lightrag
```

Tìm phần cấu hình `"Env"` và tạo lại file `.env.lightrag` ở thư mục gốc của dự án với các thông tin tương tự:

```ini
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
HOST=0.0.0.0
PORT=9621
```

Sau đó chạy lại lệnh khởi động:

```powershell
docker compose up -d
```

---

## 6. Lỗi `BrowserType.launch: Executable doesn't exist` (Playwright thiếu Browser/Dependencies)

### Triệu chứng

Các cron job sử dụng Playwright (ví dụ quét công văn) bị lỗi và dừng:

```
[INFO] Playwright unavailable, falling back to urllib: Lỗi Playwright (after 2 attempts): BrowserType.launch: Executable doesn't exist at /opt/hermes/.playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
Please run the following command to download new browsers: playwright install
```

Hoặc lỗi thiếu system dependencies:
```
Host system is missing dependencies to run browsers. Please install them with the following command: playwright install-deps
```

### Nguyên nhân

Khi cập nhật mã nguồn Hermes và build lại Docker image, Playwright có thể được nâng cấp lên phiên bản mới hơn. Phiên bản mới sẽ yêu cầu các bản build browser (Chromium, Firefox...) tương ứng. Tuy nhiên, do thư mục chứa browser (`/opt/hermes/.playwright`) nằm trong volume hoặc không được đóng gói sẵn trong image nên browser mới chưa được tải về máy ảo.

### Cách sửa

1. Chạy lệnh cài đặt lại các browser tương thích của Playwright bên trong container `hermes`:
   ```powershell
   docker exec hermes /opt/hermes/.venv/bin/playwright install
   ```
2. Nếu container báo thiếu thư viện hệ thống (system dependencies), chạy tiếp lệnh cài đặt dependencies cho Chromium:
   ```powershell
   docker exec hermes /opt/hermes/.venv/bin/playwright install-deps chromium
   ```

---

## 7. Lỗi `PermissionError: [Errno 13] Permission denied` khi chạy Cron job

### Triệu chứng

Cron job báo lỗi phân quyền khi ghi hoặc đọc file trạng thái/log (ví dụ: `vbden_state.json`):

```
PermissionError: [Errno 13] Permission denied: '/opt/data/cron/cong-van-den/vbden_state.json'
```

### Nguyên nhân

Khi debug hoặc chạy thử thủ công các file script bằng lệnh `docker exec hermes python3 ...`, Docker sẽ thực thi lệnh với tư cách user `root`. Việc này dẫn đến các file trạng thái mới tạo hoặc được cập nhật bởi script sẽ thuộc sở hữu của `root:root` với quyền ghi hạn chế. 
Sau đó, khi cron job của hệ thống tự động chạy ngầm dưới quyền user `hermes` (UID 10000), nó không có quyền ghi đè lên các file do root sở hữu này.

### Cách sửa

1. Đổi lại quyền sở hữu các file trong thư mục data về cho user `hermes`:
   ```powershell
   docker exec -u root hermes chown -R hermes:hermes /opt/data/cron/
   ```
   *(Thay đổi `/opt/data/cron/` thành đường dẫn cụ thể chứa file lỗi nếu cần thiết)*

2. **Khuyến nghị phòng ngừa:** Khi chạy thử script thủ công qua `docker exec`, hãy luôn chỉ định chạy dưới quyền user `hermes` thay vì để mặc định:
   ```powershell
   docker exec -u hermes hermes python3 /opt/data/scripts/your_script.py
   ```

---

## Tóm tắt nhanh

| # | Vấn đề | Nguyên nhân gốc | Fix |
|---|--------|-----------------|-----|
| 1 | `entrypoint.sh: No such file or directory` | CRLF line endings trên Windows | Convert sang LF, build lại |
| 2 | Dashboard không truy cập được | `network_mode: host` không hoạt động trên Docker Desktop Windows | Dùng `ports: "9119:9119"` + `--host 0.0.0.0 --insecure` |
| 3 | Build bị EOF khi đổi mạng | TCP bị ngắt giữa chừng | Chạy lại `docker compose build` |
| 4 | `COPY docker/wheels /tmp/wheels: not found` | Thư mục `docker/wheels` không được track bởi git | Tạo thư mục rỗng `docker/wheels` ở local và build lại |
| 5 | `env file .env.lightrag not found` | File `.env.lightrag` bị gitignore | Khôi phục file cấu hình (dùng `docker inspect lightrag` nếu cần) |
| 6 | `BrowserType.launch: Executable doesn't exist` | Nâng cấp Playwright nhưng chưa tải browser tương thích | Chạy `playwright install` và `playwright install-deps` trong container |
| 7 | `PermissionError: [Errno 13] Permission denied` | Lệnh debug thủ công chạy dưới quyền `root` làm sai lệch quyền sở hữu file | Chạy `chown -R hermes:hermes` và khuyến nghị dùng `-u hermes` khi debug |



