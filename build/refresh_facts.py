#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC EDGAR companyfacts(XBRL) → 회사별 재무 시계열

메뉴 정본에서 이 소스 하나에 막혀 있던 칸을 겨냥한다:
  co.html#fs          재무제표      기간·제출일이 붙은 분기/연간 시계열

🚨 2026-08-12 — 겨냥 대상이 셋에서 하나로 줄었다. valuation.html(DDM·RIM·지수 역산)과
  rel-value.html 을 지웠다(사용자 결정 — 쓰이지 않았다. 본문 링크 0). 그 페이지들만 읽던
  세 산출(clean_surplus · index_fcf · dps_years)과 그것을 만드는 149줄을 같이 걷었다.
  ⚠ 자료만 지우고 계산을 남기면 매주 아무도 안 읽는 값을 굽는다 — 그 상태를 이 저장소가
    'DDM/RIM 이 곧 살아난다'는 신호로 오해할 수 있어 계산까지 걷었다.
  ⚠ 되살릴 때 밟을 함정은 **은퇴 기록에 남겼다**(build/nav_items.json 의 retired) —
    지수 FCF 를 SEC frames 로 직접 합치면 집합이 어긋나 +80% 부풀려진다는 실측이다.
  · crosscheck_stat(xcheck)는 co.html 이 읽으므로 그대로 둔다.

── 왜 지금까지 비어 있었나 ─────────────────────────────────────────────
빈 탭에 적어 둔 사유가 정확했다: 이 사이트가 가진 재무 숫자는 **오늘 한 점짜리 단면**이라
성장률도 기울기도 정의되지 않았다. companyfacts는 그 점들을 시계열로 준다.

── 이 파일이 지키는 것 ─────────────────────────────────────────────────
* **기간과 제출일을 반드시 함께 담는다.** 재무 숫자는 '어느 기간의 것이고 언제 제출됐는지'가
  붙지 않으면 의미가 없다(그게 #fs 칸을 비워 둔 이유였다).
* **재작성(restatement)은 최신 제출본을 쓴다.** 같은 기간이 여러 번 보고되면 filed가
  가장 늦은 것을 남긴다. 옛 값으로 그린 그래프는 조용히 틀린다.
* **누적(YTD) 구간을 분기로 착각하지 않는다.** 10-Q의 duration은 3개월도 있고 6·9개월도
  섞여 온다. 일수로 갈라 분기(80~100일)와 연간(350~380일)만 남기고 나머지는 버린다.
  안 거르면 3분기 매출이 갑자기 3배로 뛴 것처럼 보인다.
* **환산은 표시 편의일 뿐 반올림 손실을 감춘다.** USD는 백만 단위로 담되(파일 크기),
  주당 금액(EPS·DPS)은 원값 그대로 둔다 — 1.65를 백만으로 나누면 0이 된다.

── 실측 비용(2026-07-25) ───────────────────────────────────────────────
  companyfacts 1건: gz 262KB(AAPL)~510KB(JPM) · 파싱 0.08s
  → 518사 전수 다운로드 약 180MB · 파싱 CPU 약 0.7분 · 호출 상한 8/s로 약 2분
  주 1회면 충분하다(실적 발표 때만 바뀐다).

── 2026-09-25 배치 R §F — 세 가지를 더했다(기존 값은 하나도 안 바뀐다) ─────────
① **태그 빈칸 메우기**(extract · FILL_KEYS). 고른 태그(src)의 값은 그대로 두고, 그 태그가 **비운
  기간만** 다음 후보 태그로 채운다. 실측: EOG 자기자본이 2009-06 → 2019-12 로 10년을 건너뛰었다
  (그 사이를 NCI 포함 태그로만 냈다) — as-of 로 읽으면 2019 년까지 2009 년 장부가가 «최신» 이었다.
  DOV·HP·PPL 도 같고, HAS·NSC·WEC·BRO 는 초기 장부가가 비었다.
  ⚠ 한 줄에 태그가 섞이는 대신 **어느 칸이 어느 태그인지 적는다**(rec.alt · rec.tg).
  ⚠ 겹치는 기간에서 두 태그가 맞는 경우에만 채운다(FILL_TOL) — 비지배지분이 큰 회사의 NCI 포함
    자기자본을 지배주주 지분 줄에 끼우면 그 칸만 부푼다. 매출·원가('max' 동점규칙 — 총액 대 일부)·
    차입금·감가상각(태그마다 범위가 다르다)은 채우지 않는다.
② **지주사 재편 잇기**(data/fx_splice.json ← _issuer_map.json 의 splice 판정). 새 지주사 CIK 로 받은
  파일은 역사가 재편일에서 시작한다(XOM 2115436 자기자본 첫 관측 2024-12 · BLK · APA · DIS …).
  선행 CIK 의 관측 가운데 **지금 파일 그 태그·그 버킷의 첫 관측보다 이른 것만** 앞에 붙인다(겹치면
  지금 파일이 이긴다). 주간 갱신이 매번 다시 잇는다 — 손으로 붙이면 다음 토요일에 사라진다.
  날짜로 가르는 두 이름(mode cut): DD 는 2017-08 까지 E.I. du Pont(30554) — 1666700 의 그 시절
  비교 재무는 회계상 인수자 Dow 의 것이다. FTI 는 2016-12 까지 FMC Technologies(1135152) — TechnipFMC
  (1681459)의 2016 비교 재무는 Technip 것이다(실측: 2016 매출 9,199.6 · 자기자본 5,002 · 주식수 126.9 —
  FMC Technologies 는 2015 매출 6,362.7 · 2016-09 자기자본 2,694 · 228.2). 지도 FTI 판정의 '회계상 인수자
  FMC Technologies' 는 이 숫자와 맞지 않는다 — 그래서 prepend 가 아니라 cut 이다.
③ **관측의 출처 CIK**(doc.ciks · rec.ck). 파일 전체의 [CIK, 첫 기간말, 끝 기간말, 칸 수] 와, CIK 가
  둘 이상 섞인 항목은 버킷별 구간을 싣는다. «그 달 쓴 관측의 CIK ∈ 그 달 §A0 CIK 집합» 을
  검사하려면 이것이 있어야 한다(cell_ciks 로 읽는다). 선행·후계가 같은 값(0.5% 안 · CORROB_TOL)을
  냈으면 둘 다 적는다 — 후계의 비교 재무가 선행의 원 보고와 같은 숫자인 기간이 그렇다.
  ⚠ 선행 법인 잇기와 빈칸 메우기 모두 **첫 관측보다 이른 칸은 450일 안에 이어질 때만** 붙인다(JOIN_DAYS).

사용: python3 build/refresh_facts.py                       (러너 — 기존 그대로)
      python build/refresh_facts.py --rate 2 --cache DIR --no-summary   (로컬 재생성 · SEC_UA 필수)
      python build/refresh_facts.py --build-splices         (data/fx_splice.json 다시 짓기 · SEC 안 씀)
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_FX = os.path.join(DATA, "fx")
OUT_SUM = os.path.join(DATA, "facts.json")
SPLICE_PATH = os.path.join(DATA, "fx_splice.json")      # ② 지주사 재편 잇기 표(--build-splices 가 짓는다)
ISSUER_MAP = os.path.join(DATA, "_issuer_map.json")

FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json"

# ── 보관 깊이 ────────────────────────────────────────────────────────────
# 🚨 이 셋은 화면 표시량이 아니라 **백테스트가 쓸 수 있는 표본 길이**를 정한다.
#   2026-08-03 에 20/8/20(=5년)에서 늘렸다. 그 전까지 이 랩의 펀더멘털 규칙은
#   가격이 2009-01-02 부터 4,421일 있는데도 재무가 5년에서 끊겨 **4.6년치로만**
#   검정되고 있었다. 본페로니 t_crit 3.32 를 넘길 표본이 애초에 없었다는 뜻이다.
#
# 값은 골라 넣은 게 아니라 두 실측이 정한다:
#   ① 위쪽 — 가격 격자가 2009-01-02 에서 시작한다. 대응 가격이 없는 재무 관측은
#      들고 있어 봐야 거래할 수 없다. 18년(72분기)이면 그 격자를 덮고 남는다.
#   ② 아래쪽 — SEC XBRL 자체가 2008~2009 년경에서 시작한다. 실측(8사, 2026-08-03):
#      72/20/72 와 200/40/200 의 산출이 **완전히 같았다**(둘 다 19.3KB/사).
#      즉 72 는 자료를 다 담는 최소값이다. 더 키우는 것은 무의미하다.
# 비용은 회사당 8.3KB → 19.3KB(실측 2.3배, data/fx 5.3MB → 약 12MB). 수집 호출 수는
# 그대로다 — companyfacts 는 전 이력을 어차피 한 번에 준다. 자르는 건 우리 정책이었다.
KEEP_Q = 72      # 분기 관측 보관 수(18년 — 가격 격자 2009-01-02 를 덮는다)
KEEP_A = 20      # 연간 관측 보관 수(20년)
KEEP_I = 72      # 시점(재무상태표) 관측 보관 수(18년)
FORMS_OK = ("10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A")

# 항목별 후보 태그 — 회사마다 쓰는 태그가 달라 우선순위로 훑는다.
# (키, 후보 태그들, 단위, 스케일[, 동점규칙])  스케일 m=백만 단위로 환산, r=원값 유지
#
# 동점규칙 'max' — 최신 관측일이 같을 때 **값이 큰 태그**를 고른다.
#   매출·매출원가·현금흐름은 후보들이 '총액 대 그 일부' 관계다. 예: 리츠의 매출은 대부분
#   리스 수익(ASC 842)이라 RevenueFromContractWithCustomer(ASC 606)는 극히 일부만 잡는다.
#   실측(2026-07-25): AVB는 계약 매출 7백만$ vs Revenues 3,041백만$ — 434배 차이였고,
#   같은 함정에 리츠·은행·보험 23사가 걸려 있었다(은행은 이자수익, 보험은 보험료가 본체).
#   기본값(관측 수 비교)은 그대로 둔다 — 자기자본처럼 '지배주주 대 전체'는 큰 쪽이 답이 아니다.
TAGS = (
    # RevenuesNetOfInterestExpense는 은행·증권의 '총수익'이다. 없으면 JPM 같은 회사는
    # 분기 매출이 2014년에서 멈춘 Revenues밖에 안 남는다(실측).
    # OperatingLeaseLeaseIncome은 리츠의 본체다. 리츠 매출은 대부분 리스 수익(ASC 842)이라
    # Revenues 태그조차 없는 회사가 있다 — CPT는 계약 매출 13백만$만 잡히고 실제 리스 수익은
    # 1,574백만$였다(실측 2026-07-25). 동점규칙 'max'가 있어서 일반 기업에는 영향이 없다.
    ("rev",   ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
               "RevenuesNetOfInterestExpense", "OperatingLeaseLeaseIncome",
               "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"), "USD", "m", "max"),
    ("cogs",  ("CostOfGoodsAndServicesSold", "CostOfRevenue"), "USD", "m", "max"),
    ("gp",    ("GrossProfit",), "USD", "m"),
    ("opinc", ("OperatingIncomeLoss",), "USD", "m"),
    ("ni",    ("NetIncomeLoss", "ProfitLoss"), "USD", "m"),
    ("eps",   ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted",
               "EarningsPerShareBasic"), "USD/shares", "r"),
    ("dps",   ("CommonStockDividendsPerShareDeclared",
               "CommonStockDividendsPerShareCashPaid"), "USD/shares", "r"),
    ("asset", ("Assets",), "USD", "m"),
    ("liab",  ("Liabilities",), "USD", "m"),
    # 지배주주지분을 먼저 쓴다 — BVPS·RIM이 쓰는 값이 이것이기 때문이다. 대신 비지배지분이
    # 큰 회사(BX·FCX·ARES 등)는 자산 ≠ 부채 + 이 값이 되므로, 화면에 그 사유를 적는다.
    ("eq",    ("StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"), "USD", "m"),
    ("cash",  ("CashAndCashEquivalentsAtCarryingValue",), "USD", "m"),
    ("cfo",   ("NetCashProvidedByUsedInOperatingActivities",
               "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"), "USD", "m"),
    ("capex", ("PaymentsToAcquirePropertyPlantAndEquipment",
               "PaymentsToAcquireProductiveAssets"), "USD", "m"),
    ("sh",    ("WeightedAverageNumberOfDilutedSharesOutstanding",
               "WeightedAverageNumberOfSharesOutstandingBasic"), "shares", "m"),
    # 기말 발행주식수 — sh(가중평균 희석)의 **대타**다. 쓰는 쪽이 sh 를 먼저 보고 없을
    # 때만 쓴다. 별 키로 두는 이유: 같은 후보 목록에 넣으면 '가장 최근까지 보고된 태그가
    # 이긴다'는 규칙이 멀쩡한 회사의 희석주식수까지 이걸로 갈아치운다. 둘은 정의가 다르다.
    # 🚨 이게 없으면 통째로 못 재는 회사가 있다. 실측(2026-08-04): HSY 는 희석주식수를
    #   2015-10 이후 안 내고(옛 태그가 11년 묵어 최신성 가드가 버린다) 이 태그만 낸다.
    #   KKR·LYB·SJM 도 같다 — 넷 다 지금 주식수 계열이 아예 없다.
    ("sho",   ("CommonStockSharesOutstanding",), "shares", "m"),
    # ── 아래 다섯은 2026-08-04 추가(사용자 요청). 지금까지 재무 태그가 16종뿐이라
    #   유동비율·순부채/EBITDA·알트만 Z 같은 표준 지표를 **물어볼 자료 자체가 없었다.**
    #   같은 엔드포인트라 호출은 안 는다. 표본 24사 실측 커버리지를 각 줄에 적는다.
    ("ca",    ("AssetsCurrent",), "USD", "m"),                     # 83% — 은행·보험은 유동/비유동을 안 가른다
    ("cl",    ("LiabilitiesCurrent",), "USD", "m"),                # 83% — 같은 이유
    ("re",    ("RetainedEarningsAccumulatedDeficit",), "USD", "m"),  # 100%
    # ⚠ 차입금은 이름마다 범위가 다르다(LongTermDebt 는 유동성 대체분을 포함하기도 한다).
    #   '가장 최근까지 보고된 태그' 규칙을 그대로 쓰되, 회사마다 다른 태그가 뽑힐 수 있음을
    #   여기 적어 둔다 — 회사 간 절대 비교보다 **한 회사의 시계열** 용도로 쓸 것.
    ("debt",  ("LongTermDebtNoncurrent", "LongTermDebt",
               "LongTermDebtAndCapitalLeaseObligations"), "USD", "m"),   # 합집합 75%+
    ("dep",   ("DepreciationDepletionAndAmortization",
               "DepreciationAmortizationAndAccretionNet",
               "DepreciationAndAmortization", "Depreciation"), "USD", "m"),  # 합집합 58%+
    # 아래 둘은 RIM의 전제(클린서플러스)를 실제로 재기 위해 넣는다. 장부가 증분이
    # '이익 − 배당'과 맞지 않는 가장 큰 이유가 자사주 매입이다 — 실측(2026-07-25):
    # AAPL의 잔차가 −79,922 → +10,789로, MTD는 −766 → +34로 줄어든다.
    ("bb",    ("PaymentsForRepurchaseOfCommonStock",
               "PaymentsForRepurchaseOfEquity"), "USD", "m"),
    ("iss",   ("ProceedsFromIssuanceOfCommonStock",
               "ProceedsFromIssuanceOrSaleOfEquity"), "USD", "m"),
)
# ── IFRS 택소노미 ───────────────────────────────────────────────────────
# 외국 사기업(foreign private issuer)은 20-F/40-F를 IFRS로 낸다. companyfacts에
# us-gaap이 아예 없고 ifrs-full만 있다 — 실측(2026-07-25): CCEP 351태그·TRI 398·FER 156.
# us-gaap만 보면 이 회사들은 '재무 없음'으로 떨어진다. 같은 항목 키에 IFRS 태그를 붙여
# 같은 표에 담되, 어느 태그에서 왔는지는 화면에 그대로 표기하므로 섞였다는 사실은 감춰지지 않는다.
# (주식수는 IFRS 필수 공시가 아니라 CCEP에 없다 — 없는 항목은 만들지 않는다.)
TAGS_IFRS = (
    ("rev",   ("Revenue", "RevenueFromContractsWithCustomers"), "USD", "m", "max"),
    ("cogs",  ("CostOfSales",), "USD", "m"),
    ("gp",    ("GrossProfit",), "USD", "m"),
    ("opinc", ("ProfitLossFromOperatingActivities",), "USD", "m"),
    ("ni",    ("ProfitLoss",), "USD", "m"),
    ("eps",   ("DilutedEarningsLossPerShare", "BasicEarningsLossPerShare"), "USD/shares", "r"),
    ("dps",   ("DividendsPaidOrdinarySharesPerShare",), "USD/shares", "r"),
    ("asset", ("Assets",), "USD", "m"),
    ("liab",  ("Liabilities",), "USD", "m"),
    ("eq",    ("Equity",), "USD", "m"),
    ("cash",  ("CashAndCashEquivalents",), "USD", "m"),
    ("cfo",   ("CashFlowsFromUsedInOperatingActivities",), "USD", "m"),
    ("capex", ("PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",), "USD", "m"),
    # IFRS 쪽에는 주식수가 아예 없었다 — 그래서 CCEP·FER·TRI 는 주식수 계열이 통째로
    # 비어 있었다(실측 2026-08-04). us-gaap 의 WeightedAverageNumberOf… 대응 이름이다.
    # 희석 기준(Adjusted…)을 먼저 본다 — us-gaap 쪽도 희석을 먼저 보므로 정의를 맞춘다.
    ("sh",    ("AdjustedWeightedAverageShares", "WeightedAverageShares"), "shares", "m"),
)

# 화면에 그대로 쓰는 항목 이름. 여기 없는 키는 만들지 않는다.
LABEL = {
    "rev": "매출", "cogs": "매출원가", "gp": "매출총이익", "opinc": "영업이익",
    "ni": "순이익", "eps": "주당순이익(희석)", "dps": "주당배당금(선언)",
    "asset": "자산총계", "liab": "부채총계", "eq": "자기자본(지배주주지분)",
    "cash": "현금및현금성자산", "cfo": "영업활동현금흐름", "capex": "설비투자(CAPEX)",
    "sh": "희석주식수", "sho": "발행주식수(기말)", "bb": "자사주 매입", "iss": "주식 발행",
    "ca": "유동자산", "cl": "유동부채", "re": "이익잉여금", "debt": "장기차입금",
    "dep": "감가상각비",
}


def _days(a: str, b: str):
    try:
        return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
    except Exception:
        return None


def pick(unitvals, scale):
    """관측 리스트 → (분기, 연간, 시점) 각각 [[end, val], …] 최신순.

    같은 기간이 여러 번 보고되면(재작성·정정) filed가 가장 늦은 것을 남긴다."""
    q, a, i = {}, {}, {}
    for o in unitvals or []:
        if str(o.get("form") or "") not in FORMS_OK:
            continue
        end, val, filed = o.get("end"), o.get("val"), str(o.get("filed") or "")
        if not end or val is None:
            continue
        start = o.get("start")
        if not start:
            bucket = i                      # 시점(재무상태표)
        else:
            n = _days(start, end)
            if n is None:
                continue
            if 80 <= n <= 100:
                bucket = q                  # 분기
            elif 350 <= n <= 380:
                bucket = a                  # 연간
            else:
                continue                    # 6·9개월 누적 등 — 분기로 섞으면 값이 뛴다
        prev = bucket.get(end)
        if prev is None or filed >= prev[1]:
            bucket[end] = (val, filed)

    def out(bucket, keep):
        rows = sorted(bucket.items(), reverse=True)[:keep]
        res = []
        for end, (val, _f) in rows:
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            res.append([end, round(v / 1e6, 2) if scale == "m" else round(v, 4)])
        return res

    return out(q, KEEP_Q), out(a, KEEP_A), out(i, KEEP_I)


def resolve_unit(units: dict, want: str):
    """실제 존재하는 단위 키를 고른다 → (단위, 관측리스트).

    보고 통화가 달러가 아닌 회사가 있다 — 실측(2026-07-25): CCEP·FER은 EUR로 보고한다.
    USD로 못 박아 두면 이 회사들이 통째로 '재무 없음'이 되고, 그렇다고 EUR 값을 달러로
    표시하면 그냥 틀린 숫자가 된다. 그래서 실제 단위를 골라 그대로 들고 다니고,
    화면은 이 단위를 읽어 통화를 표기한다. **환산하지 않는다** — 어느 시점 환율로
    바꿨는지 밝히지 못하는 환산은 정확도를 가장한 왜곡이다.
    """
    if want in units:
        return want, units[want]
    if want == "shares":
        return want, None
    if want.endswith("/shares"):
        for k in sorted(units):
            if k.endswith("/shares") and len(k) == len("XXX/shares"):
                return k, units[k]
        return want, None
    for k in sorted(units):                      # 통화 3자리(EUR·GBP·CAD…)
        if len(k) == 3 and k.isalpha() and k.isupper():
            return k, units[k]
    return want, None


# 주당지표 단위오류 걸러내기 — 두 조건을 **함께** 만족할 때만 버린다.
PERSHARE_ABS = 10000.0   # 주당 1만$ 를 넘는 주당지표는 주당지표가 아니다
PERSHARE_REL = 100.0     # 그리고 그 계열 중앙값의 100배를 넘을 것
UNIT_ERRORS = []         # (티커는 호출부가 안다) 버린 관측 기록 — main 이 로그로 찍는다


def drop_pershare_unit_errors(ser, unit, log=True):
    """EPS·DPS 에 섞여 들어온 단위오류를 버린다(log=False — 빈칸 메우기용 후보 계열이라 기록하지 않는다).

    🚨 실측(2026-08-04, 보관 깊이를 18년으로 늘린 뒤 드러났다): SEC 원문에 EPS 가
      HAL 790,000 · ICE 1.12억 · HIG 650,000 · TMO 500,000 · ROK 배당 184만 처럼 들어 있다.
      금액을 주당지표 태그에 잘못 넣은 것이고, 그대로 두면 E/P 가 850만%로 나온다.
      전에도 있던 결함인데(옛 5년 창에서 646건) 창을 늘리자 1,374건으로 드러났다.

    ⚠ 왜 '중앙값의 100배'만으로는 안 되는가 — 진짜 극단값을 죽인다. 실측: WY 배당
      26.46$(2010년 REIT 전환 특별배당, 중앙값 0.22 의 120배)는 **사실이다**.
      EXE 852.97 · AIG 181.02 · TRGP 48.1 도 100배를 넘지만 주당지표로 가능한 크기다.
      단위오류들은 전부 20만 이상이라 그 사이가 200배 넘게 비어 있다 — 절대 기준을
      함께 걸면 둘이 깨끗이 갈린다(실측: 오류 6종 전건 적중 · 정상 4종 전건 보존).
    ⚠ 총액 항목에는 쓰지 않는다. 단위는 'USD/shares' 로만 판별한다.
    """
    if unit != "USD/shares" or len(ser) < 3:
        return ser
    vs = sorted(abs(v) for _d, v in ser if v)
    if not vs:
        return ser
    med = vs[len(vs) // 2]
    if med <= 0:
        return ser
    out, bad = [], []
    for d, v in ser:
        if v and abs(v) >= PERSHARE_ABS and abs(v) / med >= PERSHARE_REL:
            bad.append((d, v))
        else:
            out.append((d, v))
    if bad and log:
        UNIT_ERRORS.append((round(med, 3), bad))
    return out


# ── ① 태그 빈칸 메우기(2026-09-25 · 배치 R §F) ────────────────────────────────
# 채우는 항목과, 겹치는 기간에서 두 태그가 맞아야 하는 폭(|대체값/본값 − 1| 의 중앙값 상한).
# 자기자본(eq)과 주식수(sh)만 채운다 — 시점별 시총·B/M 의 입력이고, 그 구멍이 배치 R 커버리지를 묶었다.
# 폭 — 자기자본은 지배주주 대 NCI 포함이라 비지배지분이 작은 회사에서만 같다(1%). 실측(2026-09-25 ·
#   fx+fx_pit 전수): 채울 수 있는 1,271칸 중 1% 문턱이 1,122칸(146사)을 통과시키고 ERIE(×10 — Exchange 포함)·
#   VTRS·HIG·UNM·OKE·CLX·FCX·HWM 같은 NCI 가 큰 회사는 막는다. EOG·DOV·HP·HAS·NSC·WEC·BRO 는 겹침이
#   전부 1.000, PPL 은 중앙값 1% 안이다. 주식수(희석 대 기본)는 정의 차가 원래 몇 % 라 3%.
# 🚨 채우지 않는 항목과 이유(같은 실측 · 채울 수 있었던 칸 · 겹침 |대체/본−1| 90분위) —
#   rev 15,259칸 · 0.98 / cogs 1,420 · 0.76   'max' 동점규칙 — 후보가 '총액 대 그 일부'(AVB 434배).
#   debt 3,160 · 0.23 / dep 3,625 · 0.86      태그마다 범위가 다르다(유동성 대체분 · DD&A 대 D&A).
#   dps 2,504 · 0.11 / cfo 1,638 · 0.24 / capex 880 · 1.54 / ni 1,080 · 0.20 / eps 971 · 0.03 / bb 209 / iss 125
#     — 선언 대 지급 시차 · 계속영업 대 전체 · 범위 차. 이번 배치가 쓰지 않는 항목이라 게시 전략 입력을
#       흔들지 않으려고 넣지 않았다(넣으려면 이 표에 폭을 적으면 된다 — _fill_gaps 가 그대로 돈다).
FILL_TOL = {"eq": 0.01, "sh": 0.03}
FILL_KEYS = tuple(FILL_TOL)
# 첫 관측보다 이른 칸(메우기 · 선행 법인 잇기)이 이어졌다고 보는 최대 간격 — extract 의 450일 가드와 같은 값.
# 실측: 알파벳 sh 는 2023-06 부터고 Google Inc 의 sh 는 2015-03 에서 끝난다 — 이으면 8년 구멍이 생긴다.
JOIN_DAYS = 450
FILL_LOG = {"cells": 0, "keys": {}, "refused": {}}   # main 이 로그로 찍는다(칸 수 · 거절 사유)


def _cand_series(gaap, cands, unit, scale, tie):
    """후보 태그마다 pick 결과 — extract 의 고르기와 **같은 순서·같은 단위 흐름**으로 돈다.

    ⚠ 옛 루프는 `unit` 을 태그마다 덮어쓴다(resolve_unit 의 반환값). 그래서 뒤 태그의 단위 탐색은
      앞 태그가 찾은 단위에서 시작하고, 레코드의 u 도 마지막으로 훑은 태그의 단위가 된다.
      기존 파일과 한 글자도 안 바뀌어야 하므로 그 흐름을 그대로 재현한다(u_rec 로 돌려준다).
    반환: (best, cands_all, u_rec) — best = (score, tag, q, a, i) · cands_all = [(score, 순번, tag, 실제단위, q, a, i)]."""
    best, allc = None, []
    for n, tag in enumerate(cands):
        node = gaap.get(tag)
        if not node:
            continue
        unit, vals = resolve_unit(node.get("units") or {}, unit)
        if not vals:
            continue
        q, a, i = pick(vals, scale)
        if not (q or a or i):
            continue
        # 최신 관측일이 늦은 태그가 이긴다. 같으면 항목별 동점규칙을 쓴다 —
        # 'max'는 값이 큰 쪽(총액), 기본은 관측이 많은 쪽(시계열이 긴 쪽).
        latest = max(s[0][0] for s in (q, a, i) if s)
        if tie == "max":
            newest = [s[0][1] for s in (a, q, i) if s and s[0][0] == latest]
            tiebreak = abs(newest[0]) if newest else 0.0
        else:
            tiebreak = len(q) + len(a) + len(i)
        score = (latest, tiebreak)
        allc.append((score, n, tag, unit, q, a, i))
        if best is None or score > best[0]:
            best = (score, tag, q, a, i)
    return best, allc, unit


def _runs(cells_asc, attr):
    """기간말 오름차순 칸 → [[첫 기간말, 끝 기간말, 속성]] (같은 속성이 이어지는 구간)."""
    out = []
    for d in cells_asc:
        a = attr(d)
        if out and out[-1][2] == a:
            out[-1][1] = d
        else:
            out.append([d, d, a])
    return out


def _set_tag_runs(rec, tag_of):
    """rec 의 칸마다 출처 태그를 적는다 — 모두 src 면 아무것도 싣지 않는다(기존 모양 그대로)."""
    alt = []
    for b in ("q", "a", "i"):
        for d, _v in rec.get(b) or []:
            t = tag_of.get((b, d), rec["src"])
            if t != rec["src"] and t not in alt:
                alt.append(t)
    rec.pop("alt", None)
    rec.pop("tg", None)
    if not alt:
        return
    idx = {rec["src"]: 0}
    idx.update({t: k + 1 for k, t in enumerate(alt)})
    rec["alt"] = alt
    rec["tg"] = {b: _runs(sorted(d for d, _v in rec[b]), lambda d, b=b: idx[tag_of.get((b, d), rec["src"])])
                 for b in ("q", "a", "i") if rec.get(b)}


def cell_tag(rec, bucket, end):
    """(버킷, 기간말) 칸의 출처 XBRL 태그."""
    for d0, d1, ti in (rec.get("tg") or {}).get(bucket) or []:
        if d0 <= end <= d1:
            return rec["src"] if ti == 0 else rec["alt"][ti - 1]
    return rec.get("src")


def _fill_gaps(key, rec, prim_unit, allc, tag_of, count=True):
    """고른 태그가 비운 기간만 다음 후보로 채운다. 기존 칸은 절대 안 건드린다. 채운 칸 수를 돌려준다.

    · 채우는 버킷 — 고른 태그 레코드에 **이미 있는 버킷만**. 새 버킷을 열면 소비자가 읽는 버킷
      (series() 는 i 없으면 q)이 바뀌어 멀쩡한 값이 달라진다.
    · 순서 — 남은 후보를 extract 의 점수(최신 관측일 · 동점규칙) 내림차순으로. 같으면 후보 목록 순.
    · 문턱 — 후보마다, 고른 태그와 **겹치는 기간**이 하나 이상 있고 |대체/본 − 1| 의 중앙값이
      FILL_TOL[key] 이하일 때만 쓴다. 겹침이 없으면 정의가 같은지 알 길이 없으므로 쓰지 않는다.
    · 단위 — 실제 단위가 고른 태그와 같은 후보만. 주당지표는 고른 계열 중앙값 기준 단위오류 칸도 거른다.
    """
    tol = FILL_TOL.get(key)
    if tol is None:
        return 0
    refused = FILL_LOG["refused"] if count else {}
    others = [c for c in allc if c[2] != rec["src"] and c[3] == prim_unit]
    others.sort(key=lambda c: (c[0], -c[1]), reverse=True)
    n_add = 0
    prim = {b: dict((d, v) for d, v in rec.get(b) or []) for b in ("q", "a", "i")}
    for _score, _n, tag, _u, q, a, i in others:
        for b, ser in (("q", q), ("a", a), ("i", i)):
            if b not in rec or not ser:
                continue
            ser = drop_pershare_unit_errors(ser, prim_unit, log=False)
            base = prim[b]
            ov = [abs(v / base[d] - 1.0) for d, v in ser if d in base and base[d]]
            have = set(d for d, _v in rec[b])
            add = [(d, v) for d, v in ser if d not in have]
            # 첫 관측보다 이른 칸은 **이어질 때만**(JOIN_DAYS) — 수년 떨어진 옛 칸을 붙이면 그 사이가
            # as-of 로 묵은 값이 되고, sh 는 load_fund 의 sho 대타(첫 sh 이전에만 쓴다)까지 막는다.
            first = min(have) if have else None
            pre = [d for d, _v in add if first and d < first]
            if pre and _days(max(pre), first) > JOIN_DAYS:
                refused["no_join"] = refused.get("no_join", 0) + len(pre)
                add = [(d, v) for d, v in add if d > first]
            if not add:
                continue
            if not ov:
                refused["no_overlap"] = refused.get("no_overlap", 0) + len(add)
                continue
            ov.sort()
            med = ov[len(ov) // 2] if len(ov) % 2 else (ov[len(ov) // 2 - 1] + ov[len(ov) // 2]) / 2
            if med > tol:
                refused["disagree"] = refused.get("disagree", 0) + len(add)
                continue
            if prim_unit == "USD/shares" or prim_unit.endswith("/shares"):
                vs = sorted(abs(v) for v in base.values() if v)
                pm = vs[len(vs) // 2] if vs else 0
                if pm > 0:
                    add = [(d, v) for d, v in add
                           if not (v and abs(v) >= PERSHARE_ABS and abs(v) / pm >= PERSHARE_REL)]
            for d, v in add:
                tag_of[(b, d)] = tag
            rec[b] = sorted(rec[b] + [[d, v] for d, v in add], key=lambda x: x[0], reverse=True)
            n_add += len(add)
    return n_add


def extract(facts: dict, fill: bool = True, guards: bool = True, force_src=None):
    """companyfacts → {키: {src, u, s, q/a/i[, alt, tg]}}. 값이 하나도 없는 항목은 담지 않는다.

    ⚠ 후보 태그는 '먼저 있는 것'이 아니라 **가장 최근까지 보고된 것**을 고른다.
    회사가 도중에 태그를 갈아타면 옛 태그도 값을 그대로 갖고 있어서, 우선순위대로
    집으면 죽은 시계열을 집는다. 실측(2026-07-25): JPM은 Revenues로 고르면 분기가
    2014년에서 멈추고, NVDA도 2020년에서 멈춘다 — 연간은 최신인데 분기만 낡아
    화면에서 알아채기 어려운 형태로 틀린다.

    🚨 2026-09-25 — 고른 태그가 **비운 기간**은 다음 후보로 채운다(fill · _fill_gaps · FILL_KEYS).
      종전엔 '한 항목 안에서 태그를 섞지 않는다' 였고 그 대가가 10년짜리 구멍이었다(EOG 자기자본
      2009-06 → 2019-12). 고른 태그의 값은 한 칸도 안 바꾸고, 채운 칸은 rec.alt · rec.tg 에 태그를
      적는다. 섞였다는 사실을 숨기지 않는 것이 옛 원칙의 뜻이었으므로 그것은 지킨다.
    guards=False — 450일 구간·항목 최신성 가드를 끈다(선행 법인 역사를 앞에 붙일 때 · 오늘 값이 아니다).
    force_src — {키: 태그}. 그 태그가 있으면 점수와 무관하게 그것을 고른다(선행 법인을 같은 태그로 잇기).
    """
    allf = (facts or {}).get("facts") or {}
    gaap = allf.get("us-gaap") or {}
    # us-gaap이 없으면 IFRS로 넘어간다(외국 사기업). 둘을 섞지는 않는다 — 한 회사의
    # 재무제표는 한 회계기준으로 작성된 것이고, 반씩 가져오면 합이 맞지 않는다.
    tagset = TAGS
    if not gaap and allf.get("ifrs-full"):
        gaap, tagset = allf["ifrs-full"], TAGS_IFRS
    out, cand_all, prim_u = {}, {}, {}
    for spec in tagset:
        key, cands, unit, scale = spec[0], spec[1], spec[2], spec[3]
        tie = spec[4] if len(spec) > 4 else "count"
        best, allc, unit = _cand_series(gaap, cands, unit, scale, tie)
        want = (force_src or {}).get(key)
        if want:
            forced = [c for c in allc if c[2] == want]
            if forced:
                c = forced[0]
                best = (c[0], c[2], c[4], c[5], c[6])
        if not best:
            continue
        _s, tag, q, a, i = best
        cand_all[key] = allc
        prim_u[key] = next(c[3] for c in allc if c[2] == tag)
        # 고른 태그 안에서도 한쪽 구간만 옛날에 멈춰 있을 수 있다(회사가 그 단위 보고를
        # 그만둔 경우). 최신 구간보다 450일 넘게 뒤처진 구간은 버린다 — 없는 것보다
        # 12년 전 숫자를 최신인 양 늘어놓는 쪽이 나쁘다. 450일이면 연간 보고 시차는 넉넉히 통과한다.
        newest = max(s[0][0] for s in (q, a, i) if s)
        rec = {"src": tag, "u": unit, "s": scale}
        dropped = []
        for name, ser in (("q", q), ("a", a), ("i", i)):
            if not ser:
                continue
            if guards and _days(ser[0][0], newest) > 450:
                dropped.append(name)
                continue
            ser = drop_pershare_unit_errors(ser, unit, log=guards)
            if not ser:
                continue
            rec[name] = ser
        if dropped:
            rec["stale"] = dropped     # 화면이 '이 구간은 회사가 더 이상 보고하지 않는다'를 적을 수 있게
        if not any(k in rec for k in ("q", "a", "i")):
            continue
        out[key] = rec

    # ── 항목 단위 최신성 가드 ────────────────────────────────────────────
    # 위 450일 규칙은 '한 항목 안에서' 뒤처진 구간만 잘라낸다. 그런데 어떤 항목은
    # 통째로 죽어 있다 — 회사가 그 줄을 우리가 읽을 수 있는 형태로 더 이상 안 내는 경우다.
    # 실측(2026-07-25): 은행은 '매출'이라는 항목 자체가 없다(순이자이익+비이자이익이 본체).
    #   RF·FITB는 후보 중 유일하게 잡히는 게 수수료수익(ASC 606)인데 2021·2023년에서 멈춘다.
    #   그걸 '매출'로 내보내면 4년 묵은 부분값이 총매출인 척한다.
    # 회사 전체의 최신 관측보다 450일 넘게 뒤처진 항목은 없는 것으로 둔다 — 없으면 없다고 적는다.
    if out and guards:
        newest_all = max(rec[k][0][0] for rec in out.values()
                         for k in ("q", "a", "i") if rec.get(k))
        dead = [key for key, rec in out.items()
                if _days(max(rec[k][0][0] for k in ("q", "a", "i") if rec.get(k)),
                         newest_all) > 450]
        for key in dead:
            out.pop(key)

    # ── ① 빈칸 메우기 — 가드를 다 통과한 항목·버킷에만(항목 집합·버킷 집합은 그대로다) ──
    if fill and tagset is TAGS:
        for key, rec in out.items():
            if key not in FILL_TOL:
                continue
            tag_of = {}
            n = _fill_gaps(key, rec, prim_u[key], cand_all[key], tag_of, count=guards)
            if n:
                _set_tag_runs(rec, tag_of)
                if guards:                  # 선행 법인 추출(guards=False)의 채움은 세지 않는다 — 다 쓰이지 않는다
                    FILL_LOG["cells"] += n
                    FILL_LOG["keys"][key] = FILL_LOG["keys"].get(key, 0) + n
    return out


# ── companyfacts 받기(러너는 그대로 · 로컬 재생성은 캐시·속도 상한) ─────────────────
_FETCH = {"dir": None, "offline": False, "mem": {}, "n_net": 0, "n_cache": 0}


def set_fetch(cache_dir=None, offline=False, rate=None):
    """로컬 재생성용. cache_dir — 원본 companyfacts gz 를 두는 곳(저장소 밖) · offline — SEC 를 안 부른다 ·
    rate — edgar 호출 상한(초당). 러너는 부르지 않는다(기존 동작 그대로)."""
    _FETCH["dir"], _FETCH["offline"] = cache_dir, bool(offline)
    if rate:
        edgar.RATE = float(rate)
        edgar._MIN_GAP = 1.0 / edgar.RATE


def get_facts(cik):
    """CIK → companyfacts dict(없으면 None). 캐시가 있으면 그것을 먼저 읽는다."""
    cik = int(cik)
    mem = _FETCH["mem"]
    if cik in mem:
        return mem[cik]
    j = None
    d = _FETCH["dir"]
    p = os.path.join(d, "CIK%010d.json.gz" % cik) if d else None
    if p and os.path.exists(p):
        with gzip.open(p) as f:
            j = json.loads(f.read().decode("utf-8"))
        _FETCH["n_cache"] += 1
    elif p and os.path.exists(p[:-8] + ".404"):
        j = None
    elif not _FETCH["offline"]:
        j = edgar.get_json(FACTS_URL % cik)
        _FETCH["n_net"] += 1
        if p and j is not None:
            os.makedirs(d, exist_ok=True)
            with gzip.open(p + ".tmp", "wb") as f:
                f.write(json.dumps(j, separators=(",", ":")).encode("utf-8"))
            os.replace(p + ".tmp", p)
    if len(mem) > 6:                    # 선행 법인은 같은 줄에서 두세 번 쓰인다 — 조금만 들고 있는다
        mem.pop(next(iter(mem)))
    mem[cik] = j
    return j


# ── ② 지주사 재편 잇기 표 — data/fx_splice.json(_issuer_map.json 에서 --build-splices 가 짓는다) ──
# 잇는 판정: §A0 발행사 지도의 splice 결정 중 **재무가 이어지는** 종류만(회계상 인수자·주주 1:1 이 선행 법인).
SPLICE_KINDS = ("holdco_reorg", "redomicile", "merger_holdco", "separation_parent")
# misfiled_alias(OKE·TMUS)는 Form 4 가 옛 CIK 로 잘못 들어온 것이지 재무 법인이 바뀐 게 아니다 — 잇지 않는다.
# 날짜로 가르는 이름(mode cut) — 기간말 ≤ 경계는 앞 법인 값만, 뒤는 지금 법인 값만(서로 채우지 않는다).
CUT_WHY = {
    "DD": "2014-06..2017-08 의 DD 는 E.I. du Pont(30554). 1666700(DowDuPont → DuPont de Nemours)의 그 시절 비교 "
          "재무는 회계상 인수자 Dow Chemical 의 것이라(주식수 11~12억 · 자기자본 260~300억$) DD 로 쓰면 남의 회사다.",
    "FTI": "2016-12 까지 FTI 는 FMC Technologies(1135152), 2017-01 부터 TechnipFMC(1681459 · 합병 종결 2017-01-16 · "
           "지도의 2017-01 행은 두 CIK). 두 법인을 기간말로 가른다 — 2016-12-31 까지는 FMC Technologies 가 낸 값만 쓰고 "
           "TechnipFMC 의 합병 전 비교 재무로 채우지 않는다.",
}


def _month_end(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
    return (nxt - dt.timedelta(days=1)).isoformat()


def build_splices(path_map=ISSUER_MAP, out=SPLICE_PATH):
    """_issuer_map.json → data/fx_splice.json. SEC 를 부르지 않는다."""
    raw = io.open(path_map, "rb").read()
    M = json.loads(raw.decode("utf-8"))
    groups, tm = M.get("groups") or {}, M.get("tm") or {}
    g_of = {}
    for g, v in groups.items():
        for c in v.get("ciks") or []:
            g_of[int(c[0])] = g
    edges = {}
    for s in M.get("splices") or []:
        if s.get("decision") != "splice" or s.get("kind") not in SPLICE_KINDS:
            continue
        g = g_of.get(int(s["succ"])) or g_of.get(int(s["pred"]))
        if not g:
            continue
        edges.setdefault(g, []).append(s)
    ent = {}
    for g, es in sorted(edges.items()):
        es = sorted(es, key=lambda s: s["date"])
        cur = int(es[-1]["succ"])
        chain, c = [], cur
        for s in reversed(es):              # 가장 최근 재편부터 거슬러 올라간다
            if int(s["succ"]) == c:
                chain.append(int(s["pred"]))
                c = int(s["pred"])
        for t in sorted((groups[g].get("tickers") or {})):
            if t in CUT_WHY:
                continue
            ent[t] = {"mode": "prepend", "cur": cur, "pred": chain, "group": g,
                      "kinds": [s["kind"] for s in es], "dates": [s["date"] for s in es]}
    for t, why in CUT_WHY.items():
        rows = tm.get(t) or []
        segs = []
        for r in rows:                      # 주 CIK 가 바뀌는 곳이 경계다
            c = int(r[3])
            if segs and segs[-1][0] == c:
                segs[-1][2] = r[1]
            else:
                segs.append([c, r[0], r[1]])
        if len(segs) < 2:
            raise SystemExit("🚨 %s: 지도에 주 CIK 가 하나뿐이다 — cut 표를 지을 수 없다" % t)
        out_segs = []
        for k, (c, m0, m1) in enumerate(segs):
            lo = None if k == 0 else out_segs[-1][2]
            hi = None if k == len(segs) - 1 else _month_end(m1)
            out_segs.append([c, lo, hi])
        # 경계는 '앞 구간의 끝 기간말 < 뒤 구간' — 뒤 구간의 lo 는 앞 구간 hi 초과로 읽는다
        ent[t] = {"mode": "cut", "segs": out_segs, "tenure": [[c, m0, m1] for c, m0, m1 in segs], "why": why}
    doc = {"note": "refresh_facts · pit_facts 가 읽는 선행 CIK 잇기 표. build/refresh_facts.py --build-splices 가 "
                   "data/_issuer_map.json 에서 짓는다(손으로 고치지 말 것). prepend = 선행 법인 관측 중 지금 파일 그 "
                   "태그·버킷의 첫 관측보다 이른 것만 앞에 붙인다. cut = segs [CIK, lo(초과), hi(이하)] 의 기간말 구간마다 "
                   "그 CIK 값만 쓴다.",
           "src": {"_issuer_map.json": hashlib.sha256(raw).hexdigest()},
           "kinds": list(SPLICE_KINDS), "t": ent}
    body = json.dumps(doc, ensure_ascii=False, indent=0, sort_keys=False) + "\n"
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    print("선행 CIK 잇기 표: prepend %d · cut %d → %s"
          % (sum(1 for v in ent.values() if v["mode"] == "prepend"),
             sum(1 for v in ent.values() if v["mode"] == "cut"), os.path.relpath(out, ROOT)))
    return doc


def load_splices(path=SPLICE_PATH):
    try:
        return (json.load(io.open(path, encoding="utf-8")).get("t")) or {}
    except Exception:
        return {}


def _pick_table(facts):
    """companyfacts → {태그: {버킷: {기간말: 값}}} — TAGS 후보 태그 전부(선행·후계가 같은 값을 냈는지 대조용)."""
    allf = (facts or {}).get("facts") or {}
    gaap = allf.get("us-gaap") or {}
    tagset = TAGS
    if not gaap and allf.get("ifrs-full"):
        gaap, tagset = allf["ifrs-full"], TAGS_IFRS
    out = {}
    for spec in tagset:
        unit, scale = spec[2], spec[3]
        for tag in spec[1]:
            node = gaap.get(tag)
            if not node or tag in out:
                continue
            _u, vals = resolve_unit(node.get("units") or {}, unit)
            if not vals:
                continue
            q, a, i = pick(vals, scale)
            out[tag] = {"q": dict(map(tuple, q)), "a": dict(map(tuple, a)), "i": dict(map(tuple, i))}
    return out


def _all_cells(tags):
    for k, rec in tags.items():
        for b in ("q", "a", "i"):
            for d, v in rec.get(b) or []:
                yield k, b, d, v


def _cell_tags(rec):
    """rec 의 (버킷, 기간말) → 태그(지금 적힌 tg 구간을 칸 단위로 편다)."""
    return {(b, d): cell_tag(rec, b, d) for b in ("q", "a", "i") for d, _v in rec.get(b) or []}


JOIN_REFUSED = []                           # _add_cells 가 이음 간격 때문에 안 붙인 (버킷, 선행 끝, 지금 첫)
SPLICE_FAIL = "선행 재무 못 받음"            # splice_doc 로그 머리 — 이 로그가 있으면 부르는 쪽이 그 파일을 쓰지 않는다


def _add_cells(rec, prec, lo=None, hi=None, below=None):
    """prec 의 칸을 rec 에 더한다 → [(버킷, 기간말, 태그)]. 규칙은 splice_doc 머리말."""
    added = []
    ptag = _cell_tags(prec)
    all_first = min((d for b in ("q", "a", "i") for d, _v in rec.get(b) or []), default=None)
    for b in ("q", "a", "i"):
        ser = prec.get(b) or []
        if not ser:
            continue
        if b in rec and rec.get(b):
            cut = min(d for d, _v in rec[b])
        elif b == "a" or not (rec.get("q") or rec.get("i")):
            cut = all_first
        else:
            continue                        # 새 i·q 버킷을 열면 소비자가 읽는 버킷이 바뀐다
        if below is False:
            cut = None
        have = set(d for d, _v in rec.get(b) or [])
        new = [[d, v] for d, v in ser
               if d not in have and (cut is None or d < cut)
               and (lo is None or d > lo) and (hi is None or d <= hi)]
        if new and cut is not None and _days(max(d for d, _v in new), cut) > JOIN_DAYS:
            JOIN_REFUSED.append((b, max(d for d, _v in new), cut))
            continue                        # 이어지지 않는다 — 수년 구멍을 사이에 둔 옛 역사는 붙이지 않는다
        if not new:
            continue
        rec[b] = sorted((rec.get(b) or []) + new, key=lambda x: x[0], reverse=True)
        added += [(b, d, ptag.get((b, d), prec["src"])) for d, _v in new]
    return added


def _agree(key, rec, prec):
    """선행 법인이 다른 태그로 이을 때 — 겹치는 기간(후계의 비교 재무)에서 값이 맞는가."""
    tol = FILL_TOL.get(key)
    if tol is None:
        return False
    ov = []
    for b in ("q", "a", "i"):
        cur = dict((d, v) for d, v in rec.get(b) or [])
        for d, v in prec.get(b) or []:
            if d in cur and cur[d]:
                ov.append(abs(v / cur[d] - 1.0))
    if not ov:
        return False
    ov.sort()
    return ov[len(ov) // 2] <= tol


def splice_doc(doc, entry, get=None, log=None):
    """③ 한 파일에 선행 법인 관측을 잇고, 칸마다 출처 CIK 를 적는다(doc 를 고쳐 돌려준다).

    prepend — entry.pred(가까운 선행부터)마다 같은 태그(force_src)로 extract(guards=False) 한 뒤,
      항목마다 **지금 파일 그 버킷의 첫 기간말보다 이른 칸만** 붙인다. 지금 파일에 없는 버킷은
      a(연간)이거나 그 항목에 i·q 가 아예 없을 때만 연다. 지금 파일에 없는 항목은 선행 법인 것을
      통째로 싣되 파일 최신 관측보다 450일 넘게 뒤처지면 싣지 않는다(extract 의 항목 가드와 같다).
      선행 법인이 같은 태그를 안 냈으면 겹치는 기간 값이 맞을 때(_agree)만 잇는다.
    cut — entry.segs 의 기간말 구간마다 그 CIK 값만 남긴다. 지금 파일(마지막 구간)의 구간 밖 칸은 지운다
      (DD 의 Dow 비교 재무). 앞 구간은 지금 파일에 있는 항목만 채운다.
    출처 — 칸마다 CIK 집합. 선행·후계 누가 내든 같은 태그·버킷·기간말에 같은 값을 냈으면 둘 다 적는다."""
    get = get or get_facts
    log = log if log is not None else []
    tags = doc["tags"]
    base = int(doc["cik"])
    src_of = {}                                            # (키, 버킷, 기간말) → 그 칸을 준 CIK
    for k, b, d, _v in _all_cells(tags):
        src_of[(k, b, d)] = base
    names = {base: doc.get("nm") or ""}
    chain = [base]
    mode = entry.get("mode")
    if mode == "prepend":
        for pc in entry.get("pred") or []:
            pc = int(pc)
            if pc == base or pc in chain:
                continue
            pf = get(pc)
            if not pf:
                log.append(SPLICE_FAIL + " 선행 %d" % pc)
                continue
            chain.append(pc)
            names[pc] = pf.get("entityName") or ""
            ptags = extract(pf, fill=True, guards=False, force_src={k: r["src"] for k, r in tags.items()})
            newest_all = max((d for _k, _b, d, _v in _all_cells(tags)), default=None)
            for k, prec in ptags.items():
                if k not in LABEL:
                    continue
                rec = tags.get(k)
                if rec is None:
                    pn = max(d for b in ("q", "a", "i") for d, _v in prec.get(b) or [])
                    if newest_all and _days(pn, newest_all) > 450:
                        continue
                    rec = {"src": prec["src"], "u": prec["u"], "s": prec["s"]}
                    tg_new = {}
                    added = _add_cells(rec, prec, below=False)
                    if not added:
                        continue
                    tags[k] = rec
                    doc.setdefault("labels", {})[k] = LABEL[k]
                    log.append("%s 항목을 선행 %d 에서 통째로(지금 파일에 없음 · %d칸)" % (k, pc, len(added)))
                else:
                    if prec["u"] != rec["u"] or prec["s"] != rec["s"]:
                        continue
                    if prec["src"] != rec["src"] and not _agree(k, rec, prec):
                        log.append("%s 선행 %d 태그 다름(%s ≠ %s) · 겹침 불일치 — 안 이음" % (k, pc, prec["src"], rec["src"]))
                        continue
                    tg_new = _cell_tags(rec)
                    n_j = len(JOIN_REFUSED)
                    added = _add_cells(rec, prec)
                    for b, pe, fc in JOIN_REFUSED[n_j:]:
                        log.append("%s.%s 선행 %d 끝 %s ↔ 지금 첫 %s — %d일 떨어져 안 이음" % (k, b, pc, pe, fc, _days(pe, fc)))
                if added:
                    tg_new.update({(b, d): t for b, d, t in added})
                    _set_tag_runs(rec, tg_new)
                    for b, d, _t in added:
                        src_of[(k, b, d)] = pc
    elif mode == "cut":
        segs = [(int(c), lo, hi) for c, lo, hi in entry.get("segs") or []]
        mine = [s for s in segs if s[0] == base]
        if not mine:
            raise SystemExit("🚨 cut 표에 지금 파일 CIK %d 가 없다" % base)
        _c, lo0, hi0 = mine[0]
        n_cut = 0
        for k in list(tags):                               # 지금 법인 구간 밖 칸을 지운다
            rec = tags[k]
            tg0 = _cell_tags(rec)
            for b in ("q", "a", "i"):
                if rec.get(b):
                    n0 = len(rec[b])
                    rec[b] = [x for x in rec[b] if (lo0 is None or x[0] > lo0) and (hi0 is None or x[0] <= hi0)]
                    n_cut += n0 - len(rec[b])
                    if not rec[b]:
                        rec.pop(b)
            _set_tag_runs(rec, tg0)
        log.append("cut: 지금 법인 %d 구간(%s, %s] 밖 %d칸을 뺐다" % (base, lo0, hi0, n_cut))
        for pc, lo, hi in segs:
            if pc == base:
                continue
            pf = get(pc)
            if not pf:
                log.append(SPLICE_FAIL + " 구간 %d" % pc)
                continue
            chain.append(pc)
            names[pc] = pf.get("entityName") or ""
            ptags = extract(pf, fill=True, guards=False, force_src={k: r["src"] for k, r in tags.items()})
            for k, rec in tags.items():
                prec = ptags.get(k)
                if not prec or prec["u"] != rec["u"] or prec["s"] != rec["s"]:
                    continue
                tg0 = _cell_tags(rec)
                added = _add_cells(rec, prec, lo=lo, hi=hi, below=False)
                if added:
                    tg0.update({(b, d): t for b, d, t in added})
                    _set_tag_runs(rec, tg0)
                    for b, d, _t in added:
                        src_of[(k, b, d)] = pc
                    log.append("cut: %s 구간 %d (%s, %s] %d칸" % (k, pc, lo, hi, len(added)))
        for k in [k for k, r in tags.items() if not any(r.get(b) for b in ("q", "a", "i"))]:
            tags.pop(k)
            (doc.get("labels") or {}).pop(k, None)
    # 같은 값을 낸 다른 CIK 도 적는다(후계의 비교 재무 = 선행의 원 보고) — prepend 만. cut 은 다른 법인이다.
    tables = {}
    if mode == "prepend":
        for c in chain[1:]:
            f = get(c)
            tables[c] = _pick_table(f) if f else {}
    doc_ck = {}
    for k, rec in tags.items():
        tagmap = _cell_tags(rec)
        ck = {}
        for b in ("q", "a", "i"):
            for d, v in rec.get(b) or []:
                tg = tagmap.get((b, d), rec["src"])
                s = {src_of.get((k, b, d), base)}
                if mode == "prepend":
                    for c in chain:
                        w = tables.get(c, {}).get(tg, {}).get(b, {}).get(d)
                        if c not in s and w is not None and _same_fig(v, w):
                            s.add(c)
                ck[(b, d)] = sorted(s)
        doc_ck[k] = ck
    _set_ck(doc, doc_ck, names)
    return doc


# 선행·후계가 «같은 숫자를 냈다» 로 보는 폭 — 후계의 비교 재무는 뒤 제출이라 소수 재작성이 섞인다.
# 실측: CI 2015-12-31 자기자본 새 지주사 12,020 · 옛 법인 12,044(0.2%). 0.5% 안이면 두 CIK 를 다 적는다.
CORROB_TOL = 0.005


def _same_fig(v, w):
    if v == w:
        return True
    try:
        return abs(float(v) - float(w)) <= CORROB_TOL * max(abs(float(v)), abs(float(w)))
    except (TypeError, ValueError):
        return False


def _set_ck(doc, doc_ck, names=None):
    """칸별 CIK 집합 → rec.ck(버킷별 구간 · 파일 CIK 하나뿐이면 싣지 않는다) · doc.ciks(요약)."""
    base = int(doc["cik"])
    summ = {}
    for k, rec in doc["tags"].items():
        rec.pop("ck", None)
        ck = doc_ck.get(k) or {}
        runs = {}
        for b in ("q", "a", "i"):
            ds = sorted(d for d, _v in rec.get(b) or [])
            if not ds:
                continue
            for d in ds:
                for c in ck.get((b, d), [base]):
                    s = summ.setdefault(c, [d, d, 0])
                    s[0], s[1], s[2] = min(s[0], d), max(s[1], d), s[2] + 1
            if any(ck.get((b, d), [base]) != [base] for d in ds):
                runs[b] = _runs(ds, lambda d, b=b: ck.get((b, d), [base]))
        if runs:
            rec["ck"] = runs
    nm = names or {}
    doc["ciks"] = [[c, v[0], v[1], v[2], (nm.get(c) if c != base else doc.get("nm")) or ""]
                   for c, v in sorted(summ.items(), key=lambda kv: (kv[1][0], kv[0]))]
    return doc


def cell_ciks(doc, key, end, bucket=None):
    """(키, 기간말[, 버킷]) 관측이 어느 CIK 의 제출에서 왔나 → [CIK…](그 칸이 없으면 []).
    버킷을 안 주면 i → q → a 차례(load_fund 의 series() 와 같은 우선)."""
    rec = (doc.get("tags") or {}).get(key) or {}
    for b in ((bucket,) if bucket else ("i", "q", "a")):
        if not any(d == end for d, _v in rec.get(b) or []):
            continue
        for d0, d1, cs in (rec.get("ck") or {}).get(b) or []:
            if d0 <= end <= d1:
                return list(cs)
        return [int(doc["cik"])]
    return []


def make_doc(t, cik, j, tags, name="", used_pred=0, splice=None, get=None, log=None):
    """수집 결과 → fx/fx_pit 파일 한 벌(refresh_facts · pit_facts 공용). splice 가 있으면 잇고, 없어도 doc.ciks 를 싣는다."""
    std = "IFRS" if not (((j.get("facts") or {}).get("us-gaap"))) else "us-gaap"
    doc = {
        "t": t, "cik": int(cik), "nm": j.get("entityName") or name,
        "labels": {k: LABEL[k] for k in tags if k in LABEL},
        "std": std,          # 화면이 '이 표는 IFRS 기준'을 적을 수 있게
        "tags": tags,
    }
    if used_pred:
        # 현행 법인이 아니라 전신 법인의 재무다 — 화면이 그 사실을 적을 수 있게 남긴다
        doc["pred"] = 1
    if splice:
        splice_doc(doc, splice, get=get, log=log)
    else:
        _set_ck(doc, {})
    return doc


def crosscheck_stat(tickers, mc_by_t, fund_by_t):
    """yfinance 단면 지표 vs SEC 원본 — 이 사이트의 펀더멘털 화면이 무엇 위에 서 있는지 재는 값.

    화면(스크리너·상대가치·종목)이 쓰는 재무는 yfinance .info의 단면이다. 오늘 SEC 원본이
    붙었으니 **같은 회사·같은 지표를 두 소스로 계산해 얼마나 맞는지** 잰다.
    안 재면 "우리 숫자가 맞나"에 답할 근거가 없다.

      PSR = 시가총액 / 최근 연간 매출        PBR = 시가총액 / 자기자본(지배주주)

    회계기준이 다른 IFRS 보고 회사는 뺀다. ROE는 넣지 않는다 — yfinance는 TTM 순이익을
    **평균** 자기자본으로 나누고 여기 값은 기말 시점이라, 차이가 나는 게 정상이라 비교가 무의미하다.
    """
    out = {}
    for key, num, den_key, den_kind in (("ps", "mc", "rev", "a"), ("pb", "mc", "eq", "i")):
        diffs = []
        for t in tickers:
            try:
                d = json.load(io.open(os.path.join(DIR_FX, "%s.json" % t), encoding="utf-8"))
            except Exception:
                continue
            if d.get("std") == "IFRS":
                continue
            ser = ((d.get("tags") or {}).get(den_key) or {}).get(den_kind) or []
            mc = mc_by_t.get(t)
            yf = (fund_by_t.get(t) or {}).get(key)
            if not ser or not mc or not yf or yf == 0 or ser[0][1] <= 0:
                continue
            sec = (mc * 100) / ser[0][1]            # fund.mc는 억$ → 백만$
            diffs.append(abs(sec - yf) / abs(yf) * 100)
        if not diffs:
            continue
        diffs.sort()
        n = len(diffs)
        out[key] = {"n": n,
                    "median": round(diffs[n // 2] if n % 2 else (diffs[n // 2 - 1] + diffs[n // 2]) / 2, 2),
                    "w5": round(sum(1 for x in diffs if x <= 5) / n * 100, 1),
                    "w20": round(sum(1 for x in diffs if x <= 20) / n * 100, 1),
                    "gross": sum(1 for x in diffs if x > 100)}
    out["note"] = ("yfinance 단면 지표와 SEC 원본으로 계산한 값의 차이(%). 화면이 쓰는 재무가 "
                   "원본과 얼마나 맞는지 재는 값이다. IFRS 보고 회사는 제외.")
    return out


def load_universe():
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        d = json.load(f)
    return [(s["t"], s.get("name") or "") for s in d["stocks"]]


def load_mc():
    """티커 → 시가총액(억$). 지수 FCF의 시총 커버를 재는 데만 쓴다."""
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {s["t"]: (s.get("fund") or {}).get("mc") for s in d["stocks"]}


def load_fund():
    """티커 → yfinance 재무 단면. SEC 원본과 대조하는 데 쓴다."""
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {s["t"]: (s.get("fund") or {}) for s in d["stocks"]}


def load_cik_map():
    """공시 파이프라인이 이미 확정한 티커→CIK를 재사용한다(전신 법인 보정 포함).
    없으면 SEC 매핑을 직접 읽는다."""
    # ⚠ 2026-08-03: data/industry.json → data/cik_map.json 으로 바뀌었고 값 모양도
    #   [sic, sd, cik] 배열 → cik 하나로 바뀌었다(SIC 분류를 걷어냈다).
    p = os.path.join(DATA, "cik_map.json")
    if os.path.exists(p):
        try:
            co = json.load(io.open(p, encoding="utf-8")).get("co") or {}
            m = {t: v for t, v in co.items() if v}
            if m:
                return m, "data/cik_map.json"
        except Exception:
            pass
    return {k: v for k, v in edgar.ticker_cik_map().items()}, "SEC company_tickers.json"


def local_args(argv=None):
    """로컬 재생성 옵션(러너는 아무것도 안 준다 — 기존 동작 그대로).
    --cache DIR  원본 companyfacts gz 캐시(저장소 밖) · --offline  캐시만 읽는다 · --rate R  초당 호출 상한
    --only T1,T2  그 종목만(정리·요약을 건너뛴다) · --no-summary  data/facts.json 을 쓰지 않는다."""
    import argparse
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--cache")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--rate", type=float)
    ap.add_argument("--only")
    ap.add_argument("--no-summary", action="store_true")
    ap.add_argument("--build-splices", action="store_true")
    a, _rest = ap.parse_known_args(argv)
    local = bool(a.cache or a.offline or a.rate or a.only or a.no_summary)
    if local and not a.offline and not (os.environ.get("SEC_UA") or "").strip():
        raise SystemExit("🚨 로컬 재생성은 SEC_UA 환경변수를 명시해야 돈다(edgar.py 기본값을 조용히 쓰지 않는다)")
    if a.offline and not a.cache:
        raise SystemExit("🚨 --offline 은 --cache 가 있어야 한다")
    set_fetch(a.cache, a.offline, a.rate)
    return a


def main() -> int:
    A = local_args()
    if A.build_splices:
        build_splices()
        return 0
    uni = load_universe()
    only = set(x.strip() for x in (A.only or "").split(",") if x.strip())
    if only:
        uni = [(t, nm) for t, nm in uni if t in only]
    mc_by_t = load_mc()
    fund_by_t = load_fund()
    cmap, src = load_cik_map()
    print("티커→CIK 출처: %s (%d개)" % (src, len(cmap)))
    splices = load_splices()
    print("선행 CIK 잇기 표: %d종 (%s)" % (len(splices), os.path.relpath(SPLICE_PATH, ROOT)))

    os.makedirs(DIR_FX, exist_ok=True)
    n_new = n_upd = n_same = n_pred = n_ifrs = 0
    cov = {spec[0]: 0 for spec in TAGS}
    got, miss, empty = [], [], []
    spl_log = {}

    for n, (t, name) in enumerate(uni, 1):
        cik = cmap.get(t) or cmap.get(t.upper())
        if not cik:
            miss.append(t)
            continue
        j = get_facts(cik)
        tags = extract(j) if j else {}
        # 지주회사 전환 직후의 새 법인은 us-gaap 사실이 0개다(XOM 실측). 재무는 전신 법인
        # 아래에 그대로 있으므로 공시 파이프라인과 같은 표를 보고 그쪽에서 가져온다.
        used_pred = 0
        if not tags:
            for pcik in edgar.PREDECESSOR.get(t.upper(), []):
                pj = get_facts(pcik)
                ptags = extract(pj) if pj else {}
                if ptags:
                    j, tags, cik, used_pred = pj, ptags, pcik, 1
                    n_pred += 1
                    break
        if not j:
            miss.append(t)
            continue
        if not tags:
            # 재무 사실이 아예 없는 회사가 실제로 있다. 실측 두 유형(2026-07-25):
            #   (1) 아직 재무를 낸 적 없는 신규 등록 법인 — FDXF·HONA(분사)·SPCX. ffd(수수료)만 있다.
            #   (2) 지주회사 전환 직후의 새 법인 — 전신 CIK에서 가져오므로 위에서 이미 처리된다.
            # 빈 파일을 만들지 않고 목록에만 남긴다(화면은 '없음'을 사유와 함께 적는다).
            empty.append((t, j.get("entityName") or name))
            continue
        # ② 지주사 재편 잇기 · ③ 칸별 출처 CIK(make_doc 이 한다 — pit_facts 와 같은 함수)
        sp = splices.get(t)
        lg = []
        doc = make_doc(t, cik, j, tags, name=name, used_pred=used_pred, splice=sp, get=get_facts, log=lg)
        if sp:
            spl_log[t] = [c[0] for c in doc.get("ciks") or []]
            for x in lg:
                print("  ~ %s %s" % (t, x))
            if any(x.startswith(SPLICE_FAIL) for x in lg):
                # 🚨 선행 법인을 못 받았다(일시 장애) — 이번 주 파일을 쓰면 잇기 역사가 한 주 동안 사라진다.
                #   지난 파일을 그대로 두고 수집 실패로 센다(정리도 건너뛰게 된다).
                print("  ⚠ %s 선행 CIK 재무를 못 받아 이번 실행에서는 파일을 안 바꾼다" % t)
                miss.append(t)
                continue
        for k in doc["tags"]:
            cov[k] += 1
        std = doc["std"]
        if std == "IFRS":
            n_ifrs += 1
        body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
        fn = os.path.join(DIR_FX, "%s.json" % t.replace("/", "_"))
        old = None
        if os.path.exists(fn):
            try:
                old = io.open(fn, encoding="utf-8", newline="").read()   # 바이트 그대로 비교(개행 변환 없이)
            except Exception:
                old = None
        if old is None:
            n_new += 1
        elif old == body:
            n_same += 1
            got.append(t)
            continue
        else:
            n_upd += 1
        io.open(fn, "w", encoding="utf-8", newline="").write(body)   # 🚨 Windows 로컬 재생성이 CRLF 로 쓰지 않게(러너는 원래 LF)
        got.append(t)
        if n % 100 == 0:
            print("  … %d/%d" % (n, len(uni)))

    if not got:
        print("❌ 수집 0건 — 갱신 중단(이전본 유지)")
        return 1

    # 유니버스에서 빠진 종목 파일 정리
    # 🚨 2026-08-05 — 기준이 `set(got)`(이번 실행에서 **성공한** 종목)이었다. 네트워크가
    #   흔들려 companyfacts 를 못 받은 회사는 miss 로 빠지고, 그 회사의 18년치 재무 시계열
    #   파일이 그대로 삭제됐다. 커버 게이트는 90% 라 그 아래를 못 잡는다 — 즉 일시적 EDGAR
    #   장애 한 번이 이미 발표한 자료를 영구히 지울 수 있었다(잡은 그대로 "성공"으로 끝난다).
    #   정리의 기준은 "못 받았다"가 아니라 **"유니버스에 없다"** 여야 한다.
    keep = {t for t, _c in uni}
    n_miss = len(uni) - len(got)
    n_del = 0
    if only:
        print("  ~ --only %d종 — 정리·요약을 건너뛴다" % len(only))
    elif n_miss:
        # 수집이 온전할 때만 정리한다. 지우는 것은 되돌릴 수 없고, 안 지우는 것은 다음
        # 실행이 다시 지울 수 있다 — 비대칭이 명백하므로 안전한 쪽으로 판단한다.
        print("  ⚠ 이번 실행에서 %d사를 못 받았다 — 스테일 파일 정리를 건너뛴다"
              "(못 받은 회사의 재무가 지워지는 것을 막는다)" % n_miss)
    else:
        for fn in os.listdir(DIR_FX):
            if fn.endswith(".json") and fn[:-5] not in keep:
                os.remove(os.path.join(DIR_FX, fn))
                n_del += 1

    # 가장 최근 관측일을 기준일로 삼는다(회사가 안 내면 안 움직인다 — 공시 축과 같은 성격)
    # ⚠ 예전엔 got[:80]만 훑었다. got 은 stocks.json 순서라 표본 밖 종목이 더 최근 기간을
    #    보고하면 기준일이 조용히 과거로 찍힌다 — 실제로 SNA(순번 227)가 2026-07-04 을
    #    보고했는데 화면은 2026-06-30 으로 4일 이르게 나왔다. 전수로 훑는다(515종·수 초).
    last = ""
    for t in got:
        try:
            d = json.load(io.open(os.path.join(DIR_FX, "%s.json" % t), encoding="utf-8"))
        except Exception:
            continue
        for rec in d["tags"].values():
            for k in ("q", "a", "i"):
                if rec.get(k) and rec[k][0][0] > last:
                    last = rec[k][0][0]

    # ── 클린서플러스 실측 ──────────────────────────────────────────────
    # RIM(잔여이익모형)은 '장부가 증분 = 이익 − 배당'이 성립한다는 전제 위에 선다.
    xc = crosscheck_stat(got, mc_by_t, fund_by_t)
    summary = {
        "note": "SEC EDGAR companyfacts(XBRL) 수집 요약. 실제 숫자는 종목별 data/fx/<티커>.json에 있다. "
                "재작성이 있으면 제출일이 가장 늦은 값을 쓴다. 6·9개월 누적 구간은 분기로 세지 않는다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": last,
        "n_co": len(got),
        "n_uni": len(uni),
        "labels": LABEL,
        "cov": {k: round(cov[k] / max(1, len(got)) * 100, 1) for k in cov},
        "no_facts": [t for t, _n in empty],
        "miss": miss,
        "xcheck": xc,
        "limits": [
            "숫자는 회사가 XBRL로 태깅해 제출한 값 그대로다 — 랩이 조정하거나 재분류하지 않는다.",
            "회사마다 쓰는 태그가 달라 같은 줄이라도 출처 태그가 다를 수 있다(각 항목에 태그명을 표기한다).",
            "6·9개월 누적 구간은 분기에서 제외한다. 그래서 분기 항목이 비는 회사가 있다.",
            "외국 사기업은 IFRS(ifrs-full)로 보고한다 — 같은 항목 키에 담되 출처 태그를 표기해 섞였다는 사실을 드러낸다.",
            "재무를 아직 낸 적 없는 신규 등록 법인(분사 직후 등)은 빈 채로 둔다 — 추정치로 채우지 않는다.",
        ],
    }
    if A.no_summary or only:
        print("  ~ data/facts.json 은 쓰지 않았다(--no-summary · --only)")
    else:
        io.open(OUT_SUM, "w", encoding="utf-8", newline="").write(
            json.dumps(summary, ensure_ascii=False, separators=(",", ":")) + "\n")

    sz = sum(os.path.getsize(os.path.join(DIR_FX, f)) for f in os.listdir(DIR_FX)) / 1024
    print("재무 시계열: %d/%d사 · %.1fMB (평균 %.1fKB) — 신규 %d · 변경 %d · 동일 %d · 삭제 %d"
          % (len(got), len(uni), sz / 1024, sz / max(1, len(got)), n_new, n_upd, n_same, n_del))
    print("기준일(최근 관측 기간말): %s" % (last or "—"))
    print("택소노미: us-gaap %d사 · IFRS %d사" % (len(got) - n_ifrs, n_ifrs))
    if xc:
        for k, lab in (("ps", "PSR"), ("pb", "PBR")):
            v = xc.get(k)
            if v:
                print("대조 %s: n=%d · 중앙값 %.2f%% · 20%%이내 %.0f%% · 2배초과 %d건"
                      % (lab, v["n"], v["median"], v["w20"], v["gross"]))
    print("항목 커버: " + " ".join("%s%.0f" % (k, summary["cov"][k]) for k in summary["cov"]))
    if UNIT_ERRORS:
        nb = sum(len(b) for _m, b in UNIT_ERRORS)
        top = sorted(((abs(v), d) for _m, b in UNIT_ERRORS for d, v in b), reverse=True)[:3]
        print("주당지표 단위오류 제거: %d관측 · 최대 %s"
              % (nb, " · ".join("%s %g" % (d, v) for v, d in top)))
    if n_pred:
        print("전신 법인에서 재무를 가져온 종목: %d개" % n_pred)
    if FILL_LOG["cells"] or FILL_LOG["refused"]:
        print("태그 빈칸 메우기: %d칸 (%s) · 문턱에 막힘 %s"
              % (FILL_LOG["cells"], " ".join("%s %d" % kv for kv in sorted(FILL_LOG["keys"].items())),
                 " ".join("%s %d" % kv for kv in sorted(FILL_LOG["refused"].items())) or "0"))
    if spl_log:
        print("선행 CIK 잇기 %d종: %s" % (len(spl_log), " · ".join("%s%s" % (t, v) for t, v in sorted(spl_log.items()))))
    if _FETCH["dir"]:
        print("companyfacts: 캐시 %d · SEC %d" % (_FETCH["n_cache"], _FETCH["n_net"]))
    if empty:
        print("⚠ us-gaap 사실 없음 %d사: %s" % (len(empty), ", ".join(t for t, _ in empty[:10])))
    if miss:
        print("⚠ 수집 실패 %d사: %s" % (len(miss), ", ".join(miss[:10])))

    cover = len(got) / max(1, len(uni))
    if cover < 0.90:
        print("❌ 커버 %.1f%% (<90%%) — 수집 실패로 보고 중단" % (cover * 100))
        return 1
    return 0


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "SEC 재무")
