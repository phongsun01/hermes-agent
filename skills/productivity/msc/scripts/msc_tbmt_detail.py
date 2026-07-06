#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

LOOKUP_SCRIPT = "scripts/msc_ib_lookup.py"
BASE = "https://muasamcong.mpi.gov.vn"

# Tab 1: Thông báo mời thầu
URL_DETAIL_TBMT_LDT = "/o/egp-portal-contractor-selection-v2/services/expose/lcnt/bid-po-bido-notify-contractor-view/get-by-id"

# Tab 2: Biên bản mở thầu
URL_NOTIFY_KQMT_LDT = "/o/egp-portal-contractor-selection-v2/services/exposeldtkqmt/bid-notification-p/notify"
URL_ROUNDMNG_KQMT_LDT = "/o/egp-portal-contractor-selection-v2/services/expose/ldtkqmt/bid-notification-p/roundmng"
URL_BIDOPEN_KQMT_LDT = "/o/egp-portal-contractor-selection-v2/services/expose/ldtkqmt/bid-notification-p/bid-open"
URL_LOTOPEN_KQMT_LDT = "/o/egp-portal-contractor-selection-v2/services/expose/ldtkqmt/bid-notification-p/lot-open"
URL_LOTOPEN_DETAIL_KQMT_LDT = "/o/egp-portal-contractor-selection-v2/services/expose/ldtkqmt/bid-notification-p/lotOpenDetail"

# Tab 3: Kết quả lựa chọn nhà thầu
URL_DETAIL_KQLCNT_LDT = "/o/egp-portal-contractor-selection-v2/services/expose/contractor-input-result/get"
URL_DETAIL_KQLCNT_LDT_BY_BID = "/o/egp-portal-contractor-selection-v2/services/expose/contractor-input-result/get-by-bid-id"


def log(msg: str, **meta):
    payload = {"msg": msg, **meta}
    print(f"[msc_tbmt_detail] {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr)


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
    return s


def as_date_vi(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    s2 = s.replace("Z", "")
    if "." in s2:
        s2 = s2.split(".", 1)[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s2[:19] if 'T' in s2 or ' ' in s2 else s2[:10], fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
    return s[:10] if len(s) >= 10 else s


def map_bid_form(code: Any) -> str:
    m = {
        "CHCT": "Chỉ định thầu",
        "CHCTRG": "Chỉ định thầu rút gọn",
        "CDTRG": "Chỉ định thầu rút gọn",
        "CDT": "Chỉ định thầu",
        "DTRR": "Đấu thầu rộng rãi",
        "DTHC": "Đấu thầu hạn chế",
        "MSTT": "Mua sắm trực tiếp",
        "CGTT": "Chào giá trực tuyến",
        "CGTTRG": "Chào giá trực tuyến rút gọn",
        "CHHG": "Chào hàng cạnh tranh",
        "CHCTTT": "Chỉ định thầu thông thường",
        "TL": "Tự thực hiện",
        "LCDB": "Lựa chọn đặc biệt",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def map_bid_mode(code: Any) -> str:
    m = {
        "1_MTHS": "Một giai đoạn một túi hồ sơ",
        "1_HS": "Một giai đoạn một túi hồ sơ",
        "1_HTHS": "Một giai đoạn hai túi hồ sơ",
        "2_GD": "Hai giai đoạn",
        "2_MTHS": "Hai giai đoạn một túi hồ sơ",
        "2_HTHS": "Hai giai đoạn hai túi hồ sơ",
        "MOT_GIAI_DOAN_MOT_TUI_HO_SO": "Một giai đoạn một túi hồ sơ",
        "MOT_GIAI_DOAN_HAI_TUI_HO_SO": "Một giai đoạn hai túi hồ sơ",
        "HAI_GIAI_DOAN": "Hai giai đoạn",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def map_plan_type(code: Any) -> str:
    m = {
        "TX": "Chi thường xuyên",
        "DT": "Chi đầu tư",
        "DTPT": "Đầu tư phát triển",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def map_bid_field(code: Any) -> str:
    m = {
        "HH": "Hàng hóa",
        "XL": "Xây lắp",
        "TV": "Tư vấn",
        "PTV": "Phi tư vấn",
        "PHI_TV": "Phi tư vấn",
        "HON_HOP": "Hỗn hợp",
    }
    s = as_text(code).strip().upper()
    return m.get(s, as_text(code))


def run_lookup(token: str, ib: str, cookie: str = "") -> Dict[str, Any]:
    cmd = ["python3", LOOKUP_SCRIPT, "--token", token, "--ib", ib]
    if cookie:
        cmd += ["--cookie", cookie]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=80)
    raw = (p.stdout or "").strip()
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {"status": "error", "message": "invalid_lookup_output", "raw": raw[:500]}


def curl_json_with_retry(path: str, token: str, payload: Dict[str, Any], cookie: str = "", retries: int = 2, timeout_sec: int = 60, use_token_query: bool = True) -> Dict[str, Any]:
    url = f"{BASE}{path}"
    if use_token_query:
        url = f"{url}?token={token}"

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


def build_payload_notify(r: Dict[str, Any]) -> Dict[str, Any]:
    bid_mode = as_text(r.get("bidMode") or "")
    return {
        "notifyNo": r.get("notifyNo"),
        "notifyId": r.get("notifyId"),
        "type": "TBMT",
        "packType": 0 if bid_mode == "1_MTHS" else 1,
    }


def adapt_tab_tender_notice(lookup_res: Dict[str, Any], tbmt_detail: Dict[str, Any], kqlcnt_obj: Any = None) -> Dict[str, Any]:
    r = (lookup_res or {}).get("result") or {}
    m = (tbmt_detail or {}).get("bidoNotifyContractorM") or {}

    bid_name = m.get("bidName")
    if isinstance(bid_name, list):
        bid_name = " | ".join(str(x) for x in bid_name)

    bid_form_raw = as_text(first_non_empty(m.get("bidForm"), r.get("bidForm"), "")).strip().upper()
    bid_mode_raw = as_text(first_non_empty(m.get("bidMode"), r.get("bidMode"), "")).strip().upper()

    mode_text = map_bid_mode(bid_mode_raw) if bid_mode_raw else ""
    # Nhóm chào giá trực tuyến/chào hàng cạnh tranh: phương thức để trống theo yêu cầu nghiệp vụ
    if bid_form_raw in {"CGTTRG", "CGTT", "CHHG"}:
        mode_text = ""

    kql_main = (kqlcnt_obj or {}).get("bideContractorInputResultDTO") if isinstance(kqlcnt_obj, dict) else {}

    out = {
        "Số TBMT": as_text(first_non_empty(m.get("notifyNo"), r.get("notifyNo"), "")),
        "Tên gói thầu": as_text(first_non_empty(bid_name, r.get("name"), "")),
        "Dự án/KHLCNT": as_text(first_non_empty(m.get("planNo"), r.get("planNo"), "")),
        "Chủ đầu tư": as_text(first_non_empty(m.get("investorName"), r.get("unit"), "")),
        "Lĩnh vực": map_bid_field(first_non_empty(m.get("investField"), m.get("bidField"), r.get("bidField"), (kql_main or {}).get("bidField"), "")),
        "Phân loại": map_plan_type(first_non_empty(m.get("planType"), r.get("planType"), (kql_main or {}).get("planType"), "")),
        "Hình thức lựa chọn nhà thầu": map_bid_form(bid_form_raw),
        "Phương thức lựa chọn": mode_text,
        "Giá gói thầu": as_money(first_non_empty(m.get("bidPrice"), r.get("bidPrice")), "VND"),
        "Thời điểm đóng thầu": as_datetime_vi(first_non_empty(m.get("bidCloseDate"), r.get("closeDate"), "")),
        "Thời điểm mở thầu": as_datetime_vi(first_non_empty(m.get("bidOpenDate"), r.get("bidOpenDate"), "")),
        "Ngày đăng tải": as_datetime_vi(first_non_empty(m.get("publicDate"), r.get("publicDate"), "")),
    }

    # Thông tin gia hạn (nếu có)
    bid_notification = ((tbmt_detail or {}).get("bidNoContractorResponse") or {}).get("bidNotification") or {}
    delay_list = bid_notification.get("delayDTOList") or m.get("delayDTOList") or []
    if isinstance(delay_list, list) and delay_list:
        d0 = delay_list[0] if isinstance(delay_list[0], dict) else {}
        out.update({
            "Gia hạn - STT": "Lần 1",
            "Gia hạn - Thời điểm gia hạn thành công": as_datetime_vi(first_non_empty(d0.get("createdDate"), "")),
            "Gia hạn - Thời điểm đóng thầu cũ": as_datetime_vi(first_non_empty(d0.get("bidCloseDate"), "")),
            "Gia hạn - Thời điểm đóng thầu sau gia hạn": as_datetime_vi(first_non_empty(d0.get("bidCloseDelayDate"), "")),
        })

    return out


def adapt_tab_bid_opening_minutes(round_mng: Dict[str, Any], bid_open: Dict[str, Any], lot_open: Any, lot_open_detail: Any) -> Dict[str, Any]:
    r1 = (round_mng or {}).get("bidoBidroundMngViewDTO") or {}
    r2 = ((bid_open or {}).get("bidSubmissionByContractorViewResponse") or {})
    bids = r2.get("bidSubmissionDTOList") or []

    bid_list = r2.get("bidSubmissionDTOList") or []
    first_bid = bid_list[0] if isinstance(bid_list, list) and bid_list and isinstance(bid_list[0], dict) else {}

    opening_time = first_non_empty(
        r1.get("bidOpenDate"),
        r1.get("openTime"),
        r2.get("bidOpenDate"),
        r2.get("openDate"),
        first_bid.get("createdDateBidOpen"),
        "",
    )
    bidder_count = len(bids) if isinstance(bids, list) else 0

    names: List[str] = []
    for x in bids if isinstance(bids, list) else []:
        if not isinstance(x, dict):
            continue
        # Ưu tiên ventureName (liên danh) thay vì contractorName đứng đầu
        n = first_non_empty(x.get("ventureName"), x.get("contractorName"), "")
        if n:
            names.append(as_text(n))

    names = _uniq_keep_order(names)

    return {
        "Thời điểm mở thầu": as_datetime_vi(opening_time),
        "Số nhà thầu tham dự": as_text(first_non_empty(r1.get("numBidderJoin"), bidder_count, "")),
        "Danh sách nhà thầu": as_text(", ".join(names)),
    }


def _collect_kqlcnt_rows(kqlcnt_obj: Any) -> List[Dict[str, Any]]:
    """Normalize contractor selection results.

    Business rule update:
    - Nếu là liên danh (ventureName/ventureCode có dữ liệu), gom thành 1 dòng kết quả liên danh,
      kèm danh sách mã định danh thành viên.
    """
    rows: List[Dict[str, Any]] = []

    if not isinstance(kqlcnt_obj, dict):
        return rows

    main = (kqlcnt_obj.get("bideContractorInputResultDTO") or {}) if isinstance(kqlcnt_obj, dict) else {}

    # Preferred source: lotResultDTO[].contractorList[]
    lot_results = main.get("lotResultDTO") or []
    if isinstance(lot_results, list):
        for lot in lot_results:
            if not isinstance(lot, dict):
                continue
            contractors = lot.get("contractorList") or []
            if isinstance(contractors, list) and contractors:
                venture_name = as_text(first_non_empty(lot.get("ventureName"), "")).strip()
                if not venture_name:
                    for c in contractors:
                        if isinstance(c, dict) and c.get("ventureName"):
                            venture_name = as_text(c.get("ventureName")).strip()
                            break

                # Liên danh: gộp về 1 dòng
                if venture_name:
                    member_codes: List[str] = []
                    member_names: List[str] = []
                    winning_price = None
                    venture_code = ""
                    for c in contractors:
                        if not isinstance(c, dict):
                            continue
                        code = as_text(first_non_empty(c.get("orgCode"), c.get("taxCode"), "")).strip()
                        if code:
                            if code.lower().startswith("vn"):
                                code = code.lower()
                            elif code.isdigit():
                                code = f"vn{code}"
                            member_codes.append(code)
                        nm = as_text(first_non_empty(c.get("orgFullname"), c.get("newContractorName"), c.get("contractorName"), "")).strip()
                        if nm:
                            member_names.append(nm)
                        if winning_price is None:
                            winning_price = first_non_empty(c.get("bidWiningPrice"), c.get("lotFinalPrice"), c.get("lotPrice"))
                        if not venture_code:
                            venture_code = as_text(first_non_empty(c.get("ventureCode"), lot.get("ventureCode"), "")).strip()

                    rows.append({
                        "contractorName": venture_name,
                        "winningPrice": winning_price,
                        "taxCode": "; ".join(_uniq_keep_order(member_codes)),
                        "memberNames": "; ".join(_uniq_keep_order(member_names)),
                        "isVenture": True,
                        "ventureCode": venture_code,
                        "decisionDate": main.get("decisionDate"),
                    })
                else:
                    # Không liên danh: giữ row-per-contractor như cũ
                    for c in contractors:
                        if not isinstance(c, dict):
                            continue
                        rows.append({
                            "contractorName": first_non_empty(c.get("orgFullname"), c.get("newContractorName"), c.get("contractorName")),
                            "winningPrice": first_non_empty(c.get("bidWiningPrice"), c.get("lotFinalPrice"), c.get("lotPrice")),
                            "taxCode": first_non_empty(c.get("taxCode"), c.get("orgCode"), c.get("winningCode")),
                            "decisionDate": main.get("decisionDate"),
                        })

    # Fallback: contractorList at root/main level
    if not rows:
        fallback_contractors = main.get("contractorList") or kqlcnt_obj.get("contractorList") or []
        if isinstance(fallback_contractors, list):
            for c in fallback_contractors:
                if not isinstance(c, dict):
                    continue
                rows.append({
                    "contractorName": first_non_empty(c.get("orgFullname"), c.get("newContractorName"), c.get("contractorName")),
                    "winningPrice": first_non_empty(c.get("bidWiningPrice"), c.get("lotFinalPrice"), c.get("lotPrice")),
                    "taxCode": first_non_empty(c.get("taxCode"), c.get("orgCode"), c.get("winningCode")),
                    "decisionDate": main.get("decisionDate"),
                })

    # Final fallback: still output one row with decision info if available
    if not rows and main:
        rows.append({
            "contractorName": "",
            "winningPrice": None,
            "taxCode": "",
            "decisionDate": main.get("decisionDate"),
        })

    return rows


def _uniq_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in items:
        k = x.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
    return out


def _brand_hint(name: str) -> str:
    s = (name or "").strip()
    up = s.upper()
    prefixes = [
        "CÔNG TY TNHH MTV ",
        "CÔNG TY TNHH MỘT THÀNH VIÊN ",
        "CÔNG TY TNHH ",
        "CÔNG TY CỔ PHẦN ",
        "CONG TY TNHH MTV ",
        "CONG TY TNHH ",
        "CONG TY CO PHAN ",
    ]
    for p in prefixes:
        if up.startswith(p):
            s = s[len(p):].strip()
            break

    stop = {"CÔNG", "NGHỆ", "VIỆT", "NAM", "GIẢI", "PHÁP", "THƯƠNG", "MẠI", "DỊCH", "VỤ"}

    # ưu tiên lấy từ khóa thương hiệu viết hoa trong tên, bỏ stopword phổ biến
    tokens = [t for t in s.replace("-", " ").split() if t]
    for t in tokens:
        t_up = t.upper()
        if len(t_up) >= 4 and t_up == t and t_up.isalpha() and t_up not in stop:
            return t.title()

    # fallback lấy 2 từ cuối
    parts = s.split()
    if len(parts) >= 2:
        return " ".join(parts[-2:])
    return s


def adapt_tab_kqlcnt(lookup_res: Dict[str, Any], kqlcnt_obj: Any) -> Dict[str, Any]:
    main = (kqlcnt_obj.get("bideContractorInputResultDTO") or {}) if isinstance(kqlcnt_obj, dict) else {}
    rows = _collect_kqlcnt_rows(kqlcnt_obj)

    winners: List[Dict[str, Any]] = []
    for i, x in enumerate(rows, 1):
        row = {
            "STT": i,
            "Nhà thầu trúng": as_text(first_non_empty(x.get("contractorName"), "")),
            "Giá trúng thầu": as_money(first_non_empty(x.get("winningPrice"), None), "VND") if first_non_empty(x.get("winningPrice"), None) is not None else "",
            "Mã số thuế/Định danh": as_text(first_non_empty(x.get("taxCode"), "")),
        }
        if x.get("isVenture"):
            row["Loại"] = "Liên danh"
            row["Mã liên danh"] = as_text(first_non_empty(x.get("ventureCode"), ""))
            row["Danh sách thành viên"] = as_text(first_non_empty(x.get("memberNames"), ""))
        winners.append(row)

    is_venture = any(bool(x.get("isVenture")) for x in rows)
    member_count = 0
    if is_venture and rows:
        codes = as_text(first_non_empty(rows[0].get("taxCode"), ""))
        member_count = len([x for x in [c.strip() for c in codes.split(";")] if x])
    else:
        member_count = len(winners)

    return {
        "thong_tin_chung": {
            "Ngày đăng tải": as_datetime_vi(first_non_empty(main.get("publicDate"), "")),
            "Ngày phê duyệt": as_date_vi(first_non_empty(main.get("decisionDate"), "")),
            "Số quyết định phê duyệt": as_text(first_non_empty(main.get("decisionNo"), "")),
        },
        "danh_sach_nha_thau_trung": winners,
        "thanh_vien_count": member_count,
        "la_lien_danh": is_venture,
    }


def main():
    ap = argparse.ArgumentParser(description="Get TBMT detail (v3 IB real API adapter)")
    ap.add_argument("--ib", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--cookie", default="")
    args = ap.parse_args()

    ib = (args.ib or "").strip().upper()
    if re.fullmatch(r"IB\d{8,}", ib) is None:
        print(json.dumps({"status": "invalid_ib", "message": "Usage: /expt IBxxxxxxxx"}, ensure_ascii=False))
        return

    lookup = run_lookup(args.token, ib, cookie=args.cookie)
    st = lookup.get("status")

    if st == "invalid_ib":
        print(json.dumps({"status": "invalid_ib", "message": "Usage: /expt IBxxxxxxxx"}, ensure_ascii=False))
        return
    if st == "not_found":
        print(json.dumps({"status": "not_found", "message": "Không tìm thấy mã IB."}, ensure_ascii=False))
        return
    if st != "ok":
        print(json.dumps({"status": "login_error", "message": "lỗi login", "lookup": lookup}, ensure_ascii=False))
        return

    result = lookup.get("result") or {}
    notify_id = as_text(first_non_empty(result.get("notifyId"), result.get("id")))
    input_result_id = as_text(first_non_empty(result.get("inputResultId"), ""))
    bid_id = as_text(first_non_empty(result.get("bidId"), ""))

    if not notify_id:
        print(json.dumps({"status": "not_found", "message": "Không tìm thấy mã IB."}, ensure_ascii=False))
        return

    payload_notify = build_payload_notify(result)

    t0 = time.time()
    # Tab 1
    tbmt_detail = curl_json_with_retry(URL_DETAIL_TBMT_LDT, args.token, {"id": notify_id}, cookie=args.cookie)

    # Tab 2
    kqmt_notify = curl_json_with_retry(URL_NOTIFY_KQMT_LDT, args.token, payload_notify, cookie=args.cookie, use_token_query=False)
    kqmt_roundmng = curl_json_with_retry(URL_ROUNDMNG_KQMT_LDT, args.token, payload_notify, cookie=args.cookie, use_token_query=False)
    kqmt_bidopen = curl_json_with_retry(URL_BIDOPEN_KQMT_LDT, args.token, payload_notify, cookie=args.cookie)
    kqmt_lotopen = curl_json_with_retry(URL_LOTOPEN_KQMT_LDT, args.token, payload_notify, cookie=args.cookie)
    kqmt_lotopen_detail = curl_json_with_retry(URL_LOTOPEN_DETAIL_KQMT_LDT, args.token, payload_notify, cookie=args.cookie)

    # Tab 3
    kqlcnt = {}
    if input_result_id:
        kqlcnt = curl_json_with_retry(URL_DETAIL_KQLCNT_LDT, args.token, {"id": input_result_id}, cookie=args.cookie)

    # fallback by bid id when needed
    if (not kqlcnt or (isinstance(kqlcnt, dict) and kqlcnt.get("_error"))) and bid_id:
        kqlcnt = curl_json_with_retry(URL_DETAIL_KQLCNT_LDT_BY_BID, args.token, {"id": bid_id}, cookie=args.cookie, use_token_query=False)

    elapsed_ms = int((time.time() - t0) * 1000)

    # guard checks
    all_objs = [tbmt_detail, kqmt_notify, kqmt_roundmng, kqmt_bidopen, kqmt_lotopen, kqmt_lotopen_detail, kqlcnt]
    if any(is_guard_number_response(x) for x in all_objs):
        print(json.dumps({"status": "login_error", "message": "lỗi login", "guard": True}, ensure_ascii=False))
        return

    if all(isinstance(x, dict) and x.get("_error") for x in [tbmt_detail, kqmt_roundmng, kqmt_bidopen, kqlcnt]):
        print(json.dumps({"status": "login_error", "message": "lỗi gọi detail API"}, ensure_ascii=False))
        return

    tab1 = adapt_tab_tender_notice(lookup, tbmt_detail if isinstance(tbmt_detail, dict) else {}, kqlcnt if isinstance(kqlcnt, dict) else {})
    tab2 = adapt_tab_bid_opening_minutes(
        kqmt_roundmng if isinstance(kqmt_roundmng, dict) else {},
        kqmt_bidopen if isinstance(kqmt_bidopen, dict) else {},
        kqmt_lotopen,
        kqmt_lotopen_detail,
    )
    tab3 = adapt_tab_kqlcnt(lookup, kqlcnt)

    out = {
        "status": "ok",
        "ib": ib,
        "tabs": {
            "thong_bao_moi_thau": tab1,
            "bien_ban_mo_thau": tab2,
            "ket_qua_lua_chon_nha_thau": tab3,
        },
        "message": "Đã lấy dữ liệu 3 tab từ API thật.",
        "source": {
            "lookup_script": "msc_ib_lookup.py",
            "detail_script": "msc_tbmt_detail.py",
            "notify_id": notify_id,
            "input_result_id": input_result_id,
            "elapsed_ms": elapsed_ms,
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
