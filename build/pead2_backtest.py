# -*- coding: utf-8 -*-
"""build/pead2_backtest.py — PEAD 2판(발표일 앵커 · 달력시간 포트폴리오) → data/pead2.json

규약: build/PREREG-2026-08-19-PEAD2.md (계산 전 커밋). 규칙은 거기 있다.

  진입: AR(접수일−1→+1 · 시장 차감)이 직전 252거래일 발표 AR 분포의 상위 20% 면,
        접수일+2 이후 첫 주말 종가에 산다. 보유 60거래일, 지난 뒤 첫 주말에 판다.
  포트: 주간 리밸 · 활성 동일가중 · 비면 유니버스 동일가중(오버레이).

    python build/pead2_backtest.py
"""
from __future__ import annotations
import bisect
import datetime as dt
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "pead2.json")
TOP_PCT = 0.20         # 상위 오분위 — 문헌 관행(§0)
HOLD_TD = 60           # Bernard–Thomas 드리프트 집중 구간(§0)
LAG_TD = 2             # 접수일+2 이후 진입(선견 차단)
PCTL_WIN = 252         # 시점정확 백분위 창
COST_BP = 5
GATE_BP = 20
START, END = "2015-01", "2026-07"


def load_px():
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dts = st["pxd_dates"]
    n = len(dts)
    px = {}
    sd = os.path.join(DATA, "sd")
    for fn in os.listdir(sd):
        if fn.endswith(".json"):
            a = (json.load(io.open(os.path.join(sd, fn), encoding="utf-8")) or {}).get("pxd") or []
            px[fn[:-5]] = a + [None] * (n - len(a))
    sl = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))
    ds2 = sl["dates"]
    d2i = {d: i for i, d in enumerate(dts)}
    for t, v in sl["px"].items():
        if t in px:
            continue
        a = [None] * n
        for k, p in enumerate(v["p"]):
            if p is not None:
                i = d2i.get(ds2[v["i0"] + k])
                if i is not None:
                    a[i] = p
        px[t] = a
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bmap = dict(zip(B["dates"], B["series"]["spx"]["px"]))
    spx = [bmap.get(d) for d in dts]
    return dts, px, spx


def week_ends(dts):
    """주간 마지막 거래일 색인 — ISO 주가 바뀌기 직전 날."""
    out = []
    for i in range(len(dts) - 1):
        w0 = dt.date.fromisoformat(dts[i]).isocalendar()[:2]
        w1 = dt.date.fromisoformat(dts[i + 1]).isocalendar()[:2]
        if w0 != w1:
            out.append(i)
    out.append(len(dts) - 1)
    return out


def tstat(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, (m / (sd / math.sqrt(n)) if sd > 0 else None)


def main() -> int:
    dts, px, spx = load_px()
    n = len(dts)
    d2i = {d: i for i, d in enumerate(dts)}
    we = week_ends(dts)
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    months = H["months"]
    ED = (json.load(io.open(os.path.join(DATA, "earn_dates.json"), encoding="utf-8")) or {}).get("co") or {}

    def gidx(d):
        i = d2i.get(d)
        if i is not None:
            return i
        j = bisect.bisect_left(dts, d)
        return j if j < n else None

    # ── 이벤트 → (발표 격자색인, AR) — 유니버스(그 달 PIT 멤버) 발표만 ─────────
    events = []                     # (i_ev, ticker, ar)
    for t, ds in ED.items():
        a = px.get(t)
        if not a:
            continue
        for d in ds:
            ym = d[:7]
            mm = months.get(ym) or {}
            if t not in (mm.get("spx") or []) and t not in (mm.get("ndx") or []):
                continue
            i = gidx(d)
            if i is None or i - 1 < 0 or i + 1 >= n:
                continue
            p0, p1 = a[i - 1], a[i + 1]
            b0, b1 = spx[i - 1], spx[i + 1]
            if not p0 or not p1 or not b0 or not b1:
                continue
            events.append((i, t, (p1 / p0) - (b1 / b0)))
    events.sort()
    ev_i = [e[0] for e in events]
    ev_ar = [e[2] for e in events]
    print("유니버스 발표 이벤트 %d건" % len(events))

    # ── 시점정확 백분위 — i 시점에서 직전 PCTL_WIN 거래일의 AR 분포 ─────────
    def is_top(i_ev, ar):
        lo = bisect.bisect_left(ev_i, i_ev - PCTL_WIN)
        hi = bisect.bisect_left(ev_i, i_ev)          # 자기 자신·같은 날 이후 제외
        past = ev_ar[lo:hi]
        if len(past) < 60:                            # 분포가 서기 전(초기)엔 진입하지 않는다
            return False
        k = sum(1 for x in past if x <= ar)
        return (k / len(past)) >= (1 - TOP_PCT)

    # ── 달력시간 포트폴리오 · 주간 ──────────────────────────────────────
    active = []                     # (만기색인, 티커)
    pend = []                       # 진입 대기 (진입가능색인, 티커)
    for i_ev, t, ar in events:
        if is_top(i_ev, ar):
            pend.append((i_ev + LAG_TD, t))
    pend.sort()
    pi = 0

    retP, retU, exs, wk_ym, n_active = [], [], [], [], []
    prev_hold = None
    navP = navU = 100.0
    turn_sum = 0.0
    for k in range(len(we) - 1):
        i0, i1 = we[k], we[k + 1]
        ym = dts[i0][:7]
        if not (START <= ym <= END):
            # 창 밖이어도 대기열은 소화한다(창 진입 시점에 이미 활성이도록)
            while pi < len(pend) and pend[pi][0] <= i0:
                active.append((pend[pi][0] + HOLD_TD, pend[pi][1]))
                pi += 1
            active = [(e, t) for e, t in active if e > i0]
            continue
        while pi < len(pend) and pend[pi][0] <= i0:
            active.append((pend[pi][0] + HOLD_TD, pend[pi][1]))
            pi += 1
        active = [(e, t) for e, t in active if e > i0]
        mm = months.get(ym) or {}
        mem = sorted(set(mm.get("spx") or []) | set(mm.get("ndx") or []))
        univ = [t for t in mem if px.get(t) and px[t][i0] and px[t][i1]]
        if len(univ) < 100:
            continue
        hold = sorted({t for _e, t in active
                       if px.get(t) and px[t][i0] and px[t][i1]})
        overlay = not hold
        use = univ if overlay else hold
        rP = sum(px[t][i1] / px[t][i0] - 1 for t in use) / len(use)
        rU = sum(px[t][i1] / px[t][i0] - 1 for t in univ) / len(univ)
        # 비용 — 실회전(교체 비율)
        if prev_hold is not None and use:
            chg = len(set(use) - set(prev_hold)) / len(use)
            turn_sum += chg
            rP -= chg * 2 * COST_BP / 10000.0
        prev_hold = use
        retP.append(rP)
        retU.append(rU)
        exs.append(rP - rU)
        wk_ym.append(dts[i0])
        n_active.append(len(hold))
        navP *= 1 + rP
        navU *= 1 + rU

    nw = len(exs)
    yrs = nw / 52.0
    avg_turn = turn_sum / max(1, nw - 1)
    m5, t5 = tstat(exs)
    # 20bp 관문 — 5bp 를 되돌리고 20bp 를 태운다(실회전)
    exs20 = [x + avg_turn * 2 * COST_BP / 10000.0 - avg_turn * 2 * GATE_BP / 10000.0 for x in exs]
    _, t20 = tstat(exs20)
    half = nw // 2
    h1, h2 = sum(exs[:half]) * 100, sum(exs[half:]) * 100
    srt = sorted(exs)
    top2ex = sum(srt[:-2]) / (len(srt) - 2)
    med_act = sorted(n_active)[nw // 2]
    cagr = lambda nav: round(((nav / 100.0) ** (1 / yrs) - 1) * 100, 2)

    g = {
        "G1_t": {"t": round(t5, 2), "pass": bool(t5 >= 2)},
        "G2_halves": {"pp": [round(h1, 2), round(h2, 2)], "pass": bool(h1 > 0 and h2 > 0)},
        "G3_top2": {"weekly_bp_ex": round(top2ex * 10000, 1), "pass": bool(top2ex > 0)},
        "G4_cost20": {"t": round(t20, 2), "pass": bool(t20 >= 2)},
        "G5_breadth": {"median_active": med_act, "pass": bool(med_act >= 15)},
    }
    n_pass = sum(1 for v in g.values() if v["pass"])
    verdict = "후보" if n_pass == 5 else "기각 (%d/5)" % n_pass

    ov_wk = sum(1 for x in n_active if x == 0)
    print("주간 %d관측 · 활성 중앙 %d종 · 오버레이(포지션 0) %d주 · 평균 실회전 %.1f%%/주"
          % (nw, med_act, ov_wk, avg_turn * 100))
    print("포트 CAGR %s%% · 대조군 %s%% · 초과 주평균 %+.3f%%p · t %.2f (20bp: %.2f)"
          % (cagr(navP), cagr(navU), m5 * 100, t5, t20))
    print("반분 [%+.2f, %+.2f]%%p · 상위2제외 주평균 %+.4f%%p" % (h1, h2, top2ex * 100))
    for kk, v in g.items():
        print("  %-12s %s %s" % (kk, "✅" if v["pass"] else "❌", {a: b for a, b in v.items() if a != "pass"}))
    print("판정:", verdict)

    doc = {
        "note": "PEAD 2판 — 발표일 앵커 달력시간 포트폴리오(진입 접수일+2 이후 첫 주말 · "
                "보유 60거래일 · 상위 20% 시점정확 백분위 · 주간 리밸 · 오버레이). "
                "창·문턱은 문헌 상수이고 규칙·채점은 PREREG-2026-08-19-PEAD2.md 에 계산 전 커밋. "
                "PEAD 계열 2번째 시도 — 다중검정 부담을 리포트에 적는다.",
        "prereg": "build/PREREG-2026-08-19-PEAD2.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"top_pct": TOP_PCT, "hold_td": HOLD_TD, "lag_td": LAG_TD,
                   "pctl_win": PCTL_WIN, "cost_bp": COST_BP},
        "weeks": nw, "events_universe": len(events),
        "median_active": med_act, "overlay_weeks": ov_wk,
        "avg_weekly_turnover_pct": round(avg_turn * 100, 1),
        "cagr_port": cagr(navP), "cagr_univ": cagr(navU),
        "excess": {"weekly_bp": round(m5 * 10000, 1), "t": round(t5, 2), "t_cost20": round(t20, 2),
                   "halves_pp": [round(h1, 2), round(h2, 2)],
                   "top2ex_weekly_bp": round(top2ex * 10000, 1)},
        "gates": g, "n_pass": n_pass, "verdict": verdict,
        "weekly": {"d": wk_ym, "ex": [round(x, 6) for x in exs], "n_active": n_active},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
