#!/usr/bin/env python3
import argparse
import json
import math
from datetime import datetime

# Vietnamese lunar conversion (astronomical algorithm, timezone Asia/Ho_Chi_Minh = UTC+7)
# Source lineage: amlich / Ho Ngoc Duc public algorithm style.

TIMEZONE = 7.0


def _int(d: float) -> int:
    return math.floor(d)


def jd_from_date(dd: int, mm: int, yy: int) -> int:
    a = _int((14 - mm) / 12)
    y = yy + 4800 - a
    m = mm + 12 * a - 3
    jd = dd + _int((153 * m + 2) / 5) + 365 * y + _int(y / 4) - _int(y / 100) + _int(y / 400) - 32045
    if jd < 2299161:
        jd = dd + _int((153 * m + 2) / 5) + 365 * y + _int(y / 4) - 32083
    return jd


def new_moon(k: int) -> float:
    T = k / 1236.85
    T2 = T * T
    T3 = T2 * T
    dr = math.pi / 180.0
    Jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
    Jd1 += 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)

    M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3

    C1 = (0.1734 - 0.000393 * T) * math.sin(M * dr) + 0.0021 * math.sin(2 * dr * M)
    C1 -= 0.4068 * math.sin(Mpr * dr) + 0.0161 * math.sin(2 * dr * Mpr)
    C1 -= 0.0004 * math.sin(3 * dr * Mpr)
    C1 += 0.0104 * math.sin(2 * dr * F) - 0.0051 * math.sin(dr * (M + Mpr))
    C1 -= 0.0074 * math.sin(dr * (M - Mpr)) + 0.0004 * math.sin(dr * (2 * F + M))
    C1 -= 0.0004 * math.sin(dr * (2 * F - M)) - 0.0006 * math.sin(dr * (2 * F + Mpr))
    C1 += 0.0010 * math.sin(dr * (2 * F - Mpr)) + 0.0005 * math.sin(dr * (2 * Mpr + M))

    if T < -11:
        deltat = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
    else:
        deltat = -0.000278 + 0.000265 * T + 0.000262 * T2

    return Jd1 + C1 - deltat


def sun_longitude(jdn: float) -> float:
    T = (jdn - 2451545.0) / 36525
    T2 = T * T
    dr = math.pi / 180
    M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
    L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
    DL = (1.914600 - 0.004817 * T - 0.000014 * T2) * math.sin(dr * M)
    DL += (0.019993 - 0.000101 * T) * math.sin(dr * 2 * M) + 0.000290 * math.sin(dr * 3 * M)
    L = (L0 + DL) * dr
    L = L - math.pi * 2 * _int(L / (math.pi * 2))
    return L


def get_sun_longitude(day_number: int, time_zone: float) -> int:
    return _int(sun_longitude(day_number - 0.5 - time_zone / 24.0) / math.pi * 6)


def get_new_moon_day(k: int, time_zone: float) -> int:
    return _int(new_moon(k) + 0.5 + time_zone / 24.0)


def get_lunar_month11(yy: int, time_zone: float) -> int:
    off = jd_from_date(31, 12, yy) - 2415021
    k = _int(off / 29.530588853)
    nm = get_new_moon_day(k, time_zone)
    sun_long = get_sun_longitude(nm, time_zone)
    if sun_long >= 9:
        nm = get_new_moon_day(k - 1, time_zone)
    return nm


def get_leap_month_offset(a11: int, time_zone: float) -> int:
    k = _int((a11 - 2415021.076998695) / 29.530588853 + 0.5)
    last = 0
    i = 1
    arc = get_sun_longitude(get_new_moon_day(k + i, time_zone), time_zone)
    while arc != last and i < 15:
        last = arc
        i += 1
        arc = get_sun_longitude(get_new_moon_day(k + i, time_zone), time_zone)
    return i - 1


def convert_solar_to_lunar(dd: int, mm: int, yy: int, time_zone: float = TIMEZONE):
    day_number = jd_from_date(dd, mm, yy)
    k = _int((day_number - 2415021.076998695) / 29.530588853)
    month_start = get_new_moon_day(k + 1, time_zone)
    if month_start > day_number:
        month_start = get_new_moon_day(k, time_zone)

    a11 = get_lunar_month11(yy, time_zone)
    b11 = a11
    if a11 >= month_start:
        lunar_year = yy
        a11 = get_lunar_month11(yy - 1, time_zone)
    else:
        lunar_year = yy + 1
        b11 = get_lunar_month11(yy + 1, time_zone)

    lunar_day = day_number - month_start + 1
    diff = _int((month_start - a11) / 29)
    lunar_month = diff + 11
    lunar_leap = 0

    if b11 - a11 > 365:
        leap_month_diff = get_leap_month_offset(a11, time_zone)
        if diff >= leap_month_diff:
            lunar_month = diff + 10
            if diff == leap_month_diff:
                lunar_leap = 1

    if lunar_month > 12:
        lunar_month = lunar_month - 12
    if lunar_month >= 11 and diff < 4:
        lunar_year -= 1

    return int(lunar_day), int(lunar_month), int(lunar_year), int(lunar_leap)


def parse_solar_date(s: str):
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            d = datetime.strptime(s, fmt)
            return d.day, d.month, d.year
        except ValueError:
            continue
    raise ValueError("invalid_date_format")


def main():
    ap = argparse.ArgumentParser(description="Convert Gregorian (solar) date to Vietnamese lunar date")
    ap.add_argument("--solar", required=True, help="Date: YYYY-MM-DD or DD/MM/YYYY")
    ap.add_argument("--json", action="store_true", help="Output JSON only")
    args = ap.parse_args()

    dd, mm, yy = parse_solar_date(args.solar)
    ld, lm, ly, leap = convert_solar_to_lunar(dd, mm, yy, TIMEZONE)

    out = {
        "ok": True,
        "solar": f"{dd:02d}/{mm:02d}/{yy}",
        "lunar": {
            "day": ld,
            "month": lm,
            "year": ly,
            "isLeapMonth": bool(leap),
            "text": f"{ld:02d}/{lm:02d}/{ly}" + (" (nhuận)" if leap else ""),
        },
        "timezone": "Asia/Ho_Chi_Minh",
    }

    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
