# -*- coding: utf-8 -*-
"""build/x_eval.py — 배치 X 평가 층: M(시장 20년 · 일관성 점검) · I(국외 10개 시장 재현) · G(성장 코어 대리 20년) · S(EG30 V0 10년 · 무해 · 구현성)
관문 · 잭나이프 · 층화 위약 · 희석 쌍둥이 · 측정 팔 BY · 라벨 · 공개 보기 · 보험료 한도(운용 조건형 멈춤 규칙 — 원장 · 예정 판정일 없음).

🚨 사용자 갱신(2026-09-27 · 계산 전): «이런 불필요한 미래 일정들은 다 꺼 · QFWD까지 모두 끄라» — 전방 원장(XFWD) · FF1 · FF2 · 날짜가 박힌
   전방 판정은 모두 취소했다(QFWD 자동 실행은 bbcc98b8b 에서 멈춤). 채택은 한 번 굽는 표본 안 등록 판정으로만 정한다 — 경로 B 는 남는다:
   모든 층을 넘으면 결과 문서 다음 월말에 a_op ½ 로 실자금 EG30 에 붙이고, 보험료 한도(뒤 24개월 −0.40%p NAV · 누적 −0.60%p NAV)는
   운용에서 감시하는 조건형 멈춤 규칙(premium_cap_kill)이다. 등록 문서 §0 · §8 에 이 변경을 적는다.

설계 원본(구속): xbatch_research.json targets · evaluation(M_market_20y · I_international_20y · growth_proxy_20y · S_layer · forward · rule_20y_compliance) ·
  multiplicity · power.fixed_b_critical_values · registration · user_answers(U1 a_op ½ · U2 경로 B) · decisions — 저장소 밖 스크래치.
  이 파일은 설계를 다시 짓지 않는다. 관문 · 문턱 · 상수는 명세 그대로 옮겼다(아래 «선언» 은 명세가 비워 둔 산수만).

얼린 함수(부르기만 · blob 단언): eg30plus.nw_t · down_months · nw_ols · cap_weights(x_adapter) · mech_episodes.zigzag · rebounds.

M 층(보유월 2006-09 ~ 2026-08 · 240 · SPY TR 일간 · T+1)
  Δ_u = −(a_{u−1} − ā)·R^e_u − κ|a_{u−1} − a_{u−2}| · 단위 d · ā = 창 평균 노출 · κ = 0.2·c/d_ref(10bp → 0.004 · 20bp → 0.008) · 첫 결정의 앞 노출 0.
  NW(6) t(eg30plus.nw_t · 바틀렛) · 한쪽 5% 고정 b 임계 1.706(등록 상수 — 다시 모의하지 않는다).
  M-C1 t ≥ 1.706 · M-C2 하락월(S&P PR 달 < 0) 평균 Δ > 0 ∧ CRASH-M(SPY TR 달 ≤ −σ_pre) 평균 Δ > 0 ·
  M-C3 RG_abs = Σ_반등일 a·r^e / Σ_급락다리일 (−a·r^e) ≤ ½(일간 · 분모 ≤ 0 이면 거짓) · M-C4 두 10년 반쪽 평균 > 0 ∧ 2019-01 ~ 2026-08 평균 ≥ 0 ·
  M-C5 에피소드 하나씩 뺀 평균 Δ ≥ 0 이 n_e 개 중 n_e − 1 개 이상(명세 10개 중 9개) · M-C6 20bp κ 에서 평균 Δ > 0.
I 층  각 시장 현지 초과(x_intl re_sig)에 같은 BEAR · Δ_i,u = −(a_i,u−1 − ā_i)·re_hold_i,u(명세 식 — 비용 항 없음) · 풀링 = 시장 등가중 ·
  DK t = 풀링 계열 NW(6) t · I-C1 ≥ 1.706 · I-C2 시장 ≥ 6 개 평균 Δ > 0 · I-C3 풀링 2019-01 ~ 2026-08 평균 ≥ 0 · I-C4 시장별 현지 하락월 평균 Δ 의 평균 > 0.
G 층  French 월 · 펀드 = 0.9·Mkt + 0.1·슬리브 · 슬리브 = (1 − a·APP)·코어 + a·APP·D · a = M 층 월말 판정(보유 = 다음 달력 달) ·
  단계 효과 e_u = 0.1·ã_{u−1}·(D_u − C_u) − c·0.2·|ã_{u−1} − ã_{u−2}| · ã = a·APP · APP = 1[β̂_C − β̂_D ≥ 0.10] ·
  β̂ = 결정 달 이하 월간 OLS((R − RF) on (Mkt − RF) · 최근 ≤ 36 · ≥ 12 개월 · 2005-08~) ·
  G-C1 희석 쌍둥이(c = 1 + e/x_LG · [0, 1] · x_LG ≤ 0 ∨ e ≥ 0 이면 1) 대비 하락월 평균 ≥ ∧ CRASH-M 평균 > ∧ CRASH-M 평균 e > 0 ·
  G-C2 Σ_SURGE e ≥ −½·Σ_CRASH e ∧ Σ_CRASH e > 0 · G-C3 2007 ~ 2025 이긴 해 수 ≥ 코어만 − 1 · G-C4 연 e 의 80% 한쪽 하한 > −0.30%p.
S 층  x_adapter 가 준 월 계열(얼린 V0 경로 · 얼린 q_switch 책) — 주 행 T+1(결정 d_m · 체결 T+1 종가 · x_adapter.mix_t1 · 두 몫 {0, 1} 이면
  얼린 q_switch.switch_fr 와 짝맞춤) · D0 행(얼린 q_switch.mix_fr · d_m 종가 되맞춤)은 보고만(명세 S_layer.reports_only «D0 행») ·
  S-C1 120개월 D 목표 · 회전(슬리브 편도 · 연) ≤ 10 · S-C2 켜진 달 e 를 (−a·R^e_m) 에
  회귀한 기울기 > 0 ∧ 켜진 달 실현 β(D) < β(C) · S-C3 연 e 80% 하한 > −0.30%p(a 1) · S-C4 g_d ≥ max(0, −0.0982·e) ∧ g_c > max(0, −0.233·e).
라벨  M 일관성 통과(오염 창) · I 국외 재현 · 방어 재현(M ∧ I) · 보험 채택 후보(방어 재현 ∧ G 무해 ∧ S 무해) · 랩 발견(맥락 · 방어 재현 ∧ M t ≥ 3.0).
운용(사용자 답 2026-09-27)  U1 a_op = ½ · U2 경로 B — 보험 채택 후보면 결과 문서 다음 월말에 a_op ½ 로 EG30 슬리브에 붙이고 보험료 한도
  (조건형 멈춤: 뒤 24개월 누적 ≤ −0.40%p NAV 이고 그 창에 완료 급락 다리 없음 · 또는 붙인 뒤 누적 ≤ −0.60%p NAV → 다음 월말 a = 0 ·
  다시 붙이려면 새 등록) · 공개 문구 «오염 창에서 고름 · 전방 미확인 · 보험 결정». FF1 · FF2 · XFWD 원장은 없다(위 사용자 갱신).

선언(명세가 비워 둔 산수 — 결과를 보기 전에 고정)
  E1 일간 rf_d = (1 + rf_u)^(1/n_u) − 1 · n_u = 보유월 u 의 T+1 창 거래일 수(qbatch_core.etf_path 의 현금 분할과 같은 식).
  E2 급락 다리 · 반등 = 얼린 mech_episodes.zigzag(^GSPC · 10%/10% · 2006-08-31 ~ 2026-08-31) · rebounds(63) · 날은 (시작, 끝] · 채점 T+1 창 안 날만.
  E3 에피소드 = 앞 다리 저점 ~ 다음 다리 고점 거래일 수 ≤ 126 이면 묶는다 · 잭나이프 구간 = 첫 다리 고점 달 ~ 마지막 반등 끝 달(보유월).
  E4 80% 한쪽 하한 = 연 평균 − 0.8416·(월 sd·√12/√(n/12)) — final_power block_S 의 식(iid).
  E5 측정 팔 p = 1 − Φ(NW t)(보고 · BY q 0.10) · 활성 달만(ā · 비용도 활성 달 안).
  E6 층화 위약: 결정 240 달을 12개월 토막 20 개로 · 토막 변동성 = 그 결정 달 vol63 평균 · 3분위(토막 순위) 안에서만 토막을 섞는다 · 1,000회 · 씨앗 20260927 ·
     순위 = #(위약 평균 Δ < 관측) + ½#(같음) / 1000.
  E7 HM · TM: y = −a·R^e(단위) 를 R^e · max(0, −R^e) | (R^e)² 에 NW(6) 회귀(eg30plus.nw_ols) — γ > 0 이면 좋은 타이밍.
  E8 G 층 D 자체 회전 비용은 French 대리에 없어 넣지 않는다(S 층은 D 책 경로 안에 있다).
  E9 G 대리 충실도 강등(F0: corr < 0.6 → Lo 20 · 관문 «참고») 이면 보험 채택 후보는 G 관문을 요구하지 않고 «G 참고» 를 라벨에 적는다.
  E10 손익분기(보고): 켜진 달 시장 초과 평균(단위 %/월)을 명세 honest_outlook 의 −0.637(α_D 0) · −0.991(α_D −0.2%/월) 과 나란히 적는다.
  E11 G 항등식 잔차(보고): e_u − 예측 · 예측 = 0.1·ã·[(β_D − β_C)·(Mkt − RF) + (α_D − α_C)] · β · α = 창 전체 월간 OLS(코어 · D 대리 각각).
  E12 I 층 USD 판(보고) = 같은 시장 · 같은 규칙에 USD TR − DGS3MO(x_intl.view «usd») · French 국가 Mkt 부호 일치(x_intl.french_sign_agreement · 자료 충실도).
  E13 D 대리 충실도(F0 · 자료 충실도) = corr(D_S 월 D0 수익 · ME5×β1) 2014-06 ~ 2026-08 · < 0.6 이면 Lo 20 로 바꾸고 G 관문 «참고»(기계적 · d_proxy_fidelity).
  E14 눈가린 연기 보고는 키 구조와 구조 개수만 싣는다(값의 형 · None 여부 · 신호가 정하는 목록 길이를 싣지 않는다 — 부호가 새지 않게).
  E15(검토 반영 2026-09-27 · 계산 전) 라벨 «G 참고(대리 충실도 강등)» 는 늘 싣는다(참/거짓 — 조건부 키는 키 구조 보고로도 결과를 흘린다) ·
      M 실패 운용 줄 = «그대로(EG30 V0)»(희석 메뉴 없음 — 사용자 원칙 «섞지 말고 스텝을 더해») · S 층 a = M 층 X-BEAR 결정(2016-08 ~ 2026-07) 단언 ·
      공개 보기의 켜짐 비율은 M 뒤 10년 반쪽 · S 10년 창만(20년 켜짐 비율 · G 켜짐 비율은 캐시 — 사용자 20년 규칙) · 연기 보고에 표준출력 길이 없음.

🚨 20년 규칙: 채점 보유월 2006-09 ~ 2026-08(assert_scored_months) · 입력 ≥ 2005-08-01(x_data 로더 · assert_input_floor) · 20년 수치는 캐시에만
   (x_data.write_cache_json 표지) · 저장소 보기(public_view)는 불리언 · 창 · n · 켜짐 비율 · 2016-09 ~ 2026-08 반쪽 · S 요약만 — x_data.public_safe 통과.
🚨 랩 규율: 등록 커밋 전에는 실자료 값을 찍지 않는다 — --selftest 는 합성만 · --blind-smoke 는 끝까지 돌리고 산출을 열지 않고 지운다(모양 · 개수 · 시간만).

  python build/x_eval.py --selftest
  python build/x_eval.py --blind-smoke [--with-s] [--no-intl]   실자료 눈가린 연기(M · I · G · 측정 팔 · --with-s 면 S(x_adapter 자식)) — 키 구조 · 개수 · 시간만
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import os
import sys
import tempfile
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
import x_signals as XS                  # noqa: E402
import x_blr as XB                      # noqa: E402

# ══════════════════════════════════════════════════════════════════════════
#  등록 상수
# ══════════════════════════════════════════════════════════════════════════
CRIT = {"T240_L6": 1.706, "T92_L3": 1.738, "T36_L3": 1.892, "T24_L3": 2.037}   # 합성 iid 20만 회 · 바틀렛 NW t 95% 분위(씨앗 20260928)
# 🔎 T36_L3 · T24_L3 은 취소된 전방 판정(FF1 · FF2)의 상수 — 등록 상수로 남기되 이 배치의 어떤 관문에도 쓰지 않는다(사용자 갱신 2026-09-27).
NW_LAG = 6
COST10, COST20 = 0.0010, 0.0020
D_REF = 0.05
KAPPA10, KAPPA20 = 0.2 * COST10 / D_REF, 0.2 * COST20 / D_REF                  # 0.004 · 0.008(단위 d)
SIGMA_PRE = 0.042903                                                             # 랩 고정 상수(data/mech_episodes.json · blob d67a2a74)
MECH_EPISODES_BLOB = "d67a2a74b486aff7f3a46d0f2a9bebe104df669f"
ZZ_HD = ZZ_HU = 0.10
ZZ_REB = 63
ZZ_START, ZZ_END = "2006-08-31", "2026-08-31"
EPISODE_GAP_TD = 126
RG_MAX = 0.5
I_BREADTH = 6
NI_LB = -0.30                                                                    # %p/년 — G-C4 · S-C3(a 1)
Z80 = 0.8416
DIL_DOWN, DIL_CRASH = 0.0982, 0.233                                              # 0.075/0.764 · 0.178/0.764
S_TURN_MAX = 10.0
PLACEBO_N, PLACEBO_SEED, PLACEBO_BLOCK = 1000, 20260927, 12
BY_Q = 0.10
LAB_T, BONF_Z = 3.0, 2.94
GFC_EXCL = XD.GFC_EXCL
OOL = XD.OUT_OF_LIT
HALVES = XD.HALVES
FULL_YEARS = XD.FULL_YEARS
S_YEARS = (2017, 2025)
A_OP = 0.5                                                                       # 사용자 U1
PATH = "B"                                                                       # 사용자 U2
PREMIUM_TRAIL_M, PREMIUM_TRAIL_CAP, PREMIUM_CUM_CAP = 24, -0.40, -0.60           # %p NAV — 운용 조건형 멈춤(원장 · 예정 판정일 없음)
DISCLOSE_B = "오염 창에서 고름 · 전방 미확인 · 보험 결정"
FORWARD_CANCELLED = "전방 원장(XFWD) · FF1 · FF2 · 날짜가 박힌 전방 판정 없음 — 사용자 갱신 2026-09-27(계산 전) «이런 불필요한 미래 일정들은 다 꺼 · QFWD까지 모두 끄라»"
BREAKEVEN_ON_RE = {"alpha_D_0": -0.637, "alpha_D_minus0.2": -0.991}               # %/월 — 명세 power.alpha_breakeven(보고만)
FROZEN_BLOBS = {"eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628", "mech_episodes": "161080fd9244c060a7a94c559044de3e3ddcc27c"}
LABELS = ("M 일관성 통과(오염 창)", "I 국외 재현", "방어 재현", "보험 채택 후보", "랩 발견(맥락)")
LABEL_G_REF = "G 참고(대리 충실도 강등)"                    # 늘 싣는다(참/거짓) — 조건부 키는 키 구조만 싣는 연기 보고로도 결과를 흘린다(검토 반영 2026-09-27)
OP_M_FAIL = "그대로(EG30 V0)"                               # M 실패 줄 — 희석(EG30 몫 줄이기) 메뉴는 싣지 않는다(사용자 원칙 «섞지 말고 스텝을 더해» · 검토 반영)

_FZ = {}


def _frozen(name):
    if name not in _FZ:
        XD.assert_blob(name, FROZEN_BLOBS[name])
        _FZ[name] = __import__(name)
    return _FZ[name]


def nw_t(x, lag=NW_LAG):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return _frozen("eg30plus").nw_t(x, lag=lag)


def nw_ols(y, X, lag=NW_LAG):
    return _frozen("eg30plus").nw_ols(y, X, lag=lag)


def _pr(a, b):
    return pd.period_range(a, b, freq="M")


HOLD = _pr(XD.SCORE_FIRST, XD.SCORE_LAST)                  # 보유월 240
DEC = HOLD - 1                                              # 결정 달 2006-08 ~ 2026-07


def _mean(x, mask=None):
    x = np.asarray(x, float)
    if mask is not None:
        x = x[np.asarray(mask, bool)]
    x = x[np.isfinite(x)]
    return float(x.mean()) if len(x) else None


def _gt(v, thr=0.0):
    return bool(v is not None and v > thr)


def _ge(v, thr=0.0):
    return bool(v is not None and v >= thr)


def norm_sf(t):
    return None if t is None else 0.5 * math.erfc(t / math.sqrt(2.0))


def by_fdr(pvals, q=BY_Q):
    """Benjamini–Yekutieli(임의 의존) — {이름: p} → {이름: 기각}."""
    items = [(p, k) for k, p in pvals.items() if p is not None]
    m = len(pvals)
    if m == 0:
        return {}
    cm = sum(1.0 / i for i in range(1, m + 1))
    items.sort()
    kmax = 0
    for r, (p, k) in enumerate(items, 1):
        if p <= q * r / (m * cm) + 1e-15:
            kmax = r
    rej = {k for _, k in items[:kmax]}
    return {k: (k in rej) for k in pvals}


def binom_sf(k, n, p=0.5):
    """P(X ≥ k | n, p) — 정확 이항."""
    if n <= 0:
        return None
    return float(sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1)))


def lb80(x_month):
    """E4 — 월 계열 → (연 평균, 80% 한쪽 하한) · 단위는 입력 그대로 × 12."""
    x = np.asarray(x_month, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return None, None
    ann = float(x.mean() * 12)
    se = float(x.std(ddof=1) * math.sqrt(12) / math.sqrt(n / 12.0))
    return ann, ann - Z80 * se


# ══════════════════════════════════════════════════════════════════════════
#  Δ(주 통계) · 비용 · 활성 달
# ══════════════════════════════════════════════════════════════════════════
def delta_series(a_dec, Re_hold, kappa=KAPPA10, abar=None, hold=None):
    """a_dec(결정 달 t 색인) · Re_hold(보유월 u = t+1 색인) → (Δ Series(보유월) · ā · 쓰인 a(보유월 색인)).
    활성(a 가 NaN 아님) 보유월만 · 첫 활성 달의 앞 노출은 0 · 비용 κ|Δa|."""
    hold = HOLD if hold is None else hold
    a = pd.Series(a_dec, dtype=float)
    a_h = pd.Series(a.to_numpy(float), index=pd.PeriodIndex(a.index, freq="M") + 1).reindex(hold)
    R = pd.Series(Re_hold, dtype=float).reindex(hold)
    act = a_h.notna() & R.notna()
    aa = a_h[act]
    if abar is None:
        abar = float(aa.mean()) if len(aa) else 0.0
    prev = aa.shift(1).fillna(0.0)
    d = -(aa - abar) * R[act] - kappa * (aa - prev).abs()
    return d, abar, aa


def market_part(a_h, Re_hold):
    """−a·R^e(단위 d · 정적 쌍둥이 대비 아님)."""
    return -(pd.Series(a_h, dtype=float) * pd.Series(Re_hold, dtype=float).reindex(pd.Series(a_h).index))


# ══════════════════════════════════════════════════════════════════════════
#  시장 틀(M 층 입력 — 수익 계열 · 라벨 · 일간 · 다리 · 에피소드)
# ══════════════════════════════════════════════════════════════════════════
class _DMShim:
    """eg30plus.down_months(Wd, hold) 에 넘길 최소 틀 — me(달 → 그달 마지막 거래일 자리) · IX_PR(^GSPC 종가 배열)."""

    def __init__(self, gspc):
        g = pd.Series(gspc, dtype=float).dropna()
        self.IX_PR = g.to_numpy(float)
        per = g.index.to_period("M")
        self.me = {}
        for i, p in enumerate(per):
            self.me[str(p)] = i


def down_months(gspc, hold=HOLD):
    """하락월 = S&P 500 PR 달 수익 < 0 인 보유월(얼린 eg30plus.down_months)."""
    E = _frozen("eg30plus")
    dm = set(E.down_months(_DMShim(gspc), [str(h) for h in hold]))
    return pd.Series([str(h) in dm for h in hold], index=hold)


def episodes_from_legs(legs, rebs, D):
    """E3 — 급락 다리(날짜) → 에피소드 [{legs: [(a, b)], rebs: [(b, e)], span: (첫 고점 달, 마지막 반등 끝 달)}]."""
    pos = {d: i for i, d in enumerate(D)}
    cr = [(l[1], l[2]) for l in legs if l[0] == "crash"]
    rb = {r["a"]: r["b"] for r in rebs}
    out = []
    for a, b in cr:
        if out and pos[a] - pos[out[-1]["legs"][-1][1]] <= EPISODE_GAP_TD:
            out[-1]["legs"].append((a, b))
        else:
            out.append({"legs": [(a, b)]})
    for ep in out:
        ep["rebs"] = [(b, rb.get(b, b)) for _, b in ep["legs"]]
        ep["span"] = (pd.Timestamp(ep["legs"][0][0]).to_period("M"), pd.Timestamp(ep["rebs"][-1][1]).to_period("M"))
    return out


class MFrame:
    """M 층 입력 한 벌(값은 메모리에만). 실자료는 MFrame.real() · 합성은 MFrame.synthetic()."""

    def __init__(self, hold, Re_t1, Re_d0, R_cal, down, daily, legs, rebs, D, rf=None, gspc=None, R_t1=None):
        self.hold = pd.PeriodIndex(hold, freq="M")
        self.Re_t1 = pd.Series(Re_t1, dtype=float).reindex(self.hold)
        self.Re_d0 = pd.Series(Re_d0, dtype=float).reindex(self.hold)
        self.R_cal = pd.Series(R_cal, dtype=float).reindex(self.hold)            # SPY TR 달력 달 수익(CRASH/SURGE 라벨)
        self.R_t1 = None if R_t1 is None else pd.Series(R_t1, dtype=float).reindex(self.hold)
        self.down = pd.Series(down, dtype=bool).reindex(self.hold).fillna(False)
        self.crash = (self.R_cal <= -SIGMA_PRE)
        self.surge = (self.R_cal >= SIGMA_PRE)
        sd_in = float(self.R_cal.std(ddof=1))
        self.crash_in, self.surge_in = (self.R_cal <= -sd_in), (self.R_cal >= sd_in)
        self.daily = daily                                                           # DataFrame(u · r · rf_d · re_d) 색인 거래일
        self.legs, self.rebs, self.D = legs, rebs, D
        self.crash_legs = [(l[1], l[2]) for l in legs if l[0] == "crash"]
        self.episodes = episodes_from_legs(legs, rebs, D)
        self.rf = rf
        XD.assert_scored_months([str(h) for h in self.hold])

    @classmethod
    def real(cls):
        dd = XD.decision_days(XD.INPUT_MIN_MONTH, XD.SCORE_LAST)
        spy, gspc, rf = XD.spy_tr(), XD.gspc_pr(), XD.rf_us_monthly()
        XD.assert_input_floor({"spy": spy, "gspc": gspc, "rf": rf})
        return cls.from_series(dd, spy, gspc, rf, XD.t_plus_1, XD.zigzag_inputs())

    @classmethod
    def from_series(cls, dd, spy, gspc, rf, tplus1, zz):
        hold = HOLD
        t1 = {t: tplus1(d) for t, d in dd.items()}
        sp = pd.Series(spy, dtype=float).dropna()

        def at(d):
            j = sp.index.searchsorted(pd.Timestamp(d), side="right") - 1
            return float(sp.iloc[j]) if j >= 0 and sp.index[j] == pd.Timestamp(d) else np.nan
        R_t1 = pd.Series({u: at(t1[u]) / at(t1[u - 1]) - 1.0 for u in hold})
        rfu = pd.Series(rf, dtype=float)
        Re_t1 = R_t1 - rfu.reindex(hold)
        re_cal = XS.monthly_excess(sp, rfu, dd)
        R_cal = XS.month_closes(sp, dd)
        R_cal = (R_cal / R_cal.shift(1) - 1.0).reindex(hold)
        down = down_months(gspc, hold)
        # 일간(E1)
        rows = []
        for u in hold:
            a, b = t1[u - 1], t1[u]
            seg = sp.loc[(sp.index >= a) & (sp.index <= b)]
            r = (seg / seg.shift(1) - 1.0).iloc[1:]
            n = len(r)
            rf_d = (1.0 + float(rfu.get(u, 0.0))) ** (1.0 / max(1, n)) - 1.0
            for d, x in r.items():
                rows.append((d, u, float(x), rf_d))
        daily = pd.DataFrame(rows, columns=["d", "u", "r", "rf_d"]).set_index("d")
        daily["re_d"] = daily["r"] - daily["rf_d"]
        D, P = zz
        ME = _frozen("mech_episodes")
        legs, op = ME.zigzag(D, P, ZZ_HD, ZZ_HU, ZZ_START, ZZ_END)
        rebs = ME.rebounds(D, P, legs, op, ZZ_REB)
        return cls(hold, Re_t1, re_cal.reindex(hold), R_cal, down, daily, legs, rebs, D, rf=rfu, gspc=gspc, R_t1=R_t1)


# ══════════════════════════════════════════════════════════════════════════
#  M 층
# ══════════════════════════════════════════════════════════════════════════
def daily_a(aa, MF):
    """보유월 a(색인 보유월) → 거래일 a_d(그 날이 속한 T+1 보유월의 a · 활성 아닌 달은 NaN)."""
    return pd.Series(MF.daily["u"].map(lambda u: aa.get(u, np.nan)).to_numpy(float), index=MF.daily.index)


def _days_in(idx, a, b):
    return (idx > pd.Timestamp(a)) & (idx <= pd.Timestamp(b))


def rg_abs(aa, MF):
    """M-C3 — Σ_반등일 a·r^e / Σ_급락다리일 (−a·r^e) · 분모 ≤ 0 → (None, 분모, 분자)."""
    ad = daily_a(aa, MF).fillna(0.0)
    re = MF.daily["re_d"]
    idx = MF.daily.index
    num = den = 0.0
    for a, b in MF.crash_legs:
        m = _days_in(idx, a, b)
        den += float((-ad[m] * re[m]).sum())
    for r in MF.rebs:
        m = _days_in(idx, r["a"], r["b"])
        num += float((ad[m] * re[m]).sum())
    return (num / den if den > 0 else None), den, num


def episode_scores(aa, MF):
    """에피소드 점수 N_e = Σ_다리일(−a·r^e) − Σ_반등일(a·r^e) · 켜진 적 있는가."""
    ad = daily_a(aa, MF).fillna(0.0)
    re = MF.daily["re_d"]
    idx = MF.daily.index
    out = []
    for ep in MF.episodes:
        g = sum(float((-ad[_days_in(idx, a, b)] * re[_days_in(idx, a, b)]).sum()) for a, b in ep["legs"])
        c = sum(float((ad[_days_in(idx, a, b)] * re[_days_in(idx, a, b)]).sum()) for a, b in ep["rebs"])
        span = (idx >= ep["span"][0].start_time) & (idx <= ep["span"][1].end_time)
        out.append({"span": [str(ep["span"][0]), str(ep["span"][1])], "n_legs": len(ep["legs"]), "N_e": g - c, "gain": g, "cost": c,
                    "ever_on": bool((ad[span] > 0).any())})
    return out


def jackknife(d, MF):
    """M-C5 — 에피소드 하나씩 뺀 평균 Δ ≥ 0 인 개수 · 필요 n_e − 1."""
    res = []
    for ep in MF.episodes:
        a, b = ep["span"]
        keep = ~((d.index >= a) & (d.index <= b))
        res.append(_mean(d[keep]))
    n_ok = sum(1 for x in res if x is not None and x >= 0)
    n_e = len(res)
    return {"n_e": n_e, "n_ok": n_ok, "need": max(0, n_e - 1), "pass": bool(n_e > 0 and n_ok >= n_e - 1), "means": res}


def off_delay(aa, MF):
    """보고 — 저점에 켜져 있던 다리마다 저점 뒤 a = 0 이 적용된 첫 거래일까지의 거래일 수."""
    ad = daily_a(aa, MF)
    idx = MF.daily.index
    out = []
    for a, b in MF.crash_legs:
        tb = pd.Timestamp(b)
        if tb not in idx or not (ad.get(tb, 0) > 0):
            continue
        after = ad.loc[idx > tb]
        z = np.flatnonzero(after.to_numpy() == 0)
        out.append(int(z[0] + 1) if len(z) else None)
    return out


def concentration(d):
    x = np.sort(np.asarray(d, float))[::-1]
    tot = float(np.nansum(x))
    if not (tot > 0):
        return None
    c = np.cumsum(x)
    return int(np.searchsorted(c, 0.5 * tot) + 1)


def stratified_placebo(a_dec, Re_hold, vol_dec, kappa=KAPPA10, n=PLACEBO_N, seed=PLACEBO_SEED, block=PLACEBO_BLOCK):
    """E6 — 변동성 3분위 안 12개월 토막 섞기 위약 순위(평균 Δ)."""
    a = pd.Series(a_dec, dtype=float).reindex(DEC).to_numpy(float)
    v = pd.Series(vol_dec, dtype=float).reindex(DEC).to_numpy(float)
    if np.isnan(a).any():
        return None
    nb = len(a) // block
    blocks = [a[i * block:(i + 1) * block] for i in range(nb)]
    bv = np.array([np.nanmean(v[i * block:(i + 1) * block]) for i in range(nb)])
    order = np.argsort(np.argsort(bv, kind="mergesort"), kind="mergesort")
    terc = (order * 3) // nb
    obs = _mean(delta_series(pd.Series(a, index=DEC), Re_hold, kappa)[0])
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n):
        perm = list(range(nb))
        for g in range(3):
            ids = [i for i in range(nb) if terc[i] == g]
            sh = list(rng.permutation(ids))
            for i, j in zip(ids, sh):
                perm[i] = j
        ap = np.concatenate([blocks[j] for j in perm])
        draws.append(_mean(delta_series(pd.Series(ap, index=DEC), Re_hold, kappa)[0]))
    dr = np.array(draws, float)
    rank = float(((dr < obs).sum() + 0.5 * (dr == obs).sum()) / len(dr))
    return {"rank": rank, "n": n, "seed": seed, "n_blocks": nb}


def timing_regressions(aa, Re_hold):
    """E7 — HM · TM · 위험 분리."""
    R = pd.Series(Re_hold, dtype=float).reindex(aa.index)
    ok = R.notna() & aa.notna()
    y = (-aa[ok] * R[ok]).to_numpy(float)
    r = R[ok].to_numpy(float)
    out = {}
    try:
        b, t = nw_ols(y, np.column_stack([np.ones(len(r)), r, np.maximum(0.0, -r)]))
        out["HM"] = {"gamma": float(b[2]), "t": float(t[2])}
    except Exception:                                                    # noqa: BLE001
        out["HM"] = None
    try:
        b, t = nw_ols(y, np.column_stack([np.ones(len(r)), r, r * r]))
        out["TM"] = {"gamma": float(b[2]), "t": float(t[2])}
    except Exception:                                                    # noqa: BLE001
        out["TM"] = None
    on, off = r[aa[ok].to_numpy() > 0], r[aa[ok].to_numpy() == 0]
    out["var_ratio_on_off"] = float(np.var(on, ddof=1) / np.var(off, ddof=1)) if len(on) > 2 and len(off) > 2 else None
    return out


def hit_rates(aa, MF):
    on = aa.reindex(MF.hold) > 0
    dn, cr = MF.down, MF.crash
    re_on = _mean(MF.Re_t1[on]) if on.any() else None
    return {"P_on_given_down": float(on[dn].mean()) if dn.any() else None, "P_on_given_crash": float(on[cr].mean()) if cr.any() else None,
            "precision_down_given_on": float(dn[on].mean()) if on.any() else None, "n_on": int(on.sum()), "n_down": int(dn.sum()),
            "n_crash": int(cr.sum()), "n_surge": int(MF.surge.sum()),
            "breakeven": {"on_month_mean_Re_pct": (None if re_on is None else re_on * 100.0), "need_pct": dict(BREAKEVEN_ON_RE),
                          "meets_alpha_D_0": (None if re_on is None else bool(re_on * 100.0 <= BREAKEVEN_ON_RE["alpha_D_0"])),
                          "meets_alpha_D_minus0.2": (None if re_on is None else bool(re_on * 100.0 <= BREAKEVEN_ON_RE["alpha_D_minus0.2"]))}}


def turnover_stats(aa):
    x = aa.fillna(0.0)
    da = x.diff().abs()
    da.iloc[0] = abs(x.iloc[0])
    yrs = len(x) / 12.0
    sw = int((da > 0).sum())
    slow_years = {str(y): int((da[[p.year == y for p in da.index]] > 0).sum()) for y in (2008, 2022)}
    return {"on_share": float((x > 0).mean()), "mean_a": float(x.mean()), "sum_abs_da": float(da.sum()), "n_switch": sw,
            "switches_slow_bear_years": slow_years, "nav_turnover_per_year_a1": float(0.2 * da.sum() / yrs),
            "nav_turnover_per_year_aop": float(0.2 * A_OP * da.sum() / yrs)}


def yearly(x, idx=None):
    s = pd.Series(x, dtype=float)
    g = s.groupby([p.year for p in s.index]).sum()
    return {str(k): float(v) for k, v in g.items()}


def m_arm(a_dec, MF, kappa=KAPPA10, full=True, vol_dec=None):
    """한 팔의 M 층 표 — 관문(주 가설만 판정에 쓴다) · 보고."""
    d, abar, aa = delta_series(a_dec, MF.Re_t1, kappa)
    d20, _, _ = delta_series(a_dec, MF.Re_t1, KAPPA20, abar=abar)
    t = nw_t(d.to_numpy())
    down, crash = MF.down.reindex(d.index), MF.crash.reindex(d.index)
    h1 = (d.index >= pd.Period(HALVES[0][0], "M")) & (d.index <= pd.Period(HALVES[0][1], "M"))
    h2 = (d.index >= pd.Period(HALVES[1][0], "M")) & (d.index <= pd.Period(HALVES[1][1], "M"))
    ool = (d.index >= pd.Period(OOL[0], "M")) & (d.index <= pd.Period(OOL[1], "M"))
    rg, den, num = rg_abs(aa, MF)
    jk = jackknife(d, MF)
    res = {"window": [str(d.index[0]), str(d.index[-1])] if len(d) else None, "n": int(len(d)), "abar": abar,
           "mean_delta": _mean(d), "nw_t": t, "down_mean": _mean(d, down), "crash_mean": _mean(d, crash),
           "rg_abs": rg, "rg_den": den, "rg_num": num, "half1_mean": _mean(d[h1]), "half2_mean": _mean(d[h2]), "ool_mean": _mean(d[ool]),
           "n_ool": int(ool.sum()), "jackknife": jk, "mean_delta_20bp": _mean(d20)}
    h2a = aa.index >= pd.Period(HALVES[1][0], "M")
    res["half2_on_share"] = float((aa[h2a] > 0).mean()) if h2a.any() else None           # 2016-09 ~ 2026-08 반쪽(공개 보기) · 20년 켜짐 비율은 reports(캐시)
    res["gates"] = {"M-C1": _ge(t, CRIT["T240_L6"]), "M-C2": _gt(res["down_mean"]) and _gt(res["crash_mean"]),
                    "M-C3": bool(rg is not None and rg <= RG_MAX), "M-C4": _gt(res["half1_mean"]) and _gt(res["half2_mean"]) and _ge(res["ool_mean"]),
                    "M-C5": jk["pass"], "M-C6": _gt(res["mean_delta_20bp"])}
    res["pass_all"] = all(res["gates"].values())
    res["p_one_sided_normal"] = norm_sf(t)
    if not full:
        return res, d, aa
    gfc = (d.index >= pd.Period(GFC_EXCL[0], "M")) & (d.index <= pd.Period(GFC_EXCL[1], "M"))
    res["reports"] = {
        "gfc_excluded_mean": _mean(d[~gfc]), "off_delay_td": off_delay(aa, MF), "episodes": episode_scores(aa, MF),
        "concentration_50pct_months": concentration(d), "timing": timing_regressions(aa, MF.Re_t1), "hits": hit_rates(aa, MF),
        "turnover": turnover_stats(aa), "crash_in_window_sd_mean": _mean(d, MF.crash_in.reindex(d.index)),
        "surge_mean": _mean(d, MF.surge.reindex(d.index)), "market_part_mean": _mean(market_part(aa, MF.Re_t1)),
        "yearly_market_part_dref": {k: v * D_REF for k, v in yearly(market_part(aa, MF.Re_t1)).items()},
        "yearly_delta_dref": {k: v * D_REF for k, v in yearly(d).items()}}
    ys = res["reports"]["yearly_delta_dref"]
    res["reports"]["worst_year_dref"] = min(ys.items(), key=lambda kv: kv[1]) if ys else None
    eps = [e for e in res["reports"]["episodes"] if e["ever_on"]]
    k = sum(1 for e in eps if e["N_e"] > 0)
    res["reports"]["episode_sign"] = {"n_ever_on": len(eps), "n_pos": k, "binom_p": binom_sf(k, len(eps))}
    d0, _, _ = delta_series(a_dec, MF.Re_d0, kappa)
    res["reports"]["d0_row"] = {"mean_delta": _mean(d0), "nw_t": nw_t(d0.to_numpy()),
                                "d0_minus_t1": (_mean(d0) - res["mean_delta"]) if (_mean(d0) is not None and res["mean_delta"] is not None) else None}
    if vol_dec is not None:
        res["reports"]["placebo_stratified"] = stratified_placebo(a_dec, MF.Re_t1, vol_dec, kappa)
    return res, d, aa


def m_layer(F, MF, arms=None, blr=None, comp_w=None, french=None):
    """F = x_signals.signal_frame(…) · MF = MFrame · arms = 측정 팔 {이름: a_dec} 추가 · blr = x_blr.blr_path 결과 ·
    comp_w = 일간 위치(Series) · french = French Mkt-RF 달(Period 색인 · 소수) — 돌려주는 것 dict(20년 · 캐시 전용)."""
    a = F["X-BEAR"].reindex(DEC)
    if a.isna().any():
        raise SystemExit("🚨 X-BEAR 결정 240 달에 빈칸 — 워밍업 오류")
    main, d_main, aa = m_arm(a, MF, full=True, vol_dec=F["vol63"])
    out = {"X-BEAR": main}
    abar = main["abar"]
    # 쌍둥이(노출 맞춤)
    sma, k_sma, ok_sma = XS.scale_to_mean(F["T-SMA200"].reindex(DEC), abar)
    tw = {}
    for nm, s in (("T-SMA200", sma), ("T-VOL", XS.vol_twin(F["vol63"].reindex(DEC), abar))):
        r, _, _ = m_arm(s, MF, full=False)
        tw[nm] = {"mean_delta": r["mean_delta"], "nw_t": r["nw_t"], "abar": r["abar"],
                  "bear_minus_twin": (main["mean_delta"] - r["mean_delta"]) if (r["mean_delta"] is not None and main["mean_delta"] is not None) else None}
    tw["T-SMA200"].update({"scale": k_sma, "scale_matched": ok_sma})
    # 정적 쌍둥이는 주 통계 안(Δ 가 ā 대비)
    out["twins"] = tw
    # 측정 팔
    meas = {}
    arms = dict(arms or {})
    arms.setdefault("X-COMP", F["X-COMP"])
    arms.setdefault("X-CRED", F["X-CRED"])
    if "X-JM" in F:
        arms.setdefault("X-JM", F["X-JM"])
    if blr is not None:
        arms.setdefault("X-BLR", blr["a"])
    for nm, s in arms.items():
        s = pd.Series(s, dtype=float).reindex(DEC)
        if s.notna().sum() < 12:
            meas[nm] = {"status": "활성 달 부족", "n": int(s.notna().sum())}
            continue
        r, dd_, aa_ = m_arm(s, MF, full=False)
        first = s.first_valid_index()
        meas[nm] = {k: r[k] for k in ("n", "abar", "mean_delta", "nw_t", "down_mean", "crash_mean", "rg_abs", "mean_delta_20bp")}
        meas[nm]["first_active"] = str(first) if first is not None else None
        meas[nm]["p"] = norm_sf(r["nw_t"])
        meas[nm]["on_share"] = float((aa_ > 0).mean()) if len(aa_) else None
    if comp_w is not None:
        meas["X-COMP-W"] = comp_w_arm(comp_w, MF)
    # Nagel 쌍둥이(BLR 대조)
    if blr is not None and blr["a"].reindex(DEC).notna().sum() >= 12:
        act = blr["a"].reindex(DEC).notna()
        zt, zs = XS.nagel_twin(F["nagel_z"].reindex(DEC), float(blr["a"].reindex(DEC)[act].mean()), mask=act)
        zt = zt.where(act)
        r, _, _ = m_arm(zt, MF, full=False)
        meas["X-BLR"]["nagel_twin"] = {"mean_delta": r["mean_delta"], "nw_t": r["nw_t"], "z_star": zs,
                                       "blr_minus_nagel": (meas["X-BLR"]["mean_delta"] - r["mean_delta"]) if (r["mean_delta"] is not None and meas["X-BLR"].get("mean_delta") is not None) else None}
    if "X-COMP" in meas and "status" not in meas["X-COMP"]:
        meas["X-COMP"]["note"] = ("정의 얼림(VTS 성분 그대로) · VTS 성분의 평균 타이밍 부호는 Fassas–Hourvouliades 2019 원문에서 반대(역행) — 공개 · "
                                  "Correction 켜짐의 근거는 신용 · 변동성 문헌(GHM 아님)")
    for nm, st in XS.ARM_STATUS.items():                                 # lit_open 판정으로 단독 팔이 빠진 것(값 없이 상태만)
        if st == "dropped":
            meas[nm] = {"status": "dropped", "why": "lit_open.json — 문헌이 반대 부호(단독 측정 팔 삭제 · COMP 성분으로만 남는다)"}
    fam = {k: meas[k].get("p") for k in XS.M_BY_FAMILY if k in meas}
    rej = by_fdr(fam)
    for k in fam:
        meas[k]["by_reject_q10"] = rej.get(k)
    out["measurement"] = meas
    out["by_family"] = list(fam)
    # COMP 켜진 달 GHM 상태 분포
    comp_on = F["X-COMP"].reindex(DEC) > 0
    gh = F["ghm"].reindex(DEC)
    out["comp_on_ghm"] = {s: int(((gh == s) & comp_on).sum()) for s in XS.GHM_STATES}
    # French Mkt-RF 판(부호) · 상태 일치율
    if french is not None:
        fr = pd.Series(french, dtype=float)
        aF = XS.bear_state(fr)
        common = aF.reindex(DEC).notna() & a.notna()
        dF, _, _ = delta_series(aF.reindex(DEC), fr.reindex(HOLD))
        out["french_version"] = {"state_agree": float((aF.reindex(DEC)[common] == a[common]).mean()) if common.any() else None,
                                 "n_common": int(common.sum()), "mean_delta_french_mkt": _mean(dF),
                                 "mean_delta_sign_same": (None if (_mean(dF) is None or main["mean_delta"] is None) else bool(np.sign(_mean(dF)) == np.sign(main["mean_delta"])))}
    out["context"] = {"bonferroni_z_30_families": BONF_Z, "lab_discovery_t": LAB_T, "lab_discovery": _ge(main["nw_t"], LAB_T)}
    out["_series"] = {"delta": d_main, "a_hold": aa}
    return out


def comp_w_arm(pos, MF, kappa=KAPPA10):
    """COMP-W — 일간 위치 → 날마다 −(a_d − ā)·r^e_d − κ|Δa|(체결일) → 보유월(T+1 창) 합 · NW(6) t(보고)."""
    p = pd.Series(pos, dtype=float).reindex(MF.daily.index)
    act = p.notna()
    if act.sum() < 252:
        return {"status": "활성 날 부족"}
    pa = p[act]
    abar = float(pa.mean())
    re = MF.daily["re_d"][act]
    cost = kappa * pa.diff().abs().fillna(abs(pa.iloc[0]))
    dd_ = -(pa - abar) * re - cost
    m = dd_.groupby(MF.daily["u"][act]).sum()
    t = nw_t(m.to_numpy())
    return {"n_months": int(len(m)), "abar": abar, "mean_delta": _mean(m), "nw_t": t, "p": norm_sf(t),
            "down_mean": _mean(m, MF.down.reindex(m.index).fillna(False)), "crash_mean": _mean(m, MF.crash.reindex(m.index).fillna(False)),
            "on_share_days": float((pa > 0).mean()), "n_switch": int((pa.diff().abs() > 0).sum()), "first_active": str(pa.index[0].date())}


# ══════════════════════════════════════════════════════════════════════════
#  I 층
# ══════════════════════════════════════════════════════════════════════════
def i_layer(views, meta=None, views_usd=None, french_agree=None):
    """views = x_intl.primary_view(frames, meta) — {cc: DataFrame(re_sig · re_hold · down · tr)} · views_usd = 같은 시장 USD 판(E12 · 보고) ·
    french_agree = x_intl.french_sign_agreement(frames, French)(자료 충실도 · 보고)."""
    res = _i_core(views)
    res["mode"] = (meta or {}).get("mode")
    rep = {}
    if views_usd is not None and (meta or {}).get("mode") != "usd":
        u = _i_core(views_usd)
        rep["usd_version"] = {k: u[k] for k in ("dk_t", "pooled_mean", "n_markets_pos", "pooled_ool_mean", "mean_of_market_down_means", "gates")}
        rep["usd_version"]["per_market_mean"] = {cc: v["mean_delta"] for cc, v in u["per_market"].items()}
    if french_agree is not None:
        rep["french_sign_agreement"] = french_agree
    res["reports"] = rep
    return res


def _i_core(views):
    per, deltas, downs = {}, {}, {}
    for cc, v in views.items():
        a = XS.bear_state(v["re_sig"]).reindex(DEC)
        if a.isna().any():
            raise SystemExit("🚨 %s BEAR 결정 240 달에 빈칸" % cc)
        d, abar, aa = delta_series(a, v["re_hold"], kappa=0.0)
        deltas[cc] = d
        dn = v["down"].reindex(d.index).astype(bool)
        cl = crash_labels_market(v)
        per[cc] = {"n": int(len(d)), "abar": abar, "on_share": float((aa > 0).mean()), "mean_delta": _mean(d), "nw_t": nw_t(d.to_numpy()),
                   "down_mean": _mean(d, dn), "n_down": int(dn.sum()),
                   "crash_mean": _mean(d, cl["crash"].reindex(d.index)), "surge_mean": _mean(d, cl["surge"].reindex(d.index))}
        downs[cc] = per[cc]["down_mean"]
    D = pd.DataFrame(deltas).reindex(HOLD)
    pooled = D.mean(axis=1, skipna=False)
    t = nw_t(pooled.to_numpy())
    ool = (pooled.index >= pd.Period(OOL[0], "M")) & (pooled.index <= pd.Period(OOL[1], "M"))
    n_pos = sum(1 for cc in per if _gt(per[cc]["mean_delta"]))
    mdown = [x for x in downs.values() if x is not None]
    res = {"window": [XD.SCORE_FIRST, XD.SCORE_LAST], "n_markets": len(per), "markets": list(per), "dk_t": t, "pooled_mean": _mean(pooled),
           "n_markets_pos": n_pos, "pooled_ool_mean": _mean(pooled[ool]), "mean_of_market_down_means": (float(np.mean(mdown)) if mdown else None),
           "per_market": per}
    res["gates"] = {"I-C1": _ge(t, CRIT["T240_L6"]), "I-C2": bool(n_pos >= I_BREADTH), "I-C3": _ge(res["pooled_ool_mean"]),
                    "I-C4": _gt(res["mean_of_market_down_means"])}
    res["pass_all"] = all(res["gates"].values())
    h2 = pooled.index >= pd.Period(XD.PUBLIC_FROM, "M")
    res["half2"] = {"window": [XD.PUBLIC_FROM, XD.SCORE_LAST], "pooled_mean": _mean(pooled[h2]), "n": int(h2.sum())}
    res["_series"] = {"pooled": pooled}
    return res


def crash_labels_market(v):
    r = v["tr"].reindex(HOLD)
    sd = float(r.std(ddof=1))
    return {"crash": r <= -sd, "surge": r >= sd}


# ══════════════════════════════════════════════════════════════════════════
#  G 층
# ══════════════════════════════════════════════════════════════════════════
def rolling_beta(y, x, rf, t_index, min_n=12, max_n=36):
    """결정 달 t 마다 t 이하 최근 ≤ max_n(≥ min_n) 달 OLS 기울기((y − rf) on (x − rf))."""
    Y = pd.Series(y, dtype=float) - pd.Series(rf, dtype=float)
    X = pd.Series(x, dtype=float) - pd.Series(rf, dtype=float)
    ok = Y.notna() & X.notna()
    Y, X = Y[ok], X[ok]
    out = {}
    for t in t_index:
        yy, xx = Y.loc[:t].iloc[-max_n:], X.loc[:t].iloc[-max_n:]
        if len(yy) < min_n or float(xx.var(ddof=1)) <= 0:
            out[t] = np.nan
            continue
        out[t] = float(np.cov(xx, yy, ddof=1)[0, 1] / np.var(xx, ddof=1))
    return pd.Series(out, dtype=float)


def dilution_c(e_ann, x_core_ann):
    """희석 몫 c = 1 + e/x · [0, 1] · x ≤ 0 이거나 e ≥ 0 이면 1."""
    if x_core_ann is None or e_ann is None or x_core_ann <= 0 or e_ann >= 0:
        return 1.0
    return float(np.clip(1.0 + e_ann / x_core_ann, 0.0, 1.0))


def g_core(a_dec, core, dproxy, mkt, rf, down, crash, surge, app_on=True, cost=COST10, hold=HOLD):
    """한 코어의 G 표 — 단계 효과 e · 펀드 X · 코어만 V · 희석 · 관문."""
    C = pd.Series(core, dtype=float).reindex(hold)
    Dp = pd.Series(dproxy, dtype=float).reindex(hold)
    M = pd.Series(mkt, dtype=float).reindex(hold)
    a = pd.Series(a_dec, dtype=float).reindex(hold - 1)
    if app_on:
        bC = rolling_beta(core, mkt, rf, hold - 1)
        bD = rolling_beta(dproxy, mkt, rf, hold - 1)
        app = ((bC - bD) >= XS.APP_MIN).astype(float)
        app[bC.isna() | bD.isna()] = 0.0
    else:
        bC = bD = None
        app = pd.Series(1.0, index=hold - 1)
    at = (a * app).fillna(0.0)
    at_h = pd.Series(at.to_numpy(), index=hold)
    prev = at_h.shift(1).fillna(0.0)
    ok = C.notna() & Dp.notna() & M.notna()
    e = (0.1 * at_h * (Dp - C) - cost * 0.2 * (at_h - prev).abs())[ok]
    V = (0.9 * M + 0.1 * C)[ok]
    X = V + e
    Mk = M[ok]
    x_core = float((V - Mk).mean() * 12)
    e_ann, e_lb = lb80(e.to_numpy())
    c = dilution_c(e_ann, x_core)
    Dil = V + 0.1 * (c - 1.0) * (C[ok] - Mk)
    dn, cr, sg = down.reindex(e.index).fillna(False), crash.reindex(e.index).fillna(False), surge.reindex(e.index).fillna(False)
    g_down_X, g_down_D = _mean((X - V)[dn]), _mean((Dil - V)[dn])
    g_cr_X, g_cr_D = _mean((X - V)[cr]), _mean((Dil - V)[cr])
    yrs = range(FULL_YEARS[0], FULL_YEARS[1] + 1)

    def won(F_):
        n = 0
        for y in yrs:
            m = np.array([p.year == y for p in F_.index])
            if m.sum() < 12:
                continue
            if float(np.prod(1 + F_[m]) - np.prod(1 + Mk[m])) > 0:
                n += 1
        return n
    wX, wV = won(X), won(V)
    s_cr, s_sg = float(e[cr].sum()), float(e[sg].sum())
    res = {"window": [str(e.index[0]), str(e.index[-1])] if len(e) else None, "n": int(len(e)), "on_share": float((at > 0).mean()),
           "app_off_months": int(((a > 0) & (app == 0)).sum()), "e_ann": e_ann, "e_lb80": e_lb, "x_core_ann": x_core, "dilution_c": c,
           "down_mean_X": g_down_X, "down_mean_dil": g_down_D, "crash_mean_X": g_cr_X, "crash_mean_dil": g_cr_D,
           "sum_crash_e": s_cr, "sum_surge_e": s_sg, "years_won_X": wX, "years_won_core": wV,
           "beta_on": _cond_beta(C[ok], Dp[ok], Mk, rf, at_h[ok] > 0), "alpha_forgone_on": _mean((Dp - C)[ok][at_h[ok] > 0])}
    res["identity"] = _g_identity(e, at_h[ok], C[ok], Dp[ok], Mk, rf)
    res["yearly_e"] = yearly(e)
    res["gates"] = {"G-C1": bool(g_down_X is not None and g_down_D is not None and g_down_X >= g_down_D - 1e-15 and
                                 g_cr_X is not None and g_cr_D is not None and g_cr_X > g_cr_D and g_cr_X > 0),
                    "G-C2": bool(s_sg >= -0.5 * s_cr and s_cr > 0), "G-C3": bool(wX >= wV - 1),
                    "G-C4": bool(e_lb is not None and e_lb * 100.0 > NI_LB)}
    res["pass_all"] = all(res["gates"].values())
    res["_series"] = {"e": e, "X": X, "V": V, "mkt": Mk, "app": app, "a_eff": at}
    return res


def _g_identity(e, a_h, C, D, M, rf):
    """E11 — e 대 0.1·ã·[(β_D − β_C)(M − RF) + (α_D − α_C)] (창 전체 월간 OLS) · 잔차 평균 · sd · 켜진 달 수."""
    rfv = pd.Series(rf, dtype=float).reindex(M.index).fillna(0.0)
    x = (M - rfv).to_numpy(float)
    ab = {}
    for nm, s in (("C", C), ("D", D)):
        y = (s - rfv).to_numpy(float)
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 12:
            return None
        b = float(np.cov(x[ok], y[ok], ddof=1)[0, 1] / np.var(x[ok], ddof=1))
        ab[nm] = (float(y[ok].mean() - b * x[ok].mean()), b)
    pred = 0.1 * a_h.reindex(e.index).to_numpy(float) * ((ab["D"][1] - ab["C"][1]) * x + (ab["D"][0] - ab["C"][0]))
    pred = pd.Series(pred, index=e.index)
    res = (e - pred).dropna()
    return {"beta_C": ab["C"][1], "beta_D": ab["D"][1], "alpha_C_m": ab["C"][0], "alpha_D_m": ab["D"][0],
            "resid_mean": _mean(res), "resid_sd": (float(res.std(ddof=1)) if len(res) > 2 else None), "n_on": int((a_h > 0).sum())}


def _cond_beta(C, D, M, rf, on):
    rfv = pd.Series(rf, dtype=float).reindex(M.index).fillna(0.0)
    out = {}
    for nm, s in (("core", C), ("D", D)):
        for tag, msk in (("on", on), ("off", ~on)):
            y, x = (s - rfv)[msk], (M - rfv)[msk]
            out["%s_%s" % (nm, tag)] = float(np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)) if len(y) > 2 and np.var(x, ddof=1) > 0 else None
    return out


GROWTH_UNWIND = ("2021-02", "2024-07")                     # 명세 growth_proxy_20y.reports_only «성장 되감기 달(2021-02 · 2024-07 · 2025)» — 서술만


def g_layer(a_dec, G, down, crash, surge, fg_arms=None, dproxy_downgraded=False, mom_panic=True, episodes=None, m_lookahead=None):
    """G = {"mkt", "rf", "cores": {LG, EXG, MOM, QG, IWF}, "d": D 대리, "spy": SPY TR 달, "rf_us"} (소수 · 달력 달 색인).
    episodes = M 층 에피소드 [{"span": (Period, Period)}](월 근사 보고) · m_lookahead = M 층 D0 − T+1 평균 Δ 차(SN-1.4 · G 선견 상한 보정 기록)."""
    cores = G["cores"]
    last = pd.Period(G.get("last", XD.SCORE_LAST), "M")
    hold = _pr(XD.SCORE_FIRST, min(last, HOLD[-1]))
    out = {"dproxy_downgraded": bool(dproxy_downgraded), "window": [str(hold[0]), str(hold[-1])],
           "lookahead_note": {"m_d0_minus_t1_unit_d": m_lookahead,
                              "rule": "G 는 월말 판정 · T+1 없음(하루 선견) — M 층의 (D0 − T+1) 평균 Δ 차를 G 수치의 선견 상한 보정으로 적는다 · G 를 M 과 나란히 비교하지 않는다(SN-1.4)"}}
    for nm, core in cores.items():
        if nm == "IWF":
            r = g_core(a_dec, core, G["d"], G["spy"], G["rf_us"], down, crash, surge, hold=hold)
        else:
            r = g_core(a_dec, core, G["d"], G["mkt"], G["rf"], down, crash, surge, hold=hold)
        e = r["_series"]["e"]
        if episodes:
            r["episodes_e"] = [{"span": [str(ep["span"][0]), str(ep["span"][1])],
                                "sum_e": float(e[(e.index >= ep["span"][0]) & (e.index <= ep["span"][1])].sum())} for ep in episodes]
        r["growth_unwind"] = {m: (float(e.get(pd.Period(m, "M"))) if pd.Period(m, "M") in e.index else None) for m in GROWTH_UNWIND}
        r["growth_unwind"]["2025"] = float(e[[p.year == 2025 for p in e.index]].sum()) if len(e) else None
        out[nm] = r
    out["LG_binding"] = not dproxy_downgraded
    out["pass_LG"] = out["LG"]["pass_all"]
    if mom_panic and "MOM" in cores:
        m24 = (1 + pd.Series(G["mkt"], dtype=float)).rolling(24, min_periods=24).apply(np.prod, raw=True) - 1
        pan = (m24.reindex(hold - 1) < 0).to_numpy()
        e = out["MOM"]["_series"]["e"]
        msk = pd.Series(pan, index=hold).reindex(e.index).fillna(False)
        out["MOM"]["panic_rebound"] = {"n": int(msk.sum()), "mean_e": _mean(e[msk])}
    # F_G 측정 팔(GVTREND · 쌍둥이 RRSHOCK) — 단계 효과의 정적 쌍둥이 대비 Δ^G = −0.1·(ã − ā)·(C − D) − 비용
    fg = {}
    for nm, s in (fg_arms or {}).items():
        s = pd.Series(s, dtype=float).reindex(hold - 1)
        act = s.notna()
        if act.sum() < 12:
            fg[nm] = {"status": "활성 달 부족"}
            continue
        C = pd.Series(cores["LG"], dtype=float).reindex(hold)
        Dp = pd.Series(G["d"], dtype=float).reindex(hold)
        sp = s[act]
        abar = float(sp.mean())
        sh = pd.Series(sp.to_numpy(), index=sp.index + 1)
        dg = (0.1 * (sh - abar) * (Dp - C).reindex(sh.index) - COST10 * 0.2 * (sh - sh.shift(1).fillna(0.0)).abs()).dropna()
        t = nw_t(dg.to_numpy())
        fg[nm] = {"n": int(len(dg)), "abar": abar, "mean": _mean(dg), "nw_t": t, "p": norm_sf(t), "status": XS.ARM_STATUS.get(nm),
                  "first_active": str(sp.index[0])}
    fam = {k: fg[k]["p"] for k in XS.FG_FAMILY if k in fg and fg[k].get("p") is not None}
    rej = by_fdr(fam)
    for k in fam:
        fg[k]["by_reject_q10"] = rej[k]
    out["F_G"] = fg
    return out


# ══════════════════════════════════════════════════════════════════════════
#  S 층(x_adapter 가 준 월 계열 — % 단위 · 보유월 2016-09 ~ 2026-08)
# ══════════════════════════════════════════════════════════════════════════
def s_layer(S):
    """S = x_adapter.s_series() 결과: hold · a(보유월 적용 a · APP 뒤 · 단위 1) · Re_m(시장 초과 %) · down · crash · d_ok · turn ·
    arms{V0, X, X_half, STATIC, DIL, IDX, CASH, X20, V0_20}(주 행 T+1 · 펀드 월 초과 % · 펀드 − 지수) · arms_d0{X, V0}(D0 행 · 보고) ·
    sleeve{V0, D}(슬리브 월 %) · index(지수 월 %) · beta_C · beta_D(사전 β̂) · evals(얼린 qbatch_core.evaluate 요약) · pairing_B · pairing_C."""
    hold = pd.PeriodIndex(S["hold"], freq="M")
    XD.assert_scored_months([str(h) for h in hold], first=XD.S_WIN[0], last=XD.S_WIN[1], n_max=120)
    V0 = pd.Series(S["arms"]["V0"], index=hold, dtype=float)
    X = pd.Series(S["arms"]["X"], index=hold, dtype=float)
    e = X - V0                                                      # 단계 효과(펀드 %p/월)
    a = pd.Series(S["a"], index=hold, dtype=float)
    Rm = pd.Series(S["Re_m"], index=hold, dtype=float)
    dn = pd.Series(S["down"], index=hold, dtype=bool)
    cr = pd.Series(S["crash"], index=hold, dtype=bool)
    e_ann, e_lb = lb80(e.to_numpy())
    g_d, g_c = _mean(e, dn), _mean(e, cr)
    on = a > 0
    slope = None
    if on.sum() >= 3:
        xx = (-a * Rm)[on].to_numpy(float)
        yy = e[on].to_numpy(float)
        if np.var(xx) > 0:
            slope = float(np.polyfit(xx, yy, 1)[0])
    ix = pd.Series(S["index"], index=hold, dtype=float)
    bD = _beta_on(pd.Series(S["sleeve"]["D"], index=hold, dtype=float), ix, on)
    bC = _beta_on(pd.Series(S["sleeve"]["V0"], index=hold, dtype=float), ix, on)
    d_ok = list(S["d_ok"])
    res = {"window": [XD.S_WIN[0], XD.S_WIN[1]], "n": int(len(hold)), "on_share": float(on.mean()), "e_ann": e_ann, "e_lb80": e_lb,
           "g_down": g_d, "g_crash": g_c, "slope_on": slope, "beta_on_D": bD, "beta_on_C": bC, "turn": S.get("turn"),
           "n_d_ok": int(sum(bool(x) for x in d_ok))}
    res["gates"] = {"S-C1": bool(len(d_ok) == 120 and all(d_ok) and S.get("turn") is not None and S["turn"] <= S_TURN_MAX),
                    "S-C2": bool(slope is not None and slope > 0 and bD is not None and bC is not None and bD < bC),
                    "S-C3": bool(e_lb is not None and e_lb > NI_LB),
                    "S-C4": bool(g_d is not None and g_c is not None and e_ann is not None and g_d >= max(0.0, -DIL_DOWN * e_ann) and g_c > max(0.0, -DIL_CRASH * e_ann))}
    res["pass_all"] = all(res["gates"].values())
    rep = {}
    for nm, s in S["arms"].items():
        s = pd.Series(s, index=hold, dtype=float)
        ann = float(s.mean() * 12)
        rep[nm] = {"ann_ex": ann, "down_mean": _mean(s, dn), "crash_mean": _mean(s, cr), "years_won": _years_won(s, ix, S_YEARS)}
    res["arms"] = rep
    arm = lambda nm: pd.Series(S["arms"][nm], index=hold, dtype=float) if nm in S["arms"] else None
    res["half_a_op"] = {"e_ann": (lb80((arm("X_half") - V0).to_numpy())[0] if arm("X_half") is not None else None), "a_op": A_OP,
                        "lb80_operating_need": NI_LB * A_OP}
    if arm("X20") is not None and arm("V0_20") is not None:
        e20 = arm("X20") - arm("V0_20")
        res["cost20"] = {"e_ann": lb80(e20.to_numpy())[0], "g_down": _mean(e20, dn), "g_crash": _mean(e20, cr)}
    d0 = S.get("arms_d0") or {}
    if "X" in d0 and "V0" in d0:                                     # D0 행(얼린 mix_fr · d_m 종가 되맞춤) — 보고만
        e0 = pd.Series(d0["X"], index=hold, dtype=float) - pd.Series(d0["V0"], index=hold, dtype=float)
        res["d0_row"] = {"e_ann": lb80(e0.to_numpy())[0], "g_down": _mean(e0, dn), "g_crash": _mean(e0, cr),
                         "d0_minus_t1_ann": (None if lb80(e0.to_numpy())[0] is None or e_ann is None else lb80(e0.to_numpy())[0] - e_ann)}
    bC_ex = pd.Series(S.get("beta_C") or [np.nan] * len(hold), index=hold, dtype=float)
    bD_ex = pd.Series([np.nan if v is None else v for v in (S.get("beta_D") or [None] * len(hold))], index=hold, dtype=float)
    pred = -0.1 * a * (bC_ex - bD_ex) * Rm                          # 시장 몫 −d_t·R^e(사전 β̂ · %p)
    resid = (e - pred)[on]
    res["identity"] = {"pred_market_part_mean_on": _mean(pred[on]), "resid_mean_on": _mean(resid), "n_on": int(on.sum()),
                       "note": "잔차 ≈ −0.1·a·(α_C − α_D) − 양식 잡음 − 비용(켜진 달)"}
    ev = S.get("evals") or {}
    if "X" in ev and "V0" in ev:
        def mech(nm, key):
            m = ((ev[nm].get("mech") or {}).get(key) or {})
            return (m.get("n") or 0) * (m.get("mean") or 0.0), m.get("win"), m.get("n")
        gl = mech("X", "crash_legs")[0] - mech("V0", "crash_legs")[0]
        rb = mech("X", "rebounds")[0] - mech("V0", "rebounds")[0]
        res["events"] = {nm: {k: ev[nm].get(k) for k in ("crash_won", "surge_won", "episodes", "mech", "years", "years_won", "roll12", "hedge_ctrl",
                                                           "down_mean", "down_n", "sleeve_beta")} for nm in ev}
        res["legs_vs_rebounds"] = {"gain_crash_legs": gl, "cost_rebounds": -rb, "ratio": (gl / -rb) if rb < 0 else None}
    for k in ("pairing_B", "pairing_C", "dil_c", "abar", "turns"):
        if k in S:
            res[k] = S[k]
    res["_series"] = {"e": e}
    return res


def _beta_on(y, x, on):
    y, x = y[on], x[on]
    if len(y) < 3 or float(np.var(x, ddof=1)) <= 0:
        return None
    return float(np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1))


def _years_won(ex, ix, yrs):
    n = 0
    for y in range(yrs[0], yrs[1] + 1):
        m = np.array([p.year == y for p in ex.index])
        if m.sum() < 12:
            continue
        f = (ix[m] + ex[m]) / 100.0
        if float(np.prod(1 + f) - np.prod(1 + ix[m] / 100.0)) > 0:
            n += 1
    return n


# ══════════════════════════════════════════════════════════════════════════
#  라벨 · 운용 결정 · 공개 보기
# ══════════════════════════════════════════════════════════════════════════
def labels(M, I, G, S):
    m_ok = bool(M and M["X-BEAR"]["pass_all"])
    i_ok = bool(I and I["pass_all"])
    g_bind = bool(G and G.get("LG_binding", True))
    g_ok = bool(G and G["pass_LG"]) if g_bind else True
    s_ok = bool(S and S["pass_all"])
    rep = m_ok and i_ok
    cand = rep and g_ok and s_ok
    lab = {LABELS[0]: m_ok, LABELS[1]: i_ok, LABELS[2]: rep, LABELS[3]: cand,
           LABELS[4]: bool(rep and M and _ge(M["X-BEAR"]["nw_t"], LAB_T))}
    lab[LABEL_G_REF] = bool(rep and not g_bind)
    if rep and not cand:
        op = "그대로 · «시장 타이밍은 재현됐으나 성장 코어에서의 비용(α 포기 · 반등)이 크다» → 지수 레버판을 새 등록으로 검토"
    elif m_ok and not i_ok:
        op = "그대로 · «미국 오염 창에서만 선다»"
    elif not m_ok:
        op = OP_M_FAIL
    else:
        op = ("경로 B: 결과 문서 다음 월말에 a_op %.1f 로 EG30 슬리브에 붙인다 · 보험료 한도는 운용 조건형 멈춤(뒤 24개월 %.2f%%p NAV 이고 그 창에 "
              "완료 급락 다리 없음 · 또는 붙인 뒤 누적 %.2f%%p NAV → 다음 월말 a = 0 · 다시 붙이려면 새 등록) · 원장 · 예정 판정일 없음 · 공개 «%s»") % (
            A_OP, PREMIUM_TRAIL_CAP, PREMIUM_CUM_CAP, DISCLOSE_B)
    return lab, op


def _strip(x):
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if not str(k).startswith("_")}
    if isinstance(x, (list, tuple)):
        return [_strip(v) for v in x]
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Period, pd.Timestamp)):
        return str(x)
    return x


def cache_doc(out):
    """20년 산출 전체(캐시 전용 · 표지는 x_data.write_cache_json 이 단다)."""
    return _strip(out)


def public_view(out):
    """저장소 결과 문서용 — 라벨 · 관문 불리언 · 창 · n · 2016-09 ~ 2026-08 반쪽(M · I — 평균 Δ · M 켜짐 비율) · S 요약(10년 창).
    20년 수치(20년 켜짐 비율 포함 · 사용자 20년 규칙) · G 값 · G 켜짐 비율 없음."""
    M, I, G, S = out.get("M"), out.get("I"), out.get("G"), out.get("S")
    pv = {"labels": out.get("labels"), "operating": out.get("operating"), "a_op": A_OP, "path": PATH, "forward": FORWARD_CANCELLED}
    if out.get("multiplicity"):
        pv["multiplicity"] = {k: out["multiplicity"][k] for k in ("counts", "total", "cumulative_before", "cumulative_after")}
    if M:
        b = M["X-BEAR"]
        pv["M"] = {"window": b["window"], "n": b["n"], "gates": b["gates"], "pass_all": b["pass_all"],
                   "half2": {"window": [XD.PUBLIC_FROM, XD.SCORE_LAST], "mean_delta": b["half2_mean"], "on_share": b.get("half2_on_share"), "n": 120},
                   "jackknife": {"n_e": b["jackknife"]["n_e"], "n_ok": b["jackknife"]["n_ok"]},
                   "measurement_by_reject": {k: v.get("by_reject_q10") for k, v in M.get("measurement", {}).items()}}
    if I:
        pv["I"] = {"window": I["window"], "n_markets": I["n_markets"], "markets": I["markets"], "mode": I.get("mode"), "gates": I["gates"],
                   "pass_all": I["pass_all"], "n_markets_pos": I["n_markets_pos"], "half2": I["half2"]}
    if G:
        pv["G"] = {"window": G["window"], "gates_LG": G["LG"]["gates"], "pass_LG": G["pass_LG"], "LG_binding": G["LG_binding"]}
    if S:
        pv["S"] = {"window": S["window"], "n": S["n"], "gates": S["gates"], "pass_all": S["pass_all"], "on_share": S["on_share"],
                   "e_ann": S["e_ann"], "e_lb80": S["e_lb80"], "g_down": S["g_down"], "g_crash": S["g_crash"], "turn": S["turn"],
                   "arms_ann_ex": {k: v["ann_ex"] for k, v in S["arms"].items()}}
    pv = _strip(pv)
    bad = XD.public_safe(pv)
    if bad:
        raise SystemExit("🚨 공개 보기가 공개 안전 점검에 걸렸다: %s" % bad[:3])
    return pv


# ══════════════════════════════════════════════════════════════════════════
#  보험료 한도 — 운용 조건형 멈춤 규칙(원장 · 예정 판정일 없음 · 사용자 갱신 2026-09-27)
# ══════════════════════════════════════════════════════════════════════════
def premium_cap_kill(diff_pct, attach, completed_leg_months=()):
    """보험료 한도(경로 B 로 붙였을 때만 · 운용이 매달 감시하는 조건 — 원장도 예정된 판정 날짜도 없다).
    diff_pct = {달: (운용 펀드 @ a_op − 같은 달 V0 그림자 펀드) 월 %p NAV} · attach = 붙인 첫 보유월 · completed_leg_months = 완료된 급락 다리가 끝난 달.
    뒤 24개월 누적 ≤ −0.40 이고 그 창에 완료 급락 다리 없음 · 또는 붙인 뒤 누적 ≤ −0.60 → 그 달 말에 조건 충족 → 다음 월말 a = 0
    (측정은 계속 · 다시 붙이려면 새 등록 — 지금 등록해야 재량이 아니다). 돌려주는 것 {"kill_month": 조건 충족 달 | None, "why"}."""
    s = pd.Series(diff_pct, dtype=float).sort_index()
    s.index = pd.PeriodIndex(s.index, freq="M")
    s = s.loc[s.index >= pd.Period(attach, "M")]
    legs = {pd.Period(m, "M") for m in completed_leg_months}
    cum = 0.0
    for k, (m, v) in enumerate(s.items()):
        cum += v
        if cum <= PREMIUM_CUM_CAP + 1e-12:
            return {"kill_month": str(m), "why": "붙인 뒤 누적 %.2f%%p ≤ %.2f" % (cum, PREMIUM_CUM_CAP)}
        if k + 1 >= PREMIUM_TRAIL_M:
            w = s.iloc[k + 1 - PREMIUM_TRAIL_M:k + 1]
            if float(w.sum()) <= PREMIUM_TRAIL_CAP + 1e-12 and not any(x in legs for x in w.index):
                return {"kill_month": str(m), "why": "뒤 24개월 누적 %.2f%%p ≤ %.2f · 완료 다리 없음" % (float(w.sum()), PREMIUM_TRAIL_CAP)}
    return {"kill_month": None, "why": None}


# ══════════════════════════════════════════════════════════════════════════
#  실자료 조립(굽기 · 눈가린 연기) — 값은 메모리 · 캐시에만
# ══════════════════════════════════════════════════════════════════════════
def g_inputs(dproxy_fallback=False):
    ff = XD.ff3("m")
    last = XD.french_last_month()
    cores = {nm: XD.growth_proxy(nm) for nm in XD.GROWTH_PROXIES}
    spy = XD.spy_tr()
    dd = XD.decision_days(XD.INPUT_MIN_MONTH, XD.SCORE_LAST)
    sc = XS.month_closes(spy, dd)
    iwf = XS.month_closes(XD.etf_tr("IWF"), dd)
    cores["IWF"] = (iwf / iwf.shift(1) - 1.0)
    G = {"mkt": ff["Mkt"], "rf": ff["RF"], "cores": cores, "d": XD.d_proxy(fallback=dproxy_fallback), "spy": sc / sc.shift(1) - 1.0,
         "rf_us": XD.rf_us_monthly(), "last": last}
    XD.assert_input_floor({"mkt": ff, "d": G["d"], **{"G:" + k: v for k, v in cores.items()}})
    return G


def d_proxy_fidelity(d_path_file, min_corr=0.6, window=("2014-06", "2026-08")):
    """E13 — F0 자료 충실도: corr(D_S 월 D0 수익(x_adapter D 자식 fidelity 파일) · French ME5×β1) · 창 2014-06 ~ 2026-08.
    돌려주는 것 {n, corr_fid, pass, fallback} — 수익 계열은 돌려주지 않는다(F0 칸 · 명세 data_plan.F0_counts_only «D 대리 충실도 corr»)."""
    with io.open(d_path_file, encoding="utf-8") as f:
        P = json.load(f)
    ds = pd.Series({pd.Period(k, "M"): v for k, v in (P.get("S") or {}).items() if v is not None}, dtype=float).sort_index()
    px = XD.d_proxy(fallback=False)
    idx = _pr(*window)
    a, b = ds.reindex(idx), px.reindex(idx)
    ok = a.notna() & b.notna()
    c = float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 12 else None
    return {"window": list(window), "n": int(ok.sum()), "corr_fid": c, "pass": bool(c is not None and c >= min_corr),
            "fallback": bool(not (c is not None and c >= min_corr))}


@contextlib.contextmanager
def signal_guard():
    """신호 층 읽기 가드 — 이 안에서 EG30 산출(_qbatch · _qfwd · _eg_q5 …) · tbatch 산출을 열면 멈춘다(신호 층에 EG30 입력 없음 · 기계적 확인).
    밖의 가드 설정은 되돌린다(S 층은 얼린 V0 경로를 자식 과정에서 쓴다)."""
    saved = (XD._GUARD["read_on"], XD._GUARD["read_marks"])
    XD.install_read_guard(signal_layer=True)
    try:
        yield
    finally:
        XD._GUARD["read_on"], XD._GUARD["read_marks"] = saved


def run_all(dproxy_fallback=False, intl=True, S=None):
    """M · I · G(· S) 전부 — 20년 dict(캐시 전용). S = x_adapter.s_series 결과(dict)를 주면 S 층도.
    신호 · 시장 · 국외 · 성장 대리 계산은 signal_guard 안에서(EG30 산출 파일을 열면 멈춘다)."""
    with signal_guard():
        return _run_all(dproxy_fallback, intl, S)


def _run_all(dproxy_fallback=False, intl=True, S=None):
    t0 = time.time()
    tm = {}
    t = time.time()
    I_ = XD.signal_inputs("T1")
    F = XS.signal_frame(I_)
    tm["signals"] = round(time.time() - t, 1)
    t = time.time()
    blr = XB.blr_path(F)
    tm["blr"] = round(time.time() - t, 1)
    fb = blr["a"].first_valid_index()
    if fb is not None:
        XD.assert_first_active("X-BLR", str(fb))
    t = time.time()
    MF = MFrame.real()
    tm["mframe"] = round(time.time() - t, 1)
    t = time.time()
    spy, rf = I_["spy"][0], I_["rf"][0]
    pos, _dec = XS.comp_w_positions(spy, rf, I_["baa10y"][0], I_["vix"][0], I_["vix3m"][0], XD.trading_days(),
                                     str(MF.daily.index[0].date()), str(MF.daily.index[-1].date()))
    tm["comp_w"] = round(time.time() - t, 1)
    ff = XD.ff3("m")
    t = time.time()
    M = m_layer(F, MF, blr=blr, comp_w=pos, french=ff["Mkt-RF"])
    tm["M"] = round(time.time() - t, 1)
    I = None
    if intl:
        import x_intl as XI
        t = time.time()
        frames, meta = XI.build_panel()
        try:
            fa = XI.french_sign_agreement(frames, XI.load_french_intl())
        except Exception as e:                                            # noqa: BLE001 — 충실도 보고만(없으면 사유)
            fa = {"err": type(e).__name__}
        I = i_layer(XI.primary_view(frames, meta), meta, views_usd=XI.view({cc: frames[cc] for cc in meta["markets"]}, "usd"), french_agree=fa)
        tm["I"] = round(time.time() - t, 1)
    t = time.time()
    G = g_layer(F["X-BEAR"], g_inputs(dproxy_fallback), MF.down, MF.crash, MF.surge,
                fg_arms={"X-GVTREND": F["X-GVTREND"], "X-RRSHOCK": F["X-RRSHOCK"]}, dproxy_downgraded=dproxy_fallback,
                episodes=MF.episodes, m_lookahead=M["X-BEAR"]["reports"]["d0_row"]["d0_minus_t1"])
    tm["G"] = round(time.time() - t, 1)
    s_a_same = None
    if S is not None:                                                     # S 층 a(x_adapter.bear_a_s_window) = M 층 X-BEAR 결정(2016-08 ~ 2026-07) — 기계적 단언(검토 반영)
        dec_s = [str(pd.Period(h, "M") - 1) for h in S["hold"]]
        m_a = [float(F["X-BEAR"].get(pd.Period(m, "M"), np.nan)) for m in dec_s]
        s_au = [float(x) for x in S["a_unit"]]
        if len(s_au) != len(m_a) or any(not (x == y) for x, y in zip(s_au, m_a)):
            raise SystemExit("🚨 S 층 a 가 M 층 X-BEAR 결정과 다르다 — S 층을 쓰지 않는다")
        s_a_same = True
    Sres = s_layer(S) if S is not None else None
    if Sres is not None:
        Sres["a_equals_M_layer"] = s_a_same
    lab, op = labels(M, I, G, Sres)
    out = {"M": M, "I": I, "G": G, "S": Sres, "labels": lab, "operating": op, "timings": tm, "sec": round(time.time() - t0, 1),
           "arm_status": XS.ARM_STATUS, "forward": FORWARD_CANCELLED, "n_episodes_label": len(MF.episodes),
           "windows": {"scored": [XD.SCORE_FIRST, XD.SCORE_LAST], "input_min": XD.INPUT_MIN, "S": list(XD.S_WIN)},
           "constants": {"crit": CRIT, "kappa": [KAPPA10, KAPPA20], "sigma_pre": SIGMA_PRE, "a_op": A_OP, "path": PATH,
                         "premium": [PREMIUM_TRAIL_M, PREMIUM_TRAIL_CAP, PREMIUM_CUM_CAP]}}
    out["multiplicity"] = arm_count(out)
    return out


CUM_N_BEFORE = 945                                              # 명세 multiplicity.cumulative_N_before(VBATCH-RESULT 9행)


def arm_count(out):
    """명세 multiplicity — 이 배치에서 실제로 잰 팔 수(러너가 결과 문서 머리에 적는다) · 누적 N = 945 + 이 수. 값 없음(개수만)."""
    M, I, G, S = out.get("M") or {}, out.get("I"), out.get("G") or {}, out.get("S")
    meas = [k for k, v in (M.get("measurement") or {}).items() if v.get("status") != "dropped"]
    ctrl = list((M.get("twins") or {}).keys())
    if "nagel_twin" in ((M.get("measurement") or {}).get("X-BLR") or {}):
        ctrl.append("T-NAGEL")
    if ((M.get("X-BEAR") or {}).get("reports") or {}).get("placebo_stratified") is not None:
        ctrl.append("P-STRAT")
    g_cores = [k for k in ("LG", "EXG", "MOM", "QG", "IWF") if k in G]
    fg = list((G.get("F_G") or {}).keys())
    s_arms = [k for k in ("X", "STATIC", "DIL", "IDX", "CASH") if S and k in (S.get("arms") or {})]
    n = {"M_primary": 1 if M else 0, "M_measurement": len(meas), "M_controls": len(ctrl), "I": 1 if I else 0, "G_cores": len(g_cores), "G_FG": len(fg),
         "S_arms": len(s_arms)}
    tot = sum(n.values())
    return {"counts": n, "names": {"M_measurement": meas, "M_controls": ctrl, "G_cores": g_cores, "G_FG": fg, "S_arms": s_arms},
            "total": tot, "cumulative_before": CUM_N_BEFORE, "cumulative_after": CUM_N_BEFORE + tot,
            "note": "X-VTS 는 단독 팔에서 뺐다(lit_open) · X-RRSHOCK 는 쌍둥이로 G_FG 칸에 센다(보고만) · ½ 판 · 20bp · D0 행은 같은 팔의 판이라 세지 않는다"}


def _keys_only(x, d=0, maxd=5):
    """E14 — 키 구조만(값 · 형 · None 여부 · 목록 길이 없음)."""
    if isinstance(x, dict):
        if d >= maxd:
            return "{…}"
        return {str(k): _keys_only(v, d + 1, maxd) for k, v in x.items() if not str(k).startswith("_")}
    return "·"


def _scrub_err(tb):
    """오류 꼬리에서 숫자 값을 지운다(부호 · 크기가 새지 않게) — «File …» 줄(파일 · 줄 번호)은 남긴다."""
    import re as _re
    out = []
    for line in tb.splitlines():
        if line.strip().startswith("File "):
            out.append(line)
        else:
            out.append(_re.sub(r"(?<![A-Za-z_])[-+]?\d+\.\d+(e[-+]?\d+)?", "<num>", line))
    return "\n".join(out)


def blind_smoke(with_s=False, intl=True):
    """실자료 눈가린 연기 — run_all 을 끝까지 · 산출은 캐시 임시 파일로 썼다가 열지 않고 지운다.
    보고는 키 구조(3단) · 구조 개수(창 달 수 · 관문 이름 · 팔 이름 · 시장 · 코어 이름 · 에피소드 수(라벨)) · 시간만(E14 — 값 · 형 · None 여부 없음)."""
    XD.install_read_guard(signal_layer=False)
    XD.install_write_guard(XD.ROOT)
    t0 = time.time()
    rep = {"started": XD._now(), "ok": False}
    buf = io.StringIO()
    try:
        S = None
        with contextlib.redirect_stdout(buf):
            if with_s:
                import x_adapter as XA
                S = XA.s_series_cached()
            out = run_all(intl=intl, S=S)
            doc = cache_doc(out)
            p = XD.write_cache_json("_xb_blind_smoke.tmp.json", doc)
            pv = public_view(out)
            pv_safe = not XD.public_safe(pv)
        rep["out_written"] = os.path.exists(p)
        os.remove(p)                                                     # 열지 않고 지운다
        rep["deleted_unread"] = not os.path.exists(p)
        rep["public_view_safe"] = pv_safe
        rep["keys"] = _keys_only({k: v for k, v in out.items() if k not in ("timings",)}, maxd=3)
        rep["timings"] = out["timings"]
        rep["counts"] = {"M_window_months": len(HOLD), "M_gate_ids": sorted(out["M"]["X-BEAR"]["gates"]),
                         "measurement_arms": sorted(out["M"]["measurement"]), "by_family": list(out["M"]["by_family"]),
                         "I_markets": (out["I"] or {}).get("markets"), "I_mode": (out["I"] or {}).get("mode"),
                         "G_cores": [k for k in out["G"] if k in ("LG", "EXG", "MOM", "QG", "IWF")], "G_window": out["G"]["window"],
                         "F_G_arms": sorted(out["G"]["F_G"]), "label_keys": sorted(out["labels"]), "episodes_n_label": out["n_episodes_label"],
                         "S_present": out["S"] is not None, "S_gate_ids": (sorted(out["S"]["gates"]) if out["S"] else None),
                         "multiplicity": out["multiplicity"]}
        del out, doc, pv, S
        if with_s:
            XA.cleanup_smoke()                                           # D 책 수익 경로 · S 작업 파일(a 상태)도 열지 않고 지운다
            rep["s_intermediates_deleted_unread"] = not any(os.path.exists(os.path.join(XA.s_dir(), f)) for f in XA.SMOKE_INTERMEDIATES)
        rep["ok"] = True
    except BaseException:                                                # noqa: BLE001
        rep["err"] = _scrub_err(traceback.format_exc()[-3000:])
    finally:
        XD.guard_off()
    rep["sec"] = round(time.time() - t0, 1)
    rep["stdout_discarded_unread"] = True                                     # 길이도 싣지 않는다(값에 따라 달라질 수 있는 셈 · 검토 반영)
    p = os.path.join(XD.cache_guard(), "meta", "_smoke_x_eval.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rep, ensure_ascii=False, indent=1, default=str) + "\n")
    return rep


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험(망 · 캐시 · 실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _syn_mframe(seed=3, mu_bear=-0.03):
    """합성 시장 — 2005-08 ~ 2026-09 거래일 · 난류 국면(월 −3%)이 BEAR 로 잡히는 세계."""
    rng = np.random.default_rng(seed)
    days = XD._syn_days("2005-08-01", "2026-09-10")
    XD.set_calendar(days)
    months = pd.period_range("2005-08", "2026-09", freq="M")
    reg = np.zeros(len(months), int)
    for a, n in ((25, 17), (90, 6), (140, 9), (170, 4), (200, 8)):
        reg[a:a + n] = 1
    mu_m = np.where(reg == 1, mu_bear, 0.011)
    sd_m = np.where(reg == 1, 0.06, 0.03)
    rows = []
    for k, m in enumerate(months):
        dm = days[days.to_period("M") == m]
        r = rng.normal(mu_m[k] / len(dm), sd_m[k] / math.sqrt(len(dm)), len(dm))
        rows.append(pd.Series(r, index=dm))
    r = pd.concat(rows)
    spy = 100 * np.exp(np.cumsum(r))
    gspc = spy * 0.98
    rf = pd.Series(0.002, index=pd.period_range("2005-09", "2026-09", freq="M"))
    dd = XD.decision_days("2005-08", "2026-08")
    zz = ([d.strftime("%Y-%m-%d") for d in gspc.index], [float(x) for x in gspc.to_numpy()])
    MF = MFrame.from_series(dd, spy, gspc, rf, XD.t_plus_1, zz)
    return MF, spy, rf, dd, days


def _st_constants():
    assert CRIT == {"T240_L6": 1.706, "T92_L3": 1.738, "T36_L3": 1.892, "T24_L3": 2.037}
    assert abs(KAPPA10 - 0.004) < 1e-15 and abs(KAPPA20 - 0.008) < 1e-15 and D_REF == 0.05
    assert SIGMA_PRE == 0.042903 and RG_MAX == 0.5 and I_BREADTH == 6 and NI_LB == -0.30 and Z80 == 0.8416
    assert (DIL_DOWN, DIL_CRASH) == (0.0982, 0.233) and abs(0.075 / 0.764 - DIL_DOWN) < 5e-4 and abs(0.178 / 0.764 - DIL_CRASH) < 5e-4
    assert (A_OP, PATH) == (0.5, "B") and (PREMIUM_TRAIL_M, PREMIUM_TRAIL_CAP, PREMIUM_CUM_CAP) == (24, -0.40, -0.60)
    # 고정 b 상수 — 다시 정하지 않고 작은 모의로 모양만 대조(20,000 회 · 등록값 ± 0.04)
    rng = np.random.default_rng(20260928)
    E = _frozen("eg30plus")
    for key, (T, L) in (("T240_L6", (240, 6)), ("T24_L3", (24, 3))):
        ts = np.array([E.nw_t(rng.standard_normal(T), lag=L) for _ in range(4000)], float)
        q = float(np.quantile(ts, 0.95))
        assert abs(q - CRIT[key]) < 0.08, (key, q)
    return "등록 상수(1.706 · 1.738 · 1.892 · 2.037 · κ 0.004/0.008 · σ_pre · 희석선 0.0982/0.233 · a_op ½ · 경로 B · 한도 −0.40/−0.60) · 고정 b 모양 대조(얼린 nw_t)"


def _st_delta_and_gates():
    MF, spy, rf, dd, days = _syn_mframe()
    try:
        re = XS.monthly_excess(spy, rf, dd)
        a = XS.bear_state(re).reindex(DEC)
        assert a.notna().all()
        res, d, aa = m_arm(a, MF)
        assert res["n"] == 240 and res["window"] == ["2006-09", "2026-08"]
        # Δ 정의: 손으로
        R = MF.Re_t1
        ah = pd.Series(a.to_numpy(), index=HOLD)
        ab = float(ah.mean())
        hand = -(ah - ab) * R - KAPPA10 * (ah - ah.shift(1).fillna(0.0)).abs()
        assert np.allclose(hand.to_numpy(), d.to_numpy(), atol=1e-15)
        # a ≡ 0 → Δ ≡ 0 · 비용 0
        z, _, _ = delta_series(pd.Series(0.0, index=DEC), MF.Re_t1)
        assert float(np.abs(z).max()) == 0.0
        # 상수 a → Δ = 비용만(첫 달) — 정적 쌍둥이와 같으면 타이밍 0
        c, ab2, _ = delta_series(pd.Series(0.3, index=DEC), MF.Re_t1)
        assert abs(float(c.iloc[0]) + 0.3 * KAPPA10) < 1e-15 and float(np.abs(c.iloc[1:]).max()) < 1e-15
        # 관문 모양 · 통계가 모두 섰다
        assert set(res["gates"]) == {"M-C1", "M-C2", "M-C3", "M-C4", "M-C5", "M-C6"} and res["nw_t"] is not None
        assert res["jackknife"]["n_e"] == len(MF.episodes) and res["n_ool"] == 92
        # 선견 판정자: 완벽 예지(다음 달 음이면 1)는 합성 세계에서 M-C1 · M-C2 를 넘는다
        per = pd.Series((MF.Re_t1 < 0).astype(float).to_numpy(), index=DEC)
        r2, _, _ = m_arm(per, MF, full=False)
        assert r2["gates"]["M-C1"] and r2["gates"]["M-C2"] and r2["gates"]["M-C6"]
        # RG: 완벽 예지는 반등에 꺼져 있다 → RG 작다
        assert r2["rg_abs"] is None or r2["rg_abs"] < 0.5
    finally:
        XD.set_calendar(None)
    return "Δ = −(a − ā)R^e − κ|Δa| 손 계산 일치 · a ≡ 0 → 0 · 상수 a → 비용만 · M-C1~C6 모양 · 2019-01~2026-08 = 92 · 완벽 예지 통과"


def _st_rg_episodes():
    days = pd.bdate_range("2006-08-01", "2006-12-31")
    D = [d.strftime("%Y-%m-%d") for d in days]
    legs = [("crash", D[5], D[20], -0.2, D[25]), ("rally", D[20], D[40], 0.2, D[45]), ("crash", D[40], D[60], -0.15, D[62])]
    rebs = [{"a": D[20], "b": D[40], "td": 20, "move": 0.1}, {"a": D[60], "b": D[80], "td": 20, "move": 0.1}]
    eps = episodes_from_legs(legs, rebs, D)
    assert len(eps) == 1 and len(eps[0]["legs"]) == 2                  # 저점(20) ~ 다음 고점(40) = 20 ≤ 126 → 한 에피소드
    legs2 = [("crash", D[5], D[20], -0.2, D[25])]
    days2 = pd.bdate_range("2006-08-01", "2007-12-31")
    D2 = [d.strftime("%Y-%m-%d") for d in days2]
    legs2 = [("crash", D2[5], D2[20], -0.2, D2[25]), ("crash", D2[200], D2[220], -0.2, D2[225])]
    rebs2 = [{"a": D2[20], "b": D2[40], "td": 20, "move": 0.1}, {"a": D2[220], "b": D2[240], "td": 20, "move": 0.1}]
    assert len(episodes_from_legs(legs2, rebs2, D2)) == 2               # 180 > 126 → 둘
    # RG 손 계산: 다리 날 a=1 · 시장 −1%/일 · 반등 날 a=1 · +1%/일 → 이득 15 · 비용 20 → RG = 20/15
    idx = days2[1:300]
    u = pd.Series([p for p in idx.to_period("M")], index=idx)
    re = pd.Series(0.0, index=idx)
    re[(idx > days2[5]) & (idx <= days2[20])] = -0.01
    re[(idx > days2[20]) & (idx <= days2[40])] = 0.01

    class _F:
        pass
    F = _F()
    F.daily = pd.DataFrame({"u": u, "re_d": re})
    F.crash_legs = [(D2[5], D2[20])]
    F.rebs = [{"a": D2[20], "b": D2[40]}]
    aa = pd.Series(1.0, index=pd.period_range("2006-08", "2008-01", freq="M"))
    rg, den, num = rg_abs(aa, F)
    assert abs(den - 0.15) < 1e-12 and abs(num - 0.20) < 1e-12 and abs(rg - 0.2 / 0.15) < 1e-12
    aa0 = aa * 0.0
    assert rg_abs(aa0, F)[0] is None                                     # 분모 0 → 거짓
    return "에피소드 병합(≤ 126 거래일 한 에피소드 · 180 이면 둘) · RG 손 계산(20/15) · 분모 ≤ 0 → None(거짓)"


def _st_jackknife_placebo():
    MF, spy, rf, dd, days = _syn_mframe(seed=5)
    try:
        re = XS.monthly_excess(spy, rf, dd)
        a = XS.bear_state(re).reindex(DEC)
        d, _, _ = delta_series(a, MF.Re_t1)
        jk = jackknife(d, MF)
        assert jk["n_e"] == len(MF.episodes) and jk["need"] == max(0, jk["n_e"] - 1) and len(jk["means"]) == jk["n_e"]
        vol = XS.vol63(spy, dd.reindex(DEC))
        pl = stratified_placebo(a, MF.Re_t1, vol, n=200)
        assert pl is not None and 0.0 <= pl["rank"] <= 1.0 and pl["n_blocks"] == 20
        pl2 = stratified_placebo(a, MF.Re_t1, vol, n=200)
        assert pl2["rank"] == pl["rank"]                                  # 씨앗 고정 · 재현
        # 위약은 켜짐 몫(ā)을 지킨다 — 토막 섞기
        assert concentration(pd.Series([3.0, 1.0, -1.0, 1.0])) == 1 and concentration(pd.Series([-1.0, -2.0])) is None
    finally:
        XD.set_calendar(None)
    return "잭나이프(n_e · 필요 n_e − 1) · 층화 위약(20 토막 · 3분위 · 씨앗 재현) · 집중도"


def _st_dilution():
    rng = np.random.default_rng(12)
    n = 240
    hold = HOLD
    mkt = pd.Series(rng.normal(0.008, 0.045, n), index=hold)
    core = 1.2 * mkt + rng.normal(0.003, 0.02, n)
    dpx = 0.7 * mkt + rng.normal(0.0, 0.015, n)
    rf = pd.Series(0.001, index=hold)
    a = pd.Series((rng.random(n) < 0.2).astype(float), index=hold - 1)
    down, crash, surge = mkt < 0, mkt <= -0.0429, mkt >= 0.0429
    r1 = g_core(a, core, dpx, mkt, rf, down, crash, surge, app_on=False, hold=hold)
    # c 해법: 희석 펀드의 연 초과 = X 펀드의 연 초과
    V, X, Mk = r1["_series"]["V"], r1["_series"]["X"], r1["_series"]["mkt"]
    c = r1["dilution_c"]
    Dil = V + 0.1 * (c - 1.0) * (pd.Series(core).reindex(V.index) - Mk)
    if 0 < c < 1:
        assert abs(float((Dil - Mk).mean()) - float((X - Mk).mean())) < 1e-12
    assert dilution_c(0.1, 0.5) == 1.0 and dilution_c(-0.1, -0.5) == 1.0 and abs(dilution_c(-0.1, 0.5) - 0.8) < 1e-15 and dilution_c(-9, 0.5) == 0.0
    # 희석선 관문은 a 크기에 무관(½ 판도 같은 판정) — 비용까지 a 에 선형이므로
    r_half = g_core(a * 0.5, core, dpx, mkt, rf, down, crash, surge, app_on=False, hold=hold)
    if 0 < c < 1:
        assert r_half["gates"]["G-C1"] == r1["gates"]["G-C1"] and r_half["gates"]["G-C2"] == r1["gates"]["G-C2"]
        assert abs(r_half["dilution_c"] - 1.0 - 0.5 * (c - 1.0)) < 1e-12
    # S-C4 식도 a 에 무관: e · g_d · g_c 가 모두 a 에 비례
    for lam in (0.5, 0.25):
        e, gd, gc = -0.2, 0.03, 0.05
        a1 = gd >= max(0, -DIL_DOWN * e) and gc > max(0, -DIL_CRASH * e)
        a2 = lam * gd >= max(0, -DIL_DOWN * lam * e) and lam * gc > max(0, -DIL_CRASH * lam * e)
        assert a1 == a2
    return "희석 c 해법(같은 연 초과 · 1e−12) · 자름 규칙 · G-C1 · G-C2 · S-C4 가 a 크기에 무관(½ 판 같은 판정)"


def _st_g_app():
    rng = np.random.default_rng(21)
    hold = _pr("2005-08", "2026-08")
    mkt = pd.Series(rng.normal(0.008, 0.045, len(hold)), index=hold)
    rf = pd.Series(0.001, index=hold)
    core = 1.25 * (mkt - rf) + rf + rng.normal(0, 0.01, len(hold))
    dpx = 0.70 * (mkt - rf) + rf + rng.normal(0, 0.01, len(hold))
    b = rolling_beta(core, mkt, rf, hold)
    assert b.loc[:"2006-06"].isna().all() and b.loc["2006-07":].notna().all()     # 12개월(2005-08 ~ 2006-07)부터
    assert abs(float(b.iloc[-1]) - 1.25) < 0.1
    a = pd.Series(1.0, index=HOLD - 1)
    r = g_core(a, core, dpx, mkt, rf, mkt < 0, mkt <= -0.0429, mkt >= 0.0429, hold=HOLD)
    assert r["app_off_months"] == 0
    r2 = g_core(a, dpx, dpx, mkt, rf, mkt < 0, mkt <= -0.0429, mkt >= 0.0429, hold=HOLD)   # 끌 베타 없음 → APP 0
    assert r2["app_off_months"] == 240 and r2["on_share"] == 0.0
    return "APP(창 안 확장 월간 β · 최소 12 · 최대 36 · 2005-08~) · β 차 ≥ 0.10 이면 켜짐 · 끌 베타 없음 → a = 0"


def _st_i_layer():
    rng = np.random.default_rng(31)
    months = _pr("2005-09", "2026-08")
    views = {}
    for k, cc in enumerate(("JP", "NL", "DE", "FR", "IT", "CH", "SE", "CA", "AU", "KR")):
        rs = pd.Series(rng.normal(0.004, 0.05, len(months)), index=months)
        rh = pd.Series(np.nan, index=months)
        rh.loc[HOLD] = rs.shift(-1).reindex(HOLD - 1).to_numpy() * 0 + rng.normal(0.004, 0.05, 240)
        views[cc] = pd.DataFrame({"re_sig": rs, "re_hold": rh, "tr": rs + 0.001, "down": (rs < 0)})
    I = i_layer(views, {"mode": "local"}, views_usd=views, french_agree={"JP": {"n": 3, "n_agree": 2}})
    assert I["reports"]["usd_version"]["dk_t"] == I["dk_t"] and I["reports"]["french_sign_agreement"]["JP"]["n"] == 3
    assert "usd_version" not in i_layer(views, {"mode": "usd"}, views_usd=views)["reports"]          # 주 판이 USD 면 USD 보고는 겹친다
    assert I["n_markets"] == 10 and set(I["gates"]) == {"I-C1", "I-C2", "I-C3", "I-C4"} and I["dk_t"] is not None
    pooled = I["_series"]["pooled"]
    hand = pd.DataFrame({cc: delta_series(XS.bear_state(v["re_sig"]).reindex(DEC), v["re_hold"], kappa=0.0)[0] for cc, v in views.items()}).mean(axis=1)
    assert np.allclose(pooled.to_numpy(), hand.reindex(HOLD).to_numpy())
    assert abs(I["dk_t"] - nw_t(hand.to_numpy())) < 1e-12
    # FX 역수 방향(명세 selftest) — x_intl 합성 시험을 엔진 묶음에서도 부른다
    import x_intl as XI
    XI._st_fx_direction()
    return "I 층 풀링 = 시장 등가중 · DK t = 풀링 NW(6) t · I-C1~C4 모양 · FX 역수 방향(x_intl 합성 시험)"


def _st_s_layer():
    hold = _pr("2016-09", "2026-08")
    rng = np.random.default_rng(41)
    ix = rng.normal(1.0, 4.0, 120)
    a = (rng.random(120) < 0.2).astype(float)
    Rm = ix - 0.1
    v0 = rng.normal(0.06, 0.4, 120)
    e = 0.1 * a * (-(1.215 - 0.7) * Rm) - 0.02 * a
    S = {"hold": [str(h) for h in hold], "a": a, "Re_m": Rm, "down": ix < 0, "crash": ix <= -4.29, "d_ok": [True] * 120, "turn": 2.0,
         "arms": {"V0": v0, "X": v0 + e, "X_half": v0 + 0.5 * e, "STATIC": v0, "DIL": v0, "IDX": v0, "CASH": v0},
         "sleeve": {"V0": 1.215 * ix + rng.normal(0, 1, 120), "D": 0.7 * ix + rng.normal(0, 1, 120)}, "index": ix,
         "beta_C": [1.215] * 120, "beta_D": [0.7] * 120}
    S["arms"].update({"X20": v0 + e - 0.001 * a, "V0_20": v0})
    S["arms_d0"] = {"X": v0 + e + 0.01 * a, "V0": v0}
    r = s_layer(S)
    assert set(r["gates"]) == {"S-C1", "S-C2", "S-C3", "S-C4"} and r["gates"]["S-C1"] and r["gates"]["S-C2"]
    assert r["d0_row"]["e_ann"] is not None and r["cost20"]["e_ann"] is not None and abs(r["identity"]["resid_mean_on"] + 0.02) < 1e-9
    assert abs(r["half_a_op"]["e_ann"] - 0.5 * r["e_ann"]) < 1e-12 and r["half_a_op"]["lb80_operating_need"] == -0.15
    S2 = dict(S, d_ok=[True] * 119 + [False])
    assert not s_layer(S2)["gates"]["S-C1"]
    S3 = dict(S, turn=10.5)
    assert not s_layer(S3)["gates"]["S-C1"]
    return "S 층 관문 모양 · S-C1(120개월 D 목표 · 회전 ≤ 10) · S-C2(기울기 · β(D) < β(C))"


def _st_premium_rule():
    ms = [str(p) for p in _pr("2027-01", "2029-12")]
    # 붙인 뒤 누적 −0.60 에서 죽임
    d = {m: -0.03 for m in ms}
    k = premium_cap_kill(d, "2027-01")
    assert k["kill_month"] == ms[19], k                                   # 20 × −0.03 = −0.60
    # 뒤 24개월 −0.40 · 완료 다리 없음이면 죽임 · 다리가 있으면 그 규칙은 안 걸리고 누적 규칙까지 간다
    d2 = {m: (-0.40 / 24 - 1e-9) for m in ms}
    k2 = premium_cap_kill(d2, "2027-01")
    assert k2["kill_month"] == ms[23], k2
    k3 = premium_cap_kill(d2, "2027-01", completed_leg_months=[ms[10]])
    assert k3["kill_month"] is None or k3["kill_month"] > ms[23]
    assert premium_cap_kill({m: 0.01 for m in ms}, "2027-01")["kill_month"] is None
    # 전방 판정 취소(사용자 갱신 2026-09-27) — FF1 · FF2 · XFWD 함수가 이 모듈에 없다 · 운용 문구에도 없다
    for nm in ("ff1", "ff2", "FF1_MONTHS", "FF2_MONTHS"):
        assert not hasattr(sys.modules[__name__], nm), nm
    _lab, op = labels({"X-BEAR": {"pass_all": True, "nw_t": 2.0}}, {"pass_all": True}, {"pass_LG": True, "LG_binding": True}, {"pass_all": True})
    assert "FF1" not in op and "XFWD" not in op and "원장 · 예정 판정일 없음" in op and "조건형 멈춤" in op
    return "보험료 한도(조건형 멈춤 · 누적 −0.60 · 뒤 24개월 −0.40 · 완료 다리 예외) · FF1 · FF2 · XFWD 없음(사용자 갱신 2026-09-27) · 운용 문구에 원장 없음"


def _st_labels_public():
    M = {"X-BEAR": {"pass_all": True, "nw_t": 3.2, "window": ["2006-09", "2026-08"], "n": 240, "gates": {"M-C1": True}, "half2_mean": 0.001,
                    "jackknife": {"n_e": 10, "n_ok": 9}, "reports": {"turnover": {"on_share": 0.14}}}, "measurement": {}}
    I = {"pass_all": True, "window": ["2006-09", "2026-08"], "n_markets": 10, "markets": ["JP"], "gates": {"I-C1": True}, "n_markets_pos": 7,
         "half2": {"window": ["2016-09", "2026-08"], "pooled_mean": 0.0004, "n": 120}, "mode": "local"}
    G = {"pass_LG": False, "LG_binding": True, "window": ["2006-09", "2026-08"], "LG": {"gates": {"G-C1": False}, "on_share": 0.13}}
    S = None
    lab, op = labels(M, I, G, S)
    assert lab["방어 재현"] and not lab["보험 채택 후보"] and lab["랩 발견(맥락)"] and "지수 레버판" in op
    G2 = dict(G, LG_binding=False)
    S2 = {"pass_all": True}
    lab2, op2 = labels(M, I, G2, S2)
    assert lab2["보험 채택 후보"] and lab2.get(LABEL_G_REF) and "경로 B" in op2 and DISCLOSE_B in op2
    assert LABEL_G_REF in lab and lab[LABEL_G_REF] is False and set(lab) == set(lab2)          # 키 집합은 결과와 무관(E14)
    lab3, _ = labels(dict(M, **{"X-BEAR": dict(M["X-BEAR"], pass_all=False)}), I, G, S2)
    assert not lab3["M 일관성 통과(오염 창)"] and not lab3["보험 채택 후보"]
    lab4, op4 = labels(dict(M, **{"X-BEAR": dict(M["X-BEAR"], pass_all=False)}), dict(I, pass_all=False), G, S2)
    assert op4 == OP_M_FAIL and "희석" not in op4 and set(lab4) == set(lab)                      # M 실패 = 그대로(EG30 V0) · 희석 메뉴 없음
    M["X-BEAR"]["half2_on_share"] = 0.1
    pv = public_view({"M": M, "I": I, "G": G, "S": None, "labels": lab, "operating": op})
    assert not XD.public_safe(pv)
    assert "on_share" not in pv["M"] and pv["M"]["half2"]["on_share"] == 0.1 and "on_share_LG" not in pv["G"]   # 20년 켜짐 비율 · G 켜짐 비율은 공개 보기에 없다
    # E14 — 연기 보고의 키 구조는 값 · 형 · None 여부를 싣지 않는다 · 오류 꼬리의 숫자는 지운다
    assert _keys_only({"a": None, "b": 1.5, "c": [1, 2], "d": {"e": None}, "_s": 1}) == {"a": "·", "b": "·", "c": "·", "d": {"e": "·"}}
    assert "0.0123" not in _scrub_err('  File "x.py", line 3, in f' + chr(10) + 'AssertionError: mean 0.0123 < -1.5e-03')
    # 20년 창 안 실수 값은 공개 보기에 없다 — 있으면 가드가 막는다
    bad = {"M": {"window": ["2006-09", "2026-08"], "mean_delta": 0.0012}}
    assert XD.public_safe(bad)
    with tempfile.TemporaryDirectory() as td:
        try:
            XD.repo_write_json("data/_xb_f0.json", XD.mark_cache_only({"a": 1}), root=td)
            raise AssertionError("20년 표지 통과")
        except PermissionError:
            pass
        try:
            XD.repo_write_json("data/_xbatch.json", {"a": 1}, root=td)
            raise AssertionError("허용 밖 경로 통과")
        except PermissionError:
            pass
    return "라벨(방어 재현 · 보험 채택 후보 · 랩 발견 · G 참고) · 운용 문구(경로 B · 공개 문구) · 공개 보기 안전 · 20년 수치 가드"


def _st_d_fidelity():
    """E13 — D 대리 충실도(합성): corr ≥ 0.6 이면 그대로 · 아니면 Lo 20 으로 바꾸고 G «참고» · 창 2014-06 ~ 2026-08 · 값 계열을 돌려주지 않는다."""
    rng = np.random.default_rng(13)
    idx = _pr("2014-06", "2026-08")
    base = pd.Series(rng.normal(0.008, 0.035, len(idx)), index=idx)
    old = XD.d_proxy
    try:
        with tempfile.TemporaryDirectory() as td:
            for noise, want in ((0.005, True), (0.2, False)):
                ds = base + rng.normal(0, noise, len(idx))
                p = os.path.join(td, "d.json")
                with io.open(p, "w", encoding="utf-8") as f:
                    json.dump({"S": {str(k): float(v) for k, v in ds.items()}}, f)
                XD.d_proxy = lambda fallback=False, start=None, end=None: base
                r = d_proxy_fidelity(p)
                assert r["pass"] is want and r["fallback"] is (not want) and r["n"] == len(idx) and r["window"] == ["2014-06", "2026-08"]
                assert not XD.value_lists(r)
    finally:
        XD.d_proxy = old
    return "D 대리 충실도(E13): corr ≥ 0.6 통과 · 아니면 Lo 20 · G 참고 · 창 2014-06 ~ 2026-08(147) · 값 계열 없음"


def _st_window_assert():
    try:
        XD.assert_scored_months(["2006-08"] + [str(p) for p in HOLD[:5]])
        raise AssertionError("창 앞 보유월 통과")
    except AssertionError as e:
        if "통과" in str(e):
            raise
    assert str(HOLD[0]) == "2006-09" and str(HOLD[-1]) == "2026-08" and len(HOLD) == 240 and str(DEC[0]) == "2006-08"
    try:
        s_layer({"hold": [str(p) for p in _pr("2016-08", "2026-08")]})
        raise AssertionError("S 창 앞 보유월 통과")
    except AssertionError as e:
        if "통과" in str(e):
            raise
    except (KeyError, TypeError):
        raise AssertionError("S 창 단언이 먼저 걸려야 한다")
    return "채점 보유월 최소 2006-09 · 240 · 결정 2006-08 ~ · S 층 2016-09 ~ 2026-08(120) 단언"


SELFTESTS = (_st_constants, _st_delta_and_gates, _st_rg_episodes, _st_jackknife_placebo, _st_dilution, _st_g_app, _st_i_layer, _st_s_layer,
             _st_premium_rule, _st_labels_public, _st_d_fidelity, _st_window_assert)


def selftest():
    res, ok = [], True
    for fn in SELFTESTS:
        t = time.time()
        try:
            res.append(("통과", fn.__name__, fn(), time.time() - t))
        except Exception:                                             # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-2500:], time.time() - t))
    for st, nm, msg, dt in res:
        print("  %s %-24s %5.2fs  %s" % ("✓" if st == "통과" else "✗", nm, dt, msg))
    print("x_eval selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--blind-smoke" in argv:
        rep = blind_smoke(with_s="--with-s" in argv, intl="--no-intl" not in argv)
        print(json.dumps({k: rep[k] for k in ("ok", "sec", "deleted_unread", "public_view_safe", "counts", "timings", "err") if k in rep},
                         ensure_ascii=False, indent=1, default=str))
        return 0 if rep.get("ok") else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
