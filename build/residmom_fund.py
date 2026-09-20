# -*- coding: utf-8 -*-
"""build/residmom_fund.py — 잔차 모멘텀 분기·밴드판. 규약은 PREREG-2026-09-20-RESIDMOM.md.

🚨 등록서에 적은 것만 한다. 결과를 보고 밴드 폭(10/20)·배합(10%)·크기(10종)·
   회귀 창(36개월)을 바꾸지 않는다. 밴드 없는 판은 **회전 진단용**이고 판정에 안 쓴다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
D18 = r"C:\Users\Win10\Documents\여두_20260918"
OUT = os.path.join(DATA, "_residmom_fund.json")

# ── 등록서 §1 의 상수 ──────────────────────────────────────────────────────
WIN, MINOBS = 36, 30       # 회귀 창 36개월 · 유효 30개월 이상
MOM_A, MOM_B = 12, 2       # 잔차 합 구간 t-12 ~ t-2 (직전 1개월 건너뜀)
TOPN, BAND = 10, 20        # 상위 10 진입 · 상위 20 밖으로 나가야 이탈
COST, MIXW = 0.0025, 0.10
NSHUF, SEED = 200, 20260920
FORM_M = (3, 6, 9, 12)
FF3 = ["mkt_rf", "smb", "hml"]


def ols_t(y, X):
    """절편 t 와 계수. X 는 상수항 없이 준다."""
    Xm = np.column_stack([np.ones(len(y))] + [X[:, i] for i in range(X.shape[1])])
    bh, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    e = y - Xm @ bh
    dof = max(1, len(y) - Xm.shape[1])
    s2 = float(e @ e) / dof
    se = np.sqrt(np.diag(np.linalg.inv(Xm.T @ Xm) * s2))
    return float(bh[0]), float(bh[0] / se[0]) if se[0] > 0 else np.nan, bh[1:]


def main():
    # ── 가격 ──────────────────────────────────────────────────────────────
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
    SEC = {s["t"]: s.get("sector") for s in st["stocks"]}

    # ── FF3 (진짜 파마-프렌치) ────────────────────────────────────────────
    ff = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
    FD = pd.DataFrame(ff["series"], index=pd.to_datetime(ff["dates"])) / 100.0
    MF = (1 + FD).groupby(FD.index.to_period("M")).prod() - 1
    print("FF 월 팩터 %d개월 (%s ~ %s)" % (len(MF), MF.index[0], MF.index[-1]))

    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    months = hist["months"]

    idx = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_index.pkl"))
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(os.path.join(D18,
        r"01_이관묶음\01_우량성장선별_산출물\idx_div_monthly_20260918.csv"))
    idiv = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
    BM = {m: ipr[m] + idiv[m] for m in ipr if m in idiv and pd.notna(ipr[m])}

    qg = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_monthly.pkl"))
    fund_sel = {}
    for f, g in qg[qg.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) in FORM_M:
            fund_sel[f] = dict(zip(g.tkr, g.wtgt / 100.0))

    # ── 점수 ──────────────────────────────────────────────────────────────
    forms = [m for m in sorted(months) if int(m[5:7]) in FORM_M
             and pd.Period(m, freq="M") in MR.index]

    def score(fm):
        """형성월 fm 의 {티커: 잔차 모멘텀 z}. t-1 까지만 쓴다."""
        p = pd.Period(fm, freq="M")
        lo, hi = p - WIN, p - 1                       # 회귀 창 t-36 ~ t-1
        if lo < MR.index[0] or hi not in MF.index:
            return {}
        widx = pd.period_range(lo, hi, freq="M")
        F = MF.reindex(widx)[FF3 + ["rf"]]
        if F[FF3].isna().any().any():
            return {}
        uni = [t for t in (months[fm].get("spx") or []) if t in MR.columns]
        out = {}
        Fx = F[FF3].to_numpy()
        rf = F["rf"].to_numpy()
        m_lo, m_hi = p - MOM_A, p - MOM_B             # 잔차 합 구간
        mask = np.array([(m_lo <= w <= m_hi) for w in widx])
        for t in uni:
            y = MR.reindex(widx)[t].to_numpy()
            ok = np.isfinite(y) & np.isfinite(Fx).all(axis=1)
            if ok.sum() < MINOBS:
                continue
            ye = y[ok] - rf[ok]
            Xm = np.column_stack([np.ones(ok.sum()), Fx[ok]])
            bh, *_ = np.linalg.lstsq(Xm, ye, rcond=None)
            res_ok = ye - Xm @ bh
            sd = float(res_ok.std(ddof=len(FF3) + 1)) if ok.sum() > len(FF3) + 1 else 0.0
            if not (sd > 0):
                continue
            res = np.full(len(widx), np.nan)
            res[ok] = res_ok
            seg = res[mask]
            if np.isnan(seg).sum() > 2:               # 모멘텀 구간이 너무 비면 뺀다
                continue
            out[t] = float(np.nansum(seg) / sd)
        return out

    picks, picks_nb, diag = {}, {}, []
    held = set()
    for fm in forms:
        sc = score(fm)
        diag.append({"m": fm, "n": len(sc)})
        if len(sc) < TOPN:
            continue
        order = sorted(sc.items(), key=lambda x: -x[1])
        rank = {t: i for i, (t, _) in enumerate(order)}
        top = [t for t, _ in order[:TOPN]]
        picks_nb[fm] = {t: 1.0 / TOPN for t in top}   # 밴드 없는 판(진단용)
        keep = [t for t in held if rank.get(t, 10 ** 9) < BAND]
        new = [t for t in top if t not in keep]
        sel = (keep + new)[:TOPN]
        if len(sel) < TOPN:
            sel = sel + [t for t in top if t not in sel][:TOPN - len(sel)]
        held = set(sel)
        picks[fm] = {t: 1.0 / len(sel) for t in sel}
        diag[-1]["blocked"] = len([t for t in top if t not in sel])
    DG = pd.DataFrame(diag)
    print("\n■ 형성 %d분기 (%s ~ %s) · 후보 중앙 %d종 (최소 %d)"
          % (len(DG), DG.m.iloc[0], DG.m.iloc[-1], DG.n.median(), DG.n.min()))
    thin = int((DG.n < 30).sum())
    print("   후보 30종 미만 분기 %d개 (%.1f%%) → F5 %s"
          % (thin, 100 * thin / len(DG), "걸림" if thin / len(DG) > 0.10 else "통과"))
    bl = DG.get("blocked")
    if bl is not None:
        print("   **밴드가 막은 신규 진입 중앙 %.0f종/분기** (최대 %.0f)"
              % (bl.median(), bl.max()))

    def run(sel):
        out, trn, prev = {}, {}, {}
        for fm in sorted(sel):
            w = dict(sel[fm])
            if not w:
                continue
            z = sum(w.values()); w = {t: v / z for t, v in w.items()}
            trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
            trn[fm] = trade
            first = True
            for k in (1, 2, 3):
                q_ = int(fm[:4]) * 12 + int(fm[5:7]) - 1 + k
                hm = "%04d-%02d" % (q_ // 12, q_ % 12 + 1)
                hp = pd.Period(hm, freq="M")
                if hp not in MR.index:
                    continue
                ok = {t: v for t, v in w.items()
                      if t in MR.columns and pd.notna(MR.at[hp, t])}
                s = sum(ok.values())
                if s <= 0:
                    continue
                r = sum(v / s * float(MR.at[hp, t]) for t, v in ok.items())
                out[hm] = r - (trade * COST if first else 0.0)
                first = False
                w = {t: (v / s) * (1 + float(MR.at[hp, t])) for t, v in ok.items()}
                zz = sum(w.values()); w = {t: v / zz for t, v in w.items()}
            prev = w
        return pd.Series(out, dtype="float64"), trn

    def ex(s):
        ms = [m for m in s.index if m in BM]
        return pd.Series([s[m] - BM[m] for m in ms],
                         index=pd.PeriodIndex(ms, freq="M"), dtype="float64")

    def stat(e, trn, turn=None):
        n = len(e); te = float(e.std(ddof=1) * np.sqrt(12) * 100)
        return {"y_pp": float(e.mean() * 1200), "te": te,
                "t": float(e.mean() / (e.std(ddof=1) / np.sqrt(n))),
                "ir": float(e.mean() * 1200 / te) if te else np.nan,
                "win": float((e > 0).mean() * 100), "n": n,
                "turn": turn if turn is not None
                else (float(np.mean(list(trn.values())) * 4) if trn else np.nan)}

    r_r, r_trn = run(picks)
    nb_r, nb_trn = run(picks_nb)
    f_r, f_trn = run(fund_sel)
    mix = {}
    for fm in sorted(set(picks) & set(fund_sel)):
        w = {}
        for t, v in fund_sel[fm].items():
            w[t] = w.get(t, 0.0) + (1 - MIXW) * v
        for t, v in picks[fm].items():
            w[t] = w.get(t, 0.0) + MIXW * v
        mix[fm] = w
    m_r, m_trn = run(mix)

    E_r, E_f, E_m, E_nb = ex(r_r), ex(f_r), ex(m_r), ex(nb_r)
    j = E_r.index.intersection(E_f.index).intersection(E_m.index)
    E_r, E_f, E_m = E_r.reindex(j), E_f.reindex(j), E_m.reindex(j)
    S_r, S_f, S_m = stat(E_r, r_trn), stat(E_f, f_trn), stat(E_m, m_trn)
    S_nb = stat(E_nb.reindex(j).dropna(), nb_trn)

    print("\n■ 성적 (비용 후 · 잣대 B) · %d개월 (%s ~ %s)" % (len(j), j[0], j[-1]))
    print("   %-16s %10s %8s %7s %7s %7s %8s" % ("", "초과/년", "TE", "t", "IR", "승률", "연회전"))
    for nm, s in (("펀드", S_f), ("잔차모멘텀 밴드", S_r), ("혼합 90/10", S_m)):
        print("   %-16s %+9.2f%%p %7.2f%% %7.2f %7.2f %6.1f%% %7.2f회"
              % (nm, s["y_pp"], s["te"], s["t"], s["ir"], s["win"], s["turn"]))
    print("   혼합 − 펀드   초과 %+.2f%%p · TE %+.2f%%p · **IR %+.3f**"
          % (S_m["y_pp"] - S_f["y_pp"], S_m["te"] - S_f["te"], S_m["ir"] - S_f["ir"]))
    lo_, hi_ = sorted([S_f["y_pp"], S_r["y_pp"]])
    print("   혼합이 두 부분 사이에 있나 — %s (%.2f ≤ %.2f ≤ %.2f)"
          % ("예" if lo_ - 1e-9 <= S_m["y_pp"] <= hi_ + 1e-9 else "🚨 아니다 = 버그",
             lo_, S_m["y_pp"], hi_))
    print("   ⚠ 진단(판정 아님) — 밴드 없는 판: 초과 %+.2f%%p · **회전 %.2f회**"
          % (S_nb["y_pp"], S_nb["turn"]))

    a, ta, _ = ols_t(E_r.to_numpy(), E_f.to_numpy().reshape(-1, 1))
    corr = float(np.corrcoef(E_r, E_f)[0, 1])
    print("\n■ F3 펀드 위의 증분 — 알파 연 %+.2f%%p · **t %.2f** · 상관 %+.2f"
          % (a * 1200, ta, corr))

    # ── F8 펀드 + x-mom12 이중 통제 ──────────────────────────────────────
    ps = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    SS = {s["sid"]: s for s in ps["strategies"]}
    mm = (SS["x-mom12"].get("chart") or {}).get("monthly") or []
    MOM = pd.Series({pd.Period(x["m"], freq="M"): (x["r"] - x["b"]) / 100.0
                     for x in mm if x.get("r") is not None and x.get("b") is not None},
                    dtype="float64")
    j2 = j.intersection(MOM.index)
    a8, t8, b8 = ols_t(E_r.reindex(j2).to_numpy(),
                       np.column_stack([E_f.reindex(j2).to_numpy(), MOM.reindex(j2).to_numpy()]))
    print("\n■ F8 펀드 + x-mom12 이중 통제 (%d개월) — 알파 연 %+.2f%%p · **t %.2f**"
          % (len(j2), a8 * 1200, t8))
    print("   계수 — 펀드 %+.2f · x-mom12 %+.2f · 잔차모멘텀 vs 총수익모멘텀 상관 %+.2f"
          % (b8[0], b8[1], float(np.corrcoef(E_r.reindex(j2), MOM.reindex(j2))[0, 1])))
    print("   단독 통제 알파 %+.2f%%p → 이중 통제 %+.2f%%p (남은 비율 %.0f%%)"
          % (a * 1200, a8 * 1200, 100 * a8 / a if a else np.nan))

    ov = []
    for fm in sorted(set(picks) & set(fund_sel)):
        A, B = fund_sel[fm], picks[fm]
        za, zb = sum(A.values()), sum(B.values())
        ov.append({"m": fm, "n": len(set(A) & set(B)),
                   "w": 100 * sum(min(A[t] / za, B[t] / zb) for t in set(A) & set(B))})
    OV = pd.DataFrame(ov)
    print("\n■ F6 펀드와 겹침 — 종목 중앙 %.0f종(최대 %d) · 비중 중앙 %.1f%% → %s"
          % (OV.n.median(), OV.n.max(), OV.w.median(),
             "걸림" if OV.w.median() > 50 else "통과"))

    # F9 섹터 쏠림
    top_sec = []
    for fm, w in picks.items():
        d_ = {}
        for t in w:
            d_[SEC.get(t) or "?"] = d_.get(SEC.get(t) or "?", 0) + 10
        top_sec.append(max(d_.values()))
    ts = pd.Series(top_sec, dtype="float64")
    print("\n■ F9 섹터 쏠림 — 최대 섹터 비중 중앙 %.0f%% (최대 %.0f%%) → %s"
          % (ts.median(), ts.max(), "걸림" if ts.median() > 40 else "통과"))

    h = len(j) // 2
    halves = {}
    print("\n■ 표본 절반씩")
    for nm, sl in (("앞 절반", slice(0, h)), ("뒤 절반", slice(h, None))):
        aa, tt, _ = ols_t(E_r.iloc[sl].to_numpy(), E_f.iloc[sl].to_numpy().reshape(-1, 1))
        halves[nm] = aa
        print("   %s (%s~%s)  단독 %+6.2f%%p · 증분 %+6.2f%%p (t %5.2f)"
              % (nm, j[sl][0], j[sl][-1], E_r.iloc[sl].mean() * 1200, aa * 1200, tt))

    rng = np.random.default_rng(SEED)
    shuf = []
    for _ in range(NSHUF):
        sel = {}
        for fm in picks:
            uni = [t for t in (months[fm].get("spx") or [])
                   if t in M.columns and pd.notna(M.at[pd.Period(fm, freq="M"), t])]
            if len(uni) < TOPN:
                continue
            pk = rng.choice(len(uni), size=TOPN, replace=False)
            sel[fm] = {uni[i]: 1.0 / TOPN for i in pk}
        e = ex(run(sel)[0]).reindex(j).dropna()
        if len(e) > 12:
            shuf.append(float(e.mean() * 1200))
    shuf = np.array(shuf)
    pct = float((shuf < S_r["y_pp"]).mean() * 100)
    print("\n■ F4 셔플 %d회 — 실측 %+.2f%%p · 셔플 평균 %+.2f%%p (sd %.2f) · **백분위 %.1f**"
          % (len(shuf), S_r["y_pp"], shuf.mean(), shuf.std(ddof=1), pct))

    # 원 규칙(ETF 대리변수)과 명단 겹침
    _h = SS.get("x-residmom", {}).get("holdings") or {}
    # ⚠ holdings 는 dict(kind·as_of·n·tickers) 다. 처음에 그대로 순회해서
    #   **키 넷을 티커로 읽고 «겹침 0/10»** 이라 찍었다. 명단 비교는 tickers 를 쓴다.
    rm = list(_h.get("tickers") or []) if isinstance(_h, dict) else list(_h)
    last = sorted(picks)[-1]
    ovl = len(set(rm) & set(picks[last]))
    print("\n■ FF 정본판 vs ETF 대리변수판 — 오늘 명단 겹침 %d/10종" % ovl)
    print("   FF 정본(%s): %s" % (last, " · ".join(sorted(picks[last]))))
    print("   ETF 대리변수: %s" % " · ".join(sorted(rm)))

    f = {"F1": S_r["y_pp"] <= 0, "F2": (S_m["ir"] - S_f["ir"]) < 0.05,
         "F3": ta < 2, "F4": pct < 95, "F5": thin / len(DG) > 0.10,
         "F6": OV.w.median() > 50,
         "F7": halves["앞 절반"] * halves["뒤 절반"] <= 0,
         "F8": t8 < 1.5, "F9": ts.median() > 40}
    txt = {"F1": "단독 초과 ≤ 0", "F2": "IR 개선 < 0.05", "F3": "증분 알파 t < 2",
           "F4": "셔플 백분위 < 95", "F5": "후보 30종 미만 분기 > 10%",
           "F6": "펀드와 겹침 > 50%", "F7": "뒤 절반 부호 반전",
           "F8": "펀드+모멘텀 이중 통제 t < 1.5", "F9": "섹터 쏠림 중앙 > 40%"}
    print("\n■ 기각 조건")
    for k in sorted(f):
        print("   %s %s %s" % ("❌ 걸림" if f[k] else "✅ 통과", k, txt[k]))
    verdict = "기각" if any(f.values()) else "등록 조건 전부 통과"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": "build/PREREG-2026-09-20-RESIDMOM.md",
        "commit_before": "a289cb0c96e7a2c149a25198a4e23a120b22957c",
        "blob": "2a25ab771de77a76c97406a582de49f53e8737d6",
        "const": {"WIN": WIN, "MINOBS": MINOBS, "TOPN": TOPN, "BAND": BAND,
                  "COST": COST, "MIXW": MIXW, "NSHUF": NSHUF, "SEED": SEED},
        "window": {"start": str(j[0]), "end": str(j[-1]), "n": len(j)},
        "stats": {"fund": S_f, "resid": S_r, "mix": S_m, "noband": S_nb},
        "incr": {"alpha_y_pp": a * 1200, "t": ta, "corr": corr},
        "f8": {"alpha_y_pp": a8 * 1200, "t": t8, "n": len(j2),
               "beta_fund": float(b8[0]), "beta_mom": float(b8[1])},
        "overlap_fund": {"n_med": float(OV.n.median()), "w_med": float(OV.w.median())},
        "sector_top_med": float(ts.median()),
        "shuffle": {"n": len(shuf), "mean": float(shuf.mean()),
                    "sd": float(shuf.std(ddof=1)), "pct": pct},
        "last_holdings": sorted(picks[last]), "etf_proxy_holdings": sorted(rm),
        "diag": DG.to_dict("records"), "fails": f, "verdict": verdict,
        "series": {"resid": {str(k): float(v) for k, v in E_r.items()},
                   "fund": {str(k): float(v) for k, v in E_f.items()},
                   "mix": {str(k): float(v) for k, v in E_m.items()}},
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
