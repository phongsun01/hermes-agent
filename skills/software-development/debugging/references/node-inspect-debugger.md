# Node.js Inspect Debugger

## Two Tools

| Tool | When |
|------|------|
| `node inspect` | Built-in, zero install, CLI REPL — prefer first |
| `chrome-remote-interface` | Scriptable from Node/Python for automation |

## Quick Reference — `node inspect`

Launch paused: `node --inspect-brk script.js`
Attach to running: `kill -SIGUSR1 <pid>` then `node inspect -p <pid>`

| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `bt` | backtrace (call stack) |
| `sb('file.js', 42)` | set breakpoint |
| `repl` | REPL in current scope |
| `watch('expr')` | watch expression |

## Debugging Hermes TUI

1. `hermes --tui &`
2. `kill -SIGUSR1 $(pgrep -f 'ui-tui/dist/entry')`
3. `node inspect ws://127.0.0.1:9229/<uuid>`

## Pitfalls

- Wrong line numbers in TypeScript sourcemaps — break in `dist/*.js`
- `--inspect` vs `--inspect-brk` — use `-brk` when you need to set breakpoints before code runs
- Port 9229 collisions — use `--inspect=0` for random port
- Child processes need their own `--inspect`
