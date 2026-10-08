#!/usr/bin/env python3
"""
congchuc_summarize.py — Tóm tắt nội dung văn bản công văn đến (v2).

Pipeline:
  1. Lấy metadata từ vbden_state.json (số CV, tác giả, trích yếu, trạng thái)
  2. Kiểm tra attachments/<so_den>/ có file không
     - Có → đọc nội dung PDF (pymupdf) / DOCX (python-docx)
     - Không có → tự động tải về qua congchuc_scrape.py --download-only, rồi đọc
  3. Feed nội dung file vào LLM → tóm tắt ngắn gọn bằng tiếng Việt

Usage:
  uv run python congchuc_summarize.py --so-den <số_đến>
"""
import sys
import os
import subprocess
import json
import glob

# --- Paths ---
HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
STATE_FILE = os.path.join(HERMES_HOME, "cron", "cong-van-den", "vbden_state.json")
ATT_BASE = os.path.join(HERMES_HOME, "cron", "cong-van-den", "attachments")
SCRAPE_SCRIPT = os.path.join(HERMES_HOME, "scripts", "congchuc", "congchuc_scrape.py")

# --- LLM config (OpenAI-compatible) ---
LLM_BASE_URL = os.environ.get("HERMES_API_BASE", "http://host.docker.internal:20128/v1")
LLM_API_KEY  = os.environ.get("HERMES_API_KEY",  "sk-52322c0dd90d1c8a-2iry8g-ebb67c15")
LLM_MODEL    = os.environ.get("HERMES_MODEL",     "hermes-combo")
MAX_CONTENT_CHARS = 12000  # Cắt nếu tổng nội dung quá dài


# ─────────────────────────────────────────────────────────────
# 1. Lấy metadata từ state file
# ─────────────────────────────────────────────────────────────
def get_metadata(so_den: str) -> dict:
    """Đọc metadata của văn bản từ vbden_state.json."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        return state.get("documents", {}).get(so_den, {})
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────
# 2. Tải file đính kèm nếu chưa có
# ─────────────────────────────────────────────────────────────
def ensure_attachments(so_den: str) -> list[str]:
    """
    Kiểm tra thư mục attachments/<so_den>/. Nếu trống/không tồn tại,
    tự động chạy congchuc_scrape.py --download-only để tải về.
    Trả về danh sách đường dẫn tuyệt đối của các file đính kèm.
    """
    att_dir = os.path.join(ATT_BASE, so_den)
    files = _list_attachments(att_dir)

    if not files:
        print(f"⏳ Chưa có file đính kèm, đang tải về cho VB #{so_den}...", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, SCRAPE_SCRIPT, "--download-only", so_den],
                capture_output=True, text=True, timeout=120,
                env={**os.environ}
            )
            if result.returncode != 0:
                print(f"⚠️ Tải file gặp lỗi:\n{result.stderr[-800:]}", flush=True)
            else:
                print(result.stdout.strip(), flush=True)
        except subprocess.TimeoutExpired:
            print("⚠️ Timeout khi tải file đính kèm (>120s).", flush=True)
        except Exception as e:
            print(f"⚠️ Không thể tải file: {e}", flush=True)
        files = _list_attachments(att_dir)

    return files


def _list_attachments(att_dir: str) -> list[str]:
    """Trả về danh sách file trong thư mục đính kèm (PDF, DOCX, DOC)."""
    if not os.path.isdir(att_dir):
        return []
    exts = ("*.pdf", "*.docx", "*.doc", "*.PDF", "*.DOCX")
    found = []
    for ext in exts:
        found.extend(glob.glob(os.path.join(att_dir, ext)))
    # Nếu không có PDF/DOCX, lấy tất cả file
    if not found:
        found = [
            os.path.join(att_dir, f)
            for f in os.listdir(att_dir)
            if os.path.isfile(os.path.join(att_dir, f))
        ]
    return sorted(found)


# ─────────────────────────────────────────────────────────────
# 3. Đọc nội dung file
# ─────────────────────────────────────────────────────────────
def read_pdf(path: str) -> str:
    """Đọc text từ PDF bằng pymupdf (fitz)."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(path)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n".join(pages).strip()
    except ImportError:
        return ""
    except Exception as e:
        return f"[Lỗi đọc PDF: {e}]"


def read_docx(path: str) -> str:
    """Đọc text từ DOCX bằng python-docx."""
    try:
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return ""
    except Exception as e:
        return f"[Lỗi đọc DOCX: {e}]"


def extract_text(files: list[str]) -> str:
    """Đọc và ghép nội dung từ tất cả file đính kèm."""
    parts = []
    for path in files:
        fname = os.path.basename(path)
        ext = os.path.splitext(fname)[1].lower()
        if ext == ".pdf":
            text = read_pdf(path)
        elif ext in (".docx", ".doc"):
            text = read_docx(path)
        else:
            # Thử đọc dạng text
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except Exception:
                text = ""

        if text and not text.startswith("[Lỗi"):
            parts.append(f"=== {fname} ===\n{text}")

    combined = "\n\n".join(parts)
    # Cắt nếu quá dài
    if len(combined) > MAX_CONTENT_CHARS:
        combined = combined[:MAX_CONTENT_CHARS] + "\n\n[... nội dung bị cắt bớt ...]"
    return combined


# ─────────────────────────────────────────────────────────────
# 4. LLM tóm tắt
# ─────────────────────────────────────────────────────────────
def llm_summarize(metadata: dict, content: str, so_den: str) -> str:
    """Gọi LLM để tóm tắt nội dung văn bản."""
    try:
        from openai import OpenAI
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    except ImportError:
        return None

    trich_yeu = metadata.get("trich_yeu", "")
    tac_gia   = metadata.get("tac_gia", "")
    so_cv     = metadata.get("so_ky_hieu", "")

    system_prompt = (
        "Bạn là trợ lý hành chính chuyên đọc và tóm tắt văn bản công văn hành chính Việt Nam. "
        "Hãy tóm tắt ngắn gọn, súc tích, đúng trọng tâm, dễ hiểu cho lãnh đạo đọc nhanh. "
        "Không bịa thêm thông tin. Trả lời hoàn toàn bằng tiếng Việt."
    )

    user_prompt = f"""Văn bản công văn #{so_den}:
- Số/ký hiệu: {so_cv}
- Cơ quan gửi: {tac_gia}
- Trích yếu: {trich_yeu}

Nội dung file đính kèm:
{content}

Hãy tóm tắt văn bản này theo cấu trúc:
1. **Mục đích / Yêu cầu chính**: (1-2 câu)
2. **Nội dung cụ thể**: (các điểm chính, gạch đầu dòng)
3. **Thời hạn / Deadline**: (nếu có, ghi rõ)
4. **Đơn vị cần thực hiện**: (nếu có)
5. **Đề xuất xử lý**: (ngắn gọn — đọc để biết / cần phản hồi / cần triển khai thực hiện)
"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=1000,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM error: {e}]"


# ─────────────────────────────────────────────────────────────
# 5. Main
# ─────────────────────────────────────────────────────────────
def main():
    # Parse --so-den
    so_den = None
    args = sys.argv[1:]
    if "--so-den" in args:
        idx = args.index("--so-den")
        so_den = args[idx + 1] if idx + 1 < len(args) else None
    elif args and not args[0].startswith("--"):
        so_den = args[0]

    if not_so_den := not so_den:
        print("Usage: congchuc_summarize.py --so-den <số_đến>")
        sys.exit(1)

    so_den = so_den.strip()

    # ── Metadata ──
    meta = get_metadata(so_den)
    so_cv    = meta.get("so_ky_hieu", "N/A")
    tac_gia  = meta.get("tac_gia",    "N/A")
    trich_yeu = meta.get("trich_yeu", "N/A")
    status   = meta.get("status",     "N/A")
    updated  = meta.get("ngay_den") or meta.get("status_updated_at", "N/A")

    header = (
        f"📄 VB #{so_den} — Tóm tắt\n"
        f"{'━'*22}\n"
        f"🏛 Cơ quan gửi: {tac_gia}\n"
        f"📑 Số công văn: {so_cv}\n"
        f"📝 Trích yếu: {trich_yeu}\n"
        f"📅 Cập nhật: {updated}\n"
        f"{'🔴' if status == 'new' else '🟡' if status == 'wip' else '✅'} Trạng thái: {status}\n"
    )
    print(header, flush=True)

    # ── Attachments ──
    files = ensure_attachments(so_den)

    if not files:
        print(
            "⚠️ Không có file đính kèm để tóm tắt nội dung.\n"
            "Chỉ hiển thị thông tin cơ bản từ state file."
        )
        return

    print(f"📎 {len(files)} file đính kèm: {', '.join(os.path.basename(f) for f in files)}\n")

    # ── Extract text ──
    content = extract_text(files)
    if not content.strip():
        print("⚠️ Không đọc được nội dung từ file đính kèm (có thể là file scan/ảnh).")
        return

    # ── LLM summarize ──
    print("🤖 Đang tóm tắt nội dung...\n", flush=True)
    summary = llm_summarize(meta, content, so_den)

    if summary:
        print(summary)
    else:
        print("⚠️ LLM không phản hồi. Nội dung thô (500 ký tự đầu):\n")
        print(content[:500])


if __name__ == "__main__":
    main()
