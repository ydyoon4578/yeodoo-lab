# -*- coding: utf-8 -*-
"""data/bench_ohlc.json — 지수 OHLCV 얇은 계열(^GSPC · ^NDX).

왜 있나. `bench_px.json` 은 **종가만** 담는다(assets.json 에서 잘라낸다). 그래서
교과서 TA 신호 37종 중 고가·저가·거래량이 필요한 23종을 못 냈다. 그 23종을 내려고
여기서만 따로 받는다.

🚨 **`bench_px.json` 을 대체하지 않는다.** 화면·전략이 읽는 벤치마크는 그쪽이 정본이다.
  이 파일은 `build/ta_signals.py` 하나만 읽는다. 두 계열이 생기는 순간 «어느 종가냐»가
  갈리므로, 아래에서 **종가를 대조하고 어긋나면 갱신을 멈춘다.**

⚠ 가격지수(PR)다. bench_px 와 같은 티커·같은 잣대여야 한다 — SPY·QQQ(TR)를 넣지 않는다
  (2026-08-13 사용자 결정으로 이 랩 벤치마크는 전부 지수 PR 이다).
⚠ `auto_adjust=False` — 지수라 배당조정이 없지만, 원본 ta_lab 과 같은 호출을 쓴다.

  python build/bench_ohlc.py
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
REF = os.path.join(DATA, "bench_px.json")
OUT = os.path.join(DATA, "bench_ohlc.json")

WANT = [("^GSPC", "S&P 500", "spx"), ("^NDX", "NASDAQ 100", "ndx")]
START = "2014-01-01"      # 10년 창(2016-09~) + 넉넉한 워밍업. 더 길게 받아 파일을 불리지 않는다
MAX_GAP = 0.005           # 종가 대조 허용 오차(%) — 이보다 벌어지면 멈춘다


def main() -> int:
    try:
        import pandas as pd
        import yfinance as yf
    except Exception as e:
        print("❌ pandas·yfinance 가 필요하다 — %s" % e)
        return 1

    ref = json.load(io.open(REF, encoding="utf-8")) if os.path.exists(REF) else None
    out = {"note": "지수 OHLCV 얇은 계열. bench_px.json(종가 정본)을 **대체하지 않는다** — "
                   "고가·저가·거래량이 필요한 TA 지표를 내려고 build/ta_signals.py 만 읽는다.",
           "source": "yfinance · auto_adjust=False", "basis": "가격지수(PR)",
           "start": START, "series": {}}
    worst = 0.0

    for tk, label, key in WANT:
        d = yf.download(tk, start=START, progress=False, auto_adjust=False)
        if isinstance(d.columns, pd.MultiIndex):
            d = d.droplevel(1, axis=1)
        d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
        if len(d) < 1000:
            print("❌ %s 행이 %d 뿐이다 — 갱신 중단(이전본 유지)" % (tk, len(d)))
            return 1

        # 🚨 종가 대조. bench_px 와 어긋나면 두 잣대가 생긴 것이므로 **멈춘다.**
        if ref:
            rp = dict(zip(ref["dates"], ref["series"][key]["px"]))
            gaps = []
            for ds, cv in zip(d.index.strftime("%Y-%m-%d"), d["close"].to_numpy()):
                b = rp.get(ds)
                if b:
                    gaps.append(abs(cv / b - 1) * 100)
            if gaps:
                g = max(gaps)
                worst = max(worst, g)
                if g > MAX_GAP:
                    print("❌ %s 종가가 bench_px 와 최대 %.4f%% 어긋난다(허용 %.3f%%) — "
                          "갱신 중단. 두 잣대를 만들지 않는다." % (tk, g, MAX_GAP))
                    return 1
                print("   %s 종가 대조 통과 — 겹친 %d일 최대 차 %.5f%%" % (tk, len(gaps), g))

        out["series"][key] = {
            "ticker": tk, "label": label + "(PR)",
            "dates": list(d.index.strftime("%Y-%m-%d")),
            "o": [round(float(x), 4) for x in d["open"]],
            "h": [round(float(x), 4) for x in d["high"]],
            "l": [round(float(x), 4) for x in d["low"]],
            "c": [round(float(x), 4) for x in d["close"]],
            "v": [int(x) for x in d["volume"]],
        }
        print("   %s %d행 · %s ~ %s" % (tk, len(d), out["series"][key]["dates"][0],
                                       out["series"][key]["dates"][-1]))

    out["as_of"] = max(v["dates"][-1] for v in out["series"].values())
    out["close_check"] = {"max_gap_pct": round(worst, 6), "tol_pct": MAX_GAP,
                          "말": "bench_px.json 종가와 대조한 최대 차. 이 수가 허용을 넘으면 "
                                "갱신을 멈춘다 — 벤치마크 잣대가 둘로 갈리지 않게."}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False) + "\n")
    print("→ %s (%.0fKB · 기준 %s)" % (OUT, os.path.getsize(OUT) / 1024, out["as_of"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
