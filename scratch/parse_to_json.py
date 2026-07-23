import re
import json

with open("scratch/riddles_extracted.txt", "r", encoding="utf-8") as f:
    text = f.read()

categories = {
    "1Câu đố mẹo hack não cho người lớn có đáp án": "Người lớn",
    "2Câu đố mẹo cho trẻ em có đáp án": "Trẻ em",
    "3Câu đố mẹo về con vật có đáp án": "Con vật",
    "4Câu đố về đồ vật, sự vật": "Đồ vật, sự vật",
    "5Câu đố mẹo hay nhất có đáp án": "Đố mẹo hay",
    "6Câu đó mẹo hay, cười đau bụng": "Cười đau bụng"
}

current_category = "Chung"
riddles = []

lines = text.split("\n")
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Check if category matches
    matched_cat = False
    for cat_raw, cat_name in categories.items():
        if cat_raw in line:
            current_category = cat_name
            matched_cat = True
            break
    if matched_cat:
        continue
        
    # Check if it has a question and answer
    if "=> Đáp án:" in line:
        parts = line.split("=> Đáp án:")
        q = parts[0].strip()
        a = parts[1].strip()
        
        # Clean question from numbers if any at start
        q = re.sub(r'^\d+\s*', '', q)
        q = re.sub(r'^Câu \d+:\s*', '', q)
        q = re.sub(r'^\-\s*', '', q)
        
        # Clean answer
        a = re.sub(r'^\-\s*', '', a)
        
        riddles.append({
            "category": current_category,
            "question": q,
            "answer": a
        })

with open("scratch/riddles.json", "w", encoding="utf-8") as f:
    json.dump(riddles, f, ensure_ascii=False, indent=2)

print(f"Parsed {len(riddles)} riddles.")
