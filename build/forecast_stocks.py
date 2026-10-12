# -*- coding: utf-8 -*-
"""build/forecast_stocks.py — 기계학습 종목 단면 순위(다음 5거래일 수익이 같은 지수 구성 종목 중앙값보다 클까) → data/forecast_stocks.json

«다음 주가 흐름» 탭(forecast.html)의 종목 순위 칸. 방법은 연구 판(표본 밖 2016-10 ~ 2026-09)을 그대로 옮겼다 —
Krauss · Do · Huck (2017) 틀:
  특성 31개 R(m) = P_t / P_{t−m} − 1, m ∈ {1..20} ∪ {40, 60, …, 240}
  목표 = 다음 5거래일 수익 > 그날 자격 종목 중앙값
  학습 = 목표가 기준일 종가까지 끝난 직전 750거래일 · 그날 그날의 시점 정확 회원만(앞 달 말 명단)
  모형 = 랜덤 포레스트(100그루 · 깊이 20 · 5 특성 · 표본 반) · 부스팅 나무(100번 · 깊이 3) · 작은 신경망(31-10-5)
         세 확률의 평균(ENS) — 설정은 연구 판과 같다(고정)

이 판이 연구 판과 다른 것 — 자료뿐이다.
  · 회원 = 위키백과 지수 목록의 과거 리비전(data/index_history.json · 월말 · 이중클래스는 회사당 하나 ·
    날짜 인식 별칭은 build/pit_alias.py) — build/pit_panel.py 의 _key · _dedup_cik 를 그대로 쓴다(사본을 두지 않는다)
  · 가격 = 오늘 유니버스 data/sd(수정 종가) + 편출 정리본 data/pit_px.json(격리 반영) — 날짜로 맞춘다
  · 연구 판 검증 숫자(AUC 0.5047 등)는 연구 판 자료에서 잰 것이다 — data/forecast_validation.json
  · 매 실행 직전 750거래일로 다시 학습한다(검증은 250거래일마다 다시 학습했다)

🚨 판정: 쓸 만한 판이 없다. 날마다 단면 AUC 0.5047(5일) 로 예측력은 있으나 아주 작고, 회전 비용 뒤 펀드 틀
   (지수 90% + 상위 30종목 10%)을 못 넘었다. 확률 숫자는 보정되지 않았다(확률 0.65 여도 과거 상위 20 의 적중은
   50.56%) — 그래서 **순위만** 싣고 확률은 싣지 않는다. 감시용 참고 순위이고 매매 신호가 아니다.

상태(그날까지 자료만 · 연구 판과 같은 정의): 급락 = 지수 252일 고점 대비 −10% 이하 ·
  급등 = 63일 수익이 2003년부터 그날까지 80 백분위 이상 · 고변동성 = 21일 실현 변동성이 그날까지 80 백분위 이상.
  S&P 500 은 총수익 지수(^SP500TR), 나스닥 100 은 가격 지수(^NDX).

  python build/forecast_stocks.py                     # data/stocks.json 의 기준일
  python build/forecast_stocks.py --asof 2026-10-08   # 기준일 지정(그날 이전 격자만 쓴다)
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys
import time
import warnings

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_alias as PA            # noqa: E402  날짜 인식 별칭 · 명단 고치기
import pit_panel as PP            # noqa: E402  _key · _dedup_cik · KEEP_DUAL · mshift(사본을 두지 않는다)
import pit_quarantine as PQ       # noqa: E402  격리 명단

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "forecast_stocks.json")

LAGS = list(range(1, 21)) + list(range(40, 241, 20))     # 31개(원문 식 1)
H = 5
TRAIN_DAYS = 750
MAX_GAP = 5
N_TOP = 20
CARRY_MAX = 2                                            # 명단 지도 끝 뒤 이월 한도(build/index_members.at 과 같은 값)
UNIVERSES = {"spx": {"name": "S&P 500", "state_tick": "^SP500TR", "state_label": "S&P 500 총수익 지수"},
             "ndx": {"name": "나스닥 100", "state_tick": "^NDX", "state_label": "나스닥 100 가격 지수"}}


def _j(fn):
    with io.open(os.path.join(DATA, fn), encoding="utf-8") as fh:
        return json.load(fh)


# ══ 자료 ═══════════════════════════════════════════════════════════════════
def load_world(asof=None):
    """오늘 유니버스 sd + 편출 정리본 pit_px 를 stocks.json 격자 위에 날짜로 맞춘다 · 월말 명단 · 별칭 표."""
    S = _j("stocks.json")
    dates = list(S["pxd_dates"])
    if asof:
        dates = [d for d in dates if d <= asof]
    D = len(dates)
    gi = {d: i for i, d in enumerate(dates)}
    info = {s["t"]: {"name": s.get("name"), "sector": s.get("sector")} for s in S["stocks"]}
    PX = {}
    for t in info:
        with io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8") as fh:
            p = (json.load(fh).get("pxd") or [])[:D]
        a = np.full(D, np.nan)
        a[:len(p)] = [np.nan if v is None else float(v) for v in p]
        PX[t] = a
    pit = _j("pit_px.json")
    pmap = np.array([gi.get(d, -1) for d in pit["dates"]])         # 편출 격자 → 랩 격자(없는 날은 버린다)
    quarantine = set(PQ.names())
    for t, obj in (pit.get("px") or {}).items():
        if t in PX or t in quarantine:
            continue
        a = np.full(D, np.nan)
        i0, arr = int(obj.get("i0") or 0), obj.get("p") or []
        for j, v in enumerate(arr):
            if v is None or not (0 <= i0 + j < len(pmap)):
                continue
            k = pmap[i0 + j]
            if k >= 0:
                a[k] = float(v)
        PX[t] = a
    Hh = _j("index_history.json")
    lists = {"spx": {}, "ndx": {}}
    last = {"spx": [], "ndx": []}
    for m in sorted(Hh["months"]):
        row = Hh["months"][m] or {}
        for ix in ("spx", "ndx"):
            if row.get(ix):
                last[ix] = [x.replace(".", "-") for x in row[ix]]
            lists[ix][m] = list(last[ix])
    PA.fix_lists(lists)
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i                                             # 그달 마지막 거래일 위치
    meta = (_j("index_ledger.json").get("meta") or {})
    return {"dates": dates, "D": D, "PX": PX, "info": info, "meta": meta, "lists": lists, "me": me,
            "splice": _j("pit_universe.json").get("cik_spliced") or {},
            "reassigned": _j("pit_reuse.json").get("reassigned") or {},
            "cikmap": Hh.get("cik") or {}, "hist_as_of": Hh.get("as_of"), "stocks_as_of": S.get("as_of")}


def list_at(W, ix, mm):
    """월 키 mm 의 명단 — 지도 끝 뒤는 CARRY_MAX 달까지 이월(build/index_members.at 규칙) · 그 밖은 멈춘다."""
    L = W["lists"][ix]
    if L.get(mm):
        return list(L[mm]), None
    keys = sorted(k for k, v in L.items() if v)
    if not keys or mm < keys[0]:
        return [], None
    lk = keys[-1]
    gap = (int(mm[:4]) * 12 + int(mm[5:7])) - (int(lk[:4]) * 12 + int(lk[5:7]))
    if gap <= 0:
        return [], None
    if gap > CARRY_MAX:
        raise SystemExit("🚨 %s 명단 지도가 %s 에서 멈췄는데 %s 을 찾는다(%d달 차) — 이월 한도 %d달을 넘었다. "
                         "묵은 명단으로 순위를 내지 않는다(build/refresh_index_history.py 가 왜 안 도는지 볼 것)"
                         % (ix, lk, mm, gap, CARRY_MAX))
    return list(L[lk]), lk


def month_members(W, ix, mm):
    """앞 달 말(mm) 명단 → [(명단 티커, 가격 키)] — pit_panel.month_rows 와 같은 규칙(이중클래스 회사당 하나 ·
    재배정 티커의 마지막 멤버월 제외 · 날짜 인식 키). 돌려줌 (목록, 이월한 원래 달)."""
    mem, carried = list_at(W, ix, mm)
    i = W["me"].get(mm)
    if i is None:
        i = W["me"].get(carried) if carried else None
    if i is None or not mem:
        return [], carried
    by_cik = {}
    for t in mem:
        c = PP._dedup_cik(W, t, i)
        by_cik.setdefault(c or ("_" + t), []).append(t)
    keep = []
    for c, ts in by_cik.items():
        if len(ts) == 1 or c.startswith("_"):
            keep.extend(ts)
            continue
        k_ = [t for t in ts if t in PP.KEEP_DUAL]
        keep.append(k_[0] if k_ else sorted(ts)[0])
    out = []
    for t in sorted(keep):
        if t in W["reassigned"] and mm >= W["reassigned"][t].get("last", "9999"):
            continue
        k = PP._key(W, t, i)
        if k is not None:
            out.append((t, k))
    return out, carried


def panel(W, ix, t_lo, t_hi):
    """격자 [t_lo, t_hi] 의 회원 행렬 · 가격 행렬. 날 t 의 우주 = t 가 속한 달의 앞 달 말 명단(시점 정확)."""
    dates = W["dates"]
    months = sorted({d[:7] for d in dates[t_lo:t_hi + 1]})
    mem_by_month, carried = {}, {}
    keys, kidx, tick_of = [], {}, {}
    for Mo in months:
        mm = PP.mshift(Mo, -1)
        lst, cr = month_members(W, ix, mm)
        if cr:
            carried[mm] = cr
        mem_by_month[Mo] = lst
        for t, k in lst:
            if k not in kidx:
                kidx[k] = len(keys)
                keys.append(k)
            tick_of[k] = t
    T, K = t_hi - t_lo + 1, len(keys)
    Mb = np.zeros((T, K), bool)
    mo_arr = np.array([d[:7] for d in dates[t_lo:t_hi + 1]])
    for Mo, lst in mem_by_month.items():
        rows = np.where(mo_arr == Mo)[0]
        cols = [kidx[k] for _, k in lst]
        if len(rows) and cols:
            Mb[np.ix_(rows, cols)] = True
    P = np.full((T, K), np.nan)
    for k, j in kidx.items():
        P[:, j] = W["PX"][k][t_lo:t_hi + 1]
    return Mb, P, keys, tick_of, carried


def logprice(P):
    """log P · 안쪽 빈 날은 직전 값(첫 값 앞 · 마지막 값 뒤는 빈 값 그대로)."""
    LP = np.log(np.where(P > 0, P, np.nan))
    T, K = LP.shape
    fin = np.isfinite(LP)
    has = fin.any(0)
    first = np.where(has, fin.argmax(0), T)
    last = np.where(has, T - 1 - fin[::-1].argmax(0), -1)
    idx = np.where(fin, np.arange(T)[:, None], 0)
    np.maximum.accumulate(idx, axis=0, out=idx)
    LPf = LP[idx, np.arange(K)[None, :]]
    rows = np.arange(T)[:, None]
    LPf[(rows < first[None, :]) | (rows > last[None, :])] = np.nan
    return LPf, fin


def eligible(Mb, LP, fin):
    """회원 · 그날과 전날 가격 있음 · P_{t−240} 있음 · 지난 240일 빈 날 ≤ 5(연구 판 eligible 과 같은 뜻)."""
    T, K = LP.shape
    prev = np.zeros_like(fin)
    prev[1:] = fin[:-1]
    c = np.cumsum(~fin, axis=0)
    gap = np.full((T, K), 10 ** 6)
    gap[240:] = c[240:] - c[:-240]
    back = np.zeros_like(fin)
    back[240:] = np.isfinite(LP[:-240])
    return Mb & fin & prev & np.isfinite(LP) & back & (gap <= MAX_GAP)


def feats(LP, t, j):
    return np.stack([np.expm1(LP[t, j] - LP[t - m, j]) for m in LAGS], axis=1)


def train_set(LP, E, Y, rows, min_n=20):
    Xs, ys, nd = [], [], 0
    for t in rows:
        if t < 240:
            continue
        S = E[t] & np.isfinite(Y[t])
        if S.sum() < min_n:
            continue
        j = np.where(S)[0]
        y = Y[t, j]
        Xs.append(feats(LP, t, j))
        ys.append((y > np.median(y)).astype(np.int8))
        nd += 1
    X = np.vstack(Xs).astype(np.float32)
    if not np.isfinite(X).all():
        raise SystemExit("🚨 학습 특성에 빈 값이 있다 — 자격 판정과 가격 행렬이 어긋났다")
    return X, np.concatenate(ys), nd


# ══ 모형(연구 판 설정 · 고정) ════════════════════════════════════════════════
def fit_models(X, y, n_jobs):
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.neural_network import MLPClassifier
    out, secs = {}, {}
    t0 = time.time()
    out["rf"] = RandomForestClassifier(n_estimators=100, max_depth=20, max_features=5, max_samples=0.5, n_jobs=n_jobs,
                                       random_state=1).fit(X, y)
    secs["rf"] = round(time.time() - t0, 1)
    t0 = time.time()
    out["gb"] = HistGradientBoostingClassifier(max_iter=100, max_depth=3, learning_rate=0.1, max_features=0.5,
                                               early_stopping=False, random_state=1).fit(X, y)
    secs["gb"] = round(time.time() - t0, 1)
    t0 = time.time()
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[~(sd > 0)] = 1.0
    out["mu"], out["sd"] = mu, sd
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out["nn"] = MLPClassifier(hidden_layer_sizes=(31, 10, 5), activation="relu", alpha=1e-5, solver="adam", batch_size=1024,
                                  max_iter=50, early_stopping=True, validation_fraction=0.1, n_iter_no_change=5,
                                  random_state=1).fit(np.clip((X - mu) / sd, -5, 5), y)
    secs["nn"] = round(time.time() - t0, 1)
    out["secs"] = secs
    return out


def predict(Mo, X):
    p = (Mo["rf"].predict_proba(X)[:, 1] + Mo["gb"].predict_proba(X)[:, 1] +
         Mo["nn"].predict_proba(np.clip((X - Mo["mu"]) / Mo["sd"], -5, 5))[:, 1]) / 3.0
    return p.astype(float)


# ══ 상태(그날까지 자료만) ══════════════════════════════════════════════════
def fetch_state_series(asof):
    import pandas as pd
    import yfinance as yf
    out = {}
    for mk, u in UNIVERSES.items():
        df = yf.download(u["state_tick"], start="2003-01-01", auto_adjust=False, progress=False, threads=False)
        c = df["Close"]
        if isinstance(c, pd.DataFrame):
            c = c.iloc[:, 0]
        c.index = pd.to_datetime(c.index).tz_localize(None) if getattr(c.index, "tz", None) is not None else pd.to_datetime(c.index)
        c = c.dropna()
        out[mk] = c[c.index <= pd.Timestamp(asof)]
    return out


def state_now(s):
    """연구 판 states 와 같은 정의 · 마지막 날 값."""
    import numpy as _np
    s = s[_np.isfinite(s) & (s > 0)]
    dd = s / s.rolling(252, min_periods=252).max() - 1
    r63 = s / s.shift(63) - 1
    q63 = r63.expanding(min_periods=252).quantile(0.8)
    v21 = _np.log(s).diff().rolling(21).std() * _np.sqrt(252)
    qv = v21.expanding(min_periods=252).quantile(0.8)
    d = s.index[-1]
    return {"date": d.strftime("%Y-%m-%d"), "crash": bool(dd[d] <= -0.10), "surge": bool(r63[d] >= q63[d]),
            "highvol": bool(v21[d] >= qv[d]), "drawdown_252d_pct": round(float(dd[d] * 100), 2),
            "ret_63d_pct": round(float(r63[d] * 100), 2), "ret_63d_p80_pct": round(float(q63[d] * 100), 2),
            "vol_21d_pct": round(float(v21[d] * 100), 2), "vol_21d_p80_pct": round(float(qv[d] * 100), 2)}


# ══ 순위 ═══════════════════════════════════════════════════════════════════
def rank_universe(W, ix, n_jobs):
    tA = W["D"] - 1
    t_lo = max(0, tA - (TRAIN_DAYS + H + 240 + 10))
    Mb, P, keys, tick_of, carried = panel(W, ix, t_lo, tA)
    LP, fin = logprice(P)
    E = eligible(Mb, LP, fin)
    T = LP.shape[0]
    Y = np.full_like(LP, np.nan)
    Y[:-H] = np.expm1(LP[H:] - LP[:-H])
    tz = T - 1
    rows = np.arange(tz - H - TRAIN_DAYS + 1, tz - H + 1)        # 목표가 기준일 종가까지 끝난 750일
    X, y, nd = train_set(LP, E, Y, rows)
    Mo = fit_models(X, y, n_jobs)
    j = np.where(E[tz])[0]
    if len(j) < 40:
        raise SystemExit("🚨 %s 기준일 자격 종목이 %d 개뿐 — 명단 · 가격을 확인할 것" % (ix, len(j)))
    p = predict(Mo, feats(LP, tz, j).astype(np.float32))
    tk = [tick_of[keys[c]] for c in j]
    order = sorted(range(len(j)), key=lambda q: (-p[q], tk[q]))
    n = len(j)

    def row(q, rank):
        t = tk[q].replace("-", ".")
        k = keys[j[q]]
        inf = W["info"].get(k) or W["info"].get(t) or {}
        m = W["meta"].get(tk[q]) or W["meta"].get(t) or []
        return {"rank": rank, "ticker": t, "name": inf.get("name") or (m[0] if m else None),
                "sector": inf.get("sector") or (m[1] if len(m) > 1 else None),
                "lab": bool(k in W["info"])}                     # 오늘 랩 유니버스(data/stocks.json) 안 — 화면이 종목 정보로 잇는다

    top = [row(q, r + 1) for r, q in enumerate(order[:N_TOP])]
    bot = [row(q, n - r) for r, q in enumerate(order[::-1][:N_TOP])]
    n_list = len(month_members(W, ix, PP.mshift(W["dates"][tA][:7], -1))[0])
    return {"name": UNIVERSES[ix]["name"], "horizon_days": H, "n_ranked": int(n), "n_members": int(n_list),
            "members_month": PP.mshift(W["dates"][tA][:7], -1), "members_carried": carried or None,
            "top": top, "bottom": bot,
            "train": {"n_samples": int(len(y)), "n_days": int(nd), "from": W["dates"][t_lo + int(rows[0])],
                      "to": W["dates"][t_lo + int(rows[-1])], "secs": Mo["secs"]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None, help="기준일 YYYY-MM-DD(없으면 data/stocks.json 의 기준일)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 1))
    a = ap.parse_args()
    W = load_world(a.asof)
    asof = W["dates"][-1]
    out = {"note": "다음 주가 흐름(forecast.html)의 종목 순위 칸 — build/forecast_stocks.py 가 매 거래일 굽는다. "
                   "순위만 싣는다(확률은 보정되지 않아 싣지 않는다). 감시용 참고 순위이고 매매 신호가 아니다 — "
                   "표본 밖 검증에서 회전 비용 뒤 펀드 틀을 못 넘었다(data/forecast_validation.json).",
           "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "as_of": asof,
           "source": "가격 data/sd(오늘 유니버스 · 수정 종가) + data/pit_px.json(편출 정리본) · 회원 data/index_history.json"
                     "(위키백과 지수 목록 과거 리비전 · 앞 달 말 명단) · 상태 yfinance(^SP500TR · ^NDX)",
           "members_as_of": W["hist_as_of"], "universes": {}}
    try:
        SS = fetch_state_series(asof)
    except Exception as e:  # noqa: BLE001
        SS = {}
        print("  ⚠ 상태 계열을 받지 못했다(%s) — 상태 칸은 비운다" % str(e)[:80])
    for ix in UNIVERSES:
        t0 = time.time()
        u = rank_universe(W, ix, a.jobs)
        s = SS.get(ix)
        u["state"] = state_now(s) if s is not None and len(s) > 300 else None
        if u["state"] is not None:
            u["state"]["series"] = UNIVERSES[ix]["state_label"]
            if u["state"]["date"] != asof:
                u["state"]["note"] = "지수 상태 날짜(%s)가 순위 기준일(%s)과 다르다" % (u["state"]["date"], asof)
        out["universes"][ix] = u
        print("%s 기준 %s · 순위 %d 종목(명단 %d) · 학습 %d 표본(%d일 %s ~ %s) · %.0f초 · 상위 %s · 하위 %s"
              % (u["name"], asof, u["n_ranked"], u["n_members"], u["train"]["n_samples"], u["train"]["n_days"],
                 u["train"]["from"], u["train"]["to"], time.time() - t0,
                 " · ".join(x["ticker"] for x in u["top"][:5]), " · ".join(x["ticker"] for x in u["bottom"][:5])),
              flush=True)
    txt = json.dumps(out, ensure_ascii=False, indent=1) + "\n"
    # ⚠ 기본 경로는 «open(OUT, "w"» 꼴로 쓴다 — build/audit_unbuilt.py 가 이 꼴로 산출물을 알아보고
    #   «굽는 잡 · 읽는 화면» 배선을 감사한다. LF 고정(Windows 에서 돌려도 CRLF 로 안 바뀐다).
    if os.path.abspath(a.out) == os.path.abspath(OUT):
        with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)
    else:
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)


if __name__ == "__main__":
    main()
