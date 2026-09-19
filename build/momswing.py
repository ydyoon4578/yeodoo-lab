# -*- coding: utf-8 -*-
"""build/momswing.py — 모멘텀 승자 중 «덜 과매수»만 (PREREG-2026-09-19-MOMSWING)

사전등록 커밋 7896d40 (계산 전) · 문서 해시 c7d922e024134b8ae7805947968be2b0351d8b83.

🚨 셔플이 이 파일의 요점이다 — 승자 52 «안에서만» 점수를 섞는다(등록서 §3).

  python build/momswing.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swing1020 import load, score, WARMUP, ann, nw_t                # noqa: E402
from tech_backtest import COST_BPS, COST_BPS_MAIN                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "_momswing.json")
DEC, HALF = 52, 26
SKIP, LOOK = 21, 252
NSHUF, SEED, OOS = 200, 20260919, "2019-01"
PREREG, COMMIT = "PREREG-2026-09-19-MOMSWING", "7896d40"


def sim(sel, R, n, start):
    """sel[i] = 보유 인덱스. 판정 다음날 종가 진입 · 표류."""
    w = None
    rets, traded = [], []
    for i in range(start, n):
        tr = 0.0
        if i - 2 in sel:
            nw = np.zeros(R.shape[1]); nw[sel[i - 2]] = 1.0 / len(sel[i - 2])
            tr = np.abs(nw - (w if w is not None else 0)).sum()
            w = nw
        r = R[i]
        x = float(w @ r) if w is not None else 0.0
        if w is not None:
            w = w * (1 + r); w = w / w.sum()
        rets.append(x); traded.append(tr)
    return np.array(rets), np.array(traded)


def main():
    dates, tick, (P, H, L) = load()
    n = len(dates)
    S, _ = score(P, H, L, tick)
    Sv = S.to_numpy()
    PX = P.to_numpy()
    LP = np.log(np.where(PX > 0, PX, np.nan))
    Rdf = P.pct_change().fillna(0.0)
    R = Rdf.to_numpy()
    bench = Rdf.mean(axis=1).to_numpy()
    start = max(WARMUP, LOOK + 5) + 1
    month_end = [i for i in range(start - 1, n - 1) if dates[i][:7] != dates[i + 1][:7]]
    dd = dates[start:n]
    oos = np.array([d[:7] >= OOS for d in dd])
    b = bench[start:n]
    print("종목 %d · %s ~ %s · 형성 %d회\n" % (len(tick), dates[start], dates[-1], len(month_end)))

    win_of = {}
    for i in month_end:
        f = LP[i - SKIP] - LP[i - LOOK]
        m = ~np.isnan(f) & ~np.isnan(Sv[i])
        if m.sum() < DEC:
            continue
        win_of[i] = np.where(m)[0][np.argsort(f[m])][-DEC:]

    sel_main = {i: w[np.argsort(Sv[i][w])[:HALF]] for i, w in win_of.items()}
    sel_base = {i: w for i, w in win_of.items()}                 # 대조군ⓑ 승자 52 단독

    r_main, t_main = sim(sel_main, R, n, start)
    r_base, t_base = sim(sel_base, R, n, start)
    yrs = len(r_main) / 252.0

    def show(nm, r, tr):
        m = ann(r)
        ex = float(np.mean(r - b)) * 252 * 100
        net = ann(r - (COST_BPS_MAIN / 10000.0) * tr)
        exn = float(np.mean(r - (COST_BPS_MAIN / 10000.0) * tr - b)) * 252 * 100
        print("   %-22s 연 %+6.2f%%  초과 %+6.2f%%p  샤프 %-6s 회전 %4.0f%%  10bp후 초과 %+6.2f%%p"
              % (nm, m["cagr"], ex, m["sharpe"], float(tr.sum()) / 2 / yrs * 100, exn))
        return m, ex, net, exn

    print("■ 성과")
    m_b = ann(b)
    print("   %-22s 연 %+6.2f%%" % ("ⓐ 유니버스 동일가중", m_b["cagr"]))
    mB, exB, ntB, exnB = show("ⓑ 모멘텀 승자 52", r_base, t_base)
    mM, exM, ntM, exnM = show("주 규칙 (덜 과매수 26)", r_main, t_main)

    incr = float(np.mean(r_main - r_base)) * 252 * 100
    t_incr = nw_t(r_main - r_base)
    ex_oos = float(np.mean((r_main - b)[oos])) * 252 * 100
    print("\n   증분(주 규칙 − ⓑ)  %+.2f%%p/년 · NW t %s" % (incr, t_incr))
    print("   %s 이후 초과       %+.2f%%p (10bp 후 %+.2f%%p)"
          % (OOS, ex_oos,
             float(np.mean((r_main - (COST_BPS_MAIN / 10000.0) * t_main - b)[oos])) * 252 * 100))
    print("   비용 " + " · ".join(
        "%dbp %+.2f%%p" % (c, float(np.mean(r_main - (c / 10000.0) * t_main - b)) * 252 * 100)
        for c in COST_BPS))

    # ── 셔플 — 승자 52 «안에서만» ──────────────────────────────────────────
    print("\n■ 셔플 %d회 — 승자 52 안에서 무작위 26 (등록서 §3)" % NSHUF)
    rng = np.random.default_rng(SEED)
    shuf = np.empty(NSHUF)
    for q in range(NSHUF):
        ss = {i: rng.choice(w, HALF, replace=False) for i, w in win_of.items()}
        rr, _ = sim(ss, R, n, start)
        shuf[q] = float(np.mean(rr - b)) * 252 * 100
        if (q + 1) % 50 == 0:
            print("   ... %d회" % (q + 1))
    pct = float((shuf < exM).mean()) * 100
    print("   실측 초과 %+.2f%%p · 셔플 평균 %+.2f%%p · 표준편차 %.2f · 백분위 %.1f (상위 %.1f%%)"
          % (exM, shuf.mean(), shuf.std(ddof=1), pct, 100 - pct))

    F = {"F1 ⓐ 대비 초과 ≤ 0": exM <= 0,
         "F2 셔플 상위 5% 밖": pct < 95.0,
         "F3 10bp 후 초과 ≤ 0": exnM <= 0,
         "F4 2019-01 이후 초과 ≤ 0": ex_oos <= 0,
         "F5 ⓑ 대비 증분 ≤ 0": incr <= 0}
    print("\n■ 기각 조건")
    for k, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k))
    verdict = "기각" if any(F.values()) else "채택"
    print("\n→ 판정: %s" % verdict)
    print("   (등록서 §4 예측: F2 에서 걸릴 것 — %s)"
          % ("맞음" if F["F2 셔플 상위 5% 밖"] else "틀림"))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": PREREG, "prereg_commit": COMMIT, "as_of": dates[-1], "start": dates[start],
        "bench": m_b, "base52": dict(mB, excess_pp=exB, excess_net_pp=exnB),
        "main": dict(mM, excess_pp=exM, excess_net_pp=exnM),
        "incr_pp": incr, "incr_t": t_incr, "oos_excess_pp": ex_oos, "oos_from": OOS,
        "shuffle": {"n": NSHUF, "seed": SEED, "mean": float(shuf.mean()),
                    "sd": float(shuf.std(ddof=1)), "pctile_of_actual": round(pct, 1)},
        "fails": {k: bool(v) for k, v in F.items()}, "verdict": verdict,
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
