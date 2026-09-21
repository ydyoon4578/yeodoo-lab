# -*- coding: utf-8 -*-
"""build/fund_fit.py — 랩의 규칙 중 **우량성장 30 에 얹을 수 있는 것**을 고른다.

🚨 이것은 사전등록이 아니라 **선별기**다. 판정을 내리지 않는다 — 다음에 무엇을
   사전등록할지 고르는 데 쓴다. 여기서 1등이라고 게시되는 것이 아니다.

무엇을 재나 — 기준을 계산 전에 적는다
   펀드는 이미 **대형 우량성장 롱온리 30종 분기 리밸**이다. 그러니 «성적이 좋은 규칙»
   이 아니라 **«펀드가 이미 하고 있지 않은 일을 하는 규칙»** 을 찾아야 한다.
   그래서 순위는 단독 성적이 아니라 **펀드 위의 증분 알파**로 낸다.

     ① 시점정확(PIT)으로 쟀나           — 소급만 있는 규칙은 아예 뺀다.
     ② PIT 초과가 양수인가              — 음수면 얹을 이유가 없다.
     ③ 펀드 월별 초과와 상관이 낮은가     — 상관이 높으면 같은 일을 두 번 한다.
     ④ **펀드 위의 증분 알파와 그 t**     — 펀드 초과에 회귀하고 남는 절편. **주 잣대.**
     ⑤ 회전율                          — 펀드는 분기 리밸이다. 연 10회를 넘으면 무겁다.
     ⑥ 롱온리로 쓸 수 있나              — 롱숏·게이트는 그대로 못 얹는다(표시만 한다).
     ⑦ 🚨 오늘 찾은 시총 결함에 걸리나    — 시총가중·주식수 규칙은 수치를 믿지 않는다
                                        (AUDIT-2026-09-20-SHARES·SHARES2).

   ⚠ 겹치는 창이 짧으면 t 가 부푼다. 최소 60개월을 요구하고, 개월 수를 함께 싣는다.
   ⚠ 118종을 한 표본에서 훑는다. **여기 t 를 다중검정 없이 읽으면 안 된다** —
     선별기의 출력은 «가설 후보» 이지 «발견» 이 아니다.

  python build/fund_fit.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
D18 = r"C:\Users\Win10\Documents\여두_20260918"
OUT = os.path.join(DATA, "_fund_fit.json")

MIN_M = 60          # 겹치는 창 최소 개월
CORR_HI = 0.60      # 이보다 높으면 «같은 일을 한다»
TURN_HI = 10.0      # 연 회전 배수 상한(사용자 결정과 같은 값)

# 오늘의 시총 결함에 걸리는 규칙 — 수치를 믿지 않는다
SUSPECT = ("x-cap", "x-ncap", "x-shiss", "x-capw", "x-capndx", "x-demega")


def fund_monthly(full=False):
    """펀드 월별 **초과**(바스켓 TR − S&P 500 TR). 확정 잣대 B 와 같은 정의다.

    🚨 2026-09-21 — **MAX_YEARS = 10 을 여기서 건다.** 사용자 지적:
      «우량성장선별 30 이건 백테스팅 최근 10년만 하라니깐 왜 아직도 2014부터야»
      아래 HOLD0/HOLD1 이 손으로 박힌 날짜(2014-07~2026-08 · 12.2년)라 이 함수를 읽는
      곳이 전부 규약 밖에 있었다. build/maxyears.py 가 어제 «규약은 코드가 아니라
      랩에 거는 것» 이라고 적으며 만들어졌는데, 정작 **펀드 계열이 그것을 안 읽었다.**
      ⚠ 원자료의 창(2014-07~)은 그대로 둔다 — 자르는 것은 **끝에서부터 10년**이다.
    full=True — 자르지 않은 전체 창. **재진술·앵커 대조에만 쓴다.**
    """
    qg = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_monthly.pkl"))
    idx = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_index.pkl"))
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(os.path.join(D18,
        r"01_이관묶음\01_우량성장선별_산출물\idx_div_monthly_20260918.csv"))
    idiv = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in qg.groupby("ym")}
    sel, forms = {}, []
    for f, g in qg[qg.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) in (3, 6, 9, 12):
            sel[f] = dict(zip(g.tkr, g.wtgt / 100.0)); forms.append(f)

    def add(y, k):
        t = int(y[:4]) * 12 + int(y[5:7]) - 1 + k
        return "%04d-%02d" % (t // 12, t % 12 + 1)
    out, prev = {}, {}
    for f in sorted(forms):
        w = sel[f]
        trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
        ch = False
        for k in (1, 2, 3):
            hm = add(f, k)
            if not ("2014-07" <= hm <= "2026-08"):
                continue
            r = ret.get(add(f, k - 1), {})
            ok = {t: v for t, v in w.items() if t in r}
            s = sum(ok.values())
            if s <= 0:
                continue
            g = sum(v / s * r[t] for t, v in ok.items())
            out[hm] = g - (trade * 0.0025 if not ch else 0.0)
            ch = True
            w = {t: (v / s) * (1 + r[t]) for t, v in ok.items()}
            z = sum(w.values()); w = {t: v / z for t, v in w.items()}
        prev = w
    ms = sorted(m for m in out if m in ipr and m in idiv and pd.notna(ipr[m]))
    S = pd.Series([out[m] - (ipr[m] + idiv[m]) for m in ms],
                  index=pd.PeriodIndex(ms, freq="M"), dtype="float64")
    if full:
        return S
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    from maxyears import cap as _cap                      # noqa: E402
    return S.reindex(_cap(S.index))


def ols(y, x):
    """y = a + b x. (a, t_a, b, R²) — 절편이 «펀드 위에 남는 몫» 이다."""
    X = np.column_stack([np.ones(len(x)), x])
    bhat, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ bhat
    n, k = len(y), 2
    s2 = float(e @ e) / max(1, n - k)
    XtX = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(XtX) * s2)
    ss = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float(e @ e) / ss if ss > 0 else np.nan
    return float(bhat[0]), float(bhat[0] / se[0]) if se[0] > 0 else np.nan, float(bhat[1]), r2


def main():
    F = fund_monthly()
    print("펀드 월별 초과 %d개월 (%s ~ %s) · 평균 %+.3f%%/월 (연 %+.2f%%p)"
          % (len(F), F.index[0], F.index[-1], F.mean() * 100, F.mean() * 1200))

    pit = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    rep = json.load(io.open(os.path.join(DATA, "strategy_report.json"), encoding="utf-8"))
    meta = {x["sid"]: x for x in rep["items"]}

    rows = []
    for s in pit.get("strategies") or []:
        ch = (s.get("chart") or {}).get("monthly") or []
        if not ch:
            continue
        e = pd.Series({pd.Period(m["m"], freq="M"): (m["r"] - m["b"]) / 100.0
                       for m in ch if m.get("r") is not None and m.get("b") is not None},
                      dtype="float64")
        j = e.index.intersection(F.index)
        if len(j) < MIN_M:
            continue
        y, x = e.reindex(j).to_numpy(), F.reindex(j).to_numpy()
        if not (np.isfinite(y).all() and np.isfinite(x).all()):
            continue
        a, ta, b, r2 = ols(y, x)
        corr = float(np.corrcoef(y, x)[0, 1])
        m = meta.get(s["sid"]) or {}
        rows.append({
            "sid": s["sid"], "name": s.get("name") or m.get("name") or "",
            "role": m.get("role"), "kind": m.get("kind"),
            "n_m": int(len(j)),
            "pit_excess": s.get("excess_cagr"), "pit_t": s.get("t"),
            "turnover": s.get("turnover"),
            "corr": corr, "alpha_m": a * 100, "alpha_y": a * 1200, "t_alpha": ta,
            "beta": b, "r2": r2,
            "ls": ("롱숏" in (s.get("name") or "")) or ("숏" in (s.get("name") or "")),
            "gate": (m.get("role") == "타이밍오버레이"),
            "cap_suspect": s["sid"].startswith(SUSPECT),
        })
    D = pd.DataFrame(rows)
    print("PIT 월별 계열이 있고 펀드와 %d개월 이상 겹치는 규칙 %d종\n" % (MIN_M, len(D)))

    ok = D[(D.pit_excess > 0) & (D["corr"].abs() < CORR_HI)
           & (D.turnover.fillna(0) <= TURN_HI)].copy()
    print("■ 거르고 남은 것 %d종 (PIT 초과 > 0 · |상관| < %.2f · 회전 ≤ %.0f배)"
          % (len(ok), CORR_HI, TURN_HI))

    ok = ok.sort_values("t_alpha", ascending=False)
    print("\n■ 펀드 위의 증분 알파 상위 15")
    print("   %-16s %-34s %8s %6s %7s %6s %6s %5s"
          % ("sid", "이름", "증분/년", "t", "상관", "PIT초과", "회전", "개월"))
    for _, r in ok.head(15).iterrows():
        print("   %-16s %-34s %+7.2f%%p %6.2f %+7.2f %+6.1f %6.1f %5d%s"
              % (r.sid, (r["name"] or "")[:34], r.alpha_y, r.t_alpha, r["corr"],
                 r.pit_excess, r.turnover if pd.notna(r.turnover) else -1, r.n_m,
                 " ⚠시총" if r.cap_suspect else (" ⚠롱숏" if r.ls else "")))

    print("\n■ 반대쪽 — 펀드와 가장 많이 겹치는 규칙 (같은 일을 한다)")
    for _, r in D.reindex(D["corr"].sort_values(ascending=False).index).head(6).iterrows():
        print("   %-16s %-38s 상관 %+.2f · β %+.2f · 증분 %+.2f%%p (t %.2f)"
              % (r.sid, (r["name"] or "")[:38], r["corr"], r.beta, r.alpha_y, r.t_alpha))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"note": ("우량성장 30 위의 증분으로 고른 선별기. 사전등록이 아니다 — "
                  "다음에 무엇을 등록할지 고르는 데 쓴다. 118종을 한 표본에서 훑었으므로 "
                  "여기 t 를 다중검정 없이 읽으면 안 된다."),
         "fund": {"n_m": int(len(F)), "start": str(F.index[0]), "end": str(F.index[-1]),
                  "mean_m_pct": float(F.mean() * 100), "mean_y_pp": float(F.mean() * 1200)},
         "criteria": {"min_months": MIN_M, "corr_hi": CORR_HI, "turnover_hi": TURN_HI},
         "rows": D.to_dict("records")}, ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
