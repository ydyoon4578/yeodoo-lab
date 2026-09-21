# -*- coding: utf-8 -*-
"""대조군 — 점수를 빼고 «크기»만 남기면 얼마가 남나.

🚨 이것은 **더 좋은 전략을 찾는 탐색이 아니다.** 손잡이를 돌려 성적을 올리려는 게 아니라,
   이미 발표한 +9.19%p 라는 «주장»이 대조군을 이기는지 보는 **진단**이다.
   대조군은 전부 같은 기계(분기형성·지수비중·상한20%·편도10bp·10년)를 쓴다.
   판정은 성적이 아니라 «주장이 서나» 로만 읽는다.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LAB, "build")); os.chdir(LAB)
import numpy as np, pandas as pd                                   # noqa: E402
import qg_cap as QC                                                # noqa: E402
from maxyears import cap as capidx                                 # noqa: E402

q = pd.read_pickle(QC.SRC); QC.CIK = QC.cik_map()
idx = pd.read_pickle(QC.SRC_IX); idx_pr = dict(zip(idx.ym, idx.ret_pct / 100.0))
X = pd.read_csv(QC.DIV); idx_div = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}
ym_add = QC.ym_add
FORMS = sorted({f for f in q.ym.unique() if int(f[5:7]) in (3, 6, 9, 12)})


def hold(sel):
    """선정 명단(회사단위 지수비중·상한20%)을 들고 간다 — qg_cap.run() 과 동일."""
    out, prev, turn, forms = {}, {}, {}, sorted(sel)
    W = {}
    for f in forms:
        pan = q[q.ym == f]
        comp = {}
        for tk, v in zip(pan.tkr, pan.idxw.astype(float)):
            c = QC.CIK.get(tk, tk)
            comp[c] = comp.get(c, 0.0) + (0.0 if pd.isna(v) else float(v))
        iw = {t: comp.get(QC.CIK.get(t, t), 0.0) for t in sel[f]}
        s = sum(iw.values())
        if s <= 0:
            continue
        W[f] = {t: v / 100.0 for t, v in
                QC.recap({t: v / s * 100.0 for t, v in iw.items()}, 20.0).items()}
    for f in sorted(W):
        w = W[f]
        trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
        ch = False
        for k in (1, 2, 3):
            hm = ym_add(f, k)
            if not (QC.HOLD0 <= hm <= QC.HOLD1):
                continue
            r = ret.get(ym_add(f, k - 1), {})
            ok = {t: v for t, v in w.items() if t in r}
            s = sum(ok.values())
            if s <= 0:
                continue
            g = sum(v / s * r[t] for t, v in ok.items())
            out[hm] = g - (trade * QC.COST_SIDE if not ch else 0.0)
            turn[hm] = trade if not ch else 0.0
            ch = True
            w = {t: (v / s) * (1 + r[t]) for t, v in ok.items()}
            z = sum(w.values()); w = {t: v / z for t, v in w.items()}
        prev = w
    ms = sorted(m for m in out if m in idx_pr and m in idx_div and pd.notna(idx_pr[m]))
    ex = pd.Series([out[m] - (idx_pr[m] + idx_div[m]) for m in ms],
                   index=pd.PeriodIndex(ms, freq="M"), dtype="float64")
    ex = ex.reindex(capidx(ex.index))
    st = QC.stats(ex)
    st["turn"] = sum(turn[m] for m in ms) / (len(ms) / 12.0) / 2 * 100
    return st, ex


def pick(fn, n=30):
    s = {}
    for f in FORMS:
        g = q[q.ym == f]
        t = fn(g, n)
        if len(t) >= 10:
            s[f] = list(t)
    return s


# ── 대조군 ───────────────────────────────────────────────────────────────
cur = pick(lambda g, n: g[g.top30 == "Y"].tkr)
siz = pick(lambda g, n: g.dropna(subset=["idxw"]).nlargest(n, "idxw").tkr)
# 시총 상위 100 안에서만 점수로 고르기 — 점수가 «크기 위에» 무엇을 더하나
s100 = pick(lambda g, n: g.dropna(subset=["idxw", "score_sm"])
            .nlargest(100, "idxw").nlargest(n, "score_sm").tkr)
# 시총 상위 100 안에서 점수 «하위» 30 — 점수가 거꾸로면 여기가 더 좋다
s100b = pick(lambda g, n: g.dropna(subset=["idxw", "score_sm"])
             .nlargest(100, "idxw").nsmallest(n, "score_sm").tkr)

R = {}
for nm, s in [("① 현행 — 점수 상위 30", cur),
              ("② 시총 상위 30 (점수 없음)", siz),
              ("③ 시총100 중 점수 상위 30", s100),
              ("④ 시총100 중 점수 하위 30", s100b)]:
    R[nm], _ = hold(s)

print("══ 대조군 — 전부 같은 기계(분기·지수비중·상한20%·편도10bp·10년) ══")
print("  %-26s %9s %6s %6s %7s %7s" % ("명단", "연초과%p", "IR", "t", "TE%", "회전%"))
for k, v in R.items():
    print("  %-26s %+9.2f %6.2f %6.2f %7.1f %7.0f"
          % (k, v["excess_y_pp"], v["ir"], v["t"], v["te_y_pct"], v["turn"]))

# 겹침 — 현행 30 중 몇 개가 시총 상위 30 인가
ov = [len(set(cur[f]) & set(siz[f])) for f in cur if f in siz]
ov100 = [len(set(cur[f]) & set(s100[f])) for f in cur if f in s100]
print("\n  현행 30 ∩ 시총 상위 30  — 중앙 %.0f종 (%.0f%%)" % (np.median(ov), np.median(ov) / 30 * 100))
print("  현행 30 ∩ 시총100·점수30 — 중앙 %.0f종" % np.median(ov100))

a = R["① 현행 — 점수 상위 30"]["excess_y_pp"]
b = R["② 시총 상위 30 (점수 없음)"]["excess_y_pp"]
print("\n  ① − ②  점수가 «크기» 위에 더하는 몫  %+.2f%%p" % (a - b))
d = R["③ 시총100 중 점수 상위 30"]["excess_y_pp"] - R["④ 시총100 중 점수 하위 30"]["excess_y_pp"]
print("  ③ − ④  크기를 묶어 놓고 본 점수의 힘  %+.2f%%p" % d)

io.open(os.path.join(LAB, "data", "_qg_control.json"), "w", encoding="utf-8").write(
    json.dumps({"rows": R, "overlap_size30_median": float(np.median(ov)),
                "vs_size_pp": a - b, "score_within_size_pp": d}, ensure_ascii=False, indent=1))
print("\n→ data/_qg_control.json")
