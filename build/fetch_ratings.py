# -*- coding: utf-8 -*-
"""애널리스트 등급 변경 이력을 유니버스 전체로 받아 캐시한다(yfinance).

캐시 위치는 data/_ratings_cache.json — 밑줄 접두는 이 저장소에서 **로컬 전용 캐시**를
뜻한다(_pit_px_cache · _pit_hl_cache 와 같은 급). 재현 가능하고 수 MB라 커밋하지 않는다.

담는 것 — 종목별로 [일자, FromGrade점수, ToGrade점수, 액션코드, 목표주가전, 목표주가후, 증권사번호].
  일자는 1970-01-01 로부터의 일수(정수). 문자열 날짜로 두면 파일이 두 배가 된다.
  증권사도 번호로 담는다(이름표는 firms 에 한 벌만) — 같은 이유다.

  🚨 증권사를 담는 이유 — 신호를 '올린 건수 ÷ 커버 수'로 만들면 분모가 작은 종목이 위로
    몰린다(실측: 상위 10의 70%가 커버 최하위 25%. 중립은 25%다. 최소 커버 문턱을 24까지
    올려도 40~50%로 안 내려온다 — 왼쪽 꼬리를 잘라도 남은 표본 안에 같은 기울기가 산다).
    대신 **증권사별 최신 등급을 이어 붙여 컨센서스 평균을 만들고 그 변화**를 본다.
    그러려면 어느 건이 어느 증권사 것인지 알아야 한다.

🚨 등급 어휘 매핑은 **결과를 보기 전에** 정한다. 브로커마다 말이 달라(Buy/Overweight/
  Outperform/Sector Perform…) 5→1 척도로 옮겨야 하는데, 수익률을 본 뒤에 'Sector Perform
  을 3이 아니라 2로 볼까'를 만지면 그 검정은 무효다. 그래서 아래 표를 여기 박아 두고
  사전등록 문서가 이 표를 그대로 인용한다.

  실측 어휘는 36가지였다(60종목 표본 · build/probe_ratings.py). 전부 아래에 있다.
  ⚠ 표에 없는 말이 새로 오면 None 이 되고, 그 건은 점수차를 못 만든다 — 조용히 3(중립)으로
    떨어뜨리지 않는다. 모르는 것을 중립이라 부르면 그건 자료가 아니라 추측이다.

⚠ 이 자료의 한계 — GradeDate 는 발표일이라 t+2 진입이면 선견은 없다. 그러나 (1) yfinance 가
  과거 행을 소급 수정하는지 알 수 없고, (2) 지금 상장된 종목만 나오므로 생존편향이 있다.
  이 랩의 다른 종목 규칙과 같은 한계이고, PIT 레그로 따로 재는 것이 규약이다.
"""
import io
import json
import os
import sys
import time
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
warnings.filterwarnings("ignore")

from refresh_stocks import _yf_sym          # 클래스주 티커 변환(BRK.B → BRK-B)을 다시 구현하지 않는다

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "_ratings_cache.json")

# ── 등급 → 5점 척도 (5 = 가장 강한 매수) ───────────────────────────────
#   I/B/E/S 관행을 따른다. 실측 36어휘를 모두 덮는다.
GRADE = {
    # 5 — 최상위 매수
    "strong buy": 5, "conviction buy": 5, "top pick": 5, "action list buy": 5,
    # 4 — 매수
    "buy": 4, "overweight": 4, "outperform": 4, "positive": 4, "accumulate": 4,
    "market outperform": 4, "sector outperform": 4, "long-term buy": 4,
    "gradually accumulate": 4, "above average": 4, "add": 4, "speculative buy": 4,
    "outperformer": 4, "sector perform - outperform": 4,
    # 3 — 중립
    "neutral": 3, "hold": 3, "equal-weight": 3, "equalweight": 3, "equal weight": 3,
    "market perform": 3, "sector perform": 3, "sector performer": 3,
    "in-line": 3, "peer perform": 3,
    "perform": 3, "sector weight": 3, "market weight": 3, "mixed": 3,
    "fair value": 3, "average": 3, "hold neutral": 3, "market neutral": 3,
    # 2 — 비중축소
    "underweight": 2, "underperform": 2, "reduce": 2, "negative": 2, "cautious": 2,
    "sector underperform": 2, "market underperform": 2, "underperformer": 2,
    "trim": 2, "below average": 2,          # 2026-08-10 추가 — 전체 유니버스에서 처음 나왔다

    # 1 — 매도
    "sell": 1, "strong sell": 1,
}
ACT = {"up": 1, "down": 2, "init": 3, "main": 4, "reit": 5}
EPOCH = None


def gscore(g):
    """등급 문자열 → 1..5. 모르면 None(중립으로 떨어뜨리지 않는다)."""
    s = str(g or "").strip().lower()
    if not s or s in ("nan", "none"):
        return None
    return GRADE.get(s)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="상위 N종목만(시험용)")
    a = ap.parse_args()

    import datetime as dt
    import yfinance as yf
    ep = dt.date(1970, 1, 1)

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    tick = [s["t"] for s in st["stocks"]]
    if a.limit:
        tick = tick[:a.limit]

    out, unknown, fail = {}, {}, []
    firms, fidx = [], {}                      # 증권사 이름표 한 벌 + 번호 대조표
    t0 = time.time()
    for i, t in enumerate(tick):
        try:
            ud = yf.Ticker(_yf_sym(t)).upgrades_downgrades
        except Exception:
            ud = None
        if ud is None or len(ud) == 0:
            fail.append(t)
            continue
        rows = []
        cols = ud.columns
        has_pt = ("currentPriceTarget" in cols) and ("priorPriceTarget" in cols)
        for ix, r in ud.iterrows():
            try:
                d = (ix.date() - ep).days
            except Exception:
                continue
            fs, ts = gscore(r.get("FromGrade")), gscore(r.get("ToGrade"))
            for raw in (r.get("FromGrade"), r.get("ToGrade")):
                s = str(raw or "").strip()
                if s and s.lower() not in ("nan", "none") and gscore(s) is None:
                    unknown[s] = unknown.get(s, 0) + 1
            act = ACT.get(str(r.get("Action") or "").strip().lower(), 0)
            pt0 = pt1 = None
            if has_pt:
                try:
                    v = float(r.get("priorPriceTarget"));  pt0 = v if v == v and v > 0 else None
                except Exception:
                    pass
                try:
                    v = float(r.get("currentPriceTarget")); pt1 = v if v == v and v > 0 else None
                except Exception:
                    pass
            fm = str(r.get("Firm") or "").strip()
            if fm not in fidx:
                fidx[fm] = len(firms)
                firms.append(fm)
            rows.append([d, fs, ts, act, pt0, pt1, fidx[fm]])
        rows.sort(key=lambda x: x[0])
        out[t] = rows
        if (i + 1) % 50 == 0:
            print("  … %d/%d (%.0fs)" % (i + 1, len(tick), time.time() - t0))

    n_ev = sum(len(v) for v in out.values())
    print()
    print("받음 — %d/%d 종목 · %d건" % (len(out), len(tick), n_ev))
    if fail:
        print("이력 없음 %d종: %s" % (len(fail), " ".join(fail[:20]) + (" …" if len(fail) > 20 else "")))
    if unknown:
        # 🚨 조용히 넘기지 않는다. 매핑에 없는 말이 나오면 표를 고쳐야 한다 —
        #   단, 그 수정은 **결과를 보기 전에** 끝나야 한다.
        print("⚠ 매핑에 없는 등급 %d가지: %s" % (len(unknown), unknown))
    print("증권사 %d곳" % len(firms))
    json.dump({"grade_scale": GRADE, "act": ACT, "fail": fail, "firms": firms,
               "unknown": unknown, "rows": out},
              io.open(CACHE, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print("→ %s (%.1fMB)" % (CACHE, os.path.getsize(CACHE) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
