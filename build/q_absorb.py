# -*- coding: utf-8 -*-
"""build/q_absorb.py — Q10 SF1-ARSHIFT · 흡수비율 급등 교체 — S&P 500 종목 공분산이 소수 요인에 묶이면 EG30 → x-bmrot
(Kritzman-Li-Page-Rigobon 2011).

근본 이유 — 흡수비율(AR)은 종목 수익 분산 가운데 상위 1/5 고유벡터(소수 공통요인)가 설명하는 몫이다. 이 몫이 한 해 평균보다
  짧은 기간(15일)에 크게 뛰면 종목들이 하나의 위험(대개 시장·유동성 요인)에 묶이고 있다는 뜻이고, 한 곳의 충격이 분산되지 않고
  전체로 빨리 번진다(«취약성»). 이 결합을 만드는 것은 레버리지 · 공통 보유자 · 위험예산(VaR) 매도이고, 결합이 강해질 때 가장 크게
  잃는 것이 베타 1.22 의 고성장 바스켓 EG30 이다. 그때만 수비 엔진 x-bmrot 으로 옮기는 것이 같은 평균 몫의 고정 혼합보다 나은지 묻는다.

규칙(카드 Q10 그대로):
  신호 유니버스(거래일 t · 2014-06-30 부터): t 이하 마지막 월말의 PIT S&P 500 명단(index_history 'spx' · 비는 달은 직전 달) ·
    회사당 한 클래스(pit_panel CIK 규칙 · KEEP_DUAL) · 재배정 티커의 마지막 멤버월 제외(pit_panel 규칙) · 날짜 인식 가격 키(그날 가격이 선 후보) ·
    t 로 끝나는 500일 중 95% 이상 유효 수익이 있는 종목만 · 결측 수익 = 0.
  AR_t = 상위 n_t 고유값 합 ÷ 대각합(500일 동일가중 표본 공분산 · n_t = round(N_t/5)).
  ΔAR_t = [평균 AR(t−14..t) − 평균 AR(t−251..t)] / sd AR(t−251..t)(표본 sd).
  결정(월말 m 종가 · 2016-08 ~ 2026-07): ΔAR_m > +1.0 → m+1 은 DEFENSE(x-bmrot) · 아니면 OFFENSE(EG30 V0) · 이력현상 없음 · 월중 발동 없음.
  대체: N_m < 300 이거나 AR 값이 252 개 미만이면 OFFENSE. 교체 = 판 장부 10bp + 산 장부 10bp · 펀드 90/10.
측정만: (a) T-bill DEFENSE · (b) 논문 3국면 지도(ΔAR < −1 / ±1 안 / > 1 → 공격 몫 1 / 0.5 / 0) · (c) 9 SPDR 의 AR(n = 2).
관문(카드 G4): 위약(하락월 Δ^D) ≥ 95 · ē 맞춘 월간 변동성 쌍둥이를 전 월 · 하락월 평균 둘 다 이긴다(아니면 «변동성 타이밍 재포장»).
출처: Kritzman, Li, Page & Rigobon(2011) «Principal Components as a Measure of Systemic Risk»(JPM) — OFR WP0001 §C.7 과
  Portfolio Optimizer 설명으로 옮김(원문은 못 열었다) · scratchpad/qbatch_final.md # Q10 · build/q_switch.py · build/q_bmrot_leg.py.
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

CARDS = {"Q10": {"cls": "S", "slot": "S1"}}
NPERM = 10000
AR0 = "2014-06-30"
WIN, COV_MIN, FRAC = 500, 0.95, 5
SHORT, LONG = 15, 252
TRIG = 1.0
N_MIN = 300
SPDR = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
SPDR_N = 2
_CACHE = {}


def month_key(Wd, i):
    """거래일 i 이하 마지막 월말의 달 — i 가 그달 마지막 거래일이면 그달, 아니면 전달."""
    d = Wd.dates[i]
    return d[:7] if Wd.me.get(d[:7]) == i else Q.mshift(d[:7], -1)


def spx_members(Wd, mm, i):
    """그달 말 S&P 500 명단 → [(명단 티커, 가격 키)] — pit_panel.union_members 와 같은 규칙(회사당 한 클래스 · 재배정 마지막 달 제외 · 날짜 인식 키)."""
    import pit_panel as PP
    W = Wd.W
    mem = set(W["lists"]["spx"].get(mm) or [])
    by = {}
    for t in mem:
        c = W["cikmap"].get(t) or W["cikmap"].get(t.replace("-", "."))
        by.setdefault(c or ("_" + t), []).append(t)
    keep = []
    for c, ts in sorted(by.items()):
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
    return out


def _returns(Wd):
    """가격 키별 일간 단순수익(유효: 전날 · 그날 가격이 둘 다 > 0) — (키 목록, R (D × K), 유효 마스크)."""
    key = ("R", id(Wd))
    if key in _CACHE:
        return _CACHE[key]
    ks = sorted(Wd.PX)
    P = np.array([Wd.PX[k] for k in ks], float).T         # D × K
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = np.zeros_like(P, bool)
        ok[1:] = (P[1:] == P[1:]) & (P[:-1] == P[:-1]) & (P[:-1] > 0) & (P[1:] > 0)
        R = np.where(ok, P / np.where(np.roll(P, 1, 0) > 0, np.roll(P, 1, 0), 1.0) - 1.0, 0.0)
    R[0] = 0.0
    out = ({k: j for j, k in enumerate(ks)}, R, ok)
    _CACHE[key] = out
    return out


def ar_of(M, n_top):
    """동일가중 표본 공분산(열 = 종목)의 상위 n_top 고유값 합 ÷ 대각합."""
    Mc = M - M.mean(0)
    C = Mc.T @ Mc / (len(M) - 1)
    ev = np.linalg.eigvalsh(C)
    return float(ev[-n_top:].sum() / np.trace(C))


def ar_at(R, ok, js, i):
    """거래일 i 의 (AR, N) — i 로 끝나는 500 수익일 창 · 유효 수익 ≥ 95% 인 열(js 중)만 · 결측 수익은 0(R 에 이미 0) · n = round(N/5)."""
    w0 = i - WIN + 1
    assert w0 >= 1
    okw = ok[w0:i + 1][:, js]
    keep = [j for j, c in zip(js, okw.sum(0)) if c >= COV_MIN * WIN]
    n = len(keep)
    return (ar_of(R[w0:i + 1][:, keep], int(round(n / FRAC))) if n >= FRAC else None), n


def ar_series(ctx):
    """거래일(2014-06-30 ~ 2026-07-31) → (AR, N) — 종목 격자 · 날마다 고유값 분해."""
    key = ("AR", id(ctx))
    if key in _CACHE:
        return _CACHE[key]
    Wd = ctx.Wd
    col, R, ok = _returns(Wd)
    i_a = Wd.dates.index(AR0)
    i_z = Wd.me[Wd.months[-1]]
    ar, nn = {}, {}
    for i in range(i_a, i_z + 1):
        mm = month_key(Wd, i)
        mem = spx_members(Wd, mm, i)
        js = sorted({col[k] for _t, k in mem})
        ar[Wd.dates[i]], nn[Wd.dates[i]] = ar_at(R, ok, js, i)
    _CACHE[key] = (ar, nn)
    return ar, nn


def delta_ar(ar_by_date, dates):
    """ΔAR_t = (평균 AR(t−14..t) − 평균 AR(t−251..t)) / sd AR(t−251..t) · 창이 안 차면 None."""
    a = np.array([np.nan if ar_by_date.get(d) is None else ar_by_date[d] for d in dates])
    out = {}
    for k in range(len(dates)):
        if k + 1 < LONG:
            out[dates[k]] = None
            continue
        L_ = a[k - LONG + 1:k + 1]
        S_ = a[k - SHORT + 1:k + 1]
        if np.isnan(L_).any():
            out[dates[k]] = None
            continue
        sd = float(np.std(L_, ddof=1))
        out[dates[k]] = (float(S_.mean()) - float(L_.mean())) / sd if sd > 0 else None
    return out


def state_of(v, fb):
    """ΔAR → (0/1 상태, 3국면 공격 몫) — ΔAR > +1 이면 수비(0) · 3국면: ΔAR < −1 → 1 · ±1 안(경계 포함) → 0.5 · > 1 → 0 · 대체면 공격."""
    if fb:
        return 1, 1.0
    return (0 if v > TRIG else 1), (1.0 if v < -TRIG else (0.0 if v > TRIG else 0.5))


def monthly_state(ctx):
    """편입월 m → 1(OFFENSE) · 0(DEFENSE) · 3국면 몫 · 기록."""
    key = ("ST", id(ctx))
    if key in _CACHE:
        return _CACHE[key]
    Wd = ctx.Wd
    ar, nn = ar_series(ctx)
    ds = sorted(ar)
    dar = delta_ar(ar, ds)
    st, s3, log = {}, {}, []
    for m in Wd.months:
        d = Wd.dates[Wd.me[m]]
        n_ar = sum(1 for x in ds if x <= d and ar[x] is not None)
        v = dar.get(d)
        fb = (nn[d] < N_MIN) or (n_ar < LONG) or v is None
        st[m], s3[m] = state_of(v, fb)
        log.append({"m": m, "N": nn[d], "AR": (None if ar[d] is None else round(ar[d], 5)), "dAR": (None if v is None else round(v, 4)),
                    "fallback": bool(fb), "state": st[m]})
    out = (st, s3, log)
    _CACHE[key] = out
    return out


def spdr_state(ctx):
    """(c) 9 SPDR AR(n = 2) — 같은 ΔAR · 같은 문턱 · 자산 격자(assets.json)."""
    A = ctx.A
    P = np.array([A.px[t] for t in SPDR]).T
    R = P[1:] / P[:-1] - 1
    ar = {}
    i_z = A.me[ctx.Wd.months[-1]]
    for i in range(WIN, i_z + 1):
        M = R[i - WIN:i]                       # 수익일 i−499 … i(R 는 한 칸 밀려 있다)
        ar[A.dates[i]] = ar_of(M, SPDR_N)
    ds = sorted(ar)
    dar = delta_ar(ar, ds)
    st = {}
    for m in ctx.Wd.months:
        v = dar.get(A.dates[A.me[m]])
        st[m] = state_of(v, v is None)[0]
    return st


# ── 계약 ─────────────────────────────────────────────────────────────────
def selftest():
    """합성 — AR: 한 요인 모형이면 상위 1/5 몫이 크고 독립이면 작다 · 대각 공분산이면 AR = 상위 분산 몫 · ΔAR 식 · 교체 틀."""
    rng = np.random.default_rng(Q.SEED)
    tests = {}
    T, N = 500, 50
    f = rng.normal(0, 0.02, (T, 1))
    M1 = f @ np.ones((1, N)) + rng.normal(0, 0.005, (T, N))
    M0 = rng.normal(0, 0.01, (T, N))
    tests["ar_factor_high"] = bool(ar_of(M1, 10) > 0.9)
    tests["ar_indep_low"] = bool(ar_of(M0, 10) < 0.35)
    D = rng.normal(0, 1, (T, 3)) * np.array([3.0, 2.0, 1.0])
    C = np.cov(D, rowvar=False)
    tests["ar_eq_topvar_share"] = bool(abs(ar_of(D, 1) - np.linalg.eigvalsh(C)[-1] / np.trace(C)) < 1e-12)
    a = {("d%03d" % k): (1.0 if k < 300 else 2.0) + 0.001 * (k % 7) for k in range(320)}
    ds = sorted(a)
    dar = delta_ar(a, ds)
    tests["dar_spike_positive"] = bool(dar[ds[-1]] > 1.0 and dar[ds[100]] is None and dar[ds[250]] is None and dar[ds[251]] is not None)
    # ΔAR 식 그대로 — 무작위 AR 계열의 한 날을 손으로 푼 값과 비교
    ar_r = rng.uniform(0.3, 0.6, 300)
    a2 = {("e%03d" % k): float(ar_r[k]) for k in range(300)}
    d2 = delta_ar(a2, sorted(a2))
    L_ = ar_r[299 - 251:300]
    tests["dar_formula"] = bool(abs(d2["e299"] - (ar_r[299 - 14:300].mean() - L_.mean()) / L_.std(ddof=1)) < 1e-12)
    # 창 커버리지 — 500일 중 유효 ≥ 95%(475) 인 열만 · 결측 = 0 을 넣은 채 공분산
    Rm = rng.normal(0, 0.01, (WIN + 5, 12)) + rng.normal(0, 0.01, (WIN + 5, 1))
    okm = np.ones_like(Rm, bool)
    okm[5:5 + 26, 3] = False                                 # 474/500 → 빠진다
    okm[5:5 + 25, 4] = False                                 # 475/500 → 남는다
    Rm[~okm] = 0.0
    a_, n_ = ar_at(Rm, okm, list(range(12)), WIN + 4)
    keep = [j for j in range(12) if j != 3]
    tests["coverage_95"] = bool(n_ == 11 and abs(a_ - ar_of(Rm[5:WIN + 5][:, keep], int(round(11 / FRAC)))) < 1e-14)
    tests["state_map"] = bool(state_of(1.0001, False) == (0, 0.0) and state_of(1.0, False) == (1, 0.5) and state_of(-1.0, False) == (1, 0.5)
                              and state_of(-1.0001, False) == (1, 1.0) and state_of(5.0, True) == (1, 1.0))

    class _W:
        dates = ["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-28", "2020-03-02"]
        me = {"2020-01": 1, "2020-02": 3, "2020-03": 4}
    tests["month_key_last_month_end"] = bool([month_key(_W, i) for i in range(4)] == ["2019-12", "2020-01", "2020-01", "2020-02"])
    tests["switch_frame"] = SW.selftest()["ok"]
    return {"ok": all(bool(v) for v in tests.values()), "tests": tests}


def dry(ctx):
    """구성만 — 신호 N(커버리지 표류) · AR 값 수 · 대체 달 · 수비 달 수 · F0 · 날짜 단언. 수익 없음."""
    st, s3, log = monthly_state(ctx)
    F = SW.frame(ctx)
    pos = SW.pos_from_monthly(F, st)
    Wd = ctx.Wd
    for r in log:                                  # 결정일 = 그달 마지막 거래일 · 쓴 수익은 그날까지 · 명단은 그달 말 것
        i = Wd.me[r["m"]]
        assert Wd.dates[i][:7] == r["m"] and Wd.dates[i + 1][:7] != r["m"] and month_key(Wd, i) == r["m"]
        assert ctx.A.dates[ctx.A.me[r["m"]]] == Wd.dates[i]          # SPDR 팔 · 변동성 쌍둥이(자산 격자)의 월말도 같은 날
    Ns = [r["N"] for r in log]
    return {"N_first_last": [Ns[0], Ns[-1]], "N_min": min(Ns), "n_fallback": sum(r["fallback"] for r in log),
            "n_defense_months": sum(1 for r in log if r["state"] == 0), "e_bar": float(pos.mean()),
            "n_switch": int(np.sum(pos[1:] != pos[:-1])), "three_state_counts": {str(k): sum(1 for v in s3.values() if v == k) for k in (0.0, 0.5, 1.0)},
            "spdr_defense_months": sum(1 for v in spdr_state(ctx).values() if v == 0), "f0": SW.f0_check(F, pos, F.dmask())}


def run(ctx):
    """한 번 굽기 — Q10 CardResult."""
    import q_bmrot_leg as BL
    F = SW.frame(ctx)
    st, s3, slog = monthly_state(ctx)
    pos = SW.pos_from_monthly(F, st)
    bO, bD, bT = SW.offense_v0(ctx), SW.defense(ctx), SW.tbill_book(ctx)
    e_bar = float(pos.mean())
    vs = SW.vol_state_monthly(ctx, e_bar, F.months)
    tw = {"vol": SW.pos_from_monthly(F, vs)}
    arms = {"tbill": SW.switch_fr(ctx, pos, bO, bT),
            "ar_3state": SW.mix_fr(ctx, [s3[m] for m in F.months], bO, bD),
            "spdr_ar": SW.switch_fr(ctx, SW.pos_from_monthly(F, spdr_state(ctx)), bO, bD)}
    _T, _ = BL.targets(ctx.Wd)
    res, twr, plac = SW.class_s(ctx, "Q10", "S", "S1", pos, bO, bD, NPERM, unit="month", months_state=st, twins=tw, arms=arms,
                                extra_log={"signal": slog, "interpretation": INTERP,
                                           "tbill_rebound_miss": SW.rebound_miss(ctx, pos, arms["tbill"]["ex"] - SW.blend_fr(ctx, e_bar, bO, bT)["ex"])},
                                targets_hash_src={"v0": BL.thash(ctx.V0_targets), "bmrot": BL.thash(_T), "trig": TRIG})
    rk = SW.pct_rank(plac["down_dD"]["draws"], plac["down_dD"]["true"])
    res["g4"] = {"placebo_down_ge95": bool(rk >= 95), "vol_twin_beaten": bool(twr["vol"]["all"] and twr["vol"]["down"])}
    res["label_caps"] = {"변동성 타이밍 재포장": not res["g4"]["vol_twin_beaten"]}
    res["log"]["placebo_rank"] = rk
    return {"Q10": res}


INTERP = ["신호 명단에 pit_panel 의 재배정 마지막 멤버월 제외도 건다(카드는 «회사당 한 클래스 · 날짜 인식 키» 만 적었다 — 같은 규칙 묶음)",
          "날짜 인식 키는 그날 t 에 가격이 선 후보로 고른다 · 유효 수익 = 전날·그날 가격이 둘 다 > 0",
          "sd AR = 표본 sd(ddof 1) · 공분산 = 표본(ddof 1) · 결측 수익 0 을 넣은 뒤 열 평균을 뺀다",
          "ΔAR 은 AR 값이 선 거래일 계열에서 센다(창 안에 결측이 있으면 None → OFFENSE)",
          "월간 변동성 쌍둥이: 월말 σ63 ≥ 월말 표본(2006-04 ~ m)의 np.quantile(수준 ē)이면 m+1 수비",
          "ē = 보유 창 수익일 중 공격 몫 · 월간 상태라 공격 달 비율과 거래일 가중이 조금 다르다",
          "3국면 팔은 월말 되맞춤 혼합(mix_fr) — 0/1 교체 틀과 달리 판 쪽 장부의 그날 되맞춤 비용도 경로 안에 있다",
          "9 SPDR AR: 자산 격자 500 수익일 · 결측 없음 · N 문턱은 쓰지 않는다(9종)"]


if __name__ == "__main__":
    import time
    t0 = time.time()
    print(json.dumps(selftest(), ensure_ascii=False, default=str))
    if "--dry" in sys.argv:
        ctx = Q.Ctx()
        print(json.dumps(dry(ctx), ensure_ascii=False, default=str))
    print("%.0f초" % (time.time() - t0))
