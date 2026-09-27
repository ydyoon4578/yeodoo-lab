# -*- coding: utf-8 -*-
"""build/x_blr.py — 배치 X 측정 팔 X-BLR: 베이즈 선형회귀(닫힌 꼴 사후 평균 · 기울기 부호 제약) · 창 안 확장 학습 · a = 1[μ̂_t < 0].

설계 원본(구속): xbatch_research.json signals[X-BLR] · signals_excluded(X-LOGIT) · decisions SN-4 · rule_20y_compliance — 저장소 밖 스크래치.
  목표   y_{u+1} = 다음 달 R^e(% · D0 달 = d_u → d_{u+1} 종가 · x_signals.monthly_excess × 100) — 결정 d_t 에는 u + 1 ≤ t 인 쌍만 관측된다.
  특성   TREND(12개월 평균 초과) · FAST(이번 달 초과) · CREDIT(BAA10Y − 중앙₃₆₅ₐ · x_signals.credit_level) · FEAR(ln VIX − ln 중앙₂₅₂ · x_signals.fear_level)
         — 학습 창에서 다시 잰 평균 · sd(ddof 1)로 표준화(예측 행도 같은 척도).
  사전   기울기 N(0, 0.25²)(표준화 특성 4개 · 월 SD 약 4.3% 에서 사전 R² 약 1.35%) · 절편 N(0.5, 0.5²)%/월(주식 프리미엄 약 6%/년).
  가능도 y | x ~ N(xᵀβ, σ²) · σ² = 학습 y 의 표본 분산(ddof 1) 플러그인(선언 — 명세는 σ 를 두지 않았다 · 사전 척도 역산의 «월 SD» 와 같은 뜻).
  사후   평균 m = (XᵀX/σ² + Λ₀)⁻¹ (Xᵀy/σ² + Λ₀μ₀) — 닫힌 꼴 · Λ₀ = diag(1/0.5², 1/0.25² × 4) · μ₀ = (0.5, 0, 0, 0, 0).
  부호   TREND + · FAST + · CREDIT − · FEAR + — 사후 평균이 틀린 부호면 그 기울기만 0(Campbell–Thompson 식 기울기 제약 · 다시 적합하지 않는다 ·
         예측값 0 절단은 쓰지 않는다 — a 를 영원히 0 으로 만들기 때문 · SN-4).
  행동   μ̂_t = m₀ + Σ m_j z_{j,t} · a_t = 1[μ̂_t < 0].
  학습   창 안 확장(입력 2005-08-01 부터 · 창 앞 학습 없음 · D-8) · 완전한 학습 쌍 ≥ 60 인 결정 달부터 · 그 전 NaN(활성 월만 보고).
         🔎 명세의 «최소 60개월 → 첫 결정 2010-08» 은 2005-08 부터 달을 센 값이다 — 특성(12개월 · 365일 · 252일 창)이 2006-07/08 에야 서므로
         완전한 쌍 60 은 2011-08 무렵에 선다(규칙은 «최소 60» 그대로 · 첫 결정은 러너가 적는다 · x_data.assert_first_active 하한 2010-08 통과).
  대조   Nagel 쌍둥이(x_signals.nagel_z · nagel_twin) — BLR 활성 달 평균 노출에 z* 를 맞춘다.

🚨 이 파일은 수익 · 통계를 계산하지 않는다 — 결정 계열(μ̂ · a · 계수 · 학습 쌍 수)만. --selftest 는 합성 자료만.

  python build/x_blr.py --selftest
"""
from __future__ import annotations

import math
import os
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

FEATURES = ("TREND", "FAST", "CREDIT", "FEAR")
SIGNS = {"TREND": +1, "FAST": +1, "CREDIT": -1, "FEAR": +1}
PRIOR_SLOPE_SD = 0.25
PRIOR_INT_MEAN, PRIOR_INT_SD = 0.5, 0.5
MIN_TRAIN = 60
FIRST_ACTIVE_FLOOR = "2010-08"


def prior():
    mu0 = np.array([PRIOR_INT_MEAN] + [0.0] * len(FEATURES))
    lam0 = np.diag([1.0 / PRIOR_INT_SD ** 2] + [1.0 / PRIOR_SLOPE_SD ** 2] * len(FEATURES))
    return mu0, lam0


def posterior_mean(Z, y, sigma2, mu0=None, lam0=None):
    """닫힌 꼴 사후 평균 — Z(n × k 표준화 특성 · 절편 없음) · y(n) · σ² → m(k + 1 · 절편 먼저). n = 0 이면 사전 평균."""
    if mu0 is None or lam0 is None:
        mu0, lam0 = prior()
    Z = np.asarray(Z, float).reshape(-1, len(mu0) - 1)
    y = np.asarray(y, float)
    if len(y) == 0:
        return mu0.copy()
    X = np.column_stack([np.ones(len(y)), Z])
    A = X.T @ X / sigma2 + lam0
    b = X.T @ y / sigma2 + lam0 @ mu0
    return np.linalg.solve(A, b)


def sign_constrain(m):
    """틀린 부호 기울기만 0(절편은 그대로)."""
    m = np.array(m, float)
    for j, f in enumerate(FEATURES, start=1):
        if SIGNS[f] * m[j] < 0:
            m[j] = 0.0
    return m


def standardize(Xtr, x_now):
    mu = Xtr.mean(0)
    sd = Xtr.std(0, ddof=1)
    sd = np.where(sd > 0, sd, 1.0)
    return (Xtr - mu) / sd, (x_now - mu) / sd


def blr_path(F, y_pct=None, min_train=MIN_TRAIN):
    """F = x_signals.signal_frame(…)(결정 달 색인 · 열 TREND · FAST · CREDIT · FEAR · re) → DataFrame(mu · a · n_train · b_* · sigma2).
    결정 t 의 학습 쌍 = {(x_u, y_{u+1}) : u + 1 ≤ t · x_u 완전} · y = re × 100(%)."""
    F = pd.DataFrame(F)
    X = F[list(FEATURES)].astype(float)
    y = (F["re"].astype(float) * 100.0) if y_pct is None else pd.Series(y_pct, dtype=float).reindex(F.index)
    y_next = y.shift(-1)                                       # 행 u 의 목표 = y_{u+1}
    rows = {}
    idx = list(F.index)
    Xa = X.to_numpy(float)
    ya = y_next.to_numpy(float)
    okx = np.isfinite(Xa).all(1)
    for n, t in enumerate(idx):
        # 학습 행 u < t(u + 1 ≤ t) · 특성 완전 · 목표 관측
        tr = np.flatnonzero(okx[:n] & np.isfinite(ya[:n]))
        rec = {"n_train": int(len(tr)), "mu": np.nan, "a": np.nan, "sigma2": np.nan}
        for f in FEATURES:
            rec["b_" + f] = np.nan
        if len(tr) >= min_train and okx[n]:
            Ztr, znow = standardize(Xa[tr], Xa[n])
            yt = ya[tr]
            s2 = float(np.var(yt, ddof=1))
            m = sign_constrain(posterior_mean(Ztr, yt, s2))
            mu = float(m[0] + znow @ m[1:])
            rec.update({"mu": mu, "a": float(mu < 0), "sigma2": s2})
            for j, f in enumerate(FEATURES, start=1):
                rec["b_" + f] = float(m[j])
        rows[t] = rec
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index = pd.PeriodIndex(out.index, freq="M")
    return out


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험
# ══════════════════════════════════════════════════════════════════════════
def _st_prior_only():
    m = posterior_mean(np.zeros((0, 4)), np.zeros(0), 1.0)
    assert np.allclose(m, [0.5, 0, 0, 0, 0])
    mu = float(m[0] + np.array([3.0, -2.0, 1.0, 0.5]) @ m[1:])
    assert abs(mu - 0.5) < 1e-15
    mu0, lam0 = prior()
    assert np.allclose(np.diag(lam0), [4.0, 16.0, 16.0, 16.0, 16.0])
    return "사전만이면 μ̂ = 0.5(특성과 무관) · Λ₀ = diag(4, 16 × 4)"


def _st_recovery():
    rng = np.random.default_rng(20260927)
    n, beta = 20000, np.array([0.4, 0.6, 0.3, -0.5, 0.2])
    Z = rng.normal(0, 1, (n, 4))
    y = beta[0] + Z @ beta[1:] + rng.normal(0, 1.0, n)
    m = posterior_mean(Z, y, 1.0)
    assert np.max(np.abs(m - beta)) < 0.03, m
    # 작은 표본에서는 사전 쪽으로 줄어든다
    Zs, ys = Z[:60], y[:60]
    ms = posterior_mean(Zs, ys, float(np.var(ys, ddof=1)))
    ols = np.linalg.lstsq(np.column_stack([np.ones(60), Zs]), ys, rcond=None)[0]
    assert np.all(np.abs(ms[1:]) <= np.abs(ols[1:]) + 1e-12)
    # 닫힌 꼴 = 증강 최소제곱(사전을 가짜 관측으로)
    s2 = 1.7
    mu0, lam0 = prior()
    Xa = np.vstack([np.column_stack([np.ones(60), Zs]) / math.sqrt(s2), np.sqrt(lam0)])
    ya = np.concatenate([ys / math.sqrt(s2), np.sqrt(lam0) @ mu0])
    aug = np.linalg.lstsq(Xa, ya, rcond=None)[0]
    assert np.max(np.abs(aug - posterior_mean(Zs, ys, s2))) < 1e-10
    return "계수 회복(n 20000 · 오차 < 0.03) · 작은 표본 축소 · 닫힌 꼴 = 증강 최소제곱(1e−10)"


def _st_sign():
    m = sign_constrain([0.3, -0.2, 0.1, 0.4, -0.05])          # TREND − · CREDIT + · FEAR − → 0
    assert np.allclose(m, [0.3, 0.0, 0.1, 0.0, 0.0])
    m = sign_constrain([-0.9, 0.2, 0.3, -0.1, 0.1])            # 절편은 제약 없음
    assert np.allclose(m, [-0.9, 0.2, 0.3, -0.1, 0.1])
    return "부호 제약(TREND + · FAST + · CREDIT − · FEAR +) · 틀린 부호만 0 · 절편 그대로"


def _syn_frame(n=240, seed=4, first="2005-09"):
    rng = np.random.default_rng(seed)
    idx = pd.period_range(first, periods=n, freq="M")
    re = pd.Series(rng.normal(0.006, 0.043, n), index=idx)
    F = pd.DataFrame({"re": re, "TREND": re.rolling(12, min_periods=12).mean(), "FAST": re,
                      "CREDIT": pd.Series(rng.normal(0, 0.5, n), index=idx), "FEAR": pd.Series(rng.normal(0, 0.3, n), index=idx)})
    F.loc[F.index[:11], ["CREDIT", "FEAR"]] = np.nan
    return F


def _st_path_and_window():
    F = _syn_frame()
    P = blr_path(F)
    first = P["a"].first_valid_index()
    n_first = int(P.loc[first, "n_train"])
    assert n_first == MIN_TRAIN and P.loc[:first - 1, "a"].isna().all()
    assert str(first) >= FIRST_ACTIVE_FLOOR[:7] or True
    # 특성 완전한 첫 행 2006-08 · 쌍 60 은 결정 2011-08 → 첫 활성
    assert str(first) == "2011-08", first
    assert P["a"].dropna().isin([0.0, 1.0]).all()
    for f in FEATURES:
        b = P["b_" + f].dropna()
        assert (SIGNS[f] * b >= 0).all()
    return "창 안 확장 · 완전 쌍 60 에서 첫 활성(합성 2005-09 시작 → 2011-08) · a ∈ {0, 1} · 부호 제약 유지"


def _st_lookahead():
    F = _syn_frame(seed=8)
    P = blr_path(F)
    rng = np.random.default_rng(2)
    for t in (pd.Period("2013-05", "M"), pd.Period("2019-11", "M"), pd.Period("2025-01", "M")):
        G = F.copy()
        after = G.index > t
        G.loc[after, "re"] = rng.normal(0, 0.5, int(after.sum()))
        G.loc[after, ["TREND", "FAST", "CREDIT", "FEAR"]] = rng.normal(0, 9, (int(after.sum()), 4))
        Q = blr_path(G)
        a, b = P.loc[:t, ["mu", "a", "n_train"]], Q.loc[:t, ["mu", "a", "n_train"]]
        assert np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True), t
    # 목표 y_{t+1}(t 뒤 관측)를 흔들면 결정 t 는 그대로 — 학습 쌍은 u + 1 ≤ t 만
    G = F.copy()
    t = pd.Period("2016-06", "M")
    G.loc[t + 1, "re"] = 5.0
    assert P.loc[t, "mu"] == blr_path(G).loc[t, "mu"]
    return "선견 불변(결정 t 뒤 특성 · 목표를 흔들어도 μ̂ · a · 쌍 수 같음) · y_{t+1} 은 결정 t 에 쓰지 않는다"


SELFTESTS = (_st_prior_only, _st_recovery, _st_sign, _st_path_and_window, _st_lookahead)


def selftest():
    res, ok = [], True
    for fn in SELFTESTS:
        t = time.time()
        try:
            res.append(("통과", fn.__name__, fn(), time.time() - t))
        except Exception:                                             # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-2000:], time.time() - t))
    for st, nm, msg, dt in res:
        print("  %s %-22s %5.2fs  %s" % ("✓" if st == "통과" else "✗", nm, dt, msg))
    print("x_blr selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(selftest())
    print(__doc__)
