# -*- coding: utf-8 -*-
"""qg_2026.py — 보고서가 띄운 깃발을 본다. 2026년 부진이 설계 탓인가 국면 탓인가."""
import io, json, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yeodoo-lab")
sys.path.insert(0, os.path.join(LAB, "build"))
from quarterly_report import fund_monthly                         # noqa: E402

ex = fund_monthly()
ff = json.load(io.open(os.path.join(LAB, "data", "ff_daily.json"), encoding="utf-8"))
F = pd.DataFrame(ff["series"], index=pd.to_datetime(ff["dates"])) / 100.0
M = (1 + F).groupby(F.index.to_period("M")).prod() - 1
df = pd.DataFrame({"ex": ex}).join(M, how="inner").dropna()

print("■ 2026년 월별 초과수익 (%p)")
y26 = ex[[i for i in ex.index if i.year == 2026]]
for i, v in y26.items():
    print("   %s  %+7.2f" % (i, v * 100))
print("   합 %+.2f%%p · 월평균 %+.3f%%" % ((np.prod(1 + y26.to_numpy()) - 1) * 100,
                                          y26.mean() * 100))

print("\n■ 팩터 귀속 — 전 구간 베타로 2026 을 설명하면")
tr = df[df.index.year < 2026]
X = np.column_stack([np.ones(len(tr))] + [tr[c].to_numpy()
                                          for c in ("mkt_rf", "smb", "hml", "rmw", "cma", "mom")])
b, *_ = np.linalg.lstsq(X, tr.ex.to_numpy(), rcond=None)
names = ["알파", "MKT", "SMB", "HML", "RMW", "CMA", "MOM"]
print("   2025년까지 추정 베타: " + " · ".join("%s %+.3f" % (n, v)
                                          for n, v in zip(names[1:], b[1:])))
print("   그때 알파 월 %+.3f%% (연 %+.2f%%p)" % (b[0] * 100, b[0] * 1200))

cur = df[df.index.year == 2026]
if len(cur):
    pred = b[0] + sum(b[i + 1] * cur[c].to_numpy()
                      for i, c in enumerate(("mkt_rf", "smb", "hml", "rmw", "cma", "mom")))
    act = cur.ex.to_numpy()
    print("\n   %-9s %10s %10s %10s" % ("월", "실제", "모형 예측", "잔차"))
    for i, (m, a, p) in enumerate(zip(cur.index, act, pred)):
        print("   %-9s %+9.2f%% %+9.2f%% %+9.2f%%" % (m, a * 100, p * 100, (a - p) * 100))
    print("   %-9s %+9.2f%% %+9.2f%% %+9.2f%%" % ("평균", act.mean() * 100,
                                                  pred.mean() * 100, (act - pred).mean() * 100))
    resid = act - pred
    se = tr.ex.to_numpy() - X @ b
    t = resid.mean() / (se.std(ddof=1) / np.sqrt(len(resid)))
    print("\n   → 2026 잔차 월평균 %+.3f%% · t %.2f (과거 잔차 표준편차 기준)"
          % (resid.mean() * 100, t))
    if abs(t) < 2:
        print("      **팩터 노출로 설명되는 범위다. 설계가 깨졌다는 증거가 아니다.**")
    else:
        print("      ⚠ 팩터로 설명 안 된다 — 설계를 더 볼 자리다.")

print("\n■ 2026 팩터가 어땠나 (월평균 %)")
for c in ("mkt_rf", "smb", "hml", "rmw", "cma", "mom"):
    h = df[df.index.year < 2026][c].mean() * 100
    n = cur[c].mean() * 100 if len(cur) else float("nan")
    print("   %-7s 과거 %+6.3f  2026 %+6.3f  차 %+6.3f" % (c.upper(), h, n, n - h))
