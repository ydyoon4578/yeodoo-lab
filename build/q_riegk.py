# -*- coding: utf-8 -*-
"""build/q_riegk.py — 배치 Q · Q02 FE1-RIEGK(RMT 정제 공분산 최적 능동 Eg 슬리브) · Q13 FE3-CRASHEIG(폭락일 고유값 재추정 · Q02 의 자식).

근본 이유: EG30 은 Eg 상위 30 을 시가총액(상한 20%)으로 담아 종목 간 상관을 보지 않는다. 그래서 바스켓 능동위험의 대부분이 Eg 신호가
아니라 시장 모드와 초대형 성장주 한 덩어리에 쌓이고, 하락장에서 상관이 오르면 그 덩어리가 한꺼번에 빠진다. Grinold-Kahn 최적 능동비중
x ∝ Σ⁻¹α 는 같은 추적오차 예산을 보상받는 위험(Eg)에만 쓰고 보상 근거가 없는 공통 모드는 비싸게 쳐서 줄인다. 약 500종 × 1000일
표본 상관의 작은 고유값은 잡음이라 회전불변 추정(BBP IWs-RIE)으로 정제한다. 무엇을 사느냐(Eg 후보 60)는 그대로, 얼마나 사느냐만 푼다.
Q13 은 같은 고유벡터를 두고 고유값만 S&P 500 최악 10% 날의 2차 적률과 반씩 섞어 «폭락일에만 커지는 모드» 를 비싸게 친다.

규칙(카드 원문 scratchpad/qbatch_final.md # Q02 · # Q13 — 여기 숫자는 모두 카드에 적힌 것):
  편입 = EG30 과 같다(EG_BASE · 2016-08 + 분기말 41번 · 보유 2016-09 ~ 2026-08 · 사이는 흘러감 · 편도 10bp · 펀드 90/10).
  U = union 명단(ex_fin=False) · w_b = U 안 PIT S&P 500 시총 비중(NASDAQ 100 전용 = 0) · R = 1000일 중 유효 수익 ≥ 750 · 252일 중 ≥ 120.
  Y = 1000일 일간 단순수익 → 종목별 평균 빼기 → 그날 횡단 규모 √Σr² 로 나누기(BBP 8.13) → 종목별 표준화 → 빈칸 0 · E = YY'/T · q = N/T.
  IWs-RIE = BBP Algorithm 1(η = N^-1/2 · λ<1 에 역위샤트 Γ 보정 · κ_IW = 2λ_N/((1−q−λ_N)² − 4qλ_N)) + 정렬 · 흔적 N · Ξ 단위 대각.
  σ = √252 × 252일 로그수익 sd · Σ = diag σ Ξ diag σ · α = ω z(P60 ∩ R 만) · ω = √252 × 252일 S&P 500 PR 회귀 잔차 sd.
  max α'x − κ/2 x'Σx · x ≥ −w_b · Σx = 0 · R 밖 x = 0 · SLSQP(ftol 1e-12 · 2000) → trust-constr(gtol 1e-10 · 5000) → 둘 다 실패면 EG30 유지.
  κ: log10 κ ∈ [−4, 6] 이분(|TE − TE*| ≤ 1e-4 · 60번 · κ = 10^-4 끝은 이분이 아래 끝을 못 벗어났을 때만 푼다)
     · TE* = EG30 의 사전 TE(d = w_EG30 − w_b ≠ 0 인 R 밖 이름 — EG30 이름과 벤치 이름 모두 — 은 시점정확 업종 평균 상관 · 252일 σ 로 Σ̃ 확장).
  Q13: Ξ = ½ U diag(ξ̂) U' + ½ U diag(ξᶜ) U'(단위 대각) · ξᶜ_k = D_c(창 안 S&P 500 PR 최악 100일)에서 (u_k'Y_t)² 평균 · TE* 는 같은 Σ_blend 로.
  대조: C2 Ξ = I(G4 · Δβ(FE1 − C2) 하락월 평균 > 0) · 측정만 팔 C3 표본 상관 · A1 Laloux 자르기(1+√q)² · A2 Ledoit-Wolf 2020 비선형 축소.
  Q13 위약: D_c 를 창 안 균등 무작위 100일로(NPERM 번 · 씨앗 SEED + i) · 참 Δβ(FE3 − FE1) ≥ 위약 95 백분위 · 거울 C3(최상 10% 날)은 측정만.

출처: Bun·Bouchaud·Potters(2017) Physics Reports 666 · arXiv 1610.08104 — §8.1.2 Algorithm 1 · 식 (3.41)(역위샤트 Stieltjes) · (7.55)(자르기)
  · (8.13)(횡단 규모) · (8.15)–(8.16)(고유포트폴리오 실현 2차 적률) / Ledoit·Wolf(2020) Annals of Statistics 48(5) §4.7 / Grinold(1994) /
  Chow·Jacquier·Kritzman·Lowry(1999)(섞기 착안) / Longin·Solnik(2001).
  🚨 Algorithm 1 본문(추출 텍스트)은 g_iw 의 제곱근 앞 κ 가 빠져 있다 — 식 (3.41) 은 κ√(z−λ+)√(z−λ−) 이고 κ 가 없으면 밀도 질량이 1/κ 가 된다
    (selftest 가 질량 1 · 띠 안 선형축소 항등식을 잰다). 식 (3.41) 을 쓴다.

🚨 이 모듈은 selftest · dry 에서 규칙 · 대조 · 팔 · 위약의 수익을 계산하거나 찍지 않는다. run() 은 한 번 굽기에서만 부른다.
"""
from __future__ import annotations
import contextlib, hashlib, io, json, math, os, pickle, shutil, subprocess, sys, tempfile, time

import numpy as np
from scipy.linalg import cho_factor, cho_solve, LinAlgError
from scipy.optimize import minimize, Bounds, LinearConstraint

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q              # noqa: E402

CARDS = {"Q02": {"cls": "B", "slot": "B1"},
         "Q13": {"cls": "C", "slot": None, "parent": "Q02"}}
NPERM = 1000                         # Q13 위약 횟수(카드) — 연기 시험에서 작게 덮어쓴다
NPROC = max(1, min(6, (os.cpu_count() or 2) - 1))   # 위약 병렬 일꾼 수(실행만 — 씨앗이 뽑기마다라 결과는 같다 · 한 코어는 본 프로세스 경로 계산)

# ── 카드 상수 ─────────────────────────────────────────────────────────────
T_WIN, MIN_T, VOL_WIN, MIN_V = 1000, 750, 252, 120      # 창 · 최소 관측(랩 FP 상수)
SIG_MIN_O = 60                        # R 밖 EG30 이름 σ 최소 관측(카드 (8))
SEC_MIN = 5                           # 업종 평균 상관을 쓰는 최소 R 이름 수(카드 (8))
WINS = 3.0                            # z 윈저(±3)
POOL = 60                             # Eg 후보(2 × 바스켓)
LOGK = (-4.0, 6.0)                    # log10 κ 이분 구간
TE_TOL, BIS_MAX = 1e-4, 60            # 이분 허용 오차 · 최대 걸음
SLSQP_OPT = {"ftol": 1e-12, "maxiter": 2000}
TC_OPT = {"gtol": 1e-10, "maxiter": 5000}
CRASH_Q, BLEND = 0.10, 0.5            # Q13 폭락일 몫(랩 CVAR_Q) · 섞기 ½
COST20 = 0.0020                       # 20bp 판
# ── 구현 상수(카드가 정하지 않은 수치 잡음 한계 — 결과를 바꾸지 않는 크기) ──
FEAS_TOL = 1e-9                       # 풀이 결과 실현 가능성(하한 · 합) 허용
W_EPS = 1e-9                          # 목표 비중 이 아래는 0(풀이 허용 오차 크기)
PDAS_MAX = 200                        # 활성집합 시작점 반복 한계(SLSQP 시작점만 — 해는 SLSQP 가 낸다)
HASH_DEC = 9                          # targets_hash 는 비중을 소수 9자리로 반올림해 잰다(BLAS 스레드 수에 따른 ~1e-15 차가 해시를 바꾸지 않게)
RESPAWN_MAX = 1                       # 위약 일꾼 자리마다 죽으면 새로 띄우는 횟수(그 뒤는 본 프로세스가 같은 씨앗으로)
BLAS_ENV = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
LW_SER, LW_TERMS = 10.0, 16           # A2 Hilbert 항: |x| > 10 은 급수(u² < 0.05 · 16항이면 0.05^16 ≈ 1e-21 까지 — 원식과 값이 같다)

VARIANTS = ("FE1", "C2", "C3", "A1", "A2", "FE3", "FE3m")
INTERP = [
    "Y 의 일간 수익은 단순수익(연구 카드 원판 'daily simple returns') · σ 는 카드대로 로그수익 · ω 회귀도 단순수익(r_i 표기가 Y 와 같다).",
    "표준화 · 횡단 규모는 유효 관측만으로(ddof 0 · 빈칸 0) · 횡단 규모는 평균 뺀 수익으로 잰다(카드 순서).",
    "IWs 정렬 = 정규화된 ξ 를 λ 순서대로 다시 늘어놓기(BBP §8.1.2 'sorting') · 흔적은 카드대로 N(Ξ 단위 대각이라 크기는 상쇄).",
    "g_iw 는 BBP 식 (3.41)(제곱근 앞 κ) — Algorithm 1 추출문은 κ 가 빠진 전사 오류(selftest 로 확인).",
    "κ_IW 분모 ≤ 0(λ_N 이 MP 아래 끝 위) 이면 κ_IW = ∞ 극한 = Marchenko-Pastur g(식이 수렴하는 값) · 표식 kiw_inf.",
    "z · ω · σ 의 sd 는 ddof 1 · z 는 R 안 Eg 가 선 이름 · 윈저 ±3 뒤 다시 표준화(ddof 1).",
    "C2 · C3 · A1 · A2 · FE3 · 위약은 «같은 최적화기» = 그 Ξ 로 (7)·(8) 전부(TE* 의 Σ̃ 확장 · 업종 평균 상관 포함)를 다시 푼다"
    " — 그래서 C2(Ξ = I)의 TE* 와 TE 는 C2 자신의 대각 Σ 로 잰다(Q13 의 'EG30 의 사전 TE 를 Σ_blend 로' 와 같은 읽기 · 카드 문구 고정 요청).",
    "TE* = √(d'Σ̃d) · d = w_EG30 − w_b 의 받침 전체 — R 밖이면서 d ≠ 0 인 이름은 EG30 이름이든 벤치(S&P) 이름이든 카드 (8) 의 선언된 대체"
    "(업종 평균 비대각 Ξ · 252일 σ ≥ 60 관측 · 아니면 업종 중앙값 σ)로 Σ̃ 에 넣는다(카드는 EG30 이름만 적었다 — 벤치 이름을 빼면 식이 정의되지 않는다 · 카드 수정 요청).",
    "R 밖 이름 o 의 상관 = o 업종 R 이름 평균 비대각 Ξ(o 와 모든 R 이름에 같은 값 · 업종 R 이름 5 미만이거나 업종을 모르면 시장 평균)"
    " · R 밖 두 이름 짝 = 두 값의 평균 0.5(ρ_a + ρ_b)(같은 업종이면 ρ_a = ρ_b 라 그 값) — 업종이 다른 R 밖 EG30 짝은 2021-03 · 2021-06 · 2021-09 에 실제로 있다(log common 'n_O30_xsec').",
    "업종 = 시점정확 GICS 만: Wd.sector 가 그달 표('month')에서 찾은 값 → 없으면 m 이전 달 표 중 가장 늦은 값 → 없으면 모름."
    " Wd.sector 의 이후 달 · 오늘 GICS 대체(미래 분류 — R 이름 편입마다 10~17개)는 쓰지 않는다. 모르는 이름은 업종 모둠에서 빠진다.",
    "R 밖 이름 σ 가 60 관측 미만이면 같은 업종 R 이름 σ 중앙값(업종을 모르거나 업종에 R 이름이 없으면 R 전체 중앙값).",
    "SLSQP 시작점 = 같은 볼록 QP 의 원쌍대 활성집합 해(KKT) — 해 · 성공 판정 · 대체는 카드대로 SLSQP → trust-constr → EG30 유지.",
    "trust-constr 에는 해석적 헤시안(κΣ)을 준다.",
    "이분은 가운데(log10 κ = 1)부터 걷는다. κ = 10^-4(거의 LP · SLSQP 가 가끔 멈추는 점)는 모든 걸음에서 TE < TE* 라 아래 끝을 못 벗어났을 때만 풀어"
    " 닿지 않음(te_unreach)을 가린다 — TE 는 κ 에 단조 감소라 한 걸음이라도 TE > TE* 면 닿는다. 쓰지 않을 점의 풀이 실패로 EG30 유지가 되지 않게 한 순서다(어느 걸음의 풀이든 둘 다 실패하면 카드대로 유지).",
    "목표 비중 < 1e-9 는 0 으로 두고 합 1 로 다시 맞춘다(풀이 허용 오차).",
    "A2(LW2020)의 Hilbert 항은 |x| > 10 에서 같은 식의 정확한 급수로 잰다 — 원식은 바깥 고유값(λ1 ≈ 100 · |x| ~ 7e4)에서 선형항과 로그항이 서로 지워져"
    " 상대 오차 ~6e-4(축소 고유값 ~2e-5)를 내고 BLAS 스레드 수에 따라 비중이 ~8e-8 흔들렸다. 급수는 60자리 기준값과 1e-13 안에서 같다(selftest). 식은 LW2020 그대로다.",
    "targets_hash = 비중을 소수 9자리로 반올림한 목표 경로의 sha256(json · 키 정렬) — BLAS 스레드 수에 따라 비중이 ~1e-15 달라져 원값 해시는 재현되지 않는다(원값 해시는 log 'hash_exact' · 스레드 설정은 log 'blas_env').",
    "Q13 D_c 동률은 날짜 순(안정 정렬) · 위약 D_c 는 편입마다 창 1000일에서 비복원 균등 100일(뽑기 i 는 씨앗 SEED + i 한 줄기로 편입 순서대로).",
    "Q13 ξᶜ 는 규모를 맞추지 않은 원래 2차 적률(카드 (3)) · ξ̂ 는 흔적 N 의 IWs.",
    "Q13 위약 G4 = 참 Δβ ≥ numpy percentile(draws, 95)(선형 보간).",
    "Q02 · Q13 에 카드 F0 가 없다 — f0.ok = 규칙이 한 편입이라도 풀렸는가(모두 EG30 유지면 규칙 = V0 라 측정 불가).",
    "위약은 하위 프로세스 일꾼(BLAS 1스레드)이 뽑기를 나눠 푼다 — 뽑기 i 의 씨앗은 SEED + i 라 일꾼 수 · 순서와 무관하다. 일꾼이 죽으면 그 자리의 남은 뽑기를 새 일꾼에 한 번 넘기고,"
    " 그래도 죽으면 본 프로세스가 같은 씨앗으로 푼다. 소비 쪽이 중간에 멈추면 남은 일꾼을 죽이고 임시 폴더를 지운다.",
]


# ── 선형대수 도구 ─────────────────────────────────────────────────────────
def unit_diag(C):
    C = 0.5 * (C + C.T)
    d = np.sqrt(np.clip(np.diag(C), 1e-300, None))
    C = C / np.outer(d, d)
    np.fill_diagonal(C, 1.0)
    return C


def corr_eig(U, xi):
    """U diag(ξ) U' → 단위 대각."""
    return unit_diag((U * xi) @ U.T)


def g_iw(z, q, k):
    """역위샤트(κ) 모집단 표본 행렬 E 의 Stieltjes 변환 — BBP 식 (3.41)(Algorithm 1 의 g_iw · 제곱근 앞 κ). κ = ∞ 는 MP."""
    z = np.asarray(z, complex)
    if not np.isfinite(k):
        lp, lm = (1 + math.sqrt(q)) ** 2, (1 - math.sqrt(q)) ** 2
        return (z + q - 1 - np.sqrt(z - lp) * np.sqrt(z - lm)) / (2 * q * z)
    s = math.sqrt((2 * k + 1) * (2 * q * k + 1))
    lp, lm = ((1 + q) * k + 1 + s) / k, ((1 + q) * k + 1 - s) / k
    return (z * (1 + k) - k * (1 - q) - k * np.sqrt(z - lp) * np.sqrt(z - lm)) / (z * (z + 2 * q * k))


def _rie(z, q, g):
    return z.real / np.abs(1 - q + q * z * g) ** 2


def rie_iws(lam, q):
    """BBP Algorithm 1(IW 보정) + 정렬(IWs) · 흔적 N. lam 내림차순 → (ξ, 정보)."""
    lam = np.asarray(lam, float)
    N = len(lam)
    z = lam - 1j / math.sqrt(N)
    G = 1.0 / (z[:, None] - lam[None, :])
    np.fill_diagonal(G, 0.0)
    g = G.sum(1) / (N - 1)
    xi = _rie(z, q, g)
    lN = float(lam.min())
    den = (1 - q - lN) ** 2 - 4 * q * lN
    kiw = 2 * lN / den if den > 0 else math.inf
    flag = not (np.isfinite(kiw) and kiw > 0)
    if flag:
        kiw = math.inf
    a = 0.0 if not np.isfinite(kiw) else 1.0 / (1 + 2 * q * kiw)
    gam = (1 + a * (lam - 1)) / _rie(z, q, g_iw(z, q, kiw))
    ap = (gam > 1) & (lam < 1)
    xi = np.where(ap, xi * gam, xi)
    xi = xi * (N / xi.sum())
    o = np.argsort(-lam, kind="stable")
    out = np.empty_like(xi)
    out[o] = np.sort(xi)[::-1]
    return out, {"kiw": (None if not np.isfinite(kiw) else float(kiw)), "kiw_inf": bool(flag), "n_gamma": int(ap.sum())}


def clip_laloux(lam, q):
    """A1 — λ ≥ (1+√q)² 는 두고 나머지는 흔적을 지키는 한 값(BBP 식 7.55)."""
    lam = np.asarray(lam, float)
    keep = lam >= (1 + math.sqrt(q)) ** 2
    out = lam.copy()
    if (~keep).any():
        out[~keep] = lam[~keep].mean()
    return out


def _lw_hilbert(x, ser=True):
    """LW2020 의 Epanechnikov Hilbert 항 (−3/10π)x + (3/4√5π)(1 − x²/5)·log|(√5 − x)/(√5 + x)|.
    |x| 가 크면(바깥 고유값 λ1 ≈ 100 에서 |x| ~ 10^4) 두 항이 서로 지워져 float64 자릿수를 잃는다 — |x| > LW_SER 는 같은 식의 정확한 급수
    −(3/(√5π)) Σ_k u^(2k−1)/((2k−1)(2k+1)) (u = √5/x) 로 잰다(값은 같고 반올림 잡음만 없앤다 · ser=False 는 원식 — selftest 비교용)."""
    x = np.asarray(x, float)
    a = math.sqrt(5.0)
    big = (np.abs(x) > LW_SER) if ser else np.zeros(x.shape, bool)
    out = np.empty_like(x)
    xs = x[~big]
    with np.errstate(divide="ignore", invalid="ignore"):
        lg = np.log(np.abs((a - xs) / (a + xs)))
    v = (-3.0 / 10.0 / math.pi) * xs + (3.0 / 4.0 / a / math.pi) * (1 - xs ** 2 / 5.0) * lg
    edge = np.isclose(np.abs(xs), a, rtol=0, atol=1e-15)
    v[edge] = ((-3.0 / 10.0 / math.pi) * xs)[edge]
    out[~big] = v
    if big.any():
        u = a / x[big]
        u2, pw, s = u * u, u.copy(), np.zeros_like(u)
        for k in range(1, LW_TERMS + 1):
            s += pw / ((2 * k - 1) * (2 * k + 1))
            pw = pw * u2
        out[big] = -(3.0 / (a * math.pi)) * s
    return out


def lw2020(lam, n, ser=True):
    """A2 — Ledoit-Wolf 2020 해석적 비선형 축소(§4.7 · p ≤ n · Epanechnikov · h = n^-1/3 · 고유값 비례 띠)."""
    lam = np.asarray(lam, float)
    p = len(lam)
    h = n ** (-1.0 / 3.0)
    H = h * lam[None, :]
    x = (lam[:, None] - lam[None, :]) / H
    f = (3.0 / 4.0 / math.sqrt(5.0)) * np.mean(np.maximum(1 - x ** 2 / 5.0, 0.0) / H, axis=1)
    ht = _lw_hilbert(x, ser)
    Hf = np.mean(ht / H, axis=1)
    c = p / n
    return lam / ((math.pi * c * lam * f) ** 2 + (1 - c - math.pi * c * lam * Hf) ** 2)


def build_Y(R):
    """R: N×T 단순수익(빈칸 NaN) → Y(BBP 8.13 · 종목 평균 빼기 → 횡단 규모 → 종목 표준화 → 빈칸 0)."""
    V = np.isfinite(R)
    nv = V.sum(1)
    X = np.where(V, R, 0.0)
    X = np.where(V, X - (X.sum(1) / nv)[:, None], 0.0)
    s = np.sqrt((X ** 2).sum(0))
    s[s <= 0] = 1.0
    X = X / s[None, :]
    mu = X.sum(1) / nv
    X = np.where(V, X - mu[:, None], 0.0)
    sd = np.sqrt((X ** 2).sum(1) / nv)
    return X / sd[:, None]


# ── 볼록 QP ───────────────────────────────────────────────────────────────
class SolveFail(Exception):
    pass


def _feasible(x, lb):
    return bool(np.all(x - lb >= -FEAS_TOL) and abs(float(x.sum())) <= FEAS_TOL and np.all(np.isfinite(x)))


def _kkt(S, a, lb, act):
    """활성집합 act(x = lb) 고정 · 나머지는 등식 KKT(1'x = 0) 풀이."""
    F = ~act
    if not F.any():
        return None
    try:
        c = cho_factor(S[np.ix_(F, F)], check_finite=False)
    except (LinAlgError, ValueError):
        return None
    b = a[F] - (S[np.ix_(F, act)] @ lb[act] if act.any() else 0.0)
    y1 = cho_solve(c, b, check_finite=False)
    y2 = cho_solve(c, np.ones(int(F.sum())), check_finite=False)
    nu = (-float(lb[act].sum()) - float(y1.sum())) / float(y2.sum())
    x = lb.copy()
    x[F] = y1 + nu * y2
    return x, nu


def qp_active(S, a, lb, act0=None, maxit=PDAS_MAX):
    """min ½x'Sx − a'x · 1'x = 0 · x ≥ lb — 원쌍대 활성집합(Hintermüller-Ito-Kunisch). 수렴하면 (x, act, 반복), 아니면 None."""
    n = len(a)
    act = np.zeros(n, bool) if act0 is None else act0.copy()
    seen = set()
    tol_mu = 1e-12 * (1.0 + float(np.abs(a).max()))
    for it in range(1, maxit + 1):
        r = _kkt(S, a, lb, act)
        if r is None:
            return None
        x, nu = r
        mu = S @ x - a - nu
        new = np.where(act, mu > -tol_mu, x < lb - 1e-13)
        if np.array_equal(new, act):
            return x, act, it
        key = new.tobytes()
        if key in seen:
            return None
        seen.add(key)
        act = new
    return None


def _minimize(method, S, al, kap, lb, x0):
    n = len(al)
    one = np.ones(n)
    f = lambda x: float(-al @ x + 0.5 * kap * (x @ (S @ x)))
    g = lambda x: -al + kap * (S @ x)
    if method == "SLSQP":
        r = minimize(f, x0, jac=g, method="SLSQP", bounds=Bounds(lb, np.full(n, np.inf)),
                     constraints=[{"type": "eq", "fun": lambda x: float(x.sum()), "jac": lambda x: one}], options=dict(SLSQP_OPT))
        ok = bool(r.success)
    else:
        HS = kap * S
        r = minimize(f, x0, jac=g, hess=lambda x: HS, method="trust-constr", bounds=Bounds(lb, np.full(n, np.inf)),
                     constraints=[LinearConstraint(one[None, :], 0.0, 0.0)], options=dict(TC_OPT))
        ok = r.status in (1, 2)
    return r, ok and _feasible(r.x, lb)


def _skip(fail, method, kap):
    """selftest 전용 — fail 이 방법 이름 모음이면 그 방법을, 함수면 fail(방법, κ) 가 참인 점을 건너뛴다(실패 흉내)."""
    if fail is None:
        return False
    return bool(fail(method, kap)) if callable(fail) else method in fail


def qp_solve(S, al, lb, kap, st, fail=None, lk=None):
    """κ 한 점 — 시작점(활성집합 KKT 해 · 실패하면 앞 해 · 없으면 0) → SLSQP → trust-constr → SolveFail. st 는 다음 κ 의 따뜻한 시작."""
    st.setdefault("logk", []).append(float(math.log10(kap) if lk is None else lk))
    pre = qp_active(S, al / kap, lb, st.get("act"))
    if pre is not None:
        x0 = pre[0]
        st["act"] = pre[1]
        st["pdas_it"] = st.get("pdas_it", 0) + pre[2]
    else:
        x0 = st.get("x", np.zeros(len(al)))
        st["pdas_fail"] = st.get("pdas_fail", 0) + 1
    for method in ("SLSQP", "trust-constr"):
        if _skip(fail, method, kap):                      # selftest 전용 — 대체 경로 시험
            continue
        r, ok = _minimize(method, S, al, kap, lb, x0)
        if ok:
            st["x"] = r.x
            st[method] = st.get(method, 0) + 1
            st["nit"] = st.get("nit", 0) + int(getattr(r, "nit", 0) or 0)
            return r.x
    raise SolveFail("SLSQP · trust-constr 둘 다 실패(κ = %.3g)" % kap)


def te_match(S, al, lb, te_star, fail=None):
    """(8) log10 κ ∈ [−4, 6] 이분 → (x, log10 κ, TE, 걸음, 표식, 풀이 기록).
    TE(κ) 는 κ 에 단조 감소다. 그래서 가장 작은 κ(10^-4 · 거의 LP) 는 모든 걸음이 TE < TE* 여서 아래 끝을 못 벗어났을 때만 푼다
    (닿지 않으면 그 해 · te_unreach) — 쓰지 않을 점의 풀이 실패가 편입을 EG30 유지로 만들지 않게."""
    st = {}
    te = lambda x: float(math.sqrt(max(float(x @ (S @ x)), 0.0)))
    lo, hi = LOGK
    x, lk, t, steps = None, lo, None, 0
    for _ in range(BIS_MAX):
        mid = 0.5 * (lo + hi)
        if mid == lo or mid == hi:                       # 부동소수 구간이 닫혔다 — 더 걸어도 같은 점
            break
        steps += 1
        x, lk = qp_solve(S, al, lb, 10.0 ** mid, st, fail, mid), mid
        t = te(x)
        if abs(t - te_star) <= TE_TOL:
            return x, mid, t, steps, [], st
        if t > te_star:
            lo = mid
        else:
            hi = mid
    if lo == LOGK[0]:                                    # 한 번도 TE > TE* 가 아니었다 — 가장 작은 κ 에서 가린다
        x0 = qp_solve(S, al, lb, 10.0 ** LOGK[0], st, fail, LOGK[0])
        t0 = te(x0)
        if t0 < te_star - TE_TOL:
            return x0, LOGK[0], t0, steps, ["te_unreach"], st
        if abs(t0 - te_star) <= TE_TOL:
            return x0, LOGK[0], t0, steps, [], st
    return x, lk, t, steps, ["bis_max"], st


# ── 편입 준비(자료 → 행렬) ────────────────────────────────────────────────
_PREP = {}


def _cand():
    import eg30plus as E
    return dict(E.EG_BASE, index="union")


def formations(ctx):
    import eg30plus as E
    return E.formations(ctx.Wd)


def sector_pit(Wd, t, k, m):
    """시점정확 GICS 업종 — Wd.sector 가 그달 표('month')에서 찾으면 그 값 · 아니면 m 이전 달 표 중 가장 늦은 값(Wd._sector_lookup 과 같은
    CIK → 티커 열쇠) · 그것도 없으면 None. Wd.sector 의 이후 달 · 오늘 GICS 대체(미래 분류)는 쓰지 않는다."""
    if Wd.sector_src(t, k, m) == "month":
        return Wd.sector(t, k, m)
    cks = [c for c in (Wd.cikmap.get(t), Wd.cikmap.get(k), Wd.cikmap.get((t or "").replace("-", "."))) if c]
    tks = [x.replace("-", ".") for x in (t, k) if x]
    best = None
    for key in ["c:" + c for c in cks] + ["t:" + x for x in tks]:
        for ym, s in Wd.Gtl.get(key, ()):
            if ym < m and (best is None or ym > best[0]):
                best = (ym, s)
    return best[1] if best else None


def prep(ctx, m):
    """편입월 m — m 월말 종가까지만 쓴다(단언). 변형과 무관한 것(Y · 고유분해 · σ · α · w_b · EG30 · 업종)을 한 번 만든다."""
    ck = (id(ctx.Wd), m)
    if ck in _PREP:
        return _PREP[ck]
    Wd = ctx.Wd
    i = Wd.me[m]
    D = Wd.dates
    assert D[i][:7] == m and (i + 1 >= len(D) or D[i + 1][:7] > m), "편입일이 %s 의 마지막 거래일이 아니다" % m
    a0 = i - T_WIN
    assert a0 >= 1, "1000일 창이 가격 격자 앞으로 나간다(%s)" % m
    U = Wd.universe(m, "union", False)
    keys = [k for _, k in U]
    assert len(set(keys)) == len(keys), "union 가격 키가 겹친다(%s)" % m
    tick = {k: t for t, k in U}
    cm = Wd.W["cikmap"]
    cik = lambda t: cm.get(t) or cm.get(t.replace("-", ".")) or ("_" + t)
    spx = {cik(t) for t in (Wd.W["lists"]["spx"].get(m) or [])}
    is_spx = np.array([cik(t) in spx for t, _ in U])
    mc = np.array([Wd.mcap(t, k, i) or 0.0 for t, k in U])
    wb = np.where(is_spx, mc, 0.0)
    wb = wb / wb.sum()
    # 가격 창 a0..i(끝 = m 월말) — 이 뒤 자리는 읽지 않는다
    Pm = np.vstack([np.asarray(Wd.PX[k][a0:i + 1], float) for k in keys])
    assert Pm.shape[1] == T_WIN + 1
    with np.errstate(divide="ignore", invalid="ignore"):
        ok = np.isfinite(Pm[:, 1:]) & np.isfinite(Pm[:, :-1]) & (Pm[:, 1:] > 0) & (Pm[:, :-1] > 0)
        Rs = np.where(ok, Pm[:, 1:] / Pm[:, :-1] - 1.0, np.nan)
        Lr = np.where(ok, np.log(Pm[:, 1:] / Pm[:, :-1]), np.nan)
    n1000, n252 = ok.sum(1), ok[:, -VOL_WIN:].sum(1)
    inR = (n1000 >= MIN_T) & (n252 >= MIN_V)
    idxR = np.flatnonzero(inR)
    N = len(idxR)
    ix = np.asarray(Wd.IX_PR[a0:i + 1], float)
    assert np.all(np.isfinite(ix)) and np.all(ix > 0)
    rm = ix[1:] / ix[:-1] - 1.0
    # σ(로그수익 252일 · ddof 1)
    def sd_last(v, lo):
        v = v[np.isfinite(v)]
        return float(np.std(v, ddof=1) * math.sqrt(252)) if len(v) >= lo else None
    sig = np.array([sd_last(Lr[j, -VOL_WIN:], MIN_V) for j in idxR], float)
    # Y · E · 고유분해(내림차순)
    Y = build_Y(Rs[idxR])
    E_ = (Y @ Y.T) / T_WIN
    lam, Ue = np.linalg.eigh(E_)
    lam, Ue = lam[::-1].copy(), Ue[:, ::-1].copy()
    q = N / T_WIN
    xi_rie, rinfo = rie_iws(lam, q)
    Pp = Ue.T @ Y                                   # 고유포트폴리오 일간(N × T)
    P2 = Pp * Pp
    S_rie = corr_eig(Ue, xi_rie) * np.outer(sig, sig)      # 변형 사이 비교용 사전 베타(기록만)
    # Eg · 후보 60 · EG30
    sc = Wd.score(_cand(), m)
    top = [x for x, _ in sc]
    top60 = [k for _, k in top[:POOL]]
    t30 = {k for _, k in top[:30]}
    tg0 = ctx.V0_targets[m]
    assert set(tg0["w"]) == t30, "V0 목표가 같은 순위의 상위 30 이 아니다(%s)" % m
    w30 = np.array([tg0["w"].get(k, 0.0) for k in keys])
    raw = Wd.raw("eg", m, "union", False, "pitgics")
    egv = {k: v for (t, k), v in raw.items()}
    kR = [keys[j] for j in idxR]
    sc_ix = [r for r, k in enumerate(kR) if k in egv]
    v = np.array([egv[kR[r]] for r in sc_ix], float)
    z = (v - v.mean()) / v.std(ddof=1)
    z = np.clip(z, -WINS, WINS)
    z = (z - z.mean()) / z.std(ddof=1)
    zR = np.zeros(N)
    zR[sc_ix] = z
    p60 = set(top60)
    alpha = np.zeros(N)
    for r, k in enumerate(kR):
        if k in p60 and k in egv:
            j = idxR[r]
            yv, xv = Rs[j, -VOL_WIN:], rm[-VOL_WIN:]
            okv = np.isfinite(yv)
            yv, xv = yv[okv], xv[okv]
            b = np.cov(xv, yv, ddof=1)[0, 1] / np.var(xv, ddof=1)
            e = yv - (yv.mean() - b * xv.mean()) - b * xv
            alpha[r] = float(np.std(e, ddof=1) * math.sqrt(252)) * zR[r]
    # 업종(시점정확만) · R 밖이면서 d = w_EG30 − w_b ≠ 0 인 이름(EG30 이름 · 벤치 이름)
    d = w30 - wb
    secR = [sector_pit(Wd, tick[k], k, m) for k in kR]
    Oi = [j for j in range(len(keys)) if not inR[j] and d[j] != 0]
    secO = [sector_pit(Wd, tick[keys[j]], keys[j], m) for j in Oi]
    pool_of = {}                                      # 업종 → R 안 위치(업종을 아는 이름만)
    for s in sorted({s for s in secO if s is not None}):
        pool_of[s] = np.flatnonzero(np.array([x == s for x in secR], bool))
    poolO = [pool_of.get(s) if s is not None else None for s in secO]
    sigO, sig_fb = [], 0
    for j, s, pl in zip(Oi, secO, poolO):
        so = sd_last(Lr[j, -VOL_WIN:], SIG_MIN_O)
        if so is None:
            sig_fb += 1
            so = float(np.median(sig[pl])) if (pl is not None and len(pl)) else float(np.median(sig))
        sigO.append(so)
    xsec = lambda js: sum(1 for a in range(len(js)) for b in range(a + 1, len(js)) if secO[js[a]] != secO[js[b]])
    o30 = [r for r, j in enumerate(Oi) if w30[j] > 0]
    ob = [r for r, j in enumerate(Oi) if w30[j] == 0]
    src = {}
    for k in kR:
        s_ = Wd.sector_src(tick[k], k, m)
        src[s_] = src.get(s_, 0) + 1
    out = {"m": m, "i": i, "keys": keys, "tick": tick, "wb": wb, "w30": w30, "idxR": idxR, "N": N, "q": q,
           "lam": lam, "U": Ue, "P2": P2, "xi_rie": xi_rie, "rinfo": rinfo, "rm": rm, "sig": sig, "alpha": alpha,
           "lb": -wb[idxR], "dR": d[idxR], "dO": d[Oi], "sigO": np.array(sigO, float), "secO": secO, "poolO": poolO,
           "E": E_, "S_rie": S_rie, "n_U": len(keys), "n_scored_R": len(sc_ix), "n_p60R": int((alpha != 0).sum()),
           "n_p60R_all": int(sum(1 for k in kR if k in p60)), "n_O": len(Oi), "n_O30": len(o30), "n_Obench": len(Oi) - len(o30),
           "wb_O": float(wb[Oi].sum()), "wb_Obench": float(sum(wb[Oi[r]] for r in ob)),
           "n_O30_xsec": xsec(o30), "n_O_xsec": xsec(list(range(len(Oi)))), "n_O_nosec": sum(1 for s in secO if s is None),
           "n_O_sig_fb": sig_fb, "n_R_nosec": sum(1 for s in secR if s is None), "secR_src": src,
           "n_spx": int(is_spx.sum()), "last_px_date": D[i], "win0": D[a0 + 1]}
    assert abs(float(d.sum())) < 1e-12, "d = w_EG30 − w_b 의 합이 0 이 아니다(%s)" % m
    _PREP[ck] = out
    return out


def te_star(P, Xi, S):
    """(8) EG30 사전 TE √(d'Σ̃d) — Σ̃ 는 Σ 를 d ≠ 0 인 R 밖 이름으로 넓힌다: 그 이름과 모든 R 이름의 상관 = 그 업종 R 이름 평균 비대각 Ξ
    (업종 R 이름 5 미만 · 업종 모름이면 시장 평균) · R 밖 두 이름 = 두 값의 평균(같은 업종이면 같은 값)."""
    N = P["N"]
    tot = (float(Xi.sum()) - N) / (N * (N - 1))
    rho = []
    for ix in P["poolO"]:
        n = 0 if ix is None else len(ix)
        rho.append((float(Xi[np.ix_(ix, ix)].sum()) - n) / (n * (n - 1)) if n >= SEC_MIN else tot)
    rho = np.array(rho, float)
    dR, dO, sO = P["dR"], P["dO"], P["sigO"]
    v = float(dR @ (S @ dR))
    if len(dO):
        v += 2.0 * float(np.sum(dO * sO * rho)) * float(P["sig"] @ dR)
        C = 0.5 * (rho[:, None] + rho[None, :])
        np.fill_diagonal(C, 1.0)
        a = dO * sO
        v += float(a @ (C @ a))
    return float(math.sqrt(max(v, 0.0))), {"rho_O": [float(x) for x in rho], "rho_mkt": tot, "neg": v < 0}


def xi_of(P, var, Dc=None):
    """변형 → Ξ(단위 대각 상관). FE3 · FE3m 은 D_c 를 창 안 S&P 500 PR 로 정한다 · PLAC 는 받은 D_c."""
    lam, U, q = P["lam"], P["U"], P["q"]
    if var == "FE1":
        return corr_eig(U, P["xi_rie"])
    if var == "C2":
        return np.eye(P["N"])
    if var == "C3":
        return unit_diag(P["E"])
    if var == "A1":
        return corr_eig(U, clip_laloux(lam, q))
    if var == "A2":
        return corr_eig(U, lw2020(lam, T_WIN))
    if var in ("FE3", "FE3m", "PLAC"):
        rm = P["rm"]
        nc = int(math.ceil(CRASH_Q * T_WIN))
        if var == "FE3":
            Dc = np.argsort(rm, kind="stable")[:nc]
        elif var == "FE3m":
            Dc = np.argsort(-rm, kind="stable")[:nc]
        assert Dc is not None and len(Dc) == nc and len(set(Dc.tolist())) == nc
        xic = P["P2"][:, Dc].mean(1)
        return corr_eig(U, BLEND * P["xi_rie"] + (1 - BLEND) * xic)
    raise ValueError(var)


def solve_formation(P, Xi, fail=None):
    """한 편입의 (7)·(8) → (w over U 또는 None(EG30 유지), 기록)."""
    sig = P["sig"]
    S = Xi * np.outer(sig, sig)
    ts, tinfo = te_star(P, Xi, S)
    rec = {"te_star": ts, "rho_mkt": tinfo["rho_mkt"], "flags": (["te_star_neg"] if tinfo["neg"] else [])}
    try:
        x, lk, te, steps, flags, st = te_match(S, P["alpha"], P["lb"], ts, fail)
    except SolveFail as e:
        rec.update({"solver": "hold_eg30", "flags": rec["flags"] + ["hold_eg30"], "err": str(e)})
        return None, rec
    w = P["wb"].copy()
    w[P["idxR"]] += x
    w[w < W_EPS] = 0.0
    w = w / w.sum()
    xR = w[P["idxR"]] - P["wb"][P["idxR"]]
    u1 = P["U"][:, 0]
    sgn = 1.0 if float((sig * P["wb"][P["idxR"]]) @ u1) >= 0 else -1.0
    base = sgn * float((sig * P["wb"][P["idxR"]]) @ u1)
    wbR = P["wb"][P["idxR"]]
    rec.update({"log10k": lk, "te": te, "steps": steps, "flags": rec["flags"] + flags,
                "n_solve": len(st.get("logk", [])), "probe": bool(LOGK[0] in st.get("logk", [])),
                "solver": ("trust-constr" if st.get("trust-constr") else "slsqp"), "n_slsqp": st.get("SLSQP", 0),
                "n_trust": st.get("trust-constr", 0), "slsqp_nit": st.get("nit", 0), "pdas_fail": st.get("pdas_fail", 0),
                "n_held": int((w > 0).sum()), "max_w": float(w.max()), "hhi": float((w ** 2).sum()),
                "overlap_eg30": float(np.minimum(w, P["w30"]).sum()),
                "beta_ex": float(1.0 + (xR @ (S @ wbR)) / (wbR @ (S @ wbR))),      # 그 변형의 Σ 로
                "beta_ex_rie": (float(1.0 + (xR @ (P["S_rie"] @ wbR)) / (wbR @ (P["S_rie"] @ wbR))) if "S_rie" in P else None),
                "mm_load": float(sgn * ((sig * xR) @ u1) / base) if base > 0 else None,
                "mm_load_eg30": float(sgn * ((sig * P["dR"]) @ u1) / base) if base > 0 else None,
                "min_w": float(w.min()), "sum_w": float(w.sum())})
    return w, rec


def to_targets(ctx, P, w):
    if w is None:
        tg = ctx.V0_targets[P["m"]]
        return {"w": dict(tg["w"]), "names": dict(tg["names"])}
    keys, tick = P["keys"], P["tick"]
    ww = {keys[j]: float(w[j]) for j in range(len(keys)) if w[j] > 0}
    return {"w": ww, "names": {k: tick[k] for k in ww}}


def build(ctx, var, verbose=False):
    """변형 하나의 목표 경로 전체 → (targets, 편입 기록)."""
    T, recs = {}, []
    t0 = time.time()
    for m in formations(ctx):
        P = prep(ctx, m)
        w, rec = solve_formation(P, xi_of(P, var))
        rec["m"] = m
        T[m] = to_targets(ctx, P, w)
        recs.append(rec)
        if verbose:
            print("  %s %s %.0f초" % (var, m, time.time() - t0), flush=True)
    return T, recs


def thash(T, dec=HASH_DEC):
    """목표 경로 sha256(json · 키 정렬) — dec 자리로 반올림(None 이면 원값)."""
    if dec is not None:
        T = {m: {"w": {k: round(float(v), dec) for k, v in tg["w"].items()}, "names": tg["names"]} for m, tg in T.items()}
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def blas_env():
    return {k: os.environ.get(k) for k in BLAS_ENV}


def common_log(ctx):
    rows = []
    for m in formations(ctx):
        P = prep(ctx, m)
        rows.append({"m": m, "n_U": P["n_U"], "n_spx": P["n_spx"], "N_R": P["N"], "q": P["q"], "n_scored_R": P["n_scored_R"],
                     "n_p60R": P["n_p60R"], "n_p60R_all": P["n_p60R_all"], "n_O": P["n_O"], "n_eg30_outR": P["n_O30"],
                     "n_bench_outR": P["n_Obench"], "wb_O": P["wb_O"], "wb_Obench": P["wb_Obench"], "n_O30_xsec": P["n_O30_xsec"],
                     "n_O_xsec": P["n_O_xsec"], "n_O_nosec": P["n_O_nosec"], "n_O_sig_fb": P["n_O_sig_fb"],
                     "n_R_nosec": P["n_R_nosec"], "secR_src": P["secR_src"],
                     "lam1": float(P["lam"][0]), "lamN": float(P["lam"][-1]), "kiw": P["rinfo"]["kiw"],
                     "kiw_inf": P["rinfo"]["kiw_inf"], "n_gamma": P["rinfo"]["n_gamma"],
                     "win": [P["win0"], P["last_px_date"]]})
    return rows


# ── 위약(Q13) — 병렬 일꾼 ─────────────────────────────────────────────────
_PK = ("m", "N", "q", "U", "P2", "xi_rie", "sig", "alpha", "lb", "dR", "dO", "sigO", "secO", "poolO", "wb", "idxR", "w30", "keys")
POOL_LOG = []                         # 일꾼 무리마다 기록(죽음 · 새로 띄움 · 죽임 · 본 프로세스 풀이 · stderr 끝) — run 의 log 로


def _pack(ctx):
    return [{k: prep(ctx, m)[k] for k in _PK} for m in formations(ctx)]


def plac_draw(pack, i):
    """위약 뽑기 i — 편입마다 창 1000일에서 비복원 균등 100일(씨앗 SEED + i · 편입 순서대로 한 줄기)."""
    rng = np.random.default_rng(Q.SEED + i)
    nc = int(math.ceil(CRASH_Q * T_WIN))
    ws, fl = [], []
    for P in pack:
        Dc = np.sort(rng.choice(T_WIN, nc, replace=False))
        Xi = corr_eig(P["U"], BLEND * P["xi_rie"] + (1 - BLEND) * P["P2"][:, Dc].mean(1))
        w, rec = solve_formation(P, Xi)
        ws.append(w)
        fl.append(rec["flags"])
    return ws, fl


def _st_draw(pack, i):
    """selftest 전용 일꾼 함수(합성 · 수익 없음) — 'die' 뽑기에서 일꾼이 한 번 죽고(표식 파일) · 'die_always' 뽑기에서는 일꾼이 늘 죽는다
    (본 프로세스에서는 산다) · 'sleep' 초 잔다."""
    wk = os.environ.get("Q_RIEGK_WORKER") == "1"
    if wk and pack.get("die") == i and not os.path.exists(pack["flag"]):
        open(pack["flag"], "w", encoding="utf-8").close()
        os._exit(3)
    if wk and pack.get("die_always") == i:
        os._exit(4)
    time.sleep(pack.get("sleep", 0.0))
    return [float(i)], [["st"]]


_DRAW = {"plac": plac_draw, "st": _st_draw}


def _worker(pack_path, out_dir, draws, fn="plac"):
    """하위 프로세스 — 뽑기마다 파일 하나(pickle · 원자적 이름 바꾸기)."""
    with open(pack_path, "rb") as f:
        pack = pickle.load(f)
    draw = _DRAW[fn]
    for i in draws:
        ws, fl = draw(pack, i)
        tmp = os.path.join(out_dir, "d%05d.tmp" % i)
        with open(tmp, "wb") as f:
            pickle.dump({"i": i, "w": ws, "flags": fl}, f)
        os.replace(tmp, os.path.join(out_dir, "d%05d.pkl" % i))


def _tail(path, n=2000):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()[-n:]
    except OSError as e:
        return "(stderr 못 읽음: %s)" % e


def _pool(pack, n, nproc, fn="plac"):
    """뽑기 0..n−1 을 일꾼 nproc 개(하위 프로세스 · BLAS 1스레드)에 나눠(뽑기 i → 자리 i mod nproc) 끝나는 대로 차례로 (i, ws, fl, 출처) 를 내준다.
    일꾼이 죽으면 그 자리의 남은 뽑기를 새 일꾼에 넘긴다(RESPAWN_MAX 번) · 그래도 죽으면 그 자리의 남은 뽑기는 본 프로세스가 같은 씨앗으로 푼다
    (결정적 오류는 거기서 예외로 드러난다). 소비 쪽이 멈추면(close · 예외) 남은 일꾼을 죽이고 임시 폴더를 지운다."""
    nw = max(1, min(nproc, n))
    d = tempfile.mkdtemp(prefix="q_riegk_")
    log = {"n": n, "nproc": nw, "dead": [], "respawn": 0, "killed": 0, "serial": 0, "done": 0, "cleaned": False}
    POOL_LOG.append(log)
    pp = os.path.join(d, "pack.pkl")
    files, slots = [], []
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="0", Q_RIEGK_WORKER="1")
    pkl = lambda i: os.path.join(d, "d%05d.pkl" % i)

    def spawn(w, dr):
        code = "import sys; sys.path.insert(0, %r); import q_riegk as M; M._worker(%r, %r, %r, %r)" % (HERE, pp, d, dr, fn)
        ef = open(os.path.join(d, "err%d_%d.txt" % (w, len(files))), "w", encoding="utf-8")
        files.append(ef)
        return subprocess.Popen([sys.executable, "-X", "utf8", "-c", code], env=env, stdout=subprocess.DEVNULL, stderr=ef), ef.name

    try:
        with open(pp, "wb") as f:
            pickle.dump(pack, f, protocol=pickle.HIGHEST_PROTOCOL)
        for w in range(nw):
            dr = list(range(w, n, nw))
            p, en = spawn(w, dr)
            slots.append({"p": p, "draws": dr, "err": en, "respawn": 0, "serial": False})
        for i in range(n):
            s = slots[i % nw]
            fi = pkl(i)
            src = "serial" if (s["serial"] and not os.path.exists(fi)) else "proc"
            while src == "proc" and not os.path.exists(fi):
                if s["p"].poll() is not None and not os.path.exists(fi):          # 그 자리 일꾼이 죽었다
                    log["dead"].append({"slot": i % nw, "draw": i, "rc": s["p"].returncode, "err": _tail(s["err"])})
                    if s["respawn"] < RESPAWN_MAX:
                        s["respawn"] += 1
                        log["respawn"] += 1
                        s["p"], s["err"] = spawn(i % nw, [j for j in s["draws"] if j >= i])
                        continue
                    s["serial"] = True
                    src = "serial"
                    break
                time.sleep(0.2)
            if src == "serial":
                log["serial"] += 1
                ws, fl = _DRAW[fn](pack, i)
            else:
                with open(fi, "rb") as f:
                    r = pickle.load(f)
                os.remove(fi)
                ws, fl = r["w"], r["flags"]
            yield i, ws, fl, src
            log["done"] += 1
    finally:
        for s in slots:
            if s["p"].poll() is None:
                if log["done"] < n:                      # 소비 쪽이 멈췄다 — 남은 뽑기를 기다리지 않는다
                    s["p"].kill()
                    log["killed"] += 1
                s["p"].wait()
        for ef in files:
            ef.close()
        shutil.rmtree(d, ignore_errors=True)
        log["cleaned"] = not os.path.exists(d)


def placebo_weights(ctx, n, nproc=None):
    """위약 n 번의 편입별 비중 — 차례로 (i, ws, fl, 출처). 🚨 소비 쪽은 contextlib.closing 으로 감싼다(멈추면 일꾼을 바로 죽이게)."""
    return _pool(_pack(ctx), n, NPROC if nproc is None else nproc, "plac")


# ── 판정 보조(카드 G4 만) ─────────────────────────────────────────────────
def sleeve_beta(ctx, fr):
    """β̂_s = qbatch_core.evaluate 의 sleeve_beta(120개월 OLS · 복제하지 않는다)."""
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


def _sumrec(recs):
    f = lambda key: [r.get(key) for r in recs if r.get(key) is not None]
    fl = {}
    for r in recs:
        for x in r["flags"]:
            fl[x] = fl.get(x, 0) + 1
    return {"n": len(recs), "flags": fl, "n_hold": sum(1 for r in recs if r.get("solver") == "hold_eg30"),
            "n_trust": sum(r.get("n_trust", 0) for r in recs), "pdas_fail": sum(r.get("pdas_fail", 0) for r in recs),
            "n_probe": sum(1 for r in recs if r.get("probe")),
            "n_solve": [min(f("n_solve"), default=None), max(f("n_solve"), default=None)],
            "max_w": max(f("max_w"), default=None), "hhi": [min(f("hhi"), default=None), max(f("hhi"), default=None)],
            "n_held": [min(f("n_held"), default=None), max(f("n_held"), default=None)],
            "te_gap_max": max((abs(r["te"] - r["te_star"]) for r in recs if "te" in r and "te_unreach" not in r["flags"]), default=None)}


def _proxy_turn(T):
    """목표 사이 편도 회전 대용(흘러감 무시 · 구성만) — 연율(분기 편입 4번)."""
    ms = sorted(T)
    tv = []
    for a, b in zip(ms, ms[1:]):
        wa, wb = T[a]["w"], T[b]["w"]
        tv.append(0.5 * sum(abs(wb.get(k, 0.0) - wa.get(k, 0.0)) for k in set(wa) | set(wb)))
    return float(np.mean(tv) * 4) if tv else None


# ── 계약 ──────────────────────────────────────────────────────────────────
def selftest() -> dict:
    """합성 자료만 — 랩 수익 없음."""
    t = {}
    rng = np.random.default_rng(Q.SEED)
    # 1) 동일 모집단 위샤트 → IWs-RIE ≈ 1
    N, T = 500, 1000
    X = rng.standard_normal((N, T))
    lam = np.linalg.eigvalsh(X @ X.T / T)[::-1]
    xi, info = rie_iws(lam, N / T)
    dev = float(np.abs(xi - 1).max())
    z = lam - 1j / math.sqrt(N)
    G = 1.0 / (z[:, None] - lam[None, :]); np.fill_diagonal(G, 0.0)
    bare = _rie(z, N / T, G.sum(1) / (N - 1)); bare = bare * N / bare.sum()
    t["rie_identity_max_dev"] = round(dev, 4)
    t["rie_identity_sd"] = round(float(xi.std()), 4)
    t["rie_identity_ok"] = bool(dev < 0.25 and xi.std() < 0.05 and dev < float(np.abs(bare - 1).max()) and abs(xi.mean() - 1) < 1e-12)
    t["rie_sample_spread"] = round(float(lam.max() - lam.min()), 3)
    # 2) g_iw(식 3.41) — 밀도 질량 1 · 띠 안 RIE = 선형축소 1 + α(λ − 1)
    ok2 = True
    for k, qq in ((1.0, 0.5), (10.0, 0.5), (0.8, 0.48)):
        s = math.sqrt((2 * k + 1) * (2 * qq * k + 1)); lp, lm = ((1 + qq) * k + 1 + s) / k, ((1 + qq) * k + 1 - s) / k
        x = np.linspace(lm, lp, 200001)
        area = float(np.trapezoid(g_iw(x - 1e-10j, qq, k).imag / np.pi, x))
        xin = x[1000:-1000:5000]
        a = 1 / (1 + 2 * qq * k)
        dv = float(np.abs(_rie(xin - 1e-10j, qq, g_iw(xin - 1e-10j, qq, k)) - (1 + a * (xin - 1))).max())
        ok2 = ok2 and abs(area - 1) < 1e-5 and dv < 1e-6
    x = np.linspace((1 - math.sqrt(.5)) ** 2, (1 + math.sqrt(.5)) ** 2, 200001)
    ok2 = ok2 and abs(float(np.trapezoid(g_iw(x - 1e-10j, .5, math.inf).imag / np.pi, x)) - 1) < 1e-5
    t["g_iw_mass_linear_ok"] = bool(ok2)
    # 3) 역위샤트 모집단에서 IW 보정이 왼쪽 끝을 끌어올린다(맨 RIE 보다 선형축소 오라클에 가깝다)
    k0, q0 = 10.0, 0.5
    W = rng.standard_normal((N, int(N / (1 / (2 * k0 + 1)))))
    Cw = W @ W.T / W.shape[1]
    ev, V = np.linalg.eigh(Cw)
    C = (V / ev) @ V.T
    C = C / np.trace(C) * N
    Lc = np.linalg.cholesky(C)
    Xs = Lc @ rng.standard_normal((N, T))
    lam2, U2 = np.linalg.eigh(Xs @ Xs.T / T); lam2, U2 = lam2[::-1], U2[:, ::-1]
    xi2, inf2 = rie_iws(lam2, q0)
    orc = np.einsum("ij,ij->j", U2, C @ U2)
    z2 = lam2 - 1j / math.sqrt(N)
    G2 = 1.0 / (z2[:, None] - lam2[None, :]); np.fill_diagonal(G2, 0.0)
    b2 = _rie(z2, q0, G2.sum(1) / (N - 1)); b2 = b2 * N / b2.sum()
    low = lam2 < np.quantile(lam2, 0.1)
    t["iw_left_edge_ok"] = bool(np.mean(np.abs(xi2[low] - orc[low])) < np.mean(np.abs(b2[low] - orc[low])))
    t["iw_kiw"] = None if inf2["kiw"] is None else round(inf2["kiw"], 2)
    # 4) 자르기 · LW2020 · 단위 대각
    cl = clip_laloux(lam, N / T)
    t["clip_trace_ok"] = bool(abs(cl.sum() - lam.sum()) < 1e-8 and np.all(cl[lam >= (1 + math.sqrt(N / T)) ** 2] == lam[lam >= (1 + math.sqrt(N / T)) ** 2]))
    lw = lw2020(lam, T)
    t["lw_identity_median_dev"] = round(float(np.median(np.abs(lw - 1))), 4)
    t["lw_identity_ok"] = bool(np.median(np.abs(lw - 1)) < 0.1 and np.all(lw > 0))
    # LW Hilbert 항 — 급수 = 60자리 기준값(원식은 큰 |x| 에서 자릿수를 잃는다) · 10 < |x| < 200 에서 원식과 같다 · 바꿈 점 연속
    from decimal import Decimal, getcontext
    getcontext().prec = 60
    a5 = Decimal(5).sqrt()
    pi_ = Decimal("3.14159265358979323846264338327950288419716939937510582097494")
    hp = lambda xv: float(Decimal(-3) / (10 * pi_) * Decimal(repr(xv)) + Decimal(3) / (4 * a5 * pi_) * (1 - Decimal(repr(xv)) ** 2 / 5)
                          * ((a5 - Decimal(repr(xv))) / (a5 + Decimal(repr(xv)))).copy_abs().ln())
    pts = np.array([10.5, 50.0, 1e3, 7e4, -3e4, -12.0])
    ref = np.array([hp(float(v)) for v in pts])
    xm = np.r_[np.linspace(10.0001, 200, 400), -np.linspace(10.0001, 200, 400)]
    sw = np.array([LW_SER * (1 - 1e-12), LW_SER * (1 + 1e-12)])
    t["lw_hilbert_ref_err"] = float(np.max(np.abs(_lw_hilbert(pts) - ref) / np.abs(ref)))
    t["lw_hilbert_direct_err"] = float(np.max(np.abs(_lw_hilbert(pts, False) - ref) / np.abs(ref)))
    t["lw_hilbert_ok"] = bool(t["lw_hilbert_ref_err"] < 1e-13
                              and np.max(np.abs(_lw_hilbert(xm) - _lw_hilbert(xm, False)) / np.abs(_lw_hilbert(xm))) < 1e-9
                              and abs(float(np.diff(_lw_hilbert(sw))[0])) < 1e-12)
    Uq = np.linalg.qr(rng.standard_normal((30, 30)))[0]
    Cq = corr_eig(Uq, rng.uniform(0.2, 3, 30))
    t["unit_diag_ok"] = bool(np.allclose(np.diag(Cq), 1) and np.allclose(Cq, Cq.T) and np.linalg.eigvalsh(Cq).min() > 0)
    # 5) Y 정규화 · 폭락일 2차 적률(모든 날이면 λ 와 같다)
    Rr = rng.standard_normal((40, 300)) * rng.uniform(0.01, 0.03, (40, 1))
    Rr[rng.random(Rr.shape) < 0.05] = np.nan
    Yy = build_Y(Rr)
    V_ = np.isfinite(Rr)
    mm = np.array([Yy[j][V_[j]].mean() for j in range(40)]); ss = np.array([Yy[j][V_[j]].std() for j in range(40)])
    t["build_Y_ok"] = bool(np.allclose(mm, 0, atol=1e-12) and np.allclose(ss, 1) and np.all(Yy[~V_] == 0))
    Ey = Yy @ Yy.T / 300
    ly, Uy = np.linalg.eigh(Ey); ly, Uy = ly[::-1], Uy[:, ::-1]
    t["crash_moment_all_days_ok"] = bool(np.allclose(((Uy.T @ Yy) ** 2).mean(1), ly))
    # 6) QP — Ξ = I 닫힌 해(물 채우기) · SLSQP 와 활성집합 일치 · KKT
    n = 80
    sg = rng.uniform(0.15, 0.5, n)
    wbq = rng.lognormal(size=n); wbq /= wbq.sum()
    al = np.zeros(n); al[rng.choice(n, 12, replace=False)] = rng.normal(size=12) * 0.2
    S = np.diag(sg ** 2)
    kap = 3.0
    lo_, hi_ = -50.0, 50.0                                  # ν 이분(닫힌 해)
    xf = lambda nu: np.maximum(-wbq, (al + nu) / (kap * sg ** 2))
    for _ in range(200):
        mid = 0.5 * (lo_ + hi_)
        lo_, hi_ = (mid, hi_) if xf(mid).sum() < 0 else (lo_, mid)
    xc = xf(0.5 * (lo_ + hi_))
    xs = qp_solve(S, al, -wbq, kap, {})
    t["qp_diag_closed_form_err"] = float(np.abs(xs - xc).max())
    B = rng.normal(size=(n, 4)); Cf = unit_diag(B @ B.T + np.diag(rng.uniform(.3, 1, n)))
    S2 = Cf * np.outer(sg, sg)
    pre = qp_active(S2, al / kap, -wbq)
    cold, _ = _minimize("SLSQP", S2, al, kap, -wbq, np.zeros(n))
    t["qp_active_vs_slsqp_cold"] = float(np.abs(pre[0] - cold.x).max())
    x_ = pre[0]; act = pre[1]
    gr = kap * (S2 @ x_) - al
    nu = float(np.mean(gr[~act]))
    t["qp_ok"] = bool(t["qp_diag_closed_form_err"] < 1e-6 and t["qp_active_vs_slsqp_cold"] < 1e-4 and _feasible(x_, -wbq)
                      and np.allclose(gr[~act], nu, atol=1e-8) and np.all(gr[act] - nu >= -1e-8))
    # 7) TE 이분 · 닿지 않는 TE* · 대체 경로
    d30 = np.zeros(n); d30[:10] = rng.dirichlet(np.ones(10)); d30 = d30 - wbq
    ts = float(math.sqrt(d30 @ S2 @ d30))
    x1, lk1, te1, st1, fl1, s1 = te_match(S2, al, -wbq, ts)
    t["te_match_gap"] = abs(te1 - ts)
    x2, lk2, te2, st2, fl2, s2 = te_match(S2, al, -wbq, 1e3)
    x3, lk3, te3, st3, fl3, s3 = te_match(S2, al, -wbq, ts, fail=("SLSQP",))
    try:
        te_match(S2, al, -wbq, ts, fail=("SLSQP", "trust-constr"))
        both = False
    except SolveFail:
        both = True
    # κ = 10^-4 에서만 두 풀이가 다 실패해도 닿는 TE* 는 풀린다(그 점을 풀지 않는다) · 닿지 않는 TE* 는 그 점에서 가린다
    lo_fail = lambda meth, kap: kap <= 10.0 ** LOGK[0] * 1.000001
    x4, lk4, te4, st4, fl4, s4 = te_match(S2, al, -wbq, ts, fail=lo_fail)
    try:
        te_match(S2, al, -wbq, 1e3, fail=lo_fail)
        unreach_fail = False
    except SolveFail:
        unreach_fail = True
    t["te_probe_skipped_ok"] = bool(LOGK[0] not in s1["logk"] and LOGK[0] not in s4["logk"] and np.array_equal(x4, x1)
                                    and not fl4 and s2["logk"][-1] == LOGK[0] and unreach_fail)
    t["te_ok"] = bool(t["te_match_gap"] <= TE_TOL and not fl1 and fl2 == ["te_unreach"] and lk2 == LOGK[0]
                      and s3.get("trust-constr", 0) > 0 and abs(te3 - ts) <= TE_TOL and both)
    # 단조 — κ 가 크면 TE 가 작다(이분의 근거)
    tes = [math.sqrt(max(float(xx @ (S2 @ xx)), 0.0)) for xx in (qp_solve(S2, al, -wbq, 10.0 ** e, {}) for e in (-2, -1, 0, 1, 2, 3))]
    t["te_monotone_ok"] = bool(all(a >= b - 1e-12 for a, b in zip(tes, tes[1:])))
    # 8) TE* 확장 — R 밖 이름이 없으면 d'Σd 와 같다 · 있으면 대칭 확장값
    Pt = {"N": n, "secO": [], "poolO": [], "dR": d30, "dO": np.zeros(0), "sigO": np.zeros(0), "sig": sg}
    t1, _ = te_star(Pt, Cf, S2)
    pA, pC = np.arange(40), np.arange(40, 43)          # 업종 A = R 40 이름 · 업종 C = R 3 이름(5 미만 → 시장 평균)
    dO = np.array([0.05, 0.02, -0.01, -0.004])           # A(EG30) · C · A(벤치) · 업종 모름(벤치)
    sO = np.array([0.3, 0.4, 0.25, 0.35])
    rA = (Cf[:40, :40].sum() - 40) / (40 * 39); rM = (Cf.sum() - n) / (n * (n - 1))
    rr = [rA, rM, rA, rM]
    no = len(dO)
    Sx = np.zeros((n + no, n + no)); Sx[:n, :n] = S2
    for a in range(no):
        Sx[n + a, :n] = Sx[:n, n + a] = rr[a] * sO[a] * sg
        for b in range(no):
            Sx[n + a, n + b] = sO[a] * sO[b] * (1.0 if a == b else 0.5 * (rr[a] + rr[b]))
    dx = np.r_[d30 - dO.sum() / n, dO]                   # 합 0 인 d(R 밖 이름 포함)
    Pt2 = dict(Pt, secO=["A", "C", "A", None], poolO=[pA, pC, pA, None], dR=dx[:n], dO=dO, sigO=sO)
    t2, i2 = te_star(Pt2, Cf, S2)
    t["te_star_ok"] = bool(abs(t1 - ts) < 1e-12 and abs(t2 - math.sqrt(dx @ Sx @ dx)) < 1e-12 and abs(i2["rho_O"][0] - rA) < 1e-12
                           and abs(i2["rho_O"][1] - rM) < 1e-12 and abs(i2["rho_O"][3] - rM) < 1e-12 and i2["rho_O"][0] == i2["rho_O"][2])
    # 시점정확 업종 — 그달 표 · 이전 달 표 · 이후 달/오늘은 쓰지 않는다(가짜 World)
    class _FW:
        cikmap = {"AAA": "c1", "BBB": "c2", "CCC": "c3"}
        Gtl = {"c:c2": [("2019-01", "Energy"), ("2019-05", "Utilities"), ("2020-02", "Materials")], "c:c3": [("2020-06", "Energy")]}

        def sector_src(self, t, k, m):
            return "month" if t == "AAA" else ("near" if t in ("BBB", "CCC") else "today")

        def sector(self, t, k, m):
            return {"AAA": "Health Care", "BBB": "Materials", "CCC": "Energy"}.get(t, "Industrials")
    fw = _FW()
    t["sector_pit_ok"] = bool(sector_pit(fw, "AAA", "AAA", "2020-01") == "Health Care" and sector_pit(fw, "BBB", "BBB", "2020-01") == "Utilities"
                              and sector_pit(fw, "CCC", "CCC", "2020-01") is None and sector_pit(fw, "DDD", "DDD", "2020-01") is None)
    # 해시 — 1e-15 흔들림에는 같고 1e-8 차이에는 다르다
    Th = {"2016-08": {"w": {"a": 0.3, "b": 0.7}, "names": {"a": "A", "b": "B"}}}
    Th2 = {"2016-08": {"w": {"a": 0.3 + 2.6e-15, "b": 0.7 - 2.6e-15}, "names": {"a": "A", "b": "B"}}}
    Th3 = {"2016-08": {"w": {"a": 0.3 + 1e-8, "b": 0.7 - 1e-8}, "names": {"a": "A", "b": "B"}}}
    t["hash_round_ok"] = bool(thash(Th) == thash(Th2) and thash(Th) != thash(Th3) and thash(Th, None) != thash(Th2, None))
    # 9) 위약 씨앗 재현
    r1 = np.random.default_rng(Q.SEED + 7).choice(T_WIN, 100, replace=False)
    r2 = np.random.default_rng(Q.SEED + 7).choice(T_WIN, 100, replace=False)
    t["seed_ok"] = bool(np.array_equal(r1, r2) and len(set(r1.tolist())) == 100)
    # 10) 위약 일꾼 무리(합성 · 수익 없음) — 차례 · 죽은 일꾼 새로 띄움 · 두 번 죽으면 본 프로세스 · 소비 쪽이 멈추면 일꾼을 죽이고 폴더를 지운다
    tmpd = tempfile.mkdtemp(prefix="q_riegk_st_")
    try:
        got = [(i, ws[0], src) for i, ws, fl, src in _pool({"sleep": 0.0}, 5, 2, "st")]
        la = POOL_LOG[-1]
        ok_a = [g[0] for g in got] == list(range(5)) and all(g[1] == float(g[0]) and g[2] == "proc" for g in got) and la["cleaned"]
        got = [(i, ws[0], src) for i, ws, fl, src in _pool({"die": 1, "flag": os.path.join(tmpd, "f")}, 4, 2, "st")]
        lb_ = POOL_LOG[-1]
        ok_b = ([g[0] for g in got] == list(range(4)) and all(g[1] == float(g[0]) and g[2] == "proc" for g in got)
                and lb_["respawn"] == 1 and len(lb_["dead"]) == 1 and lb_["dead"][0]["rc"] == 3 and lb_["cleaned"])
        got = [(i, ws[0], src) for i, ws, fl, src in _pool({"die_always": 1}, 4, 2, "st")]
        lc = POOL_LOG[-1]
        ok_c = ([g[2] for g in got] == ["proc", "serial", "proc", "serial"] and all(g[1] == float(g[0]) for g in got)
                and lc["respawn"] == 1 and lc["serial"] == 2 and lc["cleaned"])
        gen = _pool({"sleep": 2.0}, 8, 2, "st")
        first = next(gen)
        tc = time.time()
        gen.close()
        ld = POOL_LOG[-1]
        t["pool_close_sec"] = round(time.time() - tc, 2)
        ok_d = first[0] == 0 and ld["killed"] >= 1 and ld["cleaned"] and t["pool_close_sec"] < 3.0
        t["pool_ok"] = bool(ok_a and ok_b and ok_c and ok_d)
        t["pool_parts"] = [bool(ok_a), bool(ok_b), bool(ok_c), bool(ok_d)]
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    keys = [k for k, v in t.items() if k.endswith("_ok")]
    return {"ok": all(t[k] for k in keys), "tests": t}


def dry(ctx) -> dict:
    """랩 자료로 구성만 — 커버리지 · 비중 합 · 음수 · TE 맞춤 · 풀이 · 개수 · 날짜 단언 · 걸린 시간. 수익 없음."""
    t0 = time.time()
    out = {"forms": len(formations(ctx))}
    cl = common_log(ctx)
    out["prep_sec"] = round(time.time() - t0, 1)
    out["N_R"] = [min(r["N_R"] for r in cl), max(r["N_R"] for r in cl)]
    out["N_U"] = [min(r["n_U"] for r in cl), max(r["n_U"] for r in cl)]
    out["R_cover"] = [round(min(r["N_R"] / r["n_U"] for r in cl), 3), round(max(r["N_R"] / r["n_U"] for r in cl), 3)]
    out["q"] = [round(min(r["q"] for r in cl), 3), round(max(r["q"] for r in cl), 3)]
    out["n_p60R"] = [min(r["n_p60R"] for r in cl), max(r["n_p60R"] for r in cl)]
    mm = lambda key, nd=None: [min(r[key] for r in cl), max(r[key] for r in cl)] if nd is None else \
        [round(min(r[key] for r in cl), nd), round(max(r[key] for r in cl), nd)]
    out["n_O"] = mm("n_O") + [sum(r["n_O"] for r in cl)]
    out["n_eg30_outR"] = mm("n_eg30_outR") + [sum(r["n_eg30_outR"] for r in cl)]
    out["n_bench_outR"] = mm("n_bench_outR") + [sum(r["n_bench_outR"] for r in cl)]
    out["wb_O"] = mm("wb_O", 4)
    out["wb_Obench"] = mm("wb_Obench", 4)
    out["O30_xsec_months"] = [r["m"] for r in cl if r["n_O30_xsec"] > 0]
    out["n_O_xsec"] = sum(r["n_O_xsec"] for r in cl)
    out["n_O_nosec"] = sum(r["n_O_nosec"] for r in cl)
    out["n_O_sig_fb"] = sum(r["n_O_sig_fb"] for r in cl)
    out["n_R_nosec"] = mm("n_R_nosec")
    src = {}
    for r in cl:
        for k, v in r["secR_src"].items():
            src[k] = src.get(k, 0) + v
    out["secR_src_total"] = src
    out["kiw_inf"] = sum(1 for r in cl if r["kiw_inf"])
    out["kiw"] = [round(min(r["kiw"] for r in cl if r["kiw"] is not None), 3), round(max(r["kiw"] for r in cl if r["kiw"] is not None), 3)]
    out["n_gamma"] = [min(r["n_gamma"] for r in cl), max(r["n_gamma"] for r in cl)]
    out["lamN"] = [round(min(r["lamN"] for r in cl), 4), round(max(r["lamN"] for r in cl), 4)]
    out["windows"] = [cl[0]["win"], cl[-1]["win"]]
    out["var"] = {}
    bad = 0
    for v in VARIANTS:
        t1 = time.time()
        T, recs = build(ctx, v)
        for m, tg in T.items():
            s = sum(tg["w"].values())
            if abs(s - 1) > 1e-9 or min(tg["w"].values()) < 0:
                bad += 1
        sm = _sumrec(recs)
        sm.update({"sec": round(time.time() - t1, 1), "hash": thash(T)[:12], "hash_exact": thash(T, None)[:12], "turn_proxy": _proxy_turn(T),
                   "te_star": [round(min(r["te_star"] for r in recs), 4), round(max(r["te_star"] for r in recs), 4)],
                   "log10k": [round(min(r["log10k"] for r in recs if "log10k" in r), 2), round(max(r["log10k"] for r in recs if "log10k" in r), 2)],
                   "steps": [min(r["steps"] for r in recs if "steps" in r), max(r["steps"] for r in recs if "steps" in r)],
                   "overlap_eg30": [round(min(r["overlap_eg30"] for r in recs if "overlap_eg30" in r), 3),
                                    round(max(r["overlap_eg30"] for r in recs if "overlap_eg30" in r), 3)]})
        out["var"][v] = sm
        print("dry %-4s 편입 %d · 유지 %d · 표식 %s · 최대 비중 %.3f · 보유 %s · TE 차 최대 %.1e · 이분 %s · 풀이 %s · κ=1e-4 %d · trust %d · 회전 대용 %.2f · %.0f초"
              % (v, sm["n"], sm["n_hold"], sm["flags"], sm["max_w"], sm["n_held"], sm["te_gap_max"] or 0, sm["steps"], sm["n_solve"],
                 sm["n_probe"], sm["n_trust"], sm["turn_proxy"] or 0, sm["sec"]), flush=True)
    # 위약 일꾼 무리 — 일꾼마다 한 뽑기를 받고(처리량) 다음 한 바퀴 중간에 닫아 일꾼이 죽는지 본다(구성만 · 수익 없음)
    t1 = time.time()
    nw = NPROC
    holds, pfl, how, tfirst = 0, {}, {}, None
    with contextlib.closing(placebo_weights(ctx, 2 * nw)) as gen:
        for i, ws, fl, src in gen:
            tfirst = tfirst or round(time.time() - t1, 1)
            holds += sum(1 for w in ws if w is None)
            for f_ in fl:
                for x in f_:
                    pfl[x] = pfl.get(x, 0) + 1
            how[src] = how.get(src, 0) + 1
            if i == nw - 1:
                break
    tc = time.time()
    lg = POOL_LOG[-1]
    out["placebo"] = {"nproc": nw, "draws_got": sum(how.values()), "first_sec": tfirst, "round_sec": round(tc - t1, 1),
                      "holds": holds, "flags": pfl, "how": how, "killed": lg["killed"], "cleaned": lg["cleaned"], "dead": len(lg["dead"]),
                      "est_bake_placebo_min": round((tc - t1) * NPERM / nw / 60.0, 1)}
    print("dry 위약 일꾼 %d · %d 뽑기 %.0f초 · 유지 %d · 표식 %s · 죽임 %d · 폴더 지움 %s"
          % (nw, sum(how.values()), tc - t1, holds, pfl, lg["killed"], lg["cleaned"]), flush=True)
    out["bad_weights"] = bad
    out["sec"] = round(time.time() - t0, 1)
    out["ok"] = bool(bad == 0 and all(out["var"][v]["n_hold"] == 0 for v in VARIANTS) and out["placebo"]["holds"] == 0
                     and out["placebo"]["cleaned"] and out["placebo"]["killed"] >= 1)
    return out


def run(ctx) -> dict:
    """한 번 굽기 — Q02 · Q13 CardResult. 🚨 결과 값을 찍지 않는다."""
    t0 = time.time()
    T, R = {}, {}
    for v in VARIANTS:
        T[v], R[v] = build(ctx, v)
    fr = {v: ctx.stock_fr(T[v], reb=3, basis="TR") for v in VARIANTS}
    fe1_pr, fe1_20 = ctx.stock_fr(T["FE1"], reb=3, basis="PR"), ctx.stock_fr(T["FE1"], reb=3, basis="TR", cost=COST20)
    fe3_pr, fe3_20 = ctx.stock_fr(T["FE3"], reb=3, basis="PR"), ctx.stock_fr(T["FE3"], reb=3, basis="TR", cost=COST20)
    v0, v0_20 = ctx.V0(), ctx.V0(cost=COST20)
    cl = common_log(ctx)
    g4_02 = {"C2_dbeta_down_pos": bool(dbeta_down(ctx, fr["FE1"], fr["C2"]) > 0)}
    n_solved = sum(1 for r in R["FE1"] if r.get("solver") != "hold_eg30")
    q02 = {"code": "Q02", "cls": "B", "slot": "B1", "fr": fr["FE1"], "fr_pr": fe1_pr, "fr20": fe1_20,
           "controls": {"V0": v0, "V0_20": v0_20, "C2": fr["C2"]},
           "arms": {"C3": fr["C3"], "A1": fr["A1"], "A2": fr["A2"]},
           "placebo": {}, "perm": None, "g4": g4_02, "label_caps": {},
           "f0": {"ok": n_solved > 0, "why": "카드에 F0 없음 — FE1 이 풀린 편입 %d/%d" % (n_solved, len(R["FE1"]))},
           "targets_hash": thash(T["FE1"]),
           "log": {"interpretation": INTERP, "common": cl, "formations": R["FE1"], "summary": _sumrec(R["FE1"]),
                   "hash_dec": HASH_DEC, "hash_exact": thash(T["FE1"], None), "blas_env": blas_env(),
                   "controls": {v: {"summary": _sumrec(R[v]), "hash": thash(T[v]), "hash_exact": thash(T[v], None), "formations": R[v]}
                                for v in ("C2", "C3", "A1", "A2")},
                   "turn": {v: fr[v].get("turn") for v in ("FE1", "C2", "C3", "A1", "A2")}}}
    # Q13 위약
    draws, pfl, how = [], {}, {}
    tp = time.time()
    b1 = sleeve_beta(ctx, fr["FE1"])
    fms = formations(ctx)
    n_pool = len(POOL_LOG)
    with contextlib.closing(placebo_weights(ctx, NPERM)) as gen:          # 여기서 예외가 나면 일꾼을 바로 죽인다
        for i, ws, fl, src in gen:
            assert len(ws) == len(fms) and i == len(draws)
            Tm = {m_: to_targets(ctx, prep(ctx, m_), w) for m_, w in zip(fms, ws)}
            fri = ctx.stock_fr(Tm, reb=3, basis="TR")
            draws.append(dbeta_down(ctx, fri, fr["FE1"], bb=b1))
            del fri, Tm
            for f_ in fl:
                for x in f_:
                    pfl[x] = pfl.get(x, 0) + 1
            how[src] = how.get(src, 0) + 1
    plog = [dict(x) for x in POOL_LOG[n_pool:]]
    true = dbeta_down(ctx, fr["FE3"], fr["FE1"], bb=b1)
    p95 = float(np.percentile(draws, 95)) if draws else None
    n3 = sum(1 for r in R["FE3"] if r.get("solver") != "hold_eg30")
    q13 = {"code": "Q13", "cls": "C", "slot": None, "parent": "Q02", "fr": fr["FE3"], "fr_pr": fe3_pr, "fr20": fe3_20,
           "controls": {"FE1": fr["FE1"], "FE1_20": fe1_20},
           "arms": {"C3_mirror": fr["FE3m"]},
           "placebo": {"random_days": {"stat": "하락월(39) 평균 Δβ(FE3_위약 − FE1) · D_c = 편입마다 창 1000일 중 비복원 균등 100일 · 씨앗 SEED + i",
                                       "draws": draws, "true": true, "p95": p95}},
           "perm": None, "g4": {"placebo_ge95": bool(p95 is not None and true >= p95)}, "label_caps": {},
           "f0": {"ok": n3 > 0, "why": "카드에 F0 없음 — FE3 이 풀린 편입 %d/%d" % (n3, len(R["FE3"]))},
           "targets_hash": thash(T["FE3"]),
           "log": {"interpretation": INTERP, "formations": R["FE3"], "summary": _sumrec(R["FE3"]),
                   "hash_dec": HASH_DEC, "hash_exact": thash(T["FE3"], None), "blas_env": blas_env(),
                   "mirror": {"summary": _sumrec(R["FE3m"]), "hash": thash(T["FE3m"]), "hash_exact": thash(T["FE3m"], None),
                              "formations": R["FE3m"]},
                   "placebo": {"n": len(draws), "flags": pfl, "how": how, "nproc": NPROC, "pool": plog,
                               "sec": round(time.time() - tp, 1)},
                   "turn": {v: fr[v].get("turn") for v in ("FE3", "FE3m")}, "sec": round(time.time() - t0, 1)}}
    return {"Q02": q02, "Q13": q13}


if __name__ == "__main__":
    r = selftest()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(0 if r["ok"] else 1)
