#!/usr/bin/env python3
"""Vietnamese public procurement (Mua Sắm Công): Contractor analysis details."""
import argparse
import json
import urllib.request
import urllib.error
import os
import sys
from pathlib import Path

# Force stdout/stderr to use UTF-8 encoding on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

BASE = "https://muasamcong.mpi.gov.vn"
ENDPOINT = "/o/egp-portal-personal-page/services/static-overview-nt"

def get_session_token():
    # 1. Environment variable
    token = os.getenv("MSC_SESSION_TOKEN", "")
    if token:
        return token
        
    # 2. Paths check
    paths = [
        Path("C:/Users/Desktop/.hermes/.env"),
        Path("/opt/data/.env"),
        Path.home() / ".hermes" / ".env"
    ]
    for env_path in paths:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("MSC_SESSION_TOKEN="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception as e:
                print(f"Error reading token from {env_path}: {e}", file=sys.stderr)
    return ""

def format_percentage(val):
    if val is None:
        return "-"
    try:
        val_float = float(val)
        # Handle both fraction (e.g. 0.05) and percentage (e.g. 5.0) formats
        if val_float < 1.0:
            return f"{val_float * 100:.1f}%"
        return f"{val_float:.1f}%"
    except (ValueError, TypeError):
        return str(val)

def format_money(val):
    if val is None:
        return "-"
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return str(val)

def get_row_values(metric_data, is_money=False, is_percent=False):
    keys = ["total", "hh", "xl", "ptv", "tv", "honhop"]
    vals = []
    for k in keys:
        if not metric_data or k not in metric_data:
            vals.append("-")
            continue
            
        item = metric_data[k]
        if is_money:
            val = item.get("quantity") or item.get("value") or 0
            vals.append(format_money(val))
        elif is_percent:
            val = item.get("savingRate") or item.get("quantity") or 0
            vals.append(format_percentage(val))
        else:
            quantity = item.get("quantity")
            saving_rate = item.get("savingRate")
            if quantity is None:
                vals.append("-")
            elif saving_rate is not None and float(saving_rate) > 0:
                vals.append(f"{int(quantity)} ({format_percentage(saving_rate)})")
            else:
                vals.append(f"{int(quantity)}")
    return vals

def generate_markdown_report(org_code, data):
    title = f"# 📊 Báo cáo phân tích nhà thầu: `{org_code}`"
    
    headers = ["Nội dung thống kê", "Tổng số", "Hàng hóa", "Xây lắp", "Phi tư vấn", "Tư vấn", "Hỗn hợp"]
    
    rows = [
        ("Số lượng/ Tỷ lệ gói thầu chỉ có duy nhất NT tham dự", get_row_values(data.get("quantityOnlyBidderJoin"))),
        ("Số lượng/ Tỷ lệ gói thầu là NT duy nhất đáp ứng KT", get_row_values(data.get("quantityOnlyBidderJoinTech"))),
        ("Số lượng/ Tỷ lệ gói thầu trúng thầu", get_row_values(data.get("quantityBidWinningPrice"))),
        ("Tổng giá trị trúng thầu (VND)", get_row_values(data.get("totalPriceWinningPrice"), is_money=True)),
        ("Tỷ lệ tiết kiệm trung bình", get_row_values(data.get("avgSavingRate"), is_percent=True)),
        ("Số lượng/ Tỷ lệ gói thầu trượt thầu", get_row_values(data.get("totalFailWinningPrice"))),
        ("Số lượng/ Tỷ lệ gói thầu chào giá thấp nhất", get_row_values(data.get("lowestBidRateJoin"))),
        ("Số lượng/ Tỷ lệ gói thầu chào giá thấp nhất và trúng thầu", get_row_values(data.get("lowestBidAndWinning"))),
        ("Số lượng/ Tỷ lệ gói thầu chào giá thấp nhất nhưng trượt thầu", get_row_values(data.get("lowestBidAndFail"))),
        ("Số gói thầu đã tham gia nhưng hủy thầu", get_row_values(data.get("joinAndCancel"))),
        ("Số gói thầu tham gia có từ 2 NT đạt kỹ thuật mà hủy thầu", get_row_values(data.get("mulPassCancel"))),
        ("Số gói thầu là NT duy nhất đáp ứng KT mà bị hủy thầu", get_row_values(data.get("onePassCancel")))
    ]
    
    md = [title, ""]
    md.append("| " + " | ".join(headers) + " |")
    md.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    for label, vals in rows:
        md.append(f"| {label} | " + " | ".join(vals) + " |")
        
    return "\n".join(md)

def run_analysis(org_code, token):
    if not token:
        token = get_session_token()
        
    if not token:
        return json.dumps({"status": "login_error", "error": "No token available"})
        
    url = f"{BASE}{ENDPOINT}?token={token}"
    payload = {
        "orgCode": org_code,
        "fromDate": "1997-01-01T00:00:00.000Z",
        "toDate": "2121-01-01T00:00:00.000Z"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_bytes = response.read()
            if not resp_bytes:
                return json.dumps({"status": "error", "error": "Empty response from API"})
            resp_str = resp_bytes.decode('utf-8')
            data = json.loads(resp_str)
            if "quantityOnlyBidderJoin" not in data:
                return json.dumps({"status": "error", "error": "Invalid API response format", "raw": resp_str[:200]})
            return json.dumps({"status": "ok", "result": data, "markdown": generate_markdown_report(org_code, data)}, ensure_ascii=False)
    except urllib.error.HTTPError as he:
        err_body = ""
        try:
            err_body = he.read().decode('utf-8')
        except Exception:
            pass
        return json.dumps({"status": "error", "error": f"HTTP Error {he.code}: {he.reason}", "raw": err_body[:200]})
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Failed to call API: {e}"})

def main():
    ap = argparse.ArgumentParser(description="Get MSC contractor opportunity analysis report")
    ap.add_argument("--org-code", required=True, help="Contractor organization code (e.g. vn0108557117)")
    ap.add_argument("--token", default="", help="Optional keycloak JWT token")
    ap.add_argument("--markdown", action="store_true", help="Print report in markdown format")
    args = ap.parse_args()
    
    res_str = run_analysis(args.org_code, args.token)
    try:
        res = json.loads(res_str)
        if args.markdown and res.get("status") == "ok":
            print(res["markdown"])
        else:
            print(res_str)
    except Exception:
        print(res_str)

if __name__ == "__main__":
    main()
