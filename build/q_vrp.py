# -*- coding: utf-8 -*-
"""build/q_vrp.py — Q16 VRP-HIBETA · 분산위험 프리미엄 고베타 교체 — 내재분산(VIX²)이 실현분산을 평소보다 크게 웃돈 달부터
3개월은 슬리브를 고베타(SPHB)로 (Bollerslev-Tauchen-Zhou 2009).

근본 이유 — 분산위험 프리미엄(VRP = 내재분산 − 실현분산)은 투자자가 변동성 급등을 피하려고 치르는 보험료다. 이것이 평소보다 크면
  시장 전체의 위험회피가 실제 위험보다 크다는 뜻이고, 그만큼 주식의 기대수익도 높다(BTZ: 1990~2005 분기 초과수익 변동의 15% 이상).
  신호가 켜지는 때는 대개 급락 직후(실현변동은 가라앉는데 VIX 는 높게 남은 반등 초입)이거나 평온하지만 불안이 가격에 남은 구간이다.
  급락 한가운데서는 실현분산이 내재분산을 넘어 켜지지 않는다 — 급락에서는 SPY 를 그대로 들고 반등에서만 고베타로 기대수익을 더 받는
  비대칭 구조다. 판정은 같은 평균 고베타 몫의 고정 혼합 대비라 고베타 자체의 성과(고베타 이상현상 불리함)는 빠지고 타이밍만 남는다.

규칙(카드 Q16 그대로):
  달 k(2006-02 ~): IV_k = (VIX_k/100)²/12(월말 종가 · assets.json ^VIX) · RV_k = Σ_{d∈k} [ln(P_d/P_{d−1})]²(^GSPC = bench_px spx 거래일) ·
    VRP_k = IV_k − RV_k · High_m = VRP_m > median{VRP_k : 2006-02 ≤ k ≤ m}(확장 · 그달 포함).
  비중: 월말 m(monthly_forms 2016-08 ~ 2026-07)에 m+1 슬리브 = h_m·SPHB + (1 − h_m)·SPY · h_m = (High_m + High_{m−1} + High_{m−2})/3 ·
    현금 없음 · 레버리지 없음.
  매매: qbatch_core.etf_path(월말 종가 · 다음 월말까지 보유 · 거래액 전부에 편도 10bp · 흘러간 몫 되맞춤 포함) · 펀드 fund_from_path TR · PR.
  쌍둥이(관문 · 선택 불가): IV 만(High'_m = IV_m > IV 확장 중앙값) · 측정만: RV 만(RV_m < RV 확장 중앙값이면 켜짐).
  1차(부류 S): Δ^D = X_rule − X_D · D = f̄·SPHB + (1 − f̄)·SPY 매월 되맞춤 · f̄ = h_m 의 실현 평균 ·
    p = 학생화 순열 — High = 1 · High = 0 구간 길이를 따로 섞어 참 첫 상태부터 다시 엮고 분할을 다시 계산 · NW(3) t · 10,000 번.
  관문: (a) 하락월 Δ^D > 0 · (b) 규칙 − IV 쌍둥이 전 월 평균 > 0(아니면 «변동성 수준 재포장») · (c) SURGE-M Δ^D > 0 · (d) 하락월 X ≥ 0 ·
    (e) F0: High 경로 구간 ≥ 12.
출처: Bollerslev, Tauchen & Zhou(2009) «Expected Stock Returns and Variance Risk Premia»(RFS 22(11) · FEDS 2007-11 원문 열람 · eq.3 ·
  §3.2.1) · scratchpad/qbatch_final.md # Q16 · build/qbatch_core.py etf_path.
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402

CARDS = {"Q16": {"cls": "S", "slot": "A5"}}
NPERM = 10000
K0 = "2006-02"
HB, SP = "SPHB", "SPY"
COST, COST20 = Q.COST, 0.0020
RUNS_MIN = 12
_CACHE = {}


# ── 신호 ─────────────────────────────────────────────────────────────────
def iv_of(vix):
    """IV = (VIX/100)²/12 — 연율 내재분산을 월 분산으로(BTZ eq. 3 의 월 단위)."""
    return (vix / 100.0) ** 2 / 12.0


def rv_by_month(dates, px):
    """달 → RV = Σ_{d∈달} [ln(P_d/P_{d−1})]² — 그달 거래일마다(첫날은 전달 마지막 종가 대비) · 값 없는 날은 건너뛴다."""
    rv, prev = {}, None
    for d, p in zip(dates, px):
        if p is None:
            continue
        if prev is not None:
            rv[d[:7]] = rv.get(d[:7], 0.0) + math.log(p / prev) ** 2
        prev = p
    return rv


def monthly_iv_rv(ctx):
    """달 → (IV, RV) — IV 는 assets.json ^VIX 월말(격자 월말 자리) · RV 는 bench_px spx 거래일 로그수익 제곱합."""
    key = ("IVRV", id(ctx))
    if key in _CACHE:
        return _CACHE[key]
    A = ctx.A
    B = Q.load("bench_px.json")
    bd = B["dates"]
    rv = rv_by_month(bd, B["series"]["spx"]["px"])
    blast = {}
    for d in bd:
        blast[d[:7]] = d
    vix = A.px["^VIX"]
    last = Q.monthly_forms()[-1]                           # 규칙이 쓰는 마지막 달(2026-07) — 그 뒤 달(부분 달 포함)은 보지 않는다
    out = {}
    for m in sorted(A.me):
        if m < K0 or m > last or m not in rv:
            continue
        assert blast[m] == A.dates[A.me[m]], "IV 월말과 RV 마지막 날이 다르다(%s)" % m   # 같은 날 종가에서 IV · RV 가 닫힌다
        v = vix[A.me[m]]
        if v == v:
            out[m] = (iv_of(v), rv[m])
    _CACHE[key] = out
    return out


def exp_median_flag(vals, months, gt=True):
    """확장 중앙값(K0 ~ m 포함) — gt: 값 > 중앙값이면 1 · 아니면(RV 쌍둥이) 값 < 중앙값이면 1."""
    hist, out = [], {}
    for m in months:
        hist.append(vals[m])
        med = float(np.median(hist))
        out[m] = int(vals[m] > med) if gt else int(vals[m] < med)
    return out


def high_paths(ctx):
    iv_rv = monthly_iv_rv(ctx)
    ms = sorted(iv_rv)
    assert ms[0] == K0
    vrp = {m: iv_rv[m][0] - iv_rv[m][1] for m in ms}
    return {"rule": exp_median_flag(vrp, ms), "iv": exp_median_flag({m: iv_rv[m][0] for m in ms}, ms),
            "rv": exp_median_flag({m: iv_rv[m][1] for m in ms}, ms, gt=False)}, vrp


def tranche(high, m):
    return (high[m] + high[Q.mshift(m, -1)] + high[Q.mshift(m, -2)]) / 3.0


def decide_of(h):
    def f(m):
        x = h[m]
        w = {}
        if x > 1e-12:
            w[HB] = x
        if 1 - x > 1e-12:
            w[SP] = 1 - x
        return w
    return f


# ── 월 닫힌 식(순열용) · etf_path 와 같은 값(selftest) ─────────────────────
def gross(A, forms):
    ends = forms + [Q.mshift(forms[-1], 1)]
    gH = np.array([A.px[HB][A.me[ends[j + 1]]] / A.px[HB][A.me[ends[j]]] for j in range(len(forms))])
    gY = np.array([A.px[SP][A.me[ends[j + 1]]] / A.px[SP][A.me[ends[j]]] for j in range(len(forms))])
    gI = {b: np.array([(A.IX_TR if b == "TR" else A.IX_PR)[A.me[ends[j + 1]]] / (A.IX_TR if b == "TR" else A.IX_PR)[A.me[ends[j]]]
                       for j in range(len(forms))]) for b in ("TR", "PR")}
    return gH, gY, gI


def sleeve_closed(h, gH, gY, c=COST):
    """분할 경로 h(편입월 순) → 보유월 슬리브 성장(다음 편입의 되맞춤 비용 포함 · 마지막 달은 매매 없음)."""
    g = h * gH + (1 - h) * gY
    hn = np.append(h[1:], h[-1])
    tr = np.abs(g * hn - h * gH) + np.abs(g * (1 - hn) - (1 - h) * gY)
    tr[-1] = 0.0
    return g - c * tr


def fund_ex(gS, gI, c=COST):
    v = 0.9 * gI + 0.1 * gS
    return (v * (1 - 2 * c * np.abs(0.1 * gS / v - 0.1)) - gI) * 100


def runs(x):
    x = np.asarray(x)
    cut = np.flatnonzero(np.diff(x)) + 1
    b = np.concatenate([[0], cut, [len(x)]])
    return int(x[0]), np.diff(b)


def seg_shuffle(x, rng):
    """High = 1 · High = 0 구간 길이를 따로 섞고 참 첫 상태부터 번갈아 엮는다(q_switch.seg_shuffle 과 같은 식)."""
    import q_switch as SW
    return SW.seg_shuffle(np.asarray(x, np.int8), rng)


# ── 계약 ─────────────────────────────────────────────────────────────────
def selftest():
    """합성 — 닫힌 식 = etf_path + fund_from_path · 확장 중앙값 · 분할 · 구간 섞기 보존."""
    tests = {}
    rng = np.random.default_rng(Q.SEED)

    class _A:
        pass
    nM, dpm = 8, 21
    D = nM * dpm + 1
    A = _A()
    A.me = {Q.mshift("2020-01", k): k * dpm for k in range(nM + 1)}
    A.px = {HB: np.cumprod(np.r_[1.0, 1 + rng.normal(0.0006, 0.02, D - 1)]), SP: np.cumprod(np.r_[1.0, 1 + rng.normal(0.0004, 0.01, D - 1)])}
    A.IX_TR = A.IX_PR = A.px[SP].copy()
    A.RF = {}
    forms = [Q.mshift("2020-01", k) for k in range(nM)]
    hv = np.array([0, 1 / 3, 2 / 3, 1, 1, 2 / 3, 0, 1 / 3])
    h = dict(zip(forms, hv))
    sl = Q.etf_path(A, decide_of(h), forms)
    fr = Q.fund_from_path(A, sl, forms)
    gH, gY, gI = gross(A, forms)
    tests["closed_eq_etf_path"] = bool(np.max(np.abs(fund_ex(sleeve_closed(hv, gH, gY), gI["TR"]) - fr["ex"])) < 1e-10)
    # 뽑기마다 다시 짜는 D(고정 몫 f) — 닫힌 식 = etf_path(decide 상수)
    frD = Q.fund_from_path(A, Q.etf_path(A, decide_of({m: 0.37 for m in forms}), forms), forms)
    tests["closed_D_eq_etf_path"] = bool(np.max(np.abs(fund_ex(sleeve_closed(np.full(nM, 0.37), gH, gY), gI["TR"]) - frD["ex"])) < 1e-10)
    import q_switch as SW
    tests["perm_p_fail_closed"] = bool(SW.perm_p(None, [1.0]) == 1.0)
    f = exp_median_flag({"a": 1.0, "b": 3.0, "c": 2.0, "d": 2.0}, ["a", "b", "c", "d"])
    tests["exp_median"] = f == {"a": 0, "b": 1, "c": 0, "d": 0}
    fr_ = exp_median_flag({"a": 1.0, "b": 3.0, "c": 2.0, "d": 1.5}, ["a", "b", "c", "d"], gt=False)
    tests["exp_median_rv_lt"] = fr_ == {"a": 0, "b": 0, "c": 0, "d": 1}
    rv = rv_by_month(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-04", "2020-02-05"], [100.0, 110.0, 99.0, None, 99.0 * 1.02])
    tests["rv_month_log_sq"] = bool(abs(rv["2020-01"] - math.log(1.1) ** 2) < 1e-15
                                    and abs(rv["2020-02"] - (math.log(0.9) ** 2 + math.log(1.02) ** 2)) < 1e-15)
    tests["iv_monthly_var"] = abs(iv_of(20.0) - 0.04 / 12) < 1e-18
    hi = {Q.mshift("2020-01", k): v for k, v in enumerate([1, 0, 1, 1, 0])}
    tests["tranche"] = abs(tranche(hi, "2020-04") - 2 / 3) < 1e-15
    x = np.array([1, 1, 0, 1, 0, 0, 0, 1], np.int8)
    y = seg_shuffle(x, rng)
    tests["shuffle_preserve"] = bool(y.sum() == x.sum() and runs(y)[0] == runs(x)[0] and len(runs(y)[1]) == len(runs(x)[1]))
    return {"ok": all(bool(v) for v in tests.values()), "tests": tests}


def _setup(ctx):
    forms = Q.monthly_forms()
    H, vrp = high_paths(ctx)
    A = ctx.A
    for m in forms:                                        # 결정 m 은 그달 월말 종가까지 · SPHB 가격이 선다
        i = A.me[m]
        assert A.dates[i][:7] == m and A.dates[i + 1][:7] != m
        assert A.px[HB][i] == A.px[HB][i]
    hs = {k: {m: tranche(H[k], m) for m in forms} for k in H}
    win = Q.months_between(Q.mshift(forms[0], -2), forms[-1])     # 분할에 들어가는 High 달(2016-06 ~ 2026-07)
    return forms, H, hs, vrp, win


def dry(ctx):
    """구성만 — 신호 달 수 · 켜진 달 · 분할 분포 · f̄ · 구간 수(F0) · 날짜 단언. 수익 없음."""
    forms, H, hs, vrp, win = _setup(ctx)
    hv = np.array([hs["rule"][m] for m in forms])
    s0, L = runs([H["rule"][m] for m in win])
    return {"n_vrp_months": len(vrp), "first": min(vrp), "n_forms": len(forms), "f_bar": float(hv.mean()),
            "h_counts": {str(round(v, 3)): int(np.sum(np.isclose(hv, v))) for v in (0, 1 / 3, 2 / 3, 1)},
            "high_runs_window": int(len(L)), "f0": {"ok": bool(len(L) >= RUNS_MIN), "why": "High 경로(2016-06 ~ 2026-07) 구간 %d(≥ %d)" % (len(L), RUNS_MIN)},
            "iv_twin_f_bar": float(np.mean([hs["iv"][m] for m in forms])), "rv_twin_f_bar": float(np.mean([hs["rv"][m] for m in forms]))}


def run(ctx):
    """한 번 굽기 — Q16 CardResult."""
    import eg30plus as E
    forms, H, hs, vrp, win = _setup(ctx)
    A = ctx.A
    hv = np.array([hs["rule"][m] for m in forms])
    f_bar = float(hv.mean())
    fr = ctx.etf_fr(decide_of(hs["rule"]), forms, "TR", COST)
    fr_pr = ctx.etf_fr(decide_of(hs["rule"]), forms, "PR", COST)
    fr20 = ctx.etf_fr(decide_of(hs["rule"]), forms, "TR", COST20)
    hD = {m: f_bar for m in forms}
    D = ctx.etf_fr(decide_of(hD), forms, "TR", COST)
    D20 = ctx.etf_fr(decide_of(hD), forms, "TR", COST20)
    Dpr = ctx.etf_fr(decide_of(hD), forms, "PR", COST)
    arms = {"twin_iv": ctx.etf_fr(decide_of(hs["iv"]), forms, "TR", COST), "twin_rv": ctx.etf_fr(decide_of(hs["rv"]), forms, "TR", COST),
            "sphb_static": ctx.etf_fr(decide_of({m: 1.0 for m in forms}), forms, "TR", COST)}
    # 순열 — High(2016-06 ~ 2026-07) 구간 섞기 → 분할 → 닫힌 식 · 뽑기마다 D 를 그 뽑기의 f̄ 로 다시 짠다
    #   (분할 가장자리 무게가 달라 — 2016-06 · 2026-07 은 한 번, 2016-07 · 2026-06 은 두 번 — 섞으면 f̄ 가 조금 움직인다)
    import q_switch as SW
    gH, gY, gI = gross(A, forms)
    xD = D["ex"]
    x_obs = fund_ex(sleeve_closed(hv, gH, gY), gI["TR"])
    assert np.max(np.abs(x_obs - fr["ex"])) < 1e-8, "닫힌 식 ≠ etf_path"
    xD_of = lambda f: fund_ex(sleeve_closed(np.full(len(forms), f), gH, gY), gI["TR"])
    assert np.max(np.abs(xD_of(f_bar) - xD)) < 1e-8, "D 닫힌 식 ≠ etf_path"
    dm = ctx.dmask(fr["hold"])
    d_obs = fr["ex"] - xD
    t_obs = E.nw_t(d_obs)
    hw = np.array([H["rule"][m] for m in win], np.int8)
    rng = np.random.default_rng(Q.SEED)
    tp, fs = [], []
    for _ in range(NPERM):
        y = seg_shuffle(hw, rng)
        hi = dict(zip(win, y.tolist()))
        hp = np.array([tranche(hi, m) for m in forms])
        f_p = float(hp.mean())
        fs.append(f_p)
        tv = E.nw_t(fund_ex(sleeve_closed(hp, gH, gY), gI["TR"]) - (xD if f_p == f_bar else xD_of(f_p)))
        tp.append(-1e9 if tv is None else float(tv))
    p = SW.perm_p(t_obs, tp)
    ME = Q.load("mech_episodes.json")
    pos = {h: j for j, h in enumerate(fr["hold"])}
    sj = [pos[m] for m in ME["months"]["surge_m"] if m in pos]
    cj = [m for m in ME["months"]["crash_m"] if m in pos]
    di = fr["ex"] - arms["twin_iv"]["ex"]
    s0, L = runs(hw)
    # REBOUND-MISS 읽기 — «교체 밖» = 분할이 줄어든 편입(h_m < h_{m−1}) · 그 뒤 63거래일 안에 시작한 SURGE-M 의 Δ^D
    outs = [A.me[forms[k]] for k in range(1, len(forms)) if hv[k] < hv[k - 1] - 1e-12]
    rb = [h for h in ME["months"]["surge_m"] if h in pos and any(0 <= A.me[Q.mshift(h, -1)] + 1 - o <= 63 for o in outs)]
    rbv = [float(d_obs[pos[h]]) for h in rb]
    res = {"code": "Q16", "cls": "S", "slot": "A5", "fr": fr, "fr_pr": fr_pr, "fr20": fr20,
           "controls": {"D": D, "D20": D20, "D_pr": Dpr}, "arms": arms, "placebo": {},
           "perm": {"t_obs": t_obs, "t_perm": tp, "p": p, "n": NPERM, "seed": Q.SEED, "unit": "month(High 2016-06 ~ 2026-07)",
                    "D_per_draw": "뽑기마다 D = f̄_draw·SPHB + (1 − f̄_draw)·SPY(월 닫힌 식)", "f_draw_min_max": ([min(fs), max(fs)] if fs else None),
                    **({"p_note": "t_obs 없음(n < 5 또는 NW 분산 0) → p = 1(기각 못 함)"} if t_obs is None else {})},
           "g4": {"iv_twin_beaten": bool(float(di.mean()) > 0), "surge_dD_pos": bool(float(d_obs[sj].mean()) > 0) if sj else False},
           "label_caps": {}, "f0": {"ok": bool(len(L) >= RUNS_MIN), "why": "High 경로(2016-06 ~ 2026-07) 구간 %d(≥ %d)" % (len(L), RUNS_MIN)},
           "targets_hash": Q_hash({m: round(hs["rule"][m], 6) for m in forms}),
           "log": {"f_bar": f_bar, "e_bar": f_bar, "h": {m: round(hs["rule"][m], 4) for m in forms}, "high": {m: H["rule"][m] for m in win},
                   "vrp": {m: round(v, 8) for m, v in vrp.items() if m >= "2016-01"},
                   "h_pos_in_crash_m": [m for m in cj if hs["rule"].get(Q.mshift(m, -1), 0) > 0],
                   "n_surge_m": len(sj), "down_mean_X_ge0": None,
                   "rebound_miss": {"months": rb, "n": len(rb), "mean_dD": (float(np.mean(rbv)) if rbv else None),
                                    "applies": len(rb) >= 3, "ok": (None if len(rb) < 3 else bool(np.mean(rbv) >= 0)),
                                    "switch_out_def": "h_m < h_{m−1} 인 편입 월말"},
                   "turn_oneway_yr": fr["turn"], "interpretation": INTERP}}
    res["label_caps"] = {"변동성 수준 재포장": not res["g4"]["iv_twin_beaten"]}
    res["log"]["down_mean_X_ge0"] = bool(float(fr["ex"][dm].mean()) >= 0)
    SW.check_runner_keys(res)
    return {"Q16": res}


def Q_hash(o):
    import hashlib
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


INTERP = ["IV 는 assets.json ^VIX 의 그달 마지막 격자일 종가 · RV 는 bench_px spx 의 그달 거래일(첫날은 전달 마지막 종가 대비) 로그수익 제곱합",
          "확장 중앙값 = np.median(2006-02 ~ m, 그달 포함) · 규칙 «>» · RV 쌍둥이 «<»",
          "순열은 분할에 들어가는 High 달(2016-06 ~ 2026-07 · 122 달)의 구간 길이를 섞는다 · 앞선 달(2006-02 ~ 2016-05)은 쓰지 않는다 · "
          "분할 가장자리 무게 탓에 섞으면 f̄ 가 조금 움직여 뽑기마다 D 를 그 뽑기의 f̄ 로 다시 짠다 · t_obs 가 없으면 p = 1",
          "VIX 종가(오후 4:15 ET 확정)로 SPY · SPHB 를 그날 4:00 종가에 사고판다 — 15분 앞선 정보(카드 문구 그대로 · 한계로 적는다)",
          "log.e_bar = f̄(부류 S 공통 키) · IV · RV 는 규칙이 쓰는 달(≤ 2026-07)만 만든다(그 뒤 부분 달의 날짜 단언으로 굽기가 멈추지 않게)",
          "D = 매월 f̄ 로 되맞춤(etf_path · 흘러간 몫 되맞춤도 10bp) · f̄ = 120 편입 h_m 평균",
          "REBOUND-MISS(G2 추가) 읽기: 이 카드엔 수비 교체가 없어 «분할이 줄어든 편입 월말» 을 교체 밖으로 본다",
          "위약은 카드에 없다 — placebo 비움 · 1차 p 는 perm",
          "RV 원자료는 카드대로 bench_px spx(assets.json ^GSPC 와 5213일 모두 같은 값 · 결측 0 — 2026-09-25 확인) · IV 월말 날 = RV 마지막 날을 단언"]


if __name__ == "__main__":
    import time
    t0 = time.time()
    print(json.dumps(selftest(), ensure_ascii=False, default=str))
    if "--dry" in sys.argv:
        ctx = Q.Ctx()
        print(json.dumps(dry(ctx), ensure_ascii=False, default=str))
    print("%.0f초" % (time.time() - t0))
