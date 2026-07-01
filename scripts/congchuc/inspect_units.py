import sys
import os
from playwright.sync_api import sync_playwright

# Load env
_hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
_env_path = os.path.join(_hermes_home, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

USERNAME = os.environ.get("CONGVAN_USER", "")
PASSWORD = os.environ.get("CONGVAN_PASS", "")
DOCS_URL = os.environ.get("CONGVAN_URL", "https://congchuc.quangninh.gov.vn/Default.aspx?tabid=1126")
if "/Default.aspx" in DOCS_URL:
    BASE_URL = DOCS_URL.split("/Default.aspx")[0]
else:
    BASE_URL = DOCS_URL.rstrip("/")
LOGIN_URL = BASE_URL + "/SSO/Login.aspx"
STATE_DIR = os.path.join(_hermes_home, "cron", "cong-van-den")
STORAGE_STATE_FILE = os.path.join(STATE_DIR, ".playwright_storage.json")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        
        # Load session if available
        context = None
        if os.path.exists(STORAGE_STATE_FILE):
            print("Loading storage state...")
            context = browser.new_context(storage_state=STORAGE_STATE_FILE)
        else:
            print("No storage state found, creating new context...")
            context = browser.new_context()
            
        page = context.new_page()
        page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        
        # Check if redirected to login
        if "Login.aspx" in page.url or page.query_selector("#IDToken1"):
            print("Session expired or invalid, performing login...")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            page.fill('#IDToken1', USERNAME)
            page.fill('#IDToken2', PASSWORD)
            page.click('#btnLogin')
            page.wait_for_timeout(3000)
            page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            
            # Save storage state
            os.makedirs(STATE_DIR, exist_ok=True)
            context.storage_state(path=STORAGE_STATE_FILE)
            print("Saved storage state.")
            
        sel = page.query_selector("select[id$=ddlChonDonVi]")
        if sel:
            selected_val = sel.evaluate("el => el.value")
            print(f"Current selected unit value: {selected_val}")
            options = []
            for o in sel.query_selector_all("option"):
                val = o.get_attribute("value")
                txt = o.inner_text().strip()
                selected = " (SELECTED)" if val == selected_val else ""
                options.append(f"Value: {val} | Text: {txt}{selected}")
            print(f"Found {len(options)} options in ddlChonDonVi:")
            for opt in options:
                print("  " + opt)
        else:
            print("Dropdown ddlChonDonVi not found on page. URL:", page.url)
            
        browser.close()

if __name__ == "__main__":
    main()
