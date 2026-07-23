#!/usr/bin/env python3
"""Daily weather report + Tide info for Quảng Ninh, Vietnam — delivered at 06:00 VN time."""

import urllib.request, json, datetime, sys, time, re

LAT, LON = "20.9505", "107.0734"
MAX_RETRIES = 3
RETRY_DELAY = 5

# ============================================================
# WEATHER DATA
# ============================================================

# ============================================================
# MAIN
# ============================================================

import argparse
import urllib.parse

TIDE_LOCATIONS = {
    "quảng ninh": "Cam-Pha-Vietnam",
    "cẩm phả": "Cam-Pha-Vietnam",
    "hạ long": "Cam-Pha-Vietnam",
    "hải phòng": "Haiphong-Vietnam",
    "đà nẵng": "Da-Nang-Vietnam",
    "quy nhơn": "Qui-Nhon-Vietnam",
    "nha trang": "Nha-Trang-Vietnam",
    "vũng tàu": "Vung-Tau-Vietnam",
    "hồ chí minh": "Ho-Chi-Minh-City-Vietnam",
    "sài gòn": "Ho-Chi-Minh-City-Vietnam",
    "tphcm": "Ho-Chi-Minh-City-Vietnam"
}

def fetch_weather(location=None):
    """Fetch weather data from wttr.in with retry logic."""
    if location:
        loc_encoded = urllib.parse.quote(location)
        url = f'https://wttr.in/{loc_encoded}?format=j1'
    else:
        url = f'https://wttr.in/{LAT},{LON}?format=j1'
        
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; HermesBot/1.0)',
                    'Accept': 'application/json',
                }
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
                data = json.loads(raw)

            if 'current_condition' not in data or not data['current_condition']:
                raise ValueError("Missing current_condition in response")
            if 'weather' not in data or not data['weather']:
                raise ValueError("Missing weather forecast in response")

            return data

        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                json.JSONDecodeError, ValueError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    print(f"Lỗi lấy dữ liệu thời tiết sau {MAX_RETRIES} lần thử: {last_error}")
    sys.exit(1)


def get_tide_url(location):
    if not location:
        return TIDE_URL
    loc_lower = location.lower().strip()
    for k, v in TIDE_LOCATIONS.items():
        if k in loc_lower:
            return f"https://www.tide-forecast.com/locations/{v}/tides/latest"
    return None


def fetch_tides(tide_url):
    """Fetch tide data from tide-forecast.com."""
    if not tide_url:
        return None, "Không hỗ trợ dữ liệu triều cường cho khu vực này."
    try:
        req = urllib.request.Request(
            tide_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; HermesBot/1.0)',
                'Accept': 'text/html',
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None, f"Lỗi kết nối: {e}"

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

    # --- Upcoming days (from .tide-day divs) ---
    day_parts = html.split('<div class="tide-day">')
    for part in day_parts[1:]:
        date_m = re.search(r'<h4[^>]*class="tide-day__date"[^>]*>(.*?)</h4>', part)
        if not date_m:
            continue
        date_text = re.sub(r'<[^>]+>', ' ', date_m.group(1))
        date_text = re.sub(r'\s+', ' ', date_text).strip()

        rows = re.findall(
            r'<td>(Low|High)\s+Tide</td>.*?'
            r'<b>\s*([\d:]+\s*(?:AM|PM)?)\s*</b>.*?'
            r'tide-day-tides__secondary[^>]*>\(([^)]+)\)</span>.*?'
            r'js-two-units-length-value__primary[^>]*>([\d.]+)\s*m',
            part, re.DOTALL
        )
        for r in rows:
            tides.append({'type': r[0], 'time': r[1].strip(), 'date': r[2], 'height': r[3]})

    if not tides:
        return None, "Không tìm thấy dữ liệu triều cường."
    return tides, None



# ============================================================
# WEATHER ICONS
# ============================================================

def weather_icon(desc):
    d = desc.lower()
    if 'sunny' in d or 'clear' in d:
        return '☀️'
    if 'partly cloudy' in d:
        return '⛅'
    if 'cloudy' in d or 'overcast' in d:
        return '☁️'
    if 'torrential' in d or 'heavy rain' in d:
        return '🌧️'
    if 'thundery' in d or 'thunder' in d:
        return '⛈️'
    if 'light rain' in d or 'patchy rain' in d:
        return '🌦️'
    if 'rain' in d or 'drizzle' in d:
        return '🌧️'
    if 'fog' in d or 'mist' in d or 'haze' in d or 'smoke' in d:
        return '🌫️'
    if 'snow' in d or 'sleet' in d:
        return '❄️'
    return '🌈'


def moon_icon(phase):
    p = phase.lower()
    if 'new' in p:
        return '🌑'
    if 'waxing crescent' in p:
        return '🌒'
    if 'first quarter' in p:
        return '🌓'
    if 'waxing gibbous' in p:
        return '🌔'
    if 'full' in p:
        return '🌕'
    if 'waning gibbous' in p:
        return '🌖'
    if 'last quarter' in p or 'third quarter' in p:
        return '🌗'
    if 'waning crescent' in p:
        return '🌘'
    return '🌙'


def tide_icon(tide_type, height_m):
    """Return appropriate icon based on tide type and height."""
    h = float(height_m)
    if tide_type == 'High':
        if h >= 3.5:
            return '🔴'  # High spring tide
        elif h >= 2.5:
            return '🟠'  # Moderate high tide
        else:
            return '🟡'  # Low high tide
    else:  # Low
        if h <= 0.8:
            return '🔵'  # Very low tide
        elif h <= 1.5:
            return '🟢'  # Moderate low tide
        else:
            return '⚪'  # High low tide


# ============================================================
# MAIN
# ============================================================

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--location", default="Quảng Ninh", help="Location name")
    parser.add_argument("--mode", choices=["both", "weather", "tide"], default="both", help="Execution mode")
    args = parser.parse_args()

    location = args.location
    is_qn = location.lower().strip() in ("quảng ninh", "quang ninh")

    # If tide only, we don't strictly need weather, but let's fetch it or keep it simple.
    if args.mode == "tide":
        tide_url = get_tide_url(location)
        tides, tide_error = fetch_tides(tide_url)
        lines = [
            f"🌊 BẢN TIN TRIỀU CƯỜNG — {location.upper()}",
            "══════════════════════════════════════",
            ""
        ]
        if tides:
            now_vn = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
            now_en = now_vn.strftime('%a %e')
            today_tides = []
            for t in tides:
                if now_en in t['date']:
                    today_tides.append(t)
            
            display = sorted(today_tides, key=lambda x: 0 if x['type'] == 'Low' else 1)
            for ht in display:
                ico = tide_icon(ht['type'], ht['height'])
                lines.append(f"   {ico} {ht['type']}: {ht['time']} ({ht['height']}m)")
            
            if not display:
                for t in tides[:3]:
                    ico = tide_icon(t['type'], t['height'])
                    lines.append(f"   {ico} {t['type']}: {t['time']} ({t['date']}) - {t['height']}m")
        else:
            lines.append(f"   ❌ {tide_error or 'Không có dữ liệu'}")
            
        lines.append("")
        lines.append("══════════════════════════════════════")
        lines.append("📡 Nguồn: tide-forecast.com")
        print("\n".join(lines))
        return

    # For both or weather modes
    if is_qn:
        data = fetch_weather(None)
    else:
        data = fetch_weather(location)

    # --- Current conditions ---
    cur = data['current_condition'][0]
    temp = cur['temp_C']
    feels = cur['FeelsLikeC']
    desc = cur['weatherDesc'][0]['value']
    humidity = cur['humidity']
    wind = cur['windspeedKmph']
    wind_dir = cur['winddir16Point']
    uv = cur['uvIndex']
    vis = cur['visibility']
    cloud = cur['cloudcover']
    pressure = cur['pressure']

    icon_now = weather_icon(desc)

    # --- Today's forecast ---
    today = data['weather'][0]
    high = today['maxtempC']
    low = today['mintempC']
    sunrise = today['astronomy'][0]['sunrise']
    sunset = today['astronomy'][0]['sunset']
    moon_phase = today['astronomy'][0]['moon_phase']


    # Day name in Vietnamese (có dấu)
    weekday_map = {
        'Mon': 'Thứ Hai', 'Tue': 'Thứ Ba', 'Wed': 'Thứ Tư',
        'Thu': 'Thứ Năm', 'Fri': 'Thứ Sáu', 'Sat': 'Thứ Bảy',
        'Sun': 'Chủ Nhật'
    }

    # Wind direction tiếng Việt
    wind_dir_vn = {
        'N': 'Bắc', 'NNE': 'Bắc Đông Bắc', 'NE': 'Đông Bắc',
        'ENE': 'Đông Đông Bắc', 'E': 'Đông', 'ESE': 'Đông Đông Nam',
        'SE': 'Đông Nam', 'SSE': 'Nam Đông Nam', 'S': 'Nam',
        'SSW': 'Nam Tây Nam', 'SW': 'Tây Nam', 'WSW': 'Tây Tây Nam',
        'W': 'Tây', 'WNW': 'Tây Tây Bắc', 'NW': 'Tây Bắc',
        'NNW': 'Bắc Tây Bắc'
    }

    date_str = today['date']
    try:
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        day_name_en = dt.strftime('%a')
        day_vi = weekday_map.get(day_name_en, day_name_en)
        date_vn = dt.strftime('%d/%m/%Y')
    except Exception:
        day_vi = ''
        date_vn = date_str

    now_vn = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=7)
    time_str = now_vn.strftime('%H:%M')
    wind_vi = wind_dir_vn.get(wind_dir, wind_dir)

    # --- Fetch tide data ---
    tides, tide_error = fetch_tides(get_tide_url(location))

    # ============================================================
    # BUILD REPORT
    # ============================================================

    lines = []
    lines.append(f"🌤  BẢN TIN THỜI TIẾT — {day_vi}, {date_vn}")
    lines.append("")
    lines.append(f"📍 Khu vực: {location.title()}")
    lines.append(f"🕐 Cập nhật lúc: {time_str} (giờ VN)")
    lines.append("══════════════════════════════════════")
    lines.append("")


    # --- HIỆN TẠI ---
    lines.append(f"🔴 HIỆN TẠI")
    lines.append(f"   {icon_now}  {desc}")
    lines.append(f"   🌡  Nhiệt độ: {temp}°C (cảm giác {feels}°C)")
    lines.append(f"   💧 Độ ẩm: {humidity}%")
    lines.append(f"   💨 Gió: {wind} km/h (hướng {wind_vi})")
    lines.append(f"   ☁️  Mây che phủ: {cloud}%")
    lines.append(f"   👁  Tầm nhìn: {vis} km")
    lines.append(f"   🔽 Áp suất: {pressure} hPa")
    lines.append(f"   ☀️  UV Index: {uv}")
    lines.append("")

    # --- HÔM NAY ---
    icon_today = weather_icon(today['hourly'][4]['weatherDesc'][0]['value'])
    moon_ico = moon_icon(moon_phase)
    lines.append(f"📅 HÔM NAY")
    lines.append(f"   {icon_today} Cao nhất: {high}°C | Thấp nhất: {low}°C")
    lines.append(f"   🌅 Mặt trời mọc: {sunrise} | lặn: {sunset}")
    lines.append(f"   {moon_ico} Mặt trăng: {moon_phase}")
    lines.append("")

    # --- TRIỀU CƯỜNG ---
    tide_url = get_tide_url(location)
    if tide_url:
        lines.append(f"🌊 TRIỀU CƯỜNG ({location.title()})")
        if tides:
            # Find today's date (e.g. "Tue 23 June") from current day
            now_en = now_vn.strftime('%a %e')
            # Filter tide entries that belong to today's date
            today_tides = []
            next_day_tides = []
            for t in tides:
                if now_en in t['date']:
                    today_tides.append(t)
                elif len(today_tides) > 0 and len(next_day_tides) < 2:
                    next_day_tides.append(t)

            # Show today's tides (sorted: Low first, then High)
            display = sorted(today_tides, key=lambda x: 0 if x['type'] == 'Low' else 1)
            for ht in display[:2]:
                ico = tide_icon(ht['type'], ht['height'])
                lines.append(f"   {ico} {ht['type']}: {ht['time']} ({ht['height']}m)")

            # Show next tide if only 1 today
            if not display:
                for t in tides[:2]:
                    ico = tide_icon(t['type'], t['height'])
                    lines.append(f"   {ico} {t['type']}: {t['time']} ({t['date']}) - {t['height']}m")
        else:
            lines.append(f"   ❌ {tide_error or 'Không có dữ liệu'}")
        lines.append("")


    # --- THEO GIỜ (6h-22h) ---
    lines.append("🕒 THEO GIỜ")
    for h in today['hourly']:
        hour = int(h['time']) // 100
        if hour < 6 or hour > 22:
            continue
        h_temp = h['tempC']
        h_feel = h['FeelsLikeC']
        h_desc = h['weatherDesc'][0]['value']
        h_icon = weather_icon(h_desc)
        h_rain = int(h.get('chanceofrain', '0'))
        h_hum = h['humidity']
        h_wind = h['windspeedKmph']
        rain_str = f" 💧{h_rain}%" if h_rain >= 30 else ""
        lines.append(
            f"   {hour:02d}h {h_icon} {h_temp}°C (feel {h_feel}) | "
            f"{h_desc}{rain_str} | Ẩm: {h_hum}% | Gió: {h_wind}km/h"
        )
    lines.append("")

    # --- 3 NGÀY TỚI ---
    forecast_days = data['weather'][1:4]
    if forecast_days:
        lines.append("📆 3 NGÀY TỚI")
        for day in forecast_days:
            d = day['date']
            d_high = day['maxtempC']
            d_low = day['mintempC']
            d_desc = day['hourly'][4]['weatherDesc'][0]['value']
            d_icon = weather_icon(d_desc)
            try:
                dd = datetime.datetime.strptime(d, '%Y-%m-%d')
                dn = weekday_map.get(dd.strftime('%a'), '')
                lines.append(f"   {d_icon} {dn} {dd.strftime('%d/%m')}: {d_high}°C / {d_low}°C — {d_desc}")
            except Exception:
                lines.append(f"   {d_icon} {d}: {d_high}°C / {d_low}°C — {d_desc}")
    lines.append("")

    # --- KHUYẾN NGHỊ ---
    lines.append("💡 KHUYẾN NGHỊ")
    recs = []
    try:
        humidity_i = int(humidity)
        wind_i = int(wind)
        uv_i = int(uv)
        cloud_i = int(cloud)
        temp_i = int(temp)

        if humidity_i > 85:
            recs.append("💧 Độ ẩm cao, dễ bị đầm mồ hôi, giữ nhà cửa thông thoáng.")
        if wind_i > 30:
            recs.append("💨 Gió mạnh, hạn chế đi lại ngoài trời, đội mũ bảo vệ.")
        if uv_i >= 6:
            recs.append("☀️ UV cao, bôi kem chống nắng khi ra ngoài.")
        if cloud_i > 70:
            recs.append("☁️ Trời nhiều mây, có thể có mưa, mang theo ô/dù.")
        if temp_i >= 35:
            recs.append("🥵 Nóng bức, uống nhiều nước, tránh nắng 11h-15h.")
        elif temp_i <= 18:
            recs.append("🥶 Trời lạnh, mặc ấm để giữ ấm cơ thể.")

        # Rain chance
        if any(
            int(h.get('chanceofrain', '0')) > 50
            for h in today['hourly']
            if 6 <= int(h['time']) // 100 <= 12
        ):
            recs.append("🌧 Khả năng mưa buổi sáng, nhớ mang theo ô/dù.")
        elif any(
            int(h.get('chanceofrain', '0')) > 50
            for h in today['hourly']
        ):
            recs.append("🌧 Khả năng mưa trong ngày, nhớ mang theo ô/dù.")

        # Tide-based recs
        if tides:
            high_tides_today = [t for t in tides if t['type'] == 'High' and 'Jun' in t['date']]
            for ht in high_tides_today[:1]:
                h_val = float(ht['height'])
                if h_val >= 3.5:
                    recs.append(f"🔴 Triều cường cao ({h_val}m), các khu vực ven biển chú ý ngập úng.")
                elif h_val >= 3.0:
                    recs.append(f"🟠 Triều cường khá cao ({h_val}m), đề phòng nước dâng ven biển.")
    except Exception:
        pass

    if not recs:
        recs.append("✅ Điều kiện thời tiết bình thường.")
    lines.extend(recs)

    # --- Footer ---
    lines.append("")
    lines.append("══════════════════════════════════════")
    lines.append("🤖 Tự động cập nhật hàng ngày lúc 06:00 giờ VN.")
    lines.append("📡 Nguồn: wttr.in | tide-forecast.com")
    lines.append("")
    lines.append("🌟 CHÚC SẾP MỘT NGÀY LÀM VIỆC TỐT LÀNH! 🎉")

    print("\n".join(lines))


if __name__ == '__main__':
    main()
