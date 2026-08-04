#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""고객 집중도 이력 수집 → data/cust_conc.json

10-K·20-F 원문에서 **단일 고객 매출 집중도**를 뽑아 제출일과 함께 싣는다.
규약은 build/PREREG-2026-08-04-CUSTCONC.md 에 **수집 전에** 확정해 커밋했다.

── 왜 원문을 긁는가 ────────────────────────────────────────────────────
XBRL 로는 안 된다. 고객 집중은 us-gaap 의 ConcentrationRisk 계열인데 그 값이 **차원**
(MajorCustomersAxis)에 붙고, SEC companyfacts API 는 차원을 걷어내고 준다.
실측(2026-08-04): AAPL·NVDA·AVGO·QCOM·TER 의 companyfacts 에 Concentration 계열 태그 0건.

── 🚨 텍스트 추출은 브리틀하다. 그래서 이렇게 짰다 ──────────────────────
같은 날 B7 링크 스캔에서 두 방향으로 다 틀렸다.
  · 오탐 — 회사명 첫 낱말을 별칭에 자동으로 넣었더니 United Airlines → "United" →
    **"United States"** 를 잡았다(1차 16종 중 11종이 이것).
  · 누락 — 별칭을 "Apple Inc" 로 적어 본문의 "Apple" 을 놓쳤다.
그래서 여기서는 회사 실명을 아예 안 찾는다(집중도 **숫자만** 쓴다). 대신
  ① 뽑은 **문장을 그대로 저장**한다 — 사람이 검산할 수 있어야 한다.
  ② '단일 고객'과 '복수 합산'을 문구로 갈라 **단일만** 신호로 쓴다(규약).
  ③ 100% 초과·0% 같은 불가능한 값은 버린다.

── 시점 정합 ───────────────────────────────────────────────────────────
값은 **제출일(filingDate)** 부터 유효하다. 공시일이 곧 공개일이라 별도 지연이 필요 없다
(재무 태그의 FUND_LAG_DAYS 는 기간말 기준이라 지연이 필요했다 — 여기는 다르다).

사용:
  python3 build/refresh_custconc.py --sample 12   # 표본만 뽑아 문장을 눈으로 검산
  python3 build/refresh_custconc.py               # 전체 수집(재개 가능)
"""
from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "cust_conc.json")
RAW = os.path.join(DATA, "_custconc_raw.json")      # 재개용 중간 저장(gitignore)

SINCE = "2008-01-01"      # 가격 격자가 2009-01 부터라 그 앞은 쓸 데가 없다
FORMS = ("10-K", "20-F", "10-K/A")

# 🚨 '문장'을 마침표로 자르면 안 된다. 재무 원문은 소수점("10.5%")과 약어("U.S.", "Inc.")가
#   널려 있어 [^.] 가 거기서 끊긴다 — 실측(WDC 2025 10-K): customer+revenue 조각 29개가
#   나왔는데 그중 백분율을 포함한 것이 **0개**였다. 잘린 조각에 % 가 안 들어간 것이다.
#   그래서 마침표를 무시하고 customer 낱말 **주변 고정폭 창**을 본다.
CUSTW = re.compile(r"\b(?:customer|client)s?\b", re.I)
WIN = 320                                   # 앞뒤 글자수
# 🚨 % 뒤에 \b 를 붙이면 안 된다 — % 가 비단어 문자라 "88% of" 에서 경계가 성립하지 않는다.
#   실측: 이 한 글자 때문에 WDC 창 52개 중 백분율이 잡힌 것이 **0개**였다.
PCT = re.compile(r"\b(\d{1,3}(?:\.\d)?)\s?(?:%|percent\b)", re.I)
REV = re.compile(r"\b(?:net\s+)?(?:revenue|revenues|sales)\b", re.I)
# 🚨 단일 고객 표지. 규약이 '단일만 쓴다'이므로 이 표지가 없으면 신호로 안 쓴다.
ONE = re.compile(r"\b(?:one|a single|our single|its single|the single|our largest|"
                 r"its largest|the largest|one of our|a customer|customer [A-Z]\b)\b", re.I)
# 복수 합산 표지 — 있으면 단일이 아니다("a group of four customers", "two customers")
MANY = re.compile(r"\b(?:group of|two|three|four|five|six|seven|eight|nine|ten|"
                  r"\d+\s+(?:largest\s+)?customers|customers\s+(?:each\s+)?accounted)\b", re.I)
# 🚨 부정문 — 표본 검산에서 걸렸다. ASC 280 공시 문구는 **없다**고 적는 형태가 매우 흔하다:
#   "The Company does not have revenue from transactions with a single customer amounting to
#    10 percent or more of its revenues" → 이걸 '집중도 10%'로 읽으면 정반대가 된다.
#   실측(2026-08-04 표본 10종): TRV 에서 잡힌 7건이 **전부** 이 형태였다.
NEG = re.compile(r"\b(?:did not|does not|do not|no single|no customer|no one customer|"
                 r"none of|not exceed|less than|fewer than|nor did)\b", re.I)
# 🚨 문턱 문구 — "10 percent or more" 의 10% 는 **공시 기준선**이지 측정된 집중도가 아니다.
THRESH = re.compile(r"\b\d{1,3}(?:\.\d)?\s?(?:%|percent)\s+or\s+(?:more|greater|above)\b", re.I)


def fetch(url: str) -> str:
    edgar._throttle()
    rq = urllib.request.Request(url, headers={"User-Agent": edgar.UA,
                                              "Accept-Encoding": "gzip, deflate"})
    rs = urllib.request.urlopen(rq, timeout=60)
    b = rs.read()
    if rs.headers.get("Content-Encoding") == "gzip":
        b = gzip.GzipFile(fileobj=io.BytesIO(b)).read()
    return b.decode("utf-8", "replace")


def filings(cik: int):
    """그 회사의 10-K·20-F 전부(2008년 이후) — recent + 과거 조각을 합친다.

    ⚠ recent 는 최근 1,000건이라 활발한 회사는 10년도 못 덮는다. files[] 의 과거 조각을
      같이 읽지 않으면 앞 구간이 통째로 빈다(실측 AAPL: recent 가 2015-06 까지만).
    """
    sub = edgar.submissions(cik)
    if not sub:
        return []
    out, f = [], (sub.get("filings") or {})

    def take(d):
        fm = d.get("form") or []
        for i in range(len(fm)):
            if fm[i] in FORMS and (d.get("filingDate") or [""] * len(fm))[i] >= SINCE:
                out.append({"d": d["filingDate"][i],
                            "pe": (d.get("reportDate") or [""] * len(fm))[i],
                            "a": str(d["accessionNumber"][i]).replace("-", ""),
                            "p": (d.get("primaryDocument") or [""] * len(fm))[i]})
    take(f.get("recent") or {})
    for ch in (f.get("files") or []):
        if str(ch.get("filingTo") or "") < SINCE:
            continue                                  # 이 조각은 통째로 창 밖이다
        try:
            take(edgar.get_json("https://data.sec.gov/submissions/" + ch["name"]) or {})
        except Exception:
            pass
    return sorted({(x["d"], x["a"]): x for x in out}.values(), key=lambda x: x["d"])


# 🚨 숫자를 고객 절에 **구문으로 묶는다.** 창 안의 최댓값을 집으면 무관한 수가 달라붙는다 —
#   실측(TER 2026 10-K): 창 방식이 36% 를 냈는데 그 문장의 실제 수치는 12.5% 였다.
#   그래서 '단일 고객 표지 → customer → 서술어 → 백분율' 순서를 강제한다.
#   ⚠ customer(?!s) — 복수는 받지 않는다. 실측(SBAC): "customers comprised 95.4%" 가
#     상위 4사 합계인데 단수로 오인돼 잡혔다.
TIGHT = re.compile(
    r"\b(?:one|a single|our single|the single|our largest|its largest|the largest|"
    r"customer\s+[A-Z]\b)[^%]{0,90}?customer(?!s)[^%]{0,120}?"
    r"(?:accounted for|represented|comprised|was|were|generated|provided)"
    r"[^%]{0,60}?(\d{1,3}(?:\.\d)?)\s?(?:%|percent)", re.I)
TIGHT2 = re.compile(
    r"\bcustomer(?!s)[^%]{0,60}?(?:accounted for|represented|comprised)"
    r"[^%]{0,60}?(\d{1,3}(?:\.\d)?)\s?(?:%|percent)", re.I)


def scan(txt: str):
    """→ (단일고객 최대 %, 뽑은 문장들). 못 찾으면 (None, [])."""
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))
    hits = []
    for rx in (TIGHT, TIGHT2):
        for m in rx.finditer(txt):
            s = m.group(0)
            if NEG.search(s) or THRESH.search(s) or MANY.search(s):
                continue
            v = float(m.group(1))
            if 0 < v <= 100:
                hits.append((v, s[-260:]))
        if hits:
            break                                     # 엄격한 쪽이 잡으면 느슨한 쪽은 안 본다
    if not hits:
        return None, []
    hits.sort(reverse=True)
    return hits[0][0], [h[1] for h in hits[:3]]


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0,
                    help="표본 N종만 훑고 문장을 찍는다(검산용). 저장하지 않는다.")
    ap.add_argument("--pit", action="store_true",
                    help="편출 종목(data/pit_universe.json)만 훑어 같은 파일에 보탠다.")
    a = ap.parse_args()

    cik = (json.load(io.open(os.path.join(DATA, "cik_map.json"), encoding="utf-8")).get("co") or {})
    uni = sorted(t for t, c in cik.items() if c)
    if a.pit:
        # 🚨 PIT 레그가 공정하려면 **편출 종목도** 있어야 한다. 오늘의 518종만 있으면
        #   그 규칙의 후보가 생존자로만 좁혀져, 생존편향을 재려는 표가 오히려 그 편향을 갖는다
        #   (x-volsurge 를 PIT 에서 뺀 것과 같은 사유다).
        pu = json.load(io.open(os.path.join(DATA, "pit_universe.json"), encoding="utf-8"))
        want = sorted(pu.get("tickers") or {})
        cmap = dict(edgar.ticker_cik_map())
        cik = {t: cmap[t] for t in want if t in cmap}
        uni = sorted(cik)
        print("편출 %d종 중 CIK 확인 %d종 — 같은 파일에 보탠다" % (len(want), len(uni)))
    if a.sample:
        # 🚨 표본을 균등 추출하면 공급사가 거의 안 걸린다(1차 표본 10종 중 9종이 0건이었다 —
        #   유틸리티·보험·리츠였다). **참양성도 봐야** 추출기를 검산할 수 있으므로
        #   집중 공시가 있을 법한 쪽을 섞는다.
        SEED = ["WDC", "MRVL", "ALAB", "TTWO", "MCK", "SBAC", "CHD", "TER", "JBL", "FLEX",
                "MPWR", "ON", "GLW", "AVGO", "QCOM", "TRV", "DUK"]
        pick = [t for t in SEED if t in cik][:a.sample]
        rest = [t for t in uni if t not in pick]
        uni = pick + rest[:: max(1, len(rest) // max(1, a.sample // 3))][: max(0, a.sample - len(pick))]
        print("표본 %d종 — 문장을 눈으로 검산한다(저장 안 함)\n" % len(uni))

    res = {}
    if not a.sample and os.path.exists(RAW):
        res = json.load(io.open(RAW, encoding="utf-8"))
    if a.pit:
        res = {k: v for k, v in res.items() if k in uni}   # 편출분만 재개 대상으로 본다
    n_doc = 0
    for k, t in enumerate(uni, 1):
        if t in res:
            continue
        rows = []
        try:
            fl = filings(int(cik[t]))
        except Exception as e:
            res[t] = {"err": str(e)[:50], "rows": []}
            continue
        for f in fl:
            url = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s" % (int(cik[t]), f["a"], f["p"])
            try:
                v, ss = scan(fetch(url))
            except Exception:
                continue
            n_doc += 1
            if v is not None:
                rows.append({"d": f["d"], "pe": f["pe"], "pct": v, "s": ss[0] if ss else ""})
        res[t] = {"rows": rows}
        if a.sample:
            print("%-6s 10-K %2d건 · 집중도 잡힘 %2d건" % (t, len(fl), len(rows)))
            for r in rows[-2:]:
                print("    %s  %5.1f%%  %s" % (r["d"], r["pct"], r["s"][:150]))
        elif k % 20 == 0:
            json.dump(res, io.open(RAW, "w", encoding="utf-8"), ensure_ascii=False)
            print("  … %d/%d종 · 문서 %d건 · 값 있는 종목 %d"
                  % (len(res), len(uni), n_doc, sum(1 for v in res.values() if v.get("rows"))),
                  flush=True)
    if a.sample:
        return 0

    if not a.pit:
        json.dump(res, io.open(RAW, "w", encoding="utf-8"), ensure_ascii=False)
    co = {t: sorted(v["rows"], key=lambda r: r["d"]) for t, v in res.items() if v.get("rows")}
    if a.pit and os.path.exists(OUT):
        old = (json.load(io.open(OUT, encoding="utf-8")).get("co") or {})
        merged = {t: [{"d": r[0], "pct": r[1], "s": r[2] if len(r) > 2 else ""} for r in v]
                  for t, v in old.items()}
        merged.update(co)                                  # 편출분을 보탠다(기존은 그대로)
        co = merged
    n_obs = sum(len(v) for v in co.values())
    doc = {
        "note": ("10-K·20-F 원문에서 뽑은 **단일 고객** 매출 집중도(%). 값은 제출일(d)부터 "
                 "유효하며 다음 10-K 까지 유지된다 — 공시일이 곧 공개일이라 별도 지연이 없다. "
                 "복수 고객 합산 공시는 제외했다(규약: build/PREREG-2026-08-04-CUSTCONC.md). "
                 "s 는 그 값을 뽑은 원문 문장이다 — 사람이 검산할 수 있어야 한다."),
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "since": SINCE, "n_co": len(co), "n": n_obs,
        "co": {t: [[r["d"], r["pct"], r["s"][:200]] for r in v] for t, v in co.items()},
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    print("\n고객 집중도: %d사 · %d관측 · %.0fKB" % (len(co), n_obs, os.path.getsize(OUT) / 1024))
    yrs = {}
    for v in co.values():
        for r in v:
            yrs[r["d"][:4]] = yrs.get(r["d"][:4], 0) + 1
    print("연도별 관측:", " ".join("%s:%d" % (k, yrs[k]) for k in sorted(yrs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
