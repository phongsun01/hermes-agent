import os
import sys
import re
from playwright.sync_api import sync_playwright

_hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
_env_path = os.path.join(_hermes_home, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

USER = os.environ.get("CONGVAN_USER", "")
PASS = os.environ.get("CONGVAN_PASS", "")

if not USER or not PASS:
    print("Vui lòng cấu hình CONGVAN_USER và CONGVAN_PASS trong biến môi trường (.env)", file=sys.stderr)
    sys.exit(1)
BASE = "https://congchuc.quangninh.gov.vn"
LOGIN_URL = BASE + "/SSO/Login.aspx"
DOCS_URL = BASE + "/Default.aspx?tabid=1126"
UNIT = "2256"
TARGET_DOC = "2466"

sys.stdout.reconfigure(encoding='utf-8')

def parse_treelist(context, selector):
    """Parse the treelist to find the 'Vai trò' column values."""
    print("\n--- PARSING TREELIST ---")
    # Telerik RadTreeList is rendered as a table.
    headers = context.query_selector_all(f'{selector} th')
    if not headers:
        headers = context.query_selector_all('table th')
        
    role_col_idx = -1
    for idx, th in enumerate(headers):
        text = th.inner_text().strip()
        print(f"Header [{idx}]: {text}")
        if "Vai trò" in text or "Vai tro" in text:
            role_col_idx = idx
            print(f"-> Found 'Vai trò' column at index {role_col_idx}")

    # Now list all rows
    rows = context.query_selector_all(f'{selector} tbody tr')
    if not rows:
        rows = context.query_selector_all('table tbody tr')
        
    print(f"Found {len(rows)} rows in the treelist table.")
    for r_idx, r in enumerate(rows):
        cells = r.query_selector_all('td')
        if not cells: continue
        row_text = [c.inner_text().strip() for c in cells]
        if not row_text or len(row_text) <= 1:
            continue
        
        role_value = row_text[role_col_idx] if role_col_idx != -1 and role_col_idx < len(row_text) else "N/A"
        print(f"Row [{r_idx}]: {row_text} -> Vai trò: {role_value}")

p = sync_playwright().start()
browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
page = browser.new_page()

try:
    print("Logging in...", file=sys.stderr)
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)
    page.fill('#IDToken1', USER)
    page.fill('#IDToken2', PASS)
    page.click('#btnLogin')
    page.wait_for_timeout(4000)
    try: page.wait_for_load_state("networkidle", timeout=15000)
    except: pass

    print("Selecting unit...", file=sys.stderr)
    page.goto(BASE + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=30000)
    sel = page.query_selector("select[id$=ddlChonDonVi]")
    if sel:
        sel.select_option(UNIT)
        page.wait_for_timeout(2000)
        try: page.wait_for_load_state("networkidle", timeout=15000)
        except: pass

    print("Navigating to grid...", file=sys.stderr)
    page.goto(DOCS_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    try: page.wait_for_load_state("networkidle", timeout=20000)
    except: pass

    # Find row for TARGET_DOC
    print(f"Searching for document #{TARGET_DOC}...", file=sys.stderr)
    target_btn = None
    for page_idx in range(15):
        rows = page.query_selector_all('table.rgMasterTable > tbody > tr.rgRow, table.rgMasterTable > tbody > tr.rgAltRow')
        for row in rows:
            link = row.query_selector('a')
            if link and link.inner_text().strip() == TARGET_DOC:
                target_btn = row.query_selector("[id*='btnQuyTrinh']")
                break
        if target_btn:
            break
        next_btn = page.query_selector('.rgPageNext:not(.rgDisabled)')
        if not next_btn:
            break
        next_btn.click()
        page.wait_for_timeout(3000)
        try: page.wait_for_load_state("networkidle", timeout=15000)
        except: pass

    if not target_btn:
        print(f"Document #{TARGET_DOC} not found in grid!", file=sys.stderr)
        sys.exit(1)

    btn_id = target_btn.get_attribute("id")
    print(f"Clicking btnQuyTrinh: {btn_id}...", file=sys.stderr)
    target_btn.click()
    page.wait_for_timeout(4000)
    try: page.wait_for_load_state("networkidle", timeout=10000)
    except: pass

    screenshot_path = "/opt/data/scripts/congchuc/quytrinh_clicked.png"
    page.screenshot(path=screenshot_path)
    print(f"Screenshot saved to {screenshot_path}", file=sys.stderr)
    
    html = page.content()
    with open("/opt/data/scripts/congchuc/quytrinh_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved popup page HTML to /opt/data/scripts/congchuc/quytrinh_page.html", file=sys.stderr)

    # Check if there is an iframe loaded
    iframes = page.query_selector_all("iframe")
    print(f"Found {len(iframes)} iframes on the page.", file=sys.stderr)
    for idx, iframe in enumerate(iframes):
        iframe_name = iframe.get_attribute("name")
        iframe_src = iframe.get_attribute("src")
        print(f"  iframe [{idx}]: name={iframe_name}, src={iframe_src}", file=sys.stderr)

    # Search the main page HTML for treelist
    if "QuaTrinhXuLy_treQuaTrinhXuLy" in html:
        print("treQuaTrinhXuLy found in main page HTML!", file=sys.stderr)
        parse_treelist(page, 'id="QuaTrinhXuLy_treQuaTrinhXuLy"')
    else:
        print("treQuaTrinhXuLy not in main page. Trying inside iframes...", file=sys.stderr)
        found_in_iframe = False
        for iframe_element in iframes:
            try:
                frame = iframe_element.content_frame()
                frame_html = frame.content()
                if "QuaTrinhXuLy_treQuaTrinhXuLy" in frame_html:
                    print("Found treQuaTrinhXuLy inside iframe!", file=sys.stderr)
                    with open("/opt/data/scripts/congchuc/iframe_quytrinh.html", "w", encoding="utf-8") as f:
                        f.write(frame_html)
                    parse_treelist(frame, '[id*="treQuaTrinhXuLy"]')
                    found_in_iframe = True
                    break
            except Exception as fe:
                print(f"Could not inspect iframe: {fe}", file=sys.stderr)
        
        if not found_in_iframe:
            print("treQuaTrinhXuLy NOT found in main page or any iframe.", file=sys.stderr)

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
finally:
    browser.close()
    p.stop()
    print("Finished inspection script.", file=sys.stderr)
