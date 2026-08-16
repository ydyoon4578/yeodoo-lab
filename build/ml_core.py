# -*- coding: utf-8 -*-
"""build/ml_core.py — 사전등록 ML6 의 수치 알맹이. numpy 만 쓴다.

왜 손으로 짜나.
  이 저장소에는 scikit-learn 이 없고, CI 에도 넣지 않는다. 넣으면 **숨은 기본값**이
  판정에 섞인다 — 정규화 여부·절편 처리·수렴 기준·난수 소비 순서가 전부 라이브러리
  버전에 딸려 오고, 그것들은 등록서에 못박을 수 없는 자유도다.
  🚨 이 랩의 판정은 «무엇을 고정했나» 로 서는데, 고정한 줄 알았던 값이 라이브러리 안에
    있으면 그 판정은 못 쓴다. 그래서 등록서 §4 에 적은 초매개변수가 **이 파일의 상수와
    일대일로 대응**하도록 짠다.

여기 있는 것은 전부 «적합 → 예측» 뿐이다. 종목을 고르거나 비중을 주는 일은 하지 않는다 —
그건 tech_backtest 의 채점기·선택기 한 벌이 맡는다(사본을 만들지 않는다는 규약).

  PREREG-2026-08-16-ML6.md §3·§4 가 이 파일의 명세다.
"""
from __future__ import annotations
import sys

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 ⚠·— 출력 시 죽지 않게
except Exception: pass
import numpy as np

# ── 등록서 §4 의 초매개변수. 결과를 보고 바꾸지 않는다 ────────────────────
RIDGE_LAM = 10.0        # ① 능형 λ (z-점수된 12특징 기준, 절편 제외)
LOGIT_LAM = 10.0        # ③ 로지스틱 L2 λ
LOGIT_ITER = 30         # ③ IRLS 최대 반복
LOGIT_TOP = 0.20        # ③ 목표 = 다음 달 수익 상위 20%
TREE_N = 50             # ⑥ 배깅 트리 수
TREE_DEPTH = 3          # ⑥ 깊이
TREE_LEAF = 50          # ⑥ 잎 최소 표본
TREE_MTRY = 4           # ⑥ 분기마다 뽑는 특징 수 (12 중 4)
ERC_SHRINK = 0.2        # ④ 공분산 대각 방향 축소
ERC_ITER = 200          # ④ 곱셈 갱신 반복
WINSOR = 3.0            # §3 윈저라이즈 ±3
MIN_FEAT = 9            # §3 12개 중 4개 이상 결측이면 후보에서 뺀다 → 9개 이상 있어야 한다


def zscore(X):
    """열별 ±3 윈저라이즈 후 z-점수. 결측(NaN)은 0(= 그달 평균)으로 둔다.

    🚨 윈저라이즈를 z-점수 **앞에** 한다. 뒤에 하면 극단값이 이미 평균·표준편차를
      끌고 간 뒤라 자르는 뜻이 없다.
    ⚠ 표준편차 0 인 열(그달 전 종목이 같은 값)은 0 으로 둔다 — 나누면 inf 가 되고,
      그 열은 정보가 없으므로 0 이 맞다.
    """
    X = np.asarray(X, dtype=float).copy()
    out = np.zeros_like(X)
    for j in range(X.shape[1]):
        col = X[:, j]
        m = np.isfinite(col)
        if m.sum() < 3:
            continue
        v = col[m]
        mu, sd = v.mean(), v.std()
        if sd > 0:
            v = np.clip(v, mu - WINSOR * sd, mu + WINSOR * sd)
            mu, sd = v.mean(), v.std()
        if sd <= 0:
            continue
        out[m, j] = (v - mu) / sd
    return out


def ridge_fit(X, y, lam=RIDGE_LAM):
    """능형회귀. 절편은 벌점에서 뺀다(중심화로 처리).

    ⚠ 정규방정식을 푼다. 12특징이라 조건수가 문제되지 않고, 반복 해법을 쓰면
      수렴 기준이라는 새 자유도가 생긴다.
    """
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    if X.shape[0] < X.shape[1] + 2:
        return None
    xm, ym = X.mean(0), y.mean()
    Xc, yc = X - xm, y - ym
    A = Xc.T @ Xc + lam * np.eye(X.shape[1])
    try:
        b = np.linalg.solve(A, Xc.T @ yc)
    except np.linalg.LinAlgError:
        return None
    return (b, ym - xm @ b)


def ridge_pred(model, X):
    b, a = model
    return np.asarray(X, float) @ b + a


def logit_fit(X, y, lam=LOGIT_LAM, iters=LOGIT_ITER):
    """L2 로지스틱 — IRLS. y 는 0/1.

    🚨 가중치가 0 에 붙으면 IRLS 의 W 가 특이해진다. 그래서 w 에 하한(1e-6)을 둔다 —
      이것은 «수렴을 돕는 손질» 이 아니라 **없으면 계산이 죽는 자리**다.
    ⚠ 절편은 벌점에서 뺀다(마지막 열이 1 인 설계행렬을 쓰고 벌점 대각의 끝을 0 으로).
    """
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n, p = X.shape
    if n < p + 10 or y.sum() < 5 or (n - y.sum()) < 5:
        return None
    Z = np.hstack([X, np.ones((n, 1))])
    P = lam * np.eye(p + 1)
    P[p, p] = 0.0
    b = np.zeros(p + 1)
    for _ in range(iters):
        eta = np.clip(Z @ b, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(mu * (1 - mu), 1e-6, None)
        g = Z.T @ (y - mu) - P @ b
        H = (Z * w[:, None]).T @ Z + P
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return None
        b = b + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return b


def logit_pred(b, X):
    X = np.asarray(X, float)
    Z = np.hstack([X, np.ones((X.shape[0], 1))])
    return 1.0 / (1.0 + np.exp(-np.clip(Z @ b, -30, 30)))


# ── ⑥ 배깅 회귀트리 ────────────────────────────────────────────────────
def _grow(X, y, idx, depth, rng):
    """한 노드. 돌려주는 것은 (특징, 임계, 왼쪽, 오른쪽) 또는 (None, 예측값)."""
    if depth >= TREE_DEPTH or len(idx) < 2 * TREE_LEAF:
        return (None, float(y[idx].mean()) if len(idx) else 0.0)
    p = X.shape[1]
    feats = rng.choice(p, size=min(TREE_MTRY, p), replace=False)
    best = None
    yv = y[idx]
    tot = yv.sum()
    n = len(idx)
    for f in feats:
        xv = X[idx, f]
        order = np.argsort(xv, kind="stable")
        xs, ys = xv[order], yv[order]
        csum = np.cumsum(ys)
        # 잎 최소 표본을 지키는 분기점만 본다
        lo, hi = TREE_LEAF, n - TREE_LEAF
        if hi <= lo:
            continue
        k = np.arange(lo, hi)
        # 같은 값에서 자르면 안 된다(왼·오른쪽이 안 갈린다)
        ok = xs[k] < xs[k + 1] if len(k) else np.array([], bool)
        if not ok.any():
            continue
        k = k[ok]
        sl = csum[k - 1]
        nl = k.astype(float)
        # 제곱오차 감소 = 왼쪽합²/n_l + 오른쪽합²/n_r (상수항 제외)
        gain = sl * sl / nl + (tot - sl) ** 2 / (n - nl)
        b = int(np.argmax(gain))
        if best is None or gain[b] > best[0]:
            best = (gain[b], int(f), 0.5 * (xs[k[b]] + xs[k[b] + 1]))
    if best is None:
        return (None, float(yv.mean()))
    _g, f, thr = best
    m = X[idx, f] <= thr
    return (f, thr,
            _grow(X, y, idx[m], depth + 1, rng),
            _grow(X, y, idx[~m], depth + 1, rng))


def _tpred(node, x):
    while node[0] is not None:
        node = node[2] if x[node[0]] <= node[1] else node[3]
    return node[1]


def tree_fit(X, y, seed):
    """행 부트스트랩 + 특징 임의추출 배깅. seed 는 월 인덱스(등록서 §4⑥)."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n = X.shape[0]
    if n < 4 * TREE_LEAF:
        return None
    rng = np.random.default_rng(int(seed))
    trees = []
    for _ in range(TREE_N):
        idx = rng.integers(0, n, size=n)
        trees.append(_grow(X, y, idx, 0, rng))
    return trees


def tree_pred(trees, X):
    X = np.asarray(X, float)
    out = np.zeros(X.shape[0])
    for i in range(X.shape[0]):
        out[i] = np.mean([_tpred(t, X[i]) for t in trees])
    return out


# ── ④ 동일위험기여(ERC) 가중 ────────────────────────────────────────────
def erc_weights(C, shrink=ERC_SHRINK, iters=ERC_ITER):
    """공분산 C → 각 종목의 위험기여가 같아지는 롱온리 비중.

    곱셈 갱신: w_i ← w_i · (b_i / (w_i·(Cw)_i)) ^ (1/2) 후 정규화.
    b_i = 1/n (동일 위험예산). 표준적인 형태이고 롱온리·합1 을 자동으로 지킨다.

    🚨 축소를 먼저 한다. 60일 표본으로 n×n 공분산을 재면 거의 특이하다 —
      대각 방향으로 0.2 축소해야 역행렬을 안 쓰는 이 갱신도 안정된다.
    ⚠ 분산이 0 이거나 음수인 종목이 있으면 그 종목만 빼고 나머지로 푼다. 통째로
      포기하면 그달이 무보유가 되어 «가중 때문에 성적이 달라진 것»과 구별이 안 된다.
    """
    C = np.asarray(C, float)
    n = C.shape[0]
    if n == 0:
        return None
    d = np.diag(C).copy()
    good = np.isfinite(d) & (d > 0)
    if good.sum() < 2:
        return None
    C = C[np.ix_(good, good)]
    m = C.shape[0]
    C = (1.0 - shrink) * C + shrink * np.diag(np.diag(C))
    w = np.ones(m) / m
    b = np.ones(m) / m
    for _ in range(iters):
        Cw = C @ w
        rc = w * Cw
        if not np.all(np.isfinite(rc)) or rc.sum() <= 0:
            return None
        w = w * np.sqrt(np.clip(b / np.maximum(rc, 1e-18), 1e-12, 1e12))
        w = np.clip(w, 1e-12, None)
        w = w / w.sum()
    out = np.zeros(n)
    out[good] = w
    return out


# ── ⑤ 평균연결 계층군집 ────────────────────────────────────────────────
def corr_clusters(C, k):
    """상관행렬 C → 평균연결 계층군집을 k 개로 자른 라벨 배열.

    거리 = √(2(1−ρ)) — 상관을 거리로 옮기는 표준형(López de Prado 도 같은 변환을 쓴다).
    ⚠ 라이브러리를 안 쓰므로 O(n³) 이다. 유니버스 518종·월 170회면 감당된다.
    """
    C = np.asarray(C, float)
    n = C.shape[0]
    if n <= k:
        return np.arange(n)
    D = np.sqrt(np.maximum(2.0 * (1.0 - np.clip(C, -1, 1)), 0.0))
    np.fill_diagonal(D, np.inf)
    members = [[i] for i in range(n)]
    alive = list(range(n))
    Dw = D.copy()
    while len(alive) > k:
        sub = np.array(alive)
        M = Dw[np.ix_(sub, sub)]
        a, b = np.unravel_index(np.argmin(M), M.shape)
        i, j = sub[a], sub[b]
        if not np.isfinite(M[a, b]):
            break
        ni, nj = len(members[i]), len(members[j])
        # 평균연결 — 새 거리는 표본 수 가중 평균
        newd = (ni * Dw[i, :] + nj * Dw[j, :]) / (ni + nj)
        members[i] = members[i] + members[j]
        Dw[i, :] = newd
        Dw[:, i] = newd
        Dw[i, i] = np.inf
        alive.remove(j)
    lab = np.zeros(n, int)
    for c, i in enumerate(alive):
        for m in members[i]:
            lab[m] = c
    return lab
