# -*- coding: utf-8 -*-
"""build/guru_overlap_backtest.py — 겹침 포트폴리오 → data/guru_overlap.json

무엇을. guru.html#overlap 이 보여 주는 '몇 곳이 같이 들고 있나'를 **규칙으로 바꿔** 돌린다.
분기마다 명단 운용사 중 K곳 이상이 들고 있는 종목을 동일가중으로 담고 다음 분기까지 둔다.
유니버스는 이 랩의 518종목(S&P 500 ∪ NASDAQ 100)이므로 '지수 편입 종목만'은 자동으로 지켜진다.

왜 별도 스크립트인가. guru17_backtest.py 는 **운용사 하나하나**를 복제해 알파가 있는지 묻는다.
여기서 묻는 것은 다른 질문이다 — 개별 운용사가 아니라 '여러 명이 겹쳐 든 것'이라는 신호가
따로 값을 하는가. 그래서 규칙도 대조군도 다르다. 지표 계산만 그쪽에서 그대로 가져다 쓴다
(같은 자를 써야 두 화면의 숫자를 나란히 놓을 수 있다).

규칙 — 전부 그 시점에 알 수 있던 것만 쓴다.
  선정   분기말 13F 기준, K곳 이상이 보유(수량>0)한 유니버스 종목
  룩어헤드 공시일(13F filed)이 체결일보다 뒤인 운용사는 그 분기 세지 않는다
  체결   분기말 + 2개월의 월말 (3/31→5/31 · 6/30→8/31 · 9/30→11/30 · 12/31→2/28)
  비중   동일가중. 리밸런스 사이는 표류(매수후보유)
  대조군 ① 같은 풀 동일가중(월 리밸) — '풀이 좋았을 뿐'인지 가른다
         ② SPY 총수익 — 실제로 대신 살 수 있었던 것

한계 — 이 스크립트가 상쇄하지 못하는 것.
  · 명단 17곳이 사후 선택이다. 2026년 시점의 유명세로 고른 곳들이고 폐업·청산은 0곳이다.
  · 유니버스와 CUSIP→티커 매핑이 오늘 스냅샷이다. 과거 보유 중 '지금 살아남아 대형주인 것'만
    남으므로 방향은 위쪽이다. 대조군 ①을 같은 풀로 두어 일부만 상쇄한다.
  · K를 2~5로 훑는다. 넷을 보고 하나를 고르면 그건 사후 선택이므로, 넷을 **전부** 싣고
    다중검정 보정을 함께 적는다. K=2 가 사용자가 요청한 기본값이라는 사실도 그대로 적는다.
  · 거래비용·세금 0. 분기 리밸런스 회전율을 함께 실어 그 크기를 가늠할 수 있게 한다.

  python build/guru_overlap_backtest.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 지표·회귀는 진단 페이지와 **같은 자**를 쓴다. 여기서 다시 구현하면 두 화면의 CAGR·샤프가
# 미묘하게 갈리고, 그때 어느 쪽이 맞는지 아무도 모른다.
from guru17_backtest import (ann_from_monthly, capm, add_months, month_end,
                             load, LAG_MONTHS, holm_bh)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru_overlap.json")

KS = [2, 3, 4, 5]        # 훑는 문턱. 요청값은 2이고 나머지는 민감도다
MIN_HOLD = 5             # 이보다 적게 뽑히는 분기는 '동일가중 포트폴리오'라 부르기 어렵다
MIN_MONTHS = 60          # 성과를 낼 최소 개월(5년)


def spy_monthly(months):
    """assets.json 조정종가에서 월말 SPY 총수익 월수익률. 조정종가라 배당이 이미 들어 있다."""
    a = load("assets.json") or {}
    dates, px = a.get("dates") or [], (a.get("px") or {}).get("SPY") or []
    last = {}
    for d, p in zip(dates, px):
        if p is not None:
            last[d[:7]] = p                     # 그 달의 마지막 거래일 값이 남는다
    out = {}
    for i in range(1, len(months)):
        p0, p1 = last.get(months[i - 1]), last.get(months[i])
        if p0 and p1 and p0 > 0:
            out[months[i]] = p1 / p0 - 1.0
    return out


def counts_by_quarter(G, mi, P, months):
    """분기 → {티커: 보유 운용사 수}. 룩어헤드를 통과한 운용사만 센다.

    비중이 아니라 **머릿수**다. 겹침은 '몇 명이 들고 있나'이지 '얼마나 크게 들고 있나'가
    아니다 — 후자를 쓰면 큰 운용사 하나가 둘 몫을 하게 되어 규칙이 다른 것이 된다.
    """
    H, FILED = G["holdings"], G.get("filed") or {}
    out, diag = {}, []
    for q in sorted(H):
        qm = q[:7]
        rm = add_months(qm, LAG_MONTHS)
        if rm not in mi or qm not in mi:
            continue
        i_r = mi[rm]
        cnt, used, skipped = {}, 0, 0
        for cik, raw in H[q].items():
            fd = (FILED.get(q) or {}).get(cik)
            if fd and fd > month_end(rm):
                skipped += 1                    # 그때는 아직 공시 전이다
                continue
            used += 1
            for t, v in raw.items():
                if not v or v <= 0:
                    continue
                # 체결월 가격이 없으면 살 수 없다 — 셈에서도 뺀다(살 수 없는 것을 세면 분모가 거짓말한다)
                if P.get(t, [None] * len(months))[i_r] is None:
                    continue
                cnt[t] = cnt.get(t, 0) + 1
        out[rm] = cnt
        diag.append({"q": q, "rebal": rm, "managers": used, "lookahead_skipped": skipped,
                     "n_ge2": sum(1 for c in cnt.values() if c >= 2)})
    return out, diag


def build_weights(counts, k, P, mi, months):
    """K곳 이상 종목을 동일가중으로. 리밸런스 사이는 표류. 반환 (월별비중, 회전율, 종목수, 최근편입)."""
    plan = {m: sorted(t for t, c in cnt.items() if c >= k) for m, cnt in counts.items()}
    plan = {m: ts for m, ts in plan.items() if len(ts) >= MIN_HOLD}
    if not plan:
        return {}, [], [], None
    W, cur, turn, nhold = {}, None, [], []
    start = mi[min(plan)]
    for i in range(start, len(months)):
        m = months[i]
        if m in plan:
            new = {t: 1.0 / len(plan[m]) for t in plan[m]}
            if cur:
                # 회전율 = 편도. 표류한 비중에서 새 비중으로 옮기는 데 든 거래량이다.
                keys = set(cur) | set(new)
                turn.append({"m": m, "v": round(sum(abs(new.get(t, 0) - cur.get(t, 0))
                                                    for t in keys) / 2 * 100, 1)})
            cur = new
            nhold.append({"m": m, "n": len(new)})
        elif cur is not None:
            nxt, tot = {}, 0.0
            for t, x in cur.items():
                p0, p1 = P.get(t, [None] * len(months))[i - 1], P.get(t, [None] * len(months))[i]
                if p0 is None or p1 is None or p0 <= 0:
                    continue
                v = x * (p1 / p0)
                nxt[t] = v; tot += v
            cur = {t: v / tot for t, v in nxt.items()} if tot > 0 else cur
        if cur:
            W[m] = dict(cur)
    # 지금 이 규칙을 따르면 무엇을 사는가. 전략이라면 이게 없으면 안 된다 —
    # 성과만 있고 명단이 없으면 읽는 사람이 확인할 방법이 없다.
    lm = max(plan)
    last = {"rebal": lm, "n": len(plan[lm]),
            "tickers": sorted(plan[lm], key=lambda t: (-counts[lm].get(t, 0), t)),
            "counts": {t: counts[lm].get(t, 0) for t in plan[lm]}}
    return W, turn, nhold, last


def monthly_returns(W, P, mi, months):
    """비중 시계열 → 월 수익률. 비중은 그 달 말에 정해지고 다음 달 수익을 받는다."""
    out = {}
    for m, w in W.items():
        i = mi[m]
        if i + 1 >= len(months):
            continue
        num, den = 0.0, 0.0
        for t, x in w.items():
            p0, p1 = P.get(t, [None] * len(months))[i], P.get(t, [None] * len(months))[i + 1]
            if p0 is None or p1 is None or p0 <= 0:
                continue
            num += x * (p1 / p0 - 1.0); den += x
        if den > 0.5:
            out[months[i + 1]] = num / den
    return out


def main() -> int:
    G = load("guru_history.json")
    RF = (load("rf_monthly.json") or {}).get("monthly") or {}
    months, P = G["months"], G["mpx"]
    now_m = dt.date.today().strftime("%Y-%m")
    while months and months[-1] >= now_m:            # 진행 중인 달은 버린다
        months = months[:-1]
    P = {t: v[:len(months)] for t, v in P.items()}
    mi = {m: i for i, m in enumerate(months)}

    # 대조군 ① 같은 풀 동일가중(월 리밸)
    pool = {}
    for i in range(1, len(months)):
        rs = [P[t][i] / P[t][i - 1] - 1.0 for t in P
              if P[t][i] is not None and P[t][i - 1] not in (None, 0)]
        if rs:
            pool[months[i]] = float(np.mean(rs))
    spy = spy_monthly(months)                         # 대조군 ②

    counts, qdiag = counts_by_quarter(G, mi, P, months)
    print("분기 %d개 · 첫 체결 %s" % (len(counts), min(counts) if counts else "-"))

    variants, pvals = [], []
    for k in KS:
        W, turn, nhold, last = build_weights(counts, k, P, mi, months)
        rets = monthly_returns(W, P, mi, months)
        if len(rets) < MIN_MONTHS:
            variants.append({"k": k, "n_months": len(rets), "verdict": "표본 부족"})
            pvals.append(None)
            continue
        ms = sorted(rets)
        r = np.array([rets[m] for m in ms])
        rf = np.array([RF.get(m, 0.0) for m in ms])
        row = {"k": k, "start": ms[0], "end": ms[-1], "n_months": len(ms),
               "metrics": ann_from_monthly(r, rf),
               "holds": {"min": min(x["n"] for x in nhold), "max": max(x["n"] for x in nhold),
                         "last": nhold[-1]["n"], "series": nhold},
               "turnover": {"mean": round(float(np.mean([x["v"] for x in turn])), 1) if turn else None,
                            "series": turn},
               "latest": last}
        for name, bs in (("pool", pool), ("spy", spy)):
            b = np.array([bs.get(m, 0.0) for m in ms])
            a, beta, t, _ = capm(r, b, rf)
            row[name] = {"metrics": ann_from_monthly(b, rf),
                         "alpha": a, "beta": beta, "t": t}
        variants.append(row)
        pvals.append(None)
        print("  K=%d  %d개월 · CAGR %6.2f%% (풀 %5.2f · SPY %5.2f) · 샤프 %.2f (%.2f · %.2f) "
              "· MDD %6.2f%% · 종목 %d~%d · 회전 %.0f%%"
              % (k, len(ms), row["metrics"]["cagr"], row["pool"]["metrics"]["cagr"],
                 row["spy"]["metrics"]["cagr"], row["metrics"]["sharpe"],
                 row["pool"]["metrics"]["sharpe"], row["spy"]["metrics"]["sharpe"],
                 row["metrics"]["mdd"], row["holds"]["min"], row["holds"]["max"],
                 row["turnover"]["mean"] or 0))
        print("        알파 vs 풀 %+.2f%%/yr (t %+.2f · β %.2f) · vs SPY %+.2f%%/yr (t %+.2f · β %.2f)"
              % (row["pool"]["alpha"] or 0, row["pool"]["t"] or 0, row["pool"]["beta"] or 0,
                 row["spy"]["alpha"] or 0, row["spy"]["t"] or 0, row["spy"]["beta"] or 0))

    # 다중검정 — K를 4개 훑었다. 하나만 보고 고르면 그것이 사후 선택이다.
    from scipy import stats
    pv = []
    for v in variants:
        t, n = (v.get("spy") or {}).get("t"), v.get("n_months")
        pv.append(None if t is None or not n else float(2 * (1 - stats.t.cdf(abs(t), n - 2))))
    for v, p in zip(variants, pv):
        if p is not None:
            v["p_spy"] = round(p, 4)
    mult = holm_bh(pv)

    doc = {
        "note": "겹침 포트폴리오 — 명단 운용사 중 K곳 이상이 들고 있는 유니버스 종목을 "
                "동일가중으로 담고 분기마다 다시 고른다. **요청값은 K=2**이고 3~5는 민감도다. "
                "이 랩의 유니버스가 S&P 500 ∪ NASDAQ 100 이므로 '지수 편입 종목만'은 규칙에 내장돼 있다.",
        "spec": {
            "select": "분기말 13F에서 K곳 이상이 보유(수량>0)한 유니버스 종목",
            "lookahead_guard": "공시일(13F filed)이 체결일보다 뒤인 운용사는 그 분기 세지 않는다",
            "rebalance": "분기말 + 2개월의 월말 (3/31→5/31 · 6/30→8/31 · 9/30→11/30 · 12/31→2/28)",
            "weights": "동일가중. 리밸런스 사이는 표류(매수후보유)",
            "bench_pool": "같은 풀(유니버스) 동일가중 · 월 리밸 — 풀이 좋았을 뿐인지 가른다",
            "bench_spy": "SPY 총수익(조정종가) — 실제로 대신 살 수 있었던 것",
            "rf": "FRED DGS3MO 월율, 샤프·알파는 초과수익 기준",
            "costs": "거래비용·세금 0. 회전율을 함께 실어 크기를 가늠하게 한다",
        },
        "limits": [
            "명단 17곳이 **사후 선택**이다 — 2026년 시점의 유명세로 고른 곳들이고 13년 구간에서 "
            "폐업·청산이 0곳이다. 어떤 대조군도 이 편향을 상쇄하지 못한다.",
            "유니버스(518종목)와 CUSIP→티커 매핑이 모두 **오늘 스냅샷**이다. 과거 보유 중 "
            "'지금 대형주로 살아남은 것'만 남으므로 방향은 위쪽이다. 대조군을 같은 풀 "
            "동일가중으로 두어 일부만 상쇄한다.",
            "13F는 롱온리 미국 상장주식만 담는다. 숏·현금·해외가 빠져 있어 '이 사람들이 "
            "겹쳐 든 것'이지 '이 사람들의 공통 견해'가 아니다.",
            "K를 4개 훑었다 — 넷 중 제일 좋은 것을 고르면 그것이 사후 선택이다. 넷을 전부 싣고 "
            "다중검정 보정을 함께 적는다.",
            "거래비용이 0이다. 분기 리밸런스 회전율이 붙으므로 실제 수익은 이보다 낮다.",
        ],
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "span": {"start": months[0], "end": months[-1]},
        "ks": KS, "k_requested": 2,
        "quarters": qdiag,
        "multiplicity": mult,
        "variants": variants,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s (%dKB)" % (OUT, os.path.getsize(OUT) // 1024))
    print("다중검정 m=%d · Bonferroni %d · Holm %d · BH(q=.10) %d"
          % (mult["m"], mult["bonferroni"], mult["holm"], mult["bh10"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
