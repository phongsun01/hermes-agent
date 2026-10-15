#!/usr/bin/env python3
"""
congchuc_action.py — Perform remote Chuyển / Kết thúc actions on congchuc.quangninh.gov.vn via Playwright.
Called as a background process by the gateway.
"""

import os
import sys
import re
import datetime

# Ensure we can import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from congvan_status import load_state, save_state, update_status
except ImportError:
    # Fallback state management
    STATE_FILE = os.path.join(
        os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")),
        "cron", "cong-van-den", "vbden_state.json"
    )
    def load_state():
        if os.path.exists(STATE_FILE):
            import json
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"seen_ids": [], "documents": {}}
    def save_state(state):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        import json
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    def update_status(state, so_den, new_status, note=None):
        docs = state.setdefault("documents", {})
        if so_den not in docs:
            docs[so_den] = {"so_den": so_den}
        if new_status:
            docs[so_den]["status"] = new_status
        docs[so_den]["status_updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if note:
            existing_note = docs[so_den].get("note", "")
            docs[so_den]["note"] = (existing_note + " | " + note if existing_note else note).strip(" | ")
        save_state(state)
        return True, "Updated"

# Read environments
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
CONGVAN_UNIT_RAW = os.environ.get("CONGVAN_UNIT", "").strip()
UNITS = [u.strip() for u in CONGVAN_UNIT_RAW.split(",") if u.strip()]
DEFAULT_UNIT = UNITS[0] if UNITS else "2256"

# Create log/output directory
OUTPUT_DIR = os.path.join(_hermes_home, "cron", "cong-van-den", "action_logs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def notify_result(message, image_path=None):
    """Deliver result notification using the Zalo delivery system if available."""
    print(f"[ACTION_RESULT] {message}")
    # Write to a result file for the caller to parse if needed
    res_path = os.path.join(OUTPUT_DIR, "last_result.txt")
    with open(res_path, "w", encoding="utf-8") as f:
        f.write(message)
        if image_path:
            f.write(f"\nIMAGE:{image_path}")

def execute_action(action_type, so_den, extra_args):
    """Execute the action on portal using Playwright."""
    from playwright.sync_api import sync_playwright
    
    so_den = str(so_den).strip()
    print(f"Executing remote {action_type} for document #{so_den}...")
    
    STORAGE_STATE_FILE = os.path.join(_hermes_home, "cron", "cong-van-den", ".playwright_storage.json")
    
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    
    screenshot_dir = os.path.join(_hermes_home, "cron", "cong-van-den", "attachments", so_den)
    os.makedirs(screenshot_dir, exist_ok=True)
    
    try:
        context = None
        session_reused = False
        if os.path.exists(STORAGE_STATE_FILE):
            try:
                print(f"Attempting to reuse Playwright storage state...")
                context = browser.new_context(storage_state=STORAGE_STATE_FILE)
                page = context.new_page()
                page.set_default_timeout(60000)
                
                # Go to DOCS_URL and check if redirect to login page or has login elements
                page.goto(DOCS_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                
                if "Login.aspx" not in page.url and not page.query_selector("#IDToken1"):
                    print(f"Playwright storage state is valid. Session reused!")
                    session_reused = True
                else:
                    print(f"Playwright storage state expired or invalid.")
                    page.close()
                    context.close()
                    context = None
            except Exception as reuse_err:
                print(f"Failed to reuse storage state: {reuse_err}")
                if context:
                    try: context.close()
                    except: pass
                context = None
                
        if not session_reused:
            print(f"Performing fresh login...")
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(60000)
            
            # 1. Login
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)
            page.fill('#IDToken1', USERNAME)
            page.fill('#IDToken2', PASSWORD)
            page.click('#btnLogin')
            page.wait_for_timeout(3000)
            try: page.wait_for_load_state("networkidle", timeout=15000)
            except: pass
            
            # Handle password warning page
            if "CanhBaoMatKhau" in page.url or "PasswordWarning" in page.url:
                try:
                    btn = page.query_selector("input[type=submit], button")
                    if btn:
                        btn.click()
                        page.wait_for_timeout(3000)
                except: pass
                
            # Save storage state for reuse
            try:
                os.makedirs(os.path.dirname(STORAGE_STATE_FILE), exist_ok=True)
                context.storage_state(path=STORAGE_STATE_FILE)
                print(f"Saved Playwright storage state.")
            except: pass
        
        # 2. Select unit
        page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=30000)
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except: pass
        sel = page.query_selector("select[id$=ddlChonDonVi]")
        if sel:
            sel.select_option(DEFAULT_UNIT)
            page.wait_for_timeout(2000)
            try: page.wait_for_load_state("networkidle", timeout=10000)
            except: pass
            
        # 3. Nav to grid
        page.goto(DOCS_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
        try: page.wait_for_load_state("networkidle", timeout=20000)
        except: pass
        
        # 4. Find row
        target_btn = None
        for page_idx in range(15):
            rows = page.query_selector_all('table.rgMasterTable > tbody > tr.rgRow, table.rgMasterTable > tbody > tr.rgAltRow')
            for row in rows:
                link = row.query_selector('a')
                if link and link.inner_text().strip() == so_den:
                    target_btn = row.query_selector("[id*='AutoGeneratedEditButton']")
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
            raise Exception(f"Không tìm thấy văn bản Số đến {so_den} trên danh sách grid.")
            
        # Click Edit
        target_btn.click()
        page.wait_for_timeout(2000)
        
        # 5. Handle action types
        if action_type == "kethuc":
            # Find "Kết thúc" menu item
            menu_link = None
            for a in page.query_selector_all("a.rmLink"):
                if "Kết thúc" in a.inner_text():
                    menu_link = a
                    break
            if not menu_link:
                raise Exception("Không tìm thấy tùy chọn 'Kết thúc' trong menu xử lý.")
                
            menu_link.click()
            page.wait_for_timeout(3000)
            page.wait_for_selector('textarea[id$="wndKetThuc_C_txtNoiDungXuLy"]', timeout=5000)
            
            # Fill reason
            reason = extra_args if extra_args else "Đã hoàn thành xử lý."
            page.fill('textarea[id$="wndKetThuc_C_txtNoiDungXuLy"]', reason)
            
            # Take screenshot before saving
            screenshot_path = os.path.join(screenshot_dir, "kethuc_before_save.png")
            page.screenshot(path=screenshot_path)
            
            # Click Save (btnKetThucw)
            page.click('span[id$="wndKetThuc_C_btnKetThucw"]')
            page.wait_for_timeout(4000)
            try: page.wait_for_load_state("networkidle", timeout=10000)
            except: pass
            
            # Success confirmation
            screenshot_done = os.path.join(screenshot_dir, "kethuc_done.png")
            page.screenshot(path=screenshot_done)
            
            # Update state
            state = load_state()
            update_status(state, so_den, "done", note=f"[Đã Kết thúc từ xa] Lý do: {reason}")
            
            notify_result(f"✅ Đã KẾT THÚC thành công văn bản #{so_den} trên cổng thông tin.\nLý do: {reason}", screenshot_done)
            
        elif action_type == "chuyen":
            # Parse parameters: chuyen <so_den> <phong_ban> [but_phe]
            # default kieu_chuyen is chutri (checkbox index 0)
            parts = extra_args.split(" ", 1)
            target_pb = parts[0].strip()
            but_phe = parts[1].strip() if len(parts) > 1 else "Kính chuyển xử lý."
            
            # Find "Chuyển" menu item
            menu_link = None
            for a in page.query_selector_all("a.rmLink"):
                if "Chuyển" in a.inner_text():
                    menu_link = a
                    break
            if not menu_link:
                raise Exception("Không tìm thấy tùy chọn 'Chuyển' trong menu xử lý.")
                
            menu_link.click()
            page.wait_for_timeout(4000)
            page.wait_for_selector('textarea[id$="txtButPheChung"]', timeout=8000)
            
            # Fill opinion
            page.fill('textarea[id$="txtButPheChung"]', but_phe)
            
            # Find room in grdPhongBan
            pb_rows = page.query_selector_all('div[id$="grdPhongBan"] table.rgMasterTable > tbody > tr')
            target_row = None
            available_pbs = []
            for r in pb_rows:
                text = r.inner_text().strip()
                if not text: continue
                # Extract first word/title
                first_line = text.split("\n")[0]
                available_pbs.append(first_line)
                if target_pb.lower() in first_line.lower():
                    target_row = r
                    break
            
            if not target_row:
                # Try finding in NguoiDung tab if not found in PhongBan
                # Click the NguoiDung tab if needed
                raise Exception(f"Không tìm thấy phòng ban '{target_pb}' trong danh sách. Các phòng ban có sẵn: {', '.join(available_pbs[:6])}...")
                
            cbs = target_row.query_selector_all('input[type="checkbox"]')
            if not cbs:
                raise Exception(f"Không có checkbox chọn vai trò cho phòng ban {target_pb}.")
                
            # Default to index 0 (Chủ trì)
            print(f"Chọn Chủ trì cho: {target_pb}...")
            cbs[0].check()
            page.wait_for_timeout(1000)
            
            # Take screenshot before submit
            screenshot_path = os.path.join(screenshot_dir, "chuyen_before_save.png")
            page.screenshot(path=screenshot_path)
            
            # Submit Chuyen (btnChuyen)
            page.click('span[id$="btnChuyen"]')
            page.wait_for_timeout(4000)
            try: page.wait_for_load_state("networkidle", timeout=10000)
            except: pass
            
            # Success confirmation
            screenshot_done = os.path.join(screenshot_dir, "chuyen_done.png")
            page.screenshot(path=screenshot_done)
            
            # Update state
            state = load_state()
            update_status(state, so_den, "wip", note=f"[Đã Chuyển từ xa] Đơn vị nhận: {target_pb} (Chủ trì) | Ý kiến: {but_phe}")
            
            notify_result(f"✅ Đã CHUYỂN thành công văn bản #{so_den} cho '{target_pb}' (Chủ trì).\nÝ kiến: {but_phe}", screenshot_done)
            
    except Exception as e:
        err_msg = f"❌ Thất bại khi thực hiện '{action_type}' cho văn bản #{so_den}: {str(e)}"
        notify_result(err_msg)
        # Capture error screenshot
        try:
            err_shot = os.path.join(screenshot_dir, "error.png")
            page.screenshot(path=err_shot)
        except:
            pass
        sys.exit(1)
    finally:
        browser.close()
        p.stop()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: congchuc_action.py <kethuc|chuyen> <so_den> [args]")
        sys.exit(1)
        
    act_type = sys.argv[1].lower()
    doc_id = sys.argv[2]
    extra = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
    
    if act_type not in ["kethuc", "chuyen"]:
        print(f"Unknown action: {act_type}")
        sys.exit(1)
        
    execute_action(act_type, doc_id, extra)
