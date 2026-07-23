# Zalo Adapter Filter Order — Debugging Reference

## Filter execution order in `_on_inbound_message()` (`plugins/zalo/adapter.py`)

```
[1] Thread allowlist check      (line 637) ← ZALO_ALLOWED_THREADS
[2] User allowlist check        (line 642) ← ZALO_ALLOWED_USERS
[3] Group mode check            (line 647) ← ZALO_GROUP_MODE
[4] → Build source → route to agent
```

**Critical detail:** Check [1] runs BEFORE check [2]. This means a user who IS in `ZALO_ALLOWED_USERS` can still have their DM silently dropped if `ZALO_ALLOWED_THREADS` is set and doesn't include their DM thread ID.

## How DM threadId works

When a user sends a DM to the bot:
- `threadId` = the user's own Zalo UID (e.g. `2825656851207986406`)
- `type` = `dm`
- This is the same value as the user's `sender_id`/`uidFrom`

So for DM, `threadId == sender_id`. This means adding the user's ID to `ZALO_ALLOWED_THREADS` is equivalent to adding their DM channel.

## Log flow for a silently-dropped DM

| Log source | Expected if working | Expected if dropped by thread filter |
|---|---|---|
| `agent.log` | `Zalo inbound: uid=... name='Xitrum' threadId=... type=dm` | ✅ Same |
| `agent.log` | `inbound message: platform=zalo user=Xitrum chat=...` | ❌ MISSING |
| `agent.log` | Agent session created & processes message | ❌ MISSING |
| `errors.log` | — | Nothing (logger.debug, not visible) |

## Detection command

```bash
# Find Zalo inbound logs (adapter level)
grep "Zalo inbound" /opt/data/logs/agent.log | grep -E "$(date '+%H:%M'|cut -c1-2)"

# Find corresponding gateway route logs
grep "inbound message: platform=zalo" /opt/data/logs/agent.log | grep -E "$(date '+%H:%M'|cut -c1-2)"

# If first grep returns messages but second doesn't → filter is dropping them
```

## Quick fix verification

```bash
# Before fix — check config
echo "ALLOWED_THREADS=$ZALO_ALLOWED_THREADS"
echo "ALLOWED_USERS=$ZALO_ALLOWED_USERS"

# After changing env, restart gateway is required
# Check agent.log for "inbound message: platform=zalo" appearing
```

## Real example from 2026-07-06

- `ZALO_ALLOWED_THREADS=3339712927031818889` (group "Bi bống house")
- `ZALO_ALLOWED_USERS=2825656851207986406,3656141905842635373` (Xitrum + chị Huế)
- Xitrum sends DM → adapter logs `Zalo inbound: uid=2825656851207986406 name='Xitrum' threadId=2825656851207986406 type=dm`
- Thread check fires: `2825656851207986406 not in {3339712927031818889}` → **DROP**
- No `inbound message: platform=zalo` ever generated
- Earlier gateway session (before restart) worked because env was different
