# Zalo Platform Configuration Reference

## Environment Variable Reference

### ZALO_GROUP_MODE

Controls bot behavior in Zalo group chats.

| Value | Behavior | Use Case |
|-------|----------|----------|
| `off` | Bot never responds in groups (DM only) | Personal assistant |
| `mention` | Bot responds only when @mentioned or replied-to | Family/team assistant |
| `all` | Bot responds to every message in allowed groups | Announcement bot |

**Default if unset:** `mention`

### ZALO_ALLOWED_THREADS

Comma-separated thread/group IDs the bot operates in.

- **Empty** (unset or blank): Bot works in every group and DM
- **Set to one or more IDs**: Bot only processes messages from those threads
- Format: bare threadId (e.g. `3339712927031818889`)

### ZALO_ALLOWED_USERS

Comma-separated Zalo user IDs (uidFrom) allowed to talk to the bot.

- **Empty** (unset or blank): Everyone allowed (Telegram-style)
- **Set to one or more IDs**: Only those users can interact

### ZALO_HOME_CHANNEL

Default delivery channel for cron job output and notifications.

- Format: `<threadId>` (user or group thread ID)
- Example: `2825656851207986406` (user DM) or `3339712927031818889` (group)
- When set to a group ID, cron deliveries go to that group
- When set to a user ID, deliveries go to that DM

## Profile Structure Example

Standard Hermes profile for a Zalo-connected bot:

```
/opt/data/profiles/<name>/
├── .env                        # Zalo + other env vars
├── config.yaml                 # Profile config
├── SOUL.md                     # Bot persona & instructions
├── state.db + state.db-wal     # Session store (locked while gateway runs)
├── memories/
│   ├── MEMORY.md               # Agent persistent notes
│   └── USER.md                 # User profile info
├── plugins/zalo/               # Profile-local plugin (optional)
├── cron/                       # Per-profile cron jobs
└── logs/                       # Per-profile gateway logs
```

## Data Flow: RAM → Disk

```
User message → Gateway → Agent (in RAM)
  └── Session data written to state.db-wal (locked)
  └── Memory tool writes to MEMORY.md (immediate flush)
  └── On gateway stop/restart → WAL checkpoint → state.db
```

**Key implication:** If the bot saves information using conversation context alone (without calling the `memory` tool), that data exists only in the WAL file and the running process. A clean gateway restart checkpoints the WAL to `state.db`. A crash loses uncheckpointed data.

## Discovery Workflow

To find user/group IDs:

1. Set `ZALO_LOG_IDS=true` in the profile's `.env`
2. Restart the gateway
3. Have the target user send a message in the target group/DM
4. Check gateway logs for logged uidFrom + threadId
5. Add the IDs to `ZALO_ALLOWED_USERS` / `ZALO_ALLOWED_THREADS`
6. Remove or set `ZALO_LOG_IDS=false` when done

## Working with Multiple Profiles

When running multiple Hermes profiles that each connect to Zalo:

1. Each profile needs its own `.env` with separate Zalo config
2. Each profile may need its own Node.js bridge instance (separate port)
3. Profiles are fully isolated — config, sessions, memories, plugins are independent
4. Use `hermes gateway list` to see all running profile gateways
5. Use `hermes gateway stop` from outside to restart a specific profile's gateway

Example: Two profiles on the same machine:
- **default**: `ZALO_PLUGIN_URL=http://host.docker.internal:8787`, DM only
- **family**: `ZALO_PLUGIN_URL=http://host.docker.internal:8787`, group mode `mention`

Both can share the same bridge (port 8787) if they use the same Zalo account.
