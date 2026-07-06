#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# Add current scripts directory to path to allow importing lunar_convert
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from lunar_convert import convert_solar_to_lunar
except ImportError:
    # If not in path, try importing from parent or fallback to sys.argv location
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from lunar_convert import convert_solar_to_lunar

TZ_VN = timezone(timedelta(hours=7))

VN_FEEDS = [
    "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "https://tuoitre.vn/rss/tin-moi-nhat.rss",
    "https://thanhnien.vn/rss/home.rss",
    "https://vietnamnet.vn/rss/trang-chu.rss",
    "https://laodong.vn/rss/home.rss",
]

VN_FALLBACK_FEEDS = [
    "https://news.google.com/rss/search?q=Vi%E1%BB%87t+Nam+tin+m%E1%BB%9Bi+nh%E1%BA%A5t&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=kinh+t%E1%BA%BF+Vi%E1%BB%87t+Nam&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=y+t%E1%BA%BF+Vi%E1%BB%87t+Nam&hl=vi&gl=VN&ceid=VN:vi",
]

def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_date(s: str):
    if not s:
        return None
    s = s.strip()
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z"]:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None

def parse_items(raw: bytes):
    root = ET.fromstring(raw)
    items = []

    channel = root.find("channel")
    if channel is not None:
        for it in channel.findall("item"):
            title = clean_text((it.findtext("title") or "").strip())
            link = (it.findtext("link") or "").strip()
            pub = (it.findtext("pubDate") or it.findtext("published") or "").strip()
            desc = clean_text((it.findtext("description") or "").strip())
            items.append({"title": title, "link": link, "pub": pub, "summary": desc})
    else:
        ns = "{http://www.w3.org/2005/Atom}"
        for it in root.findall(f"{ns}entry"):
            title = clean_text((it.findtext(f"{ns}title") or "").strip())
            lk = it.find(f"{ns}link")
            link = (lk.attrib.get("href", "") if lk is not None else "").strip()
            pub = (it.findtext(f"{ns}updated") or it.findtext(f"{ns}published") or "").strip()
            desc = clean_text((it.findtext(f"{ns}summary") or it.findtext(f"{ns}content") or "").strip())
            items.append({"title": title, "link": link, "pub": pub, "summary": desc})

    return items

def short_summary(text: str, n: int = 150) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].strip()
    return (cut or text[:n]).strip() + "..."

def pick_recent(feed_url: str, hours: int = 24, top: int = 3):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = []
    try:
        raw = fetch(feed_url)
        for it in parse_items(raw):
            title = (it.get("title") or "").strip()
            link = (it.get("link") or "").strip()
            dt = parse_date(it.get("pub", ""))
            if not title or not link or not dt:
                continue
            if dt.astimezone(timezone.utc) < cutoff:
                continue
            items.append({
                "title": title,
                "link": link,
                "summary": it.get("summary", ""),
                "publishedAt": dt.astimezone(timezone.utc).isoformat(),
            })
    except Exception:
        return []

    dedup = {}
    for it in items:
        key = (it["link"].strip().lower(), it["title"].strip().lower())
        if key not in dedup or it["publishedAt"] > dedup[key]["publishedAt"]:
            dedup[key] = it
    return sorted(dedup.values(), key=lambda x: x["publishedAt"], reverse=True)[:top]

def pick_recent_multi(feed_urls, hours: int = 24, top: int = 3):
    all_items = []
    for u in feed_urls:
        all_items.extend(pick_recent(u, hours=hours, top=top))
    dedup = {}
    for it in all_items:
        key = (it.get("link", "").strip().lower(), it.get("title", "").strip().lower())
        if key not in dedup or it.get("publishedAt", "") > dedup[key].get("publishedAt", ""):
            dedup[key] = it
    return sorted(dedup.values(), key=lambda x: x.get("publishedAt", ""), reverse=True)[:top]

def get_lunar_today_text():
    try:
        now_vn = datetime.now(TZ_VN)
        ld, lm, ly, leap = convert_solar_to_lunar(now_vn.day, now_vn.month, now_vn.year, 7.0)
        return f"{ld:02d}/{lm:02d}/{ly}" + (" (nhuận)" if leap else "")
    except Exception as e:
        return f"Không lấy được dữ liệu âm lịch ({e})."

def get_commemorative_today():
    mmdd = datetime.now(TZ_VN).strftime("%m-%d")
    # Resolve from active profile's data folder or current directory
    paths_to_check = [
        Path("C:/Users/Desktop/AppData/Local/hermes/data/commemorative-days-vi.json"),
        Path(__file__).resolve().parent / "commemorative-days-vi.json",
        Path(__file__).resolve().parent / "zalo" / "commemorative-days-vi.json",
    ]
    for p in paths_to_check:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for d in data.get("days", []):
                    if (d.get("date") or "") == mmdd:
                        return (d.get("name") or "").strip()
            except Exception:
                continue
    return ""

def source_domain(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return "không rõ nguồn"
    try:
        host = urllib.parse.urlparse(u).netloc.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host or "không rõ nguồn"
    except Exception:
        return "không rõ nguồn"

def get_daily_quiz():
    quiz_bank = [
        {
            "q": "Con gì càng to càng nhỏ?",
            "a": "Con cua (càng to thì con cua càng nhỏ).",
        },
        {
            "q": "Cái gì của bạn nhưng người khác dùng nhiều hơn bạn?",
            "a": "Tên của bạn.",
        },
        {
            "q": "Càng lấy đi thì càng lớn, là gì?",
            "a": "Cái hố.",
        },
        {
            "q": "Có cổ mà không có đầu, là gì?",
            "a": "Cái áo.",
        },
        {
            "q": "Tháng nào có 28 ngày?",
            "a": "Tất cả các tháng.",
        },
    ]
    day_idx = datetime.now(TZ_VN).timetuple().tm_yday
    item = quiz_bank[day_idx % len(quiz_bank)]
    return item["q"], item["a"]

def build_message(vn_news):
    now_dt = datetime.now(TZ_VN)
    now_vn = now_dt.strftime("%d/%m %H:%M")
    lunar = get_lunar_today_text()
    comm = get_commemorative_today()

    lines = [
        f"🌅 Bản tin sáng Zalo — {now_vn}",
        "",
        f"🗓️ Âm lịch hôm nay: {lunar}",
    ]

    if comm:
        lines += [f"🎉 Ngày kỷ niệm: {comm}"]

    # Daily Quiz
    quiz_q, quiz_a = get_daily_quiz()
    lines += [
        "",
        "🧩 Đố vui hôm nay:",
        f"❓ {quiz_q}",
        "(Trả lời em trong chat để em bật đáp án 😄)",
    ]

    lines += ["", "📰 Tin trong nước (24h):"]
    if vn_news:
        for i, n in enumerate(vn_news[:3], 1):
            summary = short_summary(n.get('summary', '') or n.get('title', ''))
            lines += [
                f"{i}) {n.get('title', '')}",
                f"   {summary}",
                f"   🔗 Nguồn: {source_domain(n.get('link',''))}",
            ]
    else:
        lines.append("• Đang cập nhật dữ liệu tin trong nước từ nguồn dự phòng.")

    return "\n".join(lines).strip() + "\n"

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()

    vn_all = pick_recent_multi(VN_FEEDS, hours=args.hours, top=args.top)
    if not vn_all:
        vn_all = pick_recent_multi(VN_FALLBACK_FEEDS, hours=args.hours, top=args.top)

    message = build_message(vn_all)
    
    # Print output directly so scheduler can deliver it
    print(message)

if __name__ == "__main__":
    main()
