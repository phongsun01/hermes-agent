import os
import sys
import re
from datetime import datetime

# Enforce UTF-8 encoding for standard output on Windows command prompt
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Regex to extract YAML frontmatter
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL | re.MULTILINE)

# Regex patterns to detect expiry dates
EXPIRY_KEYS = [r'expiry', r'expiration', r'expires', r'han_dung', r'han', r'ngay_het_han']
DATE_RE = re.compile(r'(\d{4})[-/](\d{2})[-/](\d{2})')

def parse_yaml_fallback(text: str):
    """Simple parser for YAML frontmatter key-values and lists."""
    data = {}
    lines = text.splitlines()
    current_key = None
    list_items = []
    
    for line in lines:
        if line.strip().startswith("-"):
            # List item
            val = line.strip().lstrip("-").strip()
            # Clean quotes
            val = val.strip("'\"")
            list_items.append(val)
        else:
            if current_key and list_items:
                data[current_key] = list_items
                list_items = []
            
            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip().strip("'\"")
                data[key] = val
                current_key = key
                
    if current_key and list_items:
        data[current_key] = list_items
        
    return data

def scan_file_for_expiry(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return []

    match = FRONTMATTER_RE.search(content)
    if not match:
        return []

    frontmatter_text = match.group(1)
    yaml_data = parse_yaml_fallback(frontmatter_text)
    
    results = []
    
    # Check simple keys
    for k, v in yaml_data.items():
        if any(pattern in k.lower() for pattern in EXPIRY_KEYS):
            # Try to find a date
            date_match = DATE_RE.search(str(v))
            if date_match:
                date_str = "-".join(date_match.groups())
                results.append((k, date_str))
                
    # Also parse nested lists if any
    # Check if there is a list of dicts (custom parsing for lines)
    lines = frontmatter_text.splitlines()
    item_name = None
    for line in lines:
        line_strip = line.strip()
        if "item:" in line_strip:
            item_name = line_strip.split(":", 1)[1].strip().strip("'\"")
        elif "expiry:" in line_strip and item_name:
            date_match = DATE_RE.search(line_strip)
            if date_match:
                date_str = "-".join(date_match.groups())
                results.append((item_name, date_str))
                item_name = None
                
    return results

def check_expiry(vault_path: str, days_threshold: int = 90):
    if not os.path.exists(vault_path):
        print(f"ERROR: Thư mục Vault không tồn tại: {vault_path}")
        return
        
    found_any = False
    today = datetime.now()
    
    print(f"=== Đang quét thời hạn giấy tờ tại Vault: {vault_path} ===")
    
    for root, dirs, files in os.walk(vault_path):
        # Skip hidden obsidian directories
        if ".obsidian" in root:
            continue
            
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                expiries = scan_file_for_expiry(file_path)
                
                if expiries:
                    rel_path = os.path.relpath(file_path, vault_path)
                    print(f"\n[Ghi chú: {rel_path}]")
                    for name, date_str in expiries:
                        try:
                            expiry_date = datetime.strptime(date_str, "%Y-%m-%d")
                            days_left = (expiry_date - today).days
                            
                            status = "BÌNH THƯỜNG"
                            if days_left < 0:
                                status = "ĐÃ HẾT HẠN 🔴"
                            elif days_left <= days_threshold:
                                status = f"SẮP HẾT HẠN 🟡 (Còn {days_left} ngày)"
                            else:
                                status = f"Còn hạn 🟢 ({days_left} ngày)"
                                
                            print(f"  - {name}: Hạn {date_str} -> {status}")
                            found_any = True
                        except Exception as e:
                            print(f"  - {name}: Hạn {date_str} -> Lỗi định dạng ngày ({e})")
                            
    if not found_any:
        print("Không tìm thấy thông tin giấy tờ hoặc lịch hết hạn nào.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_expiry.py <vault_path> [days_threshold]")
        sys.exit(1)
        
    vault = sys.argv[1]
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    check_expiry(vault, threshold)
