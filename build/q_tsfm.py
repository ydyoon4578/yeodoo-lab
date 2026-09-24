# -*- coding: utf-8 -*-
"""build/q_tsfm.py — 배치 Q 카드 Q04 Q-TSFM12 · 팩터 ETF 시계열 모멘텀(베타 조정 12개월 초과 부호 · 칸 고정 1/4 · 진 칸은 SPY).

근본 이유: 팩터 수익은 한 달로 끝나지 않고 몇 달에서 1년 가까이 이어진다(Ehsani·Linnainmaa 2019 — 지난 1년이 플러스였던 팩터의
다음 달 수익 51bp, 마이너스였던 팩터 6bp). 투자심리와 느린 자본 이동이 만든 괴리가 천천히 되돌아오고, 최근 잘한 팩터로 롱 자금이
뒤늦게 몰리기 때문이다. 롱온리 ETF 에서 팩터 몫만 재려면 시장 베타 몫을 빼야 한다 — USMV(β≈0.7)를 그대로 SPY 와 견주면
«약세장 뒤 저베타 ETF 가 저절로 켜지는» 절대 모멘텀 재포장이 된다. 그래서 신호는 «ETF 초과 − β̂ × SPY 초과» 의 12개월 합이고,
양인 칸만 팩터를 들고 음인 칸은 지수(SPY)로 돌린다(패자의 이후 프리미엄은 0 근처라 진 칸을 SPY 로 두어도 잃는 것이 없다).

규칙(사전등록 카드 원문 — scratchpad/qbatch_final.md «# Q04»):
  자산 QUAL · SIZE · USMV · VLUE(iShares MSCI USA 단일 팩터 · MTUM 제외) · 바탕 SPY
  월말 m(2016-08 ~ 2026-07): e_i,k = A.monthly(i,k) − rf_k · β̂_i,m = e_i 를 e_SPY 에 OLS 회귀한 기울기(m−35..m · 36개)
    S_i(m) = Σ_{k=m−11..m}(e_i,k − β̂_i,m · e_SPY,k)(m 포함 · 건너뜀 없음)
  비중 w_i = 1/4 (S_i > 0) · 아니면 0 · SPY = 1 − Σw_i · 현금 · 레버리지 · 공매도 없음 · 매달 전체 목표 · 편도 10bp
  G4 (a) 노출 맞춘 대조 f̄·EW4 + (1 − f̄)·SPY(f̄ = 규칙의 실현 평균 팩터 몫) — 규칙 − 대조 전 월 NW t ≥ 1.0
     (b) 개수 맞춘 무작위 위약 1000번(씨앗 SEED + i) — 전 월 평균 X ≥ 95 백분위
     (c) 재포장 상한 — 칸마다 «켜짐» 과 sign(SPY 12m − rf 12m) · sign(RSP − SPY 12m) 의 phi · 넘으면(|phi| > 0.8) 측정만
  측정만 팔: TSFM1(1개월 형성) · 날 부호(β 조정 없는 12개월 ETF − SPY) · 정적 EW4
출처: Ehsani & Linnainmaa(2019, NBER w25551 · 표 2/A2) · Falck·Rej·Thesmar · 랩 STYLE8ROT(434/435) · CGATE-mom · 182/59.

🚨 selftest · dry 는 규칙 · 대조 · 팔 · 위약의 수익을 계산하거나 찍지 않는다. run 은 한 번 굽기(러너)에서만 부른다.

  python build/q_tsfm.py --selftest
  python build/q_tsfm.py --dry
"""
from __future__ import annotations
import hashlib, json, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402

CARDS = {"Q04": {"cls": "A", "slot": "A2"}}
NPERM = 1000                           # 개수 맞춘 무작위 위약 — 연기 시험에서 작게 덮어쓴다
FAC = ("QUAL", "SIZE", "USMV", "VLUE")   # 알파벳 고정(순회 순서)
BASE, EQW = "SPY", "RSP"
BWIN, FWIN = 36, 12                    # β 창 36개월 · 형성 12개월
SLOT = 0.25                            # 칸 고정 1/4
PHI_CAP = 0.8
T_CTRL = 1.0
PCT = 95
COST20 = 0.0020
KINDS = ("beta12", "beta1", "raw12")   # 주 규칙 · TSFM1 · 날 부호
INTERP = [
    "f̄ = 120 편입의 목표 팩터 몫(Σw_i) 평균 — 매달 목표로 되돌리므로 편입 때 실현 몫과 같다(흘러간 몫은 쓰지 않는다).",
    "β̂ = 절편 있는 OLS 기울기(cov/var · 36개월 m−35..m) — 날 부호 팔도 같은 창을 계산하지만 쓰지 않는다.",
    "날 부호 팔(b) = 주 규칙 식에서 β ≡ 1: Σ_{m−11..m}(e_i − e_SPY) = Σ(r_i − r_SPY) (월 합 — 12개월 복리 차가 아니다). "
    "카드 '(unadjusted)' 는 주 규칙에서 β 조정만 뺀 판이라는 뜻으로 읽었다 — 팔이 재려는 것이 β 조정 하나의 효과라서 합산 방식은 주 규칙과 같게 둔다(카드 수정 필요: 문구로 박기).",
    "phi 상한: SPY 12m · RSP 12m = me[m−12] → me[m] 수정종가 복리 · rf 12m = rf_monthly m−11..m 복리 · 켜짐 = 1(> 0) / 0. "
    "이 둘은 랩의 기존 신호(182 절대 모멘텀 · RSP−SPY 12m = CGATE 축)를 재현하는 바깥 기준이라 표준 12개월 복리로 두고, 날 부호 팔의 월 합과 일부러 다르다.",
    "phi 는 |phi| > 0.8 로 읽었다(카드 '넘으면') — 카드가 겨눈 USMV 재포장(약세 뒤 켜짐 = TSMOM 과 반대)은 음의 phi, SIZE 재포장(RSP−SPY 와 같은 편)은 양의 phi 로 "
    "나타나고 비판 원문은 둘 다를 겨눈다. 부호 있는 판(phi > 0.8)은 log['phi_cap_signed'] 에 보고만(카드 수정 필요: '|phi| > 0.8(부호 무관)' 로 박기).",
    "phi 가 정의되지 않으면(한쪽 계열이 상수) 상한을 걸지 않고 log 에 None 으로 적는다.",
    "위약: 편입마다 규칙의 켜진 칸 수 n_m 만큼 4개 중 무작위(비복원 · np.random.default_rng(SEED + i)) · 고른 칸 1/4 · 나머지 SPY.",
    "위약 관문: 참값 ≥ np.percentile(draws, 95)(선형 보간 · '이상' — q_qmj · q_eap · q_riegk · q_ltd · q_netper · q_season 과 같다). "
    "q_switch.pct_rank(참값보다 작은 뽑기의 백분율) 판은 log['placebo_pct_rank'] 에 보고만.",
    "정적 EW4 = 네 ETF 1/4 씩 매달 되돌림(10bp) — 측정만 팔.",
    "한계(발표 지연): rf_monthly[k] 는 그달 일별 DGS3MO 의 월평균이라 me[m] 날짜의 금리(FRED 는 다음 영업일에 싣는다)를 약 1/21 무게로 품는다. "
    "S 에는 (1 − β̂)·Σrf 로만 들어가 영향은 약 1e-6 — 카드가 rf_monthly 를 적었으므로 고치지 않고 알린다(phi 의 rf 12m 도 같다).",
    "PYTHONHASHSEED: qbatch_core.etf_path 가 매매액을 문자열 집합 순서로 더해 경로가 마지막 비트에서 갈릴 수 있다 — 굽기 때 값은 log['hashseed'].",
]


# ── 신호 ─────────────────────────────────────────────────────────────────
class Sig:
    """월말 m 의 칸별 β̂ · S — m 월말 종가까지만 쓴다(단언)."""

    def __init__(self, A):
        self.A = A
        self._e = {}

    def ex(self, tk, k):
        """달 k 의 초과 수익 e = A.monthly − rf_k."""
        key = (tk, k)
        if key not in self._e:
            r = self.A.monthly(tk, k)
            if r is None:
                raise RuntimeError("%s 가 %s 에 월 수익이 없다" % (tk, k))
            if k not in self.A.RF:
                raise RuntimeError("rf_monthly 에 %s 가 없다" % k)
            self._e[key] = r - float(self.A.RF[k])
        return self._e[key]

    def window(self, m):
        ks = [Q.mshift(m, -j) for j in range(BWIN - 1, -1, -1)]      # m−35 .. m
        im = self.A.me[m]
        for k in ks:                                                  # PIT: 쓰는 종가는 me[k−1] · me[k] ≤ me[m]
            assert k <= m and self.A.me[k] <= im and self.A.me[Q.mshift(k, -1)] < im
        return ks

    def at(self, m, kind="beta12"):
        ks = self.window(m)
        es = np.array([self.ex(BASE, k) for k in ks])
        out = {}
        for tk in FAC:
            ei = np.array([self.ex(tk, k) for k in ks])
            b = ols_slope(ei, es)
            if kind == "beta12":
                s = float(np.sum(ei[-FWIN:] - b * es[-FWIN:]))
            elif kind == "beta1":
                s = float(ei[-1] - b * es[-1])
            elif kind == "raw12":
                s = float(np.sum(ei[-FWIN:] - es[-FWIN:]))
            else:
                raise ValueError(kind)
            out[tk] = {"S": s, "beta": b, "n": len(ks)}
        return out

    def states(self, m):
        """재포장 기준 — sign(SPY 12m − rf 12m) · sign(RSP − SPY 12m) (m 월말까지)."""
        A = self.A
        i0, i1 = A.me[Q.mshift(m, -12)], A.me[m]
        spy, rsp = A.ret(BASE, i0, i1), A.ret(EQW, i0, i1)
        if spy is None or rsp is None:
            raise RuntimeError("%s 12개월 SPY/RSP 가 없다" % m)
        rf = float(np.prod([1 + float(A.RF[Q.mshift(m, -j)]) for j in range(FWIN)]) - 1)
        return {"tsmom": int(spy - rf > 0), "ewcw": int(rsp - spy > 0)}


def ols_slope(y, x):
    y, x = np.asarray(y, float), np.asarray(x, float)
    xc = x - x.mean()
    v = float(xc @ xc)
    if v <= 0:
        raise RuntimeError("β 창의 SPY 초과 분산이 0")
    return float(xc @ (y - y.mean()) / v)


def weights_on(on):
    """켜진 칸 목록 → 목표(칸 1/4 · 나머지 SPY)."""
    on = sorted(on)
    w = {tk: SLOT for tk in on}
    w[BASE] = 1.0 - SLOT * len(on)
    return w


def weights_from(sig):
    return weights_on([tk for tk in FAC if sig[tk]["S"] > 0])


def expo_weights(fbar):
    w = {tk: fbar / len(FAC) for tk in FAC}
    w[BASE] = 1.0 - fbar
    return w


def phi(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def count_draw(nwin, forms, i):
    """개수 맞춘 무작위 한 번 — 편입 순서대로 n_m 개를 비복원으로."""
    rng = np.random.default_rng(Q.SEED + i)
    out = {}
    for m in forms:
        pick = rng.choice(len(FAC), size=nwin[m], replace=False)
        out[m] = weights_on([FAC[j] for j in pick])
    return out


def thash(T):
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def _check_w(w):
    s = sum(w.values())
    assert abs(s - 1.0) < 1e-12, s
    assert all(-1e-15 <= x <= 1 + 1e-15 for x in w.values())
    assert set(w) <= set(FAC) | {BASE}
    return s


def build(A, forms):
    """세 신호의 목표 경로 · 켜진 칸 수 · 재포장 상태(구성만 — 수익 없음)."""
    S = Sig(A)
    sig = {k: {m: S.at(m, k) for m in forms} for k in KINDS}
    T = {k: {m: weights_from(sig[k][m]) for m in forms} for k in KINDS}
    nwin = {m: sum(1 for tk in FAC if sig["beta12"][m][tk]["S"] > 0) for m in forms}
    st = {m: S.states(m) for m in forms}
    return sig, T, nwin, st


def phi_table(sig, st, forms):
    tab = {}
    for tk in FAC:
        on = [int(sig[m][tk]["S"] > 0) for m in forms]
        tab[tk] = {ref: phi(on, [st[m][ref] for m in forms]) for ref in ("tsmom", "ewcw")}
    return tab


# ── 계약 함수 ─────────────────────────────────────────────────────────────
def dry(ctx) -> dict:
    """랩 자료로 구성만 — 커버리지 · β 창 개수 · 비중 합 · 한도 · PIT · 위약 개수 맞춤. 수익 · 신호 분포 · 켜진 칸 수는 찍지 않는다."""
    A = ctx.A
    forms = Q.monthly_forms()
    assert len(forms) == 120 and forms[0] == "2016-08" and forms[-1] == "2026-07"
    for m in forms + [Q.mshift(forms[-1], 1)]:                        # 월말 자리 = 그달 마지막 거래일
        i = A.me[m]
        assert A.dates[i][:7] == m and A.dates[i + 1][:7] > m
    sig, T, nwin, st = build(A, forms)
    nobs = sorted({sig[k][m][tk]["n"] for k in KINDS for m in forms for tk in FAC})
    dev = 0.0
    for k in KINDS:
        for m in forms:
            dev = max(dev, abs(_check_w(T[k][m]) - 1.0))
    for fb in (0.0, 0.5, 1.0):
        _check_w(expo_weights(fb))
    for i in range(2):                                               # 위약 두 번 — 칸 수가 규칙과 같은지만
        Tp = count_draw(nwin, forms, i)
        for m in forms:
            _check_w(Tp[m])
            assert sum(1 for tk in FAC if tk in Tp[m]) == nwin[m]
    first = Sig(A).window(forms[0])
    cov = {tk: all(A.px[tk][A.me[Q.mshift(m, -BWIN)]] == A.px[tk][A.me[Q.mshift(m, -BWIN)]] for m in forms) for tk in FAC + (BASE, EQW)}
    return {"n_forms": len(forms), "tickers": list(FAC) + [BASE, EQW], "coverage_36m_all": all(cov.values()),
            "beta_window_obs": nobs, "first_beta_window": "%s..%s" % (first[0], first[-1]),
            "w_sum_max_dev": dev, "w_in_0_1": True, "pit_asserts": "ok (종가 ≤ me[m] · rf 달 ≤ m)",
            "phi_pairs": len(FAC) * 2, "placebo_count_match": "ok (2 draws)"}


def run(ctx) -> dict:
    import eg30plus as E
    A = ctx.A
    forms = Q.monthly_forms()
    sig, T, nwin, st = build(A, forms)
    dec = lambda TT: (lambda m: dict(TT[m]))
    prim = T["beta12"]
    fr = ctx.etf_fr(dec(prim), forms, "TR", Q.COST)
    fr_pr = ctx.etf_fr(dec(prim), forms, "PR", Q.COST)
    fr20 = ctx.etf_fr(dec(prim), forms, "TR", COST20)
    fbar = float(np.mean([SLOT * nwin[m] for m in forms]))
    ctrl = ctx.etf_fr(lambda m: expo_weights(fbar), forms, "TR", Q.COST)
    arms = {"TSFM1": ctx.etf_fr(dec(T["beta1"]), forms, "TR", Q.COST),
            "RAW12": ctx.etf_fr(dec(T["raw12"]), forms, "TR", Q.COST),
            "EW4": ctx.etf_fr(lambda m: {tk: 1.0 / len(FAC) for tk in FAC}, forms, "TR", Q.COST)}
    draws = []
    for i in range(NPERM):
        Tp = count_draw(nwin, forms, i)
        draws.append(float(np.mean(ctx.etf_fr(dec(Tp), forms, "TR", Q.COST)["ex"])))
    true = float(np.mean(fr["ex"]))
    p95 = float(np.percentile(draws, PCT))
    t_ctrl = E.nw_t(np.asarray(fr["ex"]) - np.asarray(ctrl["ex"]))
    ptab = phi_table(sig["beta12"], st, forms)
    cap_abs = any(v is not None and abs(v) > PHI_CAP for r in ptab.values() for v in r.values())
    cap_sgn = any(v is not None and v > PHI_CAP for r in ptab.values() for v in r.values())
    wc = {str(n): sum(1 for m in forms if nwin[m] == n) for n in range(len(FAC) + 1)}
    per = {m: {"n": nwin[m], "beta": {tk: sig["beta12"][m][tk]["beta"] for tk in FAC},
               "S": {tk: sig["beta12"][m][tk]["S"] for tk in FAC}} for m in forms}
    res = {"code": "Q04", "cls": "A", "slot": "A2",
           "fr": fr, "fr_pr": fr_pr, "fr20": fr20,
           "controls": {"EXPO": ctrl},
           "arms": arms,
           "placebo": {"count_matched": {"stat": "전 월 평균 X(펀드 TR · 10bp · %/월) — 편입마다 규칙과 같은 개수를 무작위로(1/4 씩 · 나머지 SPY)",
                                         "draws": draws, "true": true}},
           "g4": {"expo_ctrl_nw_t_ge_1": bool(t_ctrl is not None and t_ctrl >= T_CTRL),
                  "count_placebo_ge_p95": bool(true >= p95)},
           "label_caps": {"phi": bool(cap_abs)},
           "f0": {"ok": True, "why": "카드에 F0 없음 — 4 ETF · SPY · RSP 가 120 편입 모두 36개월 창을 채운다(단언)"},
           "targets_hash": thash(prim),
           "log": {"interpretation": INTERP, "fbar": fbar, "winner_counts": wc, "share_100spy": wc["0"] / len(forms),
                   "turn": {"rule": fr.get("turn"), "rule20": fr20.get("turn"), "expo": ctrl.get("turn")},
                   "phi": ptab, "phi_cap_signed": bool(cap_sgn), "phi_cap_abs": bool(cap_abs),
                   "expo_nw_t": t_ctrl, "placebo_p95": p95, "placebo_pct_rank": float(np.mean(np.asarray(draws, float) < true) * 100),
                   "nperm": NPERM, "seed": Q.SEED, "hashseed": os.environ.get("PYTHONHASHSEED"),
                   "arm_hashes": {k: thash(T[k]) for k in ("beta1", "raw12")},
                   "per_formation": per}}
    return {"Q04": res}


# ── 단위 시험(합성 자료만) ─────────────────────────────────────────────────
def _fake_assets(monthly, rf=0.001, nd=20, y0=2006, y1=2026, m1=9):
    """합성 격자 — monthly = {티커: {달: 월 수익}} 를 달 안에서 기하 균등으로 펼친 가격. qbatch_core.Assets 의 메서드를 그대로 쓴다."""
    months = [m for m in Q.months_between("%04d-01" % y0, "%04d-%02d" % (y1, m1))]
    dates = ["%s-%02d" % (m, d + 1) for m in months for d in range(nd)]
    A = object.__new__(Q.Assets)
    A.dates = dates
    A.di = {d: i for i, d in enumerate(dates)}
    A.me = {m: (j + 1) * nd - 1 for j, m in enumerate(months)}
    A.RF = {m: rf for m in months}
    A.px = {}
    for tk, mm in monthly.items():
        p, v = [], 100.0
        for j, m in enumerate(months):
            r = mm.get(m, 0.0) if j > 0 else 0.0
            g = (1 + r) ** (1.0 / nd)
            for d in range(nd):
                if j > 0:
                    v *= g
                p.append(v)
        A.px[tk] = np.array(p)
    A.IX_TR = A.px[BASE].copy()
    A.IX_PR = A.px[BASE].copy()
    A.macro = {}
    return A, months


def selftest() -> dict:
    tests = {}
    rng = np.random.default_rng(7)
    months = Q.months_between("2006-01", "2026-09")
    es = {m: float(rng.normal(0.006, 0.04)) for m in months}
    for m in Q.months_between("2019-01", "2019-12"):                  # 날 부호 시험 — 2019 한 해 시장 급락
        es[m] = -0.05
    rf = 0.001
    # 계획된 α: QUAL +1%/월 · VLUE −1%/월 · USMV −0.01%/월(β 0.7) · SIZE β 1.1 + 잡음
    mk = lambda a, b, noise=0.0: {m: rf + a + b * es[m] + (float(rng.normal(0, noise)) if noise else 0.0) for m in months}
    ret = {"SPY": {m: rf + es[m] for m in months}, "QUAL": mk(0.01, 0.9), "VLUE": mk(-0.01, 1.2), "USMV": mk(-0.0001, 0.7),
           "SIZE": mk(0.0, 1.1, 0.01), "RSP": mk(0.0, 1.0, 0.005)}
    A, _ = _fake_assets(ret, rf=rf)
    S = Sig(A)
    s1 = S.at("2019-12", "beta12")
    tests["beta_recovered"] = abs(s1["QUAL"]["beta"] - 0.9) < 1e-9 and abs(s1["USMV"]["beta"] - 0.7) < 1e-9
    tests["S_planted_alpha"] = (abs(s1["QUAL"]["S"] - 0.12) < 1e-9 and abs(s1["VLUE"]["S"] + 0.12) < 1e-9
                                and abs(s1["USMV"]["S"] + 0.0012) < 1e-9)
    w = weights_from(s1)
    tests["weights_slots"] = ({k: w[k] for k in ("QUAL", "SPY")} == {"QUAL": 0.25, "SPY": 0.75 - 0.25 * (s1["SIZE"]["S"] > 0)}
                              and "VLUE" not in w and "USMV" not in w)
    raw = S.at("2019-12", "raw12")
    tests["raw_sign_is_market_timing"] = raw["USMV"]["S"] > 0 and s1["USMV"]["S"] < 0     # 베타 조정이 절대 모멘텀 재포장을 끈다
    b1 = S.at("2019-12", "beta1")
    tests["tsfm1_one_month"] = abs(b1["QUAL"]["S"] - 0.01) < 1e-9
    tests["weights_sum"] = all(abs(sum(weights_on(list(FAC[:n])).values()) - 1) < 1e-15 for n in range(5))
    tests["all_on_no_spy_line"] = weights_on(list(FAC))[BASE] == 0.0
    # 앞보기 막기 — m 뒤 가격을 바꿔도 신호가 같다
    A2, _ = _fake_assets(ret, rf=rf)
    for tk in A2.px:
        A2.px[tk][A2.me["2019-12"] + 1:] *= np.linspace(1, 2, len(A2.px[tk]) - A2.me["2019-12"] - 1)
    tests["no_lookahead"] = Sig(A2).at("2019-12") == s1 and Sig(A2).at("2020-06") != S.at("2020-06")   # 뒤는 실제로 바뀌었다
    # PIT 단언 — 창 끝은 m 자신
    tests["window_36_ends_m"] = (lambda ks: len(ks) == 36 and ks[-1] == "2019-12" and ks[0] == "2017-01")(S.window("2019-12"))
    # phi
    tests["phi_identity"] = abs(phi([0, 1, 1, 0], [0, 1, 1, 0]) - 1) < 1e-12 and abs(phi([0, 1, 1, 0], [1, 0, 0, 1]) + 1) < 1e-12
    tests["phi_constant_none"] = phi([1, 1, 1], [0, 1, 0]) is None
    st = S.states("2019-12")
    tests["states_tsmom_down"] = st["tsmom"] == 0
    # 개수 맞춘 위약 — 개수 · 재현 · 씨앗 차
    forms = Q.monthly_forms()
    nwin = {m: (j % 5) for j, m in enumerate(forms)}
    d0, d0b, d1 = count_draw(nwin, forms, 0), count_draw(nwin, forms, 0), count_draw(nwin, forms, 1)
    tests["placebo_count_match"] = all(sum(1 for tk in FAC if tk in d0[m]) == nwin[m] for m in forms)
    tests["placebo_reproducible"] = d0 == d0b and d0 != d1
    tests["expo_weights"] = abs(sum(expo_weights(0.37).values()) - 1) < 1e-12 and abs(expo_weights(0.37)["QUAL"] - 0.0925) < 1e-12
    tests["hash_stable"] = thash({"b": {"x": 1.0}, "a": {"y": 0.5}}) == thash({"a": {"y": 0.5}, "b": {"x": 1.0}})
    # 끝까지 — 합성 ctx 로 run(수익은 합성 · 모양만 본다)
    global NPERM
    old = NPERM
    NPERM = 3
    try:
        ctx = Q.Ctx()
        ctx._A = A
        out = run(ctx)["Q04"]
        tests["run_synthetic_shape"] = (len(out["placebo"]["count_matched"]["draws"]) == 3 and len(out["fr"]["ex"]) == 120
                                        and set(out["g4"]) == {"expo_ctrl_nw_t_ge_1", "count_placebo_ge_p95"}
                                        and isinstance(out["label_caps"]["phi"], bool) and len(out["targets_hash"]) == 64
                                        and out["fr"]["hold"][0] == "2016-09" and out["fr"]["hold"][-1] == "2026-08")
        tests["run_caps_g4_all_bool"] = all(type(v) is bool for d in (out["label_caps"], out["g4"]) for v in d.values())
        tests["run_log_pct_rank"] = 0.0 <= out["log"]["placebo_pct_rank"] <= 100.0 and "hashseed" in out["log"]
    finally:
        NPERM = old
    return {"ok": all(bool(v) for v in tests.values()), "tests": tests}


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0 if r["ok"] else 1)
    if "--dry" in sys.argv:
        print(json.dumps(dry(Q.Ctx()), ensure_ascii=False, indent=1))
        sys.exit(0)
    print(__doc__)
