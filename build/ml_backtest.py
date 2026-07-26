# -*- coding: utf-8 -*-
"""build/ml_backtest.py — 머신러닝 두 건을 사전등록 규약대로 한 번만 돌린다.

왜 미뤄뒀었나. 입력은 진작 다 있었다. 문제는 데이터가 아니라 **정직하게 돌리기가 어렵다**는
것이었다 — 학습·검증 분할과 하이퍼파라미터를 결과 보고 고치는 순간 그건 검정이 아니라
탐색이 되고, 그렇게 나온 성과는 믿을 수 없다.

그래서 규약을 코드에 먼저 박고 **한 번만** 돌린다. 아래 값들은 결과를 본 뒤 고치지 않는다.

  · 모델      : 릿지(선형). 트리·부스팅을 안 쓰는 이유는 튜닝할 손잡이가 많을수록
                '한 번만 돌린다'는 약속을 지키기 어려워서다.
  · 정규화    : L2 = 1.0 고정. 격자 탐색 없음.
  · 특징      : 아래 FEATS에 고정. 결과를 보고 추가·제거하지 않는다.
  · 검증      : 워크포워드 확장창. t 시점 예측은 t까지의 데이터로만 학습한다(재학습 월 1회).
  · 표준화    : 학습창 안에서만 평균·표준편차를 구한다. 전체 표본으로 표준화하면
                미래 정보가 새어 들어간다(흔한 사고다).
  · 판정      : 지수 타이밍은 SPY 상시보유, 종목선택은 동일가중 유니버스와 겨룬다.

산출은 data/ml_strategies.json. build/asset_backtest.py가 이 파일을 읽어 아카이브 재점검표에
합친다 — 표를 두 곳에 두면 갈린다.

  python build/ml_backtest.py
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tech_backtest import ann_stats, tstat, maxdd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_SD = os.path.join(DATA, "sd")
OUT = os.path.join(DATA, "ml_strategies.json")

L2 = 1.0            # 고정. 탐색하지 않는다.
REFIT = 21          # 재학습 주기(거래일) ≈ 월 1회
MIN_TRAIN = 504     # 최소 학습 표본(≈2년) — 이보다 짧으면 예측하지 않는다
HOLD = 21           # 종목선택 보유기간(거래일)


def ridge(X, y, lam):
    """닫힌 해. 절편은 별도로 두고 벌점에서 뺀다(절편까지 줄이면 예측이 0으로 끌려간다)."""
    n, p = X.shape
    Xc = np.hstack([np.ones((n, 1)), X])
    P = np.eye(p + 1) * lam
    P[0, 0] = 0.0
    try:
        return np.linalg.solve(Xc.T @ Xc + P, Xc.T @ y)
    except np.linalg.LinAlgError:
        return None


def zfit(X):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return mu, sd


# ── ① 지수 타이밍 ────────────────────────────────────────────────────────
FEATS_MKT = [
    "200일선 이격도", "50일선 이격도", "20일 실현변동성", "12-1 모멘텀",
    "1개월 수익", "장단기 금리차", "VIX 수준", "VIX 20일 변화", "신용 프록시(HYG/LQD)",
]


def market_timing(A, RF):
    DTS = A["dates"]
    n = len(DTS)
    px = A["px"]
    spy = np.array([np.nan if v is None else v for v in px["SPY"]], float)
    hyg = np.array([np.nan if v is None else v for v in px.get("HYG", [None] * n)], float)
    lqd = np.array([np.nan if v is None else v for v in px.get("LQD", [None] * n)], float)
    vix = np.array([np.nan if v is None else v for v in px.get("^VIX", [None] * n)], float)

    def macro_series(sid):
        m = A["macro"].get(sid) or {}
        ks = sorted(m)
        out = np.full(n, np.nan)
        j, last = 0, np.nan
        for i, d in enumerate(DTS):
            while j < len(ks) and ks[j] <= d:
                last = m[ks[j]]; j += 1
            out[i] = last
        return out
    t10y2y = macro_series("T10Y2Y")

    def sma(a, w):
        c = np.concatenate([[0.0], np.nancumsum(np.nan_to_num(a))])
        out = np.full(n, np.nan)
        out[w:] = (c[w + 1:] - c[1:-w]) / w
        return out

    r = np.full(n, np.nan)
    r[1:] = spy[1:] / spy[:-1] - 1
    vol20 = np.full(n, np.nan)
    for i in range(20, n):
        vol20[i] = np.nanstd(r[i - 19:i + 1])
    X = np.column_stack([
        spy / sma(spy, 200) - 1,
        spy / sma(spy, 50) - 1,
        vol20 * math.sqrt(252),
        np.concatenate([np.full(252, np.nan), spy[252:] / spy[:-252] - 1])
        - np.concatenate([np.full(21, np.nan), spy[21:] / spy[:-21] - 1]),
        np.concatenate([np.full(21, np.nan), spy[21:] / spy[:-21] - 1]),
        t10y2y,
        vix,
        np.concatenate([np.full(20, np.nan), vix[20:] - vix[:-20]]),
        hyg / lqd,
    ])
    # 목표: 향후 21거래일 SPY 수익(선견 방지 — 신호는 t, 수익은 t+1..t+21)
    y = np.full(n, np.nan)
    y[:-HOLD - 1] = spy[HOLD + 1:] / spy[1:-HOLD] - 1

    start = None
    for i in range(n):
        if np.isfinite(X[i]).all():
            start = i; break
    if start is None:
        return None
    st = start + MIN_TRAIN
    if st >= n - 60:
        return None

    pred = np.full(n, np.nan)
    beta, mu, sd = None, None, None
    for i in range(st, n):
        if (i - st) % REFIT == 0 or beta is None:
            # 학습창: 목표가 확정된 구간까지만(마지막 HOLD+1일은 미래를 보게 되므로 뺀다)
            hi = i - HOLD - 1
            rows = [k for k in range(start, hi) if np.isfinite(X[k]).all() and np.isfinite(y[k])]
            if len(rows) < MIN_TRAIN:
                continue
            Xtr = X[rows]; ytr = y[rows]
            mu, sd = zfit(Xtr)
            beta = ridge((Xtr - mu) / sd, ytr, L2)
        if beta is None or not np.isfinite(X[i]).all():
            continue
        z = (X[i] - mu) / sd
        pred[i] = beta[0] + float(z @ beta[1:])

    nav, rets, bn, brs = [100.0], [], [100.0], []
    w_prev = 0.0
    turn = 0.0
    for i in range(st + 1, n):
        w_ = 1.0 if (np.isfinite(pred[i - 1]) and pred[i - 1] > 0) else 0.0
        turn += abs(w_ - w_prev); w_prev = w_
        rr = r[i] if np.isfinite(r[i]) else 0.0
        rfd = (sum(RF.values()) / len(RF) / 21) if RF else 0.0
        v = w_ * rr + (1 - w_) * rfd
        rets.append(v); nav.append(nav[-1] * (1 + v))
        brs.append(rr); bn.append(bn[-1] * (1 + rr))
    dd = DTS[st:]
    ms, mb = ann_stats(nav, dd, RF), ann_stats(bn, dd, RF)
    step = max(1, len(nav) // 220)
    return {
        "sid": "ml-timing", "arch": "ml-market-timing",
        "holdings": {"kind": "asset", "as_of": DTS[-1],
                     "weights": [("SPY" if (np.isfinite(pred[-1]) and pred[-1] > 0) else "현금(SHY)", 100.0)],
                     "note": "모델의 마지막 예측이 %s이라 %s를 든다."
                             % (("양수" if (np.isfinite(pred[-1]) and pred[-1] > 0) else "음수/결측"),
                                ("SPY" if (np.isfinite(pred[-1]) and pred[-1] > 0) else "현금"))},
        "name": "머신러닝 지수 타이밍 (릿지·워크포워드)",
        "rule": "특징 9개로 향후 21거래일 SPY 수익을 릿지 회귀로 예측하고, 예측이 양수면 "
                "SPY 100%·아니면 현금. 월 1회 재학습하며 학습은 그 시점까지의 데이터만 쓴다.",
        "why": "'데이터가 없어 못 돌린다'가 아니라 '정직하게 돌리기 어렵다'가 미뤄둔 이유였다. "
               "모델·정규화·특징·검증 방식을 코드에 먼저 박고 한 번만 돌렸다 — "
               "결과를 보고 고치지 않았다.",
        "note": "특징: " + " · ".join(FEATS_MKT) + ". L2=1.0 고정, 격자 탐색 없음. "
                "표준화는 학습창 안에서만 한다(전체로 하면 미래가 샌다).",
        "start": DTS[st], "end": DTS[-1], "n_days": n - st,
        "metrics": ms, "bench": mb, "bench_unstable": False,
        "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
        "t": tstat(rets, brs), "turnover": round(turn / max(1e-9, (n - st) / 252), 1),
        "nav": [round(x, 2) for x in nav[::step]],
        "bnav": [round(x, 2) for x in bn[::step]],
    }


# ── ② 횡단면 종목선택 ────────────────────────────────────────────────────
FEATS_XS = ["12-1 모멘텀", "1개월 반전", "60일 변동성", "200일선 이격도",
            "50일선 이격도", "거래량 추세", "베타"]


def stock_selection(RF, TOPN=50):
    st_ = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    DTS = st_["pxd_dates"]
    n = len(DTS)
    P = {}
    V = {}
    for s in st_["stocks"]:
        t = s["t"]
        p = os.path.join(DIR_SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        a = d.get("pxd")
        if not (isinstance(a, list) and len(a) == n):
            continue
        P[t] = np.array([np.nan if x is None else x for x in a], float)
        vd = d.get("vd")
        V[t] = np.array([np.nan if x is None else x for x in vd], float) \
            if isinstance(vd, list) and len(vd) == n else np.full(n, np.nan)
    tick = sorted(P)
    if len(tick) < 100:
        return None
    M = np.column_stack([P[t] for t in tick])
    R = np.full_like(M, np.nan)
    R[1:] = M[1:] / M[:-1] - 1
    bench = np.nanmean(R, axis=1)

    def roll_mean(A_, w):
        out = np.full_like(A_, np.nan)
        for i in range(w, A_.shape[0]):
            out[i] = np.nanmean(A_[i - w + 1:i + 1], axis=0)
        return out

    def ratio(w):
        out = np.full_like(M, np.nan)
        out[w:] = M[w:] / M[:-w] - 1
        return out

    mom12 = ratio(252)
    mom1 = ratio(21)
    sma200 = roll_mean(M, 200)
    sma50 = roll_mean(M, 50)
    vol60 = np.full_like(M, np.nan)
    for i in range(60, n):
        vol60[i] = np.nanstd(R[i - 59:i + 1], axis=0)
    vtr = np.full_like(M, np.nan)
    v20 = roll_mean(np.column_stack([V[t] for t in tick]), 20)
    v60 = roll_mean(np.column_stack([V[t] for t in tick]), 60)
    with np.errstate(invalid="ignore", divide="ignore"):
        vtr = v20 / v60
        beta = np.full_like(M, np.nan)
        for i in range(120, n):
            b = R[i - 119:i + 1]
            bm = bench[i - 119:i + 1]
            bv = np.nanvar(bm)
            if bv > 0:
                beta[i] = np.nanmean((b - np.nanmean(b, axis=0)) *
                                     (bm - np.nanmean(bm))[:, None], axis=0) / bv
        F = [mom12 - mom1, -mom1, vol60, M / sma200 - 1, M / sma50 - 1, vtr, beta]

    fwd = np.full_like(M, np.nan)
    fwd[:-HOLD - 1] = M[HOLD + 1:] / M[1:-HOLD] - 1
    fwd_b = np.full(n, np.nan)
    bc = np.nancumprod(1 + np.nan_to_num(bench))
    fwd_b[:-HOLD - 1] = bc[HOLD + 1:] / bc[1:-HOLD] - 1

    start = 260
    st2 = start + 252          # 종목 패널은 3년뿐이라 학습창을 1년으로 잡는다
    if st2 >= n - 40:
        return None
    month_end = [i for i in range(st2, n - 1) if DTS[i][:7] != DTS[i + 1][:7]]

    hold, nav, rets, bn, brs = [], [100.0], [], [100.0], []
    turn = 0
    beta_w, mu, sd = None, None, None
    for i in range(st2 + 1, n):
        if (i - 1) in month_end:
            hi = i - HOLD - 2
            Xs, ys = [], []
            for k in range(start, hi):
                row = np.column_stack([f[k] for f in F])
                yk = fwd[k] - fwd_b[k]         # 초과수익을 맞힌다(시장 방향은 맞혀도 소용없다)
                ok = np.isfinite(row).all(axis=1) & np.isfinite(yk)
                if ok.sum() < 50:
                    continue
                Xs.append(row[ok]); ys.append(yk[ok])
            if Xs:
                Xtr = np.vstack(Xs); ytr = np.concatenate(ys)
                mu, sd = zfit(Xtr)
                beta_w = ridge((Xtr - mu) / sd, ytr, L2)
            if beta_w is not None:
                row = np.column_stack([f[i - 1] for f in F])
                ok = np.isfinite(row).all(axis=1)
                if ok.sum() >= TOPN:
                    z = (row[ok] - mu) / sd
                    sc = beta_w[0] + z @ beta_w[1:]
                    idx = np.array(tick)[ok][np.argsort(-sc)][:TOPN]
                    new = list(idx)
                    turn += len(set(new) - set(hold))
                    hold = new
        col = {t: j for j, t in enumerate(tick)}
        rr = [R[i, col[t]] for t in hold if np.isfinite(R[i, col[t]])]
        v = float(np.mean(rr)) if rr else 0.0
        rets.append(v); nav.append(nav[-1] * (1 + v))
        b = bench[i] if np.isfinite(bench[i]) else 0.0
        brs.append(b); bn.append(bn[-1] * (1 + b))

    dd = DTS[st2:]
    ms, mb = ann_stats(nav, dd, RF), ann_stats(bn, dd, RF)
    step = max(1, len(nav) // 220)
    yrs = max(1e-9, (n - st2) / 252)
    return {
        "sid": "ml-xsec", "arch": "ml-stock-selection",
        "holdings": {"kind": "xsec", "as_of": DTS[-1], "n": len(hold),
                     "tickers": sorted(hold),
                     "note": "마지막 월말 재학습·리밸런스에서 고른 %d종목이다." % len(hold)},
        "name": "머신러닝 횡단면 종목선택 (릿지·워크포워드)",
        "rule": "특징 7개로 종목별 향후 21거래일 초과수익을 릿지로 예측해 상위 %d종목을 "
                "동일가중 보유. 월말 재학습·리밸런스, 학습은 그 시점까지의 데이터만." % TOPN,
        "why": "지수 타이밍과 같은 이유로 미뤄둔 항목이다. 같은 규약(모델·L2·특징·워크포워드)을 "
               "코드에 먼저 박고 한 번만 돌렸다.",
        "note": "특징: " + " · ".join(FEATS_XS) + ". 목표는 초과수익이다(시장 방향을 맞혀도 "
                "횡단면 선택에는 소용이 없다). ⚠ 종목 패널이 3년뿐이라 학습창이 1년이다 — "
                "머신러닝을 논하기에는 매우 짧은 표본이다.",
        "start": DTS[st2], "end": DTS[-1], "n_days": n - st2,
        "metrics": ms, "bench": mb, "bench_unstable": False,
        "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
        "t": tstat(rets, brs), "turnover": round(turn / TOPN / yrs, 1),
        "nav": [round(x, 2) for x in nav[::step]],
        "bnav": [round(x, 2) for x in bn[::step]],
    }


# ── ③ 13F 컨빅션 복제 ───────────────────────────────────────────────────
def guru_clone(RF, TOPN=30, MIN_MGR=8):
    """분기말 보유를 45일 뒤(제출 마감)부터 쓴다. 이 지연을 안 넣으면 있지도 않은 정보를 쓴다."""
    p = os.path.join(DATA, "guru_history.json")
    if not os.path.exists(p):
        return None
    G = json.load(io.open(p, encoding="utf-8"))
    months, mpx = G.get("months") or [], G.get("mpx") or {}
    if not months or not mpx:
        return None
    mi = {m: i for i, m in enumerate(months)}
    tick = sorted(mpx)
    P = {t: np.array([np.nan if v is None else v for v in mpx[t]], float) for t in tick}

    def q_to_month(q):
        """분기말 + 45일 → 그 정보를 실제로 쓸 수 있는 첫 달."""
        y, mo = int(q[:4]), int(q[5:7])
        mo += 2                      # 45일 ≈ 1.5개월 → 다음다음 달부터 보유
        while mo > 12:
            mo -= 12; y += 1
        return "%04d-%02d" % (y, mo)

    # 분기별 목표 바스켓: 컨빅션(운용사 포트폴리오 내 비중) × 컨센서스(보유 운용사 수)
    basket = {}
    for q, mm in (G.get("holdings") or {}).items():
        if len(mm) < MIN_MGR:
            continue                 # 운용사가 적은 초기 분기는 '컨센서스'가 성립하지 않는다
        score, nheld = {}, {}
        for _cik, h in mm.items():
            tot = sum(h.values())
            if tot <= 0:
                continue
            for t, v in h.items():
                if t not in P:
                    continue
                score[t] = score.get(t, 0.0) + v / tot      # 컨빅션 합
                nheld[t] = nheld.get(t, 0) + 1              # 컨센서스
        rank = sorted(score, key=lambda t: -(score[t] * nheld[t]))
        if rank:
            basket[q_to_month(q)] = rank[:TOPN]

    if len(basket) < 12:
        return None
    st = mi.get(min(basket))
    if st is None or st >= len(months) - 12:
        return None

    hold, nav, rets, bn, brs = [], [100.0], [], [100.0], []
    turn = 0
    for i in range(st + 1, len(months)):
        m = months[i - 1]
        if m in basket:
            new = [t for t in basket[m] if np.isfinite(P[t][i - 1])]
            if new:
                turn += len(set(new) - set(hold)); hold = new
        rr = [P[t][i] / P[t][i - 1] - 1 for t in hold
              if np.isfinite(P[t][i]) and np.isfinite(P[t][i - 1]) and P[t][i - 1]]
        v = float(np.mean(rr)) if rr else 0.0
        # 대조군 = 같은 달 우리 유니버스 동일가중(복제가 '종목 고르기'로 이겼는지만 남긴다)
        allr = [P[t][i] / P[t][i - 1] - 1 for t in tick
                if np.isfinite(P[t][i]) and np.isfinite(P[t][i - 1]) and P[t][i - 1]]
        b = float(np.mean(allr)) if allr else 0.0
        rets.append(v); nav.append(nav[-1] * (1 + v))
        brs.append(b); bn.append(bn[-1] * (1 + b))

    def mstats(x, nv):
        mu = sum(x) / len(x)
        sd = math.sqrt(sum((v - mu) ** 2 for v in x) / max(1, len(x) - 1))
        yrs = len(x) / 12
        return {"cagr": round(((nv[-1] / nv[0]) ** (1 / yrs) - 1) * 100, 2),
                "vol": round(sd * math.sqrt(12) * 100, 2),
                "sharpe": round(mu / sd * math.sqrt(12), 3) if sd > 0 else None,
                "mdd": round(maxdd(nv) * 100, 2)}
    ms, mb = mstats(rets, nav), mstats(brs, bn)
    d = [x - y for x, y in zip(rets, brs)]
    mu = sum(d) / len(d)
    sd = math.sqrt(sum((v - mu) ** 2 for v in d) / max(1, len(d) - 1))
    # 베타 — 아카이브가 '초과수익 전부 베타'라고 적었으므로 그 수치를 직접 낸다
    bmu = sum(brs) / len(brs)
    bvar = sum((v - bmu) ** 2 for v in brs) / max(1, len(brs) - 1)
    beta = (sum((x - mu - 0) * (y - bmu) for x, y in zip(rets, brs)) /
            max(1, len(rets) - 1) / bvar) if bvar > 0 else None
    step = max(1, len(nav) // 220)
    return {
        "sid": "guru-clone", "arch": "13f-best-ideas-clone",
        "name": "13F 컨빅션 복제 (상위 %d종목)" % TOPN,
        "rule": "분기말 13F에서 (운용사 포트폴리오 내 비중 합) × (보유 운용사 수)가 높은 %d종목을 "
                "동일가중 보유. 분기말 45일 뒤부터 적용하고 분기마다 교체." % TOPN,
        "why": "'SEC 벌크 데이터셋이 분기당 180MB라 무거워서 못 한다'가 미뤄둔 이유였다. "
               "운용사별 EDGAR 제출을 직접 읽으면 제출당 44KB라 100배 가볍다 — 그 길로 돌렸다.",
        "note": "제출 마감 45일 지연을 반영했다. 대조군은 같은 종목 풀 동일가중이라 "
                "'고르기'의 값어치만 남는다. 13F는 롱 미국주식만 담아 실제 포트폴리오가 아니다. "
                "베타 %s (아카이브가 '초과수익 전부 베타'라 적은 대목의 실측치)."
                % ("%.2f" % beta if beta else "—"),
        "holdings": {"kind": "xsec", "as_of": months[-1], "n": len(hold),
                     "tickers": sorted(hold),
                     "note": "가장 최근 분기 13F(제출 마감 45일 지연 반영)로 고른 %d종목을 "
                             "동일가중 보유 중이다." % len(hold)},
        "start": months[st], "end": months[-1], "n_days": (len(months) - st) * 21,
        "n_months": len(months) - st,
        "metrics": ms, "bench": mb, "bench_unstable": False, "beta": round(beta, 2) if beta else None,
        "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
        "t": round(mu / (sd / math.sqrt(len(d))), 2) if sd > 0 else None,
        "turnover": round(turn / TOPN / max(1e-9, (len(months) - st) / 12), 1),
        "nav": [round(x, 2) for x in nav[::step]],
        "bnav": [round(x, 2) for x in bn[::step]],
    }


def main() -> int:
    ap = os.path.join(DATA, "assets.json")
    if not os.path.exists(ap):
        print("❌ data/assets.json 없음 — python build/refresh_assets.py 먼저"); return 1
    A = json.load(io.open(ap, encoding="utf-8"))
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"),
                           encoding="utf-8")).get("monthly") or {}
    rows = []
    for fn, label in ((lambda: market_timing(A, RF), "지수 타이밍"),
                      (lambda: stock_selection(RF), "횡단면 종목선택"),
                      (lambda: guru_clone(RF), "13F 컨빅션 복제")):
        try:
            r = fn()
        except Exception as e:
            print("  ❌ %s %s: %s" % (label, type(e).__name__, e)); continue
        if r:
            rows.append(r)
        else:
            print("  ❌ %s 산출 없음(표본 부족)" % label)
    # ⚠ 검정 구간이 짧으면 판정하지 않는다. 종목 패널이 3년뿐인데 거기서 워밍업 260일 +
    #   학습창 252일을 빼면 실제로 겨루는 구간이 1년밖에 안 남는다. 그 길이에서 나온
    #   CAGR 70%는 실력이 아니라 잡음이다 — 숫자는 싣되 '판정 불가'로 못 박는다.
    MIN_TEST = 504
    for r in rows:
        r["testable"] = r["n_days"] >= MIN_TEST
        if not r["testable"]:
            r["verdict"] = "표본 부족 · 판정 불가"
            r["use"] = ("검정 구간이 %.1f년(%d거래일)뿐이라 판정하지 않는다. 이 길이에서는 "
                        "어떤 수치가 나와도 실력과 운을 가를 수 없다 — 표를 근거로 쓰지 말 것."
                        % (r["n_days"] / 252, r["n_days"]))
        elif r["d_sharpe"] > 0 and (r.get("t") or 0) >= 2.0:
            r["verdict"] = "대조군 우위(단일검정)"
            r["use"] = "대조군을 이겼으나 다중검정 보정 전이다. 아카이브 재점검표에서 함께 보정된다."
        elif r["d_sharpe"] > 0:
            r["verdict"] = "구별 불가"
            r["use"] = "대조군보다 나은 쪽이지만 통계적으로 갈리지 않는다."
        else:
            r["verdict"] = "대조군 열위"
            r["use"] = "대조군보다 나쁘다. 사전등록 규약대로 한 번 돌린 결과이며 재시도하지 않는다."

    doc = {
        "note": "머신러닝 두 건. 규약(모델·정규화·특징·검증)을 코드에 먼저 박고 한 번만 돌린 결과다. "
                "결과를 보고 설정을 고치지 않았다 — 고치는 순간 검정이 아니라 탐색이 된다.",
        "protocol": [
            "모델은 릿지(선형), L2=1.0 고정. 격자 탐색을 하지 않는다.",
            "특징은 코드에 고정. 결과를 보고 넣거나 빼지 않는다.",
            "워크포워드 확장창 — t 시점 예측은 t까지의 데이터로만 학습한다(월 1회 재학습).",
            "표준화(평균·표준편차)는 학습창 안에서만 구한다. 전체 표본으로 하면 미래가 샌다.",
            "목표를 만들 때 마지막 22거래일은 학습에서 뺀다 — 그 구간의 정답은 아직 미래다.",
            "검정 구간이 2년(504거래일) 미만이면 수치는 싣되 판정하지 않는다. "
            "짧은 구간에서는 어떤 결과가 나와도 실력과 운을 가를 수 없다.",
        ],
        "as_of": A["dates"][-1], "strategies": rows,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("%-34s %9s %8s %8s %8s %7s" % ("전략", "구간", "CAGR", "샤프", "Δ샤프", "t"))
    for r in rows:
        m = r["metrics"]
        print("%-34s %9s %8s %8s %8s %7s"
              % (r["name"][:34], r["start"][:7], m.get("cagr"), m.get("sharpe"),
                 r["d_sharpe"], r.get("t")))
        print("     대조군 CAGR %s · 샤프 %s · %d거래일 → %s"
              % (r["bench"].get("cagr"), r["bench"].get("sharpe"), r["n_days"], r["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
