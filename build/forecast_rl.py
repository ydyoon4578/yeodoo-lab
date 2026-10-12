# -*- coding: utf-8 -*-
"""build/forecast_rl.py — 강화학습 에이전트의 다음 거래일 지수 비중(S&P 500 · 나스닥 100) → data/forecast_rl.json

«다음 주가 흐름» 탭(forecast.html)의 강화학습 칸. 학습은 하지 않는다 — 연구 판에서 옮긴 운용 접힘 모형
(build/forecast_model/rl_*.npz · 깊은 Q 학습 · 씨앗 10개)으로 그날 종가까지의 상태를 넣어 행동만 낸다.

  · 상태(Zhang · Zohren · Roberts 2020): 지난 1 · 21 · 42 · 63 · 126 · 252일 수익 ÷ (σ_t √h) ·
    이동평균 수렴 · 확산(MACD) 세 쌍 · 상대강도지수(RSI, 30일) + 직전 행동
  · 행동 {−1, 0, 1}(씨앗 10개 평균) × 변동성 배수 s = min(1, 직전 10년 변동성 중앙 ÷ 지금 변동성) = 비중
  · 결정 = 종가 t · 체결 = 다음 거래일 종가

🚨 검증(표본 밖 2016-10 ~ 2026-09, 판정 대상 12판)에서 **모두 못 넘었다** — 사서 들고 있기 · 변동성 맞춤 매수를
   못 이겼고(Holm p 최소 0.66), 다음 5일 방향 맞힘(59.57% · 60.61%)이 같은 날 «늘 오름»(61.68% · 63.25%)보다 낮다.
   이 비중은 «에이전트 자세» 이며 예측치도 매매 신호도 아니다. 검증 숫자는 data/forecast_validation.json.

  python build/forecast_rl.py                    # 마지막 확정 종가 기준
  python build/forecast_rl.py --asof 2026-10-09  # 기준일 지정(대조용)
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
MODEL_DIR = os.path.join(HERE, "forecast_model")
OUT = os.path.join(DATA, "forecast_rl.json")

H_RET = (1, 21, 42, 63, 126, 252)
PAIRS = ((8, 24), (16, 48), (32, 96))
NAMES = {"spx": "S&P 500", "ndx": "나스닥 100"}
TICK = {"spx": "^GSPC", "ndx": "^NDX"}
LABELS = {"M1": "직접 강화학습", "M2": "깊은 Q 학습", "M1_V1": "직접 강화학습 롱 · 현금", "M2_V1": "깊은 Q 학습 롱 · 현금"}


# ── 자료 ─────────────────────────────────────────────────────────────────────
def fetch_public(start="2003-01-01"):
    """yfinance 종가 ^GSPC · ^NDX(2003-01 부터 — 지수 이동평균의 시작점이 같아야 연구 판과 같은 상태가 나온다)."""
    import yfinance as yf
    out = {}
    for mk, t in TICK.items():
        df = yf.download(t, start=start, auto_adjust=False, progress=False, threads=False)
        c = df["Close"]
        if isinstance(c, pd.DataFrame):
            c = c.iloc[:, 0]
        c.index = pd.to_datetime(c.index).tz_localize(None) if getattr(c.index, "tz", None) is not None else pd.to_datetime(c.index)
        out[mk] = c.dropna()
    return out


def ny_cut(asof=None):
    """기준일: asof 를 주면 그날까지 · 안 주면 뉴욕 16:30 전 오늘 줄(장중 값)을 뺀다(build/forecast_index.py 와 같은 규칙)."""
    if asof is not None:
        return pd.Timestamp(asof)
    try:
        from zoneinfo import ZoneInfo
        now = dt.datetime.now(ZoneInfo("America/New_York"))
    except Exception:  # noqa: BLE001
        now = dt.datetime.utcnow() - dt.timedelta(hours=4)
    today = pd.Timestamp(now.date())
    return today - pd.Timedelta(days=1) if (now.hour, now.minute) < (16, 30) else today


def _hl(S):
    return np.log(0.5) / np.log(1.0 - 1.0 / S)


def features(p):
    """Zhang 외(2020) 상태 특성(그날 종가까지) + 변동성 맞춤 배수 s."""
    r = p.pct_change()
    sig = r.ewm(span=60, min_periods=60).std()
    F = {}
    for h in H_RET:
        F["r%d" % h] = (p / p.shift(h) - 1.0) / (sig * np.sqrt(h))
    for S, L in PAIRS:
        q = (p.ewm(halflife=_hl(S)).mean() - p.ewm(halflife=_hl(L)).mean()) / p.rolling(63).std()
        F["macd%d" % S] = q / q.rolling(252).std()
    d = p.diff()
    ag = d.clip(lower=0).ewm(alpha=1 / 30, adjust=False).mean()
    al = (-d.clip(upper=0)).ewm(alpha=1 / 30, adjust=False).mean()
    F["rsi"] = ((100.0 - 100.0 / (1.0 + ag / al)) - 50.0) / 50.0
    X = pd.DataFrame(F).clip(-10, 10)
    sigA = sig * np.sqrt(252)
    tgt = sigA.rolling(2520, min_periods=252).median()
    s = np.minimum(1.0, tgt / sigA)
    return X, s, sigA


# ── 정책(연구 판과 같은 식) ────────────────────────────────────────────────────
H1, H2 = 64, 32
KEYS = ("W1", "b1", "W2", "b2", "Wh", "bh")      # Wh · bh = [가치 1 | 이점 nA] 머리를 한 행렬로
DT = np.float32


def dqn_shapes(d_in, nA):
    return {"W1": (d_in, H1), "b1": (1, H1), "W2": (H1, H2), "b2": (1, H2), "Wh": (H2, 1 + nA), "bh": (1, 1 + nA)}


def unpack(flat, d_in, nA):
    """(씨앗, 모수 수) 한 줄씩 → 씨앗별 행렬 사전."""
    sh = dqn_shapes(d_in, nA)
    S = flat.shape[0]
    V, o = {}, 0
    for k in KEYS:
        m = sh[k][0] * sh[k][1]
        V[k] = np.asarray(flat[:, o:o + m], DT).reshape((S,) + sh[k])
        o += m
    return V


def _lrelu(z):
    return np.maximum(z, 0.01 * z)


def dqn_policy(V, X, i0, i1, acts):
    """탐욕 정책을 차례로(직전 행동을 넣으며). argmax Q = argmax 이점 머리."""
    d = X.shape[1]
    W1 = V["W1"].astype(np.float64)
    pre = np.einsum("td,sdh->sth", X[i0:i1], W1[:, :d, :]) + V["b1"].astype(np.float64)
    wprev = W1[:, d, :]
    W2, b2 = V["W2"].astype(np.float64), V["b2"][:, 0, :].astype(np.float64)
    Wa, ba = V["Wh"][:, :, 1:].astype(np.float64), V["bh"][:, 0, 1:].astype(np.float64)
    S, T = pre.shape[0], pre.shape[1]
    out = np.empty((T, S))
    prev = np.zeros(S)
    for k in range(T):
        h1 = _lrelu(pre[:, k, :] + prev[:, None] * wprev)
        h2 = _lrelu(np.einsum("sh,shk->sk", h1, W2) + b2)
        ai = (np.einsum("sk,ska->sa", h2, Wa) + ba).argmax(1)
        prev = acts[ai]
        out[k] = prev
    return out


def _sigm(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def rrl_policy(th, X, i0, i1, long_only):
    """직접 강화학습(Moody · Saffell 2001) — 모형 설정이 rrl 일 때만 쓴다."""
    S, d = th.shape[0], X.shape[1]
    Z = X[i0:i1] @ th[:, :d].T + th[:, d + 1]
    u = th[:, d]
    F = np.empty_like(Z)
    Fp = np.zeros(S)
    for k in range(Z.shape[0]):
        z = Z[k] + u * Fp
        Fp = _sigm(z) if long_only else np.tanh(z)
        F[k] = Fp
    return F


def acts_for(cfg):
    return (0.0, 0.5, 1.0) if cfg["long_only"] else (-1.0, 0.0, 1.0)


def _pos(dates, ts):
    return int(np.searchsorted(dates.values, np.datetime64(pd.Timestamp(ts))))


# ── 하루 판 ──────────────────────────────────────────────────────────────────
def market_today(mk, px):
    with io.open(os.path.join(MODEL_DIR, "rl_%s.json" % mk), encoding="utf-8") as fh:
        meta = json.load(fh)
    z = np.load(os.path.join(MODEL_DIR, "rl_%s.npz" % mk))
    cfg = meta["cfg"]
    if cfg.get("vix"):
        raise SystemExit("🚨 모형 설정이 VIX 상태를 쓰는데 이 빌더는 지수 종가만 받는다 — 설정을 확인할 것")
    X, s, sigA = features(px)
    D = pd.DatetimeIndex(px.index)
    Xv = X.values.astype(float)
    v = _pos(D, meta["v_date"])
    a_live = _pos(D, meta["fold_start"]) - 2
    if str(D[a_live].date()) != meta["a_live_date"]:
        raise SystemExit("🚨 %s 운용 접힘 첫 결정일이 %s 인데 지금 격자에서는 %s — 원천 날짜가 바뀌었다"
                         % (mk, meta["a_live_date"], D[a_live].date()))
    if not np.isfinite(Xv[v:]).all():
        raise SystemExit("🚨 %s 상태 특성에 빈 값이 있다(검증 시작 %s 뒤) — 원천을 확인할 것" % (mk, meta["v_date"]))
    if cfg["method"] == "rrl":
        Af = rrl_policy(z["W"], Xv, v, len(Xv), cfg["long_only"])
    else:
        Af = dqn_policy(unpack(z["W"], int(meta["off"]), len(acts_for(cfg))), Xv, v, len(Xv), np.asarray(acts_for(cfg)))
    A_live = Af[a_live - v:]
    tail_d = [str(x) for x in z["dates_tail"]]
    n_t = len(tail_d)
    want = [str(d.date()) for d in D[a_live - n_t:a_live]]
    if tail_d != want:
        raise SystemExit("🚨 %s 저장 행동의 날짜가 지금 격자와 안 맞는다(%s ~ %s) — 이어 붙이지 않는다"
                         % (mk, tail_d[0], tail_d[-1]))
    A = np.vstack([z["A_tail"].astype(float), A_live])
    i0 = a_live - n_t
    w = np.nanmean(A, 1) * s.values[i0:i0 + len(A)]
    dec = D[i0:i0 + len(A)]
    last = len(D) - 1
    j0 = _pos(D, D[last] - pd.DateOffset(years=1))
    hist = [[str(dec[k].date()), round(float(w[k]), 4)] for k in range(len(dec)) if (i0 + k) >= j0]
    pos = float(w[-1])
    acts_now = A[-1]
    return {"name": NAMES[mk], "config": LABELS.get(meta["config"], meta["config"]),
            "decided": str(D[last].date()), "position_today": round(pos, 4),
            "expected_dir_5d": 1 if pos > 0.2 else (-1 if pos < -0.2 else 0),
            "seeds": {"long": int((acts_now > 0).sum()), "flat": int((acts_now == 0).sum()),
                      "short": int((acts_now < 0).sum()), "n": int(len(acts_now))},
            "vol_scale": round(float(s.values[last]), 4), "vol_ann_pct": round(float(sigA.values[last]) * 100, 2),
            "position_hist": hist,
            "model": {"fold_start": meta["fold_start"], "v_date": meta["v_date"], "source_sha256": meta.get("source_sha256")}}


def build(P):
    out = {"note": "다음 주가 흐름(forecast.html)의 강화학습 칸 — build/forecast_rl.py 가 매 거래일 굽는다. "
                   "저장한 운용 접힘 모형(build/forecast_model/)으로 다음 거래일 비중만 낸다(다시 학습하지 않는다). "
                   "비중은 에이전트 자세이며 예측치가 아니다 — 표본 밖 검증 12판 모두 못 넘었다(data/forecast_validation.json).",
           "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "as_of": None, "source": "yfinance(^GSPC · ^NDX 종가 · 2003-01 부터)", "markets": {}}
    for mk in ("spx", "ndx"):
        r = market_today(mk, P[mk])
        out["markets"][mk] = r
        out["as_of"] = r["decided"] if out["as_of"] is None else min(out["as_of"], r["decided"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None, help="기준일 YYYY-MM-DD(없으면 마지막 확정 종가)")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    cut = ny_cut(a.asof)
    P = {mk: s[s.index <= cut] for mk, s in fetch_public().items()}
    res = build(P)
    lds = {v["decided"] for v in res["markets"].values()}
    if len(lds) != 1:
        raise SystemExit("🚨 두 지수의 결정일이 다르다 %s — 원천이 하루 덜 들어왔다. 쓰지 않는다" % sorted(lds))
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
        print("%s %s 종가 결정 · 다음 거래일 비중 %.2f(씨앗 매수 %d · 현금 %d · 숏 %d) · 변동성 배수 %.2f · 이력 %d일"
              % (v["name"], v["decided"], v["position_today"], v["seeds"]["long"], v["seeds"]["flat"],
                 v["seeds"]["short"], v["vol_scale"], len(v["position_hist"])))


if __name__ == "__main__":
    main()
