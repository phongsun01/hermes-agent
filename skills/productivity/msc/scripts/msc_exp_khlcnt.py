#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

DETAIL_SCRIPT = str(Path(__file__).parent / "msc_khlcnt_detail.py")


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
    if token:
        os.environ["MSC_SESSION_TOKEN"] = token
    if cookie:
        os.environ["MSC_COOKIE"] = cookie
    cmd = ["python3", DETAIL_SCRIPT, "--pl", pl]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    raw = (p.stdout or "").strip()
    try:
        return json.loads(raw) if raw else {"status": "error", "message": "empty_output"}
    except Exception:
        return {"status": "error", "message": "invalid_json", "raw": raw[:500]}


def main():
    ap = argparse.ArgumentParser(description="Export KHLCNT by PL to markdown")
    ap.add_argument("--pl", required=True)
    ap.add_argument("--token", default="", help="MSC API bearer token")
    ap.add_argument("--cookie", default="", help="MSC Cookie")
    ap.add_argument("--out-root", default=str(Path(__file__).parent.parent / "reports/msc/khlcnt"))
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

    pl = (args.pl or "").strip().upper()
    if not valid_pl(pl):
        print(json.dumps({"status": "invalid_pl", "message": "Usage: /exp PLxxxxxxxx"}, ensure_ascii=False))
        return

    detail = run_detail(pl, token, cookie=cookie)
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
