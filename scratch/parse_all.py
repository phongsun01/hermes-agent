import os
import re
import json
from bs4 import BeautifulSoup

paths = [
    r"C:\Users\Desktop\.gemini\antigravity-ide\brain\6b511865-1c9b-4a07-a5e2-d54fdb27304e\.system_generated\steps\17\content.md",
    r"C:\Users\Desktop\.gemini\antigravity-ide\brain\6b511865-1c9b-4a07-a5e2-d54fdb27304e\.system_generated\steps\65\content.md",
    r"C:\Users\Desktop\.gemini\antigravity-ide\brain\6b511865-1c9b-4a07-a5e2-d54fdb27304e\.system_generated\steps\67\content.md",
    r"C:\Users\Desktop\.gemini\antigravity-ide\brain\6b511865-1c9b-4a07-a5e2-d54fdb27304e\.system_generated\steps\69\content.md"
]

all_riddles = []
seen_questions = set()

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def normalize_key(text):
    # Remove all punctuation, non-alphanumeric, spaces to compare duplicates
    return re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]', '', text.lower())

for path_idx, path in enumerate(paths):
    if not os.path.exists(path):
        print(f"Skipping {path} (not found)")
        continue
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    soup = BeautifulSoup(content, "html.parser")
    
    # We find text containing matches
    # Let's search inside p, li, h3, h4, div
    for p in soup.find_all(['p', 'h3', 'h4', 'li', 'div']):
        text = p.get_text().strip()
        if not text:
            continue
            
        # Parse formats like:
        # Question text => Đáp án: Answer text
        # or similar formats
        if "=> Đáp án:" in text:
            parts = text.split("=> Đáp án:")
            q = clean_text(parts[0])
            a = clean_text(parts[1])
            
            # Clean common prefixes from questions
            q = re.sub(r'^\d+\s*', '', q)
            q = re.sub(r'^Câu \d+:\s*', '', q, flags=re.IGNORECASE)
            q = re.sub(r'^Câu \d+\s*', '', q, flags=re.IGNORECASE)
            q = re.sub(r'^\-\s*', '', q)
            q = clean_text(q)
            
            # Clean answer
            a = re.sub(r'^\-\s*', '', a)
            a = clean_text(a)
            
            if not q or not a:
                continue
                
            norm_q = normalize_key(q)
            if norm_q not in seen_questions:
                seen_questions.add(norm_q)
                all_riddles.append({
                    "question": q,
                    "answer": a,
                    "count": 0
                })
        else:
            # Maybe check other patterns like lines starting with "Câu hỏi:" and next line is "Đáp án:"
            pass

# Write to scratch first
with open("scratch/riddles_merged.json", "w", encoding="utf-8") as f:
    json.dump(all_riddles, f, ensure_ascii=False, indent=2)

print(f"Parsed and merged {len(all_riddles)} unique riddles.")
