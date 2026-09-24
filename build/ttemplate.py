# -*- coding: utf-8 -*-
"""build/ttemplate.py — 미너비니 트렌드 템플릿 × RS 상위 10 시점정확 검정 → data/_ttemplate.json

사전등록: build/PREREG-2026-09-24-TTEMPLATE.md (계산 전 커밋 f899af77)

매월 말 그때의 S&P 500 ∪ NASDAQ 100 명단(편출 종목 포함)에서 8조건(종가·이평·52주 고저·RS 백분위)을 통과한 종목 중
RS 상위 10 을 동일가중으로 든다. 핵심 대조는 **같은 RS 상위 10(템플릿 없음)** — 템플릿이 RS 위에 더하는 것이 있나.

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
⚠ 사전등록이 정하지 않은 구현 세부는 결과 문서 «정하지 않은 자리» 에 적는다(여기 주석에도 표시).

  python build/ttemplate.py
"""
from __future__ import annotations
import io, json, math, os, sys, time

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402  시점정확 패널(명단·키·이중클래스·재배정)
import rally_pattern as RP            # noqa: E402  nw_t(Newey-West) 한 벌

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_ttemplate.json")

F0M, F1M = "2016-08", "2026-07"       # 형성 월말 — 사전등록 §1 (보유 2016-09 ~ 2026-08)
TOPN, RS_CUT = 10, 70.0
COST, COST_LO = 0.0020, 0.0010        # 편도 — 사고파는 양쪽에 매긴다(정하지 않은 자리: Σ|Δw| × 편도)
NW_LAG = 3


def feats(p):
    """종가 배열 → 템플릿 재료(길이 D). 최소 자료는 정하지 않은 자리 — 창 n 에서 5일까지 결측 허용."""
    s = pd.Series(p)
    sma50 = s.rolling(50, min_periods=45).mean()
    sma150 = s.rolling(150, min_periods=145).mean()
    sma200 = s.rolling(200, min_periods=195).mean()
    hi = s.rolling(252, min_periods=240).max()
    lo = s.rolling(252, min_periods=240).min()
    ff = s.ffill(limit=5)                          # Rn 의 기준가 — t−n 에 값이 없으면 5일 안의 앞 값(정하지 않은 자리)
    R = {n: (s / ff.shift(n) - 1.0) for n in (63, 126, 189, 252)}
    rs = 0.4 * R[63] + 0.2 * R[126] + 0.2 * R[189] + 0.2 * R[252]
    return {"c": s.values, "s50": sma50.values, "s150": sma150.values, "s200": sma200.values,
            "s200l": sma200.shift(21).values, "hi": hi.values, "lo": lo.values, "rs": rs.values}


def hold_ret(p, e0, e1):
    """다음 거래일 종가에 사서 다음 달 같은 자리까지. 사는 날 값이 없으면 5일 안의 첫 값 · 끊기면 마지막 값."""
    st = None
    for j in range(e0, min(e0 + 5, e1)):
        if p[j] == p[j] and p[j] > 0:
            st = j
            break
    if st is None:
        return None
    seg = p[st:e1 + 1]
    ok = np.where(seg == seg)[0]
    return float(p[st + ok[-1]] / p[st] - 1.0)


def stats(r, rf):
    r, rf = np.asarray(r, float), np.asarray(rf, float)
    n = len(r)
    nav = np.cumprod(1 + r)
    cagr = nav[-1] ** (12.0 / n) - 1
    ex = r - rf
    sh = ex.mean() / ex.std(ddof=1) * math.sqrt(12) if ex.std(ddof=1) > 0 else None
    dd = float(np.min(nav / np.maximum.accumulate(nav) - 1))
    return {"cagr": cagr * 100, "vol": float(r.std(ddof=1) * math.sqrt(12) * 100), "sharpe": sh,
            "mdd": dd * 100, "worst": float(r.min() * 100), "n": n}


def main() -> int:
    t0 = time.time()
    W = PP.load_world()
    dates, D, PX, me = W["dates"], W["D"], W["PX"], W["me"]
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))["monthly"]
    Bj = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bidx = {d: i for i, d in enumerate(Bj["dates"])}
    spx = pd.Series([np.nan if (bidx.get(d) is None or Bj["series"]["spx"]["px"][bidx[d]] is None)
                     else float(Bj["series"]["spx"]["px"][bidx[d]]) for d in dates]).ffill().values
    FT = {k: feats(PX[k]) for k in PX}
    print("재료 %d종 (%.0fs)" % (len(FT), time.time() - t0))

    months = [m for m in sorted(me) if F0M <= m <= F1M]
    today = sorted(W["today"])

    def today_members():
        by_cik = {}
        for t in today:
            c = W["cikmap"].get(t) or W["cikmap"].get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        out = []
        for c, ts in by_cik.items():
            if len(ts) == 1 or c.startswith("_"):
                out.extend(ts)
                continue
            k_ = [t for t in ts if t in PP.KEEP_DUAL]
            out.append(k_[0] if k_ else sorted(ts)[0])
        return [(t, t) for t in sorted(out)]

    TODAY = today_members()

    def run(mode):
        rows = []
        prev = {"tt": {}, "c1": {}, "c2": {}, "all": {}}
        for m in months:
            i = me[m]
            m1 = PP.mshift(m, 1)
            i1 = me[m1]
            e0, e1 = i + 1, i1 + 1
            if e1 > D - 1:
                raise SystemExit("🚨 %s 의 보유 끝이 자료 밖이다" % m)
            mem, n_mem = PP.union_members(W, m, i) if mode == "pit" else (TODAY, len(TODAY))
            el = []
            for t, k in mem:
                f = FT[k]
                vals = [f[x][i] for x in ("c", "s50", "s150", "s200", "s200l", "hi", "lo", "rs")]
                if any(v != v for v in vals) or not (f["c"][i] > 0):
                    continue
                el.append((t, k) + tuple(vals))
            if len(el) < 50:
                raise SystemExit("🚨 %s 자격 종목 %d — 패널을 볼 것" % (m, len(el)))
            rsv = np.array([x[9] for x in el])
            pct = pd.Series(rsv).rank(pct=True, method="average").values * 100.0
            passed = []
            for (t, k, c, s50, s150, s200, s200l, hi, lo, rs), pc in zip(el, pct):
                ok = (c > s150 and c > s200 and s150 > s200 and s200 > s200l and s50 > s150 and s50 > s200
                      and c > s50 and c >= 1.30 * lo and c >= 0.75 * hi and pc >= RS_CUT)
                if ok:
                    passed.append((rs, t, k))
            passed.sort(key=lambda x: -x[0])
            rs_all = sorted([(x[9], x[0], x[1]) for x in el], key=lambda x: -x[0])
            books = {"tt": [(t, k) for _, t, k in passed[:TOPN]],
                     "c1": [(t, k) for _, t, k in rs_all[:TOPN]],
                     "all": [(t, k) for _, t, k in passed],
                     "c2": [(x[0], x[1]) for x in el]}
            rf = float(RF.get(m1, 0.0))
            out = {"m": m1, "sig": m, "n_mem": n_mem, "n_el": len(el), "n_pass": len(passed),
                   "tt_names": [t for t, _ in books["tt"]], "sec": {}}   # 🚨 "tt" 는 아래 성적 칸이 쓴다(첫 판에서 명단을 덮었다 — 서술 칸만)
            for b, lst in books.items():
                slots = TOPN if b in ("tt", "c1") else max(1, len(lst))
                w, rets = {}, {}
                for t, k in lst:
                    r = hold_ret(PX[k], e0, e1)
                    if r is None:
                        continue                     # 살 수 없으면 그 칸은 현금(정하지 않은 자리)
                    w[k] = 1.0 / slots
                    rets[k] = r
                cash = 1.0 - sum(w.values())
                gross = sum(w[k] * rets[k] for k in w) + cash * rf
                # 회전율 — 직전 달 비중이 수익만큼 흘러간 뒤와 새 비중의 차(현금 칸은 세지 않는다)
                pw, pr, pg = prev[b].get("w", {}), prev[b].get("r", {}), prev[b].get("g", 0.0)
                drift = {k: pw[k] * (1 + pr[k]) / (1 + pg) for k in pw} if pw else {}
                keys = set(drift) | set(w)
                turn = sum(abs(w.get(k, 0.0) - drift.get(k, 0.0)) for k in keys)
                out[b] = {"g": gross, "turn": turn, "n": len(w), "cash": cash}
                prev[b] = {"w": w, "r": rets, "g": gross}
            # 서술 — 템플릿 보유의 섹터
            for t, k in books["tt"]:
                s = PP._sector(W, t, k)
                out["sec"][s] = out["sec"].get(s, 0) + 1
            out["rf"] = rf
            out["spx"] = float(spx[e1] / spx[e0] - 1.0)
            rows.append(out)
        return rows

    res = {}
    for mode in ("pit", "retro"):
        rows = run(mode)
        rf = [x["rf"] for x in rows]
        ser = {}
        for b in ("tt", "c1", "c2", "all"):
            g = np.array([x[b]["g"] for x in rows])
            tv = np.array([x[b]["turn"] for x in rows])
            ser[b] = {"gross": g, "net": g - COST * tv, "net_lo": g - COST_LO * tv, "turn": tv}
        res[mode] = {"rows": rows, "ser": ser, "rf": rf}
        print("%s: %d개월 · 통과 중앙 %d종 (%.0fs)" % (mode, len(rows), int(np.median([x["n_pass"] for x in rows])), time.time() - t0))

    P, R = res["pit"], res["retro"]
    rf = np.array(P["rf"])
    S = {b: stats(P["ser"][b]["net"], rf) for b in ("tt", "c1", "c2", "all")}
    S_lo = {b: stats(P["ser"][b]["net_lo"], rf) for b in ("tt", "c1", "c2")}
    S_g = {b: stats(P["ser"][b]["gross"], rf) for b in ("tt", "c1", "c2")}
    Sr = {b: stats(R["ser"][b]["net"], np.array(R["rf"])) for b in ("tt", "c2")}
    spx_s = stats([x["spx"] for x in P["rows"]], rf)
    n_pass = [x["n_pass"] for x in P["rows"]]
    f0_share = float(np.mean([n >= 5 for n in n_pass]))
    ex_pit = S["tt"]["cagr"] - S["c2"]["cagr"]
    ex_retro = Sr["tt"]["cagr"] - Sr["c2"]["cagr"]
    diff = P["ser"]["tt"]["net"] - P["ser"]["c1"]["net"]
    t_diff = RP.nw_t(diff, lag=NW_LAG)
    turn_yr = float(np.mean(P["ser"]["tt"]["turn"]) / 2 * 12)       # 편도(= Σ|Δw| 의 절반) × 12
    ratio = (ex_retro / ex_pit) if ex_pit > 0 else None
    F0 = f0_share >= 0.80
    F1 = ex_pit > 0
    F2 = t_diff is not None and t_diff >= 1.5
    F3 = (ratio is not None and ratio < 2.0)
    F4 = turn_yr <= 10.0
    if not F0:
        verdict = "측정 불가(F0)"
    elif F1 and F2 and F3 and F4:
        verdict = "게시 후보"
    elif F1 and F2:
        verdict = "보류"
    else:
        verdict = "기각"
    # 서술 — 약세 구간
    def window(b, a, z):
        rr = [(x["m"], x[b]["g"]) for x in P["rows"] if a <= x["m"] <= z]
        return float((np.prod([1 + g for _, g in rr]) - 1) * 100) if rr else None
    bears = {nm: {b: window(b, a, z) for b in ("tt", "c1", "c2")} for nm, (a, z) in
             {"2020-02~03": ("2020-02", "2020-03"), "2022": ("2022-01", "2022-12")}.items()}
    secs = {}
    for x in P["rows"]:
        for s, c in x["sec"].items():
            secs[s] = secs.get(s, 0) + c
    tot = sum(secs.values()) or 1
    RESULT = {
        "prereg": "build/PREREG-2026-09-24-TTEMPLATE.md", "prereg_commit": "f899af77",
        "window": [P["rows"][0]["m"], P["rows"][-1]["m"]], "n_months": len(P["rows"]),
        "cost_bp": COST * 1e4,
        "pit": {b: S[b] for b in S}, "pit_cost10": S_lo, "pit_gross": S_g, "retro": Sr, "spx": spx_s,
        "excess_pit_pp": ex_pit, "excess_retro_pp": ex_retro, "retro_ratio": ratio,
        "diff_tt_c1": {"mean_pm": float(np.mean(diff) * 100), "t_nw3": t_diff,
                       "win": float(np.mean(diff > 0) * 100)},
        "turnover_oneway_yr": {b: float(np.mean(P["ser"][b]["turn"]) / 2 * 12) for b in ("tt", "c1", "c2")},
        "n_pass": {"median": float(np.median(n_pass)), "min": int(min(n_pass)), "max": int(max(n_pass)),
                   "share_ge5": f0_share, "share_ge10": float(np.mean([n >= 10 for n in n_pass])),
                   "n_el_median": float(np.median([x["n_el"] for x in P["rows"]])),
                   "n_mem_median": float(np.median([x["n_mem"] for x in P["rows"]]))},
        "cash_mean_tt": float(np.mean([x["tt"]["cash"] for x in P["rows"]])),
        "bears_pct": bears,
        "sector_share": {s: round(c / tot * 100, 1) for s, c in sorted(secs.items(), key=lambda kv: -kv[1])},
        "F": {"F0": F0, "F1": F1, "F2": F2, "F3": F3, "F4": F4},
        "verdict": verdict,
        "now": {"sig": P["rows"][-1]["sig"], "tt": P["rows"][-1]["tt_names"], "n_pass": P["rows"][-1]["n_pass"]},
        "monthly": [{"m": x["m"], "n_pass": x["n_pass"], "tt": round(x["tt"]["g"] * 100, 4),
                     "c1": round(x["c1"]["g"] * 100, 4), "c2": round(x["c2"]["g"] * 100, 4)} for x in P["rows"]],
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(RESULT, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")

    f = lambda v, d=2: "—" if v is None else "%.*f" % (d, v)
    print("\n== 시점정확 %s ~ %s (%d개월 · 비용 편도 %dbp)" % (RESULT["window"][0], RESULT["window"][1], len(P["rows"]), COST * 1e4))
    for b, nm in (("tt", "템플릿 × RS 상위 10"), ("c1", "C1 RS 상위 10"), ("c2", "C2 동일가중"), ("all", "(서술) 통과 전부")):
        s = S[b]
        print("  %-18s CAGR %6.2f%% · 변동 %5.1f%% · 샤프 %s · MDD %6.1f%% · 최악 달 %6.1f%%" % (nm, s["cagr"], s["vol"], f(s["sharpe"]), s["mdd"], s["worst"]))
    print("  S&P 500(PR)        CAGR %6.2f%% · 샤프 %s · MDD %6.1f%%" % (spx_s["cagr"], f(spx_s["sharpe"]), spx_s["mdd"]))
    print("  F0 통과 5종 이상 달 %.1f%% (중앙 %d종 · 최소 %d) → %s" % (f0_share * 100, np.median(n_pass), min(n_pass), F0))
    print("  F1 초과(대 C2) %+.2f%%p → %s" % (ex_pit, F1))
    print("  F2 템플릿 − C1 월 %+.3f%% · NW t %s → %s" % (np.mean(diff) * 100, f(t_diff), F2))
    print("  F3 소급 초과 %+.2f%%p ÷ 시점정확 %+.2f%%p = %s → %s" % (ex_retro, ex_pit, f(ratio), F3))
    print("  F4 연 편도 회전율 %.1f배 → %s" % (turn_yr, F4))
    print("  약세 구간:", bears)
    print("⇒ 판정:", verdict, " · 지금(%s) 통과 %d종: %s" % (RESULT["now"]["sig"], RESULT["now"]["n_pass"], ", ".join(RESULT["now"]["tt"])))
    print("→ %s (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
