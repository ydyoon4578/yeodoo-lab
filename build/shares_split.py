# -*- coding: utf-8 -*-
"""build/shares_split.py — 시가총액의 남은 두 결함을 고친다.

`shares_clean` 이 고친 것은 **100만 배 단위 사고** 하나뿐이다. 그것을 고치고도
재구성 지수가 공식 ^GSPC 를 **월 +0.590%(연 +7.1%p)** 이겼다. 파 보니 둘이 더 있었다.

결함 ① — **조정가격 × 미조정 주식수**
   `data/sd` 의 `pxd` 는 분할·배당 **조정** 종가다. 그런데 `data/fx` 의 주식수는
   그 분기 공시 그대로라 **분할 전 숫자**다. 둘을 곱하면 분할이 있었던 회사의
   과거 시총이 분할 배수만큼 틀린다. 방향이 양쪽 다다 —

      AMZN 2021-06   0.09조$   (실제 약 1.7조$)   ← 20:1 분할이 2022-06 이라 19배 과소
      TSLA 2021-11   0.38조$   (실제 약 1.1조$)   ← 3:1 분할이 2022-08
      GE   2017-10   0.78조$   (실제 약 0.20조$)  ← 1:8 **역**분할이 2021-07 이라 과대

   고치는 법 — 분할은 공시 주식수 계열에 **깨끗한 배수의 점프**로 남는다.
   계열을 뒤에서 앞으로 걸으며 그런 점프를 찾고, 그 앞쪽 전부에 배수를 곱해
   **오늘 기준(=조정가격과 같은 기준)** 으로 맞춘다. 배수가 정수비에 가깝지 않으면
   **건드리지 않는다** — 합병으로 주식수가 는 것(WAT 59.55→98.22 · 1.65배)을
   분할로 오해하지 않으려는 것이다.

결함 ② — **이중클래스 중복 계상**
   GOOGL 과 GOOG 의 주식수가 **똑같이 12,527M** 이다. 둘 다 회사 전체 주식수를
   들고 있어서 알파벳이 지수에 **두 번** 들어간다. 실측 2026-04 에
   GOOGL 6.89% + GOOG 6.84% = **13.7%** 였다(실제 지수 비중은 8% 안팎).
   FOX/FOXA · NWS/NWSA 도 같다.

   고치는 법 — 같은 회사의 두 티커가 **동일한 계열**을 들고 있으면 반씩 나눈다.
   정확한 클래스별 주식수가 자료에 없으므로 근사다. **근사라고 적어 둔다.**

⚠ 이것도 읽는 쪽 수리다. `refresh_facts.py` 와 `data/fx` 는 안 건드린다.

  from shares_split import cap_frame2
  python build/shares_split.py        알려진 시총과 대조한다
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shares_clean import clean_shares, DATA          # noqa: E402

# 분할 배수로 인정하는 값. 정수비·단순분수만 받는다.
RATIOS = (1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0, 20.0, 30.0, 50.0)
TOL = 0.015          # 1.5% 안에 들어야 분할로 본다


def _match(r):
    """비율 r 이 분할 배수인가. 맞으면 그 배수를, 아니면 None."""
    for x in RATIOS:
        for cand in (x, 1.0 / x):
            if abs(r / cand - 1.0) <= TOL:
                return cand
    return None


def split_adjust(ser):
    """한 회사의 {날짜: 주식수} 를 **오늘 기준**으로 맞춘다."""
    ks = sorted(ser)
    if len(ks) < 3:
        return dict(ser), []
    out, hits = dict(ser), []
    factor = 1.0
    # 뒤에서 앞으로 — 오늘 쪽 값을 기준으로 삼는다
    for a, b in zip(ks[-2::-1], ks[::-1]):
        va, vb = ser[a], ser[b]
        if va > 0 and vb > 0:
            m = _match(vb / va)
            if m is not None:
                factor *= m
                hits.append((a, b, va, vb, m))
        out[a] = ser[a] * factor
    return out, hits


def clean_shares2(data_dir=None, report=False):
    """단위 사고 + 분할 + 이중클래스까지 고친 {티커: {날짜: 주식수}}."""
    base = clean_shares(data_dir)
    out, allhits = {}, {}
    for t, ser in base.items():
        fixed, hits = split_adjust(ser)
        out[t] = fixed
        if hits:
            allhits[t] = hits

    # 이중클래스 — 같은 계열을 들고 있는 티커끼리 묶어 반씩 나눈다
    sig, dual = {}, []
    for t, ser in out.items():
        ks = sorted(ser)
        if len(ks) < 4:
            continue
        key = tuple(round(ser[k], 4) for k in ks[-4:]) + (ks[-1],)
        sig.setdefault(key, []).append(t)
    for key, ts in sig.items():
        if len(ts) > 1:
            dual.append(sorted(ts))
            for t in ts:
                out[t] = {k: v / len(ts) for k, v in out[t].items()}
    if report:
        return out, allhits, dual
    return out


def cap_frame2(M, data_dir=None):
    """월 종가 격자 M 에 맞춘 시가총액 표 — 세 결함을 다 고친 것."""
    sh = clean_shares2(data_dir)
    rows = [{"t": t, "m": e[:7], "sh": v} for t, ser in sh.items() for e, v in ser.items()]
    W = pd.DataFrame(rows).pivot_table(index="m", columns="t", values="sh", aggfunc="last")
    W.index = pd.PeriodIndex(W.index, freq="M")
    W = W.reindex(M.index).ffill()
    C = pd.DataFrame(M.reindex(columns=W.columns).to_numpy() * W.to_numpy(),
                     index=M.index, columns=W.columns)
    return C.reindex(columns=M.columns)


# ---- 검증 -------------------------------------------------------------
# 공개적으로 알려진 시가총액. 이 표가 이 수리의 채점표다.
ANCHOR = [("AAPL", "2021-11", 2.65), ("NVDA", "2024-05", 2.70), ("MSFT", "2021-11", 2.39),
          ("AMZN", "2021-06", 1.73), ("TSLA", "2021-11", 1.10), ("GE", "2017-10", 0.20),
          ("JNJ", "2017-10", 0.44), ("XOM", "2014-12", 0.39), ("WMT", "2019-06", 0.31),
          ("GOOGL", "2026-04", 1.40), ("KO", "2019-06", 0.22)]


def _px_frame():
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
    return M


def main():
    from shares_clean import cap_frame_scale_only as cap_old
    sh, hits, dual = clean_shares2(report=True)
    print("회사 %d개 · 분할을 찾은 회사 %d개 · 이중클래스 묶음 %d개\n"
          % (len(sh), len(hits), len(dual)))
    print("■ 이중클래스로 묶인 것 (반씩 나눈다)")
    for g in sorted(dual)[:14]:
        print("   %s" % " = ".join(g))
    print("\n■ 찾은 분할 몇 개")
    n = 0
    for t in ("AMZN", "TSLA", "GE", "NVDA", "AAPL", "GOOGL", "WMT"):
        for a, b, va, vb, m in hits.get(t, [])[:2]:
            print("   %-6s %s -> %s   %9.1f -> %9.1f   배수 %.3f" % (t, a[:7], b[:7], va, vb, m))
            n += 1
    if not n:
        print("   (없음)")

    M = _px_frame()
    Co, Cn = cap_old(M, DATA), cap_frame2(M, DATA)
    print("\n■ 알려진 시가총액과 대조 (조 달러)")
    print("   %-6s %-9s %8s %10s %10s %9s" % ("종목", "달", "알려진값", "고치기전", "고친뒤", "오차"))
    eo, en = [], []
    for t, ym, real in ANCHOR:
        m = pd.Period(ym, freq="M")
        if t not in Cn.columns or m not in Cn.index:
            print("   %-6s %-9s  자료 없음" % (t, ym)); continue
        a = float(Co.at[m, t]) / 1e6 if np.isfinite(Co.at[m, t]) else np.nan
        b = float(Cn.at[m, t]) / 1e6 if np.isfinite(Cn.at[m, t]) else np.nan
        if np.isfinite(a): eo.append(abs(a / real - 1))
        if np.isfinite(b): en.append(abs(b / real - 1))
        print("   %-6s %-9s %8.2f %10.2f %10.2f %8.0f%%"
              % (t, ym, real, a, b, 100 * (b / real - 1) if np.isfinite(b) else np.nan))
    print("\n   평균 절대오차 — 고치기 전 %.0f%% · 고친 뒤 %.0f%%"
          % (100 * np.mean(eo), 100 * np.mean(en)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
