"""Search for Văn bản đi (outgoing documents) from tabid=1121 by keyword."""
import os, sys, json, re, subprocess, traceback
from datetime import datetime

_hermes_home = os.environ.get("HERMES_HOME", "/opt/data")
_env_path = os.path.join(_hermes_home, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

_url = os.environ.get("CONGVAN_URL", "https://congchuc.quangninh.gov.vn")
if "/Default.aspx" in _url:
    BASE = _url.split("/Default.aspx")[0]
else:
    BASE = _url.rstrip("/")

USER = os.environ.get("CONGVAN_USER", "")
PASS = os.environ.get("CONGVAN_PASS", "")
TABID = os.environ.get("CONGVAN_DI_TABID", "1121")

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

def extract_documents(html):
    """Parse Văn bản đi RadGrid from HTML."""
    docs = []
    rows = re.findall(r'<tr[^>]*class="\s*rg(?:Alt)?Row\s*"[^>]*>(.*?)</tr>', html, re.DOTALL)
    
    for row_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if len(cells) < 10:
            continue
        
        vbdi_id = re.sub(r'<[^>]+>', '', cells[0]).strip()
        stt = re.sub(r'<[^>]+>', '', cells[2]).strip()
        so_ky_hieu_elem = re.sub(r'<[^>]+>', '', cells[4]).strip() if len(cells) > 4 else ""
        ngay_phat_hanh = re.sub(r'<[^>]+>', '', cells[5]).strip() if len(cells) > 5 else ""
        ngay_soan = re.sub(r'<[^>]+>', '', cells[6]).strip() if len(cells) > 6 else ""
        trich_yeu = re.sub(r'<[^>]+>', '', cells[7]).strip() if len(cells) > 7 else ""
        don_vi_soan = re.sub(r'<[^>]+>', '', cells[8]).strip() if len(cells) > 8 else ""
        nguoi_soan = re.sub(r'<[^>]+>', '', cells[9]).strip() if len(cells) > 9 else ""
        
        doc = {
            "vbdi_id": vbdi_id,
            "stt": stt,
            "so_ky_hieu": so_ky_hieu_elem,
            "ngay_phat_hanh": ngay_phat_hanh,
            "ngay_soan": ngay_soan,
            "trich_yeu": trich_yeu,
            "don_vi_soan_thao": don_vi_soan,
            "nguoi_soan_thao": nguoi_soan,
        }
        docs.append(doc)
    
    return docs

def pw_search_documents(query_str):
    """Login + search by keyword + parse grid using Playwright."""
    MAX_RETRIES = 2
    STORAGE_STATE_FILE = os.path.join(_hermes_home, "cron", "cong-van-den", ".playwright_storage.json")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
                
                context = None
                session_reused = False
                if os.path.exists(STORAGE_STATE_FILE):
                    try:
                        print(f"[INFO] Attempting to reuse Playwright storage state...", file=sys.stderr)
                        context = browser.new_context(storage_state=STORAGE_STATE_FILE)
                        page = context.new_page()
                        page.set_default_timeout(60000)
                        
                        # Go to Văn bản đi search directly
                        page.goto(f"{BASE}/Default.aspx?tabid={TABID}", wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(2000)
                        
                        if "Login.aspx" not in page.url and not page.query_selector("#IDToken1"):
                            print(f"[INFO] Playwright storage state is valid. Session reused!", file=sys.stderr)
                            session_reused = True
                        else:
                            print(f"[INFO] Playwright storage state expired or invalid.", file=sys.stderr)
                            page.close()
                            context.close()
                            context = None
                    except Exception as reuse_err:
                        print(f"[WARNING] Failed to reuse storage state: {reuse_err}", file=sys.stderr)
                        if context:
                            try: context.close()
                            except: pass
                        context = None
                
                if not session_reused:
                    print(f"[INFO] Performing fresh login...", file=sys.stderr)
                    context = browser.new_context()
                    page = context.new_page()
                    page.set_default_timeout(60000)
                    
                    # Login
                    page.goto(BASE + "/SSO/Login.aspx", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2000)
                    page.fill('#IDToken1', USER)
                    page.fill('#IDToken2', PASS)
                    page.click('#btnLogin')
                    page.wait_for_timeout(5000)
                    try: page.wait_for_load_state("networkidle", timeout=15000)
                    except: pass
                    
                    if "CanhBaoMatKhau" in page.url or "PasswordWarning" in page.url:
                        try:
                            btn = page.query_selector("input[type=submit], button")
                            if btn: btn.click(); page.wait_for_timeout(3000)
                        except: pass
                    
                    # Save storage state
                    try:
                        os.makedirs(os.path.dirname(STORAGE_STATE_FILE), exist_ok=True)
                        context.storage_state(path=STORAGE_STATE_FILE)
                        print(f"[INFO] Saved Playwright storage state.", file=sys.stderr)
                    except: pass
                    
                    # Navigate to Văn bản đi search directly
                    page.goto(f"{BASE}/Default.aspx?tabid={TABID}", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(3000)
                    try: page.wait_for_load_state("networkidle", timeout=20000)
                    except: pass
                
                UNITS = [u.strip() for u in os.environ.get("CONGVAN_UNIT", "").split(",") if u.strip()]
                all_docs = []
                
                def _collect_for_unit(page, unit_spec):
                    if unit_spec:
                        # Go to tabid=56 to select unit (safer, matching congchuc_scrape.py)
                        page.goto(f"{BASE}/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=30000)
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
                        except Exception as e:
                            print(f"[WARNING] Failed to select unit on tabid=56: {e}", file=sys.stderr)

                    # Now go to Văn bản đi search (tabid=1121)
                    page.goto(f"{BASE}/Default.aspx?tabid={TABID}", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(3000)
                    try: page.wait_for_load_state("networkidle", timeout=20000)
                    except: pass

                    # Enter keyword
                    page.fill('#dnn_ctr4744_VBDi_TimKiem_tbSearch', query_str)
                    
                    # Click search button
                    page.evaluate("""
                        (function() {
                            var btn = document.getElementById('dnn_ctr4744_VBDi_TimKiem_btnSearch');
                            if (btn) btn.click();
                        })();
                    """)
                    page.wait_for_timeout(5000)
                    try: page.wait_for_load_state("networkidle", timeout=20000)
                    except: pass
                    
                    # Parse results (with pagination)
                    unit_docs = []
                    pn = 1
                    last_page_ids = set()
                    while True:
                        html = page.content()
                        parsed = extract_documents(html)
                        
                        current_page_ids = {d["vbdi_id"] for d in parsed if d["vbdi_id"]}
                        if not parsed or current_page_ids == last_page_ids:
                            break
                            
                        unit_docs.extend(parsed)
                        last_page_ids = current_page_ids
                        
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
                        if pn > 50:  # Safety limit
                            break
                    return unit_docs

                if UNITS:
                    for unit_spec in UNITS:
                        all_docs.extend(_collect_for_unit(page, unit_spec))
                else:
                    all_docs.extend(_collect_for_unit(page, None))

                seen_ids = set()
                unique_docs = []
                for d in all_docs:
                    if d["vbdi_id"] and d["vbdi_id"] not in seen_ids:
                        seen_ids.add(d["vbdi_id"])
                        unique_docs.append(d)
                
                browser.close()
                return unique_docs
        except Exception as e:
            last_error = str(e)
            print(f"[WARNING] Attempt {attempt} failed: {last_error}", file=sys.stderr)
            continue
    
    return []

def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python congchuc_vbdi_search.py <từ_khóa>")
        sys.exit(1)
        
    query = sys.argv[1].strip()
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available, cannot search Văn bản đi")
        sys.exit(1)
        
    docs = pw_search_documents(query)
    
    if docs:
        print(f"🔍 Tìm thấy {len(docs)} văn bản đi với từ khóa '{query}':\n")
        for i, d in enumerate(docs, 1):
            print(f"{i}. **{d['so_ky_hieu']}** ({d['ngay_phat_hanh']})")
            print(f"   {d['trich_yeu']} — {d['don_vi_soan_thao']}")
    else:
        print(f"🔍 Không tìm thấy văn bản đi nào với từ khóa '{query}'.")

if __name__ == "__main__":
    main()
