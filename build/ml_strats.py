# -*- coding: utf-8 -*-
"""build/ml_strats.py — 사전등록 ML6 의 특징 패널과 채점. 명세는 PREREG-2026-08-16-ML6.md.

무엇을 하나.
  ① 월말마다 12특징 × 후보종목 행렬을 만든다(패널).
  ② 그 패널로 매월 재적합해 다음 달 초과수익을 예측한다.
  ③ 예측을 (점수, 티커) 목록으로 돌려준다 — 선택과 비중은 tech_backtest 가 맡는다.

🚨 특징을 **다시 구현하지 않는다.** 12개 중 8개는 `S["fn"]` 이 None 이고
  `xsec_score_at` 안의 갈래로 계산된다(x-volvol·x-lowbeta·x-dist200·x-52wh·x-rskew·
  x-mommvol·x-drift-t·x-varratio). 그러니 산식을 옮겨 적는 순간 **채점기가 두 벌**이 되고,
  이 저장소는 정확히 그 이유로 하루에 넷을 잡은 적이 있다(xsec_score_at 머리말).
  → 특징값도 `xsec_score_at` 을 그대로 불러서 얻는다. 느리지만 갈릴 자리가 없다.

🚨 풀(pool)을 그대로 물려준다. 소급 레그는 None(오늘의 518종), 시점정확 레그는 그달 실제
  편입명단이다. **학습 행도 같은 풀로 거른다** — 안 그러면 과거 학습이 «오늘까지 살아남은
  종목» 만 보고 이루어져, 재려던 생존편향이 모형 안으로 숨어 들어간다.
"""
from __future__ import annotations
import sys

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 ⚠·— 출력 시 죽지 않게
except Exception: pass
import numpy as np

import ml_core as MC

# 등록서 §2 — 순서를 바꾸지 않는다(계수 보고가 이 순서로 나간다).
FEATS = ["x-mom12", "x-rev1m", "x-ltrev", "x-lowvol", "x-volvol", "x-lowbeta",
         "x-dist200", "x-52wh", "x-rskew", "x-mommvol", "x-drift-t", "x-varratio"]
ML_SIDS = ("m-ridge", "m-ridge-w", "m-logit", "m-erc", "m-clust", "m-tree")
MIN_TRAIN_M = 36        # 등록서 §3 — 월말 36개가 쌓일 때까지 무보유

_PANEL = {}             # (레그, 격자길이) → 패널
_FIT = {}               # (sid, 레그, 격자길이, 월인덱스) → 예측 dict


def _panel_key(X, pool_at):
    """🚨 레그 태그로 가른다. pit_backtest 는 **소급 레그도** pool 을 준다(오늘 명단) —
    «pool_at 이 있으면 PIT» 로 가르면 두 레그가 같은 패널을 나눠 쓰고, 그 순간 편향이
    0 으로 나온다(잴 것이 사라진다). 부르는 쪽이 X["ml_leg"] 로 못박게 한다."""
    return (X.get("ml_leg") or ("pit" if pool_at is not None else "lab"), len(X["dates"]))


def build_panel(TB, X, pool_at=None, log=True):
    """월말마다 (특징 12, 다음달 초과수익) 을 모은다.

    돌려주는 것: {"ms": [월말 실행인덱스…], "F": {m: {티커: [12]}}, "Y": {m: {티커: y}}}
    y 는 **그달 후보 평균을 뺀** 다음 달 수익이다(등록서 §3).
    ⚠ 마지막 월말은 y 가 없다 — 학습에 안 들어가고 예측 대상으로만 쓰인다.
    """
    key = _panel_key(X, pool_at)
    if key in _PANEL:
        return _PANEL[key]
    S = {s["sid"]: s for s in TB.STRATS}
    dates, px = X["dates"], X["px"]
    n = len(dates)
    ms = [j + 1 for j in TB.month_ends(dates) if TB.MIN_HIST <= j + 1 <= n - 1]
    F, Y, POOL = {}, {}, {}
    for k, i in enumerate(ms):
        # ⚠ pool_at(i-1) 이다. 부르는 쪽(pit_backtest)이 실행 인덱스 i 에 대해 i-1 의
        #   명단으로 채점한다 — 여기서 i 를 쓰면 패널과 채점이 한 달씩 어긋난다.
        pool = pool_at(i - 1) if pool_at is not None else None
        POOL[i] = pool
        vals = {}
        for fi, f in enumerate(FEATS):
            sc, _ir, _cr = TB.xsec_score_at(S[f], i, X, pool)
            for v, t in sc:
                vals.setdefault(t, [np.nan] * len(FEATS))[fi] = v
        F[i] = {t: r for t, r in vals.items()
                if sum(1 for x in r if x == x) >= MC.MIN_FEAT}
        if k + 1 < len(ms):
            j2 = ms[k + 1]
            raw = {}
            for t in F[i]:
                a = px.get(t)
                if not a:
                    continue
                p0 = a[i - 1] if i - 1 < len(a) else None
                p1 = a[j2 - 1] if j2 - 1 < len(a) else None
                if p0 and p1 and p0 > 0:
                    raw[t] = p1 / p0 - 1.0
            if raw:
                mu = sum(raw.values()) / len(raw)
                Y[i] = {t: v - mu for t, v in raw.items()}   # 횡단면 중심화
        if log and k % 40 == 0:
            print("    [ML패널] %s %3d/%d · 종목 %d" % (key[0], k, len(ms), len(F[i])))
    out = {"ms": ms, "F": F, "Y": Y, "POOL": POOL}
    _PANEL[key] = out
    if log:
        print("    [ML패널] %s 완성 — 월말 %d · 학습가능 %d" % (key[0], len(ms), len(Y)))
    return out


def _train_rows(P, i, pool):
    """i 이전 월말의 (특징, y) 행. **그달 풀 안의 종목만** 쓴다(생존편향 차단)."""
    Xs, ys = [], []
    for m in P["ms"]:
        if m >= i or m not in P["Y"]:
            continue
        pm = P["POOL"].get(m)
        for t, r in P["F"][m].items():
            if pm is not None and t not in pm:
                continue
            y = P["Y"][m].get(t)
            if y is None:
                continue
            Xs.append(r)
            ys.append(y)
    return np.array(Xs, float), np.array(ys, float)


def score(TB, S, i, X, tickers, pool=None, pool_at=None):
    """ML 규칙의 (점수, 티커) 목록. 학습 자료가 모자라면 빈 목록(= 그달 무보유)."""
    sid = S["sid"]
    base = "m-erc" if sid == "m-erc" else sid
    if base in ("m-erc", "m-clust"):
        # ④⑤ 는 예측 모형이 아니다 — 선택·비중이 x-mom12 와 상관구조에서 나온다.
        s2 = {s["sid"]: s for s in TB.STRATS}["x-mom12"]
        sc, _ir, _cr = TB.xsec_score_at(s2, i, X, pool)
        return sc
    P = build_panel(TB, X, pool_at)
    ck = (sid, _panel_key(X, pool_at)[0], len(X["dates"]), i)
    if ck in _FIT:
        return _FIT[ck]
    if i not in P["F"]:
        return []
    n_hist = sum(1 for m in P["ms"] if m < i and m in P["Y"])
    if n_hist < MIN_TRAIN_M:
        return []
    Xtr, ytr = _train_rows(P, i, None)
    if len(ytr) < 200:
        return []
    Ztr = MC.zscore(Xtr)
    cur = [(t, r) for t, r in P["F"][i].items()
           if (pool is None or t in pool) and t in set(tickers)]
    if not cur:
        return []
    Zcur = MC.zscore(np.array([r for _t, r in cur], float))
    if sid in ("m-ridge", "m-ridge-w"):
        mdl = MC.ridge_fit(Ztr, ytr)
        if mdl is None:
            return []
        pred = MC.ridge_pred(mdl, Zcur)
    elif sid == "m-logit":
        thr = np.quantile(ytr, 1.0 - MC.LOGIT_TOP)
        b = MC.logit_fit(Ztr, (ytr >= thr).astype(float))
        if b is None:
            return []
        pred = MC.logit_pred(b, Zcur)
    elif sid == "m-tree":
        tr = MC.tree_fit(Ztr, ytr, seed=i)
        if tr is None:
            return []
        pred = MC.tree_pred(tr, Zcur)
    else:
        return []
    sc = sorted(((float(p), t) for p, (t, _r) in zip(pred, cur)), reverse=True)
    _FIT[ck] = sc
    return sc


def weights(TB, S, i, X, hold, pool=None, pool_at=None):
    """②④⑤ 의 비중. None 이면 동일가중(엔진 기본)."""
    sid = S["sid"]
    if sid == "m-ridge-w":
        sc = score(TB, S, i, X, hold, pool, pool_at)
        d = {t: v for v, t in sc if t in set(hold)}
        if len(d) < 2:
            return None
        lo = min(d.values())
        # 등록서 §4② — 10위 예측값을 뺀다. 전부 같으면(폭 0) 동일가중으로 떨어진다.
        raw = {t: max(v - lo, 0.0) for t, v in d.items()}
        s = sum(raw.values())
        if s <= 0:
            return None
        return {t: v / s for t, v in raw.items()}
    if sid == "m-erc":
        R = X["R"]
        rows = []
        for t in hold:
            a = R.get(t) or []
            w = [x for x in a[max(0, i - 61):i - 1] if x is not None]
            rows.append(w if len(w) >= 40 else None)
        L = min((len(r) for r in rows if r), default=0)
        if L < 40:
            return None
        M = np.array([r[-L:] for r in rows if r], float)
        keep = [t for t, r in zip(hold, rows) if r]
        C = np.cov(M)
        if C.ndim == 0:
            return None
        w = MC.erc_weights(np.atleast_2d(C))
        if w is None:
            return None
        return {t: float(x) for t, x in zip(keep, w) if x > 0}
    return None


def cluster_pick(TB, S, i, X, sc, topn):
    """⑤ 상관 클러스터 10개 × 각 1종. sc 는 x-mom12 점수 내림차순."""
    R = X["R"]
    cand = [t for _v, t in sc][:120]        # 상위 120종 안에서 군집 — O(n³) 을 묶어 둔다
    rows, keep = [], []
    for t in cand:
        a = R.get(t) or []
        w = [x for x in a[max(0, i - 61):i - 1] if x is not None]
        if len(w) >= 40:
            rows.append(w)
            keep.append(t)
    if len(keep) <= topn:
        return [t for _v, t in sc][:topn]
    L = min(len(r) for r in rows)
    M = np.array([r[-L:] for r in rows], float)
    C = np.corrcoef(M)
    if not np.all(np.isfinite(C)):
        return [t for _v, t in sc][:topn]
    lab = MC.corr_clusters(C, topn)
    rank = {t: k for k, (_v, t) in enumerate(sc)}
    best = {}
    for t, c in zip(keep, lab):
        c = int(c)
        if c not in best or rank.get(t, 1e9) < rank.get(best[c], 1e9):
            best[c] = t
    return sorted(best.values(), key=lambda t: rank.get(t, 1e9))[:topn]
