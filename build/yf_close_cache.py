# -*- coding: utf-8 -*-
"""같은 잡 안에서 같은 지수 종가를 두 번 받지 않게 하는 캐시 (2026-11-20).

예측 잡(refresh-forecast)은 forecast_index · forecast_rl · forecast_stocks 를 차례로 부르는데,
셋이 ^GSPC · ^NDX 를 2003-01 부터 **각자** 받고 있었다. 셋 다 auto_adjust=False 종가(Close)라
한 번 받아 러너 임시 폴더에 두고 나머지는 거기서 읽는다. 캐시는 그날 그 러너 안에서만 산다
(저장소에 안 남는다 — 커밋되는 두 번째 가격 원천을 만들지 않는다).

    from yf_close_cache import closes
    df = closes(["^GSPC", "^NDX"], start="2003-01-01")   # 열 = 티커, 값 = Close
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd

BASE = "2003-01-01"          # 셋이 쓰는 가장 이른 시작일. 이보다 늦은 start 는 잘라서 준다.
DIR = os.path.join(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "yf_close_cache")


def _path(t: str) -> str:
    return os.path.join(DIR, "%s_%s.pkl" % (t.replace("^", "IDX_").replace("/", "_"), dt.date.today().isoformat()))


def closes(tickers, start: str = BASE) -> pd.DataFrame:
    import yfinance as yf
    os.makedirs(DIR, exist_ok=True)
    tickers = [tickers] if isinstance(tickers, str) else list(tickers)
    need = [t for t in tickers if not os.path.exists(_path(t))]
    if need:
        df = yf.download(need, start=min(BASE, start), auto_adjust=False, progress=False, threads=False)["Close"]
        if isinstance(df, pd.Series):
            df = df.to_frame(need[0])
        if getattr(df.index, "tz", None) is not None:
            df.index = df.index.tz_localize(None)
        for t in need:
            if t in df.columns and df[t].notna().any():
                df[t].dropna().to_pickle(_path(t))
        print("  [종가 캐시] 새로 받음 %s" % ", ".join(need))
    hit = [t for t in tickers if t not in need]
    if hit:
        print("  [종가 캐시] 다시 받지 않고 재사용 %s" % ", ".join(hit))
    out = pd.DataFrame({t: pd.read_pickle(_path(t)) for t in tickers if os.path.exists(_path(t))})
    out.index = pd.to_datetime(out.index)
    return out[out.index >= pd.Timestamp(start)].sort_index()
