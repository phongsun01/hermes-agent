import json
import os
import re

_hermes_home = os.environ.get("HERMES_HOME", "/opt/data")
STATE_FILE = os.path.join(_hermes_home, "cron", "cong-van-den", "vbden_state.json")

target_ids = {'2732','2729','2742','2733','2730','2723','2721','2722','2716','2700','2708','2713','2698'}

with open(STATE_FILE, "r", encoding="utf-8") as f:
    state = json.load(f)

docs = state.get("documents", {})
count = 0

for sid in target_ids:
    if sid in docs:
        docs[sid]["status"] = "new"
        docs[sid]["note"] = re.sub(r'\[Tự động:.*?\]', '', docs[sid].get("note", "")).strip()
        count += 1

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print(f"✅ Successfully updated {count} active documents back to status 'new' in vbden_state.json!")
