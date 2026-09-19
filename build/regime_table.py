# -*- coding: utf-8 -*-
"""build/regime_table.py — 「언제 되는가」를 잰다. **계측이지 규칙이 아니다.**

오늘까지의 관문은 전부 «항상 되는가» 를 물었다. 그래서 열한 판이 다 기각됐다.
**전략은 늘 좋을 필요가 없다 — 어느 장에서 되는지 알면 된다.** 그것을 잰다.

국면 축(FF 일별 → 그 달 직전 12개월 누적 · 삼분위)
  ① 가치 HML   ② 모멘텀 MOM   ③ 수익성 RMW   ④ 규모 SMB   ⑤ 시장변동성

🚨 이 표는 규칙이 아니다. 8신호 × 5축 × 3칸 = 120칸을 한 표본에서 본다.
   **여기서 고른 조합은 사후 맞춤이고, 걸려면 사전등록이 따로 필요하다.**
   그래도 재는 이유는 «이 신호가 죽었다» 와 «이 국면이 아니었다» 를 가르기 위해서다.

  python build/regime_table.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_regime_table.json")
D18 = r"C:\Users\Win10\Documents\여두_20260918"


def fund_excess():
    """우량성장 30 의 월별 초과수익(확정 잣대 B)."""
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    qg = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_monthly.pkl"))
    idx = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_index.pkl"))
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(os.path.join(D18, r"01_이관묶음\01_우량성장선별_산출물\idx_div_monthly_20260918.csv"))
    idiv = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in qg.groupby("ym")}
    sel, forms = {}, []
    for f, g in qg[qg.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) in (3, 6, 9, 12):
            sel[f] = dict(zip(g.tkr, g.wtgt / 100.0)); forms.append(f)

    def ym_add(y, k):
        t = int(y[:4]) * 12 + int(y[5:7]) - 1 + k
        return "%04d-%02d" % (t // 12, t % 12 + 1)
    out, prev = {}, {}
    for f in sorted(forms):
        w = sel[f]
        trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
        ch = False
        for k in (1, 2, 3):
            hm = ym_add(f, k)
            if not ("2014-07" <= hm <= "2026-08"):
                continue
            r = ret.get(ym_add(f, k - 1), {})
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
    return pd.Series([out[m] - (ipr[m] + idiv[m]) for m in ms],
                     index=pd.PeriodIndex(ms, freq="M"))


def main():
    ff = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
    F = pd.DataFrame(ff["series"], index=pd.to_datetime(ff["dates"])) / 100.0
    MF = (1 + F).groupby(F.index.to_period("M")).prod() - 1
    cum = {c: (1 + MF[c]).rolling(12).apply(np.prod, raw=True) - 1
           for c in ("hml", "mom", "rmw", "smb")}
    cum["vol"] = F.mkt_rf.groupby(F.index.to_period("M")).std() * np.sqrt(252)
    AX = {"①가치(HML)": "hml", "②모멘텀(MOM)": "mom", "③수익성(RMW)": "rmw",
          "④규모(SMB)": "smb", "⑤시장변동성": "vol"}

    st = json.load(io.open(os.path.join(DATA, "_single_table.json"), encoding="utf-8"))
    series = {c: pd.Series(v["ls"], index=pd.PeriodIndex(v["months"], freq="M"))
              for c, v in st["series"].items() if v["ls"]}
    series["펀드(우량성장30)"] = fund_excess()
    print("계열 %d개 · FF %s ~ %s" % (len(series), ff["start"], ff["end"]))

    def tt(x):
        x = np.asarray(x, float); x = x[np.isfinite(x)]
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 5 else np.nan

    res = {}
    for axn, key in AX.items():
        c = cum[key].dropna()
        q1, q2 = c.quantile(1 / 3), c.quantile(2 / 3)
        print("\n■ %s — 삼분위 (하위 ≤ %.3f < 중간 ≤ %.3f < 상위)" % (axn, q1, q2))
        print("   %-18s %14s %14s %14s   %s" % ("계열", "하위", "중간", "상위", "차(상−하)"))
        res[axn] = {}
        for nm, s in series.items():
            j = pd.DataFrame({"r": s}).join(pd.DataFrame({"c": c}), how="inner").dropna()
            if len(j) < 30:
                continue
            cells, mus = [], []
            for lo, hi in ((-np.inf, q1), (q1, q2), (q2, np.inf)):
                x = j.r[(j.c > lo) & (j.c <= hi)]
                mu = float(x.mean()) * 100 if len(x) > 5 else np.nan
                mus.append(mu)
                cells.append("%+7.3f(t%5.2f)" % (mu, tt(x)) if len(x) > 5 else "%14s" % "—")
            res[axn][nm] = {"low": mus[0], "mid": mus[1], "high": mus[2],
                            "diff": mus[2] - mus[0], "n": len(j)}
            print("   %-18s %14s %14s %14s   %+8.3f"
                  % (nm, cells[0], cells[1], cells[2], mus[2] - mus[0]))

    # 오늘 국면 — 각 축이 어느 칸인가
    print("\n■ 오늘 국면 (%s 기준)" % ff["end"])
    today = {}
    for axn, key in AX.items():
        c = cum[key].dropna()
        q1, q2 = c.quantile(1 / 3), c.quantile(2 / 3)
        v = float(c.iloc[-1])
        b = "하위" if v <= q1 else ("중간" if v <= q2 else "상위")
        today[axn] = {"value": v, "bucket": b}
        print("   %-18s %+8.3f → **%s**" % (axn, v, b))

    print("\n■ 오늘 국면에서 기대되는 순위 (그 칸의 실측 평균 · 월 %)")
    rank = {}
    for nm in series:
        vals = [res[a][nm][{"하위": "low", "중간": "mid", "상위": "high"}[today[a]["bucket"]]]
                for a in AX if nm in res.get(a, {})]
        vals = [v for v in vals if v == v]
        if vals:
            rank[nm] = float(np.mean(vals))
    for nm, v in sorted(rank.items(), key=lambda x: -x[1]):
        print("   %-18s %+7.3f%%" % (nm, v))
    print("   ⚠ 다섯 축의 단순 평균이다. 축끼리 상관이 있으므로 더하기가 아니다.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"note": "국면별 계측. 8신호×5축×3칸=120칸을 한 표본에서 봤다 — 여기서 고른 조합은 "
                 "사후 맞춤이고 걸려면 사전등록이 따로 필요하다.",
         "axes": list(AX), "table": res, "today": today, "today_rank": rank},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
