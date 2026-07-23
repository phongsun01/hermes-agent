#!/usr/bin/env python3
"""
congvan_detail.py — Lấy chi tiết văn bản từ congchuc.quangninh.gov.vn
Dùng Playwright để login, tìm văn bản, mở form chi tiết và in thông tin.

Usage:
  uv run python <path>/congvan_detail.py <số_đến>
  uv run python <path>/congvan_detail.py 2497
"""
import sys, os, json, re

# Load env
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

so_den_target = sys.argv[1].strip() if len(sys.argv) > 1 else ""

def extract_info(page):
    """Trích xuất thông tin từ form chi tiết văn bản."""
    info = {}

    # Labels và giá trị từ các cặp label-input trong form
    label_map = {
        "Số đến": "so_den",
        "Số ký hiệu": "so_ky_hieu",
        "Số công văn": "so_cong_van",
        "Ngày đến": "ngay_den",
        "Ngày văn bản": "ngay_vb",
        "Hạn xử lý": "han_xl",
        "Tác giả": "tac_gia",
        "Trích yếu": "trich_yeu",
        "Phương thức nhận": "phuong_thuc_nhan",
        "Loại văn bản": "loai_vb",
        "Độ khẩn": "do_khan",
        "Độ mật": "do_mat",
        "Ngày ký": "ngay_ky",
        "Người ký": "nguoi_ky",
    }

    # Tìm các cặp label-value trong form
    for label_text, key in label_map.items():
        # Tìm label element chứa text, rồi lấy giá trị từ ô input/span/textbox kế bên
        try:
            # XPath: label chứa text, lấy element tiếp theo (td/div/span chứa value)
            label_el = page.query_selector(f"td:has-text('{label_text}') ~ td, "
                                           f"label:has-text('{label_text}') + input, "
                                           f"span:has-text('{label_text}') ~ span, "
                                           f"td:has-text('{label_text}')")
            if label_el:
                parent = label_el.evaluate("el => el.parentElement?.innerText?.trim() || ''")
                if parent:
                    info[key] = parent
        except:
            pass

    # Tìm trực tiếp các input/span có chứa giá trị (fallback)
    try:
        # Textarea nội dung xử lý (bút phê)
        noidung_el = page.query_selector('textarea[id$="txtNoiDungXuLy"]')
        if noidung_el:
            info["but_phe"] = noidung_el.inner_text().strip()
    except:
        pass

    return info


from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
page = browser.new_page()

try:
    # 1. Login
    print("🔑 Đang đăng nhập...", file=sys.stderr)
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)
    page.fill('#IDToken1', USERNAME)
    page.fill('#IDToken2', PASSWORD)
    page.click('#btnLogin')
    page.wait_for_timeout(3000)
    try: page.wait_for_load_state("networkidle", timeout=15000)
    except: pass

    # 2. Select unit
    print("🏢 Đang chọn đơn vị...", file=sys.stderr)
    page.goto(BASE_URL + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=30000)
    try: page.wait_for_load_state("networkidle", timeout=10000)
    except: pass
    sel = page.query_selector("select[id$=ddlChonDonVi]")
    if sel:
        sel.select_option(DEFAULT_UNIT)
        page.wait_for_timeout(2000)
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except: pass

    # 3. Nav to docs grid
    print(f"📋 Đang vào danh sách văn bản...", file=sys.stderr)
    page.goto(DOCS_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    try: page.wait_for_load_state("networkidle", timeout=20000)
    except: pass

    # 4. Find row
    print(f"🔎 Đang tìm văn bản #{so_den_target}...", file=sys.stderr)
    found = False
    row_data = {}

    for page_idx in range(20):
        rows = page.query_selector_all(
            'table.rgMasterTable > tbody > tr.rgRow, '
            'table.rgMasterTable > tbody > tr.rgAltRow'
        )
        for row in rows:
            link = row.query_selector('a')
            if link and link.inner_text().strip() == so_den_target:
                found = True
                # Thu thập thông tin từ grid cells
                cells = row.query_selector_all('td')
                full_text = " | ".join(c.inner_text().strip() for c in cells)
                row_data["grid_raw"] = full_text
                row_data["so_den"] = so_den_target

                # Click Edit để mở form chi tiết
                edit_btn = row.query_selector("[id*='AutoGeneratedEditButton']")
                if edit_btn:
                    edit_btn.click()
                    page.wait_for_timeout(3000)
                    try: page.wait_for_load_state("networkidle", timeout=10000)
                    except: pass

                    # Lấy thông tin từ form edit
                    form_info = extract_info(page)
                    row_data.update(form_info)

                    # Chụp screenshot
                    os.makedirs("/tmp/congchuc_screenshots", exist_ok=True)
                    page.screenshot(path=f"/tmp/congchuc_screenshots/{so_den_target}.png")

                break
        if found:
            break

        next_btn = page.query_selector('.rgPageNext:not(.rgDisabled)')
        if not next_btn:
            break
        next_btn.click()
        page.wait_for_timeout(3000)
        try: page.wait_for_load_state("networkidle", timeout=15000)
        except: pass

    if not found:
        # Fallback: lấy từ state
        print(f"⚠️ Không tìm thấy #{so_den_target} trên grid. Thử lấy từ state...", file=sys.stderr)
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, os.path.join(os.path.dirname(__file__), "../congvan_status.py"),
                 "status", so_den_target],
                capture_output=True, text=True, timeout=15
            )
            print(result.stdout)
        except:
            print(f"❌ Không tìm thấy văn bản #{so_den_target}")
        sys.exit(1)

    # Output
    print(f"\n✅ CHI TIẾT VĂN BẢN #{so_den_target}")
    print("=" * 50)

    # Map fields để in
    display = {
        "Số công văn": row_data.get("so_cong_van", row_data.get("so_ky_hieu", "")),
        "Cơ quan gửi": row_data.get("tac_gia", ""),
        "Ngày đến": row_data.get("ngay_den", ""),
        "Ngày văn bản": row_data.get("ngay_vb", ""),
        "Hạn xử lý": row_data.get("han_xl", ""),
        "Trích yếu": row_data.get("trich_yeu", ""),
        "Phương thức nhận": row_data.get("phuong_thuc_nhan", ""),
        "Bút phê": row_data.get("but_phe", ""),
    }

    for label, val in display.items():
        if val:
            print(f"  {label}: {val}")

except Exception as e:
    print(f"❌ Lỗi: {str(e)}", file=sys.stderr)
    try:
        os.makedirs("/tmp/congchuc_screenshots", exist_ok=True)
        page.screenshot(path=f"/tmp/congchuc_screenshots/error_{so_den_target}.png")
    except:
        pass
    sys.exit(1)
finally:
    browser.close()
    p.stop()
