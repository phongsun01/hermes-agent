import os, sys, re
from playwright.sync_api import sync_playwright

_hermes_home = "/opt/data"
_env_path = os.path.join(_hermes_home, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

USER = os.environ.get("CONGVAN_USER", "")
PASS = os.environ.get("CONGVAN_PASS", "")
BASE = "https://congchuc.quangninh.gov.vn"
STORAGE_STATE_FILE = os.path.join(_hermes_home, "cron", "cong-van-den", ".playwright_storage.json")

sys.path.insert(0, "/opt/data/scripts/congchuc")
from congchuc_vbdi_search import extract_documents

def main():
    query_str = "188"
    unit_spec = "2256" # Bệnh viện Sản nhi
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(storage_state=STORAGE_STATE_FILE)
        page = context.new_page()
        page.set_default_timeout(30000)
        
        print("Navigating to tabid=56...")
        page.goto(f"{BASE}/Default.aspx?tabid=56", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        print("Selecting unit...")
        sel = page.query_selector("select[id$=ddlChonDonVi]")
        if sel:
            sel.select_option(value=unit_spec)
            print("Selected. Waiting for reload...")
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
        else:
            print("Select dropdown not found!")
            
        print("Navigating to tabid=1121...")
        page.goto(f"{BASE}/Default.aspx?tabid=1121", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
        
        print("Filling search input...")
        page.fill('#dnn_ctr4744_VBDi_TimKiem_tbSearch', query_str)
        
        print("Clicking search...")
        page.evaluate("""
            (function() {
                var btn = document.getElementById('dnn_ctr4744_VBDi_TimKiem_btnSearch');
                if (btn) btn.click();
            })();
        """)
        page.wait_for_timeout(5000)
        page.wait_for_load_state("networkidle")
        
        print("Parsing current page docs...")
        html = page.content()
        parsed_docs = extract_documents(html)
        print(f"Parsed {len(parsed_docs)} docs on page 1:")
        for d in parsed_docs:
            print(f"  - {d['so_ky_hieu']} | {d['don_vi_soan_thao']} | {d['trich_yeu']}")
        
        # Check next page button
        next_btn = page.query_selector(".rgPageNext")
        if next_btn:
            is_disabled = next_btn.evaluate("el => el.classList.contains('rgDisabled')")
            print(f"Next button found. Is disabled: {is_disabled}.")
        else:
            print("Next button not found!")
            
        browser.close()

if __name__ == "__main__":
    main()
