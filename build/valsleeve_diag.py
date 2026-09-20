# -*- coding: utf-8 -*-
"""build/valsleeve_diag.py — 등록서에 **없던** 검정. VALSLEEVE 가 한 구간에 걸려 있나.

왜 이걸 돌리나
   VALSLEEVE 가 기각 조건 일곱을 전부 통과했다. 랩에서 그런 일은 한 번 있었고
   (CASHTA · E57) 그때 결과문서에 이렇게 적었다 —
   «등록한 여섯 관문은 전부 통과했다. **등록서에 없던 검정 하나가 죽였다.**»
   그리고 그 교훈을 규약에 넣었다: **관문이 다 통과하면 그때 더 의심한다.**

   여기서 의심할 자리는 눈에 보인다 —
     앞 절반(2014-07~2020-07) 슬리브 +0.84%p · 증분 t 1.01
     뒤 절반(2020-08~2026-08) 슬리브 +11.06%p · 증분 t 3.83
   **초과가 뒤 절반에 몰려 있다.** 랩에는 «초과의 101%가 한 구간에서 나왔다»로
   사망한 전례가 있다(REGSEC · K2).

무엇을 재나
   ① 연도별 초과 · 증분
   ② 가장 좋았던 12개월을 빼면 무엇이 남나
   ③ 초과의 절반이 몇 개월에서 나왔나(집중도)
   ④ 2022 가치 랠리 한 해를 빼면
   ⑤ 축별로 따로 — 다섯 중 하나가 끌고 가나
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
import valsleeve as V                                    # noqa: E402


def ols(y, x):
    X = np.column_stack([np.ones(len(x)), x])
    bh, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ bh
    s2 = float(e @ e) / max(1, len(y) - 2)
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * s2))
    return float(bh[0]), float(bh[0] / se[0]) if se[0] > 0 else np.nan


def main():
    d = json.load(io.open(os.path.join(DATA, "_valsleeve.json"), encoding="utf-8"))
    E = pd.Series({pd.Period(k, freq="M"): v for k, v in d["series"]["sleeve"].items()},
                  dtype="float64").sort_index()
    Fd = pd.Series({pd.Period(k, freq="M"): v for k, v in d["series"]["fund"].items()},
                   dtype="float64").sort_index()
    j = E.index.intersection(Fd.index)
    E, Fd = E.reindex(j), Fd.reindex(j)
    tot = float(E.sum())
    print("슬리브 초과 %d개월 · 누적 합 %+.1f%%p (월 %+.3f%%)" % (len(E), tot * 100, E.mean() * 100))

    print("\n■ ① 연도별")
    print("   %-6s %10s %10s %8s" % ("해", "슬리브", "펀드", "차"))
    for y, g in E.groupby(E.index.year):
        f = Fd.reindex(g.index)
        print("   %-6d %+9.2f%%p %+9.2f%%p %+7.2f" % (y, g.sum() * 100, f.sum() * 100,
                                                      (g.sum() - f.sum()) * 100))

    print("\n■ ② 가장 좋았던 달을 빼면 (누적 %+.1f%%p 에서)" % (tot * 100))
    s = E.sort_values(ascending=False)
    for k in (1, 3, 6, 12):
        rest = E.drop(s.index[:k])
        a, ta = ols(rest.to_numpy(), Fd.reindex(rest.index).to_numpy())
        print("   상위 %2d개월 제외 → 누적 %+7.2f%%p · 월평균 %+.3f%% · 증분 %+6.2f%%p (t %.2f)"
              % (k, rest.sum() * 100, rest.mean() * 100, a * 1200, ta))

    print("\n■ ③ 집중도 — 초과의 절반이 몇 개월에서 나왔나")
    pos = E[E > 0].sort_values(ascending=False)
    c, half = 0.0, tot / 2
    for i, v in enumerate(pos, 1):
        c += v
        if c >= half:
            print("   양수 달 %d개 중 **상위 %d개월(%.0f%%)이 초과의 절반**을 만들었다"
                  % (len(pos), i, 100 * i / len(E)))
            break

    print("\n   ⚠ 집중도는 **혼자 보면 못 읽는다.** 같은 잣대로 펀드도 잰다 —")
    for nm, ser_ in (("슬리브", E), ("펀드", Fd)):
        tt = float(ser_.sum()); ss = ser_.sort_values(ascending=False)
        r12 = ser_.drop(ss.index[:12])
        pp = ser_[ser_ > 0].sort_values(ascending=False)
        c2, k2 = 0.0, 0
        for i, v in enumerate(pp, 1):
            c2 += v
            if c2 >= tt / 2:
                k2 = i; break
        print("      %-6s 누적 %+7.1f%%p · 상위 12개월 빼면 %+7.2f%%p · 초과 절반을 만든 달 %d개(%.0f%%)"
              % (nm, tt * 100, r12.sum() * 100, k2, 100 * k2 / len(ser_)))

    print("\n■ ③-b 슬리브가 크게 번 달은 **펀드가 아픈 달인가**")
    top12 = E.sort_values(ascending=False).index[:12]
    print("   슬리브 상위 12개월 — 슬리브 평균 %+.2f%% · 그 달 펀드 평균 %+.2f%%"
          % (E.reindex(top12).mean() * 100, Fd.reindex(top12).mean() * 100))
    bad = Fd.sort_values().index[:20]
    print("   펀드 최악 20개월  — 펀드 평균 %+.2f%% · 그 달 슬리브 평균 %+.2f%%"
          % (Fd.reindex(bad).mean() * 100, E.reindex(bad).mean() * 100))
    good = Fd.sort_values(ascending=False).index[:20]
    print("   펀드 최고 20개월  — 펀드 평균 %+.2f%% · 그 달 슬리브 평균 %+.2f%%"
          % (Fd.reindex(good).mean() * 100, E.reindex(good).mean() * 100))
    print("   → 슬리브 상위 12개월 중 펀드가 **음수**였던 달 %d개 / 12"
          % int((Fd.reindex(top12) < 0).sum()))

    print("\n■ ④ 한 해씩 빼면")
    for y in sorted(set(E.index.year)):
        rest = E[E.index.year != y]
        a, ta = ols(rest.to_numpy(), Fd.reindex(rest.index).to_numpy())
        mark = "  ←" if ta < 2 else ""
        print("   %d 제외 → 월 %+.3f%% · 증분 %+6.2f%%p (t %.2f)%s"
              % (y, rest.mean() * 100, a * 1200, ta, mark))

    print("\n■ ⑤ 축별로 따로 — 다섯 중 하나가 끌고 가나")
    for ax, ser in (d.get("axis_series") or {}).items():
        e = pd.Series({pd.Period(k, freq="M"): v for k, v in ser.items()},
                      dtype="float64").reindex(j).dropna()
        if len(e) < 24:
            continue
        a, ta = ols(e.to_numpy(), Fd.reindex(e.index).to_numpy())
        print("   %-8s 초과 연 %+6.2f%%p (t %5.2f) · 증분 %+6.2f%%p (t %5.2f)"
              % (ax, e.mean() * 1200,
                 float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e)))), a * 1200, ta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
