# -*- coding: utf-8 -*-
"""과적합 진단 5지표 중 **남은 둘** — OOS Percentile · IS-OOS Rank Corr.

QMind README(사용자 제공)의 [8] 5지표:
  Funnel Value-Add · OOS Percentile Tracking · Strict Jaccard ·
  IS-OOS Rank Correlation · Deflation Ratio
앞 셋은 build/qg_diag.py 에서 이미 쟀다. 여기서 뒤 둘을 잰다.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LAB, "build")); os.chdir(LAB)
import numpy as np, pandas as pd                                   # noqa: E402
import qg_cap as QC                                                # noqa: E402
from maxyears import cap as capidx                                 # noqa: E402

CAP = 20.0
q = pd.read_pickle(QC.SRC); QC.CIK = QC.cik_map()
idx = pd.read_pickle(QC.SRC_IX); ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
X = pd.read_csv(QC.DIV); idiv = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
ex, extra = QC.series(CAP)
_e, _t, _t3, sel = QC.run(q, ipr, idiv, cap=CAP)
ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}


def ym_add(y, k):
    t = int(y[:4]) * 12 + int(y[5:7]) - 1 + k
    return "%04d-%02d" % (t // 12, t % 12 + 1)


def spearman(a, b):
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    if len(ra) < 3 or np.std(ra) == 0 or np.std(rb) == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


# ── ④ IS-OOS Rank Correlation ────────────────────────────────────────────
# 형성 시점의 «평활점수» 순위 ↔ 다음 분기 실제 수익 순위. 선정된 30종 안에서,
# 그리고 채점된 전체 후보 안에서 각각 잰다.
print("══ ④ IS-OOS Rank Correlation — 점수 순위가 다음 분기 수익을 맞히나 ══")
rows = []
for f in sorted(sel):
    hold = [ym_add(f, k) for k in (1, 2, 3)]
    if not all(h <= max(q.ym) for h in hold):
        continue
    g = q[(q.ym == f) & q.score_sm.notna()]
    sc = dict(zip(g.tkr, g.score_sm))
    r3 = {}
    for t in sc:
        c, ok = 1.0, True
        for k in (1, 2, 3):
            r = ret.get(ym_add(f, k - 1), {}).get(t)
            if r is None:
                ok = False; break
            c *= (1 + r)
        if ok:
            r3[t] = c - 1
    common = [t for t in sc if t in r3]
    if len(common) < 30:
        continue
    all_rho = spearman([sc[t] for t in common], [r3[t] for t in common])
    top = [t for t in sel[f] if t in r3]
    top_rho = spearman([sc[t] for t in top], [r3[t] for t in top]) if len(top) >= 10 else np.nan
    rows.append((f, all_rho, top_rho, len(common), len(top)))

A = np.array([r[1] for r in rows], float)
Tp = np.array([r[2] for r in rows], float)
Tp = Tp[np.isfinite(Tp)]
print("   형성 %d회 · 후보 중앙 %d종" % (len(rows), int(np.median([r[3] for r in rows]))))
print("   전체 후보 안에서 — 중앙 %+.3f · 평균 %+.3f · 양수 비율 %.0f%%"
      % (np.median(A), A.mean(), (A > 0).mean() * 100))
print("   선정 30종 안에서 — 중앙 %+.3f · 평균 %+.3f · 양수 비율 %.0f%%"
      % (np.median(Tp), Tp.mean(), (Tp > 0).mean() * 100))
se = A.std(ddof=1) / np.sqrt(len(A))
print("   전체 후보 평균의 t = %.2f" % (A.mean() / se))
print("   ⚠ 0 에 가까우면 «점수는 30종을 골라 내지만 그 안의 순서는 못 맞힌다» 는 뜻이다.")

# ── ⑤ OOS Percentile Tracking ────────────────────────────────────────────
# 각 OOS 분기의 초과가, 그 시점까지의 IS 분포에서 몇 백분위인가.
print("\n══ ⑤ OOS Percentile Tracking — OOS 가 IS 분포의 어디에 떨어지나 ══")
v = ex.to_numpy(); ms = [str(p) for p in ex.index]
qv, qm = [], []
for i in range(0, len(v) - len(v) % 3, 3):
    qv.append(float(np.prod(1 + v[i:i + 3]) - 1) * 100)
    qm.append(ms[i])
qv = np.array(qv)
pcts = []
for i in range(8, len(qv)):                      # 앞 8분기(2년)를 IS 로 두고 시작
    hist = qv[:i]
    pcts.append((qv[i] > hist).mean() * 100)
P = np.array(pcts)
print("   분기 %d개 중 %d개를 추적(앞 8분기는 IS 기준선)" % (len(qv), len(P)))
print("   OOS 백분위 — 중앙 %.1f · 평균 %.1f (무작위면 50)" % (np.median(P), P.mean()))
print("   50 미만 비율 %.0f%% · 25 미만 %.0f%% · 75 초과 %.0f%%"
      % ((P < 50).mean() * 100, (P < 25).mean() * 100, (P > 75).mean() * 100))
h1, h2 = P[:len(P) // 2], P[len(P) // 2:]
print("   앞 절반 평균 %.1f → 뒤 절반 %.1f  (%s)"
      % (h1.mean(), h2.mean(), "내려간다 — 열화 신호" if h2.mean() < h1.mean() - 5 else "유지"))

out = {
    "rank_corr": {"n_form": len(rows), "all_median": float(np.median(A)),
                  "all_mean": float(A.mean()), "all_pos_pct": float((A > 0).mean() * 100),
                  "all_t": float(A.mean() / se),
                  "top_median": float(np.median(Tp)), "top_mean": float(Tp.mean()),
                  "top_pos_pct": float((Tp > 0).mean() * 100)},
    "oos_percentile": {"n": len(P), "median": float(np.median(P)), "mean": float(P.mean()),
                       "below50_pct": float((P < 50).mean() * 100),
                       "below25_pct": float((P < 25).mean() * 100),
                       "above75_pct": float((P > 75).mean() * 100),
                       "first_half": float(h1.mean()), "second_half": float(h2.mean())},
}
p = os.path.join(LAB, "data", "_qg_diag2.json")
io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("\n→ %s" % p)
