from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .schema import MscSchema

SKILL_ROOT = Path(__file__).parent.parent.parent  # msc_tool/renderer.py -> lib -> msc
REPORT_DIR = SKILL_ROOT / 'reports'


def _slug(s: str) -> str:
    out = ''.join(ch if ch.isalnum() else '_' for ch in s.strip().lower())
    out = '_'.join([p for p in out.split('_') if p])
    return out[:64] or 'query'


def render_markdown(schema: MscSchema) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    qp = schema.query_params
    key = qp.code or qp.unit or 'query'
    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    path = REPORT_DIR / f"msc_{schema.query_type}_{_slug(key)}_{ts}.md"

    lines = []
    lines.append(f"# MSC {schema.query_type.upper()} Report")
    lines.append("")
    lines.append(f"- Generated at: {schema.fetched_at}")
    lines.append(f"- Source: {schema.source}")
    lines.append(f"- Script: {schema.script_used}")
    lines.append("")
    lines.append("## Query params")
    lines.append(f"- code: {qp.code}")
    lines.append(f"- unit: {qp.unit}")
    lines.append(f"- from: {qp.from_date}")
    lines.append(f"- to: {qp.to_date}")
    lines.append(f"- n: {qp.n}")
    lines.append("")

    if schema.error:
        lines.append("## Error")
        lines.append(f"- code: {schema.error.code}")
        lines.append(f"- message: {schema.error.message}")
    else:
        lines.append(f"## Results ({schema.total_count})")
        if schema.records:
            cols = sorted({k for r in schema.records for k in r.keys()})
            lines.append('| ' + ' | '.join(cols) + ' |')
            lines.append('| ' + ' | '.join(['---'] * len(cols)) + ' |')
            for r in schema.records:
                row = [str(r.get(c, '')).replace('\n', ' ') for c in cols]
                lines.append('| ' + ' | '.join(row) + ' |')
        else:
            lines.append('- No records')

    lines.append('')
    lines.append('## Notes')
    lines.append('- API-first via muasamcong hidden API scripts.')

    path.write_text('\n'.join(lines), encoding='utf-8')
    return path
