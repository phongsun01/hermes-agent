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

## Tóm tắt nhanh

| # | Vấn đề | Nguyên nhân gốc | Fix |
|---|--------|-----------------|-----|
| 1 | `entrypoint.sh: No such file or directory` | CRLF line endings trên Windows | Convert sang LF, build lại |
| 2 | Dashboard không truy cập được | `network_mode: host` không hoạt động trên Docker Desktop Windows | Dùng `ports: "9119:9119"` + `--host 0.0.0.0 --insecure` |
| 3 | Build bị EOF khi đổi mạng | TCP bị ngắt giữa chừng | Chạy lại `docker compose build` |
