# -*- coding: utf-8 -*-
"""build/t_cards.py — 배치 T 카드 12장(T01 T02 T03 T04 T05 T08 T12 T13 T15 T16 T17 T18)의 규칙 · 단계 · 대조/쌍둥이 · S 층 대용 · 평가.

설계 원본: tbatch_research.json final.slate(저장소 밖 스크래치) — 규칙 · 단계 · 대조 · 창 · 가설을 그대로 옮긴다. 다시 설계하지 않는다.
틀은 build/t_core.py(펀드틀 · 비용 · 사건 · H1 · H2 · 관문 · 라벨) · 신호는 build/t_signals.py · S 층 PIT 는 build/t_pit.py ·
자료는 build/t_data.py(고정본 · 가용 늦춤 · 선견 점검).

사용자 결정(2026-09-26) — D1 L 층은 사이트에 싣지 않는 기전 증거 층 · D2 S&P 선물 ±5% · 지수 옵션 · 커버드콜 ETF 허용, 교차자산 선물 불허
  → T02 는 측정만(forward_allowed = False · H_T0 구성원은 설계 M1 그대로) · D3 AQR · Cboe · Wurgler 파생 결과는 저장소 밖 · D4 α 는 H_T0 하나.

카드 공통(final.tests)
  · 결정 월 t 에 상태 · 비중을 정하고 t+1 을 든다(t_data.hold_next). 벤치마크 B = French Mkt(Mkt-RF + RF) · T02 · T08 은 S&P 500 TR 이음.
    선물 다리 FUT = B − RF(G5g 판에서는 S&P TR − RF) · 현금 다리 CASH = French RF(무비용).
  · 다리 이름 «파일:칸[:ew]» — F0 기업 수 ≥ 20 가 깨진 마지막 달까지는 그 다리를 쓰는 팔 전체를 «측정 불가»로 자른다(연속 구간 · 상태 선택 편향 방지).
  · 창에 기대는 대조(상수 노출 · 정적 혼합)는 층 창마다 그 창의 실현 비중으로 다시 짓는다(lazy).
  · G5 판: d 비용 2배 · e 편도 회전(내부 τ = t_pit 회전 · LEG_TAU 대리) · f French 2024-12 · 2005-08 판 재실행(판이 없는 파일을 쓰는 카드는
    그 판을 건너뛴다 · T02 · T08 은 해당 없음) · g French 카드는 B = S&P TR(1988-02~) 로 · h 동기 사건 제외.
  · S 층(2016-09~2026-08 · B = SPY TR · RF = BIL · 편도 10bp): 주 대용 = t_pit 정렬 복제 바스켓(또는 규칙이 지수면 SPY) · ETF 쌍둥이 보고 ·
    충실도 관문(카드별) · 구현성 통과 = X(총액) · X(10bp) 가 L-R 과 같은 부호 ∧ 충실도. 10bp 판은 다리 사이 교체 비용에 더해
    PIT 바스켓 자체의 재구성 비용(t_pit 회전 τ × 2 × 10bp × 비중)을 뗀다(적대 검토 2026-09-26 · 등록 §4.3) — 교체만 뗀 판은 보고.
  · G5 «해당 없음»(na)은 카드 spec 이 선언한 칸뿐: c_clean(청정 창 없는 T12 · T18) · g_sptr(French 가 아닌 T02 · T08) · e_turn(T02 — 제3자 계열).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산하거나 찍지 않는다.
   --selftest   합성 자료만(실자료 · 캐시 · 저장소를 읽지 않는다).
   --blind-smoke 실자료로 모든 카드를 끝까지 돌리되 qbatch_core.blind_smoke 안에서(표준출력 버림 · 결과는 모양만 · 파일을 쓰지 않는다) ·
                NPERM 덮어쓰기(작게) · 선견 점검은 설계대로 무작위 t 200개.
   굽기는 build/t_run.py 하나로만 한다 — run_batch(write=True) 는 러너가 판 점검 뒤 건 표(C._RUNNER_TOKEN)가 없으면 멈춘다
   (이 파일의 옛 --run 길은 뺐다 · 적대 검토 2026-09-26).

  python build/t_cards.py --selftest
  python build/t_cards.py --blind-smoke [--card T04]
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import t_core as C           # noqa: E402
import t_data as TD          # noqa: E402
import t_pit as TP           # noqa: E402
import t_signals as TS       # noqa: E402

LOOKAHEAD_N = TD.LOOKAHEAD_N          # 무작위 t 200개(설계)
SMOKE_NPERM = 3                       # 연기 시험 덮어쓰기 — 굽기에서는 t_core.NPERM_MIN 이 막는다
FROM_ETF = "2006-01"                  # S 층 ETF 월 계열을 이 달부터만 만든다


class VintageMissing(Exception):
    """그 판(빈티지)에 없는 French 파일 — G5f 는 그 판을 건너뛴다."""


def hold(s):
    return TD.hold_next(s)


def P(m):
    return pd.Period(m, "M")


# ══════════════════════════════════════════════════════════════════════════
#  자료 문맥 — L 층(Data) · S 층(SData). 카드는 이 두 문맥의 메서드만 쓴다(합성 selftest 는 같은 꼴의 가짜).
# ══════════════════════════════════════════════════════════════════════════
class Data:
    """L 층 자료 — vintage = French 판(None · "2024-12" · "2005-08") · bench = "french" | "sptr"(G5g)."""

    def __init__(self, vintage=None, bench="french"):
        self.vintage, self.bench = vintage, bench
        self._c = {}

    def _memo(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    def _french(self, fid, kind):
        def load():
            try:
                return TD.french(fid, kind, vintage=self.vintage)
            except (KeyError, FileNotFoundError) as e:
                raise VintageMissing("%s@%s" % (fid, self.vintage)) from e
        return self._memo(("fr", fid, kind), load)

    def ff3(self):
        def load():
            df = self._french("ff3_m", "m").copy()
            df["Mkt"] = df["Mkt-RF"] + df["RF"]
            return df
        return self._memo("ff3", load)

    def ff3d(self):
        return self._french("ff3_d", "d")

    def momd(self):
        return self._french("mom_d", "d")["Mom"]

    def leg(self, name):
        """«파일:칸[:ew]» → 월 수익(소수)."""
        parts = name.split(":")
        fid, col = parts[0], parts[1]
        if col in ("value_half", "growth_half"):
            cols = TD.BEME_VALUE if col == "value_half" else TD.BEME_GROWTH
            return self._memo(("half", col), lambda: self._half(cols))
        kind = "ew_m" if (len(parts) > 2 and parts[2] == "ew") else "vw_m"
        return self._french(fid, kind)[col]

    def _half(self, cols):
        try:
            return TD.french_vw_combine("beme", cols, vintage=self.vintage)
        except (KeyError, FileNotFoundError) as e:
            raise VintageMissing("beme@%s" % self.vintage) from e

    def f0_ok(self, name):
        """다리의 기업 수 ≥ 20 (월 bool) — French 다리만. 반쪽은 열 전부."""
        parts = name.split(":")
        if len(parts) < 2 or parts[0] in ("B", "FUT", "CASH", "SP", "BXMD", "TS", "BAB"):
            return None
        fid, col = parts[0], parts[1]
        cols = (TD.BEME_VALUE if col == "value_half" else TD.BEME_GROWTH) if col in ("value_half", "growth_half") else [col]
        n = self._french(fid, "nfirms")
        return (n[cols] >= TD.MIN_FIRMS).all(axis=1)

    def rf(self):
        return self.ff3()["RF"]

    def ff3_vintage(self, v):
        """F0 판별 FAST 불일치 셈용 — FF3 월 자료의 다른 판(없으면 None)."""
        try:
            return self._memo(("ff3v", v), lambda: TD.french("ff3_m", "m", vintage=v))
        except (KeyError, FileNotFoundError):
            return None

    def sptr(self):
        return self._memo("sptr", lambda: TD.sp500_tr_monthly()["ret"])

    def B(self):
        def load():
            if self.bench == "sptr":
                s = TD.sp500_tr_monthly()
                return s.loc[s["src"] == "SP500TR", "ret"]
            return self.ff3()["Mkt"]
        return self._memo(("B", self.bench), load)

    def fut(self):
        return self._memo(("fut", self.bench), lambda: (self.B() - self.rf()).dropna())

    def gspc(self):
        return self._memo("gspc", TD.gspc_daily)

    def shiller(self):
        return self._memo("shiller", TD.shiller)

    def fred(self, sid):
        return self._memo(("fred", sid), lambda: TD.fred(sid))

    def unrate_first(self):
        return self._memo("ur", TD.unrate_first_release)

    def cboe_d(self, name):
        col = {"VIX": "CLOSE"}.get(name, name)
        return self._memo(("cboe", name), lambda: TD.cboe(name)[col])

    def cboe_m(self, name):
        return self._memo(("cboe_m", name), lambda: monthly_ret(self.cboe_d(name)))

    def aqr(self, aid, col):
        return self._memo(("aqr", aid, col), lambda: TD.aqr(aid)[col])

    def wurgler(self):
        return self._memo("wurg", TD.wurgler)

    def sp500tr_d(self):
        return self._memo("sptrd", lambda: TD.yf_hist("^SP500TR")["Close"])


class SData:
    """S 층 자료 — ETF 월 · 일(yfinance 고정본 Adj Close) · PIT 패널(t_pit.Panel · 한 번 짓는다)."""

    def __init__(self):
        self._c = {}

    def _memo(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    def d(self, tk):
        return self._memo(("d", tk), lambda: TD.yf_hist(tk)["Adj Close"].dropna())

    def m(self, tk):
        return self._memo(("m", tk), lambda: monthly_ret(self.d(tk)))

    def spy(self):
        return self.m("SPY")

    def bil(self):
        return self.m("BIL")

    def panel(self):
        def mk():
            s, b = self.spy(), self.bil()
            return TP.Panel(None, {str(k): float(v) for k, v in s.items()}, {str(k): float(v) for k, v in b.items()})
        return self._memo("panel", mk)

    def pit_bk(self, sort):
        return self._memo(("bk", sort), lambda: self.panel().basket(sort))

    def pit(self, sort):
        r = self.pit_bk(sort)["ret"]
        ks = sorted(r)
        return pd.Series([float(r[k]) for k in ks], index=pd.PeriodIndex(ks, freq="M"), dtype=float)

    def holding_beta(self, sort):
        """T03 채움 — 결정 달 t 의 보유 기준 사전 베타(계열 · 결정 색인)."""
        def mk():
            bk, pn = self.pit_bk(sort), self.panel()
            ks, vs = [], []
            for m in sorted(bk["hold"]):
                t = TP.mshift(m, -1)
                b = pn.holding_beta(bk, t)
                if b is not None:
                    ks.append(t)
                    vs.append(b)
            return pd.Series(vs, index=pd.PeriodIndex(ks, freq="M"), dtype=float)
        return self._memo(("hb", sort), mk)


def monthly_ret(daily):
    """일 가격 → 월 수익(그달 마지막 값 대 전달 마지막 값) · 빈 달이 끼면 NaN."""
    m = TS.month_last(pd.Series(daily, dtype=float))
    m = TS.contiguous(m)
    return (m / m.shift(1) - 1.0).dropna()


# ══════════════════════════════════════════════════════════════════════════
#  팔 짓기 도우미
# ══════════════════════════════════════════════════════════════════════════
def legs_frame(D, names, extra=None):
    """다리 이름 → 월 수익 DataFrame. B · FUT · CASH 는 문맥에서, 그 밖은 French 다리 · extra 사전."""
    cols = {}
    for n in names:
        if extra and n in extra:
            cols[n] = extra[n]
        elif n == "B":
            cols[n] = D.B()
        elif n == "FUT":
            cols[n] = D.fut()
        elif n == "CASH":
            cols[n] = D.rf()
        else:
            cols[n] = D.leg(n)
    return pd.concat(cols, axis=1)


def apply_f0(W, D):
    """F0 — 비중이 한 번이라도 있는 French 다리의 기업 수 미달이 마지막으로 난 달까지 팔 전체를 NaN(연속 구간)."""
    if D is None or not hasattr(D, "f0_ok"):
        return W
    W = W.copy()
    for c in W.columns:
        if not (W[c].fillna(0.0).abs() > 0).any():
            continue
        ok = D.f0_ok(c)
        if ok is None:
            continue
        ok = ok.reindex(W.index)
        bad = W.index[(ok == False).to_numpy()]                      # noqa: E712  NaN(자료 밖)은 미달로 세지 않는다
        if len(bad):
            W.loc[W.index <= bad.max(), :] = np.nan
    return W


def overlay_arm(name, w_hold, B, fut, scale=1.0, meta=None):
    """S = B + scale · w · FUT (선물 오버레이) — 선물 매수 쪽은 1982-04 앞 가상 차입 스프레드."""
    w = pd.Series(w_hold, dtype=float)
    W = pd.DataFrame({"B": 1.0, "FUT": scale * w}, index=w.index)
    W.loc[w.isna().to_numpy(), :] = np.nan
    R = pd.concat({"B": B, "FUT": fut}, axis=1)
    return C.arm_weights(name, W, R, B, overlay=("FUT",), meta=meta)


def switch_arm(name, codes_hold, mapping, D, B, extra=None, costless=(), overlay=(), meta=None):
    legs = []
    for k in sorted(mapping):
        for l in mapping[k]:
            if l not in legs:
                legs.append(l)
    W = C.weights_from_codes(pd.Series(codes_hold, dtype=float), mapping, legs)
    W = apply_f0(W, D)
    R = legs_frame(D, legs, extra)
    return C.arm_weights(name, W, R, B, overlay=overlay, costless=costless, meta=meta)


def const_arm(name, weights, D, B, index=None, extra=None, meta=None):
    R = legs_frame(D, list(weights), extra)
    idx = R.dropna(how="any").index if index is None else index
    W = pd.DataFrame({k: float(v) for k, v in weights.items()}, index=idx)
    W = apply_f0(W, D)
    return C.arm_weights(name, W, R, B, meta=meta)


def weights_arm(name, W, D, B, extra=None, overlay=(), costless=(), meta=None):
    W = apply_f0(W, D)
    R = legs_frame(D, list(W.columns), extra)
    return C.arm_weights(name, W, R, B, overlay=overlay, costless=costless, meta=meta)


def static_lazy(rule_arm, D, B, extra=None, weights=None, costless=(), overlay=()):
    """정적 혼합(창의 실현 비중 · 월 되돌림 · 같은 비용) — 창마다 다시 짓는다."""
    def f(a, b):
        R = legs_frame(D, list(rule_arm.W.columns), extra)
        return C.static_mix("C:static", rule_arm.W, R, B, a, b, weights=weights, overlay=overlay, costless=costless,
                            meta={"kind": "정적 혼합(H2 주 대조)"})
    return f


def ann_ir(x):
    x = pd.Series(x, dtype=float).dropna()
    if len(x) < 12 or x.std(ddof=1) == 0:
        return None
    return float(x.mean() * 12 / (x.std(ddof=1) * math.sqrt(12)))


def common_mean(a, b):
    """두 X 계열의 공통 달 평균 (a, b)."""
    df = pd.concat([pd.Series(a, dtype=float), pd.Series(b, dtype=float)], axis=1, join="inner").dropna()
    if len(df) == 0:
        return None, None
    return float(df.iloc[:, 0].mean()), float(df.iloc[:, 1].mean())


def active_rho(a_s, a_b, b_s, b_b, win=C.S_OVERLAP):
    """능동수익 상관 ρ(a_s − a_b, b_s − b_b) — 겹치는 달(창)."""
    x = (pd.Series(a_s, dtype=float) - pd.Series(a_b, dtype=float)).dropna()
    y = (pd.Series(b_s, dtype=float) - pd.Series(b_b, dtype=float)).dropna()
    df = pd.concat([x, y], axis=1, join="inner").dropna()
    df = df.loc[C.in_win(df.index, *win)]
    if len(df) < 24 or df.iloc[:, 0].std() == 0 or df.iloc[:, 1].std() == 0:
        return {"rho": None, "n": int(len(df))}
    return {"rho": float(np.corrcoef(df.iloc[:, 0], df.iloc[:, 1])[0, 1]), "n": int(len(df))}


def S_etf(S, tk, a=FROM_ETF):
    s = S.m(tk)
    return s.loc[s.index >= P(a)]


# ══════════════════════════════════════════════════════════════════════════
#  카드 공통 꼴
# ══════════════════════════════════════════════════════════════════════════
class Card:
    id = ""
    spec = {}
    french = True                          # French 다리 · B 를 쓰는가(G5f · G5g 대상)

    def __init__(self):
        self.cache = {}

    def build_L(self, D, ctx):              # → (arms {이름: Arm}, lazy {이름: f(a, b) → Arm})
        raise NotImplementedError

    def h2_L(self, D, ctx):                 # 교체 카드 — {codes, mapping, R, B, static_weights?, costless?}
        return None

    def g4(self, E, D, ctx):
        return {}

    def build_S(self, S, D, ctx):           # → {이름: Arm} · "rule" = 주 대용
        return {}

    def fidelity(self, SA, LA, S, D, ctx):
        return {"gate": None, "kind": "없음"}

    def checks(self, D, S):                 # 실자료 선견 점검 (이름, 함수, {인자: (자료, 가용 이름)})
        return []

    def f0(self, D, arms):
        return {}


def _spec(**kw):
    kw.setdefault("forward_allowed", True)
    kw.setdefault("h_t0", kw["id"] in C.H_T0_MEMBERS)
    return kw


def _win(full, lit, clean, ool):
    return {"full": full, "lit_seen": lit, "clean": clean, "out_of_lab": ool}


# ══════════════════════════════════════════════════════════════════════════
#  T01 — MTP 속도 오버레이(GHM MED · 규모 ½)
# ══════════════════════════════════════════════════════════════════════════
class T01(Card):
    id = "T01"
    spec = _spec(id="T01", name="MTP 속도 오버레이 (GHM MED · 규모 ½)", family="가격 상태 · 전환점", role="오버레이",
                 status="측정만 · H_T0 구성원", mandate="S&P 선물 ±5%(D2 허용)",
                 windows=_win(("1927-07", "2026-07"), ("1927-07", "2018-12"), ("2019-01", "2026-07"), ("1927-07", "2005-12")))

    def build_L(self, D, ctx):
        f = D.ff3()
        mex = f["Mkt-RF"]
        B, fut = D.B(), D.fut()
        G = TS.ghm(mex)
        self.cache["G"] = G
        med = hold(G["med"])
        arms = {"rule": overlay_arm("rule", med, B, fut, 0.5, {"kind": "규칙 · MED ½"}),
                "T01-S1": overlay_arm("T01-S1", hold(TS.dyn_weight(mex)), B, fut, 0.5, {"kind": "단계 · DYN 속도(측정만)"}),
                "C:slow": overlay_arm("C:slow", hold(G["slow"]), B, fut, 0.5, {"kind": "SLOW 오버레이"}),
                "C:fast": overlay_arm("C:fast", hold(G["fast"]), B, fut, 0.5, {"kind": "FAST 오버레이"}),
                "C:faber": overlay_arm("C:faber", hold(TS.faber(TS.level_from_returns(f["Mkt"]))), B, fut, 0.5, {"kind": "Faber 10개월 SMA"}),
                "C:longonly": overlay_arm("C:longonly", hold(G["med"].clip(upper=0.0)), B, fut, 0.5, {"kind": "롱온리 주식 전용판"}),
                "C:bearonly": overlay_arm("C:bearonly", hold(pd.Series(np.where(G["state"] == TS.BEAR, -1.0, 0.0), index=G.index).where(G["state"].notna())),
                                          B, fut, 0.5, {"kind": "Bear 만 끄는 판"}),
                "C:scale1": overlay_arm("C:scale1", med, B, fut, 1.0, {"kind": "규모 1판"})}

        def const(a, b):
            w = med.loc[C.in_win(med.index, a, b)].dropna()
            e = float(w.mean()) if len(w) else np.nan
            return overlay_arm("C:const", pd.Series(e, index=med.index).where(med.notna()), B, fut, 0.5,
                               {"kind": "상수 노출 쌍둥이(창 실현 평균 w)", "e_bar": e})
        return arms, {"C:const": const}

    def g4(self, E, D, ctx):
        r, c = E["rule"]["LR"]["X"], E["lazy"]["C:const"]["L-R"]["X"]
        a, b = common_mean(r, c)
        ir_r = ann_ir(r)
        ir_s, ir_f = ann_ir(E["arms"]["C:slow"]["X_LR"]), ann_ir(E["arms"]["C:faber"]["X_LR"])
        return {"beats_const": (a is not None and a > b), "ir_gt_slow": (ir_r is not None and ir_s is not None and ir_r > ir_s),
                "ir_gt_faber": (ir_r is not None and ir_f is not None and ir_r > ir_f)}

    def build_S(self, S, D, ctx):
        spy, bil = S.spy(), S.bil()
        mex = (spy - bil).dropna()
        G = TS.ghm(mex)
        self.cache["GS"] = G
        return {"rule": overlay_arm("rule", hold(G["med"]), spy, mex, 0.5, {"kind": "SPY 상태 · S = SPY + ½w(SPY − BIL)"})}

    def fidelity(self, SA, LA, S, D, ctx):
        a = hold(self.cache["G"]["state"])
        b = hold(self.cache["GS"]["state"])
        df = pd.concat([a, b], axis=1, join="inner").dropna()
        df = df.loc[C.in_win(df.index, *C.S_OVERLAP)]
        rate = float((df.iloc[:, 0] == df.iloc[:, 1]).mean()) if len(df) else None
        return {"kind": "상태 일치율(수익 아님)", "agree": rate, "n": int(len(df)), "gate": (rate is not None and rate >= 0.90)}

    def checks(self, D, S):
        return [("ghm", lambda mex: TS.ghm(mex)[["slow", "fast", "state"]], {"mex": (D.ff3()["Mkt-RF"], "french:ff3_m")}),
                ("dyn", lambda mex: TS.dyn_weight(mex), {"mex": (D.ff3()["Mkt-RF"], "french:ff3_m")}),
                ("faber", lambda mkt: TS.faber(TS.level_from_returns(mkt)), {"mkt": (D.ff3()["Mkt"], "french:ff3_m")}),
                ("ghm_S", lambda s, b: TS.ghm((s - b).dropna())["state"], {"s": (S.spy(), "yf:SPY"), "b": (S.bil(), "yf:BIL")})]

    def f0(self, D, arms):
        st = hold(self.cache["G"]["state"]).dropna()
        w = C.layer_windows(self.spec)["L-R"]
        st = st.loc[C.in_win(st.index, *w)]
        return {"regime_months": {TS.STATE_NAMES[k]: int((st == k).sum()) for k in range(4)},
                "fast_disagree": fast_disagreements(D)}


# ══════════════════════════════════════════════════════════════════════════
#  T02 — 관리선물 TSMOM 오버레이(측정만 · D2 로 전방 불가)
# ══════════════════════════════════════════════════════════════════════════
T02_COST, T02_COST4 = 0.02 / 12, 0.04 / 12


class T02(Card):
    id = "T02"
    french = False
    spec = _spec(id="T02", name="관리선물 TSMOM 오버레이 (변동성 맞춤 · 비용 뗌)", family="교차자산 시계열 추세", role="오버레이",
                 status="측정만 · H_T0 구성원(설계 M1) · D2 교차자산 선물 불허 → 전방 후보 아님", mandate="교차자산 선물 — D2 불허",
                 forward_allowed=False, license="AQR: 사전 서면 동의 없이 재배포 · 게시 금지 — 결과 비공개(D3)",
                 publish="비공개(D3 — 설계 기본값 «T02 · T08 결과는 스크래치에만»)",
                 g5e_na="AQR TSMOM 팩터의 내부 회전을 잴 수 없다 — 비용은 고정 2%/년(규칙) · 4%/년(G4)로 뗀다",
                 windows=_win(("1988-01", "2026-05"), ("1988-01", "2012-06"), ("2012-07", "2026-05"), ("1988-01", "2006-12")),
                 extra_windows={"post2017": ("2017-01", "2026-05")})

    @staticmethod
    def _arm(name, B, ts, k, fixed, meta):
        idx = B.index.intersection(ts.index).intersection(k.dropna().index)
        S = B.reindex(idx) + k.reindex(idx) * ts.reindex(idx)
        return C.Arm(name, S, B.reindex(idx), fixed=pd.Series(fixed, index=idx), meta=meta,
                     W=pd.DataFrame({"B": 1.0, "TS": k.reindex(idx)}, index=idx))

    def build_L(self, D, ctx):
        ts = D.aqr("TSMOM", "TSMOM")
        B = D.sptr()
        k = hold(TS.tsmom_scale(ts))
        self.cache["k"], self.cache["ts"] = k, ts
        one = pd.Series(1.0, index=k.index)
        arms = {"rule": self._arm("rule", B, ts, k, T02_COST, {"kind": "규칙 · k·TSMOM − 2%/년"}),
                "C:none": self._arm("C:none", B, ts, 0 * one, 0.0, {"kind": "오버레이 없음(X = 0)"}),
                "C:raw": self._arm("C:raw", B, ts, one, 0.0, {"kind": "AQR 열 원 스케일 · 비용 없음(보고만)"}),
                "C:cost4": self._arm("C:cost4", B, ts, k, T02_COST4, {"kind": "비용 4%/년(G5d · G4 필수)"})}
        return arms, {}

    def g4(self, E, D, ctx):
        x = E["arms"]["C:cost4"]["X_LR"]
        return {"cost4_gt0": bool(pd.Series(x).dropna().mean() > 0)}

    def build_S(self, S, D, ctx):
        spy, bil = S.spy(), S.bil()
        out = {}
        for tk, nm in (("AQMIX", "rule"), ("DBMF", "etf:DBMF"), ("RYMFX", "etf:RYMFX")):
            mf = (S_etf(S, tk) - bil).dropna()
            W = pd.DataFrame({"B": 1.0, "MF": 1.0}, index=mf.index)
            R = pd.concat({"B": spy, "MF": mf}, axis=1)
            out[nm] = C.arm_weights(nm, W, R, spy, overlay=("MF",), meta={"kind": "S = SPY + (%s − BIL)" % tk})
            out[nm].fin = out[nm].fin * 0.0                          # 펀드 순액 — 차입 스프레드 없음(2016+ 이라 어차피 0)
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        mf = (S_etf(S, "AQMIX") - S.bil()).dropna()
        kts = (self.cache["k"] * self.cache["ts"].reindex(self.cache["k"].index)).dropna()
        r = active_rho(mf, 0.0 * mf, kts, 0.0 * kts, win=("2016-09", "2026-05"))
        return {"kind": "ρ(AQMIX − BIL, k·TSMOM) 2016-09~2026-05", **r, "gate": (r["rho"] is not None and r["rho"] >= C.FID_RHO)}

    def checks(self, D, S):
        return [("tsmom_k", lambda ts: TS.tsmom_scale(ts), {"ts": (D.aqr("TSMOM", "TSMOM"), "aqr:TSMOM")})]

    def f0(self, D, arms):
        ts = D.aqr("TSMOM", "TSMOM")
        full = pd.period_range(ts.index.min(), ts.index.max(), freq="M")
        return {"tsmom_months": int(ts.notna().sum()), "tsmom_missing": int(len(full) - ts.notna().sum()), "tsmom_last": str(ts.index.max()),
                "k_first_hold": str(self.cache["k"].first_valid_index())}


# ══════════════════════════════════════════════════════════════════════════
#  T03 — 저베타 소매 + 베타 채움(VW)
# ══════════════════════════════════════════════════════════════════════════
class T03(Card):
    id = "T03"
    spec = _spec(id="T03", name="저베타 소매 + 베타 채움 (VW)", family="저위험 이상현상", role="상시 + 선물 채움",
                 status="측정만 · H_T0 구성원 · 꾸준함 카드", mandate="S&P 선물 +0~5%(D2 허용)",
                 windows=_win(("1968-07", "2026-07"), ("1968-07", "2012-03"), ("2012-04", "2026-07"), ("1968-07", "2008-12")))

    @staticmethod
    def fill_arm(name, leg, D, beta_hold, B, extra=None, meta=None):
        W = pd.DataFrame({leg: 1.0, "FUT": 1.0 - beta_hold}, index=beta_hold.index)
        W.loc[beta_hold.isna().to_numpy(), :] = np.nan
        return weights_arm(name, W, D, B, extra=extra, overlay=("FUT",), meta=meta)

    def build_L(self, D, ctx):
        f = D.ff3()
        B = D.B()
        L = D.leg("beta:Lo 20")
        bh = hold(TS.beta_roll(L - f["RF"], f["Mkt-RF"]))
        self.cache["beta"] = bh
        rule = self.fill_arm("rule", "beta:Lo 20", D, bh, B, meta={"kind": "규칙 · Lo 20 VW + (1 − β̂)·(Mkt − RF)"})
        G = TS.ghm(f["Mkt-RF"])
        reb = hold(G["state"]) == TS.REB
        W1 = rule.W.copy()
        W1["B"] = 0.0
        m = reb.reindex(W1.index).fillna(False).to_numpy() & W1.notna().all(axis=1).to_numpy()
        W1.loc[m, :] = 0.0
        W1.loc[m, "B"] = 1.0
        s1 = weights_arm("T03-S1", W1, D, B, overlay=("FUT",), meta={"kind": "단계 · Rebound 면 B(측정만)"})
        Le = D.leg("beta:Lo 20:ew")
        be = hold(TS.beta_roll(Le - f["RF"], f["Mkt-RF"]))
        Lv = D.leg("var:Lo 20")
        bv = hold(TS.beta_roll(Lv - f["RF"], f["Mkt-RF"]))
        bab = D.aqr("BAB", "USA")
        arms = {"rule": rule, "T03-S1": s1,
                "C:nofill": const_arm("C:nofill", {"beta:Lo 20": 1.0}, D, B, meta={"kind": "채움 없는 Lo 20(구 T10)"}),
                "C:ew": self.fill_arm("C:ew", "beta:Lo 20:ew", D, be, B, meta={"kind": "Lo 20 EW + 채움"}),
                "C:var": self.fill_arm("C:var", "var:Lo 20", D, bv, B, meta={"kind": "VAR Lo 20 + 채움"}),
                "C:bab": weights_arm("C:bab", pd.DataFrame({"B": 1.0, "BAB": 1.0}, index=bab.dropna().index), D, B, extra={"BAB": bab},
                                     overlay=("BAB",), meta={"kind": "AQR BAB 오버레이(롱숏 · 측정만 · 라이선스 제한)"})}
        arms["C:bab"].to = arms["C:bab"].to * 0.0
        arms["C:bab"].fin = arms["C:bab"].fin * 0.0
        return arms, {}

    def g4(self, E, D, ctx):
        a, b = common_mean(E["rule"]["LR"]["X"], E["arms"]["C:nofill"]["X_LR"])
        return {"fill_gt_nofill": (a is not None and a > b)}

    def build_S(self, S, D, ctx):
        spy, bil = S.spy(), S.bil()
        fut = (spy - bil).dropna()
        pit = S.pit("beta_lo20")
        bh = hold(S.holding_beta("beta_lo20"))
        W = pd.DataFrame({"PIT": 1.0, "FUT": 1.0 - bh}, index=bh.index)
        R = pd.concat({"PIT": pit, "FUT": fut}, axis=1)
        out = {"rule": C.arm_weights("rule", W, R, spy, overlay=("FUT",), meta={"kind": "PIT 60개월 SW 베타 하위 20% VW + 보유 기준 β̂ 채움",
                                                                                 "pit_legs": {"PIT": "beta_lo20"}})}
        splv = S_etf(S, "SPLV")
        bs = hold(TS.beta_roll(splv - bil, fut))
        Ws = pd.DataFrame({"E": 1.0, "FUT": 1.0 - bs}, index=bs.index)
        Rs = pd.concat({"E": splv, "FUT": fut}, axis=1)
        out["etf:SPLV"] = C.arm_weights("etf:SPLV", Ws, Rs, spy, overlay=("FUT",), meta={"kind": "SPLV + 채움(60개월 β̂)"})
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        r = active_rho(SA["rule"].S, SA["rule"].B, LA["rule"].S, LA["rule"].B)
        return {"kind": "ρ(S_PIT − SPY, S_French − Mkt)", **r, "gate": (r["rho"] is not None and r["rho"] >= C.FID_RHO)}

    def checks(self, D, S):
        f = D.ff3()
        return [("beta60", lambda y, x: TS.beta_roll(y, x), {"y": ((D.leg("beta:Lo 20") - f["RF"]).dropna(), "french:beta"),
                                                            "x": (f["Mkt-RF"], "french:ff3_m")})]

    def f0(self, D, arms):
        b = self.cache["beta"].dropna()
        return {"beta_months": int(len(b)), "beta_clip_lo": int((b <= 0.5).sum()), "beta_clip_hi": int((b >= 1.0).sum())}


# ══════════════════════════════════════════════════════════════════════════
#  T04 — 네 국면 라우터(Bull = 시장 · 하락 국면 = 퀄리티 · 반등 = 가치)
# ══════════════════════════════════════════════════════════════════════════
IND3 = {"ind12:NoDur": 1 / 3, "ind12:Utils": 1 / 3, "ind12:Hlth": 1 / 3}


class T04(Card):
    id = "T04"
    spec = _spec(id="T04", name="네 국면 라우터 (Bull = 시장 · 하락 국면 = 퀄리티 · 반등 = 가치)", family="국면 → 전략 교체",
                 role="교체(신호 → 전략)", status="측정만 · H_T0 구성원 · H2 측정", mandate="주식 전용",
                 s_provisional="S 층 REB 다리(PIT B/M 상위 30%)의 B/M 이 배당 조정 가격(편입 뒤 배당만큼 과거 가격이 낮다)으로 잰 시가총액을 쓴다 — "
                               "편입 날 이후 배당이 큰 종목일수록 B/M 이 부푸는 선견(S 층 · §8). 구현성 통과는 잠정 — QFWD 수정 등록 전에 분할만 조정한 가격으로 다시 잰다",
                 windows=_win(("1964-07", "2026-07"), ("1964-07", "2018-12"), ("2019-01", "2026-07"), ("1964-07", "2005-12")),
                 arm_windows={"C:def_ind": {"ind_1927": ("1927-07", "2026-07"), "ind_1936": ("1936-01", "2026-07")}})
    DEF, REB_ = "op:Hi 30", "beme:Hi 30"

    def mapping(self, deff=None, reb=None):
        d = deff or {self.DEF: 1.0}
        r = reb or {self.REB_: 1.0}
        return {TS.BULL: {"B": 1.0}, TS.CORR: dict(d), TS.BEAR: dict(d), TS.REB: dict(r)}

    def build_L(self, D, ctx):
        f = D.ff3()
        B = D.B()
        G = TS.ghm(f["Mkt-RF"])
        codes = hold(G["state"])
        self.cache["codes"] = codes
        mp = self.mapping()
        rule = switch_arm("rule", codes, mp, D, B, meta={"kind": "규칙 · Bull B · Correction/Bear OP Hi 30 · Rebound BE-ME Hi 30"})
        mp1 = {TS.BULL: {"B": 1.0}, TS.CORR: {self.DEF: 1.0}, TS.BEAR: {self.DEF: 1.0}, TS.REB: {"B": 1.0}}
        slow_codes = hold(pd.Series(np.where(G["slow"] > 0, 0, 1), index=G.index).where(G["slow"].notna()))
        arms = {"rule": rule,
                "T04-S1": switch_arm("T04-S1", codes, mp1, D, B, meta={"kind": "단계 S1 · Correction/Bear → DEF"}),
                "C0": const_arm("C0", {"B": 1.0}, D, B, meta={"kind": "항상 B(X = 0)"}),
                "C:lo_prior": switch_arm("C:lo_prior", codes, self.mapping(reb={"prior12_2:Lo PRIOR": 1.0}), D, B, meta={"kind": "REB = Lo PRIOR"}),
                "C:def_beta": switch_arm("C:def_beta", codes, self.mapping(deff={"beta:Lo 20": 1.0}), D, B, meta={"kind": "DEF = BETA Lo 20"}),
                "C:def_ind": switch_arm("C:def_ind", codes, self.mapping(deff=IND3), D, B, meta={"kind": "DEF = NoDur · Utils · Hlth 동일가중"}),
                "C:slow_only": switch_arm("C:slow_only", slow_codes, {0: {"B": 1.0}, 1: {self.DEF: 1.0}}, D, B,
                                          meta={"kind": "SLOW 만 쓰는 라우터(S+ → B · S− → DEF)"})}
        return arms, {"C:static": static_lazy(rule, D, B)}

    def h2_L(self, D, ctx):
        mp = self.mapping()
        return {"codes": self.cache["codes"], "mapping": mp, "R": legs_frame(D, ["B", self.DEF, self.REB_]), "B": D.B()}

    def g4(self, E, D, ctx):
        h = E["h2"] or {}
        rm = E["rule"]["LR"]["bundle"].get("rebound_miss") or {"ok": True}
        return {"h2_delta_gt0": (h.get("delta_obs") is not None and h["delta_obs"] > 0),
                "h2_rank_ge90": (h.get("rank") is not None and h["rank"] >= C.RANK_MIN), "rebound_miss_ok": bool(rm.get("ok", True))}

    def build_S(self, S, D, ctx):
        spy, bil = S.spy(), S.bil()
        G = TS.ghm((spy - bil).dropna())
        codes = hold(G["state"])
        self.cache["codes_S"] = codes
        ex = {"B": spy, "DEF": S.pit("op_hi30"), "REB": S.pit("bm_hi30"), "QUAL": S_etf(S, "QUAL"), "RPV": S_etf(S, "RPV"),
              "IVE": S_etf(S, "IVE")}
        R = pd.concat(ex, axis=1)

        def arm(nm, d, r, kind):
            mp = {TS.BULL: {"B": 1.0}, TS.CORR: {d: 1.0}, TS.BEAR: {d: 1.0}, TS.REB: {r: 1.0}}
            W = C.weights_from_codes(codes, mp, ["B", d, r])
            meta = {"kind": kind}
            if d == "DEF":
                meta["pit_legs"] = {"DEF": "op_hi30", "REB": "bm_hi30"}
            return C.arm_weights(nm, W, R, spy, meta=meta)
        return {"rule": arm("rule", "DEF", "REB", "SPY 상태 · DEF = PIT OP 상위 30% · REB = PIT B/M 상위 30%"),
                "etf:QUAL_RPV": arm("etf:QUAL_RPV", "QUAL", "RPV", "DEF = QUAL · REB = RPV"),
                "etf:QUAL_IVE": arm("etf:QUAL_IVE", "QUAL", "IVE", "DEF = QUAL · REB = IVE")}

    def fidelity(self, SA, LA, S, D, ctx):
        spy, mkt = S.spy(), D.ff3()["Mkt"]
        a = active_rho(S.pit("op_hi30"), spy, D.leg(self.DEF), mkt)
        b = active_rho(S.pit("bm_hi30"), spy, D.leg(self.REB_), mkt)
        ok = all(x["rho"] is not None and x["rho"] >= C.FID_RHO for x in (a, b))
        return {"kind": "다리별 ρ(PIT − SPY, French − Mkt)", "DEF": a, "REB": b, "gate": ok}

    def checks(self, D, S):
        return [("ghm", lambda mex: TS.ghm(mex)["state"], {"mex": (D.ff3()["Mkt-RF"], "french:ff3_m")}),
                ("ghm_S", lambda s, b: TS.ghm((s - b).dropna())["state"], {"s": (S.spy(), "yf:SPY"), "b": (S.bil(), "yf:BIL")})]

    def f0(self, D, arms):
        c = self.cache["codes"].dropna()
        c = c.loc[C.in_win(c.index, *self.spec["windows"]["full"])]
        return {"regime_months": {TS.STATE_NAMES[k]: int((c == k).sum()) for k in range(4)},
                "def_ind_first": (str(arms["C:def_ind"].S.first_valid_index()) if arms["C:def_ind"].S.notna().any() else None)}


# ══════════════════════════════════════════════════════════════════════════
#  T05 — 모멘텀 + 패닉 중립 단계
# ══════════════════════════════════════════════════════════════════════════
class T05(Card):
    id = "T05"
    spec = _spec(id="T05", name="모멘텀 + 패닉 중립 단계 (약세장 × 고변동이면 시장으로)", family="모멘텀 상태 교체",
                 role="교체(신호 → 중립)", status="측정만 · H_T0 구성원 · H2 측정", mandate="주식 전용",
                 windows=_win(("1929-07", "2026-07"), ("1929-07", "2013-03"), ("2013-04", "2026-07"), ("1929-07", "2008-12")))
    MOM, VAL = "prior12_2:Hi PRIOR", "beme:Hi 30"

    def build_L(self, D, ctx):
        f = D.ff3()
        B = D.B()
        Pn = TS.panic(f["Mkt"], D.ff3d()["Mkt-RF"])
        codes = hold(Pn["panic"])
        self.cache["codes"], self.cache["ib"] = codes, hold(Pn["ib"])
        mp = {0: {self.MOM: 1.0}, 1: {"B": 1.0}}
        rule = switch_arm("rule", codes, mp, D, B, meta={"kind": "규칙 · PANIC → B · 아니면 Hi PRIOR"})
        k = hold(TS.bsc_scale(D.momd()))
        Wb = pd.DataFrame({"B": 1.0 - k, self.MOM: k}, index=k.index)
        Wb.loc[k.isna().to_numpy(), :] = np.nan
        G = TS.ghm(f["Mkt-RF"])
        tr = hold(pd.Series(np.where(G["slow"] < 0, 1, 0), index=G.index).where(G["slow"].notna()))
        arms = {"rule": rule,
                "C0": const_arm("C0", {self.MOM: 1.0}, D, B, meta={"kind": "항상 MOM"}),
                "C:ib_val": switch_arm("C:ib_val", self.cache["ib"], {0: {self.MOM: 1.0}, 1: {self.VAL: 1.0}}, D, B,
                                       meta={"kind": "설계 원판 IB → VAL(BE-ME Hi 30)"}),
                "C:bsc": weights_arm("C:bsc", Wb, D, B, meta={"kind": "BSC 위험관리 쌍둥이 min(1, σ*/σ̂)"}),
                "C:trend12": switch_arm("C:trend12", tr, mp, D, B, meta={"kind": "12개월 시장 추세 부호 상태판"})}
        return arms, {"C:static": static_lazy(rule, D, B)}

    def h2_L(self, D, ctx):
        return {"codes": self.cache["codes"], "mapping": {0: {self.MOM: 1.0}, 1: {"B": 1.0}},
                "R": legs_frame(D, [self.MOM, "B"]), "B": D.B()}

    def g4(self, E, D, ctx):
        h = E["h2"] or {}
        w = self.spec["windows"]["full"]
        c = self.cache["codes"]
        R = legs_frame(D, [self.MOM, "B"])
        m = (c == 1).reindex(R.index).fillna(False) & pd.Series(C.in_win(R.index, *w), index=R.index)
        d = (R[self.MOM] - R["B"])[m.to_numpy()].dropna()
        return {"h2_delta_gt0": (h.get("delta_obs") is not None and h["delta_obs"] > 0),
                "h2_rank_ge90": (h.get("rank") is not None and h["rank"] >= C.RANK_MIN),
                "panic_mom_minus_b_lt0": (len(d) > 0 and float(d.mean()) < 0)}

    def build_S(self, S, D, ctx):
        spy = S.spy()
        Pn = TS.panic(spy, S.d("SPY").pct_change().dropna())
        codes = hold(Pn["panic"])
        R = pd.concat({"B": spy, "MOM": S.pit("mom_hi10"), "MTUM": S_etf(S, "MTUM"), "SPMO": S_etf(S, "SPMO")}, axis=1)
        out = {}
        for nm, leg, kind in (("rule", "MOM", "PIT 12-2 모멘텀 상위 10% VW + PANIC(SPY)"), ("etf:MTUM", "MTUM", "MTUM + PANIC"),
                              ("etf:SPMO", "SPMO", "SPMO + PANIC")):
            W = C.weights_from_codes(codes, {0: {leg: 1.0}, 1: {"B": 1.0}}, [leg, "B"])
            out[nm] = C.arm_weights(nm, W, R, spy, meta=dict({"kind": kind}, **({"pit_legs": {"MOM": "mom_hi10"}} if leg == "MOM" else {})))
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        r = active_rho(S.pit("mom_hi10"), S.spy(), D.leg(self.MOM), D.ff3()["Mkt"])
        return {"kind": "ρ(PIT − SPY, Hi PRIOR − Mkt)", **r, "gate": (r["rho"] is not None and r["rho"] >= C.FID_RHO)}

    def checks(self, D, S):
        return [("panic", lambda mkt, day: TS.panic(mkt, day)[["ib", "panic"]],
                 {"mkt": (D.ff3()["Mkt"], "french:ff3_m"), "day": (D.ff3d()["Mkt-RF"], "french:ff3_d")}),
                ("bsc", lambda mom: TS.bsc_scale(mom), {"mom": (D.momd(), "french:mom_d")}),
                ("panic_S", lambda m, d: TS.panic(m, d)["panic"], {"m": (S.spy(), "yf:SPY"), "d": (S.d("SPY").pct_change().dropna(), "yf:SPY")})]

    def f0(self, D, arms):
        c = self.cache["codes"].dropna()
        lit, clean = self.spec["windows"]["lit_seen"], self.spec["windows"]["clean"]
        return {"panic_months_full": int((c.loc[C.in_win(c.index, *self.spec["windows"]["full"])] == 1).sum()),
                "panic_months_post_lit": int((c.loc[C.in_win(c.index, *clean)] == 1).sum()),
                "panic_months_lit": int((c.loc[C.in_win(c.index, *lit)] == 1).sum())}


# ══════════════════════════════════════════════════════════════════════════
#  T08 — 조건부 커버드콜(하락 국면만 BXMD · VRP 단계)
# ══════════════════════════════════════════════════════════════════════════
BXM_BETA = 0.62                       # Cboe BXM 팩트시트(고정값)


def third_friday(y, m):
    d = pd.Timestamp(y, m, 1)
    fri = d + pd.Timedelta(days=(4 - d.weekday()) % 7)
    return fri + pd.Timedelta(days=14)


class T08(Card):
    id = "T08"
    french = False
    spec = _spec(id="T08", name="조건부 커버드콜 (하락 국면만 BXMD · 실현분산 단계)", family="옵션 변동성 위험프리미엄",
                 role="교체(신호 → 전략) · 가족 탐침", status="측정만 · H_T0 구성원", mandate="지수 옵션 · 커버드콜 ETF(D2 허용)",
                 license="Cboe: 개인 · 비상업 — 원자료 · 파생 NAV 비공개(D3)",
                 publish="비공개(D3 — 설계 기본값 «T02 · T08 결과는 스크래치에만»)",
                 g5e_scope="S&P ↔ BXMD 교체 회전만 — BXMD 는 총액 지수(콜 매도 · 롤 거래비용 없음 · 출시 전 역산)라 옵션 롤 회전 · 비용은 G5e 와 X 에 없다",
                 forward_book="XYLD(또는 명시한 지수 옵션 오버레이) — BXMD 지수는 투자 불가 · Cboe 비상업(D3)이라 전방 장부가 아니다",
                 windows=_win(("1986-07", "2026-08"), ("1986-07", "2014-12"), ("2015-01", "2026-08"), ("1986-07", "2026-08")))

    @staticmethod
    def state_input(D):
        """상태 입력(선견 규율) — ^SP500TR 월 수익(1988-02~) · 그 앞은 (SPX_t + D_{t−6}/12)/SPX_{t−1} − 1 에서 French RF 를 뺀다.
        수익(B)은 설계의 S&P TR 이음(D_t/12) 그대로 · 상태만 Shiller D 의 선언 늦춤(6개월)을 지킨다(구현 해석 · 등록 문서에 적는다)."""
        return (TS.sp_state_ret(D.cboe_d("SPX"), D.shiller()["D"], D.sp500tr_d()) - D.rf()).dropna()

    def build_L(self, D, ctx):
        sp = D.sptr()
        rf = D.rf()
        G = TS.ghm(self.state_input(D))
        down = pd.Series(np.where(G["state"].isin([TS.CORR, TS.BEAR]), 1, 0), index=G.index).where(G["state"].notna())
        codes = hold(down)
        self.cache["codes"] = codes
        bx = D.cboe_m("BXMD")
        ex = {"SP": sp, "BXMD": bx, "FUT": (sp - rf).dropna()}
        mp = {0: {"SP": 1.0}, 1: {"BXMD": 1.0}}
        rule = switch_arm("rule", codes, mp, D, sp, extra=ex, meta={"kind": "규칙 · Correction/Bear → BXMD · 아니면 S&P TR"})
        v = TS.vrp(D.cboe_d("VIX"), D.gspc())
        s1c = hold((down.reindex(v.index) * (v > 0).astype(float)).where(down.reindex(v.index).notna()))
        Wd = C.weights_from_codes(codes, {0: {"SP": 1.0, "FUT": 0.0}, 1: {"SP": 1.0, "FUT": BXM_BETA - 1.0}}, ["SP", "FUT"])
        arms = {"rule": rule,
                "T08-S1": switch_arm("T08-S1", s1c, mp, D, sp, extra=ex, meta={"kind": "단계 · VRP > 0 일 때만 BXMD(VIX 1990+)"}),
                "C:derisk": weights_arm("C:derisk", Wd, D, sp, extra=ex, overlay=("FUT",), meta={"kind": "선물 디리스크 β 0.62(G4 필수)"}),
                "C:always_bxmd": const_arm("C:always_bxmd", {"BXMD": 1.0}, D, sp, extra=ex, meta={"kind": "항상 BXMD"}),
                "C:always_sp": const_arm("C:always_sp", {"SP": 1.0}, D, sp, extra=ex, meta={"kind": "항상 S&P(X = 0)"}),
                "C:roll": self.roll_arm(D, codes, sp)}
        self.cache["ex"] = ex
        return arms, {}

    def roll_arm(self, D, codes, sp):
        """롤 날짜(셋째 금요일) 교체판 — 결정 t 말 → 달 t+1 의 셋째 금요일 종가에 바꾼다(그 전까지 옛 국면 · 일간 ^SP500TR · BXMD)."""
        a = D.sp500tr_d().dropna()
        b = D.cboe_d("BXMD").dropna()
        df = pd.concat({"SP": a, "BX": b}, axis=1, join="inner").dropna()
        rr = df / df.shift(1) - 1.0
        rr = rr.iloc[1:]
        S, TF = {}, {}
        months = rr.index.to_period("M")
        have = set(df.index.to_period("M"))
        for m in sorted(set(months)):
            if (m - 1) not in have:                                   # 첫 달은 전달 말 종가가 없어 불완전 — 뺀다
                continue
            if m - 1 not in codes.index or m not in codes.index:
                continue
            old, new = codes.get(m - 1), codes.get(m)
            if old != old or new != new:
                continue
            seg = rr[months == m]
            fr = third_friday(m.year, m.month)
            pre = seg.index <= fr
            ro = seg["BX"] if old == 1 else seg["SP"]
            rn = seg["BX"] if new == 1 else seg["SP"]
            S[m] = float(np.prod(1 + ro[pre]) * np.prod(1 + rn[~pre]) - 1)
            TF[m] = 2.0 if old != new else 0.0
        S = pd.Series(S, dtype=float).sort_index()
        return C.Arm("C:roll", S, sp.reindex(S.index), tf=pd.Series(TF, dtype=float).reindex(S.index),
                     meta={"kind": "롤 날짜(셋째 금요일) 교체판 · 1988-02~(일간 TR)"})

    def h2_L(self, D, ctx):
        ex = self.cache["ex"]
        return {"codes": self.cache["codes"], "mapping": {0: {"SP": 1.0}, 1: {"BXMD": 1.0}},
                "R": pd.concat({"SP": ex["SP"], "BXMD": ex["BXMD"]}, axis=1), "B": ex["SP"]}

    def g4(self, E, D, ctx):
        a, b = common_mean(E["rule"]["LR"]["X"], E["arms"]["C:derisk"]["X_LR"])
        h = E["h2"] or {}
        return {"beats_derisk": (a is not None and a > b), "h2_delta_gt0": (h.get("delta_obs") is not None and h["delta_obs"] > 0),
                "h2_rank_ge90": (h.get("rank") is not None and h["rank"] >= C.RANK_MIN)}

    def build_S(self, S, D, ctx):
        spy, bil = S.spy(), S.bil()
        G = TS.ghm((spy - bil).dropna())
        down = pd.Series(np.where(G["state"].isin([TS.CORR, TS.BEAR]), 1, 0), index=G.index).where(G["state"].notna())
        codes = hold(down)
        self.cache["codes_S"] = codes
        R = pd.concat({"SPY": spy, "BXMD": D.cboe_m("BXMD"), "XYLD": S_etf(S, "XYLD")}, axis=1)
        out = {}
        for nm, leg, kind in (("rule", "BXMD", "SPY ↔ BXMD 지수(투자 불가 지수 그대로)"), ("etf:XYLD", "XYLD", "SPY ↔ XYLD(ATM · 30델타 아님)")):
            W = C.weights_from_codes(codes, {0: {"SPY": 1.0}, 1: {leg: 1.0}}, ["SPY", leg])
            out[nm] = C.arm_weights(nm, W, R, spy, meta={"kind": kind})
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        c = self.cache["codes_S"]
        spy = S.spy()
        x = (S_etf(S, "XYLD") - spy).dropna()
        y = (D.cboe_m("BXMD") - spy).dropna()
        df = pd.concat([x, y], axis=1, join="inner").dropna()
        df = df.loc[C.in_win(df.index, *C.S_WIN) & (c.reindex(df.index) == 1).to_numpy()]
        rho = float(np.corrcoef(df.iloc[:, 0], df.iloc[:, 1])[0, 1]) if len(df) >= 6 else None
        return {"kind": "Correction/Bear 달 ρ(XYLD − SPY, BXMD − SPY)", "rho": rho, "n": int(len(df)),
                "gate": (rho is not None and rho >= C.FID_RHO)}

    def checks(self, D, S):
        return [("vrp", lambda v, p: TS.vrp(v, p), {"v": (D.cboe_d("VIX"), "cboe:VIX"), "p": (D.gspc(), "yf:^GSPC")}),
                ("ghm_sp_state", lambda spx, Dd, tr, rf: TS.ghm((TS.sp_state_ret(spx, Dd, tr) - rf).dropna())["state"],
                 {"spx": (D.cboe_d("SPX"), "cboe:SPX"), "Dd": (D.shiller()["D"], "shiller:D"), "tr": (D.sp500tr_d(), "yf:^SP500TR"),
                  "rf": (D.rf(), "french:ff3_m")})]

    def f0(self, D, arms):
        c = self.cache["codes"].dropna()
        c = c.loc[C.in_win(c.index, *self.spec["windows"]["full"])]
        bx = D.cboe_m("BXMD")
        return {"down_state_months": int((c == 1).sum()), "bxmd_first": str(bx.index.min()), "bxmd_missing_months":
                int(len(pd.period_range(bx.index.min(), bx.index.max(), freq="M")) - len(bx))}


# ══════════════════════════════════════════════════════════════════════════
#  T12 — 고용 추세 → 퀄리티 방어(측정만 · 모양 판정 · H_T0 제외)
# ══════════════════════════════════════════════════════════════════════════
class T12(Card):
    id = "T12"
    spec = _spec(id="T12", name="고용 추세 → 퀄리티 방어 (GTT 변형)", family="거시 · 고용", role="교체(신호 → 전략)",
                 status="측정만(모양 판정 전용 · H_T0 제외)", mandate="주식 전용",
                 windows=_win(("1964-07", "2026-07"), ("1964-07", "2016-12"), None, ("1964-07", "2005-12")))
    DEF = "op:Hi 30"

    @staticmethod
    def signal(ur, level):
        u = TS.unrate_up(ur)["up"]
        p = TS.below_sma(level)
        df = pd.concat([u.rename("u"), p.rename("p")], axis=1, join="inner")
        return ((df["u"] > 0) & (df["p"] > 0)).astype(float).where(df.notna().all(axis=1))

    def build_L(self, D, ctx):
        B = D.B()
        sig = self.signal(D.unrate_first(), TS.level_from_returns(D.ff3()["Mkt"]))
        codes = hold(sig)
        self.cache["codes"] = codes
        mp = {0: {"B": 1.0}, 1: {self.DEF: 1.0}}
        rule = switch_arm("rule", codes, mp, D, B, meta={"kind": "규칙 · 실업 추세↑ ∧ 가격 추세↓ → OP Hi 30"})
        arms = {"rule": rule,
                "C0:cash": switch_arm("C0:cash", codes, {0: {"B": 1.0}, 1: {"CASH": 1.0}}, D, B, costless=("CASH",),
                                      meta={"kind": "C0 DEF = RF(원 GTT)"}),
                "C:def_ind": switch_arm("C:def_ind", codes, {0: {"B": 1.0}, 1: dict(IND3)}, D, B, meta={"kind": "DEF = 12 산업 방어 바스켓"})}
        return arms, {"C:static": static_lazy(rule, D, B)}

    def h2_L(self, D, ctx):
        return {"codes": self.cache["codes"], "mapping": {0: {"B": 1.0}, 1: {self.DEF: 1.0}}, "R": legs_frame(D, ["B", self.DEF]),
                "B": D.B(), "report_only": True}

    def g4(self, E, D, ctx):
        LR = E["rule"]["LR"]["bundle"]
        rm = LR.get("rebound_miss") or {"ok": True}
        return {"down_X_gt0": (LR["down"]["mean"] is not None and LR["down"]["mean"] > 0), "rebound_miss_ok": bool(rm.get("ok", True))}

    def build_S(self, S, D, ctx):
        spy = S.spy()
        sig = self.signal(D.unrate_first(), TS.level_from_returns(spy))
        codes = hold(sig)
        R = pd.concat({"SPY": spy, "DEF": S.pit("op_hi30"), "QUAL": S_etf(S, "QUAL")}, axis=1)
        out = {}
        for nm, leg, kind in (("rule", "DEF", "SPY ↔ PIT 수익성 상위 30% VW"), ("etf:QUAL", "QUAL", "SPY ↔ QUAL")):
            W = C.weights_from_codes(codes, {0: {"SPY": 1.0}, 1: {leg: 1.0}}, ["SPY", leg])
            out[nm] = C.arm_weights(nm, W, R, spy, meta=dict({"kind": kind}, **({"pit_legs": {"DEF": "op_hi30"}} if leg == "DEF" else {})))
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        r = active_rho(S.pit("op_hi30"), S.spy(), D.leg(self.DEF), D.ff3()["Mkt"])
        return {"kind": "DEF 다리 ρ(PIT − SPY, OP Hi 30 − Mkt)", **r, "gate": (r["rho"] is not None and r["rho"] >= C.FID_RHO)}

    def checks(self, D, S):
        return [("unrate_up", lambda u: TS.unrate_up(u)["up"], {"u": (D.unrate_first(), "alfred:UNRATE")}),
                ("t12_sig", lambda u, mkt: self.signal(u, TS.level_from_returns(mkt)),
                 {"u": (D.unrate_first(), "alfred:UNRATE"), "mkt": (D.ff3()["Mkt"], "french:ff3_m")})]

    def f0(self, D, arms):
        c = self.cache["codes"].dropna()
        u = TS.unrate_up(D.unrate_first())
        return {"def_months_full": int((c.loc[C.in_win(c.index, *self.spec["windows"]["full"])] == 1).sum()),
                "unrate_lag_gt1_months": int((u["lag"] > 1).sum()), "unrate_first": str(u["up"].first_valid_index())}


# ══════════════════════════════════════════════════════════════════════════
#  T13 — CAPE 가치 + 모멘텀 틸트 50~150%(CAPE 재계산)
# ══════════════════════════════════════════════════════════════════════════
class T13(Card):
    id = "T13"
    spec = _spec(id="T13", name="CAPE 가치 + 모멘텀 틸트 50~150% (CAPE 재계산)", family="밸류에이션 타이밍", role="오버레이",
                 status="측정만 · H_T0 구성원", mandate="S&P 선물 ±5%(D2 허용 · 한도 50~150% 슬리브 = 펀드 95~105%)",
                 windows=_win(("1928-01", "2026-07"), ("1928-01", "2015-12"), ("2016-01", "2026-07"), ("1928-01", "2026-07")))

    @staticmethod
    def weights(sh, mex):
        ep = TS.cape_ep(sh["P"], sh["E"], sh["CPI"])
        m12 = TS.m12_excess(mex, sh["P"], sh["D"], sh["GS10_shiller"])
        return TS.t13_weights(ep, m12)

    def build_L(self, D, ctx):
        f = D.ff3()
        B, fut = D.B(), D.fut()
        Wt = self.weights(D.shiller(), f["Mkt-RF"])
        self.cache["w"] = Wt
        wv = hold(Wt["w_VM"])
        arms = {"rule": overlay_arm("rule", wv - 1.0, B, fut, 1.0, {"kind": "규칙 · w = clip(1 + ½(tilt_V + tilt_M), 0.5, 1.5)"}),
                "C:mom_only": overlay_arm("C:mom_only", hold(Wt["w_M"]) - 1.0, B, fut, 1.0,
                                          {"kind": "모멘텀만(주 대조 · w = clip(1 + tilt_M, 0.5, 1.5) · 원문 단일 신호 척도)"}),
                "C:val_only": overlay_arm("C:val_only", hold(Wt["w_V"]) - 1.0, B, fut, 1.0,
                                          {"kind": "가치만(C0 · w = clip(1 + tilt_V, 0.5, 1.5))"})}

        def const(a, b):
            w = wv.loc[C.in_win(wv.index, a, b)].dropna()
            e = float(w.mean()) if len(w) else np.nan
            return overlay_arm("C:const", pd.Series(e - 1.0, index=wv.index).where(wv.notna()), B, fut, 1.0,
                               {"kind": "상수 노출 쌍둥이(창 실현 평균 w)", "w_bar": e})
        return arms, {"C:const": const}

    def g4(self, E, D, ctx):
        r = E["rule"]["LR"]["X"]
        a1, b1 = common_mean(r, E["arms"]["C:mom_only"]["X_LR"])
        a2, b2 = common_mean(r, E["lazy"]["C:const"]["L-R"]["X"])
        return {"beats_mom_only": (a1 is not None and a1 > b1), "beats_const": (a2 is not None and a2 > b2)}

    def build_S(self, S, D, ctx):
        spy, bil = S.spy(), S.bil()
        ex = (spy - bil).dropna()
        mex = D.ff3()["Mkt-RF"]
        mex_s = pd.concat([mex[mex.index < ex.index.min()], ex]).sort_index()   # SPY − BIL 이 있는 달부터는 그것(분위 이력은 French · Shiller)
        Wt = self.weights(D.shiller(), mex_s)
        self.cache["w_S"] = Wt
        return {"rule": overlay_arm("rule", hold(Wt["w_VM"]) - 1.0, spy, ex, 1.0, {"kind": "S = SPY + (w − 1)(SPY − BIL) · 같은 CAPE"})}

    def fidelity(self, SA, LA, S, D, ctx):
        a, b = hold(self.cache["w"]["w_VM"]), hold(self.cache["w_S"]["w_VM"])
        df = pd.concat([a, b], axis=1, join="inner").dropna()
        df = df.loc[C.in_win(df.index, *C.S_OVERLAP)]
        rho = float(np.corrcoef(df.iloc[:, 0], df.iloc[:, 1])[0, 1]) if len(df) >= 24 and df.std().min() > 0 else None
        return {"kind": "w 상관(SPY 판 대 French 판 · 수익 아님)", "rho_w": rho, "n": int(len(df)), "gate": (rho is not None and rho >= 0.9)}

    def checks(self, D, S):
        sh = D.shiller()
        return [("t13_w", lambda Pp, E, CPI, Dd, G, mex: TS.t13_weights(TS.cape_ep(Pp, E, CPI), TS.m12_excess(mex, Pp, Dd, G))[["w_VM", "w_V", "w_M"]],
                 {"Pp": (sh["P"], "shiller:P"), "E": (sh["E"], "shiller:E"), "CPI": (sh["CPI"], "shiller:CPI"), "Dd": (sh["D"], "shiller:D"),
                  "G": (sh["GS10_shiller"], "shiller:GS10_shiller"), "mex": (D.ff3()["Mkt-RF"], "french:ff3_m")})]

    def f0(self, D, arms):
        w = hold(self.cache["w"]["w_VM"]).dropna()
        w = w.loc[C.in_win(w.index, *self.spec["windows"]["full"])]
        return {"w_months": int(len(w)), "w_at_floor": int((w <= 0.5 + 1e-12).sum()), "w_at_cap": int((w >= 1.5 - 1e-12).sum())}


# ══════════════════════════════════════════════════════════════════════════
#  T15 — 심리 조건부 SML 교체(고심리 = 저변동 · 저심리 = 고변동)
# ══════════════════════════════════════════════════════════════════════════
class T15(Card):
    id = "T15"
    spec = _spec(id="T15", name="심리 조건부 SML 교체 (고심리 = 저변동 · 저심리 = 고변동)", family="투자심리 × 위험 단면",
                 role="교체(신호 → 전략)", status="측정만 · H_T0 구성원 · H2 측정", mandate="주식 전용(베타 중립판은 선물 쌍둥이)",
                 license="Wurgler: 문구 없음 — 커밋 안 함 · 실행 때 받는다(D3)",
                 s_realtime="아님 — S 층 심리는 마지막 개정 판(2026-03 판)을 3개월 늦춤으로 쓴다. 파일은 해마다 3월에 전년 12월까지 붙고 "
                            "구성요소가 개정되므로 결정 달 대부분에서 그 값은 아직 공표 전이었다(공표 달력 보고판 rpt:pubcal 을 함께 적는다)",
                 forward_block="심리 구성요소(pdnd · ripo · nipo · cefd · s)를 실시간으로 다시 모으는 경로가 없다(설계 결함 «못 하면 L 층 전용») — "
                               "QFWD 수정 등록이 그 수집 경로를 먼저 보여야 전방 자격을 다시 따진다",
                 windows=_win(("1970-10", "2026-04"), ("1970-10", "2001-12"), ("2002-01", "2026-04"), ("1970-10", "2008-12")))
    LO, HI = "var:Lo 20", "var:Hi 20"

    def build_L(self, D, ctx):
        B = D.B()
        f = D.ff3()
        W = D.wurgler()
        sp = TS.sent_pit(W)
        codes = hold(sp["high"])
        self.cache["codes"] = codes
        mp = {1: {self.LO: 1.0}, 0: {self.HI: 1.0}}
        rule = switch_arm("rule", codes, mp, D, B, meta={"kind": "규칙 · HIGH → VAR Lo 20 · LOW → VAR Hi 20"})
        bl = hold(TS.beta_roll(D.leg(self.LO) - f["RF"], f["Mkt-RF"], lo=0.5, hi=1.0))
        bh = hold(TS.beta_roll(D.leg(self.HI) - f["RF"], f["Mkt-RF"], lo=1.0, hi=2.5))
        idx = codes.index.intersection(bl.index).intersection(bh.index)
        c = codes.reindex(idx)
        Wn = pd.DataFrame(np.nan, index=idx, columns=[self.LO, self.HI, "CASH", "FUT"])
        hi_m, lo_m = (c == 1).to_numpy(), (c == 0).to_numpy()
        Wn.loc[hi_m, :] = 0.0
        Wn.loc[hi_m, self.LO] = 1.0
        Wn.loc[hi_m, "FUT"] = (1.0 - bl.reindex(idx))[hi_m]
        Wn.loc[lo_m, :] = 0.0
        Wn.loc[lo_m, self.HI] = (1.0 / bh.reindex(idx))[lo_m]
        Wn.loc[lo_m, "CASH"] = (1.0 - 1.0 / bh.reindex(idx))[lo_m]
        Wn.loc[(bl.reindex(idx).isna() | bh.reindex(idx).isna()).to_numpy(), :] = np.nan
        arms = {"rule": rule,
                "C:beta_neutral": weights_arm("C:beta_neutral", Wn, D, B, overlay=("FUT",), costless=("CASH",),
                                              meta={"kind": "베타 중립판(Lo 채움 · Hi 1/β̂ · 나머지 현금)"}),
                "C:beta_legs": switch_arm("C:beta_legs", codes, {1: {"beta:Lo 20": 1.0}, 0: {"beta:Hi 20": 1.0}}, D, B,
                                          meta={"kind": "BETA Lo/Hi 20 판"}),
                "C:orth": switch_arm("C:orth", hold(TS.sent_orth_high(W)), mp, D, B, meta={"kind": "SENT_ORTH 판(파일 값 · 비 PIT · 대조)"}),
                "C:annual": switch_arm("C:annual", hold(TS.annual_hold(sp["high"])), mp, D, B, meta={"kind": "BW 원형 연 1회판(12월 값 1년)"}),
                "C:always_lo": const_arm("C:always_lo", {self.LO: 1.0}, D, B, meta={"kind": "항상 VAR Lo 20"})}
        return arms, {"C:static": static_lazy(rule, D, B)}

    def h2_L(self, D, ctx):
        return {"codes": self.cache["codes"], "mapping": {1: {self.LO: 1.0}, 0: {self.HI: 1.0}},
                "R": legs_frame(D, [self.LO, self.HI]), "B": D.B()}

    def g4(self, E, D, ctx):
        h = E["h2"] or {}
        w = self.spec["windows"]["full"]
        R = legs_frame(D, [self.LO, self.HI])
        c = self.cache["codes"].reindex(R.index)
        inw = C.in_win(R.index, *w)
        d = (R[self.LO] - R[self.HI])
        hi = d[(c == 1).to_numpy() & inw].dropna()
        lo = (-d)[(c == 0).to_numpy() & inw].dropna()
        return {"h2_delta_gt0": (h.get("delta_obs") is not None and h["delta_obs"] > 0),
                "h2_rank_ge90": (h.get("rank") is not None and h["rank"] >= C.RANK_MIN),
                "high_lo_minus_hi_gt0": (len(hi) > 0 and float(hi.mean()) > 0), "low_hi_minus_lo_gt0": (len(lo) > 0 and float(lo.mean()) > 0)}

    def build_S(self, S, D, ctx):
        spy = S.spy()
        codes = hold(TS.sent_pit(D.wurgler())["high"])
        codes_pc = hold(TS.sent_pit_pubcal(D.wurgler())["high"])
        R = pd.concat({"LO": S.pit("var_lo20"), "HI": S.pit("var_hi20"), "SPLV": S_etf(S, "SPLV"), "SPHB": S_etf(S, "SPHB")}, axis=1)
        out = {}
        for nm, cd, lo, hi, kind, pl in (
                ("rule", codes, "LO", "HI", "PIT 63거래일 분산 하위/상위 20% VW(심리 3개월 늦춤 · 개정 판 — 실시간 아님)",
                 {"LO": "var_lo20", "HI": "var_hi20"}),
                ("etf:SPLV_SPHB", codes, "SPLV", "SPHB", "SPLV / SPHB", None),
                ("rpt:pubcal", codes_pc, "LO", "HI", "보고만 — 같은 PIT 다리 · 심리를 공표 달력(3월에 전년 12월까지)으로 · 개정 판",
                 {"LO": "var_lo20", "HI": "var_hi20"})):
            W = C.weights_from_codes(cd, {1: {lo: 1.0}, 0: {hi: 1.0}}, [lo, hi])
            meta = {"kind": kind}
            if pl:
                meta["pit_legs"] = pl
            out[nm] = C.arm_weights(nm, W, R, spy, meta=meta)
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        spy, mkt = S.spy(), D.ff3()["Mkt"]
        a = active_rho(S.pit("var_lo20"), spy, D.leg(self.LO), mkt)
        b = active_rho(S.pit("var_hi20"), spy, D.leg(self.HI), mkt)
        return {"kind": "다리별 ρ", "LO": a, "HI": b, "gate": all(x["rho"] is not None and x["rho"] >= C.FID_RHO for x in (a, b))}

    def checks(self, D, S):
        W = D.wurgler()
        return [("sent_pit", lambda w: TS.sent_pit(w)[["score", "high"]], {"w": (W, "wurgler")}),
                ("sent_annual", lambda w: TS.annual_hold(TS.sent_pit(w)["high"]), {"w": (W, "wurgler")}),
                ("sent_orth", lambda w: TS.sent_orth_high(w), {"w": (W, "wurgler")}),
                ("sent_pubcal", lambda w: TS.sent_pit_pubcal(w)[["score", "high"]], {"w": (W, "wurgler")})]

    def f0(self, D, arms):
        c = self.cache["codes"].dropna()
        w = self.spec["windows"]
        return {"high_months_full": int((c.loc[C.in_win(c.index, *w["full"])] == 1).sum()),
                "low_months_full": int((c.loc[C.in_win(c.index, *w["full"])] == 0).sum()),
                "high_months_clean": int((c.loc[C.in_win(c.index, *w["clean"])] == 1).sum()),
                "sent_first_hold": str(c.index.min()), "sent_last_hold": str(c.index.max())}


# ══════════════════════════════════════════════════════════════════════════
#  T16 — 가치 합성 소매 장기 감사
# ══════════════════════════════════════════════════════════════════════════
class T16(Card):
    id = "T16"
    spec = _spec(id="T16", name="가치 합성 소매 장기 감사 (x-valsleeve 의 축을 랩 표본 밖에서)", family="가치(싸기)",
                 role="상시 · 랩 생존 소매 감사", status="측정만 · H_T0 구성원", mandate="주식 전용",
                 s_provisional="S 층 네 축(B/M · E/P · CF/P · D/P)이 모두 배당 조정 가격으로 잰 시가총액 · 가격을 분모로 쓴다 — 편입 날 이후 배당이 "
                               "큰 종목일수록 비율이 부푸는 선견(S 층 · §8). 구현성 통과는 잠정 — QFWD 수정 등록 전에 분할만 조정한 가격으로 다시 잰다",
                 windows=_win(("1951-07", "2026-07"), ("1951-07", "1992-06"), ("1992-07", "2014-06"), ("1951-07", "2014-06")))
    AXES = ("beme", "cfp", "ep", "dp")

    def build_L(self, D, ctx):
        B = D.B()
        four = {"%s:Hi 30" % a: 0.25 for a in self.AXES}
        arms = {"rule": const_arm("rule", four, D, B, meta={"kind": "규칙 · 네 VW Hi 30 동일가중 · 월 되돌림"})}
        for a in self.AXES:
            arms["C:axis_%s" % a] = const_arm("C:axis_%s" % a, {"%s:Hi 30" % a: 1.0}, D, B, meta={"kind": "%s Hi 30 단독" % a})
        arms["C:q5"] = const_arm("C:q5", {"%s:Hi 20" % a: 0.25 for a in self.AXES}, D, B, meta={"kind": "상위 5분위판"})
        arms["C:ew"] = const_arm("C:ew", {"%s:Hi 30:ew" % a: 0.25 for a in self.AXES}, D, B, meta={"kind": "EW 판"})
        arms["C:axis_beme"].meta["alias"] = "BE-ME Hi 30 단독(설계 대조 둘이 같은 팔)"
        return arms, {}

    def g4(self, E, D, ctx):
        r = pd.Series(E["rule"]["LR"]["X"]).dropna()
        ax = [pd.Series(E["arms"]["C:axis_%s" % a]["X_LR"]).dropna() for a in self.AXES]
        df = pd.concat([r] + ax, axis=1, join="inner").dropna()
        return {"report_only": {"composite_ge_axis_mean": (bool(df.iloc[:, 0].mean() >= df.iloc[:, 1:].mean(axis=1).mean()) if len(df) else None)}}

    def build_S(self, S, D, ctx):
        spy = S.spy()
        R = pd.concat({"bm": S.pit("bm_hi30"), "cfp": S.pit("cfp_hi30"), "ep": S.pit("ep_hi30"), "dp": S.pit("dp_hi30"),
                       "RPV": S_etf(S, "RPV"), "IVE": S_etf(S, "IVE"), "COWZ": S_etf(S, "COWZ")}, axis=1)
        out = {}
        idx = R[["bm", "cfp", "ep", "dp"]].dropna().index
        out["rule"] = C.arm_weights("rule", pd.DataFrame({k: 0.25 for k in ("bm", "cfp", "ep", "dp")}, index=idx), R, spy,
                                    meta={"kind": "PIT 네 축 상위 30% VW 동일가중",
                                          "pit_legs": {"bm": "bm_hi30", "cfp": "cfp_hi30", "ep": "ep_hi30", "dp": "dp_hi30"}})
        for tk in ("RPV", "IVE", "COWZ"):
            out["etf:" + tk] = C.arm_weights("etf:" + tk, pd.DataFrame({tk: 1.0}, index=R[tk].dropna().index), R, spy, meta={"kind": tk})
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        r = active_rho(SA["rule"].S, SA["rule"].B, LA["rule"].S, LA["rule"].B)
        return {"kind": "ρ(PIT 합성 − SPY, French 합성 − Mkt)", **r, "gate": (r["rho"] is not None and r["rho"] >= C.FID_RHO)}


# ══════════════════════════════════════════════════════════════════════════
#  T17 — 금리 국면 가치/성장 교체 장기 감사(D13 가족 · 죽이기 검정)
# ══════════════════════════════════════════════════════════════════════════
class T17(Card):
    id = "T17"
    spec = _spec(id="T17", name="금리 국면 가치/성장 교체 장기 감사 (D13 가족 · 죽이기 검정)", family="금리 · 주식 듀레이션",
                 role="교체(신호 → 전략) · 랩 생존 규칙 감사", status="측정만 · 죽이기 검정 · H_T0 구성원", mandate="주식 전용",
                 windows=_win(("1953-07", "2026-07"), None, ("1953-07", "2000-05"), ("1953-07", "2000-05")))
    V, G = "beme:value_half", "beme:growth_half"

    def mapping(self, v="V", g="G"):
        v = self.V if v == "V" else v
        g = self.G if g == "G" else g
        return {TS.VALUE_TILT: {v: 0.7, g: 0.3}, TS.NEUTRAL: {v: 0.5, g: 0.5}, TS.GROWTH_TILT: {v: 0.3, g: 0.7}}

    def build_L(self, D, ctx):
        B = D.B()
        codes = hold(TS.d13_regime(D.fred("GS10"))["regime"])
        self.cache["codes"] = codes
        rule = switch_arm("rule", codes, self.mapping(), D, B, meta={"kind": "규칙 · ΔGS10 ±0.20 → 가치 70/50/30"})
        rr = hold(TS.rr_proxy_regime(D.fred("GS10"), D.fred("CPIAUCSL"))["regime"])
        arms = {"rule": rule,
                "C:5050": const_arm("C:5050", {self.V: 0.5, self.G: 0.5}, D, B, meta={"kind": "틸트 없는 50/50 반쪽(주 대조)"}),
                "C:rr_proxy": switch_arm("C:rr_proxy", rr, self.mapping(), D, B, meta={"kind": "실질금리 대리(GS10 − 12개월 CPI)"})}
        return arms, {"C:static": static_lazy(rule, D, B)}

    def h2_L(self, D, ctx):
        return {"codes": self.cache["codes"], "mapping": self.mapping(), "R": legs_frame(D, [self.V, self.G]), "B": D.B(),
                "static_weights": {self.V: 0.5, self.G: 0.5}}

    def g4(self, E, D, ctx):
        h = E["h2"] or {}
        cw = self.spec["windows"]["clean"]
        r = pd.Series(E["rule"]["LR"]["X"]).dropna()
        b = pd.Series(E["arms"]["C:5050"]["X_LR"]).dropna()
        d = (r - b).dropna()
        d = d.loc[C.in_win(d.index, *cw)]
        t = C.nw_t(d.to_numpy()) if len(d) > 5 else None
        kill = (len(d) == 0) or (float(d.mean()) <= 0) or (t is None) or (t < 1.0)
        return {"kill_not_triggered": (not kill), "h2_delta_gt0": (h.get("delta_obs") is not None and h["delta_obs"] > 0),
                "h2_rank_ge90": (h.get("rank") is not None and h["rank"] >= C.RANK_MIN),
                "kill_detail": {"window": list(cw), "n": int(len(d)), "t": t,
                                "note": "Δ(규칙 − 50/50) ≤ 0 이거나 NW t < 1.0 이면 «D13 장기 비재현» — 랩 기존 판정은 다시 읽지 않고 주석만"}}

    def build_S(self, S, D, ctx):
        spy = S.spy()
        cg = hold(TS.d13_regime(D.fred("GS10"))["regime"])
        cd = hold(TS.dfii10_regime(D.fred("DFII10"))["regime"])
        self.cache["codes_S"], self.cache["codes_D"] = cg, cd
        R = pd.concat({k: S_etf(S, k) for k in ("IVE", "IVW", "IWD", "IWF", "VTV", "VUG")}, axis=1)
        out = {}
        for nm, v, g, cds, kind in (("rule", "IVE", "IVW", cg, "IVE/IVW · GS10 신호"), ("etf:IVE_IVW_DFII10", "IVE", "IVW", cd, "IVE/IVW · DFII10 원판(D13)"),
                                    ("etf:IWD_IWF", "IWD", "IWF", cg, "IWD/IWF · GS10(오염 · 보고)"), ("etf:VTV_VUG", "VTV", "VUG", cg, "VTV/VUG · GS10(오염 · 보고)")):
            W = C.weights_from_codes(cds, self.mapping(v, g), [v, g])
            out[nm] = C.arm_weights(nm, W, R, spy, meta={"kind": kind})
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        a, b = self.cache["codes_S"], self.cache["codes_D"]
        df = pd.concat([a, b], axis=1, join="inner").dropna()
        df = df.loc[C.in_win(df.index, *C.S_WIN)]
        rate = float((df.iloc[:, 0] == df.iloc[:, 1]).mean()) if len(df) else None
        return {"kind": "GS10 판과 DFII10 판의 국면 일치율(보고만 · 수익 아님)", "agree": rate, "n": int(len(df)), "gate": None}

    def checks(self, D, S):
        return [("d13", lambda g: TS.d13_regime(g)["regime"], {"g": (D.fred("GS10"), "fred:GS10")}),
                ("rr_proxy", lambda g, c: TS.rr_proxy_regime(g, c)["regime"], {"g": (D.fred("GS10"), "fred:GS10"), "c": (D.fred("CPIAUCSL"), "fred:CPIAUCSL")}),
                ("dfii10", lambda d: TS.dfii10_regime(d)["regime"], {"d": (D.fred("DFII10"), "fred:DFII10")})]

    def f0(self, D, arms):
        c = self.cache["codes"].dropna()
        c = c.loc[C.in_win(c.index, *self.spec["windows"]["full"])]
        return {"regime_months": {"value": int((c == TS.VALUE_TILT).sum()), "neutral": int((c == TS.NEUTRAL).sum()),
                                  "growth": int((c == TS.GROWTH_TILT).sum())}, "first_hold": str(c.index.min()) if len(c) else None}


# ══════════════════════════════════════════════════════════════════════════
#  T18 — 순자사주매입 소매 장기 감사
# ══════════════════════════════════════════════════════════════════════════
class T18(Card):
    id = "T18"
    spec = _spec(id="T18", name="순자사주매입 소매 장기 감사 (주주환원 · 순발행 < 0)", family="주주환원 · 순발행",
                 role="상시 · 랩 생존 축 감사", status="측정만(청정 창 미확정 · H_T0 제외)", mandate="주식 전용",
                 windows=_win(("1963-07", "2026-07"), None, None, ("1963-07", "2014-06")),
                 dropped_controls=["«< 0» ∩ 배당 지급 — 자료 없음(설계대로 뺌)"])

    def build_L(self, D, ctx):
        B = D.B()
        arms = {"rule": const_arm("rule", {"ni:< 0": 1.0}, D, B, meta={"kind": "규칙 · NI «< 0» VW"}),
                "C:lo20": const_arm("C:lo20", {"ni:Lo 20": 1.0}, D, B, meta={"kind": "NI Lo 20 5분위"}),
                "C:ew": const_arm("C:ew", {"ni:< 0:ew": 1.0}, D, B, meta={"kind": "EW 판"})}
        return arms, {}

    def g4(self, E, D, ctx):
        return {}

    def build_S(self, S, D, ctx):
        spy = S.spy()
        R = pd.concat({"PIT": S.pit("ni_lt0"), "PKW": S_etf(S, "PKW"), "SYLD": S_etf(S, "SYLD")}, axis=1)
        out = {"rule": C.arm_weights("rule", pd.DataFrame({"PIT": 1.0}, index=R["PIT"].dropna().index), R, spy,
                                     meta={"kind": "PIT 주식수 감소 기업 VW", "pit_legs": {"PIT": "ni_lt0"}})}
        for tk in ("PKW", "SYLD"):
            out["etf:" + tk] = C.arm_weights("etf:" + tk, pd.DataFrame({tk: 1.0}, index=R[tk].dropna().index), R, spy, meta={"kind": tk})
        return out

    def fidelity(self, SA, LA, S, D, ctx):
        r = active_rho(SA["rule"].S, SA["rule"].B, LA["rule"].S, LA["rule"].B)
        return {"kind": "ρ(PIT − SPY, NI < 0 − Mkt)", **r, "gate": (r["rho"] is not None and r["rho"] >= C.FID_RHO)}


CARDS = (T01, T02, T03, T04, T05, T08, T12, T13, T15, T16, T17, T18)


def fast_disagreements(D):
    """F0 — FF3 판별 FAST(부호 Mkt-RF ≥ 0) 가 지금 판과 다른 달 수(겹치는 달) · 판 2005-08 · 2015-08 · 2020-08 · 2024-08 · 2024-12."""
    cur = D.ff3()["Mkt-RF"]
    out = {}
    for v in TD.FF_VINTAGES:
        f = D.ff3_vintage(v)
        if f is None:
            out[v] = None
            continue
        a = pd.concat([cur, f["Mkt-RF"]], axis=1, join="inner").dropna()
        out[v] = {"n": int(len(a)), "fast_differ": int(((a.iloc[:, 0] >= 0) != (a.iloc[:, 1] >= 0)).sum())}
    return out


# ══════════════════════════════════════════════════════════════════════════
#  평가 — 카드 하나 · 배치 전체
# ══════════════════════════════════════════════════════════════════════════
class Ctx:
    """배치 공용 — σ_L · ^GSPC 지그재그 사건 · S 층 사건 · PIT 회전 τ. 무거운 것은 처음 쓸 때 만든다."""

    def __init__(self, D, S, events_S=None, taus=None, make_data=None):
        self.D, self.S = D, S
        self.make_data = make_data or Data              # 판 · G5g 재실행용 Data 공장(합성 selftest 는 FakeData)
        self._sigma = None
        self._ev = {}
        self._evS = events_S
        self._taus = taus

    @property
    def sigma(self):
        if self._sigma is None:
            self._sigma = C.sigma_L(self.D.ff3()["Mkt"])
        return self._sigma

    def events_L(self, key, B):
        if key not in self._ev:
            self._ev[key] = C.events_L(B, self.sigma, self.D.gspc())
        return self._ev[key]

    @property
    def events_S(self):
        if self._evS is None:
            self._evS = C.events_S()
        return self._evS

    def pit_lookahead(self, n=12):
        """PIT 편입 선견 점검(실자료) — 무작위 편입 달의 뒤 가격을 난수로 바꿔도 같은 종목 · 같은 비중이어야 한다. 틀리면 멈춘다."""
        if getattr(self, "_pit_la", None) is None:
            self._pit_la = TP.pit_lookahead_check(self.S.panel(), n=n)
            if not self._pit_la["ok"]:
                raise SystemExit("🚨 PIT 편입 선견 점검 실패 — %d/%d · 첫 사례 %s" % (self._pit_la["n_bad"], self._pit_la["n"],
                                                                        (self._pit_la["bad"] or [None])[0]))
        return self._pit_la

    @property
    def taus(self):
        if self._taus is None:
            pn = self.S.panel()
            self._taus = {s: pn.turnover(s) for s in TP.SORTS}
        return self._taus


def _series_rec(x):
    return None if x is None else {str(k): (None if v != v else float(v)) for k, v in pd.Series(x).items()}


def _light(X, B, ev):
    x = pd.Series(X, dtype=float).dropna()
    if len(x) == 0:
        return {"h1": C.h1(x)}
    Bv = pd.Series(B).reindex(x.index)
    dn, cr, su = ev.down(x.index, Bv), ev.crash(x.index, Bv), ev.surge(x.index, Bv)
    xv = x.to_numpy()
    mean = lambda m: (float(xv[m].mean()) if m.any() else None)
    return {"h1": C.h1(x), "down_mean": mean(dn), "crash_m": mean(cr), "surge_m": mean(su), "years": C.year_table(x, Bv)["rate"]}


def _bench_key(card):
    return "sptr" if card.id in ("T02", "T08") else "french"


def g6b(X, B):
    """G6b — 네 토막 각각의 연도 승률(보고만) · 12개월이 찬 해만(G6a 와 같은 규약)."""
    yt = {y: v for y, v in C.year_table(X, B)["years"].items() if v["n"] >= 12}
    ys = sorted(yt)
    if len(ys) < 4:
        return None
    out = []
    for grp in np.array_split(np.array(ys), 4):
        w = sum(1 for y in grp if yt[y]["ex"] >= C.TIE)
        l_ = sum(1 for y in grp if yt[y]["ex"] <= -C.TIE)
        out.append((w / (w + l_)) if (w + l_) else None)
    return {"rates": out, "all_ge50": all(v is not None and v >= C.G6B_MIN for v in out)}


def evaluate_card(card, D, S, ctx, nperm=None, lookahead_n=LOOKAHEAD_N, variants=True, keep_series=False):
    """카드 하나 끝까지 — 선견 점검(멈춤) → L 층 팔 → H2 → 묶음 · 판 · 관문 · 라벨 → S 층 · 충실도 · 구현성. 수익을 찍지 않는다."""
    t0 = time.time()
    cid, spec = card.id, card.spec
    wins = C.layer_windows(spec)
    la = {}
    for nm, fn, inputs in card.checks(D, S):
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            res = TD.lookahead_check(fn, inputs, n=lookahead_n)
        TD.require_no_lookahead(res, "%s:%s" % (cid, nm))
        la[nm] = {"ok": res["ok"], "n": res["n"]}
    ctx.pit_lookahead()                                                 # PIT 편입 선견 점검(한 번 · 틀리면 멈춘다)
    arms, lazy = card.build_L(D, ctx)
    rule = arms["rule"]
    bk = _bench_key(card)
    ev = ctx.events_L(bk, (ctx.D.sptr() if bk == "sptr" else ctx.D.B()))   # 사건은 벤치마크 전 계열로(카드 차례와 무관)
    # H2
    h2 = None
    hs = card.h2_L(D, ctx) if cid in C.SWITCHING else None
    if hs is not None:
        h2 = C.h2_test(hs["codes"], hs["mapping"], hs["R"], hs["B"], *wins["L-R"], nperm=nperm,
                       static_weights=hs.get("static_weights"), costless=hs.get("costless", ()))
        h2["report_only"] = bool(hs.get("report_only"))
    # 규칙 — 층 창
    rsub = {k: (rule.sub(*w) if w else None) for k, w in wins.items() if k in ("L-R", "L-C", "out_of_lab", "lit_seen")}
    X = {k: (a.X() if a is not None else None) for k, a in rsub.items()}
    LR = C.bundle(X["L-R"], rsub["L-R"].B, ev, dD=(h2["dD"] if h2 and h2.get("dD") is not None else None))
    LC = C.bundle(X["L-C"], rsub["L-C"].B, ev) if X.get("L-C") is not None and len(X["L-C"].dropna()) else None
    OOL = C.bundle(X["out_of_lab"], rsub["out_of_lab"].B, ev) if X.get("out_of_lab") is not None and len(X["out_of_lab"].dropna()) else None
    LIT = C.h1(X["lit_seen"]) if X.get("lit_seen") is not None else None
    extra = {k: C.h1(rule.sub(*w).X()) for k, w in (spec.get("extra_windows") or {}).items()}
    # 대조 · 단계 · 쌍둥이
    E_arms = {}
    for nm, a in arms.items():
        if nm == "rule":
            continue
        xl = a.sub(*wins["L-R"]).X()
        rec = {"meta": a.meta, "LR": _light(xl, a.B, ev), "X_LR": xl}
        if wins.get("L-C"):
            rec["LC"] = C.h1(a.sub(*wins["L-C"]).X())
        for wn, w in ((spec.get("arm_windows") or {}).get(nm) or {}).items():
            rec[wn] = C.h1(a.sub(*w).X())
        E_arms[nm] = rec
    E_lazy = {}
    for nm, f in lazy.items():
        E_lazy[nm] = {}
        for wn in ("L-R", "L-C"):
            w = wins.get(wn)
            if not w:
                continue
            a = f(*w).sub(*w)
            xl = a.X()
            E_lazy[nm][wn] = {"meta": a.meta, "h1": C.h1(xl), "X": xl}
    # 판(G5)
    V = {"cost2x": float(rsub["L-R"].X(mult=2.0).dropna().mean())}
    xm = X["L-R"].dropna()
    V["sync"] = float(xm[~C.sync_mask(xm.index, cid)].mean())
    V["vintage"], V["vintage_skipped"] = {}, {}
    if variants and card.french:
        for v in ("2024-12", "2005-08"):
            try:
                a2, _ = type(card)().build_L(ctx.make_data(vintage=v), ctx)
                V["vintage"][v] = float(a2["rule"].sub(*wins["L-R"]).X().dropna().mean())
            except VintageMissing as e:
                V["vintage"][v] = None
                V["vintage_skipped"][v] = "판 없음: %s" % e
        a3, _ = type(card)().build_L(ctx.make_data(bench="sptr"), ctx)
        V["sptr"] = float(a3["rule"].sub(*wins["L-R"]).X().dropna().mean())
    else:
        V["vintage_skipped"]["all"] = "해당 없음(French 카드 아님)" if not card.french else "판 재실행 끔"
    legtau = {leg: TP.tau_for(leg, ctx.taus) for leg in (rule.W.columns if rule.W is not None else [])}
    turn = rsub["L-R"].turnover_1w({k: v for k, v in legtau.items() if v is not None})
    V["net_internal"] = float(rsub["L-R"].X(tau={k: v for k, v in legtau.items() if v is not None}).dropna().mean())
    # G5 «해당 없음» — 카드 spec 이 선언한 칸만(그 밖의 None 은 관문에서 거짓)
    na = {}
    if not wins.get("L-C"):
        na["c_clean"] = "청정 창 없음(설계)"
    if not card.french:
        na["g_sptr"] = "French 카드가 아님 — B 가 이미 S&P TR"
    if spec.get("g5e_na"):
        na["e_turn"] = spec["g5e_na"]
        turn = None
    # G4 · 관문 · 라벨 — G4 조건은 사전(보고) 말고 모두 관문 · None 은 거짓(t_core._b)
    E = {"rule": {"LR": {"X": X["L-R"], "bundle": LR}}, "arms": E_arms, "lazy": E_lazy, "h2": h2}
    g4 = card.g4(E, D, ctx)
    g4_gate = {k: v for k, v in g4.items() if not isinstance(v, dict)}
    ev_res = {"LR": LR, "LC": LC, "OOL": OOL, "variants": V, "turn_1w": turn, "g4": g4_gate, "g6b": g6b(X["L-R"], rsub["L-R"].B),
              "na": na}
    G = C.gates(cid, ev_res)
    f0 = card.f0(D, arms)
    f0_ok = bool(LR["h1"]["n"] >= 60)
    lab = C.label(cid, spec, ev_res, G, f0_ok)
    # S 층
    SA = card.build_S(S, D, ctx)
    s_res = {}
    evS = ctx.events_S
    for nm, a in SA.items():
        sub = a.sub(*C.S_WIN)
        # PIT 바스켓 자체의 재구성 비용 — 다리 → 정렬 τ(편도 · 연 · 2016-08~2026-08 · 비중 경로만) × 2 × 10bp × 비중
        tauS = {leg: (ctx.taus.get(sort) or {}).get("tau") for leg, sort in ((a.meta or {}).get("pit_legs") or {}).items()}
        tauS = {k: v for k, v in tauS.items() if v is not None} or None
        xg, x10, x10s = sub.X(gross=True), sub.X(flat=C.S_COST, tau=tauS), sub.X(flat=C.S_COST)
        s_res[nm] = {"meta": a.meta, "gross": C.h1(xg), "cost10": C.h1(x10), "cost10_switch_only": C.h1(x10s),
                     "bundle": C.bundle(x10, sub.B, evS) if len(x10.dropna()) else None,
                     "turn_1w": sub.turnover_1w(tauS), "pit_tau": tauS, "n": int(len(x10.dropna()))}
    fid = card.fidelity(SA, arms, S, D, ctx)
    sr = s_res.get("rule") or {}
    spass = C.s_pass((sr.get("gross") or {}).get("mean"), (sr.get("cost10") or {}).get("mean"), LR["h1"]["mean"], fid)
    out = {"id": cid, "spec": {k: v for k, v in spec.items()}, "lookahead": la, "sec": None,
           "L": {"LR": LR, "LC": LC, "OOL": OOL, "lit_seen": LIT, "extra": extra, "variants": V, "turn_1w": turn, "legtau": legtau,
                 "h2": ({k: v for k, v in h2.items() if k != "dD"} if h2 else None),
                 "arms": {k: {kk: vv for kk, vv in v.items() if kk != "X_LR"} for k, v in E_arms.items()},
                 "lazy": {k: {wn: {kk: vv for kk, vv in r.items() if kk != "X"} for wn, r in v.items()} for k, v in E_lazy.items()},
                 "g4": g4, "gates": G, "label": lab, "f0": f0, "f0_ok": f0_ok},
           "S": {"arms": s_res, "fidelity": fid, "pass": spass, "provisional": spec.get("s_provisional"),
                 "realtime_note": spec.get("s_realtime")},
           "pit_lookahead": ({k: v for k, v in ctx._pit_la.items() if k != "bad"} if getattr(ctx, "_pit_la", None) else None),
           "forward_ok": C.forward_ok(spec, lab, spass),
           "forward_note": (("D2 불허" if not spec.get("forward_allowed", True) else None) or spec.get("forward_block")
                            or (("S 통과 잠정 — " + spec["s_provisional"]) if spec.get("s_provisional") else None)),
           "publish": spec.get("publish", "결과 문서 §5 표대로"),
           "n_arms_L": 1 + len(arms) - 1 + len(lazy), "n_arms_S": len(SA),
           "dsr": {"LR": [C.dsr(X["L-R"], n) for n in C.DSR_N], "LC": ([C.dsr(X["L-C"], n) for n in C.DSR_N] if X.get("L-C") is not None else None)}}
    if keep_series:
        out["_X_LC"] = X.get("L-C")
        out["_X_LR"] = X["L-R"]
    out["sec"] = round(time.time() - t0, 1)
    return out


def run_batch(cards=None, nperm=None, write=False, lookahead_n=LOOKAHEAD_N, D=None, S=None, ctx=None):
    """배치 전체 — 카드마다 evaluate_card · H_T0(스타우퍼 · 청정 창 t) · BY(정보) · 팔 수(누적 N 보고).
    write=True 는 frozen_check() 를 통과한 굽기에서만 — 산출은 저장소 밖(t_core.out_path)."""
    if write:
        commit = C.frozen_check()
        if getattr(C, "_RUNNER_TOKEN", None) != commit:
            raise SystemExit("🚨 굽기는 build/t_run.py 로만 — 러너의 판 점검(시작 표식 · 판 · 상수 · 경계)을 거치지 않은 write=True 다.")
        if (nperm or C.NPERM) < C.NPERM_MIN:
            raise SystemExit("🚨 NPERM %s < 등록 값 %d." % (nperm, C.NPERM_MIN))
    D = D or Data()
    S = S or SData()
    ctx = ctx or Ctx(D, S)
    res = {}
    for K in (cards or CARDS):
        card = K()
        res[card.id] = evaluate_card(card, D, S, ctx, nperm=nperm, lookahead_n=lookahead_n, keep_series=True)
    ts = {c: (res[c]["L"]["LC"]["h1"]["t"] if (c in res and res[c]["L"]["LC"]) else None) for c in C.H_T0_MEMBERS if c in res}
    xs = {c: res[c].get("_X_LC") for c in ts}
    h0 = C.stouffer(ts, xs) if ts else None
    # D2 민감도(α 없음 · 보고만 · 저장소 밖 산출에만 — T02 가 AQR 파생이라 D3): T02 를 뺀 같은 식
    ts2 = {c: v for c, v in ts.items() if c != "T02"}
    h0s = C.stouffer(ts2, {c: xs[c] for c in ts2}) if ts2 else None
    if h0s is not None:
        h0s = {"report_only": True, "alpha": None, "note": "D2 민감도 — T02 를 뺀 스타우퍼 · α 없음 · 확인 검정은 H_T0 하나",
               **{k: v for k, v in h0s.items() if k not in ("alpha", "z_crit", "reject")}}
    pv = {c: (res[c]["L"]["LC"]["h1"]["p"] if res[c]["L"]["LC"] else None) for c in ts}
    by = C.by_info(pv) if pv else None
    for c in res:
        res[c].pop("_X_LC", None)
        res[c].pop("_X_LR", None)
    n_arms = sum(r["n_arms_L"] for r in res.values())
    out = {"cards": res, "H_T0": h0, "H_T0_sens_exT02": h0s, "BY_info": by, "n_arms_L": n_arms,
           "n_arms_S": sum(r["n_arms_S"] for r in res.values()), "dsr_N": C.DSR_N, "nperm": nperm or C.NPERM,
           "decisions": {"D1": "L 층 = 기전 증거(사이트 비게시)", "D2": "T02 측정만 · 전방 불가", "D3": "AQR · Cboe · Wurgler 파생 비공개",
                         "D4": "FWER 0.025 → H_T0 하나"}}
    import scipy
    out["versions"] = {"numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "python": sys.version.split()[0]}
    if write:
        out["prereg_commit"] = commit
        p = C.out_path()
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, default=C.js_default) + "\n")
        out["_path"] = p
    return out


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기 시험(실자료 · 표준출력 버림 · 모양만 · 파일 안 씀)
# ══════════════════════════════════════════════════════════════════════════
def _peak_mb():
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return round(pmc.PeakWorkingSetSize / 2 ** 20)
    except Exception:
        return None


def blind_smoke(card_ids=None, nperm=SMOKE_NPERM, lookahead_n=LOOKAHEAD_N):
    """모든 카드를 실자료로 끝까지 — qbatch_core.blind_smoke(표준출력 버림 · 결과는 모양만). NPERM 은 덮어쓴다(작게).
    돌려주는 것: {카드: {ok, sec, err}} · 배치(H_T0 까지) {ok, sec, shape} · 최대 작업 메모리(MB). 수익 숫자는 돌려주지 않는다."""
    import warnings
    import qbatch_core as Q
    ks = [K for K in CARDS if (not card_ids or K.id in card_ids)]
    D, S = Data(), SData()
    ctx = Ctx(D, S)
    old = C.NPERM
    C.NPERM = nperm

    def guarded(fn):
        """선견 점검 실패(SystemExit)도 연기 시험의 실패로 적는다 — 값 없이 이름 · 첫 t 만."""
        def g():
            try:
                with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                    warnings.simplefilter("ignore")
                    return fn()
            except SystemExit as e:
                raise RuntimeError("SystemExit: %s" % e) from None
        return g
    out = {}
    try:
        for K in ks:
            r = Q.blind_smoke(guarded(lambda K=K: evaluate_card(K(), D, S, ctx, nperm=nperm, lookahead_n=lookahead_n)))
            out[K.id] = {"ok": r["ok"], "sec": r["sec"], "err": (r["err"] or "")[-2500:] or None}
        if not card_ids:
            r = Q.blind_smoke(guarded(lambda: run_batch(ks, nperm=nperm, write=False, lookahead_n=20, D=D, S=S, ctx=ctx)))
            out["_batch"] = {"ok": r["ok"], "sec": r["sec"], "err": (r["err"] or "")[-2500:] or None,
                             "shape_keys": sorted((r["shape"] or {}).keys()) if r["ok"] else None}
    finally:
        C.NPERM = old
    pn = S._c.get("panel")                                              # 구조만(달 수 · 가격 키 수) — 수익 아님
    out["_panel"] = ({"months": len(pn.months), "keys": len(pn.keys), "taus_sorts": sorted(ctx._taus or {})} if pn is not None else None)
    cnt = {}                                                            # 바스켓 종목 수(F0 셈 · 수익 아님) — 조용히 빈 바스켓을 잡는다
    for (kind, sort), bk in [(k, v) for k, v in S._c.items() if isinstance(k, tuple) and k[0] == "bk"]:
        ns = [n for m, n in bk["n"].items() if C.S_WIN[0] <= m <= C.S_WIN[1]]
        cnt[sort] = {"months": len(ns), "min_names": (min(ns) if ns else 0), "median_names": (int(np.median(ns)) if ns else 0)}
    if pn is not None:
        cv = [v for v in pn.coverage().values() if v is not None]
        cnt["_coverage"] = {"months": len(cv), "min": (round(min(cv), 3) if cv else None)}
    out["_pit_counts"] = cnt
    out["_peak_mb"] = _peak_mb()
    return out


# ══════════════════════════════════════════════════════════════════════════
#  합성 자료 시험 — 가짜 Data · SData (실자료를 읽지 않는다)
# ══════════════════════════════════════════════════════════════════════════
class FakeData(Data):
    """Data 와 같은 메서드 · 합성 계열. vintage 흉내: "2005-08" 은 ff3 만 · "2024-12" 는 2024-12 에서 끝."""

    def __init__(self, vintage=None, bench="french", seed=11):
        super().__init__(vintage, bench)
        self.rng = np.random.default_rng(seed)
        self._g = {}
        end = "2024-12" if vintage == "2024-12" else ("2005-07" if vintage == "2005-08" else "2026-07")
        self.m = pd.period_range("1926-07", end, freq="M")
        n = len(self.m)
        rng = np.random.default_rng(seed)
        mex = rng.normal(0.006, 0.045, n)
        rf = np.full(n, 0.003)
        self._ff3 = pd.DataFrame({"Mkt-RF": mex, "RF": rf}, index=self.m)
        self._ff3["Mkt"] = self._ff3["Mkt-RF"] + self._ff3["RF"]
        self._legs = {}
        starts = {"beta": "1963-07", "var": "1963-07", "op": "1963-07", "ni": "1963-07", "ep": "1951-07", "cfp": "1951-07",
                  "dp": "1927-07", "prior12_2": "1927-01", "beme": "1926-07", "ind12": "1926-07"}
        self._starts = starts
        self._mex = mex

    def _leg_series(self, fid, col, ew=False):
        key = (fid, col, ew)
        if key not in self._legs:
            h = abs(hash((fid, col, ew))) % (2 ** 31)
            r = np.random.default_rng(h)
            beta = 0.6 + (h % 100) / 125.0
            s = pd.Series(self._ff3["RF"].to_numpy() + beta * self._mex + r.normal(0.0005, 0.02, len(self.m)), index=self.m)
            self._legs[key] = s.loc[s.index >= P(self._starts.get(fid, "1926-07"))]
        return self._legs[key]

    def _need(self, fid):
        if self.vintage == "2005-08" and fid != "ff3_m":
            raise VintageMissing("%s@2005-08" % fid)

    def ff3(self):
        return self._ff3

    def ff3d(self):
        self._need("ff3_d")
        if "d" not in self._g:
            days = pd.bdate_range("1926-07-01", self.m[-1].end_time.normalize())
            self._g["d"] = pd.DataFrame({"Mkt-RF": np.random.default_rng(3).normal(0.0002, 0.01, len(days))}, index=days)
        return self._g["d"]

    def momd(self):
        self._need("mom_d")
        return self.ff3d()["Mkt-RF"] * 0.5 + 0.0001

    def leg(self, name):
        parts = name.split(":")
        fid, col = parts[0], parts[1]
        self._need(fid)
        return self._leg_series(fid, col, len(parts) > 2 and parts[2] == "ew")

    def f0_ok(self, name):
        parts = name.split(":")
        if len(parts) < 2 or parts[0] in ("B", "FUT", "CASH", "SP", "BXMD", "TS", "BAB"):
            return None
        s = self.leg(name)
        ok = pd.Series(True, index=s.index)
        if name == "ind12:Hlth":
            ok[ok.index < P("1958-07")] = False
        return ok

    def sptr(self):
        if "sptr" not in self._g:
            idx = pd.period_range("1975-02", "2026-08", freq="M")
            base = self._ff3["Mkt"].reindex(idx)
            self._g["sptr"] = base.fillna(0.007) + np.random.default_rng(5).normal(0, 0.003, len(idx))
        return self._g["sptr"]

    def B(self):
        if self.bench == "sptr":
            s = self.sptr()
            return s[s.index >= P("1988-02")]
        return self._ff3["Mkt"]

    def gspc(self):
        if "gspc" not in self._g:
            days = pd.bdate_range("1927-12-30", "2026-09-24")
            self._g["gspc"] = pd.Series(17 * np.exp(np.cumsum(np.random.default_rng(6).normal(0.0002, 0.011, len(days)))), index=days)
        return self._g["gspc"]

    def shiller(self):
        if "sh" not in self._g:
            m = pd.period_range("1871-01", "2026-09", freq="M")
            r = np.random.default_rng(7)
            n = len(m)
            self._g["sh"] = pd.DataFrame({"P": 5 * np.exp(np.cumsum(r.normal(0.003, 0.035, n))), "D": np.linspace(0.2, 70, n),
                                          "E": np.linspace(0.4, 200, n) * np.exp(r.normal(0, 0.05, n)), "CPI": np.linspace(12, 330, n),
                                          "GS10_shiller": 4 + r.normal(0, 0.3, n)}, index=m)
        return self._g["sh"]

    def fred(self, sid):
        key = ("fred", sid)
        if key not in self._g:
            r = np.random.default_rng(len(sid))
            if sid == "DFII10":
                days = pd.bdate_range("2003-01-02", "2026-09-24")
                self._g[key] = pd.Series(1.5 + np.cumsum(r.normal(0, 0.03, len(days))), index=days)
            elif sid == "CPIAUCSL":
                m = pd.period_range("1947-01", "2026-08", freq="M")
                self._g[key] = pd.Series(np.linspace(21, 320, len(m)), index=m)
            else:
                m = pd.period_range("1953-04", "2026-08", freq="M")
                self._g[key] = pd.Series(4 + np.cumsum(r.normal(0, 0.12, len(m))), index=m)
        return self._g[key]

    def unrate_first(self):
        if "ur" not in self._g:
            m = pd.period_range("1948-01", "2026-08", freq="M")
            self._g["ur"] = pd.DataFrame({"value": 5 + np.cumsum(np.random.default_rng(8).normal(0, 0.15, len(m))),
                                          "first_vintage": [(p + 1).start_time.strftime("%Y-%m-%d") for p in m], "first_release": True}, index=m)
        return self._g["ur"]

    def cboe_d(self, name):
        key = ("cboe", name)
        if key not in self._g:
            r = np.random.default_rng(len(name) + 20)
            if name == "VIX":
                days = pd.bdate_range("1990-01-02", "2026-09-22")
                self._g[key] = pd.Series(12 + np.abs(r.normal(8, 6, len(days))), index=days)
            else:
                days = pd.bdate_range("1986-06-20", "2026-09-22")
                self._g[key] = pd.Series(100 * np.exp(np.cumsum(r.normal(0.0003, 0.007, len(days)))), index=days)
        return self._g[key]

    def aqr(self, aid, col):
        key = ("aqr", aid)
        if key not in self._g:
            r = np.random.default_rng(30 + len(aid))
            m = pd.period_range("1985-01", "2026-05", freq="M") if aid == "TSMOM" else pd.period_range("1930-12", "2026-07", freq="M")
            self._g[key] = pd.Series(r.normal(0.005, 0.03, len(m)), index=m)
        return self._g[key]

    def wurgler(self):
        if "w" not in self._g:
            m = pd.period_range("1958-01", "2025-12", freq="M")
            r = np.random.default_rng(9)
            f = np.cumsum(r.normal(0, 0.2, len(m)))
            W = pd.DataFrame({c: f * s + r.normal(0, 0.5, len(m)) for c, s in zip(TS.SENT_COMPS, (-1, 1, 1, -1, 0.5))}, index=m)
            W.loc[W.index < P("1965-07"), "cefd"] = np.nan
            W["SENT"] = f
            W["SENT_ORTH"] = f + r.normal(0, 0.1, len(m))
            self._g["w"] = W
        return self._g["w"]

    def sp500tr_d(self):
        if "sptrd" not in self._g:
            days = pd.bdate_range("1988-01-04", "2026-09-24")
            self._g["sptrd"] = pd.Series(250 * np.exp(np.cumsum(np.random.default_rng(12).normal(0.0004, 0.011, len(days)))), index=days)
        return self._g["sptrd"]

    def _half(self, cols):
        self._need("beme")
        return self._leg_series("beme", "half:" + ",".join(cols))

    def ff3_vintage(self, v):
        f = self._ff3.copy()
        f["Mkt-RF"] = f["Mkt-RF"] + np.random.default_rng(len(v)).normal(0, 0.0005, len(f))
        return f


class FakeSData(SData):
    def __init__(self):
        super().__init__()
        W, mkt_m, rf_m = TP.fake_world(n_names=60, seed=5)
        self._W, self._mkt, self._rf = W, mkt_m, rf_m
        self._firsts = {"SPY": "1993-01-29", "BIL": "2007-05-30", "SPLV": "2011-05-05", "SPHB": "2011-05-05", "QUAL": "2013-07-18",
                        "RPV": "2006-03-07", "IVE": "2000-05-26", "IVW": "2000-05-26", "IWD": "2000-05-26", "IWF": "2000-05-26",
                        "VTV": "2004-01-30", "VUG": "2004-01-30", "MTUM": "2013-04-18", "SPMO": "2015-10-12", "XYLD": "2013-06-24",
                        "AQMIX": "2010-01-05", "DBMF": "2019-05-08", "RYMFX": "2007-02-22", "PKW": "2006-12-20", "SYLD": "2013-05-14",
                        "COWZ": "2016-12-22"}

    def d(self, tk):
        key = ("d", tk)
        if key not in self._c:
            days = pd.bdate_range(self._firsts.get(tk, "2000-01-03"), "2026-09-25")
            r = np.random.default_rng(abs(hash(tk)) % (2 ** 31))
            mu = 0.00001 if tk == "BIL" else 0.0003
            sd = 0.0001 if tk == "BIL" else 0.011
            self._c[key] = pd.Series(50 * np.exp(np.cumsum(r.normal(mu, sd, len(days)))), index=days)
        return self._c[key]

    def panel(self):
        if "panel" not in self._c:
            self._c["panel"] = TP.Panel(self._W, self._mkt, self._rf)
        return self._c["panel"]


def _hand_checks():
    """규칙 손 계산 — T01 · T03 · T16 · T17 · T02 · T15 한 달씩(합성)."""
    D = FakeData()
    S = FakeSData()
    ctx = Ctx(D, S, events_S=_fake_events_S(), taus={s: {"tau": 1.0} for s in TP.SORTS}, make_data=FakeData)
    f = D.ff3()
    t = P("1990-06")
    a, _ = T01().build_L(D, ctx)
    G = TS.ghm(f["Mkt-RF"])
    w = G["med"][t - 1]
    assert abs(a["rule"].S[t] - (f["Mkt"][t] + 0.5 * w * f["Mkt-RF"][t])) < 1e-12
    a3, _ = T03().build_L(D, ctx)
    L = D.leg("beta:Lo 20")
    b = TS.beta_roll(L - f["RF"], f["Mkt-RF"])[t - 1]
    assert abs(a3["rule"].S[t] - (L[t] + (1 - b) * f["Mkt-RF"][t])) < 1e-12 and 0.5 <= b <= 1.0
    a16, _ = T16().build_L(D, ctx)
    want = np.mean([D.leg("%s:Hi 30" % x)[t] for x in T16.AXES])
    assert abs(a16["rule"].S[t] - want) < 1e-12
    c17 = T17()
    a17, _ = c17.build_L(D, ctx)
    reg = TS.d13_regime(D.fred("GS10"))["regime"][t - 1]
    wv = TS.D13_W[int(reg)]
    assert abs(a17["rule"].S[t] - (wv * D.leg(T17.V)[t] + (1 - wv) * D.leg(T17.G)[t])) < 1e-12
    a2, _ = T02().build_L(D, ctx)
    k = TS.tsmom_scale(D.aqr("TSMOM", "TSMOM"))[t - 1]
    X2 = a2["rule"].X()
    assert abs(X2[t] - 0.1 * (k * D.aqr("TSMOM", "TSMOM")[t] - 0.02 / 12)) < 1e-12
    a15, _ = T15().build_L(D, ctx)
    h = TS.sent_pit(D.wurgler())["high"][t - 1]
    assert abs(a15["rule"].S[t] - (D.leg("var:Lo 20")[t] if h == 1 else D.leg("var:Hi 20")[t])) < 1e-12
    a4, _ = T04().build_L(D, ctx)
    assert a4["C:def_ind"].S.first_valid_index() >= P("1958-07")        # F0 — Hlth 미달이 끝난 뒤부터
    return "손 계산: T01 S = B + ½w·r · T03 L + (1−β̂)(Mkt−RF) · T16 네 축 평균 · T17 70/50/30 · T02 X = 0.1(k·TS − 2%/12) · T15 HIGH/LOW · F0 연속 절단"


def _fake_events_S():
    idx = C.mrange("2016-09", "2026-08")
    ms = [str(p) for p in idx]
    return C.Events("S", set(ms[::3]), set(ms[::11]), set(ms[5::13]), [], [], [ms[5]], 0.04)


def _st_cards():
    D = FakeData()
    S = FakeSData()
    ctx = Ctx(D, S, events_S=_fake_events_S(), taus={s: {"tau": 1.0} for s in TP.SORTS}, make_data=FakeData)
    ctx.events_L("french", D.B())
    old = C.NPERM
    C.NPERM = 5
    seen = {}
    try:
        for K in CARDS:
            card = K()
            r = evaluate_card(card, D, S, ctx, nperm=5, lookahead_n=8)
            json.dumps({k: v for k, v in r.items()}, ensure_ascii=False, default=C.js_default)
            seen[card.id] = r
    finally:
        C.NPERM = old
    assert set(seen) == {K.id for K in CARDS}
    assert not seen["T02"]["forward_ok"] and seen["T02"]["spec"]["forward_allowed"] is False
    assert set(C.H_T0_MEMBERS) == {c for c in seen if seen[c]["spec"]["h_t0"]}
    assert all("rule" in r["S"]["arms"] for r in seen.values())
    for c in ("T04", "T05", "T08", "T15", "T17", "T12"):
        h = seen[c]["L"]["h2"]
        assert h is not None and h["n_perm"] == 5 and h["delta_obs"] is not None, c
    assert seen["T12"]["L"]["h2"]["report_only"] and "h2_rank_ge90" not in seen["T12"]["L"]["g4"]
    for c, r in seen.items():
        assert r["L"]["label"] in C.LABELS.values(), (c, r["L"]["label"])
        assert all(isinstance(v, bool) for k, v in r["L"]["gates"]["G4"]["conds"].items()), c
    v01 = seen["T01"]["L"]["variants"]
    assert set(v01["vintage"]) == {"2024-12", "2005-08"} and v01["vintage"]["2005-08"] is not None and v01.get("sptr") is not None
    v04 = seen["T04"]["L"]["variants"]
    assert v04["vintage"]["2005-08"] is None and "2005-08" in v04["vintage_skipped"]
    assert "all" in seen["T08"]["L"]["variants"]["vintage_skipped"]
    arms = {c: sorted(r["L"]["arms"]) + sorted(r["L"]["lazy"]) for c, r in seen.items()}
    want = {"T01": {"T01-S1", "C:slow", "C:fast", "C:faber", "C:longonly", "C:bearonly", "C:scale1", "C:const"},
            "T02": {"C:none", "C:raw", "C:cost4"}, "T03": {"T03-S1", "C:nofill", "C:ew", "C:var", "C:bab"},
            "T04": {"T04-S1", "C0", "C:static", "C:lo_prior", "C:def_beta", "C:def_ind", "C:slow_only"},
            "T05": {"C0", "C:static", "C:ib_val", "C:bsc", "C:trend12"},
            "T08": {"T08-S1", "C:derisk", "C:always_bxmd", "C:always_sp", "C:roll"}, "T12": {"C0:cash", "C:def_ind", "C:static"},
            "T13": {"C:mom_only", "C:const", "C:val_only"}, "T15": {"C:static", "C:beta_neutral", "C:beta_legs", "C:orth", "C:annual", "C:always_lo"},
            "T16": {"C:axis_beme", "C:axis_cfp", "C:axis_ep", "C:axis_dp", "C:q5", "C:ew"}, "T17": {"C:5050", "C:rr_proxy", "C:static"},
            "T18": {"C:lo20", "C:ew"}}
    for c, w in want.items():
        assert set(arms[c]) == w, (c, sorted(set(arms[c]) ^ w))
    n_arms = sum(r["n_arms_L"] for r in seen.values())
    # G5 해당 없음 — 선언한 칸만
    g02, g12, g01 = (seen[c]["L"]["gates"]["G5"] for c in ("T02", "T12", "T01"))
    assert g02["e_turn"] is None and "e_turn" in g02["na"] and g02["g_sptr"] is None and seen["T02"]["L"]["turn_1w"] is None
    assert g12["c_clean"] is None and set(g12["na"]) == {"c_clean"} and not g01["na"]
    assert all(type(g01[k]) is bool for k in C.G5_KEYS)
    # S 층 — PIT 다리 내부 재구성 비용(τ) · T15 공표 달력 보고판 · 잠정 표시 · 전방 차단
    for c in ("T03", "T04", "T05", "T12", "T15", "T16", "T18"):
        a = seen[c]["S"]["arms"]["rule"]
        assert a["pit_tau"], c
        assert a["cost10"]["mean"] <= a["cost10_switch_only"]["mean"] + 1e-15, c
    assert seen["T01"]["S"]["arms"]["rule"]["pit_tau"] is None
    assert "rpt:pubcal" in seen["T15"]["S"]["arms"] and seen["T15"]["forward_ok"] is False and seen["T15"]["forward_note"]
    assert seen["T04"]["S"]["provisional"] and seen["T16"]["S"]["provisional"] and not seen["T03"]["S"]["provisional"]
    assert seen["T02"]["publish"].startswith("비공개") and seen["T08"]["publish"].startswith("비공개")
    # T13 — 단일 신호 대조의 척도(1 + tilt)
    Wt = T13.weights(D.shiller(), D.ff3()["Mkt-RF"]).dropna()
    assert np.allclose(Wt["w_M"], (1 + Wt["tilt_M"]).clip(0.5, 1.5)) and np.allclose(Wt["w_V"], (1 + Wt["tilt_V"]).clip(0.5, 1.5))
    # 배치 — H_T0 스타우퍼 경로 · D2 민감도(α 없음)
    b = run_batch(CARDS, nperm=3, write=False, lookahead_n=5, D=D, S=S, ctx=ctx)
    assert b["H_T0"]["members"] == list(C.H_T0_MEMBERS) and b["BY_info"]["m"] == 10 and b["n_arms_L"] == n_arms
    assert b["H_T0_sens_exT02"]["report_only"] and "T02" not in b["H_T0_sens_exT02"]["members"] and "reject" not in b["H_T0_sens_exT02"]
    try:
        run_batch(CARDS, nperm=3, write=True, D=D, S=S, ctx=ctx)
        raise AssertionError("등록 커밋 없이 write 가 열렸다")
    except SystemExit:
        pass
    saved = C.frozen_check
    C.frozen_check = lambda: "FAKE"                                     # 판 점검을 흉내 내도 러너 표가 없으면 닫힌다
    try:
        run_batch(CARDS, nperm=3, write=True, D=D, S=S, ctx=ctx)
        raise AssertionError("러너를 거치지 않은 write 가 열렸다")
    except SystemExit as e:
        assert "t_run.py" in str(e)
    finally:
        C.frozen_check = saved
    return ("카드 12장 끝까지(합성 · NPERM 5): 팔 목록 = 설계 · T02 전방 불가 · H_T0 구성원 10 · H2 여섯(T12 보고만) · 판 건너뜀 · 라벨 · 팔 %d · "
            "G5 해당 없음 선언 · S 내부 τ 비용 · T15 공표 달력 · 잠정 · D2 민감도 · write 는 러너로만" % n_arms)


def _st_static():
    import ast
    bad = []
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id == "open":
            if not any(kw.arg == "encoding" for kw in nd.keywords):
                bad.append(nd.lineno)
    assert not bad, bad
    body = src.replace("    print(json.dumps(r", "")
    for arg in ("ev", "X", "res", "out", "LR", "h2"):                   # 계열 · 결과를 그대로 찍는 자리가 없다(연기 시험 출력은 모양뿐)
        assert ("print" + "(" + arg) not in body, arg
    return "open() encoding · 계열 print 없음 정적 점검"


def selftest():
    res, ok = [], True
    for fn in (_hand_checks, _st_cards, _st_static):
        try:
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            import traceback
            res.append(("실패", fn.__name__, traceback.format_exc()[-2500:]))
    for st, nm, msg in res:
        print("  %s %-12s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("t_cards selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv
    if "--selftest" in a:
        raise SystemExit(selftest())
    if "--blind-smoke" in a:
        ids = [a[a.index("--card") + 1]] if "--card" in a else None
        r = blind_smoke(ids)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        raise SystemExit(0 if all(v.get("ok", True) for k, v in r.items() if isinstance(v, dict)) else 1)
    if "--run" in a:
        raise SystemExit("🚨 굽기는 build/t_run.py 로만 한다(이 길은 뺐다 — 시작 표식 · 판 · 상수 · 경계를 거치지 않는다).")
    print(__doc__)
