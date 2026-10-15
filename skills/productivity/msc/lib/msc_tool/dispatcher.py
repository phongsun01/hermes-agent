from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .router import RoutedQuery
from .schema import ErrorInfo, MscSchema, QueryParams

SKILL_ROOT = Path(__file__).parent.parent.parent  # msc_tool/dispatcher.py -> lib -> msc
SCRIPTS_DIR = str(SKILL_ROOT / 'scripts')


def _now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(timespec="seconds")


def _run_json(cmd: list[str]) -> dict:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or "script_error")
    return json.loads(cp.stdout)


def dispatch(query: RoutedQuery) -> MscSchema:
    try:
        if query.intent == "lookup_pl" and query.code:
            data = _run_json(["python3", f"{SCRIPTS_DIR}/msc_pl_lookup.py", query.code])
            rows = [data] if data.get("status") == "ok" else []
            return MscSchema(
                query_type="pl",
                query_params=QueryParams(code=query.code),
                source="muasamcong_hidden_api",
                script_used="msc_pl_lookup.py",
                fetched_at=_now_iso(),
                total_count=len(rows),
                records=rows,
                error=None if rows else ErrorInfo("not_found", f"Không thấy {query.code}"),
            )

        if query.intent == "lookup_ib" and query.code:
            data = _run_json(["python3", f"{SCRIPTS_DIR}/msc_ib_lookup.py", query.code])
            rows = [data] if data.get("status") == "ok" else []
            return MscSchema(
                query_type="ib",
                query_params=QueryParams(code=query.code),
                source="muasamcong_hidden_api",
                script_used="msc_ib_lookup.py",
                fetched_at=_now_iso(),
                total_count=len(rows),
                records=rows,
                error=None if rows else ErrorInfo("not_found", f"Không thấy {query.code}"),
            )

        if query.intent == "list_kh" and query.unit:
            n = query.n or 5
            data = _run_json(["python3", f"{SCRIPTS_DIR}/msc_kh_precise.py", query.unit, "-n", str(n)])
            rows = data.get("rows", [])
            return MscSchema(
                query_type="kh",
                query_params=QueryParams(unit=query.unit, n=n),
                source="muasamcong_hidden_api",
                script_used="msc_kh_precise.py",
                fetched_at=_now_iso(),
                total_count=data.get("total", len(rows)),
                records=rows,
                error=None if rows else ErrorInfo("not_found", "Không có kết quả"),
            )

        if query.intent == "list_tbmt" and query.unit:
            n = query.n or 5
            data = _run_json(["python3", f"{SCRIPTS_DIR}/msc_tbmt_precise.py", query.unit, "-n", str(n)])
            rows = data.get("rows", [])
            return MscSchema(
                query_type="tbmt",
                query_params=QueryParams(unit=query.unit, n=n),
                source="muasamcong_hidden_api",
                script_used="msc_tbmt_precise.py",
                fetched_at=_now_iso(),
                total_count=data.get("total", len(rows)),
                records=rows,
                error=None if rows else ErrorInfo("not_found", "Không có kết quả"),
            )

        return MscSchema(
            query_type="tbmt",
            query_params=QueryParams(unit=query.unit, n=query.n),
            source="muasamcong_hidden_api",
            script_used="router",
            fetched_at=_now_iso(),
            total_count=0,
            records=[],
            error=ErrorInfo("ambiguous_unit", "Bạn muốn tra KHLCNT hay TBMT?"),
        )
    except TimeoutError:
        return MscSchema(
            query_type="tbmt",
            query_params=QueryParams(unit=query.unit, n=query.n),
            source="muasamcong_hidden_api",
            script_used="dispatcher",
            fetched_at=_now_iso(),
            total_count=0,
            records=[],
            error=ErrorInfo("api_timeout", "Quá thời gian phản hồi"),
        )
    except Exception as e:
        return MscSchema(
            query_type="tbmt",
            query_params=QueryParams(unit=query.unit, n=query.n),
            source="muasamcong_hidden_api",
            script_used="dispatcher",
            fetched_at=_now_iso(),
            total_count=0,
            records=[],
            error=ErrorInfo("parse_error", str(e)[:300]),
        )
