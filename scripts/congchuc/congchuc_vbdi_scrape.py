"""Scrape Văn bản đi (outgoing documents) from tabid=1121 with date filtering."""
import os, sys, json, re, subprocess, traceback
from datetime import datetime, timedelta

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
UNIT = os.environ.get("CONGVAN_UNIT", "")
TABID = os.environ.get("CONGVAN_DI_TABID", "1121")

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

STATE_DIR = os.path.join(_hermes_home, "cron", "cong-van-di")
STATE_FILE = os.path.join(STATE_DIR, "vbdidi_state.json")

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return {"seen_ids": [], "last_check": "", "last_count": 0, "documents": {}}

def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def extract_documents(html):
    """Parse Văn bản đi RadGrid from HTML."""
    docs = []
    rows = re.findall(r'<tr[^>]*class="\s*rg(?:Alt)?Row\s*"[^>]*>(.*?)</tr>', html, re.DOTALL)
    
    for row_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if len(cells) < 10:
            continue
        
        # Extract VanBanDiID from the first hidden cell
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

def pw_get_documents():
    """Login + set date filter + parse grid using Playwright."""
    today_str = datetime.now().strftime("%d/%m/%Y")
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%d/%m/%Y")
    
    MAX_RETRIES = 2
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                page = browser.new_page()
                
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
                
                # Navigate to Văn bản đi search directly
                page.goto(f"{BASE}/Default.aspx?tabid={TABID}", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                try: page.wait_for_load_state("networkidle", timeout=20000)
                except: pass
                
                # Set date filters
                page.fill('#dnn_ctr4744_VBDi_TimKiem_dtpNgayPhatHanhTu_dateInput', two_days_ago)
                page.fill('#dnn_ctr4744_VBDi_TimKiem_dtpNgayPhatHanhDen_dateInput', today_str)
                
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
                
                # Parse results
                html = page.content()
                all_docs = extract_documents(html)
                if not all_docs:
                    browser.close()
                    continue
                
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
            continue
    
    return []

def main():
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available, cannot scrape Văn bản đi")
        sys.exit(0)
    
    state = load_state()
    existing_ids = set(state.get("seen_ids", []))
    
    docs = pw_get_documents()
    
    new_docs = [d for d in docs if d["vbdi_id"] not in existing_ids]
    
    # Update state
    for d in docs:
        vbdi_id = d["vbdi_id"]
        if vbdi_id and vbdi_id not in state.get("documents", {}):
            if "documents" not in state:
                state["documents"] = {}
            state["documents"][vbdi_id] = {
                "so_ky_hieu": d["so_ky_hieu"],
                "trich_yeu": d["trich_yeu"],
                "ngay_phat_hanh": d["ngay_phat_hanh"],
                "don_vi_soan_thao": d["don_vi_soan_thao"],
                "nguoi_soan_thao": d["nguoi_soan_thao"],
                "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    
    state["seen_ids"] = list(existing_ids | {d["vbdi_id"] for d in docs if d["vbdi_id"]})
    state["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["last_count"] = len(docs)
    save_state(state)
    
    # Output for Zalo delivery (compact)
    if new_docs:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"📋 {len(new_docs)} VB đi mới ({now_str})\n")
        for i, d in enumerate(new_docs, 1):
            trich = d['trich_yeu'][:70]
            print(f"{i}. {d['so_ky_hieu']} ({d['ngay_phat_hanh']})")
            print(f"   {trich} — {d['don_vi_soan_thao']}")
    else:
        # Silent — no new docs
        pass

if __name__ == "__main__":
    main()
