# -*- coding: utf-8 -*-
"""애널리스트 등급 변경 이력의 **실현가능성만** 잰다 — 성과는 재지 않는다.

🚨 이 스크립트에는 수익률 코드가 없다. 성과를 보고 후보·창·부호를 고르면 그건 검정이
  아니다(이 랩의 사전등록 규약). 여기서 답하는 것은 넷이다:

    ① 몇 종목이 이 자료를 갖고 있나 (커버리지)
    ② 언제부터 있나 — 백테스트 창을 정하는 값
    ③ 한 달에 몇 건이 오나 — 신호 밀도. 너무 얇으면 월말 순위가 잡음이 된다
    ④ 등급 어휘가 몇 가지인가 — 5→1 척도로 바꾸려면 이 목록을 먼저 알아야 한다

  ④가 특히 중요하다. 브로커마다 말이 달라(Buy/Overweight/Outperform/Sector Perform…)
  매핑을 손으로 만들어야 하는데, **결과를 보고 매핑을 고치면 그 검정은 무효다.**
  그래서 어휘 목록을 먼저 뽑아 사전등록 문서에 박아 둔다.

⚠ 이 자료의 성격 — GradeDate 는 발표일이라 t+2 진입 규약이면 선견이 없다. 다만
  yfinance 가 과거 행을 소급 수정하는지는 알 수 없다. 그 한계는 사전등록에 적는다.
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(HERE, "_probe_ratings.json")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="표본 종목 수(0 이면 전체)")
    a = ap.parse_args()

    import yfinance as yf
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    tick = [s["t"] for s in st["stocks"]]
    if a.n:
        # 시총 순이 아니라 **알파벳 순 등간격**으로 뽑는다 — 대형주만 보면 커버리지가
        # 실제보다 좋게 나온다(대형주는 애널리스트가 많다).
        step = max(1, len(tick) // a.n)
        tick = tick[::step][:a.n]

    from collections import Counter
    grades, actions, firms = Counter(), Counter(), Counter()
    rows, none_n = [], 0
    for i, t in enumerate(tick):
        try:
            ud = yf.Ticker(t).upgrades_downgrades
        except Exception:
            ud = None
        if ud is None or len(ud) == 0:
            none_n += 1
            rows.append({"t": t, "n": 0})
            continue
        d0, d1 = str(ud.index.min())[:10], str(ud.index.max())[:10]
        for g in ud["ToGrade"].tolist():
            grades[str(g).strip()] += 1
        for g in ud["FromGrade"].tolist():
            grades[str(g).strip()] += 1
        for x in ud["Action"].tolist():
            actions[str(x).strip()] += 1
        for x in ud["Firm"].tolist():
            firms[str(x).strip()] += 1
        # 최근 5년 건수 — 밀도는 옛날이 아니라 지금 기준으로 봐야 한다
        recent = int((ud.index >= "2021-01-01").sum())
        rows.append({"t": t, "n": int(len(ud)), "d0": d0, "d1": d1, "n5y": recent})
        if (i + 1) % 20 == 0:
            print("  … %d/%d" % (i + 1, len(tick)))
        time.sleep(0.05)

    have = [r for r in rows if r["n"]]
    print()
    print("① 커버리지 — %d/%d 종목에 등급 이력이 있다 (%.0f%%)"
          % (len(have), len(rows), 100.0 * len(have) / max(1, len(rows))))
    if have:
        ds = sorted(r["d0"] for r in have)
        print("② 시작일 — 가장 이른 %s · 중앙 %s · 가장 늦은 %s"
              % (ds[0], ds[len(ds) // 2], ds[-1]))
        ns = sorted(r["n5y"] for r in have)
        print("③ 최근 5년 건수 — 중앙 %d건/종목 (월 %.1f건 · 유니버스 전체로는 월 %.0f건)"
              % (ns[len(ns) // 2], ns[len(ns) // 2] / 60.0,
                 sum(ns) / 60.0 / max(1, len(have)) * len(rows)))
    print()
    print("④ 등급 어휘 — %d가지" % len(grades))
    for g, c in grades.most_common(30):
        print("     %-28s %6d" % (g, c))
    print()
    print("   Action 어휘:", dict(actions))
    print("   브로커 %d곳 · 상위: %s" % (len(firms), " · ".join(f for f, _ in firms.most_common(8))))
    json.dump({"rows": rows, "grades": dict(grades), "actions": dict(actions),
               "firms": dict(firms.most_common(60))},
              io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print()
    print("→", OUT)
    print("⚠ 위에 성과는 없다. 이 프로브는 '잴 수 있는가'만 답한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
