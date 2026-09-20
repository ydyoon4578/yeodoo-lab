# -*- coding: utf-8 -*-
"""build/restate_10y.py — 오늘 낸 판정들을 **10년 창**으로 다시 읽는다(재진술).

🚨 이것은 **판정을 고치는 것이 아니다.** 등록은 그때의 창(146개월)으로 이뤄졌고,
   창을 바꿔 판정을 다시 읽으면 그것이 사후 조정이다.
   여기서 묻는 것은 하나 — **«10년으로 잘랐을 때 결론이 갈리는가»** 다.
   갈리면 그 사실을 결과문서에 정정으로 싣고, 안 갈리면 «창에 의존하지 않는다» 가 남는다.

⚠ 왜 이걸 하나 — `MAX_YEARS = 10` 은 2026-08-13 **사용자 결정**이고
  «한 화면에서 10년짜리와 20년짜리가 나란히 서면 비교가 성립하지 않는다» 가 그 이유다.
  오늘 낸 다섯은 그 상수를 안 읽고 146개월(12.2년)로 쟀다. 게시 산출물이 아니라는 이유로
  새 코드가 규약 밖에 있었던 것이고, **규약은 코드가 아니라 랩에 건다.**
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
from maxyears import MAX_YEARS, cap, check_const                 # noqa: E402

RUNS = [
    ("VALSLEEVE", "_valsleeve.json", "sleeve", "보류(조건 일곱 전부 통과)"),
    ("GURUACC", "_guruacc_fund.json", "guru", "기각(F3 t 1.39)"),
    ("RESIDMOM", "_residmom_fund.json", "resid", "기각(아홉 중 여섯)"),
    ("RUNS", "_runs_fund.json", "runs", "기각(F3 1.96 · F9 4.06회)"),
    ("RUNS2", "_runs2_fund.json", "runs2", "기각(F3 2.01 · F7 · F9 · F10)"),
]


def ols(y, x):
    X = np.column_stack([np.ones(len(x)), x])
    bh, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ bh
    s2 = float(e @ e) / max(1, len(y) - 2)
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * s2))
    return float(bh[0]), float(bh[0] / se[0]) if se[0] > 0 else np.nan


def stat(e):
    n = len(e)
    te = float(e.std(ddof=1) * np.sqrt(12) * 100)
    return (float(e.mean() * 1200), te,
            float(e.mean() / (e.std(ddof=1) / np.sqrt(n))),
            float(e.mean() * 1200 / te) if te else np.nan)


def main():
    check_const()
    print("백테스트 길이 상한 %d년 — 2026-08-13 사용자 결정\n" % MAX_YEARS)
    print("%-11s %-24s %11s %11s %8s %8s" %
          ("등록", "무엇", "전체창", "10년창", "차", "판정 갈림"))
    flips = []
    for lab, fn, key, verdict in RUNS:
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            print("%-11s (산출물 없음 — %s)" % (lab, fn)); continue
        d = json.load(io.open(p, encoding="utf-8"))
        S = d.get("series") or {}
        if key not in S or "fund" not in S:
            print("%-11s (계열 없음)" % lab); continue
        E = pd.Series({pd.Period(k, freq="M"): v for k, v in S[key].items()},
                      dtype="float64").sort_index()
        F = pd.Series({pd.Period(k, freq="M"): v for k, v in S["fund"].items()},
                      dtype="float64").sort_index()
        j = E.index.intersection(F.index)
        E, F = E.reindex(j), F.reindex(j)
        jc = cap(j)
        Ec, Fc = E.reindex(jc), F.reindex(jc)

        y_full, _, _, _ = stat(E)
        y_cap, _, _, _ = stat(Ec)
        a_f, t_f = ols(E.to_numpy(), F.to_numpy())
        a_c, t_c = ols(Ec.to_numpy(), Fc.to_numpy())

        # 그 등록의 F3 문턱 — RUNS2 만 2.24 다(두 번째 시도)
        thr = 2.24 if lab == "RUNS2" else 2.0
        pass_full, pass_cap = t_f >= thr, t_c >= thr
        flip = "🚨 **갈린다**" if pass_full != pass_cap else "—"
        if pass_full != pass_cap:
            flips.append((lab, t_f, t_c, thr))
        print("%-11s %-24s %+10.2f%%p %+10.2f%%p %+7.2f  %s"
              % (lab, "단독 초과", y_full, y_cap, y_cap - y_full, ""))
        print("%-11s %-24s %10.2f  %10.2f  %+7.2f  %s"
              % ("", "증분 알파 t (문턱 %.2f)" % thr, t_f, t_c, t_c - t_f, flip))
        print("%-11s %-24s %+10.2f%%p %+10.2f%%p %+7.2f"
              % ("", "증분 알파 연", a_f * 1200, a_c * 1200, (a_c - a_f) * 1200))
        print("%-11s   창 %d개월(%s~%s) → %d개월(%s~%s) · 등록 판정: %s\n"
              % ("", len(j), j[0], j[-1], len(jc), jc[0], jc[-1], verdict))

    # 🚨 F3 이 갈린다고 «판정이 갈린다» 는 것이 아니다. 다른 조건도 봐야 한다.
    print("=" * 74)
    print("■ F3 이 갈리는 등록의 **나머지 조건** — 판정이 실제로 갈리나")
    for lab, fn, key, verdict in RUNS:
        if lab not in [f[0] for f in flips]:
            continue
        d = json.load(io.open(os.path.join(DATA, fn), encoding="utf-8"))
        fails = d.get("fails") or {}
        others = [k for k, v in sorted(fails.items()) if v and k != "F3"]
        print("   %-9s F3 말고도 걸린 것: %s"
              % (lab, " · ".join(others) if others else "없음"))
        print("             → 10년 창에서 F3 이 통과해도 판정은 %s"
              % ("**그대로 기각**" if others else "🚨 **갈린다**"))
    print()

    if flips:
        print("🚨 10년으로 자르면 F3 통과·미통과가 갈리는 등록 %d건:" % len(flips))
        for lab, tf, tc, thr in flips:
            print("   %-11s t %.2f → %.2f (문턱 %.2f)" % (lab, tf, tc, thr))
        print("""
   ⚠ **그래도 등록의 판정을 고치지 않는다.** 등록은 그때의 창으로 이뤄졌고,
     창을 바꿔 통과로 읽으면 사후 조정이다. 결과문서에 «창을 10년으로 자르면
     이렇게 된다» 를 **정정이 아니라 재진술로** 싣는다.
   → 앞으로의 등록은 처음부터 10년으로 연다(build/maxyears.py).""")
    else:
        print("✅ 10년으로 잘라도 F3 통과·미통과가 갈리는 등록은 없다.")
        print("   → 오늘의 판정들은 **창 길이에 의존하지 않는다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
