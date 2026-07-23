# Debugging Hermes TUI Slash Commands

## Architecture (3 Layers)

```
Python backend (hermes_cli/commands.py) — COMMAND_REGISTRY (source of truth)
  → TUI gateway (tui_gateway/server.py) — slash.exec / command.dispatch
    → TUI frontend (ui-tui/src/app/slash/) — local handlers + fallthrough
```

## Investigation Steps

1. Check TUI frontend: `search_files --pattern "/commandname" --file_glob "*.ts*" --path ui-tui/`
2. Check Python backend: `search_files --pattern "CommandDef" --file_glob "*.py" --path hermes_cli/`
3. Check gateway: `search_files --pattern "slash.exec" --path tui_gateway/`

## Common Issues

| Symptom | Likely Cause |
|---------|-------------|
| Shows in TUI but not autocomplete | Missing from `COMMAND_REGISTRY` in Python |
| Shows in autocomplete but doesn't work | Missing handler in `tui_gateway/server.py` or frontend |
| CLI vs TUI behavior differs | Different implementations in `cli.py` vs TUI local handler |
| Config persists but UI doesn't update | Forgot to patch nanostore state in TUI |

## Fix: Add/Update Autocomplete

```python
CommandDef("commandname", "Description", "Session",
           cli_only=True, aliases=("alias",),
           args_hint="[arg1|arg2|arg3]", subcommands=("arg1", "arg2", "arg3")),
```

Always rebuild TUI after changes: `npm --prefix ui-tui run build`
