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
import tech_backtest as TB          # noqa: E402  성과 기준일(asof_cut)을 공유한다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "pairs_strategies.json")
OUTBOOK = os.path.join(DATA, "pairs_book.json")   # co.html 페어 탭이 지연 로드한다

FORM, TRADE = 252, 126          # 형성 12개월 → 거래 6개월 (GGR)
SIZES = (5, 20)                 # 상위 N — 원문의 두 판
# ── 규칙 C(횡단면 최대괴리) — PREREG-2026-09-03-PAIRS-XS. 값 셋 다 고정이다.
XS_POOL = 100                   # 근접 후보 풀(SSD 최소 상위 N쌍)
XS_SIZE = 10                    # 그중 |z| 최대 상위 N쌍을 보유
XS_HOLD = 21                    # 보유 21거래일(다음 월말까지) — 트리거 없음
ENTRY = 2.0                     # ±2σ
HL_LO, HL_HI = 5, 30
MIN_TRIPS = 2
BORROW_APY = 0.003
PIT_START = "2021-07-30"        # 이미 정해진 값 — 페어를 위해 다시 고르지 않는다
NW_LAGS = 3

# 규칙×크기 조합 — 표·판정·페어북이 전부 이 목록 하나를 순회한다.
# 🚨 종전에는 ("A5","A20","B5","B20") 이 여섯 군데에 하드코딩돼 있었다. 규칙 C 를 더하며
#   그중 하나만 빠뜨려도 «계산은 했는데 표에 없는» 상태가 된다 — 이 랩이 반복해 온 실패다.
COMBOS = [(r, sz) for r in ("A", "B") for sz in SIZES] + [("C", XS_SIZE)]
KEYS = tuple("%s%d" % (r, sz) for r, sz in COMBOS)
RLBL = {"A": "GGR", "B": "조합", "C": "최대괴리"}


# ══ 자료 ═══════════════════════════════════════════════════════════════
def lab_matrices():
    """오늘의 518종 — 종가·고가·저가(T×N) + 섹터·이름."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    # 🚨 성과 기준일 = 전월말(2026-08-14 사용자 지시). 랩 본편과 **같은 함수**로 자른다.
    #   ⚠ 계열 길이 검사는 자르기 전 길이(n_raw)로 해야 한다 — 자른 길이로 재면 전 종목이
    #     '길이 안 맞음' 으로 탈락해 페어 유니버스가 통째로 빈다.
    _raw = st["pxd_dates"]
    n_raw = len(_raw)
    dates = _raw[:TB.asof_cut(_raw)]
    n = len(dates)
    ts, px, hi, lo, sec = [], [], [], [], {}
    for s in st["stocks"]:
        p = os.path.join(DATA, "sd", s["t"] + ".json")
        if not os.path.exists(p):
            continue
        j = json.load(io.open(p, encoding="utf-8"))
        a, h, l = j.get("pxd") or [], j.get("hd") or [], j.get("ld") or []
        if not (len(a) == len(h) == len(l) == n_raw):
            continue
        a, h, l = a[:n], h[:n], l[:n]
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
    zmap = {}

    if rule == "A":
        order = np.argsort(ssd)[: size * 4]
        cand = [o for o in order if np.isfinite(ssd[o])][:size]
    elif rule == "C":
        # 횡단면 최대괴리 — PREREG-2026-09-03-PAIRS-XS §1.
        #   ① SSD 최소 상위 XS_POOL 쌍을 후보 풀로 두고
        #   ② 그 안에서 형성 마지막 날 |z| 가 큰 순으로 size 쌍.
        # 🚨 A 와 달리 «가장 가까운» 이 최종 선택 기준이 아니다 — 근접은 자격,
        #   선택은 괴리다. 그래서 풀 크기가 이 규칙의 성격을 정한다(풀을 넓힐수록
        #   «가장 변동성 큰 스프레드 고르기» 로 변질된다). 풀은 100 고정.
        order = [o for o in np.argsort(ssd)[: XS_POOL * 4] if np.isfinite(ssd[o])][:XS_POOL]
        scored = []
        for o in order:
            a, b = iu[0][o], iu[1][o]
            s = P[:, a] - P[:, b]
            sd = float(s.std(ddof=1))
            if not (sd > 0):
                continue
            z = (float(s[-1]) - float(s.mean())) / sd
            if np.isfinite(z):
                scored.append((abs(z), o, z))
        scored.sort(key=lambda x: -x[0])
        # 🚨 다리를 겹치지 않게 고른다(2026-09-03 사용자 지시 · 원 요청의 «10쌍 = 20종목»).
        #   |z| 큰 순으로 훑되 두 다리 모두 처음 쓰는 페어만 담는다. 안 그러면 한 종목이
        #   여러 페어의 같은 쪽 다리로 반복해 잡혀(실측: AON 롱 4회 = 순노출 +40%)
        #   «페어 10개» 가 사실상 «한 종목 대 그 이웃들» 베팅이 된다 — 분산된 스탯아빗
        #   북이 아니다. 겹침을 막으면 서로 다른 종목이 정확히 2×size 개가 된다.
        used, cand = set(), []
        for _az, o, _z in scored:
            a, b = int(iu[0][o]), int(iu[1][o])
            if a in used or b in used:
                continue
            used.add(a); used.add(b)
            cand.append(o)
            if len(cand) >= size:
                break
        zmap = {o: z for _az, o, z in scored}
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
        _z = zmap.get(o) if rule == "C" else None
        out.append((a, b, sd, float(S[a] + S[b]),
                    {"a": names[a], "b": names[b], "ssd": float(ssd[o]),
                     "sec_a": sec.get(names[a], "?"), "sec_b": sec.get(names[b], "?"),
                     # z>0 이면 a 가 비싸다 → a 숏 · b 롱. 규칙 C 는 여기서 방향이 정해진다.
                     "z": (round(_z, 3) if _z is not None else None),
                     "long": (names[b] if (_z or 0) > 0 else names[a]) if _z is not None else None,
                     "short": (names[a] if (_z or 0) > 0 else names[b]) if _z is not None else None}))
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


def trade_xs(PXw, pairs, base, held_prev, wait=1):
    """규칙 C — 고른 10쌍을 보유기간 내내 들고 간다. 트리거도 손절도 없다.

    GGR 판(trade_cohort)과 구조가 다르다:
      · 진입 조건이 없다 — 선택된 순간이 진입이다(체결은 다음 거래일 종가).
      · 청산 조건이 없다 — 보유기간 끝까지 간다. 수렴해도 안 닫고, 더 벌어져도 안 닫는다.
      · 그래서 «안 열린 페어» 가 없다 — 자본이 늘 100% 투입된다.
    방향은 선택 시점 스프레드 부호로 정한다: s>0 이면 a 가 비싸다 → a 숏 · b 롱.

    held_prev  직전 달 보유 집합 {(a이름, b이름, side)} — 여기 있으면 **비용을 안 문다**
               (실제로 갈아타지 않으므로). 이 규칙은 월마다 다시 고르는데, 전량 왕복으로
               물리면 회전율이 실제보다 부풀어 비용 과대가 아니라 모형 오류가 된다.
    돌려주는 것: (일간손익, 비용, 대차), 진단, 이번 달 보유 집합
    """
    T = PXw.shape[0]
    pnl = np.zeros(T)
    cst = np.zeros(T)
    bor = np.zeros(T)
    held_now = set()
    n_new = n_keep = n_dead = 0
    accs = []
    for a, b, sd, cost, meta in pairs:
        pa, pb = PXw[:, a] / base[a], PXw[:, b] / base[b]
        ex = min(wait, T - 1)                      # 체결일
        if not (np.isfinite(pa[ex]) and np.isfinite(pb[ex])):
            continue
        side = 1 if (pa[ex] - pb[ex]) > 0 else -1  # +1: a 고평가 → a 숏 · b 롱
        key = (meta["a"], meta["b"], side)
        held_now.add(key)
        if key in held_prev:
            n_keep += 1
        else:
            n_new += 1
            cst[ex] += cost / 2                    # 진입 반스프레드
        lp = pb if side > 0 else pa                # 롱 다리
        sp = pa if side > 0 else pb                # 숏 다리
        eal, eas = lp[ex], sp[ex]
        acc = 0.0
        last = ex
        for t in range(ex + 1, T):
            if not (np.isfinite(lp[t]) and np.isfinite(sp[t])):
                n_dead += 1
                break
            d = (lp[t] - lp[t - 1]) / eal - (sp[t] - sp[t - 1]) / eas
            pnl[t] += d
            acc += d
            bor[t] += BORROW_APY / 252.0
            last = t
        accs.append(acc)
        # 청산 반스프레드는 «다음 달에 안 들고 갈 때» 무는 것이라 여기서 미리 못 정한다.
        # 부르는 쪽이 다음 달 보유 집합과 비교해 물린다(run_leg 의 xs_exit_cost).
    return (pnl, cst, bor), {"open": len(accs), "new": n_new, "keep": n_keep,
                             "dead": n_dead, "worst": min(accs) if accs else 0.0,
                             "accs": accs, "last_idx": T - 1}, held_now


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

    # ── 규칙 C — 횡단면 최대괴리 상위10 (PREREG-2026-09-03-PAIRS-XS) ────────
    # 🚨 A·B 와 코호트 구조가 다르다. 거래창이 «다음 월말까지» 라 코호트가 겹치지 않고,
    #   자본이 늘 100% 투입된다(안 열린 페어가 없다). 그래서 위 루프에 못 끼워 넣는다 —
    #   억지로 끼우면 투입자본 나눗셈(cnt)의 의미가 규칙마다 달라진다.
    acc = np.zeros(T); acc_g = np.zeros(T); acc_c = np.zeros(T); cnt = np.zeros(T)
    held_prev, cost_prev = set(), {}
    npair, nshort = [], 0
    secct, accs_all = {}, []
    n_new = n_keep = n_dead = 0
    for k, e in enumerate(me):
        f0, f1 = e - FORM + 1, e + 1
        W = PX[f0:f1]
        ok = np.isfinite(W).all(0) & (W > 0).all(0)
        if mem is not None:
            mm = set(mem.get(dates[e][:7]) or [])
            ok &= np.array([t in mm for t in ts])
        idx = np.where(ok)[0]
        if len(idx) < 50:
            continue
        names = [ts[k2] for k2 in idx]
        pairs = select(W[:, idx], HI[f0:f1][:, idx], LO[f0:f1][:, idx],
                       names, sec, dual, "C", XS_SIZE)
        npair.append(len(pairs))
        if len(pairs) < XS_SIZE:
            nshort += 1
        if not pairs:
            continue
        for _, _, _, _, m_ in pairs:
            secct[m_["sec_a"]] = secct.get(m_["sec_a"], 0) + 1
            secct[m_["sec_b"]] = secct.get(m_["sec_b"], 0) + 1
        nxt = me[k + 1] if k + 1 < len(me) else min(e + XS_HOLD, T - 1)
        t0, t1 = e + 1, min(nxt + 1, T)
        if t1 - t0 < 5:
            continue
        (g, c, bw), d, held_now = trade_xs(PX[t0:t1][:, idx], pairs, W[0][idx], held_prev)
        # 이탈 페어의 청산 반스프레드 — 직전 달에 들었는데 이번 달에 없는 것만.
        exit_c = sum(cost_prev.get(kk, 0.0) / 2 for kk in (held_prev - held_now))
        c = c.copy()
        c[0] += exit_c
        acc[t0:t1] += (g - c - bw) / XS_SIZE
        acc_g[t0:t1] += (g - bw) / XS_SIZE
        acc_c[t0:t1] += c / XS_SIZE
        cnt[t0:t1] += 1
        n_new += d["new"]; n_keep += d["keep"]; n_dead += d["dead"]
        accs_all.extend(d["accs"])
        held_prev = held_now
        # 이번 달 페어의 왕복비용을 방향과 무관하게 기억한다 — 다음 달에 빠지면 그때 청산비를 문다.
        cost_prev = {}
        for (_a, _b, _sd, cst_, m_) in pairs:
            for s_ in (1, -1):
                cost_prev[(m_["a"], m_["b"], s_)] = cst_
    live = cnt > 0
    if live.sum() >= 252:
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
        mkt_m = np.array([mm_[k2] - 1.0 for k2 in sorted(mm_)])
        st_, mk, mr = stats(daily, dsub, mkt_m)
        gs, _, gr = stats(gross, dsub)
        sens = {}
        for lam, lbl in ((0.5, "x0.5"), (0.1, "x0.1")):
            s2, _, _ = stats(gross - lam * costs, dsub)
            sens[lbl] = {"mo_mean": s2["mo_mean"], "t_nw": s2["t_nw"], "cagr": s2["cagr"]}
        tot = sum(secct.values()) or 1
        st_.update({"rule": "C", "size": XS_SIZE, "leg": tag,
                    "n_cohort": len(npair), "pairs_med": float(np.median(npair or [0])),
                    "short_months": nshort,
                    "trades": n_new, "keep": n_keep, "dead": n_dead,
                    "turnover_pct": 100.0 * n_new / max(1, n_new + n_keep),
                    "worst_pair": 100.0 * (min(accs_all) if accs_all else 0.0),
                    "gross_mo": gs["mo_mean"], "gross_t_nw": gs["t_nw"],
                    "cost_mo": gs["mo_mean"] - st_["mo_mean"], "cost_sens": sens,
                    "util_pct": 100.0 * secct.get("Utilities", 0) / tot,
                    "sectors": dict(sorted(secct.items(), key=lambda x: -x[1])[:6]),
                    "pool": XS_POOL, "hold": "다음 월말까지"})
        nav = list(np.cumprod(1.0 + daily) * 100.0)
        res["C%d" % XS_SIZE] = {"stats": st_, "months": mk,
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
    "C": ("p-xs10", "페어 트레이딩 — 횡단면 최대괴리 상위10",
          "형성 252일 SSD 최소 상위 100쌍을 후보로 두고, 그중 형성 마지막 날 |z| 가 큰 "
          "순으로 다리가 겹치지 않게 10쌍(= 서로 다른 20종목) 보유 · 다음 월말까지 · "
          "트리거/손절 없음 · 달러중립 · 항상 만기투자",
          "🚨 사용자 요청 규칙이다(PREREG-2026-09-03-PAIRS-XS). 발상은 원문판 4종의 성적을 "
          "보기 전에 나왔지만, 배선한 나는 그 성적을 보고 있었다 — 특히 '항상 만기투자'는 "
          "GGR 의 투입자본 규약이 성적을 깎던 것을 아는 상태의 설계다. 원문판 A 를 대조로 "
          "나란히 싣는 이유가 그것이다. 근접은 자격이고 선택은 괴리라, A 와는 무엇을 "
          "고르는지가 다르다."),
}


def current_book(dates, ts, MATS, sec, dual):
    """가장 최근 형성창에서 각 (규칙,크기)가 고르는 페어 — '지금 무엇을 들고 있나'.

    🚨 이걸 안 실으면 목록에 **전략은 있는데 무엇을 사는지가 없다.** 이 저장소가 반복해 온
      실패(재 놓고 안 실었다 / 실어 놓고 안 그렸다)와 같은 자리다. 페어 전략의 보유는
      종목이 아니라 **쌍**이라 티커 목록으로 접으면 안 된다 — 'AEE 를 들고 있다'로 읽히는데
      실제로는 AEE 롱 + CNP 숏이고, 그 방향조차 형성 시점엔 정해져 있지 않다.
    """
    PX, HI, LO = MATS
    e = len(dates) - 1
    f0, f1 = e - FORM + 1, e + 1
    W = PX[f0:f1]
    ok = np.isfinite(W).all(0) & (W > 0).all(0)
    idx = np.where(ok)[0]
    names = [ts[k] for k in idx]
    out = {}
    for rule, size in COMBOS:
        if True:
            got = select(W[:, idx], HI[f0:f1][:, idx], LO[f0:f1][:, idx],
                         names, sec, dual, rule, size)
            out["%s%d" % (rule, size)] = [
                {"a": m["a"], "b": m["b"], "sec": m["sec_a"], "ssd": round(m["ssd"], 3),
                 "z": m.get("z"), "long": m.get("long"), "short": m.get("short")}
                for _, _, _, _, m in got]
    return out, dates[f0], dates[e]


def ticker_book(dates, ts, MATS, sec, dual, book, bk_from, bk_to, topk=4):
    """종목 → 그 종목의 최근접 페어들 → data/pairs_book.json (co.html 의 페어 탭이 읽는다).

    🚨 페어 선택도 진단도 **여기서 새로 만들지 않는다** — 위 select() 와 같은 형성창,
      같은 SSD 행렬, probe_pairs 의 같은 반감기 함수를 쓴다. 화면이 백테스트와 다른 페어를
      보여주면 그 화면은 이 랩의 산출물이 아니라 다른 계산이다.
    ⚠ 화면은 가격에서 스프레드 곡선을 직접 그린다(정규화가 결정적이라 재현이 정확하다).
      그러나 **밴드의 σ 는 여기서 준 값을 쓴다** — 그래야 그림의 ±2σ 가 백테스트의 진입
      문턱과 같은 숫자가 된다.
    """
    PX, HI, LO = MATS
    e = len(dates) - 1
    f0, f1 = e - FORM + 1, e + 1
    W = PX[f0:f1]
    ok = np.isfinite(W).all(0) & (W > 0).all(0)
    idx = np.where(ok)[0]
    names = [ts[k] for k in idx]
    Wk = W[:, idx]
    P = Wk / Wk[0]
    D = PP.ssd_matrix(P)
    pos = {t: k for k, t in enumerate(names)}
    for a, b in dual:
        if a in pos and b in pos:
            D[pos[a], pos[b]] = D[pos[b], pos[a]] = np.inf
    R = np.diff(np.log(Wk), axis=0)
    Rc = R - R.mean(0)
    rr = np.sqrt((Rc * Rc).sum(0))
    rr[rr == 0] = 1e-12
    CORR = (Rc.T @ Rc) / np.outer(rr, rr)

    inbook = {}
    for key, lst in (book or {}).items():
        for p in lst:
            inbook.setdefault("%s/%s" % (p["a"], p["b"]), []).append(key)

    by_t = {}
    for a in range(len(names)):
        order = np.argsort(D[a])[:topk]
        row = []
        for b in order:
            b = int(b)
            if not np.isfinite(D[a, b]):
                continue
            s = P[:, a] - P[:, b]
            sd = float(s.std(ddof=1))
            if not (sd > 0):
                continue
            hl = PP.half_life(s)
            k1, k2 = names[a] + "/" + names[b], names[b] + "/" + names[a]
            row.append({
                "b": names[b], "sec": sec.get(names[b], "?"),
                "ssd": round(float(D[a, b]), 3),
                "corr": round(float(CORR[a, b]), 3),
                "hl": round(float(hl), 1) if np.isfinite(hl) else None,
                "sd": round(sd, 5),
                # 지금 스프레드가 몇 σ 벌어져 있나. |z| ≥ 2 면 이 규칙은 지금 열려 있을 자리다.
                "z": round(float(s[-1] / sd), 2),
                "trips": trips_count(s, float(s.mean()), sd),
                "in": sorted(set(inbook.get(k1, []) + inbook.get(k2, []))),
            })
        if row:
            by_t[names[a]] = row
    return {
        "note": ("종목별 최근접 페어 %d개 — 형성창 %s~%s 의 정규화 누적수익 경로 SSD 기준. "
                 "build/pairs_backtest.py 가 백테스트와 같은 형성 함수로 만든다. "
                 "이 랩은 페어 전략 4종을 전부 기각했다(등급 열위) — 이 표는 신호가 아니라 "
                 "그 전략이 무엇을 고르는지를 보여주는 것이다." % (topk, bk_from, bk_to)),
        "as_of": bk_to, "form_from": bk_from, "form_to": bk_to, "form_days": FORM,
        "entry_sigma": ENTRY, "n_stocks": len(by_t),
        "book": {k: ["%s/%s" % (p["a"], p["b"]) for p in v] for k, v in (book or {}).items()},
        "by_t": by_t,
    }


def _note(s):
    """전략 카드의 «왜 이 판정인가» 한 문단. 규칙마다 결론을 만드는 것이 다르다.

    🚨 A·B 는 수렴 대 강제청산의 상쇄가 결론이고, C 는 회전율이 결론이다.
      한 문장으로 뭉뚱그리면 둘 중 하나는 틀린 설명이 된다 — C 에는 청산 사유 자체가 없다.
    """
    if s["rule"] == "C":
        return ("총수익(거래비용 전) 월 %+.3f%% · t_NW %.2f — 비용을 넣기 전에 이미 0이다. "
                "월 회전율 %.0f%%(10쌍 중 직전 달과 겹치는 것이 사실상 없다)라 왕복 비용이 "
                "월 %+.3f%% 쌓여 순수익이 %+.3f%% 가 된다. 즉 이 규칙의 손실은 «평균회귀가 "
                "안 통해서» 가 아니라 «벌 것이 없는데 매달 갈아타서» 다. Corwin-Schultz "
                "유효스프레드를 1/10 로 줄여도 총수익이 음수라 부호가 바뀌지 않는다."
                % (s["gross_mo"], s["gross_t_nw"] or 0, s["turnover_pct"],
                   s["cost_mo"], s["mo_mean"]))
    return ("총수익(거래비용 전) 월 %+.3f%% · t_NW %.2f — 비용을 넣기 전에 이미 0이다. "
            "수렴 청산 %d건 평균 %+.2f%% 대 기간종료 강제청산 %d건 평균 %+.2f%% 로 "
            "둘이 상쇄된다(수렴률 %.0f%%). Corwin-Schultz 유효스프레드를 1/10 로 "
            "줄여도 |t| < 0.5 라 비용 가정이 판정을 바꾸지 않는다."
            % (s["gross_mo"], s["gross_t_nw"] or 0,
               s["by_exit"]["conv"]["n"], s["by_exit"]["conv"]["mean"] or 0,
               s["by_exit"]["forced"]["n"], s["by_exit"]["forced"]["mean"] or 0,
               s["conv_pct"]))


def index_records(legs, book=None, bk_from=None, bk_to=None):
    """`full` 레그 4종 → data/strategy_index.py 가 읽는 모양.

    ⚠ 등록한 가설은 넷(규칙 2 × 크기 2)이고 목록에도 넷을 싣는다. 기각됐다고 빼지 않는다 —
      PREREG §4 가 그렇게 적었고, 빼면 다음 배치의 족 임계가 거짓말이 된다.
    ⚠ PIT 레그는 싣지 않는다. 이 랩이 PIT 배관을 걷어내는 중이라 값이 있다 없다 하면
      목록이 실행마다 달라진다 — 판정은 ⓐⓑ 에서 이미 갈렸으므로 결론이 바뀌지 않는다.
    """
    out = []
    for rule, size in COMBOS:
        sid0, nm0, rule_txt, why0 = NAMES[rule]
        if True:
            key = "%s%d" % (rule, size)
            r = (legs.get("full") or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            sh = s.get("sharpe")
            n = len(r["nav"])
            bk = (book or {}).get(key) or []
            hold = None
            if bk:
                w = round(100.0 / size, 1)     # 투입자본 규약 — N 페어에 1/N 씩
                hold = {
                    "kind": "pair", "as_of": bk_to,
                    "weights": [["%s/%s" % (p["a"], p["b"]), w] for p in bk],
                    "pairs": bk,
                    # ⚠ 마크다운을 쓰지 않는다. 이 문자열은 explorer 가 esc() 해서 넣으므로
                    #   ** 는 굵게가 아니라 별표 그대로 찍힌다(DATA-FACTS #24 와 같은 사고).
                    "note": ("형성창 %s~%s 로 고른 상위 %d페어. 어느 쪽을 롱/숏 할지는 여기 없다 — "
                             "스프레드가 ±2σ 벌어질 때 싼 쪽을 사고 비싼 쪽을 판다. "
                             "비중은 투입자본 1/%d 이고, 벌어지지 않은 페어는 현금으로 남는다."
                             % (bk_from, bk_to, size, size)),
                }
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
                "holdings": hold,
                "note": _note(s),
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
        for key in KEYS:
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            print("%-6s %-5s %5d %8.3f %7.2f %7.2f %7.2f %7s %7.1f %6s %6.0f"
                  % (lg, RLBL[s["rule"]], s["size"], s["mo_mean"],
                     s["cagr"] or 0, s["vol"], s["t_simple"] or 0,
                     "%.2f" % s["t_nw"] if s["t_nw"] is not None else "—",
                     s["mdd"], "%.2f" % s.get("beta", 0) if s.get("beta") is not None else "—",
                     s["util_pct"]))
    print("=" * len(hdr))

    print("\n총수익 vs 비용 — 🚨 이 분해가 결론을 정한다(규칙이 죽었나, 비용이 먹었나)")
    print("%-6s %-5s %4s %9s %9s %9s %9s %9s"
          % ("레그", "규칙", "N", "총 월%", "총 t_NW", "비용 월%", "순 월%", "순 t_NW"))
    for lg in ("full", "sub", "pit"):
        for key in KEYS:
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            print("%-6s %-5s %4d %9.3f %9s %9.3f %9.3f %9s"
                  % (lg, RLBL[s["rule"]], s["size"], s["gross_mo"],
                     "%.2f" % s["gross_t_nw"] if s["gross_t_nw"] is not None else "—",
                     -s["cost_mo"], s["mo_mean"],
                     "%.2f" % s["t_nw"] if s["t_nw"] is not None else "—"))
    print("비용 민감도(CS 를 배수로 줄였을 때 순 월수익%) — CS 는 대형주 실제보다 한 자릿수 크다")
    print("%-6s %-5s %4s %11s %11s %11s"
          % ("레그", "규칙", "N", "CS 그대로", "CS×0.5", "CS×0.1"))
    for lg in ("full", "sub", "pit"):
        for key in KEYS:
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            c = s["cost_sens"]
            print("%-6s %-5s %4d %11.3f %11s %11s"
                  % (lg, RLBL[s["rule"]], s["size"], s["mo_mean"],
                     "%.3f(%.2f)" % (c["x0.5"]["mo_mean"], c["x0.5"]["t_nw"] or 0),
                     "%.3f(%.2f)" % (c["x0.1"]["mo_mean"], c["x0.1"]["t_nw"] or 0)))

    print("\n청산 사유별 거래당 총손익(비용 전 · 다리 $1 기준 %) — 평균회귀가 실재하는가")
    print("%-6s %-5s %4s %18s %18s %13s"
          % ("레그", "규칙", "N", "수렴 청산", "기간종료 강제", "총기여%"))
    for lg in ("full", "sub", "pit"):
        for key in KEYS:
            r = (legs.get(lg) or {}).get(key)
            if not r or "by_exit" not in r["stats"]:
                continue          # C 는 트리거가 없어 청산 사유가 없다(결측이 아니라 설계다)
            e = r["stats"]["by_exit"]

            def f_(k, e=e):
                return ("%d건 %+.2f" % (e[k]["n"], e[k]["mean"])) if e[k]["n"] else "—"
            print("%-6s %-5s %4d %18s %18s %13.1f"
                  % (lg, RLBL[r["stats"]["rule"]], r["stats"]["size"],
                     f_("conv"), f_("forced"),
                     e["conv"]["sum"] + e["forced"]["sum"] + e["dead"]["sum"]))

    print("\n거래 진단")
    print("%-6s %-5s %4s %7s %7s %7s %7s %8s %8s %8s"
          % ("레그", "규칙", "N", "코호트", "진입", "수렴%", "강제", "첫이틀%", "최악페어%", "후보부족"))
    for lg in ("full", "sub", "pit"):
        for key in KEYS:
            r = (legs.get(lg) or {}).get(key)
            if not r:
                continue
            s = r["stats"]
            if s["rule"] == "C":
                continue          # 진입/수렴/강제 개념이 없다 — 아래 전용 표로 뺀다
            print("%-6s %-5s %4d %7d %7d %6.1f%% %7d %7.1f%% %8.1f %8d"
                  % (lg, RLBL[s["rule"]], s["size"], s["n_cohort"],
                     s["trades"], s["conv_pct"], s["forced"], s["day0_pct"],
                     s["worst_pair"], s["short_months"]))

    print(chr(10) + "규칙 C(횡단면 최대괴리) 진단 — 이 규칙의 성패는 회전율과 총·순 격차가 가른다")
    print("%-6s %6s %7s %9s %9s %9s %9s %9s"
          % ("레그", "코호트", "회전율", "총수익월", "총t_NW", "비용월", "순수익월", "최악페어%"))
    for lg in ("full", "sub", "pit"):
        r = (legs.get(lg) or {}).get("C%d" % XS_SIZE)
        if not r:
            continue
        s2 = r["stats"]
        print("%-6s %6d %6.1f%% %+8.3f%% %9.2f %+8.3f%% %+8.3f%% %9.1f"
              % (lg, s2["n_cohort"], s2["turnover_pct"], s2["gross_mo"], s2["gross_t_nw"],
                 s2["cost_mo"], s2["mo_mean"], s2["worst_pair"]))

    # ── 생존편향 = sub − pit ──────────────────────────────────────────
    print("\n생존편향(sub − pit) — 🚨 full−pit 이 아니다. 창을 맞춘 두 계열의 차이만이 편향이다.")
    for key in KEYS:
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
    for key in KEYS:
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

    book, bk_from, bk_to = current_book(dates, ts, MATS, sec, dual)
    print("\n지금의 페어북(형성창 %s ~ %s)" % (bk_from, bk_to))
    for key in KEYS:
        bk = book.get(key) or []
        print("  %-4s %2d쌍  %s%s"
              % (key, len(bk), " · ".join("%s/%s" % (p["a"], p["b"]) for p in bk[:8]),
                 " …" if len(bk) > 8 else ""))

    doc = {
        "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "prereg": "build/PREREG-2026-08-12-PAIRS.md",
        "params": {"form": FORM, "trade": TRADE, "sizes": list(SIZES), "entry_sigma": ENTRY,
                   "hl": [HL_LO, HL_HI], "min_trips": MIN_TRIPS, "borrow_apy": BORROW_APY,
                   "pit_start": PIT_START, "nw_lags": NW_LAGS},
        "bench_label": BENCH_LABEL,
        "book_from": bk_from, "book_to": bk_to, "book": book,
        "strategies": index_records(legs, book, bk_from, bk_to),
        "legs": legs, "verdicts": verdicts,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), default=float) + "\n")
    print("\n→ %s" % OUT)

    tb = ticker_book(dates, ts, MATS, sec, dual, book, bk_from, bk_to)
    io.open(OUTBOOK, "w", encoding="utf-8").write(
        json.dumps(tb, ensure_ascii=False, separators=(",", ":"), default=float) + "\n")
    print("→ %s (%d종목 × 최근접 4페어 · %dKB)"
          % (OUTBOOK, tb["n_stocks"], os.path.getsize(OUTBOOK) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
