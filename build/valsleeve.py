# -*- coding: utf-8 -*-
"""build/valsleeve.py — 가치·주주환원 슬리브. 규약은 PREREG-2026-09-20-VALSLEEVE.md.

🚨 등록서에 적은 것만 한다. 결과를 보고 배합(20%)·축 개수(5)·바스켓 크기(10)를
   바꾸지 않는다. 참고표는 내되 판정은 못박은 값으로만 한다.
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
D18 = r"C:\Users\Win10\Documents\여두_20260918"
OUT = os.path.join(DATA, "_valsleeve.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shares_split import cap_frame2                     # noqa: E402

# ── 등록서 §1 의 상수. 여기서만 바꾼다 ──────────────────────────────────────
LAG_M = 4            # 분기 종료 + 4개월 지난 것만 쓴다
TOPN = 10            # 축마다 상위 10종 동일가중
COST = 0.0025        # 왕복 25bp — 펀드와 같은 값
MIXW = 0.20          # 혼합판: 펀드 80% + 슬리브 20%
NSHUF, SEED = 200, 20260920
FORM_M = (3, 6, 9, 12)
AXES = ("FCFY", "SP", "BTP", "PAYOUT", "DIVGROW")


def ser(tag, kind="q"):
    return (tag or {}).get(kind) or []


def load_facts():
    """분기 재무 → {태그: DataFrame(t, end, v, kind)}.

    🚨 2026-09-20 구현 정정 — 처음에 흐름 항목을 `q`(분기)만 읽었더니
       **FCFY·PAYOUT 의 후보가 1종**이 됐다. 이유를 파 보니 현금흐름표 항목의 `q`
       계열이 회사마다 듬성하다 — JNJ·KO 는 18행으로 **사실상 연 1회(1분기)만** 들어 있다
       (현금흐름표가 누적 공시라 깨끗한 분기 차분이 안 나오는 분기를 추출기가 버린 것).
       반면 `a`(회계연도) 계열은 19행으로 온전하다.

       **회계연도 합계도 «최근 4분기 합»이다.** 그래서 둘을 같은 표에 넣고
       `asof` 가 그때 쓸 수 있는 **가장 최근 것**을 고르게 한다.
       ⚠ 규칙을 바꾼 것이 아니라 **규칙이 말한 것을 자료가 담긴 모양대로 읽는 것**이다.
         등록서 §1-2 의 «최근 4분기 합» 그대로이고, 분위·크기·주기는 손대지 않았다.
       ⚠ 대신 연간값은 더 낡았다(가장 오래된 분기가 최대 16개월 전). 그 대가는
         결과문서에 «어느 출처를 얼마나 썼나»로 적는다.
    """
    rows = {k: [] for k in ("cfo", "capex", "rev", "eq", "dps", "bb", "sh")}
    for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8"))
        tg = j.get("tags") or {}
        t = j["t"]
        for k in ("cfo", "capex", "rev", "dps", "bb"):
            for end, v, *_ in ser(tg.get(k)):
                rows[k].append({"t": t, "end": end, "v": float(v), "kind": "q"})
            for end, v, *_ in ser(tg.get(k), "a"):
                rows[k].append({"t": t, "end": end, "v": float(v), "kind": "a"})
        for end, v, *_ in (ser(tg.get("eq"), "i") or ser(tg.get("eq")) or ser(tg.get("eq"), "a")):
            rows["eq"].append({"t": t, "end": end, "v": float(v), "kind": "i"})
        s = tg.get("sh") or tg.get("sho")
        for end, v, *_ in (ser(s, "i") or ser(s) or ser(s, "a")):
            rows["sh"].append({"t": t, "end": end, "v": float(v), "kind": "i"})
    out = {}
    for k, r in rows.items():
        D = pd.DataFrame(r)
        if D.empty:
            out[k] = D; continue
        D = D.drop_duplicates(["t", "end", "kind"], keep="last")
        D["q"] = pd.PeriodIndex(pd.to_datetime(D.end), freq="Q")
        D["avail"] = (D.q.dt.end_time + pd.DateOffset(months=LAG_M)).dt.to_period("M")
        out[k] = D
    return out


USED = {}          # 출처 집계 — 결과문서에 싣는다


def roll4(D, tag=""):
    """최근 4분기 합 → {(t, avail월): 값}.

    ⓐ `q` 가 4분기 연속으로 있으면 그 합.
    ⓑ `a`(회계연도 합계)도 같은 표에 넣는다 — 그것도 4분기 합이다.
    asof 가 그때 쓸 수 있는 가장 최근 것을 고른다.
    """
    if D.empty:
        return {}
    got, cnt = {}, {"q": 0, "a": 0}
    Dq = D[D.kind == "q"]
    for t, g in Dq.sort_values("q").groupby("t"):
        s = g.set_index("q").v
        s = s[~s.index.duplicated(keep="last")]
        full = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="Q"))
        s4 = full.rolling(4).sum()
        for qq, v in s4.items():
            if pd.notna(v):
                got[(t, (qq.end_time + pd.DateOffset(months=LAG_M)).to_period("M"))] = float(v)
                cnt["q"] += 1
    for r in D[D.kind == "a"].itertuples():
        key = (r.t, r.avail)
        if key not in got:
            got[key] = float(r.v); cnt["a"] += 1
    USED[tag] = cnt
    return got


def roll4_prev(D, tag=""):
    """최근 4분기 합과 **그 1년 전** 4분기 합의 짝 — DIVGROW 용."""
    cur = roll4(D, tag)
    byt = {}
    for (t, a), v in cur.items():
        byt.setdefault(t, {})[a] = v
    got = {}
    for t, d in byt.items():
        for a, v in d.items():
            p = a - 12
            prev = d.get(p)
            if prev is None:                       # 정확히 12개월 전이 없으면 가장 가까운 이전
                cand = [x for x in d if a - 15 <= x <= a - 9]
                if cand:
                    prev = d[max(cand)]
            if prev is not None and prev > 0:
                got[(t, a)] = (v, prev)
    return got


def index_by_t(table):
    """{(t, avail월): v} → {t: ([avail 오름차순], [v])}. asof 를 이분탐색으로 만든다.

    ⚠ 처음에는 asof 가 표 전체를 훑었다. 종목 500 × 분기 49 × 축 7 × 관측 2만이라
      실제로 안 끝났다. **계산이 안 끝나면 규약을 못 지킨 것과 같다.**
    """
    g = {}
    for (t, a), v in table.items():
        g.setdefault(t, []).append((a, v))
    return {t: (list(x[0] for x in sorted(r)), list(x[1] for x in sorted(r)))
            for t, r in g.items()}


def asof(idx, t, m):
    """t 종목이 m 월에 **쓸 수 있는** 가장 최근 값(이분탐색)."""
    r = idx.get(t)
    if not r:
        return None
    ks, vs = r
    lo, hi = 0, len(ks)
    while lo < hi:                       # ks 에서 m 이하의 마지막 자리
        mid = (lo + hi) // 2
        if ks[mid] <= m:
            lo = mid + 1
        else:
            hi = mid
    return vs[lo - 1] if lo else None


def main():
    # ── 가격·시총·명단 ────────────────────────────────────────────────────
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
    CAP = cap_frame2(M, DATA)
    SEC = {s["t"]: s.get("sector") for s in st["stocks"]}

    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    months = hist["months"]

    # ── 지수 총수익 · 펀드 ────────────────────────────────────────────────
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

    # ── 점수 재료 ────────────────────────────────────────────────────────
    F = load_facts()
    print("재무 태그 로드 — " + " · ".join(
        "%s %d행/%d종" % (k, len(v), v.t.nunique()) for k, v in F.items() if not v.empty))
    CFO, CAPEX = index_by_t(roll4(F["cfo"], "cfo")), index_by_t(roll4(F["capex"], "capex"))
    REV, BB = index_by_t(roll4(F["rev"], "rev")), index_by_t(roll4(F["bb"], "bb"))
    DPS4, DPSG = index_by_t(roll4(F["dps"], "dps")), index_by_t(roll4_prev(F["dps"], "dps2"))
    EQ = index_by_t({(r.t, r.avail): r.v for r in F["eq"].itertuples()})
    SH = index_by_t({(r.t, r.avail): r.v for r in F["sh"].itertuples()})

    forms = sorted(m for m in months if int(m[5:7]) in FORM_M)
    forms = [m for m in forms if pd.Period(m, freq="M") in CAP.index]

    picks, diag, axis_picks = {}, [], {}
    for fm in forms:
        mp = pd.Period(fm, freq="M")
        uni = [t for t in (months[fm].get("spx") or [])
               if t in CAP.columns and np.isfinite(CAP.at[mp, t]) and CAP.at[mp, t] > 0]
        cap = {t: float(CAP.at[mp, t]) for t in uni}
        sc = {a: {} for a in AXES}
        for t in uni:
            c = cap[t]
            cf, cx = asof(CFO, t, mp), asof(CAPEX, t, mp)
            if cf is not None and cx is not None:
                sc["FCFY"][t] = (cf - cx) / c
            rv = asof(REV, t, mp)
            if rv is not None:
                sc["SP"][t] = rv / c
            eq = asof(EQ, t, mp)
            if eq is not None and eq > 0:
                sc["BTP"][t] = eq / c
            d4, bb, sh = asof(DPS4, t, mp), asof(BB, t, mp), asof(SH, t, mp)
            if d4 is not None and sh is not None and bb is not None:
                sc["PAYOUT"][t] = (d4 * sh + bb) / c
            g = asof(DPSG, t, mp)
            if g is not None and g[1] > 0:
                sc["DIVGROW"][t] = g[0] / g[1] - 1.0
        row = {"m": fm, "uni": len(uni)}
        w = {}
        for a in AXES:
            s = sc[a]
            row["n_" + a] = len(s)
            if len(s) < TOPN:
                continue
            top = sorted(s.items(), key=lambda x: -x[1])[:TOPN]
            axis_picks[(fm, a)] = {t: 1.0 / TOPN for t, _ in top}
            for t, _ in top:
                w[t] = w.get(t, 0.0) + (1.0 / len(AXES)) / TOPN
        picks[fm] = w
        row["n_sleeve"] = len(w)
        diag.append(row)
    DG = pd.DataFrame(diag)
    print("\n■ 형성 %d분기 (%s ~ %s) · 유니버스 중앙 %d종"
          % (len(DG), DG.m.iloc[0], DG.m.iloc[-1], int(DG.uni.median())))
    print("   축별 후보 중앙 — " + " · ".join("%s %d" % (a, int(DG["n_" + a].median())) for a in AXES))
    print("   슬리브 종목 수 중앙 %d (최소 %d · 최대 %d) — 다섯 축 50칸 중 겹친 만큼 줄어든다"
          % (int(DG.n_sleeve.median()), DG.n_sleeve.min(), DG.n_sleeve.max()))
    thin = int((DG.n_sleeve < 30).sum())
    print("   30종 미만인 분기 %d개 (%.1f%%)  → F5 %s"
          % (thin, 100 * thin / len(DG), "걸림" if thin / len(DG) > 0.10 else "통과"))

    # ── 굴린다 ───────────────────────────────────────────────────────────
    def run(sel):
        """{형성월: 비중} → (월수익 Series, 월회전 dict)."""
        out, trn, prev = {}, {}, {}
        for fm in sorted(sel):
            w = dict(sel[fm])
            if not w:
                continue
            z = sum(w.values())
            w = {t: v / z for t, v in w.items()}
            trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
            trn[fm] = trade
            first = True
            for k in (1, 2, 3):
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
                zz = sum(w.values()); w = {t: v / zz for t, v in w.items()}
            prev = w
        return pd.Series(out, dtype="float64"), trn

    # 축별 바스켓도 따로 굴린다 — 다섯 중 하나가 끌고 가는지 보려면 필요하다
    AXR = {}
    for a in AXES:
        sel_a = {}
        for fm in forms:
            w = axis_picks.get((fm, a))
            if w:
                sel_a[fm] = dict(w)
        if sel_a:
            r_, _t = run(sel_a)
            ms = [m for m in r_.index if m in BM]
            AXR[a] = pd.Series([r_[m] - BM[m] for m in ms],
                               index=pd.PeriodIndex(ms, freq="M"), dtype="float64")

    sl_r, sl_trn = run(picks)
    fd_r, fd_trn = run(fund_sel)
    mix_sel = {}
    for fm in sorted(set(picks) | set(fund_sel)):
        a, b = fund_sel.get(fm) or {}, picks.get(fm) or {}
        if not a or not b:
            continue
        w = {}
        for t, v in a.items():
            w[t] = w.get(t, 0.0) + (1 - MIXW) * v
        for t, v in b.items():
            w[t] = w.get(t, 0.0) + MIXW * v
        mix_sel[fm] = w
    mx_r, mx_trn = run(mix_sel)

    def ex(series):
        ms = [m for m in series.index if m in BM]
        return pd.Series([series[m] - BM[m] for m in ms],
                         index=pd.PeriodIndex(ms, freq="M"), dtype="float64")
    E_sl, E_fd, E_mx = ex(sl_r), ex(fd_r), ex(mx_r)
    j = E_sl.index.intersection(E_fd.index).intersection(E_mx.index)
    E_sl, E_fd, E_mx = E_sl.reindex(j), E_fd.reindex(j), E_mx.reindex(j)

    def stat(e, trn):
        n = len(e)
        te = float(e.std(ddof=1) * np.sqrt(12) * 100)
        return {"y_pp": float(e.mean() * 1200), "te": te,
                "t": float(e.mean() / (e.std(ddof=1) / np.sqrt(n))),
                "ir": float(e.mean() * 1200 / te) if te else np.nan,
                "win": float((e > 0).mean() * 100), "n": n,
                "turn": float(np.mean(list(trn.values())) * 4) if trn else np.nan}
    S_sl, S_fd, S_mx = stat(E_sl, sl_trn), stat(E_fd, fd_trn), stat(E_mx, mx_trn)

    print("\n■ 성적 (비용 후 · 잣대 B = TR − S&P 500 TR) · %d개월 (%s ~ %s)"
          % (len(j), j[0], j[-1]))
    print("   %-14s %10s %8s %7s %7s %7s %8s" % ("", "초과/년", "TE", "t", "IR", "승률", "연회전"))
    for nm, s in (("펀드", S_fd), ("슬리브", S_sl), ("혼합 80/20", S_mx)):
        print("   %-14s %+9.2f%%p %7.2f%% %7.2f %7.2f %6.1f%% %7.2f회"
              % (nm, s["y_pp"], s["te"], s["t"], s["ir"], s["win"], s["turn"]))
    print("   혼합 − 펀드   초과 %+.2f%%p · TE %+.2f%%p · **IR %+.3f**"
          % (S_mx["y_pp"] - S_fd["y_pp"], S_mx["te"] - S_fd["te"], S_mx["ir"] - S_fd["ir"]))

    # 증분 알파 — 슬리브를 펀드에 회귀
    def ols(y, x):
        Xm = np.column_stack([np.ones(len(x)), x])
        bh, *_ = np.linalg.lstsq(Xm, y, rcond=None)
        e = y - Xm @ bh
        s2 = float(e @ e) / (len(y) - 2)
        se = np.sqrt(np.diag(np.linalg.inv(Xm.T @ Xm) * s2))
        return float(bh[0]), float(bh[0] / se[0]), float(bh[1])
    a, ta, beta = ols(E_sl.to_numpy(), E_fd.to_numpy())
    corr = float(np.corrcoef(E_sl, E_fd)[0, 1])
    print("\n■ 펀드 위의 증분 — 슬리브 초과를 펀드 초과에 회귀")
    print("   알파 연 %+.2f%%p · **t %.2f** · β %+.2f · 상관 %+.2f"
          % (a * 1200, ta, beta, corr))

    # ── 겹침 ─────────────────────────────────────────────────────────────
    ov = []
    for fm in sorted(set(picks) & set(fund_sel)):
        a_, b_ = fund_sel[fm], picks[fm]
        za, zb = sum(a_.values()), sum(b_.values())
        if za <= 0 or zb <= 0:
            continue
        sh_ = sum(min(a_[t] / za, b_[t] / zb) for t in set(a_) & set(b_))
        ov.append({"m": fm, "n": len(set(a_) & set(b_)), "w": sh_ * 100})
    OV = pd.DataFrame(ov)
    print("\n■ 펀드와의 종목 겹침")
    print("   종목 수 중앙 %.0f종 (최대 %d) · **비중 기준 중앙 %.1f%% (최대 %.1f%%)**"
          % (OV.n.median(), OV.n.max(), OV.w.median(), OV.w.max()))
    print("   → F6 %s (문턱 50%%)" % ("걸림" if OV.w.median() > 50 else "통과"))

    # ── 섹터 쏠림 ────────────────────────────────────────────────────────
    last = forms[-1]
    ws = picks[last]; zs = sum(ws.values())
    sec = {}
    for t, v in ws.items():
        sec[SEC.get(t) or "?"] = sec.get(SEC.get(t) or "?", 0.0) + v / zs * 100
    print("\n■ 슬리브 섹터 쏠림 (%s 형성)" % last)
    for k, v in sorted(sec.items(), key=lambda x: -x[1])[:6]:
        print("   %-26s %5.1f%%" % (k, v))

    # ── 앞/뒤 절반 ───────────────────────────────────────────────────────
    h = len(j) // 2
    print("\n■ 표본 절반씩")
    for nm, sl_ in (("앞 절반", slice(0, h)), ("뒤 절반", slice(h, None))):
        y, x = E_sl.iloc[sl_].to_numpy(), E_fd.iloc[sl_].to_numpy()
        aa, tt, _ = ols(y, x)
        print("   %s (%s~%s)  슬리브 %+6.2f%%p · 증분 %+6.2f%%p (t %5.2f)"
              % (nm, j[sl_][0], j[sl_][-1], y.mean() * 1200, aa * 1200, tt))
    y2, x2 = E_sl.iloc[h:].to_numpy(), E_fd.iloc[h:].to_numpy()
    a2, _, _ = ols(y2, x2)
    print("   → F7 %s (뒤 절반 부호 %s)"
          % ("걸림" if a2 * a <= 0 else "통과", "반전" if a2 * a <= 0 else "유지"))

    # ── 셔플 ─────────────────────────────────────────────────────────────
    rng = np.random.default_rng(SEED)
    sizes = {fm: len(w) for fm, w in picks.items() if w}
    shuf = []
    for _ in range(NSHUF):
        sel = {}
        for fm, k in sizes.items():
            mp = pd.Period(fm, freq="M")
            uni = [t for t in (months[fm].get("spx") or [])
                   if t in CAP.columns and np.isfinite(CAP.at[mp, t]) and CAP.at[mp, t] > 0]
            if len(uni) < k:
                continue
            pick = rng.choice(len(uni), size=k, replace=False)
            sel[fm] = {uni[i]: 1.0 / k for i in pick}
        r, _t = run(sel)
        e = ex(r).reindex(j).dropna()
        shuf.append(float(e.mean() * 1200) if len(e) > 12 else np.nan)
    shuf = np.array([s for s in shuf if np.isfinite(s)])
    pct = float((shuf < S_sl["y_pp"]).mean() * 100)
    print("\n■ F4 셔플 %d회 — 같은 크기 무작위 바스켓" % len(shuf))
    print("   실측 %+.2f%%p · 셔플 평균 %+.2f%%p (sd %.2f) · **백분위 %.1f**"
          % (S_sl["y_pp"], shuf.mean(), shuf.std(ddof=1), pct))

    # ── 국면 ─────────────────────────────────────────────────────────────
    try:
        ffd = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
        FD = pd.DataFrame(ffd["series"], index=pd.to_datetime(ffd["dates"])) / 100.0
        vol = FD.mkt_rf.groupby(FD.index.to_period("M")).std() * np.sqrt(252)
        v = vol.reindex(j).dropna()
        q1, q2 = v.quantile(1 / 3), v.quantile(2 / 3)
        print("\n■ 시장변동성 3분위 — 펀드의 약점을 메우나 (월 %)")
        print("   %-10s %9s %9s %9s" % ("", "저변동", "중간", "고변동"))
        for nm, e in (("펀드", E_fd), ("슬리브", E_sl), ("혼합", E_mx)):
            cells = []
            for lo, hi in ((None, q1), (q1, q2), (q2, None)):
                sel = v[(v > lo if lo is not None else v == v) &
                        (v <= hi if hi is not None else v == v)].index
                cells.append(float(e.reindex(sel).mean() * 100))
            print("   %-10s %+8.3f %+8.3f %+8.3f" % (nm, *cells))
    except Exception as ex_:
        print("\n(국면 못 쟀다: %s)" % ex_)

    # ── 판정 ─────────────────────────────────────────────────────────────
    f = {
        "F1": S_sl["y_pp"] <= 0,
        "F2": (S_mx["ir"] - S_fd["ir"]) < 0.05,
        "F3": ta < 2,
        "F4": pct < 95,
        "F5": thin / len(DG) > 0.10,
        "F6": OV.w.median() > 50,
        "F7": a2 * a <= 0,
    }
    txt = {"F1": "슬리브 단독 초과 ≤ 0", "F2": "IR 개선 < 0.05", "F3": "증분 알파 t < 2",
           "F4": "셔플 백분위 < 95", "F5": "후보 30종 미만 분기 > 10%",
           "F6": "펀드와 겹침 > 50%", "F7": "뒤 절반 부호 반전"}
    print("\n■ 기각 조건")
    for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7"):
        print("   %s %s %s" % ("❌ 걸림" if f[k] else "✅ 통과", k, txt[k]))
    verdict = "기각" if any(f.values()) else "등록 조건 전부 통과(게시 여부는 별도 · 결과문서 판정은 보류)"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": "build/PREREG-2026-09-20-VALSLEEVE.md",
        "commit_before": "3343933659daaeff80b78cca092b34a333c81247",
        "blob": "97f0ab3a7b13b5a987af267a3ab511126ca5c541",
        "const": {"LAG_M": LAG_M, "TOPN": TOPN, "COST": COST, "MIXW": MIXW,
                  "NSHUF": NSHUF, "SEED": SEED},
        "window": {"start": str(j[0]), "end": str(j[-1]), "n": len(j)},
        "stats": {"fund": S_fd, "sleeve": S_sl, "mix": S_mx},
        "incr": {"alpha_y_pp": a * 1200, "t": ta, "beta": beta, "corr": corr},
        "overlap": {"n_med": float(OV.n.median()), "w_med": float(OV.w.median()),
                    "w_max": float(OV.w.max())},
        "shuffle": {"n": len(shuf), "mean": float(shuf.mean()),
                    "sd": float(shuf.std(ddof=1)), "pct": pct},
        "sector_last": sec, "fails": f, "verdict": verdict,
        "used": USED,
        # 월별 계열 — 등록서 밖 검정(valsleeve_diag.py)이 읽는다.
        "series": {"sleeve": {str(k): float(v) for k, v in E_sl.items()},
                   "fund": {str(k): float(v) for k, v in E_fd.items()},
                   "mix": {str(k): float(v) for k, v in E_mx.items()}},
        "axis_series": {a: {str(k): float(v) for k, v in s_.items()}
                        for a, s_ in AXR.items()},
        "diag": DG.to_dict("records"),
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
