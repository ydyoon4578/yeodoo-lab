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
  · 판정      : 지수 타이밍은 SPY 상시보유, 종목선택·13F 복제는 S&P 500(PR)과 겨룬다.
                (2026-07-28 사용자 결정 — 동일가중 유니버스 대조군은 쓰지 않는다)

산출은 data/ml_strategies.json. build/asset_backtest.py가 이 파일을 읽어 아카이브 재점검표에
합친다 — 표를 두 곳에 두면 갈린다.

  python build/ml_backtest.py
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tech_backtest import (ann_stats, tstat, maxdd, curve_pack,  # noqa: E402
                           risk_bootstrap)

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


def logit(X, y, lam, iters=25):
    """L2 벌점 로지스틱을 IRLS로 푼다. 절편은 벌점에서 뺀다(릿지와 같은 규약).

    왜 로지스틱을 따로 두나. 블로그가 인용한 두 논문(A Comparison of Direction and Value
    Prediction, 2025 / How To Bet On Winners, 2025)의 주장이 "수익의 **크기**를 맞히는 것보다
    **방향**을 맞히는 편이 낫다"는 것이다. 이 주장은 같은 특징·같은 워크포워드에서 목표와
    모델만 바꿔야 검정된다 — 그래서 릿지 쪽 코드를 그대로 두고 이 함수만 더한다.

    수렴은 25회로 끊는다. 완전 분리(perfectly separable)면 계수가 발산하는데, 벌점이 있어
    실제로는 발산하지 않지만 반복만 늘어난다. 결과를 보고 늘리지 않는다.
    """
    n, p = X.shape
    Xc = np.hstack([np.ones((n, 1)), X])
    P = np.eye(p + 1) * lam
    P[0, 0] = 0.0
    b = np.zeros(p + 1)
    for _ in range(iters):
        z = Xc @ b
        pr = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        w = np.clip(pr * (1 - pr), 1e-6, None)
        g = Xc.T @ (y - pr) - P @ b
        H = (Xc * w[:, None]).T @ Xc + P
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return None
        b = b + step
        if np.max(np.abs(step)) < 1e-7:
            break
    return b


def zfit(X):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return mu, sd


def expand2(row):
    """원 특징 + 제곱 + 모든 쌍곱(2차 다항 확장). 7개 → 35개.

    왜 두나. Gu·Kelly·Xiu(RFS 2020)가 트리·신경망이 선형을 이겼다고 보고하면서, 그 이득이
    **비선형 상호작용**에서 나온다고 못 박았다. 이 랩에는 선형(릿지·로지스틱)뿐이라 그 주장이
    검정된 적이 없다.

    트리를 직접 구현하는 대신 특징을 2차로 펴서 같은 릿지에 넣는다. 이유가 둘이다 —
      ① 상호작용이 값을 하는지만 묻는 것이면 이것으로 충분하다. 목표·창·표준화·솔버·벌점이
         전부 그대로라, 갈리는 것이 **오직 특징 사상**뿐이다. 트리를 넣으면 모델·분할규칙·
         깊이가 한꺼번에 바뀌어 무엇 때문에 갈렸는지 말할 수 없다.
      ② 워크플로가 pandas·numpy·yfinance 만 깐다(sklearn 없음). 트리를 손으로 짜면
         깊이·분할수 같은 새 손잡이가 생기고, 사전등록 규약상 그걸 탐색할 수 없어
         고른 값이 곧 임의값이 된다.
    벌점은 L2=1.0 그대로다. 열이 5배가 되므로 같은 벌점이면 계수당 제약이 더 세지는데,
    그것을 보정하려고 값을 만지면 그 순간 탐색이 된다 — 고정한다.
    """
    p = row.shape[1]
    cols = [row, row ** 2]
    for a in range(p):
        for b in range(a + 1, p):
            cols.append((row[:, a] * row[:, b])[:, None])
    return np.hstack(cols)


# ── 얕은 랜덤 포레스트 ────────────────────────────────────────────────────
# Gu·Kelly·Xiu 의 승자 모델이 트리다. 2차 확장은 상호작용을 '선형 해 안에서' 흉내 낸 것이고,
# 트리는 그 상호작용을 **분할로 직접** 만든다. 둘을 같이 둬야 '상호작용이 문제였나, 아니면
# 선형이라는 형태가 문제였나'가 갈린다.
#
# 사전등록 값 — 결과를 보고 고치지 않는다. 손잡이를 최소로 두려고 일부러 작게 잡았다.
#   나무 100 · 깊이 4 · 분할 후보 특징 √p · 리프 최소표본 200 · 나무당 표본 6만행
#   깊이 4 는 최대 16개 리프다. 특징이 7개뿐이라 이보다 깊이 가면 잡음을 외운다.
#   리프 200 은 종목 500개 × 학습 수백일에서 리프 하나가 최소 한 시점 폭은 되게 하는 값이다.
#   분할점은 각 특징의 사분위(25·50·75%)만 본다 — 모든 값을 훑으면 느리고, 후보를 늘리는 것
#   자체가 과적합 손잡이가 된다.
#   ⚠ 나무당 표본을 6만행으로 자른다. 학습창이 끝에서 종목 500 × 2400일 = 120만행까지
#     자라는데 그것을 100그루가 매 리밸런스마다 훑으면 실행이 끝나지 않는다(실측으로 확인).
#     자르는 것은 속도 때문만이 아니다 — 배깅의 목적이 나무마다 다른 데이터를 보게 해 분산을
#     줄이는 것이라, 부분표본은 그 목적에 오히려 부합한다(sklearn 의 max_samples 와 같은 뜻).
#     6만은 결과를 보고 고른 값이 아니라 '한 번 돌 수 있는 크기'로 먼저 박은 값이다.
RF_TREES, RF_DEPTH, RF_LEAF, RF_SEED = 100, 4, 200, 20260729
RF_MAXROWS = 60000


def _tree_fit(X, y, depth, leaf, feat_idx, rng, qs=(25, 50, 75)):
    """분산 감소 기준 회귀트리 하나. 반환은 (특징, 문턱, 왼쪽, 오른쪽) 중첩 튜플 또는 평균값."""
    if depth == 0 or len(y) < 2 * leaf:
        return float(y.mean())
    best = None
    for f in feat_idx:
        col = X[:, f]
        for q in np.percentile(col, qs):
            m = col <= q
            nl = int(m.sum())
            if nl < leaf or (len(y) - nl) < leaf:
                continue
            # 분산 감소 = 전체 SSE − (왼쪽 SSE + 오른쪽 SSE). 상수항은 비교에 영향이 없다.
            sse = ((y[m] - y[m].mean()) ** 2).sum() + ((y[~m] - y[~m].mean()) ** 2).sum()
            if best is None or sse < best[0]:
                best = (sse, f, float(q), m)
    if best is None:
        return float(y.mean())
    _, f, q, m = best
    return (f, q,
            _tree_fit(X[m], y[m], depth - 1, leaf, feat_idx, rng),
            _tree_fit(X[~m], y[~m], depth - 1, leaf, feat_idx, rng))


def _tree_pred(node, X):
    if not isinstance(node, tuple):
        return np.full(len(X), node)
    f, q, lo, hi = node
    out = np.empty(len(X))
    m = X[:, f] <= q
    if m.any():
        out[m] = _tree_pred(lo, X[m])
    if (~m).any():
        out[~m] = _tree_pred(hi, X[~m])
    return out


def forest_fit(X, y, seed=RF_SEED):
    """배깅 + 특징 부분집합. 나무마다 표본과 특징을 달리 뽑아 분산을 줄인다."""
    rng = np.random.default_rng(seed)
    p = X.shape[1]
    k = max(1, int(round(math.sqrt(p))))
    m = min(len(y), RF_MAXROWS)
    trees = []
    for _ in range(RF_TREES):
        idx = rng.integers(0, len(y), m)               # 부트스트랩(상한 RF_MAXROWS)
        fs = rng.choice(p, size=k, replace=False)      # 분할 후보 특징
        trees.append(_tree_fit(X[idx], y[idx], RF_DEPTH, RF_LEAF, fs, rng))
    return trees


def forest_pred(trees, X):
    if not trees:
        return np.zeros(len(X))
    return np.mean([_tree_pred(t, X) for t in trees], axis=0)


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
        "chart": curve_pack(dd, nav, bn),
        "bench_label": "SPY 상시보유",
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
        "t": tstat(rets, brs), "risk": risk_bootstrap(rets, brs), "turnover": round(turn / max(1e-9, (n - st) / 252), 1),
        "nav": [round(x, 2) for x in nav[::step]],
        "bnav": [round(x, 2) for x in bn[::step]],
    }


# ── ② 횡단면 종목선택 ────────────────────────────────────────────────────
FEATS_XS = ["12-1 모멘텀", "1개월 반전", "60일 변동성", "200일선 이격도",
            "50일선 이격도", "거래량 추세", "베타"]


# 사전등록 — 방향 예측판의 문턱. 결과를 보고 고치지 않는다.
CONF = 0.55         # '고신뢰'의 정의: 초과수익이 양(+)일 예측확률 55% 이상


def stock_selection(RF, TOPN=10, mode="value"):
    """mode='value' 릿지로 초과수익 **크기**를 예측(원래 것) ·
       mode='dir'   로지스틱으로 초과수익 **방향**을 예측해 확률 상위 TOPN ·
       mode='conf'  같은 확률에서 CONF 이상만 산다(없으면 현금) ·
       mode='inter' 같은 릿지·같은 목표인데 특징만 2차로 편다(상호작용 검정).

    넷은 특징 원본 7개·워크포워드·표준화·재학습 주기가 **완전히 같다**. 다른 것은 목표(y)와
    모델, 그리고 inter 판에서만 특징 사상이다. 그래야 '방향이 크기보다 낫다'·'비선형
    상호작용이 값을 한다'가 이 데이터에서 각각 갈린다 — 조건을 하나라도 더 바꾸면 무엇
    때문에 갈렸는지 말할 수 없다."""
    EXP = expand2 if mode == "inter" else (lambda a: a)
    FOREST = (mode == "tree")
    st_ = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    NMX = {x["t"]: (x.get("name") or x["t"]) for x in st_["stocks"]}
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
    # 대조군 = S&P 500(PR). 사용자 결정(2026-07-28) — 동일가중 유니버스는 쓰지 않는다.
    #   ⚠ 특징량(횡단면 순위·표준화)은 여전히 유니버스 전체에서 만든다. 바뀐 것은 **무엇과
    #     견주는가**뿐이고 규칙이 무엇을 사는지는 그대로다.
    bench = spx_daily(DTS)
    if bench is None:
        raise SystemExit("대조군(S&P 500 PR)을 assets.json 에서 읽지 못했다 — 판정을 낼 수 없다.")

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
    st2 = start + 252          # 첫 학습에 최소 1년은 쌓고 시작한다(이후 창은 확장형)
    if st2 >= n - 40:
        return None
    month_end = [i for i in range(st2, n - 1) if DTS[i][:7] != DTS[i + 1][:7]]

    # 문턱이 실제로 물었는지 세어 둔다. 한 번도 안 물면 이 규칙은 방향 예측판과 같은
    # 포트폴리오이고, 그 사실 자체가 보고할 결과다.
    diag = {"n_rebal": 0, "n_bind": 0, "n_dropped": 0, "p_min": 1.0, "p_max": 0.0}
    hold, nav, rets, bn, brs = [], [100.0], [], [100.0], []
    turn = 0
    beta_w, mu, sd = None, None, None
    # 학습창은 확장형(start 고정, hi 만 늘어난다)이라 매 리밸런스에 처음부터 다시 만들 이유가
    # 없다. 예전엔 리밸런스마다 range(start, hi) 를 전부 다시 훑어 column_stack·isfinite 를
    # 재계산했다 — 리밸런스 수 × 창 길이라 이력을 늘리면 제곱으로 튄다(10년에서 드러났다).
    # 지난번에 만든 데까지 기억해 두고 **새로 늘어난 날만** 덧붙인다. 결과는 완전히 같다.
    Xs, ys, built_to = [], [], start
    for i in range(st2 + 1, n):
        if (i - 1) in month_end:
            hi = i - HOLD - 2
            for k in range(built_to, hi):
                row = np.column_stack([f[k] for f in F])
                yk = fwd[k] - fwd_b[k]         # 초과수익을 맞힌다(시장 방향은 맞혀도 소용없다)
                ok = np.isfinite(row).all(axis=1) & np.isfinite(yk)
                if ok.sum() < 50:
                    continue
                # 결측 검사는 **원 특징**에서 한다. 확장한 뒤에 하면 곱에서 생긴 NaN 까지
                # 세게 되어 같은 종목이 이유 없이 더 걸러진다.
                Xs.append(EXP(row[ok])); ys.append(yk[ok])
            built_to = max(built_to, hi)
            if Xs:
                Xtr = np.vstack(Xs); ytr = np.concatenate(ys)
                mu, sd = zfit(Xtr)
                if FOREST:
                    # 트리는 계수가 아니라 나무 목록을 들고 있다. 표준화는 트리에 필요 없지만
                    # 다른 판과 입력을 한 글자도 다르게 두지 않으려고 그대로 통과시킨다.
                    beta_w = forest_fit((Xtr - mu) / sd, ytr)
                elif mode in ("value", "inter"):
                    beta_w = ridge((Xtr - mu) / sd, ytr, L2)
                else:
                    # 목표를 '초과수익이 양이었나'로 바꾼다. 특징·창·표준화는 그대로다.
                    beta_w = logit((Xtr - mu) / sd, (ytr > 0).astype(float), L2)
            if beta_w is not None:
                row = np.column_stack([f[i - 1] for f in F])
                ok = np.isfinite(row).all(axis=1)
                if ok.sum() >= TOPN:
                    z = (EXP(row[ok]) - mu) / sd
                    sc = forest_pred(beta_w, z) if FOREST else (beta_w[0] + z @ beta_w[1:])
                    names_ok = np.array(tick)[ok]
                    if mode == "conf":
                        # 확률로 바꿔 문턱을 넘는 것만 산다. 없으면 아무것도 사지 않는다 —
                        # '고신뢰만 베팅한다'는 규칙의 값은 안 살 때 안 잃는 데서 나온다.
                        pr = 1.0 / (1.0 + np.exp(-np.clip(sc, -30, 30)))
                        top = np.argsort(-pr)[:TOPN]
                        kept = [k for k in top if pr[k] >= CONF]
                        diag["n_rebal"] += 1
                        if len(kept) < len(top):
                            diag["n_bind"] += 1
                        diag["n_dropped"] += len(top) - len(kept)
                        diag["p_min"] = min(diag["p_min"], float(pr[top].min()))
                        diag["p_max"] = max(diag["p_max"], float(pr[top].max()))
                        new = list(names_ok[kept]) if kept else []
                    else:
                        new = list(names_ok[np.argsort(-sc)][:TOPN])
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
    SPEC = {
        "value": ("ml-xsec", "머신러닝 횡단면 종목선택 (릿지·워크포워드)",
                  "특징 7개로 종목별 향후 21거래일 초과수익을 릿지로 예측해 상위 %d종목을 "
                  "동일가중 보유. 월말 재학습·리밸런스, 학습은 그 시점까지의 데이터만." % TOPN,
                  "지수 타이밍과 같은 이유로 미뤄둔 항목이다. 같은 규약(모델·L2·특징·워크포워드)을 "
                  "코드에 먼저 박고 한 번만 돌렸다.",
                  "목표는 초과수익의 크기(값)다."),
        "dir": ("ml-xsec-dir", "머신러닝 방향 예측 종목선택 (로지스틱·워크포워드)",
                "같은 특징 7개로 '향후 21거래일 초과수익이 양(+)일 확률'을 로지스틱으로 예측해 "
                "확률 상위 %d종목을 동일가중 보유. 나머지 규약은 크기 예측판과 완전히 같다." % TOPN,
                "A Comparison of Direction and Value Prediction of Stock Excess Returns(2025)가 "
                "‘크기보다 방향을 맞히는 편이 낫다’고 보고했다. 그 주장은 특징·창·표준화를 고정하고 "
                "목표와 모델만 바꿔야 검정된다 — 그래서 크기 예측판을 남겨 둔 채 이것을 나란히 둔다.",
                "목표는 초과수익의 방향이다 — 양이면 1, 아니면 0."),
        "conf": ("ml-xsec-conf", "머신러닝 고신뢰 베팅 (확률 %d%% 이상만)" % round(CONF * 100),
                 "방향 예측판과 같은 확률에서 %d%% 이상인 종목만 최대 %d개까지 산다. 문턱을 넘는 "
                 "종목이 없으면 아무것도 사지 않는다(현금)." % (round(CONF * 100), TOPN),
                 "How To Bet On Winners (and Losers)(2025) — 기대수익 대신 승자·패자 확률로 "
                 "고르고, 확신이 없으면 베팅하지 않는 규칙이 거래비용 뒤에도 샤프를 올렸다는 보고다. "
                 "이 규칙의 값은 살 때가 아니라 안 살 때 나오므로, 방향 예측판과의 차이가 곧 "
                 "'참는 것'의 값이다.",
                 "문턱 %d%%는 사전등록 값이고 결과를 보고 고치지 않았다." % round(CONF * 100)),
        "inter": ("ml-xsec-inter", "머신러닝 상호작용 종목선택 (릿지·2차 확장)",
                  "크기 예측판과 같은 목표·같은 릿지인데, 특징 7개를 제곱과 쌍곱까지 펴서 "
                  "35개로 넣는다. 상위 %d종목 동일가중, 나머지 규약은 완전히 같다." % TOPN,
                  "Gu·Kelly·Xiu(Review of Financial Studies 2020)가 트리·신경망이 선형을 "
                  "이겼다고 보고하면서 그 이득이 비선형 상호작용에서 나온다고 못 박았다. "
                  "이 랩에는 선형뿐이라 그 주장이 검정된 적이 없다. 모델을 트리로 바꾸면 "
                  "분할규칙·깊이가 한꺼번에 달라져 무엇 때문에 갈렸는지 말할 수 없으므로, "
                  "특징 사상 하나만 바꿔 상호작용의 값을 따로 잰다.",
                  "목표는 크기 예측판과 같은 초과수익의 크기다. 벌점 L2=1.0 도 그대로 두었다 — "
                  "열이 5배라 계수당 제약은 더 세지지만, 그것을 보정하려 값을 만지면 그 순간 "
                  "탐색이 되어 사전등록이 무의미해진다."),
        "tree": ("ml-xsec-tree", "머신러닝 종목선택 (랜덤 포레스트·워크포워드)",
                 "같은 특징 7개·같은 목표로 얕은 회귀트리 %d그루를 배깅해 예측하고 상위 "
                 "%d종목을 동일가중 보유. 나무 깊이 %d · 리프 최소 %d표본 · 분할 후보는 "
                 "루트(7)개 특징. 나머지 규약은 크기 예측판과 완전히 같다."
                 % (RF_TREES, TOPN, RF_DEPTH, RF_LEAF),
                 "Gu·Kelly·Xiu 의 승자 모델이 트리다. 2차 확장판은 상호작용을 선형 해 '안에서' "
                 "흉내 낸 것이고, 트리는 그 상호작용을 분할로 직접 만든다. 둘을 같이 둬야 "
                 "'상호작용이 문제였나, 선형이라는 형태가 문제였나'가 갈린다. sklearn 이 "
                 "없어 numpy 로 직접 짰다.",
                 "깊이 %d·리프 %d·나무 %d은 사전등록 값이고 결과를 보고 고치지 않았다. "
                 "손잡이가 많을수록 '한 번만 돌린다'는 약속이 지켜지지 않으므로 일부러 작게 "
                 "잡았다 — 분할점도 각 특징의 사분위 세 곳만 본다."
                 % (RF_DEPTH, RF_LEAF, RF_TREES)),
    }
    sid, nm, rule, why, tgt = SPEC[mode]
    if mode == "conf":
        # 문턱이 한 번도 물지 않았다면 이건 방향 예측판과 같은 전략이다. 같은 숫자를 두 줄로
        # 싣는 것은 목록을 부풀리는 짓이므로 행을 만들지 않고, 그 사실을 진단으로 돌려준다.
        if diag["n_bind"] == 0:
            return {"__collapsed__": True, "diag": diag}
        tgt += (" 문턱은 리밸런스 %d회 중 %d회 물었고(총 %d종목 제외), 상위 %d종목의 예측확률은 "
                "%.3f~%.3f 범위였다." % (diag["n_rebal"], diag["n_bind"], diag["n_dropped"],
                                       TOPN, diag["p_min"], diag["p_max"]))
    return {
        "sid": sid, "arch": "ml-stock-selection" if mode == "value" else None,
        "chart": curve_pack(dd, nav, bn),
        "bench_label": "S&P 500(PR) 매수후보유",
        "holdings": {"kind": "xsec", "as_of": DTS[-1], "n": len(hold),
                     "tickers": sorted(hold),
                     "names": {t: (NMX.get(t) or t) for t in sorted(hold)},
                     "note": ("마지막 월말 재학습·리밸런스에서 고른 %d종목이다." % len(hold))
                             if hold else
                             "마지막 재학습에서 문턱을 넘은 종목이 없어 현재 보유가 없다(현금)."},
        "name": nm, "rule": rule, "why": why,
        "note": "특징: " + " · ".join(FEATS_XS) + ". " + tgt + " 시장 방향을 맞혀도 횡단면 "
                "선택에는 소용이 없으므로 목표는 언제나 초과수익 기준이다. ⚠ 종목 패널이 "
                "3년뿐이라 학습창이 1년이다 — 머신러닝을 논하기에는 매우 짧은 표본이다.",
        "start": DTS[st2], "end": DTS[-1], "n_days": n - st2,
        "metrics": ms, "bench": mb, "bench_unstable": False,
        "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
        "t": tstat(rets, brs), "risk": risk_bootstrap(rets, brs), "turnover": round(turn / TOPN / yrs, 1),
        "nav": [round(x, 2) for x in nav[::step]],
        "bnav": [round(x, 2) for x in bn[::step]],
    }


# ── ③ 13F 컨빅션 복제 ───────────────────────────────────────────────────
def guru_clone(RF, TOPN=10, MIN_MGR=8):
    """분기말 보유를 45일 뒤(제출 마감)부터 쓴다. 이 지연을 안 넣으면 있지도 않은 정보를 쓴다."""
    p = os.path.join(DATA, "guru_history.json")
    if not os.path.exists(p):
        return None
    G = json.load(io.open(p, encoding="utf-8"))
    # 회사명 — 툴팁용. 유니버스 정본에서 가져온다(13F 원문 이름은 표기가 제각각이다).
    try:
        NM = {x["t"]: (x.get("name") or x["t"]) for x in
              json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))["stocks"]}
    except Exception:
        NM = {}
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

    # 대조군 = S&P 500(PR) 월수익. 사용자 결정(2026-07-28) — 동일가중 유니버스는 쓰지 않는다.
    SPXM = spx_monthly(months)
    if SPXM is None:
        raise SystemExit("대조군(S&P 500 PR)을 assets.json 에서 읽지 못했다 — 판정을 낼 수 없다.")
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
        b = float(SPXM[i]) if np.isfinite(SPXM[i]) else 0.0
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
        # 이 판은 월 단위라 날짜 계열이 months다(다른 판은 일별 DTS를 dd에 담는다)
        "chart": curve_pack(months[st:], nav, bn),
        "bench_label": "S&P 500(PR) 매수후보유",
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
                     "tickers": sorted(hold), "names": {t: NM.get(t, t) for t in sorted(hold)},
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


def spx_daily(dates):
    """dates 축에 맞춘 S&P 500(PR) 일별 수익. 못 읽으면 None — 부르는 쪽이 멈춘다."""
    try:
        A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    except Exception:
        return None
    ad = A.get("dates") or []
    raw = (A.get("px") or {}).get("^GSPC")
    if not raw:
        return None
    pos = {d: i for i, d in enumerate(ad)}
    px_al, last = [], None
    for d in dates:
        i = pos.get(d)
        if i is not None and i < len(raw) and raw[i] is not None:
            last = float(raw[i])
        px_al.append(last)
    if sum(1 for x in px_al if x is not None) < len(dates) * 0.9:
        return None
    r = np.full(len(dates), np.nan)
    for i in range(1, len(dates)):
        a_, b_ = px_al[i - 1], px_al[i]
        r[i] = (b_ / a_ - 1) if (a_ and b_) else 0.0
    return r


def spx_monthly(months):
    """months('YYYY-MM') 축에 맞춘 S&P 500(PR) 월수익."""
    try:
        A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    except Exception:
        return None
    ad = A.get("dates") or []
    raw = (A.get("px") or {}).get("^GSPC")
    if not raw:
        return None
    last = {}
    for i, d in enumerate(ad):
        if i < len(raw) and raw[i] is not None:
            last[d[:7]] = float(raw[i])
    out = np.full(len(months), np.nan)
    for j in range(1, len(months)):
        a_, b_ = last.get(months[j - 1]), last.get(months[j])
        if a_ and b_ and a_ > 0:
            out[j] = b_ / a_ - 1.0
    return out


# ── ③ 특징 확대판 (새 사전등록) ───────────────────────────────────────────
# 왜 또 등록하나. 앞 판에서 트리·2차확장이 선형을 못 이겼는데, 그 판의 특징이 7개뿐이었다.
# Gu·Kelly·Xiu 의 설정은 특징이 수십 개이고 거기에 **시장 상태 변수를 곱해** 조건부 모형을
# 만든다. 특징이 적으면 상호작용이 값을 할 자리 자체가 없으므로, 앞 판의 결과만으로
# '비선형이 안 된다'고 말하면 성급하다. 그래서 특징을 늘려 한 번 더 등록한다.
#
# ⚠ 앞 판(FEATS 7개)은 **손대지 않는다**. 사전등록물은 결과가 나온 뒤에 고치는 순간 의미를
#   잃는다. 이건 별개의 등록이고 코드 경로도 따로 둔다.
#
# 재무를 넣지 않은 이유 — 넣고 싶었으나 표본이 못 버틴다. 실측: 시점 정합(기간종료+45일)으로
#   자르면 eps·rev·ni·sh 는 2021-05, eq·asset 은 2022-08 부터 YoY 가 선다. 거기에 학습창을
#   얹으면 검정 구간이 2년 아래로 떨어지는데, 이 파일의 MIN_TEST 규칙이 바로 그 길이를
#   '판정 불가'로 못 박아 두었다. 창을 반토막 내면 특징을 늘린 효과와 구간이 짧아진 효과가
#   섞여 무엇 때문에 갈렸는지 말할 수 없다. 그래서 전 구간에서 구할 수 있는 것만 쓴다.
#
# 시장 상태 4개는 **전 종목이 같은 값**이다. 횡단면 순위에서 상수는 선형 모형의 순서를 전혀
#   바꾸지 못한다 — 오직 상호작용을 통해서만 값을 한다. 즉 이 넷은 트리에게만 재료이고,
#   그래서 이 판이 '비선형이 값을 하는가'를 앞 판보다 정직하게 묻는다.
FEATS_WIDE = [
    "12-1 모멘텀", "1개월 반전", "6-1 모멘텀", "3개월 모멘텀",
    "60일 변동성", "특이변동성", "60일 왜도",
    "200일선 이격", "50일선 이격", "52주 고점 대비", "52주 저점 대비", "MAX(21일)",
    "거래량 추세", "거래대금(로그)", "비유동성(Amihud)", "베타",
    "시장 200일선 이격", "시장 60일 변동성", "VIX", "장단기 금리차",
]


def stock_selection_wide(RF, TOPN=10, model="ridge"):
    """특징 20개 · 워크포워드 · 상위 TOPN 동일가중. model='ridge' 또는 'forest'.

    앞 판(stock_selection)과 목표·창·표준화·재학습 주기·보유기간이 같다. 다른 것은
    **특징 집합과 모델**뿐이다."""
    st_ = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    NMX = {x["t"]: (x.get("name") or x["t"]) for x in st_["stocks"]}
    DTS = st_["pxd_dates"]
    n = len(DTS)
    P, V = {}, {}
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
    VOL = np.column_stack([V[t] for t in tick])
    R = np.full_like(M, np.nan)
    R[1:] = M[1:] / M[:-1] - 1
    bench = spx_daily(DTS)
    if bench is None:
        raise SystemExit("대조군(S&P 500 PR)을 읽지 못했다 — 판정을 낼 수 없다.")

    def roll_mean(A_, w):
        out = np.full_like(A_, np.nan)
        for i in range(w, A_.shape[0]):
            out[i] = np.nanmean(A_[i - w + 1:i + 1], axis=0)
        return out

    def ratio(w):
        out = np.full_like(M, np.nan)
        out[w:] = M[w:] / M[:-w] - 1
        return out

    with np.errstate(invalid="ignore", divide="ignore"):
        mom12, mom6, mom3, mom1 = ratio(252), ratio(126), ratio(63), ratio(21)
        sma200, sma50 = roll_mean(M, 200), roll_mean(M, 50)
        vol60 = np.full_like(M, np.nan)
        skew60 = np.full_like(M, np.nan)
        ivol = np.full_like(M, np.nan)
        maxret = np.full_like(M, np.nan)
        hi52 = np.full_like(M, np.nan)
        lo52 = np.full_like(M, np.nan)
        beta = np.full_like(M, np.nan)
        amihud = np.full_like(M, np.nan)
        dvol = np.log(np.maximum(M * VOL, 1.0))
        for i in range(252, n):
            w = R[i - 59:i + 1]
            mu_ = np.nanmean(w, axis=0)
            sd_ = np.nanstd(w, axis=0)
            vol60[i] = sd_
            with np.errstate(invalid="ignore", divide="ignore"):
                skew60[i] = np.nanmean((w - mu_) ** 3, axis=0) / np.maximum(sd_, 1e-12) ** 3
            maxret[i] = np.nanmax(R[i - 20:i + 1], axis=0)
            win = M[i - 251:i + 1]
            hi52[i] = M[i] / np.nanmax(win, axis=0) - 1
            lo52[i] = M[i] / np.nanmin(win, axis=0) - 1
            bm = bench[i - 119:i + 1]
            bb = R[i - 119:i + 1]
            bv = np.nanvar(bm)
            if bv > 0:
                bt = np.nanmean((bb - np.nanmean(bb, axis=0)) *
                                (bm - np.nanmean(bm))[:, None], axis=0) / bv
                beta[i] = bt
                # 특이변동성 = 시장 회귀 잔차의 표준편차(같은 120일 창)
                resid = bb - bt[None, :] * bm[:, None]
                ivol[i] = np.nanstd(resid, axis=0)
            amihud[i] = np.nanmean(np.abs(R[i - 20:i + 1]) /
                                   np.maximum(M[i - 20:i + 1] * VOL[i - 20:i + 1], 1.0), axis=0)
        v20, v60 = roll_mean(VOL, 20), roll_mean(VOL, 60)
        vtr = v20 / v60

    # 시장 상태 — 전 종목 공통. 열로 펴서 같은 값을 모든 종목에 준다.
    def bcast(vec):
        return np.repeat(np.asarray(vec, float)[:, None], M.shape[1], axis=1)
    bc = np.nancumprod(1 + np.nan_to_num(bench))
    bsma = np.full(n, np.nan)
    for i in range(200, n):
        bsma[i] = bc[i] / np.nanmean(bc[i - 199:i + 1]) - 1
    bvol = np.full(n, np.nan)
    for i in range(60, n):
        bvol[i] = np.nanstd(bench[i - 59:i + 1])
    A_ = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    apos = {d: i for i, d in enumerate(A_.get("dates") or [])}

    def align_px(tk):
        raw = (A_.get("px") or {}).get(tk) or []
        out, last = np.full(n, np.nan), np.nan
        for i, d in enumerate(DTS):
            j = apos.get(d)
            if j is not None and j < len(raw) and raw[j] is not None:
                last = float(raw[j])
            out[i] = last
        return out

    def align_macro(sid):
        m = (A_.get("macro") or {}).get(sid) or {}
        ks = sorted(m)
        out, last, j = np.full(n, np.nan), np.nan, 0
        for i, d in enumerate(DTS):
            while j < len(ks) and ks[j] <= d:
                last = m[ks[j]]; j += 1
            out[i] = last
        return out

    F = [mom12 - mom1, -mom1, mom6 - mom1, mom3,
         vol60, ivol, skew60,
         M / sma200 - 1, M / sma50 - 1, hi52, lo52, maxret,
         vtr, dvol, amihud, beta,
         bcast(bsma), bcast(bvol), bcast(align_px("^VIX")), bcast(align_macro("T10Y2Y"))]
    assert len(F) == len(FEATS_WIDE), "특징 수와 이름표가 어긋났다"

    fwd = np.full_like(M, np.nan)
    fwd[:-HOLD - 1] = M[HOLD + 1:] / M[1:-HOLD] - 1
    fwd_b = np.full(n, np.nan)
    fwd_b[:-HOLD - 1] = bc[HOLD + 1:] / bc[1:-HOLD] - 1

    start = 260
    st2 = start + 252
    if st2 >= n - 40:
        return None
    month_end = [i for i in range(st2, n - 1) if DTS[i][:7] != DTS[i + 1][:7]]

    hold, nav, rets, bn, brs = [], [100.0], [], [100.0], []
    turn = 0
    mdl, mu, sd = None, None, None
    Xs, ys, built_to = [], [], start
    for i in range(st2 + 1, n):
        if (i - 1) in month_end:
            hi = i - HOLD - 2
            for k in range(built_to, hi):
                row = np.column_stack([f[k] for f in F])
                yk = fwd[k] - fwd_b[k]
                ok = np.isfinite(row).all(axis=1) & np.isfinite(yk)
                if ok.sum() < 50:
                    continue
                Xs.append(row[ok]); ys.append(yk[ok])
            built_to = max(built_to, hi)
            if Xs:
                Xtr = np.vstack(Xs); ytr = np.concatenate(ys)
                mu, sd = zfit(Xtr)
                Z = (Xtr - mu) / sd
                mdl = forest_fit(Z, ytr) if model == "forest" else ridge(Z, ytr, L2)
            if mdl is not None:
                row = np.column_stack([f[i - 1] for f in F])
                ok = np.isfinite(row).all(axis=1)
                if ok.sum() >= TOPN:
                    z = (row[ok] - mu) / sd
                    sc = forest_pred(mdl, z) if model == "forest" else (mdl[0] + z @ mdl[1:])
                    names_ok = np.array(tick)[ok]
                    new = list(names_ok[np.argsort(-sc)[:TOPN]])
                    turn += len(set(new) - set(hold))
                    hold = new
        rr = 0.0
        if hold:
            idx = [tick.index(t) for t in hold]
            v = R[i, idx]
            rr = float(np.nanmean(v)) if np.isfinite(v).any() else 0.0
        rets.append(rr); nav.append(nav[-1] * (1 + rr))
        br = bench[i] if np.isfinite(bench[i]) else 0.0
        brs.append(br); bn.append(bn[-1] * (1 + br))

    dd = DTS[st2:]
    ms, mb = ann_stats(nav, dd, RF), ann_stats(bn, dd, RF)
    step = max(1, len(nav) // 220)
    yrs = max(1e-9, (n - st2) / 252)
    sid = "ml-xsec-w-forest" if model == "forest" else "ml-xsec-w-ridge"
    nm = ("특징 20개 종목선택 (랜덤 포레스트)" if model == "forest"
          else "특징 20개 종목선택 (릿지)")
    return {
        "sid": sid, "arch": None,
        "chart": curve_pack(dd, nav, bn),
        "bench_label": "S&P 500(PR) 매수후보유",
        "holdings": {"kind": "xsec", "as_of": DTS[-1], "n": len(hold),
                     "tickers": sorted(hold),
                     "names": {t: NMX.get(t, t) for t in sorted(hold)},
                     "note": "특징 20개 판이 지금 담고 있는 %d종목이다." % len(hold)},
        "name": nm,
        "rule": ("가격·거래 16개와 시장상태 4개, 모두 %d개 특징으로 향후 21거래일 초과수익을 "
                 "%s로 예측해 상위 %d종목을 동일가중 보유. 월말 재학습·리밸런스."
                 % (len(FEATS_WIDE), "랜덤 포레스트" if model == "forest" else "릿지", TOPN)),
        "why": ("앞 판(특징 7개)에서 트리·2차확장이 선형을 못 이겼는데, 특징이 적으면 상호작용이 "
                "값을 할 자리 자체가 없다. 특징을 20개로 늘리고 시장상태 4개를 더해 다시 묻는다 — "
                "시장상태는 전 종목이 같은 값이라 선형 횡단면 순위를 전혀 못 바꾸고 오직 "
                "상호작용으로만 값을 한다. 그래서 이 판이 '비선형이 값을 하는가'를 더 정직하게 묻는다."),
        "note": ("재무는 넣지 않았다. 시점 정합으로 자르면 eq·asset 이 2022-08 부터라 검정 구간이 "
                 "2년 아래로 떨어지는데, 이 파일 규칙이 그 길이를 판정 불가로 못 박고 있다. "
                 "창을 반토막 내면 특징 효과와 구간 효과가 섞인다. 앞 판은 손대지 않았다 — "
                 "사전등록물은 결과가 나온 뒤 고치면 의미를 잃으므로 별개 등록으로 둔다."),
        "start": DTS[st2], "end": DTS[-1], "n_days": n - st2,
        "metrics": ms, "bench": mb, "bench_unstable": False,
        "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
        "t": tstat(rets, brs), "risk": risk_bootstrap(rets, brs),
        "turnover": round(turn / TOPN / yrs, 1),
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
                      (lambda: stock_selection(RF, mode="value"), "횡단면 종목선택(크기)"),
                      # 같은 특징·창·표준화에서 목표와 모델만 바꾼 두 판. 셋을 나란히 둬야
                      # '방향이 크기보다 낫다'·'참는 것이 값을 한다'가 이 데이터에서 갈린다.
                      (lambda: stock_selection(RF, mode="dir"), "횡단면 종목선택(방향)"),
                      (lambda: stock_selection(RF, mode="conf"), "횡단면 종목선택(고신뢰)"),
                      # 같은 목표·같은 릿지에서 특징 사상만 2차로 편 판. 크기 예측판과 나란히
                      # 둬야 '비선형 상호작용이 값을 하는가'가 갈린다.
                      (lambda: stock_selection(RF, mode="inter"), "횡단면 종목선택(상호작용)"),
                      # 논문의 승자 모델. 상호작용판과 나란히 둬야 '상호작용이냐 형태냐'가 갈린다.
                      (lambda: stock_selection(RF, mode="tree"), "횡단면 종목선택(랜덤 포레스트)"),
                      # 새 사전등록 — 특징 20개. 같은 특징에서 선형과 트리를 나란히 돌려야
                      # '특징을 늘리면 비선형이 이기는가'가 갈린다.
                      (lambda: stock_selection_wide(RF, model="ridge"), "특징20 종목선택(릿지)"),
                      (lambda: stock_selection_wide(RF, model="forest"), "특징20 종목선택(포레스트)"),
                      (lambda: guru_clone(RF), "13F 컨빅션 복제")):
        try:
            r = fn()
        except Exception as e:
            print("  ❌ %s %s: %s" % (label, type(e).__name__, e)); continue
        if r and r.get("__collapsed__"):
            # 문턱이 한 번도 물지 않은 판 — 방향 예측판과 같은 포트폴리오라 행을 만들지 않고,
            # 방향 예측판의 설명에 그 사실을 적는다. 결과가 없어서가 아니라 결과가 '차이 없음'이다.
            d = r["diag"]
            for x in rows:
                if x.get("sid") == "ml-xsec-dir":
                    x["note"] += (" ⚠ 고신뢰 베팅(확률 %d%% 이상만 매수)도 같이 돌렸는데, "
                                  "리밸런스 %d회 내내 상위 %d종목의 확률이 문턱을 넘어(%.3f~%.3f) "
                                  "한 번도 걸러지지 않았다 — 이 표본에서 두 규칙은 같은 포트폴리오다. "
                                  "문턱을 결과 보고 올리면 사전등록이 무의미해지므로 값을 고치지 않고 "
                                  "이 사실만 남긴다."
                                  % (round(CONF * 100), d["n_rebal"], x["holdings"]["n"],
                                     d["p_min"], d["p_max"]))
            print("  · 고신뢰 베팅: 문턱 미작동 — 방향 예측판과 동일, 행 생성 안 함")
            continue
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
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "ML 사전등록 검정")
