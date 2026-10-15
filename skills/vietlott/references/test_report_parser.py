#!/usr/bin/env python3
"""test_report_parser.py"""
import re
from pathlib import Path

def parse_detail(html: str):
    m_ky = re.search(r'id="DT6X45_KY_VE">#?(\d+)', html)
    m_ngay = re.search(r'Ng&agrave;y quay thưởng\s+(\d{2}/\d{2}/\d{4})', html)
    nums = re.findall(r'class="finnish\d\s+bool"[^>]*>(\d+)<', html)
    m_jp = re.search(r'id="DT6X45_G_JACKPOT"[^>]*>([^<]+)', html)
    m_s_jp = re.search(r'id="DT6X45_S_JACKPOT"[^>]*>\s*([0-9,.]+)', html)
    m_s_g1 = re.search(r'id="DT6X45_S_G1"[^>]*>\s*([0-9,.]+)', html)
    m_s_g2 = re.search(r'id="DT6X45_S_G2"[^>]*>\s*([0-9,.]+)', html)
    m_s_g3 = re.search(r'id="DT6X45_S_G3"[^>]*>\s*([0-9,.]+)', html)

    return {
        "ky": int(m_ky.group(1)) if m_ky else None,
        "ngay": m_ngay.group(1) if m_ngay else None,
        "nums": [int(x) for x in nums[:6]] if len(nums) >= 6 else None,
        "jackpot": m_jp.group(1).strip() if m_jp else None,
        "jackpot_winners": int(m_s_jp.group(1).replace(",", "").replace(".", "")) if m_s_jp else 0,
        "g1_winners": m_s_g1.group(1).strip() if m_s_g1 else "0",
        "g2_winners": m_s_g2.group(1).strip() if m_s_g2 else "0",
        "g3_winners": m_s_g3.group(1).strip() if m_s_g3 else "0",
    }

base = Path(__file__).resolve().parent
html1572 = (base / "fixture_01572.html").read_text(encoding="utf-8", errors="ignore")
res = parse_detail(html1572)
print("Detailed parse result:", res)
