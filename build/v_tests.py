# -*- coding: utf-8 -*-
"""build/v_tests.py — 배치 V 검정: 펀드 틀 · DM 식 (3) 베타 조정 α(주 통계) · Holm 한쪽 α 0.05(m 6) · 공동 조건(L-C · 위약 순위 · 반등 놓침) ·
사용자 관문(G2 · G3 · G5 · G6a — V 명세로 매개변수화) · S 층 구현성(G5e · T+1 · 10/20bp · FID) · 채택 표시 · BY · Stouffer · DSR(보고).

설계 원본(구속): vbatch_research.json final.tests(fund_frame · primary_statistic · S_layer · L_layer · joint_conditions · user_gates_on_W_cards ·
  adoption_marking · situations_report) · final.multiplicity(H_V · secondary · stouffer · cumulative_N · discipline) · D06 · D19 · D20 · D23.
  명세 build_plan 은 이 모듈을 «v_eval.py» 로 불렀다 — 과제 지시(엔진 단계)에 따라 build/v_tests.py 로 짓는다(내용은 명세 v_eval 그대로).

복사(가져오지 않는다 — D22): eg30plus.nw_t · t_core 의 norm_sf · h1 · by_info · stouffer 틀 · events_L · events_S · zigzag_legs · year_table · blocks4 · seg_sum ·
  bundle · sync_mask · _b · _pos · _same_sign · qbatch_run.dsr. t_core gates 의 T 카드 ID 고정(DEFENSIVE · SWITCHING · SYNC_EXCL_EXTRA)은 V 명세로 매개변수화해
  새로 쓴다(비평 2 A2): G3 = 하락월 X ≥ 0(모든 전략 같다 · «방어 카드» 엄격 표시 폐지) · 반등 놓침은 모든 W 카드에 켠다. 원본 짝맞춤은 v_audit(허용 목록 별도 프로세스).
  mech_episodes 는 허용 목록(may_import)이라 함수 안에서 부른다.

주 통계(D06 · 비평 1 H2): Δ_t = a + b0·MKT_t + bB·I_B,t−1·MKT_t + bBU·I_B,t−1·I_U,t·MKT_t + e 의 a 의 NW(6) t(한쪽 p = 1 − Φ(t)) ·
  MKT = Mkt − RF · I_B,t−1 = 1[지난 24개월 누적 시장 < 0] · I_U,t = 1[MKT_t > 0](DM 식 3 의 베타 항) · αB·I_B 더미는 넣지 않는다 · 원 Δ 의 NW t 는 보고만.
H_V(확정 · L 층 내부 D1 증거): Δ_f 다섯(MOM · LBS · LIQ · VAL · QLT · W − S0) + 배분기 Δ_A(C-A − C0) = m 6 · Holm 한쪽 가족 α 0.05 ·
  문턱 z = 2.394 · 2.326 · 2.241 · 2.128 · 1.960 · 1.645. H_V 통과 = Holm 기각 ∧ (a) L-C 베타 조정 α > 0 ∧ (b) 위약 순위 ≥ 0.90 ∧ (c) 반등 놓침 ok.

명세가 정하지 않은 산수(최소 선택 · 선언)
  T1 창: L-R = 첫 활성 결정 + 1 ~ 2026-07 보유월(명세 effective_L_window 의 끝 · French CRSP 202608 판의 마지막 달은 쓰지 않는다) · L-C = 2020-02 ~ 2026-07 보유월 ·
      S = 2016-09 ~ 2026-08 보유월(120).
  T2 위약: 그 전략의 가닥 z 열을 함께 «달 블록째 섞기»(12달 토막 차례 섞기 · v_alloc.block_shuffle_rows) → 기울기 · v · θ · W 팔 · Δ · α̂ 다시(L-R 창) ·
      순위 = #{α̂_perm < α̂_obs}/nperm · 배분기는 상대 점수 행렬을 같은 방식으로 섞고 FM · 목표 · 경로 다시(섞는 구간 = 선 열 ≥ 3 인 행 — FM 이 K_s ≥ 3 달부터).
  T3 반등 놓침(V): θ_t < θ0 인 결정 달 t 뒤 보유월 t+1..t+3(≈ 63거래일)이 SURGE-M 이면 그 달을 모은다 · ≥ 3 이면 그 달들의 평균 Δ ≥ 0(t_core reb_miss 의 V 판).
  T4 FID(S 층 대리 일치) = corr(S θ = 1 능동수익, L 대리 y) · 겹친 보유월(2016-09 ~ 2026-07 · ≥ 36) ≥ 0.60 — 못 미치면 «S 대리 불일치» → 채택 차단.
  T5 H 기준(G3 보고) = X − 0.1·(β̂_책 − 1)·(SPY TR − rf)(S 층 · β̂ = 체결 책 FP β̂).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산해서 찍지 않는다. --selftest 는 합성 자료만 ·
   --blind-smoke 는 실자료로 끝까지 돌리되 산출을 저장소 밖 임시 폴더에 쓰고 열지 않고 지운다(참/거짓 · 모양만 찍는다) · NPERM 을 줄인 연기는 굽기로 새지 않는다(NPERM_MIN).

  python build/v_tests.py --selftest
  python build/v_tests.py --blind-smoke [--nperm 3]
"""
from __future__ import annotations

import io
import json
import math
import os
import shutil
import sys
import time
import traceback

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import v_core as C          # noqa: E402
import v_data as VD         # noqa: E402
import v_cond as VC         # noqa: E402

# ══════════════════════════════════════════════════════════════════════════
#  상수(final.tests · multiplicity) — 여기서만 바꾼다
# ══════════════════════════════════════════════════════════════════════════
SEED = C.SEED
NPERM, NPERM_MIN = C.NPERM, 1000
NW_LAG, NW_LAG_REPORT = 6, 12
HOLM_ALPHA = 0.05
H_V = ("V01", "V02", "V03", "V06", "V07", "V-A")
HOLM_Z = (2.394, 2.326, 2.241, 2.128, 1.960, 1.645)
L_END = "2026-07"
L_C = ("2020-02", "2026-07")
S_WIN = ("2016-09", "2026-08")
S_OVERLAP = ("2016-09", "2026-07")
SYNC_EXCL = (("1932-07", "1933-07"), ("2008-10", "2009-08"), ("2020-02", "2020-08"))
UNIVERSE_BREAKS = ("1963-07", "1973-01")
NAMED_EVENTS = {
    "crash": (("1929-09", "1932-06"), ("1937-03", "1938-03"), ("1973-01", "1974-09"), ("1987-09", "1987-11"),
              ("2000-09", "2002-09"), ("2007-11", "2009-02"), ("2020-02", "2020-03"), ("2022-01", "2022-09")),
    "rebound": (("1932-07", "1932-08"), ("1933-04", "1933-07"), ("1974-10", "1975-06"), ("1982-08", "1983-06"),
                ("2003-03", "2003-12"), ("2009-03", "2009-08"), ("2020-04", "2020-08"), ("2025-05", "2025-07")),
}
SIGMA_L_WIN = ("1927-01", "2026-07")
ZZ_HD = ZZ_HU = 0.10
ZZ_REB_TD = 63
ZZ_START, ZZ_END = "1927-12-30", "2026-08-31"
TIE = 0.00005
G6A_MIN = 0.55
TURN_MAX = C.TURN_MAX
REB_MISS_MIN = 3
REB_MISS_MONTHS = 3
RANK_MIN = 0.90
FID_RHO = 0.60
RHO_MIN_OVERLAP = 36
BY_Q = 0.10
CUM_N = (878, 85)              # 랩 누적 약 878 + V 팔 약 85(명세 cumulative_N) — DSR 보고만
ADOPT_WEB = ("V01", "V03", "V06", "V07")
GSPC_SEED = os.path.join(os.path.dirname(VD.CACHE), "tbatch_cache", "raw", "yf", "_GSPC.csv")


def per(x):
    return x if isinstance(x, pd.Period) else pd.Period(str(x)[:7], "M")


def in_win(idx, a, b):
    idx = pd.PeriodIndex(idx, freq="M")
    return np.asarray((idx >= per(a)) & (idx <= per(b)))


# ══════════════════════════════════════════════════════════════════════════
#  통계(복사: eg30plus.nw_t · t_core norm_sf · h1 · by_info · stouffer · qbatch_run.dsr)
# ══════════════════════════════════════════════════════════════════════════
def nw_t(x, lag=NW_LAG):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return None
    e = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else None


def norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def h1(x):
    x = pd.Series(x, dtype=float).dropna()
    n = int(len(x))
    if n == 0:
        return {"n": 0, "mean": None, "ann": None, "t": None, "t12": None, "p": None}
    t6, t12 = nw_t(x.to_numpy(), NW_LAG), nw_t(x.to_numpy(), NW_LAG_REPORT)
    sd = float(x.std(ddof=1)) if n > 1 else None
    return {"n": n, "mean": float(x.mean()), "ann": float(x.mean() * 12), "te": (sd * math.sqrt(12) if sd else None),
            "ir": (float(x.mean() * 12 / (sd * math.sqrt(12))) if sd else None), "t": t6, "t12": t12,
            "p": (norm_sf(t6) if t6 is not None else None), "first": str(x.index[0]), "last": str(x.index[-1])}


def holm(pvals, alpha=HOLM_ALPHA):
    """Holm 단계 하강 — 한쪽 p · 작은 p 부터 α/(m − k) · 한 번 못 넘으면 멈춘다(None 은 기각 못 함 · 분모에 남는다)."""
    ks = list(pvals)
    m = len(ks)
    order = sorted(ks, key=lambda k: (pvals[k] is None, pvals[k] if pvals[k] is not None else 9.0))
    rej = {k: False for k in ks}
    thr = {}
    for j, k in enumerate(order):
        a = alpha / (m - j)
        thr[k] = a
        p = pvals[k]
        if p is not None and p <= a:
            rej[k] = True
        else:
            break
    for k in ks:
        thr.setdefault(k, None)
    return {"reject": rej, "threshold": thr, "order": order, "alpha": alpha, "m": m}


def by_info(pvals, q=BY_Q):
    m = len(pvals)
    cm = sum(1.0 / i for i in range(1, m + 1)) if m else 1.0
    ps = sorted((v, k) for k, v in pvals.items() if v is not None)
    kmax = 0
    for r, (v, _) in enumerate(ps, 1):
        if v <= (q / cm) * r / m + 1e-15:
            kmax = r
    return {"q": q, "c_m": cm, "m": m, "k": kmax, "admitted": sorted(k for _, k in ps[:kmax])}


def stouffer(tstats, xseries, min_overlap=RHO_MIN_OVERLAP):
    ids = list(tstats)
    k = len(ids)
    Rm = np.eye(k)
    for i in range(k):
        for j in range(i + 1, k):
            a, b = xseries.get(ids[i]), xseries.get(ids[j])
            r = 0.0
            if a is not None and b is not None:
                c = pd.concat([pd.Series(a), pd.Series(b)], axis=1, join="inner").dropna()
                if len(c) >= min_overlap and c.iloc[:, 0].std() > 0 and c.iloc[:, 1].std() > 0:
                    r = float(np.corrcoef(c.iloc[:, 0], c.iloc[:, 1])[0, 1])
            Rm[i, j] = Rm[j, i] = r
    tv = np.array([0.0 if tstats[i] is None else float(tstats[i]) for i in ids])
    den = float(Rm.sum())
    z = float(tv.sum() / math.sqrt(den)) if den > 0 else None
    return {"members": ids, "z": z, "p": (norm_sf(z) if z is not None else None), "den": den, "role": "보고만"}


def dsr(x, n_trials):
    """Deflated Sharpe(보고만) — 복사: qbatch_run.dsr."""
    from scipy.stats import norm, skew, kurtosis
    x = np.asarray(pd.Series(x, dtype=float).dropna(), float)
    T = len(x)
    if T < 12 or x.std(ddof=1) == 0:
        return {"N": n_trials, "dsr": None}
    sr = x.mean() / x.std(ddof=1)
    g3, g4 = float(skew(x)), float(kurtosis(x, fisher=False))
    emc = 0.5772156649
    v = 1.0 / (T - 1)
    sr0 = math.sqrt(v) * ((1 - emc) * norm.ppf(1 - 1.0 / n_trials) + emc * norm.ppf(1 - 1.0 / (n_trials * math.e))) if n_trials > 1 else 0.0
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr * sr))
    return {"N": n_trials, "sr_m": float(sr), "sr0": float(sr0), "dsr": float(norm.cdf((sr - sr0) * math.sqrt(T - 1) / den))}


# ══════════════════════════════════════════════════════════════════════════
#  주 통계 — DM 식 (3) 베타 항을 뺀 조건부 베타 조정 α
# ══════════════════════════════════════════════════════════════════════════
def nw_ols(y, X, lag=NW_LAG):
    """OLS + NW(lag) 공분산(연속 관측 지연 · Bartlett · 자유도 보정 없음) — (계수, se, n)."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, k = X.shape
    XtX = X.T @ X
    inv = np.linalg.pinv(XtX)
    b = inv @ X.T @ y
    e = y - X @ b
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for l in range(1, min(lag, n - 1) + 1):
        G = Xe[l:].T @ Xe[:-l]
        S += (1.0 - l / (lag + 1.0)) * (G + G.T)
    V = inv @ S @ inv
    return b, np.sqrt(np.maximum(np.diag(V), 0.0)), n


def dm_regressors(mkt, rf):
    """(MKT_t, I_B,t−1, I_U,t) — 보유 달 색인. mkt = 시장 총수익(L: French Mkt · S: SPY TR) · rf = 월 무위험."""
    m = VD.contiguous(pd.Series(mkt, dtype=float))
    r = pd.Series(rf, dtype=float).reindex(m.index)
    ib = VC.ib24(m).shift(1)
    mex = m - r
    iu = (mex > 0).astype(float).where(mex.notna())
    return pd.DataFrame({"MKT": mex, "IB": ib, "IU": iu})


def beta_adj_alpha(delta, regs, win=None, lag=NW_LAG):
    """주 통계 — Δ_t = a + b0·MKT + bB·I_B,t−1·MKT + bBU·I_B,t−1·I_U,t·MKT + e · a 의 NW(6) t · 한쪽 p · 원 Δ NW t(보고). 🚨 수익 통계."""
    d = pd.Series(delta, dtype=float)
    df = pd.concat([d.rename("D"), pd.DataFrame(regs)], axis=1, join="inner").dropna()
    if win is not None:
        df = df.loc[in_win(df.index, *win)]
    n = len(df)
    if n < 24:
        return {"n": n, "a": None, "t": None, "p": None, "t_raw": None}
    M = df["MKT"].to_numpy()
    X = np.column_stack([np.ones(n), M, df["IB"].to_numpy() * M, df["IB"].to_numpy() * df["IU"].to_numpy() * M])
    b, se, _ = nw_ols(df["D"].to_numpy(), X, lag)
    t = float(b[0] / se[0]) if se[0] > 0 else None
    return {"n": n, "a": float(b[0]), "coef": [float(x) for x in b], "se_a": float(se[0]), "t": t, "p": (norm_sf(t) if t is not None else None),
            "t_raw": nw_t(df["D"].to_numpy(), lag), "first": str(df.index[0]), "last": str(df.index[-1])}


# ══════════════════════════════════════════════════════════════════════════
#  사건(복사: t_core events_L · events_S · zigzag_legs) · 보고 묶음(bundle · year_table · blocks4 · seg_sum)
# ══════════════════════════════════════════════════════════════════════════
class Events:
    def __init__(self, tag, down, crash, surge, legs, rebounds, sigma=None):
        self.tag, self.sigma = tag, sigma
        self._down, self._crash, self._surge = down, crash, surge
        self.legs, self.rebounds = legs, rebounds

    def down(self, idx, B=None):
        return self._flag(self._down, idx, B)

    def crash(self, idx, B=None):
        return self._flag(self._crash, idx, B)

    def surge(self, idx, B=None):
        return self._flag(self._surge, idx, B)

    @staticmethod
    def _flag(f, idx, B):
        idx = pd.PeriodIndex(idx, freq="M")
        if callable(f):
            return np.asarray(f(idx, B), bool)
        return np.array([str(p) in f for p in idx], bool)


def _months_between(a, b):
    return [str(p) for p in pd.period_range(a[:7], b[:7], freq="M")]


def zigzag_legs(dates, prices, start=ZZ_START, end=ZZ_END):
    import mech_episodes as MEP                                      # 허용 목록 — 함수 안
    D = list(dates)
    P = [None if (p is None or p != p) else float(p) for p in prices]
    legs, op = MEP.zigzag(D, P, ZZ_HD, ZZ_HU, start, end)
    reb = MEP.rebounds(D, P, legs, op, ZZ_REB_TD)
    L = [{"side": s, "a": a, "b": b, "move": mv, "months": _months_between(a, b)} for s, a, b, mv, _c in legs]
    Rb = [dict(r, months=_months_between(r["a"], r["b"])) for r in reb]
    return L, Rb


def sigma_L(mkt_tr):
    s = pd.Series(mkt_tr, dtype=float).dropna()
    s = s.loc[in_win(s.index, *SIGMA_L_WIN)]
    if len(s) < 1000:
        raise SystemExit("🚨 σ_L 표본이 %d개월 — French Mkt 가 모자란다" % len(s))
    return float(s.std(ddof=1))


def gspc_daily():
    """^GSPC 일간(L 사건 지그재그) — 캐시 raw/yf/_GSPC.csv(없으면 배치 T 고정본 사본을 SHA 로 들인다 · 저장소 밖)."""
    p = os.path.join(VD.cache_guard(), "raw", "yf", "_GSPC.csv")
    if not os.path.exists(p):
        if not os.path.exists(GSPC_SEED):
            raise FileNotFoundError("^GSPC 고정본 없음")
        with open(GSPC_SEED, "rb") as f:
            blob = f.read()
        VD._write_bytes(p, blob)
        meta = {"key": "yf/^GSPC", "origin": "copy:tbatch_cache", "sha256": VD.sha256_bytes(blob), "pinned_at": VD._now()}
        VD._write_bytes(os.path.join(VD.cache_guard(), "meta", "yf___GSPC.json"), json.dumps(meta, ensure_ascii=False).encode("utf-8"))
    df = pd.read_csv(p, index_col=0)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index, format="%Y-%m-%d"))
    return df["Close"].sort_index()


def gspc_month_pr(gspc):
    """^GSPC 월 가격수익(월말 종가 대 월말 종가 · 보유 달 색인) — L 하락월 판정(명세 tests.fund_frame «하락월 = S&P 500 PR < 0»)."""
    g = pd.Series(gspc, dtype=float).dropna()
    me = g.groupby(g.index.to_period("M")).last()
    return (me / me.shift(1) - 1.0).dropna()


def events_L(B, sigma, gspc):
    """L 사건 — 🔧 검토 고침(등록 전): 하락월 = ^GSPC 월 가격수익 < 0(명세 fund_frame · 고정본 1927-12-30 ~ · 첫 월 수익 1928-01) ·
    ^GSPC 가 없는 달(1928-01 앞)만 French Mkt 총수익 < 0 으로 잇는다(선언) · CRASH-M · SURGE-M 은 t_core 그대로 French Mkt TR ±σ_L · 다리 · 반등 = ^GSPC 지그재그."""
    Bs = pd.Series(B, dtype=float)
    dates = [d.strftime("%Y-%m-%d") for d in gspc.index]
    legs, reb = zigzag_legs(dates, gspc.to_numpy(float))
    pr = gspc_month_pr(gspc)

    def down(idx, _B=None):
        idx = pd.PeriodIndex(idx, freq="M")
        a = pr.reindex(idx)
        return np.where(a.notna().to_numpy(), (a < 0).to_numpy(), (Bs.reindex(idx) < 0).to_numpy())
    return Events("L", down, lambda idx, _B=None: (Bs.reindex(idx) <= -sigma).to_numpy(),
                  lambda idx, _B=None: (Bs.reindex(idx) >= sigma).to_numpy(), legs, reb, sigma)


def events_S():
    ME = json.load(io.open(os.path.join(VD.DATA, "mech_episodes.json"), encoding="utf-8"))
    fz = ME["frozen"]
    legs = [{"side": l["side"], "a": l["a"], "b": l["b"], "move": l["move"], "months": _months_between(l["a"], l["b"])} for l in fz["legs"]]
    reb = [dict(r, months=_months_between(r["a"], r["b"])) for r in fz["rebounds"]]
    return Events("S", set(ME["months"]["down_m"]), set(ME["months"]["crash_m"]), set(ME["months"]["surge_m"]), legs, reb, ME.get("sigma_pre"))


def year_table(X, B):
    df = pd.concat([pd.Series(X, dtype=float), pd.Series(B, dtype=float)], axis=1, join="inner").dropna()
    df.columns = ["X", "B"]
    out = {}
    for y, g in df.groupby(df.index.year):
        f = float(np.prod(1 + g["B"] + g["X"]) - 1)
        b = float(np.prod(1 + g["B"]) - 1)
        out[int(y)] = {"ex": f - b, "n": int(len(g))}
    full = {y: v for y, v in out.items() if v["n"] >= 12}
    won = sum(1 for v in full.values() if v["ex"] >= TIE)
    lost = sum(1 for v in full.values() if v["ex"] <= -TIE)
    ties = [y for y, v in full.items() if abs(v["ex"]) < TIE]
    dec = won + lost
    return {"years": out, "won": won, "lost": lost, "ties": ties, "rate": (won / dec if dec else None),
            "partial": sorted(y for y, v in out.items() if v["n"] < 12), "n_full": len(full)}


def blocks4(X):
    x = pd.Series(X, dtype=float).dropna()
    n = len(x)
    if n < 4:
        return [None] * 4
    return [float(x.iloc[c].mean()) for c in np.array_split(np.arange(n), 4)]


def seg_sum(X, months):
    s = pd.Series(X, dtype=float)
    v = s.reindex(pd.PeriodIndex([per(m) for m in months], freq="M")).dropna()
    return (float(v.sum()), int(len(v))) if len(v) else (None, 0)


def sync_mask(idx):
    idx = pd.PeriodIndex(idx, freq="M")
    m = np.zeros(len(idx), bool)
    for a, b in SYNC_EXCL:
        m |= in_win(idx, a, b)
    return m


def bundle(X, B, ev):
    """보고 묶음(복사: t_core.bundle — 반등 놓침은 V 규칙 reb_miss_v 로 따로)."""
    X = pd.Series(X, dtype=float).dropna()
    idx = X.index
    Bv = pd.Series(B, dtype=float).reindex(idx)
    dn, cr, su = ev.down(idx, Bv), ev.crash(idx, Bv), ev.surge(idx, Bv)
    xv = X.to_numpy()
    mean = lambda m: (float(xv[m].mean()) if m.any() else None)
    legs = []
    for l in ev.legs:
        s, n = seg_sum(X, l["months"])
        if n:
            legs.append({"side": l["side"], "a": l["a"], "b": l["b"], "x": s, "n": n})
    rebs = []
    for r in ev.rebounds:
        s, n = seg_sum(X, r["months"])
        if n:
            rebs.append({"a": r["a"], "b": r["b"], "x": s, "n": n})
    named = {}
    for kind, rows in NAMED_EVENTS.items():
        for a, b in rows:
            s, n = seg_sum(X, [str(p) for p in pd.period_range(a, b, freq="M")])
            if n:
                named["%s %s~%s" % (kind, a, b)] = {"x": s, "n": n}
    yt = year_table(X, Bv)
    r36 = X.rolling(36).sum().dropna()
    brk = {}
    for m in UNIVERSE_BREAKS:
        pre, post = X.loc[idx < per(m)], X.loc[idx >= per(m)]
        brk[m] = [float(pre.mean()) if len(pre) else None, float(post.mean()) if len(post) else None]
    cl = [x for x in legs if x["side"] == "crash"]
    return {"h1": h1(X), "down": {"n": int(dn.sum()), "mean": mean(dn), "win": (float((xv[dn] > 0).mean()) if dn.any() else None)},
            "up": {"n": int((~dn).sum()), "mean": mean(~dn)}, "crash_m": {"n": int(cr.sum()), "mean": mean(cr)},
            "surge_m": {"n": int(su.sum()), "mean": mean(su)},
            "crash_legs": {"n": len(cl), "mean": (float(np.mean([x["x"] for x in cl])) if cl else None), "won": sum(1 for x in cl if x["x"] > 0)},
            "rebounds": {"n": len(rebs), "mean": (float(np.mean([x["x"] for x in rebs])) if rebs else None), "won": sum(1 for x in rebs if x["x"] > 0)},
            "named": named, "years": yt, "roll36_neg": (float((r36 < 0).mean()) if len(r36) else None), "blocks4": blocks4(X),
            "universe_breaks": brk}


def reb_miss_v(theta, theta0, dD, ev, B):
    """T3 — θ_t < θ0 인 결정 달 뒤 보유월 t+1..t+3 가운데 SURGE-M 달 · ≥ 3 이면 평균 Δ ≥ 0."""
    th = pd.Series(theta, dtype=float)
    d = pd.Series(dD, dtype=float).dropna()
    Bv = pd.Series(B, dtype=float)
    cut = set()
    for t, x in th.items():
        if x == x and x < theta0 - 1e-12:
            for k in range(1, REB_MISS_MONTHS + 1):
                cut.add(t + k)
    ms = sorted(p for p in cut if p in d.index)
    if ms:
        ms_idx = pd.PeriodIndex(ms, freq="M")
        su = ev.surge(ms_idx, Bv.reindex(ms_idx))
        ms = [p for p, s in zip(ms, su) if s]
    v = d.reindex(pd.PeriodIndex(ms, freq="M")) if ms else pd.Series(dtype=float)
    applies = len(v) >= REB_MISS_MIN
    return {"months": [str(p) for p in v.index], "n": int(len(v)), "mean_dD": (float(v.mean()) if len(v) else None), "applies": bool(applies),
            "ok": (bool(v.mean() >= 0) if applies else True)}


# ══════════════════════════════════════════════════════════════════════════
#  관문(V 명세로 매개변수화 · D23) · S 층 구현성 · 채택 표시
# ══════════════════════════════════════════════════════════════════════════
def _b(v):
    if v is None:
        return False
    if isinstance(v, (float, np.floating)) and v != v:
        return False
    return bool(v)


def _pos(v):
    return _b(v is not None and v == v and v > 0)


def _same_sign(v, ref):
    if v is None or ref is None or ref == 0 or v != v:
        return False
    return (v > 0) == (ref > 0) and v != 0


def gates_w(bd, variants=None, turn=None, rebmiss=None, na=()):
    """사용자 관문(W 카드 · 명세 user_gates_on_W_cards) — bd = bundle(X_W) · variants = {cost2x, sync, t1}(X 평균) · turn = 편도 연 회전.
    G2 양면(CRASH-M · SURGE-M 평균 X 모두 > 0 · 반등 놓침 ok) · G3 하락월 X ≥ 0(모든 전략 같다) · G5 (a)(d)(e)(h) · T+1 · G6a 승률 ≥ 0.55."""
    V = variants or {}
    ref = bd["h1"]["mean"]
    cm, sm = bd["crash_m"]["mean"], bd["surge_m"]["mean"]
    both = _pos(cm) and _pos(sm)
    g2 = {"crash_m": cm, "surge_m": sm, "ok": both and _b((rebmiss or {"ok": True})["ok"]), "rebound_miss": rebmiss}
    dm = bd["down"]["mean"]
    g3 = {"down_mean": dm, "ok": _b(dm is not None and dm >= 0)}
    g5 = {"a_blocks": _b(sum(1 for v in bd["blocks4"] if _pos(v)) >= 3), "d_cost2x": _pos(V.get("cost2x")),
          "e_turn": _b(turn is not None and turn <= TURN_MAX), "h_sync": _same_sign(V.get("sync"), ref),
          "t1": (_same_sign(V.get("t1"), ref) if "t1" in V else None)}
    for k in na:
        g5[k] = None
    g5_ok = all(v for k, v in g5.items() if v is not None)
    yr = bd["years"]
    g6 = {"a_rate": yr["rate"], "a_ok": _b(yr["rate"] is not None and yr["rate"] >= G6A_MIN), "ties": yr["ties"], "partial": yr["partial"]}
    return {"G2": g2, "G3": g3, "G5": dict(g5, ok=g5_ok), "G6": g6, "adopt_gates": bool(g2["ok"] and g3["ok"] and g6["a_ok"])}


def fid(yS, yL, win=S_OVERLAP, min_n=RHO_MIN_OVERLAP):
    """T4 — corr(S 능동, L 대리) 겹친 달 ≥ 36 · ≥ 0.60. 🚨 수익 통계."""
    c = pd.concat([pd.Series(yS, dtype=float), pd.Series(yL, dtype=float)], axis=1, join="inner").dropna()
    c = c.loc[in_win(c.index, *win)]
    if len(c) < min_n or c.iloc[:, 0].std() == 0 or c.iloc[:, 1].std() == 0:
        return {"n": len(c), "rho": None, "gate": False}
    r = float(np.corrcoef(c.iloc[:, 0], c.iloc[:, 1])[0, 1])
    return {"n": len(c), "rho": r, "gate": bool(r >= FID_RHO)}


def h_basis(X, P, rf):
    """T5 — H = X − 0.1·(β̂_책 − 1)·(SPY TR − rf)(보유 달 · β̂ = 체결 책 FP β̂). 🚨 수익."""
    r = pd.Series(rf, dtype=float).reindex(P.index)
    return X - C.SLEEVE * (P["beta"] - 1.0) * (P["B"] - r)


def s_x(P, mult=1.0, row="t1", bench="B"):
    """S 층 X 계열 — 🔧 검토 고침(등록 전): 주 행 = T+1 종가 체결(명세 common_frame.rebalance «주 체결 T+1 종가(D0 는 측정 행)») · row="d0" 은 측정 행."""
    S = P["S_t1"] if row == "t1" else P["S"]
    return C.fund_x(S, P[bench], P["rate"], P["traded"], mult=mult)


def s_tests(P, turn, yS=None, yL=None, sid=None, rf=None, ev=None):
    """S 층 구현성(명세 S_layer.role) — P = SLayer.path 결과 · X(주 T+1 10bp · 20bp · D0 측정 행) · G5e 회전 · FID · EW 우주 기준(보고) · H 기준 G3(보고) ·
    «S 점 > 0» 은 보고만(D20). 🔧 h1_10 · h1_20 · 묶음 · H · EW 는 주 행(T+1) · h1_d0 = D0 측정 행."""
    P = P.loc[in_win(P.index, *S_WIN)]
    X10 = s_x(P)
    X20 = s_x(P, mult=2.0)
    Xd0 = s_x(P, row="d0")
    Xew = s_x(P, bench="B_EW") if "B_EW" in P else None
    f = fid(yS, yL) if (yS is not None and yL is not None) else None
    out = {"n": int(len(P)), "h1_10": h1(X10), "h1_20": h1(X20), "h1_d0": h1(Xd0), "h1_ew": (h1(Xew) if Xew is not None else None),
           "row": "T+1(주) · D0(측정 행 h1_d0)",
           "turn_1w": turn, "g5e": _b(turn is not None and turn <= TURN_MAX), "fid": f, "s_point_pos_report": _pos(h1(X10)["mean"]),
           "role": "구현성 · 부호만(채택 조건 아님: S 점)"}
    if rf is not None:
        H = h_basis(X10, P, rf)
        out["h1_H"] = h1(H)
        if ev is not None:
            out["G3_H_down_mean"] = bundle(H.dropna(), P["B"], ev)["down"]["mean"]
    if ev is not None:
        bd = bundle(X10.dropna(), P["B"], ev)
        out["G3_down_mean"] = bd["down"]["mean"]
        out["bundle"] = bd
    return out


FORWARD_ONLY = ("V08",)       # 전방 전용 카드 — H_V · 부 가족(BY) · 배분기 밖(등록 §1.8 · §8.2)


def _is_forward_only(key):
    return any(key == f or key.endswith(":" + f) or key.split(":")[-1] == f for f in FORWARD_ONLY)


def secondary_family(static_L, s_layer):
    """부 가족(명세 multiplicity.secondary · 보고) — BY FDR q 0.10: 정적판 L X > 0(5) · S 층 Δ 와 X(7 + 배분기). 쌍둥이는 어떤 가족에도 들지 않는다.
    🔧 검토 고침(등록 전): 전방 전용 카드(V08)는 들지 않는다 — 들어온 열쇠는 거르고 «excluded» 에 이름만 적는다."""
    pv = {"L_static:" + k: (v or {}).get("p") for k, v in static_L.items() if not _is_forward_only(k)}
    pv.update({"S:" + k: (v or {}).get("p") for k, v in s_layer.items() if not _is_forward_only(k)})
    out = by_info(pv, BY_Q)
    out["excluded"] = sorted([k for k in list(static_L) + list(s_layer) if _is_forward_only(k)])
    return out


def adoption_marks(hv, joint, gates_L, s_res, fidg, g_egd, anchor_ok, alloc=None):
    """채택 표시(명세 tests.adoption_marking) — 등록된 스크립트가 기계적으로. 카드를 더하거나 빼지 않는다.
    거미줄 단독(MOM · LIQ · VAL · QLT): H_V 기각 ∧ 공동 ∧ L W G2 · G3 · G6a ∧ S G5e ∧ FID ∧ G-EGD ∧ 시총 앵커.
    배분기(VFA): H_V Δ_A 기각 ∧ 공동 ∧ L FULL G2 · G3 · G6a ∧ S G5e. LBS 단독 없음 · INS · EAR 측정만 · V08 전방 전용 · 정적 경로 없음."""
    out = {}
    for sid in ADOPT_WEB:
        conds = {"holm": _b(hv.get(sid)), "joint": _b(joint.get(sid)), "gates_L": _b((gates_L.get(sid) or {}).get("adopt_gates")),
                 "g5e_S": _b((s_res.get(sid) or {}).get("g5e")), "fid": _b(fidg.get(sid)), "g_egd": _b(g_egd.get(sid)), "anchor": _b(anchor_ok)}
        out[sid] = {"path": "web_alone", "conds": conds, "adopt": all(conds.values())}
    a = alloc or {}
    conds = {"holm": _b(hv.get("V-A")), "joint": _b(joint.get("V-A")), "gates_L": _b((a.get("gates_L") or {}).get("adopt_gates")),
             "g5e_S": _b(a.get("g5e"))}
    out["VFA"] = {"path": "allocator", "conds": conds, "adopt": all(conds.values())}
    out["V02"] = {"path": "none(배분기 구성원만)", "adopt": False}
    for sid in ("V04", "V05"):
        out[sid] = {"path": "measure_only", "adopt": False}
    out["V08"] = {"path": "forward_only(VFWD 측정 · 전방 채택 카드)", "adopt": False}
    return out


def hv_family(stats_by_member):
    """H_V — {구성원: 베타 조정 α 결과} → Holm(m 6 · 한쪽 α 0.05) · 문턱 z 표 · BY(보고)."""
    pv = {k: (stats_by_member.get(k) or {}).get("p") for k in H_V}
    ho = holm(pv, HOLM_ALPHA)
    return {"members": list(H_V), "holm": ho, "z_thresholds": list(HOLM_Z), "by": by_info(pv), "t": {k: (stats_by_member.get(k) or {}).get("t") for k in H_V}}


# ══════════════════════════════════════════════════════════════════════════
#  VFWD 전방 관문(명세 forward_plan · 🔧 검토 고침 — 등록 커밋에 얼린다: VFWD 원장 등록은 이 함수를 부를 뿐 · 더 좁히는 것만)
# ══════════════════════════════════════════════════════════════════════════
FF = {"FF1_months": 24, "FF1_t": -1.0, "FF2_months": 36, "FF2_t": 1.0, "late_window": 36, "late_max": 3, "publish_months": 60,
      "events_min": {"crash_legs": 3, "rebounds": 3, "crash_m": 4, "surge_m": 4, "down": 10}}


def ff_late_fill(X, X_main, late):
    """FF0 — 늦은 결정 · 핀 어긋남 · 대체 판을 쓴 달(late = 참)은 주 대조의 X 로 채운다(W → S · VFA → VFE · VF08S → X = 0 · X_main 이 None 이면 0).
    돌려주는 것 (채운 X, 첫 late_window 달의 늦음 수)."""
    X = pd.Series(X, dtype=float)
    lt = pd.Series(late, dtype=bool).reindex(X.index).fillna(False)
    fill = (pd.Series(X_main, dtype=float).reindex(X.index) if X_main is not None else pd.Series(0.0, index=X.index)).fillna(0.0)
    out = X.where(~lt, fill)
    n_late = int(lt.iloc[:FF["late_window"]].sum())
    return out, n_late


def ff1(delta):
    """FF1(24개월) 반증 — Δ(거미줄 W − S · 배분기 VFA − VFE · VF08S 는 X 자체)의 NW(6) t ≤ −1.0 이면 기각(측정은 계속). 24개월 전에는 판정 없음."""
    d = pd.Series(delta, dtype=float).dropna()
    if len(d) < FF["FF1_months"]:
        return {"n": len(d), "due": False, "t": None, "rejected": False}
    t = nw_t(d.iloc[:FF["FF1_months"]].to_numpy(), NW_LAG)
    return {"n": len(d), "due": True, "t": t, "rejected": bool(t is not None and t <= FF["FF1_t"])}


def ff2(X, delta, regs, ev, B, H=None, X20=None, Xd0=None, turn=None, v=None, n_late=0, kind="W"):
    """FF2(≥ 36개월) «전방 일치» — 명세 forward_plan.FF2 (a)~(g) · 사건 최소(급락 다리 3 · 반등 3 · CRASH-M 4 · SURGE-M 4 · 하락월 10) · 첫 36개월 늦음 ≥ 3 이면 막힘.
    kind = "W"(거미줄 · Δ = W − S) · "A"(배분기 · Δ = VFA − VFE) · "N"(VF08S · Δ = X 자체 · (g) 해당 없음). 통과는 확인이 아니다(60개월에 한 번 더)."""
    X = pd.Series(X, dtype=float).dropna()
    D = pd.Series(delta, dtype=float).reindex(X.index)
    n = len(X)
    if n < FF["FF2_months"]:
        return {"n": n, "due": False, "pass": False}
    bd = bundle(X, B, ev)
    em = FF["events_min"]
    ev_ok = (bd["crash_legs"]["n"] >= em["crash_legs"] and bd["rebounds"]["n"] >= em["rebounds"] and bd["crash_m"]["n"] >= em["crash_m"]
             and bd["surge_m"]["n"] >= em["surge_m"] and bd["down"]["n"] >= em["down"])
    tX = nw_t(X.to_numpy(), NW_LAG)
    a = {"mean_pos": _pos(float(X.mean())), "t_ge": _b(tX is not None and tX >= FF["FF2_t"])}
    ab = beta_adj_alpha(D.dropna(), regs)
    Bv = pd.Series(B, dtype=float).reindex(D.index)
    dn = ev.down(D.index, Bv)
    Dd = D.to_numpy()[dn]
    b_ = {"alpha_t_ge": _b(ab.get("t") is not None and ab["t"] >= FF["FF2_t"]), "down_delta_ge0": _b(len(Dd) > 0 and float(np.nanmean(Dd)) >= 0)}
    c = {"two_sided": _pos(bd["crash_m"]["mean"]) and _pos(bd["surge_m"]["mean"])}
    hmean = float(pd.Series(H, dtype=float).dropna().mean()) if H is not None and len(pd.Series(H).dropna()) else None
    d = {"down_x_ge0": _b(bd["down"]["mean"] is not None and bd["down"]["mean"] >= 0), "H_pos": _pos(hmean)}
    blocks = [X.iloc[i:i + 12] for i in range(0, n - n % 12, 12)]
    won = sum(1 for bl in blocks if float(np.prod(1 + bl.to_numpy()) - 1) > 0)
    e = {"blocks_major": _b(len(blocks) > 0 and won > len(blocks) / 2.0)}
    f = {"x20_pos": _pos(float(pd.Series(X20).dropna().mean()) if X20 is not None else None),
         "d0_pos": _pos(float(pd.Series(Xd0).dropna().mean()) if Xd0 is not None else None), "turn_ok": _b(turn is not None and turn <= TURN_MAX)}
    if kind == "N":
        g = {"na": True}
    else:
        vv = pd.Series(v, dtype=float).reindex(D.index) if v is not None else pd.Series(np.nan, index=D.index)
        on, off = D[vv.fillna(0) != 0].dropna(), D[vv.fillna(0) == 0].dropna()
        g = {"on_gt_off": _b(len(on) > 0 and len(off) > 0 and float(on.mean()) > float(off.mean()))}
    conds = {"a": all(a.values()), "b": all(b_.values()), "c": c["two_sided"], "d": all(d.values()), "e": e["blocks_major"], "f": all(f.values()),
             "g": (True if kind == "N" else g["on_gt_off"]), "events": ev_ok, "late_ok": n_late < FF["late_max"]}
    return {"n": n, "due": True, "parts": {"a": a, "b": b_, "c": c, "d": d, "e": e, "f": f, "g": g}, "conds": conds, "pass": bool(all(conds.values())),
            "note": "«전방 일치»(확인이 아니다) · 60개월에 한 번 더 넘어야 게시"}


# ══════════════════════════════════════════════════════════════════════════
#  L 층 평가(🚨 수익 통계 · 굽기 · 눈가린 연기에서만 · L 층 값은 저장소에 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def l_window(first_active):
    if first_active is None:
        return None
    return (str(per(first_active) + 1), L_END)


def l_card_eval(LL, sid, ev, regs, tau=None, nperm=NPERM, seed=SEED, twin=None, over=None):
    """L 층 한 카드 — W · S0 팔 · Δ · 베타 조정 α(L-R · L-C) · 위약 순위 · 반등 놓침 · 관문(W 카드 X).
    over = 굽기 선택(F0 결정 — v_cards.spec_of 의 over · 예: liq_emergency 는 V03 의 θ0 · Δθ 를 바꾼다 · v_run 이 등록 F0 에서 넘긴다)."""
    import v_cards as VK
    import v_alloc as VA
    sp = VK.spec_of(sid, twin, **(over or {}))
    prox = VK.twin_proxy(twin, sid)
    w = LL.web(sp, proxy=prox)
    th = LL.theta(sp, w["v"])
    aW, a0 = LL.arm(prox, th, tau=tau), LL.arm(prox, pd.Series(sp["theta0"], index=LL.axis), tau=tau)
    XW = C.fund_x(aW["S"], aW["B"], aW["rate"], aW["tf"], aW["fixed"])
    X0 = C.fund_x(a0["S"], a0["B"], a0["rate"], a0["tf"], a0["fixed"])
    D = (XW - X0).dropna()
    win = l_window(w["first_active"])
    st = beta_adj_alpha(D, regs, win) if win else {"n": 0, "a": None, "t": None, "p": None}
    lc = beta_adj_alpha(D, regs, L_C)
    rm = reb_miss_v(th, sp["theta0"], D, ev, aW["B"])
    # 위약(T2)
    ranks = None
    if nperm and win and st["a"] is not None:
        cols = w["strands"]
        rng = np.random.default_rng(seed)
        below, n_ok = 0, 0
        for _ in range(nperm):
            Z2 = LL.Z.copy()
            Z2[cols] = VA.block_shuffle_rows(LL.Z[cols].to_numpy(float), rng)
            w2 = LL.web(sp, Zover=Z2, proxy=prox)
            th2 = LL.theta(sp, w2["v"])
            a2 = LL.arm(prox, th2, tau=tau)
            X2 = C.fund_x(a2["S"], a2["B"], a2["rate"], a2["tf"], a2["fixed"])
            s2 = beta_adj_alpha((X2 - X0).dropna(), regs, win)
            n_ok += 1
            if s2["a"] is not None and s2["a"] < st["a"]:
                below += 1
        ranks = below / float(nperm)
    Xw = XW.loc[in_win(XW.index, *win)] if win else XW.iloc[:0]
    bd = bundle(Xw, aW["B"], ev) if len(Xw) else None
    X2x = C.fund_x(aW["S"], aW["B"], aW["rate"], aW["tf"], aW["fixed"], mult=2.0)
    variants = {"cost2x": float(X2x.loc[Xw.index].mean()) if len(Xw) else None,
                "sync": float(Xw[~sync_mask(Xw.index)].mean()) if len(Xw) else None}
    G = gates_w(bd, variants, turn=aW["turn_1w"], rebmiss=rm, na=("t1",)) if bd else None
    joint = bool(_pos(lc.get("a")) and ranks is not None and ranks >= RANK_MIN and rm["ok"])
    return {"sid": sid, "twin": twin, "window": win, "alpha": st, "alpha_LC": lc, "placebo_rank": ranks, "nperm": nperm, "rebound_miss": rm,
            "joint": joint, "gates": G, "turn_1w": aW["turn_1w"], "strands": w["strands"], "first_active": w["first_active"],
            "static_h1": h1(X0.loc[in_win(X0.index, *(win or ("1900-01", "1900-01")))]), "delta": D, "XW": XW, "X0": X0}


def l_alloc_eval(LL, ev, regs, thetas_static, thetas_web, taus=None, nperm=NPERM, seed=SEED, members=None):
    """L 층 배분기 — Δ_A = X(C-A) − X(C0) · 베타 조정 α · 위약(상대 점수 행렬 달 블록째) · FULL 관문.
    members = 배분기 구성원(기본 MOM · LBS · LIQ · VAL · QLT — v_run 이 등록 F0 의 G-EGD «EG30-근접» 을 뺀 목록을 넘긴다 · 명세 members_primary)."""
    import v_alloc as VA
    members = tuple(members or VA.MEMBERS5)
    fm = VA.l_fm(LL, members)
    ca = VA.l_allocator(LL, thetas_static, members=members, on=True, fm=fm, taus=taus)
    c0 = VA.l_allocator(LL, thetas_static, members=members, on=False, fm=fm, taus=taus)
    full = VA.l_allocator(LL, thetas_web, members=members, on=True, fm=fm, taus=taus)
    cw = VA.l_allocator(LL, thetas_web, members=members, on=False, fm=fm, taus=taus)
    X = {k: C.fund_x(a["arm"]["S"], a["arm"]["B"], a["arm"]["rate"], a["arm"]["tf"], a["arm"]["fixed"]) for k, a in
         (("C-A", ca), ("C0", c0), ("FULL", full), ("C-W", cw))}
    D = (X["C-A"] - X["C0"]).dropna()
    ok = fm["ok"]
    fa = LL.axis[np.flatnonzero(ok)[0]] if ok.any() else None
    win = (str(fa + 1), L_END) if fa is not None else None
    st = beta_adj_alpha(D, regs, win) if win else {"n": 0, "a": None, "t": None, "p": None}
    lc = beta_adj_alpha(D, regs, L_C)
    ranks = None
    if nperm and win and st["a"] is not None:
        rng = np.random.default_rng(seed)
        below = 0
        R0 = fm["R"].to_numpy(float)
        for _ in range(nperm):
            Rp = VA.block_shuffle_rows(R0, rng, min_finite=3)                     # FM 이 K_s ≥ 3 달부터 쌓는다(A4 검토 고침과 짝)
            fm2 = VA.l_fm(LL, members, R_override=Rp)
            ca2 = VA.l_allocator(LL, thetas_static, members=members, on=True, fm=fm2, taus=taus, R_override=Rp)
            X2 = C.fund_x(ca2["arm"]["S"], ca2["arm"]["B"], ca2["arm"]["rate"], ca2["arm"]["tf"], ca2["arm"]["fixed"])
            s2 = beta_adj_alpha((X2 - X["C0"]).dropna(), regs, win)
            if s2["a"] is not None and s2["a"] < st["a"]:
                below += 1
        ranks = below / float(nperm)
    thA = pd.Series(1.0, index=LL.axis)                                             # 배분기에는 θ 가 없다 — 반등 놓침은 «1/K 보다 줄인 구성원» 달이 아니라 보고만
    Xf = X["FULL"].loc[in_win(X["FULL"].index, *win)] if win else X["FULL"].iloc[:0]
    bd = bundle(Xf, full["arm"]["B"], ev) if len(Xf) else None
    X2x = C.fund_x(full["arm"]["S"], full["arm"]["B"], full["arm"]["rate"], full["arm"]["tf"], full["arm"]["fixed"], mult=2.0)
    variants = {"cost2x": float(X2x.loc[Xf.index].mean()) if len(Xf) else None, "sync": float(Xf[~sync_mask(Xf.index)].mean()) if len(Xf) else None}
    G = gates_w(bd, variants, turn=full["arm"]["turn_1w"], na=("t1",)) if bd else None
    rm = {"ok": True, "applies": False, "note": "배분기 — θ 경로 없음(반등 놓침 조건은 거미줄 카드에만)"}
    joint = bool(_pos(lc.get("a")) and ranks is not None and ranks >= RANK_MIN and rm["ok"])
    return {"alpha": st, "alpha_LC": lc, "placebo_rank": ranks, "joint": joint, "gates": G, "window": win, "delta": D, "X": X,
            "rebound_miss": rm}


# ══════════════════════════════════════════════════════════════════════════
#  합성 자료 시험
# ══════════════════════════════════════════════════════════════════════════
def _close(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol


def _st_stats():
    rng = np.random.default_rng(3)
    x = rng.normal(0.001, 0.01, 240)
    e = x - x.mean()
    s = e @ e / 240
    for L in range(1, 7):
        s += 2 * (1 - L / 7.0) * (e[L:] @ e[:-L]) / 240
    assert _close(nw_t(x), x.mean() / math.sqrt(s / 240), 1e-12)
    # Holm — 문턱 α/(m − k) 가 명세 z 표와 같다(한쪽 α 0.05 · m 6)
    from scipy.stats import norm
    zs = [float(norm.isf(HOLM_ALPHA / (6 - k))) for k in range(6)]
    assert all(abs(round(z, 3) - zz) <= 1e-3 for z, zz in zip(zs, HOLM_Z)), zs
    pv = {"a": 0.001, "b": 0.009, "c": 0.02, "d": 0.2, "e": 0.3, "f": None}
    h = holm(pv)
    assert h["reject"] == {"a": True, "b": True, "c": False, "d": False, "e": False, "f": False} and _close(h["threshold"]["c"], 0.05 / 4)
    h2 = holm({"a": 0.0001, "b": 0.0001, "c": 0.0001, "d": 0.0001, "e": 0.0001, "f": 0.04})
    assert all(h2["reject"].values())
    # 베타 조정 α — 합성: Δ = 0.002 + 0.1·MKT + 0.3·I_B·MKT − 0.2·I_B·I_U·MKT + e → 손 OLS · NW se
    idx = pd.period_range("1960-01", periods=600, freq="M")
    mkt = pd.Series(rng.normal(0.008, 0.045, 600), index=idx)
    rf = pd.Series(0.003, index=idx)
    R = dm_regressors(mkt, rf)
    ib = VC.ib24(mkt).shift(1)
    assert np.allclose(R["IB"].dropna(), ib.dropna())
    M, IB, IU = R["MKT"], R["IB"], R["IU"]
    D = 0.002 + 0.1 * M + 0.3 * IB * M - 0.2 * IB * IU * M + pd.Series(rng.normal(0, 0.004, 600), index=idx)
    st = beta_adj_alpha(D, R)
    df = pd.concat([D.rename("D"), R], axis=1).dropna()
    Xm = np.column_stack([np.ones(len(df)), df["MKT"], df["IB"] * df["MKT"], df["IB"] * df["IU"] * df["MKT"]])
    b = np.linalg.lstsq(Xm, df["D"].to_numpy(), rcond=None)[0]
    assert _close(st["a"], b[0], 1e-12) and np.allclose(st["coef"], b, atol=1e-12)
    u = df["D"].to_numpy() - Xm @ b
    Sm = np.zeros((4, 4))
    for l in range(0, 7):
        G = np.zeros((4, 4))
        for t in range(l, len(u)):
            G += np.outer(Xm[t] * u[t], Xm[t - l] * u[t - l])
        Sm += G if l == 0 else (1 - l / 7.0) * (G + G.T)
    inv = np.linalg.inv(Xm.T @ Xm)
    assert _close(st["se_a"], math.sqrt((inv @ Sm @ inv)[0, 0]), 1e-12)
    assert st["t"] > 2 and abs(st["coef"][2] - 0.3) < 0.05                                   # 베타 항을 빼고 알파를 회복
    pure_beta = 0.3 * IB * M                                                                  # 베타 타이밍만 → α ≈ 0
    stb = beta_adj_alpha(pure_beta, R)
    assert abs(stb["a"]) < 1e-12 and stb["t_raw"] is not None
    # BY · Stouffer · DSR 모양
    by = by_info({"a": 0.001, "b": 0.5})
    assert by["k"] == 1 and by["admitted"] == ["a"]
    so = stouffer({"a": 2.0, "b": 2.0}, {})
    assert _close(so["z"], 4.0 / math.sqrt(2.0))
    assert dsr(rng.normal(0.01, 0.02, 120), 963)["dsr"] is not None
    return "NW t(eg30plus 식) 손 계산 · Holm 문턱 = z 2.394 · 2.326 · 2.241 · 2.128 · 1.960 · 1.645 · 단계 하강 멈춤 · 베타 조정 α 손 OLS · NW(6) se · 베타 타이밍만 → α 0 · BY · Stouffer · DSR"


def _fake_events(idx, B):
    sig = float(np.std(B))
    Bs = pd.Series(B, index=idx)
    return Events("F", lambda i, _b=None: (Bs.reindex(i) < 0).to_numpy(), lambda i, _b=None: (Bs.reindex(i) <= -sig).to_numpy(),
                  lambda i, _b=None: (Bs.reindex(i) >= sig).to_numpy(), [{"side": "crash", "a": "2001-03-01", "b": "2001-09-30",
                                                                            "months": _months_between("2001-03-01", "2001-09-30")}],
                  [{"a": "2002-01-01", "b": "2002-04-30", "months": _months_between("2002-01-01", "2002-04-30")}], sig)


def _st_gates():
    idx = pd.period_range("2000-01", periods=120, freq="M")
    rng = np.random.default_rng(8)
    B = pd.Series(rng.normal(0.006, 0.045, 120), index=idx)
    ev = _fake_events(idx, B.to_numpy())
    X = pd.Series(0.0005 + 0.0 * B, index=idx)
    bd = bundle(X, B, ev)
    G = gates_w(bd, {"cost2x": 0.0004, "sync": 0.0005}, turn=4.0, na=("t1",))
    assert G["G2"]["ok"] and G["G3"]["ok"] and G["G5"]["ok"] and G["G6"]["a_ok"] and G["adopt_gates"]
    Xd = pd.Series(np.where(B < 0, -0.001, 0.002), index=idx)
    Gd = gates_w(bundle(Xd, B, ev), {"cost2x": 0.001, "sync": 0.001}, turn=4.0, na=("t1",))
    assert not Gd["G3"]["ok"] and not Gd["G2"]["ok"] and not Gd["adopt_gates"]              # 하락월 X < 0 → G3 거짓(모든 전략 같은 규칙)
    Gt = gates_w(bd, {"cost2x": 0.0004, "sync": 0.0005}, turn=10.5, na=("t1",))
    assert not Gt["G5"]["e_turn"] and not Gt["G5"]["ok"] and Gt["adopt_gates"]                # G5 는 보고(채택 관문은 G2 · G3 · G6a)
    yt = year_table(pd.Series(0.001, index=idx), B)
    assert yt["n_full"] == 10 and yt["won"] == 10 and _close(yt["rate"], 1.0)
    # 반등 놓침(V 규칙) — θ < θ0 뒤 3달 안 SURGE-M 셋 이상이면 평균 Δ ≥ 0
    th = pd.Series(0.75, index=idx)
    surge_months = [p for p, v in zip(idx, ev.surge(idx, B)) if v]
    for p in surge_months[:4]:
        th[p - 1] = 0.6
    dD = pd.Series(0.0, index=idx)
    for p in surge_months[:4]:
        dD[p] = -0.001
    rm = reb_miss_v(th, 0.75, dD, ev, B)
    assert rm["applies"] and rm["n"] >= 3 and not rm["ok"]
    rm2 = reb_miss_v(pd.Series(0.75, index=idx), 0.75, dD, ev, B)
    assert not rm2["applies"] and rm2["ok"]
    # FID
    yL = pd.Series(rng.normal(0, 0.02, 120), index=pd.period_range("2016-09", periods=120, freq="M"))
    assert fid(yL + rng.normal(0, 0.005, 120), yL)["gate"] and not fid(pd.Series(rng.normal(0, 0.02, 120), index=yL.index), yL)["gate"]
    # 채택 표시 — 진리표
    allt = {s: True for s in ADOPT_WEB}
    gl = {s: {"adopt_gates": True} for s in ADOPT_WEB}
    sr = {s: {"g5e": True} for s in ADOPT_WEB}
    am = adoption_marks(dict(allt, **{"V-A": True}), dict(allt, **{"V-A": True}), gl, sr, allt, allt, True,
                        alloc={"gates_L": {"adopt_gates": True}, "g5e": True})
    assert all(am[s]["adopt"] for s in ADOPT_WEB) and am["VFA"]["adopt"] and not am["V02"]["adopt"] and not am["V08"]["adopt"]
    am2 = adoption_marks(dict(allt, **{"V-A": True}), dict(allt, **{"V-A": True}), gl, sr, dict(allt, V03=False), allt, True,
                         alloc={"gates_L": {"adopt_gates": True}, "g5e": True})
    assert not am2["V03"]["adopt"] and am2["V01"]["adopt"]                                  # FID 실패 → LIQ 채택 차단
    am3 = adoption_marks(allt, allt, gl, sr, allt, allt, False)
    assert not any(am3[s]["adopt"] for s in ADOPT_WEB)                                       # 시총 앵커 실패 → 거미줄 단독 경로 모두 차단
    # 부 가족 — 전방 전용 V08 은 BY 에 들지 않는다(검토 고침)
    sf = secondary_family({"V01": {"p": 0.01}, "V08": {"p": 1e-9}}, {"X:V01": {"p": 0.02}, "X:V08": {"p": 1e-9}, "D:V01": {"p": 0.3}, "X:VFA": {"p": 0.2}})
    assert sf["m"] == 4 and sf["excluded"] == ["V08", "X:V08"] and not any("V08" in k for k in sf["admitted"])
    # S 주 행 = T+1(검토 고침) — h1_10 은 S_t1 · h1_d0 은 S
    Ps = pd.DataFrame({"S": 0.01, "S_t1": 0.02, "traded": 0.1, "rate": 0.001, "B": 0.005, "B_EW": 0.004, "beta": 1.0},
                      index=pd.period_range("2016-09", periods=24, freq="M"))
    st = s_tests(Ps, 2.0)
    assert _close(st["h1_10"]["mean"], C.fund_x(Ps["S_t1"], Ps["B"], Ps["rate"], Ps["traded"]).mean(), 1e-15)
    assert _close(st["h1_d0"]["mean"], C.fund_x(Ps["S"], Ps["B"], Ps["rate"], Ps["traded"]).mean(), 1e-15) and st["h1_10"]["mean"] > st["h1_d0"]["mean"]
    # L 하락월 = ^GSPC 월 가격수익 < 0(검토 고침) · ^GSPC 가 없는 달은 French TR — 두 계열이 반대 부호인 달로 가른다
    gd = pd.bdate_range("1927-12-01", "1928-06-29")
    gp = pd.Series(np.r_[np.linspace(100, 110, 42), np.linspace(110, 95, len(gd) - 42)], index=gd)
    fr = pd.Series(0.01, index=pd.period_range("1927-06", "1928-06", freq="M"))
    fr[pd.Period("1927-11", "M")] = -0.02
    evL = events_L(fr, 0.05, gp)
    ms = pd.period_range("1927-11", "1928-06", freq="M")
    dm = evL.down(ms)
    pr = gspc_month_pr(gp)
    assert bool(dm[0]) is True                                                                  # 1927-11: ^GSPC 없음 → French TR < 0
    assert all(bool(dm[j]) == bool(pr[p_] < 0) for j, p_ in enumerate(ms) if p_ in pr.index) and pr.min() < 0 and (fr.reindex(pr.index) > 0).all()
    return "관문(V 매개변수화): G2 양면 · G3 하락월 ≥ 0(모든 전략) · G5 보고 · G6a 해마다 · 반등 놓침(V 규칙 · ≥ 3 달) · FID ≥ 0.60 · 채택 진리표(FID · 앵커 차단 · LBS · INS · EAR · V08 없음) · BY 에 V08 없음 · S 주 행 T+1 · L 하락월 ^GSPC PR"


def _st_ff():
    idx = pd.period_range("2026-11", periods=40, freq="M")
    rng = np.random.default_rng(11)
    B = pd.Series(rng.normal(0.006, 0.05, 40), index=idx)
    ev = _fake_events(idx, B.to_numpy())
    X = pd.Series(0.002 + 0.0005 * np.sign(B), index=idx)
    Xf, nl = ff_late_fill(X, X * 0.0, pd.Series([True, False] * 20, index=idx))
    assert nl == 18 and (Xf.iloc[::2] == 0).all() and (Xf.iloc[1::2] == X.iloc[1::2]).all()
    r1 = ff1(pd.Series(-0.001 + rng.normal(0, 0.0005, 30), index=idx[:30]))
    assert r1["due"] and r1["rejected"] and not ff1(X.iloc[:10])["due"]
    regs = dm_regressors(pd.concat([pd.Series(rng.normal(0.008, 0.045, 30), index=pd.period_range("2024-05", periods=30, freq="M")), B]),
                         pd.Series(0.003, index=pd.period_range("2024-05", periods=70, freq="M")))
    r2 = ff2(X, X, regs, ev, B, H=X, X20=X, Xd0=X, turn=3.0, kind="N")
    assert r2["due"] and set(r2["conds"]) == {"a", "b", "c", "d", "e", "f", "g", "events", "late_ok"} and r2["conds"]["g"] is True
    assert not ff2(X.iloc[:20], X.iloc[:20], regs, ev, B)["due"]
    r3 = ff2(X, X, regs, ev, B, H=X, X20=X, Xd0=X, turn=3.0, v=pd.Series(0.0, index=idx), kind="W", n_late=3)
    assert not r3["conds"]["late_ok"] and not r3["conds"]["g"] and not r3["pass"]
    return "VFWD 관문(얼림): FF0 늦은 달 채움 · 첫 36개월 늦음 셈 · FF1 NW t ≤ −1 기각 · 24개월 전 판정 없음 · FF2 (a)~(g) · 사건 최소 · 늦음 ≥ 3 막힘 · VF08S (g) 해당 없음"


def _st_l_eval():
    import v_cards as VK
    rng = np.random.default_rng(5)
    axis = pd.period_range(VK.L_AXIS[0], VK.L_AXIS[1], freq="M")
    zL = pd.DataFrame({c: np.clip(rng.normal(0, 1, len(axis)), -2, 2) for c in VC.CONDS}, index=axis)
    zL.iloc[:60] = np.nan
    mkt = pd.Series(rng.normal(0.008, 0.045, len(axis)), index=axis)
    prox = {}
    for s in VD.L_PROXIES:
        y = rng.normal(0.0, 0.02, len(axis))
        prox[s] = pd.Series(y, index=axis)
    y = prox["V01"].to_numpy().copy()
    y[1:] += 0.01 * np.nan_to_num(zL["SLOW"].to_numpy()[:-1])
    prox["V01"] = pd.Series(y, index=axis)
    st = {"SLOW": {"status": "primary"}, "DISP": {"status": "twin"}, "BSPRD": {"status": "primary"}, "VSPRD": {"status": "primary"},
          "RVAR": {"status": "primary"}, "PANICX": {"status": "twin"}, "MKT3": {"status": "twin"}, "G2own": {"status": "primary"}}
    LL = VK.LLayer(zL, prox, mkt, pd.Series(0.003, index=axis), clusters=VK.l_clusters(zL), lit_status=st)
    regs = dm_regressors(mkt, pd.Series(0.003, index=axis))
    ev = _fake_events(axis, mkt.to_numpy())
    r = l_card_eval(LL, "V01", ev, regs, tau=2.0, nperm=8)
    assert r["alpha"]["n"] > 500 and r["placebo_rank"] is not None and 0 <= r["placebo_rank"] <= 1 and r["gates"] is not None
    assert r["alpha"]["t"] is not None and r["alpha"]["a"] > 0                                  # 합성 신호(SLOW → +)가 W − S0 에 잡힌다
    th_s = {s: pd.Series(VK.CARDS[s]["theta0"], index=axis) for s in VD.L_PROXIES}
    ra = l_alloc_eval(LL, ev, regs, th_s, th_s, nperm=3)
    assert ra["alpha"]["n"] > 100 and ra["placebo_rank"] is not None
    return "L 평가(합성): W − S0 Δ · 베타 조정 α(L-R · L-C) · 위약(달 블록째 · 순위) · 반등 놓침 · W 관문 · 배분기 Δ_A(C-A − C0) · 위약"


def _st_static():
    with io.open(os.path.abspath(__file__), encoding="utf-8") as f:
        assert not C.open_violations(f.read())
    assert NPERM >= NPERM_MIN
    return "open() encoding · NPERM ≥ 1000(굽기 기본)"


def selftest():
    res, ok = [], True
    for fn in (_st_stats, _st_gates, _st_ff, _st_l_eval, _st_static):
        t0 = time.time()
        try:
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                res.append(("통과", fn.__name__, fn(), round(time.time() - t0, 1)))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-2500:], round(time.time() - t0, 1)))
    for st, nm, msg, sec in res:
        print("  %s %-12s %5ss  %s" % ("✓" if st == "통과" else "✗", nm, sec, msg))
    print("v_tests selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기 — 실자료 끝까지(L 평가 · S 카드 · 배분기 · 검정 · 채택 표시) · 산출은 열지 않고 지운다
# ══════════════════════════════════════════════════════════════════════════
def blind_smoke(nperm=3, twins=False):
    """🚨 산출(수익 통계 포함)을 저장소 밖 임시 폴더에 pickle 로 쓰고 열지 않고 지운다 · 찍는 것은 단계별 참/거짓 · 초 · 모양(구조 참/거짓)뿐."""
    import v_guard as VG
    import v_cards as VK
    import v_alloc as VA
    VG.install_open_audit()
    td = os.path.join(VD.cache_guard(), "_vb_smoke_tests")
    os.makedirs(td, exist_ok=True)
    out, box = {}, {}

    def dump(name, obj):
        pd.to_pickle(obj, os.path.join(td, name + ".pkl"))

    def s0():
        box["Lr"] = VD.Layer.real()
        box["cl"] = VK.l_clusters(box["Lr"].cond_L())
        box["LL"] = VK.LLayer.real(box["Lr"], clusters=box["cl"])
        f3 = VD.ff3("m")
        box["regsL"] = dm_regressors(f3["Mkt"], f3["RF"])
        box["evL"] = events_L(f3["Mkt"], sigma_L(f3["Mkt"]), gspc_daily())
        box["evS"] = events_S()
        return {"clusters_global": len(set(box["cl"]["global"].values())), "edges": len(box["cl"]["edges"]), "legs": len(box["evL"].legs) > 50}
    out["setup(data · L · 사건)"] = VD.blind_smoke(s0)
    if "LL" not in box:
        return out
    Lr, LL = box["Lr"], box["LL"]
    SL = VK.SLayer(Lr, clusters=box["cl"])
    box["SL"] = SL
    comps = {}

    def s_cards():
        shp = {}
        for sid in VK.CARD_IDS:
            sp = VK.spec_of(sid)
            Lw = LL.web_slopes(sp) if sp["web"] else None
            r = VK.s_card_arms(SL, sp, Lw, keep_books=True)
            comps[sid] = r
            shp[sid] = all(len(p) >= 140 for p in r["paths"].values())
        return all(shp.values())
    out["S cards V01..V08"] = VD.blind_smoke(s_cards)
    taus = {sid: comps[sid]["tau_w"].get("F") for sid in comps} if comps else {}
    LL.taus = taus
    Lres = {}

    def l_eval():
        for sid in VK.WEB_CARDS:
            Lres[sid] = l_card_eval(LL, sid, box["evL"], box["regsL"], tau=taus.get(sid), nperm=nperm)
        th_s = {s: pd.Series(VK.CARDS[s]["theta0"], index=LL.axis) for s in VA.MEMBERS5}
        th_w = {s: LL.theta(VK.spec_of(s), LL.web(VK.spec_of(s))["v"]) for s in VA.MEMBERS5}
        Lres["V-A"] = l_alloc_eval(LL, box["evL"], box["regsL"], th_s, th_w, taus=taus, nperm=nperm)
        dump("L_eval", Lres)
        return all(Lres[k]["alpha"]["n"] > 100 for k in Lres)
    out["L eval(Δ · α · 위약 %d)" % nperm] = VD.blind_smoke(l_eval)

    def l_twins():
        tw = {}
        for t, d in VK.TWINS.items():
            sp = VK.spec_of(d["card"], t)
            if sp["status"] != "built" or "L" not in sp["layers"]:
                continue
            tw[t] = l_card_eval(LL, d["card"], box["evL"], box["regsL"], tau=taus.get(d["card"]), nperm=0, twin=t)
        dump("L_twins", tw)
        return len(tw) >= 6 and all(v["alpha"]["n"] > 100 or v["window"] is None for v in tw.values())
    out["L twins(보고 · 위약 없음)"] = VD.blind_smoke(l_twins)
    Sres, Ares = {}, {}

    rfm = VD.lab_rf_monthly()

    def s_eval():
        for sid in VK.CARD_IDS:
            if sid not in comps:
                continue
            P = comps[sid]["paths"].get("W") if "W" in comps[sid]["paths"] else comps[sid]["paths"]["S0"]
            turn = C.turnover_annual(P.loc[in_win(P.index, *S_WIN)]["traded"].tolist())
            yL = LL.P.get(sid)
            Sres[sid] = s_tests(P, turn, comps[sid]["y_S"], yL, sid, rf=rfm, ev=box["evS"])
        dump("S_eval", Sres)
        return len(Sres) == len(VK.CARD_IDS)
    out["S eval(구현성 · FID)"] = VD.blind_smoke(s_eval)

    def alloc_s():
        fmL = VA.l_fm(LL)
        fmL_ns = VA.l_fm(LL, shrink=False)                                     # C-NoShrink — 배분기 FM 도 축소를 뺀다(검토 고침)
        for arm, (on, web, wopt, beta_net, members, cap80) in VA.ARM_DEF.items():
            cs = comps
            if wopt or cap80 or members != VA.MEMBERS5:
                cs = dict(comps)
                for sid in members:
                    if sid not in VA.MEMBERS5:
                        continue
                    sp = VK.spec_of(sid, ("T-%s-CAP80" % VK.CARDS[sid]["key"]) if cap80 else None)
                    Lw = LL.web_slopes(sp, shrink=wopt.get("shrink", True))
                    cs[sid] = VK.s_card_arms(SL, sp, Lw, web_opt=wopt, keep_books=True, paths=False)
            Ares[arm] = VA.s_allocator(SL, cs, members, on=on, fm_L=(fmL_ns if wopt.get("shrink") is False else fmL), beta_net=beta_net, cap80=cap80,
                                       arm_key=("W" if web else "S0"))
        dump("S_alloc", {k: {"path": v["path"], "w": v["w"]} for k, v in Ares.items()})
        return all(v["path"] is not None and len(v["path"]) >= 140 for v in Ares.values())
    out["S allocator arms(10)"] = VD.blind_smoke(alloc_s)

    def final():
        hv = hv_family({k: Lres[k]["alpha"] for k in Lres})
        gL = {k: Lres[k]["gates"] for k in Lres if k != "V-A"}
        joint = {k: Lres[k]["joint"] for k in Lres}
        fidg = {k: (Sres.get(k) or {}).get("fid", {}) and (Sres[k]["fid"] or {}).get("gate") for k in VK.WEB_CARDS}
        full = Ares.get("FULL")
        g5e_alloc = None
        if full and full["path"] is not None:
            g5e_alloc = C.turnover_annual(full["path"].loc[in_win(full["path"].index, *S_WIN)]["traded"].tolist())
        am = adoption_marks({k: hv["holm"]["reject"][k] for k in H_V}, joint, gL, Sres, fidg, {k: None for k in VK.WEB_CARDS}, None,
                            alloc={"gates_L": Lres["V-A"]["gates"], "g5e": (g5e_alloc is not None and g5e_alloc <= TURN_MAX)})
        dump("final", {"hv": hv, "adopt": am})
        return len(hv["members"]) == 6 and set(am) >= set(ADOPT_WEB) | {"VFA", "V08"}
    out["H_V Holm · 채택 표시(모양)"] = VD.blind_smoke(final)

    def f0_weights():
        mS = [m for m in SL.months if m >= VK.S_ARM_FROM]
        sc = []
        for m in mS:
            X = SL.cross(m)
            A = []
            for sid in VA.MEMBERS5:
                b = (comps.get(sid) or {}).get("books", {}).get("F", {}).get(m)
                if b is None:
                    break
                A.append(X.arr(b) - X.wB)
            if len(A) == 5:
                sc.append(C.common_share(np.vstack(A)))
        e = VK.spec_of("V03")
        b8, _ = SL.books(e, theta=0.8)
        tau08 = C.tau_weights_only([b8.get(m) for m in mS])
        dump("f0_weights", {"g_common_median": float(np.median(sc)) if sc else None, "liq_tau08": tau08})
        return len(sc) > 100 and tau08 is not None
    out["F0 비중만(G-COMMON · LIQ τ(0.8))"] = VD.blind_smoke(f0_weights)

    def f0_cov():
        rows, dec = VK.f0_signal_coverage(SL)
        dump("f0_cov", {"rows": rows, "dec": dec})
        return len(rows) >= 119 and set(dec) >= {"use_sp", "prof"}
    out["F0 신호 커버리지(S/P · OP 결정)"] = VD.blind_smoke(f0_cov)

    def cmp_export():
        p = os.path.join(VD.cache_guard(), "_vb_smoke_cmp", "vb_books.json.gz")
        VK.export_for_cmp(SL, {k: v for k, v in comps.items()}, p)
        return os.path.exists(p)
    out["G-EGD 넘김 파일(v_cmp 연기용 · 따로 지운다)"] = VD.blind_smoke(cmp_export)
    shutil.rmtree(td, ignore_errors=True)                               # 열지 않고 지운다
    rt, oa, st = VG.runtime_check(), VG.open_audit_check(), VG.noeg_static()
    out["G-NoEG runtime"] = {"ok": rt["ok"], "sec": 0, "shape": rt, "err": None}
    out["G-NoEG open audit"] = {"ok": oa["ok"], "sec": 0, "shape": {"n_opened": oa["n_opened"], "eg": oa["eg_files_opened"]}, "err": None}
    out["G-NoEG static"] = {"ok": st["ok"], "sec": 0, "shape": {"n_reached": st["n_reached"], "hits": st["hits"], "sep": st["separate_violations"]}, "err": None}
    out["outputs deleted unread"] = {"ok": not os.path.exists(td), "sec": 0, "shape": {"dir_exists": os.path.exists(td)}, "err": None}
    return out


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--blind-smoke" in sys.argv:
        n = int(sys.argv[sys.argv.index("--nperm") + 1]) if "--nperm" in sys.argv else 3
        res = blind_smoke(nperm=n)
        for k, v in res.items():
            sh = json.dumps(v.get("shape"), ensure_ascii=False, default=str)
            print("  %s %-34s %7ss %s" % ("✓" if v["ok"] else "✗", k, v["sec"], (sh[:200] if v["ok"] else v["err"])))
        print("연기 %d/%d 참" % (sum(1 for v in res.values() if v["ok"]), len(res)))
        raise SystemExit(0 if all(v["ok"] for v in res.values()) else 1)
    print(__doc__)
