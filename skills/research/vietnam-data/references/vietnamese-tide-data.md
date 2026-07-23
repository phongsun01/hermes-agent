# Vietnamese Tide Data (triều cường)

Tide data for coastal Vietnamese provinces. Essential for coastal regions like Quảng Ninh, Hải Phòng, Đà Nẵng, etc.

## Free Source: tide-forecast.com

**URL format:** `https://www.tide-forecast.com/locations/{LocationName}-Vietnam/tides/latest`

**Confirmed working direct URL:** `https://www.tide-forecast.com/locations/Cam-Pha-Vietnam/tides/latest` (page title reads "Tide Times and Tide Chart for Cam Pha Mines").

### Known working locations:

| Location | URL Slug | Notes |
|----------|----------|-------|
| Cẩm Phả, Quảng Ninh | `Cam-Pha-Vietnam` | 1 low + 1 high tide/day (diurnal pattern typical for Gulf of Tonkin) |
| Hòn Gai (Hạ Long), Quảng Ninh | `Hongay-Vietnam` | Hạ Long city centre — the most relevant location for Quảng Ninh's coastline. Page title: "Tide Times and Tide Chart for Hongay" |
| Hải Phòng | `Haiphong-Vietnam` | Major port city near Quảng Ninh |
| Đồ Sơn, Hải Phòng | `Do-Son-Vietnam` | Coastal resort area |
| Hòn Nẹu, Quảng Ninh | `Hon-Nieu-Vietnam` | Island location |
| *(add more as discovered)* | | |

### HTML scraping approach

The page returns HTML with tide data in `.tide-header-today` (today) and `.tide-day` (upcoming days) divs.

```python
import urllib.request, re

url = 'https://www.tide-forecast.com/locations/Cam-Pha-Vietnam/tides/latest'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    html = r.read().decode('utf-8', errors='replace')

tides = []

# --- Today's tide (from .tide-header-today section) ---
today_match = re.search(
    r'class="tide-header-today[^"]*"[^>]*>(.*?)(?:</div>\s*</div>\s*<div\s+class="banner|</section>)',
    html, re.DOTALL
)
if today_match:
    today_html = today_match.group(1)
    rows = re.findall(
        r'<td>(Low|High)\s+Tide</td>.*?'
        r'<b>\s*([\d:]+\s*(?:AM|PM)?)\s*</b>.*?'
        r'tide-day-tides__secondary[^>]*>\(([^)]+)\)</span>.*?'
        r'js-two-units-length-value__primary[^>]*>([\d.]+)\s*m',
        today_html, re.DOTALL
    )
    for r in rows:
        tides.append({'type': r[0], 'time': r[1].strip(), 'date': r[2], 'height': r[3]})

# --- Upcoming days (from each .tide-day div) ---
parts = html.split('<div class="tide-day">')
for part in parts[1:]:
    rows = re.findall(
        r'<td>(Low|High)\s+Tide</td>.*?'
        r'<b>\s*([\d:]+\s*(?:AM|PM)?)\s*</b>.*?'
        r'tide-day-tides__secondary[^>]*>\(([^)]+)\)</span>.*?'
        r'js-two-units-length-value__primary[^>]*>([\d.]+)\s*m',
        part, re.DOTALL
    )
    for r in rows:
        tides.append({'type': r[0], 'time': r[1].strip(), 'date': r[2], 'height': r[3]})
```

### Regex pattern notes

- **Space before AM/PM is critical**: use `([\d:]+\s*(?:AM|PM)?)` — the `\s*` before `AM|PM` is required because the HTML has `<b> 5:43 AM</b>` (space between time and AM/PM).
- The `tide-day-tides__secondary` class wraps the date like `(Tue 23 June)`.
- The `js-two-units-length-value__primary` class wraps the height in meters (e.g. `1.64 m`).
- Tide-forecast.com uses BEM-style class naming with underscores.

### Browser-based retrieval (alternative to HTML scraping)

When the regex scraping fails (e.g., site restructuring, JS rendering), use the browser tool suite:

```python
# Pseudocode for browser-based extraction
# 1. Navigate directly to the tide page:
#    browser_navigate(url="https://www.tide-forecast.com/locations/Cam-Pha-Vietnam/tides/latest")
#
# 2. Extract full page text via JS:
#    browser_console(expression="document.body.innerText")
#
# 3. The returned text contains structured tide data with sections like:
#    "Tide Times for Cam Pha Mines: Sunday 28 June 2026"
#    "Low Tide\t\t1:55 AM\t\t0.84 m"
#    "High Tide\t\t3:14 PM\t\t3.61 m"
#
# 4. Parse by splitting on "Tide Times for" markers and extracting
#    Low/High Tide lines with regex.
```

**Advantages:** No need to reverse-engineer HTML class names; works even when the page layout changes; avoids regex fragility with HTML whitespace.

**Known limitation:** The browser snapshot accessibility tree often truncates the tide table. Use `browser_console` with `document.body.innerText` (up to ~12K chars fits in one call) or slice the text with `.substring(0, N)` for pagination.

### Discovering location slugs via homepage HTML

To find available Vietnam locations on tide-forecast.com **without** interactive browsing (JSON via curl):

```bash
curl -sL "https://www.tide-forecast.com/" | grep -i "Vietnam"
```

This returns the `<select>` options embedded in the homepage. Look for the `location_filename_part` dropdown. All Vietnam locations are listed as:

```html
<option value="Cam-Pha-Vietnam">Cam Pha</option>
<option value="Hongay-Vietnam">Hongay</option>
<option value="Haiphong-Vietnam">Haiphong</option>
...
```

The `value` attribute is the URL slug: append it to `https://www.tide-forecast.com/locations/{slug}/tides/latest`.

**Note:** The site returns 404 for many direct URLs if the precise slug format is wrong. Always verify slug by extracting it from the homepage HTML first.

### curl + grep approach for single-request tide data

For a quick one-shot tide check without regex parsing:

```bash
curl -sL "https://www.tide-forecast.com/locations/Hongay-Vietnam/tides/latest" | grep -oP 'Tide Times for [^<]+|Low Tide[^<]*|High Tide[^<]*|js-two-units-length-value__primary[^>]*>([^<]+)'
```

Better: extract the `tide-header-summary` paragraph which contains a human-readable summary:

```bash
curl -sL "https://www.tide-forecast.com/locations/Hongay-Vietnam/tides/latest" | grep -oP '(?<=tide-header-summary">).*?(?=</p>)'
```

Returns: `The predicted tide times today on Tuesday 30 June 2026 for Hongay are: first low tide at  4:36am, first high tide at  4:48pm. Sunrise is at  5:13am and sunset is at  6:37pm.`

### Tide icon mapping by height

```python
def tide_icon(tide_type, height_m):
    h = float(height_m)
    if tide_type == 'High':
        if h >= 3.5: return '🔴'   # High spring tide (risk of coastal flooding)
        elif h >= 2.5: return '🟠' # Moderate high tide
        else: return '🟡'          # Low high tide
    else:  # Low
        if h <= 0.8: return '🔵'   # Very low tide
        elif h <= 1.5: return '🟢' # Moderate low tide
        else: return '⚪'          # High low tide
```

### Tidal pattern notes for Quảng Ninh

- **Tidal pattern**: Primarily **diurnal** (one high, one low per day) in the Gulf of Tonkin
- **Typical range**: 2–4m (spring tides around new/full moon)
- **Spring tides**: ~3.5–4m (🔴 alert level for coastal flooding)
- **Neap tides**: ~1.5–2.5m

### Computational fallback (lunar-based estimation)

When web-scraping sources return 404/403/timeout (common with bot-blocking), fall back to lunar-phase tide estimation. The approach calculates approximate high/low tide times based on the moon's position and the known diurnal tidal regime of the Gulf of Tonkin.

**Assumptions for Ha Long Bay:**
- **Diurnal regime** (K1/O1 constituents dominate): one primary high + one primary low per day
- **Tidal lag**: ~3.5h after moon transit
- **Spring range**: ~3.8m (new/full moon)
- **Neap range**: ~1.5m (quarter moons)
- **Mean sea level** (above chart datum): ~1.9m

**Run the pre-built script:**
```bash
uv run python3 /opt/data/skills/research/vietnam-data/scripts/tide_estimate.py
# Editable: set lat, lon, location_name and days at the bottom of the script
```

The script:
1. Calculates **Julian Day** for the target date
2. Computes **moon phase** from mean elongation (D = 297.85 + 445267.11×T)
3. Derives **tidal coefficient** (0.5 = neap, 1.0 = spring)
4. Estimates **moon transit time** from moon age
5. Applies **tidal lag** (~3.5h for HL Bay) → high tide time
6. Reports both daily tides (primary + secondary, though secondary is often weak in diurnal regimes)

**Warning:** This is ±1-2h accurate. Real conditions vary with weather (atmospheric pressure, onshore winds raise levels), bathymetry, and seasonal freshwater flow. Always treat as directional advice, not exact.

**When to use:**
- User asks for a tide overview ("lịch thủy triều 7 ngày") and web sources unreachable
- User is in Quảng Ninh (tidal patterns known)
- Quick reference when accuracy ±1h is acceptable (planning beach trips, fishing, boating)

**When NOT to use:**
- Navigation-critical or safety-critical timing
- Port operations needing exact arrival/departure windows
- Areas with mixed/semidiurnal regimes where the simplified diurnal model breaks down
