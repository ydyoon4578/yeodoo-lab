# -*- coding: utf-8 -*-
"""web/build/refresh_live.py — 클라우드 안전(yfinance·무DB) 라이브 데이터 갱신
================================================================================
GitHub Actions 크론에서 실행. 사내 DB 없이 yfinance만으로 갱신 가능한 부분을 산출:
  · 크로스에셋 RP 슬리브의 현재 배분(CORE12 역변동성 + 추세게이트 + vol타겟10%)
  · 벤치마크 최신 레벨(NDX=QQQ, SPX=SPY) 및 YTD
  · as_of 타임스탬프
→ web/data/live.json 으로 저장(사이트가 fetch해 '라이브' 표시·RP 배분 갱신).

챔피언 보유·통합 배분(Sharpe 1.42 등)은 FactSet DB가 필요해 여기서 갱신하지 않음 —
월별 로컬/셀프호스티드 갱신 담당(README 참조). 배포 스펙과 동일 로직(rp_sleeve).
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd

CORE = ["SPY", "QQQ", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "UUP", "HYG", "LQD", "VNQ"]
RISKY = {"SPY", "QQQ", "EFA", "EEM", "DBC", "VNQ"}
NAMES = {"HYG": "하이일드 회사채", "UUP": "미국달러(강세)", "IEF": "미국채 7–10년", "LQD": "투자등급 회사채",
         "TLT": "미국채 20년+", "SPY": "S&P 500", "VNQ": "미국 리츠", "EFA": "선진국 주식(미국外)",
         "DBC": "원자재 바스켓", "QQQ": "나스닥 100", "GLD": "금", "EEM": "신흥국 주식"}
ANN = 252
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "live.json")


def fetch(tickers, period="3y"):
    import yfinance as yf
    df = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0] if isinstance(tickers, list) else tickers)
    return df.reindex(pd.bdate_range(df.index.min(), df.index.max())).ffill().dropna(how="all")


def rp_allocation(px, tvol=0.10):
    px = px[CORE].dropna(how="all")
    r = px.pct_change()
    pxm = px.resample("ME").last()
    vol60 = r.rolling(60).std().resample("ME").last()
    tr = pxm / pxm.shift(12) - 1
    d = pxm.index[-1]
    iv = (1 / vol60.loc[d]).dropna()
    g = tr.loc[d].reindex(iv.index)
    keep = iv[(g > 0) | (~iv.index.isin(RISKY))]
    w = (keep / keep.sum()).sort_values(ascending=False)
    # vol타겟 레버(최근 30일 실현변동성 기준)
    wd = w.reindex(px.columns).fillna(0.0)
    port = (wd * r).sum(axis=1)
    lev = float(np.clip(tvol / (port.rolling(30).std().iloc[-1] * np.sqrt(ANN)), 0.3, 2.5))
    return w, lev


def main():
    try:
        px = fetch(CORE + ["SPY", "QQQ"])
        w, lev = rp_allocation(px)
        as_of = str(px.index.max().date())
        # 벤치마크 YTD
        def ytd(t):
            s = px[t].dropna()
            yr = s[s.index.year == s.index[-1].year]
            return round((s.iloc[-1] / yr.iloc[0] - 1) * 100, 1) if len(yr) > 1 else None
        out = dict(
            as_of=as_of, source="github-actions (yfinance)", scope="rp_sleeve + benchmarks",
            rp_leverage=round(lev, 2),
            rp_weights=[dict(ticker=t, name=NAMES.get(t, t), weight=round(float(w[t]) * 100, 1))
                        for t in w.index],
            benchmarks=dict(NDX_ytd=ytd("QQQ"), SPX_ytd=ytd("SPY")),
            note="챔피언·통합 배분(1.42)은 FactSet DB 필요 — 월별 로컬 갱신. 이 파일은 RP·벤치마크만.",
        )
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
        print(f"live.json 갱신: as_of {as_of} · RP {len(w)}종목 · 레버 {lev:.2f}x")
    except Exception as e:
        print(f"refresh 실패(기존 live.json 유지): {e}", file=sys.stderr)
        sys.exit(0)  # 실패해도 파이프라인 중단 안 함(기존 스냅샷 유지)


if __name__ == "__main__":
    main()
