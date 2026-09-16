# -*- coding: utf-8 -*-
"""build/idxrevband.py — 지수 강화 + 리비전 드리프트 **+ 능동비중 무거래 밴드**

규약: build/PREREG-2026-09-16-IDXREVBAND.md (계산 전 커밋 f0d0cae69).

  묻는 것은 성적이 아니라 구조다 — **밴드가 회전을 줄이면서 비용 뒤 성적을 지키는가.**
  대조군은 «밴드만 뺀 같은 칸»(= IDXREV 를 오늘 다시 돌린 것).

🚨 구성·λ 풀이·신호는 전부 build/idxrev.py 를 그대로 쓴다(band 인자만 켠다).
   사본을 만들지 않는다 — 만들면 대조군과 검정군이 다른 코드가 된다.
🚨 얼린 측정 — 산출물은 밑줄 접두.

    python build/idxrevband.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_idxrevband.json")
sys.path.insert(0, HERE)

import idxrev as IR
import idxtilt as IT
import tech_backtest as TB

PREREG = "f0d0cae69"
# IDXREV 결과 문서의 판정값 — 무밴드 경로가 안 바뀌었는지 보는 대조(LOWTURN 실패조건)
IDXREV_IR = {("spx", "abs"): 0.000, ("spx", "prop"): -0.010,
             ("ndx", "abs"): 0.091, ("ndx", "prop"): 0.605}


def turnover(s):
    """편도 회전율(연, %) — 비용 드래그에서 되푼다.
    cost = COST_RT × 0.5 × Σ|Δw| 이고 Σ|Δw| = 매수+매도 = 2 × 편도회전."""
    drag = (s["ex"] - s["ex_net"]) / 100.0
    return 100.0 * (drag / (IT.COST_RT * 0.5)) / 2.0


def main():
    print("자료를 읽는다")
    IR.DATES = TB.load(full=True)[0]
    TB._RAT = TB.load_ratings()
    print("  BAND = %.1f (tech_backtest 값 그대로) · 격자 %s ~ %s"
          % (IR.BAND, IR.DATES[0], IR.DATES[-1]))

    RESULT = {"prereg": "build/PREREG-2026-09-16-IDXREVBAND.md",
              "prereg_commit": PREREG, "band": IR.BAND, "idx": {}}
    ok_repro = True

    for idx, lab in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        print("\n" + "=" * 78)
        print("══ %s (%s) ══" % (lab, idx.upper()))
        P, rows = IR.build(idx)
        rows = [x for x in rows if x["m"] <= IR.RAT_END]
        j0 = next(k for k, x in enumerate(rows) if x["m"] >= IR.JUDGE_START)
        n = len(rows) - j0
        print("판정 창 %s ~ %s · %d개월" % (rows[j0]["m"], rows[-1]["m"], n))

        cells = {}
        for cap in ("abs", "prop"):
            for bd in (False, True):
                o, b, a, lw, mult, sat = IR.solve(rows, j0, "rev", cap,
                                                  IT.TE_JUDGE, band=bd)
                cells[(cap, bd)] = (IR.ev(o), b, a, sat, lw)
            o, b, a, lw, mult, sat = IR.solve(rows, j0, "rev", cap,
                                              IT.TE_JUDGE, flip=True, band=True)
            cells[(cap, "flip")] = (IR.ev(o), b, a, sat, lw)

        # 🚨 LOWTURN 실패조건 — 무밴드 경로가 한 자리라도 바뀌면 공용 코드를 건드린 것이다
        print()
        for cap in ("abs", "prop"):
            got = cells[(cap, False)][0]["ir"]
            want = IDXREV_IR[(idx, cap)]
            same = abs(got - want) < 0.0005
            ok_repro &= same
            print("  무밴드 재현 %-4s IR %+.3f (IDXREV %+.3f) → %s"
                  % (cap, got, want, "같다" if same else "🚨 달라졌다"))

        print()
        print("%-26s %9s %8s %8s %7s %7s %9s %8s"
              % ("", "초과", "순초과", "IR", "IR순", "t순", "편도회전", "걸림(수)"))
        NAME = {("abs", False): "무밴드 · ±1%p", ("abs", True): "**밴드** · ±1%p",
                ("abs", "flip"): "위약(반전) · ±1%p",
                ("prop", False): "무밴드 · 비중비례", ("prop", True): "**밴드** · 비중비례",
                ("prop", "flip"): "위약(반전) · 비중비례"}
        for key in (("abs", False), ("abs", True), ("abs", "flip"),
                    ("prop", False), ("prop", True), ("prop", "flip")):
            s, b, a, sat, _ = cells[key]
            print("%-26s %+8.2f%%p %+7.2f%%p %+8.3f %+7.3f %6.2f %7.0f%% %7.1f%%%s"
                  % (NAME[key], s["ex"], s["ex_net"], s["ir"], s["ir_net"], s["t_net"],
                     turnover(s), 100 * b[0] / max(1, b[1]), " ⚠포화" if sat else ""))
        print("   벤치 CAGR %.2f%%" % cells[("abs", False)][0]["bcagr"])

        print()
        print("── 판정 (등록 §3) ────────────────────────────────────────")
        V = {}
        for cap in ("abs", "prop"):
            sB, bB, aB, satB, _ = cells[(cap, True)]
            sN, _bN, _aN, _satN, _ = cells[(cap, False)]
            sF = cells[(cap, "flip")][0]
            tB, tN = turnover(sB), turnover(sN)
            f1 = tB < tN * 0.5
            f2 = sB["ir_net"] > sN["ir_net"]
            f3 = (sB["ir_net"] > 0 and sB["t_net"] >= 1.5)
            f4 = abs(sB["te"] - 2.0) <= 1.0 and not satB
            f5 = (sF["ir"] * sB["ir"] < 0) and (abs(sF["ir"]) >= 0.5 * abs(sB["ir"]))
            f6 = sB["win"] > 50.0
            nm = "밴드 · " + ("±1%p" if cap == "abs" else "비중비례")
            print("%s" % nm)
            print("   F1 회전 %.0f%% → %.0f%% (절반=%.0f%%)      → %s"
                  % (tN, tB, tN * 0.5, "통과" if f1 else "기각"))
            print("   F2 비용뒤 IR %+.3f vs 무밴드 %+.3f     → %s"
                  % (sB["ir_net"], sN["ir_net"], "통과" if f2 else "기각"))
            print("   F3 비용뒤 IR %+.3f · t %.2f            → %s"
                  % (sB["ir_net"], sB["t_net"], "통과" if f3 else "기각"))
            print("   F4 실현 TE %.2f%%                     → %s" % (sB["te"], "통과" if f4 else "기각"))
            print("   F5 위약 IR %+.3f (본 %+.3f · 크기 %.0f%%) → %s"
                  % (sF["ir"], sB["ir"],
                     100 * abs(sF["ir"]) / max(1e-9, abs(sB["ir"])), "통과" if f5 else "기각"))
            print("   F6 월승률 %.1f%%                       → %s" % (sB["win"], "통과" if f6 else "기각"))
            print("   [측정만] 한도걸림 %.1f%% (무밴드 %.1f%%) · 밴드가 잡은 비율 %.1f%% · 능동비중 %.1f%%"
                  % (100 * bB[0] / max(1, bB[1]),
                     100 * cells[(cap, False)][1][0] / max(1, cells[(cap, False)][1][1]),
                     100 * bB[3], 100 * sorted(aB)[len(aB) // 2]))
            V[nm] = dict(f1=f1, f2=f2, f3=f3, f4=f4, f5=f5, f6=f6,
                         turn=round(tB, 1), turn_noband=round(tN, 1),
                         ir=round(sB["ir"], 3), ir_net=round(sB["ir_net"], 3),
                         t_net=round(sB["t_net"], 2), win=round(sB["win"], 1),
                         te=round(sB["te"], 2), placebo_ir=round(sF["ir"], 3),
                         bind=round(100 * bB[0] / max(1, bB[1]), 1),
                         band_hold=round(100 * bB[3], 1),
                         active=round(100 * sorted(aB)[len(aB) // 2], 2),
                         metrics=sB, noband=sN)

        # 측정만 — 경로의존(시작월을 12개월 뒤로)
        print()
        print("── 측정만 · 경로의존 (시작월을 12개월 뒤로) ──────────────")
        for cap in ("abs", "prop"):
            o, b, a, lw, mult, sat = IR.solve(rows, j0 + 12, "rev", cap,
                                              IT.TE_JUDGE, band=True)
            s = IR.ev(o)
            o2, b2, a2, lw2, m2, s2_ = IR.solve(rows, j0 + 12, "rev", cap,
                                                IT.TE_JUDGE, band=False)
            sN2 = IR.ev(o2)
            print("   %-5s %d개월 · 밴드 IR순 %+.3f (무밴드 %+.3f) · 회전 %.0f%% (무밴드 %.0f%%)"
                  % (cap, s["n"], s["ir_net"], sN2["ir_net"], turnover(s), turnover(sN2)))
            V["경로 " + cap] = dict(n=s["n"], ir_net=round(s["ir_net"], 3),
                                    ir_net_noband=round(sN2["ir_net"], 3),
                                    turn=round(turnover(s), 1))

        RESULT["idx"][idx] = {"label": lab, "months": n,
                              "window": [rows[j0]["m"], rows[-1]["m"]],
                              "cells": {"%s|%s" % (k[0], k[1]):
                                        dict(cells[k][0], turnover=round(turnover(cells[k][0]), 1),
                                             bind_n=round(100 * cells[k][1][0]
                                                          / max(1, cells[k][1][1]), 2),
                                             band_hold=round(100 * cells[k][1][3], 2))
                                        for k in cells},
                              "verdicts": V}

    RESULT["reproduced_noband"] = ok_repro
    json.dump(RESULT, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n무밴드 재현 %s" % ("전부 같다 ✅" if ok_repro else "🚨 달라진 칸이 있다"))
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
