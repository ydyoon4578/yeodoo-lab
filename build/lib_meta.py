# -*- coding: utf-8 -*-
"""build/lib_meta.py — 라이브러리 결합 L1 «MM2S-β 양면 볼록성 배분» + 대조군 + 평가 틀(월 단위) → data/_libmeta_L1.json

사전등록: build/PREREG-2026-09-24-LIBMETA.md (배치 L 1부 · 전방 판정 가족 F-LIB m = 4)
로더: build/lib_loader.py (U_LIB 132 가족 · 순수익 = r − cost_drag/12 · 판정선 SPY 총수익)

L1 한 줄: 분기말마다 라이브러리 가족의 **조건부 베타만**(지수 상승월 c⁺ · 하락월 c⁻ — 평균 수익은 쓰지 않는다) 추정해 경험적 베이즈로
  줄이고, 지수 급등월·급락월 시나리오에서 «둘 중 나쁜 쪽» 기대 초과를 최대로 하는 보유 h 를 선형계획으로 푼다. 절반은 SPY 에 묶는다.
  대칭 베타 기울이기는 급등·급락에서 서로 상쇄되므로 양쪽을 함께 올릴 길은 «상승 포착 > 하락 포착» 볼록성뿐이다.

🚨 표본 안(2019-10 ~ 2026-08)은 «오염 측정» — 라이브러리가 창 전체를 보고 걸러졌다. 판정은 전방에서만 한다(사전등록 §E).
🚨 --f0 는 결과(수익) 없이 비중·베타로만 F0 점검을 하고 멈춘다. 등록 커밋 뒤 가장 먼저 돈다.

  python build/lib_meta.py --dry                       # 등록 전 — 선형계획이 풀리는지만(수치 없음)
  LIBMETA_COMMIT=<커밋> python build/lib_meta.py --f0  # 등록 뒤 첫째 — 비중·베타만(규칙 수익 없음)
  LIBMETA_COMMIT=<커밋> python build/lib_meta.py       # 그다음 — 표본 안 오염 측정 + 대조군 + 평가
"""
from __future__ import annotations
import hashlib, io, json, math, os, subprocess, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_loader as LL               # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_libmeta_L1.json")
F0_OUT = os.path.join(DATA, "_libmeta_L1_f0.json")
PREREG = "build/PREREG-2026-09-24-LIBMETA.md"
W0 = "2016-10"                  # 창의 첫 온전한 달
FIRST_DEC, LAST_HOLD = "2019-09", "2026-08"
WMAX, WMIN = 60, 36
CAP, ANCHOR = 0.02, 0.5
KAPPA = 0.10 / 3                # %/월 · 거래 1 단위당(편도 10bp 를 3개월 보유로 나눔)
COST = 0.10                     # 편도 10bp = 0.10%
REPL = 0.95                     # 준복제 상관 문턱
SEED, NPERM = 20260814, 1000
NW_LAG = 3
TIMING_ROLES = {"타이밍오버레이", "위험방어", "배분기"}
# 자료 판 — CI 가 strategy_*.json 을 매일 다시 구우므로 로더는 이 커밋의 판을 git show 로 읽는다. 유니버스·패널 해시는 그 판의 값(대조한다).
DATA_REV = "9e8ebd40"
SCIPY_VER = "1.18.1"
SID_SHA = "17314587cbc4393eeda8b64bd0797d1b8e27def9daa15a65f755f579aa52f09e"
PANEL_SHA = "fb6369994074d529400cb37ed1fb96f59fa4c4ad5c50c7bf8977b7119ca47b8d"


# ── 달 산술 ──────────────────────────────────────────────────────────────
def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + m - 1 + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def mrange(a, b):
    out, x = [], a
    while x <= b:
        out.append(x)
        x = mshift(x, 1)
    return out


# ── 통계 도구 ─────────────────────────────────────────────────────────────
def nw_t(x, lag=NW_LAG):
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return None
    e = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else None


def ols_nw(y, X, lag=NW_LAG):
    """계수 · NW(lag) t."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    S = np.zeros((k, k))
    for t in range(n):
        S += np.outer(X[t], X[t]) * e[t] ** 2
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1)
        for t in range(L, n):
            G = np.outer(X[t], X[t - L]) * e[t] * e[t - L]
            S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return b, b / np.sqrt(np.diag(V))


def spearman(a, b):
    """동률을 평균 순위로 다루는 스피어만. 한쪽이 상수면 0."""
    from scipy.stats import rankdata
    ra, rb = rankdata(a), rankdata(b)
    if np.ptp(ra) == 0 or np.ptp(rb) == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


# ── 추정 ─────────────────────────────────────────────────────────────────
def hm_fit(x, s):
    """x = a + c⁺·s⁺ + c⁻·s⁻ + e (고전 공분산) → (a, c⁺, c⁻, V)."""
    X = np.column_stack([np.ones(len(s)), np.maximum(s, 0), np.minimum(s, 0)])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ x
    e = x - X @ b
    s2 = (e @ e) / (len(x) - 3)
    return b, s2 * XtX_inv


def eb_shrink(k, se2):
    """경험적 베이즈(모멘트법) — 동일가중 횡단면 평균 쪽으로."""
    kbar = float(np.mean(k))
    tau2 = max(0.0, float(np.var(k, ddof=1)) - float(np.mean(se2)))
    if tau2 <= 0:
        return np.full_like(k, kbar)
    B = se2 / (se2 + tau2)
    return kbar + (1 - B) * (k - kbar)


class Lib:
    def __init__(self, rev=DATA_REV):
        L = LL.load(end=LAST_HOLD, rev=rev)
        self.L = L
        self.reps = {it["sid"]: it for it in L["reps"]}
        self.panel = L["panel"]
        self.spy = L["etf"]["SPY"]
        self.etf = L["etf"]
        self.rf = L["rf"]
        ME = json.load(io.open(os.path.join(DATA, "mech_episodes.json"), encoding="utf-8"))
        self.sig = ME["sigma_pre"] * 100
        self.ME = ME
        self.decisions = [m for m in mrange(FIRST_DEC, LAST_HOLD) if int(m[5:7]) % 3 == 0 and m < LAST_HOLD]
        self.hold = mrange(mshift(FIRST_DEC, 1), LAST_HOLD)

    def window(self, t):
        avail = mrange(W0, t)
        return avail[-min(WMAX, len(avail)):]

    def universe(self, t):
        W = self.window(t)
        U = [s for s in sorted(self.panel) if all(m in self.panel[s] for m in W)]
        # 준복제 거르기 — 떼어 낸 접미사가 적은 쪽(같으면 sid 앞)을 남긴다
        order = sorted(U, key=lambda s: (LL.stem(s)[1], s))
        X = {s: np.array([self.panel[s][m] - self.spy[m] for m in W]) for s in order}
        kept = []
        for s in order:
            if all(abs(np.corrcoef(X[s], X[k])[0, 1]) <= REPL for k in kept):
                kept.append(s)
        return sorted(kept), W

    def estimate(self, U, W):
        s = np.array([self.spy[m] for m in W])
        a, cp, cm, SEL, SED, SEA = [], [], [], [], [], []
        AU, SEU = [], []
        Xu = np.column_stack([np.ones(len(s)), s]); XuI = np.linalg.inv(Xu.T @ Xu)
        Xd = []
        for sid in U:
            x = np.array([self.panel[sid][m] - self.spy[m] for m in W])
            b, V = hm_fit(x, s)
            a.append(b[0]); cp.append(b[1]); cm.append(b[2])
            SEL.append((V[1, 1] + V[2, 2] + 2 * V[1, 2]) / 4)
            SED.append(V[1, 1] + V[2, 2] - 2 * V[1, 2])
            SEA.append(V[0, 0])
            bu = XuI @ Xu.T @ x; eu = x - Xu @ bu                     # P5 용 무조건부 알파(단순 회귀 절편 · 고전 SE)
            AU.append(bu[0]); SEU.append((eu @ eu) / (len(x) - 2) * XuI[0, 0])
            Xd.append(x - x.mean())
        a, cp, cm = np.array(a), np.array(cp), np.array(cm)
        Lh, Dh = (cp + cm) / 2, cp - cm
        Lt, Dt = eb_shrink(Lh, np.array(SEL)), eb_shrink(Dh, np.array(SED))
        at = eb_shrink(np.array(AU), np.array(SEU))
        return {"Lh": Lh, "Dh": Dh, "Lt": Lt, "Dt": Dt, "cpt": Lt + Dt / 2, "cmt": Lt - Dt / 2, "at": at,
                "Xd": np.array(Xd)}

    def scenarios(self, t):
        ms = [m for m in sorted(self.spy) if "2006-02" <= m <= t]
        s = np.array([self.spy[m] for m in ms])
        S, C = s[s >= self.sig], s[s <= -self.sig]
        N = s[(s < self.sig) & (s > -self.sig)]
        return {"S_S": float(S.mean()), "S_C": float(C.mean()), "Np": float(np.maximum(N, 0).mean()), "Nm": float(np.minimum(N, 0).mean())}


# ── 선형계획 ──────────────────────────────────────────────────────────────
LP_FALLBACKS = {"n": 0}


def _lp(c, **kw):
    """HiGHS 기본(30초 제한) → 시간 제한이면 내부점법(크로스오버 · 꼭짓점)으로 다시 푼다. 대체 횟수를 센다(산출물에 적는다)."""
    from scipy.optimize import linprog
    r = linprog(c, method="highs", options={"time_limit": 30.0}, **kw)
    if r.status == 1:                                     # 1 = 반복·시간 한도
        LP_FALLBACKS["n"] += 1
        r = linprog(c, method="highs-ipm", options={"time_limit": 300.0}, **kw)
    return r


def solve_lp(E, SC, hd, first, mode="L1"):
    """보유 h(가족 N + SPY) · mode L1 | P4(Δ̃ ≡ 0) | P5(z ≤ Σ h ã)."""
    from scipy.optimize import linprog
    Xd = E["Xd"]                                           # N × T (평균 뺀 x)
    N, T = Xd.shape
    if mode == "P4":
        cp = cm = E["Lt"]
    else:
        cp, cm = E["cpt"], E["cmt"]
    AS, AC = cp * SC["S_S"], cm * SC["S_C"]
    AN = cp * SC["Np"] + cm * SC["Nm"]
    n_vec = np.append(np.full(N, 0.5 / N), 0.5)            # ½ SPY + ½ C1
    base_cons = float(np.mean(np.maximum(0, -(n_vec[:N] @ Xd))))
    kap = 0.0 if first else KAPPA
    # 변수: h(N+1) · z · u(N+1) · v(T)
    nh, nv = N + 1, N + 1 + 1 + (N + 1) + T
    iz, iu, iv = N + 1, N + 2, N + 2 + N + 1
    c = np.zeros(nv)
    c[iz] = -1.0
    c[iu:iu + nh] = kap
    A, b = [], []

    def row():
        return np.zeros(nv)
    if mode == "P5":
        r = row(); r[iz] = 1; r[:N] = -E["at"]; A.append(r); b.append(0.0)
    else:
        r = row(); r[iz] = 1; r[:N] = -AS; A.append(r); b.append(0.0)
        r = row(); r[iz] = 1; r[:N] = -AC; A.append(r); b.append(0.0)
    r = row(); r[:N] = -AN; A.append(r); b.append(-float(n_vec[:N] @ AN))          # 평상월 바닥
    for m in range(T):                                    # v_m ≥ −Σ h x̃
        r = row(); r[:N] = -Xd[:, m]; r[iv + m] = -1; A.append(r); b.append(0.0)
    r = row(); r[iv:iv + T] = 1.0 / T; A.append(r); b.append(base_cons)            # 일관성 천장
    for j in range(nh):                                   # u ≥ |h − h^d|
        r = row(); r[j] = 1; r[iu + j] = -1; A.append(r); b.append(hd[j])
        r = row(); r[j] = -1; r[iu + j] = -1; A.append(r); b.append(-hd[j])
    Aeq = np.zeros((1, nv)); Aeq[0, :nh] = 1
    bounds = [(0, CAP)] * N + [(ANCHOR, 1)] + [(None, None)] + [(0, None)] * nh + [(0, None)] * T
    res = _lp(c, A_ub=np.array(A), b_ub=np.array(b), A_eq=Aeq, b_eq=[1.0], bounds=bounds)
    if res.status != 0:
        raise RuntimeError("LP 실패: %s" % res.message)
    opt = res.fun
    # 동률 깨기 — 목적값을 지키며 거래를 최소로
    c2 = np.zeros(nv); c2[iu:iu + nh] = 1.0
    # 목적값 허용 오차는 상대값 — 1e-9 절대값은 퇴화 꼭짓점에서 HiGHS 가 멈췄다(P5 · 2025 결정). 제한 시간을 넘기면 멈춘다(조용히 넘어가지 않는다).
    A2 = np.vstack([np.array(A), c[None, :]]); b2 = np.append(np.array(b), opt + 1e-7 * (1 + abs(opt)))
    res2 = _lp(c2, A_ub=A2, b_ub=b2, A_eq=Aeq, b_eq=[1.0], bounds=bounds)
    if res2.status != 0:
        raise RuntimeError("동률 깨기 LP 실패: %s" % res2.message)
    x = res2.x
    h = np.clip(x[:nh], 0, None)
    return h / h.sum(), {"z": float(x[iz]), "AS": AS, "AC": AC}


# ── 보유 모의 ─────────────────────────────────────────────────────────────
def simulate(lib, targets, months):
    """targets: {결정월 t: {sid 또는 'SPY': 비중}} → 월 수익(%) · 결정 때 거래량 · 드리프트 뒤 비중."""
    w, ret, turn = {"SPY": 1.0}, {}, {}
    pend_cost = 0.0
    dec = sorted(targets)
    for m in months:
        t = mshift(m, -1)
        if t in targets:
            tgt = targets[t]
            keys = set(w) | set(tgt)
            tv = sum(abs(tgt.get(k, 0.0) - w.get(k, 0.0)) for k in keys)
            turn[t] = tv
            pend_cost = COST * tv
            w = dict(tgt)
        r, moved = 0.0, 0.0
        new = {}
        for k, x in w.items():
            rk = lib.spy[m] if k == "SPY" else lib.panel.get(k, {}).get(m)
            if rk is None:                               # 계열이 끊겼다 — 그달은 SPY 로 보고 달말에 SPY 로 옮긴다
                rk = lib.spy[m]
                moved += x
                k = "SPY"
            r += x * rk
            new[k] = new.get(k, 0.0) + x * (1 + rk / 100)
        tot = sum(new.values())
        w = {k: v / tot for k, v in new.items()}
        ret[m] = r - pend_cost - 2 * COST * moved          # 끊긴 몫을 SPY 로 — 판 다리 + 산 다리
        pend_cost = 0.0
    return ret, turn


# ── 평가(월 단위 · 사전등록 §C) ────────────────────────────────────────────
def metrics(y, spy, months, ME, rf=None, etf=None, blocks=None):
    y = np.array([y[m] for m in months]); s = np.array([spy[m] for m in months])
    a = y - s
    cm_set, sm_set = set(ME["months"]["crash_m"]), set(ME["months"]["surge_m"])
    cmask = np.array([m in cm_set for m in months]); smask = np.array([m in sm_set for m in months])
    up, dn = s > 0, s < 0

    def gcap(mask):
        gp = np.prod(1 + y[mask] / 100) ** (1 / mask.sum()) - 1
        gb = np.prod(1 + s[mask] / 100) ** (1 / mask.sum()) - 1
        return gp / gb
    UC, DC = gcap(up), gcap(dn)
    rel = np.concatenate([[1.0], np.cumprod(1 + y / 100) / np.cumprod(1 + s / 100)])   # 시작점을 넣는다
    peak = np.maximum.accumulate(rel)
    dd = rel / peak - 1
    i_min = int(np.argmin(dd))
    # 회복 = 바닥에서 직전 고점을 다시 넘는 첫 달까지의 개월 · 낙폭이 없으면 0 · 창 끝까지 못 넘으면 None(바닥이 끝 24개월 안이면 «판정 보류»)
    rec = 0 if dd[i_min] > -1e-12 else next((k - i_min for k in range(i_min, len(rel)) if rel[k] >= peak[i_min] - 1e-12), None)
    roll36 = [np.prod(1 + y[k - 36:k] / 100) / np.prod(1 + s[k - 36:k] / 100) - 1 for k in range(36, len(a) + 1)]
    roll12 = [np.sum(a[k - 12:k]) for k in range(12, len(a) + 1)]
    out = {"n": len(months), "ann_active": float(a.mean() * 12), "te": float(a.std(ddof=1) * math.sqrt(12)),
           "ir": float(a.mean() * 12 / (a.std(ddof=1) * math.sqrt(12))) if a.std() > 0 else None, "t_nw": nw_t(a),
           "X_CM": float(a[cmask].mean()) if cmask.any() else None, "X_SM": float(a[smask].mean()) if smask.any() else None,
           "n_CM": int(cmask.sum()), "n_SM": int(smask.sum()),
           "UC": float(UC), "DC": float(DC), "CM": float(min(UC - 1, 1 - DC)),
           "M1_win": float(np.mean(a > 0) * 100), "M3_roll36_pos": float(np.mean(np.array(roll36) > 0) * 100) if roll36 else None,
           "M4_rel_mdd": float(dd.min() * 100), "M4_recover_months": rec, "M4_trough_months_before_end": int(len(rel) - 1 - i_min),
           "M4_worst_roll12": float(min(roll12)) if roll12 else None,
           "M5_roll12_pos": float(np.mean(np.array(roll12) > 0) * 100) if roll12 else None}
    out["Psi_M"] = min(out["X_CM"], out["X_SM"]) if out["X_CM"] is not None and out["X_SM"] is not None else None
    if blocks:
        out["M2_blocks"] = [float(np.mean([a[k] for k, m in enumerate(months) if lo <= m <= hi])) * 12 for lo, hi in blocks]
    yrs = {}
    for m, v in zip(months, a):
        yrs.setdefault(m[:4], []).append(v)
    out["M5_years"] = {k: float(np.sum(v)) for k, v in yrs.items()}
    return out


def tradeoff(y, c1, spy, months, ME):
    d = np.array([y[m] - c1[m] for m in months]); s = np.array([spy[m] for m in months])
    b, t = ols_nw(d, np.column_stack([np.ones(len(s)), np.maximum(s, 0), np.minimum(s, 0)]))
    return {"alpha": float(b[0]), "alpha_t": float(t[0]), "slope_up": float(b[1]), "slope_dn": float(b[2]),
            "label": "베타 이동" if (np.sign(b[1]) == np.sign(b[2]) and t[0] < 1) else ""}


def factor_reg(y, months, etf, rf):
    s = etf["SPY"]
    dep = np.array([y[m] - s[m] for m in months])
    F = np.column_stack([np.ones(len(months)),
                         [s[m] - rf[m] for m in months],
                         [etf["RSP"][m] - s[m] for m in months],
                         [etf["IVW"][m] - etf["IVE"][m] for m in months],
                         [etf["SPLV"][m] - s[m] for m in months],
                         [etf["SPMO"][m] - s[m] for m in months],
                         [etf["AGG"][m] - rf[m] for m in months]])
    b, t = ols_nw(dep, F)
    return {"alpha_pm": float(b[0]), "alpha_t": float(t[0]),
            "betas": dict(zip(["MKT", "EW", "GV", "LV", "MOM", "BOND"], [float(x) for x in b[1:]]))}


def beta_ols(y, spy, ms):
    if len(ms) < 12:
        return None
    Y = np.array([y[m] for m in ms]); S = np.array([spy[m] for m in ms])
    return float(np.cov(S, Y, ddof=1)[0, 1] / S.var(ddof=1))


def c2_series(lib, rule, c1, months, beta_ex, beta_c1_ex):
    """β 를 맞춘 1/N — 매달 C1 · SPY · T-bill 세 다리 비중을 규칙의 β 에 맞추고, 드리프트 뒤 Σ|Δw| 에 편도 10bp.
    β(규칙) = 직전 36개월 OLS(12개월 미만이면 결정 때 사전 β 1 + Σ h L̂) · β(C1) = C1 의 직전 36개월 OLS(12개월 미만이면 1 + 평균 L̂)."""
    out, flags, wd = {}, 0, None
    for k, m in enumerate(months):
        past = months[max(0, k - 36):k]
        bt = beta_ols(rule, lib.spy, past) if len(past) >= 12 else beta_ex.get(m)
        bc = beta_ols(c1, lib.spy, past) if len(past) >= 12 else beta_c1_ex.get(m)
        rfm = lib.rf.get(m, 0.0)
        if bt is None or bc is None:
            wt = (1.0, 0.0, 0.0)
        elif bt > 1:                                      # 규칙 β > 1 → C2 = SPY(표시)
            wt = (0.0, 1.0, 0.0); flags += 1
        elif bt >= bc and bc < 1:                         # C1 을 SPY 로 채워 β 를 올린다
            lam = min(1.0, max(0.0, (1 - bt) / (1 - bc))); wt = (lam, 1 - lam, 0.0)
        else:                                             # C1 을 T-bill 로 채워 β 를 내린다
            lam = min(1.0, max(0.0, bt / bc)) if bc > 0 else 1.0; wt = (lam, 0.0, 1 - lam)
        cost = COST * sum(abs(a - b) for a, b in zip(wt, wd)) if wd is not None else 0.0
        rs = (c1[m], lib.spy[m], rfm)
        out[m] = sum(w * r for w, r in zip(wt, rs)) - cost
        g = [w * (1 + r / 100) for w, r in zip(wt, rs)]
        tot = sum(g)
        wd = tuple(x / tot for x in g)
    return out, flags


def frozen_check(out=OUT):
    c = os.environ.get("LIBMETA_COMMIT")
    if not c:
        raise SystemExit("🚨 LIBMETA_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --dry 만 된다.")
    g = lambda *a: subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True)
    full = g("rev-parse", c + "^{commit}").stdout.strip()
    added = g("log", "--format=%H", "--diff-filter=A", full, "--", PREREG).stdout.split()
    if not added or added[-1] != full:
        raise SystemExit("🚨 %s 는 사전등록 문서를 처음 더한 커밋이 아니다." % full[:8])
    if g("merge-base", "--is-ancestor", full, "origin/main").returncode != 0:
        raise SystemExit("🚨 사전등록 커밋이 origin/main 에 없다 — 먼저 푸시.")
    for p in ("build/lib_meta.py", "build/lib_loader.py", PREREG, "data/mech_episodes.json"):
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True).stdout
        have = open(os.path.join(ROOT, p), "rb").read()
        if want.replace(b"\r\n", b"\n") != have.replace(b"\r\n", b"\n"):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    if os.path.exists(out) and not os.environ.get("LIBMETA_RERUN"):
        raise SystemExit("🚨 %s 가 이미 있다 — 한 번 굽는 측정이다(다시 돌리려면 LIBMETA_RERUN=사유 — JSON 에 남는다)." % out)
    import scipy
    if scipy.__version__ != SCIPY_VER:
        raise SystemExit("🚨 scipy %s ≠ 등록 %s — HiGHS 의 꼭짓점 선택이 판마다 다를 수 있다." % (scipy.__version__, SCIPY_VER))
    return full


# ── 본체 ─────────────────────────────────────────────────────────────────
def drift(lib, w, t_from, t_to):
    """보유 w 를 t_from 월말 → t_to 월말까지 구성 순수익으로 드리프트(끊긴 계열은 SPY 로)."""
    w = dict(w)
    for m in mrange(mshift(t_from, 1), t_to):
        new = {}
        for k, x in w.items():
            rk = lib.spy[m] if k == "SPY" else lib.panel.get(k, {}).get(m)
            if rk is None:
                rk, k = lib.spy[m], "SPY"
            new[k] = new.get(k, 0.0) + x * (1 + rk / 100)
        tot = sum(new.values())
        w = {k: v / tot for k, v in new.items()}
    return w


def build_paths(lib):
    """결정마다 U_t · 추정 · L1/P4/P5 목표 비중 · F0 재료(규칙 수익은 쓰지 않는다 — 드리프트에만 구성 수익을 쓴다)."""
    tg = {"L1": {}, "P4": {}, "P5": {}, "C1": {}}
    info = []
    prev = {k: None for k in ("L1", "P4", "P5")}
    lib.Ucache = {}
    for j, t in enumerate(lib.decisions):
        U, W = lib.universe(t)
        lib.Ucache[t] = U
        E = lib.estimate(U, W)
        SC = lib.scenarios(t)
        N = len(U)
        tg["C1"][t] = {s: 1.0 / N for s in U}
        rec = {"t": t, "N": N, "W": [W[0], W[-1]], "sc": SC}
        for mode in ("L1", "P4", "P5"):
            if prev[mode] is None:
                hd = np.append(np.full(N, 0.5 / N), 0.5)
            else:                                           # 직전 보유를 t 까지 드리프트 — U 밖으로 나간 가족은 SPY 로 본다
                wd = drift(lib, prev[mode], lib.decisions[j - 1], t)
                hd = np.array([wd.get(s, 0.0) for s in U] + [wd.get("SPY", 0.0) + sum(v for k, v in wd.items() if k != "SPY" and k not in U)])
                hd = hd / hd.sum()
            h, aux = solve_lp(E, SC, hd, prev[mode] is None, mode)
            tgt = {s: float(x) for s, x in zip(U, h[:N]) if x > 1e-9}
            tgt["SPY"] = float(h[N])
            tg[mode][t] = tgt
            prev[mode] = tgt
            if mode == "L1":
                rec.update({"z": aux["z"], "lib_share": float(h[:N].sum()),
                            "beta_ex": float(1 + h[:N] @ E["Lh"]), "beta_c1_ex": float(1 + E["Lh"].mean()),
                            "timing_share_wstar": float(sum(2 * h[i] for i, s in enumerate(U) if lib.reps[s]["role"] in TIMING_ROLES)),
                            "q_exposure": float(sum(h[i] * (-E["Lh"][i]) for i, s in enumerate(U) if lib.reps[s]["role"] in TIMING_ROLES)),
                            "top20": _top20(tgt), "Dt": dict(zip(U, map(float, E["Dt"]))), "Lh": dict(zip(U, map(float, E["Lh"])))})
        info.append(rec)
    return tg, info


def _top20(tgt):
    """보유(> 0) 가족 중 20번째 비중 이상 전부(동률 포함 · 1e-9 허용) · 20 미만이면 보유 전부."""
    pos = {s: v for s, v in tgt.items() if s != "SPY" and v > 1e-9}
    if not pos:
        return []
    thr = sorted(pos.values(), reverse=True)[min(19, len(pos) - 1)]
    return sorted(s for s, v in pos.items() if v >= thr - 1e-9)


def f0_checks(lib, tg, info):
    dec = lib.decisions
    act = [info[j]["lib_share"] for j in range(len(dec))]                  # ½Σ|h − SPY| = 가족 비중 합
    top = [set(r["top20"]) for r in info]
    changes = sum(1 for j in range(1, len(top)) if top[j] != top[j - 1])
    wL = lambda t: {k: v for k, v in tg["L1"][t].items()}
    dP = []
    for t in dec:
        a, b = tg["L1"][t], tg["P5"][t]
        keys = set(a) | set(b)
        wa = {k: 2 * a.get(k, 0) - (1 if k == "SPY" else 0) for k in keys}
        wb = {k: 2 * b.get(k, 0) - (1 if k == "SPY" else 0) for k in keys}
        dP.append(0.5 * sum(abs(wa[k] - wb[k]) for k in keys))
    # F0e — 결정 때 Δ̃ 와 다음 12개월(겹치지 않게) OLS Δ̂ 의 순위상관(라이브러리 가족 수익만 · 규칙 수익 아님)
    ics, n_const = [], 0
    for j, t in enumerate(dec):
        fut = mrange(mshift(t, 1), mshift(t, 12))
        if fut[-1] > LAST_HOLD:
            break
        U = [s for s in info[j]["Dt"] if all(m in lib.panel[s] for m in fut)]
        if len(U) < 10:
            continue
        sv = np.array([lib.spy[m] for m in fut])
        dh = []
        for s in U:
            x = np.array([lib.panel[s][m] - lib.spy[m] for m in fut])
            b, _ = hm_fit(x, sv)
            dh.append(b[1] - b[2])
        d0 = np.array([info[j]["Dt"][s] for s in U])
        if np.ptp(d0) == 0:                                # EB 가 Δ̃ 를 상수로 줄였다 — 횡단면 정보 없음 = IC 0
            ics.append(0.0); n_const += 1
            continue
        ics.append(spearman(d0, dh))
    out = {"F0a_active_share": float(np.mean(act)), "F0b_top20_changes": changes, "F0c_median_N": float(np.median([r["N"] for r in info])),
           "F0d_dist_P5": float(np.mean(dP)), "F0e_ic_mean": float(np.mean(ics)) if ics else None, "F0e_n": len(ics), "F0e_n_const": n_const,
           "F0f_timing_share": float(np.mean([r["timing_share_wstar"] for r in info]))}
    out["stop"] = out["F0a_active_share"] < 0.10 or out["F0c_median_N"] < 30
    out["measurable"] = out["F0b_top20_changes"] > 6
    out["labels"] = [x for x, c in (("성과 추종", out["F0d_dist_P5"] < 0.3), ("β 맞추기, 볼록성 정보 없음", (out["F0e_ic_mean"] or 0) <= 0),
                                     ("시장 타이밍 재포장", out["F0f_timing_share"] > 0.40)) if c]
    return out


def main() -> int:
    t0 = time.time()
    f0_only = "--f0" in sys.argv
    if "--dry" in sys.argv:                                 # 등록 전 구조 점검 — LP 가 풀리고 제약이 서는지만(수치를 찍지 않는다)
        lib = Lib()
        tg, info = build_paths(lib)
        bad = 0
        for mode in ("L1", "P4", "P5"):
            for t, w in tg[mode].items():
                if abs(sum(w.values()) - 1) > 1e-6 or w.get("SPY", 0) < ANCHOR - 1e-6 or max((v for k, v in w.items() if k != "SPY"), default=0.0) > CAP + 1e-6:
                    bad += 1
        print("dry: 결정 %d개 · 모드 3 · 제약 위반 %d · 내부점 대체 %d · %.0f초" % (len(lib.decisions), bad, LP_FALLBACKS["n"], time.time() - t0))
        return 0 if bad == 0 else 1
    commit = frozen_check(F0_OUT if f0_only else OUT)
    lib = Lib()
    if (lib.L["sha"]["sids"], lib.L["sha"]["panel"]) != (SID_SHA, PANEL_SHA):
        raise SystemExit("🚨 유니버스·패널 해시가 등록 때와 다르다(sid %s · panel %s) — 등록 커밋의 data/strategy_*.json 으로 돌린다."
                         % (lib.L["sha"]["sids"][:12], lib.L["sha"]["panel"][:12]))
    tg, info = build_paths(lib)
    F0 = f0_checks(lib, tg, info)
    print("F0: 가족 비중 평균 %.2f · 상위20 교체 %d · |U| 중앙 %.0f · P5 와 거리 %.2f · Δ 지속 IC %s(%d) · 타이밍류 비중 %.2f · 라벨 %s" % (
        F0["F0a_active_share"], F0["F0b_top20_changes"], F0["F0c_median_N"], F0["F0d_dist_P5"],
        "%.3f" % F0["F0e_ic_mean"] if F0["F0e_ic_mean"] is not None else "—", F0["F0e_n"], F0["F0f_timing_share"], F0["labels"] or "없음"))
    import scipy
    vers = {"scipy": scipy.__version__, "numpy": np.__version__, "data_rev": DATA_REV, "lp_ipm_fallbacks": LP_FALLBACKS["n"]}
    if f0_only:
        io.open(F0_OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(
            {"prereg": PREREG, "prereg_commit": commit, "rerun": os.environ.get("LIBMETA_RERUN"), "versions": vers, "f0": F0,
             "decisions": [{k: v for k, v in r.items() if k not in ("Dt", "Lh")} for r in info],
             "universe_sha": lib.L["sha"]}, ensure_ascii=False, indent=1) + "\n")
        print("→ %s (수익 없음 · %.0f초)" % (F0_OUT, time.time() - t0))
        return 0
    # 등록 §4 순서 — F0 파일이 같은 커밋으로 먼저 나와 있어야 한다
    if not os.path.exists(F0_OUT):
        raise SystemExit("🚨 F0 점검(--f0)을 먼저 돌려라.")
    f0_disk = json.load(io.open(F0_OUT, encoding="utf-8"))
    if f0_disk.get("prereg_commit") != commit or f0_disk.get("f0") != json.loads(json.dumps(F0)):
        raise SystemExit("🚨 F0 파일이 이 커밋·이 계산과 다르다.")
    if F0["stop"]:
        print("🚨 F0 멈춤 — 표본 안 측정을 하지 않는다.")
        return 1
    months = lib.hold
    R = {k: simulate(lib, tg[k], months) for k in ("L1", "P4", "P5", "C1")}
    rule, c1 = R["L1"][0], R["C1"][0]
    beta_ex = {m: next(r["beta_ex"] for r in reversed(info) if r["t"] < m) for m in months}
    beta_c1 = {m: next(r["beta_c1_ex"] for r in reversed(info) if r["t"] < m) for m in months}
    c2, c2_flags = c2_series(lib, rule, c1, months, beta_ex, beta_c1)
    qbar = float(np.mean([r["q_exposure"] for r in info]))
    p6 = {m: (1 - qbar) * lib.spy[m] + qbar * lib.rf.get(m, 0.0) for m in months}
    blocks = [("2019-10", "2022-03"), ("2022-04", "2024-09"), ("2024-10", "2026-08")]
    ser = {"L1": rule, "P4": R["P4"][0], "P5": R["P5"][0], "C1": c1, "C2": c2, "P6": p6,
           "FUND": {m: 0.9 * lib.spy[m] + 0.1 * rule[m] for m in months}}
    M = {k: metrics(v, lib.spy, months, lib.ME, blocks=blocks) for k, v in ser.items()}
    d_c2 = np.array([rule[m] - c2[m] for m in months])
    skill = {"vs_C2_mean_pm": float(d_c2.mean()), "vs_C2_t": nw_t(d_c2),
             "vs_C1_t": nw_t([rule[m] - c1[m] for m in months]), "vs_P4_t": nw_t([rule[m] - R["P4"][0][m] for m in months]),
             "vs_P5_t": nw_t([rule[m] - R["P5"][0][m] for m in months]), "vs_P6_t": nw_t([rule[m] - p6[m] for m in months])}
    # K4 — 실현된 분기 목표 순서를 섞는다(쓸 수 없는 sid 는 SPY 로)
    rng = np.random.default_rng(SEED)
    dec = lib.decisions
    perm_psi, perm_dc2 = [], []
    for _ in range(NPERM):
        order = rng.permutation(len(dec))
        tgp = {}
        for j, t in enumerate(dec):
            src = tg["L1"][dec[order[j]]]
            Ut = set(lib.Ucache[t])
            d = {k: v for k, v in src.items() if k == "SPY" or k in Ut}
            d["SPY"] = d.get("SPY", 0.0) + sum(v for k, v in src.items() if k != "SPY" and k not in Ut)
            tgp[t] = d
        rp, _ = simulate(lib, tgp, months)
        bdec = {t: 1 + sum(v * info[j]["Lh"][k] for k, v in tgp[t].items() if k != "SPY") for j, t in enumerate(dec)}
        bex = {m: next(bdec[t] for t in reversed(dec) if t < m) for m in months}           # 섞인 경로 자신의 사전 β
        c2p, _ = c2_series(lib, rp, c1, months, bex, beta_c1)
        mp = metrics(rp, lib.spy, months, lib.ME)
        perm_psi.append(mp["Psi_M"]); perm_dc2.append(float(np.mean([rp[m] - c2p[m] for m in months])))
    K4 = {"psi_pct": float(np.mean(np.array(perm_psi) < M["L1"]["Psi_M"]) * 100),
          "dc2_pct": float(np.mean(np.array(perm_dc2) < skill["vs_C2_mean_pm"]) * 100), "n": NPERM, "seed": SEED}
    TO = tradeoff(rule, c1, lib.spy, months, lib.ME)
    FR = factor_reg(rule, months, lib.etf, lib.rf)
    out = {"prereg": PREREG, "prereg_commit": commit, "rerun": os.environ.get("LIBMETA_RERUN"), "versions": vers,
           "label": "오염 측정(표본 안) — 판정 아님", "window": [months[0], months[-1]],
           "universe_sha": lib.L["sha"], "f0": F0, "metrics": M, "skill": skill, "k4": K4, "tradeoff": TO, "factor": FR,
           "c2_beta_gt1_months": c2_flags, "qbar": qbar,
           "decisions": [{k: v for k, v in r.items() if k not in ("Dt", "Lh")} for r in info],
           "targets": tg["L1"], "monthly": {k: {m: round(v[m], 5) for m in months} for k, v in ser.items()},
           "turnover": R["L1"][1]}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for k in ("L1", "C1", "C2", "P4", "P5", "P6", "FUND"):
        x = M[k]
        print("%-4s 연 초과 %+.2f%% · TE %.2f%% · IR %s · 급락월 %+.2f · 급등월 %+.2f · Ψ %+.2f · 월 승률 %.0f%% · 36m 양수 %s%% · 상대 MDD %.1f%%" % (
            k, x["ann_active"], x["te"], "%.2f" % x["ir"] if x["ir"] is not None else "—", x["X_CM"], x["X_SM"], x["Psi_M"], x["M1_win"],
            "%.0f" % x["M3_roll36_pos"] if x["M3_roll36_pos"] is not None else "—", x["M4_rel_mdd"]))
    print("기술: vs C2 t %s · vs P4 t %s · vs P5 t %s · K4 Ψ %.0f 백분위 · 교환 %s · 요인 알파 t %.2f (%.0f초)" % (
        skill["vs_C2_t"], skill["vs_P4_t"], skill["vs_P5_t"], K4["psi_pct"], TO["label"] or "—", FR["alpha_t"], time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
