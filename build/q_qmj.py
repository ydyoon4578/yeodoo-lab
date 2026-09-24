# -*- coding: utf-8 -*-
"""build/q_qmj.py — 배치 Q · Q01 SK14 퀄리티 마이너스 정크 롱온리(AFP 4기둥 · 현금흐름은 같은 회계연도 창 · 상위 30% 시총가중 · 월간)
부류 A(단독 슬리브) · 슬롯 A1 · 카드 원문 scratchpad/qbatch_final.md «# Q01» · 계약 scratchpad/qbatch_contract.md.

근본 이유: 품질주(수익성 · 성장 · 안전 · 주주환원이 높은 주식)는 마땅히 더 비싸야 하지만 실제 가격 프리미엄이 작아서 위험조정 수익이 높다.
  투자자는 복권형 · 고성장 서사를 가진 정크주를 과대평가하고, 레버리지 · 벤치마크 제약 때문에 기관은 안전한 우량주를 덜 산다.
  위기 때는 «품질로의 도피» 가 일어나 품질주가 덜 빠진다. 시총가중 상위 30% 로 담아 동일가중 − 시총가중 격차가 없다.
  약점 — 급락 직후 정크 랠리(2020-11 ~ 2021-02)에서 크게 뒤지고, 안전 기둥(−베타 · −개별변동)이 저위험 계열의 강세장 부담을 안고 온다.
  미리 적는 정직한 기대 라벨은 «급락형»(카드).

규칙(카드 그대로 · 달리 읽은 곳은 INTERP):
  편입 = qbatch_core.monthly_forms()(2016-08 ~ 2026-07 월말) · reb=1 · 유니버스 = eg30plus.World.universe(m, 'union', ex_fin=False).
  재무 = tech_backtest.load_fund + asof_all(90일 지연) — 🚨 P-FF(첫 제출 재구성)는 저장소에 원 companyfacts(제출일)가 없어 못 만든다
    → 마지막 제출값(재작성 누출이 남는다) · 첫 제출 재실행이 G5 필수 조건(배치 설계 §2(d) · §4 G5).
  흐름(NI · CFO · CAPEX)은 m 에 쓸 수 있는 가장 최근 회계연도 연간 버킷(ni_a · cfo_a · capex_a) 하나에서 · 잔고(EQ · ASSET · LIAB)는 같은 회계연도 말.
    회계연도 말 = ni_a 기간말 중 ±7일 겹친 날짜는 최근 하나 · 10-Q 날짜의 TTM 태그(AMZN)는 뺀다 · FY* 가 컷보다 550일 넘게 낡으면 없음.
  성분(단면 순위 → 순위 z):
    수익성 ROE = NI/EQ · ROA = NI/ASSET · CFOA = (CFO − CAPEX)/ASSET · ACC = −(NI − CFO)/ASSET
    성장   ΔROE = (NI_y − NI_y−5)/EQ_y−5 · ΔROA = (NI_y − NI_y−5)/ASSET_y−5 · ΔCFOA = (CF_y − CF_y−5)/ASSET_y−5 (CF = CFO − CAPEX)
    안전   BAB = −FP 베타 · IVOL = −252일 CAPM 잔차 sd(SPY) · LEV = −LIAB/ASSET · EVOL = −분기 ROE sd(최근 20분기 · 최소 12 · Q4 = 연간 − Q1 − Q2 − Q3)
    환원   EISS = −ln(SH_t/SH_t−1y)(x-shiss 의 sh_u · 이음매는 m 에 알 수 있는 단절만) · NPOP = Σ5y(NI − ΔEQ)/Σ5y NI (분모 ≤ 0 이면 없음)
  커버리지 얼림(2016-08 · 유니버스 시총 중 값이 선 몫 < 80% 인 성분은 뺀다 · LEV 는 LIAB 가 모자라면 −DEBT/ASSET 가 80% 이상일 때 그것으로) → FROZEN.
    🧊 얼린 결과: 수익성 ROE · ROA / 성장 없음(기둥째 빠짐) / 안전 BAB · IVOL · EVOL / 환원 EISS — 그래서 퀄리티는 남은 3기둥 모두 필수.
    ⚠ 빠진 성분의 결측은 대부분 랩 수집 잘림이다(실제 미공시가 아니다) — AMZN(연간 버킷이 TTM 이라 KEEP_A=20 이 2021-09 전을 잘랐다) ·
      XOM · DIS · BLK(새 지주사 CIK) · GOOGL(전신 Google Inc. CIK 안 이음) — --probe 의 attribution 이 원인별 시총 몫을 낸다.
  기둥 = (있는 성분 z 평균)의 선형 z(수익성 · 성장 · 안전 ≥ 2 성분 · 환원 ≥ 1) · 퀄리티 = (있는 기둥 z 평균)의 선형 z(4 중 ≥ 3).
  선정 = 퀄리티 상위 ceil(0.30 × N_scored)(같으면 시총 큰 쪽) · 비중 = m 시총 비례 · 한 이름 10% 상한(넘친 몫 비례 재배분) · 1개월 보유 · 편도 10bp.
대조: C1 = 퀄리티가 선 전 종목 시총가중(10%) · C0 = 가격이 선 전 유니버스 시총가중(10%) ·
      C2 위약 = 달마다 시점정확 GICS 업종 안에서 퀄리티를 섞어 같은 규칙(1000번 · 씨앗 20260925 + i) — 전 달 평균 X · 하락월 H(판마다 제 슬리브 베타).
      관문 판정은 참값 · 판 모두 비용 0(총)으로 잰다(C2_GROSS · 카드 수정 필요) — 10bp 판은 보고만.
측정만 팔: 안전 기둥 뺀 판(카드 3기둥 → 성장이 빠져 수익성 · 환원 둘 다 필수) · QUAL ETF 슬리브(자산 격자 A) · 기둥 하나씩(성장은 성분이 없어 못 돈다 → 셋).

출처: Asness, Frazzini & Pedersen (2019) «Quality minus junk», Review of Accounting Studies 24:34–112 — 부록 변수 정의 · 순위 → z · 30% 절단 · 시총가중
  (2013 초고를 앞선 연구자가 열었다 · 카드 params). Frazzini & Pedersen (2014) «Betting against beta», JFE 111:1–25 — 베타(랩 FP 상수 eg30plus).

🚨 이 모듈은 규칙 · 대조 · 팔 · 위약의 수익 · 초과 · IR · 샤프 · 적중률을 찍지 않는다. run() 은 한 번 굽기에서만 부른다(러너가 판정).

  python build/q_qmj.py --probe      # 커버리지 얼림(2016-08 · 커버리지만 · 결측 원인 · LEV 읽기 민감도)
  python build/q_qmj.py --selftest   # 합성 자료 단위 시험
  python build/q_qmj.py --dry        # 구성만(커버리지 · 개수 · 비중 합 · 한도 · 날짜 · 이음매 · 낡은 FY · 음의 자본 · 날짜 허용 0 영향)
  python build/q_qmj.py --smoke      # 눈가린 연기 시험(NPERM 3 · 예외 · 시간 · 모양만)
  python build/q_qmj.py --hashes     # 목표 해시만(PYTHONHASHSEED 결정성 확인용)
"""
from __future__ import annotations
import hashlib, io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q            # noqa: E402
import tech_backtest as TB         # noqa: E402  asof_all · yoy_pair · _shift · _days_between · SPLIT_BREAKS
import eg30plus as E               # noqa: E402  cap_weights · nw_t

CARDS = {"Q01": {"cls": "A", "slot": "A1"}}
NPERM = 1000                        # C2 위약 판 수 — 연기 시험에서 작게 덮어쓴다

# ── 카드 상수 ─────────────────────────────────────────────────────────────
LAG = TB.FUND_LAG_DAYS              # 90일(랩 규약)
FREEZE_M, COV_MIN = "2016-08", 0.80 # 커버리지 얼림 달 · 문턱(유니버스 시총 몫)
TOP_NUM, TOP_DEN = 3, 10            # 상위 ceil(0.30 × N) — 정수로 센다(0.3 × 100 = 30.000000000000004 를 피한다)
NAME_CAP = 0.10                     # 한 이름 상한
COST20 = 0.0020                     # 20bp 행
GROWTH_Y = NPOP_Y = 5               # 5 회계연도
EVOL_N, EVOL_MIN, EVOL_DAYS = 20, 12, 1826   # 최근 20분기(≈ 5년 = 1826일 창) · 최소 12
IVOL_WIN, IVOL_MIN = 252, E.FP_VOL_MIN       # 252일 · 최소 120(랩 FP 상수)
YOY_LO, YOY_HI = 320, 410           # «한 회계연도 앞» = 320 ~ 410일(tech_backtest.yoy_pair 규약) · 320일 안 = 1년 미만 간격
DATE_TOL = 7                        # «같은 회계연도 말» = 같은 날 먼저, 없으면 ±7일(52/53주 · 기간말 표기 어긋남) — 선언한 구현 선택(prereg 에 등록)
FY_FRESH_DAYS = TB.TTM_STALE_DAYS   # 550일 — FY* · EISS 최신 관측이 컷보다 이만큼 넘게 낡으면 없음(랩 ttm2 연간 갈래와 같은 층 · 카드 수정 필요)
C2_GROSS = True                     # C2 관문은 참값 · 판 모두 비용 0(총) — 달마다 새로 섞는 위약만 회전이 커서 10bp 끌림이 규칙 쪽으로 기운다(카드 수정 필요)
H0_C0 = "2019-09"                   # C0 관문 뒤 구간 시작(보유월)

PILLARS = ("prof", "grow", "safe", "pay")
COMPONENTS = {"prof": ("ROE", "ROA", "CFOA", "ACC"), "grow": ("dROE", "dROA", "dCFOA"),
              "safe": ("BAB", "IVOL", "LEV", "EVOL"), "pay": ("EISS", "NPOP")}
PILLAR_MIN = {"prof": 2, "grow": 2, "safe": 2, "pay": 1}
QUAL_MIN = 3
PROBE_EXTRA = ("LEV_DEBT",)         # LEV 대체(−DEBT/ASSET) — 얼림 판단에만
FY_COMPS = ("ROE", "ROA", "CFOA", "ACC", "LEV", "LEV_DEBT", "dROE", "dROA", "dCFOA", "NPOP")

# 🧊 커버리지 얼림 결과(--probe · 2016-08 · 유니버스 422 · 커버리지만 · 2026-09-25 수정판 — 이음매 · 낡은 FY · TTM 태그 · 겹친 날짜 고친 뒤). dry · run 이 다시 재서 같아야 한다.
#   결측 원인(ΔROA 결측 21.2% 중): 이력이 FY2010 뒤 시작 9.6(GOOGL 3.55 · IBM · MDT · ABBV · KHC …) · ni_a 가 컷 전에 없음 5.2(AMZN 2.45 · DIS · AVGO · BLK …)
#   · ni_a 없음 1.7 · 사슬 빈 해 1.1 · 항목 · 분모 2.8 · 낡은 FY 0.8 — 수집 잘림만으로 80% 문턱(1.2%p 모자람)을 넘길 몫이다.
#   성장 기둥이 통째로 빠졌다 — 카드 수정 필요(퀄리티 = 남은 3기둥 모두 필수). LEV 는 FY 맞춤 LIAB · DEBT 둘 다 80% 미만이라 뺐다
#   (DEBT 를 FY 가 아니라 as-of 로 읽으면 80% 를 넘는다 — 카드 수정 필요 · --probe 의 sensitivity).
FROZEN = {"prof": ["ROE", "ROA"], "grow": [], "safe": ["BAB", "IVOL", "EVOL"], "pay": ["EISS"]}
LEV_SRC = None
_FROZEN_COV_TXT = {"ROE": 0.8942, "ROA": 0.9232, "CFOA": 0.6134, "ACC": 0.7304, "dROE": 0.7634, "dROA": 0.7883, "dCFOA": 0.4528,
                   "BAB": 0.9804, "IVOL": 0.998, "LEV": 0.6525, "EVOL": 0.8163, "EISS": 0.859, "NPOP": 0.7475, "LEV_DEBT": 0.7138}

INTERP = [
    "P-FF(첫 제출 재구성) 불가 — 저장소 · snap 에 제출일이 붙은 원 companyfacts 가 없다(data/fx 는 refresh_facts.pick 이 마지막 제출값만 남김 · "
    "data/fil 은 제출 목록뿐 값이 없다) → 마지막 제출값 · as-of = 기간말 + 90일 · 첫 제출 재실행이 G5 필수(카드 대체 경로).",
    "회계연도 말 집합 = m 에 쓸 수 있는(기간말 ≤ m 말 − 90일) ni_a 기간말 중 ① ±7일 안에 겹친 날짜(같은 해의 다른 표기 — CIEN · JCI · YUM · DE · TAP · TSN · ATI)는 "
    "최근 날짜 하나(늦게 알 수 있는 쪽이라 시점상 보수적) ② TTM 태그 제외 = 그 날짜에 q 분기 NI 가 있고(10-Q 날짜) 그보다 320일 안 앞에 q 가 없는 ni_a 기간말"
    "(10-K 날짜)이 있는 관측(AMZN 은 연간 버킷에 분기마다 TTM 을 태그한다). FY* = 그중 가장 최근. cfo_a · capex_a · 잔고가 그 FY 에 없으면 그 성분은 없음(앞 해로 내려가지 않는다).",
    "FY* 신선도 — 컷(m 말 − 90일) − FY* > 550일(랩 TTM_STALE_DAYS · ttm2 연간 갈래와 같은 층 · 컷 기준)이면 FY 성분(ROE · ROA · CFOA · ACC · LEV · 성장 · NPOP) 전부 없음. "
    "카드에 없는 상한이다(카드 수정 필요) — 수집 태그 공백 때문에 몇 해 전 FY 가 «최신» 으로 남는 것(PAYX FY2015 를 2024 까지 · SYY FY2011 을 2020 까지)을 막는다. "
    "EISS 의 최신 주식수 관측 d0 에도 같은 상한.",
    "«같은 회계연도 말» 잔고 · 흐름 맞춤 = 같은 날 먼저, 없으면 ±7일 안 가장 가까운 관측(같은 거리면 이른 날) — 카드에 날짜 허용이 없어 선언한 구현 선택으로 등록. "
    "허용 0 과 달라지는 이름 수는 dry 가 달마다 잰다(얼림 목록은 허용 0 에서도 같다).",
    "«5 회계연도 앞» = 회계연도 말을 320 ~ 410일 걸음(yoy_pair 규약)으로 다섯 번 거슬러 간 해 — 중간 해가 비면 성장 · NPOP 은 없음.",
    "ROE · ΔROE · EVOL 의 자기자본 분모는 > 0 일 때만(JKP · FF 의 BE > 0 관례 · 음의 자본으로 나누면 부호가 뒤집힌다) · ASSET 분모도 > 0. "
    "수익성이 ROE · ROA 2개 모두 필수라 음의 자본 이름은 퀄리티 전체가 없다(C1 에서도 빠진다) — 달마다 개수 · 시총 몫 · 이름을 기록.",
    "EVOL 분기 ROE = 그 분기 NI ÷ 같은 분기말 EQ · Q1–Q3 = q 버킷(±7일 겹친 날짜는 최근 하나) · 회계연도 말 ±7일 안 q 값은 Q4 직접 태그라 빼고 공식으로 · "
    "TTM 태그 날짜의 q 값은 분기 값으로 남긴다 · Q4 = 연간 − 그 회계연도 안(FY 말 전 320일 안) q 세 개(정확히 셋일 때만) · "
    "창 = (m 말 − 90일 − 1826일, m 말 − 90일] 의 최근 20분기 · 유효 ≥ 12 · sd ddof=1.",
    "IVOL = 252 거래일 창(i−252 ~ i) 일간 단순수익을 SPY 총수익(World.IX_TR) 일간 수익에 절편 포함 OLS · 잔차 sd(ddof=1) · 유효일 ≥ 120(랩 FP_VOL_MIN).",
    "EISS = x-shiss 의 계열(yoy_pair(sh_u 또는 sh, 90일, seam)) · 🚨 이음매(seam)는 m 에 알 수 있는 것만 — 단절 날짜(tech_backtest.SPLIT_BREAKS · 내림차순) 중 "
    "≤ 컷인 가장 최근 것. 전 표본 sh_seam 을 그대로 넘기면 yoy_pair 가 d0 < seam 에서 None 을 돌려 미래 단절(합병 신주 · 분사)이 그 전 모든 달의 EISS 를 지운다"
    "(HON · DVN 2016-08 ~ 2026-05 · OMC · O · UTX · GPN · FIS …) — 미래정보. x-shiss 도 같은 흠을 안고 있다(보고). x-shiss 의 |g| ≤ 50% 거르기는 카드에 없어 안 쓴다.",
    "성분은 순위(같으면 평균 순위) → 순위의 z(ddof=1). 기둥 · 퀄리티의 «z-score» 는 카드 AGGREGATION 문구 그대로 선형 표준화(평균 · 표준편차 · 다시 순위 매기지 않는다). "
    "AFP 원문은 기둥에도 순위 z(·) 를 쓴다 — 다른 읽기이며 prereg 에 이 선택(선형)을 명시한다. 퀄리티 단계는 단조 변환이라 선정에 영향이 없다.",
    "단일 기둥 팔 = 그 기둥이 선 이름 안에서 기둥 z 상위 30%(성장은 얼림에서 성분이 없어 못 돈다) · "
    "안전 뺀 팔 = 카드는 «3기둥 모두 필수» 인데 성장이 빠져 남은 비안전 기둥(수익성 · 환원) 둘 다 선 이름 안 평균의 z 상위 30%(카드 수정 필요).",
    "커버리지 얼림으로 성장 기둥 전체 · CFOA · ACC · LEV(LIAB · DEBT 모두) · NPOP 이 빠졌다 → 퀄리티 = 수익성(ROE · ROA) · 안전(BAB · IVOL · EVOL) · 환원(EISS) "
    "3기둥 모두 필수(«4 중 ≥ 3» 의 문자 그대로 결과) — 카드 수정 필요. 원인은 대부분 랩 수집 잘림(--probe attribution: ni_a 가 컷 전에 없음 · 이력이 FY2010 뒤에 시작)이지 실제 미공시가 아니다.",
    "LEV 읽기 — 흐름창 규칙(«모든 잔고는 같은 회계연도 말»)대로 DEBT 도 FY* 말에서 맞춘다(2016-08 FY 맞춤 −DEBT/ASSET 71.4% · LIAB 65.3% → LEV 뺌). "
    "카드 data 절의 «debt 80.6% of cap» 은 as-of(컷 전 최신 debt 관측 · 80.55% · ASSET as-of > 0 이어도 80.55%) 읽기라 그 읽기면 80% 를 넘어 LEV(−DEBT/ASSET)가 산다 — 선택이 얼림을 뒤집으므로 카드 수정 필요로 올린다.",
    "C2 위약의 «95번째 백분위» = np.quantile(draws, 0.95)(선형 보간) · 참값 ≥ 그 값이면 통과. 하락월 H = evaluate 의 down_mean − hedge_ctrl.down_mean(판마다 제 sleeve_beta). "
    "C2 는 달마다 새로 섞어 위약 판의 목표 회전이 규칙보다 훨씬 크다(dry: 규칙 약 0.9 · 판 약 7.9 회/년 편도) — 10bp 끌림이 위약 쪽에만 커서 규칙에 유리하게 기운다 "
    "→ 관문은 참값 · 판 모두 비용 0(총수익 · 되돌림 비용도 0)으로 잰다(C2_GROSS · 카드 수정 필요) · 10bp 판(참값 · 판)은 placebo 의 *_net10bp 로 보고만. 판마다 같은 씨앗의 같은 섞기를 두 비용에 쓴다.",
    "C2 업종 = 시점정확 GICS 만 — 그달 표(month), 없으면 가장 가까운 이전 달(near_prev). 이후 달 표(near_next) · 오늘 분류(today)로만 서는 이름은 '?' 무리로 따로 섞는다(미래 분류를 안 쓴다).",
    "F0 는 카드에 없다 — 구조 가능성만(기둥 구성 가능 · 달마다 보유 ≥ 10 이라 10% 상한이 선다).",
    "QG30 대비 보유 겹침 · 슬리브 상관은 QG30 목표 경로가 코어에 없어 싣지 못한다(EG30 · QUAL 만).",
    "QUAL 팔은 ctx.etf_fr(자산 격자 A · 5213일)로 만든다 — 다른 행은 종목 격자(4457일). 러너 G_of 가 IX 길이로 A 를 고른다(log['grid']).",
]


# ── 작은 도구 ─────────────────────────────────────────────────────────────
def _obs(f, key, cut):
    """관측 [(기간말, 값)] 내림차순 · 기간말 ≤ cut 만."""
    return [(d, v) for d, v in (f.get(key) or []) if d <= cut and v is not None]


def _collapse(obs, tol=DATE_TOL):
    """관측(내림차순)에서 tol 일 안에 겹친 날짜는 최근 것 하나만(같은 기간의 다른 날짜 표기 — 52/53주). 늦게 알 수 있는 쪽이라 시점상 보수적."""
    out = []
    for d, v in obs:
        if out and TB._days_between(out[-1][0], d) <= tol:
            continue
        out.append((d, v))
    return out


def _at(obs, d0, tol=DATE_TOL):
    """같은 회계연도 말 값 — 같은 날 먼저, 없으면 ±tol 일 안 가장 가까운 것(같은 거리면 이른 날). → (날짜, 값) 또는 (None, None)."""
    best = None
    for d, v in obs:
        if d == d0:
            return d, v
        g = TB._days_between(d, d0)
        if g <= tol and (best is None or (g, d) < (best[0], best[1])):
            best = (g, d, v)
    return (best[1], best[2]) if best else (None, None)


def fy_ends(f, cut, tol=DATE_TOL):
    """m 에 쓸 수 있는 회계연도 말 [(기간말, 연간 NI)] 내림차순 · TTM 태그 날짜 집합.
    ① ±tol 겹친 날짜는 최근 하나 ② 10-Q 날짜(같은 날 q 분기 NI)이면서 320일 안 앞에 q 가 없는 연간 관측(10-K 날짜)이 있으면 TTM 태그 — 회계연도 말이 아니다.
    컷 뒤 관측은 보지 않는다(분류도 시점정확)."""
    na = _collapse(_obs(f, "ni_a", cut), tol)
    qd = {d for d, _ in _obs(f, "ni", cut)}
    ttm = set()
    for d, _ in na:
        if d in qd and any(e < d and e not in qd and TB._days_between(d, e) < YOY_LO for e, _ in na):
            ttm.add(d)
    return [(d, v) for d, v in na if d not in ttm], ttm


def fy_chain(a_obs, n):
    """회계연도 말(내림차순)에서 FY*, FY*−1, … FY*−n 기간말 — 한 걸음 320 ~ 410일(365 에 가장 가까운 것 · 같으면 최근)."""
    if not a_obs:
        return []
    ds = [d for d, _ in a_obs]
    ch = [ds[0]]
    while len(ch) <= n:
        cur, best = ch[-1], None
        for d in ds:
            if d >= cur:
                continue
            g = TB._days_between(cur, d)
            if g > YOY_HI:
                break
            if g >= YOY_LO and (best is None or abs(g - 365) < abs(best[0] - 365)):
                best = (g, d)
        if best is None:
            break
        ch.append(best[1])
    return ch


def rank_z(vals):
    """{키: 값} → {키: 순위 z}(같으면 평균 순위 · 순위의 평균 0 · sd 1(ddof=1)). 2개 미만이면 빈 dict."""
    from scipy.stats import rankdata
    ks = sorted(vals)
    if len(ks) < 2:
        return {}
    r = rankdata(np.array([vals[k] for k in ks], float), method="average")
    sd = float(r.std(ddof=1))
    if not sd > 0:
        return {}
    mu = float(r.mean())
    return {k: float((x - mu) / sd) for k, x in zip(ks, r)}


def zscore(vals):
    """{키: 값} → 평균 0 · sd 1(ddof=1) 선형 표준화."""
    ks = sorted(vals)
    if len(ks) < 2:
        return {}
    v = np.array([vals[k] for k in ks], float)
    sd = float(v.std(ddof=1))
    if not sd > 0:
        return {}
    mu = float(v.mean())
    return {k: float((x - mu) / sd) for k, x in zip(ks, v)}


def n_top(n):
    """ceil(0.30 × n) — 정수 산술."""
    return -(-TOP_NUM * n // TOP_DEN)


def cap_w(keys, mc):
    """시총 비례 + 한 이름 10% 상한(넘친 몫 비례 재배분 · eg30plus.cap_weights) — 키 정렬 순서로 넣는다."""
    return E.cap_weights({k: mc[k] for k in sorted(keys)}, NAME_CAP)


def select_top(score, mc):
    """점수 상위 ceil(0.30 × N) — 같으면 시총 큰 쪽 · 그다음 키."""
    ks = sorted(score, key=lambda k: (-score[k], -mc[k], k))
    return ks[:n_top(len(ks))]


def ivol(px, mk, i, win=IVOL_WIN, mn=IVOL_MIN):
    """252일 CAPM 잔차 sd — 일간 단순수익 · 절편 포함 OLS · 유효일 ≥ mn. 날짜 ≤ i 만."""
    j0 = max(0, i - win)
    a, b = np.asarray(px[j0:i + 1], float), np.asarray(mk[j0:i + 1], float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ri, rm = a[1:] / a[:-1] - 1.0, b[1:] / b[:-1] - 1.0
    ok = np.isfinite(ri) & np.isfinite(rm)
    if int(ok.sum()) < mn:
        return None
    X = np.column_stack([np.ones(int(ok.sum())), rm[ok]])
    y = ri[ok]
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ coef
    s = float(np.std(e, ddof=1))
    return s if s == s else None


def quarterly_ni(f, cut, tol=DATE_TOL):
    """분기 NI {기간말: 값} — Q1–Q3 = q 버킷(±tol 겹친 날짜는 최근 하나 · 회계연도 말 ±tol 안 값은 Q4 직접 태그라 뺀다 · TTM 태그 날짜의 q 는 남긴다)
    · Q4 = 연간 − 그 회계연도 안(FY 말 전 320일 안) q 정확히 세 개(아니면 Q4 없음)."""
    fy, _ttm = fy_ends(f, cut, tol)
    fyd = [d for d, _ in fy]
    q = _collapse(_obs(f, "ni", cut), tol)
    q13 = {d: v for d, v in q if not any(TB._days_between(d, y) <= tol for y in fyd)}
    out = dict(q13)
    for y, v in fy:
        ins = [d for d in q13 if d < y and TB._days_between(d, y) < YOY_LO]
        if len(ins) == 3:
            out[y] = v - sum(q13[d] for d in sorted(ins))
    return out


def fund_components(f, cut, tol=DATE_TOL):
    """재무 성분(마지막 제출값 · 기간말 ≤ cut) → ({성분: 값}, 쓴 기간말 최댓값, 기록)."""
    out, used = {}, []
    info = {"fy": None, "tol": 0, "stale": False, "eq_nonpos": False, "n_ttm": 0}
    fy, ttm = fy_ends(f, cut, tol)
    info["n_ttm"] = len(ttm)
    ch = fy_chain(fy, max(GROWTH_Y, NPOP_Y))
    nd = dict(fy)
    eq, at, li, de = (_obs(f, x, cut) for x in ("eq", "asset", "liab", "debt"))
    cfo, cx = _obs(f, "cfo_a", cut), _obs(f, "capex_a", cut)

    def get(obs, y):
        d, v = _at(obs, y, tol)
        if d is not None:
            used.append(d)
            if d != y:
                info["tol"] += 1
        return v

    if ch:
        y0 = ch[0]
        info["fy"] = y0
        if FY_FRESH_DAYS is not None and TB._days_between(cut, y0) > FY_FRESH_DAYS:
            info["stale"] = True                                   # 낡은 FY — FY 성분 전부 없음
            ch = []
    if ch:
        y0 = ch[0]
        used.append(y0)
        NI, EQ, A, L, D = nd[y0], get(eq, y0), get(at, y0), get(li, y0), get(de, y0)
        CF, CX = get(cfo, y0), get(cx, y0)
        if EQ is not None and EQ > 0:
            out["ROE"] = NI / EQ
        elif EQ is not None:
            info["eq_nonpos"] = True
        if A is not None and A > 0:
            out["ROA"] = NI / A
            if CF is not None and CX is not None:
                out["CFOA"] = (CF - CX) / A
            if CF is not None:
                out["ACC"] = -(NI - CF) / A
            if L is not None:
                out["LEV"] = -L / A
            if D is not None:
                out["LEV_DEBT"] = -D / A
        if len(ch) > GROWTH_Y:
            y5 = ch[GROWTH_Y]
            used.append(y5)
            NI5, EQ5, A5 = nd[y5], get(eq, y5), get(at, y5)
            CF5, CX5 = get(cfo, y5), get(cx, y5)
            if EQ5 is not None and EQ5 > 0:
                out["dROE"] = (NI - NI5) / EQ5
            if A5 is not None and A5 > 0:
                out["dROA"] = (NI - NI5) / A5
                if None not in (CF, CX, CF5, CX5):
                    out["dCFOA"] = ((CF - CX) - (CF5 - CX5)) / A5
        if len(ch) > NPOP_Y:
            nis = [nd[ch[j]] for j in range(NPOP_Y)]
            eqs = [get(eq, ch[j]) for j in range(NPOP_Y + 1)]
            used.extend(ch[:NPOP_Y + 1])
            den = sum(nis)
            if None not in eqs and den > 0:
                out["NPOP"] = sum(nis[j] - (eqs[j] - eqs[j + 1]) for j in range(NPOP_Y)) / den
    # EVOL — 분기 ROE sd(창이 5년이라 신선도는 창이 맡는다)
    qn = quarterly_ni(f, cut, tol)
    lo = TB._shift(cut, EVOL_DAYS)
    qs = sorted((d for d in qn if lo < d <= cut), reverse=True)[:EVOL_N]
    roes = []
    for d in qs:
        e = get(eq, d)
        if e is not None and e > 0:
            roes.append(qn[d] / e)
            used.append(d)
    if len(roes) >= EVOL_MIN:
        out["EVOL"] = -float(np.std(np.array(roes), ddof=1))
    umax = max(used) if used else None
    return out, umax, info


def seam_at(breaks, cut):
    """m 에 알 수 있는 이음매 — 단절 날짜(단절 뒤쪽 첫 관측) 중 ≤ cut 인 가장 최근 것. 컷 뒤 단절은 그때 몰랐다."""
    ks = [b for b in (breaks or []) if b <= cut]
    return max(ks) if ks else None


def share_breaks(Wd, t, k, f):
    """전 표본 주식수 단절 날짜들(내림차순 · tech_backtest.SPLIT_BREAKS) — f['sh_seam'] 은 그 첫째(가장 최근)와 같아야 한다."""
    if not f:
        return []
    FU = Wd.W["FUND"]
    key = k if FU.get(k) else t
    b = list(TB.SPLIT_BREAKS.get(key) or [])
    seam = f.get("sh_seam")
    assert (not seam and not b) or (b and b[0] == seam), "단절 목록과 sh_seam 이 어긋난다 %s %s %s" % (key, seam, b[:3])
    return b


def eiss(f, d, breaks):
    """EISS = −ln(SH_t/SH_t−1y) — x-shiss 계열(sh_u 또는 sh) · 90일 지연 · 이음매는 m 에 알 수 있는 단절만. → (값, 쓴 기간말, 기록)."""
    cut = TB._shift(d, LAG)
    seam = seam_at(breaks, cut)
    assert seam is None or seam <= cut, "미래 이음매 %s > 컷 %s" % (seam, cut)
    info = {"seam": seam, "stale": False}
    pr = TB.yoy_pair(f.get("sh_u") or f.get("sh"), d, LAG, seam=seam)
    if pr and pr[1] and pr[3] and pr[1] > 0 and pr[3] > 0:
        if FY_FRESH_DAYS is not None and TB._days_between(cut, pr[0]) > FY_FRESH_DAYS:
            info["stale"] = True
            return None, None, info
        return -math.log(pr[1] / pr[3]), pr[0], info
    return None, None, info


def pit_sector(Wd, t, k, m):
    """C2 위약 무리 — 시점정확 GICS 만(그달 표 → 가장 가까운 이전 달). 이후 달 · 오늘 분류로만 서면 '?'. → (업종, 출처)."""
    s = Wd.sector(t, k, m)
    src = Wd.sector_src(t, k, m)
    if src == "month":
        return str(s or "?"), "month"
    if src == "near":
        cks = [c for c in (Wd.cikmap.get(t), Wd.cikmap.get(k), Wd.cikmap.get((t or "").replace("-", "."))) if c]
        tks = [x.replace("-", ".") for x in (t, k) if x]
        keys = ["c:" + c for c in cks] + ["t:" + x for x in tks]
        if any(ym < m for key in keys for ym, _ in Wd.Gtl.get(key, ())):
            return str(s or "?"), "near_prev"                    # _sector_lookup 은 이전 달을 먼저 고른다
        return "?", "near_next"
    return "?", str(src)


# ── 달 원자료 · 점수 ──────────────────────────────────────────────────────
def month_raw(Wd, m):
    """달 m 말 결정 — 유니버스 · 시총 · 업종 · 성분 원값(얼림 전 전부 + LEV_DEBT) · 진단. 날짜 단언을 여기서 건다."""
    cache = Wd.__dict__.setdefault("_qmj_raw", {})
    if m in cache:
        return cache[m]
    i = Wd.me[m]
    d = Wd.dates[i]
    cut = TB._shift(d, LAG)
    assert Wd.dates[i][:7] == m and (i + 1 >= len(Wd.dates) or Wd.dates[i + 1][:7] != m), "월말 자리가 그달 마지막 거래일이 아니다 %s" % m
    U = Wd.universe(m, "union", False)
    keys = [k for _, k in U]
    assert len(set(keys)) == len(keys), "유니버스 가격 키 중복 %s" % m
    allc = [c for p in PILLARS for c in COMPONENTS[p]] + list(PROBE_EXTRA)
    vals = {c: {} for c in allc}
    names, mc, sec, src = {}, {}, {}, {}
    umax, n_tol, n_nofund = None, 0, 0
    diag = {"stale_fy": [], "stale_eiss": [], "eq_nonpos": [], "ttm": [], "seam_fixed": [], "seam_future_missing": [], "fy_age": {}}
    for t, k in sorted(U, key=lambda x: x[1]):
        names[k] = t
        mc[k] = Wd.mcap(t, k, i)
        assert mc[k] and mc[k] > 0 and Wd.PX[k][i] > 0, "시총 · 가격이 없는 유니버스 이름 %s %s" % (m, k)
        sec[k], src[k] = pit_sector(Wd, t, k, m)
        f = Wd.fund(t, k)
        if not f:
            n_nofund += 1
        br = share_breaks(Wd, t, k, f)
        r, u, info = fund_components(f or {}, cut)
        v, u2, ei = eiss(f or {}, d, br)
        if v is not None:
            r["EISS"] = v
        for x in (u, u2):
            if x is not None:
                umax = x if umax is None or x > umax else umax
        n_tol += info["tol"]
        if info["fy"]:
            diag["fy_age"][k] = TB._days_between(cut, info["fy"])
        if info["stale"]:
            diag["stale_fy"].append(k)
        if info["eq_nonpos"]:
            diag["eq_nonpos"].append(k)
        if info["n_ttm"]:
            diag["ttm"].append(k)
        if ei["stale"]:
            diag["stale_eiss"].append(k)
        fs = (f or {}).get("sh_seam")
        if fs and fs > cut:                                      # 전 표본 이음매가 미래 — 옛 코드는 여기서 EISS 가 늘 없었다
            (diag["seam_fixed"] if v is not None else diag["seam_future_missing"]).append(k)
        b = Wd.fp_beta(k, i)
        if b is not None:
            r["BAB"] = -b
        iv = ivol(Wd.PX[k], Wd.IX_TR, i)
        if iv is not None:
            r["IVOL"] = -iv
        for c, x in r.items():
            if c in vals and x is not None and x == x and math.isfinite(x):
                vals[c][k] = float(x)
    # 🚨 시점 단언 — 쓴 재무 · 주식수 기간말 ≤ m 말 − 90일 < m 의 마지막 거래일
    assert umax is None or umax <= cut < d, "재무 기간말 %s 가 컷 %s 을 넘는다(%s)" % (umax, cut, m)
    R = {"m": m, "i": i, "d": d, "cut": cut, "keys": sorted(keys), "names": names, "mc": mc, "sec": sec, "sec_src": src, "vals": vals,
         "umax": umax, "n_tol": n_tol, "n_nofund": n_nofund, "diag": diag}
    cache[m] = R
    return R


def frozen_list():
    if FROZEN is None:
        raise RuntimeError("커버리지 얼림이 비었다 — python build/q_qmj.py --probe 로 재고 FROZEN 을 적어라")
    return FROZEN


def aggregate(vals, keys, F, lev_src=None):
    """성분 원값 → 성분 순위 z → 기둥 선형 z(최소 성분 수) → 퀄리티 선형 z(≥ QUAL_MIN 기둥) · 안전 뺀 z(남은 비안전 기둥 모두). 얼린 성분만."""
    NS_P = [p for p in PILLARS if p != "safe" and F[p]]          # 안전 뺀 팔 — 얼림에서 남은 비안전 기둥 모두(카드는 3기둥 · 성장이 빠져 2기둥)
    src = {c: (vals["LEV_DEBT"] if (c == "LEV" and lev_src == "debt") else vals[c]) for p in PILLARS for c in F[p]}
    z = {c: rank_z(src[c]) for c in sorted(src)}
    pil = {}
    for p in PILLARS:
        raw = {}
        if F[p]:
            for k in keys:
                zs = [z[c][k] for c in F[p] if k in z[c]]
                if len(zs) >= PILLAR_MIN[p]:
                    raw[k] = float(np.mean(zs))
        pil[p] = zscore(raw)
    qraw, nsraw = {}, {}
    for k in keys:
        ps = [pil[p][k] for p in PILLARS if k in pil[p]]
        if len(ps) >= QUAL_MIN:
            qraw[k] = float(np.mean(ps))
        if NS_P and all(k in pil[p] for p in NS_P):
            nsraw[k] = float(np.mean([pil[p][k] for p in NS_P]))
    return {"z": z, "pil": pil, "Q": zscore(qraw), "NS": zscore(nsraw)}


def month_scores(Wd, m):
    cache = Wd.__dict__.setdefault("_qmj_sc", {})
    if m in cache:
        return cache[m]
    R = month_raw(Wd, m)
    S = aggregate(R["vals"], R["keys"], frozen_list(), LEV_SRC)
    S.update({"m": m, "R": R})
    cache[m] = S
    return S


# ── 목표 비중 ─────────────────────────────────────────────────────────────
def _tg(keys, R):
    w = cap_w(keys, R["mc"])
    return {"w": w, "names": {k: R["names"][k] for k in w}}


def targets_top(Wd, which):
    """which: 'Q'(규칙) · 'NS'(안전 뺀) · 기둥 이름(단일 기둥) → {편입월: 목표}."""
    T = {}
    for m in Wd.months:
        S = month_scores(Wd, m)
        sc = S[which] if which in ("Q", "NS") else S["pil"][which]
        T[m] = _tg(select_top(sc, S["R"]["mc"]), S["R"])
    return T


def targets_all_scored(Wd):
    return {m: _tg(sorted(month_scores(Wd, m)["Q"]), month_raw(Wd, m)) for m in Wd.months}


def targets_priced(Wd):
    return {m: _tg(month_raw(Wd, m)["keys"], month_raw(Wd, m)) for m in Wd.months}


def perm_prep(Wd):
    """위약 준비 — 달마다 퀄리티가 선 이름(키 정렬) · 퀄리티 · 시총 · 시점정확 업종 무리(업종 이름 정렬 순 · '?' 도 한 무리)."""
    P = {}
    for m in Wd.months:
        S = month_scores(Wd, m)
        R = S["R"]
        ks = sorted(S["Q"])
        secs = [R["sec"][k] for k in ks]
        groups = [np.array([j for j, s in enumerate(secs) if s == g], int) for g in sorted(set(secs))]
        P[m] = {"keys": ks, "q": np.array([S["Q"][k] for k in ks]), "mc": np.array([R["mc"][k] for k in ks]),
                "groups": groups, "n_sel": n_top(len(ks)), "R": R}
    return P


def perm_targets(P, rng):
    """업종 안에서 퀄리티를 섞고 같은 규칙(상위 30% · 같으면 시총 큰 쪽 · 시총가중 10%). rng=None 이면 섞지 않는다(참 규칙과 같아야 한다)."""
    T = {}
    for m in sorted(P):
        p = P[m]
        q = p["q"].copy()
        if rng is not None:
            for idx in p["groups"]:
                q[idx] = q[idx][rng.permutation(len(idx))]
        order = np.lexsort((np.arange(len(q)), -p["mc"], -q))
        sel = [p["keys"][j] for j in order[:p["n_sel"]]]
        T[m] = _tg(sel, p["R"])
    return T


def targets_hash(T):
    return hashlib.sha256(json.dumps(T, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def _turn1(a, b):
    """두 비중 사이 편도 회전 — 키 정렬 순서로 더한다(PYTHONHASHSEED 무관)."""
    return 0.5 * sum(abs(b.get(k, 0.0) - a.get(k, 0.0)) for k in sorted(set(a) | set(b)))


def target_turn(T):
    """목표 대 목표 편도 회전(드리프트 없음 · 구조만) — 달 평균 × 12."""
    ms = sorted(T)
    tt = [_turn1(T[a]["w"], T[b]["w"]) for a, b in zip(ms, ms[1:])]
    return float(np.mean(tt) * 12) if tt else None


# ── 커버리지 얼림(2016-08 · 커버리지만) ────────────────────────────────────
def _fy_cause(f, cut, comp, r, info):
    """FY 성분 결측 원인(커버리지 진단만)."""
    if not f:
        return "no_fund_file"
    na_all = f.get("ni_a") or []
    if not na_all:
        return "no_ni_a_at_all"
    fy, _ = fy_ends(f, cut)
    if not fy:
        return "ni_a_starts_after_cut"                           # 수집 잘림(KEEP_A · TTM 태그) · 새 CIK
    if info["stale"]:
        return "stale_fy"
    if comp in ("dROE", "dROA", "dCFOA", "NPOP"):
        ch = fy_chain(fy, max(GROWTH_Y, NPOP_Y))
        if len(ch) <= GROWTH_Y:
            return "short_hist_first_fy_after_2010" if min(d for d, _ in na_all) > "2010-12-31" else "chain_gap"
    return "item_missing_or_denominator"


def coverage_probe(Wd, m=FREEZE_M, detail=False):
    """성분마다 유니버스 시총 중 값이 선 몫 → 얼린 목록 · LEV 원천. detail=True 면 결측 원인 · LEV 읽기 민감도(커버리지만). 수익은 없다."""
    R = month_raw(Wd, m)
    tot = sum(R["mc"].values())
    cov = {c: float(sum(R["mc"][k] for k in v) / tot) for c, v in R["vals"].items()}
    cnt = {c: len(v) for c, v in R["vals"].items()}
    F = {p: [c for c in COMPONENTS[p] if c != "LEV" and cov[c] >= COV_MIN] for p in PILLARS}
    if cov["LEV"] >= COV_MIN:
        lev = "liab"
    elif cov["LEV_DEBT"] >= COV_MIN:
        lev = "debt"
    else:
        lev = None
    if lev:
        F["safe"] = [c for c in COMPONENTS["safe"] if c in F["safe"] or c == "LEV"]
    out = {"m": m, "n_univ": len(R["keys"]), "cov": cov, "count": cnt, "frozen": F, "lev_src": lev}
    if not detail:
        return out
    cut = R["cut"]
    pct = lambda ks: round(100.0 * sum(R["mc"][k] for k in ks) / tot, 2)
    att = {c: {} for c in FY_COMPS}
    who = {}
    lev_s = {"DEBT_asof": [], "DEBT_asof_and_ASSET_asof_pos": [], "DEBT_at_FY": [], "LIAB_asof": [], "LIAB_at_FY": []}
    for k in R["keys"]:
        t = R["names"][k]
        f = Wd.fund(t, k) or {}
        r, _u, info = fund_components(f, cut)
        for c in FY_COMPS:
            if k in R["vals"][c]:
                continue
            why = _fy_cause(f, cut, c, r, info)
            att[c].setdefault(why, []).append(k)
            if why in ("ni_a_starts_after_cut", "short_hist_first_fy_after_2010", "no_fund_file", "no_ni_a_at_all"):
                who.setdefault(why, set()).add(k)
        dbt, ast, lia = _obs(f, "debt", cut), _obs(f, "asset", cut), _obs(f, "liab", cut)
        if dbt:
            lev_s["DEBT_asof"].append(k)
            if ast and ast[0][1] and ast[0][1] > 0:
                lev_s["DEBT_asof_and_ASSET_asof_pos"].append(k)
        if lia:
            lev_s["LIAB_asof"].append(k)
        fy, _ = fy_ends(f, cut)
        if fy and not info["stale"]:
            if _at(dbt, fy[0][0])[0] is not None:
                lev_s["DEBT_at_FY"].append(k)
            if _at(lia, fy[0][0])[0] is not None:
                lev_s["LIAB_at_FY"].append(k)
    out["attribution_pct_of_union_cap"] = {c: {w: pct(ks) for w, ks in sorted(v.items())} for c, v in att.items()}
    out["attribution_top_names"] = {w: [(R["names"][k], pct([k])) for k in sorted(ks, key=lambda x: -R["mc"][x])[:12]] for w, ks in sorted(who.items())}
    out["sensitivity_lev_pct"] = {s: pct(ks) for s, ks in lev_s.items()}
    out["sensitivity_lev_note"] = ("LEV_DEBT(FY 맞춤 −DEBT/ASSET · 얼림에 쓴 읽기) %.2f%% vs DEBT as-of %.2f%%(카드 data 절의 80.6%%) · "
                                   "DEBT as-of ∧ ASSET as-of > 0 %.2f%%" % (100 * cov["LEV_DEBT"], pct(lev_s["DEBT_asof"]), pct(lev_s["DEBT_asof_and_ASSET_asof_pos"])))
    # 날짜 허용 0 이면 얼림이 같은가(커버리지만)
    v0 = {c: {} for c in FY_COMPS + ("EVOL",)}
    for k in R["keys"]:
        r0, _u, _i = fund_components(Wd.fund(R["names"][k], k) or {}, cut, tol=0)
        for c in v0:
            if c in r0 and math.isfinite(r0[c]):
                v0[c][k] = 1
    out["sensitivity_tol0_cov"] = {c: round(float(sum(R["mc"][k] for k in v) / tot), 4) for c, v in v0.items()}
    return out


# ── 단위 시험(합성 자료만) ─────────────────────────────────────────────────
class _FakeW:
    """pit_sector 시험용 가짜 World."""
    def __init__(self):
        self.cikmap = {"AAA": "c1", "BBB": "c2", "CCC": "c3", "DDD": "c4"}
        self.Gtl = {"c:c2": [("2016-05", "Energy")], "c:c3": [("2017-01", "Utilities")]}
        self._s = {"AAA": ("Health Care", "month"), "BBB": ("Energy", "near"), "CCC": ("Utilities", "near"), "DDD": ("Materials", "today")}

    def sector(self, t, k, m):
        return self._s[t][0]

    def sector_src(self, t, k, m):
        return self._s[t][1]


def selftest():
    T = {}
    # 순위 z — 같은 값 평균 순위 · 평균 0 · sd 1 · 입력 순서 무관
    a = rank_z({"a": 1.0, "b": 2.0, "c": 2.0, "d": 5.0})
    b = rank_z({"d": 5.0, "c": 2.0, "a": 1.0, "b": 2.0})
    T["rank_z_ties"] = abs(a["b"] - a["c"]) < 1e-15 and a == b
    T["rank_z_moments"] = abs(np.mean(list(a.values()))) < 1e-12 and abs(np.std(list(a.values()), ddof=1) - 1) < 1e-12
    zz = zscore({"x": 1.0, "y": 3.0, "z": 8.0})
    T["zscore_moments"] = abs(sum(zz.values())) < 1e-12 and abs(np.std(list(zz.values()), ddof=1) - 1) < 1e-12
    T["n_top"] = [n_top(n) for n in (1, 9, 10, 100, 101, 433)] == [1, 3, 3, 30, 31, 130]
    sc = {"a": 1.0, "b": 1.0, "c": 0.5, "d": 2.0}
    mc = {"a": 10.0, "b": 20.0, "c": 5.0, "d": 1.0}
    T["select_tie_cap"] = select_top(sc, mc) == ["d", "b"]
    mcs = {chr(65 + j): float(100 - 7 * j) for j in range(12)}
    mcs["A"] = 5000.0
    w = cap_w(list(mcs), mcs)
    T["cap_weights"] = abs(sum(w.values()) - 1) < 1e-12 and max(w.values()) <= NAME_CAP + 1e-12
    # 회계연도 사슬 — 52/53주 · 빈 해에서 멈춤
    ann = [("2016-01-02", 1.0), ("2015-01-03", 1.0), ("2013-12-28", 1.0), ("2012-12-29", 1.0), ("2011-12-31", 1.0), ("2011-01-01", 1.0), ("2009-01-03", 1.0)]
    ch = fy_chain(ann, 6)
    T["fy_chain"] = ch == ["2016-01-02", "2015-01-03", "2013-12-28", "2012-12-29", "2011-12-31", "2011-01-01"]
    # 겹친 날짜 — 최근 하나
    T["collapse"] = _collapse([("2019-11-02", 1.0), ("2019-10-31", 2.0), ("2018-11-03", 3.0), ("2018-10-31", 4.0), ("2017-10-31", 5.0)]) == \
        [("2019-11-02", 1.0), ("2018-11-03", 3.0), ("2017-10-31", 5.0)]
    # Q4 = 연간 − Q1 − Q2 − Q3 · 연간 기간말의 q 값(직접 Q4 태그)은 공식으로 바뀐다
    f = {"ni_a": [("2015-12-31", 100.0), ("2014-12-31", 80.0)],
         "ni": [("2015-12-31", 999.0), ("2015-09-30", 30.0), ("2015-06-30", 20.0), ("2015-03-31", 10.0), ("2014-09-30", 5.0), ("2014-06-30", 5.0)]}
    qn = quarterly_ni(f, "2016-06-30")
    T["q4_formula"] = qn.get("2015-12-31") == 40.0 and "2014-12-31" not in qn and qn.get("2015-03-31") == 10.0
    # TTM 태그(AMZN 꼴) — 연간 버킷이 분기마다 TTM · q 는 10-Q 날짜에만 → 회계연도 말은 12-31 만 · TTM 날짜의 q 는 분기로 남는다
    qe = ["%d-%s" % (y, md) for y in (2024, 2023, 2022, 2021) for md in ("12-31", "09-30", "06-30", "03-31")]
    qe = [x for x in qe if "2021-09-30" <= x <= "2024-03-31"]
    fa = {"ni_a": [(x, 400.0 + j) for j, x in enumerate(qe)],
          "ni": [(x, 90.0 + j) for j, x in enumerate(qe) if not x.endswith("12-31")]}
    fy, ttm = fy_ends(fa, "2024-05-01")
    T["ttm_fy_ends"] = [d for d, _ in fy] == ["2023-12-31", "2022-12-31", "2021-12-31", "2021-09-30"] and \
        ttm == {x for x in qe if not x.endswith("12-31") and x != "2021-09-30"}
    qa = quarterly_ni(fa, "2024-05-01")
    dq = dict(fa["ni"])
    T["ttm_quarters"] = (qa.get("2024-03-31") == dq["2024-03-31"] and
                         abs(qa["2023-12-31"] - (dict(fa["ni_a"])["2023-12-31"] - dq["2023-09-30"] - dq["2023-06-30"] - dq["2023-03-31"])) < 1e-12)
    # 재무 성분 — 합성 회사 한 곳(값을 손으로 셈)
    ys = ["%d-12-31" % y for y in range(2016, 2009, -1)]
    f2 = {"ni_a": [(y, 10.0 + j) for j, y in enumerate(ys)], "eq": [(y, 100.0 - j) for j, y in enumerate(ys)],
          "asset": [(y, 200.0) for y in ys], "liab": [(ys[0], 50.0)], "cfo_a": [(y, 12.0) for y in ys], "capex_a": [(y, 2.0) for y in ys]}
    r, umax, info = fund_components(f2, "2017-06-01")
    nis, eqs = [10.0 + j for j in range(5)], [100.0 - j for j in range(6)]
    npop = sum(nis[j] - (eqs[j] - eqs[j + 1]) for j in range(5)) / sum(nis)
    T["components"] = (abs(r["ROE"] - 0.10) < 1e-12 and abs(r["ROA"] - 0.05) < 1e-12 and abs(r["CFOA"] - 0.05) < 1e-12
                       and abs(r["ACC"] - (-(10 - 12) / 200)) < 1e-12 and abs(r["LEV"] + 0.25) < 1e-12
                       and abs(r["dROE"] - (10 - 15) / 95) < 1e-12 and abs(r["dROA"] - (10 - 15) / 200) < 1e-12
                       and abs(r["dCFOA"]) < 1e-12 and abs(r["NPOP"] - npop) < 1e-12 and umax <= "2017-06-01")
    # 시점 — 컷 뒤 관측은 쓰지 않는다
    r2, umax2, _ = fund_components(f2, "2016-06-01")
    T["pit_cut"] = umax2 is not None and umax2 <= "2016-06-01" and abs(r2["ROE"] - 11.0 / 99.0) < 1e-12
    # 낡은 FY — 컷 − FY* > 550일이면 FY 성분 없음
    r3, _u3, i3 = fund_components(f2, "2018-07-06")                      # 2016-12-31 뒤 552일
    r4, _u4, i4 = fund_components(f2, "2018-07-04")                      # 550일
    T["stale_fy"] = i3["stale"] and "ROE" not in r3 and "ROA" not in r3 and (not i4["stale"]) and "ROE" in r4
    # 음의 자본 → ROE 없음 · 기록
    f6 = dict(f2, eq=[(ys[0], -5.0)] + f2["eq"][1:])
    r6, _u6, i6 = fund_components(f6, "2017-06-01")
    T["eq_nonpos"] = "ROE" not in r6 and "ROA" in r6 and i6["eq_nonpos"]
    # 날짜 맞춤 ±7일
    T["date_tol"] = _at([("2015-11-01", 1.0), ("2015-10-20", 2.0)], "2015-10-31") == ("2015-11-01", 1.0) and _at([("2015-10-20", 2.0)], "2015-10-31") == (None, None) \
        and _at([("2015-11-01", 1.0)], "2015-10-31", tol=0) == (None, None)
    # NPOP 분모 ≤ 0 → 없음 · EVOL 최소 12
    f3 = dict(f2, ni_a=[(y, -1.0) for y in ys])
    T["npop_den"] = "NPOP" not in fund_components(f3, "2017-06-01")[0]
    qd = ["%d-%02d-%s" % (y, mm, dd) for y in range(2016, 2011, -1) for mm, dd in ((9, "30"), (6, "30"), (3, "31"))]
    f5 = {"ni": [(d, 1.0) for d in qd[:11]], "eq": [(d, 10.0) for d in qd[:11]]}
    T["evol_min"] = "EVOL" not in fund_components(f5, "2017-06-01")[0]
    # EVOL 정확값 — Q4 공식이 든 합성 계열(분기 NI · 연간 NI · 분기말 EQ)
    yrs = list(range(2016, 2010, -1))
    qv = {}
    fa7, fq7, fe7 = [], [], []
    for j, y in enumerate(yrs):
        q1, q2, q3, q4 = 1.0 + 0.1 * j, 2.0 - 0.05 * j, 1.5 + 0.2 * (j % 2), 0.7 + 0.3 * j
        fa7.append(("%d-12-31" % y, q1 + q2 + q3 + q4))
        for md, v in (("09-30", q3), ("06-30", q2), ("03-31", q1)):
            fq7.append(("%d-%s" % (y, md), v))
        for md in ("12-31", "09-30", "06-30", "03-31"):
            fe7.append(("%d-%s" % (y, md), 50.0 + 3 * j + (md == "06-30")))
        qv.update({"%d-12-31" % y: q4, "%d-09-30" % y: q3, "%d-06-30" % y: q2, "%d-03-31" % y: q1})
    f7 = {"ni_a": fa7, "ni": sorted(fq7, reverse=True), "eq": sorted(fe7, reverse=True)}
    cut7 = "2017-03-01"
    lo7 = TB._shift(cut7, EVOL_DAYS)
    eqd = dict(fe7)
    qs7 = sorted((d for d in qv if lo7 < d <= cut7), reverse=True)[:EVOL_N]
    want = -float(np.std(np.array([qv[d] / eqd[d] for d in qs7]), ddof=1))
    ev7 = fund_components(f7, cut7)[0].get("EVOL")
    T["evol_exact"] = ev7 is not None and len(qs7) == 20 and abs(ev7 - want) < 1e-12
    # IVOL — 같은 창의 명시적 lstsq 와 1e-12 · 최소 유효일
    rs = np.random.default_rng(Q.SEED)
    rm = rs.normal(0, 0.01, 400)
    eps = rs.normal(0, 0.02, 400)
    mk = np.cumprod(np.r_[1.0, 1 + rm])
    px = np.cumprod(np.r_[1.0, 1 + 0.001 + 1.3 * rm + eps])
    iv = ivol(px, mk, 400)
    ri = px[148:401][1:] / px[148:401][:-1] - 1
    rmm = mk[148:401][1:] / mk[148:401][:-1] - 1
    Xx = np.column_stack([np.ones(len(rmm)), rmm])
    cf = np.linalg.lstsq(Xx, ri, rcond=None)[0]
    want_iv = float(np.std(ri - Xx @ cf, ddof=1))
    T["ivol_exact"] = iv is not None and len(ri) == IVOL_WIN and abs(iv - want_iv) < 1e-12
    px2 = px.copy(); px2[:300] = np.nan
    T["ivol_min"] = ivol(px2, mk, 400) is None
    # EISS 이음매 — 미래 단절은 그 전 짝을 지우지 않는다 · 알려진 단절을 건너는 짝은 버린다 · 단절이 둘이면 컷 전 가장 최근 것
    shq = ["%d-%s" % (y, md) for y in range(2020, 2011, -1) for md in ("12-31", "09-30", "06-30", "03-31")]
    sh = [(d, (160.0 if d >= "2020-03-31" else 100.0) * (1.0 + 0.002 * (2020 - int(d[:4])) * (-1))) for d in shq]
    fsh = {"sh_u": sh, "sh_seam": "2020-03-31"}
    v_a, d_a, i_a = eiss(fsh, "2016-08-31", ["2020-03-31"])
    shd = dict(sh)
    T["eiss_future_seam_kept"] = v_a is not None and i_a["seam"] is None and abs(v_a + math.log(shd["2016-03-31"] / shd["2015-03-31"])) < 1e-12
    T["eiss_old_seam_erased"] = TB.yoy_pair(sh, "2016-08-31", LAG, seam="2020-03-31") is None          # 옛 코드(전 표본 이음매)는 지웠다
    v_b, _d, i_b = eiss(fsh, "2020-08-31", ["2020-03-31"])
    T["eiss_known_seam_blocks"] = v_b is None and i_b["seam"] == "2020-03-31"
    sh2 = [(d, v * (1.7 if d >= "2015-06-30" else 1.0)) for d, v in sh]
    fsh2 = {"sh_u": sh2, "sh_seam": "2020-03-31"}
    v_c, _d, i_c = eiss(fsh2, "2016-08-31", ["2020-03-31", "2015-06-30"])
    v_d, _d, i_d = eiss(fsh2, "2017-08-31", ["2020-03-31", "2015-06-30"])
    T["eiss_multi_break"] = v_c is None and i_c["seam"] == "2015-06-30" and v_d is not None and i_d["seam"] == "2015-06-30"
    T["seam_at"] = seam_at(["2020-03-31", "2015-06-30"], "2016-06-01") == "2015-06-30" and seam_at(["2020-03-31"], "2016-06-01") is None
    # 집계 — 기둥 최소 성분 수 · 3기둥 모두 필수 · 안전 뺀 팔은 수익성 · 환원 둘 다
    Fz = {"prof": ["ROE", "ROA"], "grow": [], "safe": ["BAB", "IVOL", "EVOL"], "pay": ["EISS"]}
    ks = ["n%02d" % j for j in range(12)]
    vv = {c: {} for p in PILLARS for c in COMPONENTS[p]}
    vv["LEV_DEBT"] = {}
    for j, k in enumerate(ks):
        for c in ("ROE", "ROA", "BAB", "IVOL", "EVOL", "EISS"):
            vv[c][k] = float((j * 7 + len(c)) % 11)
    del vv["ROE"]["n00"]                         # 수익성 1성분 → 기둥 없음 → 퀄리티 없음 · 안전 뺀 팔에서도 없음
    del vv["BAB"]["n01"]; del vv["IVOL"]["n01"]  # 안전 1성분 → 안전 없음 → 퀄리티 없음 · 안전 뺀 팔에는 있음
    del vv["EISS"]["n02"]                        # 환원 없음 → 둘 다 없음
    del vv["EVOL"]["n03"]                        # 안전 2성분 → 기둥 선다
    Sg = aggregate(vv, ks, Fz)
    qv_ = list(Sg["Q"].values())
    T["aggregate_min"] = (sorted(Sg["Q"]) == [k for k in ks if k not in ("n00", "n01", "n02")] and
                          sorted(Sg["NS"]) == [k for k in ks if k not in ("n00", "n02")] and "n03" in Sg["pil"]["safe"] and
                          "n01" not in Sg["pil"]["safe"] and "n00" not in Sg["pil"]["prof"])
    T["aggregate_moments"] = abs(np.mean(qv_)) < 1e-12 and abs(np.std(qv_, ddof=1) - 1) < 1e-12
    k5 = "n05"
    pm = {p: Sg["pil"][p][k5] for p in ("prof", "safe", "pay")}
    raw_all = {k: float(np.mean([Sg["pil"][p][k] for p in ("prof", "safe", "pay")])) for k in Sg["Q"]}
    T["aggregate_formula"] = abs(Sg["Q"][k5] - zscore(raw_all)[k5]) < 1e-12 and abs(raw_all[k5] - np.mean(list(pm.values()))) < 1e-12
    # 업종(C2 무리) — 그달 · 이전 달만 · 이후 달 · 오늘은 '?'
    fw = _FakeW()
    T["pit_sector"] = ([pit_sector(fw, t, t, "2016-08") for t in ("AAA", "BBB", "CCC", "DDD")] ==
                       [("Health Care", "month"), ("Energy", "near_prev"), ("?", "near_next"), ("?", "today")])
    # 위약 — 업종 안 섞기는 업종별 값 묶음을 지키고, 씨앗이 같으면 같다 · 섞지 않으면 참 규칙과 같다
    keys = ["k%02d" % j for j in range(40)]
    Rf = {"mc": {k: float(1 + (j * 37) % 17) for j, k in enumerate(keys)}, "names": {k: k.upper() for k in keys}}
    secs = ["S%d" % (j % 4) for j in range(40)]
    qv2 = np.linspace(-2, 2, 40)
    Pm = {"2016-08": {"keys": keys, "q": qv2, "mc": np.array([Rf["mc"][k] for k in keys]),
                      "groups": [np.array([j for j, s in enumerate(secs) if s == g]) for g in sorted(set(secs))], "n_sel": n_top(40), "R": Rf}}
    t0 = perm_targets(Pm, None)["2016-08"]
    sel_true = select_top({k: float(q) for k, q in zip(keys, qv2)}, Rf["mc"])
    T["perm_identity"] = sorted(t0["w"]) == sorted(sel_true)
    t1 = perm_targets(Pm, np.random.default_rng(Q.SEED + 1))["2016-08"]
    t1b = perm_targets(Pm, np.random.default_rng(Q.SEED + 1))["2016-08"]
    T["perm_seed"] = t1 == t1b and abs(sum(t1["w"].values()) - 1) < 1e-12 and len(t1["w"]) == n_top(40)
    qq = qv2.copy()
    rg = np.random.default_rng(Q.SEED + 2)
    for idx in Pm["2016-08"]["groups"]:
        qq[idx] = qq[idx][rg.permutation(len(idx))]
    T["perm_within_sector"] = all(sorted(qq[idx]) == sorted(qv2[idx]) for idx in Pm["2016-08"]["groups"]) and not np.allclose(qq, qv2)
    T["hash_stable"] = targets_hash({"b": {"w": {"y": 0.5, "x": 0.5}}}) == targets_hash({"b": {"w": {"x": 0.5, "y": 0.5}}})
    wa = {"x%d" % j: 0.1 + 0.01 * j for j in range(9)}
    wb = {"x%d" % j: 0.12 - 0.003 * j for j in range(3, 14)}
    T["turn_order_free"] = _turn1(wa, wb) == _turn1(dict(reversed(list(wa.items()))), dict(reversed(list(wb.items()))))
    return {"ok": all(bool(v) for v in T.values()), "tests": {k: bool(v) for k, v in T.items()}}


# ── 구성 점검(수익 없음) ───────────────────────────────────────────────────
def _check_targets(Wd, T, tag, nmin=10):
    out = {"n_min": None, "n_max": None, "max_w": 0.0}
    for m, tg in T.items():
        i = Wd.me[m]
        w = tg["w"]
        s = sum(w.values())
        assert abs(s - 1.0) < 1e-9, "%s %s 비중 합 %.12f" % (tag, m, s)
        assert max(w.values()) <= NAME_CAP + 1e-9, "%s %s 최대 비중 %.4f > 10%%" % (tag, m, max(w.values()))
        assert all(Wd.PX[k][i] == Wd.PX[k][i] and Wd.PX[k][i] > 0 for k in w), "%s %s 가격 없는 목표" % (tag, m)
        assert len(w) >= nmin, "%s %s 보유 %d < %d" % (tag, m, len(w), nmin)
        n = len(w)
        out["n_min"] = n if out["n_min"] is None else min(out["n_min"], n)
        out["n_max"] = n if out["n_max"] is None else max(out["n_max"], n)
        out["max_w"] = max(out["max_w"], max(w.values()))
    out["turn_target"] = target_turn(T)
    out["hash"] = targets_hash(T)[:16]
    return out


def _top_names(R, ks, n=6):
    return [R["names"][k] for k in sorted(ks, key=lambda x: -R["mc"][x])[:n]]


def month_log(Wd, T, T0=None):
    """편입별 진단(구조만) — 성분 · 기둥 개수 · 커버리지 · 보유 · 최대 비중 · 목표 회전 · EG30 겹침 · 이음매 · 낡은 FY · 음의 자본 · 업종 출처."""
    rows = []
    prev = None
    v0m = sorted(T0) if T0 else []
    for m in Wd.months:
        S = month_scores(Wd, m)
        R = S["R"]
        D = R["diag"]
        tot = sum(R["mc"].values())
        cv = lambda ks: float(sum(R["mc"][k] for k in ks) / tot)
        w = T[m]["w"]
        roe_block = [k for k in D["eq_nonpos"] if k not in S["Q"]]
        srcs = {}
        for k in S["Q"]:
            srcs[R["sec_src"][k]] = srcs.get(R["sec_src"][k], 0) + 1
        row = {"m": m, "n_univ": len(R["keys"]), "n_comp": {c: len(v) for c, v in S["z"].items()},
               "cov_comp": {c: round(cv(v), 4) for c, v in S["z"].items()},
               "n_pillar": {p: len(S["pil"][p]) for p in PILLARS}, "cov_pillar": {p: round(cv(S["pil"][p]), 4) for p in PILLARS},
               "n_scored": len(S["Q"]), "cov_scored": round(cv(S["Q"]), 4), "n_held": len(w), "max_w": round(max(w.values()), 5),
               "turn": (round(_turn1(prev, w), 5) if prev is not None else None),
               "n_date_tol": R["n_tol"], "n_nofund": R["n_nofund"], "fund_max_end": R["umax"], "cut": R["cut"],
               "seam_fixed": {"n": len(D["seam_fixed"]), "cap": round(cv(D["seam_fixed"]), 4), "top": _top_names(R, D["seam_fixed"])},
               "seam_future_still_missing": {"n": len(D["seam_future_missing"]), "cap": round(cv(D["seam_future_missing"]), 4)},
               "stale_fy": {"n": len(D["stale_fy"]), "cap": round(cv(D["stale_fy"]), 4), "top": _top_names(R, D["stale_fy"])},
               "stale_eiss": {"n": len(D["stale_eiss"]), "cap": round(cv(D["stale_eiss"]), 4)},
               "eq_nonpos": {"n": len(D["eq_nonpos"]), "cap": round(cv(D["eq_nonpos"]), 4), "n_unscored": len(roe_block),
                             "cap_unscored": round(cv(roe_block), 4), "top": _top_names(R, roe_block)},
               "n_ttm_tag_names": len(D["ttm"]), "sec_src_scored": dict(sorted(srcs.items())),
               "w_held_seam_fixed": round(float(sum(w.get(k, 0.0) for k in D["seam_fixed"])), 5)}
        if v0m:
            f0 = [x for x in v0m if x <= m]
            if f0:
                wv = T0[f0[-1]]["w"]
                row["eg30_overlap_w"] = round(float(sum(min(w.get(k, 0), wv[k]) for k in sorted(wv))), 4)
                row["eg30_overlap_n"] = len(set(w) & set(wv))
        rows.append(row)
        prev = w
    return rows


def coverage_by_year(rows):
    out = {}
    for r in rows:
        y = out.setdefault(r["m"][:4], {"n": 0, "cov_scored": 0.0, "n_scored": 0.0})
        y["n"] += 1; y["cov_scored"] += r["cov_scored"]; y["n_scored"] += r["n_scored"]
    return {y: {"cov_scored": round(v["cov_scored"] / v["n"], 4), "n_scored": round(v["n_scored"] / v["n"], 1)} for y, v in sorted(out.items())}


def tol0_impact(Wd):
    """날짜 허용 0 이면 얼린 FY · EVOL 성분(ROE · ROA · EVOL)이 달라지는 이름 수(값 또는 있음/없음) — 구성만."""
    F = frozen_list()
    comps = [c for p in PILLARS for c in F[p] if c in FY_COMPS + ("EVOL",)]
    out = []
    for m in Wd.months:
        R = month_raw(Wd, m)
        n, nm = 0, []
        for k in R["keys"]:
            r0, _u, _i = fund_components(Wd.fund(R["names"][k], k) or {}, R["cut"], tol=0)
            if any((k in R["vals"][c]) != (c in r0) or (k in R["vals"][c] and abs(R["vals"][c][k] - r0[c]) > 1e-12) for c in comps):
                n += 1
                nm.append(R["names"][k])
        out.append((m, n, sorted(nm)[:8]))
    return out


def dry(ctx):
    """랩 자료로 구성만 — 얼림 재현 · 커버리지 · 개수 · 비중 합 · 한도 · 날짜 · 진단. 수익 없음."""
    Wd = ctx.Wd
    t0 = time.time()
    pr = coverage_probe(Wd)
    frozen_ok = (FROZEN is not None and pr["frozen"] == FROZEN and pr["lev_src"] == LEV_SRC)
    assert frozen_ok, "커버리지 얼림이 FROZEN 과 다르다: %s / %s" % (pr["frozen"], pr["lev_src"])
    cov_ok = all(abs(round(pr["cov"][c], 4) - v) < 1e-9 for c, v in _FROZEN_COV_TXT.items())
    T = targets_top(Wd, "Q")
    chk = {"rule": _check_targets(Wd, T, "rule"), "C1": _check_targets(Wd, targets_all_scored(Wd), "C1"),
           "C0": _check_targets(Wd, targets_priced(Wd), "C0"), "noS": _check_targets(Wd, targets_top(Wd, "NS"), "noS")}
    for p in PILLARS:
        if frozen_list()[p]:
            chk["P_" + p] = _check_targets(Wd, targets_top(Wd, p), "P_" + p)
    P = perm_prep(Wd)
    Tid = perm_targets(P, None)
    ident = all(sorted(Tid[m]["w"]) == sorted(T[m]["w"]) and all(abs(Tid[m]["w"][k] - T[m]["w"][k]) < 1e-15 for k in T[m]["w"]) for m in T)
    Tp = perm_targets(P, np.random.default_rng(Q.SEED + 0))
    chk["C2_draw0"] = _check_targets(Wd, Tp, "C2")
    same = float(np.mean([len(set(Tp[m]["w"]) & set(T[m]["w"])) / len(T[m]["w"]) for m in T]))
    rows = month_log(Wd, T, ctx.V0_targets)
    umax = max(r["fund_max_end"] for r in rows if r["fund_max_end"])
    pit_ok = all(r["fund_max_end"] is None or r["fund_max_end"] <= r["cut"] for r in rows)
    ns = [r["n_scored"] for r in rows]
    nh = [r["n_held"] for r in rows]
    sm = lambda key, fld: [min(r[key][fld] for r in rows), round(float(np.median([r[key][fld] for r in rows])), 4), max(r[key][fld] for r in rows)]
    srcs = {}
    for r in rows:
        for s, n in r["sec_src_scored"].items():
            srcs[s] = srcs.get(s, 0) + n
    t_tol = time.time()
    tol0 = tol0_impact(Wd)
    t_tol = round(time.time() - t_tol, 1)
    return {"frozen": FROZEN, "lev_src": LEV_SRC, "frozen_reproduced": frozen_ok, "frozen_cov_reproduced": cov_ok,
            "probe_cov": {c: round(v, 4) for c, v in pr["cov"].items()}, "probe_n_univ": pr["n_univ"],
            "months": len(rows), "n_scored": [min(ns), int(np.median(ns)), max(ns)], "n_held": [min(nh), int(np.median(nh)), max(nh)],
            "cov_scored_first_last": [rows[0]["cov_scored"], rows[-1]["cov_scored"]], "coverage_by_year": coverage_by_year(rows),
            "checks": chk, "perm_identity_equals_rule": ident, "draw0_name_overlap_with_rule": round(same, 3),
            "pit_ok": pit_ok, "fund_max_end_overall": umax, "n_date_tol_total": int(sum(r["n_date_tol"] for r in rows)),
            "seam_fixed_n_cap_minmedmax": {"n": sm("seam_fixed", "n"), "cap": sm("seam_fixed", "cap")},
            "seam_fixed_months_gt0": sum(1 for r in rows if r["seam_fixed"]["n"]), "seam_fixed_2016_08": rows[0]["seam_fixed"],
            "seam_fixed_rule_weight_max": max(r["w_held_seam_fixed"] for r in rows),
            "seam_future_still_missing_n_max": max(r["seam_future_still_missing"]["n"] for r in rows),
            "stale_fy_n_cap_minmedmax": {"n": sm("stale_fy", "n"), "cap": sm("stale_fy", "cap")}, "stale_fy_2016_08": rows[0]["stale_fy"],
            "stale_fy_top_2020_08": next(r["stale_fy"] for r in rows if r["m"] == "2020-08"),
            "stale_eiss_n_max": max(r["stale_eiss"]["n"] for r in rows),
            "eq_nonpos_unscored_n_cap_minmedmax": {"n": sm("eq_nonpos", "n_unscored"), "cap": sm("eq_nonpos", "cap_unscored")},
            "eq_nonpos_top_2016_08_2026_07": [rows[0]["eq_nonpos"]["top"], rows[-1]["eq_nonpos"]["top"]],
            "ttm_tag_names_max": max(r["n_ttm_tag_names"] for r in rows),
            "sec_src_scored_total": dict(sorted(srcs.items())),
            "tol0_diff_names_minmedmax": [min(x[1] for x in tol0), int(np.median([x[1] for x in tol0])), max(x[1] for x in tol0)],
            "tol0_sample": tol0[::24], "tol0_sec": t_tol,
            "eg30_overlap_w_median": float(np.median([r.get("eg30_overlap_w", 0) for r in rows])),
            "targets_hash": targets_hash(T), "sec": round(time.time() - t0, 1)}


def hashes(ctx):
    """결정성 확인용 목표 해시(규칙 · C1 · 안전 뺀 · P_safe · 위약 판 SEED+7) — 수익 없음."""
    Wd = ctx.Wd
    P = perm_prep(Wd)
    return {"rule": targets_hash(targets_top(Wd, "Q")), "C1": targets_hash(targets_all_scored(Wd)), "NS": targets_hash(targets_top(Wd, "NS")),
            "P_safe": targets_hash(targets_top(Wd, "safe")), "C2_draw7": targets_hash(perm_targets(P, np.random.default_rng(Q.SEED + 7))),
            "turn_target_rule": target_turn(targets_top(Wd, "Q"))}


# ── 한 번 굽기 ─────────────────────────────────────────────────────────────
def _ex(fr):
    return np.asarray(fr["ex"], float)


def run(ctx):
    """한 번 굽기 — {'Q01': CardResult}. 판정 · 다중성은 러너가 한다. 🚨 여기서 수익을 찍지 않는다."""
    Wd, G = ctx.Wd, ctx.G
    t0 = time.time()
    pr = coverage_probe(Wd)                                         # 핀 · 자료가 얼림과 같은지 먼저(비용 없음 — month_raw 캐시)
    assert pr["frozen"] == FROZEN and pr["lev_src"] == LEV_SRC, "커버리지 얼림이 FROZEN 과 다르다: %s / %s" % (pr["frozen"], pr["lev_src"])
    F = frozen_list()
    T = targets_top(Wd, "Q")
    fr = ctx.stock_fr(T, reb=1)
    fr_pr = ctx.stock_fr(T, reb=1, basis="PR")
    fr20 = ctx.stock_fr(T, reb=1, cost=COST20)
    hold = fr["hold"]
    dm = ctx.dmask(hold)
    controls = {"C1": ctx.stock_fr(targets_all_scored(Wd), reb=1), "C0": ctx.stock_fr(targets_priced(Wd), reb=1)}
    arms = {"noSafety": ctx.stock_fr(targets_top(Wd, "NS"), reb=1),
            "QUAL": ctx.etf_fr(lambda m: {"QUAL": 1.0}, Q.monthly_forms())}
    for p in PILLARS:
        if F[p]:
            arms["P_" + p] = ctx.stock_fr(targets_top(Wd, p), reb=1)
    # C2 위약 — 업종 안 퀄리티 섞기 · 판마다 제 슬리브 베타로 하락월 H · 관문은 비용 0(C2_GROSS) · 10bp 판은 보고만(같은 섞기)
    def stats(f):
        ev = Q.evaluate(G, f, dm)
        return float(np.mean(_ex(f))), float(ev["down_mean"] - ev["hedge_ctrl"]["down_mean"])
    fr_gross = ctx.stock_fr(T, reb=1, cost=0.0)
    tg_all, tg_h = stats(fr_gross)
    tn_all, tn_h = stats(fr)
    P = perm_prep(Wd)
    g_all, g_h, n_all, n_h, turn_p = [], [], [], [], []
    t1 = time.time()
    for r in range(NPERM):
        Tp = perm_targets(P, np.random.default_rng(Q.SEED + r))
        a, h = stats(ctx.stock_fr(Tp, reb=1, cost=0.0))
        g_all.append(a); g_h.append(h)
        fnet = ctx.stock_fr(Tp, reb=1)
        a, h = stats(fnet)
        n_all.append(a); n_h.append(h)
        turn_p.append(fnet.get("turn"))
    gate_all, gate_h, gate_ta, gate_th = (g_all, g_h, tg_all, tg_h) if C2_GROSS else (n_all, n_h, tn_all, tn_h)
    rep_all, rep_h, rep_ta, rep_th = (n_all, n_h, tn_all, tn_h) if C2_GROSS else (g_all, g_h, tg_all, tg_h)
    gl, rl = ("비용 0(총 · 되돌림 비용도 0)", "편도 10bp(보고만)") if C2_GROSS else ("편도 10bp", "비용 0(보고만)")
    placebo = {"C2_all_X": {"stat": "전 달 평균 X(펀드 − SPY TR · %%/월) — %s · 업종 안 퀄리티 섞기 %d번 · 씨앗 SEED + i · 관문" % (gl, NPERM),
                            "draws": gate_all, "true": gate_ta},
               "C2_down_H": {"stat": "하락월(39) 평균 H = X − 0.1(β̂_s − 1)(SPYTR − rf) · β̂_s 는 판마다 제 슬리브 120개월 OLS — %s · 관문" % gl,
                             "draws": gate_h, "true": gate_th},
               ("C2_all_X_net10bp" if C2_GROSS else "C2_all_X_gross"): {"stat": "C2_all_X 와 같은 섞기 — %s" % rl, "draws": rep_all, "true": rep_ta},
               ("C2_down_H_net10bp" if C2_GROSS else "C2_down_H_gross"): {"stat": "C2_down_H 와 같은 섞기 — %s" % rl, "draws": rep_h, "true": rep_th}}
    q95 = lambda v: float(np.quantile(np.asarray(v, float), 0.95))
    x = _ex(fr)
    d1, d0 = x - _ex(controls["C1"]), x - _ex(controls["C0"])
    late = np.array([h >= H0_C0 for h in hold])
    t_c1, t_c0 = E.nw_t(d1), E.nw_t(d0)
    g4 = {"C1_nw_t>=1.0": bool(t_c1 is not None and t_c1 >= 1.0),
          "C0_nw_t>=1.0": bool(t_c0 is not None and t_c0 >= 1.0),
          "C0_2019-09+_point>0": bool(float(d0[late].mean()) > 0),
          "C2_all_X>=p95": bool(gate_ta >= q95(gate_all)),
          "C2_down_H>=p95": bool(gate_th >= q95(gate_h))}
    g4["G4"] = all(g4.values())
    rows = month_log(Wd, T, ctx.V0_targets)
    v0 = ctx.V0()
    corr = lambda a, b: float(np.corrcoef(np.asarray(a["basket"], float), np.asarray(b["basket"], float))[0, 1])
    nh = [r["n_held"] for r in rows]
    f0_ok = all(len(F[p]) >= (PILLAR_MIN[p] if p != "pay" else 1) for p in PILLARS if F[p]) and \
        sum(1 for p in PILLARS if len(F[p]) >= PILLAR_MIN[p]) >= QUAL_MIN and min(nh) >= 10
    log = {"interpretation": INTERP, "frozen": F, "lev_src": LEV_SRC, "frozen_cov": _FROZEN_COV_TXT, "p_ff": False,
           "p_ff_why": "원 companyfacts(제출일) 없음 — 마지막 제출값 · 첫 제출 재실행이 G5 필수",
           "fy_fresh_days": FY_FRESH_DAYS, "date_tol": DATE_TOL, "c2_gross": C2_GROSS,
           "grid": {"QUAL": "A", "*": "G"},
           "months": rows, "coverage_by_year": coverage_by_year(rows), "turn_target": target_turn(T),
           "turn_sleeve": fr.get("turn"), "sleeve_cost_drag_pct_yr": (2 * fr["turn"] * Q.COST * 100 if fr.get("turn") is not None else None),
           "placebo_turn_sleeve_median": float(np.median([t for t in turn_p if t is not None])) if any(t is not None for t in turn_p) else None,
           "arms_not_run": ["P_grow — 얼림에서 성장 성분 0개"],
           "sleeve_corr": {"EG30_V0": corr(fr, v0), "QUAL": corr(fr, arms["QUAL"])},
           "sleeve_corr_note": "QG30 목표 경로가 코어에 없어 뺐다", "perm_sec": round(time.time() - t1, 1),
           "c2_q95": {"all_X": q95(gate_all), "down_H": q95(gate_h)}, "g4_stats": {"C1_nw_t": t_c1, "C0_nw_t": t_c0, "C0_late_mean": float(d0[late].mean())},
           "sec": None}
    log["sec"] = round(time.time() - t0, 1)
    res = {"code": "Q01", "cls": "A", "slot": "A1", "fr": fr, "fr_pr": fr_pr, "fr20": fr20, "controls": controls, "arms": arms,
           "placebo": placebo, "perm": None, "g4": g4, "label_caps": {},
           "f0": {"ok": bool(f0_ok), "why": "카드에 F0 없음 — 구조 가능성(기둥 구성 · 달마다 보유 ≥ 10)" + ("" if f0_ok else " 실패")},
           "targets_hash": targets_hash(T), "log": log}
    return {"Q01": res}


# ── 명령줄 ────────────────────────────────────────────────────────────────
def main():
    a = sys.argv[1:]
    if "--selftest" in a:
        print(json.dumps(selftest(), ensure_ascii=False, indent=1))
        return 0
    ctx = Q.Ctx()
    if "--probe" in a:
        pr = coverage_probe(ctx.Wd, detail=True)
        print(json.dumps(pr, ensure_ascii=False, indent=1))
        return 0
    if "--dry" in a:
        print(json.dumps(dry(ctx), ensure_ascii=False, indent=1, default=str))
        return 0
    if "--hashes" in a:
        print(json.dumps(hashes(ctx), ensure_ascii=False, indent=1))
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
