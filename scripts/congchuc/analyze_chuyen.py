import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

print("Reading chuyen_page.html...")
with open("D:/Antigravity/Hermes/scripts/chuyen_page.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Searching for HTML tags containing btnDong or btnChuyen...")
# Find tags starting with < and ending with >
for tag in re.findall(r'<[^>]*btn(?:Dong|Chuyen)[^>]*>', html, re.IGNORECASE):
    # Ignore script or javascript lines
    if "Script" in tag or "Stylesheet" in tag or "function()" in tag or "Sys.Application" in tag:
        continue
    print("  Tag:", tag)
