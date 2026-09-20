# -*- coding: utf-8 -*-
"""build/rev_diag.py — 반전·역추세 여덟 규칙이 실은 몇 개인가.

랩의 반전 계열은 여덟이다. 그런데 모양을 보면 **네 신호 × 두 판(밴드/비밴드)** 이다:
   주간반전 x-rev1w(-band) · 월간반전 x-rev1m(-band) ·
   추세정렬 과매도 x-snapback(-band) · 지수 대비 괴리 x-ecm(-band)

**«여덟 개»라고 세는 것이 맞는지를 먼저 잰다.** 서로 상관이 0.95 면 그것은 여덟이 아니라
넷이고, 다중검정에서 여덟으로 세면 문턱이 헛돈다.

재는 것
   ① 여덟의 시점정확(PIT) 월별 초과 상관 행렬
   ② 밴드 ↔ 비밴드 짝의 상관(짝마다) · 회전 차이 · 성적 차이
   ③ 네 신호끼리의 상관(밴드판만으로)
   ④ 유효 자유도 — 상관행렬 고유값으로 «실질 몇 개인가»
   ⑤ 펀드와의 상관(얹을 수 있나)

⚠ 이것은 진단이고 판정이 아니다. 여기서 고른 것으로 바로 쓰지 않는다 —
  줄이고 강화하는 설계는 **사전등록으로** 묻는다.
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

PAIRS = [("x-rev1w", "x-rev1w-band", "주간반전"),
         ("x-rev1m", "x-rev1m-band", "월간반전"),
         ("x-snapback", "x-snapback-band", "추세정렬 과매도"),
         ("x-ecm", "x-ecm-band", "지수 대비 괴리")]
SIDS = [s for a, b, _ in PAIRS for s in (a, b)]


def main():
    ps = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    S = {x["sid"]: x for x in ps["strategies"]}
    rep = json.load(io.open(os.path.join(DATA, "strategy_report.json"), encoding="utf-8"))
    R = {x["sid"]: x for x in rep["items"]}

    E = {}
    for sid in SIDS:
        s = S.get(sid)
        if not s:
            print("⚠ %s 없음" % sid); continue
        mm = (s.get("chart") or {}).get("monthly") or []
        E[sid] = pd.Series({pd.Period(x["m"], freq="M"): (x["r"] - x["b"]) / 100.0
                            for x in mm if x.get("r") is not None and x.get("b") is not None},
                           dtype="float64")
    X = pd.DataFrame(E).dropna()
    print("반전 계열 %d개 · 공통 %d개월 (%s ~ %s)\n" % (X.shape[1], len(X), X.index[0], X.index[-1]))

    print("■ ② 밴드 ↔ 비밴드 — 짝마다 «두 개로 셀 만한가»")
    print("   %-16s %8s %9s %9s %9s %9s" % ("신호", "상관", "회전(민)", "회전(밴드)", "PIT초과(민)", "PIT초과(밴드)"))
    for a, b, nm in PAIRS:
        if a not in X or b not in X:
            continue
        c = float(np.corrcoef(X[a], X[b])[0, 1])
        ta = (R.get(a) or {}).get("turnover")
        tb = (R.get(b) or {}).get("turnover")
        pa = ((S.get(a) or {}).get("excess_cagr"))
        pb = ((S.get(b) or {}).get("excess_cagr"))
        print("   %-16s %8.3f %9s %9s %9s %9s"
              % (nm, c, _n(ta), _n(tb), _n(pa, "%+.2f"), _n(pb, "%+.2f")))
    print("   → 상관이 0.9 를 넘으면 그 짝은 **한 개다.** 밴드는 회전을 줄이는 손잡이이지")
    print("     새 축이 아니다(오늘 RUNS2 에서 «주기를 늦추는 것은 회전 장치가 아니다» 를 배웠다).")

    print("\n■ ① 여덟의 상관 행렬 (PIT 월별 초과)")
    C = X.corr()
    sh = [c.replace("x-", "").replace("-band", "~B")[:9] for c in C.columns]
    print("        " + " ".join("%9s" % s for s in sh))
    for i, idx in enumerate(C.index):
        print("%-8s" % sh[i] + " ".join("%9.2f" % C.at[idx, c] for c in C.columns))

    print("\n■ ③ 네 신호끼리 (밴드판으로만)")
    bands = [b for _, b, _ in PAIRS if b in X]
    Cb = X[bands].corr()
    off = Cb.to_numpy()[np.triu_indices(len(Cb), 1)]
    print("   짝 상관 중앙 %.2f · 최대 %.2f · 0.5 넘는 짝 %d/%d"
          % (np.median(off), off.max(), int((off > 0.5).sum()), len(off)))
    for i, a in enumerate(bands):
        for b in bands[i + 1:]:
            print("   %-18s ↔ %-18s %+.2f"
                  % (a.replace("-band", ""), b.replace("-band", ""), Cb.at[a, b]))

    print("\n■ ④ 유효 자유도 — 상관행렬 고유값으로")
    for lab, M in (("여덟 전부", X), ("밴드 넷만", X[bands])):
        ev = np.linalg.eigvalsh(M.corr().to_numpy())[::-1]
        ev = ev[ev > 0]
        eff = float(ev.sum() ** 2 / (ev ** 2).sum())        # 참여비 (participation ratio)
        top1 = 100 * ev[0] / ev.sum()
        print("   %-10s 규칙 %d개 → **유효 %0.1f개** · 첫 주성분이 분산의 %.0f%%"
              % (lab, M.shape[1], eff, top1))

    print("\n■ ⑤ 펀드와의 상관 — 얹을 수 있나")
    try:
        from fund_fit import fund_monthly
        F = fund_monthly()
        j = X.index.intersection(F.index)
        print("   공통 %d개월" % len(j))
        for sid in bands:
            c = float(np.corrcoef(X[sid].reindex(j), F.reindex(j))[0, 1])
            print("   %-20s 펀드 상관 %+.2f" % (sid, c))
        eq = X[bands].mean(axis=1)
        print("   %-20s 펀드 상관 %+.2f · 단독 연 %+.2f%%p"
              % ("넷 동일가중", float(np.corrcoef(eq.reindex(j), F.reindex(j))[0, 1]),
                 eq.reindex(j).mean() * 1200))
    except Exception as e:
        print("   (못 쟀다: %s)" % e)
    return 0


def _n(v, f="%.2f"):
    return (f % v) if isinstance(v, (int, float)) else "—"


if __name__ == "__main__":
    raise SystemExit(main())
