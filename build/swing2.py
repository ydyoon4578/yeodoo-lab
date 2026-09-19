# -*- coding: utf-8 -*-
"""build/swing2.py — 과매도·과매수 스프레드 2차 (PREREG-2026-09-19-SWING2)

사전등록 커밋 70fc98c (계산 전) · 문서 해시 754b34ae59a68365063cacfd01b46f3f728f9754.

주 변형 = 분기 · β중립 · 히스테리시스(10 진입 / 30 밖 이탈). 이것만 판정한다.
부 변형 5종은 싣기만 한다(다중검정 회피 — 등록서 §2).

  python build/swing2.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swing1020 import load, score, WARMUP, TOPN, ann, nw_t          # noqa: E402
from tech_backtest import COST_BPS, COST_BPS_MAIN                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "_swing2.json")
EXIT_RANK = 30
BETA_WIN = 120
NSHUF = 200
SEED = 20260919
OOS = "2019-01"
PREREG = "PREREG-2026-09-19-SWING2"
COMMIT = "70fc98c"


def pick(row, held, hyst):
    """상위/하위 선택. hyst 면 보유 중인 것은 EXIT_RANK 밖으로 나가야 뺀다."""
    good = np.where(~np.isnan(row))[0]
    if len(good) < TOPN * 2:
        return None
    o_lo = good[np.argsort(row[good])]                    # 과매도 순
    o_hi = o_lo[::-1]                                     # 과매수 순
    out = []
    for order, prev in ((o_lo, held[0]), (o_hi, held[1])):
        if not hyst or prev is None:
            out.append(list(order[:TOPN])); continue
        rank = {int(t): r for r, t in enumerate(order)}
        keep = [t for t in prev if rank.get(int(t), 10 ** 9) < EXIT_RANK]
        keep = keep[:TOPN]
        for t in order:
            if len(keep) >= TOPN:
                break
            if int(t) not in {int(x) for x in keep}:
                keep.append(int(t))
        out.append(keep)
    return out[0], out[1]


def run(Sv, R, B, n, dates, month_end, quarterly, bneut, hyst):
    forms = [i for i in month_end if (not quarterly) or dates[i][5:7] in ("03", "06", "09", "12")]
    fset, held, sel, kk = set(forms), (None, None), {}, {}
    for i in forms:
        p = pick(Sv[i], held, hyst)
        if p is None:
            continue
        sel[i] = p
        held = p
        bl = np.nanmean(B[i][np.array(p[0])])
        bs = np.nanmean(B[i][np.array(p[1])])
        kk[i] = float(bl / bs) if bneut and bs and bs == bs else 1.0
    wl = ws = None
    k = 1.0
    sr, lr, shr, traded = [], [], [], []
    for i in range(WARMUP + 1, n):
        tr = 0.0
        j = i - 2                                          # 판정 다음날 종가 진입
        if j in sel:
            nl, ns = sel[j]
            k = kk[j]
            new_l = np.zeros(R.shape[1]); new_l[np.array(nl)] = 1.0 / len(nl)
            new_s = np.zeros(R.shape[1]); new_s[np.array(ns)] = k / len(ns)
            tr = (np.abs(new_l - (wl if wl is not None else 0)).sum()
                  + np.abs(new_s - (ws if ws is not None else 0)).sum())
            wl, ws = new_l, new_s
        r = R[i]
        rl = float(wl @ r) if wl is not None else 0.0
        rs = float(ws @ r) if ws is not None else 0.0
        if wl is not None:
            wl = wl * (1 + r); wl = wl / wl.sum()
            g = ws @ (1 + r); ws = ws * (1 + r) / g * k
        lr.append(rl); shr.append(rs); sr.append(rl - rs); traded.append(tr)
    return (np.array(sr), np.array(lr), np.array(shr), np.array(traded),
            len(sel), forms)


def reg_beta(y, x):
    x = np.asarray(x, float); y = np.asarray(y, float)
    xm = x.mean()
    return float(((x - xm) @ (y - y.mean())) / ((x - xm) @ (x - xm)))


def main():
    dates, tick, (P, H, L) = load()
    n = len(dates)
    S, _ = score(P, H, L, tick)
    Sv = S.to_numpy()
    Rdf = P.pct_change().fillna(0.0)
    bench = Rdf.mean(axis=1)
    R = Rdf.to_numpy()
    bvar = bench.rolling(BETA_WIN, min_periods=60).var()
    B = Rdf.rolling(BETA_WIN, min_periods=60).cov(bench).div(bvar, axis=0).clip(0, 3).to_numpy()
    bn = bench.to_numpy()[WARMUP + 1:n]
    dd = dates[WARMUP + 1:n]
    month_end = [i for i in range(WARMUP, n - 1) if dates[i][:7] != dates[i + 1][:7]]
    oos = np.array([d[:7] >= OOS for d in dd])
    print("종목 %d · %s ~ %s\n" % (len(tick), dates[WARMUP], dates[-1]))

    VAR = [("분기·β중립·히스테리시스", True, True, True, True),
           ("분기·β중립", True, True, False, False),
           ("분기·달러중립·히스테리시스", True, False, True, False),
           ("분기·달러중립", True, False, False, False),
           ("월·β중립·히스테리시스", False, True, True, False),
           ("월·β중립", False, True, False, False)]

    res, primary = {}, None
    print("   %-24s %8s %8s %8s %7s %8s %8s"
          % ("변형", "연%", "샤프", "NWt", "β", "10bp후", "19년후"))
    for nm, q, bnu, hy, is_main in VAR:
        sr, lr, shr, traded, nreb, forms = run(Sv, R, B, n, dates, month_end, q, bnu, hy)
        yrs = len(sr) / 252.0
        turn = float(traded.sum()) / 4 / yrs * 100
        be = reg_beta(sr, bn)
        m = ann(sr)
        net = {str(b): ann(sr - (b / 10000.0) * traded) for b in COST_BPS}
        a_oos = ann(sr[oos])
        row = dict(m, t=nw_t(sr), beta=round(be, 3), turnover=round(turn, 1),
                   n_rebal=nreb, net=net, oos=a_oos,
                   oos_net=ann((sr - (COST_BPS_MAIN / 10000.0) * traded)[oos]))
        res[nm] = row
        print("   %-24s %+8.2f %8s %8s %7.3f %+8.2f %+8.2f"
              % (nm, m["cagr"], m["sharpe"], row["t"], be,
                 net[str(COST_BPS_MAIN)]["cagr"], a_oos["cagr"]))
        if is_main:
            primary = (nm, sr, traded, row, forms)

    nm, sr, traded, row, forms = primary
    print("\n■ 주 변형 — %s   (판정 대상은 이것뿐이다)" % nm)
    print("   전 구간   연 %+.2f%% · 변동성 %.2f%% · 샤프 %s · MDD %.2f%% · NW t %s"
          % (row["cagr"], row["vol"], row["sharpe"], row["mdd"], row["t"]))
    print("   잔존 β %.3f · 리밸런스 %d회 · 다리당 연 편도 회전율 %.0f%% (1차 1172%%)"
          % (row["beta"], row["n_rebal"], row["turnover"]))
    print("   비용     " + " · ".join("%dbp %+.2f%%" % (b, row["net"][str(b)]["cagr"])
                                      for b in COST_BPS))
    print("   %s 이후  연 %+.2f%%  ·  10bp 후 %+.2f%%"
          % (OOS, row["oos"]["cagr"], row["oos_net"]["cagr"]))

    # ── 셔플 ───────────────────────────────────────────────────────────────
    print("\n■ 셔플 %d회" % NSHUF)
    rng = np.random.default_rng(SEED)
    pool = {i: np.where(~np.isnan(Sv[i]))[0] for i in forms}
    shuf = np.empty(NSHUF)
    for q in range(NSHUF):
        Sr = Sv.copy()
        for i in forms:
            p = pool[i]
            Sr[i, p] = Sv[i, rng.permutation(p)]
        shuf[q] = ann(run(Sr, R, B, n, dates, month_end, True, True, True)[0])["cagr"]
        if (q + 1) % 50 == 0:
            print("   ... %d회" % (q + 1))
    pct = float((shuf < row["cagr"]).mean()) * 100
    print("   실측 %+.2f%% · 셔플 평균 %+.2f%% · 백분위 %.1f (상위 %.1f%%)"
          % (row["cagr"], shuf.mean(), pct, 100 - pct))

    F = {
        "F1 전 구간 알파 ≤ 0": row["cagr"] <= 0,
        "F2 셔플 상위 5% 밖": pct < 95.0,
        "F3 10bp 후 알파 ≤ 0": row["net"][str(COST_BPS_MAIN)]["cagr"] <= 0,
        "F4 2019-01 이후 알파 ≤ 0": row["oos"]["cagr"] <= 0,
        "F5 잔존 |β| > 0.15": abs(row["beta"]) > 0.15,
    }
    print("\n■ 기각 조건")
    for k2, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k2))
    verdict = "기각" if any(F.values()) else "채택"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": PREREG, "prereg_commit": COMMIT, "as_of": dates[-1],
        "primary": nm, "variants": res, "oos_from": OOS,
        "shuffle": {"n": NSHUF, "seed": SEED, "mean": float(shuf.mean()),
                    "pctile_of_actual": round(pct, 1)},
        "fails": {k2: bool(v) for k2, v in F.items()}, "verdict": verdict,
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
