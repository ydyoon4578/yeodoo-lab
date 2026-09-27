# -*- coding: utf-8 -*-
"""build/w_cards.py — 배치 W 등록 A 카드 목록 · 공통 슬리브 책 · W06 MOM-CR · W12 FOMC-SML · W10m TAILX · 눈가린 연기.

설계 원본(구속): wbatch_research.json final.slate(common_frame · strategies W01 W04 W03 W06 W12 W10m · steps) · evaluation · registration ·
  build_plan.modules(w_book · w_mom6 · w_fomc — 과제 지시로 이 파일에 모은다) · 사용자 갱신 2026-09-27(전방 원장 없음 · W13 뺌 · 등록 A 가족 {W01 · W04 · W10m} ·
  W03 · W06 · W12 측정만 · 스텝은 W01 위 Δ) · 사용자 규칙(최근 20년 · G-NoEG · 주식 중심 · 카드마다 근본 이유).

카드(등록 A) — 근본 이유 한 줄(자세한 규칙은 각 모듈 머리말)
  W01 IPCA-KPS8(w_ipca) — 특성은 소수 요인에 대한 시변 노출의 대리 · 기대수익을 공분산에 묶는 구조 제약(Γ_α = 0) · 가족 A.
  W04 CIQ-LT(w_ciq)    — 중개자 손상 → 하방 꼬리가 함께 두꺼워짐 → 공통 하방 꼬리 노출 종목의 이후 기대수익이 높다 · 가족 A.
  W10m TAILX(여기)     — 변동성은 국면만 알려 주고 어느 종목의 분포가 비대칭으로 망가지는지는 꼬리 모양이 알려 준다 · 꼬리 모양이 크게 갈라질 때 나쁜 꼬리
                          종목의 폭락 위험이 이어진다 · FM 한 줄(책 없음) · 가족 A.
  W03 PAP(w_pap)       — 연결 산업 사이 한쪽 방향의 느린 정보 확산 = 예측 행렬의 반대칭부 · 측정만(섹터 띠 ±0.15 이탈 · 채택 경로 없음).
  W06 MOM-CR(여기)     — 급변동 직후 12개월 승자 명단은 급락 전 베타와 테마를 품은 낡은 명단 · 6개월 순위로 빨리 갈아타면 낡은 노출이 준다(MSCI 2026-08 부록 III) ·
                          측정만(사건 연구).
  W12 FOMC-SML(여기)   — 위험 보상은 거시 불확실성이 풀리는 발표일에 몰린다(Savor–Wilson 2014) · 저베타 틸트(V02)의 비용이 발표일에 몰리니 그날만 중립 · 측정만.
  스텝 S3e · S2 · S1(w_steps) — W01 C 책 위 Δ 로만.
  뺀 카드: W13(사용자 갱신 가 — 전방 전용) · W05 · W07(U1 보류 — PyTorch 설치 안 함) · W08 · W09(w_core.DROPPED).

공통 슬리브(명세 common_frame.book · buffer_fill · costs · turnover)
  최종 책 = w_B + θ_t·(w_f − w_B) · w_f = 카드 점수 상위 q(기본 0.3) 이름의 상한 없는 시총가중 · θ ≤ 1 · 발행사 |a_i| ≤ 0.05 · 섹터 띠 |Σa| ≤ 0.10 ·
  NDX 전용 합 ≤ 0.10 · β 띠 ±0.03(frozen v_core 투영 · FP 사전 β̂) · 새 이름 q 안 · 기존 1.5q 안 유지 · 틈의 ½ 체결 · 틈 < 0.1·목표 무거래 · 삭제 전량 ·
  편도 10bp(20bp 강건) · 편도 연 회전 ≤ 10(넘으면 |Δw| 작은 거래부터 건너뛴다) · 금융주는 w_B 그대로(능동 0) · 커버리지 못 넘은 달은 흘러간다(drift).

W06 MOM-CR(측정만 · Tier-1 통계 없음)
  발동: 월말 t 에 V_t = σ(63거래일 S&P 500 일간 총수익) · Δ_t = V_t/V_{t−1} − 1 · 문턱 = t−1 까지 확장창 Δ 의 95백분위(기준 이력 1993~).
  규칙: 발동하면 결정 t · t+1 두 번 V01 선정 점수를 6개월 원수익 r_{t−6..t−1}(최근 1개월 제외 · P_{T−1}/P_{T−7} − 1)로 바꾸고 그 뒤 12-2 로 돌아간다.
  측정: 발동 뒤 21 · 42거래일 상대수익(대 V01 정기판) · 발동 창 달의 Δ X(보고). 대조: V01 정기판 · 같은 날짜에 12-2 로 다시 고른 판(«지금 갈아탄 효과» 와
  «짧은 창 효과» 를 가른다). 쌍둥이: 6개월 위험조정 모멘텀(6개월 수익 ÷ 3년 주간 σ · MSCI 그대로).
W12 FOMC-SML(측정만)
  Tier-1(보고): 일간 단면 회귀 r_{i,d} ~ β̂_i(252일 · 전일까지) + 섹터 더미 → γ_d · γ_d ~ 1[FOMC_d] 의 계수(NW 5) · H1 > 0 · 2014-06 ~ 2026-08 약 98 발표일.
  스텝 책: V02 정적 책(frozen v_cards)에서 FOMC 결정일 하루만 능동 a = 0(w_B) · 결정은 전 주 · 체결은 d−1 종가 · d 종가에 되돌림 · 10/20bp 두 번 ·
  대조: 같은 수의 무작위 비발표일에 같은 중립화(200회). 일정: 연준 공개 일정(federalreserve.gov fomccalendars · fomchistorical)의 정례 결정일(회의 마지막 날) ·
  비정례 · 전화회의 · 서면 결의 · 취소는 뺀다.
W10m TAILX(가족 A · 방향 +1)
  특성 tail_i = Q0.10(63일 일간수익)/σ(63일) · 상태 = 그 단면 IQR 의 확장창 z · 회귀 r_{i,t+1} ~ z(tail) + z(tail)·z(IQR_t) + Stage M-W 통제 ·
  교차항 γ · NW(3) · H1 > 0 · IC_lit 0.010 · σ 0.07 → P0 0.034 [합성 · 기록만] · 위험: x-kurt · x-distshape 재진입(가족 누적 N 에 더한다).

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  B1 w_f: 금융주(GICS «Financials»)는 w_B 비중 그대로 · 비금융 선정 이름은 (1 − 금융 w_B 합)을 시총 비례로 · 투영 · β 띠가 금융주를 조금 움직일 수 있다(보고).
     선정 = frozen v_cards._rank_select(내림차순 · 동점 티커 · 새 이름 round(qN) · 기존 round(1.5qN)) · N = 점수가 선 비금융 이름.
  B2 회전 예산: 월 Σ|Δw| ≤ 2 × 10/12(v_core.turnover_annual 의 ½Σ/해 식과 같은 단위) · 넘으면 |Δw| 가 작은 이름부터 흘러간 비중으로 되돌려 예산 안으로 · 합 1 로 비례.
  B3 W06 기준 책: 🚨 명세는 «V01 거미줄 책(VF01W)» 이다. V01 거미줄 θ 는 (i) 가닥 G2own:S(책의 log BE/ME − w_B 의 log BE/ME = B/M 입력) 와
     (ii) French FF3 파일(Mkt · RF — W G-NoEG 연 파일 감사의 금지 원천)로 추정한 L 층 기울기에 기댄다 → 사용자 규칙(2026-09-27 «B/M 입력 어디에도 없다») ·
     U3 엄격 해석과 부딪친다. 그래서 W06 은 V01 정적(S0 · θ0 0.75) 책 위에서 잰다(선정 · 버퍼 · 투영 · β 띠는 V01 그대로 · 이탈 공개 · 측정만 카드라
     가족 · 표시와 무관). 굽기 전 다른 판단이 필요하면 이 한 곳(W06_THETA)을 바꾼다.
  B4 W06 재선정: 발동 결정 t · t+1 에서 두 팔 모두 버퍼 없이 새로 고른다(주 팔 = 6개월 점수 · 대조 팔 = 12-2 점수) · 주 팔 − 대조 팔 = 짧은 창 효과 ·
     대조 팔 − 정기판 = 지금 갈아탄 효과 · 그 뒤 달은 V01 규칙(버퍼 · 직전 선정). 발동이 겹치면 이어진다. Δ 는 비율이라 연율 상수와 무관.
     일간 계열 = S&P 500 가격지수(^GSPC · 1993~2006-01-03) 뒤 SPY 총수익(랩 assets.json) — 이음 공개 · 문턱 = t−1 까지 Δ 가 60 개 이상일 때.
  B5 W06 사건 창: 발동 결정일 종가부터 두 책을 흘러가게 두고(재조정 없음) h = 21 · 42 거래일 누적 상대수익.
  B6 W12 β̂: 252일 일간 OLS(유효 ≥ 200) · 시장 = 합집합 시총가중(w_ipca I9) · 하루 늦춤(전일까지) · 단면 = 그날 앞 마지막 월말 합집합 명단(금융 포함 · 섹터 더미) ·
     γ_d 는 이름 ≥ 50 인 날만. 스텝 효과(날 d) = −a_d′r_d − 2·c·Σ|a_d|(a = V02 책 − w_B · 편도 c) · 달마다 더해 V02 정적 경로에 Δ 로 싣는다.
  B7 W10m: tail = Q0.10(63일)/σ(63일 · ddof 1) · 유효 ≥ 50 · 단면 z(달 안) · IQR = 그달 tail 의 P75 − P25 · 상태 z = 확장창(2010-01~ · 관측 ≥ 12 · 아니면 None) ·
     교차항 = w_stagem.state_interaction(달별 γ_t(z) 를 s_t 에 회귀한 기울기 · 달력 틈 NW(3) — w_stagem S4 선언).
  B8 Stage M-W 세계(연기용 근사 · 굽기는 w_panel): 합집합 · 시총이 선 이름 · 비금융 · 비FPI · 발행사 그룹당 한 줄(시총 큰 줄) · 섹터가 선 이름 ·
     VAL = 섹터 안 (백분위 E/P + 백분위 S/P)/2 의 섹터 안 z(E ≤ 0 이면 E/P 최하위 · 결측 더미).
  B9 🔁 W10m 상태 · 쌍둥이(등록 전 · 비평 1 L1 · M5): 상태는 w10m_state 하나(패널 모든 달의 확장창 — 가족 교차항과 위생 심기가 같은 상태) ·
     척도 없는 쌍둥이 = γ_t ÷ SD_t(tail)(그달 z 표준화의 분모 · 원 단위 기울기 b_t)를 같은 상태에 회귀(보고) — z(tail) 의 γ_t = b_t·SD_t(tail) 라
     IQR 상태와 SD 가 함께 움직이면 무조건 b > 0 만으로 교차항이 생기는 기계적 몫을 뺀 판 · 가족 교차항과 같은 부호인지를 주의 칸으로(표시 · 가족과 무관).

🚨 랩 규율 — 등록 커밋 전에는 실자료로 수익 · IC · FM γ · 신호-수익 통계를 계산하지 않는다. 공개 함수 가운데 수익을 받는 것은 kind 자물쇠를 지난다.
   --blind-smoke 는 실자료 신호 위에서 y(다음 달 수익) · 일간 평가 수익 · 섹터 수익을 씨앗 잡음으로 바꿔 파이프라인 전체를 돌리고 산출을 열지 않고 지운다
   (w_hygiene.blind_smoke) — 찍는 것은 참/거짓 · 시간 · 개수 · 모양뿐.

  python build/w_cards.py --selftest
  python build/w_cards.py --blind-smoke         실자료 눈가린 연기(산출 열지 않고 삭제)
  python build/w_cards.py --fomc                FOMC 정례 결정일 빌드(연준 공개 일정 · 캐시 · 개수만 찍는다)
"""
from __future__ import annotations

import copy
import io
import json
import math
import os
import re
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

# ══════════════════════════════════════════════════════════════════════════
#  카드 목록(등록 A · 명세 상수 그대로)
# ══════════════════════════════════════════════════════════════════════════
CARDS = {
    "W01": {"name": "IPCA-KPS8", "module": "w_ipca", "role": "가족 A", "direction": +1, "ic_lit": 0.012, "sleeve": {"q": 0.30, "theta0": 0.75},
            "c_arm": "교차항 β × z(BAA10Y) · 반전 × z(VIX)(모형 안 · 실시간 확장창)", "p0_synth": "0.082(σ 0.047) · 0.043(σ 0.07)",
            "twins": ["K1", "K2", "K4", "UNRESTRICTED", "LAM_SE", "PIT_ONLY"], "cautions": ["dm_t_gt0", "v_repack"]},
    "W04": {"name": "CIQ-LT", "module": "w_ciq", "role": "가족 A", "direction": +1, "ic_lit": 0.016, "sleeve": {"q": 0.30, "theta0": 0.50},
            "c_arm": "θ_t = 0.5 + 0.25·clip(−z_t, −2, 2)", "p0_synth": "0.141(σ 0.047) · 0.044(σ 0.092)", "twins": ["CAPM 잔차판"],
            "cautions": ["dnbeta_repack", "v_repack"]},
    "W10m": {"name": "TAILX", "module": "w_cards", "role": "가족 A", "direction": +1, "ic_lit": 0.010, "sleeve": None,
             "c_arm": "교차항 z(tail)·z(IQR_t)(FM 한 줄 · 책 없음)", "p0_synth": "0.060(σ 0.047) · 0.034(σ 0.07)", "twins": [], "cautions": []},
    "W03": {"name": "PAP", "module": "w_pap", "role": "측정만", "direction": +1, "sr_lit": 0.70, "sleeve": {"gross": 0.20, "sband": 0.15},
            "c_arm": None, "p0_synth": "0.056", "twins": ["PEP+PAP", "24 산업그룹(빌드되면)", "내부 L French 49(20년 창)"]},
    "W06": {"name": "MOM-CR", "module": "w_cards", "role": "측정만(사건)", "direction": None, "sleeve": "V01 정적(B3)", "c_arm": "발동 뒤 두 결정 6개월 점수",
            "twins": ["6개월 위험조정 모멘텀"]},
    "W12": {"name": "FOMC-SML", "module": "w_cards", "role": "측정만", "direction": +1, "sleeve": "V02 정적 + FOMC 날 중립", "c_arm": "날짜가 곧 조건",
            "twins": []},
}
STEPS = {"S3e": "w_steps.s3e_theta", "S2": "w_steps.s2_execute", "S1": "w_steps.tranche_path"}
STEP_ORDER_W01 = ("W01-S", "W01-C", "+S3e", "+S2", "+S1")
assert set(CARDS) == set(WC.REGISTRATION["A"]["cards"]) and tuple(sorted(STEPS)) == tuple(sorted(WC.STEPS))
assert all(CARDS[c]["role"] == "가족 A" for c in WC.FAMILY["A"]) and all(CARDS[c]["role"].startswith("측정만") for c in WC.MEASURE_ONLY)
assert all(CARDS[c]["direction"] == WC.CARD_DIRECTION[c] for c in CARDS if c in WC.CARD_DIRECTION)

Q_DEFAULT, BUFFER = 0.30, 1.5
TURN_BUDGET_MONTH = 2.0 * WC.TURN_MAX / 12.0                 # B2
COST, COST_ROBUST = 0.0010, 0.0020
FIN_SECTOR = "Financials"
W06_THETA = "S0"                                             # B3 — V01 정적(θ0)
W06_WIN_D, W06_Q, W06_H = 63, 0.95, (21, 42)
W06_MIN_HIST = 60
TAIL_WIN, TAIL_MIN, TAIL_Q = 63, 50, 0.10
TAIL_STATE_MIN = 12
FOMC_FROM, FOMC_TO = "2009-01", "2026-08"
FOMC_T1 = ("2014-06", "2026-08")
FOMC_NW = 5
FOMC_PLACEBO = 200
FOMC_MIN_NAMES = 50
FED = "https://www.federalreserve.gov/monetarypolicy/"
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

CARDS_UNITS = [WG.unit("mom6", source="data/pit_px.json", concept="6-month price momentum skipping last month", use="signal"),
               WG.unit("sp_vol63", source="vbatch_cache/raw/yf/_GSPC.csv + data/assets.json SPY", concept="63-day S&P 500 daily volatility ratio",
                       use="theta_state"),
               WG.unit("fomc_day", source="federalreserve.gov FOMC calendars", concept="scheduled FOMC decision day", use="signal"),
               WG.unit("beta_ols252", source="data/pit_px.json", concept="252-day daily OLS market beta (previous day)", use="signal"),
               WG.unit("tail_q10", source="data/pit_px.json", concept="10% quantile of 63-day daily returns over sigma", use="signal"),
               WG.unit("tail_iqr", source="data/pit_px.json", concept="cross-sectional IQR of tail shape", use="theta_state"),
               WG.unit("val", source="v_fund(first-filed ledger) ni rev", concept="value_ep_sp (V06 VAL within-sector)", use="control")]
WG.assert_units(CARDS_UNITS, "w_cards 입력(모듈 적재)")


def _C():
    return WC.frozen("v_core")


def _VK():
    return WC.frozen("v_cards")


# ══════════════════════════════════════════════════════════════════════════
#  공통 슬리브(B1 · B2)
# ══════════════════════════════════════════════════════════════════════════
class Cross:
    """결정 달 단면(슬리브용 · v_cards.Cross 와 같은 속성 이름) — t · k · me · wB · sec · ndx · beta(FP β̂ · β 띠) · fin · logme · mom(선택)."""

    def __init__(self, m, t, me, wB, sec, ndx, beta, fin=None, mom=None, k=None):
        self.m = m
        self.t = list(t)
        self.k = list(k) if k is not None else list(t)
        self.n = len(self.t)
        self.pos = {x: j for j, x in enumerate(self.t)}
        self.me = np.asarray(me, float)
        wB = np.asarray(wB, float)
        self.wB = wB / wB.sum() if wB.sum() > 0 else wB
        self.sec = list(sec)
        self.ndx = np.asarray(ndx, bool)
        self.beta = np.asarray(beta, float)
        self.fin = np.asarray(fin if fin is not None else [s == FIN_SECTOR for s in self.sec], bool)
        with np.errstate(divide="ignore", invalid="ignore"):
            self.logme = np.log(self.me)
        self.mom = np.asarray(mom, float) if mom is not None else np.full(self.n, np.nan)
        q80 = float(np.quantile(self.me, 0.8)) if self.n else 0.0
        self.me80 = np.minimum(self.me, q80)
        self.wB80 = self.me80 / self.me80.sum() if self.n else self.me80

    def book(self, w):
        return {self.t[j]: float(w[j]) for j in np.flatnonzero(w > 0)}


def select_top(X, score, q=Q_DEFAULT, prev=None, buffer=True, elig=None):
    """B1 선정 — 비금융 · 점수가 선 이름 안 frozen v_cards._rank_select. 돌려주는 것 bool 배열."""
    score = np.asarray(score, float)
    el = np.isfinite(score) & ~X.fin
    if elig is not None:
        el &= np.asarray(elig, bool)
    mask = np.zeros(X.n, bool)
    for i in _VK()._rank_select(score, el, X.t, q, prev, buffer):
        mask[i] = True
    return mask


def w_f_of(X, mask):
    """B1 — 금융주 w_B 그대로 · 비금융 선정 이름에 (1 − 금융 w_B 합) 시총 비례."""
    w = np.where(X.fin, X.wB, 0.0)
    sel = mask & ~X.fin
    if not sel.any():
        return None
    w[sel] = (1.0 - float(X.wB[X.fin].sum())) * X.me[sel] / float(X.me[sel].sum())
    return w / w.sum()


def sleeve_target(X, mask, theta, beta_band=True):
    """최종 목표 책 — w_f → frozen v_core.project_active → w_B + θ(w_p − w_B) → frozen v_core.beta_band. (w | None, info)."""
    C = _C()
    if theta is None or not (0.0 <= float(theta) <= 1.0 + 1e-12):
        raise SystemExit("🚨 θ ∈ [0, 1](명세 θ ≤ 1)")
    wf = w_f_of(X, mask)
    if wf is None:
        return None, {"n_sel": 0}
    proj = lambda x: C.project_active(x, X.wB, X.sec, X.ndx)[0]
    wp, pinfo = C.project_active(wf, X.wB, X.sec, X.ndx)
    w = X.wB + float(theta) * (wp - X.wB)
    info = {"n_sel": int(mask.sum()), "proj": {k: pinfo[k] for k in ("iters", "shrink", "feasible")}}
    if beta_band:
        w, binfo = C.beta_band(w, X.wB, X.beta, proj)
        info["beta"] = binfo
    w = np.where(w > 1e-15, w, 0.0)
    w = w / w.sum()
    C.assert_stock_book(X.book(w))
    WG.no_derivative_positions(X.book(w))
    return w, info


def turnover_skip(w_drift, w_exec, budget=TURN_BUDGET_MONTH):
    """B2 — Σ|Δw| > budget 이면 |Δw| 작은 이름부터 흘러간 비중으로 되돌리고 합 1 로 비례(되돌릴 때마다 실제 거래량을 다시 잰다) ·
    돌려주는 것 (책, 거래량, 건너뛴 수)."""
    names = sorted(set(w_drift) | set(w_exec))
    wd = {k: float(w_drift.get(k, 0.0)) for k in names}
    d = {k: float(w_exec.get(k, 0.0)) - wd[k] for k in names}

    def norm(b):
        b = {k: v for k, v in b.items() if v > 0}
        s_ = sum(b.values())
        return {k: v / s_ for k, v in b.items()} if s_ > 0 else b

    def traded(b):
        return sum(abs(b.get(k, 0.0) - wd[k]) for k in names)
    book = norm(dict(w_exec))
    tr = traded(book)
    if tr <= budget:
        return book, tr, 0
    raw, skipped = dict(w_exec), 0
    for k in sorted(names, key=lambda x: (abs(d[x]), x)):
        if tr <= budget:
            break
        if d[k] == 0:
            continue
        raw[k] = wd[k]
        skipped += 1
        book = norm(raw)
        tr = traded(book)
    return book, tr, skipped


def execute(w_drift, target, fill=0.5, band_frac=0.1, budget=TURN_BUDGET_MONTH):
    """체결 — frozen v_core.execute_book(½ 체결 · 틈 < 0.1·목표 무거래 · 삭제 전량) → B2 회전 예산. (책, 거래량, 건너뛴 수)."""
    b, _ = _C().execute_book(w_drift, target, fill=fill, band_frac=band_frac)
    return turnover_skip(w_drift, b, budget)


# ══════════════════════════════════════════════════════════════════════════
#  W06 MOM-CR(B3 ~ B5)
# ══════════════════════════════════════════════════════════════════════════
def sp_daily():
    """B4 — S&P 500 일간 수익 {날짜: r}: ^GSPC 가격(V 캐시 원자료 · 읽기 전용 · 2006-01-03 까지) 뒤 SPY 총수익(랩 assets.json) — 🚨 시장 상태 신호의 원천."""
    import csv
    p = os.path.join(WC.VB_CACHE, "raw", "yf", "_GSPC.csv")
    gs = {}
    with io.open(p, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                gs[row["Date"][:10]] = float(row["Close"])
            except (KeyError, ValueError):
                continue
    VD = WC.frozen("v_data")
    A = VD.read_json(VD.lab_path("data/assets.json"))
    spy = {d: float(v) for d, v in zip(A["dates"], A["px"]["SPY"]) if v is not None}
    first_spy = min(spy)
    out = {}
    ds = sorted(d for d in gs if d <= first_spy)
    for a, b in zip(ds[:-1], ds[1:]):
        out[b] = gs[b] / gs[a] - 1.0
    ss = sorted(spy)
    for a, b in zip(ss[:-1], ss[1:]):
        out[b] = spy[b] / spy[a] - 1.0
    return out


def vol_trigger(daily, from_month="1993-01", win=W06_WIN_D, q=W06_Q, min_hist=W06_MIN_HIST):
    """B4 — 월말 t 의 V_t · Δ_t · 문턱(t−1 까지 Δ 의 q 백분위 · Δ ≥ min_hist 개) · 발동. 돌려주는 것 {달: {V, delta, thr, trig}}."""
    ds = sorted(d for d in daily if d[:7] >= from_month)
    r = np.array([daily[d] for d in ds], float)
    last = {}
    for i, d in enumerate(ds):
        last[d[:7]] = i
    out, prevV, hist = {}, None, []
    for m in sorted(last):
        i = last[m]
        if i + 1 < win:
            continue
        V = float(np.std(r[i + 1 - win:i + 1], ddof=1))
        if prevV is None or prevV <= 0:
            prevV = V
            continue
        delta = V / prevV - 1.0
        thr = float(np.quantile(hist, q)) if len(hist) >= min_hist else None
        out[m] = {"V": V, "delta": delta, "thr": thr, "trig": bool(thr is not None and delta > thr)}
        hist.append(delta)
        prevV = V
    return out


def w06_schedule(trig, months):
    """B4 — 발동 결정 t · t+1 을 6개월 점수 달로(겹치면 이어진다). 돌려주는 것 {달: bool}."""
    on = set()
    for m in months:
        if (trig.get(m) or {}).get("trig"):
            on |= {m, WC.mshift(m, 1)}
    return {m: (m in on) for m in months}


def mom6_of(U, k, m):
    """6개월 원수익(최근 1개월 제외 · MSCI 정의) = P_{m−1}/P_{m−7} − 1(월말 수정종가)."""
    j = U._mpos[m]
    if j < 7:
        return None
    a, b = U.Pm[k][j - 7], U.Pm[k][j - 1]
    return float(b / a - 1.0) if (a == a and b == b and a > 0) else None


def v01_arms(crosses, months, sched, theta=0.75):
    """W06 세 팔(B3 · B4) — crosses{달: v_cards.Cross 꼴(mom · mom6 속성)} · sched{달: 6개월 점수 달}. 돌려주는 것 {팔: {달: 책}}(팔 = V01_S0 · W06 · CTRL12).
    V01 선정 · 버퍼 · 투영 · β 띠 = frozen v_cards(select · target_book)."""
    VK = _VK()
    spec = VK.spec_of("V01")
    nobuf = dict(spec, buffer=False)
    out = {"V01_S0": {}, "W06": {}, "CTRL12": {}}
    prev = {a: None for a in out}
    for m in months:
        X = crosses.get(m)
        if X is None:
            prev = {a: None for a in out}
            continue
        for arm in out:
            if arm != "V01_S0" and sched.get(m):
                if arm == "W06":
                    X6 = copy.copy(X)
                    X6.mom = np.asarray(X.mom6, float)
                    mask = VK.select(X6, nobuf, prev=None)
                else:
                    mask = VK.select(X, nobuf, prev=None)
            else:
                mask = VK.select(X, spec, prev=prev[arm])
            w, _ = VK.target_book(X, spec, mask, theta)
            if w is None:
                continue
            out[arm][m] = X.book(w)
            prev[arm] = {X.t[i] for i in np.flatnonzero(mask)}
    return out


def event_windows(kind, books_a, books_b, day_index, day_ret, horizons=W06_H):
    """B5 — 발동 결정 달 m 마다 결정일 종가부터 두 책을 흘러가게 두고 h 거래일 누적 상대수익(a − b). day_index{달: 결정일 색인} ·
    day_ret(i) → {이름: 수익}. 🚨 수익 — kind 자물쇠. 돌려주는 것 {달: {h: 상대수익}}."""
    WC.assert_kind_allowed(kind, "w_cards.event_windows")
    out = {}
    for m in sorted(set(books_a) & set(books_b) & set(day_index)):
        i0 = day_index[m]
        res = {}
        wa, wb = dict(books_a[m]), dict(books_b[m])
        ga = gb = 1.0
        for h in range(1, max(horizons) + 1):
            r = day_ret(i0 + h)
            if r is None:
                break
            for w, which in ((wa, "a"), (wb, "b")):
                g = sum(v * (1.0 + float(r.get(k, 0.0) or 0.0)) for k, v in w.items())
                for k in list(w):
                    w[k] = w[k] * (1.0 + float(r.get(k, 0.0) or 0.0)) / g
                if which == "a":
                    ga *= g
                else:
                    gb *= g
            if h in horizons:
                res[h] = ga - gb
        out[m] = res
    return out


# ══════════════════════════════════════════════════════════════════════════
#  W12 FOMC-SML(B6)
# ══════════════════════════════════════════════════════════════════════════
_MON = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}
_EXCL = ("unscheduled", "conference", "notation", "cancel")
_HEAD_RX = re.compile(r"^(?P<m1>[A-Za-z]+)(?:/(?P<m2>[A-Za-z]+))?\s+(?P<d1>\d{1,2})(?:-(?:(?P<m3>[A-Za-z]+)\s+)?(?P<d2>\d{1,2}))?\s*(?P<rest>.*?)\s*-\s*(?P<y>\d{4})\s*$")


def _mon(s):
    return _MON.get((s or "")[:3].lower())


def parse_fomc_heading(text):
    """역사 쪽 제목 한 줄(«July 31-August 1 Meeting - 2012» · «April/May 30-1 Meeting - 2013» · «March 4 (unscheduled) - 2014») → 결정일 | None."""
    t = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
    mt = _HEAD_RX.match(t)
    if not mt:
        return None
    rest = mt.group("rest").lower()
    if "meeting" not in rest or any(x in rest for x in _EXCL):
        return None
    y = int(mt.group("y"))
    if mt.group("d2"):
        mon = _mon(mt.group("m3") or mt.group("m2") or mt.group("m1"))
        day = int(mt.group("d2"))
    else:
        mon, day = _mon(mt.group("m1")), int(mt.group("d1"))
    return "%04d-%02d-%02d" % (y, mon, day) if mon else None


def parse_fomc_historical(html):
    heads = re.findall(r"<h[3-6][^>]*>([^<]*(?:Meeting|Conference Call|\(unscheduled\)|\(notation vote\))[^<]*)</h[3-6]>", html)
    out = [parse_fomc_heading(h) for h in heads]
    return sorted(set(d for d in out if d))


def parse_fomc_current(html):
    """fomccalendars 쪽 — 해 판(«YYYY FOMC Meetings») 안 달(strong) · 날(«27-28» · «17-18*» · «30-1» · «3 (unscheduled)»)."""
    out = set()
    parts = re.split(r"(\d{4}) FOMC Meetings", html)
    for j in range(1, len(parts) - 1, 2):
        y = int(parts[j])
        body = parts[j + 1]
        rows = re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', body, flags=re.S)
        for mon_s, date_s in rows:
            ds = date_s.strip().lower()
            if any(x in ds for x in _EXCL):
                continue
            nums = re.findall(r"\d{1,2}", ds)
            if not nums:
                continue
            mons = mon_s.strip().split("/")
            mon = _mon(mons[-1] if len(nums) > 1 and len(mons) > 1 else mons[0])
            day = int(nums[-1])
            if len(nums) > 1 and len(mons) == 1 and int(nums[-1]) < int(nums[0]):
                mon = mon % 12 + 1
            if mon:
                out.add("%04d-%02d-%02d" % (y, mon, day))
    return sorted(out)


def fomc_calendar(fetch=True, sleep=1.0):
    """FOMC 정례 결정일(2009-01 ~ 2026-08) — 연준 공개 쪽(원 HTML 은 캐시 raw/fomc · 저장소 밖) → 목록 · sha. 수익과 무관."""
    import hashlib
    import urllib.request
    raw = WC.cache_dir("raw", "fomc")
    pages = ["fomchistorical%d.htm" % y for y in range(int(FOMC_FROM[:4]), 2021)] + ["fomccalendars.htm"]
    dates, shas = set(), {}
    for fn in pages:
        p = os.path.join(raw, fn)
        if not os.path.exists(p):
            if not fetch:
                raise SystemExit("🚨 FOMC 원 쪽 없음: %s" % fn)
            req = urllib.request.Request(FED + fn, headers={"User-Agent": UA_BROWSER})
            blob = urllib.request.urlopen(req, timeout=60).read()
            with open(p, "wb") as f:
                f.write(blob)
            time.sleep(sleep)
        with open(p, "rb") as f:
            blob = f.read()
        shas[fn] = hashlib.sha256(blob).hexdigest()
        html = blob.decode("utf-8", "replace")
        dates |= set(parse_fomc_current(html) if fn == "fomccalendars.htm" else parse_fomc_historical(html))
    ds = sorted(d for d in dates if FOMC_FROM <= d[:7] <= FOMC_TO)
    by_year = {}
    for d in ds:
        by_year[d[:4]] = by_year.get(d[:4], 0) + 1
    return {"dates": ds, "n": len(ds), "by_year": by_year, "sha256": shas, "source": FED + "{fomccalendars,fomchistorical<YYYY>}.htm"}


def rolling_beta(DR, mkt, win=252, min_obs=200):
    """B6 — 이름마다 252일 일간 OLS β(유효 ≥ 200) · 하루 늦춤(β[d] = d−1 까지). DR(일 × 이름) · mkt(일). 누적합으로 결측을 지키며."""
    import pandas as pd
    R = pd.DataFrame(DR)
    M = pd.Series(mkt)
    valid = R.notna() & M.notna().to_numpy()[:, None]
    Rv = R.where(valid)
    Mv = pd.DataFrame(np.broadcast_to(M.to_numpy()[:, None], R.shape)).where(valid)
    n = valid.astype(float).rolling(win, min_periods=1).sum()
    sx = Mv.fillna(0.0).rolling(win, min_periods=1).sum()
    sy = Rv.fillna(0.0).rolling(win, min_periods=1).sum()
    sxy = (Mv * Rv).fillna(0.0).rolling(win, min_periods=1).sum()
    sxx = (Mv * Mv).fillna(0.0).rolling(win, min_periods=1).sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = sxy - sx * sy / n
        var = sxx - sx * sx / n
        b = (cov / var).where(n >= min_obs)
    return b.shift(1).to_numpy()


def daily_sml(kind, days, Y, B, sec_of_day, min_names=FOMC_MIN_NAMES):
    """B6 — 날 d 마다 r_{i,d} ~ 1 + β̂_i + 섹터 더미 → γ_d(β 계수). Y · B(일 × 이름) · sec_of_day(d) → (이름 bool 마스크, 섹터 배열).
    🚨 수익 — kind 자물쇠. 돌려주는 것 {날 색인: γ_d}."""
    WC.assert_kind_allowed(kind, "w_cards.daily_sml")
    out = {}
    for d in days:
        mask, sec = sec_of_day(d)
        if mask is None:
            continue
        y, b = Y[d], B[d]
        ok = mask & np.isfinite(y) & np.isfinite(b)
        if ok.sum() < min_names:
            continue
        s = np.asarray(sec, object)[ok]
        cols = [np.ones(ok.sum()), b[ok]]
        for g in sorted(set(s), key=str)[1:]:
            cols.append((s == g).astype(float))
        X = np.column_stack(cols)
        coef = np.linalg.lstsq(X, y[ok], rcond=None)[0]
        out[d] = float(coef[1])
    return out


def fomc_slope_test(kind, gamma, is_fomc, lag=FOMC_NW):
    """γ_d ~ a + b·1[FOMC_d] — b 의 NW(lag) t(연속 관측 · frozen v_tests.nw_ols) · H1 b > 0. 🚨 kind 자물쇠."""
    WC.assert_kind_allowed(kind, "w_cards.fomc_slope_test")
    ds = sorted(gamma)
    y = np.array([gamma[d] for d in ds], float)
    x = np.array([1.0 if is_fomc(d) else 0.0 for d in ds])
    if x.sum() < 3 or len(ds) < 30:
        return {"T": len(ds), "n_fomc": int(x.sum()), "b": None, "t": None}
    b, se, n = WC.frozen("v_tests").nw_ols(y, np.column_stack([np.ones(len(x)), x]), lag)
    t = float(b[1] / se[1]) if se[1] > 0 else None
    return {"T": n, "n_fomc": int(x.sum()), "b": float(b[1]), "t": t, "p_one": WC.one_sided_p(t, n, +1), "direction": +1}


def fomc_step_effect(kind, days, active_of_day, day_ret, cost=COST):
    """B6 — 날 d 마다 −a_d′r_d − 2·c·Σ|a_d|(V02 책 − w_B 의 능동 a · 결정 전 주 · d−1 종가 체결 · d 종가 되돌림). 🚨 kind 자물쇠. {날: 효과}."""
    WC.assert_kind_allowed(kind, "w_cards.fomc_step_effect")
    out = {}
    for d in days:
        a = active_of_day(d)
        r = day_ret(d)
        if a is None or r is None:
            continue
        ar = sum(v * float(r.get(k, 0.0) or 0.0) for k, v in a.items())
        out[d] = -ar - 2.0 * cost * sum(abs(v) for v in a.values())
    return out


def fomc_placebo_days(candidates, n_days, reps, seed):
    """대조 — 비발표일 후보에서 같은 수의 날을 reps 번 뽑는다(씨앗 seed + i) · 돌려주는 것 [[날]]."""
    cand = sorted(candidates)
    return [sorted(np.random.default_rng(seed + i).choice(cand, n_days, replace=False).tolist()) for i in range(int(reps))]


# ══════════════════════════════════════════════════════════════════════════
#  W10m TAILX(B7)
# ══════════════════════════════════════════════════════════════════════════
def tail_shape(Rw, q=TAIL_Q, min_obs=TAIL_MIN):
    """tail = Q0.10(63일)/σ(63일 · ddof 1) — Rw(63 × N) · 유효 ≥ min_obs."""
    Rw = np.asarray(Rw, float)
    out = np.full(Rw.shape[1], np.nan)
    for j in range(Rw.shape[1]):
        x = Rw[:, j]
        x = x[np.isfinite(x)]
        if len(x) < min_obs:
            continue
        sd = float(x.std(ddof=1))
        if sd > 0:
            out[j] = float(np.quantile(x, q)) / sd
    return out


def xs_z(x):
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    out = np.full(len(x), np.nan)
    if ok.sum() >= 3:
        sd = float(x[ok].std(ddof=1))
        out[ok] = (x[ok] - x[ok].mean()) / sd if sd > 0 else 0.0
    return out


def iqr_state(iqr_by_month, months, min_n=TAIL_STATE_MIN):
    """확장창 z(관측 ≥ min_n · 아니면 None)."""
    hist, out = [], {}
    for m in months:
        v = iqr_by_month.get(m)
        if v is None or not (v == v):
            out[m] = None
            continue
        hist.append(float(v))
        if len(hist) < min_n:
            out[m] = None
            continue
        sd = float(np.std(hist, ddof=1))
        out[m] = (v - float(np.mean(hist))) / sd if sd > 0 else 0.0
    return out


def w10m_state(P, tail_key="tail"):
    """W10m 상태 — 패널 모든 달(추정 되돌아보기 2010-01 ~ 포함)의 단면 IQR(tail) → 확장창 z(iqr_state) · 단면 SD(척도 쌍둥이 칸). 돌려주는 것 (상태{달}, SD{달}).
    가족 교차항 · 위생 심기가 **같은** 상태를 쓴다(등록 전 고침 — 비평 1 L1: 심기 쪽 상태가 2016-08 에서 확장창을 새로 시작했다)."""
    iqr, sd = {}, {}
    for m in P["months"]:
        D = P["m"].get(m)
        if D is None:
            continue
        v = np.asarray(D[tail_key], float)
        v = v[np.isfinite(v)]
        if len(v) >= 20:
            iqr[m] = float(np.quantile(v, 0.75) - np.quantile(v, 0.25))
        if len(v) >= 3:
            sd[m] = float(v.std(ddof=1))
    return iqr_state(iqr, [m for m in P["months"] if m in P["m"]]), sd


def w10m_line(P, tail_key="tail", months=None, B=None, seed=None):
    """W10m 한 줄 — FM(z(tail) · Stage M-W 통제) → 달별 γ_t → state_interaction(IQR 상태 z · 방향 +1). 🚨 kind 자물쇠(w_stagem.fm).
    B · seed 를 주면 교차항에 S11 야생 부트스트랩 p(가족 판정 칸) · 🔁 척도 없는 쌍둥이(B9 · 보고): γ_t 를 그달 단면 SD(tail) 로 나눈 판
    (z 표준화 때문에 γ_t = b_t · SD_t(tail) 이라 IQR 상태와 SD 가 함께 움직이면 무조건 b > 0 만으로도 교차항이 생긴다 — 그 기계적 몫을 뺀 판)."""
    import w_stagem as S
    ms = months or [m for m in P["months"] if m in P["m"]]
    st, sd = w10m_state(P, tail_key)
    res = S.fm(ms, lambda m: [S.stage_m_w_design(P["m"][m], [("tail_z", xs_z(P["m"][m][tail_key]))])], ["tail_z"], P["kind"])
    si = S.state_interaction(res["months"], res["g"]["tail_z"], st, WC.CARD_DIRECTION["W10m"], B=B, seed=seed)
    sc = S.state_interaction(res["months"], res["g"]["tail_z"], st, WC.CARD_DIRECTION["W10m"], scale=sd)
    same = (None if (si.get("gamma1") is None or sc.get("gamma1") is None) else bool(np.sign(si["gamma1"]) == np.sign(sc["gamma1"])))
    return {"interaction": si, "interaction_scaled": sc, "scaled_same_sign": same,
            "main": S.summarize(res["months"], res["g"]["tail_z"], +1), "n_state": sum(1 for v in st.values() if v is not None)}


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기(실자료 신호 · y 와 평가 수익은 씨앗 잡음 · 산출은 열지 않고 삭제)
# ══════════════════════════════════════════════════════════════════════════
SMOKE_FROM, SMOKE_TO = "2010-01", "2026-07"


def _log(msg):
    print(msg, flush=True)


def _pct_within(x, groups):
    """섹터 안 백분위(평균 순위 · 0~1) — 결측 NaN."""
    import w_stagem as S
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    g = np.asarray(groups, object)
    for s in set(v for v in g if v is not None):
        idx = np.flatnonzero((g == s) & np.isfinite(x))
        if len(idx) < 2:
            continue
        out[idx] = S.avg_rank(x[idx]) / (len(idx) - 1)
    return out


def smoke_world(U, m):
    """B8 — Stage M-W 세계 근사(연기용) + 슬리브 단면 행. 돌려주는 것 (세계 행, 슬리브 행)."""
    me = U.me(m)
    rows = []
    for r in U.members(m):
        v = me[r["t"]][0]
        if not v:
            continue
        sec, _ = U.sector(r["t"], m, r["ndx_only"])
        rows.append(dict(r, me=float(v), sec=sec))
    world, seen = [], {}
    for r in sorted(rows, key=lambda z: -z["me"]):
        if r["sec"] is None or r["sec"] == FIN_SECTOR or r.get("fpi"):
            continue
        g = r.get("gid") or ("_" + r["t"])
        if g in seen:
            continue
        seen[g] = True
        world.append(r)
    world.sort(key=lambda z: z["t"])
    rows.sort(key=lambda z: z["t"])
    return world, rows


def smoke_panel(U, months, DR, kcol, mkt_d, log=_log):
    """연기 패널(kind real — 곧바로 w_hygiene.blind_panel 이 y 를 잡음으로 바꾼다) · 슬리브 단면. 🚨 y 값을 찍지 않는다."""
    import w_ipca as IP
    VF = WC.frozen("v_fund")
    P = {"kind": "real", "months": [], "m": {}}
    X, t0 = {}, time.time()
    for i, m in enumerate(months):
        world, rows = smoke_world(U, m)
        if len(world) < 50:
            continue
        d = U.d_of(m)

        def asset_of(r, dd):
            if not r.get("gid"):
                return None
            at = VF.latest(U.L.series(r["gid"], "asset", "i"), dd)
            return at[0] if at else None
        K8 = IP.kps8_month(U, m, world, mkt_d, asset_of=asset_of, DR=DR, kcol=kcol)
        hr = U.hold_ret(m)
        y = np.array([np.nan if hr.get(r["t"]) is None else float(hr[r["t"]]) for r in world])
        sec = np.array([r["sec"] for r in world], object)
        ep, sp = np.full(len(world), np.nan), np.full(len(world), np.nan)
        for a, r in enumerate(world):
            if not r.get("gid"):
                continue
            ni = VF.ttm_key(U.L, r["gid"], "ni", d)
            rv = VF.ttm_key(U.L, r["gid"], "rev", d)
            if ni:
                ep[a] = (ni[0] / r["me"]) if ni[0] > 0 else -1e9
            if rv and rv[0] > 0:
                sp[a] = rv[0] / r["me"]
        pe, ps = _pct_within(ep, sec), _pct_within(sp, sec)
        cnt = np.isfinite(pe).astype(int) + np.isfinite(ps).astype(int)
        v0 = np.where(cnt > 0, (np.nan_to_num(pe) + np.nan_to_num(ps)) / np.maximum(cnt, 1), np.nan)
        val = np.full(len(world), np.nan)
        z = IP.sector_z(v0, sec)
        val[np.isfinite(v0)] = z[np.isfinite(v0)]
        i1 = U.me_idx[m]
        cols = [kcol[r["k"]] for r in world]
        Rw = DR[i1 - TAIL_WIN + 1:i1 + 1][:, cols]
        D = {"t": [r["t"] for r in world], "k": [r["k"] for r in world], "gid": [r.get("gid") for r in world], "me": np.array([r["me"] for r in world]),
             "sec": sec, "y": y, "val": val, "tail": tail_shape(Rw), "fin": np.zeros(len(world), bool)}
        D.update(K8)
        if m >= "2016-08":
            bfp = {r["k"]: U.beta_fp(r["k"], m)["beta"] for r in rows}
            D["beta_fp"] = np.array([np.nan if bfp.get(r["k"]) is None else bfp[r["k"]] for r in world])
            wb = U.w_B(m)
            X[m] = Cross(m, [r["t"] for r in rows], [r["me"] for r in rows], [wb.get(r["t"], 0.0) for r in rows], [r["sec"] for r in rows],
                         [r["ndx_only"] for r in rows], [np.nan if bfp.get(r["k"]) is None else bfp[r["k"]] for r in rows], k=[r["k"] for r in rows])
        else:
            D["beta_fp"] = np.full(len(world), np.nan)
        P["months"].append(m)
        P["m"][m] = D
        if i % 24 == 0:
            log("  패널 %s · 세계 %d · %.0fs" % (m, len(world), time.time() - t0))
    return P, X


def _books_from_scores(X_by_m, score_of, theta_of, q=Q_DEFAULT):
    out, prev = {}, None
    for m in sorted(X_by_m):
        X = X_by_m[m]
        sc = score_of(m)
        if sc is None:
            prev = None
            continue
        s = np.array([sc.get(t, np.nan) for t in X.t], float)
        mask = select_top(X, s, q, prev=prev)
        w, _ = sleeve_target(X, mask, theta_of(m))
        if w is None:
            continue
        out[m] = X.book(w)
        prev = {X.t[i] for i in np.flatnonzero(mask)}
    return out


def _d0_path(books, ret_of):
    """연기용 D0 경로(체결 · 흘러감 · 회전) — ret_of(m) → {이름: 잡음 수익} · 돌려주는 것 (S{보유 달}, traded{보유 달})."""
    S, T, Ed = {}, {}, None
    C = _C()
    for m in sorted(books):
        tgt = books[m]
        if Ed is None:
            E, tr = dict(tgt), 0.0
        else:
            E, tr, _ = execute(Ed, tgt)
        Ed, R, _ = C.drift_book(E, ret_of(m))
        h = WC.mshift(m, 1)
        S[h], T[h] = R, tr
    return S, T


def blind_run(U, X, DR, kcol, mkt_d, seed):
    """w_hygiene.blind_smoke 에 넘기는 run(pb, out) — 카드 전부 · 스텝 · 대조 · 쌍둥이 일부. 🚨 수익은 모두 pb.y 또는 씨앗 잡음."""
    import pickle
    import pandas as pd
    import w_ciq as CQ
    import w_ipca as IP
    import w_pap as PP
    import w_stagem as S
    import w_steps as ST
    VD = WC.frozen("v_data")
    VK = _VK()

    def run(pb, out):
        try:
            return _run(pb, out)
        except Exception:                                                       # noqa: BLE001 — 줄 번호만 남긴다(값 없음) · 다시 던진다
            tb = traceback.format_exc()
            with io.open(os.path.join(WC.cache_dir("blind"), "_last_tb.txt"), "w", encoding="utf-8") as f:
                f.write(chr(10).join(ln for ln in tb.splitlines() if ln.startswith("  File") or ln.startswith("Traceback") or ":" not in ln[:40]))
            raise

    def _run(pb, out):
        assert pb["kind"] == "blind"
        rng = np.random.default_rng(seed + 1)
        res, tm = {}, {}
        ms_all = [m for m in pb["months"] if m in pb["m"]]
        dec = [m for m in ms_all if IP.FIRST_DECISION <= m <= IP.LAST_DECISION]
        noise_y = {m: {t: float(v) for t, v in zip(pb["m"][m]["t"], pb["m"][m]["y"]) if v == v} for m in ms_all}

        def ret_of(m):                                                  # 슬리브 D0 경로 — 세계 밖 이름(금융 등)도 잡음
            base = dict(noise_y.get(m, {}))
            for t in (X[m].t if m in X else []):
                if t not in base:
                    base[t] = float(rng.normal(0, 0.08))
            return base
        # ── W01 ─────────────────────────────────────────────────────────
        t0 = time.time()
        A = VD.read_json(VD.lab_path("data/assets.json"))
        cross = IP.cross_states(A["macro"]["BAA10Y"], A["macro"]["VIXCLS"], ms_all)
        WS = IP.walkforward(pb, log=_log)
        WCa = IP.walkforward(pb, cross=cross)
        res["W01"] = {}
        for arm, W in (("S", WS), ("C", WCa)):
            fm = S.fm(dec, lambda m: None if m not in W["dec"] else [S.stage_m_w_design(pb["m"][m], [("ipca_z", W["dec"][m]["score"])])],
                      ["ipca_z"], pb["kind"])
            res["W01"][arm] = {"fm": S.summarize(fm["months"], fm["g"]["ipca_z"], +1), "sigma": S.sigma_analytic(fm["parts"], "ipca_z")}
        base = IP.linear_baselines(pb)
        res["W01"]["structural"] = IP.structural_test(pb, WS["dec"], base)
        for tw in ("K1", "UNRESTRICTED", "PIT_ONLY"):
            res["W01"]["twin_" + tw] = len(IP.walkforward(pb, **IP.TWIN_SPECS[tw])["dec"])
        fml = S.fm(dec, lambda m: [S.stage_m_w_design(pb["m"][m], [("lit_z", IP.lit_composite(pb["m"][m]))])], ["lit_z"], pb["kind"])
        res["W01"]["lit"] = S.summarize(fml["months"], fml["g"]["lit_z"], +1)
        sc_C = {m: dict(zip(pb["m"][m]["t"], WCa["dec"][m]["score"])) for m in WCa["dec"]}
        sc_S = {m: dict(zip(pb["m"][m]["t"], WS["dec"][m]["score"])) for m in WS["dec"]}
        bk_S = _books_from_scores(X, sc_S.get, lambda m: CARDS["W01"]["sleeve"]["theta0"])
        bk_C = _books_from_scores(X, sc_C.get, lambda m: CARDS["W01"]["sleeve"]["theta0"])
        Sx, Tx = _d0_path(bk_C, ret_of)
        idx = pd.PeriodIndex(sorted(Sx), freq="M")
        Sser = pd.Series([Sx[str(p)] for p in idx], index=idx)
        Bser = pd.Series(rng.normal(0.008, 0.04, len(idx)), index=idx)
        Xf = WC.fund_x(Sser, Bser, COST_ROBUST, traded=pd.Series([Tx[str(p)] for p in idx], index=idx))
        res["W01"]["tier2"] = WC.tier2_harmless({str(p): float(v) for p, v in Xf.items()}, WC.turnover_annual(list(Tx.values())), True)
        res["W01"]["books"] = (len(bk_S), len(bk_C))
        _log("  W01 · %.0fs" % (time.time() - t0))
        # 스텝 — S3e(실현 IC) · S2 · S1
        ics = S.ic_series(dec, lambda m: WCa["dec"][m]["score"] if m in WCa["dec"] else np.array([]),
                          lambda m: S.sector_demean(pb["m"][m]["y"], pb["m"][m]["sec"]), pb["kind"])
        icm = dict(zip(ics["months"], ics["ic"]))
        res["S3e"] = ST.s3e_theta(icm, dec, CARDS["W01"]["sleeve"]["theta0"])["e_max"]
        lt = ST.lag_ic_table(pb["kind"], [m for m in ms_all if m >= IP.LAM_FROM], lambda m: sc_C.get(m) or {},
                             lambda m: noise_y.get(m), lags=ST.S2_DECAY_LAGS)
        sch = ST.s2_schedule(dec, {m: ST.lag_ic_asof(lt, m) for m in dec if m[5:7] == "08"}, IP.IC_LIT, {m: 0.08 for m in dec if m[5:7] == "08"})
        m2 = dec[-1]
        z2 = ST.s2_aim([sc_C.get(m2) or {}, sc_C.get(WC.mshift(m2, -1)) or {}, sc_C.get(WC.mshift(m2, -2)) or {}], sch[m2]["omega"])
        trd = ST.s2_tradable(z2, sch[m2]["ic0"], sch[m2]["sigma_cs"] or 0.08, sch[m2]["H"])
        b2, tr2, i2 = ST.s2_execute(bk_C.get(WC.mshift(m2, -1), {}), bk_C.get(m2, {}), trd)
        res["S2"] = {"n_trad": int(sum(trd.values())), "fallback": i2["fallback"]}
        last24 = dec[-24:]
        me_idx = [U.me_idx[m] for m in last24]
        names = sorted({k for m in last24 for k in bk_C.get(m, {})})
        noise_d = rng.normal(0, 0.012, (U.D, max(1, len(names))))
        pos = {nm: j for j, nm in enumerate(names)}
        tp = ST.tranche_path(pb["kind"], U.D, me_idx, lambda k, j, dday: bk_C.get(last24[j]),
                             lambda dd: {nm: float(noise_d[dd, pos[nm]]) for nm in names})
        res["S1"] = len(tp["month_ret"])
        tm["W01+steps"] = time.time() - t0
        # ── W04 ─────────────────────────────────────────────────────────
        t0 = time.time()
        rf = {str(k): float(v) for k, v in VD.lab_rf_monthly().items()}
        fac = CQ.market_factors(U, WC.months_between("2009-02", WC.mshift(IP.LAST_DECISION, 1)), rf)
        wmonths = sorted(set([CQ.FIRST_DECISION] + [m for m in ms_all if m >= CQ.FIRST_DECISION]))
        wins = CQ.run_windows(U, wmonths, fac, log=_log)
        dz = CQ.state_z({m: w["d_last"] for m, w in wins.items()}, sorted(wins))
        th_c = {m: CQ.theta_c(dz.get(m)) for m in dec}
        bench = VD.read_json(VD.lab_path("data/bench_px.json"))
        spx = np.array([np.nan if v is None else float(v) for v in bench["series"]["spx"]["px"]], float)
        bpos = {d: i for i, d in enumerate(bench["dates"])}
        with np.errstate(invalid="ignore", divide="ignore"):
            lspx = np.r_[np.nan, np.log(spx[1:] / spx[:-1])]
        ctl = {}
        for m in dec:
            D = pb["m"][m]
            i1 = U.me_idx[m]
            cols = [kcol[k] for k in D["k"]]
            Rd = DR[i1 - CQ.DN_WIN + 1:i1 + 1][:, cols]
            with np.errstate(invalid="ignore"):
                Rl = np.log1p(Rd)
            mw = np.array([lspx[bpos[x]] if x in bpos else np.nan for x in U.dates[i1 - CQ.DN_WIN + 1:i1 + 1]])
            ctl[m] = {"b_dn": CQ.downside_beta(Rl, mw), "ltd": CQ.ltd_np(Rd, CQ.market_ex_i(Rd, D["me"]))}
        beta_ciq = {m: np.array([wins.get(m, {}).get("beta", {}).get(k, np.nan) for k in pb["m"][m]["k"]]) for m in dec}

        def des(m, full):
            D = pb["m"][m]
            ex = [("beta_fp", D["beta_fp"])] + ([("b_dn", ctl[m]["b_dn"]), ("ltd_np", ctl[m]["ltd"])] if full else [])
            return [S.stage_m_w_design(D, [("ciq_z", xs_z(beta_ciq[m]))], extra=ex)]
        f_full = S.fm(dec, lambda m: des(m, True), ["ciq_z"], pb["kind"])
        f_base = S.fm(dec, lambda m: des(m, False), ["ciq_z"], pb["kind"])
        s_full = S.summarize(f_full["months"], f_full["g"]["ciq_z"], +1)
        s_base = S.summarize(f_base["months"], f_base["g"]["ciq_z"], +1)
        res["W04"] = {"fm": s_full, "repack": CQ.repack_flag(s_base["mean"], s_full["mean"])}
        ynext = {m: float(rng.normal(0.006, 0.04)) for m in dec}
        res["W04"]["ts"] = CQ.ts_measure(pb["kind"], dec, {m: -(wins.get(m, {}).get("d_last") or np.nan) for m in dec}, ynext)
        sc4 = {m: {t: float(b) for t, b in zip(pb["m"][m]["t"], beta_ciq[m])} for m in dec}
        bk4S = _books_from_scores(X, sc4.get, lambda m: CQ.THETA0)
        bk4C = _books_from_scores(X, sc4.get, lambda m: th_c[m])
        bk4B = _books_from_scores(X, lambda m: {t: float(b) for t, b in zip(pb["m"][m]["t"], pb["m"][m]["beta_fp"])}, lambda m: th_c[m])
        res["W04"]["books"] = (len(bk4S), len(bk4C), len(bk4B))
        res["W04"]["shuffle"] = [len(CQ.block_shuffle(dz, sorted(dz), CQ.BLOCK, seed + i)) for i in range(3)]
        res["W04"]["nagel"] = len(CQ.nagel_state({WC.mshift(h, -1): fac[h][0] for h in fac}, dec))
        res["W04"]["qfa_conv_share"] = float(np.mean([w["converged"] for m, w in wins.items() if m >= "2016-08"]))
        tm["W04"] = time.time() - t0
        _log("  W04 · %.0fs" % tm["W04"])
        # ── W10m ────────────────────────────────────────────────────────
        t0 = time.time()
        res["W10m"] = w10m_line(pb, months=dec)
        tm["W10m"] = time.time() - t0
        # ── W03(섹터 수익은 모두 잡음) ────────────────────────────────────
        t0 = time.time()
        hold_s, secs, R = PP.sector_returns(U, WC.months_between("2009-01", IP.LAST_DECISION), blind_seed=seed + 7)
        res["W03"] = {"pap": PP.primary("blind", hold_s, R), "diag": PP.primary("blind", hold_s, R, arm="diag"),
                      "pep_pap": PP.primary("blind", hold_s, R, arm="pep_pap"), "placebo": PP.placebo("blind", hold_s, R, 20, seed)["n"]}
        fr = VD.french("ind49", "vw_m")
        fr = fr.where(fr.isna(), rng.normal(0.008, 0.05, fr.shape))
        res["W03"]["l_twin"] = PP.l_twin("blind", fr)
        m3 = dec[-1]
        Xc = X[m3]
        jj = hold_s.index(m3) if m3 in hold_s else len(hold_s) - 2
        Sg = PP.signals_from_returns(R)
        Pi, idx3 = PP.pi_hat(R, Sg, jj)
        if Pi is not None:
            act = PP.sector_active(PP.positions(Pi, Sg[jj, idx3]))
            wpap, _ = PP.pap_book(act, [secs[i] for i in idx3], Xc.wB, Xc.sec, Xc.ndx, Xc.beta)
            res["W03"]["book_ok"] = bool(abs(wpap.sum() - 1) < 1e-9)
        tm["W03"] = time.time() - t0
        # ── W06 ─────────────────────────────────────────────────────────
        t0 = time.time()
        trig = vol_trigger(sp_daily())
        sch6 = w06_schedule(trig, ms_all)
        crosses = {}
        for m in ms_all:
            inp = {"members": U.members(m), "w_B": U.w_B(m), "me": U.me(m), "signals": U.signals(m, which=("mom12_2", "beta_fp", "month_ret")),
                   "irrx": {}, "ear": {}, "ch": {}, "ins": {}}
            Xv = VK.Cross(m, inp)
            m6 = [mom6_of(U, k, m) for k in Xv.k]
            Xv.mom6 = np.array([np.nan if v is None else v for v in m6], float)
            crosses[m] = Xv
        arms = v01_arms(crosses, ms_all, sch6)
        trig_ms = [m for m in dec if (trig.get(m) or {}).get("trig")]
        names6 = sorted({k for a in arms.values() for m in trig_ms for k in a.get(m, {})})
        nd6 = rng.normal(0, 0.012, (U.D, max(1, len(names6))))
        p6 = {nm: j for j, nm in enumerate(names6)}
        dret = lambda i: ({nm: float(nd6[i, p6[nm]]) for nm in names6} if i < U.D else None)
        ev = event_windows("blind", arms["W06"], arms["V01_S0"], {m: U.me_idx[m] for m in trig_ms}, dret)
        ev2 = event_windows("blind", arms["CTRL12"], arms["V01_S0"], {m: U.me_idx[m] for m in trig_ms}, dret)
        res["W06"] = {"n_trig_S": len(trig_ms), "n_events": len(ev), "n_ctrl": len(ev2), "arms": {a: len(b) for a, b in arms.items()}}
        tm["W06"] = time.time() - t0
        _log("  W06 · %.0fs" % tm["W06"])
        # ── W12 ─────────────────────────────────────────────────────────
        t0 = time.time()
        cal = fomc_calendar(fetch=False)
        fdays = set(cal["dates"])
        B = rolling_beta(DR, mkt_d)
        Yn = rng.normal(0, 0.015, DR.shape)
        Yn[~np.isfinite(DR)] = np.nan
        me_sorted = sorted(U.me_idx, key=lambda z: U.me_idx[z])
        me_pos = [U.me_idx[z] for z in me_sorted]
        di = [i for i, d in enumerate(U.dates) if FOMC_T1[0] <= d[:7] <= FOMC_T1[1]]
        import bisect
        memo = {}

        def last_me(i):
            j = bisect.bisect_left(me_pos, i) - 1
            return me_sorted[j] if j >= 0 else None

        def sec_of_day(i):
            m = last_me(i)
            if m is None:
                return None, None
            if m not in memo:
                mask = np.zeros(DR.shape[1], bool)
                sec = np.full(DR.shape[1], None, object)
                for r in U.members(m):
                    j = kcol.get(r["k"])
                    s_, _ = U.sector(r["t"], m, r["ndx_only"])
                    if j is not None and s_ is not None:
                        mask[j] = True
                        sec[j] = s_
                memo[m] = (mask, sec)
            return memo[m]
        g = daily_sml("blind", di, Yn, B, sec_of_day)
        res["W12"] = {"sml": fomc_slope_test("blind", g, lambda i: U.dates[i] in fdays), "n_fomc_T1": sum(1 for i in di if U.dates[i] in fdays)}
        spec2 = VK.spec_of("V02")
        bk2, prev2 = {}, None
        for m in [x for x in ms_all if x >= VK.S_ARM_FROM]:                  # V 의 첫 결정 달(2014-05 → 보유 2014-06)
            Xv = crosses[m]
            mask = VK.select(Xv, spec2, prev=prev2)
            w, _ = VK.target_book(Xv, spec2, mask, spec2["theta0"])
            if w is None:
                continue
            bk2[m] = (Xv.book(w), Xv.book(Xv.wB))
            prev2 = {Xv.t[i] for i in np.flatnonzero(mask)}
        fd_idx = [i for i in di if U.dates[i] in fdays]

        def active_of(i):
            m = last_me(i)
            if m not in bk2:
                return None
            b, wb = bk2[m]
            return {k: b.get(k, 0.0) - wb.get(k, 0.0) for k in set(b) | set(wb)}
        eff = fomc_step_effect("blind", fd_idx, active_of, lambda i: {t: float(rng.normal(0, 0.015)) for t in (active_of(i) or {})})
        pl = fomc_placebo_days([i for i in di if U.dates[i] not in fdays], len(fd_idx), 3, seed)
        res["W12"]["step"] = (len(eff), len(pl), len(bk2))
        tm["W12"] = time.time() - t0
        _log("  W12 · %.0fs" % tm["W12"])
        with open(os.path.join(out, "wb_cards_blind.pkl"), "wb") as f:
            pickle.dump({"res": res, "tm": tm}, f)
        # 모양 점검(개수만 · 값 없음) — 빈 결과가 조용히 지나가지 않게
        shape = {"W01_dec": (len(WS["dec"]), len(WCa["dec"])), "W01_fm_T": (res["W01"]["S"]["fm"]["T"], res["W01"]["C"]["fm"]["T"]),
                 "W01_struct_T": res["W01"]["structural"]["T"], "W01_twins": tuple(res["W01"]["twin_" + k] for k in ("K1", "UNRESTRICTED", "PIT_ONLY")),
                 "W01_books": res["W01"]["books"], "W01_tier2_n": (res["W01"]["tier2"]["n"], res["W01"]["tier2"]["n_down"]), "S1_months": res["S1"],
                 "W04_fm_T": res["W04"]["fm"]["T"], "W04_books": res["W04"]["books"], "W04_ts_T": res["W04"]["ts"]["T"], "W04_windows": len(wins),
                 "W10m_T": (res["W10m"]["interaction"]["T"], res["W10m"]["n_state"]), "W03_T": (res["W03"]["pap"]["n"], res["W03"]["l_twin"]["summary"]["T"]),
                 "W03_assets": res["W03"]["pap"]["n_assets"], "W06": (res["W06"]["n_trig_S"], res["W06"]["n_events"], res["W06"]["arms"]["W06"]),
                 "W12_days": len(g), "W12_fomc_T1": res["W12"]["n_fomc_T1"], "W12_sml_n_fomc": res["W12"]["sml"]["n_fomc"], "W12_step": res["W12"]["step"]}
        _log("  모양(개수만): %s" % json.dumps(shape, ensure_ascii=False))
        assert len(WS["dec"]) == len(dec) == 120 and len(WCa["dec"]) == 120 and min(shape["W01_fm_T"]) >= 115, shape
        assert shape["W01_struct_T"] >= 115 and min(shape["W01_twins"]) >= 90 and min(shape["W01_books"]) == 120 and shape["W01_tier2_n"] == (120, 35), shape
        assert shape["S1_months"] >= 20 and shape["W04_fm_T"] >= 110 and min(shape["W04_books"]) >= 110 and shape["W04_ts_T"] >= 110, shape
        assert shape["W10m_T"][0] >= 110 and shape["W03_T"][0] == 120 and shape["W03_T"][1] == 240 and res["W03"].get("book_ok") is True, shape
        assert shape["W06"][2] == len(ms_all) and shape["W06"][1] == shape["W06"][0], shape
        assert shape["W12_days"] >= 2900 and 90 <= shape["W12_fomc_T1"] <= 100 and shape["W12_sml_n_fomc"] >= 90, shape
        assert shape["W12_step"][0] == len(fd_idx) and shape["W12_step"][2] >= 140, shape
        return {"sec_by_card": {k: round(v, 1) for k, v in tm.items()}, "shape": shape}
    return run


def blind_smoke_main():
    """실자료 눈가린 연기 — 찍는 것: 참/거짓 · 시간 · 개수 · 모양 · G-NoEG 세 겹 · 얼린 모듈. 값(수익 · γ · t · IC)은 찍지 않는다(산출 파일은 열지 않고 지운다)."""
    import w_hygiene as H
    import w_ipca as IP
    WG.install_open_audit()
    probs = WC.env_problems()
    if probs:
        raise SystemExit("🚨 환경 핀: %s" % probs)
    fz = WC.frozen_check()
    if not fz["ok"]:
        raise SystemExit("🚨 얼린 V 모듈 핀 어긋남: %s" % fz["bad"])
    T0 = time.time()
    import w_panel as _WPN
    U = _WPN.real_universe()   # PN8 내부 가격 오버레이를 얹은 세계
    _log("우주 %.0fs · 격자 %d 일 · 가격 키 %d" % (time.time() - T0, U.D, len(U.PX)))
    keys = sorted(U.PX)
    kcol = {k: j for j, k in enumerate(keys)}
    DR = np.column_stack([U.daily_ret(k) for k in keys])
    months = [m for m in U.months if SMOKE_FROM <= m <= SMOKE_TO and WC.mshift(m, 1) in U.me_idx]
    mkt_d = IP.union_daily_market(U, [WC.mshift(months[0], -1)] + months, DR=DR, kcol=kcol)
    _log("일간 행렬 %s · 합집합 시장 · %.0fs" % (DR.shape, time.time() - T0))
    P, X = smoke_panel(U, months, DR, kcol, mkt_d)
    _log("패널 달 %d · 슬리브 단면 %d · %.0fs" % (len(P["months"]), len(X), time.time() - T0))
    r = H.blind_smoke(blind_run(U, X, DR, kcol, mkt_d, WC.SEED), P, WC.SEED)
    nr = WG.noeg_report()
    lf = WC.loaded_frozen_check()
    out = {"blind_smoke": {k: r[k] for k in ("ok", "sec", "n_files", "bytes", "deleted", "err", "returned")},
           "noeg": {"ok": nr["ok"], "static": nr["static"]["ok"], "runtime": nr["runtime"]["ok"], "open_audit": nr["open_audit"].get("ok"),
                    "n_opened": nr["open_audit"].get("n_opened"), "n_black": nr["open_audit"].get("n_black")},
           "loaded_frozen": lf["ok"], "frozen_pins": fz["ok"], "total_sec": round(time.time() - T0, 1)}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if (r["ok"] and nr["ok"] and lf["ok"]) else 1


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 자료만)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _fake_cross(seed, n=80, m="2020-01"):
    rng = np.random.default_rng(seed)
    secs = ["Financials" if i % 8 == 0 else "S%d" % (i % 5) for i in range(n)]
    me = np.exp(rng.normal(10, 1.0, n))
    ndx = np.zeros(n, bool)
    ndx[-3:] = True
    wB = np.where(ndx, 0.0, me)
    X = Cross(m, ["N%03d" % i for i in range(n)], me, wB, secs, ndx, rng.normal(1.0, 0.25, n), mom=rng.normal(0.1, 0.3, n))
    X.mom6 = rng.normal(0.05, 0.2, n)
    return X


def _st_sleeve():
    X = _fake_cross(WC.SEED)
    rng = np.random.default_rng(WC.SEED + 1)
    score = rng.normal(0, 1, X.n)
    mask = select_top(X, score)
    assert not (mask & X.fin).any() and mask.sum() == round(0.3 * int((~X.fin).sum()))
    wf = w_f_of(X, mask)
    assert np.allclose(wf[X.fin], X.wB[X.fin]) and abs(wf.sum() - 1) < 1e-12                       # B1 금융주 w_B
    w, info = sleeve_target(X, mask, 0.75)
    a = w - X.wB
    assert abs(w.sum() - 1) < 1e-12 and (w >= 0).all() and np.max(np.abs(a)) <= 0.05 + 1e-9
    secs = sorted(set(X.sec))
    assert all(abs(a[[i for i in range(X.n) if X.sec[i] == s]].sum()) <= 0.10 + 1e-9 for s in secs)
    assert w[X.ndx].sum() <= 0.10 + 1e-9 and abs(float(w @ X.beta - X.wB @ X.beta)) <= 0.03 + 1e-6
    w0, _ = sleeve_target(X, mask, 0.0)
    assert np.allclose(w0, X.wB, atol=1e-12)                                                     # θ = 0 → w_B
    assert _raises(lambda: sleeve_target(X, mask, 1.2))
    # 버퍼: 기존 이름은 1.5q 안이면 남는다
    prev = {X.t[i] for i in np.flatnonzero(mask)}
    score2 = score + rng.normal(0, 0.3, X.n)
    m_buf = select_top(X, score2, prev=prev)
    m_nob = select_top(X, score2, prev=prev, buffer=False)
    assert m_buf.sum() >= m_nob.sum() and len(prev & {X.t[i] for i in np.flatnonzero(m_buf)}) >= len(prev & {X.t[i] for i in np.flatnonzero(m_nob)})
    # 체결 · 회전 예산(B2)
    wd = X.book(X.wB)
    tgt = X.book(w)
    b1, tr1, sk1 = execute(wd, tgt)
    b2, tr2, sk2 = execute(wd, tgt, budget=0.02)
    assert sk1 == 0 and tr2 <= 0.02 + 1e-12 and sk2 > 0 and abs(sum(b2.values()) - 1) < 1e-12 and tr2 < tr1
    assert abs(TURN_BUDGET_MONTH * 12 / 2 - WC.TURN_MAX) < 1e-12
    return "선정(비금융 · q 0.3 · 버퍼 1.5q) · 금융주 능동 0 · 투영(발행사 0.05 · 섹터 0.10 · NDX 0.10) · β 띠 · θ=0 → w_B · θ ≤ 1 · 체결 · 회전 예산 건너뛰기"


def _st_w06():
    rng = np.random.default_rng(WC.SEED + 2)
    import datetime as dt
    days, d = [], dt.date(1993, 1, 4)
    while len(days) < 34 * 252:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += dt.timedelta(days=1)
    r = rng.normal(0.0004, 0.01, len(days))
    spike = [i for i, x in enumerate(days) if "2020-03-01" <= x <= "2020-03-31"]
    r[spike] = rng.normal(0, 0.05, len(spike))
    daily = dict(zip(days, r))
    tg = vol_trigger(daily)
    assert tg["2020-03"]["trig"] and tg["2020-03"]["delta"] > 1.0
    # 문턱은 t−1 까지(선견 없음) — 뒤 날짜를 흔들어도 앞 달 판정 그대로
    d2 = dict(daily)
    for x in days:
        if x >= "2021-01-01":
            d2[x] *= 5
    tg2 = vol_trigger(d2)
    assert all(tg2[m] == tg[m] for m in tg if m <= "2020-12")
    frac = np.mean([v["trig"] for v in tg.values() if v["thr"] is not None])
    assert 0.0 < frac < 0.10                                                                     # 95 백분위 문턱 → 약 5%
    ms = WC.months_between("2019-06", "2021-06")
    sch = w06_schedule(tg, ms)
    assert sch["2020-03"] and sch["2020-04"] and not sch["2020-06"]
    # V01 세 팔(frozen v_cards) — 발동이 없으면 셋이 같다 · 발동 달에 W06 팔만 6개월 점수
    cr = {m: _fake_cross(WC.SEED + 10 + i, m=m) for i, m in enumerate(ms)}
    arms0 = v01_arms(cr, ms, {m: False for m in ms})
    assert all(arms0["W06"][m] == arms0["V01_S0"][m] == arms0["CTRL12"][m] for m in ms)
    arms = v01_arms(cr, ms, sch)
    assert arms["W06"]["2020-03"] != arms["CTRL12"]["2020-03"] and arms["W06"]["2019-12"] == arms["V01_S0"]["2019-12"]
    VK = _VK()
    X6 = copy.copy(cr["2020-03"])
    X6.mom = cr["2020-03"].mom6
    m6 = VK.select(X6, dict(VK.spec_of("V01"), buffer=False), prev=None)
    top6 = {cr["2020-03"].t[i] for i in np.flatnonzero(m6)}
    held = {k for k in arms["W06"]["2020-03"] if arms["W06"]["2020-03"][k] > cr["2020-03"].wB[cr["2020-03"].pos[k]] + 1e-9}
    assert held <= top6                                                                          # 능동 양 이름은 6개월 상위 안
    # 사건 창(합성 수익)
    names = cr["2020-03"].t
    R = rng.normal(0, 0.01, (100, len(names)))
    ev = event_windows("synth", arms["W06"], arms["V01_S0"], {"2020-03": 10}, lambda i: {k: float(R[i, j]) for j, k in enumerate(names)} if i < 100 else None)
    assert set(ev["2020-03"]) == {21, 42}
    assert _raises(lambda: event_windows("real", arms["W06"], arms["V01_S0"], {"2020-03": 10}, lambda i: {}))
    return "발동(심은 급등 · 95 백분위 · 약 %.1f%%) · 문턱 선견 없음 · 두 결정 일정 · 세 팔 항등(발동 없음) · 6개월 재선정 · 사건 창 21 · 42" % (100 * frac)


def _st_w12():
    # 제목 해석(연준 쪽 실제 표기 꼴)
    cases = {"January 27-28 Meeting - 2015": "2015-01-28", "July 31-August 1  Meeting - 2012": "2012-08-01",
             "April/May 30-1 Meeting - 2013": "2013-05-01", "Jan/Feb 31-1 Meeting - 2017": "2017-02-01", "August 9 Meeting - 2011": "2011-08-09",
             "March  4 (unscheduled) - 2014": None, "August 1 Conference Call - 2011": None, "March 17-18 (cancelled) Meeting - 2020": None,
             "March 19 (notation vote) - 2020": None, "March 15 (unscheduled) Meeting - 2020": None}
    for k, v in cases.items():
        assert parse_fomc_heading(k) == v, (k, parse_fomc_heading(k), v)
    html = ('<a id="1">2026 FOMC Meetings</a> <div class="fomc-meeting__month x"><strong>January</strong></div>'
            '<div class="fomc-meeting__date y">27-28</div> <div class="fomc-meeting__month x"><strong>Apr/May</strong></div>'
            '<div class="fomc-meeting__date y">30-1*</div> <div class="fomc-meeting__month x"><strong>October</strong></div>'
            '<div class="fomc-meeting__date y">3 (unscheduled)</div> <div class="fomc-meeting__month x"><strong>July</strong></div>'
            '<div class="fomc-meeting__date y">28-29</div>')
    assert parse_fomc_current(html) == ["2026-01-28", "2026-05-01", "2026-07-29"]
    # 일간 SML — 심은 발표일 기울기 복원 · 누적합 β = 직접 OLS
    rng = np.random.default_rng(WC.SEED + 3)
    Dn, N = 900, 120
    mkt = rng.normal(0.0004, 0.01, Dn)
    beta = rng.normal(1.0, 0.3, N)
    DR = mkt[:, None] * beta[None, :] + rng.normal(0, 0.012, (Dn, N))
    DR[:50, 0] = np.nan
    B = rolling_beta(DR, mkt)
    d = 400
    x, y = mkt[d - 252:d], DR[d - 252:d, 5]
    ref = np.cov(y, x, ddof=0)[0, 1] / np.var(x)
    assert abs(B[d, 5] - ref) < 1e-9                                                             # B[d] = d−1 까지 252일(하루 늦춤)
    assert np.isnan(B[100, 3])                                                                    # 관측 < 200
    fomc = set(range(300, Dn, 30))
    Y = rng.normal(0, 0.01, (Dn, N)) + np.where(np.isin(np.arange(Dn), list(fomc))[:, None], 0.004 * np.nan_to_num(B), 0.0)
    sec = np.array(["S%d" % (i % 6) for i in range(N)], object)
    g = daily_sml("synth", range(260, Dn), Y, B, lambda dd: (np.ones(N, bool), sec))
    ft = fomc_slope_test("synth", g, lambda dd: dd in fomc)
    assert ft["t"] > 3 and ft["n_fomc"] == len([f for f in fomc if f >= 260]), ft
    eff = fomc_step_effect("synth", [10], lambda dd: {"a": 0.1, "b": -0.1}, lambda dd: {"a": 0.02, "b": -0.01})
    assert abs(eff[10] - (-(0.1 * 0.02 + 0.1 * 0.01) - 2 * COST * 0.2)) < 1e-15
    pl = fomc_placebo_days(range(1000), 98, 3, WC.SEED)
    assert len(pl) == 3 and all(len(p) == 98 and len(set(p)) == 98 for p in pl)
    assert _raises(lambda: daily_sml("real", [1], Y, B, lambda dd: (None, None))) and _raises(lambda: fomc_step_effect("real", [], None, None))
    return "연준 제목 해석(두 날 · 달 넘김 · 하루 · 비정례 · 전화 · 취소 · 서면 뺌) · 현재 쪽 · 누적합 β = OLS · 심은 발표일 기울기 t %.1f · 스텝 효과 식 · 위약 날" % ft["t"]


def _st_w10m():
    rng = np.random.default_rng(WC.SEED + 4)
    R = rng.standard_t(4, (63, 30)) * 0.01
    R[:20, 0] = np.nan
    ts = tail_shape(R)
    x = R[:, 3]
    assert abs(ts[3] - np.quantile(x, 0.1) / x.std(ddof=1)) < 1e-15 and np.isnan(ts[0])
    # 교차항 복원: γ_t(z) = 0.3·s_t + 잡음 가 되게 y 를 심는다(합성)
    ms = WC.months_between("2010-01", "2026-07")
    P = {"kind": "synth", "months": ms, "m": {}}
    for m in ms:
        n = 250
        D = {"tail": rng.normal(-1.5, 0.2 + 0.1 * rng.random(), n), "log_me": rng.normal(10, 1, n), "r1": rng.normal(0, 8, n), "mom": rng.normal(5, 20, n),
             "val": rng.normal(0, 1, n), "sec": np.array(["S%d" % (i % 6) for i in range(n)], object)}
        P["m"][m] = D
    iq = {m: float(np.quantile(P["m"][m]["tail"], 0.75) - np.quantile(P["m"][m]["tail"], 0.25)) for m in ms}
    st = iqr_state(iq, ms)
    for m in ms:
        s = st[m] if st[m] is not None else 0.0
        P["m"][m]["y"] = (0.8 * s) * xs_z(P["m"][m]["tail"]) + rng.normal(0, 4, 250)
    r = w10m_line(P, months=[m for m in ms if m >= "2011-01"])
    assert r["interaction"]["t"] > 4 and r["interaction"]["gamma1"] > 0, r["interaction"]
    assert iqr_state({"a": 1.0}, ["a"])["a"] is None
    assert _raises(lambda: w10m_line(dict(P, kind="real")))
    return "tail = Q0.10/σ(유효 ≥ 50) · IQR 확장 z · 심은 교차항 복원 t %.1f(S4 조건부 FM) · 실자료 자물쇠" % r["interaction"]["t"]


def _st_registry():
    assert set(CARDS) == {"W01", "W04", "W10m", "W03", "W06", "W12"} and "W13" not in CARDS and "W13" in WC.DROPPED
    assert WC.FORWARD_LEDGER is None and W06_THETA == "S0"
    for p in ("data/_wfwd/genesis.json",):
        assert _raises(lambda: WC.assert_no_forward([p]))
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    mods = set()
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Import):
            mods |= {a.name.split(".")[0] for a in nd.names}
        elif isinstance(nd, ast.ImportFrom) and nd.module:
            mods.add(nd.module.split(".")[0])
    assert not [m for m in mods if WG.forbidden(m)], mods
    assert not WG.check_units(CARDS_UNITS) and not WG.literal_scan(os.path.abspath(__file__))
    return "등록 A 카드 6(가족 A 셋 · 측정만 셋) · W13 뺌 · 전방 원장 없음 · W06 기준 = V01 정적(B3) · 금지 import 없음 · 입력 단위 · 문자열 상수"


def selftest():
    res, ok = [], True
    for fn in (_st_sleeve, _st_w06, _st_w12, _st_w10m, _st_registry):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-12s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_cards selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--fomc" in sys.argv:
        cal = fomc_calendar(fetch=True)
        print(json.dumps({"n": cal["n"], "by_year": cal["by_year"], "pages": len(cal["sha256"])}, ensure_ascii=False))
        raise SystemExit(0)
    if "--blind-smoke" in sys.argv:
        raise SystemExit(blind_smoke_main())
    print(__doc__)
