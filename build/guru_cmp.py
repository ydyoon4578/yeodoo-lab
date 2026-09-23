# -*- coding: utf-8 -*-
"""build/guru_cmp.py — 거장 전략 압축·강화: «합의 점수» 지수 강화 틸트(시점정확) → data/_guru_cmp.json

사전등록: build/PREREG-2026-09-23-GURUCMP.md (계산 전 커밋 61894ace)

신호  S = ½·[z(수준) + z(변화)] — 수준 = 그 체결월에 그 종목을 든 운용사 수,
      변화 = 직전 체결월 대비 늘어난 수. 운용사 수는 guru_overlap_backtest.counts_by_quarter() 그대로
      (퀀트·분산 축 제외 · 공시일이 체결월 말보다 뒤인 운용사 제외 · 체결 = 분기말 + 2개월 월말).
패널  build/pit_panel.py — IDXEG 와 같은 시점정확 패널.
틀    idxrev.run·solve·ev 그대로 · TE 2% · 판정은 비중비례 한 칸.
🚨 매핑 없는 종목(13F 매핑이 오늘 518종만 덮는다 — 편출 종목 등)은 **중립**: 매핑 있는 종목의 점수를
   벤치 시총가중 평균 0 이 되게 다시 맞춰, 중립 종목의 틸트가 정확히 0 이 되게 한다(사전등록 §2).
🚨 얼린 측정 — CI 에 붙이지 않는다.

    python build/guru_cmp.py
"""
from __future__ import annotations
import datetime as dt
import io, json, math, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import idxrev as IR                   # noqa: E402  run·solve·ev·zsec 정본
import idxtilt as IT                  # noqa: E402  TE_JUDGE 정본
import pit_panel as PP                # noqa: E402  시점정확 패널(IDXEG 와 한 벌)
import guru_overlap_backtest as GO    # noqa: E402  counts_by_quarter 정본
from guru17_backtest import load as g_load   # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_guru_cmp.json")
JUDGE = ("2018-07", "2026-08")
LONG0 = "2016-09"
F_T = 1.5


def zs(d):
    v = np.array(list(d.values()), float)
    if len(v) < 3 or v.std(ddof=1) <= 0:
        return {k: 0.0 for k in d}
    m, s = v.mean(), v.std(ddof=1)
    return {k: (x - m) / s for k, x in d.items()}


def main() -> int:
    # ── 운용사 수(체결월 → {오늘 티커: 수}) ──────────────────────────────────
    G = g_load("guru_history.json")
    months, P = G["months"], G["mpx"]
    now_m = dt.date.today().strftime("%Y-%m")
    while months and months[-1] >= now_m:                # guru_overlap_backtest.main 과 같은 처리
        months = months[:-1]
    P = {t: v[:len(months)] for t, v in P.items()}
    mi = {m: i for i, m in enumerate(months)}
    counts, _qd = GO.counts_by_quarter(G, mi, P, months)
    reb = sorted(counts)
    print("체결월 %d개 · %s ~ %s" % (len(reb), reb[0], reb[-1]))

    def signal_at(mm):
        """신호월 mm 에 알 수 있는 최신 체결월의 (수준, 직전 체결월 수준)."""
        past = [r for r in reb if r <= mm]
        if len(past) < 2:
            return None, None
        return counts[past[-1]], counts[past[-2]]

    Wd = PP.load_world()
    today = Wd["today"]
    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))
    IDXM = CH["idx_monthly"]
    sig_months = [m for m in sorted(set(k[:7] for k in Wd["me"])) if "2016-08" <= m <= "2026-07"]

    RESULT = {"prereg": "build/PREREG-2026-09-23-GURUCMP.md", "prereg_commit": "61894ace",
              "judge": list(JUDGE), "long0": LONG0, "te_target": IT.TE_JUDGE, "idx": {}}
    for ix, lab in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        rows, cover = PP.month_rows(Wd, ix, sig_months, JUDGE[1])
        mapped_w = []
        for x in rows:
            cur, prev = signal_at(x["sig"])
            names = x["names"]
            # 13F 이력은 오늘 티커로 적혀 있다 — 과거 명단의 옛 티커는 승계된 오늘 티커(key)로 찾는다
            mp = [t for t in names if x["key"][t] in today]
            if cur is None:
                x["Z"] = {"rev": {}}
                x["cov"] = {"guru": 0.0}
                continue
            lev = {t: float(cur.get(x["key"][t], 0)) for t in mp}
            chg = {t: float(cur.get(x["key"][t], 0) - prev.get(x["key"][t], 0)) for t in mp}
            zl, zc = zs(lev), zs(chg)
            raw = {t: 0.5 * (zl[t] + zc[t]) for t in mp}
            z = IR.zsec(raw, x["sec"], names)
            # 🚨 중립 맞춤 — 매핑 있는 종목의 z 를 벤치 가중 평균 0 으로(매핑 없는 종목의 틸트가 정확히 0)
            wmp = sum(x["wb"][t] for t in z)
            c = (sum(x["wb"][t] * z[t] for t in z) / wmp) if wmp > 0 else 0.0
            x["Z"] = {"rev": {t: z[t] - c for t in z}}
            x["cov"] = {"guru": wmp}
            mapped_w.append(wmp)
        f0_ok, f0_corr, f0_gap = PP.f0_gate(rows, IDXM, lab, JUDGE)
        j0 = next(k for k, x in enumerate(rows) if x["m"] >= JUDGE[0])
        jl = next(k for k, x in enumerate(rows) if x["m"] >= LONG0)
        print("\n" + "=" * 74)
        print("══ %s ══  판정 창 %s ~ %s · %d개월" % (lab, rows[j0]["m"], rows[-1]["m"], len(rows) - j0))
        print("  명단 중 가격·주식수: 최저 %.1f%% · 중앙 %.1f%% · 13F 매핑(벤치 시총): 중앙 %.1f%% · 최저 %.1f%%"
              % (100 * min(cover), 100 * float(np.median(cover)), 100 * float(np.median(mapped_w)), 100 * min(mapped_w)))
        print("  F0 패널 벤치 vs %s(PR): 상관 %.4f · 차이 월 %+.3f%%p → %s"
              % (lab, f0_corr, f0_gap, "통과" if f0_ok else "🚨 무효"))

        TE = IT.TE_JUDGE
        V = {}
        for cap in ("prop", "abs"):
            o, b, a, lw, mult, sat = IR.solve(rows, j0, "rev", cap, TE, False)
            s = IR.ev(o)
            op, _b2, _a2, _lw2, _m2, _s2 = IR.solve(rows, j0, "rev", cap, TE, True)
            pl = IR.ev(op)
            bind = 100 * b[0] / max(1, b[1])
            f1 = bool(s["ir"] > 0 and s["t"] >= F_T)
            f2 = bool(s["ir_net"] > 0 and s["t_net"] >= F_T)
            f3 = bool(abs(s["te"] - 2.0) <= 1.0)
            f4 = bool(bind < 50.0)
            f5 = bool(pl["ir"] * s["ir"] < 0)
            f6 = bool(s["win"] > 50.0)
            judged = cap == "prop"                                   # 🚨 판정은 비중비례 한 칸(사전등록 §2)
            verdict = (None if not judged else "무효" if not f0_ok else "기각" if not (f1 and f2) else
                       "보류" if not (f3 and f4 and f5 and f6) else "게시 후보")
            ol, _b3, _a3, _lw3, _m3, _s3 = IR.solve(rows, jl, "rev", cap, TE, False)
            sl = IR.ev(ol)
            x = rows[-1]
            act = sorted(((t, lw.get(t, 0.0) - x["wb"][t]) for t in x["names"]), key=lambda z_: -z_[1])
            print("\n  ── %s · %s%s ──" % (lab, "비중비례" if cap == "prop" else "±1%p", " (판정)" if judged else " (서술)"))
            print("   초과 연 %+.2f%%p · TE %.2f%% · IR %+.3f · t %.2f · 비용 뒤 IR %+.3f · t %.2f · 월승률 %.1f%%%s"
                  % (s["ex"], s["te"], s["ir"], s["t"], s["ir_net"], s["t_net"], s["win"], " ⚠포화" if sat else ""))
            print("   한도걸림 %.1f%% · 위약 IR %+.3f · 긴 창 %s~ IR %+.3f · t %.2f"
                  % (bind, pl["ir"], rows[jl]["m"], sl["ir"], sl["t"]))
            if judged:
                print("   F1 %s · F2 %s · F3 %s · F4 %s · F5 %s · F6 %s  ⇒ %s"
                      % tuple(["통과" if f else "✗" for f in (f1, f2, f3, f4, f5, f6)] + [verdict]))
            print("   지금 더 담음: %s" % " · ".join("%s %+.2f%%p" % (t, 100 * v) for t, v in act[:6]))
            print("   지금 덜 담음: %s" % " · ".join("%s %+.2f%%p" % (t, 100 * v) for t, v in act[-6:]))
            V[cap] = {"judged": judged, "metrics": s, "bind": round(bind, 2), "placebo_ir": round(pl["ir"], 4),
                      "lam_mult": round(mult, 4), "saturated": bool(sat),
                      "f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5, "f6": f6, "verdict": verdict,
                      "long": {"start": rows[jl]["m"], "n": sl["n"], "ir": round(sl["ir"], 4), "t": round(sl["t"], 3)},
                      "now": {"over": [[t, round(100 * v, 3)] for t, v in act[:10]],
                              "under": [[t, round(100 * v, 3)] for t, v in act[-10:]]}}
        # ── §4 생존 편향의 크기(측정만) — 오늘 518종에 드는 멤버만 vs 그때 멤버 전체 ────────────
        sp = []
        for x in rows[jl:]:
            nm = x["names"]
            sv = [t for t in nm if x["key"][t] in today]
            vw_all = sum(x["wb"][t] * x["r"][t] for t in nm)
            ws = sum(x["wb"][t] for t in sv)
            vw_sv = sum(x["wb"][t] * x["r"][t] for t in sv) / ws if ws else vw_all
            ew_all = float(np.mean([x["r"][t] for t in nm]))
            ew_sv = float(np.mean([x["r"][t] for t in sv])) if sv else ew_all
            sp.append((100 * (vw_sv - vw_all), 100 * (ew_sv - ew_all), len(sv) / len(nm)))
        spv, spe = np.array([a for a, b, c in sp]), np.array([b for a, b, c in sp])
        tt = lambda v: float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))) if v.std(ddof=1) > 0 else None
        print("\n  §4 생존 편향(%s~ %d개월 · 측정만): 시총가중 월 %+.3f%%p (t %.2f) · 동일가중 월 %+.3f%%p (t %.2f) · 오늘 518종 비율 중앙 %.1f%%"
              % (rows[jl]["m"], len(sp), spv.mean(), tt(spv), spe.mean(), tt(spe), 100 * float(np.median([c for a, b, c in sp]))))
        RESULT["idx"][ix] = {"label": lab, "window": [rows[j0]["m"], rows[-1]["m"]], "months": len(rows) - j0,
                             "f0": {"ok": f0_ok, "corr": f0_corr, "gap_pm": f0_gap},
                             "cover_min": min(cover), "cover_med": float(np.median(cover)),
                             "mapped_w_med": float(np.median(mapped_w)), "mapped_w_min": float(min(mapped_w)),
                             "cells": V,
                             "survivor": {"start": rows[jl]["m"], "n": len(sp),
                                          "vw_pm": float(spv.mean()), "vw_t": tt(spv),
                                          "ew_pm": float(spe.mean()), "ew_t": tt(spe),
                                          "share_today_med": float(np.median([c for a, b, c in sp]))}}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(RESULT, ensure_ascii=False, indent=1) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
