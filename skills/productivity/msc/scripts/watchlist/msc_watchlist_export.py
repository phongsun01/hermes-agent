#!/usr/bin/env python3
import argparse
import json
import sqlite3
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent.parent  # scripts/watchlist/export.py -> msc/
DB_PATH = SKILL_ROOT / 'data/msc.sqlite3'
LEGACY_JSON = SKILL_ROOT / 'data/msc-watchlist.json'


def load_from_sqlite():
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT id, name, added_at FROM watchlist_units ORDER BY added_at ASC'
    ).fetchall()
    return [
        {'id': r['id'], 'name': r['name'], 'addedAt': r['added_at'], 'source': 'sqlite'}
        for r in rows
        if r['id']
    ]


def load_from_legacy_json():
    if not LEGACY_JSON.exists():
        return []
    try:
        raw = json.loads(LEGACY_JSON.read_text(encoding='utf-8'))
    except Exception:
        return []
    units = raw.get('units') if isinstance(raw, dict) else []
    out = []
    if isinstance(units, list):
        for u in units:
            if isinstance(u, dict):
                uid = (u.get('id') or '').strip().lower()
                if uid:
                    out.append({'id': uid, 'name': u.get('name') or uid, 'addedAt': u.get('addedAt'), 'source': 'legacy_json'})
            elif isinstance(u, str):
                uid = (u or '').strip().lower()
                if uid:
                    out.append({'id': uid, 'name': uid, 'addedAt': None, 'source': 'legacy_json'})
    return out


def dedupe(units):
    seen = set()
    out = []
    for u in units:
        uid = (u.get('id') or '').strip().lower()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        x = dict(u)
        x['id'] = uid
        out.append(x)
    return out


def main():
    ap = argparse.ArgumentParser(description='Export MSC watchlist from SQLite (with JSON fallback)')
    ap.add_argument('--ids-only', action='store_true', help='Print only unit id lines')
    ap.add_argument('--prompt', action='store_true', help='Print watchlist bullets for prompt text')
    args = ap.parse_args()

    units = load_from_sqlite()
    source = 'sqlite'
    if not units:
        units = load_from_legacy_json()
        source = 'legacy_json' if units else 'empty'

    units = dedupe(units)

    if args.ids_only:
        for u in units:
            print(u['id'])
        return

    if args.prompt:
        for u in units:
            print(f"- {u['id']} | {u.get('name','')}")
        return

    print(json.dumps({'status': 'ok', 'source': source, 'count': len(units), 'units': units}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
