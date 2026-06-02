# Phân Tích & Góp Ý: Tích Hợp Zalo vào Hermes Agent

## 📊 PHẦN 1: PHÂN TÍCH ZALOCLAW

### 1.1. Tổng Quan Kiến Trúc

**zaloclaw** là một **OpenClaw channel plugin** - không phải standalone bridge như bạn nghĩ ban đầu. Điều này rất quan trọng:

```
zaloclaw = OpenClaw Plugin (TypeScript/Node.js)
    ├── Tích hợp sâu vào OpenClaw framework
    ├── Sử dụng zca-js để kết nối Zalo
    └── Cung cấp 147 Zalo API actions dưới dạng tools
```

### 1.2. Thành Phần Chính

**A. Channel Layer** (`src/channel/`)
- `channel.ts`: Plugin lifecycle, account management, dock interface
- `monitor.ts`: Message routing, access control, mention gating
- `send.ts`: Outbound messages, markdown conversion
- `onboarding.ts`: QR code login flow
- `probe.ts`: Health checks

**B. Client Layer** (`src/client/`)
- `zalo-client.ts`: zca-js wrapper, session management
- `credentials.ts`: Secure credential storage
- `accounts.ts`: Multi-account resolution
- `qr-display.ts`: Terminal QR rendering

**C. Features** (`src/features/`)
- Auto-unsend, quote reply, reactions
- Read receipts, sticker search & cache
- Message ID mapping

**D. Tools** (`src/tools/`)
- Single mega-tool với 147 actions
- Categories: messaging (16), friends (12), groups (36), polls (4), etc.

### 1.3. Dependencies Quan Trọng

```json
{
  "zca-js": "^2.1.2",          // Core Zalo protocol
  "qrcode-terminal": "^0.12.0", // QR login
  "sharp": "^0.33.0",           // Image processing
  "@sinclair/typebox": "^0.34.0",
  "zod": "^4.3.6"              // Schema validation
}
```

**Yêu cầu:**
- Node.js ≥ 22
- OpenClaw ≥ 2026.2.0
- TypeScript runtime execution

### 1.4. Đặc Điểm Kỹ Thuật

✅ **Ưu điểm:**
- Tích hợp sâu với OpenClaw plugin SDK
- 147 Zalo actions ready-to-use
- Session persistence, auto-reconnect
- Rich message support (styled text, files, media)
- Access control (DM policy, group policy, mention gating)
- Multi-account architecture

⚠️ **Hạn chế:**
- Phụ thuộc vào OpenClaw framework (nhưng logic lõi `zca-js` và `dispatch` có thể tách rời)
- Không streaming (blockStreaming: true)
- Rate limit từ Zalo (có thể bị khóa tài khoản)
- Session instability (cookies expire)
- Node.js ≥22 required

---

## 📊 PHẦN 2: PHÂN TÍCH HERMES AGENT

### 2.1. Gateway Architecture

Hermes sử dụng **plugin-based gateway system**:

```
gateway/
├── platforms/          # Built-in adapters
│   ├── base.py        # BasePlatformAdapter abstract class
│   ├── telegram.py    # Example: Telegram adapter
│   ├── discord.py
│   ├── whatsapp.py
│   └── ...
├── config.py          # Platform enum & config
├── run.py             # Gateway orchestration
└── platform_registry.py
```

### 2.2. Platform Adapter Interface

Mỗi platform adapter kế thừa `BasePlatformAdapter` và phải implement:

**Required Methods:**
```python
class BasePlatformAdapter:
    def connect() -> bool
    def disconnect()
    def send(chat_id, text, ...) -> SendResult
    def send_typing(chat_id)
    def send_image(chat_id, image_url, caption)
    def get_chat_info(chat_id) -> dict
```

**Optional Methods:**
```python
    def send_document(chat_id, path, caption)
    def send_voice(chat_id, path)
    def send_video(chat_id, path, caption)
```

### 2.3. Message Flow

```
User → Platform API → Adapter.handle_message()
    → SessionSource construction
    → Authorization check
    → Agent processing
    → Adapter.send()
    → Platform API → User
```

### 2.4. Plugin Path (Recommended)

Hermes **hỗ trợ platform plugins** tại `~/.hermes/plugins/`:

```
~/.hermes/plugins/<platform>/
├── PLUGIN.yaml       # Metadata
└── adapter.py        # BasePlatformAdapter implementation
```

**Lợi ích:**
- Zero changes to core code
- Auto-registration via `ctx.register_platform()`
- Full feature support (cron, send_message, etc.)

---

## 🔍 PHẦN 3: ĐÁNH GIÁ KẾ HOẠCH HIỆN TẠI

### 3.1. Kiến Trúc Bridge - ❌ KHÔNG TỐI ƯU

**Vấn đề với thiết kế Bridge Service:**

1. **Overhead không cần thiết:**
   - Thêm 2 lớp trung gian: Node.js Bridge + Python Adapter
   - Latency tăng: Zalo → Bridge → Hermes → Bridge → Zalo
   - Complexity: Maintain 2 codebases (Node + Python)

2. **Session sync issues:**
   - Bridge và Adapter phải đồng bộ session state
   - Cookie refresh phải propagate qua HTTP API
   - Single point of failure (Bridge dies = toàn bộ chết)

3. **zca-js không khả dụng từ Python:**
   - ĐÚNG, nhưng có giải pháp tốt hơn
   - zaloclaw là OpenClaw plugin, không phải standalone

### 3.2. Misconception về zaloclaw

**Bạn đã nhầm khi nghĩ:**
> "zaloclaw là bridge service có thể tái sử dụng"

**Thực tế:**
- zaloclaw là **OpenClaw channel plugin**
- Tuy nhiên, **Client Layer** và **Action Dispatcher** (147 actions) được viết rất tách biệt.
- Có thể trích xuất (extract) hàm `dispatch()` và các helpers để dùng trong Hermes mà không cần OpenClaw.

### 3.3. Phases - Một Số Sai Lầm

**Giai đoạn 1: "Xây dựng Zalo Bridge"**
- ❌ Reinventing the wheel
- zaloclaw đã có full functionality
- Nên reuse, không rebuild

**Giai đoạn 2: "Hermes Zalo Adapter"**
- ⚠️ Đúng hướng nhưng thiếu detail
- Không đề cập cách wrap zca-js
- Không xử lý TypeScript runtime

**Giai đoạn 3: "Cấu hình & Bảo mật"**
- ✅ Đúng về session storage
- ⚠️ Rate limit handling quá đơn giản
- ❌ Thiếu error recovery strategy

---

## 💡 PHẦN 4: ĐỀ XUẤT KIẾN TRÚC TỐI ƯU

### 4.1. Kiến Trúc Đề Xuất: **Subprocess Adapter**

```
┌─────────────────────────────────────────────────┐
│           Hermes Agent (Python)                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Zalo Platform Adapter (Python)           │  │
│  │  ├── Subprocess manager                   │  │
│  │  ├── IPC via stdio/socket                 │  │
│  │  └── Protocol bridge                      │  │
│  └───────────────────────────────────────────┘  │
│                      ↕ JSON-RPC / MessagePack    │
│  ┌───────────────────────────────────────────┐  │
│  │  Zalo Worker Process (Node.js)            │  │
│  │  ├── zca-js client                        │  │
│  │  ├── Session manager                      │  │
│  │  └── Event emitter                        │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
           ↕
    Zalo Servers
```

### 4.2. Tại Sao Tốt Hơn Bridge?

✅ **Single process context:**
- Worker subprocess của Hermes
- Shared filesystem, signals, lifecycle
- No HTTP overhead

✅ **Tight coupling:**
- Adapter start/stop worker directly
- Immediate failure detection
- Resource cleanup guaranteed

✅ **IPC hiệu quả:**
- stdio: 0 network overhead
- Unix socket: localhost loopback
- MessagePack: faster than JSON

✅ **Code reuse:**
- Dùng lại phần lớn zca-js logic
- Không duplicate zaloclaw code
- Wrap minimal glue code

### 4.3. Implementation Strategy

**A. Zalo Worker (Node.js)**

```typescript
// zalo-worker.ts
import { ZaloClient } from 'zca-js';
import { createInterface } from 'readline';

interface IPCMessage {
  id: string;
  method: string;
  params: any;
}

interface IPCResponse {
  id: string;
  result?: any;
  error?: any;
}

class ZaloWorker {
  private client: ZaloClient;
  
  async start() {
    // Load credentials from shared location
    this.client = new ZaloClient();
    
    // Login flow with QR callback
    await this.client.loginQR(undefined, async (event: any) => {
      if (event.type === 'QRCodeGenerated') {
        console.log('📲 Mở Zalo app → Quét mã QR');
        if (event.data) {
          try {
            let qrBuffer: Buffer;
            if (typeof event.data === 'object' && event.data.image) {
              qrBuffer = Buffer.from(event.data.image, 'base64');
            } else {
              const qrStr = typeof event.data === 'string' ? event.data : JSON.stringify(event.data);
              qrBuffer = await QRCode.toBuffer(qrStr);
            }
            fs.writeFileSync('./qr.png', qrBuffer);
            console.log('✅ Đã lưu mã QR vào file: qr.png');
            
            // Thông báo cho Hermes về file QR mới
            this.emit({
              type: 'qr_generated',
              data: { path: './qr.png' }
            });
          } catch (err) {
            console.error('❌ Lỗi lưu file QR:', err);
          }
        }
      }
    });
    
    // Listen for incoming events
    this.client.on('message', (msg) => {
      this.emit({
        type: 'message',
        data: msg
      });
    });
    
    // IPC loop
    this.listenIPC();
  }
  
  private listenIPC() {
    const rl = createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    rl.on('line', async (line) => {
      const msg: IPCMessage = JSON.parse(line);
      const response: IPCResponse = {
        id: msg.id,
        result: await this.handleMethod(msg.method, msg.params)
      };
      console.log(JSON.stringify(response));
    });
  }
  
  private async handleMethod(method: string, params: any) {
    // method = "zalo_action", params = { action: "send", ... }
    if (method === 'zalo_action') {
      const { dispatch } = await import('./actions.js');
      return await dispatch(params);
    }
    
    switch (method) {
      case 'login_qr':
        return await this.qrLogin();
      // ... các method nội bộ khác
      default:
        throw new Error(`Unknown method: ${method}`);
    }
  }
  
  private emit(event: any) {
    console.log(JSON.stringify({
      type: 'event',
      data: event
    }));
  }
}

new ZaloWorker().start();
```

**B. Python Adapter**

```python
# gateway/platforms/zalo.py
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional
from gateway.platforms.base import BasePlatformAdapter, MessageEvent, SendResult
from gateway.config import Platform

class ZaloAdapter(BasePlatformAdapter):
    def __init__(self, config):
        super().__init__(config, Platform.ZALO)
        self.worker: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.pending_requests = {}
        
    async def connect(self) -> bool:
        """Start the Node.js worker subprocess."""
        worker_script = Path(__file__).parent / "zalo_worker" / "dist" / "index.js"
        
        self.worker = subprocess.Popen(
            ["node", str(worker_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Start reading loop
        asyncio.create_task(self._read_loop())
        return True
    
    async def disconnect(self):
        """Stop the worker subprocess."""
        if self.worker:
            self.worker.terminate()
            self.worker.wait(timeout=5)
            self.worker = None
    
    async def _read_loop(self):
        """Read events and responses from worker."""
        while self.worker and self.worker.poll() is None:
            line = await asyncio.get_event_loop().run_in_executor(
                None, self.worker.stdout.readline
            )
            if not line:
                break
            
            msg = json.loads(line)
            
            if msg.get('type') == 'event':
                # Handle incoming Zalo event
                await self._handle_worker_event(msg['data'])
            elif 'id' in msg:
                # Response to RPC call
                req_id = msg['id']
                if req_id in self.pending_requests:
                    self.pending_requests[req_id].set_result(msg.get('result'))
    
    async def _handle_worker_event(self, event_data):
        """Convert worker event to Hermes MessageEvent."""
        if event_data['type'] == 'message':
            msg_data = event_data['data']
            event = MessageEvent(
                source=self.build_source(
                    user_id=msg_data['from_id'],
                    username=msg_data.get('from_name'),
                    chat_id=msg_data['chat_id']
                ),
                text=msg_data.get('text', ''),
                message_type=MessageType.TEXT,
                timestamp=msg_data.get('timestamp'),
                raw=msg_data
            )
            await self.handle_message(event)
    
    async def _call_worker(self, method: str, params: dict) -> any:
        """Make RPC call to worker."""
        self.request_id += 1
        req_id = str(self.request_id)
        
        future = asyncio.Future()
        self.pending_requests[req_id] = future
        
        request = {
            'id': req_id,
            'method': method,
            'params': params
        }
        
        self.worker.stdin.write(json.dumps(request) + '\n')
        self.worker.stdin.flush()
        
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        finally:
            self.pending_requests.pop(req_id, None)
    
    async def send(self, chat_id: str, text: str, **kwargs) -> SendResult:
        """Send text message."""
        result = await self._call_worker('send_message', {
            'chat_id': chat_id,
            'text': text,
            **kwargs
        })
        return SendResult(success=True, message_id=result.get('message_id'))
    
    async def send_image(self, chat_id: str, image_url: str, caption: str = "") -> SendResult:
        """Send image."""
        result = await self._call_worker('send_image', {
            'chat_id': chat_id,
            'image_url': image_url,
            'caption': caption
        })
        return SendResult(success=True, message_id=result.get('message_id'))
    
    # Implement other required methods...

def check_zalo_requirements() -> bool:
    """Check if Node.js and zca-js are available."""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False
```

### 4.4. Code Organization

```
gateway/platforms/zalo/
├── __init__.py
├── adapter.py              # Python adapter
├── worker/                 # Node.js worker
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts        # Worker entry
│   │   ├── client.ts       # ← EXTRACTED từ zaloclaw
│   │   ├── actions.ts      # ← EXTRACTED từ zaloclaw (147 actions)
│   │   ├── ipc.ts          # IPC protocol
│   │   └── handlers.ts     # Method handlers
│   └── dist/               # Compiled JS (gitignored)
└── README.md
```

### 4.5. Deployment

**Development:**
```bash
cd gateway/platforms/zalo/worker
npm install
npm run build  # TypeScript → dist/
```

**Production:**
- Bundle worker với pkg: `npx pkg dist/index.js -t node22`
- Single binary, no npm install needed
- Include in Hermes distribution

---

## 🎯 PHẦN 5: ROADMAP CHI TIẾT (REVISED)

> **Cập nhật trạng thái: 2026-06-01**
> Hermes đã được nâng cấp lên `v0.14.0` (upstream/main). Merge ZaloClaw thành công. Docker image đã được rebuild.

### Phase 1: Minimal Worker + Adapter ✅ HOÀN THÀNH

**Mục tiêu:** Gửi/nhận text messages cơ bản

**Đã thực hiện:**
- [x] Setup worker project structure (`gateway/platforms/zalo/worker/`)
- [x] Implement basic IPC protocol (stdio JSON-RPC)
- [x] Integrate zca-js login flow (QR code)
- [x] Implement send, receive events
- [x] Python adapter với subprocess management (`gateway/platforms/zalo.py`)
- [x] Basic error handling, UTF-8 encoding fix cho Windows

**Deliverable đạt được:**
- ✅ Nhận tin nhắn từ Zalo → hiện trong Hermes chat
- ✅ Hermes trả lời ngược lại qua Zalo

**Lỗi đã xử lý trong Phase này:**
- `MessageEvent.__init__() got unexpected keyword argument 'platform'` → dùng `build_source()`
- `KeyError: 'from_id'` → dùng fallback chain `.get()` với nhiều tên trường
- QR file lock trên Windows → fallback sang tên file timestamp
- `UnicodeDecodeError` subprocess → thêm `encoding='utf-8', errors='replace'`

---

### Phase 2: Rich Messages & Media ✅ HOÀN THÀNH

**Đã thực hiện:**
- [x] Worker: Implement media handlers
  - [x] send_image (từ URL + local path) — hoàn thiện với `resolveMediaSource`
  - [x] send_file — hoàn thiện với auto-download + cleanup
  - [x] send_video — mới, hỗ trợ URL và local file
  - [x] Download và cache received media — `downloadAndCacheMedia`, TTL 1 giờ
- [x] Adapter: Media caching integration
  - [x] `cache_image_from_bytes()` — lưu vào `~/.hermes/data/zalo-media-cache/`
  - [x] `send_image`, `send_file`, `send_video` methods
  - [x] `cache_media`, `get_cached_media`, `cleanup_media_cache`, `clear_media_cache`
- [x] Message formatting
  - [x] Markdown → Zalo styled text conversion (`formatMarkdownToZalo`)
    - Bold (`**text**` → `<b>text</b>`), Italic, Strikethrough, Underline, Code, Links
  - [x] Handle max message length (Zalo giới hạn ~2000 ký tự) — `truncateMessage`
- [x] Received media detection — `detectReceivedMedia` cho image/file/video
- [x] Media cache management IPC actions
  - `cache-media`, `get-cached-media`, `cleanup-media-cache`, `clear-media-cache`
  - `format-message`, `detect-media`

**Deliverable đạt được:**
- Gửi/nhận ảnh, file, video từ URL hoặc local path
- Rich text formatting (markdown → Zalo HTML)
- Auto-truncate message > 2000 ký tự
- Received media tự động cache vào `~/.hermes/data/zalo-media-cache/`
- Cache cleanup (TTL 1 giờ, manual clear)

---

### Phase 3: Session & Auth ✅ HOÀN THÀNH (cơ bản)

**Đã thực hiện:**
- [x] QR code login flow — lưu QR tại `~/.hermes/data/zalo_qr.png`
- [x] Session persistence — lưu tại `~/.hermes/data/zalo_session.json`
- [x] Auto-reconnect cơ bản khi worker restart

**Còn thiếu (Phase 3 nâng cao):**
- [ ] Cookie refresh mechanism tự động khi hết hạn
- [ ] Multi-session support (nhiều tài khoản Zalo)
- [ ] Alert khi session hết hạn

---

### Phase 4: Access Control & Groups ✅ HOÀN THÀNH

**Đã thực hiện:**
- [x] Port access control từ zaloclaw
  - DM policy (open, closed, allowlist, denylist)
  - Group policy (open, closed, allowlist, denylist)
  - Allowlist/denylist per-user, per-group
- [x] Group message handling
  - Mention detection (phát hiện khi bot bị tag)
  - `requireMention` config option
  - Strip mention prefix tự động
  - Regex mention patterns support
- [x] User/group info caching
  - TTL-based cache (5 phút) cho user info và group info
  - Actions: `get-user-info`, `get-group-info`, `refresh-group-info`
  - IPC methods: `cache_user_info`, `cache_group_info`, `get_cached_user_info`, `get_cached_group_info`
- [x] Defense-in-depth: access control chạy cả ở worker (TypeScript) và adapter (Python)
- [x] Runtime config update qua `update_access_control` IPC method
- [x] Status reporting qua `get_access_control_status`

**Config options (config.yaml `tools.zalo.extra` hoặc env vars):**
| Option | Env Var | Default | Description |
|--------|---------|---------|-------------|
| `dm_policy` | `ZALO_DM_POLICY` | `"open"` | `"open"`, `"closed"`, `"allowlist"`, `"denylist"` |
| `group_policy` | `ZALO_GROUP_POLICY` | `"open"` | `"open"`, `"closed"`, `"allowlist"`, `"denylist"` |
| `require_mention` | `ZALO_REQUIRE_MENTION` | `false` | Yêu cầu @mention trong group |
| `allowlisted_users` | `ZALO_ALLOWLISTED_USERS` | `""` | Comma-separated user IDs |
| `denylisted_users` | `ZALO_DENYLISTED_USERS` | `""` | Comma-separated user IDs |
| `allowlisted_groups` | `ZALO_ALLOWLISTED_GROUPS` | `""` | Comma-separated group IDs |
| `denylisted_groups` | `ZALO_DENYLISTED_GROUPS` | `""` | Comma-separated group IDs |
| `mention_patterns` | `ZALO_MENTION_PATTERNS` | `[]` | JSON array of regex patterns |
| `bot_name` | `ZALO_BOT_NAME` | `null` | Tên bot để phát hiện mention |
| `bot_user_id` | `ZALO_BOT_USER_ID` | `null` | User ID của bot |

**Deliverable đạt được:**
- Bot chỉ reply khi @mention trong group (khi `require_mention: true`)
- Allowlist/denylist enforcement hoạt động đầy đủ
- User/group info caching giảm API calls
- Mention prefix tự động strip khỏi message text

---

### Phase 5: Advanced Features ⏳ CHƯA BẮT ĐẦU

**Tasks cần làm:**
1. Cron delivery integration (gửi tin nhắn theo lịch)
2. `send_message` tool support (agent chủ động gửi tin)
3. Platform hints trong system prompt
4. Rate limiting đầy đủ (1 msg/sec, backoff)
5. Error recovery & structured logging
6. Metrics & monitoring

**Deliverable mục tiêu:**
- Scheduled messages via cron
- Cross-platform send_message
- Production-ready stability

---

### Phase 6: Testing & Documentation ⏳ CHƯA BẮT ĐẦU

**Tasks cần làm:**
1. Unit tests (adapter + worker)
2. Integration tests end-to-end
3. User documentation (setup guide)
4. Setup wizard contribution cho Hermes
5. Example configurations

---

## ⚠️ PHẦN 6: RỦI RO & MITIGATION

### 6.1. Technical Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **zca-js API changes** | High | Pin exact version, monitor repo |
| **Zalo blocks account** | High | Rate limiting, usage guidelines, test accounts |
| **Worker process crashes** | Medium | Auto-restart, health checks, supervisor |
| **IPC deadlock** | Medium | Timeouts, async design, monitoring |
| **Session expiry** | Medium | Auto-refresh, QR re-login, alerts |

### 6.2. Operational Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Node.js version mismatch** | Medium | Document exact version, use nvm |
| **Memory leaks** | Medium | Periodic worker restart, monitoring |
| **Credential security** | High | Encrypt storage, file permissions |

---

## 📋 PHẦN 7: SO SÁNH KIẾN TRÚC

| Aspect | Bridge (Kế hoạch cũ) | Subprocess (Đề xuất) |
|--------|---------------------|---------------------|
| **Latency** | ~50-100ms (HTTP) | ~1-5ms (IPC) |
| **Complexity** | 3 components | 2 components |
| **Deployment** | 2 separate services | Single Hermes process |
| **Failure handling** | Complex (HTTP retry) | Simple (restart) |
| **Session sync** | Manual (HTTP endpoints) | Shared filesystem |
| **Resource usage** | Higher (2 web servers) | Lower (1 subprocess) |
| **Code reuse** | Low (rebuild bridge) | High (wrap zca-js) |
| **Maintainability** | Hard (2 codebases) | Easier (1 codebase) |

---

## 🎓 PHẦN 8: LESSONS FROM ZALOCLAW

### 8.1. Nên Học Hỏi

✅ **Access control patterns:**
- dmPolicy, groupPolicy, requireMention
- Per-group overrides
- Pairing mode for unknown users

✅ **Message handling:**
- Quote reply extraction
- Media buffering (non-mention messages)
- Mention parsing

✅ **Session management:**
- Credential storage format
- Auto-login flow
- Health probes

### 8.2. Không Nên Copy

❌ **OpenClaw-specific code:**
- Plugin SDK dependencies
- Tool registration system
- Config schema (use Hermes format)

❌ **Toolset design:**
- 147 actions in 1 mega-tool
- Hermes prefers focused tools

---

## 💻 PHẦN 9: CODE EXAMPLES

### 9.1. Worker IPC Protocol

```typescript
// Message types
type IPCRequest = {
  id: string;
  method: string;
  params: any;
};

type IPCResponse = {
  id: string;
  result?: any;
  error?: { code: number; message: string };
};

type IPCEvent = {
  type: 'event';
  data: {
    event_type: 'message' | 'status' | 'error';
    payload: any;
  };
};
```

### 9.2. Error Handling

```python
class ZaloAdapter(BasePlatformAdapter):
    async def _supervise_worker(self):
        """Monitor worker health and restart if needed."""
        while True:
            if self.worker.poll() is not None:
                logger.error(f"Zalo worker died with code {self.worker.returncode}")
                await asyncio.sleep(5)  # Backoff
                await self.connect()
            await asyncio.sleep(10)
```

### 9.3. Rate Limiting

```typescript
class RateLimiter {
  private queue: Array<() => Promise<any>> = [];
  private processing = false;
  
  async enqueue<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await fn();
          resolve(result);
        } catch (err) {
          reject(err);
        }
      });
      this.process();
    });
  }
  
  private async process() {
    if (this.processing || this.queue.length === 0) return;
    this.processing = true;
    
    while (this.queue.length > 0) {
      const task = this.queue.shift()!;
      await task();
      await this.delay(1000); // 1 msg/sec
    }
    
    this.processing = false;
  }
  
  private delay(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

---

## 🏁 PHẦN 10: TÓM TẮT GÓP Ý

### 10.1. Những Điểm Tốt trong Kế Hoạch Cũ

✅ Nhận diện đúng thư viện tốt nhất (zca-js)
✅ Ý thức về session management
✅ Phân tích rủi ro rate limiting
✅ Lưu ý về security

### 10.2. Những Điểm Cần Sửa

❌ **Kiến trúc Bridge không tối ưu** → Dùng Subprocess
❌ **Rebuild zaloclaw logic** → Wrap zca-js
❌ **Thiếu implementation details** → Cung cấp code examples
❌ **Phases quá chung chung** → Roadmap chi tiết với deliverables

### 10.3. Next Steps

**Ngay lập tức:**
1. Đọc kỹ `gateway/platforms/ADDING_A_PLATFORM.md`
2. Study Telegram adapter code (best reference)
3. Setup Node.js worker project skeleton
4. Implement minimal IPC protocol

**Tuần 1:**
- Hoàn thành Phase 1 (basic send/receive)
- Test end-to-end với Hermes gateway

**Tuần 2-3:**
- Phase 2-4 (media, session, groups)
- Iterate based on testing

**Tuần 4:**
- Phase 5 (production features)
- Documentation

### 10.4. Success Criteria

✅ Gửi/nhận text messages
✅ Media support (images, files)
✅ QR login persistence
✅ Group mention gating
✅ Rate limiting không bị ban
✅ Worker auto-restart on crash
✅ Integration với send_message tool
✅ Cron delivery support

---

## 📚 PHẦN 11: TÀI LIỆU THAM KHẢO

### Code References
- [zaloclaw/src/channel/monitor.ts](https://github.com/monasprox/zaloclaw/blob/main/src/channel/monitor.ts) - Message routing
- [zaloclaw/src/client/zalo-client.ts](https://github.com/monasprox/zaloclaw/blob/main/src/client/zalo-client.ts) - zca-js wrapper
- [hermes-agent/gateway/platforms/telegram.py](https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/telegram.py) - Reference adapter
- [hermes-agent/gateway/platforms/ADDING_A_PLATFORM.md](https://github.com/NousResearch/hermes-agent/blob/main/gateway/platforms/ADDING_A_PLATFORM.md) - Platform guide

### Documentation
- [zca-js docs](https://github.com/nicholasxuu/zca-js)
- [Hermes docs](https://hermes-agent.nousresearch.com/docs/)
- [OpenClaw plugin SDK](https://github.com/nicholasxuu/openclaw) (for reference only)

---

**Kết luận:** Kế hoạch ban đầu của bạn đi đúng hướng về mặt ý tưởng nhưng có một số misconceptions về kiến trúc. Kiến trúc Subprocess sẽ đơn giản hơn, hiệu quả hơn và maintainable hơn nhiều so với Bridge approach. Với roadmap chi tiết trên, bạn có thể hoàn thành tích hợp trong 3-4 tuần.

---

## 🛠️ PHẦN 12: NHẬT KÝ SỬA LỖI VÀ CẬP NHẬT TÍCH HỢP THỰC TẾ

Dưới đây là nhật ký các lỗi phát sinh thực tế trong quá trình tích hợp Zalo Platform Adapter vào Hermes Gateway và giải pháp đã thực hiện:

### 12.1. Sửa lỗi `MessageEvent.__init__() got unexpected keyword argument 'platform'`
* **Mô tả lỗi**: Tiến trình Zalo Python Adapter crash loop mỗi khi nhận được tin nhắn từ Node.js worker do khởi tạo sai trường trong constructor của `MessageEvent`.
* **Nguyên nhân**: Class `MessageEvent` trong Hermes core (`gateway/platforms/base.py`) không nhận trực tiếp các trường `platform`, `chat_id`, `chat_type`, `user_id`, `user_name` mà nhận qua đối số `source: SessionSource`. Thêm nữa, trường chứa dữ liệu thô là `raw_message` chứ không phải `raw_data`.
* **Giải pháp**:
  - Viết lại logic khởi tạo trong `_on_message`: gọi `self.build_source(...)` để dựng một `SessionSource` an toàn, sau đó truyền vào `MessageEvent(source=source, raw_message=data, text=text, ...)`
  - Sửa các truy cập logger / print từ `event.user_id`/`event.user_name` thành `event.source.user_id`/`event.source.user_name` để tránh lỗi `AttributeError`.

### 12.2. Sửa lỗi `KeyError: 'from_id'`
* **Mô tả lỗi**: Đọc tin nhắn từ worker Node.js thỉnh thoảng bị lỗi `KeyError` do cấu trúc dữ liệu zca-js trả về không đồng nhất giữa các nhóm chat và tin nhắn cá nhân.
* **Giải pháp**: Cải tiến logic trong `zalo.py` để trích xuất trường an toàn bằng `data.get()` với fallback chain:
  - `from_id`: `from_id` -> `uidFrom` -> `fromId` -> `senderId` -> `userId` -> `'unknown'`
  - `chat_id`: `chat_id` -> `threadId` -> `groupId` -> `from_id`
  - `text`: `text` -> `content` -> `message` -> `''`

### 12.3. Cải tiến dọn dẹp file QR đăng nhập
* **Mô tả lỗi**: Khi Zalo sinh QR đăng nhập mới, nếu file QR cũ đang bị ứng dụng khác lock (ví dụ trình xem ảnh), tiến trình sẽ ném lỗi và không khởi động tiếp được.
* **Giải pháp**: Bổ sung logic xóa QR cũ trước khi lưu. Nếu không xóa được (do bị locked), chương trình tự động fallback sinh tên QR mới chứa timestamp: `zalo_qr_<timestamp>.png` giúp tránh đụng độ tài nguyên.

### 12.4. Sửa lỗi Encoding UTF-8 trên Windows Subprocess
* **Mô tả lỗi**: Subprocess trên Windows mặc định dùng bảng mã hệ thống (thường là cp1252), gây lỗi `UnicodeDecodeError` khi đọc stdout từ Node.js worker có chứa ký tự tiếng Việt hoặc Unicode.
* **Giải pháp**: Cấu hình khởi chạy subprocess với `encoding='utf-8'` và `errors='replace'` để đảm bảo luồng đọc dữ liệu mượt mà, không bị gián đoạn.

### 12.5. Sửa lỗi CRLF trong s6-overlay scripts (Docker build trên Windows)
* **Mô tả lỗi**: Container crash ngay khi khởi động với lỗi `s6-rc-compile: fatal: invalid /etc/s6-overlay/s6-rc.d/dashboard/type: must be oneshot, longrun, or bundle` và `unable to exec sh\r: No such file or directory`.
* **Nguyên nhân**: Git trên Windows tự động convert LF → CRLF cho tất cả file text. S6-overlay (Linux) không hiểu CRLF — giá trị `longrun\r` bị coi là invalid, shebang `#!/bin/sh\r` không tìm được interpreter.
* **Giải pháp**:
  - Thêm `RUN find /etc/s6-overlay/s6-rc.d /etc/cont-init.d -type f -exec sed -i 's/\r$//' {} +` vào Dockerfile sau khi COPY các file s6.
  - Thêm `.gitattributes` với `docker/s6-rc.d/**/* text eol=lf` để Git không bao giờ convert các file này sang CRLF.
  - Áp dụng tương tự cho `main-wrapper.sh`, `stage2-hook.sh`, `hermes-exec-shim.sh`.

### 12.6. Sửa lỗi thiếu zca-js trong Docker image
* **Mô tả lỗi**: Worker khởi động nhưng crash ngay với `Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'zca-js'`.
* **Nguyên nhân**: Dockerfile không có bước `npm install` cho `gateway/platforms/zalo/worker/`. `.dockerignore` loại bỏ `node_modules` nên worker không có dependencies.
* **Giải pháp**: Thêm vào Dockerfile sau bước `COPY . .`:
  ```dockerfile
  RUN if [ -f gateway/platforms/zalo/worker/package.json ]; then \
          cd gateway/platforms/zalo/worker && \
          npm install --prefer-offline --no-audit && \
          npm run build && \
          npm cache clean --force; \
      fi
  ```

### 12.7. Sửa lỗi worker không đọc được credentials trong Docker
* **Mô tả lỗi**: Worker luôn hiện `🔑 No credentials found, please scan QR code` dù file `zaloclaw-credentials.json` đã tồn tại từ lần đăng nhập trước (ngày 20/5).
* **Nguyên nhân**: `credentials.ts` dùng `join(homedir(), ".hermes/data", ...)` để xác định đường dẫn. Trong Docker, `homedir()` trả về path của user trong container (không phải `/opt/data`), trong khi volume `~/.hermes` của host được mount tại `/opt/data`. Worker tìm sai đường dẫn → không thấy credentials.
* **Giải pháp**:
  - Sửa `credentials.ts` dùng biến môi trường `HERMES_HOME` nếu có, fallback về `homedir()/.hermes`:
    ```typescript
    function getHermesDataDir(): string {
        const hermesHome = process.env.HERMES_HOME;
        if (hermesHome) return join(hermesHome, "data");
        return join(homedir(), ".hermes", "data");
    }
    ```
  - Sửa `zalo.py` (Python adapter) truyền `HERMES_HOME` vào environment của worker subprocess:
    ```python
    from hermes_constants import get_hermes_home
    worker_env = os.environ.copy()
    worker_env["HERMES_HOME"] = str(get_hermes_home())
    self.worker = subprocess.Popen(..., env=worker_env)
    ```

