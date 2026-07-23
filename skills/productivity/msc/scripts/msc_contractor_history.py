#!/usr/bin/env python3
"""Vietnamese public procurement (Mua Sắm Công): Contractor bidding history details."""
import argparse
import json
import urllib.request
import sys
from pathlib import Path

# Force stdout/stderr to use UTF-8 encoding on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def format_money(val):
    if val is None or val == 0:
        return "-"
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return str(val)

def format_result(res_code):
    if res_code == 'Y':
        return "🟢 Trúng thầu"
    elif res_code == 'N':
        return "🔴 Trượt thầu"
    return str(res_code) if res_code else "-"

def fetch_tokens_from_service():
    """Fetch tokens from the host's FastAPI service."""
    # Attempt host.docker.internal first (if running inside Docker)
    # Fallback to localhost (if running on host directly for testing)
    endpoints = [
        "http://host.docker.internal:8789/msc/tokens",
        "http://127.0.0.1:8789/msc/tokens",
    ]
    
    last_err = None
    for url in endpoints:
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=35)
            if resp.status == 200:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            last_err = e
            continue
            
    return {"error": f"Failed to get tokens from service: {last_err}"}

def fetch_history_direct(org_code, page_num, page_size):
    """Fetch history directly via REST API using tokens from service."""
    tokens = fetch_tokens_from_service()
    
    if "error" in tokens:
        return {"status": "error", "error": tokens["error"]}
        
    bearer = tokens.get("bearer_token")
    csrf = tokens.get("csrf_token")
    jsessionid = tokens.get("jsessionid")
    
    if not bearer or not jsessionid or not csrf:
        return {"status": "error", "error": f"Service returned incomplete tokens: {tokens}"}
        
    url = "https://muasamcong.mpi.gov.vn/o/egp-portal-personal-page/services/statistic/detail/ntHisBid"
    
    payload = json.dumps({
        "orgCode": org_code,
        "startDate": "1997-01-01T00:00:00.000Z",
        "endDate": "2121-01-01T00:00:00.000Z",
        "pageSize": page_size,
        "pageNumber": page_num
    }).encode("utf-8")
    
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {bearer}",
        "x-csrf-token": csrf,
        "Cookie": f"JSESSIONID={jsessionid}"
    }
    
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode('utf-8')
        return {"status": "ok", "data": json.loads(text)}
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode('utf-8')
        except Exception:
            text = str(e)
        return {"status": "error", "error": f"API HTTP {e.code}: {text}"}
    except Exception as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}

def generate_markdown(org_code, res_data, page_num, page_size):
    content = res_data.get("content", [])
    total_elements = res_data.get("totalElements", 0)
    total_pages = res_data.get("totalPages", 0)
    
    title = f"## 📜 Lịch sử tham dự thầu của nhà thầu: `{org_code}`"
    meta = f"*Tổng số gói thầu đã tham gia: **{total_elements}** | Trang **{page_num + 1}/{total_pages}** (Hiển thị tối đa {page_size} dòng)*"
    
    headers = ["STT", "Số TBMT", "Tên gói thầu", "Giá dự thầu (VND)", "Giá trúng thầu (VND)", "Kết quả"]
    md = [title, meta, ""]
    md.append("| " + " | ".join(headers) + " |")
    md.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    start_idx = page_num * page_size
    for i, item in enumerate(content):
        stt = start_idx + i + 1
        notify_no = item.get("notifyNo", "-")
        bid_name = item.get("bidName", "-").replace("\n", " ").strip()
        # Limit bid name length for clean output
        if len(bid_name) > 80:
            bid_name = bid_name[:77] + "..."
            
        bid_price = format_money(item.get("bidPrice"))
        win_price = format_money(item.get("winPrice"))
        result = format_result(item.get("bidResult"))
        
        md.append(f"| {stt} | {notify_no} | {bid_name} | {bid_price} | {win_price} | {result} |")
        
    if not content:
        md.append("| | Không có dữ liệu lịch sử tham dự thầu | | | | |")
        
    return "\n".join(md)

def main():
    ap = argparse.ArgumentParser(description="Get contractor bidding history via REST API")
    ap.add_argument("--org-code", required=True, help="Contractor organization code (e.g. vn0108557117)")
    ap.add_argument("--page", type=int, default=0, help="Page number (0-indexed)")
    ap.add_argument("--page-size", type=int, default=20, help="Page size")
    ap.add_argument("--markdown", action="store_true", help="Print report in markdown format")
    args = ap.parse_args()
    
    res = fetch_history_direct(args.org_code, args.page, args.page_size)
    
    if res.get("status") == "ok":
        md = generate_markdown(args.org_code, res["data"], args.page, args.page_size)
        out = {"status": "ok", "result": res["data"], "markdown": md}
        if args.markdown:
            print(md)
        else:
            print(json.dumps(out, ensure_ascii=False))
    else:
        print(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()
