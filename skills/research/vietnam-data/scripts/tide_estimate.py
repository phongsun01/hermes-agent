#!/usr/bin/env python3
"""
Tide estimation for Vietnamese coastal locations using lunar phase calculation.

Computes approximate high/low tide times when web scraping is unavailable.
Default: Ha Long Bay (diurnal regime). Edit LOCATIONS dict for other areas.

Usage:
    uv run python3 scripts/tide_estimate.py              # default: Ha Long, 7 days
    uv run python3 scripts/tide_estimate.py --days 14    # 14 days
    uv run python3 scripts/tide_estimate.py --location "Cam Pha"
"""

import math
from datetime import datetime, timedelta
import argparse

# Location database: (lat, lon, tidal_lag_hours, spring_range_m, neap_range_m, msl, regime)
# tidal_lag: hours after moon transit that high tide occurs
# regime: 'diurnal' (1 high + 1 low primary/day) or 'semidiurnal' (2 of each)
LOCATIONS = {
    "Ha Long":      (20.95, 107.08, 3.5, 3.8, 1.5, 1.9, "diurnal"),
    "Hong Gai":     (20.95, 107.08, 3.5, 3.8, 1.5, 1.9, "diurnal"),
    "Cam Pha":      (21.02, 107.30, 3.5, 3.8, 1.5, 1.9, "diurnal"),
    "Haiphong":     (20.85, 106.68, 3.0, 3.5, 1.3, 1.7, "diurnal"),
    "Do Son":       (20.71, 106.80, 3.0, 3.5, 1.3, 1.7, "diurnal"),
    "Da Nang":      (16.07, 108.22, 2.5, 2.0, 0.7, 1.0, "mixed"),
    "Nha Trang":    (12.24, 109.19, 2.5, 2.2, 0.8, 1.0, "mixed"),
    "Vung Tau":     (10.34, 107.08, 2.0, 3.0, 1.0, 1.5, "semidiurnal"),
}

MOON_PHASES = [
    (0.0625, "Trang non 🌑"),
    (0.1875, "Liem dau 🌒"),
    (0.3125, "Ban nguyet dau 🌓"),
    (0.4375, "Khuyet dau 🌔"),
    (0.5625, "Trang tron 🌕"),
    (0.6875, "Khuyet cuoi 🌖"),
    (0.8125, "Ban nguyet cuoi 🌗"),
    (1.0000, "Liem cuoi 🌘"),
]


def julian_day(dt: datetime) -> float:
    """Convert datetime to Julian Day Number."""
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = (dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045)
    return jdn + (dt.hour - 12) / 24.0 + dt.minute / 1440.0


def moon_phase(jd: float) -> float:
    """Return moon phase as fraction of cycle (0=new, 0.5=full, 1=new again)."""
    dt = jd - 2451545.0
    T = dt / 36525.0
    D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T * T
    return (D % 360) / 360.0


def moon_phase_name(phase: float) -> str:
    for threshold, name in MOON_PHASES:
        if phase < threshold:
            return name
    return MOON_PHASES[-1][1]


def tidal_coefficient(phase: float) -> float:
    """0.5 (neap) to 1.0 (spring)."""
    return 0.5 + 0.5 * math.cos(2 * math.pi * (phase - 0.5) + math.pi)


def fmt_hour(h: float) -> str:
    h = h % 24
    return f"{int(h):02d}:{int((h % 1) * 60):02d}"


def estimate_tides(date: datetime, loc_name: str = "Ha Long"):
    """Return dict of estimated tide info for one day at a named location."""
    if loc_name not in LOCATIONS:
        loc_name = "Ha Long"
    lat, lon, lag, spr, neap, msl, regime = LOCATIONS[loc_name]

    jd = julian_day(date)
    phase = moon_phase(jd)
    pname = moon_phase_name(phase)
    coeff = tidal_coefficient(phase)

    # Moon transit time (rough: moon_age * lunar_day_length)
    moon_age = phase * 29.53058867  # days since new moon
    moon_transit_h = (moon_age * 24.84 / 29.53) % 24

    # Tide range
    tide_range = neap + (spr - neap) * coeff
    high_h = msl + tide_range / 2
    low_h = msl - tide_range / 2

    # High tide = moon transit + lag
    h1 = (moon_transit_h + lag) % 24
    l1 = (h1 + 6.21) % 24  # ~6h 12.5m later
    h2 = (h1 + 12.42) % 24
    l2 = (l1 + 12.42) % 24

    return {
        "date": date.strftime("%d/%m/%Y"),
        "dow": date.strftime("%a").upper(),
        "phase": pname,
        "coeff": coeff,
        "range": tide_range,
        "tides": [
            (fmt_hour(h1), round(high_h, 1), "LON"),
            (fmt_hour(l1), round(low_h, 1), "RONG"),
            (fmt_hour(h2), round(high_h, 1), "LON"),
            (fmt_hour(l2), round(low_h, 1), "RONG"),
        ],
        "loc": loc_name,
    }


def print_tide_table(days: int = 7, loc: str = "Ha Long"):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"{'=' * 80}")
    print(f"  LICH THUY TRIEU UOC TINH — {loc.upper()}")
    print(f"  Khu vuc: ({LOCATIONS[loc][0]}°N, {LOCATIONS[loc][1]}°E)")
    print(f"  Sai so ±1-2h. Cho muc dich tham khao.")
    print(f"{'=' * 80}")
    print()
    print(f"Ngay       | Pha trang       | Bien do |  Nuoc lon 1  |  Nuoc rong 1  |  Nuoc lon 2  |  Nuoc rong 2")
    print(f"-" * 90)
    for i in range(days):
        d = today + timedelta(days=i)
        t = estimate_tides(d, loc)
        print(f"{t['date']} {t['dow']} | {t['phase']:16s} | {t['range']:.1f}m   | {t['tides'][0][0]} ({t['tides'][0][1]:.1f}m) | {t['tides'][1][0]} ({t['tides'][1][1]:.1f}m) | {t['tides'][2][0]} ({t['tides'][2][1]:.1f}m) | {t['tides'][3][0]} ({t['tides'][3][1]:.1f}m)")

    print()
    print(f"Che do: {LOCATIONS[loc][6]} — ", end="")
    print("1 lan len/xuong chinh/ngay" if LOCATIONS[loc][6] == "diurnal" else "2 lan len/xuong/ngay")
    print("Nuoc lon thu 2 thuong yeu hon hoac khong ro rang voi che do nhat trieu.")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estimate tides using lunar phase")
    parser.add_argument("--days", type=int, default=7, help="Number of days to forecast")
    parser.add_argument("--location", type=str, default="Ha Long",
                        choices=list(LOCATIONS.keys()),
                        help="Coastal location")
    parser.add_argument("--list", action="store_true", help="List available locations")
    args = parser.parse_args()

    if args.list:
        print("Available locations:")
        for name, (lat, lon, lag, spr, neap, msl, regime) in sorted(LOCATIONS.items()):
            print(f"  {name:15s} ({lat}°N, {lon}°E)  {regime:12s} range {neap}-{spr}m")
        exit(0)

    print_tide_table(days=args.days, loc=args.location)
