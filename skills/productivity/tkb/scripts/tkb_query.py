#!/usr/bin/env python3
"""
TKB (Thời khóa biểu) Query Script
Đọc Google Sheet + local overlay và trả về lịch theo query_type: today, tomorrow, week, month
"""

import csv, sys, json, os
from datetime import datetime, timedelta
from io import StringIO
from urllib.request import urlopen

SHEET_URL = "https://docs.google.com/spreadsheets/d/1skHS3zAkVc1K6V8kAb54s453zTJ5bDNeuXAP4qeTcMM/export?format=csv"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_FILE = os.path.join(SCRIPT_DIR, "tkb_local.json")

VI_DAYS = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
DAY_INDEX = {name: i for i, name in enumerate(VI_DAYS)}


def get_weekday_vn(d):
    return VI_DAYS[d.weekday()]


def today_vn():
    return get_weekday_vn(datetime.now())


def tomorrow_vn():
    return get_weekday_vn(datetime.now() + timedelta(days=1))


def load_local():
    """Đọc local overlay entries."""
    if not os.path.exists(LOCAL_FILE):
        return []
    try:
        with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('local_entries', [])
    except (json.JSONDecodeError, IOError):
        return []


def load_sheet():
    resp = urlopen(SHEET_URL)
    content = resp.read().decode('utf-8')
    reader = csv.DictReader(StringIO(content))
    rows = []
    for row in reader:
        thu = row.get('Thứ / Ngày', '').strip()
        if not thu or thu == 'Thứ / Ngày':
            continue
        day_num = DAY_INDEX.get(thu)
        if day_num is None:
            continue
        rows.append({
            'thu': thu,
            'thu_index': day_num,
            'thoi_gian': row.get('Thời gian', '').strip(),
            'thanh_vien': row.get('Thành viên', '').strip(),
            'hoat_dong': row.get('Hoạt động / Công việc', '').strip(),
            'dia_diem': row.get('Địa điểm', '').strip(),
            'lap_lai': row.get('Lặp lại', '').strip(),
            'ghi_chu': row.get('Ghi chú', '').strip(),
        })
    return rows


def load_all():
    """Gộp sheet + local overlay, local ghi đè nếu trùng."""
    rows = load_sheet()
    local_rows = load_local()
    if local_rows:
        # Local entries được thêm vào cuối (ưu tiên hiển thị)
        rows.extend(local_rows)
    return rows


def filter_today(rows):
    today = today_vn()
    return [r for r in rows if r['thu'] == today]


def filter_tomorrow(rows):
    tomorrow = tomorrow_vn()
    return [r for r in rows if r['thu'] == tomorrow]


def filter_week(rows):
    """Lọc tất cả các ngày trong tuần (Thứ 2 -> CN)"""
    result = {}
    for day_name in VI_DAYS:
        day_rows = [r for r in rows if r['thu'] == day_name]
        if day_rows:
            result[day_name] = sorted(day_rows, key=lambda r: r['thoi_gian'])
    return result


def filter_month(rows):
    """Lọc sự kiện đặc biệt trong tháng, không lặp lại hàng tuần"""
    special = [r for r in rows if r['lap_lai'] not in ('Hàng tuần', 'Hàng tuần,', '') or
               any(c.isdigit() for c in r['thu'])]
    return special


def format_today(rows):
    lines = []
    sorted_rows = sorted(rows, key=lambda r: r['thoi_gian'])
    for r in sorted_rows:
        note = f" — _{r['ghi_chu']}_" if r['ghi_chu'] else ''
        lines.append(f"⏰ {r['thoi_gian']} | **{r['thanh_vien']}** — {r['hoat_dong']} tại {r['dia_diem']}{note}")
    return lines


def format_week(grouped):
    lines = []
    for day_name in VI_DAYS:
        if day_name not in grouped:
            continue
        rows = grouped[day_name]
        lines.append(f"\n📅 **{day_name}:**")
        for r in sorted(rows, key=lambda x: x['thoi_gian']):
            note = f" — _{r['ghi_chu']}_" if r['ghi_chu'] else ''
            lines.append(f"  ⏰ {r['thoi_gian']} | **{r['thanh_vien']}** — {r['hoat_dong']} ({r['dia_diem']}){note}")
    return lines


if __name__ == '__main__':
    query_type = sys.argv[1] if len(sys.argv) > 1 else 'today'

    try:
        rows = load_all()
    except Exception as e:
        print(json.dumps({"error": f"Không thể đọc dữ liệu: {e}"}))
        sys.exit(1)

    if query_type == 'today':
        filtered = filter_today(rows)
        today_name = today_vn()
        output = format_today(filtered)
        print(json.dumps({"day": today_name, "count": len(filtered), "schedule": output}))

    elif query_type == 'tomorrow':
        filtered = filter_tomorrow(rows)
        tomorrow_name = tomorrow_vn()
        output = format_today(filtered)
        print(json.dumps({"day": tomorrow_name, "count": len(filtered), "schedule": output}))

    elif query_type == 'week':
        grouped = filter_week(rows)
        output = format_week(grouped)
        total = sum(len(v) for v in grouped.values())
        print(json.dumps({"count": total, "schedule": output}))

    elif query_type == 'month':
        filtered = filter_month(rows)
        output = [f"📌 {r['thu']} {r['thoi_gian']} | **{r['thanh_vien']}** — {r['hoat_dong']}" for r in filtered]
        print(json.dumps({"count": len(filtered), "schedule": output}))

    else:
        print(json.dumps({"error": f"query_type '{query_type}' không hợp lệ. Chọn: today, tomorrow, week, month"}))
        sys.exit(1)
