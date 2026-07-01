import json
import os
import subprocess
import sys

_hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
STATE_FILE = os.path.join(_hermes_home, "cron", "cong-van-den", "vbden_state.json")

def main():
    if not os.path.exists(STATE_FILE):
        print("State file not found:", STATE_FILE)
        return
        
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
        
    target_ids = ["2515", "2516", "2517", "2522", "2524", "2525", "2527", "2529", "2531", "2532"]
    
    # Remove from seen_ids
    seen_ids = state.get("seen_ids", [])
    updated_seen = [x for x in seen_ids if x not in target_ids]
    state["seen_ids"] = updated_seen
    
    # Remove from documents
    documents = state.get("documents", {})
    for tid in target_ids:
        if tid in documents:
            del documents[tid]
            
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully reset {len(target_ids)} documents in state file.")
    
    # Trigger scrape script
    scrape_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "congchuc_scrape.py")
    print("Running congchuc_scrape.py to fetch and deliver them to Zalo...")
    subprocess.run([sys.executable, scrape_script])

if __name__ == "__main__":
    main()
