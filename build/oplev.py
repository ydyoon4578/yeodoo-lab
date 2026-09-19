# -*- coding: utf-8 -*-
"""build/oplev.py — 영업 레버리지 (PREREG-2026-09-19-OPLEV · 계산 전 647d2bc)

  주 판정 = OL-원식 (매출원가 + 판매관리비) / 자산총계 · 산업중립 · 금융제외 · 시총가중
  같은 표에 — OL-대체(rev−opinc) · OL-Chen(dep+sga) · 동일가중 · 보유 1·6·12 · 비중립 · 금융포함

🚨 항등식 검사가 성적보다 먼저다(카드 ⑥). OL ≡ ATO × (1−PM).

  python build/oplev.py
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_oplev.json")
N_SEL, MIN_POOL, NSHUF, SEED = 52, 30, 200, 20260919
HOLDS = (1, 6, 12)
FIN = {"Financials", "Real Estate"}


def yearly(tagdoc, key):
    """연간 계열 — 없으면 같은 회계연도 분기 4개가 다 있을 때만 합친다."""
    tg = (tagdoc.get("tags") or {}).get(key) or {}
    out = {}
    for end, v, *_ in (tg.get("a") or []):
        out[end[:4]] = float(v)
    if not out:
        q = {}
        for end, v, *_ in (tg.get("q") or []):
            q.setdefault(end[:4], []).append(float(v))
        for y, v in q.items():
            if len(v) == 4:
                out[y] = float(sum(v))
    return out


def snapshot(tagdoc, key):
    """시점 잔액(자산총계 등) — 회계연도 마지막 값."""
    tg = (tagdoc.get("tags") or {}).get(key) or {}
    out = {}
    for end, v, *_ in (tg.get("i") or tg.get("a") or tg.get("q") or []):
        out[end[:4]] = float(v)
    return out


def main():
    # ── 재료 ──────────────────────────────────────────────────────────────
    ext = {}
    for d in (os.path.join(DATA, "fxe"), os.path.join(DATA, "fxe_pit")):
        for p in glob.glob(os.path.join(d, "*.json")):
            j = json.load(io.open(p, encoding="utf-8"))
            ext[j["t"]] = j
    base = {}
    for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8"))
        base[j["t"]] = j

    rows = []
    for t, b in base.items():
        e = ext.get(t, {})
        rev, opinc = yearly(b, "rev"), yearly(b, "opinc")
        cogs, dep = yearly(b, "cogs"), yearly(b, "dep")
        sga = yearly(e, "sga")
        at = snapshot(b, "asset")
        for y in set(at) & set(rev):
            a = at[y]
            if not a or a <= 0:
                continue
            r = {"t": t, "fy": int(y), "asset": a, "rev": rev.get(y)}
            if cogs.get(y) is not None and sga.get(y) is not None:
                r["ol_orig"] = (cogs[y] + sga[y]) / a
            if rev.get(y) is not None and opinc.get(y) is not None:
                r["ol_sub"] = (rev[y] - opinc[y]) / a
                r["ato"] = rev[y] / a
                r["pm"] = opinc[y] / rev[y] if rev[y] else np.nan
            if dep.get(y) is not None and sga.get(y) is not None:
                r["ol_chen"] = (dep[y] + sga[y]) / a
            rows.append(r)
    F = pd.DataFrame(rows)
    print("회사-회계연도 %d행 · %d종" % (len(F), F.t.nunique()))
    for k in ("ol_orig", "ol_sub", "ol_chen"):
        n = F[k].notna().sum() if k in F else 0
        print("   %-9s %5d행 · %3d종 (커버 %.1f%%)"
              % (k, n, F.loc[F[k].notna(), "t"].nunique() if k in F else 0,
                 F.loc[F[k].notna(), "t"].nunique() / F.t.nunique() * 100 if k in F else 0))

    # ── 산업·섹터 ─────────────────────────────────────────────────────────
    mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    grp = {t: (v.get("grp") or "?") for t, v in mem.items() if isinstance(v, dict)}
    sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    hsec = hist.get("sector") or {}
    F["grp"] = F.t.map(lambda x: grp.get(x, "?"))
    F["sector"] = F.t.map(lambda x: sect.get(x) or hsec.get(x) or "?")

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
    M = P.resample("M").last()
    M.index = M.index.to_period("M")
    MR = M.pct_change()
    shrow = []
    for t, b in base.items():
        tg = (b.get("tags") or {})
        s = tg.get("sh") or tg.get("sho") or {}
        for end, v, *_ in (s.get("i") or s.get("q") or s.get("a") or []):
            shrow.append({"t": t, "m": end[:7], "sh": float(v)})
    SHW = pd.DataFrame(shrow).pivot_table(index="m", columns="t", values="sh", aggfunc="last")
    SHW.index = pd.PeriodIndex(SHW.index, freq="M")
    SHW = SHW.reindex(M.index).ffill()
    CAP = pd.DataFrame(M.reindex(columns=SHW.columns).to_numpy() * SHW.to_numpy(),
                       index=M.index, columns=SHW.columns).reindex(columns=M.columns)
    print("   가격 %d종 · 월 %d개 · 시총 %d종" % (P.shape[1], len(M), CAP.notna().any().sum()))

    # ── 연간판: 6월말 형성 ────────────────────────────────────────────────
    def panel(col, neutral, drop_fin):
        """{형성월: {종목: 점수}}"""
        out = {}
        D = F[F[col].notna()].copy() if col in F else F.iloc[0:0]
        if drop_fin:
            D = D[~D.sector.isin(FIN)]
        for fy, g in D.groupby("fy"):
            m = pd.Period("%d-06" % (fy + 1), freq="M")     # 직전 회계연도 → 다음해 6월말
            g = g[g.t.isin(M.columns)]
            if neutral:
                z = g.groupby("grp")[col].transform(
                    lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * 0)
            else:
                z = (g[col] - g[col].mean()) / (g[col].std(ddof=0) or 1)
            out[m] = dict(zip(g.t, z))
        return out

    def legs(pan, weight, hold, shuf=None, rng=None):
        ls, lo, ns = [], [], []
        ms = sorted(pan)
        for m in ms:
            d = {t: v for t, v in pan[m].items() if m in M.index and pd.notna(M.at[m, t])}
            ns.append(len(d))
            if len(d) < MIN_POOL:
                continue
            ts = list(d)
            v = np.array([d[t] for t in ts], float)
            if shuf:
                v = rng.permutation(v)
            o = np.argsort(v)
            hi = [ts[i] for i in o[-N_SEL:]]
            lowt = [ts[i] for i in o[:N_SEL]]
            fut = [x for x in M.index if x > m][:hold]
            if len(fut) < hold:
                break

            def ret(names):
                if weight == "cap":
                    w = CAP.loc[m, names].astype(float)
                    w = w / w.sum() if np.isfinite(w).all() and w.sum() > 0 else \
                        pd.Series(1.0 / len(names), index=names)
                else:
                    w = pd.Series(1.0 / len(names), index=names)
                return float(sum((w * MR.loc[x, names].astype(float).fillna(0)).sum()
                                 for x in fut)) / hold
            ls.append(ret(hi) - ret(lowt))
            lo.append(ret(hi))
        return np.array(ls), np.array(lo), np.array(ns)

    def tt(x):
        x = x[np.isfinite(x)]
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 3 else float("nan")

    # ── 카드 ⑥ 항등식 검사 — 성적보다 먼저 ────────────────────────────────
    print("\n■ 카드 ⑥ 항등식 검사 (성적보다 먼저)")
    chk = F.dropna(subset=["ol_sub", "ato", "pm"])
    err = (chk.ato * (1 - chk.pm) - chk.ol_sub).abs().max()
    print("   OL-대체 ≡ ATO × (1−PM) — 최대 오차 %.2e  → 항등식이다" % err)
    if "ol_orig" in F:
        c2 = F.dropna(subset=["ol_orig", "ol_sub"])
        print("   OL-원식 vs OL-대체 상관 %.3f (n %d)"
              % (c2.ol_orig.corr(c2.ol_sub), len(c2)))

    # Fama-MacBeth: OL 계수가 ATO·PM 통제 뒤 남는가
    def fm(col):
        co = []
        D = F[F[col].notna()].dropna(subset=["ato", "pm"])
        for fy, g in D.groupby("fy"):
            m = pd.Period("%d-06" % (fy + 1), freq="M")
            nx = [x for x in M.index if x > m][:12]
            if len(nx) < 12 or m not in M.index:
                continue
            g = g[g.t.isin(M.columns)]
            y = np.array([float(MR.loc[nx, t].astype(float).fillna(0).sum()) for t in g.t])
            cap = CAP.loc[m, g.t].astype(float).to_numpy()
            mom = (M.loc[m, g.t].astype(float).to_numpy() /
                   M.loc[m - 12, g.t].astype(float).to_numpy() - 1) if (m - 12) in M.index else np.zeros(len(g))
            X = np.column_stack([np.ones(len(g)), g[col].to_numpy(), g.ato.to_numpy(),
                                 g.pm.to_numpy(), np.log(np.where(cap > 0, cap, np.nan)),
                                 np.nan_to_num(mom)])
            ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
            if ok.sum() < 50:
                continue
            b, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
            co.append(b[1])
        co = np.array(co)
        return (float(co.mean()), tt(co), len(co)) if len(co) > 3 else (np.nan, np.nan, len(co))

    print("   Fama-MacBeth (r ~ OL + ATO + PM + log시총 + 모멘텀 · 연 1회 · 12개월 수익)")
    fmres = {}
    for col in ("ol_orig", "ol_sub", "ol_chen"):
        if col in F and F[col].notna().any():
            b, t, n = fm(col)
            fmres[col] = {"b": b, "t": t, "n": n}
            print("      %-9s b1 %+9.4f · t %5.2f · 연 %d" % (col, b, t, n))

    # ── 성적 ──────────────────────────────────────────────────────────────
    print("\n■ 성적 — 롱숏 십분위(%d종) · 월 %% · 연간판(6월말)" % N_SEL)
    res = {}
    for col in ("ol_orig", "ol_sub", "ol_chen"):
        if col not in F or not F[col].notna().any():
            continue
        res[col] = {}
        for neutral in (True, False):
            for drop_fin in (True, False):
                pan = panel(col, neutral, drop_fin)
                key = "%s|%s" % ("산업중립" if neutral else "비중립",
                                 "금융제외" if drop_fin else "금융포함")
                res[col][key] = {}
                for weight in ("cap", "ew"):
                    cells = []
                    for h in HOLDS:
                        a, b, ns = legs(pan, weight, h)
                        cells.append({"mean_pct": float(a.mean()) * 100 if len(a) else np.nan,
                                      "t": tt(a) if len(a) else np.nan, "n": int(len(a)),
                                      "pool_med": int(np.median(ns)) if len(ns) else 0})
                    res[col][key][weight] = cells
        main = res[col]["산업중립|금융제외"]["cap"]
        alt = res[col]["비중립|금융제외"]["cap"]
        ew = res[col]["산업중립|금융제외"]["ew"]
        print("   [%s]  후보 중앙 %d종" % (col, main[0]["pool_med"]))
        print("      산업중립·금융제외·시총가중 %s"
              % "  ".join("%d개월 %+6.3f(t%5.2f)" % (h, c["mean_pct"], c["t"])
                          for h, c in zip(HOLDS, main)))
        print("      같은 조건 동일가중            %s"
              % "  ".join("%d개월 %+6.3f(t%5.2f)" % (h, c["mean_pct"], c["t"])
                          for h, c in zip(HOLDS, ew)))
        print("      비중립(금융제외·시총가중)      %s"
              % "  ".join("%d개월 %+6.3f(t%5.2f)" % (h, c["mean_pct"], c["t"])
                          for h, c in zip(HOLDS, alt)))
    print("   ⚠ 원 증거 시총가중 월 0.44(t 2.69) · 동일가중 0.51(t 3.38) / 복제 0.46(t 2.70)")

    # ── F6 ────────────────────────────────────────────────────────────────
    have = set(F.loc[F.ol_orig.notna(), "t"]) if "ol_orig" in F else set()
    cols = [c for c in M.columns if c in base]
    hv = [c for c in cols if c in have]
    nv = [c for c in cols if c not in have]
    f6 = 0.0
    if len(nv) > 3 and hv:
        a = MR[hv].mean(axis=1).mean() * 1200
        b2 = MR[nv].mean(axis=1).mean() * 1200
        f6 = a - b2
        print("\n   F6 — OL-원식 되는 %d종 연 %+.2f%% vs 안 되는 %d종 %+.2f%% · 차 %+.2f%%p"
              % (len(hv), a, len(nv), b2, f6))

    # ── F2 셔플 ───────────────────────────────────────────────────────────
    print("\n■ F2 셔플 %d회 (주 판정판 · 보유 1개월)" % NSHUF)
    rng = np.random.default_rng(SEED)
    pan = panel("ol_orig", True, True)
    act = res["ol_orig"]["산업중립|금융제외"]["cap"][0]["mean_pct"]
    sh = np.array([legs(pan, "cap", 1, shuf=True, rng=rng)[0].mean() * 100 for _ in range(NSHUF)])
    pct = float((sh < act).mean()) * 100
    print("   실측 %+.3f%% · 셔플 평균 %+.3f%% (sd %.3f) · 백분위 %.1f"
          % (act, sh.mean(), sh.std(ddof=1), pct))

    mm = res["ol_orig"]["산업중립|금융제외"]["cap"]
    nn = res["ol_orig"]["비중립|금융제외"]["cap"]
    F_ = {"F1 세 기간 모두 양수 아님": not all(c["mean_pct"] > 0 for c in mm),
          "F2 셔플 상위 5% 밖": pct < 95.0,
          "F3 항등식 통제 후 |t| < 2": abs(fmres.get("ol_orig", {}).get("t", 0) or 0) < 2,
          "F5 산업중립 전후 부호 갈림": (mm[0]["mean_pct"] > 0) != (nn[0]["mean_pct"] > 0),
          "F6 태그 유무 수익차 |Δ| > 3%p": abs(f6) > 3.0}
    print("\n■ 기각 조건 (F4 는 회전율이 낮아 생략 — 연 1회)")
    for k, v in F_.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k))
    verdict = "기각" if any(F_.values()) else "채택"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"prereg": "PREREG-2026-09-19-OPLEV", "commit": "647d2bc",
         "identity_err": float(err), "fama_macbeth": fmres, "perf": res, "f6_gap": f6,
         "shuffle": {"n": NSHUF, "seed": SEED, "mean": float(sh.mean()),
                     "sd": float(sh.std(ddof=1)), "pctile": pct},
         "fails": {k: bool(v) for k, v in F_.items()}, "verdict": verdict},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
