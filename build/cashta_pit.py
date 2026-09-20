# -*- coding: utf-8 -*-
"""cashta_pit.py — CASHTA 를 시점정확 멤버십으로 다시 잰다.

🚨 등록서에 PIT 다리를 안 넣었다. ORGCAP 이 바로 거기서 +7.66 → −2.65 로 무너졌다.
   롱 명단이 RKLB·PLTR·RDDT·ALAB 처럼 최근 상장·최근 편입 종목이라 의심이 든다.
"""
import glob, io, json, os, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
LAB = r"C:\Users\Win10\AppData\Local\Temp\claude\C--Users-Win10\b027d081-e8d2-4a85-b38e-bc0850b41a41\scratchpad\yeodoo-lab"
DATA = os.path.join(LAB, "data")


def qser(j, k):
    tg = (j.get("tags") or {}).get(k) or {}
    return {e: float(v) for e, v, *_ in (tg.get("i") or tg.get("q") or tg.get("a") or [])}


base, ext = {}, {}
for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
    j = json.load(io.open(p, encoding="utf-8")); base[j["t"]] = j
for d in ("fxe", "fxe_pit"):
    for p in glob.glob(os.path.join(DATA, d, "*.json")):
        j = json.load(io.open(p, encoding="utf-8")); ext[j["t"]] = j

rows = []
for t, b in base.items():
    cash, at = qser(b, "cash"), qser(b, "asset")
    sti = qser(ext.get(t, {}), "sti")
    for e, a in at.items():
        c, s = cash.get(e), sti.get(e)
        if c is None or s is None or not a or a <= 0:
            continue
        rows.append({"t": t, "end": e, "cta": (c + s) / a})
D = pd.DataFrame(rows)
D["q"] = pd.PeriodIndex(pd.to_datetime(D.end), freq="Q")
D["avail"] = (D.q.dt.end_time + pd.DateOffset(months=4)).dt.to_period("M")
mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
D["sector"] = D.t.map(lambda x: sect.get(x, "?"))
D = D[D.sector != "Financials"]

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
# 🚨 주식수에 100만 배 단위 사고가 있다(build/audit_shares.py · 점프 238건/78종).
#   고치지 않으면 2026-06 에 WAT 가 지수의 29.5% 가 된다. 자릿수만 맞춘다.
from shares_clean import cap_frame                            # noqa: E402
CAP = cap_frame(M, DATA)

hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
months = hist["months"]


def run(pit_mode):
    cur, ls, pool, mos = {}, [], [], []
    by = {m: g.sort_values("q").drop_duplicates("t", keep="last")
          for m, g in D.groupby("avail")}
    for m in M.index:
        if m in by:
            for _, r in by[m].iterrows():
                cur[r.t] = (r.cta, r.sector)
        have = {t: v for t, v in cur.items() if t in M.columns and pd.notna(M.at[m, t])}
        if pit_mode:
            v = months.get(str(m)) or {}
            mm = set(v.get("spx") or []) | set(v.get("ndx") or [])
            have = {t: x for t, x in have.items() if t in mm} if mm else {}
        pool.append(len(have))
        if len(have) < 30:
            continue
        g = pd.DataFrame([{"t": t, "v": x[0], "s": x[1]} for t, x in have.items()])
        g["z"] = g.groupby("s").v.transform(lambda s: (s - s.mean()) / (s.std(ddof=0) or 1))
        n = max(10, int(round(len(g) / 10)))
        hi = list(g.sort_values("z", ascending=False).t.head(n))
        lo = list(g.sort_values("z").t.head(n))
        nx = [x for x in M.index if x > m][:1]
        if not nx:
            break

        def ret(names):
            w = CAP.loc[m, names].astype(float)
            w = w / w.sum() if np.isfinite(w).all() and w.sum() > 0 else \
                pd.Series(1.0 / len(names), index=names)
            return float((w * MR.loc[nx[0], names].astype(float).fillna(0)).sum())
        ls.append(ret(hi) - ret(lo)); mos.append(str(m))
    return np.array(ls), np.array(pool), mos


for tag, pm in (("소급(오늘 패널)", False), ("시점정확(그때 편입명단)", True)):
    a, pl, mo = run(pm)
    if len(a) < 10:
        print("■ %-20s 관측 %d — 측정 불가" % (tag, len(a))); continue
    t = a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))
    print("■ %-20s 월 %+.3f%% · t %.2f · 관측 %d개월 · 후보 중앙 %d종 (%s ~ %s)"
          % (tag, a.mean() * 100, t, len(a), int(np.median(pl[pl > 0])), mo[0], mo[-1]))
