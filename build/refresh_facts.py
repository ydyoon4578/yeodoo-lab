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
# (키, 후보 태그들, 단위, 스케일)  스케일 m=백만 단위로 환산, r=원값 유지
TAGS = (
    ("rev",   ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
               "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"), "USD", "m"),
    ("cogs",  ("CostOfGoodsAndServicesSold", "CostOfRevenue"), "USD", "m"),
    ("gp",    ("GrossProfit",), "USD", "m"),
    ("opinc", ("OperatingIncomeLoss",), "USD", "m"),
    ("ni",    ("NetIncomeLoss", "ProfitLoss"), "USD", "m"),
    ("eps",   ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted",
               "EarningsPerShareBasic"), "USD/shares", "r"),
    ("dps",   ("CommonStockDividendsPerShareDeclared",
               "CommonStockDividendsPerShareCashPaid"), "USD/shares", "r"),
    ("asset", ("Assets",), "USD", "m"),
    ("liab",  ("Liabilities",), "USD", "m"),
    ("eq",    ("StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"), "USD", "m"),
    ("cash",  ("CashAndCashEquivalentsAtCarryingValue",), "USD", "m"),
    ("cfo",   ("NetCashProvidedByUsedInOperatingActivities",
               "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"), "USD", "m"),
    ("capex", ("PaymentsToAcquirePropertyPlantAndEquipment",
               "PaymentsToAcquireProductiveAssets"), "USD", "m"),
    ("sh",    ("WeightedAverageNumberOfDilutedSharesOutstanding",
               "WeightedAverageNumberOfSharesOutstandingBasic"), "shares", "m"),
)
# 화면에 그대로 쓰는 항목 이름. 여기 없는 키는 만들지 않는다.
LABEL = {
    "rev": "매출", "cogs": "매출원가", "gp": "매출총이익", "opinc": "영업이익",
    "ni": "순이익", "eps": "주당순이익(희석)", "dps": "주당배당금(선언)",
    "asset": "자산총계", "liab": "부채총계", "eq": "자기자본",
    "cash": "현금및현금성자산", "cfo": "영업활동현금흐름", "capex": "설비투자(CAPEX)",
    "sh": "희석주식수",
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


def extract(facts: dict):
    """companyfacts → {키: {src, u, s, q/a/i}}. 값이 하나도 없는 항목은 담지 않는다."""
    gaap = ((facts or {}).get("facts") or {}).get("us-gaap") or {}
    out = {}
    for key, cands, unit, scale in TAGS:
        for tag in cands:
            node = gaap.get(tag)
            if not node:
                continue
            vals = (node.get("units") or {}).get(unit)
            if not vals:
                continue
            q, a, i = pick(vals, scale)
            if not (q or a or i):
                continue
            rec = {"src": tag, "u": unit, "s": scale}
            if q:
                rec["q"] = q
            if a:
                rec["a"] = a
            if i:
                rec["i"] = i
            out[key] = rec
            break      # 첫 성공 태그만 쓴다 — 섞으면 정의가 다른 숫자가 한 줄에 들어간다
    return out


def load_universe():
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        d = json.load(f)
    return [(s["t"], s.get("name") or "") for s in d["stocks"]]


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
    cmap, src = load_cik_map()
    print("티커→CIK 출처: %s (%d개)" % (src, len(cmap)))

    os.makedirs(DIR_FX, exist_ok=True)
    n_new = n_upd = n_same = 0
    cov = {k: 0 for k, _c, _u, _s in TAGS}
    got, miss, empty = [], [], []

    for n, (t, name) in enumerate(uni, 1):
        cik = cmap.get(t) or cmap.get(t.upper())
        if not cik:
            miss.append(t)
            continue
        j = edgar.get_json(FACTS_URL % int(cik))
        if not j:
            miss.append(t)
            continue
        tags = extract(j)
        if not tags:
            # us-gaap 사실이 아예 없는 회사가 실제로 있다 — 지주회사 전환 직후의 새 법인 등.
            # 빈 파일을 만들지 않고 목록에만 남긴다(화면은 '없음'을 사유와 함께 적는다).
            empty.append((t, j.get("entityName") or name))
            continue
        for k in tags:
            cov[k] += 1
        doc = {
            "t": t, "cik": int(cik), "nm": j.get("entityName") or name,
            "labels": {k: LABEL[k] for k in tags if k in LABEL},
            "tags": tags,
        }
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
    last = ""
    for t in got[:80]:
        try:
            d = json.load(io.open(os.path.join(DIR_FX, "%s.json" % t), encoding="utf-8"))
        except Exception:
            continue
        for rec in d["tags"].values():
            for k in ("q", "a", "i"):
                if rec.get(k) and rec[k][0][0] > last:
                    last = rec[k][0][0]

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
        "limits": [
            "숫자는 회사가 XBRL로 태깅해 제출한 값 그대로다 — 랩이 조정하거나 재분류하지 않는다.",
            "회사마다 쓰는 태그가 달라 같은 줄이라도 출처 태그가 다를 수 있다(각 항목에 태그명을 표기한다).",
            "6·9개월 누적 구간은 분기에서 제외한다. 그래서 분기 항목이 비는 회사가 있다.",
            "us-gaap 사실이 없는 회사가 있다(지주회사 전환 직후의 새 등록 법인 등) — 그 종목은 빈 채로 둔다.",
        ],
    }
    io.open(OUT_SUM, "w", encoding="utf-8").write(
        json.dumps(summary, ensure_ascii=False, separators=(",", ":")) + "\n")

    sz = sum(os.path.getsize(os.path.join(DIR_FX, f)) for f in os.listdir(DIR_FX)) / 1024
    print("재무 시계열: %d/%d사 · %.1fMB (평균 %.1fKB) — 신규 %d · 변경 %d · 동일 %d · 삭제 %d"
          % (len(got), len(uni), sz / 1024, sz / max(1, len(got)), n_new, n_upd, n_same, n_del))
    print("기준일(최근 관측 기간말): %s" % (last or "—"))
    print("항목 커버: " + " ".join("%s%.0f" % (k, summary["cov"][k]) for k in summary["cov"]))
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
