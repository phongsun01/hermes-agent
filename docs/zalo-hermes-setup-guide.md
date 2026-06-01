# Hướng Dẫn: Chat với Hermes qua Zalo (sử dụng zalo-tg bridge)

## 🎯 Mục Tiêu

Sử dụng **zalo-tg** như một bridge để forward tin nhắn giữa Zalo và Telegram bot (đã kết nối Hermes), cho phép bạn chat với Hermes AI trực tiếp từ Zalo.

## 📊 Luồng Hoạt Động

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Zalo User                                                      │
│     │                                                           │
│     │ 1. Send: "Hello Hermes"                                  │
│     ▼                                                           │
│  ┌──────────────────┐                                          │
│  │   zalo-tg        │                                          │
│  │   Bridge         │                                          │
│  └────────┬─────────┘                                          │
│           │                                                     │
│           │ 2. Forward to Telegram                             │
│           ▼                                                     │
│  ┌──────────────────────────────┐                             │
│  │  Telegram Supergroup         │                             │
│  │  ► Forum Topic: "Zalo User"  │                             │
│  │  ► Message: "Hello Hermes"   │                             │
│  └────────┬─────────────────────┘                             │
│           │                                                     │
│           │ 3. Bot detects message                             │
│           ▼                                                     │
│  ┌──────────────────┐                                          │
│  │  Telegram Bot    │                                          │
│  │  (Hermes)        │                                          │
│  └────────┬─────────┘                                          │
│           │                                                     │
│           │ 4. Send to Hermes API                              │
│           ▼                                                     │
│  ┌──────────────────┐                                          │
│  │   Hermes API     │                                          │
│  │   ► Process LLM  │                                          │
│  └────────┬─────────┘                                          │
│           │                                                     │
│           │ 5. Return response                                 │
│           ▼                                                     │
│  ┌──────────────────┐                                          │
│  │  Telegram Bot    │                                          │
│  │  Reply in topic  │                                          │
│  └────────┬─────────┘                                          │
│           │                                                     │
│           │ 6. zalo-tg detects reply                           │
│           ▼                                                     │
│  ┌──────────────────┐                                          │
│  │   zalo-tg        │                                          │
│  │   Forward back   │                                          │
│  └────────┬─────────┘                                          │
│           │                                                     │
│           │ 7. Send to Zalo                                    │
│           ▼                                                     │
│  Zalo User receives Hermes response                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Setup Chi Tiết

### Bước 1: Chuẩn Bị

**Yêu cầu:**
- ✅ Telegram bot đã kết nối với Hermes (đang hoạt động)
- ✅ Telegram Supergroup mới (dành cho zalo-tg)
- ✅ Tài khoản Zalo
- ✅ Node.js >= 18
- ✅ ffmpeg

**Quan trọng:** 
- **KHÔNG dùng chung supergroup** giữa Hermes bot hiện tại và zalo-tg
- Tạo một supergroup riêng cho zalo-tg

### Bước 2: Tạo Telegram Supergroup cho zalo-tg

1. Tạo supergroup mới trong Telegram (ví dụ: "Zalo Bridge")
2. Bật **Topics/Forum mode**:
   - Group Settings → Topics → Enable
3. Add bot vào group (bot từ @BotFather)
4. Đặt bot làm **admin** với quyền:
   - ✅ Manage topics
   - ✅ Delete messages
   - ✅ Pin messages
   - ✅ Manage chat (để nhận reactions)

### Bước 3: Cài Đặt zalo-tg

```bash
# Clone repo
git clone https://github.com/williamcachamwri/zalo-tg
cd zalo-tg

# Install dependencies
npm install

# Copy env file
cp .env.example .env
```

### Bước 4: Cấu Hình zalo-tg

Chỉnh sửa file `.env`:

```env
# Token của bot zalo-tg (KHÔNG phải bot Hermes của bạn)
# Tạo bot mới từ @BotFather
TG_TOKEN=123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ID của supergroup "Zalo Bridge" (số âm)
# Cách lấy: forward 1 tin nhắn từ group sang @userinfobot
TG_GROUP_ID=-1001234567890

# Thư mục lưu dữ liệu
DATA_DIR=./data

# Logging (optional)
LOG_LEVEL=info

# Local Bot API (optional - nếu muốn gửi file > 20MB)
LOCAL_BOT_API=0
```

### Bước 5: Đăng Nhập Zalo

```bash
# Start zalo-tg
npm run dev
```

Trong Telegram supergroup "Zalo Bridge":
```
/login
```

1. Bot sẽ gửi QR code
2. Mở app Zalo → Settings → Linked Devices → Scan QR
3. Xác nhận đăng nhập
4. ✅ Done! zalo-tg đã kết nối với Zalo

### Bước 6: Cấu Hình Telegram Bot Hermes

Bây giờ bạn cần config **Telegram bot Hermes** để:
- **Listen vào supergroup "Zalo Bridge"**
- **Chỉ reply trong Topics**
- **Xác định user từ Topic name**

#### Option A: Hermes Bot Đa Supergroup (Recommended)

Nếu Hermes bot của bạn có thể listen nhiều group:

```typescript
// Hermes bot config
const ALLOWED_GROUPS = [
  -1001111111111,  // Group chính của bạn
  -1001234567890,  // Zalo Bridge group
];

bot.on('message', async (ctx) => {
  // Chỉ xử lý từ allowed groups
  if (!ALLOWED_GROUPS.includes(ctx.chat.id)) return;
  
  // Nếu là Zalo Bridge group → chỉ reply trong topics
  if (ctx.chat.id === -1001234567890) {
    if (!ctx.message.message_thread_id) {
      // Ignore tin nhắn ngoài topic
      return;
    }
    
    // Get topic info
    const topicId = ctx.message.message_thread_id;
    const userId = `zalo_topic_${topicId}`; // Unique user ID
    
    // Process with Hermes
    const response = await hermesAPI.chat(userId, ctx.message.text);
    
    // Reply trong cùng topic
    await ctx.reply(response, {
      message_thread_id: topicId,
    });
  } else {
    // Logic bình thường cho group khác
    // ...
  }
});
```

#### Option B: Tạo Bot Hermes Thứ 2 (Đơn Giản Hơn)

Nếu không muốn modify bot hiện tại:

1. Tạo bot Telegram mới từ @BotFather (ví dụ: @HermesZaloBot)
2. Kết nối bot mới này với Hermes API (clone code bot hiện tại)
3. Config bot mới chỉ listen vào "Zalo Bridge" group
4. Add bot mới vào "Zalo Bridge" group

```typescript
// hermes-zalo-bot/index.ts
import { Telegraf } from 'telegraf';
import axios from 'axios';

const bot = new Telegraf(process.env.HERMES_ZALO_BOT_TOKEN!);
const ZALO_BRIDGE_GROUP = -1001234567890;
const HERMES_API_URL = 'https://your-hermes-api.com';

bot.on('message', async (ctx) => {
  // Chỉ xử lý từ Zalo Bridge group
  if (ctx.chat.id !== ZALO_BRIDGE_GROUP) return;
  
  // Chỉ xử lý tin nhắn trong topics
  if (!ctx.message.message_thread_id) return;
  
  // Skip nếu là tin nhắn từ bot
  if (ctx.message.from?.is_bot) return;
  
  const topicId = ctx.message.message_thread_id;
  const text = ctx.message.text || '';
  
  if (!text) return;
  
  try {
    // Send to Hermes
    const response = await axios.post(`${HERMES_API_URL}/chat`, {
      userId: `zalo_topic_${topicId}`,
      message: text,
      context: {
        platform: 'zalo',
        topicId,
      }
    });
    
    // Reply in same topic
    await ctx.reply(response.data.message, {
      message_thread_id: topicId,
    });
  } catch (error) {
    console.error('Hermes API error:', error);
    await ctx.reply('Xin lỗi, có lỗi xảy ra.', {
      message_thread_id: topicId,
    });
  }
});

bot.launch();
console.log('Hermes Zalo Bot started!');
```

---

## 🧪 Test Flow

### 1. Gửi tin từ Zalo

Trong Zalo, nhắn tin cho chính bạn hoặc bạn bè:
```
Hello, can you help me?
```

### 2. Kiểm tra Telegram

Trong group "Zalo Bridge", bạn sẽ thấy:
- Topic mới tự động tạo (tên = tên người gửi Zalo)
- Tin nhắn "Hello, can you help me?" xuất hiện trong topic

### 3. Hermes Bot Reply

Hermes bot (nếu đã config đúng) sẽ:
- Nhận tin nhắn trong topic
- Gửi request tới Hermes API
- Reply trong cùng topic: "Of course! How can I assist you?"

### 4. Nhận Reply trong Zalo

zalo-tg sẽ:
- Phát hiện reply từ Hermes bot trong topic
- Forward về Zalo
- User nhận được: "Of course! How can I assist you?"

---

## 🔧 Cấu Hình Nâng Cao

### 1. Lọc Tin Nhắn Từ Bot

Đảm bảo Hermes bot **KHÔNG reply chính tin nhắn của nó**:

```typescript
bot.on('message', async (ctx) => {
  // Skip bot messages
  if (ctx.message.from?.is_bot) return;
  
  // Skip messages từ zalo-tg bot
  if (ctx.message.from?.username === 'your_zalo_tg_bot_username') return;
  
  // ... process message
});
```

### 2. Context Management

Tách biệt context cho mỗi Zalo user:

```typescript
// Mỗi topic = 1 Zalo conversation
const conversationStore = new Map<number, ConversationContext>();

bot.on('message', async (ctx) => {
  const topicId = ctx.message.message_thread_id;
  if (!topicId) return;
  
  // Get or create context
  if (!conversationStore.has(topicId)) {
    conversationStore.set(topicId, {
      history: [],
      userId: `zalo_topic_${topicId}`,
    });
  }
  
  const context = conversationStore.get(topicId)!;
  
  // Add message to history
  context.history.push({
    role: 'user',
    content: ctx.message.text,
  });
  
  // Send to Hermes with full context
  const response = await hermesAPI.chat(context.userId, {
    message: ctx.message.text,
    history: context.history,
  });
  
  // Update history
  context.history.push({
    role: 'assistant',
    content: response,
  });
  
  await ctx.reply(response, { message_thread_id: topicId });
});
```

### 3. Typing Indicator

Hiển thị "typing..." khi Hermes đang xử lý:

```typescript
bot.on('message', async (ctx) => {
  const topicId = ctx.message.message_thread_id;
  if (!topicId) return;
  
  // Show typing
  await ctx.sendChatAction('typing', {
    message_thread_id: topicId,
  });
  
  // Process message
  const response = await hermesAPI.chat(/*...*/);
  
  await ctx.reply(response, { message_thread_id: topicId });
});
```

### 4. Handle Media từ Zalo

Nếu user gửi ảnh qua Zalo:

```typescript
bot.on('photo', async (ctx) => {
  const topicId = ctx.message.message_thread_id;
  if (!topicId) return;
  
  // Get photo URL
  const photo = ctx.message.photo[ctx.message.photo.length - 1];
  const fileLink = await ctx.telegram.getFileLink(photo.file_id);
  
  // Send to Hermes with image
  const response = await hermesAPI.chat(userId, {
    message: ctx.message.caption || '[Ảnh]',
    imageUrl: fileLink.href,
  });
  
  await ctx.reply(response, { message_thread_id: topicId });
});
```

---

## 📋 Checklist Hoàn Chỉnh

### Setup zalo-tg
- [ ] Clone repo zalo-tg
- [ ] Tạo bot mới cho zalo-tg (@BotFather)
- [ ] Tạo supergroup "Zalo Bridge" với Topics enabled
- [ ] Add zalo-tg bot vào group với quyền admin
- [ ] Config `.env` với token và group ID
- [ ] Run `npm run dev`
- [ ] Login Zalo qua `/login`
- [ ] Test: gửi tin từ Zalo → xuất hiện trong Telegram topic

### Setup Hermes Bot
- [ ] Quyết định: modify bot hiện tại hay tạo bot mới?
- [ ] Config bot listen vào "Zalo Bridge" group
- [ ] Implement logic: chỉ reply trong topics
- [ ] Skip tin nhắn từ bot
- [ ] Map topic ID → user ID
- [ ] Test: reply trong topic → tin về Zalo

### Tối Ưu (Optional)
- [ ] Implement context management
- [ ] Add typing indicator
- [ ] Handle media (photos, videos)
- [ ] Rate limiting
- [ ] Error handling
- [ ] Logging

---

## 🐛 Troubleshooting

### Tin từ Zalo không xuất hiện trong Telegram

**Check:**
- [ ] zalo-tg có đang chạy không? (`npm run dev`)
- [ ] Đã login Zalo chưa? (check logs)
- [ ] Bot có quyền admin trong group?
- [ ] Group ID trong `.env` đúng chưa?

**Debug:**
```bash
# Check zalo-tg logs
tail -f zalo-tg-logs.txt

# Hoặc trong code
console.log('Received Zalo message:', msg);
```

### Hermes bot không reply

**Check:**
- [ ] Hermes bot có trong "Zalo Bridge" group?
- [ ] Bot có quyền gửi tin nhắn?
- [ ] Logic có filter messages trong topics?
- [ ] Hermes API có hoạt động?

**Debug:**
```typescript
bot.on('message', async (ctx) => {
  console.log('Received message:', {
    chatId: ctx.chat.id,
    topicId: ctx.message.message_thread_id,
    text: ctx.message.text,
    from: ctx.message.from,
  });
  // ...
});
```

### Reply không về Zalo

**Check:**
- [ ] Reply có trong đúng topic không?
- [ ] Reply có từ bot account không? (zalo-tg forward tất cả tin trong topic)
- [ ] Check zalo-tg logs có error?

**Tip:** Đảm bảo reply với `message_thread_id`:
```typescript
await ctx.reply(response, {
  message_thread_id: ctx.message.message_thread_id,
});
```

---

## 🎯 Kết Luận

Với setup này, bạn **KHÔNG cần code thêm** cho Zalo integration! Chỉ cần:

1. ✅ zalo-tg bridge (forward Zalo ↔ Telegram)
2. ✅ Hermes bot listen vào Zalo Bridge group
3. ✅ Reply trong topics

Mọi conversation từ Zalo sẽ tự động tạo topic riêng, và Hermes sẽ reply như chat bình thường!

---

## 🚀 Nâng Cấp Sau Này

Nếu muốn tối ưu hơn, bạn có thể:

1. **Tách bot Hermes riêng** cho Zalo (dễ manage)
2. **Multi-turn conversation context** (nhớ lịch sử chat)
3. **Custom prompt** cho Zalo users
4. **Analytics**: track usage từ Zalo
5. **Rate limiting** per Zalo user

Nhưng ban đầu, setup đơn giản trên đã đủ để chat với Hermes qua Zalo! 🎉
