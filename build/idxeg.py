# -*- coding: utf-8 -*-
"""build/idxeg.py — 지수 강화 · 기대투자성장(Eg) 틸트 (시점정확 패널) → data/_idxeg.json

사전등록: build/PREREG-2026-09-23-IDXEG.md (계산 전 커밋 c9e755b1)

🚨 틸트 산식은 사본이 없다 — `idxrev.run` · `solve` · `ev` · `zsec` 를 그대로 import 한다.
   IDXREV 가 신호를 x["Z"]["rev"] 칸에서 읽으므로 **Eg 의 섹터 내 z 를 그 칸에 싣는다**
   (함수는 신호 이름을 모른다 — 칸 이름만 그대로 쓴다).
🚨 신호는 `build/eg_q5.py --scores` 가 내보낸 E_t(data/_eg_q5_scores.json) — Eg 등록과 같은 예측식.
🚨 패널은 시점정확으로 새로 짠다(IDXTILT 패널은 오늘 유니버스에 남은 종목만 담았다):
   그 달 index_history 의 SPX·NDX 명단 · 가격 sd + 편출 정리본 pit_px.json(격리 반영) · 주식수 load_fund sh(90일 지연)
   · 이중클래스 회사당 하나 · 달 중간 상장폐지는 마지막 가격.
🚨 얼린 측정 — CI 에 붙이지 않는다.

    python build/idxeg.py
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import idxrev as IR                   # noqa: E402  run·solve·ev·zsec 정본(IDXREV)
import idxtilt as IT                  # noqa: E402  TE_JUDGE·CAP·COST 정본(IDXTILT)
import tech_backtest as TB            # noqa: E402  load_fund·asof_all
import pit_quarantine as PQ           # noqa: E402  격리 명단

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_idxeg.json")

JUDGE = ("2018-07", "2026-08")        # 보유월 판정 창 — IDXTILT·IDXREV 와 같은 시작
LONG0 = "2016-09"                     # 서술 창 시작(Eg 점수가 처음 서는 보유월)
KEEP_DUAL = {"GOOGL", "FOXA", "NWSA"}
F_T = 1.5


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def main() -> int:
    # 🚨 2026-09-23 — 패널 준비를 build/pit_panel.py 로 떼어냈다(GURUCMP 가 같은 패널을 쓴다).
    #   계산은 한 글자도 안 바뀌어야 한다 — 떼어낸 뒤 _idxeg.json 의 판정 수치가 재현되는지 확인했다.
    import pit_panel as PP                     # noqa: E402  같은 build/ 안
    Wd = PP.load_world()
    SC = json.load(io.open(os.path.join(DATA, "_eg_q5_scores.json"), encoding="utf-8"))["months"]
    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))
    IDXM = CH["idx_monthly"]

    RESULT = {"prereg": "build/PREREG-2026-09-23-IDXEG.md", "prereg_commit": "c9e755b1",
              "judge": list(JUDGE), "long0": LONG0, "te_target": IT.TE_JUDGE, "idx": {}}
    for ix, lab, bench_name in (("spx", "S&P 500", "S&P 500"), ("ndx", "NASDAQ 100", "NASDAQ 100")):
        rows, cover = PP.month_rows(Wd, ix, SC, JUDGE[1])          # 신호월 = Eg 형성월
        for x in rows:
            names = x["names"]
            raw = {t: SC[x["sig"]][t] for t in names if t in SC[x["sig"]]}
            x["Z"] = {"rev": IR.zsec(raw, x["sec"], names)}      # 🚨 Eg z 를 IDXREV 의 신호 칸에 싣는다
            x["cov"] = {"eg": sum(x["wb"][t] for t in raw)}
        # ── F0 패널 관문 ─────────────────────────────────────────────────────
        f0_ok, f0_corr, f0_gap = PP.f0_gate(rows, IDXM, bench_name, JUDGE)
        j0 = next(k for k, x in enumerate(rows) if x["m"] >= JUDGE[0])
        jl = next(k for k, x in enumerate(rows) if x["m"] >= LONG0)
        print("\n" + "=" * 74)
        print("══ %s ══  판정 창 %s ~ %s · %d개월 · 패널 %s ~ %s" % (lab, rows[j0]["m"], rows[-1]["m"], len(rows) - j0,
                                                            rows[0]["m"], rows[-1]["m"]))
        print("  명단 중 가격·주식수 있음: 최저 %.1f%% · 중앙 %.1f%% · 평균 종목 %.0f"
              % (100 * min(cover), 100 * float(np.median(cover)), np.mean([len(x["names"]) for x in rows])))
        print("  Eg 커버리지(벤치 시총): 중앙 %.0f%%" % (100 * float(np.median([x["cov"]["eg"] for x in rows[j0:]]))))
        print("  F0 패널 벤치 vs %s(PR): 상관 %.4f · 차이 월 %+.3f%%p → %s"
              % (bench_name, f0_corr, f0_gap, "통과" if f0_ok else "🚨 무효"))

        TE = IT.TE_JUDGE
        cells = {}
        for cap in ("abs", "prop"):
            for flip in (False, True):
                o, b, a, lw, mult, sat = IR.solve(rows, j0, "rev", cap, TE, flip)
                s = IR.ev(o)
                cells[(cap, flip)] = (s, b, a, lw, mult, sat)
        V = {}
        for cap, nm in (("abs", "±1%p"), ("prop", "비중비례")):
            s, b, a, lw, mult, sat = cells[(cap, False)]
            pl = cells[(cap, True)][0]
            bind = 100 * b[0] / max(1, b[1])
            f1 = s["ir"] > 0 and s["t"] >= F_T
            f2 = s["ir_net"] > 0 and s["t_net"] >= F_T
            f3 = abs(s["te"] - 2.0) <= 1.0
            f4 = bind < 50.0
            f5 = pl["ir"] * s["ir"] < 0
            f6 = s["win"] > 50.0
            verdict = ("무효" if not f0_ok else "기각" if not (f1 and f2) else
                       "보류" if not (f3 and f4 and f5 and f6) else "게시 후보")
            print("\n  ── 판정 %s · %s ──" % (lab, nm))
            print("   초과 연 %+.2f%%p · TE %.2f%% · IR %+.3f · t %.2f · 월승률 %.1f%%%s"
                  % (s["ex"], s["te"], s["ir"], s["t"], s["win"], " ⚠포화" if sat else ""))
            print("   F1 IR %+.3f · t %.2f → %s" % (s["ir"], s["t"], "통과" if f1 else "기각"))
            print("   F2 비용 뒤 IR %+.3f · t %.2f → %s" % (s["ir_net"], s["t_net"], "통과" if f2 else "기각"))
            print("   F3 실현 TE %.2f%% → %s" % (s["te"], "통과" if f3 else "걸림"))
            print("   F4 한도걸림 %.1f%% (비중 %.1f%%) → %s" % (bind, 100 * b[2], "통과" if f4 else "걸림 — 한도가 정했다"))
            print("   F5 위약 IR %+.3f → %s" % (pl["ir"], "통과" if f5 else "걸림"))
            print("   F6 월승률 %.1f%% → %s" % (s["win"], "통과" if f6 else "걸림"))
            print("   ⇒ %s   (벤치 CAGR %.2f%% · 전략 CAGR %.2f%% · 능동비중 중앙 %.1f%%)"
                  % (verdict, s["bcagr"], s["cagr"], 100 * sorted(a)[len(a) // 2]))
            # 서술 — 긴 창
            ol, bl, al, _lw, _m, _s = IR.solve(rows, jl, "rev", cap, TE, False)
            sl = IR.ev(ol)
            print("   (서술) 긴 창 %s~ %d개월: IR %+.3f · t %.2f · 비용 뒤 IR %+.3f"
                  % (rows[jl]["m"], sl["n"], sl["ir"], sl["t"], sl["ir_net"]))
            x = rows[-1]
            act = sorted(((t, lw.get(t, 0.0) - x["wb"][t]) for t in x["names"]), key=lambda z: -z[1])
            V[cap] = {"metrics": s, "bind": round(bind, 2), "bind_w": round(100 * b[2], 2),
                      "placebo_ir": round(pl["ir"], 4), "lam_mult": round(mult, 4), "saturated": bool(sat),
                      "f1": bool(f1), "f2": bool(f2), "f3": bool(f3), "f4": bool(f4), "f5": bool(f5), "f6": bool(f6),
                      "verdict": verdict,
                      "active_median": round(100 * sorted(a)[len(a) // 2], 2),
                      "long": {"start": rows[jl]["m"], "n": sl["n"], "ir": round(sl["ir"], 4),
                               "t": round(sl["t"], 3), "ir_net": round(sl["ir_net"], 4)},
                      "now": {"over": [[t, round(100 * v, 3)] for t, v in act[:10]],
                              "under": [[t, round(100 * v, 3)] for t, v in act[-10:]]}}
        RESULT["idx"][ix] = {"label": lab, "window": [rows[j0]["m"], rows[-1]["m"]], "months": len(rows) - j0,
                             "f0": {"ok": f0_ok, "corr": f0_corr, "gap_pm": f0_gap},
                             "cover_min": min(cover), "cover_med": float(np.median(cover)),
                             "eg_cov_med": float(np.median([x["cov"]["eg"] for x in rows[j0:]])), "cells": V}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(RESULT, ensure_ascii=False, indent=1) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
