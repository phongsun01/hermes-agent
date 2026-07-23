# Zalo Delivery Flow Tracing (cron → bridge)

Full trace of how a cron job's message reaches the Zalo bridge, including the `threadType` resolution chain that causes the "nick #" bug.

## Entry point: cron scheduler

`deliver: "zalo:3339712927031818889"` → `_resolve_single_delivery_target()` in `cron/scheduler.py`:

```python
platform_name, rest = deliver_value.split(":", 1)  # "zalo" , "3339712927031818889"
```

Then `_parse_target_ref("zalo", "3339712927031818889")` from `tools/send_message_tool.py`:

- Zalo has **no special handler** in `_parse_target_ref`
- Falls through to the generic fallback at line 412:
  ```python
  if target_ref.lstrip("-").isdigit():
      return target_ref, None, True  # ("3339712927031818889", None, True)
  ```
- Returns `chat_id = "3339712927031818889"`, `thread_id = None`, `is_explicit = True`

## Adapter receive: `send()`

The adapter's `send()` method (`plugins/zalo/adapter.py` line 806):

```python
chat_id, inferred_type = self._clean_target(chat_id)
thread_type = inferred_type or self._thread_type_from_chat_id(chat_id, metadata)
```

## `_clean_target()` (line 785)

Parses optional prefix. If `chat_id` contains `:`, checks if the prefix is `"group"` or `"user"`:

```python
def _clean_target(self, chat_id: str) -> tuple[str, Optional[str]]:
    chat_id_str = str(chat_id)
    if ":" in chat_id_str:
        prefix, _, rest = chat_id_str.partition(":")
        prefix = prefix.strip().lower()
        if prefix in {"group", "user"}:
            return rest.strip(), prefix
    return chat_id_str, None
```

For `"3339712927031818889"` (no colon) → returns `("3339712927031818889", None)`.  
For `"group:3339712927031818889"` → returns `("3339712927031818889", "group")`.

## `_thread_type_from_chat_id()` (line 794) — THE BUG

```python
def _thread_type_from_chat_id(self, chat_id: str, metadata) -> str:
    chat_id, inferred_type = self._clean_target(chat_id)
    if inferred_type:
        return inferred_type
    if metadata and metadata.get("thread_type") in {"user", "group"}:
        return metadata["thread_type"]
    remembered = self._thread_types.get(str(chat_id))
    if remembered in {"user", "group"}:
        return remembered
    return "user"   # ← FALLBACK — causes nick # bug
```

**Resolution order:**
1. `_clean_target` prefix → most explicit, works with `"group:<id>"` format
2. `metadata.thread_type` → set by reply flows but NOT by cron delivery
3. `_thread_types` cache → populated from inbound messages + bridge `/groups` response at startup
4. **`"user"`** → default fallback when none of the above match

## Why proactive sends fail

- Inbound messages populate `_thread_types[str(thread_id)] = "group"` on receipt
- `_populate_group_types()` fires at startup, fetching `/groups` from the bridge
- But if the bridge session expired, `/groups` returns nothing, OR the group ID is different, OR `_populate_group_types` runs as a fire-and-forget task and fails silently → `_thread_types` lacks the group ID
- Cron delivery provides no `metadata.thread_type` because there's no source message to derive it from
- No prefix in `chat_id` → falls to `"user"`

## The fix

Add a check against `self._allowed_threads` (from `ZALO_ALLOWED_THREADS` env var) before the cache lookup:

```python
# In _thread_type_from_chatId(), right after the metadata check:
if str(chat_id) in self._allowed_threads:
    return "group"
```

`ZALO_ALLOWED_THREADS` is user-configurable and always includes known group IDs, so it's a reliable signal.

## Quick verification

```bash
# Test bridge is up and sending works
curl -X POST http://127.0.0.1:8787/send \
  -H "Content-Type: application/json" \
  -d '{"threadId": "<group_id>", "threadType": "group", "text": "test"}'

# Check gateway knows the group exists
curl http://127.0.0.1:8787/contacts | python3 -c "import sys,json; [print(g) for g in json.load(sys.stdin).get('groups',[])]"
```

## Related

- `zalo` skill SKILL.md — troubleshooting entry for this symptom
- `plugins/zalo/adapter.py` — the adapter code (lines ~785-804 for the relevant methods)
