#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B11 기술 링크 모멘텀 — 검정. 사전등록 build/PREREG-2026-08-12-TECHLINK.md 를 그대로 따른다.

입력  data/_techlink_cpc.json(build/techlink_build.py · 러너) · data/sd/*.json · data/_pit_px_cache.json
      data/index_history.json(PIT 명단) · data/members.json(GICS 산업)
규칙  월말 t: 직전 60개월 등록 특허의 CPC subclass 점유율 벡터(5년 3건 이상) → 코사인 근접도
      → 유니버스 안 상위 20 이웃의 t월 수익률을 근접도 가중평균 = 신호 → 상위 10 동일가중 롱 · 1개월 보유.
게이트 G1 커버리지 · G3 PIT assert · G4 스테일 · G5 ①레그 |t|≥3.43 ③산업 모멘텀 통제 증분 t≥2.0 ④PIT |t|≥3.31
      (② incr5 는 2026-08-12 사용자 결정으로 랩이 계산하지 않는다 — tech_backtest.py 870행.)
산출  data/_techlink_test.json · build/PREREG-2026-08-12-TECHLINK-RESULT.md 는 사람이 쓴다.

  python build/techlink_test.py
"""
from __future__ import annotations
import json
import math
import os
import sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_techlink_test.json")
WIN, MINPAT, K, TOPN = 60, 3, 20, 10
MIN_POOL = 3 * TOPN
S0, S1 = "2009-01", "2024-12"          # 신호 월(보유는 다음 달)
PIT0 = "2014-06"
T_LEG, T_INC, T_PIT = 3.43, 2.0, 3.31


def load(p):
    with open(os.path.join(DATA, p), encoding="utf-8") as f:
        return json.load(f)


def mshift(m, k):
    y, mo = int(m[:4]), int(m[5:]) + k
    y += (mo - 1) // 12; mo = (mo - 1) % 12 + 1
    return f"{y:04d}-{mo:02d}"


def tstat_daily(a, b):
    d = np.asarray(a) - np.asarray(b)
    if len(d) < 30 or d.std(ddof=1) == 0:
        return None
    return float(d.mean() / (d.std(ddof=1) / math.sqrt(len(d))))


def ols_nw(y, X, lag=3):
    y = np.asarray(y, float); X = np.column_stack([np.ones(len(y))] + [np.asarray(x, float) for x in X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += w * (G + G.T)
    V = XtXi @ S @ XtXi
    return b, b / np.sqrt(np.diag(V))


def main():
    T = load("_techlink_cpc.json")
    stk = load("stocks.json"); dates = stk["pxd_dates"]
    # 일간 가격: 현재 유니버스(data/sd) + 편출(pit 캐시)
    px = {}
    for s in stk["stocks"]:
        p = os.path.join(DATA, "sd", s["t"] + ".json")
        if os.path.exists(p):
            v = load(os.path.join("sd", s["t"] + ".json"))["pxd"]
            px[s["t"]] = [None] * (len(dates) - len(v)) + v
    cur = set(px)
    pitc = load("_pit_px_cache.json")
    pit_px = {t: [d.get(x) for x in dates] for t, d in pitc.items() if t not in px}
    allpx = dict(px); allpx.update(pit_px)
    mem = load("members.json")["members"]
    ind = {t: m.get("ind") for t, m in mem.items()}

    # 월말 인덱스
    me = [i for i in range(len(dates)) if i + 1 == len(dates) or dates[i + 1][:7] != dates[i][:7]]
    me_m = {dates[i][:7]: i for i in me}
    months = [m for m in sorted(me_m) if S0 <= m <= S1 and mshift(m, 1) in me_m]

    def mret(t, m):                                               # m월 수익률(전월말→m월말)
        s = allpx.get(t); pm = mshift(m, -1)
        if s is None or pm not in me_m:
            return None
        a, b = s[me_m[pm]], s[me_m[m]]
        return (b / a - 1) if a and b else None

    # 특허 벡터
    subs = sorted({sc for v in T["cpc"].values() for c in v.values() for sc in c})
    sidx = {s: i for i, s in enumerate(subs)}
    npm = T["npat_month"]

    def vec(t, m):
        lo = mshift(m, -WIN)
        n = sum(c for mm, c in npm.get(t, {}).items() if lo < mm <= m)
        if n < MINPAT:
            return None
        v = np.zeros(len(subs))
        for mm, c in T["cpc"].get(t, {}).items():
            if lo < mm <= m:                                      # G3② 등록월 ≤ t
                for sc, k in c.items():
                    v[sidx[sc]] += k
        nv = np.linalg.norm(v)
        return v / nv if nv else None

    pit_hist = load("index_history.json")["months"]

    def run(universe_fn, label, use_ind=False):
        hold, cover, same_ind, pool_n, nb_top = {}, [], [], [], {}
        ind_hold = {}
        for m in months:
            U = [t for t in universe_fn(m) if t in allpx]
            R = {t: mret(t, m) for t in U}
            V = {t: vec(t, m) for t in U if R[t] is not None}
            V = {t: v for t, v in V.items() if v is not None}
            cover.append(len(V))
            ts = sorted(V)
            if len(ts) < MIN_POOL:
                hold[m] = []; continue
            M = np.vstack([V[t] for t in ts]); P = M @ M.T
            assert np.allclose(np.diag(P), 1) and np.allclose(P, P.T) and P.min() >= -1e-9 and P.max() <= 1 + 1e-9
            np.fill_diagonal(P, -1)                               # 자기 자신 제외
            sig = {}
            for a, t in enumerate(ts):
                nb = np.argsort(-P[a])[:K]
                w = P[a, nb]
                if w.sum() <= 0:
                    continue
                sig[t] = float((w * np.array([R[ts[j]] for j in nb])).sum() / w.sum())
                nb_top.setdefault(m, {})[t] = [ts[j] for j in nb]
                if use_ind and ind.get(t):
                    same_ind.append(np.mean([ind.get(ts[j]) == ind[t] for j in nb]))
            pool_n.append(len(sig))
            hold[m] = sorted(sig, key=lambda t: -sig[t])[:TOPN]
            if use_ind:                                           # 대조: GICS 산업 모멘텀(자기 제외 산업 EW 지난달)
                g = {}
                for t in U:
                    if R[t] is not None and ind.get(t):
                        g.setdefault(ind[t], []).append((t, R[t]))
                isc = {}
                for t in ts:
                    peers = [r for u, r in g.get(ind.get(t), []) if u != t]
                    if peers:
                        isc[t] = float(np.mean(peers))
                ind_hold[m] = sorted(isc, key=lambda t: -isc[t])[:TOPN]
        return hold, cover, same_ind, pool_n, nb_top, ind_hold

    def daily_path(hold_by_m, base_fn=None):
        """월말 체결 · 동일가중 매수 후 보유(흘림). 일간 수익 계열."""
        out = []
        for m in months:
            i0, i1 = me_m[m], me_m[mshift(m, 1)]
            H = hold_by_m(m)
            H = [t for t in H if allpx[t][i0]]
            if not H:
                out += [0.0] * (i1 - i0); continue
            w = np.ones(len(H)) / len(H)
            prev = np.array([allpx[t][i0] for t in H], float)
            for i in range(i0 + 1, i1 + 1):
                now = np.array([allpx[t][i] or np.nan for t in H], float)
                now = np.where(np.isnan(now), prev, now)
                r = now / prev - 1
                out.append(float((w * r).sum()))
                w = w * (1 + r); w = w / w.sum(); prev = now
        return out

    def monthly(dr):
        res, k = [], 0
        for m in months:
            n = me_m[mshift(m, 1)] - me_m[m]
            res.append(float(np.prod(1 + np.array(dr[k:k + n])) - 1)); k += n
        return res

    def stats(dr):
        mr = np.array(monthly(dr)); nav = np.cumprod(1 + mr)
        yrs = len(mr) / 12
        return {"cagr": float(nav[-1] ** (1 / yrs) - 1), "vol": float(mr.std(ddof=1) * math.sqrt(12)),
                "mdd": float((nav / np.maximum.accumulate(nav) - 1).min()), "mean_m": float(mr.mean())}

    # ── 현재 유니버스 레그(랩 기본) ──
    hold, cover, same_ind, pool_n, nb_top, ind_hold = run(lambda m: sorted(cur), "cur", use_ind=True)
    eligible = lambda m: [t for t in cur if allpx[t][me_m[m]]]
    patent_univ = {m: [t for t in eligible(m) if vec(t, m) is not None] for m in months}
    d_s = daily_path(lambda m: hold[m])
    d_eq = daily_path(eligible)
    d_pt = daily_path(lambda m: patent_univ[m])
    d_ind = daily_path(lambda m: ind_hold.get(m, []))
    t_eq, t_pt = tstat_daily(d_s, d_eq), tstat_daily(d_s, d_pt)
    ms, meq, mind = np.array(monthly(d_s)), np.array(monthly(d_eq)), np.array(monthly(d_ind))
    b, tt = ols_nw(ms - meq, [mind - meq])
    # ── PIT 레그 ──
    pm = [m for m in months if m >= PIT0]
    def pit_u(m):
        mm = pit_hist.get(m) or {}
        return sorted(set(mm.get("spx", [])) | set(mm.get("ndx", [])))
    months_bak = months[:]
    months[:] = pm
    hold_p, cover_p, _, _, _, _ = run(pit_u, "pit")
    d_sp = daily_path(lambda m: hold_p[m])
    d_eqp = daily_path(lambda m: [t for t in pit_u(m) if t in allpx and allpx[t][me_m[m]]])
    t_pit = tstat_daily(d_sp, d_eqp)
    st_pit, st_pit_b = stats(d_sp), stats(d_eqp)
    months[:] = months_bak

    # G4 스테일
    def ov(a, b):
        A, B = nb_top.get(a, {}), nb_top.get(b, {})
        c = [len(set(A[t]) & set(B[t])) / K for t in A if t in B]
        return float(np.median(c)) if c else None
    g4 = ov("2020-12", "2024-12")
    nh = [len(hold[m]) for m in months]
    cov = np.array(cover)
    res = {
        "note": "B11 기술 링크 모멘텀 검정 — build/techlink_test.py. 사전등록 PREREG-2026-08-12-TECHLINK.md.",
        "window": [months[0], mshift(months[-1], 1)],
        "rule": {"win_m": WIN, "min_pat": MINPAT, "k": K, "topn": TOPN, "min_pool": MIN_POOL},
        "G1": {"median": float(np.median(cov)), "min": int(cov.min()), "pass": bool(np.median(cov) >= 90 and cov.min() >= 60),
               "series": dict(zip(months, map(int, cov)))},
        "G4": {"overlap_median_2020_12_vs_2024_12": g4, "pass": bool(g4 is not None and g4 >= 0.60)},
        "checks": {"holdings_mean": float(np.mean(nh)), "holdings_min": int(min(nh)), "empty_months": sum(1 for n in nh if n == 0),
                   "same_industry_share_top20": float(np.mean(same_ind)) if same_ind else None},
        "leg": {"t_vs_eq518": t_eq, "t_vs_patent_eq": t_pt, "pass": bool(t_eq is not None and abs(t_eq) >= T_LEG),
                "strategy": stats(d_s), "bench_eq": stats(d_eq), "bench_patent_eq": stats(d_pt), "ind_mom": stats(d_ind)},
        "ind_control": {"alpha_m": float(b[0]), "t_alpha": float(tt[0]), "beta": float(b[1]), "t_beta": float(tt[1]),
                        "pass": bool(tt[0] >= T_INC), "how": "월간 (전략−EW) = a + b·(산업모멘텀 상위10 − EW), 뉴이-웨스트 시차 3"},
        "pit": {"window": [pm[0], mshift(pm[-1], 1)], "t_vs_eq": t_pit, "pass": bool(t_pit is not None and abs(t_pit) >= T_PIT),
                "strategy": st_pit, "bench_eq": st_pit_b, "cover_median": float(np.median(cover_p))},
        "incr5": "계산 안 함(2026-08-12 사용자 결정 · tech_backtest.py)",
        "holdings_last": {m: hold[m] for m in months[-3:]},
    }
    res["G5_pass"] = bool(res["leg"]["pass"] and res["ind_control"]["pass"] and res["pit"]["pass"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    L = res["leg"]
    print(f"창 {res['window']} · G1 중앙값 {res['G1']['median']:.0f} 최소 {res['G1']['min']} → {'통과' if res['G1']['pass'] else '미달'}")
    print(f"검산: 보유 평균 {res['checks']['holdings_mean']:.2f} · 빈 달 {res['checks']['empty_months']} · 이웃 20 중 같은 산업 {res['checks']['same_industry_share_top20']}")
    print(f"레그: 전략 CAGR {L['strategy']['cagr']:.2%} vs EW518 {L['bench_eq']['cagr']:.2%} vs 특허EW {L['bench_patent_eq']['cagr']:.2%} · t(EW) {t_eq} · t(특허EW) {t_pt}")
    print(f"산업 모멘텀 통제: 알파 {b[0]*100:.3f}%/월 t {tt[0]:.2f} · 베타 {b[1]:.2f}")
    print(f"PIT {res['pit']['window']}: 전략 {st_pit['cagr']:.2%} vs EW {st_pit_b['cagr']:.2%} · t {t_pit}")
    print(f"G4 이웃 중복 중앙값 {g4} · G5 {'통과' if res['G5_pass'] else '기각'}")


if __name__ == "__main__":
    main()
