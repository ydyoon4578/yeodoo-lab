# -*- coding: utf-8 -*-
"""build/e12_improve.py — E12 개선판 «편입 페이드» 포트폴리오 → data/e12_fade.json

규약: PREREG-2026-08-19-E12.md §7 (수익률 계산 전에 커밋). 규칙은 거기 있다.

  포트 A: 그 달 말 지수 멤버 전원 동일가중 · 월 리밸
  포트 B: A − 최근 12개월 편입종목
  포트 C: 최근 12개월 편입종목만
  두 지수(SPX·NDX) 각각 · 2015-01 ~ 2026-07 · 비용 회전율 × 편도 5bp

🚨 이 규칙은 같은 날의 E12 결과에서 유래했다 — 이 백테스트는 구성상 표본 내다.
   통과해도 «검증됨» 이 아니라 «표본 내 일관» 이다(§7 채점 기준).

    python build/e12_improve.py
"""
from __future__ import annotations
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
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(DATA, "e12_fade.json")
COST = 0.0005          # 편도 5bp — §7
START, END = "2015-01", "2026-07"
EXCL_TD = 252          # 편입 제외창(거래일) — §7, 맞추지 않는다
SENS_TD = (63, 126)    # 민감도 전용


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
    return dts, px


def month_ends(dts):
    me, cur = [], None
    for i, d in enumerate(dts):
        m = d[:7]
        if cur is None:
            cur = m
        elif m != cur:
            me.append(i - 1)
            cur = m
    me.append(len(dts) - 1)
    return me


def stats_t(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 6:
        return None, None
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    return m, (m / (sd / math.sqrt(len(xs))) if sd > 0 else None)


def run(tag, mem_key, ev_file, dts, px, me):
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    months = H["months"]
    E = json.load(io.open(os.path.join(BUILD, ev_file), encoding="utf-8"))
    add_ed = {}                      # 티커 → 실효일들(같은 이름이 두 번 들 수 있다)
    for e in E:
        if e.get("add"):
            add_ed.setdefault(e["add"], []).append(e["d"])
    n = len(dts)

    def recent_add(t, i):
        """dts[i] 시점에 «최근 EXCL_TD 거래일 안 편입» 인가 — 실효일 ≤ 오늘만 안다."""
        for d in add_ed.get(t, ()):
            j = next((k for k, x in enumerate(dts) if x >= d), None)
            if j is not None and j <= i and i - j < EXCL_TD:
                return True
        return False

    navA = navB = navC = 100.0
    rowsA, rowsB, rowsC = [], [], []
    prevA = prevB = prevC = None
    ym_list = []
    n_excl_sum = 0
    for k in range(len(me) - 1):
        i0, i1 = me[k], me[k + 1]
        ym = dts[i0][:7]
        if not (START <= ym <= END):
            continue
        mem = (months.get(ym) or {}).get(mem_key) or []
        holdA = [t for t in mem if px.get(t) and px[t][i0] and px[t][i1]]
        if len(holdA) < 30:
            continue                  # 멤버십 결손 달은 건너뛴다(만들어 채우지 않는다)
        excl = {t for t in holdA if recent_add(t, i0)}
        holdB = [t for t in holdA if t not in excl]
        holdC = sorted(excl)
        n_excl_sum += len(excl)

        def ew_ret(hold):
            if not hold:
                return None
            return sum(px[t][i1] / px[t][i0] - 1 for t in hold) / len(hold)

        def turn_cost(prev, hold):
            if prev is None:
                return COST           # 첫 진입 편도
            s0, s1 = set(prev), set(hold)
            if not s1:
                return 0.0
            chg = len(s1 - s0) / len(s1)
            return chg * 2 * COST

        rA, rB, rC = ew_ret(holdA), ew_ret(holdB), ew_ret(holdC)
        if rA is None or rB is None:
            continue
        rA -= turn_cost(prevA, holdA)
        rB -= turn_cost(prevB, holdB)
        navA *= 1 + rA
        navB *= 1 + rB
        rowsA.append(rA); rowsB.append(rB)
        if rC is not None:
            rC -= turn_cost(prevC, holdC)
            navC *= 1 + rC
            rowsC.append(rC)
        else:
            rowsC.append(None)
        prevA, prevB, prevC = holdA, holdB, holdC
        ym_list.append(ym)

    nm = len(ym_list)
    yrs = nm / 12.0
    def cagr(nav):
        return round(((nav / 100.0) ** (1 / yrs) - 1) * 100, 2)
    dBA = [b - a for a, b in zip(rowsA, rowsB)]
    dCA = [(c - a) if c is not None else None for a, c in zip(rowsA, rowsC)]
    mBA, tBA = stats_t(dBA)
    # 연도별 — B−A 월간 합(근사)
    by_year = {}
    for ym, dd in zip(ym_list, dBA):
        by_year.setdefault(ym[:4], []).append(dd)
    year_tbl = {y: round(sum(v) * 100, 2) for y, v in sorted(by_year.items())}
    wins = sum(1 for v in year_tbl.values() if v >= 0)
    half = nm // 2
    h1 = sum(dBA[:half]) * 100
    h2 = sum(dBA[half:]) * 100
    c1 = sum(x for x in dCA[:half] if x is not None) * 100
    c2 = sum(x for x in dCA[half:] if x is not None) * 100
    q = {"Q1_t": (None if tBA is None else round(tBA, 2)),
         "Q2_year_wins": "%d/%d" % (wins, len(year_tbl)),
         "Q3_halves_BA": [round(h1, 2), round(h2, 2)],
         "Q4_halves_CA": [round(c1, 2), round(c2, 2)]}
    passed = sum([
        1 if (tBA is not None and tBA >= 2) else 0,
        1 if wins >= 8 else 0,
        1 if (h1 > 0 and h2 > 0) else 0,
        1 if (c1 < 0 and c2 < 0) else 0])
    print("[%s] %d개월 · A(전멤버 EW) CAGR %s%% · B(편입 페이드) %s%% · C(최근 편입만) %s%%"
          % (tag, nm, cagr(navA), cagr(navB), cagr(navC)))
    print("   B−A 월평균 %+.3f%%p · t %s · 연도승률 %s · 반분 [%s, %s] · C−A 반분 [%s, %s]"
          % (mBA * 100, q["Q1_t"], q["Q2_year_wins"], q["Q3_halves_BA"][0], q["Q3_halves_BA"][1],
             q["Q4_halves_CA"][0], q["Q4_halves_CA"][1]))
    print("   채점 %d/4 · 월평균 제외종목 %.1f개" % (passed, n_excl_sum / max(1, nm)))
    return {"months": nm, "cagrA": cagr(navA), "cagrB": cagr(navB), "cagrC": cagr(navC),
            "ba_monthly_bp": round(mBA * 10000, 1), "q": q, "passed": passed,
            "years": year_tbl, "avg_excluded": round(n_excl_sum / max(1, nm), 1)}


def main() -> int:
    dts, px = load_px()
    me = month_ends(dts)
    spx = run("SPX", "spx", "e12_events.json", dts, px, me)
    ndx = run("NDX", "ndx", "e12_events_ndx.json", dts, px, me)
    doc = {
        "note": "E12 개선판 «편입 페이드» — 지수 멤버 동일가중(A)에서 최근 12개월 편입종목을 "
                "뺀 것(B). 🚨 규칙이 같은 날의 E12 결과에서 유래했으므로 이 백테스트는 구성상 "
                "표본 내다 — 채점을 통과해도 «표본 내 일관» 이지 «검증됨» 이 아니다. "
                "진짜 판정은 2026-08-19 이후 편입 이벤트의 전방 기록으로만 한다(§7).",
        "prereg": "build/PREREG-2026-08-19-E12.md §7",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cost_oneway": COST, "excl_td": EXCL_TD, "span": [START, END],
        "spx": spx, "ndx": ndx,
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
