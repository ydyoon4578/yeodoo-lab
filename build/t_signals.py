# -*- coding: utf-8 -*-
"""build/t_signals.py — 배치 T 신호 층(B3 파생 입력 · B4 상태): 결정 월 t 의 값은 «t 에 쓸 수 있는 자료»로만 만든다.

설계 원본: tbatch_research.json final.slate 의 rule · steps · controls(저장소 밖) · data_build_plan B3 · B4.
모든 함수는 순수 함수다 — 입력(월 PeriodIndex 또는 일 DatetimeIndex)을 받아 결정 월 t 색인의 계열을 돌려준다.
가용 늦춤은 t_data.LAGS 에 선언된 것을 함수 안에서 스스로 건다(lagged). 선견 점검은 t_data.lookahead_check(절단 + 독) —
selftest 는 합성 자료로, 실자료는 build/t_cards.py --blind-smoke 안에서만(값은 버린다) 돈다.

GHM 상태(Goulding–Harvey–Mazzoleni 2023 JFE) — SLOW_t = sign(12개월 평균 초과수익) · FAST_t = sign(r_t) (≥ 0 이면 +1).
  Bull(S+,F+)=0 · Correction(S+,F−)=1 · Bear(S−,F−)=2 · Rebound(S−,F+)=3 · MED w = ½SLOW + ½FAST.
  DYN(T01-S1 · GHM 식 32~33 꼴): Bull · Bear 포지션 ±1 고정, Correction · Rebound 포지션 w_s 를 샤프 최대 1차 조건으로 —
  w_s = (A / Bm) · μ_s / m2_s, A = p_Bu·m2_Bu + p_Be·m2_Be, Bm = p_Bu·μ_Bu − p_Be·μ_Be (μ · m2 = 다음 달 초과수익의 국면별 1 · 2차
  적률 · 확장창 · 짝 (s_k, r_{k+1}) 은 k+1 ≤ t 만). a = 속도로 옮기면 Correction a = (1 − w)/2 · Rebound a = (1 + w)/2 → [0,1] 절단(우리 선택)
  = w 를 [−1, 1] 로 자르는 것과 같다. 짝 < 120 · 국면 표본 < 12 · Bm ≤ 0 이면 MED(a = ½)로 둔다(선언).
T05 PANIC(Daniel–Moskowitz) — IB_t = Π_{k=0..23}(1 + Mkt_{t−k}) < 1 · σ²_t = 일간 Mkt-RF 126거래일 분산(그달 마지막 거래일) ·
  PANIC = IB ∧ σ²_t > 확장창 중앙값(일간 σ² 값 전부 · 첫 관측 달부터 36개월 이상).
T13 CAPE 재계산 — P = Shiller 월평균 가격(늦춤 0) · CPI 1개월 · E 6개월 늦춤 · 10년 평균 실질 E → EP = 1/CAPE. CAPE 열은 안 쓴다.
  AQR 척도(Sin a Little): tilt = (clip(x_t, P5, P95) − P50)/(P95 − P5) · 분위 창 = [max(1881-01, t − 719), t](1941 뒤 60년 이동) · 최소 60개.
  tilt_M 의 12개월 시장 초과수익 = French Mkt-RF(1926-07~) · 그 앞은 Shiller (P + D/12)/P₋₁ − 1 − GS10/1200(현금 대리 · 근사 공개).
  규칙 w_VM = clip(1 + ½(tilt_V + tilt_M), 0.5, 1.5) · 단일 신호 대조 w_V = clip(1 + tilt_V, ·) · w_M = clip(1 + tilt_M, ·)(원문 50~150% 척도).
T15 SENT^PIT — 다섯 구성요소(pdnd · ripo · nipo · cefd · s)를 t−3 까지 · ripo 결측은 직전 값 · 다섯이 다 선 첫 달(1965-07)부터 확장창
  표준화 · 상관행렬 첫 주성분(최소 60개월 · ripo 적재 > 0) · HIGH ⇔ 마지막 관측의 점수 > 0.
  S 층 보고판(sent_pit_pubcal) — 같은 식을 공표 달력(3월에 전년 12월까지)으로 · 판은 마지막 개정본(실시간 판 아님).
T12 — 최초 공표 UNRATE: 결정 t 에 «obs ≤ t−1 ∧ 최초 판 날짜 ≤ t 말» 인 관측만 · 마지막 관측 m* 의 값 > m*−11..m* 평균(≥ 10개) ·
  t−1 이 아직 없으면(2025-10 미공표 · 2025-09 늦은 공표) 그때 있는 마지막 관측을 쓴다(선언). 가격: 지수_t < 10개월 평균.
T17 D13 — ΔGS10_t = GS10_{t−1} − GS10_{t−4} ≥ +0.20 → 가치 70 · ≤ −0.20 → 30 · 사이 50. 실질금리 대리 = GS10 − 12개월 CPI 상승률(둘 다 t−1).
T08-S1 — VRP_t = (VIX_t/100)²/12 − Σ_{d∈t}(ln S&P 일간)²(^GSPC · 그달 첫날은 전달 말 대비).
T02 — k_t = 0.10/σ̂_t · σ̂ = 1985-01..t 월 TSMOM 확장창 표준편차 × √12(최소 36).

🚨 이 모듈은 수익 · 신호-수익 통계를 계산하지 않는다.

  python build/t_signals.py --selftest
"""
from __future__ import annotations

import io
import math
import os
import sys

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import t_data as TD          # noqa: E402

BULL, CORR, BEAR, REB = 0, 1, 2, 3
STATE_NAMES = ("Bull", "Correction", "Bear", "Rebound")
DYN_MIN, DYN_MIN_STATE = 120, 12
PANIC_MIN_MONTHS = 36
VAR_N = 126
AQR_START, AQR_ROLL, AQR_MIN = "1881-01", 720, 60
AQR_FROM = "1927-01"                  # 척도는 이 달부터만 계산한다(카드 창 1928-01 앞 · 계산량)
SENT_COMPS = ("pdnd", "ripo", "nipo", "cefd", "s")
SENT_LAG, SENT_MIN = 3, 60
D13_THR = 0.20
TSMOM_TARGET, TSMOM_MIN = 0.10, 36
BETA_N = 60


# ══════════════════════════════════════════════════════════════════════════
#  도우미
# ══════════════════════════════════════════════════════════════════════════
def lagged(s, k):
    """관측 달 s 의 값을 결정 달 s + k 에 쓴다(가용 늦춤)."""
    out = s.copy()
    out.index = out.index + k
    return out


def contiguous(s):
    """월 계열을 빈 달 없는 색인으로(빈 달은 NaN) — 위치 기반 창이 달을 건너뛰지 않게."""
    s = s.sort_index()
    if len(s) == 0:
        return s
    return s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))


def month_last(daily):
    d = daily.dropna()
    return d.groupby(d.index.to_period("M")).last()


def months_since_first(idx, first):
    return np.array([(p - first).n for p in pd.PeriodIndex(idx)])


# ══════════════════════════════════════════════════════════════════════════
#  GHM 상태 · MED · DYN · Faber
# ══════════════════════════════════════════════════════════════════════════
def ghm(mex):
    """월 초과수익 → DataFrame(slow, fast, state, med). 12개월이 안 차면 NaN."""
    r = contiguous(pd.Series(mex, dtype=float))
    m12 = r.rolling(12).mean()
    cnt = r.rolling(12).count()
    slow = pd.Series(np.where(m12 >= 0, 1.0, -1.0), index=r.index).where(cnt == 12)
    fast = pd.Series(np.where(r >= 0, 1.0, -1.0), index=r.index).where(r.notna())
    st = pd.Series(np.nan, index=r.index)
    ok = slow.notna() & fast.notna()
    s, f = slow[ok], fast[ok]
    st[ok] = np.where((s > 0) & (f > 0), BULL, np.where((s > 0) & (f < 0), CORR, np.where((s < 0) & (f < 0), BEAR, REB)))
    return pd.DataFrame({"slow": slow, "fast": fast, "state": st, "med": 0.5 * slow + 0.5 * fast})


def dyn_weight(mex, min_n=DYN_MIN, min_state=DYN_MIN_STATE):
    """T01-S1 DYN 포지션(−1..1) — 확장창 국면별 적률(짝 (s_k, r_{k+1}) · k+1 ≤ t)로 Correction · Rebound 포지션을 정한다."""
    G = ghm(mex)
    r = contiguous(pd.Series(mex, dtype=float)).reindex(G.index)
    st = G["state"].to_numpy()
    rv = r.to_numpy()
    n = len(st)
    out = np.full(n, np.nan)
    # 짝 k: 상태 st[k] · 다음 달 수익 rv[k+1] — 결정 i 에서는 k ≤ i−1 만
    ok = np.zeros(n, bool)
    ok[:-1] = ~np.isnan(st[:-1]) & ~np.isnan(rv[1:])
    r1 = np.zeros(n)
    r1[:-1] = np.nan_to_num(rv[1:])
    cnt = np.zeros((4, n))
    s1 = np.zeros((4, n))
    s2 = np.zeros((4, n))
    for k in range(4):
        m = ok & (np.nan_to_num(st, nan=-1) == k)
        cnt[k] = np.cumsum(m)
        s1[k] = np.cumsum(np.where(m, r1, 0.0))
        s2[k] = np.cumsum(np.where(m, r1 * r1, 0.0))
    for i in range(1, n):
        if np.isnan(st[i]):
            continue
        c = cnt[:, i - 1]
        tot = c.sum()
        w = {BULL: 1.0, BEAR: -1.0, CORR: 0.0, REB: 0.0}              # MED 기본
        if tot >= min_n and (c >= min_state).all():
            p = c / tot
            mu = s1[:, i - 1] / c
            m2 = s2[:, i - 1] / c
            A = p[BULL] * m2[BULL] + p[BEAR] * m2[BEAR]
            Bm = p[BULL] * mu[BULL] - p[BEAR] * mu[BEAR]
            if Bm > 0 and m2[CORR] > 0 and m2[REB] > 0:
                cst = A / Bm
                w[CORR] = float(np.clip(cst * mu[CORR] / m2[CORR], -1.0, 1.0))
                w[REB] = float(np.clip(cst * mu[REB] / m2[REB], -1.0, 1.0))
        out[i] = w[int(st[i])]
    return pd.Series(out, index=G.index)


def dyn_positions_closed(p, mu, m2):
    """DYN 닫힌 해(selftest 가 격자 탐색으로 확인한다) — (w_C, w_R)."""
    A = p[BULL] * m2[BULL] + p[BEAR] * m2[BEAR]
    Bm = p[BULL] * mu[BULL] - p[BEAR] * mu[BEAR]
    c = A / Bm
    return c * mu[CORR] / m2[CORR], c * mu[REB] / m2[REB]


def faber(level, n=10):
    """Faber 10개월 SMA — 지수 ≥ 10개월 평균이면 +1, 아니면 −1."""
    L = contiguous(pd.Series(level, dtype=float))
    sma = L.rolling(n).mean()
    return pd.Series(np.where(L >= sma, 1.0, -1.0), index=L.index).where(sma.notna())


def level_from_returns(r):
    r = contiguous(pd.Series(r, dtype=float))
    return np.exp(np.log1p(r).cumsum())


def below_sma(level, n=10):
    """지수_t < mean(지수_{t−n+1..t}) (T12 가격 조건)."""
    L = contiguous(pd.Series(level, dtype=float))
    sma = L.rolling(n).mean()
    return pd.Series((L < sma).astype(float), index=L.index).where(sma.notna())


# ══════════════════════════════════════════════════════════════════════════
#  T05 IB · PANIC · BSC
# ══════════════════════════════════════════════════════════════════════════
def ib24(mkt_tr):
    """IB_t = Π_{k=0..23}(1 + Mkt_{t−k}) < 1 (1/0)."""
    r = contiguous(pd.Series(mkt_tr, dtype=float))
    lg = np.log1p(r).rolling(24).sum()
    return pd.Series((lg < 0).astype(float), index=r.index).where(lg.notna())


def _daily_roll_monthly(dx, fn_roll, min_months=PANIC_MIN_MONTHS):
    """일간 굴림 값 v(fn_roll) → (그달 마지막 값, 확장 중앙값(일간 값 전부 · 그달 말까지)) · 첫 관측 달부터 min_months 미만이면 NaN."""
    d = pd.Series(dx, dtype=float).dropna().sort_index()
    v = fn_roll(d)
    med = v.expanding().median()
    vm = v.groupby(v.index.to_period("M")).last()
    mm = med.groupby(med.index.to_period("M")).last()
    first = d.index[0].to_period("M")
    ok = months_since_first(vm.index, first) >= (min_months - 1)
    return vm.where(ok), mm.where(ok)


def panic(mkt_tr, mex_daily, n=VAR_N, min_months=PANIC_MIN_MONTHS):
    """PANIC_t = IB_t ∧ σ²_t > 확장 중앙값 — DataFrame(ib, var, med, panic)."""
    ib = ib24(mkt_tr)
    vm, mm = _daily_roll_monthly(mex_daily, lambda d: d.rolling(n).var(), min_months)
    df = pd.concat([ib.rename("ib"), vm.rename("var"), mm.rename("med")], axis=1)
    ok = df.notna().all(axis=1)
    df["panic"] = ((df["ib"] > 0) & (df["var"] > df["med"])).astype(float).where(ok)
    return df


def bsc_scale(mom_daily, n=VAR_N, min_months=PANIC_MIN_MONTHS):
    """Barroso–Santa-Clara — k_t = min(1, σ*/σ̂_t) · σ̂ = 일간 Mom 126일 표준편차 · σ* = σ̂ 의 확장 중앙값."""
    vm, mm = _daily_roll_monthly(mom_daily, lambda d: d.rolling(n).std(), min_months)
    k = np.minimum(1.0, mm / vm)
    return k.where(vm.notna() & mm.notna() & (vm > 0))


# ══════════════════════════════════════════════════════════════════════════
#  T03 β̂ · T02 척도
# ══════════════════════════════════════════════════════════════════════════
def beta_roll(y_ex, x_ex, n=BETA_N, lo=0.5, hi=1.0):
    """t−n+1..t 월 OLS 기울기(y 초과수익 on x 초과수익) · [lo, hi] 절단 · n 달이 다 있어야."""
    df = pd.concat([pd.Series(y_ex, dtype=float).rename("y"), pd.Series(x_ex, dtype=float).rename("x")], axis=1)
    df = df.reindex(pd.period_range(df.index.min(), df.index.max(), freq="M"))
    ok = df.notna().all(axis=1).astype(float).rolling(n).sum() == n
    b = df["y"].rolling(n).cov(df["x"]) / df["x"].rolling(n).var()
    b = b.where(ok)
    return b.clip(lo, hi) if (lo is not None or hi is not None) else b


def tsmom_scale(ts, target=TSMOM_TARGET, min_n=TSMOM_MIN):
    """k_t = 0.10 / σ̂_t · σ̂ = 확장창 월 표준편차 × √12(최소 36)."""
    s = contiguous(pd.Series(ts, dtype=float))
    sd = s.expanding(min_n).std() * math.sqrt(12)
    return (target / sd).where(sd > 0)


# ══════════════════════════════════════════════════════════════════════════
#  T13 CAPE · AQR 척도
# ══════════════════════════════════════════════════════════════════════════
def cape_ep(P, E, CPI, lag_e=6, lag_cpi=1, n=120):
    """EP_t = 10년 평균 실질 E(E ≤ t−6 · 실질화 CPI 같은 달) / 실질 P_t(P_t / CPI_{t−1})."""
    P = contiguous(pd.Series(P, dtype=float))
    E = contiguous(pd.Series(E, dtype=float))
    C = contiguous(pd.Series(CPI, dtype=float))
    rE = (E / C.reindex(E.index))
    cntE = rE.notna().astype(float).rolling(n).sum()
    avgE = rE.rolling(n).mean().where(cntE == n)
    a_t = lagged(avgE, lag_e)                                       # 결정 t 에 E ≤ t−6 의 10년 평균
    c_t = lagged(C, lag_cpi)                                        # 결정 t 에 CPI_{t−1}
    rP = P / c_t.reindex(P.index)
    ep = (a_t.reindex(P.index) / rP)
    return ep.where(ep > 0)


def aqr_tilt(x, start=AQR_START, roll=AQR_ROLL, min_n=AQR_MIN, t_from=AQR_FROM):
    """AQR 척도 — tilt_t = (clip(x_t, P5, P95) − P50)/(P95 − P5) · 창 [max(start, t − roll + 1), t] · 최소 min_n 개."""
    s = contiguous(pd.Series(x, dtype=float))
    idx = s.index
    v = s.to_numpy()
    out = np.full(len(v), np.nan)
    p0 = pd.Period(start, "M")
    tf = pd.Period(t_from, "M")
    pos0 = max(0, (p0 - idx[0]).n) if len(idx) else 0
    for i, t in enumerate(idx):
        if t < tf or np.isnan(v[i]):
            continue
        lo = max(pos0, i - roll + 1)
        w = v[lo:i + 1]
        w = w[~np.isnan(w)]
        if len(w) < min_n:
            continue
        p5, p50, p95 = np.percentile(w, [5, 50, 95])
        if p95 - p5 <= 0:
            continue
        out[i] = (min(max(v[i], p5), p95) - p50) / (p95 - p5)
    return pd.Series(out, index=idx)


def m12_excess(mex_french, P, D, GS10sh):
    """12개월 시장 초과수익 — French Mkt-RF 가 있는 달부터는 그것, 그 앞은 Shiller (P + D/12)/P₋₁ − 1 − GS10/1200(현금 대리 · 근사).
    Shiller 부분은 1926-06 까지의 달뿐이라 D(6개월 늦춤) · GS10(1개월)은 1927-01 이후 결정에서 늘 가용이다 —
    그래서 척도(aqr_tilt)는 t_from = 1927-01 부터만 계산한다(그 앞 결정의 값은 만들지 않는다)."""
    f = contiguous(pd.Series(mex_french, dtype=float))
    P = contiguous(pd.Series(P, dtype=float))
    D = contiguous(pd.Series(D, dtype=float))
    g = contiguous(pd.Series(GS10sh, dtype=float))
    f0 = f.dropna().index.min() if f.notna().any() else None
    sh = (P + D.reindex(P.index) / 12.0) / P.shift(1) - 1.0 - g.reindex(P.index) / 1200.0
    if f0 is not None:
        sh = sh[sh.index < f0]
        r = pd.concat([sh, f.loc[f.index >= f0]]).sort_index()
    else:
        r = sh
    r = contiguous(r[~r.index.duplicated(keep="last")])
    m12 = np.exp(np.log1p(r).rolling(12).sum()) - 1.0
    cnt = r.notna().astype(float).rolling(12).sum()
    return m12.where(cnt == 12)


def t13_weights(ep, m12, **kw):
    """T13 — w_VM = clip(1 + ½(tilt_V + tilt_M), 0.5, 1.5) · 단일 신호 대조 w_V = clip(1 + tilt_V, 0.5, 1.5) · w_M = clip(1 + tilt_M, 0.5, 1.5).
    대조는 원문(AQR «Sin a Little»)의 단일 신호 전략과 같은 척도(50~150%)다 — VM 은 두 단일 신호 포지션의 평균
    (절단이 걸리지 않으면 w_VM − 1 = ½((w_V − 1) + (w_M − 1))). 그래서 G4 «VM X > 모멘텀만 X» 는
    «가치 타이밍 X > 모멘텀 타이밍 X» 와 같다(원문 표 5 의 비교). 반 척도(1 + ½tilt)로 두면 그 조건이 «반 척도 가치 X > 0» 으로
    무너진다(적대 검토 2026-09-26 — 등록 전 수정 · §8)."""
    tv, tm = aqr_tilt(ep, **kw), aqr_tilt(m12, **kw)
    df = pd.concat([tv.rename("tilt_V"), tm.rename("tilt_M")], axis=1)
    df["w_VM"] = (1 + 0.5 * (df["tilt_V"] + df["tilt_M"])).clip(0.5, 1.5)
    df["w_V"] = (1 + df["tilt_V"]).clip(0.5, 1.5)
    df["w_M"] = (1 + df["tilt_M"]).clip(0.5, 1.5)
    return df


# ══════════════════════════════════════════════════════════════════════════
#  T17 D13 · 실질금리 대리 · DFII10
# ══════════════════════════════════════════════════════════════════════════
VALUE_TILT, NEUTRAL, GROWTH_TILT = 2, 1, 0
D13_W = {VALUE_TILT: 0.7, NEUTRAL: 0.5, GROWTH_TILT: 0.3}      # 가치 다리 비중


def _regime(d, thr=D13_THR):
    return pd.Series(np.where(d >= thr, VALUE_TILT, np.where(d <= -thr, GROWTH_TILT, NEUTRAL)), index=d.index).where(d.notna())


def d13_regime(gs10, thr=D13_THR, lag=1):
    """ΔGS10_t = GS10_{t−1} − GS10_{t−4} → 국면(2 가치 · 1 중립 · 0 성장)."""
    g = lagged(contiguous(pd.Series(gs10, dtype=float)), lag)
    d = g - lagged(g, 3).reindex(g.index)
    return pd.DataFrame({"d": d, "regime": _regime(d, thr)})


def rr_proxy_regime(gs10, cpi, thr=D13_THR, lag=1):
    """실질금리 대리 RR = GS10 − 100·(CPI/CPI₋₁₂ − 1) · 결정 t 에 RR_{t−1} − RR_{t−4}."""
    g = contiguous(pd.Series(gs10, dtype=float))
    c = contiguous(pd.Series(cpi, dtype=float))
    infl = 100.0 * (c / lagged(c, 12).reindex(c.index) - 1.0)
    rr = (g - infl.reindex(g.index))
    rr_t = lagged(rr, lag)
    d = rr_t - lagged(rr_t, 3).reindex(rr_t.index)
    return pd.DataFrame({"d": d, "regime": _regime(d, thr)})


def dfii10_regime(dfii_daily, thr=D13_THR):
    """D13 원판(S 층) — DFII10 월말 값의 3개월 변화(늦춤 0)."""
    m = month_last(pd.Series(dfii_daily, dtype=float))
    m = contiguous(m)
    d = m - lagged(m, 3).reindex(m.index)
    return pd.DataFrame({"d": d, "regime": _regime(d, thr)})


# ══════════════════════════════════════════════════════════════════════════
#  T12 최초 공표 UNRATE 추세
# ══════════════════════════════════════════════════════════════════════════
def unrate_up(ur_first, n=12, min_obs=10):
    """결정 t — 가용(obs ≤ t−1 ∧ first_vintage ≤ t 말) 관측의 마지막 m* 값 > m*−n+1..m* 평균(≥ min_obs 개) → 1/0.
    DataFrame(up, m_star, lag) — lag = t − m*(보통 1)."""
    df = ur_first.copy()
    df = df[df["value"].notna()].sort_index()
    if len(df) == 0:
        return pd.DataFrame(columns=["up", "m_star", "lag"])
    fv = pd.to_datetime(df["first_vintage"]).to_numpy()
    obs = df.index
    val = df["value"].to_numpy(float)
    cal = pd.period_range(obs.min() + 1, obs.max() + 2, freq="M")
    up, ms, lg = np.full(len(cal), np.nan), [None] * len(cal), np.full(len(cal), np.nan)
    ends = np.array([t.end_time.to_datetime64() for t in cal])
    for j, t in enumerate(cal):
        m = (obs <= t - 1) & (fv <= ends[j])
        if not m.any():
            continue
        io_ = np.flatnonzero(m)
        k = io_[-1]
        mstar = obs[k]
        win = io_[(obs[io_] >= mstar - (n - 1)) & (obs[io_] <= mstar)]
        if len(win) < min_obs:
            continue
        up[j] = float(val[k] > val[win].mean())
        ms[j] = str(mstar)
        lg[j] = (t - mstar).n
    return pd.DataFrame({"up": up, "m_star": ms, "lag": lg}, index=cal)


# ══════════════════════════════════════════════════════════════════════════
#  T08-S1 VRP
# ══════════════════════════════════════════════════════════════════════════
def realized_var_month(px_daily):
    """Σ_{d∈t} (ln P_d/P_{d−1})² — 그달 첫날은 전달 마지막 종가 대비."""
    p = pd.Series(px_daily, dtype=float).dropna().sort_index()
    lr = np.log(p / p.shift(1)).dropna()
    rv = (lr * lr).groupby(lr.index.to_period("M")).sum()
    first = p.index[0].to_period("M")
    return rv[rv.index > first]                                       # 첫 달은 전달 말이 없어 불완전 — 뺀다


def sp_state_ret(spx_daily, D, tr_daily, lag_d=6):
    """T08 상태 입력 — ^SP500TR 이 전월 말 값을 갖는 첫 달부터는 TR 월말 비, 그 앞은 (SPX_t + D_{t−6}/12)/SPX_{t−1} − 1.
    t_data.sp500_tr_splice 와 같은 이음이되 Shiller D 에 선언 늦춤(6개월)을 건다(상태는 t 에 쓸 수 있는 자료로만)."""
    spx = contiguous(month_last(pd.Series(spx_daily, dtype=float)))
    trs = pd.Series(tr_daily, dtype=float).dropna()
    Dl = lagged(contiguous(pd.Series(D, dtype=float)), lag_d).reindex(spx.index)
    pre = (spx + Dl / 12.0) / spx.shift(1) - 1.0
    if len(trs):
        tr = contiguous(month_last(trs))
        first_full = tr.index.min() + 1
        pre = pre[pre.index < first_full]
        post = (tr / tr.shift(1) - 1.0)
        post = post[post.index >= first_full]
        out = pd.concat([pre.dropna(), post.dropna()]).sort_index()
    else:
        out = pre.dropna()
    return out[~out.index.duplicated(keep="last")]


def vrp(vix_close_daily, px_daily):
    v = month_last(pd.Series(vix_close_daily, dtype=float))
    rv = realized_var_month(px_daily)
    out = (v / 100.0) ** 2 / 12.0 - rv.reindex(v.index)
    return out.dropna()


# ══════════════════════════════════════════════════════════════════════════
#  T15 SENT^PIT
# ══════════════════════════════════════════════════════════════════════════
def _pc1_score(Z):
    C = np.corrcoef(Z, rowvar=False)
    w, V = np.linalg.eigh(C)
    v = V[:, int(np.argmax(w))]
    return v


def pubcal_horizon(t):
    """Wurgler 파일의 공표 달력(보고용) — 해마다 3월에 전년 12월까지 붙는다(README «UPDATED: March»).
    결정 t(월말)에 쓸 수 있는 마지막 관측 = t 가 3~12월이면 (t 의 해 − 1)-12 · 1~2월이면 (t 의 해 − 2)-12. 늘 t − 3 이상 늦다."""
    t = pd.Period(t, "M")
    return pd.Period("%04d-12" % (t.year - (1 if t.month >= 3 else 2)), "M")


def sent_pit(wurg, comps=SENT_COMPS, lag=SENT_LAG, min_n=SENT_MIN, horizon=None, extend=0):
    """결정 t — 구성요소 t−lag 까지 · ripo 결측 앞값 · 다섯이 선 첫 달부터 확장창 표준화 · 첫 주성분(ripo 적재 > 0) 점수.
    horizon(t) 를 주면 t−lag 대신 그 달까지(공표 달력 보고판 — pubcal_horizon) · extend = 마지막 관측 뒤로 더 둘 결정 달 수.
    DataFrame(score, high, n_obs, obs)."""
    X = wurg[list(comps)].copy().sort_index()
    X = X.reindex(pd.period_range(X.index.min(), X.index.max(), freq="M"))
    X["ripo"] = X["ripo"].ffill()
    full = X.notna().all(axis=1)
    if not full.any():
        return pd.DataFrame(columns=["score", "high", "n_obs", "obs"])
    start = X.index[np.flatnonzero(full.to_numpy())[0]]
    Xs = X.loc[X.index >= start]
    A = Xs.to_numpy(float)
    ok_rows = ~np.isnan(A).any(axis=1)
    cal = pd.period_range(start + lag, Xs.index.max() + lag + extend, freq="M")
    rip = list(comps).index("ripo")
    sc, nn, ob = np.full(len(cal), np.nan), np.zeros(len(cal), int), [None] * len(cal)
    last = Xs.index.max()
    for j, t in enumerate(cal):
        h = t - lag if horizon is None else min(horizon(t), t - lag)
        h = min(h, last)
        k = (h - start).n
        if k < 0:
            continue
        rows = np.flatnonzero(ok_rows[:k + 1])
        if len(rows) < min_n or not ok_rows[k]:
            continue
        D = A[rows]
        mu, sd = D.mean(0), D.std(0, ddof=1)
        if (sd <= 0).any():
            continue
        Z = (D - mu) / sd
        v = _pc1_score(Z)
        if v[rip] < 0:
            v = -v
        sc[j] = float(((A[k] - mu) / sd) @ v)
        nn[j] = len(rows)
        ob[j] = str(h)
    df = pd.DataFrame({"score": sc, "n_obs": nn, "obs": ob}, index=cal)
    df["high"] = (df["score"] > 0).astype(float).where(df["score"].notna())
    return df


def sent_pit_pubcal(wurg):
    """T15 S 층 보고판 — 같은 SENT^PIT 식을 Wurgler 공표 달력(3월에 전년 12월까지)으로. 판은 여전히 마지막 개정본이다(PIT 아님).
    결정은 마지막 관측 뒤 14개월까지 둔다(다음 3월 공표 전까지 그 판을 쓴다)."""
    return sent_pit(wurg, horizon=pubcal_horizon, extend=14)


def annual_hold(sig):
    """BW 원형 연 1회판 — 결정 t 의 값 = t 이전(포함) 마지막 12월 결정의 값(1~12월 보유에 전년 말 값)."""
    s = contiguous(pd.Series(sig, dtype=float))
    dec = s.where(np.array([p.month == 12 for p in s.index]))
    return dec.ffill()


def sent_orth_high(wurg, lag=SENT_LAG):
    """SENT_ORTH 판(대조 · 파일 값 · 비 PIT) — 결정 t 에 SENT_ORTH_{t−3} > 0."""
    s = contiguous(pd.Series(wurg["SENT_ORTH"], dtype=float))
    v = lagged(s, lag)
    return (v > 0).astype(float).where(v.notna())


# ══════════════════════════════════════════════════════════════════════════
#  선견 점검 명단 — (이름, 함수, 입력 {인자: 가용 이름}) · 실자료 점검은 t_cards 연기 시험이 쓴다
# ══════════════════════════════════════════════════════════════════════════
def checks_catalog():
    """이 모듈 신호 전부의 선견 점검 틀 — 입력 이름은 t_data.LAGS 에 선언된 것."""
    return [
        ("ghm", lambda mex: ghm(mex)[["slow", "fast", "state"]], {"mex": "french:ff3_m"}),
        ("dyn", lambda mex: dyn_weight(mex), {"mex": "french:ff3_m"}),
        ("faber", lambda mkt: faber(level_from_returns(mkt)), {"mkt": "french:ff3_m"}),
        ("below_sma", lambda mkt: below_sma(level_from_returns(mkt)), {"mkt": "french:ff3_m"}),
        ("panic", lambda mkt, day: panic(mkt, day)[["ib", "panic"]], {"mkt": "french:ff3_m", "day": "french:ff3_d"}),
        ("bsc", lambda mom: bsc_scale(mom), {"mom": "french:mom_d"}),
        ("beta60", lambda y, x: beta_roll(y, x), {"y": "french:beta", "x": "french:ff3_m"}),
        ("tsmom_k", lambda ts: tsmom_scale(ts), {"ts": "aqr:TSMOM"}),
        ("cape_ep", lambda P, E, CPI: cape_ep(P, E, CPI), {"P": "shiller:P", "E": "shiller:E", "CPI": "shiller:CPI"}),
        ("t13_w", lambda P, E, CPI, D, G, mex: t13_weights(cape_ep(P, E, CPI), m12_excess(mex, P, D, G))[["w_VM", "w_V", "w_M"]],
         {"P": "shiller:P", "E": "shiller:E", "CPI": "shiller:CPI", "D": "shiller:D", "G": "shiller:GS10_shiller", "mex": "french:ff3_m"}),
        ("d13", lambda g: d13_regime(g)["regime"], {"g": "fred:GS10"}),
        ("rr_proxy", lambda g, c: rr_proxy_regime(g, c)["regime"], {"g": "fred:GS10", "c": "fred:CPIAUCSL"}),
        ("dfii10", lambda d: dfii10_regime(d)["regime"], {"d": "fred:DFII10"}),
        ("unrate_up", lambda u: unrate_up(u)["up"], {"u": "alfred:UNRATE"}),
        ("vrp", lambda v, p: vrp(v, p), {"v": "cboe:VIX", "p": "yf:^GSPC"}),
        ("sp_state", lambda spx, D, tr: sp_state_ret(spx, D, tr), {"spx": "cboe:SPX", "D": "shiller:D", "tr": "yf:^SP500TR"}),
        ("sent_pit", lambda w: sent_pit(w)[["score", "high"]], {"w": "wurgler"}),
        ("sent_annual", lambda w: annual_hold(sent_pit(w)["high"]), {"w": "wurgler"}),
        ("sent_orth", lambda w: sent_orth_high(w), {"w": "wurgler"}),
        ("sent_pubcal", lambda w: sent_pit_pubcal(w)[["score", "high"]], {"w": "wurgler"}),
    ]


# ══════════════════════════════════════════════════════════════════════════
#  합성 자료 시험
# ══════════════════════════════════════════════════════════════════════════
def _fake_monthly(start, end, mu=0.006, sd=0.045, seed=1):
    idx = pd.period_range(start, end, freq="M")
    return pd.Series(np.random.default_rng(seed).normal(mu, sd, len(idx)), index=idx)


def _st_ghm():
    r = pd.Series([0.01] * 11 + [-0.02, 0.03, -0.20, 0.05], index=pd.period_range("2000-01", periods=15, freq="M"))
    G = ghm(r)
    assert G["slow"].iloc[:11].isna().all() and G["slow"].iloc[11] == 1.0 and G["fast"].iloc[11] == -1.0
    assert G["state"].iloc[11] == CORR and G["state"].iloc[12] == BULL and G["med"].iloc[11] == 0.0
    assert G["state"].iloc[13] == BEAR and G["state"].iloc[14] == REB        # 12개월 평균 < 0 인 뒤
    assert ghm(pd.Series([0.0] * 12, index=pd.period_range("2000-01", periods=12, freq="M")))["state"].iloc[-1] == BULL
    return "GHM SLOW/FAST(≥ 0 → +1) · 네 국면 · MED"


def _st_dyn():
    rng = np.random.default_rng(0)
    p = np.array([0.5, 0.15, 0.2, 0.15])
    mu = np.array([0.010, 0.004, -0.006, 0.003])
    m2 = np.array([0.0020, 0.0030, 0.0050, 0.0040])
    wc, wr = dyn_positions_closed(p, mu, m2)
    best, arg = -9, None                                             # 격자로 샤프 최대 확인(분산 = 2차 − 평균²)
    for a in np.linspace(-1.5, 1.5, 301):
        for b in np.linspace(-1.5, 1.5, 301):
            w = np.array([1.0, a, -1.0, b])
            M = (p * w * mu).sum()
            Q = (p * w * w * m2).sum()
            sr = M / math.sqrt(Q - M * M)
            if sr > best:
                best, arg = sr, (a, b)
    assert abs(arg[0] - wc) < 0.011 and abs(arg[1] - wr) < 0.011, (arg, wc, wr)
    r = _fake_monthly("1926-07", "1960-12", seed=4)
    d = dyn_weight(r)
    G = ghm(r)
    first = d.first_valid_index()
    assert first is not None and (d.dropna().abs() <= 1.0).all()
    bb = G["state"].reindex(d.index)
    assert (d[bb == BULL].dropna() == 1.0).all() and (d[bb == BEAR].dropna() == -1.0).all()
    early = d.index[:11 + DYN_MIN]                                  # 짝 k ≥ 11 · 결정 i 에서 짝 수 = i − 11
    med_early = G["med"].reindex(early)
    assert np.allclose(d.reindex(early).dropna(), med_early.reindex(d.reindex(early).dropna().index))
    return "DYN 닫힌 해 = 샤프 최대(격자) · Bull/Bear ±1 · 짝 < 120 이면 MED · |w| ≤ 1"


def _st_panic():
    rng = np.random.default_rng(2)
    days = pd.bdate_range("1926-07-01", "1935-12-31")
    dx = pd.Series(rng.normal(0.0003, 0.01, len(days)) * np.where(np.arange(len(days)) > 1500, 2.5, 1.0), index=days)
    mkt = dx.groupby(dx.index.to_period("M")).apply(lambda z: float(np.prod(1 + z) - 1))
    mkt.iloc[30:60] = -0.05
    P = panic(mkt, dx)
    assert P["panic"].first_valid_index() == pd.Period("1929-06", "M")
    ib = ib24(mkt)
    t = pd.Period("1931-06", "M")
    assert ib[t] == float(np.prod(1 + mkt.loc[t - 23:t]) < 1)
    k = bsc_scale(dx)
    assert (k.dropna() <= 1.0).all() and (k.dropna() > 0).all()
    return "IB24 곱 < 1 · 126일 분산 · 확장 중앙값(첫 달부터 36개월 → 1929-06) · BSC 척도 ≤ 1"


def _st_cape():
    idx = pd.period_range("1871-01", "1940-12", freq="M")
    n = len(idx)
    P = pd.Series(np.linspace(10, 30, n), index=idx)
    E = pd.Series(np.linspace(1, 2, n), index=idx)
    C = pd.Series(np.linspace(10, 20, n), index=idx)
    ep = cape_ep(P, E, C)
    t = pd.Period("1900-06", "M")
    rE = (E / C).loc[t - 6 - 119:t - 6].mean()
    want = rE / (P[t] / C[t - 1])
    assert abs(ep[t] - want) < 1e-12 and ep.first_valid_index() == pd.Period("1871-01", "M") + 119 + 6
    x = pd.Series(np.arange(n, dtype=float), index=idx)
    tl = aqr_tilt(x, t_from="1900-01")
    i = idx.get_loc(pd.Period("1900-01", "M"))
    w = x.to_numpy()[max((pd.Period("1881-01", "M") - idx[0]).n, i - 719):i + 1]
    p5, p50, p95 = np.percentile(w, [5, 50, 95])
    assert abs(tl.iloc[i] - (min(max(x.iloc[i], p5), p95) - p50) / (p95 - p5)) < 1e-12 and abs(tl.iloc[i] - 0.5) < 1e-9
    assert tl.loc[:"1899-12"].isna().all()
    # T13 척도 — 단일 신호 대조 = 1 + tilt(50~150%) · VM = 두 포지션의 평균(절단이 안 걸리면 정확히)
    r = np.random.default_rng(4)
    ix = pd.period_range("1871-01", "1960-12", freq="M")
    Wt = t13_weights(pd.Series(r.normal(0.05, 0.01, len(ix)), index=ix), pd.Series(r.normal(0.05, 0.15, len(ix)), index=ix),
                     t_from="1890-01").dropna()
    assert len(Wt) > 500
    assert np.allclose(Wt["w_V"], (1 + Wt["tilt_V"]).clip(0.5, 1.5)) and np.allclose(Wt["w_M"], (1 + Wt["tilt_M"]).clip(0.5, 1.5))
    free = (Wt["w_V"] > 0.5) & (Wt["w_V"] < 1.5) & (Wt["w_M"] > 0.5) & (Wt["w_M"] < 1.5)
    assert free.sum() > 100 and np.allclose((Wt["w_VM"] - 1)[free], 0.5 * ((Wt["w_V"] - 1) + (Wt["w_M"] - 1))[free])
    assert Wt["w_M"].max() - Wt["w_M"].min() > 0.75                     # 50~150% 척도(반 척도면 폭 ≤ 0.5)
    return "CAPE 재계산(E 6 · CPI 1 늦춤 · 10년 실질 평균) · AQR 척도(1881 확장 · 60년 이동 · 윈저 P5/P95) · T13 대조 척도 1 + tilt(VM = 평균)"


def _st_regimes():
    idx = pd.period_range("1953-04", "1954-12", freq="M")
    g = pd.Series([2.0, 2.1, 2.3, 2.5, 2.6, 2.4, 2.2, 2.0, 2.0, 2.0] + [2.0] * 11, index=idx)
    d = d13_regime(g)
    t = pd.Period("1953-08", "M")
    assert abs(d["d"][t] - (g[t - 1] - g[t - 4])) < 1e-12 and d["regime"][t] == VALUE_TILT
    t2 = pd.Period("1954-01", "M")
    assert abs(d["d"][t2] - (g[t2 - 1] - g[t2 - 4])) < 1e-12 and d["regime"][t2] == GROWTH_TILT
    assert d["regime"].first_valid_index() == pd.Period("1953-08", "M")
    return "D13 ΔGS10 = GS10_{t−1} − GS10_{t−4} · ±0.20 국면 · 첫 결정 1953-08"


def _st_unrate():
    obs = pd.period_range("2024-01", "2025-09", freq="M")
    val = [4.0 + 0.1 * k for k in range(len(obs))]
    fv = [(p + 1).start_time.strftime("%Y-%m-%d") for p in obs]
    fv[-1] = "2025-11-30"                                           # 2025-09 늦은 공표
    df = pd.DataFrame({"value": val, "first_vintage": fv, "first_release": True}, index=obs)
    u = unrate_up(df)
    assert u.loc[pd.Period("2025-09", "M"), "m_star"] == "2025-08" and u.loc[pd.Period("2025-10", "M"), "m_star"] == "2025-08"
    assert u.loc[pd.Period("2025-11", "M"), "m_star"] == "2025-09" and u.loc[pd.Period("2025-11", "M"), "lag"] == 2
    assert u["up"].dropna().eq(1.0).all()
    return "최초 공표 UNRATE — 판 날짜 가용 · 늦은 공표는 그때 있던 마지막 관측 · ≥ 10개 평균"


def _st_sent():
    rng = np.random.default_rng(9)
    idx = pd.period_range("1958-01", "1990-12", freq="M")
    f = np.cumsum(rng.normal(0, 0.2, len(idx)))
    W = pd.DataFrame({c: f * s + rng.normal(0, 0.5, len(idx)) for c, s in zip(SENT_COMPS, (-1, 1, 1, -1, 0.5))}, index=idx)
    W.loc[W.index < pd.Period("1965-07", "M"), "cefd"] = np.nan
    W.iloc[200:203, 1] = np.nan
    W["SENT_ORTH"] = f
    s = sent_pit(W)
    assert s["score"].first_valid_index() == pd.Period("1965-07", "M") + (SENT_MIN - 1) + SENT_LAG
    assert s["obs"].dropna().iloc[0] == str(pd.Period("1965-07", "M") + SENT_MIN - 1)
    c = np.corrcoef(s["score"].dropna(), pd.Series(f, index=idx).reindex(s["score"].dropna().index - SENT_LAG))[0, 1]
    assert c > 0.8, c                                              # ripo 적재 > 0 → 요인과 같은 쪽
    a = annual_hold(s["high"])
    t = pd.Period("1980-05", "M")
    assert a[t] == s["high"][pd.Period("1979-12", "M")]
    # 공표 달력 보고판 — 3~12월 결정은 전년 12월까지 · 1~2월은 전전년 12월까지 · 같은 관측이면 같은 점수
    assert pubcal_horizon("1980-03") == pd.Period("1979-12", "M") and pubcal_horizon("1980-02") == pd.Period("1978-12", "M")
    pc = sent_pit_pubcal(W)
    for t in ("1980-03", "1980-11", "1981-02"):
        t = pd.Period(t, "M")
        h = pubcal_horizon(t)
        assert pc.loc[t, "obs"] == str(h) and abs(pc.loc[t, "score"] - s.loc[h + SENT_LAG, "score"]) < 1e-12
    assert pc.index.max() == W.index.max() + SENT_LAG + 14 and s.index.max() == W.index.max() + SENT_LAG
    return "SENT^PIT(1965-07 + 60개월 + 3개월 늦춤 · ripo 앞값 · 부호 고정) · 연 1회판 · 공표 달력 보고판(3월 · 전년 12월)"


def _st_lookahead():
    """선견 틀(t_data.lookahead_check · 절단 + 독)을 이 모듈 신호 전부에 합성 자료로 건다."""
    rng = np.random.default_rng(12)
    m = pd.period_range("1871-01", "2005-12", freq="M")
    fm = pd.period_range("1926-07", "2005-12", freq="M")
    days = pd.bdate_range("1926-07-01", "1940-12-31")
    mex = pd.Series(rng.normal(0.005, 0.045, len(fm)), index=fm)
    ff3 = pd.DataFrame({"Mkt-RF": mex, "RF": 0.003}, index=fm)
    ff3["Mkt"] = ff3["Mkt-RF"] + ff3["RF"]
    day = pd.Series(rng.normal(0.0003, 0.01, len(days)), index=days)
    shil = pd.DataFrame({"P": np.exp(np.cumsum(rng.normal(0.003, 0.03, len(m)))) * 5, "D": np.linspace(0.2, 1.0, len(m)),
                         "E": np.linspace(0.4, 2.0, len(m)) * np.exp(rng.normal(0, 0.05, len(m))), "CPI": np.linspace(10, 100, len(m)),
                         "G": 4 + rng.normal(0, 0.2, len(m))}, index=m)
    gm = pd.period_range("1953-04", "2005-12", freq="M")
    gs = pd.Series(4 + np.cumsum(rng.normal(0, 0.1, len(gm))), index=gm)
    cpi = pd.Series(np.linspace(30, 200, len(gm)), index=gm)
    dd = pd.bdate_range("2003-01-02", "2012-12-31")
    dfii = pd.Series(1 + np.cumsum(rng.normal(0, 0.03, len(dd))), index=dd)
    uo = pd.period_range("1960-01", "2005-12", freq="M")
    ur = pd.DataFrame({"value": 5 + np.cumsum(rng.normal(0, 0.1, len(uo))),
                       "first_vintage": [(p + 1).start_time.strftime("%Y-%m-%d") for p in uo], "first_release": True}, index=uo)
    sd = pd.bdate_range("1975-01-02", "1995-12-29")
    spx = pd.Series(70 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(sd)))), index=sd)
    trd = sd[sd >= "1988-01-04"]
    trs = pd.Series(250 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, len(trd)))), index=trd)
    vd = pd.bdate_range("1990-01-02", "1999-12-31")
    vix = pd.Series(15 + np.abs(rng.normal(0, 5, len(vd))), index=vd)
    gspc = pd.Series(300 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(vd)))), index=vd)
    wm = pd.period_range("1958-01", "1990-12", freq="M")
    f = np.cumsum(rng.normal(0, 0.2, len(wm)))
    W = pd.DataFrame({c: f * s + rng.normal(0, 0.5, len(wm)) for c, s in zip(SENT_COMPS, (-1, 1, 1, -1, 0.5))}, index=wm)
    W.loc[W.index < pd.Period("1965-07", "M"), "cefd"] = np.nan
    W["SENT_ORTH"] = f
    ts = pd.Series(rng.normal(0.005, 0.03, 200), index=pd.period_range("1985-01", periods=200, freq="M"))
    beta_y = mex.loc["1963-07":] * 0.8 + rng.normal(0, 0.01, len(mex.loc["1963-07":]))
    feed = {"mex": (mex, "french:ff3_m"), "mkt": (ff3["Mkt"], "french:ff3_m"), "day": (day, "french:ff3_d"),
            "mom": (day, "french:mom_d"), "y": (beta_y, "french:beta"), "x": (mex, "french:ff3_m"), "ts": (ts, "aqr:TSMOM"),
            "P": (shil["P"], "shiller:P"), "E": (shil["E"], "shiller:E"), "CPI": (shil["CPI"], "shiller:CPI"),
            "D": (shil["D"], "shiller:D"), "G": (shil["G"], "shiller:GS10_shiller"), "g": (gs, "fred:GS10"), "c": (cpi, "fred:CPIAUCSL"),
            "d": (dfii, "fred:DFII10"), "u": (ur, "alfred:UNRATE"), "v": (vix, "cboe:VIX"), "p": (gspc, "yf:^GSPC"), "w": (W, "wurgler"),
            "spx": (spx, "cboe:SPX"), "tr": (trs, "yf:^SP500TR")}
    done = []
    for nm, fn, spec in checks_catalog():
        inp = {}
        for arg, lagname in spec.items():
            inp[arg] = (feed[arg][0], lagname)
        kw = {}
        if nm in ("t13_w",):
            kw = {"t_min": "1928-01"}
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):   # 독 시험의 난수(< −1)가 log1p 에서 NaN — 지평 뒤 값이라 무관
            res = TD.lookahead_check(fn, inp, n=25, **kw)
        assert res["ok"], (nm, res)
        done.append(nm)
    # 심은 누수는 잡힌다 — UNRATE 를 t 달 값으로 쓰면(가용 t−1 위반)
    leak = lambda u: (u["value"] > u["value"].rolling(12).mean()).astype(float)
    assert not TD.lookahead_check(leak, {"u": (ur, "alfred:UNRATE")}, n=25)["ok"]
    return "선견 틀 통과 %d 신호(%s) · 심은 누수는 잡힘" % (len(done), " · ".join(done))


def _st_static():
    import ast
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    bad = []
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id == "open":
            if not any(kw.arg == "encoding" for kw in nd.keywords):
                bad.append(nd.lineno)
    assert not bad, bad
    return "open() encoding 정적 점검"


def selftest():
    res, ok = [], True
    for fn in (_st_ghm, _st_dyn, _st_panic, _st_cape, _st_regimes, _st_unrate, _st_sent, _st_lookahead, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            import traceback
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("t_signals selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
