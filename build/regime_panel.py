# -*- coding: utf-8 -*-
"""build/regime_panel.py — 시장 국면을 수로 가른다. **계측이지 규칙이 아니다.**

탐색 풀 127장이 «어떤 장에서 되는 전략인가» 를 말하려면 **장이 먼저 정의**돼야 한다.
여기서 축을 만들고, 각 축의 오늘 상태와 과거 분포를 낸다.

축 일곱
  ① 가치/성장   HML 12개월 누적
  ② 대형/소형   SMB 12개월 누적
  ③ 모멘텀      Mom 12개월 누적 + 붕괴 표식(시장 하락 뒤 패자 반등)
  ④ 수익성/투자 RMW · CMA 12개월 누적
  ⑤ 변동성      시장 21일 실현변동성
  ⑥ 금리        10년 수준 · 12개월 변화 · 10년−2년
  ⑦ 폭          지수 이긴 종목 비율(breadth_gauge 와 같은 정의)

🚨 국면으로 **매매하지 않는다.** 이 랩은 국면 조건부 규칙을 10건 돌려 9건 기각했다.
   여기 산출물은 «카드를 분류하는 자» 이지 «전환 신호» 가 아니다.

  python build/regime_panel.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_regime_panel.json")


def pct_exp(s, minp=756):
    return s.expanding(min_periods=minp).apply(
        lambda a: (a[:-1] < a[-1]).mean() * 100 if len(a) > 1 else np.nan, raw=True)


def main():
    ff = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
    F = pd.DataFrame(ff["series"], index=pd.to_datetime(ff["dates"])) / 100.0
    print("FF 일별 %s ~ %s · %d일" % (ff["start"], ff["end"], ff["n"]))

    cum = lambda c, w: (1 + F[c]).rolling(w).apply(np.prod, raw=True) - 1
    AX = {}
    for c, nm in (("hml", "①가치(HML)"), ("smb", "②소형(SMB)"), ("mom", "③모멘텀(Mom)"),
                  ("rmw", "④수익성(RMW)"), ("cma", "④저투자(CMA)")):
        AX["%s 12개월" % nm] = cum(c, 252) * 100
    AX["⑤시장변동성 21일(연율%)"] = F.mkt_rf.rolling(21).std() * np.sqrt(252) * 100

    # ③ 모멘텀 붕괴 표식 — 시장이 크게 빠진 뒤 모멘텀이 음수인 달
    nav = (1 + F.mkt_rf).cumprod()
    dd = nav / nav.cummax() - 1
    crash = (dd.rolling(504).min() < -0.20) & (cum("mom", 63) < 0)
    AX["③모멘텀 붕괴위험"] = crash.astype(float) * 100

    # ⑥ 금리
    try:
        rt = json.load(io.open(os.path.join(DATA, "rates.json"), encoding="utf-8"))
        ks = [k for k in rt if isinstance(rt[k], dict) or isinstance(rt[k], list)]
        print("   rates.json keys:", list(rt.keys())[:10])
        R = None
        for key in ("series", "rates", "data"):
            if isinstance(rt.get(key), dict):
                R = pd.DataFrame({k: pd.Series(v) for k, v in rt[key].items()})
                break
        if R is None and isinstance(rt.get("dates"), list):
            R = pd.DataFrame({k: v for k, v in rt.items()
                              if isinstance(v, list) and len(v) == len(rt["dates"])},
                             index=pd.to_datetime(rt["dates"]))
        if R is not None:
            R.index = pd.to_datetime(R.index)
            for c in R.columns:
                if "10" in str(c):
                    AX["⑥10년 금리(%)"] = R[c].astype(float)
                    AX["⑥10년 12개월 변화(%p)"] = R[c].astype(float).diff(252)
                    break
            c10 = [c for c in R.columns if "10" in str(c)]
            c2 = [c for c in R.columns if str(c).startswith("2") or "2y" in str(c).lower()]
            if c10 and c2:
                AX["⑥10년−2년(%p)"] = R[c10[0]].astype(float) - R[c2[0]].astype(float)
    except Exception as e:
        print("   ⚠ 금리 축 실패: %s" % e)

    # ⑦ 폭
    try:
        bg = json.load(io.open(os.path.join(DATA, "_breadth_gauge.json"), encoding="utf-8"))
        t = bg["today"]["②지수이긴비율 21일"]
        print("   폭(breadth_gauge) — 지수이긴비율 %.1f%% · 백분위 %.0f"
              % (t["level"], t["pct"]))
    except Exception:
        pass

    print("\n■ 오늘 상태 (각 축의 최근값 · 확장창 백분위)")
    print("   %-24s %12s %10s %s" % ("축", "값", "백분위", "읽는 법"))
    HOW = {"①가치(HML) 12개월": "＋면 가치 우위 · −면 성장 우위",
           "②소형(SMB) 12개월": "＋면 소형 우위 · −면 대형 우위",
           "③모멘텀(Mom) 12개월": "＋면 추세 지속 · −면 반전",
           "④수익성(RMW) 12개월": "＋면 우량 우위",
           "④저투자(CMA) 12개월": "＋면 보수적 투자 우위",
           "⑤시장변동성 21일(연율%)": "높을수록 변동성 국면",
           "③모멘텀 붕괴위험": "100 = 큰 낙폭 뒤 모멘텀 음수",
           "⑥10년 금리(%)": "수준", "⑥10년 12개월 변화(%p)": "＋면 금리 상승 국면",
           "⑥10년−2년(%p)": "−면 역전"}
    today = {}
    for k, v in AX.items():
        v = v.dropna()
        if v.empty:
            continue
        p = pct_exp(v)
        cur = float(v.iloc[-1])
        pc = float(p.iloc[-1]) if p.notna().any() else float("nan")
        today[k] = {"value": cur, "pct": pc, "as_of": str(v.index[-1].date())}
        print("   %-24s %12.2f %9.0f%%  %s" % (k, cur, pc, HOW.get(k, "")))

    print("\n■ 각 국면이 표본에서 얼마나 자주 있었나 (일 기준 · 1963~)")
    for k, v in AX.items():
        v = v.dropna()
        if v.empty or "붕괴" in k:
            continue
        pos = (v > 0).mean() * 100 if v.min() < 0 else np.nan
        print("   %-24s 중앙 %8.2f · 양수 비율 %s · 표본 %d일"
              % (k, v.median(), ("%.0f%%" % pos) if pos == pos else "—", len(v)))
    c = AX.get("③모멘텀 붕괴위험")
    if c is not None:
        print("   %-24s 발동 %.1f%% 의 날" % ("③모멘텀 붕괴위험", c.dropna().mean()))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"as_of": ff["end"], "today": today,
         "note": "국면 분류용 계측. 전환 신호가 아니다 — 랩은 국면 조건부 규칙 10건 중 9건 기각."},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
