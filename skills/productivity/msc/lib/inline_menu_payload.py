#!/usr/bin/env python3
from __future__ import annotations


def _build_inline_menu_payload(level: str = 'root') -> dict:
    lvl = (level or 'root').strip().lower()

    if lvl in ('root', 'menu', 'main'):
        return {
            'text': '🏛️ Mua sắm công (MSC)\n\nChọn chức năng:\n1) 📋 Watchlist\n2) 🔎 Tra cứu TBMT/KHLCNT\n3) 🧾 Export chi tiết\n4) 📊 Phân tích nhà thầu\n5) 📜 Lịch sử tham dự thầu\n6) 📈 Trạng thái token\n\nLệnh nhanh:\n- `msc fl list` - Danh sách theo dõi\n- `msc tbmt <n> <đơn vị>` - TBMT mới nhất\n- `msc kh <n> <đơn vị>` - KHLCNT mới nhất\n- `msc exp <IB/PL code>` - Export chi tiết\n- `msc ptnt <MST>` - Phân tích nhà thầu\n- `msc ls <MST>` - Lịch sử tham dự thầu\n- `msc status` - Kiểm tra token',
            'buttons': [
                [
                    {'text': '📋 Watchlist', 'callback_data': 'v1|msc|open|watchlist'},
                    {'text': '🔎 Tra cứu', 'callback_data': 'v1|msc|open|lookup'},
                ],
                [
                    {'text': '🧾 Export', 'callback_data': 'v1|msc|open|export'},
                    {'text': '📊 Phân tích NT', 'callback_data': 'v1|msc|open|ptnt'},
                ],
                [
                    {'text': '📜 Lịch sử NT', 'callback_data': 'v1|msc|open|hisbid'},
                    {'text': '📈 Trạng thái', 'callback_data': 'v1|msc|run|status'},
                ],
            ],
            'meta': {'menu_level': 'root'}
        }

    if lvl in ('msc_ptnt', 'ptnt'):
        return {
            'text': '📊 Phân tích nhà thầu (PTNT)\n\nCú pháp:\n- `msc ptnt <MST>` hoặc `/msc ptnt <MST>`\n\nVí dụ:\n- `/msc ptnt vn0108557117` (Công ty TNHH Đầu tư Thiết bị Công nghệ Khoa học VINMED)',
            'buttons': [
                [
                    {'text': '⬅️ Quay lại', 'callback_data': 'v1|msc|open|main'},
                ],
            ],
            'meta': {'menu_level': 'msc_ptnt'}
        }

    if lvl in ('msc_hisbid', 'hisbid', 'ls'):
        return {
            'text': '📜 Lịch sử tham dự thầu (LS)\n\nCú pháp:\n- `msc ls <MST>` hoặc `/msc ls <MST>`\n\nVí dụ:\n- `/msc ls vn0108557117` (Công ty TNHH Đầu tư Thiết bị Công nghệ Khoa học VINMED)',
            'buttons': [
                [
                    {'text': '⬅️ Quay lại', 'callback_data': 'v1|msc|open|main'},
                ],
            ],
            'meta': {'menu_level': 'msc_hisbid'}
        }

    if lvl in ('msc_watchlist', 'watchlist'):
        return {
            'text': '📋 Watchlist\n\nLệnh:\n- `msc fl list` - Danh sách theo dõi\n- `msc fl add <id> [name]` - Thêm đơn vị\n- `msc fl remove <id>` - Xóa đơn vị\n- `msc fl latest [n]` - TBMT mới nhất',
            'buttons': [
                [
                    {'text': '📄 Danh sách', 'callback_data': 'v1|msc|run|fl_list'},
                    {'text': '📊 Latest TBMT', 'callback_data': 'v1|msc|run|fl_latest'},
                ],
                [
                    {'text': '⬅️ Quay lại', 'callback_data': 'v1|msc|open|main'},
                ],
            ],
            'meta': {'menu_level': 'msc_watchlist'}
        }

    if lvl in ('msc_lookup', 'lookup'):
        return {
            'text': '🔎 Tra cứu TBMT/KHLCNT\n\nLệnh:\n- `msc tbmt <n> <đơn vị>` - Ví dụ: `msc tbmt 5 bệnh viện`\n- `msc kh <n> <đơn vị>` - Ví dụ: `msc kh 3 bạch mai`\n- `msc tbmt IB...` - Tra theo mã IB\n- `msc kh PL...` - Tra theo mã PL',
            'buttons': [
                [
                    {'text': '⬅️ Quay lại', 'callback_data': 'v1|msc|open|main'},
                ],
            ],
            'meta': {'menu_level': 'msc_lookup'}
        }

    if lvl in ('msc_export', 'export'):
        return {
            'text': '🧾 Export chi tiết\n\nLệnh:\n- `msc exp IB...` - Export TBMT theo mã IB\n- `msc exp PL...` - Export KHLCNT theo mã PL\n- `msc exp IB... PL...` - Export nhiều mã (batch)\n\nThêm `--skip-invalid` để bỏ qua mã sai',
            'buttons': [
                [
                    {'text': '⬅️ Quay lại', 'callback_data': 'v1|msc|open|main'},
                ],
            ],
            'meta': {'menu_level': 'msc_export'}
        }

    # Default fallback
    return {
        'text': '🏛️ Mua sắm công (MSC)\n\nChọn chức năng:',
        'buttons': [
            [
                {'text': '📋 Watchlist', 'callback_data': 'v1|msc|open|watchlist'},
                {'text': '🔎 Tra cứu', 'callback_data': 'v1|msc|open|lookup'},
            ],
            [
                {'text': '🧾 Export', 'callback_data': 'v1|msc|open|export'},
                {'text': '📊 Phân tích NT', 'callback_data': 'v1|msc|open|ptnt'},
            ],
            [
                {'text': '📜 Lịch sử NT', 'callback_data': 'v1|msc|open|hisbid'},
                {'text': '📈 Trạng thái', 'callback_data': 'v1|msc|run|status'},
            ],
        ],
        'meta': {'menu_level': 'root'}
    }
