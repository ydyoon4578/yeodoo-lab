# -*- coding: utf-8 -*-
"""build/w_frag.py — 배치 W 등록 B · W11 FRAG(13F 보유 집중 취약성 · 신용 스트레스 상승 중에만 비중 축소): SEC 13F 자료집 → 운용사 × 종목 보유 행렬 ·
CUSIP → 발행사 그룹(FTD 기호 · §A0 날짜 인식 지도) · 취약성 F_i = Σ_k A_{k,i}² · X_i 쌍둥이 · 스트레스 상승 강도 s_t(BAA10Y) · 방어 책 · 대조 ·
F0(13F 시작 · 보유자 커버리지 · CUSIP 연결률 · 스위치 활성 — 개수만).

설계 원본(구속): wbatch_research.json final.slate.strategies[W11] · common_frame(tier1_world «W11 보유 행렬은 금융 포함» · G_NoEG_inputs «sh · sho 는 13F 보유
  비율의 분모로만» · no_derivatives) · evaluation.controls(시계열 상태 사상 카드 — Nagel 대조군 · 반전 심은 인공자료 위약 · 노출 맞춘 대조) ·
  data_plan(13f · fred · coverage_gates_F0 · public_repo_rule) · registration(allowed_F0_decisions «W11 자료 관문 → 닫기») · build_plan.modules[w_frag] ·
  갱신 2026-09-27(가 사용자 말 — 전방 원장 없음 · 나 오케스트레이터 결정 — 등록 B 가족 {W02 · W11} 한쪽 Holm α 0.05 · 채택 표시 = Holm 기각 ∧ Tier-2 무해 ∧ G-EGD) ·
  사용자 규칙(최근 20년 · G-NoEG · 주식 중심 · 카드마다 근본 이유). 설계를 다시 짓지 않는다. SEC 접속 규약은 w_geo(G13)와 같다(SecClient).

근본 이유(명세 그대로): 같은 소수의 기관이 크게 들고 있는 종목은 환매 · 디레버리지 때 함께 강제 매도되어 가격 압력이 급락을 키운다(유동성 공급자가 모자랄 때).
  자금 조건이 조여 가는 동안에만 그 다리를 피하고, 조임이 멈추면 지수 비중으로 돌아가 가격 압력의 되돌림을 놓치지 않는다 — 방어와 반등 양쪽을 한 규칙으로.

카드(명세 base · primary_statistic 그대로)
  행렬  분기마다 A_{k,i} = 13F 운용사 k 의 종목 i 보유 주식수 / i 의 발행주식수(sho · v_fund 최초 제출) · 가용 = 13F 접수 다음 NYSE 거래일.
  취약성 F_i = Σ_k A_{k,i}² — Greenwood–Thesmar G_i = Σ_{k,l} A_{k,i}A_{l,i}Ω_{kl} 에서 Ω = σ²I 인 정확한 특수형(선언 · 흐름 자료가 없어서 · 🔎 G–T 원문은 등록 전에
        열지 못했다 — [지식 · 미확인]) = 2605.26740 의 원시 집중 M(A) = Σ A² 의 종목(열) 성분([초록 · 직접] — 정의는 이쪽이 적는다).
  상태  s_t = clip(z(BAA10Y 3개월 변화)_t, 0, 2)/2 ∈ [0, 1] · 확장창 표준화 · 월말 값 1영업일 늦춤 — 수준이 아니라 변화라 스프레드가 정점을 찍으면 자동으로 0.
  책    평상시 w_B · s_t > 0 인 달 F 상위 20% 이름의 비중을 a_i = −0.5·s_t·w_B,i 로 줄이고(발행사 하한 −0.05) 풀린 비중은 같은 섹터 나머지에 w_B 비례 ·
        β 띠 ±0.03 · 월간 T+1 · 10/20bp.
  주 통계 FM r_{i,t+1} ~ z(F_i) + z(F_i)·s_t + Stage M-W 통제 · 교차항 γ · NW(3) · H1 γ < 0(방향 −1) — w_stagem S4(달별 γ_t(z(F)) 를 s_t 에 회귀).
  쌍둥이(보고만) 종목 수준 벤치 조정 의존도 X_i 로 F 를 바꾼 판. 대조(보고만) 무조건 F 틸트(s ≡ 1) · 같은 달 같은 몫 무작위 20% 축소(200회) ·
        베타 상위 20% 에 같은 축소 경로(노출 맞춘 대조) · Nagel 상태판 · 반전 심은 인공자료 위약(합성).
  F0(개수만 · 등록 B 자료 관문) 13F 구조화 자료집 존재 · 시작 분기 ≤ 2014Q2(아니면 카드를 닫는다 · 대용을 사후에 만들지 않는다) ·
        분기마다 Stage M-W 이름의 90% 이상에 보유자 ≥ 1 · CUSIP → 발행사 그룹 연결률 ≥ 95% · 스위치 활성(s ≥ 0.5 달 · 독립 사건).

🔎 명세가 정하지 않은 산수(선언 — 등록 B 문서에 옮긴다)
  F1 13F 자료집 = SEC Form 13F Data Sets(접수 창별 ZIP · SUBMISSION · COVERPAGE · INFOTABLE) · 보유 행 = SSHPRNAMTTYPE «SH» ∧ PUTCALL 빈칸(옵션 · 원금 행 제외) ·
     같은 (접수 번호, CUSIP) 는 더한다(재량 · 공동 운용사 행). 운용사 k = 제출 CIK(13F 보고 · 결합 보고 · 13F 통지는 보유 없음 — 결합 보고의 겹침은 그대로 · 공개).
  F2 분기 Q(t) = 분기말 + 45일 < 결정일 d 인 가장 늦은 분기말(정규 마감이 지난 분기) · 그 분기 보고 가운데 접수일 < d 인 것(다음 NYSE 거래일 가용 ≤ d) ·
     운용사마다 기준 = 가장 늦은 원본(13F-HR) 또는 «RESTATEMENT» 수정 · 기준 뒤에 접수된 «NEW HOLDINGS» 수정은 더한다(랩 refresh_13f 규약과 같다) ·
     기준이 없는 운용사는 뺀다. 늦게 낸 보고는 그 달부터 들어온다(달마다 d 로 자른다 — 시점정확).
  F3 CUSIP → 그룹(§A0 날짜 인식 지도): CUSIP ↔ 거래 기호 = SEC 결제 불이행(FTD) 파일(반월 · 결제일이 있는 기호 쌍 · 랩 refresh_13f 의 방식)의 날짜 구간 ·
     그룹 g 의 기호 = 결정 달 명단 티커 + groups[g].tickers 가운데 [Q 달 − 12, t] 와 겹치는 것 · 연결 CUSIP = 그 기호(영숫자만 비교)의 FTD 구간이
     [Q − 180일, d] 와 겹치는 CUSIP · 같은 그룹의 여러 보통주 종류(GOOG · GOOGL 등)는 주식 대 주식으로 더한다(BRK.A 는 명단 기호가 아니라 빠진다 · 공개).
  F4 분모 S_Q = frozen v_fund.shares_at(그룹, d)(최초 제출 · 가용 ≤ d · 백만 주) 를 Q 말 기준으로 분할 조정(명단 가격 키의 분할 사건 · v_px_split.me_value 와
     같은 규칙: 기준일 뒤 · Q 말까지 사건은 곱하고, Q 말 뒤 · 기준일까지 사건은 나눈다) · A = h / (S_Q × 10⁶) 를 [0, 1] 로 자른다(한 운용사가 100% 넘게
     들 수 없다 · 자른 개수 공개) · 입력 단위 sho 쓰임 = holding_ratio_denominator(w_guard 허용 예외).
  F4b 분모 위생(F0 탐침 뒤 · 계산 전 선언 — 수익 없이 보유 비율만 보고 정했다): (가) IO = Σ_k A_{k,i} > 1.5 이면 그달 F · X 결측(분모 오류 —
     얼린 v_fund.shares_at 이 COP 를 백만 주 단위의 1/1000(1.19 ≈ 11.9억 주)로 주고 · 합병 직후 낡은 주식수(WAB 2019) · ADS 비율(CTRP) 같은 경우 ·
     개수 공개) (나) FPI(§A0 fpi 표지 = 1) 이름은 F 결측(13F 는 ADS 로 · 분모는 보통주로 적혀 비율이 맞지 않는다 · Stage M-W 세계도 FPI 를 뺀다).
  F5 z(F) = 세계(Stage M-W) 안 단면 z(ddof 1 · w_cards.xs_z 와 같은 식 · 명세 그대로 원값 F) · 보유자 없는 이름 · 분모 없는 이름은 F 결측(행 제외 —
     focal_miss "drop") · 책의 «F 상위 20%» = 비금융 · F 가 선 이름 가운데 round(0.2·N) 개(내림차순 · 동점 티커).
  F6 s_t: x_m = 그달 BAA10Y 두 번째로 늦은 관측(1영업일 늦춤 · w_ipca I5 와 같다) · Δ_t = x_t − x_{t−3}(세 달 모두 선 때) · 확장창 z(계열 첫 달부터 ·
     관측 ≥ 60 · w_ipca month_state 와 같은 표본 규칙 · 평가 창이 아니라 신호 입력 — w_core K3) · 없으면 s = 0(축소 없음).
  F7 책 재분배: 줄인 합을 같은 섹터의 «선정 밖 · 비금융» 이름에 w_B 비례 · 그 섹터에 받을 이름이 없으면 그 섹터는 줄이지 않는다 ·
     그 뒤 frozen v_core.project_active(발행사 · 섹터 · NDX 전용 띠) → frozen v_core.beta_band(±0.03) · 체결 = w_cards.execute(½ 체결 · 무거래 띠 · 회전 예산).
     s_t = 0 이면 목표 = w_B(정체 selftest).
  F8 X_i 쌍둥이(2605.26740 [초록 · 식 직접]): X(A) = Σ_{k,i}(N_{ki} − p_k s_i)²/(p_k s_i) · N = 달러 보유(A·ME_t)를 풀(합집합 · 금융 포함) 전체 합 1 로 ·
     p_k = Σ_i N_{ki} · s_i = Σ_k N_{ki} · 종목 수준 = X 의 열 성분 ÷ s_i = Σ_k (N_{ki}/s_i − p_k)²/p_k(«종목의 투자자 구성이 시장 투자자 구성에서 벗어난
     정도» — 초록의 «size-weighted average of stock-level deviations» 에서 식으로 유도 · 원문 본문 미확인 → 쌍둥이 보고만).
  F9 대조: Nagel 상태 s^N_t = clip(−z_N, 0, 2)/2(w_ciq.nagel_state · 지난 12개월 시장 수익 선형 감소 가중 ÷ SD 의 확장창 z · 나쁜 최근 시장 = 스트레스) ·
     무작위 20%(«같은 달 같은 몫 무작위 20% 축소 200회»): 같은 달 · 같은 s_t · 같은 개수를 씨앗 default_rng(SEED + 3 + 1000·i)(K6)로 ·
     «θ 만 같은 달 같은 폭으로 줄인 판» = evaluation.controls «노출 맞춘 대조» 의 베타 판(같은 s_t 경로를 FP β̂ 상위 20% 에) — 방어가 «노출을 덜 든 효과» 가
     아님을 보인다 · 반전 심은 인공자료 위약 = reversal_placebo(합성 · F 효과 0 · 상태 조건 단기 반전만) · G-EGD 입력 = gegd_entry(θ = 1 = s ≡ 1 책 · 신호 F).
  F10 스위치 활성(시장 상태만 · 명세 coverage_gates_F0): S 창 결정 달 2016-08 ~ 2026-07 에서 s ≥ 0.5 인 달 수 · 독립 사건 = s ≥ 0.5 달의 연속 묶음 수 ·
     활성 12달 미만 또는 사건 4 미만이면 «사건 측정만» 라벨(규칙은 그대로 굽는다).
  F11 커버리지 F0: 결정 달마다 세계 이름 가운데 (가) 연결 CUSIP ≥ 1(연결률) (나) 보유자 ≥ 1(커버리지) 비율 — 분기(첫 사용 달)마다 ≥ 0.90 · 연결률은
     전체 이름-분기 몫 ≥ 0.95(분기 최소도 보고). 어느 하나라도 못 넘으면 등록 전에 카드를 닫는다.
  F12 🔎 BRK.A(선언 · 비평 2 L4): 랩 13F 파이프라인은 2026-09-27 커밋 38969b55e 에서 BRK.A 보유를 1 A = 1,500 B 로 더하도록 고쳤지만 이 모듈은 BRK.A
     (CUSIP 084670108)를 연결하지 않는다(F3 — 명단 기호가 아니다) → 버크셔의 IO · F 는 B 주 보유만이라 과소다. 영향: 버크셔는 GICS Financials 라
     Stage M-W 세계(W11 FM) · 축소 대상(reduce_set 은 비금융만)에 들지 않는다 — 가족 통계 · 책에 닿지 않는다(한 이름 · 공개). 맞추지 않는다(계산 전 결정).
  F13 🔁 추론(등록 전 · 비평 1 C1): 가족 판정 p 는 w_stagem S11 제약 야생 부트스트랩(B 9,999 · 씨앗 SEED + 505) — S4 NW(3) t 를 t 분포로 읽으면
     s_t 가 0 인 달 73/120 · 최대 지렛대 0.18 에서 한쪽 α/2 크기 5.7 ~ 8.7% · 두쪽 12.8 ~ 17.1% 로 부풀었다(씨앗 잡음 γ_t 3,000 회 · 부트스트랩판 2.5 ~ 2.7% · 4.9 ~ 5.2%).

🚨 랩 규율 — 등록 커밋 전에는 실자료로 수익 · IC · FM γ · 신호-수익 통계를 계산하지 않는다. 수익을 받는 공개 함수(w11_fm)는 kind 자물쇠를 지난다.
   실자료 명령(--build · --f0)은 개수 · 비율 · 날짜 · 분포 모양(F 의 분위 — 수익 아님)만 찍는다. 원자료 · 파생(13F · FTD)은 저장소 밖 캐시에만.

  python build/w_frag.py --selftest
  python build/w_frag.py --build-ftd [--from 2015-01]    FTD CUSIP ↔ 기호(재개 가능 · SEC)
  python build/w_frag.py --build-13f [--from 2016-04-01] 13F 자료집 → 보유 추출(재개 가능 · SEC · FTD 먼저)
  python build/w_frag.py --f0                            F0 개수 → 캐시 f0/w11_f0.json
  python build/w_frag.py --blind-smoke                   실자료 눈가린 연기(y · 평가 수익 = 씨앗 잡음 · 산출 열지 않고 삭제)
  python build/w_frag.py --manifest                      자료 핀(FTD · 13F 창별 원 ZIP · 추출 sha256 · BAA10Y) → 캐시 f0/w11_manifest.json
  python build/w_frag.py --plan                          재개 계획
"""
from __future__ import annotations

import bisect
import collections
import datetime as _dt
import gzip
import io
import json
import math
import os
import re
import sys
import time
import traceback
import zipfile

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import w_core as WC          # noqa: E402
import w_guard as WG         # noqa: E402
import w_geo as GEO          # noqa: E402 — SEC 접속 규약(SecClient) · 색인 · gz 입출력 · xs_z

# ══════════════════════════════════════════════════════════════════════════
#  카드 상수(명세 W11 그대로 · 지금 고정)
# ══════════════════════════════════════════════════════════════════════════
CARD = {"id": "W11", "name": "FRAG", "role": "가족 B", "direction": -1, "ic_lit": 0.020, "sigma_cat": 0.07, "t_eff": 60,
        "p0_synth": "0.114(σ 0.047) · 0.056(σ 0.07)", "book": {"top": 0.20, "cut": -0.5, "floor": -0.05, "beta_band": 0.03},
        "state": "clip(z(ΔBAA10Y 3개월), 0, 2)/2", "twins": ["X_i(벤치 조정 의존도)"],
        "controls": ["무조건 F 틸트(s ≡ 1)", "무작위 20% 축소(200)", "베타 상위 20% 같은 경로", "Nagel 상태", "반전 심은 인공자료 위약"],
        "cautions": ["data_gate", "v_repack"]}
assert CARD["direction"] == WC.CARD_DIRECTION["W11"] and "W11" in WC.FAMILY["B"]
TOP_FRAC, CUT, FLOOR = 0.20, -0.5, -0.05
Z_MIN_N = 60
DELTA_M = 3
DEADLINE_DAYS = 45
N_RANDOM = 200
RANDOM_SEED = WC.SEED + 3                                     # K6 — F9
FIN_SECTOR = "Financials"
S_ACTIVE = 0.5
ACT_MIN_MONTHS, ACT_MIN_EVENTS = 12, 4
COV_GATE, LINK_GATE = 0.90, 0.95
IO_MAX = 1.5                                                  # F4b — 기관 보유 합이 발행주식의 150% 를 넘으면 분모 오류로 본다
START_GATE = "2014q2"
LINK_BACK_DAYS = 180
LINK_BACK_M = 12

F13_INDEX = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
F13_PATTERN = r"(\d{4}q[1-4]|\d{2}[a-z]{3}\d{4}-\d{2}[a-z]{3}\d{4})_form13f\.zip"
F13_FROM = "2016-04-01"                                       # 첫 결정 달 2016-08 의 분기(2016Q2) 접수 창보다 한 창 앞
FTD_INDEX = "https://www.sec.gov/data/foiadocsfailsdatahtm"
FTD_PATTERN = r"cnsfails(\d{6})([ab])\.zip"
FTD_FROM = "2015-01"

FRAG_UNITS = [WG.unit("frag", source="SEC Form 13F Data Sets INFOTABLE + v_fund sho", concept="13F ownership concentration sum of squared holdings shares",
                      use="signal"),
              WG.unit("sho", source="v_fund(first-filed ledger)", concept="shares outstanding", use="holding_ratio_denominator"),
              WG.unit("frag_x", source="SEC Form 13F Data Sets INFOTABLE + v_fund sho + v_pit.me_row",
                      concept="stock-level benchmark-adjusted ownership dependence (chi-square)", use="signal"),
              WG.unit("stress_up", source="data/assets.json macro BAA10Y", concept="positive part of expanding z of 3-month credit spread change",
                      use="theta_state"),
              WG.unit("nagel_state", source="data/assets.json SPY", concept="linear-decay weighted 12-month market return over sd (Nagel control)",
                      use="theta_state")]
WG.assert_units(FRAG_UNITS, "w_frag 입력(모듈 적재)")


def _log(msg):
    print(msg, flush=True)


# ══════════════════════════════════════════════════════════════════════════
#  날짜
# ══════════════════════════════════════════════════════════════════════════
_MON = {m: i for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}


def iso_dmy(s):
    """'30-JUN-2016' → '2016-06-30' · 이미 ISO 면 그대로 · 모르면 None."""
    s = str(s or "").strip().upper()
    m = re.fullmatch(r"(\d{2})-([A-Z]{3})-(\d{4})", s)
    if m and m.group(2) in _MON:
        return "%s-%02d-%s" % (m.group(3), _MON[m.group(2)], m.group(1))
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    if re.fullmatch(r"\d{8}", s):
        return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])
    return None


def _add_days(d, k):
    return (_dt.date.fromisoformat(d) + _dt.timedelta(days=k)).isoformat()


def quarter_ends(a="2010-01-01", b="2026-12-31"):
    out = []
    for y in range(int(a[:4]), int(b[:4]) + 1):
        for md in ("03-31", "06-30", "09-30", "12-31"):
            d = "%d-%s" % (y, md)
            if a <= d <= b:
                out.append(d)
    return out


def q_of(d):
    """F2 — 결정일 d 의 분기 Q(분기말 + 45일 < d 인 가장 늦은 분기말)."""
    qs = [q for q in quarter_ends("2000-01-01", d) if _add_days(q, DEADLINE_DAYS) < d]
    return qs[-1] if qs else None


def f13_window(fn):
    """13F ZIP 이름 → (창 시작, 창 끝). '2016q3_form13f.zip' → 2016-07-01 ~ 2016-09-30 · '01jun2024-31aug2024_form13f.zip' → 그대로."""
    m = re.fullmatch(r"(\d{4})q([1-4])_form13f\.zip", fn)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        a = "%d-%02d-01" % (y, 3 * q - 2)
        b = quarter_ends("%d-01-01" % y, "%d-12-31" % y)[q - 1]
        return a, b
    m = re.fullmatch(r"(\d{2})([a-z]{3})(\d{4})-(\d{2})([a-z]{3})(\d{4})_form13f\.zip", fn)
    if m:
        a = "%s-%02d-%s" % (m.group(3), _MON[m.group(2).upper()], m.group(1))
        b = "%s-%02d-%s" % (m.group(6), _MON[m.group(5).upper()], m.group(4))
        return a, b
    return None, None


# ══════════════════════════════════════════════════════════════════════════
#  FTD — CUSIP ↔ 기호(F3)
# ══════════════════════════════════════════════════════════════════════════
def ftd_dir():
    return WC.cache_dir("raw", "ftd")


def norm_sym(s):
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def ftd_extract(zbytes):
    """FTD ZIP → {(cusip, 기호): [첫 결제일, 끝 결제일, 행 수]}(기호는 원 표기 · 날짜 ISO)."""
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    out = {}
    for name in z.namelist():
        with z.open(name) as fh:
            for line in io.TextIOWrapper(fh, encoding="latin-1", newline=""):
                p = line.rstrip("\r\n").split("|")
                if len(p) < 3:
                    continue
                d = iso_dmy(p[0])
                c, s = p[1].strip().upper(), p[2].strip().upper()
                if not d or len(c) != 9 or not s:
                    continue
                k = (c, s)
                v = out.get(k)
                if v is None:
                    out[k] = [d, d, 1]
                else:
                    v[0] = min(v[0], d)
                    v[1] = max(v[1], d)
                    v[2] += 1
    return out


def ftd_files(client):
    html = client.get(FTD_INDEX, "FTD 색인").decode("utf-8", "ignore")
    out = []
    for fn, u in GEO.index_zips(html, FTD_PATTERN):
        m = re.fullmatch(FTD_PATTERN, fn, re.I)
        out.append((m.group(1) + m.group(2).lower(), u))
    return sorted(out)


def build_ftd(client=None, ym_from=FTD_FROM, log=_log):
    client = client or GEO.SecClient()
    files = [(k, u) for k, u in ftd_files(client) if k[:4] + "-" + k[4:6] >= ym_from]
    done, new, deferred = [], [], []
    for k, u in files:
        p = os.path.join(ftd_dir(), "ftd_%s.json.gz" % k)
        if os.path.isfile(p):
            done.append(k)
            continue
        try:
            b = client.get(u, "FTD %s" % k)
        except GEO.SecDeferred:
            deferred.append(k)
            continue
        pairs = ftd_extract(b)
        GEO.write_json_gz(p, {"id": k, "url": u, "zip_sha256": GEO.sha256_bytes(b), "zip_bytes": len(b), "n_pairs": len(pairs),
                              "pairs": [[c, s, a, e, n] for (c, s), (a, e, n) in sorted(pairs.items())]})
        new.append(k)
        if len(new) % 24 == 1:
            log("  FTD %s · 쌍 %d · %.1f MB" % (k, len(pairs), len(b) / 1e6))
    return {"listed": [k for k, _ in files], "done_before": done, "new": new, "deferred": deferred, "n_req": client.n_req}


def ftd_intervals(files=None):
    """모든 FTD 추출 → {norm 기호: [(첫, 끝, cusip)]} · {cusip: [(첫, 끝, 기호)]}."""
    by_sym, by_cu = {}, {}
    acc = {}
    for fn in sorted(os.listdir(ftd_dir())):
        if not fn.startswith("ftd_") or (files and fn[4:11] not in files):
            continue
        for c, s, a, e, n in GEO.read_json_gz(os.path.join(ftd_dir(), fn))["pairs"]:
            k = (c, norm_sym(s))
            v = acc.get(k)
            acc[k] = [a, e] if v is None else [min(v[0], a), max(v[1], e)]
    for (c, s), (a, e) in acc.items():
        by_sym.setdefault(s, []).append((a, e, c))
        by_cu.setdefault(c, []).append((a, e, s))
    for v in by_sym.values():
        v.sort()
    for v in by_cu.values():
        v.sort()
    return by_sym, by_cu


class Linker:
    """F3 — 그룹 g · 분기 Q · 결정일 d → 연결 CUSIP 집합. by_sym = ftd_intervals()[0] · groups = §A0 지도 groups."""

    def __init__(self, by_sym, groups):
        self.by_sym = by_sym
        self.groups = groups

    def symbols(self, gid, member_t, qm, tm_):
        out = {norm_sym(member_t)} if member_t else set()
        for t, (a, b) in ((self.groups.get(gid) or {}).get("tickers") or {}).items():
            if a <= tm_ and b >= WC.mshift(qm, -LINK_BACK_M):
                out.add(norm_sym(t))
        return sorted(x for x in out if x)

    def cusips(self, gid, member_t, Q, d):
        lo = _add_days(Q, -LINK_BACK_DAYS)
        out = set()
        for s in self.symbols(gid, member_t, Q[:7], d[:7]):
            for a, e, c in self.by_sym.get(s, ()):
                if a <= d and e >= lo:
                    out.add(c)
        return sorted(out)


def keep_cusips(by_sym, groups, tm):
    """13F 추출 거르개 — 랩 지도 기호(tm 키 · 그룹 기호)의 FTD CUSIP 전부(날짜 무관 · 넉넉히)."""
    syms = {norm_sym(t) for t in tm} | {norm_sym(t) for g in groups.values() for t in (g.get("tickers") or {})}
    return sorted({c for s in syms for _a, _e, c in by_sym.get(s, ())})


# ══════════════════════════════════════════════════════════════════════════
#  13F 자료집(F1 · F2)
# ══════════════════════════════════════════════════════════════════════════
def f13_dir():
    return WC.cache_dir("raw", "f13")


def f13_files(client):
    html = client.get(F13_INDEX, "13F 색인").decode("utf-8", "ignore")
    out = []
    for fn, u in GEO.index_zips(html, F13_PATTERN):
        a, b = f13_window(fn)
        if a:
            out.append((a, b, fn, u))
    return sorted(out)


def _tsv_rows(z, name):
    with z.open(name) as fh:
        txt = io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline="")
        hdr = [h.strip().upper() for h in txt.readline().rstrip("\r\n").split("\t")]
        for line in txt:
            p = line.rstrip("\r\n").split("\t")
            if len(p) >= len(hdr):
                yield dict(zip(hdr, p))


def f13_extract(zbytes, keep):
    """13F ZIP → (접수 메타 {acc: {cik, period, filed, type, amend, report}}, 보유 [(acc, cusip, 주식수)], 개수).
    보유는 keep CUSIP · SH · PUTCALL 빈칸만 · 같은 (acc, cusip) 는 더한다."""
    keep = set(keep)
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    names = {n.upper().rsplit("/", 1)[-1]: n for n in z.namelist()}
    meta = {}
    for r in _tsv_rows(z, names["SUBMISSION.TSV"]):
        a = r.get("ACCESSION_NUMBER", "").strip()
        if not a:
            continue
        meta[a] = {"cik": int(re.sub(r"\D", "", r.get("CIK", "0")) or 0), "period": iso_dmy(r.get("PERIODOFREPORT")), "filed": iso_dmy(r.get("FILING_DATE")),
                   "type": r.get("SUBMISSIONTYPE", "").strip().upper(), "amend": "", "report": ""}
    for r in _tsv_rows(z, names["COVERPAGE.TSV"]):
        a = r.get("ACCESSION_NUMBER", "").strip()
        if a in meta:
            meta[a]["amend"] = r.get("AMENDMENTTYPE", "").strip().upper()
            meta[a]["report"] = r.get("REPORTTYPE", "").strip().upper()
    agg = {}
    n_rows = n_keep = n_opt = n_prn = 0
    for r in _tsv_rows(z, names["INFOTABLE.TSV"]):
        n_rows += 1
        c = r.get("CUSIP", "").strip().upper()
        if c not in keep:
            continue
        if r.get("PUTCALL", "").strip():
            n_opt += 1
            continue
        if r.get("SSHPRNAMTTYPE", "").strip().upper() != "SH":
            n_prn += 1
            continue
        try:
            sh = float(r.get("SSHPRNAMT", "").replace(",", ""))
        except ValueError:
            continue
        a = r.get("ACCESSION_NUMBER", "").strip()
        k = (a, c)
        agg[k] = agg.get(k, 0.0) + sh
        n_keep += 1
    hold = [(a, c, v) for (a, c), v in agg.items()]
    return meta, hold, {"n_info": n_rows, "n_keep_rows": n_keep, "n_opt": n_opt, "n_prn": n_prn, "n_hold": len(hold), "n_acc": len(meta)}


def f13_save(path, meta, hold, info, extra):
    acc = sorted({a for a, _, _ in hold} | set(meta))
    cus = sorted({c for _, c, _ in hold})
    ai = {a: i for i, a in enumerate(acc)}
    ci = {c: i for i, c in enumerate(cus)}
    ia = np.array([ai[a] for a, _, _ in hold], np.int32)
    ic = np.array([ci[c] for _, c, _ in hold], np.int32)
    sh = np.array([v for _, _, v in hold], np.float64)
    WC.assert_writable(path)
    np.savez_compressed(path + ".tmp.npz", acc_i=ia, cus_i=ic, shares=sh)
    os.replace(path + ".tmp.npz", path + ".npz")
    GEO.write_json_gz(path + ".json.gz", dict(extra, acc=acc, cusip=cus, meta={a: meta[a] for a in acc if a in meta}, info=info))
    return path


def f13_load(path):
    J = GEO.read_json_gz(path + ".json.gz")
    Z = np.load(path + ".npz")
    return J, Z["acc_i"], Z["cus_i"], Z["shares"]


def build_13f(client=None, d_from=F13_FROM, log=_log):
    """13F 추출(재개 가능 · FTD 먼저) — 창마다 한 요청 · ZIP 은 메모리에서만 · 개수만 찍는다."""
    client = client or GEO.SecClient()
    by_sym, _ = ftd_intervals()
    if not by_sym:
        raise SystemExit("🚨 FTD 추출이 없다 — --build-ftd 먼저")
    VD = WC.frozen("v_data")
    im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
    keep = keep_cusips(by_sym, im.get("groups") or {}, im.get("tm") or {})
    files = f13_files(client)
    start = files[0][2] if files else None
    todo = [(a, b, fn, u) for a, b, fn, u in files if b >= d_from]
    done, new, deferred = [], [], []
    for a, b, fn, u in todo:
        stem = os.path.join(f13_dir(), fn[:-4])
        if os.path.isfile(stem + ".npz") and os.path.isfile(stem + ".json.gz"):
            done.append(fn)
            continue
        t0 = time.time()
        try:
            zb = client.get(u, "13F %s" % fn)
        except GEO.SecDeferred:
            deferred.append(fn)
            continue
        meta, hold, info = f13_extract(zb, keep)
        f13_save(stem, meta, hold, info, {"file": fn, "url": u, "window": [a, b], "zip_sha256": GEO.sha256_bytes(zb), "zip_bytes": len(zb),
                                          "n_keep_cusip": len(keep)})
        new.append(fn)
        log("  13F %s · 정보표 %d 행 · 보유 %d · 접수 %d · %.1f MB · %.0fs" % (fn, info["n_info"], info["n_hold"], info["n_acc"], len(zb) / 1e6,
                                                                       time.time() - t0))
        del zb, meta, hold
    return {"listed": [fn for _, _, fn, _ in files], "first_listed": start, "todo": [fn for _, _, fn, _ in todo], "done_before": done, "new": new,
            "deferred": deferred, "n_keep_cusip": len(keep), "n_req": client.n_req}


class Holdings:
    """13F 추출 — 메타는 한 번에 · 보유 배열은 분기(Q)마다 게으르게(현재 분기 하나만 메모리 · ≤ 3 GB 규율) · 결정일마다 운용사 × 그룹 보유(F2).
    rows 를 주면(합성 selftest) {acc: {cusip: 주식수}} 에서 짓는다."""

    def __init__(self, files=None, meta=None, rows=None):
        self.meta, self.acc_file, self.stems = {}, {}, []
        self._rows = rows
        if meta is not None:
            self.meta = dict(meta)
        else:
            for fn in sorted(os.listdir(f13_dir())):
                if not fn.endswith(".npz") or (files and fn[:-4] not in files):
                    continue
                stem = os.path.join(f13_dir(), fn[:-4])
                J = GEO.read_json_gz(stem + ".json.gz")
                self.stems.append(stem)
                for a, m in J["meta"].items():
                    if a not in self.meta:
                        self.meta[a] = m
                        self.acc_file[a] = stem
        self.by_period = {}
        for a, m in self.meta.items():
            if m.get("period"):
                self.by_period.setdefault(m["period"], []).append(a)
        self._cache, self._per, self._amap = {}, (None, None), {}

    def _period(self, Q):
        """분기 Q 의 보유 배열 — {acc[], pa, pc(정렬), ps, off{cusip: (lo, hi)}}."""
        if self._per[0] == Q:
            return self._per[1]
        accs = sorted(self.by_period.get(Q, ()))
        apos = {a: i for i, a in enumerate(accs)}
        pa, pcs, ps = [], [], []
        if self._rows is not None:
            for a in accs:
                for c, v in (self._rows.get(a) or {}).items():
                    pa.append(apos[a])
                    pcs.append(c)
                    ps.append(v)
            pa = np.array(pa, np.int64)
            ps = np.array(ps, float)
        else:
            A_, C_, S_ = [], [], []
            for stem in sorted({self.acc_file[a] for a in accs if a in self.acc_file}):
                J, ia, ic, sh = f13_load(stem)
                fa = np.array([apos.get(a, -1) for a in J["acc"]], np.int64)
                sel = fa[ia] >= 0
                A_.append(fa[ia[sel]])
                C_.append(np.asarray(J["cusip"], object)[ic[sel]])
                S_.append(sh[sel])
            pa = np.concatenate(A_) if A_ else np.zeros(0, np.int64)
            pcs = list(np.concatenate(C_)) if C_ else []
            ps = np.concatenate(S_) if S_ else np.zeros(0)
        cu = np.asarray(pcs, object)
        order = np.argsort(cu, kind="stable") if len(cu) else np.zeros(0, np.int64)
        cu, pa, ps = cu[order], pa[order], ps[order]
        off = {}
        if len(cu):
            brk = np.flatnonzero(cu[1:] != cu[:-1]) + 1
            lo = np.r_[0, brk]
            hi = np.r_[brk, len(cu)]
            off = {cu[a]: (int(a), int(b)) for a, b in zip(lo, hi)}
        P = {"acc": accs, "pa": pa, "ps": ps, "off": off}
        self._per, self._amap = (Q, P), {}
        return P

    def filings_at(self, Q, d):
        """F2 — 운용사 CIK → 쓸 접수 번호 목록(기준 + 뒤의 NEW HOLDINGS)."""
        key = (Q, d)
        if key in self._cache:
            return self._cache[key]
        base, adds = {}, {}
        for a in self.by_period.get(Q, ()):
            m = self.meta[a]
            if not m.get("filed") or not m["filed"] < d:
                continue
            k = m["cik"]
            if m["type"] == "13F-HR" or (m["type"] == "13F-HR/A" and "RESTATE" in m.get("amend", "")):
                if k not in base or (m["filed"], a) > (self.meta[base[k]]["filed"], base[k]):
                    base[k] = a
            elif m["type"] == "13F-HR/A" and "NEW" in m.get("amend", ""):
                adds.setdefault(k, []).append(a)
        out = {}
        for k, a in base.items():
            fb = self.meta[a]["filed"]
            out[k] = [a] + sorted(x for x in adds.get(k, ()) if (self.meta[x]["filed"], x) > (fb, a))
        if len(self._cache) > 64:
            self._cache.clear()
        self._cache[key] = out
        return out

    def _acc_mgr(self, Q, d):
        """분기 배열의 접수 위치 → 운용사 CIK(쓰지 않는 접수는 −1)."""
        if d in self._amap:
            return self._amap[d]
        P = self._period(Q)
        pos = {a: i for i, a in enumerate(P["acc"])}
        am = np.full(len(P["acc"]), -1, np.int64)
        for k, accs in self.filings_at(Q, d).items():
            for a in accs:
                if a in pos:
                    am[pos[a]] = k
        self._amap[d] = am
        return am

    def group_holdings(self, Q, d, cusips):
        """{운용사: 주식수}(연결 CUSIP 합) — 0 보다 큰 것만."""
        P = self._period(Q)
        am = self._acc_mgr(Q, d)
        idx = [np.arange(*P["off"][c]) for c in sorted(set(cusips)) if c in P["off"]]
        if not idx:
            return {}
        rows = np.concatenate(idx)
        mg = am[P["pa"][rows]]
        ok = mg >= 0
        if not ok.any():
            return {}
        u, inv = np.unique(mg[ok], return_inverse=True)
        v = np.bincount(inv, weights=P["ps"][rows][ok])
        return {int(k): float(x) for k, x in zip(u, v) if x > 0}


# ══════════════════════════════════════════════════════════════════════════
#  분모 · A · F · X(F4 · F8) — 순수 함수
# ══════════════════════════════════════════════════════════════════════════
def split_adjust(S, basis, target, events):
    """F4 — 기준일 basis 의 주식수 S 를 target 날짜 기준으로(분할 사건 [(날짜, 배수)])."""
    f = 1.0
    for s, q in events or ():
        if basis < s <= target:
            f *= float(q)
        elif target < s <= basis:
            f /= float(q)
    return float(S) * f


def a_column(h, S_Q):
    """F4 — {운용사: 주식수} · 분모(백만 주) → ({운용사: A ∈ [0, 1]}, 자른 수)."""
    if not S_Q or not (S_Q > 0):
        return None, 0
    den = S_Q * 1e6
    out, n_clip = {}, 0
    for k, v in h.items():
        a = v / den
        if a > 1.0:
            a, n_clip = 1.0, n_clip + 1
        if a > 0:
            out[k] = a
    return out, n_clip


def fragility(A):
    """F_i = Σ_k A_{k,i}² · IO = Σ_k A · 보유자 수."""
    if A is None:
        return None, None, 0
    v = np.array(list(A.values()), float)
    return float((v * v).sum()), float(v.sum()), int(len(v))


def x_dependence(cols, me):
    """F8 — cols = {이름: {운용사: A}} · me = {이름: 시총} → {이름: D_i = Σ_k (N_ki/s_i − p_k)²/p_k}(N = A·ME 를 합 1 로)."""
    N = {}
    tot = 0.0
    for i, A in cols.items():
        w = me.get(i)
        if A is None or not w or not (w > 0):
            continue
        row = {k: a * w for k, a in A.items()}
        N[i] = row
        tot += sum(row.values())
    if tot <= 0:
        return {}
    p = {}
    for i, row in N.items():
        for k, v in row.items():
            p[k] = p.get(k, 0.0) + v / tot
    out = {}
    for i, row in N.items():
        s = sum(row.values()) / tot
        if s <= 0:
            continue
        out[i] = sum(((v / tot) / s) ** 2 / p[k] for k, v in row.items()) - 1.0
    return out


# ══════════════════════════════════════════════════════════════════════════
#  상태 s_t(F6) · Nagel(F9) · 스위치 활성(F10)
# ══════════════════════════════════════════════════════════════════════════
def month_x(daily):
    """FRED 일간 {날짜: 값} → {달: 그달 두 번째로 늦은 관측}(1영업일 늦춤 · w_ipca I5)."""
    by = {}
    for d in sorted(daily):
        v = daily[d]
        if v is None or not (v == v):
            continue
        by.setdefault(d[:7], []).append(float(v))
    return {m: v[-2] for m, v in by.items() if len(v) >= 2}


def stress_state(daily, months, min_n=Z_MIN_N, k=DELTA_M):
    """F6 — {결정 달: s_t ∈ [0, 1]}(없으면 0.0) · {달: z}(보고) — 계열 첫 달부터 확장창(그달까지)."""
    x = month_x(daily)
    allm = sorted(x)
    hist, z = [], {}
    for m in allm:
        m0 = WC.mshift(m, -k)
        if m0 not in x:
            continue
        dlt = x[m] - x[m0]
        hist.append(dlt)
        if len(hist) >= min_n:
            sd = float(np.std(hist, ddof=1))
            z[m] = (dlt - float(np.mean(hist))) / sd if sd > 0 else 0.0
    s = {m: (min(max(z[m], 0.0), 2.0) / 2.0 if z.get(m) is not None else 0.0) for m in months}
    return s, {m: z.get(m) for m in months}


def nagel_s(mkt_by_month, months):
    """F9 — Nagel 대조 상태 s^N = clip(−z_N, 0, 2)/2(w_ciq.nagel_state · 나쁜 최근 시장 = 스트레스)."""
    import w_ciq as CQ
    zN = CQ.nagel_state(mkt_by_month, months)
    return {m: min(max(-float(zN.get(m) or 0.0), 0.0), 2.0) / 2.0 for m in months}


def activity(s, months, thr=S_ACTIVE):
    """F10 — s ≥ thr 인 달 수 · 연속 묶음(독립 사건) 수 · s > 0 달 수 · 라벨."""
    act = [m for m in months if (s.get(m) or 0.0) >= thr]
    ev, prev = 0, None
    for m in act:
        if prev is None or WC.mno(m) - WC.mno(prev) > 1:
            ev += 1
        prev = m
    pos = sum(1 for m in months if (s.get(m) or 0.0) > 0)
    lab = "사건 측정만" if (len(act) < ACT_MIN_MONTHS or ev < ACT_MIN_EVENTS) else "규칙 측정"
    return {"n_months": len(months), "n_pos": pos, "n_active": len(act), "n_events": ev, "label": lab, "active": act}


# ══════════════════════════════════════════════════════════════════════════
#  실자료 월 입력(굽기 · 연기 · F0)
# ══════════════════════════════════════════════════════════════════════════
def frag_month(U, m, H, LK, world_t=None):
    """결정 달 m — 합집합 회원마다 {cusips, n_holders, F, IO, n_clip, S_Q, A(열)} · 분기 Q · d. 🚨 수익을 읽지 않는다."""
    VF = WC.frozen("v_fund")
    d = U.d_of(m)
    Q = q_of(d)
    out = {}
    for r in U.members(m):
        g = r.get("gid")
        rec = {"cusips": [], "n_holders": 0, "F": None, "IO": None, "n_clip": 0, "S_Q": None, "A": None, "gid": g, "io_flag": False,
               "fpi": bool(r.get("fpi"))}
        if g and Q:
            cs = LK.cusips(g, r["t"], Q, d)
            rec["cusips"] = cs
            sa = VF.shares_at(U.L, g, d)
            if sa is not None:
                S, basis = sa[0], sa[1]
                rec["S_Q"] = split_adjust(S, basis, Q, U.share_ev.get(r["k"]) or [])
            if cs:
                h = H.group_holdings(Q, d, cs)
                A, nc = a_column(h, rec["S_Q"])
                rec["n_holders"] = len(h)
                rec["n_clip"] = nc
                if A is not None:
                    rec["F"], rec["IO"], _ = fragility(A)
                    rec["A"] = A
                    if rec["IO"] > IO_MAX or rec["fpi"]:                           # F4b — 분모 위생
                        rec["io_flag"] = rec["IO"] > IO_MAX
                        rec["F"], rec["A"] = None, None
        out[r["t"]] = rec
    return {"m": m, "d": d, "Q": Q, "rows": out}


def frag_panel(U, months, H=None, LK=None, with_x=False, log=_log):
    """실자료 W11 입력 — {달: frag_month(…)}(with_x 면 그달 X 쌍둥이를 짓는다 · A 열은 메모리 규율로 곧바로 버린다). 🚨 값을 찍지 않는다."""
    if H is None:
        H = Holdings()
    if LK is None:
        VD = WC.frozen("v_data")
        im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
        LK = Linker(ftd_intervals()[0], im.get("groups") or {})
    out, t0 = {}, time.time()
    for i, m in enumerate(months):
        fm = frag_month(U, m, H, LK)
        if with_x:
            me = {t: v[0] for t, v in U.me(m).items() if v[0]}
            fm["X"] = x_dependence({t: r["A"] for t, r in fm["rows"].items()}, me)
        for r in fm["rows"].values():
            r.pop("A", None)
        out[m] = fm
        if i % 24 == 0:
            log("  W11 입력 %s · Q %s · 회원 %d · %.0fs" % (m, fm["Q"], len(fm["rows"]), time.time() - t0))
    return out


# ══════════════════════════════════════════════════════════════════════════
#  카드 계산(kind 자물쇠)
# ══════════════════════════════════════════════════════════════════════════
def _vals(D, rows, key):
    return np.array([np.nan if (rows.get(t) or {}).get(key) is None else float(rows[t][key]) for t in D["t"]], float)


def w11_fm(P, FR, s, kind, months=None, key="F", B=None, seed=None):
    """W11 Tier-1 — 달별 FM(z(F) · Stage M-W 통제) → γ_t 를 s_t 에 회귀(w_stagem S4) · 교차항 t · 방향 −1. key = "F"(주) · "X"(쌍둥이 — FR[m]["X"]).
    🚨 kind 자물쇠(w_stagem.fm). 돌려주는 것 {interaction, main, n_state, fm}."""
    import w_stagem as S
    if P.get("kind") != kind:
        raise SystemExit("🚨 패널 종류 %s ≠ %s" % (P.get("kind"), kind))
    ms = [m for m in (months or P["months"]) if m in P["m"] and m in FR]
    nm = "frag" if key == "F" else "frag_x"

    def des(m):
        D = P["m"][m]
        v = _vals(D, FR[m]["rows"], "F") if key == "F" else np.array([np.nan if FR[m]["X"].get(t) is None else FR[m]["X"][t] for t in D["t"]], float)
        return [S.stage_m_w_design(D, [(nm, GEO.xs_z(v))], focal_miss="drop", where="W11 %s" % key)]
    res = S.fm(ms, des, [nm], kind)
    si = S.state_interaction(res["months"], res["g"][nm], s, CARD["direction"], B=B, seed=seed)   # B · seed = S11 가족 판정 칸
    return {"interaction": si, "main": S.summarize(res["months"], res["g"][nm], CARD["direction"]), "fm": res,
            "n_state": sum(1 for m in res["months"] if s.get(m) is not None)}


def reduce_set(X, score, frac=TOP_FRAC, pick="top", rng=None):
    """축소 이름 — 비금융 · 점수가 선 이름 가운데 round(frac·N) 개. pick: top(내림차순 · 동점 티커) · random(rng)."""
    score = np.asarray(score, float)
    el = [i for i in range(X.n) if not X.fin[i] and np.isfinite(score[i])]
    n = int(round(frac * len(el)))
    if n <= 0:
        return np.zeros(X.n, bool)
    if pick == "top":
        chosen = sorted(el, key=lambda i: (-score[i], X.t[i]))[:n]
    elif pick == "random":
        chosen = [el[j] for j in rng.permutation(len(el))[:n]]
    else:
        raise ValueError(pick)
    mask = np.zeros(X.n, bool)
    mask[chosen] = True
    return mask


def w11_target(X, mask, s, cut=CUT, floor=FLOOR, beta_band=True):
    """F7 — 목표 책: a_i = max(cut·s·w_B,i, floor)(축소 이름) · 같은 섹터 선정 밖 비금융에 w_B 비례 재분배 → 투영 → β 띠. (w, info)."""
    C = WC.frozen("v_core")
    wB = X.wB.copy()
    if s is None or not (s > 0):
        return wB, {"n_red": 0, "cut_sum": 0.0}
    a = np.zeros(X.n)
    red = np.flatnonzero(mask & ~X.fin)
    sec = np.array([x if x is not None else "_none" for x in X.sec], object)
    cut_sum, n_red = 0.0, 0
    for sc in sorted(set(sec[red]), key=str):
        ri = [i for i in red if sec[i] == sc]
        rc = [i for i in range(X.n) if sec[i] == sc and not mask[i] and not X.fin[i] and wB[i] > 0]
        if not rc:
            continue                                                            # 받을 이름이 없으면 그 섹터는 줄이지 않는다
        ai = np.array([max(cut * float(s) * wB[i], floor) for i in ri])
        tot = -float(ai.sum())
        a[ri] = ai
        wr = wB[rc]
        a[rc] += tot * wr / wr.sum()
        cut_sum += tot
        n_red += len(ri)
    w = wB + a
    proj = lambda x: C.project_active(x, X.wB, X.sec, X.ndx)[0]
    w, pinfo = C.project_active(w, X.wB, X.sec, X.ndx)
    info = {"n_red": n_red, "cut_sum": cut_sum, "proj": {k: pinfo[k] for k in ("iters", "shrink", "feasible")}}
    if beta_band:
        w, binfo = C.beta_band(w, X.wB, X.beta, proj)
        info["beta"] = binfo
    w = np.where(w > 1e-15, w, 0.0)
    w = w / w.sum()
    C.assert_stock_book(X.book(w))
    WG.no_derivative_positions(X.book(w))
    return w, info


def w11_book(X, fr_rows, s, variant="main", rng=None):
    """책 한 달 — variant: main(F 상위 20% · s_t) · uncond(s ≡ 1) · random(같은 개수 무작위) · beta(FP β̂ 상위 20%) · xtwin(X 상위)."""
    if variant == "beta":
        score = np.asarray(X.beta, float)
    elif variant == "xtwin":
        score = np.array([np.nan if (fr_rows.get(t) is None) else fr_rows[t] for t in X.t], float)
    else:
        score = np.array([np.nan if (fr_rows.get(t) or {}).get("F") is None else fr_rows[t]["F"] for t in X.t], float)
    mask = reduce_set(X, score, pick="random" if variant == "random" else "top", rng=rng)
    return w11_target(X, mask, 1.0 if variant == "uncond" else s)


def gegd_entry(X, fr_rows):
    """G-EGD 입력 한 달 — θ = 1 책(s ≡ 1 · 무조건 F 축소) {티커: 비중} · 신호 {티커: F}(선 이름만 · |Spearman| 이라 부호 무관)."""
    w, _ = w11_book(X, fr_rows, 1.0, variant="uncond")
    sig = {t: float(r["F"]) for t, r in fr_rows.items() if r.get("F") is not None}
    return {"book": X.book(w), "signal": sig}


def reversal_placebo(seed=WC.SEED + 7, months=None, reversal=0.3):
    """반전 심은 인공자료 위약(명세 evaluation.controls · 합성 전용) — F 효과 없이 상태 조건 단기 반전만 심은 자료에서 교차항 t(보고)."""
    ms = months or WC.months_between("2016-08", "2026-07")
    P, FR, s = _synth_panel(seed, ms, reversal=reversal)
    return w11_fm(P, FR, s, "synth")["interaction"]


def w11_execute(w_drift, target):
    """월간 T+1 체결 — 공통 규칙(w_cards.execute · ½ 체결 · 무거래 띠 · 회전 예산)."""
    import w_cards as WCD
    return WCD.execute(w_drift, target)


# ══════════════════════════════════════════════════════════════════════════
#  F0 — 개수만(F10 · F11)
# ══════════════════════════════════════════════════════════════════════════
def coverage_months(FR, world_of_m):
    """결정 달마다 세계 이름의 연결 · 보유자 · 분모 · F 비율 · 자른 A 수 · IO 분위(값 모양 · 수익 아님)."""
    out = {}
    for m, fm in sorted(FR.items()):
        W = world_of_m(m)
        rows = fm["rows"]
        n = len(W)
        nl = sum(1 for t in W if (rows.get(t) or {}).get("cusips"))
        nh = sum(1 for t in W if (rows.get(t) or {}).get("n_holders", 0) >= 1)
        nf = sum(1 for t in W if (rows.get(t) or {}).get("F") is not None)
        io = [rows[t]["IO"] for t in W if (rows.get(t) or {}).get("IO") is not None]
        out[m] = {"Q": fm["Q"], "n_world": n, "link": nl / n if n else None, "holders": nh / n if n else None, "F": nf / n if n else None,
                  "n_io_flag": sum(1 for t in W if (rows.get(t) or {}).get("io_flag")),
                  "n_io_flag_all": sum(1 for r in rows.values() if r.get("io_flag")), "n_fpi_all": sum(1 for r in rows.values() if r.get("fpi")),
                  "n_clip": sum((rows.get(t) or {}).get("n_clip", 0) for t in W),
                  "io_q": [float(np.quantile(io, q)) for q in (0.1, 0.5, 0.9)] if io else None, "n_io_gt1": sum(1 for x in io if x > 1.0)}
    return out


def gate_eval(cov, first_listed, tier_from="2016-08"):
    """F11 — 분기(첫 사용 달)마다 보유자 비율 ≥ 0.90 · 연결률 전체 ≥ 0.95 · 13F 시작 ≤ 2014Q2."""
    tier = {m: v for m, v in cov.items() if m >= tier_from}
    firstm = {}
    for m, v in sorted(tier.items()):
        firstm.setdefault(v["Q"], m)
    qrows = {Q: tier[m] for Q, m in firstm.items()}
    hold_min = min((v["holders"] for v in qrows.values() if v["holders"] is not None), default=None)
    nl = sum(v["link"] * v["n_world"] for v in tier.values() if v["link"] is not None)
    nw = sum(v["n_world"] for v in tier.values() if v["link"] is not None)
    link = nl / nw if nw else None
    start = None
    if first_listed:
        a, _b = f13_window(first_listed)
        start = "%sq%d" % (a[:4], (int(a[5:7]) - 1) // 3 + 1) if a else None
    ok_start = start is not None and start <= START_GATE
    return {"start_listed": start, "start_ok": ok_start, "holders_min_by_quarter": hold_min, "holders_ok": hold_min is not None and hold_min >= COV_GATE,
            "link_pooled": link, "link_min_by_quarter": min((v["link"] for v in qrows.values() if v["link"] is not None), default=None),
            "link_ok": link is not None and link >= LINK_GATE, "n_quarters": len(qrows),
            "pass": bool(ok_start and hold_min is not None and hold_min >= COV_GATE and link is not None and link >= LINK_GATE)}


def f0_main(months=None, log=_log):
    """F0(개수만) → 캐시 f0/w11_f0.json. 🚨 수익을 읽지 않는다."""
    WG.install_open_audit()
    T0 = time.time()
    VD = WC.frozen("v_data")
    im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
    by_sym, by_cu = ftd_intervals()
    LK = Linker(by_sym, im.get("groups") or {})
    H = Holdings()
    log("FTD 기호 %d · CUSIP %d · 13F 접수 %d · 분기 %d · %.0fs" % (len(by_sym), len(by_cu), len(H.meta), len(H.by_period), time.time() - T0))
    import w_panel as _WPN
    U = _WPN.real_universe()   # PN8 내부 가격 오버레이를 얹은 세계
    ms = months or [m for m in U.months if "2016-06" <= m <= "2026-07" and WC.mshift(m, 1) in U.me_idx]
    FR = frag_panel(U, ms, H, LK)
    wcache = {}

    def world(m):
        if m not in wcache:
            wcache[m] = GEO.world_of(U, m)
        return wcache[m]
    cov = coverage_months(FR, world)
    first_listed = None
    try:
        idx = os.path.join(f13_dir(), "_index.json")
        with io.open(idx, encoding="utf-8") as f:
            first_listed = json.load(f).get("first_listed")
    except OSError:
        pass
    gate = gate_eval(cov, first_listed)
    A = VD.read_json(VD.lab_path("data/assets.json"))
    tier = [m for m in ms if m >= "2016-08"]
    s, z = stress_state(A["macro"]["BAA10Y"], tier)
    act = activity(s, tier)
    Fq = [r["F"] for m in tier[::12] for t, r in FR[m]["rows"].items() if r.get("F") is not None and t in set(world(m))]
    doc = {"card": "W11", "rule": "F0 개수만(명세 f0_gates · 등록 B 자료 관문) — 수익 없음", "at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "ftd": {"n_sym": len(by_sym), "n_cusip": len(by_cu)}, "f13": {"n_acc": len(H.meta), "periods": sorted(H.by_period)[:1] + sorted(H.by_period)[-1:]},
           "gate": gate, "coverage": cov, "activity": {k: v for k, v in act.items() if k != "active"}, "active_months": act["active"],
           "state_z_quantiles": [float(np.quantile([v for v in z.values() if v is not None], q)) for q in (0.1, 0.5, 0.9)],
           "F_shape": {"n": len(Fq), "q": [float(np.quantile(Fq, q)) for q in (0.01, 0.1, 0.5, 0.9, 0.99)] if Fq else None},
           "decision": {"close_card": not gate["pass"], "label": act["label"]},
           "noeg": {"ok": WG.noeg_report()["ok"]}, "sec": round(time.time() - T0, 1)}
    p = os.path.join(WC.cache_dir("f0"), "w11_f0.json")
    WC.assert_writable(p)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc, p


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기(w_hygiene.blind_smoke · 산출 열지 않고 삭제)
# ══════════════════════════════════════════════════════════════════════════
N_SMOKE_RANDOM = 2                                            # 연기는 모양만(굽기는 N_RANDOM 200)


def blind_run(U, FR, s, sN, X, seed):
    """run(pb, out) — W11 주 교차항 · X 쌍둥이 · Nagel 상태 · 책 다섯(주 · 무조건 · 무작위 · 베타 · X) · D0 · 펀드 X · 무해. 🚨 수익은 pb.y 또는 잡음."""
    import pickle
    import pandas as pd

    def run(pb, out):
        assert pb["kind"] == "blind"
        rng = np.random.default_rng(seed + 1)
        ms = [m for m in pb["months"] if GEO.TIER_FROM <= m <= GEO.TIER_TO and m in FR]
        res = {"main": w11_fm(pb, FR, s, "blind", months=ms), "xtwin": w11_fm(pb, FR, s, "blind", months=ms, key="X"),
               "nagel": w11_fm(pb, FR, sN, "blind", months=ms)}
        ret_of = GEO._noise_ret(pb, X, seed + 2)
        variants = [("main", None), ("uncond", None), ("beta", None), ("xtwin", None)] + [("random", i) for i in range(N_SMOKE_RANDOM)]
        for var, rep in variants:
            books = {}
            rr = np.random.default_rng(RANDOM_SEED + 1000 * rep) if rep is not None else None
            for m in ms:
                if m not in X:
                    continue
                rows = FR[m]["X"] if var == "xtwin" else FR[m]["rows"]
                w, _ = w11_book(X[m], rows, s.get(m, 0.0), variant=var, rng=rr)
                books[m] = X[m].book(w)
            Sx, Tx = GEO.d0_path(books, ret_of, w11_execute)
            idx = pd.PeriodIndex(sorted(Sx), freq="M")
            Ss = pd.Series([Sx[str(p)] for p in idx], index=idx)
            Bs = pd.Series(rng.normal(0.008, 0.04, len(idx)), index=idx)
            Xf = WC.fund_x(Ss, Bs, 0.001, traded=pd.Series([Tx[str(p)] for p in idx], index=idx), mult=2.0)
            key = var if rep is None else "%s%d" % (var, rep)
            res["tier2_" + key] = WC.tier2_harmless({str(p): float(v) for p, v in Xf.items()}, WC.turnover_annual(list(Tx.values())), True)
            assert len(books) >= 100 and res["tier2_" + key]["n"] >= 100 and res["tier2_" + key]["n_down"] >= 20, "모양: 책 · Tier-2 달 수"
        for k in ("main", "xtwin", "nagel"):
            assert res[k]["interaction"]["T"] >= 100 and res[k]["interaction"]["t"] is not None, "모양: 교차항 달 수 %s" % k
        with open(os.path.join(out, "w11_blind.pkl"), "wb") as f:
            pickle.dump(res, f)
        return res
    return run


def blind_smoke_main(log=_log):
    """W11 실자료 눈가린 연기 — 찍는 것: 참/거짓 · 시간 · 개수 · G-NoEG 세 겹 · 얼린 모듈. 값은 찍지 않는다."""
    import w_hygiene as HY
    WG.install_open_audit()
    probs = WC.env_problems()
    if probs:
        raise SystemExit("🚨 환경 핀: %s" % probs)
    fz = WC.frozen_check()
    if not fz["ok"]:
        raise SystemExit("🚨 얼린 V 모듈 핀 어긋남: %s" % fz["bad"])
    T0 = time.time()
    U, P, X, months = GEO.smoke_setup(log)
    VD = WC.frozen("v_data")
    im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
    LK = Linker(ftd_intervals()[0], im.get("groups") or {})
    FR = frag_panel(U, months, Holdings(), LK, with_x=True, log=lambda *_: None)
    A = VD.read_json(VD.lab_path("data/assets.json"))
    s, _z = stress_state(A["macro"]["BAA10Y"], months)
    sN = nagel_s(U.spy_month(), months)
    log("W11 입력 · 달 %d · %.0fs" % (len(FR), time.time() - T0))
    r = HY.blind_smoke(blind_run(U, FR, s, sN, X, WC.SEED), P, WC.SEED)
    nr = WG.noeg_report()
    lf = WC.loaded_frozen_check()
    out = {"blind_smoke": {k: r[k] for k in ("ok", "sec", "n_files", "bytes", "deleted", "err", "returned")},
           "noeg": {"ok": nr["ok"], "static": nr["static"]["ok"], "runtime": nr["runtime"]["ok"], "open_audit": nr["open_audit"].get("ok"),
                    "n_opened": nr["open_audit"].get("n_opened"), "n_black": nr["open_audit"].get("n_black")},
           "loaded_frozen": lf["ok"], "frozen_pins": fz["ok"], "total_sec": round(time.time() - T0, 1)}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if (r["ok"] and nr["ok"] and lf["ok"]) else 1


def manifest():
    """W11 자료 핀 — FTD 파일 · 13F 창마다 원 ZIP sha256 · 추출 sha256 · 개수 · BAA10Y 추출 sha · 전체 요약 sha."""
    ftd, f13 = [], []
    for fn in sorted(os.listdir(ftd_dir())):
        if fn.startswith("ftd_"):
            p = os.path.join(ftd_dir(), fn)
            d = GEO.read_json_gz(p)
            ftd.append([d["id"], d["zip_sha256"], GEO.file_sha256(p), d["n_pairs"]])
    for fn in sorted(os.listdir(f13_dir())):
        if fn.endswith(".npz"):
            stem = os.path.join(f13_dir(), fn[:-4])
            J = GEO.read_json_gz(stem + ".json.gz")
            f13.append([J["file"], J["zip_sha256"], GEO.file_sha256(stem + ".npz"), GEO.file_sha256(stem + ".json.gz"), J["info"]["n_hold"]])
    VD = WC.frozen("v_data")
    A = VD.read_json(VD.lab_path("data/assets.json"))
    baa = sorted((k, v) for k, v in A["macro"]["BAA10Y"].items() if k <= "2026-08-31")
    doc = {"card": "W11", "ftd": ftd, "ftd_digest": GEO.digest(ftd), "f13": f13, "f13_digest": GEO.digest(f13),
           "baa10y_to_2026_08": {"n": len(baa), "first": baa[0][0] if baa else None, "last": baa[-1][0] if baa else None, "sha256": GEO.digest(baa)},
           "issuer_map_sha256": GEO.file_sha256(VD.lab_path("data/_issuer_map.json"))}
    doc["digest"] = GEO.digest([["ftd", doc["ftd_digest"]], ["f13", doc["f13_digest"]], ["baa", doc["baa10y_to_2026_08"]["sha256"]],
                                ["im", doc["issuer_map_sha256"]]])
    p = os.path.join(WC.cache_dir("f0"), "w11_manifest.json")
    WC.assert_writable(p)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc, p


def plan():
    ftd = sorted(fn[4:11] for fn in os.listdir(ftd_dir()) if fn.startswith("ftd_"))
    f13 = sorted(fn[:-4] for fn in os.listdir(f13_dir()) if fn.endswith(".npz"))
    return {"ftd_have": len(ftd), "ftd_first_last": ftd[:1] + ftd[-1:], "f13_have": f13, "deferral_notes": GEO.notes_path(),
            "resume": "python build/w_frag.py --build-ftd · --build-13f(있는 파일은 건너뛴다)"}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 · 망 없음)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn, exc=SystemExit):
    try:
        fn()
    except exc:
        return True
    return False


def _st_dates():
    assert iso_dmy("30-JUN-2016") == "2016-06-30" and iso_dmy("20160630") == "2016-06-30" and iso_dmy("x") is None
    assert q_of("2016-08-31") == "2016-06-30" and q_of("2016-08-14") == "2016-03-31" and q_of("2016-08-15") == "2016-06-30"
    assert q_of("2016-10-31") == "2016-06-30" and q_of("2016-11-30") == "2016-09-30" and q_of("2017-02-28") == "2016-12-31"
    assert f13_window("2016q3_form13f.zip") == ("2016-07-01", "2016-09-30")
    assert f13_window("01jun2024-31aug2024_form13f.zip") == ("2024-06-01", "2024-08-31") and f13_window("x.zip") == (None, None)
    assert norm_sym("BRK.B") == norm_sym("BRK/B") == norm_sym("brk-b") == "BRKB"
    return "날짜(DD-MON-YYYY · Q(t) = 분기말 + 45일 < d) · 13F 창 이름 둘 · 기호 정규화"


def _fake_13f_zip(subs, covers, infos):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        def put(name, hdr, rows):
            z.writestr(name, "\n".join(["\t".join(hdr)] + ["\t".join(str(r.get(h, "")) for h in hdr) for r in rows]) + "\n")
        put("SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "CIK", "PERIODOFREPORT"], subs)
        put("COVERPAGE.tsv", ["ACCESSION_NUMBER", "REPORTCALENDARORQUARTER", "ISAMENDMENT", "AMENDMENTTYPE", "REPORTTYPE"], covers)
        put("INFOTABLE.tsv", ["ACCESSION_NUMBER", "INFOTABLE_SK", "NAMEOFISSUER", "TITLEOFCLASS", "CUSIP", "VALUE", "SSHPRNAMT", "SSHPRNAMTTYPE",
                              "PUTCALL"], infos)
    return buf.getvalue()


def _st_13f():
    subs = [dict(ACCESSION_NUMBER="A1", FILING_DATE="10-AUG-2016", SUBMISSIONTYPE="13F-HR", CIK="0000000001", PERIODOFREPORT="30-JUN-2016"),
            dict(ACCESSION_NUMBER="A2", FILING_DATE="20-SEP-2016", SUBMISSIONTYPE="13F-HR/A", CIK="1", PERIODOFREPORT="30-JUN-2016"),
            dict(ACCESSION_NUMBER="A3", FILING_DATE="05-OCT-2016", SUBMISSIONTYPE="13F-HR/A", CIK="1", PERIODOFREPORT="30-JUN-2016"),
            dict(ACCESSION_NUMBER="B1", FILING_DATE="12-AUG-2016", SUBMISSIONTYPE="13F-HR", CIK="2", PERIODOFREPORT="30-JUN-2016"),
            dict(ACCESSION_NUMBER="B2", FILING_DATE="15-SEP-2016", SUBMISSIONTYPE="13F-HR/A", CIK="2", PERIODOFREPORT="30-JUN-2016"),
            dict(ACCESSION_NUMBER="C1", FILING_DATE="02-SEP-2016", SUBMISSIONTYPE="13F-HR", CIK="3", PERIODOFREPORT="30-JUN-2016")]
    covers = [dict(ACCESSION_NUMBER="A2", AMENDMENTTYPE="NEW HOLDINGS", REPORTTYPE="13F HOLDINGS REPORT"),
              dict(ACCESSION_NUMBER="A3", AMENDMENTTYPE="NEW HOLDINGS", REPORTTYPE="13F HOLDINGS REPORT"),
              dict(ACCESSION_NUMBER="B2", AMENDMENTTYPE="RESTATEMENT", REPORTTYPE="13F HOLDINGS REPORT")]
    infos = [dict(ACCESSION_NUMBER="A1", CUSIP="037833100", SSHPRNAMT="1000", SSHPRNAMTTYPE="SH"),
             dict(ACCESSION_NUMBER="A1", CUSIP="037833100", SSHPRNAMT="500", SSHPRNAMTTYPE="SH"),
             dict(ACCESSION_NUMBER="A1", CUSIP="037833100", SSHPRNAMT="9999", SSHPRNAMTTYPE="SH", PUTCALL="Put"),
             dict(ACCESSION_NUMBER="A1", CUSIP="037833AK6", SSHPRNAMT="5000", SSHPRNAMTTYPE="PRN"),
             dict(ACCESSION_NUMBER="A2", CUSIP="02079K305", SSHPRNAMT="200", SSHPRNAMTTYPE="SH"),
             dict(ACCESSION_NUMBER="A3", CUSIP="037833100", SSHPRNAMT="7", SSHPRNAMTTYPE="SH"),
             dict(ACCESSION_NUMBER="B1", CUSIP="037833100", SSHPRNAMT="3000", SSHPRNAMTTYPE="SH"),
             dict(ACCESSION_NUMBER="B2", CUSIP="037833100", SSHPRNAMT="2500", SSHPRNAMTTYPE="SH"),
             dict(ACCESSION_NUMBER="C1", CUSIP="037833100", SSHPRNAMT="100", SSHPRNAMTTYPE="SH"),
             dict(ACCESSION_NUMBER="C1", CUSIP="999999999", SSHPRNAMT="100", SSHPRNAMTTYPE="SH")]
    meta, hold, info = f13_extract(_fake_13f_zip(subs, covers, infos), keep=["037833100", "037833AK6", "02079K305"])
    hd = {(a, c): v for a, c, v in hold}
    assert hd[("A1", "037833100")] == 1500 and ("A1", "037833AK6") not in hd and info["n_opt"] == 1 and info["n_prn"] == 1
    assert meta["B2"]["amend"] == "RESTATEMENT" and meta["A1"]["period"] == "2016-06-30" and meta["A1"]["cik"] == 1
    td = WC.cache_dir("selftest", "w_frag_13f")
    stem = os.path.join(td, "t")
    f13_save(stem, meta, hold, info, {"file": "t"})
    J, ia, ic, sh = f13_load(stem)
    assert len(ia) == len(hold) and abs(sh.sum() - sum(v for _, _, v in hold)) < 1e-9
    rows = {}
    for a, c, v in hold:
        rows.setdefault(a, {})[c] = v
    H = Holdings(meta=meta, rows=rows)
    f = H.filings_at("2016-06-30", "2016-08-31")
    assert f == {1: ["A1"], 2: ["B1"]}, f                                           # C1 은 d 뒤 접수
    f2 = H.filings_at("2016-06-30", "2016-09-30")
    assert f2 == {1: ["A1", "A2"], 2: ["B2"], 3: ["C1"]}, f2                         # NEW HOLDINGS 더함 · RESTATEMENT 교체
    f3 = H.filings_at("2016-06-30", "2016-10-31")
    assert f3[1] == ["A1", "A2", "A3"]
    h = H.group_holdings("2016-06-30", "2016-09-30", ["037833100", "02079K305"])
    assert h == {1: 1700.0, 2: 2500.0, 3: 100.0}, h
    assert H.group_holdings("2016-06-30", "2016-08-10", ["037833100"]) == {}        # 접수 당일은 아직
    import shutil
    shutil.rmtree(td, ignore_errors=True)
    return "13F 추출(SH · 옵션 · 원금 거르기 · 같은 행 더하기 · npz 왕복) · 접수 규칙(d 로 자름 · RESTATEMENT 교체 · NEW HOLDINGS 더함 · 당일 제외)"


def _st_ftd_link():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("cnsfails201606b.txt", "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n"
                   "20160615|037833100|AAPL|100|APPLE INC|95\n20160630|037833100|AAPL|5|APPLE INC|95\n"
                   "20160615|30303M102|FB|10|FACEBOOK|110\n20160620|084670702|BRK/B|3|BERKSHIRE B|140\nTrailer record count 4\n")
    pairs = ftd_extract(buf.getvalue())
    assert pairs[("037833100", "AAPL")] == ["2016-06-15", "2016-06-30", 2] and len(pairs) == 3
    by_sym = {"AAPL": [("2014-01-02", "2026-08-28", "037833100")], "FB": [("2014-01-02", "2022-06-08", "30303M102"), ("2023-01-03", "2025-01-01", "99999X100")],
              "META": [("2022-06-09", "2026-08-28", "30303M102")], "BRKB": [("2014-01-02", "2026-08-28", "084670702")],
              "GOOGL": [("2014-04-03", "2026-08-28", "02079K305")], "GOOG": [("2014-04-03", "2026-08-28", "02079K107")]}
    groups = {"gA": {"tickers": {"AAPL": ["2014-06", "2026-09"]}}, "gM": {"tickers": {"FB": ["2014-06", "2022-05"], "META": ["2022-06", "2026-09"]}},
              "gG": {"tickers": {"GOOGL": ["2014-06", "2026-09"], "GOOG": ["2014-06", "2026-09"]}}, "gB": {"tickers": {"BRK.B": ["2014-06", "2026-09"]}}}
    LK = Linker(by_sym, groups)
    assert LK.cusips("gA", "AAPL", "2016-06-30", "2016-08-31") == ["037833100"]
    assert LK.cusips("gG", "GOOGL", "2016-06-30", "2016-08-31") == ["02079K107", "02079K305"]
    assert LK.cusips("gB", "BRK.B", "2016-06-30", "2016-08-31") == ["084670702"]
    assert LK.cusips("gM", "META", "2025-06-30", "2025-08-29") == ["30303M102"]      # FB 기호의 뒤 주인(99999X100)은 그룹 기호 창 밖이라 안 붙는다
    assert LK.cusips("gM", "FB", "2016-06-30", "2016-08-31") == ["30303M102"]
    assert LK.cusips("gX", None, "2016-06-30", "2016-08-31") == []
    assert keep_cusips(by_sym, groups, {"AAPL": []}) == sorted({"037833100", "30303M102", "99999X100", "02079K305", "02079K107", "084670702"})
    return "FTD 추출(결제일 구간 · 꼬리 줄) · 연결(명단 · 그룹 기호 · 여러 종류 · 기호 재사용 창 · BRK/B 정규화)"


def _st_math():
    ev = [("2020-08-31", 4.0)]
    assert split_adjust(100.0, "2020-07-30", "2020-09-30", ev) == 400.0 and split_adjust(400.0, "2020-10-30", "2020-06-30", ev) == 100.0
    assert split_adjust(100.0, "2020-07-30", "2020-08-30", ev) == 100.0
    A, nc = a_column({1: 5e6, 2: 2e6, 3: 2e9}, 1000.0)
    assert nc == 1 and A[3] == 1.0 and abs(A[1] - 0.005) < 1e-15
    F, IO, n = fragility({1: 0.1, 2: 0.2})
    assert abs(F - 0.05) < 1e-15 and abs(IO - 0.3) < 1e-15 and n == 2
    assert a_column({1: 1.0}, None) == (None, 0)
    # X — 모든 종목의 투자자 구성이 같으면 0 · 한 투자자만 든 종목은 크다 · 무작정 계산(χ² 열 성분 ÷ s_i)과 대조
    cols = {"a": {1: 0.1, 2: 0.2}, "b": {1: 0.05, 2: 0.1}}
    X0 = x_dependence(cols, {"a": 10.0, "b": 20.0})
    assert all(abs(v) < 1e-12 for v in X0.values()), X0
    rng = np.random.default_rng(WC.SEED)
    cols = {i: {k: float(rng.uniform(0, 0.05)) for k in range(12) if rng.random() < 0.7} for i in range(15)}
    me = {i: float(rng.lognormal(3, 1)) for i in range(15)}
    X1 = x_dependence(cols, me)
    Nm = np.zeros((12, 15))
    for i, A_ in cols.items():
        for k, a in A_.items():
            Nm[k, i] = a * me[i]
    Nm /= Nm.sum()
    p, sv = Nm.sum(1), Nm.sum(0)
    for i in range(15):
        ok = p > 0
        chi = float((((Nm[ok, i] - p[ok] * sv[i]) ** 2) / (p[ok] * sv[i])).sum())
        assert abs(chi / sv[i] - X1[i]) < 1e-9, (i, chi / sv[i], X1[i])
    tot = sum(sv[i] * X1[i] for i in range(15))
    ok = p > 0
    Xall = float((((Nm[ok] - np.outer(p[ok], sv)) ** 2) / np.outer(p[ok], sv)).sum())
    assert abs(tot - Xall) < 1e-9                                                    # Σ_i s_i·D_i = X(A)(열 분해)
    return "분할 조정 두 방향 · A 자르기 · F = ΣA² · X 열 분해(= χ² 열 성분 ÷ s_i · Σ s_i D_i = X(A) · 같은 구성 → 0)"


def _st_state():
    d = {}
    day = _dt.date(1990, 1, 1)
    rng = np.random.default_rng(WC.SEED)
    v = 2.0
    while day <= _dt.date(2026, 8, 31):
        if day.weekday() < 5:
            v = max(0.5, v + float(rng.normal(0, 0.03)))
            d[day.isoformat()] = v
        day += _dt.timedelta(days=1)
    ms = WC.months_between("2016-08", "2026-07")
    s, z = stress_state(d, ms)
    assert all(0.0 <= s[m] <= 1.0 for m in ms) and any(s[m] > 0 for m in ms) and any(s[m] == 0 for m in ms)
    for m in ms:
        if z[m] is not None:
            assert abs(s[m] - min(max(z[m], 0), 2) / 2) < 1e-15
    cut = "2020-12-31"
    s2, _ = stress_state({k: x for k, x in d.items() if k <= cut}, [m for m in ms if m <= "2020-12"])
    assert all(s2[m] == s[m] for m in s2)                                             # 선견 없음
    x = month_x({"2020-01-30": 1.0, "2020-01-31": 2.0, "2020-02-27": 3.0, "2020-02-28": 4.0})
    assert x == {"2020-01": 1.0, "2020-02": 3.0}                                     # 두 번째로 늦은 관측(1영업일 늦춤)
    act = activity({"2020-01": 0.6, "2020-02": 0.7, "2020-04": 0.5, "2020-05": 0.1}, ["2020-01", "2020-02", "2020-03", "2020-04", "2020-05"])
    assert act["n_active"] == 3 and act["n_events"] == 2 and act["label"] == "사건 측정만" and act["n_pos"] == 4
    return "s_t(두 번째 늦은 관측 · 3개월 변화 · 확장창 z · clip/2 · 선견 없음) · 스위치 활성(달 · 사건 · 라벨)"


def _synth_cross(seed, n=80):
    import w_cards as WCD
    rng = np.random.default_rng(seed)
    t = ["N%02d" % i for i in range(n)]
    sec = [("S%d" % (i % 4)) if i % 9 else FIN_SECTOR for i in range(n)]
    me = rng.lognormal(4, 1, n)
    X = WCD.Cross("2020-01", t, me, me, sec, np.zeros(n, bool), rng.normal(1, 0.25, n))
    rows = {tt: {"F": float(rng.lognormal(-5, 1))} for tt in t[:70]}
    return X, rows


def _st_book():
    X, rows = _synth_cross(WC.SEED)
    w0, i0 = w11_book(X, rows, 0.0)
    assert np.max(np.abs(w0 - X.wB)) < 1e-15 and i0["n_red"] == 0                   # s = 0 → w_B(정체)
    w, info = w11_book(X, rows, 1.0)
    el = [i for i in range(X.n) if not X.fin[i] and X.t[i] in rows]
    assert info["n_red"] == round(0.2 * len(el)) and abs(w.sum() - 1) < 1e-9
    top = sorted(el, key=lambda i: (-rows[X.t[i]]["F"], X.t[i]))[:info["n_red"]]
    assert all(w[i] < X.wB[i] + 1e-12 for i in top)                                  # 축소 이름은 줄었다
    assert np.max(np.abs(w - X.wB)) <= 0.05 + 1e-9 and abs(float(np.dot(w - X.wB, X.beta))) <= 0.03 + 1e-6
    wh, ih = w11_book(X, rows, 0.5)
    assert ih["cut_sum"] < info["cut_sum"] + 1e-12                                   # s 가 작으면 덜 줄인다
    wu, iu = w11_book(X, rows, 0.0, variant="uncond")
    assert iu["n_red"] == info["n_red"]                                              # 무조건 틸트는 s ≡ 1
    wr, ir = w11_book(X, rows, 1.0, variant="random", rng=np.random.default_rng(RANDOM_SEED))
    assert ir["n_red"] == info["n_red"]
    wbeta, ib = w11_book(X, rows, 1.0, variant="beta")
    assert ib["n_red"] == round(0.2 * sum(1 for i in range(X.n) if not X.fin[i]))
    fin = X.fin
    assert np.allclose(w[fin], X.wB[fin], atol=0.01)                                  # 금융주는 축소 대상이 아니다(투영 · β 띠가 조금 움직일 수 있다)
    ge = gegd_entry(X, rows)
    assert abs(sum(ge["book"].values()) - 1) < 1e-9 and len(ge["signal"]) == 70
    b, tr, sk = w11_execute(X.book(X.wB), X.book(w))
    assert abs(sum(b.values()) - 1) < 1e-9
    return "책(s 0 → w_B · 상위 20% 축소 · 섹터 재분배 · 발행사 · β 띠 · s 비례) · 대조(무조건 · 무작위 · 베타) · 체결"


def _synth_panel(seed, months, n=250, gamma1=0.0, reversal=0.0):
    """합성 패널 — y = γ1·s_t·z(F) + 반전(reversal·(−r1)·s_t) + 잡음 · FR{달: rows{t: F}} · s{달}."""
    rng = np.random.default_rng(seed)
    P = {"kind": "synth", "months": list(months), "m": {}}
    FR, s = {}, {}
    for m in months:
        s[m] = float(max(0.0, rng.normal(0, 0.5)))
        t = ["N%03d" % i for i in range(n)]
        F = rng.lognormal(-5, 0.8, n)
        zF = GEO.xs_z(F)
        r1 = rng.normal(0, 0.08, n)
        y = gamma1 * s[m] * zF + reversal * s[m] * (-r1 / 0.08) + rng.normal(0, 1, n)
        P["m"][m] = {"t": t, "y": y, "log_me": rng.normal(8, 1, n), "r1": r1, "mom": rng.normal(0.1, 0.3, n), "val": rng.normal(0, 1, n),
                     "sec": np.array(["S%d" % (i % 6) for i in range(n)], object), "me": np.exp(rng.normal(8, 1, n))}
        FR[m] = {"rows": {tt: {"F": float(f)} for tt, f in zip(t, F)}, "X": {tt: float(f) for tt, f in zip(t, F)}}
    return P, FR, s


def _st_card():
    ms = WC.months_between("2016-08", "2026-07")
    P0, FR0, s0 = _synth_panel(WC.SEED, ms)
    r0 = w11_fm(P0, FR0, s0, "synth")
    P1, FR1, s1 = _synth_panel(WC.SEED, ms, gamma1=-0.35)
    r1 = w11_fm(P1, FR1, s1, "synth")
    assert r1["interaction"]["t"] < -2.5 and r1["interaction"]["p_one"] < 0.02, r1["interaction"]
    assert r0["interaction"]["T"] == len(ms) and abs(r0["interaction"]["t"]) < 3.5
    # 반전이 심긴 인공자료 위약(F 효과 없음) — r1 이 통제라 교차항이 반전을 F 로 잡지 않는다
    rr = reversal_placebo()
    assert abs(rr["t"]) < 3.0, rr
    rx = w11_fm(P1, FR1, s1, "synth", key="X")
    assert rx["interaction"]["T"] == len(ms)
    assert _raises(lambda: w11_fm(dict(P1, kind="real"), FR1, s1, "real")) and _raises(lambda: w11_fm(P1, FR1, s1, "blind"))
    import w_core
    rb = w11_fm(P1, FR1, s1, "synth", B=999, seed=WC.SEED)                          # 가족 판정 칸(S11 야생 부트스트랩 p)
    assert rb["interaction"]["p_wild_one"] <= 0.01 and abs(rb["interaction"]["t"] - r1["interaction"]["t"]) < 1e-12
    w02 = {"t": 1.0, "T": 120, "p_wild_one": w_core.one_sided_p(1.0, 120, +1), "B": w_core.WILD_B, "direction": +1}
    w11 = {k: rb["interaction"][k] for k in ("t", "T", "df", "p_wild_one", "direction")}
    w11["B"] = w_core.WILD_B                                                         # 합성 — 등록 반복 칸만 맞춘다(판정 p 는 999 회 값)
    H = w_core.holm_family({"W02": w02, "W11": w11}, "B", alpha=w_core.FAMILY_ALPHA)
    assert H["reject"]["W11"] and not H["reject"]["W02"] and H["m"] == 2
    return "교차항(심은 −효과 t < −2.5 · 효과 0 작음) · 반전 심은 위약(잡지 않음) · X 쌍둥이 · kind 자물쇠 · 가족 B Holm(방향 −1)"


def _st_static():
    r = WG.noeg_static(targets=["w_frag"])
    assert r["ok"], {k: r[k] for k in ("hits", "literal_hits", "unpinned", "separate_violations")}
    import ast
    with io.open(os.path.abspath(__file__), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    calls = [nd for nd in ast.walk(tree) if isinstance(nd, ast.Call) and
             ((isinstance(nd.func, ast.Attribute) and nd.func.attr == "urlopen") or (isinstance(nd.func, ast.Name) and nd.func.id == "urlopen"))]
    assert not calls
    assert WG.unit_violation(WG.unit("sho", use="holding_ratio_denominator")) is None
    return "G-NoEG 정적(w_frag 폐포 %d) · urlopen 없음 · sho 허용 쓰임(13F 보유 비율 분모)" % r["n_reached"]


def selftest():
    res, ok = [], True
    for fn in (_st_dates, _st_13f, _st_ftd_link, _st_math, _st_state, _st_book, _st_card, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                              # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_frag selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--build-ftd" in sys.argv:
        yf = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else FTD_FROM
        r = build_ftd(ym_from=yf)
        print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in r.items()}, ensure_ascii=False))
        print(json.dumps({"deferred": r["deferred"]}, ensure_ascii=False))
        raise SystemExit(0 if not r["deferred"] else 2)
    if "--build-13f" in sys.argv:
        df = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else F13_FROM
        r = build_13f(d_from=df)
        idx = os.path.join(f13_dir(), "_index.json")
        with io.open(idx, "w", encoding="utf-8") as f:
            json.dump({"first_listed": r["first_listed"], "listed": r["listed"], "at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
                      f, ensure_ascii=False)
        print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in r.items()}, ensure_ascii=False))
        print(json.dumps({"deferred": r["deferred"], "first_listed": r["first_listed"]}, ensure_ascii=False))
        raise SystemExit(0 if not r["deferred"] else 2)
    if "--f0" in sys.argv:
        doc, p = f0_main()
        print(json.dumps({"gate": doc["gate"], "activity": doc["activity"], "path": p, "sec": doc["sec"]}, ensure_ascii=False))
        raise SystemExit(0)
    if "--blind-smoke" in sys.argv:
        raise SystemExit(blind_smoke_main())
    if "--manifest" in sys.argv:
        doc, p = manifest()
        print(json.dumps({"n_ftd": len(doc["ftd"]), "n_f13": len(doc["f13"]), "digest": doc["digest"], "path": p}, ensure_ascii=False))
        raise SystemExit(0)
    if "--plan" in sys.argv:
        print(json.dumps(plan(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    print(__doc__)
