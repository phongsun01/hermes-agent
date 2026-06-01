# REUSE TOOLS Từ ZALOCLAW - GIẢI PHÁP HOÀN CHỈNH

## 🎯 TÓM TẮT: TOOLS **HOÀN TOÀN CÓ THỂ** REUSE

**Nhận định cũ của tôi SAI!** Tools **CÓ THỂ** reuse gần như 100% - chỉ cần tách logic ra khỏi OpenClaw wrapper.

---

## 📊 PHÂN TÍCH TOOL ARCHITECTURE

### Cấu trúc tool của zaloclaw:

```typescript
// tool.ts
export const ZaloClawToolSchema = Type.Object({ ... })  // ← OpenClaw format

export async function executeZaloClawTool(callId, params, signal) {
  return await dispatch(params);  // ← Core logic HERE
}

async function dispatch(params) {
  const api = await getApi();  // ← zca-js client
  
  switch (params.action) {
    case "send":
      // ✅ Pure zca-js calls - 100% reusable!
      const res = await api.sendMessage(content, threadId, type);
      return ok({ success: true, msgId: res.message.msgId });
    
    case "send-image":
      // ✅ Download + zca-js - reusable!
      const buffer = await safeFetch(url);
      const res = await api.sendMessage({ attachments: [path] }, ...);
      return ok({ success: true, msgId: res.message.msgId });
    
    // ... 147 actions - ALL reusable!
  }
}
```

**Insight quan trọng:**
- ❌ Schema wrapper: OpenClaw-specific (Type.Object)
- ✅ **dispatch() function: PURE zca-js logic** → 100% reusable
- ✅ Helper functions: resolveUserId, resolveGroupId → reusable

---

## ✅ GIẢI PHÁP: 3-LAYER ARCHITECTURE

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Hermes Tool Interface (Python)        │
│ - Send via worker IPC                          │
│ - Hermes tool format                           │
└─────────────────────────────────────────────────┘
                    ↓ IPC
┌─────────────────────────────────────────────────┐
│ Layer 2: Worker RPC Handler (Node.js)          │
│ - Receive method calls                         │
│ - Route to action handlers                     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Layer 3: Action Handlers (COPIED from zaloclaw)│
│ - dispatch() function + 147 actions            │
│ - Pure zca-js logic                            │
└─────────────────────────────────────────────────┘
```

---

## 🔧 IMPLEMENTATION CHI TIẾT

### **Step 1: Copy action handlers từ zaloclaw**

```bash
# Copy toàn bộ dispatch logic
cp /tmp/zaloclaw/src/tools/tool.ts \
   gateway/platforms/zalo/worker/src/actions.ts
```

### **Step 2: Strip OpenClaw dependencies**

```typescript
// worker/src/actions.ts - AFTER copy

// ❌ Remove OpenClaw imports
- import { Type } from "@sinclair/typebox";
- import { executeZaloClawTool } from "...";

// ✅ Keep pure logic
import { getApi } from './client.js';

// ❌ Remove schema (OpenClaw-specific)
- export const ZaloClawToolSchema = Type.Object({ ... });

// ✅ Keep ENTIRE dispatch function
export async function dispatch(params: any): Promise<any> {
  const api = async () => getApi();
  
  switch (params.action) {
    case "send": {
      // ← 100% original code from zaloclaw
      if (!params.threadId || !params.message) 
        throw new Error("threadId and message required");
      const a = await api();
      const type = params.isGroup ? ThreadType.Group : ThreadType.User;
      const res = await a.sendMessage(
        { msg: params.message }, 
        params.threadId, 
        type
      );
      return { success: true, msgId: res?.message?.msgId };
    }
    
    case "send-image": {
      // ← 100% original code from zaloclaw
      if (!params.threadId || !params.url) 
        throw new Error("threadId and url required");
      const a = await api();
      const type = params.isGroup ? ThreadType.Group : ThreadType.User;
      
      // Download to temp
      const tmpPath = await downloadToTemp(params.url);
      const res = await a.sendMessage(
        { msg: params.message || "", attachments: [tmpPath] },
        params.threadId,
        type
      );
      return { success: true, msgId: res?.message?.msgId };
    }
    
    // ✅ Copy ALL 147 cases từ zaloclaw
    // case "send-file": { ... }
    // case "send-video": { ... }
    // case "add-friend": { ... }
    // case "create-group": { ... }
    // ... total ~1500 lines - COPY NGUYÊN XI
  }
}

// ✅ Keep helper functions
export async function resolveUserId(nameOrId: string): Promise<string> {
  // ← Copy nguyên từ zaloclaw
}

export async function resolveGroupId(nameOrId: string): Promise<string> {
  // ← Copy nguyên từ zaloclaw
}
```

### **Step 3: Worker RPC handler**

```typescript
// worker/src/index.ts

import { dispatch } from './actions.js';
import { loginWithQR, loginWithCredentials } from './client.js';

class ZaloWorker {
  async start() {
    // Login...
    this.listenIPC();
  }
  
  private async handleMethod(method: string, params: any) {
    // Special methods
    if (method === 'login_qr') {
      return await this.qrLogin();
    }
    
    // ALL Zalo actions → dispatch
    // method = "send", params = { action: "send", threadId: "123", ... }
    if (method === 'zalo_action') {
      return await dispatch(params);
    }
    
    throw new Error(`Unknown method: ${method}`);
  }
}
```

### **Step 4: Hermes Tool Interface (Python)**

```python
# tools/zalo_tool.py - NEW FILE

from typing import Optional, List, Dict, Any
from tools.registry import tool

# Tool schema với 147 actions
ZALO_ACTIONS = [
    "send", "send-styled", "send-image", "send-file", "send-video",
    "add-friend", "remove-friend", "block-friend",
    "create-group", "add-to-group", "remove-from-group",
    "create-poll", "vote-poll",
    # ... total 147 actions
]

@tool(
    name="zalo",
    description=f"Interact with Zalo messaging platform. {len(ZALO_ACTIONS)} actions available.",
    parameters={
        "action": {
            "type": "string",
            "enum": ZALO_ACTIONS,
            "description": "Action to perform"
        },
        "threadId": {"type": "string", "description": "Chat/thread ID"},
        "message": {"type": "string", "description": "Message text"},
        "isGroup": {"type": "boolean", "description": "Is group chat"},
        "url": {"type": "string", "description": "Media URL"},
        "userId": {"type": "string", "description": "User ID or name"},
        "groupId": {"type": "string", "description": "Group ID or name"},
        # ... all parameters from zaloclaw schema
    }
)
async def zalo_tool(
    action: str,
    threadId: Optional[str] = None,
    message: Optional[str] = None,
    isGroup: Optional[bool] = None,
    url: Optional[str] = None,
    userId: Optional[str] = None,
    groupId: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """Execute Zalo action via worker."""
    
    # Get worker instance
    from gateway.platforms.zalo import get_zalo_adapter
    adapter = get_zalo_adapter()
    
    if not adapter or not adapter.worker:
        raise RuntimeError("Zalo worker not running")
    
    # Call worker với ALL params
    params = {
        "action": action,
        "threadId": threadId,
        "message": message,
        "isGroup": isGroup,
        "url": url,
        "userId": userId,
        "groupId": groupId,
        **kwargs  # Forward all extra params
    }
    
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    
    # RPC call to worker
    result = await adapter._call_worker('zalo_action', params)
    
    return result
```

### **Step 5: Adapter integration**

```python
# gateway/platforms/zalo.py

class ZaloAdapter(BasePlatformAdapter):
    # ... existing code ...
    
    async def _call_worker(self, method: str, params: dict) -> any:
        """RPC call to worker."""
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
        
        result = await asyncio.wait_for(future, timeout=30.0)
        return result

# Global accessor for tool
_zalo_adapter: Optional[ZaloAdapter] = None

def get_zalo_adapter() -> Optional[ZaloAdapter]:
    return _zalo_adapter

def set_zalo_adapter(adapter: ZaloAdapter):
    global _zalo_adapter
    _zalo_adapter = adapter
```

---

## 📋 TOOL REGISTRATION trong Hermes

```python
# toolsets.py

ZALO_TOOLS = ["zalo"]  # Single mega-tool như zaloclaw

"hermes-zalo": {
    "description": "Zalo messaging toolset with 147 actions",
    "tools": ZALO_TOOLS,
    "includes": []
},

"hermes-gateway": {
    "description": "Full gateway toolset",
    "includes": [
        "hermes-telegram",
        "hermes-discord",
        "hermes-zalo",  # ← Add here
    ]
}
```

---

## 🎯 USAGE EXAMPLES

### **From Hermes CLI:**

```
User: Send "Hello" to my friend John on Zalo

Agent: I'll send that message for you.
[calls zalo tool with action="send", userId="John", message="Hello"]

Result: {"success": true, "msgId": "123456"}

Agent: Sent! Message ID: 123456
```

### **From Hermes Agent (tool call):**

```python
# Agent decides to use Zalo
tools_result = await call_tool(
    name="zalo",
    parameters={
        "action": "send-image",
        "threadId": "987654321",
        "url": "https://example.com/photo.jpg",
        "message": "Check this out!",
        "isGroup": True
    }
)

# Result: {"success": true, "msgId": "789012"}
```

### **Advanced: Create poll**

```
User: Create a poll in my Zalo group asking what restaurant for dinner

Agent: I'll create that poll.
[calls zalo tool]
{
  "action": "create-poll",
  "groupId": "MyFriendsGroup",
  "question": "Where should we go for dinner?",
  "options": ["Italian", "Japanese", "Mexican", "Thai"]
}

Result: {"success": true, "pollId": "456789"}
```

---

## 📊 CODE REUSE BREAKDOWN

### Từ zaloclaw/src/tools/tool.ts (1950 lines):

| Component | Lines | Reusable? | Strategy |
|-----------|-------|-----------|----------|
| **OpenClaw schema** | 150 | ❌ 0% | Replace with Hermes tool schema |
| **dispatch() function** | 1500 | ✅ **100%** | **Copy nguyên xi** |
| **Helper functions** | 200 | ✅ **100%** | **Copy nguyên xi** |
| **Type definitions** | 100 | ✅ 80% | Keep interfaces, remove OpenClaw types |

**Total reusable: ~1700/1950 lines (87%)**

---

## 🔄 UPDATE STRATEGY cho Tools

### **Khi zaloclaw thêm action mới:**

```bash
# Example: zaloclaw v2.1.0 adds "send-location" action

# 1. Check diff
cd /tmp/zaloclaw
git diff v2.0.3..v2.1.0 src/tools/tool.ts

# 2. Find new action
+ case "send-location": {
+   if (!p.threadId || !p.latitude || !p.longitude) 
+     throw new Error("threadId, latitude, longitude required");
+   const a = await api();
+   const res = await a.sendLocation({
+     lat: p.latitude,
+     lng: p.longitude,
+     name: p.locationName
+   }, p.threadId, p.isGroup ? ThreadType.Group : ThreadType.User);
+   return ok({ success: true, msgId: res?.msgId });
+ }

# 3. Copy to worker/src/actions.ts
# Add case "send-location" { ... } trong dispatch()

# 4. Update Python tool schema
# Add "send-location" to ZALO_ACTIONS array
# Add latitude, longitude params to tool definition

# 5. Test
hermes gateway restart
# Try: "send my location to John on Zalo"
```

**Effort per update: ~30 phút - 1 giờ**

---

## 💡 OPTIMIZATION: Code Generation

**Để giảm manual work, tạo script tự động:**

```python
# scripts/sync_zaloclaw_actions.py

import re
import json

def extract_actions_from_zaloclaw(tool_ts_path: str):
    """Parse zaloclaw tool.ts and extract all actions."""
    with open(tool_ts_path) as f:
        content = f.read()
    
    # Extract ACTIONS array
    actions_match = re.search(
        r'const ACTIONS = \[(.*?)\] as const;',
        content,
        re.DOTALL
    )
    
    if not actions_match:
        raise ValueError("Could not find ACTIONS array")
    
    actions_str = actions_match.group(1)
    # Parse action names
    actions = re.findall(r'"([^"]+)"', actions_str)
    
    # Extract dispatch cases
    cases = re.findall(
        r'case "([^"]+)":\s*{(.*?)\n\s*}(?=\n\s*case|\n\s*default)',
        content,
        re.DOTALL
    )
    
    return {
        'actions': actions,
        'implementations': dict(cases)
    }

def generate_worker_actions(zaloclaw_data: dict, output_path: str):
    """Generate worker/src/actions.ts from zaloclaw data."""
    
    template = """
// Auto-generated from zaloclaw tool.ts
// DO NOT EDIT MANUALLY - run sync_zaloclaw_actions.py

import { getApi } from './client.js';
import { ThreadType } from 'zca-js';

export async function dispatch(params: any): Promise<any> {
  const api = async () => getApi();
  
  switch (params.action) {
{cases}
    default:
      throw new Error(`Unknown action: ${params.action}`);
  }
}
"""
    
    cases_code = []
    for action, impl in zaloclaw_data['implementations'].items():
        case_code = f'    case "{action}": {{{impl}\n    }}'
        cases_code.append(case_code)
    
    final_code = template.format(cases='\n\n'.join(cases_code))
    
    with open(output_path, 'w') as f:
        f.write(final_code)

def generate_python_tool_schema(actions: list, output_path: str):
    """Generate Python tool schema."""
    
    template = """
# Auto-generated from zaloclaw
# DO NOT EDIT MANUALLY

ZALO_ACTIONS = {actions}
"""
    
    actions_str = '[\n    ' + ',\n    '.join(f'"{a}"' for a in actions) + '\n]'
    
    with open(output_path, 'w') as f:
        f.write(template.format(actions=actions_str))

# Usage
zaloclaw_data = extract_actions_from_zaloclaw('/tmp/zaloclaw/src/tools/tool.ts')
generate_worker_actions(zaloclaw_data, 'worker/src/actions.ts')
generate_python_tool_schema(zaloclaw_data['actions'], 'tools/zalo_actions.py')

print(f"✅ Generated {len(zaloclaw_data['actions'])} actions")
```

**Với script này, update chỉ mất 5 phút:**

```bash
# Update workflow
git clone https://github.com/monasprox/zaloclaw.git /tmp/zaloclaw
cd /tmp/zaloclaw && git pull

cd hermes-agent
python scripts/sync_zaloclaw_actions.py

# Review changes
git diff worker/src/actions.ts
git diff tools/zalo_actions.py

# Test & commit
npm run build --prefix gateway/platforms/zalo/worker
hermes gateway restart
```

---

## 🎓 KEY INSIGHTS

### ✅ **Tôi đã nhầm ở document trước:**

**Nhận định cũ:**
> "Tools 0% reusable - phụ thuộc OpenClaw"

**Thực tế:**
- Schema wrapper: 10% của code - OpenClaw specific
- **dispatch() + helpers: 90% của code - PURE zca-js** ← 100% reusable!

### ✅ **Zaloclaw tools = Gold Mine:**

- 147 actions = ~1700 lines tested code
- 100% business logic, 0% OpenClaw coupling (trong dispatch)
- Just copy + thin wrapper = instant 147 Zalo actions trong Hermes

### ✅ **3-layer architecture = Best of both worlds:**

```
Python (Hermes tool interface)
  ↓
Node.js RPC (thin wrapper)
  ↓
zaloclaw dispatch() (COPY NGUYÊN XI - 1700 lines)
```

---

## 📊 FINAL COMPARISON

| Approach | Development | Maintenance | Feature Coverage |
|----------|-------------|-------------|------------------|
| **Viết lại tools** | 4-6 tuần | Easy | Incomplete (chỉ implement cái cần) |
| **Copy dispatch()** | 3-5 ngày | Easy | **100% (147 actions)** |
| **Bê nguyên zaloclaw** | Impossible | N/A | N/A |

---

## 🚀 QUICK START

```bash
# 1. Copy tools logic
cp /tmp/zaloclaw/src/tools/tool.ts \
   gateway/platforms/zalo/worker/src/actions.ts

# 2. Strip OpenClaw imports (5 phút manual edit)
# Remove: @sinclair/typebox, openclaw imports
# Keep: dispatch() function + helpers

# 3. Create Python tool wrapper
cat > tools/zalo_tool.py <<'EOF'
# See Step 4 implementation above
EOF

# 4. Test
cd gateway/platforms/zalo/worker
npm run build

hermes gateway start
# Chat: "send 'hi' to John on Zalo"
# → Uses zalo tool → dispatch("send") → zca-js
```

**Result: 147 Zalo actions trong 1 ngày thay vì 4-6 tuần!**

---

## 📝 TÓM TẮT

**CÂU HỎI CỦA BẠN:**
> "Tools quan trọng nhất lại không dùng được?"

**TRẢ LỜI:**
✅ **HOÀN TOÀN DÙNG ĐƯỢC!** 

- ❌ Schema wrapper: Không dùng (10% code)
- ✅ **dispatch() function: Copy nguyên xi (90% code)**
- ✅ 147 actions = ~1700 lines business logic = 100% reusable
- ⏱️ Effort: 1 ngày copy + test thay vì 4-6 tuần viết lại
- 🔄 Update: 30 phút - 1 giờ/release (hoặc 5 phút với script)

**Đây chính là giá trị lớn nhất của zaloclaw - không phải framework mà là 147 battle-tested action handlers!**
