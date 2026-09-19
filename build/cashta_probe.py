# -*- coding: utf-8 -*-
"""cashta_probe.py — CASHTA 가 너무 좋다. 무엇을 사고 있는지 본다."""
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
        c = cash.get(e)
        if c is None or not a or a <= 0:
            continue
        r = {"t": t, "end": e, "cta_low": c / a}
        s = sti.get(e)
        if s is not None:
            r["cta_full"] = (c + s) / a
            r["sti_share"] = s / (c + s) if (c + s) > 0 else np.nan
        rows.append(r)
D = pd.DataFrame(rows)
D["q"] = pd.PeriodIndex(pd.to_datetime(D.end), freq="Q")

print("■ ① sti 를 보고하는 회사는 누구인가")
mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
hasf = set(D.loc[D.cta_full.notna(), "t"])
import collections
print("   sti 있는 %d종 섹터: %s" % (len(hasf),
      " · ".join("%s %d" % x for x in collections.Counter(sect.get(t, "?") for t in hasf).most_common(5))))
print("   현금비율 중앙 — sti 있는 쪽 %.3f · 없는 쪽 %.3f"
      % (D[D.cta_full.notna()].cta_low.median(), D[D.cta_full.isna()].cta_low.median()))
print("   Cta-원문 중앙 %.3f vs Cta-하한(같은 회사) %.3f — 단기투자 몫 중앙 %.0f%%"
      % (D.cta_full.median(), D[D.cta_full.notna()].cta_low.median(),
         D.sti_share.median() * 100))

print("\n■ ② sti 보고 여부가 시간에 따라 변하나 (선견 위험)")
D["yr"] = D.q.dt.year
g = D.groupby("yr").apply(lambda x: pd.Series({
    "n": len(x), "n_full": int(x.cta_full.notna().sum()),
    "share": x.cta_full.notna().mean() * 100}))
print(g.tail(12).to_string())
print("   → 비율이 시간에 따라 크게 늘면 «나중에 보고하기 시작한 회사» 가 앞구간에 없다는 뜻이다.")

print("\n■ ③ 실제로 무엇을 사고 있나 — 최근 형성월 상위 10종")
st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
dates = st["pxd_dates"]
px = {}
for s in st["stocks"]:
    p = os.path.join(DATA, "sd", "%s.json" % s["t"])
    if os.path.exists(p):
        v = json.load(io.open(p, encoding="utf-8")).get("pxd")
        if isinstance(v, list) and len(v) == len(dates):
            px[s["t"]] = v
P = pd.DataFrame(px, index=pd.to_datetime(dates))
M = P.resample("M").last(); M.index = M.index.to_period("M")
D["avail"] = (D.q.dt.end_time + pd.DateOffset(months=4)).dt.to_period("M")
d = D[D.cta_full.notna()].copy()
d["sector"] = d.t.map(lambda x: sect.get(x, "?"))
d = d[d.sector != "Financials"]
cur = {}
hold_hist = []
for m in M.index:
    for _, r in d[d.avail == m].sort_values("q").drop_duplicates("t", keep="last").iterrows():
        cur[r.t] = (r.cta_full, r.sector)
    have = {t: v for t, v in cur.items() if t in M.columns and pd.notna(M.at[m, t])}
    if len(have) < 30:
        continue
    gg = pd.DataFrame([{"t": t, "v": v[0], "s": v[1]} for t, v in have.items()])
    gg["z"] = gg.groupby("s").v.transform(lambda s: (s - s.mean()) / (s.std(ddof=0) or 1))
    n = max(10, round(len(gg) / 10))
    hold_hist.append((m, list(gg.sort_values("z", ascending=False).t.head(n)),
                      list(gg.sort_values("z").t.head(n))))
print("   형성 %d개월 · 최근 3개" % len(hold_hist))
for m, hi, lo in hold_hist[-3:]:
    print("      %s  롱: %s" % (m, " ".join(hi[:12])))
    print("             숏: %s" % " ".join(lo[:12]))
allhi = collections.Counter(t for _, hi, _ in hold_hist for t in hi)
allo = collections.Counter(t for _, _, lo in hold_hist for t in lo)
print("   롱에 가장 자주 든 10종 (전체 %d개월 중):" % len(hold_hist))
print("      " + " · ".join("%s %d" % x for x in allhi.most_common(10)))
print("   숏에 가장 자주 든 10종:")
print("      " + " · ".join("%s %d" % x for x in allo.most_common(10)))
