# -*- coding: utf-8 -*-
"""build/orgcap.py — 조직자본 (PREREG-2026-09-19-ORGCAP · 계산 전 커밋 46bcf2a)

  OC_t = (1-δ)·OC_{t-1} + SG&A_t/디플레이터 · δ=0.15 · OC_0 = SG&A_1/(g+δ) · g=0.10
  신호 = OC/자산총계 를 산업 내 표준화 → 상위 십분위 52종 동일가중 롱온리 · 6월말 연 1회

🚨 F3(셔플)이 본체다 — 같은 산업 안에서만 점수를 섞는다.

  python build/orgcap.py
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_orgcap.json")
DELTA, GROW, COST, NSHUF, SEED = 0.15, 0.10, 0.0005, 200, 20260919
N_MAIN, N_ALT = 52, 104


def load_sga_assets():
    """fxe(현재) + fxe_pit(편출) 에서 연간 판관비·자산총계를 뽑는다."""
    rows = []
    for d, tag in ((os.path.join(DATA, "fxe"), "cur"), (os.path.join(DATA, "fxe_pit"), "gone")):
        for p in glob.glob(os.path.join(d, "*.json")):
            j = json.load(io.open(p, encoding="utf-8"))
            tg = j.get("tags") or {}
            sga = tg.get("sga")
            if not sga:
                continue
            ser = sga.get("a") or []                  # 연간 구간
            if ser:
                for end, val, *_ in ser:
                    rows.append({"t": j["t"], "src": tag, "end": end,
                                 "sga": float(val), "how": "a"})
            else:
                # 연간을 안 내고 분기만 내는 회사가 있다(실측: 514종 중 106종).
                # 같은 회계연도의 분기 4개가 다 있을 때만 합친다 — 3개만 더하면 조용히 작아진다.
                q = {}
                for end, val, *_ in (sga.get("q") or []):
                    q.setdefault(end[:4], []).append((end, float(val)))
                for y, v in q.items():
                    if len(v) == 4:
                        rows.append({"t": j["t"], "src": tag, "end": max(x[0] for x in v),
                                     "sga": sum(x[1] for x in v), "how": "q4"})
    S = pd.DataFrame(rows)
    # 자산총계는 기존 22태그 쪽(data/fx)에 있다 — 읽기만 한다
    arow = []
    for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8"))
        a = (j.get("tags") or {}).get("asset")
        if not a:
            continue
        for end, val, *_ in (a.get("i") or a.get("a") or []):
            arow.append({"t": j["t"], "end": end, "asset": float(val)})
    A = pd.DataFrame(arow)
    return S, A


def main():
    S, A = load_sga_assets()
    print("판관비(연간) %d행 · %d종 (현재 %d · 편출 %d)"
          % (len(S), S.t.nunique(), S[S.src == "cur"].t.nunique(), S[S.src == "gone"].t.nunique()))
    print("자산총계 %d행 · %d종" % (len(A), A.t.nunique()))
    if S.empty or A.empty:
        print("❌ 자료가 비었다"); return 1
    S["fy"] = S.end.str[:4].astype(int)
    A["fy"] = A.end.str[:4].astype(int)
    S = S.sort_values(["t", "end"]).groupby(["t", "fy"], as_index=False).agg(sga=("sga","last"), src=("src","last"), how=("how","last"))
    A = A.sort_values(["t", "end"]).groupby(["t", "fy"], as_index=False).asset.last()
    print("   회계연도 정리 후 — 판관비 %d행 · 자산 %d행 · 연도 %d~%d"
          % (len(S), len(A), S.fy.min(), S.fy.max()))

    # ── 디플레이터 (CPIAUCSL · 연평균) ─────────────────────────────────────
    a = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    cpi = (a.get("macro") or {}).get("CPIAUCSL") or {}
    # ⚠ macro 계열은 {날짜: 값} 사전이다(일별 격자가 아니다). 처음에 dates 로 붙였다가
    #   길이가 안 맞아 인덱스에 NaT 가 생겼다 — 연도 집계에서 KeyError(nan) 으로 터진다.
    cser = pd.Series({pd.Timestamp(k): float(v) for k, v in cpi.items()
                      if v is not None}).sort_index()
    defl = cser.groupby(cser.index.year).mean()
    defl = defl / defl.loc[defl.index.max()]
    print("   디플레이터(CPIAUCSL 연평균) %d~%d" % (defl.index.min(), defl.index.max()))

    # ── 조직자본 영구재고 ─────────────────────────────────────────────────
    S["real"] = S.sga / S.fy.map(defl).astype(float)
    oc = []
    for t, g in S.dropna(subset=["real"]).sort_values("fy").groupby("t"):
        prev = None
        for _, r in g.iterrows():
            prev = r.real / (GROW + DELTA) if prev is None else (1 - DELTA) * prev + r.real
            oc.append({"t": t, "fy": int(r.fy), "oc": prev})
    OC = pd.DataFrame(oc).merge(A, on=["t", "fy"], how="inner")
    OC["ocat"] = OC.oc / OC.asset
    OC = OC[np.isfinite(OC.ocat) & (OC.asset > 0)]
    print("   OC/자산 %d행 · %d종 · 중앙 %.3f" % (len(OC), OC.t.nunique(), OC.ocat.median()))

    # ── 산업 (GICS 산업그룹) ──────────────────────────────────────────────
    mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    grp = {t: (v.get("grp") or "?") for t, v in mem.items() if isinstance(v, dict)}
    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    sec = hist.get("sector") or {}
    OC["grp"] = OC.t.map(lambda x: grp.get(x) or sec.get(x) or "?")
    print("   산업그룹 %d종 · 미분류 %d행" % (OC.grp.nunique(), int((OC.grp == "?").sum())))

    # 산업 내 표준화
    def z(g):
        s = g.ocat.std(ddof=0)
        return (g.ocat - g.ocat.mean()) / s if s and s > 0 else g.ocat * 0
    OC["score"] = OC.groupby(["fy", "grp"], group_keys=False).apply(z)
    OC_BASE = OC

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
    pdates, ppx = pit["dates"], pit["px"]
    off = {d: i for i, d in enumerate(pdates)}
    # ⚠ pit_px 의 값은 리스트가 아니라 {"i0": 시작 오프셋, "p": [...]} 다.
    #   편출 종목은 격자 중간에 상장돼 앞쪽이 비므로 그 시작점을 따로 담는다.
    n_gone = 0
    for t, v in ppx.items():
        if t in px or not isinstance(v, dict):
            continue
        arr = [np.nan] * len(dates)
        i0, p = int(v.get("i0") or 0), (v.get("p") or [])
        for k, val in enumerate(p):
            j2 = i0 + k
            if 0 <= j2 < len(dates) and val is not None:
                arr[j2] = float(val)
        px[t] = arr
        n_gone += 1
    P = pd.DataFrame(px, index=pd.to_datetime(dates))
    print("   가격 %d종 (오늘 패널 %d + 편출 %d)" % (P.shape[1], P.shape[1] - n_gone, n_gone))

    # ── 멤버십 ────────────────────────────────────────────────────────────
    months = hist["months"]
    def members(ym):
        v = months.get(ym) or {}
        return set(v.get("spx") or [])

    # ── 6월말 형성 ────────────────────────────────────────────────────────
    ym = pd.Series([d[:7] for d in dates], index=P.index)
    june = [i for i in range(len(dates) - 1)
            if dates[i][5:7] == "06" and dates[i][:7] != dates[i + 1][:7]]
    R = P.pct_change()

    def run(pick_fn, n_sel, pit_mode, TBL=None):
        # 🚨 점수표를 인자로 받는다. 처음에 globals()["OC"] 를 바꿔치기했는데 run 이
        #   main 의 **지역** OC 를 닫아 잡고 있어 셔플이 통째로 안 먹었다 —
        #   200회가 전부 같은 값이 나와(표준편차 0.00) 그 사실이 드러났다.
        OC = TBL if TBL is not None else OC_BASE
        w, rets, traded, hold = None, [], [], set()
        picks = {}
        for i in range(june[0] + 1, len(dates)):
            if i - 2 in june:
                d = dates[i - 2]
                fy = int(d[:4]) - 1                      # 직전 회계연도 확정분
                pool = OC[OC.fy == fy]
                if pit_mode:
                    mm = members(d[:7])
                    pool = pool[pool.t.isin(mm)] if mm else pool.iloc[0:0]
                pool = pool[pool.t.isin(P.columns)]
                pool = pool[P[pool.t].iloc[i - 2].notna().values] if len(pool) else pool
                if len(pool) >= n_sel:
                    sel = pick_fn(pool, n_sel, d)
                    picks[d] = sel
                    nw = pd.Series(0.0, index=P.columns)
                    nw[sel] = 1.0 / len(sel)
                    traded.append(float(np.abs(nw - (w if w is not None else 0)).sum()))
                    w, hold = nw, set(sel)
                else:
                    traded.append(0.0)
            else:
                traded.append(0.0)
            r = R.iloc[i].fillna(0.0)
            rets.append(float(w @ r) if w is not None else 0.0)
        return np.array(rets), np.array(traded), picks

    def top(pool, n, d):
        return list(pool.sort_values("score", ascending=False).t.head(n))

    # 대조군 — 같은 유니버스 시총가중은 못 만든다(시총 계열이 없다) → 지수(^GSPC)로
    b = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    SPX = pd.Series(b["series"]["spx"]["px"], index=pd.to_datetime(b["dates"]),
                    dtype="float64").reindex(P.index).pct_change()

    def ann(r, tr=None, bps=0.0):
        x = np.asarray(r, float)
        if tr is not None and bps:
            x = x - (bps / 10000.0) * np.asarray(tr, float) * 10000 / 10000
        nav = np.cumprod(1 + x)
        yrs = len(x) / 252
        c = (float(nav[-1]) ** (1 / yrs) - 1) * 100
        v = float(x.std(ddof=1)) * np.sqrt(252) * 100
        return {"cagr": c, "vol": v, "sharpe": c / v if v else None}

    res = {}
    for tag, pit_mode in (("소급(오늘 518)", False), ("시점정확(partial)", True)):
        r, tr, picks = run(top, N_MAIN, pit_mode)
        bench = SPX.iloc[june[0] + 1:].fillna(0.0).to_numpy()
        m, mb = ann(r), ann(bench)
        net = ann(r - COST * tr)
        yrs = len(r) / 252
        res[tag] = {"cagr": m["cagr"], "sharpe": m["sharpe"], "bench_cagr": mb["cagr"],
                    "bench_sharpe": mb["sharpe"], "excess": m["cagr"] - mb["cagr"],
                    "net_excess": net["cagr"] - mb["cagr"],
                    "turnover": float(tr.sum()) / 2 / yrs * 100, "n_rebal": len(picks)}
        print("\n■ %s" % tag)
        print("   연 %+.2f%% · 샤프 %s · 지수 %+.2f%% · 초과 %+.2f%%p · 5bp후 %+.2f%%p"
              % (m["cagr"], round(m["sharpe"], 3), mb["cagr"], m["cagr"] - mb["cagr"],
                 net["cagr"] - mb["cagr"]))
        print("   재구성 %d회 · 연 편도 회전율 %.0f%%" % (len(picks), res[tag]["turnover"]))
        if pit_mode:
            main_r, main_tr, main_picks = r, tr, picks

    infl = res["소급(오늘 518)"]["sharpe"] - res["시점정확(partial)"]["sharpe"]
    print("\n   부풀림(소급 샤프 − PIT 샤프) %.3f  (랩 문턱 0.36 · 중앙값 0.179)" % infl)

    # ── F5 판관비 유무 집단 ───────────────────────────────────────────────
    have = set(OC.t.unique())
    allc = [t for t in P.columns if t in set(st and [s["t"] for s in st["stocks"]])]
    hv = [t for t in allc if t in have]
    nv = [t for t in allc if t not in have]
    rh = R[hv].mean(axis=1).iloc[june[0] + 1:].fillna(0)
    rn = R[nv].mean(axis=1).iloc[june[0] + 1:].fillna(0) if nv else None
    d5 = (ann(rh)["cagr"] - ann(rn)["cagr"]) if rn is not None and len(nv) > 3 else 0.0
    print("   F5 — 판관비 있는 %d종 연 %+.2f%% vs 없는 %d종 연 %+.2f%% · 차 %+.2f%%p"
          % (len(hv), ann(rh)["cagr"], len(nv), ann(rn)["cagr"] if rn is not None else float("nan"), d5))

    # ── F2 셔플 — 같은 산업 안에서만 ──────────────────────────────────────
    print("\n■ F2 셔플 %d회 — 산업 안에서만 점수를 섞는다" % NSHUF)
    rng = np.random.default_rng(SEED)
    OCs = OC.copy()
    sh = np.empty(NSHUF)
    for q in range(NSHUF):
        OCs = OC.copy()
        OCs["score"] = OC.groupby(["fy", "grp"], group_keys=False).score.transform(
            lambda s: rng.permutation(s.to_numpy()))
        rr, _t, _p = run(top, N_MAIN, True, TBL=OCs)
        bench = SPX.iloc[june[0] + 1:].fillna(0.0).to_numpy()
        sh[q] = ann(rr)["cagr"] - ann(bench)["cagr"]
        if (q + 1) % 50 == 0:
            print("   ... %d회" % (q + 1))
    act = res["시점정확(partial)"]["excess"]
    pct = float((sh < act).mean()) * 100
    print("   실측 초과 %+.2f%%p · 셔플 평균 %+.2f%%p (표준편차 %.2f) · 백분위 %.1f"
          % (act, sh.mean(), sh.std(ddof=1), pct))

    F = {"F1 PIT 초과 ≤ 0": act <= 0,
         "F2 셔플 상위 5% 밖": pct < 95.0,
         "F3 5bp 후 초과 ≤ 0": res["시점정확(partial)"]["net_excess"] <= 0,
         "F4 부풀림 > 0.36": infl > 0.36,
         "F5 판관비 유무 수익차 |Δ| > 3%p": abs(d5) > 3.0}
    print("\n■ 기각 조건")
    for k, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k))
    verdict = "기각" if any(F.values()) else "채택"
    print("\n→ 판정: %s" % verdict)
    print("   (등록서 §5 예측: F2 에서 걸릴 것 — %s)"
          % ("맞음" if F["F2 셔플 상위 5% 밖"] else "틀림"))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"prereg": "PREREG-2026-09-19-ORGCAP", "commit": "46bcf2a",
         "params": {"delta": DELTA, "g": GROW, "n": N_MAIN, "cost_bps": 5},
         "legs": res, "inflation": infl, "f5_gap": d5,
         "shuffle": {"n": NSHUF, "seed": SEED, "mean": float(sh.mean()),
                     "sd": float(sh.std(ddof=1)), "pctile": pct},
         "fails": {k: bool(v) for k, v in F.items()}, "verdict": verdict},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
