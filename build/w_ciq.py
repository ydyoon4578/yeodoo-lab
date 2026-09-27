# -*- coding: utf-8 -*-
"""build/w_ciq.py — 배치 W 카드 W04 CIQ-LT(하방 공통 고유분위 요인 노출 + 꼬리 악화 뒤 연속 θ) — 등록 A 확증 가족 카드(갱신 나 — 오케스트레이터 결정).

설계 원본(구속): wbatch_research.json final.slate.strategies[W04] · build_plan.modules[w_qfa](과제 지시로 이 파일 이름) · D18 · G_NoEG_inputs ·
  사용자 갱신(2026-09-27): 전방 원장 없음 · 등록 A 가족 {W01 · W04 · W10m} 한쪽 Holm α 0.05 — W04 의 Tier-1 주 통계 방향 +1(w_core.CARD_DIRECTION).

근본 이유(명세 fundamental_reason): 중개자의 위험 감당 능력이 손상되면 매도 쪽 유동성이 마르고 종목들의 하방 꼬리가 함께 두꺼워진다. 그때 꼬리위험의 가격이
  오르고, 공통 하방 꼬리에 노출된 종목의 이후 기대수익이 높다(He–Krishnamurthy · Brunnermeier–Sannikov 중개자 자본).
출처: Barunik · Nevrla «Common Idiosyncratic Quantile Factors and Asset Prices» arXiv 2208.14267 v5 [직접] — CIQLT = CIQ(τ 0.2) · 60개월 롤링 ·
  창 안 FF3 잔차 · 창 안 SD 표준화 · 48개월 이상 · $1 미만 제외 · 높은 쪽이 연 7~8% 앞섬 · 시계열 1σ 하락 → 다음 달 시장 초과 연 +5.49%p(스카우트) ·
  Chen · Dolado · Gonzalo (2021) 분위 요인분석. 🔎 등록 전 확인(open_before_register): QFA 절편 유무 · 표 12 칸 수치.

규칙(명세 base · 지금 고정 · 초모수 없음 — τ 0.2 · 60 · 48 원문값)
  잔차: 결정 달 m 마다 60개월 월간 초과수익을 랩 자체 MKT(합집합 시총가중) + SMB(분할만 조정 ME 중앙값 분할 VW 차)에 회귀한 잔차 —
    🚨 가치 요인은 B/M 입력이라 뺐다(G-NoEG 입력 단위 · 원전 FF3 에서 이탈 공개) · 창 안 SD 로 표준화.
  QFA: τ = 0.2 · 1요인 · 교대 추정 — 각 단계가 스칼라 계수 분위회귀(절편 없음 — 창 안 표준화 뒤)라 «일반화 가중 분위수» 로 정확한 O(n log n) 해:
    ρ_τ(y − b x) = |x|·ρ_{τ′}(y/x − b) · τ′ = τ(x > 0) 또는 1 − τ(x < 0) → b* = c_j = y_j/x_j 를 정렬해 누적 |x| 가 Σ|x_j|τ′_j 에 처음 닿는 c.
    IRLS 대신 이 정확해 · 결정적 · 초기값 = 첫 주성분 · 상대 목적 변화 < 1e−6 · 최대 200 · selftest 에서 3달을 HiGHS LP 로 교차 확인.
  부호 규칙: corr(CIQLT_t, 그달 표준화 잔차의 단면 20분위) > 0 — «높을수록 하방 꼬리 양호».
  혁신: 창 안 1차 차분 ΔCIQLT · 상태 변수 z_t = 최신 창의 마지막 달 ΔCIQLT 를 확장창 SD 로 표준화.
  노출: β^CIQ_i = 창 안 회귀 r_i − rf = a + b_M·MKT + b·ΔCIQLT + e 의 b(48개월 이상).
  첫 창: 2009-01~2013-12(자료 격자 첫 월수익 2009-02 · 2014-06 앞은 S-E 명단 역적용 공개).
  슬리브: β^CIQ 상위 30% · θ0 0.5(위험 프리미엄 카드라 능동 예산을 낮춘다) · 나머지 기본값(w_cards.sleeve_target).
  C 팔(연속 θ 사상 · 고정 기울기 · 추정 없음): θ_t = 0.5 + 0.25·clip(−z_t, −2, 2) ∈ [0, 1] — 꼬리가 나빠질수록(z < 0) 노출을 싣고 좋아지면 줄인다 ·
    V 의 |Δθ| ≤ 0.10 면제(다음 달 효과라 늦추면 기전이 사라진다 · 점프 비용은 계산에 넣는다).
  주 통계: z(β^CIQ) 의 FM γ · Stage M-W + 시장베타 + b_dn(x-dnbeta 정의) + 코퓰러 LTD 통제 · NW(3) · H1 γ > 0 ·
    🚨 b_dn · LTD 를 넣어 γ 가 절반 넘게 줄면 «DNBETA 재포장» 주의 칸(w_core K5 — 표시를 바꾸지 않는 주의).
  시계열 측정(보고): 다음 달 S&P 초과수익 ~ −ΔCIQLT 의 NW(6) · 확장창 표본 밖 R²(Campbell–Thompson).
  C 팔 주 대비: 시장베타 상위 30% 책에 같은 θ 경로 · CIQ 상태 라벨 12개월 블록 섞기 1,000회 · Nagel 대조군. 쌍둥이: CAPM 잔차판(MKT 만).
  IC_lit 0.016 · σ 범주 0.092 → P0 0.044(σ 0.047 이면 0.141) [합성 · 기록만].

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  Q1 정확해의 동률: 누적 |x| 가 Σ|x|τ′ 와 정확히 같으면 그 c(구간 [c_(k), c_(k+1)] 전체가 최적 — 가장 작은 끝) · x = 0 항은 상수라 뺀다 · 결측은 뺀다.
  Q2 QFA 정규화: 매 교대 뒤 (1/T)Σf² = 1(λ 반대 척도 · 목적 불변) · 초기 f = 결측을 0 으로 채운 행렬의 첫 좌특이벡터 · 수렴 못 한 창은 노출 결측(F0 허용 결정).
  Q3 z_t = d_t / SD(d_{≤t})(평균을 빼지 않는다 — 명세 «SD 로 표준화» · 차분의 평균 ≈ 0) · 관측 < 12 이면 z = 0(θ = 0.5).
  Q4 MKT · SMB(보유월 τ): 명단 = 결정 달 τ−1 의 합집합(시총이 선 이름) · 가중 = τ−1 말 분할만 조정 ME · 수익 = v_pit.hold_ret(τ−1)(y_stop) ·
     SMB = 중앙값 아래 VW − 위 VW · 초과수익 = r − rf(랩 rf_monthly) · 창의 종목 수익 = 월말 수정종가 비(v_pit.Pm) · $1 규칙은 원 종가(V-D1 · 사내 DB)가 선 이름만.
  Q5 b_dn(x-dnbeta 정의 그대로): 252 거래일 일간 로그수익 · 시장 = S&P 500 가격지수(data/bench_px.json) · 시장 < 창 평균인 날만의 Cov/Var · 그런 날 < 20% 면 결측.
  Q6 LTD — 🚨 명세는 «코퓰러 LTD(Q07 정의)» 다. Q07 주 추정기(64 혼합 코퓰러 최우 · 적분 AD 거리)는 단위 3,688 에 5 일꾼 3,820초였다 — W04 통제는
     약 500 이름 × 150 달 = 7.5만 단위(≈ 2 일꾼 40 시간 · 이 PC 의 다른 무거운 작업과 겹친다)라 굽기 예산 밖이다. 그래서 Q07 이 정의한 비모수 팔(A3)
     Ĉ(u,u)/u(u = 0.05 · 252일 · 유효 짝 ≥ 200 · 주변 = 순위/(n+1) · 시장 M_−i = i 를 뺀 합집합 시총가중 — 가중은 결정 달 말 ME 고정 근사)을 쓴다(이탈 공개).
  Q7 시계열 측정: y_{t+1} = S&P 500(SPY 총수익) 초과 · x_t = −ΔCIQLT_t(결정 달) · NW(6) · CT 표본 밖 R² 는 확장창 36개월부터(기준 = 확장 평균).
  Q9 첫 창: 명세 2009-01~2013-12 · 랩 가격 격자의 첫 월말이 2009-01 이라 첫 월수익은 2009-02 → 첫 계산 창 2009-02~2014-01(한 달 늦음 · 공개 ·
     평가 창 2016-08~ 과 무관 · 상태 z 의 확장 이력이 한 달 짧다).
  Q8 Nagel 대조군 상태: x_t = Σ_{k=1..12}(13 − k)·r_{m,t−k+1} / Σ(13 − k) ÷ σ_12(r_m) → 확장창 z(관측 ≥ 12) → 같은 θ 사상.

🚨 랩 규율 — 이 모듈은 과거 수익으로 신호(잔차 · 분위 요인 · 노출 · 상태)를 만든다(신호의 입력). 다음 달 수익을 쓰는 통계(FM γ · 시계열 측정 · 표본 밖 R²)는
   kind 를 받고 w_core.assert_kind_allowed 를 지난다. --selftest 는 합성 자료만.

  python build/w_ciq.py --selftest
"""
from __future__ import annotations

import math
import os
import sys
import time
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import w_core as WC          # noqa: E402
import w_guard as WG         # noqa: E402

CARD = "W04"
TAU = 0.2
WIN, MIN_OBS = 60, 48
QFA_TOL, QFA_MAXIT = 1e-6, 200
FIRST_WINDOW = ("2009-01", "2013-12")                     # 명세
FIRST_DECISION = "2014-01"                                 # 자료 격자의 첫 월수익이 2009-02 → 첫 계산 창 2009-02~2014-01(Q9)
Q_TOP = 0.30
THETA0 = 0.5
THETA_SLOPE, Z_CLIP = 0.25, 2.0
Z_MIN_N = 12
IC_LIT = 0.016
DN_WIN, DN_MIN_FRAC = 252, 0.20
LTD_U, LTD_MIN = 0.05, 200
TS_NW, CT_MIN = 6, 36
N_PLACEBO, BLOCK = 1000, 12
REPACK_SHRINK = 0.5
DIRECTION = WC.CARD_DIRECTION[CARD]
assert DIRECTION == +1

CIQ_UNITS = [WG.unit("ret_ex_m", source="data/pit_px.json", concept="monthly excess return (60-month window)", use="signal"),
             WG.unit("mkt_lab", source="v_pit.hold_ret + v_px_split.me_value", concept="union cap-weighted market return", use="residual_factor"),
             WG.unit("smb_lab", source="v_pit.hold_ret + v_px_split.me_value", concept="size spread (split-only ME median split VW difference)",
                     use="residual_factor"),
             WG.unit("ciq_beta", source="w_ciq.qfa1", concept="exposure to common idiosyncratic quantile factor innovation", use="signal"),
             WG.unit("ciq_state", source="w_ciq.qfa1", concept="standardized last innovation of the tau 0.2 quantile factor", use="theta_state"),
             WG.unit("beta_fp", source="v_pit.beta_fp", concept="market beta (FP daily)", use="control"),
             WG.unit("b_dn", source="data/bench_px.json + data/pit_px.json", concept="downside beta (x-dnbeta definition)", use="control"),
             WG.unit("ltd_np", source="data/pit_px.json", concept="nonparametric lower tail dependence C(u,u)/u (Q07 A3)", use="control")]
WG.assert_units(CIQ_UNITS, "w_ciq 입력(모듈 적재)")


# ══════════════════════════════════════════════════════════════════════════
#  정확 스칼라 분위 해(Q1)
# ══════════════════════════════════════════════════════════════════════════
def rho(u, tau):
    u = np.asarray(u, float)
    return u * (tau - (u < 0))


def wq_scalar(y, x, tau):
    """min_b Σ ρ_τ(y_j − b·x_j) 의 정확해 — (b*, 목적값). x = 0 · 결측 항은 뺀다(목적에는 x = 0 항의 상수 ρ_τ(y) 를 더한다)."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    nz = x != 0
    const = float(rho(y[~nz], tau).sum())
    y, x = y[nz], x[nz]
    if len(y) == 0:
        return float("nan"), const
    c = y / x
    w = np.abs(x)
    tp = np.where(x > 0, tau, 1.0 - tau)
    target = float((w * tp).sum())
    order = np.argsort(c, kind="stable")
    cs = np.cumsum(w[order])
    k = int(np.searchsorted(cs, target * (1.0 - 1e-13), side="left"))
    k = min(k, len(c) - 1)
    b = float(c[order[k]])
    return b, float(rho(y - b * x, tau).sum()) + const


def wq_columns(Y, X, tau):
    """열마다 min_b Σ_i ρ_τ(Y_ij − b·X_ij) 의 정확해(벡터화 · wq_scalar 와 비트까지 같은 해) — 결측 · X = 0 은 뺀다 · 선 항이 없으면 NaN."""
    Y = np.asarray(Y, float)
    X = np.asarray(X, float)
    ok = np.isfinite(Y) & np.isfinite(X) & (X != 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(ok, Y / np.where(ok, X, 1.0), np.inf)
    w = np.where(ok, np.abs(X), 0.0)
    tp = np.where(X > 0, tau, 1.0 - tau)
    target = (w * np.where(ok, tp, 0.0)).sum(0)
    order = np.argsort(c, axis=0, kind="stable")
    cs = np.cumsum(np.take_along_axis(w, order, 0), 0)
    hit = cs >= (target * (1.0 - 1e-13))[None, :]
    k = np.argmax(hit, axis=0)
    b = np.take_along_axis(np.take_along_axis(c, order, 0), k[None, :], 0)[0]
    b = np.where(ok.any(0), b, np.nan)
    return b


def wq_lp(y, x, tau):
    """HiGHS LP 판(교차 확인 · selftest) — min Σ τu⁺ + (1−τ)u⁻ s.t. y − b·x = u⁺ − u⁻ · u ≥ 0 · b 자유. 돌려주는 것 (b, 목적값)."""
    from scipy.optimize import linprog
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    n = len(y)
    cvec = np.r_[0.0, np.full(n, tau), np.full(n, 1.0 - tau)]
    A = np.hstack([x[:, None], np.eye(n), -np.eye(n)])
    bounds = [(None, None)] + [(0, None)] * (2 * n)
    r = linprog(cvec, A_eq=A, b_eq=y, bounds=bounds, method="highs")
    if not r.success:
        raise SystemExit("🚨 HiGHS LP 실패: %s" % r.message)
    return float(r.x[0]), float(r.fun)


# ══════════════════════════════════════════════════════════════════════════
#  분위 요인분석(1요인 · 교대 · Q2)
# ══════════════════════════════════════════════════════════════════════════
def qfa1(Y, tau=TAU, tol=QFA_TOL, maxit=QFA_MAXIT, sign_ref=None):
    """Y(T × N · 결측 NaN) → {f(T), lam(N), obj, iters, converged, path(목적 경로)} — Q_τ(Y_it) = λ_i f_t 의 교대 정확해(Q2).
    sign_ref(T)가 있으면 corr(f, sign_ref) > 0 이 되게 부호를 정한다(명세 부호 규칙)."""
    Y = np.asarray(Y, float)
    T, N = Y.shape
    M = np.isfinite(Y)
    Y0 = np.where(M, Y, 0.0)
    U, s, Vt = np.linalg.svd(Y0, full_matrices=False)
    f = U[:, 0] * s[0]
    f = f / math.sqrt(float(np.mean(f * f)))
    if f.sum() < 0:
        f = -f
    lam = np.zeros(N)
    obj_prev, path, conv, it = None, [], False, 0
    n_obs = max(1, int(M.sum()))
    for it in range(1, maxit + 1):
        lam = wq_columns(Y, np.broadcast_to(f[:, None], Y.shape), tau)
        lam = np.where(np.isfinite(lam), lam, 0.0)
        f = wq_columns(Y.T, np.broadcast_to(lam[:, None], (N, T)), tau)
        f = np.where(np.isfinite(f), f, 0.0)
        sc = math.sqrt(float(np.mean(f * f)))
        if sc <= 0:
            break
        f, lam = f / sc, lam * sc
        obj = float(np.where(M, rho(Y0 - np.outer(f, lam), tau), 0.0).sum()) / n_obs
        path.append(obj)
        if obj_prev is not None and abs(obj_prev - obj) <= tol * max(abs(obj_prev), 1e-300):
            conv = True
            break
        obj_prev = obj
    if sign_ref is not None:
        r = np.asarray(sign_ref, float)
        ok = np.isfinite(r)
        if ok.sum() >= 3 and np.corrcoef(f[ok], r[ok])[0, 1] < 0:
            f, lam = -f, -lam
    return {"f": f, "lam": lam, "obj": path[-1] if path else None, "iters": it, "converged": conv, "path": path}


# ══════════════════════════════════════════════════════════════════════════
#  창 하나(잔차 · QFA · 혁신 · 노출)
# ══════════════════════════════════════════════════════════════════════════
def _ols_cols(Y, X, min_obs):
    """열마다 선 행으로 OLS — Y(T × N) · X(T × k · 결측 없음) → (계수 k × N, 잔차 T × N(NaN), 유효 수 N)."""
    T, N = Y.shape
    M = np.isfinite(Y)
    B = np.full((X.shape[1], N), np.nan)
    E = np.full((T, N), np.nan)
    n = M.sum(0)
    full = np.flatnonzero(M.all(0) & (n >= min_obs))
    if len(full):
        b = np.linalg.lstsq(X, Y[:, full], rcond=None)[0]
        B[:, full] = b
        E[:, full] = Y[:, full] - X @ b
    for j in np.flatnonzero(~M.all(0) & (n >= min_obs)):
        r = M[:, j]
        b = np.linalg.lstsq(X[r], Y[r, j], rcond=None)[0]
        B[:, j] = b
        E[r, j] = Y[r, j] - X[r] @ b
    return B, E, n


def ciq_window(R_ex, mkt_ex, smb, tau=TAU, min_obs=MIN_OBS, capm_only=False):
    """결정 달 창 하나 — R_ex(60 × N 월 초과수익 · 결측 NaN) · mkt_ex · smb(60) → {f, dciq(59), d_last, beta(N · 결측 NaN), q20, converged, iters, n}.
    capm_only = CAPM 잔차 쌍둥이(MKT 만)."""
    R_ex = np.asarray(R_ex, float)
    T, N = R_ex.shape
    X = np.column_stack([np.ones(T), mkt_ex] + ([] if capm_only else [smb]))
    _, E, n = _ols_cols(R_ex, X, min_obs)
    keep = n >= min_obs
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)                            # 이력이 없는 열(모두 결측)의 nanstd 경고
        sd = np.nanstd(E, axis=0, ddof=1)
    Z = np.where(keep[None, :] & (sd[None, :] > 0), E / np.where(sd > 0, sd, 1.0)[None, :], np.nan)
    cols = np.flatnonzero(keep & (sd > 0))
    out = {"n": int(len(cols)), "beta": np.full(N, np.nan), "converged": False, "iters": 0}
    if len(cols) < 10:
        return out
    Zc = Z[:, cols]
    with np.errstate(all="ignore"):
        q20 = np.array([np.nanpercentile(Zc[t], 100 * tau) if np.isfinite(Zc[t]).sum() >= 5 else np.nan for t in range(T)])
    q = qfa1(Zc, tau, sign_ref=q20)
    f = q["f"]
    d = np.diff(f)
    out.update(f=f, dciq=d, d_last=float(d[-1]), q20=q20, converged=q["converged"], iters=q["iters"], obj=q["obj"])
    X2 = np.column_stack([np.ones(T - 1), mkt_ex[1:], d])
    B2, _, n2 = _ols_cols(R_ex[1:], X2, min_obs)
    beta = np.where(n2 >= min_obs, B2[2], np.nan)
    out["beta"] = beta if q["converged"] else np.full(N, np.nan)
    return out


def theta_c(z):
    """C 팔 θ_t = 0.5 + 0.25·clip(−z_t, −2, 2) ∈ [0, 1] · z 결측 = 0(θ0)."""
    z = 0.0 if (z is None or not (z == z)) else float(z)
    return THETA0 + THETA_SLOPE * min(max(-z, -Z_CLIP), Z_CLIP)


def state_z(d_by_month, months, min_n=Z_MIN_N):
    """Q3 — z_t = d_t / SD(d_{≤t}) · 관측 < min_n 이면 0 · 돌려주는 것 {달: z}."""
    hist, out = [], {}
    for m in months:
        d = d_by_month.get(m)
        if d is None or not (d == d):
            out[m] = 0.0
            continue
        hist.append(float(d))
        if len(hist) < min_n:
            out[m] = 0.0
            continue
        sd = float(np.std(hist, ddof=1))
        out[m] = float(d / sd) if sd > 0 else 0.0
    return out


def block_shuffle(z_by_month, months, block, seed):
    """CIQ 상태 라벨 12개월 블록 섞기(위약) — 연속 블록 차례를 씨앗으로 섞어 다시 잇는다(블록 안 차례 보존)."""
    v = [z_by_month.get(m) for m in months]
    blocks = [v[i:i + block] for i in range(0, len(v), block)]
    order = np.random.default_rng(seed).permutation(len(blocks))
    flat = [x for j in order for x in blocks[j]]
    return {m: x for m, x in zip(months, flat)}


def nagel_state(mkt_by_month, months, min_n=Z_MIN_N):
    """Q8 — Nagel 대조군 상태 → 확장창 z. mkt_by_month{달: 그달 시장 수익}."""
    raw = {}
    wts = np.array([13 - k for k in range(1, 13)], float)
    for m in months:
        r = [mkt_by_month.get(WC.mshift(m, -(k - 1))) for k in range(1, 13)]
        if any(x is None or not (x == x) for x in r):
            continue
        r = np.array(r, float)
        sd = float(r.std(ddof=1))
        if sd > 0:
            raw[m] = float((wts * r).sum() / wts.sum()) / sd
    hist, out = [], {}
    for m in months:
        if m not in raw:
            out[m] = 0.0
            continue
        hist.append(raw[m])
        if len(hist) < min_n:
            out[m] = 0.0
            continue
        mu, sd = float(np.mean(hist)), float(np.std(hist, ddof=1))
        out[m] = (raw[m] - mu) / sd if sd > 0 else 0.0
    return out


def repack_flag(gamma_base, gamma_full, shrink=REPACK_SHRINK):
    """«DNBETA 재포장» 주의(명세) — b_dn · LTD 를 넣은 γ 가 넣기 전 γ 의 절반 아래로 줄면 참(표시를 바꾸지 않는 주의 · K5)."""
    if gamma_base is None or gamma_full is None or gamma_base == 0:
        return None
    return bool(abs(gamma_full) < shrink * abs(gamma_base) or np.sign(gamma_full) != np.sign(gamma_base))


# ══════════════════════════════════════════════════════════════════════════
#  하방 통제(Q5 · Q6)
# ══════════════════════════════════════════════════════════════════════════
def downside_beta(Lw, mw, min_frac=DN_MIN_FRAC):
    """Q5 — x-dnbeta β_dn(W): 시장 < 창 평균인 날만의 Cov/Var(표본 분산 n−1) · 그런 날 < min_frac·W 면 결측. Lw(W × N 로그수익) · mw(W)."""
    Lw = np.asarray(Lw, float)
    mw = np.asarray(mw, float)
    W = len(mw)
    rows = np.isfinite(mw) & (mw < np.nanmean(mw))
    X = np.broadcast_to(mw[:, None], Lw.shape)
    valid = np.isfinite(Lw) & np.isfinite(X) & rows[:, None]
    n = valid.sum(0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        mx = np.where(valid, X, 0.0).sum(0) / n
        my = np.where(valid, Lw, 0.0).sum(0) / n
        dx = np.where(valid, X - mx, 0.0)
        dy = np.where(valid, Lw - my, 0.0)
        b = (dx * dy).sum(0) / (dx * dx).sum(0)
    b[(n < max(int(min_frac * W), 2)) | ~np.isfinite(b)] = np.nan
    return b


def ltd_np(Ri, Mi, u=LTD_U, min_pairs=LTD_MIN):
    """Q6 — Ĉ(u,u)/u = #{R/(n+1) ≤ u ∧ S/(n+1) ≤ u}/n ÷ u(주변 = 순위 · 유효 짝만) · Ri · Mi(W × N · 열마다 i 와 M_−i)."""
    from scipy.stats import rankdata
    Ri = np.asarray(Ri, float)
    Mi = np.asarray(Mi, float)
    out = np.full(Ri.shape[1], np.nan)
    for j in range(Ri.shape[1]):
        ok = np.isfinite(Ri[:, j]) & np.isfinite(Mi[:, j])
        n = int(ok.sum())
        if n < min_pairs:
            continue
        R = rankdata(Ri[ok, j], method="max")
        S = rankdata(Mi[ok, j], method="max")
        out[j] = float(np.sum((R / (n + 1.0) <= u) & (S / (n + 1.0) <= u)) / n / u)
    return out


def market_ex_i(Rd, w):
    """M_−i(Q6) — Rd(W × N 일간 수익) · w(N · 결정 달 말 ME 가중 고정 근사) → (W × N) 열마다 i 를 뺀 가중 평균(그날 선 이름끼리)."""
    Rd = np.asarray(Rd, float)
    w = np.asarray(w, float)
    M = np.isfinite(Rd)
    W = np.where(M, w[None, :], 0.0)
    S = (np.where(M, Rd, 0.0) * W).sum(1)
    Wt = W.sum(1)
    num = S[:, None] - np.where(M, Rd * w[None, :], 0.0)
    den = Wt[:, None] - W
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


# ══════════════════════════════════════════════════════════════════════════
#  시계열 측정(Q7) — 🚨 다음 달 수익
# ══════════════════════════════════════════════════════════════════════════
def ts_measure(kind, months, x_by_month, y_next_by_month, lag=TS_NW, ct_min=CT_MIN):
    """y_{t+1} ~ a + b·x_t(x = −ΔCIQLT) — NW(lag) t · CT 확장창 표본 밖 R²(기준 확장 평균 · 첫 ct_min 달은 추정만). 🚨 kind 자물쇠."""
    WC.assert_kind_allowed(kind, "w_ciq.ts_measure")
    import w_stagem as S
    rows = [(m, x_by_month.get(m), y_next_by_month.get(m)) for m in months]
    rows = [(m, float(x), float(y)) for m, x, y in rows if x is not None and y is not None and x == x and y == y]
    if len(rows) < ct_min + 12:
        return {"T": len(rows), "b": None, "t": None, "r2_os": None}
    ms = [r[0] for r in rows]
    x = np.array([r[1] for r in rows])
    y = np.array([r[2] for r in rows])
    b, se, n = S.nw_ols_gap(ms, y, np.column_stack([np.ones(len(x)), x]), lag)
    num = den = 0.0
    for j in range(ct_min, len(rows)):
        X = np.column_stack([np.ones(j), x[:j]])
        bb = np.linalg.lstsq(X, y[:j], rcond=None)[0]
        yhat = bb[0] + bb[1] * x[j]
        ybar = float(y[:j].mean())
        num += (y[j] - yhat) ** 2
        den += (y[j] - ybar) ** 2
    return {"T": n, "b": float(b[1]), "t": float(b[1] / se[1]) if se[1] > 0 else None, "r2_os": (1 - num / den) if den > 0 else None,
            "direction": +1}


# ══════════════════════════════════════════════════════════════════════════
#  실자료 입력 빌드(신호의 입력 · 값을 찍지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def market_factors(U, hold_months, rf_m):
    """Q4 — 보유월 τ 의 MKT(합집합 시총가중) · SMB(ME 중앙값 분할 VW 차) · rf · 초과 MKT. 돌려주는 것 {τ: (mkt, smb, rf)}.
    🚨 실자료 과거 수익(신호의 입력) — 값을 찍지 않는다."""
    out = {}
    for tau_m in hold_months:
        m = WC.mshift(tau_m, -1)
        if m not in U.me_idx or tau_m not in U.me_idx:
            continue
        me = U.me(m)
        hr = U.hold_ret(m)
        rows = [(me[r["t"]][0], hr.get(r["t"])) for r in U.members(m)]
        rows = [(v, x) for v, x in rows if v and x is not None and np.isfinite(x)]
        if len(rows) < 20:
            continue
        v = np.array([a for a, _ in rows])
        x = np.array([b for _, b in rows])
        med = float(np.median(v))
        sm, bg = v <= med, v > med
        mkt = float((v * x).sum() / v.sum())
        smb = float((v[sm] * x[sm]).sum() / v[sm].sum() - (v[bg] * x[bg]).sum() / v[bg].sum())
        out[tau_m] = (mkt, smb, float(rf_m.get(tau_m, 0.0)))
    return out


def window_matrix(U, keys, end_month, fac, win=WIN):
    """창 행렬 — 가격 키 keys 의 월 초과수익(τ = end−win+1 .. end · 월말 수정종가 비) · 초과 MKT · SMB. $1 규칙(원 종가가 선 이름만 · Q4).
    돌려주는 것 (R_ex(win × N), mkt_ex(win), smb(win), 달 목록) · 요인이 빠진 달이 있으면 None."""
    ms = [WC.mshift(end_month, -(win - 1 - j)) for j in range(win)]
    if any(m not in fac for m in ms):
        return None
    pos = [U._mpos.get(m) for m in ms]
    if any(p is None or p < 1 for p in pos):
        return None
    pos = np.array(pos)
    R = np.full((win, len(keys)), np.nan)
    for j, k in enumerate(keys):
        pm = U.Pm.get(k)
        if pm is None:
            continue
        a, b = pm[pos - 1], pm[pos]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.where((a > 0) & (b > 0), b / a - 1.0, np.nan)
        raw = U.vd1.get(k) if k in U.vd1 else U.rawdb.get(k)
        if raw is not None:
            ends = np.array([U.me_idx[m] for m in ms])
            pr = np.asarray(raw, float)[ends]
            r = np.where(np.isfinite(pr) & (pr < 1.0), np.nan, r)
        R[:, j] = r
    rf = np.array([fac[m][2] for m in ms])
    return R - rf[:, None], np.array([fac[m][0] for m in ms]) - rf, np.array([fac[m][1] for m in ms]), ms


def run_windows(U, dec_months, fac, log=None):
    """결정 달마다 창 · QFA · 노출 — 돌려주는 것 {달: {"keys", "beta"{키}, "d_last", "converged", "iters", "n"}}(신호 · 값을 찍지 않는다)."""
    out = {}
    t0 = time.time()
    for i, m in enumerate(dec_months):
        mem = U.members(m)
        keys = sorted({r["k"] for r in mem})
        wm = window_matrix(U, keys, m, fac)
        if wm is None:
            out[m] = {"keys": keys, "beta": {}, "d_last": None, "converged": False, "iters": 0, "n": 0, "why": "window"}
            continue
        R_ex, mx, smb, _ = wm
        w = ciq_window(R_ex, mx, smb)
        out[m] = {"keys": keys, "beta": {k: float(b) for k, b in zip(keys, w["beta"]) if np.isfinite(b)}, "d_last": w.get("d_last"),
                  "converged": bool(w.get("converged")), "iters": int(w.get("iters", 0)), "n": int(w.get("n", 0))}
        if log and (i % 24 == 0):
            log("  W04 창 %s · %d/%d · %.0fs" % (m, i + 1, len(dec_months), time.time() - t0))
    return out


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 자료만)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _st_exact():
    rng = np.random.default_rng(WC.SEED)
    worst = 0.0
    for rep in range(600):
        n = int(rng.integers(1, 40))
        y = rng.normal(0, 1, n)
        x = rng.normal(0, 1, n)
        if rep % 5 == 0:
            x[rng.random(n) < 0.3] = 0.0                    # x = 0 항
        if rep % 7 == 0:
            y = np.round(y, 1)
            x = np.round(x, 1)                              # 동률
        tau = float(rng.choice([0.2, 0.5, 0.8, 0.05]))
        b, obj = wq_scalar(y, x, tau)
        if not np.isfinite(b):
            assert np.all(x == 0)
            continue
        nz = x != 0
        cands = y[nz] / x[nz]
        objs = [float(rho(y - c * x, tau).sum()) for c in cands]
        best = min(objs)
        worst = max(worst, abs(obj - best) / max(1.0, abs(best)))
        assert obj <= best + 1e-12 * max(1.0, abs(best)), (rep, obj, best)
        # 어떤 b 도 더 낫지 않다(격자 · 볼록)
        grid = np.linspace(cands.min() - 1, cands.max() + 1, 101)
        assert obj <= min(float(rho(y - g * x, tau).sum()) for g in grid) + 1e-12
    # 벡터화 = 스칼라(비트까지)
    Y = rng.normal(0, 1, (60, 80))
    Y[rng.random(Y.shape) < 0.1] = np.nan
    X = rng.normal(0, 1, (60, 80))
    bv = wq_columns(Y, X, 0.2)
    bs = np.array([wq_scalar(Y[:, j], X[:, j], 0.2)[0] for j in range(80)])
    assert np.array_equal(bv, bs)
    # HiGHS LP 교차 확인 — 합성 QFA 의 f 단계 3달(명세 «3달을 HiGHS LP 로»)
    T, N = 60, 120
    f0 = rng.normal(0, 1, T)
    l0 = rng.normal(1, 0.5, N)
    E = rng.standard_normal((T, N))
    Yq = np.outer(f0, l0) + (E - np.quantile(rng.standard_normal(100000), 0.2))
    q = qfa1(Yq, 0.2)
    for t in (0, 29, 59):
        b_e, o_e = wq_scalar(Yq[t], q["lam"], 0.2)
        b_l, o_l = wq_lp(Yq[t], q["lam"], 0.2)
        assert abs(o_e - o_l) <= 1e-7 * max(1.0, abs(o_l)), (t, o_e, o_l)
        assert abs(b_e - b_l) < 1e-6 or abs(float(rho(Yq[t] - b_l * q["lam"], 0.2).sum()) - o_e) < 1e-7
    return "정확해 = 꺾인 점 최소 · 격자보다 나쁘지 않음(600 사례 · x=0 · 동률 · τ 넷) · 벡터화 = 스칼라(비트) · HiGHS LP 3달 일치"


def _st_qfa():
    rng = np.random.default_rng(WC.SEED + 1)
    T, N = 60, 450
    f0 = rng.standard_normal(T)
    l0 = rng.normal(0.8, 0.4, N)
    e = rng.standard_normal((T, N))
    Y = np.outer(f0, l0) + (e - (-0.8416212335729143))      # Q_0.2(e − q) = 0 → Q_τ(Y) = λ f
    Y[rng.random(Y.shape) < 0.05] = np.nan
    q = qfa1(Y, 0.2, sign_ref=f0)
    c = float(np.corrcoef(q["f"], f0)[0, 1])
    assert q["converged"] and c > 0.97, (q["converged"], c, q["iters"])
    assert abs(float(np.mean(q["f"] ** 2)) - 1.0) < 1e-12                               # Q2 정규화
    p = np.array(q["path"])
    assert np.all(np.diff(p) <= 1e-12 * np.abs(p[:-1])), "목적이 늘었다"                  # 교대 정확 최소 → 단조
    q2 = qfa1(Y, 0.2, sign_ref=-f0)
    assert np.allclose(q2["f"], -q["f"]) and np.allclose(q2["lam"], -q["lam"])          # 부호 규칙
    q3 = qfa1(Y, 0.2, sign_ref=f0)
    assert np.array_equal(q3["f"], q["f"])                                              # 결정적
    # 창 하나 — 잔차 · 노출 복원(합성: ΔCIQLT 에 심은 노출)
    mkt = rng.normal(0.008, 0.045, T)
    smb = rng.normal(0.0, 0.02, T)
    bet = rng.normal(1.0, 0.3, N)
    R = mkt[:, None] * bet[None, :] + 0.3 * smb[:, None] * rng.normal(0, 1, N)[None, :] + Y * 0.05
    R[:3, :10] = np.nan
    w = ciq_window(R, mkt, smb)
    assert w["converged"] and w["n"] == N and np.isfinite(w["beta"]).sum() == N and len(w["dciq"]) == T - 1
    R2 = R.copy()
    R2[:15, :5] = np.nan                                                                # 48개월 미만 → 결측
    w2 = ciq_window(R2, mkt, smb)
    assert np.isnan(w2["beta"][:5]).all() and w2["n"] == N - 5
    wc = ciq_window(R, mkt, smb, capm_only=True)
    assert wc["n"] == N
    return "QFA 심은 분위 요인 복원 corr %.3f(%d회) · 정규화 · 단조 목적 · 부호 규칙 · 결정적 · 창(잔차 · 노출 · 48개월 규칙 · CAPM 쌍둥이)" % (c, q["iters"])


def _st_theta_state():
    assert theta_c(0.0) == 0.5 and theta_c(None) == 0.5 and theta_c(-10) == 1.0 and theta_c(10) == 0.0 and abs(theta_c(-1) - 0.75) < 1e-15
    ms = WC.months_between("2013-12", "2026-07")
    rng = np.random.default_rng(WC.SEED + 2)
    d = {m: float(rng.normal(0, 0.3)) for m in ms}
    z = state_z(d, ms)
    assert all(z[m] == 0.0 for m in ms[:Z_MIN_N - 1]) and z[ms[20]] != 0.0
    h = [d[m] for m in ms[:31]]
    assert abs(z[ms[30]] - d[ms[30]] / np.std(h, ddof=1)) < 1e-12                       # Q3 — 확장 SD(t 까지)
    # 선견 없음 — 뒤 달 d 를 바꿔도 앞 z 그대로
    d2 = dict(d)
    d2[ms[40]] = 99.0
    z2 = state_z(d2, ms)
    assert all(z2[m] == z[m] for m in ms[:40]) and z2[ms[40]] != z[ms[40]]
    # 항등(명세 guards.identity): z ≡ 0 → θ ≡ θ0 → C 책 = S 책
    assert all(theta_c(v) == THETA0 for v in state_z({m: 0.0 for m in ms}, ms).values())
    bs = block_shuffle(z, ms, 12, WC.SEED)
    assert sorted(bs.values()) == sorted(z.values()) and set(bs) == set(ms)
    orig_blocks = [tuple(z[m] for m in ms[i:i + 12]) for i in range(0, len(ms), 12)]
    seq = [bs[m] for m in ms]
    pos, used = 0, []
    while pos < len(seq):                                                               # 섞인 열 = 원래 블록(안 차례 보존)을 이은 것
        hit = [j for j, b in enumerate(orig_blocks) if j not in used and tuple(seq[pos:pos + len(b)]) == b]
        assert hit, pos
        used.append(hit[0])
        pos += len(orig_blocks[hit[0]])
    assert sorted(used) == list(range(len(orig_blocks))) and used != list(range(len(orig_blocks)))
    mk = {m: float(rng.normal(0.008, 0.04)) for m in WC.months_between("2012-01", "2026-07")}
    ng = nagel_state(mk, ms)
    assert len(ng) == len(ms) and all(np.isfinite(list(ng.values())))
    assert repack_flag(0.1, 0.04) is True and repack_flag(0.1, 0.06) is False and repack_flag(0.1, -0.2) is True and repack_flag(None, 1) is None
    return "θ 사상(범위 [0, 1] · z=0 → 0.5) · 확장 SD 상태 · 선견 없음 · 항등(z≡0 → C = S) · 블록 섞기 보존 · Nagel 대조 · 재포장 주의"


def _st_controls():
    rng = np.random.default_rng(WC.SEED + 3)
    W, N = 252, 40
    m = rng.normal(0.0003, 0.01, W)
    L = 1.2 * m[:, None] + rng.normal(0, 0.012, (W, N))
    L[:10, 0] = np.nan
    b = downside_beta(L, m)
    rows = m < m.mean()
    j = 3
    ok = rows & np.isfinite(L[:, j])
    ref = np.cov(L[ok, j], m[ok], ddof=1)[0, 1] / np.var(m[ok], ddof=1)
    assert abs(b[j] - ref) < 1e-12 and np.all(np.isfinite(b))
    b2 = downside_beta(L[:40], m[:40], min_frac=0.9)
    assert np.isnan(b2).all()                                                            # 하락일 < 20%(여기서는 90%) 면 결측
    # LTD: 손 계산과 같다 · 완전 동조면 1/u · 독립이면 ≈ u/u·u ≈ 작다
    Ri = rng.standard_normal((W, 3))
    Mi = np.column_stack([Ri[:, 0], rng.standard_normal(W), -Ri[:, 2]])
    lt = ltd_np(Ri, Mi)
    from scipy.stats import rankdata
    R = rankdata(Ri[:, 1], method="max")
    S = rankdata(Mi[:, 1], method="max")
    assert abs(lt[1] - np.sum((R / (W + 1) <= LTD_U) & (S / (W + 1) <= LTD_U)) / W / LTD_U) < 1e-15
    assert lt[0] > 0.9 and lt[2] == 0.0 and np.isnan(ltd_np(Ri[:100], Mi[:100])).all()
    # M_−i: 둘이면 서로의 수익
    Rd = rng.normal(0, 0.01, (5, 2))
    Me = market_ex_i(Rd, np.array([2.0, 1.0]))
    assert np.allclose(Me[:, 0], Rd[:, 1]) and np.allclose(Me[:, 1], Rd[:, 0])
    # 시계열 측정 — 심은 기울기 복원 · 실자료 자물쇠
    ms = WC.months_between("2013-12", "2026-07")
    x = {mm: float(v) for mm, v in zip(ms, rng.normal(0, 1, len(ms)))}
    y = {mm: 0.01 * x[mm] + float(rng.normal(0, 0.02)) for mm in ms}
    tm = ts_measure("synth", ms, x, y)
    assert tm["t"] > 3 and tm["r2_os"] > 0
    assert _raises(lambda: ts_measure("real", ms, x, y))
    return "b_dn = x-dnbeta 식(1e−12 · 하락일 규칙) · LTD Ĉ(u,u)/u 손풀이 · 짝 < 200 결측 · M_−i · 시계열 NW(6) · CT R²_OS · 자물쇠"


def _st_static():
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    mods = set()
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Import):
            mods |= {a.name.split(".")[0] for a in nd.names}
        elif isinstance(nd, ast.ImportFrom) and nd.module:
            mods.add(nd.module.split(".")[0])
    assert not [m for m in mods if WG.forbidden(m)], mods
    assert not WG.check_units(CIQ_UNITS) and not WG.literal_scan(os.path.abspath(__file__))
    assert CARD in WC.FAMILY["A"]
    return "금지 import 없음 · 입력 단위(잔차 요인 MKT · SMB 만) · 문자열 상수 · 등록 A 가족"


def selftest():
    res, ok = [], True
    for fn in (_st_exact, _st_qfa, _st_theta_state, _st_controls, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-16s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_ciq selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
