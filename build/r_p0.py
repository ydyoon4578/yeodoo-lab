# -*- coding: utf-8 -*-
"""build/r_p0.py — 배치 R 의 **P0 자격 계산기**(1차 자격 관문 · Holm 가족 크기 m) → data/_r_p0.json

근거: 배치 R 설계 batch_design_changes 1(P0 관문을 식으로 고정하고, 등록 전 F0 뒤에 계산한다) · data_build_plan §E.
원 계획이 R1·R2 에 적은 P0 0.15 는 계산에서 나온 값이 아니었다 — 그래서 식으로 고정한다.

  P0 = q·π + (1−q)·α₁
    q   = 0.4       효과가 이 창·대형주에서 살아 있을 사전 확률(모든 카드에 같다)
    α₁  = 0.0125    효과가 없을 때 1차 문턱(한쪽, Holm m=2 의 첫 칸 t(119) 2.27)을 넘을 확률
    π   = P(t ≥ 2.27 | γ_alt = 0.5·γ_lit, σ_plan) = 1 − Φ(2.27 − 0.5·|γ_lit|·√T / σ_plan)
    σ_plan = max(σ_analytic, σ_placebo)          (γ 월 계열의 SD · %/월)
      σ_analytic = 월별 «통제만» 횡단면 회귀의 잔차 SD × √(1/n1 + 1/n0) 을 제곱평균근으로 모은 값(n1 = 그달 플래그 수 ·
                   JT 카드는 (달 t, 시차 k) 마다 n1 = t−k 의 개수로 재서 함께 모은다)
      σ_placebo  = 매월 섹터 × 시총 3분위 칸에서 **실제 플래그의 칸별 개수만큼** 무작위 플래그를 뽑아 같은 회귀를 돌리기를
                   200회 → 회마다 γ 월 계열의 SD → 그 90분위. 🚨 위약 γ 의 평균은 저장하지도 찍지도 않는다.
                   🔒 JT 카드(R1)는 **시차마다 한 회귀** γ 계열의 SD 를 재고 회마다 k 에 걸쳐 제곱평균근으로 모은다(한 회귀 기준).
                   달마다 독립으로 뽑은 위약의 JT 평균 SD 는 한 회귀의 약 1/√3 로 줄어 분석적 σ(한 회귀 공식)와 견줄 수 없고,
                   그러면 칸 구조를 잡으려는 위약 쪽이 R1 에서 결코 묶이지 않는다 — 같은 것끼리 견주려고 한 회귀로 잰다
                   (보수적: 실제 JT 계열 SD ≤ 한 회귀 SD). JT 평균 SD 90분위는 진단(diag_jt_sd_p90)으로만 싣는다.
    T   = 커버리지 F0 를 넘은 신호월 가운데 카드가 쓰는 표지가 모든 시차에서 **정의된** 달이면서 주 표지 개수가 모든 시차에서
          1 이상인 달 수(주 창 2016-08..2026-07 = 보유 2016-09..2026-08 안). 표지 원천이 정의하지 않은 달(예: DERA 2026Q2 에서
          끝나는 cikmonth 의 2026-07)은 «0 개» 로 읽지 않는다 — 기본은 멈춤이고, --drop-undefined-months 로 빼기로 정해야 돈다
          (뺀 달은 문서에 남는다).
  🔒 P0 바닥(2026-09-26 등록 전 결정 · META-2 문헌 t 옮기기 — F0 전에 정했다):
    P0 = min(P0_σ, P0_lit) · P0_σ = 위 식(σ_plan 규칙) · P0_lit = q·π_lit + (1−q)·α₁ · π_lit = 1 − Φ(2.27 − t_alt_lit) ·
    t_alt_lit = 0.5 · t_lit · √(T / T_lit)(문헌 t 를 우리 달 수로 옮기고 발표 뒤 · 대형주 할인 0.5 를 건다). 입력(LIT · 검증 기록 포함):
    R1 = CMP «Decoding Inside Information» 표 IX 열 (2) 대형주 기회주의 매도 t 3.44 · 264개월 · R2 = Lazy Prices 표 A-15 Q1 5요인
    동일가중 t 2.22(가치가중 2.34 — 작은 쪽을 쓴다) · 240개월. T 는 σ 규칙과 같은 P0 카드 T.
  자격: P0 ≥ 0.15(⇔ π ≥ 0.35625 ⇔ t_alt ≥ 1.9016) · T ≥ 84 · 카드 밀도 F0(개수 · 정의된 관문 달 위에서) · 카드 외부 F0(R2 파서 §C ·
        연간 짝 ≥ 900 · 분리 실패 ≤ 20% — 입력으로 받는다). 달 관문(§F 가격 커버리지 · §A0 지도 위반율 ≤ 2%)은 T 를 정하는 달
        목록으로 받는다.
  Holm 가족 m = 자격 카드 수(0·1·2) — 등록 커밋에 고정하고, 등록 뒤 어떤 사건에도 바뀌지 않는다(R3 조건부 승격 없음).
    m 은 (가) 달 관문 목록이 있고 (나) CARDS 의 모든 카드에 개수 표가 있고 (다) 기본 관문을 넘은 카드의 외부 F0 가 모두 알려졌을 때만
    확정한다 — 하나라도 빠지면 m = None(미정). 카드는 «명시적으로 떨어진 관문» 으로만 가족에서 빠진다(파일이 없어서가 아니라).
    달을 빼면 P0 가 오르내릴 수 있으므로(중앙값·최소·σ 모두 단조가 아니다) 달 관문 없이는 0 도 확정하지 않는다.
  R2 경계 세계: 공개연도 Y 의 하위 20% 경계는 Y−1 에 공개된 세계 짝으로 정한다(r_r2flags.boundaries). 그래서 카운트 단계는
    개수 표의 달(2016-06..)과 따로 **SIG0 앞 해의 1월(2015-01)부터** 멤버 세계(member_world — 비금융 · 지도에서 푼 그룹 · FPI 제외 ·
    가격 무관)의 (그룹, 월) 집합을 경계 세계로 넘긴다. 정식 R2 자료가 있는데 경계 세계가 2015-01 보다 늦게 시작하면 멈춘다.
  2026-09-26: FPI 는 지도의 등록 표지(fpi_registered.tm_index · r_p0_adapt) · 지도 F0 위반 멤버-월은 두 세계(member_world · world_panel)
    에서 뺀다 — r_stagem.boundary_world · build_panel 과 같은 표본 규칙.
  2026-09-26(배치 R 등록 전 정렬 · 수익 없음): member_world 는 시점정확 GICS 섹터를 모르는 멤버를 **남긴다**(금융만 뺀다) —
    r_stagem.boundary_world · r_r2flags.members_from_im 과 같은 뜻. 전에는 섹터 모름을 빼서 경계 세계가 78 그룹-월(2015-01..2019-03 ·
    NDX 의 Liberty 계열 추적주 · CTRX · TFCF 등) 작았고 r_run --check-reg 가 두 세계의 크기 차이로 멈췄다.

🚨 방화벽 — 이 파일은 실제 플래그의 γ 를 계산하지 않는다.
  두 단계로 나눈다.
    counts : 세계(명단·시총·섹터)와 플래그 집합만 읽어 «월 × 칸별 개수 표» 를 쓴다. **수익을 읽지 않는다**(with_returns=False).
    run    : 세계(수익 포함)와 개수 표만 읽는다. 실제 플래그 파일을 읽으려 하면 r_p0_adapt.GUARD 가 멈춘다.
  위약 생성기(placebo_draws)는 칸 배정·개수 표·씨앗만 인자로 받는다 — 이름이 든 플래그를 받을 자리가 없다.
  run 이 계산하는 수익 관계는 «무작위 플래그 대 실제 수익» 뿐이고, 저장하는 것은 SD 뿐이다.

회귀(카드 Stage M 과 같은 꼴 — 월별 횡단면 OLS, FWL 로 통제를 먼저 빼고 더미 계수만 푼다).
  r_{i,t+1}(%) ~ 1 + log 시총 + log B/M(B/M ≤ 0·결측은 0 과 결측 더미) + r_t + r_{t−12..t−2} + GICS 섹터 더미 + 위약 더미들
  R1: 위약 OS_{t−k} + 위약 RS_{t−k}, k = 0,1,2 세 회귀의 계수 평균(JT) · R2: 위약 CH_t + 위약 CH_MISS_t(단일 회귀).
  실제 동반 더미(RS · 결측 더미)도 **자기 개수 표로 뽑은 위약**으로 바꾼다 — 실제 동반 플래그의 계수도 계산하지 않기 위해서다.

선언(한계).
  · 위약은 달마다 독립으로 뽑는다. 실제 플래그의 달 사이 지속(같은 회사가 연달아 켜짐)은 옮기지 않는다 — 평범한 SD 는
    거의 안 바뀌지만 JT 평균(R1)의 SD 는 조금 작게 나올 수 있다. 그래서 σ_plan 은 분석적 σ(단일 회귀 공식)와의 max 다.
  · π 는 정규 근사(§E 식 그대로)다. 비중심 t(nct) 값과 NW(3) 환산 σ 는 진단으로만 싣는다(관문에 쓰지 않는다).
  · n1 은 개수 표의 그달 합(칸 크기로 자름)이고, 회귀 행(통제가 선 이름)보다 큰 세계에서 센 것이다.
  · 시총 3분위는 그달 세계 전체의 log 시총 순위로 나눈다(섹터 안이 아니다) — 칸 = (섹터, 3분위).
  · 시차 위약: 달 t 의 k 달 전 위약은 t−k 세계(그 달 칸)에서 뽑아 같은 티커의 t−k 그룹으로 달 t 행에 잇는다. t−k 와 t 사이에
    지수에 들어온 이름은 위약이 늘 0 이고(실제 OS_{t−k} 는 1 일 수 있다), 떠난 이름에 떨어진 개수는 회귀에서 사라진다 — 월 교체
    1~3% · k ≤ 2 라 영향은 작다(실효 n1 이 조금 어긋남).
  · cikmonth 의 os_na/rs_na(자료 부족 N 행 · 선언 f)는 창 안에서 나오지 않는다(N 은 분류 첫해 2014 전뿐). 개수 표에 세계 안
    na 수를 싣고, 창 안에서 나오면 경고한다(Stage M 엔진은 거기에 _unk 통제를 넣는다 — 이 파일은 넣지 않는다).
  · σ 엔진이 둘이다(이 파일 · build/r_stagem.sigma_analytic/sigma_placebo) — 등록 전에 하나를 정해야 한다(보고서 참고).

  python build/r_p0.py closed                         # 닫힌 꼴 표(카드 문구의 1.58 · 2.30 · 1.32 · 1.93 · P0 예시 재현)
  python build/r_p0.py selftest                       # 합성 자료 끝에서 끝까지(실제 자료 없음)
  python build/r_p0.py panel-check --lab-root <판>    # 세계 패널 구성 점검 — 모양·결측·칸 크기만(수익 통계 없음)
  python build/r_p0.py counts --lab-root <판>         # 개수 표 → data/_r_p0_counts.json(수익을 읽지 않는다)
  python build/r_p0.py run --lab-root <판> --coverage <달 관문> --external-f0 f.json [--drop-undefined-months]
                                                      # P0 → data/_r_p0.json(등록 전에 커밋)
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, io, json, math, os, platform, subprocess, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as QC              # noqa: E402  SEED · FORM0 · HOLD1(배치 Q 틀과 같은 창)
import r_p0_adapt as AD               # noqa: E402  새 자료 필드 이름은 거기 한 곳

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(AD.DATA_R, "_r_p0.json")
COUNTS = os.path.join(AD.DATA_R, "_r_p0_counts.json")

# ── 고정 상수(batch_design_changes 1 · 등록 커밋에 얼린다) ──────────────────
Q_PRIOR = 0.4
ALPHA1 = 0.0125
T_CRIT = 2.27                 # t(119) 한쪽 0.0125 — Holm m=2 첫 칸(식에 상수로 둔다 · T 가 줄어도 바꾸지 않는다)
ALT_SCALE = 0.5               # γ_alt = 0.5 · γ_lit(발표 뒤·대형주 할인)
GATE = 0.15
T_MIN = 84                    # 남은 달 수가 이보다 적으면 R1·R2 모두 측정으로 내린다(§F)
HOLM_ALPHA = 0.025            # 한쪽 가족 수준 — m=2: 0.0125(2.27) → 0.025(1.98) · m=1: 0.025(1.98)
N_PLACEBO = 200
SD_PCT = 90
NW_LAG = 3
N_TERC = 3
SEED = QC.SEED                # 20260925 · 회 i 는 default_rng(SEED + i)(랩 위약 규약)
SIG0 = QC.FORM0               # 2016-08 첫 신호월
SIG1 = QC.mshift(QC.HOLD1, -1)  # 2026-07 끝 신호월(보유 2026-08)
FIN = "Financials"
KMAX = 2                      # JT 최대 시차(R1 k = 0..2)
BW0 = "%04d-01" % (int(SIG0[:4]) - 1)   # 2015-01 — R2 경계 세계의 첫 달(SIG0 해의 경계 = 전년도 분포)
IN_SHARE_MIN = 0.30           # 표지(그룹, 월) 가운데 세계 키에 맞는 몫이 이보다 작으면 키가 어긋났다고 보고 멈춘다
IN_SHARE_MIN_N = 20           # 그 점검을 거는 최소 표지 수(합성 소표본 제외)

CARDS = {
    "R1-OPPSELL": {"family": "insider", "gamma_lit": -0.55, "target": "OS", "companions": ["RS"], "lags": [0, 1, 2],
                   "lit": "CMP(2012) Table IX 열 (2) 전월 기회주의 매도 더미 −0.55%/월(t −3.44)",
                   "density_f0": [["OS", "median", 20], ["OS", "min", 5], ["RS", "median", 10]],
                   "external_f0": []},
    "R2-LAZYRF": {"family": "text", "gamma_lit": -0.80, "target": "CH", "companions": ["CH_MISS"], "lags": [0],
                  "lit": "Lazy Prices 표 A-15 동일가중 Q1 5요인 −0.80%/월(t −2.22)",
                  "density_f0": [["CH", "median", 30]],
                  "external_f0": ["parser_c_validation", "annual_pairs_ge_900", "split_fail_le_20pct"]},
}
# ── P0 바닥 — 문헌 t 옮기기(META-2 · 2026-09-26 등록 전 결정 · 등록 커밋에 얼린다) ─────────────────
# 쓰는 값은 t_lit · T_lit 둘뿐이다(나머지는 검증 기록). 🔒 T_lit 이 짧을수록 바닥이 높아진다(관대) — 모를 때는 긴 쪽(보수)을 쓴다.
LIT = {
    "R1-OPPSELL": {
        "t_lit": 3.44, "T_lit": 264,
        "source": "Cohen · Malloy · Pomorski, «Decoding Inside Information», NBER WP w16454(2010-10) 표 IX 열 (2) «Large Stocks» "
                  "Opportunistic Sell −0.55***(−3.44) · 풀링 회귀 · 달 고정효과 · 회사 군집 SE(JF 2012 게재판 쪽번호는 열어 보지 못했다)",
        "verified": {"t": "확인 — 로컬 NBER 판 본문(cmp.txt · 저장소 밖) 표 IX: −0.55***(−3.44) · 열 (2) = 시총 상위 절반(12월 시총)",
                     "months": "부분 확인 — 본문 «Form 4 filings for the period January, 1986 to December, 2007»(22년 = 264개월 · "
                               "«our entire 22 year sample»). 수익 검정 · 표는 3년 분류 이력 뒤 1989–2007(228개월)로 적힌 곳이 많다 "
                               "(표 II · Figure). 등록 입력은 선언대로 264(긴 쪽 · 보수 — 228 이면 t_alt_lit 가 √(264/228) = 1.076배)",
                     "stat_kind": "풀링 OLS t(회사 군집) — 우리 주 통계는 FM-NW(3) t(선언된 이탈 · 옮기기는 크기만 쓴다)"}},
    "R2-LAZYRF": {
        "t_lit": 2.22, "T_lit": 240, "t_lit_vw": 2.34,
        "source": "Cohen · Malloy · Nguyen, «Lazy Prices», NBER WP w25084(2018-09 · 2019-03 개정) 표 A-15 «Measuring Sequential "
                  "Quarterly Changes to the Risk Factors Section» Panel A 동일가중 Q1 5요인 알파 −0.80**(−2.22) · Panel B 가치가중 "
                  "−0.96**(−2.34)",
        "verified": {"t": "확인 — 로컬 NBER 판(%TEMP%/rbatch/lp.txt) 표 A-15: EW Q1 5요인 −0.80(−2.22) · VW −0.96(−2.34). "
                          "동일가중 t(작은 쪽 · 카드 γ_lit −0.80 과 같은 판)를 쓴다",
                     "months": "미확인 — 표 A-15 에 표본 기간이 적혀 있지 않다. 논문 표본은 1995–2014(240개월)이나 10-Q Part II Item 1A "
                               "위험요인은 2005 증권 공모 개혁(Release 33-8591 · 회계연도 2005-12-01 이후 10-K 부터) 뒤에야 있어 실제 "
                               "짝 표본은 대략 2006–2014(≤ 108개월)로 보인다. 등록 입력은 선언대로 240(긴 쪽 · 보수 — 108 이면 "
                               "t_alt_lit 가 √(240/108) = 1.49배)",
                     "stat_kind": "달력 시간 포트폴리오 5요인 알파 t(Q1 · 다음 달 진입 3개월 보유) — 우리 주 통계는 회귀 더미의 FM-NW(3) t"}},
}
P0_RULE = "P0 = min(P0_σ, P0_lit)"

NOT_P0 = {"R3-8KNE": "측정 전용(Holm 가족 밖 · 조건부 승격 없음) — P0 를 계산하지 않는다",
          "R5-ALARM": "표본 안에서 사건 수만 센다(전방 기록 팔) — P0 를 계산하지 않는다"}


# ════════════════════════════════════════════════════════════════════════
# 닫힌 꼴
# ════════════════════════════════════════════════════════════════════════
def _norm():
    from scipy.stats import norm
    return norm


def t_alt(gamma_lit, T, sigma, scale=ALT_SCALE):
    """대립 가설의 기대 t = scale·|γ_lit|·√T / σ(한쪽 H1 γ < 0 이므로 크기만 쓴다)."""
    return scale * abs(gamma_lit) * math.sqrt(T) / sigma


def power_pi(gamma_lit, T, sigma, crit=T_CRIT, scale=ALT_SCALE):
    """π = P(t ≥ crit | γ_alt, σ) = 1 − Φ(crit − t_alt) — §E 식(정규 근사)."""
    return float(_norm().sf(crit - t_alt(gamma_lit, T, sigma, scale)))


def power_pi_nct(gamma_lit, T, sigma, crit=T_CRIT, scale=ALT_SCALE):
    """진단 — γ_t 가 iid 정규일 때의 정확값: 비중심 t(df = T−1, nc = t_alt) 의 윗꼬리. 관문에 쓰지 않는다."""
    from scipy.stats import nct
    return float(nct.sf(crit, T - 1, t_alt(gamma_lit, T, sigma, scale)))


def p0_of_pi(pi, q=Q_PRIOR, a1=ALPHA1):
    return q * pi + (1.0 - q) * a1


def p0(gamma_lit, T, sigma):
    """σ 규칙 P0(바닥 전) — 카드 P0 는 p0_card(바닥 포함)."""
    return p0_of_pi(power_pi(gamma_lit, T, sigma))


def t_alt_lit(t_lit, T, T_lit, scale=ALT_SCALE):
    """META-2 문헌 t 옮기기 — t_alt_lit = scale · |t_lit| · √(T / T_lit)."""
    return scale * abs(t_lit) * math.sqrt(T / T_lit)


def p0_lit(code, T, lit=None):
    """문헌 규칙 P0 → (P0_lit, π_lit, t_alt_lit). lit = LIT(등록 입력) — 시험에서만 다른 값을 넘긴다."""
    L = (lit or LIT)[code]
    ta = t_alt_lit(L["t_lit"], T, L["T_lit"])
    pi = float(_norm().sf(T_CRIT - ta))
    return p0_of_pi(pi), pi, ta


def p0_card(code, gamma_lit, T, sigma, lit=None):
    """카드 P0(2026-09-26 바닥 포함) = min(σ 규칙 P0, 문헌 규칙 P0) → {p0, p0_sigma, p0_lit, pi, t_alt, pi_lit, t_alt_lit, binding}."""
    ta = t_alt(gamma_lit, T, sigma)
    pi = power_pi(gamma_lit, T, sigma)
    ps = p0_of_pi(pi)
    pl, pil, tal = p0_lit(code, T, lit)
    return {"p0": min(ps, pl), "p0_sigma": ps, "p0_lit": pl, "pi": pi, "t_alt": ta, "pi_lit": pil, "t_alt_lit": tal,
            "binding": "sigma" if ps <= pl else "lit"}


def T_needed_lit(code, gate=GATE, lit=None):
    """문헌 바닥이 관문을 넘는 데 필요한 T — t_alt_lit ≥ t_alt* ⇔ T ≥ T_lit · (t_alt* / (0.5·t_lit))²."""
    L = (lit or LIT)[code]
    return L["T_lit"] * (t_alt_needed(gate) / (ALT_SCALE * abs(L["t_lit"]))) ** 2


def pi_needed(gate=GATE, q=Q_PRIOR, a1=ALPHA1):
    """P0 ≥ gate ⇔ π ≥ (gate − (1−q)·α₁)/q."""
    return (gate - (1.0 - q) * a1) / q


def t_alt_needed(gate=GATE, crit=T_CRIT):
    """π ≥ π* ⇔ t_alt ≥ crit − Φ⁻¹(1 − π*)."""
    return crit - float(_norm().ppf(1.0 - pi_needed(gate)))


def sigma_max(gamma_lit, T, gate=GATE, scale=ALT_SCALE):
    """자격이 되는 σ_plan 의 최댓값 — σ* = scale·|γ_lit|·√T / t_alt*."""
    return scale * abs(gamma_lit) * math.sqrt(T) / t_alt_needed(gate)


def holm_crit(m, T, alpha=HOLM_ALPHA):
    """Holm 계단 임계(한쪽) — j = m, m−1, …, 1 에 t(1 − α/j, df = T−1). m=0 이면 빈 목록."""
    from scipy.stats import t as _t
    return [float(_t.ppf(1.0 - alpha / j, T - 1)) for j in range(m, 0, -1)]


def lrv_nw(x, lag=NW_LAG):
    """eg30plus.nw_t 와 같은 분산 — Bartlett 시차 lag · 분모 n. nw_t(x) = mean / √(lrv/n)."""
    x = np.asarray(x, float)
    n = len(x)
    e = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * (e[L:] @ e[:-L]) / n
    return float(s)


# ════════════════════════════════════════════════════════════════════════
# 패널 — 달마다 횡단면 한 벌(CS). 패널 공급자(세계·합성)가 바뀌어도 P0 핵심은 이 모양만 안다.
# ════════════════════════════════════════════════════════════════════════
class CS:
    """한 달 횡단면. keys(발행사 그룹 id 또는 티커) · cell(칸 번호) · y(r_{t+1} %, 없으면 None) · Z(통제, 절편 포함) · row(회귀 행 가면)."""

    def __init__(self, keys, cell, y=None, Z=None, row=None, lag_keys=None):
        self.keys = np.asarray(keys, dtype=object)
        self.cell = np.asarray(cell, dtype=np.int64)
        self.n = len(self.keys)
        self.pos = {k: j for j, k in enumerate(self.keys)}
        self.y, self.Z, self.row = y, Z, row
        self.lag_keys = lag_keys or {}   # {k: 같은 티커의 k 달 전 그룹 id} — 없으면 지금 키(r_stagem glag 와 같은 뜻)


class Panel:
    def __init__(self, xs, cell_labels, meta=None):
        self.xs = xs                           # {월: CS}
        self.months = sorted(xs)
        self.cell_labels = list(cell_labels)   # 칸 번호 → "섹터|3분위"
        self.meta = meta or {}


def assign_cells(sectors, mcap, label_ix, labels, n_terc=N_TERC):
    """그달 세계 전체 log 시총 순위로 3분위(0 = 작은 쪽) × 섹터 → 칸 번호. 같은 값은 키 순서(안정 정렬)."""
    mc = np.asarray(mcap, float)
    order = np.argsort(mc, kind="mergesort")
    rank = np.empty(len(mc), int)
    rank[order] = np.arange(len(mc))
    terc = np.minimum(n_terc - 1, (rank * n_terc) // max(1, len(mc)))
    out = []
    for s, q in zip(sectors, terc):
        lab = "%s|%d" % (s, q)
        if lab not in label_ix:
            label_ix[lab] = len(labels)
            labels.append(lab)
        out.append(label_ix[lab])
    return np.array(out, np.int64)


def universe_hash(panel):
    """세계·칸 배정의 지문 — 개수 표를 만든 세계와 P0 를 도는 세계가 같은지 본다."""
    h = hashlib.sha256()
    for m in panel.months:
        cs = panel.xs[m]
        h.update(m.encode())
        for k, c in sorted(zip(cs.keys.tolist(), cs.cell.tolist())):
            h.update(("%s:%s;" % (k, panel.cell_labels[c])).encode())
    return h.hexdigest()


# ════════════════════════════════════════════════════════════════════════
# 회귀 핵심 — FWL: 통제 Z 로 y 와 더미를 먼저 빼고 더미 계수만 푼다(전체 OLS 와 같은 값 · 시험 test_fwl)
# ════════════════════════════════════════════════════════════════════════
def basis(Z, tol=1e-9):
    """Z 열공간의 정규직교 기저(SVD · 계수 부족 열은 버린다) → (Q, rank)."""
    U, s, _ = np.linalg.svd(np.asarray(Z, float), full_matrices=False)
    r = int((s > tol * s[0]).sum()) if len(s) else 0
    return U[:, :r], r


def resid(Q, A):
    return A - Q @ (Q.T @ A)


def fwl_gamma(yt, Dt, Ct=None, tol=1e-10):
    """이미 통제를 뺀 ỹ(n,) · D̃(n,B) · C̃(n,B) 또는 None → 첫 더미 계수(B,). 첫 더미의 분산이 0 이면 NaN.
    동반 더미가 분산 0(개수 0 · 모든 이름을 덮음)이거나 첫 더미와 겹치면(공선) 동반 더미를 버리고 첫 더미만으로 푼다 —
    실제 회귀(r_stagem._solve: 플래그 순서대로 그람–슈미트 · 설명되는 열은 버림)와 같은 처리다."""
    a = np.einsum("ij,ij->j", Dt, Dt)
    e = Dt.T @ yt
    with np.errstate(invalid="ignore", divide="ignore"):
        g1 = np.where(a > tol, e / np.where(a > tol, a, 1.0), np.nan)
    if Ct is None:
        return g1
    b = np.einsum("ij,ij->j", Dt, Ct)
    c = np.einsum("ij,ij->j", Ct, Ct)
    f = Ct.T @ yt
    det = a * c - b * b
    full = (a > tol) & (c > tol) & (det > tol * np.maximum(a * c, 1e-300))
    with np.errstate(invalid="ignore", divide="ignore"):
        g = (c * e - b * f) / np.where(full, det, 1.0)
    return np.where(full, g, g1)


# ════════════════════════════════════════════════════════════════════════
# 위약 생성기 — 칸 배정 · 개수 표 · 씨앗만 받는다(실제 플래그를 받을 자리가 없다)
# ════════════════════════════════════════════════════════════════════════
def count_vec(counts_m, panel, cs):
    """{칸 이름: n} → 칸 번호 벡터(길이 = 칸 수). 칸 크기를 넘으면 자르고 모자란 수를 돌려준다."""
    L = len(panel.cell_labels)
    ix = {lab: j for j, lab in enumerate(panel.cell_labels)}
    want = np.zeros(L, np.int64)
    for lab, n in (counts_m or {}).items():
        if lab not in ix:
            raise SystemExit("🚨 개수 표의 칸 %r 이 세계에 없다 — 세계가 다르다" % lab)
        want[ix[lab]] = int(n)
    size = np.bincount(cs.cell, minlength=L)
    got = np.minimum(want, size)
    return got, int((want - got).sum())


def placebo_draws(panel, counts, months, dummies, B=N_PLACEBO, seed=SEED):
    """무작위 플래그 — 회 b 는 default_rng(seed + b) 하나로 달(오름차순) × 더미(주어진 순) 차례로 균등난수를 뽑고,
    달 s 의 칸 c 에서 난수가 가장 작은 counts[더미][s][c] 개 이름을 켠다(칸 안 비복원 균등 추출과 같다).
    반환 ({더미: {달: bool (B, n_s)}}, 칸 크기로 잘린 수)."""
    vecs, short = {}, 0
    for d in dummies:
        for s in months:
            v, sh = count_vec((counts.get(d) or {}).get(s), panel, panel.xs[s])
            vecs[(d, s)] = v
            short += sh
    out = {d: {s: np.zeros((B, panel.xs[s].n), bool) for s in months} for d in dummies}
    for b in range(B):
        rng = np.random.default_rng(seed + b)
        for s in months:
            cs = panel.xs[s]
            for d in dummies:
                u = rng.random(cs.n)
                order = np.lexsort((u, cs.cell))                        # 칸 순 → 칸 안 난수 순(정확 · 부동소수 겹침 없음)
                sc = cs.cell[order]
                start = np.searchsorted(sc, sc, side="left")
                rank = np.arange(cs.n) - start
                out[d][s][b, order] = rank < vecs[(d, s)][sc]
    return out, short


# ════════════════════════════════════════════════════════════════════════
# σ 두 가지
# ════════════════════════════════════════════════════════════════════════
def n1_of(panel, counts_d, s):
    v, _ = count_vec((counts_d or {}).get(s), panel, panel.xs[s])
    return int(v.sum())


def sigma_analytic(panel, counts_d, months, lags=(0,)):
    """월별 통제만 회귀의 잔차 SD s_t × √(1/n1 + 1/n0) → 제곱평균근. n1 = 개수 합(시차 k 면 t−k 의 개수) · n0 = 회귀 행 − n1.
    JT 카드는 (t, k) 마다 한 항 — 한 회귀의 표준오차 기준(위약 σ 와 같은 기준)."""
    se2, per = [], []
    for t in months:
        cs = panel.xs[t]
        r = cs.row
        y, Z = cs.y[r], cs.Z[r]
        Q, rk = basis(Z)
        e = resid(Q, y)
        n = len(y)
        s2 = float(e @ e) / max(1, n - rk)
        for k in lags:
            s = QC.mshift(t, -k)
            n1 = min(n1_of(panel, counts_d, s), n - 1)
            n0 = n - n1
            if n1 <= 0:
                per.append([t, k, n, n1, None])
                continue
            v = s2 * (1.0 / n1 + 1.0 / n0)
            se2.append(v)
            per.append([t, k, n, n1, round(math.sqrt(v), 6)])
    return (float(math.sqrt(np.mean(se2))) if se2 else None), per


def lag_index(cs, src, r, k):
    """달 t 의 회귀 행(r 가면) → 달 t−k 횡단면(src)의 자리(없으면 −1). 키는 같은 티커의 k 달 전 그룹(lag_keys) · 없으면 지금 키."""
    kk = np.asarray(cs.lag_keys[k], dtype=object)[r] if (k and k in cs.lag_keys) else cs.keys[r]
    return np.array([src.pos.get(x, -1) for x in kk], dtype=np.int64)


def placebo_gamma(panel, counts, card, months, B=N_PLACEBO, seed=SEED):
    """위약 γ 월 계열 — 카드와 같은 회귀(JT 시차 · 동반 더미). 반환 (G_jt (T, B), 잘린 수, {k: (T, B)} 시차별 한 회귀).
    JT 평균은 모든 시차의 계수가 있을 때만 낸다(하나라도 NaN 이면 그 달·회는 NaN — r_stagem.fm 의 «세 k 가 다 있는 달» 과 같다).
    돌려주는 것은 행렬뿐이고 저장은 부르는 쪽이 SD 만 한다."""
    lags = card["lags"]
    dums = [card["target"]] + list(card["companions"])
    need = sorted({QC.mshift(t, -k) for t in months for k in lags})
    miss = [s for s in need if s not in panel.xs]
    if miss:
        raise SystemExit("🚨 시차 달 %s 의 횡단면이 없다" % miss[:3])
    P, short = placebo_draws(panel, counts, need, dums, B=B, seed=seed)
    G = np.full((len(months), B), np.nan)
    Gk = {k: np.full((len(months), B), np.nan) for k in lags}   # 시차별 한 회귀(JT 카드의 σ_placebo 기준)
    for a, t in enumerate(months):
        cs = panel.xs[t]
        r = cs.row
        keys = cs.keys[r]
        Q, _ = basis(cs.Z[r])
        yt = resid(Q, cs.y[r])
        per_k = []
        for k in lags:
            s = QC.mshift(t, -k)
            src = panel.xs[s]
            idx = lag_index(cs, src, r, k)
            hit = idx >= 0
            def col(d):
                M = np.zeros((len(keys), B))
                M[hit] = P[d][s][:, idx[hit]].T
                return resid(Q, M)
            Dt = col(dums[0])
            Ct = col(dums[1]) if len(dums) > 1 else None
            if len(dums) > 2:
                raise SystemExit("🚨 동반 더미는 하나까지(fwl_gamma) — 카드 %s" % dums)
            per_k.append(fwl_gamma(yt, Dt, Ct))
        for k, gk in zip(lags, per_k):
            Gk[k][a] = gk
        G[a] = np.vstack(per_k).mean(0)                          # NaN 이 하나라도 있으면 NaN(모든 시차 필요)
    return G, short, Gk


def placebo_sigma(Gs):
    """회마다 γ 월 계열의 SD(ddof 1) → 90분위(선형 보간) · NW(3) 환산 σ = √lrv 의 90분위(진단). 평균은 돌려주지 않는다.
    Gs 가 행렬 목록(시차별 한 회귀)이면 회마다 목록에 걸친 SD 의 제곱평균근을 그 회의 SD 로 쓴다. 표본 달이 2 보다 적은
    계열이 있으면 그 회의 SD 는 NaN(부르는 쪽이 멈춘다)."""
    if isinstance(Gs, np.ndarray):
        Gs = [Gs]
    sd, nw, nnan = [], [], 0
    for b in range(Gs[0].shape[1]):
        v, w = [], []
        for G in Gs:
            x = G[:, b]
            x = x[~np.isnan(x)]
            nnan += int(G.shape[0] - len(x))
            v.append(float(np.std(x, ddof=1)) if len(x) >= 2 else float("nan"))
            w.append(lrv_nw(x) if len(x) >= 2 else float("nan"))
        sd.append(math.sqrt(float(np.mean(np.square(v)))))
        nw.append(math.sqrt(max(0.0, float(np.mean(w)))) if not any(x != x for x in w) else float("nan"))
    sd, nw = np.array(sd), np.array(nw)
    if np.isnan(sd).any():
        return {"sigma_placebo": float("nan"), "nan_sd_draws": int(np.isnan(sd).sum())}
    q = lambda a, p: float(np.percentile(a, p))
    return {"sigma_placebo": q(sd, SD_PCT),
            "sd_quantiles": {"p10": round(q(sd, 10), 6), "p50": round(q(sd, 50), 6), "p90": round(q(sd, 90), 6),
                             "min": round(float(sd.min()), 6), "max": round(float(sd.max()), 6)},
            "sd_each": [round(float(v), 6) for v in sd],
            "diag_nw3_sigma_p90": round(q(nw, SD_PCT), 6),
            "nan_month_draws": nnan}


# ════════════════════════════════════════════════════════════════════════
# 개수 표(카운트 단계) — 수익을 읽지 않는 세계 + 플래그 집합 → 월 × 칸 개수
# ════════════════════════════════════════════════════════════════════════
def counts_from_sets(panel, sets, months=None):
    """{월: set(키)} → ({월: {칸 이름: n}}(0 칸은 적지 않는다), 세계 밖 키 수, 표지 총수) — months(기본 패널 달) 안에서만 센다."""
    out, outside, total = {}, 0, 0
    for s in (panel.months if months is None else months):
        cs = panel.xs[s]
        fl = sets.get(s) or set()
        hit = [cs.pos[k] for k in fl if k in cs.pos]
        total += len(fl)
        outside += len(fl) - len(hit)
        if hit:
            bc = np.bincount(cs.cell[hit], minlength=len(panel.cell_labels))
            out[s] = {panel.cell_labels[j]: int(n) for j, n in enumerate(bc) if n}
    return out, outside, total


def panel_world(panel):
    return {(k, m) for m in panel.months for k in panel.xs[m].keys.tolist()}


def build_counts(panel, cards=CARDS, allow_provisional=False, allow_override=False, bworld=None):
    """카운트 단계 본체 — 🚨 panel 은 수익 없이 만든 것이어야 한다(y 가 None).
    출처가 provisional(어댑터 간이판)이나 override(덮어쓰기 파일)면 각각 allow_provisional · allow_override 없이는 멈춘다 —
    등록에 얼릴 개수는 정식 빌더의 것이어야 한다.
    bworld = R2 경계 분포의 세계 {(그룹, 월)} — BW0(2015-01) 부터여야 한다(없으면 패널 세계 · 정식 R2 자료가 있는데 짧으면 멈춘다).
    원천이 정의한 달(defined_months)을 카드·더미마다 싣고, 개수는 그 달 안에서만 센다(정의 밖 달을 «0 개» 로 만들지 않는다)."""
    if any(cs.y is not None for cs in panel.xs.values()):
        raise SystemExit("🚨 카운트 단계에 수익이 든 패널이 왔다")
    world = bworld if bworld is not None else panel_world(panel)
    wm = sorted({m for _, m in world})
    doc = {"kind": "r_p0_counts", "version": 2,
           "note": "배치 R P0 용 개수 표 — 월(가용월) × 칸(섹터|시총 3분위) 별 플래그 수. 이름이 없다. 수익을 읽지 않고 만들었다. "
                   "defined_months = 표지 원천이 정의한 달(그 밖의 달은 개수가 없는 것이지 0 이 아니다).",
           "generated": _now(), "cell_def": CELL_DEF, "universe": {"hash": universe_hash(panel),
           "months": [panel.months[0], panel.months[-1], len(panel.months)]}, "cells": panel.cell_labels,
           "r2_boundary_world": {"first": wm[0] if wm else None, "last": wm[-1] if wm else None, "n": len(world),
                                 "need_first": BW0, "ok": bool(wm and wm[0] <= BW0)},
           "panel_meta": panel.meta, "cards": {}}
    pset = set(panel.months)
    for code, c in cards.items():
        cd = {}
        for d in [c["target"]] + list(c["companions"]):
            fs = AD.flag_source(code, d, world=world, allow_provisional=allow_provisional)
            sets, src = fs["sets"], fs["src"]
            if src.startswith("provisional") and not allow_provisional:
                raise SystemExit("🚨 %s/%s 출처가 간이판(%s) — 정식 빌더 판을 쓰거나 --allow-provisional" % (code, d, src))
            if src.startswith("override"):
                if not allow_override:
                    raise SystemExit("🚨 %s/%s 출처가 덮어쓰기 파일(%s) — 정식 빌더를 가린다. 일부러 쓰려면 --allow-override" % (code, d, src))
                print("⚠ %s/%s 덮어쓰기 파일 출처(%s) — 등록 판이면 그 파일의 해시를 함께 얼릴 것" % (code, d, src))
            if sets is None:
                cd[d] = {"src": src, "months": None, "defined_months": None}
                continue
            if src.startswith("canonical") and AD.PROVIDER.get((code, d), "").startswith("tenq") and not doc["r2_boundary_world"]["ok"]:
                raise SystemExit("🚨 %s/%s — R2 경계 세계가 %s 부터다(필요 %s): 첫해 경계가 비어 CH 가 0 · 전부 결측이 된다"
                                 % (code, d, doc["r2_boundary_world"]["first"], BW0))
            dm = None if fs["defined"] is None else sorted(set(fs["defined"]) & pset)
            cm, outside, total = counts_from_sets(panel, sets, months=dm)
            share = (1.0 - outside / total) if total else None
            if total >= IN_SHARE_MIN_N and share < IN_SHARE_MIN:
                raise SystemExit("🚨 %s/%s — 표지 %d 건 가운데 세계 키에 맞는 몫 %.3f < %.2f: 그룹 키 모양이 어긋났다(예: int CIK 대 'g…')"
                                 % (code, d, total, share, IN_SHARE_MIN))
            na, dms = {}, (set(dm) if dm is not None else pset)
            for m, gs in (fs.get("na") or {}).items():
                if m not in dms:
                    continue
                n = sum(1 for g in gs if g in panel.xs[m].pos)
                if n:
                    na[m] = n
            if any(SIG0 <= m <= SIG1 for m in na):
                print("⚠ %s/%s — 창 안에 표지 모름(na) 행 %d 달(합 %d) · Stage M 엔진은 _unk 통제를 넣는다"
                      % (code, d, sum(1 for m in na if SIG0 <= m <= SIG1), sum(v for m, v in na.items() if SIG0 <= m <= SIG1)))
            cd[d] = {"src": src, "months": cm, "defined_months": dm, "outside_universe": outside, "flagged_total": total,
                     "in_universe_share": None if share is None else round(share, 6), "na_in_universe": na}
        doc["cards"][code] = cd
    return doc


def validate_counts(doc):
    """개수 표 방화벽 점검 — 잎은 모두 0 이상의 정수 · 이름(키 목록)이 없다 · defined_months 는 달 문자열 목록."""
    if doc.get("kind") != "r_p0_counts":
        raise SystemExit("🚨 개수 표가 아니다")
    for code, cd in (doc.get("cards") or {}).items():
        for d, rec in cd.items():
            dm = rec.get("defined_months")
            if dm is not None and not (isinstance(dm, list) and all(AD._is_ym(x) for x in dm)):
                raise SystemExit("🚨 %s/%s — defined_months 가 달 목록이 아니다" % (code, d))
            ms = rec.get("months")
            if ms is None:
                continue
            for m, byc in ms.items():
                if not isinstance(byc, dict):
                    raise SystemExit("🚨 %s/%s/%s — 칸별 개수 dict 가 아니다(이름 목록?)" % (code, d, m))
                for lab, n in byc.items():
                    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
                        raise SystemExit("🚨 %s/%s/%s/%s — 정수 개수가 아니다" % (code, d, m, lab))
    return True


# ════════════════════════════════════════════════════════════════════════
# 카드 평가 · 자격 · Holm
# ════════════════════════════════════════════════════════════════════════
def density_f0(panel, counts_card, card, months):
    out, ok = [], True
    for d, stat, lim in card["density_f0"]:
        v = [n1_of(panel, counts_card.get(d), t) for t in months]
        x = float(np.median(v)) if stat == "median" else float(np.min(v))
        p = x >= lim
        ok &= p
        out.append({"dummy": d, "stat": stat, "value": x, "min_req": lim, "pass": bool(p)})
    return bool(ok), out


def eval_card(panel, code, card, counts_card, months, B=N_PLACEBO, seed=SEED, dens_months=None):
    """카드 한 장의 P0. months = T 를 이루는 달(관문 · 정의 · 주 표지 ≥ 1) · dens_months = 밀도 F0 를 재는 달(관문 · 정의 · 기본 months)."""
    T = len(months)
    lags = card["lags"]
    sa, per = sigma_analytic(panel, counts_card.get(card["target"]), months, lags=lags)
    G, short, Gk = placebo_gamma(panel, counts_card, card, months, B=B, seed=seed)
    jt = len(lags) > 1
    ps = placebo_sigma([Gk[k] for k in lags] if jt else G)     # 🔒 JT 카드: 시차별 한 회귀 SD 의 제곱평균근(머리말)
    sp = ps["sigma_placebo"]
    if sp is None or sp != sp:
        raise SystemExit("🚨 %s — 위약 σ 가 NaN(표본 달이 2 보다 적은 회가 %s) — 달 목록을 확인하라" % (code, ps.get("nan_sd_draws")))
    if jt:                                                      # 진단 — JT 평균 계열 SD 90분위(달마다 독립 위약 → 약 1/√3 로 준다)
        d = placebo_sigma(G)
        ps["diag_jt_sd_p90"] = d["sd_quantiles"]["p90"] if "sd_quantiles" in d else None
        ps["diag_lag_sd_p90"] = {str(k): placebo_sigma(Gk[k])["sd_quantiles"]["p90"] for k in lags}
    del G, Gk                                                   # 위약 γ 행렬은 여기서 버린다(평균을 남기지 않는다)
    splan = max(sa, sp) if sa is not None else sp
    pc = p0_card(code, card["gamma_lit"], T, splan)                # 🔒 P0 = min(σ 규칙, 문헌 바닥) — 2026-09-26
    ta, pi, P0 = pc["t_alt"], pc["pi"], pc["p0"]
    dpass, dens = density_f0(panel, counts_card, card, dens_months if dens_months is not None else months)
    return {"status": "ok", "family": card["family"], "gamma_lit": card["gamma_lit"], "gamma_alt": ALT_SCALE * card["gamma_lit"],
            "lit": card["lit"], "lags": lags, "dummies": [card["target"]] + list(card["companions"]),
            "T": T, "months": [months[0], months[-1]] if months else None,
            "sigma_analytic": round(sa, 6) if sa is not None else None, "sigma_placebo": round(sp, 6),
            "sigma_placebo_basis": "시차별 한 회귀 SD 의 k 제곱평균근 → P%d" % SD_PCT if jt else "한 회귀 SD → P%d" % SD_PCT,
            "sigma_plan": round(splan, 6), "binding": "analytic" if (sa is not None and sa >= sp) else "placebo",
            "placebo": dict(ps, sigma_placebo=round(sp, 6), B=B, seed0=seed, pct=SD_PCT, capped_draws=short),
            "analytic_by_month": per,
            "t_alt": round(ta, 6), "pi": round(pi, 6), "pi_nct_diag": round(power_pi_nct(card["gamma_lit"], T, splan), 6),
            "p0_sigma": round(pc["p0_sigma"], 6), "lit_t": LIT[code]["t_lit"], "lit_T": LIT[code]["T_lit"],
            "t_alt_lit": round(pc["t_alt_lit"], 6), "pi_lit": round(pc["pi_lit"], 6), "p0_lit": round(pc["p0_lit"], 6),
            "p0_binding": pc["binding"], "T_needed_lit": round(T_needed_lit(code), 2),
            "p0": round(P0, 6), "sigma_max_for_gate": round(sigma_max(card["gamma_lit"], T), 6),
            "p0_pass": bool(P0 >= GATE), "T_pass": bool(T >= T_MIN),
            "density_f0": dens, "density_pass": dpass}


def decide(cards_out, external=None, months_final=True):
    """자격과 Holm m. m 은 다음이 모두 참일 때만 확정한다(아니면 m = None · pending_why 에 이유):
      (가) 달 관문 목록이 있다(months_final) — 달을 빼면 P0 가 어느 쪽으로도 움직일 수 있어 0 도 확정하지 않는다.
      (나) CARDS 의 모든 카드에 개수 표가 있다 — 자료가 없는 카드는 «떨어짐» 이 아니라 «미정» 이다.
      (다) 기본 관문(P0 · T · 밀도)을 넘은 카드의 외부 F0 가 모두 참/거짓으로 알려졌다.
    카드가 가족에서 빠지는 길은 명시적으로 떨어진 관문뿐이다."""
    external = external or {}
    elig, why = [], []
    if not months_final:
        why.append("달 관문 목록(§F 커버리지 · §A0 지도 F0) 없음 — T 가 잠정")
    for code in CARDS:
        r = cards_out.get(code)
        if r is None:
            why.append("카드 자료 없음: %s(평가 안 됨)" % code)
            continue
        if r.get("p0") is None and r.get("status") != "no_months":
            r["eligible"] = r["eligible_if_external_pass"] = False
            why.append("카드 자료 없음: %s(%s)" % (code, r.get("status") or "p0 없음"))
            continue
        ext = {k: (external.get(code) or {}).get(k) for k in CARDS[code]["external_f0"]}
        r["external_f0"] = ext
        known = all(v is not None for v in ext.values())
        base = bool(r.get("p0") is not None and r["p0_pass"] and r["T_pass"] and r["density_pass"])
        r["eligible"] = bool(base and known and all(ext.values()))
        r["eligible_if_external_pass"] = base
        if base and not known:
            why.append("카드 외부 F0 미확인: %s %s" % (code, [k for k, v in ext.items() if v is None]))
        if r["eligible"]:
            elig.append(code)
    fam = {}
    for code in elig:
        fam.setdefault(CARDS[code]["family"], []).append(code)
    clash = {f: v for f, v in fam.items() if len(v) > 1}
    if clash:
        raise SystemExit("🚨 같은 자료 가족에 1차 후보가 둘 — %s (규칙 2: 가족마다 하나)" % clash)
    pending = bool(why)
    m = None if pending else len(elig)
    Ts = [cards_out[c]["T"] for c in elig if cards_out[c].get("T")]
    Tm = min(Ts) if Ts else None
    prov = len([c for c, r in cards_out.items() if r.get("eligible_if_external_pass")])
    return {"m": m, "members": sorted(elig) if m is not None else None, "pending": pending, "pending_why": why,
            "m_if_external_pass": prov,
            "crit_t": [round(x, 4) for x in holm_crit(m, Tm)] if (m and Tm) else [],
            "crit_note": "한쪽 α 0.025 · t(T−1)(T = 구성원 T 의 최소) · T=120 이면 m=2: 2.27 → 1.98, m=1: 1.98(카드 문구와 같다)",
            "frozen_rule": "m 은 등록 커밋에 고정한다. 등록 뒤 어떤 사건에도 바뀌지 않는다."}


# ════════════════════════════════════════════════════════════════════════
# 실행(run) — 개수 표 + 세계 → 문서
# ════════════════════════════════════════════════════════════════════════
CELL_DEF = {"cell": "GICS 섹터(시점정확) × 시총 3분위(그달 세계 전체 log 시총 순위 · 0=작은 쪽)",
            "universe": "시점정확 S&P 500 ∪ NASDAQ 100(pit_panel.union_members) · 비금융(시점정확 GICS) · 시총이 선 이름 · "
                        "FPI(fpi=1) 제외 · 발행사 그룹마다 시총이 큰 한 종목 · 지도에서 못 푼 멤버-월 제외"}


def card_months(panel, card, cnt, defined, gate):
    """카드가 쓸 달 — gate(창 · 회귀 행 · 달 관문) 가운데
      undefined : 어느 더미·시차(t−k)가 원천이 정의하지 않은 달에 걸림(«0 개» 가 아니라 «모름»)
      zero_focal: 주 표지 개수가 어느 시차에서 0(그 달 γ 를 풀 수 없다 — 실제 회귀도 그 달을 버린다)
    반환 (T 달, 밀도 F0 달 = gate − undefined, undefined, zero_focal)."""
    dums = [card["target"]] + list(card["companions"])
    undef = [t for t in gate if any(QC.mshift(t, -k) not in defined[d] for d in dums for k in card["lags"])]
    us = set(undef)
    dens = [t for t in gate if t not in us]
    zero = [t for t in dens if any(n1_of(panel, cnt[card["target"]], QC.mshift(t, -k)) < 1 for k in card["lags"])]
    zs = set(zero)
    return [t for t in dens if t not in zs], dens, undef, zero


def run(panel, counts_doc, months_ok=None, B=N_PLACEBO, seed=SEED, external=None, allow_universe_drift=False,
        cards=CARDS, drop_undefined=False):
    """P0 단계. drop_undefined=False(기본)면 카드가 쓰는 표지가 원천이 정의하지 않은 달에 걸릴 때 멈춘다 —
    그 달을 빼기로 정하는 것은 부르는 쪽의 명시적 결정(--drop-undefined-months)이고 뺀 달은 문서에 남는다."""
    AD.GUARD["run"] = True                                       # 🚨 이 뒤로 실제 플래그 파일을 읽을 수 없다
    validate_counts(counts_doc)
    uh = universe_hash(panel)
    match = counts_doc.get("universe", {}).get("hash") == uh
    if not match and not allow_universe_drift:
        raise SystemExit("🚨 개수 표를 만든 세계와 지금 세계가 다르다(지문 불일치) — 같은 판으로 다시 세라")
    win = [m for m in panel.months if SIG0 <= m <= SIG1 and panel.xs[m].y is not None]
    reg = [m for m in win if int(panel.xs[m].row.sum()) >= 40]
    mo = None if months_ok is None else set(months_ok)
    months = [m for m in reg if (mo is None or m in mo)]
    regs = set(reg)
    out = {}
    for code, c in cards.items():
        cc = (counts_doc.get("cards") or {}).get(code) or {}
        dums = [c["target"]] + list(c["companions"])
        absent = [d for d in dums if (cc.get(d) or {}).get("months") is None]
        if absent:
            out[code] = {"p0": None, "status": "absent", "why": "자료 없음 — %s" % {d: (cc.get(d) or {}).get("src") for d in absent},
                         "T": None}
            continue
        undeclared = [d for d in dums if cc[d].get("defined_months") is None]
        if undeclared:
            raise SystemExit("🚨 %s/%s — 원천이 정의한 달(defined_months)을 모른다: 없는 달을 0 으로 읽게 된다. "
                             "r_p0_adapt.FIELDS 로 원천의 months_ok 를 찾게 하거나 덮어쓰기 파일에 months_ok 를 실어라" % (code, undeclared))
        cnt = {d: cc[d]["months"] for d in dums}
        defined = {d: set(cc[d]["defined_months"]) for d in dums}
        ms, dens, undef, zero = card_months(panel, c, cnt, defined, months)
        if undef and not drop_undefined:
            raise SystemExit("🚨 %s — 표지 원천이 정의하지 않은 달에 걸린 신호월 %d 개(%s…): «0 개» 로 읽지 않는다. "
                             "빼기로 정했으면 --drop-undefined-months(뺀 달은 문서에 남는다)" % (code, len(undef), undef[:3]))
        drop = {"window_no_rows": [m for m in win if m not in regs],
                "gate": [m for m in reg if mo is not None and m not in mo], "undefined": undef, "zero_focal": zero}
        if not ms:
            out[code] = {"p0": None, "status": "no_months", "why": "쓸 달 없음", "T": 0, "T_pass": False, "p0_pass": False,
                         "density_pass": False, "dropped": drop}
            continue
        out[code] = eval_card(panel, code, c, cnt, ms, B=B, seed=seed, dens_months=dens)
        out[code]["count_src"] = {d: cc[d].get("src") for d in dums}
        out[code]["dropped"] = drop
    holm = decide(out, external, months_final=months_ok is not None)
    doc = {"kind": "r_p0", "version": 2,
           "note": "배치 R 1차 자격(P0) — batch_design_changes 1 의 식 그대로. 실제 플래그의 γ 는 계산하지 않았다 "
                   "(개수 표만 읽음 · 위약은 무작위 플래그 대 실제 수익 · SD 만 저장).",
           "formula": "P0 = min(P0_σ, P0_lit) · P0_σ = q·π + (1−q)·α₁ · π = 1 − Φ(%.2f − %.1f·|γ_lit|·√T / σ_plan) · "
                      "σ_plan = max(σ_analytic, P%d(위약 SD)) · P0_lit = q·π_lit + (1−q)·α₁ · π_lit = 1 − Φ(%.2f − %.1f·t_lit·√(T/T_lit))"
                      % (T_CRIT, ALT_SCALE, SD_PCT, T_CRIT, ALT_SCALE),
           "constants": {"q": Q_PRIOR, "alpha1": ALPHA1, "t_crit": T_CRIT, "alt_scale": ALT_SCALE, "gate": GATE,
                         "pi_needed": round(pi_needed(), 6), "t_alt_needed": round(t_alt_needed(), 6), "T_min": T_MIN,
                         "B": B, "sd_pct": SD_PCT, "seed0": seed, "n_terc": N_TERC, "window": [SIG0, SIG1], "holm_alpha": HOLM_ALPHA,
                         "placebo_basis_jt": "JT 카드의 σ_placebo = 시차별 한 회귀 γ 계열 SD 의 k 제곱평균근 → P90(분석적 σ 와 같은 한 회귀 기준)",
                         "r2_boundary_world_from": BW0,
                         "p0_floor": {"rule": P0_RULE, "lit_scale": ALT_SCALE,
                                      "lit": {c: {"t_lit": v["t_lit"], "T_lit": v["T_lit"]} for c, v in sorted(LIT.items())}}},
           "window_decision": {"drop_undefined_months": bool(drop_undefined),
                               "undefined_dropped": {c: (r.get("dropped") or {}).get("undefined") for c, r in out.items()}},
           "cell_def": CELL_DEF,
           "universe": {"hash": uh, "match_counts": match, "months": [panel.months[0], panel.months[-1], len(panel.months)],
                        "n_median": float(np.median([panel.xs[m].n for m in months])) if months else None,
                        "rows_median": float(np.median([int(panel.xs[m].row.sum()) for m in months])) if months else None,
                        "coverage_f0": "given" if months_ok is not None else "absent — 전 달(잠정 · 등록 전에 §F 로 바꾼다)"},
           "cards": out, "not_p0": NOT_P0, "holm": holm,
           "firewall": {"real_flag_files_read_in_run": False, "placebo_mean_stored": False,
                        "inputs": "개수 표(월 × 칸 정수) · 세계(명단·시총·섹터·통제·수익) · 씨앗"},
           "panel_meta": panel.meta}
    doc["result_sha"] = hashlib.sha256(json.dumps({k: doc[k] for k in ("formula", "constants", "universe", "cards", "holm")},
                                                  ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return doc


# ════════════════════════════════════════════════════════════════════════
# 세계 패널(실자료) — eg30plus.World(시점정확 명단 · 날짜 인식 가격 키 · 시점정확 GICS) 위에서
# ════════════════════════════════════════════════════════════════════════
def member_world(W, imap, months):
    """R2 경계 분포의 세계 {(그룹, 월)} — 시점정확 S&P 500 ∪ NASDAQ 100 멤버 가운데 비금융(시점정확 GICS · 섹터를 모르면 남긴다 — 세기만) ·
    지도에서 푼 그룹 · FPI(fpi=1) 제외. 🔒 가격·시총은 묻지 않는다 — 경계는 «우리 세계» 의 전년도 분포이고 가격 커버리지는
    세계의 정의가 아니다(W.universe 와 pit_panel.union_members 는 가격 키·시총이 선 이름만 주므로 쓰지 않고 날것의 월말 명단
    W.W["lists"] 를 읽는다 · 2015 달은 가격 결측이 커서 시총을 요구하면 그룹 수가 약 ¼ 준다). 재배정 티커의 마지막 멤버월은
    union_members 처럼 뺀다. r_r2flags.dry(members_from_im)의 멤버 세계와 같은 뜻."""
    out, tally = set(), {"fin": 0, "nosec": 0, "unresolved": 0, "fpi": 0, "reassigned_last": 0, "members": 0}
    raw = getattr(W, "W", None)
    lists = raw.get("lists") if isinstance(raw, dict) else None
    reas = (raw.get("reassigned") or {}) if isinstance(raw, dict) else {}
    for s in months:
        if lists is None:                                           # 날것 명단이 없는 판 — 가격이 선 멤버로 물러선다(기록)
            if s not in W.me:
                continue
            mem = [(t, k) for t, k in W.universe(s, "union", ex_fin=False)]
            tally["fallback_priced"] = tally.get("fallback_priced", 0) + 1
        else:
            ts = set(lists["spx"].get(s) or []) | set(lists["ndx"].get(s) or [])
            mem = []
            for t in sorted(ts):
                if t in reas and s >= reas[t].get("last", "9999"):
                    tally["reassigned_last"] += 1
                    continue
                mem.append((t, None))
        tally["members"] += len(mem)
        for t, k in mem:
            sec = W.sector(t, k, s)
            if sec == FIN:
                tally["fin"] += 1
                continue
            if not sec or sec == "?":
                tally["nosec"] += 1                                     # 세기만 한다 — 섹터 모름은 남긴다(r_stagem.boundary_world 와 같다 · 2026-09-26 등록 전 정렬)
            if imap.ok:
                g = imap.get(t, s, k)
                if g is None or g["gid"] is None:
                    tally["unresolved"] += 1
                    continue
                if g["fpi"] == 1:
                    tally["fpi"] += 1
                    continue
                if getattr(imap, "violated", None) and imap.violated(t, s):   # 지도 F0 위반 멤버-월(r_stagem.boundary_world 와 같다 · 2026-09-26)
                    tally["im_viol"] = tally.get("im_viol", 0) + 1
                    continue
                out.add((g["gid"], s))
            else:
                out.add(("t:" + t, s))
    return out, tally


def world_panel(lab_root, months, with_returns=True, imap=None, bworld_months=None):
    """lab_root/build 의 eg30plus.World 를 읽어 달마다 CS 를 만든다(판 = 그 트리의 data/).
    with_returns=False 면 수익·통제를 만들지 않는다(카운트 단계 · 방화벽).
    bworld_months 를 주면 그 달들의 멤버 세계(member_world)를 panel.bworld 에 단다(R2 경계 세계 · 카운트 단계)."""
    sys.path.insert(0, os.path.join(lab_root, "build"))
    import eg30plus as E
    import stoploss as SL
    import tech_backtest as TB
    W = E.World()
    imap = imap if imap is not None else AD.IssuerMap()
    labels, lix = [], {}
    xs = {}
    tally = {"fin": 0, "nosec": 0, "unresolved": 0, "fpi": 0, "fpi_null": 0, "dup_group": 0, "no_next": 0,
             "miss_rt": 0, "miss_mom": 0, "bm_missing": 0, "fwd_zero": 0, "lag_key_changed": 0}
    secs_all = set()
    for s in months:
        if s not in W.me:
            continue
        i = W.me[s]
        best = {}
        for t, k in W.universe(s, "union", ex_fin=False):
            sec = W.sector(t, k, s)
            if sec == FIN:
                tally["fin"] += 1
                continue
            if not sec or sec == "?":
                tally["nosec"] += 1
                continue
            mc = W.mcap(t, k, i)
            if not mc:
                continue
            if imap.ok:
                g = imap.get(t, s, k)
                if g is None or g["gid"] is None:
                    tally["unresolved"] += 1
                    continue
                if g["fpi"] == 1:
                    tally["fpi"] += 1
                    continue
                if getattr(imap, "violated", None) and imap.violated(t, s):   # 지도 F0 위반 멤버-월(Stage M 표본과 같다 · 2026-09-26)
                    tally["im_viol"] = tally.get("im_viol", 0) + 1
                    continue
                if g["fpi"] is None:
                    tally["fpi_null"] += 1
                key = g["gid"]
            else:
                key = "t:" + t
            if key in best:
                tally["dup_group"] += 1
                if best[key][3] >= mc:
                    continue
            best[key] = (t, k, sec, mc)
        keys = sorted(best)
        if not keys:
            continue
        sec = [best[x][2] for x in keys]
        mc = [best[x][3] for x in keys]
        secs_all.update(sec)
        cell = assign_cells(sec, np.log(mc), lix, labels)
        lagk = {}
        if imap.ok:                                   # 같은 티커의 k 달 전 그룹(지주사 재편 등으로 그룹이 바뀐 달 · JT 시차용)
            for kk in range(1, KMAX + 1):
                sm = QC.mshift(s, -kk)
                lagk[kk] = [((imap.get(best[x][0], sm, best[x][1]) or {}).get("gid") or x) for x in keys]
                tally["lag_key_changed"] += sum(1 for a_, b_ in zip(lagk[kk], keys) if a_ != b_)
        cs = CS(keys, cell, lag_keys=lagk)
        if with_returns:
            i1 = W.me.get(QC.mshift(s, 1))
            ia, ib, ic = W.me.get(QC.mshift(s, -1)), W.me.get(QC.mshift(s, -13)), W.me.get(QC.mshift(s, -2))
            y = np.full(len(keys), np.nan)
            X = np.full((len(keys), 5), np.nan)
            for j, x in enumerate(keys):
                t, k, _, m_ = best[x]
                p = W.PX[k]
                if i1 is not None:
                    seg = p[i + 1:i1 + 1]
                    ok = np.where(seg == seg)[0]
                    if len(ok):
                        y[j] = 100.0 * (seg[ok[-1]] / p[i] - 1.0)
                    else:
                        y[j] = 0.0                               # pit_panel.month_rows 규약(이후 가격이 없으면 0)
                        tally["fwd_zero"] += 1
                pa = SL.last_valid(p, ia, max(0, ia - 5)) if ia is not None else None
                rt = (p[i] / pa - 1.0) if pa else np.nan
                p13 = SL.last_valid(p, ib, max(0, ib - 5)) if ib is not None else None
                p2 = SL.last_valid(p, ic, max(0, ic - 5)) if ic is not None else None
                mom = (p2 / p13 - 1.0) if (p13 and p2) else np.nan
                f = W.fund(t, k)
                eq = TB.asof_all(f.get("eq") or [], W.dates[i]) if f.get("eq") else None
                bmv = eq[0][1] if (eq and eq[0][1] is not None) else None
                if bmv is not None and bmv > 0:
                    lbm, bmm = math.log(bmv / m_), 0.0
                else:
                    lbm, bmm = 0.0, 1.0
                    tally["bm_missing"] += 1
                X[j] = [math.log(m_), lbm, bmm, rt, mom]
                tally["miss_rt"] += int(rt != rt)
                tally["miss_mom"] += int(mom != mom)
            row = ~np.isnan(y) & ~np.isnan(X).any(1)
            if i1 is None:
                tally["no_next"] += 1
                row[:] = False
            cs.y, cs.row = y, row
            cs._X, cs._sec = X, sec
        xs[s] = cs
    if with_returns:
        order = sorted(secs_all)
        for s, cs in xs.items():
            D = np.array([[1.0 if cs._sec[j] == q else 0.0 for q in order[1:]] for j in range(cs.n)]).reshape(cs.n, -1)
            X = np.where(np.isnan(cs._X), 0.0, cs._X)
            cs.Z = np.hstack([np.ones((cs.n, 1)), X, D])
            del cs._X, cs._sec
    meta = {"lab_root": os.path.abspath(lab_root), "lab_head": _git(lab_root, "rev-parse", "HEAD"),
            "lab_dirty": bool(_git(lab_root, "status", "--porcelain", "--", "data/stocks.json", "data/pit_px.json",
                                   "data/pit_gics_sectors.json", "data/index_history.json")),
            "lab_build_status": (_git(lab_root, "status", "--porcelain", "--", "build/") or "").splitlines(),
            "modules": module_provenance([lab_root, ROOT]),
            "issuer_map_sha256": _sha_lf(imap.path) if (imap.ok and os.path.exists(imap.path)) else None,
            "last_date": W.dates[-1], "issuer_map": imap.ok, "tally": tally, "sectors": sorted(secs_all),
            "with_returns": with_returns}
    P = Panel(xs, labels, meta)
    if bworld_months is not None:
        P.bworld, bt = member_world(W, imap, bworld_months)
        meta["bworld_tally"] = bt
    return P


def module_provenance(roots):
    """세계·통제를 만든 모듈의 출처 — 지금 import 된 모듈 가운데 roots/build 아래 파일의 (경로, sha256 LF). lab_head 만으로는
    판(snap_wt)의 고친·더한 build 파일을 가리지 못한다."""
    bases = [os.path.normcase(os.path.abspath(os.path.join(r, "build"))) for r in roots]
    out = {}
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f or not f.endswith(".py"):
            continue
        fa = os.path.normcase(os.path.abspath(f))
        if any(fa.startswith(b + os.sep) for b in bases) and os.path.exists(f):
            out[name] = {"file": os.path.abspath(f), "sha256": _sha_lf(f)}
    return out


# ════════════════════════════════════════════════════════════════════════
# 합성 자료(시험 · selftest 전용)
# ════════════════════════════════════════════════════════════════════════
def synth_panel(seed=7, n_names=450, months=None, n_sec=10, churn=0.01, vol=8.0, sec_vol=3.0,
                cell_shock=0.0, shock_cell=("S0", 2), with_returns=True):
    """합성 세계 — 지속 키(달마다 churn 만큼 교체) · 고정 섹터 · log 시총 랜덤워크 · r_{t+1} = 섹터 충격 + 개별 잡음(%).
    cell_shock > 0 이면 shock_cell(섹터, 3분위) 이름에만 달마다 공통 충격을 더한다(선형 통제로 흡수되지 않는 칸 구조)."""
    rng = np.random.default_rng(seed)
    months = months or QC.months_between(QC.mshift(SIG0, -14), SIG1)
    nxt = n_names
    ids = ["s%04d" % j for j in range(n_names)]
    sec = {x: "S%d" % rng.integers(n_sec) for x in ids}
    lmc = {x: rng.normal(10.0, 1.0) for x in ids}
    bm = {x: rng.normal(-1.0, 0.7) for x in ids}
    hist = {x: [] for x in ids}
    labels, lix, xs = [], {}, {}
    for s in months:
        if churn:
            out_ = [x for x in ids if rng.random() < churn]
            for x in out_:
                ids.remove(x)
                nw = "s%04d" % nxt
                nxt += 1
                ids.append(nw)
                sec[nw] = "S%d" % rng.integers(n_sec)
                lmc[nw], bm[nw], hist[nw] = rng.normal(9.5, 0.8), rng.normal(-1.0, 0.7), []
        keys = sorted(ids)
        cell = assign_cells([sec[x] for x in keys], [lmc[x] for x in keys], lix, labels)
        cs = CS(keys, cell)
        f = {q: rng.normal(0, sec_vol) for q in sorted({sec[x] for x in keys})}   # 정렬 — 해시 씨앗에 따라 갈리지 않게
        shock = rng.normal(0, cell_shock) if cell_shock else 0.0
        lab_sh = "%s|%d" % shock_cell
        y = np.array([f[sec[x]] + rng.normal(0, vol) + (shock if labels[c] == lab_sh else 0.0)
                      for x, c in zip(keys, cell)])
        if with_returns:
            rt = np.array([hist[x][-1] if hist[x] else np.nan for x in keys])
            mom = np.array([np.sum(hist[x][-12:-1]) if len(hist[x]) >= 12 else np.nan for x in keys])
            X = np.column_stack([[lmc[x] for x in keys], [bm[x] for x in keys], np.zeros(len(keys)), rt, mom])
            row = ~np.isnan(X).any(1)
            secs = sorted(f)
            D = np.array([[1.0 if sec[x] == q else 0.0 for q in secs[1:]] for x in keys])
            cs.y, cs.row = y, row
            cs.Z = np.hstack([np.ones((len(keys), 1)), np.where(np.isnan(X), 0.0, X), D])
        xs[s] = cs
        for x, v in zip(keys, y):                               # 다음 달 r_t · 모멘텀용 이력(r_{t+1} 이 다음 달의 r_t)
            hist[x].append(v)
            lmc[x] += v / 100.0
    return Panel(xs, labels, {"synthetic": True, "seed": seed, "cell_shock": cell_shock, "with_returns": with_returns})


def synth_counts_doc(panel, rate=None, bias_cell=None, bias=4.0, seed=11):
    """합성 개수 표 — 카드 더미마다 칸별 이항 개수(합성 «플래그» 는 만들지 않는다 · 이름 없음)."""
    rng = np.random.default_rng(seed)
    rate = rate or {"OS": 0.08, "RS": 0.04, "CH": 0.12, "CH_MISS": 0.03}
    cards = {}
    for code, c in CARDS.items():
        cd = {}
        for d in [c["target"]] + list(c["companions"]):
            ms = {}
            for s in panel.months:
                cs = panel.xs[s]
                size = np.bincount(cs.cell, minlength=len(panel.cell_labels))
                byc = {}
                for j, n in enumerate(size):
                    if not n:
                        continue
                    p = rate[d] * (bias if (bias_cell and panel.cell_labels[j] == bias_cell) else 1.0)
                    k = int(rng.binomial(n, min(0.9, p)))
                    if k:
                        byc[panel.cell_labels[j]] = k
                ms[s] = byc
            cd[d] = {"src": "synthetic", "months": ms, "defined_months": list(panel.months)}
        cards[code] = cd
    return {"kind": "r_p0_counts", "version": 2, "generated": _now(), "cell_def": CELL_DEF,
            "universe": {"hash": universe_hash(panel)}, "cells": panel.cell_labels, "cards": cards}


# ════════════════════════════════════════════════════════════════════════
# 도우미 · 명령
# ════════════════════════════════════════════════════════════════════════
def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(root, *a):
    try:
        return subprocess.run(["git", "-C", root] + list(a), capture_output=True, text=True).stdout.strip()
    except Exception:
        return None


def _sha_lf(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def _wj(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def _env():
    import scipy
    return {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"), "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS")}


def closed_table():
    """카드 문구의 수치를 식에서 다시 낸다(등록 문서에 그대로 옮길 표)."""
    rows = {"pi_needed": pi_needed(), "t_alt_needed": t_alt_needed(), "holm_T120": {m: holm_crit(m, 120) for m in (1, 2)}}
    for code, c in CARDS.items():
        rows[code] = {"sigma_max_T120": sigma_max(c["gamma_lit"], 120), "sigma_max_T84": sigma_max(c["gamma_lit"], 84),
                      "p0_sigma_T120": {s: p0(c["gamma_lit"], 120, s) for s in (1.2, 1.8, 2.4)},
                      "p0_lit_T84": p0_lit(code, 84)[0], "p0_lit_T120": p0_lit(code, 120)[0],
                      "t_alt_lit_T84": p0_lit(code, 84)[2], "t_alt_lit_T120": p0_lit(code, 120)[2],
                      "T_needed_lit_for_gate": T_needed_lit(code),
                      "p0_card_T120": {s: p0_card(code, c["gamma_lit"], 120, s)["p0"] for s in (1.2, 1.8, 2.4)},
                      "lit": LIT[code]}
    return rows


def _months_all():
    """패널 달 — 첫 신호월의 JT 시차(−2)부터 끝 신호월까지."""
    return QC.months_between(QC.mshift(SIG0, -max(max(c["lags"]) for c in CARDS.values())), SIG1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="배치 R P0 자격 계산기")
    ap.add_argument("cmd", choices=["closed", "selftest", "panel-check", "counts", "run"])
    ap.add_argument("--lab-root", default=os.environ.get("R_LAB_ROOT") or ROOT, help="세계 판(가격을 읽는 트리)")
    ap.add_argument("--counts", default=COUNTS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--B", type=int, default=N_PLACEBO)
    ap.add_argument("--external-f0", default=None, help='{"R2-LAZYRF": {"parser_c_validation": true, "annual_pairs_ge_900": true, "split_fail_le_20pct": true}}')
    ap.add_argument("--allow-provisional", action="store_true", help="개수 표에 어댑터 간이판 표지를 허용(개발용 · 등록 불가)")
    ap.add_argument("--allow-override", action="store_true", help="덮어쓰기 파일(FIELDS['flags_override'])을 표지 출처로 허용")
    ap.add_argument("--drop-undefined-months", action="store_true",
                    help="표지 원천이 정의하지 않은 달에 걸린 신호월을 빼기로 정한다(기본은 멈춤 · 뺀 달은 문서에 남는다)")
    ap.add_argument("--seed", type=int, default=SEED, help="위약 씨앗(회 b = default_rng(seed + b)) — 등록 커밋에서 하나로 고정")
    ap.add_argument("--coverage", default=None, help="달 관문 파일(months_ok 목록 또는 r_stagem --construct 산출물)")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.cmd == "closed":
        print(json.dumps(closed_table(), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "selftest":
        P = synth_panel()
        C = synth_counts_doc(P)
        doc = run(P, C, B=a.B, seed=a.seed)
        AD.GUARD["run"] = False
        doc["env"], doc["code"] = _env(), {n: _sha_lf(os.path.join(HERE, n)) for n in ("r_p0.py", "r_p0_adapt.py")}
        out = a.out or os.path.join(os.environ.get("TEMP", "."), "r_p0_selftest.json")
        _wj(out, doc)
        for code, r in doc["cards"].items():
            print("%s  T %d · σ_an %.3f · σ_pl %.3f(%s) · π %.3f · P0 %.3f · 자격(외부 F0 제외) %s"
                  % (code, r["T"], r["sigma_analytic"], r["sigma_placebo"], r["binding"], r["pi"], r["p0"],
                     r["eligible_if_external_pass"]))
        print("합성 → %s · m %s(미정 이유 %s) · result_sha %s · %.1fs" % (out, doc["holm"]["m"], doc["holm"]["pending_why"],
                                                                     doc["result_sha"][:16], time.time() - t0))
        return 0
    months = _months_all()
    if a.cmd == "panel-check":
        P = world_panel(a.lab_root, months, with_returns=True)
        rows = [int(P.xs[m].row.sum()) for m in P.months if SIG0 <= m <= SIG1]
        size = [int(np.bincount(P.xs[m].cell).max()) for m in P.months]
        print(json.dumps({"months": [P.months[0], P.months[-1], len(P.months)], "n_median": float(np.median([P.xs[m].n for m in P.months])),
                          "rows_median": float(np.median(rows)), "rows_min": min(rows), "cells": len(P.cell_labels),
                          "cell_max_median": float(np.median(size)), "universe_hash": universe_hash(P), "meta": P.meta},
                         ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "counts":
        P = world_panel(a.lab_root, months, with_returns=False, bworld_months=QC.months_between(min(BW0, months[0]), months[-1]))
        doc = build_counts(P, allow_provisional=a.allow_provisional, allow_override=a.allow_override, bworld=P.bworld)
        doc["r2_boundary_world"]["rule"] = "멤버 세계(member_world) — 비금융 · 지도에서 푼 그룹 · FPI 제외 · 가격 무관"
        doc["provisional_allowed"] = bool(a.allow_provisional)
        doc["override_allowed"] = bool(a.allow_override)
        doc["sources"] = {k: v for k, v in AD.status().items()}
        doc["code"] = {n: _sha_lf(os.path.join(HERE, n)) for n in ("r_p0.py", "r_p0_adapt.py")}
        _wj(a.out or a.counts, doc)
        print("개수 표 → %s · %s · %.1fs" % (a.out or a.counts,
              {c: {d: (v["src"], None if v["months"] is None else len(v["months"])) for d, v in cd.items()}
               for c, cd in doc["cards"].items()}, time.time() - t0))
        return 0
    if a.cmd == "run":
        with io.open(a.counts, encoding="utf-8") as f:
            C = json.load(f)
        ext = None
        if a.external_f0:
            with io.open(a.external_f0, encoding="utf-8") as f:
                ext = json.load(f)
        cov, cov_src = AD.month_gate(a.coverage)
        AD.GUARD["run"] = True
        P = world_panel(a.lab_root, months, with_returns=True)
        doc = run(P, C, months_ok=cov, B=a.B, seed=a.seed, external=ext, drop_undefined=a.drop_undefined_months)
        doc["env"] = _env()
        doc["code"] = {n: _sha_lf(os.path.join(HERE, n)) for n in ("r_p0.py", "r_p0_adapt.py")}
        doc["inputs"] = {"counts": {"path": a.counts, "sha256": _sha_lf(a.counts)},
                         "month_gate": cov_src, "external_f0": a.external_f0,
                         "external_f0_sha256": _sha_lf(a.external_f0) if a.external_f0 else None}
        _wj(a.out or OUT, doc)
        print("P0 → %s · m %s · %.1fs" % (a.out or OUT, doc["holm"]["m"], time.time() - t0))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
