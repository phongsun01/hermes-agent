#!/usr/bin/env python3
"""
Script tự động kiểm tra công văn đến trên congchuc.quangninh.gov.vn
Chạy mỗi 1 tiếng để kiểm tra văn bản đến mới và thông báo qua Zalo/Telegram.
"""

import sys
import threading
import time as _time

import re
import json
import os
import io
import zipfile
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import ssl
import datetime
from html.parser import HTMLParser

# Conditional playwright import
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# === CONFIG ===
_hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
_env_path = os.path.join(_hermes_home, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

USERNAME = os.environ.get("CONGVAN_USER", "")
PASSWORD = os.environ.get("CONGVAN_PASS", "")
DOCS_URL = os.environ.get("CONGVAN_URL", "https://congchuc.quangninh.gov.vn/Default.aspx?tabid=1126")
if "/Default.aspx" in DOCS_URL:
    BASE_URL = DOCS_URL.split("/Default.aspx")[0]
else:
    BASE_URL = DOCS_URL.rstrip("/")
LOGIN_URL = BASE_URL + "/SSO/Login.aspx"

# State directory
STATE_DIR = os.path.join(_hermes_home, "cron", "cong-van-den")
STATE_FILE = os.path.join(STATE_DIR, "vbden_state.json")
STORAGE_STATE_FILE = os.path.join(STATE_DIR, ".playwright_storage.json")

# Unit selection — hỗ trợ nhiều đơn vị cách nhau bằng dấu phẩy
# Mỗi entry có thể là ID số (ví dụ "2256") hoặc substring tên (ví dụ "Sản nhi")
CONGVAN_UNIT_RAW = os.environ.get("CONGVAN_UNIT", "").strip()
UNITS = [u.strip() for u in CONGVAN_UNIT_RAW.split(",") if u.strip()]
MAX_ATTACHMENT_DOCS = int(os.environ.get("CONGVAN_MAX_ATTACHMENT_DOCS", "10"))
SCRIPT_TIMEOUT = int(os.environ.get("CONGVAN_SCRIPT_TIMEOUT", "600"))
CONGVAN_FULLNAME = os.environ.get("CONGVAN_FULLNAME", "Nguyễn Huy Phong")

def _time_remaining():
    return SCRIPT_TIMEOUT - (_time.monotonic() - _script_start_time)

# === SSL CONTEXT ===
ssl_ctx = ssl.create_default_context()
ssl_ctx.set_ciphers('DEFAULT:@SECLEVEL=0')

# === COOKIE JAR ===
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPSHandler(context=ssl_ctx)
)
opener.addheaders = [
    ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
    ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
]


def html_unescape(s):
    s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    s = s.replace('&quot;', '"').replace('&apos;', "'")
    s = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), s)
    return s


def strip_tags(html_text):
    """Strip HTML tags, keeping text content."""
    clean = re.sub(r'<[^>]+>', ' ', html_text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return html_unescape(clean)


def get_page(url, data=None, referer=None):
    """Fetch a page with optional POST data."""
    headers = {}
    if referer:
        headers['Referer'] = referer
    if data:
        data = urllib.parse.urlencode(data).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        resp = opener.open(req, timeout=30)
        html = resp.read().decode('utf-8', errors='replace')
        return html, resp.geturl()
    except urllib.error.HTTPError as e:
        html = e.read().decode('utf-8', errors='replace')
        return html, url
    except Exception as e:
        return None, str(e)


def extract_form_fields(html):
    """Extract ASP.NET form hidden fields."""
    fields = {}
    # Match inputs with value attribute
    for m in re.finditer(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html):
        fields[m.group(1)] = m.group(2)
    # Also match inputs without value attribute (empty value)
    for m in re.finditer(r'<input[^>]*name="([^"]+)"[^>]*/?>', html):
        name = m.group(1)
        if name not in fields:
            fields[name] = ''
    return fields


def extract_dropdown_options(html, dropdown_id):
    """Extract options from a <select> element by id."""
    pattern = rf'<select[^>]*id="{re.escape(dropdown_id)}"[^>]*>(.*?)</select>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return []
    options = []
    for m in re.finditer(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', match.group(1), re.DOTALL):
        options.append((m.group(1), strip_tags(m.group(2)).strip()))
    return options


def select_unit(target_unit_id=None, target_unit_name=None):
    """Select the target unit from the dnn_banner_ddlChonDonVi dropdown.
    Flow: GET tabid=56 → POST with unit selection → GET tabid=1135 for docs.
    Returns (success, message, documents_or_None).
    If target_unit_id is set (numeric), use it directly. Otherwise match by name substring."""
    if not target_unit_id and not target_unit_name:
        return True, "No target unit configured, skipping selection", None

    # Step 1: Navigate to the main page (tabid=56) where the dropdown lives
    main_url = BASE_URL + "/Default.aspx?tabid=56"
    html, url = get_page(main_url)
    if html is None:
        return False, f"Không thể tải trang chủ: {url}", None

    # Find the dropdown and its options
    options = extract_dropdown_options(html, "dnn_banner_ddlChonDonVi")
    if not options:
        for alt_id in ["ddlChonDonVi", "dnn_ctrBanner_ddlChonDonVi", "ctl00_ddlChonDonVi"]:
            options = extract_dropdown_options(html, alt_id)
            if options:
                break

    if not options:
        return False, "Không tìm thấy dropdown chọn đơn vị", None

    # Find the target unit value
    target_value = None
    available = []
    for val, label in options:
        available.append(label)
        # Priority: exact ID match > name substring match
        if target_unit_id and val == target_unit_id:
            target_value = val
        elif target_unit_name and target_unit_name.lower() in label.lower():
            target_value = val

    if target_value is None:
        return False, f"Không tìm thấy đơn vị (id={target_unit_id}, name={target_unit_name}). Có sẵn: {', '.join(available[:5])}...", None

    # Step 2: ASP.NET postback to select the unit
    fields = extract_form_fields(html)
    fields.update({
        '__EVENTTARGET': 'dnn$banner$ddlChonDonVi',
        '__EVENTARGUMENT': '',
        '__LASTFOCUS': '',
        'dnn$banner$ddlChonDonVi': target_value,
    })

    html2, url2 = get_page(url, data=fields, referer=url)
    if html2 is None:
        return False, f"Lỗi khi chọn đơn vị: {url2}", None

    # Step 3: Navigate to documents page (tabid=1126) to get docs for selected unit
    html3, url3 = get_page(DOCS_URL, referer=url2)
    if html3 is None:
        return False, f"Không thể tải trang documents sau khi chọn đơn vị: {url3}", None

    docs_after = extract_documents(html3)
    if docs_after:
        first_tac_gia = docs_after[0].get('tac_gia', 'unknown')
        print(f"[INFO] Unit select done: {len(docs_after)} docs, first tac_gia={first_tac_gia}", file=sys.stderr)
        return True, f"Đã chọn đơn vị: {target_unit_name}", docs_after

    return True, f"Đã submit chọn đơn vị (tại {url3})", None


def login():
    """Login to the portal, return (success, message)."""
    html, url = get_page(LOGIN_URL)
    if html is None:
        return False, f"Không thể kết nối: {url}"

    fields = extract_form_fields(html)

    fields.update({
        'IDToken1': USERNAME,
        'IDToken2': PASSWORD,
        'ctlCaptcha$CaptchaTextBox': '',
        'ctlCaptcha_ClientState': '',
        '__LASTFOCUS': '',
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATEENCRYPTED': '',
    })

    html2, url2 = get_page(LOGIN_URL, data=fields, referer=LOGIN_URL)
    if html2 is None:
        return False, f"Login connection error: {url2}"

    # Password warning page: click "Tiếp tục"
    if 'Kính chào' in html2 and 'TIẾP TỤC' in html2:
        fields2 = extract_form_fields(html2)
        # The Tiếp tục button name - look for it
        for m in re.finditer(r'<input[^>]*value="TIẾP TỤC"[^>]*name="([^"]+)"', html2):
            fields2[m.group(1)] = 'TIẾP TỤC'
            break
        fields2['IDToken1'] = USERNAME
        fields2['IDToken2'] = PASSWORD
        fields2['ctlCaptcha$CaptchaTextBox'] = ''
        fields2['ctlCaptcha_ClientState'] = ''
        fields2['__LASTFOCUS'] = ''
        fields2['__EVENTTARGET'] = ''
        fields2['__EVENTARGUMENT'] = ''
        fields2['__VIEWSTATEENCRYPTED'] = ''

        html3, url3 = get_page(url2, data=fields2, referer=url2)
        if html3 is None:
            return False, f"Password warning page failed"
        if 'Nguyễn Huy Phong' in html3 or 'tabid=56' in url3:
            return True, "Đăng nhập thành công"
        return True, f"Đã xử lý password warning, tại {url3}"

    # Direct success
    if 'Nguyễn Huy Phong' in html2 or 'tabid=' in url2:
        return True, "Đăng nhập thành công"

    # Check error
    error_match = re.search(r'<span[^>]*id="lblError"[^>]*>([^<]*)</span>', html2)
    if error_match and error_match.group(1).strip():
        return False, f"Lỗi: {error_match.group(1).strip()}"
    if 'unexpected error' in html2.lower() or 'unexpected' in url2.lower():
        return False, "Lỗi đăng nhập: unexpected error (có thể captcha)"
    
    return False, "Đăng nhập thất bại"


def extract_urgency(row_html):
    """Extract urgency level from lblDoKhan span in the row."""
    m = re.search(r'id="[^"]*lblDoKhan"[^>]*>([^<]*)', row_html)
    if m:
        text = m.group(1).strip()
        if text:
            return text
    # Fallback: check for colored text or class indicating urgency
    color_m = re.search(r'color:\s*red[^>]*>([^<]+)', row_html)
    if color_m:
        return color_m.group(1).strip()
    return "Thường"


def extract_but_phe(row_html):
    """Extract bút phê from showToolTip in the row.
    Handles both 'Bút phê:' and 'Thông tin xử lý:' tooltips."""
    # Find all showToolTip calls in the row
    for m in re.finditer(r"showToolTip\(this,'([^']*)'", row_html):
        raw = m.group(1)
        # Unescape HTML entities
        raw = raw.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('<br>', '\n').replace('<br/>', '\n')
        # Look for Bút phê content in brackets
        bp = re.search(r'\[Bút phê:\s*(.*?)\]', raw, re.DOTALL)
        if bp:
            return bp.group(1).strip()
        # Look for "Thông tin xử lý" content
        if 'Thông tin xử lý' in raw or 'Bút phê' in raw:
            # Extract the actual message (after any timestamp/name prefix)
            content = re.sub(r'-{2,}\[.*?\]-{2,}', '', raw).strip()
            content = re.sub(r'^[\n\s]+', '', content)
            if content:
                return content
    return ""


def extract_pager_info(html):
    """Extract pagination info and __doPostBack targets from RadGrid HTML.
    Returns (current_page, total_pages_str, page_buttons_dict, total_records).
    """
    # Find all page number <a> tags in the numeric pager section
    pager_num = re.search(r'class="[^"]*rgNumPart[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if not pager_num:
        return None, None, {}, 0

    buttons = {}
    current_page = 1
    for a in re.findall(r'<a[^>]*href="javascript:__doPostBack\(&?#39;([^&]+)&?#39;,&?#39;([^&]*)&?#39;\)"[^>]*>\s*<span>(\d+)</span>\s*</a>', pager_num.group(0)):
        target, arg, page_num = a
        buttons[page_num] = target
        # rgCurrentPage = the active/current page
    # Find current page
    cur = re.search(r'class="rgCurrentPage"[^>]*>\s*<span>(\d+)</span>', pager_num.group(0))
    if cur:
        current_page = int(cur.group(1))

    # Also detect total pages and visible text
    pager_text = re.sub(r'<[^>]+>', ' ', pager_num.group(0))
    pager_text = re.sub(r'\s+', ' ', pager_text).strip()

    # Try to get total records from "tổng số" or pager info elsewhere
    total_records = 0
    m = re.search(r'tổng\s*số[^:]*:\s*<strong[^>]*>(\d+)', html, re.DOTALL)
    if not m:
        m = re.search(r'tổng\s*số[^:]*:\s*<b[^>]*>(\d+)', html, re.DOTALL)
    if m:
        total_records = int(m.group(1))

    return current_page, pager_text, buttons, total_records


def fetch_page(url, form_fields, event_target, referer):
    """POST to get a specific page of the RadGrid.
    Returns (html, url) or (None, error)."""
    fields = dict(form_fields)
    fields['__EVENTTARGET'] = event_target
    fields['__EVENTARGUMENT'] = ''
    fields['__LASTFOCUS'] = ''
    return get_page(url, data=fields, referer=referer)


def extract_documents(html):
    documents = []
    trs = re.findall(r'<tr[^>]*class="\s*rg(?:Alt)?Row\s*"[^>]*>(.*?)</tr>', html, re.DOTALL)

    for tr in trs:
        tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)

        if len(tds) >= 15:
            stt = strip_tags(tds[4])
            if not stt.isdigit():
                continue
            doc = {
                'stt': stt,
                'so_den': strip_tags(tds[6]),
                'tac_gia': strip_tags(tds[7]),
                'so_ky_hieu': strip_tags(tds[8]),
                'ngay_vb': strip_tags(tds[9]),
                'ngay_den': strip_tags(tds[14]),
                'han_xl': strip_tags(tds[12]),
                'do_khan': extract_urgency_from_td(tds[11]),
                'but_phe': extract_but_phe(tr),
                'nguoi_gui': strip_tags(tds[13]),
                'trich_yeu': extract_trich_yeu(tds[10]),
            }
        elif len(tds) >= 11:
            stt = strip_tags(tds[1])
            if not stt.isdigit():
                continue
            doc = {
                'stt': stt,
                'so_den': strip_tags(tds[4]),
                'ngay_den': strip_tags(tds[5]),
                'ngay_vb': strip_tags(tds[6]),
                'han_xl': '',
                'so_ky_hieu': strip_tags(tds[8]),
                'tac_gia': strip_tags(tds[9]),
                'trich_yeu': strip_tags(tds[10]),
                'do_khan': extract_urgency(tr),
                'but_phe': extract_but_phe(tr),
            }
        else:
            continue

        if doc['so_den'] or doc['so_ky_hieu']:
            documents.append(doc)

    return documents


def extract_trich_yeu(td_html):
    """Extract 'Trích yếu' text from the 'Thông tin văn bản' cell."""
    m = re.search(r'<b[^>]*>Trích yếu:[^<]*</b>\s*(.*?)(?:<br|<span|$)', td_html, re.DOTALL)
    if m:
        return strip_tags(m.group(1)).strip()
    return strip_tags(td_html).strip()


def extract_urgency_from_td(td_html):
    """Extract urgency from the Độ khẩn cell (17-column format)."""
    m = re.search(r'id="[^"]*lblDoKhan"[^>]*>([^<]*)', td_html)
    if m:
        text = m.group(1).strip()
        if text:
            return text
    return "Thường"


def get_documents():
    """Get ALL documents from the văn bản đến page using urllib.
    Handles pagination: fetches page 1, then POSTs for subsequent pages."""
    main_page_url = BASE_URL + "/Default.aspx?tabid=56"
    html, url = get_page(DOCS_URL, referer=main_page_url)
    if html is None:
        return None, f"Không thể tải: {url}"

    docs = extract_documents(html)
    if not docs:
        return docs, url

    return docs, url


def dedup_documents(docs):
    """Dedup documents by so_den (keep first occurrence, preserve order)."""
    seen = set()
    result = []
    for d in docs:
        key = d.get('so_den', '') or d.get('so_ky_hieu', '')
        if key and key not in seen:
            seen.add(key)
            result.append(d)
    return result


def pw_get_documents():
    """Get ALL documents via Playwright (handles Telerik RadGrid AJAX pagination).
    Replaces the full urllib flow: login + unit select + multi-page collection.
    Returns (docs_list, status_message)."""
    if not HAS_PLAYWRIGHT:
        return None, "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"

    docs = []
    seen_so_den = set()

    def _select_unit_and_collect(page, unit_spec):
        """Select a unit and collect all pages. Returns doc count."""
        if unit_spec:
            page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=30000)
            try: page.wait_for_load_state("networkidle", timeout=15000)
            except: pass
            try:
                sel = page.query_selector("select[id$=ddlChonDonVi]")
                if sel:
                    val = unit_spec if unit_spec.isdigit() else None
                    if val:
                        sel.select_option(value=val)
                    else:
                        for o in sel.query_selector_all('option'):
                            if unit_spec.lower() in o.inner_text().lower():
                                sel.select_option(value=o.get_attribute('value'))
                                break
                    page.wait_for_timeout(2000)
                    try: page.wait_for_load_state("networkidle", timeout=15000)
                    except: pass
            except: pass

        page.goto(DOCS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        try: page.wait_for_selector(".rgLoadingDiv", state="hidden", timeout=10000)
        except: pass
        try: page.wait_for_load_state("networkidle", timeout=20000)
        except: pass

        def collect_current():
            html = page.content()
            parsed = extract_documents(html)
            new = []
            for d in parsed:
                key = d.get("so_den", "")
                if key and key not in seen_so_den:
                    seen_so_den.add(key)
                    d['unit'] = unit_spec or ''
                    new.append(d)
            return new

        local_count = 0
        docs_page1 = collect_current()
        if not docs_page1:
            return 0
        docs.extend(docs_page1)
        local_count += len(docs_page1)
        pn = 1
        while True:
            next_btn = page.query_selector(".rgPageNext:not(.rgDisabled)")
            if not next_btn:
                break
            try:
                next_btn.click()
            except:
                page.evaluate("""
                    var btn = document.querySelector('.rgPageNext:not(.rgDisabled)');
                    if (btn) btn.click();
                """)
            page.wait_for_timeout(2000)
            try: page.wait_for_selector(".rgLoadingDiv", state="hidden", timeout=10000)
            except: pass
            try: page.wait_for_load_state("networkidle", timeout=20000)
            except: pass
            pn += 1
            new_docs = collect_current()
            if not new_docs:
                break
            docs.extend(new_docs)
            local_count += len(new_docs)
            if pn > 50:
                break
        return local_count

    MAX_RETRIES = 2
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True, args=["--no-sandbox"]
                )
                page = browser.new_page()
                page.set_default_timeout(60000)

                # --- Login via OpenAM SSO ---
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)
                page.fill('#IDToken1', USERNAME)
                page.fill('#IDToken2', PASSWORD)
                page.click('#btnLogin')
                page.wait_for_timeout(3000)
                try: page.wait_for_load_state("networkidle", timeout=15000)
                except: pass

                # Save storage state for attachment download to reuse
                try:
                    os.makedirs(STATE_DIR, exist_ok=True)
                    page.context.storage_state(path=STORAGE_STATE_FILE)
                except: pass

                # --- Collect docs for each unit ---
                if UNITS:
                    for unit_spec in UNITS:
                        count = _select_unit_and_collect(page, unit_spec)
                        if count:
                            print(f"[INFO] Unit '{unit_spec}': {count} docs", file=sys.stderr)
                else:
                    count = _select_unit_and_collect(page, None)
                    if not count:
                        browser.close()
                        continue

                browser.close()
            return docs, f"Lấy được {len(docs)} văn bản (Playwright, {len(UNITS) if UNITS else 1} đơn vị)"
        except Exception as e:
            last_error = str(e)
            continue

    return None, f"Lỗi Playwright (after {MAX_RETRIES} attempts): {last_error}"


def load_state():
    """Load previously seen state."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {'seen_ids': [], 'last_check': None}


def save_state(state):
    """Save current state."""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main():
    global _script_start_time
    _script_start_time = _time.monotonic()

    # --- Try Playwright first (handles pagination, AJAX) ---
    docs, msg = pw_get_documents()
    if docs is None:
        # Fallback to urllib
        print(f"[INFO] Playwright unavailable, falling back to urllib: {msg}", file=sys.stderr)
        success, message = login()
        if not success:
            print(f"[LỖI] {message}")
            sys.exit(1)

        if UNITS:
            all_unit_docs = []
            for unit_spec in UNITS:
                unit_id = unit_spec if unit_spec.isdigit() else None
                unit_name = unit_spec if not unit_spec.isdigit() else ""
                success, msg, unit_docs = select_unit(unit_id, unit_name)
                if unit_docs:
                    all_unit_docs.extend(unit_docs)
                    print(f"[INFO] Unit '{unit_spec}': {len(unit_docs)} docs", file=sys.stderr)
            if all_unit_docs:
                docs = all_unit_docs
            else:
                docs, url = get_documents()
        else:
            docs, url = get_documents()

        if docs is None:
            print(f"[LỖI] Không lấy được văn bản nào")
            sys.exit(1)

    # Silent exit if no docs at all
    if not docs:
        sys.exit(0)

    docs = dedup_documents(docs)

    # Load state, find new docs, save updated state
    state = load_state()
    seen = set(state.get('seen_ids', []))
    new_docs = [d for d in docs if (d.get('so_den', '') or d.get('so_ky_hieu', '')) not in seen]

    current_ids = set((d.get('so_den', '') or d.get('so_ky_hieu', '')) for d in docs if d.get('so_den', '') or d.get('so_ky_hieu', ''))
    old_seen = set(state.get('seen_ids', []))
    state['seen_ids'] = list(old_seen | current_ids)
    state['last_check'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    state['last_count'] = len(docs)
    # Save document details for new VBs
    state.setdefault('documents', {})
    now_ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for d in docs:
        key = d.get('so_den', '') or d.get('so_ky_hieu', '')
        if key and key not in state['documents']:
            state['documents'][key] = {
                'so_den': d.get('so_den', ''),
                'so_ky_hieu': d.get('so_ky_hieu', ''),
                'tac_gia': d.get('tac_gia', ''),
                'trich_yeu': d.get('trich_yeu', ''),
                'ngay_vb': d.get('ngay_vb', ''),
                'ngay_den': d.get('ngay_den', ''),
                'do_khan': d.get('do_khan', 'Thường'),
                'but_phe': d.get('but_phe', ''),
                'unit': d.get('unit', ''),
                'first_seen': now_ts,
                'status': 'new',
                'status_updated_at': now_ts,
                'note': '',
            }
    save_state(state)

    # --- F20: Phát hiện VB trùng/thay thế ---
    replace_keywords = ["thay thế", "đính chính", "bổ sung", "hủy bỏ", "sửa đổi"]
    dup_warnings = []
    # Build so_ky_hieu → so_den index from existing state (excluding current docs)
    skh_index = {}
    for sid, sd in state.get('documents', {}).items():
        skh = sd.get('so_ky_hieu', '').strip()
        if skh:
            skh_index.setdefault(skh, []).append(sid)
    for d in new_docs:
        skh = d.get('so_ky_hieu', '').strip()
        if not skh:
            continue
        existing = skh_index.get(skh)
        if not existing:
            continue
        old_ids = ", ".join(f"#{e}" for e in existing)
        trich = d.get('trich_yeu', '').lower()
        match_kw = [kw for kw in replace_keywords if kw in trich]
        if match_kw:
            dup_warnings.append((d, old_ids, match_kw, "related"))
        else:
            dup_warnings.append((d, old_ids, [], "duplicate"))
    # Save relationship in state
    if dup_warnings:
        for d, old_ids, kw, kind in dup_warnings:
            key = d.get('so_den', '') or d.get('so_ky_hieu', '')
            skh = d.get('so_ky_hieu', '')
            if key and key in state.get('documents', {}):
                if kind == "related":
                    state['documents'][key]['note'] = (state['documents'][key].get('note', '')
                        + f"[Liên quan đến {old_ids}, từ khóa: {', '.join(kw)}] ")
                else:
                    state['documents'][key]['note'] = (state['documents'][key].get('note', '')
                        + f"[Trùng số {skh} với {old_ids}] ")

    # --- F20: Fetch roles and auto-finish ---
    auto_finish_list = fetch_vai_tro_for_docs(new_docs, state)
    if auto_finish_list:
        save_state(state)
        import subprocess
        action_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "congchuc_action.py")
        python_bin = "/opt/hermes/.venv/bin/python" if os.path.exists("/opt/hermes/.venv/bin/python") else sys.executable
        for so_den in auto_finish_list:
            vai_tro = state['documents'].get(so_den, {}).get('vai_tro', 'Thông báo')
            reason = f"Đã nhận văn bản (Tự động kết thúc - {vai_tro})"
            print(f"[AUTO-FINISH] Spawning background task for #{so_den}...", file=sys.stderr)
            subprocess.Popen([python_bin, action_script, "kethuc", str(so_den), reason],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Update local list output to reflect auto-finish
            for d in new_docs:
                if str(d.get('so_den', '')) == str(so_den):
                    d['auto_finished'] = True

    # Download attachments for new docs (optional, requires Playwright)
    CONGVAN_DOWNLOAD_ATTACHMENTS = os.environ.get("CONGVAN_DOWNLOAD_ATTACHMENTS", "").strip()
    attachment_results = {}
    if HAS_PLAYWRIGHT and CONGVAN_DOWNLOAD_ATTACHMENTS in ("1", "true", "yes"):
        if _time_remaining() < 15:
            print(f"[SKIP] Chỉ còn {_time_remaining():.0f}s, bỏ qua attachment download", file=sys.stderr)
        else:
            # Skip attachment download for docs that are being auto-finished
            attachment_docs = [d for d in new_docs if str(d.get('so_den', '')) not in auto_finish_list]
            if not attachment_docs:
                for sid, d in state.get('documents', {}).items():
                    if d.get('attachments') and not d.get('attachments_complete') and str(sid) not in auto_finish_list:
                        attachment_docs.append({**d, 'so_den': str(sid)})
                attachment_docs = attachment_docs[:5]
            if attachment_docs:
                attachment_results = download_attachments_for_docs(attachment_docs, state, STATE_DIR)
                if attachment_results:
                    state = load_state()

    # Silent if no new docs and no attachments downloaded
    if not new_docs and not attachment_results and not auto_finish_list:
        sys.exit(0)

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_str = datetime.datetime.now().strftime('%d/%m/%Y')

    # Sort by so_den descending (newest first)
    new_docs.sort(key=lambda d: int(d.get('so_den', '0') or '0'), reverse=True)

    # Urgency detection
    urgent_keywords = ['Cực Khẩn', 'Hỏa tốc hẹn giờ', 'Hỏa tốc', 'Thượng khẩn', 'Khẩn', 'Gấp', 'Tốc ký']
    def get_urgency(doc):
        parsed = doc.get('do_khan', '').strip()
        if parsed and parsed != 'Thường':
            return parsed
        trich_yeu = doc.get('trich_yeu', '')
        so_ky_hieu = doc.get('so_ky_hieu', '')
        so_den = doc.get('so_den', '')
        combined = f"{trich_yeu} {so_ky_hieu} {so_den}".replace('(', '').replace(')', '')
        for kw in urgent_keywords:
            if kw.lower() in combined.lower():
                return kw
        return "Thường"

    so_khan = sum(1 for d in new_docs if get_urgency(d) != "Thường")
    so_thuong = len(new_docs) - so_khan
    unit_label = ", ".join(UNITS) if UNITS else "Tất cả đơn vị"

    # Build compact report (Zalo-friendly, short enough to deliver)
    lines = []
    lines.append(f"📋 {len(new_docs)} VB đến mới ({unit_label})")
    lines.append(f"({now})\n")

    if dup_warnings:
        for d, old_ids, kw, kind in dup_warnings:
            so_den = d.get('so_den', '')
            skh = d.get('so_ky_hieu', '')
            if kind == "related":
                icon = "🔄"
                kw_tag = f" ({', '.join(kw)})" if kw else ""
                lines.append(f"{icon} VB {skh} (#{so_den}) — liên quan {old_ids}{kw_tag}")
            else:
                lines.append(f"⚠️ VB {skh} (#{so_den}) — trùng số với {old_ids}")
        lines.append("")

    urgent_docs = [(d, get_urgency(d)) for d in new_docs if get_urgency(d) != "Thường"]
    for doc, urgency in urgent_docs:
        so_den = doc.get('so_den', '')
        so_ky_hieu = doc.get('so_ky_hieu', '')
        trich_yeu = doc.get('trich_yeu', '')[:80]
        lines.append(f"🔴 [{urgency}] #{so_den} {so_ky_hieu}")
        lines.append(f"   {trich_yeu}")
    if urgent_docs:
        lines.append("")

    for i, doc in enumerate(new_docs, 1):
        so_den = doc.get('so_den', '')
        so_ky_hieu = doc.get('so_ky_hieu', '')
        tac_gia = doc.get('tac_gia', '')
        trich_yeu = doc.get('trich_yeu', '')[:70]
        do_khan = get_urgency(doc)
        urgency_tag = f"[{do_khan}]" if do_khan != "Thường" else ""
        but_phe = doc.get('but_phe', '')
        bp_tag = " 📝" if but_phe else ""
        af_tag = " ✅(Auto-Finished)" if doc.get('auto_finished') else ""
        lines.append(f"{i}. {urgency_tag} #{so_den} | {so_ky_hieu}{af_tag}")
        lines.append(f"   {tac_gia} — {trich_yeu}{bp_tag}")

    lines.append("")
    lines.append(f"📊 {len(new_docs)} mới (khẩn: {so_khan}, thường: {so_thuong})")
    lines.append(f"🔗 {DOCS_URL}")

    print('\n'.join(lines), flush=True)


def download_attachments_for_docs(new_docs, state, state_dir):
    """Download attachments for new VB đến docs via Playwright.
    Returns dict: {so_den: [{"filename": ..., "size": ..., "path": ...}]}
    """
    if not HAS_PLAYWRIGHT:
        print("[ATTACHMENT] Playwright not available, skipping", file=sys.stderr)
        return {}
    
    print(f"[ATTACHMENT] Starting for {len(new_docs)} VBs...", file=sys.stderr)
    att_base = os.path.join(state_dir, "attachments")
    os.makedirs(att_base, exist_ok=True)
    
    results = {}
    try:
        from playwright.sync_api import sync_playwright
        import zipfile, io
        
        print("[ATTACHMENT] Launching Playwright...", file=sys.stderr)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Use saved storage_state from pw_get_documents to skip re-login
            if os.path.exists(STORAGE_STATE_FILE):
                print("[ATTACHMENT] Reusing login session from state file", file=sys.stderr)
                login_context = browser.new_context(storage_state=STORAGE_STATE_FILE)
            else:
                login_context = browser.new_context()
                login_page = login_context.new_page()
                
                login_page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
                login_page.wait_for_timeout(2000)
                login_page.fill('#IDToken1', USERNAME)
                login_page.fill('#IDToken2', PASSWORD)
                login_page.click('#btnLogin')
                login_page.wait_for_timeout(3000)
                try: login_page.wait_for_load_state("networkidle", timeout=15000)
                except: pass
                
                if UNITS:
                    login_page.goto(BASE_URL + "/Default.aspx?tabid=56", timeout=60000, wait_until='domcontentloaded')
                    try: login_page.wait_for_load_state("networkidle", timeout=10000)
                    except: pass
                    login_page.wait_for_timeout(2000)
                    sel = login_page.query_selector('select[id$=ddlChonDonVi]')
                    if sel:
                        unit_spec = UNITS[0]
                        for o in sel.query_selector_all('option'):
                            val = o.get_attribute('value')
                            txt = o.inner_text().strip()
                            if unit_spec.isdigit() and val == unit_spec:
                                sel.select_option(value=val)
                                print(f"[ATTACHMENT] Selected unit: {txt}", file=sys.stderr)
                                break
                            elif unit_spec.lower() in txt.lower():
                                sel.select_option(value=val)
                                print(f"[ATTACHMENT] Selected unit: {txt}", file=sys.stderr)
                                break
                        login_page.wait_for_timeout(2000)
                
                login_page.close()
            
            for idx, doc in enumerate(new_docs[:MAX_ATTACHMENT_DOCS]):
                if _time_remaining() < 15:
                    remaining = len(new_docs[:MAX_ATTACHMENT_DOCS]) - idx
                    print(f"[SKIP] Còn {remaining} VB (cạn time {_time_remaining():.0f}s)", file=sys.stderr)
                    break
                so_den = str(doc.get('so_den', '') or '').strip()
                if not so_den:
                    continue
                
                existing = state.get('documents', {}).get(so_den, {}).get('attachments', [])
                complete = state.get('documents', {}).get(so_den, {}).get('attachments_complete', False)
                if complete:
                    print(f"[ATTACHMENT] [{idx+1}/{min(len(new_docs),10)}] Số đến {so_den} — already complete, skipping", file=sys.stderr)
                    continue
                print(f"[ATTACHMENT] [{idx+1}/{min(len(new_docs),10)}] Số đến {so_den} ({len(existing)} files)...", file=sys.stderr)
                
                # Fresh tab for each VB — avoids page-state carryover
                page = login_context.new_page()
                page.goto(DOCS_URL, timeout=60000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
                try: page.wait_for_selector(".rgLoadingDiv", state="hidden", timeout=10000)
                except: pass
                try: page.wait_for_load_state("networkidle", timeout=20000)
                except: pass
                
                # Find the row with "Tải tất cả file" button for this VB
                dl_btn = None
                for page_idx in range(20):
                    rows = page.query_selector_all('table.rgMasterTable > tbody > tr.rgRow, table.rgMasterTable > tbody > tr.rgAltRow')
                    for row in rows:
                        link = row.query_selector('a')
                        if link and link.inner_text().strip() == so_den:
                            dl_btn = row.query_selector('input[title*="Tải tất cả"]')
                            break
                    if dl_btn:
                        break
                    next_btn = page.query_selector('.rgPageNext:not(.rgDisabled)')
                    if not next_btn:
                        break
                    next_btn.click()
                    page.wait_for_timeout(3000)
                
                if not dl_btn:
                    print(f"[ATTACHMENT] Số đến {so_den} not found or no download button", file=sys.stderr)
                    page.close()
                    continue
                
                # Click "Tải tất cả file" → captures ZIP of all files
                try:
                    with page.expect_download(timeout=45000) as dw:
                        dl_btn.click()
                    dl = dw.value
                    tmp_path = dl.path()
                    if not tmp_path:
                        print(f"[ATTACHMENT] No temp path for VB {so_den}", file=sys.stderr)
                        page.close()
                        continue
                    with open(tmp_path, 'rb') as f:
                        zip_bytes = f.read()
                    
                    att_dir = os.path.join(att_base, so_den)
                    os.makedirs(att_dir, exist_ok=True)
                    
                    doc_attachments = []
                    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                        for name in z.namelist():
                            safe_name = name.replace('/', '_').replace('\\', '_')
                            save_path = os.path.join(att_dir, safe_name)
                            with z.open(name) as src, open(save_path, 'wb') as dst:
                                dst.write(src.read())
                            doc_attachments.append({
                                'filename': safe_name,
                                'display_name': name,
                                'size': os.path.getsize(save_path),
                                'path': os.path.join('attachments', so_den, safe_name),
                                'downloaded_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            })
                            print(f"[ATTACHMENT]   Extracted: {safe_name} ({os.path.getsize(save_path)} bytes)", file=sys.stderr)
                    
                    existing_names = {a.get('display_name', '') for a in existing}
                    new_names = {a['display_name'] for a in doc_attachments}
                    if existing_names == new_names:
                        print(f"[ATTACHMENT] VB {so_den}: file set unchanged, marking complete", file=sys.stderr)
                        state.setdefault('documents', {}).setdefault(so_den, {})['attachments_complete'] = True
                        save_state(state)
                    else:
                        state.setdefault('documents', {}).setdefault(so_den, {})['attachments'] = doc_attachments
                        state.setdefault('documents', {}).setdefault(so_den, {})['attachments_complete'] = True
                        save_state(state)
                        results[so_den] = doc_attachments
                        print(f"[ATTACHMENT] VB {so_den}: {len(doc_attachments)} files downloaded and saved", file=sys.stderr)
                except Exception as e:
                    print(f"[ATTACHMENT] Download/extract failed for VB {so_den}: {e}", file=sys.stderr)
                finally:
                    page.close()
            
            browser.close()
    
    except Exception as e:
        print(f"[ATTACHMENT] Error: {e}", file=sys.stderr)
    
    return results

def fetch_vai_tro_for_docs(new_docs, state):
    if not HAS_PLAYWRIGHT or not new_docs:
        return []
    
    print(f"[ROLE] Starting role extraction for {len(new_docs)} new VBs...", file=sys.stderr)
    auto_finish_docs = []
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            
            if os.path.exists(STORAGE_STATE_FILE):
                login_context = browser.new_context(storage_state=STORAGE_STATE_FILE)
            else:
                login_context = browser.new_context()
                login_page = login_context.new_page()
                login_page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
                login_page.wait_for_timeout(2000)
                login_page.fill('#IDToken1', USERNAME)
                login_page.fill('#IDToken2', PASSWORD)
                login_page.click('#btnLogin')
                login_page.wait_for_timeout(3000)
                try: login_page.wait_for_load_state("networkidle", timeout=15000)
                except: pass
                
                if UNITS:
                    login_page.goto(BASE_URL + "/Default.aspx?tabid=56", timeout=60000, wait_until='domcontentloaded')
                    try: login_page.wait_for_load_state("networkidle", timeout=10000)
                    except: pass
                    login_page.wait_for_timeout(2000)
                    sel = login_page.query_selector('select[id$=ddlChonDonVi]')
                    if sel:
                        unit_spec = UNITS[0]
                        for o in sel.query_selector_all('option'):
                            val = o.get_attribute('value')
                            txt = o.inner_text().strip()
                            if unit_spec.isdigit() and val == unit_spec:
                                sel.select_option(value=val)
                                break
                            elif unit_spec.lower() in txt.lower():
                                sel.select_option(value=val)
                                break
                        login_page.wait_for_timeout(2000)
                login_page.close()
            
            for idx, doc in enumerate(new_docs):
                if _time_remaining() < 25:
                    print(f"[SKIP] Cạn time ({_time_remaining():.0f}s), skip role extraction", file=sys.stderr)
                    break
                
                so_den = str(doc.get('so_den', '')).strip()
                if not so_den: continue
                
                page = login_context.new_page()
                page.goto(DOCS_URL, timeout=60000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
                try: page.wait_for_load_state("networkidle", timeout=20000)
                except: pass
                
                target_btn = None
                for page_idx in range(15):
                    rows = page.query_selector_all('table.rgMasterTable > tbody > tr.rgRow, table.rgMasterTable > tbody > tr.rgAltRow')
                    for row in rows:
                        link = row.query_selector('a')
                        if link and link.inner_text().strip() == so_den:
                            target_btn = row.query_selector("[id*='btnQuyTrinh']")
                            break
                    if target_btn:
                        break
                    next_btn = page.query_selector('.rgPageNext:not(.rgDisabled)')
                    if not next_btn:
                        break
                    next_btn.click()
                    page.wait_for_timeout(3000)
                
                if target_btn:
                    target_btn.click()
                    page.wait_for_timeout(4000)
                    try: page.wait_for_load_state("networkidle", timeout=10000)
                    except: pass
                    
                    role_value = "N/A"
                    frames_to_check = [page] + [f.content_frame() for f in page.query_selector_all('iframe') if f.content_frame()]
                    for frame in frames_to_check:
                        try:
                            if "QuaTrinhXuLy_treQuaTrinhXuLy" in frame.content():
                                rws = frame.query_selector_all('[id*="treQuaTrinhXuLy"] tbody tr')
                                for r in rws:
                                    cells = r.query_selector_all('td')
                                    if not cells: continue
                                    row_text = [c.inner_text().strip() for c in cells]
                                    row_str = " ".join(row_text).lower()
                                    if CONGVAN_FULLNAME.lower() in row_str:
                                        if "thông báo" in row_str or "để biết" in row_str or "thong bao" in row_str or "de biet" in row_str:
                                            role_value = "Thông báo"
                                        else:
                                            role_value = "Khác"
                                        break
                                if role_value != "N/A":
                                    break
                        except Exception as e:
                            pass
                            
                    print(f"[ROLE] Văn bản #{so_den} Vai trò của {CONGVAN_FULLNAME}: {role_value}", file=sys.stderr)
                    if so_den in state.get('documents', {}):
                        state['documents'][so_den]['vai_tro'] = role_value
                    if role_value in ["Thông báo", "Để biết", "Thong bao", "De biet"]:
                        auto_finish_docs.append(so_den)
                else:
                    print(f"[ROLE] Không tìm thấy btnQuyTrinh cho #{so_den}", file=sys.stderr)
                    
                page.close()
            browser.close()
    except Exception as e:
        print(f"[ROLE] Error: {e}", file=sys.stderr)
        
    return auto_finish_docs

if __name__ == '__main__':
    main()
