# Implementation Plan - Zalo Bot Catch-up & Checkpoint Mechanism (v2)

Triển khai cơ chế khôi phục tin nhắn tự động (Catch-up) sau khi mất kết nối Zalo WebSocket, theo đặc tả RFC v8.

> **Thay đổi so với bản trước:** bổ sung bước xác minh bắt buộc (blocking) trước khi code, thêm 2 bài test còn thiếu (self-loop, corrupted checkpoint), thêm tham số clamp còn sót (cửa sổ quét lùi), tích hợp `SESSION_DEAD` với state đã có (`this.sessionDead`), thêm graceful shutdown flush.

---

## ⚠️ Scope Limitation: Group-Only Catch-up (Upstream-Bound)

Dựa trên kiểm tra thực tế, thư viện lõi `zca-js` hoàn toàn không hỗ trợ API lấy lịch sử tin nhắn cá nhân (DM - type 1). Do đó:
* Cơ chế Catch-up sẽ **chỉ áp dụng cho các Thread là Group (Nhóm)**.
* Các luồng DM (Chat cá nhân 1-1) sẽ bị bỏ qua trong quá trình Catch-up để tránh lỗi.

**Giới hạn này là do upstream (`zca-js`), không phải implementation gap.** DM catch-up sẽ không khả thi trong bất kỳ phiên bản tương lai nào trừ khi chính thư viện `zca-js` bổ sung API cho DM history. Không có kế hoạch workaround phía Hermes cho vấn đề này.

---

## User Review Required

> **IMPORTANT:** Toàn bộ logic Catch-up đã thu gọn scope so với v7 để phù hợp quy mô thực tế (vài chục thread cá nhân/gia đình). Cơ chế quét lịch sử (DM/Group History) có thể kích hoạt rate-limit của Zalo nếu tham số cấu hình quá lớn — mọi tham số catch-up **MUST** được clamp khi load. Ngoài ra, 2 rủi ro **MUST** có test riêng, không được coi là "đã xong" chỉ vì có code fallback: (1) bot có thể tự trả lời chính mình (self-loop) nếu bộ lọc sai/thiếu, (2) checkpoint hỏng có thể làm bridge crash nếu fallback không hoạt động đúng.

---

## Proposed Changes

### Component: Zalo Client Bridge — `zaloClient.js`

**PR #1 — Checkpoint Persistence Engine**
- Load checkpoint (`thread_checkpoint.json`) trong `_afterLogin()`, fallback an toàn: nếu file hỏng/parse lỗi → log warning, reset về `{ version: 1, threads: {} }`, **không throw**, catch-up bị tắt cho session hiện tại thay vì crash tiến trình.
- `_saveCheckpoint()`: ghi atomic (`.tmp` → `renameSync`).
- Debounce lưu (~10s/lần nếu có thay đổi), dùng `setTimeout(...).unref()`.
- **Graceful shutdown flush (mới):** thêm handler `process.on("SIGTERM", ...)` / `process.on("SIGINT", ...)` gọi `_saveCheckpoint()` ngay trước khi thoát, để tránh lệch tới 10s mỗi lần PM2 restart/deploy.
- Config có clamp:
  - `ZALO_MAX_TRACKED_THREADS` (10–500, default 100)
  - `ZALO_MAX_MESSAGES_PER_THREAD` (1–200, default 50)
  - **`ZALO_CATCHUP_MAX_WINDOW_MS` (mới, thiếu ở bản trước)** — clamp 5 phút (300000) đến 24 giờ (86400000), default 2 giờ (7200000). Dùng để chặn trần cửa sổ quét lùi: `Math.max(lastSeenTs, Date.now() - MAX_WINDOW)`.

**PR #2 — Connection Lifecycle & State Machine**
- State machine: `DISCONNECTED → CONNECTING → CONNECTED → (READY | CATCHUP) → READY`, cộng thêm `SESSION_DEAD`.
- **Tích hợp với state đã có (mới, sửa thiếu sót bản trước):** state machine **không** duy trì `SESSION_DEAD` như một nguồn sự thật độc lập — nó **đọc** từ `this.sessionDead` (boolean đã có sẵn từ `_declareSessionDead()`). Bất cứ khi nào `this.sessionDead === true`, state machine phải phản ánh `SESSION_DEAD` bất kể đang ở state nào khác, tránh 2 nguồn trạng thái mâu thuẫn nhau.
- Cờ `_hasConnectedOnce = false`: chỉ trigger catch-up khi `listener.on("connected")` fire **sau** lần connect đầu tiên (reconnect thật).
- Cờ `_catchingUp`: chặn catch-up chạy chồng lấp nếu socket rớt lại giữa lúc đang catch-up.
- KeepAlive: đếm fail liên tiếp, ≥3 lần và `!this._reconnecting && !this.sessionDead` → chủ động `_scheduleAutoRelogin(0, "keepalive 3x failure")`.

**PR #3 — Catch-up & Replay Engine**
- `_fetchThreadHistory(threadId, threadType, lastMsgId)`: gọi `loadmsg`(DM, sau khi Step 0 xác nhận) / `getGroupChatHistory` (Group), qua hàng đợi throttle tuần tự riêng (không tái dùng `_cachedInfo` TTL-cache).
- `_normaliseHistoryMessage(rawMsg, threadId, threadType)`:
  - **MUST** lọc bỏ bản ghi có sender trùng `ownId` (self-message filter — field chính xác theo Step 0) **trước khi** đưa vào dedup/emit.
  - Map về đúng shape mà `_normaliseMessage()` đường live trả ra.
- Sắp xếp theo `ts` tăng dần trước khi emit.
- Chỉ quét thread có trong checkpoint (không `getAllGroups`/`getAllFriends`), ưu tiên active gần nhất, áp `ZALO_CATCHUP_MAX_WINDOW_MS` + `ZALO_MAX_MESSAGES_PER_THREAD`.
- `_updateThreadLastSeen(threadId, ts)`: chỉ cập nhật nếu `ts` mới hơn giá trị hiện có (`Math.max`), không ghi đè vô điều kiện.

### Component: `server.js`
- Phối hợp emit với SSE ring buffer: nếu số lượng tin catch-up trong 1 đợt gần chạm giới hạn 200-item, giãn tốc độ emit (throttle nhỏ giữa các message) để không tự evict tin live.
- Mở rộng `/health`: thêm `checkpoint` (loaded, trackedThreads), `catchup` (running, lastCatchupAt, recoveredCount, historyFetchErrors), `connection` (disconnectCount, lastDisconnectDurationMs, keepAliveFailures) — không rò rỉ path đĩa hay nội dung tin nhắn.

---

## Verification Plan

### Automated Tests
- `scratch/test_checkpoint.js`: giả lập ghi đĩa atomic, debounce, và các transition của state machine (bao gồm việc `SESSION_DEAD` phản ánh đúng khi `this.sessionDead = true` được set thủ công).
- Chạy bridge với cờ log debug để quan sát chuyển trạng thái và replay tin nhắn khi reconnect.

### Manual Verification

1. **Self-loop test (bổ sung — bắt buộc, ưu tiên cao nhất):**
   Khởi động bridge, để bot **tự gửi** 1 tin nhắn test (qua chính API gửi tin của Hermes) tới 1 thread. Ngắt mạng bridge ngay sau đó trong ~15s, khôi phục mạng, trigger catch-up. Kiểm tra log/`Hermes Agent` **KHÔNG** nhận lại tin nhắn đó như một message mới — đây là bài test duy nhất phát hiện được lỗi bộ lọc self-message nếu có (test bằng tin từ tài khoản khác sẽ không phát hiện ra lỗi này).

2. **Corrupted checkpoint test (bổ sung — bắt buộc):**
   Dừng bridge, ghi đè `thread_checkpoint.json` bằng nội dung JSON không hợp lệ (hoặc file rỗng). Khởi động lại bridge, xác nhận: (a) tiến trình **không crash**, (b) log có warning về checkpoint hỏng, (c) `/health` trả về `checkpoint.loaded = false`, (d) bridge vẫn nhận tin nhắn live bình thường (chỉ mất khả năng catch-up cho session này, không mất toàn bộ chức năng).

3. **Reconnect catch-up thực tế (Group-only — DM không được hỗ trợ bởi zca-js):**
   Gửi 1 tin nhắn Group để tạo checkpoint ban đầu. Ngắt mạng tạm thời (hoặc kill socket), gửi tin nhắn Group từ tài khoản/thiết bị khác trong lúc mất kết nối. Khôi phục mạng, xác nhận tin nhắn Group bị nhỡ được catch-up, emit đúng thứ tự thời gian lên SSE stream, và xuất hiện đúng 1 lần (không trùng lặp) ở Hermes Agent. *(DM catch-up bỏ qua do upstream không hỗ trợ — đây là giới hạn cứng, không phải thiếu implementation.)*

4. **Graceful shutdown flush test (bổ sung):**
   Gửi vài tin nhắn (chưa tới mốc debounce 10s), gửi `SIGTERM` cho tiến trình bridge ngay sau đó, xác nhận `thread_checkpoint.json` đã được flush với timestamp mới nhất trước khi tiến trình thoát hẳn.

5. **Config clamping test:**
   Set `ZALO_CATCHUP_MAX_WINDOW_MS=999999999999` (vượt trần) và `ZALO_MAX_MESSAGES_PER_THREAD=0` (dưới sàn), khởi động bridge, xác nhận cả 2 tự động clamp về giá trị hợp lệ gần nhất, không dùng giá trị vượt ngưỡng.
