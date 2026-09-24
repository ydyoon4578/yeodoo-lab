# -*- coding: utf-8 -*-
"""build/q_eap.py — 배치 Q · Q05 B-EAP1 실적발표 예정월 프리미엄(Frazzini-Lamont 원문 규칙 · 시총가중 · 얇은 달은 지수)
                   + 자식 Q12 SK15 실적발표 프리미엄 + 이익 계절성 단계(역사적으로 큰 분기를 발표하는 종목만 · CHSS 2017 착안 랩 변형)
Q05 = 부류 A(단독 슬리브) · 슬롯 A3(첫 무게 1/8) · Q12 = 부류 C(Q05 자식 · 그래프 간선 1) · 카드 원문 scratchpad/qbatch_final.md «# Q05» «# Q12»
계약 scratchpad/qbatch_contract.md.

근본 이유(Q05): 실적발표가 예정된 달에는 주가가 체계적으로 오른다. 발표 무렵 개인 매수와 거래량이 몰리고 대형 투자자가 이를 앞서 산다(주의 · 수급),
  발표가 시장 전체 이익 정보를 담아 그달 발표 기업의 체계적 위험이 커진다(위험 보상 · Savor-Wilson), 발표로 풀리는 정보 불확실성에 대한 보상이다
  (Barber 외 · 46개국). 모든 종목이 1년에 네 번 들고 나므로 가치 · 규모 · 베타에 쏠리지 않고 «발표 시점» 만 산다.
  반대 증거 — 2004년 8-K 개정 뒤 미국 프리미엄이 8-K 접수일로 옮겨 사라졌다는 워킹페이퍼(Heitz 외 · 카드 인용). 이 슬리브는 그 논쟁을
  2016~2026 S&P 500 대형주에서 가르는 검정이다.
근본 이유(Q12): 기업 이익에는 계절성이 있어 특정 분기에 이익이 늘 크게 나온다. 투자자는 직전의(계절적으로 낮은) 분기에 과하게 무게를 두어
  다음 «큰 분기» 를 비관적으로 예측한다 → 역사적으로 큰 분기를 발표하는 기업은 발표 시점에 높은 수익. 발표 프리미엄(Q05) 위에 예측 가능한
  긍정 서프라이즈를 겹친다 — 섞기가 아니라 «어느 발표 종목을 담을지» 를 좁히는 단계이고, 그 증분(Q12 − Q05)만 판정한다.

규칙(카드 그대로):
  편입 = World.months(2016-08 ~ 2026-07 월말 m) · 보유 t = m + 1 · reb=1 · 편도 10bp · 펀드 90/10(SPY 총수익 · PR 보고).
  유니버스 = pit_panel.union_members(World.universe(m, 'union', False) — 가격 > 0 · 시점 주식수) 중 W['lists']['spx'][m] 에 든 이름(회사당 한 줄 · 날짜 인식 키).
  기록 = data/earn_dates.json 'co' — 명단 티커 → 가격 키 → 점 표기 → cik_spliced 차례. 기록이 없으면 발표 예정자가 아니다.
  발표 예정자(보유월 t): ① 달력 월 t−12 에 8-K 2.02 접수 ≥ 1 ② t−12 ~ t−1 에 서로 다른 접수일 정확히 4 — m 의 마지막 거래일 «전» 접수만(단언).
  선정 = 예정자 ≥ 30 이면 전부 · 아니면 유니버스 전체(능동 베팅 0). 비중 = m 시총 · 한 이름 20% 상한(넘친 몫 비례 · qg_lab.weights 와 같은 반복).
  Q12: 예정자 i 의 «다가오는 회계분기 f» = t−12 달 2.02 접수가 발표한 분기 — 접수 0~100일 전 분기 NI 기간말(회계 Q1~Q3 줄) → 그 분기 ·
    아니면 연간 ni_a 기간말 0~100일 전 → 회계 Q4 · 못 맞추면 단계에서 뺀다.
    점수 S_i = 직전 5 회계연도 중 네 분기가 m 에 90일 지연으로 다 알려진 해(≥ 3 해)의 «그해 네 분기 NI 중 분기 f 의 순위(1..4 · 4 = 가장 큼)» 평균 ·
    Q4 = 연간 NI − (Q1 + Q2 + Q3). 선정 = S_i ≥ 3.0 인 예정자 · 30 미만이면 그달은 Q05 바스켓(Q05 의 얇은 달 대체가 따라온다).
대조(Q05): 비발표 바스켓(유니버스 − 예정자 · 얇은 달은 유니버스 = 슬리브) · C0 = 유니버스 전체 시총가중 ·
  런업 재포장 표시 = x-earngap 월말 스냅숏(마지막 2.02 접수 뒤 ≥ 60 거래일 · 시총가중) — (슬리브 − 유니버스) 를 (스냅숏 − 유니버스) 에 회귀해
  절편 점 추정 ≤ 0 이면 «발표 전 런업 재포장 — 측정만» 상한(관문 = 120개월 절편 · 능동 80 달 회귀는 보고만) · 능동 달(≥ 30) 만의 슬리브 − 비발표 평균 · t(검정력 손실 약 √(2/3) 공개).
  공개(구성만): 쓸 수 있는 기록(창 안 접수 ≥ 1) 커버리지 · 창이 빈 이름(재편 뒤 CIK) · 스냅숏의 낡은 접수자 몫 · 정밀도(카드 92.7% 와의 차이 재현).
위약(Q12): 달마다 적격 예정자(S 가 선 이름) 안에서 S 를 섞고 같은 규칙(1000번 · 씨앗 20260925 + i) — 참 Δ(Q12 − Q05) ≥ 95번째 백분위.

출처: Frazzini & Lamont (2007) «The Earnings Announcement Premium and Trading Volume», NBER w13090 — §II · 표 III(t−12 예측 · 정확히 4번 · 시총가중 ·
  1개월 보유 — 카드가 원문을 열었다). Savor & Wilson (2016) «Earnings Announcements and Systematic Risk», JF 71(1). Barber, De George, Lehavy &
  Trueman (2013) «The earnings announcement premium around the globe», JFE 108(1). Chang, Hartzmark, Solomon & Soltes (2017) «Being Surprised by
  the Unsurprising: Earnings Seasonality and Stock Returns», RFS 30(1) — 초록만(전문을 열지 않았다 · 순위 · S ≥ 3.0 · 0~100일 대응은 랩 선택).

🚨 이 모듈은 규칙 · 대조 · 팔 · 위약의 수익 · 초과 · IR · 샤프 · 적중률을 찍지 않는다. run() 은 한 번 굽기에서만 부른다(러너가 판정).

  python build/q_eap.py --selftest   # 합성 자료 단위 시험(AAPL · WMT · KO 회계 달력 대응 · Q4 포함)
  python build/q_eap.py --probe      # Q12 대응 몫(커버리지만)
  python build/q_eap.py --dry        # 구성만(커버리지 · 개수 · 비중 합 · 한도 · 날짜 · 실제 AAPL/WMT/KO 대응)
  python build/q_eap.py --smoke      # 눈가린 연기 시험(NPERM 3 · 예외 · 시간 · 모양만)
"""
from __future__ import annotations
import bisect, hashlib, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q            # noqa: E402
import tech_backtest as TB         # noqa: E402  FUND_LAG_DAYS · _shift · _ord
import eg30plus as E               # noqa: E402  cap_weights · nw_t · nw_ols · down_t

CARDS = {"Q05": {"cls": "A", "slot": "A3"}, "Q12": {"cls": "C", "slot": "A3", "parent": "Q05"}}
NPERM = 1000                        # Q12 위약 판 수 — 연기 시험에서 작게 덮어쓴다

# ── 카드 상수 ─────────────────────────────────────────────────────────────
N_ANN = 4                           # t−12 ~ t−1 에 서로 다른 2.02 접수일 정확히 4(FL 표 III)
MIN_N = 30                          # 예정자 30 미만이면 유니버스 전체
CAP = 0.20                          # 한 이름 20% 상한(qg_lab 기본)
COST20 = 0.0020                     # 20bp 행
GAP_TD = 60                         # x-earngap 스냅숏 — 마지막 2.02 뒤 ≥ 60 거래일
STALE_TD = 130                      # 진단만(규칙 아님) — 스냅숏 이름 중 마지막 2.02 뒤 > 130 거래일(약 두 분기 건너뜀) = «낡은/비분기 접수자» 몫 공개
CARD_PREC = 0.927                   # 진단만 — 카드 why_keep 의 «t−12 정밀도 92.7%»(dry 의 합산 정밀도와 차이를 공개)
MAP_DAYS = 100                      # Q12 — 기간말이 접수 0~100일 전
S_CUT, S_YEARS, S_MIN = 3.0, 5, 3   # Q12 — S ≥ 3.0 · 직전 5 회계연도 · 최소 3 해
LAG = TB.FUND_LAG_DAYS              # 90일(랩 규약)
FY_IN = 320                         # «같은 회계연도 안» = 연간 기간말 전 320일 미만(q_qmj.quarterly_ni · yoy_pair 규약)
YOY_LO, YOY_HI = 320, 410           # 회계연도 사슬 한 걸음(yoy_pair 규약)
QLEN = 365.25 / 4                   # 분기 길이(일) — 기간말의 회계분기 번호를 날짜 간격으로 센다
REFS = {"AAPL": {1: 1, 2: 1, 4: 2, 5: 2, 7: 3, 8: 3, 10: 4, 11: 4},     # 실제 대응 시험 — 접수 달 → 기대 회계분기(9월 · 1월 · 12월 결산)
        "WMT": {2: 4, 3: 4, 5: 1, 6: 1, 8: 2, 9: 2, 11: 3, 12: 3},
        "KO": {1: 4, 2: 4, 3: 4, 4: 1, 5: 1, 7: 2, 8: 2, 10: 3, 11: 3}}

INTERP = [
    "유니버스 = World.universe(m, 'union', False)(union_members + 가격 > 0 + 시점 주식수) 중 명단 티커가 W['lists']['spx'][m] 에 있는 이름 — "
    "카드 «union_members filtered to spx» 그대로(dry 에서 World.universe(m, 'spx', False) 와 같은지 잰다).",
    "«t−12 ~ t−1» = 보유월 t = m + 1 이므로 달력 월 m − 11 ~ m · 접수일 문자열 < LTD(m) 만(같은 날 접수는 뺀다) · 8-K/A 도 기록에 있으면 같은 날은 하나로 센다(서로 다른 날).",
    "비중 = eg30plus.cap_weights(시총 · 20%) — qg_lab.weights 와 같은 넘친 몫 비례 재배분 반복. 이름이 5 미만이면 20% 가 설 수 없어 비례 그대로(스냅숏만 해당 · dry 기록).",
    "기록 커버리지 = 키가 있는 몫은 100% 지만 «쓸 수 있는 기록»(창 m − 11 ~ m 에 LTD 전 접수 ≥ 1)은 수 기준 97.6~99.8% 다. 창이 빈 이름 30 종 · 492 이름-달 — "
    "XOM(120 달 전부 · 기록 CIK 2115436 첫 접수 2026-07-31) · BLK(98 · 2024-10 전) · APA(57) · XRX(37) · CI(33) · DIS(33) · AVGO(22) · DD(13) 등은 "
    "index_history 가 재편 뒤 지주회사 CIK 로 잇고 그 CIK 의 2.02 이력이 재편에서 시작해서다(EVHC · BWA · FLS 는 옛 CIK 의 기록 공백). "
    "카드 «기록이 없으면 예정자가 아니다» 를 문자 그대로 둔다 — 앞 CIK 기록 보강은 핀 박힌 earn_dates 를 바꾸므로 새 핀 등록이 필요해 이번 굽기 밖이다. "
    "이들은 절대 예정자가 못 되고 능동 달엔 늘 비발표 대조에 든다(시총 몫 0.7~4.0% · 능동 달 비발표 대조 안 비중 중앙 2.1% · 최대 9.3%) — 달별 값은 log05['usable_record'].",
    "비발표 대조 = 능동 달에는 유니버스 − 예정자(기록 없는 · 창이 빈 이름 포함) · 얇은 달은 유니버스 전체(카드). G4 = 전 달 (X_규칙 − X_비발표) 평균 > 0 이고 NW(3) t ≥ 1.0(펀드 초과 차 · q_qmj C1 과 같은 잣대).",
    "런업 스냅숏 = 유니버스 중 기록이 있고 LTD(m) «전» 마지막 2.02 접수일에서 LTD(m) 까지 거래일 ≥ 60(카드 «at least 60» · x-earngap 엔진은 > 60 · 접수일이 휴장일이면 다음 거래일로 센다) · "
    "시총가중 20% 상한(Q05 틀과 같은 비중 규약 — 카드는 «cap-weighted» 만 적었다) · 그달 스냅숏이 비면 유니버스(차 0).",
    "스냅숏은 얇다(중앙 12 종 · 17 달은 5 종 미만이라 20% 상한이 못 선다). 게다가 발표 전 이름만이 아니라 비분기 · 낡은 기록 접수자도 카드 · x-earngap 정의 그대로 든다 — "
    "TROW(2022 까지 2.02 연 1회) · BRK-B(2017 까지 불규칙) · FLS · BWA(2018 공백) · EVHC(2016-11 뒤 기록 끊김) · SATS/ECHO(2017-02 뒤 끊김) · AES(2025-11 뒤 끊김). "
    "마지막 2.02 뒤 > 130 거래일(약 두 분기 건너뜀 · 진단 문턱일 뿐 규칙 아님) 이름이 120 달 중 60 달에 있고, 15 달은 그 몫이 스냅숏 비중의 20% 이상이다"
    "(2019-03 BWA 60% · 2018-03 BWA+EVHC 40% · 2026-06 AES+ECHO 40%). 런업 회귀의 설명변수 잡음이 크고 그 회귀가 표시 상한을 정한다는 것을 알고 읽을 것. 달별 몫은 log05['snapshot_stale'].",
    "런업 회귀 = 슬리브 월 수익(fund_from_path 'basket' · 비용 뺀 뒤 %) 기준 y = Q05 − C0 · x = 스냅숏 − C0 · 120개월 절편 포함 OLS(eg30plus.nw_ols · NW 3) · 절편 ≤ 0 이면 label_caps['runup_repack'] = True. "
    "🚨 관문은 이 120개월 절편이다(사전등록에 박는다 · 카드는 달을 적지 않았다 — 가장 문자 그대로의 읽기). 얇은 40 달은 목표가 C0 와 같아 y ≈ 0(비용 · 드리프트 차만)이라 "
    "기울기를 0 쪽으로 끌고 절편을 옮기므로, 능동 80 달만의 같은 회귀를 log05['runup_active_report_only'] 에 보고만 한다(갈림길 공개 · 상한에 쓰지 않는다).",
    "능동 달 기전 행 = 편입 m 에 예정자 ≥ 30 인 보유월만의 (X_규칙 − X_비발표) 평균 · 달력 HAC(eg30plus.down_t 에 능동 마스크) 와 부분열 NW t 둘 다 싣는다(보고만).",
    "예측 정밀도 = 예정자 중 보유월 t 에 실제 2.02 접수가 있는 몫(진단만 — 비중에 쓰지 않는다 · earn_dates 가 2026-08-18 에 끝나 2026-08 은 덜 찼다). "
    "유니버스 · 보유 2016-09 ~ 2026-07 에서 0.898 로 카드 why_keep 의 92.7% 와 다르다. 92.7% 는 «모든 기록 · 보유 2009-01 ~ 2026-07 · LTD 당일 접수까지 셈»(카드 비판 1 수정 전 정의)으로 재현되고, "
    "같은 바탕에 엄격 컷(< LTD)을 걸면 0.898 이다 — 차이는 유니버스가 아니라 엄격 컷 탓이다(LTD 당일 접수 이름이 4 번으로 잡혀 예정자가 되지만 실제 발표는 m 에 끝났다). "
    "빗나감 갈래는 log05['precision_detail'].",
    "Q12 분기 NI 줄 = ni 버킷 중 연간(ni_a) 기간말과 같은 날짜 줄을 뺀 것 — 🚨 카드 «ni 분기 버킷에 회계 Q4 줄이 없다» 는 틀렸다(snap 에서 663 중 476 회사 · 4,563 줄이 연간 기간말에 직접 Q4 태그). "
    "빼지 않으면 «분기 먼저» 규칙이 Q4 발표를 Q1~Q3 으로 잡는다. Q4 값은 카드대로 연간 − (Q1 + Q2 + Q3)(직접 태그는 쓰지 않는다).",
    "회계분기 번호 = 기간말 p 의 직전 연간 기간말 Y_prev(< p)에서 간격 g · f = 반올림(g / (365.25/4)) · g < 320 이고 f ∈ {1,2,3} 인 줄만 «회계 Q1~Q3 줄»(f = 4 로 나오는 줄은 날짜가 어긋난 직접 Q4 태그라 없는 것으로 친다). "
    "과거 해의 칸도 같은 식(연간 기간말 Y 에서 거꾸로 4 − 반올림(간격/분기 길이) · 칸 1·2·3 이 정확히 하나씩일 때만 그해가 완결).",
    "t−12 달에 2.02 접수가 둘 이상이면 날짜 순으로 처음 대응되는 것을 쓴다(나머지는 기록만). 한 접수에 0~100일 분기 줄이 여럿이면 가장 늦은 기간말.",
    "«직전 5 회계연도» = m 말 − 90일까지 기간말이 선 가장 최근 ni_a 부터 320~410일 걸음(365 에 가장 가까운 것)으로 거슬러 간 5 해(q_qmj.fy_chain 과 같은 사슬 · 중간 해가 비면 사슬이 멈춰 해가 줄어든다) · "
    "그중 네 분기가 다 선 해 ≥ 3 이어야 S 가 선다. 같은 분기값 순위는 평균 순위.",
    "재무는 마지막 제출값(P-FF 첫 제출 재구성은 저장소에 제출일 붙은 원 companyfacts 가 없어 못 만든다 — q_qmj 와 같은 사유) → 재작성 누출이 남는다 · 첫 제출 재실행이 G5 필수(pff_same_sign = pending).",
    "Q12 위약 = 달마다 «S 가 선 예정자»(키 정렬) 안에서 S 값을 rng.permutation 으로 섞고 같은 선정(≥ 3.0 · 30 미만이면 Q05) — S ≥ 3.0 개수가 달마다 보존되어 대체 달이 참 규칙과 같다. "
    "통계 = 전 달 평균(X_위약 − X_Q05) · 참값 = 평균(X_Q12 − X_Q05) · «95번째 백분위» = np.quantile(draws, 0.95)(선형 보간).",
    "Q05 F0 = earn_dates 의 마지막 접수일 ≥ 마지막 편입의 LTD 전날까지 덮는가(카드 «낡은 기록은 전방 달 측정 불가») · Q12 F0 = Q12 가 Q05 와 한 달이라도 다른가(아니면 Δ ≡ 0 이라 잴 수 없다) — 카드에 F0 문구가 없어 구조만.",
]


# ── 작은 도구 ─────────────────────────────────────────────────────────────
def _days(a, b):
    """b − a (일 · 부호 있음)."""
    return TB._ord(b) - TB._ord(a)


def _rnd(x):
    return int(math.floor(x + 0.5))


def load_earn():
    """{기록 키: 서로 다른 접수일 오름차순} · 기록 전체의 마지막 접수일."""
    d = Q.load("earn_dates.json")
    co = {t: sorted(set(v)) for t, v in sorted((d.get("co") or {}).items()) if v}
    return co, max(v[-1] for v in co.values())


def record(W, ED, t, k):
    """카드 차례 — 명단 티커 → 가격 키 → 점 표기 → cik_spliced. → (출처, 기록 키, 접수일)."""
    for src, c in (("t", t), ("k", k), ("dot", (t or "").replace("-", ".")), ("splice", W["splice"].get(t))):
        if c and c in ED:
            return src, c, ED[c]
    return None, None, []


def announcer(dates, m, ltd):
    """보유월 t = m + 1 의 발표 예정자인가 — ① 달력 월 t−12(= m − 11) 에 ≥ 1 ② m − 11 ~ m 에 서로 다른 접수일 정확히 4 · 접수일 < ltd 만."""
    lo = Q.mshift(m, -11)
    used = [d for d in dates if lo <= d[:7] <= m and d < ltd]
    flag = len(used) == N_ANN and any(d[:7] == lo for d in used)
    return flag, used


def last_before(dates, ltd):
    """ltd 전 마지막 접수일(없으면 None)."""
    j = bisect.bisect_left(dates, ltd)
    return dates[j - 1] if j > 0 else None


def td_gap(grid, d, i):
    """접수일 d 에서 격자 자리 i 까지 거래일 수 — d 가 휴장일이면 다음 거래일부터 센다."""
    return i - bisect.bisect_left(grid, d)


def cap_w(keys, mc):
    """시총 비례 + 한 이름 20% 상한(eg30plus.cap_weights) — 키 정렬 순서로 넣는다."""
    return E.cap_weights({k: mc[k] for k in sorted(keys)}, CAP)


def targets_hash(T):
    return hashlib.sha256(json.dumps(T, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def target_turn(T):
    """목표 대 목표 편도 회전(드리프트 없음 · 구조만) — 달 평균 × 12."""
    ms = sorted(T)
    tt = [0.5 * sum(abs(T[b]["w"].get(k, 0.0) - T[a]["w"].get(k, 0.0)) for k in sorted(set(T[a]["w"]) | set(T[b]["w"]))) for a, b in zip(ms, ms[1:])]
    return float(np.mean(tt) * 12) if tt else None


# ── Q12 회계분기 대응 · 계절 점수 ─────────────────────────────────────────
def _ann_dates(f):
    return sorted({d for d, v in (f.get("ni_a") or []) if v is not None})


def q13_rows(f, lt):
    """회계 Q1~Q3 분기 NI 줄 {기간말: (분기 번호, 값)} — 기간말 < lt · 연간 기간말과 같은 날 줄은 뺀다 · 번호 = 직전 연간 기간말에서 간격/분기 길이."""
    ann = _ann_dates(f)
    aset = set(ann)
    out = {}
    for d, v in sorted(f.get("ni") or []):
        if v is None or d in aset or d >= lt:
            continue
        j = bisect.bisect_left(ann, d)
        if j == 0:
            continue
        g = _days(ann[j - 1], d)
        fq = _rnd(g / QLEN)
        if g < FY_IN and fq in (1, 2, 3):
            out[d] = (fq, float(v))
    return out


def map_quarter(f, filings, ltd):
    """t−12 달 접수(들) → (회계분기 f, 쓴 접수일, 기간말, 'q'|'a') 또는 None. 기간말 · 접수일은 모두 < ltd(단언)."""
    q = q13_rows(f, ltd)
    ann = [y for y in _ann_dates(f) if y < ltd]
    for F in sorted(filings):
        assert F < ltd, "접수일 %s ≥ LTD %s" % (F, ltd)
        qc = [p for p in q if p <= F and _days(p, F) <= MAP_DAYS]
        if qc:
            p = max(qc)
            return q[p][0], F, p, "q"
        ac = [y for y in ann if y <= F and _days(y, F) <= MAP_DAYS]
        if ac:
            return 4, F, max(ac), "a"
    return None


def fy_chain(ann_desc, n):
    """연간 기간말(내림차순)에서 FY*, FY*−1, … 최대 n 해 — 한 걸음 320 ~ 410일(365 에 가장 가까운 것 · 같으면 최근). 빈 해에서 멈춘다."""
    if not ann_desc:
        return []
    ch = [ann_desc[0]]
    while len(ch) < n:
        cur, best = ch[-1], None
        for d in ann_desc:
            if d >= cur:
                continue
            g = _days(d, cur)
            if g > YOY_HI:
                break
            if g >= YOY_LO and (best is None or abs(g - 365) < abs(best[0] - 365)):
                best = (g, d)
        if best is None:
            break
        ch.append(best[1])
    return ch


def season_score(f, fq, cut):
    """S = 직전 5 회계연도(기간말 ≤ cut) 중 네 분기가 다 선 해의 분기 fq 순위(1..4 · 4 = 가장 큼 · 같으면 평균 순위) 평균 · 해 < 3 이면 None.
    → (S, 쓴 해 수, 쓴 기간말 최댓값)."""
    from scipy.stats import rankdata
    na = {d: float(v) for d, v in (f.get("ni_a") or []) if v is not None and d <= cut}
    ch = fy_chain(sorted(na, reverse=True), S_YEARS)
    aset = set(_ann_dates(f))
    qv = {d: float(v) for d, v in (f.get("ni") or []) if v is not None and d <= cut and d not in aset}
    ranks, umax = [], None
    for Y in ch:
        slots = {}
        for d, v in qv.items():
            g = _days(d, Y)
            if 0 < g < FY_IN:
                s = 4 - _rnd(g / QLEN)
                if s in (1, 2, 3):
                    slots.setdefault(s, []).append((d, v))
        if sorted(slots) != [1, 2, 3] or any(len(x) != 1 for x in slots.values()):
            continue
        vals = [slots[1][0][1], slots[2][0][1], slots[3][0][1]]
        vals.append(na[Y] - sum(vals))
        ranks.append(float(rankdata(np.array(vals), method="average")[fq - 1]))
        umax = Y if umax is None or Y > umax else umax
    if len(ranks) >= S_MIN:
        return float(np.mean(ranks)), len(ranks), umax
    return None, len(ranks), umax


# ── 달 원자료 ─────────────────────────────────────────────────────────────
def _ED(Wd):
    if "_eap_ed" not in Wd.__dict__:
        Wd._eap_ed = load_earn()
    return Wd._eap_ed


def month_frame(Wd, m):
    """달 m 말 결정 — 유니버스 · 시총 · 기록 · 예정자 · 마지막 접수 뒤 거래일 · Q12 대응 · 점수. 날짜 단언을 여기서 건다."""
    cache = Wd.__dict__.setdefault("_eap_frame", {})
    if m in cache:
        return cache[m]
    W = Wd.W
    ED, _ = _ED(Wd)
    i = Wd.me[m]
    ltd = Wd.dates[i]
    cut = TB._shift(ltd, LAG)
    assert ltd[:7] == m and (i + 1 >= len(Wd.dates) or Wd.dates[i + 1][:7] != m), "월말 자리가 그달 마지막 거래일이 아니다 %s" % m
    spx = set(W["lists"]["spx"].get(m) or [])
    U = sorted(((t, k) for t, k in Wd.universe(m, "union", False) if t in spx), key=lambda x: x[1])
    keys = [k for _, k in U]
    assert len(set(keys)) == len(keys), "유니버스 가격 키 중복 %s" % m
    names, mc, src, ann, gap, used_max, ann_next = {}, {}, {}, [], {}, None, {}
    fq, S, nyrs, mapinfo, nwin, rkey = {}, {}, {}, {}, {}, {}
    n_multi, fund_max = 0, None
    lo = Q.mshift(m, -11)
    t_hold = Q.mshift(m, 1)
    for t, k in U:
        names[k] = t
        mc[k] = Wd.mcap(t, k, i)
        assert mc[k] and mc[k] > 0 and Wd.PX[k][i] > 0, "시총 · 가격이 없는 유니버스 이름 %s %s" % (m, k)
        s, rk, ds = record(W, ED, t, k)
        src[k], rkey[k] = s, rk
        flag, used = announcer(ds, m, ltd)
        nwin[k] = len(used)                                     # 창(m − 11 ~ m · < LTD) 안 접수 수 — 0 이면 «쓸 수 없는 기록»(진단만)
        for d in used:
            assert d < ltd, "접수일 %s ≥ LTD %s (%s)" % (d, ltd, k)
            used_max = d if used_max is None or d > used_max else used_max
        lb = last_before(ds, ltd)
        if lb is not None:
            assert lb < ltd
            gap[k] = td_gap(Wd.dates, lb, i)
        if not flag:
            continue
        ann.append(k)
        ann_next[k] = any(d[:7] == t_hold for d in ds)          # 진단만(미래 자료 — 비중에 쓰지 않는다)
        f = Wd.fund(t, k) or {}
        fil = [d for d in used if d[:7] == lo]
        n_multi += len(fil) > 1
        mp = map_quarter(f, fil, ltd)
        if mp is None:
            continue
        fq[k] = mp[0]
        mapinfo[k] = {"f": mp[0], "filing": mp[1], "pe": mp[2], "via": mp[3]}
        assert mp[1] < ltd and mp[2] < ltd, "Q12 대응 날짜가 LTD 를 넘는다 %s %s" % (m, k)
        sv, ny, um = season_score(f, mp[0], cut)
        nyrs[k] = ny
        if um is not None:
            assert um <= cut < ltd, "Q12 재무 기간말 %s 가 컷 %s 을 넘는다(%s)" % (um, cut, m)
            fund_max = um if fund_max is None or um > fund_max else fund_max
        if sv is not None:
            S[k] = sv
    R = {"m": m, "i": i, "ltd": ltd, "cut": cut, "keys": keys, "names": names, "mc": mc, "src": src, "ann": sorted(ann), "gap": gap,
         "used_max": used_max, "ann_next": ann_next, "fq": fq, "S": S, "nyrs": nyrs, "map": mapinfo, "n_multi": n_multi, "fund_max": fund_max,
         "nwin": nwin, "rkey": rkey}
    cache[m] = R
    return R


# ── 목표 비중 ─────────────────────────────────────────────────────────────
def _tg(keys, R):
    w = cap_w(keys, R["mc"])
    return {"w": w, "names": {k: R["names"][k] for k in w}}


def active(R):
    return len(R["ann"]) >= MIN_N


def sel_q05(R):
    return R["ann"] if active(R) else R["keys"]


def sel_nonann(R):
    if not active(R):
        return R["keys"]
    a = set(R["ann"])
    return [k for k in R["keys"] if k not in a]


def sel_snap(R):
    s = [k for k in R["keys"] if R["gap"].get(k) is not None and R["gap"][k] >= GAP_TD]
    return s if s else R["keys"]


def sel_q12(R, S=None):
    """S ≥ 3.0 인 예정자 · 30 미만이면 Q05 바스켓. S 를 주면(위약) 그 점수로."""
    S = R["S"] if S is None else S
    s = sorted(k for k, v in S.items() if v >= S_CUT)
    return (s, True) if len(s) >= MIN_N else (sel_q05(R), False)


def targets(Wd, which):
    """which: 'Q05' · 'nonann' · 'C0' · 'snap' · 'Q12' → {편입월: 목표}."""
    f = {"Q05": sel_q05, "nonann": sel_nonann, "C0": lambda R: R["keys"], "snap": sel_snap, "Q12": lambda R: sel_q12(R)[0]}[which]
    return {m: _tg(f(month_frame(Wd, m)), month_frame(Wd, m)) for m in Wd.months}


def perm_prep(Wd):
    """위약 준비 — 달마다 S 가 선 예정자(키 정렬) · S 값."""
    P = {}
    for m in Wd.months:
        R = month_frame(Wd, m)
        ks = sorted(R["S"])
        P[m] = {"keys": ks, "s": np.array([R["S"][k] for k in ks], float), "R": R}
    return P


def perm_targets(P, rng):
    """S 를 적격 예정자 안에서 섞고 같은 규칙. rng=None 이면 섞지 않는다(참 규칙과 같아야 한다)."""
    T = {}
    for m in sorted(P):
        p = P[m]
        s = p["s"] if rng is None else p["s"][rng.permutation(len(p["s"]))]
        sel, _ = sel_q12(p["R"], {k: float(v) for k, v in zip(p["keys"], s)})
        T[m] = _tg(sel, p["R"])
    return T


# ── 단위 시험(합성 자료만) ─────────────────────────────────────────────────
def _synthetic_calendars():
    """AAPL(9월 마지막 토요일 결산 · 52/53주) · WMT(1월 31일) · KO(12월 31일 · 분기말은 금요일) 의 실제 모양을 본뜬 합성 회계 달력 ·
    분기 NI(연간 기간말 날짜의 직접 Q4 태그 포함 — snap 의 ni 버킷 모양) · 2.02 접수일. 값은 손으로 정한 합성 수."""
    cal = {
        "AAPL": {"ann": ["2013-09-28", "2014-09-27", "2015-09-26", "2016-09-24"],
                 "q": [("2013-12-28", "2014-01-27"), ("2014-03-29", "2014-04-23"), ("2014-06-28", "2014-07-22"), ("2014-09-27", "2014-10-20"),
                       ("2014-12-27", "2015-01-27"), ("2015-03-28", "2015-04-27"), ("2015-06-27", "2015-07-21"), ("2015-09-26", "2015-10-27"),
                       ("2015-12-26", "2016-01-26"), ("2016-03-26", "2016-04-26"), ("2016-06-25", "2016-07-26"), ("2016-09-24", "2016-10-25")]},
        "WMT": {"ann": ["2014-01-31", "2015-01-31", "2016-01-31", "2017-01-31"],
                "q": [("2014-04-30", "2014-05-15"), ("2014-07-31", "2014-08-14"), ("2014-10-31", "2014-11-13"), ("2015-01-31", "2015-02-19"),
                      ("2015-04-30", "2015-05-19"), ("2015-07-31", "2015-08-18"), ("2015-10-31", "2015-11-17"), ("2016-01-31", "2016-02-18"),
                      ("2016-04-30", "2016-05-19"), ("2016-07-31", "2016-08-18"), ("2016-10-31", "2016-11-17"), ("2017-01-31", "2017-02-21")]},
        "KO": {"ann": ["2013-12-31", "2014-12-31", "2015-12-31", "2016-12-31"],
               "q": [("2014-03-28", "2014-04-15"), ("2014-06-27", "2014-07-22"), ("2014-09-26", "2014-10-21"), ("2014-12-31", "2015-02-10"),
                     ("2015-04-03", "2015-04-22"), ("2015-07-03", "2015-07-22"), ("2015-10-02", "2015-10-21"), ("2015-12-31", "2016-02-09"),
                     ("2016-04-01", "2016-04-20"), ("2016-07-01", "2016-07-27"), ("2016-09-30", "2016-10-26"), ("2016-12-31", "2017-02-09")]},
    }
    out = {}
    for tk, c in cal.items():
        ann = set(c["ann"])
        ni, fil, want = [], [], []
        for j, (pe, fd) in enumerate(c["q"]):
            fq = (j % 4) + 1
            ni.append((pe, 10.0 + fq))                        # 분기 fq 의 값 = 10 + fq(Q4 직접 태그 포함)
            fil.append(fd)
            want.append((fd, fq, pe))
        ni_a = [(y, 0.0) for y in sorted(ann)]
        out[tk] = {"f": {"ni": sorted(ni, reverse=True), "ni_a": sorted(ni_a, reverse=True)}, "filings": fil, "want": want}
    return out


def selftest():
    T = {}
    # 발표 예정자 — 정확히 4 · t−12 달 필수 · LTD 당일 접수 제외
    f1, u1 = announcer(["2015-09-10", "2015-12-10", "2016-03-10", "2016-06-10", "2016-08-31"], "2016-08", "2016-08-31")
    T["ann_strict_ltd"] = (f1 is True and u1 == ["2015-09-10", "2015-12-10", "2016-03-10", "2016-06-10"])   # LTD 당일 접수는 빠져 4번
    f2, _ = announcer(["2015-09-10", "2015-12-10", "2016-03-10", "2016-06-10", "2016-08-30"], "2016-08", "2016-08-31")
    T["ann_five_is_not4"] = f2 is False
    f3, _ = announcer(["2015-10-10", "2015-12-10", "2016-03-10", "2016-06-10"], "2016-08", "2016-08-31")
    T["ann_needs_t12"] = f3 is False                       # 4번이지만 t−12(2015-09) 달이 비었다
    f4, _ = announcer(["2015-08-31", "2015-09-10", "2015-12-10", "2016-03-10", "2016-06-10"], "2016-08", "2016-08-31")
    T["ann_window_lo"] = f4 is True                         # 2015-08 은 창 밖
    # 마지막 접수 · 거래일 간격(휴장일 접수는 다음 거래일)
    grid = ["2016-01-04", "2016-01-05", "2016-01-06", "2016-01-08", "2016-01-11"]
    T["td_gap"] = td_gap(grid, "2016-01-07", 4) == 1 and td_gap(grid, "2016-01-04", 4) == 4 and last_before(["2016-01-04", "2016-01-11"], "2016-01-11") == "2016-01-04"
    # 기록 찾기 차례
    Wf = {"splice": {"FB": "META"}}
    EDf = {"META": ["x"], "BRK.B": ["y"], "ABC": ["z"]}
    T["record_order"] = (record(Wf, EDf, "FB", "FB")[0] == "splice" and record(Wf, EDf, "BRK-B", "BRK.B")[0] == "k"
                         and record(Wf, EDf, "BRK-B", "ZZZ")[0] == "dot" and record(Wf, EDf, "ABC", "ABC")[0] == "t" and record(Wf, EDf, "Q", "Q")[0] is None)
    # 20% 상한
    mcs = {chr(65 + j): float(100 - 7 * j) for j in range(12)}
    mcs["A"] = 5000.0
    w = cap_w(list(mcs), mcs)
    T["cap_weights"] = abs(sum(w.values()) - 1) < 1e-12 and max(w.values()) <= CAP + 1e-12
    # Q12 대응 — AAPL · WMT · KO 합성 달력 · Q4 포함(연간 기간말 날짜의 직접 Q4 태그가 Q1~Q3 으로 잡히면 안 된다)
    cal = _synthetic_calendars()
    ok_map, n_q4 = True, 0
    for tk, c in cal.items():
        for fd, want, pe in c["want"]:
            got = map_quarter(c["f"], [fd], Q.mshift(fd[:7], 2) + "-01")
            ok_map &= got is not None and got[0] == want and got[2] == pe
            n_q4 += want == 4
    T["map_AAPL_WMT_KO_incl_Q4"] = bool(ok_map) and n_q4 == 9
    # 직접 Q4 태그를 빼지 않으면(카드 문자 그대로) AAPL Q4 발표가 Q1~Q3 줄로 잡힌다 — 뺀 판만 맞는지 대조
    fa = cal["AAPL"]["f"]
    T["map_q4_tag_excluded"] = map_quarter(fa, ["2015-10-27"], "2015-11-30")[:2] == (4, "2015-10-27") and "2015-09-26" not in q13_rows(fa, "2099-12-31")
    # 접수 0~100일 창 — 기간말 101일 뒤 접수는 대응 안 됨 · 접수일 ≥ LTD 는 단언으로 막는다
    fz = {"ni": [("2015-03-31", 1.0)], "ni_a": [("2014-12-31", 4.0)]}
    T["map_window"] = map_quarter(fz, ["2015-07-10"], "2099-12-31") is None and map_quarter(fz, ["2015-07-09"], "2099-12-31")[0] == 1
    try:
        map_quarter(fz, ["2015-04-20"], "2015-04-20")
        T["map_ltd_assert"] = False
    except AssertionError:
        T["map_ltd_assert"] = True
    # 계절 점수 — 분기 값 10+fq 이면 Q4 = 연간 − (Q1+Q2+Q3) 로 순위가 정해진다
    f = {"ni_a": [("2016-12-31", 100.0), ("2015-12-31", 100.0), ("2014-12-31", 100.0), ("2013-12-31", 100.0), ("2012-12-31", 100.0), ("2011-12-31", 100.0)],
         "ni": []}
    for y in range(2011, 2017):
        f["ni"] += [("%d-03-31" % y, 30.0), ("%d-06-30" % y, 10.0), ("%d-09-30" % y, 20.0), ("%d-12-31" % y, 777.0)]   # Q4 = 100 − 60 = 40(직접 태그 777 은 안 쓴다)
    f["ni"].sort(reverse=True)
    s4, n4, u4 = season_score(f, 4, "2017-06-01")
    s1, _, _ = season_score(f, 1, "2017-06-01")
    s2, _, _ = season_score(f, 2, "2017-06-01")
    T["season_rank"] = s4 == 4.0 and s1 == 3.0 and s2 == 1.0 and n4 == 5 and u4 == "2016-12-31"
    s_cut, n_cut, _ = season_score(f, 4, "2015-06-01")         # 기간말 ≤ 컷만 — 2014 · 2013 · 2012 · 2011 · (2010 없음) → 4 해
    T["season_pit"] = n_cut == 4 and s_cut == 4.0
    f_few = {"ni_a": f["ni_a"][:2], "ni": [x for x in f["ni"] if x[0] >= "2015-01-01"]}
    T["season_min3"] = season_score(f_few, 4, "2017-06-01")[0] is None
    f_gap = {"ni_a": f["ni_a"], "ni": [x for x in f["ni"] if not x[0].startswith("2015-06")]}
    T["season_incomplete_year"] = season_score(f_gap, 4, "2017-06-01")[1] == 4
    # 위약 — 섞어도 S 값 묶음 보존 · 씨앗이 같으면 같다 · 섞지 않으면 참 규칙
    keys = ["k%02d" % j for j in range(60)]
    Rf = {"keys": keys, "ann": keys[:50], "mc": {k: float(1 + (j * 37) % 17) for j, k in enumerate(keys)}, "names": {k: k.upper() for k in keys},
          "S": {k: (1.0 + (j % 7) * 0.5) for j, k in enumerate(keys[:50])}}
    Pm = {"2016-08": {"keys": sorted(Rf["S"]), "s": np.array([Rf["S"][k] for k in sorted(Rf["S"])]), "R": Rf}}
    t0 = perm_targets(Pm, None)["2016-08"]
    T["perm_identity"] = sorted(t0["w"]) == sorted(sel_q12(Rf)[0])
    t1 = perm_targets(Pm, np.random.default_rng(Q.SEED + 1))["2016-08"]
    t1b = perm_targets(Pm, np.random.default_rng(Q.SEED + 1))["2016-08"]
    T["perm_seed"] = t1 == t1b and abs(sum(t1["w"].values()) - 1) < 1e-12 and len(t1["w"]) == len(t0["w"])
    T["q12_fallback"] = sel_q12(dict(Rf, S={k: 1.0 for k in keys[:50]}))[1] is False and sel_q12(dict(Rf, S={k: 1.0 for k in keys[:50]}))[0] == Rf["ann"]
    T["hash_stable"] = targets_hash({"b": {"w": {"y": 0.5, "x": 0.5}}}) == targets_hash({"b": {"w": {"x": 0.5, "y": 0.5}}})
    return {"ok": all(bool(v) for v in T.values()), "tests": {k: bool(v) for k, v in T.items()}}


# ── 구성 점검(수익 없음) ───────────────────────────────────────────────────
def _check_targets(Wd, T, tag, nmin=1, cap=True):
    out = {"n_min": None, "n_max": None, "max_w": 0.0, "cap_breach_months": 0}
    for m, tg in T.items():
        i = Wd.me[m]
        w = tg["w"]
        s = sum(w.values())
        assert abs(s - 1.0) < 1e-9, "%s %s 비중 합 %.12f" % (tag, m, s)
        assert all(Wd.PX[k][i] == Wd.PX[k][i] and Wd.PX[k][i] > 0 for k in w), "%s %s 가격 없는 목표" % (tag, m)
        assert len(w) >= nmin, "%s %s 보유 %d < %d" % (tag, m, len(w), nmin)
        if max(w.values()) > CAP + 1e-9:
            assert len(w) < 5 or not cap, "%s %s 최대 비중 %.4f > 20%%" % (tag, m, max(w.values()))
            out["cap_breach_months"] += 1
        n = len(w)
        out["n_min"] = n if out["n_min"] is None else min(out["n_min"], n)
        out["n_max"] = n if out["n_max"] is None else max(out["n_max"], n)
        out["max_w"] = max(out["max_w"], max(w.values()))
    out["turn_target"] = target_turn(T)
    out["hash"] = targets_hash(T)[:16]
    return out


def month_log(Wd, T05, T12, Tn=None, Ts=None):
    """편입별 진단(구조만) — 유니버스 · 기록 · 쓸 수 있는 기록 · 예정자 · 능동 · 보유 · 최대 비중(상한 전/후) · 목표 회전 · 스냅숏(낡은 몫) · 정밀도 · Q12 대응."""
    rows, p05, p12 = [], None, None
    for m in Wd.months:
        R = month_frame(Wd, m)
        w, w12 = T05[m]["w"], T12[m]["w"]
        held = sorted(w)
        mcs = sum(R["mc"][k] for k in held)
        tot = sum(R["mc"].values())
        n_rec = sum(1 for k in R["keys"] if R["src"][k] is not None)
        # 쓸 수 있는 기록 = 창(m − 11 ~ m · < LTD) 안 접수 ≥ 1 — 키가 있어도 창이 비면 절대 예정자가 못 된다(재편 뒤 지주회사 CIK 등)
        empty = [k for k in R["keys"] if R["nwin"].get(k, 0) == 0]
        wn = Tn[m]["w"] if Tn is not None else None
        sn = sel_snap(R)
        snap_real = sn is not R["keys"]
        stale = [k for k in sn if snap_real and R["gap"].get(k, 0) > STALE_TD]
        ws = Ts[m]["w"] if Ts is not None else None
        s12, act12 = sel_q12(R)
        na = len(R["ann"])
        rows.append({"m": m, "ltd": R["ltd"], "n_univ": len(R["keys"]), "n_rec": n_rec, "rec_cov": round(n_rec / len(R["keys"]), 4),
                     "rec_src": {s: sum(1 for k in R["keys"] if R["src"][k] == s) for s in ("t", "k", "dot", "splice")},
                     "n_usable": len(R["keys"]) - len(empty), "usable_cov": round(1 - len(empty) / len(R["keys"]), 4),
                     "empty_rec": [R["names"][k] for k in empty], "empty_cap_share": round(sum(R["mc"][k] for k in empty) / tot, 5),
                     "nonann_empty_w": (round(float(sum(wn.get(k, 0.0) for k in empty)), 5) if wn is not None else None),
                     "snap_stale": [R["names"][k] for k in stale], "snap_stale_w": (round(float(sum(ws.get(k, 0.0) for k in stale)), 5) if ws is not None else None),
                     "snap_max_gap": (max(R["gap"][k] for k in sn) if snap_real else None),
                     "n_ann": na, "ann_cov_w": round(sum(R["mc"][k] for k in R["ann"]) / tot, 4), "active": active(R),
                     "n_held": len(held), "max_w_pre": round(max(R["mc"][k] for k in held) / mcs, 5), "max_w": round(max(w.values()), 5),
                     "turn": (round(0.5 * sum(abs(w.get(k, 0) - p05.get(k, 0)) for k in sorted(set(w) | set(p05))), 5) if p05 is not None else None),
                     "n_nonann": len(sel_nonann(R)), "n_snap": (len(sn) if sn is not R["keys"] else 0),
                     "precision": (round(sum(R["ann_next"].values()) / na, 4) if na else None),
                     "used_max": R["used_max"], "n_multi_t12": R["n_multi"],
                     "q12_mapped": len(R["fq"]), "q12_mapped_share": (round(len(R["fq"]) / na, 4) if na else None),
                     "q12_scored": len(R["S"]), "q12_n_sel": len([k for k, v in R["S"].items() if v >= S_CUT]), "q12_active": act12,
                     "q12_held": len(w12), "q12_overlap_w_q05": round(float(sum(min(w12.get(k, 0), w[k]) for k in w)), 4),
                     "q12_via_a": sum(1 for v in R["map"].values() if v["via"] == "a"),
                     "q12_fq": {q: sum(1 for v in R["fq"].values() if v == q) for q in (1, 2, 3, 4)},
                     "q12_turn": (round(0.5 * sum(abs(w12.get(k, 0) - p12.get(k, 0)) for k in sorted(set(w12) | set(p12))), 5) if p12 is not None else None),
                     "fund_max": R["fund_max"], "cut": R["cut"]})
        p05, p12 = w, w12
    return rows


def _spans(ms):
    """정렬된 달 목록 → 이어진 구간 [[처음, 끝], …]."""
    out = []
    for m in ms:
        if out and Q.mshift(out[-1][1], 1) == m:
            out[-1][1] = m
        else:
            out.append([m, m])
    return out


def empty_records(Wd, rows):
    """창이 빈 이름(쓸 수 없는 기록) 모음 — 티커별 달 수 · 이어진 구간 · 기록 출처 · 기록 키 · 기록 처음/마지막 접수일(날짜만 · 수익 없음). 달 수 내림차순."""
    ED, _ = _ED(Wd)
    agg = {}
    for r in rows:
        R = month_frame(Wd, r["m"])
        for k in R["keys"]:
            if R["nwin"].get(k, 0):
                continue
            t = R["names"][k]
            a = agg.setdefault(t, {"months": [], "key": k, "src": R["src"][k], "rec_key": R["rkey"][k]})
            a["months"].append(r["m"])
    out = []
    for t, a in agg.items():
        ds = ED.get(a["rec_key"]) or []
        out.append({"t": t, "n_months": len(a["months"]), "spans": _spans(sorted(a["months"])), "key": a["key"], "rec_src": a["src"],
                    "rec_key": a["rec_key"], "rec_first": ds[0] if ds else None, "rec_last": ds[-1] if ds else None, "rec_n": len(ds)})
    return sorted(out, key=lambda x: (-x["n_months"], x["t"]))


def _prec_all(Wd, ED, lo, hi, strict):
    """모든 기록(유니버스 무관)의 정밀도 — 보유월 lo ~ hi · strict 면 접수일 < LTD(규칙) · 아니면 LTD 당일 접수까지 센다(카드 수정 전 정의)."""
    n = h = 0
    for m in Wd.all_m:
        t = Q.mshift(m, 1)
        if not (lo <= t <= hi):
            continue
        ltd, a = Wd.dates[Wd.me[m]], Q.mshift(m, -11)
        for key in sorted(ED):
            ds = ED[key]
            u = [d for d in ds if a <= d[:7] <= m and (d < ltd if strict else d <= ltd)]
            if len(u) == N_ANN and any(d[:7] == a for d in u):
                n += 1
                h += any(d[:7] == t for d in ds)
    return {"n": n, "hit": h, "precision": round(h / n, 4) if n else None}


def precision_detail(Wd, rows, t_last="2026-07", full=False):
    """예측 정밀도 진단(날짜만) — 유니버스 예정자의 적중 · 빗나감 갈래(m 의 LTD 이후 접수 · m 의 LTD 전 접수 · t+1 접수 · 없음) ·
    같은 기간 earn_dates 모든 기록(유니버스 무관)의 정밀도 — 카드 92.7% 와의 차이가 유니버스 탓인지 가른다. 비중에 쓰지 않는다.
    full 이면(dry) 카드 수치의 바탕을 재현한다 — 모든 기록 · 보유월 2009-01 ~ t_last · LTD 당일 접수 포함 / 제외."""
    ED, _ = _ED(Wd)
    hit, n, miss = 0, 0, {"m_on_or_after_ltd": 0, "m_before_ltd": 0, "t_plus1": 0, "none": 0}
    for r in rows:
        t = Q.mshift(r["m"], 1)
        if t > t_last:
            continue
        R = month_frame(Wd, r["m"])
        t1 = Q.mshift(t, 1)
        for k in R["ann"]:
            n += 1
            if R["ann_next"][k]:
                hit += 1
                continue
            ds = ED.get(R["rkey"][k]) or []
            if any(d[:7] == r["m"] and d >= R["ltd"] for d in ds):
                miss["m_on_or_after_ltd"] += 1
            elif any(d[:7] == r["m"] for d in ds):
                miss["m_before_ltd"] += 1
            elif any(d[:7] == t1 for d in ds):
                miss["t_plus1"] += 1
            else:
                miss["none"] += 1
    ha, na_ = 0, 0
    for r in rows:
        t = Q.mshift(r["m"], 1)
        if t > t_last:
            continue
        ltd = r["ltd"]
        for key in sorted(ED):
            ds = ED[key]
            f, _ = announcer(ds, r["m"], ltd)
            if f:
                na_ += 1
                ha += any(d[:7] == t for d in ds)
    out = {"universe": {"n": n, "hit": hit, "precision": round(hit / n, 4) if n else None, "miss": miss},
           "all_records": {"n": na_, "hit": ha, "precision": round(ha / na_, 4) if na_ else None},
           "card_stated": CARD_PREC, "hold_months": "2016-09 ~ %s" % t_last}
    if full:
        out["card_basis_2009_incl_ltd_day"] = _prec_all(Wd, ED, "2009-01", t_last, strict=False)
        out["card_basis_2009_strict"] = _prec_all(Wd, ED, "2009-01", t_last, strict=True)
    return out


def ref_mapping(Wd):
    """실제 자료 대응 시험 — AAPL · WMT · KO 가 예정자인 달마다 t−12 접수 달 → 기대 회계분기(Q4 포함)와 같은가(날짜 · 재무 기간말만 · 수익 없음)."""
    out = {}
    for tk, want in REFS.items():
        rows, bad = [], []
        for m in Wd.months:
            R = month_frame(Wd, m)
            ks = [k for k in R["ann"] if R["names"][k] == tk]
            if not ks:
                continue
            mp = R["map"].get(ks[0])
            if mp is None:
                bad.append((m, "unmapped"))
                continue
            exp = want.get(int(mp["filing"][5:7]))
            rows.append((m, mp["filing"], mp["pe"], mp["f"], mp["via"]))
            if exp != mp["f"]:
                bad.append((m, mp["filing"], mp["pe"], mp["f"], exp))
        out[tk] = {"n": len(rows), "q4": sum(1 for r in rows if r[3] == 4), "via_a": sum(1 for r in rows if r[4] == "a"), "bad": bad[:10], "n_bad": len(bad),
                   "sample": rows[:5]}
    out["ok"] = all(v["n"] > 0 and v["n_bad"] == 0 and v["q4"] > 0 for k, v in out.items() if k in REFS)
    return out


def coverage_probe(Wd):
    """Q12 대응 몫(커버리지만) — 달마다 예정자 · 대응 · 점수 · S ≥ 3.0 수."""
    rows = []
    for m in Wd.months:
        R = month_frame(Wd, m)
        na = len(R["ann"])
        rows.append({"m": m, "n_ann": na, "mapped": len(R["fq"]), "scored": len(R["S"]), "sel": len([k for k, v in R["S"].items() if v >= S_CUT]),
                     "active05": active(R), "active12": sel_q12(R)[1]})
    act = [r for r in rows if r["n_ann"]]
    return {"months": rows, "mapped_share_mean": round(float(np.mean([r["mapped"] / r["n_ann"] for r in act])), 4),
            "scored_share_mean": round(float(np.mean([r["scored"] / r["n_ann"] for r in act])), 4),
            "q05_active": sum(r["active05"] for r in rows), "q12_active": sum(r["active12"] for r in rows)}


def dry(ctx):
    """랩 자료로 구성만 — 커버리지 · 개수 · 비중 합 · 한도 · 날짜 · 실제 대응 시험. 수익 없음."""
    Wd = ctx.Wd
    t0 = time.time()
    ED, ed_end = _ED(Wd)
    T05, T12 = targets(Wd, "Q05"), targets(Wd, "Q12")
    Tn, T0, Ts = targets(Wd, "nonann"), targets(Wd, "C0"), targets(Wd, "snap")
    chk = {"Q05": _check_targets(Wd, T05, "Q05", MIN_N), "Q12": _check_targets(Wd, T12, "Q12", MIN_N),
           "nonann": _check_targets(Wd, Tn, "nonann"), "C0": _check_targets(Wd, T0, "C0", MIN_N), "snap": _check_targets(Wd, Ts, "snap")}
    P = perm_prep(Wd)
    Tid = perm_targets(P, None)
    ident = all(sorted(Tid[m]["w"]) == sorted(T12[m]["w"]) and all(abs(Tid[m]["w"][k] - T12[m]["w"][k]) < 1e-15 for k in T12[m]["w"]) for m in T12)
    Tp = perm_targets(P, np.random.default_rng(Q.SEED + 0))
    chk["Q12_perm_draw0"] = _check_targets(Wd, Tp, "Q12perm", MIN_N)
    rg0 = np.random.default_rng(Q.SEED + 0)
    same_act = all(int((P[m]["s"][rg0.permutation(len(P[m]["s"]))] >= S_CUT).sum()) == int((P[m]["s"] >= S_CUT).sum()) for m in sorted(P))
    rows = month_log(Wd, T05, T12, Tn, Ts)
    emp = empty_records(Wd, rows)
    prec = precision_detail(Wd, rows, full=True)
    # 유니버스가 World.universe(m, 'spx', False) 와 같은가
    uni_same = sum(1 for m in Wd.months if sorted(k for _, k in Wd.universe(m, "spx", False)) == month_frame(Wd, m)["keys"])
    ref = ref_mapping(Wd)
    act = [r for r in rows if r["active"]]
    thin = [r["m"] for r in rows if not r["active"]]
    thin_moy = {}
    for mm in thin:
        h = Q.mshift(mm, 1)[5:7]
        thin_moy[h] = thin_moy.get(h, 0) + 1
    pit_ok = all(r["used_max"] is None or r["used_max"] < r["ltd"] for r in rows) and all(r["fund_max"] is None or r["fund_max"] <= r["cut"] for r in rows)
    prec_n = sum(r["n_ann"] for r in rows if Q.mshift(r["m"], 1) <= "2026-07")
    prec_hit = sum(sum(month_frame(Wd, r["m"])["ann_next"].values()) for r in rows if Q.mshift(r["m"], 1) <= "2026-07")
    last_ltd = Wd.dates[Wd.me[Wd.months[-1]]]
    na = [r["n_ann"] for r in rows]
    nh = [r["n_held"] for r in rows]
    nsn = [r["n_snap"] for r in rows]
    mmm = lambda v, nd=4: [round(float(min(v)), nd), round(float(np.median(v)), nd), round(float(max(v)), nd)] if len(v) else None
    stw = [r["snap_stale_w"] for r in rows if r["snap_max_gap"] is not None]
    return {"months": len(rows), "univ_equals_World_spx": "%d/%d" % (uni_same, len(rows)),
            "n_univ": [min(r["n_univ"] for r in rows), int(np.median([r["n_univ"] for r in rows])), max(r["n_univ"] for r in rows)],
            "rec_cov_key_exists": [min(r["rec_cov"] for r in rows), round(float(np.median([r["rec_cov"] for r in rows])), 4), max(r["rec_cov"] for r in rows)],
            "usable_cov_count": mmm([r["usable_cov"] for r in rows]),
            "empty_rec_cap_share": mmm([r["empty_cap_share"] for r in rows]),
            "empty_rec_n": mmm([len(r["empty_rec"]) for r in rows], 0), "empty_rec_name_months": int(sum(len(r["empty_rec"]) for r in rows)),
            "empty_rec_names": len(emp),
            "nonann_empty_w_active": mmm([r["nonann_empty_w"] for r in act]),
            "empty_rec_top": [{"t": e["t"], "n": e["n_months"], "spans": e["spans"], "rec_key": e["rec_key"], "rec_first": e["rec_first"], "rec_last": e["rec_last"]}
                              for e in emp[:16]],
            "snap_months_with_stale": sum(1 for r in rows if r["snap_stale"]), "snap_stale_w": mmm(stw),
            "snap_stale_w_ge_0.2_months": sum(1 for x in stw if x >= 0.2 - 1e-12),
            "snap_stale_top": sorted(({"m": r["m"], "w": r["snap_stale_w"], "names": r["snap_stale"]} for r in rows if r["snap_stale"]),
                                     key=lambda z: (-z["w"], z["m"]))[:8],
            "rec_src_total": {s: int(sum(r["rec_src"][s] for r in rows)) for s in ("t", "k", "dot", "splice")},
            "n_ann": [min(na), int(np.median(na)), max(na)], "active_months": len(act), "thin_months_by_hold_month": dict(sorted(thin_moy.items())),
            "n_held_q05": [min(nh), int(np.median(nh)), max(nh)], "n_held_active": [min(r["n_held"] for r in act), int(np.median([r["n_held"] for r in act])), max(r["n_held"] for r in act)],
            "max_w_pre_cap": max(r["max_w_pre"] for r in rows), "max_w_post_cap": max(r["max_w"] for r in rows),
            "months_cap_binding": sum(1 for r in rows if r["max_w_pre"] > CAP + 1e-9),
            "n_nonann_active": [min(r["n_nonann"] for r in act), int(np.median([r["n_nonann"] for r in act])), max(r["n_nonann"] for r in act)],
            "n_snap": [min(nsn), int(np.median(nsn)), max(nsn)], "snap_empty_months": sum(1 for x in nsn if x == 0),
            "snap_under5_months": sum(1 for x in nsn if 0 < x < 5),
            "precision_pooled_t<=2026-07": round(prec_hit / prec_n, 4) if prec_n else None, "precision_detail": prec,
            "n_multi_t12_total": int(sum(r["n_multi_t12"] for r in rows)),
            "ed_end": ed_end, "last_form_ltd": last_ltd, "f0_q05": bool(ed_end >= Wd.dates[Wd.me[Wd.months[-1]] - 1]),
            "q12_mapped_share": [min(r["q12_mapped_share"] for r in act), round(float(np.median([r["q12_mapped_share"] for r in act])), 4), max(r["q12_mapped_share"] for r in act)],
            "q12_scored": [min(r["q12_scored"] for r in rows), int(np.median([r["q12_scored"] for r in rows])), max(r["q12_scored"] for r in rows)],
            "q12_n_sel": [min(r["q12_n_sel"] for r in rows), int(np.median([r["q12_n_sel"] for r in rows])), max(r["q12_n_sel"] for r in rows)],
            "q12_active_months": sum(1 for r in rows if r["q12_active"]),
            "q12_fq_total": {q: int(sum(r["q12_fq"][q] for r in rows)) for q in (1, 2, 3, 4)}, "q12_via_annual_total": int(sum(r["q12_via_a"] for r in rows)),
            "q12_overlap_w_q05_median_active": round(float(np.median([r["q12_overlap_w_q05"] for r in rows if r["q12_active"]])), 4) if any(r["q12_active"] for r in rows) else None,
            "ref_mapping": ref, "checks": chk, "perm_identity_equals_rule": ident, "perm_draw0_fallback_months_same": bool(same_act),
            "pit_ok": pit_ok, "turn_target_q05": target_turn(T05), "turn_target_q12": target_turn(T12),
            "targets_hash": {"Q05": targets_hash(T05), "Q12": targets_hash(T12)}, "sec": round(time.time() - t0, 1)}


# ── 한 번 굽기 ─────────────────────────────────────────────────────────────
def _ex(fr):
    return np.asarray(fr["ex"], float)


def run(ctx):
    """한 번 굽기 — {'Q05': CardResult, 'Q12': CardResult}. 판정 · 다중성은 러너가 한다. 🚨 여기서 수익을 찍지 않는다."""
    Wd = ctx.Wd
    t0 = time.time()
    _, ed_end = _ED(Wd)
    T05, T12 = targets(Wd, "Q05"), targets(Wd, "Q12")
    Tn, T0, Ts = targets(Wd, "nonann"), targets(Wd, "C0"), targets(Wd, "snap")
    fr = ctx.stock_fr(T05, reb=1)
    fr_pr = ctx.stock_fr(T05, reb=1, basis="PR")
    fr20 = ctx.stock_fr(T05, reb=1, cost=COST20)
    ctrl = {"nonann": ctx.stock_fr(Tn, reb=1), "C0": ctx.stock_fr(T0, reb=1), "runup_snapshot": ctx.stock_fr(Ts, reb=1)}
    hold = fr["hold"]
    rows = month_log(Wd, T05, T12, Tn, Ts)
    act = np.array([r["active"] for r in rows], bool)          # 편입 m 의 능동 여부 = 보유월 m + 1
    assert [Q.mshift(r["m"], 1) for r in rows] == hold
    # G4 — 비발표 대조
    x = _ex(fr)
    d = x - _ex(ctrl["nonann"])
    t_n = E.nw_t(d)
    g4 = {"nonann_mean>0_nw_t>=1.0": bool(float(d.mean()) > 0 and t_n is not None and t_n >= 1.0)}
    g4["G4"] = all(g4.values())
    # 런업 재포장 표시 — 슬리브 월 수익 기준 회귀
    b, b0, bs = (np.asarray(f["basket"], float) for f in (fr, ctrl["C0"], ctrl["runup_snapshot"]))
    y, xx = b - b0, bs - b0

    def _ols(yv, xv):
        try:
            cb, ct = E.nw_ols(yv, np.column_stack([np.ones(len(yv)), xv]))
            return {"intercept": float(cb[0]), "intercept_t": float(ct[0]), "slope": float(cb[1]), "slope_t": float(ct[1]), "n": len(yv)}
        except Exception as e:                               # 스냅숏 = 유니버스 인 달뿐이면 특이 — 절편만(평균)
            return {"intercept": float(yv.mean()) if len(yv) else None, "intercept_t": None, "slope": None, "slope_t": None, "n": len(yv), "err": str(e)[:200]}
    runup = _ols(y, xx)                                      # 🚨 관문(표시 상한) = 이 120개월 절편 — 사전등록에 박는다
    runup["gate"] = True
    # 보고만 — 능동 달(80)만의 같은 회귀(얇은 달은 목표가 C0 와 같아 y ≈ 0 이라 기울기를 0 쪽으로 끈다 · 갈림길 공개)
    runup_act = _ols(y[act], xx[act]) if act.any() else None
    if runup_act is not None:
        runup_act["gate"] = False
    caps = {"runup_repack": bool(runup["intercept"] is not None and runup["intercept"] <= 0)}
    # 능동 달 기전 행(보고만)
    mech = {"n_active": int(act.sum()), "mean": float(d[act].mean()) if act.any() else None,
            "t_calendar_hac": E.down_t(d, act), "t_sub_nw": E.nw_t(d[act]) if act.any() else None,
            "power_note": "능동 %d/120 달 — 같은 효과라도 t 는 약 √(%d/120) ≈ %.2f 배(카드 √(2/3))" % (int(act.sum()), int(act.sum()), math.sqrt(act.sum() / 120.0))}
    prec_n = sum(r["n_ann"] for r in rows if Q.mshift(r["m"], 1) <= "2026-07")
    prec_hit = sum(sum(month_frame(Wd, r["m"])["ann_next"].values()) for r in rows if Q.mshift(r["m"], 1) <= "2026-07")
    f0_05 = bool(ed_end >= Wd.dates[Wd.me[Wd.months[-1]] - 1])
    log05 = {"interpretation": INTERP, "months": rows, "active_months": int(act.sum()), "thin_hold_months": [h for h, a in zip(hold, act) if not a],
             "turn_sleeve": fr.get("turn"), "turn_target": target_turn(T05), "turn_le_10x": (fr.get("turn") is not None and fr["turn"] <= 10.0),
             "sleeve_cost_drag_pct_yr": (2 * fr["turn"] * Q.COST * 100 if fr.get("turn") is not None else None),
             "precision_pooled": (prec_hit / prec_n if prec_n else None), "precision_note": "보유월 ≤ 2026-07 · 예정자 중 그달 실제 2.02 접수 몫",
             "max_w_pre_cap": max(r["max_w_pre"] for r in rows), "max_w_post_cap": max(r["max_w"] for r in rows),
             "mechanism_active": mech, "runup": runup, "runup_active_report_only": runup_act,
             "runup_gate_note": "label_caps.runup_repack 는 120개월 절편(runup)으로만 정한다 · 능동 달 판(runup_active_report_only)은 보고만",
             "g4_stats": {"nonann_mean": float(d.mean()), "nonann_nw_t": t_n},
             "usable_record": {"usable_cov_count": [r["usable_cov"] for r in rows], "empty_cap_share": [r["empty_cap_share"] for r in rows],
                               "nonann_empty_w": [r["nonann_empty_w"] for r in rows], "empty_names": empty_records(Wd, rows),
                               "note": "창(m − 11 ~ m · < LTD) 안 접수 0 = 절대 예정자가 못 되고 능동 달엔 늘 비발표 대조에 든다 — 카드 문자 그대로 둔다(앞 CIK 기록 보강은 새 earn_dates 핀이 필요)"},
             "snapshot_stale": {"td": STALE_TD, "w": [r["snap_stale_w"] for r in rows], "names": [r["snap_stale"] for r in rows],
                                "note": "스냅숏 이름 중 마지막 2.02 뒤 > %d 거래일(비분기 · 낡은 기록) 비중 — 규칙은 문자 그대로(진단만)" % STALE_TD},
             "precision_detail": precision_detail(Wd, rows),
             "ed_end": ed_end, "family": "EAP ≥ 5(x-earngap · 301 PEAD · PEAD 2판 · 663 · EVENT E3)", "sec": None}
    log05["sec"] = round(time.time() - t0, 1)
    r05 = {"code": "Q05", "cls": "A", "slot": "A3", "fr": fr, "fr_pr": fr_pr, "fr20": fr20, "controls": ctrl, "arms": {},
           "placebo": {}, "perm": None, "g4": g4, "label_caps": caps,          # Q05 카드는 위약이 없다 · perm 은 부류 S 만
           "f0": {"ok": f0_05, "why": "earn_dates 마지막 접수일 %s · 마지막 편입 LTD %s — 기록이 편입 컷을 덮는가(낡은 기록은 전방 달 측정 불가)" % (ed_end, Wd.dates[Wd.me[Wd.months[-1]]])},
           "targets_hash": targets_hash(T05), "log": log05}
    # ── Q12 ──
    t1 = time.time()
    f12 = ctx.stock_fr(T12, reb=1)
    f12_pr = ctx.stock_fr(T12, reb=1, basis="PR")
    f12_20 = ctx.stock_fr(T12, reb=1, cost=COST20)
    x12 = _ex(f12)
    true_d = float(np.mean(x12 - x))
    P = perm_prep(Wd)
    draws = []
    for r in range(NPERM):
        fp = ctx.stock_fr(perm_targets(P, np.random.default_rng(Q.SEED + r)), reb=1)
        draws.append(float(np.mean(_ex(fp) - x)))
    q95 = float(np.quantile(np.asarray(draws, float), 0.95)) if draws else None
    g12 = {"placebo>=p95": bool(q95 is not None and true_d >= q95)}
    g12["G4"] = all(g12.values())
    n12 = sum(1 for r in rows if r["q12_active"])
    act_rows = [r for r in rows if r["n_ann"]]
    log12 = {"interpretation": INTERP, "parent": "Q05", "q12_active_months": n12,
             "mapped_share": [{"m": r["m"], "n_ann": r["n_ann"], "mapped": r["q12_mapped"], "share": r["q12_mapped_share"], "scored": r["q12_scored"],
                               "n_sel": r["q12_n_sel"], "active": r["q12_active"], "overlap_w_q05": r["q12_overlap_w_q05"], "turn": r["q12_turn"],
                               "fq": r["q12_fq"]} for r in rows],
             "mapped_share_mean": float(np.mean([r["q12_mapped"] / r["n_ann"] for r in act_rows])) if act_rows else None,
             "turn_sleeve": f12.get("turn"), "turn_target": target_turn(T12), "p_ff": False, "pff_same_sign": "pending",
             "p_ff_why": "원 companyfacts(제출일) 없음 — 마지막 제출값(재작성 누출) · 첫 제출 재실행이 G5 필수",
             "placebo_q95": q95, "perm_sec": round(time.time() - t1, 1), "chss": "CHSS 착안 랩 변형 — 전문 미열람 · 증거 옮기지 않음", "sec": None}
    log12["sec"] = round(time.time() - t1, 1)
    r12 = {"code": "Q12", "cls": "C", "slot": "A3", "parent": "Q05", "fr": f12, "fr_pr": f12_pr, "fr20": f12_20, "controls": {"Q05": fr}, "arms": {},
           "placebo": {"S_perm_dQ05": {"stat": "전 달 평균 Δ = X_Q12 − X_Q05(%%/월) — 달마다 S 가 선 예정자 안에서 S 섞기 %d번 · 씨앗 SEED + i" % NPERM,
                                       "draws": draws, "true": true_d}},
           "perm": None, "g4": g12, "label_caps": {},
           "f0": {"ok": bool(n12 > 0), "why": "Q12 가 Q05 와 다른 달 %d — 0 이면 Δ ≡ 0 이라 잴 수 없다(카드에 F0 문구 없음 · 구조만)" % n12},
           "targets_hash": targets_hash(T12), "log": log12}
    return {"Q05": r05, "Q12": r12}


# ── 명령줄 ────────────────────────────────────────────────────────────────
def main():
    a = sys.argv[1:]
    if "--selftest" in a:
        print(json.dumps(selftest(), ensure_ascii=False, indent=1))
        return 0
    ctx = Q.Ctx()
    if "--probe" in a:
        pr = coverage_probe(ctx.Wd)
        pr["months"] = pr["months"][:3] + pr["months"][-3:]
        print(json.dumps(pr, ensure_ascii=False, indent=1))
        return 0
    if "--dry" in a:
        print(json.dumps(dry(ctx), ensure_ascii=False, indent=1, default=str))
        return 0
    if "--smoke" in a:
        global NPERM
        NPERM = 3
        print(json.dumps(Q.blind_smoke(run, ctx), ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
