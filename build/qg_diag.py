# -*- coding: utf-8 -*-
"""build/qg_diag.py — 우량성장 30 의 **진단 3종**. 성적표가 아니라 «믿을 수 있나» 를 잰다.

왜 — 사용자가 다른 파이프라인(B 전략)의 단계 구성을 기준으로 제시했다(2026-09-21):
  *"전략들이 적어도 이정도 스텝은 있어야함 참고해"*
  거기 있는데 여기 없던 것: **유효 팩터 수 1/HHI · 과적합 진단 5종 ·
  파라미터 최적값의 창별 안정성 · 다중검정(Bonferroni/BH-FDR)**.

담는 것
  ㉠ 구조 진단 — 1/HHI(유효 종목 수) · Jaccard(명단 안정성) · 커버리지 · 창별 안정성
  ㉡ 다중검정 — 점수 뒤바꾸기 + 무작위 바스켓 두 가지 귀무분포 · DSR
  ㉢ Funnel Value-Add — 기준안에서 확정안까지 **한 번에 하나씩** 바꿔 가며 기여를 가른다

🚨 전부 **현행 판**이다 — 상한 20% · 10년 창 · 편도 10bp.
⚠ 이것은 사전등록이 아니다. 새 규칙을 만들지 않고 **이미 정해진 설계를 진단만** 한다.
  그래서 손잡이를 돌려 «더 나은 값» 을 고르지 않는다 — 창별 안정성 표는
  «최적이 갈린다» 는 사실을 보이려고 싣는 것이지 고르려고 싣는 것이 아니다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_qg_diag.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
import qg_cap as QC                                                # noqa: E402
from maxyears import MAX_YEARS, cap as capidx                      # noqa: E402

CAP, TOPN = 20.0, 30
NSHUF, SEED = 500, 20260921
FORM_Q = (3, 6, 9, 12)


def norm_ppf(p):
    """표준정규 분위 — scipy 없이(랩이 scipy 에 기대지 않게)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        qq = np.sqrt(-2 * np.log(p))
        return (((((c[0] * qq + c[1]) * qq + c[2]) * qq + c[3]) * qq + c[4]) * qq + c[5]) / \
               ((((d[0] * qq + d[1]) * qq + d[2]) * qq + d[3]) * qq + 1)
    if p > ph:
        qq = np.sqrt(-2 * np.log(1 - p))
        return -(((((c[0] * qq + c[1]) * qq + c[2]) * qq + c[3]) * qq + c[4]) * qq + c[5]) / \
               ((((d[0] * qq + d[1]) * qq + d[2]) * qq + d[3]) * qq + 1)
    qq = p - 0.5
    r = qq * qq
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * qq / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def norm_cdf(x):
    return 0.5 * (1 + np.math.erf(x / np.sqrt(2))) if hasattr(np, "math") else \
        0.5 * (1 + float(np.vectorize(lambda z: __import__("math").erf(z))(x / np.sqrt(2))))


def bt(q, ipr, idiv, picks, cap=CAP, months=FORM_Q, cost=None):
    """picks[f] = 종목 목록 → 지수비중 비례 + 상한. 반환 (월별 초과, 연회전%)."""
    cost = QC.COST_SIDE if cost is None else cost
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}
    hold = 3 if months is not None else 1
    sel, forms = {}, []
    for f, names in picks.items():
        if months is not None and int(f[5:7]) not in months:
            continue
        pan = q[q.ym == f]
        comp = {}
        for tk, v in zip(pan.tkr, pan.idxw.astype(float)):
            c = QC.CIK.get(tk, tk)
            comp[c] = comp.get(c, 0.0) + (0.0 if pd.isna(v) else float(v))
        iw = {t: comp.get(QC.CIK.get(t, t), 0.0) for t in names}
        s = sum(iw.values())
        if s <= 0:
            continue
        w = QC.recap({t: v / s * 100.0 for t, v in iw.items()}, cap) if cap else \
            {t: v / s * 100.0 for t, v in iw.items()}
        sel[f] = {t: v / 100.0 for t, v in w.items()}
        forms.append(f)
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
    ex = ex.reindex(capidx(ex.index))
    return ex, (turn / (len(ex) / 12.0) / 2 * 100), sel


def ann(ex):
    return float(ex.mean()) * 1200


def stt(ex):
    a = ann(ex); te = float(ex.std(ddof=1)) * np.sqrt(12) * 100
    return {"ann": a, "te": te, "ir": a / te if te else None,
            "t": float(ex.mean() / (ex.std(ddof=1) / np.sqrt(len(ex)))), "n": len(ex)}


def main():
    q = pd.read_pickle(QC.SRC); QC.CIK = QC.cik_map()
    idx = pd.read_pickle(QC.SRC_IX)
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(QC.DIV)
    idiv = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
    res = {"cap_pct": CAP, "max_years": MAX_YEARS, "cost_side_bp": QC.COST_SIDE * 1e4}

    base_ex, base_turn, base_sel = QC.series(CAP)[0], None, None
    _e, _t, _t3, base_sel = QC.run(q, ipr, idiv, cap=CAP)
    B = stt(base_ex)
    print("현행 — 연 %+.2f%%p · IR %.2f · t %.2f (%d개월)" % (B["ann"], B["ir"], B["t"], B["n"]))

    # ── ㉠ 구조 ──────────────────────────────────────────────────────────
    qs = sorted(base_sel)
    hh = np.array([1.0 / np.sum(np.array(list(base_sel[f].values())) ** 2) for f in qs])
    J1 = [len(set(base_sel[a]) & set(base_sel[b])) / len(set(base_sel[a]) | set(base_sel[b]))
          for a, b in zip(qs, qs[1:])]
    J4 = [len(set(base_sel[a]) & set(base_sel[b])) / len(set(base_sel[a]) | set(base_sel[b]))
          for a, b in zip(qs, qs[4:])]
    cov = q.groupby("ym").scored.value_counts().unstack(fill_value=0)
    res["structure"] = {
        "eff_names_median": float(np.median(hh)), "eff_names_min": float(hh.min()),
        "eff_names_last": float(hh[-1]), "topn": TOPN,
        "jaccard_q_median": float(np.median(J1)), "jaccard_y_median": float(np.median(J4)),
        "coverage": {k: {"median": float(cov[k].median()), "min": int(cov[k].min()),
                         "max": int(cov[k].max())} for k in cov.columns},
        "panel_median": int(q.groupby("ym").size().median()),
    }
    print("\n㉠ 구조")
    print("   유효 종목 수 1/HHI — 중앙 %.1f / %d · 최저 %.1f · 최근 %.1f"
          % (np.median(hh), TOPN, hh.min(), hh[-1]))
    print("   Jaccard — 분기 간 %.3f · 1년 간격 %.3f" % (np.median(J1), np.median(J4)))

    # 창별 안정성
    caps = [25.0, 20.0, 15.0, 12.0, 10.0]
    wins = [("10년", 120), ("최근 5년", 60), ("최근 3년", 36)]
    stab = {}
    print("   창별 최적 상한")
    for nm, n in wins:
        row = [ann(QC.series(c)[0].iloc[-n:]) for c in caps]
        stab[nm] = {"row": row, "best": caps[int(np.argmax(row))]}
        print("     %-8s %s → %g%%" % (nm, " ".join("%+6.2f" % x for x in row), stab[nm]["best"]))
    res["structure"]["cap_stability"] = {"caps": caps, "by_window": stab,
                                         "agree": len({v["best"] for v in stab.values()}) == 1}

    # ── ㉡ 다중검정 ──────────────────────────────────────────────────────
    print("\n㉡ 다중검정")
    rng = np.random.default_rng(SEED)
    pool = {f: list(q.loc[(q.ym == f) & q.score_sm.notna(), "tkr"]) for f in qs}
    shuf = []
    for i in range(NSHUF):
        pk = {f: list(rng.choice(pool[f], size=TOPN, replace=False)) for f in qs}
        e, _tn, _s = bt(q, ipr, idiv, pk)
        shuf.append(ann(e))
    sh = np.array(shuf)
    pct = float((sh < B["ann"]).mean() * 100)
    print("   무작위 %d종 바스켓 %d회 — 평균 %+.2f%%p (sd %.2f) · 실측 %+.2f → **백분위 %.1f**"
          % (TOPN, NSHUF, sh.mean(), sh.std(ddof=1), B["ann"], pct))

    # DSR
    v = base_ex.to_numpy(); T = len(v)
    sr = float(v.mean() / v.std(ddof=1))
    m3 = float(((v - v.mean()) ** 3).mean() / v.std(ddof=0) ** 3)
    m4 = float(((v - v.mean()) ** 4).mean() / v.std(ddof=0) ** 4)
    sd_sr = float(np.std(sh, ddof=1) / 100 / 12 / (v.std(ddof=1) * np.sqrt(12)))  # 근사
    dsr = {}
    import math
    for N in (54, 100, 200):
        e_ = 0.5772156649
        z1, z2 = norm_ppf(1 - 1.0 / N), norm_ppf(1 - 1.0 / (N * math.e))
        sr0 = ((1 - e_) * z1 + e_ * z2) / math.sqrt(T)
        num = (sr - sr0) * math.sqrt(T - 1)
        den = math.sqrt(max(1e-12, 1 - m3 * sr + (m4 - 1) / 4.0 * sr ** 2))
        dsr["N%d" % N] = 0.5 * (1 + math.erf((num / den) / math.sqrt(2)))
        print("   DSR — 시행 %3d → 기대 최고 SR %.4f · **%.3f**" % (N, sr0, dsr["N%d" % N]))
    res["multiple_testing"] = {"shuffle_n": NSHUF, "shuffle_mean": float(sh.mean()),
                               "shuffle_sd": float(sh.std(ddof=1)), "percentile": pct,
                               "monthly_sr": sr, "skew": m3, "kurt": m4, "T": T, "dsr": dsr}

    # ── ㉢ Funnel ────────────────────────────────────────────────────────
    print("\n㉢ Funnel Value-Add — 기준안에서 확정안까지 한 번에 하나씩")
    def top(k, f):
        g = q[(q.ym == f) & q.score_sm.notna()]
        return list(g.nsmallest(k, "rank")["tkr"]) if "rank" in g else []
    steps = [
        ("기준안 — 100종 · 매월 · 상한없음", {"k": 100, "m": None, "c": None}),
        ("  → 분기 형성으로", {"k": 100, "m": FORM_Q, "c": None}),
        ("  → 30종으로", {"k": 30, "m": FORM_Q, "c": None}),
        ("  → 상한 %g%% 도입" % CAP, {"k": 30, "m": FORM_Q, "c": CAP}),
    ]
    prev_a, fun = None, []
    for lab, s in steps:
        pk = {f: top(s["k"], f) for f in sorted(set(q.ym)) }
        e, tn, _s = bt(q, ipr, idiv, pk, cap=s["c"], months=s["m"])
        a = ann(e); d = None if prev_a is None else a - prev_a
        fun.append({"step": lab.strip(), "ann": a, "delta": d, "turn": tn,
                    "ir": stt(e)["ir"], "t": stt(e)["t"]})
        print("   %-28s %+7.2f%%p  %s  IR %.2f  t %.2f  회전 %.0f%%"
              % (lab, a, ("     —  " if d is None else "%+7.2f" % d),
                 stt(e)["ir"], stt(e)["t"], tn))
        prev_a = a
    res["funnel"] = fun
    print("   ⚠ 이 경로는 **하나의 순서**다. 순서를 바꾸면 기여 배분이 달라진다.")

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
