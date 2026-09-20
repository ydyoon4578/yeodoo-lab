# -*- coding: utf-8 -*-
"""build/fund_fit3.py — 선별기 상위 10 슬리브의 t 에서 **선택편향을 뺀다**.

`fund_fit2.py` 가 낸 «상위 10 슬리브 증분 t 3.84» 는 그대로 읽으면 안 된다.
그 열은 **증분 t 가 큰 순으로 고른 것**이고, 고른 잣대로 다시 채점했다.
랩의 전례가 있다 — MOMSWING 에서 셔플을 전 유니버스로 돌리면 백분위 99 가 나오는데
그것은 모멘텀의 성적이지 타점의 성적이 아니었다. 같은 함정이다.

그래서 **거름을 통과한 52종에서 무작위로 열을 뽑아** 같은 채점을 2000번 한다.
실측 t 가 그 분포의 어디에 서는지가 «고른 솜씨» 의 크기다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fund_fit import fund_monthly, ols          # noqa: E402

NSHUF, SEED = 2000, 20260920
TOP = ["x-fcfy", "x-sp", "x-payout-n50", "x-divgrow", "x-runs",
       "x-btp", "x-guruacc", "x-poacc-n52", "x-residmom", "x-agrow"]


def main():
    F = fund_monthly()
    pit = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    ff = json.load(io.open(os.path.join(DATA, "_fund_fit.json"), encoding="utf-8"))
    passed = {r["sid"] for r in ff["rows"]
              if r.get("pit_excess") and r["pit_excess"] > 0
              and abs(r.get("corr") or 9) < ff["criteria"]["corr_hi"]
              and (r.get("turnover") or 0) <= ff["criteria"]["turnover_hi"]}
    E = {}
    for s in pit.get("strategies") or []:
        if s["sid"] not in passed:
            continue
        ch = (s.get("chart") or {}).get("monthly") or []
        E[s["sid"]] = pd.Series(
            {pd.Period(m["m"], freq="M"): (m["r"] - m["b"]) / 100.0
             for m in ch if m.get("r") is not None and m.get("b") is not None},
            dtype="float64")
    X = pd.DataFrame(E).dropna()
    j = X.index.intersection(F.index)
    X, f = X.reindex(j), F.reindex(j).to_numpy()
    print("거름 통과 %d종 · 공통 %d개월 (%s ~ %s)" % (X.shape[1], len(j), j[0], j[-1]))

    top = [c for c in TOP if c in X.columns]
    a, ta, b, _ = ols(X[top].mean(axis=1).to_numpy(), f)
    print("\n실측 — 상위 %d 슬리브 증분 연 %+.2f%%p · t %.2f" % (len(top), a * 1200, ta))

    rng = np.random.default_rng(SEED)
    ts, ays = [], []
    for _ in range(NSHUF):
        pick = rng.choice(X.shape[1], size=len(top), replace=False)
        aa, tt, _, _ = ols(X.iloc[:, pick].mean(axis=1).to_numpy(), f)
        ts.append(tt); ays.append(aa * 1200)
    ts, ays = np.array(ts), np.array(ays)
    pct = float((ts < ta).mean() * 100)
    print("무작위 %d종 슬리브 %d회 — t 중앙 %.2f · 95분위 %.2f · 최대 %.2f"
          % (len(top), NSHUF, np.median(ts), np.percentile(ts, 95), ts.max()))
    print("                         증분 중앙 %+.2f%%p · 95분위 %+.2f%%p"
          % (np.median(ays), np.percentile(ays, 95)))
    print("\n**실측 t %.2f 의 백분위 = %.1f**" % (ta, pct))

    print("""
🚨 **백분위 100 은 증거가 아니다. 내가 바로 그 통계로 골랐기 때문이다.**
   상위 10 을 «증분 t 가 큰 순»으로 뽑아 놓고 같은 t 로 채점했으니 100 이 안 나오면
   그게 이상한 것이다. 이 셔플이 말해 주는 것은 하나뿐이고, 그것은 밑의 수다 —

   **무작위로 열을 뽑으면 증분 연 %+.2f%%p · t %.2f 다(중앙값).**
   그것이 «아무 슬리브나 얹었을 때» 의 정직한 기대치다. t 1 대는 증거가 아니다.
   실측 %+.2f%%p 와 그 중앙값의 차이가 **통째로 선택편향**이라고 보는 것이 출발점이다.

   → 그래서 아래에서 진짜 질문을 묻는다: **앞 절반으로 고른 열이 뒤 절반에서도 되나.**
""" % (np.median(ays), np.median(ts), a * 1200))

    # ── 표본 밖 흉내 — 앞 절반으로 고르고 뒤 절반에서 채점한다 ──────────────
    h = len(j) // 2
    Xa, fa = X.iloc[:h], f[:h]
    Xb, fb = X.iloc[h:], f[h:]
    sc = {}
    for c in X.columns:
        _, tt, _, _ = ols(Xa[c].to_numpy(), fa)
        sc[c] = tt
    picked = [c for c, _ in sorted(sc.items(), key=lambda x: -x[1])[:len(top)]]
    a1, t1, _, _ = ols(Xa[picked].mean(axis=1).to_numpy(), fa)
    a2, t2, _, _ = ols(Xb[picked].mean(axis=1).to_numpy(), fb)
    ab, tb, _, _ = ols(Xb.mean(axis=1).to_numpy(), fb)       # 52종 전부(안 고름)
    print("■ 앞 절반(%s~%s)에서 고른 열 → 뒤 절반(%s~%s)에서 채점"
          % (j[0], j[h - 1], j[h], j[-1]))
    print("   고른 열: %s" % " · ".join(c.replace("x-", "") for c in picked))
    print("   앞 절반(고른 창)  증분 연 %+6.2f%%p · t %5.2f   ← 여기는 당연히 좋다"
          % (a1 * 1200, t1))
    print("   **뒤 절반(새 창)   증분 연 %+6.2f%%p · t %5.2f**" % (a2 * 1200, t2))
    print("   비교 — 52종 전부  증분 연 %+6.2f%%p · t %5.2f   (아무것도 안 고른 판)"
          % (ab * 1200, tb))
    keep = 100 * (a2 / a1) if a1 else float("nan")
    print("\n   **앞에서 고른 우위의 %.0f%% 가 뒤 창에 남았다.**" % keep)
    if a2 <= ab:
        print("   🚨 그런데 **고르지 않은 52종 전부가 더 낫거나 같다.** 고르는 행위가 "
              "값을 더하지 않았다 — 슬리브는 쓰되 «어느 열인지»는 고르지 말라는 뜻이다.")
    else:
        print("   고른 열이 안 고른 판보다 낫다 — 다만 한 번의 분할이라 증거로는 약하다.")
    print("""
   ⚠ 이 분할은 **한 번**이고 뒤 창이 %d개월뿐이다. 이것도 증거가 아니라 **표시등**이다.
     진짜 검정은 사전등록이고, 그것이 다음에 할 일이다.""" % len(fb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
