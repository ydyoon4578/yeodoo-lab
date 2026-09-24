# -*- coding: utf-8 -*-
"""build/q_bmrot_leg.py — 배치 Q 수비 엔진 · x-bmrot(B/M 금리 국면 로테이션)을 종목 격자(eg30plus.World) 위에서 다시 만든다.

카드: Q03 · Q10 · Q06 의 DEFENSE 다리(PREREG-2026-09-03-BMROT §1 · 카드 Q03 LEGS). 이 모듈은 카드가 아니라 다리다 — CARDS 가 비어 있다.

근본 이유 — 공격 엔진 EG30(고성장 시총가중 · 바스켓 베타 1.22)이 가장 크게 잃는 곳은 레버리지 축소·위험예산 매도가 고베타·
  고성장 바스켓에 몰리는 하락 국면이다. x-bmrot 은 채점 가능한 명단 전부를 B/M 중앙값으로 반씩 나눠 동일가중으로 들고,
  실질금리(DFII10)가 오르는 국면에만 가치 쪽으로 기울인다 — 시총 집중도 성장 틸트도 없는 넓은 바스켓이라 EG30 과 능동수익
  상관이 음(EGBEST −0.52)이다. 교체 카드는 이 두 엔진 사이를 국면 신호로 오간다.

규칙(§1 그대로 · 수는 탐색 풀 카드 D13 의 것) — 채점·선택은 **랩의 한 벌**(TB.xsec_score_at · TB.xsec_pick_at → _bmrot_pick)을 그대로 부른다:
  · 월말 m 에 그달 S&P 500 ∪ NASDAQ 100 명단(index_members.at · 이중클래스 줄이지 않음) ∩ PIT 가격 지도(pit_backtest.load_prices —
    오늘 유니버스 sd + 편출 캐시 _pit_px_cache.json · 재사용 방어 · 꼬리 절단 · 크기 검사 · CIK 승계)
  · 시총 = 주식수(90일 공시 지연) × 월말 종가 · 시총이 선 명단의 하위 20% 를 자른다(랩 기본 MCF_CUT · PREREG-2026-08-25-DEFAULT-PIT —
    게시된 x-bmrot PIT 계열도 이 하한을 탔다)
  · 점수 = 자기자본(90일 지연) ÷ 시총 · 내림차순 · 앞 절반 = 가치 다리 · 뒤 절반 = 성장 다리(100종 미만이면 직전 바스켓 유지)
  · DFII10 달력 3개월 변화 ≥ +0.20%p → 가치 70 / 성장 30 · ≤ −0.20%p → 30/70 · 그 사이 50/50 · 다리 안은 동일가중
  · 월말 종가에 매매(게시 계열과 같다 — 신호일 i−1 의 명단이 i 일 수익부터 든다) · 날짜 격자 = stocks.json pxd_dates = eg30plus.World.dates
두 회계:
  · "pub"  게시 계열의 회계 — 총수익(비용 없음) · 매일 목표 비중으로 되맞춤(TB.weighted_ret · 결측은 남은 비중으로 되정규화). 재현 관문 전용.
  · "leg"  카드의 다리 — 월간 되맞춤 · 일간 흘러감 · 편도 cost(qbatch_core.stock_path = qg_lab.sleeve · 상장폐지는 마지막 가격 보유).
재현 관문(등록 전 · 후보 계산 아님): pub 회계 월 수익과 data/strategy_charts.json 의 t-x-bmrot 월 수익(pit_strategies.json 에서 옮긴 PIT 레그)의
  월별 |Δ| 최대가 1bp 이하. 수준은 찍지 않는다 — 차이만 낸다.
🚨 가격 지도가 종목 격자(pit_px.json 정리본)가 아니라 편출 캐시인 이유(2026-09-25 진단): 정리본은 벤더가 더는 안 주는 인수 종목
  (EA · ESRX · AET · TWX · ANDV · SCG · HOT …)을 남겨 두지만, 게시 PIT 계열은 캐시를 읽어 그 이름들이 빠져 있다. 정리본 위에서 같은
  규칙을 돌리면 바스켓이 119/120 달에서 갈려 월 |Δ| 최대 18.6bp 로 관문을 못 넘는다(gate_variants · targets_grid). 관문은 «다리 = 게시된 x-bmrot» 을
  보증하려는 것이라 게시 계열의 가격 지도를 쓴다. 정리본 쪽이 생존편향이 덜하다 — 그 차이는 한계로 적는다.
⚠ 회계 차이(2026-09-25 진단 · 차이만): 카드 다리(월간 되맞춤 · 흘러감)와 게시 회계(매일 되맞춤)의 월 |Δ| 최대 59.7bp(총) · 61.2bp(10bp).
관문 방식(선언 · GATE_MODE = "composition"): 재현 관문은 **구성 관문**이다 — 명단 · 비중 · 틸트를 게시 계열의 회계(총수익 · 매일 목표 비중)로
  재서 월 |Δ| ≤ 1bp. 교체 틀이 사고파는 장부는 같은 목표의 월간 되맞춤 · 일간 흘러감 · 편도 10bp 판(카드 LEGS 문구)이다. 게시 계열은
  매일 되맞춤 · 비용 없음이라 거래 가능한 장부가 아니다 — 카드의 두 문장(«월간 되맞춤 · 흘러감» 과 «게시 월 수익 ≤ 1bp»)은 글자 그대로
  함께 설 수 없어서, 관문의 뜻(재생성 코드 = 게시 규칙)을 구성으로 지키고 회계 차이는 선언한다. T-bill 대체로 바꾸려면 q_switch.DEFENSE_LEG.
얼린 핀(굽기에서 verify_pins 가 다시 단언 — 하나라도 다르면 멈춘다): 목표 해시 · 가격 지도 해시 · 편출 캐시 blob · 게시 계열 blob · 재현 관문 통과.
출처: build/PREREG-2026-09-03-BMROT.md §1 · build/tech_backtest.py _bmrot_pick(8845) · x-bmrot 채점(8081) · mcap_floor(1333) ·
  build/pit_backtest.py run()(월말 리밸 · weighted_ret) · build/pit_panel.py _key(날짜 인식 키).
"""
from __future__ import annotations
import bisect, hashlib, io, json, os, subprocess, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CARDS = {}                            # 다리 모듈 — 카드를 내지 않는다
NPERM = 0
TILT = 0.20                           # DFII10 3개월 변화 문턱(%p) — 카드 D13
W_HI, W_LO, W_MID = 0.7, 0.3, 0.5     # 가치 다리 몫
MIN_SPLIT = 100                       # _bmrot_pick — 반씩 쪼개려면 양쪽 50종
MCF_CUT = 0.20                        # tech_backtest.MCF_CUT(랩 기본 시총 하한 · 하위 20% 절단)
LAG = 90                              # tech_backtest.FUND_LAG_DAYS
PUB_FILE, PUB_SID = "strategy_charts.json", "t-x-bmrot"
GATE_BP = 1.0
GATE_MODE = "composition"             # 구성 관문(게시 회계로 명단 · 비중 · 틸트) · 거래 장부 = 월간 되맞춤 · 흘러감(카드 LEGS)
CACHE_FILE = "_pit_px_cache.json"     # pit_backtest.load_prices 가 읽는 편출 캐시(eg30plus SNAP/BASE 밖 → 여기서 핀)
# 얼린 핀(2026-09-25 · snap_wt = 가격 940f0bda · 나머지 bef4eea8 · 수준 없이 해시만)
FROZEN_THASH = "34cc8bb5c4ec6ad30d678f5b5fa695b3d0caab679d35e0c36b969a3368c63e2e"
FROZEN_PXHASH = "d7ddb2001cc8f556f80078adfaf37c1e1e504d33a7d521dd36c88763b94a6deb"
FROZEN_CACHE_BLOB = "f8c1a16ba22c89f54999cf4291807feb30c53225"
FROZEN_PUB_BLOB = "cc67b1bb142593d60e8143643aae578a146bd7da"
# 게시 가격 지도가 빠뜨리고 P1 정리본(pit_px.json)엔 있는 이름(targets_grid − targets · 달 수) — 인수 · 비상장 종목(생존편향)
MISSING_VS_P1 = (("EA", 119), ("ESRX", 28), ("AET", 27), ("TWX", 22), ("ANDV", 14), ("SCG", 7), ("HOT", 1))
MISSING_VS_P1_BOUNDARY = 57           # 그 밖 1~4달만 갈린 경계 이름 수(중앙값 · 시총 하한 자리의 연쇄)
HOLD0, HOLD1 = Q.HOLD0, Q.HOLD1
_CACHE = {}


def _raw(t):
    """pit_panel 명단 티커('BRK-B') → index_history 원 표기('BRK.B') — pit_backtest 가 쓰는 이름."""
    return t.replace("-", ".")


def _span(Wd):
    """명단 티커 → 창(2016-08~) 안 마지막 멤버월(pit_backtest MEMBER_SPAN 의 hi)."""
    L = Wd.W["lists"]
    hi = {}
    for ix in ("spx", "ndx"):
        for m in sorted(L[ix]):
            if m < Q.FORM0:
                continue
            for t in L[ix][m]:
                if hi.get(t, "") < m:
                    hi[t] = m
    return hi


def _fund(Wd, t):
    """재무 사전 — pit_backtest 와 같은 순서: 원 표기 → 명단 표기 → CIK 승계 티커."""
    F = Wd.W["FUND"]
    r = _raw(t)
    for c in (r, t):
        if c in F:
            return F[c]
    sp = Wd.W["splice"]
    a = sp.get(r) or sp.get(t)
    return F.get(a) or {}


def targets_grid(Wd):
    """진단 전용 — 같은 규칙을 종목 격자(pit_panel 키 · pit_px.json 정리본) 위에서 손으로 옮긴 판. 관문 실패의 원인을 재는 데만 쓴다."""
    key = ("TG", id(Wd))
    if key in _CACHE:
        return _CACHE[key]
    import pit_panel as PP
    import tech_backtest as TB
    W, PX, dates = Wd.W, Wd.PX, Wd.dates
    mr = TB.macro_level("DFII10", dates)
    Amac = (json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8")).get("macro") or {}).get("DFII10") or {}
    hi = _span(Wd)
    today, reas = W["today"], W["reassigned"]
    L = W["lists"]
    T, log = {}, []
    for m in Wd.months:
        i = Wd.me[m]
        d = dates[i]
        ltd = d
        assert d[:7] == m and (i + 1 >= len(dates) or dates[i + 1][:7] != m), "월말 자리가 그달 마지막 거래일이 아니다"
        mem = sorted(set(L["spx"].get(m) or []) | set(L["ndx"].get(m) or []))
        pool, mc = [], {}
        rows = {}
        for t in mem:
            k = PP._key(W, t, i)
            if k is None:
                continue                                    # 가격 계열이 없다 — pit_backtest 의 px_map 밖
            pool.append(t)
            f = _fund(Wd, t)
            p0 = PX[k][i]
            sn = TB.asof_fund(f.get("sh"), d)
            ok_p = bool(p0 == p0 and p0 > 0)
            if sn and ok_p and sn > 0:
                mc[t] = sn * float(p0)
            rows[t] = (k, f, ok_p)
        # 시총 하한(하위 20% 절단 · 시총을 모르는 이름은 통과)
        thr = None
        if len(mc) >= 2:
            vals = sorted(mc.values())
            thr = vals[int(len(vals) * MCF_CUT)]
        kept = [t for t in pool if mc.get(t) is None or thr is None or mc[t] >= thr]
        sc = []
        cut_d = TB._shift(d, LAG)
        for t in kept:
            k, f, ok_p = rows[t]
            if t not in mc:
                continue
            e = TB.asof_fund(f.get("eq"), d)
            if e is None:
                continue
            # PIT 단언 — 쓴 재무 관측의 기준일이 신호일 − 90일 이하
            for fld in ("eq", "sh"):
                ser = f.get(fld) or []
                used = next((dd for dd, _v in ser if dd <= cut_d), None)
                assert used is not None and used <= cut_d < ltd, "재무 지연 위반 %s %s %s" % (t, fld, m)
            sc.append((e / mc[t], _raw(t), t))
        sc.sort(reverse=True)
        if len(sc) < MIN_SPLIT:
            raise RuntimeError("x-bmrot %s 채점 %d종 < %d — 규칙상 무보유(게시 계열도 그랬다면 직전 바스켓 유지)" % (m, len(sc), MIN_SPLIT))
        h = len(sc) // 2
        val, grw = sc[:h], sc[h:]
        # DFII10 — 달력 3개월(같은 날짜 문자열의 3개월 전 이하 마지막 거래일) · 격자 ffill 수준(macro_level)
        y, mm = int(d[:4]), int(d[5:7]) - 3
        y += (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        tgt = "%04d-%02d-%s" % (y, mm, d[8:10])
        j = bisect.bisect_right(dates, tgt) - 1
        now, prev = mr[i], (mr[j] if j >= 0 else None)
        last_obs = max((dd for dd in Amac if dd <= d), default=None)
        assert last_obs is None or last_obs <= ltd
        if now is None or prev is None:
            w = W_MID
            ch = None
        else:
            ch = now - prev
            w = W_HI if ch >= TILT else (W_LO if ch <= -TILT else W_MID)
        wt, names = {}, {}
        for _v, _r, t in val:
            k = rows[t][0]
            assert k not in wt, "가격 키 중복 %s %s" % (k, m)
            wt[k] = w / len(val); names[k] = t
        for _v, _r, t in grw:
            k = rows[t][0]
            assert k not in wt, "가격 키 중복 %s %s" % (k, m)
            wt[k] = (1 - w) / len(grw); names[k] = t
        # 재배정 티커의 마지막 멤버월 — pit_backtest 는 그 뒤 가격을 잘라 다음 달 수익이 결측(되정규화) → 뽑되 바스켓 전체로 되정규화
        #   ⚠ CIK 승계 티커로 값을 잇는 경우(LB → BBWI)는 재배정 절단을 안 건다(pit_backtest.load_prices 의 승계 갈래).
        drop = [k for k, t in names.items() if t in reas and t not in today and k in (t, _raw(t)) and m >= hi.get(t, "9999")]
        dropped = [names[k] for k in drop]
        if drop:
            s = 1.0 - sum(wt[k] for k in drop)
            for k in drop:
                wt.pop(k); names.pop(k)
            wt = {k: v / s for k, v in wt.items()}
        assert abs(sum(wt.values()) - 1) < 1e-9
        T[m] = {"w": wt, "names": names}
        log.append({"m": m, "n_mem": len(mem), "n_pool": len(pool), "n_mcap": len(mc), "n_kept": len(kept), "n_scored": len(sc),
                    "n_val": len(val), "n_grw": len(grw), "w_val": w, "dfii_ch": (None if ch is None else round(ch, 4)),
                    "drop_reassigned": dropped, "max_w": max(wt.values())})
    _CACHE[key] = (T, log)
    return T, log


def _pb(Wd):
    """게시 PIT 레그와 같은 입력 — pit_backtest.main 의 X 중 x-bmrot 채점이 읽는 것만. 가격 지도는 pit_backtest.load_prices."""
    key = ("PB", id(Wd))
    if key in _CACHE:
        return _CACHE[key]
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        import tech_backtest as TB
        import pit_backtest as PB
        import index_members as IM
        mem = PB.fetch_members()
        need = set()
        for v in mem.values():
            need |= set(v)
        span = {}
        for ym, lst in mem.items():
            for t in lst:
                a, b = span.get(t, (ym, ym))
                span[t] = (min(a, ym), max(b, ym))
        px_map, rep = PB.load_prices(need, span, mem)
        alias = (rep.get("cik_splice") or {}).get("map") or {}
        st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
        dates = list(st["pxd_dates"])
        assert dates == list(Wd.dates), "게시 레그 격자 ≠ 종목 격자"
        n = len(dates)
        tickers = sorted(px_map)
        px = {t: [px_map[t].get(d) for d in dates] for t in tickers}
        fu = TB.load_fund(extra_dirs=[os.path.join(DATA, "fx_pit")])
        for t, a in sorted(alias.items()):
            if t not in fu and fu.get(a):
                fu[t] = fu[a]
        me_l = TB.month_ends(dates)
        X = {"FACP": {}, "FU": fu, "R": {}, "dates": dates, "hid": {}, "lod": {}, "ixr": [0.0] * n, "ixvol": [None] * n,
             "me": set(me_l), "me_list": me_l, "meta": {}, "px": px, "vlm": {t: None for t in tickers}, "tickers": tickers,
             "macd10": [None] * n, "macfx": [None] * n, "mac_real": TB.macro_level("DFII10", dates),
             "mac_curve": TB.macro_level("T10Y2Y", dates), "mac_usd": TB.macro_level("DTWEXBGS", dates)}
        TB.build_strats()
        S = {s_["sid"]: s_ for s_ in TB.STRATS}["x-bmrot"]
    assert S.get("reb", "me") == "me"
    PXb = {t: np.array([np.nan if v is None else float(v) for v in px[t]]) for t in tickers}
    out = {"mem": mem, "X": X, "S": S, "PX": PXb, "alias": alias, "IM": IM, "TB": TB,
           "rep": {"n_px": len(px_map), "n_alias": len(alias), "n_cut": rep.get("n_cut"), "n_bad_scale": rep.get("n_bad_scale"),
                   "n_dropped": rep.get("n_dropped")}}
    _CACHE[key] = out
    return out


def targets(Wd):
    """월말 m(2016-08 ~ 2026-07) → {"w": {가격키: 비중}, "names": {가격키: 티커}} · 기록. 채점·선택은 TB 한 벌."""
    key = ("T", id(Wd))
    if key in _CACHE:
        return _CACHE[key]
    P = _pb(Wd)
    TB, IM, X, S = P["TB"], P["IM"], P["X"], P["S"]
    dates = X["dates"]
    Amac = (json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8")).get("macro") or {}).get("DFII10") or {}
    T, log, hold, hw = {}, [], [], None
    for m in Wd.months:
        i1 = Wd.me[m]                                   # 신호일(월말 종가)
        i = i1 + 1                                      # pit_backtest 의 i — 이 날 수익부터 새 바스켓
        d = dates[i1]
        assert d[:7] == m and dates[i][:7] != m, "월말 자리가 그달 마지막 거래일이 아니다"
        pool = IM.at(P["mem"], m, say=None)
        sc, ind_raw, _cr = TB.xsec_score_at(S, i, X, pool)
        n_sc = len(sc)
        if n_sc >= TB.min_pool(S["sid"]):
            new, new_w = TB.xsec_pick_at(S, i, X, sc, ind_raw, held=hold)
            if new:
                hold, hw = new, new_w
        assert hw, "x-bmrot %s 바스켓이 없다" % m
        # PIT 단언 — 쓴 재무 관측(자기자본 · 주식수)의 기준일 ≤ 신호일 − 90일 < 그달 마지막 거래일 · DFII10 관측 ≤ 신호일
        cut_d = TB._shift(d, LAG)
        for t in hold:
            f = X["FU"].get(t) or {}
            for fld in ("eq", "sh"):
                used = next((dd for dd, _v in (f.get(fld) or []) if dd <= cut_d), None)
                assert used is not None and used <= cut_d < d, "재무 지연 위반 %s %s %s" % (t, fld, m)
            assert P["PX"][t][i1] == P["PX"][t][i1] and P["PX"][t][i1] > 0
        last_obs = max((dd for dd in Amac if dd <= d), default=None)
        assert last_obs is None or last_obs <= d
        w = {t: float(hw[t]) for t in sorted(hold)}
        assert abs(sum(w.values()) - 1) < 1e-9 and min(w.values()) > 0
        T[m] = {"w": w, "names": {t: t for t in w}}
        vals = sorted(set(round(x, 12) for x in w.values()))
        log.append({"m": m, "n_pool": len(pool), "n_scored": n_sc, "n_basket": len(w), "w_levels": vals,
                    "w_val": _tilt_of(w, sc), "max_w": max(w.values())})
    _CACHE[key] = (T, log)
    return T, log


def _tilt_of(w, sc):
    """가치 다리 몫(기록용) — 점수 앞 절반의 비중 합."""
    h = len(sc) // 2
    return round(sum(w.get(t, 0.0) for _v, t in sc[:h]), 6)


# ── 경로 ─────────────────────────────────────────────────────────────────
class _Book:
    """qg_lab.sleeve 를 게시 레그의 가격 지도로 돌리는 얇은 틀 — 날짜 · 월말 · 무위험은 종목 격자(Wd)의 것."""

    def __init__(self, Wd, PX):
        import eg30plus as E
        import qg_lab as QL
        self.PX, self.me, self.months, self.RF, self.dates = PX, Wd.me, Wd.months, Wd.RF, Wd.dates
        self._w, self._s = E.World.weights, QL.World.sleeve

    def weights(self, cand, m):
        return self._w(self, cand, m)

    def sleeve(self, cand):
        return self._s(self, cand)


def pub_path(Wd, T, PX=None):
    """게시 계열의 회계 — 총수익 · 매일 목표 비중(결측 되정규화 · TB.weighted_ret 과 같은 식). {날 인덱스: NAV}(첫 편입 월말 = 1)."""
    PX = PX if PX is not None else _pb(Wd)["PX"]
    months = Wd.months
    i0 = Wd.me[months[0]]
    path = {i0: 1.0}
    v = 1.0
    for m in months:
        i, i1 = Wd.me[m], Wd.me[Q.mshift(m, 1)]
        ks = sorted(T[m]["w"])
        w = np.array([T[m]["w"][k] for k in ks])
        P = np.array([PX[k][i:i1 + 1] for k in ks], float)          # (n, 1 + 일수)
        p0, p1 = P[:, :-1], P[:, 1:]
        with np.errstate(invalid="ignore", divide="ignore"):
            ok = (p0 == p0) & (p1 == p1) & (p0 > 0) & (p1 != 0)
            R = np.where(ok, p1 / np.where(ok, p0, 1.0) - 1.0, 0.0)
        sw = (w[:, None] * ok).sum(0)
        r = np.where(sw > 0, (w[:, None] * R).sum(0) / np.where(sw > 0, sw, 1.0), 0.0)
        for dd in range(i + 1, i1 + 1):
            v *= 1.0 + r[dd - i - 1]
            path[dd] = v
    return path


def leg_path(Wd, T, cost=Q.COST):
    """카드의 다리 — 월간 되맞춤 · 일간 흘러감 · 편도 cost(qbatch_core.stock_path · 게시 레그 가격 지도)."""
    key = ("L", id(Wd), cost)
    if key not in _CACHE:
        _CACHE[key] = Q.stock_path(_Book(Wd, _pb(Wd)["PX"]), T, reb=1, cost=cost)
    return _CACHE[key]


def leg(ctx, cost=Q.COST):
    """부르는 쪽(교체 틀)이 쓰는 한 줄 — 수비 다리 슬리브 경로 {"path", "turn", "books"}."""
    T, _ = targets(ctx.Wd)
    return leg_path(ctx.Wd, T, cost)


def monthly_of(Wd, path):
    """보유월(2016-09 ~ 2026-08) → 월 수익(%)."""
    out = {}
    for m in Wd.months:
        h = Q.mshift(m, 1)
        a, b = Wd.me[m], Wd.me[h]
        out[h] = (path[b] / path[a] - 1.0) * 100
    return out


# ── 재현 관문 ─────────────────────────────────────────────────────────────
def _published():
    p = os.path.join(DATA, PUB_FILE)
    raw = open(p, "rb").read()
    blob = subprocess.run(["git", "hash-object", p], capture_output=True, text=True).stdout.strip()
    ch = json.loads(raw.decode("utf-8"))["charts"][PUB_SID]
    mon = {x["m"]: x["r"] for x in ch["monthly"]}
    sha = hashlib.sha256(json.dumps(ch["monthly"], sort_keys=True).encode()).hexdigest()
    return mon, {"file": "data/" + PUB_FILE, "blob": blob, "monthly_sha256": sha, "src": "pit_strategies.json(PIT 레그)"}


def _diff(Wd, mine_path):
    mine = monthly_of(Wd, mine_path)
    pub, meta = _published()
    hold = [h for h in sorted(mine) if HOLD0 <= h <= HOLD1]
    miss = [h for h in hold if pub.get(h) is None]
    d = {h: (mine[h] - pub[h]) * 100 for h in hold if pub.get(h) is not None}          # bp
    return d, miss, meta


def repro_gate(ctx):
    """pub 회계로 다시 만든 월 수익 − 게시 월 수익(bp · 게시는 %의 소수 둘째 자리 반올림 → 반올림 오차 ≤ 0.5bp). 수준은 돌려주지 않는다."""
    Wd = ctx.Wd
    T, log = targets(Wd)
    d, miss, meta = _diff(Wd, pub_path(Wd, T))
    over = {h: round(v, 2) for h, v in sorted(d.items()) if abs(v) > GATE_BP}
    mx = max(abs(v) for v in d.values())
    return {"n": len(d), "missing": miss, "max_abs_bp": round(mx, 3), "n_over_1bp": len(over), "over_1bp": over,
            "pass": bool(not miss and mx <= GATE_BP), "pub": meta, "targets_hash": thash(T), "price_map": _pb(Wd)["rep"]}


def gate_variants(ctx):
    """진단 — 다리 회계(흘러감 · 비용 0 / 10bp)와 게시 계열의 월별 |Δ| 최대(bp) · 종목 격자 판(grid)의 |Δ| 최대와 바스켓 차이. 차이만."""
    Wd = ctx.Wd
    T, _ = targets(Wd)
    out = {}
    for nm, cost in (("drift_gross", 0.0), ("drift_10bp", Q.COST)):
        d, _m, _x = _diff(Wd, Q.stock_path(_Book(Wd, _pb(Wd)["PX"]), T, reb=1, cost=cost)["path"])
        out[nm] = round(max(abs(v) for v in d.values()), 2)
    Tg, _lg = targets_grid(Wd)
    d, _m, _x = _diff(Wd, pub_path(Wd, Tg, Wd.PX))
    only_g, only_p, nm_diff = {}, {}, 0
    for m in sorted(T):
        a = {_raw(t) for t in Tg[m]["names"].values()}
        b = set(T[m]["w"])
        if a != b:
            nm_diff += 1
        for x in a - b:
            only_g[x] = only_g.get(x, 0) + 1
        for x in b - a:
            only_p[x] = only_p.get(x, 0) + 1
    out["grid"] = {"max_abs_bp": round(max(abs(v) for v in d.values()), 2), "n_over_1bp": int(sum(abs(v) > GATE_BP for v in d.values())),
                   "months_basket_differs": nm_diff,
                   "only_grid_top": sorted(only_g.items(), key=lambda kv: (-kv[1], kv[0]))[:15],
                   "only_pub_top": sorted(only_p.items(), key=lambda kv: (-kv[1], kv[0]))[:15]}
    return out


def thash(T):
    return hashlib.sha256(json.dumps({m: {"w": {k: round(v, 12) for k, v in sorted(x["w"].items())}} for m, x in sorted(T.items())},
                                     sort_keys=True).encode()).hexdigest()


def pxhash(Wd, T, PX=None):
    """가격 지도 해시 — 목표에 한 번이라도 든 키(정렬) · 보유 창(첫 편입 월말 ~ 마지막 보유 월말) float64 원바이트. 입력 핀(수익 아님)."""
    PX = PX if PX is not None else _pb(Wd)["PX"]
    i0, iE = Wd.me[Wd.months[0]], Wd.me[Q.mshift(Wd.months[-1], 1)]
    h = hashlib.sha256()
    for k in sorted({k for x in T.values() for k in x["w"]}):
        h.update(k.encode())
        h.update(np.ascontiguousarray(PX[k][i0:iE + 1], dtype="<f8").tobytes())
    return h.hexdigest()


def _blob(rel):
    """git blob 해시(체크아웃 줄바꿈 설정과 무관) — git 이 없으면 빈 문자열(단언이 멈춘다)."""
    p = os.path.join(ROOT, rel)
    try:
        return subprocess.run(["git", "hash-object", p], capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def verify_pins(ctx):
    """굽기 단언 — 편출 캐시 · 게시 계열 blob · 목표 해시 · 가격 지도 해시 · 재현 관문(구성 · ≤ 1bp). 하나라도 어긋나면 AssertionError.
    수비 장부를 만들기 전에 q_switch.defense_bmrot 가 부른다. 돌려주는 것은 해시 · 차이만(수준 없음)."""
    key = ("PIN", id(ctx.Wd))
    if key in _CACHE:
        return _CACHE[key]
    Wd = ctx.Wd
    T, _ = targets(Wd)
    got = {"cache_blob": _blob(os.path.join("data", CACHE_FILE)), "pub_blob": _blob(os.path.join("data", PUB_FILE)),
           "targets_hash": thash(T), "px_hash": pxhash(Wd, T)}
    want = {"cache_blob": FROZEN_CACHE_BLOB, "pub_blob": FROZEN_PUB_BLOB, "targets_hash": FROZEN_THASH, "px_hash": FROZEN_PXHASH}
    bad = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
    assert not bad, "x-bmrot 다리 핀이 얼린 값과 다르다: %s" % bad
    g = repro_gate(ctx)
    assert g["pass"] and g["pub"]["blob"] == FROZEN_PUB_BLOB, "x-bmrot 재현 관문 실패(최대 %.3fbp · 결측 %s)" % (g["max_abs_bp"], g["missing"])
    out = dict(got, gate_mode=GATE_MODE, gate_max_abs_bp=float(g["max_abs_bp"]), gate_n=g["n"], gate_pass=True)
    _CACHE[key] = out
    return out


# 교체 카드(Q03 · Q10 · Q06)의 log["interpretation"] 에 싣는 수비 다리 선언 — 카드 §1 과 다르게 읽은 곳 · 한계
INTERP_LEG = [
    "수비 다리 재현 관문 = 구성 관문(GATE_MODE composition): 명단 · 비중 · 틸트를 게시 PIT x-bmrot 의 회계(총수익 · 매일 목표 비중 되맞춤)로 재서 "
    "월 |Δ| ≤ 1bp(120/120달 · 최대 0.49bp · 게시 수익은 0.01% 반올림). 교체가 사고파는 장부는 같은 목표의 월간 되맞춤 · 일간 흘러감 · 편도 10bp 판"
    "(카드 LEGS 문구) — 게시 계열과 월 |Δ| 최대 59.7bp(총) · 61.2bp(10bp) 다르다(회계 차이 · 선언 · 카드 수정 필요)",
    "가격 지도 = 게시 계열과 같은 pit_backtest.load_prices(오늘 sd + 편출 캐시 data/_pit_px_cache.json blob f8c1a16b) — P1 정리본(pit_px.json)엔 있는 "
    "인수 · 비상장 종목이 빠진다: " + " · ".join("%s %d달" % kv for kv in MISSING_VS_P1) +
    " (+ 1~4달만 갈린 경계 이름 %d종) → 수비 다리 생존편향(한계 · 정리본 판은 관문 18.6bp 로 실패)" % MISSING_VS_P1_BOUNDARY,
    "랩 기본 시총 하한(MCF_CUT · 선 명단 하위 20% 절단 · PREREG-2026-08-25-DEFAULT-PIT)을 탄다 — BMROT §1 의 «채점 가능한 명단 전부» 와 다르다"
    "(게시 계열이 탔다 · 관문이 강제)",
    "이중 클래스를 한 회사로 줄이지 않는다(pit_backtest 규약 · 게시 계열과 같다) · 채점 가능 < 100종이면 직전 바스켓 유지(_bmrot_pick)",
    "DFII10 은 신호일 당일 관측을 쓴다 — 실질금리는 다음 영업일에 발표되므로 1일 앞선 정보다(게시 계열 관문에 묶여 고치지 않는다 · 한계)",
    "B/M 의 자기자본 · 주식수는 최신 제출본(data/fx · fx_pit · 90일 지연) — 재작성 누설(Q01/Q12 와 같은 한계 · 게시 계열 관문에 묶인다)",
    "얼린 핀: 목표 해시 %s… · 가격 지도 해시 %s… · 캐시 blob %s · 게시 계열 blob %s — 굽기에서 verify_pins 가 다시 단언"
    % (FROZEN_THASH[:12], FROZEN_PXHASH[:12], FROZEN_CACHE_BLOB[:8], FROZEN_PUB_BLOB[:8])]


# ── 계약 ─────────────────────────────────────────────────────────────────
def selftest():
    """합성 자료로 — 틸트 문턱(부동소수 경계) · _bmrot_pick 반 가르기 · 시총 하한 · pub 회계의 되정규화 = TB.weighted_ret."""
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        import tech_backtest as TB
    tests = {}
    # 틸트: 경계 부동소수(1.5 − 1.3 = 0.19999… 는 50/50) — _bmrot_pick 과 같은 식
    f = lambda now, prev: (W_HI if now - prev >= TILT else (W_LO if now - prev <= -TILT else W_MID))
    tests["tilt_up"] = f(1.50, 1.30) == W_MID and f(1.51, 1.30) == W_HI
    tests["tilt_dn"] = f(1.00, 1.21) == W_LO and f(1.00, 1.19) == W_MID
    # _bmrot_pick 을 합성 점수로 — 101종이면 가치 50 · 성장 51 · 다리 안 동일가중
    dates = ["2020-%02d-15" % k for k in range(1, 13)]
    X = {"dates": dates, "mac_real": [1.0] * 6 + [1.3] * 6}   # mr[5](06-15) = 1.0 · mr[8](09-15) = 1.3
    sc = sorted([(float(v), "T%03d" % v) for v in range(101)], reverse=True)
    ts, wt = TB._bmrot_pick(sc, X, 9)                   # 신호일 dates[8] = 09-15 · 3개월 전 06-15 → 1.3 − 1.0 = 0.30 ≥ 0.20 → 70/30
    tests["pick_tilt70"] = bool(len(ts) == 101 and abs(wt["T100"] - 0.7 / 50) < 1e-15 and abs(wt["T000"] - 0.3 / 51) < 1e-15)
    Xd = {"dates": dates, "mac_real": [1.3] * 6 + [1.0] * 6}  # 거울: −0.30 ≤ −0.20 → 30/70
    ts, wt = TB._bmrot_pick(sc, Xd, 9)
    tests["pick_tilt30"] = bool(len(ts) == 101 and abs(wt["T100"] - 0.3 / 50) < 1e-15 and abs(wt["T000"] - 0.7 / 51) < 1e-15)
    Xm = {"dates": dates, "mac_real": [1.0] * 6 + [1.15] * 6}  # 0.15 < 0.20 → 50/50
    ts, wt = TB._bmrot_pick(sc, Xm, 9)
    tests["pick_tilt50"] = bool(abs(wt["T100"] - 0.5 / 50) < 1e-15 and abs(wt["T000"] - 0.5 / 51) < 1e-15)
    tests["pick_min100"] = TB._bmrot_pick(sc[:99], X, 9) == ([], None)
    # 시총 하한 — 하위 20%(int(n·0.2) 번째 값 이상)
    vals = sorted([float(x) for x in range(1, 11)])
    thr = vals[int(len(vals) * MCF_CUT)]
    tests["mcap_floor"] = thr == 3.0 and sum(v >= thr for v in vals) == 8
    # pub 회계의 벡터 식 = TB.weighted_ret(결측 되정규화)
    rng = np.random.default_rng(Q.SEED)
    w = rng.random(7); w /= w.sum()
    R = rng.normal(0, 0.01, (7, 5)); ok = rng.random((7, 5)) > 0.3
    sw = (w[:, None] * ok).sum(0)
    r = np.where(sw > 0, (w[:, None] * np.where(ok, R, 0)).sum(0) / np.where(sw > 0, sw, 1), 0.0)
    ref = [TB.weighted_ret([(w[k], R[k, j]) for k in range(7) if ok[k, j]], False) for j in range(5)]
    tests["renorm_eq_weighted_ret"] = bool(np.max(np.abs(r - np.array(ref))) < 1e-15)
    return {"ok": all(bool(v) for v in tests.values()), "tests": tests}


def dry(ctx):
    """구성만 — 개수 · 비중 합 · 틸트 상태 분포 · 날짜 단언 · 격자 일치. 재현 관문은 repro_gate(차이만)."""
    T, log = targets(ctx.Wd)
    ns = [r["n_basket"] for r in log]
    tilt = {}
    for r in log:
        k = min((0.3, 0.5, 0.7), key=lambda x: abs(x - r["w_val"]))
        tilt[k] = tilt.get(k, 0) + 1
    sw = max(abs(sum(x["w"].values()) - 1) for x in T.values())
    # 회계 차이(선언 수치 · 재현 차이만): 거래 장부(흘러감) − 게시 월 수익의 |Δ| 최대
    acc = {}
    for nm, cost in (("drift_gross", 0.0), ("drift_10bp", Q.COST)):
        d, _m, _x = _diff(ctx.Wd, Q.stock_path(_Book(ctx.Wd, _pb(ctx.Wd)["PX"]), T, reb=1, cost=cost)["path"])
        acc[nm] = round(float(max(abs(v) for v in d.values())), 2)
    return {"n_forms": len(T), "n_basket_min": min(ns), "n_basket_med": int(np.median(ns)), "n_basket_max": max(ns),
            "n_scored_min": min(r["n_scored"] for r in log), "tilt_months": {str(k): v for k, v in sorted(tilt.items())},
            "sum_w_err": sw, "max_w": max(r["max_w"] for r in log), "price_map": _pb(ctx.Wd)["rep"], "targets_hash": thash(T),
            "pins": verify_pins(ctx), "accounting_diff_max_bp": acc}


def run(ctx):
    return {}


if __name__ == "__main__":
    import time
    t0 = time.time()
    print(json.dumps(selftest(), ensure_ascii=False))
    ctx = Q.Ctx()
    print(json.dumps(dry(ctx), ensure_ascii=False, default=str))
    print("재현 관문", json.dumps(repro_gate(ctx), ensure_ascii=False, default=str))
    if "--variants" in sys.argv:
        print("회계 차이", json.dumps(gate_variants(ctx), ensure_ascii=False, default=str))
    print("%.0f초" % (time.time() - t0))
