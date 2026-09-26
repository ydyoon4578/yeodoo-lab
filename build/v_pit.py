# -*- coding: utf-8 -*-
"""build/v_pit.py — 배치 V 시점정확 우주: PIT S&P 500 ∪ NASDAQ 100(회사당 한 줄) · 중립 w_B(S&P 500 상한 없는 시총가중) · 시총 규칙 ·
섹터(과거 쪽 가장 가까운 달) · 보유월 수익(y_stop) · 종목 신호 입력(12-2 모멘텀 · FP β̂ · SW β̂ · 재무 원값 · V08 순발행) · 커버리지 F0 · 선견 독 넣기.

설계 원본(구속): vbatch_research.json final.slate.common_frame(universe · neutral_w_B · rebalance) · data_plan(market_cap_rule · sectors · survivorship ·
  coverage_gates_F0) · slate V01 · V02 · V06 · V07 base_signal · 오케스트레이터 결정 8(V08).
  우주 = pit_panel.union_members(회사당 하나 · 재배정 티커 마지막 멤버월 제외 · pit_alias 날짜 인식 키) — 허용 목록 모듈(may_import)을 함수 안에서 부른다.
  2014-06 앞 달(S-E 추정 전용 · D27)은 명단 · 섹터 · 발행사 지도 모두 2014-06 첫 달 값(선견 · 생존 · 공개 — 추정 전용이고 평가 창에 쓰지 않는다).
  중립 w_B = 그달 PIT S&P 500 회사의 시총 비중(상한 없음) · NASDAQ 100 전용 이름은 w_B = 0.
  섹터 = pit_gics_sectors 그달 또는 과거 쪽 가장 가까운 달(미래 달 금지) · 통신 표기 둘(«Telecommunication(s) Services»)은 «Communication Services» 로 이름만 맞춘다(선언) ·
    표에 한 번도 없는 이름(NASDAQ 100 전용 등)은 오늘 분류(index_history.sector → stocks.json · 선견 · 개수 공개). pit_panel._sector(오늘 섹터)는 쓰지 않는다(D24).
  보유월 수익 = 수정종가(총수익 · 랩 가격 계열) 비 · pit_panel.y_stop 규칙(결측 · 마지막 가격 · 짧은 끝) — t_pit 의 «마지막 가격 → 다음 달 0» 은 쓰지 않는다.
  신호 원값(결정일 d = 그달 격자 마지막 날 종가):
    mom12_2  P_{m−1}/P_{m−12} − 1(월말 수정종가 · French Prior_12_2 정의)
    beta_fp  FP w16601 식 15 — 일간 252 거래일 · 관측 ≥ 200 · Dimson 5 지연 · β = 0.5·β_TS + 0.5 · 시장 = SPY 총수익 일간 초과(랩 assets.json) — 복사: u_data PitSide.stock_beta
    beta_sw  L 충실도 쌍둥이 — t_pit.beta_sw(60개월 · 최소 24 · SPY 총수익 월)
    fund     v_fund.fund_signals(E = TTM NI · S = TTM 매출 · BE · 자산 · OP 분자 · ROA · LEV · σROA) — 최초 제출 · 가용일 ≤ d
    ni_v08   v_fund.net_issuance(6월 말만 · 분할 조정)

🚨 수익 · 신호-수익 통계를 계산하지 않는다. 보유월 수익 행렬은 굽기(v_run)가 쓰는 입력이고 이 모듈은 값을 찍지 않는다(연기 시험은 모양만).

  python build/v_pit.py --selftest
"""
from __future__ import annotations

import bisect
import copy
import datetime as _dt
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
import v_fund as VF          # noqa: E402
import v_px_split as VX      # noqa: E402

PIT_FIRST = "2014-06"                                   # index_history · pit_gics_sectors · issuer_map 의 첫 달
FP_WIN, FP_MIN, FP_K, FP_W = 252, 200, 5, 0.5
SEC_ALIAS = {"Telecommunications Services": "Communication Services", "Telecommunication Services": "Communication Services"}


def _norm_sec(s):
    s = (s or "").strip()
    return SEC_ALIAS.get(s, s) or None


def _lagmat(x, K):
    n = len(x)
    M = np.full((n, K + 1), np.nan)
    for k in range(K + 1):
        M[k:, k] = x[:n - k]
    return M


def dimson_ols(y, X):
    """y on [1, X] 최소제곱 — (기울기 합 β_TS, 잔차 sd, n) — 복사: u_data.dimson_ols."""
    n, k = X.shape
    A = np.column_stack([np.ones(n), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ coef
    dof = n - (k + 1)
    sd = float(np.sqrt((res @ res) / dof)) if dof > 0 else np.nan
    return float(coef[1:].sum()), sd, n


class Universe:
    """PIT 우주 한 벌. W = pit_panel.load_world() 꼴(합성 시험은 같은 꼴의 가짜) · L = v_fund.Ledger · spy = 격자 SPY 총수익 지수 ·
    rf_m = {달: 월 무위험} · im_tm = issuer_map tm · secmap = {(티커, 달): 섹터} · sec_today = {티커: 섹터} · vd1 = {가격 키: P_raw 격자 배열} ·
    share_ev = {가격 키: [(날짜, q)]} · rawdb = {가격 키: 원 종가 배열}."""

    def __init__(self, W, L, spy, rf_m, im_tm=None, secmap=None, sec_today=None, vd1=None, share_ev=None, rawdb=None, fxv_tickers=None,
                 lab_fund_ok=True):
        self.W, self.L = W, L
        self.dates = W["dates"]
        self.D = len(self.dates)
        self.PX = W["PX"]
        self.me_idx = W["me"]
        self.spy = np.asarray(spy, float)
        self.rf_m = dict(rf_m)
        self.im_tm = im_tm or {}
        self.secmap = secmap or {}
        self.sec_today = sec_today or {}
        self.vd1 = vd1 or {}
        self.share_ev = share_ev or {}
        self.rawdb = rawdb or {}
        self.fxv_tickers = fxv_tickers or {}
        self.lab_fund_ok = lab_fund_ok
        self.months = [m for m in sorted(self.me_idx) if m >= VD.SE_FROM]
        per = [d[:7] for d in self.dates]
        cnt = {}
        for p in per:
            cnt[p] = cnt.get(p, 0) + 1
        self.rf_d = np.array([(1.0 + float(self.rf_m.get(p, 0.0))) ** (1.0 / cnt[p]) - 1.0 for p in per])
        rm = np.full(self.D, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            rm[1:] = self.spy[1:] / self.spy[:-1] - 1.0
        self.spy_r = rm
        self.mex_d = rm - self.rf_d
        self.XL = _lagmat(self.mex_d, FP_K)
        self._mem, self._me, self._pm, self._sec_months = {}, {}, {}, None
        self._build_month_prices()

    # ── 실자료 ────────────────────────────────────────────────────────────
    @classmethod
    def real(cls, with_vd1=True):
        import pit_panel as PP                                   # 허용 목록(may_import) — 함수 안
        W = PP.load_world()
        if W["dates"] != VD.grid_dates():
            raise SystemExit("🚨 가격 격자가 stocks.json 과 다르다")
        L = VF.Ledger(grid=W["dates"])
        spy = VD.lab_spy_daily().reindex(pd.DatetimeIndex(pd.to_datetime(W["dates"]))).ffill().to_numpy(float)
        rf = {str(k): float(v) for k, v in VD.lab_rf_monthly().items()}
        im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
        G = VD.read_json(VD.lab_path("data/pit_gics_sectors.json"))
        secmap = {}
        for ym, row in (G.get("months") or {}).items():
            for s, ts in (row.get("sec") or {}).items():
                for t in ts:
                    secmap[(t.replace(".", "-"), ym)] = _norm_sec(s)
        H = VD.read_json(VD.lab_path("data/index_history.json"))
        sec_today = {t.replace(".", "-"): _norm_sec(s) for t, s in (H.get("sector") or {}).items()}
        for t, s in (W.get("sector_now") or {}).items():
            sec_today.setdefault(t.replace(".", "-"), _norm_sec(s))
        fxv_t = (VD.read_json(VD.lab_path("data/_fxv/index.json")).get("tickers") or {})
        vd1, sev, rawdb = {}, {}, {}
        R = VX._raw_db()
        for k in (R.get("px") or {}):
            if k in W["PX"]:
                rawdb[k] = VX.raw_db_on_grid(k, W["dates"], R)
        U = cls(W, L, spy, rf, im_tm=im.get("tm") or {}, secmap=secmap, sec_today=sec_today, rawdb=rawdb,
                fxv_tickers={t.replace(".", "-"): v["gid"] for t, v in fxv_t.items()})
        splits = (VD.read_json(VD.lab_path("data/splits.json")).get("co") or {})
        for k in W["PX"]:
            gid = U.gid_of(k.split("@")[0], k, "2026-08") or U.any_gid(k) or U.fxv_tickers.get(k.replace(".", "-"))
            sec = VF.sec_share_series(L, gid) if gid else []
            if with_vd1 and k in W.get("today", set()):
                df = VX.load_vd1(k)
                if df is not None:
                    vd1[k] = VX.p_raw_on_grid(df, W["dates"])
                    sev[k] = VX.split_share_events(k, VX.yahoo_events(df), sec)
                    continue
            if k in rawdb:
                sev[k] = [(d, float(r)) for d, r in ((R.get("basis") or {}).get(k) or {}).get("splits") or []]
            else:
                ev = [(d, float(r)) for d, r in (splits.get(k) or splits.get(k.split("@")[0]) or [])]
                sev[k] = VX.split_share_events(k, ev, sec) if ev else []
        U.vd1, U.share_ev = vd1, sev
        return U

    # ── 월말 가격 ──────────────────────────────────────────────────────────
    def _build_month_prices(self):
        """월말 수정종가(그달 안 마지막 유효 값 · 없으면 NaN) — 모멘텀 · 월 수익용."""
        ms = sorted(self.me_idx)
        self._months_all = ms
        self._mpos = {m: j for j, m in enumerate(ms)}
        ends = np.array([self.me_idx[m] for m in ms])
        starts = np.r_[0, ends[:-1] + 1]
        Pm = {}
        for k, p in self.PX.items():
            p = np.asarray(p, float)
            ok = ~np.isnan(p) & (p > 0)
            pos = np.where(ok, np.arange(len(p)), -1)
            last = np.maximum.accumulate(pos)
            lp = last[ends]
            good = lp >= starts
            a = np.full(len(ms), np.nan)
            a[good] = p[lp[good]]
            Pm[k] = a
        self.Pm = Pm

    def d_of(self, m):
        return self.dates[self.me_idx[m]]

    # ── 명단 ──────────────────────────────────────────────────────────────
    def _eff(self, m):
        return m if m >= PIT_FIRST else PIT_FIRST

    def gid_of(self, t, k, m):
        """(명단 티커, 달) → 발행사 그룹 — issuer_map tm(2014-06 앞은 첫 달 · 뒤는 마지막 달 값) → _fxv 색인 티커 → None."""
        me = self._eff(m)
        for c in (t, t.replace("-", "."), k, (k or "").replace("-", ".")):
            rows = self.im_tm.get(c)
            if not rows:
                continue
            best = None
            for r in rows:
                if r[0] <= me <= r[1] and r[2]:
                    return r[2]
                if r[2] and (best is None or abs(_mdist(r, me)) < abs(_mdist(best, me))):
                    best = r
            if best is not None and me < best[0] and m < PIT_FIRST:
                return best[2]
        return self.fxv_tickers.get(t) or self.fxv_tickers.get((k or "").split("@")[0])

    def any_gid(self, k):
        """가격 키 → 그 티커의 마지막 tm 행 그룹(분할 판별용 SEC 주식수 계열을 찾을 때만 · 날짜 무관)."""
        for c in (k.split("@")[0], k.split("@")[0].replace("-", ".")):
            rows = [r for r in (self.im_tm.get(c) or []) if r[2]]
            if rows:
                return max(rows, key=lambda r: r[1])[2]
        return None

    def fpi_of(self, t, m):
        me = self._eff(m)
        for c in (t, t.replace("-", ".")):
            for r in self.im_tm.get(c) or []:
                if r[0] <= me <= r[1]:
                    return r[7] if len(r) > 7 else r[5]
        return None

    def members(self, m):
        """그달 말 PIT S&P 500 ∪ NASDAQ 100 — [{t, k, gid, spx, ndx, ndx_only, fpi}](회사당 한 줄 · 가격 키가 선 이름)."""
        if m in self._mem:
            return self._mem[m]
        import pit_panel as PP
        W = self.W
        i = self.me_idx[m]
        mm = self._eff(m)
        pairs, n_list = PP.union_members(W, mm, i)
        spx = set(W["lists"]["spx"].get(mm) or [])
        ndx = set(W["lists"]["ndx"].get(mm) or [])
        cik_spx = {PP._dedup_cik(W, t, i) or ("_" + t) for t in spx}
        out = []
        for t, k in pairs:
            c = PP._dedup_cik(W, t, i) or ("_" + t)
            is_spx = t in spx or c in cik_spx
            is_ndx = t in ndx
            out.append({"t": t, "k": k, "gid": self.gid_of(t, k, m), "spx": bool(is_spx), "ndx": bool(is_ndx),
                        "ndx_only": bool(is_ndx and not is_spx), "fpi": self.fpi_of(t, m)})
        self._mem[m] = out
        return out

    # ── 섹터 ──────────────────────────────────────────────────────────────
    def sector(self, t, m, ndx_only=False):
        """그달 또는 과거 쪽 가장 가까운 달의 GICS 섹터(미래 달 금지) · 2014-06 앞은 첫 달(2014-06) 값 · 그래도 없으면 **NASDAQ 100 전용 이름만** 오늘 분류
        (고정 표 · 선견 공개 · 명세 data_plan.sectors · D24) — (섹터, 출처). 🔧 검토 고침(등록 전): S&P 500 이름은 오늘 분류로 채우지 않는다 → (None, "none")
        (섹터 안 선정(VAL · LBS · QLT · V08)에서 빠지고 섹터 띠 · 투영에서는 «없음» 한 칸)."""
        if self._sec_months is None:
            self._sec_months = sorted({ym for (_t, ym) in self.secmap})
        ms = self._sec_months
        me = self._eff(m)
        j = bisect.bisect_right(ms, me) - 1
        while j >= 0:
            s = self.secmap.get((t, ms[j]))
            if s:
                return s, ("pit_first(S-E 선견)" if m < PIT_FIRST else ("pit" if ms[j] == me else "pit_past"))
            j -= 1
        if not ndx_only:
            return None, "none"
        s = self.sec_today.get(t) or self.sec_today.get(t.replace("-", "."))
        return (s, "today(선견)") if s else (None, "none")

    # ── 시총 ──────────────────────────────────────────────────────────────
    def me_row(self, row, m):
        """이름 한 줄의 그달 말 시총(백만 달러) — (값, 방법) | (None, 사유). 규칙은 머리말 · v_px_split."""
        i = self.me_idx[m]
        d = self.dates[i]
        k, gid = row["k"], row["gid"]
        sh = VF.shares_at(self.L, gid, d) if gid else None
        sev = self.share_ev.get(k) or []
        if sh is not None:
            S, basis, src, pe = sh
            if k in self.vd1:
                pr = self.vd1[k][i]
                v = VX.me_value(pr, S, basis, d, sev)
                if v is not None:
                    return v, "vd1"
            if k in self.rawdb:
                pr = self.rawdb[k][i]
                v = VX.me_value(pr, S, basis, d, sev)
                if v is not None:
                    return v, "raw_db"
            p = np.asarray(self.PX[k], float)
            if p[i] == p[i] and p[i] > 0:
                last = self.dates[int(np.where(~np.isnan(p))[0].max())]
                v = VX.me_value(p[i], S, basis, last, sev)       # 조정 가격(계열 끝 기준) × 계열 끝 기준 주식수 — 배당 수준 선견(공개)
                if v is not None:
                    return v, "adj_fallback"
            return None, "no_price"
        if self.lab_fund_ok:
            import pit_panel as PP
            s2 = PP._shares(self.W, row["t"], k, d)                 # 랩 원장(최신 제출 · 90일 지연 · 오늘 기준) — 최초 제출이 없을 때만(선언)
            p = np.asarray(self.PX[k], float)
            if s2 and s2 > 0 and p[i] == p[i] and p[i] > 0:
                return float(p[i]) * float(s2), "lab_fund_fallback"
        return None, "no_shares"

    def me(self, m):
        """{명단 티커: (시총, 방법)} — 그달 명단 전체(값이 서지 않은 이름은 (None, 사유))."""
        if m not in self._me:
            self._me[m] = {r["t"]: self.me_row(r, m) for r in self.members(m)}
        return self._me[m]

    def w_B(self, m):
        """중립 — 그달 PIT S&P 500 회사의 상한 없는 시총가중(시총이 선 이름만 · 합 1) · NASDAQ 100 전용은 0."""
        me = self.me(m)
        mc = {r["t"]: me[r["t"]][0] for r in self.members(m) if r["spx"] and me[r["t"]][0]}
        tot = sum(mc.values())
        return {t: v / tot for t, v in mc.items()} if tot > 0 else {}

    def me_of_ticker(self, t, m):
        """앵커용 — 명단 티커 또는 가격 키가 t 인 줄의 그달 시총(백만 달러) · (값, 방법)."""
        for r in self.members(m):
            if r["t"] == t or r["k"] == t:
                v, how = self.me_row(r, m)
                return v, how
        return None, "not_member"

    # ── 보유월 수익(y_stop) ────────────────────────────────────────────────
    def hold_ret(self, m):
        """결정 달 m → 보유월 m+1 의 이름별 수익 {명단 티커: r | None(결측)} — pit_panel.y_stop 규칙. 🚨 값을 찍지 않는다(굽기 입력)."""
        import pit_panel as PP
        m1 = VD.mshift(m, 1)
        if m1 not in self.me_idx:
            return {}
        i, i1 = self.me_idx[m], self.me_idx[m1]
        out = {}
        for r in self.members(m):
            k = r["k"]
            p = np.asarray(self.PX[k], float)
            if not (p[i] == p[i] and p[i] > 0):
                out[r["t"]] = None
                continue
            ys = PP.y_stop(self.W, k, i, i1)
            if ys == "missing":
                out[r["t"]] = None
                continue
            seg = p[i + 1:i1 + 1]
            ok = np.where(seg == seg)[0]
            out[r["t"]] = float(seg[ok[-1]] / p[i] - 1.0) if len(ok) else 0.0
        return out

    # ── 신호 원값 ──────────────────────────────────────────────────────────
    def month_ret(self, k, m):
        j = self._mpos[m]
        a, b = self.Pm[k][j - 1] if j else np.nan, self.Pm[k][j]
        return float(b / a - 1.0) if (a == a and b == b and a > 0) else None

    def mom12_2(self, k, m):
        j = self._mpos[m]
        if j < 12:
            return None
        a, b = self.Pm[k][j - 12], self.Pm[k][j - 1]
        return float(b / a - 1.0) if (a == a and b == b and a > 0) else None

    def daily_ret(self, k):
        p = np.asarray(self.PX[k], float)
        r = np.full(len(p), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            r[1:] = np.where((p[1:] > 0) & (p[:-1] > 0), p[1:] / p[:-1] - 1.0, np.nan)
        return r

    def beta_fp(self, k, m):
        """FP 일간 β̂ — 결정일까지 252 거래일 · ≥ 200 · Dimson 5 · β = 0.5·β_TS + 0.5(복사: u_data PitSide.stock_beta)."""
        i = self.me_idx[m]
        y = self.daily_ret(k) - self.rf_d
        p0 = max(0, i - FP_WIN + 1)
        Y, X = y[p0:i + 1], self.XL[p0:i + 1]
        ok = np.isfinite(Y) & np.isfinite(X).all(axis=1)
        if ok.sum() < FP_MIN:
            return {"beta": None, "beta_ts": None, "n": int(ok.sum())}
        bts, sd, n = dimson_ols(Y[ok], X[ok])
        return {"beta": FP_W * bts + (1 - FP_W) * 1.0, "beta_ts": bts, "n": int(n)}

    def spy_month(self):
        s = pd.Series(self.spy, index=pd.DatetimeIndex(pd.to_datetime(self.dates)))
        return {str(p): float(v) for p, v in VD.month_ret_from_daily(s).items()}

    def beta_sw(self, k, m, _spy_m=None):
        """L 충실도 쌍둥이 — t_pit.beta_sw(60개월 · 최소 24 · 시장 = SPY 총수익 월)."""
        import t_pit as TP                                       # 허용 목록 — 함수 안
        spy_m = _spy_m or self.spy_month()
        j1 = self._mpos[m]
        j0 = max(1, j1 - TP.BETA_N + 1)
        ms = self._months_all[j0:j1 + 1]
        pm = self.Pm[k]
        r = np.array([pm[j] / pm[j - 1] - 1.0 if (pm[j - 1] == pm[j - 1] and pm[j] == pm[j] and pm[j - 1] > 0) else np.nan
                      for j in range(j0, j1 + 1)])
        mk = np.array([spy_m.get(x, np.nan) for x in ms])
        return TP.beta_sw(r, mk)

    def fund(self, row, m):
        return VF.fund_signals(self.L, row["gid"], self.d_of(m)) if row.get("gid") else None

    def ni_v08(self, row, m):
        """V08 — 6월 말 재구성(T18 규칙) · 6월이 아닌 달은 None(편입 사이 유지는 책의 몫)."""
        if m[5:7] != "06" or not row.get("gid"):
            return None
        return VF.net_issuance(self.L, row["gid"], self.d_of(m), self.share_ev.get(row["k"]) or [])

    def signals(self, m, which=("mom12_2", "beta_fp", "month_ret", "fund", "ni_v08")):
        """그달 이름별 신호 원값 {명단 티커: {…}} — 백분위 · 부호 · 선정은 책(v_books)의 몫."""
        out = {}
        for r in self.members(m):
            k = r["k"]
            rec = {"k": k, "gid": r["gid"], "spx": r["spx"], "ndx_only": r["ndx_only"]}
            sec, how = self.sector(r["t"], m, r["ndx_only"])
            rec["sector"], rec["sector_src"] = sec, how
            if "mom12_2" in which:
                rec["mom12_2"] = self.mom12_2(k, m)
            if "month_ret" in which:
                rec["month_ret"] = self.month_ret(k, m)
            if "beta_fp" in which:
                rec["beta_fp"] = self.beta_fp(k, m)["beta"]
            if "fund" in which:
                rec["fund"] = self.fund(r, m)
            if "ni_v08" in which:
                rec["ni_v08"] = self.ni_v08(r, m)
            out[r["t"]] = rec
        return out

    # ── 커버리지 F0(개수 · 몫만) ──────────────────────────────────────────
    def coverage(self, m):
        """F0 칸 — 그달 명단 수 · 가격 · 시총이 선 몫(개수) · 시총 몫(S&P 500 덮인 시총 ÷ 알려진 S&P 500 시총 근사는 굽기 전 F0 가) ·
        방법별 이름 수 · 섹터 출처별 수. 🚨 수익 없음."""
        mem = self.members(m)
        me = self.me(m)
        n = len(mem)
        how = {}
        for r in mem:
            how[me[r["t"]][1]] = how.get(me[r["t"]][1], 0) + 1
        covered = [r for r in mem if me[r["t"]][0]]
        tot = sum(me[r["t"]][0] for r in covered)
        fb = sum(me[r["t"]][0] for r in covered if me[r["t"]][1] in ("adj_fallback", "lab_fund_fallback"))
        secs = {}
        for r in mem:
            src = self.sector(r["t"], m, r["ndx_only"])[1]
            secs[src] = secs.get(src, 0) + 1
        extreme = sum(1 for r in covered if not (1e1 <= me[r["t"]][0] <= 8e6))     # 1천만 달러 ~ 8조 달러 밖(단위 사고 표지 · F0 에서 0 이어야)
        return {"m": m, "n": n, "n_spx": sum(1 for r in mem if r["spx"]), "n_ndx_only": sum(1 for r in mem if r["ndx_only"]), "me_extreme": extreme,
                "share_names_me": (len(covered) / n) if n else None, "fallback_me_share": (fb / tot) if tot else None,
                "how": how, "sector_src": secs, "no_gid": sum(1 for r in mem if not r["gid"])}

    def survivorship(self, m):
        """명세 data_plan.survivorship — 그달 명단을 «오늘 살아 있는 이름(data/sd)» 과 «뒤에 편출된 이름» 으로 갈라 시총 · 재무 성분이 선 이름 수(개수만)."""
        sig = self.signals(m, which=("fund",))
        me = self.me(m)
        out = {}
        for r in self.members(m):
            grp = "survivor" if r["k"] in (self.W.get("today") or set()) else "later_delisted"
            c = out.setdefault(grp, {"n": 0, "me": 0, "E": 0, "S": 0, "OP": 0, "ROA": 0, "LEV": 0, "sigROA": 0, "BE": 0})
            c["n"] += 1
            c["me"] += int(bool(me[r["t"]][0]))
            f = sig[r["t"]].get("fund") or {}
            for k, key in (("E", "ni_ttm"), ("S", "rev_ttm"), ("OP", "op"), ("ROA", "roa_ttm"), ("LEV", "lev"), ("sigROA", "sig_roa"), ("BE", "be")):
                c[k] += int(f.get(key) is not None)
        return out

    def hygiene(self, months):
        """명세 coverage_gates_F0 위생 — w_B 월수익 대 SPY 총수익 월수익의 상관(≥ 0.98) · 차이 sd(TE).
        🚨 수익 계열을 쓴다 — 등록 F0 · 굽기 프로세스에서만 부른다(자료 층 연기 · selftest 실자료에서는 부르지 않는다)."""
        spy_m = self.spy_month()
        xs, ys = [], []
        for m in months:
            m1 = VD.mshift(m, 1)
            if m1 not in spy_m:
                continue
            wb, hr = self.w_B(m), self.hold_ret(m)
            num = sum(w * hr[t] for t, w in wb.items() if hr.get(t) is not None)
            den = sum(w for t, w in wb.items() if hr.get(t) is not None)
            if den > 0:
                xs.append(num / den)
                ys.append(spy_m[m1])
        if len(xs) < 12:
            return {"rho": None, "te_m": None, "n": len(xs)}
        x, y = np.asarray(xs), np.asarray(ys)
        return {"rho": float(np.corrcoef(x, y)[0, 1]), "te_m": float(np.std(x - y, ddof=1)), "n": len(xs)}

    # ── 선견 독 넣기 ──────────────────────────────────────────────────────
    def poison_after(self, m, rng):
        """결정 달 m(결정일 d) 뒤 자료를 모두 난수로 바꾼 우주 — 가격 · V-D1 · 원 DB 가격 d 뒤 · 원장 가용일 > d · 분할 사건 > d · 섹터 · 명단 > m ·
        랩 원장(기간말 > d − 90)."""
        i = self.me_idx[m]
        d = self.dates[i]
        U = copy.copy(self)
        U.PX = {k: np.r_[np.asarray(p, float)[:i + 1], np.asarray(p, float)[i + 1:] * rng.uniform(0.3, 3.0, len(p) - i - 1)]
                for k, p in self.PX.items()}
        U.W = dict(self.W, PX=U.PX)
        U.vd1 = {k: np.r_[a[:i + 1], a[i + 1:] * rng.uniform(0.3, 3.0, len(a) - i - 1)] for k, a in self.vd1.items()}
        U.rawdb = {k: np.r_[a[:i + 1], a[i + 1:] * rng.uniform(0.3, 3.0, len(a) - i - 1)] for k, a in self.rawdb.items()}
        # 분할 사건 d 뒤를 흔든다 — 원 가격 경로(V-D1)의 이름만. 대체 경로(«조정 가격 × 계열 끝 기준 주식수» ·
        #   랩 원장 대체)는 계열 끝까지의 분할 · 배당 수준을 쓰는 «선언된 선견»(명세 market_cap_rule.fallback)이라 이 흔들기에서 뺀다 —
        #   그 몫은 v_pit.coverage 의 fallback_me_share 로 달마다 보고한다(가격 · 원장 · 섹터 · 명단 독은 모든 이름에 그대로 건다).
        nxt = VD.next_session(self.dates, d)
        sev2 = {}
        for k, ev in self.share_ev.items():
            if k in self.vd1:                                    # V-D1 이름(원 가격 · 전 기간) — 사내 DB 이름은 DB 빈 날에 대체 경로로 내려가 뺀다
                sev2[k] = [(s, (q if s <= d else q * float(rng.uniform(0.5, 4.0)))) for s, q in ev] + [(nxt, 7.0)]
            else:
                sev2[k] = list(ev)
        U.share_ev = sev2
        U.L = PoisonLedger(self.L, d, rng)
        me_ = U._eff(m)
        secs = sorted({s for s in self.secmap.values() if s})
        U.secmap = {kk: (v if kk[1] <= me_ else secs[int(rng.integers(len(secs)))]) for kk, v in self.secmap.items()}
        U._sec_months = None
        lists = {ix: {mm: (v if mm <= me_ else list(reversed(v))[: max(1, len(v) // 2)]) for mm, v in self.W["lists"][ix].items()}
                 for ix in ("spx", "ndx")}
        fund2 = {}
        cut = (_dt.date.fromisoformat(d) - _dt.timedelta(days=90)).isoformat()

        def _pois_ser(ser):
            out = []
            for x in ser:
                if isinstance(x, (list, tuple)) and len(x) == 2 and isinstance(x[1], (int, float)) and str(x[0]) > cut:
                    out.append((x[0], x[1] * float(rng.uniform(0.3, 3.0))))
                else:
                    out.append(x)
            return out
        for t, F in (self.W.get("FUND") or {}).items():
            fund2[t] = {key: (_pois_ser(ser) if isinstance(ser, list) else ser) for key, ser in (F or {}).items()}
        U.W = dict(U.W, lists=lists, FUND=fund2)
        U._mem, U._me = {}, {}
        U._build_month_prices()
        return U


def _mdist(r, me):
    """tm 행과 달 사이 거리(달 수 · 부호 = 행이 뒤면 +)."""
    y, mo = int(me[:4]), int(me[5:7])
    y0, m0 = int(r[0][:4]), int(r[0][5:7])
    return (y0 - y) * 12 + (m0 - mo)


class PoisonLedger:
    """v_fund.Ledger 감싸개 — 가용일이 d 뒤인 기록의 값을 난수 배수로 바꾼다(선견 점검용)."""

    def __init__(self, L, d, rng):
        self.L, self.d, self.rng = L, d, rng
        self._c = {}

    def series(self, gid, key, bucket):
        ck = (gid, key, bucket)
        if ck not in self._c:
            self._c[ck] = [(pe, av, (v * float(self.rng.uniform(0.3, 3.0)) if av > self.d else v), fd)
                           for pe, av, v, fd in self.L.series(gid, key, bucket)]
        return self._c[ck]


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험 — 가짜 세계(pit_panel.load_world 꼴 · union_members 가 읽는 칸 전부)
# ══════════════════════════════════════════════════════════════════════════
def fake_universe(n=30, seed=7):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2009-01-02", "2017-12-29")
    dates = [d.strftime("%Y-%m-%d") for d in days]
    D = len(dates)
    me = VD.month_ends(dates)
    names = ["N%02d" % j for j in range(n)]
    mkt = rng.normal(0.0003, 0.01, D)
    PX = {}
    for j, t in enumerate(names):
        b = 0.5 + j / n
        p = 20 * np.exp(np.cumsum(b * mkt + rng.normal(0, 0.012, D)))
        if j == 3:
            p[1800:] = np.nan
        PX[t] = p
    spy = 100 * np.exp(np.cumsum(mkt))
    lists = {"spx": {}, "ndx": {}}
    for m in sorted(me):
        if m >= PIT_FIRST:
            lists["spx"][m] = [t for j, t in enumerate(names) if j < n - 5 and not (j == 3 and m > dates[1790][:7])]
            lists["ndx"][m] = [t for j, t in enumerate(names) if j >= n - 8]
    W = {"dates": dates, "D": D, "PX": PX, "sector_now": {t: "S%d" % (j % 3) for j, t in enumerate(names)}, "today": set(names),
         "splice": {}, "reassigned": {}, "meta": {}, "cikmap": {t: str(1000 + j) for j, t in enumerate(names)}, "FUND": {}, "me": me,
         "lists": lists, "stops": {}}
    grid = dates
    wide = {"groups": {}}
    for j, t in enumerate(names):
        cells = {}
        q_ends = [x.strftime("%Y-%m-%d") for x in pd.date_range("2009-03-31", "2017-12-31", freq="QE")]
        for e in q_ends:
            filed = (_dt.date.fromisoformat(e) + _dt.timedelta(days=40)).isoformat()
            av = VF.avail_of(e, filed, grid)
            cells.setdefault("sh", {}).setdefault("q", {})[e] = [[av, 100.0 + j, filed, "10-Q", "x", 0, "us-gaap"]]
            cells.setdefault("eq", {}).setdefault("i", {})[e] = [[av, 500.0 + 10 * j, filed, "10-Q", "x", 0, "us-gaap"]]
            cells.setdefault("asset", {}).setdefault("i", {})[e] = [[av, 2000.0, filed, "10-Q", "x", 0, "us-gaap"]]
            cells.setdefault("ni", {}).setdefault("q", {})[e] = [[av, 10.0 + j * 0.1, filed, "10-Q", "x", 0, "us-gaap"]]
            cells.setdefault("rev", {}).setdefault("q", {})[e] = [[av, 100.0, filed, "10-Q", "x", 0, "us-gaap"]]
        wide["groups"]["g%d" % (1000 + j)] = {"cells": cells, "first_xbrl": "2009-01-01"}
    L = VF.Ledger(wide=wide, fxv_index={"groups": {}, "candidates": VF.BASE_TAGS}, fxv_dir=VD.cache_guard(), grid=grid)
    im_tm = {t: [[PIT_FIRST, "2026-09", "g%d" % (1000 + j), 1000 + j, [1000 + j], 0, "fake", 0]] for j, t in enumerate(names)}
    secmap = {(t, m): "S%d" % (j % 3) for j, t in enumerate(names) for m in lists["spx"] if j < n - 5}
    U = Universe(W, L, spy, {m: 0.001 for m in me}, im_tm=im_tm, secmap=secmap, sec_today={t: "S%d" % (j % 3) for j, t in enumerate(names)},
                 lab_fund_ok=False)
    return U, mkt


def _st_members():
    U, _ = fake_universe()
    m = "2015-06"
    mem = U.members(m)
    assert len(mem) == 30 and sum(r["spx"] for r in mem) == 25 and sum(r["ndx_only"] for r in mem) == 5
    wb = U.w_B(m)
    assert len(wb) == 25 and abs(sum(wb.values()) - 1) < 1e-12 and all(not r["ndx_only"] or r["t"] not in wb for r in mem)
    me = U.me(m)
    r0 = mem[0]
    i = U.me_idx[m]
    assert abs(me[r0["t"]][0] - U.PX[r0["k"]][i] * 100.0) < 1e-9 and me[r0["t"]][1] == "adj_fallback"
    mem_se = U.members("2012-03")                                                     # S-E — 첫 달 명단(선언)
    assert len(mem_se) == 30
    assert U.sector("N00", "2012-03")[1].startswith("pit_first") and U.sector("N29", "2015-06", ndx_only=True)[1] == "today(선견)"
    assert U.sector("N29", "2015-06") == (None, "none")                                  # S&P 500 이름은 오늘 분류로 채우지 않는다(D24 · 검토 고침)
    assert U.sector("N01", "2015-06") == ("S1", "pit")
    cv = U.coverage(m)
    assert cv["n"] == 30 and cv["n_spx"] == 25 and cv["share_names_me"] == 1.0 and cv["me_extreme"] == 0
    sv = U.survivorship(m)
    assert sv["survivor"]["n"] == 30 and sv["survivor"]["BE"] == 30
    hy = U.hygiene([x for x in U.months if "2014-07" <= x <= "2016-12"])                # 합성 자료 — 가짜 시장과 같은 요인이라 상관이 높다
    assert hy["n"] == 30 and hy["rho"] is not None and hy["rho"] > 0.5
    return "합집합 · 중립 w_B(S&P 500 만 · 합 1 · NDX 전용 0) · 시총 규칙(대체 경로) · S-E 첫 달 명단 · 섹터(pit · 첫 달 · 오늘 분류) · 커버리지 · 생존 표 · 위생(합성)"


def _st_signals():
    U, mkt = fake_universe()
    m = "2016-03"
    j = U._mpos[m]
    k = "N05"
    assert abs(U.mom12_2(k, m) - (U.Pm[k][j - 1] / U.Pm[k][j - 12] - 1)) < 1e-15
    b_lo, b_hi = U.beta_fp("N02", m)["beta"], U.beta_fp("N27", m)["beta"]
    assert b_lo is not None and b_hi is not None and b_lo < b_hi
    assert U.beta_fp("N03", "2016-03")["beta"] is None                               # 편출 뒤 — 관측 모자람
    f = U.fund(next(r for r in U.members(m) if r["t"] == "N05"), m)
    assert f["be"] == 550.0 and f["ni_ttm"] is not None and abs(f["ni_ttm"] - 4 * 10.5) < 1e-9 and f["rev_ttm"] == 400.0
    hr = U.hold_ret(m)
    assert len(hr) == len(U.members(m)) == 29                                       # N03 은 편출 뒤 명단에 없다
    sw = U.beta_sw("N10", m)
    assert sw is None or np.isfinite(sw)
    sig = U.signals(m)
    assert set(sig) == {r["t"] for r in U.members(m)} and all("sector" in v for v in sig.values())
    return "12-2 모멘텀 · FP β̂(일간 · Dimson 5 · 번호 따라 오름) · 편출 뒤 None · 재무(TTM · BE) · 보유월 · SW 쌍둥이 · 신호 표"


def _st_lookahead():
    U, _ = fake_universe()
    months = [m for m in U.months if "2014-07" <= m <= "2017-10"]

    def comp(Ux, m):
        out = {}
        for r in Ux.members(m):
            v, how = Ux.me_row(r, m)
            f = Ux.fund(r, m) or {}
            out[r["t"]] = (v if v else np.nan, Ux.mom12_2(r["k"], m) or np.nan, Ux.beta_fp(r["k"], m)["beta"] or np.nan,
                           f.get("ni_ttm") or np.nan, f.get("be") or np.nan, Ux.month_ret(r["k"], m) or np.nan,
                           float(hash(Ux.sector(r["t"], m)[0]) % 997))
        wb = Ux.w_B(m)
        out["_wB"] = tuple(sorted(wb.values()))
        return out
    res = VD.pit_lookahead(comp, U, months, lambda Ux, m, rg: Ux.poison_after(m, rg), n=6)
    assert res["ok"], res

    def leak(Ux, m):                                                                 # 다음 달 수익을 쓰는 신호 — 잡혀야 한다
        return {r["t"]: (Ux.month_ret(r["k"], VD.mshift(m, 1)) or np.nan) for r in Ux.members(m)}
    assert not VD.pit_lookahead(leak, U, months, lambda Ux, m, rg: Ux.poison_after(m, rg), n=4)["ok"]
    return "PIT 선견: 시총 · w_B · 모멘텀 · FP β̂ · 재무 · 월 수익 · 섹터가 결정일 뒤 독(가격 · 원장 · 분할 · 섹터 · 명단)에 불변 · 다음 달 수익은 잡음"


def selftest():
    res, ok = [], True
    for fn in (_st_members, _st_signals, _st_lookahead):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_pit selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
