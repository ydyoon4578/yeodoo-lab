# -*- coding: utf-8 -*-
"""build/fund_fit2.py — 선별기 상위가 «여덟 개 아이디어» 인지 «하나» 인지 본다.

`fund_fit.py` 의 상위는 전부 가치·주주환원 축이었다(잉여현금흐름수익률 · 저PSR ·
총주주환원 · 배당증액 · 장부가). **서로 상관이 높으면 그것은 여덟 후보가 아니라
한 후보를 여덟 번 센 것**이고, 다중검정에서 여덟으로 세면 안 된다.

그리고 묶었을 때(동일가중 슬리브) 펀드 위에 무엇이 남는지도 본다 —
**신규 펀드로 쓸 수 있는 형태인가**를 묻는 자리다.

⚠ 여전히 선별기다. 판정이 아니다.
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

TOP = ["x-fcfy", "x-sp", "x-payout-n50", "x-divgrow", "x-runs",
       "x-btp", "x-guruacc", "x-poacc-n52", "x-residmom", "x-agrow"]


def main():
    F = fund_monthly()
    pit = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    E = {}
    for s in pit.get("strategies") or []:
        if s["sid"] not in TOP:
            continue
        ch = (s.get("chart") or {}).get("monthly") or []
        E[s["sid"]] = pd.Series(
            {pd.Period(m["m"], freq="M"): (m["r"] - m["b"]) / 100.0
             for m in ch if m.get("r") is not None and m.get("b") is not None},
            dtype="float64")
    X = pd.DataFrame(E).dropna()
    j = X.index.intersection(F.index)
    X, f = X.reindex(j), F.reindex(j)
    print("상위 %d종 · 공통 %d개월 (%s ~ %s)\n" % (X.shape[1], len(j), j[0], j[-1]))

    C = X.corr()
    print("■ 상위끼리의 상관 — 여덟 아이디어인가, 하나인가")
    print("        " + " ".join("%7s" % c.replace("x-", "")[:7] for c in C.columns))
    for i in C.index:
        print("%-8s" % i.replace("x-", "")[:8]
              + " ".join("%7.2f" % C.at[i, c] for c in C.columns))
    off = C.to_numpy()[np.triu_indices(len(C), 1)]
    print("\n   짝 상관 중앙 %.2f · 최대 %.2f · 0.5 넘는 짝 %d/%d"
          % (np.median(off), off.max(), int((off > 0.5).sum()), len(off)))

    # 가치·환원 묶음과 나머지를 갈라 본다
    VAL = [c for c in X.columns if c in ("x-fcfy", "x-sp", "x-btp",
                                         "x-payout-n50", "x-divgrow")]
    OTH = [c for c in X.columns if c not in VAL]
    print("\n■ 묶어서 — 펀드 위에 무엇이 남나 (동일가중 슬리브)")
    for nm, cols in (("가치·주주환원 5종", VAL), ("나머지 5종", OTH), ("열 전부", list(X.columns))):
        y = X[cols].mean(axis=1).to_numpy()
        a, ta, b, r2 = ols(y, f.to_numpy())
        cr = float(np.corrcoef(y, f.to_numpy())[0, 1])
        print("   %-14s 단독 연 %+6.2f%%p · 펀드상관 %+.2f · 증분 연 %+6.2f%%p (t %.2f) · β %+.2f"
              % (nm, y.mean() * 1200, cr, a * 1200, ta, b))

    # 펀드 + 슬리브를 섞으면
    print("\n■ 펀드에 가치·주주환원 슬리브를 섞으면 (초과수익 기준 · 비용 전)")
    v = X[VAL].mean(axis=1).to_numpy(); fu = f.to_numpy()
    print("   %-8s %10s %10s %8s" % ("배합", "연 초과", "변동성", "정보비율"))
    for w in (0.0, 0.1, 0.2, 0.3, 0.5):
        m = (1 - w) * fu + w * v
        sd = m.std(ddof=1) * np.sqrt(12)
        print("   펀드%3d%% %+9.2f%%p %9.2f%% %8.2f"
              % (100 - w * 100, m.mean() * 1200, sd * 100,
                 (m.mean() * 12) / sd if sd > 0 else np.nan))
    print("""
   ⚠ 이 표는 «초과수익끼리» 섞은 것이라 실제 운용의 비용·제약이 안 들어 있다.
     슬리브를 실제로 넣으려면 종목이 겹치는 몫·리밸 주기·거래비용을 다시 재야 한다.
     그래서 이것은 **다음 사전등록의 설계도**이지 성적표가 아니다.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
