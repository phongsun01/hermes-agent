import os
import sys
import json
import subprocess
from playwright.sync_api import sync_playwright

def main():
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
    BASE_URL = DOCS_URL.split("/Default.aspx")[0] if "/Default.aspx" in DOCS_URL else DOCS_URL.rstrip("/")
    LOGIN_URL = BASE_URL + "/SSO/Login.aspx"
    CONGVAN_UNIT_RAW = os.environ.get("CONGVAN_UNIT", "").strip()
    UNIT = CONGVAN_UNIT_RAW.split(",")[0] if CONGVAN_UNIT_RAW else "2256"
    CONGVAN_FULLNAME = os.environ.get("CONGVAN_FULLNAME", "Nguyễn Huy Phong")
    
    STATE_FILE = os.path.join(_hermes_home, "cron", "cong-van-den", "vbden_state.json")

    print(f"Starting force role scan for user {CONGVAN_FULLNAME}...", file=sys.stderr)
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        print(f"Error loading state: {e}", file=sys.stderr)
        state = {"documents": {}}
        
    not_done_docs = []
    for so_den, d in state.get("documents", {}).items():
        if d.get("status") != "done":
            not_done_docs.append(str(so_den))
            
    print(f"Found {len(not_done_docs)} docs not 'done' in state.", file=sys.stderr)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)
        
        print("Logging in...", file=sys.stderr)
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.fill('#IDToken1', USERNAME)
        page.fill('#IDToken2', PASSWORD)
        page.click('#btnLogin')
        page.wait_for_timeout(3000)
        try: page.wait_for_load_state("networkidle", timeout=15000)
        except: pass
        
        print(f"Selecting unit {UNIT}...", file=sys.stderr)
        page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="domcontentloaded")
        sel = page.query_selector("select[id$=ddlChonDonVi]")
        if sel:
            unit_spec = UNIT
            for o in sel.query_selector_all('option'):
                val = o.get_attribute('value')
                txt = o.inner_text().strip()
                if unit_spec.isdigit() and val == unit_spec:
                    sel.select_option(value=val)
                    break
                elif unit_spec.lower() in txt.lower():
                    sel.select_option(value=val)
                    break
            page.wait_for_timeout(2000)
            
        print("Navigating to docs...", file=sys.stderr)
        page.goto(DOCS_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        docs_to_finish = []
        action_script = "/opt/data/scripts/congchuc/congchuc_action.py"
        python_bin = "/opt/hermes/.venv/bin/python" if os.path.exists("/opt/hermes/.venv/bin/python") else sys.executable

        for page_idx in range(20):
            print(f"Scanning page {page_idx+1}...", file=sys.stderr)
            rows = page.query_selector_all('table.rgMasterTable > tbody > tr.rgRow, table.rgMasterTable > tbody > tr.rgAltRow')
            page_docs = []
            for row in rows:
                link = row.query_selector('a')
                if link:
                    so_den = link.inner_text().strip()
                    if so_den in not_done_docs:
                        page_docs.append(so_den)
                        
            for so_den in page_docs:
                print(f"Found pending doc #{so_den}, checking role...", file=sys.stderr)
                
                # Re-fetch rows to avoid DOM detach error
                rows = page.query_selector_all('table.rgMasterTable > tbody > tr.rgRow, table.rgMasterTable > tbody > tr.rgAltRow')
                target_btn = None
                for row in rows:
                    link = row.query_selector('a')
                    if link and link.inner_text().strip() == so_den:
                        target_btn = row.query_selector("[id*='btnQuyTrinh']")
                        break
                        
                if not target_btn: continue
                
                target_btn.click()
                page.wait_for_timeout(4000)
                
                role_value = "N/A"
                frames_to_check = [page] + [f.content_frame() for f in page.query_selector_all('iframe') if f.content_frame()]
                for frame in frames_to_check:
                    try:
                        if "QuaTrinhXuLy_treQuaTrinhXuLy" in frame.content():
                            headers = frame.query_selector_all('[id*="treQuaTrinhXuLy"] th')
                            role_col_idx = -1
                            for hi, th in enumerate(headers):
                                if "Vai trò" in th.inner_text() or "Vai tro" in th.inner_text():
                                    role_col_idx = hi
                                    break
                            
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
                
                print(f"Role for #{so_den} is: {role_value}", file=sys.stderr)
                if role_value in ["Thông báo", "Để biết", "Thong bao", "De biet"]:
                    print(f"-> Auto finish for #{so_den}", file=sys.stderr)
                    docs_to_finish.append((so_den, role_value))
                    
                close_btn = page.query_selector('.rwCloseButton')
                if close_btn:
                    try:
                        close_btn.click()
                        page.wait_for_timeout(2000)
                    except:
                        pass

            next_btn = page.query_selector('.rgPageNext:not(.rgDisabled)')
            if not next_btn:
                break
            try:
                next_btn.click()
                page.wait_for_timeout(3000)
            except:
                break
            
        browser.close()
        
    print(f"\nFound {len(docs_to_finish)} documents to auto-finish.", file=sys.stderr)
    for so_den, role in docs_to_finish:
        reason = f"Đã nhận văn bản (Tự động kết thúc - {role})"
        print(f"Finishing #{so_den}...", file=sys.stderr)
        subprocess.run([python_bin, action_script, "kethuc", str(so_den), reason])
        
    print("Force scan complete.", file=sys.stderr)

if __name__ == '__main__':
    main()
