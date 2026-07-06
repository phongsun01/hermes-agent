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
    if end:
        dt = d.replace(hour=23, minute=59, second=59, microsecond=59000)
    else:
        dt = d.replace(hour=0, minute=0, second=0, microsecond=0)
    # frontend pushes local time; use timezone-aware iso
    return dt.isoformat()


def payload_for(noti: str, day: datetime) -> Dict[str, Any]:
    filters = [
        {
            "fieldName": "publicDate",
            "searchType": "range",
            "from": iso_from_date(day, end=False),
            "to": iso_from_date(day, end=True),
        }
    ]

    if noti == "khlcnt":
        filters.append({
            "fieldName": "type",
            "searchType": "in",
            "fieldValues": ["es-plan-project-p"],
        })
    elif noti == "tbmt":
        filters.append({
            "fieldName": "type",
            "searchType": "in",
            "fieldValues": ["es-notify-contractor"],
        })
    else:
        raise ValueError("noti must be khlcnt|tbmt")

    p = {
        "pageSize": 10,
        "pageNumber": 0,
        "query": [
            {
                "index": "es-contractor-selection",
                "keyWord": "",
                "matchType": "all-1",
                "matchFields": ["notifyNo", "bidName"],
                "filters": filters,
            }
        ],
    }
    # Endpoint expects array payload from frontend format function
    return [p]


def fetch_total(token: str, noti: str, day: datetime, cookie: str = '') -> int:
    url = f"{BASE}{ENDPOINT}?token={token}"
    body = json.dumps(payload_for(noti, day), ensure_ascii=False)

    cmd = [
        'curl', '-sS', '-L', '--max-time', '45',
        '-H', 'User-Agent: Mozilla/5.0',
        '-H', 'Accept: application/json, text/plain, */*',
        '-H', 'Content-Type: application/json',
        '-H', f'Origin: {BASE}',
        '-H', f'Referer: {BASE}/web/guest/contractor-selection',
    ]
    if cookie:
        cmd += ['-H', f'Cookie: {cookie}']
    cmd += ['--data-raw', body, url]

    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f'curl failed: {p.returncode}')

    raw = (p.stdout or '').strip()
    if not raw:
        raise RuntimeError('empty response')

    data = json.loads(raw)

    # success path commonly object with page.totalElements
    if isinstance(data, dict):
        page = data.get("page") or {}
        total = page.get("totalElements")
        if total is None:
            raise RuntimeError(f"No page.totalElements in response keys={list(data.keys())[:12]}")
        return int(total)

    # blocked path observed as number
    if isinstance(data, (int, float)):
        raise RuntimeError(f"Gateway returned numeric guard value: {data} (likely token/session invalid)")

    raise RuntimeError(f"Unexpected response type: {type(data).__name__}")


def main():
    ap = argparse.ArgumentParser(description="Query hidden smart/search endpoint for KHLCNT/TBMT counts")
    ap.add_argument("--token", required=True, help="reCAPTCHA token from active browser session")
    ap.add_argument("--date", default="today", help="today|yesterday|YYYY-MM-DD")
    ap.add_argument("--noti", choices=["khlcnt", "tbmt"], required=True)
    ap.add_argument("--cookie", default="", help="Optional Cookie header if needed")
    args = ap.parse_args()

    now = datetime.now(TZ7)
    if args.date == "today":
        day = now
    elif args.date == "yesterday":
        day = now - timedelta(days=1)
    else:
        day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=TZ7)

    total = fetch_total(args.token, args.noti, day, args.cookie)
    out = {
        "noti": args.noti,
        "date": day.strftime("%Y-%m-%d"),
        "total": total,
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
