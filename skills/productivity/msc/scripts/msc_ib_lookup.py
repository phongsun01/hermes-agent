#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from typing import Any, Dict

BASE = "https://muasamcong.mpi.gov.vn"
ENDPOINT = "/o/egp-portal-contractor-selection-v2/services/smart/search"


def normalize_ib(s: str) -> str:
    return (s or "").strip().upper()


def valid_ib(s: str) -> bool:
    return re.fullmatch(r"IB\d{8,}", s or "") is not None


def build_payload(ib: str):
    return [{
        "pageSize": 10,
        "pageNumber": 0,
        "query": [{
            "index": "es-contractor-selection",
            "keyWord": ib,
            "matchType": "all-1",
            "matchFields": ["notifyNo", "bidName", "procuringEntityName"],
            "filters": [
                {"fieldName": "type", "searchType": "in", "fieldValues": ["es-notify-contractor"]}
            ],
        }],
    }]


def fetch(token: str, ib: str, cookie: str = "") -> Dict[str, Any]:
    url = f"{BASE}{ENDPOINT}?token={token}"
    body = json.dumps(build_payload(ib), ensure_ascii=False)

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
        bid_name = " | ".join(str(i) for i in bid_name)
    detail_link = x.get("url") or x.get("link") or x.get("linkDetail") or x.get("detailUrl")
    return {
        "id": x.get("id"),
        "notifyId": x.get("notifyId") or x.get("id"),
        "inputResultId": x.get("inputResultId"),
        "bidOpenId": x.get("bidOpenId"),
        "planNo": x.get("planNo"),
        "notifyNo": x.get("notifyNo"),
        "name": bid_name,
        "unit": x.get("procuringEntityName") or x.get("investorName"),
        "publicDate": x.get("publicDate") or x.get("publishDate"),
        "closeDate": x.get("bidCloseDate") or x.get("closeDate") or x.get("closingDate"),
        "bidMode": x.get("bidMode"),
        "bidForm": x.get("bidForm"),
        "processApply": x.get("processApply"),
        "stepCode": x.get("stepCode"),
        "type": x.get("type"),
        "isInternet": x.get("isInternet"),
        "detail_link": detail_link,
    }


def parse_args():
    ap = argparse.ArgumentParser(description="Lookup a single TBMT by IB code")
    # Backward compatible: accepts positional IB OR --ib
    ap.add_argument("ib_pos", nargs="?", help="IB code, e.g. IB12345678")
    ap.add_argument("--ib", dest="ib_opt", default="", help="IB code, e.g. IB12345678")
    ap.add_argument("--token", default="", help="reCAPTCHA token (optional)")
    ap.add_argument("--cookie", default="")
    return ap.parse_args()


def main():
    args = parse_args()
    ib = normalize_ib(args.ib_opt or args.ib_pos or "")
    if not valid_ib(ib):
        print(json.dumps({"status": "invalid_ib", "message": "sai số IB", "ib": ib}, ensure_ascii=False))
        return

    data = fetch(args.token, ib, cookie=args.cookie)
    rows = [extract_row(x) for x in (data.get("page", {}).get("content") or [])]

    exact = [r for r in rows if (r.get("notifyNo") or "").upper() == ib]

    if len(exact) == 0:
        print(json.dumps({"status": "not_found", "message": "sai số IB", "ib": ib}, ensure_ascii=False))
        return
    if len(exact) > 1:
        print(json.dumps({"status": "multiple", "message": "nhiều hơn 1 kết quả", "ib": ib, "count": len(exact)}, ensure_ascii=False))
        return

    print(json.dumps({"status": "ok", "ib": ib, "result": exact[0]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
