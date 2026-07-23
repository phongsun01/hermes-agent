import json
import os
import re
import csv
import datetime
import urllib.request
import urllib.error
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# --- Timezone Resolution ---
def get_tz_context(tz_name: str) -> datetime.tzinfo:
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        if tz_name == "Asia/Ho_Chi_Minh":
            return datetime.timezone(datetime.timedelta(hours=7))
        return datetime.timezone.utc

# --- Weekday & Date Parsing Helpers ---
def normalize_weekday(s: str) -> int:
    s = s.strip().lower()
    # Normalize common Vietnamese names
    s = s.replace("hai", "2").replace("ba", "3").replace("tư", "4").replace("năm", "5").replace("sáu", "6").replace("bảy", "7").replace("bẩy", "7")
    
    # Monday
    if "t2" in s or "thứ 2" in s or "thu 2" in s or "monday" in s or "mon" in s:
        return 0
    # Tuesday
    if "t3" in s or "thứ 3" in s or "thu 3" in s or "tuesday" in s or "tue" in s:
        return 1
    # Wednesday
    if "t4" in s or "thứ 4" in s or "thu 4" in s or "wednesday" in s or "wed" in s:
        return 2
    # Thursday
    if "t5" in s or "thứ 5" in s or "thu 5" in s or "thursday" in s or "thu" in s:
        return 3
    # Friday
    if "t6" in s or "thứ 6" in s or "thu 6" in s or "friday" in s or "fri" in s:
        return 4
    # Saturday
    if "t7" in s or "thứ 7" in s or "thu 7" in s or "saturday" in s or "sat" in s:
        return 5
    # Sunday
    if "cn" in s or "chủ nhật" in s or "chu nhat" in s or "sunday" in s or "sun" in s:
        return 6
    return -1

def extract_day_number(s: str) -> int:
    m = re.search(r'\d+', s)
    if m:
        val = int(m.group(0))
        if 1 <= val <= 31:
            return val
    return -1

def parse_specific_date(s: str) -> Optional[datetime.date]:
    s = s.strip()
    # Try different common date formats
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def is_quarter_start(d: datetime.date) -> bool:
    # Quarter starts: Jan 1, Apr 1, Jul 1, Oct 1
    return d.month in (1, 4, 7, 10) and d.day == 1

def is_quarter_end(d: datetime.date) -> bool:
    # Quarter ends: Mar 31, Jun 30, Sep 30, Dec 31
    import calendar
    _, last_day = calendar.monthrange(d.year, d.month)
    return d.month in (3, 6, 9, 12) and d.day == last_day

def match_quarter(s: str, d: datetime.date) -> bool:
    s = s.strip().lower()
    if "đầu" in s or "dau" in s or "start" in s:
        return is_quarter_start(d)
    if "cuối" in s or "cuoi" in s or "end" in s:
        return is_quarter_end(d)
    day_num = extract_day_number(s)
    if day_num != -1:
        return d.month in (1, 4, 7, 10) and d.day == day_num
    return False

# --- Fetching & Normalizing Schedule Data ---
def fetch_google_sheet_csv(url: str) -> str:
    # Convert standard sharing link to export CSV if necessary
    if "docs.google.com/spreadsheets" in url and "/export" not in url:
        # Match spreadsheet ID
        m = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if m:
            sheet_id = m.group(1)
            # Find gid if specified
            gid_m = re.search(r'[#&]gid=([0-9]+)', url)
            gid = f"&gid={gid_m.group(1)}" if gid_m else ""
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid}"

    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Lỗi kết nối Google Sheets (HTTP {e.code}: {e.reason}). "
            "Vui lòng kiểm tra xem bạn đã chia sẻ Sheet ở chế độ 'Bất kỳ ai có liên kết đều có thể xem' (Anyone with link can view) chưa."
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Không thể kết nối đến Google Sheets ({e.reason}). "
            "Vui lòng kiểm tra lại liên kết bảng tính hoặc kết nối mạng của bạn."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Lỗi không xác định khi tải dữ liệu từ Google Sheets: {e}") from e

def fetch_notion_database(database_id: str, token: str) -> List[Dict[str, str]]:
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Lỗi kết nối Notion API (HTTP {e.code}). Vui lòng kiểm tra Notion Token "
            "và Database ID, đồng thời đảm bảo đã share Database với Notion Integration của bạn."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Lỗi không xác định khi gọi Notion API: {e}") from e

    results = []
    for page in res_data.get("results", []):
        props = page.get("properties", {})
        row = {}
        for prop_name, prop_val in props.items():
            # Extract plain text from various Notion property types
            ptype = prop_val.get("type")
            text_val = ""
            if ptype == "title":
                text_val = "".join([t.get("plain_text", "") for t in prop_val.get("title", [])])
            elif ptype == "rich_text":
                text_val = "".join([t.get("plain_text", "") for t in prop_val.get("rich_text", [])])
            elif ptype == "select":
                sel = prop_val.get("select")
                text_val = sel.get("name", "") if sel else ""
            elif ptype == "multi_select":
                text_val = ", ".join([s.get("name", "") for s in prop_val.get("multi_select", [])])
            elif ptype == "date":
                dval = prop_val.get("date")
                text_val = dval.get("start", "") if dval else ""
            else:
                # Fallback simple string representation
                text_val = str(prop_val)
            row[prop_name] = text_val
        results.append(row)
    return results

def get_config_value() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        return load_config().get("tkb", {})
    except Exception:
        return {}

def load_schedule_data() -> List[Dict[str, str]]:
    cfg = get_config_value()
    google_url = cfg.get("google_sheet_url")
    notion_id = cfg.get("notion_database_id")
    notion_token = cfg.get("notion_token")

    if not google_url and not notion_id:
        # Fallback to local check
        local_path = os.path.expanduser("~/.hermes/tkb.csv")
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return [dict(row) for row in reader]
        raise ValueError(
            "Chưa cấu hình nguồn dữ liệu Thời khóa biểu. Vui lòng thêm google_sheet_url "
            "hoặc notion_database_id vào config.yaml dưới mục 'tkb'."
        )

    # 1. Fetch from Google Sheets
    if google_url:
        csv_data = fetch_google_sheet_csv(google_url)
        reader = csv.DictReader(csv_data.strip().splitlines())
        return [dict(row) for row in reader]

    # 2. Fetch from Notion
    if notion_id and notion_token:
        notion_rows = fetch_notion_database(notion_id, notion_token)
        # Normalize column names to match the standard schema
        normalized = []
        for r in notion_rows:
            norm_r = {}
            for k, v in r.items():
                k_clean = k.strip().lower()
                if "thứ" in k_clean or "ngày" in k_clean or "date" in k_clean:
                    norm_r["Thứ / Ngày"] = v
                elif "thời gian" in k_clean or "time" in k_clean:
                    norm_r["Thời gian"] = v
                elif "thành viên" in k_clean or "member" in k_clean:
                    norm_r["Thành viên"] = v
                elif "hoạt động" in k_clean or "công việc" in k_clean or "activity" in k_clean or "task" in k_clean:
                    norm_r["Hoạt động / Công việc"] = v
                elif "địa điểm" in k_clean or "location" in k_clean:
                    norm_r["Địa điểm"] = v
                elif "lặp" in k_clean or "repeat" in k_clean or "frequency" in k_clean:
                    norm_r["Lặp lại"] = v
                elif "ghi chú" in k_clean or "note" in k_clean:
                    norm_r["Ghi chú"] = v
                else:
                    norm_r[k] = v
            normalized.append(norm_r)
        return normalized

    raise ValueError("Thiếu cấu hình notion_token cho Notion Database.")

def filter_schedule(raw_data: List[Dict[str, str]], query_type: str, now: datetime.datetime) -> List[Dict[str, str]]:
    today_date = now.date()
    today_weekday = now.weekday()  # 0=Monday, ..., 6=Sunday

    filtered = []
    
    # Pre-parse and normalize columns for all rows
    normalized_rows = []
    for r in raw_data:
        # Standardize keys in case of minor whitespace differences
        standardized = {}
        for k, v in r.items():
            k_clean = k.strip()
            if "Thứ / Ngày" in k_clean:
                standardized["Thứ / Ngày"] = v
            elif "Thời gian" in k_clean:
                standardized["Thời gian"] = v
            elif "Thành viên" in k_clean:
                standardized["Thành viên"] = v
            elif "Hoạt động / Công việc" in k_clean:
                standardized["Hoạt động / Công việc"] = v
            elif "Địa điểm" in k_clean:
                standardized["Địa điểm"] = v
            elif "Lặp lại" in k_clean:
                standardized["Lặp lại"] = v
            elif "Ghi chú" in k_clean:
                standardized["Ghi chú"] = v
            else:
                standardized[k_clean] = v
        normalized_rows.append(standardized)

    if query_type == "today":
        for r in normalized_rows:
            day_field = str(r.get("Thứ / Ngày", "")).strip()
            repeat = str(r.get("Lặp lại", "")).strip().lower()
            
            # Default empty repeat to "Một lần" or "Hàng tuần" based on context
            if not repeat:
                spec_date = parse_specific_date(day_field)
                repeat = "một lần" if spec_date else "hàng tuần"

            # 1. Weekly repeat
            if repeat in ("hàng tuần", "hang tuan", "weekly"):
                if normalize_weekday(day_field) == today_weekday:
                    filtered.append(r)
            # 2. Monthly repeat
            elif repeat in ("hàng tháng", "hang thang", "monthly"):
                if extract_day_number(day_field) == today_date.day:
                    filtered.append(r)
            # 3. Quarterly repeat
            elif repeat in ("hàng quý", "hang quy", "quarterly"):
                if match_quarter(day_field, today_date):
                    filtered.append(r)
            # 4. One-time event
            elif repeat in ("một lần", "mot lan", "once", "one-time"):
                spec_date = parse_specific_date(day_field)
                if spec_date == today_date:
                    filtered.append(r)

    elif query_type == "tomorrow":
        tomorrow_date = today_date + datetime.timedelta(days=1)
        tomorrow_weekday = tomorrow_date.weekday()
        for r in normalized_rows:
            day_field = str(r.get("Thứ / Ngày", "")).strip()
            repeat = str(r.get("Lặp lại", "")).strip().lower()
            
            if not repeat:
                spec_date = parse_specific_date(day_field)
                repeat = "một lần" if spec_date else "hàng tuần"

            # 1. Weekly repeat
            if repeat in ("hàng tuần", "hang tuan", "weekly"):
                if normalize_weekday(day_field) == tomorrow_weekday:
                    filtered.append(r)
            # 2. Monthly repeat
            elif repeat in ("hàng tháng", "hang thang", "monthly"):
                if extract_day_number(day_field) == tomorrow_date.day:
                    filtered.append(r)
            # 3. Quarterly repeat
            elif repeat in ("hàng quý", "hang quy", "quarterly"):
                if match_quarter(day_field, tomorrow_date):
                    filtered.append(r)
            # 4. One-time event
            elif repeat in ("một lần", "mot lan", "once", "one-time"):
                spec_date = parse_specific_date(day_field)
                if spec_date == tomorrow_date:
                    filtered.append(r)

    elif query_type == "week":
        # Get start of week (Monday)
        start_of_week = today_date - datetime.timedelta(days=today_weekday)
        week_dates = [start_of_week + datetime.timedelta(days=i) for i in range(7)]
        
        # We want to return events for each of the 7 days of the week
        for i, dt in enumerate(week_dates):
            day_events = []
            for r in normalized_rows:
                day_field = str(r.get("Thứ / Ngày", "")).strip()
                repeat = str(r.get("Lặp lại", "")).strip().lower()
                
                if not repeat:
                    spec_date = parse_specific_date(day_field)
                    repeat = "một lần" if spec_date else "hàng tuần"

                if repeat in ("hàng tuần", "hang tuan", "weekly"):
                    if normalize_weekday(day_field) == i:
                        day_events.append(r)
                elif repeat in ("hàng tháng", "hang thang", "monthly"):
                    if extract_day_number(day_field) == dt.day:
                        day_events.append(r)
                elif repeat in ("hàng quý", "hang quy", "quarterly"):
                    if match_quarter(day_field, dt):
                        day_events.append(r)
                elif repeat in ("một lần", "mot lan", "once", "one-time"):
                    spec_date = parse_specific_date(day_field)
                    if spec_date == dt:
                        day_events.append(r)
            
            for de in day_events:
                # Add day name info for the LLM to easily group
                event_copy = de.copy()
                event_copy["_date_str"] = dt.strftime("%Y-%m-%d")
                event_copy["_weekday_name"] = f"Thứ {i+2}" if i < 5 else ("Thứ 7" if i == 5 else "Chủ Nhật")
                filtered.append(event_copy)

    elif query_type == "month":
        # Show monthly, quarterly (if falling in this month), and one-time events in this calendar month.
        # EXCLUDE weekly events.
        for r in normalized_rows:
            day_field = str(r.get("Thứ / Ngày", "")).strip()
            repeat = str(r.get("Lặp lại", "")).strip().lower()
            
            if not repeat:
                spec_date = parse_specific_date(day_field)
                repeat = "một lần" if spec_date else "hàng tuần"

            # Skip weekly events
            if repeat in ("hàng tuần", "hang tuan", "weekly"):
                continue

            # Monthly events are always included
            if repeat in ("hàng tháng", "hang thang", "monthly"):
                filtered.append(r)
            # Quarterly events if it matches this month
            elif repeat in ("hàng quý", "hang quy", "quarterly"):
                # Check if quarter milestone falls in this month.
                milestone_match = False
                for day in range(1, 32):
                    try:
                        test_date = datetime.date(today_date.year, today_date.month, day)
                        if match_quarter(day_field, test_date):
                            milestone_match = True
                            break
                    except ValueError:
                        continue
                if milestone_match:
                    filtered.append(r)
            # One-time events falling in the current month
            elif repeat in ("một lần", "mot lan", "once", "one-time"):
                spec_date = parse_specific_date(day_field)
                if spec_date and spec_date.year == today_date.year and spec_date.month == today_date.month:
                    filtered.append(r)

    return filtered

# --- Tool Handler ---
def get_tkb_tool(query_type: str = "today") -> str:
    query_type = str(query_type).strip().lower()
    if query_type not in ("today", "tomorrow", "week", "month"):
        query_type = "today"
        
    try:
        cfg = get_config_value()
        tz_name = cfg.get("timezone", "Asia/Ho_Chi_Minh")
        tz = get_tz_context(tz_name)
        now = datetime.datetime.now(tz)

        raw_data = load_schedule_data()
        filtered = filter_schedule(raw_data, query_type, now)
        
        return json.dumps({
            "success": True,
            "query_type": query_type,
            "timezone": tz_name,
            "current_time": now.isoformat(),
            "results": filtered
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Lỗi khi chạy get_tkb_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)

# --- Dynamic Cron Job Registration ---
def auto_register_tkb_cron():
    """Reads configuration from config.yaml and registers/updates TKB cron jobs in jobs.json."""
    try:
        cfg = get_config_value()
        cron_cfg = cfg.get("cron", {})
        if not cron_cfg or not cron_cfg.get("enabled", True):
            return

        daily_morning_time = cron_cfg.get("daily_morning_report", "06:00")
        daily_evening_time = cron_cfg.get("daily_evening_report", "21:00")
        weekly_time = cron_cfg.get("weekly_report", "Mon 07:00")
        deliver = cron_cfg.get("deliver", "zalo")

        # Parse times to cron expression
        def time_to_cron(t_str, default_cron):
            dm_match = re.match(r"^(\d{1,2}):(\d{2})$", t_str.strip())
            if dm_match:
                return f"{int(dm_match.group(2))} {int(dm_match.group(1))} * * *"
            return default_cron

        morning_cron = time_to_cron(daily_morning_time, "0 6 * * *")
        evening_cron = time_to_cron(daily_evening_time, "0 21 * * *")

        # weekly_time format e.g. "Mon 07:00" or "T2 07:00" -> "0 7 * * 1"
        weekly_cron = "0 7 * * 1"
        wm_match = re.match(r"^(\w+)\s+(\d{1,2}):(\d{2})$", weekly_time.strip())
        if wm_match:
            day_str = wm_match.group(1).lower()
            hour = int(wm_match.group(2))
            minute = int(wm_match.group(3))
            
            day_map = {
                "mon": "1", "t2": "1", "thu 2": "1", "hai": "1",
                "tue": "2", "t3": "2", "thu 3": "2", "ba": "2",
                "wed": "3", "t4": "3", "thu 4": "3", "tu": "3",
                "thu": "4", "t5": "4", "thu 5": "4", "nam": "4",
                "fri": "5", "t6": "5", "thu 6": "5", "sau": "5",
                "sat": "6", "t7": "6", "thu 7": "6", "bay": "6",
                "sun": "0", "cn": "0", "chu nhat": "0", "nhat": "0"
            }
            day_num = day_map.get(day_str, "1")
            weekly_cron = f"{minute} {hour} * * {day_num}"

        from cron.jobs import load_jobs, save_jobs, compute_next_run, parse_schedule
        jobs = load_jobs()
        
        updated = False
        
        # Clean up old single daily report if exists
        jobs_cleaned = []
        for job in jobs:
            if job.get("id") == "tkb_daily_report":
                updated = True
                continue
            jobs_cleaned.append(job)
        jobs = jobs_cleaned
        
        morning_job_def = {
            "id": "tkb_daily_morning",
            "name": "Báo cáo TKB sáng (Hôm nay)",
            "prompt": "/tkb today",
            "skills": ["tkb"],
            "skill": "tkb",
            "schedule": parse_schedule(morning_cron),
            "schedule_display": f"TKB Hôm nay lúc {daily_morning_time}",
            "deliver": deliver,
            "enabled": True,
            "state": "scheduled"
        }

        evening_job_def = {
            "id": "tkb_daily_evening",
            "name": "Báo cáo TKB tối (Ngày mai)",
            "prompt": "/tkb tomorrow",
            "skills": ["tkb"],
            "skill": "tkb",
            "schedule": parse_schedule(evening_cron),
            "schedule_display": f"TKB Ngày mai lúc {daily_evening_time}",
            "deliver": deliver,
            "enabled": True,
            "state": "scheduled"
        }
        
        weekly_job_def = {
            "id": "tkb_weekly_report",
            "name": "Báo cáo Thời khóa biểu hàng tuần",
            "prompt": "/tkb week",
            "skills": ["tkb"],
            "skill": "tkb",
            "schedule": parse_schedule(weekly_cron),
            "schedule_display": f"TKB hàng tuần lúc {weekly_time}",
            "deliver": deliver,
            "enabled": True,
            "state": "scheduled"
        }

        for jdef in (morning_job_def, evening_job_def, weekly_job_def):
            exists = False
            for job in jobs:
                if job.get("id") == jdef["id"]:
                    job["prompt"] = jdef["prompt"]
                    job["schedule"] = jdef["schedule"]
                    job["schedule_display"] = jdef["schedule_display"]
                    job["deliver"] = jdef["deliver"]
                    job["next_run_at"] = compute_next_run(jdef["schedule"])
                    exists = True
                    updated = True
                    break
            if not exists:
                jdef["next_run_at"] = compute_next_run(jdef["schedule"])
                jobs.append(jdef)
                updated = True

        if updated:
            save_jobs(jobs)
            logger.info("Đã tự động cập nhật lịch cron TKB trong database.")
    except Exception as e:
        logger.warning(f"Không thể tự động đăng ký cron TKB: {e}")

# --- Register Tool with Registry ---
from tools.registry import registry

TKB_SCHEMA = {
    "name": "get_tkb",
    "description": (
        "Truy vấn thời khóa biểu gia đình. Có thể lọc theo ngày hôm nay ('today'), "
        "ngày mai ('tomorrow'), cả tuần hiện tại ('week'), hoặc cả tháng hiện tại ('month')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": ["today", "tomorrow", "week", "month"],
                "description": "Loại truy vấn: 'today' (mặc định), 'tomorrow' (ngày mai), 'week' (cả tuần), hoặc 'month' (cả tháng).",
                "default": "today"
            }
        },
        "required": []
    }
}

registry.register(
    name="get_tkb",
    toolset="tkb",
    schema=TKB_SCHEMA,
    handler=lambda args, **kw: get_tkb_tool(
        query_type=args.get("query_type", "today")
    ),
    check_fn=lambda: True,
    emoji="📅"
)
