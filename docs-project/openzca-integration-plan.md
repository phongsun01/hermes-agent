# Hermes Zalo Plugin — OpenZCA Integration Plan v3

> Kiến trúc: SQLite Store (DAO), MessageRepository (orchestrator), HistorySync (resumable), Queue-based SSE.
> Inspired by OpenZCA, redesigned for Hermes single-profile + realtime priority.

---

> **Lưu ý về Repository:** Hiện tại `MessageRepository` quản lý checkpoint, cache, sqlite, api, search, history, attachment, context, sync — khá nhiều. Về sau có thể tách thành `MessageWriter` / `MessageReader` hoặc `MessageQueryService` / `CheckpointService` / `HistorySyncService`. Nhưng Phase 1 chưa cần. Design doc này ghi nhận để refactor sau.

## 1. Kiến trúc tổng thể

### Hiện tại:
```
WebSocket → MessageHandler → SSE → Hermes Agent
```

### Sau:
```
WebSocket
  ↓
MessageHandler
  ├── emit SSE ngay (không await DB)
  └── push → InMemoryQueue → Worker → Repository.saveIncoming()
                                          │
                                    ┌─────┴──────────┐
                                    │ Repository      │
                                    │  biết:          │
                                    │  - SQLite       │
                                    │  - zca-js API   │
                                    │  - checkpoint   │
                                    └─────┬──────────┘
                                          │
                              ┌───────────┼───────────┐
                              ↓           ↓           ↓
                      SQLiteStore    Checkpoint    Thread/Friend
                      (pure DAO)     (SQLite)      (SQLite)

HistorySync
  ↓  (chỉ gọi Repository, không biết API)
Repository.sync(groupId)
  ↓  (tự quyết định: cache → SQLite → API)
zca-js
```
MessageHandler
  │
  ├─► SSE emit (sync, ngay lập tức)
  │
  └─► repository.saveIncoming(msg)  ← async, trong transaction
         │
         ▼
       try {
         store.insertMessage(msg)     ← trong transaction
         store.upsertCheckpoint(...)
         store.upsertThread(...)
       } catch (err) {
         log.error(`saveIncoming fail: ${err.message}`)
         // SSE đã emit. CatchupService sẽ bù khi chạy tiếp.
       }
       cache.update(...)              ← best-effort, ngoài transaction
```

> **Weight:** Hermes Zalo Bot xu ly vai tin/giay den vai chuc tin/giay.
> Neu muon don gian, co the thay queue bang:
> ```
> handler() {
>   emitSSE(msg);
>   void repository.saveIncoming(msg).catch(logError);
> }
> ```
> Node.js async I/O du cho bot Zalo. Queue that su can khi co nhieu account hoac can retry/sync batch.
> Quyet dinh: giu queue trong design de san cho tuong lai, co the simplify sau.
**Cấu hình queue:**
- `MAX_SIZE = 10000` — nếu queue đầy, chính sách drop: xem bên dưới
- Worker: `setImmediate()` loop — flush batch đến khi queue rỗng
- `MAX_RETRY = 3` — mỗi message retry 3 lần: `[100, 500, 1000]` ms
- Nếu retry hết: drop message, ghi log error + expose `/health`
- Back pressure: nếu SQLite bị lock kéo dài, queue drop thay vì block handler

**Chính sách drop khi queue đầy:**
```
Queue state trước khi drop:
  [A (cũ nhất), B, C, D (mới nhất)]

Drop oldest (giữ D):     mất A. Group: catchup bù được. DM: mất vĩnh viễn.
Drop newest (giữ A):     mất D. Dữ liệu cũ giữ nguyên thứ tự. DM cũ được bảo toàn.
```

Quyết định: **drop newest** (giữ oldest). Lý do:
- DM message cũ không fetch lại được → mất vĩnh viễn. Drop newest: DM cũ được giữ.
- Queue đầy thường xảy ra khi SQLite chậm (load đột biến). Lúc đó message cũ quan trọng hơn (catchup đã xử lý xong), message mới nhất sắp được retry.
- Nếu muốn drop oldest (giữ newest), set `QUEUE_DROP_POLICY = 'oldest'` trong config.

**Chi tiết retry queue worker:**
```
RETRY_DELAYS = [100, 500, 1000]  // ms

flush()
  for each msg in queue:
    for delay in RETRY_DELAYS:
      try:
        repository.saveIncoming(msg)
        break  // success
      catch err:
        if code is permanent (FULL, READONLY):
          log.error(`permanent drop msg ${msg.msgId}: ${err.message}`)
          queue.stats.dropped++
          break
        await sleep(delay)
    else:
      // retry hết
      log.error(`drop msg ${msg.msgId} after ${RETRY_DELAYS.length} retries`)
      queue.stats.dropped++
```

Luồng cũ (blocking):
```
handler → SSE (ngay, không await)
        → saveIncoming() async
              → transaction (insert + checkpoint + thread)
              → cache (best-effort ngoài transaction)
```

Luồng mới:
```
handler → SSE (ngay)
        → queue → setImmediate() → worker → batch transaction
```

---

## 3. SQLiteStore — Pure DAO (Không business logic)

Chỉ có `insert` / `select` / `update` / `delete`. Không `getContext()`, không `search()`. Đưa lên Repository.

### Tables

> **Privacy:** Lưu toàn bộ nội dung tin nhắn vào `content_text`/`content_json` là thay đổi có chủ đích.
> Khác với log tạm thời (ZALO_LOG_MESSAGES default off), SQLite persist dữ liệu để phục vụ AI context/search.
> **Khuyến nghị:** File SQLite cần quyền `chmod 600`. Có thể thêm mã hóa (SQLCipher) hoặc TTL clean up ở phase sau.
> Hermes dùng cho công văn chính phủ (Quảng Ninh) — nội dung nhạy cảm sẽ nằm vĩnh viễn trên đĩa, cần cân nhắc.

```sql
-- Migration: PRAGMA user_version = 1;

CREATE TABLE messages (
    message_uid   TEXT PRIMARY KEY,       -- `${threadId}_${msgId || cliMsgId || hash(threadId+sender+ts+type)}`
    thread_id     TEXT NOT NULL,
    thread_type   TEXT NOT NULL,          -- "group" | "user"
    direction     TEXT NOT NULL,          -- "incoming" | "outgoing"
    msg_id        TEXT,
    cli_msg_id    TEXT,
    sender_id     TEXT,
    sender_name   TEXT,
    timestamp_ms  INTEGER NOT NULL,
    msg_type      TEXT,
    content_text  TEXT,
    content_json  TEXT,
    status        TEXT NOT NULL DEFAULT 'normal',  -- normal | recalled | deleted | edited
    quote_msg_id  TEXT,
    quote_cli_msg_id TEXT,
    quote_owner_id  TEXT,
    source        TEXT NOT NULL DEFAULT 'live',     -- live | catchup | sync | manual | migration
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_messages_thread_time ON messages(thread_id, timestamp_ms DESC);
CREATE INDEX idx_messages_msg_id ON messages(msg_id);
CREATE INDEX idx_messages_cli_msg_id ON messages(cli_msg_id);
CREATE INDEX idx_messages_direction ON messages(thread_id, direction);

-- Attachments (tách riêng, không nhồi vào content_json)
CREATE TABLE attachments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    message_uid   TEXT NOT NULL REFERENCES messages(message_uid) ON DELETE CASCADE,
    type          TEXT NOT NULL,            -- image | video | audio | file | link | sticker
    url           TEXT,
    file_path     TEXT,
    width         INTEGER,
    height        INTEGER,
    duration_ms   INTEGER,
    mime_type     TEXT,
    file_size     INTEGER,
    raw_json      TEXT
);

CREATE INDEX idx_attachments_msg ON attachments(message_uid);
CREATE INDEX idx_attachments_type ON attachments(type, message_uid);

-- Checkpoint
CREATE TABLE checkpoint (
    thread_id        TEXT PRIMARY KEY,
    thread_type      TEXT NOT NULL,
    last_msg_id      TEXT,
    last_cli_msg_id  TEXT,
    last_timestamp_ms INTEGER NOT NULL DEFAULT 0,
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Threads (groups + friends metadata)
CREATE TABLE threads (
    thread_id     TEXT PRIMARY KEY,
    thread_type   TEXT NOT NULL,       -- "group" | "user"
    title         TEXT,
    peer_id       TEXT,                -- for DM: userId
    avatar_url    TEXT,
    is_hidden     INTEGER NOT NULL DEFAULT 0,
    raw_json      TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Friends (user directory)
CREATE TABLE friends (
    user_id       TEXT PRIMARY KEY,
    display_name  TEXT,
    zalo_name     TEXT,
    avatar_url    TEXT,
    raw_json      TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sync checkpoint (resumable)
CREATE TABLE sync_state (
    entity_type   TEXT NOT NULL,       -- "group" | "friend"
    entity_id     TEXT NOT NULL,
    cursor        TEXT,                -- dùng để resume (page token, timestamp...)
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending | syncing | done | error
    synced_count  INTEGER NOT NULL DEFAULT 0,
    error_msg     TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entity_type, entity_id)
);
```

### API

```javascript
class SQLiteStore {
    // Messages
    insertMessage(msg)               {}  // INSERT OR IGNORE
    insertMessages(msgs)             {}  // batch, transaction
    selectMessages(threadId, opts)   {}  // WHERE thread_id=? ORDER BY timestamp_ms DESC LIMIT/OFFSET
    selectMessageByMsgId(msgId)      {}
    selectMessageByCliMsgId(cliMsgId){}
    updateMessageStatus(msgId, status){}
    deleteMessage(messageUid)        {}

    // Attachments
    insertAttachment(att)            {}
    selectAttachments(messageUid)    {}

    // Checkpoint
    selectCheckpoint(threadId)       {}
    upsertCheckpoint(cp)             {}
    selectAllCheckpoints()           {}

    // Threads
    upsertThread(thread)             {}
    selectAllThreads()               {}
    selectThread(threadId)           {}
    deleteThread(threadId)           {}

    // Friends
    upsertFriend(friend)             {}
    selectAllFriends()               {}
    selectFriend(userId)             {}
    deleteFriend(userId)             {}

    // Sync state
    upsertSyncState(state)           {}
    selectSyncState(entityType, entityId) {}
    selectSyncStatesByStatus(status) {}

    // Schema
    runMigrations()                  {}  // PRAGMA user_version based
    close()                          {}
}
```

---

## 4. MessageRepository — Orchestrator duy nhất

Repository là nơi duy nhất biết:
- SQLiteStore (DAO)
- zca-js API (network)
- Cache (in-memory)

Mọi module khác (MessageHandler, HistorySync, CatchupService, AI) chỉ gọi Repository.

```javascript
class MessageRepository {
    constructor(api, store)

    // ── Write (trong transaction) ──
    async saveIncoming(msg)
        // BEGIN
        // 1. store.insertMessage(normalized)
        // 2. store.upsertCheckpoint(threadId, lastMsgId, lastTimestamp)
        // 3. store.upsertThread(...)  nếu thread chưa có
        // COMMIT
        // 4. try { cache.update(msg.senderId, senderName) } catch { log.warn }
        // 3.5 if (String(msg.senderId) === String(ownId)) msg.direction = 'outgoing'
        //    (self-loop filter: không cho bot message lọt vào incoming)
        //    Cache luôn là best-effort, không ảnh hưởng DB transaction
        // 5. return msg

    async saveOutgoing(msg)
        // Tương tự, direction='outgoing'

    async saveHistory(threadId, threadType, msgs)
        // batch insert (transaction), update checkpoint

    async saveCatchup(threadId, msgs)
        // batch insert (transaction), source='catchup'

    // ── Read ──
    async getContext(threadId, limit = 50)
        // store.selectMessages(threadId, { limit, order: 'DESC' })
        // → newest-first → reverse → AI context

    async search(filter)
        // filter: { threadId, senderId, since, until, text, type, status, direction, limit, offset }
        // Repository tự build WHERE clause nội bộ.
        // KHÔNG expose SQL builder ra ngoài.
        //
        // Ví dụ:
        //   repo.search({ threadId: 'xxx', senderId: 'yyy', text: 'hello', limit: 20 })
        //   → SELECT ... WHERE thread_id=? AND sender_id=? AND content_text LIKE ?
        //     ORDER BY timestamp_ms DESC LIMIT 20

        // Implementation:
        //   Phase 1-2: LIKE (don gian, du cho Zalo bot).
        //   Phase 3+:   FTS5 (full-text, nhanh hon voi du lieu lon).
        //   Interface khong doi, chi thay doi backend.
        //   Neu them FTS5, them VIRTUAL TABLE messages_fts + trigger sync.

    async getRecentMessages(threadId, limit, fallbackToApi = true)
        // 1. store.selectMessages(threadId, { limit })
        // 2. if length < limit && fallbackToApi
        //      if threadType === "group":
        //        msgs = await api.getGroupChatHistory(threadId, limit)
        //      if threadType === "user" (DM):
        //        msgs = await api.loadmsg(threadId, 50)  // loadmsg API, verified v8
        //    return combined

    // ── Checkpoint ──
    async getCheckpoint(threadId)
    async updateCheckpoint(threadId, msgId, ts)
    async getAllCheckpoints()

    // ── Sync ──
    async syncGroupHistory(groupId)
        // 1. check sync_state → resume nếu có cursor
        // 2. api.getGroupChatHistory(groupId, count)
        // 3. batch insert (transaction)
        // 4. update sync_state


    async syncDMHistory(userId)
        // 1. api.loadmsg(String(userId), this.maxMessagesPerThread || 50)  // loadmsg: verified working for DM in v8
        // 2. Giới hạn: mặc định 2h (ZALO_CATCHUP_MAX_WINDOW_MS, config), chưa verify rõ Zalo-side limit.
        //    Nhưng đủ để catch-up trong cửa sổ 2h.
        // 3. batch insert (transaction, filter self-loop)
        // 4. update checkpoint
    async syncFriends()
        // 1. api.getAllFriends()
        // 2. for each: store.upsertFriend(friend)
        // 3. update sync_state

    async saveGroupInfo(groupId)
        // 1. api.getGroupInfo(groupId)
        // 2. store.upsertThread(...)

    // ── Attachment ──
    async saveAttachment(messageUid, att)
    async getAttachments(messageUid)
}
```

---

## 5. HistorySync - chi con start/resume/stop

`javascript
class HistorySync {
    constructor(repository)
    // KHONG biet API, KHONG biet store. Tat ca logic sync nam trong Repository.

    async start()
        // repository.syncAllGroups()
        //   - api.getAllGroups()
        //   - for each: api.getGroupChatHistory() + batch insert + update sync_state
        //   - update thread info
        // repository.syncFriends()
        // repository.syncResume() - xu ly cac entity dang pending/error
        // return { total, done, remaining }

    async resume()
        // repository.syncResume()
        //   - sync_state WHERE status IN ('pending','error') -> tiep tuc

    async stop()
        // Dung sync dang chay (neu co)
}
```

**Resumable:** Sync 500 groups, dang o group 320 roi restart, resume() doc sync_state -> tiep tuc tu 321. Repository tu quan ly cursor va batch insert.
## 6. CatchupService — Chuyển checkpoint sang SQLite

Hiện tại: `thread_checkpoint.json`.
Sau: `repository.getCheckpoint(threadId)` / `repository.updateCheckpoint(...)`.

```javascript
// Trong zaloClient.js — thay đổi

// Cũ:
this._checkpoint = JSON.parse(fs.readFileSync('thread_checkpoint.json'))

// Mới:
this.checkpoints = await this.repository.getAllCheckpoints()
// Map<threadId, { lastMsgId, lastTimestampMs }>

// Cũ:
this._saveCheckpoint()
this._updateThreadLastSeen(threadId, msgId, ts)

// Mới:
await this.repository.updateCheckpoint(threadId, msgId, ts)
// (Repository tự gọi store.upsertCheckpoint)
```

Vẫn 50ms emit spacing. DM dùng loadmsg API (dã verify ở v8).

**Self-loop filter (bắt buộc):** `saveHistory()`/`saveCatchup()`/`saveIncoming()` phải kiểm tra `String(senderId) === String(ownId)` trước insert. Nếu trùng → `direction: 'outgoing'`. Tuyệt đối không insert message của bot thành `incoming` — sẽ gây bug self-loop trên AI context. Tương tự, checkpoint của bot outgoing vẫn được update (không skip).

**State machine (kế thừa từ v8):** `CatchupService` vẫn dùng 3 state: `CATCHUP`/`READY`/`SESSION_DEAD`. Các phương thức `_fetchThreadHistory()` và `_catchupMissedMessages()` kiểm tra `this.state === 'CATCHUP'` và abort nếu state đã đổi (do interrupt/stop/error). Chuyển checkpoint sang SQLite không làm thay đổi state machine.

---

## 7. Thread & Friend — Mọi thứ trong SQLite

Không tách JSON riêng. `friends`, `threads` cùng DB với `messages`.

```
SQLite DB file:
  ├── messages        (live + catchup + sync)
  ├── attachments
  ├── checkpoint      (last seen per thread)
  ├── threads         (group info, DM peer info)
  ├── friends         (user directory)
  ├── sync_state      (resumable sync cursor)
  └── schema_version  (PRAGMA user_version)
```

**Cache in-memory** vẫn có (Set/Map) để tránh query DB mỗi lần:
```javascript
class InMemoryCache {
    knownGroupIds = new Set()      // group-id-cache.ts style
    msgIdToCliMsgId = new LRU()    // msg-id-store.ts style, 500 entries, 30min TTL
    friendMap = new Map()          // userId → displayName
}
```

Nhưng persistence chỉ có SQLite.

---

## 8. Migration

```javascript
runMigrations() {
    const version = this.db.pragma('user_version', { simple: true });
    
    if (version < 1) {
        this.db.exec(`CREATE TABLE messages (...)`);
        this.db.exec(`CREATE TABLE attachments (...)`);
        this.db.exec(`CREATE TABLE checkpoint (...)`);
        this.db.exec(`CREATE TABLE threads (...)`);
        this.db.exec(`CREATE TABLE friends (...)`);
        this.db.exec(`CREATE TABLE sync_state (...)`);
        this.db.pragma('user_version = 1');
    }

    if (version < 2) {
        // Thêm cột mới, migration data, etc
        this.db.pragma('user_version = 2');
    }
}
```

**Migration từ JSON cũ:**
```javascript
async migrateFromJson() {
    if (!fs.existsSync('thread_checkpoint.json')) return;
    // Đọc toàn bộ file cũ trước khi ghi DB
    const raw = fs.readFileSync('thread_checkpoint.json', 'utf-8');
    let old;
    try { old = JSON.parse(raw); } catch (err) {
        log.error(`invalid checkpoint JSON, keep .bak for manual recovery: ${err}`);
        fs.renameSync('thread_checkpoint.json', 'thread_checkpoint.json.corrupted');
        return;
    }
    const entries = Object.entries(old.threads || {});
    if (entries.length === 0) {
        fs.renameSync('thread_checkpoint.json', 'thread_checkpoint.json.empty');
        return;
    }
    // Transaction: tất cả hoặc không gì cả
    const tx = this.db.transaction(() => {
        for (const [threadId, cp] of entries) {
            this.store.upsertCheckpoint({
                thread_id: threadId,
                thread_type: old.threadTypes?.[threadId] || 'group',
                last_msg_id: cp.checkpoint?.messageId || cp.lastMsgId || null,
                last_timestamp_ms: cp.checkpoint?.timestamp || cp.lastTimestampMs || 0,
            });
        }
    });
    try {
        tx();
        // Chỉ rename sau khi transaction thành công
        fs.renameSync('thread_checkpoint.json', 'thread_checkpoint.json.migrated');
    } catch (err) {
        log.error(`migration failed: ${err}. DB rolled back. Keep original .json`);
        // DB tự động rollback (transaction throw). File cũ giữ nguyên.
        throw err;  // gọi migration lại sau
    }
}
```

**Chi tiết rollback:** Nếu migration thất bại (SQL error, unique constraint...), transaction tự rollback, DB ở trạng thái trước migration. File `.json` cũ không bị xóa, có thể thử lại. Nếu `.json` bị corrupt, rename thành `.corrupted` để debug, DB bắt đầu từ checkpoint rỗng (catchup sẽ fill dần).
```

---

## 9. Error Handling Strategy

### 9.1 Queue — SQLite ghi thất bại

| Tình huống | Xử lý |
|---|---|
| Lỗi transient (lock, busy, timeout) | Retry 3 lần, backoff 100ms→500ms→1s |
| Lỗi persistent (disk full, readonly) | Drop ngay không retry. Ghi log + `/health` |
| Transaction fail (unique constraint, FK) | Drop message, ghi log + `/health` |

```
saveIncoming() → catch
  ├── if err.code === 'SQLITE_BUSY' | 'SQLITE_LOCKED' | 'SQLITE_IOERR' → retry
  ├── if err.code === 'SQLITE_FULL' | 'SQLITE_READONLY' → drop, emergency log
  └── else → retry, fallback drop
```

**Impact:** Message bị drop → SSE đã emit → Agent không thấy trong context. CatchupService sẽ bù sau (phần 9.5).

### 9.2 Queue — Đầy

```
Queue
  ├── size < MAX_SIZE (10000) → push bình thường
  ├── size === MAX_SIZE → skip push, log.warn(`queue full, dropping newest msg ${msgId}`)
  └── queue.stats.peak = max(queue.stats.peak, queue.length)
```

- **Không block handler** — handler luôn emit SSE + push, không await worker
- **Metric:** `queue.stats.dropped`, `queue.stats.peak` - expose trong `/health`

### 9.X /health endpoint

```json
GET /health
{
  "queueLength": 2,
  // Phase 2+: queueLength, queueDropped, queuePeak
  "queueDropped": 4,
  "queuePeak": 87,
  "sqliteStatus": "ok",
  "lastCatchup": "2026-07-22T10:30:00Z",
  "lastSync": "2026-07-22T09:15:00Z",
  "dbVersion": 1,
  "uptimeSeconds": 3600
}
```

Cac field duoc cap nhat boi:
- `sqliteStatus` - SQLiteStore ping (SELECT 1)
- `lastCatchup` - CatchupService last run timestamp
- `lastSync` - HistorySync last start() timestamp
- `dbVersion` - PRAGMA user_version
- `uptimeSeconds` - process.uptime()

### 9.3 HistorySync — Lỗi group

```
for each groupId:
  try:
    repository.syncGroupHistory(groupId)
  catch err:
    log.error(`sync failed for group ${groupId}: ${err}`)
    store.upsertSyncState({ entity_id: groupId, status: 'error', error_msg: err.message })
    continue  // Không dừng, sang group tiếp theo
```

- **Không dừng toàn bộ sync** — một group lỗi không ảnh hưởng group khác
- **Ghi sync_state error** — lần chạy `resumeSync()` sau sẽ thử lại
- **Rate limit (429):** `await sleep(5000)` → retry group hiện tại (tối đa 5 lần/group)

### 9.4 Migration — Lỗi giữa chừng

Migration chạy trong SQLite transaction:

- **Transaction thành công:** DB có checkpoint, file .json rename → `.migrated`
- **Transaction thất bại:** DB rollback (không checkpoint nào được insert), file .json giữ nguyên
- **File .json corrupt:** rename → `.corrupted`, DB bắt đầu rỗng (catchup fill sau)
- **Không có crash recovery:** Hermes single-process, nếu process die giữa transaction, SQLite tự rollback trên next open

### 9.5 saveIncoming() fail sau khi SSE emit

Đây là kịch bản tệ nhất: Agent đã nhận message và xử lý, nhưng SQLite không lưu được.

```
SSE emit (success)
    │
    ▼
queue → saveIncoming() → FAIL (retry hết)
    │
    ▼
Message KHÔNG có trong SQLite → Agent không thấy trong context
```

**Giải pháp:** Dùng checkpoint để CatchupService bù.

CatchupService so sánh `lastTimestampMs` trong SQLite checkpoint với `lastSeenTimestamp` (từ message handler). Nếu checkpoint cũ hơn → chứng tỏ có message bị drop → catchup fetch lại từ API.

```
CatchupService._catchupMissedMessages()
  │
  ├── repository.getAllCheckpoints()
  ├── for each thread:
  │     lastInDb = checkpoint.lastTimestampMs
  │     lastLive  = repository.getLastLiveTimestamp(threadId)  // cap nhat boi saveIncoming()
  │     if lastInDb < lastLive:
  │       → có gap → fetch group history từ lastInDb → fill
  └── update checkpoint sau khi fill
```

**Hạn chế:** DM dùng loadmsg (giới hạn 2h gần nhất), không fetch lịch sử xa như group. DM ngoài 2h bị drop → mất vĩnh viễn. Catchup bù trong 2h.

### 9.6 Graceful shutdown

Khi process nhận SIGINT/SIGTERM:

```
1. pause inbound queue (không nhận WS message mới)
2. drain queue: setImmediate loop đến khi queue.length === 0
3. close SQLite (checkpoint + WAL flush)
4. disconnect WebSocket
5. exit
```

Queue drain timeout: 5s. Nếu quá 5s, force exit (log warning).

---

| Module | Trạng thái | Ghi chú |
|---|---|---|
| **SQLiteStore** (DAO) | ❌ Chưa có | insert/select/update/delete thuần |
| **MessageRepository** | ❌ Chưa có | Orchestrator duy nhất. `saveIncoming()` transaction |
| **InMemoryCache** | ❌ Chưa có | LRU msgId→cliMsgId (500 entries), Set groupId, Map friend |
| **InboundQueue** | ❌ Phase 2+ | Phase 1: `void saveIncoming().catch()` đơn giản |
| **HistorySync** | ❌ Chưa có | Resumable, chỉ biết Repository |
| **CatchupService** | ✅ Có (JSON) | Cần chuyển `repository.*Checkpoint()` |
| **Checkpoint** | ✅ Có (atomic JSON) | Chuyển sang SQLite + migration |
| **Migration** | ❌ Chưa có | PRAGMA user_version + JSON→SQLite |
| **FTS5 search** | ❌ Optional | Thêm sau nếu cần |
| **Markdown parser** | ❌ Optional | Từ OpenZCA text-send.ts |

---

## 10. Roadmap

### Phase 1: Nền tảng
- `SQLiteStore` — 5 tables, migration (PRAGMA user_version), WAL mode
- `InMemoryCache` — LRU msgId→cliMsgId, Set groupId, Map friend
- `MessageRepository.saveIncoming()` + `getCheckpoint()` / `updateCheckpoint()`
- Migration từ `thread_checkpoint.json` cũ

### Phase 2: Sync
- `HistorySync` — resumable, group backfill, friend directory
- `Repository.syncGroupHistory()` / `syncFriends()`
- `sync_state` table + resume logic

### Phase 3: AI Context
- `Repository.getContext()` — N messages gần nhất
- `Repository.search(filter)` — MessageFilter object, tự build WHERE
- REST endpoint `/api/context?threadId=...&limit=50`

---

## 11. Data Flow Diagrams

### Inbound message:
```
handler.normalize()
  │
  ├───► SSE emit "message"       (sync, priority)
  │
  └───► repository.saveIncoming(msg)  (async, void catch)
              │
              ▼
            transaction:
              ├── store.insertMessage(msg)
              ├── repo.updateCheckpoint(msg.threadId, msg.msgId, msg.ts)
              ├── store.upsertThread(...)   (nếu chưa có)
              └── cache.update(msg.senderId, ...)  (best-effort)
```

### AI context request:
```
AI → HTTP /api/context?threadId=xxx&limit=50
  │
  ▼
repository.getContext(threadId, 50)
  │
  ▼
store.selectMessages(threadId, { limit: 50, order: 'DESC' })
  │
  ▼
reverse() → format → response
```

### History sync:
```
Login event
  │
  ▼
historySync.syncAll()
  │
  ├── repository.getAllGroups()  (tự fetch api + cache)
  │     │
  │     ▼
  │   for each groupId:
  │     repository.syncGroupHistory(groupId)
  │       ├── check sync_state → resume if exists
  │       ├── api.getGroupChatHistory(groupId, count)
  │       ├── store.insertMessages(msgs)         (batch, transaction)
  │       ├── store.upsertSyncState({ done }) 
  │       └── store.upsertThread(groupInfo)
  │
  └── repository.syncFriends()
        │
        ├── api.getAllFriends()
        └── for each: store.upsertFriend(friend)
```

---

## 12. Tổng kết

```
Trước:                                Sau:
zaloClient.js   (~2000 dòng)         zaloClient.js          (~1200 dòng)
                                      sqlite-store.js        (~200 dòng) DAO
                                      message-repository.js  (~200 dòng) orchestrator
                                      inbound-queue.js       (~60 dòng)
                                      in-memory-cache.js     (~40 dòng)
                                      history-sync.js        (~100 dòng)
```

~600 dòng mới. Không IPC. Không CLI. Không multi-profile. Một DB file duy nhất.
SSE không bao giờ chờ DB. HistorySync resume được.
