#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
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
DRAFT_DIR = os.path.join(_hermes_home, "cron", "cong-van-den", "drafts")

# xlvp package: mounted at /opt/xlvp inside container
XLVP_PATH = os.environ.get("XLVP_PATH", "/opt/xlvp")
if XLVP_PATH not in sys.path:
    sys.path.insert(0, XLVP_PATH)


def resolve_org_for_unit(unit_id: str) -> tuple[str, str, str]:
    """
    Tra cứu org_parent, org_name và org_code theo unit_id.
    """
    default_parent = os.environ.get("CONGVAN_ORG_PARENT", "ỦY BAN NHÂN DÂN TỈNH QUẢNG NINH")
    default_name = os.environ.get("CONGVAN_ORG_NAME", "SỞ THÔNG TIN VÀ TRUYỀN THÔNG")
    
    # Fallback default code
    default_code = default_name.replace(" ", "")[:5]

    unit_map_raw = os.environ.get("CONGVAN_UNIT_ORG_MAP", "").strip()
    if not unit_map_raw or not unit_id:
        return default_parent, default_name, default_code

    try:
        unit_map = json.loads(unit_map_raw)
        entry = unit_map.get(str(unit_id))
        if entry:
            name = entry.get("org_name", default_name)
            code = entry.get("org_code") or name.replace(" ", "")[:5]
            return (
                entry.get("org_parent", default_parent),
                name,
                code
            )
    except json.JSONDecodeError as e:
        print(f"[WARN] CONGVAN_UNIT_ORG_MAP parse error: {e}", file=sys.stderr)

    return default_parent, default_name, default_code


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
        except:
            return ""
    elif ext == '.pdf':
        try:
            import fitz
            doc = fitz.open(filepath)
            return "".join([page.get_text() for page in doc])
        except:
            return ""
    return ""


def parse_markdown_to_nd30_json(md_path: str) -> dict:
    import re
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter = {}
    body_text = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body_text = parts[2]
            for line in fm_text.splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    frontmatter[k.strip()] = v.strip().strip('"').strip("'")

    data = {
        "co_quan_chu_quan": frontmatter.get("org_parent", ""),
        "co_quan_ban_hanh": frontmatter.get("org_name", ""),
        "so_ky_hieu": frontmatter.get("so_ky_hieu", ""),
        "dia_danh_ngay_thang": frontmatter.get("date", ""),
        "ten_loai_van_ban": frontmatter.get("ten_loai_van_ban", ""),
        "trich_yeu": frontmatter.get("trich_yeu", ""),
        "kinh_gui": "",
        "can_cu": [],
        "noi_dung": [],
        "noi_nhan": [],
        "chuc_danh_nguoi_ky": "",
        "ten_nguoi_ky": ""
    }

    lines = body_text.splitlines()
    in_noi_nhan = False
    in_signature = False
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        if "nơi nhận" in line_str.lower():
            in_noi_nhan = True
            in_signature = False
            continue
            
        if in_noi_nhan:
            # Check transition from Nơi nhận to Signature block
            clean_check = line_str.replace("**", "").replace("*", "").strip().upper()
            is_sig_title = any(title in clean_check for title in ["GIÁM ĐỐC", "PHÓ GIÁM ĐỐC", "TRƯỞNG PHÒNG", "PHÓ TRƯỞNG PHÒNG", "ỦY BAN NHÂN DÂN", "CỤC TRƯỞNG", "VỤ TRƯỞNG"])
            if is_sig_title or (not line_str.startswith('-') and not line_str.startswith('*') and not line_str.startswith('+')):
                in_noi_nhan = False
                in_signature = True
            
        if in_noi_nhan:
            clean_item = re.sub(r'^[-\*\+]\s*', '', line_str).strip()
            data["noi_nhan"].append(clean_item)
            continue
            
        if in_signature:
            if "ký" in line_str.lower() or "kí" in line_str.lower() or line_str.startswith('('):
                continue
            if not data["chuc_danh_nguoi_ky"]:
                data["chuc_danh_nguoi_ky"] = line_str.replace("**", "").replace("*", "").strip()
            else:
                data["ten_nguoi_ky"] = line_str.replace("**", "").replace("*", "").strip()
            continue

        if line_str.lower().startswith("kính gửi:"):
            data["kinh_gui"] = line_str[9:].strip().replace("**", "").replace("*", "")
            continue

        if line_str.lower().startswith("căn cứ"):
            data["can_cu"].append(line_str)
            continue

        dieu_match = re.match(r'^(Điều\s+\d+\.?)\s*(.*)', line_str, re.IGNORECASE)
        if dieu_match:
            tieu_de = dieu_match.group(1)
            noi_dung_txt = dieu_match.group(2)
            data["noi_dung"].append({
                "loai": "dieu",
                "tieu_de": tieu_de,
                "noi_dung": noi_dung_txt
            })
        else:
            data["noi_dung"].append({
                "loai": "doan_van",
                "noi_dung": line_str
            })

    return data


def convert_to_docx_xlvp(md_path: str, docx_path: str) -> bool:
    """
    Chuyển đổi Markdown sang DOCX dùng generate_nd30_docx.js.
    """
    try:
        import subprocess
        json_data = parse_markdown_to_nd30_json(md_path)
        json_path = md_path.replace(".md", "_nd30.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        js_script = "/opt/xlvp/nd30-document-drafter/scripts/generate_nd30_docx.js"
        subprocess.run(["node", js_script, json_path, docx_path], check=True)
        print(f"[nd30-drafter] DOCX generated successfully: {docx_path}")
        return True
    except Exception as e:
        import traceback
        print(f"[nd30-drafter] Conversion failed: {e}", file=sys.stderr)
        traceback.print_exc()
        return False


def convert_to_docx_legacy(md_path: str, docx_path: str) -> bool:
    """
    Fallback: Dùng script convert_md_to_docx.py cũ.
    Trả về True nếu thành công, False nếu thất bại.
    """
    import subprocess

    convert_script = "/opt/hermes/docs/xu-ly-van-phong-v1.0/scripts/convert/convert_md_to_docx.py"
    if not os.path.exists(convert_script):
        convert_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "docs", "xu-ly-van-phong-v1.0", "scripts", "convert", "convert_md_to_docx.py"
        )

    if not os.path.exists(convert_script):
        print(f"[legacy] convert_md_to_docx.py not found at: {convert_script}", file=sys.stderr)
        return False

    python_bin = sys.executable
    if os.path.exists("/opt/hermes/.venv/bin/python"):
        python_bin = "/opt/hermes/.venv/bin/python"

    print(f"[legacy] Converting with script: {convert_script}")
    try:
        subprocess.run([python_bin, convert_script, md_path, docx_path], check=True)
        print(f"[legacy] DOCX generated successfully: {docx_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[legacy] Conversion failed: {e}", file=sys.stderr)
        return False


def generate_draft(so_den, send_zalo=False):
    import datetime
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
    ngay_vb = doc_info.get('ngay_vb', '')
    han_xl = doc_info.get('han_xl', '').strip()

    # Lấy unit_id từ doc_info (field 'unit' do scraper lưu) hoặc fallback về CONGVAN_UNIT
    # CONGVAN_UNIT có thể chứa nhiều unit cách nhau bằng dấu phẩy — lấy unit đầu tiên làm default
    unit_id = str(
        doc_info.get('unit') or
        doc_info.get('unit_id') or
        os.environ.get("CONGVAN_UNIT", "").split(",")[0].strip()
    )
    org_parent, org_name, org_code = resolve_org_for_unit(unit_id)

    print(f"[org] unit_id={unit_id!r} → org_parent={org_parent!r}, org_name={org_name!r}, org_code={org_code!r}")

    # Tính toán ngày ban hành văn bản dự thảo
    # Ưu tiên hạn xử lý (han_xl) trước, định dạng han_xl thường là DD/MM/YYYY
    target_date = None
    if han_xl:
        try:
            target_date = datetime.datetime.strptime(han_xl, "%d/%m/%Y")
        except ValueError:
            pass

    if not target_date:
        target_date = datetime.datetime.now()

    date_str = f"Quảng Ninh, ngày {target_date.day:02d} tháng {target_date.month:02d} năm {target_date.year}"

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

    # Clean trich_yeu to avoid double "V/v" prefixes using regex
    import re
    clean_trich_yeu = re.sub(r'^\s*v/v\s*', '', trich_yeu, flags=re.IGNORECASE).strip()

    # Tự động dựng phần frontmatter đúng chuẩn NĐ 30 bằng code Python
    frontmatter = f"""---
nd30_header: true
org_parent: "{org_parent}"
org_name: "{org_name}"
so_ky_hieu: "Số:      /{org_code}"
date: "{date_str}"
trich_yeu: "V/v {clean_trich_yeu}"
---"""

    system_prompt = f"""Bạn là trợ lý ảo hỗ trợ soạn thảo văn bản hành chính nhà nước.
Nhiệm vụ: Dựa vào thông tin văn bản đến, bút phê của lãnh đạo, nội dung đính kèm, và KIẾN THỨC NỀN từ LightRAG, hãy soạn một dự thảo văn bản trả lời/xử lý.

QUY TẮC BẮT BUỘC:
1. Bạn chỉ được viết nội dung văn bản bắt đầu bằng "Kính gửi: ...". 
2. Tuyệt đối KHÔNG viết phần tiêu đề, frontmatter, và KHÔNG viết lại dòng trích yếu bắt đầu bằng "V/v..." hay "**V/v...**" ở phần đầu văn bản (vì phần này sẽ được hệ thống tự ghép tự động).
3. Bạn PHẢI sử dụng chính xác tên đơn vị soạn thảo là "{org_name}" (ví dụ: Bệnh viện Sản Nhi Quảng Ninh) và cơ quan chủ quản là "{org_parent}" (nếu có nhắc đến). Tuyệt đối không tự ý viết các tên đơn vị khác (như Bệnh viện Đa khoa tỉnh) vào nội dung.
4. Nội dung văn bản chia thành các đoạn, có thể dùng số thứ tự (ví dụ: 1., 2., a), b)). 
   - Tuyệt đối KHÔNG bao quanh các số thứ tự này bằng dấu in đậm `**` hay in nghiêng `*` (ví dụ: viết "1. Tên mục" chứ KHÔNG viết "**1. Tên mục**" hay "**1.**").
   - Tuyệt đối KHÔNG đặt dấu gạch đầu dòng `-` hoặc `*` trước số thứ tự (ví dụ: KHÔNG viết "- 1." hay "- *1.").
5. Dùng từ ngữ trang trọng, đúng văn phong hành chính.
6. Ở CUỐI văn bản, bắt buộc phải có phần Nơi nhận và chức danh ký tên.
   Định dạng khối cuối văn bản BẮT BUỘC như sau (không được sai lệch):
   
   **Nơi nhận:**
   - Như trên;
   - Lưu: VT, {org_code.split('-')[-1]}.

   **GIÁM ĐỐC**
   *(Ký, ghi rõ họ tên)*

7. QUY TẮC TRÍCH DẪN VĂN BẢN ĐẾN:
- Khi viết phần viện dẫn mở đầu, bạn PHẢI sử dụng chính xác thông tin ngày của văn bản đến (ví dụ: "Thực hiện Công văn số {skh} ngày {ngay_vb} của {tac_gia}..."). Không được để trống ngày tháng năm ở chỗ này.

KIẾN THỨC TỪ HỆ THỐNG (LIGHTRAG):
{context_text}
"""

    user_prompt = f"""Thông tin văn bản đến:
- Số đến: {so_den}
- Số ký hiệu: {skh}
- Tác giả: {tac_gia}
- Ngày văn bản: {ngay_vb}
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

    llm_body = response.choices[0].message.content.strip()
    
    # Programmatic cleanup: remove markdown bullet indicators (- or *) if they prefix numbered list items
    # e.g., "- 1. " -> "1. ", "* a) " -> "a) "
    cleaned_lines = []
    for line in llm_body.splitlines():
        # Match leading dash/asterisk followed by number+dot or char+parenthesis
        cleaned_line = re.sub(r'^\s*[-\*]\s*(\d+\.|\w+\))', r'\1', line)
        cleaned_lines.append(cleaned_line)
    llm_body = "\n".join(cleaned_lines)
    
    # Auto-append Nơi nhận and Signer block if LLM misses them
    # This guarantees they always exist for the xlvp converter to build the footer table
    if "nơi nhận" not in llm_body.lower():
        # Clean formatting to ensure xlvp parser detects it correctly
        dept_code = org_code.split('-')[-1] if '-' in org_code else "VP"
        llm_body += f"\n\n**Nơi nhận:**\n- Như trên;\n- Lưu: VT, {dept_code}."
        
    if "giám đốc" not in llm_body.lower() and "kí" not in llm_body.lower():
        llm_body += f"\n\n**GIÁM ĐỐC**\n*(Ký, ghi rõ họ tên)*"
    
    # Ghép frontmatter của Python và body của LLM thành file Markdown hoàn chỉnh
    md_content = f"{frontmatter}\n\n{llm_body}"

    # Save markdown draft
    out_dir = os.path.join(DRAFT_DIR, str(so_den))
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, "draft.md")
    docx_path = os.path.join(out_dir, "draft_v4.docx")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    # Convert to DOCX: try xlvp first, fallback to legacy
    print("Converting to DOCX...")
    xlvp_ok = convert_to_docx_xlvp(md_path, docx_path)
    if not xlvp_ok:
        legacy_ok = convert_to_docx_legacy(md_path, docx_path)
        if not legacy_ok:
            print("[ERROR] Both xlvp and legacy converters failed. DOCX not generated.", file=sys.stderr)
            sys.exit(1)

    print(f"Draft generated successfully: {docx_path}")

    # Phase 3: Send via Zalo Plugin (if requested)
    if send_zalo:
        chat_id = os.environ.get("CONGVAN_ZALO_CHAT_ID", "2825656851207986406")
        bridge_url = os.environ.get("ZALO_PLUGIN_URL", "http://host.docker.internal:8787")
        api_url = f"{bridge_url}/send-attachment"

        # Translate path to Windows Host path
        win_path = docx_path
        host_hermes_home = os.environ.get("ZALO_HOST_HERMES_HOME", "").strip()
        if not host_hermes_home:
            host_hermes_home = r"C:\Users\Desktop\.hermes"
        host_hermes_home = host_hermes_home.replace("/", "\\").rstrip("\\")

        if docx_path.startswith("/opt/data/"):
            win_path = docx_path.replace("/opt/data/", host_hermes_home + "\\").replace("/", "\\")
        elif docx_path.startswith("/root/.hermes/"):
            win_path = docx_path.replace("/root/.hermes/", host_hermes_home + "\\").replace("/", "\\")
        elif _hermes_home and docx_path.startswith(_hermes_home):
            win_path = docx_path.replace(_hermes_home, host_hermes_home).replace("/", "\\")

        if win_path.startswith("\\\\"):
            win_path = "\\\\" + win_path[2:].replace("\\\\", "\\")
        else:
            win_path = win_path.replace("\\\\", "\\")

        print(f"Sending to Zalo chat_id: {chat_id} via API: {api_url} using Path: {win_path}")
        try:
            payload = {
                "threadId": chat_id,
                "threadType": "user",
                "path": win_path,
                "caption": f"Gửi dự thảo Word cho VB #{so_den}"
            }
            data_payload = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                api_url, data=data_payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                print(f"Zalo Plugin Response: {result}")
        except Exception as e:
            print(f"Failed to send to Zalo: {e}")

    return docx_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--so-den', required=True, help="Số đến của văn bản")
    parser.add_argument('--chat-id', help="Zalo Chat ID to send the file to")
    parser.add_argument('--zalo', action='store_true', help="Tự động gửi file dự thảo qua Zalo sau khi tạo xong")
    args = parser.parse_args()

    if args.chat_id:
        os.environ["CONGVAN_ZALO_CHAT_ID"] = args.chat_id

    generate_draft(args.so_den, send_zalo=args.zalo)
