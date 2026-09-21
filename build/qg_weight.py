# -*- coding: utf-8 -*-
"""선정 vs 가중 분해 — 같은 30종을 동일가중으로 들면 얼마가 남나.

🚨 잣대는 **생산코드 그대로** 쓴다. qg_cap.run() 을 복사하되 «가중 한 줄»만 바꾸고
   초과·연율·IR·t 는 qg_cap.stats() 를 그대로 부른다. 내가 다시 짜면 틀린다
   (실제로 한 번 틀렸다 — idx_div 는 이미 월 소수이고, 초과 연율은 산술 ×12 다).
앵커 — '지수비중 상한 20%' 판이 qg_cap.series(20.0) 과 소수점까지 같아야 한다.
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


def run_w(mode, cap=None):
    sel, forms = {}, []
    for f, g in q[q.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) not in (3, 6, 9, 12):
            continue
        if mode == "ew":
            w = {t: 1.0 / len(g) for t in g.tkr}
        else:
            pan = q[q.ym == f]
            comp = {}
            for tk, v in zip(pan.tkr, pan.idxw.astype(float)):
                c = QC.CIK.get(tk, tk)
                comp[c] = comp.get(c, 0.0) + (0.0 if pd.isna(v) else float(v))
            iw = {t: comp.get(QC.CIK.get(t, t), 0.0) for t in g.tkr}
            s = sum(iw.values())
            if s <= 0:
                continue
            w = {t: v / 100.0 for t, v in
                 QC.recap({t: v / s * 100.0 for t, v in iw.items()}, cap).items()}
        sel[f] = w; forms.append(f)
    # ↓ 여기부터 끝까지 qg_cap.run() 과 한 글자도 다르지 않다.
    out, prev, turn = {}, {}, {}
    for f in sorted(forms):
        w = sel[f]
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
    tn = sum(turn[m] for m in ms) / (len(ms) / 12.0) / 2 * 100
    ex = ex.reindex(capidx(ex.index))
    st = QC.stats(ex)
    eff = float(np.median([1.0 / ((np.array(list(sel[f].values())) /
                                   sum(sel[f].values())) ** 2).sum() for f in sorted(sel)]))
    st["turn"] = tn; st["eff"] = eff
    return st, ex


A20, exA = run_w("idx", 20.0)
NOC, _ = run_w("idx", 100.0)
EW, _ = run_w("ew")

# ── 앵커 ────────────────────────────────────────────────────────────────
ref, _x = QC.series(20.0)
d = float((exA - ref.reindex(exA.index)).abs().max())
print("앵커 — 지수비중 20%% 판 vs qg_cap.series(20.0) 최대 차 %.2e" % d)
assert d < 1e-9, "앵커 실패 — 재현이 생산코드와 다르다"
print("       qg_cap.stats(series(20)) 연초과 %+.2f%%p / 내 재현 %+.2f%%p\n"
      % (QC.stats(ref)["excess_y_pp"], A20["excess_y_pp"]))

print("══ 같은 30종 · 같은 시점규칙 · 같은 편도 10bp — 가중만 바꾼다 ══")
print("  %-26s %9s %6s %6s %7s %7s %8s"
      % ("가중", "연초과%p", "IR", "t", "TE%", "회전%", "유효종목"))
for k, v in [("지수비중 · 상한 20% (현행)", A20), ("지수비중 · 상한 없음", NOC),
             ("동일가중 (3.33% 씩)", EW)]:
    print("  %-26s %+9.2f %6.2f %6.2f %7.1f %7.0f %8.1f"
          % (k, v["excess_y_pp"], v["ir"], v["t"], v["te_y_pct"], v["turn"], v["eff"]))

a, b = A20["excess_y_pp"], EW["excess_y_pp"]
print("\n  선정이 버는 몫  (동일가중)      %+.2f%%p   t %.2f" % (b, EW["t"]))
print("  가중이 더 얹는 몫              %+.2f%%p" % (a - b))
print("  ───────────────────────────────────────")
print("  합계 (현행)                    %+.2f%%p   t %.2f" % (a, A20["t"]))
print("\n  → 초과의 %.0f%% 가 «어느 30종을 고르나» 가 아니라"
      " «그 안에서 누구에게 몰아주나» 에서 온다." % ((a - b) / a * 100))

io.open(os.path.join(LAB, "data", "_qg_weight.json"), "w", encoding="utf-8").write(
    json.dumps({"cap20": A20, "uncapped": NOC, "equal": EW,
                "sel_share_pp": b, "wgt_share_pp": a - b,
                "wgt_share_pct": (a - b) / a * 100}, ensure_ascii=False, indent=1))
print("\n→ data/_qg_weight.json")
