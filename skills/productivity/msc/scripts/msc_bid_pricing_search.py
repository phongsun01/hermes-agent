#!/usr/bin/env python3
import argparse
import json
import subprocess
from copy import deepcopy

BASE = "https://muasamcong.mpi.gov.vn"
ENDPOINT = "/o/egp-portal-personal-page/services/smart/search_prc"

TAB_PRESETS = {
    "hang_hoa": {
        "matchFields": ["danh_muc_hang_hoa", "ma_hs", "xuat_xu", "ma_tbmt", "ky_ma_hieu", "nhan_hieu", "hang_san_xuat"],
        "filters": [
            {"fieldName": "type", "searchType": "in", "fieldValues": ["HANG_HOA"]},
            {"fieldName": "tab", "searchType": "in", "fieldValues": ["HANG_HOA"]}
        ]
    },
    "thiet_bi_vat_tu_y_te": {
        "matchFields": ["ten_thiet_bi", "ma_hs", "xuat_xu", "ma_tbmt", "ky_ma_hieu", "nhan_hieu", "hang_san_xuat"],
        "filters": [
            {"fieldName": "type", "searchType": "in", "fieldValues": ["HANG_HOA"]},
            {"fieldName": "tab", "searchType": "in", "fieldValues": ["THIET_BI_VAT_TU_Y_TE"]}
        ]
    },
    "thuoc_generic": {
        "matchFields": ["ten_thuoc", "ten_hoat_chat", "ma_tbmt"],
        "filters": [
            {"fieldName": "medicines", "searchType": "in", "fieldValues": ["0"]},
            {"fieldName": "type", "searchType": "in", "fieldValues": ["HANG_HOA"]},
            {"fieldName": "tab", "searchType": "in", "fieldValues": ["THUOC_TAN_DUOC"]}
        ]
    },
    "thuoc_biet_duoc_goc": {
        "matchFields": ["ten_thuoc", "ten_hoat_chat", "ma_tbmt"],
        "filters": [
            {"fieldName": "medicines", "searchType": "in", "fieldValues": ["1"]},
            {"fieldName": "type", "searchType": "in", "fieldValues": ["HANG_HOA"]},
            {"fieldName": "tab", "searchType": "in", "fieldValues": ["THUOC_TAN_DUOC"]}
        ]
    },
    "thuoc_duoc_lieu": {
        "matchFields": ["ten_thuoc", "ten_hoat_chat", "ma_tbmt"],
        "filters": [
            {"fieldName": "medicines", "searchType": "in", "fieldValues": ["2"]},
            {"fieldName": "type", "searchType": "in", "fieldValues": ["HANG_HOA"]},
            {"fieldName": "tab", "searchType": "in", "fieldValues": ["THUOC_TAN_DUOC"]}
        ]
    },
    "duoc_lieu": {
        "matchFields": ["ten_duoc_lieu", "ten_khoa_hoc", "ten_san_pham", "ma_tbmt"],
        "filters": [
            {"fieldName": "medicine_type", "searchType": "in", "fieldValues": [0, None]},
            {"fieldName": "type", "searchType": "in", "fieldValues": ["HANG_HOA"]},
            {"fieldName": "tab", "searchType": "in", "fieldValues": ["DUOC_LIEU"]}
        ]
    },
    "vi_thuoc_co_truyen": {
        "matchFields": ["ten_duoc_lieu", "ten_khoa_hoc", "ten_san_pham", "ma_tbmt"],
        "filters": [
            {"fieldName": "medicine_type", "searchType": "in", "fieldValues": [0, None]},
            {"fieldName": "type", "searchType": "in", "fieldValues": ["HANG_HOA"]},
            {"fieldName": "tab", "searchType": "in", "fieldValues": ["VI_THUOC_CO_TRUYEN"]}
        ]
    },
}


def build_payload(tab_key: str, keyword: str, keyword_not: str = "", page_size: int = 20, page: int = 0):
    if tab_key not in TAB_PRESETS:
        raise ValueError(f"unknown tab key: {tab_key}")
    conf = deepcopy(TAB_PRESETS[tab_key])
    return [{
        "pageSize": page_size,
        "pageNumber": page,
        "query": [{
            "index": "es-smart-pricing",
            "keyWord": keyword,
            "keyWordNotMatch": keyword_not,
            "matchType": "all-1",
            "matchFields": conf["matchFields"],
            "filters": conf["filters"],
        }]
    }]


def run_search(base_url: str, cookie: str, payload):
    url = base_url.rstrip("/") + ENDPOINT
    body = json.dumps(payload, ensure_ascii=False)
    cmd = [
        "curl", "-sS", "-L", "--max-time", "60",
        "-H", "User-Agent: Mozilla/5.0",
        "-H", "Accept: application/json, text/plain, */*",
        "-H", "Content-Type: application/json",
        "-H", f"Origin: {base_url.rstrip('/')}",
        "-H", f"Referer: {base_url.rstrip('/')}/web/guest/profile-info",
    ]
    if cookie:
        cmd += ["-H", f"Cookie: {cookie}"]
    cmd += ["--data-raw", body, url]

    p = subprocess.run(cmd, capture_output=True, text=True, timeout=70)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f"curl failed: {p.returncode}")
    return p.stdout


def simplify(raw_json: str):
    data = json.loads(raw_json)
    content = (data.get("page") or {}).get("content") or []
    rows = []
    for x in content[:20]:
        name = (
            x.get("ten_thiet_bi") or x.get("tenThietBi") or
            x.get("ten_thuoc") or x.get("tenThuoc") or
            x.get("ten_duoc_lieu") or x.get("tenDuocLieu") or
            x.get("ten_san_pham") or x.get("tenSanPham") or
            x.get("bidName")
        )
        if isinstance(name, list):
            name = " | ".join(name)
        rows.append({
            "ma_tbmt": x.get("ma_tbmt") or x.get("maTbmt") or x.get("notifyNo"),
            "ten": name,
            "ky_ma_hieu": x.get("ky_ma_hieu") or x.get("kyMaHieu"),
            "nhan_hieu": x.get("nhan_hieu") or x.get("nhanHieu"),
            "hang_san_xuat": x.get("hang_san_xuat") or x.get("hangSanXuat"),
            "xuat_xu": x.get("xuat_xu") or x.get("xuatXu"),
            "don_gia": x.get("gia_tham_chieu") or x.get("don_gia") or x.get("donGia"),
            "ten_cdt": x.get("tenCdtBmt") or x.get("ten_cdt_bmt"),
            "thoi_gian_dang_tai_kqlcnt": x.get("ngayDangTaiKqlcnt") or x.get("ngay_dang_tai_kqlcnt")
        })
    return {
        "total": (data.get("page") or {}).get("totalElements", 0),
        "rows": rows
    }


def main():
    ap = argparse.ArgumentParser(description="Search MSC bid-pricing hidden API")
    ap.add_argument("--tab", required=True, choices=sorted(TAB_PRESETS.keys()))
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--keyword-not", default="")
    ap.add_argument("--cookie", default="", help="Optional session cookie header")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--page-size", type=int, default=20)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--print-payload-only", action="store_true")
    args = ap.parse_args()

    payload = build_payload(args.tab, args.keyword, args.keyword_not, args.page_size, args.page)
    if args.print_payload_only:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    raw = run_search(args.base, args.cookie, payload)
    try:
        simplified = simplify(raw)
        print(json.dumps({
            "endpoint": ENDPOINT,
            "tab": args.tab,
            "keyword": args.keyword,
            "payload": payload,
            "result": simplified
        }, ensure_ascii=False, indent=2))
    except Exception:
        low = (raw or '').lower()
        if '<html' in low or 'portal/login' in low or 'dang nhap' in low or 'đăng nhập' in low:
            print(json.dumps({
                "status": "login_error",
                "message": "lỗi login",
                "endpoint": ENDPOINT,
                "tab": args.tab,
                "keyword": args.keyword
            }, ensure_ascii=False, indent=2))
            return
        print(json.dumps({
            "endpoint": ENDPOINT,
            "tab": args.tab,
            "keyword": args.keyword,
            "payload": payload,
            "raw": raw[:2000]
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
