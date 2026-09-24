# -*- coding: utf-8 -*-
"""build/stoploss.py — 12-1 모멘텀 상위 10 에 −8% 손절 시점정확 검정 → data/_stoploss.json

사전등록: build/PREREG-2026-09-24-STOPLOSS.md (계산 전 커밋 cbb879ef)

기저는 랩 `x-mom12` 그대로(점수 = 252일 수익 − 21일 수익 · 상위 10 동일가중 · 월말 종가 리밸런스)를 시점정확 패널에서 다시 만들고,
그 위에 «처음 산 값 대비 −8% 면 다음 날 종가에 팔고 월말까지 현금» 을 얹는다. 두 판을 **같은 일간 엔진**으로 돌린다.

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
⚠ 사전등록이 정하지 않은 구현 세부는 결과 문서 «정하지 않은 자리» 에 적는다(여기 주석에도 표시).

  python build/stoploss.py
"""
from __future__ import annotations
import io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402  시점정확 패널(명단·키·이중클래스·재배정)
import rally_pattern as RP            # noqa: E402  nw_t 한 벌

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_stoploss.json")

F0M, F1M = "2016-08", "2026-07"       # 형성 월말 — 보유 2016-09 ~ 2026-08 (사전등록 §1)
TOPN, COST, STOP = 10, 0.0020, 0.08
NW_LAG = 3


def ret(p, i, n):
    """랩 tech_backtest.ret 과 같은 뜻 — 정확한 자리 · 결측·비양수면 None(여기 배열은 NaN 을 쓴다)."""
    if i - n < 0:
        return None
    a, b = p[i - n], p[i]
    if not (a == a and b == b) or a <= 0 or b <= 0:
        return None
    return b / a - 1.0


def last_valid(p, j, lo):
    """j 이하 lo 이상에서 마지막 유효 가격(없으면 None)."""
    for x in range(j, lo - 1, -1):
        if p[x] == p[x] and p[x] > 0:
            return p[x]
    return None


def simulate(W, months, picks, RF, stop=None, reset_monthly=False, cost=COST):
    """일간 엔진. stop=None 이면 기저. 반환: 월 기록 목록."""
    PX, me = W["PX"], W["me"]
    cash, pos = 1.0, {}             # pos[k] = {"u": 수량, "E": 기준가, "last": 마지막 유효 가격 자리}
    rows = []
    for m in months:
        i = me[m]
        m1 = PP.mshift(m, 1)
        i1 = me[m1]
        # ── 월말 i 리밸런스 ────────────────────────────────────────────────
        val = {k: pos[k]["u"] * (last_valid(PX[k], i, pos[k]["last"]) or 0.0) for k in pos}
        V = cash + sum(val.values())
        tgt = [k for k in picks[m] if PX[k][i] == PX[k][i] and PX[k][i] > 0]
        tv = V / TOPN
        traded = sum(val.get(k, 0.0) for k in pos if k not in tgt)
        traded += sum(abs(tv - val.get(k, 0.0)) for k in tgt)
        c_rb = cost * traded
        V2 = V - c_rb
        tv2 = V2 / TOPN
        newpos = {}
        for k in tgt:
            keepE = (k in pos) and (not reset_monthly)
            newpos[k] = {"u": tv2 / PX[k][i], "E": (pos[k]["E"] if keepE else PX[k][i]), "last": i}
        cash = V2 - tv2 * len(tgt)          # 살 수 없던 칸은 현금
        pos = newpos
        # ── 일간 i+1 .. i1 ────────────────────────────────────────────────
        nd = i1 - i
        rf_d = (1.0 + float(RF.get(m1, 0.0))) ** (1.0 / max(1, nd)) - 1.0
        stops, c_st, pending = [], 0.0, {}
        for d in range(i + 1, i1 + 1):
            cash *= (1.0 + rf_d)
            # 전날 걸린 손절을 오늘 종가에 판다
            for k in list(pending):
                pk = PX[k][d]
                if not (pk == pk and pk > 0):
                    if d < i1:
                        continue            # 값이 없는 날은 미룬다(정하지 않은 자리)
                    pk = last_valid(PX[k], d, pos[k]["last"])
                v = pos[k]["u"] * pk
                c_st += cost * v
                cash += v - cost * v
                stops.append({"k": k, "sell": pk, "E": pos[k]["E"], "d": d})
                del pos[k]
                del pending[k]
            for k in pos:
                pk = PX[k][d]
                if pk == pk and pk > 0:
                    pos[k]["last"] = d
                    if stop is not None and d < i1 and k not in pending and pk <= (1.0 - stop) * pos[k]["E"]:
                        pending[k] = d      # 월말 당일에 걸린 것은 월말 리밸런스가 정한다(정하지 않은 자리)
        V_end = cash + sum(pos[k]["u"] * (last_valid(PX[k], i1, pos[k]["last"]) or 0.0) for k in pos)
        # 손절 뒤 반등 — 판 값보다 월말 값이 높았나(서술)
        reb = [1 if (last_valid(PX[s["k"]], i1, s["d"]) or 0) > s["sell"] else 0 for s in stops]
        rows.append({"m": m1, "V0": V, "V1": V_end, "r": V_end / V - 1.0, "rf": float(RF.get(m1, 0.0)),
                     "turn": traded / V if V > 0 else 0.0,          # 리밸런스 양쪽 거래액 ÷ 가치(손절 매도는 stop_turn)
                     "stop_val": sum(1 for _ in stops), "cost": c_rb + c_st, "rebound": reb,
                     "stop_turn": (c_st / cost) / V if (V > 0 and cost > 0) else 0.0})
    return rows


def summarize(rows):
    r = np.array([x["r"] for x in rows])
    rf = np.array([x["rf"] for x in rows])
    nav = np.cumprod(1 + r)
    ex = r - rf
    return {"cagr": float((nav[-1] ** (12.0 / len(r)) - 1) * 100), "vol": float(r.std(ddof=1) * math.sqrt(12) * 100),
            "sharpe": float(ex.mean() / ex.std(ddof=1) * math.sqrt(12)), "mdd": float(np.min(nav / np.maximum.accumulate(nav) - 1) * 100),
            "worst": float(r.min() * 100), "best": float(r.max() * 100),
            "turn_oneway_yr": float(np.mean([x["turn"] + x["stop_turn"] for x in rows]) / 2 * 12),
            "n_stops": int(sum(x["stop_val"] for x in rows))}


def main() -> int:
    t0 = time.time()
    W = PP.load_world()
    dates, PX, me = W["dates"], W["PX"], W["me"]
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))["monthly"]
    months = [m for m in sorted(me) if F0M <= m <= F1M]
    # ── 기저의 선택(랩 x-mom12) — 월마다 한 번 ──────────────────────────────
    picks, npool = {}, []
    for m in months:
        i = me[m]
        mem, _ = PP.union_members(W, m, i)
        sc = []
        for t, k in mem:
            a = ret(PX[k], i, 252)
            if a is None:
                continue
            b = ret(PX[k], i, 21)
            sc.append((a - (b or 0.0), t, k))
        sc.sort(key=lambda x: (-x[0], x[1]))
        picks[m] = [k for _, _, k in sc[:TOPN]]
        npool.append(len(sc))
    print("선택 %d개월 · 후보 중앙 %d (%.0fs)" % (len(months), int(np.median(npool)), time.time() - t0))

    base_g = simulate(W, months, picks, RF, stop=None, cost=0.0)
    base = simulate(W, months, picks, RF, stop=None)
    sl = simulate(W, months, picks, RF, stop=STOP)
    var = {"stop7": simulate(W, months, picks, RF, stop=0.07),
           "stop10": simulate(W, months, picks, RF, stop=0.10),
           "hzz10": simulate(W, months, picks, RF, stop=0.10, reset_monthly=True)}

    # ── F0 앵커 — 랩 시점정확 엔진의 x-mom12 월수익 ───────────────────────────
    PS = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    rows_ = PS.get("strategies") or []
    if isinstance(rows_, dict):
        rows_ = list(rows_.values())
    lab = [x for x in rows_ if x.get("sid") in ("x-mom12", "t-x-mom12")][0]
    labm = {x["m"]: x["r"] for x in (lab.get("chart") or {}).get("monthly") or []}
    pairs = [(x["r"] * 100, labm[x["m"]]) for x in base_g if x["m"] in labm]
    a = np.array(pairs)
    corr = float(np.corrcoef(a[:, 0], a[:, 1])[0, 1])
    gap = float(np.mean(a[:, 0] - a[:, 1]))
    F0 = bool(corr >= 0.95 and abs(gap) <= 0.30)

    Sb, Ss = summarize(base), summarize(sl)
    diff = np.array([y["r"] - x["r"] for x, y in zip(base, sl)])
    t_diff = RP.nw_t(diff, lag=NW_LAG)
    j = int(np.argmax(diff))
    rest = np.delete(diff, j)
    F1 = Ss["sharpe"] - Sb["sharpe"] > 0
    F2 = t_diff is not None and t_diff >= 1.5
    F3 = float(rest.mean()) > 0
    F4 = Ss["turn_oneway_yr"] <= 10.0
    if not F0:
        verdict = "측정 불가(F0)"
    elif F1 and F2 and F3 and F4:
        verdict = "게시 후보"
    elif F1 and F2:
        verdict = "보류"
    else:
        verdict = "기각"

    def window(rows, a_, z_):
        rr = [x["r"] for x in rows if a_ <= x["m"] <= z_]
        return float((np.prod([1 + v for v in rr]) - 1) * 100) if rr else None
    crash = {nm: {"base": window(base, a_, z_), "stop8": window(sl, a_, z_)}
             for nm, (a_, z_) in {"2020-02~03": ("2020-02", "2020-03"), "2022": ("2022-01", "2022-12")}.items()}
    reb = [v for x in sl for v in x["rebound"]]
    RESULT = {
        "prereg": "build/PREREG-2026-09-24-STOPLOSS.md", "prereg_commit": "cbb879ef",
        "window": [base[0]["m"], base[-1]["m"]], "n_months": len(base), "cost_bp": COST * 1e4, "stop": STOP,
        "f0_anchor": {"ok": F0, "corr": corr, "gap_pm": gap, "n": len(pairs)},
        "base": Sb, "stop8": Ss, "variants": {k: summarize(v) for k, v in var.items()},
        "base_gross": summarize(base_g),
        "diff": {"mean_pm": float(diff.mean() * 100), "t_nw3": t_diff, "win": float(np.mean(diff > 0) * 100),
                 "best_month": base[j]["m"], "best_pp": float(diff[j] * 100), "mean_ex_best_pm": float(rest.mean() * 100)},
        "sharpe_diff": Ss["sharpe"] - Sb["sharpe"],
        "crash_pct": crash, "rebound_share": (float(np.mean(reb)) if reb else None), "n_stops": len(reb),
        "F": {"F0": F0, "F1": F1, "F2": F2, "F3": F3, "F4": F4}, "verdict": verdict,
        "monthly": [{"m": x["m"], "base": round(x["r"] * 100, 4), "stop8": round(y["r"] * 100, 4)} for x, y in zip(base, sl)],
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(RESULT, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")

    f = lambda v, d=2: "—" if v is None else "%.*f" % (d, v)
    print("\n== %s ~ %s (%d개월 · 편도 %dbp)" % (RESULT["window"][0], RESULT["window"][1], len(base), COST * 1e4))
    print("  F0 앵커: 랩 x-mom12 과 상관 %.4f · 월 차이 %+.3f%%p (%d개월) → %s" % (corr, gap, len(pairs), F0))
    for nm, s in (("기저 x-mom12", Sb), ("손절 −8%", Ss)) + tuple(("(서술) " + k, summarize(v)) for k, v in var.items()):
        print("  %-16s CAGR %6.2f%% · 변동 %5.1f%% · 샤프 %.3f · MDD %6.1f%% · 최악 달 %6.1f%% · 회전 %.1f배 · 손절 %d" % (
            nm, s["cagr"], s["vol"], s["sharpe"], s["mdd"], s["worst"], s["turn_oneway_yr"], s["n_stops"]))
    print("  F1 샤프 차 %+.3f → %s · F2 월 차이 %+.3f%% · t %s → %s · F3 최고 달(%s %+.2f%%p) 빼면 %+.3f%% → %s · F4 %.1f배 → %s" % (
        Ss["sharpe"] - Sb["sharpe"], F1, diff.mean() * 100, f(t_diff), F2, base[j]["m"], diff[j] * 100, rest.mean() * 100, F3, Ss["turn_oneway_yr"], F4))
    print("  급락 구간:", crash, "· 손절 뒤 월말 반등 비율:", f(RESULT["rebound_share"], 3))
    print("⇒ 판정:", verdict)
    print("→ %s (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
