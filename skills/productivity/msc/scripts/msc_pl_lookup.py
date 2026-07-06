#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from typing import Any, Dict

BASE = "https://muasamcong.mpi.gov.vn"
ENDPOINT = "/o/egp-portal-contractor-selection-v2/services/smart/search"


def normalize_pl(s: str) -> str:
    return (s or "").strip().upper()


def valid_pl(s: str) -> bool:
    return re.fullmatch(r"PL\d{8,}", s or "") is not None


def build_payload(pl: str):
    return [{
        "pageSize": 5,
        "pageNumber": 0,
        "query": [{
            "index": "es-contractor-selection",
            "keyWord": pl,
            "matchType": "all-1",
            "matchFields": ["notifyNo", "planNo", "bidName", "procuringEntityName"],
            "filters": [
                {"fieldName": "type", "searchType": "in", "fieldValues": ["es-plan-project-p"]}
            ],
        }],
    }]


def fetch(token: str, pl: str, cookie: str = "") -> Dict[str, Any]:
    url = f"{BASE}{ENDPOINT}?token={token}"
    body = json.dumps(build_payload(pl), ensure_ascii=False)

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

    raw = (p.stdout or "").strip()
    if not raw:
        raise RuntimeError("empty response")
    data = json.loads(raw)
    if not isinstance(data, dict) or "page" not in data:
        raise RuntimeError("invalid response format")
    return data


def extract_row(x: Dict[str, Any]) -> Dict[str, Any]:
    bid_name = x.get("bidName")
    if isinstance(bid_name, list):
        bid_name = " | ".join(bid_name)
    detail_link = x.get("url") or x.get("link") or x.get("linkDetail") or x.get("detailUrl")
    return {
        "id": x.get("id"),
        "planNo": x.get("planNo"),
        "notifyNo": x.get("notifyNo") or x.get("planNo") or x.get("id"),
        "name": bid_name,
        "unit": x.get("procuringEntityName") or x.get("investorName"),
        "publicDate": x.get("publicDate") or x.get("publishDate"),
        "detail_link": detail_link,
    }


def main():
    ap = argparse.ArgumentParser(description="Lookup a single KHLCNT by PL code")
    ap.add_argument("--token", required=True, help="reCAPTCHA token")
    ap.add_argument("--pl", required=True, help="PL code, e.g. PL12345678")
    ap.add_argument("--cookie", default="")
    args = ap.parse_args()

    pl = normalize_pl(args.pl)
    if not valid_pl(pl):
        print(json.dumps({"status": "invalid_pl", "message": "sai số PL", "pl": pl}, ensure_ascii=False))
        return

    data = fetch(args.token, pl, cookie=args.cookie)
    rows = [extract_row(x) for x in (data.get("page", {}).get("content") or [])]

    exact = [r for r in rows if (r.get("notifyNo") or "").upper() == pl]

    if len(exact) == 0:
        print(json.dumps({"status": "not_found", "message": "sai số PL", "pl": pl}, ensure_ascii=False))
        return
    if len(exact) > 1:
        print(json.dumps({"status": "multiple", "message": "nhiều hơn 1 kết quả", "pl": pl, "count": len(exact)}, ensure_ascii=False))
        return

    print(json.dumps({"status": "ok", "pl": pl, "result": exact[0]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
