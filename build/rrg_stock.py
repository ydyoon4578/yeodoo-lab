# -*- coding: utf-8 -*-
"""build/rrg_stock.py — 종목 RRG(주간) 4분면 검정 → data/_rrg_stock.json

사전등록: build/PREREG-2026-09-23-RRGSTOCK.md (계산 전 커밋 064bdb29)

어제(PREREG-2026-09-22-RRG) 팩터 110종·월간 판에 건 검정을 **종목 518종·주간** 판에 다시 건다.
  같은 산식(rrg.py rrg_axes)·같은 컷·같은 되돌아보기 수(12)·같은 문턱(1.5)·같은 셔플 수(200).
  새로 더한 것은 F6(생존편향) 하나다.

🚨 이 스크립트는 **한 번** 돌린다. CI 에 붙이지 않는다 — 판정이 날마다 바뀌면 사전등록이 아니다.
   판(rrg_board.py)은 여기서 낸 _rrg_stock.json 을 옮겨 적기만 한다.

  python build/rrg_stock.py
"""
from __future__ import annotations
import io, json, os, sys, time

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rrg as RRG                     # noqa: E402  — 어제의 산식 정본(rrg_axes)
import rrg_board as RB                # noqa: E402  — 판과 같은 주간 패널

DATA = RB.DATA
OUT = os.path.join(DATA, "_rrg_stock.json")

W0, W1 = "2016-09-02", "2026-09-11"   # 형성 주 창 — 사전등록 고정(다음 주 = 2026-09-18 까지)
NSHUF = 200                            # F3 셔플 — 사전등록 고정
SEED = 20260923
F2_T = 1.5
F4_MIN = 500
Q = RB.Q
QEN = RB.QEN


def mean(v):
    return float(np.mean(v)) if len(v) else None


def welch(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if len(a) < 2 or len(b) < 2:
        return None
    den = (a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) ** .5
    return float((a.mean() - b.mean()) / den) if den > 0 else None


def t1(v):
    v = np.asarray(v)
    if len(v) < 2:
        return None
    s = v.std(ddof=1)
    return float(v.mean() / (s / len(v) ** .5)) if s > 0 else None


def cw_count(q, rows):
    """사분면 코드 행렬(주 × 종목)에서 rows 의 각 주 → 다음 주 전이를 센다. 제자리·맞은편은 안 센다."""
    a = q[rows, :]
    b = q[rows + 1, :]
    ok = (a >= 0) & (b >= 0) & (a != b)
    d = (b.astype(int) - a.astype(int)) % 4
    return int(((d == 1) & ok).sum()), int(((d == 3) & ok).sum())


def check_formula(rel, ratio, mom):
    """numpy 판이 rrg.py rrg_axes() 와 같은지 — 결측 없는 종목 몇에서 소수 6자리까지 대조한다."""
    full = [t for t in rel.columns if rel[t].notna().all()]
    pick = full[:3] + full[len(full) // 2:len(full) // 2 + 2] if len(full) >= 5 else full
    worst = 0.0
    for t in pick:
        ra, mo = RRG.rrg_axes(list(rel[t].values))
        for k in range(len(ra)):
            for ref, got in ((ra[k], ratio[t].values[k]), (mo[k], mom[t].values[k])):
                if ref is None:
                    if got == got:
                        raise SystemExit("🚨 %s 칸 %d: rrg_axes 는 None 인데 numpy 판은 %r" % (t, k, got))
                    continue
                worst = max(worst, abs(ref - got))
    if worst > 1e-6:
        raise SystemExit("🚨 numpy 판이 rrg_axes 와 %.2e 만큼 다르다 — 사전등록대로 멈춘다" % worst)
    return pick, worst


def pit_mask(W):
    """F6 — 그 주가 속한 달의 **전월말** S&P 500 ∪ NASDAQ 100 명단에 있던 (주, 종목)만 True.

    위키 명단의 티커는 그때 표기다. 오늘 티커와 CIK 를 공유하는 옛 티커를 전부 별칭으로 묶어 찾는다.
    NDX 가 비어 있는 달(파싱 공백)은 직전 달 명단을 잇는다.
    """
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    cik = H.get("cik") or {}
    hist = H.get("cik_hist") or {}
    norm = lambda s: s.replace(".", "-").upper()
    alias = {}
    for t in W.columns:
        a = {norm(t)}
        c = cik.get(t) or cik.get(t.replace("-", "."))
        if c and c in hist:
            a |= {norm(x) for x in hist[c]}
        alias[t] = a
    months = sorted(H["months"])
    mem, last = {}, {"spx": set(), "ndx": set()}
    for m in months:
        row = H["months"][m] or {}
        for k in ("spx", "ndx"):
            if row.get(k):
                last[k] = {norm(x) for x in row[k]}
        mem[m] = last["spx"] | last["ndx"]
    M = np.zeros(W.shape, dtype=bool)
    for i, d in enumerate(W.index):
        pm = (d.replace(day=1) - pd.Timedelta(days=1)).strftime("%Y-%m")
        s = mem.get(pm)
        if not s:
            continue
        for j, t in enumerate(W.columns):
            if alias[t] & s:
                M[i, j] = True
    return M


def main() -> int:
    t0 = time.time()
    pn = RB.panel()
    W, r, rb, mask, rel = pn["W"], pn["r"], pn["rb"], pn["mask"], pn["rel"]
    ratio, mom = RB.rrg_np(rel)
    pick, worst = check_formula(rel, ratio, mom)
    print("산식 대조: rrg_axes 와 최대 차 %.1e (%s) — 같다" % (worst, ", ".join(pick)))
    q = RB.quad_np(ratio, mom)
    dates = W.index
    n, J = W.shape

    # ── 창 ────────────────────────────────────────────────────────────────
    rows = np.where((dates >= W0) & (dates <= W1))[0]
    if dates[rows[0]].strftime("%Y-%m-%d") != W0 or dates[rows[-1]].strftime("%Y-%m-%d") != W1:
        raise SystemExit("🚨 창 끝 주가 사전등록과 다르다: %s ~ %s" % (dates[rows[0]].date(), dates[rows[-1]].date()))
    if rows[-1] + 1 >= n:
        raise SystemExit("🚨 마지막 형성 주의 다음 주가 없다")
    nxt = dates[rows[-1] + 1].strftime("%Y-%m-%d")
    print("형성 주 %d개 · %s ~ %s · 마지막 다음 주 %s · 부분 주 %s 제외"
          % (len(rows), W0, W1, nxt, pn["partial"].date() if pn["partial"] is not None else "없음"))

    # ── 다음 주 초과 ──────────────────────────────────────────────────────
    R = r.values * 100.0
    RBv = rb.values * 100.0
    EX = np.full((n, J), np.nan)
    EX[:-1, :] = R[1:, :] - RBv[1:, None]
    Qw, Ew = q[rows, :], EX[rows, :]
    ok = (Qw >= 0) & ~np.isnan(Ew)
    cells = {k: Ew[ok & (Qw == i)] for i, k in enumerate(Q)}
    base = Ew[ok]
    stat = {k: {"n": int(len(v)), "mean": mean(v),
                "win": float((v > 0).mean() * 100) if len(v) else None,
                "lift": (mean(v) - float(base.mean())) if len(v) else None}
            for k, v in cells.items()}

    lead, lag = cells["주도"], cells["부진"]
    f1_diff = float(lead.mean() - lag.mean())
    f1_hit = not (f1_diff > 0)
    t_pool = welch(lead, lag)
    f2_hit = not (t_pool is not None and abs(t_pool) >= F2_T)

    def clustered(okm):
        md = []
        for k in range(len(rows)):
            qa, ea, o = Qw[k], Ew[k], okm[k]
            a = ea[o & (qa == 1)]
            b = ea[o & (qa == 3)]
            if len(a) and len(b):
                md.append(a.mean() - b.mean())
        return md

    md = clustered(ok)
    t_clu = t1(md)
    f5_pass = (t_clu is not None and abs(t_clu) >= F2_T)
    f5_split = ((not f2_hit) != f5_pass)

    # ── F6 — 시점별 편입 관측만 ──────────────────────────────────────────
    PM = pit_mask(W)
    okp = ok & PM[rows, :]
    mdp = clustered(okp)
    t_pit = t1(mdp)
    full_sign = np.sign(np.mean(md)) if md else 0
    pit_sign = np.sign(np.mean(mdp)) if mdp else 0
    f6_flip = bool(full_sign != pit_sign)
    lead_p = Ew[okp & (Qw == 1)]
    lag_p = Ew[okp & (Qw == 3)]

    # ── F3 — 셔플 귀무 ────────────────────────────────────────────────────
    cw, ccw = cw_count(q, rows)
    real = cw / (cw + ccw)
    rng = np.random.default_rng(SEED)
    Rv = r.values
    valid = [np.where(~np.isnan(Rv[:, j]))[0] for j in range(J)]
    null = []
    t1s = time.time()
    for it in range(NSHUF):
        S = Rv.copy()
        for j in range(J):
            v = valid[j]
            if len(v) > 1:
                S[v, j] = Rv[rng.permutation(v), j]
        rs2 = RB.rel_from_returns(pd.DataFrame(S, index=W.index, columns=W.columns), rb, mask)
        ra2, mo2 = RB.rrg_np(rs2)
        a, c = cw_count(RB.quad_np(ra2, mo2), rows)
        null.append(a / (a + c))
        if it == 0:
            print("  셔플 1회 %.1f초 — 200회 예상 %.0f초" % (time.time() - t1s, (time.time() - t1s) * NSHUF))
    null = sorted(null)
    p95 = null[int(.95 * len(null))]
    f3_hit = not (real > p95)

    thin = [k for k in Q if stat[k]["n"] < F4_MIN]
    f4_hit = bool(thin)
    verdict = ("측정 불가" if f4_hit else
               "기각" if (f1_hit or f3_hit) else
               "보류" if (f5_split or f6_flip) else "측정만")

    # 현재 위치(마지막 완전한 주) — 예상 4 채점용
    cur = {k: int((q[n - 1, :] == i).sum()) for i, k in enumerate(Q)}

    doc = {"note": "종목 RRG(주간) 4분면 검정. 사전등록 PREREG-2026-09-23-RRGSTOCK(커밋 064bdb29) 대로 "
                   "계산 전에 실패조건을 못박았다. 되돌아보기·컷·산식 판·주기는 그 문서 값 그대로다.",
           "prereg": "build/PREREG-2026-09-23-RRGSTOCK.md", "commit": "064bdb29",
           "window": "%s ~ %s (형성 주 %d개 · 다음 주 %s 까지)" % (W0, W1, len(rows), nxt),
           "as_of": dates[-1].strftime("%Y-%m-%d"), "bench": "S&P 500(PR)", "look": RB.LOOK,
           "cut": RB.CUT, "n_stocks": int(J), "n_obs": int(len(base)),
           "formula_check": {"vs": "build/rrg.py rrg_axes", "stocks": pick, "max_abs_diff": worst},
           "quadrants": {k: {"en": QEN[k], **stat[k]} for k in Q},
           "base_mean": float(base.mean()),
           "f1": {"hit": f1_hit, "diff": f1_diff, "n_lead": int(len(lead)), "n_lag": int(len(lag)),
                  "말": "주도 사분면의 다음 주 초과가 부진 사분면보다 큰가"},
           "f2": {"hit": f2_hit, "t_pooled": t_pool, "문턱": F2_T},
           "f3": {"hit": f3_hit, "cw": cw, "ccw": ccw, "real": real, "null_p95": p95,
                  "null_median": null[len(null) // 2], "null_min": null[0], "null_max": null[-1],
                  "n_shuffle": NSHUF, "seed": SEED,
                  "말": "시계 방향 회전이 산식이 강제하는 것보다 많은가(셔플 귀무 95%)"},
           "f4": {"hit": f4_hit, "thin": thin, "문턱": F4_MIN},
           "f5": {"split": f5_split, "t_clustered": t_clu, "n_weeks": len(md),
                  "mean_diff": float(np.mean(md)), "말": "주 단위로 묶어도 같은 판정인가"},
           "f6": {"flip": f6_flip, "t_clustered": t_pit, "n_weeks": len(mdp),
                  "mean_diff": float(np.mean(mdp)) if mdp else None,
                  "n_obs": int(okp.sum()), "share_obs": float(okp.sum() / ok.sum()),
                  "lead_mean": mean(lead_p), "lag_mean": mean(lag_p),
                  "말": "그 시점 실제 편입 (종목·주)만 남겨도 주도−부진 부호가 같은가"},
           "now": cur, "verdict": verdict}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    # ── 화면 ──────────────────────────────────────────────────────────────
    print("\n관측 %d(종목·주) · 기준선 %+.3f%%p" % (len(base), base.mean()))
    print("\n  %-4s %-10s %8s %9s %6s %10s   지금" % ("사분면", "", "관측", "다음주", "승률", "기준선차"))
    for k in Q:
        s = stat[k]
        print("  %-4s %-10s %8d %+8.3f%% %5.1f%% %+9.3f%%p   %d종"
              % (k, QEN[k], s["n"], s["mean"], s["win"], s["lift"], cur[k]))
    print("\n🚨 실패 조건")
    print("  F1 주도 − 부진 = %+.4f%%p → %s" % (f1_diff, "걸림 ✗" if f1_hit else "통과"))
    print("  F2 t(묶지 않음) = %.2f (문턱 %.1f) → %s" % (t_pool, F2_T, "구별 불가" if f2_hit else "통과"))
    print("  F3 시계 %d · 반시계 %d → 실제 %.2f%% vs 귀무 중앙 %.2f%% · 95%% %.2f%% (범위 %.2f~%.2f) → %s"
          % (cw, ccw, real * 100, null[len(null) // 2] * 100, p95 * 100, null[0] * 100, null[-1] * 100,
             "걸림 ✗" if f3_hit else "통과"))
    print("  F4 %d 미만 칸 %s → %s" % (F4_MIN, thin or "없음", "측정 불가 ✗" if f4_hit else "통과"))
    print("  F5 주 단위 묶음 t = %.2f (주 %d · 평균차 %+.4f%%p) → %s"
          % (t_clu, len(md), np.mean(md), "갈림 → 보류" if f5_split else "같은 판정"))
    print("  F6 시점별 편입만: 관측 %.1f%% · 묶음 t = %.2f · 평균차 %+.4f%%p → %s"
          % (okp.sum() / ok.sum() * 100, t_pit, np.mean(mdp), "부호 뒤집힘 → 보류" if f6_flip else "부호 같음"))
    print("\n판정: **%s**   (%.0f초)" % (verdict, time.time() - t0))
    print("→ _rrg_stock.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
