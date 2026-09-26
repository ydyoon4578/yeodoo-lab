# -*- coding: utf-8 -*-
"""build/v_cond.py — 배치 V 조건(거미줄 가닥) 층: 관측 달 식 · 결정 달 늦춤 · z 변환 · 늦은 자료 · S 층 이음 · 가닥 표 · 군 배정 · 선견 목록.

설계 원본(구속): vbatch_research.json final.conditions(principle · primary_strands · twin_only_strands · forbidden · clusters_R2 · share_matrix) ·
  final.estimator(Z_MIN 60 · rolling240 · ±2) · final.slate[*].web_theta. 설계를 다시 짓지 않는다.
복사(가져오지 않는다 — D22): u_data 의 z_expanding · z_rolling · z_onesided · zt · _zero_small · to_decision · extend_to · finalize · _tail_z ·
  x_slow · x_disp · x_vsprd · x_bsprd · daily_var_month · x_panicx · cond_x/cond_z 틀 · sf_market(S 층 이음) · t_signals 의 ib24 · contiguous · lagged.
새 가닥: RVAR(log 21거래일 Σ 시장 초과 일수익²) · MKT3(3개월 시장 초과 로그수익) · G2own L(25_ME_BETA ME5 BETA1 월별 BE/ME − 시장) ·
  PQ(6_ME_OP BIG HiOP − BIG LoOP 월별 BE/ME) · G2own S(책 BE/ME − 벤치마크 BE/ME · 이름 수준 입력은 v_pit) · G1rel(배분기 · 수익 입력은 굽기 v_alloc 에서) ·
  ATTN 은 이름 특성이라 build/v_ear.py.

〔초록〕 가닥 규칙(D26 · 등록 전 원문 열기 — data/_vb_lit_open.json 이 한 곳): 원문을 못 열면 그 가닥은 쌍둥이로 강등 · 원문 부호가 반대면 삭제(뒤집지 않는다).
  판정(파일 참조 · 2026-09-27 네 번째 시도 = 사용자 브라우저로 받은 저자 공개 사본 뒤): SLOW = CGH 2004 본문을 열었다(표 IV 12개월 상태 · 표 V 연속 LAGMKT +) ·
  DM 표 5 와 같은 방향 → 주 가닥 · DISP = Stivers–Sun 본문 미개봉(SSRN 초록만) → 쌍둥이 · PANICX(V03) = HKV 2010 본문을 열었다 — 부호는 같은 쪽이지만 상태가
  «지난 4주 누적 시장 수익 −1.5σ 아래»(표 VIII · IX)라 등록 정의(24개월 약세 표지 × 126일 분산)의 결과가 아니다 → 쌍둥이(삭제 아님) · MKT3 = Cheng 외 2017 원문을 열었으나
  종목 수준 결과(각주 3) → 쌍둥이 · ATTN 같은 날 발표 수 = HLT 2006-10-25 작업 논문 판을 열었다(결과 · 부호가 있다) → 주 판(ATTN = ½·금 + ½·같은 날 수 · v_ear).
  이 판정은 strand_status 가 파일에서 읽는다 — 파일을 고치면 코드를 고치지 않고 바뀐다(등록 커밋에서 닫힌다).

🚨 수익 · 신호-수익 통계를 계산하지 않는다. 조건 x · z 는 시장 수준 계열이다. 군 배정(|ρ| ≥ 0.5 · L 층 z 역사)은 F0 에서 한 번(명세 clusters_R2) —
   이 모듈은 함수만 두고 selftest 는 합성 계열로 돈다. 실자료 --smoke 는 모양만.

  python build/v_cond.py --selftest
  python build/v_cond.py --smoke            실자료 조건 L · S 모양 + 모든 조건 선견 점검(200 · 씨앗 20260925) — 참/거짓 · 개수만
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
import time
import traceback

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import v_data as VD          # noqa: E402

contiguous, lagged = VD.contiguous, VD.lagged
Z_MIN, Z_ROLL, Z_CLIP, LATE_TOL, MIN_FIRMS = VD.Z_MIN, VD.Z_ROLL, VD.Z_CLIP, VD.LATE_TOL, VD.MIN_FIRMS
IND_N, VAR_N, RVAR_N = 63, 126, 21
S_FROM = "2006-03"            # S 층 결정 달의 처음(랩 SPY 일간 2006-01-03 → 첫 월 수익 2006-02 → t−1 ≥ 2006-02 · u_data SF_FROM 과 같다)
LIT_FILE = os.path.join(VD.DATA, "_vb_lit_open.json")


# ══════════════════════════════════════════════════════════════════════════
#  z 변환 · 결정 달 · 늦은 자료 — 복사: u_data
# ══════════════════════════════════════════════════════════════════════════
def to_decision(obs, lag, tol=LATE_TOL, freeze=False):
    """관측 달 계열 → 결정 달 계열(s + lag). 마지막 관측 뒤 tol 달은 그 값을 늦게 쓴다(late) — 복사: u_data.to_decision."""
    s = contiguous(pd.Series(obs, dtype=float))
    if len(s) == 0 or s.notna().sum() == 0:
        e = pd.Series(dtype=float, index=pd.PeriodIndex([], freq="M"))
        return e, e.astype(bool)
    d = lagged(s, lag)
    lv = s.last_valid_index()
    fresh_end = lv + lag
    ext = max(int(tol), 0)
    idx = pd.period_range(d.index.min(), fresh_end + ext, freq="M")
    d = d.reindex(idx)
    late = pd.Series(False, index=idx)
    for k in range(1, ext + 1):
        prev = lagged(s, lag + k).reindex(idx)
        fill = d.isna() & prev.notna()
        d[fill] = prev[fill]
        late[fill] = True
    return d, late


def extend_to(x, until, freeze=False):
    x = contiguous(pd.Series(x, dtype=float))
    until = pd.Period(until, "M")
    if len(x) == 0 or until <= x.index.max():
        return x
    idx = pd.period_range(x.index.min(), until, freq="M")
    out = x.reindex(idx)
    if freeze and x.notna().any():
        out.loc[out.index > x.index.max()] = x.loc[x.last_valid_index()]
    return out


def _zero_small(s, scale):
    return s.where(~(s.abs() <= 1e-12 * np.maximum(1.0, scale.fillna(0.0))), 0.0)


def z_expanding(x, min_n=Z_MIN, clip=Z_CLIP):
    x = contiguous(pd.Series(x, dtype=float))
    m = x.expanding(min_n).mean()
    s = _zero_small(x.expanding(min_n).std(ddof=1), x.abs().expanding(min_n).max())
    z = ((x - m) / s).where(s > 0, 0.0).where(m.notna() & x.notna())
    return z.clip(-clip, clip)


def z_rolling(x, n=Z_ROLL, min_n=Z_MIN, clip=Z_CLIP):
    x = contiguous(pd.Series(x, dtype=float))
    r = x.rolling(n, min_periods=min_n)
    m = r.mean()
    s = _zero_small(r.std(ddof=1), x.abs().rolling(n, min_periods=min_n).max())
    z = ((x - m) / s).where(s > 0, 0.0).where(m.notna() & x.notna())
    return z.clip(-clip, clip)


def z_onesided(x, n=Z_ROLL, min_n=Z_MIN, clip=Z_CLIP):
    """U21 한쪽 척도형 — z = clip(x/s₂₄₀, 0, 2) · s₂₄₀ 정의 전(관측 < 60)은 NaN(가닥 비활성) — 복사: u_data.z_onesided."""
    x = contiguous(pd.Series(x, dtype=float))
    s = _zero_small(x.rolling(n, min_periods=min_n).std(ddof=1), x.abs().rolling(n, min_periods=min_n).max())
    z = (x / s).where(s > 0).clip(0.0, clip)
    return z.where(s.isna() | z.notna(), 0.0).where(x.notna() & s.notna())


def zt(x, ztype, **kw):
    if ztype == "expanding":
        return z_expanding(x, **kw)
    if ztype == "rolling240":
        return z_rolling(x, **kw)
    if ztype == "onesided":
        return z_onesided(x, **kw)
    raise ValueError(ztype)


def finalize(z, until=None):
    """첫 유효 z 전은 NaN(가닥 비활성) · 그 뒤 빈 달(늦은 자료 · 공백)은 0 과 stale 표지 — 복사: u_data.finalize."""
    z = contiguous(pd.Series(z, dtype=float))
    if until is not None:
        z = extend_to(z, until)
    fv = z.first_valid_index()
    stale = pd.Series(False, index=z.index)
    if fv is None:
        return z, stale
    after = z.index >= fv
    miss = after & z.isna().to_numpy()
    stale[miss] = True
    z = z.copy()
    z[miss] = 0.0
    return z, stale


def _tail_z(hist, tail, ztype, n=Z_ROLL, min_n=Z_MIN, clip=Z_CLIP):
    """S 층 결정 달 t 의 z — 적률은 [L 계열 x(≤ t−2), 이은 x_{t−1}, 이은 x_t] — 복사: u_data._tail_z."""
    arr = np.r_[np.asarray(hist, float), np.asarray(tail, float)]
    xt = arr[-1]
    if not np.isfinite(xt):
        return np.nan
    w = arr if ztype == "expanding" else arr[-n:]
    v = w[np.isfinite(w)]
    if ztype == "onesided":
        if len(v) < min_n:
            return np.nan
        s = float(np.std(v, ddof=1))
        if s <= 1e-12 * max(1.0, float(np.max(np.abs(v)))):
            return 0.0
        return float(min(max(xt / s, 0.0), clip))
    if len(v) < min_n:
        return np.nan
    m, s = float(np.mean(v)), float(np.std(v, ddof=1))
    if s <= 1e-12 * max(1.0, float(np.max(np.abs(v)))):
        return 0.0
    return float(min(max((xt - m) / s, -clip), clip))


# ══════════════════════════════════════════════════════════════════════════
#  관측 달 식(순수 함수) — 복사 + 새 가닥
# ══════════════════════════════════════════════════════════════════════════
def ib24(mkt_tr):
    """I_B,t = 1[Π_{k=0..23}(1 + Mkt_{t−k}) < 1] — 복사: t_signals.ib24(DM 정의)."""
    r = contiguous(pd.Series(mkt_tr, dtype=float))
    lg = np.log1p(r).rolling(24).sum()
    return pd.Series((lg < 0).astype(float), index=r.index).where(lg.notna())


def x_slow(mkt, rf):
    """SLOW(U01) 관측 t: Σ_{t−11..t} log(1 + R_mkt) − Σ log(1 + RF) — 12달이 다 있어야 — 복사: u_data.x_slow."""
    m, r = contiguous(pd.Series(mkt, dtype=float)), contiguous(pd.Series(rf, dtype=float))
    ex = (np.log1p(m) - np.log1p(r.reindex(m.index)))
    return ex.rolling(12, min_periods=12).sum()


def x_mkt3(mkt, rf):
    """MKT3(새) 관측 t: 최근 3개월 시장 초과 로그수익 Σ_{t−2..t} log(1 + R_mkt) − log(1 + RF) — 3달이 다 있어야."""
    m, r = contiguous(pd.Series(mkt, dtype=float)), contiguous(pd.Series(rf, dtype=float))
    ex = (np.log1p(m) - np.log1p(r.reindex(m.index)))
    return ex.rolling(3, min_periods=3).sum()


def x_disp(ind_m, nfirms, min_firms=MIN_FIRMS):
    """DISP(U08) 관측 t: 30 산업 월 VW 수익의 단면 sd(ddof 1) — 그달 기업 수 < 20 인 칸 제외 · 칸 둘 이상 — 복사: u_data.x_disp."""
    R = pd.DataFrame(ind_m)
    N = pd.DataFrame(nfirms).reindex(index=R.index, columns=R.columns)
    ok = R.notna() & (N >= min_firms)
    V = R.where(ok)
    sd = V.std(axis=1, ddof=1)
    return contiguous(sd.where(ok.sum(axis=1) >= 2))


def x_vsprd(bm_a, ret_xd, hi="Hi 30", lo="Lo 30"):
    """VSPRD(U16) 관측 t: log(BE/ME_Hi30 / BE/ME_Lo30) — 연 절(행 Y = Y년 6월 편입)을 7월부터 두 포트폴리오 배당 제외 VW 가격 비로 매달 갱신 —
    복사: u_data.x_vsprd."""
    B = pd.DataFrame(bm_a)
    R = contiguous(pd.DataFrame(ret_xd)[[hi, lo]].copy()) if isinstance(ret_xd, pd.DataFrame) else None
    lr = (np.log1p(R[hi]) - np.log1p(R[lo])) if R is not None else None
    out = {}
    for y in pd.Index(B.index).astype(int):
        bh, bl = B.loc[y, hi], B.loc[y, lo]
        if not (bh == bh and bl == bl and bh > 0 and bl > 0):
            continue
        base = math.log(bh) - math.log(bl)
        cum = 0.0
        for mth in pd.period_range("%04d-07" % y, "%04d-06" % (y + 1), freq="M"):
            v = lr.get(mth, np.nan) if lr is not None else np.nan
            if v != v:
                break
            cum += float(v)
            out[mth] = base - cum
    s = pd.Series(out, dtype=float)
    s.index = pd.PeriodIndex(s.index, freq="M")
    return contiguous(s.sort_index())


def x_bsprd(beta_a, hi="Hi 20", lo="Lo 20"):
    """BSPRD(U17) 관측 t: FP 형 (β̄_Hi20 − β̄_Lo20)/(β̄_Lo20 · β̄_Hi20) — «Value-Weighted Average of Prior Beta»(연 · 행 Y = Y년 6월) ·
    연 계단 t ∈ [Y-06, (Y+1)-05] — 복사: u_data.x_bsprd."""
    B = pd.DataFrame(beta_a)
    out = {}
    for y in pd.Index(B.index).astype(int):
        bh, bl = B.loc[y, hi], B.loc[y, lo]
        if not (bh == bh and bl == bl) or bh * bl == 0:
            continue
        v = (bh - bl) / (bl * bh)
        for mth in pd.period_range("%04d-06" % y, "%04d-05" % (y + 1), freq="M"):
            out[mth] = float(v)
    s = pd.Series(out, dtype=float)
    s.index = pd.PeriodIndex(s.index, freq="M")
    return contiguous(s.sort_index())


def daily_var_month(mex_d, n=VAR_N):
    """σ̂²_m,t = 그달 마지막 거래일까지 n 거래일 일간 시장 초과수익 분산(ddof 1) — 복사: u_data.daily_var_month."""
    d = pd.Series(mex_d, dtype=float).dropna().sort_index()
    v = d.rolling(n, min_periods=n).var(ddof=1)
    return contiguous(v.groupby(v.index.to_period("M")).last())


def x_panicx(mkt, mex_d, n=VAR_N):
    """PANICX(U21) 관측 t: I_B,t · σ̂²_m,t — 복사: u_data.x_panicx."""
    ib = ib24(mkt)
    v = daily_var_month(mex_d, n)
    idx = ib.index.union(v.index)
    return contiguous(ib.reindex(idx) * v.reindex(idx))


def x_rvar(mex_d, n=RVAR_N):
    """RVAR(새) 관측 t: log(그달 마지막 거래일까지 21 거래일 Σ 시장 초과 일수익²) — Nagel 의 VIX 대리(주식 자료 · VIX 는 보유 · 입력 아님)."""
    d = pd.Series(mex_d, dtype=float).dropna().sort_index()
    ss = (d * d).rolling(n, min_periods=n).sum()
    m = ss.groupby(ss.index.to_period("M")).last()
    return contiguous(np.log(m.where(m > 0)))


def _vw_beme(beme, nf, sz, cols):
    """월별 BE/ME 절(«Value Weight Average of BE/ME Calculated … Dec t−1») 의 칸 묶음 VW 평균 — 가중 = 그달 기업 수 × 평균 시총.
    칸 가운데 BE/ME · 가중이 없는 칸은 뺀다 · 남은 칸이 없으면 NaN."""
    B = pd.DataFrame(beme)[cols]
    W = (pd.DataFrame(nf)[cols] * pd.DataFrame(sz)[cols]).reindex(B.index)
    ok = B.notna() & W.notna() & (W > 0) & (B > 0)
    num = (B.where(ok) * W.where(ok)).sum(axis=1)
    den = W.where(ok).sum(axis=1)
    return (num / den).where(den > 0)


def x_g2own_beta(beme, nf, sz, cell="BIG LoBETA"):
    """G2own(V02 · L) 관측 t: log(BE/ME_ME5β1) − log(BE/ME_시장) · ME5 × β1 = French 칸 «BIG LoBETA» · 시장 = 25 칸 전부의 VW 평균(같은 절 · 같은 가중)."""
    B = pd.DataFrame(beme)
    mk = _vw_beme(B, nf, sz, list(B.columns))
    c = B[cell].where(B[cell] > 0)
    return contiguous(np.log(c) - np.log(mk.where(mk > 0)))


def x_pq(beme, hi="BIG HiOP", lo="BIG LoOP"):
    """PQ(V07 G2own · L) 관측 t: 퀄리티의 값 = log(BE/ME BIG HiOP) − log(BE/ME BIG LoOP)(6_ME_OP 월별 BE/ME 절 · AFP)."""
    B = pd.DataFrame(beme)
    h, l = B[hi].where(B[hi] > 0), B[lo].where(B[lo] > 0)
    return contiguous(np.log(h) - np.log(l))


def g2own_book(w_book, w_bench, be, me):
    """G2own S(책 수준 · MOM · LIQ · LBS · QLT 의 S 판 · INS · EAR 쌍둥이): log(VW 평균 BE/ME_책) − log(VW 평균 BE/ME_기준).
    w_* = {이름: 비중} · be · me = {이름: 최초 제출 장부가 · 시총(v_pit · 같은 단위)} · BE ≤ 0 · 결측 이름은 두 평균 모두에서 빼고 비중을 다시 맞춘다
    (French BE/ME 절이 음의 BE 를 빼는 것과 같다 · 선언). 한쪽이라도 서지 않으면 None."""
    def vwavg(w):
        num = den = 0.0
        for k, x in w.items():
            b, m = be.get(k), me.get(k)
            if x and x > 0 and b is not None and m and m > 0 and b > 0:
                num += x * b / m
                den += x
        return num / den if den > 0 else None
    a, b = vwavg(w_book), vwavg(w_bench)
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return math.log(a) - math.log(b)


def g1rel(y, lag=0, k_min=3):
    """G1rel(배분기 · 명세 allocator.signal): G1_f,t = Σ_{s=t−11..t} y_f,s(12달이 다 있어야) → 전략 사이 상대 z r_f = (G1_f − 평균_f)/sd_f(K_t ≥ 3).
    y = DataFrame(관측 달 × 전략 · θ = 1 책 능동수익) · lag = 결정 달 늦춤(L 2 · S 0). 🚨 수익 입력이라 굽기(v_alloc)에서만 실자료로 부른다."""
    Y = pd.DataFrame(y).sort_index()
    Y = Y.reindex(pd.period_range(Y.index.min(), Y.index.max(), freq="M"))
    G = Y.rolling(12, min_periods=12).sum()
    mu = G.mean(axis=1)
    sd = G.std(axis=1, ddof=1)
    K = G.notna().sum(axis=1)
    Z = G.sub(mu, axis=0).div(sd.where(sd > 0), axis=0).where(K >= k_min, np.nan)
    Z.index = Z.index + lag
    return Z


# ══════════════════════════════════════════════════════════════════════════
#  조건 표(명세 conditions.primary_strands) · 가닥 표(slate[*].web_theta) · 〔초록〕 판정
# ══════════════════════════════════════════════════════════════════════════
#  id: (이름, z 유형, 늦춤 L, 늦춤 S("sf" = S 층 이음), 늦은 자료 규칙, 기전 가족(군의 손 배정), U 번호)
CONDS = {
    "SLOW": ("12개월 시장 초과 로그수익", "expanding", 0, "sf", "zero", "시장 상태", "U01"),
    "DISP": ("French 30 산업 월수익 단면 sd", "expanding", 2, 2, "zero", "구조", "U08"),
    "BSPRD": ("사전 베타 스프레드(FP 형)", "rolling240", 2, 2, "zero", "스프레드(베타)", "U17"),
    "VSPRD": ("French BE-ME Hi30/Lo30 log BE/ME 스프레드", "rolling240", 2, 2, "zero", "자기 값(가치 스프레드)", "U16"),
    "RVAR": ("log(21거래일 Σ 시장 초과 일수익²)", "rolling240", 0, "sf", "zero", "변동성", "새"),
    "PANICX": ("I_B × 126일 시장 분산", "onesided", 0, "sf", "zero", "패닉", "U21"),
    "MKT3": ("최근 3개월 시장 초과 로그수익", "expanding", 0, "sf", "zero", "시장 하락", "새"),
    "G2own:V02": ("log BE/ME(ME5×β1 = BIG LoBETA) − log BE/ME(시장)", "rolling240", 2, 2, "zero", "자기 값(HKS)", "U19→G2"),
    "G2own:V07": ("PQ = log BE/ME(BIG HiOP) − log BE/ME(BIG LoOP)", "rolling240", 2, 2, "zero", "자기 값(퀄리티의 값)", "U19→G2"),
}
#  전략 → [(가닥, 부호, 층, 출처 가닥 id(문헌 판정)))] — 명세 slate[*].web_theta(뺀 가닥은 없다 · D07)
STRANDS = {
    "V01": [("SLOW", +1, "L·S", "SLOW"), ("DISP", -1, "L·S", "DISP"), ("G2own:S", +1, "S", "G2own")],
    "V02": [("BSPRD", +1, "L·S", "BSPRD"), ("G2own:V02", +1, "L·S", "G2own")],
    "V03": [("RVAR", +1, "L·S", "RVAR"), ("PANICX", +1, "L·S", "PANICX"), ("MKT3", -1, "L·S", "MKT3"), ("G2own:S", +1, "S", "G2own")],
    "V06": [("VSPRD", +1, "L·S", "VSPRD"), ("DISP", +1, "L·S", "DISP")],
    "V07": [("G2own:V07", +1, "L·S", "G2own")],
    "V04": [], "V05": [], "V08": [],
}
#  문헌 판정이 없을 때의 기본(명세 level) — 파일이 덮는다. 〔초록〕 만인 가닥은 파일이 «열었다 · 같은 부호» 를 적지 않으면 쌍둥이.
STRAND_LEVEL = {"SLOW": "초록+직접", "DISP": "초록", "BSPRD": "본문", "VSPRD": "본문+직접", "RVAR": "본문", "PANICX": "초록", "MKT3": "초록",
                "G2own": "직접", "ATTN_friday": "직접", "ATTN_sameday": "초록"}


def strand_status(path=None):
    """{가닥 id: {"status": primary | twin | dropped, "why": …}} — data/_vb_lit_open.json(한 곳)을 읽는다 · 파일이 없으면 〔초록〕 만인 가닥은 쌍둥이(D26)."""
    p = path or LIT_FILE
    doc = VD.read_json(p) if os.path.exists(p) else {}
    dec = (doc.get("strand_decisions") or {})
    out = {}
    for sid, lvl in STRAND_LEVEL.items():
        if sid in dec:
            out[sid] = {"status": dec[sid]["status"], "why": dec[sid].get("why")}
        elif lvl == "초록":
            out[sid] = {"status": "twin", "why": "원문 열기 기록 없음 — D26 강등(기본)"}
        else:
            out[sid] = {"status": "primary", "why": "본문 · 직접 출처(%s)" % lvl}
    return out


def web(sid, status=None):
    """전략 sid 의 주 가닥 · 쌍둥이 가닥 — ([(가닥, 부호, 층)], [(가닥, 부호, 층, 사유)]) · 삭제 가닥은 어느 쪽에도 없다."""
    st = status or strand_status()
    prim, twin = [], []
    for c, sg, layer, lid in STRANDS[sid]:
        s = st.get(lid, {"status": "primary"})
        if s["status"] == "primary":
            prim.append((c, sg, layer))
        elif s["status"] == "twin":
            twin.append((c, sg, layer, s.get("why")))
    return prim, twin


def share_matrix(status=None):
    """가닥 공유 행렬(조건 × 전략 · 부호) — P3 점검(한 조건은 최대 두 전략 · G2own 면제). 돌려주는 것 (표, P3 위반 목록)."""
    rows = {}
    for sid in STRANDS:
        prim, _ = web(sid, status)
        for c, sg, layer in prim:
            rows.setdefault(c, {})[sid] = sg
    viol = [c for c, d in rows.items() if not c.startswith("G2own") and len(d) > 2]
    return rows, viol


def assign_clusters(z_hist, families, rho=0.5):
    """군 = (손으로 붙인 기전 가족) ∪ (L 층 조건 z 역사의 |ρ| ≥ rho 이면 합침 · 전이적 폐포) — 명세 clusters_R2(F0 에서 한 번 · 등록문에 고정).
    z_hist = DataFrame(결정 달 × 조건 z) · families = {조건: 가족}. 돌려주는 것 {조건: 군 번호}."""
    Z = pd.DataFrame(z_hist)
    cols = list(Z.columns)
    par = {c: c for c in cols}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[max(ra, rb)] = min(ra, rb)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            if families.get(a) is not None and families.get(a) == families.get(b):
                union(a, b)
            pair = Z[[a, b]].dropna()
            if len(pair) >= 24:
                r = float(np.corrcoef(pair[a], pair[b])[0, 1])
                if np.isfinite(r) and abs(r) >= rho:
                    union(a, b)
    roots = sorted({find(c) for c in cols})
    return {c: roots.index(find(c)) for c in cols}


def pair_rho(z_hist, min_n=24, nd=4):
    """F0 — 조건 z 역사 쌍마다 상관(겹친 달 ≥ min_n · 소수 nd 자리) — {"A|B": ρ}(A < B 글자 차례). 시장 수준 · 특성 계열의 상관이다(수익 아님)."""
    Z = pd.DataFrame(z_hist)
    cols = sorted(Z.columns)
    out = {}
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            pair = Z[[a, b]].dropna()
            if len(pair) >= min_n and pair[a].std() > 0 and pair[b].std() > 0:
                r = float(np.corrcoef(pair[a], pair[b])[0, 1])
                if np.isfinite(r):
                    out["%s|%s" % (a, b)] = round(r, nd)
    return out


def pkey(a, b):
    return "%s|%s" % tuple(sorted((a, b)))


def clusters_for(conds, families, rho_pairs, rho=0.5, extra=None):
    """웹 하나의 군 이름(가닥 차례) — 그 웹의 가닥끼리만 (가족 같음) ∪ (|ρ| ≥ rho) 로 합치는 전이적 폐포.
    🔧 검토 고침(등록 전 · 선언): 폐포 범위 = 그 웹의 가닥(주 가닥 · 쌍둥이는 제 가닥 목록). 옛 판은 L 조건 아홉 전부의 폐포라, 한 웹의 두 가닥이
    웹 밖 조건(강등된 쌍둥이 가닥 등)을 거쳐 합쳐질 수 있었다(서로 |ρ| < 0.5 여도) — 명세 clusters_R2 «같은 쪽 군» 의 뜻(서로 다른 확인 증거)에 맞춘다.
    rho_pairs = pair_rho 결과(등록 F0) · extra = {"A|B": ρ}(S 전용 책 G2own 쌍 등 — F0 에서 잰 값). 군 이름 = 그 군의 첫 가닥 이름(가닥 차례)."""
    conds = list(conds)
    pos = {c: i for i, c in enumerate(conds)}
    par = {c: c for c in conds}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    rp = dict(rho_pairs or {})
    rp.update(extra or {})
    for i, a in enumerate(conds):
        for b in conds[i + 1:]:
            same_fam = families.get(a) is not None and families.get(a) == families.get(b)
            r = rp.get(pkey(a, b))
            if same_fam or (r is not None and abs(r) >= rho):
                ra, rb = find(a), find(b)
                if ra != rb:
                    lo, hi = (ra, rb) if pos[ra] < pos[rb] else (rb, ra)
                    par[hi] = lo
    return [find(c) for c in conds]


# ══════════════════════════════════════════════════════════════════════════
#  조건 → 결정 달 x · z (L 층)
# ══════════════════════════════════════════════════════════════════════════
def cond_x(cid, inp, extra=0):
    """조건 하나의 결정 달 x(L 층 · 늦춤은 여기서) — (x, late). inp = 입력 dict(inputs_L 이 만든다)."""
    nm, ztype, lagL, lagS, stale_rule, fam, ucode = CONDS[cid]
    freeze = stale_rule == "freeze"
    if cid == "SLOW":
        obs = x_slow(inp["mkt"], inp["rf"])
    elif cid == "MKT3":
        obs = x_mkt3(inp["mkt"], inp["rf"])
    elif cid == "DISP":
        obs = x_disp(inp["ind_m"], inp["ind_nf"])
    elif cid == "BSPRD":
        obs = x_bsprd(inp["beta_a"])
    elif cid == "VSPRD":
        obs = x_vsprd(inp["bm_a"], inp["bm_xd"])
    elif cid == "RVAR":
        obs = x_rvar(inp["mex_d"])
    elif cid == "PANICX":
        obs = x_panicx(inp["mkt"], inp["mex_d"])
    elif cid == "G2own:V02":
        obs = x_g2own_beta(inp["mb_beme"], inp["mb_nf"], inp["mb_sz"])
    elif cid == "G2own:V07":
        obs = x_pq(inp["op_beme"])
    else:
        raise KeyError(cid)
    return to_decision(obs, int(lagL) + extra, freeze=freeze)


def cond_z(cid, inp, extra=0, until=None):
    """조건 하나의 결정 달 z(L 층) — DataFrame(x, z, late, stale)."""
    x, late = cond_x(cid, inp, extra=extra)
    z = zt(x, CONDS[cid][1])
    z, stale = finalize(z, until)
    return pd.DataFrame({"x": x.reindex(z.index), "z": z, "late": late.reindex(z.index).fillna(False).astype(bool), "stale": stale})


def inputs_L(vintage=None):
    """L 층 조건 입력(French · 모두 CRSP 202608 고정본 · vintage = "2024-12" 이면 FIZ 판 사본 — 보고 전용 판 민감도) — {인자: (obj, 가용 이름)}.
    선견 점검도 이 표를 쓴다."""
    V = vintage
    f3 = VD.ff3("m", vintage=V)
    d3 = VD.ff3("d", vintage=V)
    mb = {"mb_beme": VD.french("me_beta", "vwbeme_m", vintage=V, pct=False), "mb_nf": VD.french("me_beta", "nfirms", vintage=V, pct=False),
          "mb_sz": VD.french("me_beta", "avgsize", vintage=V, pct=False)}
    return {"mkt": (f3["Mkt"], "french:mkt"), "rf": (f3["RF"], "french:mkt"), "mex_d": (d3["Mkt-RF"], "french:mkt_d"),
            "ind_m": (VD.french("ind30", "vw_m", vintage=V), "french:lag2"), "ind_nf": (VD.french("ind30", "nfirms", vintage=V, pct=False), "french:lag2"),
            "beta_a": (VD.french("beta", "vwavg_a", vintage=V, pct=False), "french:june"),
            "bm_a": (VD.french("beme", "vwavg_a", vintage=V, pct=False), "french:june"), "bm_xd": (VD.french("beme_xd", "vw_m", vintage=V), "french:lag2"),
            "mb_beme": (mb["mb_beme"], "french:lag2"), "mb_nf": (mb["mb_nf"], "french:lag2"), "mb_sz": (mb["mb_sz"], "french:lag2"),
            "op_beme": (VD.french("me_op", "vwbeme_m", vintage=V, pct=False), "french:lag2")}


COND_ARGS = {"SLOW": ("mkt", "rf"), "MKT3": ("mkt", "rf"), "DISP": ("ind_m", "ind_nf"), "BSPRD": ("beta_a",), "VSPRD": ("bm_a", "bm_xd"),
             "RVAR": ("mex_d",), "PANICX": ("mkt", "mex_d"), "G2own:V02": ("mb_beme", "mb_nf", "mb_sz"), "G2own:V07": ("op_beme",)}


def conditions_L(inp=None, until=None):
    """모든 조건 L 층 결정 달 z — DataFrame(결정 달 × 조건) · 열 이름 = 조건 id. 🚨 내부 기전 증거 층(D1) — 저장소에 쓰지 않는다."""
    inp = inp or inputs_L()
    raw = {k: o for k, (o, nm) in inp.items()}
    return pd.DataFrame({cid: cond_z(cid, {a: raw[a] for a in COND_ARGS[cid]}, until=until)["z"] for cid in CONDS})


# ══════════════════════════════════════════════════════════════════════════
#  S 층 — 결정 달 t 마다 이은 계열(French ≤ t−2 · SPY TR / rf_monthly t−1 · t · 일간은 SPY) — 복사 + 확장: u_data.sf_market
# ══════════════════════════════════════════════════════════════════════════
def s_market(cid, mkt, rf, spy_m, rf_lab, mex_d=None, spy_d=None, rf_lab_d=None, t_from=S_FROM, t_to=None, only=None):
    """S 층 시장 조건(SLOW · MKT3 · RVAR · PANICX) — x 역사(≤ t−2)는 L 계열 · t−1 · t 는 SPY 로 이은 값 · 적률은 이은 계열.
    돌려주는 것 DataFrame(x, z) · 결정 달 색인."""
    mkt = contiguous(pd.Series(mkt, dtype=float))
    rf = contiguous(pd.Series(rf, dtype=float)).reindex(mkt.index)
    spy_m, rf_lab = pd.Series(spy_m, dtype=float), pd.Series(rf_lab, dtype=float)
    ztype = CONDS[cid][1]
    daily = cid in ("RVAR", "PANICX")
    if cid == "SLOW":
        xL = x_slow(mkt, rf)
    elif cid == "MKT3":
        xL = x_mkt3(mkt, rf)
    elif cid == "RVAR":
        xL = x_rvar(mex_d)
    elif cid == "PANICX":
        xL = x_panicx(mkt, mex_d)
    else:
        raise KeyError(cid)
    if daily:
        sp = pd.Series(spy_d, dtype=float).dropna().sort_index()
        rs = sp / sp.shift(1) - 1.0
        rfd = pd.Series(rf_lab_d, dtype=float).reindex(rs.index)
        ex_s = (rs - rfd).dropna()
        v_spy = daily_var_month(ex_s) if cid == "PANICX" else x_rvar(ex_s)
    xL = contiguous(xL)
    lo = pd.Period(t_from, "M")
    hi_c = [spy_m.dropna().index.max(), rf_lab.dropna().index.max(), mkt.dropna().index.max() + 2]
    hi = min(hi_c) if t_to is None else min(pd.Period(t_to, "M"), min(hi_c))
    ts = [pd.Period(only, "M")] if only is not None else list(pd.period_range(lo, hi, freq="M"))
    rows = {}
    mkt_v, rf_v = mkt.to_dict(), rf.to_dict()
    for t in ts:
        a, b, base = t - 1, t, t - 2
        win = pd.period_range(t - 30, t, freq="M")
        r = pd.Series([mkt_v.get(p, np.nan) if p <= base else spy_m.get(p, np.nan) for p in win], index=win)
        f = pd.Series([rf_v.get(p, np.nan) if p <= base else rf_lab.get(p, np.nan) for p in win], index=win)
        if cid == "SLOW":
            xs = x_slow(r, f)
        elif cid == "MKT3":
            xs = x_mkt3(r, f)
        elif cid == "RVAR":
            xs = pd.Series({p: v_spy.get(p, np.nan) for p in (a, b)})
        else:
            ib = ib24(r)
            xs = pd.Series({p: ib.get(p, np.nan) * v_spy.get(p, np.nan) for p in (a, b)})
        hist = xL.loc[:base].to_numpy(float) if len(xL) and base >= xL.index.min() else np.array([])
        tail = [xs.get(a, np.nan), xs.get(b, np.nan)]
        rows[t] = {"x": tail[1], "z": _tail_z(hist, tail, ztype)}
    df = pd.DataFrame.from_dict(rows, orient="index")
    if len(df):
        df.index = pd.PeriodIndex(df.index, freq="M")
    return df


def inputs_S():
    spy = VD.lab_spy_daily()
    rfm = VD.lab_rf_monthly()
    return {"spy_m": (VD.month_ret_from_daily(spy), "lab:spy"), "rf_lab": (rfm, "lab:rf"), "spy_d": (spy, "lab:spy_d"),
            "rf_lab_d": (VD.daily_rf_from_monthly(rfm, spy.index), "lab:rf")}


def conditions_S(inpL=None, inpS=None):
    """모든 조건 S 층 결정 달 z — 시장 조건 넷은 이은 계열 · French t−2 조건(DISP · BSPRD · VSPRD · G2own L)은 L 과 같은 늦춤이라 L 값 그대로."""
    inpL = inpL or inputs_L()
    inpS = inpS or inputs_S()
    L = {k: o for k, (o, _) in inpL.items()}
    S = {k: o for k, (o, _) in inpS.items()}
    out = {}
    for cid in CONDS:
        if CONDS[cid][3] == "sf":
            out[cid] = s_market(cid, L["mkt"], L["rf"], S["spy_m"], S["rf_lab"], mex_d=L["mex_d"], spy_d=S["spy_d"], rf_lab_d=S["rf_lab_d"])["z"]
        else:
            out[cid] = cond_z(cid, {a: L[a] for a in COND_ARGS[cid]})["z"]
    df = pd.DataFrame(out)
    return df.loc[df.index >= pd.Period(S_FROM, "M")]


# ══════════════════════════════════════════════════════════════════════════
#  선견 점검 목록 — 모든 조건(L 9 · S 넷 이음) · x · z 둘 다
# ══════════════════════════════════════════════════════════════════════════
def checks_catalog(inpL=None, inpS=None):
    inpL = inpL or inputs_L()
    cat = []
    for cid in CONDS:
        args = {a: inpL[a] for a in COND_ARGS[cid]}
        cat.append(("L:" + cid, (lambda _c=cid: (lambda **kw: cond_z(_c, kw)[["x", "z"]]))(), args, "L"))
    inpS = inpS or inputs_S()
    for cid in [c for c in CONDS if CONDS[c][3] == "sf"]:
        sfi = {"mkt": inpL["mkt"], "rf": inpL["rf"], "spy_m": inpS["spy_m"], "rf_lab": inpS["rf_lab"], "mex_d": inpL["mex_d"],
               "spy_d": inpS["spy_d"], "rf_lab_d": inpS["rf_lab_d"]}
        cat.append(("S:" + cid, (lambda _c=cid: (lambda mkt, rf, spy_m, rf_lab, mex_d, spy_d, rf_lab_d, _t=None:
                                                s_market(_c, mkt, rf, spy_m, rf_lab, mex_d=mex_d, spy_d=spy_d, rf_lab_d=rf_lab_d, only=_t)))(),
                    sfi, "S"))
    return cat


def run_lookahead(n=VD.LOOKAHEAD_N, names=None, inpL=None, inpS=None):
    out = {}
    for nm, fn, inp, mode in checks_catalog(inpL, inpS):
        if names and nm not in names:
            continue
        t0 = time.time()
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            r = VD.lookahead_check(fn, inp, n=n, mode=mode)
        r["sec"] = round(time.time() - t0, 1)
        out[nm] = r
    return out


# ══════════════════════════════════════════════════════════════════════════
#  연기 · 합성 시험
# ══════════════════════════════════════════════════════════════════════════
def smoke(n=VD.LOOKAHEAD_N):
    inpL, inpS = inputs_L(), inputs_S()
    tests = {
        "conditions_L(9)": (lambda: conditions_L(inpL), ()),
        "conditions_S(9)": (lambda: conditions_S(inpL, inpS), ()),
        "strand_status · share_matrix": (lambda: (strand_status(), share_matrix()), ()),
    }
    out = {nm: VD.blind_smoke(fn, *a) for nm, (fn, a) in tests.items()}
    la = {}
    for nm, r in run_lookahead(n=n, inpL=inpL, inpS=inpS).items():
        la[nm] = {"ok": r["ok"], "n": r["n"], "n_bad": r["n_bad"], "sec": r.get("sec")}
    out["lookahead"] = {"ok": all(v["ok"] for v in la.values()), "sec": sum(v["sec"] or 0 for v in la.values()), "shape": la, "err": None}
    return out


def _fake_french(seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("1926-07", "2026-08", freq="M")
    mkt = pd.Series(rng.normal(0.008, 0.05, len(idx)), index=idx)
    rf = pd.Series(0.003, index=idx)
    days = pd.bdate_range("1926-07-01", "2026-08-31")
    mex_d = pd.Series(rng.normal(0.0003, 0.01, len(days)), index=days)
    ind = pd.DataFrame(rng.normal(0.008, 0.06, (len(idx), 30)), index=idx, columns=["I%02d" % j for j in range(30)])
    nf = pd.DataFrame(25, index=idx, columns=ind.columns)
    yrs = pd.Index(range(1926, 2026))
    beta_a = pd.DataFrame({"Hi 20": 1.4 + rng.normal(0, 0.05, len(yrs)), "Lo 20": 0.6 + rng.normal(0, 0.05, len(yrs))}, index=yrs)
    bm_a = pd.DataFrame({"Hi 30": 1.5 + rng.normal(0, 0.1, len(yrs)), "Lo 30": 0.4 + rng.normal(0, 0.03, len(yrs))}, index=yrs)
    bm_xd = pd.DataFrame({"Hi 30": rng.normal(0.007, 0.06, len(idx)), "Lo 30": rng.normal(0.006, 0.05, len(idx))}, index=idx)
    lab = {(1, 1): "SMALL LoBETA", (1, 5): "SMALL HiBETA", (5, 1): "BIG LoBETA", (5, 5): "BIG HiBETA"}
    cells = [lab.get((a, b), "ME%d BETA%d" % (a, b)) for a in range(1, 6) for b in range(1, 6)]
    mbi = pd.period_range("1963-07", "2026-08", freq="M")
    mb_beme = pd.DataFrame(np.exp(rng.normal(-0.3, 0.3, (len(mbi), 25))), index=mbi, columns=cells)
    mb_nf = pd.DataFrame(30, index=mbi, columns=cells)
    mb_sz = pd.DataFrame(np.exp(rng.normal(5, 1, (len(mbi), 25))), index=mbi, columns=cells)
    op_beme = pd.DataFrame(np.exp(rng.normal(-0.4, 0.2, (len(mbi), 2))), index=mbi, columns=["BIG HiOP", "BIG LoOP"])
    return {"mkt": (mkt, "french:mkt"), "rf": (rf, "french:mkt"), "mex_d": (mex_d, "french:mkt_d"), "ind_m": (ind, "french:lag2"),
            "ind_nf": (nf, "french:lag2"), "beta_a": (beta_a, "french:june"), "bm_a": (bm_a, "french:june"), "bm_xd": (bm_xd, "french:lag2"),
            "mb_beme": (mb_beme, "french:lag2"), "mb_nf": (mb_nf, "french:lag2"), "mb_sz": (mb_sz, "french:lag2"), "op_beme": (op_beme, "french:lag2")}


def _fake_S(seed=5):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2006-01-03", "2026-08-31")
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, len(days)))), index=days)
    rfm = pd.Series(0.002, index=pd.period_range("2005-01", "2026-09", freq="M"))
    return {"spy_m": (VD.month_ret_from_daily(spy), "lab:spy"), "rf_lab": (rfm, "lab:rf"), "spy_d": (spy, "lab:spy_d"),
            "rf_lab_d": (VD.daily_rf_from_monthly(rfm, spy.index), "lab:rf")}


def _st_transforms():
    x = pd.Series(np.r_[np.arange(59.0), 100.0], index=pd.period_range("2000-01", periods=60, freq="M"))
    z = z_expanding(x)
    assert z.iloc[:59].isna().all() and z.iloc[59] == 2.0
    o = z_onesided(pd.Series(np.r_[np.zeros(30), np.ones(40)], index=pd.period_range("2000-01", periods=70, freq="M")))
    assert o.iloc[:59].isna().all() and (o.iloc[59:] >= 0).all()
    d, late = to_decision(pd.Series([1.0, 2.0], index=pd.PeriodIndex(["2000-01", "2000-02"], freq="M")), 2)
    assert str(d.index[0]) == "2000-03" and d.iloc[-1] == 2.0 and bool(late.iloc[-1]) and str(d.index[-1]) == "2000-05"
    zz, st = finalize(pd.Series([np.nan, 1.0, np.nan, 0.5], index=pd.period_range("2000-01", periods=4, freq="M")))
    assert np.isnan(zz.iloc[0]) and zz.iloc[2] == 0.0 and bool(st.iloc[2])
    assert abs(_tail_z(np.arange(60.0), [60.0, 61.0], "expanding") - min(2.0, (61 - np.mean(np.r_[np.arange(60.0), 60, 61])) /
                                                                       np.std(np.r_[np.arange(60.0), 60, 61], ddof=1))) < 1e-12
    return "z 확장 · 한쪽 척도형(정의 전 NaN) · 결정 달 늦춤 + late · stale → 0 · S 층 꼬리 z"


def _st_formulas():
    idx = pd.period_range("2000-01", periods=30, freq="M")
    m = pd.Series(0.01, index=idx)
    rf = pd.Series(0.0, index=idx)
    assert abs(x_slow(m, rf).iloc[11] - 12 * math.log(1.01)) < 1e-12 and np.isnan(x_slow(m, rf).iloc[10])
    assert abs(x_mkt3(m, rf).iloc[2] - 3 * math.log(1.01)) < 1e-12 and np.isnan(x_mkt3(m, rf).iloc[1])
    days = pd.bdate_range("2000-01-03", "2000-03-31")
    ex = pd.Series(0.01, index=days)
    rv = x_rvar(ex)
    assert abs(rv.loc[pd.Period("2000-02", "M")] - math.log(21 * 1e-4)) < 1e-12
    beme = pd.DataFrame({"A": [1.0, 2.0], "B": [0.5, 0.5]}, index=pd.period_range("2000-01", periods=2, freq="M"))
    nf = pd.DataFrame({"A": [10, 10], "B": [10, 30]}, index=beme.index)
    sz = pd.DataFrame({"A": [1.0, 1.0], "B": [1.0, 1.0]}, index=beme.index)
    g = x_g2own_beta(beme, nf, sz, cell="A")
    assert abs(g.iloc[0] - (math.log(1.0) - math.log(0.75))) < 1e-12 and abs(g.iloc[1] - (math.log(2.0) - math.log((20 + 15) / 40))) < 1e-12
    pq = x_pq(pd.DataFrame({"BIG HiOP": [0.4], "BIG LoOP": [0.8]}, index=beme.index[:1]))
    assert abs(pq.iloc[0] - math.log(0.5)) < 1e-12
    gb = g2own_book({"a": 0.5, "b": 0.5}, {"a": 0.2, "b": 0.3, "c": 0.5}, {"a": 10.0, "b": -1.0, "c": 20.0}, {"a": 100.0, "b": 50.0, "c": 100.0})
    want = math.log(0.1) - math.log((0.2 * 0.1 + 0.5 * 0.2) / 0.7)
    assert abs(gb - want) < 1e-12 and g2own_book({"b": 1.0}, {"a": 1.0}, {"a": 1.0, "b": -1.0}, {"a": 1.0, "b": 1.0}) is None
    y = pd.DataFrame(np.tile([0.01, 0.0, -0.01], (14, 1)), index=pd.period_range("2000-01", periods=14, freq="M"), columns=["f1", "f2", "f3"])
    G = g1rel(y, lag=2)
    assert str(G.dropna().index[0]) == "2001-02" and abs(G.dropna().iloc[0]["f1"] - 1.0) < 1e-12 and abs(G.dropna().iloc[0].sum()) < 1e-12
    y2 = y[["f1", "f2"]]
    assert g1rel(y2).dropna(how="all").empty
    return "SLOW · MKT3 · RVAR · G2own(25 칸 VW 시장) · PQ · G2own 책(BE ≤ 0 제외) · G1rel(12달 합 · 상대 z · K ≥ 3 · 늦춤)"


def _st_strands():
    st = {"SLOW": {"status": "primary"}, "DISP": {"status": "twin", "why": "x"}, "BSPRD": {"status": "primary"}, "VSPRD": {"status": "primary"},
          "RVAR": {"status": "primary"}, "PANICX": {"status": "twin"}, "MKT3": {"status": "dropped"}, "G2own": {"status": "primary"}}
    p1, t1 = web("V01", st)
    assert [c for c, _, _ in p1] == ["SLOW", "G2own:S"] and [c for c, *_ in t1] == ["DISP"]
    p3, t3 = web("V03", st)
    assert [c for c, _, _ in p3] == ["RVAR", "G2own:S"] and [c for c, *_ in t3] == ["PANICX"]      # MKT3 삭제는 어디에도 없다
    rows, viol = share_matrix(st)
    assert not viol and set(rows["SLOW"]) == {"V01"}
    st2 = dict(st, DISP={"status": "primary"})
    rows2, viol2 = share_matrix(st2)
    assert rows2["DISP"] == {"V01": -1, "V06": +1} and not viol2
    nofile = strand_status(os.path.join(VD.cache_guard(), "_no_such_lit.json"))
    assert nofile["DISP"]["status"] == "twin" and nofile["SLOW"]["status"] == "primary" and nofile["ATTN_sameday"]["status"] == "twin"
    # 군 배정 — 상관된 셋 = 한 군 · 같은 가족 = 한 군 · 무관한 하나 = 따로
    rng = np.random.default_rng(1)
    base = rng.normal(0, 1, 300)
    Z = pd.DataFrame({"a": base, "b": base + rng.normal(0, 0.3, 300), "c": base + rng.normal(0, 0.4, 300), "d": rng.normal(0, 1, 300),
                      "e": rng.normal(0, 1, 300)})
    cl = assign_clusters(Z, {"d": "fam", "e": "fam"})
    assert cl["a"] == cl["b"] == cl["c"] and cl["d"] == cl["e"] and cl["a"] != cl["d"]
    # 웹 하나의 폐포(검토 고침) — a · c 는 서로 |ρ| < 0.5 여도 웹 밖 b 를 거치면 옛 판(전체 폐포)은 합쳤다 · 웹 {a, c} 만이면 따로
    rp = {"a|b": 0.8, "b|c": 0.8, "a|c": 0.3}
    assert clusters_for(["a", "c"], {}, rp) == ["a", "c"] and clusters_for(["a", "b", "c"], {}, rp) == ["a", "a", "a"]
    assert clusters_for(["x", "y"], {"x": "f", "y": "f"}, {}) == ["x", "x"] and clusters_for(["x", "y"], {}, {}, extra={"x|y": -0.6}) == ["x", "x"]
    pr = pair_rho(Z)
    assert set(pr) >= {"a|b", "d|e"} and abs(pr["a|b"]) > 0.5 and abs(pr["d|e"]) < 0.5
    assert set(CONDS) == set(COND_ARGS) and all(len(v) == 7 for v in CONDS.values())
    for sid, lst in STRANDS.items():
        for c, sg, layer, lid in lst:
            assert sg in (-1, 1) and (c in CONDS or c == "G2own:S") and lid in STRAND_LEVEL
    return "가닥 표 · 〔초록〕 판정(강등 · 삭제는 어디에도 없음) · 파일 없으면 초록만 강등 · 공유 행렬 P3 · 군 배정(상관 셋 · 가족 · 전이 · 웹 하나의 폐포 · 쌍 ρ)"


def _st_lookahead():
    inpL, inpS = _fake_french(), _fake_S()
    res = run_lookahead(n=25, inpL=inpL, inpS=inpS)
    bad = {k: v for k, v in res.items() if not v["ok"]}
    assert not bad and len(res) == len(CONDS) + 4, bad
    zL = conditions_L(inpL)
    zS = conditions_S(inpL, inpS)
    assert list(zL.columns) == list(CONDS) and list(zS.columns) == list(CONDS)
    assert zS.index.min() >= pd.Period(S_FROM, "M") and zS["RVAR"].notna().sum() > 100
    # 늦춤 위반을 심으면 잡는다(SLOW 를 한 달 앞 관측으로)
    leak = lambda mkt, rf: to_decision(x_slow(mkt, rf).shift(-1), 0)[0]
    assert not VD.lookahead_check(leak, {"mkt": inpL["mkt"], "rf": inpL["rf"]}, n=20)["ok"]
    leak2 = lambda ind_m, ind_nf: to_decision(x_disp(ind_m, ind_nf), 1)[0]           # French t−2 인데 t−1 로
    assert not VD.lookahead_check(leak2, {"ind_m": inpL["ind_m"], "ind_nf": inpL["ind_nf"]}, n=20)["ok"]
    return "선견: 조건 9(L) + S 이음 4 모두 통과(합성) · 늦춤 위반(SLOW 한 달 앞 · DISP t−1) 잡음 · L/S 표 모양"


def selftest():
    res, ok = [], True
    for fn in (_st_transforms, _st_formulas, _st_strands, _st_lookahead):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-16s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_cond selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--smoke" in sys.argv:
        for k, v in smoke().items():
            print("  %s %-30s %6ss %s" % ("✓" if v["ok"] else "✗", k, v["sec"], json.dumps(v["shape"], ensure_ascii=False)[:900] if v["ok"] else v["err"]))
        raise SystemExit(0)
    print(__doc__)
