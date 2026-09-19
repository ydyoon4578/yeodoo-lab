#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build/refresh_facts_ext_pit.py — 편출 종목의 재무 확장 태그. 시점정확 다리용.

`refresh_facts_ext.py` 는 **오늘의 518종**만 받는다. 그걸로 만든 측정은 전부 소급이고
생존편향이 들어간다 — 이 랩에서 그 편향이 규칙을 죽인 전례가 많다(E33 듀폰:
소급 t 3.61 → 시점정확 2.05).

여기서는 **지금은 지수에 없지만 과거에 있었던 종목**의 같은 태그를 받는다.
대상은 `data/index_history.json`(위키 과거 리비전 · 2014-06~)에 나오는 SPX 편입 이력
797종 중 오늘 패널에 없고 **`data/pit_px.json` 에 가격이 있는** 128종이다.

  가격 없는 편출 종목(166종)은 어차피 수익을 못 만들어 이번 대상이 아니다.
  그래서 이 다리는 **`partial`** 이다 — 편출 294종 중 128종(44%)만 덮는다.

🚨 기존 파일을 건드리지 않는다. `data/fxe_pit/*.json` 에만 쓴다.

  python build/refresh_facts_ext_pit.py
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
from refresh_facts_ext import TAGS_EXT, LABEL_EXT                # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR = os.path.join(DATA, "fxe_pit")
OUT = os.path.join(DATA, "facts_ext_pit.json")


def targets():
    h = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    cur = {s["t"] for s in json.load(io.open(os.path.join(DATA, "stocks.json"),
                                             encoding="utf-8"))["stocks"]}
    px = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))["px"]
    allt = set()
    for _m, v in h["months"].items():
        if isinstance(v, dict) and isinstance(v.get("spx"), list):
            allt |= set(v["spx"])
    cik = h.get("cik") or {}
    gone = allt - cur
    tgt = sorted(t for t in gone if t in px and cik.get(t))
    return tgt, cik, len(gone)


def main() -> int:
    tgt, cik, n_gone = targets()
    print("SPX 편입 이력 중 오늘 패널에 없는 종목 %d · 그중 가격 있는 것 %d (%.0f%%)"
          % (n_gone, len(tgt), len(tgt) / n_gone * 100))
    print("🚨 기존 data/fx · fxe · facts*.json 은 건드리지 않는다.\n")

    old_t, old_i = RF.TAGS, RF.TAGS_IFRS
    RF.TAGS, RF.TAGS_IFRS = TAGS_EXT, ()
    os.makedirs(DIR, exist_ok=True)
    cov = {s[0]: 0 for s in TAGS_EXT}
    got, miss, empty = [], [], []
    try:
        for n, t in enumerate(tgt, 1):
            c = cik.get(t)
            try:
                c = int(str(c).lstrip("0") or 0)
            except Exception:
                miss.append(t); continue
            if not c:
                miss.append(t); continue
            j = edgar.get_json(RF.FACTS_URL % c)
            if not j or not ((j.get("facts") or {}).get("us-gaap")):
                miss.append(t); continue
            tags = RF.extract(j)
            if not tags:
                empty.append(t); continue
            for k in tags:
                cov[k] += 1
            io.open(os.path.join(DIR, "%s.json" % t), "w", encoding="utf-8").write(
                json.dumps({"t": t, "cik": c, "nm": j.get("entityName") or t,
                            "labels": {k: LABEL_EXT[k] for k in tags},
                            "tags": tags}, ensure_ascii=False) + "\n")
            got.append(t)
            if n % 25 == 0 or n == len(tgt):
                print("   %3d/%d  수집 %d · 못 받음 %d" % (n, len(tgt), len(got), len(miss)))
    finally:
        RF.TAGS, RF.TAGS_IFRS = old_t, old_i

    N = max(1, len(got))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"note": "편출 종목의 재무 확장 태그. 시점정확 다리용 — 이 다리는 partial 이다"
                 "(편출 %d종 중 %d종만 덮는다)." % (n_gone, len(got)),
         "generated": dt.datetime.now().isoformat(timespec="seconds"),
         "n_co": len(got), "n_target": len(tgt), "n_gone": n_gone,
         "pit_kind": "partial", "coverage_of_gone": round(len(got) / n_gone * 100, 1),
         "labels": LABEL_EXT,
         "cov": {k: round(v / N * 100, 1) for k, v in cov.items()},
         "miss": miss, "empty": empty}, ensure_ascii=False, indent=1) + "\n")

    print("\n■ 커버리지 (분모 %d사)" % len(got))
    for k, v in cov.items():
        print("   %-8s %-10s %6.1f%%" % (k, LABEL_EXT[k], v / N * 100))
    print("\n→ %s · %s (%d파일) · 편출 커버 %.0f%%"
          % (OUT, DIR, len(got), len(got) / n_gone * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
