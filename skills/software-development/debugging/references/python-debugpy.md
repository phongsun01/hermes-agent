# Python Debugging (pdb + debugpy)

## Quick Reference

| Tool | When |
|------|------|
| `breakpoint()` + pdb | Local, interactive, simplest |
| `python -m pdb` | Launch under debugger with no source edits |
| `debugpy` | Remote/headless/attach to running process (DAP) |
| `remote-pdb` | Agent-friendly — `nc` to get (Pdb) prompt |

## pdb Quick Commands

- `n` — next line; `s` — step into; `c` — continue; `r` — return
- `l` / `ll` — list source / full function; `w` — stack trace
- `u` / `d` — move up/down in stack; `a` — current function args
- `interact` — full Python REPL in current scope (Ctrl+D to exit)
- `!stmt` — execute arbitrary Python (assignments, etc.)
- `q` — quit

## Pitfalls

- **pdb under pytest-xdist silently hangs** — use `-p no:xdist` or `-n 0`
- `breakpoint()` in CI hangs the process — pre-commit grep to catch
- `PYTHONBREAKPOINT=0` disables all breakpoint() calls
- `scripts/run_tests.sh` strips credentials — debug with raw pytest first
- pdb does not follow forks — each child needs its own breakpoint()
