# -*- coding: utf-8 -*-
"""build/aegis_backtest.py — 이지스(선택×방패) → data/aegis.json

규약: build/PREREG-2026-08-19-AEGIS.md (계산 전 커밋). 판정은 사용자 6문 —
vs SPX·NDX 각각 수익(CAGR)·샤프·MDD. 통계 관문은 참고 패널로만 병기.

  선택: PIT SPX∪NDX 멤버 중 dist200(종가/MA200−1) 상위 25종 EW · 주간 리밸
  방패: 주말 종가에 ^GSPC < MA200 이면 전량 현금(0%) — Faber(2007) 상수
  분해: A 선택만 · B 방패만(지수 보유) · C 이지스

    python build/aegis_backtest.py
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
OUT = os.path.join(DATA, "aegis.json")
N_SEL = 25
MA_TD = 200
MA_MIN = 160
COST_BP = 5
START = "2015-01"
DIV_ADJ = {"spx": 1.8, "ndx": 0.8}     # 배당 보정(%p/yr) — §0 배당 기저


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
    bench = {}
    for key in ("spx", "ndx"):
        bmap = dict(zip(B["dates"], B["series"][key]["px"]))
        bench[key] = [bmap.get(d) for d in dts]
    return dts, px, bench


def week_ends(dts):
    out = []
    for i in range(len(dts) - 1):
        w0 = dt.date.fromisoformat(dts[i]).isocalendar()[:2]
        w1 = dt.date.fromisoformat(dts[i + 1]).isocalendar()[:2]
        if w0 != w1:
            out.append(i)
    out.append(len(dts) - 1)
    return out


class Sig:
    """dist200 — 티커별 prefix 합으로 O(1) 창 평균."""
    def __init__(self, px, n):
        self.px, self.n, self.c = px, n, {}

    def _pref(self, t):
        pr = self.c.get(t)
        if pr is None:
            a = self.px[t]
            ps = [0.0] * (self.n + 1)
            pc = [0] * (self.n + 1)
            for i in range(self.n):
                v = a[i]
                ps[i + 1] = ps[i] + (v if v else 0.0)
                pc[i + 1] = pc[i] + (1 if v else 0)
            pr = self.c[t] = (ps, pc)
        return pr

    def dist(self, t, i):
        if i < MA_TD - 1:
            return None
        p = self.px[t][i]
        if not p:
            return None
        ps, pc = self._pref(t)
        s = ps[i + 1] - ps[i + 1 - MA_TD]
        c = pc[i + 1] - pc[i + 1 - MA_TD]
        if c < MA_MIN:
            return None
        return p / (s / c) - 1


def engine(dts, px, bench, months, we, sig, bsig,
           select=True, shield=True, n_sel=N_SEL, cost_bp=COST_BP,
           shield_key="spx", monthly=False, cash_rate=0.0, cash_from=None,
           hold_key="spx", want_detail=False):
    """한 변형 실행 → 일간 NAV·주간 수익·상태. select=False 면 지수(hold_key) 보유."""
    cost = cost_bp / 10000.0
    nav = 100.0
    was_on, prev_hold, state = None, None, None
    hold, on = [], False
    daily_d, daily_v = [], []
    wk_ret, wk_on, wk_d = [], [], []
    ew_univ = []
    skipped = 0
    for k in range(len(we) - 1):
        i0, i1 = we[k], we[k + 1]
        ym = dts[i0][:7]
        if ym < START:
            continue
        mm = months.get(ym) or {}
        mem = sorted(set(mm.get("spx") or []) | set(mm.get("ndx") or []))
        univ = [t for t in mem if px.get(t) and px[t][i0] and px[t][i1]]
        if len(univ) < 100:
            skipped += 1
            continue
        # 방패 상태 — 주간이면 매주, 월간이면 그 달 마지막 주말에만 갱신(§5)
        upd = (state is None) or (not monthly) or (dts[i1][:7] != ym)
        if upd:
            d200 = bsig.dist(shield_key, i0)
            state = (d200 is not None and d200 >= 0) if shield else True
        on = state
        # 보유 결정
        if select:
            cand = [(t, sig.dist(t, i0)) for t in univ]
            cand = [(t, v) for t, v in cand if v is not None]
            cand.sort(key=lambda x: (-x[1], x[0]))
            hold = [t for t, _v in cand[:n_sel]] if on else []
        else:
            hold = ["<IDX>"] if on else []
        # 비용 — 실거래(편도 cost × 거래 비율)
        c = 0.0
        if on:
            if not was_on:
                c = cost                                    # 전량 매수
            elif select and prev_hold:
                c = (len(set(hold) - set(prev_hold)) / max(1, len(hold))) * 2 * cost
        elif was_on:
            c = cost                                        # 전량 매도
        nav0 = nav * (1 - c)
        # 일간 경로 i0→i1
        if not daily_d:
            daily_d.append(dts[i0]); daily_v.append(nav0)
        if on and select:
            p0 = {t: px[t][i0] for t in hold}
            cur = dict(p0)
            for d in range(i0 + 1, i1 + 1):
                s = 0.0
                for t in hold:
                    v = px[t][d]
                    if v:
                        cur[t] = v
                    s += cur[t] / p0[t]
                daily_d.append(dts[d]); daily_v.append(nav0 * s / len(hold))
        elif on:
            b = bench[hold_key]
            last_b = b[i0]
            for d in range(i0 + 1, i1 + 1):
                if b[d] is not None:                     # 결측일 carry — 상류 null 방어(2026-08-20)
                    last_b = b[d]
                daily_d.append(dts[d]); daily_v.append(nav0 * last_b / b[i0])
        else:
            cr = cash_rate if (cash_rate and (cash_from is None or dts[i0] >= cash_from)) else 0.0
            for j, d in enumerate(range(i0 + 1, i1 + 1), 1):
                daily_d.append(dts[d]); daily_v.append(nav0 * (1 + cr / 252) ** j)
        new_nav = daily_v[-1]
        wk_ret.append(new_nav / nav - 1)
        wk_on.append(1 if on else 0)
        wk_d.append(dts[i0])
        ew_univ.append(sum(px[t][i1] / px[t][i0] - 1 for t in univ) / len(univ))
        nav = new_nav
        was_on, prev_hold = on, (hold if select else None)
    out = {"daily_d": daily_d, "daily_v": daily_v, "wk_ret": wk_ret,
           "wk_on": wk_on, "wk_d": wk_d, "ew_univ": ew_univ, "skipped": skipped}
    if want_detail:
        out["last_hold"] = hold
        out["last_on"] = on
    return out


def metrics(daily_d, daily_v, wk_ret):
    yrs = (dt.date.fromisoformat(daily_d[-1]) - dt.date.fromisoformat(daily_d[0])).days / 365.25
    cagr = (daily_v[-1] / daily_v[0]) ** (1 / yrs) - 1
    m = sum(wk_ret) / len(wk_ret)
    sd = math.sqrt(sum((x - m) ** 2 for x in wk_ret) / (len(wk_ret) - 1))
    sharpe = m / sd * math.sqrt(52) if sd > 0 else None
    vol = sd * math.sqrt(52)
    peak, mdd = daily_v[0], 0.0
    for v in daily_v:
        if v > peak:
            peak = v
        dd = v / peak - 1
        if dd < mdd:
            mdd = dd
    return {"cagr": round(cagr * 100, 2), "vol": round(vol * 100, 2),
            "sharpe": (None if sharpe is None else round(sharpe, 2)),
            "mdd": round(mdd * 100, 2)}


def bench_track(dts, bench, key, daily_d, we):
    d2i = {d: i for i, d in enumerate(dts)}
    i_first, i_last = d2i[daily_d[0]], d2i[daily_d[-1]]
    b = bench[key]
    dd = [dts[i] for i in range(i_first, i_last + 1)]
    bf, last = [], None                                   # 전방 채움 — 상류 null 방어(2026-08-20)
    for i in range(i_first, i_last + 1):
        if b[i] is not None:
            last = b[i]
        bf.append(last)
    dv = [100.0 * v / bf[0] for v in bf]
    b = [None] * i_first + bf                             # 주간 계산도 채운 값을 쓴다
    wk = [b[we[k + 1]] / b[we[k]] - 1 for k in range(len(we) - 1)
          if we[k] >= i_first and we[k + 1] <= i_last]
    return dd, dv, wk


def tstat(xs):
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    return m, (m / (sd / math.sqrt(len(xs))) if sd > 0 else None)


def year_table(daily_d, daily_v):
    out, last_by_yr = {}, {}
    for d, v in zip(daily_d, daily_v):
        last_by_yr[d[:4]] = v
    prev = daily_v[0]
    for y in sorted(last_by_yr):
        out[y] = round((last_by_yr[y] / prev - 1) * 100, 1)
        prev = last_by_yr[y]
    return out


def off_periods(wk_d, wk_on):
    out, start = [], None
    for d, on in zip(wk_d, wk_on):
        if not on and start is None:
            start = d
        elif on and start is not None:
            out.append([start, d]); start = None
    if start is not None:
        out.append([start, wk_d[-1] + "~"])
    return out


def main() -> int:
    # 🚨 동결 가드(2026-08-20 점검) — 얼린 사전등록 산출물을 무심코 덮지 못하게 한다.
    #   재동결은 자료 정정 등 사유가 있을 때 --refreeze 로만, 사유는 커밋 메시지·장부에.
    if os.path.exists(OUT) and "--refreeze" not in sys.argv:
        raise SystemExit("%s 가 이미 있다 — 얼린 측정이다. 재동결은 --refreeze 로만." % OUT)
    dts, px, bench = load_px()
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    months = H["months"]
    we = week_ends(dts)
    n = len(dts)
    sig = Sig(px, n)
    bsig = Sig(bench, n)

    runs = {}
    runs["C"] = engine(dts, px, bench, months, we, sig, bsig, want_detail=True)
    runs["A"] = engine(dts, px, bench, months, we, sig, bsig, shield=False)
    runs["B"] = engine(dts, px, bench, months, we, sig, bsig, select=False)
    M = {k: metrics(r["daily_d"], r["daily_v"], r["wk_ret"]) for k, r in runs.items()}

    C = runs["C"]
    bm = {}
    for key in ("spx", "ndx"):
        dd, dv, wk = bench_track(dts, bench, key, C["daily_d"], we)
        bm[key] = metrics(dd, dv, wk)
        bm[key]["cagr_div_adj"] = round(bm[key]["cagr"] + DIV_ADJ[key], 2)
        bm[key]["years"] = year_table(dd, dv)

    mc = M["C"]
    gates = {}
    for key, tag in (("spx", ("U1", "U2", "U3")), ("ndx", ("U4", "U5", "U6"))):
        b = bm[key]
        gates[tag[0]] = {"q": "CAGR>" + key.upper(), "strat": mc["cagr"], "bm": b["cagr"],
                         "bm_div_adj": b["cagr_div_adj"],
                         "pass": bool(mc["cagr"] > b["cagr"]),
                         "pass_div_adj": bool(mc["cagr"] > b["cagr_div_adj"])}
        gates[tag[1]] = {"q": "Sharpe>" + key.upper(), "strat": mc["sharpe"], "bm": b["sharpe"],
                         "pass": bool(mc["sharpe"] > b["sharpe"])}
        gates[tag[2]] = {"q": "MDD<" + key.upper(), "strat": mc["mdd"], "bm": b["mdd"],
                         "pass": bool(abs(mc["mdd"]) < abs(b["mdd"]))}
    n_pass = sum(1 for v in gates.values() if v["pass"])
    n_pass_adj = sum(1 for k, v in gates.items()
                     if v.get("pass_div_adj", v["pass"]))
    verdict = ("통과 (6/6)" if n_pass == 6 else "미달 (%d/6)" % n_pass)

    # 참고 패널 — vs EW 유니버스(같은 배당 기저)
    exs = [r - u for r, u in zip(C["wk_ret"], C["ew_univ"])]
    m5, t5 = tstat(exs)
    half = len(exs) // 2
    h1, h2 = sum(exs[:half]) * 100, sum(exs[half:]) * 100
    srt = sorted(exs)
    top2ex = sum(srt[:-2]) / (len(srt) - 2)
    offs = off_periods(C["wk_d"], C["wk_on"])

    # 민감도(§5 고정)
    sens = {}
    for name, kw in (("N15", {"n_sel": 15}), ("N40", {"n_sel": 40}),
                     ("monthly", {"monthly": True}),
                     ("shield_ndx", {"shield_key": "ndx"}),
                     ("cash4_2022", {"cash_rate": 0.04, "cash_from": "2022-01-01"}),
                     ("cost20", {"cost_bp": 20})):
        r = engine(dts, px, bench, months, we, sig, bsig, **kw)
        sens[name] = metrics(r["daily_d"], r["daily_v"], r["wk_ret"])

    print("이지스 · %s ~ %s · 주 %d회 · 방패 꺼짐 %d주 (%.0f%%) · 건너뜀 %d"
          % (C["daily_d"][0], C["daily_d"][-1], len(C["wk_ret"]),
             len(C["wk_on"]) - sum(C["wk_on"]),
             100 * (1 - sum(C["wk_on"]) / len(C["wk_on"])), C["skipped"]))
    print("%-14s %8s %8s %8s %8s" % ("", "CAGR%", "Vol%", "Sharpe", "MDD%"))
    for k, lab in (("A", "A 선택만"), ("B", "B 방패만"), ("C", "C 이지스")):
        mm = M[k]
        print("%-14s %8.2f %8.2f %8.2f %8.2f" % (lab, mm["cagr"], mm["vol"], mm["sharpe"], mm["mdd"]))
    for key in ("spx", "ndx"):
        b = bm[key]
        print("%-14s %8.2f %8.2f %8.2f %8.2f  (배당보정 CAGR %.2f)"
              % ("BM " + key.upper(), b["cagr"], b["vol"], b["sharpe"], b["mdd"], b["cagr_div_adj"]))
    for k, v in gates.items():
        extra = "" if "pass_div_adj" not in v else (" · 배당보정 %s" % ("✅" if v["pass_div_adj"] else "❌"))
        print("  %s %-12s %s  전략 %s vs BM %s%s" % (k, v["q"], "✅" if v["pass"] else "❌",
                                                     v["strat"], v["bm"], extra))
    print("판정: %s (배당보정 %d/6)" % (verdict, n_pass_adj))
    print("참고 — vs EW유니버스: 주평균 %+.3f%%p · t %.2f · 반분 [%+.1f, %+.1f] · 상위2제외 %+.4f%%p"
          % (m5 * 100, t5, h1, h2, top2ex * 100))
    print("방패 꺼짐 구간:", offs)
    print("민감도:")
    for k, v in sens.items():
        print("  %-12s CAGR %6.2f · Sharpe %5.2f · MDD %6.2f" % (k, v["cagr"], v["sharpe"], v["mdd"]))

    doc = {
        "note": "이지스 — dist200 상위 25 EW(선택) × ^GSPC 200일선 레짐(방패·Faber 2007). "
                "판정은 사용자 6문(vs SPX·NDX 수익·샤프·MDD) — PREREG-2026-08-19-AEGIS.md 에 "
                "계산 전 커밋. 배당 기저·현금 0%·체결 규약의 정직성 항목은 §0.",
        "prereg": "build/PREREG-2026-08-19-AEGIS.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"n_sel": N_SEL, "ma_td": MA_TD, "cost_bp": COST_BP, "start": START},
        "span": [C["daily_d"][0], C["daily_d"][-1]], "weeks": len(C["wk_ret"]),
        "off_weeks": len(C["wk_on"]) - sum(C["wk_on"]),
        "decomp": {k: M[k] for k in ("A", "B", "C")},
        "bench": bm, "gates": gates, "n_pass": n_pass, "n_pass_div_adj": n_pass_adj,
        "verdict": verdict,
        "ref_panel": {"weekly_ex_bp_vs_ewuniv": round(m5 * 10000, 1),
                      "t": round(t5, 2), "halves_pp": [round(h1, 2), round(h2, 2)],
                      "top2ex_weekly_bp": round(top2ex * 10000, 1)},
        "years": {"aegis": year_table(C["daily_d"], C["daily_v"]),
                  "spx": bm["spx"]["years"], "ndx": bm["ndx"]["years"]},
        "shield_off_periods": offs, "sens": sens,
        "last_week": {"date": C["wk_d"][-1], "on": bool(C["last_on"]),
                      "hold": C.get("last_hold") or []},
        "weekly": {"d": C["wk_d"], "ret": [round(x, 6) for x in C["wk_ret"]],
                   "on": C["wk_on"]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
