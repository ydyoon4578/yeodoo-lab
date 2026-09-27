# -*- coding: utf-8 -*-
"""build/x_signals.py — 배치 X 신호 층: X-BEAR(주 가설) · COMP · CRED · VTS · COMP-W · RRSHOCK · GVTREND · JM · 쌍둥이(200일선 · 변동성 · Nagel).

설계 원본(구속): xbatch_research.json signals · combiner · action(APP) · evaluation.M_market_20y.controls · rule_20y_compliance ·
  decisions SN-1.1 ~ SN-1.5 · D-8 · UF-7 — 저장소 밖 스크래치. 이 파일은 설계를 다시 짓지 않는다. 옮기는 것은 정의 · 상수 · 가용 늦춤뿐이다.

규약(명세 그대로)
  결정      달 t 의 마지막 NYSE 거래일 d_t 종가(x_data.decision_days) · 체결 T+1 종가(평가 층의 몫) · 보유 = 다음 T+1 까지.
  r^e_t     SPY TR(수정종가) 달 수익(d_{t−1} 종가 → d_t 종가) − rf_t · rf_t = DGS3MO(t−1 월평균)/12(x_data.rf_us_monthly) — 결정 d_t 에 다 관측된다.
  X-BEAR    a_t = 1[(1/12)·Σ_{j=0}^{11} r^e_{t−j} < 0 ∧ r^e_t < 0] — 상수 12 · 1 · 0(GHM 2023 · 자유 모수 0) · 워밍업 2005-09 ~ 2006-08 · 첫 결정 2006-08.
  GHM 상태  SLOW = 12개월 평균 · FAST = 이번 달: Bull(≥ · ≥) · Correction(≥ · <) · Bear(< · <) · Rebound(< · ≥).
  X-CRED    BAA10Y(d_t − 1 영업일) > 그 날 앞 365 달력일(그 날 포함) 관측의 중앙값 → 1 — 관측 수가 아니라 날짜 창(채권 휴장일).
  X-VTS     VIX/VIX3M ≥ 1.0 → 1 · 공표일(x_data.vxv_pub_date · 기본 2009-09-18) 전 0 · T1 행 d_t 값 · D0 행 d_t − 1 거래일 값(SN-1.2) ·
            선언 V1: 그 지평의 날에 한쪽이 비면 두 값이 함께 선 마지막 날(빈칸 없음 · 결과를 보기 전에 정함).
            🔎 lit_open: 단독 측정 팔은 삭제(Fassas–Hourvouliades 2019 역행) — COMP 성분으로만 남는다(ARM_STATUS).
  X-COMP    k = BEAR + CRED + VTS · s = clip((k − 1)/2, 0, 1) ∈ {0, ½, 1} · Rebound 차단기: SLOW < 0 ∧ FAST ≥ 0 이면 0.
  X-RRSHOCK DFII10(d_t − 1 영업일) − DFII10(그 날 앞 63거래일) ≥ +0.20%p → 1(BMROT 고정 상수) · 🔎 lit_open: 쌍둥이(보고만).
  X-GVTREND IVW/IVE 252거래일 TR 비 < 1 → 1 · 첫 결정 2006-12(SN-1.5).
  X-COMP-W  금요일(그 주 마지막 거래일) 종가 판정 · SLOW = 252거래일 초과 합 · FAST = 21거래일 초과 합 · CRED · VTS 같은 날 · 차단기 같음 ·
            다음 거래일 종가 체결(그 다음 날부터 보유) — 일간 위치 계열.
  X-JM      얼린 q_jump(λ 50 · K 2 · DD10 · SOR20 · SOR60 · fit_jm · online_final)을 창 안 확장 표본(첫 특징일 ~ 적합 전날 · 최소 756 · 최대 3000 거래일)에
            1 · 7월 첫 거래일마다 적합 · 온라인 DP 로 날마다 상태 · 월말 d_t 상태가 BEAR 면 a = 1 · 첫 적합 전 NaN(활성 월만 보고).
            특징 입력 R_d = SPY TR 일간 − rf_d · rf_d = rf_u(그 거래일 달 u · x_data.rf_us_monthly = DGS3MO(u−1 월평균)/12)의 그달 거래일 수 복리 분할
            (q_jump.excess_returns 의 «끝난 달 값» 시점 규율과 같은 뜻 · 🚨 20년 규칙: 2005-09 거래일부터 — 2005-08 rf 를 쓰지 않는다).
  쌍둥이    200일선: ^GSPC 종가 < 200일 SMA(그날 포함) → 1 · 평균 노출 ā 로 척도(상한 1 · 못 맞추면 척도 1 과 ā 비 보고).
            변동성: SPY 63일 실현변동성(일간 단순수익 sd · 그날 포함) ≥ 창 안 확장 분위수(수준 1 − ā · 결정 달 표본) → 1(q_switch.vol_state_monthly 의 뜻).
            Nagel(BLR 대조): z = −(12개월 초과 합)/(σ̂₆₃·√21·√12) · s = clip(z/z*, 0, 1) · z* 는 BLR 활성 달 평균 노출에 맞춘다(이분법).
  APP       a = a_unit × APP_t · APP_t = 1[β̂_C − β̂_D ≥ 0.10](결정 시점) — M · I 층은 코어가 없어 적용하지 않는다(G · S 층은 x_eval · x_adapter 가 β̂ 를 준다).

🚨 20년 규칙: 입력은 x_data 창 로더(≥ 2005-08-01 · ≤ bake_end)만 · signal_frame 이 assert_input_floor · assert_first_active 를 다시 건다.
🚨 신호 층 입력에 EG30 산출 · French · ^SP500TR 없음(x_data.install_read_guard(signal_layer=True) · 가용 표가 French 를 신호 입력으로 거부).
🚨 이 파일은 수익 · 통계를 계산하지 않는다 — 상태(0/½/1) 계열만 낸다. --selftest 는 합성 자료만.

  python build/x_signals.py --selftest
  python build/x_signals.py --lookahead-real     실자료 선견 점검(결정 해시만 · 참/거짓 · 개수 — 신호 층 읽기 가드 안) → 캐시 meta/_lookahead_x_signals.json
"""
from __future__ import annotations

import io
import json
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
import x_data as XD                     # noqa: E402

# ══════════════════════════════════════════════════════════════════════════
#  등록 상수(명세 signals · combiner · action — 결과를 본 뒤 바꾸지 않는다)
# ══════════════════════════════════════════════════════════════════════════
BEAR_SLOW, BEAR_FAST, BEAR_THR = 12, 1, 0.0          # GHM 2023 JFE — SLOW 12개월 산술평균 · FAST 1개월 · 문턱 0
APP_MIN = 0.10                                         # APP: β̂_C − β̂_D < 0.10 이면 a = 0
CRED_DAYS = 365                                        # 달력일 창(관측 수가 아니다)
VTS_THR = 1.0
RR_TD, RR_THR = 63, 0.20                               # BMROT 고정 상수(%p)
GV_TD = 252
GV_FIRST = "2006-12"                                   # SN-1.5
SMA_N, VOL_N = 200, 63
VOL_MIN_OBS = 12                                       # 변동성 쌍둥이 확장 분위수 최소 표본(결정 달) — 그 전 0(선언)
CW_SLOW, CW_FAST = 252, 21                             # COMP-W
JM_MIN, JM_MAX = 756, 3000                             # 창 안 확장 학습 길이(거래일)
JM_FIT_MONTHS = ("01", "07")
Q_JUMP_BLOB = "b55652b5bf2db83e28e9e54480aa6254d20ffb95"
ARM_STATUS = {                                         # lit_open.json(자료 단계 · 2026-09-27) 판정 — 등록 문서에 옮긴다
    "X-BEAR": "primary",
    "X-COMP": "measure", "X-CRED": "measure", "X-BLR": "measure", "X-JM": "measure", "X-COMP-W": "measure",
    "X-VTS": "dropped",                                # Fassas–Hourvouliades 2019 역행 → 단독 팔 삭제(COMP 성분으로만)
    "X-GVTREND": "measure_FG",                         # F_G = {X-GVTREND}(m = 1)
    "X-RRSHOCK": "twin",                               # Weber 2018 열림 · 등록 상태 변수 결과 없음 · DSS 초록만 → 쌍둥이(F_G 밖)
}
M_BY_FAMILY = ("X-COMP", "X-CRED", "X-BLR", "X-JM", "X-COMP-W")   # M 층 측정 팔 BY q 0.10 가족(VTS 삭제)
FG_FAMILY = ("X-GVTREND",)
GHM_STATES = ("Bull", "Correction", "Bear", "Rebound")


# ══════════════════════════════════════════════════════════════════════════
#  달 수익 · BEAR · GHM 상태
# ══════════════════════════════════════════════════════════════════════════
def _ts(x):
    return pd.Timestamp(x)


def month_closes(px, dd):
    """결정 달 t → d_t 이하 마지막 종가(d_t 가 그달 마지막 거래일이라 그달 끝 종가). 그달 안 종가가 없으면 NaN. 색인 = dd.index(Period)."""
    px = px.dropna()
    pv, pi = px.to_numpy(float), px.index
    j = pi.searchsorted(pd.DatetimeIndex(dd.to_numpy()), side="right") - 1
    out = np.full(len(dd), np.nan)
    for n, (t, jj) in enumerate(zip(dd.index, j)):
        if jj >= 0 and pi[jj].to_period("M") == t:           # 그달 안의 종가만(앞 달 종가로 채우지 않는다)
            out[n] = pv[jj]
    return pd.Series(out, index=dd.index, name="close")


def monthly_excess(spy, rf, dd):
    """r^e_t = SPY TR(d_{t−1} → d_t) − rf_t — 색인 결정 달 t(두 번째 달부터) · rf 는 달(Period) 색인(x_data.rf_us_monthly)."""
    c = month_closes(spy, dd)
    r = c / c.shift(1) - 1.0
    rf_t = pd.Series(rf, dtype=float).reindex(dd.index)
    re = (r - rf_t).iloc[1:]
    re.name = "re"
    return re


def bear_state(re):
    """X-BEAR a_t(0/1 · 12개월 창이 차기 전 NaN) — re 는 연속 달(Period) 색인."""
    re = pd.Series(re, dtype=float)
    _assert_contiguous(re.index)
    slow = re.rolling(BEAR_SLOW, min_periods=BEAR_SLOW).mean()
    fast = re.rolling(BEAR_FAST, min_periods=BEAR_FAST).mean()
    a = ((slow < BEAR_THR) & (fast < BEAR_THR)).astype(float)
    a[slow.isna() | fast.isna()] = np.nan
    a.name = "X-BEAR"
    return a


def ghm_state(re):
    re = pd.Series(re, dtype=float)
    slow = re.rolling(BEAR_SLOW, min_periods=BEAR_SLOW).mean()
    out = pd.Series(None, index=re.index, dtype=object)
    for t in re.index:
        s, f = slow.get(t), re.get(t)
        if s is None or f is None or not (np.isfinite(s) and np.isfinite(f)):
            continue
        out[t] = ("Bull" if f >= 0 else "Correction") if s >= 0 else ("Rebound" if f >= 0 else "Bear")
    return out


def slow_fast(re):
    re = pd.Series(re, dtype=float)
    return re.rolling(BEAR_SLOW, min_periods=BEAR_SLOW).mean(), re


def _assert_contiguous(idx):
    if len(idx) > 1:
        p = pd.PeriodIndex(idx, freq="M")
        n = (p[-1] - p[0]).n + 1
        if n != len(p) or not p.is_monotonic_increasing:
            raise AssertionError("달 색인이 연속이 아니다(%d ≠ %d)" % (n, len(p)))


# ══════════════════════════════════════════════════════════════════════════
#  측정 팔 성분(결정일마다 가용 지평에서 자른다)
# ══════════════════════════════════════════════════════════════════════════
def _last_le(s, c):
    s = s.dropna()
    j = s.index.searchsorted(_ts(c), side="right") - 1
    return (float(s.iloc[j]), s.index[j]) if j >= 0 else (None, None)


def _cred_window_full(baa, dv):
    """365일 워밍업(명세 rule_20y_compliance «CRED 365일»): 계열 첫 관측이 창 시작 + 3일(주말) 안이어야 창이 찬 것으로 본다(그 전 NaN)."""
    return len(baa) and baa.index[0] <= dv - pd.Timedelta(days=CRED_DAYS) + pd.Timedelta(days=3)


def cred_state(baa, dd, mode="T1"):
    """X-CRED — BAA10Y(가용 마지막 · d − 1 영업일) > 그 날 앞 365 달력일(포함) 관측 중앙값 · 창이 차기 전 NaN."""
    baa = pd.Series(baa, dtype=float).dropna()
    out = {}
    for t, d in dd.items():
        c = XD.cutoff("fred_d", d, mode)
        v, dv = _last_le(baa, c)
        if v is None or not _cred_window_full(baa, dv):
            out[t] = np.nan
            continue
        w = baa.loc[(baa.index > dv - pd.Timedelta(days=CRED_DAYS)) & (baa.index <= dv)]
        out[t] = float(v > float(w.median())) if len(w) else np.nan
    return pd.Series(out, dtype=float, name="X-CRED")


def credit_level(baa, dd, mode="T1"):
    """X-BLR CREDIT = BAA10Y − 중앙₃₆₅ₐ(%p) — 같은 가용 지평."""
    baa = pd.Series(baa, dtype=float).dropna()
    out = {}
    for t, d in dd.items():
        c = XD.cutoff("fred_d", d, mode)
        v, dv = _last_le(baa, c)
        if v is None or not _cred_window_full(baa, dv):
            out[t] = np.nan
            continue
        w = baa.loc[(baa.index > dv - pd.Timedelta(days=CRED_DAYS)) & (baa.index <= dv)]
        out[t] = float(v - float(w.median()))
    return pd.Series(out, dtype=float, name="CREDIT")


def vts_ratio(vix, vix3m, pub=None):
    """VIX/VIX3M 비 — 두 값이 모두 선 날만(공표일 앞 VIX3M 은 버린다). 결정일마다 가용 지평 안의 마지막 공통 관측을 쓴다(선언 V1)."""
    pub = _ts(pub or XD.vxv_pub_date())
    vix = pd.Series(vix, dtype=float).dropna()
    v3 = pd.Series(vix3m, dtype=float).dropna()
    v3 = v3.loc[(v3.index >= pub) & (v3 > 0)]
    idx = vix.index.intersection(v3.index)
    return (vix.reindex(idx) / v3.reindex(idx)).sort_index()


def vts_state(vix, vix3m, dd, mode="T1", pub=None):
    """X-VTS — VIX/VIX3M ≥ 1.0 → 1 · 공표일 전 0 · 비는 가용 지평(T1 d_t · D0 d_t − 1 거래일) 안의 마지막 공통 관측
    (선언 V1: 그날 한쪽이 비면 두 값이 함께 선 마지막 날 · 공표 뒤에도 아직 공통 관측이 없으면 0)."""
    pub = _ts(pub or XD.vxv_pub_date())
    ratio = vts_ratio(vix, vix3m, pub)
    out = {}
    for t, d in dd.items():
        c = XD.cutoff("vix", d, mode)
        if _ts(c) < pub:
            out[t] = 0.0
            continue
        v, _dv = _last_le(ratio, c)
        out[t] = 0.0 if v is None else float(v >= VTS_THR)
    return pd.Series(out, dtype=float, name="X-VTS")


def fear_level(vix, dd, mode="T1"):
    """X-BLR FEAR = ln VIX_c − ln 중앙값(마지막 252 VIX 관측 · c 포함)."""
    vix = pd.Series(vix, dtype=float).dropna()
    out = {}
    for t, d in dd.items():
        c = XD.cutoff("vix", d, mode)
        j = vix.index.searchsorted(_ts(c), side="right")
        w = vix.iloc[max(0, j - 252):j]
        if len(w) < 252:
            out[t] = np.nan
            continue
        v, md = float(w.iloc[-1]), float(w.median())
        out[t] = float(math.log(v) - math.log(md)) if (v > 0 and md > 0) else np.nan   # VIX 는 늘 양(0 이하 관측은 쓰지 않는다)
    return pd.Series(out, dtype=float, name="FEAR")


def comp_state(bear, cred, vts, re):
    """X-COMP s = clip((BEAR + CRED + VTS − 1)/2, 0, 1) · 차단기(SLOW < 0 ∧ FAST ≥ 0 → 0)."""
    idx = pd.Series(bear).index
    b, c, v = (pd.Series(x, dtype=float).reindex(idx) for x in (bear, cred, vts))
    slow, fast = slow_fast(pd.Series(re, dtype=float).reindex(idx))
    k = b + c + v
    s = ((k - 1.0) / 2.0).clip(0.0, 1.0)
    s[(slow < 0) & (fast >= 0)] = 0.0
    s[b.isna() | c.isna() | v.isna()] = np.nan
    s.name = "X-COMP"
    return s


def rrshock_state(dfii, dd, tdays, mode="T1"):
    """X-RRSHOCK — DFII10(c) − DFII10(c 앞 63거래일 날 이하 마지막) ≥ 0.20 → 1 · c = d − 1 영업일."""
    dfii = pd.Series(dfii, dtype=float).dropna()
    tdays = pd.DatetimeIndex(tdays)
    out = {}
    for t, d in dd.items():
        c = XD.cutoff("fred_d", d, mode)
        v, _ = _last_le(dfii, c)
        j = tdays.searchsorted(_ts(c), side="right") - 1
        if v is None or j - RR_TD < 0:
            out[t] = np.nan
            continue
        v0, _ = _last_le(dfii, tdays[j - RR_TD])
        out[t] = np.nan if v0 is None else float((v - v0) >= RR_THR - 1e-12)
    return pd.Series(out, dtype=float, name="X-RRSHOCK")


def gvtrend_state(ivw, ive, dd, first=GV_FIRST):
    """X-GVTREND — (IVW_d/IVW_{d−252})/(IVE_d/IVE_{d−252}) < 1 → 1 · 첫 결정 2006-12 전 NaN."""
    ivw, ive = pd.Series(ivw, dtype=float).dropna(), pd.Series(ive, dtype=float).dropna()
    out = {}
    for t, d in dd.items():
        if t < pd.Period(first, "M"):
            out[t] = np.nan
            continue
        ja = ivw.index.searchsorted(_ts(d), side="right")
        jb = ive.index.searchsorted(_ts(d), side="right")
        if ja - 1 - GV_TD < 0 or jb - 1 - GV_TD < 0:
            out[t] = np.nan
            continue
        ra = ivw.iloc[ja - 1] / ivw.iloc[ja - 1 - GV_TD]
        rb = ive.iloc[jb - 1] / ive.iloc[jb - 1 - GV_TD]
        out[t] = float(ra / rb < 1.0)
    return pd.Series(out, dtype=float, name="X-GVTREND")


# ══════════════════════════════════════════════════════════════════════════
#  쌍둥이(대조군 — 채택 경로 없음)
# ══════════════════════════════════════════════════════════════════════════
def sma200_state(gspc, dd):
    """^GSPC 종가 < 200일 SMA(그날 포함) → 1(수비) · 창이 차기 전 NaN."""
    g = pd.Series(gspc, dtype=float).dropna()
    out = {}
    for t, d in dd.items():
        j = g.index.searchsorted(_ts(d), side="right")
        if j < SMA_N:
            out[t] = np.nan
            continue
        w = g.iloc[j - SMA_N:j].to_numpy(float)
        out[t] = float(w[-1] < w.mean())
    return pd.Series(out, dtype=float, name="T-SMA200")


def vol63(spy, dd):
    """SPY 63일 실현변동성(일간 단순수익 표본 sd · d 포함 · 연율 아님) — q_switch.vol63 의 뜻."""
    p = pd.Series(spy, dtype=float).dropna()
    r = p / p.shift(1) - 1.0
    out = {}
    for t, d in dd.items():
        j = r.index.searchsorted(_ts(d), side="right")
        w = r.iloc[max(0, j - VOL_N):j].dropna()
        out[t] = float(np.std(w.to_numpy(float), ddof=1)) if len(w) >= VOL_N else np.nan
    return pd.Series(out, dtype=float, name="vol63")


def vol_twin(vol, abar, min_obs=VOL_MIN_OBS):
    """변동성 쌍둥이 — vol_t ≥ 확장 분위수({vol_s : s ≤ t}, 수준 1 − ā) → 1 · 표본 < min_obs 이면 0."""
    v = pd.Series(vol, dtype=float)
    out = {}
    hist = []
    q_lvl = float(np.clip(1.0 - abar, 0.0, 1.0))
    for t, x in v.items():
        if not np.isfinite(x):
            out[t] = np.nan
            continue
        hist.append(x)
        if len(hist) < min_obs:
            out[t] = 0.0
            continue
        out[t] = float(x >= float(np.quantile(np.asarray(hist), q_lvl)))
    return pd.Series(out, dtype=float, name="T-VOL")


def scale_to_mean(state, abar, mask=None):
    """평균 노출 ā 로 맞춘 척도 k·state(상한 k ≤ 1/max) — 돌려주는 것 (계열, k, 맞춤 여부)."""
    s = pd.Series(state, dtype=float)
    ss = s if mask is None else s[mask]
    m = float(ss.mean()) if ss.notna().any() else 0.0
    if m <= 0:
        return s * 0.0, 0.0, False
    k = abar / m
    ok = True
    if k > 1.0:
        k, ok = 1.0, False
    return s * k, float(k), ok


def nagel_z(re, spy, dd):
    """Nagel 쌍둥이 z_t = −(Σ_{12} r^e)/(σ̂₆₃·√21·√12) — σ̂₆₃ = SPY 63일 일간 수익 sd."""
    re = pd.Series(re, dtype=float)
    s12 = re.rolling(12, min_periods=12).sum()
    v = vol63(spy, dd).reindex(re.index)
    z = -s12 / (v * math.sqrt(21.0) * math.sqrt(12.0))
    z.name = "nagel_z"
    return z


def nagel_twin(z, target_mean, mask=None, iters=200):
    """s = clip(z/z*, 0, 1) · z* > 0 은 mask 달 평균 노출 = target_mean 이 되게(이분법). target ≤ 0 이거나 z 가 모두 ≤ 0 이면 0."""
    z = pd.Series(z, dtype=float)
    zz = z if mask is None else z[mask]
    zz = zz.dropna()
    if target_mean <= 0 or not (zz > 0).any():
        return z * 0.0, None
    f = lambda zs: float(np.clip(zz.to_numpy() / zs, 0.0, 1.0).mean())
    lo, hi = 1e-9, max(1e-6, float(zz.max()) * 1e6)
    if f(lo) < target_mean:                               # 켜질 수 있는 몫의 최대(z > 0 몫)보다 크면 z* → 0
        zs = lo
    else:
        for _ in range(iters):
            mid = math.sqrt(lo * hi)
            if f(mid) > target_mean:
                lo = mid
            else:
                hi = mid
        zs = math.sqrt(lo * hi)
    return (z / zs).clip(0.0, 1.0), zs


# ══════════════════════════════════════════════════════════════════════════
#  X-COMP-W(주별 · 일간 위치)
# ══════════════════════════════════════════════════════════════════════════
def daily_excess(spy, rf):
    """일간 초과 R_d = SPY TR 일간 − rf_d · rf_d = rf_u(그 날의 달 u)를 그달 거래일 수로 복리 분할(달력은 미리 안다) · 첫 달 u < 2005-09 는 NaN."""
    p = pd.Series(spy, dtype=float).dropna()
    r = p / p.shift(1) - 1.0
    per = p.index.to_period("M")
    cnt = pd.Series(1, index=p.index).groupby(per).transform("sum")
    rfu = pd.Series(rf, dtype=float).reindex(per).to_numpy(float)
    rf_d = (1.0 + rfu) ** (1.0 / cnt.to_numpy(float)) - 1.0
    out = pd.Series(r.to_numpy(float) - rf_d, index=p.index, name="re_d")
    return out


def week_ends(tdays, first=None, last=None):
    """그 주(월~일)의 마지막 거래일 — 금요일 휴장이면 목요일."""
    td = pd.DatetimeIndex(tdays)
    wk = td.to_period("W-SUN")
    s = pd.Series(td, index=td).groupby(wk).max()
    out = pd.DatetimeIndex(s.to_numpy())
    if first is not None:
        out = out[out >= _ts(first)]
    if last is not None:
        out = out[out <= _ts(last)]
    return out


def comp_w_positions(spy, rf, baa, vix, vix3m, tdays, first_day, last_day, pub=None):
    """X-COMP-W 일간 위치 a_d(체결 다음 날부터) — 판정일 f(주 마지막 거래일) · 체결 = f 다음 거래일 종가 · 보유 = 그 다음 날부터.
    돌려주는 것 (pos Series(거래일 · first_day ~ last_day), decisions DataFrame(판정일 · slow · fast · bear · cred · vts · s))."""
    pub = _ts(pub or XD.vxv_pub_date())
    td = pd.DatetimeIndex(tdays)
    re_d = daily_excess(spy, rf)
    wd = week_ends(td, first=td[0] + pd.Timedelta(days=380), last=last_day)
    baa = pd.Series(baa, dtype=float).dropna()
    ratio = vts_ratio(vix, vix3m, pub)
    rows = {}
    cs = re_d.fillna(np.nan)
    for f in wd:
        j = cs.index.searchsorted(f, side="right")
        w252 = cs.iloc[max(0, j - CW_SLOW):j]
        w21 = cs.iloc[max(0, j - CW_FAST):j]
        if len(w252) < CW_SLOW or w252.isna().any():
            continue
        slow, fast = float(w252.sum()), float(w21.sum())
        bear = float(slow < 0 and fast < 0)
        c = XD.cutoff("fred_d", f, "T1")
        v, dv = _last_le(baa, c)
        if v is None or not _cred_window_full(baa, dv):
            continue
        ww = baa.loc[(baa.index > dv - pd.Timedelta(days=CRED_DAYS)) & (baa.index <= dv)]
        cred = float(v > float(ww.median()))
        if f < pub:
            vts = 0.0
        else:
            v, _dv = _last_le(ratio, f)
            vts = 0.0 if v is None else float(v >= VTS_THR)
        k = bear + cred + vts
        s = float(np.clip((k - 1.0) / 2.0, 0.0, 1.0))
        if slow < 0 and fast >= 0:
            s = 0.0
        rows[f] = {"slow": slow, "fast": fast, "bear": bear, "cred": cred, "vts": vts, "s": s}
    dec = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    days = td[(td >= _ts(first_day)) & (td <= _ts(last_day))]
    pos = pd.Series(np.nan, index=days, name="X-COMP-W")
    # 판정 f → 체결 e = f 다음 거래일 → 보유 e 다음 거래일부터
    eff = {}
    for f, r in dec.iterrows():
        j = td.searchsorted(f, side="right")
        if j + 1 < len(td):
            eff[td[j + 1]] = r["s"]
    es = pd.Series(eff).sort_index()
    if len(es):
        pos = es.reindex(td).ffill().reindex(days)
    return pos, dec


# ══════════════════════════════════════════════════════════════════════════
#  X-JM(얼린 q_jump 원시 함수만 부른다)
# ══════════════════════════════════════════════════════════════════════════
_QJ = None


def _q_jump():
    global _QJ
    if _QJ is None:
        XD.assert_blob("q_jump", Q_JUMP_BLOB)
        import q_jump as _m                                    # noqa: E402 — blob 단언 뒤에만
        _QJ = _m
    return _QJ


def jm_features(re_d, QJ=None):
    """(R, X) — q_jump.features 와 같은 식(DD10 = √EWM10[R²·1{R<0}] · SOR20/SOR60 = EWM[R]/√EWM[R²·1{R<0}]) · 얼린 q_jump.ewm 을 부른다.
    R 은 창 안 일간 초과(첫 값부터) — 창 앞 굴림 없음."""
    QJ = QJ or _q_jump()
    r = pd.Series(re_d, dtype=float).dropna()
    x = r.to_numpy(float)
    neg2 = np.where(x < 0, x * x, 0.0)
    cols = []
    for nm, h in QJ.HL:
        if nm.startswith("DD"):
            cols.append(np.sqrt(QJ.ewm(neg2, h)))
        else:
            with np.errstate(divide="ignore", invalid="ignore"):
                cols.append(QJ.ewm(x, h) / np.sqrt(QJ.ewm(neg2, h)))
    X = np.column_stack(cols)
    return r, pd.DataFrame(X, index=r.index, columns=[nm for nm, _ in QJ.HL])


def jm_daily_states(re_d, first_fit=None, QJ=None, lam=None, wmin=JM_MIN, wmax=JM_MAX):
    """얼린 fit_jm · online_final 로 날마다 상태(1 BULL · 0 BEAR) — 적합 = 1 · 7월 첫 거래일(학습 길이 ≥ wmin) · 학습 = 첫 특징일 ~ 전날(최대 wmax).
    돌려주는 것 (states Series(적합일부터), log[적합 기록 — 수익 없음])."""
    QJ = QJ or _q_jump()
    lam = QJ.LAM if lam is None else lam
    R, Xdf = jm_features(re_d, QJ)
    ok = np.isfinite(Xdf.to_numpy()).all(1)
    f0 = int(np.argmax(ok)) if ok.any() else len(ok)
    dates = Xdf.index
    X = Xdf.to_numpy(float)
    Rv = R.to_numpy(float)
    fits, seen = [], set()
    for i, d in enumerate(dates):
        ym = d.strftime("%Y-%m")
        if d.strftime("%m") in JM_FIT_MONTHS and ym not in seen and i - f0 >= wmin:
            seen.add(ym)
            fits.append(i)
    if first_fit is not None:
        fits = [i for i in fits if dates[i] >= _ts(first_fit)]
    states = pd.Series(np.nan, index=dates, name="jm_bull")
    log = []
    for q, f in enumerate(fits):
        a = max(f0, f - wmax)
        L = f - a
        Xt = X[a:f]
        mu, sd = Xt.mean(0), Xt.std(0)
        f_next = fits[q + 1] if q + 1 < len(fits) else len(dates)
        days = np.arange(f, f_next)
        rec = {"fit": str(dates[f].date()), "train": [str(dates[a].date()), str(dates[f - 1].date())], "L": int(L)}
        if not (np.all(sd > 0) and np.isfinite(Xt).all()):
            states.iloc[days] = 1.0
            rec["fail"] = "표준화 불가"
            log.append(rec)
            continue
        Z = (Xt - mu) / sd
        best, objs, iters = QJ.fit_jm(Z, lam=lam)
        S = best["S"]
        occ = [int((S == k).sum()) for k in range(QJ.K)]
        if min(occ) == 0:
            states.iloc[days] = 1.0
            rec["fail"] = "한 국면만 선 해(퇴화)"
            log.append(rec)
            continue
        cum = [float(np.prod(1 + Rv[a:f][S == k]) - 1) for k in range(QJ.K)]
        bull = int(np.argmax(cum))
        Zall = (X - mu) / sd
        fin = QJ.online_final(Zall, best["theta"], lam, days, L)
        states.iloc[days] = np.where(fin == bull, 1.0, 0.0)
        rec.update({"best_j": int(best["j"]), "occ": occ, "n_days": int(len(days))})
        log.append(rec)
    return states, log


def jm_monthly(states, dd):
    """월말 d_t 상태 → a_t = 1[BEAR] · 첫 적합 전 NaN."""
    s = pd.Series(states, dtype=float)
    out = {}
    for t, d in dd.items():
        j = s.index.searchsorted(_ts(d), side="right") - 1
        v = s.iloc[j] if j >= 0 else np.nan
        out[t] = np.nan if (j < 0 or not np.isfinite(v)) else float(v == 0.0)
    return pd.Series(out, dtype=float, name="X-JM")


# ══════════════════════════════════════════════════════════════════════════
#  I 층 — 시장마다 같은 BEAR(12 · 1 · 0)
# ══════════════════════════════════════════════════════════════════════════
def bear_panel(views):
    """views = x_intl.primary_view(...) {cc: DataFrame(re_sig · re_hold · down · tr)} → {cc: a_t(결정 달 t · 워밍업 NaN)}."""
    return {cc: bear_state(v["re_sig"]) for cc, v in views.items()}


# ══════════════════════════════════════════════════════════════════════════
#  신호 표(실자료 — x_data 창 로더) · 20년 단언
# ══════════════════════════════════════════════════════════════════════════
def calendar(first=XD.INPUT_MIN_MONTH, last=XD.SCORE_LAST):
    return XD.decision_days(first, last)


def signal_frame(I=None, mode="T1", with_jm=True, dd=None):
    """결정 달(2005-09 ~ 2026-08) × 신호 표 — 상태만(수익 · 통계 없음). I = x_data.signal_inputs(mode) · dd = x_data.decision_days.
    열: re(D0 달 초과 · BEAR 입력) · slow · X-BEAR · ghm · X-CRED · X-VTS · X-COMP · X-RRSHOCK · X-GVTREND · T-SMA200 · vol63 · nagel_z ·
        CREDIT · FEAR · TREND · FAST · X-JM(with_jm). 🚨 BEAR 의 a 는 결정 달 t 에서 보유월 t+1 에 쓴다(평가 층)."""
    I = I or XD.signal_inputs(mode)
    XD.assert_input_floor(I)
    dd = dd if dd is not None else calendar()
    spy, rf = I["spy"][0], I["rf"][0]
    re = monthly_excess(spy, rf, dd)
    F = pd.DataFrame(index=re.index)
    F["re"] = re
    slow, fast = slow_fast(re)
    F["slow"], F["TREND"], F["FAST"] = slow, slow, fast
    F["X-BEAR"] = bear_state(re)
    F["ghm"] = ghm_state(re)
    d2 = dd.reindex(re.index)
    F["X-CRED"] = cred_state(I["baa10y"][0], d2, mode)
    F["CREDIT"] = credit_level(I["baa10y"][0], d2, mode)
    F["X-VTS"] = vts_state(I["vix"][0], I["vix3m"][0], d2, mode)
    F["FEAR"] = fear_level(I["vix"][0], d2, mode)
    F["X-COMP"] = comp_state(F["X-BEAR"], F["X-CRED"], F["X-VTS"], re)
    F["X-RRSHOCK"] = rrshock_state(I["dfii10"][0], d2, XD.trading_days(), mode)
    F["X-GVTREND"] = gvtrend_state(I["ivw"][0], I["ive"][0], d2)
    F["T-SMA200"] = sma200_state(I["gspc"][0], d2)
    F["vol63"] = vol63(spy, d2)
    F["nagel_z"] = nagel_z(re, spy, d2)
    if with_jm:
        re_d = daily_excess(spy, rf)
        re_d = re_d.loc[re_d.index.to_period("M") >= pd.Period("2005-09", "M")]
        st, _log = jm_daily_states(re_d)
        F["X-JM"] = jm_monthly(st, d2)
    first = {"X-BEAR": F["X-BEAR"].first_valid_index(), "X-GVTREND": F["X-GVTREND"].first_valid_index()}
    if with_jm:
        first["X-JM"] = F["X-JM"].first_valid_index()
    for k, v in first.items():
        if v is not None:
            XD.assert_first_active(k, str(v))
    return F


def lookahead_real(n_main=200, n_arm=80, seed=XD.SEED):
    """실자료 선견 점검(x_data.lookahead_check) — 결정일마다 가용 지평 뒤 자료를 자르거나 난수로 바꿔도 그 결정의 해시가 같은가.
    돌려주는 것 {팔: {ok, n, n_bad}} — 참/거짓 · 개수만(값 · 해시 없음 · 상태 계열도 싣지 않는다)."""
    I = XD.signal_inputs("T1")
    dd = calendar()
    tdays = XD.trading_days()
    dates = list(dd.loc[dd.index >= pd.Period("2006-08", "M")])
    spy, rf = I["spy"], I["rf"]

    def bear_vec(spy, rf):
        return bear_state(monthly_excess(spy, rf, dd))

    def comp_vec(spy, rf, baa, vix, vix3m):
        re = monthly_excess(spy, rf, dd)
        d2 = dd.reindex(re.index)
        return comp_state(bear_state(re), cred_state(baa, d2), vts_state(vix, vix3m, d2, "T1"), re)

    def vts_d0(vix, vix3m):
        return vts_state(vix, vix3m, dd, "D0")

    def rr_vec(dfii):
        return rrshock_state(dfii, dd, tdays)

    def gv_vec(ivw, ive):
        return gvtrend_state(ivw, ive, dd)

    def sma_vec(gspc):
        return sma200_state(gspc, dd)

    def fear_vec(vix):
        return fear_level(vix, dd)

    def cred_lvl(baa):
        return credit_level(baa, dd)

    jobs = {"X-BEAR": (bear_vec, {"spy": spy, "rf": rf}, "T1", n_main),
            "X-COMP": (comp_vec, {"spy": spy, "rf": rf, "baa": I["baa10y"], "vix": I["vix"], "vix3m": I["vix3m"]}, "T1", n_arm),
            "X-VTS(D0)": (vts_d0, {"vix": I["vix"], "vix3m": I["vix3m"]}, "D0", n_arm),
            "X-RRSHOCK": (rr_vec, {"dfii": I["dfii10"]}, "T1", n_arm),
            "X-GVTREND": (gv_vec, {"ivw": I["ivw"], "ive": I["ive"]}, "T1", n_arm),
            "T-SMA200": (sma_vec, {"gspc": I["gspc"]}, "T1", n_arm),
            "FEAR": (fear_vec, {"vix": I["vix"]}, "T1", n_arm),
            "CREDIT": (cred_lvl, {"baa": I["baa10y"]}, "T1", n_arm)}
    out = {}
    for nm, (fn, inp, mode, n) in jobs.items():
        t = time.time()
        r = XD.lookahead_check(fn, inp, dates, mode=mode, n=n, seed=seed)
        out[nm] = {"ok": bool(r["ok"]), "n": int(r["n"]), "n_bad": int(r["n_bad"]), "mode": mode, "sec": round(time.time() - t, 1)}
    return out


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험(망 · 캐시 · 실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _pidx(a, n):
    return pd.period_range(a, periods=n, freq="M")


def _st_constants():
    assert (BEAR_SLOW, BEAR_FAST, BEAR_THR) == (12, 1, 0.0)
    assert APP_MIN == 0.10 and CRED_DAYS == 365 and VTS_THR == 1.0 and (RR_TD, RR_THR) == (63, 0.20) and GV_FIRST == "2006-12"
    assert ARM_STATUS["X-VTS"] == "dropped" and ARM_STATUS["X-RRSHOCK"] == "twin" and "X-VTS" not in M_BY_FAMILY
    assert set(M_BY_FAMILY) == {"X-COMP", "X-CRED", "X-BLR", "X-JM", "X-COMP-W"} and FG_FAMILY == ("X-GVTREND",)
    return "등록 상수(12 · 1 · 0 · APP 0.10 · CRED 365일 · VTS 1.0 · RRSHOCK 63/0.20 · GVTREND 2006-12) · 팔 상태(VTS 삭제 · RRSHOCK 쌍둥이)"


def _st_bear_truth():
    # 진리표: 12개월 평균 < 0 ∧ 이번 달 < 0 만 1
    base = np.full(24, 0.01)
    idx = _pidx("2005-09", 24)
    re = pd.Series(base, index=idx)
    a = bear_state(re)
    assert a.iloc[:11].isna().all() and (a.iloc[11:] == 0).all()
    cases = [((-0.02,) * 11 + (-0.01,), 1.0), ((-0.02,) * 11 + (0.01,), 0.0), ((0.02,) * 11 + (-0.01,), 0.0),
             ((0.001,) * 11 + (-0.02,), 1.0), ((0.01,) * 11 + (-0.01,), 0.0), ((0.0,) * 11 + (-1e-9,), 1.0), ((0.0,) * 12, 0.0)]
    for seq, want in cases:
        r = pd.Series(list(seq), index=_pidx("2010-01", 12))
        got = bear_state(r).iloc[-1]
        assert got == want, (seq[-3:], got, want)
    # GHM 네 상태
    r = pd.Series([-0.02] * 11 + [0.01], index=_pidx("2010-01", 12))
    assert ghm_state(r).iloc[-1] == "Rebound"
    r = pd.Series([0.02] * 11 + [-0.01], index=_pidx("2010-01", 12))
    assert ghm_state(r).iloc[-1] == "Correction"
    # 명제 2: 합성 V 경로(저점 뒤 모든 달이 양)에서 켜짐은 저점 다음 첫 달 하나뿐 — 켜진 달 = 음의 달 바로 뒤의 결정
    seq = [0.01] * 14 + [-0.05, -0.08, -0.12, -0.06] + [0.04, 0.05, 0.03, 0.06, 0.02, 0.03, 0.04, 0.05, 0.02, 0.03]
    r = pd.Series(seq, index=_pidx("2005-09", len(seq)))
    a = bear_state(r)
    trough = 17                                            # 마지막 음의 달(저점 달)
    after = a.iloc[trough + 1:]
    on_after = int(after.fillna(0).sum())
    assert on_after == 0, on_after                          # 저점 뒤 결정은 모두 FAST ≥ 0 → 0
    assert a.iloc[trough] == 1.0                            # 저점 달 결정(음의 달) → 다음 보유월(첫 반등 달) 1 · 명제 2 의 «첫 달 하나»
    on = a.fillna(0) > 0
    assert (r[on] < 0).all()                                 # 켜진 결정 달은 모두 음의 달
    # 고점 근처 빠른 급락(12개월 평균 아직 양)에서는 켜지지 않는다
    seq2 = [0.03] * 12 + [-0.12] + [0.05] * 3
    a2 = bear_state(pd.Series(seq2, index=_pidx("2005-09", len(seq2))))
    assert a2.fillna(0).sum() == 0
    return "BEAR 진리표 7 · 워밍업 11개월 NaN · GHM 상태 · 명제 2(V 경로 켜짐 ≤ 저점 달 하나 · 켜진 달 = 음의 달) · 빠른 급락 무반응"


def _st_comp_truth():
    idx = _pidx("2010-01", 14)
    re = pd.Series([-0.01] * 14, index=idx)                 # SLOW < 0 · FAST < 0 → BEAR 1(12번째부터)
    b = bear_state(re)
    one = pd.Series(1.0, index=idx)
    zero = pd.Series(0.0, index=idx)
    t = idx[-1]
    for (bb, cc, vv), want in (((1, 1, 1), 1.0), ((1, 1, 0), 0.5), ((1, 0, 0), 0.0), ((0, 0, 0), 0.0), ((0, 1, 1), 0.5), ((0, 1, 0), 0.0)):
        B = one if bb else zero
        got = comp_state(B, one if cc else zero, one if vv else zero, re)[t]
        assert got == want, (bb, cc, vv, got, want)
    # 차단기: SLOW < 0 ∧ FAST ≥ 0 → 0 (CRED · VTS 가 켜져도)
    re2 = pd.Series([-0.02] * 13 + [0.01], index=idx)
    assert comp_state(bear_state(re2), one, one, re2)[t] == 0.0
    # Correction(SLOW ≥ 0 · FAST < 0) 에서 CRED + VTS 만으로 ½ · 셋 다면(BEAR 0) 여전히 ½
    re3 = pd.Series([0.02] * 13 + [-0.01], index=idx)
    assert comp_state(bear_state(re3), one, one, re3)[t] == 0.5
    return "COMP 진리표 6 · Rebound 차단기 · Correction 에서 CRED+VTS = ½"


def _syn_days(a="2005-08-01", b="2026-09-10"):
    return XD._syn_days(a, b)


def _st_components():
    days = _syn_days()
    XD.set_calendar(days)
    try:
        dd = XD.decision_days("2005-08", "2026-08")
        rng = np.random.default_rng(3)
        # CRED: 365일 창(날짜) · d − 1 영업일 — 마지막 값이 창 중앙보다 크면 1
        baa = pd.Series(2.0, index=days)
        d = dd.loc[pd.Period("2012-06", "M")]
        c = XD.cutoff("fred_d", d, "T1")
        baa.loc[baa.index == c] = 3.0
        cs = cred_state(baa, dd.loc[[pd.Period("2012-06", "M")]])
        assert cs.iloc[0] == 1.0
        early = cred_state(baa, dd.loc[pd.Period("2005-09", "M"):pd.Period("2006-09", "M")])
        assert early.loc[:pd.Period("2006-07", "M")].isna().all() and early.loc[pd.Period("2006-08", "M"):].notna().all()   # 365일 워밍업
        baa2 = baa.copy()
        baa2.loc[baa2.index == d] = 9.0                      # d 당일 값(선견)은 보지 않는다
        baa2.loc[baa2.index == c] = 1.0
        assert cred_state(baa2, dd.loc[[pd.Period("2012-06", "M")]]).iloc[0] == 0.0
        # VTS: 공표 전 0 · D0 는 앞 거래일
        vix = pd.Series(20.0, index=days)
        v3 = pd.Series(18.0, index=days)
        s = vts_state(vix, v3, dd, "T1", pub="2009-09-18")
        assert (s.loc[s.index < pd.Period("2009-09", "M")] == 0).all() and (s.loc[s.index >= pd.Period("2009-10", "M")] == 1).all()
        vix2 = vix.copy()
        dd1 = dd.loc[[pd.Period("2015-03", "M")]]
        d1 = dd1.iloc[0]
        vix2.loc[vix2.index == d1] = 10.0                     # d 당일만 낮춤 → T1 은 0 · D0 는 앞 거래일 값 20/18 → 1
        assert vts_state(vix2, v3, dd1, "T1", pub="2009-09-18").iloc[0] == 0.0
        assert vts_state(vix2, v3, dd1, "D0", pub="2009-09-18").iloc[0] == 1.0
        v3b = v3.drop(d1)                                     # V1: 그날 VIX3M 이 비면 두 값이 함께 선 마지막 날(앞 거래일 20/18 → 1) · NaN 없음
        assert vts_state(vix2, v3b, dd1, "T1", pub="2009-09-18").iloc[0] == 1.0
        assert vts_state(vix, v3, dd, "T1", pub="2009-09-18").notna().all()
        # RRSHOCK: 63거래일 전 대비 +0.20 이상
        dfii = pd.Series(1.0, index=days)
        dq = dd.loc[[pd.Period("2020-06", "M")]]
        cq = XD.cutoff("fred_d", dq.iloc[0], "T1")
        dfii.loc[dfii.index == cq] = 1.20
        assert rrshock_state(dfii, dq, days).iloc[0] == 1.0
        dfii.loc[dfii.index == cq] = 1.19
        assert rrshock_state(dfii, dq, days).iloc[0] == 0.0
        # GVTREND: 2006-12 전 NaN · 성장 부진이면 1
        ivw = pd.Series(np.linspace(100, 110, len(days)), index=days)
        ive = pd.Series(np.linspace(100, 130, len(days)), index=days)
        g = gvtrend_state(ivw, ive, dd)
        assert g.loc[g.index < pd.Period("2006-12", "M")].isna().all() and (g.loc[g.index >= pd.Period("2007-01", "M")] == 1).all()
        # SMA200 · vol63 · 변동성 쌍둥이 · 척도
        g2 = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(days)))), index=days)
        sm = sma200_state(g2, dd)
        assert sm.iloc[:8].isna().any() and sm.dropna().isin([0.0, 1.0]).all()
        v = vol63(g2, dd)
        vt = vol_twin(v, 0.2)
        assert abs(float(vt.dropna().iloc[40:].mean()) - 0.2) < 0.15
        sc, k, ok = scale_to_mean(pd.Series([1.0, 0, 0, 0], index=_pidx("2010-01", 4)), 0.1)
        assert ok and abs(k - 0.4) < 1e-12 and abs(sc.mean() - 0.1) < 1e-12
        sc, k, ok = scale_to_mean(pd.Series([1.0, 0, 0, 0], index=_pidx("2010-01", 4)), 0.5)
        assert not ok and k == 1.0
        # Nagel 이분법
        z = pd.Series(rng.normal(0, 1, 200), index=_pidx("2008-01", 200))
        s, zs = nagel_twin(z, 0.15)
        assert zs and abs(float(s.mean()) - 0.15) < 1e-6
    finally:
        XD.set_calendar(None)
    return "CRED(365일 날짜 창 · d−1 영업일 · 당일 무시) · VTS(공표 전 0 · T1/D0) · RRSHOCK(63거래일 · 0.20) · GVTREND(2006-12) · SMA200 · 변동성 쌍둥이 · 척도 · Nagel z* 이분법"


def _st_comp_w():
    days = _syn_days("2005-08-01", "2008-12-31")
    rng = np.random.default_rng(11)
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(-0.0005, 0.01, len(days)))), index=days)
    rf = pd.Series(0.002, index=pd.period_range("2005-09", "2009-01", freq="M"))
    baa = pd.Series(2.0 + 0.001 * np.arange(len(days)), index=days)        # 늘 오른다 → CRED 1
    vix = pd.Series(20.0, index=days)
    v3 = pd.Series(21.0, index=days)
    XD.set_calendar(days)
    try:
        pos, dec = comp_w_positions(spy, rf, baa, vix, v3, days, "2006-09-01", "2008-12-31", pub="2009-09-18")
        assert len(dec) > 50 and pos.dropna().isin([0.0, 0.5, 1.0]).all()
        # 체결 규칙: 판정 f 의 s 는 f 다음 거래일 다음 날부터
        f = dec.index[60]
        j = days.searchsorted(f, side="right")
        if j + 2 < len(days) and days[j + 1] in pos.index:
            assert pos.loc[days[j + 1]] == dec.loc[f, "s"]
        # 금요일 휴장이면 목요일
        we = week_ends(pd.DatetimeIndex([x for x in days if x != pd.Timestamp("2006-07-07")]))
        assert pd.Timestamp("2006-07-06") in we
    finally:
        XD.set_calendar(None)
    return "COMP-W 주 판정(252 · 21 거래일) · 다음 거래일 체결 · 금요일 휴장 목요일 · 값 {0, ½, 1}"


def _st_jm():
    QJ = _q_jump()
    rng = np.random.default_rng(5)
    days = pd.bdate_range("2005-09-01", "2012-12-31")
    reg = np.zeros(len(days), int)
    reg[900:1100] = 1
    reg[1500:1600] = 1
    r = np.where(reg == 1, rng.normal(-0.002, 0.03, len(days)), rng.normal(0.0006, 0.008, len(days)))
    re_d = pd.Series(r, index=days)
    st, log = jm_daily_states(re_d, QJ=QJ)
    fits = [x["fit"] for x in log]
    assert fits and all(f[5:7] in ("01", "07") for f in fits) and log[0]["L"] >= JM_MIN and max(x["L"] for x in log) <= JM_MAX
    first = pd.Timestamp(fits[0])
    assert st.loc[st.index < first].isna().all() and st.loc[st.index >= first].notna().all()
    b = st.loc[days[1500:1600]].dropna()
    if len(b):
        assert (b == 0).mean() > 0.5                         # 합성 난류 구간은 BEAR 가 대부분
    dd = pd.Series([days[days.to_period("M") == p].max() for p in pd.period_range("2005-09", "2012-12", freq="M")],
                   index=pd.period_range("2005-09", "2012-12", freq="M"))
    m = jm_monthly(st, dd)
    assert m.loc[m.index < first.to_period("M")].isna().all()
    # 선견: 적합일 뒤 자료를 흔들어도 그 전 상태는 같다
    k = days.searchsorted(pd.Timestamp("2011-03-15"))
    r2 = r.copy()
    r2[k:] = rng.normal(0, 0.05, len(r2) - k)
    st2, _ = jm_daily_states(pd.Series(r2, index=days), QJ=QJ)
    same = st.iloc[:k].fillna(-1).to_numpy() == st2.iloc[:k].fillna(-1).to_numpy()
    assert same.all()
    return "JM(얼린 q_jump blob · fit_jm · online_final) — 1·7월 적합 · 학습 756 ~ 3000 · 첫 적합 전 NaN · 합성 난류 BEAR · 선견 불변"


def _st_lookahead_signals():
    days = _syn_days()
    rng = np.random.default_rng(9)
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(days)))), index=days)
    rf = pd.Series(0.002, index=pd.period_range("2005-09", "2026-09", freq="M"))
    baa = pd.Series(2.0 + np.cumsum(rng.normal(0, 0.02, len(days))), index=days)
    vix = pd.Series(18 + np.abs(np.cumsum(rng.normal(0, 0.3, len(days)))), index=days)
    v3 = vix * (1 + rng.normal(0.02, 0.03, len(days)))
    XD.set_calendar(days)
    try:
        dd = XD.decision_days("2005-08", "2026-08")
        dates = list(dd.loc[dd.index >= pd.Period("2006-08", "M")])

        def bear_vec(spy, rf):
            return bear_state(monthly_excess(spy, rf, dd))

        def comp_vec(spy, rf, baa, vix, vix3m):
            re = monthly_excess(spy, rf, dd)
            d2 = dd.reindex(re.index)
            return comp_state(bear_state(re), cred_state(baa, d2), vts_state(vix, vix3m, d2, "T1", pub="2009-09-18"), re)

        def comp_d0(spy, rf, baa, vix, vix3m):
            re = monthly_excess(spy, rf, dd)
            d2 = dd.reindex(re.index)
            return vts_state(vix, vix3m, d2, "D0", pub="2009-09-18")

        def leak(spy, rf):                                   # 선견: 다음 달 수익을 쓴다 — 잡혀야 한다
            re = monthly_excess(spy, rf, dd)
            return (re.shift(-1) < 0).astype(float)

        I = {"spy": (spy, "spy"), "rf": (rf, "rf_us_m")}
        r1 = XD.lookahead_check(bear_vec, I, dates, n=40)
        assert r1["ok"], r1
        I2 = dict(I, baa=(baa, "fred_d"), vix=(vix, "vix"), vix3m=(v3, "vix3m"))
        r2 = XD.lookahead_check(comp_vec, I2, dates, n=30)
        assert r2["ok"], r2
        r3 = XD.lookahead_check(comp_d0, I2, dates, mode="D0", n=30)
        assert r3["ok"], r3
        r4 = XD.lookahead_check(leak, I, dates, n=30)
        assert not r4["ok"]
    finally:
        XD.set_calendar(None)
    return "선견 틀(x_data.lookahead_check) — BEAR · COMP(T1) · VTS(D0) 통과 · 다음 달 수익 선견 잡음"


def _st_window():
    days = _syn_days()
    XD.set_calendar(days)
    try:
        dd = XD.decision_days("2005-08", "2026-08")
        rng = np.random.default_rng(1)
        spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(days)))), index=days)
        rf = pd.Series(0.002, index=pd.period_range("2005-09", "2026-09", freq="M"))
        re = monthly_excess(spy, rf, dd)
        a = bear_state(re)
        assert str(re.index[0]) == "2005-09" and str(a.first_valid_index()) == "2006-08"
        XD.assert_first_active("X-BEAR", str(a.first_valid_index()))
        hold = [str(p + 1) for p in a.loc["2006-08":"2026-07"].index]
        assert XD.assert_scored_months(hold)["n"] == 240
        try:
            XD.assert_input_floor({"spy": pd.Series(1.0, index=pd.bdate_range("2005-07-01", "2005-09-01"))})
            raise AssertionError("창 앞 입력 통과")
        except AssertionError as e:
            if "통과" in str(e):
                raise
    finally:
        XD.set_calendar(None)
    return "r^e 첫 달 2005-09 · BEAR 첫 결정 2006-08 → 채점 보유월 240(2006-09 ~ 2026-08) · 입력 하한 단언"


SELFTESTS = (_st_constants, _st_bear_truth, _st_comp_truth, _st_components, _st_comp_w, _st_jm, _st_lookahead_signals, _st_window)


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
        print("  %s %-24s %5.2fs  %s" % ("✓" if st == "통과" else "✗", nm, dt, msg))
    print("x_signals selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(selftest())
    if "--lookahead-real" in sys.argv[1:]:
        XD.install_read_guard(signal_layer=True)                   # 신호 층: EG30 산출 · tbatch 산출을 열면 멈춘다
        XD.install_write_guard(XD.ROOT)
        t0 = time.time()
        res = lookahead_real()
        XD.guard_off()
        rep = {"arms": res, "all_ok": all(v["ok"] for v in res.values()), "sec": round(time.time() - t0, 1)}
        p = os.path.join(XD.cache_guard(), "meta", "_lookahead_x_signals.json")
        with io.open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        raise SystemExit(0 if rep["all_ok"] else 1)
    print(__doc__)
