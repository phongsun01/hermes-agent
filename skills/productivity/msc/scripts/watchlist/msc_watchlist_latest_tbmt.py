#!/usr/bin/env python3
import argparse
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent.parent  # scripts/watchlist/latest_tbmt.py -> msc/
DB_PATH = SKILL_ROOT / 'data/msc.sqlite3'
LIST_SCRIPT = str(SKILL_ROOT / 'scripts/msc_hidden_api_list.py')


def parse_dt(s: str):
    s = (s or '').strip()
    if not s:
        return datetime.min
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
    except Exception:
        return datetime.min


def get_top_tbmt(unit_id: str, field: str):
    cmd = [
        'python3', LIST_SCRIPT,
        '--token', '',
        '--kind', 'tbmt',
        '--unit-id', unit_id,
        '--entity-field', field,
        '-n', '1'
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return None, (p.stderr or 'script error').strip()
    try:
        data = json.loads((p.stdout or '{}').strip() or '{}')
    except Exception as e:
        return None, f'json error: {e}'
    rows = data.get('rows') or []
    if not rows:
        return None, None
    return rows[0], None


def pick_latest(unit_id: str):
    a, e1 = get_top_tbmt(unit_id, 'procuringEntityCode')
    b, e2 = get_top_tbmt(unit_id, 'investorCode')

    if not a and not b:
        return None, {'procuringEntityCode': e1, 'investorCode': e2}

    if a and not b:
        a['_sourceField'] = 'procuringEntityCode'
        return a, None
    if b and not a:
        b['_sourceField'] = 'investorCode'
        return b, None

    da = parse_dt(a.get('publicDate'))
    db = parse_dt(b.get('publicDate'))
    if db > da:
        b['_sourceField'] = 'investorCode'
        return b, None
    a['_sourceField'] = 'procuringEntityCode'
    return a, None


def main():
    ap = argparse.ArgumentParser(description='Latest 1 TBMT per watchlist unit with dual-field fallback')
    ap.add_argument('-n', type=int, default=100)
    args = ap.parse_args()

    if not DB_PATH.exists():
        raise SystemExit('watchlist db not found')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    units = conn.execute('SELECT id, name FROM watchlist_units ORDER BY added_at ASC LIMIT ?', (args.n,)).fetchall()

    out = []
    for u in units:
        unit_id = u['id']
        unit_name = u['name']
        top, err = pick_latest(unit_id)
        if not top:
            out.append({
                'unit': unit_name,
                'id': unit_id,
                'error': err,
            })
            continue
        out.append({
            'unit': unit_name,
            'id': unit_id,
            'notifyNo': top.get('notifyNo'),
            'publicDate': top.get('publicDate'),
            'name': top.get('name'),
            'sourceField': top.get('_sourceField'),
        })

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
