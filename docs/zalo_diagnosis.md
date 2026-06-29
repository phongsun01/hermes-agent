# 🔍 Chẩn đoán Zalo Plugin — Hermes Gateway

> Thời điểm cập nhật: 2026-06-16 09:45 ICT

---

## 📊 Tóm tắt trạng thái

| Thành phần | Trạng thái | Chi tiết |
|---|---|---|
| Plugin Python (`~/.hermes/plugins/zalo/`) | ✅ Cài đặt | `adapter.py` có retry (5 lần) + `max_message_length=4000` + login retry 60s |
| Bridge Node.js (`server.js` port 8787) | ✅ **v1.0.8** | KeepAlive 60s, auto-relogin 5 attempts với 30s timeout, cookieOnly relogin |
| Bridge resilience | ✅ **uncaughtException + unhandledRejection handlers** | Không crash khi async error |
| Watchdog (`bridge-watchdog.js`) | ✅ **Forever restart** | Không max retries, restart 3s, health poll 10s + auto /relogin |
| Credentials (`~/.hermes-zalo/credentials.json`) | ✅ Có | Auto-refreshed sau mỗi keepAlive |
| QR login | ✅ Đã quét | Cookie login ổn định |
| Config `config.yaml` | ✅ Đầy đủ | `platforms.zalo.enabled: true` + `plugins.enabled: [zalo-platform]` (cả 2 cần) |
| `.env` | ✅ Đúng | `ZALO_PLUGIN_URL=http://host.docker.internal:8787` |
| DM reply | ✅ OK | Text thuần, strip markdown, chunk 4000 ký tự |
| Group reply (@mention) | ✅ OK | Chỉ reply khi được mention (`ZALO_GROUP_MODE=mention`) |
| Markdown handling | ✅ Strip → text thuần | Không còn lỗi gửi JSON card |
| Recovery code 1006 | ✅ **zca-js WS retry** (Fix 22) | Inject 1006 vào retry list → reconnect nội bộ ~2s, không cần full relogin |
| Recovery code 1000 | ✅ **zca-js tự retry WS** | Inject code 1000 vào `close_and_retry_codes` + `retryCount`, zca-js reconnect nội bộ 0 API call, downtime ~5s |
| SSE single-client 409 gate | ✅ **HTTP 409 rejection** (Fix 22) | Bridge trả 409 khi đã có SSE client; Docker phantom bị chặn ổn định |
| SSE reconnect adapter | ✅ **409 sleep 10s** | Adapter code mới: nhận 409 → sleep 10s im lặng thay vì reconnect storm |
| SSE reconnect | ✅ **Giảm downtime + cleanup** | Backoff max 10s + health poll 2s + `TCPConnector(force_close=True)` + `/disconnect` trước retry |
| Gateway reconnect match | ✅ **Login retry polling** | Adapter poll `/health` 60s khi "not_logged_in" trước khi báo fail |
| Bridge-watchdog | ✅ **Forever** | Không max retries, restart 3s, health poll 10s + auto /relogin |
| Message dedup | ✅ **4 layers** | server.js (isSelf + messageId ring + **single-client SSE**) + adapter.py (messageId ring) |
| `sseClients` | ✅ **Single-client mode → 409 gate** | 409 reject thay vì evict; Docker phantom bị từ chối tại HTTP level |
| Windows Firewall | ✅ **Rule port 8787** (Fix 23) | Inbound rule cho Docker → host bridge traffic |

---

## 🔧 Các sửa đổi đã áp dụng (2026-06-16 v4 - Docker Bridge Stability)

### 22. Single-client SSE 409 gate + adapter 409 handler (2026-06-16)

**Vấn đề:** Docker Desktop proxy (Windows) tạo 2 TCP connections đồng thời khi container gọi `GET /events`. Bridge thêm cả 2 vào `sseClients` → mỗi event được push 2 lần → bot reply 2 lần. Giải pháp evict (fix 21) gây "Death Spiral": evict → adapter disconnect → backoff ngắn → reconnect → evict lại.

**Root cause chính xác:**
- Docker Desktop NAT proxy tạo phantom connection ngay sau real connection
- Eviction kill real client, adapter reconnect → vòng lặp vô hạn

**Fix A — `server.js`:** Thay eviction bằng **HTTP 409 Conflict rejection**. Khi đã có `sseClients=1`, bridge từ chối SSE request mới bằng `res.status(409)`:
```javascript
app.get("/events", (req, res) => {
  if (sseClients.size >= 1) {
    console.log("[bridge] SSE rejected (already have 1 client) — returning 409");
    res.status(409).json({ error: "already_connected" });
    return;
  }
  // ... setup SSE
});
```

**Fix B — `adapter.py`:** Nhận 409 → sleep 10s im lặng thay vì raise exception:
```python
if resp.status == 409:
    logger.debug("Zalo: SSE 409 (bridge slot busy); waiting 10s for phantom to clear")
    await asyncio.sleep(10.0)
    continue  # retry loop
```

**Fix C — `bridge-watchdog.js`:** Pass `ZALO_PLUGIN_HOST=0.0.0.0` vào env của bridge child:
```javascript
const child = spawn("node", ["server.js"], {
  env: { ...process.env, ZALO_PLUGIN_HOST: "0.0.0.0" },
  ...
});
```

**Kết quả:** `sseClients` ổn định = 1, không còn double reply, bridge không bị eviction storm.

### 23. Windows Firewall rule port 8787 (2026-06-16)

**Vấn đề:** Bridge listen `0.0.0.0:8787` nhưng Windows Firewall block inbound traffic từ Docker network (`192.168.65.254`) → container không reach được `host.docker.internal:8787`.

**Fix:** Thêm Windows Firewall inbound rule:
```powershell
# Chạy với quyền Admin:
New-NetFirewallRule -DisplayName "Zalo Bridge 8787" -Direction Inbound -Protocol TCP -LocalPort 8787 -Action Allow -Profile Any
```

**Lưu ý:** Rule này persist sau reboot. Kiểm tra: `Get-NetFirewallRule -DisplayName "Zalo Bridge 8787"`

### 24. zca-js code 1006 WS retry injection (2026-06-16)

**Vấn đề:** Zalo WebSocket đóng với `code=1006` (abnormal closure) mỗi ~3 phút. zca-js không có code 1006 trong `close_and_retry_codes` → rơi vào `closed` event → `_scheduleAutoRelogin()` với 5s delay → full cookie relogin (~8-10s) → **blackout window 7-12s** mỗi 3 phút. Tin nhắn gửi trong window này bị mất hoàn toàn.

**Root cause:** `zca-js/dist/apis/listen.js` `canRetry(1006)` → `false` (1006 không trong retry list từ server settings).

**Fix (`zaloClient.js` `_afterLogin()`):** Inject code 1006 vào retry system cùng code 1000:
```javascript
if (!codes.includes(1006)) codes.push(1006);
if (!listener.retryCount["1006"]) {
  listener.retryCount["1006"] = {
    count: 0, max: 999, times: [2000],  // retry sau 2s, tối đa 999 lần
  };
}
```

**Kết quả:**
| Metric | Before (full relogin) | After (WS retry) |
|--------|----------------------|------------------|
| Downtime per code 1006 | 7-12s | ~2s |
| API call | 1 (cookie relogin) | 0 |
| Message loss window | 7-12s/3min | ~2s/3min |

**Cần restart bridge** để load fix: Ctrl+C trong terminal watchdog → `node bridge-watchdog.js`

### 25. Slash Command Skill execution environment (WSL/Docker) (2026-06-25)

**Vấn đề:** Khi tạo một AI Skill (như `/cc`) bằng file `SKILL.md` để user giao tiếp qua bot Zalo, nếu hướng dẫn Agent chạy các công cụ bằng Windows PowerShell (vd: `powershell -Command` với đường dẫn `C:\Users\Desktop\...`), Agent Zalo sẽ báo lỗi.

**Root cause:**
- Gateway và Agent phục vụ Zalo Bot đang chạy trực tiếp bên trong container Docker/WSL2 (Linux) - cụ thể là container `hermes`.
- Các Agent này không có tool `run_command` tương tác với PowerShell trên host Windows, mà dùng terminal Linux cục bộ.
- File system được mount vào `/opt/data` hoặc truy cập qua home directory `~/.hermes`, không phải ổ `C:\`.

**Giải pháp (Lesson Learned cho thiết kế Skill):**
- Khi viết file `SKILL.md` phục vụ qua Zalo (Gateway), phải viết hướng dẫn thực thi (Action) tương thích với môi trường **Linux/Docker**.
- Dùng `python ~/.hermes/scripts/...` thay vì `C:\Users\...`
- Bỏ các wrapper lệnh như `docker exec hermes ...` vì bản thân Agent Zalo đã nằm TRONG container `hermes` rồi.
- *Lưu ý: Nếu thay đổi, thêm bớt Skill mới (`SKILL.md`), cần restart Gateway container (`docker restart hermes`) để Gateway load lại danh sách Slash Command Registry.*

---

## 🔧 Các sửa đổi đã áp dụng (2026-06-12 v3 - Stability Round)

### 13. Server crash resilience — uncaughtException / unhandledRejection handlers

**Vấn đề:** Bridge Node.js crash không báo với `TransferEncodingError` trên gateway (HTTP response bị cắt giữa chừng). Nguyên nhân: unhandled promise rejection từ zca-js listener hoặc Express route handler không có try/catch.

**Giải pháp (`server.js`):**
```javascript
process.on("uncaughtException", (err) => {
  console.error("[bridge] UNCAUGHT EXCEPTION:", err);
});
process.on("unhandledRejection", (reason) => {
  console.error("[bridge] UNHANDLED REJECTION:", reason);
});
```

→ Bridge không còn crash khi có async error. Watchdog restart không còn cần thiết cho các lỗi này.

### 14. Auto-relogin timeout — 30s giới hạn

**Vấn đề:** `zalo.login(saved)` trong `relogin()` có thể HANG vô thời hạn nếu saved credentials stale hoặc server không response → `_reconnecting` bị lock vĩnh viễn → không có relogin attempt nào tiếp theo → bridge stuck ở `loggedIn=false`.

**Giải pháp (`zaloClient.js`):**
```javascript
async relogin({ forceQR = true, cookieOnly = false } = {}) {
    this._stopReconnect();
    this._stopKeepAlive();
    // ... cleanup ...
    const TIMEOUT_MS = 30_000;
    const result = await Promise.race([
      this.login({ forceQR, cookieOnly }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("login timed out")), TIMEOUT_MS),
      ),
    ]);
    return result;
}
```

→ Mỗi relogin attempt timeout sau 30s, không block các attempt tiếp theo.

### 15. SSE backoff với health polling

**Vấn đề:** Khi SSE disconnect, adapter dùng exponential backoff từ 1s lên 30s => nếu bridge restart nhanh (3-5s), adapter vẫn chờ tới 30s mới reconnect.

**Giải pháp (`adapter.py`):**
1. **Max backoff giảm** từ 30s → 10s
2. **Health poll trong backoff:** mỗi 2s poll `/health` → nếu bridge online, reconnect ngay

```python
async def _wait_with_health_poll(self, max_wait: float) -> None:
    slept = 0.0
    while slept < max_wait:
        remaining = max_wait - slept
        chunk = min(2.0, remaining)
        await asyncio.sleep(chunk)
        slept += chunk
        try:
            async with self._session.get(
                f"{self.bridge_url}/health", timeout=aiohttp.ClientTimeout(total=3),
                ...
            ) as resp:
                if resp.status == 200:
                    return  # bridge is up, reconnect now
        except Exception:
            pass  # bridge still down
```

### 16. Adapter login retry — Poll tới 60s khi bridge "not logged in"

**Vấn đề:** Gateway reconnect watcher exponential backoff 30s-300s. Bridge có thể auto-relogin thành công trong ~10-75s, nhưng gateway bỏ lỡ vì đang backoff.

**Giải pháp (`adapter.py` start()):** Khi `/health` trả về `loggedIn=false`, adapter KHÔNG fail ngay. Thay vào đó poll `/health` mỗi 5s tới 60s:

```python
MAX_LOGIN_RETRIES = 12  # ~60s total with 5s polling
login_retry = 0
while login_retry < MAX_LOGIN_RETRIES:
    data = await self._session.get(f"{self.bridge_url}/health").json()
    if data.get("loggedIn"):
        break  # bridge is ready
    login_retry += 1
    if login_retry < MAX_LOGIN_RETRIES:
        await asyncio.sleep(5)
    else:
        # still not logged in after 60s — fail with "not_logged_in"
```

→ Gateway reconnect watcher có tỷ lệ thành công cao hơn nhiều vì chịu đựng được transient logout trong ~60s.

### 17. Watchdog forever — Không giới hạn retry

**Vấn đề:** Watchdog cũ có `MAX_RETRIES = 50` → bridge không thể restart sau 50 lần crash. Bridge có thể crash nhiều lần nếu credentials corrupt hoặc zca-js lỗi.

**Giải pháp (`bridge-watchdog.js`):** Bỏ max retries, restart forever với 3s delay:
```javascript
child.on("exit", (code) => {
    console.log(`[watchdog] bridge exited with code ${code}`);
    console.log(`[watchdog] restarting in ${RETRY_DELAY_MS / 1000}s...`);
    setTimeout(startBridge, RETRY_DELAY_MS);
});
```

### 18. Double reply root cause v2 — Zombie SSE connections + Docker proxy (2026-06-11)

**Vấn đề:** Bot Zalo trả lời 2 lần cho mỗi tin nhắn. Bridge health endpoint trả về `sseClients: 2`
dù chỉ có 1 adapter instance đang chạy.

**Root cause:** aiohttp `ClientSession()` dùng connection pool mặc định với keep-alive. Khi SSE
stream bị drop (do zca-js session death code 1006), TCP connection vẫn được giữ alive trong pool.
Docker Desktop proxy (trên Windows) không detect được RST từ container → bridge vẫn xem client cũ là active.
Khi adapter reconnect, bridge có 2 SSE clients → mỗi event được gửi tới cả 2 clients → mỗi client
có `_dedup_set` riêng (không shared) → không dedup được → bot trả lời 2 lần.

**Cơ chế zombie:**
```
Container adapter      Docker proxy (10632)      Bridge (8787)
     |                        |                        |
     |--- SSE connect ------->|---- SSE connect ------>| sseClients = {A}
     |                        |                        |
     |--- session death ----->|---- code 1006 -------->|
     |                        |                        |
     |                        | (proxy giữ TCP open)   | sseClients = {A} (zombie)
     |                        |                        |
     |--- reconnect --------->|---- SSE connect ------>| sseClients = {A, B}
     |                        |                        | ← DOUBLE EVENT!
```

**Các vấn đề liên quan phát hiện cùng lúc:**

1. **`setup_logging()` double-handler bug** (`hermes_logging.py`): Handlers được thêm TRƯỚC guard
   `if _logging_initialized` → mỗi lần gọi `setup_logging()` thêm duplicate handlers → mỗi log line
   ghi 2 lần với timestamp lệch nhau 7h (UTC vs ICT).

2. **Log file timestamp lệch 7h:** UTC handler + ICT handler cùng ghi vào 1 file → mỗi dòng xuất hiện
   2 lần (vd: `04:22:08` và `11:22:08`).

**Giải pháp:**

**Fix 1: `hermes_logging.py` — Di chuyển guard trước handler creation**
```python
root = logging.getLogger()

if _logging_initialized and not force:
    return log_dir

# Handler creation AFTER the guard
_add_rotating_handler(root, log_dir / "agent.log", ...)
```

**Fix 2: Zalo adapter `adapter.py` — Force-close TCP connection**
```python
self._session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(force_close=True),
)
```
Khi SSE stream kết thúc, TCP connection được đóng ngay (RST) thay vì trả về pool → Docker proxy
detect được disconnect sớm hơn.

**Fix 3: Bridge `server.js` — `/disconnect` endpoint**
```javascript
app.post("/disconnect", (req, res) => {
  if (!checkAuth(req, res)) return;
  for (const client of sseClients) {
    try { client.end(); } catch { /* ignore */ }
  }
  sseClients.clear();
  res.json({ ok: true, cleared: true });
});
```
Cho phép adapter cleanup zombie clients trước khi reconnect.

**Fix 4: Adapter gọi `/disconnect` trước retry**
```python
except Exception as e:
    # Cleanup zombie clients before reconnect
    try:
        await self._session.post(
            f"{self.bridge_url}/disconnect",
            headers=self._headers(),
            timeout=aiohttp.ClientTimeout(total=3),
        )
    except Exception:
        pass
    # Then backoff + retry...
    await self._wait_with_health_poll(backoff)
```

**Kết quả:** Sau container restart, `sseClients` xuống còn 1. Khi reconnect, adapter cleanup
zombie clients trước → không tích lũy duplicate SSE clients.

### 19. setup_logging double-handler (2026-06-11)

**Vấn đề:** Mỗi log line trong `gateway.log` xuất hiện 2 lần — một với timestamp UTC, một với ICT.
Gây khó đọc log.

**Root cause:** `setup_logging()` trong `hermes_logging.py` thêm handlers trước guard check:

```python
# OLD — handlers added BEFORE guard
root = logging.getLogger()
_add_rotating_handler(root, ...)  # ← handler added unconditionally
if _logging_initialized and not force:
    return log_dir
_logging_initialized = True
```

Khi gọi lần 2 (có `force=True`), handlers được thêm lại → mỗi handler có format khác nhau (UTC vs ICT) →
mỗi LogRecord được ghi 2 lần.

**Fix:** Đảo thứ tự — guard trước, handlers sau:

```python
# FIXED — guard first, handlers after
root = logging.getLogger()
if _logging_initialized and not force:
    return log_dir  # ← handler creation skipped on subsequent calls
_add_rotating_handler(root, ...)
_logging_initialized = True
```

**Ghi chú:** Fix này cần áp dụng vào image (hoặc `docker exec` patch + `docker restart hermes`) vì
`hermes_logging.py` nằm trong Docker image, không phải volume mount.

### 20. Code 1000 retry — zca-js tự reconnect WS, 0 API call (2026-06-12)

**Vấn đề:** Zalo server gửi websocket `code 1000` (ManualClosure) ~6s sau mỗi kết nối.
zca-js `Listener.canRetry()` kiểm tra `close_and_retry_codes.includes(1000)` → false (vì code 1000
không nằm trong retry list từ server settings) → rơi vào `closed` event → full API relogin mỗi lần.

**Hậu quả:** cycle `connected ~6s → relogin ~8s → login ~2s → connected ~6s → relogin...`
Downtime ~8s mỗi 14s (57%). Mỗi lần relogin tốn API call.

**Root cause trong zca-js** (`node_modules/zca-js/dist/apis/listen.js`):
```javascript
// ws.onclose handler (line 123-139):
ws.onclose = (event) => {
    this.reset();
    this.emit("disconnected", event.code, event.reason);
    const retry = retryOnClose && this.canRetry(event.code);  // ← canRetry(1000)=false
    if (retry && retryOnClose) {
        // ... retry logic (không bao giờ chạy cho code 1000)
    } else {
        this.onClosedCallback(event.code, event.reason);  // ← luôn chạy
        this.emit("closed", event.code, event.reason);
    }
};

canRetry(code) {
    if (!this.ctx.settings.features.socket.close_and_retry_codes.includes(code))
        return false;  // ← code 1000 không trong danh sách → false
    ...
}
```

**Giải pháp (`zaloClient.js` `_afterLogin()`):** Inject code 1000 vào retry system của zca-js
trước khi gọi `listener.start()`:

```javascript
const listener = this.api.listener;
if (listener && listener.ctx?.settings?.features?.socket) {
  const codes = listener.ctx.settings.features.socket.close_and_retry_codes;
  if (!codes.includes(1000)) codes.push(1000);     // cho phép retry code 1000
  if (!listener.retryCount["1000"]) {
    listener.retryCount["1000"] = {
      count: 0, max: 999, times: [5000],           // retry mỗi 5s, tối đa 999 lần
    };
  }
}
this.api.listener.start({ retryOnClose: true });
```

**Cơ chế hoạt động:** Khi code 1000 đến, zca-js `canRetry(1000)` trả về `5000` (delay). Sau 5s,
zca-js gọi `this.start({ retryOnClose: true })` → tạo WebSocket mới trên cùng listener instance
→ emit `connected` → bridge thấy `status: { connected: true }`. **0 API call, không cần relogin.**

**Kết quả:**
| Metric | Before | After |
|--------|--------|-------|
| Downtime mỗi cycle | ~8s (full relogin) | ~5s (WS reconnect) |
| API call mỗi cycle | 1 (relogin→api.login) | 0 |
| Connected window | ~6s | ~6s |
| log pattern | `disconnected → CLOSED → auto-relogin 1/5 → logged in → connected` | `disconnected → connected` |

### 21. Single-client SSE mode — Chống zombie SSH clients từ Docker Desktop (2026-06-12)

**Vấn đề:** Bridge health endpoint trả về `sseClients: 2` dù adapter chỉ có 1 SSE connection.
Docker Desktop proxy trên Windows tạo TCP connection phụ → bridge thêm 2 Express `res` objects
vào `sseClients` → mỗi event được `res.write()` 2 lần. Kết hợp với bridge `pushEvent` dedup
vẫn không đủ vì adapter nhận event qua 2 đường riêng biệt.

**Biểu hiện:** Bot Zalo trả lời 2 lần cho 1 tin nhắn. Gateway log có 2 `send()` calls với
cùng `reply_to` nhưng nội dung khác nhau (AI generate 2 response).

**Giải pháp (`server.js` `/events` handler):** Single-client mode — evict tất cả client cũ
khi có client mới connect:

```javascript
app.get("/events", (req, res) => {
  // Single-client mode: evict any existing SSE client.
  for (const old of sseClients) {
    try { old.end(); } catch { /* ignore */ }
  }
  sseClients.clear();
  sseClients.add(res);
  console.log("[bridge] SSE client connected, total:", sseClients.size);
  // ... heartbeat, cleanup ...
});
```

**Tại sao an toàn:** Bridge đã có `ring` buffer (200 events) hỗ trợ SSE `Last-Event-ID`.
Khi adapter bị evict, nó reconnect với `Last-Event-ID` → bridge replay events đã miss.

**Kết quả:** `sseClients` luôn = 1. Docker Desktop zombie không tích lũy. Nếu zombie
thay thế client thật, adapter reconnect trong <1s (backoff 1s) → không mất event.

## 🔧 Các sửa đổi đã áp dụng (v1 - 2026-06-10 v1)

### 0. Cập nhật v1.0.8 upstream (2026-06-10)

Đã reset repo về tag `v1.0.8` từ `github.com/cuongdev/hermes-zalo-plugin`.

**Thay đổi từ upstream:**
- **KeepAlive heartbeat:** `_startKeepAlive()` gọi `api.keepAlive()` mỗi 60s (constant `KEEPALIVE_INTERVAL_MS`)
- **Auto-relogin có backoff:** `_scheduleAutoRelogin()` với linear backoff (5s, 10s, 15s... tối đa 60s), tối đa 5 lần thử
- **`cookieOnly` param:** Cho phép relogin mà không fallback xuống QR (không block)
- **`_declareSessionDead()`:** Method chuẩn hóa cho fatal session death (code 3000/3003)
- **`_stopReconnect()`:** Cleanup timer reconnect khi shutdown/relogin
- **Constructor fields mới:** `_keepAliveTimer`, `_autoReloginTimer`, `_autoReloginAttempts`, `_reconnecting`

**Custom patches giữ lại (re-applied sau merge):**
- Markdown strip trong `sendText()` (xóa `**`, `*`, `__`, `~~`, `` ` ``, headers, lists, links)
- Cookie refresh sau mỗi lần `api.keepAlive()` (lưu cookie mới vào `credentials.json`)
- `loggedIn = true` restore trong listener `connected` event

### 1. KeepAlive Heartbeat — Chống session death (code=1006)

**Vấn đề:** Session Zalo liên tục chết sau ~3-5 phút với `code=1006` (abnormal close). Bridge vẫn `loggedIn=True` nhưng listener websocket đóng, không nhận tin nhắn.

**Giải pháp:** Học từ [zaloclaw](https://github.com/monas-team/zaloclaw) — thêm cơ chế `keepAlive` định kỳ:

**File:** `D:\Antigravity\hermes-zalo-plugin\zaloClient.js`

```javascript
// Trong _afterLogin():
this._startKeepAlive();

/** Periodic keepAlive + cookie refresh to prevent session death. */
_startKeepAlive() {
  if (this._keepAliveTimer) {
    clearInterval(this._keepAliveTimer);
    this._keepAliveTimer = null;
  }
  const keepaliveDuration = this.api.getContext?.()?.settings?.keepalive?.keepalive_duration;
  const intervalSec = (keepaliveDuration && keepaliveDuration > 0) ? keepaliveDuration : 60;
  const intervalMs = intervalSec * 1000;
  console.log(`[zalo] keepAlive: ${intervalSec}s interval`);

  this._keepAliveTimer = setInterval(async () => {
    if (!this.loggedIn || !this.api) return;
    try {
      await this.api.keepAlive();
      // Refresh cookies after keepAlive — server may have issued new ones.
      const jar = this.api.getCookie?.();
      if (jar) {
        const serialized = jar.serializeSync?.()?.cookies ?? jar.toJSON?.()?.cookies;
        if (serialized) {
          const creds = this._loadCredentials();
          if (creds) {
            creds.cookie = serialized;
            this._saveCredentials(creds);
            console.log("[zalo] credentials refreshed after keepAlive");
          }
        }
      }
    } catch (e) {
      console.error("[zalo] keepAlive failed:", e && e.message ? e.message : e);
    }
  }, intervalMs);

  if (this._keepAliveTimer.unref) this._keepAliveTimer.unref();
}
```

**Cơ chế hoạt động:**
1. Gọi `api.keepAlive()` mỗi 60-120s (Zalo server quy định)
2. Sau mỗi lần keepAlive, lấy cookie mới từ `api.getCookie()` và lưu vào `credentials.json`
3. Cookie được refresh liên tục → session không bị hết hạn

### 2. Listener `closed` — Auto-relogin khi code 1006

**Vấn đề:** Khi listener đóng với `code=1006`, `retryOnClose` của zca-js không reconnect được. Bridge treo ở trạng thái `loggedIn=false, sessionDead=true` nhưng không tự recovery.

**Giải pháp:** Khai báo session dead ngay khi code 1006 → trigger auto-relogin từ `server.js`:

```javascript
listener.on("closed", (code, reason) => {
  console.log("[zalo] listener CLOSED", code, reason);

  if (code === 1006) {
    console.log("[zalo] abnormal close (1006) — auto-relogin triggered");
    this.loggedIn = false;
    this.sessionDead = true;
    this.sessionDeadReason = `code=${code} reason=${reason || ""}`.trim();
    this.emit("status", { connected: false, dead: true, code, reason });
    this.emit("session_dead", {
      code, reason: reason || "",
      message: "Zalo session closed (cookie expired or network). Auto-relogin triggered.",
    });
    return;
  }

  this._declareSessionDead(code, reason);
});
```

**Trong `server.js`** (đã có từ trước):
```javascript
client.on("session_dead", (d) => {
  pushEvent("session_dead", d);
  // Auto-relogin on session death (code 1006 = abnormal close)
  console.log("[bridge] session dead — auto-relogin triggered");
  client.relogin({ forceQR: false })
    .then((r) => console.log("[bridge] auto-relogin complete via", r.method))
    .catch((e) => console.error("[bridge] auto-relogin failed:", e && e.message ? e.message : e));
});
```

### 3. Listener `connected` — Restore `loggedIn` khi reconnect

```javascript
listener.on("connected", () => {
  console.log("[zalo] listener connected");
  this.sessionDead = false;
  this.loggedIn = true; // Restore nếu bị set false trong transient drop
  this.emit("status", { connected: true });
});
```

### 4. Cleanup — Stop keepAlive timer khi shutdown/relogin

```javascript
// Trong shutdown():
if (this._keepAliveTimer) {
  clearInterval(this._keepAliveTimer);
  this._keepAliveTimer = null;
}

// Trong relogin():
if (this._keepAliveTimer) {
  clearInterval(this._keepAliveTimer);
  this._keepAliveTimer = null;
}
```

### 5. Constructor — Thêm field `_keepAliveTimer`

```javascript
this._keepAliveTimer = null; // setInterval for keepAlive heartbeat
```

### 6. Silent relogin — Không emit `session_dead` event cho code 1006

**Vấn đề:** Khi listener đóng code 1006, emit `session_dead` → gateway thấy `session_dead` SSE event → báo lỗi fatal.

**Giải pháp:** Auto-relogin trực tiếp trong listener handler, không emit `session_dead` — gateway chỉ thấy SSE disconnect nhẹ.

```javascript
listener.on("closed", (code, reason) => {
  console.log("[zalo] listener CLOSED", code, reason);
  if (code === 1006 || code === 1000) {
    // Silent auto-relogin — don't emit session_dead to avoid SSE error to gateway
    this.loggedIn = false;
    this.relogin({ forceQR: false })
      .then(r => console.log("[zalo] silent relogin completed via", r.method))
      .catch(e => console.error("[zalo] silent relogin failed:", e?.message));
    return;
  }
  this._declareSessionDead(code, reason);
});
```

### 7. Markdown stripping — Gửi text thuần

**Vấn đề:** Bridge cố gắng parse markdown → gửi JSON card object thay vì text → Zalo hiển thị lỗi.

**Giải pháp:** Strip tất cả markdown syntax trước khi gửi:

```javascript
// Trong sendText():
sendText(uid, text) {
  const plain = text
    .replace(/[*_~`]+/g, '')         // **bold**, *italic*, __underline__, ~~strikethrough~~, `code`
    .replace(/#{1,6}\s+/g, '')        // headers: # ## ###
    .replace(/^[-*+]\s+/gm, '')       // unordered lists
    .replace(/^\d+\.\s+/gm, '')       // ordered lists
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links [text](url)
    .replace(/>\s+/g, '')             // blockquotes
    .replace(/\n{3,}/g, '\n\n')       // limit blank lines
    .trim();
  return this.api.sendText(uid, plain);
}
```

### 8. Retry logic trong adapter.py

**Vấn đề:** Container gateway gọi POST tới bridge mỗi lần gửi tin nhắn. Nếu bridge đang relogin (chết tạm thời), request fail → mất tin nhắn.

**Giải pháp:** Retry `_post()` tới 5 lần với exponential backoff + xử lý cả connection error và bridge error:

```python
def _post(self, endpoint, data):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            r = requests.post(f"{self.bridge_url}{endpoint}", json=data, timeout=10)
            result = r.json()
            if result.get("error"):
                logger.warning(f"[bridge] error from bridge: {result['error']}")
                if attempt < max_retries - 1:
                    time.sleep(min(2 ** attempt, 10))
                    continue
                return None
            return result
        except Exception as e:
            logger.warning(f"[bridge] _post attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(min(2 ** attempt, 10))
                continue
            return None
```

### 9. Giới hạn tin nhắn — `max_message_length=2000`

**Vấn đề:** Tin nhắn dài >4000 ký tự (mặc định) bị Zalo từ chối với lỗi "Nội dung quá dài".

**Giải pháp:** Giảm xuống 2000 ký tự + tự động chunk:

```python
# Trong adapter.py
max_message_length = 2000

# Tự động chunk nếu text > 2000 ký tự
if len(text) > self.max_message_length:
    for chunk in [text[i:i+self.max_message_length] for i in range(0, len(text), self.max_message_length)]:
        self._post("/send", {"uid": uid, "text": chunk, "otp": otp})
        time.sleep(0.5)
else:
    self._post("/send", {"uid": uid, "text": text, "otp": otp})
```

### 10. Cleanup timers trong `shutdown()` / `relogin()`

### 11. Message dedup — Chống trả lời 2 lần (2026-06-10)

**Vấn đề:** Bot Zalo trả lời 2 lần cho mỗi tin nhắn. Nguyên nhân: zca-js hardcoded `selfListen=true` (để tracking cliMsgId cho undo), kết hợp với auto-relogin v1.0.8 có thể tạo overlap ngắn giữa listener cũ và mới → cùng message được deliver 2 lần qua SSE.

**Giải pháp:** Hai lớp dedup:

**Layer 1: `server.js` — Filter trước khi push SSE**
```javascript
function pushEvent(type, payload) {
  // Never echo own messages back to the gateway adapter.
  if (type === "message" && payload.isSelf) return;
  // Dedup by messageId (catches rare duplicate pushes from listener overlap).
  if (type === "message" && payload.messageId) {
    if (msgDedupSet.has(payload.messageId)) {
      console.log("[bridge] dedup: skipping duplicate message", payload.messageId);
      return;
    }
    msgDedupSet.add(payload.messageId);
    msgDedupRing.push(payload.messageId);
    if (msgDedupRing.length > DEDUP_SIZE) {
      const old = msgDedupRing.shift();
      msgDedupSet.delete(old);
    }
  }
  // ... push to SSE clients
}
```

**Layer 2: `adapter.py` — Dedup ring trong Python adapter**
```python
# Trong __init__:
self._dedup_max = 200
self._dedup_set = set()
self._dedup_ring = []

# Trong _on_inbound_message:
msg_id = str(m.get("messageId") or "")
if msg_id:
    if msg_id in self._dedup_set:
        logger.debug("Zalo: dedup dropped duplicate message %s", msg_id)
        return
    self._dedup_set.add(msg_id)
    self._dedup_ring.append(msg_id)
    if len(self._dedup_ring) > self._dedup_max:
        old = self._dedup_ring.pop(0)
        self._dedup_set.discard(old)
```

```javascript
// Trong shutdown() và relogin():
if (this._keepAliveTimer) {
  clearInterval(this._keepAliveTimer);
  this._keepAliveTimer = null;
}
```

### 12. Root cause double reply v1 — Plugin loading vs Config loading (2026-06-10, outdated)

**⚠️ Phân tích này KHÔNG phải nguyên nhân thực sự.** Xem tiếp section 18 cho kết luận chính xác.

Config từng có cả `gateway.platforms.zalo.enabled: true` và `plugins.enabled: [zalo-platform]`.
Tôi đã xoá `plugins.enabled` vì nghĩ gây duplicate adapter → bot chết hoàn toàn (0 adapter, 0 SSE).

**Cơ chế thực tế — 2 lớp cần cả 2:**

| Lớp | Vai trò | Codepath |
|---|---|---|
| `plugins.enabled: [zalo-platform]` | PluginManager load plugin → `register()` gọi `ctx.register_platform(name="zalo", ...)` → đăng ký adapter factory vào `platform_registry` | `hermes_cli/plugins.py` → `gateway/platform_registry.py` |
| `platforms.zalo.enabled: true` | Gateway tìm platform "zalo" trong config → tìm trong `platform_registry` → tạo adapter | `gateway/run.py:4564-4582` → `_create_adapter()` |

**Không có built-in Zalo adapter** trong `gateway/platforms/` → config `platforms.zalo.enabled: true`
một mình vô dụng. Chỉ plugin mới cung cấp factory.

## 🔴 Nguyên nhân gốc rễ: Bot Zalo không phản hồi (historical)

### Vấn đề 1 (Đã sửa): Session death code=1006

Session Zalo liên tục chết sau ~3-5 phút do websocket disconnect từ phía Zalo server. Bridge không có cơ chế keepAlive → cookie hết hạn → session dead.

### Vấn đề 2 (Đã sửa): Bridge không tự recovery

Khi session chết, bridge không tự động relogin → phải scan QR lại.

### Vấn đề 3 (Đã sửa): Container không reach được bridge

`host.docker.internal` resolve sai IP (`192.168.65.254`) khi bridge chưa bind `0.0.0.0`. Đã fix bằng `ZALO_PLUGIN_HOST=0.0.0.0` trong `server.js`.

### Vấn đề 4 (Đã sửa): `.env` mất newline trên Windows mount

File `.env` mount từ Windows host bị dính hết thành 1 dòng trong container → gateway không parse được env vars. Đã chuyển env vars Zalo trực tiếp vào `docker-compose.yml`.

---

## 🛠️ Hướng dẫn khởi động Bridge

### Khởi động bridge với watchdog (khuyến nghị)

```powershell
cd D:\Antigravity\hermes-zalo-plugin
# Lần đầu — với log file
Start-Process -NoNewWindow -FilePath "node" -ArgumentList "bridge-watchdog.js" -WorkingDirectory "D:\Antigravity\hermes-zalo-plugin" -RedirectStandardOutput "$env:USERPROFILE\hermes-zalo\bridge_stdout.log" -RedirectStandardError "$env:USERPROFILE\hermes-zalo\bridge_stderr.log"

# Hoặc chạy trực tiếp (không log file, output ra console hiện tại)
node bridge-watchdog.js
```

Watchdog tự động restart bridge khi crash (3s delay, không giới hạn).
Health check mỗi 10s, auto /relogin khi session dead.

**Kiểm tra bridge đang chạy:**
```powershell
curl.exe -s http://127.0.0.1:8787/health
```
Kết quả mong muốn (`sseClients` có thể là 1 hoặc 2):
```json
{ "ok": true, "loggedIn": true, "sessionDead": false, "ownId": "...", "sseClients": 1 }
```
`sseClients` luôn = 1 nhờ single-client mode (xem section 21). Nếu vẫn thấy 2,
Docker proxy tạo phantom connection → single-client mode tự evict và adapter reconnect.

### Khởi động không watchdog (debug)

```powershell
cd D:\Antigravity\hermes-zalo-plugin
node server.js
```

### Nếu cần quét lại QR
```powershell
cd D:\Antigravity\hermes-zalo-plugin
node login.mjs
# Quét QR trên màn hình bằng ứng dụng Zalo
```

### Restart gateway sau khi bridge lên
```powershell
docker exec hermes hermes gateway restart
# hoặc
docker restart hermes
```

---

## 🔁 Luồng hoạt động đúng

```
Người dùng nhắn Zalo
        ↓
zca-js (bên trong bridge) nhận tin
        ↓
bridge POST SSE event → GET /events
        ↓
adapter.py (_sse_loop) nhận event
        ↓
_on_inbound_message() → kiểm tra ZALO_ALLOWED_USERS, ZALO_GROUP_MODE
        ↓
handle_message() → Hermes AIAgent xử lý
        ↓
adapter.send() → POST bridge/send → zca-js → Zalo
```

**Markdown strip (trước khi gửi):**
```
response từ AIAgent (markdown)
        ↓
sendText() strip: ** * __ ~~ ` # - []()
        ↓
text thuần → POST /send → zca-api → Zalo
```

**Retry adapter (khi bridge bận / relogin):**
```
adapter.send() → _post(/send, data)
        ↓
request fail hoặc result.error
        ↓
retry attempt 1..5 (backoff 1s..10s)
        ↓
thành công hoặc bỏ qua sau 5 lần
```

**KeepAlive loop (chạy ngầm):**
```
_api.keepAlive() mỗi 60s (KEEPALIVE_INTERVAL_MS)
        ↓
api.getCookie() → cookie mới
        ↓
_saveCredentials() → cập nhật credentials.json
        ↓
Session không bị hết hạn → listener không đóng
```

**Silent relogin (khi session chết code 1006):**
```
listener "closed" (code 1006)
        ↓
_scheduleAutoRelogin() với linear backoff (5s, 10s...)
        ↓
relogin({ cookieOnly: true }) với 30s timeout
        ↓
thành công hoặc fail → schedule attempt tiếp theo
        ↓
thành công → listener "connected" → loggedIn=true → _autoReloginAttempts=0
```

**SSE disconnect → adapter recovery (v2 — 2026-06-11):**
```
_adapter._sse_loop() catch exception
        ↓
POST /disconnect  ← cleanup zombie SSE clients (fix Docker proxy)
        ↓
_wait_with_health_poll(backoff)  ← poll /health mỗi 2s
        ↓
bridge online → reconnect SSE ngay (không chờ hết backoff)
        ↓
SSE connected + Last-Event-ID replay → không mất event
```

**Gateway reconnect watcher (khi start fail):**
```
_gateway reconnect watcher retry sau 30..300s (exponential backoff)
        ↓
adapter.start()
        ↓
/health → loggedIn=false → poll mỗi 5s tới ~60s
        ↓
bridge login thành công → loggedIn=true → SSE connect
```

---

## ⚙️ Config summary hiện tại

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `ZALO_PLUGIN_URL` | `http://host.docker.internal:8787` | ✅ Đúng cho Docker container |
| `ZALO_PLUGIN_HOST` | `0.0.0.0` | ✅ Bridge bind all interfaces |
| `ZALO_ALLOWED_USERS` | `2825656851207986406` | Chỉ user này mới được talk to bot |
| `ZALO_GROUP_MODE` | `mention` | Bot trả lời trong group khi được @mention |
| `ZALO_ALLOWED_ACTION_GROUPS` | `read,send,interact` | OK |
| `ZALO_HOME_CHANNEL` | `2825656851207986406` | DM channel |
| `ZALO_LOG_IDS` | `true` | Log uid + threadId |

---

### 7. Docker Desktop proxy không forward TCP RST → zombie SSE connections

**Vấn đề:** Docker Desktop trên Windows dùng `com.docker.backend` làm proxy giữa container và host.
Khi container gửi TCP RST (từ `force_close=True`), proxy có thể không forward RST tới host → bridge
không nhận được `req.on("close")` → zombie client trong `sseClients`.

**Biểu hiện:** `sseClients: 2` (hoặc nhiều hơn) trên bridge health.

**Fix v3 (2026-06-12):** Single-client mode — `/events` handler evict client cũ khi client mới connect.
Không cần workaround. Docker zombie tự cleanup. (Xem section 21.)

**Fix cũ (v2, còn dùng):**
- `force_close=True` trong aiohttp connector (giảm thiểu)
- `POST /disconnect` endpoint + adapter gọi trước reconnect

### 8. Bridge login mất sau khi Windows restart

Nếu Windows restart, bridge watchdog không tự start lại (vì chạy trong PowerShell session).

**Fix:** Cài bridge như Windows service (dùng `nssm` hoặc Task Scheduler):
```
nssm install HermesZaloBridge "C:\Program Files\nodejs\node.exe" "D:\Antigravity\hermes-zalo-plugin\bridge-watchdog.js"
```

## 📝 Known Issues

### 6. s6-log lock file conflict trên volume mount (Gây treo Gateway và Bridge)

**Vấn đề:** `s6-log: fatal: unable to lock /opt/data/logs/gateways/default/lock: Resource busy`. Khi container restart (hoặc bị force kill), tiến trình cũ để lại lock file trên volume mount của Windows -> s6-log khởi động lại không acquire được lock. 

**Tác động nghiêm trọng:** S6-log bị kẹt khiến bộ đệm (pipe buffer) của luồng stdout bị đầy. Khi buffer đầy, tiến trình Gateway bên trong container bị block lại và **treo cứng** toàn bộ API. Kéo theo đó, Webhook từ Zalo Bridge gửi tới Gateway bị timeout liên tục, dẫn tới tiến trình Node.js của Zalo Bridge (`server.js`) cũng có thể bị treo hoặc kẹt kết nối. 

**Cách xử lý vĩnh viễn:** Bỏ qua cơ chế `s6-log` supervision để ghi log trực tiếp ra stdout mà không qua pipe.
- Sửa file `docker-compose.yml`, thêm biến môi trường vào container `gateway`:
```yaml
      - HERMES_GATEWAY_NO_SUPERVISE=1
```
- Recreate lại container:
```bash
docker rm -f hermes
docker compose up -d gateway
```

### 1. Process node cũ không kill được trên Windows

Một số process node chạy dưới quyền khác (Administrator/System) → `taskkill /F` báo "Access is denied".

**Workaround:**
- Mở PowerShell as Administrator → `taskkill /F /IM node.exe`
- Hoặc Task Manager → End Task

### 2. Port 8787 bị chiếm bởi process cũ

Nếu bridge cũ (PID 21480, 23464) chưa kill hết, bridge mới không start được (`EADDRINUSE`).

**Kiểm tra:**
```powershell
netstat -ano | findstr 8787
```

**Kill process chiếm port:**
```powershell
taskkill /F /PID 21480
taskkill /F /PID 23464
```

**Note:** Các process này có thể cần admin rights — mở PowerShell as Administrator.

### 3. Gateway không reach được bridge từ container

`host.docker.internal` có thể resolve sai IP trên một số phiên bản Docker Desktop.

**Kiểm tra từ container:**
```powershell
docker exec hermes python3 -c "import urllib.request; r = urllib.request.urlopen('http://host.docker.internal:8787/health', timeout=5); print(r.read().decode())"
```

**Nếu không reach được:** Restart Docker Desktop hoặc dùng IP host thực tế.

### 4. `zca-js` websocket disconnect code 1006 — ✅ Fixed via WS retry injection (Fix 24)

Bất chấp keepAlive 60s, session vẫn chết `code=1006` mỗi ~3 phút. **Fix 24** inject code 1006 vào zca-js retry list → WS reconnect nội bộ ~2s thay vì full relogin 7-12s.

**Cơ chế chịu đựng sau fix:**
- **Code 1006:** zca-js tự reconnect WS sau 2s (0 API call) — downtime ~2s
- **Code 1000:** zca-js tự reconnect WS sau 1s (0 API call) — downtime ~1s
- Fallback auto-relogin vẫn hoạt động nếu WS retry exhausted (999 lần)
- Watchdog restart bridge trong 3s nếu crash
- `uncaughtException` + `unhandledRejection` handlers → không crash khi async error

**Cần restart bridge** để load fix 24: xem hướng dẫn bên dưới.

### 5. Gateway reconnect watcher backoff mismatch (300s max)

**Vấn đề:** Gateway reconnect watcher dùng exponential backoff lên tới 300s (5 phút) giữa các lần thử kết nối lại bridge. Trong khoảng đó, bridge có thể đã online nhưng gateway không biết.

**Giải pháp hiện tại (adapter `start()`):** Khi reconnect watcher gọi `start()`, adapter poll `/health` mỗi 5s tới 60s → nếu bridge logged in trong lúc đợi, kết nối thành công ngay.

**Giới hạn:** Nếu watcher vừa fail ngay trước khi bridge online, phải chờ hết backoff (tối đa 300s từ fail trước). Với cơ chế mới, adapter đợi 60s nên xác suất miss giảm đáng kể.

### 6. s6-log lock file conflict trên volume mount

**Vấn đề:** `s6-log: fatal: unable to lock /opt/data/logs/gateways/default/lock: Resource busy`. Khi container restart, lock file cũ (0 bytes) còn tồn tại trên volume mount → s6-log mới không acquire được lock → stdout của container (docker logs) không show gateway output.

**Tác động:** Không ảnh hưởng tới gateway. Log vẫn ghi vào `gateway.log` qua Python logging.

**Fix:** Xoá lock file sau restart:
```bash
docker exec hermes rm -f /opt/data/logs/gateways/default/lock
```

### 7. 429 reconnect storm từ grace period single-client SSE (Fix 21)

**Vấn đề:** Grace period 10s (số lượng tin nhắn) → khi SSE disconnect vì Docker proxy, adapter retry trong 10s → bridge trả 429 → **reconnect loop ∞** kéo dài hàng phút. Trong storm:
- Adapter không nhận được event mới
- Khi reconnect thành công, bridge replay event từ `Last-Event-ID` qua ring buffer (200 events)
- Nếu ring buffer wrap, event bị replay → double reply hoặc lost message

**Fix 22 (server.js):** Xóa grace period + single-client eviction. Docker phantom connections coexists với client thật. Adapter `_dedup_set` xử lý duplicate event.

**Fix 23 (adapter.py _consume_sse):** Update `_last_event_id` BEFORE `_handle_sse_event` để tránh SSE replay khi disconnect trong lúc agent execution.

**Triệu chứng trong log:**
```
WARNING ... Zalo: SSE disconnected (SSE status 429); reconnecting in X.Xs
```
Hàng trăm dòng 429 liên tục trong nhiều phút.

### 26. Zalo Rich Text Formatting (Bold, Italic, Lists) (2026-06-29)

**Vấn đề:**
- Tin nhắn gửi qua Zalo Bridge bị mất in đậm (`**`), in nghiêng (`_`), số thứ tự (`1. `), và ký tự đầu dòng (`* `) do Zalo không hỗ trợ trực tiếp cú pháp markdown truyền thống và Bridge cũ đã xoá sạch markdown bằng biểu thức chính quy (regex) để tránh hiển thị literal dấu sao.
- Việc chuyển đổi in đậm text thuần dạng `**text**` -> `*text*` cũng bị thất bại do Zalo render plain text thuần túy.

**Nguyên nhân:**
- Thư viện `zca-js` của Zalo Bridge yêu cầu định dạng in đậm / in nghiêng thông qua tham số `styles` (mảng Style object dạng `{ start, len, st }`) đi kèm message gốc đã strip định dạng.
- Regex in nghiêng đơn cũ `\*(?!\*)(.+?)\*(?!\*)` nhận diện nhầm các ký tự gạch đầu dòng của list (`* Dòng 1`, `* Dòng 2`) là một khối in nghiêng siêu lớn và xoá sạch dấu sao đầu dòng.

**Cách khắc phục:**
1. **Parse Markdown sang Rich Styles:** Trong hàm `sendText` của `zaloClient.js`, bổ sung thuật toán duyệt chuỗi (regex matchAll) để bóc tách `**bold**`, `__bold__`, và `_italic_` thành các cặp `{ start, len, st }` tương ứng (với `st: "b"` cho bold và `st: "i"` cho italic) rồi gửi kèm object `content.styles`.
2. **Khắc phục List Bullet Point:** Sửa regex pattern chỉ match `_italic_` đối với in nghiêng, loại bỏ hoàn toàn việc match `*italic*` bằng dấu sao đơn để tránh nhận nhầm và nuốt mất ký tự gạch đầu dòng (`* `) của danh sách.

---

## 📚 Tham khảo

- [zaloclaw](https://github.com/monas-team/zaloclaw) — Plugin Zalo cho OpenClaw, nguồn cảm hứng cho keepAlive mechanism
- [zca-js](https://github.com/nicholasxuu/zca-js) — Thư viện Zalo unofficial API
- `D:\Antigravity\hermes-zalo-plugin\zaloClient.js` — File đã sửa
- `D:\Antigravity\hermes-zalo-plugin\server.js` — Bridge chính (đã có auto-relogin)
