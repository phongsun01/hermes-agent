---
name: debugging
description: "Python and Node.js debuggers + systematic root-cause methodology. Use breakpoint-driven debugging (pdb, node inspect, debugpy) before attempting fixes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, python, nodejs, pdb, debugpy, node-inspect, root-cause, troubleshooting]
    related_skills: [test-driven-development]
---

# Debugging Tools & Methodology

Consolidated debugging resource covering Python debuggers (pdb, debugpy), Node.js debugger (node inspect), and systematic root-cause investigation methodology.

## Core Principle

ALWAYS find root cause before attempting fixes. Symptom fixes are failure. The Iron Law: **No fixes without root cause investigation first.**

## Available Modules

### Python Debugging (`references/python-debugpy.md`)
- `breakpoint()` + pdb — simplest, add inline and run
- `python -m pdb` — launch script under debugger with no source edits
- `debugpy` — remote/headless/attach to running process via DAP protocol

### Node.js Debugging (`references/node-inspect-debugger.md`)
- `node inspect` — built-in CLI debugger, zero install
- CDP via `chrome-remote-interface` — scriptable from Node/Python

### Hermes TUI Debugging (`references/debugging-hermes-tui-commands.md`)
Debug slash commands in Hermes TUI spanning three layers: Python command registry, tui_gateway JSON-RPC bridge, and Ink/TypeScript frontend.

### Systematic Debugging Methodology (`references/systematic-debugging.md`)
4-phase root cause debugging process: Phase 1 (Root Cause Investigation), Phase 2 (Hypothesis), Phase 3 (Fix), Phase 4 (Verify). Must complete each phase before proceeding.

## Decision Flow

1. **Test failure with traceback** → Check `pytest -vv --tb=long --showlocals` first
2. **Simple Python bug** → `breakpoint()` + pdb (cheapest thing that works)
3. **Need step-through in Python** → `python -m pdb` or `debugpy`
4. **Node.js bug** → `node inspect` built-in debugger
5. **Hermes TUI slash command issue** → Debugging Hermes TUI Commands reference
6. **Cannot reproduce or complex bug** → Systematic Debugging methodology

## Rules

1. Start with the simplest tool that could work (breakpoint() over debugpy over systematic)
2. Always reproduce consistently before attempting any fix
3. Read error messages carefully — they often contain the exact solution
4. Complete root cause analysis before proposing any fix
