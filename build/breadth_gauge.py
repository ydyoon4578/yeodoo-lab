# -*- coding: utf-8 -*-
"""build/breadth_gauge.py — 시장 폭(breadth) 계기판. **계측이지 전략이 아니다.**

boulder2163 의 「주간 Market Breadth」(2026-08-23~)가 쓰는 세 축을 이 랩의 미국
패널에 옮겨 재고, **그 축들이 실제로 무엇을 예고하는지까지** 본다.

  ① 집중도   지수(시총가중) 수익 − 동일가중 수익
  ② 참여 범위 상승 종목 비율
  ③ 분포 꼬리 20일·252일 신고가 비율 − 신저가 비율

🚨 블로그는 «검증된 임계값이 없으므로 강함·약함으로 판정하지 않고 기록만 한다» 고
   적었다. 맞는 태도다. 다만 «그러면 이 기록이 무엇에 쓰이나» 는 남는다.
   그래서 여기서는 한 걸음만 더 간다 — **문턱을 만들지 않고**, 세 축의 백분위별로
   이후 수익이 실제로 갈리는지 **표로만** 낸다. 규칙을 만들지 않는다.

🚨 랩의 선례를 먼저 적는다. 국면 조건부 규칙은 10건 중 9건 기각됐다
   (REGIME0·FACROT·SSROT·CGATE·RATEUP·IDXTILT·IDXREV·IDXREVBAND·DURSTYLE4).
   특히 **CGATE 가 바로 「집중도로 국면을 가른다」였고 기각(F2 · t 0.86)됐다.**
   그 결과문서의 핵심 발견도 같이 본다 — 집중도 **수준**은 이 창에서 단조 증가라
   121달 중 109달(90%)이 한 상태였다. **수준으로는 국면이 안 갈린다.**
   그래서 여기서는 수준과 **변화율**을 나란히 낸다.

  python build/breadth_gauge.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_SD = os.path.join(DATA, "sd")
OUT = os.path.join(DATA, "_breadth_gauge.json")
WARM = 252 * 2          # 백분위·252일 신고가용 워밍업
HOR = (21, 63)


def load():
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    n = len(dates)
    px = {}
    for s in st["stocks"]:
        p = os.path.join(DIR_SD, "%s.json" % s["t"])
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        a = d.get("pxd")
        if isinstance(a, list) and len(a) == n:
            px[s["t"]] = a
    P = pd.DataFrame(px, index=pd.to_datetime(dates))
    b = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    sp = b["series"]["spx"]                    # {ticker, label, px}
    S = pd.Series(sp["px"], index=pd.to_datetime(b["dates"]), dtype="float64")
    print("   지수 = %s (%s)" % (sp.get("ticker"), sp.get("label")))
    S = S.reindex(P.index)            # 랩 격자에 맞춘다
    return dates, P, S


def pctile_expanding(s, minp=WARM):
    """그 시점까지의 자료로만 본 백분위(선견 없음)."""
    return s.expanding(min_periods=minp).apply(
        lambda a: (a[:-1] < a[-1]).mean() * 100 if len(a) > 1 else np.nan, raw=True)


def main():
    dates, P, S = load()
    n = len(dates)
    print("종목 %d · %s ~ %s (%d거래일)" % (P.shape[1], dates[0], dates[-1], n))
    if S.isna().mean() > 0.02:
        print("⚠ 지수 계열 결측 %.1f%%" % (S.isna().mean() * 100))

    R = P.pct_change()
    ew = R.mean(axis=1)                       # 동일가중
    ix = S.pct_change()                       # 시총가중(공식 지수 PR)

    # ── ① 집중도 — 지수 − 동일가중 (누적 스프레드) ──────────────────────────
    conc21 = (ix - ew).rolling(21).sum() * 100
    conc63 = (ix - ew).rolling(63).sum() * 100
    # ── ② 참여 범위 — 상승 종목 비율 ───────────────────────────────────────
    adv = (R > 0).sum(axis=1) / R.notna().sum(axis=1) * 100
    adv21 = adv.rolling(21).mean()
    # 지수를 이긴 종목 비율 — 집중도의 다른 얼굴
    beat21 = (P.pct_change(21).sub(S.pct_change(21), axis=0) > 0).sum(axis=1) \
        / P.pct_change(21).notna().sum(axis=1) * 100
    # ── ③ 분포 꼬리 — 신고가·신저가 ────────────────────────────────────────
    def nh_nl(w):
        hi = P.rolling(w).max()
        lo = P.rolling(w).min()
        h = (P >= hi - 1e-12).sum(axis=1) / P.notna().sum(axis=1) * 100
        l = (P <= lo + 1e-12).sum(axis=1) / P.notna().sum(axis=1) * 100
        return h - l
    tail20 = nh_nl(20).rolling(5).mean()
    tail252 = nh_nl(252).rolling(5).mean()

    AX = {"①집중도 21일": conc21, "①집중도 63일": conc63,
          "②상승종목비율 21일": adv21, "②지수이긴비율 21일": beat21,
          "③꼬리 20일(신고−신저)": tail20, "③꼬리 252일(신고−신저)": tail252}

    # ── 오늘의 값 ──────────────────────────────────────────────────────────
    print("\n■ 오늘 (%s) — 수준 · 5일전 대비 · 확장창 백분위" % dates[-1])
    print("   %-24s %10s %10s %9s" % ("축", "수준", "5일 변화", "백분위"))
    today = {}
    for k, v in AX.items():
        p = pctile_expanding(v)
        cur, prev = float(v.iloc[-1]), float(v.iloc[-6])
        today[k] = {"level": cur, "chg5": cur - prev, "pct": float(p.iloc[-1])}
        print("   %-24s %+10.2f %+10.2f %8.0f%%" % (k, cur, cur - prev, p.iloc[-1]))

    # ── 이 축들이 무엇을 예고하나 ──────────────────────────────────────────
    # 🚨 문턱을 만들지 않는다. 백분위 5구간으로 나눠 이후 수익을 표로만 낸다.
    print("\n■ 각 축의 백분위 구간별 «이후» 수익 (%, 연율 아님 · 겹침 있음)")
    print("   대상 셋 — 지수 · 동일가중 · 동일가중−지수(스프레드)")
    fwd = {}
    for h in HOR:
        fwd[h] = {"지수": S.shift(-h) / S - 1,
                  "동일가중": (1 + ew).rolling(h).apply(np.prod, raw=True).shift(-h) - 1}
        fwd[h]["스프레드"] = fwd[h]["동일가중"] - fwd[h]["지수"]

    res = {}
    for k, v in AX.items():
        p = pctile_expanding(v)
        res[k] = {}
        print("\n   [%s]" % k)
        print("      %-10s %s" % ("백분위", "".join(
            "%22s" % ("%d일 %s" % (h, t)) for h in HOR for t in ("지수", "스프레드"))))
        for lo, hi, lab in ((0, 20, "하위 20%"), (20, 40, "20~40"), (40, 60, "40~60"),
                            (60, 80, "60~80"), (80, 100, "상위 20%")):
            m = (p >= lo) & (p < hi if hi < 100 else p <= 100)
            cells, row = [], {}
            for h in HOR:
                for t in ("지수", "스프레드"):
                    x = fwd[h][t][m].dropna()
                    cells.append("%10.2f (n%5d)" % (x.mean() * 100, len(x)) if len(x) > 30
                                 else "%16s" % "—")
                    row["%d_%s" % (h, t)] = float(x.mean()) * 100 if len(x) > 30 else None
            res[k][lab] = row
            print("      %-10s %s" % (lab, "".join("%22s" % c for c in cells)))

    # ── 🚨 유의성 — 겹친 관측을 빼고 보면 남는가 ────────────────────────────
    # 위 표의 n 은 **일별 관측**이라 21·63일 선행 수익이 서로 겹친다. 실효 표본은
    # n/h 수준이다(63일이면 1273 → 약 20). 겹침을 Newey-West 로 잡고, 겹치지 않는
    # 표본(h일 간격 재추출)으로도 다시 낸다.
    def nw_t(x, lag):
        x = np.asarray(x, float); x = x[~np.isnan(x)]
        m = len(x)
        if m < 30:
            return None
        d = x - x.mean()
        var = float((d * d).sum() / m)
        for k in range(1, min(lag, m - 1) + 1):
            var += 2 * (1 - k / (lag + 1.0)) * float((d[k:] * d[:-k]).sum() / m)
        return round(float(x.mean() / np.sqrt(var / m)), 2) if var > 0 else None

    print("\n■ 🚨 상위20% − 하위20% 차이가 겹침을 걷고도 남는가")
    print("   %-24s %s" % ("축", "".join("%26s" % ("%d일 %s" % (h, t))
                                         for h in HOR for t in ("지수", "스프레드"))))
    sig = {}
    for k, v in AX.items():
        p = pctile_expanding(v)
        hi_m, lo_m = p >= 80, p < 20
        cells, row = [], {}
        for h in HOR:
            for t in ("지수", "스프레드"):
                f = fwd[h][t]
                a, b2 = f[hi_m].dropna(), f[lo_m].dropna()
                diff = (a.mean() - b2.mean()) * 100
                # 겹침 보정 t — 상위/하위 더미로 만든 계열의 NW t
                z = f.where(hi_m, np.nan).fillna(0) * 0
                s_ = pd.Series(np.nan, index=f.index)
                s_[hi_m] = f[hi_m] - b2.mean()
                s_[lo_m] = -(f[lo_m] - a.mean())
                t_nw = nw_t(s_.dropna().to_numpy(), h)
                # 겹치지 않는 표본 — h일 간격
                idx = np.arange(0, len(f), h)
                fs, ps = f.iloc[idx], p.iloc[idx]
                d2 = (fs[ps >= 80].mean() - fs[ps < 20].mean()) * 100
                cells.append("%+7.2f t%5s ind%+6.2f" % (diff, t_nw, d2))
                row["%d_%s" % (h, t)] = {"diff": diff, "t_nw": t_nw, "indep": float(d2)}
        sig[k] = row
        print("   %-24s %s" % (k, "".join("%26s" % c for c in cells)))
    print("   ind = 겹치지 않게 %s일 간격으로만 뽑아 다시 낸 차이" % "·".join(str(h) for h in HOR))

    # ── 단조성 — 구간이 순서대로 가나 ──────────────────────────────────────
    print("\n■ 단조성 — 백분위가 오를수록 이후 수익이 한 방향으로 가나")
    print("   (같은 방향으로 죽 가면 신호, 들쭉날쭉하면 구간의 성질이다)")
    print("   %-24s %14s %14s" % ("축", "21일 지수", "21일 스프레드"))
    for k in AX:
        out = []
        for t in ("지수", "스프레드"):
            v = [res[k][l]["21_%s" % t] for l in ("하위 20%", "20~40", "40~60", "60~80", "상위 20%")]
            if any(x is None for x in v):
                out.append("—"); continue
            d = np.diff(v)
            out.append("단조↑" if all(d > 0) else ("단조↓" if all(d < 0) else "들쭉날쭉"))
        print("   %-24s %14s %14s" % (k, out[0], out[1]))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"as_of": dates[-1], "n_stocks": int(P.shape[1]), "today": today,
         "buckets": res, "sig": sig, "horizons": list(HOR),
         "note": "계측 전용 — 문턱도 규칙도 만들지 않는다. CGATE(기각) 선례를 볼 것."},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
