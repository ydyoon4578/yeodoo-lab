#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""페어 트레이딩 백테스트 → data/pairs_strategies.json

사전등록: build/PREREG-2026-08-12-PAIRS.md — **그 문서를 먼저 읽을 것.** 규칙·유니버스·
게시 기준·미리 적은 예측이 전부 거기 있고, 이 파일은 그것을 실행만 한다.

이 랩의 다섯 번째 엔진이다. 종목 전략(횡단면 바스켓)도 자산배분(배분기)도 아니라
**종목쌍 롱숏**이라 채점 축이 다르다 — 대조군이 시장이 아니라 0 이고, 판정에
시장 베타가 들어간다.

── 규칙 둘 ─────────────────────────────────────────────────────────────
A `p-ggr`   GGR(2006) 원문 거리법 — 형성창 SSD 최소 상위 N. 섹터 무제약.
B `p-comb`  동일섹터 ∧ 상관 상위1% ∧ SSD 상위1% ∧ 반감기 5~30일 ∧ 형성창 왕복≥2.
            🚨 B 는 **형성 단계 결과를 보고 만든 규칙**이다(PREREG §0). A 와 나란히
              놓는 이유가 그것이다 — B 가 이겨도 그 차이에 오염이 섞여 있다.

── 유니버스 셋 ─────────────────────────────────────────────────────────
full  오늘의 518종 소급 · 전 구간          sub   같은 518종 · **PIT 과 같은 창**
pit   그때의 SPX∪NDX 멤버 + 편출 가격 캐시
🚨 편향 = sub − pit 이다. full − pit 이 아니다 — 그건 창 차이가 섞인 값이다.

── 채점기를 두 벌 만들지 않는다 ────────────────────────────────────────
형성 통계(SSD·반감기·Corwin-Schultz)는 build/probe_pairs.py 에서 import 한다.
여기서 다시 구현하면 프로브가 고른 페어와 백테스트가 고른 페어가 조용히 갈린다.

  python build/pairs_backtest.py            # 소급 레그(full·sub)
  python build/pairs_backtest.py --pit      # PIT 레그까지(배관이 남아 있을 때만)
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_pairs as PP            # noqa: E402  형성 통계는 여기 하나뿐

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "pairs_strategies.json")

FORM, TRADE = 252, 126          # 형성 12개월 → 거래 6개월 (GGR)
SIZES = (5, 20)                 # 상위 N — 원문의 두 판
ENTRY = 2.0                     # ±2σ
HL_LO, HL_HI = 5, 30
MIN_TRIPS = 2
BORROW_APY = 0.003
PIT_START = "2021-07-30"        # 이미 정해진 값 — 페어를 위해 다시 고르지 않는다
NW_LAGS = 3


# ══ 자료 ═══════════════════════════════════════════════════════════════
def lab_matrices():
    """오늘의 518종 — 종가·고가·저가(T×N) + 섹터·이름."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    n = len(dates)
    ts, px, hi, lo, sec = [], [], [], [], {}
    for s in st["stocks"]:
        p = os.path.join(DATA, "sd", s["t"] + ".json")
        if not os.path.exists(p):
            continue
        j = json.load(io.open(p, encoding="utf-8"))
        a, h, l = j.get("pxd") or [], j.get("hd") or [], j.get("ld") or []
        if not (len(a) == len(h) == len(l) == n):
            continue
        ts.append(s["t"])
        px.append([np.nan if v is None else v for v in a])
        hi.append([np.nan if v is None else v for v in h])
        lo.append([np.nan if v is None else v for v in l])
        sec[s["t"]] = s.get("sector") or "?"
    return dates, ts, (np.array(px, float).T, np.array(hi, float).T,
                       np.array(lo, float).T), sec


def pit_matrices(dates, sec_lab):
    """PIT — 그때의 멤버 + 편출 가격/고저가 캐시. 월별 멤버십도 같이 돌려준다."""
    import pit_backtest as PB
    mem = PB.fetch_members()
    need = set()
    for v in mem.values():
        need |= set(v)
    span = {}
    for ym, lst in mem.items():
        for t in lst:
            a, b = span.get(t, (ym, ym))
            span[t] = (min(a, ym), max(b, ym))
    px_map, _rep = PB.load_prices(need, span)
    ts = sorted(px_map)
    n = len(dates)
    PX = np.full((n, len(ts)), np.nan)
    for k, t in enumerate(ts):
        d = px_map[t]
        for i, dd in enumerate(dates):
            v = d.get(dd)
            if v is not None:
                PX[i, k] = v
    # ⚠ load_hilo 는 (지도, 랩종수, 편출종수) 세 값을 준다 — 커버리지를 부르는 쪽이
    #   보라고 그렇게 돼 있다. 첫 값만 받으면 조용히 튜플이 들어와 뒤에서 터진다.
    HI, nh_lab, nh_gone = PB.load_hilo(set(ts), dates, span, 0)
    LO, _, _ = PB.load_hilo(set(ts), dates, span, 1)
    print("  고저가 %d종 (랩 %d + 편출 %d) — 없는 종목은 비용 추정이 중앙값으로 대체된다"
          % (len(HI), nh_lab, nh_gone))
    H = np.full((n, len(ts)), np.nan)
    L = np.full((n, len(ts)), np.nan)
    for k, t in enumerate(ts):
        for src, dst in ((HI.get(t), H), (LO.get(t), L)):
            if src:
                dst[:, k] = [np.nan if v is None else v for v in src]
    # 섹터 — 랩에 있으면 그것, 편출 종목은 GICS 수동 지도, 없으면 '?'(B 규칙에서 자동 탈락)
    gm = {}
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gics_manual.json")
    if os.path.exists(p):
        raw = json.load(io.open(p, encoding="utf-8"))
        gm = {k: (v.get("sector") if isinstance(v, dict) else v) for k, v in raw.items()}
    sec = {t: (sec_lab.get(t) or gm.get(t) or "?") for t in ts}
    return ts, (PX, H, L), sec, mem


def month_end_idx(dates):
    out = []
    for i in range(len(dates) - 1):
        if dates[i][:7] != dates[i + 1][:7]:
            out.append(i)
    out.append(len(dates) - 1)
    return out


# ══ 형성 ═══════════════════════════════════════════════════════════════
def select(PXf, HIf, LOf, names, sec, dual, rule, size):
    """형성창 행렬(FORM×n)에서 페어 N 쌍 + 페어별 σ·비용을 고른다.

    돌려주는 튜플: (i, j, sigma, cost, meta)
      i,j    형성창 열 인덱스 · sigma  형성창 스프레드 표준편차
      cost   왕복 유효스프레드(다리 둘 합) · meta 진단
    """
    P = PXf / PXf[0]
    D = PP.ssd_matrix(P)
    n = len(names)
    pos = {t: k for k, t in enumerate(names)}
    for a, b in dual:                       # 같은 회사의 두 가격표는 페어가 아니다
        if a in pos and b in pos:
            D[pos[a], pos[b]] = D[pos[b], pos[a]] = np.inf
    S = PP.corwin_schultz(HIf, LOf)
    S = np.where(np.isfinite(S), S, np.nanmedian(S))
    iu = np.triu_indices(n, 1)
    ssd = D[iu]

    if rule == "A":
        order = np.argsort(ssd)[: size * 4]
        cand = [o for o in order if np.isfinite(ssd[o])][:size]
    else:
        R = np.diff(np.log(PXf), axis=0)
        Rc = R - R.mean(0)
        rr = np.sqrt((Rc * Rc).sum(0))
        rr[rr == 0] = 1e-12
        CORR = (Rc.T @ Rc) / np.outer(rr, rr)
        corr = CORR[iu]
        fin = np.isfinite(ssd)
        if fin.sum() < 100:
            return []
        cq = float(np.percentile(corr[fin], 99))
        dq = float(np.percentile(ssd[fin], 1))
        smat = np.array([sec.get(t, "?") for t in names])
        same = (smat[iu[0]] == smat[iu[1]]) & (smat[iu[0]] != "?")
        pre = np.where(fin & same & (corr >= cq) & (ssd <= dq))[0]
        cand = []
        for o in pre:                        # 반감기·왕복은 걸러 남은 것만 — 전 쌍은 낭비다
            a, b = iu[0][o], iu[1][o]
            s = P[:, a] - P[:, b]
            mu, sd = float(s.mean()), float(s.std(ddof=1))
            hl = PP.half_life(s)
            if not np.isfinite(hl) or not (HL_LO <= hl <= HL_HI):
                continue
            if trips_count(s, mu, sd) < MIN_TRIPS:
                continue
            cand.append(o)
        cand.sort(key=lambda o: ssd[o])
        cand = cand[:size]

    out = []
    for o in cand:
        a, b = int(iu[0][o]), int(iu[1][o])
        s = P[:, a] - P[:, b]
        sd = float(s.std(ddof=1))
        if not (sd > 0):
            continue
        out.append((a, b, sd, float(S[a] + S[b]),
                    {"a": names[a], "b": names[b], "ssd": float(ssd[o]),
                     "sec_a": sec.get(names[a], "?"), "sec_b": sec.get(names[b], "?")}))
    return out


def trips_count(s, mu, sd):
    """형성창에서 ±2σ 진입 → 0 수렴 횟수(표본 안 서술)."""
    z = (s - mu) / (sd if sd > 0 else 1e-12)
    side = done = 0
    for v in z:
        if side == 0:
            if abs(v) >= ENTRY:
                side = 1 if v > 0 else -1
        elif (side > 0 and v <= 0) or (side < 0 and v >= 0):
            done += 1
            side = 0
    return done


# ══ 거래 ═══════════════════════════════════════════════════════════════
def trade_cohort(PXw, pairs, base, wait=1):
    """한 코호트의 거래창 일간 손익.

    PXw   거래창 가격(TRADE×n) — 형성창 **다음** 거래일부터
    base  형성창 첫날 가격(n,) — 정규화 기준. GGR 원문대로 거래창에서 다시 잡지 않는다.
    wait  신호 다음 거래일 종가 체결(GGR one-day-waiting). 0 이면 당일 체결.

    돌려주는 것: (일간손익 배열(TRADE,), 진단)
    ⚠ 손익은 **페어당 다리 $1** 기준이다. 포트폴리오 수익으로 바꾸는 나눗셈(투입자본 N)은
      부르는 쪽에서 한다 — 여기서 나누면 코호트마다 다른 N 이 섞인다.
    """
    T = PXw.shape[0]
    # 🚨 총수익·거래비용·대차를 **따로** 쌓는다. 합쳐 놓으면 "규칙이 안 먹는 것"과 "비용이
    #   먹는 것"을 구별할 수 없고, 이 전략에서 그 구별이 곧 결론이다(Do·Faff 2010 의 요지).
    #   비용이 비례항이라 나중에 배수만 곱해 민감도를 낼 수 있다 — 다시 돌릴 필요가 없다.
    pnl = np.zeros(T)
    cst = np.zeros(T)
    bor = np.zeros(T)
    n_open = n_conv = n_forced = n_dead = n_day0 = 0
    worst = 0.0
    # 거래당 총손익을 청산 사유별로 나눠 담는다. 🚨 이게 이 전략의 작동 여부를 직접 말한다 —
    #   수렴한 거래가 벌고 강제청산이 잃는 것은 설계상 당연하고, **둘의 크기 비교**가 곧
    #   '평균회귀가 실재하는가'다. 합계만 보면 그 둘이 상쇄된 결과만 남는다.
    by_exit = {"conv": [], "forced": [], "dead": []}
    for a, b, sd, cost, meta in pairs:
        pa, pb = PXw[:, a] / base[a], PXw[:, b] / base[b]
        s = pa - pb
        side = 0            # +1: a 고평가 → a 숏 b 롱 / −1: 반대
        ei = -1
        eal = eas = 0.0
        acc = 0.0
        for t in range(T):
            if not (np.isfinite(pa[t]) and np.isfinite(pb[t])):
                if side != 0:            # 다리가 끊겼다 — 마지막 유효값으로 청산
                    n_dead += 1
                    cst[t] += cost / 2
                    by_exit["dead"].append(acc)
                    side, acc = 0, 0.0
                continue
            if side != 0:
                # 보유 중 일간 손익 — 재조정 없는 GGR 규약(진입가 대비 비율)
                lp = pa if side < 0 else pb
                sp = pb if side < 0 else pa
                if t > ei:
                    d = (lp[t] - lp[t - 1]) / eal - (sp[t] - sp[t - 1]) / eas
                    pnl[t] += d
                    acc += d
                bor[t] += BORROW_APY / 252.0
                if (side > 0 and s[t] <= 0) or (side < 0 and s[t] >= 0):
                    ex = min(t + wait, T - 1)
                    if ex > t:
                        lp2, sp2 = (pa, pb) if side < 0 else (pb, pa)
                        for u in range(t + 1, ex + 1):
                            if np.isfinite(lp2[u]) and np.isfinite(sp2[u]):
                                d = (lp2[u] - lp2[u - 1]) / eal - (sp2[u] - sp2[u - 1]) / eas
                                pnl[u] += d
                                acc += d
                                bor[u] += BORROW_APY / 252.0
                    cst[ex] += cost / 2
                    n_conv += 1
                    worst = min(worst, acc)
                    by_exit["conv"].append(acc)
                    side, acc = 0, 0.0
            elif abs(s[t]) >= ENTRY * sd:
                ex = t + wait
                if ex >= T - 1:
                    continue                        # 체결일이 창 밖 — 진입하지 않는다
                if not (np.isfinite(pa[ex]) and np.isfinite(pb[ex])):
                    continue
                side = 1 if s[t] > 0 else -1
                ei = ex
                eal = (pb[ex] if side > 0 else pa[ex])
                eas = (pa[ex] if side > 0 else pb[ex])
                cst[ex] += cost / 2
                n_open += 1
                if t <= 1:
                    # 🚨 거래창 **첫 이틀**에 열린 것. GGR 은 형성창 첫날을 기준으로
                    #   정규화를 이어 쓰므로, 형성 끝에 이미 벌어져 있던 페어는 거래창이
                    #   열리자마자 진입한다. 그러면 이 규칙은 '거래창 안의 발산에 베팅'이
                    #   아니라 '지난 12개월 발산의 되돌림에 베팅'이 된다 — 다른 내기다.
                    n_day0 += 1
        if side != 0:                                # 거래창 종료 강제 청산
            cst[T - 1] += cost / 2
            n_forced += 1
            worst = min(worst, acc)
            by_exit["forced"].append(acc)
    return (pnl, cst, bor), {"open": n_open, "conv": n_conv, "forced": n_forced,
                             "dead": n_dead, "worst": worst, "day0": n_day0,
                             "by_exit": by_exit}


# ══ 통계 ═══════════════════════════════════════════════════════════════
def nw_t(x, lags=NW_LAGS):
    """Newey-West t. 겹치는 코호트라 단순 t 는 과대다 — 판정은 이쪽으로 한다."""
    x = np.asarray(x, float)
    T = len(x)
    if T < 12:
        return None
    m = x.mean()
    e = x - m
    s = float(e @ e) / T
    for l in range(1, min(lags, T - 1) + 1):
        g = float(e[l:] @ e[:-l]) / T
        s += 2 * (1 - l / (lags + 1)) * g
    if s <= 0:
        return None
    return float(m / np.sqrt(s / T))


def stats(daily, dates_sub, mkt_m=None):
    nav = np.cumprod(1.0 + daily)
    mo = {}
    for r, d in zip(daily, dates_sub):
        mo[d[:7]] = mo.get(d[:7], 1.0) * (1.0 + r)
    keys = sorted(mo)
    mr = np.array([mo[k] - 1.0 for k in keys])
    yrs = len(daily) / 252.0
    dd = nav / np.maximum.accumulate(nav) - 1.0
    out = {
        "n_days": int(len(daily)), "n_months": int(len(mr)),
        "from": dates_sub[0], "to": dates_sub[-1],
        "mo_mean": float(mr.mean() * 100),
        "cagr": float((nav[-1] ** (1 / yrs) - 1) * 100) if yrs > 0 and nav[-1] > 0 else None,
        "vol": float(daily.std(ddof=1) * np.sqrt(252) * 100),
        "mdd": float(dd.min() * 100),
        "t_simple": float(mr.mean() / (mr.std(ddof=1) / np.sqrt(len(mr)))) if mr.std() > 0 else None,
        "t_nw": nw_t(mr),
        "hit": float((mr > 0).mean() * 100),
    }
    out["sharpe"] = (out["cagr"] / out["vol"]) if out["vol"] else None
    if mkt_m is not None and len(mkt_m) == len(mr):
        v = float(((mkt_m - mkt_m.mean()) ** 2).sum())
        out["beta"] = float(((mkt_m - mkt_m.mean()) @ (mr - mr.mean())) / v) if v > 0 else None
        out["corr_mkt"] = float(np.corrcoef(mr, mkt_m)[0, 1])
    return out, keys, mr


# ══ 한 레그 돌리기 ═════════════════════════════════════════════════════
def run_leg(tag, dates, ts, MATS, sec, dual, i_from, i_to, mem=None):
    PX, HI, LO = MATS
    me = [i for i in month_end_idx(dates) if i >= max(FORM, i_from) and i < i_to]
    T = len(dates)
    res = {}
    for rule in ("A", "B"):
        for size in SIZES:
            acc = np.zeros(T)
            acc_g = np.zeros(T)
            acc_c = np.zeros(T)
            cnt = np.zeros(T)
            dg = {"open": 0, "conv": 0, "forced": 0, "dead": 0, "day0": 0, "worst": 0.0}
            bx = {"conv": [], "forced": [], "dead": []}
            npair, nshort, secct = [], 0, {}
            for e in me:
                f0, f1 = e - FORM + 1, e + 1
                W = PX[f0:f1]
                ok = np.isfinite(W).all(0) & (W > 0).all(0)
                if mem is not None:              # PIT — 그달 실제 멤버만
                    mm = set(mem.get(dates[e][:7]) or [])
                    ok &= np.array([t in mm for t in ts])
                idx = np.where(ok)[0]
                if len(idx) < 50:
                    continue
                names = [ts[k] for k in idx]
                pairs = select(W[:, idx], HI[f0:f1][:, idx], LO[f0:f1][:, idx],
                               names, sec, dual, rule, size)
                npair.append(len(pairs))
                if len(pairs) < size:
                    nshort += 1
                if not pairs:
                    continue
                for _, _, _, _, m_ in pairs:
                    secct[m_["sec_a"]] = secct.get(m_["sec_a"], 0) + 1
                    secct[m_["sec_b"]] = secct.get(m_["sec_b"], 0) + 1
                t0, t1 = e + 1, min(e + 1 + TRADE, T)
                if t1 - t0 < 20:
                    continue
                (g, c, bw), d = trade_cohort(PX[t0:t1][:, idx], pairs, W[0][idx])
                acc[t0:t1] += (g - c - bw) / size  # 투입자본 규약 — 안 열린 페어도 분모
                acc_g[t0:t1] += (g - bw) / size    # 거래비용만 뺀 총수익(대차는 실비다)
                acc_c[t0:t1] += c / size
                cnt[t0:t1] += 1
                for k in ("open", "conv", "forced", "dead", "day0"):
                    dg[k] += d[k]
                dg["worst"] = min(dg["worst"], d["worst"])
                for k in bx:
                    bx[k].extend(d["by_exit"][k])
            live = cnt > 0
            if live.sum() < 252:
                continue
            i0, i1 = int(np.argmax(live)), int(T - np.argmax(live[::-1]))
            cc = np.maximum(cnt[i0:i1], 1)
            daily = np.where(cnt[i0:i1] > 0, acc[i0:i1] / cc, 0.0)
            gross = np.where(cnt[i0:i1] > 0, acc_g[i0:i1] / cc, 0.0)
            costs = np.where(cnt[i0:i1] > 0, acc_c[i0:i1] / cc, 0.0)
            dsub = dates[i0:i1]
            eqr = universe_daily(PX, ts, mem, dates, i0, i1)
            mm_ = {}
            for r, d_ in zip(eqr, dsub):
                mm_[d_[:7]] = mm_.get(d_[:7], 1.0) * (1.0 + r)
            mkt_m = np.array([mm_[k] - 1.0 for k in sorted(mm_)])
            st_, mk, mr = stats(daily, dsub, mkt_m)
            gs, _, gr = stats(gross, dsub)
            # 비용 민감도 — CS 는 대형주 실제 스프레드보다 한 자릿수 크다(PREREG 에 그렇게 적었다).
            # 비용이 비례항이라 배수만 곱하면 되고, 다시 돌릴 필요가 없다.
            sens = {}
            for lam, lbl in ((0.5, "x0.5"), (0.1, "x0.1")):
                s2, _, _ = stats(gross - lam * costs, dsub)
                sens[lbl] = {"mo_mean": s2["mo_mean"], "t_nw": s2["t_nw"], "cagr": s2["cagr"]}
            tot = sum(secct.values()) or 1
            ex_ = {}
            for k, v in bx.items():
                ex_[k] = {"n": len(v), "mean": 100.0 * float(np.mean(v)) if v else None,
                          "sum": 100.0 * float(np.sum(v)) if v else 0.0}
            st_.update({"by_exit": ex_,
                        "rule": rule, "size": size, "leg": tag,
                        "n_cohort": len(npair), "pairs_med": float(np.median(npair or [0])),
                        "short_months": nshort, "trades": dg["open"],
                        "conv": dg["conv"], "forced": dg["forced"], "dead": dg["dead"],
                        "day0": dg["day0"],
                        "day0_pct": 100.0 * dg["day0"] / max(1, dg["open"]),
                        "conv_pct": 100.0 * dg["conv"] / max(1, dg["open"]),
                        "worst_pair": 100.0 * dg["worst"],
                        "gross_mo": gs["mo_mean"], "gross_t_nw": gs["t_nw"],
                        "cost_mo": gs["mo_mean"] - st_["mo_mean"], "cost_sens": sens,
                        "util_pct": 100.0 * secct.get("Utilities", 0) / tot,
                        "sectors": dict(sorted(secct.items(), key=lambda x: -x[1])[:6])})
            nav = list(np.cumprod(1.0 + daily) * 100.0)
            res["%s%d" % (rule, size)] = {"stats": st_, "months": mk,
                                          "rets": [round(float(x), 6) for x in mr],
                                          "gross": [round(float(x), 6) for x in gr],
                                          "nav": [round(float(x), 2) for x in nav],
                                          "dates": dsub}
    return res


def universe_daily(PX, ts, mem, dates, i0, i1):
    """대조군 — 그 레그 유니버스의 동일가중 일간수익. 시장 베타를 재는 데만 쓴다."""
    out = np.zeros(i1 - i0)
    for k, i in enumerate(range(i0, i1)):
        if i == 0:
            continue
        if mem is not None:
            mm = set(mem.get(dates[i - 1][:7]) or [])
            sel = np.array([t in mm for t in ts])
        else:
            sel = np.ones(len(ts), bool)
        a, b = PX[i - 1], PX[i]
        m = sel & np.isfinite(a) & np.isfinite(b) & (a > 0)
        if m.sum():
            out[k] = float(np.mean(b[m] / a[m] - 1.0))
    return out


# ══ 랩 통합 목록용 레코드 ══════════════════════════════════════════════
# 🚨 이 랩의 다른 네 소스는 전부 **시장**(또는 동일가중 유니버스)과 겨룬다. 페어는 달러중립
#   롱숏이라 대조군이 **현금**이고, 그래서 Δ샤프의 분모가 0 이다 — 우열을 나란히 못 놓는다.
#   `strategy_index.comparability()` 에 이미 그 갈래가 있다(bench_unstable). 새 성격 어휘를
#   만들지 않고 그 갈래를 탄다: 성격은 초과수익이 목적이므로 **수익엔진**이 맞고,
#   비교 가능성만 끈다. 화면이 "같은 눈금이 아니다"를 말할 수 있으면 그것으로 충분하다.
BENCH_LABEL = "현금(무위험) — 달러중립 롱숏이라 대조군이 0이다"

NAMES = {
    "A": ("p-ggr", "페어 트레이딩 — GGR 거리법",
          "형성 252일 정규화 경로의 SSD 최소 상위 N페어 · 거래 126일 · ±2σ 진입 → 0교차 청산 "
          "· 달러중립 · 매월 코호트 시작(6개 중첩)",
          "Gatev·Goetzmann·Rouwenhorst(2006, RFS 19:797) 의 거리법을 그대로 옮긴 것. "
          "이중클래스(CIK 동일)만 자료 위생으로 제외했다."),
    "B": ("p-comb", "페어 트레이딩 — 조합 스크리너",
          "동일섹터 ∧ 수익률상관 상위1% ∧ SSD 상위1% ∧ 반감기 5~30일 ∧ 형성창 ±2σ 왕복≥2 "
          "· 나머지 프로토콜은 GGR 과 같다",
          "🚨 형성 단계 진단을 보고 만든 규칙이다(PREREG §0). 거리 하나로 고르면 유틸리티에 "
          "쏠리고(26개 창 누적 62%), 거리·공적분·상관 상위20의 교집합이 0/20 이라 기준 하나로는 "
          "무엇을 고르는지가 정해지지 않는다는 관찰에서 나왔다."),
}


def index_records(legs):
    """`full` 레그 4종 → data/strategy_index.py 가 읽는 모양.

    ⚠ 등록한 가설은 넷(규칙 2 × 크기 2)이고 목록에도 넷을 싣는다. 기각됐다고 빼지 않는다 —
      PREREG §4 가 그렇게 적었고, 빼면 다음 배치의 족 임계가 거짓말이 된다.
    ⚠ PIT 레그는 싣지 않는다. 이 랩이 PIT 배관을 걷어내는 중이라 값이 있다 없다 하면
      목록이 실행마다 달라진다 — 판정은 ⓐⓑ 에서 이미 갈렸으므로 결론이 바뀌지 않는다.
    """
    out = []
    for rule in ("A", "B"):
        sid0, nm0, rule_txt, why0 = NAMES[rule]
        for size in SIZES:
            r = (legs.get("full") or {}).get("%s%d" % (rule, size))
            if not r:
                continue
            s = r["stats"]
            sh = s.get("sharpe")
            n = len(r["nav"])
            out.append({
                "sid": "%s-top%d" % (sid0, size),
                "name": "%s (상위 %d페어)" % (nm0, size),
                "role": "수익엔진",
                # 대조군이 현금이라 d_sharpe = 샤프 그대로다. tech_backtest 의 판정 규칙
                # (d_sharpe ≤ 0 → 열위)을 같은 글자로 적용한다 — 채점 규칙을 새로 만들지 않는다.
                "verdict": "열위" if (sh is None or sh <= 0) else
                           ("통과 후보" if abs(s["t_nw"] or 0) >= 3.45 else "구별 불가"),
                "rule": rule_txt, "why": why0,
                "bench_label": BENCH_LABEL, "bench_unstable": True,
                "start": s["from"], "end": s["to"],
                "metrics": {"cagr": round(s["cagr"] or 0, 2), "vol": round(s["vol"], 2),
                            "sharpe": round(sh, 3) if sh is not None else None,
                            "mdd": round(s["mdd"], 2)},
                "bench": {"cagr": 0.0, "vol": 0.0, "sharpe": 0.0, "mdd": 0.0},
                "d_sharpe": round(sh, 3) if sh is not None else None,
                "t": round(s["t_nw"], 2) if s["t_nw"] is not None else None,
                "beta": round(s["beta"], 3) if s.get("beta") is not None else None,
                "nav": r["nav"], "bnav": [100.0] * n, "dates": r["dates"],
                "note": ("총수익(거래비용 전) 월 %+.3f%% · t_NW %.2f — **비용을 넣기 전에 이미 0이다.** "
                         "수렴 청산 %d건 평균 %+.2f%% 대 기간종료 강제청산 %d건 평균 %+.2f%% 로 "
                         "둘이 상쇄된다(수렴률 %.0f%%). Corwin-Schultz 유효스프레드를 1/10 로 "
                         "줄여도 |t| < 0.5 라 비용 가정이 판정을 바꾸지 않는다."
                         % (s["gross_mo"], s["gross_t_nw"] or 0,
                            s["by_exit"]["conv"]["n"], s["by_exit"]["conv"]["mean"] or 0,
                            s["by_exit"]["forced"]["n"], s["by_exit"]["forced"]["mean"] or 0,
                            s["conv_pct"])),
            })
    return out


# ══ 본체 ═══════════════════════════════════════════════════════════════
def main() -> int:
    dates, ts, MATS, sec = lab_matrices()
    dual, dgroups = PP.load_same_company(ts)
    T = len(dates)
    print("페어 백테스트 — 형성 %d일 → 거래 %d일 · 상위 %s · 진입 ±%.0fσ"
          % (FORM, TRADE, "·".join(map(str, SIZES)), ENTRY))
    print("사전등록: build/PREREG-2026-08-12-PAIRS.md")
    print("이중클래스 제외 %d쌍: %s"
          % (len(dual), " · ".join("/".join(g) for g in dgroups.values())))

    i_pit = next(i for i, d in enumerate(dates) if d >= PIT_START)
    legs = {}
    print("\n[full] 오늘의 518종 소급 · 전 구간")
    legs["full"] = run_leg("full", dates, ts, MATS, sec, dual, FORM, T)
    print("[sub ] 같은 518종 · PIT 과 같은 창(%s~)" % PIT_START)
    legs["sub"] = run_leg("sub", dates, ts, MATS, sec, dual, i_pit, T)

    # 🚨 PIT 레그는 **기본에서 뺐다**(2026-08-12). 이 랩이 PIT 배관을 걷어내는 중이라
    #   있다 없다 하면 통합 목록이 실행마다 달라진다. 판정은 ⓐ(t_NW)·ⓑ(순수익)에서 이미
    #   갈렸으므로 ⓒ 가 없어도 결론이 안 바뀐다 — 넷 다 기각이고, 근거는 PIT 이 아니었다.
    #   ⚠ 한 번 잰 값은 PREREG-...-PAIRS-RESULT.md §3 에 남겨 뒀다(편향 ≈ 0.03%p).
    if "--pit" in sys.argv:
        print("[pit ] 그때의 SPX∪NDX 멤버 + 편출 캐시")
        try:
            pts, pmats, psec, mem = pit_matrices(dates, sec)
            pdual, _ = PP.load_same_company(pts)
            legs["pit"] = run_leg("pit", dates, pts, pmats, psec, pdual, i_pit, T, mem)
        except SystemExit as ex:
            print("  ❌ PIT 레그를 못 돌린다 — %s" % ex)
            legs["pit"] = {}
        except Exception as ex:
            print("  ❌ PIT 레그 실패 — %s: %s" % (type(ex).__name__, ex))
            legs["pit"] = {}

    # ── 표 ────────────────────────────────────────────────────────────
    hdr = ("%-6s %-5s %5s %8s %7s %7s %7s %7s %7s %6s %6s"
           % ("레그", "규칙", "N", "월평균%", "연CAGR", "변동성", "t단순", "t_NW", "MDD%", "β", "유틸%"))
    print("\n" + "=" * len(hdr))
    print(hdr)
    print("=" * len(hdr))
    for lg in ("full", "sub", "pit"):
        for key in ("A5", "A20", "B5", "B20"):
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            print("%-6s %-5s %5d %8.3f %7.2f %7.2f %7.2f %7s %7.1f %6s %6.0f"
                  % (lg, "GGR" if s["rule"] == "A" else "조합", s["size"], s["mo_mean"],
                     s["cagr"] or 0, s["vol"], s["t_simple"] or 0,
                     "%.2f" % s["t_nw"] if s["t_nw"] is not None else "—",
                     s["mdd"], "%.2f" % s.get("beta", 0) if s.get("beta") is not None else "—",
                     s["util_pct"]))
    print("=" * len(hdr))

    print("\n총수익 vs 비용 — 🚨 이 분해가 결론을 정한다(규칙이 죽었나, 비용이 먹었나)")
    print("%-6s %-5s %4s %9s %9s %9s %9s %9s"
          % ("레그", "규칙", "N", "총 월%", "총 t_NW", "비용 월%", "순 월%", "순 t_NW"))
    for lg in ("full", "sub", "pit"):
        for key in ("A5", "A20", "B5", "B20"):
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            print("%-6s %-5s %4d %9.3f %9s %9.3f %9.3f %9s"
                  % (lg, "GGR" if s["rule"] == "A" else "조합", s["size"], s["gross_mo"],
                     "%.2f" % s["gross_t_nw"] if s["gross_t_nw"] is not None else "—",
                     -s["cost_mo"], s["mo_mean"],
                     "%.2f" % s["t_nw"] if s["t_nw"] is not None else "—"))
    print("비용 민감도(CS 를 배수로 줄였을 때 순 월수익%) — CS 는 대형주 실제보다 한 자릿수 크다")
    print("%-6s %-5s %4s %11s %11s %11s"
          % ("레그", "규칙", "N", "CS 그대로", "CS×0.5", "CS×0.1"))
    for lg in ("full", "sub", "pit"):
        for key in ("A5", "A20", "B5", "B20"):
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            c = s["cost_sens"]
            print("%-6s %-5s %4d %11.3f %11s %11s"
                  % (lg, "GGR" if s["rule"] == "A" else "조합", s["size"], s["mo_mean"],
                     "%.3f(%.2f)" % (c["x0.5"]["mo_mean"], c["x0.5"]["t_nw"] or 0),
                     "%.3f(%.2f)" % (c["x0.1"]["mo_mean"], c["x0.1"]["t_nw"] or 0)))

    print("\n청산 사유별 거래당 총손익(비용 전 · 다리 $1 기준 %) — 평균회귀가 실재하는가")
    print("%-6s %-5s %4s %18s %18s %13s"
          % ("레그", "규칙", "N", "수렴 청산", "기간종료 강제", "총기여%"))
    for lg in ("full", "sub", "pit"):
        for key in ("A5", "A20", "B5", "B20"):
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            e = r["stats"]["by_exit"]

            def f_(k, e=e):
                return ("%d건 %+.2f" % (e[k]["n"], e[k]["mean"])) if e[k]["n"] else "—"
            print("%-6s %-5s %4d %18s %18s %13.1f"
                  % (lg, "GGR" if r["stats"]["rule"] == "A" else "조합", r["stats"]["size"],
                     f_("conv"), f_("forced"),
                     e["conv"]["sum"] + e["forced"]["sum"] + e["dead"]["sum"]))

    print("\n거래 진단")
    print("%-6s %-5s %4s %7s %7s %7s %7s %8s %8s %8s"
          % ("레그", "규칙", "N", "코호트", "진입", "수렴%", "강제", "첫이틀%", "최악페어%", "후보부족"))
    for lg in ("full", "sub", "pit"):
        for key in ("A5", "A20", "B5", "B20"):
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            print("%-6s %-5s %4d %7d %7d %6.1f%% %7d %7.1f%% %8.1f %8d"
                  % (lg, "GGR" if s["rule"] == "A" else "조합", s["size"], s["n_cohort"],
                     s["trades"], s["conv_pct"], s["forced"], s["day0_pct"],
                     s["worst_pair"], s["short_months"]))

    # ── 생존편향 = sub − pit ──────────────────────────────────────────
    print("\n생존편향(sub − pit) — 🚨 full−pit 이 아니다. 창을 맞춘 두 계열의 차이만이 편향이다.")
    for key in ("A5", "A20", "B5", "B20"):
        a = (legs.get("sub") or {}).get(key)
        b = (legs.get("pit") or {}).get(key)
        if not (a and b):
            continue
        print("  %-4s 월평균 %+.3f%%p · CAGR %+.2f%%p · t_NW %s → %s"
              % (key, a["stats"]["mo_mean"] - b["stats"]["mo_mean"],
                 (a["stats"]["cagr"] or 0) - (b["stats"]["cagr"] or 0),
                 "%.2f" % (a["stats"]["t_nw"] or 0), "%.2f" % (b["stats"]["t_nw"] or 0)))

    # ── 게시 판정 (PREREG §3) ─────────────────────────────────────────
    print("\n게시 판정 — ⓐ t_NW>3.45 · ⓑ 순수익>0 · ⓒ pit 부호 유지 · ⓓ |β|<0.2")
    verdicts = {}
    for key in ("A5", "A20", "B5", "B20"):
        f = (legs.get("full") or {}).get(key)
        p = (legs.get("pit") or {}).get(key)
        if not f:
            continue
        s = f["stats"]
        ga = (s["t_nw"] or 0) > 3.45
        gb = s["mo_mean"] > 0
        # ⚠ PIT 을 안 돌렸으면 ⓒ 는 **미측정**이지 실패가 아니다. ❌ 로 찍으면 "재 봤더니
        #   틀렸다"로 읽힌다. 게시는 ⓐ~ⓓ 전부를 요구하므로 미측정도 게시는 못 하지만,
        #   기각 사유에 없는 것을 사유로 적지 않는다.
        gc = None if not p else ((p["stats"]["mo_mean"] > 0) == gb)
        gd = s.get("beta") is not None and abs(s["beta"]) < 0.2
        ok = bool(ga and gb and gc and gd)
        verdicts[key] = {"a": ga, "b": gb, "c": gc, "d": gd, "pass": ok}
        mk_ = lambda v: "—" if v is None else ("✅" if v else "❌")
        print("  %-4s ⓐ%s ⓑ%s ⓒ%s ⓓ%s → **%s**%s"
              % (key, mk_(ga), mk_(gb), mk_(gc), mk_(gd),
                 "게시" if ok else "기각",
                 "" if gc is not None else "  (ⓒ 미측정 — PIT 미실행. ⓐⓑ 에서 이미 갈렸다)"))

    doc = {
        "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "prereg": "build/PREREG-2026-08-12-PAIRS.md",
        "params": {"form": FORM, "trade": TRADE, "sizes": list(SIZES), "entry_sigma": ENTRY,
                   "hl": [HL_LO, HL_HI], "min_trips": MIN_TRIPS, "borrow_apy": BORROW_APY,
                   "pit_start": PIT_START, "nw_lags": NW_LAGS},
        "bench_label": BENCH_LABEL,
        "strategies": index_records(legs),
        "legs": legs, "verdicts": verdicts,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
