#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

DETAIL_SCRIPT = "scripts/msc_tbmt_detail.py"


def valid_ib(s: str) -> bool:
    return re.fullmatch(r"IB\d{8,}", (s or "").strip().upper()) is not None


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def safe_filename(ib: str, payload: dict) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = f"{ib}__{ts}"
    h = hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"{base}__{h}.md"


def run_detail(ib: str, token: str, cookie: str = "") -> dict:
    cmd = ["python3", DETAIL_SCRIPT, "--ib", ib, "--token", token]
    if cookie:
        cmd += ["--cookie", cookie]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    raw = (p.stdout or "").strip()
    try:
        return json.loads(raw) if raw else {"status": "error", "message": "empty_output"}
    except Exception:
        return {"status": "error", "message": "invalid_json", "raw": raw[:500]}


def main():
    ap = argparse.ArgumentParser(description="Export TBMT by IB to markdown (v3)")
    ap.add_argument("--ib", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--cookie", default="")
    ap.add_argument("--out-root", default=str(Path(__file__).parent.parent / "reports/msc/tbmt"))
    args = ap.parse_args()

    ib = (args.ib or "").strip().upper()
    if not valid_ib(ib):
        print(json.dumps({"status": "invalid_ib", "message": "Usage: /expt IBxxxxxxxx"}, ensure_ascii=False))
        return

    detail = run_detail(ib, args.token, cookie=args.cookie)
    st = detail.get("status")

    if st in ("invalid_ib", "not_found", "login_error"):
        print(json.dumps(detail, ensure_ascii=False))
        return

    tabs = detail.get("tabs") or {}

    from msc_tbmt_md import render_markdown

    now = datetime.now()
    out_dir = os.path.join(args.out_root, now.strftime("%Y"), now.strftime("%m"))
    ensure_dir(out_dir)
    fname = safe_filename(ib, detail)
    fpath = os.path.join(out_dir, fname)

    md = render_markdown(ib=ib, tabs=tabs)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(md)

    tab3 = tabs.get("ket_qua_lua_chon_nha_thau") or {}
    winners = (tab3.get("danh_sach_nha_thau_trung") or []) if isinstance(tab3, dict) else []
    print(json.dumps({
        "status": st if st else "ok",
        "ib": ib,
        "file": fpath,
        "message": detail.get("message") or "exported",
        "tab1_fields": len(tabs.get("thong_bao_moi_thau") or {}),
        "tab2_fields": len(tabs.get("bien_ban_mo_thau") or {}),
        "tab3_count": len(winners) if isinstance(winners, list) else 0,
        "tab3_member_count": (tab3.get("thanh_vien_count") or 0) if isinstance(tab3, dict) else 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
