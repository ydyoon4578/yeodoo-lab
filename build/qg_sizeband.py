# -*- coding: utf-8 -*-
"""가설 — «점수는 대형주에서만 듣는다». 크기 구간을 나눠 같은 십분위 시험을 반복한다.
   동일가중이므로 가중 효과가 섞이지 않는다.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LAB, "build")); os.chdir(LAB)
import numpy as np, pandas as pd                                   # noqa: E402
import qg_cap as QC                                                # noqa: E402

q = pd.read_pickle(QC.SRC)
ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}
ym_add = QC.ym_add
FORMS = sorted({f for f in q.ym.unique() if int(f[5:7]) in (3, 6, 9, 12)})


def fwd3(f, tkrs):
    o = {}
    for t in tkrs:
        c, ok = 1.0, True
        for k in (1, 2, 3):
            r = ret.get(ym_add(f, k - 1), {}).get(t)
            if r is None:
                ok = False; break
            c *= (1 + r)
        if ok:
            o[t] = c - 1
    return o


def band(lo, hi, label):
    """시총 순위 lo~hi 구간 안에서 점수 상위30 − 하위30 (동일가중)."""
    sp, hi_, lo_ = [], [], []
    for f in FORMS:
        g = q[(q.ym == f)].dropna(subset=["idxw", "score_sm"])
        g = g.sort_values("idxw", ascending=False).iloc[lo:hi]
        if len(g) < 80:
            continue
        r3 = fwd3(f, g.tkr)
        g = g[g.tkr.isin(r3)].copy()
        if len(g) < 80:
            continue
        g["r3"] = [r3[t] for t in g.tkr]
        g = g.sort_values("score_sm", ascending=False)
        a, b = g.r3.iloc[:30].mean(), g.r3.iloc[-30:].mean()
        sp.append(a - b); hi_.append(a); lo_.append(b)
    sp = np.array(sp)
    t = sp.mean() / (sp.std(ddof=1) / np.sqrt(len(sp)))
    print("  %-22s  상위30 %6.2f%%  하위30 %6.2f%%  차 %+6.2f%%p  t %+5.2f  분기 %d"
          % (label, np.mean(hi_) * 100, np.mean(lo_) * 100, sp.mean() * 100, t, len(sp)))
    return {"label": label, "hi": float(np.mean(hi_) * 100), "lo": float(np.mean(lo_) * 100),
            "spread_pp": float(sp.mean() * 100), "t": float(t), "n": len(sp)}


print("══ 점수의 힘을 «크기 구간»별로 — 동일가중 3개월, 가중효과 없음 ══")
B = [band(0, 100, "시총 1~100위"), band(100, 250, "시총 101~250위"),
     band(250, 600, "시총 251위~"), band(0, 600, "전체")]

# ③ − ④ 차이계열의 t (대조군 스크립트의 두 다리를 직접 뺀다)
print("\n══ ③−④ 차이계열 — 지수비중·상한20% 판에서 ══")
J = json.load(io.open(os.path.join(LAB, "data", "_qg_control.json"), encoding="utf-8"))
print("  ③ %+.2f%%p (t %.2f) · ④ %+.2f%%p (t %.2f) · 차 %+.2f%%p"
      % (J["rows"]["③ 시총100 중 점수 상위 30"]["excess_y_pp"],
         J["rows"]["③ 시총100 중 점수 상위 30"]["t"],
         J["rows"]["④ 시총100 중 점수 하위 30"]["excess_y_pp"],
         J["rows"]["④ 시총100 중 점수 하위 30"]["t"], J["score_within_size_pp"]))

io.open(os.path.join(LAB, "data", "_qg_sizeband.json"), "w", encoding="utf-8").write(
    json.dumps(B, ensure_ascii=False, indent=1))
print("\n→ data/_qg_sizeband.json")
