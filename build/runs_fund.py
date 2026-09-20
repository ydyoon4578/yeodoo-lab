# -*- coding: utf-8 -*-
"""build/runs_fund.py — 런 검정 분기·밴드판. 규약은 PREREG-2026-09-20-RUNS.md.

🚨 등록서에 적은 것만 한다. 방향(낮은 z 를 산다)을 뒤집지 않고, 결과를 보고
   밴드 폭(10/20)·배합(10%)·크기(10종)·창(252일)을 바꾸지 않는다.
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
OUT = os.path.join(DATA, "_runs_fund.json")

# ── 등록서 §3 의 상수 ──────────────────────────────────────────────────────
WIN = 252                  # 최근 252거래일
MINSIDE = 5                # n1·n2 각각 5 이상
TOPN, BAND = 10, 20        # z 최하위 10 진입 · 상위 20(=z 하위 20) 밖이면 이탈
COST, MIXW = 0.0025, 0.10
TURN_CAP = 4.0             # F9 — 밴드 후 연 회전 상한
NSHUF, SEED = 200, 20260920
FORM_M = (3, 6, 9, 12)


def runs_z(x):
    """부호 런 z(Wald–Wolfowitz). 랩 build/tech_backtest.py 의 runs_z 와 같은 식."""
    sg = [1 if v > 0 else (-1 if v < 0 else 0) for v in x]
    sg = [v for v in sg if v]                    # 0 은 부호가 없다 — 뺀다
    n1 = sum(1 for v in sg if v > 0)
    n2 = len(sg) - n1
    if n1 < MINSIDE or n2 < MINSIDE:
        return None
    r = 1 + sum(1 for j in range(1, len(sg)) if sg[j] != sg[j - 1])
    n = n1 + n2
    mu = 2.0 * n1 * n2 / n + 1.0
    var = 2.0 * n1 * n2 * (2.0 * n1 * n2 - n) / (n * n * (n - 1.0))
    return (r - mu) / (var ** 0.5) if var > 0 else None


def ols_t(y, X):
    Xm = np.column_stack([np.ones(len(y))] + [X[:, i] for i in range(X.shape[1])])
    bh, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    e = y - Xm @ bh
    s2 = float(e @ e) / max(1, len(y) - Xm.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(Xm.T @ Xm) * s2))
    return float(bh[0]), float(bh[0] / se[0]) if se[0] > 0 else np.nan, bh[1:]


def main():
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
    DR = P.pct_change()                      # 일간수익 — 런 검정의 재료
    M = P.resample("M").last(); M.index = M.index.to_period("M")
    MR = M.pct_change()
    SEC = {s["t"]: s.get("sector") for s in st["stocks"]}
    DEF = {"Utilities", "Real Estate", "Consumer Staples", "Health Care"}

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
    dser = pd.Series(range(len(P.index)), index=P.index)
    forms = [m for m in sorted(months) if int(m[5:7]) in FORM_M
             and pd.Period(m, freq="M") in MR.index]

    def score(fm):
        p = pd.Period(fm, freq="M")
        end = P.index[P.index <= p.end_time]
        if len(end) < WIN + 1:
            return {}, np.nan
        i1 = dser[end[-1]]                       # 형성월 마지막 거래일 (포함)
        i0 = i1 - WIN + 1
        if i0 < 1:
            return {}, np.nan
        seg = DR.iloc[i0:i1 + 1]
        uni = [t for t in (months[fm].get("spx") or []) if t in seg.columns]
        out, vols = {}, {}
        for t in uni:
            x = seg[t].to_numpy()
            x = x[np.isfinite(x)]
            if len(x) < WIN * 0.8:
                continue
            z = runs_z(x)
            if z is None:
                continue
            out[t] = z
            vols[t] = float(np.std(x, ddof=1) * np.sqrt(252))
        med_vol = float(np.median(list(vols.values()))) if vols else np.nan
        return out, (out, vols, med_vol)[2]

    def score_full(fm):
        p = pd.Period(fm, freq="M")
        end = P.index[P.index <= p.end_time]
        if len(end) < WIN + 1:
            return {}, {}, np.nan
        i1 = dser[end[-1]]; i0 = i1 - WIN + 1
        if i0 < 1:
            return {}, {}, np.nan
        seg = DR.iloc[i0:i1 + 1]
        uni = [t for t in (months[fm].get("spx") or []) if t in seg.columns]
        out, vols = {}, {}
        for t in uni:
            x = seg[t].to_numpy(); x = x[np.isfinite(x)]
            if len(x) < WIN * 0.8:
                continue
            z = runs_z(x)
            if z is None:
                continue
            out[t] = z
            vols[t] = float(np.std(x, ddof=1) * np.sqrt(252))
        return out, vols, (float(np.median(list(vols.values()))) if vols else np.nan)

    picks, picks_nb, diag, prev_sc = {}, {}, [], None
    held, volrows = set(), []
    for fm in forms:
        sc, vols, medv = score_full(fm)
        row = {"m": fm, "n": len(sc)}
        if prev_sc:
            common = [t for t in sc if t in prev_sc]
            if len(common) > 20:
                row["ac"] = float(np.corrcoef([sc[t] for t in common],
                                              [prev_sc[t] for t in common])[0, 1])
        prev_sc = sc
        if len(sc) < TOPN:
            diag.append(row); continue
        order = sorted(sc.items(), key=lambda x: x[1])       # z 낮은 순
        rank = {t: i for i, (t, _) in enumerate(order)}
        top = [t for t, _ in order[:TOPN]]
        picks_nb[fm] = {t: 1.0 / TOPN for t in top}
        keep = [t for t in held if rank.get(t, 10 ** 9) < BAND]
        new = [t for t in top if t not in keep]
        sel = (keep + new)[:TOPN]
        if len(sel) < TOPN:
            sel += [t for t in top if t not in sel][:TOPN - len(sel)]
        held = set(sel)
        picks[fm] = {t: 1.0 / len(sel) for t in sel}
        row["blocked"] = len([t for t in top if t not in sel])
        row["vol_sleeve"] = float(np.mean([vols[t] for t in sel if t in vols]))
        row["vol_uni_med"] = medv
        row["def_share"] = 100.0 * sum(1 for t in sel if (SEC.get(t) in DEF)) / len(sel)
        diag.append(row)
    DG = pd.DataFrame(diag)
    print("■ 형성 %d분기 (%s ~ %s) · 후보 중앙 %d종 (최소 %d)"
          % (len(DG), DG.m.iloc[0], DG.m.iloc[-1], DG.n.median(), DG.n.min()))
    thin = int((DG.n < 30).sum())
    print("   후보 30종 미만 분기 %d개 (%.1f%%) → F5 %s"
          % (thin, 100 * thin / len(DG), "걸림" if thin / len(DG) > 0.10 else "통과"))
    if "ac" in DG:
        print("   **점수의 분기 자기상관 중앙 %.2f** — 밴드가 걸릴 자리가 있나"
              % DG["ac"].median())
    if "blocked" in DG:
        print("   밴드가 막은 신규 진입 중앙 %.0f종/분기 (최대 %.0f)"
              % (DG["blocked"].median(), DG["blocked"].max()))

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

    def stat(e, trn):
        n = len(e); te = float(e.std(ddof=1) * np.sqrt(12) * 100)
        return {"y_pp": float(e.mean() * 1200), "te": te,
                "t": float(e.mean() / (e.std(ddof=1) / np.sqrt(n))),
                "ir": float(e.mean() * 1200 / te) if te else np.nan,
                "win": float((e > 0).mean() * 100), "n": n,
                "turn": float(np.mean(list(trn.values())) * 4) if trn else np.nan}

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

    E_r, E_f, E_m = ex(r_r), ex(f_r), ex(m_r)
    j = E_r.index.intersection(E_f.index).intersection(E_m.index)
    E_r, E_f, E_m = E_r.reindex(j), E_f.reindex(j), E_m.reindex(j)
    S_r, S_f, S_m = stat(E_r, r_trn), stat(E_f, f_trn), stat(E_m, m_trn)
    S_nb = stat(ex(nb_r).reindex(j).dropna(), nb_trn)

    print("\n■ 성적 (비용 후 · 잣대 B) · %d개월 (%s ~ %s)" % (len(j), j[0], j[-1]))
    print("   %-16s %10s %8s %7s %7s %7s %8s" % ("", "초과/년", "TE", "t", "IR", "승률", "연회전"))
    for nm, s in (("펀드", S_f), ("런검정 밴드판", S_r), ("혼합 90/10", S_m)):
        print("   %-16s %+9.2f%%p %7.2f%% %7.2f %7.2f %6.1f%% %7.2f회"
              % (nm, s["y_pp"], s["te"], s["t"], s["ir"], s["win"], s["turn"]))
    print("   혼합 − 펀드   초과 %+.2f%%p · TE %+.2f%%p · **IR %+.3f**"
          % (S_m["y_pp"] - S_f["y_pp"], S_m["te"] - S_f["te"], S_m["ir"] - S_f["ir"]))
    lo_, hi_ = sorted([S_f["y_pp"], S_r["y_pp"]])
    print("   혼합이 두 부분 사이에 있나 — %s"
          % ("예" if lo_ - 1e-9 <= S_m["y_pp"] <= hi_ + 1e-9 else "🚨 아니다 = 버그"))
    print("   ⚠ 진단(판정 아님) — 밴드 없는 판: 초과 %+.2f%%p · **회전 %.2f회**"
          % (S_nb["y_pp"], S_nb["turn"]))
    print("   **F9 회전 %.2f회 (상한 %.1f) → %s**"
          % (S_r["turn"], TURN_CAP, "걸림" if S_r["turn"] > TURN_CAP else "통과"))

    a, ta, _ = ols_t(E_r.to_numpy(), E_f.to_numpy().reshape(-1, 1))
    print("\n■ F3 펀드 위의 증분 — 알파 연 %+.2f%%p · **t %.2f** · 상관 %+.2f"
          % (a * 1200, ta, float(np.corrcoef(E_r, E_f)[0, 1])))

    # ── F8 삼중 통제 ─────────────────────────────────────────────────────
    ps = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    SS = {s["sid"]: s for s in ps["strategies"]}

    def ser(sid):
        mm = (SS[sid].get("chart") or {}).get("monthly") or []
        return pd.Series({pd.Period(x["m"], freq="M"): (x["r"] - x["b"]) / 100.0
                          for x in mm if x.get("r") is not None and x.get("b") is not None},
                         dtype="float64")
    LV, MO = ser("x-lowvol"), ser("x-mom12")
    j3 = j.intersection(LV.index).intersection(MO.index)
    a8, t8, b8 = ols_t(E_r.reindex(j3).to_numpy(),
                       np.column_stack([E_f.reindex(j3).to_numpy(),
                                        LV.reindex(j3).to_numpy(),
                                        MO.reindex(j3).to_numpy()]))
    print("\n■ F8 펀드 + x-lowvol + x-mom12 삼중 통제 (%d개월)" % len(j3))
    print("   알파 연 %+.2f%%p · **t %.2f** · 계수 펀드 %+.2f · 저변동 %+.2f · 모멘텀 %+.2f"
          % (a8 * 1200, t8, b8[0], b8[1], b8[2]))
    print("   상관 — 저변동 %+.2f · 모멘텀 %+.2f"
          % (float(np.corrcoef(E_r.reindex(j3), LV.reindex(j3))[0, 1]),
             float(np.corrcoef(E_r.reindex(j3), MO.reindex(j3))[0, 1])))
    print("   단독 통제 %+.2f%%p → 삼중 통제 %+.2f%%p (남은 비율 %.0f%%)"
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

    last = sorted(picks)[-1]
    lv_h = set((SS["x-lowvol"].get("holdings") or {}).get("tickers") or [])
    print("\n■ 저변동 규칙과의 명단 겹침 — %d/10종 (%s)"
          % (len(lv_h & set(picks[last])), last))
    print("   런검정: %s" % " · ".join(sorted(picks[last])))
    print("   저변동: %s" % " · ".join(sorted(lv_h)))

    if "vol_sleeve" in DG:
        vs, vu = DG["vol_sleeve"].median(), DG["vol_uni_med"].median()
        print("\n■ P6 실현 변동성 — 슬리브 중앙 %.1f%% vs 유니버스 중앙 %.1f%% → 슬리브가 %s"
              % (100 * vs, 100 * vu, "낮다" if vs < vu else "**높다**"))
        print("   방어 업종(유틸·리츠·필수소비·헬스케어) 비중 중앙 %.0f%%"
              % DG["def_share"].median())

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

    try:
        ffd = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
        FD = pd.DataFrame(ffd["series"], index=pd.to_datetime(ffd["dates"])) / 100.0
        vol = FD.mkt_rf.groupby(FD.index.to_period("M")).std() * np.sqrt(252)
        v = vol.reindex(j).dropna(); q1, q2 = v.quantile(1 / 3), v.quantile(2 / 3)
        print("\n■ 시장변동성 3분위 (월 %)")
        print("   %-12s %9s %9s %9s" % ("", "저변동", "중간", "고변동"))
        for nm, e in (("펀드", E_f), ("런검정", E_r), ("혼합", E_m)):
            cells = []
            for lo, hi in ((None, q1), (q1, q2), (q2, None)):
                s_ = v[(v > lo if lo is not None else v == v)
                       & (v <= hi if hi is not None else v == v)].index
                cells.append(float(e.reindex(s_).mean() * 100))
            print("   %-12s %+8.3f %+8.3f %+8.3f" % (nm, *cells))
    except Exception as e_:
        print("(국면 못 쟀다: %s)" % e_)

    f = {"F1": S_r["y_pp"] <= 0, "F2": (S_m["ir"] - S_f["ir"]) < 0.05,
         "F3": ta < 2, "F4": pct < 95, "F5": thin / len(DG) > 0.10,
         "F6": OV.w.median() > 50,
         "F7": halves["앞 절반"] * halves["뒤 절반"] <= 0,
         "F8": t8 < 1.5, "F9": S_r["turn"] > TURN_CAP}
    txt = {"F1": "단독 초과 ≤ 0", "F2": "IR 개선 < 0.05", "F3": "증분 알파 t < 2",
           "F4": "셔플 백분위 < 95", "F5": "후보 30종 미만 분기 > 10%",
           "F6": "펀드와 겹침 > 50%", "F7": "뒤 절반 부호 반전",
           "F8": "삼중 통제 후 t < 1.5", "F9": "연 회전 > 4회"}
    print("\n■ 기각 조건")
    for k in sorted(f):
        print("   %s %s %s" % ("❌ 걸림" if f[k] else "✅ 통과", k, txt[k]))
    verdict = "기각" if any(f.values()) else "등록 조건 전부 통과"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": "build/PREREG-2026-09-20-RUNS.md",
        "commit_before": "fab20cd11b1b77280db6f1f001f472c5108ea177",
        "blob": "c4c45579746fef161219323fed1e6dd69c7c0074",
        "const": {"WIN": WIN, "TOPN": TOPN, "BAND": BAND, "COST": COST,
                  "MIXW": MIXW, "TURN_CAP": TURN_CAP, "NSHUF": NSHUF, "SEED": SEED},
        "window": {"start": str(j[0]), "end": str(j[-1]), "n": len(j)},
        "stats": {"fund": S_f, "runs": S_r, "mix": S_m, "noband": S_nb},
        "incr": {"alpha_y_pp": a * 1200, "t": ta},
        "f8": {"alpha_y_pp": a8 * 1200, "t": t8, "n": len(j3),
               "beta_fund": float(b8[0]), "beta_lowvol": float(b8[1]),
               "beta_mom": float(b8[2])},
        "overlap_fund": {"n_med": float(OV.n.median()), "w_med": float(OV.w.median())},
        "overlap_lowvol": len(lv_h & set(picks[last])),
        "shuffle": {"n": len(shuf), "mean": float(shuf.mean()),
                    "sd": float(shuf.std(ddof=1)), "pct": pct},
        "last_holdings": sorted(picks[last]),
        "diag": DG.to_dict("records"), "fails": f, "verdict": verdict,
        "series": {"runs": {str(k): float(v) for k, v in E_r.items()},
                   "fund": {str(k): float(v) for k, v in E_f.items()},
                   "mix": {str(k): float(v) for k, v in E_m.items()}},
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
