# -*- coding: utf-8 -*-
"""build/mombreak.py — 모멘텀 주도주 부러짐: 이익이 뒷받침하지 않는 승자(SUE ≤ 0) 빼기 → data/_mombreak.json

사전등록: build/PREREG-2026-09-24-MOMBREAK.md (계산 전 커밋 0c3418eb)

기저 = 랩 x-mom12(점수 252일 − 21일 · 상위 10 동일가중 · 월말 종가) 시점정확 재현(stoploss.py 와 같은 선택).
① 깃발(형성일에 알 수 있던 최근 분기 SUE ≤ 0) 종목이 63거래일 안에 더 부러지나 — 달 안 순열 1,000번.
② 깃발 종목을 빼고 11~20위 깃발 없는 종목으로 채운 판 vs 같은 수를 무작위로 빼고 같은 종목으로 채운 판 1,000개.

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
⚠ 사전등록이 정하지 않은 구현 세부는 결과 문서 «정하지 않은 자리» 에 적는다(여기 주석에도 표시).

  python build/mombreak.py
"""
from __future__ import annotations
import io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402  시점정확 패널
import tech_backtest as TB            # noqa: E402  sue() — 글자 하나 안 고치고 쓴다
import stoploss as SL                 # noqa: E402  ret() — 랩 x-mom12 와 같은 정의(앵커 0.988)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_mombreak.json")

F0M, F1M = "2016-08", "2026-07"
TOPN, FILL_TO, COST = 10, 20, 0.0020
H, DROP, STAY, UP = 63, 0.75, 0.85, 1.25
NPERM, NCTRL, SEED = 1000, 1000, 20260924


def mdd(r):
    nav = np.cumprod(1 + np.asarray(r))
    return float(np.min(nav / np.maximum.accumulate(nav) - 1) * 100)


def main() -> int:
    t0 = time.time()
    W = PP.load_world()
    dates, D, PX, me, FU = W["dates"], W["D"], W["PX"], W["me"], W["FUND"]
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))["monthly"]
    months = [m for m in sorted(me) if F0M <= m <= F1M]
    rng = np.random.default_rng(SEED)

    def eps_of(t, k):
        for c in (k, t):
            s = (FU.get(c) or {}).get("eps")
            if s:
                return s
        return []

    M = []                                   # 달마다: 상위 20(키·깃발·sue) · 사건 · 수익
    for m in months:
        i = me[m]
        i1 = me[PP.mshift(m, 1)]
        mem, _ = PP.union_members(W, m, i)
        sc = []
        for t, k in mem:
            a = SL.ret(PX[k], i, 252)
            if a is None:
                continue
            b = SL.ret(PX[k], i, 21)
            sc.append((a - (b or 0.0), t, k))
        sc.sort(key=lambda x: (-x[0], x[1]))
        top = []
        for _, t, k in sc[:FILL_TO]:
            v = TB.sue(eps_of(t, k), dates[i])
            top.append({"t": t, "k": k, "sue": v, "flag": (v is not None and v <= 0)})
        full = (i + H) <= D - 1              # 63일 창이 자료 안에 다 있나(정하지 않은 자리 — 아니면 사건 통계에서 뺀다)
        for x in top:
            p = PX[x["k"]]
            p0 = p[i]
            seg = p[i + 1:min(i + H, D - 1) + 1]
            ok = seg[seg == seg]
            if len(ok) == 0 or not (p0 == p0 and p0 > 0):
                x["brk"] = x["surge"] = None
            else:
                x["brk"] = bool(ok.min() <= DROP * p0 and ok[-1] <= STAY * p0)
                x["surge"] = bool(ok.max() >= UP * p0)
            seg2 = p[i:i1 + 1]
            ok2 = np.where(seg2 == seg2)[0]
            x["r"] = float(seg2[ok2[-1]] / p0 - 1.0) if (len(ok2) and p0 == p0 and p0 > 0) else 0.0
        M.append({"m": PP.mshift(m, 1), "sig": m, "top": top, "full": full, "rf": float(RF.get(PP.mshift(m, 1), 0.0))})
    print("형성 %d개월 (%.0fs)" % (len(M), time.time() - t0))

    # ── ① 깃발 종목이 더 부러지나 ─────────────────────────────────────────────
    ev = [(j, x) for j, mo in enumerate(M) if mo["full"] for x in mo["top"][:TOPN] if x["brk"] is not None]
    n_all = len([1 for mo in M for _ in mo["top"][:TOPN]])
    cov = float(np.mean([x["sue"] is not None for mo in M for x in mo["top"][:TOPN]]))
    brk_n = sum(1 for _, x in ev if x["brk"])

    def ratios(flags):
        fb = [x["brk"] for (_, x), f in zip(ev, flags) if f]
        nb = [x["brk"] for (_, x), f in zip(ev, flags) if not f]
        fs = [x["surge"] for (_, x), f in zip(ev, flags) if f]
        ns = [x["surge"] for (_, x), f in zip(ev, flags) if not f]
        rb = (np.mean(fb) / np.mean(nb)) if (fb and nb and np.mean(nb) > 0) else None
        rs = (np.mean(fs) / np.mean(ns)) if (fs and ns and np.mean(ns) > 0) else None
        return rb, rs, (float(np.mean(fb)) if fb else None), (float(np.mean(nb)) if nb else None), \
            (float(np.mean(fs)) if fs else None), (float(np.mean(ns)) if ns else None), len(fb), len(nb)

    flags = [x["flag"] for _, x in ev]
    rb, rs, pbf, pbn, psf, psn, nf, nn = ratios(flags)
    # 달 안 순열 — 깃발 수를 그달 그대로 두고 자리만 섞는다
    by_month = {}
    for idx, (j, _) in enumerate(ev):
        by_month.setdefault(j, []).append(idx)
    perm_ge = 0
    for _ in range(NPERM):
        pf = list(flags)
        for j, ids in by_month.items():
            vals = [flags[q] for q in ids]
            rng.shuffle(vals)
            for q, v in zip(ids, vals):
                pf[q] = v
        rbp = ratios(pf)[0]
        if rbp is not None and rb is not None and rbp >= rb:
            perm_ge += 1
    p_perm = (perm_ge + 1) / (NPERM + 1)

    # 서술 — SUE 문턱 −1 · +1
    def ratio_at(th):
        fl = [(x["sue"] is not None and x["sue"] <= th) for _, x in ev]
        return ratios(fl)[0]
    alt = {"sue<=-1": ratio_at(-1.0), "sue<=+1": ratio_at(1.0)}

    # ── ② 빼면 나아지나 ───────────────────────────────────────────────────────
    def book_returns(pick_fn):
        """pick_fn(달 index) → 키 목록(최대 10) · 월 수익(비용 뒤)·회전·들고 있던 부러짐."""
        prev_w, prev_r, prev_g = {}, {}, 0.0
        net, held_brk, turns = [], 0, []
        for j, mo in enumerate(M):
            ks = pick_fn(j)
            rmap = {x["k"]: x for x in mo["top"]}
            w = {k: 1.0 / TOPN for k in ks}
            cash = 1.0 - sum(w.values())
            g = sum(w[k] * rmap[k]["r"] for k in w) + cash * mo["rf"]
            drift = {k: prev_w[k] * (1 + prev_r[k]) / (1 + prev_g) for k in prev_w} if prev_w else {}
            turn = sum(abs(w.get(k, 0.0) - drift.get(k, 0.0)) for k in set(w) | set(drift))
            net.append(g - COST * turn)
            turns.append(turn)
            if mo["full"]:
                held_brk += sum(1 for k in ks if rmap[k]["brk"])
            prev_w, prev_r, prev_g = w, {k: rmap[k]["r"] for k in w}, g
        return np.array(net), held_brk, float(np.mean(turns) / 2 * 12)

    fills, drops_k = [], []
    for mo in M:
        top10, rest = mo["top"][:TOPN], mo["top"][TOPN:]
        k_t = sum(1 for x in top10 if x["flag"])
        f = [x["k"] for x in rest if not x["flag"]][:k_t]
        fills.append(f)
        drops_k.append(k_t)
    base_net, base_brk, base_turn = book_returns(lambda j: [x["k"] for x in M[j]["top"][:TOPN]])
    tr_net, tr_brk, tr_turn = book_returns(lambda j: [x["k"] for x in M[j]["top"][:TOPN] if not x["flag"]] + fills[j])
    ctrl_mean, ctrl_brk, ctrl_mdd = [], [], []
    for _ in range(NCTRL):
        picks = []
        for j, mo in enumerate(M):
            top10 = [x["k"] for x in mo["top"][:TOPN]]
            k_t = drops_k[j]
            drop = set(rng.choice(len(top10), size=k_t, replace=False).tolist()) if k_t else set()
            picks.append([k for q, k in enumerate(top10) if q not in drop] + fills[j])
        cn, cb, _ = book_returns(lambda j, P_=picks: P_[j])
        ctrl_mean.append(float(np.mean(cn)))
        ctrl_brk.append(cb)
        ctrl_mdd.append(mdd(cn))
    ctrl_mean, ctrl_brk, ctrl_mdd = np.array(ctrl_mean), np.array(ctrl_brk), np.array(ctrl_mdd)
    p_brk = float(np.mean(ctrl_brk <= tr_brk))           # 처리판보다 부러짐을 덜 든 대조의 비율
    F0 = bool(brk_n >= 40 and cov >= 0.80)
    F1 = bool(rb is not None and rb >= 1.5 and p_perm < 0.05)
    F2 = bool(rb is not None and rs is not None and rs > 0 and (rb / rs) >= 1.25)
    F3 = bool(p_brk <= 0.10)
    F4 = bool(np.mean(tr_net) >= np.median(ctrl_mean) - 0.0010)
    F5 = bool(tr_turn <= 5.7)
    if not F0:
        verdict = "측정 불가(F0)"
    elif F1 and F2 and F3 and F4 and F5:
        verdict = "게시 후보"
    elif F1 and F2:
        verdict = "보류"
    else:
        verdict = "기각"

    # 서술 — 부러짐이 몰린 달 · 부러진 종목
    brk_months = {}
    for j, x in ev:
        if x["brk"]:
            brk_months[M[j]["sig"]] = brk_months.get(M[j]["sig"], 0) + 1
    top_months = sorted(brk_months.items(), key=lambda kv: -kv[1])[:10]
    names = sorted({(M[j]["sig"], x["t"], x["flag"]) for j, x in ev if x["brk"]})
    rf = np.array([mo["rf"] for mo in M])

    def sh(r):
        ex = np.asarray(r) - rf
        return float(ex.mean() / ex.std(ddof=1) * math.sqrt(12))
    RESULT = {
        "prereg": "build/PREREG-2026-09-24-MOMBREAK.md", "prereg_commit": "0c3418eb",
        "window": [M[0]["m"], M[-1]["m"]], "n_months": len(M), "n_event_months": sum(1 for mo in M if mo["full"]),
        "events": {"n": len(ev), "breaks": brk_n, "flagged_n": nf, "unflagged_n": nn,
                   "flag_share": nf / max(1, len(ev)), "sue_coverage": cov,
                   "p_break_flag": pbf, "p_break_noflag": pbn, "ratio_break": rb, "p_perm": p_perm,
                   "p_surge_flag": psf, "p_surge_noflag": psn, "ratio_surge": rs,
                   "ratio_break_over_surge": (rb / rs) if (rb and rs) else None, "alt_thresholds": alt},
        "book": {"base": {"mean_pm": float(base_net.mean() * 100), "sharpe": sh(base_net), "mdd": mdd(base_net), "held_breaks": base_brk, "turn": base_turn},
                 "treat": {"mean_pm": float(tr_net.mean() * 100), "sharpe": sh(tr_net), "mdd": mdd(tr_net), "held_breaks": tr_brk, "turn": tr_turn},
                 "ctrl": {"mean_pm_median": float(np.median(ctrl_mean) * 100), "held_breaks_median": float(np.median(ctrl_brk)),
                          "held_breaks_p10": float(np.percentile(ctrl_brk, 10)), "mdd_median": float(np.median(ctrl_mdd)),
                          "treat_mdd_pct_better": float(np.mean(ctrl_mdd <= mdd(tr_net)) * 100)},
                 "p_breaks": p_brk, "mean_drop_k": float(np.mean(drops_k)),
                 "fill_short_months": int(sum(1 for f, k in zip(fills, drops_k) if len(f) < k))},
        "F": {"F0": F0, "F1": F1, "F2": F2, "F3": F3, "F4": F4, "F5": F5}, "verdict": verdict,
        "break_months_top": top_months, "broke": [{"sig": s, "t": t, "flag": f} for s, t, f in names],
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(RESULT, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")

    f = lambda v, d=2: "—" if v is None else "%.*f" % (d, v)
    E, B = RESULT["events"], RESULT["book"]
    print("\n== %s ~ %s · 사건 창 %d개월" % (RESULT["window"][0], RESULT["window"][1], RESULT["n_event_months"]))
    print("  종목-월 %d · 부러짐 %d · 깃발 %d(%.1f%%) · SUE 커버 %.1f%% → F0 %s" % (E["n"], brk_n, nf, E["flag_share"] * 100, cov * 100, F0))
    print("  부러짐 비율 깃발 %s · 비깃발 %s → 비 %s · 순열 p %.3f → F1 %s" % (f(pbf, 3), f(pbn, 3), f(rb), p_perm, F1))
    print("  급등 비율 깃발 %s · 비깃발 %s → 비 %s · 부러짐비÷급등비 %s → F2 %s" % (f(psf, 3), f(psn, 3), f(rs), f(E["ratio_break_over_surge"]), F2))
    print("  문턱 서술: %s" % alt)
    print("  기저 월 %.3f%% · 샤프 %.3f · MDD %.1f%% · 든 부러짐 %d · 회전 %.1f배" % (B["base"]["mean_pm"], B["base"]["sharpe"], B["base"]["mdd"], base_brk, base_turn))
    print("  처리 월 %.3f%% · 샤프 %.3f · MDD %.1f%% · 든 부러짐 %d · 회전 %.1f배" % (B["treat"]["mean_pm"], B["treat"]["sharpe"], B["treat"]["mdd"], tr_brk, tr_turn))
    print("  대조 중앙 월 %.3f%% · 든 부러짐 중앙 %.0f(하위10%% %.0f) · MDD 중앙 %.1f%% · 처리판이 대조보다 MDD 나은 비율 %.1f%%" % (
        B["ctrl"]["mean_pm_median"], B["ctrl"]["held_breaks_median"], B["ctrl"]["held_breaks_p10"], B["ctrl"]["mdd_median"], B["ctrl"]["treat_mdd_pct_better"]))
    print("  F3 p %.3f → %s · F4 %s · F5 %s" % (p_brk, F3, F4, F5))
    print("  부러짐이 몰린 형성월:", top_months)
    print("⇒ 판정:", verdict)
    print("→ %s (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
