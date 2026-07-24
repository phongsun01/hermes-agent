import os
import json
import random

# Get directory path of this file
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(DIR_PATH, "..", "resources", "riddles.json")

def load_riddles():
    if not os.path.exists(JSON_PATH):
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_riddles(riddles):
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(riddles, f, ensure_ascii=False, indent=2)

def get_random_riddles(count=1):
    riddles = load_riddles()
    if not riddles:
        return []
    
    selected_riddles = []
    for _ in range(count):
        # Find minimum count
        min_count = min(r.get("count", 0) for r in riddles)
        
        # Filter candidates with min count
        candidates = [r for r in riddles if r.get("count", 0) == min_count]
        
        # Pick a random one
        selected = random.choice(candidates)
        selected_riddles.append(selected)
        
        # Increment count in original list
        for r in riddles:
            if r["question"] == selected["question"]:
                r["count"] = r.get("count", 0) + 1
                break
                
    save_riddles(riddles)
    return selected_riddles

if __name__ == "__main__":
    import sys
    # Reconfigure stdout to use UTF-8 for Vietnamese characters
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    # Simple CLI interface
    if len(sys.argv) > 1 and sys.argv[1] == "random":
        count = 1
        if len(sys.argv) > 2:
            try:
                count = int(sys.argv[2])
            except ValueError:
                pass
        
        if count > 1:
            riddles = get_random_riddles(count)
            print(json.dumps(riddles, ensure_ascii=False))
        else:
            riddles = get_random_riddles(1)
            riddle = riddles[0] if riddles else {"error": "No riddles found."}
            print(json.dumps(riddle, ensure_ascii=False))
    else:
        print(json.dumps({"usage": "python dovui_tool.py random [count]"}))
