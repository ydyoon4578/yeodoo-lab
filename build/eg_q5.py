# -*- coding: utf-8 -*-
"""build/eg_q5.py — 기대투자성장(Eg · Hou·Mo·Xue·Zhang RoF 2021) 시점정확 검정 → data/_eg_q5.json

사전등록: build/PREREG-2026-09-23-EG.md (계산 전 커밋 cee33124)

원문 3.1절을 랩 자료로 옮긴다 —
  ① 매월 t: 랩이 재무를 가진 전 종목(금융·음(−)자본 제외)에서
       y = (t 에 알려진 I/A) − (t−12 에 알려져 있던 I/A)
     를 t−12 의 [log q, Cop, dRoe] 에 시총가중 WLS 로 회귀(좌우변 1–99% 윈저) → 기울기 b_t
  ② 평균 기울기 = 직전 120개월 b 의 평균(최소 30개월)
  ③ 형성월 t 의 예측 E_t = [1, X_t(윈저)] · 평균 기울기
  ④ 그때의 S&P 500 ∪ NASDAQ 100 멤버(금융 제외)를 E_t 3분위(30/70)로 갈라 시총가중, 다음 달 보유
🚨 원문과 다른 자리(사전등록 §1): Cop ≈ cfo(연간) ÷ 총자산 · dRoe 는 90일 지난 최신 분기 · 회귀 표본은 랩 전 종목.
🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.

  python build/eg_q5.py
"""
from __future__ import annotations
import bisect, io, json, math, os, sys, time
from datetime import date, timedelta

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import index_members as IM            # noqa: E402
import tech_backtest as TB            # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_eg_q5.json")

F0, F1_ = "2016-08", "2026-07"
POST = "2019-01"
REG0 = "2010-01"          # 회귀를 시작하는 달(재무가 2008 무렵부터라 t−12 설명변수가 서는 첫 해)
ROLL, ROLL_MIN = 120, 30
LAG_Q = 90                # dRoe 분기 공시 지연(랩 FUND_LAG_DAYS)
COST = 0.0010
F_T = 1.5
KEEP_DUAL = {"GOOGL", "FOXA", "NWSA"}


def d_(s):
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))


def add_months(dt, k):
    y, m = dt.year + (dt.month - 1 + k) // 12, (dt.month - 1 + k) % 12 + 1
    day = min(dt.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def tstat(v):
    v = np.asarray(v, float)
    if len(v) < 2 or v.std(ddof=1) == 0:
        return None
    return float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v))))


def ols_alpha_t(y, X):
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    s2 = (e @ e) / (len(y) - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    return float(b[0]), float(b[0] / math.sqrt(cov[0, 0]))


def winsor(a, lo=1, hi=99):
    a = np.asarray(a, float)
    ok = ~np.isnan(a)
    if ok.sum() < 5:
        return a
    p1, p99 = np.percentile(a[ok], [lo, hi])
    return np.clip(a, p1, p99)


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra = a.argsort().argsort().astype(float)
    rb = b.argsort().argsort().astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


class Firm:
    """한 회사의 재무 계열(날짜 오름차순). fx/fx_pit 의 태그를 그대로 읽는다."""

    def __init__(self, tg):
        def inst(k):
            v = tg.get(k) or {}
            a = v.get("i") or v.get("q") or []
            return sorted((d_(x[0]), float(x[1])) for x in a if isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float)))

        def flow(k, b):
            v = tg.get(k) or {}
            a = v.get(b) or []
            return sorted((d_(x[0]), float(x[1])) for x in a if isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float)))
        self.asset = inst("asset")
        self.debt = inst("debt")
        self.eq = inst("eq")
        self.ni_q = flow("ni", "q")
        self.ni_a = flow("ni", "a")
        self.cfo_a = flow("cfo", "a")
        self.fy = sorted({d for d, _ in self.ni_a} | {d for d, _ in self.cfo_a})

    @staticmethod
    def at(series, d, tol=12):
        """d 에서 ±tol 일 안의 관측값(가장 가까운 것)."""
        if not series:
            return None
        ds = [x[0] for x in series]
        i = bisect.bisect_left(ds, d)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(ds):
                gap = abs((ds[j] - d).days)
                if gap <= tol and (best is None or gap < best[0]):
                    best = (gap, series[j][1])
        return best[1] if best else None

    def fy_known(self, t):
        """t 에 «4개월 이상 지난» 가장 최근 회계연도말."""
        cut = add_months(t, -4)
        i = bisect.bisect_right(self.fy, cut)
        return self.fy[i - 1] if i else None

    def prev_fy(self, fy):
        i = bisect.bisect_left(self.fy, fy)
        if i >= 1:
            p = self.fy[i - 1]
            if 300 <= (fy - p).days <= 430:
                return p
        return fy - timedelta(days=365)

    def ia(self, fy):
        a1 = self.at(self.asset, fy)
        a0 = self.at(self.asset, self.prev_fy(fy), tol=20)
        if a1 and a0 and a0 > 0 and a1 > 0:
            return a1 / a0 - 1
        return None

    def droe(self, t):
        """90일 지난 최신 분기의 Roe − 4분기 전 Roe. Roe = 분기 순이익 ÷ 직전 분기말 자본."""
        cut = t - timedelta(days=LAG_Q)
        qs = [x for x in self.ni_q if x[0] <= cut]
        if len(qs) < 5:
            return None
        def roe(k):
            dq, ni = qs[k]
            e = self.at(self.eq, dq - timedelta(days=91), tol=20)
            return ni / e if e and e > 0 else None
        r0 = roe(-1)
        # 4분기 전 — 날짜로 찾는다(분기가 빠진 회사가 있다)
        target = qs[-1][0] - timedelta(days=364)
        k4 = min(range(len(qs)), key=lambda k: abs((qs[k][0] - target).days))
        if abs((qs[k4][0] - target).days) > 20:
            return None
        dq4, ni4 = qs[k4]
        e4 = self.at(self.eq, dq4 - timedelta(days=91), tol=20)
        r4 = ni4 / e4 if e4 and e4 > 0 else None
        return (r0 - r4) if (r0 is not None and r4 is not None) else None


def main() -> int:
    t0 = time.time()
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = S["pxd_dates"]
    D = len(dates)
    didx = {d: i for i, d in enumerate(dates)}
    ddates = [d_(x) for x in dates]
    sector_now = {s["t"]: s.get("sector") for s in S["stocks"]}

    PX = {}
    for t in sector_now:
        d = json.load(io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8"))
        PX[t] = np.array([np.nan if v is None else float(v) for v in d["pxd"]])
    # 🚨 2026-09-23 정정 — 편출 가격은 **정리본 data/pit_px.json** 을 쓴다(격리·합병 보정 반영).
    #   처음에는 원시 캐시 _pit_px_cache.json 을 읽었는데, 그 안의 PARA 는 랩이 2026-09-14 에 격리한
    #   «다른 증권» 계열이다(주당 57~113,900달러). 그 한 종목이 시총가중을 지배해 Eg 첫 판을 오염시켰다.
    #   정리본은 157종으로 원시 캐시(122종)보다 넓다 — 인수된 36종이 더 들어 있다.
    pxc = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))["px"]
    for t, obj in pxc.items():
        if t not in PX:
            # pit_px.json 의 한 종목 = {i0: 격자 시작 인덱스, p: 가격 배열} (날짜 사전이 아니다)
            a = np.full(D, np.nan)
            i0, arr = int(obj.get("i0") or 0), obj.get("p") or []
            for j, v in enumerate(arr):
                if v is not None and 0 <= i0 + j < D:
                    a[i0 + j] = float(v)
            PX[t] = a
    PU = json.load(io.open(os.path.join(DATA, "pit_universe.json"), encoding="utf-8"))
    splice = PU.get("cik_spliced") or {}
    reassigned = (json.load(io.open(os.path.join(DATA, "pit_reuse.json"), encoding="utf-8")).get("reassigned") or {})
    meta = json.load(io.open(os.path.join(DATA, "index_ledger.json"), encoding="utf-8")).get("meta") or {}
    cikmap = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8")).get("cik") or {}
    FUND = TB.load_fund(extra_dirs=[os.path.join(DATA, "fx_pit")])

    # 재무 원장 — fx(오늘) + fx_pit(편출)
    FIRMS = {}
    for sub in ("fx", "fx_pit"):
        dd = os.path.join(DATA, sub)
        for fn in sorted(os.listdir(dd)):
            if not fn.endswith(".json"):
                continue
            tk = fn[:-5]
            if tk in FIRMS:
                continue
            j = json.load(io.open(os.path.join(dd, fn), encoding="utf-8"))
            FIRMS[tk] = Firm(j.get("tags") or {})

    def key(t):
        if t in PX:
            return t
        n = splice.get(t)
        return n if (n and n in PX) else None

    def fkey(t, k):
        return k if k in FIRMS else (t if t in FIRMS else (splice.get(t) if splice.get(t) in FIRMS else None))

    def sector(t, k):
        s = sector_now.get(k) or sector_now.get(t)
        if s:
            return s
        m = meta.get(t) or meta.get(k)
        return m[1] if (m and len(m) > 1) else None

    def shares(t, k, d, lag=None):
        for c in (k, t):
            f = FUND.get(c) or {}
            sh = f.get("sh")
            if sh:
                obs = TB.asof_all(sh, d) if lag is None else TB.asof_all(sh, d, lag=lag)
                if obs and obs[0][1]:
                    return obs[0][1]
        return None

    def px_on(k, d):
        """d 이전 가장 가까운 거래일 종가(10거래일 안)."""
        i = bisect.bisect_right(ddates, d) - 1
        p = PX[k]
        for j in range(i, max(-1, i - 10), -1):
            if p[j] == p[j]:
                return p[j]
        return None

    # 월말 거래일
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    allm = sorted(me)

    def mshift(ym, k):
        y, m = int(ym[:4]), int(ym[5:7])
        n = y * 12 + (m - 1) + k
        return "%04d-%02d" % (n // 12, n % 12 + 1)

    # ── 회사·월별 예측변수 X 와 현재 I/A ─────────────────────────────────────
    #   회귀용 표본은 가격 계열이 있는 모든 회사(금융·음(−)자본 제외) — 사전등록 §1
    # 이중클래스의 남기지 않는 쪽(GOOG·FOX·NWS)은 회귀에서도 뺀다 — 같은 회사를 두 번 세지 않게
    universe_all = sorted({t for t in FIRMS if key(t)} - {"GOOG", "FOX", "NWS"})
    fin = {t for t in universe_all if (sector(t, key(t)) or "").strip() == "Financials"}
    cache = {}

    def state(t, ym):
        """(logq, cop, droe, ia, fy, me_t) — ym 월말에 알 수 있던 값. 없으면 None."""
        ck = (t, ym)
        if ck in cache:
            return cache[ck]
        out = None
        k = key(t)
        fk = fkey(t, k)
        if k and fk and ym in me:
            F = FIRMS[fk]
            td = ddates[me[ym]]
            fy = F.fy_known(td)
            if fy:
                at = F.at(F.asset, fy)
                eq = F.at(F.eq, fy)
                cfo = F.at(F.cfo_a, fy, tol=5)
                ia = F.ia(fy)
                p_fy = px_on(k, fy)
                sh_fy = shares(t, k, fy.isoformat(), lag=0)
                p_t = PX[k][me[ym]]
                sh_t = shares(t, k, dates[me[ym]])
                if (at and at > 0 and eq is not None and eq > 0 and cfo is not None and ia is not None
                        and p_fy and sh_fy and p_t == p_t and sh_t):
                    debt = F.at(F.debt, fy) or 0.0
                    q = (p_fy * sh_fy + debt) / at
                    dr = F.droe(td)
                    if q > 0:
                        out = (math.log(q), cfo / at, dr if dr is not None else 0.0, ia, fy, p_t * sh_t)
        cache[ck] = out
        return out

    # ── ① 월별 회귀 ─────────────────────────────────────────────────────────
    reg_months = [m for m in allm if REG0 <= m <= F1_]
    B = {}
    nreg = {}
    for ym in reg_months:
        y, X, w = [], [], []
        for t in universe_all:
            if t in fin:
                continue
            s1 = state(t, ym)
            s0 = state(t, mshift(ym, -12))
            if not s1 or not s0 or s1[4] == s0[4]:
                continue                    # 새 회계연도가 안 들어왔으면 실현된 변화가 없다
            y.append(s1[3] - s0[3])
            X.append([s0[0], s0[1], s0[2]])
            w.append(s0[5])
        if len(y) < 60:
            continue
        y = winsor(y)
        X = np.column_stack([winsor(np.asarray(X)[:, j]) for j in range(3)])
        W = np.asarray(w, float)
        Xc = np.column_stack([np.ones(len(y)), X])
        sw = np.sqrt(W / W.mean())
        b, *_ = np.linalg.lstsq(Xc * sw[:, None], y * sw, rcond=None)
        B[ym] = b
        nreg[ym] = len(y)

    def bbar(ym):
        ks = [m for m in B if mshift(ym, -ROLL + 1) <= m <= ym]
        if len(ks) < ROLL_MIN:
            return None
        return np.mean([B[m] for m in ks], axis=0)

    # ── ③④ 형성·보유 ─────────────────────────────────────────────────────────
    mem, _c = IM.load(F0)
    months = [m for m in sorted(mem) if F0 <= m <= F1_]
    rows, prev_w, prev_rn, f4_rho, drops = [], {}, {}, [], {"no_state": 0, "fin": 0, "dual": 0, "no_px": 0, "reuse": 0}
    for m in months:
        bb = bbar(m)
        if bb is None:
            raise SystemExit("🚨 %s: 평균 기울기를 낼 회귀가 %d개월뿐이다(최소 %d)" % (m, len([x for x in B if x <= m]), ROLL_MIN))
        e1, e2 = me[m], me[mshift(m, 1)]
        # 예측변수 윈저 기준 = 그 달 회귀 표본 전체의 분포(원문 «most recent winsorized predictors»)
        Xall = [state(t, m) for t in universe_all if t not in fin]
        Xall = np.array([[s[0], s[1], s[2]] for s in Xall if s])
        lo = np.percentile(Xall, 1, axis=0)
        hi = np.percentile(Xall, 99, axis=0)
        by_cik = {}
        for t in mem[m]:
            c = cikmap.get(t) or cikmap.get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        keep = set()
        for c, ts in by_cik.items():
            if len(ts) == 1 or c.startswith("_"):
                keep.update(ts)
                continue
            k_ = [t for t in ts if t in KEEP_DUAL]
            keep.add(k_[0] if k_ else sorted(ts)[0])
            drops["dual"] += len(ts) - 1
        cand = []
        for t in sorted(keep):
            k = key(t)
            if k is None or not (PX[k][e1] == PX[k][e1]):
                drops["no_px"] += 1
                continue
            if (sector(t, k) or "").strip() == "Financials":
                drops["fin"] += 1
                continue
            if t in reassigned and m >= reassigned[t].get("last", "9999"):
                drops["reuse"] += 1
                continue
            s = state(t, m)
            if not s:
                drops["no_state"] += 1
                continue
            x = np.clip(np.array([s[0], s[1], s[2]]), lo, hi)
            eg = float(bb[0] + x @ bb[1:])
            p = PX[k]
            seg2 = p[e1 + 1:e2 + 1]
            ok = np.where(seg2 == seg2)[0]
            rn = (seg2[ok[-1]] / p[e1] - 1) if len(ok) else 0.0
            # F4 — 12개월 뒤에 알려진 I/A − 지금 I/A (실현 d1 I/A)
            s12 = state(t, mshift(m, 12)) if mshift(m, 12) <= allm[-1] else None
            real = (s12[3] - s[3]) if (s12 and s12[4] != s[4]) else None
            cand.append({"t": t, "eg": eg, "mc": s[5], "rn": rn, "real": real})
        if len(cand) < 60:
            raise SystemExit("🚨 %s 자격 종목 %d — 너무 얇다" % (m, len(cand)))
        egs = np.array([c["eg"] for c in cand])
        q30, q70 = np.percentile(egs, [30, 70])
        legs = {"H": [c for c in cand if c["eg"] >= q70], "L": [c for c in cand if c["eg"] <= q30]}
        res = {}
        for nm, g in legs.items():
            ws = sum(c["mc"] for c in g)
            res[nm] = {"ret": sum(c["mc"] * c["rn"] for c in g) / ws, "w": {c["t"]: c["mc"] / ws for c in g}, "n": len(g)}
        wu = sum(c["mc"] for c in cand)
        univ = sum(c["mc"] * c["rn"] for c in cand) / wu
        turns = {}
        for nm in ("H", "L"):
            pw = prev_w.get(nm) or {}
            if pw:
                drift = {t: w * (1 + prev_rn.get(t, 0.0)) for t, w in pw.items()}
                s_ = sum(drift.values()) or 1.0
                drift = {t: w / s_ for t, w in drift.items()}
                nw = res[nm]["w"]
                turns[nm] = 0.5 * sum(abs(nw.get(t, 0.0) - drift.get(t, 0.0)) for t in set(drift) | set(nw))
            else:
                turns[nm] = None
            prev_w[nm] = res[nm]["w"]
        prev_rn = {c["t"]: c["rn"] for c in cand}
        rr = [(c["eg"], c["real"]) for c in cand if c["real"] is not None]
        if len(rr) >= 30:
            f4_rho.append(spearman([a for a, b in rr], [b for a, b in rr]))
        rows.append({"m": mshift(m, 1), "form": m, "spread": (res["H"]["ret"] - res["L"]["ret"]) * 100,
                     "lo": (res["H"]["ret"] - univ) * 100, "univ": univ * 100,
                     "n": {"H": res["H"]["n"], "L": res["L"]["n"], "all": len(cand)}, "turn": turns,
                     "slopes": [round(float(v), 5) for v in bb]})
    dt = time.time() - t0

    sp = np.array([r["spread"] for r in rows])
    lo_ = np.array([r["lo"] for r in rows])
    post = np.array([r["spread"] for r in rows if r["m"] >= POST])
    pre = np.array([r["spread"] for r in rows if r["m"] < POST])
    cost = np.array([0.0] + [COST * (r["turn"]["H"] + r["turn"]["L"]) * 100 for r in rows[1:]])
    net = sp - cost

    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))
    IX = {s["sid"]: s for s in json.load(io.open(os.path.join(DATA, "strategy_index.json"), encoding="utf-8"))["items"]}
    spx = CH["idx_monthly"]["S&P 500"]
    uu = [(r["univ"], spx[r["m"]]) for r in rows if r["m"] in spx]
    corr_spx = float(np.corrcoef([a for a, b in uu], [b for a, b in uu])[0, 1])
    mset = [r["m"] for r in rows]
    pool = []
    for sid, c in CH["charts"].items():
        s = IX.get(sid)
        mo = c.get("monthly") or []
        if not s or s.get("src") != "종목 전략" or s.get("role") != "수익엔진" or len(mo) < 100:
            continue
        ex = {x["m"]: x["r"] - x["b"] for x in mo if x.get("r") is not None and x.get("b") is not None}
        if all(m_ in ex for m_ in mset):
            pool.append((sid, s.get("name"), np.array([ex[m_] for m_ in mset])))
    cors = sorted(((abs(np.corrcoef(sp, v)[0, 1]), float(np.corrcoef(sp, v)[0, 1]), sid, nm, v) for sid, nm, v in pool),
                  key=lambda x: -x[0])
    # 상관 상위 5 — 서로 사실상 같은 계열(상관 0.999 초과, 예: 밴드판 = 원판)은 하나만 남긴다.
    #   같은 계열 둘을 넣으면 회귀 행렬이 특이해진다(첫 실행에서 실제로 죽었다).
    top5 = []
    for x in cors:
        if all(abs(np.corrcoef(x[4], y[4])[0, 1]) < 0.999 for y in top5):
            top5.append(x)
        if len(top5) == 5:
            break
    a5, t5 = ols_alpha_t(sp, np.column_stack([x[4] for x in top5]))

    f1m, f1t = float(sp.mean()), tstat(sp)
    rho = float(np.mean(f4_rho)) if f4_rho else None
    R = {
        "f1": {"hit": not (f1m > 0), "mean_pm": f1m},
        "f2": {"hit": not (f1t is not None and f1t >= F_T), "t": f1t, "문턱": F_T},
        "f3": {"hit": not (post.mean() > 0), "post_mean_pm": float(post.mean()), "post_t": tstat(post), "n_post": len(post),
               "pre_mean_pm": float(pre.mean()), "pre_t": tstat(pre), "n_pre": len(pre)},
        "f4": {"hit": not (rho is not None and rho > 0), "rank_corr_mean": rho, "n_months": len(f4_rho),
               "rank_corr_t": tstat(f4_rho)},
        "f5": {"hit": not (t5 >= F_T), "alpha_pm": a5, "t": t5, "n_pool": len(pool),
               "top5": [{"sid": x[2], "name": x[3], "corr": x[1]} for x in top5]},
        "f6": {"hit": not (net.mean() > 0), "net_mean_pm": float(net.mean()), "net_t": tstat(net), "cost_mean_pm": float(cost.mean())},
    }
    verdict = ("기각" if any(R[k]["hit"] for k in ("f1", "f2", "f3", "f4", "f6")) else
               "보류" if R["f5"]["hit"] else "게시 후보")
    slopes = np.array([r["slopes"] for r in rows])
    doc = {"note": "기대투자성장(Eg) PIT 검정. 사전등록 PREREG-2026-09-23-EG(계산 전 커밋 cee33124) 값 그대로.",
           "prereg": "build/PREREG-2026-09-23-EG.md", "commit": "cee33124",
           "window": "보유 %s ~ %s (%d개월)" % (rows[0]["m"], rows[-1]["m"], len(rows)),
           "summary": {"spread_mean_pm": f1m, "spread_t": f1t, "longonly_pm": float(lo_.mean()), "longonly_t": tstat(lo_),
                       "avg_turnover": {nm: float(np.mean([r["turn"][nm] for r in rows[1:]])) for nm in ("H", "L")},
                       "avg_n": {k: float(np.mean([r["n"][k] for r in rows])) for k in ("H", "L", "all")},
                       "slopes_mean": {"const": float(slopes[:, 0].mean()), "logq": float(slopes[:, 1].mean()),
                                       "cop": float(slopes[:, 2].mean()), "droe": float(slopes[:, 3].mean())},
                       "n_regressions": len(B), "reg_n_median": float(np.median(list(nreg.values())))},
           "sanity": {"univ_vs_spx_corr": corr_spx}, "drops": drops, **R, "verdict": verdict,
           "monthly": [{"m": r["m"], "spread": round(r["spread"], 4), "lo": round(r["lo"], 4)} for r in rows]}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("보유 %s ~ %s · %d개월 · 회귀 %d개월(표본 중앙 %d) · %.0f초"
          % (rows[0]["m"], rows[-1]["m"], len(rows), len(B), np.median(list(nreg.values())), dt))
    print("평균 기울기: 상수 %.4f · log q %.4f · Cop %.4f · dRoe %.4f  (원문 1년: log q 음 · Cop 양 · dRoe 양)"
          % tuple(slopes.mean(axis=0)))
    print("위생: 모집단 시총가중 vs S&P 500 상관 %.3f · 제외 %s" % (corr_spx, drops))
    print("평균 종목 수 %s · 편도 회전 %s" % (doc["summary"]["avg_n"], {k: round(v, 3) for k, v in doc["summary"]["avg_turnover"].items()}))
    print("\n  고Eg − 저Eg  월 %+.3f%% · t %.2f" % (f1m, f1t))
    print("  롱온리 고Eg − 모집단  월 %+.3f%% · t %.2f   (서술)" % (lo_.mean(), tstat(lo_)))
    print("\n🚨 실패 조건")
    print("  F1 평균 %+.3f%% → %s" % (f1m, "걸림 ✗" if R["f1"]["hit"] else "통과"))
    print("  F2 t %.2f → %s" % (f1t, "구별 불가 ✗" if R["f2"]["hit"] else "통과"))
    print("  F3 발표 후 %d개월 %+.3f%% · t %.2f (앞 %d개월 %+.3f%% · t %.2f) → %s"
          % (len(post), post.mean(), tstat(post), len(pre), pre.mean(), tstat(pre), "걸림 ✗" if R["f3"]["hit"] else "통과"))
    print("  F4 예측 순위상관 평균 %.3f (t %.2f · %d개월) → %s"
          % (rho, tstat(f4_rho), len(f4_rho), "걸림 ✗ 예측기가 안 선다" if R["f4"]["hit"] else "통과"))
    print("  F5 증분 알파 %+.3f%% · t %.2f → %s" % (a5, t5, "보류 ✗" if R["f5"]["hit"] else "통과"))
    for x in top5:
        print("       %+.3f  %s  %s" % (x[1], x[2], x[3]))
    print("  F6 편도 10bp 뒤 %+.3f%% · t %.2f (비용 월 %.3f%%) → %s"
          % (net.mean(), tstat(net), cost.mean(), "걸림 ✗" if R["f6"]["hit"] else "통과"))
    print("\n판정: **%s**" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
