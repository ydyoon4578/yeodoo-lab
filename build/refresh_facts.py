#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEC EDGAR companyfacts(XBRL) → 회사별 재무 시계열

메뉴 정본에서 이 소스 하나에 막혀 있던 세 칸을 겨냥한다:
  co.html#fs          재무제표      기간·제출일이 붙은 분기/연간 시계열
  valuation.html#ddm  DDM          분기별 주당배당금(DPS) 이력이 있어야 성립
  valuation.html#rim  RIM          기초 자기자본·순이익·배당이 맞물려야 성립

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

사용: python3 build/refresh_facts.py
"""
from __future__ import annotations

import datetime as dt
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

FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json"

KEEP_Q = 20      # 분기 관측 보관 수(5년)
KEEP_A = 8       # 연간 관측 보관 수
KEEP_I = 20      # 시점(재무상태표) 관측 보관 수
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
)

# 화면에 그대로 쓰는 항목 이름. 여기 없는 키는 만들지 않는다.
LABEL = {
    "rev": "매출", "cogs": "매출원가", "gp": "매출총이익", "opinc": "영업이익",
    "ni": "순이익", "eps": "주당순이익(희석)", "dps": "주당배당금(선언)",
    "asset": "자산총계", "liab": "부채총계", "eq": "자기자본(지배주주지분)",
    "cash": "현금및현금성자산", "cfo": "영업활동현금흐름", "capex": "설비투자(CAPEX)",
    "sh": "희석주식수", "bb": "자사주 매입", "iss": "주식 발행",
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


def extract(facts: dict):
    """companyfacts → {키: {src, u, s, q/a/i}}. 값이 하나도 없는 항목은 담지 않는다.

    ⚠ 후보 태그는 '먼저 있는 것'이 아니라 **가장 최근까지 보고된 것**을 고른다.
    회사가 도중에 태그를 갈아타면 옛 태그도 값을 그대로 갖고 있어서, 우선순위대로
    집으면 죽은 시계열을 집는다. 실측(2026-07-25): JPM은 Revenues로 고르면 분기가
    2014년에서 멈추고, NVDA도 2020년에서 멈춘다 — 연간은 최신인데 분기만 낡아
    화면에서 알아채기 어려운 형태로 틀린다.

    한 항목 안에서 태그를 섞지는 않는다. 섞으면 정의가 다른 숫자가 한 줄에 들어간다.
    """
    allf = (facts or {}).get("facts") or {}
    gaap = allf.get("us-gaap") or {}
    # us-gaap이 없으면 IFRS로 넘어간다(외국 사기업). 둘을 섞지는 않는다 — 한 회사의
    # 재무제표는 한 회계기준으로 작성된 것이고, 반씩 가져오면 합이 맞지 않는다.
    tagset = TAGS
    if not gaap and allf.get("ifrs-full"):
        gaap, tagset = allf["ifrs-full"], TAGS_IFRS
    out = {}
    for spec in tagset:
        key, cands, unit, scale = spec[0], spec[1], spec[2], spec[3]
        tie = spec[4] if len(spec) > 4 else "count"
        best = None
        for tag in cands:
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
            if best is None or score > best[0]:
                best = (score, tag, q, a, i)
        if not best:
            continue
        _s, tag, q, a, i = best
        # 고른 태그 안에서도 한쪽 구간만 옛날에 멈춰 있을 수 있다(회사가 그 단위 보고를
        # 그만둔 경우). 최신 구간보다 450일 넘게 뒤처진 구간은 버린다 — 없는 것보다
        # 12년 전 숫자를 최신인 양 늘어놓는 쪽이 나쁘다. 450일이면 연간 보고 시차는 넉넉히 통과한다.
        newest = max(s[0][0] for s in (q, a, i) if s)
        rec = {"src": tag, "u": unit, "s": scale}
        dropped = []
        for name, ser in (("q", q), ("a", a), ("i", i)):
            if not ser:
                continue
            if _days(ser[0][0], newest) > 450:
                dropped.append(name)
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
    if out:
        newest_all = max(rec[k][0][0] for rec in out.values()
                         for k in ("q", "a", "i") if rec.get(k))
        dead = [key for key, rec in out.items()
                if _days(max(rec[k][0][0] for k in ("q", "a", "i") if rec.get(k)),
                         newest_all) > 450]
        for key in dead:
            out.pop(key)
    return out


def index_fcf_stat(tickers, mc_by_t):
    """지수 단위 FCF 합계 — valuation.html#index가 읽는다.

    ⚠ 이건 '지수의 FCF'가 아니라 **두 다리가 모두 잡히고 최근 회계연도인 회사들의 합계**다.
    그 사실을 숫자로 같이 내보낸다(커버 종목 수·시총 비중). 실측(2026-07-25):

      · SEC frames API로 직접 합치면 영업현금흐름 488사 대 설비투자 329사로 집합이 어긋난다.
        무시하고 빼면 FCF가 **+80% 부풀려진다**. 교집합만 쓰면 시총 커버가 60%로 떨어진다.
      · 반면 이 수집분은 회사별로 후보 태그 중 살아 있는 것을 골라 뒀기 때문에 두 다리가
        모두 있는 회사가 457사다. 거기서 최근 18개월 안에 끝난 회계연도만 남기면
        **427사 · 시총 87%**가 된다(2018년에 멈춘 회사가 섞이면 합산이 성립하지 않는다).
    """
    cut = (dt.date.today() - dt.timedelta(days=548)).isoformat()   # 약 18개월
    fcf = 0.0
    mc = 0.0
    used, neg = 0, 0
    for t in tickers:
        try:
            d = json.load(io.open(os.path.join(DIR_FX, "%s.json" % t), encoding="utf-8"))
        except Exception:
            continue
        tg = d.get("tags") or {}
        cm = {x: y for x, y in ((tg.get("cfo") or {}).get("a") or [])}
        pm = {x: y for x, y in ((tg.get("capex") or {}).get("a") or [])}
        common = sorted(set(cm) & set(pm), reverse=True)
        if not common or common[0] < cut:
            continue
        v = cm[common[0]] - pm[common[0]]
        m = mc_by_t.get(t)
        if not m:
            continue
        fcf += v
        mc += m
        used += 1
        if v < 0:
            neg += 1
    tot_mc = sum(v for v in mc_by_t.values() if v)
    if not used or not mc:
        return None
    return {"n": used, "n_uni": len(mc_by_t), "n_neg": neg,
            "fcf_musd": round(fcf, 0),                    # 백만 달러
            "mc_cover": round(mc / tot_mc * 100, 1) if tot_mc else None,
            # fund.mc는 억$ 단위다 — 백만$로 맞춰 수익률을 낸다
            "fcfy": round(fcf / (mc * 100) * 100, 3),
            "window_months": 18,
            "note": "지수의 FCF가 아니다. 영업현금흐름과 설비투자가 모두 잡히고 최근 18개월 안에 "
                    "끝난 회계연도가 있는 회사들의 합계다. 커버 종목 수와 시총 비중을 함께 봐야 한다."}


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


def clean_surplus_stat(tickers):
    """장부가 증분이 '이익 − 배당'과 얼마나 어긋나는지 — RIM 전제의 실측.

    두 가지로 잰다:
      naive = ΔBV − (순이익 − 배당)
      full  = ΔBV − (순이익 − 배당 − 자사주매입 + 주식발행)
    분모는 기초 자기자본. 실측(2026-07-25): naive 중앙값 7.9%, full 4.8%.
    자사주 매입이 가장 큰 누락 항목이지만, 넣어도 4곳 중 1곳은 10%를 넘는다.
    """
    naive, full = [], []
    for t in tickers:
        try:
            d = json.load(io.open(os.path.join(DIR_FX, "%s.json" % t), encoding="utf-8"))
        except Exception:
            continue
        T = d.get("tags") or {}

        def ann(k):
            return {x: y for x, y in ((T.get(k) or {}).get("a") or [])}
        eq = {x: y for x, y in ((T.get("eq") or {}).get("i") or [])}
        ni, dps, sh, bb, iss = ann("ni"), ann("dps"), ann("sh"), ann("bb"), ann("iss")
        ds = sorted(set(eq) & set(ni), reverse=True)
        if len(ds) < 2:
            continue
        t1, t0 = ds[0], ds[1]
        base = abs(eq[t0])
        if not base:
            continue
        dbv, earn = eq[t1] - eq[t0], ni[t1]
        div = dps.get(t1, 0) * sh.get(t1, 0) if (t1 in dps and t1 in sh) else 0
        naive.append(abs(dbv - (earn - div)) / base * 100)
        full.append(abs(dbv - (earn - div - bb.get(t1, 0) + iss.get(t1, 0))) / base * 100)
    if not naive:
        return None

    def med(v):
        v = sorted(v)
        n = len(v)
        return round(v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2, 2)

    def within(v, th):
        return round(sum(1 for x in v if x <= th) / len(v) * 100, 1)
    return {"n": len(naive),
            "naive": {"median": med(naive), "w5": within(naive, 5), "w10": within(naive, 10)},
            "full": {"median": med(full), "w5": within(full, 5), "w10": within(full, 10)},
            "note": "장부가 증분이 '이익 − 배당'과 어긋나는 정도(기초 자기자본 대비 %). "
                    "full은 자사주 매입·주식 발행까지 반영한 값. RIM의 전제가 실제로는 성립하지 않는다."}


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
    p = os.path.join(DATA, "industry.json")
    if os.path.exists(p):
        try:
            co = json.load(io.open(p, encoding="utf-8")).get("co") or {}
            m = {t: v[2] for t, v in co.items() if len(v) > 2}
            if m:
                return m, "data/industry.json"
        except Exception:
            pass
    return {k: v for k, v in edgar.ticker_cik_map().items()}, "SEC company_tickers.json"


def main() -> int:
    uni = load_universe()
    mc_by_t = load_mc()
    fund_by_t = load_fund()
    cmap, src = load_cik_map()
    print("티커→CIK 출처: %s (%d개)" % (src, len(cmap)))

    os.makedirs(DIR_FX, exist_ok=True)
    n_new = n_upd = n_same = n_pred = n_ifrs = 0
    cov = {spec[0]: 0 for spec in TAGS}
    got, miss, empty = [], [], []

    for n, (t, name) in enumerate(uni, 1):
        cik = cmap.get(t) or cmap.get(t.upper())
        if not cik:
            miss.append(t)
            continue
        j = edgar.get_json(FACTS_URL % int(cik))
        tags = extract(j) if j else {}
        # 지주회사 전환 직후의 새 법인은 us-gaap 사실이 0개다(XOM 실측). 재무는 전신 법인
        # 아래에 그대로 있으므로 공시 파이프라인과 같은 표를 보고 그쪽에서 가져온다.
        used_pred = 0
        if not tags:
            for pcik in edgar.PREDECESSOR.get(t.upper(), []):
                pj = edgar.get_json(FACTS_URL % int(pcik))
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
        for k in tags:
            cov[k] += 1
        std = "IFRS" if not (((j.get("facts") or {}).get("us-gaap"))) else "us-gaap"
        if std == "IFRS":
            n_ifrs += 1
        doc = {
            "t": t, "cik": int(cik), "nm": j.get("entityName") or name,
            "labels": {k: LABEL[k] for k in tags if k in LABEL},
            "std": std,          # 화면이 '이 표는 IFRS 기준'을 적을 수 있게
            "tags": tags,
        }
        if used_pred:
            # 현행 법인이 아니라 전신 법인의 재무다 — 화면이 그 사실을 적을 수 있게 남긴다
            doc["pred"] = 1
        body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
        fn = os.path.join(DIR_FX, "%s.json" % t.replace("/", "_"))
        old = None
        if os.path.exists(fn):
            try:
                old = io.open(fn, encoding="utf-8").read()
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
        io.open(fn, "w", encoding="utf-8").write(body)
        got.append(t)
        if n % 100 == 0:
            print("  … %d/%d" % (n, len(uni)))

    if not got:
        print("❌ 수집 0건 — 갱신 중단(이전본 유지)")
        return 1

    # 유니버스에서 빠진 종목 파일 정리
    keep = set(got)
    n_del = 0
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
    # 미국 회계에서 이게 실제로 얼마나 맞는지 재서 남긴다 — 안 재고 모형을 켜면
    # 내부적으로 모순된 값을 RIM이라고 부르게 된다.
    cs = clean_surplus_stat(got)
    idx = index_fcf_stat(got, mc_by_t)
    xc = crosscheck_stat(got, mc_by_t, fund_by_t)
    # DDM이 쓸 수 있는 범위 — 연간 주당배당금이 몇 년치나 있는가
    dy = {"n1": 0, "n2": 0, "n4": 0}
    for t in got:
        try:
            d = json.load(io.open(os.path.join(DIR_FX, "%s.json" % t), encoding="utf-8"))
        except Exception:
            continue
        rows = (((d.get("tags") or {}).get("dps") or {}).get("a") or [])
        if rows:
            dy["n1"] += 1
        if len(rows) >= 2:
            dy["n2"] += 1
        if len(rows) >= 4:
            dy["n4"] += 1

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
        "clean_surplus": cs,
        "index_fcf": idx,
        "xcheck": xc,
        "dps_years": dy,
        "limits": [
            "숫자는 회사가 XBRL로 태깅해 제출한 값 그대로다 — 랩이 조정하거나 재분류하지 않는다.",
            "회사마다 쓰는 태그가 달라 같은 줄이라도 출처 태그가 다를 수 있다(각 항목에 태그명을 표기한다).",
            "6·9개월 누적 구간은 분기에서 제외한다. 그래서 분기 항목이 비는 회사가 있다.",
            "외국 사기업은 IFRS(ifrs-full)로 보고한다 — 같은 항목 키에 담되 출처 태그를 표기해 섞였다는 사실을 드러낸다.",
            "재무를 아직 낸 적 없는 신규 등록 법인(분사 직후 등)은 빈 채로 둔다 — 추정치로 채우지 않는다.",
        ],
    }
    io.open(OUT_SUM, "w", encoding="utf-8").write(
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
    if n_pred:
        print("전신 법인에서 재무를 가져온 종목: %d개" % n_pred)
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
    sys.exit(main())
