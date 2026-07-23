#!/usr/bin/env python3
import argparse
import json
import re
import subprocess


def main():
    ap = argparse.ArgumentParser(description="Unified /exp for PL or IB")
    ap.add_argument("--code", required=True, help="PL... or IB...")
    ap.add_argument("--token", required=True)
    ap.add_argument("--cookie", default="")
    args = ap.parse_args()

    code = (args.code or "").strip().upper()

    if re.fullmatch(r"PL\d{8,}", code):
        cmd = [
            "python3",
            "scripts/msc_exp_khlcnt.py",
            "--pl", code,
            "--token", args.token,
        ]
        if args.cookie:
            cmd += ["--cookie", args.cookie]
    elif re.fullmatch(r"IB\d{8,}", code):
        cmd = [
            "python3",
            "scripts/msc_expt_tbmt.py",
            "--ib", code,
            "--token", args.token,
        ]
        if args.cookie:
            cmd += ["--cookie", args.cookie]
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
