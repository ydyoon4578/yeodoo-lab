# -*- coding: utf-8 -*-
"""build/q_corrsurp.py — Q06 SF2-CORRSURP · 상관 놀람 교체 — 크기와 상관이 함께 놀란 달 뒤에만 EG30 → x-bmrot
(Kinlaw-Turkington 2014) · 측정만(부류 M · F-Q 밖 · 시행 수와 DSR N 에는 센다).

근본 이유 — 터뷸런스(마할라노비스 거리)는 크기 놀람과 상관 놀람으로 나뉜다. 변동성 큰 달은 두 종류다: 모두 같이 떨어진 달(전형적
  상관)과, 평소 같이 움직이던 업종이 갈라진 달(상관 붕괴). 전형적 상관의 급락은 유동성 고갈·강제매도라 뒤에 반등 보상이 붙기 쉽고,
  상관 붕괴는 정보가 업종 사이로 천천히 번지는 중이거나 과거 상관을 믿은 위험모형이 깨져 위험축소가 이어진다는 신호다.
  Kinlaw·Turkington(2014)에서 둘이 함께 높은 달 다음 달 미국 주식은 연 2.5%, 크기만 높은 달 다음 달은 10.8% 였다.
  이 규칙은 «갈라지며 흔들린 달» 뒤에만 수비 엔진으로 옮긴다.

규칙(카드 Q06 그대로):
  자산: 원조 SPDR 9종(XLB XLE XLF XLI XLK XLP XLU XLV XLY) 일간 단순수익 · n = 9.
  추정: t ≥ 2009-01-02 마다 t−1 로 끝나는 창의 동일가중 μ · Σ — 창은 2006-01-04 이후 모든 날 · 최소 756 · 최대 2520.
  점수: TURB = (y−μ)'Σ⁻¹(y−μ)/n · MS = (y−μ)'diag(Σ)⁻¹(y−μ)/n · CS = TURB/MS.
  월: MonthMS = 그달 MS 평균 · MonthCS = Σ CS·MS / Σ MS.
  신호: HighMS_m = MonthMS_m ≥ {MonthMS_k : 2009-01 ≤ k ≤ m} 의 80 백분위(확장 · 36 개월 전엔 거짓) · Signal_m = HighMS_m 이고 MonthCS_m > 1.
  위치: Signal_m 이면 m+1 슬리브 = DEFENSE(x-bmrot) · 아니면 OFFENSE(EG30 V0) · 교체 10bp 씩 · 펀드 90/10.
팔: T-bill DEFENSE · 쌍둥이 T1 = HighMS 만 · T2 = HighMS 이고 CS ≤ 1.
보고: GICS 개편(2016-09 XLRE · 2018-09 커뮤니케이션 · 2023-03 V/MA) 뒤 6개월의 MS/CS · 2018-10 이후 자료만으로 다시 추정한 부분 표본.
F0: 신호 달 < 6 → 측정 불가.
출처: Kinlaw & Turkington(2014) «Correlation Surprise»(J. Asset Mgmt · 공개본 열람) · scratchpad/qbatch_final.md # Q06 · build/q_switch.py.
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

CARDS = {"Q06": {"cls": "M", "slot": None}}
NPERM = 10000
SPDR = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
D0, S0 = "2006-01-04", "2009-01-02"
WMIN, WMAX = 756, 2520
PCT, NMIN_M = 80, 36
M0 = "2009-01"
SUB0 = "2018-10-01"
BREAKS = ("2016-09", "2018-09", "2023-03")
F0_MIN = 6
_CACHE = {}


def tms(e, S):
    """한 날의 (TURB, MS, CS) — e = y − μ · S = Σ · TURB = e'Σ⁻¹e/n · MS = e'diag(Σ)⁻¹e/n · CS = TURB/MS."""
    n = len(e)
    turb = float(e @ np.linalg.solve(S, e)) / n
    ms = float((e * e / np.diag(S)).sum()) / n
    return turb, ms, turb / ms


def scores(Y, i_start, i_first, i_last):
    """일간 (TURB, MS, CS) — t 마다 [max(i_start, t − WMAX), t − 1] 창(≥ WMIN) 의 μ · Σ(표본 · ddof 1)."""
    out = {}
    for t in range(i_first, i_last + 1):
        a = max(i_start, t - WMAX)
        if t - a < WMIN:
            continue
        W = Y[a:t]
        assert a + len(W) == t                            # 창은 t−1 에서 끝난다(그날 t 는 빠진다)
        out[t] = tms(Y[t] - W.mean(0), np.cov(W, rowvar=False))
    return out


def monthly(A, sc):
    """달 → (MonthMS, MonthCS = ΣTURB/ΣMS)."""
    acc = {}
    for t, (tu, ms, cs) in sc.items():
        m = A.dates[t][:7]
        a = acc.setdefault(m, [0.0, 0.0, 0])
        a[0] += ms; a[1] += cs * ms; a[2] += 1
    return {m: (v[0] / v[2], v[1] / v[0]) for m, v in sorted(acc.items())}


def signals(mon, m_from=M0):
    """(HighMS, Signal, T2) — 확장 80 백분위(그달 포함) · 36 개월 전엔 거짓."""
    ks = [m for m in sorted(mon) if m >= m_from]
    hi, sig, t2 = {}, {}, {}
    hist = []
    for m in ks:
        hist.append(mon[m][0])
        h = len(hist) >= NMIN_M and mon[m][0] >= float(np.percentile(hist, PCT))
        hi[m] = bool(h)
        sig[m] = bool(h and mon[m][1] > 1)
        t2[m] = bool(h and mon[m][1] <= 1)
    return hi, sig, t2


def _series(ctx, start=D0):
    key = ("S", id(ctx), start)
    if key in _CACHE:
        return _CACHE[key]
    A = ctx.A
    P = np.array([A.px[t] for t in SPDR]).T
    Y = np.full_like(P, np.nan)
    Y[1:] = P[1:] / P[:-1] - 1
    i_st = A.dates.index(start) if start in A.di else next(i for i, d in enumerate(A.dates) if d >= start)
    i_first = max(i_st + WMIN, A.dates.index(S0))
    i_last = A.me[ctx.Wd.months[-1]]
    assert not np.isnan(Y[i_st:i_last + 1]).any(), "SPDR 수익 결측"
    sc = scores(Y, i_st, i_first, i_last)
    mon = monthly(A, sc)
    out = (sc, mon)
    _CACHE[key] = out
    return out


def states(ctx):
    """편입월 m → 1(OFFENSE) · 0(DEFENSE) · 쌍둥이 T1 · T2 · 기록."""
    sc, mon = _series(ctx)
    hi, sig, t2 = signals(mon)
    months = ctx.Wd.months
    st = {m: (0 if sig.get(m) else 1) for m in months}
    s1 = {m: (0 if hi.get(m) else 1) for m in months}
    s2 = {m: (0 if t2.get(m) else 1) for m in months}
    return st, s1, s2, mon, sig


# ── 계약 ─────────────────────────────────────────────────────────────────
def selftest():
    """합성 — Σ 가 대각이면 CS ≡ 1(식 tms · 창 경로 scores 둘 다) · 상관 깨진 날은 CS > 1 · 창은 t−1 까지 · 월 가중 CS · 백분위 신호 · 교체 틀."""
    global WMIN, WMAX
    rng = np.random.default_rng(Q.SEED)
    tests = {}
    n = 9
    # ① 대각 Σ — 무작위 e 200 개 · 무작위 분산
    ok = True
    for _ in range(200):
        sd = rng.uniform(0.2, 3.0, n)
        cs = tms(rng.normal(0, 1, n) * sd * rng.uniform(0.1, 5.0), np.diag(sd ** 2))[2]
        ok &= abs(cs - 1) < 1e-12
    tests["cs_one_diag"] = bool(ok)
    # ② 창 경로 — 주기 16 푸리에 열(서로 직교 · 창 평균 0)이면 16일 창마다 표본 Σ 가 대각 → scores 의 CS 가 모든 날 1
    tt = np.arange(96)
    cols = [f(2 * np.pi * k * tt / 16) for k in (1, 2, 3, 4) for f in (np.cos, np.sin)] + [np.cos(2 * np.pi * 5 * tt / 16)]
    Yd = np.column_stack(cols) * np.linspace(0.005, 0.03, n)
    old = (WMIN, WMAX)
    try:
        WMIN, WMAX = 16, 16
        sc = scores(Yd, 0, 16, len(tt) - 1)
        tests["cs_one_diag_scores_path"] = bool(len(sc) == len(tt) - 16 and max(abs(v[2] - 1) for v in sc.values()) < 1e-9)
        # 그날 값은 창에 들지 않는다 — 마지막 날을 바꿔도 그 전 날 점수는 그대로
        Yr = rng.normal(0, 0.01, (80, n))
        WMIN, WMAX = 20, 40
        s1 = scores(Yr, 0, 20, 79)
        Yr2 = Yr.copy(); Yr2[79] += 0.05
        s2 = scores(Yr2, 0, 20, 79)
        tests["window_excludes_t"] = bool(all(s1[t] == s2[t] for t in s1 if t < 79) and s1[79] != s2[79]
                                          and min(s1) == 20 and len(s1) == 60)
    finally:
        WMIN, WMAX = old
    C = np.full((n, n), 0.8) + 0.2 * np.eye(n)
    e2 = np.r_[np.ones(4), -np.ones(5)]                  # 평소 같이 움직이는데 갈라진 날
    tests["cs_gt1_decorrelation"] = bool(tms(e2, C)[2] > 1)
    e3 = np.ones(n)                                      # 모두 같이 움직인 날
    tests["cs_lt1_typical"] = bool(tms(e3, C)[2] < 1)

    class _A:
        dates = ["2020-01-02", "2020-01-03", "2020-02-03"]
    mon = monthly(_A, {0: (2.0, 1.0, 2.0), 1: (1.0, 3.0, 1 / 3), 2: (1.0, 1.0, 1.0)})
    tests["month_cs_weighted"] = bool(abs(mon["2020-01"][1] - (2.0 * 1.0 + (1 / 3) * 3.0) / 4.0) < 1e-12 and abs(mon["2020-01"][0] - 2.0) < 1e-12)
    mm = {"%04d-%02d" % (2009 + k // 12, k % 12 + 1): (float(k % 10), 1.5) for k in range(48)}
    hi, sig, t2 = signals(mm)
    tests["pct_signal"] = bool(not any(hi[m] for m in sorted(mm)[:35]) and any(sig.values()) and not any(t2.values()))
    tests["switch_frame"] = SW.selftest()["ok"]
    return {"ok": all(bool(v) for v in tests.values()), "tests": tests}


def dry(ctx):
    """구성만 — 점수 날 수 · 월 수 · 신호 달 수 · 쌍둥이 달 수 · F0 · 개편 뒤 기록 · 부분 표본 신호 달. 수익 없음."""
    st, s1, s2, mon, sig = states(ctx)
    sc, _ = _series(ctx)
    A = ctx.A
    F = SW.frame(ctx)
    n_sig = sum(1 for m in ctx.Wd.months if st[m] == 0)
    for t in sc:                                          # 점수 t 는 t−1 까지의 창 · 월 신호는 그달 마지막 거래일까지
        assert A.dates[t] >= S0
    last = {}
    for t in sc:
        last[A.dates[t][:7]] = max(t, last.get(A.dates[t][:7], -1))
    for m in ctx.Wd.months:                               # 결정 m 의 MonthMS · CS 는 그달 마지막 거래일 종가에서 닫힌다 · 두 격자의 월말이 같다
        assert last[m] == A.me[m] and A.dates[A.me[m]] == ctx.Wd.dates[ctx.Wd.me[m]] and A.dates[A.me[m] + 1][:7] != m
    _sub, mon_sub = _series(ctx, SUB0)
    _h, sig_sub, _t = signals(mon_sub, SUB0[:7])
    return {"n_score_days": len(sc), "n_months": len(mon), "n_signal_months": n_sig,
            "n_T1_months": sum(1 for m in ctx.Wd.months if s1[m] == 0), "n_T2_months": sum(1 for m in ctx.Wd.months if s2[m] == 0),
            "f0": {"ok": n_sig >= F0_MIN, "why": "신호 달 %d(≥ %d)" % (n_sig, F0_MIN)},
            "sub_2018_10_signal_months": [m for m, v in sig_sub.items() if v and m in set(ctx.Wd.months)],
            "e_bar": float(SW.pos_from_monthly(F, st).mean())}


def run(ctx):
    """한 번 굽기 — Q06 CardResult(측정만)."""
    import q_bmrot_leg as BL
    F = SW.frame(ctx)
    st, s1, s2, mon, sig = states(ctx)
    pos = SW.pos_from_monthly(F, st)
    bO, bD, bT = SW.offense_v0(ctx), SW.defense(ctx), SW.tbill_book(ctx)
    n_sig = int((np.array([st[m] for m in F.months]) == 0).sum())
    tw = {"T1_highMS": SW.pos_from_monthly(F, s1), "T2_highMS_cs_le1": SW.pos_from_monthly(F, s2)}
    arms = {"tbill": SW.switch_fr(ctx, pos, bO, bT)}
    brk = {b: {m: [round(mon[m][0], 5), round(mon[m][1], 5)] for m in Q.months_between(b, Q.mshift(b, 5)) if m in mon} for b in BREAKS}
    _sub, mon_sub = _series(ctx, SUB0)
    _h, sig_sub, _t = signals(mon_sub, SUB0[:7])
    _T, _ = BL.targets(ctx.Wd)
    f0 = {"ok": bool(n_sig >= F0_MIN), "why": "신호 달 %d(≥ %d)" % (n_sig, F0_MIN)}
    res, twr, plac = SW.class_s(ctx, "Q06", "M", None, pos, bO, bD, NPERM, unit="month", months_state=st, twins=tw, arms=arms, f0=f0,
                                extra_log={"signal_months": [m for m in F.months if st[m] == 0], "gics_breaks": brk,
                                           "sub_2018_10": {"signal_months": [m for m, v in sig_sub.items() if v],
                                                           "monthly": {m: [round(v[0], 5), round(v[1], 5)] for m, v in mon_sub.items()}},
                                           "monthly_ms_cs": {m: [round(v[0], 5), round(v[1], 5)] for m, v in mon.items() if m >= "2016-01"},
                                           "interpretation": INTERP},
                                targets_hash_src={"v0": BL.thash(ctx.V0_targets), "bmrot": BL.thash(_T)})
    res["log"]["placebo_rank"] = SW.pct_rank(plac["down_dD"]["draws"], plac["down_dD"]["true"])
    # 카드의 측정 행(판정 아님) — 러너는 부류 M 에 평균 X 만 내므로 여기서 싣는다: Δ^D 전 월 · 하락월 · 규칙 − T1 · T2 · 순열 p · 위약 백분위
    res["log"]["measured"] = SW.measured_rows(res, F.dmask())
    res["g4"] = {}
    res["label_caps"] = {"측정만(부류 M)": True}
    return {"Q06": res}


INTERP = ["Σ = 표본 공분산(ddof 1) · 창 = [max(2006-01-04, t − 2520), t − 1] 거래일 · 752 < 756 이면 점수 없음",
          "80 백분위 = np.percentile(선형 보간) · 그달 값을 포함한 확장 표본 · «≥»",
          "부분 표본(2018-10 이후 자료만)은 신호 기록만 싣는다 — 팔로 굽지 않는다(카드는 «MS/CS 와 부분 표본을 보고» 만 적었다)",
          "GICS 개편 뒤 6개월 = 개편 달 포함 6개월의 MonthMS · MonthCS",
          "측정만이라 g4 는 비우고 순열 · 위약 백분위는 기록으로만 낸다",
          "측정 행은 log.measured(Δ^D 전 월 · 하락월 평균과 NW t · down_t · 규칙 − T1 · 규칙 − T2 전 월 · 하락월 · 순열 p · 위약 백분위) — 판정에 쓰지 않는다"]


if __name__ == "__main__":
    import time
    t0 = time.time()
    print(json.dumps(selftest(), ensure_ascii=False, default=str))
    if "--dry" in sys.argv:
        ctx = Q.Ctx()
        print(json.dumps(dry(ctx), ensure_ascii=False, default=str))
    print("%.0f초" % (time.time() - t0))
