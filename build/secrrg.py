# -*- coding: utf-8 -*-
"""build/secrrg.py — 섹터 RRG 로테이션(주간) 검정 → data/_secrrg.json

사전등록: build/PREREG-2026-09-23-SECRRG.md (계산 전 커밋 06d1050f)

SPDR 섹터 9종을 SPY 대비 주간 RRG 에 놓고,
  S1 — 매주 말 주도 사분면 섹터를 동일가중으로 든다(없으면 9종 동일가중)
를 9종 동일가중(매주 재조정)과 견준다. 산식은 종목 판과 같은 rrg_board.rrg_np()(= rrg.py rrg_axes()).

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
⚠ 체결은 신호를 낸 주말 종가에 한다고 둔다(종가→종가). 랩의 월말 리밸 규약과 같은 가정이다.

  python build/secrrg.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rrg_board as RB                # noqa: E402  — 종목 판과 같은 주간·축·사분면 함수

DATA = RB.DATA
OUT = os.path.join(DATA, "_secrrg.json")

SECT = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]   # 사전등록 고정 9종
BENCH = "SPY"
W1 = "2026-09-11"          # 마지막 형성 주 — 다음 주 2026-09-18
COST = 0.0010              # 편도 10bp (F5)
F_T = 1.5
Q = RB.Q                   # 0 회복 · 1 주도 · 2 약화 · 3 부진


def tstat(v):
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) < 2:
        return None
    s = v.std(ddof=1)
    return float(v.mean() / (s / len(v) ** .5)) if s > 0 else None


def perf(r):
    """주간 수익 계열(소수) → CAGR·변동성·MDD·샤프(rf=0)."""
    r = np.asarray(r, dtype=float)
    nav = np.cumprod(1 + r)
    yrs = len(r) / 52.0
    cagr = nav[-1] ** (1 / yrs) - 1
    vol = r.std(ddof=1) * 52 ** .5
    peak = np.maximum.accumulate(nav)
    mdd = (nav / peak - 1).min()
    return {"cagr": cagr * 100, "vol": vol * 100, "mdd": mdd * 100,
            "sharpe_rf0": (r.mean() * 52) / vol if vol > 0 else None}


def book(weights, Rn):
    """주별 비중 행렬(형성 주 × 9) + 다음 주 수익 → (주간 수익, 주별 거래량 Σ|Δw|)."""
    ret = (weights * Rn).sum(axis=1)
    dw = np.abs(np.diff(weights, axis=0)).sum(axis=1)
    trade = np.concatenate([[weights[0].sum()], dw])      # 첫 주는 처음 사는 것
    return ret, trade


def main() -> int:
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    idx = pd.to_datetime(A["dates"])
    P = pd.DataFrame({t: [np.nan if v is None else float(v) for v in A["px"][t]] for t in SECT}, index=idx)
    b = pd.Series([np.nan if v is None else float(v) for v in A["px"][BENCH]], index=idx)
    if P.isna().any().any() or b.isna().any():
        raise SystemExit("🚨 섹터·SPY 일간 격자에 결측이 있다 — 사전등록은 결측 없는 9종을 전제했다")

    W, wb, partial = RB.weekly(P, b)
    r = W.pct_change(fill_method=None)
    rb = wb.pct_change(fill_method=None)
    rel = RB.rel_from_returns(r, rb, W.notna())
    ratio, mom = RB.rrg_np(rel)
    q = RB.quad_np(ratio, mom)
    dates = W.index
    n = len(dates)

    ok_all = (q >= 0).all(axis=1)
    rows = np.where(ok_all & (dates <= W1))[0]
    rows = rows[rows + 1 < n]
    if dates[rows[-1]].strftime("%Y-%m-%d") != W1:
        raise SystemExit("🚨 마지막 형성 주가 %s 이다 — 사전등록은 %s" % (dates[rows[-1]].date(), W1))
    Rn = r.values[rows + 1, :]              # 다음 주 섹터 수익(소수)
    RBn = rb.values[rows + 1]               # 다음 주 SPY 수익
    Qw = q[rows, :]
    print("형성 주 %d개 · %s ~ %s · 다음 주 %s 까지 · 부분 주 %s 제외"
          % (len(rows), dates[rows[0]].date(), W1, dates[rows[-1] + 1].date(),
             partial.date() if partial is not None else "없음"))

    # ── 비중 ──────────────────────────────────────────────────────────────
    J = len(SECT)
    ew = np.full((len(rows), J), 1.0 / J)

    def rule(mask):
        w = np.zeros((len(rows), J))
        k = mask.sum(axis=1)
        for i in range(len(rows)):
            w[i] = (mask[i] / k[i]) if k[i] else (1.0 / J)
        return w, int((k == 0).sum())

    w1, empty1 = rule(Qw == 1)                       # S1 — 주도
    w2, empty2 = rule((Qw == 0) | (Qw == 1))         # S2 — RS-Mom ≥ 100 (회복+주도) · 측정만
    r_ew, _ = book(ew, Rn)
    r1, tr1 = book(w1, Rn)
    r2, tr2 = book(w2, Rn)
    e1 = r1 - r_ew
    e2 = r2 - r_ew
    r1n = r1 - COST * tr1
    e1n = r1n - r_ew

    ann = lambda v: float(np.mean(v) * 52 * 100)          # 연 산술 초과(%p)
    turn1 = float(tr1[1:].mean() * 52 / 2)                # 연 회전(편도 합 ÷ 2)
    turn2 = float(tr2[1:].mean() * 52 / 2)

    f1_ex, f1_t = ann(e1), tstat(e1)
    f1_hit = not (f1_ex > 0)
    f2_hit = not (f1_t is not None and f1_t >= F_T)

    # ── F3 — 주도 − 부진, 주 단위 묶음 ─────────────────────────────────────
    exn = (Rn - RBn[:, None]) * 100
    md = []
    for i in range(len(rows)):
        a = exn[i][Qw[i] == 1]
        z = exn[i][Qw[i] == 3]
        if len(a) and len(z):
            md.append(a.mean() - z.mean())
    t3 = tstat(md)
    f3_hit = not (t3 is not None and t3 >= F_T)
    qmean = {Q[k]: float(exn[Qw == k].mean()) for k in range(4)}
    qn = {Q[k]: int((Qw == k).sum()) for k in range(4)}

    # ── F4 — 앞뒤 절반 부호 ────────────────────────────────────────────────
    h = len(e1) // 2
    a1, a2 = ann(e1[:h]), ann(e1[h:])
    f4_split = bool(np.sign(a1) != np.sign(a2))

    # ── F5 — 편도 10bp ────────────────────────────────────────────────────
    f5_ex, f5_t = ann(e1n), tstat(e1n)
    f5_hit = not (f5_ex > 0)

    # 서술 — 시계 방향 비율(검정하지 않는다)
    a = q[rows, :]
    bq = q[rows + 1, :]
    okq = (a >= 0) & (bq >= 0) & (a != bq)
    d = (bq.astype(int) - a.astype(int)) % 4
    cw, ccw = int(((d == 1) & okq).sum()), int(((d == 3) & okq).sum())

    # 판정 매핑 — 실행 전에 이 스크립트를 커밋해 못박는다(사전등록 문서 §2 의 문구를 판정어로 옮긴 것).
    #   F1·F5 걸림 → 기각. F2 «구별 불가» 도 기각 — SECEW(PREREG-2026-09-07) 가 «대조군 대비 t < 1.5 → 기각(F2)» 로
    #   쓴 이 랩의 선례를 따른다. F4 부호 갈림 또는 F3 걸림(규칙은 서는데 칸 전제가 안 섬) → 보류.
    verdict = ("기각" if (f1_hit or f2_hit or f5_hit) else
               "보류" if (f4_split or f3_hit) else "게시 후보")
    # ⚠ «게시 후보» 라도 곧바로 게시하지 않는다 — 사전등록 §4(자산 랩 규약으로 다시 잰다)

    last = n - 1
    now = {t: (Q[int(q[last, j])] if q[last, j] >= 0 else None) for j, t in enumerate(SECT)}
    spy = rb.values[rows + 1]
    doc = {
        "note": "섹터 RRG 로테이션(주간). 사전등록 PREREG-2026-09-23-SECRRG(커밋 06d1050f) 값 그대로.",
        "prereg": "build/PREREG-2026-09-23-SECRRG.md", "commit": "06d1050f",
        "sectors": SECT, "bench_rs": BENCH, "look": RB.LOOK, "cut": RB.CUT,
        "window": "%s ~ %s (형성 주 %d개)" % (dates[rows[0]].date(), W1, len(rows)),
        "perf": {"S1": perf(r1), "S1_net10bp": perf(r1n), "S2": perf(r2), "EW": perf(r_ew), "SPY": perf(spy)},
        "f1": {"hit": f1_hit, "ann_excess_pp": f1_ex, "t": f1_t, "말": "S1 − 9종 동일가중 연 초과 > 0"},
        "f2": {"hit": f2_hit, "t": f1_t, "문턱": F_T},
        "f3": {"hit": f3_hit, "t_clustered": t3, "n_weeks": len(md), "mean_diff_pp": float(np.mean(md)) if md else None,
               "quad_next_excess_vs_spy_pct": qmean, "quad_n": qn,
               "말": "주도 − 부진 다음 주 SPY 대비 초과(주 단위 묶음)"},
        "f4": {"split": f4_split, "first_half_pp": a1, "second_half_pp": a2,
               "halves": ["%s ~ %s" % (dates[rows[0]].date(), dates[rows[h - 1]].date()),
                          "%s ~ %s" % (dates[rows[h]].date(), W1)]},
        "f5": {"hit": f5_hit, "ann_excess_pp": f5_ex, "t": f5_t, "cost_one_way": COST},
        "s2": {"ann_excess_pp": ann(e2), "t": tstat(e2), "turnover": turn2, "empty_weeks": empty2,
               "말": "측정만 — 판정에 안 쓴다"},
        "turnover": {"S1": turn1, "S2": turn2}, "empty_weeks": {"S1": empty1, "S2": empty2},
        "avg_held": {"S1": float((w1 > 0).sum(axis=1).mean()), "S2": float((w2 > 0).sum(axis=1).mean())},
        "cw_share": cw / (cw + ccw) if (cw + ccw) else None, "cw": cw, "ccw": ccw,
        "now": {"week": dates[last].strftime("%Y-%m-%d"), "quad": now},
        "verdict": verdict,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    P_ = doc["perf"]
    print("\n  %-12s %7s %7s %8s %7s" % ("", "CAGR", "변동성", "MDD", "샤프0"))
    for k in ("S1", "S1_net10bp", "S2", "EW", "SPY"):
        p = P_[k]
        print("  %-12s %6.2f%% %6.2f%% %7.2f%% %7.3f" % (k, p["cagr"], p["vol"], p["mdd"], p["sharpe_rf0"]))
    print("\n  사분면별 다음 주 SPY 대비 초과:", " · ".join("%s %+.3f%%(%d)" % (k, qmean[k], qn[k]) for k in Q))
    print("  S1 평균 보유 %.2f종 · 주도 없는 주 %d · 연 회전 %.1f배" % (doc["avg_held"]["S1"], empty1, turn1))
    print("  S2 평균 보유 %.2f종 · 연 초과 %+.2f%%p · t %.2f · 연 회전 %.1f배 (측정만)"
          % (doc["avg_held"]["S2"], ann(e2), tstat(e2), turn2))
    print("\n🚨 실패 조건")
    print("  F1 S1 − EW 연 초과 %+.2f%%p → %s" % (f1_ex, "걸림 ✗" if f1_hit else "통과"))
    print("  F2 t = %.2f (문턱 %.1f) → %s" % (f1_t, F_T, "구별 불가" if f2_hit else "통과"))
    print("  F3 주도 − 부진 묶음 t = %.2f (주 %d · 평균차 %+.3f%%p) → %s"
          % (t3, len(md), np.mean(md), "걸림 ✗" if f3_hit else "통과"))
    print("  F4 앞 절반 %+.2f%%p · 뒤 절반 %+.2f%%p → %s" % (a1, a2, "부호 갈림 → 보류" if f4_split else "부호 같음"))
    print("  F5 편도 10bp 뒤 %+.2f%%p · t %.2f → %s" % (f5_ex, f5_t, "걸림 ✗" if f5_hit else "통과"))
    print("  (서술) 시계 방향 %.1f%% (%d · %d)" % (doc["cw_share"] * 100, cw, ccw))
    print("  지금(%s):" % doc["now"]["week"], " · ".join("%s %s" % (t, now[t]) for t in SECT))
    print("\n판정: **%s**" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
