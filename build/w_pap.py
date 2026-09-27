# -*- coding: utf-8 -*-
"""build/w_pap.py — 배치 W 카드 W03 PAP(섹터 주성분 알파 포트 · 교차 예측 행렬의 반대칭부) — 측정만(채택 경로 없음 · D17 · D30 · U5).

설계 원본(구속): wbatch_research.json final.slate.strategies[W03] · build_plan.modules[w_pp](과제 지시로 이 파일 이름) · D17 · D30 · U5 ·
  사용자 규칙 2026-09-27 «백테스트 최대 기간은 최근 20년» — 내부 L 쌍둥이(French 49 산업)의 평가 달은 보유월 ≥ 2006-09 로 자른다(w_core.trim_window).

근본 이유(명세 fundamental_reason): 경제적으로 연결된 산업 사이에서 정보가 천천히, 그리고 한쪽 방향으로 퍼진다. 예측 행렬 Π 의 반대칭부가
  «i 의 신호가 j 를 예측하지만 반대는 아니다» 라는 선후행 비대칭 그 자체다. 랩의 INDMOM · RRG · SECROT 는 모두 대각(자기 신호)만 썼다 — 비대각이 랩에 없는 축이다.
출처: Kelly · Malamud · Pedersen (2023 JF) «Principal Portfolios»(NBER w27388) [본문] — 선두 PEP + PAP 가 같은 신호의 표준 요인 샤프를 두 배 넘게 ·
  기본 표본에서 유의한 것은 첫 두 PP · PEP 와 첫 PAP. 🔎 KMP §2 PAP 식 번호는 등록 전 원문에서 옮긴다(open_before_register).

규칙(명세 base · 지금 고정 · 초모수 없음)
  자산 = PIT GICS 11 섹터 VW(합집합 · 분할만 조정 ME · 총수익 · 금융 포함) · 월간(원문 20일 일간에서 이탈 공개).
  신호 S_t = 자기 지난 1개월 수익의 단면 순위 표준화([−0.5, 0.5]).
  Π̂_t = (1/60) Σ_{τ=t−60}^{t−1} R̃_{τ+1} S_τ′ · R̃ = 창 평균을 뺀 수익(중심화 — 2014-06 앞 역적용 명단의 생존편향 드리프트가 R̄·S̄′ 로 새는 것을 막는다 ·
    KMP 원식에서 이탈 공개) · 60개월(2009 자료 제약 · 원문 120 에서 이탈) · 수축 없음.
  주 팔 = PAP 1~3 동일가중(Π_a = (Π − Π′)/2 의 고유쌍) · PEP 는 대각(섹터 모멘텀)을 품어 쌍둥이로 내린다.
  슬리브: 섹터 능동 a_g ∝ PAP 포지션 · Σ|a_g| = 0.20 · 섹터 안은 벤치 비중 비례 배수(롱온리) · 섹터 띠 ±0.15(이 카드만) · β 띠 ±0.03 · 월간 · 10bp.
  C 팔 없음(VIX 고저로 Π 를 나누면 표본이 반으로 준다 — 금지 · 국면별 차이는 보고만).
  주 통계: PAP 1~3 섹터 롱숏 월수익의 NW(6) t · H1 > 0(시계열). IC_lit: 연 SR_lit 0.70 가정 → P0 0.056 [합성 · 기록만].
  쌍둥이(보고만): PEP 1~3 + PAP 1~3(원문 결합) · 24 산업그룹판(위키 Sub-Industry PIT 파싱 빌드가 서면 — 없으면 F0 허용 결정으로 삭제) ·
    내부 L 쌍둥이 French 49 산업 월간(내부 층 · 원문 발표 뒤 2020-07~ 만 청정 표시 · 보유월 ≥ 2006-09).
  대조: 대각만 판(표준 섹터 모멘텀 L = I) · Π 비대각 섞기 위약(S 열 라벨 섞기 1,000회) · 섹터 1/N · 시장.
  위험(등록문에 적는다): N 11 · W 60 이면 Π̂ 원소 신호 대 잡음 약 0.3 — 상위 고유값을 잡음이 지배할 공산 · 랩 섹터 로테이션은 모두 기각 · 섹터 띠 완화는 규칙 이탈.

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  A1 PAP 식: Π = E[R_{t+1} S_t′](행 = 수익 · 열 = 신호) · 포지션 행렬 L 의 수익 = S_t′ L R_{t+1} · 기대 = tr(L Π).
     Π_a 의 고유값 ±iμ_k(μ_k > 0 내림차순) · 단위 복소 고유벡터 v_k = x_k + i y_k(에르미트 iΠ_a 의 eigh — 음 고유값 −μ_k) · L_k = y_k x_k′ − x_k y_k′ →
     tr(L_k Π) = μ_k(대칭부 몫 0) · L_k 는 평면 안 회전 · 위상에 불변(부호 규칙이 필요 없다 — 명세 «W03 첫 원소 양» 은 PEP 고유벡터에만 건다).
     PAP_k 자산 비중 = L_k′ S_t · PAP 1~3 동일가중 = 셋의 평균. PEP_k: Π_s = (Π + Π′)/2 의 고유쌍(내림차순) · L = w_k w_k′ · 첫 원소 양.
  A2 자산 집합: 결정 t 의 창 60 쌍 모두에 수익 · 신호가 선 섹터만(11 섹터 가운데 Real Estate 는 2016-09 부터 — 창이 차기 전에는 뺀다) · N_t 가 바뀐다.
  A3 롱숏 월수익 = w_t′R_{t+1}(정규화 없음 — 순위 신호라 ‖S_t‖ 가 달마다 같아 규모가 일정) · 주 창 = 결정 2016-08 ~ 2026-07(S 창 · 보유 120).
  A4 섹터 능동: a = (w − 평균 w)(동일가중 중심화 — 완전 투자) → Σ|a| = 0.20 으로 척도 → 이름 비중 = w_B,i·(W_g + a_g)/W_g(롱온리 · 음이면 투영이 0 으로) →
     frozen v_core.project_active(발행사 0.05 · 섹터 띠 0.15 · NDX 전용 0.10) → frozen v_core.beta_band(±0.03 · 같은 투영).
  A5 섞기 위약: 씨앗 default_rng(seed + i) 로 섹터 열 차례를 한 번 섞어(모든 달 같은 치환) S 에 걸고 Π̂ · PAP 를 다시 · 위약 t 분포 · 관측 t 의 방향 쪽 백분위(보고).

🚨 랩 규율 — Π̂ · PAP 수익은 신호-수익 통계다. 공개 함수는 kind 를 받고 w_core.assert_kind_allowed 를 지난다(synth · blind 는 언제나 · real 은 등록 커밋 뒤).
   눈가림 연기는 섹터 수익 전체(신호의 원천 포함)를 씨앗 잡음으로 바꾼다. --selftest 는 합성 자료만.

  python build/w_pap.py --selftest
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

CARD = "W03"
WIN = 60
K_PAP = 3
GROSS = 0.20                 # Σ|a_g|
SBAND = 0.15                 # 이 카드만 섹터 띠 ±0.15
NW_LAG = 6
SR_LIT = 0.70
N_PLACEBO = 1000
CLEAN_FROM = "2020-07"       # 원문 발표 뒤(내부 L 쌍둥이 청정 표시)
EIG_TOL = 1e-12
DIRECTION = WC.CARD_DIRECTION[CARD]
assert DIRECTION == +1

PAP_UNITS = [WG.unit("sector_ret", source="data/pit_px.json + data/pit_gics_sectors.json", concept="PIT GICS sector VW total return", use="signal"),
             WG.unit("sector_mom1", source="data/pit_px.json", concept="own last 1-month sector return rank", use="signal"),
             WG.unit("ind49_ret", source="French 49_Industry_Portfolios(vw_m)", concept="industry VW return (internal L twin)", use="signal")]
WG.assert_units(PAP_UNITS, "w_pap 입력(모듈 적재)")


def _C():
    return WC.frozen("v_core")


# ══════════════════════════════════════════════════════════════════════════
#  신호 · Π̂ · 주성분 포트
# ══════════════════════════════════════════════════════════════════════════
def rank_signal(x):
    """단면 순위 → [−0.5, 0.5](동률 평균 · 결측 NaN 그대로). 이름 1 개면 0."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    ok = np.flatnonzero(np.isfinite(x))
    n = len(ok)
    if n == 0:
        return out
    if n == 1:
        out[ok] = 0.0
        return out
    v = x[ok]
    order = np.argsort(v, kind="stable")
    r = np.empty(n)
    r[order] = np.arange(n, dtype=float)
    u, inv = np.unique(v, return_inverse=True)
    if len(u) < n:
        r = (np.bincount(inv, weights=r) / np.bincount(inv))[inv]
    out[ok] = r / (n - 1) - 0.5
    return out


def pi_hat(R, S, j, win=WIN, center=True):
    """결정 j 의 Π̂ — R[τ] = 달 τ 의 자산 수익(T × N) · S[τ] = 결정 τ 의 신호(T × N) · 쌍 (S_τ, R_{τ+1}) τ = j−win..j−1(A2 — 창 안 모두 선 자산만).
    돌려주는 것 (Π̂(N_j × N_j), 쓴 자산 색인) · 창이 모자라면 (None, None)."""
    if j - win < 0:
        return None, None
    Sw = S[j - win:j]
    Rw = R[j - win + 1:j + 1]
    ok = np.isfinite(Sw).all(0) & np.isfinite(Rw).all(0) & np.isfinite(S[j])
    idx = np.flatnonzero(ok)
    if len(idx) < 3:
        return None, None
    Sw, Rw = Sw[:, idx], Rw[:, idx]
    if center:
        Rw = Rw - Rw.mean(0, keepdims=True)
    return (Rw.T @ Sw) / float(win), idx


def pap_parts(Pi, k=K_PAP):
    """A1 — Π_a 의 주 반대칭 포트 [(μ_k, L_k)](μ 내림차순 · 최대 k). 에르미트 iΠ_a 의 eigh(음 고유값 −μ)."""
    A = 0.5 * (Pi - Pi.T)
    lam, V = np.linalg.eigh(1j * A)
    out = []
    for i in np.argsort(lam):                         # 가장 음(μ 가장 큼)부터
        mu = -float(lam[i])
        if mu <= EIG_TOL:
            break
        v = V[:, i] / np.linalg.norm(V[:, i])
        x, y = v.real, v.imag
        out.append((mu, np.outer(y, x) - np.outer(x, y)))
        if len(out) >= k:
            break
    return out


def pep_parts(Pi, k=K_PAP):
    """PEP — Π_s 의 고유쌍 [(e_k, w_k w_k′)](고윳값 내림차순 · 첫 원소 양)."""
    Sm = 0.5 * (Pi + Pi.T)
    ev, V = np.linalg.eigh(Sm)
    out = []
    for i in np.argsort(-ev)[:k]:
        w = V[:, i]
        if w[0] < 0:
            w = -w
        out.append((float(ev[i]), np.outer(w, w)))
    return out


def positions(Pi, s_t, arm="pap", k=K_PAP):
    """자산 비중 벡터(결정 달) — arm: pap(PAP 1~k 평균) · pep_pap(PEP 1~k + PAP 1~k 평균 · 쌍둥이) · diag(L = I · 표준 섹터 모멘텀 대조)."""
    s_t = np.asarray(s_t, float)
    if arm == "diag":
        return s_t.copy()
    parts = pap_parts(Pi, k) if arm == "pap" else pap_parts(Pi, k) + pep_parts(Pi, k)
    if arm not in ("pap", "pep_pap"):
        raise KeyError(arm)
    if not parts:
        return np.zeros(len(s_t))
    return np.mean([L.T @ s_t for _, L in parts], axis=0)


def signals_from_returns(R):
    """S[τ] = rank_signal(R[τ]) — 자기 지난 1개월 수익(결정 달 τ 의 그달 수익)의 단면 순위 표준화."""
    return np.vstack([rank_signal(R[j]) for j in range(len(R))])


def ls_series(kind, months, R, arm="pap", win=WIN, perm=None, S=None):
    """롱숏 월수익 계열(A3) — months[j] = 달 j(R[j] = 그달 수익) · 결정 j 의 포지션 × R[j+1]. perm(열 치환)은 신호 열에만(A5).
    돌려주는 것 {dec[], ret[], n_assets[], mu1[]}(결정 달 · 다음 달 수익). 🚨 신호-수익 통계 — kind 자물쇠."""
    WC.assert_kind_allowed(kind, "w_pap.ls_series")
    R = np.asarray(R, float)
    S = signals_from_returns(R) if S is None else np.asarray(S, float)
    if perm is not None:
        S = S[:, perm]
    out = {"dec": [], "ret": [], "n_assets": [], "mu1": []}
    for j in range(win, len(months) - 1):
        Pi, idx = pi_hat(R, S, j, win)
        if Pi is None:
            continue
        r1 = R[j + 1, idx]
        if not np.isfinite(r1).all():
            continue
        w = positions(Pi, S[j, idx], arm)
        out["dec"].append(months[j])
        out["ret"].append(float(w @ r1))
        out["n_assets"].append(int(len(idx)))
        pp = pap_parts(Pi, 1)
        out["mu1"].append(pp[0][0] if pp else None)
    return out


def primary(kind, months, R, window=("2016-08", "2026-07"), arm="pap"):
    """주 통계 — 결정 window 안 롱숏 월수익의 NW(6) t · 방향 +1(w_stagem.summarize · 달력 틈 판)."""
    import w_stagem as S
    ls = ls_series(kind, months, R, arm)
    rows = [(m, r) for m, r in zip(ls["dec"], ls["ret"]) if window[0] <= m <= window[1]]
    sm = S.summarize([m for m, _ in rows], [r for _, r in rows], DIRECTION, lag=NW_LAG)
    return {"summary": sm, "n": len(rows), "arm": arm, "n_assets": sorted(set(ls["n_assets"]))}


def placebo(kind, months, R, n, seed, window=("2016-08", "2026-07")):
    """A5 — S 열 라벨 섞기 위약 n 회(모든 달 같은 치환) · 돌려주는 것 {t[], n, seed}. 🚨 kind 자물쇠."""
    import w_stagem as S
    WC.assert_kind_allowed(kind, "w_pap.placebo")
    if not isinstance(n, int) or n < 1:
        raise SystemExit("🚨 n 은 명시 정수")
    R = np.asarray(R, float)
    S0 = signals_from_returns(R)
    ts = []
    for i in range(n):
        perm = np.random.default_rng(seed + i).permutation(R.shape[1])
        ls = ls_series(kind, months, R, "pap", perm=perm, S=S0)
        rows = [(m, r) for m, r in zip(ls["dec"], ls["ret"]) if window[0] <= m <= window[1]]
        sm = S.summarize([m for m, _ in rows], [r for _, r in rows], DIRECTION, lag=NW_LAG)
        ts.append(sm["nw_t"] if sm["nw_t"] is not None else float("nan"))
    return {"t": np.array(ts, float), "n": n, "seed": seed, "scheme": "S 열 라벨 섞기(모든 달 같은 치환)"}


# ══════════════════════════════════════════════════════════════════════════
#  슬리브 책(A4) · 섹터 수익 빌드 · 내부 L 쌍둥이
# ══════════════════════════════════════════════════════════════════════════
def sector_active(w_sec, gross=GROSS):
    """섹터 능동 a = (w − 평균 w) 척도 Σ|a| = gross(완전 투자) · 모두 0 이면 0."""
    w = np.asarray(w_sec, float)
    a = w - w.mean()
    s = float(np.abs(a).sum())
    return a * (gross / s) if s > 0 else np.zeros_like(a)


def pap_book(a_sec, sec_names, wB, sector, ndx_only, beta):
    """이름 책 — 섹터 능동 a_g(sec_names 차례) → w_B 비례 배수 → frozen v_core 투영(섹터 띠 0.15) → β 띠. 돌려주는 것 (w, info)."""
    C = _C()
    wB = np.asarray(wB, float)
    sec = ["_none" if s is None else str(s) for s in sector]
    Wg = {}
    for s, v in zip(sec, wB):
        Wg[s] = Wg.get(s, 0.0) + float(v)
    amap = {str(g): float(a) for g, a in zip(sec_names, a_sec)}
    w = np.array([wB[i] * (Wg[s] + amap.get(s, 0.0)) / Wg[s] if Wg[s] > 0 else wB[i] for i, s in enumerate(sec)])
    w = np.where(w > 0, w, 0.0)
    w = w / w.sum()
    proj = lambda x: C.project_active(x, wB, sector, ndx_only, sband=SBAND)[0]
    wp = proj(w)
    wb, binfo = C.beta_band(wp, wB, beta, proj)
    wb = np.where(wb > 1e-15, wb, 0.0)
    return wb / wb.sum(), {"beta": binfo, "active_sector": {g: float(a) for g, a in zip(sec_names, a_sec)}}


def sector_returns(U, months, blind_seed=None):
    """PIT GICS 섹터 VW 월수익 — 결정 달 m 의 명단(합집합 · 금융 포함) · 시총 m · 보유월 m+1 수익(v_pit.hold_ret · y_stop) → 행렬(달 × 섹터).
    months = 결정 달 차례 · 돌려주는 것 (보유 달 목록, 섹터 이름, R) · blind_seed 가 있으면 선 칸을 씨앗 잡음(월 표준편차 0.05)으로 바꾼다(눈가림).
    🚨 실자료 수익(굽기 입력) — 값을 찍지 않는다."""
    rows, secs = {}, set()
    for m in months:
        me = U.me(m)
        hr = U.hold_ret(m)
        acc = {}
        for r in U.members(m):
            s, _ = U.sector(r["t"], m, r["ndx_only"])
            v = me[r["t"]][0]
            x = hr.get(r["t"])
            if s is None or not v or x is None or not np.isfinite(x):
                continue
            a = acc.setdefault(s, [0.0, 0.0])
            a[0] += v * x
            a[1] += v
        rows[WC.mshift(m, 1)] = {s: a[0] / a[1] for s, a in acc.items() if a[1] > 0}
        secs |= set(rows[WC.mshift(m, 1)])
    names = sorted(secs)
    hold = sorted(rows)
    R = np.array([[rows[h].get(s, np.nan) for s in names] for h in hold], float)
    if blind_seed is not None:
        rng = np.random.default_rng(blind_seed)
        ok = np.isfinite(R)
        R = np.where(ok, rng.normal(0.0, 0.05, R.shape), np.nan)
    return hold, names, R


def l_twin(kind, R_df, window_hold=None):
    """내부 L 쌍둥이(French 49 산업 VW 월수익 · 소수) — 평가 달(보유월)을 20년 창으로 자른다(사용자 규칙 · w_core.trim_window) ·
    Π̂ 창의 과거 수익(보유월 < 2006-09)은 신호 입력(K3 선언). 돌려주는 것 {summary, clean_summary(2020-07~), n_assets}. 🚨 kind 자물쇠."""
    import w_stagem as S
    WC.assert_kind_allowed(kind, "w_pap.l_twin")
    months = [str(p) for p in R_df.index]
    R = R_df.to_numpy(float)
    R = np.where(R <= -0.99, np.nan, R)                     # French 결측 부호(−99.99 %)
    ls = ls_series(kind, months, R, "pap")
    hold = {WC.mshift(m, 1): r for m, r in zip(ls["dec"], ls["ret"])}
    hold = WC.trim_window(hold, basis="hold")
    if window_hold:
        hold = {m: v for m, v in hold.items() if window_hold[0] <= m <= window_hold[1]}
    WC.assert_window(list(hold), "W03 내부 L 쌍둥이", "hold")
    ms = sorted(hold)
    dec = [WC.mshift(m, -1) for m in ms]
    sm = S.summarize(dec, [hold[m] for m in ms], DIRECTION, lag=NW_LAG)
    cl = [(d, hold[m]) for d, m in zip(dec, ms) if m >= CLEAN_FROM]
    smc = S.summarize([d for d, _ in cl], [v for _, v in cl], DIRECTION, lag=NW_LAG)
    return {"summary": sm, "clean_summary": smc, "first_hold": ms[0] if ms else None, "n_assets": sorted(set(ls["n_assets"])),
            "layer": "내부 L(사이트 · 공개 산출에 싣지 않는다)"}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 자료만)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _st_identity():
    rng = np.random.default_rng(WC.SEED)
    N = 11
    Pi = rng.normal(0, 1, (N, N))
    A = 0.5 * (Pi - Pi.T)
    Sm = 0.5 * (Pi + Pi.T)
    assert np.allclose(A.T, -A, atol=0) and np.allclose(Sm + A, Pi, atol=1e-15)
    parts = pap_parts(Pi, 5)
    mus = [mu for mu, _ in parts]
    assert len(parts) == 5 and all(a >= b for a, b in zip(mus, mus[1:]))           # N 11 → 반대칭 쌍 5
    ev = np.linalg.eigvals(A)
    pos = sorted([e.imag for e in ev if e.imag > 1e-12], reverse=True)
    assert np.allclose(pos, mus, atol=1e-10)
    for mu, L in parts:
        assert np.allclose(L.T, -L, atol=1e-14)                                    # L_k 반대칭
        assert abs(np.trace(L @ Pi) - mu) < 1e-10                                  # 기대 수익 = μ_k
        assert abs(np.trace(L @ Sm)) < 1e-12                                       # 대칭부 몫 0
        assert abs(np.linalg.norm(L, "fro") - 1.0 / math.sqrt(2.0)) < 1e-10        # 단위 복소 고유벡터(‖x‖ = ‖y‖ = 1/√2 · x ⊥ y) → ‖L‖_F = 1/√2
    # 위상 불변(평면 안 회전) — v → e^{iφ} v 로 같은 L
    lam, V = np.linalg.eigh(1j * A)
    v = V[:, np.argmin(lam)]
    for phi in (0.3, 1.7, -2.2):
        u = v * np.exp(1j * phi)
        L1 = np.outer(u.imag, u.real) - np.outer(u.real, u.imag)
        assert np.allclose(L1, parts[0][1], atol=1e-12)
    # 서로 다른 PAP 는 직교(tr(L_j′ L_k) = 0)
    for a in range(len(parts)):
        for b in range(a + 1, len(parts)):
            assert abs(np.trace(parts[a][1].T @ parts[b][1])) < 1e-10
    # PEP: tr(w w′ Π) = e_k · 첫 원소 양
    for e, Lp in pep_parts(Pi, 3):
        assert abs(np.trace(Lp @ Pi) - e) < 1e-10
    w0 = np.linalg.eigh(Sm)[1][:, -1]
    assert np.allclose(pep_parts(Pi, 1)[0][1], np.outer(w0, w0), atol=1e-12)
    return "Π = Π_s + Π_a · 반대칭 쌍 5(N 11) · tr(L_k Π) = μ_k · 대칭부 몫 0 · ‖L‖_F 1/√2 · 위상 불변 · PAP 직교 · PEP 고유값"


def _st_center_recover():
    rng = np.random.default_rng(WC.SEED + 1)
    T, N = 240, 11
    months = WC.months_between("2006-01", WC.mshift("2006-01", T - 1))
    # 심은 선후행: R_{t+1} = B S_t + 드리프트 + 잡음 · B 반대칭(한쪽 방향 전파)
    B = np.zeros((N, N))
    for i in range(N - 1):
        B[i + 1, i] = 0.02
        B[i, i + 1] = -0.02
    R = np.zeros((T, N))
    R[0] = rng.normal(0, 0.04, N)
    for t in range(T - 1):
        s = rank_signal(R[t])
        R[t + 1] = B @ s + 0.01 + rng.normal(0, 0.03, N)
    S = signals_from_returns(R)
    # 중심화: 모든 수익에 상수를 더해도 Π̂ 불변(1e−12) — R̄·S̄′ 누수 차단
    P1, i1 = pi_hat(R, S, 100)
    P2, i2 = pi_hat(R + 0.5, S, 100)
    assert np.allclose(P1, P2, atol=1e-12) and np.array_equal(i1, i2)
    P3, _ = pi_hat(R + 0.5, S, 100, center=False)
    assert not np.allclose(P1, P3, atol=1e-6)
    # 창 · 선견: 결정 j 의 Π̂ 는 R[j+1] 을 쓰지 않는다
    R2 = R.copy()
    R2[101] += 5.0
    assert np.allclose(pi_hat(R2, S, 100)[0], P1, atol=0)
    assert pi_hat(R, S, 59)[0] is None and pi_hat(R, S, 60)[0] is not None
    # 복원: PAP 롱숏이 양 · NW(6) t 크다 · 대각 대조는 작다(심은 효과가 비대각뿐)
    pr = primary("synth", months, R, window=(months[60], months[-2]))
    assert pr["summary"]["nw_t"] > 4 and pr["summary"]["p_one"] < 1e-4, pr["summary"]
    dg = primary("synth", months, R, window=(months[60], months[-2]), arm="diag")
    assert abs(dg["summary"]["nw_t"]) < 3, dg["summary"]
    # 위약: 섞기 분포 가운데 관측이 위쪽 끝
    pl = placebo("synth", months, R, 30, WC.SEED, window=(months[60], months[-2]))
    import w_stagem as SM
    assert SM.placebo_rank(pr["summary"]["nw_t"], pl["t"], +1) >= 0.9
    # 귀무(순수 잡음)에서 t 는 작다
    R0 = rng.normal(0.005, 0.04, (T, N))
    p0 = primary("synth", months, R0, window=(months[60], months[-2]))
    assert abs(p0["summary"]["nw_t"]) < 3.5
    # 자산 결측(A2): 한 섹터가 늦게 시작하면 창이 찰 때까지 뺀다
    R3 = R.copy()
    R3[:120, 10] = np.nan
    ls = ls_series("synth", months, R3)
    na = dict(zip(ls["dec"], ls["n_assets"]))
    assert na[months[150]] == 10 and na[months[181]] == 11, (na[months[150]], na[months[181]])
    assert _raises(lambda: ls_series("real", months, R))
    return "중심화(상수 드리프트 불변) · 선견 없음 · 심은 반대칭 복원 t %.1f · 대각 대조 t %.1f · 위약 백분위 · 귀무 · 늦은 섹터(A2)" % (
        pr["summary"]["nw_t"], dg["summary"]["nw_t"])


def _st_book_twin():
    rng = np.random.default_rng(WC.SEED + 2)
    a = sector_active([0.3, -0.1, 0.05, 0.0])
    assert abs(np.abs(a).sum() - GROSS) < 1e-12 and abs(a.sum()) < 1e-12
    assert np.all(sector_active([1.0, 1.0, 1.0]) == 0)
    # 이름 책 — 섹터 능동이 실린다 · 띠 · 상한 · β 띠
    n = 60
    secs = ["S%d" % (i % 6) for i in range(n)]
    wB = rng.dirichlet(np.ones(n) * 3)
    ndx = np.zeros(n, bool)
    beta = rng.normal(1.0, 0.2, n)
    names = ["S%d" % g for g in range(6)]
    act = sector_active([0.5, -0.5, 0.2, -0.2, 0.0, 0.0])
    w, info = pap_book(act, names, wB, secs, ndx, beta)
    assert abs(w.sum() - 1) < 1e-12 and (w >= 0).all() and np.max(np.abs(w - wB)) <= 0.05 + 1e-9
    sa = {g: float(sum(w[i] - wB[i] for i in range(n) if secs[i] == g)) for g in names}
    assert all(abs(v) <= SBAND + 1e-9 for v in sa.values()) and sa["S0"] > 0 > sa["S1"]
    assert abs(float(w @ beta - wB @ beta)) <= 0.03 + 1e-6 and info["beta"]["ok"]
    # 섹터 능동 0 이면 책 = w_B(항등 · 투영 · β 띠 뒤에도)
    w0, _ = pap_book(np.zeros(6), names, wB, secs, ndx, beta)
    assert np.allclose(w0, wB / wB.sum(), atol=1e-12)
    # 내부 L 쌍둥이 — 20년 창 자르기(보유월 ≥ 2006-09) · 청정 표시
    import pandas as pd
    idx = pd.period_range("1990-01", "2026-08", freq="M")
    df = pd.DataFrame(rng.normal(0.008, 0.05, (len(idx), 12)), index=idx)
    df.iloc[:30, 3] = -99.99 / 100.0
    tw = l_twin("synth", df)
    assert tw["first_hold"] == WC.HOLD_FLOOR and tw["summary"]["T"] == 240 and tw["clean_summary"]["T"] == len(WC.months_between("2020-07", "2026-08"))
    assert _raises(lambda: l_twin("real", df))
    return "섹터 능동 Σ|a| 0.20 · 완전 투자 · 이름 책(띠 0.15 · 상한 · β 띠) · 능동 0 = w_B · L 쌍둥이 20년 창(첫 보유 %s · T 240) · 청정 2020-07~" % tw["first_hold"]


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
    assert not WG.check_units(PAP_UNITS) and not WG.literal_scan(os.path.abspath(__file__))
    assert CARD in WC.MEASURE_ONLY
    return "금지 import 없음 · 입력 단위 · 문자열 상수 · 측정만(채택 경로 없음)"


def selftest():
    res, ok = [], True
    for fn in (_st_identity, _st_center_recover, _st_book_twin, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-18s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_pap selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
