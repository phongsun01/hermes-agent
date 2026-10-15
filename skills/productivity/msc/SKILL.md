---
name: msc
description: "Vietnamese public procurement (Mua Sắm Công): search, tender announcements, procurement plans via MSC API"
version: 1.0.0
author: OpenClaw Migration
license: MIT
platforms: [linux, macos]
prerequisites:
  env_vars: [MSC_SESSION_TOKEN]
  commands: [python3, curl]
metadata:
  hermes:
    tags: [MSC, Procurement, Vietnam, Government, API]
    homepage: https://muasamcong.mpi.gov.vn
---

# MSC — Vietnamese Public Procurement

Mục tiêu: Chuẩn hóa một skill umbrella cho MSC: parse slash command, gọi msc_mvp_router.py, trả kết quả ngắn gọn/đúng dữ liệu và fail-fast khi lỗi login hoặc input không hợp lệ.

## Khi nào dùng
- chạy lệnh /mscmenu (inline buttons điều hướng, MSC-only)
- chạy lệnh msc <tab> <từ khóa>
- chạy batch msc <tab> "hàng hóa 1", "hàng hóa 2"; "hàng hóa 3" (split bằng `,` hoặc `;`, mỗi keyword trả top 20 bằng code)
- chạy lệnh msc tbmt <n> <đơn vị|id> hoặc msc tbmt IB...
- chạy lệnh msc kh <n> <đơn vị|id> hoặc msc kh PL...
- chạy lệnh msc fl <đơn vị|số xác nhận|id> (watchlist)
- chạy lệnh msc exp <PL...|IB...> [PL...|IB...] (batch export)
- với batch có mã lỗi: thêm `--skip-invalid` để bỏ qua mã sai và tiếp tục chạy mã hợp lệ
- kiểm tra msc status để biết token/login còn hạn

**Command format:** Skill prefix pattern - tất cả lệnh bắt đầu bằng `msc <action>`

## Cách chạy

```bash
# When in skill directory (skills/productivity/msc/)
python3 lib/msc_mvp_router.py "/mscmenu"

# From hermes-agent root
python3 skills/productivity/msc/lib/msc_mvp_router.py "msc tbmt 5 bệnh viện"
```

Or from skill context:
```
Execute: cd skills/productivity/msc && python3 lib/msc_mvp_router.py "msc kh 3 bệnh viện"
```

## Đầu ra
Kết quả JSON từ router + phần trả lời ngắn cho người dùng: ưu tiên kết luận trước, kèm lỗi chuẩn (lỗi login, sai số IB/PL, tab không hợp lệ) khi có.

## Menu Rendering Contract

**Nguồn đúng cho menu:**
- Menu payload: `lib/inline_menu_payload.py` → `_build_inline_menu_payload(level)`
- Router: `lib/msc_mvp_router.py` (imports payload generator)

**Contract renderer (bắt buộc):**
1. Router trả `result.buttons` → renderer phải giữ nguyên cấu trúc nút
2. Telegram inline keyboard format: mảng 2 chiều `[[{text, callback_data}]]`
3. Cấm: flatten callback token ra text, tự sáng tác menu, hiện token `v1|...` cho user

## Watchlist Commands

- `msc fl list` — danh sách 30 đơn vị theo dõi
- `msc fl add <id> [name]` — thêm đơn vị
- `msc fl remove <id>` — xóa đơn vị
- `msc fl latest [n]` — TBMT mới nhất từ watchlist
- `msc fl export` — export danh sách

**Watchlist cron:** Daily 18:00 publish to Telegram (30 units: Quảng Ninh + Hà Nội hospitals)

## Export Path

Export files → `skills/productivity/msc/reports/msc/{tbmt|khlcnt}/YYYY/MM/`

Example: `reports/msc/tbmt/2026/05/IB2500281578__2026-05-17_11-12-58__52352559.md`

## Tools cho phép
exec, read

## Nguồn tham chiếu
- https://muasamcong.mpi.gov.vn

## Quy tắc an toàn
- Chỉ thao tác trong scope được phép.
- Nếu thiếu dữ liệu hoặc lỗi: báo rõ, không bịa.
- Không tự mở rộng quyền tool ngoài `tools_allowed`.
