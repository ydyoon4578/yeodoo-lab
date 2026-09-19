#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build/refresh_facts_ext.py — SEC 재무 태그 **확장분**. 기존 것을 건드리지 않는다.

🚨 왜 따로 만드나. `build/refresh_facts.py` 의 TAGS 에 줄을 더해 다시 돌리면
   `data/fx/*.json` 518개와 `data/facts.json` 이 **통째로 다시 구워진다.** 그건
   게시 산출물이고(co.html#fs 가 읽는다), 중간에 한 회사라도 받다 실패하면 이미
   멀쩡한 자료가 나빠진다. 그래서 **읽기만 하고 새 파일에만 쓴다** —
   `data/fxe/*.json` · `data/facts_ext.json`. 기존 경로는 손대지 않는다.
   (오늘 tech_backtest 를 같은 사유로 중단했다 — 등급 캐시가 없는 클론에서 다시
    구우면 등급 의존 규칙이 입력 없이 덮어써진다. 그 교훈을 그대로 적용한다.)

무엇을 더 받나 — 탐색 풀 카드가 «이 태그가 없어서 못 잰다»고 적어 둔 것들이다.

  sga   판관비                A21 조직자본 · E36 비용규율 · E60 의 영업수익성(OP) 정의
  rnd   연구개발비             E40 R&D 집약도 · B3 혁신효율(일부)
  intexp 이자비용              E60 의 OP 정의(원문 분자에 들어간다)
  tax   법인세비용             E56 세금비용 서프라이즈 — 이 카드의 신호 그 자체
  sti   단기투자자산           🚨 E57 현금보유의 **정의 불일치**를 푼다(원문 분자는 현금+단기투자)
  opex  영업비용              E58 영업 레버리지 — 이 카드의 신호 그 자체
  inv   재고자산              E7 발생액
  ar    매출채권              E7 발생액
  dtl   이연법인세부채         A23 · E60 의 장부자본 정의
  pfd   우선주                A23 · E60 의 장부자본 정의

  python build/refresh_facts_ext.py            전수 수집
  python build/refresh_facts_ext.py --n 20     앞 20사만(연습)
  python build/refresh_facts_ext.py --check    지금 파일 상태만
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edgar                                                     # noqa: E402
import refresh_facts as RF                                       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_FXE = os.path.join(DATA, "fxe")
OUT = os.path.join(DATA, "facts_ext.json")
FACTS_URL = RF.FACTS_URL

# ⚠ 후보 태그 순서는 뜻이 없다 — extract() 가 «가장 최근까지 보고된 태그» 를 고른다.
#   한 항목 안에서 태그를 섞지 않는 것도 그쪽 규약 그대로다.
TAGS_EXT = (
    ("sga",    ("SellingGeneralAndAdministrativeExpense",
                "GeneralAndAdministrativeExpense",
                "SellingGeneralAndAdministrativeExpenses"), "USD", "m", "max"),
    ("rnd",    ("ResearchAndDevelopmentExpense",
                "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"), "USD", "m"),
    ("intexp", ("InterestExpense", "InterestExpenseNonoperating",
                "InterestIncomeExpenseNet", "InterestExpenseDebt"), "USD", "m", "max"),
    ("tax",    ("IncomeTaxExpenseBenefit",
                "CurrentIncomeTaxExpenseBenefit"), "USD", "m"),
    # 🚨 E57 카드가 지목한 구멍. 원문(Compustat CHEQ)의 분자는 현금 + 단기투자다.
    #   이 저장소에는 cash(현금) 하나뿐이라 애플 같은 회사가 통째로 눌려 있었다.
    ("sti",    ("ShortTermInvestments", "OtherShortTermInvestments",
                "MarketableSecuritiesCurrent",
                "AvailableForSaleSecuritiesDebtSecuritiesCurrent"), "USD", "m", "max"),
    ("opex",   ("OperatingExpenses", "CostsAndExpenses",
                "OperatingCostsAndExpenses"), "USD", "m", "max"),
    ("inv",    ("InventoryNet",), "USD", "m"),
    ("ar",     ("AccountsReceivableNetCurrent", "ReceivablesNetCurrent"), "USD", "m"),
    ("dtl",    ("DeferredIncomeTaxLiabilitiesNet",
                "DeferredTaxLiabilitiesNoncurrent",
                "DeferredIncomeTaxesAndTaxCredits"), "USD", "m"),
    ("pfd",    ("PreferredStockValue", "PreferredStockValueOutstanding"), "USD", "m"),
)
LABEL_EXT = {"sga": "판매관리비", "rnd": "연구개발비", "intexp": "이자비용",
             "tax": "법인세비용", "sti": "단기투자자산", "opex": "영업비용",
             "inv": "재고자산", "ar": "매출채권", "dtl": "이연법인세부채", "pfd": "우선주"}
OPENS = {"sga": "A21 조직자본 · E36 비용규율 · E60 OP정의", "rnd": "E40 R&D · B3 혁신효율",
         "intexp": "E60 OP정의", "tax": "E56 세금비용 서프라이즈", "sti": "E57 현금보유(정의 교정)",
         "opex": "E58 영업 레버리지", "inv": "E7 발생액", "ar": "E7 발생액",
         "dtl": "A23·E60 장부자본", "pfd": "A23·E60 장부자본"}


def main() -> int:
    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            print("❌ %s 없음" % OUT); return 1
        d = json.load(io.open(OUT, encoding="utf-8"))
        print("facts_ext — %s · %d사 수집" % (d["generated"][:10], d["n_co"]))
        print("   %-8s %-10s %7s  %s" % ("키", "이름", "커버", "여는 카드"))
        for k, v in d["cov"].items():
            print("   %-8s %-10s %6.1f%%  %s" % (k, LABEL_EXT[k], v, OPENS[k]))
        return 0

    lim = None
    if "--n" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--n") + 1])

    uni = RF.load_universe()
    if lim:
        uni = uni[:lim]
    cmap, src = RF.load_cik_map()
    print("티커→CIK 출처: %s (%d개) · 대상 %d사" % (src, len(cmap), len(uni)))
    print("🚨 기존 data/fx/ · data/facts.json 은 읽지도 쓰지도 않는다.\n")

    # extract() 는 모듈 전역 TAGS 를 본다 — 확장 태그로 바꿔 끼운다.
    # ⚠ 원본을 되돌려 놓는다. 같은 프로세스에서 refresh_facts 를 또 쓰면 오염된다.
    old_tags, old_ifrs = RF.TAGS, RF.TAGS_IFRS
    RF.TAGS, RF.TAGS_IFRS = TAGS_EXT, ()          # IFRS 는 이번에 안 건드린다
    os.makedirs(DIR_FXE, exist_ok=True)
    cov = {s[0]: 0 for s in TAGS_EXT}
    got, miss, empty, ifrs_skip = [], [], [], []
    try:
        for n, (t, name) in enumerate(uni, 1):
            cik = cmap.get(t) or cmap.get(t.upper())
            if not cik:
                miss.append(t); continue
            j = edgar.get_json(FACTS_URL % int(cik))
            if not j:
                miss.append(t); continue
            if not ((j.get("facts") or {}).get("us-gaap")):
                ifrs_skip.append(t); continue     # IFRS 사는 태그명이 달라 이번엔 건너뛴다
            tags = RF.extract(j)
            if not tags:
                empty.append(t); continue
            for k in tags:
                cov[k] += 1
            io.open(os.path.join(DIR_FXE, "%s.json" % t), "w", encoding="utf-8").write(
                json.dumps({"t": t, "cik": int(cik), "nm": j.get("entityName") or name,
                            "labels": {k: LABEL_EXT[k] for k in tags},
                            "tags": tags}, ensure_ascii=False) + "\n")
            got.append(t)
            if n % 50 == 0 or n == len(uni):
                print("   %4d/%d  수집 %d · 없음 %d · IFRS 건너뜀 %d"
                      % (n, len(uni), len(got), len(empty), len(ifrs_skip)))
    finally:
        RF.TAGS, RF.TAGS_IFRS = old_tags, old_ifrs

    N = max(1, len(got))
    doc = {"note": "SEC 재무 태그 확장분. build/refresh_facts.py 의 22태그를 덮지 않고 "
                   "별도 파일로 둔다 — 그쪽은 게시 산출물이라 다시 굽지 않는다.",
           "generated": dt.datetime.now().isoformat(timespec="seconds"),
           "n_co": len(got), "n_uni": len(uni),
           "labels": LABEL_EXT, "opens": OPENS,
           "cov": {k: round(v / N * 100, 1) for k, v in cov.items()},
           "miss": miss, "empty": empty, "ifrs_skipped": ifrs_skip,
           "limits": ["IFRS 사는 건너뛴다 — 태그명이 달라 대응표가 따로 필요하다.",
                      "커버리지는 «수집된 회사» 기준이다(분모 %d사)." % len(got)]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("\n■ 커버리지 (분모 %d사)" % len(got))
    print("   %-8s %-10s %7s  %s" % ("키", "이름", "커버", "여는 카드"))
    for k, v in cov.items():
        print("   %-8s %-10s %6.1f%%  %s" % (k, LABEL_EXT[k], v / N * 100, OPENS[k]))
    print("\n→ %s · %s (%d파일)" % (OUT, DIR_FXE, len(got)))
    if ifrs_skip:
        print("   IFRS 건너뜀 %d사: %s" % (len(ifrs_skip), ", ".join(ifrs_skip[:10])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
