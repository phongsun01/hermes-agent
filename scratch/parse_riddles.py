import re
import json
from bs4 import BeautifulSoup

path = r"C:\Users\Desktop\.gemini\antigravity-ide\brain\6b511865-1c9b-4a07-a5e2-d54fdb27304e\.system_generated\steps\17\content.md"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

soup = BeautifulSoup(content, "html.parser")

# Let's inspect headings, list items, or paragraphs
# Frequently, riddles on websites like avakids are inside paragraphs, lists, or headers.
# Let's find all text blocks and check if they contain "Câu " and extract them.
out = []
for p in soup.find_all(['p', 'h3', 'h4', 'li', 'div']):
    text = p.get_text().strip()
    if not text:
        continue
    # Let's see if it looks like a riddle or answer: e.g. starting with "Câu 1", "Câu 2", etc.
    # or containing "Đáp án"
    if re.match(r'^Câu \d+:', text) or "đáp án" in text.lower() or "câu hỏi" in text.lower():
        if text not in out:
            out.append(text)

with open("scratch/riddles_extracted.txt", "w", encoding="utf-8") as f:
    for item in out:
        f.write(item + "\n\n")

print(f"Extracted {len(out)} paragraphs/headers.")
