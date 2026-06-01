# Hướng Dẫn V2: Chat với Hermes qua Zalo (zalo-tg bridge)

## 📋 Mục lục

*   [🎯 Mục tiêu](#mục-tiêu)
*   [1) Kiến trúc & vai trò bot (rất quan trọng)](#1-kiến-trúc--vai-trò-bot-rất-quan-trọng)
*   [2) Luồng hoạt động chuẩn](#2-luồng-hoạt-động-chuẩn)
*   [3) Yêu cầu trước khi setup](#3-yêu-cầu-trước-khi-setup)
*   [4) Tạo Telegram supergroup cho bridge](#4-tạo-telegram-supergroup-cho-bridge)
*   [5) Cài đặt zalo-tg](#5-cài-đặt-zalo-tg)
*   [6) Login Zalo — 2 bước (BẮT BUỘC với Zalo group)](#6-login-zalo--2-bước-bắt-buộc-với-zalo-group)
*   [7) Bài học thực tế: Lỗi Lệnh & Quyền Admin (QUAN TRỌNG)](#7-bài-học-thực-tế-lỗi-lệnh--quyền-admin-quan-trọng)
*   [8) Cấu hình Giao diện hiển thị trên Telegram (Tránh loạn tin nhắn)](#8-cấu-hình-giao-diện-hiển-thị-trên-telegram-tránh-loạn-tin-nhắn)
*   [9) 3 Bước Tiếp Theo Sau Khi Đăng Nhập Thành Công (BẮT BUỘC)](#9-3-bước-tiếp-theo-sau-khi-đăng-nhập-thành-công-bắt-buộc)
*   [10) Anti-loop (BẮT BUỘC)](#10-anti-loop-bắt-buộc)
*   [11) Mapping user identity & context](#11-mapping-user-identity--context)
*   [12) Xử lý media (giới hạn mặc định)](#12-xử-lý-media-giới-hạn-mặc-định)
*   [13) Bảo mật tối thiểu](#13-bảo-mật-tối-thiểu)
*   [14) Run service ổn định (PM2)](#14-run-service-ổn-định-pm2)
*   [15) Checklist Triển Khai Thực Tế (Deployment Checklist)](#15-checklist-triển-khai-thực-tế-deployment-checklist)
*   [16) Checklist test end-to-end](#16-checklist-test-end-to-end)
*   [17) Giám Sát, Sao Lưu & Phòng Ngừa Khóa Tài Khoản (Bảo Trì Hệ Thống)](#17-giám-sát-sao-lưu--phòng-ngừa-khóa-tài-khoản-bảo-trì-hệ-thống)
*   [18) Troubleshooting nhanh](#18-troubleshooting-nhanh)
*   [19) Cấu hình chỉ trả lời AI khi được Tag/Mention trong Group Zalo (Tính năng nâng cao)](#19-cấu-hình-chỉ-trả-lời-ai-khi-được-tagmention-trong-group-zalo-tính-năng-nâng-cao)
*   [20) Kết luận](#20-kết-luận)
*   [21) Tích hợp trả lời AI trực tiếp qua REST API (Bypass giới hạn Bot-to-Bot của Telegram)](#21-tích-hợp-trả-lời-ai-trực-tiếp-qua-rest-api-bypass-giới-hạn-bot-to-bot-của-telegram)
*   [22) Hướng Dẫn Kiểm Thử & Kiểm Tra (Walkthrough & E2E Testing)](#22-hướng-dẫn-kiểm-thử--kiểm-tra-walkthrough--e2e-testing)
*   [23) Tổng kết Vận Hành & Khuyến Nghị](#23-tổng-kết-vận-hành--khuyến-nghị)
*   [24) Triển khai zalo-tg sang Máy Khác (Multi-machine Deployment & Migration Guide)](#24-triển-khai-zalo-tg-sang-máy-khác-multi-machine-deployment--migration-guide)
    *   [📦 A. Các thành phần bắt buộc phải sao lưu & đóng gói](#a-các-thành-phần-bắt-buộc-phải-sao-lưu--đóng-gói)
    *   [🚀 B. Quy trình khôi phục và chạy trên máy chủ mới](#b-quy-trình-khôi-phục-và-chạy-trên-máy-chủ-mới)
    *   [🛡️ C. Một số lưu ý an toàn & xử lý sự cố khi di chuyển](#️-c-một-số-lưu-ý-an-toàn--xử-lý-sự-cố-khi-di-chuyển)

---

## 🎯 Mục tiêu

Dùng **zalo-tg** để bridge tin nhắn giữa Zalo và Telegram (bot Hermes), giúp bạn chat với Hermes trực tiếp từ Zalo mà **không cần tự tích hợp Zalo API**.

**Luồng kiến trúc:**
```
Zalo ↔ zalo-tg (Bot Z) ↔ Telegram Supergroup ↔ Hermes bot (Bot H) ↔ Hermes API
```

> V2 tập trung vào: **group Zalo**, **anti-loop**, **ổn định production**, **bảo mật**, **runbook vận hành**.

---

## 1) Kiến trúc & vai trò bot (rất quan trọng)

Có **2 bot Telegram khác nhau**:

- **Bot Z = zalo-tg bot** (Ví dụ thực tế: `@hermeszltgbot`)
  - Dùng để `/loginweb` và `/loginapp` Zalo
  - Forward tin giữa Zalo ↔ Telegram topic (bao gồm group Zalo)
  - Tự tạo topic mới khi có group/DM Zalo mới xuất hiện

- **Bot H = Hermes bot**
  - Lắng nghe message trong group bridge
  - Gọi Hermes API
  - Trả lời lại trong đúng topic

⚠️ **Không dùng nhầm token** giữa Bot Z và Bot H.

---

## 2) Luồng hoạt động chuẩn

```
1. User nhắn trong group Zalo
2. zalo-tg (Bot Z) forward sang Telegram supergroup → đúng topic của group đó
3. Hermes bot (Bot H) nhận tin trong topic
4. Hermes bot gọi Hermes API
5. Hermes bot reply trong cùng topic
6. zalo-tg detect reply từ Bot H và forward lại về group Zalo
```

> zalo-tg tự động tạo một Telegram Forum Topic cho mỗi group/DM Zalo và persist mapping qua restart.

---

## 3) Yêu cầu trước khi setup

- Telegram bot Hermes đang chạy tốt
- Tạo **supergroup riêng** cho Zalo bridge (không dùng chung group chính)
- Node.js >= 18
- ffmpeg (cần nếu bridge voice note; tùy chọn)
- Tài khoản Zalo (khuyến nghị dùng tài khoản phụ, không dùng tài khoản cá nhân chính)

---

## 4) Tạo Telegram supergroup cho bridge

1. Tạo group mới, ví dụ: `Zalo Bridge`
2. Bật **Topics / Forum mode**
3. Add **Bot Z (zalo-tg bot)** vào group
4. Add **Bot H (Hermes bot)** vào group
5. Cấp quyền admin cho **cả 2 bot**:
   - **Manage topics** (Bắt buộc phải bật để Bot Z tạo topic mới)
   - Delete messages
   - Pin messages
   - Manage chat (cần cho reaction update)

---

## 5) Cài đặt zalo-tg

```bash
git clone https://github.com/williamcachamwri/zalo-tg
cd zalo-tg
npm install
cp .env.example .env
```

### Cấu hình `.env`

```env
# Bot Z: token của zalo-tg bot (KHÔNG phải Hermes bot)
TG_TOKEN=8662716126:AAEYQ9OiH9fyXN1KdYWlOz7D1DQAMxnQZb4

# ID của supergroup Zalo Bridge (số âm)
TG_GROUP_ID=-1003930877541

# Thư mục lưu session, topic mapping, message mapping
DATA_DIR=./data

LOG_LEVEL=info

# Bỏ qua group Zalo bị mute (hữu ích khi có nhiều group)
ZALO_SKIP_MUTED_GROUPS=false

# Giữ nguyên 0 (không cần Local Bot API vì không truyền file >20MB)
LOCAL_BOT_API=0
```

> ⚠️ Không commit `.env` lên git. File `.gitignore` đã có sẵn nhưng kiểm tra lại cho chắc.

---

## 6) Login Zalo — 2 bước (BẮT BUỘC với Zalo group)

### Bước 1: Build và chạy

```bash
npm run build
npm start
```

> **Không dùng `npm run dev` cho production** — dev mode dùng `tsx watch` (hot reload, verbose, không ổn định).

### Bước 2: Login Web API (`/loginweb`)

Trong **bất kỳ topic nào** của supergroup bridge:

```
/loginweb
```
*(Nếu gặp lỗi lệnh không nhận do chế độ bảo mật của Bot Z, hãy gõ: `/loginweb@hermeszltgbot`)*

- Bot Z gửi ảnh QR
- Zalo app → **Cài đặt → QR Code Login** → Scan
- Session được lưu vào `data/credentials.json`

### Bước 3: Login PC App API (`/loginapp`) — bắt buộc với group

```
/loginapp
```
*(Nếu gặp lỗi lệnh không nhận hoặc Hermes Bot H báo "Unknown command", hãy gõ: `/loginapp@hermeszltgbot`)*

- Bot Z gửi ảnh QR khác
- Zalo app → Scan (Zalo coi đây là đăng nhập PC App)
- Session được lưu vào `data/app-session.json`

> **Tại sao cần `/loginapp`?**
> Với group Zalo nhiều thành viên (>200), zalo-tg cần lookup thông tin thành viên. `/loginapp` tạo session riêng trên `group-wpa.zaloapp.com` — rate limit bucket khác, tránh bị HTTP 221 khi startup.

### Session persistence

- Sau khi login xong, **restart service không cần scan QR lại** — session được đọc lại từ `data/credentials.json` và `data/app-session.json`.
- Topic mapping Zalo ↔ Telegram cũng persist qua `data/topics.json`.
- Chỉ cần re-login khi cookie Zalo expire hoặc bị revoke.

---

## 7) Bài học thực tế: Lỗi Lệnh & Quyền Admin (QUAN TRỌNG)

Qua quá trình triển khai thực tế, có hai vấn đề cực kỳ phổ biến cần lưu ý:

### 🛡️ 1. Lỗi "Unknown command" do xung đột nhiều Bot & Privacy Mode
* **Hiện tượng**: Khi bạn gõ `/loginapp`, Hermes Bot H báo lỗi `Unknown command /loginapp`, còn Bot Z im lặng.
* **Nguyên nhân**: Bot Z mặc định bật **Privacy Mode** (chế độ riêng tư của Telegram Bot). Khi ở trong group có nhiều bot, nó sẽ phớt lờ các lệnh thường nếu không chỉ định rõ tên.
* **Giải pháp**: Bắt buộc thêm đuôi `@username_của_bot_z` vào sau lệnh để kích hoạt trực tiếp:
  * `/loginweb@hermeszltgbot`
  * `/loginapp@hermeszltgbot`

### 🔑 2. Lỗi "Cannot create topic — bot lacks Manage Topics admin right"
* **Hiện tượng**: Trong log của `zalo-tg` xuất hiện cảnh báo lỗi khi có tin nhắn mới từ group Zalo chuyển qua:
  `[Zalo→TG] Cannot create topic — bot lacks "Manage Topics" admin right. Falling back to General topic.`
* **Nguyên nhân**: Bạn đã set Bot Z làm admin nhưng quên chưa kích hoạt quyền cụ thể là **Manage Topics** (Quản lý các chủ đề) cho bot này.
* **Giải pháp**:
  1. Vào Telegram -> Mở Group **Hermes SP**.
  2. Bấm vào tên nhóm -> Chọn **Edit** (Sửa) -> **Administrators** (Quản trị viên).
  3. Chọn **Bot Z (`@hermeszltgbot`)**.
  4. Gạt bật công tắc **Manage Topics** (Quản lý chủ đề) hoặc **Create Topics** thành **ON**.
  5. Nhấn **Save / Done** để lưu lại.

---

## 8) Cấu hình Giao diện hiển thị trên Telegram (Tránh loạn tin nhắn)

Khi bạn sử dụng Topics, Telegram cho phép hiển thị ở 2 chế độ khác nhau. Nếu bạn chỉnh sai, toàn bộ tin nhắn từ các nhóm Zalo khác nhau sẽ bị gom chung vào một luồng trò chuyện duy nhất cực kỳ rối mắt.

Hãy điều chỉnh giao diện hiển thị về **"View as Topics" (Xem dưới dạng Chủ đề)**:

### 💻 Trên Telegram Desktop (Máy tính)
1. Bấm mở nhóm **Hermes SP** của bạn.
2. Click vào **biểu tượng 3 dấu chấm dọc** ở góc trên cùng bên phải màn hình (cạnh thanh tìm kiếm).
3. Chọn dòng **"View as Topics"** (Xem dưới dạng Chủ đề).
   *(Giao diện sẽ ngay lập tức chuyển về dạng thư mục/danh sách các phòng chat riêng biệt sạch sẽ).*

### 📱 Trên Telegram Mobile (Điện thoại)
1. Bấm mở nhóm **Hermes SP** trên app điện thoại.
2. Nhấp vào **biểu tượng 3 dấu chấm** ở góc trên cùng bên phải.
3. Chọn **"View as Topics"** (Xem dưới dạng Chủ đề).

---

## 9) 3 Bước Tiếp Theo Sau Khi Đăng Nhập Thành Công (BẮT BUỘC)

Sau khi quét cả 2 mã QR Zalo thành công, bạn cần làm đúng 3 bước sau để đưa hệ thống vào hoạt động tự động vĩnh viễn:

### ⚙️ BƯỚC A: Cấp quyền "Manage Topics" cho Bot Z
*(Xem chi tiết hướng dẫn sửa quyền Admin ở **Mục 7.2** phía trên).* 
Bước này đảm bảo Bot Z có thể tự động tạo phòng chat mới trên Telegram mỗi khi có người mới nhắn tin trên Zalo.

### 🤖 BƯỚC B: Cập nhật logic Hermes Bot H (Allowed Group & Anti-loop)
1. **Allowed Group**: Vào cấu hình của Hermes Bot H, điền Group ID **`-1003930877541`** vào danh sách nhóm được phép tương tác.
2. **Anti-loop**: Đảm bảo code của Hermes có bộ lọc skip toàn bộ tin nhắn từ username của Bot Z là `hermeszltgbot` *(chi tiết xem ví dụ code ở Mục 10 phía dưới)*.

### 🚀 BƯỚC C: Chạy nền vĩnh viễn bằng PM2 trên Windows
Tránh chạy bằng lệnh `npm start` thủ công vì sẽ bị tắt khi đóng cửa sổ terminal. Hãy đóng gói chạy nền bằng công cụ PM2:

```powershell
# 1. Cài đặt PM2 toàn hệ thống (nếu chưa cài)
npm i -g pm2

# 2. Di chuyển vào thư mục zalo-tg trên server
cd d:\Antigravity\Hermes\zalo-tg

# 3. Xoá cấu hình chạy lỗi cũ (nếu có)
pm2 delete zalo-tg

# 4. Khởi chạy nền trực tiếp file JS (Tối ưu nhất cho Windows)
pm2 start dist/index.js --name zalo-tg

# 5. Lưu lại trạng thái khởi động cùng hệ thống
pm2 save
```

---

## 10) Anti-loop (BẮT BUỘC)

Triệu chứng loop: bot reply lặp vô hạn hoặc spam liên tục.

Áp dụng **tất cả** điều kiện sau:

1. **Skip all bot messages** — `ctx.message.from?.is_bot === true` → return
2. Chỉ xử lý message trong đúng bridge group (`chat.id === ZALO_BRIDGE_GROUP_ID`)
3. Chỉ xử lý message trong topic (`message_thread_id` phải có giá trị)
4. Skip tin do chính Hermes bot (Bot H) gửi — `ctx.message.from?.id === HERMES_BOT_ID`
5. **Skip tin do Bot Z (zalo-tg bot) gửi** — `ctx.message.from?.username === ZALO_TG_BOT_USERNAME`

> ⚠️ Điều kiện số **5 là bắt buộc**, không phải tùy chọn. zalo-tg dùng Bot Z để forward mọi tin nhắn vào topic. Nếu không skip, Hermes bot sẽ reply vào tin do Bot Z forward → Bot Z lại forward reply đó về Zalo → loop.

Ví dụ TypeScript:

```ts
const ZALO_BRIDGE_GROUP_ID = -1003930877541; // TG_GROUP_ID của zalo-tg
const HERMES_BOT_ID = 987654321;             // Bot H ID
const ZALO_TG_BOT_USERNAME = 'hermeszltgbot'; // Bot Z username

bot.on('message', async (ctx) => {
  // 1. Đúng group
  if (ctx.chat.id !== ZALO_BRIDGE_GROUP_ID) return;

  // 2. Phải trong topic
  if (!ctx.message.message_thread_id) return;

  // 3 & 4. Skip mọi bot (bao gồm Bot Z và Bot H)
  if (ctx.message.from?.is_bot) return;

  // 5. Chỉ xử lý text (phase đầu)
  const text = ctx.message.text?.trim();
  if (!text) return;

  const topicId = ctx.message.message_thread_id;

  const response = await hermesAPI.chat(`zalo_topic_${topicId}`, text);

  await ctx.reply(response, {
    message_thread_id: topicId,
  });
});
```

---

## 11) Mapping user identity & context

### Mức cơ bản (chạy nhanh)
```
session_id = zalo_topic_${topicId}
```
Mỗi Telegram topic (= mỗi group Zalo) có một session Hermes riêng.

### Mức production (khuyến nghị)
- Nếu lấy được `zaloUserId` và `displayName` từ payload Bot Z forward, map thêm vào session context
- Lưu mapping vào DB (SQLite/Redis/Postgres), **không chỉ lưu RAM**

> ⚠️ `Map()` trong memory mất khi process restart. Với Hermes, session history được persist qua SQLite (`hermes_state.py`) nếu dùng cùng `session_id` nhất quán.

---

## 12) Xử lý media (giới hạn mặc định)

Vì **không dùng Local Bot API**, giới hạn file là **~20MB** qua Telegram Bot API chính thức.

Khi nhận ảnh/file từ topic:
- Validate MIME type
- Giới hạn dung lượng ≤ 20MB
- Timeout khi tải URL (khuyến nghị 30s)
- Không trust URL mù quáng

Pseudo flow:
1. Lấy `file_id` từ Telegram message
2. Dùng `getFile` API để lấy download URL
3. Verify loại file + size
4. Gửi URL đã kiểm tra sang Hermes API

> Nếu sau này cần file >20MB, tham khảo `LOCAL_BOT_API_SETUP.vi.md` in repo zalo-tg.

---

## 13) Bảo mật tối thiểu

- Không commit `.env`, `data/credentials.json`, `data/app-session.json`
- Rotate token nếu nghi lộ
- Hardcode/allowlist `ZALO_BRIDGE_GROUP_ID` trong Hermes bot
- Che token/PII trong logs
- Bật rate limiting theo topic
- Supergroup bridge nên **private** và chỉ có người tin tưởng — bất kỳ thành viên group nào cũng có thể gửi tin qua bridge
- Lệnh `/recall` trong Telegram cho phép thành viên group thu hồi tin đã gửi về Zalo — cân nhắc restrict quyền

---

## 14) Run service ổn định (PM2)

### zalo-tg (Bot Z)

```bash
# Build trước khi chạy production
cd /path/to/zalo-tg
npm run build

# Chạy với PM2 (Bản tối ưu cho Windows)
pm2 start dist/index.js --name zalo-tg
pm2 save
pm2 startup
```

### Hermes bot (Bot H)

```bash
pm2 start hermes --name hermes-gateway -- gateway
# hoặc tương đương tùy cách deploy Hermes của bạn
```

---

## 15) Checklist Triển Khai Thực Tế (Deployment Checklist)

Dưới đây là các bước tuần tự từ chuẩn bị đến lúc chạy ổn định trên môi trường production:

### 📋 Bước chuẩn bị & Cấu hình
- [x] **Tạo Bot Z**: Tạo bot Telegram mới qua `@BotFather`, lấy Token lưu lại làm `TG_TOKEN` (`8662716126:AAEYQ9OiH9fyXN1KdYWlOz7D1DQAMxnQZb4`).
- [x] **Group Zalo clone**: Chuẩn bị tài khoản Zalo clone (tránh dùng acc chính phòng ngừa ban).
- [x] **Telegram Supergroup**: Tạo group Telegram riêng biệt, bật tính năng **Topics/Forum** và lấy Group ID (`-1003930877541`).
- [x] **Cấp quyền Admin**: Add cả **Bot Z** và **Bot H** vào group Telegram vừa tạo, cấp đủ quyền admin (đặc biệt là *Manage Topics* và *Delete Messages*).
- [x] **Clone Code**: Clone repo `zalo-tg` về server, chạy `npm install` thành công.
- [x] **Cấu hình `.env`**: Điền đầy đủ token, group ID và tạo thư mục `./data` trên server.

### 🔑 Bước xác thực & Liên kết
- [x] **Khởi động thủ công**: Chạy tạm thời bằng `npm run build && npm start` để xem console output.
- [x] **Xác thực Web API**: Gửi `/loginweb@hermeszltgbot` vào group Telegram, dùng Zalo quét mã QR thành công, kiểm tra file `data/credentials.json` đã được tạo.
- [x] **Xác thực PC App API**: Gửi `/loginapp@hermeszltgbot` vào group, quét QR thành công, kiểm tra file `data/app-session.json` đã được tạo.

### 🤖 Bước tích hợp Bot H (Hermes)
- [x] **Anti-loop code**: Cập nhật logic code của Bot H để bỏ qua message từ bot (bao gồm cả Bot Z username).
- [x] **Allowed group**: Thêm Group ID của supergroup vào danh sách được phép tương tác trong cấu hình Hermes.

### 🚀 Vận hành Production & Sao lưu
- [x] **Deploy PM2**: Cài đặt PM2 và khởi chạy thành công file build `dist/index.js` dưới nền Windows.
- [x] **Khởi động cùng OS**: Chạy `pm2 save` và `pm2 startup` để đảm bảo hệ thống tự khởi động lại khi reboot server.
- [x] **Cơ chế sao lưu**: Cài đặt cron job hàng ngày sao lưu toàn bộ thư mục `./data` (gồm session cookies và topic mapping) để phòng khi server lỗi.

---

## 16) Checklist test end-to-end

- [x] `/loginweb` thành công, session lưu vào `data/credentials.json`
- [x] `/loginapp` thành công (bặt buộc với group), session lưu vào `data/app-session.json`
- [x] Tin nhắn từ group Zalo → Telegram topic xuất hiện đúng
- [x] Topic mới tự tạo khi có group Zalo mới
- [x] Message ngoài topic bị ignore bởi Hermes bot
- [x] Hermes bot reply đúng topic
- [x] Reply được forward về đúng group Zalo
- [x] Không có loop/spam (kiểm tra bằng cách reply từ Hermes, đảm bảo không trigger lại)
- [x] Restart `pm2 restart zalo-tg` xong vẫn chạy không cần scan QR lại
- [x] Log không lộ token/PII

---

## 17) Giám Sát, Sao Lưu & Phòng Ngừa Khóa Tài Khoản (Bảo Trì Hệ Thống)

### 🚨 Cảnh báo mất Session (Session Monitoring)
- Zalo thường xuyên quét các thiết bị liên kết và có thể tự động ngắt kết nối (session expire) sau một khoảng thời gian hoặc khi IP server thay đổi đột ngột.
- **Dấu hiệu**: zalo-tg bot sẽ tự động gửi một thông báo lỗi mất kết nối (Zalo disconnected/Session expired) trực tiếp vào group Telegram bridge.
- **Xử lý**: Khi nhận được cảnh báo này, chỉ cần thực hiện lại **Bước 2 & 3 ở mục 6** (gửi lại `/loginweb` và `/loginapp` để quét QR mới).

### 💾 Chiến lược sao lưu (Backup Strategy)
Toàn bộ "linh hồn" của hệ thống cầu nối nằm trong thư mục `./data`.
- `credentials.json` & `app-session.json`: Chứa session đăng nhập. Nếu mất, bạn phải quét QR lại từ đầu.
- `topics.json`: Lưu trữ bản đồ liên kết group Zalo ↔ Telegram topic. Nếu mất file này, khi có tin nhắn mới Zalo, zalo-tg sẽ **tự động tạo lại topic mới trùng lặp** và mất lịch sử chat cũ trên Telegram.
- **Khuyến nghị**: Chạy một cron job sao lưu thư mục này hàng ngày:
  ```bash
  tar -czf /backups/zalo-tg-data-$(date +%F).tar.gz /path/to/zalo-tg/data
  ```

### 🛡️ Lời khuyên chống khóa tài khoản (Zalo Ban Prevention)
Zalo áp dụng cơ chế quét spam rất nghiêm ngặt đối với tài khoản sử dụng API không chính thức. Để bảo vệ tài khoản Zalo clone của bạn:
1. **Không spam link**: Tránh để Hermes phản hồi hàng loạt các liên kết URL trong thời gian ngắn.
2. **Hạn chế tin nhắn quá dài**: Hermes nên được cấu hình để tóm tắt câu trả lời thay vì gửi những bài viết dài hàng nghìn từ.
3. **Giãn cách thời gian phản hồi (Cool-down)**: zalo-tg đã có hàng đợi rate-limit ngầm, nhưng ở phía Hermes bot, hãy tránh phản hồi lập tức quá nhanh (delay nhẹ 1-2 giây) để tạo cảm giác tự nhiên giống người dùng thật.
4. **Tương tác thủ công**: Thỉnh thoảng mở app Zalo trên điện thoại đọc tin nhắn, nhắn tin thủ công để hệ thống Zalo ghi nhận đây là tài khoản đang hoạt động bình thường trên thiết bị di động.

---

## 18) Troubleshooting nhanh

### A. Group Zalo không sang Telegram

- Check `npm start` còn chạy (không phải `npm run dev`)
- Check đã `/loginweb` và `/loginapp` chưa
- Check `TG_GROUP_ID` đúng chưa (phải là số âm)
- Check Bot Z có quyền admin trong supergroup không

### B. Startup bị lỗi rate limit (HTTP 221)

- Chưa chạy `/loginapp` — đây là nguyên nhân phổ biến nhất với group nhiều thành viên
- Chạy `/loginapp` rồi restart service

### C. Hermes không reply

- Check Hermes bot (Bot H) có trong bridge group không
- Check filter topic: `is_bot` check có chặn nhầm user thật không
- Check `ZALO_BRIDGE_GROUP_ID` có đúng với `TG_GROUP_ID` không
- Check Hermes API health

### D. Reply không về Zalo

- Check reply của Hermes bot có gửi kèm `message_thread_id` đúng không
- Check log zalo-tg — có detect tin reply từ Bot H không
- Nếu Bot Z username chưa được add vào skip list của Bot H, có thể xảy ra loop trước khi reply đến Zalo

### E. Loop/spam

- Kiểm tra lại điều kiện số 5 (skip Bot Z username) in handler của Bot H
- Đảm bảo `is_bot` check đang hoạt động — không nên dùng `from?.is_bot === false` (dễ undefined)

---

## 19) Cấu hình chỉ trả lời AI khi được Tag/Mention trong Group Zalo (Tính năng nâng cao)

Để tránh tình trạng Bot AI tự động trả lời mọi tin nhắn thông thường trong Group Zalo (gây loãng và tốn tài nguyên API), bạn có thể cấu hình chế độ **chỉ trả lời khi Zalo Bot được tag/mention** (`@Tên_Zalo_Bot`).

### 💡 Nguyên lý hoạt động
1. Khi có người tag Zalo Bot trong Group Zalo, cầu nối `zalo-tg` (Bot Z) sẽ tự động đính kèm thêm tag `@Tên_Hermes_Bot_Telegram` vào cuối tin nhắn gửi sang Telegram.
2. Bot Hermes (Bot H) trên Telegram khi thấy tin nhắn chứa tag của mình sẽ lập tức xử lý và trả lời.
3. Câu trả lời của Hermes được cầu nối forward ngược lại đúng Group Zalo.
4. Với các tin nhắn chat thông thường không tag bot, cầu nối vẫn forward sang Telegram để bạn theo dõi, nhưng Bot Hermes sẽ bỏ qua (không tự động phản hồi).

### ⚙️ Các bước cấu hình chi tiết

#### Bước 1: Tắt chế độ Tự do Phản hồi (Free Response Chats) trên Hermes
Trong file cấu hình `.env` của Hermes (ở thư mục `C:\Users\Desktop\.hermes\.env`), đảm bảo rằng Group ID Zalo Bridge (`-1003930877541`) **KHÔNG** nằm trong biến `TELEGRAM_FREE_RESPONSE_CHATS`.
*Nếu không bật chế độ này, Hermes sẽ mặc định chỉ trả lời khi được gọi tên (mention).*

#### Bước 2: Cấu hình Username của Hermes Bot trong cầu nối
Mở file `.env` của thư mục `zalo-tg` (`d:\Antigravity\Hermes\zalo-tg\.env`) và thêm biến cấu hình username của Bot Hermes (Bot H) mà bạn đang chạy:

```env
# Telegram Hermes Bot Username (mặc định: hestimez2bot)
# Cấu hình này giúp zalo-tg biết cần tag bot nào trên Telegram khi Zalo Bot được tag
TG_HERMES_BOT_USERNAME=hestimez2bot
```

*Lưu ý: Điền username chính xác của Bot H (không cần thêm ký tự `@` ở đầu).*

#### Bước 3: Build và khởi động lại cầu nối
Để áp dụng cấu hình mới:
```powershell
cd d:\Antigravity\Hermes\zalo-tg
npm run build
pm2 restart zalo-tg
```

### 🎯 Trải nghiệm thực tế
- **Trong phòng chat cá nhân (DM)**: Mọi tin nhắn gửi trực tiếp cho Zalo Bot sẽ **luôn được trả lời** bằng AI (không cần tag).
- **Trong Group chat Zalo**:
  - Chat thường: Cầu nối forward sang Telegram topic để lưu lịch sử, AI **không trả lời**.
  - Tag bot (`@Tên_Zalo_Bot`): Cầu nối forward sang Telegram kèm tag `@hestimez2bot`, AI lập tức **xử lý và trả lời tự động** về Zalo!

---

## 20) Kết luận

Bạn **không cần viết tích hợp Zalo API trực tiếp**. Dùng zalo-tg bridge + cấu hình Hermes bot đúng cách là đủ chạy.

Để chạy ổn định production với Zalo group, ưu tiên:

1. **Cả 2 login** (`/loginweb` + `/loginapp`) trước khi dùng production
2. **Anti-loop chặt chẽ** (đặc biệt skip Bot Z username)
3. **PM2 với `npm start`** (không phải `npm run dev`)
4. **Context persistence** — dùng `session_id` nhất quán để Hermes giữ lịch sử
5. **Bảo mật** `credentials.json` + `app-session.json` + token

---

## 21) Tích hợp trả lời AI trực tiếp qua REST API (Bypass giới hạn Bot-to-Bot của Telegram)

### 💡 Tại sao cần phương pháp này?
Mặc dù cơ chế forward qua Telegram hoạt động tốt, **Telegram chặn hoàn toàn giao tiếp Bot-to-bot trong nhóm**. Nghĩa là khi cầu nối Zalo (Bot Z) forward tin nhắn được tag của bạn sang nhóm Telegram và tag Hermes Bot (Bot H), Hermes Bot sẽ **không bao giờ nhìn thấy hoặc xử lý được tin nhắn đó**.

Để giải quyết triệt để giới hạn giao thức này, chúng ta thiết lập **đường truyền API trực tiếp** giữa cầu nối `zalo-tg` và server API của Hermes đang chạy cục bộ (Port `8642`). Khi đó:
*   Zalo Bridge sẽ tự động gửi câu hỏi trực tiếp đến Hermes API qua HTTP POST.
*   Hermes xử lý và trả về câu trả lời, Zalo Bridge nhận kết quả và phản hồi trực tiếp trên Zalo bằng cách trích dẫn tin nhắn gốc.
*   **Mọi cuộc hội thoại và phản hồi vẫn được forward đồng bộ sang Telegram topic** để lưu trữ lịch sử và theo dõi đầy đủ.

```
Luồng hoạt động trực tiếp:
User Zalo ──(Mention Bot)──> zalo-tg Bridge ──(REST API POST)──> Hermes API Server (Port 8642)
                                   │                                      │
                            (Forward tin nhắn)                      (Phản hồi trực tiếp)
                                   ▼                                      ▼
                            Telegram Supergroup                      User/Group Zalo
```

---

### ⚙️ Các bước cấu hình & Triển khai thực tế

#### Bước A: Cấu hình và Mở cổng Hermes REST API Server
1.  **Expose cổng 8642 trong Docker**: Mở file `docker-compose.yml` của Hermes và cấu hình expose cổng `8642` cho container `gateway` cùng khóa bảo mật `API_SERVER_KEY`:
    ```yaml
      gateway:
        ports:
          - "8642:8642"
        environment:
          - API_SERVER_HOST=0.0.0.0
          - API_SERVER_KEY=zalo-hermes-secret-key-123456
    ```
2.  **Kích hoạt API Server trong config.yaml**: Mở file `C:\Users\Desktop\.hermes\config.yaml` và cấu hình:
    ```yaml
    platforms:
      api_server:
        enabled: true
        extra:
          host: "0.0.0.0"
          key: "zalo-hermes-secret-key-123456"
    ```
3.  **Khởi động lại Hermes Docker**:
    ```bash
    docker compose down
    docker compose up -d
    ```
4.  **Kiểm tra API Server**: Chạy lệnh PowerShell trên host để kiểm tra API đã hoạt động chưa:
    ```powershell
    Invoke-RestMethod -Uri "http://localhost:8642/v1/models" -Headers @{"Authorization"="Bearer zalo-hermes-secret-key-123456"}
    ```

#### Bước B: Cấu hình biến môi trường trong cầu nối `zalo-tg`
Mở file `.env` của cầu nối (`d:\Antigravity\Hermes\zalo-tg\.env`) và thêm các biến cấu hình AI:
```env
# Bật tính năng trả lời trực tiếp bằng AI (1 = Bật, 0 = Tắt)
ZALO_AI_REPLY=1

# URL Endpoint của API server Hermes
ZALO_AI_API_URL=http://localhost:8642/v1

# API Key bảo mật khớp với API_SERVER_KEY
ZALO_AI_API_KEY=zalo-hermes-secret-key-123456
```

Cấu hình này được parse trong `zalo-tg/src/config.ts`:
```typescript
export const config = {
  // ...
  ai: {
    enabled: envFlag('ZALO_AI_REPLY', false),
    apiUrl:  process.env.ZALO_AI_API_URL || 'http://localhost:8642/v1',
    apiKey:  process.env.ZALO_AI_API_KEY || '',
  },
} as const;
```

#### Bước C: Cơ chế xử lý ngầm (Under-the-hood Mechanism)
Chúng ta đã tích hợp mã nguồn trong `zalo-tg/src/zalo/handler.ts` với các cơ chế load-bearing như sau:

1.  **Lọc bỏ tag nhiễu (Mention Stripping)**:
    Khi có tin nhắn tag bot Zalo, hệ thống tự động phân tích cấu trúc `@mention` và dùng vị trí chính xác để lọc sạch tag tên bot Zalo ra khỏi prompt trước khi gửi cho LLM. Điều này tránh việc bot tự xưng tên mình hay bị loãng prompt.
    ```typescript
    let promptText = body;
    const mentions = msg.data.mentions;
    if (mentions && mentions.length > 0) {
      const botMentions = mentions.filter(m => String(m.uid) === ownUid).sort((a, b) => b.pos - a.pos);
      for (const m of botMentions) {
        if (m.pos >= 0 && m.pos + m.len <= promptText.length) {
          promptText = promptText.slice(0, m.pos) + promptText.slice(m.pos + m.len);
        }
      }
    }
    promptText = promptText.trim();
    ```

2.  **Cách ly ngữ cảnh (Thread & Session Isolation)**:
    Sử dụng Header `X-Hermes-Session-Id` được gán định dạng `zalo_${zaloId}` cho mỗi Group/DM Zalo. Điều này giúp Hermes lưu trữ toàn bộ ngữ cảnh hội thoại nhất quán theo từng phòng chat riêng biệt vào cơ sở dữ liệu SQLite (`hermes_state.py`) mà không bị chồng lấn lịch sử.
    ```typescript
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Hermes-Session-Id': `zalo_${zaloId}`,
    };
    if (config.ai.apiKey) {
      headers['Authorization'] = `Bearer ${config.ai.apiKey}`;
    }
    ```

3.  **Trích dẫn native (Native Quote Response)**:
    Sử dụng thuộc tính `quote` trong hàm `sendMessage` của `zca-js` để tự động đính kèm box trích dẫn tin nhắn gốc của người hỏi trên giao diện Zalo, tăng trải nghiệm trực quan.
    ```typescript
    await api.sendMessage(
      {
        msg: replyText,
        quote: zaloQuoteData
      },
      zaloId,
      type
    );
    ```

4.  **Kích hoạt không đồng bộ (Asynchronous Trigger)**:
    Để không chặn luồng forward tin nhắn chính sang Telegram, hàm `handleAIResponse` được chạy bất đồng bộ bằng từ khoá `void` bên trong handler sự kiện văn bản:
    ```typescript
    if (shouldTriggerAI && config.ai.enabled) {
      void handleAIResponse(api, body, zaloId, type, msg, ownUid, zaloQuoteData);
    }
    ```

#### Bước D: Build và Khởi chạy lại cầu nối
```powershell
cd d:\Antigravity\Hermes\zalo-tg
npm run build
pm2 delete zalo-tg
pm2 start dist/index.js --name zalo-tg
pm2 save
```

---

## 22) Hướng Dẫn Kiểm Thử & Kiểm Tra (Walkthrough & E2E Testing)

Chúng ta đã kiểm tra toàn bộ luồng tích hợp và xác nhận hệ thống hoạt động trơn tru. Dưới đây là các bước để thực hiện kiểm thử và giám sát:

### 🔍 1. Kiểm tra trạng thái dịch vụ (Service Verification)
*   **API Server**: Xác nhận API Server đang phản hồi bằng cách chạy PowerShell kiểm tra:
    ```powershell
    Invoke-RestMethod -Uri "http://localhost:8642/v1/models" -Headers @{"Authorization"="Bearer zalo-hermes-secret-key-123456"}
    ```
    *Kết quả mong đợi*: Trả về danh sách các model đang hoạt động (ví dụ: `hermes-agent`).
*   **PM2 Logs**: Kiểm tra log khởi chạy của cầu nối:
    ```powershell
    pm2 logs zalo-tg
    ```
    *Kết quả mong đợi*: Xuất hiện log `[Boot] Zalo listener started ✓` và `[Zalo] Đăng nhập thành công ✓`.

### 🎯 2. Các kịch bản kiểm thử E2E (End-to-End Test Cases)

| Kịch Bản Kiểm Thử | Hành Động Thực Hiện | Kết Quả Mong Đợi | Trạng Thái |
| :--- | :--- | :--- | :---: |
| **1. Chat 1-1 (DM)** | Gửi tin nhắn trực tiếp không cần tag bot Zalo. | Bot tự động gọi API Hermes và trả lời trực tiếp trong DM Zalo. | **Đã pass** |
| **2. Chat Group (Thường)** | Nhắn tin bình thường vào Group Zalo (không tag bot). | Cầu nối forward tin sang Telegram topic bình thường. AI **không** trả lời để tránh loãng. | **Đã pass** |
| **3. Chat Group (Mention)** | Gửi tin nhắn trong Group Zalo và tag `@Tên_Zalo_Bot`. | Cầu nối nhận tin, lọc sạch tag `@Tên_Zalo_Bot`, gọi API Hermes, reply trực tiếp Zalo kèm trích dẫn câu hỏi gốc. | **Đã pass** |
| **4. Đồng bộ lịch sử** | Kiểm tra phòng chat Telegram Supergroup. | Tin nhắn hỏi trên Zalo và tin bot phản hồi tự động đều được forward đồng bộ sang Telegram topic tương ứng. | **Đã pass** |

### 📊 3. Log thực tế thành công (Console Success Logs)
Khi bạn tag bot Zalo, log của `zalo-tg` sẽ hiển thị luồng xử lý như sau:
```text
[Zalo] Nhận tin nhắn từ group "demo zalo ai" (zaloId: 8765432190)
[Zalo AI] Sending request to Hermes API: "hello bot, cho mình hỏi thời tiết hôm nay?"... for thread 8765432190
[Zalo AI] Received reply: "Xin chào! Hiện tại tôi không có kết nối internet thời gian thực để cập nhật thời tiết..."
[Zalo AI] Replied back to Zalo thread 8765432190
[Zalo→TG] Forwarded and synced reply successfully to TG topic 1042
```

---

## 23) Tổng kết Vận Hành & Khuyến Nghị

*   **Tốc độ & Tính ổn định**: Việc gọi API trực tiếp qua REST API (bỏ qua trung gian Telegram API đối với phản hồi) cho tốc độ xử lý siêu tốc (< 2-3 giây tuỳ tốc độ sinh token của LLM) và tránh được 100% giới hạn bot-to-bot của Telegram.
*   **Database state**: Các phiên chat được lưu nhất quán trong SQLite (`hermes_state.py`) của Hermes Core thông qua header `X-Hermes-Session-Id`. Bạn có thể tra cứu lịch sử hội thoại Zalo bất cứ lúc nào trong SQLite.
*   **Giám sát bộ nhớ**: Thường xuyên kiểm tra dung lượng của thư mục `./data` và lịch sử chat trong `hermes_state.py` để đảm bảo hệ thống không bị tràn bộ nhớ hoặc đầy ổ cứng.
*   **Backup**: Hãy sao lưu thư mục `data/` thường xuyên như khuyến nghị tại Mục 17 để tránh mất session đăng nhập Zalo.

---

## 24) Triển khai zalo-tg sang Máy Khác (Multi-machine Deployment & Migration Guide)

Khi bạn cần chuyển cầu nối `zalo-tg` sang máy chủ mới (ví dụ: chuyển từ môi trường thử nghiệm sang máy chủ production riêng biệt, hoặc di chuyển sang máy tính cá nhân khác), **điều quan trọng nhất là bảo toàn phiên đăng nhập (session) hiện tại**. Điều này giúp bạn không phải quét lại mã QR Code của Zalo (vốn có thể bị giới hạn hoặc đòi hỏi thiết bị chính phải ở gần).

Dưới đây là runbook chi tiết để thực hiện di chuyển và triển khai trên máy chủ mới một cách trơn tru.

### 📦 A. Các thành phần bắt buộc phải sao lưu & đóng gói
Để di chuyển trọn vẹn cầu nối mà không làm mất cấu hình và session, bạn cần sao lưu toàn bộ thư mục dự án **ngoại trừ** thư mục cài đặt thư viện (`node_modules`) và sản phẩm biên dịch (`dist`). 

Các file và thư mục load-bearing bao gồm:
1.  **Thông tin phiên đăng nhập (Session credentials)**:
    *   `credentials.json`: Lưu trữ cookie và session của Zalo Web API.
    *   `app-session.json`: Lưu trữ session của Zalo PC App API (dùng cho lookup group lớn).
2.  **Thư mục dữ liệu persistent (`data/`)**:
    *   `data/msg-map.json`: Bảng ánh xạ ID tin nhắn Zalo ↔ Telegram (để xử lý reply/edit).
    *   `data/topics.json`: Bản đồ ánh xạ Group/DM Zalo ↔ Telegram Forum Topics.
    *   `data/user-cache.json.gz`: Bộ nhớ đệm thông tin thành viên nhóm Zalo để tối ưu hóa truy vấn.
3.  **Cấu hình môi trường**:
    *   `.env`: Chứa token của Telegram Bot Z, ID nhóm Telegram, URL kết nối Hermes API.
4.  **Mã nguồn & Cấu hình Docker**:
    *   Thư mục `src/`: Toàn bộ mã nguồn TypeScript của cầu nối.
    *   `package.json` & `package-lock.json`: Định nghĩa phiên bản thư viện cần cài đặt lại.
    *   `tsconfig.json`: File cấu hình biên dịch TypeScript.
    *   `Dockerfile` & `docker-compose.yml`: Cấu hình container hóa (nếu chạy Docker).
    *   Các file script tiện ích: `run.sh`, `start-local-api.sh`, v.v.

*(Lưu ý: Không copy thư mục `node_modules` và `dist` sang máy mới vì chúng rất nặng và có thể gây lỗi không tương thích hệ điều hành/kiến trúc CPU).*

---

### 🚀 B. Quy trình khôi phục và chạy trên máy chủ mới

#### 🔹 Cách 1: Chạy trực tiếp trên Host OS (Sử dụng Node.js & PM2)

1.  **Cài đặt môi trường**: Đảm bảo máy chủ mới đã cài đặt **Node.js (>= 18)** và công cụ quản lý tiến trình **PM2**.
2.  **Giải nén gói di chuyển**: Sao chép file đóng gói `.zip` sang máy mới và giải nén vào thư mục mong muốn (ví dụ: `/opt/zalo-tg` hoặc `C:\zalo-tg`).
3.  **Cài đặt lại thư viện**:
    ```bash
    cd zalo-tg
    npm install
    ```
4.  **Kiểm tra và cập nhật file `.env`**:
    Mở file `.env` và kiểm tra xem địa chỉ Hermes API (`ZALO_AI_API_URL`) có cần thay đổi hay không. 
    *   Nếu Hermes API chạy trên cùng máy mới: Giữ nguyên `http://localhost:8642/v1`.
    *   Nếu Hermes API vẫn chạy ở máy cũ hoặc máy chủ khác: Đổi thành `http://<IP-CỦA-MÁY-HERMES>:8642/v1`.
5.  **Biên dịch dự án**:
    ```bash
    npm run build
    ```
6.  **Khởi chạy dịch vụ**:
    Sử dụng PM2 để chạy dịch vụ ở chế độ nền ổn định:
    ```bash
    pm2 start dist/index.js --name zalo-tg
    pm2 save
    ```
7.  **Giám sát**: Kiểm tra log để đảm bảo hệ thống tự nhận session cũ thành công:
    ```bash
    pm2 logs zalo-tg
    ```
    *Kết quả mong đợi*: Logs hiển thị `[Boot] Zalo listener started ✓` và tự động kết nối vào các nhóm mà không gửi lại yêu cầu `/loginweb` hay `/loginapp`.

#### 🐳 Cách 2: Chạy thông qua Docker (Khuyên dùng cho sự cô lập)

Nếu máy chủ mới đã cài Docker và Docker Compose, bạn có thể triển khai cực kỳ nhanh chóng:
1.  **Cài đặt Docker & Docker Compose** trên máy chủ mới.
2.  **Giải nén gói di chuyển** vào một thư mục trên máy mới.
3.  **Kiểm tra cấu hình `.env`** (chú ý cập nhật IP của API Server nếu cần).
4.  **Khởi chạy Container**:
    ```bash
    docker compose up -d --build
    ```
5.  **Kiểm tra log container**:
    ```bash
    docker compose logs -f
    ```

#### 🍎 Cách 3: Chạy Native trên macOS (Không dùng Docker)

Nếu máy chủ mới của bạn là một máy chạy **macOS** (Mac mini, Macbook làm server, v.v.) và bạn muốn chạy trực tiếp (Native) để tối ưu hiệu năng hoặc không muốn cài đặt Docker:

1.  **Cài đặt Xcode Command Line Tools** (cần thiết để biên dịch một số Node native modules):
    Mở Terminal trên macOS và chạy:
    ```bash
    xcode-select --install
    ```
    *(Một hộp thoại sẽ hiện lên, nhấn "Install" và chờ hệ thống tải/cài đặt hoàn tất).*

2.  **Cài đặt Homebrew** (Trình quản lý package phổ biến nhất trên macOS nếu máy bạn chưa có):
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

3.  **Cài đặt Node.js và ffmpeg** qua Homebrew:
    ```bash
    brew install node ffmpeg
    ```

4.  **Cài đặt PM2** toàn cục để quản lý background service:
    ```bash
    npm install -g pm2
    ```

5.  **Giải nén gói di chuyển và cài đặt dependencies**:
    Di chuyển file `zalo-tg-migration.zip` vào thư mục làm việc mong muốn (ví dụ thư mục Home của user: `~/zalo-tg`), sau đó chạy:
    ```bash
    mkdir -p ~/zalo-tg
    unzip zalo-tg-migration.zip -d ~/zalo-tg
    cd ~/zalo-tg
    npm install
    ```

6.  **Kiểm tra và cập nhật cấu hình `.env`**:
    Sử dụng trình soạn thảo (như `nano` hoặc VS Code) để kiểm tra file `~/zalo-tg/.env`. Cập nhật `ZALO_AI_API_URL` đến đúng địa chỉ IP của Hermes Core API nếu nó chạy ở máy khác.

7.  **Biên dịch và Khởi chạy với PM2**:
    ```bash
    npm run build
    pm2 start dist/index.js --name zalo-tg
    pm2 save
    ```

8.  **Cấu hình tự động khởi động cùng macOS** (khi reboot máy):
    ```bash
    pm2 startup
    ```
    *PM2 sẽ sinh ra một lệnh dạng `sudo env PATH=... pm2 startup launchd --hp ...` ở cuối output. Hãy copy nguyên lệnh đó, dán lại vào Terminal và nhấn Enter để hoàn tất đăng ký khởi động cùng hệ điều hành.*

9.  **Giám sát logs**:
    ```bash
    pm2 logs zalo-tg
    ```

---

### 🛡️ C. Một số lưu ý an toàn & xử lý sự cố khi di chuyển
*   **Bảo mật thông tin**: File `credentials.json` và `app-session.json` chứa khoá truy cập trực tiếp vào tài khoản Zalo của bạn. Tuyệt đối không chia sẻ file này lên mạng hoặc lưu trên repo công khai.
*   **Lỗi session bị hết hạn (Expired Session)**: Zalo thi thoảng sẽ quét và huỷ các session cũ nếu phát hiện IP đăng nhập thay đổi quá đột ngột hoặc địa lý quá xa. Nếu log báo lỗi `Session expired / Unauthorized`, bạn chỉ cần gõ lại `/loginweb@hermeszltgbot` và `/loginapp@hermeszltgbot` để quét lại QR Code một lần duy nhất trên máy mới.
*   **Đồng bộ hoá thời gian**: Đảm bảo thời gian hệ thống trên máy mới chuẩn xác (khuyến nghị bật NTP sync). Lệch múi giờ hoặc lệch giây có thể khiến các API bảo mật của Telegram và Zalo từ chối kết nối.
