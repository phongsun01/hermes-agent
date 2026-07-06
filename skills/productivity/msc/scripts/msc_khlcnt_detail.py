#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

LOOKUP_SCRIPT = "scripts/msc_pl_lookup.py"
BASE = "https://muasamcong.mpi.gov.vn"
URL_DETAIL_KHLCNT = "/o/egp-portal-contractor-selection-v2/services/expose/lcnt/bid-po-bidp-plan-project-view/get-by-id"
URL_DETAIL_BID_KHLCNT = "/o/egp-portal-contractor-selection-v2/services/lcnt/bid-po-bidp-plan-project-view/get-bidp-plan-detail-by-id"


def log(msg: str, **meta):
    payload = {"msg": msg, **meta}
    print(f"[msc_khlcnt_detail] {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr)


def first_non_empty(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def as_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def as_money(v: Any, unit: str = "VND") -> str:
    if v is None or v == "":
        return ""
    try:
        n = float(str(v).replace(",", "").strip())
        if abs(n - int(n)) < 1e-9:
            return f"{int(n):,} {unit}".replace(",", ".")
        return f"{n:,.2f} {unit}".replace(",", ".")
    except Exception:
        return f"{v} {unit}".strip()


def as_datetime_vi(v: Any) -> str:
    """Format ISO-like datetime to dd/mm/YYYY HH:MM. Fallback raw string."""
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    s2 = s.replace("Z", "")
    if "." in s2:
        s2 = s2.split(".", 1)[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s2[:19], fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
    # date only fallback
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s2[:10], fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
    return s


def map_plan_type(code: Any) -> str:
    m = {
        "TX": "Chi thường xuyên",
        "DT": "Chi đầu tư phát triển",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def map_bid_mode(code: Any) -> str:
    m = {
        "1_MTHS": "Một giai đoạn một túi hồ sơ",
        "1_HS": "Một giai đoạn một túi hồ sơ",
        "1_HTHS": "Một giai đoạn hai túi hồ sơ",
        "2_GD": "Hai giai đoạn",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def map_contract_type(code: Any) -> str:
    m = {
        "TG": "Trọn gói",
        "DGCD": "Theo đơn giá cố định",
        "DGDC": "Theo đơn giá điều chỉnh",
        "TGTG": "Theo thời gian",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def map_process_apply(code: Any) -> str:
    m = {
        "LDT": "Lựa chọn nhà thầu",
        "LDTTR": "Lựa chọn nhà thầu trong nước",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def map_bid_form(code: Any) -> str:
    m = {
        "CHCT": "Chỉ định thầu",
        "CHCTRG": "Chỉ định thầu rút gọn",
        "CDTRG": "Chỉ định thầu rút gọn",
        "CDT": "Chỉ định thầu",
        "DTRR": "Đấu thầu rộng rãi",
        "DTHC": "Đấu thầu hạn chế",
        "MSTT": "Mua sắm trực tiếp",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def extract_id_from_detail_link(link: str) -> str:
    if not link:
        return ""
    try:
        q = parse_qs(urlparse(link).query)
        arr = q.get("id") or []
        return arr[0] if arr else ""
    except Exception:
        return ""


def parse_json_maybe(v: Any) -> Dict[str, Any]:
    if isinstance(v, dict):
        return v
    if not isinstance(v, str):
        return {}
    s = v.strip()
    if not s:
        return {}
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def run_lookup(token: str, pl: str, cookie: str = "") -> Dict[str, Any]:
    cmd = ["python3", LOOKUP_SCRIPT, "--token", token, "--pl", pl]
    if cookie:
        cmd += ["--cookie", cookie]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=80)
    raw = (p.stdout or "").strip()
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {"status": "error", "message": "invalid_lookup_output", "raw": raw[:500]}
    return data


def curl_json_with_retry(path: str, token: str, payload: Dict[str, Any], cookie: str = "", retries: int = 2, timeout_sec: int = 60) -> Dict[str, Any]:
    url = f"{BASE}{path}?token={token}"
    body = json.dumps(payload, ensure_ascii=False)

    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        cmd = [
            "curl", "-sS", "-L", "--max-time", str(timeout_sec),
            "-H", "User-Agent: Mozilla/5.0",
            "-H", "Accept: application/json, text/plain, */*",
            "-H", "Content-Type: application/json",
            "-H", f"Origin: {BASE}",
            "-H", f"Referer: {BASE}/web/guest/contractor-selection",
        ]
        if cookie:
            cmd += ["-H", f"Cookie: {cookie}"]
        cmd += ["--data-raw", body, "-w", "\n__HTTP_STATUS__:%{http_code}", url]

        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec + 10)
        if p.returncode != 0:
            last_err = p.stderr.strip() or f"curl_failed_{p.returncode}"
            log("request_error", path=path, attempt=attempt + 1, error=last_err)
            if attempt < retries:
                time.sleep(0.4 * (2 ** attempt))
                continue
            return {"_error": "network", "_message": last_err}

        raw = (p.stdout or "").strip()
        marker = "\n__HTTP_STATUS__:"
        if marker not in raw:
            last_err = "missing_http_status_marker"
            log("request_error", path=path, attempt=attempt + 1, error=last_err)
            if attempt < retries:
                time.sleep(0.4 * (2 ** attempt))
                continue
            return {"_error": "invalid_http", "_message": last_err}

        body_raw, status_raw = raw.rsplit(marker, 1)
        try:
            http_status = int(status_raw.strip())
        except Exception:
            http_status = 0

        if http_status in (429,) or http_status >= 500:
            last_err = f"http_{http_status}"
            log("request_retry", path=path, attempt=attempt + 1, http_status=http_status)
            if attempt < retries:
                time.sleep(0.4 * (2 ** attempt))
                continue
            return {"_error": "http", "_http_status": http_status, "_body": body_raw[:500]}

        if http_status >= 400:
            return {"_error": "http", "_http_status": http_status, "_body": body_raw[:1000]}

        body_raw = body_raw.strip()
        if not body_raw:
            return {"_error": "empty", "_message": "empty_response"}

        try:
            return json.loads(body_raw)
        except Exception:
            return {"_error": "invalid_json", "_body": body_raw[:1000]}

    return {"_error": "unknown", "_message": last_err or "unknown"}


def is_guard_number_response(x: Any) -> bool:
    return isinstance(x, (int, float))


def normalize_general(lookup_result: Dict[str, Any], detail_main: Dict[str, Any], plan_id: str, pl: str) -> Dict[str, Any]:
    r = (lookup_result or {}).get("result") or {}
    v = (detail_main or {}).get("bidPoBidpPlanProjectDetailView") or {}

    money_v = first_non_empty(v.get("planBidTotal"), v.get("totalBidPrice"), v.get("estimate"), v.get("bidPrice"))
    money_u = first_non_empty(v.get("planBidTotalUnit"), v.get("totalBidPriceUnit"), v.get("estimateUnit"), v.get("bidPriceUnit"), "VND")

    # Fallback: nhiều KHLCNT không trả tổng dự toán ở main object,
    # nhưng có ở danh sách gói thầu con (bidpPlanDetailToProjectList).
    if money_v in (None, ""):
        pkg_rows = (detail_main or {}).get("bidpPlanDetailToProjectList") or []
        if isinstance(pkg_rows, list):
            for row in pkg_rows:
                if not isinstance(row, dict):
                    continue
                pv = first_non_empty(row.get("bidPrice"), row.get("packagePrice"), row.get("totalBidPrice"))
                if pv not in (None, ""):
                    money_v = pv
                    money_u = first_non_empty(
                        row.get("bidPriceUnit"),
                        row.get("packagePriceUnit"),
                        row.get("totalBidPriceUnit"),
                        money_u,
                        "VND",
                    )
                    break

    return {
        "Mã PL": first_non_empty(v.get("planNo"), r.get("notifyNo"), pl) or "",
        "Tên KHLCNT": as_text(first_non_empty(v.get("name"), r.get("name"), "")),
        "Chủ đầu tư": as_text(first_non_empty(v.get("investorName"), r.get("unit"), "")),
        "Phân loại": map_plan_type(first_non_empty(v.get("planTypeName"), v.get("planType"), "")),
        "Dự toán mua sắm": as_money(money_v, as_text(money_u) or "VND") if money_v is not None else "",
        "Nguồn vốn": as_text(first_non_empty(v.get("investmentFunds"), v.get("fundSource"), v.get("capitalSource"), "")),
        "Số quyết định phê duyệt": as_text(first_non_empty(v.get("decisionNo"), "")),
        "Cơ quan phê duyệt": as_text(first_non_empty(v.get("decisionAgency"), "")),
        "Ngày phê duyệt": as_datetime_vi(first_non_empty(v.get("decisionDate"), v.get("approveDate"), v.get("approvalDate"), "")),
        "Ngày đăng tải": as_datetime_vi(first_non_empty(v.get("publicDate"), r.get("publicDate"), "")),
        "Số phiên bản": as_text(first_non_empty(v.get("planVersion"), "")),
    }


def collect_package_raws(detail_main: Dict[str, Any], detail_bid: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    main_list = (detail_main or {}).get("bidpPlanDetailToProjectList") or []
    if isinstance(main_list, list):
        rows.extend([x for x in main_list if isinstance(x, dict)])

    if isinstance(detail_bid, list):
        rows.extend([x for x in detail_bid if isinstance(x, dict)])
    elif isinstance(detail_bid, dict):
        for _, v in detail_bid.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                rows.extend(v)

    return rows


def adapt_packages(detail_main: Dict[str, Any], detail_bid: Any) -> List[Dict[str, Any]]:
    raws = collect_package_raws(detail_main, detail_bid)

    dedup = {}
    for i, x in enumerate(raws, 1):
        key = as_text(first_non_empty(x.get("id"), x.get("bidNo"), x.get("name"), f"idx-{i}")).strip().lower()
        if key in dedup:
            # merge missing fields from new row
            for k, v in x.items():
                if k not in dedup[key] or dedup[key].get(k) in (None, ""):
                    dedup[key][k] = v
        else:
            dedup[key] = dict(x)

    out: List[Dict[str, Any]] = []
    for i, x in enumerate(dedup.values(), 1):
        price = first_non_empty(x.get("bidPrice"), x.get("packagePrice"), x.get("totalBidPrice"))
        price_unit = as_text(first_non_empty(x.get("bidPriceUnit"), x.get("packagePriceUnit"), x.get("totalBidPriceUnit"), "VND"))

        # "Thời gian bắt đầu tổ chức LCNT" ưu tiên biểu diễn dạng Quý/Tháng/Năm
        y = x.get("bidStartYear")
        q = x.get("bidStartQuarter")
        m = x.get("bidStartMonth")
        u = as_text(x.get("bidStartUnit")).strip().upper()

        bid_start_text = ""
        if y and q:
            q_text = as_text(q).strip().upper().replace("Q", "")
            bid_start_text = f"Quý {q_text}, {y}"
        elif y and m not in (None, "", 0):
            bid_start_text = f"Tháng {m}, {y}"
        elif y and u in ("Y", "YEAR"):
            bid_start_text = f"Năm {y}"
        elif y and u in ("Q", "QUARTER"):
            bid_start_text = f"Quý ?, {y}"
        elif y:
            bid_start_text = f"Năm {y}"
        else:
            # fallback cuối nếu không có cấu phần quý/tháng/năm
            bid_start = first_non_empty(x.get("startDate"), x.get("startTime"), x.get("bidStartDate"), x.get("createdDate"), x.get("publicDate"), "")
            bid_start_text = as_datetime_vi(bid_start)

        # Mã gói thầu: chỉ nhận dạng IB..., nếu không thì để trống
        notify_info = parse_json_maybe(x.get("linkNotifyInfo"))
        bid_no_candidate = first_non_empty(
            notify_info.get("notifyNo"),
            x.get("notifyNo"),
            x.get("bidNo"),
            x.get("packageCode"),
            x.get("no"),
            "",
        )
        bid_no_text = as_text(bid_no_candidate).strip().upper()
        if not bid_no_text.startswith("IB"):
            bid_no_text = ""

        # thời gian thực hiện gói thầu theo cperiod + unit nếu có
        cperiod = first_non_empty(x.get("cperiod"), x.get("contractPeriod"))
        cperiod_unit = as_text(first_non_empty(x.get("cperiodUnit"), x.get("contractPeriodUnit"), "")).strip().upper()
        cperiod_text = ""
        if cperiod not in (None, ""):
            unit_map = {"D": "ngày", "M": "tháng", "Y": "năm", "Q": "quý"}
            cperiod_text = f"{cperiod} {unit_map.get(cperiod_unit, cperiod_unit.lower())}".strip()

        row = {
            "STT": i,
            "Mã gói thầu": bid_no_text,
            "Tên gói thầu": as_text(first_non_empty(x.get("name"), x.get("bidName"), x.get("projectName"), "")),
            "Giá gói thầu": as_money(price, price_unit) if price is not None else "",
            "Nguồn vốn": as_text(first_non_empty(x.get("capitalDetail"), x.get("fundSource"), x.get("capitalSource"), "")),
            "Hình thức lựa chọn nhà thầu": map_bid_form(first_non_empty(x.get("bidFormName"), x.get("bidForm"), x.get("contractorSelectionMethod"), "")),
            "Phương thức lựa chọn": map_bid_mode(first_non_empty(x.get("selectionMethodName"), x.get("selectionMethod"), x.get("bidMode"), "")),
            "Loại hợp đồng": map_contract_type(first_non_empty(x.get("contractTypeName"), x.get("contractType"), x.get("ctype"), "")),
            "Thời gian tổ chức lựa chọn nhà thầu": as_text(first_non_empty(x.get("bidTime"), x.get("performTime"), x.get("duration"), x.get("contractTime"), "")),
            "Thời gian bắt đầu tổ chức LCNT": bid_start_text,
            "Thời gian thực hiện gói thầu": cperiod_text,
        }
        out.append(row)

    return out


def main():
    ap = argparse.ArgumentParser(description="Get KHLCNT detail (v2 real API adapter)")
    ap.add_argument("--pl", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--cookie", default="")
    args = ap.parse_args()

    pl = (args.pl or "").strip().upper()
    if re.fullmatch(r"PL\d{8,}", pl) is None:
        print(json.dumps({"status": "invalid_pl", "message": "Usage: /exp PLxxxxxxxx"}, ensure_ascii=False))
        return

    lookup = run_lookup(args.token, pl, cookie=args.cookie)
    st = lookup.get("status")

    if st == "invalid_pl":
        print(json.dumps({"status": "invalid_pl", "message": "Usage: /exp PLxxxxxxxx"}, ensure_ascii=False))
        return
    if st == "not_found":
        print(json.dumps({"status": "not_found", "message": "Không tìm thấy mã PL."}, ensure_ascii=False))
        return
    if st != "ok":
        print(json.dumps({"status": "login_error", "message": "lỗi login", "lookup": lookup}, ensure_ascii=False))
        return

    result = lookup.get("result") or {}
    plan_id = as_text(first_non_empty(result.get("id"), extract_id_from_detail_link(result.get("detail_link") or "")))
    if not plan_id:
        print(json.dumps({
            "status": "unsupported_detail_api",
            "pl": pl,
            "message": "Đã có PL nhưng không suy ra được plan id để gọi detail API.",
            "general": {
                "Mã PL": pl,
                "Tên KHLCNT": as_text(result.get("name") or ""),
                "Đơn vị": as_text(result.get("unit") or ""),
                "Ngày công bố": as_text(result.get("publicDate") or ""),
                "Link chi tiết": as_text(result.get("detail_link") or ""),
            },
            "packages": [],
            "source": {
                "lookup_script": "msc_pl_lookup.py",
                "detail_script": "msc_khlcnt_detail.py",
            }
        }, ensure_ascii=False, indent=2))
        return

    t0 = time.time()
    detail_main = curl_json_with_retry(URL_DETAIL_KHLCNT, args.token, {"id": plan_id}, cookie=args.cookie)
    detail_bid = curl_json_with_retry(URL_DETAIL_BID_KHLCNT, args.token, {"id": plan_id}, cookie=args.cookie)
    elapsed_ms = int((time.time() - t0) * 1000)

    if is_guard_number_response(detail_main) or is_guard_number_response(detail_bid):
        print(json.dumps({"status": "login_error", "message": "lỗi login", "guard": True}, ensure_ascii=False))
        return

    if isinstance(detail_main, dict) and detail_main.get("_error") and isinstance(detail_bid, dict) and detail_bid.get("_error"):
        print(json.dumps({
            "status": "login_error",
            "message": "lỗi gọi detail API",
            "errors": {
                "detail_main": detail_main,
                "detail_bid": detail_bid,
            }
        }, ensure_ascii=False, indent=2))
        return

    main_obj = detail_main if isinstance(detail_main, dict) and not detail_main.get("_error") else {}
    bid_obj = detail_bid if not (isinstance(detail_bid, dict) and detail_bid.get("_error")) else {}

    general = normalize_general(lookup, main_obj, plan_id=plan_id, pl=pl)
    packages = adapt_packages(main_obj, bid_obj)

    status = "ok" if (main_obj or packages) else "unsupported_detail_api"
    message = "Đã lấy dữ liệu chi tiết từ API thật." if status == "ok" else "Chưa lấy được dữ liệu chi tiết đầy đủ."

    out = {
        "status": status,
        "pl": pl,
        "general": general,
        "packages": packages,
        "message": message,
        "source": {
            "lookup_script": "msc_pl_lookup.py",
            "detail_script": "msc_khlcnt_detail.py",
            "detail_main_endpoint": URL_DETAIL_KHLCNT,
            "detail_bid_endpoint": URL_DETAIL_BID_KHLCNT,
            "plan_id": plan_id,
            "elapsed_ms": elapsed_ms,
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
