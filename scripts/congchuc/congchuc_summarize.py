#!/usr/bin/env python3
import os
import sys
import json
import argparse
from openai import OpenAI

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

def summarize(so_den):
    if not os.path.exists(STATE_FILE):
        print(f"Lỗi: Không tìm thấy file state tại {STATE_FILE}.")
        sys.exit(1)
        
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
        
    doc_info = state.get('documents', {}).get(str(so_den))
    if not doc_info:
        print(f"Lỗi: Không tìm thấy văn bản số {so_den} trong hệ thống.")
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
            
    if not att_text.strip():
        print(f"Văn bản #{so_den} hiện chưa được tải file đính kèm về. Vui lòng đợi cronjob tự tải hoặc đây là văn bản không có đính kèm.")
        sys.exit(0)
            
    system_prompt = """Bạn là trợ lý AI chuyên tóm tắt văn bản hành chính.
Nhiệm vụ: Đọc thông tin và nội dung đính kèm của văn bản, sau đó tạo một bản tóm tắt RÕ RÀNG, NGẮN GỌN và ĐẦY ĐỦ THÔNG TIN CỐT LÕI.
Cấu trúc tóm tắt mong muốn:
- 📌 **Mục đích chính**: (1 câu)
- 📝 **Nội dung tóm tắt**: (Các ý chính gạch đầu dòng)
- ⏰ **Thời hạn / Yêu cầu**: (Nếu có)
- 🏢 **Đơn vị phối hợp / thực hiện**: (Nếu có)

Hãy dùng emoji phù hợp để dễ đọc. Văn phong trang trọng nhưng trực diện.
"""

    user_prompt = f"""Thông tin văn bản đến:
- Số đến: {so_den}
- Số ký hiệu: {skh}
- Tác giả: {tac_gia}
- Trích yếu: {trich_yeu}
- Bút phê lãnh đạo: {but_phe}

Nội dung đính kèm:
{att_text[:8000]} # Giới hạn 8000 ký tự đầu để tránh quá tải

Hãy tóm tắt văn bản này.
"""

    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(
        api_key=api_key or "dummy-key",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://host.docker.internal:20128/v1")
    )
    
    try:
        response = client.chat.completions.create(
            model=os.environ.get("HERMES_MODEL", "hermes-combo"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Lỗi khi gọi AI tóm tắt: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--so-den', required=True, help="Số đến của văn bản")
    args = parser.parse_args()
    
    summarize(args.so_den)
