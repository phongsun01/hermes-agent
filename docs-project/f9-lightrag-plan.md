# F9 — Dự thảo văn bản trả lời với LightRAG

**Trạng thái:** 📌 Kế hoạch triển khai | **Cập nhật:** 2026-06-24 ICT  
**Thay thế:** Onyx RAG → LightRAG (HKUDS/LightRAG, MIT license)

---

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hermes Gateway (Docker)                        │
│                                                                   │
│  Zalo msg "dự thảo #2348"                                        │
│         │                                                         │
│         ▼                                                         │
│  [F9 Handler: congchuc_draft.py]                                  │
│         │                                                         │
│    1. Đọc vbden_state.json → lấy metadata + path attachment      │
│    2. Extract text từ attachment (PDF/DOCX)                       │
│    3. Query LightRAG API → lấy context pháp lý                   │
│    4. LLM generate Markdown theo template NĐ 30                   │
│    5. convert_md_to_docx.py → .docx                              │
│    6. Gửi Zalo kèm link tải + preview 3 dòng                     │
└─────────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐      ┌──────────────────────────┐
│  LightRAG Server│      │  ~/.hermes/cron/          │
│  localhost:9621 │      │  cong-van-den/            │
│  (Docker)       │      │  ├── attachments/         │
│                 │      │  ├── drafts/              │
│  /query         │      │  └── vbden_state.json     │
│  /documents/    │      └──────────────────────────┘
│    upload       │
└─────────────────┘
```

---

## Phase 0 — Triển khai LightRAG (1–2 ngày)

### 0.1 Docker Compose

Thêm service `lightrag` vào `docker-compose.yml` hiện tại của Hermes:

```yaml
# docker-compose.yml — thêm vào services:
  lightrag:
    image: ghcr.io/hkuds/lightrag:latest
    ports:
      - "9621:9621"
    env_file:
      - .env.lightrag          # file riêng, không lẫn vào .env Hermes
    volumes:
      - lightrag_data:/app/data
    restart: unless-stopped

volumes:
  lightrag_data:
```

### 0.2 File `.env.lightrag`

```ini
HOST=0.0.0.0
PORT=9621

# LLM cho entity extraction (cần model mạnh, ít nhất 32B)
LLM_BINDING=openai
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=sk-your-key
LLM_MODEL=gpt-4o-mini               # hoặc gemini-2.5-flash nếu dùng OpenAI-compat endpoint

# Embedding (KHÔNG THAY ĐỔI SAU KHI ĐÃ INDEX)
EMBEDDING_BINDING=openai
EMBEDDING_BINDING_HOST=https://api.openai.com/v1
EMBEDDING_BINDING_API_KEY=sk-your-key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Auth
AUTH_ACCOUNTS=admin:changeme123
LIGHTRAG_API_KEY=your-internal-api-key

# Storage (default: NetworkX + NanoVectorDB — đủ cho corpus nhỏ <500 docs)
WORKING_DIR=/app/data/rag_storage
INPUT_DIR=/app/data/inputs

# Query defaults
DEFAULT_SEARCH_MODE=hybrid           # hybrid = graph + vector, tốt nhất cho VB hành chính
```

> ⚠️ **Quan trọng:** `EMBEDDING_MODEL` và `EMBEDDING_DIM` KHÔNG được thay đổi sau lần index đầu tiên. Thay đổi yêu cầu xóa toàn bộ vector store và re-index.

### 0.3 Khởi động & kiểm tra

```bash
docker compose up -d lightrag

# Kiểm tra health
curl http://localhost:9621/health

# Xem Web UI (knowledge graph visualization)
# http://localhost:9621/webui
```

---

## Phase 1 — Xây dựng Corpus (2–3 ngày)

### Corpus cần ingest theo thứ tự ưu tiên:

| Ưu tiên | Loại tài liệu | Nguồn | Số lượng ước tính |
|---------|--------------|-------|------------------|
| 🔴 Cao | Văn bản mẫu NĐ 30 (công văn, quyết định, tờ trình) | `xu-ly-van-phong/templates/` | ~9 file |
| 🔴 Cao | Công văn đến đã có trong `attachments/` | `~/.hermes/cron/cong-van-den/attachments/` | tất cả |
| 🟡 Trung bình | NĐ/TT ngành Y tế hay dùng | Thư mục tài liệu pháp quy | 10–30 file |
| 🟢 Thấp | Công văn đi đã ban hành (văn bản mẫu thực tế) | Nếu có sẵn | tuỳ |

### Script ingest batch (`scripts/lightrag/ingest_corpus.py`):

```python
#!/usr/bin/env python3
"""Ingest batch documents vào LightRAG."""

import os
import requests
from pathlib import Path

LIGHTRAG_URL = os.getenv("LIGHTRAG_API_URL", "http://localhost:9621")
LIGHTRAG_KEY = os.getenv("LIGHTRAG_API_KEY", "your-internal-api-key")

HEADERS = {"X-API-Key": LIGHTRAG_KEY}

def upload_file(filepath: Path):
    with open(filepath, "rb") as f:
        resp = requests.post(
            f"{LIGHTRAG_URL}/documents/upload",
            headers=HEADERS,
            files={"file": (filepath.name, f, "application/octet-stream")},
            timeout=120
        )
    if resp.status_code == 200:
        print(f"✅ {filepath.name}")
    else:
        print(f"❌ {filepath.name}: {resp.status_code} {resp.text[:100]}")

def ingest_directory(directory: str, extensions: list[str] = None):
    exts = extensions or [".pdf", ".docx", ".txt", ".md"]
    path = Path(directory)
    files = [f for f in path.rglob("*") if f.suffix.lower() in exts]
    print(f"Tìm thấy {len(files)} file trong {directory}")
    for f in files:
        upload_file(f)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ingest_corpus.py <directory>")
        sys.exit(1)
    ingest_directory(sys.argv[1])
```

```bash
# Ingest templates NĐ 30
python scripts/lightrag/ingest_corpus.py \
  D:/Antigravity/Hermes/docs/xu-ly-van-phong-v1.0/templates/

# Ingest attachments đã tải về
python scripts/lightrag/ingest_corpus.py \
  ~/.hermes/cron/cong-van-den/attachments/

# Ingest NĐ/TT ngành (nếu có thư mục riêng)
python scripts/lightrag/ingest_corpus.py \
  D:/Antigravity/docs/phap-quy/
```

### Auto-ingest attachment mới (tích hợp vào F16a):

Sau khi F16a tải xong attachment, thêm 1 bước tự động ingest vào LightRAG:

```python
# Trong congchuc_scrape.py, sau khi download xong attachment:
def auto_ingest_to_lightrag(filepath: str):
    """Ingest file mới vào LightRAG ngay sau khi tải về."""
    url = os.getenv("LIGHTRAG_API_URL", "http://localhost:9621")
    key = os.getenv("LIGHTRAG_API_KEY", "")
    if not key:
        return  # LightRAG chưa cấu hình, bỏ qua
    try:
        with open(filepath, "rb") as f:
            requests.post(
                f"{url}/documents/upload",
                headers={"X-API-Key": key},
                files={"file": (os.path.basename(filepath), f)},
                timeout=60
            )
    except Exception as e:
        print(f"[LightRAG ingest warning] {e}")  # Không raise, không block F16a
```

---

## Phase 2 — Script F9 (`congchuc_draft.py`)

### File: `~/.hermes/scripts/congchuc/congchuc_draft.py`

```python
#!/usr/bin/env python3
"""
F9 — Dự thảo văn bản trả lời chuẩn NĐ 30.
Usage: python congchuc_draft.py --so-den 2348
"""

import os
import json
import argparse
import requests
import subprocess
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
HERMES_HOME    = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
STATE_FILE     = HERMES_HOME / "cron/cong-van-den/vbden_state.json"
DRAFTS_DIR     = HERMES_HOME / "cron/cong-van-den/drafts"
ATTACHMENTS_DIR= HERMES_HOME / "cron/cong-van-den/attachments"
TEMPLATE_PATH  = Path(os.getenv("CONGVAN_TEMPLATE",
    "D:/Antigravity/Hermes/docs/xu-ly-van-phong-v1.0/templates/docx-hanh-chinh-cong-van.md"))
CONVERT_SCRIPT = Path(os.getenv("CONVERT_SCRIPT",
    "D:/Antigravity/Hermes/scripts/convert/convert_md_to_docx.py"))

LIGHTRAG_URL   = os.getenv("LIGHTRAG_API_URL", "http://localhost:9621")
LIGHTRAG_KEY   = os.getenv("LIGHTRAG_API_KEY", "")
LLM_API_KEY    = os.getenv("OPENAI_API_KEY", "")

ORG_NAME       = os.getenv("CONGVAN_ORG_NAME", "SỞ Y TẾ")
SIGNER_NAME    = os.getenv("CONGVAN_SIGNER_NAME", "Nguyễn Văn A")
SIGNER_TITLE   = os.getenv("CONGVAN_SIGNER_TITLE", "GIÁM ĐỐC")


# ── Step 1: Đọc metadata từ state ─────────────────────────────────────────────
def get_vb_metadata(so_den: str) -> dict:
    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)
    docs = state.get("documents", {})
    if so_den not in docs:
        raise ValueError(f"Không tìm thấy số đến {so_den} trong state")
    return docs[so_den]


# ── Step 2: Extract text từ attachment ────────────────────────────────────────
def extract_attachment_text(so_den: str) -> str:
    att_dir = ATTACHMENTS_DIR / so_den
    if not att_dir.exists():
        return ""
    texts = []
    for f in att_dir.iterdir():
        if f.suffix.lower() == ".pdf":
            try:
                result = subprocess.run(
                    ["pdftotext", str(f), "-"],
                    capture_output=True, text=True, timeout=30
                )
                texts.append(result.stdout[:3000])  # giới hạn 3000 ký tự / file
            except Exception:
                pass
        elif f.suffix.lower() in [".docx", ".doc"]:
            try:
                result = subprocess.run(
                    ["python", "-c",
                     f"import docx2txt; print(docx2txt.process('{f}'))"],
                    capture_output=True, text=True, timeout=30
                )
                texts.append(result.stdout[:3000])
            except Exception:
                pass
    return "\n---\n".join(texts)


# ── Step 3: Query LightRAG ─────────────────────────────────────────────────────
def query_lightrag(query: str) -> str:
    if not LIGHTRAG_KEY:
        return ""  # LightRAG chưa cấu hình → fallback
    try:
        resp = requests.post(
            f"{LIGHTRAG_URL}/query",
            headers={
                "X-API-Key": LIGHTRAG_KEY,
                "Content-Type": "application/json"
            },
            json={"query": query, "mode": "hybrid"},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception as e:
        print(f"[LightRAG warning] {e}")
    return ""


# ── Step 4: LLM generate Markdown ─────────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là chuyên viên hành chính soạn thảo công văn theo chuẩn Nghị định 30/2020/NĐ-CP.
Trả về DUY NHẤT nội dung Markdown của công văn, không có giải thích hay bình luận thêm.

Cấu trúc bắt buộc (giữ nguyên thứ tự):
1. Quốc hiệu tiêu ngữ (2 dòng, in hoa, căn giữa)
2. Tên cơ quan ban hành + số ký hiệu (cột trái) | Địa danh ngày tháng (cột phải) 
3. Tên loại văn bản + trích yếu (in hoa, căn giữa)
4. Kính gửi
5. Nội dung (đầy đủ các mục, viết cẩn thận)
6. Chức danh người ký (cột phải)
7. Nơi nhận (cột trái)"""

def generate_draft_markdown(meta: dict, attachment_text: str, rag_context: str) -> str:
    import openai
    client = openai.OpenAI(api_key=LLM_API_KEY)

    user_content = f"""Soạn thảo công văn trả lời cho văn bản đến sau:

**Thông tin văn bản đến:**
- Số đến: {meta.get('so_den', '')}
- Số ký hiệu: {meta.get('so_ky_hieu', '')}
- Tác giả/Cơ quan gửi: {meta.get('tac_gia', '')}
- Ngày nhận: {meta.get('ngay_nhan', '')}
- Trích yếu: {meta.get('trich_yeu', '')}

**Nội dung chi tiết văn bản đến (trích xuất từ file đính kèm):**
{attachment_text[:2000] if attachment_text else "(Không có file đính kèm)"}

**Căn cứ pháp lý và văn bản tham chiếu từ hệ thống:**
{rag_context[:2000] if rag_context else "(Không có context)"}

**Thông tin cơ quan ban hành:**
- Tên cơ quan: {ORG_NAME}
- Người ký: {SIGNER_NAME} — {SIGNER_TITLE}
- Ngày: {datetime.now().strftime('%d tháng %m năm %Y')}

Yêu cầu: Soạn nội dung công văn trả lời đầy đủ, chuyên nghiệp, đúng thể thức NĐ 30."""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0.3,
        max_tokens=2000
    )
    return resp.choices[0].message.content


# ── Step 4b: Validate cấu trúc Markdown ───────────────────────────────────────
REQUIRED_SECTIONS = ["CỘNG HÒA", "Kính gửi", "Nơi nhận"]

def validate_draft(md_text: str) -> bool:
    for section in REQUIRED_SECTIONS:
        if section not in md_text:
            print(f"[Validate] Thiếu section: {section}")
            return False
    return True


# ── Step 5: Convert sang DOCX ─────────────────────────────────────────────────
def convert_to_docx(md_text: str, so_den: str) -> Path:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = DRAFTS_DIR / f"{so_den}_draft.md"
    docx_path = DRAFTS_DIR / f"{so_den}_draft.docx"

    md_path.write_text(md_text, encoding="utf-8")

    result = subprocess.run(
        ["python", str(CONVERT_SCRIPT), str(md_path), str(docx_path)],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(f"Convert DOCX thất bại: {result.stderr}")

    md_path.unlink()  # xóa file MD tạm
    return docx_path


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--so-den", required=True, help="Số đến cần dự thảo")
    args = parser.parse_args()
    so_den = args.so_den

    print(f"[F9] Bắt đầu dự thảo cho số đến: {so_den}")

    # Step 1
    meta = get_vb_metadata(so_den)
    print(f"[F9] ✅ Đọc metadata: {meta.get('trich_yeu', '')[:60]}...")

    # Step 2
    attachment_text = extract_attachment_text(so_den)
    print(f"[F9] ✅ Trích xuất attachment: {len(attachment_text)} ký tự")

    # Step 3
    query = f"{meta.get('trich_yeu', '')} {meta.get('so_ky_hieu', '')}"
    rag_context = query_lightrag(query)
    print(f"[F9] ✅ LightRAG context: {len(rag_context)} ký tự")

    # Step 4
    md_text = generate_draft_markdown(meta, attachment_text, rag_context)
    if not validate_draft(md_text):
        # Retry 1 lần nếu validate fail
        print("[F9] ⚠️  Validate fail, retry...")
        md_text = generate_draft_markdown(meta, attachment_text, rag_context)
        if not validate_draft(md_text):
            raise RuntimeError("Dự thảo không đạt cấu trúc tối thiểu sau 2 lần thử")
    print(f"[F9] ✅ Generate dự thảo: {len(md_text)} ký tự")

    # Step 5
    docx_path = convert_to_docx(md_text, so_den)
    print(f"[F9] ✅ DOCX: {docx_path}")

    # Step 6: Output cho Hermes delivery
    preview = "\n".join(md_text.split("\n")[:5])  # 5 dòng đầu làm preview
    print(f"""
📝 DỰ THẢO CÔNG VĂN — Số đến {so_den}
{preview}
...
📎 File: {docx_path}
""")

if __name__ == "__main__":
    main()
```

---

## Phase 3 — Tích hợp Zalo trigger

### Cron job / Hermes handler

```json
// jobs.json — thêm job F9
{
  "id": "f9-draft",
  "name": "Dự thảo công văn trả lời",
  "trigger": "zalo_command",
  "pattern": "^(dự thảo|du thao|draft)\\s+(\\d+)",
  "script": "congchuc/congchuc_draft.py",
  "args": ["--so-den", "$2"],
  "deliver": "zalo"
}
```

### Zalo command flow:

```
User: "dự thảo 2348"
  → Hermes match pattern → chạy congchuc_draft.py --so-den 2348
  → Output gửi Zalo:

📝 DỰ THẢO CÔNG VĂN — Số đến 2348
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập – Tự do – Hạnh phúc
SỞ Y TẾ QUẢNG NINH          Hạ Long, ngày 24 tháng 6 năm 2026
...
📎 Tải file: http://localhost:8642/drafts/2348_draft.docx
```

---

## Cấu hình `.env` bổ sung

```ini
# Thêm vào .env Hermes
LIGHTRAG_API_URL=http://localhost:9621
LIGHTRAG_API_KEY=your-internal-api-key

CONGVAN_DRAFT_MODE=lightrag         # lightrag | static (fallback nếu LightRAG down)
CONGVAN_ORG_NAME=SỞ Y TẾ QUẢNG NINH
CONGVAN_SIGNER_NAME=Nguyễn Văn A
CONGVAN_SIGNER_TITLE=GIÁM ĐỐC
```

---

## Roadmap & Thứ tự triển khai

```
Tuần 1:
  [x] Phase 0: Deploy LightRAG Docker → kiểm tra health + Web UI
  [ ] Phase 1a: Ingest templates NĐ 30 + attachment hiện có
  [ ] Verify query "hybrid" mode trả về kết quả có nghĩa

Tuần 2:
  [ ] Phase 2: Viết congchuc_draft.py
  [ ] Test với 3–5 công văn thực tế đã có
  [ ] Kiểm tra chất lượng DOCX output (font, margin, header 2 cột)

Tuần 3:
  [ ] Phase 3: Tích hợp Zalo trigger
  [ ] Phase 1b: Hook auto-ingest vào F16a
  [ ] Bàn giao người dùng test thực tế
```

---

## Lưu ý kỹ thuật

**Header 2 cột NĐ 30** — Pandoc không tự handle được. `convert_md_to_docx.py` cần xử lý riêng phần này bằng `python-docx` table (2 cột, no border) sau khi convert, không phải trong Markdown.

**Fallback khi LightRAG down** — `CONGVAN_DRAFT_MODE=static` bỏ qua Step 3, LLM chạy với template tĩnh. Chất lượng thấp hơn nhưng không block.

**LLM cho entity extraction** — LightRAG yêu cầu model mạnh để extract knowledge graph. `gpt-4o-mini` là mức tối thiểu chấp nhận được. Nếu muốn tiết kiệm chi phí ingest, dùng `gemini-2.5-flash` qua OpenAI-compatible endpoint.

**Corpus không thay đổi embedding** — Sau khi chọn `text-embedding-3-small`, không được đổi sang model khác trừ khi xóa toàn bộ `rag_storage/` và re-index.
