# Timeout Context Manager Error — Full Debugging Trace

> **Session:** 2026-07-05, Hermes Agent (default profile)
> **Symptom:** `Adapter send failed: Timeout context manager should be used inside a task` when calling `send_message` to Zalo (both DM and group)

## Error Signature

```
send_message(target="zalo:3339712927031818889", ...)
  → {"error": "Adapter send failed: Timeout context manager should be used inside a task"}
```

Also reproduced with bare `zalo` (home channel) target — same error, ruling out group-specific issues.

## Code Path

### 1. Entry point — `/opt/hermes/tools/send_message_tool.py`

`send_message_tool()` (line 158) → `_send_to_platform()` (line 583) → `_send_via_adapter()` (line 488)

```python
# send_message_tool.py:531
result = await adapter.send(chat_id=chat_id, content=chunk, metadata=metadata)
```

When exception caught at line 534:
```python
except Exception as e:
    return {"error": f"Plugin platform send failed: {e}"}
```

Wait — the error message says "Adapter send failed:", not "Plugin platform send failed:". Let me re-check...

Actually looking more carefully:
```python
# line 536-538
if result.success:
    return {"success": True, "message_id": result.message_id}
return {"error": f"Adapter send failed: {result.error}"}
```

So `adapter.send()` returned a `SendResult` with `success=False` and `error="Timeout context manager should be used inside a task"`. This means the exception was caught INSIDE the adapter's `_post` method (line 782-783):

```python
except Exception as e:
    return {"error": str(e)}
```

### 2. The adapter — `/opt/data/plugins/zalo/adapter.py`

**`send()` (line 809):** Splits long messages into chunks, calls `_post("/send", ...)` for each.

```python
async def send(self, chat_id, content, reply_to=None, metadata=None):
    chunks = self.truncate_message(content, max_length=self.max_message_length)
    for chunk in chunks:
        res = await self._post("/send", {"threadId": chat_id, "threadType": thread_type, "text": chunk})
        if res.get("error"):
            return SendResult(success=False, error=res["error"])
```

**`_post()` (line 769):** The culprit.

```python
async def _post(self, path, body):
    import aiohttp
    if not self._session or self._session.closed:
        return {"error": "no session"}
    try:
        async with self._session.post(
            f"{self.bridge_url}{path}",
            data=json.dumps(body),
            headers=self._headers(),
            timeout=aiohttp.ClientTimeout(total=60),  # ← CAUSE
        ) as resp:
            return await resp.json()
    except Exception as e:
        return {"error": str(e)}  # ← Error surfaces here as "Timeout context manager..."
```

### 3. Why it fails — Python async internals

In **Python 3.11+**, aiohttp's `ClientTimeout` uses `asyncio.timeout()` internally. `asyncio.timeout()` calls `asyncio.get_running_loop().timeout()`, which requires a **current running Task** in the event loop.

When the Hermes tool runner invokes an async tool, it uses `asyncio.run_coroutine_threadsafe()` or similar — this schedules the coroutine on the event loop but NOT as a proper `asyncio.Task`. The coroutine runs in a bare context, so `asyncio.timeout()` raises:

```
RuntimeError: Timeout context manager should be used inside a task
```

## Environment

| Component | Detail |
|-----------|--------|
| Hermes Agent | Docker container (s6-overlay supervision) |
| Platform | Zalo via `zalo-platform` plugin |
| Plugin path | `/opt/data/plugins/zalo/adapter.py` |
| Bridge | hermes-zalo-plugin (Node.js, port 8787, zca-js) |
| aiohttp | Version using `asyncio.timeout()` internally |

## Comparison: Same bug in weixin.py

`/opt/hermes/gateway/platforms/weixin.py` had the identical issue and was fixed with this pattern:

```python
# weixin.py:381-390
# Use asyncio.wait_for() instead of aiohttp ClientTimeout to avoid
# "Timeout context manager should be used inside a task" errors when
# invoked via asyncio.run_coroutine_threadsafe() from cron jobs.
async def _do() -> Dict[str, Any]:
    async with session.post(url, data=body, headers=_headers(token, body)) as response:
        raw = await response.text()
        ...
        return json.loads(raw)
return await asyncio.wait_for(_do(), timeout=timeout_ms / 1000)
```

## All Affected Lines in adapter.py

| Line | Method | Current code | Fix needed (replace timeout= with asyncio.wait_for) |
|------|--------|-------------|------------------------------------------------------|
| 338-339 | start() health check | `session.get(url, timeout=ClientTimeout(total=10))` | Yes — called from adapter `start()` |
| 374-375 | start() policy check | `session.get(url, timeout=ClientTimeout(total=10))` | Yes — called from adapter `start()` |
| 437-439 | SSE connect | `session.get(url, headers=headers, timeout=ClientTimeout(total=None, sock_read=None))` | Yes — but `total=None` means infinite; `sock_read=None` also means no timeout. Mitigated because SSE has its own reconnection |
| 458 | disconnect POST | `session.post(url, timeout=ClientTimeout(total=3))` | Yes — but short timeout means retry is tolerable |
| 584-586 | login poll GET | `session.get(url, timeout=ClientTimeout(total=3))` | Yes — short timeout, retry loop exists |
| 694-695 | QR fetch | `session.get(url, timeout=ClientTimeout(total=120))` | Yes — long timeout reduces retry frequency |
| 775-779 | **/_post() /send** | `session.post(url, timeout=ClientTimeout(total=60))` | **Production path — highest priority** |
| 1013-1017 | bridge status | `session.get(url, timeout=ClientTimeout(total=60))` | Yes — error recovery path |
