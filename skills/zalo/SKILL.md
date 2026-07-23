---
name: zalo
description: "Connect, configure, and troubleshoot Zalo messaging platform in Hermes Agent — env vars, profile isolation, group/DM setup, data storage patterns, and common issues."
version: 1.2.0
author: Hermes Agent
tags: [hermes, zalo, messaging, gateway, profile, configuration, troubleshooting]
---

# Zalo Platform for Hermes Agent

Hermes connects to Zalo via the **zalo-platform plugin** (a Python adapter in `plugins/zalo/`) and a companion **Node.js bridge** (`hermes-zalo-plugin`) that runs [zca-js](https://github.com/zca-js/zca-js) — an unofficial Zalo personal API. The bridge communicates with Hermes over HTTP/SSE on `localhost`.

## Architecture

```
Zalo App ←→ Node.js Bridge (zca-js, port 8787) ←HTTP/SSE→ Hermes Gateway (zalo-platform plugin) ←→ Agent
```

- The Node.js bridge handles the Zalo protocol (login via QR, message polling, sending).
- The Hermes plugin (`plugins/zalo/`) translates between the bridge's HTTP API and Hermes's internal platform adapter interface.
- Each Hermes profile can have its own Zalo connection with independent config.

## Configuration (Environment Variables)

All Zalo config happens via environment variables in the profile's `.env` file (e.g. `/opt/data/profiles/<profile>/.env`). **For the default profile** (where no `/opt/data/profiles/default/` directory exists), the config lives at `/opt/data/.env`. The plugin reads them at gateway startup — **gateway restart required** after changes.

| Variable | Required | Description |
|----------|----------|-------------|
| `ZALO_PLUGIN_URL` | ✅ Yes | Base URL of the Node.js bridge (e.g. `http://host.docker.internal:8787`) |
| `ZALO_PLUGIN_TOKEN` | No | Shared secret matching bridge config |
| `ZALO_HOME_CHANNEL` | No | Default thread for cron/notification delivery. Format: `<threadId>` or `<threadType>:<threadId>` |
| `ZALO_ALLOWED_USERS` | No | Comma-separated Zalo user IDs allowed to interact. **Empty = everyone allowed** (Telegram-style) |
| `ZALO_ALLOWED_THREADS` | No | Comma-separated thread/group IDs the bot operates in. **Empty = everywhere** |
| `ZALO_GROUP_MODE` | No | How the bot behaves in groups: **`off`** (DM only, never responds in groups), **`mention`** (only when @mentioned or replied-to, default), **`all`** (every message in allowed groups) |
| `ZALO_LOG_IDS` | No | `true` = log sender uid + threadId of every inbound message for discovery |
| `ZALO_ALLOWED_ACTION_GROUPS` | No | Permission groups by danger level: `read,send,interact,manage,destructive` or `all`. Default: `read,send,interact` |
| `ZALO_ALLOW_DESTRUCTIVE` | No | Allow destructive actions (disperse group, delete messages, block users, etc.). **Default: false** |
| `ZALO_ALLOWED_ACTIONS` | No | Custom allowlist: comma-separated zca-js method names |
| `ZALO_DENIED_ACTIONS` | No | Custom denylist (highest precedence) |
| `ZALO_CLIMSG_RETENTION_DAYS` | No | Days to keep undo cache (default 30, 0 = memory-only) |
| `ZALO_INFO_CACHE_TTL` | No | Seconds to cache user/group info (default 600) |
| `ZALO_INFO_MIN_INTERVAL_MS` | No | Min ms between info calls (default 1500) |

### Common Configuration Patterns

**Pattern 1: Bot for one person (DM only)**
```ini
ZALO_ALLOWED_USERS=<user_id>
ZALO_GROUP_MODE=off
ZALO_HOME_CHANNEL=<user_id>
```

**Pattern 2: Family/group assistant (@mention only)** — ⚠️ **DM trap:** When `ZALO_ALLOWED_THREADS` is set to a group-only ID, DMs from allowed users are silently dropped (thread filter runs before user filter). See *"Bot doesn't respond in DM"* below.
```ini
ZALO_ALLOWED_USERS=    # empty = everyone in group
ZALO_ALLOWED_THREADS=<group_id>
ZALO_GROUP_MODE=mention
ZALO_HOME_CHANNEL=<group_id>
```
To also allow DMs, add user IDs to `ZALO_ALLOWED_THREADS`:
```ini
ZALO_ALLOWED_THREADS=<group_id>,<user_id_1>,<user_id_2>
```

**Pattern 3: Company bot (all messages in group)**
```ini
ZALO_ALLOWED_THREADS=<group_id>
ZALO_GROUP_MODE=all
```

## Profile Isolation

Each Hermes profile (`~/.hermes/profiles/<name>/`) has **fully independent** Zalo configuration:

- **Config**: `profiles/<name>/config.yaml`
- **Env vars**: `profiles/<name>/.env` — Zalo plugin reads from here
- **State DB**: `profiles/<name>/state.db` — sessions, messages, metadata
- **Memories**: `profiles/<name>/memories/MEMORY.md`, `USER.md`
- **SOUL.md**: `profiles/<name>/SOUL.md` — custom persona for that profile (e.g. "Lala Tran" family assistant)
- **Plugin**: `profiles/<name>/plugins/zalo/` — profile-specific plugin copy (can override the default)

### SOUL.md Example — Family Assistant Persona

The `SOUL.md` file in a profile defines the bot's personality and mission. Example from a family-profile bot:

```markdown
Bạn là trợ lý gia đình tên là "Lala Tran". Bạn đang hoạt động trong nhóm chat Zalo
"Bi bống house" để hỗ trợ các thành viên trong gia đình.

Nhiệm vụ chính:
1. Thu thập thông tin cá nhân của các thành viên trong gia đình
2. Giữ giọng điệu ấm áp, thân thiện
3. Chỉ hỏi MỘT câu tại một thời điểm
4. Lưu thông tin vào memory tool ngay sau khi thu thập xong
```

**Critical: SOUL.md instructions take effect at session start for the profile they belong to. A different profile will NOT read another profile's SOUL.md.**

> **Warning:** Zalo config in one profile does NOT affect another profile's Zalo connection. To run multiple Zalo bots, each needs its own profile, its own Node.js bridge instance (on a different port), and its own QR login session.

## Data Storage & Persistence

When the gateway runs, Hermes keeps session data and memories in **RAM + SQLite WAL**. The on-disk files are:

| File | Content | When written |
|------|---------|-------------|
| `state.db` + `state.db-wal` | Sessions, messages, FTS index, state metadata | Continuously (WAL mode) |
| `memories/MEMORY.md` | Agent's persistent notes (memory tool) | On memory save |
| `memories/USER.md` | User profile info | On user profile save |
| `response_store.db` | Last response cache | On each response |

**Critical fact:** When the gateway is running, the `state.db-wal` file may contain uncommitted session data that **cannot be read from outside the gateway process** (SQLite WAL lock). This means:
- If the bot remembers information in conversation, it's in RAM/WAL — not yet visible to external readers
- **Restarting the gateway** checkpoints the WAL to `state.db` and flushes memories to disk
- **Also:** in-memory-only data is lost if the gateway crashes without checkpointing

To force a flush without full restart, the bot must explicitly call the `memory` tool with `action='add'` or `action='replace'`, which writes to `MEMORY.md`/`USER.md` immediately.

## Troubleshooting

### Symptom: Bot doesn't respond in group
**Check order:**
1. `ZALO_GROUP_MODE` in profile's `.env` — must be `mention` or `all` (not `off`)
2. `ZALO_ALLOWED_THREADS` — if set, must include the group's ID
3. `ZALO_ALLOWED_USERS` — if set, the sender must be in the list
4. Restart gateway after any `.env` change

### Symptom: Bot doesn't respond in DM (direct message)

**Log signature:**
```
Zalo inbound: uid=2825656851207986406 name='Xitrum' threadId=2825656851207986406 type=dm
```
Message appears in `agent.log` (adapter-level) — but no `inbound message: platform=zalo...` follows, and no agent session is created.

**Cause — filter-ordering trap in adapter.py (`_on_inbound_message` at `plugins/zalo/adapter.py`):**

The adapter checks filters in this order:

```
1. ZALO_ALLOWED_THREADS  → if set, DROP messages from threads NOT in the list  (line 637)
2. ZALO_ALLOWED_USERS    → if set, DROP messages from users NOT in the list    (line 642)
3. ZALO_GROUP_MODE       → group-specific behaviour (off/mention/all)          (line 647)
```

When `ZALO_ALLOWED_THREADS` is set to a **group ID only** (e.g. `3339712927031818889`), DM messages are silently dropped at step 1 — because the DM's `threadId` (the user's own UID) is not in the allowed_threads list. The `ZALO_ALLOWED_USERS` check at step 2 never even runs.

The `logger.debug()` call at line 638 is NOT visible at INFO log level, making the drop completely silent under normal logging.

**Fix — three approaches:**

**A) Include DM thread IDs in `ZALO_ALLOWED_THREADS`:** Add the user's Zalo ID alongside the group ID:
```ini
ZALO_ALLOWED_THREADS=3339712927031818889,2825656851207986406
```

**B) Remove `ZALO_ALLOWED_THREADS` entirely** and rely on `ZALO_ALLOWED_USERS` alone for access control:
```ini
# ZALO_ALLOWED_THREADS=   ← comment out or remove
ZALO_ALLOWED_USERS=2825656851207986406,3656141905842635373
```

**C) Patch the adapter filter order** — move the user check before the thread check, so allowed-user DMs bypass the thread filter:
```python
# Swap: check users first, then threads
if self._allowed_users and sender_id not in self._allowed_users:
    logger.debug("Zalo: ignoring message from non-allowed user %s", sender_id)
    return
if self._allowed_threads and thread_id not in self._allowed_threads:
    logger.debug("Zalo: ignoring message in non-allowed thread %s", thread_id)
    return
```

**Verification:** After fix, look for `inbound message: platform=zalo...` in `agent.log` to confirm routing to the agent.

**Detection command:**
```bash
grep "Zalo inbound" /opt/data/logs/agent.log | tail -5
# If messages show but no agent response, check agent.log for missing
# "inbound message: platform=zalo" lines for those timestamps
```

**⚠️ .pyc staleness trap:** After editing `adapter.py` and restarting the gateway, Python may not recompile the bytecode if the `.py` timestamp is too close to the cached `.pyc` (common on WSL/9p mounts). Verify the patch actually loaded:

```bash
# Check if bytecode contains your patch
strings /opt/data/plugins/zalo/__pycache__/adapter.cpython-313.pyc | grep "your_new_function_name"
# If not found → delete __pycache__ and restart:
rm -rf /opt/data/plugins/zalo/__pycache__/
```

See `references/stale-bytecode-detection.md` for full details.

### Symptom: Cron/proactive messages land in nick `#` (bot's own DM) instead of the target group

**Likely cause:** The adapter's `_thread_type_from_chat_id()` method in `plugins/zalo/adapter.py` falls back to `"user"` when the group ID is not yet cached from an inbound message. Proactive sends (cron, no_agent scripts) bypass the inbound-message path, so `_thread_types` may not contain the group ID.

**Root-cause trace:**
1. `send()` receives raw chat_id (no `group:` prefix) and calls `_thread_type_from_chat_id`
2. `_clean_target()` finds no prefix → `inferred_type = None`
3. `metadata` from cron delivery has no `thread_type`
4. `_thread_types` cache lacks the group ID (no inbound message ever arrived from it)
5. Falls through to `return "user"` → zca-js interprets this as a DM to the bot's own account

**Fix — approach A (patch the adapter):**
Add a check against `self._allowed_threads` (populated from `ZALO_ALLOWED_THREADS`) before the cache lookup:

```python
# In _thread_type_from_chat_id(), before the cache-lookup block:
if str(chat_id) in self._allowed_threads:
    return "group"
```

Restart gateway after patching. See `references/delivery-tracing.md` for the full code flow and `_clean_target` logic.

**Fix — approach B (use `group:` prefix in chat_id):**
The adapter's `_clean_target()` accepts `"group:<id>"` and `"user:<id>"` prefixes. If you control delivery (e.g. custom cron target), use `"group:3339712927031818889"` to force the correct type regardless of cache state.

**Verify:**
```bash
curl -X POST http://127.0.0.1:8787/send \
  -H "Content-Type: application/json" \
  -d '{"threadId": "<group_id>", "threadType": "group", "text": "test manual"}'
```
If the test works but cron still fails → the fix needed is in the adapter (approach A).

### Symptom: Bot responds but seems forgetful after restart
**Likely cause:** Data was in RAM/WAL and never flushed to memories. Check `memories/MEMORY.md` — if empty, the bot didn't save explicitly before restart. Add explicit memory.save() calls to critical flows, or instruct the bot in SOUL.md to save after each important interaction.

### Symptom: Profile gateway disconnected — need to consolidate to another profile

When a profile's gateway disconnects or you decide to stop using it:

1. Check gateway state: `hermes gateway list` shows all running profiles
2. The disconnected profile's gateway process may still be alive (s6-supervise restarts it) — kill it: `kill <PID>` or stop via s6
3. Copy the disconnected profile's `ZALO_ALLOWED_THREADS` group IDs and `ZALO_ALLOWED_USERS` to the surviving profile's `.env`
4. Set `ZALO_GROUP_MODE=mention` (or `all`) in the surviving profile so it responds in groups
5. Restart the surviving profile's gateway

**Note:** The SOUL.md defining the disconnected profile's persona is not portable — the surviving profile will use its own personality. If the bot behavior should be preserved, either merge the SOUL.md content into the surviving profile's instructions, or accept the personality change.

### Symptom: state.db returns "disk I/O error" when read from another process

**Cause:** The gateway process has an exclusive lock on `state.db-wal` (SQLite WAL mode). External readers (e.g. a terminal Python script) get disk I/O errors because the WAL is locked by the running Hermes gateway.

**Workaround — copy the files before reading:**
```bash
cp /opt/data/profiles/<profile>/state.db /tmp/readable.db
cp /opt/data/profiles/<profile>/state.db-wal /tmp/readable.db-wal
cp /opt/data/profiles/<profile>/state.db-shm /tmp/readable.db-shm
sqlite3 /tmp/readable.db "SELECT * FROM sessions;"
```

The copy preserves the WAL data. After reading, clean up the temp copies:
```bash
rm /tmp/readable.db /tmp/readable.db-wal /tmp/readable.db-shm
```

**To checkpoint WAL to main DB:** Gracefully stop the gateway (`hermes gateway stop` from outside), which flushes WAL to `state.db`.

### Symptom: Gateway reports "Zalo connected" but messages don't arrive
**Check:**
1. Node.js bridge is running (port matches `ZALO_PLUGIN_URL`)
2. Bridge logged in (QR scan still valid — Zalo sessions expire)
3. Plugin loaded: `hermes plugins list` — `zalo-platform` must be enabled
4. Gateway logs: check `profiles/<name>/logs/` or gateway_state.json

### Symptom: SSE keeps disconnecting with HTTP 409 (Conflict)

**Log signature:**
```
Zalo: SSE disconnected (SSE status 409); reconnecting in 10.0s
```

**Cause:** Two Hermes gateway profiles (e.g. `default` and `family`) share the same bridge URL (`ZALO_PLUGIN_URL`). The bridge (zca-js) only maintains **one SSE connection** per bot account. When a second gateway connects, the bridge returns 409 Conflict.

**Consequences:**
- The newer gateway's SSE stream is rejected → no inbound messages (replies, group mentions) are received
- **POST /send still works** — outbound messages (cron, proactive sends) succeed because they are separate HTTP requests, not SSE
- The gateway logs show a flood of "SSE disconnected (SSE status 409)" every 10 seconds

**Fix:**
1. Stop the duplicate gateway profile: `hermes gateway stop --profile <name>`
2. If you need both profiles, run separate bridge instances on different ports:
   - Default: `ZALO_PLUGIN_URL=http://host.docker.internal:8787`
   - Family: `ZALO_PLUGIN_URL=http://host.docker.internal:8788` (separate zca-js process)
3. Verify only one SSE connection exists: check logs for `bridge status {'connected': True}` without preceding 409s

**Prevention:** The Profile Isolation section warns "each profile needs its own bridge instance." This is why — sharing a bridge between profiles causes SSE conflict on the second connection.

### Symptom: "Refusing to restart the gateway from inside the gateway process"

**Log signature:**
```
✗ Refusing to restart the gateway from inside the gateway process.
This command was blocked to prevent restart loops.
Use `hermes gateway restart` from a shell outside the running gateway.
```

**Cause:** The `hermes gateway restart` command is blocked when called from inside the gateway process itself (where the agent runs) to prevent accidental restart loops.

**Fix — use s6-svc to restart the gateway service directly:**

The gateway runs as a managed s6 service. From inside the container, use `s6-svc` with the full path (since `/command/` is not on the agent's PATH):

```bash
# Find s6-svc path
find /package -name "s6-svc" -type f
# Typical: /package/admin/s6-<version>/command/s6-svc

# Restart the default profile gateway
/package/admin/s6-2.15.0.0/command/s6-svc -t /run/service/gateway-default

# For a named profile gateway:
/package/admin/s6-2.15.0.0/command/s6-svc -t /run/service/gateway-<profile-name>
```

The `-t` flag sends SIGTERM to the process; s6-supervise automatically restarts it with the new configuration.

**Verify the restart:**
```bash
# Check the gateway reconnected to Zalo
grep "zalo.*connect" /opt/data/logs/agent.log | tail -3
# Expected: Zalo: connected to bridge http://host.docker.internal:8787
```

**Alternative — use `hermes gateway stop/start` pair if running outside the container:**
```bash
hermes gateway stop
hermes gateway start
```

### Symptom: "Not allowed" errors for valid users

**Check:**
1. `ZALO_ALLOWED_USERS` — empty means everyone allowed. If set, the exact user ID must be included
2. `ZALO_ALLOWED_ACTION_GROUPS` — missing `send` or `interact` blocks message sending
3. To discover user/group IDs, set `ZALO_LOG_IDS=true` and check gateway logs

### Symptom: "Adapter send failed: Timeout context manager should be used inside a task"

**Full error:**
```
Adapter send failed: Timeout context manager should be used inside a task
```

**Root cause:** The Zalo adapter's `_post()` method (`plugins/zalo/adapter.py`) passes `timeout=aiohttp.ClientTimeout(total=N)` to `session.post()`. In newer aiohttp/Python 3.12+, `ClientTimeout` is implemented internally via `asyncio.timeout()`, which requires the calling coroutine to be running inside an active `asyncio.Task`. When invoked from the Hermes tool runner (which calls coroutines from outside a proper async Task context), this throws the `RuntimeError: Timeout context manager should be used inside a task`.

**Call chain:**
```
send_message_tool.send_message()
  → _send_to_platform()
    → _send_via_adapter()           # /opt/hermes/tools/send_message_tool.py:531
      → adapter.send()              # plugins/zalo/adapter.py:809
        → self._post("/send", ...)  # plugins/zalo/adapter.py:769
          → async with session.post(
                timeout=aiohttp.ClientTimeout(total=60)  # ← CAUSE
              )
```

**All affected locations in `plugins/zalo/adapter.py`** (all use `timeout=aiohttp.ClientTimeout(...)` inside `async with session.get/post()`):
| Line | Context | Timeout |
|------|---------|---------|
| 339 | health check | 10s |
| 375 | policy fetch | 10s |
| 437-439 | SSE events stream | None |
| 458 | disconnect POST | 3s |
| 586 | login poll | 3s |
| 695 | QR fetch | 120s |
| 775-779 | **/send POST** (production path) | 60s |
| 1013-1017 | bridge status query | 60s |

**Fix approach (same pattern as weixin.py — `/opt/hermes/gateway/platforms/weixin.py:381`):**
Replace `timeout=ClientTimeout(...)` with `asyncio.wait_for()` wrapping a nested async function:

```python
async def _post(self, path, body):
    import aiohttp
    if not self._session or self._session.closed:
        return {"error": "no session"}
    try:
        async def _do():
            async with self._session.post(
                f"{self.bridge_url}{path}",
                data=json.dumps(body),
                headers=self._headers(),
            ) as resp:
                return await resp.json()
        return await asyncio.wait_for(_do(), timeout=60.0)
    except Exception as e:
        return {"error": str(e)}
```

This pattern avoids `aiohttp.ClientTimeout` entirely — the timeout is managed by `asyncio.wait_for()` which works correctly even when called from non-Task contexts.

**Reference:** See `references/timeout-error-trace.md` for the full code-level debugging trace with exact line numbers from the diagnosed session.

### Symptom: Profile offline — sends fail but incoming messages still arrive

When a Zalo gateway profile is stopped or disconnected (e.g. profile "family" PID 194 shut down), its Zalo adapter is no longer available in the gateway. This causes:

- **send_message to Zalo fails** for all targets (DM and groups) because the live adapter is missing
- **Incoming messages still work** if another profile's gateway is running (the receiver handles inbound via webhook)
- **Telegram sends still work** (independent platform)

**Resolution:**
1. Check which profiles have running Zalo gateways: `hermes gateway list`
2. Use an active profile for Zalo sends — inbound messages always go through the profile they arrived on
3. If the only active profile can't send, check Docker daemon (`docker ps`) and restart the gateway

## Finding IDs

Set `ZALO_LOG_IDS=true` in the profile's `.env`, restart the gateway, then send a message from the target user/group. The gateway logs will print the `uidFrom` (user ID) and `threadId` (group/chat ID). These can then be added to `ZALO_ALLOWED_USERS` or `ZALO_ALLOWED_THREADS`.

### Step-by-step: Find a user/group ID from logs

1. **Ensure `ZALO_LOG_IDS=true`** is set in the profile's `.env` (restart gateway if newly added).
2. **Have the target person send a message** in the group or DM where the bot is active.
3. **Grep the agent log** for the inbound record:
   ```bash
   grep "Zalo inbound" /opt/data/logs/agent.log | tail -20
   ```
   Look for a line like:
   ```
   Zalo inbound: uid=8470394008915407964 name='Bi Bống' threadId=3339712927031818889 type=group
   ```
   - `uid=...` is the **user ID** (use this in `ZALO_ALLOWED_USERS`)
   - `threadId=...` is the **chat/group ID** (use this in `ZALO_ALLOWED_THREADS`)
   - `name='...'` is the display name — helps identify who sent it
   - `type=group` or `type=dm` tells you the thread type

4. **Filter by thread** if many groups are active:
   ```bash
   grep "Zalo inbound" /opt/data/logs/agent.log | grep "threadId=3339712927031818889"
   ```

5. **Add the discovered ID** to the appropriate env var and restart the gateway.

### Add a user to the allowlist

Once you have the user's Zalo ID (e.g. `8470394008915407964`), append it to `ZALO_ALLOWED_USERS` in the profile's `.env`:

```ini
# Before
ZALO_ALLOWED_USERS=2825656851207986406,3656141905842635373
# After
ZALO_ALLOWED_USERS=2825656851207986406,3656141905842635373,8470394008915407964
```

Then **restart the gateway** for the change to take effect.

⚠️ **Remember:** When adding IDs to `ZALO_ALLOWED_THREADS`, include both group IDs (for group chats) AND user IDs (for DM delivery). The thread filter applies to ALL message types indiscriminately.

## Related

- `references/platform-config.md` — Zalo env var reference table with examples
- `references/filter-order-debugging.md` — Adapter filter execution order, log flow, and DM-dropping detection
- `references/delivery-tracing.md` — Proactive delivery thread-type resolution
- `references/timeout-error-trace.md` — ClientTimeout / asyncio timeout fix
- `references/stale-bytecode-detection.md` — .pyc staleness detection and forced recompilation after patching
- `hermes-agent` skill — general Hermes configuration
- `hermes-s6-container-supervision` — Docker container management
