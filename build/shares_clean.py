# -*- coding: utf-8 -*-
"""build/shares_clean.py — 주식수 단위 사고를 고쳐서 돌려주는 한 군데.

🚨 `data/fx` 의 주식수에 **정확히 100만 배** 크기의 단위 사고가 있다
   (`build/audit_shares.py` 실측: 시계열 점프 238건/78종 · sh↔sho 자릿수 불일치
   136건/47종 — AAPL·AMZN·AVGO·GILD 포함).
   같은 회사의 같은 계열 안에서 어떤 분기는 백만 단위, 어떤 분기는 주 단위다.

   시가총액을 「종가 × 주식수」로 만들면 그 분기에 비중이 100만 배가 되고,
   실측으로 **2026-06 재구성 지수에서 WAT 가 29.5%** 를 차지했다.

고치는 법 — 회사마다 중앙값을 기준으로 자릿수를 맞춘다.
   관측이 중앙값의 100배를 넘으면 1e6 으로 나누고, 1/100 아래면 1e6 을 곱한다.
   **값을 지어내지 않는다** — 자릿수만 옮긴다. 그래도 안 맞으면 버린다.

⚠ 근본 수리는 `build/refresh_facts.py` 의 단위 판정이다. 여기서는 읽는 쪽을 막는다 —
   그쪽을 고치면 `data/fx` 518개를 다시 구워야 하고, 그것은 게시 산출물이다.

  from shares_clean import clean_shares
  python build/shares_clean.py      고친 뒤 남은 이상치를 센다
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SCALE, FAR = 1e6, 100.0


def _fix(vals):
    """한 회사의 {날짜: 값} 을 자릿수만 맞춰 돌려준다."""
    if len(vals) < 3:
        return vals
    med = float(np.median(list(vals.values())))
    if not (med > 0):
        return vals
    out = {}
    for k, v in vals.items():
        if v <= 0:
            continue
        r = v / med
        if r > FAR:
            v = v / SCALE
        elif r < 1.0 / FAR:
            v = v * SCALE
        # 옮기고도 여전히 멀면 버린다 — 지어내지 않는다
        if 1.0 / FAR <= v / med <= FAR:
            out[k] = v
    return out


def clean_shares(data_dir=None):
    """{티커: {날짜: 주식수(백만)}} — 단위 사고를 고친 것."""
    d = data_dir or DATA
    out = {}
    for p in glob.glob(os.path.join(d, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8"))
        tg = j.get("tags") or {}
        best = None
        for key in ("sh", "sho"):
            v = tg.get(key) or {}
            ser = {e: float(x) for e, x, *_ in (v.get("i") or v.get("q") or v.get("a") or [])}
            ser = _fix(ser)
            if ser and (best is None or len(ser) > len(best)):
                best = ser
        if best:
            out[j["t"]] = best
    return out


def cap_frame(M, data_dir=None):
    """월 종가 격자 M(Period 인덱스)에 맞춘 시가총액 표.

    🚨 2026-09-20 2차 — 단위 사고를 고치고도 시총이 틀렸다(`AUDIT-2026-09-20-SHARES2`).
       조정가격에 **분할 전** 주식수를 곱하고 있었고(AMZN 2021-06 이 0.09조\$ · 실제 1.7조\$),
       이중클래스를 두 번 세고 있었다(GOOGL+GOOG = 지수의 13.7%).
       **정본은 `shares_split.cap_frame2` 다.** 여기서 그리로 넘긴다 —
       이미 `cap_frame` 을 쓰도록 고쳐 둔 코드가 자동으로 고쳐진 값을 받게 한다.
    """
    from shares_split import cap_frame2          # 순환 참조를 피해 늦게 부른다
    return cap_frame2(M, data_dir)


def cap_frame_scale_only(M, data_dir=None):
    """단위 사고만 고친 옛 시총 표 — 정정 전후를 대조할 때만 쓴다."""
    sh = clean_shares(data_dir)
    rows = []
    for t, ser in sh.items():
        for e, v in ser.items():
            rows.append({"t": t, "m": e[:7], "sh": v})
    W = pd.DataFrame(rows).pivot_table(index="m", columns="t", values="sh", aggfunc="last")
    W.index = pd.PeriodIndex(W.index, freq="M")
    W = W.reindex(M.index).ffill()
    C = pd.DataFrame(M.reindex(columns=W.columns).to_numpy() * W.to_numpy(),
                     index=M.index, columns=W.columns)
    return C.reindex(columns=M.columns)


def main():
    raw, fixed = {}, clean_shares()
    for p in glob.glob(os.path.join(DATA, "fx", "*.json")):
        j = json.load(io.open(p, encoding="utf-8"))
        tg = j.get("tags") or {}
        for key in ("sh", "sho"):
            v = tg.get(key) or {}
            ser = {e: float(x) for e, x, *_ in (v.get("i") or v.get("q") or v.get("a") or [])}
            if ser and (j["t"] not in raw or len(ser) > len(raw[j["t"]])):
                raw[j["t"]] = ser
    print("회사 %d개 · 고친 뒤 %d개\n" % (len(raw), len(fixed)))

    def worst(d):
        n = 0
        for t, s in d.items():
            if len(s) < 3:
                continue
            ks = sorted(s)
            for a, b in zip(ks[:-1], ks[1:]):
                if s[a] > 0 and s[b] > 0 and max(s[a] / s[b], s[b] / s[a]) >= 10:
                    n += 1
        return n
    print("■ 10배 넘게 튀는 관측")
    print("   고치기 전 %d건 · 고친 뒤 %d건" % (worst(raw), worst(fixed)))

    # 대표 종목 확인
    print("\n■ 확인 — 최근 주식수(백만주)")
    for t in ("WAT", "PCG", "FITB", "AAPL", "NVDA", "KO"):
        if t in fixed:
            s = fixed[t]
            k = max(s)
            print("   %-5s %s  %10.1f" % (t, k, s[k]))

    # 시총 상위 — 말이 되는가
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    px = {}
    for s in st["stocks"]:
        p = os.path.join(DATA, "sd", "%s.json" % s["t"])
        if os.path.exists(p):
            v = json.load(io.open(p, encoding="utf-8")).get("pxd")
            if isinstance(v, list) and len(v) == len(dates):
                px[s["t"]] = v
    P = pd.DataFrame(px, index=pd.to_datetime(dates))
    M = P.resample("M").last(); M.index = M.index.to_period("M")
    C = cap_frame(M)   # 정본(분할·이중클래스까지)
    m = M.index[-2]
    c = C.loc[m].dropna(); c = c[c > 0]
    w = (c / c.sum() * 100).sort_values(ascending=False)
    print("\n■ %s 시총 비중 상위 10 (고친 뒤)" % m)
    for t, v in w.head(10).items():
        print("   %-6s %6.2f%%" % (t, v))
    print("   상위 10 합 %.1f%%" % w.head(10).sum())
    print("   ⚠ 실제 S&P 500 의 상위 10 합은 30% 대다. 이 패널은 SPX∪NDX 518종이고")
    print("      수정종가를 쓰므로 정확히 같을 수 없다 — 자릿수가 맞는지만 본다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
