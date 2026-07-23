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


def _escape_config_value(val: str) -> str:
    # Order of replace is critical: escape backslash first, then escape double quotes, then strip newlines
    return val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "").replace("\r", "")


def fetch(token: str, ib: str, cookie: str = "") -> Dict[str, Any]:
    url = f"{BASE}{ENDPOINT}?token={token}"
    body = json.dumps(build_payload(ib), ensure_ascii=False)

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
        "--data-raw", body,
        "--config", "-"
    ]

    p = subprocess.run(cmd, input=config_str, capture_output=True, text=True, timeout=70)
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
    ap.add_argument("--token", default="", help="MSC API bearer token")
    ap.add_argument("--cookie", default="", help="MSC Cookie")
    return ap.parse_args()


def main():
    import os
    from pathlib import Path
    args = parse_args()
    ib = normalize_ib(args.ib_opt or args.ib_pos or "")
    if not valid_ib(ib):
        print(json.dumps({"status": "invalid_ib", "message": "sai số IB", "ib": ib}, ensure_ascii=False))
        return

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

    data = fetch(token, ib, cookie=cookie)
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
