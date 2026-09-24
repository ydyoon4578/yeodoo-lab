# -*- coding: utf-8 -*-
"""build/fund_mix.py — 펀드 적용(S&P 500 PR 90% + 바스켓 10%) 네 바스켓과 B·E·M 조합 → data/_fund_mix.json

사전등록: build/PREREG-2026-09-24-FUNDMIX.md (계산 전 커밋 78df5e15)
리포트 PDF 는 build/fund_mix_pdf.py 가 이 JSON 에서만 굽는다.

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다. ⚠ 정하지 않은 자리는 결과 문서에 적는다.

  python build/fund_mix.py
"""
from __future__ import annotations
import io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402
import stoploss as SL                 # noqa: E402  ret · last_valid (x-mom12 재현과 같은 함수)
import tech_backtest as TB            # noqa: E402  asof_all

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_fund_mix.json")
F0M, F1M, R3 = "2016-08", "2026-07", "2023-09"
COST, SLEEVE, CAP = 0.0010, 0.10, 0.20
# 급등락 구간 — 우량성장 30 리포트와 같은 12 구간(시작일 종가 → 끝일 종가)
EPIS = [("급락", "코로나19 팬데믹", "2020-02-19", "2020-03-16"), ("급등", "무제한 QE·재정부양 랠리", "2020-03-16", "2020-06-03"),
        ("급락", "2020년 9월 기술주 조정", "2020-09-02", "2020-09-23"), ("급등", "백신 기대·대선 불확실성 해소", "2020-09-23", "2020-12-01"),
        ("급락", "금리 급등 쇼크", "2021-02-12", "2021-03-08"), ("급등", "금리 안정 반등", "2021-03-08", "2021-04-09"),
        ("급락", "인플레이션·연준 급속 긴축", "2021-12-27", "2022-11-03"), ("급등", "생성형 AI 랠리", "2022-11-03", "2023-12-13"),
        ("급락", "엔 캐리 청산 쇼크", "2024-07-10", "2024-08-07"), ("급등", "연준 인하 개시 랠리", "2024-08-07", "2024-11-06"),
        ("급락", "관세 쇼크", "2025-02-19", "2025-04-08"), ("급등", "관세 유예·협상 진전 반등", "2025-04-08", "2025-06-24")]


def main() -> int:
    t0 = time.time()
    W = PP.load_world()
    dates, D, PX, me = W["dates"], W["D"], W["PX"], W["me"]
    di = {d: i for i, d in enumerate(dates)}
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))["monthly"]
    Bj = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bidx = {d: i for i, d in enumerate(Bj["dates"])}
    IX = np.array([np.nan if (bidx.get(d) is None or Bj["series"]["spx"]["px"][bidx[d]] is None)
                   else float(Bj["series"]["spx"]["px"][bidx[d]]) for d in dates])
    for j in range(1, D):
        if IX[j] != IX[j]:
            IX[j] = IX[j - 1]
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    DF = (A.get("macro") or {}).get("DFII10") or {}
    dfk = sorted(DF)
    EG = json.load(io.open(os.path.join(DATA, "_eg_q5_scores.json"), encoding="utf-8"))["months"]
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    NAME = {s["t"]: (s.get("name") or s["t"]) for s in S["stocks"]}
    all_m = sorted(me)
    months = [m for m in all_m if F0M <= m <= F1M]

    def mcap(t, k, i):
        sh = PP._shares(W, t, k, dates[i])
        p = PX[k][i]
        return (p * sh) if (sh and p == p and p > 0) else None

    def dfii(i):
        d = dates[i]
        lo, hi = 0, len(dfk) - 1
        if not dfk or dfk[0] > d:
            return None
        while lo < hi:                                   # d 이하 마지막 관측
            mid = (lo + hi + 1) // 2
            if dfk[mid] <= d:
                lo = mid
            else:
                hi = mid - 1
        v = DF[dfk[lo]]
        return None if v is None else float(v)

    # 월말 수익(알파용) — 달마다 월말 가격
    def mret(k, m):
        a, b = me[PP.mshift(m, -1)], me[m]
        pa = SL.last_valid(PX[k], a, max(0, a - 5))
        pb = SL.last_valid(PX[k], b, max(0, b - 5))
        return (pb / pa - 1.0) if (pa and pb) else None
    ixm = {m: IX[me[m]] / IX[me[PP.mshift(m, -1)]] - 1.0 for m in all_m if PP.mshift(m, -1) in me}

    # ── 바스켓 규칙 — 형성월 m → {키: 비중} (합 ≤ 1) ────────────────────────────
    def rule_M(m):
        i = me[m]
        sc = []
        for t, k in PP.union_members(W, m, i)[0]:
            a = SL.ret(PX[k], i, 252)
            if a is None:
                continue
            b = SL.ret(PX[k], i, 21)
            sc.append((a - (b or 0.0), t, k))
        sc.sort(key=lambda x: (-x[0], x[1]))
        return {k: 0.1 for _, _, k in sc[:10]}, {k: t for _, t, k in sc[:10]}

    def alpha(k, m):
        ys, xs = [], []
        mm = m
        for _ in range(12):
            r = mret(k, mm)
            if r is None or mm not in ixm:
                return None
            rf = float(RF.get(mm, 0.0))
            ys.append(r - rf); xs.append(ixm[mm] - rf)
            mm = PP.mshift(mm, -1)
        x, y = np.array(xs), np.array(ys)
        vx = x.var(ddof=1)
        if vx <= 0:
            return None
        beta = np.cov(x, y, ddof=1)[0, 1] / vx
        return float(y.mean() - beta * x.mean())

    def rule_A(m):
        i = me[m]
        sc = []
        for t, k in PP.union_members(W, m, i)[0]:
            a1, a0 = alpha(k, m), alpha(k, PP.mshift(m, -6))
            if a1 is None or a0 is None:
                continue
            sc.append((a1 - a0, t, k))
        sc.sort(key=lambda x: (-x[0], x[1]))
        return {k: 0.1 for _, _, k in sc[:10]}, {k: t for _, t, k in sc[:10]}

    def rule_B(m):
        i = me[m]
        rows = []
        for t, k in PP.union_members(W, m, i)[0]:
            f = W["FUND"].get(k) or W["FUND"].get(t) or {}
            obs = TB.asof_all(f.get("eq") or [], dates[i]) if f.get("eq") else None
            if not obs or obs[0][1] is None or obs[0][1] <= 0:
                continue                                  # 자기자본 ≤ 0 은 채점 불가(정하지 않은 자리)
            mc = mcap(t, k, i)
            if not mc:
                continue
            rows.append((obs[0][1] / mc, t, k))
        rows.sort(key=lambda x: -x[0])
        h = len(rows) // 2
        val, gro = rows[:h], rows[h:]
        now, then = dfii(i), dfii(me[PP.mshift(m, -3)])
        chg = (now - then) if (now is not None and then is not None) else 0.0
        wv = 0.7 if chg >= 0.20 else (0.3 if chg <= -0.20 else 0.5)
        w = {k: wv / len(val) for _, _, k in val}
        w.update({k: (1 - wv) / len(gro) for _, _, k in gro})
        return w, {k: t for _, t, k in rows}

    def rule_E(m):
        i = me[m]
        sc = EG.get(m) or {}
        rows = []
        for t, k in PP.union_members(W, m, i)[0]:
            v = sc.get(t) if t in sc else sc.get(k)
            if v is None:
                continue
            mc = mcap(t, k, i)
            if mc:
                rows.append((v, t, k, mc))
        rows.sort(key=lambda x: -x[0])
        top = rows[:30]
        tot = sum(x[3] for x in top)
        w = {x[2]: x[3] / tot for x in top}
        for _ in range(50):                                # 20% 상한 · 넘친 몫 비례 재배분
            over = {k: v for k, v in w.items() if v > CAP + 1e-12}
            if not over:
                break
            ex = sum(v - CAP for v in over.values())
            free = {k: v for k, v in w.items() if v < CAP - 1e-12}
            fs = sum(free.values())
            for k in over:
                w[k] = CAP
            for k in free:
                w[k] += ex * free[k] / fs
        return w, {x[2]: x[1] for x in top}

    RULES = {"B": (rule_B, 1), "A": (rule_A, 1), "E": (rule_E, 3), "M": (rule_M, 1)}

    # ── 바스켓 일간 경로 ───────────────────────────────────────────────────────
    def sleeve(code):
        fn, every = RULES[code]
        path = {}                                          # 날짜 인덱스 → 가치(비용 뒤)
        v, w_units, cash = 1.0, {}, 1.0
        last = {}
        turns, books = [], []
        for j, m in enumerate(months):
            i, i1 = me[m], me[PP.mshift(m, 1)]
            is_reb = (j == 0) or (int(m[5:7]) % 3 == 0 if every == 3 else True)
            val = {k: w_units[k] * PX[k][last[k]] for k in w_units}
            V = cash + sum(val.values())
            if is_reb:
                tgt, names = fn(m)
                tgt = {k: x for k, x in tgt.items() if PX[k][i] == PX[k][i] and PX[k][i] > 0}
                tv = {k: V * x for k, x in tgt.items()}
                traded = sum(abs(tv.get(k, 0.0) - val.get(k, 0.0)) for k in set(tv) | set(val))
                c = COST * traded
                V2 = V - c
                w_units = {k: (V2 * x) / PX[k][i] for k, x in tgt.items()}
                cash = V2 - sum(V2 * x for x in tgt.values())
                last = {k: i for k in w_units}
                turns.append(traded / V)
                books.append({"sig": m, "w": {names.get(k, k): round(x, 6) for k, x in tgt.items()},
                              "prev": {(books[-1]["keymap"].get(k, k) if books else k): round(val.get(k, 0.0) / V, 6) for k in val},
                              "keymap": {k: names.get(k, k) for k in tgt}})
                path[i] = V2
            else:
                turns.append(0.0)
                path[i] = V
            rf_d = (1 + float(RF.get(PP.mshift(m, 1), 0.0))) ** (1.0 / max(1, i1 - i)) - 1
            for d in range(i + 1, i1 + 1):
                cash *= (1 + rf_d)
                for k in w_units:
                    p = PX[k][d]
                    if p == p and p > 0:
                        last[k] = d
                path[d] = cash + sum(w_units[k] * PX[k][last[k]] for k in w_units)
        return path, float(np.mean(turns) / 2 * 12), books

    SLV = {}
    for code in ("B", "A", "E", "M"):
        SLV[code] = sleeve(code)
        print("바스켓 %s (%.0fs)" % (code, time.time() - t0))
    i_start = me[months[0]]
    i_end = me[PP.mshift(months[-1], 1)]
    days = list(range(i_start, i_end + 1))
    mends = [me[m] for m in months] + [i_end]

    def daily_ret(path):
        return {d: path[d] / path[d - 1] - 1.0 for d in days[1:]}
    R = {c: daily_ret(SLV[c][0]) for c in SLV}

    # 조합 C — B·E·M 1/3 · 매월 말 되돌림(되돌림 비용 10bp)
    def combo(codes, wts):
        path = {days[0]: 1.0}
        v = 1.0
        parts = {c: v * w for c, w in zip(codes, wts)}
        for d in days[1:]:
            for c in codes:
                parts[c] *= (1 + R[c][d])
            v = sum(parts.values())
            if d in mends[1:-1] or d == mends[-1]:
                tgt = {c: v * w for c, w in zip(codes, wts)}
                cst = COST * sum(abs(tgt[c] - parts[c]) for c in codes)
                v -= cst
                parts = {c: v * w for c, w in zip(codes, wts)}
            path[d] = v
        return path
    SLV["C"] = (combo(["B", "E", "M"], [1 / 3] * 3), None, None)
    R["C"] = daily_ret(SLV["C"][0])

    # 펀드 — S&P 500 PR 90% + 바스켓 10% · 매월 말 되돌림
    def fund(code):
        path = {days[0]: 1.0}
        ix_v, sl_v = 0.9, 0.1
        resets = []
        for d in days[1:]:
            ix_v *= IX[d] / IX[d - 1]
            sl_v *= (1 + R[code][d])
            v = ix_v + sl_v
            if d in mends[1:]:
                dev = abs(sl_v / v - SLEEVE)
                v -= COST * 2 * dev * v
                resets.append(dev)
                ix_v, sl_v = v * 0.9, v * 0.1
            path[d] = v
        return path, float(np.mean(resets) * 12)

    def monthly(path):
        return np.array([path[mends[j + 1]] / path[mends[j]] - 1.0 for j in range(len(months))])
    ixp = {d: IX[d] / IX[days[0]] for d in days}
    im = monthly(ixp)
    hold = [PP.mshift(m, 1) for m in months]
    rfm = np.array([float(RF.get(h, 0.0)) for h in hold])

    def stats(r, rf):
        nav = np.cumprod(1 + r)
        ex = r - rf
        return {"cagr": float((nav[-1] ** (12 / len(r)) - 1) * 100), "vol": float(r.std(ddof=1) * math.sqrt(12) * 100),
                "sharpe": float(ex.mean() / ex.std(ddof=1) * math.sqrt(12))}

    def mdd_daily(path, a, z):
        xs = np.array([path[d] for d in days if a <= d <= z])
        return float(np.min(xs / np.maximum.accumulate(xs) - 1) * 100)

    def block(fr, sr, sel):
        e = (fr - im)[sel]
        n = sel.sum()
        te = e.std(ddof=1) * math.sqrt(12)
        return {"ann_ex": float(e.mean() * 1200), "cum_ex": float((np.prod(1 + fr[sel]) - np.prod(1 + im[sel])) * 100),
                "te": float(te * 100), "ir": float(e.mean() * 12 / te) if te > 0 else None,
                "t": float(e.mean() / (e.std(ddof=1) / math.sqrt(n))), "win": float(np.mean(e > 0) * 100),
                "fund": stats(fr[sel], rfm[sel]), "index": stats(im[sel], rfm[sel]), "basket": stats(sr[sel], rfm[sel]),
                "basket_ann_ex": float((sr - im)[sel].mean() * 1200),
                "basket_ir": float((sr - im)[sel].mean() * 12 / ((sr - im)[sel].std(ddof=1) * math.sqrt(12)))}
    sel_all = np.ones(len(months), bool)
    sel_3y = np.array([h >= R3 for h in hold])
    OUTD = {"prereg": "build/PREREG-2026-09-24-FUNDMIX.md", "prereg_commit": "78df5e15",
            "window": [hold[0], hold[-1]], "r3": [R3, hold[-1]], "cost_bp": COST * 1e4, "sleeve": SLEEVE, "strategies": {}}
    i3 = me[PP.mshift(R3, -1)]
    for code in ("B", "A", "E", "M", "C"):
        fp, reset_turn = fund(code)
        fr, sr = monthly(fp), monthly(SLV[code][0])
        yrs = {}
        for h, a, b, c_ in zip(hold, fr, im, sr):
            y = h[:4]
            yrs.setdefault(y, [1, 1, 1])
            yrs[y][0] *= 1 + a; yrs[y][1] *= 1 + b; yrs[y][2] *= 1 + c_
        epi = []
        for kind, nm, a, z in EPIS:
            ia, iz = di.get(a), di.get(z)
            if ia is None or iz is None or ia < days[0] or iz > days[-1]:
                continue
            ri = IX[iz] / IX[ia] - 1
            rfu = fp[iz] / fp[ia] - 1
            rsl = SLV[code][0][iz] / SLV[code][0][ia] - 1
            epi.append({"kind": kind, "name": nm, "a": a, "z": z, "index": ri * 100, "fund": rfu * 100,
                        "ex": (rfu - ri) * 100, "basket": rsl * 100, "basket_ex": (rsl - ri) * 100})
        info = {"all": block(fr, sr, sel_all), "3y": block(fr, sr, sel_3y),
                "mdd": {"fund_all": mdd_daily(fp, days[0], days[-1]), "index_all": mdd_daily(ixp, days[0], days[-1]),
                        "fund_3y": mdd_daily(fp, i3, days[-1]), "index_3y": mdd_daily(ixp, i3, days[-1]),
                        "basket_all": mdd_daily(SLV[code][0], days[0], days[-1])},
                "yearly": {y: {"index": (v[1] - 1) * 100, "fund": (v[0] - 1) * 100, "ex": (v[0] - v[1]) * 100, "basket": (v[2] - 1) * 100}
                           for y, v in sorted(yrs.items())},
                "episodes": epi, "reset_turn": reset_turn,
                "monthly_ex": [round(float(x) * 100, 4) for x in (fr - im)]}
        if SLV[code][1] is not None:
            bk = SLV[code][2]
            last_b = bk[-1]
            info["basket_turn_oneway"] = SLV[code][1]
            info["nav_turn_oneway"] = SLV[code][1] * SLEEVE + reset_turn
            top = sorted(last_b["w"].items(), key=lambda kv: -kv[1])
            info["holdings"] = {"sig": last_b["sig"], "n": len(top), "top": [{"t": t, "name": NAME.get(t, t), "w": w * 100} for t, w in top[:15]],
                                "eff_n": float(1 / sum(w * w for _, w in top)) if top else None}
            prev = last_b["prev"]
            cur = last_b["w"]
            tr = []
            for t in set(prev) | set(cur):
                dlt = (cur.get(t, 0.0) - prev.get(t, 0.0)) * SLEEVE * 100
                if abs(dlt) > 1e-6:
                    kind = "신규 매수" if t not in prev or prev.get(t, 0) == 0 else ("전량 매도" if t not in cur else ("늘림" if dlt > 0 else "줄임"))
                    tr.append({"t": t, "name": NAME.get(t, t), "kind": kind, "pct": dlt, "eok": dlt * 100})
            info["trades"] = sorted(tr, key=lambda x: (x["kind"], -abs(x["pct"])))
            info["n_books"] = len(bk)
            info["name_turnover_median"] = float(np.median([len(set(b["w"]) - set(bk[j - 1]["w"])) for j, b in enumerate(bk) if j]))
        OUTD["strategies"][code] = info
    exs = {c: np.array(OUTD["strategies"][c]["monthly_ex"]) for c in ("B", "E", "M")}
    OUTD["corr_ex"] = {a + b: float(np.corrcoef(exs[a], exs[b])[0, 1]) for a, b in (("B", "E"), ("B", "M"), ("E", "M"))}
    irs = {c: OUTD["strategies"][c]["all"]["ir"] for c in ("B", "E", "M", "C")}
    Cc = OUTD["strategies"]["C"]
    F1 = all(irs["C"] > irs[c] for c in ("B", "E", "M"))
    F2 = Cc["mdd"]["fund_all"] >= Cc["mdd"]["index_all"] - 1.0
    F3 = Cc["all"]["t"] >= 1.5
    OUTD["F"] = {"F1": F1, "F2": F2, "F3": F3}
    OUTD["verdict"] = "게시 후보" if (F1 and F2 and F3) else ("보류" if (F1 and F2) else "기각")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(OUTD, ensure_ascii=False, indent=1) + "\n")
    for c in ("B", "A", "E", "M", "C"):
        s = OUTD["strategies"][c]
        a = s["all"]
        print("%s  연초과 %+.2f%% · TE %.2f%% · IR %.2f · t %.2f · 승률 %.1f%% · 펀드 MDD %.1f%% (지수 %.1f%%) · 바스켓 연초과 %+.2f%%" % (
            c, a["ann_ex"], a["te"], a["ir"], a["t"], a["win"], s["mdd"]["fund_all"], s["mdd"]["index_all"], a["basket_ann_ex"]))
    print("상관", OUTD["corr_ex"], "| F", OUTD["F"], "| 판정", OUTD["verdict"], "(%.0fs)" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
