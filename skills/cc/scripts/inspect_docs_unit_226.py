import sys
import os
import re
from playwright.sync_api import sync_playwright
from html.parser import HTMLParser

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

def extract_documents(html):
    docs = []
    rows = re.findall(r'<tr[^>]*class="\s*rg(?:Alt)?Row\s*"[^>]*>(.*?)</tr>', html, re.DOTALL)
    for r_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r_html, re.DOTALL)
        if len(cells) < 12:
            continue
        so_den = re.sub(r'<[^>]+>', '', cells[2]).strip()
        so_ky_hieu = re.sub(r'<[^>]+>', '', cells[4]).strip()
        trich_yeu = re.sub(r'<[^>]+>', '', cells[6]).strip()
        docs.append({"so_den": so_den, "so_ky_hieu": so_ky_hieu, "trich_yeu": trich_yeu[:40]})
    return docs

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(storage_state=STORAGE_STATE_FILE)
        page = context.new_page()
        
        # Go to unit select page and select 226 (Sở Y tế)
        print("Selecting unit 226...")
        page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        sel = page.query_selector("select[id$=ddlChonDonVi]")
        if sel:
            sel.select_option(value="226")
            page.wait_for_timeout(3000)
            
        # Go to docs page
        print("Navigating to DOCS_URL...")
        page.goto(DOCS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        
        html = page.content()
        docs = extract_documents(html)
        print(f"Found {len(docs)} documents on page 1 of Unit 226:")
        for d in docs:
            print(f"  #{d['so_den']} | {d['so_ky_hieu']} | {d['trich_yeu']}")
            
        browser.close()

if __name__ == "__main__":
    main()
