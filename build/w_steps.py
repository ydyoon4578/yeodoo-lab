# -*- coding: utf-8 -*-
"""build/w_steps.py — 배치 W 스텝 셋(W01 C 책 위 Δ 로만 보고 · 갱신 나 — 오케스트레이터 결정): S3e 베팅 부 θ · S2 비용 인지 조준(무거래 규칙) · S1 4앵커 트랜치.

설계 원본(구속): wbatch_research.json final.slate.steps(S1 · S2 · S3e) · step_order_W01 · build_plan.guards.identity · D14 · D15.
  명세 build_plan 은 스텝을 «w_book.py» 에 두었다 — 과제 지시(등록 A 카드 단계)에 따라 build/w_steps.py 로 짓는다(내용은 명세 그대로).
  사용자 갱신(2026-09-27): 전방 원장이 없다 → S3e 의 «언제나-유효 e-값» 은 표본 안 보고로만 싣고 날짜 박힌 전방 판정을 만들지 않는다.
  스텝 순서(명세 step_order_W01): WF01S(θ0 정적) → C(+교차항) → +S3e → +S2 → +S1 · 각 Δ 따로(섞지 않고 한 단계씩).

S3e 기량 보정 θ — 베팅 부(wealth)로 약하면 지수로 돌아간다
  근본 이유: 고정된 큰 능동 베팅은 과신이다(M6 — 163팀 중 IR 로 벤치를 이긴 팀 28.8% · 12개월 내내 이긴 팀 0). 신호의 실현 표본 밖 적중을 공정한 베팅으로
    누적하면, 귀무(죽은 신호)에서 부가 음이 아닌 초마팅게일이라 시간이 지나며 줄고 살아 있으면 유지된다(Ville 부등식) — 이론 없는 혼합 상수를 없앤다.
  규칙: W_t = Π_{s≤t}(1 + λ·clip(IC_s, −c, c)/c) · λ 0.25 · c 0.20 · IC_s = 그 카드의 실현 표본 밖 월 순위 IC(결정 t 에는 IC_{t−1} 까지) ·
    θ_t = θ0·min(1, W_{t−1}) · 한 달 |Δθ| ≤ 0.10 · W 는 언제나-유효 e-값으로도 보고.
  정직: 잡음이 크다(60개월 뒤 평균 θ — 죽은 신호 0.52 · IC 0.012 인 신호 0.69 · θ0 0.75 [명세 합성]) · V-A(자기 모멘텀)와 기전이 겹친다(선언) ·
    랩 TWOHEADS(과거 성과로 고르기 워크포워드 부호 뒤집힘)는 반대 근거.
S2 비용 인지 조준 — 앞을 겨누고 수익이 비용을 넘는 거래만
  근본 이유: 비용은 거래 크기에 붙고 신호마다 붕괴 속도가 다르다. 빨리 붕괴하는 성분은 덜 따라가고 느린 성분은 앞서 겨누면 비용이 알파보다 더 크게 준다
    (Gârleanu–Pedersen 2013 · Jensen–Kelly–Malamud–Pedersen 2026 · DeMiguel 외 2020).
  규칙: ŝ*_t = Σ_{h=0..2} ω_h ŝ_{t−h} · ω_h ∝ max(0, 학습창 시차 h 순위 IC) 합 1 · 모두 ≤ 0 이면 (1, 0, 0) · 해마다 8월 갱신 ·
    무거래 규칙(차원 고침 D14): 이름 i 는 |α̂_i|·H > 2c_i 일 때만 거래 — α̂_i = IC_0·σ_CS·z*_i(IC_0 = ½·IC_lit · σ_CS = 학습창 월 단면 수익 SD) ·
    H = 학습창 시차 IC 감쇠 IC_h = IC_0·φ^h 적합의 반감기 ln2/(−ln φ) · [1, 12] 로 자름 · c = 편도 10bp · 그 뒤 V 의 ½ 체결.
S1 리밸런스 타이밍 운 제거 — 4앵커 트랜치
  근본 이유: 기대수익은 리밸런스 날짜와 무관한데 실현 경로는 날짜에 달려 있다. 날짜를 나누면 평균은 그대로 두고 날짜 잡음의 분산만 준다(대수의 법칙).
  규칙: 자본 4등분 · 앵커 = 월말 · +5 · +10 · +15 거래일 · 각 트랜치는 자기 앵커에서 월 1회 같은 규칙 · 앵커 날짜의 편입 명단은 «그 날 이전 마지막 월말 명단» ·
    재무 가용일 규칙은 날마다 · 우주 탈락은 각 트랜치 앵커에서 처리(앵커 목표 함수의 몫) · Tier-2 주 행은 단일 앵커(월말) · S1 은 Δ 로만.

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  P1 S3e 첫 결정의 θ 는 θ0(W_0 = 1) · IC 가 없는 달(결측)은 곱하지 않는다(인자 1) · 단계 상한은 직전 θ 대비(첫 달 앞 θ = θ0).
  P2 S2 시차 점수 ŝ_{t−h} 가 없는 이름은 0(중립 z) · ω 는 8월 결정에서 그 결정까지 라벨이 선 학습쌍(라벨 달 ≤ t)으로 다시 잰다 · 첫 8월 앞은 (1, 0, 0).
  P3 S2 반감기 적합: h = 0..5 의 학습창 평균 시차 IC 에 IC_0·φ^h 를 최소제곱(φ ∈ [1e−6, 1 − 1e−6] 황금분할 탐색) · 시차 IC 가 없으면 H = 1.
  P4 S2 무거래 이름은 흘러간 비중을 목표로 둔다 · 목표 0(우주 탈락)은 규칙과 무관하게 판다 · 거래 가능 이름의 목표를 비례로 맞춰 합 1 · 그 뒤
     frozen v_core.execute_book(½ 체결 · 틈 < 0.1·목표 무거래) — 거래 가능 이름이 없으면 흘러간 책 그대로(거래 0).
  P5 S1 트랜치는 NAV 로 따로 흘러가고 합친 책 = 트랜치 NAV 가중 합 · 앵커 k 의 날짜 = 그달 마지막 거래일 + k 거래일(다음 달로 넘어가면 그 날) ·
     트랜치 체결 = frozen v_core.execute_book(같은 ½ 체결 · 띠) · 비용 = 편도 비율 × Σ|Δw| × 트랜치 몫 · 월 수익 = 월말 NAV 비.

🚨 랩 규율 — 이 모듈의 공개 함수는 수익을 받는 곳(S3e 의 IC · S2 의 시차 IC · S1 의 일간 수익)이 있다. 등록 커밋 전에는 합성 · 눈가림 자료만 넘긴다
   (kind 인자 · w_core.assert_kind_allowed). --selftest 는 합성 자료만.

  python build/w_steps.py --selftest
"""
from __future__ import annotations

import math
import os
import sys
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import w_core as WC          # noqa: E402
import w_guard as WG         # noqa: E402

# ── 명세 상수(지금 고정) ──────────────────────────────────────────────────
S3E_LAMBDA, S3E_C = 0.25, 0.20
S3E_STEP = 0.10
S2_LAGS = (0, 1, 2)
S2_UPDATE_MONTH = "08"
S2_COST = 0.0010                     # 편도 10bp
S2_H_CLIP = (1.0, 12.0)
S2_DECAY_LAGS = 6                    # P3 — h = 0..5
S1_OFFSETS = (0, 5, 10, 15)          # 월말 · +5 · +10 · +15 거래일
FILL, BAND_FRAC = 0.5, 0.1           # V 의 ½ 체결 · 틈 < 0.1·목표 무거래(frozen v_core 와 같은 값 — selftest 가 대조)

STEP_UNITS = [WG.unit("ic_realized", source="w_stagem.rank_ic", concept="realized out-of-sample rank IC of the card score", use="step"),
              WG.unit("score_lag", source="card score", concept="lagged card score (aim)", use="step"),
              WG.unit("sigma_cs", source="panel y (training window)", concept="cross-sectional return SD", use="step"),
              WG.unit("daily_ret", source="data/pit_px.json", concept="daily total return (tranche drift)", use="step")]
WG.assert_units(STEP_UNITS, "w_steps 입력(모듈 적재)")


def _C():
    return WC.frozen("v_core")


# ══════════════════════════════════════════════════════════════════════════
#  S3e — 베팅 부 θ
# ══════════════════════════════════════════════════════════════════════════
def s3e_wealth(ic_by_month, months, lam=S3E_LAMBDA, c=S3E_C):
    """W_t = Π_{s≤t}(1 + λ·clip(IC_s, −c, c)/c) — months(결정 달 차례) · ic_by_month{결정 달 s: 실현 IC_s}(결측은 인자 1 · P1).
    돌려주는 것 {달: W_t}(그 달 IC 까지 곱한 부)."""
    if not (0 < lam < 1) or c <= 0:
        raise SystemExit("🚨 S3e λ ∈ (0, 1) · c > 0")
    W, out = 1.0, {}
    for m in months:
        ic = ic_by_month.get(m)
        if ic is not None and ic == ic:
            W *= 1.0 + lam * min(max(float(ic), -c), c) / c
        out[m] = W
    return out


def s3e_theta(ic_by_month, months, theta0, lam=S3E_LAMBDA, c=S3E_C, step=S3E_STEP):
    """θ_t = θ0·min(1, W_{t−1}) · |Δθ| ≤ step(직전 θ 대비 · 첫 앞 θ0). 결정 t 에는 IC_{t−1} 까지(W_{t−1}) — 선견 없음.
    돌려주는 것 {theta{달}, wealth{달}, e_value{달}(= W_t · 보고), e_max}."""
    W = s3e_wealth(ic_by_month, months, lam, c)
    th, prev, out = {}, float(theta0), None
    for j, m in enumerate(months):
        w_prev = W[months[j - 1]] if j > 0 else 1.0
        tgt = float(theta0) * min(1.0, w_prev)
        prev = prev + min(max(tgt - prev, -step), step)
        th[m] = prev
    ev = dict(W)
    out = {"theta": th, "wealth": W, "e_value": ev, "e_max": max(ev.values()) if ev else None,
           "rule": "W_t = Π(1 + %.2f·clip(IC, ±%.2f)/%.2f) · θ = θ0·min(1, W_{t−1}) · |Δθ| ≤ %.2f" % (lam, c, c, step)}
    return out


def s3e_shuffle(ic_by_month, months, theta0, n, seed):
    """θ 경로 섞기 위약(보고) — IC 순서를 씨앗으로 섞은 θ 경로 n 개 · 돌려주는 것 [{달: θ}]."""
    vals = [ic_by_month.get(m) for m in months]
    out = []
    for i in range(int(n)):
        rng = np.random.default_rng(seed + i)
        perm = rng.permutation(len(vals))
        out.append(s3e_theta({m: vals[p] for m, p in zip(months, perm)}, months, theta0)["theta"])
    return out


# ══════════════════════════════════════════════════════════════════════════
#  S2 — 비용 인지 조준
# ══════════════════════════════════════════════════════════════════════════
def s2_weights(lag_ic):
    """ω_h ∝ max(0, 시차 h 평균 순위 IC)(h = 0, 1, 2) · 합 1 · 모두 ≤ 0(또는 결측)이면 (1, 0, 0)."""
    v = np.array([max(0.0, float(lag_ic.get(h))) if (lag_ic.get(h) is not None and lag_ic.get(h) == lag_ic.get(h)) else 0.0 for h in S2_LAGS])
    if v.sum() <= 0:
        return {h: (1.0 if h == 0 else 0.0) for h in S2_LAGS}
    return {h: float(x / v.sum()) for h, x in zip(S2_LAGS, v)}


def s2_aim(scores, weights):
    """ŝ*_t = Σ_h ω_h ŝ_{t−h} — scores = [ŝ_t, ŝ_{t−1}, ŝ_{t−2}] 각각 {이름: z}(없는 이름 0 · P2) · 이름 = ŝ_t 의 이름."""
    base = scores[0]
    out = {}
    for k in base:
        out[k] = sum(weights[h] * float((scores[h] if h < len(scores) and scores[h] is not None else {}).get(k, 0.0) or 0.0) for h in S2_LAGS)
    return out


def half_life(lag_ic, ic0, lags=S2_DECAY_LAGS):
    """P3 — IC_h ≈ ic0·φ^h(h = 0..lags−1) 최소제곱 φ → H = ln2/(−ln φ) · [1, 12]. 돌려주는 것 {H, phi, n}."""
    hs = [h for h in range(lags) if lag_ic.get(h) is not None and lag_ic.get(h) == lag_ic.get(h)]
    if not hs or not ic0 or ic0 <= 0:
        return {"H": S2_H_CLIP[0], "phi": None, "n": len(hs)}
    y = np.array([float(lag_ic[h]) for h in hs])
    hh = np.array(hs, float)

    def sse(phi):
        return float(((y - ic0 * phi ** hh) ** 2).sum())
    a, b = 1e-6, 1.0 - 1e-6
    g = (math.sqrt(5) - 1) / 2
    x1, x2 = b - g * (b - a), a + g * (b - a)
    f1, f2 = sse(x1), sse(x2)
    for _ in range(200):
        if f1 <= f2:
            b, x2, f2 = x2, x1, f1
            x1 = b - g * (b - a)
            f1 = sse(x1)
        else:
            a, x1, f1 = x1, x2, f2
            x2 = a + g * (b - a)
            f2 = sse(x2)
        if b - a < 1e-10:
            break
    phi = 0.5 * (a + b)
    H = math.log(2.0) / (-math.log(phi)) if 0 < phi < 1 else S2_H_CLIP[1]
    return {"H": float(min(max(H, S2_H_CLIP[0]), S2_H_CLIP[1])), "phi": float(phi), "n": len(hs)}


def s2_tradable(zstar, ic0, sigma_cs, H, cost=S2_COST):
    """무거래 규칙(D14) — 이름 i 는 |α̂_i|·H > 2c 일 때만 거래(α̂_i = IC_0·σ_CS·z*_i). 돌려주는 것 {이름: bool}."""
    thr = 2.0 * float(cost)
    return {k: (abs(float(ic0) * float(sigma_cs) * float(z)) * float(H) > thr) if (z is not None and z == z) else False
            for k, z in zstar.items()}


def s2_execute(w_drift, target, tradable, fill=FILL, band_frac=BAND_FRAC):
    """P4 — 무거래 이름은 흘러간 비중을 목표로 · 목표 0(우주 탈락)은 판다 · 거래 가능 이름 목표를 비례로 맞춰 합 1 → frozen v_core.execute_book.
    돌려주는 것 (체결 책, 거래량 Σ|Δw|, 정보)."""
    names = set(w_drift) | set(target)
    frozen_all = {k: float(w_drift.get(k, 0.0)) for k in names if float(target.get(k, 0.0)) > 0 and not tradable.get(k, False)}
    frozen_w = {k: v for k, v in frozen_all.items() if v > 0}          # 무거래 새 이름(흘러간 비중 0)은 사지 않는다
    trad = {k: float(target[k]) for k in target if float(target[k]) > 0 and tradable.get(k, False)}
    left = 1.0 - sum(frozen_w.values())
    if not trad or left <= 0 or sum(trad.values()) <= 0:
        tot = sum(v for v in w_drift.values() if v > 0)
        book = {k: v / tot for k, v in w_drift.items() if v > 0 and float(target.get(k, 0.0)) > 0} if tot > 0 else dict(w_drift)
        s = sum(book.values())
        book = {k: v / s for k, v in book.items()} if s > 0 else book
        traded = sum(abs(book.get(k, 0.0) - float(w_drift.get(k, 0.0))) for k in names)
        return book, traded, {"n_frozen": len(frozen_w), "n_trad": 0, "fallback": True}
    sc = left / sum(trad.values())
    tgt2 = dict(frozen_w)
    tgt2.update({k: v * sc for k, v in trad.items()})
    book, traded = _C().execute_book(w_drift, tgt2, fill=fill, band_frac=band_frac)
    return book, traded, {"n_frozen": len(frozen_w), "n_trad": len(trad), "fallback": False}


def s2_schedule(months, lag_ic_by_update, ic_lit, sigma_by_update):
    """8월 갱신표 — lag_ic_by_update{8월 결정 달: {h: 평균 시차 IC}} · sigma_by_update{8월 결정 달: σ_CS} →
    {결정 달: {omega, H, ic0, sigma_cs, updated_at}}(첫 8월 앞은 ω = (1, 0, 0) · H = 1 · σ 없음 = 거래 규칙 끔 표시)."""
    ic0 = 0.5 * float(ic_lit)
    cur = {"omega": s2_weights({}), "H": S2_H_CLIP[0], "ic0": ic0, "sigma_cs": None, "updated_at": None}
    out = {}
    for m in months:
        if m[5:7] == S2_UPDATE_MONTH and m in lag_ic_by_update:
            li = lag_ic_by_update[m]
            cur = {"omega": s2_weights(li), "H": half_life(li, ic0)["H"], "ic0": ic0, "sigma_cs": sigma_by_update.get(m), "updated_at": m}
        out[m] = dict(cur)
    return out


def lag_ic_table(kind, months, score_of, y_of, lags=S2_DECAY_LAGS):
    """학습창 시차 IC — 결정 달 s 의 점수 ŝ_s 와 라벨 r_{s+1+h}(= 결정 s+h 의 y) 의 순위 IC 를 달마다 · 돌려주는 것 {h: [(s, IC)]}.
    score_of(m) · y_of(m) → {이름: 값}. 🚨 수익 — kind 자물쇠."""
    WC.assert_kind_allowed(kind, "w_steps.lag_ic_table")
    import w_stagem as S
    out = {h: [] for h in range(lags)}
    for s in months:
        sc = score_of(s)
        if not sc:
            continue
        for h in range(lags):
            y = y_of(WC.mshift(s, h))
            if not y:
                continue
            ks = [k for k in sc if k in y and y[k] is not None and sc[k] is not None]
            if len(ks) < 10:
                continue
            ic = S.rank_ic(np.array([sc[k] for k in ks], float), np.array([y[k] for k in ks], float))
            if ic is not None:
                out[h].append((s, ic))
    return out


def lag_ic_asof(table, t):
    """8월 결정 t 의 학습창 평균 시차 IC — 라벨 달(s + 1 + h) ≤ t 인 쌍만(선견 없음)."""
    res = {}
    for h, rows in table.items():
        v = [ic for s, ic in rows if WC.mshift(s, 1 + h) <= t]
        res[h] = float(np.mean(v)) if v else None
    return res


# ══════════════════════════════════════════════════════════════════════════
#  S1 — 4앵커 트랜치
# ══════════════════════════════════════════════════════════════════════════
def anchor_days(month_end_idx, n_days, offsets=S1_OFFSETS):
    """앵커 날짜 색인 — month_end_idx = 월말 거래일 색인(차례) · 앵커 k = 월말 + k 거래일(격자 밖이면 버린다). 돌려주는 것 {오프셋: [(월 순번, 날 색인)]}."""
    out = {}
    for k in offsets:
        out[k] = [(j, i + k) for j, i in enumerate(month_end_idx) if i + k < n_days]
    return out


def tranche_path(kind, n_days, month_end_idx, target_at, day_ret, offsets=S1_OFFSETS, fill=FILL, band_frac=BAND_FRAC, rate=S2_COST):
    """S1 트랜치 경로(P5) — target_at(오프셋, 월 순번, 날 색인) → 목표 책{이름: 비중}(명단은 «그 날 이전 마지막 월말 명단» — 목표 함수의 몫) ·
    day_ret(날 색인) → {이름: 그날 수익}(없는 이름은 0 수익으로 흘러가지 않고 그대로) · 첫 앵커 전 트랜치는 현금 없이 첫 목표에서 시작한다.
    돌려주는 것 {nav[날], month_ret[월 순번 → 수익](월말 대 월말), traded[월 순번 → Σ 트랜치 몫 × Σ|Δw|], cost[월 순번], books_last}.
    🚨 수익 계열 — kind 자물쇠."""
    WC.assert_kind_allowed(kind, "w_steps.tranche_path")
    k_n = len(offsets)
    anchors = anchor_days(month_end_idx, n_days, offsets)
    at = {}
    for k, rows in anchors.items():
        for j, i in rows:
            at.setdefault(i, []).append((k, j))
    first = min(i for rows in anchors.values() for _, i in rows) if anchors else n_days
    nav_t = {k: 1.0 / k_n for k in offsets}
    book = {k: None for k in offsets}
    nav = np.full(n_days, np.nan)
    trade_by_m, cost_by_m = {}, {}
    me_pos = {i: j for j, i in enumerate(month_end_idx)}
    for d in range(first, n_days):
        if d > first:
            r = day_ret(d)
            for k in offsets:
                b = book[k]
                if not b:
                    continue
                g = sum(w * (1.0 + float(r.get(n, 0.0) or 0.0)) for n, w in b.items())
                if g > 0:
                    book[k] = {n: w * (1.0 + float(r.get(n, 0.0) or 0.0)) / g for n, w in b.items()}
                    nav_t[k] *= g
        for k, j in at.get(d, []):
            T = target_at(k, j, d)
            if T is None:
                continue
            if book[k] is None:
                book[k] = dict(T)
                continue
            newb, tr = _C().execute_book(book[k], T, fill=fill, band_frac=band_frac)
            c = rate * tr
            nav_t[k] *= (1.0 - c)
            book[k] = newb
            mj = j
            trade_by_m[mj] = trade_by_m.get(mj, 0.0) + tr * nav_t[k] / max(sum(nav_t.values()), 1e-300)
            cost_by_m[mj] = cost_by_m.get(mj, 0.0) + c * nav_t[k] / max(sum(nav_t.values()), 1e-300)
        nav[d] = sum(nav_t[k] for k in offsets if book[k] is not None) + sum(nav_t[k] for k in offsets if book[k] is None)
    mret = {}
    for j in range(1, len(month_end_idx)):
        a, b = month_end_idx[j - 1], month_end_idx[j]
        if a >= first and b < n_days and np.isfinite(nav[a]) and np.isfinite(nav[b]):
            mret[j] = float(nav[b] / nav[a] - 1.0)
    return {"nav": nav, "month_ret": mret, "traded": trade_by_m, "cost": cost_by_m, "books_last": book, "offsets": tuple(offsets),
            "first_day": first, "me_pos": me_pos}


def luck_report(x_by_anchor):
    """단일 앵커 판들의 연 X 흩어짐(명세 S1 report) — x_by_anchor{오프셋: [월 X]} → {ann{오프셋}, sd, range}."""
    ann = {k: float(np.mean(v) * 12) for k, v in x_by_anchor.items() if len(v)}
    vals = np.array(list(ann.values()), float)
    return {"ann": ann, "sd": float(vals.std(ddof=1)) if len(vals) > 1 else None,
            "range": float(vals.max() - vals.min()) if len(vals) else None}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 자료만)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _st_s3e():
    ms = WC.months_between("2016-08", "2026-07")
    # 항등(명세 guards.identity): IC ≡ 0 → W ≡ 1 → θ = θ0
    r0 = s3e_theta({m: 0.0 for m in ms}, ms, 0.75)
    assert all(abs(v - 0.75) < 1e-15 for v in r0["theta"].values()) and all(v == 1.0 for v in r0["wealth"].values())
    # 결정 t 에는 IC_{t−1} 까지 — t 의 IC 를 바꿔도 θ_t 는 그대로(선견 없음)
    rng = np.random.default_rng(WC.SEED)
    ic = {m: float(rng.normal(0.0, 0.08)) for m in ms}
    a = s3e_theta(ic, ms, 0.75)
    icn = {m: -0.01 for m in ms}                                 # W < 1 인 길(θ 가 min(1, ·) 에 묶이지 않게)
    icn2 = dict(icn)
    icn2[ms[50]] = -0.9
    an, bn = s3e_theta(icn, ms, 0.75), s3e_theta(icn2, ms, 0.75)
    assert an["theta"][ms[50]] == bn["theta"][ms[50]] and an["theta"][ms[51]] != bn["theta"][ms[51]]
    assert an["wealth"][ms[49]] == bn["wealth"][ms[49]] and an["wealth"][ms[50]] != bn["wealth"][ms[50]]
    # 단계 상한
    th = [a["theta"][m] for m in ms]
    assert max(abs(x - y) for x, y in zip(th[1:], th[:-1])) <= S3E_STEP + 1e-12 and abs(th[0] - 0.75) <= S3E_STEP + 1e-12
    assert all(0.0 <= x <= 0.75 + 1e-12 for x in th)
    # 귀무(대칭 · 평균 0 IC)에서 부는 마팅게일(E[W_T] = 1) · 평균 IC ≤ 0 이면 초마팅게일 · Ville: P(sup W ≥ 1/α) ≤ α
    n_path, T = 20000, 120
    Z = rng.normal(0.0, 0.08, (n_path, T))
    fac = 1.0 + S3E_LAMBDA * np.clip(Z, -S3E_C, S3E_C) / S3E_C
    Wp = np.cumprod(fac, axis=1)
    mean_WT = float(Wp[:, -1].mean())
    assert abs(mean_WT - 1.0) < 0.03, mean_WT
    Zn = rng.normal(-0.01, 0.08, (n_path, T))
    Wn = np.cumprod(1.0 + S3E_LAMBDA * np.clip(Zn, -S3E_C, S3E_C) / S3E_C, axis=1)
    assert float(Wn[:, -1].mean()) < 1.0
    for alpha in (0.05, 0.10):
        p_sup = float(np.mean(Wp.max(axis=1) >= 1.0 / alpha))
        assert p_sup <= alpha, (alpha, p_sup)
    # 살아 있는 신호(IC 0.012)는 죽은 신호보다 60개월 뒤 평균 θ 가 높다(명세 정직 칸 보고 — 수치는 보고만)
    def mean_theta60(mu, reps=4000):
        acc = []
        m60 = ms[:61]
        for i in range(reps):
            r = np.random.default_rng(WC.SEED + 10 + i).normal(mu, 0.08, 61)
            acc.append(s3e_theta({m: float(v) for m, v in zip(m60, r)}, m60, 0.75)["theta"][m60[-1]])
        return float(np.mean(acc))
    dead, alive = mean_theta60(0.0, 1500), mean_theta60(0.012, 1500)
    assert dead < alive < 0.75, (dead, alive)
    sh = s3e_shuffle(ic, ms, 0.75, 3, WC.SEED)
    assert len(sh) == 3 and all(len(x) == len(ms) for x in sh)
    assert _raises(lambda: s3e_wealth(ic, ms, lam=1.5))
    return "항등(IC≡0 → θ0) · 선견 없음(IC_{t−1}) · |Δθ| ≤ 0.10 · 귀무 E[W_T] = %.3f · 초마팅게일 · Ville(α 0.05 · 0.10) · 60개월 평균 θ 죽은 %.2f < 산 %.2f" % (
        mean_WT, dead, alive)


def _st_s2():
    # 명세 selftest: IC_0 0.006 · σ_CS 0.08 · H 3 에서 거래 가능 몫 ≈ 0.16 · 5~95% 안
    rng = np.random.default_rng(WC.SEED + 1)
    z = {("n%d" % i): float(v) for i, v in enumerate(rng.normal(0, 1, 20000))}
    tr = s2_tradable(z, 0.006, 0.08, 3.0)
    share = float(np.mean(list(tr.values())))
    from scipy.stats import norm
    exact = 2 * (1 - norm.cdf(0.002 / (0.006 * 0.08 * 3.0)))
    assert 0.05 <= share <= 0.95 and abs(share - exact) < 0.01 and abs(exact - 0.16) < 0.01, (share, exact)
    # 옛 공식(|Δw| < c/α̂ 이면 무거래)은 띠가 비중보다 커서 아무것도 거래하지 않는다(명세 D14 · 합성)
    alpha = {k: 0.006 * 0.08 * v for k, v in z.items()}
    dw = np.abs(rng.normal(0, 0.002, len(z)))
    old_trade = np.mean([abs(d) >= 0.001 / max(abs(a), 1e-300) for d, a in zip(dw, alpha.values())])
    assert old_trade < 0.001, old_trade
    # ω · 반감기
    assert s2_weights({0: -0.1, 1: -0.2, 2: None}) == {0: 1.0, 1: 0.0, 2: 0.0}
    w = s2_weights({0: 0.02, 1: 0.01, 2: -0.01})
    assert abs(w[0] - 2 / 3) < 1e-12 and abs(w[1] - 1 / 3) < 1e-12 and w[2] == 0.0
    hl = half_life({h: 0.006 * 0.7 ** h for h in range(6)}, 0.006)
    assert abs(hl["phi"] - 0.7) < 1e-6 and abs(hl["H"] - math.log(2) / -math.log(0.7)) < 1e-4
    assert half_life({h: 0.006 * 0.99 ** h for h in range(6)}, 0.006)["H"] == 12.0
    assert half_life({h: 0.0 for h in range(6)}, 0.006)["H"] == 1.0 and half_life({}, 0.006)["H"] == 1.0
    aim = s2_aim([{"a": 1.0, "b": -1.0}, {"a": 0.5}, None], {0: 0.5, 1: 0.5, 2: 0.0})
    assert aim == {"a": 0.75, "b": -0.5}
    # 체결: c = 0(모두 거래 가능)이면 frozen execute_book 과 같다(항등) · 무거래 이름은 흘러간 비중 · 목표 0 은 판다
    C = _C()
    assert C.FILL == FILL and C.BAND_FRAC == BAND_FRAC
    wd = {"a": 0.3, "b": 0.3, "c": 0.4}
    T = {"a": 0.5, "b": 0.2, "d": 0.3}
    b1, t1, _ = s2_execute(wd, T, {k: True for k in "abcd"})
    b0, t0 = C.execute_book(wd, T, fill=FILL, band_frac=BAND_FRAC)
    assert all(abs(b1.get(k, 0) - b0.get(k, 0)) < 1e-15 for k in "abcd") and abs(t1 - t0) < 1e-15
    b2, t2, inf = s2_execute(wd, T, {"a": False, "b": True, "d": True})
    # a 는 흘러간 0.3 을 목표로(틈 0 → 무거래) · b 는 목표 0.28(틈 < 0.1·목표 → 무거래 0.3) · d 는 ½ 체결 0.21 · c 는 판다 → 합 0.81 로 비례 맞춤
    assert abs(b2["a"] - 0.3 / 0.81) < 1e-12 and abs(b2["d"] - 0.21 / 0.81) < 1e-12 and "c" not in b2 and inf["n_frozen"] == 1
    assert abs(sum(b2.values()) - 1.0) < 1e-12
    b3, t3, inf3 = s2_execute(wd, T, {})
    assert inf3["fallback"] and "c" not in b3 and "d" not in b3 and abs(b3["a"] - 0.5) < 1e-12 and abs(sum(b3.values()) - 1) < 1e-12
    # 8월 갱신 · 선견 없는 시차 IC
    ms = WC.months_between("2015-01", "2018-12")
    sch = s2_schedule(ms, {"2016-08": {0: 0.02, 1: 0.01, 2: 0.0, 3: 0.0}, "2017-08": {0: 0.01}}, 0.012, {"2016-08": 0.08})
    assert sch["2016-07"]["updated_at"] is None and sch["2016-08"]["updated_at"] == "2016-08" and sch["2017-07"]["updated_at"] == "2016-08"
    assert sch["2017-08"]["omega"] == {0: 1.0, 1: 0.0, 2: 0.0} and abs(sch["2016-08"]["ic0"] - 0.006) < 1e-15
    tab = {0: [("2016-06", 0.1), ("2016-07", 0.2)], 1: [("2016-06", 0.3), ("2016-07", 0.4)]}
    li = lag_ic_asof(tab, "2016-08")
    assert abs(li[0] - 0.15) < 1e-15 and li[1] == 0.3                      # (2016-07, h 1) 의 라벨 달 2016-09 > t → 뺀다
    ys = {m: {("n%d" % i): float(v) for i, v in enumerate(np.random.default_rng(i0).normal(0, 1, 50))} for i0, m in enumerate(ms)}
    sc = {m: {k: v + 0.0 for k, v in ys[WC.mshift(m, 0)].items()} for m in ms}
    lt = lag_ic_table("synth", ms[:-6], lambda m: sc[m], lambda m: ys.get(m), lags=3)
    assert all(abs(ic - 1.0) < 1e-12 for _, ic in lt[0])       # 점수 = 라벨(합성) → 시차 0 IC = 1
    assert _raises(lambda: lag_ic_table("real", ms, lambda m: sc[m], lambda m: ys.get(m)))
    return "거래 가능 몫 %.3f(명세 0.16) · 옛 공식 얼어붙음(%.4f) · ω · 반감기(φ 복원 · 자름) · 조준 · 체결 항등(c=0 = execute_book) · 무거래 · 8월 갱신 · 선견 없는 시차 IC" % (
        share, old_trade)


def _st_s1():
    rng = np.random.default_rng(WC.SEED + 2)
    n_days, names = 800, ["n%d" % i for i in range(30)]
    me_idx = list(range(20, n_days, 21))
    R = rng.normal(0.0003, 0.015, (n_days, len(names)))
    tgt_seed = {}

    def target_at(k, j, d):                                    # 달마다 바뀌는 목표(앵커와 무관한 규칙 — 같은 규칙)
        if j not in tgt_seed:
            v = np.random.default_rng(WC.SEED + 100 + j).dirichlet(np.ones(len(names)) * 2.0)
            tgt_seed[j] = {n: float(x) for n, x in zip(names, v)}
        return tgt_seed[j]

    def day_ret(d):
        return {n: float(R[d, i]) for i, n in enumerate(names)}
    one = tranche_path("synth", n_days, me_idx, target_at, day_ret, offsets=(0,))
    # 항등(명세 guards.identity): 앵커 하나면 단일 월간 책 경로와 같다 — 손으로 푼 단일 책
    C = _C()
    book, nav, first = None, 1.0, me_idx[0]
    navs = np.full(n_days, np.nan)
    for d in range(first, n_days):
        if d > first and book:
            r = day_ret(d)
            g = sum(w * (1 + r[n]) for n, w in book.items())
            book = {n: w * (1 + r[n]) / g for n, w in book.items()}
            nav *= g
        if d in me_idx:
            T = target_at(0, me_idx.index(d), d)
            if book is None:
                book = dict(T)
            else:
                book, tr = C.execute_book(book, T, fill=FILL, band_frac=BAND_FRAC)
                nav *= 1 - S2_COST * tr
        navs[d] = nav
    ok = np.isfinite(navs) & np.isfinite(one["nav"])
    assert np.allclose(navs[ok], one["nav"][ok], rtol=0, atol=1e-12)
    four = tranche_path("synth", n_days, me_idx, target_at, day_ret)
    # 트랜치 회전 ≈ 단일 월간 책 회전(명세 report · 합성) — 연 회전 비 0.8~1.25
    t1 = float(np.mean(list(one["traded"].values())))
    t4 = float(np.mean(list(four["traded"].values())))
    assert 0.8 < t4 / t1 < 1.25, (t1, t4)
    assert len(four["month_ret"]) >= len(me_idx) - 3
    lr = luck_report({0: [0.001, 0.002], 5: [0.0, 0.001], 10: [0.002, 0.002], 15: [-0.001, 0.0]})
    assert abs(lr["range"] - 12 * 0.0025) < 1e-12 and lr["sd"] > 0
    assert _raises(lambda: tranche_path("real", n_days, me_idx, target_at, day_ret))
    ad = anchor_days([10, 30], 40)
    assert ad[15] == [(0, 25)] and ad[0] == [(0, 10), (1, 30)]
    return "앵커 하나 = 단일 책(1e−12 · 손풀이) · 4앵커 회전 비 %.2f · 앵커 날짜 · 흩어짐 보고 · 실자료 자물쇠" % (t4 / t1)


def _st_static():
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    mods = set()
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Import):
            mods |= {a.name.split(".")[0] for a in nd.names}
        elif isinstance(nd, ast.ImportFrom) and nd.module:
            mods.add(nd.module.split(".")[0])
    assert not [m for m in mods if WG.forbidden(m)], mods
    assert not WG.check_units(STEP_UNITS) and not WG.literal_scan(os.path.abspath(__file__))
    return "금지 import 없음 · 입력 단위 · 문자열 상수"


def selftest():
    res, ok = [], True
    for fn in (_st_s3e, _st_s2, _st_s1, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-10s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_steps selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
