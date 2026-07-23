#!/usr/bin/env python3
import argparse
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RESOLVE = 'scripts/msc_unit_resolve.py'
WATCH = 'scripts/msc_watchlist_manage.py'
DB_PATH = Path('./memory/msc.sqlite3')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_json(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or f'cmd failed: {p.returncode}').strip())
    return json.loads((p.stdout or '').strip() or '{}')


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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


def save_pending(conn, query: str, candidates):
    conn.execute('DELETE FROM follow_pending')
    conn.execute(
        'INSERT INTO follow_pending(query, candidates_json, created_at) VALUES (?, ?, ?)',
        (query, json.dumps(candidates, ensure_ascii=False), now_iso()),
    )
    conn.commit()


def load_pending(conn):
    row = conn.execute('SELECT id, query, candidates_json, created_at FROM follow_pending ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        return None
    return {
        'query': row['query'],
        'createdAt': row['created_at'],
        'candidates': json.loads(row['candidates_json'] or '[]'),
    }


def clear_pending(conn):
    conn.execute('DELETE FROM follow_pending')
    conn.commit()


def action_start(conn, query: str):
    res = run_json(['python3', RESOLVE, query])
    st = res.get('status')
    if st == 'ok':
        unit = res.get('unit') or {}
        out = run_json(['python3', WATCH, 'add', '--id', unit.get('id', ''), '--name', unit.get('name', '')])
        print(json.dumps({'status': 'added', 'unit': out.get('unit'), 'watchlist_count': out.get('count')}, ensure_ascii=False, indent=2))
        return

    if st == 'ambiguous':
        cands = res.get('candidates') or []
        save_pending(conn, query, cands)
        print(json.dumps({'status': 'ambiguous', 'query': query, 'candidates': cands}, ensure_ascii=False, indent=2))
        return

    print(json.dumps(res, ensure_ascii=False, indent=2))


def action_confirm(conn, choice: str):
    p = load_pending(conn)
    if not p:
        print(json.dumps({'status': 'no_pending', 'message': 'Không có yêu cầu /fl đang chờ xác nhận.'}, ensure_ascii=False, indent=2))
        return

    cands = p.get('candidates') or []
    pick = None
    c = (choice or '').strip()

    if c.isdigit():
        i = int(c)
        if 1 <= i <= len(cands):
            pick = cands[i - 1]

    if pick is None:
        for x in cands:
            if (x.get('id') or '').lower() == c.lower():
                pick = x
                break

    if pick is None:
        print(json.dumps({'status': 'invalid_choice', 'message': 'Lựa chọn không hợp lệ.', 'candidates': cands}, ensure_ascii=False, indent=2))
        return

    out = run_json(['python3', WATCH, 'add', '--id', pick.get('id', ''), '--name', pick.get('name', '')])
    clear_pending(conn)
    print(json.dumps({'status': 'added', 'unit': out.get('unit'), 'watchlist_count': out.get('count')}, ensure_ascii=False, indent=2))


def action_status(conn):
    p = load_pending(conn)
    if not p:
        print(json.dumps({'status': 'no_pending'}, ensure_ascii=False, indent=2))
        return
    print(json.dumps({'status': 'pending', **p}, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description='Follow a unit into MSC watchlist with confirm flow (SQLite)')
    ap.add_argument('action', choices=['start', 'confirm', 'status', 'clear'])
    ap.add_argument('value', nargs='?', default='')
    args = ap.parse_args()

    conn = connect_db()

    if args.action == 'start':
        if not args.value.strip():
            print(json.dumps({'status': 'error', 'message': 'Thiếu tên/mã đơn vị.'}, ensure_ascii=False, indent=2))
            return
        action_start(conn, args.value)
        return
    if args.action == 'confirm':
        action_confirm(conn, args.value)
        return
    if args.action == 'status':
        action_status(conn)
        return
    if args.action == 'clear':
        clear_pending(conn)
        print(json.dumps({'status': 'cleared'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
