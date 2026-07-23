# Stale .pyc Bytecode — Detection After Patching adapter.py

## The Problem

After editing `plugins/zalo/adapter.py`, the gateway may continue running the **old** compiled bytecode from `__pycache__/adapter.cpython-313.pyc` instead of the new `.py` source.

This happens when:
1. The `.py` modification time is too close to the `.pyc` — Python's `py_compile` uses mtime to decide if recompilation is needed, and coarse filesystem resolution (e.g., Docker overlay, WSL 9p mount) can miscompare timestamps.
2. The gateway restart only reloads the plugin into memory — if the .pyc is present and "looks fresh enough", Python skips recompilation.

## Detection Methods

### 1. Compare mtimes

```bash
stat /opt/data/plugins/zalo/adapter.py
stat /opt/data/plugins/zalo/__pycache__/adapter.cpython-313.pyc
```

If `.pyc` mtime is **older than** `.py` mtime → stale. But if they're identical (or very close), you can't tell from mtime alone.

### 2. Check bytecode for your patch string

```bash
strings /opt/data/plugins/zalo/__pycache__/adapter.cpython-313.pyc | grep "is_allowed_user_dm"
```

If your patch introduced a unique string (function name, variable name, comment), `strings` can confirm it's in the compiled bytecode:
- **Found** → the .pyc contains your patch → good
- **Not found** → the .pyc is stale (or your string was optimised away by the compiler)

### 3. Verify at runtime — grep agent.log for the new behaviour

```bash
grep "Zalo inbound" /opt/data/logs/agent.log | tail -3
grep "inbound message: platform=zalo" /opt/data/logs/agent.log | tail -3
```

If messages appear in the first grep but not the second, the filter is still dropping them — the running code may still be the old version.

## Forcing Recompilation

### Option A — Delete the .pyc (most reliable)

```bash
rm -rf /opt/data/plugins/zalo/__pycache__/
```

Python will recreate the .pyc fresh from the .py source on the next import. Works regardless of mtime resolution.

### Option B — Touch the .py file

```bash
touch /opt/data/plugins/zalo/adapter.py
```

Updates the mtime to `now`, ensuring it's newer than any cached .pyc.

### Option C — Bump the minor version of the .py

Add or modify a unique comment string at the top of `adapter.py` that forces Python to see the file as changed (e.g., `# v2` → `# v3`). Python's import machinery compares the entire source hash in some cases.

## Recommended workflow after any adapter patch

```bash
# 1. Delete bytecode cache
rm -rf /opt/data/plugins/zalo/__pycache__/

# 2. Restart gateway
hermes gateway restart  # or via s6

# 3. Verify the new bytecode was compiled
ls -la /opt/data/plugins/zalo/__pycache__/adapter.cpython-313.pyc
strings /opt/data/plugins/zalo/__pycache__/adapter.cpython-313.pyc | grep "your_patch_marker"

# 4. Send a test message and check agent.log
grep "Zalo inbound" /opt/data/logs/agent.log | tail -1
grep "inbound message: platform=zalo" /opt/data/logs/agent.log | tail -1
```
