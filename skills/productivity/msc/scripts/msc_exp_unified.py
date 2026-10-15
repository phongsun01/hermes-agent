#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    ap = argparse.ArgumentParser(description="Unified /exp for PL or IB")
    ap.add_argument("--code", required=True, help="PL... or IB...")
    ap.add_argument("--token", default="")
    ap.add_argument("--cookie", default="")
    args = ap.parse_args()

    token = args.token or os.environ.get("MSC_SESSION_TOKEN") or os.environ.get("MSC_TOKEN") or ""
    cookie = args.cookie or os.environ.get("MSC_COOKIE") or ""
    code = (args.code or "").strip().upper()

    scripts_dir = Path(__file__).resolve().parent

    if re.fullmatch(r"PL\d{8,}", code):
        cmd = [
            "python3",
            str(scripts_dir / "msc_exp_khlcnt.py"),
            "--pl", code,
        ]
    elif re.fullmatch(r"IB\d{8,}", code):
        cmd = [
            "python3",
            str(scripts_dir / "msc_expt_tbmt.py"),
            "--ib", code,
        ]
    else:
        print(json.dumps({
            "status": "invalid_code",
            "message": "Usage: /exp PLxxxxxxxx hoặc /exp IBxxxxxxxx",
        }, ensure_ascii=False))
        return

    env = os.environ.copy()
    if token:
        env["MSC_SESSION_TOKEN"] = token
        env["MSC_TOKEN"] = token
    if cookie:
        env["MSC_COOKIE"] = cookie

    p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)
    out = (p.stdout or "").strip()
    if not out:
        print(json.dumps({"status": "error", "message": "empty_output"}, ensure_ascii=False))
        return
    print(out)


if __name__ == "__main__":
    main()
