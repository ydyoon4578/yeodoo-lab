# -*- coding: utf-8 -*-
"""build/q_jump.py — Q03 SF3-JM-ENGINE · 통계적 점프모형(Shu-Yu-Mulvey 2024) 공격·수비 엔진 교체 — S&P 500 하방위험·소르티노
국면이 하락이면 EG30 → x-bmrot(B/M 금리 국면 로테이션) · λ = 50 · 1일 지연.

근본 이유 — 주식시장 수익 분포는 몇 달에서 몇 년 지속되는 국면(평온한 상승 · 고위험 하락)으로 나뉘고, 전환 뒤에는 새 행동이 여러
  기간 이어진다(Ang·Timmermann 2012). 점프모형은 하방편차와 소르티노 비율로 두 국면을 군집하되 국면이 바뀔 때마다 벌점 λ 를 매겨
  HMM 의 짧은 가짜 국면(휩쏘)을 누른다. 하락 국면에서는 레버리지 축소·위험예산 매도가 연쇄되어 고베타·고성장 바스켓(EG30)이 가장
  크게 잃으므로 그 구간에만 수비 엔진(x-bmrot)으로 옮기고, 상승 국면에 공격 엔진으로 돌아오면 늘 섞어 두는 것보다 양쪽 구간에서
  낫다는 것이 이 교체의 근거다. 판정은 같은 평균 몫의 고정 혼합 D 대비(Δ^D)라 국면 판단의 정보만 잰다.

규칙(카드 Q03 그대로 · 한 곳만 시점 규율로 고침):
  입력 R_t = SPY 수정종가 일간 수익 − rf_t · 2006-01-04 부터. rf_t = 직전 달 rf_monthly(DGS3MO 월평균)를 그달 거래일 수로 나눠 복리 —
    카드는 «그달 rf_monthly» 지만 그 값은 그달 일별 평균이라 t 뒤의 날을 담는다(계약 규율 2 위반) → 끝난 달의 값을 쓴다(카드 수정 필요).
  특징(종가 t · 반감기 h 거래일 EWM · adjust=True): DD10 = √EWM10[R²·1{R<0}] · SOR20 = EWM20[R]/√EWM20[R²·1{R<0}] · SOR60(h 60) ·
    2007-01-03 부터 쓴다.
  적합: 2016-07-01 부터 매년 1월 · 7월 첫 거래일 · 학습 = max(2007-01-03, 3000 거래일 전) ~ 전날 · 특징을 학습 평균 · sd 로 표준화 ·
    Σ½‖x_t − θ_{s_t}‖² + λΣ1{s_t ≠ s_{t−1}} 최소(λ = 50 · K = 2) · 좌표 하강(θ = 국면 평균 · S = 비터비 DP) · k-means++ 초기값 10개
    (씨앗 20260925 + j) · 목적 최소를 남긴다 · S 가 안 바뀌거나 100 번이면 멈춘다 · BULL = 학습 초과수익 누적이 큰 국면.
  온라인: 매일 t 에 θ · 표준화를 고정하고 마지막 L 특징일(L = 그 적합의 학습 길이)로 DP 를 돌려 마지막 상태를 쓴다.
  위치: 종가 t 의 상태는 종가 t+1 부터(1일 지연) · BULL → OFFENSE(EG30 V0) · BEAR → DEFENSE(x-bmrot) · 교체마다 판 장부 10bp + 산 장부 10bp
    + 든 장부의 자기 회전 · 펀드 90/10 월말 되돌림. 첫 적합 전 · 적합 실패 = OFFENSE.
측정만(승격 불가): (a) T-bill DEFENSE · (b) 월말에 뽑은 JM 상태(월간 교체) · (c) sma200 · 변동성 쌍둥이 · 논문 비교 SPY/T-bill 0/1.
출처: Shu, Yu & Mulvey(2024) «Downside risk reduction using regime-switching signals: a statistical jump model approach»(J. Asset Mgmt) —
  카드가 연 원문 Table 2 · §3-4 · scratchpad/qbatch_final.md # Q03 · build/q_switch.py(교체 틀) · build/q_bmrot_leg.py(수비 다리).
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402
import q_switch as SW                 # noqa: E402

CARDS = {"Q03": {"cls": "S", "slot": "S1"}}
NPERM = 10000
LAM, K = 50.0, 2
HL = (("DD10", 10), ("SOR20", 20), ("SOR60", 60))
R0, FEAT0, FIT0 = "2006-01-04", "2007-01-03", "2016-07-01"
WIN = 3000
NINIT, MAXIT = 10, 100
_CACHE = {}


# ── 특징 ─────────────────────────────────────────────────────────────────
def ewm(x, h):
    """pandas ewm(halflife=h, adjust=True).mean() — α = 1 − 0.5^(1/h) · 분자·분모를 따로 굴린다."""
    q = 0.5 ** (1.0 / h)
    num = den = 0.0
    out = np.empty(len(x))
    for t, v in enumerate(x):
        num = v + q * num
        den = 1.0 + q * den
        out[t] = num / den
    return out


def rf_month_for(ym):
    """거래일이 달 ym 에 있을 때 쓰는 rf_monthly 의 달 — 직전 달(그달 값은 그달 DGS3MO 일별 평균이라 t 뒤의 날을 담는다 → 시점 규율 2)."""
    return Q.mshift(ym, -1)


def excess_returns(A):
    """SPY 일간 수익 − 그날 rf. rf = 가장 최근에 끝난 달(ym − 1)의 rf_monthly 를 그달(ym) 거래일 수로 복리 분할(거래소 달력은 미리 안다).
    인덱스 = A.dates 자리(2006-01-04 = 1)."""
    p = A.px["SPY"]
    n = len(p)
    cnt = {}
    for d in A.dates:
        cnt[d[:7]] = cnt.get(d[:7], 0) + 1
    R = np.full(n, np.nan)
    for i in range(1, n):
        ym = A.dates[i][:7]
        rm = rf_month_for(ym)
        assert rm < ym and rm in A.RF, "rf 달 %s 가 거래일 달 %s 보다 앞서지 않거나 없다" % (rm, ym)   # PIT — 끝난 달의 값만
        rf_d = (1 + float(A.RF[rm])) ** (1.0 / cnt[ym]) - 1
        R[i] = p[i] / p[i - 1] - 1 - rf_d
    return R


def features(A):
    """(자리 배열 from R0, R, X(n × 3)) — 특징은 R0 부터 굴리고 FEAT0 부터 쓴다."""
    key = ("FEAT", id(A))
    if key in _CACHE:
        return _CACHE[key]
    R = excess_returns(A)
    i_r0 = A.dates.index(R0)
    r = R[i_r0:]
    assert not np.isnan(r).any(), "SPY 수익 결측"
    neg2 = np.where(r < 0, r * r, 0.0)
    cols = []
    for nm, h in HL:
        if nm.startswith("DD"):
            cols.append(np.sqrt(ewm(neg2, h)))
        else:
            with np.errstate(divide="ignore", invalid="ignore"):         # 2006 첫 며칠(음수일 전) — 2007-01-03 부터만 쓴다
                cols.append(ewm(r, h) / np.sqrt(ewm(neg2, h)))
    X = np.full((len(R), 3), np.nan)
    X[i_r0:] = np.column_stack(cols)
    assert np.isfinite(X[A.dates.index(FEAT0):]).all(), "특징 결측(2007-01-03 이후)"
    out = (R, X)
    _CACHE[key] = out
    return out


# ── 점프모형 ─────────────────────────────────────────────────────────────
def viterbi2(L, lam):
    """2국면 비터비 — L (n × 2) 손실 · 전환 벌점 lam → (S, 목적). 동점은 머무름 · 국면 0 쪽."""
    l0, l1 = L[:, 0].tolist(), L[:, 1].tolist()
    n = len(l0)
    v0, v1 = l0[0], l1[0]
    b0, b1 = bytearray(n), bytearray(n)
    for t in range(1, n):
        s1 = v1 + lam
        if v0 <= s1:
            p0 = v0
        else:
            p0 = s1; b0[t] = 1
        s0 = v0 + lam
        if v1 <= s0:
            p1 = v1; b1[t] = 1
        else:
            p1 = s0
        v0 = p0 + l0[t]
        v1 = p1 + l1[t]
    s = 0 if v0 <= v1 else 1
    obj = v0 if s == 0 else v1
    S = np.empty(n, np.int8)
    S[-1] = s
    for t in range(n - 1, 0, -1):
        s = b0[t] if s == 0 else b1[t]
        S[t - 1] = s
    return S, obj


def losses(Z, theta):
    return 0.5 * ((Z[:, None, :] - theta[None, :, :]) ** 2).sum(2)


def objective(Z, S, theta, lam):
    L = losses(Z, theta)
    return float(L[np.arange(len(Z)), S].sum() + lam * np.sum(S[1:] != S[:-1]))


def kmeanspp(Z, k, rng):
    n = len(Z)
    c = [Z[int(rng.integers(n))]]
    for _ in range(1, k):
        d2 = np.min(((Z[:, None, :] - np.array(c)[None]) ** 2).sum(2), axis=1)
        pr = d2 / d2.sum() if d2.sum() > 0 else np.full(n, 1.0 / n)
        c.append(Z[int(rng.choice(n, p=pr))])
    return np.array(c, float)


def fit_jm(Z, lam=LAM, seeds=None):
    """좌표 하강 10회(k-means++ 씨앗) → 목적 최소 해 · 모든 목적값 · 반복 수."""
    seeds = seeds if seeds is not None else [Q.SEED + j for j in range(NINIT)]
    runs = []
    for j, sd in enumerate(seeds):
        rng = np.random.default_rng(sd)
        theta = kmeanspp(Z, K, rng)
        S_prev, it = None, 0
        for it in range(1, MAXIT + 1):
            S, _o = viterbi2(losses(Z, theta), lam)
            if S_prev is not None and np.array_equal(S, S_prev):
                break
            for k in range(K):
                if (S == k).any():
                    theta[k] = Z[S == k].mean(0)
            S_prev = S
        runs.append({"j": j, "obj": objective(Z, S, theta, lam), "theta": theta.copy(), "S": S.copy(), "iters": it})
    best = min(runs, key=lambda r: (r["obj"], r["j"]))
    return best, [r["obj"] for r in runs], [r["iters"] for r in runs]


def online_final(Zs, theta, lam, ends, L):
    """온라인 DP — 끝날 ends(배열)마다 창 [e − L + 1, e] 의 앞으로 DP 를 한꺼번에(벡터) 돌려 마지막 상태."""
    Ls = losses(Zs, theta)
    ends = np.asarray(ends)
    st = ends - L + 1
    assert st.min() >= 0
    v0, v1 = Ls[st, 0].copy(), Ls[st, 1].copy()
    for k in range(1, L):
        idx = st + k
        n0 = np.minimum(v0, v1 + lam) + Ls[idx, 0]
        n1 = np.minimum(v1, v0 + lam) + Ls[idx, 1]
        v0, v1 = n0, n1
    return np.where(v0 <= v1, 0, 1).astype(np.int8)


def fit_dates(A):
    """2016-07-01 부터 매년 1 · 7월 첫 거래일(A 격자)."""
    out, seen = [], set()
    for i, d in enumerate(A.dates):
        if d >= FIT0 and d[5:7] in ("01", "07") and d[:7] not in seen:
            seen.add(d[:7])
            out.append(i)
    return out


def jm_states(ctx):
    """{날짜: 1(BULL) · 0(BEAR)} (첫 적합일부터) · 적합 기록."""
    key = ("JM", id(ctx))
    if key in _CACHE:
        return _CACHE[key]
    A = ctx.A
    R, X = features(A)
    i_f0 = A.dates.index(FEAT0)
    fits = fit_dates(A)
    last_need = A.di[ctx.G.dates[SW.frame(ctx).iE]] if ctx.G.dates[SW.frame(ctx).iE] in A.di else len(A.dates) - 1
    states, log = {}, []
    for q, f in enumerate(fits):
        a = max(i_f0, f - WIN)
        L = f - a
        Xt = X[a:f]
        mu, sd = Xt.mean(0), Xt.std(0)
        ok = bool(np.all(sd > 0) and not np.isnan(Xt).any())
        rec = {"fit": A.dates[f], "train": [A.dates[a], A.dates[f - 1]], "L": L}
        f_next = fits[q + 1] if q + 1 < len(fits) else last_need + 1
        days = np.arange(f, min(f_next, last_need + 1))
        if len(days) == 0:
            continue
        if not ok:
            for i in days:
                states[A.dates[i]] = 1
            rec.update({"fail": "표준화 불가"})
            log.append(rec)
            continue
        Z = (Xt - mu) / sd
        best, objs, iters = fit_jm(Z)
        S = best["S"]
        occ = [int((S == k).sum()) for k in range(K)]
        if min(occ) == 0:
            for i in days:                                  # 한 국면만 선 해 = 적합 실패 → OFFENSE
                states[A.dates[i]] = 1
            rec.update({"fail": "한 국면만 선 해(퇴화)", "objs": objs, "iters": iters, "occ": occ})
            log.append(rec)
            continue
        rtr = R[a:f]
        cum = [float(np.prod(1 + rtr[S == k]) - 1) for k in range(K)]
        bull = int(np.argmax(cum))
        Zall = (X - mu) / sd
        fin = online_final(Zall, best["theta"], LAM, days, L)
        for i, s in zip(days, fin):
            states[A.dates[i]] = 1 if int(s) == bull else 0
        # 온라인 DP 가 학습 창 끝에서 비터비 마지막 상태와 같은가(구현 점검 · 수익 없음)
        chk = int(online_final(Zall, best["theta"], LAM, [f - 1], L)[0]) == int(S[-1])
        rec.update({"objs": [round(o, 4) for o in objs], "best_j": best["j"], "iters": iters, "occ": occ,
                    "bull": bull, "theta": np.round(best["theta"], 4).tolist(), "mu": np.round(mu, 6).tolist(),
                    "sd": np.round(sd, 6).tolist(), "train_jumps": int(np.sum(S[1:] != S[:-1])), "online_eq_viterbi_end": chk,
                    "n_days": int(len(days)), "bear_days": int(sum(1 for i in days if states[A.dates[i]] == 0))})
        log.append(rec)
    _CACHE[key] = (states, log)
    return states, log


def sampled_monthly(ctx, states):
    """(b) 월말에 뽑은 상태 — 날마다 «그날 이하 마지막 월말 종가의 상태» (그 뒤 1일 지연은 규칙과 같다)."""
    A = ctx.A
    out, cur = {}, None
    for d in sorted(states):
        i = A.di.get(d)
        if i is not None and A.me.get(d[:7]) == i:
            cur = states[d]
        if cur is not None:
            out[d] = cur
    return out


def _spells(F, pos):
    out, j = [], 0
    while j < len(pos):
        if pos[j] == 0:
            k = j
            while k + 1 < len(pos) and pos[k + 1] == 0:
                k += 1
            out.append((j, k))
            j = k + 1
        else:
            j += 1
    return out


# ── 계약 ─────────────────────────────────────────────────────────────────
def selftest():
    """합성 2국면 계열 — 비터비 최적성(전수) · 좌표 하강 단조 · 국면 복원 · 온라인 DP = 비터비 끝 상태 · EWM = pandas."""
    tests = {}
    rng = np.random.default_rng(Q.SEED)
    # ① 비터비 = 전수 탐색(n = 12)
    import itertools
    L = rng.random((12, 2)) * 3
    S, obj = viterbi2(L, 1.3)
    brute = min(sum(L[t, s[t]] for t in range(12)) + 1.3 * sum(s[t] != s[t - 1] for t in range(1, 12))
                for s in itertools.product((0, 1), repeat=12))
    tests["viterbi_optimal"] = bool(abs(obj - brute) < 1e-9 and abs(sum(L[t, S[t]] for t in range(12)) + 1.3 * np.sum(S[1:] != S[:-1]) - obj) < 1e-9)
    # ② 합성 2국면(지속 국면 · 3 특징) — 좌표 하강이 국면을 복원
    n = 2000
    s_true = np.zeros(n, np.int8)
    t = 0
    st = 0
    while t < n:
        ln = int(rng.integers(120, 300))
        s_true[t:t + ln] = st
        st = 1 - st
        t += ln
    mu = np.array([[1.0, -0.8, 0.6], [-1.0, 0.8, -0.6]])
    Z = mu[s_true] + rng.normal(0, 0.7, (n, 3))
    best, objs, iters = fit_jm(Z, 50.0)
    acc = max(np.mean(best["S"] == s_true), np.mean(best["S"] != s_true))
    tests["recover_acc"] = round(float(acc), 4)
    tests["recover_ok"] = bool(acc > 0.97)
    tests["best_is_min"] = bool(best["obj"] == min(objs))
    # ③ 좌표 하강 단조(한 초기값에서 목적이 늘지 않는다)
    r2 = np.random.default_rng(Q.SEED + 3)
    theta = kmeanspp(Z, 2, r2)
    prev, mono = None, True
    for _ in range(20):
        S2, _o = viterbi2(losses(Z, theta), 50.0)
        o1 = objective(Z, S2, theta, 50.0)
        for k in range(2):
            if (S2 == k).any():
                theta[k] = Z[S2 == k].mean(0)
        o2 = objective(Z, S2, theta, 50.0)
        if prev is not None and o1 > prev + 1e-9:
            mono = False
        if o2 > o1 + 1e-9:
            mono = False
        prev = o2
    tests["cd_monotone"] = mono
    # ④ 온라인 DP 의 끝 상태 = 비터비 끝 상태(같은 창)
    ends = np.array([n - 1])
    tests["online_eq_viterbi"] = bool(int(online_final(Z, best["theta"], 50.0, ends, n)[0]) == int(best["S"][-1]))
    # 창을 여러 끝날로 한꺼번에 = 끝날마다 따로
    e2 = np.arange(1500, 1520)
    v = online_final(Z, best["theta"], 50.0, e2, 1000)
    v_each = [viterbi2(losses(Z[e - 999:e + 1], best["theta"]), 50.0)[0][-1] for e in e2]
    tests["online_vectorized"] = bool(np.array_equal(v, np.array(v_each, np.int8)))
    # ⑤ EWM adjust=True = pandas
    try:
        import pandas as pd
        x = rng.normal(0, 1, 300)
        tests["ewm_eq_pandas"] = bool(np.max(np.abs(ewm(x, 20) - pd.Series(x).ewm(halflife=20, adjust=True).mean().values)) < 1e-12)
    except Exception:
        tests["ewm_eq_pandas"] = "pandas 없음"
    sw = SW.selftest()
    tests["switch_frame"] = sw["ok"]
    return {"ok": all(bool(v) for k, v in tests.items() if k != "recover_acc"), "tests": tests}


def dry(ctx):
    """구성만 — 적합 수 · 학습 길이 · 목적 10개의 폭 · 온라인 = 비터비 끝 · 교체 수 · 수비 일 · 격자 · 날짜 단언. 수익 없음."""
    states, log = jm_states(ctx)
    A = ctx.A
    F = SW.frame(ctx)
    pos = SW.pos_from_daily(F, states)
    # PIT 단언 — 적합은 전날까지 · 온라인 상태는 그날 종가까지의 특징
    for r in log:
        assert r["train"][1] < r["fit"]
    assert all(F.G.dates[d - 2] in states for d in F.day), "보유 창에 상태가 없는 날"
    pm = SW.pos_from_daily(F, sampled_monthly(ctx, states))
    fails = [r["fit"] for r in log if r.get("fail")]
    return {"n_fits": len(log), "fails": fails, "L_first_last": [log[0]["L"], log[-1]["L"]],
            "obj_spread_max": max((max(r["objs"]) - min(r["objs"])) for r in log if r.get("objs")),
            "online_eq_viterbi_end": all(r.get("online_eq_viterbi_end", True) for r in log),
            "iters_max": max(max(r["iters"]) for r in log if r.get("iters")),
            "e_bar": float(pos.mean()), "shifts_per_year": SW.shifts_per_year(F, pos), "n_switch": int(np.sum(pos[1:] != pos[:-1])),
            "bear_days": int((pos == 0).sum()), "n_bear_spells": len(_spells(F, pos)),
            "monthly_arm_shifts_per_year": SW.shifts_per_year(F, pm),
            "f0": SW.f0_check(F, pos, F.dmask()), "switch_dry": SW.dry(ctx)}


def run(ctx):
    """한 번 굽기 — Q03 CardResult."""
    import q_bmrot_leg as BL
    F = SW.frame(ctx)
    states, fitlog = jm_states(ctx)
    pos = SW.pos_from_daily(F, states)
    bO, bD, bT = SW.offense_v0(ctx), SW.defense(ctx), SW.tbill_book(ctx)
    e_bar = float(pos.mean())
    # 쌍둥이(관문 · 선택 불가)
    tw = {"sma200": SW.pos_from_daily(F, SW.sma200_state(ctx)), "vol": SW.pos_from_daily(F, SW.vol_state_daily(ctx, e_bar))}
    # 측정만 팔
    pm = SW.pos_from_daily(F, sampled_monthly(ctx, states))
    arms = {"tbill": SW.switch_fr(ctx, pos, bO, bT), "jm_monthly": SW.switch_fr(ctx, pm, bO, bD),
            "spy_tbill_01": SW.switch_fr(ctx, pos, SW.spy_book(ctx), bT)}
    arms["tbill_pr"] = SW.switch_fr(ctx, pos, bO, bT, basis="PR")
    _T, blog = BL.targets(ctx.Wd)
    tilt = {r["m"]: r["w_val"] for r in blog}
    spells = []
    for a, b in _spells(F, pos):
        ms = sorted({F.hold[F.mon_of[j]] for j in range(a, b + 1)})
        spells.append({"from": F.dates[a], "to": F.dates[b], "days": b - a + 1,
                       "bmrot_value_share": [tilt.get(Q.mshift(h, -1)) for h in ms]})
    dT = arms["tbill"]["ex"]
    res, twr, plac = SW.class_s(ctx, "Q03", "S", "S1", pos, bO, bD, NPERM, unit="day", twins=tw, arms=arms,
                                extra_log={"fits": fitlog, "bear_spells": spells,
                                           "tbill_rebound_miss": SW.rebound_miss(ctx, pos, dT - SW.blend_fr(ctx, e_bar, bO, bT)["ex"]),
                                           "paper_check": {"shifts_per_year": SW.shifts_per_year(F, pos), "expect": "< 1 / 년"},
                                           "monthly_arm_shifts_per_year": SW.shifts_per_year(F, pm),
                                           "interpretation": INTERP},
                                targets_hash_src={"v0": BL.thash(ctx.V0_targets), "bmrot": BL.thash(_T), "lam": LAM})
    rk = SW.pct_rank(plac["down_dD"]["draws"], plac["down_dD"]["true"])
    res["g4"] = {"placebo_down_ge95": bool(rk >= 95), "sma200_twin_beaten": bool(twr["sma200"]["all"] and twr["sma200"]["down"]),
                 "vol_twin_beaten": bool(twr["vol"]["all"] and twr["vol"]["down"])}
    res["label_caps"] = {"추세 게이트 재포장": not res["g4"]["sma200_twin_beaten"], "변동성 타이밍 재포장": not res["g4"]["vol_twin_beaten"]}
    res["log"]["placebo_rank"] = rk
    return {"Q03": res}


INTERP = ["ē = 보유 창 수익일 중 공격(BULL 위치) 몫 — 1일 지연 뒤의 위치로 잰다(노출과 같은 뜻)",
          "rf 일할(특징 · BULL 이름표) = (1 + 직전 달 rf_monthly)^(1/그달 거래일 수) − 1 — 카드의 «그달 rf_monthly» 는 그달 DGS3MO 일별 평균이라 "
          "t 뒤의 날을 담는다(시점 규율 2) → 끝난 달의 값(카드 수정 필요 · 단언). T-bill 장부의 보유 수익은 그달 값 그대로(신호가 아니다)",
          "sma200 쌍둥이: 카드 문구대로 ^GSPC 종가 < 그날 포함 200일 단순평균이면 수비(동점 = 공격) · 랩 t-sma200 은 동일가중 유니버스 지수에서 "
          "종가 > SMA 일 때만 투자(동점 = 수비)라 다르다 — 카드 문구를 골랐다",
          "표준화 sd = 모집단 sd(ddof 0 · sklearn StandardScaler 와 같다)",
          "BULL = 학습일 중 그 국면 날들의 초과수익 복리 누적(Π(1 + R) − 1)이 큰 국면",
          "적합 실패 = 표준화 불가 또는 최적 해가 한 국면만 쓴 퇴화 해 → 그 반년은 OFFENSE(카드 FALLBACK)",
          "비터비 동점은 머무름 · 국면 0 쪽 · 온라인 마지막 동점은 국면 0",
          "T-bill 팔: 현금 쪽 매매 비용 0 — 교체마다 주식 장부 쪽 10bp 만",
          "월간 팔(b): 날마다 그 이전 마지막 월말 종가의 JM 상태를 쓰고 1일 지연은 규칙과 같다",
          "변동성 쌍둥이(일간): σ_t ≥ {σ_s : 2006-04 ≤ s ≤ t} 의 np.quantile(수준 ē · 선형 보간)이면 수비",
          "REBOUND-MISS: 공격→수비 교체 종가 뒤 0~63 거래일 안에 첫 거래일이 오는 SURGE-M 보유월",
          "위약 백분위 = 100 × mean(뽑기 < 참값)(eg30plus 규약) · 관문 ≥ 95"]


if __name__ == "__main__":
    import time
    t0 = time.time()
    print(json.dumps(selftest(), ensure_ascii=False, default=str))
    if "--dry" in sys.argv:
        ctx = Q.Ctx()
        print(json.dumps(dry(ctx), ensure_ascii=False, default=str))
    print("%.0f초" % (time.time() - t0))
