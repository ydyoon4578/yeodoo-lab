# -*- coding: utf-8 -*-
"""build/guruacc_fund.py — 거장 순매집 분기판. 규약은 PREREG-2026-09-20-GURUACC.md.

🚨 등록서에 적은 것만 한다. 결과를 보고 배합(10%)·크기(10종)·분기 정렬을 바꾸지 않는다.
   신규 진입 포함 변형도 만들지 않는다 — 빠진 건수만 센다.
"""
from __future__ import annotations
import calendar, datetime as dt, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
D18 = r"C:\Users\Win10\Documents\여두_20260918"
OUT = os.path.join(DATA, "_guruacc_fund.json")

# ── 등록서 §2 의 상수 ──────────────────────────────────────────────────────
LAG_D = 45           # 13F 마감 — 그 뒤 첫 월말에 형성
TOPN = 10            # 상위 10종 동일가중
COST = 0.0025        # 왕복 25bp
MIXW = 0.10          # 펀드 90% + 이 축 10%
NSHUF, SEED = 200, 20260920


def form_month(qend):
    """분기말 → 형성 월(자료 가용 +45일 뒤 첫 월말)."""
    a = dt.date.fromisoformat(qend) + dt.timedelta(days=LAG_D)
    return pd.Period("%04d-%02d" % (a.year, a.month), freq="M")


def px_frame():
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
    return M, {s["t"]: s.get("sector") for s in st["stocks"]}


def main():
    G = json.load(io.open(os.path.join(DATA, "guru_history.json"), encoding="utf-8"))
    Q, H, NAMES = G["quarters"], G["holdings"], G["names"]
    base22 = set(H[Q[0]])          # F8 — 2013-06 에 이미 있던 매니저(날짜로 정한다)
    print("13F 패널 — 분기 %d개(%s ~ %s) · 매니저 %d명 · 2013-06 시점 %d명"
          % (len(Q), Q[0], Q[-1], G["n_managers"], len(base22)))

    M, SEC = px_frame()
    MR = M.pct_change()
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
        if int(f[5:7]) in (3, 6, 9, 12):
            fund_sel[f] = dict(zip(g.tkr, g.wtgt / 100.0))

    def agg(qi, keep=None):
        """분기 qi 의 {티커: 합산 보유금액}. keep 이 있으면 그 매니저만."""
        out = {}
        for cik, hh in H[Q[qi]].items():
            if keep is not None and cik not in keep:
                continue
            for t, v in hh.items():
                out[t] = out.get(t, 0.0) + float(v)
        return out

    def build(keep=None):
        """{형성월: 비중}, 진단행."""
        picks, diag, contrib = {}, [], {}
        for qi in range(1, len(Q)):
            fm = form_month(Q[qi])
            if fm not in M.index:
                continue
            ym = str(fm)
            cur, prv = agg(qi, keep), agg(qi - 1, keep)
            uni = set(months.get(ym, {}).get("spx") or [])
            if not uni:
                continue
            sc, newpos = {}, 0
            for t, v in cur.items():
                if t not in uni or t not in M.columns or pd.isna(M.at[fm, t]):
                    continue
                p = prv.get(t, 0.0)
                if p <= 0:
                    newpos += 1            # 🚨 신규 진입은 뺀다(등록서 §2-2)
                    continue
                sc[t] = v / p - 1.0
            diag.append({"m": ym, "q": Q[qi], "n_cand": len(sc), "n_new": newpos,
                         "n_mgr": len(H[Q[qi]] if keep is None
                                      else {k: 1 for k in H[Q[qi]] if k in keep})})
            if len(sc) < TOPN:
                continue
            top = sorted(sc.items(), key=lambda x: -x[1])[:TOPN]
            picks[ym] = {t: 1.0 / TOPN for t, _ in top}
            # 매니저별 기여 — 그 종목의 증가분을 누가 만들었나
            for t, _ in top:
                for cik, hh in H[Q[qi]].items():
                    if keep is not None and cik not in keep:
                        continue
                    dv = float(hh.get(t, 0.0)) - float(H[Q[qi - 1]].get(cik, {}).get(t, 0.0))
                    if dv > 0:
                        contrib[cik] = contrib.get(cik, 0.0) + dv
        return picks, pd.DataFrame(diag), contrib

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

    def ex(series):
        ms = [m for m in series.index if m in BM]
        return pd.Series([series[m] - BM[m] for m in ms],
                         index=pd.PeriodIndex(ms, freq="M"), dtype="float64")

    def ols(y, x):
        Xm = np.column_stack([np.ones(len(x)), x])
        bh, *_ = np.linalg.lstsq(Xm, y, rcond=None)
        e = y - Xm @ bh
        s2 = float(e @ e) / max(1, len(y) - 2)
        se = np.sqrt(np.diag(np.linalg.inv(Xm.T @ Xm) * s2))
        return float(bh[0]), float(bh[0] / se[0]) if se[0] > 0 else np.nan, float(bh[1])

    def stat(e, trn):
        n = len(e); te = float(e.std(ddof=1) * np.sqrt(12) * 100)
        return {"y_pp": float(e.mean() * 1200), "te": te,
                "t": float(e.mean() / (e.std(ddof=1) / np.sqrt(n))),
                "ir": float(e.mean() * 1200 / te) if te else np.nan,
                "win": float((e > 0).mean() * 100), "n": n,
                "turn": float(np.mean(list(trn.values())) * 4) if trn else np.nan}

    picks, DG, contrib = build()
    print("\n■ 형성 %d분기 (%s ~ %s)" % (len(DG), DG.m.iloc[0], DG.m.iloc[-1]))
    print("   후보 중앙 %d종 (최소 %d) · **신규 진입으로 뺀 것 중앙 %d건/분기** (최대 %d)"
          % (DG.n_cand.median(), DG.n_cand.min(), DG.n_new.median(), DG.n_new.max()))
    thin = int((DG.n_cand < 30).sum())
    print("   후보 30종 미만 분기 %d개 (%.1f%%) → F5 %s"
          % (thin, 100 * thin / len(DG), "걸림" if thin / len(DG) > 0.10 else "통과"))

    g_r, g_trn = run(picks)
    f_r, f_trn = run(fund_sel)

    # ── 혼합 — 🚨 «형성월에 두 명단을 합친다» 로 짜면 안 된다 ────────────────
    #   두 슬리브의 형성월이 어긋난다(펀드 3·6·9·12 / 거장 2·5·8·11). 등록서 §2-3 이
    #   그것을 **맞추지 않겠다**고 못박았다. 그래서 형성월 기준으로 합치면 어느 달이든
    #   한쪽만 있고, 굴리는 쪽이 비중을 다시 1로 정규화하면서
    #   **«3개월은 펀드 100%, 다음 3개월은 거장 100%»** 라는 엉뚱한 것이 된다.
    #   첫 실행에서 실제로 그렇게 나왔다 — 펀드 +7.89%p · 거장 +1.72%p 인데
    #   «혼합» 이 −0.45%p 였다. 90/10 혼합이 두 부분보다 낮을 수는 없다.
    #   산술적으로 불가능한 수가 나오면 그것은 결과가 아니라 버그다.
    #
    #   바른 뜻은 «두 슬리브를 **동시에** 들고 각자 제 주기로 리밸런스한다» 이다.
    #   ⚠ 그리고 이 자료에서는 그것이 수익률 가중합과 **정확히 같다** —
    #     실측으로 **펀드와 거장의 종목 겹침이 0종**이기 때문이다(F6).
    #     겹치는 종목이 있으면 비중이 더해져 달라지지만, 겹침이 0이면 동일하다.
    m_r = (1 - MIXW) * f_r.reindex(f_r.index.union(g_r.index)).fillna(0.0) \
        + MIXW * g_r.reindex(f_r.index.union(g_r.index)).fillna(0.0)
    m_r = m_r.reindex(f_r.index.intersection(g_r.index))
    m_trn = {k: (1 - MIXW) * f_trn.get(k, 0.0) + MIXW * g_trn.get(k, 0.0)
             for k in set(f_trn) | set(g_trn)}

    E_g, E_f, E_m = ex(g_r), ex(f_r), ex(m_r)
    j = E_g.index.intersection(E_f.index).intersection(E_m.index)
    E_g, E_f, E_m = E_g.reindex(j), E_f.reindex(j), E_m.reindex(j)
    S_g, S_f, S_m = stat(E_g, g_trn), stat(E_f, f_trn), stat(E_m, m_trn)
    # 두 슬리브를 함께 들면 회전도 비중대로 합쳐진다. 두 주기의 거래를 한 평균에
    # 섞으면 분모가 두 배가 되어 회전이 반토막으로 보인다 — 그래서 직접 계산한다.
    S_m["turn"] = (1 - MIXW) * S_f["turn"] + MIXW * S_g["turn"]

    print("\n■ 성적 (비용 후 · 잣대 B) · %d개월 (%s ~ %s)" % (len(j), j[0], j[-1]))
    print("   %-14s %10s %8s %7s %7s %7s %8s" % ("", "초과/년", "TE", "t", "IR", "승률", "연회전"))
    for nm, s in (("펀드", S_f), ("거장 분기판", S_g), ("혼합 90/10", S_m)):
        print("   %-14s %+9.2f%%p %7.2f%% %7.2f %7.2f %6.1f%% %7.2f회"
              % (nm, s["y_pp"], s["te"], s["t"], s["ir"], s["win"], s["turn"]))
    print("   혼합 − 펀드   초과 %+.2f%%p · TE %+.2f%%p · **IR %+.3f**"
          % (S_m["y_pp"] - S_f["y_pp"], S_m["te"] - S_f["te"], S_m["ir"] - S_f["ir"]))

    a, ta, beta = ols(E_g.to_numpy(), E_f.to_numpy())
    corr = float(np.corrcoef(E_g, E_f)[0, 1])
    print("\n■ 펀드 위의 증분 — 알파 연 %+.2f%%p · **t %.2f** · β %+.2f · 상관 %+.2f"
          % (a * 1200, ta, beta, corr))

    ov = []
    for fm in sorted(set(picks) & set(fund_sel)):
        A, B = fund_sel[fm], picks[fm]
        za, zb = sum(A.values()), sum(B.values())
        if za <= 0 or zb <= 0:
            continue
        ov.append({"m": fm, "n": len(set(A) & set(B)),
                   "w": 100 * sum(min(A[t] / za, B[t] / zb) for t in set(A) & set(B))})
    OV = pd.DataFrame(ov) if ov else pd.DataFrame([{"m": "-", "n": 0, "w": 0.0}])
    print("\n■ 펀드와의 겹침 — 종목 중앙 %.0f종(최대 %d) · 비중 중앙 %.1f%%(최대 %.1f%%) → F6 %s"
          % (OV.n.median(), OV.n.max(), OV.w.median(), OV.w.max(),
             "걸림" if OV.w.median() > 50 else "통과"))

    # ── F8 매니저 생존편향 ────────────────────────────────────────────────
    picks22, DG22, _ = build(keep=base22)
    g22_r, g22_trn = run(picks22)
    E22 = ex(g22_r).reindex(j).dropna()
    S22 = stat(E22, g22_trn)
    ratio = S22["y_pp"] / S_g["y_pp"] if S_g["y_pp"] else np.nan
    print("\n■ F8 매니저 생존편향 — 2013-06 에 있던 %d명만으로 다시" % len(base22))
    print("   전체 27명판 %+.2f%%p (t %.2f)  →  22명 고정판 %+.2f%%p (t %.2f)"
          % (S_g["y_pp"], S_g["t"], S22["y_pp"], S22["t"]))
    print("   **남은 비율 %.0f%%** → F8 %s (문턱 50%%)"
          % (100 * ratio, "걸림" if ratio < 0.5 else "통과"))

    print("\n■ 매니저별 기여 (고른 종목의 증가분 합 · 상위 8)")
    tt = sum(contrib.values()) or 1
    for cik, v in sorted(contrib.items(), key=lambda x: -x[1])[:8]:
        print("   %-28s %5.1f%%" % ((NAMES.get(cik) or cik)[:28], 100 * v / tt))

    h = len(j) // 2
    print("\n■ 표본 절반씩")
    halves = {}
    for nm, sl in (("앞 절반", slice(0, h)), ("뒤 절반", slice(h, None))):
        aa, tt2, _ = ols(E_g.iloc[sl].to_numpy(), E_f.iloc[sl].to_numpy())
        halves[nm] = aa
        print("   %s (%s~%s)  단독 %+6.2f%%p · 증분 %+6.2f%%p (t %5.2f)"
              % (nm, j[sl][0], j[sl][-1], E_g.iloc[sl].mean() * 1200, aa * 1200, tt2))

    rng = np.random.default_rng(SEED)
    shuf = []
    for _ in range(NSHUF):
        sel = {}
        for fm in picks:
            uni = [t for t in (months.get(fm, {}).get("spx") or [])
                   if t in M.columns and pd.notna(M.at[pd.Period(fm, freq="M"), t])]
            if len(uni) < TOPN:
                continue
            pk = rng.choice(len(uni), size=TOPN, replace=False)
            sel[fm] = {uni[i]: 1.0 / TOPN for i in pk}
        r, _t = run(sel)
        e = ex(r).reindex(j).dropna()
        if len(e) > 12:
            shuf.append(float(e.mean() * 1200))
    shuf = np.array(shuf)
    pct = float((shuf < S_g["y_pp"]).mean() * 100)
    print("\n■ F4 셔플 %d회 — 실측 %+.2f%%p · 셔플 평균 %+.2f%%p (sd %.2f) · **백분위 %.1f**"
          % (len(shuf), S_g["y_pp"], shuf.mean(), shuf.std(ddof=1), pct))

    try:
        ffd = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
        FD = pd.DataFrame(ffd["series"], index=pd.to_datetime(ffd["dates"])) / 100.0
        vol = FD.mkt_rf.groupby(FD.index.to_period("M")).std() * np.sqrt(252)
        v = vol.reindex(j).dropna(); q1, q2 = v.quantile(1 / 3), v.quantile(2 / 3)
        print("\n■ 시장변동성 3분위 (월 %)")
        print("   %-12s %9s %9s %9s" % ("", "저변동", "중간", "고변동"))
        for nm, e in (("펀드", E_f), ("거장", E_g), ("혼합", E_m)):
            cells = []
            for lo, hi in ((None, q1), (q1, q2), (q2, None)):
                s_ = v[(v > lo if lo is not None else v == v)
                       & (v <= hi if hi is not None else v == v)].index
                cells.append(float(e.reindex(s_).mean() * 100))
            print("   %-12s %+8.3f %+8.3f %+8.3f" % (nm, *cells))
    except Exception as e_:
        print("\n(국면 못 쟀다: %s)" % e_)

    last = sorted(picks)[-1]
    sec = {}
    for t in picks[last]:
        sec[SEC.get(t) or "?"] = sec.get(SEC.get(t) or "?", 0.0) + 10.0
    print("\n■ %s 형성 보유 — %s" % (last, " · ".join(sorted(picks[last]))))
    print("   섹터 — " + " · ".join("%s %.0f%%" % (k, v)
                                    for k, v in sorted(sec.items(), key=lambda x: -x[1])[:5]))

    f = {"F1": S_g["y_pp"] <= 0,
         "F2": (S_m["ir"] - S_f["ir"]) < 0.05,
         "F3": ta < 2,
         "F4": pct < 95,
         "F5": thin / len(DG) > 0.10,
         "F6": OV.w.median() > 50,
         "F7": halves["앞 절반"] * halves["뒤 절반"] <= 0,
         "F8": ratio < 0.5}
    txt = {"F1": "단독 초과 ≤ 0", "F2": "IR 개선 < 0.05", "F3": "증분 알파 t < 2",
           "F4": "셔플 백분위 < 95", "F5": "후보 30종 미만 분기 > 10%",
           "F6": "펀드와 겹침 > 50%", "F7": "뒤 절반 부호 반전",
           "F8": "22명 고정판이 절반 미만"}
    print("\n■ 기각 조건")
    for k in sorted(f):
        print("   %s %s %s" % ("❌ 걸림" if f[k] else "✅ 통과", k, txt[k]))
    verdict = "기각" if any(f.values()) else "등록 조건 전부 통과"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": "build/PREREG-2026-09-20-GURUACC.md",
        "commit_before": "96e65937241855bbb526c40f905914ff2e1587ed",
        "blob": "c928fcd79703b4b4f75b4581c3e95be512e66160",
        "const": {"LAG_D": LAG_D, "TOPN": TOPN, "COST": COST, "MIXW": MIXW,
                  "NSHUF": NSHUF, "SEED": SEED},
        "window": {"start": str(j[0]), "end": str(j[-1]), "n": len(j)},
        "stats": {"fund": S_f, "guru": S_g, "mix": S_m, "guru22": S22},
        "incr": {"alpha_y_pp": a * 1200, "t": ta, "beta": beta, "corr": corr},
        "overlap": {"n_med": float(OV.n.median()), "w_med": float(OV.w.median()),
                    "w_max": float(OV.w.max())},
        "shuffle": {"n": len(shuf), "mean": float(shuf.mean()),
                    "sd": float(shuf.std(ddof=1)), "pct": pct},
        "f8_ratio": float(ratio),
        "contrib": {(NAMES.get(c) or c): v / tt for c, v in contrib.items()},
        "diag": DG.to_dict("records"), "fails": f, "verdict": verdict,
        "series": {"guru": {str(k): float(v) for k, v in E_g.items()},
                   "fund": {str(k): float(v) for k, v in E_f.items()},
                   "mix": {str(k): float(v) for k, v in E_m.items()},
                   "guru22": {str(k): float(v) for k, v in E22.items()}},
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
