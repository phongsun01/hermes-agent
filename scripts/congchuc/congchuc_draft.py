#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import argparse
from openai import OpenAI
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

_hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
_env_path = os.path.join(_hermes_home, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

STATE_FILE = os.path.join(_hermes_home, "cron", "cong-van-den", "vbden_state.json")
STATE_DIR = os.path.join(_hermes_home, "cron", "cong-van-den")
DRAFT_DIR = os.path.join(_hermes_home, "cron", "cong-van-den", "drafts")

def query_lightrag(prompt, api_url):
    endpoint = f"{api_url}/query"
    payload = json.dumps({"query": prompt, "mode": "hybrid"}).encode('utf-8')
    req = urllib.request.Request(endpoint, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except Exception as e:
        print(f"Error querying LightRAG: {e}")
        return None

def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.md', '.txt']:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == '.docx':
        try:
            import docx
            doc = docx.Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        except: return ""
    elif ext == '.pdf':
        try:
            import fitz
            doc = fitz.open(filepath)
            return "".join([page.get_text() for page in doc])
        except: return ""
    return ""

def generate_draft(so_den):
    if not os.path.exists(STATE_FILE):
        print(f"State file {STATE_FILE} not found.")
        sys.exit(1)
        
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
        
    doc_info = state.get('documents', {}).get(str(so_den))
    if not doc_info:
        print(f"Document {so_den} not found in state.")
        sys.exit(1)
        
    trich_yeu = doc_info.get('trich_yeu', '')
    tac_gia = doc_info.get('tac_gia', '')
    skh = doc_info.get('so_ky_hieu', '')
    but_phe = doc_info.get('but_phe', '')
    
    # Extract attachments
    att_text = ""
    attachments = doc_info.get('attachments', [])
    for att in attachments:
        att_path = os.path.join(STATE_DIR, att.get('path', ''))
        if os.path.exists(att_path):
            att_text += f"\n--- NỘI DUNG FILE {att.get('filename')} ---\n"
            att_text += extract_text_from_file(att_path)
            
    # Query LightRAG
    lightrag_url = os.environ.get("LIGHTRAG_API_URL", "http://host.docker.internal:9621")
    lr_query = f"Hướng dẫn xử lý, quy định liên quan đến loại văn bản: {trich_yeu}"
    print(f"Querying LightRAG: {lr_query}")
    lr_context = query_lightrag(lr_query, lightrag_url)
    context_text = lr_context if lr_context else "Không tìm thấy kiến thức liên quan."
    
    org_parent = os.environ.get("CONGVAN_ORG_PARENT", "ỦY BAN NHÂN DÂN TỈNH QUẢNG NINH")
    org_name = os.environ.get("CONGVAN_ORG_NAME", "SỞ THÔNG TIN VÀ TRUYỀN THÔNG")
    
    system_prompt = f"""Bạn là trợ lý ảo hỗ trợ soạn thảo văn bản hành chính nhà nước.
Nhiệm vụ: Dựa vào thông tin văn bản đến, bút phê của lãnh đạo, nội dung đính kèm, và KIẾN THỨC NỀN từ LightRAG, hãy soạn một dự thảo văn bản trả lời/xử lý.

QUY TẮC BẮT BUỘC:
1. Bạn PHẢI xuất ra định dạng Markdown có YAML frontmatter ở trên cùng để script chuyển đổi DOCX nhận diện Header NĐ 30.
2. Cấu trúc frontmatter bắt buộc:
---
nd30_header: true
org_parent: "{org_parent}"
org_name: "{org_name}"
so_ky_hieu: "Số:      /{org_name.replace(' ', '')[:5]}-VP"
date: "Quảng Ninh, ngày      tháng      năm 202..."
---

3. Dưới phần frontmatter là nội dung văn bản:
- Bắt đầu bằng Kính gửi: (Tên cơ quan, cá nhân nhận văn bản).
- Nội dung văn bản chia thành các đoạn, có thể dùng heading (ví dụ **1.**, **2.**).
- Dùng từ ngữ trang trọng, đúng văn phong hành chính.
- Ký tên ở cuối (ví dụ: GIÁM ĐỐC).

KIẾN THỨC TỪ HỆ THỐNG (LIGHTRAG):
{context_text}
"""

    user_prompt = f"""Thông tin văn bản đến:
- Số đến: {so_den}
- Số ký hiệu: {skh}
- Tác giả: {tac_gia}
- Trích yếu: {trich_yeu}
- Bút phê lãnh đạo: {but_phe}

Nội dung đính kèm:
{att_text[:5000]} # Giới hạn 5000 ký tự đầu

Hãy soạn dự thảo văn bản phản hồi/xử lý ngay bây giờ."""

    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(
        api_key=api_key or "dummy-key",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://host.docker.internal:20128/v1")
    )
    
    print("Generating draft with LLM...")
    response = client.chat.completions.create(
        model=os.environ.get("HERMES_MODEL", "hermes-combo"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )
    
    md_content = response.choices[0].message.content
    
    # Save files
    out_dir = os.path.join(DRAFT_DIR, str(so_den))
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, "draft.md")
    docx_path = os.path.join(out_dir, "draft.docx")
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    # Call convert script
    convert_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "xu-ly-van-phong-v1.0", "scripts", "convert", "convert_md_to_docx.py")
    print(f"Converting to DOCX: {convert_script}")
    
    python_bin = sys.executable
    if os.path.exists("/opt/hermes/.venv/bin/python"):
        python_bin = "/opt/hermes/.venv/bin/python"
    
    subprocess.run([python_bin, convert_script, md_path, docx_path], check=True)
    
    print(f"Draft generated successfully: {docx_path}")
    
    # Phase 3: Send via Zalo Plugin
    chat_id = os.environ.get("CONGVAN_ZALO_CHAT_ID", "2825656851207986406")
    api_url = os.environ.get("CONGVAN_ZALO_API_URL", "http://localhost:8787/send-attachment")
    print(f"Sending to Zalo chat_id: {chat_id} via API: {api_url}")
    try:
        # Use curl to send multipart/form-data
        curl_cmd = [
            "curl", "-s", "-X", "POST",
            api_url,
            "-F", f"file=@{docx_path}",
            "-F", f"chat_id={chat_id}"
        ]
        res = subprocess.run(curl_cmd, capture_output=True, text=True)
        print(f"Zalo Plugin Response: {res.stdout}")
    except Exception as e:
        print(f"Failed to send to Zalo: {e}")
        
    return docx_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--so-den', required=True, help="Số đến của văn bản")
    parser.add_argument('--chat-id', help="Zalo Chat ID to send the file to")
    args = parser.parse_args()
    
    if args.chat_id:
        os.environ["CONGVAN_ZALO_CHAT_ID"] = args.chat_id
        
    generate_draft(args.so_den)
