import os
import sys
import json
import argparse
import urllib.request
import re
from openai import OpenAI

# Paths
_hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
STATE_DIR = os.path.join(_hermes_home, "cron", "cong-van-den")
STATE_FILE = os.path.join(STATE_DIR, "vbden_state.json")
DRAFT_DIR = os.path.join(STATE_DIR, "drafts")

def extract_docx_to_json(input_docx, output_json):
    """Gọi Node.js script để trích xuất text từ file docx"""
    js_script = "/opt/xlvp/nd30-sualoi/scripts/extract_docx.js"
    import subprocess
    print(f"Running extract_docx.js on {input_docx}...")
    subprocess.run(["node", js_script, input_docx, output_json], check=True)

def generate_edited_docx(json_data_path, output_docx):
    """Gọi Node.js script để sinh file docx tô màu đỏ các phần chỉnh sửa"""
    js_script = "/opt/xlvp/nd30-sualoi/scripts/generate_nd30_editor.js"
    import subprocess
    print(f"Running generate_nd30_editor.js to generate {output_docx}...")
    subprocess.run(["node", js_script, json_data_path, output_docx], check=True)

def query_llm_for_editing(extracted_data):
    """Đưa nội dung cho LLM để soát lỗi chính tả (Standard) và tối ưu hóa văn phong (Optimized)"""
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(
        api_key=api_key or "dummy-key",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://host.docker.internal:20128/v1")
    )

    system_prompt = """Bạn là trợ lý ảo chuyên soát lỗi chính tả và hiệu đính văn bản hành chính Việt Nam theo Nghị định 30/2020/NĐ-CP.
Nhiệm vụ của bạn là nhận danh sách các đoạn văn bản trích xuất từ file Word gốc, sau đó trả về cấu trúc JSON chứa 02 phiên bản:
1. "standard": Bản Chuẩn hóa. Giữ nguyên câu từ gốc. Chỉ sửa lỗi chính tả, lỗi gõ phím, dính chữ. 
   Đặc biệt: Những từ/cụm từ được sửa lỗi chính tả phải được bọc trong cấu trúc segment: [{"text": "từ đã sửa", "is_edited": true}]. Phần còn lại không sửa giữ nguyên là {"text": "...", "is_edited": false} hoặc string thường.
2. "optimized": Bản Tối ưu. Sửa lỗi chính tả + nâng cấp câu chữ sang văn phong hành chính pháp lý chuẩn mực, chuyên nghiệp.
   Đặc biệt: Cả câu hoặc đoạn từ được viết lại/tối ưu phải được đánh dấu "is_edited": true để hệ thống bôi đỏ nổi bật giúp sếp dễ đối chiếu.

Định dạng JSON đầu ra bắt buộc khớp chính xác cấu trúc sau:
{
  "standard": {
    "co_quan_chu_quan": "Tên cơ quan chủ quản (nếu có, ví dụ: SỞ Y TẾ)",
    "co_quan_ban_hanh": "Tên cơ quan ban hành (ví dụ: BỆNH VIỆN SẢN NHI)",
    "so_ky_hieu": "Số:.../...",
    "dia_danh_ngay_thang": "Địa danh, ngày... tháng... năm...",
    "ten_loai_van_ban": "Tên loại văn bản (ví dụ: QUYẾT ĐỊNH, CÔNG VĂN thì để trống)",
    "trich_yeu": "Về việc... (hoặc có thể là array segment nếu bị sửa)",
    "kinh_gui": "Kính gửi (nếu có)",
    "can_cu": [
       "Căn cứ..." (mỗi căn cứ là một string, hoặc array segment nếu bị sửa chính tả)
    ],
    "noi_dung": [
       { "loai": "doan_van", "noi_dung": "nội dung đoạn..." },
       { "loai": "dieu", "tieu_de": "Điều 1.", "noi_dung": "nội dung điều..." }
    ],
    "noi_nhan": [
       "Như Điều 3",
       "Lưu VT"
    ],
    "chuc_danh_nguoi_ky": "GIÁM ĐỐC",
    "ten_nguoi_ky": "Tên người ký"
  },
  "optimized": {
    "co_quan_chu_quan": "Tên cơ quan chủ quản",
    "co_quan_ban_hanh": "Tên cơ quan ban hành",
    "so_ky_hieu": "Số:.../...",
    "dia_danh_ngay_thang": "Địa danh, ngày...",
    "ten_loai_van_ban": "Tên loại văn bản",
    "trich_yeu": "Về việc...",
    "kinh_gui": "Kính gửi",
    "can_cu": [
       "Căn cứ..."
    ],
    "noi_dung": [
       { "loai": "doan_van", "noi_dung": "nội dung đoạn..." },
       { "loai": "dieu", "tieu_de": "Điều 1.", "noi_dung": "nội dung điều..." }
    ],
    "noi_nhan": [
       "Như Điều 3",
       "Lưu VT"
    ],
    "chuc_danh_nguoi_ky": "GIÁM ĐỐC",
    "ten_nguoi_ky": "Tên người ký"
  }
}

Chú ý: Trả về duy nhất JSON hợp lệ, không bọc trong tag ```json hay các ký tự markdown khác.
"""

    user_prompt = f"Dưới đây là các đoạn văn bản trích xuất được từ văn bản gốc:\n{json.dumps(extracted_data, ensure_ascii=False, indent=2)}"

    print("Sending text to LLM for spelling check and optimization...")
    response = client.chat.completions.create(
        model=os.environ.get("HERMES_MODEL", "hermes-combo"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    result_text = response.choices[0].message.content.strip()
    if result_text.startswith("```"):
        result_text = re.sub(r'^```[a-zA-Z]*\n', '', result_text)
        result_text = re.sub(r'\n```$', '', result_text)
    
    return json.loads(result_text.strip())

def send_to_zalo(docx_path, chat_id, caption):
    """Gửi file Word đính kèm sang Zalo Plugin"""
    bridge_url = os.environ.get("ZALO_PLUGIN_URL", "http://host.docker.internal:8787")
    api_url = f"{bridge_url}/send-attachment"

    host_hermes_home = os.environ.get("ZALO_HOST_HERMES_HOME", "").strip()
    if not host_hermes_home:
        host_hermes_home = r"C:\Users\Desktop\.hermes"
    host_hermes_home = host_hermes_home.replace("/", "\\").rstrip("\\")

    win_path = docx_path
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

    print(f"Sending file to Zalo chat_id: {chat_id} via API: {api_url} using Path: {win_path}")
    try:
        payload = {
            "threadId": chat_id,
            "threadType": "user",
            "path": win_path,
            "caption": caption
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
        print(f"Failed to send to Zalo: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--so-den', help="Số đến của văn bản cần hiệu đính từ state")
    parser.add_argument('--file-path', help="Đường dẫn file Word cần soát lỗi")
    parser.add_argument('--chat-id', help="Zalo Chat ID to send the files to")
    parser.add_argument('--zalo', action='store_true', help="Tự động gửi file Word kết quả qua Zalo")
    args = parser.parse_args()

    input_docx = None

    if args.so_den:
        if not os.path.exists(STATE_FILE):
            print(f"State file {STATE_FILE} not found.")
            sys.exit(1)
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        doc_info = state.get('documents', {}).get(str(args.so_den))
        if not doc_info:
            print(f"Document {args.so_den} not found in state.")
            sys.exit(1)
        attachments = doc_info.get('attachments', [])
        if not attachments:
            print(f"Document {args.so_den} has no attachments to edit.")
            sys.exit(1)
        input_docx = os.path.join(STATE_DIR, attachments[0].get('path', ''))
    elif args.file_path:
        input_docx = args.file_path
    else:
        print("Error: Yêu cầu cung cấp --so-den hoặc --file-path.")
        sys.exit(1)

    if not input_docx or not os.path.exists(input_docx):
        print(f"Error: Không tìm thấy file Word đầu vào '{input_docx}'.")
        sys.exit(1)

    temp_json = "/tmp/temp_extracted.json"
    extract_docx_to_json(input_docx, temp_json)

    with open(temp_json, 'r', encoding='utf-8') as f:
        extracted_data = json.load(f)

    edited_data = query_llm_for_editing(extracted_data)

    standard_json_path = "/tmp/data_standard.json"
    optimized_json_path = "/tmp/data_optimized.json"

    with open(standard_json_path, 'w', encoding='utf-8') as f:
        json.dump(edited_data["standard"], f, ensure_ascii=False, indent=2)

    with open(optimized_json_path, 'w', encoding='utf-8') as f:
        json.dump(edited_data["optimized"], f, ensure_ascii=False, indent=2)

    base_name = os.path.splitext(os.path.basename(input_docx))[0]
    out_dir = os.path.dirname(input_docx) if os.path.dirname(input_docx) else "."
    
    standard_docx = os.path.join(out_dir, f"{base_name}_Ban_Chuan_Hoa.docx")
    optimized_docx = os.path.join(out_dir, f"{base_name}_Ban_Toi_Uu.docx")

    generate_edited_docx(standard_json_path, standard_docx)
    generate_edited_docx(optimized_json_path, optimized_docx)

    print(f"\n✅ Đã tạo 2 bản hiệu đính đối chiếu thành công:")
    print(f"   - Bản Chuẩn hóa (sửa lỗi chính tả): {standard_docx}")
    print(f"   - Bản Tối ưu (nâng cấp hành văn): {optimized_docx}")

    if args.zalo:
        chat_id = args.chat_id or os.environ.get("CONGVAN_ZALO_CHAT_ID", "2825656851207986406")
        send_to_zalo(standard_docx, chat_id, f"Bản Chuẩn Hóa (Chỉ sửa lỗi chính tả) cho VB: {base_name}")
        send_to_zalo(optimized_docx, chat_id, f"Bản Tối Ưu (Nâng cấp câu từ hành chính) cho VB: {base_name}")

if __name__ == "__main__":
    main()
