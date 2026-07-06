#!/usr/bin/env python3
import json
from datetime import datetime
from typing import Any, Dict, List


def _kv_table(data: Dict[str, Any]) -> str:
    lines = ["| Trường | Giá trị |", "|---|---|"]
    for k, v in data.items():
        vv = "" if v is None else str(v).replace("\n", "<br>")
        lines.append(f"| {k} | {vv} |")
    return "\n".join(lines)


def render_markdown(pl: str, general: Dict[str, Any], packages: List[Dict[str, Any]], source: Dict[str, Any], status: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# KHLCNT Export — {pl}",
        "",
        f"- Mã PL: `{pl}`",
        f"- Thời điểm export: {now}",
        "",
        "## 1) Thông tin chung",
        "",
        _kv_table(general or {"Ghi chú": "Chưa có dữ liệu"}),
        "",
        "## 2) Thông tin gói thầu",
        "",
    ]

    if packages:
        for i, p in enumerate(packages, 1):
            lines += [f"### Gói thầu {i}", "", _kv_table(p), ""]
    else:
        lines += ["- Chưa lấy được dữ liệu mục này.", ""]

    return "\n".join(lines)
