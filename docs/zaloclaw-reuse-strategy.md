# Chiến Lược Tái Sử Dụng Code từ zaloclaw

## 🎯 MỤC TIÊU

**KHÔNG** bê nguyên zaloclaw → **EXTRACT** business logic + **REWRITE** glue code

---

## 📊 PHÂN TÍCH CODE ZALOCLAW

### ✅ CÓ THỂ REUSE (Pure Business Logic)

#### 1. **Client Layer** (90% reusable)

**File: `src/client/zalo-client.ts`**
- ✅ `loginWithQR()` - QR login flow
- ✅ `loginWithCredentials()` - Session restore
- ✅ `getApi()` - API singleton with race condition protection
- ✅ `imageMetadataGetter()` - Image helper

**Dependency:** CHỈ `zca-js` + `sharp` (không có OpenClaw)

**Cách reuse:**
```bash
# Copy trực tiếp vào worker
cp zaloclaw/src/client/zalo-client.ts \
   gateway/platforms/zalo/worker/src/client.ts
```

---

**File: `src/client/credentials.ts`**
- ✅ `saveCredentials()` - Lưu session với chmod 0600
- ✅ `loadCredentials()` - Load session
- ✅ `hasCredentials()` - Check auth state
- ✅ `refreshCredentials()` - Update cookies

**Dependency:** CHỈ Node.js built-ins (fs, path, os)

**Cần modify:**
```typescript
// Đổi path từ OpenClaw sang Hermes
- const CREDENTIALS_PATH = join(homedir(), ".openclaw", "zaloclaw-credentials.json");
+ const CREDENTIALS_PATH = join(homedir(), ".hermes", "data", "zalo_session.json");
```

---

#### 2. **QR Display** (100% reusable)

**File: `src/client/qr-display.ts`**
- ✅ `displayQRFromPNG()` - Terminal QR rendering

**Dependency:** CHỈ `qrcode-terminal` + `jsqr` + `pngjs`

**Copy nguyên xi:**
```bash
cp zaloclaw/src/client/qr-display.ts \
   gateway/platforms/zalo/worker/src/qr-display.ts
```

---

#### 3. **Features** (80% reusable)

**Message ID Store** (`src/features/msg-id-store.ts`)
```typescript
// ✅ Reusable - map cliMsgId ↔ msgId
export class MessageIdStore {
  private map = new Map<string, string>();
  
  set(cliMsgId: string, msgId: string) { /* ... */ }
  get(cliMsgId: string): string | undefined { /* ... */ }
}
```

**Sticker Cache** (`src/features/sticker.ts`)
```typescript
// ✅ Reusable - search & cache stickers
export async function searchStickers(keyword: string): Promise<Sticker[]>
export function cacheSticker(id: string, data: any): void
```

---

### ❌ KHÔNG THỂ REUSE (OpenClaw-specific)

#### 1. **Channel Layer** (0% reusable)

**File: `src/channel/channel.ts`**
```typescript
import type { ChannelPlugin } from "openclaw/plugin-sdk/channel-plugin-common";
import type { OpenClawConfig } from "openclaw/plugin-sdk/channel-core";
// ❌ Toàn bộ tied to OpenClaw SDK
```

**File: `src/channel/monitor.ts`**
```typescript
import { type MessageHandler } from "openclaw/plugin-sdk/channel-contract";
// ❌ Message routing logic phụ thuộc OpenClaw events
```

**→ Phải viết lại cho Hermes**

---

#### 2. **Config Schema** (0% reusable)

**File: `src/config/config-schema.ts`**
```typescript
import { Type } from "@sinclair/typebox";
// ❌ Schema cho OpenClaw config format
```

**→ Hermes dùng YAML + Python Pydantic, không dùng được**

---

#### 3. **Tools** (90% reusable)

**File: `src/tools/tool.ts`**
- ❌ Tool Schema wrapper: OpenClaw-specific
- ✅ **`dispatch()` function**: Chứa 147 Zalo actions pure logic → **100% Reusable**
- ✅ **Helper functions**: resolveUserId, resolveGroupId → **100% Reusable**

**Cách reuse:**
- Copy toàn bộ file `tool.ts` sang `src/actions.ts`.
- Xóa các phần import `@sinclair/typebox` và các wrapper của OpenClaw.
- Giữ lại toàn bộ hàm `dispatch` với 147 `case`.

---

## 🏗️ KIẾN TRÚC WORKER MỚI

```
gateway/platforms/zalo/worker/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # Entry point (NEW)
│   ├── ipc.ts                # IPC protocol (NEW)
│   ├── handlers.ts           # Method handlers (NEW)
│   │
│   ├── client.ts             # ← COPY từ zaloclaw
│   ├── credentials.ts        # ← COPY + MODIFY path
│   ├── qr-display.ts         # ← COPY nguyên
│   │
│   └── features/             # ← COPY selective
│       ├── msg-id-store.ts
│       └── sticker.ts
└── dist/
```

---

## 📋 STEP-BY-STEP REUSE GUIDE

### **Bước 1: Clone zaloclaw (chỉ để copy files)**

```bash
cd /tmp
git clone https://github.com/monasprox/zaloclaw.git
```

### **Bước 2: Setup worker project**

```bash
cd hermes-agent/gateway/platforms/zalo
mkdir -p worker/src/features
cd worker

# Init package.json
npm init -y

# Install dependencies (SAME as zaloclaw)
npm install zca-js@2.1.2 sharp@0.33.0 qrcode-terminal@0.12.0 \
            jsqr@1.4.0 pngjs@7.0.0

# Dev dependencies
npm install -D typescript@5.4.0 @types/node@25.6.0
```

### **Bước 3: Copy reusable files**

```bash
# Client layer (core logic)
cp /tmp/zaloclaw/src/client/zalo-client.ts src/client.ts
cp /tmp/zaloclaw/src/client/credentials.ts src/credentials.ts
cp /tmp/zaloclaw/src/client/qr-display.ts src/qr-display.ts

# Features
cp /tmp/zaloclaw/src/features/msg-id-store.ts src/features/
cp /tmp/zaloclaw/src/features/sticker.ts src/features/
```

### **Bước 4: Modify credentials path**

```typescript
// src/credentials.ts
import { homedir } from "node:os";
import { join } from "node:path";

- const CREDENTIALS_PATH = join(homedir(), ".openclaw", "zaloclaw-credentials.json");
+ const CREDENTIALS_PATH = join(homedir(), ".hermes", "data", "zalo_session.json");
```

### **Bước 5: Write NEW glue code**

**File: `src/index.ts`** (Entry point)
```typescript
import { loginWithQR, loginWithCredentials, getApi } from './client.js';
import { hasCredentials } from './credentials.js';
import { createInterface } from 'readline';

class ZaloWorker {
  private api: any = null;
  
  async start() {
    console.error('🚀 Zalo Worker starting...');
    
    // Auto-login with saved session or QR
    if (hasCredentials()) {
      try {
        this.api = await loginWithCredentials();
        console.error('✅ Logged in with saved credentials');
      } catch (err) {
        console.error('⚠️ Saved credentials invalid, need QR login');
        await this.qrLogin();
      }
    } else {
      await this.qrLogin();
    }
    
    // Setup message listener
    this.api.listener.on('message', (msg: any) => {
      this.emit({
        type: 'message',
        data: this.normalizeMessage(msg)
      });
    });
    
    this.api.listener.start();
    
    // IPC loop
    this.listenIPC();
  }
  
  private async qrLogin() {
    this.api = await loginWithQR(async (event) => {
      if (event.type === 'QRCodeGenerated') {
        // Emit QR event to Hermes
        this.emit({
          type: 'qr_code',
          data: { qr_data: event.data }
        });
      }
    });
    console.error('✅ QR login successful');
  }
  
  private normalizeMessage(msg: any) {
    // Convert zca-js message format → Hermes format
    return {
      from_id: msg.uidFrom || msg.fromId,
      from_name: msg.dName,
      chat_id: msg.threadId || msg.groupId,
      text: msg.content || msg.message,
      timestamp: msg.ts || Date.now(),
      is_group: !!msg.groupId,
      raw: msg
    };
  }
  
  private listenIPC() {
    const rl = createInterface({
      input: process.stdin,
      terminal: false
    });
    
    rl.on('line', async (line) => {
      try {
        const request = JSON.parse(line);
        const result = await this.handleMethod(request.method, request.params);
        this.respond(request.id, result);
      } catch (err: any) {
        this.respondError(request.id, err.message);
      }
    });
  }
  
  private async handleMethod(method: string, params: any) {
    const api = await getApi();
    
    switch (method) {
      case 'send_message':
        return await api.sendMessage(params);
      
      case 'send_image':
        return await api.sendImageMessage(params);
      
      case 'send_file':
        return await api.sendFileMessage(params);
      
      // Add more methods as needed
      
      default:
        throw new Error(`Unknown method: ${method}`);
    }
  }
  
  private emit(event: any) {
    console.log(JSON.stringify({ type: 'event', data: event }));
  }
  
  private respond(id: string, result: any) {
    console.log(JSON.stringify({ id, result }));
  }
  
  private respondError(id: string, error: string) {
    console.log(JSON.stringify({ id, error }));
  }
}

// Start worker
new ZaloWorker().start().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
```

---

**File: `src/ipc.ts`** (IPC Protocol)
```typescript
export interface IPCRequest {
  id: string;
  method: string;
  params: any;
}

export interface IPCResponse {
  id: string;
  result?: any;
  error?: string;
}

export interface IPCEvent {
  type: 'event';
  data: {
    type: string;
    [key: string]: any;
  };
}
```

---

**File: `tsconfig.json`**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

## 🔄 UPDATE STRATEGY (Khi zaloclaw có update)

### **Monitoring**

1. **Watch GitHub releases:**
```bash
# Add to RSS reader hoặc GitHub watch
https://github.com/monasprox/zaloclaw/releases
```

2. **Check changelog:**
```bash
# Định kỳ xem CHANGELOG.md
curl https://raw.githubusercontent.com/monasprox/zaloclaw/main/CHANGELOG.md
```

---

### **Update Workflow**

**Khi zaloclaw release version mới:**

#### **1. Check dependencies update**
```bash
cd /tmp/zaloclaw
git pull
git diff v2.0.3..v2.0.4 package.json

# Nếu zca-js update:
cd hermes-agent/gateway/platforms/zalo/worker
npm install zca-js@<new-version>
```

#### **2. Check reusable files changes**
```bash
# Xem files nào đã thay đổi
git diff v2.0.3..v2.0.4 src/client/

# Nếu có changes quan trọng:
# - client.ts: Copy lại method mới
# - credentials.ts: Merge changes (giữ Hermes path)
# - qr-display.ts: Copy lại nếu có fix bugs
```

#### **3. Manual merge**
```bash
# Ví dụ: zaloclaw thêm function mới trong client.ts
# File: /tmp/zaloclaw/src/client/zalo-client.ts

+ export async function refreshSession(): Promise<void> {
+   const api = await getApi();
+   const freshCookies = await api.refreshCookies();
+   refreshCredentials(freshCookies);
+ }

# → Copy vào worker/src/client.ts
```

#### **4. Test regressions**
```bash
cd worker
npm run build
node dist/index.js  # Test standalone

# Test trong Hermes
hermes gateway restart
# Chat test từ Zalo
```

---

### **Tracking Changes Template**

**File: `worker/ZALOCLAW_SYNC.md`**
```markdown
# zaloclaw Sync History

## Current Base
- zaloclaw version: v2.0.3
- Last sync: 2024-05-08

## Files Copied
- [x] src/client/zalo-client.ts → src/client.ts
- [x] src/client/credentials.ts → src/credentials.ts (MODIFIED: Hermes path)
- [x] src/client/qr-display.ts → src/qr-display.ts
- [x] src/features/msg-id-store.ts → src/features/msg-id-store.ts

## Modifications
- credentials.ts: Changed path to ~/.hermes/data/zalo_session.json
- client.ts: No changes (copied as-is)

## Update Log
### 2024-05-15 - zaloclaw v2.0.4
- Changes: Added refreshSession() in client.ts
- Action: Copied new function to worker/src/client.ts
- Status: ✅ Tested, working

### 2024-06-01 - zaloclaw v2.1.0
- Changes: zca-js upgraded to 2.2.0
- Action: Updated package.json dependency
- Status: ✅ Tested, working
```

---

## 📊 REUSE STATISTICS

| Category | Files | Reusable | Strategy |
|----------|-------|----------|----------|
| **Client** | 4 files | 95% | Copy + minor path changes |
| **Features** | 7 files | 80% | Selective copy (msg-id, sticker) |
| **QR Display** | 1 file | 100% | Copy as-is |
| **Channel** | 5 files | 0% | Rewrite for Hermes |
| **Config** | 2 files | 0% | Use Hermes config |
| **Tools** | 1 file | 90% | Extract dispatch logic |

**Total LOC reused: ~2300 lines (~80% of zaloclaw)**

**Total LOC new: ~400 lines (glue code)**

---

## 🎯 BENEFITS

### ✅ Reuse Strategy
- **Faster development:** Dùng lại tested code
- **Fewer bugs:** Client logic đã được battle-tested
- **Easy updates:** Chỉ sync 40% code
- **Independence:** Không phụ thuộc OpenClaw framework

### ❌ Bê Nguyên zaloclaw
- **Impossible:** OpenClaw dependencies không có trong Hermes
- **Brittle:** Mỗi OpenClaw update break Hermes
- **Complex:** Maintain 2 frameworks cùng lúc

---

## 🚀 QUICK START

```bash
# 1. Clone zaloclaw (read-only)
git clone https://github.com/monasprox/zaloclaw.git /tmp/zaloclaw

# 2. Setup worker
cd hermes-agent/gateway/platforms/zalo
mkdir -p worker/src/features
cd worker
npm init -y

# 3. Copy dependencies
cat > package.json <<EOF
{
  "name": "zalo-worker",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "zca-js": "^2.1.2",
    "sharp": "^0.33.0",
    "qrcode-terminal": "^0.12.0",
    "jsqr": "^1.4.0",
    "pngjs": "^7.0.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "@types/node": "^25.6.0"
  },
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js"
  }
}
EOF

npm install

# 4. Copy reusable files
cp /tmp/zaloclaw/src/client/zalo-client.ts src/client.ts
cp /tmp/zaloclaw/src/client/credentials.ts src/credentials.ts
cp /tmp/zaloclaw/src/client/qr-display.ts src/qr-display.ts

# 5. Modify credentials path
sed -i 's/.openclaw/.hermes\/data/g' src/credentials.ts

# 6. Write glue code (see above)
# Create src/index.ts, src/ipc.ts, tsconfig.json

# 7. Build & test
npm run build
npm start  # Should show "🚀 Zalo Worker starting..."
```

---

## 📚 SUMMARY

**TL;DR:**
- ❌ KHÔNG bê nguyên zaloclaw (impossible due to OpenClaw deps)
- ✅ REUSE 80% business logic (client, features, tools, QR)
- ✅ REWRITE 60% glue code (IPC, handlers, Hermes integration)
- ✅ TRACK updates manually (sync important changes)
- ⏱️ Effort: 3-4 tuần total (~1 tuần reuse, 2-3 tuần new code)

**Update frequency:**
- zaloclaw updates: ~1-2 tháng/lần
- Sync effort: ~2-4 giờ/update (chỉ copy changes)
- Critical updates (zca-js major version): Rare (<1/năm)
