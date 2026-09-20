# -*- coding: utf-8 -*-
"""build/revcomp.py — 반전 네 축을 하나로. 규약은 PREREG-2026-09-20-REVCOMP.md.

🚨 등록서에 적은 것만 한다. 결과를 보고 축 개수(4)·크기(10)·밴드 폭(10/20)·주기(월말)를
   바꾸지 않고, 가중치를 최적화하지 않는다(F3 이 그것을 재는 자리다).
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
OUT = os.path.join(DATA, "_revcomp.json")

# ── 등록서 §1 의 상수 ──────────────────────────────────────────────────────
W_W, W_M, W_S, W_E = 5, 21, 14, 252   # 주간 · 월간 · RSI · ECM 회귀창
SMA = 200                             # 추세정렬 관문
TOPN, BAND = 10, 20
COST = 0.0025
TURN_CAP = 12.0                       # F7
NSHUF, SEED = 200, 20260920
AXES = ("W", "M", "S", "E")


def rsi(x, n=14):
    """Wilder RSI. x 는 종가 배열."""
    d = np.diff(x)
    if len(d) < n:
        return np.nan
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    au, ad = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(d)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
    if ad == 0:
        return 100.0
    return 100.0 - 100.0 / (1 + au / ad)


def z(d):
    """{티커: 값} → 횡단면 z. 표준편차가 0 이면 빈 dict."""
    if len(d) < 5:
        return {}
    v = np.array(list(d.values()), dtype="float64")
    m, s = float(v.mean()), float(v.std(ddof=1))
    if not (s > 0):
        return {}
    return {k: (x - m) / s for k, x in d.items()}


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
    M = P.resample("M").last(); M.index = M.index.to_period("M")
    MR = M.pct_change()
    LP = np.log(P)

    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    months = hist["months"]
    b = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    SPX = pd.Series(b["series"]["spx"]["px"], index=pd.to_datetime(b["dates"]),
                    dtype="float64").reindex(P.index).ffill()
    LSPX = np.log(SPX)

    idx = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_index.pkl"))
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    Xd = pd.read_csv(os.path.join(D18,
        r"01_이관묶음\01_우량성장선별_산출물\idx_div_monthly_20260918.csv"))
    idiv = dict(zip(Xd.iloc[:, 0].astype(str), Xd.iloc[:, 4]))
    BM = {m: ipr[m] + idiv[m] for m in ipr if m in idiv and pd.notna(ipr[m])}

    dpos = pd.Series(range(len(P.index)), index=P.index)
    forms = [m for m in sorted(months) if pd.Period(m, freq="M") in MR.index]

    def scores(fm):
        """형성월 fm 의 축별 원점수 {축: {티커: 값}} — 전부 «낮을수록 산다»."""
        p = pd.Period(fm, freq="M")
        end = P.index[P.index <= p.end_time]
        if len(end) < W_E + 2:
            return {}
        i1 = int(dpos[end[-1]])
        if i1 < W_E + 1:
            return {}
        uni = [t for t in (months[fm].get("spx") or []) if t in P.columns]
        out = {a: {} for a in AXES}
        sp = LSPX.iloc[i1 - W_E + 1:i1 + 1].to_numpy()
        sp_ok = np.isfinite(sp).all()
        for t in uni:
            col = P[t].to_numpy()
            seg = col[i1 - W_E + 1:i1 + 1]
            if np.isnan(seg).sum() > W_E * 0.2 or not np.isfinite(col[i1]):
                continue
            # W · M — 단순 수익(낮을수록 산다)
            for a, w in (("W", W_W), ("M", W_M)):
                p0, p1 = col[i1 - w], col[i1]
                if np.isfinite(p0) and p0 > 0 and np.isfinite(p1):
                    out[a][t] = p1 / p0 - 1.0
            # S — RSI(14). ⚠ 200일선 위인 종목만 후보
            s200 = col[i1 - SMA + 1:i1 + 1]
            s200 = s200[np.isfinite(s200)]
            if len(s200) >= SMA * 0.8 and col[i1] > s200.mean():
                xs = col[i1 - 60:i1 + 1]
                xs = xs[np.isfinite(xs)]
                if len(xs) > W_S + 1:
                    r = rsi(xs, W_S)
                    if np.isfinite(r):
                        out["S"][t] = r
            # E — 지수 대비 오차수정 잔차(낮을수록 저평가)
            if sp_ok:
                y = LP[t].to_numpy()[i1 - W_E + 1:i1 + 1]
                ok = np.isfinite(y)
                if ok.sum() >= W_E * 0.8:
                    A = np.column_stack([np.ones(ok.sum()), sp[ok]])
                    bh, *_ = np.linalg.lstsq(A, y[ok], rcond=None)
                    out["E"][t] = float(y[ok][-1] - (bh[0] + bh[1] * sp[ok][-1]))
        return out

    picks, parts, diag, held = {}, {a: {} for a in AXES}, [], set()
    for fm in forms:
        sc = scores(fm)
        if not sc:
            continue
        Z = {a: z(sc[a]) for a in AXES}
        common = set.intersection(*[set(Z[a]) for a in AXES]) if all(Z[a] for a in AXES) else set()
        row = {"m": fm, "n": len(common)}
        for a in AXES:
            row["n_" + a] = len(Z[a])
            if len(Z[a]) >= TOPN:                      # 부분도 같은 창·같은 비용으로 굴린다
                top = sorted(Z[a].items(), key=lambda x: x[1])[:TOPN]
                parts[a][fm] = {t: 1.0 / TOPN for t, _ in top}
        if len(common) < TOPN:
            diag.append(row); continue
        comp = {t: float(np.mean([Z[a][t] for a in AXES])) for t in common}
        order = sorted(comp.items(), key=lambda x: x[1])
        rank = {t: i for i, (t, _) in enumerate(order)}
        top = [t for t, _ in order[:TOPN]]
        keep = [t for t in held if rank.get(t, 10 ** 9) < BAND]
        new = [t for t in top if t not in keep]
        sel = (keep + new)[:TOPN]
        if len(sel) < TOPN:
            sel += [t for t in top if t not in sel][:TOPN - len(sel)]
        held = set(sel)
        picks[fm] = {t: 1.0 / len(sel) for t in sel}
        row["blocked"] = len([t for t in top if t not in sel])
        diag.append(row)
    DG = pd.DataFrame(diag)
    print("■ 형성 %d개월 (%s ~ %s)" % (len(DG), DG.m.iloc[0], DG.m.iloc[-1]))
    print("   축별 후보 중앙 — " + " · ".join("%s %d" % (a, int(DG["n_" + a].median()))
                                            for a in AXES))
    print("   **네 축을 다 가진 종목 중앙 %d종** (최소 %d)" % (DG.n.median(), DG.n.min()))
    thin = int((DG.n < 30).sum())
    print("   30종 미만인 달 %d개 (%.1f%%) → F5 %s"
          % (thin, 100 * thin / len(DG), "걸림" if thin / len(DG) > 0.10 else "통과"))
    if "blocked" in DG:
        print("   밴드가 막은 신규 진입 중앙 %.0f종/월" % DG["blocked"].median())

    def run(sel, hold=1):
        out, trn, prev = {}, {}, {}
        for fm in sorted(sel):
            w = dict(sel[fm])
            if not w:
                continue
            zz = sum(w.values()); w = {t: v / zz for t, v in w.items()}
            trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
            trn[fm] = trade
            first = True
            for k in range(1, hold + 1):
                q = int(fm[:4]) * 12 + int(fm[5:7]) - 1 + k
                hm = "%04d-%02d" % (q // 12, q % 12 + 1)
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
                z2 = sum(w.values()); w = {t: v / z2 for t, v in w.items()}
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
                "turn": float(np.mean(list(trn.values())) * 12) if trn else np.nan}

    c_r, c_trn = run(picks)
    E_c = ex(c_r)
    P_e, P_s = {}, {}
    for a in AXES:
        r, tr = run(parts[a])
        P_e[a] = ex(r)
        P_s[a] = stat(P_e[a].reindex(E_c.index).dropna(), tr)
    S_c = stat(E_c, c_trn)

    NAME = {"W": "주간반전(5일)", "M": "월간반전(21일)",
            "S": "추세정렬 과매도(RSI)", "E": "지수 대비 괴리(ECM)"}
    print("\n■ 성적 (PIT · 비용 후 · 잣대 B) · %d개월 (%s ~ %s)"
          % (len(E_c), E_c.index[0], E_c.index[-1]))
    print("   %-22s %10s %8s %7s %7s %8s" % ("", "초과/년", "TE", "t", "IR", "연회전"))
    for a in AXES:
        s = P_s[a]
        print("   %-22s %+9.2f%%p %7.2f%% %7.2f %7.2f %7.2f회"
              % (NAME[a], s["y_pp"], s["te"], s["t"], s["ir"], s["turn"]))
    print("   %-22s %+9.2f%%p %7.2f%% %7.2f %7.2f %7.2f회"
          % ("**컴포지트**", S_c["y_pp"], S_c["te"], S_c["t"], S_c["ir"], S_c["turn"]))
    best = max(P_s.values(), key=lambda s: s["y_pp"])
    bname = [NAME[a] for a in AXES if P_s[a] is best][0]
    print("   부분 최고: %s %+.2f%%p → 컴포지트가 %s"
          % (bname, best["y_pp"], "넘었다" if S_c["y_pp"] > best["y_pp"] else "**못 넘었다**"))
    print("   **F7 회전 %.2f회 (상한 %.0f) → %s**"
          % (S_c["turn"], TURN_CAP, "걸림" if S_c["turn"] > TURN_CAP else "통과"))

    # F6 — 부분과의 상관
    print("\n■ F6 컴포지트와 부분의 상관")
    cmax, carg = -9, ""
    for a in AXES:
        j = E_c.index.intersection(P_e[a].index)
        c = float(np.corrcoef(E_c.reindex(j), P_e[a].reindex(j))[0, 1])
        print("   %-22s %+.2f" % (NAME[a], c))
        if c > cmax:
            cmax, carg = c, NAME[a]
    print("   최대 %+.2f (%s) → %s" % (cmax, carg, "걸림" if cmax > 0.90 else "통과"))

    # F3 — 무작위 가중
    rng = np.random.default_rng(SEED)
    Pm = pd.DataFrame({a: P_e[a] for a in AXES}).dropna()
    j = Pm.index.intersection(E_c.index)
    rw = []
    for _ in range(NSHUF):
        w = rng.dirichlet(np.ones(len(AXES)))
        rw.append(float((Pm.reindex(j).to_numpy() @ w).mean() * 1200))
    rw = np.array(rw)
    pct_w = float((rw < S_c["y_pp"]).mean() * 100)
    print("\n■ F3 무작위 가중 %d회 (부분 수익을 섞는다)" % NSHUF)
    print("   실측 %+.2f%%p · 무작위 평균 %+.2f%%p (sd %.2f) · **백분위 %.1f** → %s"
          % (S_c["y_pp"], rw.mean(), rw.std(ddof=1), pct_w,
             "걸림" if pct_w < 95 else "통과"))

    # F4 — 셔플
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
        e = ex(run(sel)[0]).reindex(E_c.index).dropna()
        if len(e) > 12:
            shuf.append(float(e.mean() * 1200))
    shuf = np.array(shuf)
    pct_s = float((shuf < S_c["y_pp"]).mean() * 100)
    print("\n■ F4 셔플 %d회 — 실측 %+.2f%%p · 평균 %+.2f%%p (sd %.2f) · **백분위 %.1f** → %s"
          % (len(shuf), S_c["y_pp"], shuf.mean(), shuf.std(ddof=1), pct_s,
             "걸림" if pct_s < 95 else "통과"))

    # 유효 자유도 · 펀드 상관
    ev = np.linalg.eigvalsh(Pm.corr().to_numpy())[::-1]
    ev = ev[ev > 0]
    print("\n■ 부분 넷의 유효 자유도 %.1f개 (첫 주성분 %.0f%%)"
          % (ev.sum() ** 2 / (ev ** 2).sum(), 100 * ev[0] / ev.sum()))
    try:
        from fund_fit import fund_monthly
        F = fund_monthly()
        jj = E_c.index.intersection(F.index)
        print("   펀드 상관 %+.2f (%d개월)"
              % (float(np.corrcoef(E_c.reindex(jj), F.reindex(jj))[0, 1]), len(jj)))
    except Exception as e_:
        print("   (펀드 상관 못 쟀다: %s)" % e_)

    h = len(E_c) // 2
    print("\n■ 표본 절반씩 — 앞 %+.2f%%p · 뒤 %+.2f%%p"
          % (E_c.iloc[:h].mean() * 1200, E_c.iloc[h:].mean() * 1200))

    f = {"F1": S_c["y_pp"] <= 0, "F2": S_c["y_pp"] <= best["y_pp"],
         "F3": pct_w < 95, "F4": pct_s < 95, "F5": thin / len(DG) > 0.10,
         "F6": cmax > 0.90, "F7": S_c["turn"] > TURN_CAP}
    txt = {"F1": "PIT 초과 ≤ 0", "F2": "부분의 최고를 못 넘음",
           "F3": "무작위 가중 백분위 < 95", "F4": "셔플 백분위 < 95",
           "F5": "후보 30종 미만 > 10%", "F6": "부분과 상관 0.90 초과",
           "F7": "연 회전 > 12회"}
    print("\n■ 기각 조건")
    for k in sorted(f):
        print("   %s %s %s" % ("❌ 걸림" if f[k] else "✅ 통과", k, txt[k]))
    verdict = "기각" if any(f.values()) else "등록 조건 전부 통과"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": "build/PREREG-2026-09-20-REVCOMP.md",
        "commit_before": "0706357a134aa1899818357eb8962bed36ebd77c",
        "blob": "c19f465c0246d640f6daf4766d2ed172add95b9b",
        "const": {"W_W": W_W, "W_M": W_M, "W_S": W_S, "W_E": W_E, "SMA": SMA,
                  "TOPN": TOPN, "BAND": BAND, "COST": COST, "TURN_CAP": TURN_CAP,
                  "NSHUF": NSHUF, "SEED": SEED},
        "stats": {"comp": S_c, "parts": {a: P_s[a] for a in AXES}},
        "corr_max": cmax, "rand_w_pct": pct_w, "shuffle_pct": pct_s,
        "diag": DG.to_dict("records"), "fails": f, "verdict": verdict,
        "series": {"comp": {str(k): float(v) for k, v in E_c.items()}},
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
