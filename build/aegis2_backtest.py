# -*- coding: utf-8 -*-
"""build/aegis2_backtest.py — 이지스 2판(NDX 코어 + 부분 방패) → data/aegis2.json

규약: build/PREREG-2026-08-19-AEGIS2.md (계산 전 커밋 · 예측 P1~P5 포함).
판정은 사용자 6문 — vs SPX·NDX 각각 수익(CAGR)·샤프·MDD. 선언 BM(S&P500) 3/3 병기.

  보유: ^NDX(실물 QQQ). 노출: 주말 종가에 ^NDX ≥ MA200 → 100%, 아니면 50%.
  비용: 편도 5bp × 노출 변경분. 현금 0%. NAV 일간.

    python build/aegis2_backtest.py
"""
from __future__ import annotations
import datetime as dt
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aegis_backtest import (load_px, week_ends, Sig, metrics, bench_track,   # noqa: E402
                            tstat, year_table, DIV_ADJ)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "aegis2.json")
FLOOR = 0.5
COST_BP = 5
START = "2015-01"


def engine2(dts, bench, we, bsig, hold_key="ndx", shield_key="ndx",
            floor=FLOOR, monthly=False, cost_bp=COST_BP):
    """지수 코어 + 부분 방패 — 노출 e ∈ {1.0, floor}."""
    cost = cost_bp / 10000.0
    b = bench[hold_key]
    nav = 100.0
    e_prev, state = None, None
    daily_d, daily_v = [], []
    wk_ret, wk_e, wk_d = [], [], []
    for k in range(len(we) - 1):
        i0, i1 = we[k], we[k + 1]
        ym = dts[i0][:7]
        if ym < START:
            continue
        if b[i0] is None or b[i1] is None:
            continue
        upd = (state is None) or (not monthly) or (dts[i1][:7] != ym)
        if upd:
            d200 = bsig.dist(shield_key, i0)
            state = 1.0 if (d200 is not None and d200 >= 0) else floor
        e = state
        c = cost * abs(e - (e_prev if e_prev is not None else 0.0))
        nav0 = nav * (1 - c)
        if not daily_d:
            daily_d.append(dts[i0]); daily_v.append(nav0)
        for d in range(i0 + 1, i1 + 1):
            bd = b[d] if b[d] is not None else b[i0]
            daily_d.append(dts[d])
            daily_v.append(nav0 * (1 + e * (bd / b[i0] - 1)))
        new_nav = daily_v[-1]
        wk_ret.append(new_nav / nav - 1)
        wk_e.append(e)
        wk_d.append(dts[i0])
        nav = new_nav
        e_prev = e
    return {"daily_d": daily_d, "daily_v": daily_v, "wk_ret": wk_ret,
            "wk_e": wk_e, "wk_d": wk_d}


def half_periods(wk_d, wk_e):
    out, start = [], None
    for d, e in zip(wk_d, wk_e):
        if e < 1.0 and start is None:
            start = d
        elif e >= 1.0 and start is not None:
            out.append([start, d]); start = None
    if start is not None:
        out.append([start, wk_d[-1] + "~"])
    return out


def main() -> int:
    dts, _px, bench = load_px()
    we = week_ends(dts)
    bsig = Sig(bench, len(dts))

    C = engine2(dts, bench, we, bsig)
    mc = metrics(C["daily_d"], C["daily_v"], C["wk_ret"])
    avg_e = sum(C["wk_e"]) / len(C["wk_e"])
    strat_div_adj = round(mc["cagr"] + DIV_ADJ["ndx"] * avg_e, 2)

    bm = {}
    for key in ("spx", "ndx"):
        dd, dv, wk = bench_track(dts, bench, key, C["daily_d"], we)
        bm[key] = metrics(dd, dv, wk)
        bm[key]["cagr_div_adj"] = round(bm[key]["cagr"] + DIV_ADJ[key], 2)
        bm[key]["years"] = year_table(dd, dv)
        bm[key]["wk"] = wk

    gates = {}
    for key, tag in (("spx", ("U1", "U2", "U3")), ("ndx", ("U4", "U5", "U6"))):
        b = bm[key]
        gates[tag[0]] = {"q": "CAGR>" + key.upper(),
                         "strat": mc["cagr"], "strat_div_adj": strat_div_adj,
                         "bm": b["cagr"], "bm_div_adj": b["cagr_div_adj"],
                         "pass": bool(mc["cagr"] > b["cagr"]),
                         "pass_div_adj": bool(strat_div_adj > b["cagr_div_adj"])}
        gates[tag[1]] = {"q": "Sharpe>" + key.upper(), "strat": mc["sharpe"], "bm": b["sharpe"],
                         "pass": bool(mc["sharpe"] > b["sharpe"])}
        gates[tag[2]] = {"q": "MDD<" + key.upper(), "strat": mc["mdd"], "bm": b["mdd"],
                         "pass": bool(abs(mc["mdd"]) < abs(b["mdd"]))}
    n_pass = sum(1 for v in gates.values() if v["pass"])
    n_pass_adj = sum(1 for v in gates.values() if v.get("pass_div_adj", v["pass"]))
    spx_3 = all(gates[k]["pass"] for k in ("U1", "U2", "U3"))
    spx_3_adj = all(gates[k].get("pass_div_adj", gates[k]["pass"]) for k in ("U1", "U2", "U3"))
    verdict = ("통과 (6/6)" if n_pass == 6 else
               ("선언 BM(S&P500) 3/3 통과 · 전체 %d/6" % n_pass) if spx_3 else
               "미달 (%d/6)" % n_pass)

    # 참고 — vs NDX 주간 초과
    exs = [r - w for r, w in zip(C["wk_ret"], bm["ndx"]["wk"])]
    m5, t5 = tstat(exs)

    # 예측 채점(§3 — 계산 전 커밋분)
    yrs_a = year_table(C["daily_d"], C["daily_v"])
    p4_gap = yrs_a.get("2022", 0) - bm["ndx"]["years"].get("2022", 0)
    pred = {
        "P1_spx3": {"pred": "vs SPX 3/3 통과", "pass": bool(spx_3)},
        "P2_u4_close": {"pred": "U4 차이 ±1%p 안", "gap": round(mc["cagr"] - bm["ndx"]["cagr"], 2),
                        "pass": bool(abs(mc["cagr"] - bm["ndx"]["cagr"]) <= 1.0)},
        "P3_mdd_range": {"pred": "MDD −22~−30%", "mdd": mc["mdd"],
                         "pass": bool(-30 <= mc["mdd"] <= -22)},
        "P4_2022_defense": {"pred": "2022년 NDX 대비 +8%p 이상", "gap_pp": round(p4_gap, 1),
                            "pass": bool(p4_gap >= 8)},
        "P5_sharpe_ndx": {"pred": "U5 통과", "pass": bool(gates["U5"]["pass"])},
    }

    # 민감도(§5 고정)
    sens = {}
    for name, kw in (("floor0", {"floor": 0.0}), ("floor25", {"floor": 0.25}),
                     ("monthly", {"monthly": True}), ("shield_spx", {"shield_key": "spx"}),
                     ("cost20", {"cost_bp": 20})):
        r = engine2(dts, bench, we, bsig, **kw)
        sens[name] = metrics(r["daily_d"], r["daily_v"], r["wk_ret"])

    halfp = half_periods(C["wk_d"], C["wk_e"])
    n_half = sum(1 for e in C["wk_e"] if e < 1.0)
    print("이지스2 · %s ~ %s · 주 %d회 · 절반방어 %d주 (%.0f%%) · 평균노출 %.2f"
          % (C["daily_d"][0], C["daily_d"][-1], len(C["wk_ret"]), n_half,
             100 * n_half / len(C["wk_e"]), avg_e))
    print("%-14s %8s %8s %8s %8s" % ("", "CAGR%", "Vol%", "Sharpe", "MDD%"))
    print("%-14s %8.2f %8.2f %8.2f %8.2f  (배당보정 %.2f)"
          % ("이지스2", mc["cagr"], mc["vol"], mc["sharpe"], mc["mdd"], strat_div_adj))
    for key in ("spx", "ndx"):
        b = bm[key]
        print("%-14s %8.2f %8.2f %8.2f %8.2f  (배당보정 %.2f)"
              % ("BM " + key.upper(), b["cagr"], b["vol"], b["sharpe"], b["mdd"], b["cagr_div_adj"]))
    for k, v in gates.items():
        extra = "" if "pass_div_adj" not in v else (" · 배당보정 %s" % ("✅" if v["pass_div_adj"] else "❌"))
        print("  %s %-12s %s  전략 %s vs BM %s%s" % (k, v["q"], "✅" if v["pass"] else "❌",
                                                     v["strat"], v["bm"], extra))
    print("판정: %s (배당보정 %d/6 · 선언BM 3/3: %s)" % (verdict, n_pass_adj, "✅" if spx_3_adj else "—"))
    print("참고 — vs NDX 주간 초과 %+.3f%%p · t %.2f" % (m5 * 100, t5))
    print("예측 채점:")
    for k, v in pred.items():
        print("  %-16s %s %s" % (k, "✅" if v["pass"] else "❌",
                                 {a: b for a, b in v.items() if a != "pass"}))
    print("절반방어 구간:", halfp)
    print("민감도:")
    for k, v in sens.items():
        print("  %-12s CAGR %6.2f · Sharpe %5.2f · MDD %6.2f" % (k, v["cagr"], v["sharpe"], v["mdd"]))

    for key in ("spx", "ndx"):
        bm[key].pop("wk", None)
    doc = {
        "note": "이지스 2판 — ^NDX 코어(실물 QQQ) + 부분 방패(200일선 아래 50% 노출). "
                "판정은 사용자 6문 + 선언 BM(S&P500) 3/3 병기 — PREREG-2026-08-19-AEGIS2.md 에 "
                "예측 5건과 함께 계산 전 커밋. 사용자 기준 2번째 시도(다중검정 §0).",
        "prereg": "build/PREREG-2026-08-19-AEGIS2.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"floor": FLOOR, "ma_td": 200, "cost_bp": COST_BP, "start": START},
        "span": [C["daily_d"][0], C["daily_d"][-1]], "weeks": len(C["wk_ret"]),
        "half_weeks": n_half, "avg_exposure": round(avg_e, 3),
        "strat": dict(mc, cagr_div_adj=strat_div_adj),
        "bench": bm, "gates": gates, "n_pass": n_pass, "n_pass_div_adj": n_pass_adj,
        "spx3": bool(spx_3), "spx3_div_adj": bool(spx_3_adj), "verdict": verdict,
        "predictions": pred,
        "ref_panel": {"weekly_ex_vs_ndx_bp": round(m5 * 10000, 1), "t": round(t5, 2)},
        "years": {"aegis2": yrs_a, "spx": bm["spx"]["years"], "ndx": bm["ndx"]["years"]},
        "half_periods": halfp, "sens": sens,
        "last_week": {"date": C["wk_d"][-1], "exposure": C["wk_e"][-1]},
        "weekly": {"d": C["wk_d"], "ret": [round(x, 6) for x in C["wk_ret"]], "e": C["wk_e"]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
