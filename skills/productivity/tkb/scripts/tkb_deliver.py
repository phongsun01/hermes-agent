#!/usr/bin/env python3
"""
TKB Delivery Script for Zalo (plain text, no markdown).
Usage:
  python tkb_deliver.py today      -> Lịch hôm nay
  python tkb_deliver.py tomorrow   -> Lịch ngày mai
  python tkb_deliver.py week       -> Lịch cả tuần

Output plain text for Zalo delivery (no markdown formatting).
"""
import json
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QUERY_SCRIPT = os.path.join(SCRIPT_DIR, "tkb_query.py")

# Map query types
QUERY_MAP = {
    "today": "today",
    "tomorrow": "tomorrow",
    "week": "week",
}

# Vietnamese day names
VI_DAYS = ['Thu 2', 'Thu 3', 'Thu 4', 'Thu 5', 'Thu 6', 'Thu 7', 'Chu nhat']


def run_query(query_type):
    """Run tkb_query.py and return parsed JSON."""
    cmd = ["uv", "run", "python", QUERY_SCRIPT, query_type]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"error": f"Script error: {result.stderr.strip()}"}
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}"}
    except subprocess.TimeoutExpired:
        return {"error": "Script timeout"}
    except Exception as e:
        return {"error": str(e)}


def format_today(data, title="Hom nay"):
    """Format TKB today/tomorrow for Zalo (plain text)."""
    day = data.get("day", "")
    schedule = data.get("schedule", [])
    count = data.get("count", 0)

    lines = []
    lines.append(f"[TKB] Lich {title.lower()} - {day}")
    lines.append("=" * 30)

    if count == 0:
        lines.append("Hom nay khong co lich hoc nao. Ca nha nghi nhe! 🏠")
    else:
        for item in schedule:
            # Strip markdown but keep emoji
            # Original format: "⏰ {time} | **{name}** — {activity} tại {location}{note}"
            # Remove ** markers, _ markers
            text = item
            text = text.replace("**", "")
            text = text.replace("_", "")
            lines.append(text)
        lines.append(f"\nTong cong: {count} lich.")

    lines.append("=" * 30)
    lines.append("Chuc ca nha mot ngay vui ve! 🌟")
    return "\n".join(lines)


def format_week(data):
    """Format TKB whole week for Zalo (plain text)."""
    schedule = data.get("schedule", [])
    count = data.get("count", 0)

    lines = []
    lines.append("[TKB] Lich ca tuan")
    lines.append("=" * 30)

    if count == 0:
        lines.append("Tuan nay khong co lich hoc nao.")
    else:
        for item in schedule:
            text = item
            text = text.replace("**", "")
            text = text.replace("_", "")
            lines.append(text)

    lines.append("=" * 30)
    lines.append(f"Tong cong: {count} lich trong tuan.")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in QUERY_MAP:
        print("Usage: tkb_deliver.py <today|tomorrow|week>")
        sys.exit(1)

    query_type = QUERY_MAP[sys.argv[1]]
    data = run_query(query_type)

    if "error" in data:
        print(f"[TKB Error] {data['error']}")
        sys.exit(1)

    if query_type == "today":
        output = format_today(data, "Hom nay")
    elif query_type == "tomorrow":
        output = format_today(data, "Ngay mai")
    else:
        output = format_week(data)

    print(output)


if __name__ == "__main__":
    main()
