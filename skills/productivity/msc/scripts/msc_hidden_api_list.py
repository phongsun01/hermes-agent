#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import subprocess

BASE = "https://muasamcong.mpi.gov.vn"
ENDPOINT = "/o/egp-portal-contractor-selection-v2/services/smart/search"
TZ7 = timezone(timedelta(hours=7))


def iso_from_date(d: datetime, end: bool = False) -> str:
    dt = d.replace(hour=23 if end else 0, minute=59 if end else 0, second=59 if end else 0, microsecond=59000 if end else 0)
    return dt.isoformat()


def payload_for(kind: str, unit_id: str, page_size: int, page_number: int, day_from: datetime | None, day_to: datetime | None, exclude_case_khkq: bool = False, entity_field: str = "procuringEntityCode") -> Dict[str, Any]:
    filters = []

    if kind == "kh":
        filters.append({"fieldName": "type", "searchType": "in", "fieldValues": ["es-plan-project-p"]})
    elif kind == "tbmt":
        filters.append({"fieldName": "type", "searchType": "in", "fieldValues": ["es-notify-contractor"]})
        if exclude_case_khkq:
            filters.append({"fieldName": "caseKHKQ", "searchType": "not_in", "fieldValues": ["1"]})
    else:
        raise ValueError("kind must be kh|tbmt")

    filters.append({"fieldName": entity_field, "searchType": "in", "fieldValues": [unit_id]})

    if day_from and day_to:
        filters.append({
            "fieldName": "publicDate",
            "searchType": "range",
            "from": iso_from_date(day_from, end=False),
            "to": iso_from_date(day_to, end=True),
        })

    p = {
        "pageSize": page_size,
        "pageNumber": page_number,
        "query": [{
            "index": "es-contractor-selection",
            "keyWord": "",
            "matchType": "all-1",
            "matchFields": ["notifyNo", "bidName", "procuringEntityName"],
            "filters": filters,
        }],
    }
    return [p]


def fetch(token: str, kind: str, unit_id: str, n: int, day_from: datetime | None, day_to: datetime | None, cookie: str = "", exclude_case_khkq: bool = False, entity_field: str = "procuringEntityCode"): 
    url = f"{BASE}{ENDPOINT}?token={token}"

    # Lấy nhiều trang để đảm bảo đúng "mới nhất" theo publicDate.
    page_size = min(max(n, 20), 100)
    max_pages = 8
    all_rows = []
    total = 0

    for page_number in range(max_pages):
        body = json.dumps(payload_for(kind, unit_id, page_size, page_number, day_from, day_to, exclude_case_khkq=exclude_case_khkq, entity_field=entity_field), ensure_ascii=False)

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
        cmd += ["--data-raw", body, url]

        p = subprocess.run(cmd, capture_output=True, text=True, timeout=70)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.strip() or f"curl failed: {p.returncode}")

        data = json.loads((p.stdout or "").strip() or "{}")
        if not isinstance(data, dict) or "page" not in data:
            raise RuntimeError("invalid response")

        pg = data.get("page") or {}
        total = int(pg.get("totalElements") or total or 0)
        content = pg.get("content") or []
        if not content:
            break

        for x in content:
            bid_name = x.get("bidName")
            if isinstance(bid_name, list):
                bid_name = " | ".join(bid_name)
            all_rows.append({
                "notifyNo": x.get("notifyNo") or x.get("planNo") or x.get("id"),
                "name": bid_name,
                "unit": x.get("procuringEntityName") or x.get("investorName"),
                "publicDate": x.get("publicDate") or x.get("publishDate"),
                "rawId": x.get("id"),
                "planNo": x.get("planNo"),
            })

        # đủ dữ liệu để sort rồi cắt n
        if len(all_rows) >= max(n * 2, n + 20):
            break

    # Sắp xếp đúng theo ngày công bố mới nhất (desc), rồi cắt n
    all_rows.sort(key=lambda r: (r.get("publicDate") or ""), reverse=True)

    # dedupe linh hoạt theo mã hiện có (notifyNo/planNo/id)
    seen = set()
    rows = []
    for r in all_rows:
        key_parts = [r.get("notifyNo"), r.get("planNo"), r.get("rawId")]
        k = "|".join([(p or "").strip().lower() for p in key_parts if (p or "").strip()])
        if not k:
            # fallback cuối theo tên + ngày
            k = f"{(r.get('name') or '').strip().lower()}|{(r.get('publicDate') or '').strip()}"
        if k in seen:
            continue
        seen.add(k)
        rows.append(r)
        if len(rows) >= n:
            break

    return {
        "total": total,
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description="List TBMT/KH by unit id from MSC hidden API")
    ap.add_argument("--token", required=True)
    ap.add_argument("--kind", required=True, choices=["tbmt", "kh"])
    ap.add_argument("--unit-id", required=True)
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--date-from", default="")
    ap.add_argument("--date-to", default="")
    ap.add_argument("--cookie", default="")
    ap.add_argument("--exclude-case-khkq", action="store_true", help="TBMT only: loại bản ghi có caseKHKQ=1")
    ap.add_argument("--entity-field", default="procuringEntityCode", choices=["procuringEntityCode", "investorCode"], help="Field đơn vị để lọc")
    args = ap.parse_args()

    df = datetime.strptime(args.date_from, "%Y-%m-%d").replace(tzinfo=TZ7) if args.date_from else None
    dt = datetime.strptime(args.date_to, "%Y-%m-%d").replace(tzinfo=TZ7) if args.date_to else None
    if (df and not dt) or (dt and not df):
        raise SystemExit("date-from and date-to must go together")

    out = fetch(args.token, args.kind, args.unit_id, args.n, df, dt, args.cookie, exclude_case_khkq=args.exclude_case_khkq, entity_field=args.entity_field)
    print(json.dumps({
        "kind": args.kind,
        "unit_id": args.unit_id,
        "n": args.n,
        "total": out["total"],
        "rows": out["rows"][: args.n],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
