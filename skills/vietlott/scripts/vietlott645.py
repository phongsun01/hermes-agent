#!/usr/bin/env python3
"""Vietlott Mega 6/45: kiểm định ngẫu nhiên, backtest "dự đoán", xác suất, sinh bộ số.

Lệnh:
  parse  raw.txt > draws.csv   # dán bảng kết quả copy từ vietlott.vn -> CSV (cũ -> mới)
  odds                         # xác suất trúng k/6 (siêu bội)
  stats  draws.csv             # kiểm định: chi-square đã hiệu chỉnh + order-statistics (Q)
  backtest draws.csv           # walk-forward: chiến lược nào đánh bại ngẫu nhiên?
  pick [--mode random|hot|cold] [--n 1] [--csv draws.csv]

draws.csv: "ngay,n1..n6,ky" theo thứ tự thời gian (cũ -> mới). Chỉ cần thư viện chuẩn.
Cơ sở: Coronel-Brizio et al., arXiv:0806.4595 (kiểm định Q); Nkomozake, arXiv:2403.12836 (CDM).
"""
import argparse, csv, math, os, random, re, sys
from collections import Counter
from math import comb, exp, factorial
from pathlib import Path

# Đảm bảo UTF-8 cho Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR / "draws.csv"

N, K = 45, 6
TOTAL = comb(N, K)  # 8,145,060


# ---------- xác suất ----------
def p_match(k):
    """P(đúng k/6 số trên 1 vé) = C(6,k)*C(39,6-k)/C(45,6)  (bài 0806.4595, Eq.1)."""
    return comb(K, k) * comb(N - K, K - k) / TOTAL


def chi2_sf(x, df):
    """P(chi2_df > x), df chẵn (công thức đóng, không cần scipy)."""
    assert df % 2 == 0
    h = x / 2
    return exp(-h) * sum(h ** j / factorial(j) for j in range(df // 2))


# ---------- dữ liệu ----------
def parse_text(text):
    """Dòng Vietlott: 'dd/mm/yyyy 00642 020817233041' (12 chữ số = 6 cặp)."""
    rows = []
    for d, ky, s in re.findall(r"(\d{2}/\d{2}/\d{4})\s+(\d{5})\s+(\d{12})", text):
        rows.append((int(ky), d, [int(s[i:i + 2]) for i in range(0, 12, 2)]))
    rows.sort()
    return rows


def load(path=None, limit=None):
    csv_file = Path(path) if path else DEFAULT_CSV
    if not csv_file.exists():
        if path:
            sys.exit(f"Không tìm thấy file: {csv_file}")
        else:
            sys.exit(f"Chưa có cache dữ liệu {csv_file}. Vui lòng chạy 'python vl_fetch.py --update' trước.")
    draws = []
    with open(csv_file, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            try:
                nums = sorted(int(x) for x in row[1:1 + K])
            except ValueError:
                continue  # header
            if len(nums) == K and all(1 <= n <= N for n in nums):
                draws.append(nums)
    if limit and limit > 0 and len(draws) > limit:
        draws = draws[-limit:]
    return draws


def freq(draws):
    c = Counter(n for d in draws for n in d)
    return {i: c.get(i, 0) for i in range(1, N + 1)}


# ---------- kiểm định (bài 0806.4595) ----------
def _cov():
    """Ma trận hiệp phương sai của thống kê thứ tự Y(1..K) dưới H0 (Eq.10)."""
    V = [[0.0] * K for _ in range(K)]
    for i in range(1, K + 1):
        for j in range(1, K + 1):
            a, b = min(i, j), max(i, j)
            V[i - 1][j - 1] = a * (K - b + 1) * (N + 1) * (N - K) / ((K + 1) ** 2 * (K + 2))
    return V


def _inverse(M):
    n = len(M)
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(M)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[p] = A[p], A[c]
        piv = A[c][c]
        A[c] = [v / piv for v in A[c]]
        for r in range(n):
            if r != c:
                f = A[r][c]
                A[r] = [v - f * w for v, w in zip(A[r], A[c])]
    return [row[n:] for row in A]


def q_stat(sum_y, m, Vinv, mu):
    d = [s / m - u for s, u in zip(sum_y, mu)]
    return m * sum(d[i] * Vinv[i][j] * d[j] for i in range(K) for j in range(K))


def order_stat_test(draws, mc=2000, seed=1):
    m = len(draws)
    mu = [(N + 1) * i / (K + 1) for i in range(1, K + 1)]  # Eq.9
    Vinv = _inverse(_cov())
    sum_y = [sum(d[i] for d in draws) for i in range(K)]
    Q = q_stat(sum_y, m, Vinv, mu)
    p_clt = chi2_sf(Q, K)  # Q ~ chi2(K) (Eq.12)
    rnd = random.Random(seed)
    pop = range(1, N + 1)
    ge = 0
    for _ in range(mc):
        s = [0] * K
        for _ in range(m):
            for i, v in enumerate(sorted(rnd.sample(pop, K))):
                s[i] += v
        ge += q_stat(s, m, Vinv, mu) >= Q
    return Q, p_clt, (ge + 1) / (mc + 1)


def freq_test(draws):
    """Chi-square tần suất ĐÃ HIỆU CHỈNH: X2*(N-1)/(N-K) ~ chi2(N-1).
    (Mỗi kỳ bốc không hoàn lại nên Var(đếm) nhỏ hơn đa thức; X2 thô có kỳ vọng N-K, không phải N-1.)"""
    m = len(draws)
    e = m * K / N
    f = freq(draws)
    x2 = sum((c - e) ** 2 / e for c in f.values())
    adj = x2 * (N - 1) / (N - K)
    return x2, adj, chi2_sf(adj, N - 1)


# ---------- backtest ----------
def predictor(name, hist, rnd):
    if name == "random":
        return set(rnd.sample(range(1, N + 1), K))
    f = freq(hist)
    order = sorted(range(1, N + 1), key=lambda i: (f[i], i), reverse=(name != "cold"))
    return set(order[:K])  # hot = cdm (xem ghi chú trong SKILL.md)


def backtest(draws, warm=50, seed=1):
    rnd = random.Random(seed)
    T = len(draws) - warm
    if T < 30:
        sys.exit("Cần >= 80 kỳ để backtest có nghĩa.")
    mean0 = K * K / N
    var0 = K * (K / N) * (1 - K / N) * (N - K) / (N - 1)  # phương sai siêu bội
    print(f"Số kỳ đánh giá: {T}. Kỳ vọng trùng/kỳ nếu ngẫu nhiên: {mean0:.3f} (sd/kỳ {var0**.5:.3f})")
    for name in ("random", "hot", "cold"):
        hits = [len(predictor(name, draws[:t], rnd) & set(draws[t])) for t in range(warm, len(draws))]
        mean = sum(hits) / T
        z = (mean - mean0) / math.sqrt(var0 / T)
        p = math.erfc(abs(z) / math.sqrt(2))
        print(f"  {name:6s} trung bình {mean:.3f}  z={z:+.2f}  p={p:.3f}"
              + ("  <- có lợi thế?" if p < 0.01 else ""))
    print("Lưu ý: chạy nhiều chiến lược => p nhỏ ngẫu nhiên; dùng ngưỡng nghiêm (Bonferroni) và dữ liệu mới để kiểm lại.")


# ---------- lệnh ----------
def cmd_parse(a):
    rows = parse_text(open(a.raw, encoding="utf-8").read() if a.raw != "-" else sys.stdin.read())
    w = csv.writer(sys.stdout)
    w.writerow(["ngay"] + [f"n{i}" for i in range(1, K + 1)] + ["ky"])
    for ky, d, nums in rows:
        w.writerow([d] + nums + [ky])
    print(f"# {len(rows)} kỳ", file=sys.stderr)


def cmd_odds(_):
    print(f"Tổng tổ hợp: {TOTAL:,}")
    for k in range(K, -1, -1):
        p = p_match(k)
        print(f"Trúng {k}/6: {p:.8f}  (~1/{1 / p:,.0f})")


def cmd_stats(a):
    draws = load(a.csv, limit=a.n)
    m = len(draws)
    f = freq(draws)
    ranked = sorted(f.items(), key=lambda x: (-x[1], x[0]))
    print(f"Số kỳ phân tích: {m} | kỳ vọng mỗi số: {m * K / N:.1f}")
    if m < 100:
        print("CẢNH BÁO: < 100 kỳ, kết quả kiểm định không đáng tin.")
    print("Nóng:", ranked[:6], "\nLạnh:", ranked[-6:])
    x2, adj, p = freq_test(draws)
    print(f"[Tần suất] X2 thô={x2:.1f}, hiệu chỉnh={adj:.1f} (df={N - 1}), p={p:.3f}")
    Q, pc, pm = order_stat_test(draws, mc=a.mc)
    print(f"[Thống kê thứ tự] Q={Q:.2f} (df={K}), p_CLT={pc:.3f}, p_MonteCarlo={pm:.3f}")
    print("p < 0.01 mới là dấu hiệu lệch khỏi công bằng (bài 0806.4595 tìm thấy ở 2/8 giai đoạn "
          "dữ liệu Mexico/Ý); p lớn = không bằng chứng lệch, KHÔNG phải bằng chứng dự đoán được.")


def cmd_backtest(a):
    draws = load(a.csv, limit=a.n)
    backtest(draws, warm=a.warm)


def cmd_pick(a):
    csv_file = a.csv if a.csv else (str(DEFAULT_CSV) if DEFAULT_CSV.exists() else None)
    f = freq(load(csv_file)) if csv_file else {i: 0 for i in range(1, N + 1)}
    pool = list(range(1, N + 1))
    m = max(f.values()) if f else 0
    w = {"random": [1] * N, "hot": [f[i] + 1 for i in pool],
         "cold": [m - f[i] + 1 for i in pool]}[a.mode]
    for _ in range(a.n):
        s = set()
        while len(s) < K:
            s.add(random.choices(pool, w)[0])
        print(sorted(s))
    print(f"Mọi bộ số đều có xác suất jackpot 1/{TOTAL:,}; EV mỗi vé < 0.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(required=True)
    p = sp.add_parser("parse"); p.add_argument("raw"); p.set_defaults(fn=cmd_parse)
    sp.add_parser("odds").set_defaults(fn=cmd_odds)
    p = sp.add_parser("stats")
    p.add_argument("csv", nargs="?", default=None, help="File CSV kết quả (mặc định lấy draws.csv cùng thư mục)")
    p.add_argument("-n", "--n", type=int, default=300, help="Số kỳ gần nhất cần kiểm định (mặc định 300)")
    p.add_argument("--mc", type=int, default=2000)
    p.set_defaults(fn=cmd_stats)
    
    p = sp.add_parser("backtest")
    p.add_argument("csv", nargs="?", default=None, help="File CSV kết quả (mặc định lấy draws.csv cùng thư mục)")
    p.add_argument("-n", "--n", type=int, default=300, help="Số kỳ gần nhất cần backtest (mặc định 300)")
    p.add_argument("--warm", type=int, default=50)
    p.set_defaults(fn=cmd_backtest)
    
    p = sp.add_parser("pick")
    p.add_argument("--mode", default="random", choices=["random", "hot", "cold"])
    p.add_argument("-n", "--n", type=int, default=1, help="Số lượng bộ số cần sinh")
    p.add_argument("--csv", default=None, help="File CSV kết quả để tính trọng số hot/cold (mặc định draws.csv)")
    p.set_defaults(fn=cmd_pick)
    
    a = ap.parse_args()
    a.fn(a)
