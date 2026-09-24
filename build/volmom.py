# -*- coding: utf-8 -*-
"""build/volmom.py — 변동성 관리 모멘텀(Barroso·Santa-Clara) 시점정확 검정 → data/_volmom.json

사전등록: build/PREREG-2026-09-24-VOLMOM.md (계산 전 커밋 c3a1e2ca)

기저 = 랩 x-mom12 시점정확 재현(stoploss.py 와 같은 선택 · F0 앵커로 확인). 기저의 **일간** 수익 경로를 2014 부터 만들어
σ̂(직전 126거래일 · 연율)와 확장창 목표 σ*(이전 월말 σ̂ 평균)를 잡고, 노출 e = min(1, σ*/σ̂) 로 판정 120개월을 돈다.
위약 = 같은 노출 값을 판정 달들에 무작위로 뒤섞은 1,000판.

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
⚠ 사전등록이 정하지 않은 구현 세부는 결과 문서 «정하지 않은 자리» 에 적는다(여기 주석에도 표시).

  python build/volmom.py
"""
from __future__ import annotations
import io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402  시점정확 패널
import stoploss as SL                 # noqa: E402  ret() · last_valid() — x-mom12 재현과 같은 함수

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_volmom.json")

W0, J0, J1 = "2014-06", "2016-08", "2026-07"      # 준비 형성 시작 · 판정 형성 창(보유 2016-09 ~ 2026-08)
TOPN, COST, LOOKD, MIN_PRIOR = 10, 0.0020, 126, 12
NPLAC, SEED = 1000, 20260924


def main() -> int:
    t0 = time.time()
    W = PP.load_world()
    dates, D, PX, me = W["dates"], W["D"], W["PX"], W["me"]
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))["monthly"]
    Bj = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bidx = {d: i for i, d in enumerate(Bj["dates"])}
    spx = np.array([np.nan if (bidx.get(d) is None or Bj["series"]["spx"]["px"][bidx[d]] is None)
                    else float(Bj["series"]["spx"]["px"][bidx[d]]) for d in dates])
    for j in range(1, D):                                    # 벤치 결측은 앞 값으로 잇는다
        if spx[j] != spx[j]:
            spx[j] = spx[j - 1]
    months = [m for m in sorted(me) if W0 <= m <= J1]

    # ── 선택 — stoploss.py 와 같은 x-mom12 재현(F0 앵커가 같음을 확인한다) ─────────
    picks = {}
    for m in months:
        i = me[m]
        mem, _ = PP.union_members(W, m, i)
        sc = []
        for t, k in mem:
            a = SL.ret(PX[k], i, 252)
            if a is None:
                continue
            b = SL.ret(PX[k], i, 21)
            sc.append((a - (b or 0.0), t, k))
        sc.sort(key=lambda x: (-x[0], x[1]))
        picks[m] = [k for _, _, k in sc[:TOPN] if PX[k][i] == PX[k][i] and PX[k][i] > 0]

    # ── 기저 일간 경로(비용 전) · 달마다 종목 수익 ─────────────────────────────
    dret = np.full(D, np.nan)
    mon = []
    for m in months:
        i, i1 = me[m], me[PP.mshift(m, 1)]
        ks = picks[m]
        u = {k: (1.0 / TOPN) / PX[k][i] for k in ks}           # 가치 1 기준 · 모자란 칸은 현금(0 수익 — 일간 경로에서만)
        cash = 1.0 - len(ks) / TOPN
        last = {k: i for k in ks}
        prev = 1.0
        for d in range(i + 1, i1 + 1):
            v = cash
            for k in ks:
                pk = PX[k][d]
                if pk == pk and pk > 0:
                    last[k] = d
                v += u[k] * PX[k][last[k]]
            dret[d] = v / prev - 1.0
            prev = v
        rk = {k: float(SL.last_valid(PX[k], i1, i) / PX[k][i] - 1.0) for k in ks}
        mon.append({"sig": m, "m": PP.mshift(m, 1), "i": i, "i1": i1, "ks": ks, "rk": rk,
                    "rf": float(RF.get(PP.mshift(m, 1), 0.0))})

    # ── σ̂ · σ* · 노출 ─────────────────────────────────────────────────────────
    def sig_at(ser, i):
        seg = ser[i - LOOKD + 1:i + 1]
        seg = seg[seg == seg]
        return float(np.std(seg, ddof=1) * math.sqrt(252)) if len(seg) >= LOOKD - 5 else None
    sret = np.full(D, np.nan)
    sret[1:] = spx[1:] / spx[:-1] - 1.0
    hist, hist_m = [], []
    for x in mon:
        s = sig_at(dret, x["i"])
        sm = sig_at(sret, x["i"])
        x["sig_hat"], x["sig_mkt"] = s, sm
        x["sig_star"] = float(np.mean(hist)) if len(hist) >= MIN_PRIOR else None
        x["sig_star_mkt"] = float(np.mean(hist_m)) if len(hist_m) >= MIN_PRIOR else None
        x["e"] = (min(1.0, x["sig_star"] / s) if (s and x["sig_star"]) else None)
        x["e_mkt"] = (min(1.0, x["sig_star_mkt"] / sm) if (sm and x["sig_star_mkt"]) else None)
        x["e15"] = (min(1.5, x["sig_star"] / s) if (s and x["sig_star"]) else None)
        if s is not None:
            hist.append(s)
        if sm is not None:
            hist_m.append(sm)
    J = [x for x in mon if J0 <= x["sig"] <= J1]
    if any(x["e"] is None for x in J):
        raise SystemExit("🚨 판정 달에 노출이 안 선 달이 있다 — 준비 창을 볼 것")

    # ── 월 수익(비용 뒤) — 노출 목록을 받아 돈다 ─────────────────────────────────
    def run(expo):
        pw, pr, pg = {}, {}, 0.0
        net, gross, turns = [], [], []
        for x, e in zip(J, expo):
            w = {k: e / TOPN for k in x["ks"]}
            g = sum(w[k] * x["rk"][k] for k in w) + (1.0 - sum(w.values())) * x["rf"]
            drift = {k: pw[k] * (1 + pr[k]) / (1 + pg) for k in pw} if pw else {}
            tv = sum(abs(w.get(k, 0.0) - drift.get(k, 0.0)) for k in set(w) | set(drift))
            net.append(g - COST * tv)
            gross.append(g)
            turns.append(tv)
            pw, pr, pg = w, x["rk"], g
        return np.array(net), np.array(gross), float(np.mean(turns) / 2 * 12)

    rf = np.array([x["rf"] for x in J])

    def st(r):
        r = np.asarray(r)
        nav = np.cumprod(1 + r)
        ex = r - rf
        return {"cagr": float((nav[-1] ** (12.0 / len(r)) - 1) * 100), "vol": float(r.std(ddof=1) * math.sqrt(12) * 100),
                "sharpe": float(ex.mean() / ex.std(ddof=1) * math.sqrt(12)), "mdd": float(np.min(nav / np.maximum.accumulate(nav) - 1) * 100),
                "worst": float(r.min() * 100)}

    E = [x["e"] for x in J]
    b_net, b_gross, b_turn = run([1.0] * len(J))
    m_net, m_gross, m_turn = run(E)
    SB, SM = st(b_net), st(m_net)

    # F0 앵커 — 랩 시점정확 엔진 x-mom12
    PS = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    rows_ = PS.get("strategies") or []
    if isinstance(rows_, dict):
        rows_ = list(rows_.values())
    lab = [x for x in rows_ if x.get("sid") in ("x-mom12", "t-x-mom12")][0]
    labm = {x["m"]: x["r"] for x in (lab.get("chart") or {}).get("monthly") or []}
    pairs = np.array([(g * 100, labm[x["m"]]) for x, g in zip(J, b_gross) if x["m"] in labm])
    corr = float(np.corrcoef(pairs[:, 0], pairs[:, 1])[0, 1])
    gap = float(np.mean(pairs[:, 0] - pairs[:, 1]))

    # 위약 — 같은 노출 값을 판정 달들에 뒤섞는다
    rng = np.random.default_rng(SEED)
    plac = []
    for _ in range(NPLAC):
        pe = list(rng.permutation(E))
        plac.append(st(run(pe)[0])["sharpe"])
    plac = np.array(plac)
    p90 = float(np.percentile(plac, 90))

    F0 = bool(corr >= 0.95 and abs(gap) <= 0.30)
    F1 = bool(SM["sharpe"] > SB["sharpe"])
    F2 = bool(SM["mdd"] - SB["mdd"] >= 5.0)
    F3 = bool(SM["sharpe"] > p90)
    F4 = bool(m_turn <= 10.0)
    if not F0:
        verdict = "측정 불가(F0)"
    elif F1 and F2 and F3 and F4:
        verdict = "게시 후보"
    elif F2 and F3:
        verdict = "보류"
    else:
        verdict = "기각"

    # ── 서술 — 랩 서술판 설정 · 레버리지 1.5 · 시장 변동성판 · 급락 구간 ────────────
    allm = np.array([sum(x["rk"][k] for k in x["ks"]) / TOPN + (1 - len(x["ks"]) / TOPN) * x["rf"] for x in mon])
    rep = []
    for x in J:
        j = mon.index(x)
        if j < 24:
            rep.append(1.0)
            continue
        tgt = float(np.std(allm[:j], ddof=1))
        v = float(np.std(allm[j - 6:j], ddof=1))
        rep.append(1.0 if v <= 0 else min(1.0, tgt / v))
    V_rep = st(run(rep)[0])
    V_15 = st(run([x["e15"] for x in J])[0])
    V_mkt = st(run([x["e_mkt"] if x["e_mkt"] is not None else 1.0 for x in J])[0])

    def win(r, a, z):
        rr = [v for x, v in zip(J, r) if a <= x["m"] <= z]
        return float((np.prod([1 + v for v in rr]) - 1) * 100) if rr else None
    crash = {nm: {"base": win(b_net, a, z), "managed": win(m_net, a, z),
                  "exposure_mean": float(np.mean([e for x, e in zip(J, E) if a <= x["m"] <= z]))}
             for nm, (a, z) in {"2018-10~12": ("2018-10", "2018-12"), "2020-02~03": ("2020-02", "2020-03"),
                                "2022": ("2022-01", "2022-12")}.items()}
    RESULT = {
        "prereg": "build/PREREG-2026-09-24-VOLMOM.md", "prereg_commit": "c3a1e2ca",
        "window": [J[0]["m"], J[-1]["m"]], "n_months": len(J), "cost_bp": COST * 1e4, "lookd": LOOKD,
        "f0_anchor": {"ok": F0, "corr": corr, "gap_pm": gap, "n": int(len(pairs))},
        "base": dict(SB, turn=b_turn), "managed": dict(SM, turn=m_turn),
        "exposure": {"mean": float(np.mean(E)), "min": float(np.min(E)), "share_below_1": float(np.mean(np.array(E) < 0.999)),
                     "share_below_07": float(np.mean(np.array(E) < 0.7))},
        "placebo": {"n": NPLAC, "sharpe_p50": float(np.median(plac)), "sharpe_p90": p90,
                    "managed_pct": float(np.mean(plac < SM["sharpe"]) * 100)},
        "variants": {"lab_report_monthly6": V_rep, "cap15_leverage": V_15, "market_vol": V_mkt},
        "crash": crash, "F": {"F0": F0, "F1": F1, "F2": F2, "F3": F3, "F4": F4}, "verdict": verdict,
        "monthly": [{"m": x["m"], "e": round(e, 4), "base": round(b * 100, 4), "managed": round(v * 100, 4)}
                    for x, e, b, v in zip(J, E, b_net, m_net)],
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(RESULT, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")

    print("== %s ~ %s (%d개월 · 편도 %dbp)" % (RESULT["window"][0], RESULT["window"][1], len(J), COST * 1e4))
    print("  F0 앵커 상관 %.4f · 월 차이 %+.3f%%p → %s" % (corr, gap, F0))
    for nm, s, tv in (("기저 x-mom12", SB, b_turn), ("변동성 관리", SM, m_turn)):
        print("  %-12s CAGR %6.2f%% · 변동 %5.1f%% · 샤프 %.3f · MDD %6.1f%% · 최악 달 %6.1f%% · 회전 %.1f배" % (nm, s["cagr"], s["vol"], s["sharpe"], s["mdd"], s["worst"], tv))
    for nm, s in (("(서술) 랩 서술판", V_rep), ("(서술) 상한 1.5", V_15), ("(서술) 시장 변동성", V_mkt)):
        print("  %-14s CAGR %6.2f%% · 샤프 %.3f · MDD %6.1f%% · 최악 달 %6.1f%%" % (nm, s["cagr"], s["sharpe"], s["mdd"], s["worst"]))
    print("  노출 평균 %.2f · 최저 %.2f · 1 미만인 달 %.0f%%" % (np.mean(E), np.min(E), np.mean(np.array(E) < 0.999) * 100))
    print("  F1 샤프 %.3f vs %.3f → %s · F2 MDD %+.1f%%p → %s · F3 위약 90백분위 %.3f (관리판 백분위 %.1f) → %s · F4 %.1f배 → %s" % (
        SM["sharpe"], SB["sharpe"], F1, SM["mdd"] - SB["mdd"], F2, p90, RESULT["placebo"]["managed_pct"], F3, m_turn, F4))
    print("  급락 구간:", crash)
    print("⇒ 판정:", verdict)
    print("→ %s (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
