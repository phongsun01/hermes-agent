import datetime
import json
import pytest
from tools.tkb_tool import (
    normalize_weekday,
    extract_day_number,
    parse_specific_date,
    match_quarter,
    filter_schedule
)

def test_normalize_weekday():
    assert normalize_weekday("Thứ 2") == 0
    assert normalize_weekday("t2") == 0
    assert normalize_weekday("Monday") == 0
    assert normalize_weekday("Mon") == 0
    
    assert normalize_weekday("Thứ 3") == 1
    assert normalize_weekday("T3") == 1
    
    assert normalize_weekday("Thứ 7") == 5
    assert normalize_weekday("Sat") == 5
    
    assert normalize_weekday("Chủ Nhật") == 6
    assert normalize_weekday("CN") == 6
    assert normalize_weekday("Sunday") == 6
    assert normalize_weekday("sun") == 6
    
    assert normalize_weekday("Không hợp lệ") == -1

def test_extract_day_number():
    assert extract_day_number("Ngày 5") == 5
    assert extract_day_number("5") == 5
    assert extract_day_number("Ngày 31") == 31
    assert extract_day_number("Không có số") == -1
    assert extract_day_number("Ngày 32") == -1  # Chỉ cho phép 1-31

def test_parse_specific_date():
    assert parse_specific_date("2026-07-02") == datetime.date(2026, 7, 2)
    assert parse_specific_date("02-07-2026") == datetime.date(2026, 7, 2)
    assert parse_specific_date("02/07/2026") == datetime.date(2026, 7, 2)
    assert parse_specific_date("không phải ngày") is None

def test_match_quarter():
    # 2026-07-01 là đầu quý 3
    assert match_quarter("Đầu quý", datetime.date(2026, 7, 1)) is True
    assert match_quarter("Đầu quý", datetime.date(2026, 7, 2)) is False
    
    # 2026-06-30 là cuối quý 2
    assert match_quarter("Cuối quý", datetime.date(2026, 6, 30)) is True
    assert match_quarter("Cuối quý", datetime.date(2026, 7, 1)) is False

def test_filter_schedule_today():
    raw_data = [
        {"Thứ / Ngày": "Thứ 5", "Thời gian": "08:00", "Thành viên": "Bi", "Hoạt động / Công việc": "Học bóng rổ", "Lặp lại": "Hàng tuần"},
        {"Thứ / Ngày": "Thứ 2", "Thời gian": "09:00", "Thành viên": "Bống", "Hoạt động / Công việc": "Học nhảy", "Lặp lại": "Hàng tuần"},
        {"Thứ / Ngày": "Ngày 2", "Thời gian": "10:00", "Thành viên": "Bố", "Hoạt động / Công việc": "Nộp tiền điện nước", "Lặp lại": "Hàng tháng"},
        {"Thứ / Ngày": "Đầu quý", "Thời gian": "Cả ngày", "Thành viên": "Cả nhà", "Hoạt động / Công việc": "Bảo dưỡng ô tô", "Lặp lại": "Hàng quý"},
        {"Thứ / Ngày": "2026-07-02", "Thời gian": "19:00", "Thành viên": "Bố", "Hoạt động / Công việc": "Đi ăn tối", "Lặp lại": "Một lần"}
    ]
    
    # 2026-07-02 là thứ Năm (weekday = 3), ngày mùng 2. Đầu quý 3 bắt đầu từ 2026-07-01 nên 07-02 không phải đầu quý.
    now = datetime.datetime(2026, 7, 2, 8, 0, 0)
    
    filtered = filter_schedule(raw_data, "today", now)
    
    # Kết quả kỳ vọng: 
    # 1. Thứ 5 (hàng tuần) -> khớp vì 07-02 là thứ Năm
    # 2. Ngày 2 (hàng tháng) -> khớp vì 07-02 là ngày 2
    # 3. 2026-07-02 (một lần) -> khớp vì trùng ngày
    assert len(filtered) == 3
    names = [r["Hoạt động / Công việc"] for r in filtered]
    assert "Học bóng rổ" in names
    assert "Nộp tiền điện nước" in names
    assert "Đi ăn tối" in names
    assert "Học nhảy" not in names
    assert "Bảo dưỡng ô tô" not in names

def test_filter_schedule_week():
    raw_data = [
        {"Thứ / Ngày": "Thứ 2", "Thời gian": "08:00", "Thành viên": "Bi", "Hoạt động / Công việc": "Học nhảy", "Lặp lại": "Hàng tuần"},
        {"Thứ / Ngày": "Thứ 5", "Thời gian": "09:00", "Thành viên": "Bi", "Hoạt động / Công việc": "Học vẽ", "Lặp lại": "Hàng tuần"}
    ]
    # 2026-07-02 (thứ Năm). Tuần này bắt đầu từ thứ Hai (2026-06-29) đến Chủ Nhật (2026-07-05)
    now = datetime.datetime(2026, 7, 2, 8, 0, 0)
    filtered = filter_schedule(raw_data, "week", now)
    
    assert len(filtered) == 2
    assert filtered[0]["_weekday_name"] == "Thứ 2"
    assert filtered[1]["_weekday_name"] == "Thứ 5"

def test_filter_schedule_month():
    raw_data = [
        {"Thứ / Ngày": "Thứ 5", "Thời gian": "08:00", "Thành viên": "Bi", "Hoạt động / Công việc": "Lịch tuần nhảy", "Lặp lại": "Hàng tuần"},
        {"Thứ / Ngày": "Ngày 5", "Thời gian": "09:00", "Thành viên": "Mẹ", "Hoạt động / Công việc": "Thanh toán cước", "Lặp lại": "Hàng tháng"},
        {"Thứ / Ngày": "2026-07-15", "Thời gian": "10:00", "Thành viên": "Bi", "Hoạt động / Công việc": "Sinh nhật bạn", "Lặp lại": "Một lần"},
        {"Thứ / Ngày": "2026-08-20", "Thời gian": "10:00", "Thành viên": "Bi", "Hoạt động / Công việc": "Sự kiện tháng sau", "Lặp lại": "Một lần"}
    ]
    # Month = 7 / 2026
    now = datetime.datetime(2026, 7, 2, 8, 0, 0)
    filtered = filter_schedule(raw_data, "month", now)
    
    # Kết quả kỳ vọng: 
    # - Loại bỏ "Lịch tuần nhảy" (hàng tuần)
    # - Giữ "Thanh toán cước" (hàng tháng)
    # - Giữ "Sinh nhật bạn" (2026-07-15)
    # - Loại bỏ "Sự kiện tháng sau" (2026-08-20)
    assert len(filtered) == 2
    jobs = [r["Hoạt động / Công việc"] for r in filtered]
    assert "Thanh toán cước" in jobs
    assert "Sinh nhật bạn" in jobs
    assert "Lịch tuần nhảy" not in jobs
