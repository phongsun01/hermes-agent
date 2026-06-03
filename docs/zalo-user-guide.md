# Zalo Platform — User Guide

Quick start guide for connecting Hermes Agent to Zalo via the Zalo Platform Adapter.

## Overview

The Zalo platform adapter uses a **Node.js subprocess worker** that communicates with Hermes via JSON-RPC over stdio. The worker uses `zca-js` to connect to Zalo's API.

**Features:**
- Text messages with markdown formatting (bold, italic, strikethrough, underline, code)
- Media support: images, files, videos
- Group message handling with mention gating
- Access control: allowlist/denylist for users and groups
- Auto cookie refresh to prevent session expiry
- Rate limiting to prevent account bans
- 142 Zalo API actions (messaging, friends, groups, polls, reminders, etc.)

## Prerequisites

- **Node.js ≥ 22** — required by `zca-js`
- **Hermes Agent** — installed and configured
- **Zalo account** — the account that will act as the bot

## Quick Setup

### 1. Install Dependencies

```bash
cd gateway/platforms/zalo/worker
npm install
npm run build
```

### 2. Enable Zalo Platform

In Hermes gateway mode, Zalo is auto-detected if the worker is built. No extra config needed for basic usage.

### 3. Start Gateway

```bash
hermes gateway
```

On first start, you'll see:
```
[Zalo] 🔑 No credentials found, please scan QR code.
[Zalo] QR code saved to ~/.hermes/data/zalo_qr.png. Please scan to login.
```

### 4. Scan QR Code

1. Open Zalo on your phone
2. Go to Settings → Scan QR
3. Scan the QR code saved at `~/.hermes/data/zalo_qr.png`
4. Wait for "✅ QR Login successful!" message

The session is persisted automatically. Subsequent restarts will use saved credentials.

## Configuration

### Basic Config (`~/.hermes/config.yaml`)

```yaml
zalo:
  enabled: true
  extra:
    dm_policy: "open"           # open | closed | allowlist | denylist
    group_policy: "open"        # open | closed | allowlist | denylist
    require_mention: false      # require @mention in groups
    allowlisted_users: ""       # comma-separated Zalo user IDs
    denylisted_users: ""        # comma-separated Zalo user IDs
    allowlisted_groups: ""      # comma-separated Zalo group IDs
    denylisted_groups: ""       # comma-separated Zalo group IDs
    bot_name: "MyBot"           # for mention detection
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZALO_DM_POLICY` | `open` | DM access policy |
| `ZALO_GROUP_POLICY` | `open` | Group access policy |
| `ZALO_REQUIRE_MENTION` | `false` | Require @mention in groups |
| `ZALO_ALLOWLISTED_USERS` | `""` | Comma-separated user IDs |
| `ZALO_DENYLISTED_USERS` | `""` | Comma-separated user IDs |
| `ZALO_ALLOWLISTED_GROUPS` | `""` | Comma-separated group IDs |
| `ZALO_DENYLISTED_GROUPS` | `""` | Comma-separated group IDs |
| `ZALO_BOT_NAME` | `null` | Bot name for mention detection |
| `ZALO_BOT_USER_ID` | `null` | Bot user ID for mention detection |
| `ZALO_MENTION_PATTERNS` | `[]` | JSON array of regex patterns |
| `ZALO_COOKIE_SAVE_INTERVAL_MS` | `1800000` | Cookie auto-save interval (30 min) |
| `ZALO_SESSION_CHECK_INTERVAL_MS` | `3600000` | Session health check interval (60 min) |
| `ZALO_RATE_INTERVAL_MS` | `1000` | Minimum interval between messages (1 sec) |
| `ZALO_RATE_MAX_BACKOFF_MS` | `30000` | Max backoff delay on errors (30 sec) |

### Access Control Policies

**DM Policy:**
- `open` — anyone can DM the bot (default)
- `closed` — no DMs allowed
- `allowlist` — only listed users can DM
- `denylist` — listed users cannot DM

**Group Policy:**
- `open` — bot responds in all groups (default)
- `closed` — bot ignores all groups
- `allowlist` — bot only responds in listed groups
- `denylist` — bot ignores listed groups

**Mention Gating:**
When `require_mention: true`, the bot only responds in groups when mentioned. Mentions are detected by:
- Bot name in message (case-insensitive): `@MyBot` or `MyBot`
- Bot user ID in message
- `[mention:USER_ID:Name]` tag format
- Custom regex patterns via `ZALO_MENTION_PATTERNS`

## Session Management

### Cookie Auto-Refresh

The worker automatically saves refreshed cookies every 5 minutes. This prevents session expiry during normal operation. When the worker restarts, it uses the latest saved cookies.

### Session Health Monitoring

Every 10 minutes, the worker checks if the session is still valid. If it detects authentication failures:

1. **1-2 failures**: Warning alert sent to Hermes logs
2. **3+ consecutive failures**: Critical alert + automatic QR re-login triggered

### Manual QR Re-Login

If you need to manually trigger QR re-login:

```bash
# Via IPC (if you have a running gateway)
# The adapter exposes trigger_qr_login() method
```

Or simply delete the credentials file and restart:

```bash
rm ~/.hermes/data/zaloclaw-credentials.json
hermes gateway
```

## Rate Limiting

The worker enforces a minimum interval between outbound messages to prevent Zalo account bans:

- **Default**: 1 message per second
- **Exponential backoff**: On consecutive errors, delay doubles (1s → 2s → 4s → ... → 30s cap)
- **Configurable**: Via `ZALO_RATE_INTERVAL_MS` and `ZALO_RATE_MAX_BACKOFF_MS`

## send_message Tool

The agent can proactively send messages to Zalo from any platform:

```
send_message(target="zalo", message="Hello from Hermes!")
send_message(target="zalo:chat_id", message="Direct message")
```

Media delivery is supported via `MEDIA:/path/to/file` syntax.

## Cron Delivery

Scheduled cron jobs can deliver results to Zalo:

```bash
hermes cron add --schedule "every 1h" --target "zalo" --prompt "Check system status"
```

## Troubleshooting

### Worker not starting

```
[Zalo] Worker script not found at ... Did you run 'npm run build'?
```

**Fix:**
```bash
cd gateway/platforms/zalo/worker
npm install
npm run build
```

### Session expired

```
[Zalo Session] CRITICAL: Zalo session expired. QR re-login required.
```

**Fix:** The worker will automatically trigger QR re-login. Scan the new QR code.

### Rate limit warnings

```
[RateLimiter] Backoff: 2000ms (consecutive errors: 2)
```

**Fix:** This is normal. The worker is backing off to avoid bans. If persistent, increase `ZALO_RATE_INTERVAL_MS`.

### Worker crash loop

```
[Zalo] Worker died with exit code 1
[Zalo] Restarting worker in 5s (attempt 1/10)
```

**Fix:** Check stderr logs for the actual error. Common causes:
- Node.js version < 22
- Missing `zca-js` dependency
- Invalid credentials file

### Messages not received in groups

**Check:**
1. `group_policy` is not `closed`
2. If `require_mention: true`, ensure you're mentioning the bot
3. Bot user ID is correctly set in `ZALO_BOT_USER_ID`

## Metrics

The adapter tracks:
- Messages sent/received
- Error count
- Restart count
- Uptime
- Pending requests

Access via `adapter.get_metrics()` in Python or check gateway logs.

## File Structure

```
gateway/platforms/zalo/
├── __init__.py
├── adapter.py              # Python adapter (not used, see zalo.py)
├── worker/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── index.ts        # Worker entry + IPC loop
│   │   ├── client.ts       # zca-js wrapper + session management
│   │   ├── credentials.ts  # Credential storage
│   │   ├── actions.ts      # 142 Zalo API actions + rate limiter
│   │   ├── access-control.ts # DM/group policy, mention gating
│   │   ├── media.ts        # Media handling, caching, formatting
│   │   ├── ipc.ts          # IPC protocol types
│   │   └── __tests__/
│   │       └── rate-limiter.test.ts
│   └── dist/               # Compiled JS (gitignored)
└── README.md

gateway/platforms/zalo.py   # Main Python adapter
```
