# -*- coding: utf-8 -*-
"""build/qg_sector.py — 우량성장 30 의 초과수익은 섹터 베팅인가 종목 선택인가. **계측이다.**

이 펀드의 가장 큰 미해결 위험은 **정보기술 계열 85.7%** 다. 사전등록 §10 이
«상한을 걸지 않고 조건을 뺐다» 로 닫았는데, **정작 「그 쏠림이 알파의 원천인가」는
안 쟀다.** 그것을 잰다.

Brinson 분해 — 초과수익을 둘로 가른다.

    배분 효과 = Σ (펀드섹터비중 − 지수섹터비중) × (지수섹터수익 − 지수수익)
    선택 효과 = Σ  펀드섹터비중 × (펀드섹터수익 − 지수섹터수익)

**배분이 대부분이면 이 펀드는 섹터 베팅이고, 85.7% 가 이야기의 전부다.**
**선택이 대부분이면 점수가 섹터 안에서 실제로 일하고 있다.**

🚨 지수 섹터 비중·수익은 **그 달 실제 편입명단**(index_history.json)의 시총가중으로
   만든다. 오늘 패널로 만들면 편입편향이 분해에 들어간다.

  python build/qg_sector.py
"""

# 🚨 2026-09-20 — 이 스크립트는 **폐기**한다. 돌려도 결과를 쓰지 않는다.
#
#    이 분해는 「그 달 편입명단 시총가중」으로 재구성한 지수를 벤치마크로 쓴다.
#    그 지수가 공식 ^GSPC 를 **월 +0.799%(연 +9.59%p)** 이긴다.
#
#    원인은 시총이 아니라 패널이다 — 편입명단에 한 번이라도 나온 797종 중
#    **가격이 아예 없는 것이 166종(21%)** 이고, 그 166종은
#    **2014-06 기준 120종 중 오늘 지수에 남은 것이 0종**이다.
#    즉 빠진 종목은 무작위 결측이 아니라 **탈락자 명단**이고,
#    그것을 빼고 만든 지수는 **생존편향 그 자체**다.
#
#    분해 합계가 확정 잣대(+8.16%p)의 절반도 안 되는 +3.41%p 로 나온 것이
#    처음부터 그 증상이었다. 고치려면 **탈락 종목의 과거 가격**이 필요하고
#    이 랩에는 없다.  → `build/AUDIT-2026-09-20-SHARES2.md` §5
#
#    ⚠ 펀드의 확정 초과수익 +8.16%p 는 멀쩡하다 — 그것은 공식 S&P 500 TR 을 쓴다.
#      무효가 된 것은 **그 초과를 섹터와 종목으로 쪼개려던 시도 하나**다.

from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_qg_sector.json")
D18 = r"C:\Users\Win10\Documents\여두_20260918"


def main():
    qg = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_monthly.pkl"))
    mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    hsec = hist.get("sector") or {}
    months = hist["months"]

    def sof(t):
        return sect.get(t) or hsec.get(t) or "?"

    # 가격·시총
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    px = {}
    for s in st["stocks"]:
        p = os.path.join(DATA, "sd", "%s.json" % s["t"])
        if os.path.exists(p):
            v = json.load(io.open(p, encoding="utf-8")).get("pxd")
            if isinstance(v, list) and len(v) == len(dates):
                px[s["t"]] = v
    pit = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))
    for t, v in pit["px"].items():
        if t in px or not isinstance(v, dict):
            continue
        arr = [np.nan] * len(dates)
        i0, pp = int(v.get("i0") or 0), (v.get("p") or [])
        for k, val in enumerate(pp):
            if 0 <= i0 + k < len(dates) and val is not None:
                arr[i0 + k] = float(val)
        px[t] = arr
    P = pd.DataFrame(px, index=pd.to_datetime(dates))
    M = P.resample("M").last(); M.index = M.index.to_period("M")
    MR = M.pct_change()
    # 🚨 시총은 직접 만들지 않는다 — AUDIT-2026-09-20-SHARES 규약 §7-1.
    #    data/fx 의 주식수에 100만 배 단위 사고가 있어, 이 분해의 첫 판이 무효가 됐다.
    from shares_clean import cap_frame
    CAP = cap_frame(M, DATA)
    top = CAP.iloc[-1].dropna().sort_values(ascending=False)
    tot = float(top.sum())
    print("   시총 비중 상위 5 (%s) — %s" % (
        str(M.index[-1]),
        " · ".join("%s %.2f%%" % (t, 100 * v / tot) for t, v in top.head(5).items())))
    print("가격 %d종 · 월 %d개" % (P.shape[1], len(M)))

    # 펀드 보유 — 분기 형성 뒤 3개월 유지(표류는 무시하고 목표비중으로 근사)
    hold = {}
    for f, g in qg[qg.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) not in (3, 6, 9, 12):
            continue
        w = dict(zip(g.tkr, g.wtgt / 100.0))
        for k in (1, 2, 3):
            t = int(f[:4]) * 12 + int(f[5:7]) - 1 + k
            hold["%04d-%02d" % (t // 12, t % 12 + 1)] = w
    print("펀드 보유월 %d개 (%s ~ %s)" % (len(hold), min(hold), max(hold)))

    rows = []
    for ymk, w in sorted(hold.items()):
        m = pd.Period(ymk, freq="M")
        if m not in MR.index:
            continue
        v = months.get(ymk) or {}
        uni = [t for t in (v.get("spx") or []) if t in CAP.columns and
               np.isfinite(CAP.at[m, t]) and CAP.at[m, t] > 0 and pd.notna(MR.at[m, t])]
        if len(uni) < 100:
            continue
        cap = pd.Series({t: float(CAP.at[m, t]) for t in uni})
        bw = cap / cap.sum()
        br = pd.Series({t: float(MR.at[m, t]) for t in uni})
        idx_r = float((bw * br).sum())
        fw = pd.Series({t: x for t, x in w.items() if t in MR.columns and pd.notna(MR.at[m, t])})
        if fw.empty:
            continue
        fw = fw / fw.sum()
        fr = pd.Series({t: float(MR.at[m, t]) for t in fw.index})
        secs = sorted({sof(t) for t in set(uni) | set(fw.index)})
        alloc = sel = 0.0
        detail = {}
        for s in secs:
            bi = [t for t in uni if sof(t) == s]
            fi = [t for t in fw.index if sof(t) == s]
            wb = float(bw[bi].sum()) if bi else 0.0
            wf = float(fw[fi].sum()) if fi else 0.0
            rb = float((bw[bi] * br[bi]).sum() / wb) if wb > 0 else idx_r
            rf = float((fw[fi] * fr[fi]).sum() / wf) if wf > 0 else rb
            a = (wf - wb) * (rb - idx_r)
            e = wf * (rf - rb)
            alloc += a; sel += e
            detail[s] = {"wf": wf, "wb": wb, "a": a, "e": e}
        rows.append({"m": ymk, "alloc": alloc, "sel": sel,
                     "total": float((fw * fr).sum()) - idx_r, "detail": detail})

    D = pd.DataFrame(rows)
    print("분해한 달 %d개 (%s ~ %s)\n" % (len(D), D.m.iloc[0], D.m.iloc[-1]))

    def tt(x):
        x = np.asarray(x, float)
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))

    print("■ Brinson 분해 — 지수(그 달 편입명단 시총가중) 대비")
    print("   %-14s %12s %8s %12s" % ("", "월평균", "t", "연환산"))
    for k, nm in (("alloc", "배분 효과(섹터)"), ("sel", "선택 효과(종목)"), ("total", "합계")):
        x = D[k].to_numpy()
        print("   %-14s %+11.3f%% %8.2f %+11.2f%%p" % (nm, x.mean() * 100, tt(x), x.mean() * 1200))
    share = D.sel.mean() / (D.alloc.mean() + D.sel.mean()) * 100
    print("   → **선택 효과가 초과수익의 %.0f%%** 다" % share)

    print("\n■ 섹터별 기여 (월평균 %p · 상위 6)")
    agg = {}
    for r in rows:
        for s, d in r["detail"].items():
            a = agg.setdefault(s, {"a": [], "e": [], "wf": [], "wb": []})
            a["a"].append(d["a"]); a["e"].append(d["e"])
            a["wf"].append(d["wf"]); a["wb"].append(d["wb"])
    tab = []
    for s, a in agg.items():
        tab.append({"s": s, "wf": np.mean(a["wf"]) * 100, "wb": np.mean(a["wb"]) * 100,
                    "a": np.mean(a["a"]) * 100, "e": np.mean(a["e"]) * 100})
    T = pd.DataFrame(tab).sort_values("e", key=abs, ascending=False)
    print("   %-26s %8s %8s %9s %9s" % ("섹터", "펀드비중", "지수비중", "배분", "선택"))
    for _, r in T.head(6).iterrows():
        print("   %-26s %7.1f%% %7.1f%% %+8.3f %+8.3f" % (r.s[:26], r.wf, r.wb, r.a, r.e))

    it = T[T.s.astype(str).str.contains("Information Tech")]
    if len(it):
        r = it.iloc[0]
        print("\n   정보기술 — 펀드 %.1f%% vs 지수 %.1f%% (초과 %+.1f%%p)"
              % (r.wf, r.wb, r.wf - r.wb))
        print("      그 초과비중이 만든 배분 효과 월 %+.3f%%p (연 %+.2f%%p)" % (r.a, r.a * 12))
        print("      정보기술 **안에서** 고른 값 월 %+.3f%%p (연 %+.2f%%p)" % (r.e, r.e * 12))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"n_months": len(D),
         "alloc_pm": float(D.alloc.mean()) * 100, "alloc_t": tt(D.alloc.to_numpy()),
         "sel_pm": float(D.sel.mean()) * 100, "sel_t": tt(D.sel.to_numpy()),
         "total_pm": float(D.total.mean()) * 100, "sel_share_pct": float(share),
         "by_sector": T.to_dict("records"),
         "note": "Brinson 분해. 지수는 그 달 실제 편입명단의 시총가중."},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
