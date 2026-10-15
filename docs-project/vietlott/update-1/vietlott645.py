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
import argparse, csv, math, random, re, sys
from collections import Counter
from math import comb, exp, factorial

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


def load(path):
    draws = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            try:
                nums = sorted(int(x) for x in row[1:1 + K])
            except ValueError:
                continue  # header
            if len(nums) == K and all(1 <= n <= N for n in nums):
                draws.append(nums)
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


# ---------- EV: giá trị kỳ vọng mỗi vé ----------
PRICE = 10_000
PRIZE = {5: 10_000_000, 4: 300_000, 3: 30_000}  # Nhất / Nhì / Ba (cố định) - đối chiếu thể lệ hiện hành
TAX_RATE, TAX_FREE = 0.10, 10_000_000           # TNCN 10% phần trúng thưởng vượt 10 triệu / giải


def vn(x):
    return f"{x:,.0f}".replace(",", ".")


def vf(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


def after_tax(x, tax=True):
    return x - TAX_RATE * max(0.0, x - TAX_FREE) if tax else x


def ev_secondary():
    """EV/vé từ giải Nhất+Nhì+Ba (mỗi giải <= 10 triệu nên không chịu thuế)."""
    return sum(PRIZE[k] * p_match(k) for k in PRIZE)


def poisson_pmf(x, lam):
    if lam <= 0:
        return 1.0 if x == 0 else 0.0
    return exp(-lam + x * math.log(lam) - math.lgamma(x + 1))


def ev_jackpot(J, lam, tax=True):
    """EV/vé từ jackpot J (đồng). Chia đều cho 1+X người trúng, X ~ Poisson(lam) là số người trúng KHÁC.
    Thuế áp lên phần mỗi người nhận được, nên lấy kỳ vọng của after_tax(J/(1+X))."""
    top = int(lam + 12 * math.sqrt(lam + 1) + 30)
    tot = sum(poisson_pmf(x, lam) * after_tax(J / (1 + x), tax) for x in range(top))
    return p_match(K) * tot


def ev_total(J, lam, tax=True):
    return ev_secondary() + ev_jackpot(J, lam, tax)


def breakeven(lam_of_J, tax=True, price=PRICE):
    """Jackpot nhỏ nhất (đồng) để EV >= giá vé; lam_of_J: hàm J -> lam. None nếu không đạt tới 1e14."""
    lo, hi = 1e9, 1e14
    if ev_total(hi, lam_of_J(hi), tax) < price:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if ev_total(mid, lam_of_J(mid), tax) >= price:
            hi = mid
        else:
            lo = mid
    return hi


def load_full(path):
    """draws.csv đầy đủ: ngay,n1..n6,ky[,jackpot,w_jackpot,w_nhat,w_nhi,w_ba]. Trả list dict (None nếu thiếu)."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.reader(f):
            try:
                nums = sorted(int(x) for x in r[1:1 + K])
                ky = int(r[7])
            except (ValueError, IndexError):
                continue

            def g(i, r=r):
                try:
                    return int(r[i])
                except (ValueError, IndexError):
                    return None
            out.append({"ngay": r[0], "nums": nums, "ky": ky,
                        "jackpot": g(8), "wj": g(9), "w1": g(10), "w2": g(11), "w3": g(12)})
    return out


def tickets_hat(row):
    """Ước lượng số vé bán (MLE Poisson): tổng số giải 3..6 / tổng xác suất tương ứng.
    Thiên lệch nếu bộ số quay ra được nhiều người chọn (vd nhiều số <= 31)."""
    w = [row["wj"], row["w1"], row["w2"], row["w3"]]
    if any(x is None for x in w):
        return None
    t = sum(w) / sum(p_match(k) for k in (6, 5, 4, 3))
    return t if t > 0 else None


def fit_sales(rows, min_n=30):
    """Hồi quy ln(số vé) = a + b*ln(jackpot). Trả None nếu < min_n kỳ có đủ dữ liệu."""
    pts = []
    for r in rows:
        t = tickets_hat(r)
        if t and r["jackpot"] and r["jackpot"] > 0:
            pts.append((math.log(r["jackpot"]), math.log(t)))
    n = len(pts)
    if n < min_n:
        return None
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in pts) / sxx
    a = my - b * mx
    res = [y - (a + b * x) for x, y in pts]
    sd = math.sqrt(sum(e * e for e in res) / (n - 2))
    sst = sum((y - my) ** 2 for _, y in pts)
    r2 = 1 - sum(e * e for e in res) / sst if sst else 0.0
    return {"a": a, "b": b, "sd": sd, "r2": r2, "n": n}


def cmd_ev(a):
    tax = not a.no_tax
    p6 = p_match(K)
    sec = ev_secondary()
    J = a.jackpot_ty * 1e9 if a.jackpot_ty else None
    print(f"Vé {vn(a.price)}đ | giải phụ cố định (Nhất+Nhì+Ba): {vn(sec)}đ/vé"
          f" | thuế TNCN {'10% phần > 10 triệu' if tax else 'bỏ qua'}")
    print(f"Hòa vốn khi chưa chia giải, chưa thuế: jackpot >= {vf((a.price - sec) / p6 / 1e9)} tỷ")

    scen = []  # (nhãn, hàm J -> lam)
    rows_p = []
    if a.csv:
        rows = load_full(a.csv)
        rows_p = [r for r in rows if tickets_hat(r)]
        if not rows_p:
            print("CẢNH BÁO: csv chưa có cột jackpot/số giải. Chạy: python vl_fetch.py --enrich")
        else:
            ts = sorted(tickets_hat(r) for r in rows_p)
            med = ts[len(ts) // 2]
            last = rows_p[-1]
            print(f"Dữ liệu: {len(rows_p)} kỳ có số giải. Số vé ước lượng: trung vị ≈ {vn(med)}"
                  f" (λ≈{vf(med * p6, 2)}); kỳ #{last['ky']:05d} ≈ {vn(tickets_hat(last))} vé.")
    if a.lam is not None:
        scen.append((f"λ={vf(a.lam, 2)} (cho trước)", lambda _J, l=a.lam: l))
    elif a.tickets is not None:
        l = a.tickets * p6
        scen.append((f"{vn(a.tickets)} vé → λ={vf(l, 2)}", lambda _J, l=l: l))
    elif rows_p:
        fit = fit_sales(rows_p)
        if fit:
            print(f"Mô hình bán vé: ln(vé) = {vf(fit['a'], 2)} + {vf(fit['b'], 2)}·ln(jackpot)"
                  f"  (R²={vf(fit['r2'], 2)}, n={fit['n']}, sd dư={vf(fit['sd'], 2)})")
            for lab, z in (("λ thấp (P10)", -1.2816), ("λ ước lượng", 0.0), ("λ cao (P90)", 1.2816)):
                scen.append((lab, lambda Jx, z=z: exp(fit["a"] + fit["b"] * math.log(Jx) + z * fit["sd"]) * p6))
        else:
            ts = sorted(tickets_hat(r) for r in rows_p)
            l = ts[len(ts) // 2] * p6
            print(f"(< 30 kỳ đủ dữ liệu: dùng λ trung vị = {vf(l, 2)}, không mô hình hóa theo jackpot)")
            scen.append((f"λ trung vị={vf(l, 2)}", lambda _J, l=l: l))
    else:
        for l in (0.1, 0.5, 1.0, 2.0):
            scen.append((f"λ={vf(l, 1)}", lambda _J, l=l: l))

    print()
    for lab, fn in scen:
        be = breakeven(fn, tax, a.price)
        be_s = f"hòa vốn khi jackpot >= {vf(be / 1e9, 0)} tỷ" if be else "không hòa vốn ở mọi jackpot < 100.000 tỷ"
        if J:
            lam = fn(J)
            ej = ev_jackpot(J, lam, tax)
            tot = sec + ej
            print(f"{lab:<22} λ={vf(lam, 2):>5} → EV {vn(tot)}đ ({vf(100 * tot / a.price)}% giá vé)"
                  f" = giải phụ {vn(sec)} + jackpot {vn(ej)} | {be_s}")
        else:
            print(f"{lab:<22} {be_s}")
    if J:
        print(f"\nJackpot {vf(J / 1e9)} tỷ: theo kịch bản cuối, kỳ vọng mất {vn(a.price - tot)}đ trên mỗi vé {vn(a.price)}đ.")
    print("Giả định: jackpot chia đều; số người trúng khác ~ Poisson (vé chọn đều). Thực tế người chơi chọn số "
          "không đều nên λ ước lượng từ số giải có sai số. Mức giải/thuế ở PRIZE/TAX_* — đối chiếu thể lệ hiện hành.")


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
    draws = load(a.csv)
    m = len(draws)
    f = freq(draws)
    ranked = sorted(f.items(), key=lambda x: (-x[1], x[0]))
    print(f"Số kỳ: {m} | kỳ vọng mỗi số: {m * K / N:.1f}")
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
    backtest(load(a.csv), warm=a.warm)


def cmd_pick(a):
    f = freq(load(a.csv)) if a.csv else {i: 0 for i in range(1, N + 1)}
    pool = list(range(1, N + 1))
    m = max(f.values())
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
    p = sp.add_parser("stats"); p.add_argument("csv"); p.add_argument("--mc", type=int, default=2000); p.set_defaults(fn=cmd_stats)
    p = sp.add_parser("backtest"); p.add_argument("csv"); p.add_argument("--warm", type=int, default=50); p.set_defaults(fn=cmd_backtest)
    p = sp.add_parser("ev", help="EV mỗi vé theo jackpot (xem --help)")
    p.add_argument("--jackpot-ty", type=float, help="jackpot kỳ tới, đơn vị tỷ đồng")
    p.add_argument("--lam", type=float, help="số người trúng jackpot KHÁC kỳ vọng (λ)")
    p.add_argument("--tickets", type=float, help="số vé dự kiến bán ra (λ = vé × P(6/6))")
    p.add_argument("--csv", help="draws.csv có cột jackpot/số giải để ước lượng λ")
    p.add_argument("--no-tax", action="store_true"); p.add_argument("--price", type=int, default=PRICE)
    p.set_defaults(fn=cmd_ev)
    p = sp.add_parser("pick"); p.add_argument("--mode", default="random", choices=["random", "hot", "cold"])
    p.add_argument("--n", type=int, default=1); p.add_argument("--csv"); p.set_defaults(fn=cmd_pick)
    a = ap.parse_args()
    a.fn(a)
