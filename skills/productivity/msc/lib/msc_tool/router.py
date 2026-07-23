from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Intent = Literal["lookup_pl", "lookup_ib", "list_kh", "list_tbmt", "ambiguous"]

PL_RE = re.compile(r"\bPL\d{8,}\b", re.IGNORECASE)
IB_RE = re.compile(r"\bIB\d{8,}\b", re.IGNORECASE)
TOP_RE = re.compile(r"(?:\btop\s*(\d+)\b|\b(\d+)\s*(?:gói|mới nhất)\b)", re.IGNORECASE)
SLASH_RE = re.compile(r"/(tbmt|kh)(?:@\w+)?\b", re.IGNORECASE)
LEADING_N_RE = re.compile(r"^\s*(\d{1,3})\s+(.+?)\s*$", re.IGNORECASE)


@dataclass
class RoutedQuery:
    intent: Intent
    code: str | None = None
    unit: str | None = None
    n: int | None = None
    raw: str = ""


def _strip_slash_prefix(text: str) -> tuple[str | None, str]:
    m = SLASH_RE.search(text)
    if not m:
        return None, text.strip()
    cmd = m.group(1).lower()
    args = text[m.end() :].strip()
    return cmd, args


def route_query(text: str) -> RoutedQuery:
    raw = text.strip()
    cmd, body = _strip_slash_prefix(raw)

    pl = PL_RE.search(body)
    if pl:
        return RoutedQuery(intent="lookup_pl", code=pl.group(0).upper(), raw=raw)

    ib = IB_RE.search(body)
    if ib:
        return RoutedQuery(intent="lookup_ib", code=ib.group(0).upper(), raw=raw)

    top_m = TOP_RE.search(body)
    n = None
    if top_m:
        n = int(next(g for g in top_m.groups() if g))

    normalized = body.lower()
    has_kh = (cmd == "kh") or ("khlcnt" in normalized) or re.search(r"\bkh\b", normalized) is not None
    has_tbmt = (cmd == "tbmt") or ("tbmt" in normalized) or ("mời thầu" in normalized)

    unit = body
    unit = re.sub(r"^(tbmt|kh|khlcnt)\b", "", unit, flags=re.IGNORECASE).strip()

    # /tbmt 5 bệnh viện bạch mai -> n=5, unit='bệnh viện bạch mai'
    m_leading_n = LEADING_N_RE.match(unit)
    if m_leading_n:
        lead_n = int(m_leading_n.group(1))
        if 1 <= lead_n <= 100:
            n = n or lead_n
            unit = m_leading_n.group(2).strip()

    unit = re.sub(r"\btop\s*\d+\b", "", unit, flags=re.IGNORECASE).strip()
    unit = re.sub(r"\b\d+\s*(gói|mới nhất)\b", "", unit, flags=re.IGNORECASE).strip()

    if has_kh and has_tbmt:
        return RoutedQuery(intent="ambiguous", unit=unit, n=n, raw=raw)
    if has_kh:
        return RoutedQuery(intent="list_kh", unit=unit, n=n or 5, raw=raw)
    if has_tbmt:
        return RoutedQuery(intent="list_tbmt", unit=unit, n=n or 5, raw=raw)

    if cmd == "kh":
        return RoutedQuery(intent="list_kh", unit=unit, n=n or 5, raw=raw)
    if cmd == "tbmt":
        return RoutedQuery(intent="list_tbmt", unit=unit, n=n or 5, raw=raw)

    return RoutedQuery(intent="ambiguous", unit=unit, n=n, raw=raw)
