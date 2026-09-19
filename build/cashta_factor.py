# -*- coding: utf-8 -*-
"""cashta_factor.py — Cta 롱숏이 팩터로 설명되나 · 겹침 보정 t."""
import io, json, os, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
LAB = r"C:\Users\Win10\AppData\Local\Temp\claude\C--Users-Win10\b027d081-e8d2-4a85-b38e-bc0850b41a41\scratchpad\yeodoo-lab"

d = json.load(io.open(os.path.join(LAB, "data", "_cashta.json"), encoding="utf-8"))
s = d["main_series"]
ls = pd.Series(s["ls"], index=pd.PeriodIndex(s["months"], freq="M"))
print("주 판정판 월 롱숏 %d개월 (%s ~ %s) · 평균 %+.3f%%"
      % (len(ls), ls.index[0], ls.index[-1], ls.mean() * 100))

ff = json.load(io.open(os.path.join(LAB, "data", "ff_daily.json"), encoding="utf-8"))
F = pd.DataFrame(ff["series"], index=pd.to_datetime(ff["dates"])) / 100.0
M = (1 + F).groupby(F.index.to_period("M")).prod() - 1
df = pd.DataFrame({"ls": ls}).join(M, how="inner").dropna()
print("겹치는 달 %d개 (FF 는 %s 까지)\n" % (len(df), ff["end"]))

y = df.ls.to_numpy()
names = ["알파", "MKT", "SMB", "HML", "RMW", "CMA", "MOM"]
X = np.column_stack([np.ones(len(df))] + [df[c].to_numpy()
                                          for c in ("mkt_rf", "smb", "hml", "rmw", "cma", "mom")])
b, *_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X @ b
se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * (res @ res) / (len(y) - X.shape[1])))
print("■ 6팩터 회귀")
print("   %-6s %10s %8s" % ("", "계수", "t"))
for i, nm in enumerate(names):
    v = b[i] * (100 if i == 0 else 1)
    print("   %-6s %10.4f %8.2f%s" % (nm, v, b[i] / se[i], "  ← 월 %+.3f%%" % v if i == 0 else ""))
print("   R² %.3f" % (1 - res.var() / y.var()))

# 겹침 보정 t (Newey-West)
def nw(x, lag):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    m = len(x); dd = x - x.mean()
    var = float((dd * dd).sum() / m)
    for k in range(1, min(lag, m - 1) + 1):
        var += 2 * (1 - k / (lag + 1.0)) * float((dd[k:] * dd[:-k]).sum() / m)
    return float(x.mean() / np.sqrt(var / m))

print("\n■ 겹침 보정 — 원 t 와 Newey-West t")
raw = ls.mean() / (ls.std(ddof=1) / np.sqrt(len(ls)))
print("   보유 1개월 · 원 t %.2f · NW(6) %.2f · NW(12) %.2f"
      % (raw, nw(ls.to_numpy(), 6), nw(ls.to_numpy(), 12)))
print("   ⚠ 보유 6·12개월의 t 는 관측이 겹쳐 무효다 — cashta.py 가 단순 t 를 썼다.")

# 유효 표본 — 명단이 안 바뀌면 독립 관측이 적다
print("\n■ 유효 표본")
print("   월 교체율 6%% → 명단 반감기 약 %.0f개월" % (np.log(0.5) / np.log(1 - 0.06)))
print("   207개월 / 반감기 → 사실상 독립 구간 약 %.0f개" % (207 / (np.log(0.5) / np.log(1 - 0.06))))
