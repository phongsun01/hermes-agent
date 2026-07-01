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

def get_gia_vang():
    try:
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
        return '\n'.join(lines)
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


# ── 3. GIÁ XĂNG (scrape webgia.com, fallback hardcode) ─────────────────────

# Dữ liệu dự phòng khi không scrape được — cập nhật thủ công sau mỗi lần
# phát hiện scraper bị lỗi (đổi cấu trúc HTML, chặn IP, v.v.)
GIA_XANG_FALLBACK = {
    "ngay_hieu_luc": "26/06/2026",
    "ky_tiep_theo":  "06/07/2026",
    "RON 95-III":    "21,346",
    "E5 RON 92":     "20,888",
    "Dầu diesel":    "19,772",
    "nguon":         "Bộ Công Thương / Petrolimex (dữ liệu dự phòng, có thể lỗi thời)",
}

def _strip_tags(s):
    return re.sub(r'<[^>]+>', '', s).strip()

def _parse_webgia_table(html):
    """Parse bảng giá Petrolimex từ webgia.com. Trả về {tên_sp: (vùng1, vùng2)}."""
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    result = {}
    for row in rows:
        # Hỗ trợ cả thẻ <th> cho tên sản phẩm và <td> cho các cột giá
        cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row, re.S)
        if len(cells) < 3:
            continue
        name = _strip_tags(cells[0])
        v1 = _strip_tags(cells[1])
        v2 = _strip_tags(cells[2])
        if name:
            result[name] = (v1, v2)
    return result

def _find_update_time(html):
    m = re.search(r'[Cc]ập nhật[^0-9]*(\d{2}:\d{2}:\d{2}\s+\d{2}/\d{2}/\d{4})', html)
    return m.group(1) if m else ''

def get_gia_xang():
    try:
        html = fetch('https://webgia.com/gia-xang-dau/petrolimex/')
        table = _parse_webgia_table(html)
        update_time = _find_update_time(html)

        def find_price(*keywords):
            for name, (v1, v2) in table.items():
                if all(k.lower() in name.lower() for k in keywords):
                    price = v1 if v1 not in ('-', '', None) else v2
                    if price not in ('-', '', None):
                        return price
            return None

        # Hỗ trợ lấy giá theo từ khóa
        ron95 = find_price('RON', '95-III') or find_price('RON', '95-V')
        e5 = find_price('E5')
        diesel = find_price('DO', '0,05S') or find_price('DO', '0,001S') or find_price('diesel')

        if not any([ron95, e5, diesel]):
            raise ValueError("Không tìm thấy giá xăng dầu khả dụng trực tuyến")

        lines = [f"⛽ **Giá xăng dầu** (Petrolimex, cập nhật {update_time or 'mới nhất'}):"]
        if ron95:
            lines.append(f"  • RON 95-III: {ron95} đ/lít")
        if e5:
            lines.append(f"  • E5 RON 92:  {e5} đ/lít")
        if diesel:
            lines.append(f"  • Dầu diesel: {diesel} đ/lít")
        lines.append(f"  📌 Nguồn: webgia.com (tổng hợp từ Petrolimex)")
        return '\n'.join(lines)

    except Exception as e:
        g = GIA_XANG_FALLBACK
        return (
            f"⛽ **Giá xăng dầu** (hiệu lực từ {g['ngay_hieu_luc']}, kỳ tới ~{g['ky_tiep_theo']}):\n"
            f"  • RON 95-III: {g['RON 95-III']} đ/lít\n"
            f"  • E5 RON 92:  {g['E5 RON 92']} đ/lít\n"
            f"  • Dầu diesel: {g['Dầu diesel']} đ/lít\n"
            f"  📌 Nguồn: {g['nguon']}\n"
            f"  ⚠️ Lỗi khi lấy dữ liệu trực tuyến: {e}"
        )


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"📊 **Tổng hợp giá sáng** ({now})\n")
    print(get_gia_xang())
    print()
    print(get_gia_vang())
    print()
    print(get_ty_gia())


if __name__ == "__main__":
    main()
