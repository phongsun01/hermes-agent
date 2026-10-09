# Test test_fixtures.py
import re
from pathlib import Path

def parse_html(html: str):
    nums = re.findall(r'class="finnish\d\s+bool"[^>]*>(\d+)<', html)
    ky_m = re.search(r'id="DT6X45_KY_VE">#?(\d+)', html)
    return {
        "nums": [int(x) for x in nums[:6]] if len(nums) >= 6 else None,
        "ky": int(ky_m.group(1)) if ky_m else None
    }

base = Path(__file__).resolve().parent

# Test fixture 00642 (23/09/2020) -> 02 08 17 23 30 41, ky 642
fix642 = (base / "fixture_00642.html").read_text(encoding="utf-8", errors="ignore")
res642 = parse_html(fix642)
print("Fixture 00642:", res642)
assert res642["ky"] == 642
assert res642["nums"] == [2, 8, 17, 23, 30, 41]

# Test fixture 01572 (07/10/2026) -> 10 14 36 37 41 43, ky 1572
fix1572 = (base / "fixture_01572.html").read_text(encoding="utf-8", errors="ignore")
res1572 = parse_html(fix1572)
print("Fixture 01572:", res1572)
assert res1572["ky"] == 1572
assert res1572["nums"] == [10, 14, 36, 37, 41, 43]

print("ALL FIXTURE TESTS PASSED!")
