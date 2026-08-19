# -*- coding: utf-8 -*-
"""build/pead_backtest.py — 실적발표 반응 드리프트(PEAD) → data/pead.json

규약: build/PREREG-2026-08-19-PEAD.md (수익률 계산 전에 커밋). 규칙은 거기 있다.

  신호: 월말 기준 최근 63거래일 안의 실적발표(8-K Item 2.02 접수일)에 대해
        발표 반응 AR = ret(발표일−1 → 발표일+1) − 같은 창 ^GSPC.
  포트: PIT 멤버(그 달 SPX∪NDX) 중 신호 보유 종목을 AR 십분위로 나눠
        상위 십분위(D1) 동일가중 · 월 리밸. 대조군 = 같은 달 멤버 전원 동일가중.
  근거: Chan–Jegadeesh–Lakonishok (1996) — 발표 반응 모멘텀. x-sue(회계 서프라이즈)와
        보완축: 시장이 가이던스·마진까지 평가한 값이다.

    python build/pead_backtest.py
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
OUT = os.path.join(DATA, "pead.json")
COST = 0.0005            # 편도 5bp · 민감도 20bp
LOOK = 63                # 신호 창(거래일) — 한 분기
START, END = "2015-01", "2026-07"
NDEC = 10


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
        return None, None, None
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    t = m / (sd / math.sqrt(len(xs))) if sd > 0 else None
    srt = sorted(xs)
    ex = srt[:-2] if len(srt) > 4 else srt
    return m, t, sum(ex) / len(ex)


def main() -> int:
    dts, px, spx = load_px()
    n = len(dts)
    me = month_ends(dts)
    d2i = {d: i for i, d in enumerate(dts)}
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    months = H["months"]
    ED = (json.load(io.open(os.path.join(DATA, "earn_dates.json"), encoding="utf-8")) or {}).get("co") or {}

    def gidx(d):
        i = d2i.get(d)
        if i is not None:
            return i
        lo, hi = 0, n - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if dts[mid] < d:
                lo = mid + 1
            else:
                hi = mid
        return lo if dts[lo] >= d else None

    # 종목별 발표일 → 격자 색인(미리 계산)
    EIX = {t: sorted(x for x in (gidx(d) for d in ds) if x is not None)
           for t, ds in ED.items()}

    def ar3(t, i_ev):
        """발표 반응 — 발표일−1 → 발표일+1 종가, 시장(^GSPC) 차감."""
        a = px.get(t)
        if not a or i_ev - 1 < 0 or i_ev + 1 >= n:
            return None
        p0, p1 = a[i_ev - 1], a[i_ev + 1]
        b0, b1 = spx[i_ev - 1], spx[i_ev + 1]
        if not p0 or not p1 or not b0 or not b1:
            return None
        return (p1 / p0 - b1 / b0)

    navD = [100.0] * NDEC
    navA = 100.0
    retD = [[] for _ in range(NDEC)]
    retA, dBA, ym_list = [], [], []
    prev_hold = None
    cov_num = cov_den = 0
    import bisect
    for k in range(len(me) - 1):
        i0, i1 = me[k], me[k + 1]
        ym = dts[i0][:7]
        if not (START <= ym <= END):
            continue
        mm = months.get(ym) or {}
        mem = sorted(set(mm.get("spx") or []) | set(mm.get("ndx") or []))
        univ = [t for t in mem if px.get(t) and px[t][i0] and px[t][i1]]
        if len(univ) < 100:
            continue
        sig = {}
        for t in univ:
            ev = EIX.get(t)
            cov_den += 1
            if not ev:
                continue
            j = bisect.bisect_right(ev, i0) - 1     # 월말 이전 마지막 발표(당일 포함 — 접수일 ≤ 월말)
            if j < 0 or i0 - ev[j] >= LOOK:
                continue
            v = ar3(t, ev[j])
            if v is not None:
                sig[t] = v
                cov_num += 1
        cand = sorted(sig, key=lambda t: -sig[t])
        if len(cand) < 100:
            continue
        dec = max(1, len(cand) // NDEC)
        # 전 멤버 대조군
        rA = sum(px[t][i1] / px[t][i0] - 1 for t in univ) / len(univ)
        retA.append(rA)
        navA *= 1 + rA
        hold1 = None
        for q in range(NDEC):
            hh = cand[q * dec:(q + 1) * dec] if q < NDEC - 1 else cand[(NDEC - 1) * dec:]
            r = sum(px[t][i1] / px[t][i0] - 1 for t in hh) / len(hh)
            if q == 0:
                # 비용은 매매하는 D1 에만 태운다(다른 십분위는 관찰용)
                if prev_hold is None:
                    r -= COST
                else:
                    chg = len(set(hh) - set(prev_hold)) / max(1, len(hh))
                    r -= chg * 2 * COST
                hold1 = hh
            retD[q].append(r)
            navD[q] *= 1 + r
        prev_hold = hold1
        dBA.append(retD[0][-1] - rA)
        ym_list.append(ym)

    nm = len(ym_list)
    yrs = nm / 12.0
    cagr = lambda nav: round(((nav / 100.0) ** (1 / yrs) - 1) * 100, 2)
    mBA, tBA, top2ex = stats_t(dBA)
    by_year = {}
    for ym, ddd in zip(ym_list, dBA):
        by_year.setdefault(ym[:4], []).append(ddd)
    year_tbl = {y: round(sum(v) * 100, 2) for y, v in sorted(by_year.items())}
    wins = sum(1 for v in year_tbl.values() if v >= 0)
    half = nm // 2
    h1, h2 = sum(dBA[:half]) * 100, sum(dBA[half:]) * 100
    # 십분위 단조성 — D 순위와 평균수익의 스피어만
    dec_mean = [sum(r) / len(r) for r in retD]
    rank_ret = sorted(range(NDEC), key=lambda q: -dec_mean[q])
    import statistics
    d_rank = list(range(NDEC))
    r_rank = [rank_ret.index(q) for q in range(NDEC)]
    mu_d, mu_r = statistics.mean(d_rank), statistics.mean(r_rank)
    cov = sum((a - mu_d) * (b - mu_r) for a, b in zip(d_rank, r_rank))
    sd_d = math.sqrt(sum((a - mu_d) ** 2 for a in d_rank))
    sd_r = math.sqrt(sum((b - mu_r) ** 2 for b in r_rank))
    spear = round(cov / (sd_d * sd_r), 3) if sd_d and sd_r else None
    # 비용 민감도 20bp — D1 총수익에서 회전율 근사 재계산은 생략하고 평균 회전율로 근사하지 않는다.
    # 대신 «비용 전 평균 − 0.4×평균회전» 대신, 매월 전량 교체 가정(최악)을 같이 낸다.
    worst20 = (mBA - 2 * 0.0020) if mBA is not None else None

    cover = round(100.0 * cov_num / max(1, cov_den), 1)
    print("월 %d · 커버 %.1f%% · D1 CAGR %s%% · 전멤버 %s%%"
          % (nm, cover, cagr(navD[0]), cagr(navA)))
    print("D1−전멤버 월평균 %+.3f%%p · t %s · 상위2제외 %+.3f%%p"
          % (mBA * 100, (None if tBA is None else round(tBA, 2)), top2ex * 100))
    print("연도승률 %d/%d · 반분 [%+.2f, %+.2f]%%p · 십분위 스피어만 %s"
          % (wins, len(year_tbl), h1, h2, spear))
    print("십분위 CAGR:", [cagr(v) for v in navD])
    print("최악 비용(월 전량교체·20bp): 월평균 %+.3f%%p" % (worst20 * 100))

    doc = {
        "note": "실적발표 반응 드리프트(PEAD·CJL 1996). 신호는 8-K Item 2.02 접수일의 "
                "3일 반응(시장 차감), 포트는 PIT 멤버 상위 십분위 동일가중 월 리밸. "
                "규칙·채점은 PREREG-2026-08-19-PEAD.md 에 계산 전 커밋.",
        "prereg": "build/PREREG-2026-08-19-PEAD.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "months": nm, "coverage_pct": cover, "cost_oneway": COST, "look_td": LOOK,
        "cagr_d1": cagr(navD[0]), "cagr_univ": cagr(navA),
        "cagr_deciles": [cagr(v) for v in navD],
        "ba": {"monthly_bp": round(mBA * 10000, 1),
               "t": (None if tBA is None else round(tBA, 2)),
               "top2ex_bp": round(top2ex * 10000, 1),
               "halves_pp": [round(h1, 2), round(h2, 2)],
               "year_wins": "%d/%d" % (wins, len(year_tbl)),
               "worst_cost20_bp": round(worst20 * 10000, 1)},
        "years": year_tbl, "decile_spearman": spear,
        "monthly": {"ym": ym_list, "d1": [round(x, 6) for x in retD[0]],
                    "univ": [round(x, 6) for x in retA]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
