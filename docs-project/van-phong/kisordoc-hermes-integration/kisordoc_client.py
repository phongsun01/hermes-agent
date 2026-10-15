#!/usr/bin/env python3
"""
kisordoc_client.py
──────────────────
HTTP client cho KisorDoc FastAPI.  Được gọi bởi Hermes skill qua subprocess.

Cách dùng (tất cả output đều là JSON trên stdout):

    # Liệt kê quy trình
    python kisordoc_client.py list-options

    # Liệt kê gói thầu theo quy trình
    python kisordoc_client.py list-packages --option Opt1

    # Liệt kê template theo quy trình
    python kisordoc_client.py list-templates --option Opt1

    # Sinh văn bản (tự poll đến done/failed, in log incremental ra stderr)
    python kisordoc_client.py generate \\
        --option Opt1 \\
        --package "01. MS26-01 - Gói thầu tư vấn XYZ" \\
        --templates "BaoCao" "TuTrinhPheDuyet" \\
        [--dry-run] \\
        [--config-row-range "2-97"]

    # Liệt kê job gần đây
    python kisordoc_client.py list-jobs [--limit 10]

Biến môi trường:
    KISORDOC_API_URL       URL gốc của KisorDoc API
                           Mặc định: http://host.docker.internal:8000 (Docker)
                           Đổi sang http://localhost:8000 nếu chạy CLI Windows native
    KISORDOC_POLL_INTERVAL Giây chờ giữa mỗi lần poll job status (mặc định: 2)
    KISORDOC_TIMEOUT       Timeout tổng tính từ lúc tạo job, tính bằng giây (mặc định: 300)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Config từ env
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL: str = os.environ.get(
    "KISORDOC_API_URL",
    "http://host.docker.internal:8000",  # Docker default
).rstrip("/")

POLL_INTERVAL: float = float(os.environ.get("KISORDOC_POLL_INTERVAL", "2"))
TIMEOUT: float = float(os.environ.get("KISORDOC_TIMEOUT", "300"))


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib only — không cần requests/httpx)
# ─────────────────────────────────────────────────────────────────────────────

def _get(path: str, params: dict[str, str] | None = None) -> Any:
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        _die(f"HTTP {e.code} GET {path}: {body}")
    except (urllib.error.URLError, OSError) as e:
        _die(
            f"Không kết nối được KisorDoc API tại {BASE_URL}\n"
            f"  Lỗi: {e}\n"
            f"  Kiểm tra:\n"
            f"    1. KisorDoc runner.py đang chạy?\n"
            f"    2. Nếu Hermes trong Docker: KISORDOC_API_URL=http://host.docker.internal:8000\n"
            f"    3. Nếu chạy CLI Windows: KISORDOC_API_URL=http://localhost:8000"
        )


def _post(path: str, body: dict) -> Any:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_str = e.read().decode(errors="replace")
        _die(f"HTTP {e.code} POST {path}: {body_str}")
    except (urllib.error.URLError, OSError) as e:
        _die(f"Không kết nối được KisorDoc API tại {BASE_URL}: {e}")


def _die(msg: str) -> None:
    print(json.dumps({"success": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────────────────────────────────────

def action_list_options() -> None:
    """GET /options → [{key, label}]"""
    data = _get("/options")
    print(json.dumps({"success": True, "options": data}, ensure_ascii=False))


def action_list_packages(option: str) -> None:
    """GET /packages?option=X → [{id, label}]
    
    LƯU Ý: API hiện tại trả id = label = ID thuần (ví dụ "MS26-01").
    Label đầy đủ ("01. MS26-01 - Tên gói thầu") hiển thị trên Gradio UI.
    Khi gọi generate, truyền id này vào --package.
    """
    data = _get("/packages", {"option": option})
    print(json.dumps({"success": True, "option": option, "packages": data}, ensure_ascii=False))


def action_list_templates(option: str) -> None:
    """GET /templates?option=X → [template_name_str]"""
    data = _get("/templates", {"option": option})
    print(json.dumps({"success": True, "option": option, "templates": data}, ensure_ascii=False))


def action_generate(
    option: str,
    package_label: str,
    templates: list[str],
    dry_run: bool = False,
    config_row_range: str | None = None,
) -> None:
    """POST /generate → poll /jobs/{id} đến done/failed.
    
    Log tiến độ in ra stderr theo thời gian thực.
    Kết quả cuối cùng (JSON) in ra stdout.
    """
    # 1. Tạo job
    body: dict = {
        "option": option,
        "package_label": package_label,
        "templates": templates,
        "dry_run": dry_run,
    }
    if config_row_range:
        body["config_row_range"] = config_row_range

    created = _post("/generate", body)
    job_id: str = created["job_id"]

    print(f"[kisordoc] Job tạo thành công: {job_id}", file=sys.stderr)
    print(f"[kisordoc] Đang sinh văn bản — option={option}, package={package_label}", file=sys.stderr)
    if dry_run:
        print("[kisordoc] ⚠️  Chế độ dry-run — không tạo file thật", file=sys.stderr)

    # 2. Poll đến khi done/failed hoặc timeout
    offset = 0
    deadline = time.monotonic() + TIMEOUT

    while True:
        if time.monotonic() > deadline:
            _die(
                f"Timeout sau {TIMEOUT}s — job {job_id} vẫn chưa hoàn thành.\n"
                f"Kiểm tra trạng thái thủ công: GET {BASE_URL}/jobs/{job_id}"
            )

        params = {"log_offset": str(offset)}
        status_data = _get(f"/jobs/{job_id}", params)

        # In log mới ra stderr (để Hermes thấy tiến độ)
        new_logs: list[dict] = status_data.get("log", [])
        for entry in new_logs:
            level = entry.get("level", "INFO").upper()
            msg = entry.get("message", "")
            ts = entry.get("ts", "")[:19]  # cắt bỏ microseconds
            icon = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "⚠️ " if level == "WARNING" else "  "
            print(f"[kisordoc] {icon} [{ts}] {msg}", file=sys.stderr)
        offset += len(new_logs)

        job_status = status_data.get("status")
        if job_status == "done":
            result = status_data.get("result", {})
            output = {
                "success": True,
                "job_id": job_id,
                "status": "done",
                "total": result.get("total", 0),
                "succeeded": result.get("succeeded", 0),
                "failed": result.get("failed", 0),
                "skipped": result.get("skipped", 0),
                "duration_seconds": result.get("duration_seconds"),
                "files": result.get("files", []),
                "output_paths": result.get("output_paths", []),
                "download_url": f"{BASE_URL}/jobs/{job_id}/files",
            }
            # Tóm tắt ra stderr
            print(
                f"[kisordoc] ✅ Hoàn thành: {output['succeeded']}/{output['total']} file"
                f" ({output['duration_seconds']:.1f}s)",
                file=sys.stderr,
            )
            if output["failed"]:
                print(f"[kisordoc] ❌ {output['failed']} file lỗi", file=sys.stderr)
            print(json.dumps(output, ensure_ascii=False))
            return

        if job_status == "failed":
            error = status_data.get("error") or "Không rõ lỗi"
            _die(f"Job {job_id} thất bại: {error}")

        # Vẫn đang chạy — chờ
        time.sleep(POLL_INTERVAL)


def action_list_jobs(limit: int = 10) -> None:
    """GET /jobs?limit=N → danh sách job gần đây"""
    data = _get("/jobs", {"limit": str(limit)})
    print(json.dumps({"success": True, "jobs": data}, ensure_ascii=False))


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="KisorDoc HTTP client — dùng bởi Hermes skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="action", required=True)

    # list-options
    sub.add_parser("list-options", help="Liệt kê các quy trình (Opt1, Opt2...)")

    # list-packages
    p_pkg = sub.add_parser("list-packages", help="Liệt kê gói thầu theo quy trình")
    p_pkg.add_argument("--option", required=True, help="Ví dụ: Opt1")

    # list-templates
    p_tpl = sub.add_parser("list-templates", help="Liệt kê template Word theo quy trình")
    p_tpl.add_argument("--option", required=True, help="Ví dụ: Opt1")

    # generate
    p_gen = sub.add_parser("generate", help="Sinh văn bản (tự poll đến done/failed)")
    p_gen.add_argument("--option", required=True, help="Ví dụ: Opt1")
    p_gen.add_argument(
        "--package", required=True, dest="package_label",
        help='Package ID từ list-packages. Ví dụ: "MS26-01" hoặc label đầy đủ',
    )
    p_gen.add_argument(
        "--templates", required=True, nargs="+",
        help="Tên template (không extension). Ví dụ: BaoCao TuTrinhPheDuyet",
    )
    p_gen.add_argument("--dry-run", action="store_true", help="Kiểm tra không tạo file thật")
    p_gen.add_argument(
        "--config-row-range",
        help='Dải hàng config cần sinh. Ví dụ: "2-97". Bỏ qua = sinh tất cả',
    )

    # list-jobs
    p_jobs = sub.add_parser("list-jobs", help="Liệt kê job gần đây")
    p_jobs.add_argument("--limit", type=int, default=10, help="Số job tối đa (mặc định: 10)")

    args = parser.parse_args()

    if args.action == "list-options":
        action_list_options()
    elif args.action == "list-packages":
        action_list_packages(args.option)
    elif args.action == "list-templates":
        action_list_templates(args.option)
    elif args.action == "generate":
        action_generate(
            option=args.option,
            package_label=args.package_label,
            templates=args.templates,
            dry_run=args.dry_run,
            config_row_range=args.config_row_range,
        )
    elif args.action == "list-jobs":
        action_list_jobs(limit=args.limit)


if __name__ == "__main__":
    main()
