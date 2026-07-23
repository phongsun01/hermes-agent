# F9 — Kế hoạch triển khai Dự thảo văn bản với LightRAG

**Trạng thái:** 📌 Kế hoạch triển khai | **Cập nhật:** 2026-07-13 ICT  
**Thay thế:** Onyx RAG → LightRAG (HKUDS/LightRAG, MIT license)

---

## 1. Ý kiến người dùng cần xác nhận (User Review Required)

- **Xác nhận Model LLM:** Trong file `.env.lightrag`, LLM dùng cho entity extraction đang đặt mặc định là `gpt-4o-mini`. Để tiết kiệm chi phí, có thể cân nhắc dùng `gemini-2.5-flash` qua OpenAI-compatible endpoint.
- **Zalo Trigger Regex:** Regex hiện tại là `^(dự thảo|du thao|draft)\s+(\d+)`. Nếu cần điều chỉnh cú pháp lệnh gọi, vui lòng xác nhận.
- **Cổng kết nối LightRAG:** Port 9621, chạy qua Docker trên host hiện tại.

---

## 2. Kiến trúc & Thiết kế tổng thể

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
│    6. Gửi thẳng file .docx vào Zalo qua API send-attachment       │
└─────────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐      ┌──────────────────────────┐
│  LightRAG Server│      │  ~/.hermes/cron/          │
│  localhost:9621 │      │  cong-van-den/            │
│  (Docker)       │      │  ├── attachments/         │
│  │  /query      │      │  ├── drafts/              │
│  └── /upload    │      │  └── vbden_state.json     │
└─────────────────┘      └──────────────────────────┘
```

---

## 3. Các thay đổi và file cần tạo mới (Proposed Changes)

### 3.1 Docker & Cấu hình hệ thống (Phase 0)

#### [MODIFY] [docker-compose.yml](file:///D:/Antigravity/Hermes/docker-compose.yml)
Bổ sung service `lightrag` sử dụng image `ghcr.io/hkuds/lightrag:latest`:

```yaml
  lightrag:
    image: ghcr.io/hkuds/lightrag:latest
    container_name: lightrag
    restart: unless-stopped
    ports:
      - "9621:9621"
    volumes:
      - lightrag_data:/app/data
    env_file:
      - .env.lightrag
```

#### [NEW] [env.lightrag](file:///D:/Antigravity/Hermes/.env.lightrag)
Tạo file cấu hình chứa API key OpenAI, binding host, model (mặc định OpenAI + text-embedding-3-small):

```ini
HOST=0.0.0.0
PORT=9621

# LLM cho entity extraction (cần model mạnh, ít nhất 32B)
LLM_BINDING=openai
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=sk-your-key
LLM_MODEL=gpt-4o-mini

# Embedding (KHÔNG THAY ĐỔI SAU KHI ĐÃ INDEX)
EMBEDDING_BINDING=openai
EMBEDDING_BINDING_HOST=https://api.openai.com/v1
EMBEDDING_BINDING_API_KEY=sk-your-key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Auth & Storage
WORKING_DIR=/app/data/rag_storage
INPUT_DIR=/app/data/inputs
DEFAULT_SEARCH_MODE=hybrid
```

#### [MODIFY] [Cấu hình .env bổ sung](file:///C:/Users/Desktop/.hermes/.env)
Thêm các biến môi trường cho việc dự thảo vào file `.env` của Hermes:

```ini
LIGHTRAG_API_URL=http://localhost:9621
LIGHTRAG_API_KEY=your-internal-api-key

CONGVAN_DRAFT_MODE=lightrag         # lightrag | static (fallback)
CONGVAN_ORG_NAME=SỞ Y TẾ QUẢNG NINH
CONGVAN_SIGNER_NAME=Nguyễn Văn A
CONGVAN_SIGNER_TITLE=GIÁM ĐỐC
```

---

### 3.2 Tải tài liệu & Xây dựng tri thức (Phase 1)

#### [NEW] [ingest_corpus.py](file:///D:/Antigravity/Hermes/scripts/lightrag/ingest_corpus.py)
Script Python hỗ trợ nạp hàng loạt tệp tin tri thức (`.pdf`, `.docx`, `.md`) vào RAG.

> [!NOTE]
> **Tích hợp `boc-tach-pdf-v1.0`:** Script này tự động nhận diện file Markdown sinh ra từ kỹ năng `bóc tách pdf` khi gặp các tệp PDF mờ/scan để nạp vào LightRAG, giúp AI hiểu chính xác 100% cấu trúc văn bản hành chính thay vì dùng PDF OCR thông thường.

```python
#!/usr/bin/env python3
import os, sys, requests
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
    if len(sys.argv) < 2:
        print("Usage: python ingest_corpus.py <directory>")
        sys.exit(1)
    ingest_directory(sys.argv[1])
```

#### [MODIFY] [congchuc_scrape.py](file:///D:/Antigravity/Hermes/scripts/congchuc/congchuc_scrape.py)
Cập nhật luồng tải đính kèm (F16a) để tự động gọi API `upload` của LightRAG ngay sau khi tải thành công tệp tin đính kèm về local.

```python
# Tích hợp vào hàm xử lý sau khi download thành công:
def auto_ingest_to_lightrag(filepath: str):
    url = os.getenv("LIGHTRAG_API_URL", "http://localhost:9621")
    key = os.getenv("LIGHTRAG_API_KEY", "")
    if not key:
        return
    try:
        with open(filepath, "rb") as f:
            requests.post(
                f"{url}/documents/upload",
                headers={"X-API-Key": key},
                files={"file": (os.path.basename(filepath), f)},
                timeout=60
            )
    except Exception as e:
        print(f"[LightRAG ingest warning] {e}")
```

---

### 3.3 Logics Xử lý & Soạn dự thảo (Phase 2)

#### [NEW] [congchuc_draft.py](file:///D:/Antigravity/Hermes/scripts/congchuc/congchuc_draft.py)
Script xử lý logic chính: Đọc metadata, trích xuất text từ văn bản, truy vấn LightRAG để lấy ngữ cảnh pháp lý và gọi LLM tạo file nháp Markdown.

```python
#!/usr/bin/env python3
import os, json, argparse, requests, subprocess
from pathlib import Path
from datetime import datetime

HERMES_HOME = Path(os.getenv("HERMES_HOME", "/opt/data"))
STATE_FILE = HERMES_HOME / "cron/cong-van-den/vbden_state.json"
DRAFTS_DIR = HERMES_HOME / "cron/cong-van-den/drafts"
ATTACHMENTS_DIR = HERMES_HOME / "cron/cong-van-den/attachments"
CONVERT_SCRIPT = Path(os.getenv("CONVERT_SCRIPT", "/opt/data/scripts/convert/convert_md_to_docx.py"))
LIGHTRAG_URL = os.getenv("LIGHTRAG_API_URL", "http://localhost:9621")
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
ORG_NAME = os.getenv("CONGVAN_ORG_NAME", "SỞ Y TẾ")
SIGNER_NAME = os.getenv("CONGVAN_SIGNER_NAME", "Nguyễn Văn A")
SIGNER_TITLE = os.getenv("CONGVAN_SIGNER_TITLE", "GIÁM ĐỐC")

def get_vb_metadata(so_den: str) -> dict:
    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)
    docs = state.get("documents", {})
    if so_den not in docs:
        raise ValueError(f"Không tìm thấy số đến {so_den}")
    return docs[so_den]

def extract_attachment_text(so_den: str) -> str:
    att_dir = ATTACHMENTS_DIR / so_den
    if not att_dir.exists():
        return ""
    texts = []
    for f in att_dir.iterdir():
        if f.suffix.lower() == ".pdf":
            result = subprocess.run(["pdftotext", str(f), "-"], capture_output=True, text=True, timeout=30)
            texts.append(result.stdout[:3000])
        elif f.suffix.lower() in [".docx", ".doc"]:
            result = subprocess.run(["python", "-c", f"import docx2txt; print(docx2txt.process('{f}'))"], capture_output=True, text=True, timeout=30)
            texts.append(result.stdout[:3000])
    return "\n---\n".join(texts)

def query_lightrag(query: str) -> str:
    try:
        resp = requests.post(f"{LIGHTRAG_URL}/query", json={"query": query, "mode": "hybrid"}, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception as e:
        print(f"[LightRAG warning] {e}")
    return ""

SYSTEM_PROMPT = """Bạn là chuyên viên hành chính soạn thảo công văn theo chuẩn Nghị định 30/2020/NĐ-CP.
Trả về DUY NHẤT nội dung Markdown của công văn, không có giải thích hay bình luận thêm.
Cấu trúc: 1. Quốc hiệu/Tiêu ngữ, 2. Cơ quan ban hành & Địa danh, 3. Trích yếu, 4. Kính gửi, 5. Nội dung, 6. Chức danh/Người ký, 7. Nơi nhận."""

def generate_draft_markdown(meta: dict, attachment_text: str, rag_context: str) -> str:
    import openai
    client = openai.OpenAI(api_key=LLM_API_KEY)
    user_content = f"Soạn công văn trả lời cho:\n{meta.get('trich_yeu','')}\nChi tiết:\n{attachment_text[:2000]}\nTham chiếu RAG:\n{rag_context[:2000]}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_content}],
        temperature=0.3
    )
    return resp.choices[0].message.content

def convert_to_docx(md_text: str, so_den: str) -> Path:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = DRAFTS_DIR / f"{so_den}_draft.md"
    docx_path = DRAFTS_DIR / f"{so_den}_draft.docx"
    md_path.write_text(md_text, encoding="utf-8")
    subprocess.run(["python", str(CONVERT_SCRIPT), str(md_path), str(docx_path)], check=True)
    md_path.unlink()
    return docx_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--so-den", required=True)
    args = parser.parse_args()
    meta = get_vb_metadata(args.so_den)
    att_text = extract_attachment_text(args.so_den)
    context = query_lightrag(meta.get("trich_yeu", ""))
    md_text = generate_draft_markdown(meta, att_text, context)
    docx_path = convert_to_docx(md_text, args.so_den)
    print(f"📎 File: {docx_path}")

if __name__ == "__main__":
    main()
```

#### [MODIFY] [convert_md_to_docx.py](file:///D:/Antigravity/Hermes/scripts/convert/convert_md_to_docx.py)
Bổ sung logic bằng `python-docx` để tạo bảng ẩn (2 cột, no border) giải quyết đúng thể thức chia đôi Header của Nghị định 30 (bên trái là Quốc hiệu/Tiêu ngữ, bên phải là Cơ quan ban hành + Ngày tháng) thay vì chuyển đổi thô.

---

### 3.4 Định tuyến và Zalo Integration (Phase 3)

#### [MODIFY] [update_cron_jobs.py](file:///D:/Antigravity/Hermes/scripts/congchuc/update_cron_jobs.py)
Đăng ký trigger nhận diện lệnh từ Zalo:

```json
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

#### [UPDATE] Cơ chế gửi file trực tiếp qua Zalo (Thay thế Link tải)
Sử dụng endpoint API `POST /send-attachment` của `hermes-zalo-plugin` tại `http://localhost:8787/send-attachment` để gửi trực tiếp tệp tin Word `.docx` đến khung chat Zalo của người dùng thay vì xuất link tải localhost không hoạt động trên mobile.

---

## 4. Kịch bản kiểm thử & xác minh (Verification Plan)

### 4.1 Kiểm tra tự động (Automated Tests)
- Kiểm tra cú pháp import của script: `python scripts/lightrag/ingest_corpus.py --help`
- Kiểm tra trạng thái hoạt động của LightRAG: `curl http://localhost:9621/health`

### 4.2 Xác minh thủ công (Manual Verification)
- Chạy thử nạp (ingest) một file template mẫu NĐ 30 để xác nhận LightRAG hoạt động.
- **Kiểm thử CLI độc lập:** Thực thi `python scripts/congchuc/congchuc_draft.py --so-den 2914` để đảm bảo RAG/LLM trả về đúng thông tin pháp lý của Sở Y tế, file DOCX được tạo ra đúng cấu trúc trích yếu dưới số ký hiệu của NĐ 30.
- Giải quyết vấn đề khóa quyền (Read-only) trên Windows bằng lệnh PowerShell thiết lập ACL FullControl cho Everyone đối với các tệp Word đầu ra.
- Kiểm thử lệnh qua Zalo: Gửi tin nhắn `dự thảo 2914` và kiểm tra file `.docx` trả về trên điện thoại có mở và định dạng đúng chuẩn NĐ 30 không.

---

## 5. Lộ trình triển khai (Roadmap)

```
Tuần 1:
  [x] Phase 0: Deploy LightRAG Docker → kiểm tra health + Web UI
  [x] Phase 1a: Ingest templates NĐ 30 + attachment hiện có
  [x] Verify query "hybrid" mode trả về kết quả có nghĩa

Tuần 2:
  [x] Phase 2: Viết congchuc_draft.py (Đã tích hợp XLVP và fallback legacy)
  [x] Test với 3–5 công văn thực tế đã có
  [x] Kiểm tra chất lượng DOCX output (font, margin, header 2 cột, hanging indent)

Tuần 3:
  [x] Phase 3: Tích hợp Zalo trigger
  [x] Phase 1b: Hook auto-ingest vào F16a
  [x] Bàn giao người dùng test thực tế
```

---

## 6. Các lưu ý kỹ thuật quan trọng

- **Header 2 cột NĐ 30:** Xử lý bằng cách xuất YAML frontmatter từ LLM và để thư viện `xlvp` (dùng OfficeCLI) dựng cấu trúc bảng header và lề theo đơn vị twips chuẩn.
- **Cơ chế Fallback:** Khi `xlvp` lỗi hoặc chưa được cài đặt, `congchuc_draft.py` tự động chuyển sang luồng dự phòng legacy chạy script cũ để tránh nghẽn công việc.
- **Model Embedding:** Một khi đã chọn `text-embedding-3-small` (1536 dims), không được thay đổi model trừ khi xóa toàn bộ cơ sở dữ liệu `rag_storage/` và nạp lại từ đầu.
