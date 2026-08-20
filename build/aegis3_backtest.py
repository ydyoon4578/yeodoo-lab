# -*- coding: utf-8 -*-
"""build/aegis3_backtest.py — 이지스 3판(NDX 코어 + 편입비 밴드 90~110%) → data/aegis3.json

규약: build/PREREG-2026-08-19-AEGIS3.md (계산 전 커밋 · 예측 P1~P5 포함).
밴드 90~110% 는 사용자 지시 상수(2026-08-19) — 표본에서 스캔하지 않았다.

  편입비: 주말 종가에 ^NDX ≥ MA200 → 110%, 아니면 90%.
  조달: (편입비−100%)⁺ × 실측 rf(FRED DGS3MO 월복리 → 주 환산) 매주 차감.
  현금(90% 구간의 10%)은 0% — 보수 방향 비대칭(§0).

    python build/aegis3_backtest.py
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
OUT = os.path.join(DATA, "aegis3.json")
E_UP, E_DN = 1.10, 0.90
COST_BP = 5
START = "2015-01"


def load_rf():
    d = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))
    return d["monthly"]                      # {"YYYY-MM": 월복리}


def engine3(dts, bench, we, bsig, rf, e_up=E_UP, e_dn=E_DN,
            hold_key="ndx", shield_key="ndx", monthly=False,
            cost_bp=COST_BP, fin_mult=1.0):
    cost = cost_bp / 10000.0
    b = bench[hold_key]
    nav = 100.0
    e_prev, state = None, None
    daily_d, daily_v = [], []
    wk_ret, wk_e, wk_d = [], [], []
    fin_paid = 0.0                           # 조달비 누계(NAV 대비 근사 합)
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
            state = e_up if (d200 is not None and d200 >= 0) else e_dn
        e = state
        c = cost * abs(e - (e_prev if e_prev is not None else 0.0))
        rf_m = rf.get(ym) or 0.0
        fin = max(0.0, e - 1.0) * ((1 + rf_m) ** (12.0 / 52.0) - 1) * fin_mult
        fin_paid += fin
        nav0 = nav * (1 - c) * (1 - fin)
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
            "wk_e": wk_e, "wk_d": wk_d, "fin_paid": fin_paid}


def dn_periods(wk_d, wk_e):
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
    # 🚨 동결 가드(2026-08-20 점검) — 얼린 사전등록 산출물을 무심코 덮지 못하게 한다.
    #   재동결은 자료 정정 등 사유가 있을 때 --refreeze 로만, 사유는 커밋 메시지·장부에.
    if os.path.exists(OUT) and "--refreeze" not in sys.argv:
        raise SystemExit("%s 가 이미 있다 — 얼린 측정이다. 재동결은 --refreeze 로만." % OUT)
    dts, _px, bench = load_px()
    we = week_ends(dts)
    bsig = Sig(bench, len(dts))
    rf = load_rf()

    C = engine3(dts, bench, we, bsig, rf)
    mc = metrics(C["daily_d"], C["daily_v"], C["wk_ret"])
    avg_e = sum(C["wk_e"]) / len(C["wk_e"])
    yrs_span = (dt.date.fromisoformat(C["daily_d"][-1])
                - dt.date.fromisoformat(C["daily_d"][0])).days / 365.25
    fin_pp_yr = C["fin_paid"] / yrs_span * 100
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

    exs = [r - w for r, w in zip(C["wk_ret"], bm["ndx"]["wk"])]
    m5, t5 = tstat(exs)

    yrs_a = year_table(C["daily_d"], C["daily_v"])
    p4_gap = yrs_a.get("2022", 0) - bm["ndx"]["years"].get("2022", 0)
    u4_gap = round(mc["cagr"] - bm["ndx"]["cagr"], 2)
    pred = {
        "P1_u4": {"pred": "U4 통과 · 격차 +0.7~+2.2%p", "gap": u4_gap,
                  "pass": bool(gates["U4"]["pass"] and 0.7 <= u4_gap <= 2.2)},
        "P2_u3_close": {"pred": "MDD −30~−35% (U3 접전)", "mdd": mc["mdd"],
                        "pass": bool(-35 <= mc["mdd"] <= -30)},
        "P3_sharpe": {"pred": "샤프 0.93~1.00", "sharpe": mc["sharpe"],
                      "pass": bool(0.93 <= mc["sharpe"] <= 1.00)},
        "P4_2022": {"pred": "2022년 NDX 대비 +2~+5%p", "gap_pp": round(p4_gap, 1),
                    "pass": bool(2 <= p4_gap <= 5)},
        "P5_spx_ret_sharpe": {"pred": "U1·U2 통과",
                              "pass": bool(gates["U1"]["pass"] and gates["U2"]["pass"])},
    }

    sens = {}
    for name, kw in (("defense_only", {"e_up": 1.0}), ("lever_only", {"e_dn": 1.0}),
                     ("monthly", {"monthly": True}), ("shield_spx", {"shield_key": "spx"}),
                     ("cost20", {"cost_bp": 20}), ("fin_x2", {"fin_mult": 2.0})):
        r = engine3(dts, bench, we, bsig, rf, **kw)
        sens[name] = metrics(r["daily_d"], r["daily_v"], r["wk_ret"])

    dnp = dn_periods(C["wk_d"], C["wk_e"])
    n_dn = sum(1 for e in C["wk_e"] if e < 1.0)
    print("이지스3 · %s ~ %s · 주 %d회 · 90%% 구간 %d주 (%.0f%%) · 평균 편입비 %.3f · 조달 %.2f%%p/yr"
          % (C["daily_d"][0], C["daily_d"][-1], len(C["wk_ret"]), n_dn,
             100 * n_dn / len(C["wk_e"]), avg_e, fin_pp_yr))
    print("%-14s %8s %8s %8s %8s" % ("", "CAGR%", "Vol%", "Sharpe", "MDD%"))
    print("%-14s %8.2f %8.2f %8.2f %8.2f  (배당보정 %.2f)"
          % ("이지스3", mc["cagr"], mc["vol"], mc["sharpe"], mc["mdd"], strat_div_adj))
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
        print("  %-18s %s %s" % (k, "✅" if v["pass"] else "❌",
                                 {a: b for a, b in v.items() if a != "pass"}))
    print("90% 구간:", dnp)
    print("민감도:")
    for k, v in sens.items():
        print("  %-13s CAGR %6.2f · Sharpe %5.2f · MDD %6.2f" % (k, v["cagr"], v["sharpe"], v["mdd"]))

    for key in ("spx", "ndx"):
        bm[key].pop("wk", None)
    doc = {
        "note": "이지스 3판 — ^NDX 코어 + 편입비 밴드 90~110%(200일선 위 110 · 아래 90). "
                "밴드는 사용자 지시 상수(2026-08-19). 조달은 실측 rf(FRED DGS3MO)로 차감, "
                "90% 구간 현금은 0%(보수 비대칭). 판정은 사용자 6문 — "
                "PREREG-2026-08-19-AEGIS3.md 에 예측 5건과 함께 계산 전 커밋. 3번째 시도(§0).",
        "prereg": "build/PREREG-2026-08-19-AEGIS3.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"e_up": E_UP, "e_dn": E_DN, "ma_td": 200, "cost_bp": COST_BP,
                   "start": START, "rf": "FRED DGS3MO 월복리 → 주 환산"},
        "span": [C["daily_d"][0], C["daily_d"][-1]], "weeks": len(C["wk_ret"]),
        "dn_weeks": n_dn, "avg_exposure": round(avg_e, 3),
        "financing_pp_yr": round(fin_pp_yr, 2),
        "strat": dict(mc, cagr_div_adj=strat_div_adj),
        "bench": bm, "gates": gates, "n_pass": n_pass, "n_pass_div_adj": n_pass_adj,
        "spx3": bool(spx_3), "spx3_div_adj": bool(spx_3_adj), "verdict": verdict,
        "predictions": pred,
        "ref_panel": {"weekly_ex_vs_ndx_bp": round(m5 * 10000, 1), "t": round(t5, 2)},
        "years": {"aegis3": yrs_a, "spx": bm["spx"]["years"], "ndx": bm["ndx"]["years"]},
        "dn_periods": dnp, "sens": sens,
        "last_week": {"date": C["wk_d"][-1], "exposure": C["wk_e"][-1]},
        "weekly": {"d": C["wk_d"], "ret": [round(x, 6) for x in C["wk_ret"]], "e": C["wk_e"]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
