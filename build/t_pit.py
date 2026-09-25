# -*- coding: utf-8 -*-
"""build/t_pit.py — 배치 T S 층 대용(B6) · 내부 회전 추정(B5): 랩 PIT S&P 500 패널 위에서 French 정렬 규칙을 복제한다.

설계 원본: tbatch_research.json final.slate[*].secondary · data_build_plan B5 · B6(저장소 밖). 다시 설계하지 않는다.
패널 = build/pit_panel.load_world()(명단 index_history SPX · 가격 data/sd + data/pit_px.json({i0,p} · 격리 반영) ·
  주식수 tech_backtest.load_fund(fx + fx_pit · 90일 공시 지연) · 이중클래스 회사당 하나 · 재배정 티커 마지막 멤버월 제외 ·
  날짜 인식 가격 키 pit_panel._key(W, t, i)) — 사본을 두지 않는다(두 벌이면 갈린다).
정렬(S&P 500 명단 안 · 개수 분위 · NYSE 문턱 대신 명단 분위 — 한계 공개):
  6월 말 연 1회(French 와 같다) — 60개월 Scholes–Williams 베타(최소 24 · 시장 = SPY 총수익 월) 하위/상위 20% ·
    OP = ttm 영업이익 / 자기자본(French 는 매출 − 매출원가 − 판관비 − 이자 — 이자를 못 뺀다 · 근사) 상위 30% ·
    B/M = 자기자본 / 전년 12월 말 시가총액 상위 30% · 상위/하위 50%(T17 반쪽) · E/P = ttm 순이익 / 12월 시총 ·
    CF/P = (ttm 순이익 + ttm 감가상각) / 12월 시총 · D/P = ttm 주당배당 / 6월 가격 · 모두 상위 30% ·
    NI = log(주식수_6월 / 주식수_1년 전)(분할 되맞춤 계열) < 0.
  매월 말 — 12-2 모멘텀 P_{t−1}/P_{t−12} − 1 상위/하위 10% · 63거래일 일간 수익 분산 하위/상위 20%.
  가중 = 편입 때 시가총액(가격 × 90일 지연 주식수) · 연 1회 바스켓은 1년 동안 흘러간다(사고팔지 않는다) ·
  달 중간 상장폐지는 그달 마지막 가격 · 그달 가격이 하나도 없으면 0 수익 뒤 빠진다(pit_panel.month_rows 와 같다).
  🚨 S 층 선견(등록 §8 · 적대 검토 2026-09-26): 가격은 yfinance auto_adjust(배당 조정)라 편입 날의 가격 수준에 **편입 뒤에 나간 배당**이
     이미 들어 있다(과거 가격 = 원 가격 × 오늘까지 배당 계수). 그래서 편입 날 이후 배당이 큰 종목일수록 B/M · E/P · CF/P · D/P 가 부풀고
     (2016 편입 · 연 3% 배당주면 약 30%) 시가총액 비중은 작아진다 — 미래 배당을 쓴 정렬 · 가중이다. 편입 뒤 가격만 바꾸는
     pit_lookahead_check 는 이것을 못 잡는다(편입 날 가격 수준 자체가 오염). 수익(조정 가격의 비)은 총수익이라 맞다.
     영향: T04 REB · T16 네 축(정렬 변수) → 두 카드의 S 층 통과는 «잠정»(카드 spec s_provisional) · 모든 PIT 바스켓의 VW 비중(작은 왜곡).
     모멘텀 · 분산 · 베타 · OP · NI 정렬 변수는 수익 · 재무 · 주식수만 써서 해당 없다. 재무(fx)는 90일 늦춤이지만 최신 정정 값이다(최초 공시 값 아님 — §8).
보유 기준 사전 베타(T03 S 층 채움): 지금 비중으로 과거 60개월(최소 24)을 되짚은 바스켓 초과수익 on SPY 초과수익 OLS · [0.5, 1.0] 절단 —
  PIT 패널은 2014-06 부터라 바스켓 실현 이력으로는 2016-08 에 60개월이 안 된다(선언).
회전(B5): 편입마다 편도 = ½Σ|w_new − w_흘러간| · 연 편도 = 창 안 편입의 합 / 해(첫 매수 제외) — 수익을 계산하지 않는다.

🚨 이 모듈은 수익 · 신호-수익 통계를 찍지 않는다. 실자료 경로는 t_cards --blind-smoke(표준출력 버림 · 모양만) 안에서만 돈다.

  python build/t_pit.py --selftest
"""
from __future__ import annotations

import io
import math
import os
import sys

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FORM_FROM, FORM_TO = "2016-06", "2026-07"      # 편입 달(연 1회 첫 편입 2016-06 → 보유 2016-07~ · S 창 2016-09~2026-08)
TURN_FROM, TURN_TO = "2016-08", "2026-08"      # B5 회전 창(설계)
BETA_N, BETA_MIN = 60, 24
MOM_FRAC, VAR_FRAC = 0.10, 0.20
VAR_N, VAR_MIN = 63, 50
HOLD_BETA_N, HOLD_BETA_MIN = 60, 24
DUAL_KEEP = {"GOOGL", "FOXA", "NWSA"}

# 정렬 목록 — 이름: (주기, 변수, 몫, 쪽) · 쪽 top = 큰 값 · bot = 작은 값 · lt0 = 음수 전부
SORTS = {
    "beta_lo20": ("annual", "beta_sw", 0.20, "bot"), "beta_hi20": ("annual", "beta_sw", 0.20, "top"),
    "op_hi30": ("annual", "op", 0.30, "top"),
    "bm_hi30": ("annual", "bm", 0.30, "top"), "bm_top50": ("annual", "bm", 0.50, "top"), "bm_bot50": ("annual", "bm", 0.50, "bot"),
    "ep_hi30": ("annual", "ep", 0.30, "top"), "cfp_hi30": ("annual", "cfp", 0.30, "top"), "dp_hi30": ("annual", "dp", 0.30, "top"),
    "ni_lt0": ("annual", "ni", None, "lt0"),
    "mom_hi10": ("monthly", "mom", MOM_FRAC, "top"), "mom_lo10": ("monthly", "mom", MOM_FRAC, "bot"),
    "var_lo20": ("monthly", "var63", VAR_FRAC, "bot"), "var_hi20": ("monthly", "var63", VAR_FRAC, "top"),
}
# L 층 다리(French 파일:칸) → 내부 회전 대리(PIT 정렬) — G5e 순액판. 대응이 없는 다리의 선언된 대리 · 산업 포트폴리오는 0.
LEG_TAU = {
    "prior12_2:Hi PRIOR": "mom_hi10", "prior12_2:Lo PRIOR": "mom_lo10",
    "beta:Lo 20": "beta_lo20", "beta:Hi 20": "beta_hi20", "beta:Lo 20:ew": "beta_lo20",
    "var:Lo 20": "var_lo20", "var:Hi 20": "var_hi20",
    "op:Hi 30": "op_hi30",
    "beme:Hi 30": "bm_hi30", "beme:Hi 20": "bm_hi30", "beme:Hi 30:ew": "bm_hi30",
    "ep:Hi 30": "ep_hi30", "ep:Hi 20": "ep_hi30", "ep:Hi 30:ew": "ep_hi30",
    "cfp:Hi 30": "cfp_hi30", "cfp:Hi 20": "cfp_hi30", "cfp:Hi 30:ew": "cfp_hi30",
    "dp:Hi 30": "dp_hi30", "dp:Hi 20": "dp_hi30", "dp:Hi 30:ew": "dp_hi30",
    "beme:value_half": "bm_top50", "beme:growth_half": "bm_bot50",
    "ni:< 0": "ni_lt0", "ni:Lo 20": "ni_lt0", "ni:< 0:ew": "ni_lt0",
    "ind12:NoDur": 0.0, "ind12:Utils": 0.0, "ind12:Hlth": 0.0,
}


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def mrange(a, b):
    out, m = [], a
    while m <= b:
        out.append(m)
        m = mshift(m, 1)
    return out


def beta_sw(r, m):
    """Scholes–Williams 베타 — (β₋₁ + β₀ + β₊₁)/(1 + 2ρ₁). r · m 은 같은 달 차례의 배열(창 안) · 앞뒤 달 짝은 창 안에서만."""
    r, m = np.asarray(r, float), np.asarray(m, float)
    n = len(r)
    if n < 3:
        return None
    s = np.arange(1, n - 1)                       # s−1, s, s+1 이 모두 창 안
    rr, m0, mm1, mp1 = r[s], m[s], m[s - 1], m[s + 1]
    ok = ~np.isnan(rr) & ~np.isnan(m0) & ~np.isnan(mm1) & ~np.isnan(mp1)
    if ok.sum() < BETA_MIN:
        return None
    rr, m0, mm1, mp1 = rr[ok], m0[ok], mm1[ok], mp1[ok]

    def slope(y, x):
        vx = np.var(x, ddof=1)
        return np.cov(y, x, ddof=1)[0, 1] / vx if vx > 0 else np.nan
    rho = np.corrcoef(m0, mm1)[0, 1]
    b = (slope(rr, mm1) + slope(rr, m0) + slope(rr, mp1)) / (1 + 2 * rho)
    return float(b) if b == b else None


class Panel:
    """랩 PIT S&P 500 패널 위의 정렬 복제. W = pit_panel.load_world() 꼴(합성 selftest 는 같은 꼴의 가짜) ·
    mkt_m = 시장(SPY 총수익) 월 수익 {'YYYY-MM': r} · rf_m = BIL 월 수익(보유 기준 베타의 초과수익)."""

    def __init__(self, W=None, mkt_m=None, rf_m=None):
        import pit_panel as PP
        import tech_backtest as TB
        self.PP, self.TB = PP, TB
        self.W = W if W is not None else PP.load_world()
        W = self.W
        self.dates, self.PX, self.me = W["dates"], W["PX"], W["me"]
        self.months = sorted(self.me)
        self.mpos = {m: j for j, m in enumerate(self.months)}
        self.keys = sorted(self.PX)
        self.kpos = {k: j for j, k in enumerate(self.keys)}
        self.mkt = dict(mkt_m or {})
        self.rf = dict(rf_m or {})
        self._build_month_prices()
        self._mem = {}
        self._var = {}

    # ── 월말 가격 · 월 수익 행렬 ──────────────────────────────────────────
    def _build_month_prices(self):
        M, K = len(self.months), len(self.keys)
        ends = np.array([self.me[m] for m in self.months])
        starts = np.r_[0, ends[:-1] + 1]
        Pm = np.full((K, M), np.nan)
        for j, k in enumerate(self.keys):
            p = np.asarray(self.PX[k], float)
            ok = ~np.isnan(p) & (p > 0)
            pos = np.where(ok, np.arange(len(p)), -1)
            last = np.maximum.accumulate(pos)
            lp = last[ends]
            good = lp >= starts
            Pm[j, good] = p[lp[good]]
        self.Pm = Pm
        R = np.full((K, M), np.nan)
        prev, cur = Pm[:, :-1], Pm[:, 1:]
        with np.errstate(invalid="ignore", divide="ignore"):
            R[:, 1:] = np.where(~np.isnan(prev) & ~np.isnan(cur), cur / prev - 1.0, np.where(~np.isnan(prev), 0.0, np.nan))
        self.R = R                                  # 전달 말 가격이 있고 그달 가격이 없으면 0(그 뒤 빠진다)
        self.dead = ~np.isnan(np.c_[np.full((K, 1), np.nan), Pm[:, :-1]]) & np.isnan(Pm)

    # ── 명단 · 시가총액 ───────────────────────────────────────────────────
    def members(self, mm):
        """그달 말 S&P 500 명단 → {명단 티커: (가격 키, 시가총액)} · 이중클래스 하나 · 재배정 마지막 달 제외 · 날짜 인식 키."""
        if mm in self._mem:
            return self._mem[mm]
        W, PP = self.W, self.PP
        i = self.me[mm]
        lst = W["lists"]["spx"].get(mm) or []
        by_cik = {}
        for t in lst:
            c = W["cikmap"].get(t) or W["cikmap"].get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        keep = []
        for c, ts in by_cik.items():
            if len(ts) == 1 or str(c).startswith("_"):
                keep.extend(ts)
                continue
            k_ = [t for t in ts if t in DUAL_KEEP]
            keep.append(k_[0] if k_ else sorted(ts)[0])
        out = {}
        for t in sorted(keep):
            if t in W["reassigned"] and mm >= W["reassigned"][t].get("last", "9999"):
                continue
            k = PP._key(W, t, i)
            if k is None:
                continue
            p = self.PX[k][i]
            if not (p == p and p > 0):
                continue
            sh = PP._shares(W, t, k, self.dates[i])
            if not sh or sh <= 0:
                continue
            out[t] = (k, float(p) * float(sh))
        self._mem[mm] = out
        self._cover = getattr(self, "_cover", {})
        self._cover[mm] = (len(out), len(keep))
        return out

    def _fund(self, t, k):
        F = self.W["FUND"]
        return F.get(k) or F.get(t) or {}

    def _mc_at(self, t, k, mm):
        if mm not in self.me:
            return None
        i = self.me[mm]
        p = self.PX[k][i]
        if not (p == p and p > 0):
            return None
        sh = self.PP._shares(self.W, t, k, self.dates[i])
        return float(p) * float(sh) if sh and sh > 0 else None

    # ── 정렬 변수 ─────────────────────────────────────────────────────────
    def var_value(self, name, t, k, mm):
        TB = self.TB
        d = self.dates[self.me[mm]]
        F = self._fund(t, k)
        if name == "beta_sw":
            j1 = self.mpos[mm]
            j0 = max(0, j1 - BETA_N + 1)
            ms = self.months[j0:j1 + 1]
            r = self.R[self.kpos[k], j0:j1 + 1]
            m = np.array([self.mkt.get(x, np.nan) for x in ms])
            return beta_sw(r, m)
        if name == "mom":
            j = self.mpos[mm]
            if j < 12:
                return None
            a, b = self.Pm[self.kpos[k], j - 12], self.Pm[self.kpos[k], j - 1]
            return float(b / a - 1.0) if (a == a and b == b and a > 0) else None
        if name == "var63":
            i = self.me[mm]
            p = np.asarray(self.PX[k][max(0, i - VAR_N):i + 1], float)
            with np.errstate(invalid="ignore", divide="ignore"):
                r = p[1:] / p[:-1] - 1.0
            r = r[~np.isnan(r)]
            return float(np.var(r, ddof=1)) if len(r) >= VAR_MIN else None
        if name == "op":
            be = TB.asof_fund(F.get("eq"), d)
            oi = TB.ttm2(F.get("opinc"), F.get("opinc_a"), d)
            return (oi / be) if (be and be > 0 and oi is not None) else None
        if name in ("bm", "ep", "cfp"):
            dec = "%04d-12" % (int(mm[:4]) - 1)
            me_dec = self._mc_at(t, k, dec)
            if not me_dec:
                return None
            if name == "bm":
                be = TB.asof_fund(F.get("eq"), d)
                return (be / me_dec) if (be and be > 0) else None
            ni = TB.ttm2(F.get("ni"), F.get("ni_a"), d)
            if ni is None:
                return None
            if name == "ep":
                return ni / me_dec
            dep = TB.ttm2(F.get("dep"), F.get("dep_a"), d)
            return ((ni + dep) / me_dec) if dep is not None else None
        if name == "dp":
            dps = TB.ttm2(F.get("dps"), F.get("dps_a"), d)
            p = self.PX[k][self.me[mm]]
            return (dps / p) if (dps is not None and p == p and p > 0) else None
        if name == "ni":
            s1 = TB.asof_fund(F.get("sh"), d)
            y0 = "%04d%s" % (int(d[:4]) - 1, d[4:])
            s0 = TB.asof_fund(F.get("sh"), y0)
            return math.log(s1 / s0) if (s1 and s0 and s1 > 0 and s0 > 0) else None
        raise KeyError(name)

    # ── 편입 · 바스켓 경로 ────────────────────────────────────────────────
    def form(self, sort, mm):
        """정렬 하나의 편입(그달 말) → {명단 티커: (가격 키, 비중)} · 비중 = 시가총액 · 합 1."""
        freq, var, frac, side = SORTS[sort]
        mem = self.members(mm)
        vals = []
        for t, (k, mc) in mem.items():
            v = self.var_value(var, t, k, mm)
            if v is not None and v == v and np.isfinite(v):
                vals.append((v, t, k, mc))
        if not vals:
            return {}
        if side == "lt0":
            pick = [x for x in vals if x[0] < 0]
        else:
            vals.sort(key=lambda z: (z[0], z[1]), reverse=(side == "top"))
            n = max(1, int(math.ceil(frac * len(vals))))
            pick = vals[:n]
        tot = sum(x[3] for x in pick)
        return {x[1]: (x[2], x[3] / tot) for x in pick} if tot > 0 else {}

    def form_months(self, sort, a=FORM_FROM, b=FORM_TO):
        freq = SORTS[sort][0]
        ms = [m for m in mrange(a, b) if m in self.me]
        return [m for m in ms if m[5:7] == "06"] if freq == "annual" else ms

    def basket(self, sort, hold_from="2016-07", hold_to="2026-08", forms=None):
        """보유월 VW 바스켓 — 돌려주는 것 dict(ret: {월: r}, hold: {월: {가격 키: 비중(월초)}}, turns: {편입월: 편도}, n: {월: 종목 수})."""
        forms = forms or self.form_months(sort)
        fset = set(forms)
        out, hold, turns, nn = {}, {}, {}, {}
        V = {}
        for m in mrange(hold_from, hold_to):
            prev = mshift(m, -1)
            if prev in fset:
                tgt = self.form(sort, prev)
                if tgt:
                    tot = sum(V.values())
                    if tot > 0:
                        wd = {k: v / tot for k, v in V.items()}
                        wn = {}
                        for _t, (k, w) in tgt.items():
                            wn[k] = wn.get(k, 0.0) + w
                        turns[prev] = 0.5 * sum(abs(wn.get(k, 0.0) - wd.get(k, 0.0)) for k in set(wn) | set(wd))
                    V = {}
                    for _t, (k, w) in tgt.items():
                        V[k] = V.get(k, 0.0) + w
            if not V or m not in self.mpos:
                continue
            j = self.mpos[m]
            tot = sum(V.values())
            hold[m] = {k: v / tot for k, v in V.items()}
            num, NV = 0.0, {}
            for k, v in V.items():
                r = self.R[self.kpos[k], j]
                if r != r:
                    r = 0.0
                num += v * r
                if not self.dead[self.kpos[k], j]:
                    NV[k] = v * (1.0 + r)
            out[m] = num / tot
            nn[m] = len(V)
            V = NV
        return {"ret": out, "hold": hold, "turns": turns, "n": nn}

    def turnover(self, sort, a=TURN_FROM, b=TURN_TO):
        """B5 — 연 편도 회전(창 안 편입 · 첫 매수 제외). 수익을 계산하지 않는다(경로의 비중만 쓴다)."""
        bk = self.basket(sort, hold_from=mshift(a, 1), hold_to=b, forms=[m for m in self.form_months(sort, a, mshift(b, -1))])
        ts = [v for m, v in bk["turns"].items() if a <= m <= b]
        yrs = len(mrange(a, b)) / 12.0
        return {"sort": sort, "tau": (sum(ts) / yrs if yrs > 0 else None), "n_rebal": len(ts), "years": yrs}

    def holding_beta(self, bk, m, n=HOLD_BETA_N, min_n=HOLD_BETA_MIN, lo=0.5, hi=1.0):
        """보유 기준 사전 베타 — 결정 달 m(월말)의 지금 비중(다음 달 월초 비중)으로 m−n+1..m 을 되짚은 바스켓 초과수익 on SPY 초과수익."""
        w = bk["hold"].get(mshift(m, 1))
        if not w or m not in self.mpos:
            return None
        j1 = self.mpos[m]
        j0 = max(1, j1 - n + 1)
        ks = [self.kpos[k] for k in w]
        wv = np.array([w[k] for k in w])
        ys, xs = [], []
        for j in range(j0, j1 + 1):
            mo = self.months[j]
            r = self.R[ks, j]
            ok = ~np.isnan(r)
            if ok.sum() == 0 or mo not in self.mkt or mo not in self.rf:
                continue
            rp = float((wv[ok] * r[ok]).sum() / wv[ok].sum())
            ys.append(rp - self.rf[mo])
            xs.append(self.mkt[mo] - self.rf[mo])
        if len(ys) < min_n:
            return None
        x, y = np.array(xs), np.array(ys)
        b = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
        return float(min(max(b, lo), hi))

    def coverage(self):
        """명단 대비 가격 · 주식수가 선 비율(달마다) — 표본 ÷ 명단(F0 · 수익 없음)."""
        c = getattr(self, "_cover", {})
        return {m: (a / b if b else None) for m, (a, b) in sorted(c.items())}

    def hygiene(self, a="2016-09", b="2026-08"):
        """패널 위생 — 명단 전체 VW 월 수익과 SPY 월 수익의 상관(정상 ≈ 0.98+) · 커버 비율. 실자료에서는 굽기 · 연기 시험에서만."""
        xs, ys = [], []
        for m in mrange(a, b):
            prev = mshift(m, -1)
            if prev not in self.me or m not in self.mpos or m not in self.mkt:
                continue
            mem = self.members(prev)
            j = self.mpos[m]
            tot, num = 0.0, 0.0
            for t, (k, mc) in mem.items():
                r = self.R[self.kpos[k], j]
                num += mc * (0.0 if r != r else r)
                tot += mc
            if tot > 0:
                xs.append(num / tot)
                ys.append(self.mkt[m])
        rho = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 12 else None
        cov = [v for v in self.coverage().values() if v is not None]
        return {"rho_vs_spy": rho, "n_months": len(xs), "cover_min": (min(cov) if cov else None),
                "cover_mean": (float(np.mean(cov)) if cov else None), "ok": (rho is not None and rho >= 0.98)}


def pit_lookahead_check(panel, n=12, seed=20260925, sorts=None):
    """편입 선견 점검 — 정렬마다 무작위 편입 달 n 개(연 1회는 6월 중에서)에서 그달 말 뒤 가격을 난수 배수로 바꾼 패널로
    다시 편입해 종목 · 비중이 같아야 한다(주식수 · 재무는 tech_backtest 의 공시 지연 asof 가 맡는다). 수익을 계산하지 않는다."""
    rng = np.random.default_rng(seed)
    sorts = sorts or list(SORTS)
    W = panel.W
    bad, done = [], 0
    for sort in sorts:
        ms = panel.form_months(sort)
        pick = rng.choice(len(ms), size=min(n, len(ms)), replace=False)
        for j in sorted(pick):
            mm = ms[j]
            i = W["me"][mm]
            PX2 = {}
            for k, p in W["PX"].items():
                q = np.array(p, float, copy=True)
                q[i + 1:] = q[i + 1:] * rng.uniform(0.3, 3.0, len(q) - i - 1)
                PX2[k] = q
            W2 = dict(W, PX=PX2)
            p2 = Panel(W2, panel.mkt, panel.rf)
            a, b = panel.form(sort, mm), p2.form(sort, mm)
            same = set(a) == set(b) and all(abs(a[t][1] - b[t][1]) < 1e-12 and a[t][0] == b[t][0] for t in a)
            done += 1
            if not same:
                bad.append({"sort": sort, "m": mm})
    return {"ok": not bad, "n": done, "n_bad": len(bad), "bad": bad[:5], "seed": seed}


def tau_for(leg, taus):
    """L 층 다리 → 내부 회전 τ(편도 · 연) — LEG_TAU 대리 · 수치면 그 값 · 모르면 None."""
    v = LEG_TAU.get(leg)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    x = taus.get(v)
    return None if x is None else x.get("tau")


# ══════════════════════════════════════════════════════════════════════════
#  합성 자료 시험 — 가짜 세계(pit_panel.load_world 꼴)
# ══════════════════════════════════════════════════════════════════════════
def fake_world(n_names=40, seed=7, start="2009-01-02", end="2026-09-24"):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end)
    dates = [d.strftime("%Y-%m-%d") for d in days]
    D = len(dates)
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    PX, FUND = {}, {}
    names = ["N%02d" % j for j in range(n_names)]
    mkt = rng.normal(0.0003, 0.01, D)
    for j, t in enumerate(names):
        beta = 0.5 + j / n_names
        r = beta * mkt + rng.normal(0.0001 * (j % 5), 0.008 + 0.0004 * j, D)
        p = 20 * np.exp(np.cumsum(r))
        if j == 3:
            p[3000:] = np.nan                                     # 편출 · 상장폐지
        PX[t] = p
        q_ends = [d.strftime("%Y-%m-%d") for d in pd.date_range("2008-03-31", end, freq="QE")]
        sh = [(e, 1e8 * (1 - 0.01 * (j % 3 == 0)) ** k) for k, e in enumerate(q_ends)]
        eq = [(e, 1e9 * (1 + 0.1 * j)) for e in q_ends]
        ni = [(e, 2e7 * (1 + 0.05 * j)) for e in q_ends]
        oi = [(e, 3e7 * (1 + 0.07 * j)) for e in q_ends]
        dep = [(e, 5e6) for e in q_ends]
        dps = [(e, 0.1 * (j % 4)) for e in q_ends]
        FUND[t] = {"sh": sorted(sh, reverse=True), "eq": sorted(eq, reverse=True), "ni": sorted(ni, reverse=True), "ni_a": [],
                   "opinc": sorted(oi, reverse=True), "opinc_a": [], "dep": sorted(dep, reverse=True), "dep_a": [],
                   "dps": sorted(dps, reverse=True), "dps_a": []}
    lists = {"spx": {}, "ndx": {}}
    for m in sorted(me):
        if m >= "2014-06":
            lists["spx"][m] = [t for j, t in enumerate(names) if not (j == 3 and m > dates[2990][:7])]
    W = {"dates": dates, "D": D, "PX": PX, "sector_now": {t: "X" for t in names}, "today": set(names), "splice": {},
         "reassigned": {}, "meta": {}, "cikmap": {}, "FUND": FUND, "me": me, "lists": lists}
    idx = pd.PeriodIndex([d[:7] for d in dates], freq="M")
    mk = pd.Series(mkt, index=idx).groupby(level=0).apply(lambda z: float(np.prod(1 + z) - 1))
    mkt_m = {str(k): float(v) for k, v in mk.items()}
    rf_m = {k: 0.001 for k in mkt_m}
    return W, mkt_m, rf_m


def _st_sw():
    rng = np.random.default_rng(1)
    m = rng.normal(0.01, 0.05, 60)
    r = 1.3 * m + rng.normal(0, 0.01, 60)
    b = beta_sw(r, m)
    assert abs(b - 1.3) < 0.1, b
    assert beta_sw(r[:20], m[:20]) is None
    return "Scholes–Williams 베타(앞뒤 달 짝 · 최소 24)"


def _st_panel():
    W, mkt_m, rf_m = fake_world()
    P = Panel(W, mkt_m, rf_m)
    mem = P.members("2016-06")
    assert len(mem) == 40 and all(v[1] > 0 for v in mem.values())
    lo = P.form("beta_lo20", "2016-06")
    hi = P.form("beta_hi20", "2016-06")
    assert len(lo) == 8 and len(hi) == 8 and abs(sum(w for _, w in lo.values()) - 1) < 1e-12
    lo_ids = {int(t[1:]) for t in lo}
    hi_ids = {int(t[1:]) for t in hi}
    assert np.mean(list(lo_ids)) < np.mean(list(hi_ids))            # 가짜 베타는 번호와 함께 오른다
    ni = P.form("ni_lt0", "2017-06")
    assert ni and all(int(t[1:]) % 3 == 0 for t in ni)                # 주식수가 주는 종목(j % 3 == 0)만
    mom = P.form("mom_hi10", "2018-03")
    assert len(mom) == 4
    # 선견 없음 — 편입 달 뒤 가격을 바꿔도 편입은 같다
    W2, _, _ = fake_world()
    i = W2["me"]["2016-06"]
    for t in W2["PX"]:
        W2["PX"][t] = W2["PX"][t].copy()
        W2["PX"][t][i + 1:] *= np.random.default_rng(3).uniform(0.5, 1.5)
    P2 = Panel(W2, mkt_m, rf_m)
    assert set(P2.form("beta_lo20", "2016-06")) == set(lo) and set(P2.form("var_lo20", "2016-06")) == set(P.form("var_lo20", "2016-06"))
    # 바스켓 경로 — 월초 비중 합 1 · 연 1회 편입 사이에는 흘러간다 · 상장폐지는 빠진다
    bk = P.basket("beta_lo20")
    ms = sorted(bk["ret"])
    assert ms[0] == "2016-07" and ms[-1] == "2026-08"
    for m in ms[:14]:
        assert abs(sum(bk["hold"][m].values()) - 1) < 1e-12
    assert set(bk["turns"]) == {"%d-06" % y for y in range(2017, 2027)}
    j = P.mpos["2016-08"]
    w = bk["hold"]["2016-08"]
    want = sum(v * np.nan_to_num(P.R[P.kpos[k], j]) for k, v in w.items())
    assert abs(bk["ret"]["2016-08"] - want) < 1e-15
    tv = P.turnover("mom_hi10")
    assert tv["tau"] is not None and tv["tau"] >= 0 and tv["n_rebal"] == 119
    hb = P.holding_beta(bk, "2016-08")
    assert hb is not None and 0.5 <= hb <= 1.0
    hy = P.hygiene()
    assert hy["rho_vs_spy"] is not None and hy["n_months"] == 120
    la = pit_lookahead_check(P, n=2)
    assert la["ok"] and la["n"] == 2 * len(SORTS), la
    assert tau_for("ind12:NoDur", {}) == 0.0 and tau_for("op:Hi 30", {"op_hi30": {"tau": 0.4}}) == 0.4 and tau_for("x", {}) is None
    return "패널: 명단 · 시총 · 베타/NI/모멘텀 정렬 · 편입 뒤 가격을 바꿔도 같은 편입(선견 없음) · VW 경로 · 회전 · 보유 기준 베타 · 위생"


def _st_static():
    import ast
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    bad = []
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id == "open":
            if not any(kw.arg == "encoding" for kw in nd.keywords):
                bad.append(nd.lineno)
    assert not bad, bad
    return "open() encoding 정적 점검"


def selftest():
    res, ok = [], True
    for fn in (_st_sw, _st_panel, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            import traceback
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-10s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("t_pit selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
