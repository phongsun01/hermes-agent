# Zalo Platform — Hướng Dẫn Sử Dụng

Hướng dẫn kết nối Hermes Agent với Zalo qua Zalo Platform Adapter.

## Tổng Quan

Zalo platform adapter sử dụng **Node.js subprocess worker** giao tiếp với Hermes qua JSON-RPC trên stdio. Worker dùng thư viện `zca-js` để kết nối với API của Zalo.

**Tính năng:**
- Tin nhắn văn bản với định dạng markdown (in đậm, in nghiêng, gạch ngang, gạch chân, code)
- Hỗ trợ media: ảnh, file, video
- Xử lý tin nhắn nhóm với kiểm soát @mention
- Kiểm soát truy cập: allowlist/denylist cho người dùng và nhóm
- Tự động refresh cookie để tránh hết hạn session
- Rate limiting để tránh bị khóa tài khoản
- 142 hành động Zalo API (nhắn tin, bạn bè, nhóm, bình chọn, nhắc nhở, v.v.)

## Yêu Cầu Hệ Thống

- **Node.js ≥ 22** — bắt buộc cho `zca-js`
- **Hermes Agent** — đã cài đặt và cấu hình
- **Tài khoản Zalo** — tài khoản sẽ đóng vai trò bot

## Cài Đặt Nhanh

### 1. Cài Dependencies

```bash
cd gateway/platforms/zalo/worker
npm install
npm run build
```

### 2. Kích Hoạt Zalo Platform

Ở chế độ Hermes gateway, Zalo được tự động phát hiện nếu worker đã build. Không cần cấu hình thêm cho sử dụng cơ bản.

### 3. Khởi Động Gateway

```bash
hermes gateway
```

Lần đầu khởi động, bạn sẽ thấy:
```
[Zalo] 🔑 No credentials found, please scan QR code.
[Zalo] QR code saved to ~/.hermes/data/zalo_qr.png. Please scan to login.
```

### 4. Quét Mã QR

1. Mở Zalo trên điện thoại
2. Vào Cài đặt → Quét mã QR
3. Quét mã QR tại `~/.hermes/data/zalo_qr.png`
4. Đợi thông báo "✅ QR Login successful!"

Session được lưu tự động. Các lần khởi động sau sẽ dùng credentials đã lưu.

## Cấu Hình

### Cấu Hình Cơ Bản (`~/.hermes/config.yaml`)

```yaml
zalo:
  enabled: true
  extra:
    dm_policy: "open"           # open | closed | allowlist | denylist
    group_policy: "open"        # open | closed | allowlist | denylist
    require_mention: false      # yêu cầu @mention trong nhóm
    allowlisted_users: ""       # danh sách Zalo user IDs, cách nhau bằng dấu phẩy
    denylisted_users: ""        # danh sách user IDs bị chặn
    allowlisted_groups: ""      # danh sách group IDs được phép
    denylisted_groups: ""       # danh sách group IDs bị chặn
    bot_name: "MyBot"           # tên bot để phát hiện mention
```

### Biến Môi Trường

| Biến | Mặc Định | Mô Tả |
|------|----------|-------|
| `ZALO_DM_POLICY` | `open` | Chính sách tin nhắn riêng (DM) |
| `ZALO_GROUP_POLICY` | `open` | Chính sách tin nhắn nhóm |
| `ZALO_REQUIRE_MENTION` | `false` | Yêu cầu @mention trong nhóm |
| `ZALO_ALLOWLISTED_USERS` | `""` | Danh sách user IDs được phép (cách nhau bởi dấu phẩy) |
| `ZALO_DENYLISTED_USERS` | `""` | Danh sách user IDs bị chặn |
| `ZALO_ALLOWLISTED_GROUPS` | `""` | Danh sách group IDs được phép |
| `ZALO_DENYLISTED_GROUPS` | `""` | Danh sách group IDs bị chặn |
| `ZALO_BOT_NAME` | `null` | Tên bot để phát hiện mention |
| `ZALO_BOT_USER_ID` | `null` | User ID của bot để phát hiện mention |
| `ZALO_MENTION_PATTERNS` | `[]` | Mảng JSON các regex pattern |
| `ZALO_COOKIE_SAVE_INTERVAL_MS` | `1800000` | Khoảng thời gian tự lưu cookie (30 phút) |
| `ZALO_SESSION_CHECK_INTERVAL_MS` | `3600000` | Khoảng thời gian kiểm tra session (60 phút) |
| `ZALO_RATE_INTERVAL_MS` | `1000` | Khoảng cách tối thiểu giữa các tin nhắn (1 giây) |
| `ZALO_RATE_MAX_BACKOFF_MS` | `30000` | Độ trễ backoff tối đa khi lỗi (30 giây) |

### Chính Sách Kiểm Soát Truy Cập

**DM Policy (Tin nhắn riêng):**
- `open` — bất kỳ ai cũng có thể nhắn tin cho bot (mặc định)
- `closed` — không cho phép nhắn tin riêng
- `allowlist` — chỉ user trong danh sách mới nhắn được
- `denylist` — user trong danh sách bị chặn nhắn tin

**Group Policy (Tin nhắn nhóm):**
- `open` — bot phản hồi trong tất cả nhóm (mặc định)
- `closed` — bot bỏ qua tất cả nhóm
- `allowlist` — bot chỉ phản hồi trong nhóm được liệt kê
- `denylist` — bot bỏ qua các nhóm được liệt kê

**Kiểm Soát Mention:**
Khi `require_mention: true`, bot chỉ phản hồi trong nhóm khi được @mention. Mention được phát hiện qua:
- Tên bot trong tin nhắn (không phân biệt hoa thường): `@MyBot` hoặc `MyBot`
- User ID của bot trong tin nhắn
- Định dạng tag `[mention:USER_ID:Name]`
- Regex pattern tùy chỉnh qua `ZALO_MENTION_PATTERNS`

## Quản Lý Session

### Tự Động Lưu Cookie

Worker tự động lưu cookie đã refresh mỗi **30 phút**. Điều này giúp tránh hết hạn session trong quá trình hoạt động bình thường. Khi worker khởi động lại, nó sẽ dùng cookie mới nhất đã lưu.

> **Lưu ý:** Thao tác này chỉ đọc cookie từ memory và ghi ra file local, **không gọi API hay network request**, không tốn rate limit.

### Giám Sát Session

Mỗi **60 phút**, worker kiểm tra session còn hợp lệ hay không bằng cách đọc user ID từ cached context (local, không network). Nếu phát hiện lỗi xác thực:

1. **1-2 lần lỗi**: Cảnh báo warning ghi vào Hermes logs
2. **3+ lần lỗi liên tiếp**: Cảnh báo critical + tự động trigger QR re-login

> **Lưu ý:** Health check chỉ đọc `getOwnId()` từ cached context, **không gọi API hay network request**.

### QR Re-Login Thủ Công

Nếu cần trigger QR re-login thủ công:

```bash
# Qua IPC (nếu gateway đang chạy)
# Adapter có method trigger_qr_login()
```

Hoặc đơn giản xóa file credentials và khởi động lại:

```bash
rm ~/.hermes/data/zaloclaw-credentials.json
hermes gateway
```

## Rate Limiting

Worker áp dụng khoảng cách tối thiểu giữa các tin nhắn gửi đi để tránh bị Zalo khóa tài khoản:

- **Mặc định**: 1 tin nhắn mỗi giây
- **Exponential backoff**: Khi có lỗi liên tiếp, độ trễ tăng gấp đôi (1s → 2s → 4s → ... → tối đa 30s)
- **Cấu hình được**: Qua `ZALO_RATE_INTERVAL_MS` và `ZALO_RATE_MAX_BACKOFF_MS`

## Công Cụ send_message

Agent có thể chủ động gửi tin nhắn đến Zalo từ bất kỳ platform nào:

```
send_message(target="zalo", message="Xin chào từ Hermes!")
send_message(target="zalo:chat_id", message="Tin nhắn trực tiếp")
```

Hỗ trợ gửi media qua cú pháp `MEDIA:/đường/dẫn/đến/file`.

## Cron Delivery

Cron jobs có thể gửi kết quả đến Zalo:

```bash
hermes cron add --schedule "every 1h" --target "zalo" --prompt "Kiểm tra trạng thái hệ thống"
```

## Xử Lý Sự Cố

### Worker không khởi động

```
[Zalo] Worker script not found at ... Did you run 'npm run build'?
```

**Khắc phục:**
```bash
cd gateway/platforms/zalo/worker
npm install
npm run build
```

### Session hết hạn

```
[Zalo Session] CRITICAL: Zalo session expired. QR re-login required.
```

**Khắc phục:** Worker sẽ tự động trigger QR re-login. Quét mã QR mới.

### Cảnh báo rate limit

```
[RateLimiter] Backoff: 2000ms (consecutive errors: 2)
```

**Khắc phục:** Đây là bình thường. Worker đang tăng độ trễ để tránh bị khóa. Nếu liên tục, tăng `ZALO_RATE_INTERVAL_MS`.

### Worker crash loop

```
[Zalo] Worker died with exit code 1
[Zalo] Restarting worker in 5s (attempt 1/10)
```

**Khắc phục:** Kiểm tra stderr logs để tìm lỗi cụ thể. Nguyên nhân phổ biến:
- Node.js version < 22
- Thiếu dependency `zca-js`
- File credentials bị hỏng

### Không nhận tin nhắn trong nhóm

**Kiểm tra:**
1. `group_policy` không phải `closed`
2. Nếu `require_mention: true`, đảm bảo bạn đang @mention bot
3. Bot user ID được set đúng trong `ZALO_BOT_USER_ID`

## Metrics

Adapter theo dõi:
- Số tin nhắn gửi/nhận
- Số lỗi
- Số lần restart
- Thời gian hoạt động (uptime)
- Số request đang chờ

Truy cập qua `adapter.get_metrics()` trong Python hoặc kiểm tra gateway logs.

## Cấu Trúc Thư Mục

```
gateway/platforms/zalo/
├── __init__.py
├── adapter.py              # Python adapter (không dùng, xem zalo.py)
├── worker/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── index.ts        # Worker entry + IPC loop
│   │   ├── client.ts       # zca-js wrapper + quản lý session
│   │   ├── credentials.ts  # Lưu trữ credentials
│   │   ├── actions.ts      # 142 Zalo API actions + rate limiter
│   │   ├── access-control.ts # DM/group policy, mention gating
│   │   ├── media.ts        # Xử lý media, caching, định dạng
│   │   ├── ipc.ts          # IPC protocol types
│   │   └── __tests__/
│   │       └── rate-limiter.test.ts
│   └── dist/               # JS đã biên dịch (gitignored)
└── README.md

gateway/platforms/zalo.py   # Python adapter chính
```
