# -*- coding: utf-8 -*-
"""data/bench_px.json — 벤치마크 일간 종가만 얇게 뽑는다.

왜 있나. 내 포트폴리오 화면(portfolio.html)이 «내 것이 S&P 500 · 나스닥 100 대비
어땠나»를 그리려면 지수 일간 계열이 필요한데, 그것이 지금 **assets.json(5.2MB) 안에만**
있다. 각주 한 줄 때문에 4MB 를 받던 홈의 사고(2026-08-14)와 같은 자리라, 화면이 통째로
받게 두지 않는다.

무엇을 넣나. 지수 **가격지수(PR)** 둘만 — ^GSPC · ^NDX.
🚨 SPY·QQQ(총수익)를 넣지 않는다. 이 랩은 2026-08-13 에 벤치마크를 **전부 지수 PR 로
  통일**했다(사용자 결정). 여기서 TR 을 같이 실으면 화면마다 다른 잣대를 고르게 되고,
  그 순간 «두 잣대» 사고가 되돌아온다.
⚠ 배당 격차는 연 2.00%p 다(이 랩 실측 · SPY 11.19% vs ^GSPC 9.19%, 2006~2026).
  화면이 «내 포트가 지수를 이겼다»를 말할 때 그 사실을 함께 적어야 한다 —
  내 보유 종가가 배당조정이면 지수 PR 과 견주는 것만으로 연 2%p 를 공짜로 받는다.
"""
from __future__ import annotations
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(DATA, "assets.json")
OUT = os.path.join(DATA, "bench_px.json")

WANT = [("^GSPC", "S&P 500", "spx"), ("^NDX", "NASDAQ 100", "ndx")]
PR_GAP = 2.00          # 연 %p — asset_backtest.PR_GAP · strategy_index.PR_GAP 과 같은 수


def main() -> int:
    if not os.path.exists(SRC):
        print("❌ %s 없음 — python build/refresh_assets.py 먼저" % SRC)
        return 1
    A = json.load(io.open(SRC, encoding="utf-8"))
    dates, px = A.get("dates") or [], A.get("px") or {}
    if not dates:
        print("❌ assets.json 에 dates 가 없다")
        return 1

    out = {}
    for tk, label, key in WANT:
        a = px.get(tk)
        if not a or len(a) != len(dates):
            print("❌ %s 계열이 없거나 격자와 길이가 다르다 — 갱신 중단(이전본 유지)" % tk)
            return 1
        out[key] = {"ticker": tk, "label": label + "(PR)", "px": a}

    # 🚨 결측을 세어 적는다. 조용히 None 이 섞이면 화면이 그 날을 건너뛰며 그리는데,
    #   건너뛴 것과 값이 0 인 것을 눈으로 구별할 수 없다.
    holes = {k: sum(1 for v in v_["px"] if v is None) for k, v_ in out.items()}

    doc = {
        "note": "벤치마크 일간 종가(가격지수 PR). 내 포트폴리오 화면이 이것만 받는다 — "
                "assets.json 은 5.2MB 라 각주 하나에 통째로 받게 두지 않는다.",
        "as_of": dates[-1], "start": dates[0], "n": len(dates),
        "basis": "가격지수(PR) — 배당 재투자 없음",
        "pr_gap": PR_GAP,
        "pr_gap_note": "배당을 넣은 총수익과의 격차는 연 %.2f%%p 다(이 랩 실측 · "
                       "SPY 11.19%% vs ^GSPC 9.19%%, 2006~2026). 보유 종가가 배당조정이면 "
                       "이 지수와 견주는 것만으로 연 %.2f%%p 를 공짜로 얻는다 — "
                       "화면이 그 사실을 함께 적어야 한다." % (PR_GAP, PR_GAP),
        "holes": holes,
        "dates": dates,
        "series": out,
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s · %d일 (%s ~ %s) · %s · 결측 %s"
          % (os.path.relpath(OUT, ROOT), len(dates), dates[0], dates[-1],
             " · ".join(v["label"] for v in out.values()), holes))
    print("   %.0fKB (assets.json %.1fMB 대신)"
          % (os.path.getsize(OUT) / 1024, os.path.getsize(SRC) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
