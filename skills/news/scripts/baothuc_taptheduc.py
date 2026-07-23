#!/usr/bin/env python3
"""Báo thức cả nhà dậy tập thể dục — chạy hàng ngày lúc 06:30 sáng VN."""
import datetime
import sys
import os
import json
from pathlib import Path

# Thêm đường dẫn để import lunar_convert từ skill news
current_dir = Path(__file__).resolve().parent
for p in [str(current_dir), "/opt/hermes/scripts", "/opt/hermes/scripts/news", "D:/Antigravity/Hermes/scripts/news", "/opt/hermes/scripts/zalo"]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)

try:
    import lunar_convert
    from lunar_convert import convert_solar_to_lunar
    has_lunar = True
except ImportError as e:
    has_lunar = False
    print(f"DEBUG: {e}")

def get_lunar_text(dt):
    if not has_lunar:
        return ""
    try:
        ld, lm, ly, leap = convert_solar_to_lunar(dt.day, dt.month, dt.year, 7.0)
        return f"{ld:02d}/{lm:02d}/{ly}" + (" (nhuận)" if leap else "")
    except Exception:
        return ""

def get_comm_text(dt):
    mmdd = dt.strftime("%m-%d")
    paths = [
        str(current_dir / "commemorative-days-vi.json"),
        "/opt/data/skills/news/scripts/commemorative-days-vi.json",
        "/opt/data/commemorative-days-vi.json",
        "/opt/hermes/scripts/news/commemorative-days-vi.json",
        "/opt/hermes/scripts/commemorative-days-vi.json",
        "D:/Antigravity/Hermes/scripts/news/commemorative-days-vi.json",
        "/opt/hermes/scripts/zalo/commemorative-days-vi.json"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for d in data.get("days", []):
                    if d.get("date") == mmdd:
                        return d.get("name", "").strip()
            except Exception:
                pass
    return ""

import urllib.request

now = datetime.datetime.now()
lunar_str = get_lunar_text(now)
comm_str = get_comm_text(now)

try:
    req = urllib.request.Request("https://wttr.in/QuangNinh?format=%c+%t", headers={'User-Agent': 'curl/7.68.0'})
    weather_str = urllib.request.urlopen(req, timeout=5).read().decode('utf-8').strip()
except Exception:
    weather_str = "Không lấy được thông tin thời tiết."

print(f"""Hãy đóng vai một trợ lý gia đình vui vẻ. Viết một tin nhắn báo thức buổi sáng lúc 6:30.
Yêu cầu:
1. Chào buổi sáng gia đình.
2. Cung cấp thông tin ngày hôm nay:
   - Âm lịch: {lunar_str}
   - Thời tiết: {weather_str}
   - Kỷ niệm (nếu có, không có thì bỏ qua): {comm_str}
3. Nhắc từng người theo các ý chính sau một cách sáng tạo, KHÔNG lặp lại y hệt mỗi ngày:
   - Sếp Phong: Xuống giường, vươn vai, hít thở sáng.
   - Chị Huế tồ: Dậy tập Yoga / đi bộ buổi sáng.
   - Bi béo: Dậy vận động, tập bơi.
   - Bống: Hát một bài khởi động ngày mới.

Chỉ in ra tin nhắn cuối cùng để gửi trực tiếp vào nhóm, dùng emoji phù hợp. Lời văn tự nhiên, thân thiện và năng động.
Không thêm các câu mào đầu như "Dưới đây là tin nhắn...", chỉ trả về nội dung tin nhắn.""")
