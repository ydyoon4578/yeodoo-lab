# -*- coding: utf-8 -*-
"""build/style_fmom.py — 스타일 로테이션(팩터 모멘텀). 규약은 PREREG-2026-09-21-STYLE8ROT.md.

🚨 등록서에 적은 것만 한다. 결과를 보고 자산 수(8/9)·선택 크기(상위 절반)·
   신호(12-1)·주기(월말)를 바꾸지 않는다. 16종판·9종판·7종판은 만들지 않는다.
🚨 자산 선정을 **네 번 고쳤다**(등록서 §3-1-a). 최종은 «표준 8종» 이고
   기준은 성적이 아니라 **표준 팩터 분류**다. 그래도 나는 성적표를 이미 봤다 —
   그래서 fmom8 > fmom 을 «축을 다양화하면 좋아진다» 의 증거로 쓰지 않는다.
   두 판 다 **8종**이라, 바뀐 것은 개수가 아니라 **축의 다양성** 하나다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_style_fmom.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maxyears import MAX_YEARS, cap                              # noqa: E402

# ── 등록서 §3 의 상수 ──────────────────────────────────────────────────────
LB_A, LB_B = 12, 2          # 점수 구간 t-12 ~ t-2 (직전 1개월 건너뜀)
COST = 0.0020               # 왕복 20bp — STYLE8W F4 와 같은 값
NSHUF, SEED = 200, 20260921
EIGHT = ["val", "grow", "hbeta", "div", "spmo", "qvm", "squal", "size"]
# 표준 8종 — MSCI 6대(val·size·spmo·squal·lowvol·div) + 수익성(fcfy 대용)
#            + 투자/순발행(netbuy 대용). 등록서 §3-1-b · §3-1-b-2.
STD8 = ["val", "size", "spmo", "squal", "div", "lowvol", "fcfy", "netbuy"]


def eff_n(C):
    """상관행렬의 유효 자산 수 — 고유값 참여비."""
    ev = np.linalg.eigvalsh(C.to_numpy())[::-1]
    ev = ev[ev > 1e-12]
    return float(ev.sum() ** 2 / (ev ** 2).sum())


def main():
    d = json.load(io.open(os.path.join(DATA, "style_pit.json"), encoding="utf-8"))
    S = d["styles"]
    print("style_pit.json — %s · 레그 %d종 · 월말 %d회"
          % (d.get("as_of"), len(S), d.get("n_month_ends")))

    # ── 레그의 월별 수익 ──────────────────────────────────────────────────
    # 🚨 pit 레그만 쓴다(등록서 §3-2). 소급 레그는 안 쓴다.
    def nav(k):
        p = (S.get(k) or {}).get("pit") or {}
        for key in ("monthly", "nav_m", "ret_m", "series"):
            if key in p:
                return p[key]
        return None

    probe = nav("val")
    if probe is None:
        print("\n🚨 pit 레그에 월별 계열이 없다. 실제 키를 찍는다:")
        print("   pit 키:", list(((S.get("val") or {}).get("pit") or {}).keys()))
        print("   styles['val'] 키:", list((S.get("val") or {}).keys()))
        return 2

    R = {}
    for k in sorted(set(EIGHT) | set(STD8)):
        v = nav(k)
        if v is None:
            print("   ⚠ %s — 월별 계열 없음" % k); continue
        R[k] = pd.Series({pd.Period(m, freq="M"): float(x) for m, x in v.items()},
                         dtype="float64").sort_index()
    X = pd.DataFrame(R).dropna()
    print("공통 %d개월 (%s ~ %s)" % (len(X), X.index[0], X.index[-1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
