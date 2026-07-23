#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime
from typing import Any, Dict, List

BASE = "https://muasamcong.mpi.gov.vn"
ENDPOINT = "/o/egp-portal-contractor-selection-v2/services/smart/search"
RESOLVE_SCRIPT = "scripts/msc_unit_resolve.py"


def to_dt(s: str) -> datetime:
    s = (s or "").strip()
    if not s:
        return datetime.min
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return datetime.min


def resolve_unit(query: str) -> Dict[str, Any]:
    p = subprocess.run(["python3", RESOLVE_SCRIPT, query], capture_output=True, text=True, timeout=35)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "resolve failed").strip())
    return json.loads((p.stdout or "{}").strip() or "{}")


def build_payload(unit_id: str, page_number: int, page_size: int, exclude_case_khkq: bool, entity_field: str) -> List[Dict[str, Any]]:
    filters = [
        {"fieldName": "type", "searchType": "in", "fieldValues": ["es-notify-contractor"]},
        {"fieldName": entity_field, "searchType": "in", "fieldValues": [unit_id]},
    ]
    if exclude_case_khkq:
        filters.append({"fieldName": "caseKHKQ", "searchType": "not_in", "fieldValues": ["1"]})

    return [{
        "pageSize": page_size,
        "pageNumber": page_number,
        "query": [{
            "index": "es-contractor-selection",
            "keyWord": "",
            "matchType": "all-1",
            "matchFields": ["notifyNo", "bidName", "procuringEntityName"],
            "filters": filters,
        }],
    }]


def _escape_config_value(val: str) -> str:
    # Order of replace is critical: escape backslash first, then escape double quotes, then strip newlines
    return val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "").replace("\r", "")


def call_api(token: str, payload: List[Dict[str, Any]], cookie: str = "") -> Dict[str, Any]:
    url = f"{BASE}{ENDPOINT}?token={token}"
    config_lines = [
        f'url = "{_escape_config_value(url)}"'
    ]
    if cookie:
        config_lines.append(f'header = "Cookie: {_escape_config_value(cookie)}"')

    config_str = "\n".join(config_lines) + "\n"

    cmd = [
        "curl", "-sS", "-L", "--max-time", "60",
        "-H", "User-Agent: Mozilla/5.0",
        "-H", "Accept: application/json, text/plain, */*",
        "-H", "Content-Type: application/json",
        "-H", f"Origin: {BASE}",
        "-H", f"Referer: {BASE}/web/guest/contractor-selection",
        "--data-raw", json.dumps(payload, ensure_ascii=False),
        "--config", "-"
    ]

    p = subprocess.run(cmd, input=config_str, capture_output=True, text=True, timeout=70)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or f"curl failed {p.returncode}").strip())
    return json.loads((p.stdout or "{}").strip() or "{}")


def normalize_rows(content: List[Dict[str, Any]], source_field: str) -> List[Dict[str, Any]]:
    rows = []
    for x in content or []:
        bid_name = x.get("bidName")
        if isinstance(bid_name, list):
            bid_name = " | ".join(str(i) for i in bid_name)
        rows.append({
            "notifyNo": x.get("notifyNo") or x.get("planNo") or x.get("id") or "",
            "name": bid_name or "",
            "unit": x.get("procuringEntityName") or x.get("investorName") or "",
            "publicDate": x.get("publicDate") or x.get("publishDate") or "",
            "sourceField": source_field,
        })
    return rows


def fetch_field(unit_id: str, n: int, token: str, cookie: str, exclude_case_khkq: bool, entity_field: str) -> Dict[str, Any]:
    page_size = min(max(20, n * 2), 100)
    max_pages = 12
    all_rows: List[Dict[str, Any]] = []
    total = 0

    for page in range(max_pages):
        payload = build_payload(unit_id, page, page_size, exclude_case_khkq, entity_field)
        data = call_api(token, payload, cookie=cookie)
        pg = data.get("page") or {}
        total = int(pg.get("totalElements") or total or 0)
        content = pg.get("content") or []
        if not content:
            break

        all_rows.extend(normalize_rows(content, entity_field))
        if len(all_rows) >= max(n * 4, n + 50):
            break

    return {"total": total, "rows": all_rows}


def fetch_tbmt(unit_id: str, n: int, token: str = "", cookie: str = "", exclude_case_khkq: bool = False) -> Dict[str, Any]:
    a = fetch_field(unit_id, n, token, cookie, exclude_case_khkq, "procuringEntityCode")
    b = fetch_field(unit_id, n, token, cookie, exclude_case_khkq, "investorCode")

    all_rows = (a.get("rows") or []) + (b.get("rows") or [])
    all_rows.sort(key=lambda r: to_dt(r.get("publicDate", "")), reverse=True)

    seen = set()
    out = []
    for r in all_rows:
        k = (r.get("notifyNo") or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(r)
        if len(out) >= n:
            break

    return {"total": max(a.get("total", 0), b.get("total", 0)), "rows": out}


def main():
    import os
    from pathlib import Path
    ap = argparse.ArgumentParser(description="TBMT precise list by unit (resolved by name or id)")
    ap.add_argument("query", help="Tên/alias đơn vị hoặc ID vn...")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--token", default="", help="MSC API bearer token")
    ap.add_argument("--cookie", default="", help="MSC Cookie")
    ap.add_argument("--exclude-case-khkq", action="store_true")
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

    resolved = resolve_unit(args.query)
    st = resolved.get("status")
    if st != "ok":
        print(json.dumps({
            "status": st,
            "query": args.query,
            "message": resolved.get("message") or "resolve_failed",
            "candidates": resolved.get("candidates") or [],
        }, ensure_ascii=False, indent=2))
        return

    unit = resolved.get("unit") or {}
    unit_id = unit.get("id")
    if not unit_id:
        raise SystemExit("resolve missing unit id")

    result = fetch_tbmt(unit_id=unit_id, n=args.n, token=token, cookie=cookie, exclude_case_khkq=args.exclude_case_khkq)

    print(json.dumps({
        "status": "ok",
        "query": args.query,
        "unit": unit,
        "n": args.n,
        "total": result.get("total", 0),
        "rows": result.get("rows", []),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
