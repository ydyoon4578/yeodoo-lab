# -*- coding: utf-8 -*-
"""build/style_fmom.py — 스타일 로테이션(팩터 모멘텀). 규약은 PREREG-2026-09-21-STYLE8ROT.md.

🚨 등록서에 적은 것만 한다. 결과를 보고 자산 수(8/8)·선택 크기(상위 절반)·
   신호(12-1)·주기(월말)·창(계산값)을 바꾸지 않는다. 16종판·9종판·7종판은 만들지 않는다.
🚨 자산 선정을 **네 번 고쳤다**(등록서 §3-1-a). 최종은 «표준 8종» 이고
   기준은 성적이 아니라 **표준 팩터 분류**다. 그래도 나는 성적표를 이미 봤다 —
   그래서 fmom8 > fmom 을 «축을 다양화하면 좋아진다» 의 증거로 쓰지 않는다.
   두 판 다 **8종**이라, 바뀐 것은 개수가 아니라 **축의 다양성** 하나다.

🚨 레그를 여기서 다시 굽는다(등록서 §3-2-a). data/style_pit.json 의 레그는 1년짜리라
   (n_rebal 11) 12-1 신호를 얹으면 시험할 달이 0개다. ST.WINDOW 를 늘리고
   **패널도 같은 인자로** 준비한다 — 짧은 패널에 긴 창을 돌리면 앞쪽이 조용히
   생존자가 된다(style_pit.py §259 가 적어 둔 사고).
🚨 창 길이는 leg_days() 가 **계산한다**(등록서 §3-2-a 재개정). 10년이 상한이지만
   멤버십이 2014-06 부터라 가드(3년) 때문에 10년에 못 미친다. 그 값을 손대지 않는다.

⚠ data/style_pit.json 을 덮어쓰지 않는다. 게시 산출물이다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_style_fmom.json")
HERE = os.path.join(ROOT, "build")
sys.path.insert(0, HERE)
from maxyears import MAX_YEARS, check_const, cap                  # noqa: E402

# ── 등록서 §3 의 상수 ──────────────────────────────────────────────────────
LB_A, LB_B = 12, 2          # 점수 구간 t-12 ~ t-2 (직전 1개월 건너뜀)
COST = 0.0020               # 왕복 20bp — STYLE8W F4 와 같은 값
NSHUF, SEED = 200, 20260921
GUARD_Y = 3                 # style_pit_panel.prepare §124 — 창 시작보다 3년 앞까지 멤버십 요구


def leg_days(P, mem):
    """§3-2-a 재개정 — 창 길이를 **계산한다.** 손으로 고르지 않는다.

    허용 시작 = (멤버십 첫 달의 첫 거래일) + 252*3
    LEG_DAYS  = min(MAX_YEARS*252,  마지막날 − 허용 시작)
    """
    m0 = min(mem.keys())
    i0 = next(i for i, d in enumerate(P.dates) if d[:7] >= m0)
    lo = i0 + 252 * GUARD_Y
    end = len(P.dates) - 1
    n = min(MAX_YEARS * 252, end - lo)
    print("멤버십 시작 %s · 가드 %d년 → 허용 시작 %s · 창 %d거래일(%.1f년)"
          % (m0, GUARD_Y, P.dates[lo], n, n / 252.0))
    return n

EIGHT = ["val", "grow", "hbeta", "div", "spmo", "qvm", "squal", "size"]
# 표준 8종 — MSCI 6대(val·size·spmo·squal·lowvol·div) + 수익성(fcfy 대용)
#            + 투자/순발행(netbuy 대용). 등록서 §3-1-b · §3-1-b-2.
STD8 = ["val", "size", "spmo", "squal", "div", "lowvol", "fcfy", "netbuy"]


def bench_m():
    """F5 용 벤치(S&P 500) 월수익. data/bench_px.json 의 spx 계열.

    ⚠ 이 계열은 **가격지수(PR)** 다 — 배당 재투자가 없다. 그만큼 벤치가 낮게 잡힌다.
      F5 를 통과해도 «배당까지 포함한 벤치를 넘었다» 는 뜻이 아니다. 결과문서에 적는다.
    """
    b = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    s = pd.Series(b["series"]["spx"]["px"], index=pd.to_datetime(b["dates"]), dtype="float64")
    s = s.dropna()
    return s.resample("ME").last().pct_change().dropna()


def eff_n(C):
    """상관행렬의 유효 자산 수 — 고유값 참여비."""
    ev = np.linalg.eigvalsh(np.asarray(C, float))[::-1]
    ev = ev[ev > 1e-12]
    return float(ev.sum() ** 2 / (ev ** 2).sum())


def monthly(nav, dates):
    """일별 nav + 날짜 → 월말 수익 Series. 부분 첫 달은 버린다."""
    s = pd.Series(np.asarray(nav, float), index=pd.to_datetime(list(dates)))
    m = s.resample("ME").last().dropna()
    return m.pct_change().dropna()


def build_legs():
    """PIT 레그의 월별 수익. §3-2-a 의 창·패널로."""
    import index_members
    import style_top_pdf as ST
    import style_pit_panel as SPP
    mem, _ = index_members.load()
    P0 = ST.Panel()
    LEG_DAYS = leg_days(P0, mem)
    ST.WINDOW = LEG_DAYS                       # §3-2-a — 창을 계산된 값으로
    prep = SPP.prepare(ST, P=P0, window=LEG_DAYS)   # 🚨 패널도 **같은 인자**
    P = prep["P"]
    SPP.inject(prep)                           # 편출 종목 주입 — 이것이 PIT 의 뜻
    members_at = prep["members_at"]
    inject, missing = prep["inject"], prep.get("missing") or []
    print("주입 %d종 · 가격 부재 %d종" % (len(inject), len(missing)))

    out, failed = {}, {}
    for st in ST.STYLES:
        key, label, fn = st[0], st[1], st[3]
        R = ST.backtest(P, fn, pool_of=members_at)
        if not R:
            failed[key] = label
            print("  ⚠ %-10s %s — 레그 실패(후보가 문턱에 못 닿음)" % (key, label))
            continue
        nav = R["nav"]
        d = P.dates[len(P.dates) - len(nav):]
        r = monthly(nav, d)
        out[key] = r
        print("  %-10s %-14s %3d개월 (%s ~ %s) 리밸 %d"
              % (key, label, len(r), r.index[0].strftime("%Y-%m"),
                 r.index[-1].strftime("%Y-%m"), R["n_rebal"]))
    return out, failed, len(inject), len(missing), LEG_DAYS


def fmom(X, names):
    """§3-2·3-3 — 12-1 위험조정 점수 상위 절반 동일가중, 월말 형성·1개월 보유."""
    X = X[names].dropna()
    idx = X.index
    k = max(1, len(names) // 2)
    rows, held, prev, scores = [], [], set(), []
    for i in range(LB_A, len(idx) - 1):
        win = X.iloc[i - LB_A:i - LB_B + 1]          # t-12 ~ t-2
        sd = win.std().replace(0, np.nan)
        sc = (((1 + win).prod() - 1) / sd).dropna()
        if len(sc) < k:
            continue
        pick = list(sc.sort_values(ascending=False).index[:k])
        nxt = X.iloc[i + 1]                           # 다음 달 수익
        gross = float(np.mean([nxt[t] for t in pick]))
        churn = len(set(pick) ^ prev) / (2.0 * k) if prev else 1.0
        rows.append((idx[i + 1], gross, gross - COST * churn, churn))
        held.append(pick)
        scores.append(sc.reindex(names))
        prev = set(pick)
    R = pd.DataFrame(rows, columns=["m", "gross", "net", "churn"]).set_index("m")
    S = pd.DataFrame(scores, index=R.index)      # §4-5 신호의 지속성
    return R, held, S


def stats(r):
    n = len(r)
    if n < 2:
        return {}
    ann = float((1 + r).prod() ** (12.0 / n) - 1)
    vol = float(r.std() * np.sqrt(12))
    nav = (1 + r).cumprod()
    return {"n": n, "ann": ann * 100, "vol": vol * 100,
            "sharpe": (ann / vol) if vol else None,
            "mdd": float((nav / nav.cummax() - 1).min() * 100)}


def tstat(d):
    d = np.asarray(d, float)
    return float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))) if len(d) > 1 else None


def main():
    check_const()
    legs, failed, n_inj, n_miss, leg_d = build_legs()
    X = pd.DataFrame(legs).dropna()
    X = X.loc[cap(X.index)]                     # 🚨 10년 상한
    print("\n공통 %d개월 (%s ~ %s) · 레그 %d종"
          % (len(X), X.index[0].strftime("%Y-%m"),
             X.index[-1].strftime("%Y-%m"), X.shape[1]))

    res = {"max_years": MAX_YEARS, "leg_days": leg_d, "leg_years": leg_d / 252.0, "cost_bp": COST * 1e4,
           "n_inject": n_inj, "n_missing_px": n_miss, "failed_legs": failed,
           "window": [X.index[0].strftime("%Y-%m"), X.index[-1].strftime("%Y-%m")],
           "n_month": len(X), "runs": {}}

    BM = bench_m()
    rng = np.random.default_rng(SEED)
    for tag, want in (("fmom", EIGHT), ("fmom8", STD8)):
        names = [n for n in want if n in X.columns]
        sub = X[names]
        en = eff_n(sub.corr())
        R, held, S = fmom(X, names)
        ew = sub.loc[R.index].mean(axis=1)
        d = R["net"] - ew
        k = max(1, len(names) // 2)
        sh = []
        for _ in range(NSHUF):
            pr = [float(sub.loc[t, list(rng.choice(names, size=k, replace=False))].mean())
                  for t in R.index]
            sh.append(float((1 + pd.Series(pr)).prod() ** (12.0 / len(pr)) - 1) * 100)
        a_net = stats(R["net"])["ann"]
        pct = float((np.asarray(sh) < a_net).mean() * 100)
        half = len(d) // 2
        ac = float(np.mean([S[c].autocorr() for c in S.columns]))
        # 명단 지속성 — 다음 달에도 남아 있는 비율
        keep = float(np.mean([len(set(a) & set(b)) / len(a)
                              for a, b in zip(held[:-1], held[1:])])) * 100
        bm = BM.reindex(R.index).dropna()
        b_st = stats(bm)
        res["runs"][tag] = {
            "names": names, "eff_n": en,
            "gross": stats(R["gross"]), "net": stats(R["net"]), "ew": stats(ew),
            "excess_ann": a_net - stats(ew)["ann"],
            "excess_gross_ann": stats(R["gross"])["ann"] - stats(ew)["ann"],
            "t_excess": tstat(d),
            "churn_m": float(R["churn"].mean() * 100),
            "shuffle_pct": pct, "shuffle_mean": float(np.mean(sh)),
            "half1_excess": float(d.iloc[:half].mean() * 1200),
            "half2_excess": float(d.iloc[half:].mean() * 1200),
            "score_ac": ac, "keep_pct": keep,
            "bench": b_st, "bench_n": len(bm),
            "f5_beat_bench": bool(stats(R["net"])["sharpe"] > (b_st.get("sharpe") or 9e9)),
        }
        r = res["runs"][tag]
        print("\n== %s · %d종 · 유효 %.2f ==============================" % (tag, len(names), en))
        print("   비용후 연 %6.2f%% (샤프 %5.2f) · ew 연 %6.2f%% (샤프 %5.2f)"
              % (r["net"]["ann"], r["net"]["sharpe"], r["ew"]["ann"], r["ew"]["sharpe"]))
        print("   초과 %+.2f%%p · t %.2f · 비용전 초과 %+.2f%%p"
              % (r["excess_ann"], r["t_excess"] or 0, r["excess_gross_ann"]))
        print("   월회전 %.1f%% · 셔플백분위 %.1f (무작위 평균 연 %.2f%%)"
              % (r["churn_m"], r["shuffle_pct"], r["shuffle_mean"]))
        print("   앞절반 초과 %+.2f%%p · 뒤절반 %+.2f%%p"
              % (r["half1_excess"], r["half2_excess"]))
        print("   점수 자기상관 %.2f · 명단 유지 %.1f%%" % (r["score_ac"], r["keep_pct"]))
        print("   벤치 S&P500 연 %6.2f%% (샤프 %5.2f, %d개월) → F5 %s"
              % (r["bench"]["ann"], r["bench"]["sharpe"], r["bench_n"],
                 "통과" if r["f5_beat_bench"] else "❌ 걸림"))

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
