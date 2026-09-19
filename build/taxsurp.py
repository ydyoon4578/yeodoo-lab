# -*- coding: utf-8 -*-
"""build/taxsurp.py — 세금비용 서프라이즈 (PREREG-2026-09-19-TAXSURP · 계산 전 2300c7c)

  신호 = (세금_주당(q) − 세금_주당(q−4)) / 자산총계_주당(q−4)
  매월 초 · 최소 4개월 지난 분기만 · 세금 0 제외 · 십분위 52종
  동일가중·시총가중 둘 다 · 보유 1·6·12개월 셋 다 · 본문에 나란히

🚨 등록서 §0 — 0 이 나오면 그대로 0 이라고 적는다. 규칙을 손보지 않는다.

  python build/taxsurp.py
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_taxsurp.json")
N_SEL, MIN_POOL, NSHUF, SEED = 52, 30, 200, 20260919
HOLDS = (1, 6, 12)
LAG_M = 4                      # 최소 4개월 지난 분기만
TAXYEARS = (2018, 2026)        # 세법 개정 회계연도


def ser(tag, kind="q"):
    return (tag or {}).get(kind) or []


def load():
    """fxe(세금) + fx(자산·주식수) → 분기 패널."""
    rows = []
    for d in (os.path.join(DATA, "fxe"), os.path.join(DATA, "fxe_pit")):
        for p in glob.glob(os.path.join(d, "*.json")):
            j = json.load(io.open(p, encoding="utf-8"))
            for end, v, *_ in ser((j.get("tags") or {}).get("tax")):
                rows.append({"t": j["t"], "end": end, "tax": float(v)})
    TX = pd.DataFrame(rows)
    ar, sh = [], []
    for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8"))
        tg = j.get("tags") or {}
        for end, v, *_ in (ser(tg.get("asset"), "i") or ser(tg.get("asset"), "q")):
            ar.append({"t": j["t"], "end": end, "asset": float(v)})
        s = tg.get("sh") or tg.get("sho")
        for end, v, *_ in (ser(s, "i") or ser(s, "q") or ser(s, "a")):
            sh.append({"t": j["t"], "end": end, "sh": float(v)})
    return TX, pd.DataFrame(ar), pd.DataFrame(sh)


def main():
    TX, A, SH = load()
    print("세금(분기) %d행 · %d종 | 자산 %d행 · %d종 | 주식수 %d행 · %d종"
          % (len(TX), TX.t.nunique(), len(A), A.t.nunique(), len(SH), SH.t.nunique()))
    if TX.empty:
        print("❌ 세금 자료 없음"); return 1

    df = TX.merge(A, on=["t", "end"], how="inner").merge(SH, on=["t", "end"], how="inner")
    df = df[(df.sh > 0) & (df.asset > 0)]
    df["q"] = pd.PeriodIndex(pd.to_datetime(df.end), freq="Q")
    df = df.sort_values(["t", "q"]).drop_duplicates(["t", "q"], keep="last")
    df["tax_ps"] = df.tax / df.sh
    df["at_ps"] = df.asset / df.sh
    print("   합쳐진 분기 %d행 · %d종 · %s ~ %s"
          % (len(df), df.t.nunique(), df.q.min(), df.q.max()))

    # ── 계절차분 — q−4 가 «정확히» 4분기 전이어야 한다 ──────────────────────
    prev = df[["t", "q", "tax_ps", "at_ps"]].copy()
    prev["q"] = prev.q + 4
    prev = prev.rename(columns={"tax_ps": "tax_ps4", "at_ps": "at_ps4"})
    S = df.merge(prev, on=["t", "q"], how="inner")
    n_before = len(S)
    S = S[(S.tax != 0) & (S.at_ps4 > 0)]                    # 세금 0 제외(카드 ①)
    S["sig"] = (S.tax_ps - S.tax_ps4) / S.at_ps4
    S = S[np.isfinite(S.sig)]
    print("   계절차분 %d행 (세금 0 제외 전 %d) · %d종" % (len(S), n_before, S.t.nunique()))

    # 사용 가능 시점 = 분기말 + 4개월. 실적발표일이 더 늦으면 그쪽을 쓴다(카드 ②).
    S["avail"] = (S.q.dt.end_time + pd.DateOffset(months=LAG_M)).dt.to_period("M")
    try:
        ed = json.load(io.open(os.path.join(DATA, "earn_dates.json"), encoding="utf-8"))
        emap = {}
        for t, v in (ed.get("co") or ed.get("dates") or {}).items():
            for x in (v if isinstance(v, list) else []):
                d = x if isinstance(x, str) else (x.get("d") or x.get("date"))
                if d:
                    emap.setdefault(t, []).append(d)
        n_pushed = 0
        for t in emap:
            emap[t] = sorted(emap[t])
        av = []
        for _, r in S.iterrows():
            qe = r.q.end_time.strftime("%Y-%m-%d")
            lst = emap.get(r.t) or []
            nxt = next((d for d in lst if d > qe), None)
            p1 = r.avail
            if nxt:
                p2 = pd.Period(nxt[:7], freq="M") + 1
                if p2 > p1:
                    n_pushed += 1
                    p1 = p2
            av.append(p1)
        S["avail"] = av
        print("   실적발표일 대조 — 더 늦어서 미룬 관측 %d / %d (%.1f%%)"
              % (n_pushed, len(S), n_pushed / max(1, len(S)) * 100))
    except Exception as e:
        print("   ⚠ 실적발표일 대조 실패: %s — 4개월 규약만 적용" % e)

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
    M = P.resample("M").last()
    MR = M.pct_change()
    # 🚨 월 인덱스를 Period 로 바꿔 둔다. Timestamp 인덱스에 Period 로 조회하면 조용히
    #   전부 NaN 이 되고, 처음에 «신호 생기는 종목 0종» 이 그렇게 나왔다.
    mper = M.index.to_period("M")
    M.index = mper
    MR.index = mper
    print("   가격 %d종 · 월 %d개" % (P.shape[1], len(M)))

    # 시총 = 종가 × 보고 주식수(카드 §3 — 최대 3개월 낡는다)
    shp = SH.copy()
    shp["m"] = pd.PeriodIndex(pd.to_datetime(shp.end), freq="M")
    shw = shp.pivot_table(index="m", columns="t", values="sh", aggfunc="last")
    shw = shw.reindex(mper).ffill()
    CAP = M.reindex(columns=shw.columns).to_numpy() * shw.to_numpy()
    CAP = pd.DataFrame(CAP, index=mper, columns=shw.columns).reindex(columns=M.columns)

    # ── 월별 신호판 ───────────────────────────────────────────────────────
    S["avail"] = pd.PeriodIndex(S.avail, freq="M")
    sig_by_m = {}
    for m, g in S.groupby("avail"):
        g = g.sort_values("q").drop_duplicates("t", keep="last")   # 가장 최근 분기
        sig_by_m[m] = dict(zip(g.t, g.sig))
    # 매월: 그 달까지 나온 것 중 가장 최근 신호를 쓴다
    months = [m for m in mper if m >= min(sig_by_m)] if sig_by_m else []
    cur, panel, npool = {}, {}, []
    for m in months:
        cur.update(sig_by_m.get(m, {}))
        have = {t: v for t, v in cur.items() if t in M.columns and (m in M.index and pd.notna(M.at[m, t]))}
        panel[m] = have
        npool.append(len(have))
    print("\n■ 카드 §4-1 — 신호가 생기는 종목 수")
    npa = np.array(npool)
    print("   월 %d개 · 중앙 %d종 · 최소 %d · 최대 %d · 30종 미만인 달 %d개"
          % (len(npa), int(np.median(npa)), npa.min(), npa.max(), int((npa < MIN_POOL).sum())))

    def legs(panel_, weight, hold, drop_tax_years=False, shuffled=None, rng=None):
        rows = {"ls": [], "lo": [], "bench": []}
        mlist = [m for m in months if len(panel_.get(m, {})) >= MIN_POOL]
        for k, m in enumerate(mlist):
            if drop_tax_years and (m.year in TAXYEARS):
                continue
            d = panel_[m]
            ts = list(d)
            v = np.array([d[t] for t in ts], float)
            if shuffled is not None:
                v = rng.permutation(v)
            o = np.argsort(v)
            lo_t = [ts[i] for i in o[-N_SEL:]]               # 상위(롱)
            hi_t = [ts[i] for i in o[:N_SEL]]                # 하위(숏)
            fut = [mm for mm in months if mm > m][:hold]
            if len(fut) < hold:
                break

            def ret(names):
                if weight == "cap":
                    w = CAP.loc[m, names].astype(float)
                    w = w / w.sum() if np.isfinite(w).all() and w.sum() > 0 else None
                    if w is None:
                        w = pd.Series(1.0 / len(names), index=names)
                else:
                    w = pd.Series(1.0 / len(names), index=names)
                acc = 0.0
                for mm in fut:
                    r = MR.loc[mm, names].astype(float).fillna(0.0)
                    acc += float((w * r).sum())
                return acc / hold                              # 월평균
            rows["ls"].append(ret(lo_t) - ret(hi_t))
            rows["lo"].append(ret(lo_t))
            allt = [t for t in d if t in M.columns]
            rows["bench"].append(float(MR.loc[fut, allt].astype(float).fillna(0).mean(axis=1).mean()))
        return {k: np.array(v) for k, v in rows.items()}

    def tstat(x):
        x = x[np.isfinite(x)]
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 5 else float("nan")

    print("\n■ 카드 §4-2 — 동일가중 vs 시총가중 (월 %% · 롱숏 십분위 %d종)" % N_SEL)
    print("   %-8s %s" % ("가중", "".join("%22s" % ("보유 %d개월" % h) for h in HOLDS)))
    res = {}
    for wname, wtag in (("동일가중", "ew"), ("시총가중", "cap")):
        cells, row = [], {}
        for h in HOLDS:
            L = legs(panel, wtag, h)
            mu, t = L["ls"].mean() * 100, tstat(L["ls"])
            cells.append("%+8.3f%% (t%5.2f)" % (mu, t))
            row["%d" % h] = {"mean_pct": mu, "t": t, "n": int(len(L["ls"])),
                             "long_only_pct": float(L["lo"].mean()) * 100,
                             "bench_pct": float(L["bench"].mean()) * 100}
        res[wname] = row
        print("   %-8s %s" % (wname, "".join("%22s" % c for c in cells)))
    print("   ⚠ 복제 논문(Hou·Xue·Zhang 2020) — 동일가중 0.78·0.40·0.15 / 시총가중 0.23·0.24·0.16")

    print("\n■ 카드 §4-4 — 세법 개정 회계연도(%s) 넣은 판과 뺀 판 · 보유 1개월"
          % "·".join(map(str, TAXYEARS)))
    tw = {}
    for wname, wtag in (("동일가중", "ew"), ("시총가중", "cap")):
        a = legs(panel, wtag, 1)["ls"]
        b = legs(panel, wtag, 1, drop_tax_years=True)["ls"]
        tw[wname] = {"in": a.mean() * 100, "out": b.mean() * 100,
                     "t_in": tstat(a), "t_out": tstat(b), "n_out": int(len(b))}
        print("   %-8s 넣은 판 %+7.3f%% (t%5.2f) · 뺀 판 %+7.3f%% (t%5.2f · n%d)"
              % (wname, a.mean() * 100, tstat(a), b.mean() * 100, tstat(b), len(b)))

    # ── F6 — 세금 태그 유무 ───────────────────────────────────────────────
    have_t = set(S.t.unique())
    cols = [c for c in M.columns if c in {s["t"] for s in st["stocks"]}]
    hv = [c for c in cols if c in have_t]
    nv = [c for c in cols if c not in have_t]
    f6 = 0.0
    if len(nv) > 3:
        a = MR[hv].mean(axis=1).mean() * 1200
        b = MR[nv].mean(axis=1).mean() * 1200
        f6 = a - b
        print("\n   F6 — 세금 태그 있는 %d종 연 %+.2f%% vs 없는 %d종 연 %+.2f%% · 차 %+.2f%%p"
              % (len(hv), a, len(nv), b, f6))

    # ── F2 셔플 ───────────────────────────────────────────────────────────
    print("\n■ F2 셔플 %d회 (시총가중 · 보유 1개월)" % NSHUF)
    rng = np.random.default_rng(SEED)
    act = res["시총가중"]["1"]["mean_pct"]
    sh_ = np.empty(NSHUF)
    for q in range(NSHUF):
        sh_[q] = legs(panel, "cap", 1, shuffled=True, rng=rng)["ls"].mean() * 100
        if (q + 1) % 50 == 0:
            print("   ... %d회" % (q + 1))
    pct = float((sh_ < act).mean()) * 100
    print("   실측 %+.3f%% · 셔플 평균 %+.3f%% (표준편차 %.3f) · 백분위 %.1f"
          % (act, sh_.mean(), sh_.std(ddof=1), pct))

    pos3 = all(res["시총가중"]["%d" % h]["mean_pct"] > 0 for h in HOLDS)
    F = {"F1 시총가중 세 기간 모두 양수 아님": not pos3,
         "F2 셔플 상위 5% 밖": pct < 95.0,
         "F4 세법연도 빼면 부호 반전": (tw["시총가중"]["in"] > 0) != (tw["시총가중"]["out"] > 0),
         "F6 태그 유무 수익차 |Δ| > 3%p": abs(f6) > 3.0}
    print("\n■ 기각 조건 (F3·F5 는 §7 참조)")
    for k, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k))
    verdict = "기각" if any(F.values()) else "보류(F3·F5 필요)"
    print("\n→ 판정: %s" % verdict)
    print("   (등록서 §6 예측 ①: 시총가중이 0 에 가까워 F1 에 걸릴 것 — %s)"
          % ("맞음" if F["F1 시총가중 세 기간 모두 양수 아님"] else "틀림"))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"prereg": "PREREG-2026-09-19-TAXSURP", "commit": "2300c7c",
         "n_pool": {"median": int(np.median(npa)), "min": int(npa.min()),
                    "max": int(npa.max()), "months": len(npa),
                    "below_threshold": int((npa < MIN_POOL).sum())},
         "weights": res, "taxyears": tw, "f6_gap": f6,
         "shuffle": {"n": NSHUF, "seed": SEED, "mean": float(sh_.mean()),
                     "sd": float(sh_.std(ddof=1)), "pctile": pct},
         "fails": {k: bool(v) for k, v in F.items()}, "verdict": verdict},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
