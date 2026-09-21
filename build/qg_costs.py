# -*- coding: utf-8 -*-
"""build/qg_costs.py — 「설계를 바꾸면 드는 비용」을 **현행 판**으로 다시 잰다.

왜 — 카드의 네 줄이 서로 다른 창·상한에서 잰 값이었는데 한 표에 있었다.
  사용자 지시 2026-09-21: *"costs·국면표를 20% 판으로 다시 재기 … 다 반영해. 무비용으로 해"*

🚨 «무비용» 을 두 가지로 읽을 수 있어 **둘 다** 낸다:
   ⒜ 거래비용 있음(**편도 10bp** — 살 때 10 · 팔 때 10) — 카드가 쓰는 값
   ⒝ 거래비용 없음 — **설계 효과만** 본다. 회전이 달라지는 변형(매월 리밸런스)에서
     «신호가 나빠진 것» 과 «거래를 더 한 것» 이 섞이는 것을 가른다.

🚨 **네 줄 중 둘만 여기서 다시 잴 수 있다.** 나머지 둘은 이 클론에 입력이 없다:
   QGMAX  복권형(MAX5) 배제 — 일별 수익이 필요하다. qg_monthly.pkl 은 월말 값뿐이다.
   qg_max 한 계열 상한 60% — 「계열」의 정의가 원 등록서(§10)에 있고 그 산출이 여기 없다.
   ⚠ 두 값은 **얼린 값으로 두고, 어느 창·어느 상한에서 잰 것인지 카드에 적는다.**
     둘 다 **20% 상한**에서 쟀다(결과문서의 «확정안 재현 +8.16%p · IR 0.987» 이 그 증거다).
     창은 146개월이라 지금 카드(120개월)와 다르다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_qg_costs.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
import qg_cap as QC                                                # noqa: E402
from maxyears import MAX_YEARS, cap as capidx                      # noqa: E402

CAP = 20.0                    # 현행 상한(2026-09-21)
FORM_Q = (3, 6, 9, 12)


def run(q, ipr, idiv, cap, months, cost):
    """months = 형성월 집합(분기 또는 매월) · cost = **편도** 비용률(0 이면 무비용)."""
    sel, forms = {}, []
    for f, g in q[q.top30 == "Y"].groupby("ym"):
        if months is not None and int(f[5:7]) not in months:
            continue
        pan = q[q.ym == f]
        comp = {}
        for tk, v in zip(pan.tkr, pan.idxw.astype(float)):
            c = QC.CIK.get(tk, tk)
            comp[c] = comp.get(c, 0.0) + (0.0 if pd.isna(v) else float(v))
        iw = {t: comp.get(QC.CIK.get(t, t), 0.0) for t in g.tkr}
        s = sum(iw.values())
        if s <= 0:
            continue
        w = QC.recap({t: v / s * 100.0 for t, v in iw.items()}, cap)
        sel[f] = {t: v / 100.0 for t, v in w.items()}
        forms.append(f)
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}
    hold = 3 if months is not None else 1
    out, prev, turn = {}, {}, 0.0
    for f in sorted(forms):
        w = sel[f]
        trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
        turn += trade
        ch = False
        for k in range(1, hold + 1):
            hm = QC.ym_add(f, k)
            r = ret.get(QC.ym_add(f, k - 1), {})
            ok = {t: v for t, v in w.items() if t in r}
            s = sum(ok.values())
            if s <= 0:
                continue
            g = sum(v / s * r[t] for t, v in ok.items())
            out[hm] = g - (trade * cost if not ch else 0.0)
            ch = True
            w = {t: (v / s) * (1 + r[t]) for t, v in ok.items()}
            z = sum(w.values()); w = {t: v / z for t, v in w.items()}
        prev = w
    ms = sorted(m for m in out if m in ipr and m in idiv and pd.notna(ipr[m]))
    ex = pd.Series([out[m] - (ipr[m] + idiv[m]) for m in ms],
                   index=pd.PeriodIndex(ms, freq="M"), dtype="float64")
    ex = ex.reindex(capidx(ex.index))                    # 🚨 10년 상한
    yrs = len(ex) / 12.0
    return ex, (turn / yrs / 2 * 100)


def st(ex):
    n = len(ex); a = float(ex.mean()) * 1200
    te = float(ex.std(ddof=1)) * np.sqrt(12) * 100
    return {"n": n, "ann": a, "te": te, "ir": a / te if te else None,
            "t": float(ex.mean() / (ex.std(ddof=1) / np.sqrt(n)))}


def main():
    q = pd.read_pickle(QC.SRC); QC.CIK = QC.cik_map()
    idx = pd.read_pickle(QC.SRC_IX)
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(QC.DIV)
    idiv = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))

    res = {"cap_pct": CAP, "max_years": MAX_YEARS,
           "note": "「바꾸면 드는 비용」 재측정. 비용 있음/없음 두 판.", "runs": {}}
    print("── 상한 %g%% · %d년 창 ──" % (CAP, MAX_YEARS))
    print("%-22s %8s %7s %7s %7s %9s" % ("", "연초과%p", "TE%", "IR", "t", "연회전%"))
    base = {}
    for cost, lab in ((QC.COST_SIDE, "비용 %gbp(편도)" % (QC.COST_SIDE*1e4)), (0.0, "무비용")):
        exq, tq = run(q, ipr, idiv, CAP, FORM_Q, cost)
        exm, tm = run(q, ipr, idiv, CAP, None, cost)
        a, b = st(exq), st(exm)
        base[lab] = a
        res["runs"][lab] = {"quarterly": dict(a, turn=tq), "monthly": dict(b, turn=tm),
                            "delta_ann": b["ann"] - a["ann"]}
        print("  [%s]" % lab)
        print("   %-20s %+8.2f %7.2f %7.2f %7.2f %9.1f"
              % ("분기 형성(현행)", a["ann"], a["te"], a["ir"], a["t"], tq))
        print("   %-20s %+8.2f %7.2f %7.2f %7.2f %9.1f   차 %+.2f%%p"
              % ("매월 형성", b["ann"], b["te"], b["ir"], b["t"], tm, b["ann"] - a["ann"]))
    _CK = "비용 %gbp(편도)" % (QC.COST_SIDE*1e4)
    d_cost = res["runs"][_CK]["delta_ann"]
    d_free = res["runs"]["무비용"]["delta_ann"]
    print("\n  매월 리밸런스의 «비용» 분해")
    print("   비용 포함 차 %+.2f%%p  =  설계 효과 %+.2f  +  거래비용 %+.2f"
          % (d_cost, d_free, d_cost - d_free))
    res["monthly_decomp"] = {"total": d_cost, "design": d_free, "trading": d_cost - d_free}
    res["not_remeasured"] = {
        "QGMAX": "복권형(MAX5) 배제 — 일별 수익 필요. 얼린 값 −0.80%p/년 · 20% 상한 · 146개월",
        "qg_max": "한 계열 상한 60% — 「계열」 정의가 이 클론에 없다. 얼린 값 −1.64%p/년 · 20% 상한 · 146개월",
        "QGDELAY": "신규 편입 1개월 지연 — build/qg_delay.py 가 있으나 얼린 사전등록이라 "
                   "다시 돌리지 않는다. 얼린 값 −0.26%p/년 · 20% 상한 · 146개월",
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
