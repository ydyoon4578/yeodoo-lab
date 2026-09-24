# -*- coding: utf-8 -*-
"""build/q_ltd.py — 배치 Q · Q07 FE2-LTDSWAP(코퓰러 폭락 민감도 교체 — 베타로 설명되지 않는 하방 꼬리 동조가 큰 Eg 종목을 걸러낸다 · Eg 상위 45 → 30).

근본 이유: 베타는 평소의 선형 동조만 잰다. 시장이 무너지는 날에만 함께 무너지는 성질(하방 꼬리 의존 LTD)은 코퓰러로 따로 잰다.
CRW(2018)는 LTD 가 베타 · 하방베타 · 공왜도 · 공첨도와 구별되고, 직전 12개월 LTD 가 약했던 종목이 극단적 하락장에서 덜 빠진다는 것을
보였다. 이 단계는 LTD 를 FP 베타에 회귀한 잔차(베타로 설명되지 않는 꼬리 동조)만 써서 EG30 후보 45 중 15 를 뺀다 — 바스켓 베타는
거의 그대로라 급등 포착은 지키고 폭락일 동반 붕괴만 줄이려는 것이다. 강한 LTD 종목은 보험료(연 4.32%)를 받으므로 전 기간 Δ 는
V0 보다 낮을 것으로 미리 적었다(판정은 그 보험료가 «바스켓 덜 들기» 보다 싼지 — 하락월 Δβ).

규칙(카드 원문 scratchpad/qbatch_final.md # Q07 — 숫자는 모두 카드에 적힌 것):
  편입 = EG30 과 같다(EG_BASE · 2016-08 + 분기말 41번 · 사이는 흘러감 · 편도 10bp · 펀드 90/10 · 시총가중 20% 상한).
  (1) P = Eg 상위 45(qg_lab.score base · V0 와 같은 적격).
  (2) i ∈ P 마다 편입일까지 252일 단순수익 r_i 와 M_−i(union PIT 시총가중 · i 제외(가격 키 · CIK · 선언된 CIK 없는 같은 발행사) · 전날 종가 비중)
      · 유효 짝 ≥ 200 이 아니면 LTD 결측.
  (3) 주변 = 순위/(n+1)(CRW 식 6).
  (4) 64 혼합 w1·C_L + w2·C_N + w3·C_U · (w1,w2,w3) = softmax(a1,a2,0) · 정준 최우(식 7) · 모수 한도는 log/logit 변환 ·
      L-BFGS-B 씨앗 3 시작(20260925+s · 카드) + 결정적 1 시작(무게 같게 · θ = 족 하나만의 최우 · 검토 수정 · 카드 수정 필요)
      · 가장 큰 로그우도 · 한도에 닿은 적합 · 시작 일치(n_near) 는 기록.
      C_L ∈ {Clayton, 회전 Gumbel, 회전 Joe, 회전 Galambos} · C_N ∈ {Gauss, Frank, FGM, Plackett} · C_U ∈ {Gumbel, Joe, Galambos, 회전 Clayton}.
  (5) 적분 앤더슨-달링 거리(CRW 식 9 · Deheuvels 경험 코퓰러 n×n 격자) 최소 혼합을 고른다.
  (6) LTD = w1*·λ_L(θ1*) · SE = 관측 정보의 델타법(식별되는 방향만의 무어-펜로즈 역 — 무게 0 성분의 θ 는 식별되지 않는다 · 기록만).
  (7) LTD⊥ = P 안 OLS LTD ~ 1 + β_FP 의 잔차.
  (8) 결측(LTD 또는 β)부터, 다음은 LTD⊥ 높은 순으로 15 개를 빼 30 을 남긴다.   (9) 시총가중 20% 상한 · 흘러감 · 10bp.
  대조: C3 FP 베타 상위 15 빼기(G4 · 하락월 평균 Δβ(V1 − C3) > 0) · C2 무작위 빼기 위약 1000번(씨앗 SEED + i · G4 · 참 Δβ ≥ 95 백분위)
      — 판정 C2 는 V1 과 같은 결측을 먼저 빼고 나머지를 균등 무작위(검토 수정) · 카드 문구 그대로의 P 45 균등 15 는 기록만.
  F0: 카드에 없다 → 늘 ok(제안 F0 는 기록만). 굽기는 얼린 적합(FITS_MANIFEST)만 쓰고 다시 적합하지 않는다.
  측정만 팔: A1 원 LTD · A2 꼬리 비대칭(UTD⊥ − LTD⊥ 낮은 순) · A3 비모수 Ĉ(u,u)/u (u = 0.05) · A4 시장 = S&P 500 PR.

출처: Chabi-Yo · Ruenzi · Weigert (2018) JFQA 53(3) 1059-1100 · 작업논문 WPF-1324(2016 판) §2.1.1–2.1.3 · 식 (5)–(9) · 각주 13(시장에서 i 제외).
  코퓰러 식: Nelsen (2006) An Introduction to Copulas · Joe (1997) Multivariate Models and Dependence Concepts · 가우스 CDF 는 Owen (1956) T 함수.

🚨 이 모듈은 selftest · dry 에서 규칙 · 대조 · 팔 · 위약의 수익을 계산하거나 찍지 않는다. run() 은 한 번 굽기에서만 부른다.
🚨 편입별 LTD 추정치(신호 · 성과 아님)는 $TEMP/qbatch/q_ltd_cache/<추정기 해시>/ 에 «입력 수익 바이트 + 추정기 원문 해시 + numpy/scipy 판» 열쇠로 둔다.
   추정기 구간(▼▼ ~ ▲▲)을 한 글자라도 고치면 해시가 바뀌어 다시 계산한다.
"""
from __future__ import annotations
import hashlib, io, json, math, os, pickle, subprocess, sys, tempfile, time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, ndtri, owens_t
from scipy.stats import kendalltau, rankdata, spearmanr

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q              # noqa: E402

CARDS = {"Q07": {"cls": "B", "slot": "B2"}}
NPERM = 1000                         # C2 위약 횟수(카드) — 연기 시험에서 작게 덮어쓴다
NPROC = 3                            # 코퓰러 적합 일꾼 수(다른 작업과 CPU 를 나눈다 · 결과는 일꾼 수와 무관)

# ── 카드 상수 ─────────────────────────────────────────────────────────────
POOL, DROP = 45, 15                  # Eg 상위 45 → 15 빼기(EGBEST C2 선례)
WIN, MIN_PAIRS = 252, 200            # 252일 창 · 유효 짝 최소
U_NP = 0.05                          # A3 비모수 LTD 의 u
CAP = 0.20                           # 발행사 상한(V0 와 같다)
COST20 = 0.0020                      # 20bp 판
VARIANTS = ("V1", "C3", "A1", "A2", "A3", "A4")

# ▼▼ 추정기 — 이 구간의 원문이 캐시 열쇠(EST_HASH)에 들어간다 ─────────────
N_START = 3                          # L-BFGS-B 씨앗 시작 수(카드)
START_SEED = 20260925                # 시작 씨앗 20260925 + s(카드)
# 결정적 시작 1개(검토 수정 · 카드 수정 필요): 무게 같게(a1 = a2 = 0) · 각 성분 θ = 그 족 하나만의 최우값.
#   씨앗 셋만으로는 무게가 0 으로 가며 θ 기울기가 사라지는 평원에 자주 멈춘다(혼합 64 × 단위 3688 중 최고와 1e-3 안 22.5%).
SG_N = 40                            # 단일 족 최우 — σ 좌표 등간격 격자 (j + ½)/40 에서 최대 뒤 이웃 구간 유계 Brent
SG_XATOL = 1e-6                      # 그 Brent 허용오차(변환 좌표)
NEAR_TOL = 1e-3                      # «같은 최적» = 로그우도 차 < 1e-3 (시작 진단 · 기록만)
# 구현 상수(카드가 정하지 않은 수치 한계 — 선언):
X_GUARD = 30.0                       # 변환 좌표 상자 ±30(σ(±30) ≈ 1e-13 — 한도에 사실상 닿은 값 · 넘침 방지)
H_GRAD = 1e-5                        # θ 좌표 중앙 차분 걸음(a1 · a2 는 해석 기울기)
H_HESS = 1e-4                        # 델타법 헤시안 차분 걸음
BOUND_TOL = 1e-6                     # «한도에 닿음» = σ(x) < 1e-6 또는 > 1 − 1e-6
W_TOL = 1e-6                         # «무게 0» 표식
FRANK_EPS = 1e-6                     # Frank 급수 전개 구간(카드)
LN2 = math.log(2.0)


def _views(u, v):
    """코퓰러 식이 쓰는 점별 변환 (V: (u, v) · Vr: (1−u, 1−v)) — 한 번 만들어 모든 혼합이 같이 쓴다.
    Vr 의 로그는 V 의 log u ↔ log1p(−u) 를 맞바꿔 만든다(1 − u 를 뺄셈으로 만들면 u → 0 에서 정밀도를 잃는다)."""
    u, v = np.asarray(u, float), np.asarray(v, float)
    lu, lv, l1u, l1v = np.log(u), np.log(v), np.log1p(-u), np.log1p(-v)
    za, zb = ndtri(u), ndtri(v)
    ab, zz, z2, p1 = u + v - 2 * u * v, za * zb, za * za + zb * zb, (1 - 2 * u) * (1 - 2 * v)
    V = {"u": u, "v": v, "lu": lu, "lv": lv, "l1u": l1u, "l1v": l1v, "x": -lu, "y": -lv, "lx": np.log(-lu), "ly": np.log(-lv),
         "za": za, "zb": zb, "zz": zz, "z2": z2, "ab": ab, "dv": u - v, "p1": p1, "q1": (1 - u) * (1 - v)}
    Vr = {"u": 1 - u, "v": 1 - v, "lu": l1u, "lv": l1v, "l1u": lu, "l1v": lv, "x": -l1u, "y": -l1v,
          "lx": np.log(-l1u), "ly": np.log(-l1v), "za": -za, "zb": -zb, "zz": zz, "z2": z2, "ab": ab, "dv": v - u, "p1": p1,
          "q1": u * v}
    return V, Vr


# Clayton — C = (u^-θ + v^-θ − 1)^(-1/θ) · 로그 공간(θ = 50 · θ = 1e-4 모두 정확)
def _clay_L(V, th):
    a, b = -th * V["lu"], -th * V["lv"]
    mx, mn = np.maximum(a, b), np.minimum(a, b)
    with np.errstate(over="ignore", invalid="ignore"):
        t = np.where(mn < 700.0, np.exp(-mx) * np.expm1(np.minimum(mn, 700.0)), np.exp(mn - mx) - np.exp(-mx))
    return mx + np.log1p(t)                                  # log(u^-θ + v^-θ − 1)


def clay_lpdf(V, th):
    return np.log1p(th) - (1 + th) * (V["lu"] + V["lv"]) - (2 + 1 / th) * _clay_L(V, th)


def clay_cdf(V, th):
    lc = -_clay_L(V, th) / th
    return np.exp(lc), -np.expm1(lc)


# Gumbel — C = exp(−A^(1/θ)) · A = x^θ + y^θ · x = −ln u
def _gum_A(V, th):
    lx, ly = V["lx"], V["ly"]
    logA = th * np.maximum(lx, ly) + np.log1p(np.exp(-th * np.abs(lx - ly)))
    return logA, np.exp(logA / th)


def gum_lpdf(V, th):
    logA, A1 = _gum_A(V, th)
    return -A1 + V["x"] + V["y"] + (th - 1) * (V["lx"] + V["ly"]) + (2 / th - 2) * logA + np.log1p((th - 1) / A1)


def gum_cdf(V, th):
    _, A1 = _gum_A(V, th)
    return np.exp(-A1), -np.expm1(-A1)


# Joe — C = 1 − D^(1/θ) · D = p + q − pq · p = (1−u)^θ (D 가 1 가까우면 log1p, 작으면 로그합)
def _joe_D(V, th):
    lp, lq = th * V["l1u"], th * V["l1v"]
    p = np.exp(lp)
    omp, omq = -np.expm1(lp), -np.expm1(lq)
    D = p + np.exp(lq) * omp
    with np.errstate(divide="ignore", invalid="ignore"):
        big = np.log1p(-omp * omq)
        small = np.logaddexp(lp, lq + np.log(omp))
    return np.where(D > 0.5, big, small), D


def joe_lpdf(V, th):
    logD, D = _joe_D(V, th)
    return (1 / th - 2) * logD + (th - 1) * (V["l1u"] + V["l1v"]) + np.log(th - 1 + D)


def joe_cdf(V, th):
    logD, _ = _joe_D(V, th)
    e = logD / th
    return -np.expm1(e), np.exp(e)


# Galambos — C = uv·exp(B) · B = (x^-θ + y^-θ)^(-1/θ) · c = C/(uv)·[(1 − B_x)(1 − B_y) + B_xy]
def _gal_B(V, th):
    lx, ly = V["lx"], V["ly"]
    d = lx - ly
    logS = -th * np.minimum(lx, ly) + np.log1p(np.exp(-th * np.abs(d)))
    return np.exp(-logS / th), expit(-th * d), expit(th * d)


def _softplus(z):
    return np.maximum(z, 0.0) + np.log1p(np.exp(-np.abs(z)))


def gal_lpdf(V, th):
    """1 − B_x = −expm1(−(1+θ)/θ · softplus(θ(ln x − ln y))) — 둘 다 양수 항의 합이라 상쇄가 없다(θ = 50 근처 포함)."""
    lx, ly = V["lx"], V["ly"]
    d = lx - ly
    spx, spy = _softplus(th * d), _softplus(-th * d)                  # −log r_x · −log r_y
    logS = -th * np.minimum(lx, ly) + np.log1p(np.exp(-th * np.abs(d)))
    lB = -logS / th
    B = np.exp(lB)
    k = (1 + th) / th
    cross = np.exp(np.log1p(th) + lB - spx - spy - lx - ly)          # (1+θ) B r_x r_y / (x y)
    return B + np.log(-np.expm1(-k * spx) * -np.expm1(-k * spy) + cross)


def gal_cdf(V, th):
    B, _, _ = _gal_B(V, th)
    lc = -V["x"] - V["y"] + B
    return np.exp(lc), -np.expm1(lc)


# Gauss — 밀도 닫힌 꼴 · CDF = Owen T(Φ2(h,k;ρ) = ½Φ(h) + ½Φ(k) − T(h,a_h) − T(k,a_k) − β)
def gau_lpdf(V, r):
    r2 = r * r
    return -0.5 * np.log1p(-r2) - (r2 * V["z2"] - 2 * r * V["zz"]) / (2 * (1 - r2))


def gau_cdf(V, r):
    za, zb = V["za"], V["zb"]
    s = np.sqrt(1 - r * r)
    with np.errstate(divide="ignore", invalid="ignore"):
        ah = (zb - r * za) / (za * s)
        ak = (za - r * zb) / (zb * s)
        T = owens_t(za, ah) + owens_t(zb, ak)
    beta = np.where((V["zz"] < 0) | ((V["zz"] == 0) & (za + zb < 0)), 0.5, 0.0)
    C = 0.5 * (V["u"] + V["v"]) - T - beta
    C = np.where((za == 0) & (zb == 0), 0.25 + np.arcsin(r) / (2 * math.pi), C)
    return C, 1 - C


# Frank — |θ| < 1e-6 은 1차 급수(C = uv(1 + θ/2 (1−u)(1−v))) · θ > 1 은 K = log(a + b − ab − c)(a = e^−θu · c = e^−θ)를
#   −θ min(u,v) + log(1 + e^−θ|u−v| − e^−θ max(u,v) − e^−θ(1−min(u,v))) 로(괄호 ≥ 1 − e^−θ · 상쇄 없음) · 그 밖은 expm1 직접 꼴(상쇄 없음)
def _fra_K(V, ts):
    u, v = V["u"], V["v"]
    em, eu, ev = np.expm1(-ts), np.expm1(-ts * u), np.expm1(-ts * v)
    lo, hi = np.minimum(u, v), np.maximum(u, v)
    with np.errstate(divide="ignore", invalid="ignore"):
        direct = np.log(np.abs(-em - eu * ev))
        brk = -ts * lo + np.log(1 + np.exp(-ts * (hi - lo)) - np.exp(-ts * hi) - np.exp(-ts * (1 - lo)))
    return np.where(ts > 1.0, brk, direct), em, eu, ev


def fra_lpdf(V, th):
    th = np.asarray(th, float)
    sm = np.abs(th) < FRANK_EPS
    ts = np.where(sm, 1.0, th)
    K, em, _, _ = _fra_K(V, ts)
    full = np.log(ts * (-em)) - ts * (V["u"] + V["v"]) - 2 * K
    with np.errstate(invalid="ignore"):
        ser = np.log1p(0.5 * np.where(sm, th, 0.0) * V["p1"])
    return np.where(sm, ser, full)


def fra_cdf(V, th):
    th = np.asarray(th, float)
    sm = np.abs(th) < FRANK_EPS
    ts = np.where(sm, 1.0, th)
    K, em, eu, ev = _fra_K(V, ts)
    with np.errstate(divide="ignore", invalid="ignore"):
        direct = -np.log1p(eu * ev / em) / ts
        brk = -(K - np.log(-em)) / ts
    C = np.where(sm, V["u"] * V["v"] * (1 + 0.5 * np.where(sm, th, 0.0) * V["q1"]), np.where(ts > 1.0, brk, direct))
    return C, 1 - C


# FGM — C = uv(1 + θ(1−u)(1−v))
def fgm_lpdf(V, th):
    return np.log1p(th * V["p1"])


def fgm_cdf(V, th):
    C = V["u"] * V["v"] * (1 + th * V["q1"])
    return C, 1 - C


# Plackett — Q = 1 + 2(θ−1)(u+v−2uv) + (θ−1)²(u−v)² (= S² − 4θ(θ−1)uv · 상쇄 없는 꼴)
def pla_lpdf(V, th):
    t1 = th - 1
    Qd = 1 + 2 * t1 * V["ab"] + t1 * t1 * V["dv"] * V["dv"]
    return np.log(th) + np.log1p(t1 * V["ab"]) - 1.5 * np.log(Qd)


def pla_cdf(V, th):
    t1 = th - 1
    u, v = V["u"], V["v"]
    sq = np.sqrt(1 + 2 * t1 * V["ab"] + t1 * t1 * V["dv"] * V["dv"])
    Sm = 1 + t1 * (u + v)
    with np.errstate(divide="ignore", invalid="ignore"):
        A_ = (Sm - sq) / (2 * t1)                            # Sm < 0 (θ < 1) 일 때 — 상쇄 없음
    C = np.where(Sm >= 0, 2 * th * u * v / (Sm + sq), A_)
    return C, 1 - C


def lam_pow(th):
    """2^(−1/θ) — Clayton λ_L · Galambos λ_U."""
    return np.exp(-LN2 / np.asarray(th, float))


def lam_gum(th):
    """2 − 2^(1/θ) — Gumbel · Joe λ_U (θ = 1 에서 정확히 0)."""
    return -2.0 * np.expm1((1.0 / np.asarray(th, float) - 1.0) * LN2)


# 족 표 — 회전(180°)은 C_r(u,v) = u + v − 1 + C(1−u, 1−v) · c_r(u,v) = c(1−u, 1−v) · λ_L(회전) = λ_U(원)
BASE = {"clayton": (clay_lpdf, clay_cdf), "gumbel": (gum_lpdf, gum_cdf), "joe": (joe_lpdf, joe_cdf), "galambos": (gal_lpdf, gal_cdf),
        "gauss": (gau_lpdf, gau_cdf), "frank": (fra_lpdf, fra_cdf), "fgm": (fgm_lpdf, fgm_cdf), "plackett": (pla_lpdf, pla_cdf)}
FAM = {   # 이름: (원족, 회전, 하한, 상한, 변환, λ_L, λ_U)
    "clayton":   ("clayton", False, 1e-4, 50.0, "log", lam_pow, None),
    "rgumbel":   ("gumbel", True, 1.0, 50.0, "log", lam_gum, None),
    "rjoe":      ("joe", True, 1.0, 50.0, "log", lam_gum, None),
    "rgalambos": ("galambos", True, 1e-4, 50.0, "log", lam_pow, None),
    "gauss":     ("gauss", False, -0.999, 0.999, "lin", None, None),
    "frank":     ("frank", False, -50.0, 50.0, "lin", None, None),
    "fgm":       ("fgm", False, -1.0, 1.0, "lin", None, None),
    "plackett":  ("plackett", False, 1e-3, 1e3, "log", None, None),
    "gumbel":    ("gumbel", False, 1.0, 50.0, "log", None, lam_gum),
    "joe":       ("joe", False, 1.0, 50.0, "log", None, lam_gum),
    "galambos":  ("galambos", False, 1e-4, 50.0, "log", None, lam_pow),
    "rclayton":  ("clayton", True, 1e-4, 50.0, "log", None, lam_pow),
}
C_L = ("clayton", "rgumbel", "rjoe", "rgalambos")
C_N = ("gauss", "frank", "fgm", "plackett")
C_U = ("gumbel", "joe", "galambos", "rclayton")
MIXES = [(a, b, c) for a in C_L for b in C_N for c in C_U]  # 64 · CRW 표기 1-A-I … 4-D-IV
_ROM = ("I", "II", "III", "IV")


def mix_label(j):
    return "%d-%s-%s" % (j // 16 + 1, "ABCD"[(j // 4) % 4], _ROM[j % 4])


def th_of(name, x):
    """변환 좌표 x → θ — «log»: log θ = log lo + (log hi − log lo)σ(x) · «lin»: θ = lo + (hi − lo)σ(x)."""
    _, _, lo, hi, tr, _, _ = FAM[name]
    s = expit(np.asarray(x, float))
    if tr == "log":
        return np.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * s)
    return lo + (hi - lo) * s


def fam_lpdf(name, V, Vr, th):
    base, rot = FAM[name][0], FAM[name][1]
    return BASE[base][0](Vr if rot else V, th)


def fam_cdf(name, V, Vr, th):
    """(C, 1 − C) — 회전은 C_r = u + v − (1 − C(ū,v̄)) · 1 − C_r = (ū + v̄) − C(ū,v̄)."""
    base, rot = FAM[name][0], FAM[name][1]
    if not rot:
        return BASE[base][1](V, th)
    Cb, Sb = BASE[base][1](Vr, th)
    return V["u"] + V["v"] - Sb, Vr["u"] + Vr["v"] - Cb


def _lse3(a, b, c):
    m = np.maximum(np.maximum(a, b), c)
    with np.errstate(invalid="ignore"):
        return m + np.log(np.exp(a - m) + np.exp(b - m) + np.exp(c - m))


def _logw(a1, a2):
    z = np.array([a1, a2, 0.0])
    mz = z.max()
    return z - (mz + math.log(np.exp(z - mz).sum()))


class Mix:
    """혼합 하나의 로그우도 · 기울기(a1 · a2 해석 · θ 좌표 중앙 차분을 한 번에 묶어 계산)."""

    def __init__(self, names, V, Vr):
        self.names, self.V, self.Vr = names, V, Vr
        self.nfev = self.nbad = 0

    def comp(self, k, xs):
        nm = self.names[k]
        return fam_lpdf(nm, self.V, self.Vr, th_of(nm, np.asarray(xs, float))[:, None])

    def fg(self, psi):
        self.nfev += 1
        lw = _logw(psi[0], psi[1])
        st = np.array([0.0, H_GRAD, -H_GRAD])
        L = [self.comp(k, psi[2 + k] + st) for k in range(3)]
        B = [lw[k] + L[k][0] for k in range(3)]
        M0 = _lse3(*B)
        ll = float(M0.sum())
        if not np.isfinite(ll):
            self.nbad += 1
            return 1e12, np.zeros(5)
        g = np.empty(5)
        R = [np.exp(B[k] - M0) for k in range(3)]            # 책임도 w_k c_k / c
        w = np.exp(lw)
        for j in range(2):                                   # ∂ℓ/∂a_j = Σ w_j (c_j / c − 1)
            g[j] = float((R[j] - w[j]).sum())
        with np.errstate(invalid="ignore", divide="ignore"):
            for k in range(3):                               # ℓ(x_k ± h) − ℓ = Σ log1p(w_k c_k± / c − R_k)
                dp = np.log1p(np.exp(lw[k] + L[k][1] - M0) - R[k]).sum()
                dm = np.log1p(np.exp(lw[k] + L[k][2] - M0) - R[k]).sum()
                g[2 + k] = float(dp - dm) / (2 * H_GRAD)
        if not np.all(np.isfinite(g)):
            self.nbad += 1
            return 1e12, np.zeros(5)
        return -ll, -g

    def ll(self, psi):
        lw = _logw(psi[0], psi[1])
        return float(_lse3(*[lw[k] + self.comp(k, [psi[2 + k]])[0] for k in range(3)]).sum())

    def params(self, psi):
        w = np.exp(_logw(psi[0], psi[1]))
        th = [float(th_of(self.names[k], psi[2 + k])) for k in range(3)]
        return w, th

    def bounds_hit(self, psi):
        s = expit(np.asarray(psi[2:], float))
        return [self.names[k] for k in range(3) if s[k] < BOUND_TOL or s[k] > 1 - BOUND_TOL]


def starts():
    """씨앗 시작점 s = 0,1,2 — default_rng(20260925 + s) 의 표준정규 5개(a1, a2, x1, x2, x3) · 모든 적합에 같다."""
    return [np.random.default_rng(START_SEED + s).standard_normal(5) for s in range(N_START)]


def single_mle(name, V, Vr):
    """한 족만의 최우(1차원 · 변환 좌표) — σ 격자 (j + ½)/SG_N 에서 ℓ 최대 j → [x_{j−1}, x_{j+1}] 유계 Brent(끝 칸은 ±X_GUARD 까지).
    Brent 가 격자보다 나쁘면 격자 점. 돌려준다 (x̂, ℓ̂)."""
    from scipy.optimize import minimize_scalar
    xs = np.log((np.arange(SG_N) + 0.5) / (SG_N - np.arange(SG_N) - 0.5))       # logit((j + ½)/N)
    with np.errstate(all="ignore"):
        ll = fam_lpdf(name, V, Vr, th_of(name, xs)[:, None]).sum(axis=1)
    ll = np.where(np.isfinite(ll), ll, -np.inf)
    j = int(np.argmax(ll))
    if not np.isfinite(ll[j]):
        return 0.0, -np.inf
    a = xs[j - 1] if j > 0 else -X_GUARD
    b = xs[j + 1] if j < SG_N - 1 else X_GUARD

    def f(x):
        with np.errstate(all="ignore"):
            v = float(fam_lpdf(name, V, Vr, th_of(name, np.array([x]))[:, None]).sum())
        return -v if np.isfinite(v) else 1e300
    r = minimize_scalar(f, bounds=(a, b), method="bounded", options={"xatol": SG_XATOL})
    if np.isfinite(r.fun) and -float(r.fun) > ll[j]:
        return float(r.x), -float(r.fun)
    return float(xs[j]), float(ll[j])


def det_start(names, sx):
    """결정적 시작 — 무게 같게(a1 = a2 = 0) · x_k = 성분 k 족 하나만의 최우 x̂."""
    return np.array([0.0, 0.0] + [sx[nm][0] for nm in names], float)


def fit_mix(names, V, Vr, X0=None):
    """정준 최우 — L-BFGS-B(scipy 기본 허용오차) · 시작 = 씨앗 3(카드) + 결정적 1 · 로그우도 최대(동률은 앞 시작).
    X0 가 없으면 이 혼합의 세 족 단일 최우로 결정적 시작을 만든다."""
    M = Mix(names, V, Vr)
    if X0 is None:
        X0 = starts() + [det_start(names, {nm: single_mle(nm, V, Vr) for nm in names})]
    best = None
    nfail = 0
    lls = []
    for x0 in X0:
        try:
            r = minimize(M.fg, x0, jac=True, method="L-BFGS-B", bounds=[(-X_GUARD, X_GUARD)] * 5)
        except Exception:
            nfail += 1
            lls.append(None)
            continue
        llv = -float(r.fun)
        if not np.isfinite(llv) or llv <= -1e11:
            nfail += 1
            lls.append(None)
            continue
        lls.append(llv)
        if best is None or llv > best[0] + 1e-12:
            best = (llv, np.array(r.x, float), bool(r.success))
    if best is None:
        return {"ok": False, "nfev": M.nfev, "nfail": nfail, "nbad": M.nbad}
    w, th = M.params(best[1])
    ok_ll = sorted([x for x in lls if x is not None], reverse=True)
    return {"ok": True, "ll": best[0], "psi": best[1], "w": w, "th": th, "conv": best[2], "bound": M.bounds_hit(best[1]),
            "w0": [names[k] for k in range(3) if w[k] < W_TOL], "nfev": M.nfev, "nfail": nfail, "nbad": M.nbad, "M": M,
            "ll_starts": lls, "n_near": int(sum(1 for x in ok_ll if x >= best[0] - NEAR_TOL)),
            "gap12": (float(ok_ll[0] - ok_ll[1]) if len(ok_ll) > 1 else None),
            "best_start": int(next(j for j, x in enumerate(lls) if x is not None and x == best[0]))}


_GRID = {}


def grid(n):
    """격자 (a/n, b/n) · a,b = 1..n−1 의 위 삼각(대칭 코퓰러 · a ≤ b) · 가장자리(a 또는 b = n)는 모든 혼합에 같은 C(1,v) = v."""
    if n in _GRID:
        return _GRID[n]
    g = np.arange(1, n) / n
    ia, ib = np.triu_indices(n - 1)
    u, v = g[ia], g[ib]
    out = {"n": n, "ia": ia, "ib": ib, "md": (ia != ib).astype(float), "V": None, "Vr": None}
    out["V"], out["Vr"] = _views(u, v)
    if len(_GRID) >= 3:
        _GRID.pop(next(iter(_GRID)))
    _GRID[n] = out
    return out


def emp_copula(R, S, n):
    """Deheuvels(1981) — Ĉ(a/n, b/n) = (1/n)#{R ≤ a, S ≤ b} · a,b = 1..n (CRW 식 8)."""
    H = np.zeros((n, n))
    np.add.at(H, (np.asarray(R, int) - 1, np.asarray(S, int) - 1), 1.0)
    return H.cumsum(0).cumsum(1) / n


def iad_const(E, n):
    """가장자리 행 · 열의 IAD 몫 — C(1, b/n) = b/n 이 모든 코퓰러에 같다 · (n, n) 칸은 0/0 := 0."""
    b = np.arange(1, n) / n
    den = b * (1 - b)
    return float((((E[n - 1, :n - 1] - b) ** 2 + (E[:n - 1, n - 1] - b) ** 2) / den).sum())


def iad(Gd, E1, E2, C, S):
    """CRW 식 (9) 의 안쪽 칸 합 — 위 삼각 대칭을 써서 한 번에(Ĉ 는 비대칭 · C 는 대칭)."""
    num = (E1 - C) ** 2 + np.where(Gd["md"] > 0, (E2 - C) ** 2, 0.0)
    den = C * S
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(den > 0, num / den, np.where(num > 0, np.inf, 0.0))
    return float(t.sum())


def comp_lattice(name, Gd, th):
    return fam_cdf(name, Gd["V"], Gd["Vr"], np.asarray(th, float))


def hessian_se(M, psi):
    """델타법 — SE = √(∇LTD' H⁺ ∇LTD) · H = −∇²ℓ(관측 정보 · 변환 좌표 · 중앙 차분) · ∇LTD 는 중앙 차분 ·
    H⁺ = 식별되는 방향만의 역(무어-펜로즈) — 양의 고유값이 하나도 없으면 None."""
    k = len(psi)
    h = H_HESS
    f0 = M.ll(psi)
    Hm = np.zeros((k, k))
    fp = [M.ll(psi + h * np.eye(k)[i]) for i in range(k)]
    fm = [M.ll(psi - h * np.eye(k)[i]) for i in range(k)]
    for i in range(k):
        Hm[i, i] = (fp[i] - 2 * f0 + fm[i]) / (h * h)
        for j in range(i + 1, k):
            ei, ej = h * np.eye(k)[i], h * np.eye(k)[j]
            v = (M.ll(psi + ei + ej) - M.ll(psi + ei - ej) - M.ll(psi - ei + ej) + M.ll(psi - ei - ej)) / (4 * h * h)
            Hm[i, j] = Hm[j, i] = v
    info = -Hm
    lamL = FAM[M.names[0]][5]

    def ltd(p):
        w, th = M.params(p)
        return float(w[0] * lamL(th[0]))
    g = np.zeros(k)
    for i in range(k):
        e = 1e-6 * np.eye(k)[i]
        g[i] = (ltd(psi + e) - ltd(psi - e)) / 2e-6
    # 무게 0 성분의 θ 처럼 식별되지 않는 방향(고유값 ≤ 1e-8·최대 · 음수 포함)은 뺀다 = 무어-펜로즈 역(기록 se_pinv:뺀 수)
    ev, U = np.linalg.eigh(0.5 * (info + info.T))
    if not np.all(np.isfinite(ev)) or ev.max() <= 0:
        return None, "se_nopd"
    keep = ev > 1e-8 * ev.max()
    z = U[:, keep].T @ g
    se = float(math.sqrt(float(np.sum(z * z / ev[keep]))))
    return se, (None if keep.all() else "se_pinv:%d" % int((~keep).sum()))


def margins(ri, rm):
    """CRW 식 (6) — F̂(x) = #{r ≤ x}/(n + 1) · 동률은 최대 순위(식 그대로)."""
    R, S = rankdata(ri, method="max").astype(int), rankdata(rm, method="max").astype(int)
    return R, S


def fit_unit(ri, rm, keep_all=True):
    """한 종목 · 한 편입 — 64 혼합 정준 최우 → IAD 최소 선택 → LTD · UTD · SE."""
    t0 = time.time()
    ri, rm = np.asarray(ri, float), np.asarray(rm, float)
    n = len(ri)
    R, S = margins(ri, rm)
    u, v = R / (n + 1.0), S / (n + 1.0)
    V, Vr = _views(u, v)
    E = emp_copula(R, S, n)
    Gd = grid(n)
    E1, E2 = E[Gd["ia"], Gd["ib"]], E[Gd["ib"], Gd["ia"]]
    K = iad_const(E, n)
    S0 = starts()
    sx = {nm: single_mle(nm, V, Vr) for nm in FAM}              # 12 족 단일 최우(결정적 시작 재료)
    lls, Ds, fits = [], [], []
    nfev = nfail = nbound = nbad = nnc = 0
    near, bst = [], []
    for names in MIXES:
        f = fit_mix(names, V, Vr, S0 + [det_start(names, sx)])
        nfev += f["nfev"]; nfail += f["nfail"]; nbad += f["nbad"]
        if not f["ok"]:
            lls.append(None); Ds.append(None); fits.append(None)
            continue
        nbound += bool(f["bound"])
        nnc += not f["conv"]
        near.append(f["n_near"]); bst.append(f["best_start"])
        Cm = np.zeros(len(E1)); Sm = np.zeros(len(E1))
        for kk in range(3):
            Ck, Sk = comp_lattice(names[kk], Gd, f["th"][kk])
            Cm += f["w"][kk] * Ck; Sm += f["w"][kk] * Sk
        lls.append(f["ll"]); Ds.append(iad(Gd, E1, E2, Cm, Sm) + K); fits.append(f)
    ok = [j for j in range(64) if Ds[j] is not None and np.isfinite(Ds[j])]
    if not ok:
        return {"n": n, "ok": False, "nfev": nfev, "nfail": nfail, "sec": round(time.time() - t0, 2)}
    js = min(ok, key=lambda j: (Ds[j], j))
    f = fits[js]
    names = MIXES[js]
    ltd = float(f["w"][0] * FAM[names[0]][5](f["th"][0]))
    utd = float(f["w"][2] * FAM[names[2]][6](f["th"][2]))
    se, sef = hessian_se(f["M"], f["psi"])
    flags = [x for x in (sef,) if x] + (["sel_bound:" + "+".join(f["bound"])] if f["bound"] else []) + \
            (["sel_w0:" + "+".join(f["w0"])] if f["w0"] else []) + ([] if f["conv"] else ["sel_nonconv"])
    Dk = sorted(Ds[j] for j in ok)
    out = {"n": n, "ok": True, "sel": js, "label": mix_label(js), "fams": list(names), "w": [float(x) for x in f["w"]],
           "th": [float(x) for x in f["th"]], "psi": [float(x) for x in f["psi"]], "ll": f["ll"], "D": Ds[js],
           "ltd": ltd, "utd": utd, "se": se, "flags": flags, "n_bound": nbound, "n_nonconv": nnc, "ll_starts": f["ll_starts"],
           # 시작 진단(기록만): 선택 혼합의 1e-3 안 시작 수 · 최고 − 둘째 · 이긴 시작(0..2 씨앗 · 3 결정적) · 64 혼합 평균
           "n_near": f["n_near"], "gap12": f["gap12"], "best_start": f["best_start"],
           "near_mean_all": float(np.mean(near)), "det_best_share_all": float(np.mean([b == N_START for b in bst])),
           "D_gap_rel": (float((Dk[1] - Dk[0]) / Dk[0]) if len(Dk) > 1 and Dk[0] > 0 else None),
           "nfev": nfev, "nfail": nfail, "nbad": nbad,
           "ties": [int(n - len(np.unique(ri))), int(n - len(np.unique(rm)))], "sec": round(time.time() - t0, 2)}
    if keep_all:
        out["ll_all"] = lls
        out["D_all"] = Ds
    return out
# ▲▲ 추정기 끝 ───────────────────────────────────────────────────────────


def _est_hash():
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read().replace("\r\n", "\n")
    a, b = src.index("# ▼▼ 추정기"), src.index("# ▲▲ 추정기 끝")
    import scipy
    return hashlib.sha256((src[a:b] + "|np" + np.__version__ + "|sp" + scipy.__version__).encode("utf-8")).hexdigest()


EST_HASH = _est_hash()
CACHE_ROOT = os.path.join(os.environ.get("TEMP") or tempfile.gettempdir(), "qbatch", "q_ltd_cache")
CACHE = os.path.join(CACHE_ROOT, EST_HASH[:16])
# 얼린 적합(검토 수정 — 굽기의 재현을 %TEMP% 캐시에 기대지 않는다): 랩 단위 3688 의 지문 · 묶음 파일 위치(있으면 캐시 대신)
FITS_MANIFEST = "d89f00d2a7fc501251bd0c8a0112b8a01bf64d810e0741ad1abeca60c2fb7655"   # 2026-09-25 dry(추정기 d150aaab6bf03115 · 5 일꾼 · 3820초) — run 은 이 값과 다르면 멈춘다
FITS_N = 3688
FITS_FILE = os.environ.get("Q07_FITS") or os.path.join(Q.DATA, "_q07_ltd_fits.json")


def unit_key(ri, rm):
    h = hashlib.sha256(EST_HASH.encode("ascii"))
    h.update(np.ascontiguousarray(ri, dtype=np.float64).tobytes())
    h.update(b"|")
    h.update(np.ascontiguousarray(rm, dtype=np.float64).tobytes())
    return h.hexdigest()


def _cpath(key):
    return os.path.join(CACHE, key[:2], key + ".json")


def cache_get(key):
    p = _cpath(key)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def cache_put(key, res):
    p = _cpath(key)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".%d.tmp" % os.getpid()
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(res, allow_nan=True))
    os.replace(tmp, p)


def _worker(pack_path):
    """하위 프로세스 — 맡은 단위를 적합해 캐시에 쓴다(이미 있으면 건너뛴다)."""
    units = pickle.load(open(pack_path, "rb"))
    for key, ri, rm in units:
        if cache_get(key) is not None:
            continue
        cache_put(key, fit_unit(ri, rm))


def manifest(fits):
    """적합 묶음의 지문 — 열쇠 정렬 순서로 «열쇠 + json(결과 · 키 정렬)» 의 sha256. 캐시 폴더든 묶음 파일이든 같은 값."""
    h = hashlib.sha256()
    for k in sorted(fits):
        h.update(k.encode("ascii") + b"\n")
        h.update(json.dumps(fits[k], sort_keys=True, allow_nan=True).encode("utf-8") + b"\n")
    return h.hexdigest()


def _pinned():
    """얼린 묶음 파일(있으면) — {열쇠: 결과}. 없으면 None(캐시 폴더를 쓴다)."""
    p = FITS_FILE
    if not p or not os.path.exists(p):
        return None
    d = json.load(io.open(p, encoding="utf-8"))
    assert d.get("est_hash") == EST_HASH, "q_ltd 묶음 파일의 추정기 해시가 다르다(%s)" % p
    return d["fits"]


def export_fits(fits, path):
    """캐시 → 묶음 파일 하나(P3 고정용 · 러너가 FITS_FILE 로 읽는다)."""
    d = {"est_hash": EST_HASH, "manifest": manifest(fits), "n": len(fits), "fits": {k: fits[k] for k in sorted(fits)}}
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, sort_keys=True, allow_nan=True))
    os.replace(tmp, path)
    return d["manifest"]


def estimate(units, nproc=None, verbose=True, strict=False):
    """units = [(key, r_i, r_m)] → {key: 결과} · 캐시에 없는 것만 일꾼 nproc 개로(BLAS 1스레드) · 일꾼이 죽으면 여기서 이어 한다.
    strict(run 의 랩 단위): 다시 적합하지 않는다 — 얼린 묶음 파일(FITS_FILE) 또는 캐시에 전부 있고 지문이 FITS_MANIFEST 와 같아야 한다."""
    nproc = NPROC if nproc is None else nproc
    if strict:
        pin = _pinned()
        keys = sorted({k for k, _, _ in units})
        src = "file" if pin is not None else "cache"
        out = {k: (pin.get(k) if pin is not None else cache_get(k)) for k in keys}
        miss = [k for k in keys if out[k] is None]
        assert not miss, "q_ltd: 적합이 없는 단위 %d/%d(%s) — run() 은 다시 적합하지 않는다(dry 로 채우고 지문을 얼린다)" % (len(miss), len(keys), src)
        mf = manifest(out)
        assert FITS_MANIFEST is not None and mf == FITS_MANIFEST, \
            "q_ltd: 적합 지문 %s ≠ 얼린 FITS_MANIFEST %s(%s) — 다른 기계 · 판에서 다시 적합된 캐시일 수 있다" % (mf[:16], (FITS_MANIFEST or "None")[:16], src)
        return out, {"units": len(keys), "todo": 0, "nproc": 0, "source": src, "manifest": mf, "sec": 0.0}
    todo = sorted({k: (k, a, b) for k, a, b in units if cache_get(k) is None}.values(), key=lambda x: x[0])
    t0 = time.time()
    stat = {"units": len({k for k, _, _ in units}), "todo": len(todo), "nproc": 0}
    if todo:
        d = tempfile.mkdtemp(prefix="q_ltd_")
        env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="0")
        procs, errs = [], []
        npr = max(1, min(nproc, len(todo)))
        for w in range(npr):
            part = todo[w::npr]
            pp = os.path.join(d, "pack%d.pkl" % w)
            with open(pp, "wb") as f:
                pickle.dump(part, f, protocol=pickle.HIGHEST_PROTOCOL)
            code = "import sys; sys.path.insert(0, %r); import q_ltd as M; M._worker(%r)" % (HERE, pp)
            errs.append(open(os.path.join(d, "err%d.txt" % w), "w", encoding="utf-8"))
            procs.append(subprocess.Popen([sys.executable, "-X", "utf8", "-c", code], env=env,
                                          stdout=subprocess.DEVNULL, stderr=errs[-1]))
        stat["nproc"] = npr
        last = 0.0
        while any(p.poll() is None for p in procs):
            time.sleep(2.0)
            if verbose and time.time() - last > 120:
                done = sum(1 for k, _, _ in todo if os.path.exists(_cpath(k)))
                print("  q_ltd 적합 %d/%d (%.0f초)" % (done, len(todo), time.time() - t0), flush=True)
                last = time.time()
        for e in errs:
            e.close()
        rest = [u for u in todo if cache_get(u[0]) is None]
        stat["serial"] = len(rest)
        if rest:
            stat["worker_err"] = [io.open(os.path.join(d, "err%d.txt" % w), encoding="utf-8", errors="replace").read()[-1500:]
                                  for w in range(npr)]
        for key, ri, rm in rest:
            cache_put(key, fit_unit(ri, rm))
    out = {k: cache_get(k) for k, _, _ in units}
    assert all(v is not None for v in out.values()), "q_ltd 캐시에 빈 단위가 남았다"
    stat["sec"] = round(time.time() - t0, 1)
    return out, stat


# ── 시장(M_−i) · 편입 준비 ────────────────────────────────────────────────
def formations(ctx):
    import eg30plus as E
    return E.formations(ctx.Wd)


def _cand():
    import eg30plus as E
    return dict(E.EG_BASE, index="union")


def _cik(Wd, t):
    cm = Wd.W["cikmap"]
    return cm.get(t) or cm.get((t or "").replace("-", ".")) or None


def pools(ctx):
    """편입월 → P(Eg 상위 45 · [(t, k)] · Eg 순)."""
    if getattr(ctx, "_q07_pools", None) is not None:
        return ctx._q07_pools
    Wd = ctx.Wd
    out = {}
    for m in formations(ctx):
        i = Wd.me[m]
        assert Wd.dates[i][:7] == m and (i + 1 >= len(Wd.dates) or Wd.dates[i + 1][:7] > m), "편입일이 %s 의 마지막 거래일이 아니다" % m
        sc = Wd.score(_cand(), m)
        P = [x for x, _ in sc[:POOL]]
        assert len(P) == POOL and len({k for _, k in P}) == POOL, "P 가 45 가 아니다(%s)" % m
        out[m] = P
    ctx._q07_pools = out
    return out


def build_market(dates, me, members, mcap, px, cik, keep_keys, keep_ciks, dA, dB, keep_ticks=frozenset()):
    """d ∈ [dA, dB] 의 시총가중 합 — 그날 명단 = d−1 이전 가장 가까운 월말 명단 · 비중 = mcap(t, k, d−1) · 수익 = px[d]/px[d−1] − 1.
    돌려준다: S[d] = Σ w r · W[d] = Σ w(유효한 이름만) · 제외용 몫 {k: (cw, cr)}(keep_keys · keep_ciks · keep_ticks 에 걸리는 이름만)
    · 이름 → cik · 이름 → 티커."""
    T = dB - dA + 1
    Ssum, Wsum = np.zeros(T), np.zeros(T)
    contrib, kcik, ktick = {}, {}, {}
    ms = sorted(m for m in me if me[m] < dB and (me.get(Q.mshift(m, 1), 10 ** 9) >= dA))
    cover = []
    for mm in ms:
        a, b = me[mm] + 1, min(dB, me.get(Q.mshift(mm, 1), dB))       # 수익일 d: d−1 ∈ [월말 mm, 다음 월말 − 1]
        a = max(a, dA)
        if a > b:
            continue
        mem = members(mm)
        nv = 0
        for t, k in mem:
            p = px(k)
            d = np.arange(a, b + 1)
            p0, p1 = p[d - 1], p[d]
            w = np.array([mcap(t, k, int(x) - 1) or np.nan for x in d], float)
            with np.errstate(divide="ignore", invalid="ignore"):
                r = p1 / p0 - 1.0
            ok = np.isfinite(r) & np.isfinite(w) & (w > 0) & (p0 > 0)
            if not ok.any():
                continue
            nv += 1
            j = d[ok] - dA
            Ssum[j] += w[ok] * r[ok]
            Wsum[j] += w[ok]
            c = cik(t)
            if k in keep_keys or (c is not None and c in keep_ciks) or t in keep_ticks:
                cw, cr = contrib.setdefault(k, (np.zeros(T), np.zeros(T)))
                cw[j] += w[ok]
                cr[j] += w[ok] * r[ok]
                kcik.setdefault(k, set()).add(c)
                ktick.setdefault(k, set()).add(t)
        cover.append((mm, len(mem), nv))
    return Ssum, Wsum, contrib, kcik, cover, ktick


def market(ctx):
    """M_−i 를 위한 시장 합(한 번 만든다)."""
    if getattr(ctx, "_q07_mkt", None) is not None:
        return ctx._q07_mkt
    import qg_lab as QL
    Wd = ctx.Wd
    P = pools(ctx)
    fm = formations(ctx)
    dB = max(Wd.me[m] for m in fm)
    dA = min(Wd.me[m] for m in fm) - WIN + 1
    keep_keys = {k for m in fm for _, k in P[m]}
    keep_ciks = {c for m in fm for t, _ in P[m] for c in [_cik(Wd, t)] if c}
    keep_ticks = frozenset(s for m in fm for t, _ in P[m] for s in SIBLINGS.get(t, ()))
    t0 = time.time()
    S, W, contrib, kcik, cover, ktick = build_market(Wd.dates, Wd.me, lambda mm: Wd.universe(mm, "union", False),
                                                     lambda t, k, d: QL.World.mcap(Wd, t, k, d), lambda k: Wd.PX[k],
                                                     lambda t: _cik(Wd, t), keep_keys, keep_ciks, dA, dB, keep_ticks)
    ctx._q07_mkt = {"dA": dA, "dB": dB, "S": S, "W": W, "contrib": contrib, "kcik": kcik, "ktick": ktick, "cover": cover,
                    "sec": round(time.time() - t0, 1)}
    return ctx._q07_mkt


# CIK 가 없는 이중클래스(cikmap 밖 — union_members 도 하나로 줄이지 못한다) · 같은 발행사 = M_−i 에서 함께 뺀다(CRW 각주 13).
#   union 명단 전체(2015-08..2026-06)에서 CIK 없는 29 티커 중 같은 발행사 쌍은 이것 하나(검토 탐침 · 선언).
SIBLINGS = {"LBTYA": ("LBTYK",), "LBTYK": ("LBTYA",)}


def mkt_excl(MK, k, c, d, t=None):
    """d(배열)의 M_−i — i 의 가격 키 k · cik c 가 같거나 · 선언된 같은 발행사 티커(SIBLINGS[t])인 명단 이름의 몫을 뺀다. 유효하지 않으면 NaN."""
    j = d - MK["dA"]
    S, W = MK["S"][j].copy(), MK["W"][j].copy()
    hit = []
    sib = set(SIBLINGS.get(t, ()))
    for kk, (cw, cr) in MK["contrib"].items():
        if kk == k or (c is not None and c in MK["kcik"].get(kk, ())) or (sib and sib & MK.get("ktick", {}).get(kk, set())):
            S -= cr[j]; W -= cw[j]
            hit.append(kk)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(W > 0, S / W, np.nan)
    return out, hit


def prep(ctx):
    """편입마다 P · 창 수익(시장 둘) · FP 베타 → 적합 단위 목록. 🚨 m 월말 종가(편입일 i)까지만 읽는다(단언)."""
    if getattr(ctx, "_q07_prep", None) is not None:
        return ctx._q07_prep
    Wd = ctx.Wd
    P = pools(ctx)
    MK = market(ctx)
    lpr = np.asarray(Wd.IX_PR, float)
    rows, units = {}, []
    for m in formations(ctx):
        i = Wd.me[m]
        d = np.arange(i - WIN + 1, i + 1)
        assert d[-1] == i and d[0] >= MK["dA"] and d[-1] <= MK["dB"], "창이 편입일 뒤를 읽는다(%s)" % m
        spx = lpr[d] / lpr[d - 1] - 1.0
        names = []
        for t, k in P[m]:
            p = np.asarray(Wd.PX[k], float)
            with np.errstate(divide="ignore", invalid="ignore"):
                ri = np.where((p[d - 1] > 0) & (p[d] > 0), p[d] / p[d - 1] - 1.0, np.nan)
            c = _cik(Wd, t)
            mx, hit = mkt_excl(MK, k, c, d, t)
            pw = p[d[0] - 1:i + 1]
            pw = pw[np.isfinite(pw) & (pw > 0)]
            # 가격 양자(기록만 · 한계 선언): 고정 판 가격은 수정종가 소수 2자리 — 최저가가 낮으면 수익이 0.01/최저가 단위로 묶여 동률이 는다
            rec = {"t": t, "k": k, "cik": c, "hit": hit, "beta": Wd.fp_beta(k, i), "mcap": Wd.mcap(t, k, i),
                   "px_min": (float(pw.min()) if len(pw) else None), "quantum": (float(0.01 / pw.min()) if len(pw) else None),
                   "zero_ret": int(np.sum(ri == 0.0))}
            for mk, rmk in (("mx", mx), ("spx", spx)):
                ok = np.isfinite(ri) & np.isfinite(rmk)
                n = int(ok.sum())
                rec["n_" + mk] = n
                if n >= MIN_PAIRS:
                    a, b = ri[ok].copy(), rmk[ok].copy()
                    key = unit_key(a, b)
                    rec["key_" + mk] = key
                    units.append((key, a, b))
                    if mk == "mx":
                        R, S = margins(a, b)
                        rec["np_ltd"] = float(np.sum((R / (n + 1.0) <= U_NP) & (S / (n + 1.0) <= U_NP)) / n / U_NP)
                        rec["tau"] = float(kendalltau(a, b)[0])            # 진단(기록만) — LTD⊥ 에 남은 순위 상관
                else:
                    rec["key_" + mk] = None
            names.append(rec)
        rows[m] = {"i": i, "last_date": Wd.dates[i], "win0": Wd.dates[d[0] - 1], "names": names}
    ctx._q07_prep = (rows, units)
    return rows, units


def resid(vals, betas):
    """P 안 OLS vals ~ 1 + β → 잔차(둘 다 선 이름만 · 3 개 미만이면 없음)."""
    ks = [k for k in vals if vals[k] is not None and betas.get(k) is not None]
    if len(ks) < 3:
        return {}, None
    y = np.array([vals[k] for k in ks], float)
    X = np.column_stack([np.ones(len(ks)), np.array([betas[k] for k in ks], float)])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    return {k: float(x) for k, x in zip(ks, e)}, {"a": float(b[0]), "b": float(b[1]), "n": len(ks),
                                                   "r2": float(1 - (e @ e) / max(1e-300, ((y - y.mean()) @ (y - y.mean()))))}


def drop_rule(pool, stat, miss, highest=True, n_drop=DROP):
    """(8) — 결측을 먼저(Eg 순 · qg_lab screen 선례) · 다음은 통계 높은(또는 낮은) 순 · 동률은 티커 순 → 남는 30 (Eg 순)."""
    ms = [x for x in pool if x[1] in miss]
    hv = [x for x in pool if x[1] not in miss]
    hv.sort(key=lambda x: ((-stat[x[1]]) if highest else stat[x[1]], x[0]))
    drop = {x[1] for x in (ms + hv)[:n_drop]}
    return [x for x in pool if x[1] not in drop], len(ms)


def weights_of(Wd, i, keep):
    """V0 와 같은 시총가중 20% 상한(eg30plus.cap_weights · qg_lab 과 같은 반복)."""
    import eg30plus as E
    mc = {k: Wd.mcap(t, k, i) for t, k in keep}
    w = E.cap_weights(mc, CAP)
    return {"w": dict(w), "names": {k: t for t, k in keep}}


def signals(ctx, fits):
    """편입마다 변형별 (통계, 결측, 방향) · 진단."""
    rows, _ = prep(ctx)
    out = {}
    for m, R in rows.items():
        nm = R["names"]
        beta = {r["k"]: r["beta"] for r in nm}
        g = lambda r, mk: fits.get(r["key_" + mk]) if r["key_" + mk] else None
        ltd = {r["k"]: (g(r, "mx")["ltd"] if g(r, "mx") and g(r, "mx").get("ok") else None) for r in nm}
        utd = {r["k"]: (g(r, "mx")["utd"] if g(r, "mx") and g(r, "mx").get("ok") else None) for r in nm}
        ltd4 = {r["k"]: (g(r, "spx")["ltd"] if g(r, "spx") and g(r, "spx").get("ok") else None) for r in nm}
        npl = {r["k"]: r.get("np_ltd") for r in nm}
        eL, oL = resid(ltd, beta)
        eU, oU = resid(utd, beta)
        e4, o4 = resid(ltd4, beta)
        eN, oN = resid(npl, beta)
        mb = {k for k, v in beta.items() if v is None}
        asym = {k: eU[k] - eL[k] for k in eL if k in eU}
        # 진단(기록만 · 규칙 불변): LTD⊥ 가 β 로 걷히지 않은 보통 순위 상관(Kendall τ)을 얼마나 싣는가
        tau = {r["k"]: r.get("tau") for r in nm}
        eT, _ = resid(tau, beta)
        kt = [k for k in eL if k in eT]
        kr = [k for k in ltd if ltd[k] is not None and tau.get(k) is not None]
        rs_perp = float(spearmanr([eL[k] for k in kt], [eT[k] for k in kt])[0]) if len(kt) >= 3 else None
        rs_raw = float(spearmanr([ltd[k] for k in kr], [tau[k] for k in kr])[0]) if len(kr) >= 3 else None
        out[m] = {
            "V1": (eL, {k for k in ltd if k not in eL}, True),
            "C3": ({k: v for k, v in beta.items() if v is not None}, mb, True),
            "A1": ({k: ltd[k] for k in eL}, {k for k in ltd if k not in eL}, True),
            "A2": (asym, {k for k in ltd if k not in asym}, False),
            "A3": (eN, {k for k in npl if k not in eN}, True),
            "A4": (e4, {k for k in ltd4 if k not in e4}, True),
            "_diag": {"ols": {"V1": oL, "UTD": oU, "A4": o4, "A3": oN}, "miss_beta": len(mb),
                      "miss_ltd": sum(1 for v in ltd.values() if v is None), "miss_ltd_spx": sum(1 for v in ltd4.values() if v is None),
                      "spearman_ltdperp_tauperp": rs_perp, "spearman_ltd_tau": rs_raw},
        }
    return out


def build_targets(ctx, sig):
    """변형별 목표 경로 {편입월: {"w", "names"}} · 편입 기록."""
    Wd = ctx.Wd
    P = pools(ctx)
    T = {v: {} for v in VARIANTS}
    rec = []
    for m in formations(ctx):
        i = Wd.me[m]
        r = {"m": m}
        for v in VARIANTS:
            stat, miss, hi = sig[m][v]
            keep, nm = drop_rule(P[m], stat, miss, hi)
            assert len(keep) == POOL - DROP
            T[v][m] = weights_of(Wd, i, keep)
            r["miss_" + v] = nm
        rec.append(r)
    return T, rec


def placebo_targets(ctx, i_draw, miss=None):
    """C2 뽑기 i — default_rng(SEED + i) 한 줄기로 편입 순서대로.
    miss = {편입월: V1 결측 집합}(G4 판정 위약 · 검토 수정): V1 처럼 결측(LTD 또는 β)을 먼저 빼고(15 를 넘으면 Eg 순 앞 15),
      모자란 15 − 결측 개를 결측 아닌 이름에서 비복원 균등으로 뺀다 — 규칙과 위약이 «결측 먼저» 구조를 같이 갖고 LTD⊥ 순위만 다르다.
    miss = None(카드 문구 그대로 · 기록만): P 45 에서 비복원 균등 15."""
    Wd = ctx.Wd
    P = pools(ctx)
    rng = np.random.default_rng(Q.SEED + i_draw)
    T = {}
    for m in formations(ctx):
        keep = _placebo_keep(P[m], None if miss is None else miss[m], rng)
        assert len(keep) == POOL - DROP
        T[m] = weights_of(Wd, Wd.me[m], keep)
    return T


def _placebo_keep(pool, ms, rng, n_drop=DROP):
    """한 편입의 C2 빼기 — ms 없음: pool 에서 비복원 균등 n_drop · ms 있음: ms(Eg 순 앞 n_drop)를 먼저, 모자란 만큼 ms 밖에서 비복원 균등."""
    if ms is None:
        dr = set(rng.choice(len(pool), n_drop, replace=False).tolist())
        return [x for j, x in enumerate(pool) if j not in dr]
    forced = [x for x in pool if x[1] in ms][:n_drop]
    rest = [x for x in pool if x[1] not in ms]
    kr = n_drop - len(forced)
    dr = set(rng.choice(len(rest), kr, replace=False).tolist()) if kr > 0 else set()
    dk = {x[1] for x in forced} | {rest[j][1] for j in dr}
    return [x for x in pool if x[1] not in dk]


def v1_miss(sig):
    """편입월 → V1 결측 집합(위약이 규칙과 같이 먼저 뺀다)."""
    return {m: set(sig[m]["V1"][1]) for m in sig}


def thash(T):
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def exante_beta(Wd, i, tg):
    """바스켓 사전 베타 Σ w β_FP(β 가 선 이름만 · 비중 다시 맞춤) · 선 몫."""
    ws = {k: w for k, w in tg["w"].items() if Wd.fp_beta(k, i) is not None}
    s = sum(ws.values())
    if s <= 0:
        return None, 0.0
    return float(sum(w * Wd.fp_beta(k, i) for k, w in ws.items()) / s), float(s)


def v0_check(ctx):
    """V0 목표를 같은 함수(weights_of · Eg 상위 30)로 다시 만들어 공개 판 목표와 비교 — 구성 재현."""
    Wd = ctx.Wd
    P = pools(ctx)
    gap = 0.0
    for m in formations(ctx):
        a = weights_of(Wd, Wd.me[m], P[m][:30])["w"]
        b = ctx.V0_targets[m]["w"]
        assert set(a) == set(b), "V0 상위 30 이 P 의 앞 30 과 다르다(%s)" % m
        gap = max(gap, max(abs(a[k] - b[k]) for k in a))
    return gap


def fit_all(ctx, verbose=True, strict=False):
    rows, units = prep(ctx)
    fits, st = estimate(units, verbose=verbose, strict=strict)
    return rows, fits, st


CALIB_RHO, CALIB_DRAWS = (0.3, 0.5, 0.7), 5      # 합성 Gauss 교정(기록만 · 검토 요청) — ρ 셋 × 5 표본 · n = 252


def gauss_calib(nproc=None):
    """꼬리 독립(참 λ_L = 0) 합성 Gauss 에서 같은 추정기의 LTD — LTD⊥ 가 보통 순위 상관을 얼마나 싣는지 읽는 눈금(규칙 불변 · 기록만).
    표본 = default_rng(SEED + 100 + 10a + j) · a = ρ 번호 · j = 0..4."""
    units, lab = [], []
    for a, rho in enumerate(CALIB_RHO):
        for j in range(CALIB_DRAWS):
            u, v = _sample("gauss", WIN, rho, np.random.default_rng(Q.SEED + 100 + 10 * a + j))
            units.append((unit_key(u, v), u, v))
            lab.append(rho)
    fits, _ = estimate(units, nproc=nproc, verbose=False)
    out = {}
    for rho, (k, _, _) in zip(lab, units):
        out.setdefault("%.1f" % rho, []).append(fits[k]["ltd"])
    return {r: {"ltd_mean": round(float(np.mean(v)), 4), "ltd_min": round(float(min(v)), 4), "ltd_max": round(float(max(v)), 4),
                "n": len(v)} for r, v in out.items()}


def diag(ctx, rows, fits, sig, T):
    """구성 진단(수익 없음) — 편입별 개수 · 결측 · 선택 혼합 · 한도 · SE · 사전 베타."""
    Wd = ctx.Wd
    fam_freq, flag_freq = {}, {}
    per = []
    ses, nbs, ns = [], [], []
    st = {"n_near": [], "gap12": [], "best_start": [], "near_mean_all": [], "det_best_share_all": [], "D_gap_rel": []}
    qn = {"units_quantum_gt_0.5pct": 0, "units_ties_ge10": 0, "forms": {}}
    for m in formations(ctx):
        R = rows[m]
        i = R["i"]
        sel = []
        for r in R["names"]:
            for mk in ("mx", "spx"):
                f = fits.get(r["key_" + mk]) if r["key_" + mk] else None
                if not f or not f.get("ok"):
                    continue
                for kk in st:
                    if f.get(kk) is not None:
                        st[kk].append(f[kk])
                if mk == "mx":
                    fam_freq[f["label"]] = fam_freq.get(f["label"], 0) + 1
                    sel.append(f["label"])
                    if f.get("se") is not None:
                        ses.append(f["se"])
                    nbs.append(f["n_bound"])
                    ns.append(f["n"])
                    big_q = (r.get("quantum") or 0) > 0.005
                    qn["units_quantum_gt_0.5pct"] += big_q
                    qn["units_ties_ge10"] += f["ties"][0] >= 10
                    if big_q or f["ties"][0] >= 10:
                        qn["forms"].setdefault(m, []).append(r["t"])
                for x in f["flags"]:
                    key = mk + ":" + x.split(":")[0]
                    flag_freq[key] = flag_freq.get(key, 0) + 1
        b1, c1 = exante_beta(Wd, i, T["V1"][m])
        b0, c0 = exante_beta(Wd, i, ctx.V0_targets[m])
        b3, c3 = exante_beta(Wd, i, T["C3"][m])
        per.append({"m": m, "last_date": R["last_date"], "win0": R["win0"], "n_mx": [r["n_mx"] for r in R["names"]],
                    "miss": sig[m]["_diag"], "beta_V1": b1, "beta_V0": b0, "beta_C3": b3, "beta_cov": [c1, c0, c3],
                    "dbeta_exante": (None if b1 is None or b0 is None else b1 - b0),
                    "overlap_V0": len(set(T["V1"][m]["w"]) & set(ctx.V0_targets[m]["w"])),
                    "max_w": {v: max(T[v][m]["w"].values()) for v in VARIANTS},
                    "hits": sum(1 for r in R["names"] if r["hit"]), "cik_only": sum(1 for r in R["names"] if r["hit"] and r["k"] not in r["hit"])})
    q5 = lambda x: [round(float(v), 6) for v in np.quantile(x, [0.0, 0.1, 0.5, 0.9, 1.0])] if len(x) else None
    starts_diag = {"n_near_hist(1..4)": np.bincount(st["n_near"], minlength=N_START + 2)[1:].tolist() if st["n_near"] else None,
                   "share_n_near_ge2": float(np.mean(np.array(st["n_near"]) >= 2)) if st["n_near"] else None,
                   "gap12_q0_10_50_90_100": q5(st["gap12"]), "best_start_hist(s0,s1,s2,det)":
                   np.bincount(st["best_start"], minlength=N_START + 1).tolist() if st["best_start"] else None,
                   "near_mean_all_median": float(np.median(st["near_mean_all"])) if st["near_mean_all"] else None,
                   "det_best_share_all_median": float(np.median(st["det_best_share_all"])) if st["det_best_share_all"] else None,
                   "D_gap_rel_q0_10_50_90_100": q5(st["D_gap_rel"]),
                   "D_gap_rel_lt_1e-6": int(sum(1 for x in st["D_gap_rel"] if x < 1e-6)),
                   "D_gap_rel_lt_1e-4": int(sum(1 for x in st["D_gap_rel"] if x < 1e-4))}
    rsp = [r["miss"]["spearman_ltdperp_tauperp"] for r in per if r["miss"].get("spearman_ltdperp_tauperp") is not None]
    rsr = [r["miss"]["spearman_ltd_tau"] for r in per if r["miss"].get("spearman_ltd_tau") is not None]
    return {"formations": per, "family_freq": dict(sorted(fam_freq.items(), key=lambda kv: -kv[1])), "flags": flag_freq,
            "se_median": float(np.median(ses)) if ses else None, "se_q90": float(np.quantile(ses, 0.9)) if ses else None,
            "n_bound_mean": float(np.mean(nbs)) if nbs else None, "n_pairs_min": min(ns) if ns else None,
            "n_pairs_median": float(np.median(ns)) if ns else None, "starts": starts_diag,
            "price_quantum": {"units_quantum_gt_0.5pct": qn["units_quantum_gt_0.5pct"], "units_ties_ge10": qn["units_ties_ge10"],
                              "forms": {m: sorted(set(v)) for m, v in sorted(qn["forms"].items())}},
            "tau_corr": {"spearman_ltdperp_tauperp_median_min_max": ([round(float(np.median(rsp)), 3), round(min(rsp), 3), round(max(rsp), 3)]
                                                                     if rsp else None),
                         "spearman_ltd_tau_median": round(float(np.median(rsr)), 3) if rsr else None}}


INTERP = [
    "θ 변환: 양의 한도 족(Clayton · Galambos · Gumbel · Joe · Plackett 과 회전)은 log θ 를 logit 으로, Gauss · Frank · FGM 은 θ 를 logit 으로 한도 안에 둔다.",
    "L-BFGS-B 는 변환 좌표 상자 ±30(σ(±30) ≈ 1e-13 · 넘침 방지 · a1 · a2 포함) · scipy 기본 허용오차 · 목적 = −Σ log c.",
    "시작 = 씨앗 셋(카드 · default_rng(20260925 + s).standard_normal(5), s = 0,1,2 — 모든 종목 · 편입 · 혼합에 같은 세 점) + 결정적 하나(검토 수정 · 카드 수정 필요): "
    "a1 = a2 = 0(무게 1/3 씩) · x_k = 성분 k 족 하나만의 최우(σ 격자 (j+½)/40 최대 → 이웃 구간 유계 Brent xatol 1e-6). 로그우도 최대 · 동률은 앞 시작(씨앗 먼저).",
    "시작 의존(공개 · 검토 수치와 수정 전 탐침): 씨앗 셋만이면 단위 3688 의 선택 적합 중 최고 두 시작이 1e-3 안에서 만나는 몫 22.5% · 서로 다른 씨앗 셋 두 벌의 선택 혼합 LTD 차 90 백분위 0.031(표본 40 단위). "
    "결정적 시작을 더하면 같은 비교가 0.035 · 75 백분위 0.013 → 0.004 · 선택 일치 17/40 → 25/40. 남는 차이는 작은 무게(≈3%)의 극단 θ(한도 50 · Frank −25) «뾰족» 최적 — 씨앗을 늘려도(8 · 12) 선택 일치가 늘지 않아 늘리지 않았다. "
    "단위마다 n_near(1e-3 안 시작 수) · gap12 · best_start · near_mean_all · D_gap_rel(IAD 1 · 2 위 상대 차)을 캐시 · log 에 남긴다. 굽기는 얼린 적합(FITS_MANIFEST)만 쓴다.",
    "기울기: softmax 로짓은 해석 · θ 좌표는 중앙 차분(h = 1e-5) — 세 족 밀도를 θ, θ ± h 에서 한 번에 계산.",
    "«한도에 닿은 적합» = 변환 σ(x) < 1e-6 또는 > 1 − 1e-6 · 64 적합 중 수(n_bound)와 선택 적합의 족을 기록 · 무게 < 1e-6 은 w0 표식.",
    "주변 동률은 CRW 식 (6) 그대로 최대 순위(#{r ≤ x}) · 격자 경험 코퓰러도 같은 순위.",
    "IAD: (n, n) 칸은 0/0 := 0 · 안쪽 칸 C(1−C) = 0 이면 Ĉ = C 일 때 0, 아니면 ∞ · 가장자리 행 · 열은 모든 혼합에 같다(C(1,v) = v) — 합에 넣는다.",
    "M_−i: 수익일 d 의 명단 = d−1 이전 가장 가까운 월말의 Wd.universe(월, 'union', False) · 비중 = qg_lab mcap(t, k, d−1)(수정종가 × 90일 지연 주식수) · "
    "i 는 가격 키 또는 CIK 가 같거나, CIK 없는 이중클래스로 선언된 같은 발행사(SIBLINGS: LBTYA ↔ LBTYK — union 전체의 CIK 없는 29 티커 중 유일한 쌍)면 뺀다.",
    "r_i 와 M_−i 가 둘 다 선 날만 짝 · 252 수익일 창(편입일 포함) · A4 는 같은 창의 S&P 500 PR.",
    "Frank |θ| < 1e-6 은 1차 급수 C = uv(1 + θ/2 (1−u)(1−v)) · c = 1 + θ/2 (1−2u)(1−2v).",
    "SE: 선택 적합의 관측 정보(변환 좌표 · 중앙 차분 h = 1e-4)로 델타법 · ∇LTD 는 중앙 차분 · 역은 식별되는 방향만(아래 줄) · 양의 고유값이 없으면 SE 없음(se_nopd).",
    "결측이 15 를 넘으면 결측을 Eg 순으로 뺀다(qg_lab screen · EGBEST C2 선례) · 통계 동률은 티커 순(같은 선례).",
    "C3 은 β 결측을 먼저 뺀다 · A1 · A4 의 결측 집합은 V1 과 같은 꼴(그 LTD 또는 β) · A2 는 LTD/UTD 또는 β · A3 은 짝 < 200 또는 β.",
    "UTD(A2) = w3·λ_U(θ3) (CRW §2.1.3) · UTD⊥ 는 LTD⊥ 와 같은 OLS · A2 는 UTD⊥ − LTD⊥ 가장 낮은 15 를 뺀다.",
    "A3: Ĉ(u,u) = #{R/(n+1) ≤ 0.05 이고 S/(n+1) ≤ 0.05}/n · ÷ 0.05 · V1 처럼 β 에 잔차화.",
    "C2 위약(G4 판정 · 검토 수정 · 카드 수정 필요): 뽑기 i 마다 default_rng(SEED + i) 한 줄기로 편입 순서대로 — V1 과 같은 결측(LTD 또는 β)을 먼저 빼고 "
    "남은 15 − 결측 개를 결측 아닌 이름에서 rng.choice(비복원 균등). 규칙과 구조(어린 상장 · 분사 이름 강제 빼기 · 16/41 편입 21 개)가 같고 LTD⊥ 순위만 다르다.",
    "C2 문자 그대로(카드 문구 · 기록만 · 판정에 쓰지 않는다): 같은 씨앗으로 P 45 에서 rng.choice(45, 15) — 결측과 무관. 두 판의 차 = 강제 빼기 몫.",
    "위약 통계 = 하락월(39) 평균 Δβ(C2_i − V0) · 참값 = 같은 식의 Δβ(V1 − V0) · 95 백분위 = numpy percentile(선형 보간).",
    "Δβ 의 β̂ 는 qbatch_core.evaluate 의 sleeve_beta(120개월 SPY 총수익 기울기) — 러너의 dbeta 와 같은 식.",
    "사전 바스켓 베타 = Σ w β_FP(β 가 선 이름 · 비중 다시 맞춤) — 카드 «±0.05 안» 은 기록만.",
    "카드에 F0 가 없다 — f0 = {ok: True}(규칙을 지어내지 않는다 · 계약 4). 제안 F0(V1 ≠ V0 편입 수 · 결측 ≥ 15 편입 수)는 log.f0_proposed 에 기록만 — 카드에 넣으면 그때 판정.",
    "SE 가 정의되지 않는 방향(무게 0 성분의 θ 등 · 관측 정보 고유값 ≤ 1e-8·최대)은 무어-펜로즈 역으로 뺀다(se_pinv:뺀 수) — SE 는 기록만.",
    "M_−i 의 명단은 월말 PIT union(시총이 선 이름만 — qg_lab.universe) · 2015-08 스냅숏은 394 이름(주식수 커버리지 한계 · 카드 OPEN RISKS 3).",
    "가격 양자(한계 · 고칠 수 없다): 고정 판 가격(sd pxd)은 분할 · 배당 수정 종가 소수 2자리뿐 — 최저가가 낮은 창(2016-17 NVDA $0.8-2.7 등)은 수익이 0.01/최저가 "
    "(최대 ≈1.25%) 단위로 묶여 0 수익 · 동률이 많다(최대 89). 최대 순위 동률(식 6)과 겹쳐 (0,0) 근처 Ĉ · 꼬리 적합이 뭉개진다. 떨림(jitter)은 새 파라미터라 넣지 않고 "
    "단위마다 ties · quantum(0.01/최저가) · px_min · zero_ret 를 log.ltd 에 · 0.5% 초과 · 동률 ≥ 10 편입 목록을 log.diag.price_quantum 에 둔다.",
    "해석 위험(기록만 · 규칙 불변): LTD⊥ 는 FP β(ρ 와 σ_i/σ_m 을 섞는다)로 걷히지 않은 보통 순위 상관을 싣는다 — 편입마다 Spearman(LTD⊥, τ⊥)(τ = Kendall(r_i, M_−i) 를 같은 β 에 잔차화) "
    "를 log.diag.tau_corr 에, 꼬리 독립 합성 Gauss(ρ = 0.3/0.5/0.7 · n = 252 · 5 표본)에서 같은 추정기 LTD 를 log.gauss_calib 에 둔다.",
    "재현(검토 수정): 굽기(run)는 다시 적합하지 않는다 — 랩 단위 3688 이 얼린 묶음 파일(FITS_FILE · 없으면 %TEMP% 캐시)에 모두 있고 manifest(열쇠 정렬 · json 키 정렬 sha256)가 "
    "FITS_MANIFEST 와 같아야 한다. IAD 1 · 2 위 차가 최적화 허용오차보다 작은 단위가 있어 다른 기계에서 다시 적합하면 선택이 뒤집힐 수 있기 때문이다.",
]


# ── 판정 보조(카드 G4 만) ─────────────────────────────────────────────────
def sleeve_beta(ctx, fr):
    return Q.evaluate(ctx.G, fr)["sleeve_beta"]


def dbeta_down(ctx, fa, fb, ba=None, bb=None):
    """하락월(39) 평균 Δβ = (X_a − X_b) − 0.1(β̂_a − β̂_b)(SPYTR − rf)."""
    ha, hb = fa["hold"], fb["hold"]
    assert ha == hb and fa["basis"] == fb["basis"] == "TR"
    ba = sleeve_beta(ctx, fa) if ba is None else ba
    bb = sleeve_beta(ctx, fb) if bb is None else bb
    dm = ctx.dmask(ha)
    rf = np.array([float(ctx.G.RF.get(h, 0.0)) * 100 for h in ha])
    ix = np.asarray(fa["index"], float)
    assert np.allclose(ix, fb["index"])
    db = (np.asarray(fa["ex"]) - np.asarray(fb["ex"])) - Q.SLEEVE * (ba - bb) * (ix - rf)
    return float(db[dm].mean())


def _proxy_turn(T):
    ms = sorted(T)
    tv = [0.5 * sum(abs(T[b]["w"].get(k, 0.0) - T[a]["w"].get(k, 0.0)) for k in set(T[a]["w"]) | set(T[b]["w"])) for a, b in zip(ms, ms[1:])]
    return float(np.mean(tv) * 4) if tv else None


# ── 계약 ──────────────────────────────────────────────────────────────────
def _naive(name, u, v, th):
    """시험용 교과서 식(Nelsen · Joe) 그대로 — 안정화 없이 100 자리 십진(decimal)로 계산 · Gauss 는 scipy 이변량 정규(Genz)."""
    import decimal
    base, rot = FAM[name][0], FAM[name][1]
    if base == "gauss":
        from scipy.stats import multivariate_normal, norm
        uu, vv = (1 - u, 1 - v) if rot else (u, v)
        a, bb = norm.ppf(uu), norm.ppf(vv)
        C = float(multivariate_normal(mean=[0, 0], cov=[[1, th], [th, 1]]).cdf([a, bb]))
        c = 1 / math.sqrt(1 - th * th) * math.exp(-(th * th * (a * a + bb * bb) - 2 * th * a * bb) / (2 * (1 - th * th)))
        return C, c
    with decimal.localcontext() as cx:
        cx.prec = 100
        D = decimal.Decimal
        uu, vv, tt = D(u), D(v), D(th)
        if rot:
            C, c = _naive_base(base, 1 - uu, 1 - vv, tt)
            C = uu + vv - 1 + C
        else:
            C, c = _naive_base(base, uu, vv, tt)
        return float(C), float(c)


def _naive_base(b, u, v, t):
    one = type(u)(1)
    e = lambda z: z.exp()
    if b == "clayton":
        s = u ** (-t) + v ** (-t) - one
        return s ** (-one / t), (one + t) * (u * v) ** (-one - t) * s ** (-2 - one / t)
    if b == "gumbel":
        x, y = -u.ln(), -v.ln()
        A = x ** t + y ** t
        C = e(-(A ** (one / t)))
        return C, C / (u * v) * (x * y) ** (t - one) * A ** (2 / t - 2) * (one + (t - one) * A ** (-one / t))
    if b == "joe":
        p, q = (one - u) ** t, (one - v) ** t
        Dd = p + q - p * q
        return one - Dd ** (one / t), Dd ** (one / t - 2) * (one - u) ** (t - one) * (one - v) ** (t - one) * (t - one + Dd)
    if b == "galambos":
        x, y = -u.ln(), -v.ln()
        S = x ** (-t) + y ** (-t)
        C = u * v * e(S ** (-one / t))
        Bx, By = S ** (-one / t - one) * x ** (-t - one), S ** (-one / t - one) * y ** (-t - one)
        Bxy = (one + t) * S ** (-one / t - 2) * x ** (-t - one) * y ** (-t - one)
        return C, C / (u * v) * ((one - Bx) * (one - By) + Bxy)
    if b == "frank":
        C = -(one / t) * (one + (e(-t * u) - one) * (e(-t * v) - one) / (e(-t) - one)).ln()
        return C, t * (one - e(-t)) * e(-t * (u + v)) / ((one - e(-t)) - (one - e(-t * u)) * (one - e(-t * v))) ** 2
    if b == "fgm":
        return u * v * (one + t * (one - u) * (one - v)), one + t * (one - 2 * u) * (one - 2 * v)
    if b == "plackett":
        S = one + (t - one) * (u + v)
        C = (S - (S * S - 4 * u * v * t * (t - one)).sqrt()) / (2 * (t - one))
        Qd = (one + (t - one) * (u + v)) ** 2 - 4 * t * (t - one) * u * v
        return C, t * (one + (t - one) * (u + v - 2 * u * v)) / (Qd * Qd.sqrt())
    raise ValueError(b)


def _pv(name, u, v, th):
    """모듈 식으로 한 점 (C, c)."""
    V, Vr = _views(np.array([u]), np.array([v]))
    C, _ = fam_cdf(name, V, Vr, np.asarray(th, float))
    return float(C[0]), float(np.exp(fam_lpdf(name, V, Vr, np.asarray(th, float)))[0])


def _tau_closed(name, t):
    from scipy.integrate import quad
    b = FAM[name][0]
    if b == "clayton":
        return t / (t + 2)
    if b == "gumbel":
        return 1 - 1 / t
    if b == "joe":
        k = np.arange(1, 400001, dtype=float)
        return float(1 - 4 * np.sum(1.0 / (k * (t * k + 2) * (t * (k - 1) + 2))))
    if b == "gauss":
        return 2 / math.pi * math.asin(t)
    if b == "fgm":
        return 2 * t / 9
    if b == "frank":
        D1 = quad(lambda s: s / math.expm1(s), 0, t)[0] / t
        return 1 - 4 / t * (1 - D1)
    return None


def _rho_closed(name, t):
    from scipy.integrate import quad
    b = FAM[name][0]
    if b == "plackett":
        return (t + 1) / (t - 1) - 2 * t * math.log(t) / (t - 1) ** 2
    if b == "gauss":
        return 6 / math.pi * math.asin(t / 2)
    if b == "fgm":
        return t / 3
    if b == "frank":
        D1 = quad(lambda s: s / math.expm1(s), 0, t)[0] / t
        D2 = 2 * quad(lambda s: s * s / math.expm1(s), 0, t)[0] / t ** 2
        return 1 - 12 / t * (D1 - D2)
    if b == "galambos":
        A = lambda s: 1 - (s ** -t + (1 - s) ** -t) ** (-1 / t)
        return 12 * quad(lambda s: 1 / (1 + A(s)) ** 2, 0, 1, limit=200)[0] - 3
    if b == "gumbel":
        A = lambda s: (s ** t + (1 - s) ** t) ** (1 / t)
        return 12 * quad(lambda s: 1 / (1 + A(s)) ** 2, 0, 1, limit=200)[0] - 3
    return None


def _sample(kind, n, th, rng):
    u = rng.random(n)
    if kind == "clayton":                                    # 조건부 역변환
        w = rng.random(n)
        v = ((w ** (-th / (1 + th)) - 1) * u ** (-th) + 1) ** (-1 / th)
        return u, v
    from scipy.stats import norm
    z1, z2 = rng.standard_normal(n), rng.standard_normal(n)
    return norm.cdf(z1), norm.cdf(th * z1 + math.sqrt(1 - th * th) * z2)


def selftest() -> dict:
    """합성 자료만 — 랩 수익 없음. 12 족 CDF · 밀도 · λ(한도) 를 닫힌 꼴과 · 추정 파이프라인 · 시장 합 · 빼기 규칙을 잰다."""
    t = {}
    names = list(FAM)
    pts = [(0.13, 0.27), (0.4, 0.75), (0.62, 0.55), (0.85, 0.2), (0.93, 0.88)]
    TH = {"clayton": (1e-4, 0.8, 4.0, 50.0), "rclayton": (1e-4, 0.8, 4.0, 50.0), "gumbel": (1.0, 1.7, 5.0, 50.0),
          "rgumbel": (1.0, 1.7, 5.0, 50.0), "joe": (1.0, 2.2, 6.0, 50.0), "rjoe": (1.0, 2.2, 6.0, 50.0),
          "galambos": (1e-4, 0.9, 3.0, 50.0), "rgalambos": (1e-4, 0.9, 3.0, 50.0), "gauss": (-0.999, -0.4, 0.6, 0.999),
          "frank": (-50.0, -3.0, 5.0, 50.0), "fgm": (-1.0, -0.3, 0.7, 1.0), "plackett": (1e-3, 0.3, 6.0, 1e3)}
    # 1) 교과서 식과 일치(CDF · 밀도) — 안쪽 두 θ 는 모든 점 · 한도 θ 는 교과서 식이 넘치지 않는 점만
    worst_c, worst_d = {}, {}
    for nm in names:
        ec = ed = 0.0
        for j, th in enumerate(TH[nm]):
            for u, v in pts:
                C0, c0 = _naive(nm, u, v, th)
                if not (np.isfinite(C0) and np.isfinite(c0)) or c0 <= 1e-250 or C0 <= 1e-250:
                    continue
                C1, c1 = _pv(nm, u, v, th)
                ec = max(ec, abs(C1 - C0) / max(abs(C0), 1e-300))
                ed = max(ed, abs(c1 - c0) / max(abs(c0), 1e-300))
        worst_c[nm], worst_d[nm] = ec, ed
    t["cdf_vs_textbook_max_rel"] = float(max(worst_c.values()))
    t["pdf_vs_textbook_max_rel"] = float(max(worst_d.values()))
    t["cdf_pdf_textbook_ok"] = bool(max(worst_c.values()) < 1e-12 and max(worst_d.values()) < 1e-11)
    # 2) 밀도 = CDF 혼합 편미분(중앙 차분) · 안쪽 θ
    worst = 0.0
    hh = 1e-4
    for nm in names:
        for th in TH[nm][1:3]:
            for u, v in pts:
                Cf = lambda a, b: _pv(nm, a, b, th)[0]
                fd = (Cf(u + hh, v + hh) - Cf(u + hh, v - hh) - Cf(u - hh, v + hh) + Cf(u - hh, v - hh)) / (4 * hh * hh)
                c1 = _pv(nm, u, v, th)[1]
                worst = max(worst, abs(fd - c1) / c1)
    t["pdf_vs_cdf_fd_max_rel"] = float(worst)
    t["pdf_cdf_consistent_ok"] = bool(worst < 2e-4)
    # 3) 경계 · Fréchet 한계 · 밀도 질량 1
    okb = True
    for nm in names:
        for th in TH[nm]:
            V1_, Vr1 = _views(np.array([0.37, 1 - 1e-13]), np.array([1 - 1e-13, 0.61]))
            C, S = fam_cdf(nm, V1_, Vr1, np.asarray(th, float))
            okb &= bool(abs(C[0] - 0.37) < 1e-9 and abs(C[1] - 0.61) < 1e-9)
            g = np.linspace(0.05, 0.95, 7)
            U_, V_ = np.meshgrid(g, g)
            Cg, _ = fam_cdf(nm, *_views(U_.ravel(), V_.ravel()), np.asarray(th, float))
            lo = np.maximum(U_.ravel() + V_.ravel() - 1, 0); hi = np.minimum(U_.ravel(), V_.ravel())
            okb &= bool(np.all(Cg >= lo - 1e-12) and np.all(Cg <= hi + 1e-12))
    t["boundary_frechet_ok"] = okb
    N = 1200
    gm = (np.arange(N) + 0.5) / N
    U_, V_ = np.meshgrid(gm, gm)
    Vg, Vgr = _views(U_.ravel(), V_.ravel())
    mass, tau_err, rho_err = {}, {}, {}
    for nm in names:
        th = TH[nm][1]
        c = np.exp(fam_lpdf(nm, Vg, Vgr, np.asarray(th, float)))
        C, _ = fam_cdf(nm, Vg, Vgr, np.asarray(th, float))
        mass[nm] = float(c.mean())
        tc = _tau_closed(nm, th)
        if tc is not None:
            tau_err[nm] = abs(4 * float((C * c).mean()) - 1 - tc)
        rc = _rho_closed(nm, th)
        if rc is not None:
            rho_err[nm] = abs(12 * float(C.mean()) - 3 - rc)
    t["mass_max_dev"] = float(max(abs(v - 1) for v in mass.values()))
    t["tau_closed_max_err"] = float(max(tau_err.values()))
    t["rho_closed_max_err"] = float(max(rho_err.values()))
    t["tau_rho_families"] = sorted(set(tau_err) | set(rho_err))
    t["mass_tau_rho_ok"] = bool(t["mass_max_dev"] < 5e-3 and t["tau_closed_max_err"] < 3e-3 and t["rho_closed_max_err"] < 1e-4
                               and len(t["tau_rho_families"]) == 12)
    # 4) λ 한도값 = 닫힌 꼴(식) = 수치 극한 C(u,u)/u (u → 0) · 위 꼬리는 1 − 2t + C(t,t) 를 (1 − t) 로
    lam_rows, okl = {}, True
    for nm in names:
        _, _, lo, hi, _, lL, lU = FAM[nm]
        if lL is None and lU is None:
            continue
        for th in (lo, hi):
            # 닫힌 꼴(Nelsen 표 5.1 · Joe 1997): Clayton · Galambos 2^(−1/θ) · Gumbel · Joe 2 − 2^(1/θ) — 회전은 꼬리를 바꾼다
            closed = 2 ** (-1 / th) if FAM[nm][0] in ("clayton", "galambos") else 2 - 2 ** (1 / th)
            f = float((lL or lU)(th))
            num = []
            for e in (1e-6, 1e-8):
                if lL is not None:
                    V_, Vr_ = _views(np.array([e]), np.array([e]))
                    C, _ = fam_cdf(nm, V_, Vr_, np.asarray(th, float))
                    num.append(float(C[0]) / e)
                else:
                    Vr_, V_ = _views(np.array([e]), np.array([e]))          # (1−e, 1−e) 는 (e, e) 의 회전 보기
                    C, S = fam_cdf(nm, V_, Vr_, np.asarray(th, float))
                    num.append(float((2 * e - float(S[0])) / e))    # (1 − 2t + C(t,t))/(1 − t) · t = 1 − e · 1 − C = S
            lam_rows["%s@%g" % (nm, th)] = [round(f, 6), round(closed, 6), round(num[-1], 6)]
            okl &= bool(abs(f - closed) < 1e-12 and abs(num[-1] - closed) < 2e-4 and abs(num[-1] - closed) <= abs(num[0] - closed) + 1e-12)
    t["lambda_bounds"] = lam_rows
    t["lambda_bounds_ok"] = okl
    # 5) Frank 급수 = 닫힌 꼴(작은 θ) · Gauss CDF 의 0 좌표
    Vf, Vfr = _views(np.array([0.2, 0.7]), np.array([0.6, 0.35]))
    a_ser = fam_cdf("frank", Vf, Vfr, np.asarray(5e-7))[0]
    a_cl = fam_cdf("frank", Vf, Vfr, np.asarray(2e-6))[0]
    ser_d = np.exp(fam_lpdf("frank", Vf, Vfr, np.asarray(5e-7)))
    ind = Vf["u"] * Vf["v"]
    t["frank_series_ok"] = bool(np.all(np.abs((a_cl - ind) / (2e-6) - (a_ser - ind) / 5e-7) < 1e-4) and np.all(np.abs(ser_d - 1) < 1e-6))
    from scipy.stats import multivariate_normal as MVN, norm
    zs = [(0.5, 0.5), (0.5, 0.2), (0.8, 0.5), (0.3, 0.9)]
    ge = 0.0
    for r_ in (-0.7, 0.35, 0.999):
        for u, v in zs:
            Cg, _ = gau_cdf(_views(np.array([u]), np.array([v]))[0], np.asarray(r_))
            ref = float(MVN(mean=[0, 0], cov=[[1, r_], [r_, 1]]).cdf([norm.ppf(u), norm.ppf(v)]))
            ge = max(ge, abs(float(Cg[0]) - ref))
    t["gauss_zero_coord_err"] = ge
    t["gauss_zero_ok"] = bool(ge < 1e-7)
    # 6) IAD 삼각 합 = 전체 격자 합(작은 n · 비대칭 Ĉ)
    rng = np.random.default_rng(Q.SEED)
    n0 = 40
    a0, b0 = rng.standard_normal(n0), rng.standard_normal(n0)
    b0 = 0.6 * a0 + 0.8 * b0
    R0, S0 = margins(a0, b0)
    E0 = emp_copula(R0, S0, n0)
    Gd = grid(n0)
    mx_ = ("clayton", "frank", "gumbel")
    w_ = np.array([0.3, 0.5, 0.2]); th_ = [1.5, 3.0, 1.4]
    Cm = sum(w_[k] * comp_lattice(mx_[k], Gd, th_[k])[0] for k in range(3))
    Sm = sum(w_[k] * comp_lattice(mx_[k], Gd, th_[k])[1] for k in range(3))
    tri = iad(Gd, E0[Gd["ia"], Gd["ib"]], E0[Gd["ib"], Gd["ia"]], Cm, Sm) + iad_const(E0, n0)
    full = 0.0
    for a in range(1, n0 + 1):
        for b in range(1, n0 + 1):
            if a == n0 and b == n0:
                continue
            ua, vb = a / n0, b / n0
            if a == n0 or b == n0:
                Cv = min(ua, vb)
            else:
                Cv = sum(w_[k] * _naive(mx_[k], ua, vb, th_[k])[0] for k in range(3))
            full += (E0[a - 1, b - 1] - Cv) ** 2 / (Cv * (1 - Cv))
    t["iad_tri_vs_full_rel"] = abs(tri - full) / full
    t["iad_ok"] = bool(t["iad_tri_vs_full_rel"] < 1e-10)
    # 7) 순위 동률 = 최대 순위(식 6)
    Rt, _ = margins(np.array([0.1, -0.2, 0.1, 0.3, 0.0]), np.arange(5.0))
    t["ties_max_rank_ok"] = bool(list(Rt) == [4, 1, 4, 5, 2])
    # 8) 추정 파이프라인 — 합성 Clayton(θ = 2 · λ_L = 0.707) vs Gauss(ρ = 0.5 · λ_L = 0) · n = 252 · 시작점 · 캐시 열쇠 재현
    rs = np.random.default_rng(Q.SEED + 11)
    uc, vc = _sample("clayton", 252, 2.0, rs)
    ug, vg = _sample("gauss", 252, 0.5, rs)
    t0 = time.time()
    fc = fit_unit(uc, vc, keep_all=False)
    fg_ = fit_unit(ug, vg, keep_all=False)
    t["unit_fit_sec"] = round((time.time() - t0) / 2, 2)
    t["synth_clayton_ltd"] = [round(fc["ltd"], 3), fc["label"], None if fc["se"] is None else round(fc["se"], 3)]
    t["synth_gauss_ltd"] = [round(fg_["ltd"], 3), fg_["label"], None if fg_["se"] is None else round(fg_["se"], 3)]
    t["synth_pipeline_ok"] = bool(fc["ok"] and fg_["ok"] and fc["ltd"] > 0.45 and fg_["ltd"] < fc["ltd"] - 0.2 and fc["nfail"] == 0)
    # 단일 족 최우 = 닫힌 꼴 근처(Clayton 표본을 Clayton 으로만 · 시작점 무관)
    Rr, Sr = margins(uc, vc)
    Vc, Vcr = _views(Rr / 253.0, Sr / 253.0)
    grid_th = np.exp(np.linspace(math.log(0.5), math.log(8), 4001))
    llg = np.array([clay_lpdf(Vc, th).sum() for th in grid_th])
    f1 = fit_mix(("clayton", "fgm", "gumbel"), Vc, Vcr)
    t["mle_single_vs_grid"] = [round(float(grid_th[llg.argmax()]), 3), round(float(llg.max()), 3), round(f1["ll"], 3)]
    t["mle_mixture_ge_single_ok"] = bool(f1["ll"] >= float(llg.max()) - 1e-6)
    # 목적 기울기(a 해석 · θ 묶음 차분) = ℓ 의 중앙 차분(h = 1e-6) — 무작위 ψ 에서 여러 혼합
    ge = 0.0
    for j in (0, 21, 42, 63):
        Mx = Mix(MIXES[j], Vc, Vcr)
        psi = np.random.default_rng(Q.SEED + j).normal(0, 1, 5)
        _, g = Mx.fg(psi)
        gn = np.array([(Mx.ll(psi + 1e-6 * e) - Mx.ll(psi - 1e-6 * e)) / 2e-6 for e in np.eye(5)])
        ge = max(ge, float(np.max(np.abs(-g - gn)) / max(1.0, float(np.max(np.abs(gn))))))
    t["grad_check_max_rel"] = ge
    t["grad_check_ok"] = bool(ge < 1e-5)
    t["starts_ok"] = bool(all(np.array_equal(a, b) for a, b in zip(starts(), starts())) and len(starts()) == 3)
    t["unit_key_ok"] = bool(unit_key(uc, vc) == unit_key(uc.copy(), vc.copy()) and unit_key(uc, vc) != unit_key(vc, uc))
    # 9) 시장 합(i 제외) — 가짜 세 이름 · 두 달 · 손으로 계산
    dates = ["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-28", "2020-03-02"]
    me = {"2020-01": 1, "2020-02": 3, "2020-03": 4}
    PXf = {"A": np.array([10, 11, 12, 12, 13.]), "B": np.array([20, 20, 19, 21, 22.]), "C": np.array([5, 5, np.nan, 6, 6.])}
    SH = {"A": 2.0, "B": 1.0, "C": 4.0}
    mem = {"2020-01": [("A", "A"), ("B", "B"), ("C", "C")], "2020-02": [("A", "A"), ("B", "B")]}
    S_, W_, con, kc, _, ktk = build_market(dates, me, lambda mm: mem.get(mm, []), lambda tt, k, d: PXf[k][d] * SH[k], lambda k: PXf[k],
                                           lambda tt: "cik" + tt, {"A"}, set(), 2, 4)
    MKf = {"dA": 2, "S": S_, "W": W_, "contrib": con, "kcik": kc, "ktick": ktk}
    got, _ = mkt_excl(MKf, "A", "cikA", np.array([2, 3, 4]))
    # d=2: 명단 01월(A,B,C) · C 는 수익 없음 → B 만 = 19/20 − 1 · d=3: 명단 01월 · B,C(C 전날 NaN → 빠짐) → B = 21/19 − 1
    # d=4: 명단 02월(A,B) → B = 22/21 − 1
    want = np.array([19 / 20 - 1, 21 / 19 - 1, 22 / 21 - 1])
    allm = S_ / W_
    # 전날 종가 비중: d=2 A 11×2 · B 20 · d=3 A 12×2 · B 19 · d=4 A 12×2 · B 21
    want_all = np.array([(22 * (12 / 11 - 1) + 20 * (19 / 20 - 1)) / 42, (24 * 0 + 19 * (21 / 19 - 1)) / 43, (24 * (13 / 12 - 1) + 21 * (22 / 21 - 1)) / 45])
    t["market_excl_ok"] = bool(np.allclose(got, want, rtol=0, atol=1e-15) and np.allclose(allm, want_all, rtol=0, atol=1e-15))
    # 9b) CIK 없는 같은 발행사(SIBLINGS) — LBTYA 의 M_−i 는 LBTYK 도 뺀다 · 다른 이름은 그대로
    memL = {"2020-01": [("LBTYA", "LA"), ("LBTYK", "LK"), ("C", "C")], "2020-02": [("LBTYA", "LA"), ("LBTYK", "LK"), ("C", "C")]}
    PXl = {"LA": PXf["A"], "LK": PXf["B"], "C": np.array([5, 5, 5.5, 6, 6.])}
    SHl = {"LA": 2.0, "LK": 1.0, "C": 4.0}
    S2, W2, con2, kc2, _, kt2 = build_market(dates, me, lambda mm: memL.get(mm, []), lambda tt, k, d: PXl[k][d] * SHl[k], lambda k: PXl[k],
                                             lambda tt: None, {"LA"}, set(), 2, 4, frozenset(SIBLINGS["LBTYA"]))
    MK2 = {"dA": 2, "S": S2, "W": W2, "contrib": con2, "kcik": kc2, "ktick": kt2}
    gotL, hitL = mkt_excl(MK2, "LA", None, np.array([2, 3, 4]), "LBTYA")
    wantL = PXl["C"][2:] / PXl["C"][1:4] - 1                        # C 만 남는다
    gotX, hitX = mkt_excl(MK2, "LA", None, np.array([2, 3, 4]), "OTHER")   # 선언 없는 티커면 LK 가 남는다
    t["sibling_excl_ok"] = bool(np.allclose(gotL, wantL, rtol=0, atol=1e-15) and sorted(hitL) == ["LA", "LK"] and hitX == ["LA"])
    # 10) 빼기 규칙 — 결측 먼저(Eg 순) · 높은 통계 · 동률 티커
    pool = [("T%02d" % j, "K%02d" % j) for j in range(45)]
    st = {k: float(j % 7) for j, (_, k) in enumerate(pool)}
    miss = {"K03", "K40"}
    keep, nm_ = drop_rule(pool, {k: v for k, v in st.items() if k not in miss}, miss)
    dropped = [x for x in pool if x not in keep]
    exp_drop = {"K03", "K40"} | {k for _, k in sorted([x for x in pool if x[1] not in miss], key=lambda x: (-st[x[1]], x[0]))[:13]}
    t["drop_rule_ok"] = bool(len(keep) == 30 and {k for _, k in dropped} == exp_drop and nm_ == 2 and keep == [x for x in pool if x in keep])
    # 11) C2 위약 빼기 — 판정 판: 결측은 늘 빠지고 무작위 몫은 결측 밖에서만 · 씨앗 재현 · 결측 > 15 면 Eg 순 앞 15 · 문자 판: 균등 15
    okp = True
    for sd in range(20):
        kp = _placebo_keep(pool, miss, np.random.default_rng(Q.SEED + sd))
        okp &= len(kp) == 30 and not ({"K03", "K40"} & {k for _, k in kp}) and kp == _placebo_keep(pool, miss, np.random.default_rng(Q.SEED + sd))
        kl = _placebo_keep(pool, None, np.random.default_rng(Q.SEED + sd))
        okp &= len(kl) == 30
    big = {k for _, k in pool[:17]}
    kb = _placebo_keep(pool, big, np.random.default_rng(Q.SEED))
    okp &= [x[1] for x in pool if x not in kb] == [k for _, k in pool[:15]]
    # 뽑기 200 번이면 45 이름이 모두 한 번은 빠진다(결측 둘은 늘 · 나머지 43 은 균등 무작위로)
    seen = set()
    for sd in range(200):
        seen |= {k for _, k in pool} - {k for _, k in _placebo_keep(pool, miss, np.random.default_rng(Q.SEED + sd))}
    okp &= seen == {k for _, k in pool}
    t["placebo_keep_ok"] = bool(okp)
    # 12) 단일 족 최우 = 고운 격자 최대 이상(1차원 · 네 족) · 결정적 시작이 든 혼합 최우 ≥ 씨앗 셋만의 최우 · 시작 진단 일관
    oks = True
    for nm in ("clayton", "frank", "plackett", "gauss", "rjoe"):
        xs_ = np.linspace(-12, 12, 4801)
        llf = fam_lpdf(nm, Vc, Vcr, th_of(nm, xs_)[:, None]).sum(axis=1)
        x1_, l1_ = single_mle(nm, Vc, Vcr)
        oks &= bool(l1_ >= float(np.nanmax(llf)) - 1e-6)
    f3 = fit_mix(("clayton", "fgm", "gumbel"), Vc, Vcr, starts())
    oks &= bool(f1["ll"] >= f3["ll"] - 1e-12 and len(f1["ll_starts"]) == N_START + 1 and 1 <= f1["n_near"] <= N_START + 1
                and f1["ll_starts"][f1["best_start"]] == f1["ll"])
    t["single_mle_det_ok"] = bool(oks)
    # 13) 적합 지문 — 사전 순서와 무관 · 값이 바뀌면 바뀐다
    fa = {"b" * 64: {"ltd": 0.1, "w": [0.2, 0.3, 0.5]}, "a" * 64: {"ltd": float("nan"), "se": None}}
    fb = dict(reversed(list(fa.items())))
    fc_ = {k: dict(v) for k, v in fa.items()}
    fc_["b" * 64]["ltd"] = 0.1000000001
    t["manifest_ok"] = bool(manifest(fa) == manifest(fb) and manifest(fa) != manifest(fc_))
    keys = [k for k, v in t.items() if k.endswith("_ok")]
    return {"ok": all(t[k] for k in keys), "tests": t}


def dry(ctx) -> dict:
    """랩 자료로 구성만 — 커버리지 · 결측 · 적합(캐시 채움) · 개수 · 비중 합 · 한도 · 날짜 단언 · V0 구성 재현 · 사전 베타. 수익 없음."""
    t0 = time.time()
    out = {"forms": len(formations(ctx)), "est_hash": EST_HASH[:16], "cache": CACHE}
    P = pools(ctx)
    MK = market(ctx)
    out["market_sec"] = MK["sec"]
    cov = MK["cover"]
    out["market_members"] = [min(c[1] for c in cov), max(c[1] for c in cov)]
    out["market_priced_share"] = [round(min(c[2] / max(1, c[1]) for c in cov), 3), round(max(c[2] / max(1, c[1]) for c in cov), 3)]
    rows, units = prep(ctx)
    out["units"] = len(units)
    out["units_cached_before"] = sum(1 for k, _, _ in units if cache_get(k) is not None)
    fits, st = estimate(units)
    out["estimate"] = st
    sig = signals(ctx, fits)
    T, rec = build_targets(ctx, sig)
    out["v0_rebuild_gap"] = v0_check(ctx)
    bad = 0
    for v in VARIANTS:
        for m, tg in T[v].items():
            s = sum(tg["w"].values())
            if abs(s - 1) > 1e-9 or min(tg["w"].values()) < 0 or max(tg["w"].values()) > CAP + 1e-9 or len(tg["w"]) != POOL - DROP:
                bad += 1
    miss = v1_miss(sig)
    bad_forced = 0
    for i_ in (0, 1):
        for ms in (miss, None):
            Tp = placebo_targets(ctx, i_, ms)
            bad += sum(1 for m, tg in Tp.items() if abs(sum(tg["w"].values()) - 1) > 1e-9 or len(tg["w"]) != POOL - DROP)
            if ms is not None:                                # 판정 위약: V1 결측은 늘 빠진다
                bad_forced += sum(1 for m, tg in Tp.items() if set(tg["w"]) & miss[m])
    out["bad_weights"] = bad
    out["placebo_forced_leak"] = bad_forced
    out["placebo_hash0"] = {"C2_random_drop": thash(placebo_targets(ctx, 0, miss))[:12], "C2_uniform_literal": thash(placebo_targets(ctx, 0))[:12]}
    dg = diag(ctx, rows, fits, sig, T)
    fr = dg["formations"]
    out["n_pairs"] = [dg["n_pairs_min"], dg["n_pairs_median"]]
    out["miss_ltd"] = [min(r["miss"]["miss_ltd"] for r in fr), max(r["miss"]["miss_ltd"] for r in fr)]
    out["miss_beta"] = [min(r["miss"]["miss_beta"] for r in fr), max(r["miss"]["miss_beta"] for r in fr)]
    out["miss_gt15"] = sum(1 for r in rec if r["miss_V1"] > DROP)
    out["overlap_V0"] = [min(r["overlap_V0"] for r in fr), max(r["overlap_V0"] for r in fr)]
    db = [r["dbeta_exante"] for r in fr if r["dbeta_exante"] is not None]
    out["dbeta_exante"] = [round(min(db), 3), round(float(np.median(db)), 3), round(max(db), 3)] if db else None
    out["dbeta_exante_within_005"] = sum(1 for x in db if abs(x) <= 0.05)
    out["family_top5"] = list(dg["family_freq"].items())[:5]
    out["n_families_selected"] = len(dg["family_freq"])
    out["flags"] = dg["flags"]
    out["se_median_q90"] = [dg["se_median"], dg["se_q90"]]
    out["n_bound_mean"] = dg["n_bound_mean"]
    out["ols_b"] = [round(min(r["miss"]["ols"]["V1"]["b"] for r in fr if r["miss"]["ols"]["V1"]), 3),
                    round(max(r["miss"]["ols"]["V1"]["b"] for r in fr if r["miss"]["ols"]["V1"]), 3)]
    out["cik_only_hits"] = sum(r["cik_only"] for r in fr)
    out["no_self_in_market"] = sum(1 for m in rows for r in rows[m]["names"] if not r["hit"])
    out["windows"] = [[fr[0]["win0"], fr[0]["last_date"]], [fr[-1]["win0"], fr[-1]["last_date"]]]
    out["hash"] = {v: thash(T[v])[:12] for v in VARIANTS}
    out["turn_proxy"] = {v: round(_proxy_turn(T[v]), 3) for v in VARIANTS}
    out["max_w"] = max(max(r["max_w"].values()) for r in fr)
    out["forced_V1"] = {"forms": sum(1 for r in rec if r["miss_V1"]), "names": sum(r["miss_V1"] for r in rec)}
    out["starts"] = dg["starts"]
    out["price_quantum"] = {"units_quantum_gt_0.5pct": dg["price_quantum"]["units_quantum_gt_0.5pct"],
                            "units_ties_ge10": dg["price_quantum"]["units_ties_ge10"], "forms": len(dg["price_quantum"]["forms"]),
                            "names": sorted({t for v in dg["price_quantum"]["forms"].values() for t in v})}
    out["tau_corr"] = dg["tau_corr"]
    out["f0_proposed"] = _f0_proposed(ctx, T, rec)
    out["sibling_hits"] = sorted({(m, r["t"], tuple(r["hit"])) for m in rows for r in rows[m]["names"] if r["t"] in SIBLINGS})[:6]
    lab = {k: fits[k] for k, _, _ in units}
    out["manifest"] = manifest(lab)
    out["manifest_frozen"] = FITS_MANIFEST
    out["manifest_match"] = bool(FITS_MANIFEST is not None and out["manifest"] == FITS_MANIFEST)
    ep = os.path.join(CACHE_ROOT, EST_HASH[:16] + "_fits.json")
    export_fits(lab, ep)
    out["export"] = {"path": ep, "mb": round(os.path.getsize(ep) / 1e6, 2), "n": len(lab)}
    out["gauss_calib"] = gauss_calib()
    out["sec"] = round(time.time() - t0, 1)
    out["ok"] = bool(bad == 0 and bad_forced == 0 and out["v0_rebuild_gap"] < 1e-12 and out["miss_gt15"] == 0 and len(lab) == FITS_N)
    return out


def _ltd_log(rows, fits):
    """편입별 이름 기록 — LTD · 적합 진단 · 가격 양자(신호만 · 성과 없음)."""
    FK = ("ltd", "utd", "se", "label", "w", "th", "flags", "n_bound", "ties", "n_near", "gap12", "best_start", "D_gap_rel")
    return {m: [{"t": r["t"], "k": r["k"], "beta": r["beta"], "n": r["n_mx"],
                 **({kk: fits[r["key_mx"]].get(kk) for kk in FK} if r["key_mx"] else {}), "np_ltd": r.get("np_ltd"), "tau": r.get("tau"),
                 "px_min": r.get("px_min"), "quantum": r.get("quantum"), "zero_ret": r.get("zero_ret"),
                 "ltd_spx": (fits[r["key_spx"]].get("ltd") if r["key_spx"] else None)} for r in rows[m]["names"]]
            for m in rows}


def _f0_proposed(ctx, T, rec):
    diffs = sum(1 for m in T["V1"] if set(T["V1"][m]["w"]) != set(ctx.V0_targets[m]["w"]))
    thin = sum(1 for r in rec if r["miss_V1"] >= DROP)
    return {"v1_ne_v0_forms": diffs, "n_forms": len(T["V1"]), "forms_miss_ge15": thin, "would_pass": bool(diffs > 0 and thin == 0)}


def run(ctx) -> dict:
    """한 번 굽기 — Q07 CardResult. 🚨 결과 값을 찍지 않는다. 적합은 얼린 것만(strict — 다시 적합하지 않는다)."""
    t0 = time.time()
    rows, fits, st = fit_all(ctx, strict=True)
    sig = signals(ctx, fits)
    T, rec = build_targets(ctx, sig)
    gap = v0_check(ctx)
    assert gap < 1e-12, "V0 구성 재현 실패"
    fr = {v: ctx.stock_fr(T[v], reb=3, basis="TR") for v in VARIANTS}
    fr_pr, fr20 = ctx.stock_fr(T["V1"], reb=3, basis="PR"), ctx.stock_fr(T["V1"], reb=3, basis="TR", cost=COST20)
    v0, v0_20 = ctx.V0(), ctx.V0(cost=COST20)
    b0 = sleeve_beta(ctx, v0)
    g4 = {"C3_dbeta_down_gt0": bool(dbeta_down(ctx, fr["V1"], fr["C3"]) > 0)}
    true = dbeta_down(ctx, fr["V1"], v0, bb=b0)
    miss = v1_miss(sig)
    tp = time.time()
    pl = {}
    for name, ms in (("C2_random_drop", miss), ("C2_uniform_literal", None)):
        draws = []
        for i in range(NPERM):
            fri = ctx.stock_fr(placebo_targets(ctx, i, ms), reb=3, basis="TR")
            draws.append(dbeta_down(ctx, fri, v0, bb=b0))
            del fri
        pl[name] = {"draws": draws, "true": true, "p95": (float(np.percentile(draws, 95)) if draws else None)}
    pl["C2_random_drop"]["stat"] = ("G4 판정 · 하락월(39) 평균 Δβ(C2_i − V0) · C2_i = 편입마다 V1 과 같은 결측을 먼저 빼고 나머지를 "
                                    "결측 아닌 이름에서 균등 무작위로 15 까지 · 씨앗 SEED + i")
    pl["C2_uniform_literal"]["stat"] = "기록만(판정 아님) · 같은 통계 · C2_i = 편입마다 P 45 에서 균등 무작위 15(카드 문구 그대로) · 씨앗 SEED + i"
    p95 = pl["C2_random_drop"]["p95"]
    g4["placebo_ge95"] = bool(p95 is not None and true >= p95)
    dg = diag(ctx, rows, fits, sig, T)
    f0p = _f0_proposed(ctx, T, rec)
    f0 = {"ok": True, "why": "카드에 F0 없음 — 측정 불가 조건을 만들지 않는다(제안 F0 는 log.f0_proposed 기록만)"}
    q07 = {"code": "Q07", "cls": "B", "slot": "B2", "fr": fr["V1"], "fr_pr": fr_pr, "fr20": fr20,
           "controls": {"V0": v0, "V0_20": v0_20, "C3": fr["C3"]},
           "arms": {"A1": fr["A1"], "A2": fr["A2"], "A3": fr["A3"], "A4": fr["A4"]},
           "placebo": pl,
           "perm": None, "g4": g4, "label_caps": {}, "f0": f0, "targets_hash": thash(T["V1"]),
           "log": {"interpretation": INTERP, "est_hash": EST_HASH, "fits_manifest": st.get("manifest"), "estimate": st,
                   "formations": rec, "diag": dg, "f0_proposed": f0p, "gauss_calib": gauss_calib(),
                   "placebo_gate": "C2_random_drop", "forced_V1": {r["m"]: r["miss_V1"] for r in rec if r["miss_V1"]},
                   "controls": {v: {"hash": thash(T[v]), "turn_proxy": _proxy_turn(T[v])} for v in VARIANTS},
                   "turn": {v: fr[v].get("turn") for v in VARIANTS},
                   "ltd": _ltd_log(rows, fits),
                   "placebo": {"n": NPERM, "sec": round(time.time() - tp, 1)}, "sec": round(time.time() - t0, 1)}}
    return {"Q07": q07}


if __name__ == "__main__":
    r = selftest()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(0 if r["ok"] else 1)
