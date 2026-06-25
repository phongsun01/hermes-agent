"""Debug VB đến document extraction."""
import os, sys, re
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

p = sync_playwright().start()
browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
page = browser.new_page()

# Login
page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
page.wait_for_timeout(2000)
page.evaluate(f"""
    document.getElementById('IDToken1').value = '{USER}';
    document.getElementById('IDToken2').value = '{PASS}';
    document.getElementById('btnLogin').click();
""")
page.wait_for_timeout(5000)
try:
    page.wait_for_load_state("networkidle", timeout=15000)
except:
    pass

# Unit select
UNIT = "2256"
page.goto(BASE + "/Default.aspx?tabid=56", wait_until="domcontentloaded", timeout=30000)
try:
    page.wait_for_load_state("networkidle", timeout=15000)
except:
    pass
sel = page.query_selector("select[id$=ddlChonDonVi]")
if sel:
    sel.select_option(UNIT)
    page.wait_for_timeout(2000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    print("Unit selected:", UNIT, file=sys.stderr)

# Navigate to docs
page.goto(DOCS_URL, wait_until="domcontentloaded", timeout=45000)
page.wait_for_timeout(3000)
try:
    page.wait_for_load_state("networkidle", timeout=20000)
except:
    pass

# Extract
html = page.content()
print(f"Page size: {len(html)} bytes", file=sys.stderr)

# Check for rgRow
rg_rows = re.findall(r'<tr[^>]*class="\s*rgRow\s*"[^>]*>', html)
alt_rows = re.findall(r'<tr[^>]*class="\s*rgAltRow\s*"[^>]*>', html)
print(f"rgRow matches: {len(rg_rows)}", file=sys.stderr)
print(f"rgAltRow matches: {len(alt_rows)}", file=sys.stderr)

# Check for grid presence
if "grdVBDenChoXuLy" in html:
    print("Grid grdVBDenChoXuLy found", file=sys.stderr)
elif "RadGrid" in html:
    print("RadGrid found", file=sys.stderr)
else:
    print("NO GRID FOUND", file=sys.stderr)

# Check all tr classes
all_trs = re.findall(r'<tr[^>]*class="([^"]*)"', html)
classes = set()
for c in all_trs:
    if 'rg' in c:
        classes.add(c)
print(f"rg* classes: {classes}", file=sys.stderr)

# Try broader matching
all_rows = re.findall(r'<tr[^>]*class="[^"]*\brgRow\b[^"]*"[^>]*>.*?</tr>', html, re.DOTALL)
print(f"Broader rgRow match: {len(all_rows)}", file=sys.stderr)
if all_rows:
    print(f"First row snippet: {all_rows[0][:200]}", file=sys.stderr)

browser.close()
p.stop()
