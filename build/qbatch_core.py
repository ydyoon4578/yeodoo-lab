# -*- coding: utf-8 -*-
"""build/qbatch_core.py — 배치 Q(2026-09-25 · 금융공학·통계·수학 전략 묶음) 공용 평가 틀.

틀은 EG30+ 와 같다(PREREG-2026-09-24-EG30PLUS §2): 펀드 = 지수 90% + 슬리브 10%(매월 말 되돌림 · 되돌림 비용 2 × 10bp × 벗어난 몫) ·
판정선 SPY 총수익(assets.json 수정종가) · 보유 2016-09 ~ 2026-08(120개월) · 하락월 = S&P 500 PR 월 수익 < 0 인 보유월 · 편도 10bp.
전략 모듈은 «월말 m 에 그때까지의 자료로 정한 목표 비중» 만 낸다 — 경로 · 비용 · 펀드 · 지표는 여기서 한 벌로 잰다.

  ETF 슬리브: Assets() · etf_path(A, decide, forms) → fund_from_path(A, path, forms) → evaluate(A, fr)
  종목 슬리브: eg30plus.World 의 sleeve(목표 비중)로 경로를 만들고 Grid.from_world(Wd) 로 같은 fund_from_path · evaluate 를 쓴다.

판정 통계는 eg30plus 의 것을 그대로 쓴다(down_t 달력 HAC · t_crit · rolling12 복리 · nw_t · nw_ols · cluster_t) — 복제하면 표가 갈린다.
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
FORM0, HOLD0, HOLD1 = "2016-08", "2016-09", "2026-08"
COST, SLEEVE = 0.0010, 0.10
EPIS = [("급락", "코로나19 팬데믹", "2020-02-19", "2020-03-16"), ("급등", "무제한 QE·재정부양 랠리", "2020-03-16", "2020-06-03"),
        ("급락", "2020년 9월 기술주 조정", "2020-09-02", "2020-09-23"), ("급등", "백신 기대·대선 불확실성 해소", "2020-09-23", "2020-12-01"),
        ("급락", "금리 급등 쇼크", "2021-02-12", "2021-03-08"), ("급등", "금리 안정 반등", "2021-03-08", "2021-04-09"),
        ("급락", "인플레이션·연준 급속 긴축", "2021-12-27", "2022-11-03"), ("급등", "생성형 AI 랠리", "2022-11-03", "2023-12-13"),
        ("급락", "엔 캐리 청산 쇼크", "2024-07-10", "2024-08-07"), ("급등", "연준 인하 개시 랠리", "2024-08-07", "2024-11-06"),
        ("급락", "관세 쇼크", "2025-02-19", "2025-04-08"), ("급등", "관세 유예·협상 진전 반등", "2025-04-08", "2025-06-24")]   # qg_lab.EPIS 와 같다


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7]) + k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def months_between(a, b):
    out, m = [], a
    while m <= b:
        out.append(m)
        m = mshift(m, 1)
    return out


def load(name):
    return json.load(io.open(os.path.join(DATA, name), encoding="utf-8"))


def ffill(a):
    """첫 유효값 뒤로만 앞값 채움(상장 전은 NaN 그대로)."""
    a = np.array(a, float)
    for j in range(1, len(a)):
        if a[j] != a[j] and a[j - 1] == a[j - 1]:
            a[j] = a[j - 1]
    return a


# ── 날짜 격자 ─────────────────────────────────────────────────────────────
class Grid:
    """일간 날짜 · 월말 자리(그달 마지막 거래일) · SPY 총수익 · S&P 500 PR · 무위험(월)."""

    def __init__(self, dates, ix_tr, ix_pr):
        self.dates = list(dates)
        self.di = {d: i for i, d in enumerate(self.dates)}
        self.IX_TR, self.IX_PR = ffill(ix_tr), ffill(ix_pr)
        me = {}
        for i, d in enumerate(self.dates):
            me[d[:7]] = i
        self.me = me
        self.RF = load("rf_monthly.json")["monthly"]            # 달 → 그달 무위험 수익(소수)

    @classmethod
    def from_world(cls, Wd):
        g = cls(Wd.dates, Wd.IX_TR, Wd.IX_PR)
        g.me = dict(Wd.me)
        return g

    def down_months(self, hold):
        return [h for h in hold if self.IX_PR[self.me[h]] / self.IX_PR[self.me[mshift(h, -1)]] - 1 < 0]


class Assets(Grid):
    """assets.json(ETF · 지수 · FRED) — 수정종가 · 상장 전 NaN · 거시는 원자료(발표 지연은 쓰는 쪽이 건다)."""

    def __init__(self):
        A = load("assets.json")
        self.A = A
        B = load("bench_px.json")
        bpos = {d: i for i, d in enumerate(B["dates"])}
        pr = [B["series"]["spx"]["px"][bpos[d]] if d in bpos and B["series"]["spx"]["px"][bpos[d]] is not None else np.nan for d in A["dates"]]
        spy = [np.nan if v is None else v for v in A["px"]["SPY"]]
        super().__init__(A["dates"], spy, pr)
        self.px = {k: ffill([np.nan if v is None else v for v in s]) for k, s in A["px"].items()}
        self.macro = A.get("macro", {})

    def ret(self, tk, i0, i1):
        p = self.px[tk]
        a, b = p[i0], p[i1]
        return (b / a - 1.0) if (a == a and b == b and a > 0) else None

    def monthly(self, tk, m):
        """달 m 의 수익(전달 말 → 그달 말) · 없으면 None."""
        if m not in self.me or mshift(m, -1) not in self.me:
            return None
        return self.ret(tk, self.me[mshift(m, -1)], self.me[m])


# ── 슬리브 경로(ETF) ──────────────────────────────────────────────────────
def etf_path(A, decide, forms, cost=COST):
    """forms = 편입 월(월말) 목록 · decide(m) → {티커: 비중}(합 ≤ 1 · 나머지 현금 · None 이면 그달 매매 없이 흘러간다).
    달 m 말에 정하고 그 종가로 매매 → 다음 달 말까지 일간 경로. 현금은 그달 무위험으로 일할 복리."""
    px = A.px
    path, units, cash, last = {}, {}, 1.0, {}
    turns, books = [], []
    ends = forms + [mshift(forms[-1], 1)]
    for j, m in enumerate(forms):
        i, i1 = A.me[m], A.me[ends[j + 1]]
        val = {k: units[k] * px[k][last[k]] for k in units}
        V = cash + sum(val.values())
        w = decide(m)
        if w is None and j == 0:
            raise RuntimeError("첫 편입 %s 에 비중이 없다" % m)
        if w is not None:
            w = {k: x for k, x in w.items() if x > 1e-12}
            for k in w:
                if not (px[k][i] == px[k][i] and px[k][i] > 0):
                    raise RuntimeError("%s 가 %s 에 가격이 없다" % (k, m))
            if sum(w.values()) > 1 + 1e-9 or min(w.values(), default=0) < 0:
                raise RuntimeError("비중 합 %.6f(%s)" % (sum(w.values()), m))
            tv = {k: V * x for k, x in w.items()}
            traded = sum(abs(tv.get(k, 0.0) - val.get(k, 0.0)) for k in sorted(set(tv) | set(val)))   # 정렬 — 해시 씨앗에 매이지 않는 합 순서
            V2 = V - cost * traded
            units = {k: (V2 * x) / px[k][i] for k, x in w.items()}
            cash = V2 - sum(V2 * x for x in w.values())
            last = {k: i for k in units}
            turns.append(traded / V)
            books.append({"m": m, "w": dict(w)})
            path[i] = V2
        else:
            turns.append(0.0)
            path[i] = V
        rf_d = (1 + float(A.RF.get(ends[j + 1], 0.0))) ** (1.0 / max(1, i1 - i)) - 1
        for d in range(i + 1, i1 + 1):
            cash *= (1 + rf_d)
            for k in units:
                p = px[k][d]
                if p == p and p > 0:
                    last[k] = d
            path[d] = cash + sum(units[k] * px[k][last[k]] for k in units)
    return {"path": path, "turn": float(np.mean(turns) / 2 * 12), "books": books}


# ── 펀드 ──────────────────────────────────────────────────────────────────
def fund_from_path(G, sl, forms, cost=COST, basis="TR"):
    """슬리브 일간 경로 → 펀드(지수 90 + 슬리브 10 · 매월 말 되돌림) 월 초과(%) · 슬리브 월(%) · 지수 월(%) · 일간 경로."""
    path = sl["path"]
    IX = G.IX_TR if basis == "TR" else G.IX_PR
    months = forms
    i0, iE = G.me[months[0]], G.me[mshift(months[-1], 1)]
    mends = [G.me[m] for m in months] + [iE]
    ms = set(mends[1:])
    fp = {i0: 1.0}
    ixv, slv = 1 - SLEEVE, SLEEVE
    for d in range(i0 + 1, iE + 1):
        ixv *= IX[d] / IX[d - 1]
        slv *= path[d] / path[d - 1]
        v = ixv + slv
        if d in ms:
            v -= cost * 2 * abs(slv / v - SLEEVE) * v
            ixv, slv = v * (1 - SLEEVE), v * SLEEVE
        fp[d] = v
    f = lambda p: np.array([p[mends[j + 1]] / p[mends[j]] - 1.0 for j in range(len(months))])
    fr, im, sr = f(fp), f(IX), f(path)
    days = list(range(i0, iE + 1))
    return {"hold": [mshift(m, 1) for m in months], "ex": (fr - im) * 100, "basket": sr * 100, "index": im * 100,
            "fund": fr * 100, "fp": fp, "days": days, "path": path, "IX": IX, "turn": sl.get("turn"), "basis": basis}


# ── 지표 ──────────────────────────────────────────────────────────────────
def evaluate(G, fr, dmask=None):
    """EG30+ summary 와 같은 지표 + 이름 붙은 구간 · 기계적 틀 · 교환 탐지 · 베타 맞춘 현금 헤지 대조."""
    import eg30plus as E
    hold, ex, bk, ix, fu = fr["hold"], fr["ex"], fr["basket"], fr["index"], fr["fund"]
    if dmask is None:
        dset = set(G.down_months(hold))
        dmask = np.array([h in dset for h in hold])
    up = ~dmask
    n = len(ex)
    te = float(ex.std(ddof=1) * math.sqrt(12))
    rfm = np.array([float(G.RF.get(h, 0.0)) * 100 for h in hold])
    beta = float(np.cov(ix, bk, ddof=1)[0, 1] / np.var(ix, ddof=1))
    h1 = np.array([h < "2021-09" for h in hold])
    yrs = {}
    for h, a, b in zip(hold, fu, ix):
        y = yrs.setdefault(h[:4], [1.0, 1.0])
        y[0] *= 1 + a / 100; y[1] *= 1 + b / 100
    years = {y: (v[0] - v[1]) * 100 for y, v in sorted(yrs.items())}
    fp, IX, days = fr["fp"], fr["IX"], fr["days"]
    d0 = days[0]

    def seg(a, b):
        ia, ib = G.di.get(a), G.di.get(b)
        if ia is None or ib is None or ia < d0 or ib > days[-1]:
            return None
        return float((fp[ib] / fp[ia] - IX[ib] / IX[ia]) * 100)
    epi = []
    for kind, nm, a, b in EPIS:
        x = seg(a, b)
        if x is not None:
            epi.append({"kind": kind, "name": nm, "ex": x})
    ME = load("mech_episodes.json")
    pos = {h: j for j, h in enumerate(hold)}
    mech = {}
    for key in ("crash_m", "surge_m"):
        js = [pos[m] for m in ME["months"][key] if m in pos]
        e = ex[js]
        mech[key] = {"n": len(js), "mean": float(e.mean()) if js else None, "win": int((e > 0).sum())}
    for key, rows in (("crash_legs", [l for l in ME["frozen"]["legs"] if l["side"] == "crash"]), ("rebounds", ME["frozen"]["rebounds"])):
        v = [y for y in (seg(r["a"], r["b"]) for r in rows) if y is not None]
        mech[key] = {"n": len(v), "mean": float(np.mean(v)) if v else None, "win": int(sum(y > 0 for y in v))}
    b_s, t_s = E.nw_ols(ex, np.column_stack([np.ones(n), ix]))
    # 베타 맞춘 현금 헤지 대조 — 슬리브를 «SPY β + 현금 (1 − β)» 로 바꾼 판의 펀드 초과(β = 전 표본 실현 월 베타)
    hedge = 0.1 * (beta - 1.0) * (ix - rfm)
    r12, r12h = E.rolling12(ex, ix), E.rolling12(ex[h1], ix[h1])
    return {"n": n, "ann_ex": float(ex.mean() * 12), "te": te, "ir": float(ex.mean() * 12 / te) if te > 0 else None,
            "t_iid": float(ex.mean() / (ex.std(ddof=1) / math.sqrt(n))), "nw_t": E.nw_t(ex),
            "down_n": int(dmask.sum()), "down_mean": float(ex[dmask].mean()), "down_t": E.down_t(ex, dmask),
            "down_win": float(np.mean(ex[dmask] > 0) * 100), "up_mean": float(ex[up].mean()), "up_win": float(np.mean(ex[up] > 0) * 100),
            "win": float(np.mean(ex > 0) * 100),
            "down_capture": float(bk[dmask].mean() / ix[dmask].mean()), "up_capture": float(bk[up].mean() / ix[up].mean()),
            "sleeve_beta": beta, "roll12": r12, "roll12_h1": r12h, "turn": fr.get("turn"),
            "years": years, "years_won": int(sum(v > 0 for v in years.values())), "n_years": len(years),
            "episodes": epi, "crash_won": int(sum(e["ex"] > 0 for e in epi if e["kind"] == "급락")),
            "surge_won": int(sum(e["ex"] > 0 for e in epi if e["kind"] == "급등")),
            "mech": mech, "shift": {"alpha_m": float(b_s[0]), "alpha_t": float(t_s[0]), "slope": float(b_s[1]), "slope_t": float(t_s[1])},
            "hedge_ctrl": {"down_mean": float(hedge[dmask].mean()), "all_mean": float(hedge.mean()), "beta": beta},
            "halves": [float(ex[h1].mean() * 12), float(ex[~h1].mean() * 12)],
            "blocks": [float(ex[(np.arange(n) // 30) == q].mean() * 12) for q in range(4)]}


def monthly_forms():
    """월간 편입 — 2016-08 말부터 2026-07 말까지(보유 2016-09 ~ 2026-08)."""
    return months_between(FORM0, mshift(HOLD1, -1))


def quarterly_forms():
    """분기 편입 — 첫 달 2016-08 뒤 3·6·9·12월 말(EG30 과 같다)."""
    return [m for j, m in enumerate(monthly_forms()) if j == 0 or int(m[5:7]) % 3 == 0]


def expand_quarterly(decide_q, forms_m):
    """분기 결정을 월 경로에 펼친다 — 분기 달이 아니면 None(흘러감)."""
    qs = set(quarterly_forms())
    return lambda m: decide_q(m) if m in qs else None


# ── 슬리브 경로(종목) ─────────────────────────────────────────────────────
def stock_path(Wd, targets, reb=3, cost=COST):
    """eg30plus.World(시점정확 S&P 500 ∪ NASDAQ 100 · 날짜 인식 키) 위에서 목표 비중 경로 — targets = {편입월: {"w": {키: 비중}, "names": {키: 티커}}}.
    reb 3 = 첫 달 + 분기말(EG30 과 같다) · reb 1 = 매월. 편입 사이는 흘러간다 · 편도 cost."""
    import eg30plus as E
    import qg_lab as QL
    old = QL.COST
    QL.COST = cost
    try:
        path, turn, books = Wd.sleeve(dict(E.EG_BASE, targets=targets, reb=reb))
    finally:
        QL.COST = old
    return {"path": path, "turn": turn, "books": books}


# ── 공용 문맥(배치 Q 카드 모듈이 받는 ctx) ────────────────────────────────
SEED = 20260925


class Ctx:
    """카드 모듈 공용 — 자산 격자 · 종목 세계 · V0(EG30 공개 판) · 하락월 · 씨앗. 무거운 것은 처음 쓸 때 만든다.
    🚨 카드 모듈은 dry/selftest 에서 자기 규칙 · 대조 · 팔의 수익을 계산하거나 찍지 않는다(V0 재현 · x-bmrot 재현만 예외)."""

    def __init__(self):
        self._A = self._Wd = self._G = self._T0 = None
        self._V0 = {}
        self.seed = SEED

    @property
    def A(self):
        if self._A is None:
            self._A = Assets()
        return self._A

    @property
    def Wd(self):
        if self._Wd is None:
            import eg30plus as E
            self._Wd = E.World()
        return self._Wd

    @property
    def G(self):
        if self._G is None:
            self._G = Grid.from_world(self.Wd)
        return self._G

    @property
    def V0_targets(self):
        if self._T0 is None:
            import eg30plus as E
            self._T0 = E.v0_targets(self.Wd)
        return self._T0

    def V0(self, basis="TR", cost=COST):
        """EG30 공개 판(EG_BASE) 펀드 결과 — 종목 격자 · 분기 편입."""
        k = (basis, cost)
        if k not in self._V0:
            sl = stock_path(self.Wd, self.V0_targets, reb=3, cost=cost)
            self._V0[k] = fund_from_path(self.G, sl, self.Wd.months, cost=cost, basis=basis)
        return self._V0[k]

    def stock_fr(self, targets, reb=3, basis="TR", cost=COST):
        sl = stock_path(self.Wd, targets, reb=reb, cost=cost)
        return fund_from_path(self.G, sl, self.Wd.months, cost=cost, basis=basis)

    def etf_fr(self, decide, forms=None, basis="TR", cost=COST):
        forms = forms or monthly_forms()
        sl = etf_path(self.A, decide, forms, cost=cost)
        return fund_from_path(self.A, sl, forms, cost=cost, basis=basis)

    def dmask(self, hold):
        dset = set(self.A.down_months(hold))
        return np.array([h in dset for h in hold])


def blind_smoke(fn, *a, **k):
    """눈가린 연기 시험 — fn 을 돌려 예외 · 모양 · 시간만 보고 수익 숫자는 버린다(표준출력도 버린다).
    돌려주는 것: {"ok", "sec", "shape"(키 구조), "err"}. 결과 값은 돌려주지 않는다."""
    import contextlib, time, traceback
    buf = io.StringIO()
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(buf):
            out = fn(*a, **k)
        return {"ok": True, "sec": round(time.time() - t0, 1), "shape": _shape(out), "err": None}
    except Exception:
        return {"ok": False, "sec": round(time.time() - t0, 1), "shape": None, "err": traceback.format_exc()[-4000:]}


def _shape(x, d=0):
    if d > 3:
        return "…"
    if isinstance(x, dict):
        return {str(k): _shape(v, d + 1) for k, v in list(x.items())[:40]}
    if isinstance(x, (list, tuple)):
        return "list[%d]" % len(x)
    if isinstance(x, np.ndarray):
        return "array%s" % (x.shape,)
    return type(x).__name__
