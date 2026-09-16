# -*- coding: utf-8 -*-
"""build/strategy_diag.py — 게시 규칙 진단 셋 → data/strategy_diag.json

무엇을 붙이나(사용자 요청 2026-09-15 «이 진단들을 랩의 게시 규칙에 붙여»).
  블로그 논문 재현(스크래치패드)에서 전략마다 돌린 진단 셋을 **게시 규칙 전부**(strategy_index
  items)에 같은 식으로 잰다. 판정이 아니다 — 판정은 여전히 기각/게시/측정만/보류 넷뿐이다.

  ① 시장 상태 삼분위  형성월(보유 직전 월말) 시장 변수 8개로 달을 셋으로 나눠 보유월 초과수익 평균.
                      상−하 차이는 NW t(시차 3). 규칙 × 변수 전체에 BH FDR 10% 를 한 번에 건다.
  ② 급등락 12구간     사용자가 준 고정 구간표(data/market_episodes.json). 곡선에 경계값(chart.epi —
                      tech_backtest.curve_pack 이 전체 일간 계열에서 집은 값)이 있으면 **시작일 → 끝일**로
                      정확히 잰다. 없으면 시작월 ~ 끝월 월 복리로 재고 «월 격자» 로 표시한다.
                      🚨 월 격자는 짧은 구간을 못 잰다 — QE 랠리 S&P 500 이 일간 +30.9% 인데 3~6월 창은 +5.0%.
                      구간당 1회라 사례이지 검정이 아니다.
  ③ 평균 변화점       초과수익 r = a + b·1(t ≥ τ) · τ 는 표본 15~85% · Wald(NW) 최대 ·
                      Andrews(1993) q=1 π0=0.15 임계 10% 7.12 · 5% 8.68 · 1% 12.16.

원천(전부 커밋된 파일 — 러너가 똑같이 굽는다).
  · 규칙 곡선     data/strategy_charts.json 의 monthly(r·b·i)·epi — 카드가 그리는 그 계열이다.
                  🚨 strategy_index 의 국면 칸(rg)은 tech_strategies(소급)에서 재는데 카드 곡선은
                     대개 시점정확(pit_strategies)이다. 여기서는 **카드 곡선과 같은 계열**을 쓴다.
  · 시장 변수     S&P 500 가격(bench_px) · 편입 종목(index_history 월말 명단) × 가격(tech_backtest.load)
                  × 주식수(tech_backtest.load_fund + fx_pit) · 금리(rates.json DGS10·DGS3MO)
                  ⚠ 로컬 캐시(_pit_px_cache · _pit_sh_cache)는 읽지 않는다. 읽으면 PC 와 러너가
                    다른 수를 굽고 커밋마다 값이 흔들린다.
  · 지수 일간     data/bench_px.json (spx · ndx, 가격지수) — 구간표 참고값

⚠ 표준 라이브러리만 쓴다. ci_push.sh REBAKE_TABLE 에 올라가는 파일이라 세 잡(stocks·assets·tech)
  어디서든 다시 구워져야 하는데 잡마다 pip 목록이 다르다.

  python build/strategy_diag.py
"""
from __future__ import annotations
import bisect
import datetime as dt
import io
import json
import math
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_diag.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VARS = (("mkt12", "추세", "S&P 500 12개월 수익"),
        ("vol1", "변동성", "S&P 500 최근 21거래일 실현변동성(연율)"),
        ("disp", "분산", "S&P 500 편입 종목 그 달 수익의 횡단면 표준편차"),
        ("conc", "집중도", "S&P 500 시총 상위 10종 비중"),
        ("dconc12", "집중변화", "집중도의 12개월 변화"),
        ("breadth12", "폭", "편입 종목 동일가중 − 시총가중 12개월 누적 수익"),
        ("rate12", "금리변화", "10년물 금리 12개월 변화(%p)"),
        ("curve", "곡선", "10년물 − 3개월물(%p)"))
MIN_TERC = 36          # 삼분위 한 칸에 12개월은 들어가야 평균이라 부를 수 있다
MIN_BREAK = 60
TRIM = 0.15
NW_LAG = 3
ANDREWS = ((12.16, "1%"), (8.68, "5%"), (7.12, "10%"))
FDR_Q = 0.10
MAX_GAP = 7            # 경계값을 집은 날짜가 구간 날짜에서 이만큼(달력일)보다 멀면 정확 측정으로 안 친다


def load(fn):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def load_episodes():
    j = load("market_episodes.json") or {}
    return [(e["k"], e["nm"], e.get("why") or "", e["a"], e["b"]) for e in (j.get("episodes") or [])], j.get("src")


# ── 작은 통계 도구(표준 라이브러리) ──────────────────────────────────────────
def _inv(A):
    n = len(A)
    M = [list(map(float, row)) + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-14:
            return None
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        M[c] = [v / pv for v in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [row[n:] for row in M]


def nw_ols(y, cols, lag=NW_LAG):
    """y = a + Σ b·col. Newey–West(바틀렛) 표준오차. (계수, t) — 못 풀면 (None, None)."""
    n = len(y)
    X = [[1.0] + [c[i] for c in cols] for i in range(n)]
    p = len(X[0])
    Q = _inv([[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p)] for a in range(p)])
    if Q is None:
        return None, None
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(p)]
    b = [sum(Q[a][c] * Xty[c] for c in range(p)) for a in range(p)]
    g = [[X[i][a] * (y[i] - sum(X[i][k] * b[k] for k in range(p))) for a in range(p)] for i in range(n)]
    S = [[sum(g[i][a] * g[i][c] for i in range(n)) for c in range(p)] for a in range(p)]
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1.0)
        for a in range(p):
            for c in range(p):
                S[a][c] += w * sum(g[i][a] * g[i - L][c] + g[i - L][a] * g[i][c] for i in range(L, n))
    QS = [[sum(Q[a][k] * S[k][c] for k in range(p)) for c in range(p)] for a in range(p)]
    V = [[sum(QS[a][k] * Q[k][c] for k in range(p)) for c in range(p)] for a in range(p)]
    t = [(b[a] / math.sqrt(V[a][a])) if V[a][a] > 0 else None for a in range(p)]
    return b, t


def pct(xs, q):
    s = sorted(xs)
    pos = (len(s) - 1) * q / 100.0
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _sd(xs):
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else float("nan")


def _r(x, k=4):
    return None if (x is None or not isinstance(x, (int, float)) or not math.isfinite(x)) else round(x, k)


def _days(a, b):
    return abs((dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days)


# ── ① 시장 변수 ────────────────────────────────────────────────────────────
def market_state():
    import tech_backtest as TB
    D, px, _v, _h, _l, _meta, _rf = TB.load(full=True)
    N = len(D)
    uni = set(px)
    di = {d: i for i, d in enumerate(D)}
    pit = load("pit_px.json") or {}
    pds = pit.get("dates") or []
    for t, v in (pit.get("px") or {}).items():
        if t in px:
            continue
        a = [None] * N
        for k, p in enumerate(v.get("p") or []):
            j = (v.get("i0") or 0) + k
            if j < len(pds) and pds[j] in di:
                a[di[pds[j]]] = p
        px[t] = a
    pitset = set((pit.get("px") or {}))
    H = load("index_history.json") or {}
    MH, t2c = H.get("months") or {}, H.get("cik") or {}
    c2u = {}
    for u in sorted(uni):
        c = t2c.get(u)
        if c:
            c2u.setdefault(c, u)

    def key(t):
        if t in uni:
            return t
        u = c2u.get(t2c.get(t))
        if u:
            return u
        return t if (t in pitset and t in px) else None

    FU = TB.load_fund(extra_dirs=[os.path.join(DATA, "fx_pit")])
    me = {}
    for i, d in enumerate(D):
        me[d[:7]] = i
    allm = sorted(me)
    mpos = {m: q for q, m in enumerate(allm)}
    months = [m for m in sorted(MH) if m in me and mpos[m] >= 1]

    def good(k, i):
        p = px.get(k)
        return p is not None and i < len(p) and p[i] is not None and p[i] > 0

    MC = {}
    for m in months:
        i = me[m]
        byc = {}
        for t in (MH[m].get("spx") or []):
            k = key(t)
            if not k or not good(k, i):
                continue
            f = FU.get(k) or FU.get(t)
            sn = TB.asof_fund(f.get("sh"), D[i]) if f else None
            if not sn or sn <= 0:
                continue
            byc.setdefault(t2c.get(t) or ("k:" + k), []).append((k, sn * px[k][i]))
        mc = {}
        for L in byc.values():                      # 다종 주식은 한 회사 시총을 종목 수로 나눈다
            tot = max(v for _, v in L)
            for k, _ in L:
                mc[k] = mc.get(k, 0.0) + tot / len(L)
        MC[m] = mc

    B = load("bench_px.json") or {}
    bd = B.get("dates") or []
    spx = (B.get("series") or {}).get("spx", {}).get("px") or []

    def bpx_at(d):
        j = bisect.bisect_right(bd, d) - 1
        while j >= 0 and not spx[j]:
            j -= 1
        return (spx[j], j) if j >= 0 else (None, None)

    R = load("rates.json") or {}
    rds = R.get("dates") or []

    def rate(code, d):
        s = (R.get("series") or {}).get(code) or []
        j = bisect.bisect_right(rds, d) - 1
        while j >= 0 and (j >= len(s) or s[j] is None):
            j -= 1
        return s[j] if j >= 0 else None

    ew, cw, rows = {}, {}, {}
    for m in months:
        pm = allm[mpos[m] - 1]
        i0, i1 = me[pm], me[m]
        if pm in MC and MC[pm]:
            rr = [(px[k][i1] / px[k][i0] - 1, w) for k, w in MC[pm].items() if good(k, i0) and good(k, i1)]
            if rr:
                ew[m] = sum(r for r, _ in rr) / len(rr)
                cw[m] = sum(r * w for r, w in rr) / sum(w for _, w in rr)
    for m in months:
        i = me[m]
        pm = allm[mpos[m] - 1]
        m12 = allm[mpos[m] - 12] if mpos[m] >= 12 else None
        v = {}
        p1, j1 = bpx_at(D[i])
        p0, _ = bpx_at(D[me[m12]]) if m12 else (None, None)
        v["mkt12"] = (p1 / p0 - 1) if (p1 and p0) else None
        if j1 is not None and j1 >= 21:
            seg = [spx[q] for q in range(j1 - 21, j1 + 1)]
            if all(seg):
                v["vol1"] = _sd([seg[q + 1] / seg[q] - 1 for q in range(21)]) * math.sqrt(252)
        mc = MC.get(m) or {}
        rr = [px[k][i] / px[k][me[pm]] - 1 for k in mc if good(k, me[pm])]
        v["disp"] = _sd(rr) if len(rr) > 30 else None
        if len(mc) > 30:
            wv = sorted(mc.values(), reverse=True)
            v["conc"] = sum(wv[:10]) / sum(wv)
        if m12 and rows.get(m12, {}).get("conc") is not None and v.get("conc") is not None:
            v["dconc12"] = v["conc"] - rows[m12]["conc"]
        last12 = [allm[mpos[m] - q] for q in range(12)] if mpos[m] >= 11 else []
        if last12 and all(x in ew for x in last12):
            v["breadth12"] = math.prod(1 + ew[x] for x in last12) - math.prod(1 + cw[x] for x in last12)
        y10, y3 = rate("DGS10", D[i]), rate("DGS3MO", D[i])
        y10p = rate("DGS10", D[me[m12]]) if m12 else None
        v["rate12"] = (y10 - y10p) if (y10 is not None and y10p is not None) else None
        v["curve"] = (y10 - y3) if (y10 is not None and y3 is not None) else None
        rows[m] = v
    return rows


# ── ②·③ 규칙별 진단 ──────────────────────────────────────────────────────
def episode_meta(EPIS):
    B = load("bench_px.json") or {}
    bd = B.get("dates") or []
    out = []
    for k, nm, why, a, b in EPIS:
        def daily(code):
            s = (B.get("series") or {}).get(code, {}).get("px") or []
            i, j = bisect.bisect_right(bd, a) - 1, bisect.bisect_right(bd, b) - 1
            return (s[j] / s[i] - 1) * 100 if (i >= 0 and j >= 0 and s[i] and s[j]) else None
        out.append({"k": k, "nm": nm, "why": why, "a": a, "b": b, "days": _days(a, b),
                    "mw": [a[:7], b[:7]], "spx_d": _r(daily("spx"), 2), "ndx_d": _r(daily("ndx"), 2)})
    return out


def month_span(m0, m1):
    y, mo = int(m0[:4]), int(m0[5:])
    out = []
    while True:
        s = "%04d-%02d" % (y, mo)
        out.append(s)
        if s >= m1:
            return out
        mo += 1
        if mo > 12:
            y, mo = y + 1, 1


def prev_month(m):
    y, mo = int(m[:4]), int(m[5:])
    return "%04d-%02d" % ((y, mo - 1) if mo > 1 else (y - 1, 12))


def _episodes(chart, rows, basis, EPIS):
    """구간마다 {g, r, b, x, s, n, at}. g='d' 경계값(일간·주간) · g='m' 월 격자. 못 재면 None."""
    ce = chart.get("epi") or {}
    pos = {d: q for q, d in enumerate(ce.get("d") or [])}
    vals = ce.get("v") or []
    mm = {x["m"]: x for x in rows}
    out = []
    for _k, _nm, _why, a, b in EPIS:
        va = vals[pos[a]] if a in pos and pos[a] < len(vals) else None
        vb = vals[pos[b]] if b in pos and pos[b] < len(vals) else None
        if va and vb and va[0] < vb[0] and _days(va[0], a) <= MAX_GAP and _days(vb[0], b) <= MAX_GAP \
                and va[1] and va[2]:
            ia, ib = (va[3] if len(va) > 3 else {}), (vb[3] if len(vb) > 3 else {})
            ret = lambda x, y: _r((y / x - 1) * 100, 2) if (x and y) else None
            e = {"g": "d", "r": ret(va[1], vb[1]), "b": ret(va[2], vb[2]),
                 "s": ret(ia.get("S&P 500"), ib.get("S&P 500")), "n": ret(ia.get("NASDAQ 100"), ib.get("NASDAQ 100")),
                 "at": [va[0], vb[0]]}
        else:
            ms = month_span(a[:7], b[:7])
            if not all(m in mm for m in ms):
                out.append(None)
                continue
            comp = lambda f: _r((math.prod(1 + f(mm[m]) / 100 for m in ms) - 1) * 100, 2) \
                if all(isinstance(f(mm[m]), (int, float)) for m in ms) else None
            e = {"g": "m", "r": comp(lambda x: x["r"]),
                 "b": comp((lambda x: x.get("b")) if basis == "b" else (lambda x: (x.get("i") or {}).get("S&P 500"))),
                 "s": comp(lambda x: (x.get("i") or {}).get("S&P 500")),
                 "n": comp(lambda x: (x.get("i") or {}).get("NASDAQ 100")), "at": [ms[0], ms[-1]]}
        if basis != "b" and e["g"] == "d":
            e["b"] = e["s"]
        e["x"] = _r(e["r"] - e["b"], 2) if (e["r"] is not None and e["b"] is not None) else None
        out.append(e)
    return out


def rule_diag(chart, end, state, EPIS):
    rows = [x for x in (chart.get("monthly") or []) if x.get("m") and x["m"] <= end and isinstance(x.get("r"), (int, float))]
    basis = "b" if all(isinstance(x.get("b"), (int, float)) for x in rows) else "S&P 500"
    ser = []
    for x in rows:
        bv = x.get("b") if basis == "b" else (x.get("i") or {}).get("S&P 500")
        if isinstance(bv, (int, float)):
            ser.append((x["m"], x["r"], bv))
    xs = [(m, r - b) for m, r, b in ser]
    out = {"basis": basis, "n": len(xs), "span": [xs[0][0], xs[-1][0]] if xs else None}
    flat = sum(1 for _, v in xs if abs(v) < 1e-9)
    out["flat"] = flat                    # 대조군과 수익이 같은 달 — 타이밍 오버레이가 꺼져 있던 달
    live = len(xs) - flat >= MIN_TERC

    # ① 삼분위
    terc = []
    for k, _ko, _df in VARS:
        pairs = [(state[prev_month(m)][k], v) for m, v in xs
                 if state.get(prev_month(m), {}).get(k) is not None]
        if not live or len(pairs) < MIN_TERC:
            terc.append({"k": k, "n": len(pairs)})
            continue
        s = [p for p, _ in pairs]
        c1, c2 = pct(s, 100 / 3), pct(s, 200 / 3)
        g = [0 if p <= c1 else (1 if p <= c2 else 2) for p in s]
        y = [v for _, v in pairs]
        nn = [sum(1 for z in g if z == q) for q in range(3)]
        means = [sum(y[i] for i in range(len(y)) if g[i] == q) / max(1, nn[q]) for q in range(3)]
        b, t = nw_ols(y, [[1.0 if z == 1 else 0.0 for z in g], [1.0 if z == 2 else 0.0 for z in g]])
        terc.append({"k": k, "n": len(pairs), "cut": [_r(c1, 4), _r(c2, 4)],
                     "lo": _r(means[0], 3), "mid": _r(means[1], 3), "hi": _r(means[2], 3), "nn": nn,
                     "d": _r(b[2], 3) if b else None, "t": _r(t[2], 2) if (t and t[2] is not None) else None})
    out["terc"] = terc

    # ② 급등락
    out["epi"] = _episodes(chart, rows, basis, EPIS)
    summ = {}
    for kind in ("dn", "up"):
        ex = [e["x"] for e, E in zip(out["epi"], EPIS) if e is not None and e["x"] is not None and E[0] == kind]
        summ[kind] = {"n": len(ex), "avg": _r(sum(ex) / len(ex), 2) if ex else None, "pos": sum(1 for v in ex if v > 0)}
    summ["grid_d"] = sum(1 for e in out["epi"] if e and e["g"] == "d")
    summ["grid_m"] = sum(1 for e in out["epi"] if e and e["g"] == "m")
    out["epi_sum"] = summ

    # ③ 변화점
    if live and len(xs) >= MIN_BREAK:
        y = [v for _, v in xs]
        n = len(y)
        best = None
        for q in range(int(TRIM * n), int((1 - TRIM) * n) + 1):
            _b, t = nw_ols(y, [[1.0 if j >= q else 0.0 for j in range(n)]])
            if t is None or t[1] is None:
                continue
            w = t[1] ** 2
            if best is None or w > best[0]:
                best = (w, q)
        if best:
            w, q = best
            lvl = next((lab for crit, lab in ANDREWS if w > crit), None)
            out["brk"] = {"tau": xs[q][0], "w": _r(w, 2), "lvl": lvl,
                          "pre": _r(sum(y[:q]) / q, 3), "post": _r(sum(y[q:]) / (n - q), 3),
                          "n_pre": q, "n_post": n - q}
    return out


def main() -> int:
    EPIS, epi_src = load_episodes()
    if len(EPIS) != 12:
        print("  ⚠ data/market_episodes.json 구간이 %d개다(12개여야 한다)" % len(EPIS))
    si = load("strategy_index.json") or {}
    cj = load("strategy_charts.json") or {}
    charts = cj.get("charts") or {}
    items = [x for x in (si.get("items") or []) if isinstance(x, dict) and x.get("sid")]
    state = market_state()
    sm = sorted(m for m in state if any(v is not None for v in state[m].values()))
    print("시장 변수 %s ~ %s · %d개월 · 변수별 값 있는 달: %s"
          % (sm[0], sm[-1], len(sm), " ".join("%s %d" % (ko, sum(1 for m in sm if state[m].get(k) is not None)) for k, ko, _ in VARS)))

    rules, miss = {}, []
    for it in items:
        c = charts.get(it["sid"])
        if not c or not c.get("monthly"):
            miss.append(it["sid"])
            continue
        rules[it["sid"]] = rule_diag(c, (it.get("end") or "9999-12")[:7], state, EPIS)
        rules[it["sid"]]["name"] = it.get("name")

    # BH FDR — 규칙 × 변수 전부를 한 가족으로
    tests = [(sid, q, rr["terc"][q]["t"]) for sid, rr in rules.items() for q in range(len(VARS))
             if rr["terc"][q].get("t") is not None]
    ps = sorted(((math.erfc(abs(t) / math.sqrt(2)), sid, q) for sid, q, t in tests), key=lambda z: z[0])
    kmax = 0
    for rank, (p, _s, _q) in enumerate(ps, 1):
        if p <= rank / len(ps) * FDR_Q:
            kmax = rank
    for rank, (p, sid, q) in enumerate(ps, 1):
        rules[sid]["terc"][q]["p"] = _r(p, 4)
        rules[sid]["terc"][q]["fdr"] = rank <= kmax
    nbrk = {lab: sum(1 for r in rules.values() if (r.get("brk") or {}).get("lvl") == lab) for _, lab in ANDREWS}
    gd = sum(r["epi_sum"]["grid_d"] for r in rules.values())
    gm = sum(r["epi_sum"]["grid_m"] for r in rules.values())

    doc = {
        "note": "게시 규칙 진단 — 시장 상태 삼분위 · 급등락 12구간 · 평균 변화점. 판정이 아니라 서술이다. "
                "규칙 곡선은 strategy_charts.json(카드가 그리는 계열), 초과는 판정 기준(b) 대비.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # 🚨 같은 실행 대조용 — 차트를 다시 굽고 이것을 안 구우면 validate_site 가 잡는다.
        "charts_generated": cj.get("generated"),
        "vars": [{"k": k, "ko": ko, "def": df} for k, ko, df in VARS],
        "state_span": [sm[0], sm[-1]],
        "state": {m: {k: _r(v, 5) for k, v in state[m].items()} for m in sm},
        "episodes": episode_meta(EPIS),
        "episodes_src": epi_src,
        "epi_note": "g=d 는 곡선 전체 계열에서 구간 시작일·끝일 값을 집어 잰 것(at = 실제로 집은 날짜), "
                    "g=m 은 경계값이 없어 시작월~끝월 월 복리로 잰 것 — 짧은 구간은 월 격자로 못 잰다. 구간당 1회라 사례다.",
        "epi_grid": {"d": gd, "m": gm},
        "terc_note": "형성월 변수를 그 규칙 표본 안에서 삼분위로 나눈 보유월 초과수익(%%/월) 평균. 상−하 차이 NW t(시차 %d). "
                     "규칙×변수 %d개에 BH FDR %.0f%% — 살아남은 칸 %d개." % (NW_LAG, len(ps), 100 * FDR_Q, kmax),
        "brk_note": "평균 변화점 sup-Wald(15%% 절단 · NW 시차 %d) · Andrews 임계 10%% 7.12 · 5%% 8.68 · 1%% 12.16. "
                    "변화점 날짜는 표본에서 고른 것이라 그 날짜 자체를 사건으로 읽으면 안 된다." % NW_LAG,
        "fdr": {"q": FDR_Q, "m": len(ps), "k": kmax},
        "n": len(rules), "miss": miss,
        "rules": rules,
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("규칙 %d개 진단 · 차트 없음 %d · 삼분위 검정 %d개 중 FDR 10%% 통과 %d · 변화점 1%% %d · 5%% %d · 10%% %d · "
          "구간 경계값 %d / 월 격자 %d · %.0fKB"
          % (len(rules), len(miss), len(ps), kmax, nbrk["1%"], nbrk["5%"], nbrk["10%"], gd, gm, os.path.getsize(OUT) / 1024))
    if miss:
        print("  ⚠ 차트가 없어 못 잰 규칙: %s" % ", ".join(miss))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
