import json
import os
import sys

_hermes_home = os.environ.get("HERMES_HOME", "/opt/data")
sys.path.append("/opt/hermes/skills/cc/scripts")
sys.path.append("/opt/data/skills/cc/scripts")

from congchuc_scrape import pw_get_documents, HAS_PLAYWRIGHT, STATE_FILE, load_state

docs, msg = pw_get_documents()
print(f"pw_get_documents result: {msg}")
print(f"\nFOUND {len(docs)} UNPROCESSED DOCUMENTS ON WEB PORTAL GRID:")

state = load_state()
stored_docs = state.get("documents", {})
seen_ids = set(state.get("seen_ids", []))

for d in docs:
    so_den = str(d.get('so_den', '')).strip()
    so_kh = d.get('so_ky_hieu', '')
    tac_gia = d.get('tac_gia', '')
    trich_yeu = (d.get('trich_yeu') or '')[:50]
    
    st_info = stored_docs.get(so_den, {})
    current_status = st_info.get('status', 'NOT_FOUND')
    in_seen = so_den in seen_ids
    note = st_info.get('note', '')
    
    print(f" #{so_den} | Web: {so_kh} | Local Status: {current_status} | In seen_ids: {in_seen} | {tac_gia} | {trich_yeu} | Note: {note}")
