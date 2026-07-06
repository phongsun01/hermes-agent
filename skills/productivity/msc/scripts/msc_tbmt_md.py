#!/usr/bin/env python3
from datetime import datetime
from typing import Any, Dict, List


def _kv_table(data: Dict[str, Any]) -> str:
    lines = ["| Trường | Giá trị |", "|---|---|"]
    for k, v in (data or {}).items():
        vv = "" if v is None else str(v).replace("\n", "<br>")
        lines.append(f"| {k} | {vv} |")
    return "\n".join(lines)


def render_markdown(ib: str, tabs: Dict[str, Any]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab1 = (tabs or {}).get("thong_bao_moi_thau") or {}
    tab2 = (tabs or {}).get("bien_ban_mo_thau") or {}
    tab3 = (tabs or {}).get("ket_qua_lua_chon_nha_thau") or {}

    lines = [
        f"# TBMT Export — {ib}",
        "",
        f"- Số TBMT: `{ib}`",
        f"- Thời điểm export: {now}",
        "",
        "## 1) Thông báo mời thầu",
        "",
        _kv_table(tab1 if tab1 else {"Ghi chú": "Chưa có dữ liệu"}),
        "",
        "## 2) Biên bản mở thầu",
        "",
        _kv_table(tab2 if tab2 else {"Ghi chú": "Chưa có dữ liệu"}),
        "",
        "## 3) Kết quả lựa chọn nhà thầu",
        "",
    ]

    if isinstance(tab3, dict) and tab3:
        general = tab3.get("thong_tin_chung") or {}
        winners = tab3.get("danh_sach_nha_thau_trung") or []

        lines += ["### Thông tin chung", "", _kv_table(general if general else {"Ghi chú": "Chưa có dữ liệu"}), ""]

        if isinstance(winners, list) and winners:
            lines += ["### Danh sách nhà thầu trúng thầu", ""]
            for i, row in enumerate(winners, 1):
                lines += [f"#### Nhà thầu {i}", "", _kv_table(row if isinstance(row, dict) else {}), ""]
        else:
            lines += ["- Chưa có nhà thầu trúng thầu.", ""]
    else:
        lines += ["- Chưa lấy được dữ liệu mục này.", ""]

    return "\n".join(lines)
