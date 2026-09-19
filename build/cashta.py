# -*- coding: utf-8 -*-
"""build/cashta.py — 현금보유 프리미엄 (PREREG-2026-09-19-CASHTA · 계산 전 4ba7eed)

  Cta-원문 = (현금 + 단기투자) / 자산총계   ← 주 판정
  Cta-하한 = 현금 / 자산총계                ← 병기(판정 안 함)
  월간 재구성 · 최소 4개월 지난 분기 · **그 달 후보의 십분위** · 섹터중립이 본문

🚨 E38(순영업자산) 뒷면 검사가 성적보다 먼저다(카드 ⑦).

  python build/cashta.py
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_cashta.json")
MIN_POOL, MIN_N, NSHUF, SEED = 30, 10, 200, 20260919
HOLDS = (1, 6, 12)
LAG_M, COST = 4, 0.0010
FIN = {"Financials"}


def qser(tagdoc, key):
    tg = (tagdoc.get("tags") or {}).get(key) or {}
    out = {}
    for end, v, *_ in (tg.get("i") or tg.get("q") or tg.get("a") or []):
        out[end] = float(v)
    return out


def main():
    base, ext = {}, {}
    for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8")); base[j["t"]] = j
    for d in (os.path.join(DATA, "fxe"), os.path.join(DATA, "fxe_pit")):
        for p in glob.glob(os.path.join(d, "*.json")):
            j = json.load(io.open(p, encoding="utf-8")); ext[j["t"]] = j

    rows = []
    for t, b in base.items():
        cash, at = qser(b, "cash"), qser(b, "asset")
        noa_a, noa_l = qser(b, "asset"), qser(b, "liab")
        sti = qser(ext.get(t, {}), "sti")
        for end, a in at.items():
            if not a or a <= 0:
                continue
            c = cash.get(end)
            if c is None:
                continue
            r = {"t": t, "end": end, "asset": a, "cta_low": c / a}
            s = sti.get(end)
            if s is not None:
                r["cta_full"] = (c + s) / a
            # E38 뒷면 — 순영업자산 = (자산 − 현금) − (부채 − 차입금 근사) / 자산
            l_ = noa_l.get(end)
            if l_ is not None:
                r["noa"] = ((a - c) - l_) / a
            rows.append(r)
    D = pd.DataFrame(rows)
    D["q"] = pd.PeriodIndex(pd.to_datetime(D.end), freq="Q")
    D = D.sort_values(["t", "q"]).drop_duplicates(["t", "q"], keep="last")
    D["avail"] = (D.q.dt.end_time + pd.DateOffset(months=LAG_M)).dt.to_period("M")
    print("분기 %d행 · %d종 · %s ~ %s" % (len(D), D.t.nunique(), D.q.min(), D.q.max()))
    for k in ("cta_low", "cta_full", "noa"):
        print("   %-9s %5d행 · %3d종" % (k, D[k].notna().sum(), D.loc[D[k].notna(), "t"].nunique()))

    mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    hsec = hist.get("sector") or {}
    D["sector"] = D.t.map(lambda x: sect.get(x) or hsec.get(x) or "?")

    # ── 가격·시총 ─────────────────────────────────────────────────────────
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
    shrow = []
    for t, b in base.items():
        s = (b.get("tags") or {}).get("sh") or (b.get("tags") or {}).get("sho") or {}
        for end, v, *_ in (s.get("i") or s.get("q") or s.get("a") or []):
            shrow.append({"t": t, "m": end[:7], "sh": float(v)})
    SW = pd.DataFrame(shrow).pivot_table(index="m", columns="t", values="sh", aggfunc="last")
    SW.index = pd.PeriodIndex(SW.index, freq="M"); SW = SW.reindex(M.index).ffill()
    CAP = pd.DataFrame(M.reindex(columns=SW.columns).to_numpy() * SW.to_numpy(),
                       index=M.index, columns=SW.columns).reindex(columns=M.columns)
    print("   가격 %d종 · 월 %d개" % (P.shape[1], len(M)))

    def build_panel(col, neutral, drop_fin):
        """{월: {종목: 점수}} — 그 달까지 나온 가장 최근 분기값."""
        d = D[D[col].notna()].copy()
        if drop_fin:
            d = d[~d.sector.isin(FIN)]
        by = {}
        for m, g in d.groupby("avail"):
            g = g.sort_values("q").drop_duplicates("t", keep="last")
            by[m] = g[["t", col, "sector"]].rename(columns={col: "v"})
        cur, out = {}, {}
        for m in M.index:
            if m in by:
                for _, r in by[m].iterrows():
                    cur[r.t] = (r.v, r.sector)
            have = {t: v for t, v in cur.items()
                    if t in M.columns and pd.notna(M.at[m, t])}
            if not have:
                continue
            g = pd.DataFrame([{"t": t, "v": v[0], "sector": v[1]} for t, v in have.items()])
            if neutral:
                g["z"] = g.groupby("sector").v.transform(
                    lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * 0)
            else:
                g["z"] = (g.v - g.v.mean()) / (g.v.std(ddof=0) or 1)
            out[m] = dict(zip(g.t, g.z))
        return out

    def legs(pan, weight, hold, shuf=None, rng=None, sectmap=None, want_months=False):
        ls, ns, traded, mos = [], [], [], []
        prev = set()
        for m in sorted(pan):
            d = pan[m]
            ns.append(len(d))
            if len(d) < MIN_POOL:
                continue
            n_sel = max(MIN_N, int(round(len(d) / 10)))     # 🚨 그 달 후보의 십분위
            ts = list(d)
            v = np.array([d[t] for t in ts], float)
            if shuf:
                if sectmap is not None:                     # 섹터 안에서만 섞는다
                    v = v.copy()
                    idx = {}
                    for i, t in enumerate(ts):
                        idx.setdefault(sectmap.get(t, "?"), []).append(i)
                    for _s, ii in idx.items():
                        v[ii] = rng.permutation(v[ii])
                else:
                    v = rng.permutation(v)
            o = np.argsort(v)
            hi = [ts[i] for i in o[-n_sel:]]
            lo = [ts[i] for i in o[:n_sel]]
            fut = [x for x in M.index if x > m][:hold]
            if len(fut) < hold:
                break
            traded.append(len(set(hi) - prev) / max(1, len(hi)))
            prev = set(hi)

            def ret(names):
                if weight == "cap":
                    w = CAP.loc[m, names].astype(float)
                    w = w / w.sum() if np.isfinite(w).all() and w.sum() > 0 else \
                        pd.Series(1.0 / len(names), index=names)
                else:
                    w = pd.Series(1.0 / len(names), index=names)
                return float(sum((w * MR.loc[x, names].astype(float).fillna(0)).sum()
                                 for x in fut)) / hold
            ls.append(ret(hi) - ret(lo))
            mos.append(str(m))
        return (np.array(ls), np.array(ns), np.array(traded), mos) if want_months else (np.array(ls), np.array(ns), np.array(traded))

    def tt(x):
        x = x[np.isfinite(x)]
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 3 else float("nan")

    # ── 카드 ⑦ E38 뒷면 검사 — 성적보다 먼저 ──────────────────────────────
    print("\n■ 카드 ⑦ E38(순영업자산) 뒷면 검사 — 성적보다 먼저")
    c2 = D.dropna(subset=["cta_full", "noa"])
    print("   Cta-원문 vs 순영업자산 횡단면 상관 %.3f (n %d · %d종)"
          % (c2.cta_full.corr(c2.noa), len(c2), c2.t.nunique()))
    pan_c = build_panel("cta_full", True, True)
    pan_n = build_panel("noa", True, True)
    a_c, _, _ = legs(pan_c, "cap", 1)
    a_n, _, _ = legs(pan_n, "cap", 1)
    k = min(len(a_c), len(a_n))
    if k > 10:
        x, y = a_n[-k:], a_c[-k:]
        b1 = np.polyfit(x, y, 1)
        resid = y - (b1[0] * x + b1[1])
        se = resid.std(ddof=2) / np.sqrt(k)
        print("   롱숏 수익 상관 %.3f · E38 회귀 알파 %+.4f%%/월 (t %.2f · n %d)"
              % (np.corrcoef(x, y)[0, 1], b1[1] * 100, b1[1] / se, k))
        alpha_t = float(b1[1] / se)
    else:
        alpha_t = float("nan"); print("   ⚠ 겹치는 관측 부족")

    # ── 성적 ──────────────────────────────────────────────────────────────
    print("\n■ 성적 — 롱숏 · 월 %% · 그 달 후보의 십분위")
    res = {}
    for col, nm in (("cta_full", "Cta-원문(현금+단기투자)"), ("cta_low", "Cta-하한(현금만)")):
        res[col] = {}
        for neutral in (True, False):
            for dfin in (True, False):
                pan = build_panel(col, neutral, dfin)
                key = "%s|%s" % ("섹터중립" if neutral else "비중립",
                                 "금융제외" if dfin else "금융포함")
                res[col][key] = {}
                for w in ("cap", "ew"):
                    cells = []
                    for h in HOLDS:
                        a, ns, tr = legs(pan, w, h)
                        cells.append({"mean_pct": float(a.mean()) * 100 if len(a) else np.nan,
                                      "t": tt(a) if len(a) else np.nan, "n": int(len(a)),
                                      "pool_med": int(np.median(ns)) if len(ns) else 0,
                                      "turn": float(tr.mean()) if len(tr) else np.nan})
                    res[col][key][w] = cells
        mn = res[col]["섹터중립|금융제외"]["cap"]
        nn = res[col]["비중립|금융제외"]["cap"]
        ew = res[col]["섹터중립|금융제외"]["ew"]
        print("   [%s]  후보 중앙 %d종 → 분위 %d종 · 월 교체율 %.0f%%"
              % (nm, mn[0]["pool_med"], max(MIN_N, round(mn[0]["pool_med"] / 10)),
                 (mn[0]["turn"] or 0) * 100))
        for lab, cs in (("섹터중립·시총가중", mn), ("섹터중립·동일가중", ew), ("비중립·시총가중", nn)):
            print("      %-16s %s" % (lab, "  ".join(
                "%2d개월 %+6.3f(t%5.2f)" % (h, c["mean_pct"], c["t"]) for h, c in zip(HOLDS, cs))))
    print("   ⚠ 복제(Hou·Xue·Zhang 2020) 시총가중 0.27(t1.36)·0.14(0.69)·0.11(0.58) — 8/8 미달")

    # ── F6 (섹터맞춤) ─────────────────────────────────────────────────────
    have = set(D.loc[D.cta_full.notna(), "t"])
    uni = [c for c in M.columns if c in base]
    gs, wts = [], []
    for s in {sect.get(t, "?") for t in uni}:
        h2 = [t for t in uni if t in have and sect.get(t, "?") == s]
        n2 = [t for t in uni if t not in have and sect.get(t, "?") == s]
        if len(h2) >= 5 and len(n2) >= 5:
            gs.append(MR[h2].mean(axis=1).mean() * 1200 - MR[n2].mean(axis=1).mean() * 1200)
            wts.append(len(h2) + len(n2))
    f6 = float(np.average(gs, weights=wts)) if gs else float("nan")
    print("\n   F6(섹터맞춤) %+.2f%%p · 비교 섹터 %d개" % (f6, len(gs)))

    # ── F2 셔플 ───────────────────────────────────────────────────────────
    print("\n■ F2 셔플 %d회 (주 판정판 · 섹터 안에서만)" % NSHUF)
    rng = np.random.default_rng(SEED)
    pan = build_panel("cta_full", True, True)
    smap = {t: sect.get(t, "?") for t in uni}
    act = res["cta_full"]["섹터중립|금융제외"]["cap"][0]["mean_pct"]
    sh = np.array([legs(pan, "cap", 1, shuf=True, rng=rng, sectmap=smap)[0].mean() * 100
                   for _ in range(NSHUF)])
    pct = float((sh < act).mean()) * 100
    print("   실측 %+.3f%% · 셔플 평균 %+.3f%% (sd %.3f) · 백분위 %.1f"
          % (act, sh.mean(), sh.std(ddof=1), pct))

    _ls, _n2, _t2, _mos = legs(build_panel("cta_full", True, True), "cap", 1, want_months=True)
    mm = res["cta_full"]["섹터중립|금융제외"]["cap"]
    nn = res["cta_full"]["비중립|금융제외"]["cap"]
    net1 = mm[0]["mean_pct"] - (COST * 1e4 / 100) * (mm[0]["turn"] or 0) * 2
    F = {"F1 세 기간 모두 양수 아님": not all(c["mean_pct"] > 0 for c in mm),
         "F2 셔플 상위 5% 밖": pct < 95.0,
         "F3 E38 대비 알파 |t| < 2": abs(alpha_t) < 2 if alpha_t == alpha_t else True,
         "F4 10bp 후 ≤ 0": net1 <= 0,
         "F5 섹터중립 전후 부호 갈림": (mm[0]["mean_pct"] > 0) != (nn[0]["mean_pct"] > 0),
         "F6 섹터맞춤 수익차 |Δ| > 3%p": abs(f6) > 3.0 if f6 == f6 else False}
    print("\n■ 기각 조건")
    for k2, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k2))
    verdict = "기각" if any(F.values()) else "채택"
    print("\n→ 판정: %s" % verdict)
    print("   ⚠ 카드 ⑨(자금조달 국면 분할)는 못 쟀다 — 하이일드 스프레드가 2023-09 부터뿐이다.")
    print("      Jensen(2022)의 「자금제약 국면에만 있다」를 못 재면서 원 주장을 반증한 것이 아니다.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"prereg": "PREREG-2026-09-19-CASHTA", "commit": "4ba7eed",
         "e38": {"alpha_t": alpha_t}, "perf": res, "f6_sector_neutral": f6,
         "shuffle": {"n": NSHUF, "seed": SEED, "mean": float(sh.mean()),
                     "sd": float(sh.std(ddof=1)), "pctile": pct},
         "main_series": {"months": _mos, "ls": [float(x) for x in _ls]},
         "fails": {k2: bool(v) for k2, v in F.items()}, "verdict": verdict,
         "not_measured": ["카드 ⑨ 자금조달 국면 분할 — 하이일드 스프레드 표본 부족"]},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
