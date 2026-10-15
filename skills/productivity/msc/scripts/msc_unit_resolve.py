#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from pathlib import Path
import subprocess

MAP_PATH = Path('./memory/msc-unit-map.json')
LIVE_URL = 'https://muasamcong.mpi.gov.vn/o/egp-portal-bid-solicitor-approved/services/um/lookup-orgInfo'


def fold(s: str) -> str:
    s = (s or '').lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def score_text(query: str, cand: str) -> float:
    q = fold(query)
    c = fold(cand)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    if q in c or c in q:
        return 0.8
    q_tokens = set(q.split())
    c_tokens = set(c.split())
    if not q_tokens or not c_tokens:
        return 0.0
    return len(q_tokens & c_tokens) / len(q_tokens | c_tokens)


def live_lookup(org_name_or_code: str, page_size: int = 10):
    payload = {
        'pageSize': page_size,
        'pageNumber': 0,
        'queryParams': {
            'roleType': {'equals': 'BMT'},
            'orgName': {'contains': None},
            'orgCode': {'contains': None},
            'orgNameOrOrgCode': {'contains': org_name_or_code},
            'agencyName': {'in': None},
            'effRoleDate': {'greaterThanOrEqual': None, 'lessThanOrEqual': None},
        },
    }
    body = json.dumps(payload, ensure_ascii=False)
    cmd = [
        'curl', '-sS', '-L', '--max-time', '25',
        '-H', 'User-Agent: Mozilla/5.0',
        '-H', 'Accept: application/json, text/plain, */*',
        '-H', 'Content-Type: application/json',
        '-H', 'Origin: https://muasamcong.mpi.gov.vn',
        '-H', 'Referer: https://muasamcong.mpi.gov.vn/web/guest/bid-solicitor-approval',
        '--data-raw', body,
        LIVE_URL,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or f'curl failed: {p.returncode}').strip())
    data = json.loads((p.stdout or '').strip() or '{}')
    return ((data or {}).get('ebidOrgInfos') or {}).get('content') or []


def resolve_by_live(query: str):
    try:
        rows = live_lookup(query)
    except Exception as e:
        return {'status': 'live_error', 'error': str(e), 'candidates': []}

    cands = []
    for r in rows:
        code = (r.get('orgCode') or '').strip()
        name = (r.get('orgFullname') or '').strip()
        if not code or not name:
            continue
        sc = score_text(query, name)
        # ưu tiên nếu query là mã orgCode
        if fold(query) == fold(code):
            sc = max(sc, 1.0)
        cands.append({'id': code, 'name': name, 'score': round(sc, 4), 'source': 'live'})

    cands.sort(key=lambda x: x['score'], reverse=True)

    if not cands:
        return {'status': 'not_found', 'query': query, 'candidates': []}

    top = cands[0]
    near = [c for c in cands if c['score'] >= max(0.5, top['score'] - 0.15)]

    # nếu query là mã đơn vị -> cần match exact id
    if re.fullmatch(r'vn[0-9a-z]+', query.lower()):
        exact = [c for c in cands if c['id'].lower() == query.lower()]
        if exact:
            return {'status': 'ok', 'query': query, 'unit': exact[0]}
        return {'status': 'invalid_id', 'query': query, 'message': 'sai id đơn vị'}

    # Guardrail: điểm match thấp thì không tự chọn bừa
    if top['score'] < 0.55:
        return {'status': 'ambiguous', 'query': query, 'candidates': cands[:5], 'message': 'độ khớp thấp, cần xác nhận'}

    if len(near) > 1:
        return {'status': 'ambiguous', 'query': query, 'candidates': near[:5]}

    return {'status': 'ok', 'query': query, 'unit': top}


def resolve_by_map(query: str):
    if not MAP_PATH.exists():
        return {'status': 'not_found', 'query': query, 'candidates': []}
    data = json.loads(MAP_PATH.read_text(encoding='utf-8'))
    raw_query = (query or '').strip()
    q = fold(raw_query)

    # If user passed explicit unit id (vn...)
    if re.fullmatch(r'vn[0-9a-z]+', raw_query.lower()):
        for u in data.get('units', []):
            if (u.get('id') or '').lower() == raw_query.lower():
                return {'status': 'ok', 'query': query, 'unit': {'id': u.get('id'), 'name': u.get('name'), 'score': 1.0, 'source': 'map'}}
        return {'status': 'invalid_id', 'query': query, 'message': 'sai id đơn vị'}

    cands = []
    for u in data.get('units', []):
        name = u.get('name', '')
        aliases = u.get('aliases', [])
        fields = [name] + aliases
        score = 0
        for f in fields:
            score = max(score, score_text(q, f))
        if score > 0:
            cands.append({'id': u.get('id'), 'name': name, 'score': round(score, 4), 'source': 'map'})

    cands.sort(key=lambda x: x['score'], reverse=True)

    if not cands:
        return {'status': 'not_found', 'query': query, 'candidates': []}

    top = cands[0]
    near = [c for c in cands if c['score'] >= max(0.5, top['score'] - 0.15)]
    if top['score'] < 0.55:
        return {'status': 'ambiguous', 'query': query, 'candidates': cands[:5], 'message': 'độ khớp thấp, cần xác nhận'}
    if len(near) > 1:
        return {'status': 'ambiguous', 'query': query, 'candidates': near[:5]}
    return {'status': 'ok', 'query': query, 'unit': top}


def main():
    ap = argparse.ArgumentParser(description='Resolve MSC unit id by live lookup, fallback to local map')
    ap.add_argument('query')
    ap.add_argument('--map-only', action='store_true', help='Skip live lookup and use local map only')
    args = ap.parse_args()

    if args.map_only:
        out = resolve_by_map(args.query)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    live = resolve_by_live(args.query)
    if live.get('status') in {'ok', 'ambiguous', 'invalid_id'}:
        print(json.dumps(live, ensure_ascii=False, indent=2))
        return

    # live lỗi/không có -> fallback map
    out = resolve_by_map(args.query)
    # annotate fallback reason for debug
    if live.get('status') == 'live_error':
        out['fallback'] = 'map'
        out['live_error'] = live.get('error')
    elif live.get('status') == 'not_found':
        out['fallback'] = 'map'
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
