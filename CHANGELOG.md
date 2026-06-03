# Changelog

## [Unreleased] — Zalo Platform Integration

### Added (Phase 5: Advanced Features — 2026-06-03)
- **`send_message` tool support** — Zalo integrated into cross-platform messaging tool; agent can proactively send messages to Zalo from any platform
- **Cron delivery** — Scheduled jobs can deliver results to Zalo via `send_message` tool
- **Platform hints** — Added "zalo" entry to `PLATFORM_HINTS` in `agent/prompt_builder.py`; agent understands Zalo capabilities (markdown, MEDIA: syntax, image URLs, 2000-char limit)
- **Rate limiter** — `RateLimiter` class in worker enforces 1 msg/sec with exponential backoff on consecutive errors; configurable via `ZALO_RATE_INTERVAL_MS` and `ZALO_RATE_MAX_BACKOFF_MS` env vars
- **Worker supervision** — `_supervise_worker()` async task auto-restarts crashed worker with exponential backoff (5s→300s cap), max 10 restarts before manual intervention required
- **Metrics tracking** — `get_metrics()` method exposes uptime, messages sent/received, error count, restart count, pending requests; `record_message_sent()` / `record_message_received()` for per-operation tracking
- **Rate limiter status IPC** — `get_rate_limiter_status` method for monitoring queue depth, backoff state, consecutive errors

### Added (Phase 2: Rich Messages & Media — 2026-06-02)
- **Media Handlers** — `send_image`, `send_file`, `send_video` actions in worker (URL + local path)
- **Message Formatting** — Markdown → Zalo HTML conversion (bold, italic, strikethrough, underline, code, links)
- **Auto-Truncate** — Messages > 2000 chars auto-truncated at word boundary
- **Received Media Caching** — Auto-detect and cache incoming media (image/file/video) with 1-hour TTL
- **Media Cache Management** — `cache_media`, `get_cached_media`, `cleanup_media_cache`, `clear_media_cache`
- **`cache_image_from_bytes()`** — Python adapter method for Hermes image caching integration
- **`send-typing` trigger** — Auto-trigger typing indicator before agent responds
- **Auto-echo image URLs** — Detect image URLs in inbound messages and echo before agent processing
- **New module** — `gateway/platforms/zalo/worker/src/media.ts` (formatting, caching, download, detection)
- **Full zaloclaw action dispatch (142 actions)** — All messaging, friends, groups, polls, reminders, conversations, settings, and profile actions wired to `zca-js` v2.1.2 API

### Added (Phase 1–4)
- **Zalo Platform Adapter** (`gateway/platforms/zalo.py`) — Python adapter using Node.js subprocess worker with JSON-RPC IPC
- **Zalo Worker** (`gateway/platforms/zalo/worker/`) — TypeScript worker using `zca-js` for Zalo API communication
- **QR Login** — Automatic QR code generation and session persistence at `~/.hermes/data/zaloclaw-credentials.json`
- **Access Control System** — DM policy (open/closed/allowlist/denylist), group policy, mention gating, per-user/per-group allowlists
- **User/Group Info Caching** — TTL-based cache (5 min) for `get-user-info`, `get-group-info`, `refresh-group-info` actions
- **Platform Registration** — `Platform.ZALO` added to gateway platform enum with auto-detection

### Fixed
- **Docker CRLF crash** — s6-overlay scripts failed on Windows due to CRLF line endings; fixed via `.gitattributes` (`eol=lf`) + Dockerfile `sed` step
- **Missing zca-js in Docker** — Added `npm install` step for `gateway/platforms/zalo/worker/` in Dockerfile
- **Credentials path in Docker** — Worker used `homedir()` which resolved incorrectly in container; now uses `HERMES_HOME` env var
- **Worker crash on connect** — `try` block was misplaced inside `_format_id_list` method instead of `connect()`
- **Message parsing** — zca-js wraps message payload in `msg.data`; worker now unwraps before extracting `uidFrom`, `dName`, `content`
- **Expired credentials fallback** — Worker now falls back to QR login when saved cookies expire instead of crashing
- **Access control env var passing** — Python adapter now explicitly passes `ZALO_DM_POLICY`, `ZALO_GROUP_POLICY`, `ZALO_ALLOWLISTED_USERS`, etc. to worker subprocess
- **Docker gateway startup loop** — Container CMD must be `hermes gateway` (not bare `hermes`) to run gateway mode; bare `hermes` starts interactive CLI which exits without terminal
- **TypeScript API signature mismatches** — Fixed 10+ `zca-js` v2.1.2 API call signatures in `actions.ts` (`deleteChat`, `addQuickMessage`, `updateArchivedChatList`, `deleteProductCatalog`, `getMute`, `getBizAccount`, `getFriendBoardList`, `updateCatalog`, `getListReminder`)

### Configuration
```yaml
# ~/.hermes/config.yaml
zalo:
  enabled: true
  extra:
    dm_policy: "allowlist"        # open | closed | allowlist | denylist
    group_policy: "closed"        # open | closed | allowlist | denylist
    require_mention: true         # require @mention in groups
    allowlisted_users: "2825656851207986406"  # comma-separated Zalo user IDs
    bot_name: "Your Bot Name"     # for mention detection
```

### Files Changed
| File | Description |
|------|-------------|
| `Dockerfile` | CRLF fix, Zalo worker npm install, gateway mode CMD |
| `.gitattributes` | Force LF for docker/ scripts |
| `gateway/platforms/zalo.py` | Python adapter with access control, media send, auto-echo, typing |
| `gateway/platforms/zalo/worker/src/index.ts` | Worker with AC, message unwrapping, QR fallback, media events |
| `gateway/platforms/zalo/worker/src/credentials.ts` | HERMES_HOME-aware credential paths |
| `gateway/platforms/zalo/worker/src/access-control.ts` | Access control module (new) |
| `gateway/platforms/zalo/worker/src/actions.ts` | Full 142-action dispatch with zca-js v2.1.2 signatures |
| `gateway/platforms/zalo/worker/src/media.ts` | Media formatting, caching, download, detection (new) |
| `gateway/config.py` | Platform.ZALO enum member |
| `gateway/run.py` | Zalo adapter registration |
| `docs/zalo-hermes-integration-plan.md` | Updated Phase 2 status with full action list |
| `docs/zaloclaw-progress-log.md` | Updated progress to 90% |
| `CHANGELOG.md` | This file |
