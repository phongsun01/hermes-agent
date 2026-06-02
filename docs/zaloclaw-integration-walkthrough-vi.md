# Báo Cáo Hoàn Thành Tích Hợp Nền Tảng Zalo (ZaloClaw)

## 🗓️ Lịch Sử Thay Đổi

| Phiên bản | Ngày | Nội dung |
|-----------|------|----------|
| v1.0 | 2026-05 | Hoàn thành tích hợp ban đầu (Phase 1 + 3) |
| v1.1 | 2026-06-01 | Cập nhật Hermes upstream → v0.14.0, merge ZaloClaw, rebuild Docker |
| v1.2 | 2026-06-01 | Cập nhật Hermes upstream → v0.15.2 (tag v2026.5.29.2), Phase 4 Access Control & Groups |

---

## PHẦN 1: Tích Hợp Ban Đầu (v1.0)

Đã hoàn thành việc tích hợp nền tảng nhắn tin Zalo vào Hermes Agent bằng kiến trúc subprocess worker (tiến trình con) mạnh mẽ.

### 1.1. Node.js Worker (`gateway/platforms/zalo/worker`)
- **Tích hợp zca-js**: Xây dựng một worker Node.js độc lập sử dụng thư viện `zca-js` để tương tác với API Zalo.
- **Xác thực**: Hỗ trợ đăng nhập bằng mã QR với khả năng lưu trữ phiên đăng nhập tự động vào `~/.hermes/data/zalo_session.json`.
- **Điều phối Hành động (Action Dispatcher)**: Đã triển khai các trình xử lý cho:
  - `send`: Gửi tin nhắn văn bản (có hỗ trợ mức độ khẩn cấp).
  - `send-image`: Tải lên hình ảnh (hỗ trợ cả URL và đường dẫn cục bộ).
  - `send-file`: Tải lên tài liệu/file.
  - `add-reaction`: Thả biểu cảm (reaction) vào tin nhắn.
  - `me` & `get-group-info`: Truy xuất thông tin cá nhân và thông tin nhóm.
- **Giao thức IPC**: Sử dụng JSON-RPC qua stdin/stdout để giao tiếp mượt mà với adapter Python.

### 1.2. Python Adapter (`gateway/platforms/zalo.py`)
- **Quản lý Subprocess**: Quản lý vòng đời của worker Node.js (khởi động, giám sát, dừng).
- **Ánh xạ Sự kiện**: Chuyển đổi các sự kiện tin nhắn từ Zalo thành các đối tượng `MessageEvent` chuẩn của Hermes.
- **Trải nghiệm QR (UX)**: Tự động lưu mã QR được tạo thành file ảnh tại `~/.hermes/data/zalo_qr.png` để người dùng dễ dàng quét.
- **Phân quyền**: Tích hợp với hệ thống allowlist toàn cầu và riêng biệt của Hermes (`ZALO_ALLOWED_USERS`).
- **Encoding Windows**: Cấu hình subprocess với `encoding='utf-8'` và `errors='replace'` để xử lý ký tự tiếng Việt đúng đắn.

### 1.3. Hệ thống Lõi Gateway (`gateway/run.py` & `gateway/config.py`)
- **Đăng ký Nền tảng**: Thêm `Platform.ZALO` vào danh sách các nền tảng chính thức.
- **Khởi tạo Adapter**: Đăng ký `ZaloAdapter` trong phương thức `GatewayRunner._create_adapter`.
- **Cấu hình Auth**: Thêm các ánh xạ biến môi trường dành riêng cho Zalo để quản lý quyền truy cập của người dùng.

---

## PHẦN 2: Quy Trình Cập Nhật Hermes + Merge ZaloClaw (v1.1 — 2026-06-01)

### 2.1. Bối Cảnh

Sau khi hoàn thành tích hợp ZaloClaw vào phiên bản Hermes cũ (`v0.12.0`, chậm hơn `upstream/main` 1879 commit), chúng tôi tiến hành cập nhật lên phiên bản mới nhất (`v0.14.0`) từ kho chứa gốc `NousResearch/hermes-agent` trong khi bảo toàn toàn bộ tích hợp Zalo.

### 2.2. Lưu Trữ Lên GitHub Trước Khi Cập Nhật

**Bước 1: Thiết lập cấu trúc Git Fork chuẩn**
```powershell
# Đổi tên remote gốc thành upstream (để cập nhật từ Nous Research sau này)
git remote rename origin upstream

# Thêm remote origin trỏ về fork cá nhân của bạn
git remote add origin https://github.com/phongsun01/hermes-agent.git
```

**Bước 2: Cấu hình định danh Git (local)**
```powershell
git config user.name "phongsun01"
git config user.email "phongsun01@users.noreply.github.com"
```

**Bước 3: Commit và đẩy toàn bộ mã nguồn ZaloClaw lên GitHub**
```powershell
git add .
git commit -m "feat: Tich hop hoan chinh ZaloClaw"
git push --force -u origin main
```

> [!NOTE]
> Dùng `--force` vì GitHub fork đã tự động sync với upstream (mới hơn bản cục bộ). Fork cá nhân là không gian riêng của bạn nên force-push là an toàn.

### 2.3. Cập Nhật Hermes Lên Bản Mới Nhất

**Bước 1: Tải các commit mới nhất từ kho chứa gốc Nous Research về máy**
```powershell
git fetch upstream
```

**Bước 2: Tiến hành gộp code (merge)**
```powershell
git merge upstream/main
```

**Kết quả:** Git tự động gộp (auto-merge) thành công **không xung đột** trên các file lõi quan trọng nhất:
- ✅ `gateway/run.py` — tự động gộp an toàn
- ✅ `gateway/config.py` — tự động gộp an toàn
- ✅ `docker-compose.yml` — tự động gộp an toàn
- ✅ `docker/entrypoint.sh` — tự động gộp an toàn

### 2.4. Giải Quyết Xung Đột Còn Lại

Có 3 file xuất hiện xung đột nhẹ và đã được giải quyết như sau:

**File 1: `tui_gateway/entry.py`**
- **Nguyên nhân:** Upstream có cải tiến xử lý tín hiệu hệ thống Windows (`SIGBREAK`, `SIGPIPE` guard).
- **Giải pháp:** Lấy nguyên bản upstream vì bản mới tốt hơn và tương thích Windows hơn.
```powershell
git checkout upstream/main -- tui_gateway/entry.py
```

**File 2: `ui-tui/package.json`**
- **Nguyên nhân:** Upstream thay đổi lệnh build TUI từ `tsc + babel` sang `node scripts/build.mjs` (dùng esbuild, nhanh hơn nhiều).
- **Giải pháp:** Dùng lệnh build mới của upstream.
- Sửa xung đột trong file:
  ```diff
  - "build": "npm run build --prefix packages/hermes-ink && tsc -p tsconfig.build.json && npm run build:compile",
  - "build:compile": "babel dist --out-dir dist ...",
  + "build": "node scripts/build.mjs",
  ```

**File 3: `.gitignore`**
- **Nguyên nhân:** File bị lỗi encoding nhị phân (binary conflict) do sự khác biệt về line ending (CRLF/LF).
- **Giải pháp:** Ghi đè file bằng nội dung sạch của upstream (bao gồm các pattern mới như `.hermes/`, `.gemini/`, `.codex/`, v.v.).

**Đánh dấu xung đột đã giải quyết và commit:**
```powershell
git add .gitignore ui-tui/package.json tui_gateway/entry.py
git commit -m "Merge upstream changes and resolve ZaloClaw conflicts"
git push origin main
```

### 2.5. Build Lại Docker Container

Sau khi gộp code xong, tiến hành build lại Docker image để áp dụng toàn bộ thay đổi:

```powershell
docker compose build
```

**Kết quả Build:**
- ✅ Hermes Agent được cài đặt: `hermes-agent==0.14.0`
- ✅ Web dashboard (Vite) build thành công trong 7.88s
- ✅ TUI (esbuild) build thành công: `dist/entry.js 2.9mb` trong 144ms
- ✅ Image tag: `docker.io/library/hermes-agent:latest`

---

## PHẦN 2B: Cập Nhật Hermes v0.15.2 + Phase 4 Access Control (v1.2 — 2026-06-01)

### 2B.1. Bối Cảnh

Sau khi hoàn thành Phase 4 (Access Control & Groups) trên nền v0.14.0, tiến hành cập nhật Hermes lên bản phát hành chính thức **v0.15.2** (tag `v2026.5.29.2`) từ `NousResearch/hermes-agent` — chênh lệch ~100+ commit so với v0.14.0.

### 2B.2. Commit Code Phase 4 Trước Khi Merge

```powershell
# Stage các file Zalo access control
git add gateway/platforms/zalo.py gateway/platforms/zalo/worker/src/access-control.ts `
  gateway/platforms/zalo/worker/src/index.ts gateway/platforms/zalo/worker/src/actions.ts `
  gateway/platforms/zalo/worker/dist/ docs/zalo-hermes-integration-plan.md

git commit -m "feat(zalo): Phase 4 - Access Control & Groups (DM/group policy, mention gating, user/group caching)"

# Đẩy lên fork
git push origin main
```

### 2B.3. Fetch và Merge Tag Release

```powershell
# Fetch tags mới nhất từ upstream
git fetch upstream --tags

# Xác nhận tag có sẵn
git tag -l | Select-String "2026.5.29"
# Kết quả: v2026.5.29, v2026.5.29.2

# Merge tag release cụ thể
git merge v2026.5.29.2 --no-edit
```

### 2B.4. Giải Quyết Xung Đột

Có **2 file** xung đột:

**File 1: `.gitignore`**
- **Nguyên nhân:** Xung đột nội dung giữa phần `scripts/out/` (HEAD) và phần trống (tag).
- **Giải pháp:** Giữ cả hai — giữ `scripts/out/` từ HEAD, xóa marker xung đột.

**File 2: `gateway/run.py`**
- **Nguyên nhân:** Upstream thay đổi cấu trúc vùng `_create_adapter` (thêm/bớt platform adapters). Code Zalo của chúng ta nằm giữa `WEIXIN` và `MATTERMOST` bị bao bởi conflict markers.
- **Giải pháp:** Giữ nguyên code Zalo adapter + giữ code upstream xung quanh. Xóa markers `<<<<<<<`, `=======`, `>>>>>>>`.

```powershell
# Sau khi sửa xong
git add .gitignore gateway/run.py
git commit --no-edit
git push origin main
```

### 2B.5. Phase 4 — Access Control & Groups (Tổng Kết)

**File mới:**
- `gateway/platforms/zalo/worker/src/access-control.ts` — Module AC TypeScript (230+ dòng)

**File sửa đổi:**
- `gateway/platforms/zalo/worker/src/index.ts` — Tích hợp AC vào message handler, thêm IPC methods
- `gateway/platforms/zalo/worker/src/actions.ts` — Thêm `get-user-info`, `get-group-info`, `refresh-group-info` với caching
- `gateway/platforms/zalo.py` — Thêm class `ZaloAccessControl` (Python-side defense-in-depth)
- `docs/zalo-hermes-integration-plan.md` — Cập nhật trạng thái Phase 4

**Tính năng đã triển khai:**
| Tính năng | Trạng thái |
|-----------|-----------|
| DM policy (open/closed/allowlist/denylist) | ✅ |
| Group policy (open/closed/allowlist/denylist) | ✅ |
| Allowlist/denylist per-user, per-group | ✅ |
| `requireMention` cho group messages | ✅ |
| Mention detection (regex, bot name, user ID) | ✅ |
| Strip mention prefix tự động | ✅ |
| User/group info caching (TTL 5 phút) | ✅ |
| Defense-in-depth (worker + Python) | ✅ |
| Runtime config update qua IPC | ✅ |
| Status reporting | ✅ |

### 2B.6. Build Lại Docker

```powershell
cd D:\Antigravity\Hermes
docker compose build
docker compose up -d
```

**Kết quả:**
- ✅ Hermes Agent: `v0.15.2` (tag `v2026.5.29.2`)
- ✅ Zalo Phase 4 Access Control tích hợp đầy đủ
- ✅ Worker TypeScript build thành công
- ✅ Python adapter import sạch sẽ

---

## PHẦN 3: Kế Hoạch Xác Minh (Verification)

### 3.1. Kiểm Tra Thủ Công
1. **Kích hoạt Zalo**: Thêm `zalo: {}` vào phần `platforms:` trong file `~/.hermes/config.yaml` của bạn.
2. **Khởi động Gateway**: Chạy lệnh `docker compose up -d` hoặc `python -m gateway.run`.
3. **Đăng nhập**:
   - Theo dõi log để thấy dòng chữ `[Zalo] QR code saved to .../zalo_qr.png`.
   - Mở file ảnh đó và dùng ứng dụng Zalo trên điện thoại để quét mã.
4. **Kiểm tra Chat**: Thử gửi một tin nhắn cho bot trên Zalo và xác nhận bot có phản hồi.

### 3.2. Trạng Thái Build
- [x] Node.js worker build thành công.
- [x] Adapter Python được import sạch sẽ, không lỗi.
- [x] Hệ thống Registry đã nhận diện được nền tảng ZALO.
- [x] Merge với tag v2026.5.29.2 (v0.15.2) thành công, không mất code ZaloClaw.
- [x] Docker image build thành công với Hermes v0.15.2.
- [x] Phase 4 Access Control & Groups hoàn thành.
- [x] User/group info caching hoạt động.
- [x] Mention detection + requireMention hoạt động.

---

## PHẦN 4: Nhật Ký Log (Mô phỏng)

```
[Zalo] Starting worker process: node .../index.js
🚀 Zalo Worker starting...
🔑 No credentials found, please scan QR code.
[Zalo] QR code saved to C:\Users\...\.hermes\data\zalo_qr.png. Please scan to login.
✅ QR Login successful!
👂 Listening for Zalo messages...
```

---

## PHẦN 5: Quy Trình Cập Nhật Hermes Trong Tương Lai

Từ nay, mỗi khi có phiên bản Hermes mới từ `NousResearch`, quy trình cập nhật như sau:

```powershell
# 1. Kéo code mới từ Nous Research
git fetch upstream

# 2. Gộp code mới vào nhánh của bạn
git merge upstream/main

# 3. Giải quyết xung đột nếu có (thường chỉ ở file lõi gateway)
# ... sửa file nếu cần ...

# 4. Commit và đẩy lên GitHub cá nhân
git add .
git commit -m "Merge upstream vX.Y.Z"
git push origin main

# 5. Build lại Docker
cd D:\Antigravity\Hermes
docker compose build
docker compose up -d
```

> [!TIP]
> Các file ZaloClaw độc lập (`gateway/platforms/zalo.py`, `gateway/platforms/zalo/`) **sẽ không bao giờ bị xung đột** vì đây là file mới hoàn toàn không có trong upstream. Xung đột chỉ xảy ra ở file đã sửa đổi: `gateway/run.py` và đôi khi `.gitignore`.

### Kinh Nghiệm Từ Lần Merge v0.15.2

- **Nên merge theo tag release** (`git merge v2026.5.29.2`) thay vì `upstream/main` để có phiên bản ổn định, đã được test.
- **Commit code Zalo trước khi merge** — luôn push code của mình lên fork trước, tránh mất work khi có conflict.
- **Xung đột `gateway/run.py`** thường chỉ là conflict markers bao quanh vùng `_create_adapter` — giữ code Zalo + giữ code upstream, xóa markers là xong.
- **Docker cache** giúp build nhanh — chỉ các file thay đổi (`zalo.py`, `zalo/worker/`) rebuild lại, phần còn lại dùng cache.
