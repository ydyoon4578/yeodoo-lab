# -*- coding: utf-8 -*-
"""build/combo.py — 약한 신호 8개를 섞는다 (PREREG-2026-09-19-COMBO · 계산 전 883b96e)

🚨 F3(무작위 가중 200회)이 본체다 — 가중치를 «고른 것» 이 값을 하는가.
🚨 시점정확 멤버십·섹터중립·그 달 후보의 십분위·다음날 진입을 전부 켠다.

  python build/combo.py
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_combo.json")
MIN_POOL, MIN_N, NRW, SEED, COST = 30, 10, 200, 20260919, 0.0010
SIGS = ["Cta", "OL", "TaxSurp", "OCAT", "Mom", "negOsc", "negNOA", "negResid"]


def qser(j, k):
    tg = (j.get("tags") or {}).get(k) or {}
    return {e: float(v) for e, v, *_ in (tg.get("i") or tg.get("q") or tg.get("a") or [])}


def yser(j, k):
    tg = (j.get("tags") or {}).get(k) or {}
    out = {}
    for e, v, *_ in (tg.get("a") or []):
        out[e[:4]] = float(v)
    if not out:
        q = {}
        for e, v, *_ in (tg.get("q") or []):
            q.setdefault(e[:4], []).append(float(v))
        out = {y: float(sum(v)) for y, v in q.items() if len(v) == 4}
    return out


def main():
    base, ext = {}, {}
    for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8")); base[j["t"]] = j
    for d in ("fxe", "fxe_pit"):
        for p in glob.glob(os.path.join(DATA, d, "*.json")):
            j = json.load(io.open(p, encoding="utf-8")); ext[j["t"]] = j

    # ── 재무 신호 (분기) ──────────────────────────────────────────────────
    rows = []
    for t, b in base.items():
        e = ext.get(t, {})
        cash, at, liab = qser(b, "cash"), qser(b, "asset"), qser(b, "liab")
        sti, tax = qser(e, "sti"), qser(e, "tax")
        sh = qser(b, "sh") or qser(b, "sho")
        cogs_y, sga_y = yser(b, "cogs"), yser(e, "sga")
        for end, a in at.items():
            if not a or a <= 0:
                continue
            r = {"t": t, "end": end}
            c, s = cash.get(end), sti.get(end)
            if c is not None and s is not None:
                r["Cta"] = (c + s) / a
            if c is not None and liab.get(end) is not None:
                r["negNOA"] = -(((a - c) - liab[end]) / a)
            y = end[:4]
            if cogs_y.get(y) is not None and sga_y.get(y) is not None:
                r["OL"] = (cogs_y[y] + sga_y[y]) / a
            if sga_y.get(y) is not None:
                r["OCAT"] = sga_y[y] / a          # 조직자본 강도의 대리(축적 전 흐름)
            if tax.get(end) is not None and sh.get(end):
                r["_tax_ps"] = tax[end] / sh[end]
                r["_at_ps"] = a / sh[end]
            rows.append(r)
    D = pd.DataFrame(rows)
    D["q"] = pd.PeriodIndex(pd.to_datetime(D.end), freq="Q")
    D = D.sort_values(["t", "q"]).drop_duplicates(["t", "q"], keep="last")
    # 세금 계절차분
    prev = D[["t", "q", "_tax_ps", "_at_ps"]].copy(); prev["q"] = prev.q + 4
    prev = prev.rename(columns={"_tax_ps": "p_tax", "_at_ps": "p_at"})
    D = D.merge(prev, on=["t", "q"], how="left")
    ok = D._tax_ps.notna() & D.p_tax.notna() & (D.p_at > 0) & (D._tax_ps != 0)
    D.loc[ok, "TaxSurp"] = (D._tax_ps - D.p_tax) / D.p_at
    D["avail"] = (D.q.dt.end_time + pd.DateOffset(months=4)).dt.to_period("M")

    mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    hsec = hist.get("sector") or {}
    months_hist = hist["months"]

    # ── 가격 신호 ─────────────────────────────────────────────────────────
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    px = {}
    for s in st["stocks"]:
        p = os.path.join(DATA, "sd", "%s.json" % s["t"])
        if os.path.exists(p):
            v = json.load(io.open(p, encoding="utf-8")).get("pxd")
            if isinstance(v, list) and len(v) == len(dates):
                px[s["t"]] = v
    pit = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))
    for t, v in pit["px"].items():
        if t in px or not isinstance(v, dict):
            continue
        arr = [np.nan] * len(dates)
        i0, pp = int(v.get("i0") or 0), (v.get("p") or [])
        for k, val in enumerate(pp):
            if 0 <= i0 + k < len(dates) and val is not None:
                arr[i0 + k] = float(val)
        px[t] = arr
    P = pd.DataFrame(px, index=pd.to_datetime(dates))
    M = P.resample("M").last(); M.index = M.index.to_period("M")
    MR = M.pct_change()
    MOM = M.shift(1) / M.shift(13) - 1                       # 12-1
    RESID = M.pct_change(1)                                  # 전월 수익(잔차 대용)
    bench = MR.mean(axis=1)
    NEGRES = -(RESID.sub(bench, axis=0))
    # 진동자 과매수 점수
    # ⚠ SWING1020 은 진동자 5종(고가·저가 필요)을 썼는데, **편출 종목에는 고가·저가가 없다.**
    #   시점정확 다리를 켜려면 편출 종목이 들어와야 하므로 **종가만으로 되는 둘**(RSI·%b)로
    #   좁힌다. 그래서 이 축은 SWING1020 의 것과 같은 신호가 아니다 — 결과에 적는다.
    from refresh_stocks import rsi as _rsi, boll as _boll     # noqa: E402
    _z = []
    for _fn in (lambda c: _rsi(c), lambda c: _boll(c)[3]):
        _Mx = P.apply(_fn, axis=0)
        _z.append(((_Mx.sub(_Mx.mean(axis=1), axis=0))
                   .div(_Mx.std(axis=1).replace(0, np.nan), axis=0)).clip(-3, 3))
    S_osc = sum(_z) / len(_z)
    OSC = -S_osc.resample("M").last()
    OSC.index = OSC.index.to_period("M")

    shrow = []
    for t, b in base.items():
        s = (b.get("tags") or {}).get("sh") or (b.get("tags") or {}).get("sho") or {}
        for e, v, *_ in (s.get("i") or s.get("q") or s.get("a") or []):
            shrow.append({"t": t, "m": e[:7], "sh": float(v)})
    SW = pd.DataFrame(shrow).pivot_table(index="m", columns="t", values="sh", aggfunc="last")
    SW.index = pd.PeriodIndex(SW.index, freq="M"); SW = SW.reindex(M.index).ffill()
    CAP = pd.DataFrame(M.reindex(columns=SW.columns).to_numpy() * SW.to_numpy(),
                       index=M.index, columns=SW.columns).reindex(columns=M.columns)
    print("가격 %d종 · 월 %d개 · 재무 %d행/%d종" % (P.shape[1], len(M), len(D), D.t.nunique()))

    # ── 월별 패널 (시점정확 · 섹터중립 z) ─────────────────────────────────
    fin_cols = ["Cta", "OL", "TaxSurp", "OCAT", "negNOA"]
    by = {m: g.sort_values("q").drop_duplicates("t", keep="last")
          for m, g in D.groupby("avail")}
    cur = {}
    panel = {}
    for m in M.index:
        if m in by:
            for _, r in by[m].iterrows():
                cur[r.t] = {c: r.get(c) for c in fin_cols}
        v = months_hist.get(str(m)) or {}
        mm = set(v.get("spx") or []) | set(v.get("ndx") or [])
        if not mm:
            continue
        rec = []
        for t in mm:
            if t not in M.columns or pd.isna(M.at[m, t]):
                continue
            d = dict(cur.get(t) or {})
            d["Mom"] = MOM.at[m, t] if t in MOM.columns else np.nan
            d["negResid"] = NEGRES.at[m, t] if t in NEGRES.columns else np.nan
            d["negOsc"] = OSC.at[m, t] if (m in OSC.index and t in OSC.columns) else np.nan
            d["t"] = t; d["s"] = sect.get(t) or hsec.get(t) or "?"
            rec.append(d)
        if len(rec) < MIN_POOL:
            continue
        g = pd.DataFrame(rec)
        for c in SIGS:
            if c not in g:
                g[c] = np.nan
            g[c] = g.groupby("s")[c].transform(
                lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * 0)
            g[c] = g[c].clip(-3, 3)
        panel[m] = g
    ms = sorted(panel)
    print("형성월 %d개 (%s ~ %s) · 후보 중앙 %d종"
          % (len(ms), ms[0], ms[-1], int(np.median([len(panel[m]) for m in ms]))))
    cov = {c: float(np.mean([panel[m][c].notna().mean() for m in ms])) * 100 for c in SIGS}
    print("   신호 커버(후보 대비 평균): " + " · ".join("%s %.0f%%" % (c, cov[c]) for c in SIGS))

    # ── 실행기 ────────────────────────────────────────────────────────────
    def run(wfun, weight="cap"):
        ls, mo = [], []
        for i, m in enumerate(ms):
            g = panel[m]
            w = wfun(i, m)
            sc = np.nansum(g[SIGS].to_numpy() * w, axis=1)
            cnt = (~np.isnan(g[SIGS].to_numpy())).sum(axis=1)
            sc = np.where(cnt >= 3, sc / np.maximum(cnt, 1), np.nan)   # 3개 이상만
            gg = g.assign(sc=sc).dropna(subset=["sc"])
            if len(gg) < MIN_POOL:
                continue
            n = max(MIN_N, int(round(len(gg) / 10)))
            hi = list(gg.sort_values("sc", ascending=False).t.head(n))
            lo = list(gg.sort_values("sc").t.head(n))
            nx = [x for x in M.index if x > m][:1]
            if not nx:
                break

            def ret(names):
                if weight == "cap":
                    ww = CAP.loc[m, names].astype(float)
                    ww = ww / ww.sum() if np.isfinite(ww).all() and ww.sum() > 0 else \
                        pd.Series(1.0 / len(names), index=names)
                else:
                    ww = pd.Series(1.0 / len(names), index=names)
                return float((ww * MR.loc[nx[0], names].astype(float).fillna(0)).sum())
            ls.append(ret(hi) - ret(lo)); mo.append(str(m))
        return np.array(ls), mo

    def tt(x):
        x = x[np.isfinite(x)]
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 3 else np.nan

    # ⓐ 단일 신호
    print("\n■ ⓐ 단일 신호 (시점정확 · 섹터중립 · 시총가중 · 보유 1개월)")
    single = {}
    for j, c in enumerate(SIGS):
        w = np.zeros(len(SIGS)); w[j] = 1.0
        a, _ = run(lambda i, m, w=w: w)
        single[c] = {"mean_pct": float(a.mean()) * 100, "t": tt(a), "n": len(a)}
        print("   %-9s 월 %+6.3f%% (t %5.2f · n %d)" % (c, single[c]["mean_pct"], single[c]["t"], len(a)))
    best = max(single, key=lambda k: single[k]["mean_pct"])
    print("   → 최고 단일: %s (월 %+.3f%%)" % (best, single[best]["mean_pct"]))

    # ⓑ 동일가중
    ew_w = np.ones(len(SIGS))
    a_ew, _ = run(lambda i, m: ew_w)
    print("\n■ ⓑ 동일가중 결합  월 %+.3f%% (t %.2f · n %d)"
          % (a_ew.mean() * 100, tt(a_ew), len(a_ew)))

    # 축소 추정 — 확장창으로 b̂ = (Σ + γI)⁻¹ μ̂
    hist_ret = {c: [] for c in SIGS}

    def shrink_w(i, m):
        if i < 36:
            return ew_w
        Xr = np.array([hist_ret[c][:i] for c in SIGS], float)     # 신호별 과거 롱숏 수익
        ok = np.isfinite(Xr).all(axis=0)
        Xr = Xr[:, ok]
        if Xr.shape[1] < 24:
            return ew_w
        mu = Xr.mean(axis=1)
        Sg = np.cov(Xr) + 1e-10 * np.eye(len(SIGS))
        gam = np.trace(Sg) / len(SIGS)                            # κ 대용 — 표본 밖에서 안 고른다
        b = np.linalg.solve(Sg + gam * np.eye(len(SIGS)), mu)
        n = np.linalg.norm(b)
        return b / n * np.sqrt(len(SIGS)) if n > 0 else ew_w

    # 신호별 월 수익을 먼저 쌓는다(축소 추정 입력)
    for c in SIGS:
        j = SIGS.index(c)
        w = np.zeros(len(SIGS)); w[j] = 1.0
        a, _ = run(lambda i, m, w=w: w)
        hist_ret[c] = list(a) + [np.nan] * (len(ms) - len(a))
    a_sh, _ = run(shrink_w)
    print("■ 축소 추정 결합  월 %+.3f%% (t %.2f · n %d)"
          % (a_sh.mean() * 100, tt(a_sh), len(a_sh)))

    # ⓒ 무작위 가중
    print("\n■ ⓒ 무작위 가중 %d회" % NRW)
    rng = np.random.default_rng(SEED)
    rw = np.empty(NRW)
    for q in range(NRW):
        w = rng.normal(size=len(SIGS))
        w = w / np.linalg.norm(w) * np.sqrt(len(SIGS))
        rw[q] = run(lambda i, m, w=w: w)[0].mean() * 100
        if (q + 1) % 50 == 0:
            print("   ... %d회" % (q + 1))
    act = a_sh.mean() * 100
    pct = float((rw < act).mean()) * 100
    print("   축소 추정 %+.3f%% · 무작위 평균 %+.3f%% (sd %.3f) · 백분위 %.1f"
          % (act, rw.mean(), rw.std(ddof=1), pct))
    print("   동일가중 %+.3f%% 의 백분위 %.1f" % (a_ew.mean() * 100, float((rw < a_ew.mean() * 100).mean()) * 100))

    F = {"F1 시점정확 롱숏 ≤ 0": act <= 0,
         "F2 최고 단일 신호를 못 넘음": act <= single[best]["mean_pct"],
         "F3 무작위 가중 상위 5% 밖": pct < 95.0,
         "F4 10bp 후 ≤ 0": act - 0.10 * 2 <= 0}
    print("\n■ 기각 조건")
    for k, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k))
    print("   %s F5 동일가중 대비 — 축소 %+.3f vs 동일 %+.3f%s"
          % ("⚠" if act <= a_ew.mean() * 100 else "✅", act, a_ew.mean() * 100,
             "  → 「축소 추정은 불필요」" if act <= a_ew.mean() * 100 else ""))
    verdict = "기각" if any(F.values()) else "채택"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"prereg": "PREREG-2026-09-19-COMBO", "commit": "883b96e",
         "signals": SIGS, "coverage": cov, "n_months": len(ms),
         "single": single, "best_single": best,
         "equal": {"mean_pct": float(a_ew.mean()) * 100, "t": tt(a_ew)},
         "shrink": {"mean_pct": act, "t": tt(a_sh)},
         "random_w": {"n": NRW, "mean": float(rw.mean()), "sd": float(rw.std(ddof=1)),
                      "pctile_shrink": pct,
                      "pctile_equal": float((rw < a_ew.mean() * 100).mean()) * 100},
         "fails": {k: bool(v) for k, v in F.items()}, "verdict": verdict},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
