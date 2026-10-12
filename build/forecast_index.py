# -*- coding: utf-8 -*-
"""build/forecast_index.py — S&P 500 · 나스닥 100 의 다음 1~5 거래일 수익 분포 · 상승 확률(매일) → data/forecast.json

«다음 주가 흐름» 탭(forecast.html)의 지수 칸. 방법과 검증은 연구 판(표본 밖 2016-10 ~ 2026-09)을
그대로 옮겼고, 이 파일은 그 판을 매일 다시 돌리는 몫만 한다. 검증 숫자는 data/forecast_validation.json
(얼린 기록 · 손으로 굽지 않는다)에 있다.

  M0 기준        : 직전 10년(2,520일) 평균 상승 속도 + HAR 변동성(Corsi 2009) + 표준화 수익의 경험 분위
                   · 상승 확률 = 직전 10년 같은 길이 구간의 상승 빈도
  M1 부스팅 나무 : 일별 특성 17개(가격 · 변동성 · VIX/VXN · 금융 여건 · 달력) → 상승 분류기 + 표준화 수익 분위 나무

🚨 대표(경로 · 방향)는 M0 다. 표본 밖 검증에서 방향(Brier)을 기준보다 낫게 맞힌 방법이 **하나도 없었고**,
   통과한 칸은 «M1 의 1일 분위 손실» 하나뿐이다(두 지평 모두 통과해야 경로 대표가 된다).
   그래서 화면은 M0 경로를 대표로 그리고, M1 은 «내일 범위» 보조로만 쓴다.
⚠ 시계열 기초 모형(Chronos-2)과 그것이 들어가는 단순 결합은 여기서 계산하지 않는다(무거운 의존 · 검증 탈락) —
  화면에는 검증 기록만 나간다.

상황 표시(검증의 «상황별» 표와 같은 정의 · 그날까지 자료만):
  고변동 = VIX(나스닥은 VXN)의 직전 10년 백분위 ≥ 2/3 · 저변동 ≤ 1/3
  급락 뒤 = 5일 로그 수익의 직전 10년 백분위 ≤ 10% · 급등 뒤 ≥ 90%
  추세 아래 = 종가 < 200일 평균
  → 급락 뒤 · 추세 아래 이면 «범위가 좁게 나올 수 있음»(검증: 그런 날 M0 90% 범위가 실제로는 78 ~ 81% 만 담았다).

공개 자료만 쓴다: yfinance(^GSPC · ^NDX · ^VIX · ^VXN) · FRED NFCI(1주 늦춤) · 연준 EBP(2개월 늦춤).
학습은 기준일 종가까지 결과가 끝난 표본만(h일 정화) · 직전 2,520 거래일 · 기준일마다 다시 학습(검증은 매달 말 다시 학습).

  python build/forecast_index.py                    # 마지막 확정 종가 기준
  python build/forecast_index.py --asof 2026-10-09  # 기준일 지정(대조용)
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import math
import os
import sys
import warnings

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "forecast.json")

WIN = 2520
QS = [0.05, 0.25, 0.5, 0.75, 0.95]
QN = ["q05", "q25", "q50", "q75", "q95"]
FEATS = ["r1", "r1l", "r5", "r10", "r20", "lrv5", "lrv21", "lrv63", "vix", "dvix5", "vrp",
         "nfci", "ebp", "dd", "d200", "dow", "eom"]
MKTS = {"spx": {"name": "S&P 500", "px": "^GSPC", "vol": "^VIX", "vol_name": "VIX"},
        "ndx": {"name": "나스닥 100", "px": "^NDX", "vol": "^VXN", "vol_name": "VXN"}}
METHODS = {"M0": "기준(평균 + HAR 변동성)", "M1": "부스팅 나무"}
CLF_KW = dict(max_depth=3, learning_rate=0.05, min_samples_leaf=100, l2_regularization=1.0,
              early_stopping=False, random_state=0)
QR_KW = dict(loss="quantile", max_depth=2, learning_rate=0.05, max_iter=100, min_samples_leaf=200,
             early_stopping=False, random_state=0)


# ───────────────────────── 거래일 달력(뉴욕 증권거래소 정규 휴장) ─────────────────────────
def _easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    da = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(y, mo, da)


def _nth_weekday(y, mo, wd, n):
    d = dt.date(y, mo, 1)
    d += dt.timedelta(days=(wd - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_weekday(y, mo, wd):
    d = dt.date(y, mo + 1, 1) - dt.timedelta(days=1) if mo < 12 else dt.date(y, 12, 31)
    return d - dt.timedelta(days=(d.weekday() - wd) % 7)


def _observed(d, sat_to_fri=True):
    if d.weekday() == 5:
        return d - dt.timedelta(days=1) if sat_to_fri else None
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def nyse_holidays(y):
    hs = [_observed(dt.date(y, 1, 1), sat_to_fri=False), _nth_weekday(y, 1, 0, 3), _nth_weekday(y, 2, 0, 3),
          _easter(y) - dt.timedelta(days=2), _last_weekday(y, 5, 0), _observed(dt.date(y, 6, 19)) if y >= 2022 else None,
          _observed(dt.date(y, 7, 4)), _nth_weekday(y, 9, 0, 1), _nth_weekday(y, 11, 3, 4), _observed(dt.date(y, 12, 25))]
    return {h for h in hs if h is not None}


def next_trading_days(last, n):
    out, d = [], pd.Timestamp(last).date()
    while len(out) < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in nyse_holidays(d.year):
            out.append(pd.Timestamp(d))
    return out


# ───────────────────────── 특성 ─────────────────────────
def on_days(s, idx):
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(idx.union(s.index)).ffill().reindex(idx)


def features(px, vol, nfci, ebp):
    """px: 종가 Series · vol: VIX 또는 VXN(%) · nfci · ebp: 이미 발표 늦춤을 한 Series. 모두 t 종가까지 아는 값."""
    idx = px.index
    lp = np.log(px)
    r = lp.diff()
    X = pd.DataFrame(index=idx)
    X["r1"] = r
    X["r1l"] = r.shift(1)
    for k in (5, 10, 20):
        X["r%d" % k] = lp - lp.shift(k)
    for k in (5, 21, 63):
        X["lrv%d" % k] = np.log(r.rolling(k).std() * math.sqrt(252) + 1e-4)
    v = on_days(vol, idx) / 100.0
    X["vix"] = v
    X["dvix5"] = np.log(v) - np.log(v.shift(5))
    X["vrp"] = v ** 2 - (r.rolling(21).std() * math.sqrt(252)) ** 2
    X["nfci"] = on_days(nfci, idx)
    X["ebp"] = on_days(ebp, idx)
    X["dd"] = lp - np.log(px.rolling(252).max())
    X["d200"] = lp - np.log(px.rolling(200).mean())
    X["dow"] = idx.dayofweek.astype(float)
    cal = pd.DatetimeIndex(list(idx) + next_trading_days(idx[-1], 30))
    s = pd.Series(np.arange(len(cal)), index=cal)
    last_pos = s.groupby(cal.to_period("M")).transform("max")
    X["eom"] = np.minimum(last_pos.values - s.values, 5)[: len(idx)].astype(float)
    return X[FEATS]


def har_x(r):
    r2 = r ** 2
    return pd.DataFrame({"d": r2, "w": r2.rolling(5).mean(), "m": r2.rolling(22).mean()})


# ───────────────────────── M0 ─────────────────────────
def m0_fit(r, pe, h):
    """pe(위치)까지 직전 WIN 일로 HAR 적합.
    돌려줌: b · μ · 정렬된 표준화 z · 상승 빈도 · 창 안 위치별 z(Series, 결과 끝난 날만)."""
    lo = max(0, pe - WIN + 1)
    rr = r.iloc[lo: pe + 1]
    X = har_x(rr)
    y = (rr ** 2)[::-1].rolling(h).mean()[::-1].shift(-1)
    cum = rr[::-1].rolling(h).sum()[::-1].shift(-1)
    ok = X.notna().all(axis=1) & y.notna()
    A = np.column_stack([np.ones(ok.sum()), X[ok].values])
    b, *_ = np.linalg.lstsq(A, y[ok].values, rcond=None)
    fitted = np.clip(A @ b, 1e-10, None)
    mu = float(rr.mean())
    z = pd.Series((cum[ok].values - h * mu) / np.sqrt(h * fitted), index=rr.index[ok.values])
    base = float((cum.dropna() > 0).mean())
    return {"b": b, "mu": mu, "zs": np.sort(z.values[np.isfinite(z.values)]), "base": base, "z": z}


def m0_s2(fit, hx_rows):
    """hx_rows: (n, 3) HAR 특성 → 일평균 분산 예측."""
    A = np.column_stack([np.ones(len(hx_rows)), np.asarray(hx_rows, float)])
    return np.clip(A @ fit["b"], 1e-10, None)


def m0_quant(fit, s2, h):
    qz = np.quantile(fit["zs"], QS)
    return h * fit["mu"] + np.outer(np.sqrt(h * s2), qz)


# ───────────────────────── M1 ─────────────────────────
def m1_dir_fit(Xtr, ytr, h, max_iter=300):
    """앞 80% 적합 · 뒤 20%(h일 띄움) 검증 Brier 최소 단계(0 = 기준 빈도) → 창 전체 다시 적합. None = 기준 빈도."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    n = len(ytr)
    cut = int(0.8 * n)
    fi, va = np.arange(0, cut - h), np.arange(cut, n)
    clf = HistGradientBoostingClassifier(max_iter=max_iter, **CLF_KW).fit(Xtr[fi], ytr[fi])
    yv = ytr[va]
    best_k, best_b = 0, float(np.mean((ytr[fi].mean() - yv) ** 2))
    for k, pr in enumerate(clf.staged_predict_proba(Xtr[va]), 1):
        bs = float(np.mean((pr[:, 1] - yv) ** 2))
        if bs < best_b - 1e-12:
            best_k, best_b = k, bs
    if best_k == 0:
        return None, 0
    return HistGradientBoostingClassifier(max_iter=best_k, **CLF_KW).fit(Xtr, ytr), best_k


def m1_q_fit(Xtr, ztr):
    from sklearn.ensemble import HistGradientBoostingRegressor
    return [HistGradientBoostingRegressor(quantile=q, **QR_KW).fit(Xtr, ztr) for q in QS]


def m1_quant(models, Xp, fit0, s2, h):
    zq = np.sort(np.column_stack([m.predict(Xp) for m in models]), axis=1)
    return h * fit0["mu"] + zq * np.sqrt(h * s2)[:, None]


# ───────────────────────── 공개 자료 내려받기 ─────────────────────────
def _get_csv(url, timeout=60):
    """urllib(브라우저 UA) → 안 되면 curl. 공개 CSV 만."""
    import subprocess
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return pd.read_csv(io.BytesIO(urllib.request.urlopen(req, timeout=timeout).read()))
    except Exception:  # noqa: BLE001
        out = subprocess.run(["curl", "-s", "-L", "-m", str(timeout), url], capture_output=True, check=True).stdout
        return pd.read_csv(io.BytesIO(out))


def _nfci():
    """NFCI(주간) — FRED 공개 CSV → FRED API(키가 있을 때 · FRED_API_KEY) → 시카고 연준 CSV. 값은 같은 계열이다."""
    try:
        nf = _get_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=NFCI").iloc[:, :2]
        nf.columns = ["date", "NFCI"]
        return nf, "FRED 공개 CSV"
    except Exception:  # noqa: BLE001
        pass
    key = os.environ.get("FRED_API_KEY")
    if key:
        try:
            import urllib.request
            u = ("https://api.stlouisfed.org/fred/series/observations?series_id=NFCI&file_type=json&api_key=" + key)
            obs = json.loads(urllib.request.urlopen(u, timeout=60).read().decode("utf-8"))["observations"]
            nf = pd.DataFrame({"date": [o["date"] for o in obs], "NFCI": [o["value"] for o in obs]})
            return nf, "FRED API"
        except Exception:  # noqa: BLE001
            pass
    nf = _get_csv("https://www.chicagofed.org/-/media/publications/nfci/nfci-data-series-csv.csv").iloc[:, :2]
    nf.columns = ["date", "NFCI"]
    return nf, "시카고 연준 CSV"


def load_public(start="2003-01-01"):
    import yfinance as yf
    tk = ["^GSPC", "^NDX", "^VIX", "^VXN"]
    df = yf.download(tk, start=start, auto_adjust=False, progress=False, threads=False)["Close"]
    df = df.dropna(how="all")
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    nf, nf_src = _nfci()
    nf["date"] = pd.to_datetime(nf["date"])
    nfci = pd.Series(pd.to_numeric(nf["NFCI"], errors="coerce").values, index=nf["date"] + pd.Timedelta(days=7))
    eb = _get_csv("https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv")
    eb["date"] = pd.to_datetime(eb["date"])
    ebp = pd.Series(pd.to_numeric(eb["ebp"], errors="coerce").values, index=eb["date"] + pd.DateOffset(months=2))
    return {"px": {"spx": df["^GSPC"].dropna(), "ndx": df["^NDX"].dropna()},
            "vol": {"spx": df["^VIX"].dropna(), "ndx": df["^VXN"].dropna()}, "nfci": nfci, "ebp": ebp,
            "nfci_src": nf_src}


def ny_cut(asof=None):
    """기준일: asof 를 주면 그날까지 · 안 주면 뉴욕 16:30 전 오늘 줄(장중 값)을 뺀다."""
    if asof is not None:
        return pd.Timestamp(asof)
    try:
        from zoneinfo import ZoneInfo
        now = dt.datetime.now(ZoneInfo("America/New_York"))
    except Exception:  # noqa: BLE001
        now = dt.datetime.utcnow() - dt.timedelta(hours=4)
    today = pd.Timestamp(now.date())
    return today - pd.Timedelta(days=1) if (now.hour, now.minute) < (16, 30) else today


def cut_asof(data, asof=None):
    cut = ny_cut(asof)
    for k in ("px", "vol"):
        data[k] = {mk: s[s.index <= cut] for mk, s in data[k].items()}
    return data


# ───────────────────────── 상황(그날까지 자료만) ─────────────────────────
def pct_rank_last(v, win=WIN):
    """마지막 값의 직전 win 일 백분위(자기 포함 · 252개 미만이면 None) — 검증의 pct_rank 와 같은 식."""
    v = np.asarray(v, float)
    if not len(v) or not np.isfinite(v[-1]):
        return None
    w = v[max(0, len(v) - win):]
    w = w[np.isfinite(w)]
    if len(w) < 252:
        return None
    return float(np.mean(w <= v[-1]))


def state_now(px, vol, X):
    idx = px.index
    vv = on_days(vol, idx).values
    vixp = pct_rank_last(vv)
    r5p = pct_rank_last(X["r5"].values)
    d200 = float(X["d200"].values[-1])
    above = bool(d200 >= 0)
    flags = {"고변동": bool(vixp is not None and vixp >= 2 / 3), "저변동": bool(vixp is not None and vixp <= 1 / 3),
             "급락 뒤": bool(r5p is not None and r5p <= 0.10), "급등 뒤": bool(r5p is not None and r5p >= 0.90),
             "추세 아래": not above, "추세 위": above}
    return {"date": idx[-1].strftime("%Y-%m-%d"),
            "vol": round(float(vv[-1]), 2), "vol_pct": None if vixp is None else round(vixp * 100, 1),
            "r5_pct": None if r5p is None else round(r5p * 100, 1),
            "r5": round(float(np.expm1(X["r5"].values[-1])) * 100, 2),
            "d200": round(float(np.expm1(d200)) * 100, 2),
            "flags": flags,
            # 검증에서 M0 90% 범위가 실제로 덜 담은 두 상황(78 ~ 81%) — 화면의 «좁게 나올 수 있음» 표시
            "narrow": bool(flags["급락 뒤"] or flags["추세 아래"])}


# ───────────────────────── 최신 예측 ─────────────────────────
def forecast_market(px, vol, nfci, ebp, H=5):
    """기준일 = px 마지막 날. 돌려줌: 방법별 {h: 분위(5)} · {1, 5: 상승 확률} · 정보."""
    px = px.dropna()
    lp = np.log(px)
    r = lp.diff()
    n = len(px)
    pe = n - 1
    HX = har_x(r)
    X = features(px, vol, nfci, ebp)
    Xv = X.values
    Q = {"M0": {}, "M1": {}}
    P = {"M0": {}, "M1": {}}
    info = {}
    for h in range(1, H + 1):
        f0 = m0_fit(r, pe, h)
        s2 = m0_s2(f0, HX.iloc[[pe]].values)
        Q["M0"][h] = m0_quant(f0, s2, h)[0]
        lo, hi = max(0, pe - WIN + 1), pe - h
        tr = np.arange(lo, hi + 1)
        zpos = px.index.get_indexer(f0["z"].index)
        Q["M1"][h] = m1_quant(m1_q_fit(Xv[zpos], f0["z"].values), Xv[[pe]], f0, s2, h)[0]
        if h in (1, 5):
            P["M0"][h] = f0["base"]
            cum = (lp.shift(-h) - lp).values
            ytr = (cum[tr] > 0).astype(float)
            clf, k = m1_dir_fit(Xv[tr], ytr, h)
            P["M1"][h] = float(clf.predict_proba(Xv[[pe]])[0, 1]) if clf is not None else f0["base"]
            info["%dd" % h] = int(k)
    return Q, P, info, X


def build(data):
    out = {"note": "다음 주가 흐름(forecast.html)의 지수 칸 — build/forecast_index.py 가 매 거래일 굽는다. "
                   "대표 경로 · 방향은 기준(M0)이고 부스팅 나무(M1)는 «내일 범위» 보조다(표본 밖 검증에서 방향을 기준보다 "
                   "낫게 맞힌 방법이 없었다). 검증 숫자는 data/forecast_validation.json.",
           "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "as_of": None,
           "source": "yfinance(^GSPC · ^NDX · ^VIX · ^VXN 종가) · NFCI(%s · 1주 늦춤) · 연준 EBP(2개월 늦춤)"
                     % data.get("nfci_src", "FRED"),
           "methods": dict(METHODS), "rep": "M0", "rep_dir": "M0", "aux_1d": "M1", "markets": {}}
    for mk, meta in MKTS.items():
        px = data["px"][mk].dropna()
        Q, P, info, X = forecast_market(px, data["vol"][mk], data["nfci"], data["ebp"])
        last = float(px.iloc[-1])
        nd = next_trading_days(px.index[-1], 5)
        paths = {m: {qn: [round(last * math.exp(float(Q[m][h][i])), 2) for h in range(1, 6)]
                     for i, qn in enumerate(QN)} for m in Q}
        st = state_now(px, data["vol"][mk], X)
        st["vol_name"] = meta["vol_name"]
        rec = px.iloc[-21:]                                  # 그림 앞부분 — 최근 20거래일 + 기준일 실제 종가
        out["markets"][mk] = {
            "name": meta["name"], "last": round(last, 2), "last_date": px.index[-1].strftime("%Y-%m-%d"),
            "recent": [[d.strftime("%Y-%m-%d"), round(float(v), 2)] for d, v in rec.items()],
            "next_dates": [d.strftime("%Y-%m-%d") for d in nd], "path": paths["M0"], "paths": paths,
            "p_up": {"1d": {m: round(P[m][1] * 100, 2) for m in P}, "5d": {m: round(P[m][5] * 100, 2) for m in P}},
            "m1_trees": info, "state": st}
        out["as_of"] = px.index[-1].strftime("%Y-%m-%d") if out["as_of"] is None else min(out["as_of"], px.index[-1].strftime("%Y-%m-%d"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None, help="기준일 YYYY-MM-DD(없으면 마지막 확정 종가)")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    data = cut_asof(load_public(), a.asof)
    res = build(data)
    # 두 시장의 기준일이 다르면 멈춘다 — 한 화면이 두 날짜를 말하게 두지 않는다
    lds = {v["last_date"] for v in res["markets"].values()}
    if len(lds) != 1:
        raise SystemExit("🚨 두 지수의 마지막 종가 날짜가 다르다 %s — 원천이 하루 덜 들어왔다. 쓰지 않는다" % sorted(lds))
    txt = json.dumps(res, ensure_ascii=False, indent=1) + "\n"
    # ⚠ 기본 경로는 «open(OUT, "w"» 꼴로 쓴다 — build/audit_unbuilt.py 가 이 꼴로 산출물을 알아보고
    #   «굽는 잡 · 읽는 화면» 배선을 감사한다. LF 고정(Windows 에서 돌려도 CRLF 로 안 바뀐다).
    if os.path.abspath(a.out) == os.path.abspath(OUT):
        with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)
    else:
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)
    for mk, v in res["markets"].items():
        print("%s %s %.2f · 5일 뒤 중앙 %.2f · 90%% %.2f ~ %.2f · 5일 상승 확률(기준) %.2f%% · 상황 %s"
              % (v["name"], v["last_date"], v["last"], v["path"]["q50"][-1], v["path"]["q05"][-1], v["path"]["q95"][-1],
                 v["p_up"]["5d"]["M0"], " · ".join(k for k, f in v["state"]["flags"].items() if f)))


if __name__ == "__main__":
    main()
