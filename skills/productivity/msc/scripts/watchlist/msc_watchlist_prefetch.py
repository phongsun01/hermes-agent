#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent.parent  # scripts/watchlist/prefetch.py -> msc/
SCRIPTS_DIR = SKILL_ROOT / 'scripts/watchlist'

TASKS = [
    ["python3", str(SCRIPTS_DIR / "msc_watchlist_export.py")],
    ["python3", str(SCRIPTS_DIR / "msc_watchlist_latest_tbmt.py"), "-n", "100"],
]


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return {
        "cmd": " ".join(cmd),
        "ok": p.returncode == 0,
        "returncode": p.returncode,
        "stdout_preview": (p.stdout or "")[:300],
        "stderr_preview": (p.stderr or "")[:300],
    }


def main():
    results = [run(c) for c in TASKS]
    ok = all(r["ok"] for r in results)
    out = {
        "ok": ok,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
        "note": "Prefetch only: warms watchlist/API paths before publish jobs.",
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
