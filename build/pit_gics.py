# -*- coding: utf-8 -*-
"""build/pit_gics.py — 월말 시점의 S&P 500 GICS 섹터(위키 과거 리비전) → data/pit_gics.json

왜: 랩의 섹터(stocks.json · index_ledger meta)는 **오늘** 분류뿐이다. 금융을 빼는 규칙(Eg 등)이 오늘 분류를
  과거에 덮어쓰면 GICS 개편이 미래 정보가 된다 — 2023-03 결제 처리(IT → 금융) · 2016-09 부동산 분리(금융 → 부동산) ·
  종목별 리츠 편입(AMT 2012 · CCI 2014 · WY 2011) 같은 것들. 적대 검토(PREREG-2026-09-24-EGBEST)가 잡았다.
  편출 종목 섹터와 같은 공개 출처(위키 «List of S&P 500 companies» 과거 리비전의 GICS Sector 열)를 월말마다 읽는다.

무엇을 담나: 월말마다 표에 있던 티커 전부를 «금융» 과 «그 밖» 으로 가르고, 표에 CIK 열이 있으면(2014-06~) CIK 도.
  섹터 이름 전체가 아니라 금융 여부만 싣는다 — 쓰는 곳이 금융 경계뿐이라 파일을 작게 둔다.
한계: 위키 편집 지연(발효일과 며칠~몇 주 어긋날 수 있다) · 표에 없는 회사(NASDAQ 100 전용 · 비멤버)는 쓰는 쪽이
  가장 가까운 달의 분류나 오늘 분류로 메운다. 발효일 정본이 아니라 근사다(index_history.json 과 같은 한계).

  python build/pit_gics.py            # 2009-12 ~ 2023-06 월말 · 약 170 리비전 · 몇 분(위키 예의 PAUSE)
"""
from __future__ import annotations
import io, json, os, sys, time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refresh_index_history as RIH   # noqa: E402  snapshot · month_ends · parse(GICS 열을 값으로 찾는다)

# 옛 표(~2014)는 통신 섹터를 «Telecommunications Services»(s 가 붙은 비표준 표기)로 적었다 — 파서의 닫힌 집합에 없어
#   T·VZ·AMT·CCI 등이 «섹터 없음» 이 되고, 쓰는 쪽이 가까운 달(금융이 된 뒤)로 메우는 오류가 났다. 그 표기를 받아 준다.
RIH.GICS.add("Telecommunications Services")

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "pit_gics.json")
M0, M1 = "2009-12", "2023-06"      # Eg 회귀 첫 달(2010-01)의 직전부터 2023-03 개편 뒤 석 달까지


OUT_SEC = os.path.join(ROOT, "data", "pit_gics_sectors.json")
M0S, M1S = "2014-06", "2026-08"   # --sectors: 업종 전체(EG30+ 의 업종 안 선별 · 업종 폭 · 벤치 업종 비중) — 명단 기록이 서는 달부터


def main_sectors() -> int:
    """--sectors: 월말마다 표의 GICS 섹터 이름 전체를 싣는다(pit_gics.json 은 건드리지 않는다 — EGBEST 가 얼린 판이다)."""
    t0 = time.time()
    months, fails = {}, []
    for ym, iso in RIH.month_ends(M0S, M1S):
        tk, meta = RIH.snapshot("spx", iso)
        if not tk:
            fails.append({"m": ym, "why": str(meta.get("fail"))})
            print("  ✗ %s %s" % (ym, meta.get("fail")))
            continue
        sec = {}
        for t, v in tk.items():
            sec.setdefault(v[2] or "", []).append(t)
        months[ym] = {"rev": meta["rev"], "ts": meta["ts"], "sec": {k: sorted(v) for k, v in sorted(sec.items())},
                      "cik": {t: v[0] for t, v in tk.items() if v[0]}}
        print("  %s rev %s · 섹터 %d · 종목 %d · 섹터 없음 %d" % (ym, meta["rev"], len([k for k in sec if k]), len(tk), len(sec.get("", []))))
    doc = {"note": "월말 S&P 500 표(위키 과거 리비전)의 GICS 섹터 이름 전체(값으로 찾는다 · 비표준 통신 표기 포함). 빈 키 = 섹터 칸이 빈 종목. "
                   "발효일 정본이 아니라 근사 — 위키 편집 지연이 있다. 표에 없는 회사는 쓰는 쪽이 메운다.",
           "source": "en.wikipedia.org «List of S&P 500 companies» (CC BY-SA) — 월마다 리비전 번호를 싣는다",
           "range": [M0S, M1S], "fails": fails, "months": months}
    io.open(OUT_SEC, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s (%d개월 · 실패 %d · %.0f초)" % (OUT_SEC, len(months), len(fails), time.time() - t0))
    return 0 if not fails else 1


def main() -> int:
    if "--sectors" in sys.argv:
        return main_sectors()
    t0 = time.time()
    months, fails = {}, []
    for ym, iso in RIH.month_ends(M0, M1):
        tk, meta = RIH.snapshot("spx", iso)
        if not tk:
            fails.append({"m": ym, "why": str(meta.get("fail"))})
            print("  ✗ %s %s" % (ym, meta.get("fail")))
            continue
        fin = sorted(t for t, v in tk.items() if v[2] == "Financials")
        other = sorted(t for t, v in tk.items() if v[2] and v[2] != "Financials")
        nosec = sorted(t for t, v in tk.items() if not v[2])
        cik = {t: v[0] for t, v in tk.items() if v[0]}
        months[ym] = {"rev": meta["rev"], "ts": meta["ts"], "fin": fin, "other": other, "nosec": nosec, "cik": cik}
        print("  %s rev %s · 금융 %d · 그 밖 %d · 섹터 없음 %d · CIK %d" % (ym, meta["rev"], len(fin), len(other), len(nosec), len(cik)))
    doc = {"note": "월말 S&P 500 표(위키 과거 리비전)의 GICS 금융 여부. 섹터 열을 값으로 찾는다(refresh_index_history.parse). "
                   "발효일 정본이 아니라 근사 — 위키 편집 지연이 있다. 표에 없는 회사는 쓰는 쪽이 메운다.",
           "source": "en.wikipedia.org «List of S&P 500 companies» (CC BY-SA) — 월마다 리비전 번호를 싣는다",
           "range": [M0, M1], "fails": fails, "months": months}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s (%d개월 · 실패 %d · %.0f초)" % (OUT, len(months), len(fails), time.time() - t0))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
