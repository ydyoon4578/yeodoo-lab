# -*- coding: utf-8 -*-
"""점수 십분위 단조성 — «ρ≈0 인데 바스켓은 왜 이기나» 를 가른다."""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LAB, "build")); os.chdir(LAB)
import numpy as np, pandas as pd                                   # noqa: E402
import qg_cap as QC                                                # noqa: E402

q = pd.read_pickle(QC.SRC)
ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}


def ym_add(y, k):
    t = int(y[:4]) * 12 + int(y[5:7]) - 1 + k
    return "%04d-%02d" % (t // 12, t % 12 + 1)


forms = sorted({f for f in q.ym.unique() if int(f[5:7]) in (3, 6, 9, 12)})
D = {i: [] for i in range(10)}
TOP30, BOT30, UNI = [], [], []
for f in forms:
    g = q[(q.ym == f) & q.score_sm.notna()]
    if len(g) < 100:
        continue
    r3 = {}
    for t in g.tkr:                                # 생산코드와 같은 시점규칙: ret[f+k-1]
        c, ok = 1.0, True
        for k in (1, 2, 3):
            r = ret.get(ym_add(f, k - 1), {}).get(t)
            if r is None:
                ok = False; break
            c *= (1 + r)
        if ok:
            r3[t] = c - 1
    gg = g[g.tkr.isin(r3)].copy()
    if len(gg) < 100:
        continue
    gg["r3"] = [r3[t] for t in gg.tkr]
    gg = gg.sort_values("score_sm", ascending=False).reset_index(drop=True)
    n = len(gg)
    for i in range(10):
        a, b = int(n * i / 10), int(n * (i + 1) / 10)
        D[i].append(gg.r3.iloc[a:b].mean())
    TOP30.append(gg.r3.iloc[:30].mean())
    BOT30.append(gg.r3.iloc[-30:].mean())
    UNI.append(gg.r3.mean())

nq = len(UNI)
print("══ 점수 십분위 — 분기 %d회 · 동일가중 3개월 수익, 전체평균 대비 %%p ══" % nq)
u = np.mean(UNI) * 100
rows = []
for i in range(10):
    v = np.mean(D[i]) * 100
    t = np.mean(np.array(D[i]) - np.array(UNI)) / (np.std(np.array(D[i]) - np.array(UNI), ddof=1) / np.sqrt(nq))
    rows.append((i + 1, v, v - u, t))
    bar = "█" * max(0, int(round((v - u) * 6))) or ("·" if v - u >= 0 else "")
    neg = "▁" * max(0, int(round(-(v - u) * 6)))
    print("  %2d분위  %6.2f%%   %+5.2f%%p  t %+5.2f  %s%s"
          % (i + 1, v, v - u, t, neg, bar))
print("  ─────────────────────────────────────────")
print("  전체평균 %6.2f%%" % u)
print("  상위30   %6.2f%%   %+5.2f%%p   ← 실제 뽑는 칸" % (np.mean(TOP30) * 100, (np.mean(TOP30) - np.mean(UNI)) * 100))
print("  하위30   %6.2f%%   %+5.2f%%p" % (np.mean(BOT30) * 100, (np.mean(BOT30) - np.mean(UNI)) * 100))
sp = (np.array(D[0]) - np.array(D[9]))
print("\n  1분위−10분위 스프레드 평균 %+.2f%%p · t %.2f · 양수 비율 %.0f%%"
      % (sp.mean() * 100, sp.mean() / (sp.std(ddof=1) / np.sqrt(nq)), (sp > 0).mean() * 100))
mid = np.array([np.mean(D[i]) for i in range(2, 8)]) * 100
print("  3~8분위 폭 %.2f%%p (밋밋하면 «끝만 산다» 는 뜻)" % (mid.max() - mid.min()))

out = {"n_q": nq, "uni": u, "deciles": [{"d": a, "ret": b, "vs_uni": c, "t": d} for a, b, c, d in rows],
       "top30": np.mean(TOP30) * 100, "bot30": np.mean(BOT30) * 100,
       "spread_1_10": float(sp.mean() * 100), "spread_t": float(sp.mean() / (sp.std(ddof=1) / np.sqrt(nq))),
       "mid_range": float(mid.max() - mid.min())}
io.open(os.path.join(LAB, "data", "_qg_decile.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print("\n→ data/_qg_decile.json")
