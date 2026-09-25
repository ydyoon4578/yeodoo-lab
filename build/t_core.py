# -*- coding: utf-8 -*-
"""build/t_core.py — 배치 T 평가 틀: 펀드틀 · 비용 · 선물 차입 · 사건 · H1 · H2(블록 셔플) · NW · H_T0 · 층 창 · 관문 G2~G6 · 라벨.

설계 원본: tbatch_research.json 의 final(저장소 밖 스크래치) — final.tests 를 옮긴 것이다. 다시 설계하지 않는다.
  카드 규칙은 build/t_cards.py · 신호는 build/t_signals.py · S 층 PIT 복제 바스켓은 build/t_pit.py · 자료는 build/t_data.py.

사용자 결정(2026-09-26)
  D1 장기 검정(1926+)은 사이트에 싣지 않는 «기전 증거 층»(L-R · L-C)에서만. 사이트 10년 규약(maxyears.MAX_YEARS)은 그대로다 —
     S 층 창은 정확히 MAX_YEARS × 12 개월이어야 하고(layer_windows 가 단언), L 층 산출은 저장소 밖 캐시에만 쓴다(out_path).
  D2 S&P 지수 선물(±5%) · 지수 옵션 · 커버드콜 ETF 허용 · 교차자산 선물 불허 → T02 는 측정만이고 전방 후보가 아니다(forward_ok).
  D3 AQR · Cboe · Wurgler 원자료와 파생 NAV 는 커밋 · 게시하지 않는다 — 결과 파일도 저장소 밖(out_path).
  D4 배치 FWER 0.025 는 H_T0 하나(스타우퍼 · 청정 창 t) · 누적 N 은 DSR 보고만.

틀(final.tests)
  · 펀드 F_t = 0.9·B_t + 0.1·S_t (월말 되돌림) → X_t = F_t − B_t = 0.1·(S_t − B_t) − 0.1·c_t. 슬리브와 펀드의 IR · t 는 같다.
  · 비용 c_t = 편도 비율(t) × Σ|Δw| (+ 차입 · 고정 · 내부 회전) — 1975-04 까지 50bp · 1975-05~2000-12 20bp · 2001-01 부터 10bp.
    Σ|Δw| = 자금 다리(흘러간 비중 대비) + 선물 다리(|Δw|). 현금 다리는 무비용. 창 첫 달 · 공백 뒤 첫 달은 매매 0(첫 매수 미과금).
    1982-04 이전 선물 오버레이의 매수 쪽은 가상 차입 RF + 50bp/년(차입 스프레드만 비용으로 뗀다).
    French 포트폴리오 내부 회전은 L 층에서 총액 · G5e 순액판에서만 PIT 로 잰 회전율 τ(편도 · 연)로 뗀다(비용 = 비율 × 2τ/12 × 비중).
  · H1: X 평균 > 0 · NW(6) t(eg30plus.nw_t · L=12 보고) · 한쪽 p = 1 − Φ(t).
  · H2: Δ^D = X_rule − X_static · X_static = 창 전체 실현 비중 고정 · 월 되돌림 · 같은 비용. 위약 = 상태 런 블록 셔플(상태마다 런 길이를
    섞고 런 차례는 그대로 — 빈도 · 런 길이 · 교체 수 보존 · 두 상태면 q_switch.seg_shuffle 과 같다) 1,000회 · 씨앗 20260925 ·
    p = (1 + #{Δ_perm ≥ Δ_obs})/1001 · 순위 = #{Δ_perm < Δ_obs}/1000.
  · 사건: 하락월 B_t < 0 · CRASH/SURGE-M = B_t ≤ −σ_L / ≥ +σ_L(σ_L = French Mkt TR 1927-01~2026-07 표준편차 하나 · 실행 때 한 번) ·
    급락 다리 · 반등 = mech_episodes 지그재그(문턱 10% · ^GSPC PR 일간 1927-12-30~ · 반등 63거래일). S 층은 mech_episodes.json(동결).
  · 층: L-R = 카드 full 창 · L-C = 카드 clean 창 · S = 2016-09~2026-08(B = SPY TR · RF = BIL · 편도 10bp) · 겹침 2016-09~2026-07.
  · H_T0: Z = Σ t_i / √(Σ_i Σ_j ρ_ij) · ρ_ij = 두 카드 청정 창 월 X 의 겹친 달 상관(≥ 36 개월 · 아니면 0) · 한쪽 α 0.025(z ≥ 1.96).
    설계 식 그대로(부분 겹침을 n_ij/√(n_i n_j) 로 줄이지 않는다 — ρ > 0 이면 보수 · 합성 크기 0.023~0.030 · 등록 §2.3).
  · 관문 조건은 모두 bool 로 바꿔 AND 한다(None · NaN = 거짓) — «해당 없음» 은 카드 spec 이 선언한 G5 칸(na)뿐.
  · G6a 연도 승률은 12개월이 찬 달력 해만 센다(부분 해는 따로 적는다).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산하거나 찍지 않는다.
   --selftest 는 합성 자료만 · --blind-smoke 는 build/t_cards.py 가 돌린다(표준출력 버림 · 결과는 모양만 · 파일 안 씀).
   run_batch(write=True) 는 frozen_check()(등록 커밋 · 얼린 파일 · 한 번 굽기)를 통과해야만 돈다.

  python build/t_core.py --selftest
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import subprocess
import sys

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

import t_data as TD          # noqa: E402  자료 · 늦춤 · 캐시 경계

# ══════════════════════════════════════════════════════════════════════════
#  상수(final.tests · multiplicity) — 여기서만 바꾼다
# ══════════════════════════════════════════════════════════════════════════
SEED = 20260925                       # 블록 셔플 · 선견 점검 씨앗(설계)
NPERM = 1000                          # H2 블록 셔플 횟수(설계) — 연기 시험에서만 작게 덮어쓴다
NPERM_MIN = 1000                      # 굽기에서 이보다 적으면 멈춘다(연기 시험 덮어쓰기가 굽기로 새지 않게)
SLEEVE = 0.10                         # 펀드 = 0.9·B + 0.1·S
NW_LAG, NW_LAG_REPORT = 6, 12
COST_ERAS = (("1975-04", 0.0050), ("2000-12", 0.0020), ("9999-12", 0.0010))   # 편도 · 경계는 역사적 사실(끝 달 포함)
S_COST = 0.0010                       # S 층 편도 10bp
FUT_START = "1982-04"                 # S&P 500 선물 상장 — 그 앞 선물 오버레이의 매수 쪽은 가상 차입
BORROW_SPREAD = 0.0050                # 가상 차입 RF + 50bp/년 → 스프레드만 비용
S_WIN = ("2016-09", "2026-08")        # S 10년 구현성(보유월)
S_OVERLAP = ("2016-09", "2026-07")    # French 와 겹치는 달(능동수익 상관)
SIGMA_L_WIN = ("1927-01", "2026-07")  # σ_L 표본(French Mkt TR 월)
ZZ_HD = ZZ_HU = 0.10                  # 지그재그 문턱(mech_episodes 와 같다)
ZZ_REB_TD = 63
ZZ_START, ZZ_END = "1927-12-30", "2026-08-31"
SYNC_EXCL = (("1932-07", "1933-07"), ("2008-10", "2009-08"), ("2020-02", "2020-08"))   # G5h 동기 사건 제외
SYNC_EXCL_EXTRA = {"T08": (("2020-01", "2023-12"),)}
UNIVERSE_BREAKS = ("1963-07", "1973-01")                  # 우주 단절 부표본(앞 · 뒤)
NAMED_EVENTS = {                                          # 보고만(설계 events.named_events_report_only)
    "crash": (("1929-09", "1932-06"), ("1937-03", "1938-03"), ("1973-01", "1974-09"), ("1987-09", "1987-11"),
              ("2000-09", "2002-09"), ("2007-11", "2009-02"), ("2020-02", "2020-03"), ("2022-01", "2022-09")),
    "rebound": (("1932-07", "1932-08"), ("1933-04", "1933-07"), ("1974-10", "1975-06"), ("1982-08", "1983-06"),
                ("2003-03", "2003-12"), ("2009-03", "2009-08"), ("2020-04", "2020-08"), ("2025-05", "2025-07")),
}
TIE = 0.00005                         # G6a — |연 X| < 0.5bp 인 해는 무승부(빼고 따로 적는다)
G6A_MIN = 0.55
G6B_MIN = 0.50                        # 보고만
TURN_MAX = 10.0                       # G5e 편도 회전 ≤ 연 10배(사용자 규칙 2026-08-24 · 내부 회전 포함)
REB_MISS_MIN = 3                      # 반등 놓침 점검 — 그런 달이 3개 이상일 때만
RANK_MIN = 0.90                       # G4 교체 카드 위약 순위
FID_RHO = 0.60                        # S 층 능동수익 상관 문턱
H_T0_MEMBERS = ("T01", "T02", "T03", "T04", "T05", "T08", "T13", "T15", "T16", "T17")
H_T0_ALPHA = 0.025
Z_CRIT = 1.959963984540054            # Φ⁻¹(0.975)
RHO_MIN_OVERLAP = 36
BY_M = 10                             # 청정 창이 있는 카드 수 → c(m) = Σ 1/i
BY_Q = 0.10
DSR_N = (12, 62, 816)                 # 카드 · 팔 · 랩 누적(추정) — 보고만
DEFENSIVE = ("T02", "T04", "T12", "T15", "T17")     # G3 > 0
SWITCHING = ("T04", "T05", "T08", "T12", "T15", "T17")
LAB_OOS_CARDS = ("T16", "T17", "T18")               # «랩 표본 밖 재현» 라벨
LABELS = {"rep": "문헌 재현(전방 대기)", "rep_lab": "랩 표본 밖 재현(전방 대기)", "one": "한쪽형 — 측정만",
          "mix": "정적 혼합과 구별 안 됨 — 측정만", "none": "비재현", "f0": "측정 불가",
          "rep_d2": "문헌 재현 — 측정만(D2 · 전방 불가)"}     # 위임이 막은 카드(T02)가 «재현» 조건을 모두 넘었을 때 — «전방 대기» 라 쓰지 않는다


# ══════════════════════════════════════════════════════════════════════════
#  달 · 창
# ══════════════════════════════════════════════════════════════════════════
def per(x):
    return x if isinstance(x, pd.Period) else pd.Period(str(x)[:7], "M")


def mrange(a, b):
    return pd.period_range(per(a), per(b), freq="M")


def in_win(idx, a, b):
    idx = pd.PeriodIndex(idx)
    return np.asarray((idx >= per(a)) & (idx <= per(b)))


def years_of(n_months):
    return n_months / 12.0


def layer_windows(spec):
    """카드 spec → 층 창 {이름: (처음, 끝) 또는 None}. S 창은 MAX_YEARS × 12 개월이어야 한다(D1 · 사이트 10년 규약)."""
    import maxyears as MY
    w = spec["windows"]
    n = len(mrange(*S_WIN))
    if n != MY.MAX_YEARS * 12:
        raise SystemExit("🚨 S 층 창 %d개월 ≠ MAX_YEARS × 12 (%d)" % (n, MY.MAX_YEARS * 12))
    return {"L-R": w["full"], "L-C": w.get("clean"), "lit_seen": w.get("lit_seen"), "out_of_lab": w.get("out_of_lab"),
            "S": S_WIN, "S_overlap": S_OVERLAP, **{k: v for k, v in (spec.get("extra_windows") or {}).items()}}


# ══════════════════════════════════════════════════════════════════════════
#  비용
# ══════════════════════════════════════════════════════════════════════════
def cost_rate(idx, flat=None):
    """보유월마다 편도 비율(소수). flat 이 있으면 그 값(S 층 10bp · 총액 0)."""
    idx = pd.PeriodIndex(idx)
    if flat is not None:
        return np.full(len(idx), float(flat))
    out = np.empty(len(idx))
    ends = [per(e) for e, _ in COST_ERAS]
    rates = [r for _, r in COST_ERAS]
    for j, p in enumerate(idx):
        for e, r in zip(ends, rates):
            if p <= e:
                out[j] = r
                break
    return out


def borrow_mask(idx):
    """1982-04 이전 보유월(가상 차입 스프레드가 붙는 달)."""
    return np.asarray(pd.PeriodIndex(idx) < per(FUT_START))


# ══════════════════════════════════════════════════════════════════════════
#  팔(규칙 · 단계 · 대조 · 쌍둥이) — 보유월 계열
# ══════════════════════════════════════════════════════════════════════════
class Arm:
    """한 팔의 보유월 계열. S = 슬리브 총수익(비용 전) · B = 벤치마크 · tf = 자금 다리 Σ|Δw|(비용 붙는 것) ·
    to = 선물 다리 Σ|Δw| · fin = 선물 매수 쪽 명목(차입 스프레드 대상) · fixed = 달마다 고정 비용(소수) · W = 다리 비중(내부 회전용).
    X(mult, flat) = 0.1·(S − B) − 0.1·c. 수익 통계는 여기서 계산하지 않는다 — 계열만 낸다."""

    def __init__(self, name, S, B, tf=None, to=None, fin=None, fixed=None, W=None, meta=None, ov_cols=(), cl_cols=()):
        S = pd.Series(S, dtype=float)
        idx = S.index
        z = pd.Series(0.0, index=idx)
        self.name = name
        self.S = S
        self.B = pd.Series(B, dtype=float).reindex(idx)
        self.tf = z if tf is None else pd.Series(tf, dtype=float).reindex(idx).fillna(0.0)
        self.to = z if to is None else pd.Series(to, dtype=float).reindex(idx).fillna(0.0)
        self.fin = z if fin is None else pd.Series(fin, dtype=float).reindex(idx).fillna(0.0)
        self.fixed = z if fixed is None else pd.Series(fixed, dtype=float).reindex(idx).fillna(0.0)
        self.W = None if W is None else W.reindex(idx)
        self.meta = dict(meta or {})
        self.ov_cols, self.cl_cols = tuple(ov_cols), tuple(cl_cols)

    @property
    def valid(self):
        return self.S.notna() & self.B.notna()

    def sub(self, a, b):
        m = in_win(self.S.index, a, b) & self.valid.to_numpy()
        idx = self.S.index[m]
        return Arm(self.name, self.S.loc[idx], self.B.loc[idx], self.tf.loc[idx], self.to.loc[idx], self.fin.loc[idx],
                   self.fixed.loc[idx], None if self.W is None else self.W.loc[idx], self.meta, self.ov_cols, self.cl_cols)

    def cost(self, mult=1.0, flat=None, tau=None, gross=False):
        idx = self.S.index
        if gross:
            return pd.Series(0.0, index=idx)
        rate = cost_rate(idx, flat)
        c = rate * (self.tf.to_numpy() + self.to.to_numpy())
        c = c + self.fin.to_numpy() * BORROW_SPREAD / 12.0 * borrow_mask(idx)
        c = c + self.fixed.to_numpy()
        if tau and self.W is not None:                       # G5e 순액판 — 내부 회전 τ(편도 · 연) × 2/12 × 비중
            for leg, t_ in tau.items():
                if leg in self.W.columns and t_ is not None:
                    c = c + rate * 2.0 * float(t_) / 12.0 * np.abs(self.W[leg].fillna(0.0).to_numpy())
        return pd.Series(mult * c, index=idx)

    def X(self, mult=1.0, flat=None, tau=None, gross=False):
        c = self.cost(mult, flat, tau, gross)
        return SLEEVE * (self.S - self.B) - SLEEVE * c

    def turnover_1w(self, tau=None):
        """편도 회전(연) = (½·Σ 자금 Σ|Δw| + Σ 선물 |Δw|) / 해 + 내부 τ × 평균 비중."""
        v = self.valid.to_numpy()
        n = int(v.sum())
        if n == 0:
            return None
        tr = (0.5 * self.tf.to_numpy()[v].sum() + self.to.to_numpy()[v].sum()) / years_of(n)
        if tau and self.W is not None:
            for leg, t_ in tau.items():
                if leg in self.W.columns and t_ is not None:
                    tr += float(t_) * float(np.abs(self.W[leg].fillna(0.0).to_numpy()[v]).mean())
        return float(tr)


def _turn_arrays(Wm, R0, valid, funded, costly, ov):
    """비중 행렬(n×J) · 다리 수익(n×J · 없으면 0) → (tf, to). 흘러간 비중 = 전달 자금 비중 × (1 + r) 정규화 × 전달 자금 합.
    전달이 무효(창 밖 · 공백)면 그달 매매 0."""
    n = Wm.shape[0]
    tf, to = np.zeros(n), np.zeros(n)
    if n < 2:
        return tf, to
    Wp, Rp = Wm[:-1], R0[:-1]
    Wf = Wp[:, funded]
    g = Wf * (1.0 + Rp[:, funded])
    tot = g.sum(1, keepdims=True)
    base = Wf.sum(1, keepdims=True)
    drift = np.where(np.abs(tot) > 1e-15, g / np.where(np.abs(tot) > 1e-15, tot, 1.0) * base, Wf)
    d = np.abs(Wm[1:, funded] - drift)
    cf = costly[funded]
    tf[1:] = d[:, cf].sum(1)
    if ov.any():
        to[1:] = np.abs(Wm[1:, ov] - Wp[:, ov]).sum(1)
    ok = valid[1:] & valid[:-1]
    tf[1:] = np.where(ok, tf[1:], 0.0)
    to[1:] = np.where(ok, to[1:], 0.0)
    tf[0] = to[0] = 0.0
    return tf, to


def arm_weights(name, W, R, B, overlay=(), costless=(), fixed=None, meta=None):
    """다리 비중 W(보유월 × 다리 · 결정은 전달 말) · 다리 수익 R(같은 색인 · 선물 다리는 초과수익) · B → Arm.
    비중이 0 인 다리는 수익이 없어도 된다. 비중이 NaN 이면(신호 없음) 그달 팔이 없다."""
    W = W.astype(float)
    cols = list(W.columns)
    idx = W.index.intersection(pd.Series(B).dropna().index)
    W = W.reindex(idx)
    Rr = R.reindex(index=idx, columns=cols).astype(float)
    Wm, Rm = W.to_numpy(float), Rr.to_numpy(float)
    need = np.abs(np.nan_to_num(Wm)) > 0
    valid = ~np.isnan(Wm).any(1) & ~(need & np.isnan(Rm)).any(1)
    Wm0 = np.nan_to_num(Wm)
    R0 = np.where(need, np.nan_to_num(Rm), 0.0)
    S = (Wm0 * R0).sum(1)
    S = np.where(valid, S, np.nan)
    ov = np.array([c in overlay for c in cols])
    funded = ~ov
    costly = np.array([(c not in costless) and (c not in overlay) for c in cols])
    tf, to = _turn_arrays(Wm0, R0, valid, funded, costly, ov)
    fin = np.where(ov, np.maximum(Wm0, 0.0), 0.0).sum(1) if ov.any() else np.zeros(len(idx))
    fx = None if fixed is None else pd.Series(fixed).reindex(idx)
    return Arm(name, pd.Series(S, index=idx), pd.Series(B).reindex(idx), tf=pd.Series(tf, index=idx), to=pd.Series(to, index=idx),
               fin=pd.Series(fin, index=idx), fixed=fx, W=W, meta=meta, ov_cols=[c for c in cols if c in overlay],
               cl_cols=[c for c in cols if c in costless])


def weights_from_codes(codes, mapping, legs):
    """상태 부호(보유월 색인) → 비중 DataFrame. mapping = {부호: {다리: 비중}} · 부호 NaN 이면 행 NaN."""
    W = pd.DataFrame(np.nan, index=codes.index, columns=list(legs))
    for c, wd in mapping.items():
        m = (codes == c).to_numpy()
        if m.any():
            W.loc[m, :] = 0.0
            for leg, w in wd.items():
                W.loc[m, leg] = w
    return W


def static_mix(name, W, R, B, a, b, weights=None, overlay=(), costless=(), meta=None):
    """정적 혼합 — 창 [a, b] 의 실현 비중(다리별 평균 비중)을 고정 · 월 되돌림(흘러간 비중 대비 편도) · 같은 비용."""
    Wa = W.loc[in_win(W.index, a, b)]
    Wa = Wa[Wa.notna().all(axis=1)]
    e = pd.Series(weights, dtype=float) if weights is not None else Wa.mean()
    Wc = pd.DataFrame([e.reindex(W.columns).fillna(0.0).to_numpy()] * len(Wa), index=Wa.index, columns=W.columns)
    arm = arm_weights(name, Wc, R, B, overlay, costless, meta=dict(meta or {}, static=True, weights={k: float(v) for k, v in e.items()}))
    return arm


# ══════════════════════════════════════════════════════════════════════════
#  블록 셔플 · H2
# ══════════════════════════════════════════════════════════════════════════
def runs(codes):
    """정수 부호 배열 → (런 부호 배열, 런 길이 배열)."""
    x = np.asarray(codes)
    if len(x) == 0:
        return np.array([], int), np.array([], int)
    cut = np.flatnonzero(x[1:] != x[:-1]) + 1
    b = np.concatenate([[0], cut, [len(x)]])
    return x[b[:-1]], np.diff(b)


def block_shuffle(codes, rng):
    """상태 런 블록 셔플 — 상태마다 그 상태 런들의 길이를 섞고, 런의 상태 차례는 그대로 둔다(빈도 · 런 길이 · 교체 수 보존).
    두 상태면 q_switch.seg_shuffle(1 쪽을 먼저, 그다음 0 쪽)과 같은 난수 소비 · 같은 결과."""
    rc, L = runs(codes)
    Ln = L.copy()
    for s in sorted(set(rc.tolist()), reverse=True):
        m = rc == s
        seg = L[m].copy()
        rng.shuffle(seg)
        Ln[m] = seg
    return np.repeat(rc, Ln).astype(np.asarray(codes).dtype)


def _x_fast(Wm, R0, Bv, rate, funded, costly, ov, finmask):
    """비중 행렬로 월 X(비용 포함) — 순열 안의 빠른 경로. 모든 달이 유효하다고 본다(창을 미리 좁힌다)."""
    S = (Wm * R0).sum(1)
    valid = np.ones(len(S), bool)
    tf, to = _turn_arrays(Wm, R0, valid, funded, costly, ov)
    fin = np.where(ov, np.maximum(Wm, 0.0), 0.0).sum(1) if ov.any() else 0.0
    c = rate * (tf + to) + fin * BORROW_SPREAD / 12.0 * finmask
    return SLEEVE * (S - Bv) - SLEEVE * c


def h2_test(codes, mapping, R, B, a, b, nperm=None, seed=SEED, static_weights=None, overlay=(), costless=(), mult=1.0, flat=None):
    """H2 — Δ^D = X_rule − X_static(창 실현 비중 · 또는 static_weights) · 상태 런 블록 셔플 nperm 회.
    창은 부호 · 모든 다리 수익 · B 가 있는 달로 좁힌다(순열이 어느 다리든 들 수 있어서). 돌려주는 것:
    {"n", "delta_obs", "p", "rank", "n_perm", "seed", "dD"(월 계열), "static_w", "window"}."""
    nperm = NPERM if nperm is None else nperm
    legs = []
    for k in sorted(mapping):                            # 다리 차례 = 부호 차례의 첫 등장(결정적)
        for l in mapping[k]:
            if l not in legs:
                legs.append(l)
    idx = codes.index[in_win(codes.index, a, b)]
    c = codes.reindex(idx)
    Rr = R.reindex(index=idx, columns=legs)
    ok = c.notna().to_numpy() & Rr.notna().all(axis=1).to_numpy() & pd.Series(B).reindex(idx).notna().to_numpy()
    # 연속 구간만(가운데 공백이 있으면 가장 긴 연속 구간) — 셔플이 공백을 건너뛰지 않게
    runs_ok = np.split(np.arange(len(ok)), np.flatnonzero(np.diff(ok.astype(int))) + 1)
    best = max((r for r in runs_ok if len(r) and ok[r[0]]), key=len, default=np.array([], int))
    idx = idx[best]
    if len(idx) < 24:
        return {"n": int(len(idx)), "delta_obs": None, "p": None, "rank": None, "n_perm": 0, "seed": seed, "dD": None,
                "window": None, "err": "창이 너무 짧다"}
    codes_v = c.loc[idx].to_numpy().astype(int)
    keys = sorted(mapping)
    kpos = {k: j for j, k in enumerate(keys)}
    M = np.array([[float(mapping[k].get(l, 0.0)) for l in legs] for k in keys])
    R0 = Rr.loc[idx].to_numpy(float)
    Bv = pd.Series(B).reindex(idx).to_numpy(float)
    rate = mult * cost_rate(idx, flat)
    fm = borrow_mask(idx).astype(float) * mult
    ov = np.array([l in overlay for l in legs])
    funded = ~ov
    costly = np.array([(l not in costless) and (l not in overlay) for l in legs])
    ci = np.array([kpos[x] for x in codes_v])
    Wobs = M[ci]
    x_obs = _x_fast(Wobs, R0, Bv, rate, funded, costly, ov, fm)
    ew = (np.array([float(static_weights.get(l, 0.0)) for l in legs]) if static_weights is not None else Wobs.mean(0))
    Ws = np.repeat(ew[None, :], len(idx), 0)
    x_st = _x_fast(Ws, R0, Bv, rate, funded, costly, ov, fm)
    dD = x_obs - x_st
    d_obs = float(dD.mean())
    rng = np.random.default_rng(seed)
    dp = np.empty(nperm)
    for k in range(nperm):
        cp = block_shuffle(ci, rng)
        xp = _x_fast(M[cp], R0, Bv, rate, funded, costly, ov, fm)
        if static_weights is None:
            ewp = M[cp].mean(0)
            if not np.allclose(ewp, ew, atol=1e-12):
                raise AssertionError("블록 셔플이 실현 비중을 바꿨다")
        dp[k] = float((xp - x_st).mean())
    p = (1 + int((dp >= d_obs).sum())) / (nperm + 1) if nperm else None
    rank = float((dp < d_obs).mean()) if nperm else None
    return {"n": int(len(idx)), "window": [str(idx[0]), str(idx[-1])], "delta_obs": d_obs, "p": p, "rank": rank,
            "n_perm": int(nperm), "seed": seed, "static_w": {l: float(w) for l, w in zip(legs, ew)},
            "dD": pd.Series(dD, index=idx), "draws_hash": hashlib.sha256(np.round(dp, 12).tobytes()).hexdigest()[:16]}


# ══════════════════════════════════════════════════════════════════════════
#  통계(eg30plus 의 것을 쓴다 — 복제하면 표가 갈린다)
# ══════════════════════════════════════════════════════════════════════════
def nw_t(x, lag=NW_LAG):
    import eg30plus as E
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return E.nw_t(x, lag)


def norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def h1(x):
    """H1 — X 평균 > 0 · NW(6) t · 한쪽 p = 1 − Φ(t) · NW(12) 보고."""
    x = pd.Series(x, dtype=float).dropna()
    n = int(len(x))
    if n == 0:
        return {"n": 0, "mean": None, "ann": None, "t": None, "t12": None, "p": None}
    t6, t12 = nw_t(x.to_numpy(), NW_LAG), nw_t(x.to_numpy(), NW_LAG_REPORT)
    sd = float(x.std(ddof=1)) if n > 1 else None
    return {"n": n, "mean": float(x.mean()), "ann": float(x.mean() * 12), "te": (sd * math.sqrt(12) if sd else None),
            "ir": (float(x.mean() * 12 / (sd * math.sqrt(12))) if sd else None), "t": t6, "t12": t12,
            "p": (norm_sf(t6) if t6 is not None else None), "first": str(x.index[0]), "last": str(x.index[-1])}


def stouffer(tstats, xseries, min_overlap=RHO_MIN_OVERLAP):
    """H_T0 — Z = Σ t_i / √(Σ_i Σ_j ρ_ij). t 가 없는 구성원은 0 으로 넣고 분모에는 남긴다(보수).
    ρ_ij = 두 카드 청정 창 월 X 의 겹친 달 상관(겹침 ≥ min_overlap · 아니면 0) · ρ_ii = 1."""
    ids = list(tstats)
    k = len(ids)
    Rm = np.eye(k)
    ov = {}
    for i in range(k):
        for j in range(i + 1, k):
            a, b = xseries.get(ids[i]), xseries.get(ids[j])
            r = 0.0
            n_ov = 0
            if a is not None and b is not None:
                c = pd.concat([pd.Series(a), pd.Series(b)], axis=1, join="inner").dropna()
                n_ov = len(c)
                if n_ov >= min_overlap and c.iloc[:, 0].std() > 0 and c.iloc[:, 1].std() > 0:
                    r = float(np.corrcoef(c.iloc[:, 0], c.iloc[:, 1])[0, 1])
            Rm[i, j] = Rm[j, i] = r
            ov["%s~%s" % (ids[i], ids[j])] = {"n": int(n_ov), "rho": r}
    tv = np.array([0.0 if tstats[i] is None else float(tstats[i]) for i in ids])
    den = float(Rm.sum())
    z = float(tv.sum() / math.sqrt(den)) if den > 0 else None
    return {"members": ids, "t": {i: tstats[i] for i in ids}, "sum_t": float(tv.sum()), "den": den, "z": z,
            "alpha": H_T0_ALPHA, "z_crit": Z_CRIT, "reject": (z is not None and z >= Z_CRIT),
            "p": (norm_sf(z) if z is not None else None), "rho": ov, "t_missing_as_zero": [i for i in ids if tstats[i] is None]}


def by_info(pvals, q=BY_Q, m=BY_M):
    """Benjamini–Yekutieli — 정보로만(PRDS 가정 불필요). q/c(m) · c(m) = Σ 1/i."""
    cm = sum(1.0 / i for i in range(1, m + 1))
    ps = sorted((v, k) for k, v in pvals.items() if v is not None)
    kmax = 0
    for r, (v, _) in enumerate(ps, 1):
        if v <= (q / cm) * r / m + 1e-15:
            kmax = r
    return {"q": q, "c_m": cm, "m": m, "k": kmax, "admitted": sorted(k for _, k in ps[:kmax])}


def dsr(x, n_trials):
    import qbatch_run as QR
    x = np.asarray(pd.Series(x, dtype=float).dropna(), float)
    if len(x) < 12 or x.std(ddof=1) == 0:
        return {"N": n_trials, "dsr": None}
    return QR.dsr(x, n_trials)


# ══════════════════════════════════════════════════════════════════════════
#  사건(final.tests.events)
# ══════════════════════════════════════════════════════════════════════════
def sigma_L(mkt_tr):
    """σ_L = French Mkt TR 월 수익 1927-01~2026-07 표본 표준편차 하나(모든 카드 공통 · 실행 때 한 번)."""
    s = pd.Series(mkt_tr, dtype=float).dropna()
    s = s.loc[in_win(s.index, *SIGMA_L_WIN)]
    if len(s) < 1000:
        raise SystemExit("🚨 σ_L 표본이 %d개월 — French Mkt 가 모자란다" % len(s))
    return float(s.std(ddof=1))


class Events:
    """층 하나의 사건 — 하락월 · CRASH/SURGE-M · 급락 다리 · 반등 · 반등 놓침 달 · 이름 붙은 사건(보고)."""

    def __init__(self, tag, down, crash, surge, legs, rebounds, reb_miss, sigma=None):
        self.tag, self.sigma = tag, sigma
        self._down, self._crash, self._surge = down, crash, surge          # 월 → bool 판정 함수 또는 집합
        self.legs = legs                                                   # [{side, a, b, months}]
        self.rebounds = rebounds                                           # [{a, b, months}]
        self.reb_miss = set(reb_miss)                                      # 급락 저점 뒤 63거래일 안 SURGE-M 달

    def down(self, idx, B=None):
        return self._flag(self._down, idx, B)

    def crash(self, idx, B=None):
        return self._flag(self._crash, idx, B)

    def surge(self, idx, B=None):
        return self._flag(self._surge, idx, B)

    @staticmethod
    def _flag(f, idx, B):
        idx = pd.PeriodIndex(idx)
        if callable(f):
            return np.asarray(f(idx, B), bool)
        return np.array([str(p) in f for p in idx], bool)


def _months_between(a_date, b_date):
    return [str(p) for p in mrange(a_date[:7], b_date[:7])]


def zigzag_legs(dates, prices, start=ZZ_START, end=ZZ_END, hd=ZZ_HD, hu=ZZ_HU, reb_td=ZZ_REB_TD):
    """mech_episodes 지그재그를 그대로 부른다(문턱 · 반등 규약 공유). 돌려주는 것 (legs, rebounds, reb_windows)."""
    import mech_episodes as MEP
    D = list(dates)
    P = [None if (p is None or p != p) else float(p) for p in prices]
    legs, op = MEP.zigzag(D, P, hd, hu, start, end)
    reb = MEP.rebounds(D, P, legs, op, reb_td)
    pos = {d: i for i, d in enumerate(D)}
    L = [{"side": s, "a": a, "b": b, "move": m, "months": _months_between(a, b)} for s, a, b, m, _c in legs]
    Rb = [dict(r, months=_months_between(r["a"], r["b"])) for r in reb]
    win = []
    for l in L:                                          # 반등 놓침 창 — 급락 저점부터 63거래일(반등 길이 규약과 같다)
        if l["side"] != "crash":
            continue
        i = pos[l["b"]]
        e = D[min(i + reb_td, len(D) - 1)]
        win.append(_months_between(l["b"], e))
    return L, Rb, win


def events_L(B, sigma, gspc):
    """L 층 사건 — B(카드 벤치마크) 로 하락월 · CRASH/SURGE-M(σ_L) · ^GSPC 지그재그로 다리 · 반등."""
    Bs = pd.Series(B, dtype=float)
    dates = [d.strftime("%Y-%m-%d") for d in gspc.index]
    legs, reb, win = zigzag_legs(dates, gspc.to_numpy(float))
    surge_set = {str(p) for p, v in Bs.items() if v == v and v >= sigma}
    rm = sorted({m for w in win for m in w if m in surge_set})

    def f_down(idx, _B=None):
        return (Bs.reindex(idx) < 0).to_numpy()

    def f_crash(idx, _B=None):
        return (Bs.reindex(idx) <= -sigma).to_numpy()

    def f_surge(idx, _B=None):
        return (Bs.reindex(idx) >= sigma).to_numpy()
    return Events("L", f_down, f_crash, f_surge, legs, reb, rm, sigma)


def events_S():
    """S 층 사건 — data/mech_episodes.json(동결) 의 달 목록 · 얼린 다리 · 반등. 반등 놓침 창은 bench_px 거래일로 63일."""
    ME = json.load(io.open(os.path.join(DATA, "mech_episodes.json"), encoding="utf-8"))
    BP = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    D = BP["dates"]
    pos = {d: i for i, d in enumerate(D)}
    fz = ME["frozen"]
    legs = [{"side": l["side"], "a": l["a"], "b": l["b"], "move": l["move"], "months": _months_between(l["a"], l["b"])} for l in fz["legs"]]
    reb = [dict(r, months=_months_between(r["a"], r["b"])) for r in fz["rebounds"]]
    surge = set(ME["months"]["surge_m"])
    rm = set()
    for l in legs:
        if l["side"] == "crash" and l["b"] in pos:
            e = D[min(pos[l["b"]] + ZZ_REB_TD, len(D) - 1)]
            rm |= {m for m in _months_between(l["b"], e) if m in surge}
    return Events("S", set(ME["months"]["down_m"]), set(ME["months"]["crash_m"]), surge, legs, reb, sorted(rm),
                  ME.get("sigma_pre"))


# ══════════════════════════════════════════════════════════════════════════
#  보고 묶음 · 관문(final.tests.events.report_bundle · gates)
# ══════════════════════════════════════════════════════════════════════════
def year_table(X, B):
    """해마다 펀드 − 지수(복리) — F_t = B_t + X_t. 무승부 = |차| < 0.5bp.
    G6a 승률은 12개월이 다 찬 달력 해만 센다(창의 첫 해 · 끝 해가 몇 달뿐이면 «해» 가 아니다 — 등록 전 선언 · §4.1).
    부분 해(n < 12)는 "partial" 에 따로 적는다(승 · 패 · 무승부 셈에 넣지 않는다)."""
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
    cut = np.array_split(np.arange(n), 4)
    return [float(x.iloc[c].mean()) for c in cut]


def seg_sum(X, months):
    s = pd.Series(X, dtype=float)
    ks = [per(m) for m in months]
    v = s.reindex(pd.PeriodIndex(ks, freq="M")).dropna()
    return (float(v.sum()), int(len(v))) if len(v) else (None, 0)


def bundle(X, B, ev, dD=None):
    """보고 묶음 — 하락월 · 상승월 · CRASH/SURGE-M · 다리 · 반등 · 이름 사건 · 해마다 · 36개월 음수 비율 · 네 토막 · 우주 단절."""
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
            s, n = seg_sum(X, [str(p) for p in mrange(a, b)])
            if n:
                named["%s %s~%s" % (kind, a, b)] = {"x": s, "n": n}
    yt = year_table(X, Bv)
    r36 = X.rolling(36).sum().dropna()
    brk = {}
    for m in UNIVERSE_BREAKS:
        pre, post = X.loc[idx < per(m)], X.loc[idx >= per(m)]
        brk[m] = [float(pre.mean()) if len(pre) else None, float(post.mean()) if len(post) else None]
    cl = [x for x in legs if x["side"] == "crash"]
    out = {"h1": h1(X), "down": {"n": int(dn.sum()), "mean": mean(dn), "win": (float((xv[dn] > 0).mean()) if dn.any() else None)},
           "up": {"n": int((~dn).sum()), "mean": mean(~dn)},
           "crash_m": {"n": int(cr.sum()), "mean": mean(cr)}, "surge_m": {"n": int(su.sum()), "mean": mean(su)},
           "crash_legs": {"n": len(cl), "mean": (float(np.mean([x["x"] for x in cl])) if cl else None),
                          "won": sum(1 for x in cl if x["x"] > 0), "rows": cl},
           "rebounds": {"n": len(rebs), "mean": (float(np.mean([x["x"] for x in rebs])) if rebs else None),
                        "won": sum(1 for x in rebs if x["x"] > 0), "rows": rebs},
           "named": named, "years": yt, "roll36_neg": (float((r36 < 0).mean()) if len(r36) else None), "blocks4": blocks4(X),
           "universe_breaks": brk}
    if dD is not None:
        d = pd.Series(dD, dtype=float)
        rm = [per(m) for m in ev.reb_miss if per(m) in d.index]
        v = d.reindex(pd.PeriodIndex(rm, freq="M")).dropna() if rm else pd.Series(dtype=float)
        out["rebound_miss"] = {"months": [str(p) for p in v.index], "n": int(len(v)), "mean_dD": (float(v.mean()) if len(v) else None),
                               "applies": bool(len(v) >= REB_MISS_MIN), "ok": (bool(v.mean() >= 0) if len(v) >= REB_MISS_MIN else True)}
    return out


def sync_mask(idx, card_id):
    idx = pd.PeriodIndex(idx)
    m = np.zeros(len(idx), bool)
    for a, b in SYNC_EXCL + SYNC_EXCL_EXTRA.get(card_id, ()):
        m |= in_win(idx, a, b)
    return m


def _pos(v):
    return (v is not None) and v > 0


def _same_sign(v, ref):
    if v is None or ref is None or ref == 0:
        return False
    return (v > 0) == (ref > 0) and v != 0


G5_KEYS = ("a_blocks", "b_out_of_lab", "c_clean", "d_cost2x", "e_turn", "g_sptr", "h_sync")   # f_vintage 는 판별 사전


def _b(v):
    """관문 조건 한 칸 → 파이썬 bool. None(잴 수 없음)은 거짓 — «해당 없음» 은 na 목록으로만 뺀다(적대 검토 2026-09-26:
    numpy bool · None 이 isinstance 거르개에서 조용히 빠져 관문이 꺼지던 것을 막는다)."""
    if v is None:
        return False
    if isinstance(v, (float, np.floating)) and v != v:
        return False
    return bool(v)


def gates(card_id, ev_res):
    """G2~G6(final.tests.gates) — ev_res = {"LR": bundle, "LC": bundle|None, "OOL": bundle|None, "variants": {...},
    "turn_1w": 연 편도 회전(내부 포함), "g4": {이름: bool|None}, "h2": H2 결과|None, "na": {G5 칸 이름 → 사유}}.
    돌려주는 것 {G2..G6, "all"}. 모든 조건은 _b 로 bool 이 된다 — None 은 거짓, 해당 없음은 na 에 적힌 G5 칸뿐
    (c_clean: 청정 창 없는 카드 · g_sptr: French 가 아닌 카드 · e_turn: 회전을 잴 수 없는 제3자 계열 — 카드 spec 이 선언)."""
    LR = ev_res["LR"]
    ref = LR["h1"]["mean"]
    na = dict(ev_res.get("na") or {})
    cm, sm = LR["crash_m"]["mean"], LR["surge_m"]["mean"]
    both = _b(_pos(cm)) and _b(_pos(sm))
    lab2 = "양면" if both else ("급락형" if _b(_pos(cm)) else ("급등형" if _b(_pos(sm)) else "없음"))
    g2 = {"crash_m": cm, "surge_m": sm, "label": lab2, "ok": both}
    if card_id in SWITCHING and "rebound_miss" in LR:
        g2["rebound_miss"] = LR["rebound_miss"]
        g2["ok"] = both and _b(LR["rebound_miss"]["ok"])
    dmean = LR["down"]["mean"]
    g3 = {"down_mean": dmean, "strict": card_id in DEFENSIVE,
          "ok": _b((dmean is not None) and (dmean > 0 if card_id in DEFENSIVE else dmean >= 0))}
    g4 = {k: _b(v) for k, v in (ev_res.get("g4") or {}).items()}
    g4ok = all(g4.values())
    V = ev_res.get("variants") or {}
    b4 = LR["blocks4"]
    g5 = {"a_blocks": _b(sum(1 for v in b4 if _b(_pos(v))) >= 3),
          "b_out_of_lab": (_pos(ev_res["OOL"]["h1"]["mean"]) if ev_res.get("OOL") else None),
          "c_clean": (_pos(ev_res["LC"]["h1"]["mean"]) if ev_res.get("LC") else None),
          "d_cost2x": _pos(V.get("cost2x")),
          "e_turn": ((ev_res["turn_1w"] <= TURN_MAX) if ev_res.get("turn_1w") is not None else None),
          "f_vintage": {k: _b(_same_sign(v, ref)) for k, v in (V.get("vintage") or {}).items() if v is not None},
          "g_sptr": (_same_sign(V.get("sptr"), ref) if V.get("sptr") is not None else None),
          "h_sync": _same_sign(V.get("sync"), ref)}
    for k in G5_KEYS:
        g5[k] = None if k in na else _b(g5[k])
    g5_ok = all(g5[k] for k in G5_KEYS if k not in na) and all(g5["f_vintage"].values())
    yr = LR["years"]
    g6 = {"a_rate": yr["rate"], "a_ok": _b(yr["rate"] is not None and yr["rate"] >= G6A_MIN), "ties": yr["ties"],
          "partial_years": yr.get("partial"), "b_blocks_report": ev_res.get("g6b")}
    return {"G2": g2, "G3": g3, "G4": {"conds": g4, "ok": g4ok}, "G5": dict(g5, ok=g5_ok, na=na), "G6": g6,
            "all": bool(g2["ok"] and g3["ok"] and g4ok and g5_ok and g6["a_ok"])}


def label(card_id, spec, ev_res, G, f0_ok=True):
    """라벨(final.tests.labels) — 표본 안 라벨은 채택이 아니다(채택은 F 층으로만)."""
    if not f0_ok:
        return LABELS["f0"]
    LR = ev_res["LR"]
    if card_id in LAB_OOS_CARDS:
        rep = _pos(ev_res["OOL"]["h1"]["mean"]) if ev_res.get("OOL") else False
        if rep and G["all"]:
            return LABELS["rep_lab"]
    else:
        clean_ok = _pos(ev_res["LC"]["h1"]["mean"]) if ev_res.get("LC") else True
        if _pos(LR["h1"]["mean"]) and G["all"] and clean_ok:
            return LABELS["rep"] if (spec or {}).get("forward_allowed", True) else LABELS["rep_d2"]
    if G["G2"]["label"] in ("급락형", "급등형"):
        return LABELS["one"]
    h2c = {k: v for k, v in G["G4"]["conds"].items() if k.startswith("h2_")}
    if card_id in SWITCHING and h2c and not all(bool(v) for v in h2c.values()):
        return LABELS["mix"]
    return LABELS["none"]


def s_pass(x_gross, x_10, lr_mean, fid):
    """S 층 구현성 — X 점추정 L-R 과 같은 부호 ∧ 10bp 뒤 같은 부호 ∧ 충실도 관문(카드별 · None 이면 보고만)."""
    ok = _same_sign(x_gross, lr_mean) and _same_sign(x_10, lr_mean)
    if fid is not None and fid.get("gate") is not None:
        ok = ok and bool(fid["gate"])
    return bool(ok)


def forward_ok(spec, lab, spass):
    """전방 진입 자격(정보) — 라벨 «재현(전방 대기)» ∧ S 통과 ∧ D1 · D2 승인. D2 가 막은 카드(T02)는 늘 거짓.
    카드 spec 의 forward_block(사유 문자열)이 있으면 거짓 — T15(심리 구성요소를 실시간으로 다시 모으는 경로가 없다 · §1.9 · §4.4)."""
    if not spec.get("forward_allowed", True) or spec.get("forward_block"):
        return False
    return bool(lab in (LABELS["rep"], LABELS["rep_lab"]) and spass)


# ══════════════════════════════════════════════════════════════════════════
#  산출 경계 · 얼린 판 점검(한 번 굽기)
# ══════════════════════════════════════════════════════════════════════════
PREREG = "build/PREREG-2026-09-26-TBATCH.md"
FROZEN = ("build/t_core.py", "build/t_cards.py", "build/t_signals.py", "build/t_pit.py", "build/t_data.py", PREREG,
          "data/_tb_manifest.json", "build/eg30plus.py", "build/qbatch_core.py", "build/qbatch_run.py", "build/mech_episodes.py",
          "build/maxyears.py", "build/pit_panel.py", "build/pit_quarantine.py", "build/tech_backtest.py", "data/mech_episodes.json")
# S 층이 읽는 랩 자료(PIT 가격 · 명단 · 재무 · 사건 · 벤치) — 작업 사본이 등록 커밋의 판과 같아야 굽는다(QBATCH SNAP 과 같은 뜻)
S_FILES = ("data/stocks.json", "data/sd", "data/pit_px.json", "data/fx", "data/fx_pit", "data/index_history.json", "data/index_ledger.json",
           "data/pit_universe.json", "data/pit_reuse.json", "data/splits.json", "data/shares_yf.json", "data/bench_px.json",
           "data/mech_episodes.json", "data/_tb_fred")


def out_path(name="_tbatch.json"):
    """L 층 산출 · 라이선스 파생값은 저장소 밖 캐시에만(D1 · D3) — 저장소 안이면 멈춘다."""
    d = os.path.join(TD._cache_guard(), "out")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def _git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True, encoding="utf-8")


def frozen_check():
    """굽기 전 관문 — TBATCH_COMMIT = 사전등록 문서를 처음 더한 커밋 · origin/main 에 있음 · 얼린 파일이 그 커밋과 같음 · 산출 없음."""
    c = os.environ.get("TBATCH_COMMIT")
    if not c:
        raise SystemExit("🚨 TBATCH_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --blind-smoke 만 된다.")
    full = _git("rev-parse", c + "^{commit}").stdout.strip()
    added = _git("log", "--format=%H", "--diff-filter=A", full, "--", PREREG).stdout.split()
    if not added or added[-1] != full:
        raise SystemExit("🚨 %s 는 사전등록 문서를 처음 더한 커밋이 아니다." % full[:8])
    if _git("merge-base", "--is-ancestor", full, "origin/main").returncode != 0:
        raise SystemExit("🚨 사전등록 커밋이 origin/main 에 없다 — 먼저 푸시.")
    if os.path.exists(out_path()):
        raise SystemExit("🚨 산출물이 이미 있다 — 한 번 굽는 측정이다(다시 굽기는 새 등록).")
    for p in FROZEN:
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True).stdout
        fp = os.path.join(ROOT, p)
        have = open(fp, "rb").read() if os.path.exists(fp) else None
        if have is None or want.replace(b"\r\n", b"\n") != have.replace(b"\r\n", b"\n"):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    if _git("diff", "--quiet", full, "--", *S_FILES).returncode != 0:
        raise SystemExit("🚨 S 층 랩 자료가 등록 커밋의 판과 다르다(%s)." % ", ".join(S_FILES[:4]))
    ok, bad = TD.check_pins()
    if not ok:
        raise SystemExit("🚨 자료 고정본이 명세와 다르다: %s" % "; ".join(bad[:5]))
    if os.environ.get("PYTHONHASHSEED") != "0" or os.environ.get("OPENBLAS_NUM_THREADS") != "1":
        raise SystemExit("🚨 PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 로 돌려라.")
    return full


def js_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if o != o else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.Series):
        return {str(k): (None if v != v else float(v)) for k, v in o.items()}
    if isinstance(o, (pd.Period, pd.Timestamp)):
        return str(o)
    if isinstance(o, set):
        return sorted(o)
    return str(o)


# ══════════════════════════════════════════════════════════════════════════
#  합성 자료 시험 — 실자료를 읽지 않는다
# ══════════════════════════════════════════════════════════════════════════
def _st_costs():
    idx = pd.PeriodIndex(["1975-04", "1975-05", "2000-12", "2001-01", "1926-07"], freq="M")
    assert list(cost_rate(idx)) == [0.005, 0.002, 0.002, 0.001, 0.005]
    assert list(borrow_mask(pd.PeriodIndex(["1982-03", "1982-04"], freq="M"))) == [True, False]
    assert list(cost_rate(idx, flat=0.001)) == [0.001] * 5
    return "비용 시대 경계(1975-04 · 2000-12 끝 달 포함) · 선물 상장 1982-04 · 평탄 비율"


def _st_arm():
    idx = mrange("1990-01", "1990-06")
    R = pd.DataFrame({"B": [0.01, -0.02, 0.03, 0.00, 0.01, -0.01], "D": [0.02, 0.01, -0.01, 0.02, 0.0, 0.01]}, index=idx)
    B = R["B"]
    codes = pd.Series([0, 0, 1, 1, 0, 1], index=idx)
    W = weights_from_codes(codes, {0: {"B": 1.0}, 1: {"D": 1.0}}, ["B", "D"])
    a = arm_weights("sw", W, R, B)
    assert list(a.tf) == [0, 0, 2, 0, 2, 2] and list(a.to) == [0] * 6
    X = a.X()
    want = 0.1 * (a.S - B) - 0.1 * 0.002 * a.tf                   # 1990 = 20bp
    assert np.allclose(X, want)
    assert abs(X.iloc[2] - (0.1 * (-0.01 - 0.03) - 0.1 * 0.002 * 2)) < 1e-15
    # 70/30 흘러간 비중
    W2 = pd.DataFrame({"B": [0.7, 0.7], "D": [0.3, 0.3]}, index=idx[:2])
    a2 = arm_weights("mix", W2, R, B)
    g = np.array([0.7 * 1.01, 0.3 * 1.02])
    drift = g / g.sum()
    assert abs(a2.tf.iloc[1] - np.abs(np.array([0.7, 0.3]) - drift).sum()) < 1e-15
    # 선물 오버레이 · 차입 스프레드(1982-04 이전 매수 쪽만)
    i2 = mrange("1982-02", "1982-05")
    Wo = pd.DataFrame({"B": 1.0, "FUT": [0.5, -0.5, 0.5, 0.5]}, index=i2)
    Ro = pd.DataFrame({"B": [0.01] * 4, "FUT": [0.005] * 4}, index=i2)
    ao = arm_weights("ov", Wo, Ro, Ro["B"], overlay=("FUT",))
    assert list(ao.to) == [0, 1, 1, 0] and list(ao.tf) == [0] * 4 and list(ao.fin) == [0.5, 0, 0.5, 0.5]
    c = ao.cost()
    assert abs(c.iloc[0] - 0.5 * 0.005 / 12) < 1e-15 and abs(c.iloc[3] - 0.0) < 1e-15            # 1982-05 은 스프레드 없음
    assert abs(c.iloc[2] - 0.002 * 1) < 1e-15 and abs(c.iloc[1] - 0.002 * 1) < 1e-15   # 1982-04 부터 스프레드 없음 · 매도 쪽은 늘 없음
    assert abs(ao.turnover_1w() - (0 + 2) / (4 / 12)) < 1e-12
    # 현금 다리는 무비용 — B → 현금 전환은 Σ|Δw| = 1
    Wc = weights_from_codes(pd.Series([0, 1], index=idx[:2]), {0: {"B": 1.0}, 1: {"CASH": 1.0}}, ["B", "CASH"])
    Rc = pd.DataFrame({"B": [0.01, 0.02], "CASH": [0.001, 0.001]}, index=idx[:2])
    ac = arm_weights("cash", Wc, Rc, Rc["B"], costless=("CASH",))
    assert list(ac.tf) == [0, 1]
    # 비중 0 인 다리는 수익 없어도 된다 · 비중 있는 다리가 없으면 그달 없음
    R3 = R.copy()
    R3.loc[idx[0], "D"] = np.nan
    R3.loc[idx[2], "D"] = np.nan
    a3 = arm_weights("gap", W, R3, B)
    assert a3.S.notna().tolist() == [True, True, False, True, True, True] and a3.tf.iloc[3] == 0.0
    # 내부 회전 τ(G5e 순액판)
    cint = a.cost(tau={"D": 2.0}) - a.cost()
    assert abs(cint.iloc[2] - 0.002 * 2 * 2.0 / 12) < 1e-15 and cint.iloc[0] == 0.0
    assert abs(a.X(mult=2.0).iloc[2] - (0.1 * (-0.04) - 0.1 * 2 * 0.004)) < 1e-15
    # 정적 혼합 — 실현 비중 · 흘러간 비중 되돌림
    st = static_mix("st", W, R, B, "1990-01", "1990-06")
    assert abs(st.meta["weights"]["D"] - 0.5) < 1e-15 and st.tf.iloc[0] == 0.0 and st.tf.iloc[1] > 0
    return "팔: X = 0.1(S−B) − 0.1c · 교체 Σ|Δw| = 2 · 흘러간 비중 · 선물 |Δw| · 차입 스프레드 · 현금 무비용 · 공백 · 내부 τ · 정적 혼합"


def _st_shuffle():
    rng = np.random.default_rng(SEED)
    x = np.array([1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0], np.int8)
    import q_switch as QS
    for k in range(50):
        r1, r2 = np.random.default_rng(k), np.random.default_rng(k)
        assert np.array_equal(block_shuffle(x, r1), QS.seg_shuffle(x, r2))
    y = np.array([0, 0, 1, 2, 2, 2, 3, 0, 1, 1, 2, 3, 3, 0, 0, 0, 2])
    rc, L = runs(y)
    for _ in range(200):
        z = block_shuffle(y, rng)
        rc2, L2 = runs(z)
        assert len(z) == len(y) and all((z == s).sum() == (y == s).sum() for s in range(4))
        for s in range(4):
            assert sorted(L2[rc2 == s].tolist()) == sorted(L[rc == s].tolist())
        assert len(rc2) == len(rc)
    a = block_shuffle(y, np.random.default_rng(1))
    b = block_shuffle(y, np.random.default_rng(1))
    assert np.array_equal(a, b)
    return "블록 셔플: 두 상태 = q_switch.seg_shuffle · 네 상태 빈도 · 런 길이(상태별) · 런 수 보존 · 씨앗 재현"


def _st_h2():
    rng = np.random.default_rng(3)
    idx = mrange("1950-01", "2009-12")
    n = len(idx)
    st = np.zeros(n, int)
    k = 0
    while k < n:                                          # 긴 런의 두 상태
        L = int(rng.integers(3, 30))
        st[k:k + L] = rng.integers(0, 2)
        k += L
    B = pd.Series(rng.normal(0.006, 0.04, n), index=idx)
    edge = np.where(st == 1, 0.02, -0.02)                 # 상태가 다리 초과를 알려 준다(정보 있음)
    R = pd.DataFrame({"B": B, "D": B + edge + rng.normal(0, 0.01, n)}, index=idx)
    codes = pd.Series(st, index=idx)
    mp = {0: {"B": 1.0}, 1: {"D": 1.0}}
    r_info = h2_test(codes, mp, R, B, "1950-01", "2009-12", nperm=200)
    assert r_info["delta_obs"] > 0 and r_info["rank"] >= 0.99 and r_info["p"] <= 0.01, r_info
    R2 = pd.DataFrame({"B": B, "D": B + rng.normal(0, 0.01, n)}, index=idx)    # 정보 없음
    r0 = h2_test(codes, mp, R2, B, "1950-01", "2009-12", nperm=200)
    assert 0.0 <= r0["rank"] <= 1.0 and r0["n"] == n
    # 관측 Δ = 팔 계열로 잰 것(창 안 첫 달 매매 0)과 같다
    W = weights_from_codes(codes, mp, ["B", "D"])
    arm = arm_weights("r", W, R, B)
    stm = static_mix("s", W, R, B, "1950-01", "2009-12")
    d = (arm.X() - stm.X()).mean()
    assert abs(d - r_info["delta_obs"]) < 1e-12
    # 씨앗 재현 · 고정 정적 비중(T17 의 50/50)
    r_a = h2_test(codes, mp, R, B, "1950-01", "2009-12", nperm=30)
    r_b = h2_test(codes, mp, R, B, "1950-01", "2009-12", nperm=30)
    assert r_a["draws_hash"] == r_b["draws_hash"] and r_a["p"] == r_b["p"]
    r_f = h2_test(codes, {0: {"B": 0.5, "D": 0.5}, 1: {"B": 0.3, "D": 0.7}}, R, B, "1950-01", "2009-12", nperm=10,
                  static_weights={"B": 0.5, "D": 0.5})
    assert r_f["static_w"] == {"B": 0.5, "D": 0.5}
    return "H2: 정보 있는 상태 → 순위 ≥ 0.99 · 정보 없는 상태 → 순위 [0,1] · 관측 Δ = 팔 계열 Δ · 씨앗 재현 · 고정 정적 비중"


def _st_stats():
    import eg30plus as E
    rng = np.random.default_rng(11)
    x = rng.normal(0.001, 0.01, 300)
    assert nw_t(x, 6) == E.nw_t(x, 6) and nw_t(x, 12) == E.nw_t(x, 12)
    h = h1(pd.Series(x, index=mrange("1990-01", "2014-12")))
    assert abs(h["p"] - norm_sf(h["t"])) < 1e-15 and abs(norm_sf(Z_CRIT) - 0.025) < 1e-12
    s = stouffer({"A": 1.0, "B": 2.0, "C": None}, {})
    assert abs(s["z"] - 3.0 / math.sqrt(3.0)) < 1e-12 and s["t_missing_as_zero"] == ["C"]
    i = mrange("2000-01", "2009-12")
    a = pd.Series(rng.normal(size=len(i)), index=i)
    b = a + 0.0
    c = pd.Series(rng.normal(size=30), index=mrange("2000-01", "2002-06"))
    s2 = stouffer({"A": 2.0, "B": 2.0, "C": 1.0}, {"A": a, "B": b, "C": c})
    assert abs(s2["rho"]["A~B"]["rho"] - 1.0) < 1e-12 and s2["rho"]["A~C"]["rho"] == 0.0
    assert abs(s2["z"] - 5.0 / math.sqrt(3 + 2 * 1.0)) < 1e-12
    bi = by_info({"A": 0.0001, "B": 0.5})
    assert abs(bi["c_m"] - 2.9289682539682538) < 1e-12 and bi["admitted"] == ["A"]
    yi = mrange("1999-07", "2003-02")                                   # 1999 · 2003 은 부분 해(6 · 2개월)
    xv = np.zeros(len(yi))
    for j, p in enumerate(yi):
        xv[j] = {1999: 0.01, 2000: 0.001, 2001: -0.001, 2002: 0.000001, 2003: -0.01}[p.year] / 12.0
    yt = year_table(pd.Series(xv, index=yi), pd.Series(0.0, index=yi))
    assert yt["won"] == 1 and yt["lost"] == 1 and yt["ties"] == [2002] and yt["rate"] == 0.5, yt
    assert yt["partial"] == [1999, 2003] and yt["n_full"] == 3 and yt["years"][1999]["n"] == 6
    assert blocks4(pd.Series(np.arange(8.0), index=mrange("2000-01", "2000-08"))) == [0.5, 2.5, 4.5, 6.5]
    d = dsr(rng.normal(0.002, 0.01, 120), 62)
    assert 0 <= d["dsr"] <= 1
    return "NW = eg30plus.nw_t · p = 1 − Φ(t) · 스타우퍼(t 없음 = 0 · 겹침 < 36 → ρ 0) · BY c(10) · 해마다 무승부 · 네 토막 · DSR"


def _st_events():
    rng = np.random.default_rng(5)
    days = pd.bdate_range("1990-01-01", "1995-12-31")
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, len(days))))
    g = pd.Series(p, index=days)
    idx = mrange("1990-01", "1995-12")
    B = pd.Series(rng.normal(0.005, 0.045, len(idx)), index=idx)
    sig = 0.04
    ev = events_L(B, sig, g.loc["1990-01-01":])
    d = ev.down(idx)
    assert np.array_equal(d, (B < 0).to_numpy()) and np.array_equal(ev.crash(idx), (B <= -sig).to_numpy())
    assert np.array_equal(ev.surge(idx), (B >= sig).to_numpy())
    import mech_episodes as MEP
    D = [x.strftime("%Y-%m-%d") for x in days]
    legs, op = MEP.zigzag(D, list(p), 0.1, 0.1, "1990-01-01", "1995-12-31")
    L2, _, _ = zigzag_legs(D, p, "1990-01-01", "1995-12-31")
    assert [(l["side"], l["a"], l["b"]) for l in L2] == [(s, a, b) for s, a, b, *_ in legs]
    assert all(m in {str(q) for q in idx} for m in ev.reb_miss) and all(B[per(m)] >= sig for m in ev.reb_miss)
    X = pd.Series(rng.normal(0, 0.001, len(idx)), index=idx)
    bd = bundle(X, B, ev, dD=X)
    assert bd["down"]["n"] == int(d.sum()) and len(bd["blocks4"]) == 4 and "rebound_miss" in bd
    sm = sync_mask(mrange("2008-09", "2009-09"), "T01")
    assert sm.tolist() == [False] + [True] * 11 + [False]
    assert sync_mask(pd.PeriodIndex(["2021-06"], freq="M"), "T08").tolist() == [True]
    try:
        sigma_L(pd.Series([0.01] * 10, index=mrange("1927-01", "1927-10")))
        raise AssertionError("짧은 σ_L 이 통과했다")
    except SystemExit:
        pass
    return "사건: 하락 · CRASH/SURGE-M(σ) · 지그재그 = mech_episodes · 반등 놓침 달 ⊂ SURGE-M · 묶음 · 동기 제외(T08 추가) · σ_L 표본 점검"


def _st_gates():
    idx = mrange("2000-01", "2009-12")

    def bd(mean, cm, sm, dmean, blocks, rate):
        return {"h1": {"mean": mean}, "crash_m": {"mean": cm}, "surge_m": {"mean": sm}, "down": {"mean": dmean},
                "blocks4": blocks, "years": {"rate": rate, "ties": []}}
    LR = bd(0.001, 0.002, 0.001, 0.0005, [1, 1, 1, -1], 0.6)
    ev = {"LR": LR, "LC": bd(0.001, 0, 0, 0, [1] * 4, 0.6), "OOL": bd(0.001, 0, 0, 0, [1] * 4, 0.6),
          "variants": {"cost2x": 0.0005, "vintage": {"2024-12": 0.001, "2005-08": None}, "sptr": 0.001, "sync": 0.0008},
          "turn_1w": 3.0, "g4": {"x": True}}
    G = gates("T01", ev)
    assert G["all"] and G["G2"]["label"] == "양면"
    assert label("T01", {}, ev, G) == LABELS["rep"]
    ev2 = dict(ev, LR=bd(0.001, 0.002, -0.001, 0.0005, [1, 1, 1, 1], 0.6))
    G2 = gates("T01", ev2)
    assert not G2["all"] and label("T01", {}, ev2, G2) == LABELS["one"]
    ev3 = dict(ev, g4={"h2_rank_ge90": False})
    assert label("T04", {}, ev3, gates("T04", ev3)) == LABELS["mix"]
    ev4 = dict(ev, LR=bd(0.001, 0.002, 0.001, 0.0, [1, 1, 1, 1], 0.6))
    assert not gates("T04", ev4)["G3"]["ok"] and gates("T01", ev4)["G3"]["ok"]            # 방어 카드는 > 0
    ev5 = dict(ev, turn_1w=12.0)
    assert not gates("T01", ev5)["G5"]["e_turn"]
    assert label("T16", {}, ev, G) == LABELS["rep_lab"] and label("T16", {}, ev, G, f0_ok=False) == LABELS["f0"]
    assert s_pass(0.001, 0.0008, 0.002, {"gate": True}) and not s_pass(0.001, -0.0001, 0.002, None)
    assert not forward_ok({"forward_allowed": False}, LABELS["rep"], True) and forward_ok({}, LABELS["rep"], True)
    assert not forward_ok({"forward_block": "실시간 구성요소 없음"}, LABELS["rep"], True)
    # 형 거르개 — numpy 실수 · numpy bool · None 이 관문을 조용히 끄지 않는다
    evn = dict(ev, variants=dict(ev["variants"], cost2x=np.float64(-0.0005)))
    Gn = gates("T01", evn)
    assert Gn["G5"]["d_cost2x"] is False and not Gn["G5"]["ok"] and not Gn["all"]
    evb = dict(ev, variants=dict(ev["variants"], cost2x=np.float64(0.0005), sync=np.float64(0.0008)), turn_1w=np.float64(3.0),
               g4={"x": np.bool_(True)})
    Gb = gates("T01", evb)
    assert Gb["all"] and all(type(Gb["G5"][k]) is bool for k in G5_KEYS) and type(Gb["G4"]["conds"]["x"]) is bool
    assert not gates("T01", dict(ev, g4={"x": None}))["all"]                  # G4 조건이 None 이면 거짓
    assert not gates("T01", dict(ev, g4={"x": np.bool_(False)}))["all"]
    assert not gates("T01", dict(ev, LC=None))["all"]                         # 청정 창이 없는데 na 선언이 없으면 거짓
    Gna = gates("T12", dict(ev, LC=None, na={"c_clean": "청정 창 없음"}))
    assert Gna["G5"]["c_clean"] is None and Gna["G5"]["ok"]
    assert not gates("T02", dict(ev, turn_1w=None))["G5"]["ok"] and gates("T02", dict(ev, turn_1w=None, na={"e_turn": "잴 수 없음"}))["G5"]["ok"]
    assert gates("T01", dict(ev, variants=dict(ev["variants"], cost2x=float("nan"))))["G5"]["d_cost2x"] is False
    assert label("T02", {"forward_allowed": False}, ev, G) == LABELS["rep_d2"] and label("T01", {"forward_allowed": True}, ev, G) == LABELS["rep"]
    return ("관문 G2~G6 · 라벨(재현 · 랩 표본 밖 · 한쪽형 · 정적 혼합 · 측정 불가 · D2 측정만) · 방어 카드 G3 > 0 · 회전 10배 · S 통과 · D2 · 전방 차단 · "
            "형 거르개(numpy · None · NaN → 거짓 · 해당 없음은 na 로만)")


def _st_windows():
    spec = {"windows": {"full": ("1927-07", "2026-07"), "clean": ("2019-01", "2026-07")}}
    w = layer_windows(spec)
    assert w["S"] == S_WIN and len(mrange(*w["S"])) == 120 and w["L-C"] == ("2019-01", "2026-07")
    try:
        TD.CACHE, old = os.path.join(ROOT, "data", "_x"), TD.CACHE
        try:
            out_path()
            raise AssertionError("저장소 안 산출 경로가 통과했다")
        except SystemExit:
            pass
    finally:
        TD.CACHE = old
    saved = os.environ.pop("TBATCH_COMMIT", None)
    try:
        frozen_check()
        raise AssertionError("TBATCH_COMMIT 없이 굽기가 열렸다")
    except SystemExit:
        pass
    finally:
        if saved is not None:
            os.environ["TBATCH_COMMIT"] = saved
    return "층 창(S = MAX_YEARS × 12) · 산출은 저장소 밖만 · 등록 커밋 없이 굽기 닫힘"


def _st_static():
    import ast
    bad = []
    for fn in ("t_core.py",):
        src = io.open(os.path.join(HERE, fn), encoding="utf-8").read()
        for nd in ast.walk(ast.parse(src)):
            if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id == "open":
                if any(kw.arg == "encoding" for kw in nd.keywords):
                    continue
                mode = nd.args[1].value if len(nd.args) > 1 and isinstance(nd.args[1], ast.Constant) else ""
                if "b" not in str(mode):
                    bad.append("%s:%d" % (fn, nd.lineno))
    assert not bad, bad
    return "open() encoding 정적 점검"


def selftest():
    res, ok = [], True
    for fn in (_st_costs, _st_arm, _st_shuffle, _st_h2, _st_stats, _st_events, _st_gates, _st_windows, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            import traceback
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("t_core selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
