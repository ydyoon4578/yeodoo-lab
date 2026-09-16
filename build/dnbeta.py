# -*- coding: utf-8 -*-
"""하방 베타(풀 카드 E59) — 보통 베타와 다른 신호인가.

규약 build/PREREG-2026-09-14-DNBETA.md. 🚨 성과 문턱이 없다(등록 §0).

- 전체 베타는 TB.beta 와 같은 식이다. 속도 때문에 numpy 로 짜고 표본 월말에서 TB.beta 와
  대조한다(등록 §3 검산) — 식을 새로 발명하지 않는다.
- 편출 가격은 index_ledger._pitpx() 를 그대로 읽는다(커밋된 pit_px.json 종목만 쓴다).
- 정지시세 게이트는 TB._stall 을 그대로 부른다.

산출 data/_dnbeta.json (얼린 측정 · 커밋 안 함).
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA = os.path.join(os.path.dirname(HERE), "data")

WINS = (252, 1260)            # 등록 §1 — 12개월 · 60개월
DOWN_MIN_FRAC = 0.20          # 하락일 표본 문턱(창의 20%)
SEMI_MIN_DAYS = 15            # 세미베타 형성월 유효일 문턱
MIN_CAND = 30                 # 판별 후보 문턱(카드 ⑪)
SEC_MIN = 5                   # 섹터중립 — 섹터 안 최소 종목 수
WINSOR = (1.0, 99.0)
NW_LAG = 3
DIV_ADJ = 0.0200              # 벤치 가격지수 배당보정(연)
START, END = "2014-06", "2026-07"   # 형성월 범위 · 보유는 다음 달


def nw_t(x, lag=NW_LAG):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    T = len(x)
    if T < 12:
        return None, None, T
    mu = float(x.mean())
    e = x - mu
    s = float(e @ e) / T
    for l in range(1, lag + 1):
        s += 2.0 * (1.0 - l / (lag + 1.0)) * float(e[l:] @ e[:-l]) / T
    se = math.sqrt(s / T) if s > 0 else float("nan")
    return mu, (mu / se if se and se > 0 else None), T


def cbeta(Lw, mw, rows=None, min_n=2):
    """열마다 조건부(또는 전체) 베타 = Cov/Var — 유효 짝만으로. 표본분산 n−1 (TB.beta 와 같다)."""
    X = np.broadcast_to(mw[:, None], Lw.shape)
    valid = np.isfinite(Lw) & np.isfinite(X)
    if rows is not None:
        valid = valid & rows[:, None]
    n = valid.sum(0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        mx = np.where(valid, X, 0.0).sum(0) / n
        my = np.where(valid, Lw, 0.0).sum(0) / n
        dx = np.where(valid, X - mx, 0.0)
        dy = np.where(valid, Lw - my, 0.0)
        cov = (dx * dy).sum(0) / (n - 1)
        var = (dx * dx).sum(0) / (n - 1)
        b = cov / var
    b[(n < max(min_n, 2)) | ~np.isfinite(b) | ~(var > 0)] = np.nan
    return b


def semibetas(Lm, mm):
    ok = np.isfinite(Lm) & np.isfinite(mm)[:, None]
    n = ok.sum(0)
    rp = np.where(ok, np.maximum(Lm, 0.0), 0.0)
    rn = np.where(ok, np.minimum(Lm, 0.0), 0.0)
    mf = np.where(np.isfinite(mm), mm, 0.0)
    mpos, mneg = np.maximum(mf, 0.0), np.minimum(mf, 0.0)
    D = float((mf ** 2).sum())
    if D <= 0:
        nan = np.full(Lm.shape[1], np.nan)
        return nan, nan, nan, nan
    N_ = (rn * mneg[:, None]).sum(0) / D
    P_ = (rp * mpos[:, None]).sum(0) / D
    Mp = -(rn * mpos[:, None]).sum(0) / D
    Mn = -(rp * mneg[:, None]).sum(0) / D
    bad = n < SEMI_MIN_DAYS
    for a in (N_, P_, Mp, Mn):
        a[bad] = np.nan
    return N_, P_, Mp, Mn


def quint(vals):
    """0..4 (Q1..Q5). 유효값이 MIN_CAND 미만이면 None."""
    ok = np.isfinite(vals)
    idx = np.where(ok)[0]
    if len(idx) < MIN_CAND:
        return None
    order = idx[np.argsort(vals[idx], kind="mergesort")]
    q = np.full(len(vals), -1, int)
    k = len(order)
    for r, j in enumerate(order):
        q[j] = min(4, r * 5 // k)
    return q


def quint_sector(vals, sec):
    q = np.full(len(vals), -1, int)
    used = 0
    for s in set(sec):
        if not s:
            continue
        ix = np.where((np.array(sec) == s) & np.isfinite(vals))[0]
        if len(ix) < SEC_MIN:
            continue
        order = ix[np.argsort(vals[ix], kind="mergesort")]
        for r, j in enumerate(order):
            q[j] = min(4, r * 5 // len(order))
        used += len(ix)
    return q if used >= MIN_CAND else None


def port(q, fwd, w=None):
    """(Q1, Q5, Q5−Q1) — w 가 있으면 가중."""
    out = []
    for g in (0, 4):
        m = (q == g) & np.isfinite(fwd)
        if w is not None:
            m = m & np.isfinite(w) & (w > 0)
        if m.sum() == 0:
            out.append(None)
            continue
        if w is None:
            out.append(float(fwd[m].mean()))
        else:
            out.append(float((fwd[m] * w[m]).sum() / w[m].sum()))
    ls = (out[1] - out[0]) if (out[0] is not None and out[1] is not None) else None
    return out[0], out[1], ls


def zwin(v):
    v = v.astype(float).copy()
    ok = np.isfinite(v)
    if ok.sum() < MIN_CAND:
        return None
    lo, hi = np.percentile(v[ok], WINSOR)
    v[ok] = np.clip(v[ok], lo, hi)
    sd = v[ok].std(ddof=1)
    if not sd > 0:
        return None
    v[ok] = (v[ok] - v[ok].mean()) / sd
    return v


def xs_ols(y, Xs):
    ok = np.isfinite(y)
    for x in Xs:
        ok &= np.isfinite(x)
    if ok.sum() < MIN_CAND:
        return None
    A = np.column_stack([np.ones(ok.sum())] + [x[ok] for x in Xs])
    co, *_ = np.linalg.lstsq(A, y[ok], rcond=None)
    return co[1:]


def capm(y, x):
    y, x = np.asarray(y, float), np.asarray(x, float)
    k = len(y)
    if k < 24:
        return None
    X = np.column_stack([np.ones(k), x])
    co, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ co
    s2 = float(res @ res) / (k - 2)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return {"alpha_yr": float(co[0]) * 1200, "t": float(co[0] / se[0]), "beta": float(co[1]),
            "cagr": (float(np.prod(1 + y)) ** (12.0 / k) - 1) * 100, "n": k}


def main():
    import tech_backtest as TB
    import index_ledger as IL

    dates, px, vlm, hid, lod, meta, rf_ = TB.load(full=True)
    FU = TB.load_fund()
    di = {d: k for k, d in enumerate(dates)}
    cur = sorted(px)
    committed = set((json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))
                     .get("px") or {}).keys())
    pit = IL._pitpx()
    dl = sorted(t for t in pit if t not in px and t in committed)
    # 민감도 점검 전용 — 등록 측정은 제외 없이 돈다. 제외 판은 별도 파일로만 쓴다.
    excl = set()
    for a in sys.argv[1:]:
        if a.startswith("--exclude="):
            excl = set(x.strip() for x in a.split("=", 1)[1].split(",") if x.strip())
    if excl:
        dl = [t for t in dl if t not in excl]
    tick = cur + dl
    col = {t: j for j, t in enumerate(tick)}
    T, N = len(dates), len(tick)
    P = np.full((T, N), np.nan)
    for j, t in enumerate(cur):
        P[:, j] = [x if (x is not None and x > 0) else np.nan for x in px[t]]
    for j, t in enumerate(dl, start=len(cur)):
        for d, p in pit[t].items():
            k = di.get(d)
            if k is not None and p and p > 0:
                P[k, j] = p
    with np.errstate(invalid="ignore", divide="ignore"):
        R = np.vstack([np.full((1, N), np.nan), P[1:] / P[:-1] - 1.0])
        L = np.log1p(R)
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bmap = dict(zip(B["dates"], B["series"]["spx"]["px"]))
    mp = np.array([bmap.get(d) if bmap.get(d) else np.nan for d in dates], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        lm = np.log1p(np.concatenate([[np.nan], mp[1:] / mp[:-1] - 1.0]))
    IH = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))["months"]
    RG = {h["dt"][:7]: h["r"] for h in (json.load(io.open(os.path.join(DATA, "regime.json"),
                                                          encoding="utf-8")).get("history") or [])
          if not h.get("prov")}

    Rlist = {}

    def stalled(j, i):
        if j not in Rlist:
            Rlist[j] = [None if not np.isfinite(v) else float(v) for v in R[:, j]]
        return TB._stall(Rlist[j], i)

    me = TB.month_ends(dates)
    mes = [(a, b) for a, b in zip(me, me[1:]) if START <= dates[a][:7] <= END]

    SIGS = [f"{s}_{w}" for w in WINS for s in ("tot", "dn", "dn0", "rel")] + ["N", "Mn"]
    CELLS = ("A", "B", "C", "D")
    ser = {c: {s: {"q1": [], "q5": [], "ls": []} for s in SIGS} for c in CELLS}
    fm = {k: [] for k in ["tot+dn_%d_%s" % (w, th) for w in WINS for th in ("mean", "zero")]
          + ["dn_%d" % w for w in WINS] + ["tot_%d" % w for w in WINS] + ["semi"]}
    months, bench_m, ncand, xcorr, overlap, regime_ls = [], [], [], {w: [] for w in WINS}, {w: [] for w in WINS}, {}
    prev_me = None
    check = None
    comp = {"q5": [], "q1": []}      # 진단 — 판 A dn_252 오분위의 편출/생존 구성(측정과 무관)

    for i, i1 in mes:
        mm = dates[i][:7]
        hm = dates[i1][:7]
        hist = IH.get(mm)
        if not hist:
            prev_me = i
            continue
        members = set(hist.get("spx") or []) | set(hist.get("ndx") or [])
        cand = [col[t] for t in members if t in col and np.isfinite(P[i, col[t]])]
        cand = [j for j in cand if not stalled(j, i)]
        if len(cand) < MIN_CAND:
            prev_me = i
            continue
        cand = np.array(sorted(cand))
        surv = np.array([tick[j] in px for j in cand])
        # 보유 수익 — 끊기면 마지막 가격까지
        last = np.full(len(cand), np.nan)
        for r in P[i + 1:i1 + 1, cand]:
            m = np.isfinite(r)
            last[m] = r[m]
        fwd = last / P[i, cand] - 1.0
        bret = mp[i1] / mp[i] - 1.0 + DIV_ADJ / 12.0
        sig = {}
        for W in WINS:
            if i - W + 1 < 1:
                continue
            Lw, mw = L[i - W + 1:i + 1][:, cand], lm[i - W + 1:i + 1]
            tot = cbeta(Lw, mw, min_n=W // 2)
            mu = np.nanmean(mw)
            dmin = int(DOWN_MIN_FRAC * W)
            dn = cbeta(Lw, mw, rows=(mw < mu) & np.isfinite(mw), min_n=dmin)
            dn0 = cbeta(Lw, mw, rows=(mw < 0) & np.isfinite(mw), min_n=dmin)
            sig[f"tot_{W}"], sig[f"dn_{W}"], sig[f"dn0_{W}"], sig[f"rel_{W}"] = tot, dn, dn0, dn - tot
            if check is None and W == 252 and dates[i][:4] == "2020":
                js = [k for k in range(len(cand)) if np.isfinite(tot[k])][:6]
                diffs = []
                llist = [None if not np.isfinite(v) else float(v) for v in lm]
                for k in js:
                    colv = [None if not np.isfinite(v) else float(v) for v in L[:, cand[k]]]
                    tb = TB.beta(colv, llist, i, W)
                    if tb is not None:
                        diffs.append(abs(tb - float(tot[k])))
                check = {"date": dates[i], "n": len(diffs), "max_abs_diff": max(diffs) if diffs else None}
        if prev_me is not None:
            rows = slice(prev_me + 1, i + 1)
            N_, P_, Mp, Mn = semibetas(L[rows][:, cand], lm[rows])
            sig["N"], sig["_P"], sig["_Mp"], sig["Mn"] = N_, P_, Mp, Mn
        prev_me = i
        if not all(k in sig for k in ("tot_252", "dn_252")):
            continue
        months.append(hm)
        bench_m.append(bret)
        # 시총·섹터 (생존 종목만)
        mcap = np.full(len(cand), np.nan)
        secs = [""] * len(cand)
        for k, j in enumerate(cand):
            t = tick[j]
            if t in px:
                f = FU.get(t) or {}
                sh = TB.asof_fund(f.get("sh"), dates[i]) if f else None
                if sh and sh > 0:
                    mcap[k] = sh * P[i, j]
                secs[k] = (meta.get(t) or {}).get("sector") or ""
        ncand.append({"m": hm, "A": int(len(cand)), "B": int(surv.sum()),
                      "C": int(np.isfinite(mcap).sum())})
        for s in SIGS:
            v = sig.get(s)
            for c in CELLS:
                res = (None, None, None)
                if v is not None:
                    if c == "A":
                        q = quint(v)
                        res = port(q, fwd) if q is not None else res
                        if s == "dn_252" and q is not None:
                            for g, key in ((4, "q5"), (0, "q1")):
                                inq = (q == g) & np.isfinite(fwd)
                                dq, sq = inq & ~surv, inq & surv
                                top = sorted(((tick[cand[k]], float(fwd[k])) for k in np.where(dq)[0]),
                                             key=lambda z: abs(z[1]), reverse=True)[:3]
                                comp[key].append({"m": hm, "n": int(inq.sum()), "n_dl": int(dq.sum()),
                                                  "r_dl": float(fwd[dq].mean()) if dq.sum() else None,
                                                  "r_sv": float(fwd[sq].mean()) if sq.sum() else None,
                                                  "top_dl": [(a, round(b * 100, 1)) for a, b in top]})
                    elif c == "B":
                        vv = np.where(surv, v, np.nan)
                        q = quint(vv)
                        res = port(q, fwd) if q is not None else res
                    elif c == "C":
                        vv = np.where(np.isfinite(mcap), v, np.nan)
                        q = quint(vv)
                        res = port(q, fwd, mcap) if q is not None else res
                    else:
                        vv = np.where(np.isfinite(mcap), v, np.nan)
                        q = quint_sector(vv, secs)
                        res = port(q, fwd, mcap) if q is not None else res
                d = ser[c][s]
                d["q1"].append(res[0])
                d["q5"].append(res[1])
                d["ls"].append(res[2])
        # 횡단면 회귀(판 A)
        for W in WINS:
            if f"tot_{W}" not in sig:
                for k in fm:
                    if str(W) in k:
                        fm[k].append(None)
                continue
            zt, zd, zd0 = zwin(sig[f"tot_{W}"]), zwin(sig[f"dn_{W}"]), zwin(sig[f"dn0_{W}"])
            for th, z in (("mean", zd), ("zero", zd0)):
                co = xs_ols(fwd, [zt, z]) if (zt is not None and z is not None) else None
                fm["tot+dn_%d_%s" % (W, th)].append(float(co[1]) if co is not None else None)
            co = xs_ols(fwd, [zd]) if zd is not None else None
            fm["dn_%d" % W].append(float(co[0]) if co is not None else None)
            co = xs_ols(fwd, [zt]) if zt is not None else None
            fm["tot_%d" % W].append(float(co[0]) if co is not None else None)
            a, b = sig[f"tot_{W}"], sig[f"dn_{W}"]
            ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= MIN_CAND:
                ra = np.argsort(np.argsort(a[ok]))
                rb = np.argsort(np.argsort(b[ok]))
                xcorr[W].append((float(np.corrcoef(a[ok], b[ok])[0, 1]),
                                 float(np.corrcoef(ra, rb)[0, 1])))
                qa, qb = quint(np.where(ok, a, np.nan)), quint(np.where(ok, b, np.nan))
                if qa is not None and qb is not None:
                    s5 = set(np.where(qa == 4)[0])
                    overlap[W].append(len(s5 & set(np.where(qb == 4)[0])) / max(1, len(s5)))
        if all(k in sig for k in ("N", "_P", "_Mp", "Mn")):
            zs = [zwin(sig[k]) for k in ("N", "_P", "_Mp", "Mn")]
            co = xs_ols(fwd, zs) if all(z is not None for z in zs) else None
            fm["semi"].append([float(x) for x in co] if co is not None else None)
        else:
            fm["semi"].append(None)
        lab = RG.get(mm)
        v = ser["C"]["dn_252"]["ls"][-1]
        if lab and v is not None:
            regime_ls.setdefault(lab, []).append(v)

    # ── 집계 ──────────────────────────────────────────────────────────
    out = {"note": "하방 베타(E59). 규약 PREREG-2026-09-14-DNBETA.md. 얼린 측정.",
           "n_months": len(months), "months": [months[0], months[-1]] if months else None,
           "tickers": {"current": len(cur), "delisted_used": len(dl)},
           "check_tb_beta": check}
    bm = np.array(bench_m)

    def stat(lst):
        mu, t, n = nw_t(lst)
        return {"mean_pm": None if mu is None else mu * 100, "t": t, "n": n}

    out["fm"] = {k: stat(v) for k, v in fm.items() if k != "semi"}
    semi = [x for x in fm["semi"] if x is not None]
    out["fm_semi"] = {nm: stat([x[k] for x in semi]) for k, nm in enumerate(("N", "P", "M+", "M-"))}
    out["xcorr"] = {str(W): {"pearson_med": float(np.median([a for a, _ in xcorr[W]])) if xcorr[W] else None,
                             "rank_med": float(np.median([b for _, b in xcorr[W]])) if xcorr[W] else None,
                             "q5_overlap_med": float(np.median(overlap[W])) if overlap[W] else None}
                    for W in WINS}
    spreads = {}
    for c in CELLS:
        for s in SIGS:
            d = ser[c][s]
            spreads[f"{c}:{s}"] = stat(d["ls"])
    out["spreads"] = spreads

    def lscorr(c, s1, s2):
        a, b = ser[c][s1]["ls"], ser[c][s2]["ls"]
        pr = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
        return float(np.corrcoef([x for x, _ in pr], [y for _, y in pr])[0, 1]) if len(pr) > 24 else None

    out["ls_corr_dn_tot"] = {f"{c}_{W}": lscorr(c, f"dn_{W}", f"tot_{W}") for c in CELLS for W in WINS}
    alphas = {}
    for c in ("C", "A"):
        for W in WINS:
            for g in ("q5", "q1"):
                y = ser[c][f"dn_{W}"][g]
                pr = [(v, b) for v, b in zip(y, bm) if v is not None]
                r = capm([v for v, _ in pr], [b for _, b in pr]) if pr else None
                alphas[f"{c}:dn_{W}:{g}"] = r
    out["alphas"] = alphas
    out["bench_cagr"] = ((float(np.prod(1 + bm)) ** (12.0 / len(bm)) - 1) * 100) if len(bm) else None

    def diff(c1, c2, s):
        a, b = ser[c1][s]["ls"], ser[c2][s]["ls"]
        return stat([x - y for x, y in zip(a, b) if x is not None and y is not None])

    out["gaps"] = {f"{k}_{W}": diff(c1, c2, f"dn_{W}") for W in WINS
                   for k, (c1, c2) in (("vw_minus_ew(C-B)", ("C", "B")),
                                       ("surv(A-B)", ("A", "B")),
                                       ("sector(D-C)", ("D", "C")))}
    # 랩 규칙과의 관계
    try:
        import union as U
        raw = U.gather()
        Bu = U.bench_monthly()
        LM = {s: U.monthly(v["dates"], v["nav"]) for s, v in raw.items()}

        def labcorr(sid, mine):
            pr = [(mine[k], LM[sid][m] - Bu[m]) for k, m in enumerate(months)
                  if mine[k] is not None and m in LM.get(sid, {}) and m in Bu]
            return (float(np.corrcoef([x for x, _ in pr], [y for _, y in pr])[0, 1]), len(pr)) if len(pr) > 24 else None

        q1ex = [(v - b) if v is not None else None for v, b in zip(ser["A"]["dn_252"]["q1"], bm)]
        out["lab_corr"] = {"rel252_LS~x-updown": labcorr("t-x-updown", ser["A"]["rel_252"]["ls"]),
                           "dn252_Q1ex~x-maxlow": labcorr("t-x-maxlow", q1ex),
                           "dn252_Q1ex~x-lowvol": labcorr("t-x-lowvol", q1ex)}
    except Exception as e:
        out["lab_corr"] = {"error": str(e)[:120]}
    out["regime_C_dn252_ls"] = {k: {"mean_pm": float(np.mean(v)) * 100, "n": len(v)}
                                for k, v in sorted(regime_ls.items())}
    out["ncand"] = ncand
    out["comp_A_dn252"] = comp
    out["excluded"] = sorted(excl)
    out["series"] = {"months": months, "bench": list(map(float, bm)),
                     "C_dn_252": ser["C"]["dn_252"], "A_dn_252": ser["A"]["dn_252"],
                     "C_dn_1260": ser["C"]["dn_1260"], "A_dn_1260": ser["A"]["dn_1260"],
                     "B_dn_252": ser["B"]["dn_252"], "B_dn_1260": ser["B"]["dn_1260"]}
    with open(os.path.join(DATA, "_dnbeta_excl.json" if excl else "_dnbeta.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    # ── 출력 ──────────────────────────────────────────────────────────
    f2 = lambda x, p=2: "—" if x is None else ("%+.*f" % (p, x))
    print("표본 %d개월 (%s ~ %s) · 종목 현재 %d · 편출 %d" % (len(months), months[0], months[-1], len(cur), len(dl)))
    nc = np.array([[c["A"], c["B"], c["C"]] for c in ncand])
    print("후보 중앙  A %d · B %d · C %d" % tuple(np.median(nc, axis=0)))
    print("검산 TB.beta 대조:", check)
    print("\nQ2 원 신호 = 베타?")
    for W in WINS:
        x = out["xcorr"][str(W)]
        print("  %4d일  상관 중앙 %.3f (순위 %.3f) · Q5 겹침 %.0f%% · 롱숏 상관 A %s · C %s"
              % (W, x["pearson_med"], x["rank_med"], x["q5_overlap_med"] * 100,
                 f2(out["ls_corr_dn_tot"][f"A_{W}"], 3), f2(out["ls_corr_dn_tot"][f"C_{W}"], 3)))
    print("\nQ1 본론 — 횡단면 회귀 (월평균 %%p per 1sd · NW t)")
    for k, v in out["fm"].items():
        print("  %-18s %s  (t %s · %d개월)" % (k, f2(v["mean_pm"], 3), f2(v["t"]), v["n"]))
    print("\nQ4 세미베타 (N 양 · M− 음 기대)")
    for k, v in out["fm_semi"].items():
        print("  %-3s %s  (t %s)" % (k, f2(v["mean_pm"], 3), f2(v["t"])))
    print("\n롱숏 Q5−Q1 월평균 %%p (NW t)")
    print("  %-10s" % "" + "".join("%18s" % c for c in CELLS))
    for s in SIGS:
        print("  %-10s" % s + "".join("%11s (t %s)" % (f2(spreads[f"{c}:{s}"]["mean_pm"], 2),
                                                     f2(spreads[f"{c}:{s}"]["t"], 1)) for c in CELLS))
    print("\nQ5 롱온리 CAPM (벤치 CAGR %.2f%%)" % out["bench_cagr"])
    for k, v in alphas.items():
        if v:
            print("  %-16s CAGR %6.2f%% · 알파 %+6.2f%%p (t %+.2f) · 베타 %.2f"
                  % (k, v["cagr"], v["alpha_yr"], v["t"], v["beta"]))
    print("\nQ3·Q6·Q7 격차 (β_dn 롱숏 차이, 월 %%p)")
    for k, v in out["gaps"].items():
        print("  %-24s %s (t %s)" % (k, f2(v["mean_pm"], 3), f2(v["t"])))
    print("\nQ8 랩 규칙과의 상관:", out["lab_corr"])
    print("\nQ9 국면별 C·dn_252 롱숏 (서술만):", {k: (round(v["mean_pm"], 2), v["n"]) for k, v in out["regime_C_dn252_ls"].items()})
    print()
    print("[진단] 제외:", sorted(excl) or "없음(등록 측정)")
    print("[진단] A−B (β_dn 롱숏) 월별 분해")
    for W in WINS:
        a_, b_ = ser["A"][f"dn_{W}"]["ls"], ser["B"][f"dn_{W}"]["ls"]
        d_ = [(months[k], x - y) for k, (x, y) in enumerate(zip(a_, b_)) if x is not None and y is not None]
        v_ = [z for _, z in d_]
        worst = sorted(d_, key=lambda z: z[1])[:5]
        wset = set(w[0] for w in worst)
        rest = [z for m_, z in d_ if m_ not in wset]
        neg = sum(1 for z in v_ if z < 0)
        print("  %4d일  %d개월 중 음(−) %d개월(%.0f%%) · 평균 %+.3f%%p (t %s) · 최악 5개월 빼면 %+.3f%%p (t %s)" % (W, len(v_), neg, 100.0 * neg / len(v_), np.mean(v_) * 100, f2(nw_t(v_)[1]), np.mean(rest) * 100, f2(nw_t(rest)[1])))
        print("         최악 5개월: " + ", ".join("%s %+.2f%%p" % (m_, z * 100) for m_, z in worst))
        if W == 252:
            c5 = {x["m"]: x for x in comp["q5"]}
            c1 = {x["m"]: x for x in comp["q1"]}
            for m_, z in worst:
                print("           %s  Q5 편출 %s · Q1 편출 %s" % (m_, (c5.get(m_) or {}).get("top_dl"), (c1.get(m_) or {}).get("top_dl")))
    for key in ("q5", "q1"):
        rr = [x for x in comp[key] if x["n_dl"] > 0 and x["r_dl"] is not None and x["r_sv"] is not None]
        sh = np.mean([x["n_dl"] / x["n"] for x in comp[key] if x["n"]]) * 100
        dd = [x["r_dl"] - x["r_sv"] for x in rr]
        mu, t, n = nw_t(dd)
        print("  판 A dn_252 %s — 편출 종목 비중 평균 %.1f%% · 편출이 든 달 %d · (편출 − 생존) 월수익 %+.2f%%p (t %s)" % (key.upper(), sh, len(rr), (mu or 0) * 100, f2(t)))


if __name__ == "__main__":
    main()
