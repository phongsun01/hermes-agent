#!/usr/bin/env python3
"""Daily morning price report: Xăng (scrape webgia.com + fallback), Vàng SJC, Tỷ giá USD.
Chạy no-agent (script stdout), không cần LLM hay local gateway.
"""

import urllib.request, ssl, json, re, datetime, time, sys

MAX_RETRIES = 3
RETRY_DELAY = 5
SSL_CTX = ssl._create_unverified_context()


def fetch(url, headers=None, timeout=20):
    _h = {'User-Agent': 'Mozilla/5.0 (compatible; HermesBot/1.0)'}
    if headers:
        _h.update(headers)
    last_err = None
    for i in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=_h)
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            last_err = e
            if i < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise RuntimeError(f"{last_err}")


# ── 1. GIÁ VÀNG SJC ─────────────────────────────────────────────────────────

def _fetch_gia_vang_sjc_api():
    raw = fetch(
        'https://sjc.com.vn/GoldPrice/Services/PriceService.ashx',
        headers={'Referer': 'https://sjc.com.vn/'}
    )
    data = json.loads(raw)
    items = data.get('data', [])
    latest = data.get('latestDate', '')

    sjc_mien = next((x for x in items if '1L' in str(x.get('TypeName','')) or '1L, 10L' in str(x.get('TypeName',''))), None)
    nhan_9999 = next((x for x in items if 'nhẫn' in str(x.get('TypeName','')).lower() or '9999' in str(x.get('TypeName',''))), None)

    lines = [f"💰 **Giá vàng SJC** (cập nhật {latest}):"]
    if sjc_mien:
        lines.append(f"  • Vàng miếng 1L: Mua {sjc_mien['Buy']} / Bán {sjc_mien['Sell']} (nghìn đồng/lượng)")
    if nhan_9999:
        lines.append(f"  • Nhẫn 9999: Mua {nhan_9999['Buy']} / Bán {nhan_9999['Sell']} (nghìn đồng/lượng)")
    if not sjc_mien and not nhan_9999 and items:
        first = items[0]
        lines.append(f"  • {first.get('TypeName','')}: Mua {first.get('Buy','—')} / Bán {first.get('Sell','—')}")
    lines.append("  📌 Nguồn: SJC")
    return '\n'.join(lines)

def _fetch_gia_vang_vietnambiz():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    html = fetch('https://vietnambiz.vn/gia-vang-hom-nay.html', headers=headers, timeout=15)

    m_time = re.search(r'Cập nhật lúc:?\s*([\d/:\s]+)', html)
    update_time = m_time.group(1).strip() if m_time else ""

    trs = re.findall(r'<tr[^>]*>.*?</tr>', html, re.S)
    sjc_1l = None
    nhan_9999 = None
    for tr in trs:
        tds = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', tr, re.S)
        clean_tds = [_strip_tags(td) for td in tds]
        if len(clean_tds) >= 3:
            name = clean_tds[0]
            buy = clean_tds[1]
            sell = clean_tds[2]
            if ("1L" in name or "1l" in name or "10L" in name) and not sjc_1l:
                sjc_1l = (buy, sell)
            elif ("nhẫn" in name.lower() or "99,99%" in name or "9999" in name) and not nhan_9999:
                nhan_9999 = (buy, sell)

    if not sjc_1l and not nhan_9999:
        raise ValueError("Không parse được bảng giá vàng vietnambiz")

    lines = [f"💰 **Giá vàng SJC** (cập nhật {update_time or 'mới nhất'}):"]
    if sjc_1l:
        lines.append(f"  • Vàng miếng 1L: Mua {sjc_1l[0]} / Bán {sjc_1l[1]} (đ/lượng)")
    if nhan_9999:
        lines.append(f"  • Nhẫn 9999: Mua {nhan_9999[0]} / Bán {nhan_9999[1]} (đ/lượng)")
    lines.append("  📌 Nguồn: vietnambiz.vn / SJC")
    return '\n'.join(lines)

def get_gia_vang():
    # 1. Thử SJC API trực tiếp
    try:
        return _fetch_gia_vang_sjc_api()
    except Exception:
        pass

    # 2. Thử Vietnambiz fallback
    try:
        return _fetch_gia_vang_vietnambiz()
    except Exception as e:
        return f"💰 **Giá vàng SJC**: Không lấy được dữ liệu ({e})"


# ── 2. TỶ GIÁ USD (Vietcombank XML) ─────────────────────────────────────────

def get_ty_gia():
    try:
        raw = fetch('https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx?b=68')
        dt_m = re.search(r'<DateTime>([^<]+)</DateTime>', raw)
        dt_str = dt_m.group(1).strip() if dt_m else ''
        usd_m = re.search(r'CurrencyCode="USD"[^/]*Buy="([^"]+)"[^/]*Transfer="([^"]+)"[^/]*Sell="([^"]+)"', raw)
        if usd_m:
            buy, transfer, sell = usd_m.group(1), usd_m.group(2), usd_m.group(3)
            return (f"🏦 **Tỷ giá USD** (Vietcombank, {dt_str}):\n"
                     f"  • Mua: {buy} | Chuyển khoản: {transfer} | Bán: {sell} (VND)")
        return "🏦 **Tỷ giá USD**: Không parse được dữ liệu Vietcombank"
    except Exception as e:
        try:
            raw2 = fetch('https://open.er-api.com/v6/latest/USD', timeout=10)
            data = json.loads(raw2)
            rate = data.get('rates', {}).get('VND')
            if rate:
                return f"🏦 **Tỷ giá USD** (ExchangeRate):\n  • 1 USD ≈ {int(rate):,} VND"
        except Exception:
            pass
        return f"🏦 **Tỷ giá USD**: Không lấy được dữ liệu ({e})"


# ── 3. GIÁ XĂNG DẦU (scrape vietnambiz / webgia / pvoil / fallback) ────────────

GIA_XANG_FALLBACK = {
    "ngay_hieu_luc": "13/08/2026",
    "RON 95-III":    "22.110",
    "E5 RON 92":     "21.230",
    "Dầu diesel":    "27.230",
    "nguon":         "Bộ Công Thương / Tổng hợp điều hành giá (dữ liệu dự phòng)",
}

def _strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def _fetch_xang_vietnambiz():
    """Lấy giá xăng dầu từ vietnambiz.vn."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    html = fetch('https://vietnambiz.vn/gia-xang-dau-hom-nay.html', headers=headers, timeout=15)
    
    # Lấy thông tin thời gian điều chỉnh / cập nhật
    m_time = re.search(r"Giá điều chỉnh lúc\s*([\d:]+\s*ngày\s*[\d/]+)", html, re.I)
    effective_time = m_time.group(0).strip() if m_time else ""
    if not effective_time:
        m_up = re.search(r"Cập nhật lúc:?\s*([\d/:\s]+)", html, re.I)
        effective_time = m_up.group(0).strip() if m_up else "mới nhất"

    trs = re.findall(r"<tr[^>]*>.*?</tr>", html, re.S)
    items = []
    for tr in trs:
        tds = re.findall(r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", tr, re.S)
        clean_tds = [_strip_tags(td) for td in tds]
        if len(clean_tds) >= 3:
            product = clean_tds[1]
            price = clean_tds[2]
            change = clean_tds[3] if len(clean_tds) > 3 else ""
            if any(k in product.lower() for k in ["ron", "e5", "e10", "do", "dầu", "diesel"]):
                # Làm sạch giá nếu có chữ đ thừa
                clean_price = re.sub(r'[^\d\.,]', '', price).strip()
                if clean_price:
                    items.append({
                        "product": product,
                        "price": clean_price,
                        "change": change
                    })

    if not items:
        raise ValueError("Không parse được bảng giá vietnambiz")

    lines = [f"⛽ **Giá xăng dầu** ({effective_time}):"]
    for it in items:
        prod = it['product']
        price = it['price']
        change = it['change']
        change_str = f" ({change})" if change and change != '-' else ""
        lines.append(f"  • {prod}: {price} đ/lít{change_str}")
    lines.append("  📌 Nguồn: vietnambiz.vn (Tổng hợp điều hành giá)")
    return '\n'.join(lines)

def _fetch_xang_pvoil():
    """Lấy giá xăng dầu từ pvoil.com.vn."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    html = fetch('https://www.pvoil.com.vn/tin-gia-xang-dau', headers=headers, timeout=15)
    m_time = re.search(r"<strong>\s*(Giá điều chỉnh lúc[^<]+)</strong>", html, re.I)
    effective_time = _strip_tags(m_time.group(1)) if m_time else "PVOIL"

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S)
    items = []
    for row in rows:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(tds) < 3:
            continue
        product = _strip_tags(tds[1])
        price = _strip_tags(tds[2])
        change = _strip_tags(tds[3]) if len(tds) > 3 else ""
        if product and any(k in product.lower() for k in ["ron", "dầu", "do", "ko", "e5", "e10"]):
            clean_price = re.sub(r'[^\d\.,]', '', price).strip()
            if clean_price:
                items.append({"product": product, "price": clean_price, "change": change})

    if not items:
        raise ValueError("Không parse được bảng giá PVOIL")

    seen = set()
    uniq = []
    for it in items:
        k = it["product"].lower()
        if k not in seen:
            seen.add(k)
            uniq.append(it)

    lines = [f"⛽ **Giá xăng dầu** ({effective_time}):"]
    for it in uniq:
        prod = it['product']
        price = it['price']
        change = it['change']
        change_str = f" ({change})" if change and change != '-' else ""
        lines.append(f"  • {prod}: {price} đ/lít{change_str}")
    lines.append("  📌 Nguồn: pvoil.com.vn")
    return '\n'.join(lines)

def get_gia_xang():
    errors = []
    # 1. Thử Vietnambiz
    try:
        return _fetch_xang_vietnambiz()
    except Exception as e:
        errors.append(f"Vietnambiz: {e}")

    # 2. Thử PVOIL
    try:
        return _fetch_xang_pvoil()
    except Exception as e:
        errors.append(f"PVOIL: {e}")

    # 3. Fallback dữ liệu nội bộ
    g = GIA_XANG_FALLBACK
    err_str = "; ".join(errors)
    return (
        f"⛽ **Giá xăng dầu** (hiệu lực từ {g['ngay_hieu_luc']}):\n"
        f"  • RON 95-III: {g['RON 95-III']} đ/lít\n"
        f"  • E5 RON 92:  {g['E5 RON 92']} đ/lít\n"
        f"  • Dầu diesel: {g['Dầu diesel']} đ/lít\n"
        f"  📌 Nguồn: {g['nguon']}\n"
        f"  ⚠️ Lỗi khi lấy dữ liệu trực tuyến: {err_str}"
    )


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=["all", "vang", "xang", "tygia"], default="all")
    args = parser.parse_args()

    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if args.section == "all":
        print(f"📊 **Tổng hợp giá sáng** ({now})\n")
        print(get_gia_xang())
        print()
        print(get_gia_vang())
        print()
        print(get_ty_gia())
    elif args.section == "xang":
        print(get_gia_xang())
    elif args.section == "vang":
        print(get_gia_vang())
    elif args.section == "tygia":
        print(get_ty_gia())


if __name__ == "__main__":
    import argparse
    main()

