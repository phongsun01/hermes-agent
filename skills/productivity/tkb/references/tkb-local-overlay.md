# TKB Local Overlay Pattern

## Khi nào dùng

Khi không có Google OAuth (chưa setup) hoặc user muốn thêm/sửa lịch nhanh mà không cần mở Google Sheet.

## Cách hoạt động

`tkb_query.py` gọi `load_all()` → `load_sheet()` (CSV từ Google) + `load_local()` (JSON file). Local entries được append vào cuối mảng sheet rows — không ghi đè, không xoá.

## File overlay

Đường dẫn: `/opt/data/scripts/tkb/tkb_local.json`

Cấu trúc:
```json
{
  "local_entries": [
    {
      "thu": "Thứ 4",
      "thu_index": 2,
      "thoi_gian": "17:30 - 18:30",
      "thanh_vien": "Bi",
      "hoat_dong": "Học tiếng Anh",
      "dia_diem": "Scots",
      "lap_lai": "Hàng tuần",
      "ghi_chu": "Mang cặp"
    }
  ]
}
```

## `thu_index` mapping

| Ngày | thu_index |
|------|-----------|
| Thứ 2 | 0 |
| Thứ 3 | 1 |
| Thứ 4 | 2 |
| Thứ 5 | 3 |
| Thứ 6 | 4 |
| Thứ 7 | 5 |
| Chủ nhật | 6 |

## Nâng cấp lên Google Sheets API

Khi OAuth được setup:
- `google-workspace` skill có `sheets append` để ghi trực tiếp vào sheet
- Lúc đó local overlay không còn cần thiết
- Nhưng vẫn giữ script đọc từ sheet cho đồng bộ
