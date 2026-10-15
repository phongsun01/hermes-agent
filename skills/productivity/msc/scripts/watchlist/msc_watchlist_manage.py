#!/usr/bin/env python3
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent.parent  # scripts/watchlist/manage.py -> msc/
DB_PATH = SKILL_ROOT / 'data/msc.sqlite3'
LEGACY_JSON = SKILL_ROOT / 'data/msc-watchlist.json'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize_id(v: str) -> str:
    return (v or '').strip().lower()


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist_units (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS follow_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            candidates_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def _legacy_units():
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
                uid = normalize_id(u.get('id', ''))
                if uid:
                    out.append((uid, u.get('name') or uid, u.get('addedAt') or now_iso()))
            elif isinstance(u, str):
                uid = normalize_id(u)
                if uid:
                    out.append((uid, uid, now_iso()))
    return out


def migrate_legacy_if_needed(conn):
    count = conn.execute('SELECT COUNT(*) AS n FROM watchlist_units').fetchone()['n']
    if count > 0:
        return
    rows = _legacy_units()
    for uid, name, added_at in rows:
        conn.execute(
            'INSERT OR IGNORE INTO watchlist_units(id, name, added_at) VALUES (?, ?, ?)',
            (uid, name, added_at),
        )
    conn.commit()


def list_units(conn):
    rows = conn.execute('SELECT id, name, added_at FROM watchlist_units ORDER BY added_at ASC').fetchall()
    return [{'id': r['id'], 'name': r['name'], 'addedAt': r['added_at']} for r in rows]


def main():
    ap = argparse.ArgumentParser(description='Manage MSC watchlist (SQLite)')
    ap.add_argument('action', choices=['list', 'add', 'remove'])
    ap.add_argument('--id', default='')
    ap.add_argument('--name', default='')
    args = ap.parse_args()

    conn = connect_db()
    migrate_legacy_if_needed(conn)

    if args.action == 'list':
        units = list_units(conn)
        print(json.dumps({'status': 'ok', 'count': len(units), 'units': units}, ensure_ascii=False, indent=2))
        return

    if args.action == 'add':
        uid = normalize_id(args.id)
        if not uid:
            print(json.dumps({'status': 'error', 'message': 'missing id'}, ensure_ascii=False))
            return
        ex = conn.execute('SELECT id, name, added_at FROM watchlist_units WHERE id=?', (uid,)).fetchone()
        if ex:
            if args.name and ex['name'] == ex['id']:
                conn.execute('UPDATE watchlist_units SET name=? WHERE id=?', (args.name, uid))
                conn.commit()
                ex = conn.execute('SELECT id, name, added_at FROM watchlist_units WHERE id=?', (uid,)).fetchone()
            n = conn.execute('SELECT COUNT(*) AS n FROM watchlist_units').fetchone()['n']
            print(json.dumps({'status': 'exists', 'unit': {'id': ex['id'], 'name': ex['name'], 'addedAt': ex['added_at']}, 'count': n}, ensure_ascii=False, indent=2))
            return

        unit = {'id': uid, 'name': args.name or uid, 'addedAt': now_iso()}
        conn.execute('INSERT INTO watchlist_units(id, name, added_at) VALUES (?, ?, ?)', (unit['id'], unit['name'], unit['addedAt']))
        conn.commit()
        n = conn.execute('SELECT COUNT(*) AS n FROM watchlist_units').fetchone()['n']
        print(json.dumps({'status': 'added', 'unit': unit, 'count': n}, ensure_ascii=False, indent=2))
        return

    if args.action == 'remove':
        uid = normalize_id(args.id)
        if not uid:
            print(json.dumps({'status': 'error', 'message': 'missing id'}, ensure_ascii=False))
            return
        cur = conn.execute('DELETE FROM watchlist_units WHERE id=?', (uid,))
        conn.commit()
        n = conn.execute('SELECT COUNT(*) AS n FROM watchlist_units').fetchone()['n']
        if cur.rowcount == 0:
            print(json.dumps({'status': 'not_found', 'id': uid, 'count': n}, ensure_ascii=False, indent=2))
            return
        print(json.dumps({'status': 'removed', 'id': uid, 'count': n}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
