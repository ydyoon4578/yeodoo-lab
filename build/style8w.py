# -*- coding: utf-8 -*-
"""build/style8w.py — 스타일 8종의 **가중 방식** 넷을 겨룬다 → data/_style8w.json

등록: `build/PREREG-2026-09-18-STYLE8W.md`
🚨 **PIT 레그로만 돌린다**(사용자 지시 2026-09-18 — 「백테스트에 소급은 쓰지말고 pit으로」).
  소급 레그는 천장 진단에서 이미 순위가 갈리는 것을 확인했고(중소형 소급 1위 · PIT 6위),
  동일가중 총수익이 3.4배 부풀려진다. 여기서는 다시 재지 않는다.

  x-style8w-ew    1/8 동일가중 — 손잡이 0개 · 🚨 F1 의 대조군
  x-style8w-iv    역변동성  w ∝ 1/σ
  x-style8w-erc   동일위험기여 w_i(Σw)_i 가 모두 같게
  x-style8w-mv    최소분산 · Ledoit-Wolf 축소 공분산 · 롱온리

공분산은 굴림 252거래일 일별수익 하나로 고정한다(등록 §1-3). 월말에 다시 추정하고
**다음 거래일에 체결**한다. 롱온리 · 합 1 · 개별 상한 없음 · 무위험자산 없음.

레그는 `build/style8_oracle.build_legs` 를 **그대로 쓴다** — 백테스트를 두 벌로 만들면
반드시 어긋난다(style_pit.py 규약). 그 함수는 창을 WINDOW5 로 바꿔 ST.backtest 를 부른다.

    python build/style8w.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_style8w.json")

sys.path.insert(0, HERE)
import style_top_pdf as ST                            # noqa: E402
import style_pit_panel as SPP                         # noqa: E402
import style8_oracle as OR                            # noqa: E402

E8 = OR.E8
COV_WIN = 252              # 등록 §1-3 — 하나로 고정. 126·504 를 같이 돌리지 않는다.
COST_BP = 20.0             # 왕복 20bp — 스타일 간 비중 변경분에만 건다
N_SHUF = 200               # 등록 §2-3
SEED = 20260918
SCHEMES = ("ew", "iv", "erc", "mv")


# ── 비중 넷 ──────────────────────────────────────────────────────────────────
def w_ew(S):
    n = S.shape[0]
    return np.full(n, 1.0 / n)


def w_iv(S):
    sd = np.sqrt(np.maximum(np.diag(S), 1e-18))
    w = 1.0 / sd
    return w / w.sum()


def w_erc(S, iters=20000, tol=1e-12):
    """동일위험기여. ERC 에서 w_i(Σw)_i 가 모두 같으므로 w ∝ 1/(Σw) 가 고정점이다."""
    n = S.shape[0]
    w = np.full(n, 1.0 / n)
    for _ in range(iters):
        mrc = S @ w
        nw = 1.0 / np.maximum(mrc, 1e-18)
        nw /= nw.sum()
        nw = 0.5 * w + 0.5 * nw                        # 감쇠 — 진동을 막는다
        if np.max(np.abs(nw - w)) < tol:
            w = nw
            break
        w = nw
    return w


def ledoit_wolf(X):
    """Ledoit-Wolf(2004) 축소 — 표본 공분산을 스케일 항등행렬 쪽으로 당긴다.
    강도는 자료가 정한다(등록 §1-2: 내가 고르는 수가 아니다)."""
    T, N = X.shape
    Xc = X - X.mean(axis=0)
    S = (Xc.T @ Xc) / T
    mu = np.trace(S) / N
    F = mu * np.eye(N)
    d2 = np.sum((S - F) ** 2) / N
    b2 = 0.0
    for t in range(T):
        x = Xc[t:t + 1].T @ Xc[t:t + 1]
        b2 += np.sum((x - S) ** 2)
    b2 = b2 / (T ** 2) / N
    b2 = min(b2, d2)
    a2 = d2 - b2
    if d2 <= 0:
        return S, 0.0
    lam = b2 / d2
    return lam * F + (a2 / d2) * S, float(lam)


def proj_simplex(v):
    """단체(합 1 · 음수 없음)로의 유클리드 투영 — Duchi 외(2008)."""
    n = len(v)
    u = np.sort(v)[::-1]
    css = np.cumsum(u)
    rho = np.nonzero(u * np.arange(1, n + 1) > (css - 1))[0][-1]
    theta = (css[rho] - 1) / (rho + 1.0)
    return np.maximum(v - theta, 0.0)


def w_mv(S, iters=20000):
    """롱온리 최소분산 — 투영경사법. N=8 이라 안정적으로 수렴한다."""
    n = S.shape[0]
    lmax = float(np.max(np.linalg.eigvalsh(S)))
    step = 1.0 / (2.0 * lmax) if lmax > 0 else 1.0
    w = np.full(n, 1.0 / n)
    for _ in range(iters):
        g = 2.0 * (S @ w)
        nw = proj_simplex(w - step * g)
        if np.max(np.abs(nw - w)) < 1e-14:
            w = nw
            break
        w = nw
    return w


WFN = {"ew": lambda S, X: w_ew(S), "iv": lambda S, X: w_iv(S),
       "erc": lambda S, X: w_erc(S), "mv": lambda S, X: w_mv(S)}


# ── 백테스트 ─────────────────────────────────────────────────────────────────
def run(D, rebal, hold_from, perm=None, only=None):
    """일별 수익행렬 D(일 × 8)에서 비중 스킴별 일별 NAV 와 회전율.

    rebal      … 비중을 다시 정하는 날의 D 인덱스(월말)
    hold_from  … 그 비중을 적용하기 시작하는 날(= 월말 다음 거래일)
    perm       … F3 셔플용. 월마다 비중 벡터의 **자산 라벨만** 섞는다.
    only       … 이 스킴만 돌린다(셔플에서 쓴다 — 넷을 다 돌릴 이유가 없다)
    """
    n_d, n_s = D.shape
    out = {}
    for sch in (SCHEMES if only is None else (only,)):
        nav = np.ones(n_d)
        w = np.full(n_s, 1.0 / n_s)
        turn, whist, mx = [], [], []
        ri = 0
        for d in range(1, n_d):
            # 하루 표류
            r = D[d]
            w = w * (1.0 + r)
            s = w.sum()
            nav[d] = nav[d - 1] * s
            w = w / s if s > 0 else w
            # 월말에 정하고 다음 거래일부터 그 비중으로
            if ri < len(rebal) and d == hold_from[ri]:
                tgt = W_CACHE[sch][ri]
                if perm is not None:
                    tgt = tgt[perm[ri]]
                turn.append(0.5 * float(np.sum(np.abs(tgt - w))))
                whist.append(tgt.copy())
                mx.append(float(np.max(tgt)))
                w = tgt
                ri += 1
        out[sch] = {"nav": nav, "turn": np.asarray(turn),
                    "w": np.asarray(whist) if whist else np.zeros((0, n_s)),
                    "maxw": np.asarray(mx)}
    return out


def main() -> int:
    print("① PIT 패널 · 8종 레그 (소급 레그는 돌리지 않는다 — 사용자 지시)")
    prep = SPP.prepare(ST, window=max(ST.WINDOW, ST.WINDOW5), quiet=True)
    P = prep["P"]
    SPP.inject(prep)
    legs, start, end = OR.build_legs(P, prep["members_at"])
    print("   %s ~ %s · 리밸 %d · 주입 %d종"
          % (P.dates[start], P.dates[end], legs[E8[0]]["n_rebal"], len(prep["inject"])))

    # 일별 수익 행렬
    NAV = np.column_stack([np.asarray(legs[k]["nav"], float) for k in E8])
    D = np.zeros_like(NAV)
    D[1:] = NAV[1:] / NAV[:-1] - 1.0
    n_d = D.shape[0]
    me_abs = OR.month_ends(P.dates, start, end)
    me = [i - start for i in me_abs]

    print("② 등록 §1-0 — 가중이 일할 여지가 있나 (판정 아님)")
    Rm_all = np.column_stack([OR.seg_rets(legs[k]["nav"], me_abs, start) for k in E8]) - 1.0
    C = np.corrcoef(Rm_all.T)
    off = C[np.triu_indices(8, 1)]
    ev = np.linalg.eigvalsh(C)
    eff_n = float((ev.sum() ** 2) / np.sum(ev ** 2))
    print("   월간 수익 상관 — 최소 %.2f · 중앙 %.2f · 최대 %.2f"
          % (off.min(), np.median(off), off.max()))
    print("   유효 자산 수(상관 고유값 기준) %.2f / 8" % eff_n)
    # 명단 겹침 — backtest 가 돌려주는 두 달만 정확히 잰다. 다시 짜면 두 벌이 된다.
    jac = {}
    for tag in ("prev", "today"):
        sets = {k: {t for t, _s, _u in (legs[k][tag] or [])} for k in E8}
        vals = [len(sets[a] & sets[b]) / max(1, len(sets[a] | sets[b]))
                for i, a in enumerate(E8) for b in E8[i + 1:]]
        uni = len(set().union(*sets.values()))
        jac[tag] = {"date": P.dates[legs[E8[0]][tag + "_i"]], "mean_jaccard": round(float(np.mean(vals)), 4),
                    "max_jaccard": round(float(np.max(vals)), 4), "union_names": uni}
        print("   %s(%s) 평균 자카드 %.3f · 최대 %.3f · 8종 합집합 %d종"
              % (tag, jac[tag]["date"], jac[tag]["mean_jaccard"], jac[tag]["max_jaccard"], uni))
    print("   ⚠ 전 구간 명단 겹침은 못 쟀다 — ST.backtest 가 월별 선정 명단을 돌려주지 "
          "않는다. 다시 짜면 두 벌이 되므로 안 짠다.")

    print("③ 비중 — 굴림 %d거래일 일별 공분산 · 월말 추정 · 다음 거래일 체결" % COV_WIN)
    rebal = [d for d in me if d >= COV_WIN and d < n_d - 1]
    hold_from = [d + 1 for d in rebal]
    global W_CACHE
    W_CACHE = {s: [] for s in SCHEMES}
    lams = []
    for d in rebal:
        X = D[d - COV_WIN + 1:d + 1]
        S_lw, lam = ledoit_wolf(X)
        lams.append(lam)
        Xc = X - X.mean(axis=0)
        S = (Xc.T @ Xc) / X.shape[0]
        for s in SCHEMES:
            W_CACHE[s].append(WFN[s](S_lw if s == "mv" else S, X))
    for s in SCHEMES:
        W_CACHE[s] = np.asarray(W_CACHE[s])
    print("   재조정 %d회 (%s ~ %s) · LW 축소강도 중앙 %.3f"
          % (len(rebal), P.dates[start + rebal[0]], P.dates[start + rebal[-1]],
             float(np.median(lams))))

    print("④ 실행")
    res = run(D, rebal, hold_from)
    first = hold_from[0]
    me_oos = [d for d in me if d >= first]
    def mrets(nav):
        return OR.seg_rets(nav[first:], [d - first for d in me_oos], 0)
    def msum(nav):
        return OR.ann(mrets(nav))
    n_oos = len(mrets(res["ew"]["nav"]))          # 가짜 첫 달을 뺀 실제 월 수
    bnav = ST.bench_nav(P, P.gspc, start, end)
    bm = msum(bnav) if bnav is not None else None

    rows = {}
    for s in SCHEMES:
        nav = res[s]["nav"]
        m = msum(nav)
        cost_ann = float(np.sum(res[s]["turn"])) * COST_BP / 1e4 / (n_oos / 12.0)
        rows[s] = {"total": m["total"], "cagr": m["cagr"], "vol": m["vol"], "sharpe": m["sharpe"],
                   "turn_mo_pct": round(float(np.mean(res[s]["turn"])) * 100, 2),
                   "maxw_med": round(float(np.median(res[s]["maxw"])), 4),
                   "maxw_p90": round(float(np.percentile(res[s]["maxw"], 90)), 4),
                   "cost_drag_pp_yr": round(cost_ann * 100, 3)}
    print("   %-5s %9s %8s %7s %8s %8s %9s %9s"
          % ("", "총수익", "연율", "변동", "샤프", "월회전", "최대비중", "비용p.a."))
    for s in SCHEMES:
        r = rows[s]
        print("   %-5s %8.1f%% %7.1f%% %6.1f%% %8.2f %7.1f%% %8.1f%% %7.2f%%p"
              % (s, r["total"], r["cagr"], r["vol"], r["sharpe"], r["turn_mo_pct"],
                 r["maxw_med"] * 100, r["cost_drag_pp_yr"]))
    if bm:
        print("   %-5s %8.1f%% %7.1f%% %6.1f%% %8.2f" % ("bench", bm["total"], bm["cagr"], bm["vol"], bm["sharpe"]))

    print("⑤ F1·F2 — ew 대비")
    base_m = mrets(res["ew"]["nav"]) - 1.0
    f12 = {}
    for s in SCHEMES:
        if s == "ew":
            continue
        rs = mrets(res[s]["nav"]) - 1.0
        d_sh = rows[s]["sharpe"] - rows["ew"]["sharpe"]
        t = OR.tstat(rs - base_m)
        f12[s] = {"d_sharpe": round(d_sh, 4), "excess_pp_mo": round(float(np.mean(rs - base_m)) * 100, 4),
                  "t": round(t, 3), "F1": bool(d_sh > 0), "F2": bool(t >= 1.5)}
        print("   %-4s Δ샤프 %+.3f · 월초과 %+.3f%%p · t %+.2f → F1 %s · F2 %s"
              % (s, d_sh, f12[s]["excess_pp_mo"], t, "통과" if f12[s]["F1"] else "기각",
                 "통과" if f12[s]["F2"] else "기각"))

    print("⑥ F3 — 무작위 라벨 셔플 %d회 (월별 독립)" % N_SHUF)
    rng = np.random.default_rng(SEED)
    f3 = {}
    for s in SCHEMES:
        if s == "ew":
            f3[s] = {"note": "동일가중은 라벨을 섞어도 같다 — 셔플 대상이 아니다"}
            continue
        sh = []
        for _ in range(N_SHUF):
            perm = [rng.permutation(8) for _ in rebal]
            rr = run(D, rebal, hold_from, perm=perm, only=s)[s]["nav"]
            sh.append(OR.ann(mrets(rr))["sharpe"])
        sh = np.asarray(sh, float)
        pct = float((sh < rows[s]["sharpe"]).mean())
        f3[s] = {"pctile": round(pct, 3), "shuf_med": round(float(np.median(sh)), 3),
                 "shuf_p95": round(float(np.percentile(sh, 95)), 3),
                 "shuf_max": round(float(sh.max()), 3), "actual": round(rows[s]["sharpe"], 3),
                 "F3": bool(pct >= 0.95)}
        print("   %-4s 실측 %.2f · 셔플 중앙 %.2f · 95%% %.2f · 최고 %.2f → 백분위 %.1f%% → %s"
              % (s, rows[s]["sharpe"], f3[s]["shuf_med"], f3[s]["shuf_p95"], f3[s]["shuf_max"],
                 pct * 100, "통과" if f3[s]["F3"] else "기각"))

    print("⑦ F4 — 왕복 %dbp 뒤" % COST_BP)
    f4 = {}
    for s in SCHEMES:
        if s == "ew":
            continue
        d_sh_net = (rows[s]["sharpe"] - rows[s]["cost_drag_pp_yr"] / max(rows[s]["vol"], 1e-9)) - \
                   (rows["ew"]["sharpe"] - rows["ew"]["cost_drag_pp_yr"] / max(rows["ew"]["vol"], 1e-9))
        f4[s] = {"d_sharpe_net": round(d_sh_net, 4), "F4": bool(d_sh_net > 0 and f12[s]["F2"])}
        print("   %-4s 비용 뒤 Δ샤프 %+.3f → %s" % (s, d_sh_net, "유지" if f4[s]["F4"] else "기각"))

    verdict = {s: ("통과" if (f12.get(s, {}).get("F1") and f12.get(s, {}).get("F2")
                             and f3.get(s, {}).get("F3") and f4.get(s, {}).get("F4")) else "기각")
               for s in SCHEMES if s != "ew"}
    print("\n판정: " + " · ".join("%s %s" % (s, v) for s, v in verdict.items()))

    out = {
        "note": "🚨 얼린 측정 — 커밋 금지. 등록 build/PREREG-2026-09-18-STYLE8W.md · PIT 레그 전용.",
        "leg": "pit only (사용자 지시 2026-09-18 — 소급 레그는 백테스트에 쓰지 않는다)",
        "window": {"from": P.dates[start + first], "to": P.dates[end], "n_months_oos": n_oos,
                   "cov_win": COV_WIN, "n_rebal": len(rebal)},
        "styles": list(E8),
        "preflight": {"corr_min": round(float(off.min()), 4), "corr_med": round(float(np.median(off)), 4),
                      "corr_max": round(float(off.max()), 4), "effective_n": round(eff_n, 3),
                      "jaccard": jac,
                      "note": "판정 아님 — 가중이 일할 여지가 있는지 읽는 자리(등록 §1-0)"},
        "lw_shrink_med": round(float(np.median(lams)), 4),
        "perf": rows, "bench": bm,
        "w_mean": {s: {k: round(float(v), 4) for k, v in zip(E8, W_CACHE[s].mean(axis=0))}
                   for s in SCHEMES},
        "F1_F2": f12, "F3": f3, "F4": f4, "verdict": verdict,
        "caveat": "표본 밖 %d개월뿐이다(랩 표준 120개월의 절반 아래). F3 을 못 넘으면 "
                  "F1·F2 를 넘어도 «가중이 자산을 구별했다» 고 말할 수 없다." % n_oos,
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
