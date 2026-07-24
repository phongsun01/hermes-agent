#!/usr/bin/env python3
import argparse
import json
import re
import subprocess


def main():
    import os
    from pathlib import Path
    ap = argparse.ArgumentParser(description="Unified /exp for PL or IB")
    ap.add_argument("--code", required=True, help="PL... or IB...")
    ap.add_argument("--token", default="", help="MSC API bearer token")
    ap.add_argument("--cookie", default="", help="MSC Cookie")
    args = ap.parse_args()

    token = args.token or os.environ.get("MSC_SESSION_TOKEN") or os.environ.get("MSC_BEARER_TOKEN") or ""
    cookie = args.cookie or os.environ.get("MSC_COOKIE") or ""

    # Try loading from .env if still empty (backward compatibility)
    if not token or not cookie:
        paths = [
            Path(__file__).parent / ".env",
            Path(__file__).parent.parent / ".env",
            Path.home() / ".hermes" / ".env",
        ]
        for p in paths:
            if p.exists():
                try:
                    for raw in p.read_text(encoding="utf-8").splitlines():
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        if k == "MSC_SESSION_TOKEN" and not token:
                            token = v.strip().strip('"').strip("'")
                        elif k == "MSC_COOKIE" and not cookie:
                            cookie = v.strip().strip('"').strip("'")
                except Exception:
                    pass

    if not token:
        print(json.dumps({"status": "error", "message": "Missing MSC API token. Configure in env or .env file."}, ensure_ascii=False))
        return

    # Set resolved values to env to propagate to subprocesses
    os.environ["MSC_SESSION_TOKEN"] = token
    if cookie:
        os.environ["MSC_COOKIE"] = cookie

    code = (args.code or "").strip().upper()
    SKILL_SCRIPTS_DIR = Path(__file__).parent

    if re.fullmatch(r"PL\d{8,}", code):
        cmd = [
            "python3",
            str(SKILL_SCRIPTS_DIR / "msc_exp_khlcnt.py"),
            "--pl", code,
        ]
    elif re.fullmatch(r"IB\d{8,}", code):
        cmd = [
            "python3",
            str(SKILL_SCRIPTS_DIR / "msc_expt_tbmt.py"),
            "--ib", code,
        ]
    else:
        print(json.dumps({
            "status": "invalid_code",
            "message": "Usage: /exp PLxxxxxxxx hoặc /exp IBxxxxxxxx",
        }, ensure_ascii=False))
        return

    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (p.stdout or "").strip()
    if not out:
        print(json.dumps({"status": "error", "message": "empty_output"}, ensure_ascii=False))
        return
    print(out)


if __name__ == "__main__":
    main()
