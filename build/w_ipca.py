# -*- coding: utf-8 -*-
"""build/w_ipca.py — 배치 W 카드 W01 IPCA-KPS8(조건부 잠재요인 기대수익 · 특성 = 시변 공분산의 도구) — 등록 A 확증 가족 카드(갱신 나 — 오케스트레이터 결정).

설계 원본(구속): wbatch_research.json final.slate.strategies[W01] · build_plan.modules[w_ipca] · oos_protocol · D03 ~ D07 · G_NoEG_inputs ·
  사용자 갱신(2026-09-27): 전방 원장 없음 · 등록 A 가족 {W01 · W04 · W10m} 한쪽 Holm α 0.05 — W01 방향 +1 · 스텝 S3e/S2/S1 은 W01 C 책 위 Δ 로만.

근본 이유(명세 fundamental_reason): 특성은 소수의 위험 · 오가격 요인에 대한 노출이 시간에 따라 변하는 것을 대리한다. 기대수익을 공분산 구조에 묶으면
  (제약 Γ_α = 0) 특성 → 수익을 직접 적합하는 것보다 자유도가 작고, 종목 특성이 바뀌면 노출이 따라 바뀌는 조건부 조정이 모형 안에 들어 있다.
  랩은 특성을 하나씩(동물원 314)과 가격 전용 ML(ML6)로만 쟀고 조건부 잠재요인 모형은 쓴 적이 없다.
금지 결합이 아닌 까닭(명세 why_not_a_banned_combination): 주장은 «특성 결합» 이 아니라 구조 제약 하나(수익은 공분산으로만 보상된다 · Γ_α = 0)다 →
  주 대비 = IPCA 대 같은 KPS8 의 비제약 선형(FM 기울기 확장평균 · 능형)의 Diebold–Mariano · DM t ≤ 0 이면 «모형이 일하지 않음» 주의(K5 주의 칸).
출처: Kelly · Pruitt · Su (2019 JFE · w24540)[직접 — 표 VI 주석 · 표 VII · §4.8] · Gu · Kelly · Xiu (2020 RFS) · Avramov · Cheng · Metzker (2023 MS) ·
  bkelly-lab/ipca(MIT · ALS 구조 참고 · 코드는 numpy 로 새로 짰다). 🔎 등록 전 확인(open_before_register): KPS 첫 IPCA 요인과 시장 상관(K 사유) · 표 VI · VII 문장.

규칙(명세 base · 초모수 없음 · 지금 고정)
  Z = KPS8 + 상수(L 9): ① 시장 베타(252일 일간 OLS 대 합집합 시총가중 시장 · 0.6·OLS + 0.4·1 축소) ② 단기반전 r_t ③ log ME(분할만 조정) ④ 12-2 모멘텀 ⑤ 52주 고점 대비
    P_t / max_{252일} P ⑥ 장기반전 r_{t−36..t−13}(36개월 이력 없으면 결측) ⑦ 12-7 모멘텀 ⑧ log 총자산(v_fund asset · 가용일 규칙 · 수준만 — G-NoEG 허용 예외 kps_size).
    🚨 B/M · E/P · CF/P · ROA · ROE · 레버리지 · 발생액은 없다(D03).
  변환: 달마다 단면 순위를 [−0.5, 0.5] 로 · 결측은 0(KPS).
  모형: 제약 IPCA(Γ_α = 0) · K = 3 고정 · Γ_β(9 × 3) 교대최소제곱(numpy) · 식별 Γ′Γ = I · 요인 직교 · 분산 내림차순 · 부호는 요인 평균이 양이 되게 ·
    초기값 = 관리 포트 PCA(첫 추정) · 다음 달부터 직전 Γ 로 따뜻한 시작 · 상대 목적 변화 < 1e−6 · 최대 500회.
  K 사유: K = 1 은 시장형이라 그 단면 예측은 «조건부 베타 × 시장 프리미엄» 이 되고 β 띠가 지운다 · K = 3 은 시장 밖의 모멘텀 · 반전 · 크기 축을 담는 가장 작은 K ·
    K 1 · 2 · 4 는 쌍둥이(보고).
  추정: Γ̂ 는 확장창 S-E(2010-01~ · 2014-06 앞 명단은 역적용 · 공개)로 매월 재적합 · 학습쌍 (z_s, r_{s+1}) 은 s+1 ≤ t ·
    🚨 λ̂(요인 평균)는 2014-06 이후 PIT 달로만 평균(워밍업 선견이 예측의 평균 부분으로 새지 않게 · D05).
  예측: r̂_{i,t+1} = z_{i,t}′Γ̂_β λ̂ → 섹터 안 z 가 카드 점수.
  C 팔: Z 에 교차항 2개만 더한다(L 11) — 시장 베타 × z(BAA10Y)(자금 제약 · Frazzini–Pedersen) · 단기반전 × z(VIX)(유동성 공급 보상 · Nagel 2012 ·
    V03 과 같은 기전 — 겹침 선언) · FRED 월말 값 1영업일 늦춤 · 확장창 표준화 · 모형이 실시간 확장창으로 적재를 추정하는 연속 조정 · 가설 하나(C 대 S).
  주 통계: z(r̂) 의 FM γ · Stage M-W 통제 · NW(3) · H1 γ > 0.
  구조 검정(보고 · 주의 칸): 월별 단면 MSE(섹터 평균을 뺀 r_{t+1} 목표 · 예측도 섹터 평균을 빼서 같은 목표)로 IPCA 대 (a) 같은 KPS8 의 FM 기울기 확장평균
    (b) 능형(λ 10점 로그 격자 · 학습창 안 퍼지 CV)의 DM t · 표본 밖 R²(0 예측 대비) · 폴드별 학습 곡선.
  IC_lit 0.012(½ 전) · P0 기록만(σ 0.047 에서 0.082 · σ 0.07 에서 0.043 [합성]).
  쌍둥이(보고만): K ∈ {1, 2, 4} · 비제약(Γ_α 자유) · λ̂ 를 S-E 전체로(선견 공개) · PIT 전용 학습(표본 밖 2018-08~ · T ≈ 96).
  대조: KPS8 문헌 부호 동일가중 합성(베타 − · 단기반전 − · 크기 − · 12-2 + · 52주 고점 + · 장기반전 − · 12-7 + · 총자산 −) · 비교선 x-mom12.
  F0 대체: G-EGD 가 W01 에서 실패하면 등록 전에 정한 대로 KPS7(총자산 뺌) — F0 허용 결정(수익 없음).

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  I1 ALS 목적 = 달마다 이름 평균 제곱오차의 달 평균(관리 포트 충분통계 W_t = Z′Z/N · x_t = Z′r/N · 달 같은 무게 — bkelly-lab/ipca 와 같은 무게).
     Γ 단계: [Σ_t (f_t f_t′) ⊗ W_t] vec(Γ) = vec(Σ_t x_t f_t′) · f 단계: f_t = (Γ′W_tΓ)^{−1}Γ′(x_t − W_tΓ_α).
  I2 식별(끝에 한 번): Γ = QR(Γ′Γ = I) → 요인 비중심 2차 모멘트 F′F/T 의 고유분해로 회전(내림차순) → 요인 평균 < 0 인 열은 부호를 뒤집는다 ·
     비제약판은 Γ_α ⊥ Γ_β(Γ_α ← (I − Γ_βΓ_β′)Γ_α · f ← f + Γ_β′Γ_α) 뒤 회전.
  I3 학습창에서 한 번도 0 이 아닌 적이 없는 도구 열은 뺀다(Γ 의 그 행 = 0) — C 팔 상태가 늘 0 이면 C = S(1e−12 · 명세 guards.identity).
  I4 λ̂ 평균 달 = 특성 달 s ≥ 2014-06(PIT 명단으로 만든 쌍 · 라벨 s+1 ≥ 2014-07) — 첫 표본 밖 결정 2016-08 에 26개월(명세 «26개월» 과 같다).
  I5 교차항 = rank(β) × z_t(BAA10Y) · rank(r_t) × z_t(VIX)(순위는 다시 매기지 않는다 — 다시 매기면 시간 변동이 사라진다) · z_t = 확장창 (x − 평균)/SD(월 관측 ≥ 60) ·
     x_t = 결정 달 안 두 번째로 늦은 관측(마지막 관측일에서 1영업일 늦춤).
  I6 선형 기준선: X = 섹터 안 평균을 뺀 KPS8 순위(상수 없음) · y = 섹터 평균을 뺀 r_{s+1} · 학습 달 = λ̂ 와 같은 PIT 달(I4 — 평균 부분 선견 차단) ·
     FM 기울기 = 달마다 OLS 의 평균 · 능형 b(λ) = (ΣA_s + λI)^{−1}Σc_s(달 같은 무게) · λ = τ·tr(ΣA)/L · τ ∈ logspace(−3, 2, 10) ·
     퍼지 5블록 CV(연속 블록 · 검증 블록 [a, b] 에 대해 학습에서 s ∈ [a − 1, b + 2] 를 뺀다 = 라벨 지평 1 퍼지 + 엠바고 2) · 손실 최소(동률이면 큰 λ).
  I7 손실_t = 이름 평균 (y_dm − ŷ_dm)²(ŷ 도 섹터 평균을 뺀다) · DM d_t = 손실(기준) − 손실(IPCA)(양수면 IPCA 가 낫다) · 학습 곡선 = 표본 밖 달을 차례로 4 폴드 · 폴드별 평균 손실.
  I8 KPS 베타 관측 ≥ 200(252일 안) · 52주 고점 = 252일 안 선 가격 ≥ 200 · 장기반전은 P_{m−36} 이 서야 한다 · 결측 특성은 순위 0.
  I9 시장(베타용) = 결정 달 m 말 합집합 시총 비중으로 m+1 달 일간 수익을 가중(그날 선 이름끼리 비례) — 달 안 흘러감 없는 근사.
  I10 🔎 ALS 멈춤 규칙(비평 1 L6 · 선언 · 명세 그대로 둔다): 명세 «상대 목적 변화 < 1e−6 · 최대 500회» 의 목적(I1)은 설명되지 않는 수익 분산이 지배해
     따뜻한 시작이면 두어 번 만에 멈춘다 — Γ̂_t 는 결정마다의 정확한 argmin 이 아니라 직전 Γ 에서 이어진 경로에 기댄 해다(선견은 아니다 · 쌍둥이 · 팔마다
     경로가 다르다). 합성 대조(등록 전 · 수익 없음 · 잡음 0.10 · 요인 SD 0.015 ~ 0.03 · 400 종 · 결정 120): 명세 규칙 대 완전 수렴(허용 1e−13) 결정 점수
     상관 최소 0.99999 · r̂ 상대 차 최대 0.34% — 규칙을 바꾸지 않고 경로 의존을 공개한다(결과 문서에 반복 수 · 수렴 표지를 싣는다).

🚨 랩 규율 — IPCA 적합은 학습쌍의 수익을 쓴다(신호의 추정). 등록 전에는 합성 · 눈가림(y = 씨앗 잡음) 패널에서만 돌린다: 수익을 읽는 공개 함수
   (walkforward · linear_baselines · structural_test)는 패널 kind 를 받고 w_core.assert_kind_allowed 를 지난다. --selftest 는 합성 자료만.

  python build/w_ipca.py --selftest
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

CARD = "W01"
KPS8 = ("beta_kps", "r1", "log_me", "mom", "hi52", "ltr", "mom12_7", "log_asset")
KPS7 = tuple(c for c in KPS8 if c != "log_asset")          # F0 대체(G-EGD 실패 시 · 허용 결정)
LIT_SIGN = {"beta_kps": -1, "r1": -1, "log_me": -1, "mom": +1, "hi52": +1, "ltr": -1, "mom12_7": +1, "log_asset": -1}
CROSS = (("beta_kps", "z_baa"), ("r1", "z_vix"))           # C 팔 교차항(I5)
K_MAIN, K_TWINS = 3, (1, 2, 4)
ALS_TOL, ALS_MAXIT = 1e-6, 500
TRAIN_FROM = "2010-01"                                     # S-E(D27)
LAM_FROM = "2014-06"                                       # PIT(I4)
FIRST_DECISION, LAST_DECISION = "2016-08", "2026-07"
PIT_ONLY_FIRST = "2018-08"                                 # 쌍둥이 PIT 전용 학습의 첫 표본 밖
IC_LIT = 0.012
BETA_SHRINK = (0.6, 0.4)
BETA_WIN, BETA_MIN = 252, 200
RIDGE_TAU = tuple(float(x) for x in np.logspace(-3, 2, 10))
CV_BLOCKS, CV_PURGE, CV_EMBARGO = 5, 1, 2
Z_STATE_MIN = 60
DIRECTION = WC.CARD_DIRECTION[CARD]
assert DIRECTION == +1

IPCA_UNITS = [WG.unit("beta_kps", source="data/pit_px.json", concept="market beta 252d OLS vs union cap-weighted market (shrunk)", use="signal"),
              WG.unit("r1", source="data/pit_px.json", concept="short-term reversal r_t", use="signal"),
              WG.unit("log_me", source="v_px_split.me_value", concept="log market cap (split-only ME)", use="signal"),
              WG.unit("mom", source="data/pit_px.json", concept="momentum r_{t-12..t-2}", use="signal"),
              WG.unit("hi52", source="data/pit_px.json", concept="price relative to 52-week high", use="signal"),
              WG.unit("ltr", source="data/pit_px.json", concept="long-term reversal r_{t-36..t-13}", use="signal"),
              WG.unit("mom12_7", source="data/pit_px.json", concept="intermediate momentum r_{t-12..t-7}", use="signal"),
              WG.unit("log_asset", source="v_fund(first-filed ledger)", concept="log_asset_level", use="kps_size"),
              WG.unit("z_baa", source="data/assets.json macro BAA10Y", concept="credit spread level expanding z", use="theta_state"),
              WG.unit("z_vix", source="data/assets.json macro VIXCLS", concept="implied volatility expanding z", use="theta_state")]
WG.assert_units(IPCA_UNITS, "w_ipca 입력(모듈 적재)")


# ══════════════════════════════════════════════════════════════════════════
#  변환 · 도구 행렬
# ══════════════════════════════════════════════════════════════════════════
def rank_transform(x):
    """KPS 변환 — 단면 순위(동률 평균) → [−0.5, 0.5] · 결측 0 · 선 이름 1 개면 0."""
    x = np.asarray(x, float)
    out = np.zeros(len(x))
    ok = np.flatnonzero(np.isfinite(x))
    n = len(ok)
    if n <= 1:
        return out
    v = x[ok]
    order = np.argsort(v, kind="stable")
    r = np.empty(n)
    r[order] = np.arange(n, dtype=float)
    u, inv = np.unique(v, return_inverse=True)
    if len(u) < n:
        r = (np.bincount(inv, weights=r) / np.bincount(inv))[inv]
    out[ok] = r / (n - 1) - 0.5
    return out


def instruments(D, chars=KPS8, cross=None):
    """달 dict D(열쇠 = 특성 이름 · 배열) → Z(N × L) = [순위 특성 · 상수 · (교차항)]. cross = {"z_baa": z_t, "z_vix": z_t} 이면 C 팔(I5)."""
    cols = [rank_transform(D[c]) for c in chars]
    cols.append(np.ones(len(cols[0])))
    if cross is not None:
        for c, s in CROSS:
            zs = cross.get(s)
            zs = 0.0 if (zs is None or not (zs == zs)) else float(zs)
            cols.append(rank_transform(D[c]) * zs)
    return np.column_stack(cols)


def month_stats(Z, y):
    """관리 포트 충분통계(I1) — y 가 선 이름만: W = Z′Z/N · x = Z′y/N · rr = y′y/N · N."""
    y = np.asarray(y, float)
    ok = np.isfinite(y)
    Z, y = Z[ok], y[ok]
    N = len(y)
    if N == 0:
        return None
    return {"W": Z.T @ Z / N, "x": Z.T @ y / N, "rr": float(y @ y) / N, "N": N}


# ══════════════════════════════════════════════════════════════════════════
#  ALS(I1 · I2)
# ══════════════════════════════════════════════════════════════════════════
def _f_step(G, Ws, xs, Ga=None):
    A = np.einsum("lk,tlm,mj->tkj", G, Ws, G)
    xr = xs if Ga is None else xs - np.einsum("tlm,m->tl", Ws, Ga)
    b = np.einsum("lk,tl->tk", G, xr)
    try:
        return np.linalg.solve(A, b[..., None])[..., 0]
    except np.linalg.LinAlgError:
        return np.stack([np.linalg.lstsq(A[t], b[t], rcond=None)[0] for t in range(len(b))])


def _g_step(Ws, xs, F, alpha):
    T, L, _ = Ws.shape
    Ft = np.column_stack([F, np.ones(T)]) if alpha else F
    Kt = Ft.shape[1]
    A = np.einsum("tk,tm,tij->kimj", Ft, Ft, Ws).reshape(Kt * L, Kt * L)
    b = np.einsum("tk,ti->ki", Ft, xs).reshape(Kt * L)
    try:
        g = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        g = np.linalg.lstsq(A, b, rcond=None)[0]
    Gt = g.reshape(Kt, L).T
    return (Gt[:, :-1], Gt[:, -1]) if alpha else (Gt, None)


def _objective(G, Ga, F, Ws, xs, rr):
    pred = F @ G.T if Ga is None else F @ G.T + Ga[None, :]          # T × L(= Γf + Γ_α)
    return float(np.mean(rr - 2.0 * np.einsum("tl,tl->t", xs, pred) + np.einsum("tl,tlm,tm->t", pred, Ws, pred)))


def pca_init(xs, K):
    """관리 포트 PCA 초기값 — X(T × L)의 첫 K 오른쪽 특이벡터(L × K)."""
    _, _, Vt = np.linalg.svd(np.asarray(xs, float), full_matrices=False)
    return Vt[:K].T.copy()


def normalize(G, F, Ga=None):
    """I2 — Γ′Γ = I · 요인 비중심 2차 모멘트 대각(내림차순) · 요인 평균 양 · (비제약) Γ_α ⊥ Γ_β. 예측 z′(Γf + Γ_α) 는 바뀌지 않는다."""
    Q, R = np.linalg.qr(G)
    G1, F1 = Q, F @ R.T
    Ga1 = Ga
    if Ga is not None:
        c = G1.T @ Ga
        Ga1 = Ga - G1 @ c
        F1 = F1 + c[None, :]
    M = F1.T @ F1 / len(F1)
    ev, V = np.linalg.eigh(M)
    V = V[:, np.argsort(-ev)]
    G2, F2 = G1 @ V, F1 @ V
    sgn = np.where(F2.mean(0) < 0, -1.0, 1.0)
    return G2 * sgn[None, :], F2 * sgn[None, :], Ga1


def als(stats, K, alpha=False, G0=None, tol=ALS_TOL, maxit=ALS_MAXIT):
    """IPCA ALS — stats = [month_stats(…)](달 차례) → {G(L × K), Ga, F(T × K), obj, path, iters, converged, active}(I3 · 뺀 열의 Γ 행 = 0)."""
    Ws = np.stack([s["W"] for s in stats])
    xs = np.stack([s["x"] for s in stats])
    rr = np.array([s["rr"] for s in stats])
    L = Ws.shape[1]
    active = np.flatnonzero(np.abs(np.einsum("tii->i", Ws)) > 0)
    Wa, xa = Ws[:, active][:, :, active], xs[:, active]
    G = pca_init(xa, K) if G0 is None else np.asarray(G0, float)[active]
    if G0 is not None and np.linalg.matrix_rank(G) < K:
        G = pca_init(xa, K)
    Ga = np.zeros(len(active)) if alpha else None
    F = _f_step(G, Wa, xa, Ga)
    obj_prev, path, conv, it = None, [], False, 0
    for it in range(1, maxit + 1):
        G, Ga_new = _g_step(Wa, xa, F, alpha)
        Ga = Ga_new if alpha else None
        F = _f_step(G, Wa, xa, Ga)
        obj = _objective(G, Ga, F, Wa, xa, rr)
        path.append(obj)
        if obj_prev is not None and abs(obj_prev - obj) <= tol * max(abs(obj_prev), 1e-300):
            conv = True
            break
        obj_prev = obj
    G, F, Ga = normalize(G, F, Ga)
    Gf = np.zeros((L, K))
    Gf[active] = G
    Gaf = None
    if alpha:
        Gaf = np.zeros(L)
        Gaf[active] = Ga
    return {"G": Gf, "Ga": Gaf, "F": F, "obj": path[-1] if path else None, "path": path, "iters": it, "converged": conv, "active": active}


def forecast(Z, fit, lam):
    """r̂ = z′Γ̂λ̂ (+ z′Γ_α)."""
    r = Z @ (fit["G"] @ lam)
    return r + Z @ fit["Ga"] if fit.get("Ga") is not None else r


def sector_z(x, sector):
    """섹터 안 z(카드 점수) — 섹터 선 이름 ≥ 3 · SD > 0 이면 (x − 평균)/SD(ddof 1) · 아니면 0 · 섹터 없음은 NaN."""
    x = np.asarray(x, float)
    sec = np.asarray(sector, object)
    out = np.full(len(x), np.nan)
    for s in set(v for v in sec if v is not None):
        idx = np.flatnonzero((sec == s) & np.isfinite(x))
        if not len(idx):
            continue
        v = x[idx]
        sd = float(v.std(ddof=1)) if len(idx) >= 3 else 0.0
        out[idx] = (v - v.mean()) / sd if sd > 0 else 0.0
    return out


def sector_demean(x, sector):
    x = np.asarray(x, float)
    sec = np.asarray(sector, object)
    out = x.copy()
    for s in set(sec):
        m = sec == s
        ok = m & np.isfinite(x)
        if ok.any():
            out[m] = x[m] - x[ok].mean()
    return out


# ══════════════════════════════════════════════════════════════════════════
#  워크포워드(확장창 · λ̂ PIT 전용 · 따뜻한 시작)
# ══════════════════════════════════════════════════════════════════════════
def _panel_months(P):
    return [m for m in P["months"] if m in P["m"]]


def walkforward(P, K=K_MAIN, alpha=False, chars=KPS8, cross=None, train_from=TRAIN_FROM, lam_from=LAM_FROM,
                first=FIRST_DECISION, last=LAST_DECISION, log=None):
    """확장 워크포워드 — P = 패널{"kind", "months", "m": {달: D(특성 · y · sec)}} · cross = {달: {"z_baa", "z_vix"}}(C 팔) 또는 None.
    결정 t 마다 학습쌍 s ∈ [train_from, t−1](라벨 s+1 ≤ t) · Γ 는 직전 결정의 Γ 로 따뜻한 시작 · λ̂ = s ≥ lam_from 인 f_{s+1} 평균(I4).
    돌려주는 것 {dec: {t: {"rhat", "score", "lam", "n_lam", "T", "iters", "converged"}}, "spec"}. 🚨 학습쌍 수익 — kind 자물쇠."""
    WC.assert_kind_allowed(P.get("kind"), "w_ipca.walkforward")
    ms = _panel_months(P)
    Zc, St = {}, {}
    for m in ms:
        if m < train_from:
            continue
        D = P["m"][m]
        Zc[m] = instruments(D, chars, None if cross is None else (cross.get(m) or {}))
        s = month_stats(Zc[m], D["y"])
        if s is not None:
            St[m] = s
    decs = [m for m in ms if first <= m <= last]
    out, G_prev = {}, None
    t0 = time.time()
    for i, t in enumerate(decs):
        tr = [s for s in sorted(St) if train_from <= s <= WC.mshift(t, -1)]
        if len(tr) < max(12, 3 * K):
            continue
        fit = als([St[s] for s in tr], K, alpha, G0=G_prev)
        G_prev = fit["G"]
        lam_idx = [j for j, s in enumerate(tr) if s >= lam_from]
        if not lam_idx:
            continue
        lam = fit["F"][lam_idx].mean(0)
        rhat = forecast(Zc[t], fit, lam)
        out[t] = {"rhat": rhat, "score": sector_z(rhat, P["m"][t]["sec"]), "lam": lam, "n_lam": len(lam_idx), "T": len(tr),
                  "iters": fit["iters"], "converged": fit["converged"], "G": fit["G"], "active": fit["active"].tolist()}
        if log and i % 24 == 0:
            log("  W01 IPCA %s · K %d · T %d · 반복 %d · %.0fs" % (t, K, len(tr), fit["iters"], time.time() - t0))
    return {"dec": out, "spec": {"K": K, "alpha": alpha, "chars": list(chars), "cross": cross is not None, "train_from": train_from,
                                 "lam_from": lam_from, "first": first, "last": last}}


TWIN_SPECS = {
    "K1": dict(K=1), "K2": dict(K=2), "K4": dict(K=4),
    "UNRESTRICTED": dict(alpha=True),
    "LAM_SE": dict(lam_from=TRAIN_FROM),                  # λ̂ 를 S-E 전체로(선견 공개)
    "PIT_ONLY": dict(train_from=LAM_FROM, first=PIT_ONLY_FIRST),
}


def lit_composite(D, chars=KPS8):
    """대조 — KPS8 문헌 부호 동일가중 합성 = Σ 부호·순위 / 8(순위 결측 0)."""
    return np.sum([LIT_SIGN[c] * rank_transform(D[c]) for c in chars], axis=0) / len(chars)


# ══════════════════════════════════════════════════════════════════════════
#  C 팔 상태(I5)
# ══════════════════════════════════════════════════════════════════════════
def month_state(daily, months, min_n=Z_STATE_MIN):
    """FRED 일간 {날짜: 값} → 결정 달 m 의 x_m(그달 두 번째로 늦은 관측 · 1영업일 늦춤) → 확장창 z(관측 ≥ min_n · 아니면 None). 돌려주는 것 {달: z}."""
    by = {}
    for d in sorted(daily):
        v = daily[d]
        if v is None or not (v == v):
            continue
        by.setdefault(d[:7], []).append(float(v))
    allm = sorted(by)
    x = {m: (by[m][-2] if len(by[m]) >= 2 else None) for m in allm}
    hist, zs = [], {}
    for m in allm:
        if x[m] is None:
            continue
        hist.append(x[m])
        if len(hist) >= min_n:
            mu, sd = float(np.mean(hist)), float(np.std(hist, ddof=1))
            zs[m] = (x[m] - mu) / sd if sd > 0 else 0.0
    return {m: zs.get(m) for m in months}


def cross_states(baa_daily, vix_daily, months):
    zb, zv = month_state(baa_daily, months), month_state(vix_daily, months)
    return {m: {"z_baa": zb.get(m), "z_vix": zv.get(m)} for m in months}


# ══════════════════════════════════════════════════════════════════════════
#  선형 기준선 · 구조 검정(I6 · I7)
# ══════════════════════════════════════════════════════════════════════════
def _lin_month(D, chars=KPS8):
    sec = D["sec"]
    X = np.column_stack([sector_demean(rank_transform(D[c]), sec) for c in chars])
    y = sector_demean(np.asarray(D["y"], float), sec)
    ok = np.isfinite(y)
    return X, y, ok


def _lin_stats(X, y, ok):
    Xo, yo = X[ok], y[ok]
    N = len(yo)
    return {"A": Xo.T @ Xo / N, "c": Xo.T @ yo / N, "yy": float(yo @ yo) / N, "N": N} if N else None


def cv_blocks(train, n_blocks=CV_BLOCKS, purge=CV_PURGE, embargo=CV_EMBARGO):
    """퍼지 5블록 CV(I6) — [(학습 달, 검증 달)] · 검증 [a, b] 에 대해 학습에서 s ∈ [a − purge, b + embargo](달력) 를 뺀다."""
    tr = sorted(train)
    parts = np.array_split(np.arange(len(tr)), n_blocks)
    out = []
    for p in parts:
        if not len(p):
            continue
        val = [tr[j] for j in p]
        lo, hi = WC.mshift(val[0], -purge), WC.mshift(val[-1], embargo)
        fit = [s for s in tr if not (lo <= s <= hi)]
        out.append((fit, val))
    return out


def ridge_fit(stats, months, lam):
    A = sum(stats[s]["A"] for s in months)
    c = sum(stats[s]["c"] for s in months)
    return np.linalg.solve(A + lam * np.eye(A.shape[0]), c)


def ridge_choose(stats, train):
    """λ = τ·tr(ΣA)/L 격자에서 퍼지 CV 손실 최소(동률이면 큰 λ) — 돌려주는 것 (λ, τ, 손실 표)."""
    A = sum(stats[s]["A"] for s in train)
    scale = float(np.trace(A)) / A.shape[0]
    folds = cv_blocks(train)
    table = []
    for tau in RIDGE_TAU:
        lam = tau * scale
        loss = 0.0
        for fit, val in folds:
            if not fit:
                continue
            b = ridge_fit(stats, fit, lam)
            loss += sum(stats[s]["yy"] - 2 * b @ stats[s]["c"] + b @ stats[s]["A"] @ b for s in val)
        table.append((loss, -tau, tau, lam))
    best = min(table)
    return best[3], best[2], [(t[2], t[0]) for t in table]


def linear_baselines(P, first=FIRST_DECISION, last=LAST_DECISION, lam_from=LAM_FROM, chars=KPS8):
    """(a) FM 기울기 확장평균 · (b) 능형(퍼지 CV) — 학습 = 특성 달 s ∈ [lam_from, t−1](I6). 돌려주는 것 {t: {"fm": ŷ, "ridge": ŷ, "tau"}}.
    🚨 학습쌍 수익 — kind 자물쇠."""
    WC.assert_kind_allowed(P.get("kind"), "w_ipca.linear_baselines")
    ms = _panel_months(P)
    X, St, B = {}, {}, {}
    for m in ms:
        if m < lam_from:
            continue
        Xm, ym, ok = _lin_month(P["m"][m], chars)
        X[m] = Xm
        s = _lin_stats(Xm, ym, ok)
        if s is not None and s["N"] > len(chars) + 1:
            St[m] = s
            B[m] = np.linalg.lstsq(s["A"], s["c"], rcond=None)[0]
    out = {}
    for t in [m for m in ms if first <= m <= last]:
        tr = [s for s in sorted(St) if lam_from <= s <= WC.mshift(t, -1)]
        if len(tr) < 12 or t not in X:
            continue
        bfm = np.mean([B[s] for s in tr], axis=0)
        lam, tau, _ = ridge_choose(St, tr)
        brd = ridge_fit(St, tr, lam)
        out[t] = {"fm": X[t] @ bfm, "ridge": X[t] @ brd, "tau": tau}
    return out


def structural_test(P, ipca_dec, base, n_folds=4):
    """구조 검정(I7) — 손실 · DM(IPCA 대 FM · 능형) · 표본 밖 R² · 폴드별 학습 곡선. 🚨 수익 — kind 자물쇠."""
    WC.assert_kind_allowed(P.get("kind"), "w_ipca.structural_test")
    import w_stagem as S
    loss = {"ipca": {}, "fm": {}, "ridge": {}}
    ys, yh = {}, {"ipca": {}, "fm": {}, "ridge": {}}
    for t in sorted(set(ipca_dec) & set(base)):
        D = P["m"][t]
        y = sector_demean(np.asarray(D["y"], float), D["sec"])
        ok = np.isfinite(y)
        if ok.sum() < 20:
            continue
        preds = {"ipca": sector_demean(ipca_dec[t]["rhat"], D["sec"]), "fm": base[t]["fm"], "ridge": base[t]["ridge"]}
        ys[t] = y[ok]
        for k, p in preds.items():
            p = sector_demean(p, D["sec"])[ok]
            loss[k][t] = float(np.mean((y[ok] - p) ** 2))
            yh[k][t] = p
    ms = sorted(ys)
    res = {"T": len(ms)}
    for b in ("fm", "ridge"):
        res["dm_vs_" + b] = S.dm_test(ms, [loss[b][m] for m in ms], [loss["ipca"][m] for m in ms])
    res["oos_r2"] = {k: S.oos_r2(ys, yh[k])["r2"] for k in yh}
    folds = np.array_split(np.arange(len(ms)), n_folds)
    res["learning_curve"] = [{"from": ms[f[0]], "to": ms[f[-1]], **{k: float(np.mean([loss[k][ms[j]] for j in f])) for k in loss}}
                             for f in folds if len(f)]
    res["dm_t_gt0"] = bool((res["dm_vs_fm"]["t"] or -1) > 0 and (res["dm_vs_ridge"]["t"] or -1) > 0)
    return res


# ══════════════════════════════════════════════════════════════════════════
#  KPS8 특성 빌드(실자료 · v_pit.Universe 위 · 수익 없음 — 값을 찍지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def union_daily_market(U, months, DR=None, kcol=None):
    """I9 — 합집합 시총가중 일간 시장 수익(격자 배열 · 결측 NaN) · 결정 달 m 의 비중으로 m+1 달 날들을 가중 · DR/kcol(일간 수익 행렬 · 열 색인)을 주면 다시 쓴다."""
    D = U.D
    num = np.zeros(D)
    den = np.zeros(D)
    for m in months:
        m1 = WC.mshift(m, 1)
        if m not in U.me_idx or m1 not in U.me_idx:
            continue
        i0, i1 = U.me_idx[m] + 1, U.me_idx[m1] + 1
        me = U.me(m)
        for r in U.members(m):
            v = me[r["t"]][0]
            if not v:
                continue
            dr = (DR[i0:i1, kcol[r["k"]]] if DR is not None else U.daily_ret(r["k"])[i0:i1])
            ok = np.isfinite(dr)
            num[i0:i1][ok] += v * dr[ok]
            den[i0:i1][ok] += v
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def kps_beta(R, mkt):
    """KPS 베타(I8) — 252일 일간 OLS(유효 짝 ≥ 200) · 0.6·OLS + 0.4·1. R(W × N) · mkt(W)."""
    X = np.broadcast_to(np.asarray(mkt, float)[:, None], R.shape)
    valid = np.isfinite(R) & np.isfinite(X)
    n = valid.sum(0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        mx = np.where(valid, X, 0.0).sum(0) / n
        my = np.where(valid, R, 0.0).sum(0) / n
        dx = np.where(valid, X - mx, 0.0)
        dy = np.where(valid, R - my, 0.0)
        b = (dx * dy).sum(0) / (dx * dx).sum(0)
    b = BETA_SHRINK[0] * b + BETA_SHRINK[1] * 1.0
    b[(n < BETA_MIN) | ~np.isfinite(b)] = np.nan
    return b


def kps8_month(U, m, rows, mkt_d, asset_of=None, DR=None, kcol=None):
    """결정 달 m 의 KPS8 원값(rows = [{t, k, gid}]) — 돌려주는 것 {특성: 배열}. log_asset 은 asset_of(행, 결정일) → 값 | None(v_fund 가용일 규칙).
    52주 고점은 넘겨받은 가격 계열(수정종가)의 252일 최대 대비(I8) — 명세는 분할만 조정 종가(패널 빌드가 원 종가 × 분할로 만든다 · 여기 근사는 배당 몫만 다르다)."""
    i = U.me_idx[m]
    j = U._mpos[m]
    n = len(rows)
    out = {c: np.full(n, np.nan) for c in KPS8}
    p0 = max(0, i - BETA_WIN + 1)
    if DR is not None and n:
        Rd = DR[p0:i + 1][:, [kcol[r["k"]] for r in rows]]
    else:
        Rd = np.column_stack([U.daily_ret(r["k"])[p0:i + 1] for r in rows]) if n else np.zeros((0, 0))
    out["beta_kps"] = kps_beta(Rd, mkt_d[p0:i + 1]) if n else out["beta_kps"]
    me = U.me(m)
    d = U.d_of(m)
    for a, r in enumerate(rows):
        k = r["k"]
        pm = U.Pm[k]
        g = lambda jj: pm[jj] if 0 <= jj < len(pm) else np.nan
        with np.errstate(invalid="ignore", divide="ignore"):
            out["r1"][a] = g(j) / g(j - 1) - 1.0
            out["mom"][a] = g(j - 1) / g(j - 12) - 1.0
            out["mom12_7"][a] = g(j - 6) / g(j - 12) - 1.0
            out["ltr"][a] = g(j - 12) / g(j - 36) - 1.0
        v = me.get(r["t"], (None,))[0]
        out["log_me"][a] = math.log(v) if v else np.nan
        px = np.asarray(U.PX[k], float)[p0:i + 1]
        okp = np.isfinite(px) & (px > 0)
        if okp.sum() >= BETA_MIN and np.isfinite(px[-1]) and px[-1] > 0:
            out["hi52"][a] = float(px[-1] / px[okp].max())
        if asset_of is not None:
            at = asset_of(r, d)
            out["log_asset"][a] = math.log(at) if (at is not None and at > 0) else np.nan
    for c in ("r1", "mom", "mom12_7", "ltr"):
        out[c] = np.where(np.isfinite(out[c]), out[c], np.nan)
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


def _synth_ipca(seed, months, N=300, K=3, alpha_true=None, noise=0.05, f_sd=0.08):
    rng = np.random.default_rng(seed)
    L = len(KPS8) + 1
    G = np.linalg.qr(rng.normal(0, 1, (L, K)))[0]
    lam = np.array([0.02, 0.01, 0.005][:K] + [0.004] * max(0, K - 3))
    P = {"kind": "synth", "months": list(months), "m": {}}
    truth = {"G": G, "lam": lam, "f": {}}
    for m in months:
        D = {c: rng.normal(0, 1, N) for c in KPS8}
        D["hi52"][rng.random(N) < 0.05] = np.nan
        D["sec"] = np.array(["S%d" % (i % 7) for i in range(N)], object)
        Z = instruments(D)
        f = lam + rng.normal(0, f_sd, K)
        y = Z @ G @ f + (Z @ alpha_true if alpha_true is not None else 0.0) + rng.normal(0, noise, N)
        D["y"] = y
        P["m"][m] = D
        truth["f"][m] = f
    return P, truth


def _st_transform():
    x = np.array([3.0, 1.0, np.nan, 1.0, 5.0])
    r = rank_transform(x)
    assert np.allclose(r, [2 / 3 - 0.5, 0.5 / 3 - 0.5, 0.0, 0.5 / 3 - 0.5, 0.5], atol=1e-15)          # 동률 평균 순위 · 결측 0
    assert np.allclose(rank_transform([1.0, 2.0, 3.0]), [-0.5, 0.0, 0.5]) and np.all(rank_transform([np.nan, 2.0]) == 0)
    rr = rank_transform(np.random.default_rng(1).normal(0, 1, 101))
    assert abs(rr.mean()) < 1e-12 and rr.min() == -0.5 and rr.max() == 0.5
    D = {c: np.arange(5.0) for c in KPS8}
    Z = instruments(D)
    assert Z.shape == (5, 9) and np.all(Z[:, 8] == 1.0)
    Zc = instruments(D, cross={"z_baa": 2.0, "z_vix": None})
    assert Zc.shape == (5, 11) and np.allclose(Zc[:, 9], 2.0 * Z[:, 0]) and np.all(Zc[:, 10] == 0)
    s = month_stats(Z, np.array([1.0, np.nan, 0.0, 2.0, 1.0]))
    assert s["N"] == 4 and s["W"].shape == (9, 9)
    assert abs(lit_composite(D).mean()) < 1e-12
    return "KPS 순위 변환([−0.5, 0.5] · 결측 0 · 동률) · 도구 L 9 / C 팔 L 11 · 충분통계 · 문헌 부호 합성"


def _st_als_recovery():
    months = WC.months_between("2010-01", "2019-12")
    P, tr = _synth_ipca(WC.SEED, months)
    stats = [month_stats(instruments(P["m"][m]), P["m"][m]["y"]) for m in months]
    fit = als(stats, 3)
    G = fit["G"]
    assert fit["converged"] and np.allclose(G.T @ G, np.eye(3), atol=1e-10)                      # Γ′Γ = I
    M = fit["F"].T @ fit["F"] / len(fit["F"])
    assert np.allclose(M, np.diag(np.diag(M)), atol=1e-10) and np.all(np.diff(np.diag(M)) <= 1e-12)   # 요인 직교 · 내림차순
    assert np.all(fit["F"].mean(0) > 0)                                                        # 부호
    Pt = tr["G"] @ tr["G"].T
    Pe = G @ G.T
    dist = float(np.linalg.norm(Pt - Pe, 2))
    assert dist < 0.05, dist                                                                   # 심은 Γ 부분공간 복원
    p = np.array(fit["path"])
    assert np.all(np.diff(p) <= 1e-12 * np.abs(p[:-1]) + 1e-18), "ALS 목적이 늘었다"
    # 예측 불변(식별 전후) — normalize 는 z′Γf 를 바꾸지 않는다
    rng = np.random.default_rng(3)
    G0 = rng.normal(0, 1, (9, 3))
    F0 = rng.normal(0, 1, (50, 3))
    Gn, Fn, _ = normalize(G0, F0)
    assert np.allclose(F0 @ G0.T, Fn @ Gn.T, atol=1e-12)
    # 비제약: 심은 Γ_α 복원
    at = np.zeros(9)
    at[1] = 0.01
    at[8] = 0.002
    Pa, tra = _synth_ipca(WC.SEED + 1, months, alpha_true=at)
    sa = [month_stats(instruments(Pa["m"][m]), Pa["m"][m]["y"]) for m in months]
    fa = als(sa, 3, alpha=True)
    ap = (np.eye(9) - fa["G"] @ fa["G"].T) @ at
    assert np.allclose(fa["G"].T @ fa["Ga"], 0, atol=1e-10) and float(np.linalg.norm(fa["Ga"] - ap)) < 0.003, (fa["Ga"], ap)
    # 따뜻한 시작 = 같은 해(빠르게)
    fw = als(stats, 3, G0=fit["G"])
    assert fw["iters"] <= fit["iters"] and np.allclose(fw["G"] @ fw["G"].T, Pe, atol=1e-5)
    return "심은 Γ 부분공간 복원(‖ΔP‖ %.3f) · Γ′Γ = I · 요인 직교 · 내림차순 · 평균 양 · 단조 목적 · 식별 불변 · 비제약 Γ_α ⊥ Γ_β 복원 · 따뜻한 시작(%d → %d회)" % (
        dist, fit["iters"], fw["iters"])


def _st_walkforward():
    months = WC.months_between("2010-01", "2019-06")
    P, tr = _synth_ipca(WC.SEED + 2, months, N=200)
    W = walkforward(P, first="2016-08", last="2019-04")
    t = "2017-03"
    e = W["dec"][t]
    assert e["n_lam"] == len(WC.months_between(LAM_FROM, WC.mshift(t, -1))) and e["T"] == len(WC.months_between(TRAIN_FROM, WC.mshift(t, -1)))
    assert W["dec"]["2016-08"]["n_lam"] == 26                                                  # I4 — 명세 «첫 표본 밖 달에 26개월»
    # 선견 이동 검사(w_hygiene.lookahead_shift) — t 뒤 자료를 모두 바꿔도 결정 t 의 점수는 같다
    import w_hygiene as H

    def trunc(PP, tt):
        Q = {"kind": PP["kind"], "months": [m for m in PP["months"] if m <= tt], "m": {}}
        for m in Q["months"]:
            D = dict(PP["m"][m])
            if m == tt:
                D["y"] = np.full(len(D["y"]), np.nan)            # 결정 t 의 y(다음 달 수익)는 t 에 모른다
            Q["m"][m] = D
        return Q

    def sig(PP, tt):
        return walkforward(PP, first=tt, last=tt)["dec"][tt]["rhat"]
    la = H.lookahead_shift(sig, P, trunc, ["2016-11", "2018-02", "2019-01"], WC.SEED)
    assert la["ok"], la
    # 점수 = 섹터 안 z · λ̂ = PIT 달 f 평균(직접)
    D = P["m"][t]
    assert np.allclose(e["score"], sector_z(e["rhat"], D["sec"]), atol=0)
    tr_ms = [s for s in months if TRAIN_FROM <= s <= WC.mshift(t, -1)]
    fit = als([month_stats(instruments(P["m"][s]), P["m"][s]["y"]) for s in tr_ms], 3)
    lam = fit["F"][[j for j, s in enumerate(tr_ms) if s >= LAM_FROM]].mean(0)
    fr = forecast(instruments(D), fit, lam)                                                # 따뜻한 시작 · PCA 시작의 수렴 오차(상대 목적 1e−6) 안에서 같다
    assert np.corrcoef(fr, e["rhat"])[0, 1] > 0.99999 and float(np.max(np.abs(fr - e["rhat"]))) < 1e-3 * float(np.std(fr))
    # 예측과 참 기대수익의 상관(심은 구조 · 합성) · 쌍둥이 명세 · 실자료 자물쇠
    Et = instruments(D) @ tr["G"] @ tr["lam"]
    assert np.corrcoef(Et, e["rhat"])[0, 1] > 0.9
    assert set(TWIN_SPECS) == {"K1", "K2", "K4", "UNRESTRICTED", "LAM_SE", "PIT_ONLY"}
    Wp = walkforward(P, first="2018-08", last="2018-09", **{k: v for k, v in TWIN_SPECS["PIT_ONLY"].items() if k != "first"})
    assert Wp["dec"]["2018-08"]["T"] == len(WC.months_between(LAM_FROM, "2018-07"))
    assert _raises(lambda: walkforward(dict(P, kind="real")))
    return "확장창 T · λ̂ PIT 26개월(2016-08) · 선견 이동 검사 통과 · 점수 = 섹터 z · 직접 재적합과 같은 예측 · 참 기대수익 상관 · 쌍둥이 · 실자료 자물쇠"


def _st_carm_identity():
    months = WC.months_between("2010-01", "2018-06")
    P, _ = _synth_ipca(WC.SEED + 3, months, N=150)
    S0 = walkforward(P, first="2016-08", last="2018-04")
    C0 = walkforward(P, first="2016-08", last="2018-04", cross={m: {"z_baa": 0.0, "z_vix": 0.0} for m in months})
    worst = max(float(np.max(np.abs(S0["dec"][t]["rhat"] - C0["dec"][t]["rhat"]))) for t in S0["dec"])
    assert worst <= 1e-12, worst                                                             # 명세 guards.identity(상태 ≡ 0 → C = S)
    rng = np.random.default_rng(5)
    C1 = walkforward(P, first="2016-08", last="2016-09", cross={m: {"z_baa": float(rng.normal()), "z_vix": float(rng.normal())} for m in months})
    assert C1["dec"]["2016-08"]["G"].shape == (11, 3) and len(C1["dec"]["2016-08"]["active"]) == 11
    # 상태 z(I5) — 1영업일 늦춤 · 확장창 · 최소 60 · 선견 없음
    days = {}
    for m in WC.months_between("1990-01", "2026-08"):
        for dd in (3, 15, 27, 28):
            days["%s-%02d" % (m, dd)] = float(rng.normal(2, 0.5))
    z = month_state(days, WC.months_between("1994-01", "2026-08"))
    assert z["1994-01"] is None and z["1995-01"] is not None
    xs = [days["%s-27" % m] for m in WC.months_between("1990-01", "2000-06")]
    assert abs(z["2000-06"] - (xs[-1] - np.mean(xs)) / np.std(xs, ddof=1)) < 1e-12
    d2 = dict(days)
    d2["2000-07-27"] = 99.0
    assert month_state(d2, ["2000-06"])["2000-06"] == z["2000-06"]
    return "C 팔 항등(상태 ≡ 0 → C = S · 최대 차 %.1e) · L 11 · 상태 z(1영업일 늦춤 · 확장 · 최소 60 · 선견 없음)" % worst


def _st_baselines():
    months = WC.months_between("2014-06", "2019-06")
    P, tr = _synth_ipca(WC.SEED + 4, months, N=250)
    # CV 블록 — 퍼지 · 엠바고
    ms = WC.months_between("2014-06", "2016-07")
    folds = cv_blocks(ms)
    assert len(folds) == 5
    for fit, val in folds:
        lo, hi = WC.mshift(val[0], -1), WC.mshift(val[-1], 2)
        assert not [s for s in fit if lo <= s <= hi] and not (set(fit) & set(val))
    # 능형 = 직접 풀이 · λ → 0 이면 합동 OLS
    St = {}
    for m in ms:
        X, y, ok = _lin_month(P["m"][m])
        St[m] = _lin_stats(X, y, ok)
    b0 = ridge_fit(St, ms, 1e-12)
    Xa = np.vstack([_lin_month(P["m"][m])[0] / math.sqrt(St[m]["N"]) for m in ms])
    ya = np.concatenate([_lin_month(P["m"][m])[1] / math.sqrt(St[m]["N"]) for m in ms])
    assert np.allclose(b0, np.linalg.lstsq(Xa, ya, rcond=None)[0], atol=1e-8)
    lam, tau, tab = ridge_choose(St, ms)
    assert tau in RIDGE_TAU and len(tab) == 10
    base = linear_baselines(P, first="2016-08", last="2019-04")
    W = walkforward(P, first="2016-08", last="2019-04", train_from="2014-06")
    stt = structural_test(P, W["dec"], base)
    assert stt["T"] >= 30 and stt["dm_vs_fm"]["t"] is not None and set(stt["oos_r2"]) == {"ipca", "fm", "ridge"}
    assert len(stt["learning_curve"]) == 4
    # 참 구조가 IPCA 이면 IPCA 손실이 FM 평균보다 작다(DM t > 0 쪽 · 합성)
    assert stt["dm_vs_fm"]["mean"] > 0, stt["dm_vs_fm"]
    assert _raises(lambda: linear_baselines(dict(P, kind="real")))
    return "퍼지 CV(퍼지 1 · 엠바고 2) · 능형 = 합동 OLS 극한 · λ 격자 10 · 기준선 · 구조 검정(DM · R²_OS · 학습 곡선 4) · IPCA 구조에서 DM 평균 > 0"


def _st_features():
    # KPS 베타 식 · 축소 · 관측 규칙
    rng = np.random.default_rng(WC.SEED + 5)
    mkt = rng.normal(0.0004, 0.01, 252)
    R = 1.3 * mkt[:, None] + rng.normal(0, 0.01, (252, 4))
    R[:60, 3] = np.nan
    b = kps_beta(R, mkt)
    ols = np.cov(R[:, 0], mkt, ddof=1)[0, 1] / np.var(mkt, ddof=1)
    assert abs(b[0] - (0.6 * ols + 0.4)) < 1e-12 and np.isnan(b[3])
    assert KPS7 == ("beta_kps", "r1", "log_me", "mom", "hi52", "ltr", "mom12_7")
    assert set(LIT_SIGN) == set(KPS8) and not WG.check_units(IPCA_UNITS)
    assert WG.unit_violation(WG.unit("log_asset", concept="log_asset_level", use="signal"))            # 총자산은 kps_size 쓰임으로만
    return "KPS 베타(0.6·OLS + 0.4 · 관측 ≥ 200) · KPS7 대체 · 문헌 부호 표 · 총자산 쓰임 제한(kps_size)"


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
    assert not WG.literal_scan(os.path.abspath(__file__))
    assert CARD in WC.FAMILY["A"]
    return "금지 import 없음 · 문자열 상수 · 등록 A 가족"


def selftest():
    res, ok = [], True
    for fn in (_st_transform, _st_als_recovery, _st_walkforward, _st_carm_identity, _st_baselines, _st_features, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-18s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_ipca selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
