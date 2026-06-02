# Changelog

## [Unreleased] — Zalo Platform Integration

### Added
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
| `Dockerfile` | CRLF fix, Zalo worker npm install |
| `.gitattributes` | Force LF for docker/ scripts |
| `gateway/platforms/zalo.py` | Python adapter with access control |
| `gateway/platforms/zalo/worker/src/index.ts` | Worker with AC, message unwrapping, QR fallback |
| `gateway/platforms/zalo/worker/src/credentials.ts` | HERMES_HOME-aware credential paths |
| `gateway/platforms/zalo/worker/src/access-control.ts` | Access control module (new) |
| `gateway/platforms/zalo/worker/src/actions.ts` | User/group info actions with caching |
| `gateway/config.py` | Platform.ZALO enum member |
| `gateway/run.py` | Zalo adapter registration |
