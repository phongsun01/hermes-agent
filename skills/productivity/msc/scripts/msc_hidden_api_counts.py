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


def _escape_config_value(val: str) -> str:
    # Order of replace is critical: escape backslash first, then escape double quotes, then strip newlines
    return val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "").replace("\r", "")


def fetch_total(token: str, noti: str, day: datetime, cookie: str = '') -> int:
    url = f"{BASE}{ENDPOINT}?token={token}"
    body = json.dumps(payload_for(noti, day), ensure_ascii=False)

    config_lines = [
        f'url = "{_escape_config_value(url)}"'
    ]
    if cookie:
        config_lines.append(f'header = "Cookie: {_escape_config_value(cookie)}"')

    config_str = "\n".join(config_lines) + "\n"

    cmd = [
        'curl', '-sS', '-L', '--max-time', '45',
        '-H', 'User-Agent: Mozilla/5.0',
        '-H', 'Accept: application/json, text/plain, */*',
        '-H', 'Content-Type: application/json',
        '-H', f'Origin: {BASE}',
        '-H', f'Referer: {BASE}/web/guest/contractor-selection',
        '--data-raw', body,
        '--config', '-'
    ]

    p = subprocess.run(cmd, input=config_str, capture_output=True, text=True, timeout=60)
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
    import os
    from pathlib import Path
    ap = argparse.ArgumentParser(description="Query hidden smart/search endpoint for KHLCNT/TBMT counts")
    ap.add_argument("--token", default="", help="MSC API bearer token")
    ap.add_argument("--date", default="today", help="today|yesterday|YYYY-MM-DD")
    ap.add_argument("--noti", choices=["khlcnt", "tbmt"], required=True)
    ap.add_argument("--cookie", default="", help="Optional Cookie header if needed")
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

    now = datetime.now(TZ7)
    if args.date == "today":
        day = now
    elif args.date == "yesterday":
        day = now - timedelta(days=1)
    else:
        day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=TZ7)

    total = fetch_total(token, args.noti, day, cookie)
    out = {
        "noti": args.noti,
        "date": day.strftime("%Y-%m-%d"),
        "total": total,
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
