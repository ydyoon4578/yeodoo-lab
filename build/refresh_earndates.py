# -*- coding: utf-8 -*-
"""build/refresh_earndates.py — 실적발표일(8-K Item 2.02 접수일) → data/earn_dates.json

## 왜 있나 (2026-08-19)

  실적발표 반응 드리프트(PEAD)를 재려면 **발표일**이 필요하다. 랩의 실적 캘린더
  (data/earnings.json·Finnhub)는 앞으로의 일정이라 과거가 없고, yfinance 추정치 이력은
  생존자만 준다(x-revdrift 가 그 사유로 막혔다).

  🚨 8-K Item 2.02(실적 공시)의 EDGAR **접수일**은 다르다 — 접수 순간 도장이 찍히는
    시점정확 기록이고, 벤더가 소급하지 않으며, 상장폐지된 회사 것도 CIK 로 그대로 있다.
    이 랩이 원하는 성질을 전부 갖춘 드문 원천이다.

## 무엇을 하나

  지수 이력에 든 적 있는 전 종목(CIK 795)의 8-K 제출 목록에서 Item 2.02 가 든 것의
  접수일을 모은다. recent(최근 1,000건)만으로는 활발한 회사가 10년을 못 덮으므로
  files[] 과거 조각도 읽는다(refresh_13f_history 와 같은 패턴).

  ⚠ 접수일은 «발표일» 의 대리다. 대부분 발표 당일 또는 다음날 접수된다 — 하루의
    오차는 있을 수 있고, 쓰는 쪽(pead_backtest)이 그 사실을 창 설계에 반영한다.

    python build/refresh_earndates.py
"""
from __future__ import annotations
import io
import json
import os
import sys
import time
import urllib.request

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "earn_dates.json")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edgar  # noqa: E402

SINCE = "2008-01-01"


def eightk_dates(cik: int):
    """그 회사의 8-K(Item 2.02 포함) 접수일 전부 — recent + 과거 조각."""
    sub = edgar.submissions(cik)
    if not sub:
        return []
    out = []

    def take(d):
        fm = d.get("form") or []
        fd = d.get("filingDate") or [""] * len(fm)
        it = d.get("items") or [""] * len(fm)
        for i in range(len(fm)):
            if fm[i] in ("8-K", "8-K/A") and "2.02" in (it[i] or "") and fd[i] >= SINCE:
                out.append(fd[i])

    f = sub.get("filings") or {}
    take(f.get("recent") or {})
    for extra in f.get("files") or []:
        nm = extra.get("name")
        if not nm:
            continue
        try:
            d = edgar.get_json("https://data.sec.gov/submissions/" + nm)
            take(d)
        except Exception:
            pass
    return sorted(set(out))


def main() -> int:
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    cik = {t: int(c) for t, c in (H.get("cik") or {}).items() if c}
    print("대상 %d종(지수 이력 전 종목·CIK 확인분)" % len(cik))
    res = {}
    if os.path.exists(OUT):
        res = (json.load(io.open(OUT, encoding="utf-8")) or {}).get("co") or {}
    n_new = 0
    for k, (t, c) in enumerate(sorted(cik.items()), 1):
        if t in res:
            continue                       # 재개 — 이미 받은 종목은 건너뛴다
        try:
            res[t] = eightk_dates(c)
            n_new += 1
        except Exception as e:
            print("  ❌ %-6s %s" % (t, str(e)[:60]))
        if k % 50 == 0:
            io.open(OUT, "w", encoding="utf-8", newline="").write(json.dumps(
                {"co": res}, ensure_ascii=False, separators=(",", ":")) + chr(10))
            print("  … %d/%d종 · 새로 %d" % (k, len(cik), n_new), flush=True)
    n_ev = sum(len(v) for v in res.values())
    doc = {
        "note": "실적발표일 대리 — 8-K Item 2.02 의 EDGAR 접수일. 접수 순간 도장이 찍히는 "
                "시점정확 기록이라 벤더 소급이 없고, 상장폐지된 회사 것도 CIK 로 남아 있다. "
                "⚠ 접수일은 발표 당일 또는 다음날일 수 있다 — 쓰는 쪽이 창 설계에 반영할 것.",
        "source": "SEC EDGAR submissions API", "since": SINCE,
        "n_co": len(res), "n": n_ev, "co": res,
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s · %d종 · 발표일 %d건 · %.0fKB"
          % (os.path.relpath(OUT, ROOT), len(res), n_ev, os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
