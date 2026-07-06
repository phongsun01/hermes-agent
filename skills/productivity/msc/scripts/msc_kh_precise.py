#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

BASE = "https://muasamcong.mpi.gov.vn"
ENDPOINT = "/o/egp-portal-contractor-selection-v2/services/smart/search"
RESOLVE_SCRIPT = "scripts/msc_unit_resolve.py"
TZ7 = timezone(timedelta(hours=7))


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


def iso_from_date(d: datetime, end: bool = False) -> str:
    dt = d.replace(hour=23 if end else 0, minute=59 if end else 0, second=59 if end else 0, microsecond=59000 if end else 0)
    return dt.isoformat()


def build_payload(unit_id: str, page_number: int, page_size: int, entity_field: str, day_from: datetime | None = None, day_to: datetime | None = None) -> List[Dict[str, Any]]:
    filters = [
        {"fieldName": "type", "searchType": "in", "fieldValues": ["es-plan-project-p"]},
        {"fieldName": entity_field, "searchType": "in", "fieldValues": [unit_id]},
    ]
    if day_from and day_to:
        filters.append({
            "fieldName": "publicDate",
            "searchType": "range",
            "from": iso_from_date(day_from, end=False),
            "to": iso_from_date(day_to, end=True),
        })

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


def call_api(token: str, payload: List[Dict[str, Any]], cookie: str = "") -> Dict[str, Any]:
    url = f"{BASE}{ENDPOINT}?token={token}"
    cmd = [
        "curl", "-sS", "-L", "--max-time", "60",
        "-H", "User-Agent: Mozilla/5.0",
        "-H", "Accept: application/json, text/plain, */*",
        "-H", "Content-Type: application/json",
        "-H", f"Origin: {BASE}",
        "-H", f"Referer: {BASE}/web/guest/contractor-selection",
    ]
    if cookie:
        cmd += ["-H", f"Cookie: {cookie}"]
    cmd += ["--data-raw", json.dumps(payload, ensure_ascii=False), url]

    p = subprocess.run(cmd, capture_output=True, text=True, timeout=70)
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


def fetch_field(unit_id: str, n: int, token: str, cookie: str, entity_field: str, day_from: datetime | None = None, day_to: datetime | None = None) -> Dict[str, Any]:
    page_size = min(max(20, n * 2), 100)
    max_pages = 12
    all_rows: List[Dict[str, Any]] = []
    total = 0

    for page in range(max_pages):
        payload = build_payload(unit_id, page, page_size, entity_field, day_from=day_from, day_to=day_to)
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


def fetch_kh(unit_id: str, n: int, token: str = "", cookie: str = "", date_from: str = "", date_to: str = "") -> Dict[str, Any]:
    df = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=TZ7) if date_from else None
    dt = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=TZ7) if date_to else None

    a = fetch_field(unit_id, n, token, cookie, "investorCode", day_from=df, day_to=dt)
    b = fetch_field(unit_id, n, token, cookie, "procuringEntityCode", day_from=df, day_to=dt)

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
    ap = argparse.ArgumentParser(description="KH precise list by unit (resolved by name or id)")
    ap.add_argument("query", help="Tên/alias đơn vị hoặc ID vn...")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--token", default="")
    ap.add_argument("--cookie", default="")
    ap.add_argument("--date-from", default="")
    ap.add_argument("--date-to", default="")
    args = ap.parse_args()

    if bool(args.date_from) ^ bool(args.date_to):
        raise SystemExit("date-from và date-to phải đi cùng nhau")

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

    result = fetch_kh(unit_id=unit_id, n=args.n, token=args.token, cookie=args.cookie, date_from=args.date_from, date_to=args.date_to)

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
