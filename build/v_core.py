# -*- coding: utf-8 -*-
"""build/v_core.py — 배치 V 추정기 · 책 산수: 가닥 기울기 · 군 R2 · 띠 · θ 사상 · 책 안 기울기(ATTN) · FM 배분기 추정기 ·
능동 상한 투영 · β 띠 · G-COMMON(크기 중립) · 종목 체결 · 흘러감 · 회전 · 비용(S 10bp · LIQ 상태 의존 · L COST_ERAS) · L 층 다리 팔.

설계 원본(구속): vbatch_research.json final.estimator(slope_path · targets · combine · R2_fix · theta_map · in_book_lever · allocator_estimator ·
  parameters_table · selftests) · final.slate.common_frame(book · theta_blend · beta_band · execution · costs · turnover_cap · identity · g_common_rule) ·
  final.allocator(estimator · target · execution · net_book). 설계를 다시 짓지 않는다.

복사(가져오지 않는다 — D22 · build_plan.no_import_rule): u_core 의 _shift3 · slope_path · pi_matrix · lw_corr · _lw_corr_batch · rhat_series · band ·
  direction_eval(🚨 군 R2 로 고침) · proj_box_sum0 · lw_cc_cov · sigma_series(다리 수 일반화) · execute_a · drift · a_path(K 일반화) · pct01 · _group_cap ·
  cap_book · net_book · no_derivative_positions · _draw_book · _st_calibration 틀. t_core 의 COST_ERAS · cost_rate · _turn_arrays · arm_weights 비용 ·
  turnover_1w 식. 원본과의 짝맞춤(합성 입력 · 1e−12)은 허용 목록 별도 프로세스(v_audit)의 몫이다 — 이 모듈은 u_core · t_core 를 부르지 않는다.

🚨 R2 고침(비평 2 A3 · u_core.py 의 agree = ((d≠0)&(sign==sign u)).sum(1) 은 가닥 수를 센다): 같은 쪽 «군» 의 수를 센다.
   군 합 D_c = Σ_{i∈c} d_i · 🔧 활성 군 = Σ_{i∈c} |d_i| > 0 인 군(검토 고침 · 등록 전) — 부호 잘림으로 b^c = 0 인 가닥 · z = 0(늦은 자료 stale) 인 달의
   가닥은 «증거 없음» 이라 활성도 같은 쪽도 아니다(옛 판은 z · b^c 가 선 가닥이면 활성으로 세어, 잘린 가닥 하나를 더하면 절반 강도 웹이 0 이 되는
   비단조가 있었다 — D09 «성긴 웹이 통째로 죽지 않게» 에 어긋남) · 같은 쪽 군 = D_c ≠ 0 ∧ sign(D_c) = sign(u).
   r2="cluster"(주): 활성 군 ≥ 2 → 같은 쪽 군 ≥ 2 여야 v = band(u), 아니면 0 · 활성 군 = 1 → v = band(u)/2 · 0 → v = 0.
   r2="strict"(C-R2S): 활성 군 = 1 → 0 · r2="off"(C-R2off): v = band(u).

명세가 정하지 않은 산수(최소 선택 · 여기서 선언 — 등록문에 옮긴다)
  V1 능동 상한 투영(project_active): 상자 lo_i = max(0, w_B,i − 0.05) ≤ w_i ≤ w_B,i + 0.05 · 섹터 |Σ_s(w − w_B)| ≤ 띠 · NASDAQ 100 전용 합 ≤ 0.10 · Σw = 1.
      차례: 상자 자르기 → 합 맞춤(더할 몫은 상자 밑 이름에 (w − lo) 비례 · 뺄 몫은 (w − lo) 비례 — u_core N2 의 «비중 비례» 를 능동 쪽으로) →
      섹터 띠(넘친 섹터는 (w − lo) 비례로 덜고 · 모자란 섹터는 w_B 비례로 채운 뒤 나머지 섹터에서 합 맞춤) → NASDAQ 100 전용(비례 축소 · 나머지에 합 맞춤) ·
      최대 200회. 그래도 어긋나면 w_B + s·(w − w_B) 를 이분법으로 줄여 맞춘다(w_B 는 늘 가능 · 볼록) — 줄임 몫을 보고한다.
  V2 β 띠(beta_band): 목표 = β̂(w_B) ± 0.03·(1 − 1e−3)(가까운 띠 끝 · 투영 뒤 미끄러짐 여유) · 기울기는 책 안(w > 0) 이름만 · κ 는 이분법 ·
      기울기 → 투영을 최대 20회 · 남은 틈 보고. β̂ 결측 이름은 1.0(u_core N3 와 같다).
  V3 종목 체결(execute_book): 틈 g_i = w*_i − w̃_i · w*_i = 0 이면 전량(삭제) · |g_i| < 0.1·w*_i 면 무거래(w0 = 그 이름의 목표 비중) · 아니면 fill·g_i
      (LIQ fill = 1) · 체결 뒤 합 1 로 비례 맞춤(u_core N1). 거래량 = Σ|w − w̃|(양쪽) · 편도 회전 = ½Σ.
  V4 흘러감(drift_book): 보유월 수익이 결측인 이름은 그달 책의 (알려진 이름) 가중 수익으로 흘러간다 · 책 수익은 알려진 이름끼리 비례 맞춤(pit_panel 과 같다).
  V5 θ 경로(theta_path): 첫 달의 «앞 θ» 는 θ0 · v 결측은 0(가닥 비활성 → 정적).
  V6 ATTN u^A = b^c/se(축소 · 부호 잘림 뒤 NW(6) t) · λ = ½·band(u^A) · pct_책 = 책 이름끼리 평균 순위 백분위 · γ_A 는 주 판 특성으로 보정 —
     주 판 = 명세 정의 a = ½·1[금] + ½·pct(같은 날 수)(문헌 판정 data/_vb_lit_open.json · HLT 작업 논문 판을 열었다 · 2026-09-27) · 합성 a = ½·Bernoulli(p = 0.082 ·
     earn_dates 금요일 접수 몫 · 개수만) + ½·연속 백분위.
  V7 FM 배분기: 달마다 ỹ_{f,s+1} = y_{f,s+1}/σ̂_f(s)(σ̂ = y_f 60개월 sd · 달 ≤ s−2 · 최소 36)를 r_{f,s} 에 절편 있는 OLS(K_s ≥ 3 · var(r) > 0) →
      c_s · 결정 t 표본 = s ≤ t−3 · 평균의 NW(6)(달력 지연 · 두 달 모두 유효한 쌍 · Bartlett · 자유도 보정 없음 — u_core N7) · 쌍 ≥ 120.
  V8 LIQ 비용 c_t = 10bp × max(1, σ_t / 중앙값_{≤t}(σ)) · σ_t = 결정일까지 SPY 21거래일 일수익 sd · 중앙값은 월말 σ 의 확장 중앙값(자료 첫 달부터).
  V9 L 다리 팔(arm_legs): t_core arm_weights · _turn_arrays · cost · turnover_1w 식(선물 다리 없음 · 내부 τ = 편도 연 · 2/12 × 비중).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산해서 찍지 않는다. --selftest 는 합성 자료만.

  python build/v_core.py --selftest
"""
from __future__ import annotations

import io
import math
import os
import re
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

# ══════════════════════════════════════════════════════════════════════════
#  등록 상수(final.estimator.parameters_table) — 여기서만 바꾼다
# ══════════════════════════════════════════════════════════════════════════
RHO = 0.0025
PAIRS_MIN, PAIRS_MIN_BSPRD = 120, 240
NW_SLOPE, NW_SLOPE_BSPRD = 6, 12
WLS_N, WLS_MIN = 60, 36
Y_LAG = 2
RHAT_N, RHAT_MIN = 120, 60
Z_MIN = 60
DEAD, BAND_END = 0.5, 2.0
R2_MIN_CLUSTERS = 2
SINGLE_CLUSTER_SCALE = 0.5
THETA0, DTHETA = 0.75, 0.25
THETA0_LIQ, DTHETA_LIQ = 0.5, 0.3
THETA0_LIQ_EMERG, DTHETA_LIQ_EMERG = 0.4, 0.2          # 비상 규칙 [0.2, 0.6] · θ0 0.4
DTHETA_STEP_MAX = 0.10
BETA_BAND, BETA_BAND_ITERS = 0.03, 20
ISSUER_ACTIVE_CAP = 0.05
SECTOR_BAND, SECTOR_BAND_LBS, SECTOR_BAND_SN = 0.10, 0.05, 0.03
NDX_ONLY_MAX = 0.10
FILL, FILL_LIQ = 0.5, 1.0
BAND_FRAC = 0.1
BUFFER = 1.5
A_B_FRAC, A_BOX_FRAC, A_FLOOR_FRAC = 0.25, 0.5, 0.5     # B = ¼w0 · 상자 ½w0 · 바닥 ½w0
A_TRADE_MAX = 0.20
NET_ISSUER_CAP = 0.10
NET_TE_MAX = 0.05
SIG_N, SIG_MIN = 60, 36                                  # Σ̂_A 60개월(최소 36)
G_COMMON_MAX = 0.30
LIQ_TURN_EMERGENCY = 9.0
SEED = 20260925
NPERM = 1000
LOOKAHEAD_T = 200
CLUSTER_RHO = 0.5
IBL_ONEWAY_MAX = 1.0 / 3.0
GAMMA_A = 2.75                                           # ATTN 합성 보정(λ = ½ 에서 한쪽 이동 중앙 ⅙ · N 100 · u_core 틀) — selftest 가 다시 잰다
#   보정 이력(모두 등록 전 · 합성 · 수익 없음): 2.77(첫 판 · 연속 백분위 틀) → 5.60(검토 반영 판 · 같은 날 절반이 문헌 강등돼 주 판이 이진 금요일 표지 ·
#   a ~ Bernoulli(p)) → **2.75**(2026-09-27 · HLT 작업 논문 판을 열어 같은 날 절반이 주 판으로 돌아왔다 — 주 판 = 명세 정의 a = ½·1[금] + ½·pct(같은 날 수) ·
#   합성 a = ½·Bernoulli(p) + ½·연속 백분위 · 이분법 근 2.752 → 소수 둘째 자리 2.75 · 한쪽 중앙 0.1666). 5.60 을 섞은 특성에 쓰면 한쪽 중앙 약 0.32(⅙ 의 두 배)다.
#   p = ATTN_FRIDAY_P = 8-K 2.02 접수일이 금요일인 몫(data/earn_dates.json · 2010~2026 · 개수만 · 수익 없음).
ATTN_FRIDAY_P = 0.082
SLEEVE = 0.10
S_COST, S_COST_ROBUST = 0.0010, 0.0020
LIQ_SIG_N = 21
COST_ERAS = (("1975-04", 0.0050), ("2000-12", 0.0020), ("9999-12", 0.0010))   # 복사: t_core.COST_ERAS
TURN_MAX = 10.0


# ══════════════════════════════════════════════════════════════════════════
#  E2 — 가닥 기울기(복사: u_core._shift3 · slope_path)
# ══════════════════════════════════════════════════════════════════════════
_MON = 5


def _shift3(c):
    out = np.zeros_like(c)
    if len(c) > 3:
        out[3:] = c[:-3]
    return out


def slope_path(z, y, sign, min_pairs=PAIRS_MIN, nw_lag=NW_SLOPE, wls=True, stambaugh=True, shrink=True, trunc=True, rho=RHO,
               y_lag=Y_LAG, sig_n=WLS_N, sig_min=WLS_MIN, detail=False):
    """가닥 하나의 결정 달별 기울기 — 복사: u_core.slope_path(식 · 차례 그대로).
    쌍 s: (z(s), ỹ(s+1) = y(s+1)/σ̂(s), z(s+1)) · σ̂(s) = y 의 [s−y_lag−sig_n+1, s−y_lag] sd(최소 sig_min · ddof 1) · 결정 i 의 표본 = 유효 쌍 s ≤ i − 3.
    Stambaugh 1차 · NW(nw_lag) · 사전 N(0, ρ) 사후 평균 · 부호 잘림. 돌려주는 것 dict(n, b_hat, b_corr, se, b_shr, b_c, ok[, …])."""
    z = np.asarray(z, float)
    y = np.asarray(y, float)
    T = len(z)
    if y_lag != Y_LAG:
        raise ValueError("목표 늦춤은 등록값 2 만")
    if wls:
        sd = pd.Series(y).rolling(sig_n, min_periods=sig_min).std(ddof=1).to_numpy()
        sig = np.full(T, np.nan)
        sig[y_lag:] = sd[:T - y_lag]
        sig = np.where(sig > 0, sig, np.nan)
    else:
        sig = np.ones(T)
    yt = np.full(T, np.nan)
    yt[:-1] = y[1:] / sig[:-1]
    z1 = np.full(T, np.nan)
    z1[:-1] = z[1:]
    val = np.isfinite(z) & np.isfinite(yt) & np.isfinite(z1)
    Z0 = np.where(val, z, 0.0)
    Y0 = np.where(val, yt, 0.0)
    Z1 = np.where(val, z1, 0.0)
    V = val.astype(float)
    cs = lambda a: _shift3(np.cumsum(a))
    n = cs(V)
    Sz, Szz, Sy, Syy, Syz = cs(Z0), cs(Z0 * Z0), cs(Y0), cs(Y0 * Y0), cs(Y0 * Z0)
    Sz1, Sz1z1, Szz1, Syz1 = cs(Z1), cs(Z1 * Z1), cs(Z0 * Z1), cs(Y0 * Z1)
    with np.errstate(invalid="ignore", divide="ignore"):
        det = n * Szz - Sz * Sz
        b = (n * Syz - Sz * Sy) / det
        a = (Sy - b * Sz) / n
        phi = (n * Szz1 - Sz * Sz1) / det
        c = (Sz1 - phi * Sz) / n
        suv = Syz1 - c * Sy - phi * Syz - a * Sz1 + a * c * n + a * phi * Sz - b * Szz1 + b * c * Sz + b * phi * Szz
        svv = Sz1z1 + c * c * n + phi * phi * Szz - 2 * c * Sz1 - 2 * phi * Szz1 + 2 * c * phi * Sz
        corr = (suv / svv) * (1.0 + 3.0 * phi) / n if stambaugh else np.zeros(T)
        A = np.stack([V, Z0, Y0, Z0 * Z0, Z0 * Y0], axis=1)
        Cc = np.zeros((T, 2, _MON))
        Cc[:, 0, 0], Cc[:, 0, 1], Cc[:, 0, 2] = -a, -b, 1.0
        Cc[:, 1, 1], Cc[:, 1, 3], Cc[:, 1, 4] = -a, -b, 1.0
        Cc = np.nan_to_num(Cc)
        Shat = np.zeros((T, 2, 2))
        for l in range(0, nw_lag + 1):
            Al = np.zeros_like(A)
            if l == 0:
                Al = A
            elif l < T:
                Al[l:] = A[:-l]
            prod = np.einsum("tm,tk->tmk", A, Al)
            Pl = _shift3(np.cumsum(prod, axis=0).reshape(T, -1)).reshape(T, _MON, _MON)
            G = np.einsum("tjm,tmk,tnk->tjn", Cc, Pl, Cc)
            if l == 0:
                Shat += G
            else:
                w = 1.0 - l / (nw_lag + 1.0)
                Shat += w * (G + np.transpose(G, (0, 2, 1)))
        inv = np.zeros((T, 2, 2))
        inv[:, 0, 0], inv[:, 0, 1], inv[:, 1, 0], inv[:, 1, 1] = Szz / det, -Sz / det, -Sz / det, n / det
        Vb = np.einsum("tij,tjk,tkl->til", inv, Shat, inv)
        se = np.sqrt(np.maximum(Vb[:, 1, 1], 0.0))
        if not wls:
            sdy = np.sqrt(np.maximum((Syy - Sy * Sy / n) / (n - 1.0), 0.0))
            sdy = np.where(sdy > 0, sdy, np.nan)
            b, corr, se = b / sdy, corr / sdy, se / sdy
        bc = b + corr
        bs = bc * rho / (rho + se * se) if shrink else bc.copy()
        bcut = sign * np.maximum(0.0, sign * bs) if trunc else bs.copy()
    ok = (n >= min_pairs) & np.isfinite(bcut) & np.isfinite(se) & (det > 0)
    out = {"n": n.astype(int), "b_hat": np.where(ok, b, np.nan), "b_corr": np.where(ok, bc, np.nan), "se": np.where(ok, se, np.nan),
           "b_shr": np.where(ok, bs, np.nan), "b_c": np.where(ok, bcut, np.nan), "ok": ok}
    if detail:
        out.update({"phi": phi, "a_hat": a, "suv": suv, "svv": svv, "valid_pairs": val, "ytil": yt})
    return out


def _wls_scale(y, y_lag=Y_LAG, sig_n=WLS_N, sig_min=WLS_MIN):
    """σ̂(s) = y 의 [s−y_lag−sig_n+1, s−y_lag] sd(최소 sig_min) — slope_path 와 같은 식(길이 T · 결측 NaN)."""
    y = np.asarray(y, float)
    T = len(y)
    sd = pd.Series(y).rolling(sig_n, min_periods=sig_min).std(ddof=1).to_numpy()
    sig = np.full(T, np.nan)
    sig[y_lag:] = sd[:T - y_lag]
    return np.where(sig > 0, sig, np.nan)


def _nw_mean_path(c, nw_lag):
    """c (T · 결측 NaN) → 결정 i 마다 표본 {c_s : s ≤ i − 3} 의 (n, 평균, NW(nw_lag) se). 달력 지연 · 두 달 모두 유효한 쌍 · Bartlett ·
    자유도 보정 없음(u_core N7). 앞합으로 한 번에."""
    c = np.asarray(c, float)
    T = len(c)
    v = np.isfinite(c)
    C = np.where(v, c, 0.0)
    V = v.astype(float)
    cs = lambda a: _shift3(np.cumsum(a))
    n = cs(V)
    S1, S2 = cs(C), cs(C * C)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = S1 / n
        tot = S2 - 2 * mu * S1 + n * mu * mu                        # Σ e²
        for l in range(1, nw_lag + 1):
            if l >= T:
                break
            Cl = np.zeros(T)
            Vl = np.zeros(T)
            Cl[l:], Vl[l:] = C[:-l], V[:-l]
            P = V * Vl                                              # 두 달 모두 유효
            Scc = cs(C * Cl * P)
            Sca = cs(C * P)                                         # Σ c_s (쌍)
            Scb = cs(Cl * P)                                        # Σ c_{s−l} (쌍)
            Np = cs(P)
            gl = Scc - mu * (Sca + Scb) + Np * mu * mu
            tot = tot + 2.0 * (1.0 - l / (nw_lag + 1.0)) * gl
        se = np.sqrt(np.maximum(tot, 0.0)) / n
    return n.astype(int), mu, se


def mean_path(y, sign=+1, min_pairs=PAIRS_MIN, nw_lag=NW_SLOPE, wls=True, shrink=True, trunc=True, rho=RHO):
    """책 안 기울기(ATTN) — slope_path 의 상수 조건(z ≡ 1) 판 = 실시간 축소 평균(명세 estimator.in_book_lever).
    ỹ(s+1) = y(s+1)/σ̂(s) · 결정 i 의 표본 s ≤ i − 3 · b̂ = 평균 · se = NW(nw_lag) · 사전 N(0, ρ) 사후 평균 · 부호 잘림 · 쌍 ≥ min_pairs.
    Stambaugh 는 없다(z 가 상수). 돌려주는 것 dict(n, b_hat, se, b_shr, b_c, u(= b_c/se · V6), ok)."""
    y = np.asarray(y, float)
    T = len(y)
    sig = _wls_scale(y) if wls else np.ones(T)
    yt = np.full(T, np.nan)
    yt[:-1] = y[1:] / sig[:-1]
    n, b, se = _nw_mean_path(yt, nw_lag)
    with np.errstate(invalid="ignore", divide="ignore"):
        bs = b * rho / (rho + se * se) if shrink else b.copy()
        bc = sign * np.maximum(0.0, sign * bs) if trunc else bs.copy()
        u = np.where(se > 0, bc / se, 0.0)
    ok = (n >= min_pairs) & np.isfinite(bc) & np.isfinite(se) & (se > 0)
    return {"n": n, "b_hat": np.where(ok, b, np.nan), "se": np.where(ok, se, np.nan), "b_shr": np.where(ok, bs, np.nan),
            "b_c": np.where(ok, bc, np.nan), "u": np.where(ok, u, np.nan), "ok": ok}


# ══════════════════════════════════════════════════════════════════════════
#  E4 π · E5 R̂ · 확신도 · 군 R2 · 띠 (복사: u_core pi_matrix · lw_corr · _lw_corr_batch · rhat_series · band · direction_eval[고침])
# ══════════════════════════════════════════════════════════════════════════
def pi_matrix(act, families, blocks, mode="family"):
    act = np.asarray(act, bool)
    T, p = act.shape
    out = np.zeros((T, p))
    if p == 0:
        return out
    A = act.astype(float)
    if mode == "flat":
        n = A.sum(1, keepdims=True)
        return np.where(n > 0, A / np.where(n > 0, n, 1.0), 0.0)
    blk = list(blocks) if mode == "family" else ["one"] * p
    fam = list(families)
    ub = list(dict.fromkeys(blk))
    ns_f = {}
    for f in dict.fromkeys(fam):
        cols = [i for i in range(p) if fam[i] == f]
        ns_f[f] = A[:, cols].sum(1)
    nf_b, bact = {}, {}
    for bname in ub:
        fs = list(dict.fromkeys(fam[i] for i in range(p) if blk[i] == bname))
        nf_b[bname] = sum((ns_f[f] > 0).astype(float) for f in fs)
        bact[bname] = nf_b[bname] > 0
    nb = sum(bact[bname].astype(float) for bname in ub)
    for i in range(p):
        f, bname = fam[i], blk[i]
        with np.errstate(invalid="ignore", divide="ignore"):
            v = A[:, i] / np.where(nb > 0, nb, 1.0) / np.where(nf_b[bname] > 0, nf_b[bname], 1.0) / np.where(ns_f[f] > 0, ns_f[f], 1.0)
        out[:, i] = np.where(act[:, i], v, 0.0)
    return out


def lw_corr(X, target_identity=True):
    X = np.asarray(X, float)
    n, p = X.shape
    if p == 0:
        return np.zeros((0, 0)), None
    Xc = X - X.mean(0, keepdims=True)
    sd = Xc.std(0)
    zero = ~(sd > 1e-12 * np.maximum(1.0, np.abs(X).max(0)))
    Xs = np.where(zero, 0.0, Xc / np.where(zero, 1.0, sd))
    S0 = Xs.T @ Xs / n
    S = S0.copy()
    S[np.diag_indices(p)] = np.where(zero, 1.0, np.diag(S0))
    I = np.eye(p)
    d2 = float(((S - I) ** 2).sum() / p)
    nx = (Xs * Xs).sum(1)
    b2bar = float(((nx * nx).sum() - n * (S0 ** 2).sum()) / (n * n * p))
    b2 = min(max(b2bar, 0.0), d2)
    delta = (b2 / d2) if d2 > 0 else 1.0
    R = delta * I + (1.0 - delta) * S
    if zero.any():
        R[zero, :] = 0.0
        R[:, zero] = 0.0
        R[np.diag_indices(p)] = 1.0
    return R, delta


def _lw_corr_batch(W):
    G, n, p = W.shape
    Xc = W - W.mean(1, keepdims=True)
    sd = Xc.std(1)
    scale = np.maximum(1.0, np.abs(W).max(1))
    zero = ~(sd > 1e-12 * scale)
    Xs = np.where(zero[:, None, :], 0.0, Xc / np.where(zero, 1.0, sd)[:, None, :])
    S0 = np.einsum("gnp,gnq->gpq", Xs, Xs) / n
    S = S0.copy()
    di = np.arange(p)
    S[:, di, di] = np.where(zero, 1.0, S0[:, di, di])
    I = np.eye(p)[None]
    d2 = ((S - I) ** 2).sum((1, 2)) / p
    nx = (Xs * Xs).sum(2)
    b2bar = ((nx * nx).sum(1) - n * (S0 ** 2).sum((1, 2))) / (n * n * p)
    b2 = np.minimum(np.maximum(b2bar, 0.0), d2)
    delta = np.where(d2 > 0, b2 / np.where(d2 > 0, d2, 1.0), 1.0)
    R = delta[:, None, None] * I + (1.0 - delta)[:, None, None] * S
    if zero.any():
        for g in np.flatnonzero(zero.any(1)):
            zc = zero[g]
            R[g][zc, :] = 0.0
            R[g][:, zc] = 0.0
            R[g][di, di] = 1.0
    return R


def rhat_series(Zmat, act, n=RHAT_N, min_n=RHAT_MIN):
    Zmat = np.asarray(Zmat, float)
    T, p = Zmat.shape
    R = np.broadcast_to(np.eye(p), (T, p, p)).copy()
    act = np.asarray(act, bool)
    sig = {}
    for t in range(T):
        if act[t].sum() >= 2:
            sig.setdefault(act[t].tobytes(), []).append(t)
    for key, ts in sig.items():
        cols = np.flatnonzero(np.frombuffer(key, dtype=bool))
        Zc = Zmat[:, cols]
        fin = np.isfinite(Zc).all(1)
        full, part = [], []
        for t in ts:
            if t >= n - 1 and fin[t - n + 1:t + 1].all():
                full.append(t)
            else:
                part.append(t)
        if full:
            sw = np.lib.stride_tricks.sliding_window_view(Zc, n, axis=0)
            Wn = np.transpose(sw[np.array(full) - (n - 1)], (0, 2, 1))
            Rg = _lw_corr_batch(np.ascontiguousarray(Wn))
            for j, t in enumerate(full):
                R[t][np.ix_(cols, cols)] = Rg[j]
        for t in part:
            lo = max(0, t - n + 1)
            Wt = Zc[lo:t + 1]
            Wt = Wt[np.isfinite(Wt).all(1)]
            if len(Wt) >= min_n:
                R[t][np.ix_(cols, cols)] = lw_corr(Wt)[0]
    return R


def band(u):
    """E6 — v = sign(u)·min(1, max(0, (|u| − 0.5)/1.5)) — 복사: u_core.band."""
    u = np.asarray(u, float)
    return np.sign(u) * np.minimum(1.0, np.maximum(0.0, (np.abs(u) - DEAD) / (BAND_END - DEAD)))


def direction_eval(Zf, Bc, act, signs, families, clusters, rho=RHO, conf="floor", r2="cluster", R=None, weights="family"):
    """한 전략 거미줄의 E3~E6(복사: u_core.direction_eval + 🚨 군 R2) — Zf (T×p) 예측 z · Bc (T×p) b^c · act (T×p) · signs (p) · 가족 · 군 번호.
    π = 가족 균형(pi_matrix family · 덩어리 하나) · u = D / max(√(aᵀR̂a), √(āᵀR̂ā)) · v = band(u) 뒤 군 R2(머리말).
    돌려주는 것 dict(u, v, v_raw, D, pi, d, n_act, n_clusters_act, n_clusters_same, scale)."""
    Zf = np.asarray(Zf, float)
    T, p = Zf.shape
    act = np.asarray(act, bool) & np.isfinite(Zf) & np.isfinite(Bc)
    pi = pi_matrix(act, families, ["char"] * p, weights)
    Z0 = np.where(act, Zf, 0.0)
    B0 = np.where(act, Bc, 0.0)
    d = pi * B0 * Z0
    D = d.sum(1)
    if R is None:
        R = rhat_series(np.where(np.isfinite(Zf), Zf, np.nan), act)
    a = pi * B0
    ab = pi * np.asarray(signs, float)[None, :] * math.sqrt(rho)
    qa = np.einsum("ti,tij,tj->t", a, R, a)
    qb = np.einsum("ti,tij,tj->t", ab, R, ab)
    den_own, den_pri = np.sqrt(np.maximum(qa, 0.0)), np.sqrt(np.maximum(qb, 0.0))
    den = np.maximum(den_own, den_pri) if conf == "floor" else den_own
    with np.errstate(invalid="ignore", divide="ignore"):
        u = np.where(den > 0, D / np.where(den > 0, den, 1.0), 0.0)
    cl = np.asarray(clusters)
    ucl = list(dict.fromkeys(cl.tolist()))
    n_cact = np.zeros(T, int)
    n_csame = np.zeros(T, int)
    su = np.sign(u)
    for c in ucl:
        m = cl == c
        n_cact += (np.abs(d[:, m]).sum(1) > 0.0).astype(int)                         # 활성 군 = 증거가 있는 군(Σ|d| > 0 · 잘린 · stale 가닥 제외)
        Dc = d[:, m].sum(1)
        n_csame += ((Dc != 0.0) & (np.sign(Dc) == su) & (su != 0)).astype(int)
    v_raw = band(u)
    if r2 == "off":
        scale = np.ones(T)
    elif r2 == "strict":
        scale = np.where((n_cact >= R2_MIN_CLUSTERS) & (n_csame >= R2_MIN_CLUSTERS), 1.0, 0.0)
    elif r2 == "cluster":
        scale = np.where(n_cact >= R2_MIN_CLUSTERS, np.where(n_csame >= R2_MIN_CLUSTERS, 1.0, 0.0),
                         np.where(n_cact == 1, SINGLE_CLUSTER_SCALE, 0.0))
    else:
        raise ValueError(r2)
    v = v_raw * scale
    return {"u": u, "v": v, "v_raw": v_raw, "D": D, "pi": pi, "d": d, "n_act": act.sum(1), "n_clusters_act": n_cact,
            "n_clusters_same": n_csame, "scale": scale, "den_own": den_own, "den_prior": den_pri}


def theta_path(v, theta0, dtheta, step=DTHETA_STEP_MAX, start=None, lo=None, hi=None):
    """θ_t = θ_{t−1} + clip(θ0 + Δθ·v_t − θ_{t−1}, −step, step)(V5 · 첫 앞 θ = θ0 · v 결측 = 0). v ≡ 0 이면 θ ≡ θ0(항등)."""
    v = np.nan_to_num(np.asarray(v, float), nan=0.0)
    tgt = theta0 + dtheta * v
    if lo is not None or hi is not None:
        tgt = np.clip(tgt, -np.inf if lo is None else lo, np.inf if hi is None else hi)
    out = np.empty(len(v))
    prev = theta0 if start is None else float(start)
    for t in range(len(v)):
        dd = min(max(tgt[t] - prev, -step), step)
        prev = prev + dd
        out[t] = prev
    return out


# ══════════════════════════════════════════════════════════════════════════
#  배분기 추정기 — Fama–MacBeth 전략 사이 기울기(명세 allocator.estimator · V7)
# ══════════════════════════════════════════════════════════════════════════
def fm_cross_slopes(R, Y, k_min=3, wls=True):
    """달 s 마다 ỹ_{f,s+1} 를 r_{f,s} 에 절편 있는 OLS → c_s(길이 T · 없으면 NaN) · 그달 K_s. R · Y = (T×K) · Y 는 보유 달 값."""
    R = np.asarray(R, float)
    Y = np.asarray(Y, float)
    T, K = R.shape
    if wls:
        sig = np.column_stack([_wls_scale(Y[:, f]) for f in range(K)])
    else:
        sig = np.ones((T, K))
    Yt = np.full((T, K), np.nan)
    Yt[:-1] = Y[1:] / sig[:-1]
    c = np.full(T, np.nan)
    ks = np.zeros(T, int)
    for s in range(T):
        m = np.isfinite(R[s]) & np.isfinite(Yt[s])
        ks[s] = int(m.sum())
        if m.sum() < k_min:
            continue
        x, y = R[s, m], Yt[s, m]
        vx = float(((x - x.mean()) ** 2).sum())
        if vx <= 1e-15:
            continue
        c[s] = float(((x - x.mean()) * (y - y.mean())).sum() / vx)
    return c, ks


def fm_slope_path(R, Y, min_pairs=PAIRS_MIN, nw_lag=NW_SLOPE, k_min=3, wls=True, shrink=True, trunc=True, rho=RHO):
    """배분기 기울기 — b̂_t = {c_s : s ≤ t−3} 평균 · NW(6) se · 사전 N(0, ρ) 사후 평균 · 부호 잘림(≥ 0) · 쌍(달) ≥ min_pairs.
    돌려주는 것 dict(c, K, n, b_hat, se, b_shr, b_c, ok)."""
    c, ks = fm_cross_slopes(R, Y, k_min=k_min, wls=wls)
    n, b, se = _nw_mean_path(c, nw_lag)
    with np.errstate(invalid="ignore", divide="ignore"):
        bs = b * rho / (rho + se * se) if shrink else b.copy()
        bc = np.maximum(0.0, bs) if trunc else bs.copy()
    ok = (n >= min_pairs) & np.isfinite(bc) & np.isfinite(se)
    return {"c": c, "K": ks, "n": n, "b_hat": np.where(ok, b, np.nan), "se": np.where(ok, se, np.nan), "b_shr": np.where(ok, bs, np.nan),
            "b_c": np.where(ok, bc, np.nan), "ok": ok}


def alloc_v(b_c, r, rho=RHO):
    """u_f = b^c·r_f / max(|b^c|, √ρ)(가닥 하나 · π = 1 · R̂ = 1 인 direction_eval 과 같다) · v^A_f = band(u_f) · 결측 0."""
    b_c = np.asarray(b_c, float)
    r = np.asarray(r, float)
    bb = np.nan_to_num(b_c, nan=0.0)
    den = np.maximum(np.abs(bb), math.sqrt(rho))
    u = (bb / den)[:, None] * np.nan_to_num(r, nan=0.0) if r.ndim == 2 else bb / den * np.nan_to_num(r, nan=0.0)
    return band(u), u


# ══════════════════════════════════════════════════════════════════════════
#  사영 · 공분산 · 배분 체결(복사: u_core proj_box_sum0 · lw_cc_cov · sigma_series · execute_a · drift · a_path)
# ══════════════════════════════════════════════════════════════════════════
def proj_box_sum0(x, b):
    x = np.asarray(x, float)
    f = lambda lam: float(np.clip(x - lam, -b, b).sum())
    ks = np.sort(np.r_[x - b, x + b])
    vals = np.array([f(k) for k in ks])
    if abs(f(0.0)) == 0.0 and (np.abs(x) <= b).all():
        return x.copy()
    lam = None
    for j in range(len(ks) - 1):
        if vals[j] >= 0.0 >= vals[j + 1]:
            if vals[j] == vals[j + 1]:
                lam = ks[j]
            else:
                lam = ks[j] + vals[j] * (ks[j + 1] - ks[j]) / (vals[j] - vals[j + 1])
            break
    if lam is None:
        lam = ks[0] if vals[0] <= 0 else ks[-1]
    return np.clip(x - lam, -b, b)


def lw_cc_cov(X):
    X = np.asarray(X, float)
    n, p = X.shape
    Xc = X - X.mean(0, keepdims=True)
    S = Xc.T @ Xc / n
    var = np.diag(S).copy()
    sq = np.sqrt(np.maximum(var, 0.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        rbar = (float((S / np.outer(sq, sq)).sum()) - p) / (p * (p - 1)) if p > 1 else 0.0
    F = rbar * np.outer(sq, sq)
    F[np.diag_indices(p)] = var
    Y = Xc * Xc
    phiM = Y.T @ Y / n - 2.0 * (Xc.T @ Xc) * S / n + S * S
    phi = float(phiM.sum())
    t1 = (Xc ** 3).T @ Xc / n
    theta = t1 - var[:, None] * S
    theta[np.diag_indices(p)] = 0.0
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = float(np.diag(phiM).sum() + rbar * ((np.outer(1.0 / sq, sq)) * theta).sum())
    gam = float(((S - F) ** 2).sum())
    kappa = (phi - rho) / gam if gam > 0 else 0.0
    delta = max(0.0, min(1.0, kappa / n))
    return delta * F + (1.0 - delta) * S, delta


def te_sleeve(dw, Sigma):
    dw = np.asarray(dw, float)
    return math.sqrt(max(12.0 * float(dw @ np.asarray(Sigma, float) @ dw), 0.0))


def sigma_series(legs_ex, n=SIG_N, min_n=SIG_MIN, lag=Y_LAG):
    L = np.asarray(legs_ex, float)
    T, p = L.shape
    out = np.full((T, p, p), np.nan)
    for t in range(T):
        e = t - lag
        if e < 0:
            continue
        W = L[max(0, e - n + 1):e + 1]
        W = W[np.isfinite(W).all(1)]
        if len(W) >= min_n:
            out[t] = lw_cc_cov(W)[0]
    return out


def execute_a(w_drift, target, w0, fill=FILL, band_frac=BAND_FRAC, trade_max=A_TRADE_MAX):
    w_drift, target, w0 = (np.asarray(x, float) for x in (w_drift, target, w0))
    gap = target - w_drift
    tr = np.where(np.abs(gap) >= band_frac * w0, fill * gap, 0.0)
    tot = float(np.abs(tr).sum())
    if tot > trade_max:
        tr = tr * (trade_max / tot)
    w = w_drift + tr
    w = w / w.sum()
    return w, float(np.abs(w - w_drift).sum())


def drift(w, r):
    w, r = np.asarray(w, float), np.asarray(r, float)
    g = w * (1.0 + r)
    R = float(g.sum()) - 1.0
    return g / g.sum(), R


def a_path(targets, R, w0, start_w=None, fill=FILL, band_frac=BAND_FRAC, trade_max=A_TRADE_MAX):
    """배분 경로 — 복사: u_core.a_path(다리 수 K 일반화). targets (T×K) · R (T×K 보유 달 수익) · 결정 i 체결 → 보유 i+1.
    돌려주는 것 dict(w (T×K) · S (T · 보유 달) · traded (T · 보유 달))."""
    targets, R = np.asarray(targets, float), np.asarray(R, float)
    T, K = targets.shape
    W = np.full((T, K), np.nan)
    S = np.full(T, np.nan)
    tr = np.zeros(T)
    cur = None
    for i in range(T):
        tg = targets[i]
        if not np.isfinite(tg).all():
            cur = None
            continue
        if cur is None:
            w = tg.copy() if start_w is None else np.asarray(start_w, float).copy()
            t_ = 0.0
        else:
            w, t_ = execute_a(cur, tg, w0, fill, band_frac, trade_max)
        W[i] = w
        if i + 1 < T and np.isfinite(R[i + 1]).all():
            cur, S[i + 1] = drift(w, R[i + 1])
            tr[i + 1] = t_
        else:
            cur = None
    return {"w": W, "S": S, "traded": tr}


def alloc_target(vA, w0, b_frac=A_B_FRAC, box_frac=A_BOX_FRAC):
    """Δw* = Π_{Σ=0, |Δw_f| ≤ ½w0}(B·(v^A_f − 평균 v^A)) · B = ¼w0 → 목표 w0 + Δw*(바닥 ½w0 는 상자에서 따라 나온다)."""
    vA = np.asarray(vA, float)
    x = b_frac * w0 * (vA - vA.mean())
    dw = proj_box_sum0(x, box_frac * w0)
    return w0 + dw, dw


# ══════════════════════════════════════════════════════════════════════════
#  백분위 · 발행사 상한 · 순액 책 · G8(복사: u_core pct01 · _group_cap · cap_book · net_book · no_derivative_positions)
# ══════════════════════════════════════════════════════════════════════════
def pct01(vals):
    ks = [k for k, v in vals.items() if v is not None and v == v and np.isfinite(v)]
    if not ks:
        return {}
    if len(ks) == 1:
        return {ks[0]: 0.5}
    x = np.array([vals[k] for k in ks], float)
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=float)
    u, inv = np.unique(x, return_inverse=True)
    for j in range(len(u)):
        m = inv == j
        if m.sum() > 1:
            r[m] = r[m].mean()
    return {k: float(rr / (len(x) - 1)) for k, rr in zip(ks, r)}


def _group_cap(w, w0, groups, cap):
    w = np.asarray(w, float).copy()
    g = np.asarray(groups)
    ug = list(dict.fromkeys(g.tolist()))
    gi = {x: np.flatnonzero(g == x) for x in ug}
    capg = {x: max(cap, float(w0[gi[x]].sum())) for x in ug}
    bound = False
    for _ in range(200):
        tot = {x: float(w[gi[x]].sum()) for x in ug}
        over = [x for x in ug if tot[x] > capg[x] + 1e-12]
        if not over:
            break
        bound = True
        ex = 0.0
        for x in over:
            ex += tot[x] - capg[x]
            w[gi[x]] *= capg[x] / tot[x]
        free = np.zeros(len(w), bool)
        for x in ug:
            if tot[x] < capg[x] - 1e-12 and x not in over:
                free[gi[x]] = True
        fs = float(w[free].sum())
        if fs <= 0:
            break
        w[free] += ex * w[free] / fs
    return w, bound


def cap_book(N, issuer_of, cap=0.10, limit=None):
    ks = sorted(N, key=lambda k: -N[k])
    tot = sum(N.values())
    if limit is not None and len(ks) > limit:
        ks = ks[:limit]
        s = sum(N[k] for k in ks)
        N = {k: N[k] * tot / s for k in ks}
    ks = sorted(N)
    w = np.array([N[k] for k in ks])
    g = np.array([issuer_of(k) for k in ks])
    w2, bound = _group_cap(w, np.zeros(len(w)), g, cap)
    return dict(zip(ks, w2)), bound


def net_book(w_blocks, holds, issuer_of, cap=0.10, limit=None, no_cap=False, nocap_key=None):
    """순액 한 권 — 복사: u_core.net_book. holds = [({키: 덩어리 안 비중}, 덩어리 현금 몫)] × K."""
    N, cash = {}, 0.0
    for j, (h, c) in enumerate(holds):
        cash += w_blocks[j] * c
        for k, x in h.items():
            N[k] = N.get(k, 0.0) + w_blocks[j] * x
    if nocap_key is not None:
        names = {k: v for k, v in N.items() if not nocap_key(k)}
        other = {k: v for k, v in N.items() if nocap_key(k)}
    else:
        names, other = N, {}
    capped, bound = (names, False) if no_cap else cap_book(names, issuer_of, cap=cap, limit=limit)
    return capped, other, cash, bound


DERIV_RE = re.compile(r"(?i)(futur|option|=F\b|\bMES\b|\bES1\b|\bES=|BXM|\bVIX|cboe|covered|\bput\b|_put|put_|\bcall\b|margin|overlay_fut|k_web)")
STOCK_DERIV_RE = re.compile(r"(?i)(=F\b|^/|\d{6}[CP]\d{8}|\bfutur|\boption|\bput\b|\bcall\b|\bmini\b|\bES1\b|\bMES\b)")
ALLOWED_KINDS = ("market_slot", "french_leg", "french_spread", "pit_basket", "stock", "cash")


def no_derivative_positions(positions):
    """positions = [(종류, 이름)] — 복사: u_core.no_derivative_positions(ETF 종류는 V 에 없다 — 주식 · French 다리 · 현금만)."""
    bad = []
    for kind, name in positions:
        if kind not in ALLOWED_KINDS:
            bad.append("%s:%s(종류)" % (kind, name))
            continue
        rx = STOCK_DERIV_RE if kind == "stock" else DERIV_RE
        if rx.search(str(name)) or DERIV_RE.search(str(kind)):
            bad.append("%s:%s(표식)" % (kind, name))
    return (not bad), bad


def assert_stock_book(book):
    """G-DER — 한 권의 보유 표식(종목 티커)이 모두 주식. 위반이면 멈춘다."""
    ok, bad = no_derivative_positions([("stock", k) for k in book])
    if not ok:
        raise SystemExit("🚨 파생 보유 표식(주식 중심 위반): %s" % ", ".join(bad[:5]))
    return True


# ══════════════════════════════════════════════════════════════════════════
#  능동 상한 투영(V1) · 지수 기울기 · β 띠(V2) · 크기 중립 · G-COMMON
# ══════════════════════════════════════════════════════════════════════════
def _waterfill_add(x, amt, pref, room, mask):
    """x 에 amt(> 0)를 mask 안 이름에 pref 비례로 더한다 · 이름마다 room 까지 · 남으면 room 비례로. 돌려주는 것 (x, 못 넣은 몫)."""
    x = x.copy()
    room = np.asarray(room, float).copy()
    pref = np.asarray(pref, float)
    left = float(amt)
    for use_room in (False, True):
        for _ in range(60):
            if left <= 1e-15:
                return x, 0.0
            m = mask & (room > 1e-15)
            r = np.where(m, room, 0.0)
            g = np.where(m, (r if use_room else pref), 0.0)
            g = np.where(g > 0, g, 0.0)
            gs = float(g.sum())
            if gs <= 0:
                break
            add = np.minimum(left * g / gs, r)
            x += add
            room = room - add
            left -= float(add.sum())
    return x, max(left, 0.0)


def _fix_total(x, lo, hi, total, mask):
    """mask 안 이름으로 Σx = total 로 맞춘다 — 더할 때 (x − lo) 비례(상자 hi 까지) · 뺄 때 (x − lo) 비례(lo 까지). 돌려주는 것 (x, 남은 차이)."""
    d = total - float(x.sum())
    if abs(d) <= 1e-15:
        return x, 0.0
    if d > 0:
        room = np.where(mask, np.maximum(hi - x, 0.0), 0.0)
        x2, left = _waterfill_add(x, d, np.maximum(x - lo, 0.0), room, mask)
        return x2, left
    room = np.where(mask, np.maximum(x - lo, 0.0), 0.0)
    x2, left = _waterfill_add(-x, -d, room.copy(), room.copy(), mask)
    return -x2, -left


def _feasible(x, wB, lo, hi, sec_ids, nsec, sband, ndx, ndx_max, tol=1e-10, sector_on=True):
    if abs(float(x.sum()) - 1.0) > tol or (x < lo - tol).any() or (x > hi + tol).any():
        return False
    if sector_on and nsec:
        A = np.bincount(sec_ids, weights=x - wB, minlength=nsec)
        if (np.abs(A) > sband + tol).any():
            return False
    if ndx.any() and float(x[ndx].sum()) > ndx_max + tol:
        return False
    return True


def project_active(w, wB, sector, ndx_only, cap=ISSUER_ACTIVE_CAP, sband=SECTOR_BAND, ndx_max=NDX_ONLY_MAX, sector_on=True, iters=200, tol=1e-10):
    """능동 상한 투영(V1) — w(목표 · 합 1 · ≥ 0) · w_B(중립 · NDX 전용 0) · sector(이름별 섹터 · None 은 «없음» 한 칸) · ndx_only(bool).
    돌려주는 것 (w_proj, info{iters, shrink(줄임 배수 · 1 = 줄이지 않음), feasible, cap_bound, sector_bound, ndx_bound})."""
    w = np.asarray(w, float)
    wB = np.asarray(wB, float)
    n = len(w)
    sec = ["_none" if s is None else str(s) for s in sector]
    us = sorted(set(sec))
    sec_ids = np.array([us.index(s) for s in sec], int) if n else np.zeros(0, int)
    nsec = len(us)
    ndx = np.asarray(ndx_only, bool)
    lo = np.maximum(0.0, wB - cap)
    hi = wB + cap
    hi = np.where(ndx, np.minimum(hi, ndx_max), hi)
    info = {"iters": 0, "shrink": 1.0, "feasible": True, "cap_bound": False, "sector_bound": False, "ndx_bound": False}
    if n == 0:
        return w.copy(), info
    x = np.clip(w, lo, hi)
    info["cap_bound"] = bool(np.any(np.abs(x - w) > 1e-15))
    allm = np.ones(n, bool)
    for it in range(iters):
        x, _ = _fix_total(x, lo, hi, 1.0, allm)
        if sector_on and nsec:
            A = np.bincount(sec_ids, weights=x - wB, minlength=nsec)
            over = np.flatnonzero(A > sband + tol)
            under = np.flatnonzero(A < -sband - tol)
            if len(over) or len(under):
                info["sector_bound"] = True
            for s in over:
                m = sec_ids == s
                ex = float(A[s] - sband)
                room = np.where(m, np.maximum(x - lo, 0.0), 0.0)
                y, left = _waterfill_add(-x, ex, room.copy(), room.copy(), m)
                x = -y
            for s in under:
                m = sec_ids == s
                de = float(-sband - A[s])
                room = np.where(m, np.maximum(hi - x, 0.0), 0.0)
                x, left = _waterfill_add(x, de, np.where(m, wB, 0.0) + 1e-300 * m, room, m)
            if len(over) or len(under):
                A2 = np.bincount(sec_ids, weights=x - wB, minlength=nsec)
                free_s = np.ones(nsec, bool)
                free_s[over] = False
                free_s[under] = False
                d = 1.0 - float(x.sum())
                if d > 0:
                    free_s &= A2 < sband - tol
                else:
                    free_s &= A2 > -sband + tol
                mfree = free_s[sec_ids]
                x, _ = _fix_total(x, lo, hi, 1.0, mfree)
        if ndx.any():
            N = float(x[ndx].sum())
            if N > ndx_max + tol:
                info["ndx_bound"] = True
                x[ndx] *= ndx_max / N
                x, _ = _fix_total(x, lo, hi, 1.0, ~ndx)
        info["iters"] = it + 1
        if _feasible(x, wB, lo, hi, sec_ids, nsec, sband, ndx, ndx_max, tol, sector_on):
            return x, info
    # 줄임(볼록 · w_B 는 가능) — w_B + s(x − w_B) 를 이분법으로
    xs = x / x.sum() if x.sum() > 0 else wB.copy()
    lo_s, hi_s = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo_s + hi_s)
        if _feasible(wB + mid * (xs - wB), wB, lo, hi, sec_ids, nsec, sband, ndx, ndx_max, tol, sector_on):
            lo_s = mid
        else:
            hi_s = mid
    out = wB + lo_s * (xs - wB)
    info.update(shrink=lo_s, feasible=_feasible(out, wB, lo, hi, sec_ids, nsec, sband, ndx, ndx_max, 1e-9, sector_on))
    return out, info


def exp_tilt(w, x, target, mask=None, k_max=400.0):
    """w_i(κ) ∝ w_i·exp(κ(x_i − x̄)) · mask 안 이름만(밖은 그대로 · 합은 mask 몫 보존) · Σ w(κ)x = target 인 κ 를 이분법으로.
    돌려주는 것 (w(κ), κ, 닿음 여부)."""
    w = np.asarray(w, float)
    x = np.asarray(x, float)
    m = (w > 0) if mask is None else (np.asarray(mask, bool) & (w > 0))
    if not m.any():
        return w.copy(), 0.0, False
    tot_m = float(w[m].sum())
    rest = float((w * x)[~m].sum())
    xm = x[m]
    xbar = float((w[m] * xm).sum() / tot_m)

    def f(k):
        e = w[m] * np.exp(np.clip(k * (xm - xbar), -700, 700))
        e = e / e.sum() * tot_m
        return float((e * xm).sum()) + rest, e
    lo, hi = -k_max, k_max
    flo, fhi = f(lo)[0], f(hi)[0]
    if target <= flo:
        k, hit = lo, False
    elif target >= fhi:
        k, hit = hi, False
    else:
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if f(mid)[0] < target:
                lo = mid
            else:
                hi = mid
        k, hit = 0.5 * (lo + hi), True
    out = w.copy()
    out[m] = f(k)[1]
    return out, k, hit


def beta_band(w, wB, beta, project, band_w=BETA_BAND, iters=BETA_BAND_ITERS):
    """β 띠(V2) — |β̂_책 − β̂(w_B)| ≤ band_w 가 되도록 책 안 이름에 지수 기울기 → project(w) 재적용 · 최대 iters 회 · 남은 틈 보고.
    beta 결측(NaN)은 1.0. 돌려주는 것 (w, info{gap_pre, gap, iters, ok})."""
    beta = np.where(np.isfinite(np.asarray(beta, float)), np.asarray(beta, float), 1.0)
    w = np.asarray(w, float).copy()
    bB = float(np.asarray(wB, float) @ beta)
    gap0 = float(w @ beta) - bB
    it = 0
    for it in range(1, iters + 1):
        gap = float(w @ beta) - bB
        if abs(gap) <= band_w + 1e-12:
            it -= 1
            break
        tgt = bB + math.copysign(band_w * (1.0 - 1e-3), gap)
        w, _, _ = exp_tilt(w, beta, tgt)
        w = project(w)
    gap = float(w @ beta) - bB
    return w, {"gap_pre": gap0, "gap": gap, "iters": it, "ok": abs(gap) <= band_w + 1e-9}


def size_neutral(w, wB, logme, project, iters=BETA_BAND_ITERS):
    """G-COMMON 크기 중립 — Σ a·log ME = 0(a = w − w_B) 이 되도록 책 안 이름에 지수 기울기 → project 재적용(최대 iters 회)."""
    x = np.asarray(logme, float)
    x = np.where(np.isfinite(x), x, np.nanmedian(x) if np.isfinite(x).any() else 0.0)
    w = np.asarray(w, float).copy()
    tgt = float(np.asarray(wB, float) @ x)
    for _ in range(iters):
        if abs(float(w @ x) - tgt) <= 1e-6:
            break
        w, _, _ = exp_tilt(w, x, tgt)
        w = project(w)
    return w, {"gap": float(w @ x) - tgt}


def common_share(A):
    """G-COMMON(F0 · 비중만) — A (K×N · 전략별 θ = 1 능동 벡터) → s_c = ‖평균_f a_f‖² / 평균_f ‖a_f‖². 서로 독립이면 기대값 1/K."""
    A = np.asarray(A, float)
    if A.ndim != 2 or len(A) == 0:
        return None
    den = float((A * A).sum(1).mean())
    if den <= 0:
        return None
    m = A.mean(0)
    return float(m @ m / den)


def attn_tilt(w, a, lam, gamma=GAMMA_A, oneway_max=IBL_ONEWAY_MAX):
    """EAR 책 안 ATTN 기울기 — w* ∝ w·exp(γ_A·λ·(pct_책(a_i) − ½)) · 한쪽 ½Σ|w* − w| ≤ ⅓(w 쪽 선형 되섞기) · λ ≤ 0 이면 그대로(부호 잘림).
    w · a = 같은 이름 차례 배열(a 결측 = 중앙). 돌려주는 것 (w*, 한쪽 이동)."""
    w = np.asarray(w, float)
    if lam is None or not np.isfinite(lam) or lam <= 0 or not (w > 0).any():
        return w.copy(), 0.0
    idx = np.flatnonzero(w > 0)
    pc = pct01({int(i): (None if not np.isfinite(a[i]) else float(a[i])) for i in idx})
    q = np.array([pc.get(int(i), 0.5) - 0.5 for i in idx])
    x = w.copy()
    x[idx] = w[idx] * np.exp(gamma * lam * q)
    x = x / x.sum() * w.sum()
    ow = 0.5 * float(np.abs(x - w).sum())
    if ow > oneway_max:
        x = w + (oneway_max / ow) * (x - w)
        ow = oneway_max
    return x, ow


# ══════════════════════════════════════════════════════════════════════════
#  종목 체결(V3) · 흘러감(V4) · 회전
# ══════════════════════════════════════════════════════════════════════════
def execute_book(w_drift, target, fill=FILL, band_frac=BAND_FRAC):
    """w_drift · target = {이름: 비중}. 삭제(목표 0 · 목표에 없음)는 전량 · |틈| < band_frac·목표면 무거래 · 아니면 fill·틈 · 합 1 로 비례 맞춤.
    돌려주는 것 ({이름: 비중}, 거래량 Σ|w − w̃|)."""
    names = sorted(set(w_drift) | set(target))
    out = {}
    for k in names:
        d, t = float(w_drift.get(k, 0.0)), float(target.get(k, 0.0))
        if t <= 0.0:
            x = 0.0
        else:
            g = t - d
            x = d if abs(g) < band_frac * t else d + fill * g
        if x > 0:
            out[k] = x
    s = sum(out.values())
    if s > 0:
        out = {k: v / s for k, v in out.items()}
    traded = sum(abs(out.get(k, 0.0) - float(w_drift.get(k, 0.0))) for k in names)
    return out, traded


def execute_abs(w_drift, target, fill=FILL, band_frac=BAND_FRAC):
    """execute_book 의 소매 판(합을 맞추지 않는다 · 배분기 두 소매 체결 A5) — 삭제 전량 · |틈| < band_frac·목표 무거래 · 아니면 fill·틈. {이름: 비중}."""
    out = {}
    for k in set(w_drift) | set(target):
        d, t = float(w_drift.get(k, 0.0)), float(target.get(k, 0.0))
        if t <= 0.0:
            continue
        g = t - d
        x = d if abs(g) < band_frac * t else d + fill * g
        if x > 0:
            out[k] = x
    return out


def drift_book(w, r):
    """w = {이름: 비중} · r = {이름: 보유월 수익 | None} → (흘러간 {이름: 비중}, 책 수익 R, 결측 이름 수). 결측은 V4."""
    if not w:
        return {}, None, 0
    known = {k: r.get(k) for k in w if r.get(k) is not None and np.isfinite(r.get(k))}
    wk = sum(w[k] for k in known)
    if wk <= 0:
        return dict(w), None, len(w)
    R = sum(w[k] * known[k] for k in known) / wk
    g = {k: w[k] * (1.0 + (known[k] if k in known else R)) for k in w}
    tot = sum(g.values())
    return ({k: v / tot for k, v in g.items()} if tot > 0 else dict(w)), float(R), len(w) - len(known)


def book_ret(w, r):
    """책 한 달 수익(알려진 이름끼리 비례 맞춤 · V4)."""
    return drift_book(w, r)[1]


def tau_weights_only(books):
    """비중만 회전(F0) — 이어지는 목표 책 사이 ½Σ|w_t − w_{t−1}| 의 달 평균 × 12(흘러감 없음 · 수익 없음)."""
    vals = []
    prev = None
    for b in books:
        if b is None:
            prev = None
            continue
        if prev is not None:
            ks = set(b) | set(prev)
            vals.append(0.5 * sum(abs(b.get(k, 0.0) - prev.get(k, 0.0)) for k in ks))
        prev = b
    return 12.0 * float(np.mean(vals)) if vals else None


def turnover_annual(traded, n_months=None):
    """편도 연 회전 = ½Σ(거래량) / 해(t_core turnover_1w 의 자금 다리 식)."""
    t = [x for x in traded if x is not None and np.isfinite(x)]
    n = len(t) if n_months is None else n_months
    return (0.5 * float(np.sum(t)) / (n / 12.0)) if n else None


# ══════════════════════════════════════════════════════════════════════════
#  비용 — S 10bp · LIQ 상태 의존(V8) · L COST_ERAS(복사: t_core.cost_rate)
# ══════════════════════════════════════════════════════════════════════════
def cost_rate_L(idx):
    idx = pd.PeriodIndex(idx, freq="M")
    out = np.empty(len(idx))
    ends = [pd.Period(e, "M") for e, _ in COST_ERAS]
    rates = [r for _, r in COST_ERAS]
    for j, p in enumerate(idx):
        for e, r in zip(ends, rates):
            if p <= e:
                out[j] = r
                break
    return out


def liq_cost_rate(spy_px, dates, base=S_COST, n=LIQ_SIG_N):
    """LIQ 상태 의존 편도 비율(V8) — {결정 달: 비율}. spy_px = 격자 SPY 총수익 지수 배열 · dates = 격자 날짜."""
    p = np.asarray(spy_px, float)
    r = np.full(len(p), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r[1:] = p[1:] / p[:-1] - 1.0
    sd = pd.Series(r).rolling(n, min_periods=n).std(ddof=1).to_numpy()
    last = {}
    for i, d in enumerate(dates):
        last[d[:7]] = i
    out, hist = {}, []
    for m in sorted(last):
        s = sd[last[m]]
        if np.isfinite(s):
            hist.append(float(s))
            med = float(np.median(hist))
            out[m] = base * max(1.0, s / med) if med > 0 else base
        else:
            out[m] = base
    return out


def fund_x(S, B, rate, traded=None, fixed=None, mult=1.0):
    """펀드 틀(명세 tests.fund_frame) — 복사: u_tests.fund_x. 보유 달 계열 → X = F − B. S(슬리브 총수익) · B(벤치 총수익) · rate(편도 비율) ·
    traded(Σ|거래| · 슬리브 몫) · fixed(달마다 슬리브 비용 소수 · 내부 τ 등). 슬리브 순수익 S − c_s · F_gross = 0.9B + 0.1(S − c_s) ·
    월말 되돌림 c_f = 비율 × 2 × |0.1(1 + S − c_s)/(1 + F_gross) − 0.1| × (1 + F_gross). 🚨 수익 계열 — 굽기 · 눈가린 연기에서만 부른다."""
    S = pd.Series(S, dtype=float)
    idx = S.index
    Bv = pd.Series(B, dtype=float).reindex(idx)
    r = pd.Series(rate, dtype=float).reindex(idx) * mult if not np.isscalar(rate) else pd.Series(float(rate) * mult, index=idx)
    tr = pd.Series(0.0, index=idx) if traded is None else pd.Series(traded, dtype=float).reindex(idx).fillna(0.0)
    fx = pd.Series(0.0, index=idx) if fixed is None else pd.Series(fixed, dtype=float).reindex(idx).fillna(0.0) * mult
    cs = r * tr + fx
    Sn = S - cs
    Fg = (1 - SLEEVE) * Bv + SLEEVE * Sn
    share = SLEEVE * (1.0 + Sn) / (1.0 + Fg)
    cf = r * 2.0 * (share - SLEEVE).abs() * (1.0 + Fg)
    return (Fg - cf) - Bv


# ══════════════════════════════════════════════════════════════════════════
#  L 층 다리 팔(V9 · 복사: t_core _turn_arrays · arm_weights · cost · turnover_1w — 선물 다리 없음)
# ══════════════════════════════════════════════════════════════════════════
def _turn_arrays(Wm, R0, valid):
    n = Wm.shape[0]
    tf = np.zeros(n)
    if n < 2:
        return tf
    Wp, Rp = Wm[:-1], R0[:-1]
    g = Wp * (1.0 + Rp)
    tot = g.sum(1, keepdims=True)
    base = Wp.sum(1, keepdims=True)
    dr = np.where(np.abs(tot) > 1e-15, g / np.where(np.abs(tot) > 1e-15, tot, 1.0) * base, Wp)
    d = np.abs(Wm[1:] - dr)
    tf[1:] = d.sum(1)
    ok = valid[1:] & valid[:-1]
    tf[1:] = np.where(ok, tf[1:], 0.0)
    tf[0] = 0.0
    return tf


def arm_legs(W, R, rate, tau=None, mult=1.0):
    """W(보유 달 × 다리 비중 · 결정은 전달 말) · R(같은 색인 · 다리 수익) · rate(보유 달 편도 비율) · tau = {다리: 내부 편도 연 회전}.
    돌려주는 것 dict(S(슬리브 총수익) · tf(Σ|Δw|) · cost(편도 비율 × tf + 내부 τ) · turn_1w · valid)."""
    W = pd.DataFrame(W, dtype=float)
    idx = W.index
    cols = list(W.columns)
    Rr = pd.DataFrame(R).reindex(index=idx, columns=cols).astype(float)
    Wm, Rm = W.to_numpy(float), Rr.to_numpy(float)
    need = np.abs(np.nan_to_num(Wm)) > 0
    valid = ~np.isnan(Wm).any(1) & ~(need & np.isnan(Rm)).any(1)
    Wm0 = np.nan_to_num(Wm)
    R0 = np.where(need, np.nan_to_num(Rm), 0.0)
    S = np.where(valid, (Wm0 * R0).sum(1), np.nan)
    tf = _turn_arrays(Wm0, R0, valid)
    rate = np.asarray(rate, float) * mult
    c_int = np.zeros(len(idx))
    tr_int = 0.0
    if tau:
        for leg, t_ in tau.items():
            if leg in cols and t_ is not None:
                j = cols.index(leg)
                c_int = c_int + rate * 2.0 * float(t_) / 12.0 * np.abs(Wm0[:, j])
                tr_int += float(t_) * float(np.abs(Wm0[valid, j]).mean()) if valid.any() else 0.0
    c = rate * tf + c_int
    nv = int(valid.sum())
    turn = ((0.5 * tf[valid].sum()) / (nv / 12.0) + tr_int) if nv else None
    return {"S": pd.Series(S, index=idx), "tf": pd.Series(tf, index=idx), "cost": pd.Series(np.where(valid, c, np.nan), index=idx),
            "fixed": pd.Series(np.where(valid, c_int, np.nan), index=idx), "rate": pd.Series(rate, index=idx),
            "turn_1w": turn, "valid": pd.Series(valid, index=idx)}


# ══════════════════════════════════════════════════════════════════════════
#  합성 책(복사: u_core._draw_book 틀) · ATTN γ 보정
# ══════════════════════════════════════════════════════════════════════════
def _draw_book(rng, N=30, cap=0.20, logcap_sd=1.2):
    lc = rng.standard_normal(N)
    c = np.exp(logcap_sd * lc)
    w = c / c.sum()
    for _ in range(200):
        over = w > cap + 1e-12
        if not over.any():
            break
        ex = (w[over] - cap).sum()
        w[over] = cap
        free = w < cap - 1e-12
        w[free] += ex * w[free] / w[free].sum()
    a = rng.standard_normal(N)
    q = a.argsort().argsort() / (N - 1) - 0.5
    return w, q


def attn_oneway_median(gamma, seed=20260926, n=1500, N=100, lam=0.5, kind="mixed", p=None):
    """합성 보정 — N 100 책 · λ = ½ · 한쪽 상한 없이 ½Σ|w* − w| 의 중앙값(u_core _st_calibration 틀).
    kind="mixed"(주 · 명세 정의 a = ½·Bernoulli(p) + ½·pct(연속 표본) · q = pct_책(a) − ½ 평균 순위 — attn_tilt 와 같은 식) |
    "binary"(금요일 단독 a ~ Bernoulli(p) · 보고) | "continuous"(옛 u_core 틀 · 보고)."""
    rng = np.random.default_rng(seed)
    p = ATTN_FRIDAY_P if p is None else p
    ows = []
    for _ in range(n):
        w, q = _draw_book(rng, N=N)
        if kind in ("binary", "mixed"):
            a = (rng.random(N) < p).astype(float)
            if kind == "mixed":
                u = rng.standard_normal(N)
                pu = pct01({i: float(u[i]) for i in range(N)})
                a = 0.5 * a + 0.5 * np.array([pu[i] for i in range(N)])
            pc = pct01({i: float(a[i]) for i in range(N)})
            q = np.array([pc[i] - 0.5 for i in range(N)])
        x = w * np.exp(gamma * lam * q)
        x /= x.sum()
        ows.append(0.5 * float(np.abs(x - w).sum()))
    return float(np.median(ows))


# ══════════════════════════════════════════════════════════════════════════
#  합성 자료 시험 — 실자료 · 캐시 · 저장소 자료를 읽지 않는다
# ══════════════════════════════════════════════════════════════════════════
def _close(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol


def _pairs_by_hand(z, y, t, lag=2, sig_n=WLS_N, sig_min=WLS_MIN):
    T = len(z)
    rows = []
    for s in range(0, t - lag):
        if not (np.isfinite(z[s]) and s + 1 < T and np.isfinite(y[s + 1]) and np.isfinite(z[s + 1])):
            continue
        e = s - lag
        if e < 0:
            continue
        w = y[max(0, e - sig_n + 1):e + 1]
        w = w[np.isfinite(w)]
        if len(w) < sig_min:
            continue
        sg = np.std(w, ddof=1)
        if not sg > 0:
            continue
        rows.append((z[s], y[s + 1] / sg, z[s + 1]))
    return np.array(rows)


def _nw_by_hand(X, u, L):
    n = len(u)
    S = np.zeros((X.shape[1], X.shape[1]))
    for l in range(0, L + 1):
        G = np.zeros_like(S)
        for s in range(l, n):
            G += np.outer(X[s] * u[s], X[s - l] * u[s - l])
        S += G if l == 0 else (1 - l / (L + 1.0)) * (G + G.T)
    inv = np.linalg.inv(X.T @ X)
    return math.sqrt((inv @ S @ inv)[1, 1])


def _nw_mean_by_hand(c, L):
    """달력 지연 NW 평균 se(쌍 = 두 달 모두 유효) — 손 계산."""
    idx = [i for i in range(len(c)) if np.isfinite(c[i])]
    n = len(idx)
    mu = float(np.mean([c[i] for i in idx]))
    e = {i: c[i] - mu for i in idx}
    tot = sum(v * v for v in e.values())
    for l in range(1, L + 1):
        g = sum(e[i] * e[i - l] for i in idx if (i - l) in e)
        tot += 2 * (1 - l / (L + 1.0)) * g
    return n, mu, math.sqrt(max(tot, 0.0)) / n


def _st_slopes():
    rng = np.random.default_rng(1)
    T = 420
    z = np.full(T, np.nan)
    z[10:] = np.clip(np.cumsum(rng.normal(0, 0.3, T - 10)) * 0.2 + rng.normal(0, 1, T - 10), -2, 2)
    y = np.full(T, np.nan)
    y[5:] = rng.normal(0, 0.04, T - 5)
    y[6:] += 0.004 * z[5:-1] * np.isfinite(z[5:-1])
    y = np.where(np.isfinite(y), y, np.nan)
    out = slope_path(z, y, +1, detail=True)
    for t in (200, 300, 419):
        P = _pairs_by_hand(z, y, t)
        assert out["n"][t] == len(P)
        X = np.column_stack([np.ones(len(P)), P[:, 0]])
        coef = np.linalg.lstsq(X, P[:, 1], rcond=None)[0]
        assert _close(out["b_hat"][t], coef[1], 1e-10)
        u = P[:, 1] - X @ coef
        ca = np.linalg.lstsq(X, P[:, 2], rcond=None)[0]
        v = P[:, 2] - X @ ca
        corr = (u @ v) / (v @ v) * (1 + 3 * ca[1]) / len(P)
        assert _close(out["b_corr"][t], coef[1] + corr, 1e-10)
        se = _nw_by_hand(X, u, 6)
        assert _close(out["se"][t], se, 1e-9)
        bs = (coef[1] + corr) * RHO / (RHO + se * se)
        assert _close(out["b_c"][t], max(0.0, bs), 1e-11)
    t = 300
    y2 = y.copy()
    y2[t - 1:] = rng.normal(0, 1, T - t + 1)
    assert _close(slope_path(z, y2, +1)["b_c"][t], out["b_c"][t], 1e-14)          # t−1 뒤 목표는 쓰지 않는다
    k = int(np.flatnonzero(out["n"] >= 120)[0])
    assert out["ok"][k] and not out["ok"][k - 1]
    o17 = slope_path(z, y, +1, min_pairs=PAIRS_MIN_BSPRD, nw_lag=NW_SLOPE_BSPRD)
    assert o17["n"][int(np.flatnonzero(o17["ok"])[0])] == 240
    # 상수 조건 판(ATTN) · FM 평균 — 손 계산
    mp = mean_path(y, +1)
    sig = _wls_scale(y)
    yt = np.full(T, np.nan)
    yt[:-1] = y[1:] / sig[:-1]
    for t in (250, 419):
        n_, mu, se = _nw_mean_by_hand(yt[:t - 2], 6)
        assert mp["n"][t] == n_ and _close(mp["b_hat"][t], mu, 1e-12) and _close(mp["se"][t], se, 1e-12)
        bs = mu * RHO / (RHO + se * se)
        assert _close(mp["b_c"][t], max(0.0, bs), 1e-13) and _close(mp["u"][t], max(0.0, bs) / se, 1e-10)
    neg = mean_path(-np.abs(y) - 0.01, +1)
    assert np.nanmax(neg["b_c"]) == 0.0 and np.nanmax(neg["u"]) == 0.0                   # ATTN 부호 잘림(음이면 0)
    return "E2 기울기 손 OLS · Stambaugh · NW(6)/(12) · 축소 · 잘림 · 쌍 120/240 · 늦춤 · 상수 조건(ATTN) 평균 · NW · 부호 잘림"


def _st_r2_clusters():
    one = np.ones((1, 3), bool)
    Z = np.array([[1.5, 1.2, 1.0]])
    B = np.array([[0.05, 0.05, 0.05]])
    Rm = np.eye(3)[None]
    # 상관된 가닥 셋 = 한 군 → 활성 군 1 → v = band(u)/2
    r = direction_eval(Z, B, one, [1, 1, 1], ["a", "b", "c"], [0, 0, 0], R=Rm)
    assert r["n_clusters_act"][0] == 1 and _close(r["v"][0], 0.5 * band(r["u"])[0], 1e-15) and r["v"][0] > 0
    # 가닥 수로 셌다면 3 ≥ 2 라 전 강도 — 옛 결함 재현: 군 R2 는 절반
    assert r["n_act"][0] == 3 and _close(r["v_raw"][0], band(r["u"])[0], 1e-15)
    r2 = direction_eval(Z, B, one, [1, 1, 1], ["a", "b", "c"], [0, 1, 1], R=Rm)          # 두 군 · 둘 다 같은 쪽
    assert r2["n_clusters_act"][0] == 2 and r2["n_clusters_same"][0] == 2 and _close(r2["v"][0], band(r2["u"])[0], 1e-15)
    r3 = direction_eval(np.array([[2.0, 2.0, -1.0]]), B, one, [1, 1, 1], ["a", "b", "c"], [0, 0, 1], R=Rm)   # 두 군 · 한 군 반대
    assert r3["n_clusters_act"][0] == 2 and r3["n_clusters_same"][0] == 1 and r3["v"][0] == 0.0
    rs = direction_eval(Z, B, one, [1, 1, 1], ["a", "b", "c"], [0, 0, 0], R=Rm, r2="strict")
    assert rs["v"][0] == 0.0
    ro = direction_eval(np.array([[2.0, 2.0, -1.0]]), B, one, [1, 1, 1], ["a", "b", "c"], [0, 0, 1], R=Rm, r2="off")
    assert ro["v"][0] > 0 and _close(ro["v"][0], band(ro["u"])[0], 1e-15)
    r0 = direction_eval(Z, B, np.zeros((1, 3), bool), [1, 1, 1], ["a", "b", "c"], [0, 1, 2], R=Rm)
    assert r0["v"][0] == 0.0 and r0["n_clusters_act"][0] == 0
    # 잘린 가닥(b^c = 0)은 활성 군도 같은 쪽 군도 아니다(증거 없음) — 군 셋 중 둘이 잘리면 활성 군 1 → 절반 강도
    rt = direction_eval(np.array([[2.0, 2.0, 2.0]]), np.array([[0.05, 0.0, 0.0]]), one, [1, 1, 1], ["a", "b", "c"], [0, 1, 2], R=Rm)
    assert rt["n_clusters_act"][0] == 1 and rt["n_clusters_same"][0] == 1 and rt["v"][0] > 0 and _close(rt["v"][0], 0.5 * band(rt["u"])[0], 1e-15)
    # 단조성 — 잘린 가닥을 더해도 v 가 0 으로 떨어지지 않는다(두 군 · 하나 잘림 = 그 가닥이 없는 웹과 같은 절반 강도)
    r1 = direction_eval(np.array([[2.0]]), np.array([[0.05]]), np.ones((1, 1), bool), [1], ["a"], [0], R=np.eye(1)[None])
    r12 = direction_eval(np.array([[2.0, 2.0]]), np.array([[0.05, 0.0]]), np.ones((1, 2), bool), [1, 1], ["a", "b"], [0, 1], R=np.eye(2)[None])
    assert r1["v"][0] > 0 and r12["v"][0] > 0 and r12["n_clusters_act"][0] == 1
    # stale(z = 0) 가닥도 같다
    rz = direction_eval(np.array([[2.0, 0.0]]), np.array([[0.05, 0.05]]), np.ones((1, 2), bool), [1, 1], ["a", "b"], [0, 1], R=np.eye(2)[None])
    assert rz["n_clusters_act"][0] == 1 and rz["v"][0] > 0
    # 가족 균형 π(가족 둘 · 한 가족 가닥 둘)
    pi = direction_eval(Z, B, one, [1, 1, 1], ["a", "a", "b"], [0, 0, 1], R=Rm)["pi"][0]
    assert np.allclose(pi, [0.25, 0.25, 0.5])
    # 띠 · θ 경로
    assert np.allclose(band([0.5, -0.5, 1.25, -1.25, 2.0, 3.0, -9.0, 0.0]), [0, 0, 0.5, -0.5, 1, 1, -1, 0])
    th = theta_path([1, 1, 1, -1, 0, np.nan], 0.75, 0.25)
    assert np.allclose(th, [0.85, 0.95, 1.0, 0.9, 0.8, 0.75])
    th0 = theta_path(np.zeros(50), THETA0, DTHETA)
    assert np.all(th0 == THETA0)
    return "군 R2: 상관 셋 = 한 군(절반 강도 · 옛 가닥 셈은 전 강도) · 두 군 같은 쪽 → 전 강도 · 반대 → 0 · 엄격 · 끔 · 비활성 · 잘린 · stale 가닥 = 증거 없음(단조) · 가족 π · 띠 · θ 경로(|Δθ| ≤ 0.10 · v ≡ 0 → θ0)"


def _book(rng, n=60, n_ndx=6, top=(0.12, 0.08, 0.06)):
    me = np.exp(rng.normal(0, 1.2, n))
    me[:len(top)] = 0
    wB = me / me.sum() * (1 - sum(top))
    wB[:len(top)] = top
    ndx = np.zeros(n, bool)
    ndx[-n_ndx:] = True
    wB[ndx] = 0.0
    wB = wB / wB.sum()
    sec = ["S%d" % (j % 5) for j in range(n)]
    return wB, sec, ndx


def _st_project():
    rng = np.random.default_rng(3)
    wB, sec, ndx = _book(rng)
    n = len(wB)
    # 선정: 1 · 2 번 메가캡 빼고 작은 이름 · NDX 전용 여럿
    sel = np.zeros(n, bool)
    sel[1] = True
    sel[10:30] = True
    sel[-4:] = True
    me = np.where(sel, np.exp(rng.normal(0, 1, n)), 0.0)
    me[1] = 40.0
    wf = me / me.sum()
    w, info = project_active(wf, wB, sec, ndx)
    sid = np.array([int(s[1:]) for s in sec])
    A = np.bincount(sid, weights=w - wB)
    assert abs(w.sum() - 1) < 1e-10 and (w >= -1e-12).all() and (np.abs(w - wB) <= 0.05 + 1e-10).all()
    assert (np.abs(A) <= 0.10 + 1e-10).all() and w[ndx].sum() <= 0.10 + 1e-10, (A, w[ndx].sum())
    assert _close(w[0], wB[0] - 0.05, 1e-10) and _close(w[2], wB[2] - 0.05, 1e-10)          # 선정 안 된 메가캡 = w_B − 0.05(능동 하한)
    assert _close(w[1], wB[1] + 0.05, 1e-10)                                                # 선정 메가캡은 +0.05 상한
    # 이미 가능한 목표는 그대로
    feas = wB + 0.5 * (w - wB)
    w2, i2 = project_active(feas, wB, sec, ndx)
    assert np.allclose(w2, feas, atol=1e-14) and i2["iters"] == 1 and i2["shrink"] == 1.0
    # 섹터 띠 0.05(LBS) · NDX 끔
    w3, _ = project_active(wf, wB, sec, ndx, sband=0.05)
    assert (np.abs(np.bincount(sid, weights=w3 - wB)) <= 0.05 + 1e-10).all()
    # θ 혼합은 가능성을 지킨다(볼록)
    for th in (0.2, 0.75, 1.0):
        x = wB + th * (w - wB)
        _, i4 = project_active(x, wB, sec, ndx)
        assert i4["iters"] == 1
    # β 띠 — 저베타 쪽 책을 띠 안으로
    beta = np.where(sel, 0.6, 1.2) + rng.normal(0, 0.05, n)
    beta[5] = np.nan
    proj = lambda x: project_active(x, wB, sec, ndx)[0]
    wb_, bi = beta_band(w, wB, beta, proj)
    bb = np.where(np.isfinite(beta), beta, 1.0)
    assert bi["ok"] and abs(wb_ @ bb - wB @ bb) <= 0.03 + 1e-9 and abs(bi["gap_pre"]) > 0.03, bi
    assert abs(wb_.sum() - 1) < 1e-10 and (np.abs(wb_ - wB) <= 0.05 + 1e-10).all() and (np.abs(np.bincount(sid, weights=wb_ - wB)) <= 0.1 + 1e-10).all()
    assert wb_[ndx].sum() <= 0.1 + 1e-10
    # 이미 띠 안이면 그대로
    w_in = wB + 0.1 * (w - wB)
    same, si = beta_band(w_in, wB, beta, proj)
    if abs(w_in @ bb - wB @ bb) <= 0.03:
        assert np.allclose(same, w_in) and si["iters"] == 0
    # 지수 기울기 손 확인 · 크기 중립
    t_, k_, hit = exp_tilt(np.array([0.5, 0.5]), np.array([0.0, 1.0]), 0.7)
    assert hit and _close(t_ @ np.array([0.0, 1.0]), 0.7, 1e-10) and _close(t_[1] / t_[0], math.exp(k_), 1e-9)
    lme = np.log(np.maximum(wB, 1e-6) * 1e6)
    ws, sinfo = size_neutral(w, wB, lme, proj)
    assert abs(sinfo["gap"]) < 1e-4
    # G-COMMON
    a1 = np.array([1.0, -1.0, 0.0, 0.0])
    assert _close(common_share(np.vstack([a1, a1])), 1.0) and _close(common_share(np.vstack([a1, -a1])), 0.0)
    assert _close(common_share(np.eye(4) - 0.25), 0.0)
    rng2 = np.random.default_rng(9)
    sc = [common_share(rng2.normal(0, 1, (5, 400))) for _ in range(200)]
    assert abs(np.mean(sc) - 0.2) < 0.01                                                    # 독립 → 1/K
    return "능동 상한 투영(발행사 ±5%p · 섹터 ±10/5%p · NDX 전용 ≤ 10% · 합 1 · 선정 안 된 메가캡 w_B − 0.05) · 가능 목표 불변 · θ 볼록 · β 띠(결측 β 1 · 상한 · 띠 동시) · 지수 기울기 · 크기 중립 · G-COMMON(1/K)"


def _st_exec():
    d = {"A": 0.30, "B": 0.30, "C": 0.40}
    t = {"A": 0.31, "B": 0.49, "D": 0.20}
    w, tr = execute_book(d, t, fill=0.5)
    raw = {"A": 0.30, "B": 0.30 + 0.5 * 0.19, "D": 0.10}                                    # A: |0.01| < 0.1·0.31 무거래 · C 삭제 전량 · D ½
    s = sum(raw.values())
    want = {k: v / s for k, v in raw.items()}
    assert set(w) == set(want) and all(_close(w[k], want[k], 1e-15) for k in want)
    assert _close(tr, sum(abs(w.get(k, 0) - d.get(k, 0)) for k in set(w) | set(d)), 1e-15)
    wl, _ = execute_book(d, t, fill=1.0)                                                    # LIQ 전량 체결
    assert _close(wl["B"], 0.49 / (0.30 + 0.49 + 0.20), 1e-15) and "C" not in wl
    dr, R, nm = drift_book({"A": 0.5, "B": 0.3, "C": 0.2}, {"A": 0.1, "B": -0.1, "C": None})
    Rk = (0.5 * 0.1 + 0.3 * -0.1) / 0.8
    assert _close(R, Rk, 1e-15) and nm == 1
    g = {"A": 0.5 * 1.1, "B": 0.3 * 0.9, "C": 0.2 * (1 + Rk)}
    assert all(_close(dr[k], g[k] / sum(g.values()), 1e-15) for k in g)
    assert _close(tau_weights_only([{"A": 1.0}, {"A": 0.5, "B": 0.5}, None, {"B": 1.0}]), 12 * 0.5, 1e-15)
    assert _close(turnover_annual([0.2] * 12), 1.2, 1e-15)
    # 배분 체결(복사) — 상자 · Σ = 0 · 틈 ½ · 무거래 · 속도 상한
    w0 = np.full(5, 0.2)
    tg, dw = alloc_target(np.array([1.0, 0.5, 0.0, -0.5, -1.0]), w0)
    assert _close(dw.sum(), 0.0, 1e-15) and (np.abs(dw) <= 0.1 + 1e-15).all() and (tg >= 0.1 - 1e-15).all()
    assert np.allclose(dw, 0.05 * np.array([1.0, 0.5, 0.0, -0.5, -1.0]))
    ex, trd = execute_a(w0, tg, w0)
    assert np.allclose(ex, w0 + 0.5 * dw) and _close(trd, 0.5 * np.abs(dw).sum(), 1e-15)
    tg0, dw0 = alloc_target(np.zeros(5), w0)
    assert np.all(dw0 == 0) and np.all(tg0 == w0)                                            # 배분기 v ≡ 0 → C0(1/K)
    P = a_path(np.tile(tg0, (4, 1)), np.full((4, 5), 0.01), w0)
    assert np.allclose(P["w"][1:], w0)
    return "종목 체결(½ · 무거래 0.1·목표 · 삭제 전량 · 합 1) · LIQ 전량 · 흘러감(결측 = 책 수익) · 비중만 회전 · 편도 연 회전 · 배분 목표(¼w0 · 상자 ½w0 · Σ 0) · 체결 · v ≡ 0 → 1/K"


def _st_fm():
    rng = np.random.default_rng(11)
    T, K = 360, 5
    Rm = rng.standard_normal((T, K))
    Rm[:40, 3:] = np.nan                                                                    # 앞 40달은 K = 3
    Y = np.full((T, K), np.nan)
    Y[1:] = 0.02 * rng.standard_normal((T - 1, K)) + 0.004 * np.nan_to_num(Rm[:-1])
    o = fm_slope_path(Rm, Y)
    c, ks = o["c"], o["K"]
    sig = np.column_stack([_wls_scale(Y[:, f]) for f in range(K)])
    for s in (60, 200):
        m = np.isfinite(Rm[s]) & np.isfinite(Y[s + 1] / sig[s])
        x, yy = Rm[s, m], (Y[s + 1] / sig[s])[m]
        cc = np.polyfit(x, yy, 1)[0]
        assert _close(c[s], cc, 1e-10)
    for t in (180, 359):
        n_, mu, se = _nw_mean_by_hand(c[:t - 2], 6)
        assert o["n"][t] == n_ and _close(o["b_hat"][t], mu, 1e-12) and _close(o["se"][t], se, 1e-12)
        assert _close(o["b_c"][t], max(0.0, mu * RHO / (RHO + se * se)), 1e-13)
    # 합성 회복 — 참 기울기 +(WLS 척도 ≈ 0.004/0.02 = 0.2) · 사후 평균은 0 쪽으로 줄되 양수
    assert 0.1 < o["b_hat"][-1] < 0.3 and 0 < o["b_c"][-1] <= o["b_hat"][-1]
    Yn = np.full((T, K), np.nan)
    Yn[1:] = 0.02 * rng.standard_normal((T - 1, K)) - 0.004 * np.nan_to_num(Rm[:-1])
    assert fm_slope_path(Rm, Yn)["b_c"][-1] == 0.0                                          # 부호 잘림(≥ 0)
    v, u = alloc_v(np.array([0.2, 0.01]), np.array([[1.5, -1.5, 0.0], [2.0, 0.0, -2.0]]))
    assert np.allclose(u[0], [1.5, -1.5, 0.0]) and np.allclose(u[1], np.array([2.0, 0.0, -2.0]) * 0.01 / 0.05)
    assert np.allclose(v[0], band([1.5, -1.5, 0.0]))
    return "FM 배분기: 달마다 절편 있는 단면 OLS(손 polyfit) · s ≤ t−3 평균 · NW(6) 손 계산 · 사후 평균 · 부호 잘림 · 합성 기울기 회복 · u = b^c r/max(b^c, √ρ)"


def _st_costs():
    idx = pd.PeriodIndex(["1975-04", "1975-05", "2000-12", "2001-01"], freq="M")
    assert np.allclose(cost_rate_L(idx), [0.005, 0.002, 0.002, 0.001])
    days = pd.bdate_range("2015-01-01", "2016-12-31")
    dates = [d.strftime("%Y-%m-%d") for d in days]
    rng = np.random.default_rng(2)
    r = rng.normal(0, 0.01, len(dates))
    r[300:320] *= 4
    px = 100 * np.cumprod(1 + r)
    lc = liq_cost_rate(px, dates)
    assert min(lc.values()) >= S_COST - 1e-15 and max(lc.values()) > 2 * S_COST
    # L 다리 팔 — 손 계산(두 다리 · 흘러감 대비 Σ|Δw| · 내부 τ)
    ix = pd.period_range("2001-01", periods=3, freq="M")
    W = pd.DataFrame({"Mkt": [0.25, 0.25, 0.1], "P": [0.75, 0.75, 0.9]}, index=ix)
    R = pd.DataFrame({"Mkt": [0.01, 0.02, 0.0], "P": [0.03, -0.01, 0.0]}, index=ix)
    a = arm_legs(W, R, cost_rate_L(ix), tau={"P": 2.0})
    g = np.array([0.25 * 1.01, 0.75 * 1.03])
    dr = g / g.sum()
    tf1 = abs(0.25 - dr[0]) + abs(0.75 - dr[1])
    assert _close(a["tf"].iloc[1], tf1, 1e-15) and a["tf"].iloc[0] == 0.0
    assert _close(a["cost"].iloc[1], 0.001 * tf1 + 0.001 * 2 * 2.0 / 12 * 0.75, 1e-15)
    assert _close(a["S"].iloc[0], 0.25 * 0.01 + 0.75 * 0.03, 1e-15)
    return "COST_ERAS(1975-04 · 2000-12 경계) · LIQ 상태 의존(≥ 10bp · 변동성 급등에 오름) · L 다리 팔(흘러감 대비 Σ|Δw| · 내부 τ 2/12 · 슬리브 수익) 손 계산"


def _st_calibration():
    med = attn_oneway_median(GAMMA_A)                                                       # 명세 정의 ½·금 + ½·같은 날 수 백분위(주 판)
    assert abs(med - 1.0 / 6.0) <= 0.01, med
    med_c = attn_oneway_median(GAMMA_A, kind="binary")                                     # 금요일 단독(보고) — 같은 γ 면 덜 움직인다
    w = np.array([0.4, 0.3, 0.2, 0.1])
    a = np.array([1.0, 0.0, np.nan, 1.0])
    x, ow = attn_tilt(w, a, 0.5)
    assert ow > 0 and x[0] / w[0] > x[1] / w[1] and _close(x.sum(), 1.0, 1e-15)
    x0, ow0 = attn_tilt(w, a, 0.0)
    assert np.all(x0 == w) and ow0 == 0.0                                                   # λ = 0(부호 잘림) → 그대로
    xb, owb = attn_tilt(w, np.array([1.0, 0.0, 0.0, 1.0]), 0.5, gamma=60.0)
    assert _close(owb, IBL_ONEWAY_MAX, 1e-15) and _close(0.5 * np.abs(xb - w).sum(), IBL_ONEWAY_MAX, 1e-12)
    return ("ATTN γ_A %.2f 합성 보정(½·금요일 p %.3f + ½·같은 날 수 백분위 · N 100 · λ ½ · 한쪽 중앙 %.4f = ⅙ ± 0.01 · 금요일 단독 특성이면 %.4f) · "
            "λ = 0 이면 불변 · 한쪽 ≤ ⅓" % (GAMMA_A, ATTN_FRIDAY_P, med, med_c))


def _st_g8():
    ok, bad = no_derivative_positions([("market_slot", "French Mkt"), ("french_leg", "me_prior12:BIG HiPRIOR"), ("stock", "AAPL"), ("cash", "RF"),
                                       ("stock", "BRK-B"), ("stock", "CBOE")])
    assert ok and not bad
    for p in (("futures", "ES"), ("stock", "ES=F"), ("etf_equity", "XYLD"), ("stock", "SPX 4500 put"), ("option", "SPY"),
              ("stock", "SPY251219C00600000"), ("stock", "/ES")):
        assert not no_derivative_positions([p])[0], p
    try:
        assert_stock_book({"AAPL": 0.5, "ES=F": 0.5})
        raise AssertionError("파생 표식 통과")
    except SystemExit:
        pass
    return "G-DER: 주식 · French 다리 · 현금만 · 선물 · 옵션 · ETF 종류 멈춤"


def open_violations(src):
    import ast
    bad = []
    for nd in ast.walk(ast.parse(src)):
        if not isinstance(nd, ast.Call):
            continue
        f = nd.func
        is_open = (isinstance(f, ast.Name) and f.id == "open") or (isinstance(f, ast.Attribute) and f.attr == "open"
                                                                   and isinstance(f.value, ast.Name) and f.value.id == "io")
        if not is_open:
            continue
        mode = nd.args[1].value if len(nd.args) > 1 and isinstance(nd.args[1], ast.Constant) else ""
        if "b" in str(mode):
            continue
        if not any(kw.arg == "encoding" and isinstance(kw.value, ast.Constant) and kw.value.value == "utf-8" for kw in nd.keywords):
            bad.append(nd.lineno)
    return bad


def _st_static():
    for fn in ("v_core.py", "v_cards.py", "v_alloc.py", "v_tests.py", "v_cmp.py"):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            with io.open(p, encoding="utf-8") as f:
                assert not open_violations(f.read()), fn
    planted = "\n".join(["x = open('a')", "y = io.open('b', 'rb')", "z = io.open('c', encoding='utf-8')"])
    assert open_violations(planted) == [1]
    return "엔진 v_*.py 의 모든 텍스트 open() 에 encoding='utf-8'"


def selftest():
    res, ok = [], True
    for fn in (_st_slopes, _st_r2_clusters, _st_project, _st_exec, _st_fm, _st_costs, _st_calibration, _st_g8, _st_static):
        t0 = time.time()
        try:
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                res.append(("통과", fn.__name__, fn(), round(time.time() - t0, 1)))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-2000:], round(time.time() - t0, 1)))
    for st, nm, msg, sec in res:
        print("  %s %-16s %5ss  %s" % ("✓" if st == "통과" else "✗", nm, sec, msg))
    print("v_core selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
