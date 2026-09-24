# -*- coding: utf-8 -*-
"""build/q_switch.py — 배치 Q 교체(부류 S) 공용 틀 · 두 일간 장부(공격 OFFENSE · 수비 DEFENSE)를 국면 계열로 오간다.

카드: Q03(점프모형 · 일간) · Q10(흡수비율 · 월간) · Q06(상관 놀람 · 월간 · 측정만)이 이 틀을 쓴다. Q16(SPY ↔ SPHB 분할)은 ETF 라 q_vrp 가 따로 푼다.
이 모듈은 카드가 아니다 — CARDS 가 비어 있다.

근본 이유 — 교체 규칙의 값은 «국면 판단의 정보» 뿐이어야 한다. 두 엔진을 같은 평균 몫(ē)으로 늘 섞어 둔 고정 혼합 D 와 견주면
  노출(얼마나 오래 수비에 있었나)이 같아서, 남는 차이 Δ^D 는 «언제» 옮겼는가에서만 나온다. 순열도 같은 뜻이다 — 수비·공격 구간의
  길이를 따로 섞어 다시 엮으면 교체 횟수와 ē 가 그대로인 채 시점만 무작위가 된다.

틀(카드 Q03 POSITION · controls · 배치 설계 §1):
  · 장부는 그림자 장부 — OFFENSE = EG30 V0(재생성 목표 · 분기 · 흘러감) · DEFENSE = x-bmrot(q_bmrot_leg · 월간 · 흘러감) 또는 T-bill.
    장부 자신의 되맞춤 비용은 장부 안에 있다(qbatch_core.stock_path). 교체 날 종가에 판 장부 10bp + 산 장부 10bp(슬리브 가치 기준) —
    그날 판 장부의 되맞춤 비용은 물지 않고(팔기 때문), 산 장부의 되맞춤은 교체 매수가 덮는다. 교체가 없는 날은 든 장부의 되맞춤만.
  · 일간 상태 s_t(종가 t)는 종가 t+1 부터 적용(1일 지연) — 수익일 t+2 부터. 월간 상태는 월말 m 종가에 매매, m+1 을 든다.
  · 펀드 = qbatch_core.fund_from_path(0.9 SPY TR + 0.1 슬리브 · 월말 되돌림).
  · D = ē·OFFENSE + (1 − ē)·DEFENSE · 월말 되맞춤 · 편도 10bp(거래액) + 각 장부의 자기 회전(장부 안) · D20 = 모두 20bp.
  · 순열(학생화 구간 섞기): 공격 구간 길이들과 수비 구간 길이들을 따로 섞어 참 첫 상태부터 번갈아 엮는다 → 교체 수 · ē 보존.
    통계 = Δ^D 월 계열 평균의 NW(3) t(eg30plus.nw_t) · p = (1 + #{t_perm ≥ t_obs})/(N + 1). 순열 안의 펀드는 월 닫힌 식
    (월초 0.9/0.1 → 월말 0.9·g_IX + 0.1·g_SL · 되돌림 비용 2c·|몫 − 0.1|) — fund_from_path 와 대수적으로 같다(selftest).
    뽑기마다 D 를 그 뽑기의 실현 몫 ē_draw 로 다시 짠다(mix_fr 의 월 닫힌 식) — 월 단위 섞기는 달마다 거래일 수가 달라 일 가중 ē 가
    조금 움직이기 때문(일 단위 섞기는 ē_draw = ē 그대로). t_obs 가 없으면(n < 5 · NW 분산 0) p = 1(기각 못 함 · 열린 쪽으로 새지 않는다).
  · 수비 다리 = DEFENSE_LEG("x-bmrot" · 등록 전 재현 관문이 실패로 판정되면 "T-bill" 로 바꿔 얼린다) — x-bmrot 은 장부를 만들기 전에
    q_bmrot_leg.verify_pins(목표 · 가격 지도 · 캐시 · 게시 계열 해시 + 구성 관문)를 다시 단언한다.
  · 쌍둥이: sma200(^GSPC 종가 < 200일 단순평균이면 수비) · ē 맞춘 변동성(SPY 63일 실현변동성 ≥ 확장 분위수(수준 ē)이면 수비).
  · REBOUND-MISS · F0 도우미.
출처: scratchpad/qbatch_final.md «BATCH DESIGN» §1·§3·§4 · 카드 Q03 POSITION/controls · Q10 controls · build/qbatch_core.py.
"""
from __future__ import annotations
import hashlib, io, json, math, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402

CARDS = {}
NPERM = 10000                         # 카드 — 10,000 번
SEED = Q.SEED                         # 20260925
COST, COST20 = Q.COST, 0.0020
SMA_N, VOL_N = 200, 63
VOL_FROM = "2006-04"                  # 변동성 쌍둥이 확장 분위수 시작(카드)
REB_WIN = 63                          # REBOUND-MISS — 교체 뒤 63거래일 안에 시작한 급등월
REB_MIN = 3
F0_OFF, F0_OFFDOWN = 12, 6            # F0 — 수비 몫 ≥ 50% 인 달 ≥ 12 · 그중 하락월 ≥ 6
DEFENSE_LEG = "x-bmrot"               # 선언: 구성 관문 통과(0.49bp) → x-bmrot · 등록 전에 관문을 실패로 판정하면 "T-bill"(카드의 선언된 대체)
_CACHE = {}


def _nw_t(x):
    import eg30plus as E
    return E.nw_t(x)


# ── 장부 ─────────────────────────────────────────────────────────────────
class Frame:
    """보유 창(2016-08 말 ~ 2026-08 말)의 일간 자리 · 월 경계 · 지수 월 성장(TR/PR)."""

    def __init__(self, ctx):
        Wd, G = ctx.Wd, ctx.G
        self.ctx, self.Wd, self.G = ctx, Wd, G
        self.months = list(Wd.months)                       # 편입월 2016-08 ~ 2026-07
        self.hold = [Q.mshift(m, 1) for m in self.months]   # 보유월 2016-09 ~ 2026-08
        self.i0, self.iE = G.me[self.months[0]], G.me[Q.mshift(self.months[-1], 1)]
        self.T = self.iE - self.i0                          # 수익일 수(i0+1 … iE)
        self.day = np.arange(self.i0 + 1, self.iE + 1)
        mends = [G.me[m] for m in self.months] + [self.iE]
        self.mends = np.array(mends)
        # 수익일 j 가 속한 보유월 번호 · 월 첫 수익일 오프셋
        self.mon_of = np.searchsorted(self.mends[1:], self.day, side="left")
        self.mstart = np.array([mends[k] + 1 - (self.i0 + 1) for k in range(len(self.months))])
        self.gIX = {b: np.array([(G.IX_TR if b == "TR" else G.IX_PR)[mends[k + 1]] / (G.IX_TR if b == "TR" else G.IX_PR)[mends[k]]
                                 for k in range(len(self.months))]) for b in ("TR", "PR")}
        self.dates = [G.dates[d] for d in self.day]
        self.years = self.T / 252.0

    def dmask(self):
        return self.ctx.dmask(self.hold)


class Book:
    """그림자 장부 하나 — 총 일간 성장 g0(되맞춤 비용 전) · 비용 배수 f_c(되맞춤 날 종가 · 1 − c·거래율) · 비용 c 별.
    f_c = g_c / g0 — 같은 목표 · 같은 가격에서 비용이 가치에 비례하므로(qg_lab.sleeve) 되맞춤 날 말고는 두 경로의 성장이 같다."""

    def __init__(self, name, F, paths, turn=None):
        self.name = name
        d = F.day
        p0 = paths[0.0]
        self.g0 = np.array([p0[x] / p0[x - 1] for x in d])
        self.lg0 = np.log(self.g0)
        self.lf, self.turn = {}, dict(turn or {})
        for c in sorted(paths):
            if c == 0.0:
                continue
            g = np.array([paths[c][x] / paths[c][x - 1] for x in d])
            self.lf[c] = np.log(g / self.g0)
        c1 = min(self.lf) if self.lf else None
        self.reb_days = np.flatnonzero(np.abs(self.lf[c1]) > 1e-12) if c1 else np.array([], int)
        self.cash = False


def stock_book(ctx, name, targets, reb, costs=(COST, COST20)):
    """종목 목표 경로 → Book(비용 0 · 10bp · 20bp 경로를 qbatch_core.stock_path 로)."""
    key = ("SB", id(ctx), name)
    if key in _CACHE:
        return _CACHE[key]
    F = frame(ctx)
    paths, turn = {}, {}
    for c in (0.0,) + tuple(costs):
        sl = Q.stock_path(ctx.Wd, targets, reb=reb, cost=c)
        paths[c], turn[c] = sl["path"], sl["turn"]
    b = Book(name, F, paths, turn)
    _CACHE[key] = b
    return b


def path_book(ctx, name, path_fn, costs=(COST, COST20)):
    """비용별 경로를 주는 함수(c → {"path", "turn"}) → Book."""
    key = ("PB", id(ctx), name)
    if key in _CACHE:
        return _CACHE[key]
    F = frame(ctx)
    paths, turn = {}, {}
    for c in (0.0,) + tuple(costs):
        sl = path_fn(c)
        paths[c], turn[c] = sl["path"], sl.get("turn")
    b = Book(name, F, paths, turn)
    _CACHE[key] = b
    return b


def offense_v0(ctx):
    return stock_book(ctx, "V0", ctx.V0_targets, 3)


def defense_bmrot(ctx):
    """x-bmrot 수비 장부 — 얼린 핀 · 구성 관문을 다시 단언한 뒤(어긋나면 멈춘다) 월간 되맞춤 · 흘러감 장부."""
    import q_bmrot_leg as BL
    BL.verify_pins(ctx)
    T, _ = BL.targets(ctx.Wd)
    return path_book(ctx, "x-bmrot", lambda c: BL.leg_path(ctx.Wd, T, c))


def defense(ctx):
    """카드 Q03 · Q10 · Q06 의 DEFENSE 장부 — DEFENSE_LEG 로 한 곳에서 고른다."""
    if DEFENSE_LEG == "x-bmrot":
        return defense_bmrot(ctx)
    if DEFENSE_LEG == "T-bill":
        return tbill_book(ctx)
    raise ValueError("DEFENSE_LEG %r" % DEFENSE_LEG)


def tbill_book(ctx):
    """T-bill — 그달 rf_monthly 를 그달 거래일 수로 나눠 복리(qg_lab.sleeve 의 현금과 같은 식) · 매매 비용 없음(현금)."""
    key = ("TBILL", id(ctx))
    if key in _CACHE:
        return _CACHE[key]
    F = frame(ctx)
    G = ctx.G
    g = np.ones(F.T)
    for k, m in enumerate(F.months):
        a, b = F.mends[k], F.mends[k + 1]
        rf_d = (1 + float(G.RF.get(Q.mshift(m, 1), 0.0))) ** (1.0 / max(1, b - a)) - 1
        g[a + 1 - (F.i0 + 1): b + 1 - (F.i0 + 1)] = 1 + rf_d
    bk = Book.__new__(Book)
    bk.name, bk.g0, bk.lg0 = "T-bill", g, np.log(g)
    bk.lf = {COST: np.zeros(F.T), COST20: np.zeros(F.T)}
    bk.turn, bk.reb_days, bk.cash = {COST: 0.0, COST20: 0.0}, np.array([], int), True
    _CACHE[key] = bk
    return bk


def spy_book(ctx):
    """SPY 총수익(종목 격자의 IX_TR) — 논문 비교용 SPY/T-bill 0/1 팔."""
    key = ("SPY", id(ctx))
    if key in _CACHE:
        return _CACHE[key]
    F = frame(ctx)
    IX = ctx.G.IX_TR
    g = np.array([IX[d] / IX[d - 1] for d in F.day])
    bk = Book.__new__(Book)
    bk.name, bk.g0, bk.lg0 = "SPY", g, np.log(g)
    bk.lf = {COST: np.zeros(F.T), COST20: np.zeros(F.T)}
    bk.turn, bk.reb_days, bk.cash = {COST: 0.0, COST20: 0.0}, np.array([], int), False
    _CACHE[key] = bk
    return bk


def frame(ctx):
    key = ("F", id(ctx))
    if key not in _CACHE:
        _CACHE[key] = Frame(ctx)
    return _CACHE[key]


# ── 위치 ─────────────────────────────────────────────────────────────────
def pos_from_daily(F, state_by_date, delay=1):
    """일간 상태 {날짜: 1(BULL/공격) · 0(BEAR/수비)} → 수익일 j 의 위치. 상태 s_t 는 종가 t+delay 에 매매 → 수익일 t+delay+1 부터.
    즉 수익일 d 의 위치 = 상태(d − delay − 1). 상태가 없는 날(첫 적합 전)은 공격(카드 FALLBACK)."""
    G = F.G
    pos = np.ones(F.T, np.int8)
    for j, d in enumerate(F.day):
        s = state_by_date.get(G.dates[d - delay - 1])
        pos[j] = 1 if s is None else int(s)
    return pos


def pos_from_monthly(F, state_by_month):
    """월간 상태 {편입월 m: 1 · 0} → 보유월 m+1 의 모든 수익일 위치(월말 m 종가에 매매)."""
    pos = np.empty(F.T, np.int8)
    for k, m in enumerate(F.months):
        a = F.mstart[k]
        b = F.mstart[k + 1] if k + 1 < len(F.months) else F.T
        pos[a:b] = int(state_by_month[m])
    return pos


# ── 슬리브 · 펀드 ────────────────────────────────────────────────────────
def _close_terms(pos, bO, bD, c):
    """종가 비용 로그 — 교체 날 log(1 − 2c) · 아니면 그 뒤 든 장부의 되맞춤 비용 배수."""
    T = len(pos)
    nxt = np.empty_like(pos)
    nxt[:-1] = pos[1:]
    nxt[-1] = pos[-1]
    sw = (nxt != pos)
    cO = bO.lf[c] if c in bO.lf else np.zeros(T)
    cD = bD.lf[c] if c in bD.lf else np.zeros(T)
    reb = np.where(nxt == 1, cO, cD)
    sc = _switch_cost(bO, bD, c)
    return np.where(sw, math.log(1 - sc), reb), sw


def _switch_cost(bO, bD, c):
    """교체 한 번의 비용(슬리브 가치 몫) — 판 장부 c + 산 장부 c · 현금(T-bill) 쪽은 매매 비용이 없다."""
    return (0.0 if bO.cash else c) + (0.0 if bD.cash else c)


def sleeve_daily(pos, bO, bD, c):
    """교체 슬리브의 일간 로그 성장(수익일 j · 그날 종가 비용 포함)."""
    cl, sw = _close_terms(pos, bO, bD, c)
    lg = np.where(pos == 1, bO.lg0, bD.lg0) + cl
    return lg, sw


def to_path(F, lg):
    v = np.exp(np.cumsum(lg))
    path = {F.i0: 1.0}
    for j, d in enumerate(F.day):
        path[int(d)] = float(v[j])
    return path


def switch_fr(ctx, pos, bO, bD, c=COST, basis="TR"):
    """교체 규칙의 펀드 결과(fund_from_path) + 회전(편도 · 연) · 교체 수 · 비용 끌림(슬리브 연 %)."""
    F = frame(ctx)
    lg, sw = sleeve_daily(pos, bO, bD, c)
    nxt = np.append(pos[1:], pos[-1])
    own = 0.0
    for bk, flag in ((bO, 1), (bD, 0)):
        if c in bk.lf:
            tt = (1.0 - np.exp(bk.lf[c])) / c                    # 그날 종가 양방향 거래율
            own += float((tt * ((nxt == flag) & ~sw)).sum())
    n_sw = int(sw.sum())
    sc = _switch_cost(bO, bD, c)
    fr = Q.fund_from_path(F.G, {"path": to_path(F, lg), "turn": (own + 2.0 * n_sw) / 2.0 / F.years}, F.months, cost=c, basis=basis)
    fr["n_switch"] = n_sw
    fr["cost_drag"] = float((c * own + sc * n_sw) / F.years * 100)
    fr["turn_ex_switch"] = own / 2.0 / F.years
    return fr


def mix_fr(ctx, shares, bO, bD, c=COST, basis="TR"):
    """월별 공격 몫 s_k(보유월 k) 혼합 — 월초 s_k/(1 − s_k) · 월 안 흘러감(각 장부의 비용 포함 경로 = 자기 회전) ·
    월말 다음 몫으로 되맞춤 편도 c(거래액 · 현금 쪽은 무비용). D(고정 ē)와 Q10 3국면 팔이 쓴다."""
    F = frame(ctx)
    lO = bO.lg0 + bO.lf.get(c, 0.0)
    lD = bD.lg0 + bD.lf.get(c, 0.0)
    path = {F.i0: 1.0}
    V, trs = 1.0, 0.0
    nM = len(F.months)
    shares = np.asarray(shares, float)
    assert len(shares) == nM and shares.min() >= 0 and shares.max() <= 1
    for k in range(nM):
        a = F.mstart[k]
        b = F.mstart[k + 1] if k + 1 < nM else F.T
        s_ = shares[k]
        cO = np.exp(np.cumsum(lO[a:b]))
        cD = np.exp(np.cumsum(lD[a:b]))
        vals = V * (s_ * cO + (1 - s_) * cD)
        for j in range(a, b):
            path[int(F.day[j])] = float(vals[j - a])
        if k + 1 < nM:                                      # 마지막 월말(2026-08)은 편입이 끝나 되맞춤이 없다
            s1 = shares[k + 1]
            Ve = float(vals[-1])
            tO = abs(s1 * Ve - V * s_ * cO[-1])
            tD = abs((1 - s1) * Ve - V * (1 - s_) * cD[-1])
            Ve -= c * ((0.0 if bO.cash else tO) + (0.0 if bD.cash else tD))
            trs += (tO + tD) / float(vals[-1])
            path[int(F.day[b - 1])] = Ve
            V = Ve
        else:
            V = float(vals[-1])
    own = sum(float((1.0 - np.exp(bk.lf[c])).sum()) / c * float(np.mean(w)) for bk, w in ((bO, shares), (bD, 1 - shares)) if c in bk.lf)
    fr = Q.fund_from_path(F.G, {"path": path, "turn": (trs + own) / 2.0 / F.years}, F.months, cost=c, basis=basis)
    fr["cost_drag"] = float(c * (trs + own) / F.years * 100)
    return fr


def blend_fr(ctx, e_bar, bO, bD, c=COST, basis="TR"):
    """고정 혼합 D — 매월 초 ē/(1 − ē) 로 되맞춤(mix_fr 의 상수 몫)."""
    fr = mix_fr(ctx, np.full(len(frame(ctx).months), e_bar), bO, bD, c, basis)
    fr["e_bar"] = e_bar
    return fr


# ── 월 닫힌 식(순열용) ────────────────────────────────────────────────────
def month_sums(F, lg):
    return np.add.reduceat(lg, F.mstart)


def fund_ex_closed(F, gS, basis="TR", c=COST):
    """월초 0.9/0.1 · 월말 되돌림 비용 2c·|슬리브 몫 − 0.1| — fund_from_path 의 월 초과(%)와 같은 값."""
    gI = F.gIX[basis]
    v = 0.9 * gI + 0.1 * gS
    dev = np.abs(0.1 * gS / v - 0.1)
    f = v * (1 - 2 * c * dev)
    return (f - gI) * 100


def month_growth(F, bk, c=COST):
    """장부 하나의 보유월 성장(비용 c 포함 경로 = 자기 회전 안) — mix_fr 가 월마다 쓰는 cO · cD 의 끝값."""
    return np.exp(month_sums(F, bk.lg0 + bk.lf.get(c, 0.0)))


def mix_ex_closed(F, shares, gO, gD, cashO, cashD, basis="TR", c=COST):
    """mix_fr 의 월 닫힌 식 — 월초 몫 s_k · 월 안 흘러감 · 월말 다음 몫 s_{k+1} 로 되맞춤 편도 c(현금 쪽 무비용) · 마지막 달 되맞춤 없음
    → 펀드 월 초과(%). 순열 뽑기마다 D 를 그 뽑기의 ē 로 다시 짤 때 쓴다(selftest: = mix_fr)."""
    s = np.broadcast_to(np.asarray(shares, float), np.shape(gO)).astype(float)
    g = s * gO + (1 - s) * gD
    s1 = np.append(s[1:], s[-1])
    tO = np.abs(s1 * g - s * gO)
    tD = np.abs((1 - s1) * g - (1 - s) * gD)
    cost = c * ((0.0 if cashO else tO) + (0.0 if cashD else tD))
    cost = np.asarray(cost, float) * np.ones_like(g)
    cost[-1] = 0.0
    return fund_ex_closed(F, g - cost, basis, c)


def perm_p(t_obs, tp):
    """p = (1 + #{t_perm ≥ t_obs})/(N + 1) — t_obs 가 없으면(n < 5 · NW 분산 0) 1.0(기각 못 함 · 닫힌 쪽). 뽑기 t 가 없으면 −∞ 로 센다."""
    if t_obs is None:
        return 1.0
    return (1 + sum(1 for v in tp if v is not None and v >= t_obs)) / (len(tp) + 1)


# ── 구간 섞기 ─────────────────────────────────────────────────────────────
def runs(x):
    """0/1 계열 → (첫 상태, 구간 길이 배열)."""
    x = np.asarray(x)
    cut = np.flatnonzero(np.diff(x)) + 1
    b = np.concatenate([[0], cut, [len(x)]])
    return int(x[0]), np.diff(b)


def seg_shuffle(x, rng):
    """공격(1) 구간 길이 · 수비(0) 구간 길이를 따로 섞고 참 첫 상태부터 번갈아 엮는다(교체 수 · 몫 보존)."""
    s0, L = runs(x)
    st = np.array([s0 if k % 2 == 0 else 1 - s0 for k in range(len(L))], np.int8)
    L1, L0 = L[st == 1].copy(), L[st == 0].copy()
    rng.shuffle(L1)
    rng.shuffle(L0)
    Ln = np.empty_like(L)
    Ln[st == 1], Ln[st == 0] = L1, L0
    return np.repeat(st, Ln).astype(x.dtype)


def perm_test(ctx, pos, bO, bD, xD, dmask, nperm, seed=SEED, unit="day", months_state=None, basis="TR", c=COST, fr_ex=None):
    """학생화 구간 섞기 순열 — t = NW(3) t(평균 Δ^D) · 위약 = 하락월 평균 Δ^D(같은 뽑기).
    unit 'day' = 일간 위치 계열을 섞는다 · 'month' = 월간 상태 계열을 섞고 보유월로 편다."""
    F = frame(ctx)
    lg, _ = sleeve_daily(pos, bO, bD, c)
    x_obs = fund_ex_closed(F, np.exp(month_sums(F, lg)), basis, c)
    if fr_ex is not None:
        assert np.max(np.abs(x_obs - fr_ex)) < 1e-8, "닫힌 식 ≠ fund_from_path"
    # D 의 월 닫힌 식 — 참 ē 에서 blend_fr 와 같아야 한다 · 뽑기마다 그 뽑기의 ē 로 다시 짠다
    gO, gD = month_growth(F, bO, c), month_growth(F, bD, c)
    e_obs = float(pos.mean())
    xD_chk = mix_ex_closed(F, e_obs, gO, gD, bO.cash, bD.cash, basis, c)
    assert np.max(np.abs(xD_chk - xD)) < 1e-8, "D 닫힌 식 ≠ blend_fr"
    d_obs = x_obs - xD
    t_obs = _nw_t(d_obs)
    dn_obs = float(d_obs[dmask].mean())
    rng = np.random.default_rng(seed)
    tp, dn, es = [], [], []
    ms = np.array([months_state[m] for m in F.months], np.int8) if unit == "month" else None
    mlen = np.diff(np.append(F.mstart, F.T))
    if unit == "month":
        assert np.array_equal(np.repeat(ms, mlen), pos), "월간 상태와 위치가 다르다"
    for _ in range(nperm):
        if unit == "month":
            p = np.repeat(seg_shuffle(ms, rng), mlen)
        else:
            p = seg_shuffle(pos, rng)
        lgp, _ = sleeve_daily(p, bO, bD, c)
        xp = fund_ex_closed(F, np.exp(month_sums(F, lgp)), basis, c)
        e_p = float(p.mean())
        dp = xp - (xD if e_p == e_obs else mix_ex_closed(F, e_p, gO, gD, bO.cash, bD.cash, basis, c))
        es.append(e_p)
        tp.append(_nw_t(dp))
        dn.append(float(dp[dmask].mean()))
    tp = [(-1e9 if v is None else float(v)) for v in tp]
    p = perm_p(t_obs, tp)
    perm = {"t_obs": t_obs, "t_perm": tp, "p": p, "n": nperm, "seed": seed, "unit": unit,
            "D_per_draw": "뽑기마다 D = mix(ē_draw) 로 다시 짠다(월 닫힌 식)",
            "e_draw_min_max": ([min(es), max(es)] if es else None), "e_obs": e_obs}
    if t_obs is None:
        perm["p_note"] = "t_obs 없음(n < 5 또는 NW 분산 0) → p = 1(기각 못 함)"
    return (perm,
            {"down_dD": {"stat": "하락월(39) 평균 Δ^D = X_rule − X_D(뽑기는 제 ē 의 D 대비) — 같은 구간 섞기 뽑기(교체 수 보존 · ē 는 월 단위면 거래일 가중으로 조금 움직인다)",
                         "draws": dn, "true": dn_obs}})


def pct_rank(draws, true):
    """랩 규약(eg30plus) — 참값보다 작은 뽑기의 백분율."""
    return float(np.mean(np.asarray(draws) < true) * 100)


# ── 쌍둥이 ───────────────────────────────────────────────────────────────
def sma200_state(ctx):
    """^GSPC 종가 < 200일 단순평균(그날 포함 · tech_backtest.sma) 이면 수비(0) — {날짜: 1/0}."""
    A = ctx.A
    p = A.px["^GSPC"]
    out = {}
    cs = np.cumsum(np.where(p == p, p, 0.0))
    for i in range(SMA_N - 1, len(p)):
        s = (cs[i] - (cs[i - SMA_N] if i >= SMA_N else 0.0)) / SMA_N
        out[A.dates[i]] = 0 if p[i] < s else 1
    return out


def vol63(ctx):
    """SPY 63일 실현변동성(일간 단순수익 표본 sd) — {날짜: σ} (2006-04 부터 창이 찬다)."""
    A = ctx.A
    p = A.px["SPY"]
    r = p[1:] / p[:-1] - 1
    out = {}
    for i in range(VOL_N, len(p)):
        w = r[i - VOL_N:i]
        out[A.dates[i]] = float(np.std(w, ddof=1))
    return out


def vol_state_daily(ctx, e_bar):
    """ē 맞춘 변동성 쌍둥이(일간) — σ_t ≥ 확장 분위수({σ_s : 2006-04 ≤ s ≤ t}, 수준 ē)이면 수비."""
    v = vol63(ctx)
    ds = sorted(d for d in v if d[:7] >= VOL_FROM)
    arr = np.array([v[d] for d in ds])
    out = {}
    F = frame(ctx)
    need = set(F.G.dates[d - 2] for d in F.day)
    for k, d in enumerate(ds):
        if d not in need:
            continue
        q = float(np.quantile(arr[:k + 1], e_bar))
        out[d] = 0 if arr[k] >= q else 1
    return out


def vol_state_monthly(ctx, e_bar, months):
    """ē 맞춘 변동성 쌍둥이(월간) — 월말 σ ≥ 월말 표본(2006-04 ~ m)의 확장 분위수(수준 ē)이면 m+1 수비."""
    v = vol63(ctx)
    A = ctx.A
    mends = sorted(mm for mm in A.me if mm >= VOL_FROM)
    arr = np.array([v[A.dates[A.me[mm]]] for mm in mends])
    pos = {mm: k for k, mm in enumerate(mends)}
    out = {}
    for m in months:
        k = pos[m]
        q = float(np.quantile(arr[:k + 1], e_bar))
        out[m] = 0 if arr[k] >= q else 1
    return out


# ── 진단 도우미 ───────────────────────────────────────────────────────────
def off_share_by_month(F, pos):
    return np.array([1.0 - pos[F.mstart[k]:(F.mstart[k + 1] if k + 1 < len(F.months) else F.T)].mean() for k in range(len(F.months))])


def f0_check(F, pos, dmask, n_off=F0_OFF, n_offdown=F0_OFFDOWN):
    """F0 — 수비 몫 ≥ 50% 인 보유월 ≥ 12 이고 그중 하락월 ≥ 6. 아니면 측정 불가."""
    off = off_share_by_month(F, pos) >= 0.5
    a, b = int(off.sum()), int((off & dmask).sum())
    ok = a >= n_off and b >= n_offdown
    return {"ok": bool(ok), "why": "수비 몫 ≥ 50%% 인 달 %d(≥ %d) · 그중 하락월 %d(≥ %d)" % (a, n_off, b, n_offdown), "n_off": a, "n_off_down": b}


def rebound_miss(ctx, pos, dD):
    """REBOUND-MISS — 공격→수비 교체(종가) 뒤 63거래일 안에 시작한 급등월(SURGE-M)들의 평균 Δ^D. 3달 이상일 때만 판정(≥ 0)."""
    F = frame(ctx)
    ME = Q.load("mech_episodes.json")
    nxt = np.append(pos[1:], pos[-1])
    outs = [F.day[j] for j in np.flatnonzero((pos == 1) & (nxt == 0))]           # 교체 종가 날 인덱스
    first = {h: F.mends[k] + 1 for k, h in enumerate(F.hold)}                     # 그 보유월 첫 거래일
    hp = {h: k for k, h in enumerate(F.hold)}
    ms = []
    for h in ME["months"]["surge_m"]:
        if h not in hp:
            continue
        f = first[h]
        if any(0 <= f - o <= REB_WIN for o in outs):
            ms.append(h)
    vals = [float(dD[hp[h]]) for h in ms]
    mean = float(np.mean(vals)) if vals else None
    return {"months": ms, "n": len(ms), "mean_dD": mean, "applies": len(ms) >= REB_MIN,
            "ok": (None if len(ms) < REB_MIN else bool(mean >= 0)), "n_switch_out": len(outs)}


def book_drag(bk, c, F):
    """장부 하나를 늘 들 때의 비용 끌림(슬리브 연 %) — 되맞춤 날 c·거래율의 합 ÷ 햇수."""
    if c not in bk.lf:
        return 0.0
    return float((1.0 - np.exp(bk.lf[c])).sum() / F.years * 100)


def shifts_per_year(F, pos):
    return float(np.sum(pos[1:] != pos[:-1]) / F.years)


def hash_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


# ── 한 카드의 부류 S 결과 ──────────────────────────────────────────────────
def class_s(ctx, code, cls, slot, pos, bO, bD, nperm, unit="day", months_state=None, twins=None, arms=None, extra_log=None,
            parent=None, f0=None, targets_hash_src=None):
    """교체 카드 한 장의 CardResult — 규칙 fr/fr_pr/fr20 · D · D20 · V0 · 순열 · 위약 · 쌍둥이(팔) · REBOUND-MISS · F0."""
    F = frame(ctx)
    dm = F.dmask()
    e_bar = float(pos.mean())                               # 실현 공격 몫(수익일 가중)
    fr = switch_fr(ctx, pos, bO, bD, COST, "TR")
    fr_pr = switch_fr(ctx, pos, bO, bD, COST, "PR")
    fr20 = switch_fr(ctx, pos, bO, bD, COST20, "TR")
    D = blend_fr(ctx, e_bar, bO, bD, COST, "TR")
    D20 = blend_fr(ctx, e_bar, bO, bD, COST20, "TR")
    Dpr = blend_fr(ctx, e_bar, bO, bD, COST, "PR")
    perm, plac = perm_test(ctx, pos, bO, bD, D["ex"], dm, nperm, SEED, unit, months_state, fr_ex=fr["ex"])
    dD = fr["ex"] - D["ex"]
    res = {"code": code, "cls": cls, "slot": slot, "fr": fr, "fr_pr": fr_pr, "fr20": fr20,
           "controls": {"D": D, "D20": D20, "D_pr": Dpr, "V0": ctx.V0()}, "arms": dict(arms or {}),
           "placebo": plac, "perm": perm, "g4": {}, "label_caps": {},
           "f0": f0 if f0 is not None else f0_check(F, pos, dm),
           "targets_hash": hash_obj({"pos": "".join(map(str, pos.tolist())), "src": targets_hash_src}),
           "log": {"e_bar": e_bar, "n_switch": fr["n_switch"], "shifts_per_year": shifts_per_year(F, pos),
                   "defense_days": int((pos == 0).sum()), "off_months_ge50": int((off_share_by_month(F, pos) >= 0.5).sum()),
                   "turn_oneway_yr": fr["turn"], "cost_drag_pct_yr": fr["cost_drag"],
                   # 러너 G3 키(qbatch_run.judge_card: log["cost_drag"] ≤ 2 × cd0 · cd0 = 2·V0.turn·COST) — 같은 단위(슬리브 연 소수)
                   "cost_drag": fr["cost_drag"] / 100.0, "v0_cost_drag": book_drag(bO, COST, F) / 100.0,
                   "cost_drag_unit": "cost_drag · v0_cost_drag = 슬리브 연 비용 끌림(소수 · 교체 비용 포함 · 첫 매수 미과금) · *_pct_yr = 같은 값 %",
                   "rebound_miss": rebound_miss(ctx, pos, dD), "defense": bD.name, "offense": bO.name, "defense_leg": DEFENSE_LEG,
                   "placebo_rank_def": "100 × mean(draws < true) · 관문 ≥ 95",
                   "v0_cost_drag_pct_yr": book_drag(bO, COST, F), "D_cost_drag_pct_yr": D["cost_drag"]}}
    if bD.name == "x-bmrot":
        import q_bmrot_leg as BL
        res["log"]["defense_pins"] = BL.verify_pins(ctx)
    if parent:
        res["parent"] = parent
    tw = {}
    for nm, tpos in (twins or {}).items():
        tfr = switch_fr(ctx, tpos, bO, bD, COST, "TR")
        res["arms"]["twin_" + nm] = tfr
        d = fr["ex"] - tfr["ex"]
        tw[nm] = {"all": float(d.mean()) > 0, "down": float(d[dm].mean()) > 0, "e_bar": float(tpos.mean()),
                  "n_switch": tfr["n_switch"]}
    res["log"]["twins"] = tw
    card_interp = list((extra_log or {}).get("interpretation") or [])
    if extra_log:
        res["log"].update(extra_log)
    res["log"]["interpretation"] = card_interp + INTERP_FRAME + (BL_INTERP() if bD.name == "x-bmrot" else
                                                                 ["수비 다리 = T-bill(DEFENSE_LEG · 카드의 선언된 대체)"])
    check_runner_keys(res)
    return res, tw, plac


def BL_INTERP():
    import q_bmrot_leg as BL
    return list(BL.INTERP_LEG)


# 교체 틀의 읽기(Q03 · Q10 · Q06 공통) — log["interpretation"] 에 카드 읽기 뒤로 붙는다
INTERP_FRAME = [
    "틀: ē = 보유 창 수익일 중 공격 위치 몫(1일 지연 뒤) · D = ē·OFFENSE + (1 − ē)·DEFENSE 월말 되맞춤 편도 10bp + 각 장부 자기 회전 · 마지막 월말(2026-08)은 되맞춤 없음",
    "틀: 교체 = 판 장부 10bp + 산 장부 10bp(슬리브 가치 · 현금 쪽 0) · 교체 날 판 장부의 되맞춤은 안 물고 산 장부의 되맞춤은 교체 매수가 덮는다 · 첫 매수(2016-08-31)는 V0 처럼 미과금",
    "틀: 순열 뽑기마다 D 를 그 뽑기의 ē 로 다시 짠다(월 단위 섞기는 거래일 가중 ē 가 조금 움직인다 · 일 단위는 그대로) · t_obs 가 없으면 p = 1",
    "틀: 비용 끌림(G3 하한) = 슬리브 연 비용(교체 비용 + 든 장부 되맞춤 · 소수) — log.cost_drag 와 log.v0_cost_drag(같은 장부 분해의 V0) · "
    "러너의 cd0 = 2·V0.turn·COST 는 V0 첫 매수 1회(연 0.01%p)를 더 센다",
    "틀: REBOUND-MISS 는 G2 조건이라 log.rebound_miss{applies, ok} 에 둔다(g4 에 넣지 않는다 — G4 로 두 번 세지 않게)"]


def check_runner_keys(res):
    """러너(qbatch_run.judge_card)가 읽는 키가 CardResult 에 다 있는가 — 모자라면 굽기 전에(연기 시험에서) 멈춘다."""
    need = ("code", "cls", "slot", "fr", "fr_pr", "fr20", "controls", "arms", "placebo", "perm", "g4", "label_caps", "f0", "targets_hash", "log")
    miss = [k for k in need if k not in res]
    assert not miss, "CardResult 키 없음 %s" % miss
    if res["cls"] == "S":
        assert "D" in res["controls"] and "D20" in res["controls"], "부류 S 는 controls D · D20 필수"
        p = res["perm"].get("p")
        assert isinstance(p, float) and 0.0 < p <= 1.0, "perm.p %r" % (p,)
    lg = res["log"]
    rm = lg.get("rebound_miss")
    assert isinstance(rm, dict) and "applies" in rm and "ok" in rm, "log.rebound_miss{applies, ok} 없음"
    assert isinstance(lg.get("e_bar"), float), "log.e_bar 없음"
    if res["code"] in ("Q03", "Q10"):
        assert isinstance(lg.get("cost_drag"), float) and isinstance(lg.get("v0_cost_drag"), float), "log.cost_drag(소수) 없음"
    assert isinstance(res["f0"].get("ok"), bool) and isinstance(lg.get("interpretation"), list)
    return True


def measured_rows(res, dm):
    """측정만(부류 M) 보고 행 — Δ^D(전 월 · 하락월) · 규칙 − 쌍둥이(전 월 · 하락월) · 순열 p · 위약 백분위. 판정에 쓰지 않는다 · run() 안에서만."""
    import eg30plus as E
    fr, D = res["fr"], res["controls"]["D"]
    d = fr["ex"] - D["ex"]
    out = {"dD_all_mean": float(d.mean()), "dD_all_nw_t": E.nw_t(d), "dD_down_mean": float(d[dm].mean()), "dD_down_t": E.down_t(d, dm),
           "perm_p": res["perm"].get("p"), "twins": {}}
    for nm in sorted(res["arms"]):
        if nm.startswith("twin_"):
            x = fr["ex"] - res["arms"][nm]["ex"]
            out["twins"][nm] = {"all_mean": float(x.mean()), "down_mean": float(x[dm].mean()), "all_nw_t": E.nw_t(x)}
    pl = (res.get("placebo") or {}).get("down_dD")
    if pl:
        out["placebo_rank_down_dD"] = pct_rank(pl["draws"], pl["true"])
    return out


# ── 계약 ─────────────────────────────────────────────────────────────────
def selftest():
    """합성 자료 — 구간 섞기(교체 수 · ē · 번갈음 보존) · 월 닫힌 식 = 일간 되돌림 틀 · 교체 비용 · 혼합 D 의 되맞춤."""
    tests = {}
    rng = np.random.default_rng(SEED)
    x = np.repeat(np.array([1, 0, 1, 0, 1, 0, 1], np.int8), [40, 7, 90, 12, 33, 60, 5])
    y = seg_shuffle(x, rng)
    s0, L = runs(x)
    s1, L1 = runs(y)
    tests["shuffle_preserve"] = bool(s0 == s1 and len(L) == len(L1) and y.sum() == x.sum() and len(y) == len(x)
                                     and sorted(L[::2]) == sorted(L1[::2]) and sorted(L[1::2]) == sorted(L1[1::2]))
    # 월 닫힌 식 = fund_from_path 의 일간 되돌림(합성 격자)
    class _G:
        pass
    n_m, dpm = 6, 20
    D = n_m * dpm + 1
    G = _G()
    G.me = {"2020-%02d" % (k + 1): k * dpm for k in range(n_m + 1)}
    ix = np.cumprod(np.r_[1.0, 1 + rng.normal(0.0004, 0.01, D - 1)])
    G.IX_TR = G.IX_PR = ix
    sl = np.cumprod(np.r_[1.0, 1 + rng.normal(0.0006, 0.02, D - 1)])
    months = ["2020-%02d" % (k + 1) for k in range(n_m)]
    fr = Q.fund_from_path(G, {"path": {i: float(sl[i]) for i in range(D)}}, months)
    gS = np.array([sl[(k + 1) * dpm] / sl[k * dpm] for k in range(n_m)])
    gI = np.array([ix[(k + 1) * dpm] / ix[k * dpm] for k in range(n_m)])
    Fk = _G(); Fk.gIX = {"TR": gI}
    tests["closed_form_eq_fund_from_path"] = bool(np.max(np.abs(fund_ex_closed(Fk, gS) - fr["ex"])) < 1e-10)
    # 교체 비용 — 한 번 바꾸면 2c, 되맞춤 날이 겹치면 판 장부 비용은 안 문다
    class _B:
        pass
    T = 10
    bO, bD = _B(), _B()
    bO.cash = bD.cash = False
    bO.lg0, bD.lg0 = np.zeros(T), np.zeros(T)
    bO.lf = {COST: np.zeros(T)}; bD.lf = {COST: np.zeros(T)}
    bD.lf[COST][4] = math.log(1 - COST * 0.5)             # 수비 장부가 4일 종가에 되맞춤
    bO.lf[COST][4] = math.log(1 - COST * 0.3)
    pos = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0], np.int8)   # 4일 종가 교체
    lg, sw = sleeve_daily(pos, bO, bD, COST)
    tests["switch_cost"] = bool(abs(lg.sum() - math.log(1 - 2 * COST)) < 1e-15 and sw.sum() == 1)
    pos2 = np.ones(T, np.int8)
    lg2, _ = sleeve_daily(pos2, bO, bD, COST)
    tests["own_rebalance"] = bool(abs(lg2.sum() - math.log(1 - COST * 0.3)) < 1e-15)
    # NW t 는 eg30plus 의 것
    tests["nw_from_eg30plus"] = _nw_t(np.r_[np.ones(5), -np.ones(5)] + 0.1) is not None
    # D 의 월 닫힌 식 = mix_fr(합성 틀 · 월마다 다른 몫 · 되맞춤 날 있는 장부 · 현금 장부)
    class _Ctx:
        pass
    cx = _Ctx()
    Fs = _G()
    Fs.G, Fs.months = G, months
    Fs.i0, Fs.iE, Fs.T = 0, n_m * dpm, n_m * dpm
    Fs.day = np.arange(1, Fs.T + 1)
    Fs.mends = np.array([k * dpm for k in range(n_m + 1)])
    Fs.mstart = np.array([k * dpm for k in range(n_m)])
    Fs.gIX = {"TR": gI, "PR": gI}
    Fs.years = Fs.T / 252.0
    _CACHE[("F", id(cx))] = Fs
    try:
        def _bk(cash, seed_):
            r_ = np.random.default_rng(SEED + seed_)
            b = _B()
            b.cash = cash
            b.lg0 = np.log(1 + r_.normal(0.0005, 0.01, Fs.T))
            lf = np.zeros(Fs.T)
            if not cash:
                lf[[dpm - 1, 3 * dpm - 1, 5 * dpm - 1]] = np.log(1 - COST * r_.uniform(0.2, 1.5, 3))
            b.lf = {COST: lf}
            return b
        oK = True
        for cO_, cD_ in ((False, False), (False, True)):
            bO_, bD_ = _bk(cO_, 1), _bk(cD_, 2)
            gO_, gD_ = month_growth(Fs, bO_), month_growth(Fs, bD_)
            for sh in (np.full(n_m, 0.62), np.array([1.0, 0.5, 0.0, 0.3, 1.0, 0.8])):
                a_ = mix_ex_closed(Fs, sh, gO_, gD_, bO_.cash, bD_.cash)
                b_ = mix_fr(cx, sh, bO_, bD_)["ex"]
                oK &= bool(np.max(np.abs(a_ - b_)) < 1e-10)
        tests["mix_closed_eq_mix_fr"] = oK
    finally:
        _CACHE.pop(("F", id(cx)), None)
    # 순열 p — t_obs 가 없으면 1(열린 쪽으로 새지 않는다) · 있으면 (1 + #≥)/(N + 1)
    tests["perm_p_fail_closed"] = bool(perm_p(None, [0.1, -1e9]) == 1.0 and perm_p(1.0, [0.5, 1.5, -1e9]) == 2 / 4
                                       and perm_p(_nw_t(np.zeros(10)), [0.0]) == 1.0)
    return {"ok": all(bool(v) for v in tests.values()), "tests": tests}


def dry(ctx):
    """구성만 — 창 · 격자 일치 · 장부 되맞춤 날 수. 수익 없음."""
    F = frame(ctx)
    A = ctx.A
    sd = set(A.dates)
    miss = [F.G.dates[d] for d in range(F.i0 - 2, F.iE + 1) if F.G.dates[d] not in sd]
    win = [d for d in A.dates if F.G.dates[F.i0 - 2] <= d <= F.G.dates[F.iE]]
    bO, bD = offense_v0(ctx), defense(ctx)
    # 틀 항등(차이만 · 수준 없음): 늘 공격이면 V0 공개 판과 같고 · 늘 수비면 다리 경로 그대로 · ē = 1 혼합도 V0 · 닫힌 식 = fund_from_path
    ones, zeros = np.ones(F.T, np.int8), np.zeros(F.T, np.int8)
    v0 = ctx.V0()
    s1 = switch_fr(ctx, ones, bO, bD)
    lg, _ = sleeve_daily(ones, bO, bD, COST)
    ident = {"all_offense_vs_V0": float(np.max(np.abs(s1["ex"] - v0["ex"]))),
             "blend_e1_vs_V0": float(np.max(np.abs(blend_fr(ctx, 1.0, bO, bD)["ex"] - v0["ex"]))),
             "closed_vs_fund_from_path": float(np.max(np.abs(fund_ex_closed(F, np.exp(month_sums(F, lg))) - s1["ex"])))}
    if bD.name == "x-bmrot":
        import q_bmrot_leg as BL
        Tb, _ = BL.targets(ctx.Wd)
        legfr = Q.fund_from_path(F.G, BL.leg_path(ctx.Wd, Tb, COST), F.months)
        ident["all_defense_vs_leg"] = float(np.max(np.abs(switch_fr(ctx, zeros, bO, bD)["ex"] - legfr["ex"])))
    # D 의 월 닫힌 식(순열 뽑기용) = blend_fr — 몫 0.3 · 0.7 에서(차이만)
    gO, gD = month_growth(F, bO), month_growth(F, bD)
    for s_ in (0.3, 0.7):
        ident["mix_closed_vs_blend_%.1f" % s_] = float(np.max(np.abs(mix_ex_closed(F, s_, gO, gD, bO.cash, bD.cash) - blend_fr(ctx, s_, bO, bD)["ex"])))
    assert all(v < 1e-9 for v in ident.values()), ident
    reb_me = set(int(x) for x in F.mends)
    assert all(int(F.day[j]) in reb_me for j in bO.reb_days) and all(int(F.day[j]) in reb_me for j in bD.reb_days), "되맞춤 날이 월말이 아니다"
    # 비용 끌림 단위(러너 G3): 러너 cd0 = 2·V0.turn·COST(소수 · 첫 매수 포함) ↔ 같은 장부 분해의 V0 끌림(소수 · 첫 매수 미과금)
    cd0_runner = 2 * (v0.get("turn") or 0) * COST
    cd0_book = book_drag(bO, COST, F) / 100.0
    return {"T_days": F.T, "n_months": len(F.months), "grid_missing_in_assets": len(miss), "assets_extra_in_window": len(win) - (F.iE - F.i0 + 3),
            "defense_leg": DEFENSE_LEG, "offense_reb_days": int(len(bO.reb_days)), "defense_reb_days": int(len(bD.reb_days)),
            "offense_turn": bO.turn.get(COST), "defense_turn": bD.turn.get(COST), "identity_max_abs_pct": ident,
            "cost_drag_units": {"runner_cd0": cd0_runner, "v0_book_drag": cd0_book, "gap": cd0_runner - cd0_book,
                                "first_buy_term": 2 * (1.0 / len(F.months)) / 2 * 12 * COST}}


def run(ctx):
    return {}


if __name__ == "__main__":
    print(json.dumps(selftest(), ensure_ascii=False, default=str))
    if "--dry" in sys.argv:
        print(json.dumps(dry(Q.Ctx()), ensure_ascii=False, default=str))
