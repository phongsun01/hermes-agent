#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

DETAIL_SCRIPT = "scripts/msc_khlcnt_detail.py"


def valid_pl(s: str) -> bool:
    return re.fullmatch(r"PL\d{8,}", (s or "").strip().upper()) is not None


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def safe_filename(pl: str, payload: dict) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = f"{pl}__{ts}"
    h = hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"{base}__{h}.md"


def run_detail(pl: str, token: str, cookie: str = "") -> dict:
    cmd = ["python3", DETAIL_SCRIPT, "--pl", pl, "--token", token]
    if cookie:
        cmd += ["--cookie", cookie]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    raw = (p.stdout or "").strip()
    try:
        return json.loads(raw) if raw else {"status": "error", "message": "empty_output"}
    except Exception:
        return {"status": "error", "message": "invalid_json", "raw": raw[:500]}


def main():
    ap = argparse.ArgumentParser(description="Export KHLCNT by PL to markdown")
    ap.add_argument("--pl", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--cookie", default="")
    ap.add_argument("--out-root", default=str(Path(__file__).parent.parent / "reports/msc/khlcnt"))
    args = ap.parse_args()

    pl = (args.pl or "").strip().upper()
    if not valid_pl(pl):
        print(json.dumps({"status": "invalid_pl", "message": "Usage: /exp PLxxxxxxxx"}, ensure_ascii=False))
        return

    detail = run_detail(pl, args.token, cookie=args.cookie)
    st = detail.get("status")

    if st in ("invalid_pl", "not_found", "login_error"):
        print(json.dumps(detail, ensure_ascii=False))
        return

    general = detail.get("general") or {}
    packages = detail.get("packages") or []

    # render md
    from msc_khlcnt_md import render_markdown

    now = datetime.now()
    out_dir = os.path.join(args.out_root, now.strftime("%Y"), now.strftime("%m"))
    ensure_dir(out_dir)
    fname = safe_filename(pl, detail)
    fpath = os.path.join(out_dir, fname)

    md = render_markdown(
        pl=pl,
        general=general,
        packages=packages,
        source=detail.get("source") or {},
        status=st,
    )

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(md)

    print(json.dumps({
        "status": st if st else "ok",
        "pl": pl,
        "file": fpath,
        "message": detail.get("message") or "exported",
        "general_fields": len(general),
        "package_count": len(packages),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
