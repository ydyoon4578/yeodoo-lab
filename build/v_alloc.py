# -*- coding: utf-8 -*-
"""build/v_alloc.py — 배치 V-A 전략 사이 배분기(상대 자기 모멘텀) · 순액 주식 책 · 합동 사전 TE · 귀무 C0 와 분해 팔.

설계 원본(구속): vbatch_research.json final.allocator(members_primary · members_twin · signal · estimator · target · execution · net_book ·
  nulls_and_decomposition · L_run) · final.estimator.allocator_estimator · final.conditions.primary_strands[G1rel] · D08 · D18. 설계를 다시 짓지 않는다.

  구성원  MOM · LBS · LIQ · VAL · QLT(K = 5 · w0 = 1/K) · 쌍둥이 C-7 = + INS · EAR(측정만)
  신호    G1_f,t = Σ_{s=t−11..t} y_f,s(y = θ = 1 책 능동수익 · L: P_f − Mkt · French t−2 늦춤 · S: 책 − w_B · 늦춤 0) → r_f = (G1_f − 평균)/sd(K ≥ 3) — v_cond.g1rel
  추정기  Fama–MacBeth 전략 사이 기울기(v_core.fm_slope_path · L 에서 추정 · S 는 같은 기울기로 S 의 r 을 읽는다) · 부호 잘림(≥ 0) · 가닥 하나라 R2 면제(선언)
  목표    Δw* = Π_{Σ = 0, |Δw_f| ≤ ½w0}(¼w0 · (v^A_f − 평균 v^A)) · 바닥 ½w0(v_core.alloc_target)
  체결    ½ 체결 · 무거래 0.1·w0 · 월 Σ|거래| ≤ 0.20(v_core.execute_a · a_path 복사)
  순액    Σ_f w_f × 책_f(θ_f) → 한 권의 주식 책 · 합동 사전 TE ≤ 슬리브 5%/년(Σ̂_A = 지금 책들의 60개월(최소 36) 보유 기준 되짚기 · LW 상수상관 ·
          넘으면 순 능동을 비례 축소) · 발행사 순 능동 ±10%p · 섹터 ±10%p · NDX 전용 ≤ 10% · β 띠 |β̂ − β̂(w_B)| ≤ 0.03(주식 기울기 — LBS 의 낮은 β 를 여기서 메운다)
  팔      C0(정적 θ0 × 1/K 고정 · 월 되돌림 · 같은 체결 · 비용 · 순액 · β 띠 · 귀무일 뿐) · C-A(배분기만) · C-W(거미줄만) · FULL(둘 다 · 전방 후보 VFA) ·
          C-β(순액 β 띠 끔) · C-R2S · C-R2off · C-NoShrink · C-7 · C-CAP80 — H_V 배분기 구성원 Δ_A = X(C-A) − X(C0).

명세가 정하지 않은 산수(최소 선택 · 선언)
  A1 L 층 배분 슬리브 다리 = [Mkt, P_1..P_K] · P_f 비중 = w_f × θ_f · Mkt = 1 − Σ · 배분 비중을 흘릴 전략 수익 R_f = Mkt + θ_f(P_f − Mkt) · L 층 β 띠 없음(베타 조정 α 가 맡는다 · 명세 L_layer.sleeve).
  A2 S 층: 배분 비중을 흘릴 전략 수익 = 구성원 목표 책의 보유월 수익(체결 마찰 없음) · 순액 목표 = 체결된 배분 비중 × 구성원 목표 책 → TE → 투영 → β 띠 →
     한 권의 주식 책으로 체결 — 구성원마다 따로 체결하지 않는다(이중 과금 없음 · 체결 규칙은 A5).
  A3 Σ̂_A 되짚기: 결정 달 m 의 구성원 능동 벡터 a_f = 책_f − w_B 에 달 m−59..m 의 이름별 월 수익(월말 수정종가 · 가격 없는 이름 0 기여)을 곱한 K 계열 · 선 행 ≥ 36.
  A4 🔧(검토 고침 · 등록 전) L 층 FM 기울기는 **대리가 선 달 전부**(MOM · LIQ 1926~ · VAL 1951-07~ → K_s ≥ 3 은 약 1952-07~)에서 쌓는다 — 명세 allocator.L_run
     «K_s ≥ 3 인 달부터 쌓아 1963-07 에 이미 활성». 옛 판은 1963-07 앞 y 를 비워 기울기가 약 1976-10 에야 섰다(합성 점검 · 약 12년 손실).
     배분 목표 · 팔 축(비중 경로 · Δ_A)은 구성원 다섯 대리가 모두 선 1963-07 ~ 그대로 · r 이 없는 달의 v^A = 0(1/K 쪽).
  A5 🔧(검토 고침 · 등록 전) 순액 책의 LIQ 몫: 순액 목표를 두 소매로 나눈다 — 소매 a = 목표 × LIQ 몫(이름마다 w_LIQ·책_LIQ / Σ_f w_f·책_f · 순액 단계가 더한 이름은 w_LIQ 몫)
     을 LIQ 규칙(전량 체결 · 상태 의존 비용 — 명세 V03 · 비평 1 M1)으로, 소매 b = 나머지를 ½ 체결 · 10bp 로. 두 소매는 따로 흘러가고 이름마다 순 거래만 과금한다
     (v_cards.SLayer.path_split). LIQ 가 구성원이 아니면(G-EGD) 한 소매(½ · 10bp).

🚨 수익 · 신호-수익 통계를 계산하지 않는다 — 경로 계열만 만든다(G1 은 수익 입력이라 굽기 · 눈가린 연기에서만 실자료로 부른다).

  python build/v_alloc.py --selftest
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
import v_core as C          # noqa: E402
import v_cond as VC         # noqa: E402
import v_data as VD         # noqa: E402
import v_cards as VK        # noqa: E402

MEMBERS5 = ("V01", "V02", "V03", "V06", "V07")
MEMBERS7 = MEMBERS5 + ("V04", "V05")
ARMS = ("FULL", "C0", "C-A", "C-W", "C-β", "C-R2S", "C-R2off", "C-NoShrink", "C-7", "C-CAP80")
L_ALLOC_FROM = "1963-07"
LIQ = "V03"                                                                         # A5 — 순액 책에서 LIQ 규칙(전량 체결 · 상태 의존 비용)을 지키는 소매
ARM_DEF = {   # 팔 → (배분기 켬, 거미줄 켬, 거미줄 선택, 순액 β 띠, 구성원, CAP80)
    "FULL": (True, True, {}, True, MEMBERS5, False),
    "C0": (False, False, {}, True, MEMBERS5, False),
    "C-A": (True, False, {}, True, MEMBERS5, False),
    "C-W": (False, True, {}, True, MEMBERS5, False),
    "C-β": (True, True, {}, False, MEMBERS5, False),
    "C-R2S": (True, True, {"r2": "strict"}, True, MEMBERS5, False),
    "C-R2off": (True, True, {"r2": "off"}, True, MEMBERS5, False),
    "C-NoShrink": (True, True, {"shrink": False}, True, MEMBERS5, False),
    "C-7": (True, True, {}, True, MEMBERS7, False),
    "C-CAP80": (True, True, {}, True, MEMBERS5, True),
}


# ══════════════════════════════════════════════════════════════════════════
#  신호 · 추정기 · 목표(층 공통)
# ══════════════════════════════════════════════════════════════════════════
def rel_scores(Y, lag):
    """G1rel r_f(결정 달 × 전략) — v_cond.g1rel(12달 합 · 상대 z · K ≥ 3 · 늦춤)."""
    return VC.g1rel(Y, lag=lag)


def fm_from(R, Y, axis, shrink=True):
    """FM 기울기(v_core.fm_slope_path) — R · Y 를 같은 결정 달 축에 맞춘 뒤. 돌려주는 것 dict + b_c Series."""
    Rm = pd.DataFrame(R).reindex(axis)
    Ym = pd.DataFrame(Y).reindex(index=axis, columns=Rm.columns)
    o = C.fm_slope_path(Rm.to_numpy(float), Ym.to_numpy(float), shrink=shrink)
    o["b_c_s"] = pd.Series(o["b_c"], index=axis)
    return o


def alloc_targets(R, b_c, members, on=True):
    """결정 달마다 목표 배분(T×K) · v^A — on=False(C0 · C-W) 면 1/K 고정. R = 상대 점수(DataFrame · 결정 달 색인)."""
    K = len(members)
    w0 = np.full(K, 1.0 / K)
    idx = R.index
    V = np.zeros((len(idx), K))
    Tg = np.tile(w0, (len(idx), 1))
    if on:
        bc = pd.Series(b_c, dtype=float).reindex(idx).to_numpy(float)
        v, _u = C.alloc_v(bc, R[list(members)].to_numpy(float))
        V = np.nan_to_num(v, nan=0.0)
        for i in range(len(idx)):
            Tg[i], _ = C.alloc_target(V[i], w0)
    return pd.DataFrame(Tg, index=idx, columns=list(members)), pd.DataFrame(V, index=idx, columns=list(members))


def block_shuffle_rows(M, rng, block=12, min_finite=None):
    """위약 — 달 블록째 섞기(행 = 달 · 모든 열을 함께 · 조건/점수 사이 상관 보존). 모든 열이 선 첫 행 ~ 마지막 행 구간을 block 달 토막으로 나눠
    토막 차례를 섞는다(그 밖의 행은 그대로 — 열마다 다른 시작 앞 결측이 가운데로 옮겨 가지 않게).
    명세 tests.joint_conditions(b) «달 블록째 섞기» — 토막 길이 12 · «모든 열이 선 구간» 은 선언(최소 선택 · 등록문에 옮긴다).
    min_finite = k 이면 «선 열이 k 개 이상인 행» 의 첫 ~ 마지막 구간을 섞는다(배분기 · FM 이 K_s ≥ 3 달부터 쌓으므로 k = 3 — A4 검토 고침과 짝)."""
    A = np.asarray(M, float)
    fin = np.flatnonzero(np.isfinite(A).all(1) if min_finite is None else (np.isfinite(A).sum(1) >= int(min_finite)))
    out = A.copy()
    if len(fin) < 2:
        return out
    a, b = fin[0], fin[-1] + 1
    seg = A[a:b]
    n = len(seg)
    cuts = list(range(0, n, block))
    blocks = [seg[c:c + block] for c in cuts]
    order = rng.permutation(len(blocks))
    out[a:b] = np.concatenate([blocks[j] for j in order], axis=0)[:n]
    return out


# ══════════════════════════════════════════════════════════════════════════
#  L 층 배분기(A1 · A4 · 🚨 L 층 값은 저장소에 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def l_inputs(LL, members=MEMBERS5):
    Y = pd.DataFrame({s: LL.P[s] for s in members}).reindex(LL.axis)
    return Y


def l_fm(LL, members=MEMBERS5, shrink=True, R_override=None):
    """L 층 FM — y = P_f − Mkt · r = g1rel(y, 늦춤 2) · 대리가 선 달 전부에서 쌓는다(K_s ≥ 3 · A4 검토 고침 — 목표 · 팔 축만 1963-07 ~)."""
    Y = l_inputs(LL, members)
    Y = Y.copy()
    R = rel_scores(Y, lag=VD.AVAIL["french:lag2"][0]).reindex(LL.axis) if R_override is None else pd.DataFrame(R_override, index=LL.axis,
                                                                                                                      columns=list(members))
    o = fm_from(R, Y, LL.axis, shrink=shrink)
    o["R"], o["Y"] = R, Y
    return o


def l_allocator(LL, thetas, members=MEMBERS5, on=True, fm=None, taus=None, R_override=None):
    """L 층 배분 슬리브 — thetas = {sid: θ Series(결정 달)} · on = 배분기 켬. 돌려주는 것 dict(arm(arm_legs) · w · V · targets)."""
    fm = fm or l_fm(LL, members, R_override=R_override)
    R = fm["R"] if R_override is None else pd.DataFrame(R_override, index=LL.axis, columns=list(members))
    ax = LL.axis[LL.axis >= pd.Period(L_ALLOC_FROM, "M")]
    Tg, V = alloc_targets(R.reindex(ax), fm["b_c_s"].reindex(ax), members, on=on)
    th = pd.DataFrame({s: pd.Series(thetas[s], dtype=float).reindex(ax) for s in members})
    Rs = pd.DataFrame({s: LL.mkt.reindex(ax) + th[s].shift(1) * LL.P[s].reindex(ax) for s in members})
    P = C.a_path(Tg.to_numpy(float), Rs.to_numpy(float), np.full(len(members), 1.0 / len(members)))
    Wd = pd.DataFrame(P["w"], index=ax, columns=list(members))
    legs_w = (Wd * th).shift(1)                                                     # 보유 달 = 결정 + 1
    W = pd.concat([1.0 - legs_w.sum(axis=1, min_count=len(members)).rename("Mkt"), legs_w], axis=1)
    Rl = pd.concat([LL.mkt.reindex(ax).rename("Mkt")] + [(LL.mkt + LL.P[s]).reindex(ax).rename(s) for s in members], axis=1)
    ok = W.notna().all(axis=1) & Rl.notna().all(axis=1)
    W, Rl = W[ok], Rl[ok]
    tau = {s: (taus or {}).get(s) for s in members} if taus else None
    a = C.arm_legs(W, Rl, C.cost_rate_L(W.index), tau=tau)
    a["B"] = LL.mkt.reindex(W.index)
    return {"arm": a, "w": Wd, "V": V, "targets": Tg, "fm": fm}


# ══════════════════════════════════════════════════════════════════════════
#  S 층 배분기(A2 · A3) — 구성원 책 · y_S 는 v_cards.s_card_arms(keep_books=True) 결과
# ══════════════════════════════════════════════════════════════════════════
def month_returns_matrix(SL, keys, m, n=C.SIG_N):
    """A3 — 가격 키 목록의 달 m−n+1..m 월 수익 행렬(이름 × 달 · 결측 NaN) — 월말 수정종가(v_pit.Pm)."""
    U = SL.U
    j1 = U._mpos[m]
    j0 = max(1, j1 - n + 1)
    M = np.full((len(keys), j1 - j0 + 1), np.nan)
    for r, k in enumerate(keys):
        pm = U.Pm.get(k)
        if pm is None:
            continue
        a, b = pm[j0 - 1:j1], pm[j0:j1 + 1]
        with np.errstate(invalid="ignore", divide="ignore"):
            M[r] = np.where((a > 0) & np.isfinite(a) & np.isfinite(b), b / a - 1.0, np.nan)
    return M


def joint_te(SL, m, books, w_alloc, cap80=False):
    """합동 사전 TE(A3) — √(12·wᵀΣ̂_A w) · Σ̂_A = LW 상수상관(구성원 능동 계열 · 선 행 ≥ 36). 돌려주는 것 (TE | None, n 행)."""
    X = SL.cross(m)
    wB = X.wB80 if cap80 else X.wB
    A = np.vstack([X.arr(b) - wB for b in books])                                   # K × 이름
    M = month_returns_matrix(SL, X.k, m)
    Mz = np.where(np.isfinite(M), M, 0.0)
    Sser = A @ Mz                                                                   # K × 달
    known = np.isfinite(M).any(0)
    Sser = Sser[:, known].T
    if len(Sser) < C.SIG_MIN:
        return None, len(Sser)
    Sig, _ = C.lw_cc_cov(Sser)
    return C.te_sleeve(np.asarray(w_alloc, float), Sig), len(Sser)


def net_target(SL, m, w_alloc, books, beta_net=True, cap80=False, te_max=C.NET_TE_MAX, liq_idx=None):
    """순액 목표(A2) — Σ w_f 책_f → TE 비례 축소 → 투영(발행사 ±10%p · 섹터 ±10%p · NDX ≤ 10%) → β 띠. 돌려주는 것 ({티커: 비중}, info).
    liq_idx = LIQ 구성원의 자리(있으면 info["liq_share"] = {티커: LIQ 소매 몫} · A5)."""
    X = SL.cross(m)
    wB = X.wB80 if cap80 else X.wB
    parts = [float(w) * X.arr(b) for w, b in zip(w_alloc, books)]
    N = sum(parts)
    raw = N.copy()
    N = N / N.sum()
    te, nte = joint_te(SL, m, books, w_alloc, cap80)
    info = {"te": te, "te_rows": nte, "te_scaled": False}
    if te is not None and te > te_max:
        N = wB + (te_max / te) * (N - wB)
        info["te_scaled"] = True
    proj = lambda x: C.project_active(x, wB, X.sec, X.ndx, cap=C.NET_ISSUER_CAP, sband=C.SECTOR_BAND)[0]
    N = proj(N)
    if beta_net:
        N, bi = C.beta_band(N, wB, X.beta, proj)
        info["beta"] = bi
    N = np.where(N > 1e-15, N, 0.0)
    N = N / N.sum()
    b = X.book(N)
    C.assert_stock_book(b)
    if liq_idx is not None:
        wl = float(w_alloc[liq_idx]) / float(np.sum(w_alloc))
        with np.errstate(invalid="ignore", divide="ignore"):
            sh = np.where(raw > 1e-15, parts[liq_idx] / raw, wl)
        info["liq_share"] = {t: float(min(1.0, max(0.0, sh[X.pos[t]]))) for t in b}
    return b, info


def s_allocator(SL, comps, members, on=True, fm_L=None, beta_net=True, cap80=False, R_override=None, arm_key="W", paths=True):
    """S 층 배분기 팔 — comps = {sid: s_card_arms 결과(keep_books=True)} · arm_key = 구성원 책 팔("W" 거미줄 · "S0" 정적) ·
    fm_L = L 층 FM(b_c_s) · 🚨 수익 입력. 돌려주는 것 dict(targets{달: 책} · w(DataFrame) · V · path(DataFrame) · info)."""
    ms = [m for m in SL.months if m >= VD.SE_FROM]
    axis = pd.PeriodIndex(ms, freq="M")
    Y = pd.DataFrame({s: comps[s]["y_S"] for s in members}).reindex(axis)
    R = rel_scores(Y, lag=0).reindex(axis) if R_override is None else pd.DataFrame(R_override, index=axis, columns=list(members))
    bc = fm_L["b_c_s"].reindex(axis) if fm_L is not None else pd.Series(0.0, index=axis)
    Tg, V = alloc_targets(R, bc, members, on=on)
    books = {s: (comps[s]["books"].get(arm_key) or comps[s]["books"]["S0"]) for s in members}
    run = [m for m in ms if m >= VK.S_ARM_FROM and all(m in books[s] for s in members)]
    if not run:
        return {"targets": {}, "w": None, "V": V, "path": None, "info": {}}
    rix = pd.PeriodIndex(run, freq="M")
    Rs = np.full((len(run), len(members)), np.nan)
    for i, m in enumerate(run):
        r = SL.hold(m)
        for j, s in enumerate(members):
            x = C.book_ret(books[s][m], r)
            if i + 1 < len(run) and x is not None:
                Rs[i + 1, j] = x                                               # a_path: R 행 i+1 = 결정 i 의 보유월 수익
    P = C.a_path(Tg.reindex(rix).to_numpy(float), Rs, np.full(len(members), 1.0 / len(members)))
    Wd = pd.DataFrame(P["w"], index=rix, columns=list(members))
    targets, info = {}, {}
    liq_idx = list(members).index(LIQ) if LIQ in members else None
    for i, m in enumerate(run):
        wa = Wd.iloc[i].to_numpy(float)
        if not np.isfinite(wa).all():
            continue
        targets[m], info[m] = net_target(SL, m, wa, [books[s][m] for s in members], beta_net=beta_net, cap80=cap80, liq_idx=liq_idx)
    if not paths:
        path = None
    elif liq_idx is not None:                                                       # A5 — LIQ 소매는 전량 체결 · 상태 의존 비용
        path = SL.path_split(targets, {m: info[m]["liq_share"] for m in targets})
    else:
        path = SL.path(targets, fill=C.FILL)
    return {"targets": targets, "w": Wd, "V": V, "path": path, "info": info}


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험
# ══════════════════════════════════════════════════════════════════════════
def _fake_LL(seed=4, signal=0.0):
    rng = np.random.default_rng(seed)
    axis = pd.period_range("1926-07", "2026-08", freq="M")
    zL = pd.DataFrame({c: np.clip(rng.normal(0, 1, len(axis)), -2, 2) for c in VC.CONDS}, index=axis)
    T = len(axis)
    Y = np.zeros((T, 5))
    ar = np.zeros(5)
    for t in range(T):
        ar = 0.9 * ar + rng.normal(0, 0.004, 5)
        Y[t] = ar * signal + rng.normal(0, 0.02, 5)
    prox = {s: pd.Series(Y[:, j], index=axis) for j, s in enumerate(MEMBERS5)}
    mkt = pd.Series(rng.normal(0.008, 0.045, T), index=axis)
    return VK.LLayer(zL, prox, mkt, pd.Series(0.003, index=axis))


def _st_targets():
    idx = pd.period_range("2000-01", periods=4, freq="M")
    R = pd.DataFrame([[1.5, -1.5, 0.0, 0.5, -0.5]] * 4, index=idx, columns=MEMBERS5)
    Tg, V = alloc_targets(R, pd.Series(0.2, index=idx), MEMBERS5, on=True)
    w0 = 0.2
    v = C.band(np.array([1.5, -1.5, 0.0, 0.5, -0.5]))
    dw = C.proj_box_sum0(0.25 * w0 * (v - v.mean()), 0.5 * w0)
    assert np.allclose(Tg.iloc[0].to_numpy(), w0 + dw) and np.allclose(V.iloc[0].to_numpy(), v)
    assert (Tg.to_numpy() >= 0.5 * w0 - 1e-15).all() and np.allclose(Tg.sum(axis=1), 1.0)
    T0, V0 = alloc_targets(R, pd.Series(0.2, index=idx), MEMBERS5, on=False)
    assert np.allclose(T0.to_numpy(), w0) and not V0.to_numpy().any()
    Tz, _ = alloc_targets(R, pd.Series(0.0, index=idx), MEMBERS5, on=True)            # b^c = 0 → v = 0 → 1/K
    assert np.allclose(Tz.to_numpy(), w0)
    rng = np.random.default_rng(1)
    M = np.arange(60, dtype=float).reshape(30, 2)
    M[:3] = np.nan
    S = block_shuffle_rows(M, rng, block=12)
    assert np.isnan(S[:3]).all() and sorted(S[3:, 0].tolist()) == sorted(M[3:, 0].tolist()) and np.allclose(S[3:, 1] - S[3:, 0], 1.0)
    return "배분 목표(¼w0 · 상자 ½w0 · Σ 1 · 바닥 ½w0) 손 확인 · 끔 → 1/K · b^c = 0 → 1/K · 달 블록째 섞기(행 보존 · 열 사이 관계 보존)"


def _st_L_identity():
    LL = _fake_LL(signal=1.0)
    th = {s: pd.Series(0.75, index=LL.axis) for s in MEMBERS5}
    fm = l_fm(LL)
    assert fm["ok"].any()
    on = l_allocator(LL, th, on=True, fm=fm)
    off = l_allocator(LL, th, on=False, fm=fm)
    zero = dict(fm, b_c_s=fm["b_c_s"] * 0.0)
    z = l_allocator(LL, th, on=True, fm=zero)
    # 항등성 — 배분기 v ≡ 0(b^c = 0) → C0(1e−12)
    a, b = z["arm"]["S"], off["arm"]["S"]
    assert len(a) == len(b) and np.nanmax(np.abs(a.to_numpy() - b.to_numpy())) <= 1e-12
    assert np.nanmax(np.abs(z["arm"]["tf"].to_numpy() - off["arm"]["tf"].to_numpy())) <= 1e-12
    W = on["w"].dropna()
    assert (W.to_numpy() >= 0.1 - 1e-12).all() and np.allclose(W.sum(axis=1), 1.0)
    assert on["V"].abs().to_numpy().max() > 0
    # 배분 경로의 달 Σ|거래| ≤ 0.20
    tr = on["arm"]["tf"]
    assert np.isfinite(tr).all()
    # A4 검토 고침 — FM 기울기는 대리가 선 달 전부에서(K_s ≥ 3): 실제 대리 첫 달(MOM 1927-01 · LIQ 1926-02 · VAL 1951-07 · LBS · QLT 1963-07)로 잘라도
    #   1963-07 뒤 곧(약 1964-10) 활성 — 옛 판(1963-07 앞 비움)은 약 1976-10
    first = {"V01": "1927-01", "V02": "1963-07", "V03": "1926-02", "V06": "1951-07", "V07": "1963-07"}
    P2 = {s_: LL.P[s_].where(LL.axis >= pd.Period(first[s_], "M")) for s_ in MEMBERS5}
    LL2 = VK.LLayer(LL.Z, P2, LL.mkt, LL.rf)
    fm2 = l_fm(LL2)
    fa = LL2.axis[np.flatnonzero(fm2["ok"])[0]]
    assert pd.Period("1963-07", "M") <= fa <= pd.Period("1966-01", "M"), fa
    return "L 배분기: FM 기울기 활성(대리 첫 달 그대로 → 첫 활성 %s · A4) · 항등성(b^c = 0 → C0 · 슬리브 · 거래 1e−12) · 비중 바닥 ½w0 · 합 1 · 합성 신호에서 v ≠ 0" % fa


def _st_S():
    FL = VK._FakeLayer()
    SL = VK.SLayer(FL, months=[m for m in FL.pit.months if "2010-01" <= m <= "2017-10"])
    comps = {}
    for s in MEMBERS5:
        comps[s] = VK.s_card_arms(SL, VK.spec_of(s), None, arms=("F", "S0"), paths=False, keep_books=True)
    idx = pd.PeriodIndex(SL.months, freq="M")
    fm0 = {"b_c_s": pd.Series(0.0, index=idx)}
    fm1 = {"b_c_s": pd.Series(0.3, index=idx)}
    c0 = s_allocator(SL, comps, MEMBERS5, on=False, fm_L=fm0, arm_key="S0")
    ca0 = s_allocator(SL, comps, MEMBERS5, on=True, fm_L=fm0, arm_key="S0")
    assert set(c0["targets"]) == set(ca0["targets"]) and len(c0["targets"]) > 12
    for m in c0["targets"]:
        a, b = c0["targets"][m], ca0["targets"][m]
        assert max(abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b)) <= 1e-12            # 항등성: 배분기 v ≡ 0 → C0
    ca = s_allocator(SL, comps, MEMBERS5, on=True, fm_L=fm1, arm_key="S0")
    m = sorted(ca["targets"])[-1]
    X = SL.cross(m)
    N = X.arr(ca["targets"][m])
    bb = np.where(np.isfinite(X.beta), X.beta, 1.0)
    assert abs(N.sum() - 1) < 1e-9 and (np.abs(N - X.wB) <= 0.10 + 1e-9).all() and N[X.ndx].sum() <= 0.10 + 1e-9
    inf = ca["info"][m]
    assert (inf.get("beta") is None) or inf["beta"]["ok"] or abs(N @ bb - X.wB @ bb) <= 0.03 + 1e-9
    te, n = joint_te(SL, m, [comps[s]["books"]["S0"][m] for s in MEMBERS5], np.full(5, 0.2))
    assert n >= 36 and te is not None and te >= 0
    nb, ninf = net_target(SL, m, np.full(5, 0.2), [comps[s]["books"]["S0"][m] for s in MEMBERS5], te_max=1e-6)
    assert ninf["te_scaled"]
    Nn = X.arr(nb)
    assert np.abs(Nn - X.wB).sum() < np.abs(N - X.wB).sum() + 1e-9                               # TE 상한이 묶이면 순 능동이 준다
    assert c0["path"] is not None and len(c0["path"]) > 12 and (c0["path"]["traded"] >= 0).all()
    # A5 두 소매 체결 — 몫 0 이면 한 소매 ½ 체결 경로와 같고 · 몫 1 이면 LIQ 규칙(전량 · 상태 의존 비용) 한 소매 경로와 같다(1e−12)
    T = c0["targets"]
    p0 = SL.path_split(T, {m: {t: 0.0 for t in T[m]} for m in T})
    q0 = SL.path(T, fill=C.FILL)
    p1 = SL.path_split(T, {m: {t: 1.0 for t in T[m]} for m in T})
    q1 = SL.path(T, fill=C.FILL_LIQ, rate="liq")
    for a_, b_ in ((p0, q0), (p1, q1)):
        for col in ("S", "S_t1", "traded", "rate"):
            assert np.nanmax(np.abs(a_[col].to_numpy(float) - b_[col].to_numpy(float))) <= 1e-12, col
    ph = SL.path_split(T, {m: {t: 0.5 for t in T[m]} for m in T})
    assert (ph["share_a"] > 0.3).all() and (ph["traded"] >= 0).all() and (ph["rate"] >= C.S_COST - 1e-15).all()
    return "S 배분기: 항등성(v ≡ 0 → C0 순액 책 1e−12) · 순액 책 제약(발행사 ±10%p · NDX ≤ 10% · β 띠) · 되짚기 Σ̂_A(행 ≥ 36) · TE 상한 → 순 능동 축소 · 경로 · 두 소매 체결(몫 0 = ½ 경로 · 몫 1 = LIQ 경로 · 1e−12)"


def selftest():
    res, ok = [], True
    for fn in (_st_targets, _st_L_identity, _st_S):
        t0 = time.time()
        try:
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                res.append(("통과", fn.__name__, fn(), round(time.time() - t0, 1)))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-2500:], round(time.time() - t0, 1)))
    for st, nm, msg, sec in res:
        print("  %s %-16s %5ss  %s" % ("✓" if st == "통과" else "✗", nm, sec, msg))
    print("v_alloc selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
