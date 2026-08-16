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
import io, json, os, re, sys

import math
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
TOPN = 10                # 좁힌 판의 종목 수(요청)
SH_COVER = 0.80          # 시총 순위를 매기려면 그 분기 후보의 이 비율 이상에 주식수가 있어야 한다


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


def load_shares():
    """티커 → [(기간종료일, 백만주)…] 오름차순. 랩이 SEC XBRL 로 이미 갖고 있는 것을 쓴다.

    ⚠ 이 시계열은 종목당 20관측(약 5년)뿐이다 — 496종 중 331종이 2019년, 132종이 2020년에
      시작한다. **2019-11 이전에는 커버가 0%다.** 그래서 시총 순위로 좁힌 판은 13년을 못 돌린다.
      없는 것을 오늘 주식수로 메우면 그건 PIT 가 아니라 '오늘의 승자를 과거에 심는 것'이다.
    """
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tech_backtest.py")
    spec = importlib.util.spec_from_file_location("_tb", p)
    tb = importlib.util.module_from_spec(spec); spec.loader.exec_module(tb)
    return {t: sorted(v["sh"]) for t, v in tb.load_fund().items() if v.get("sh")}


def issuer_map():
    """티커 → 발행사 키. 같은 회사의 다른 클래스를 한 몸으로 묶는다.

    왜 필요한가 — 10종목만 담는데 GOOGL·GOOG 가 둘 다 들어오면 알파벳 한 회사가 20%다.
    분산이 아니라 착시다. 이름에서 클래스 꼬리(-CL A · - CLASS B · -A)를 떼어 묶는다.
    유니버스 518종목에서 걸리는 것은 셋뿐이다 — 알파벳·폭스·뉴스코프(2026-07-28 실측).
    ⚠ 시총으로 순위를 매길 때도 이게 필요하다. SEC XBRL 의 주식수는 클래스별이 아니라
      **회사 전체**라, 두 클래스가 같은 시총으로 잡혀 나란히 상위에 올라온다.
    """
    st = load("stocks.json") or {}
    out = {}
    for s in (st.get("stocks") or []):
        n = (s.get("n") or s.get("name") or "").upper().strip()
        if not n:
            out[s["t"]] = s["t"]
            continue
        n = re.sub(r"\s*-\s*(CL|CLASS|SER|SERIES)\s+[A-Z0-9]+$", "", n)
        n = re.sub(r"\s*-\s*[A-Z]$", "", n)
        out[s["t"]] = re.sub(r"[^A-Z0-9]", "", n) or s["t"]
    return out


def pick_top(ranked, n, ISS):
    """순위 목록에서 발행사가 겹치지 않게 위에서부터 n개. 반환 (고른 것, 밀려난 것)."""
    keep, seen, dropped = [], set(), []
    for t in ranked:
        k = ISS.get(t, t)
        if k in seen:
            dropped.append(t)          # 같은 회사의 다른 클래스 — 자리를 아래로 넘긴다
            continue
        seen.add(k); keep.append(t)
        if len(keep) >= n:
            break
    return keep, dropped


def mcap_at(t, m, SH, P, mi, months):
    """그 시점 시가총액(백만$) = 그 달 말까지 공시된 최신 주식수 × 그 달 종가. 없으면 None."""
    end = month_end(m)
    sh = None
    for d, v in SH.get(t, []):            # 오름차순 — 마지막으로 통과한 값이 그 시점 최신이다
        if d <= end:
            sh = v
        else:
            break
    px = P.get(t, [None] * len(months))[mi[m]]
    return None if (sh is None or px is None) else sh * px


def build_topn(counts, k, n, rank, SH, P, mi, months, ISS):
    """K곳 이상 중 상위 n종목만 동일가중. rank='mc'(시점 시총) 또는 'ov'(겹친 운용사 수).

    'ov' 를 함께 두는 이유 — 시총 순위는 주식수가 있는 구간(2020~)에서만 매길 수 있다.
    겹침 수는 13F 만으로 매겨지므로 13년 전체를 돌 수 있다. 같은 '상위 10종목' 규칙을
    두 잣대로 재 두면, 짧은 구간의 결과가 규칙 탓인지 구간 탓인지 가늠할 수 있다.
    """
    plan, skipped, dropped = {}, 0, {}
    for m, cnt in counts.items():
        sel = [t for t, c in cnt.items() if c >= k]
        if len(sel) < n:
            continue
        if rank == "mc":
            mc = {t: mcap_at(t, m, SH, P, mi, months) for t in sel}
            have = [t for t in sel if mc[t] is not None]
            if len(have) < max(n, SH_COVER * len(sel)):
                skipped += 1              # 그 시점엔 순위를 매길 수 없다 — 추정으로 메우지 않는다
                continue
            ranked = sorted(have, key=lambda t: -mc[t])
        else:
            ranked = sorted(sel, key=lambda t: (-cnt[t], t))
        # 같은 발행사의 다른 클래스는 하나만 — 밀려난 자리는 다음 순위가 채운다
        keep, drop = pick_top(ranked, n, ISS)
        if len(keep) < n:
            continue                      # 후보가 모자라면 그 분기는 건너뛴다
        plan[m] = keep
        if drop:
            dropped[m] = drop
    if not plan:
        return {}, [], [], None, skipped
    W, cur, turn, nhold = {}, None, [], []
    start = mi[min(plan)]
    for i in range(start, len(months)):
        m = months[i]
        if m in plan:
            new = {t: 1.0 / len(plan[m]) for t in plan[m]}
            if cur:
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
                v = x * (p1 / p0); nxt[t] = v; tot += v
            cur = {t: v / tot for t, v in nxt.items()} if tot > 0 else cur
        if cur:
            W[m] = dict(cur)
    lm = max(plan)
    last = {"rebal": lm, "n": len(plan[lm]), "tickers": plan[lm],
            "counts": {t: counts[lm].get(t, 0) for t in plan[lm]},
            "dropped": dropped.get(lm) or []}
    return W, turn, nhold, last, skipped, dropped


# ── 곡선 (2026-08-16 사용자 요청: "차트랑 해서 더 잘 볼 수 있게") ──────────────
# 🚨 화면이 월별 수익률로 곡선을 다시 만들지 않게 **여기서 굽는다.** 화면이 만들면
#   기준점(100 시작)을 화면이 정하게 되고, 그러면 전략과 대조군이 다른 높이에서
#   출발하는 사고가 난다 — 이 저장소가 2026-08-14 에 그것으로 그림이 승패를 거꾸로
#   말하고 있었다(자산 랩 9종 중 8종).
# ⚠ 세 계열을 **같은 달 목록**으로 만든다. 하나라도 달이 다르면 같은 그림에 못 올린다.
# ⚠ 점이 많으면 파일이 커진다 — 월 격자라 154개월이면 그대로 실어도 작다(얇게 안 만든다).
def curve(ms, series):
    """{이름: {달: 수익률}} → {"m": [...], "s": {이름: [100 기준 지수]}}"""
    out = {}
    for nm, d in series.items():
        v, acc = [], 100.0
        for m in ms:
            acc *= (1.0 + float(d.get(m, 0.0)))
            v.append(round(acc, 2))
        out[nm] = v
    return {"m": list(ms), "s": out}


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
        # 곡선 — 셋을 같은 달 목록으로 굽는다(위 curve() 주석 참조)
        row["curve"] = curve(ms, {"s": rets, "pool": pool, "spy": spy})
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

    # ── 상위 10종목으로 좁힌 판 ──────────────────────────────────────────
    # 요청은 '시총 상위 10'이다. 그런데 시점별 주식수가 2019~2020년부터라 그 규칙은 13년을
    # 못 돈다. 없는 구간을 오늘 주식수로 메우면 오늘의 승자를 과거에 심는 것이 되므로 하지 않고,
    # **돌 수 있는 구간만** 돌린다. 대신 13F 만으로 매길 수 있는 '겹친 운용사 수 상위 10'을
    # 같은 규칙·전 구간으로 나란히 둔다 — 짧은 구간의 결과가 규칙 탓인지 구간 탓인지 가르려는 것이다.
    SH, ISS = load_shares(), issuer_map()
    tops = []
    for rank, label in (("mc", "시점 시가총액 상위 %d" % TOPN),
                        ("ov", "겹친 운용사 수 상위 %d" % TOPN)):
        W, turn, nhold, last, skip, drop = build_topn(counts, 2, TOPN, rank, SH, P, mi, months, ISS)
        rets = monthly_returns(W, P, mi, months)
        if len(rets) < MIN_MONTHS:
            tops.append({"rank": rank, "label": label, "n_months": len(rets),
                         "verdict": "표본 부족", "skipped_quarters": skip})
            continue
        ms = sorted(rets)
        r = np.array([rets[m] for m in ms])
        rf = np.array([RF.get(m, 0.0) for m in ms])
        row = {"rank": rank, "label": label, "k": 2, "top": TOPN,
               "start": ms[0], "end": ms[-1], "n_months": len(ms),
               "skipped_quarters": skip, "dedup_quarters": len(drop),
               "metrics": ann_from_monthly(r, rf),
               "turnover": {"mean": round(float(np.mean([x["v"] for x in turn])), 1) if turn else None},
               "latest": last}
        for name, bs in (("pool", pool), ("spy", spy)):
            b = np.array([bs.get(m, 0.0) for m in ms])
            a, beta, t, _ = capm(r, b, rf)
            row[name] = {"metrics": ann_from_monthly(b, rf), "alpha": a, "beta": beta, "t": t}
        row["curve"] = curve(ms, {"s": rets, "pool": pool, "spy": spy})
        tops.append(row)
        print("  상위%d(%s) %s~%s %d개월 · CAGR %6.2f%% (풀 %5.2f · SPY %5.2f) · 샤프 %.2f "
              "(%.2f · %.2f) · MDD %6.2f%% · 회전 %.0f%%"
              % (TOPN, rank, row["start"], row["end"], len(ms), row["metrics"]["cagr"],
                 row["pool"]["metrics"]["cagr"], row["spy"]["metrics"]["cagr"],
                 row["metrics"]["sharpe"], row["pool"]["metrics"]["sharpe"],
                 row["spy"]["metrics"]["sharpe"], row["metrics"]["mdd"],
                 row["turnover"]["mean"] or 0))
        print("        알파 vs 풀 %+.2f%%/yr (t %+.2f) · vs SPY %+.2f%%/yr (t %+.2f · β %.2f)"
              % (row["pool"]["alpha"] or 0, row["pool"]["t"] or 0,
                 row["spy"]["alpha"] or 0, row["spy"]["t"] or 0, row["spy"]["beta"] or 0))
        print("        지금 담는 것: %s" % ", ".join(last["tickers"]))

    # 다중검정 — 문턱 4개 + 좁힌 판 2개 = 6개를 쟀다. 그중 하나를 골라 보이면 그것이
    # 사후 선택이다. K 변형만 세고 좁힌 판을 빼면 분모가 거짓말을 한다.
    # 🚨 scipy 를 안 쓴다. 쓰던 것은 t분포 양측 p 하나뿐인데, 그것 때문에 이 빌더가
    #   scipy 없는 곳에서 **산출 직전에 죽었다**(2026-08-16 실측 — 곡선까지 다 계산해
    #   놓고 마지막 줄에서 ModuleNotFoundError). 무거운 의존성을 수식 하나에 걸지 않는다.
    # ⚠ 불완전베타로 정확히 같은 값을 낸다(연분수 전개). scipy.stats.t.cdf 와 대조해
    #   소수 6자리까지 일치를 확인했다.
    def _betacf(a_, b_, x):
        MAXIT, EPS, FPMIN = 200, 3e-16, 1e-300
        qab, qap, qam = a_ + b_, a_ + 1.0, a_ - 1.0
        c, d = 1.0, 1.0 - qab * x / qap
        if abs(d) < FPMIN: d = FPMIN
        d = 1.0 / d; h = d
        for m in range(1, MAXIT + 1):
            m2 = 2 * m
            aa = m * (b_ - m) * x / ((qam + m2) * (a_ + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN: d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN: c = FPMIN
            d = 1.0 / d; h *= d * c
            aa = -(a_ + m) * (qab + m) * x / ((a_ + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN: d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN: c = FPMIN
            d = 1.0 / d; de = d * c; h *= de
            if abs(de - 1.0) < EPS: break
        return h

    def _betai(a_, b_, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lb = (math.lgamma(a_ + b_) - math.lgamma(a_) - math.lgamma(b_)
              + a_ * math.log(x) + b_ * math.log(1.0 - x))
        bt = math.exp(lb)
        if x < (a_ + 1.0) / (a_ + b_ + 2.0):
            return bt * _betacf(a_, b_, x) / a_
        return 1.0 - bt * _betacf(b_, a_, 1.0 - x) / b_

    def _t_two_sided(t, df):
        if df <= 0: return None
        return float(_betai(0.5 * df, 0.5, df / (df + t * t)))

    tested = variants + tops
    pv = []
    for v in tested:
        t, n = (v.get("spy") or {}).get("t"), v.get("n_months")
        pv.append(None if t is None or not n else _t_two_sided(abs(t), n - 2))
    for v, p in zip(tested, pv):
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
            "**시총 상위 10은 2020-06부터만 잰다.** 시점별 주식수(SEC XBRL)가 종목당 20관측"
            "(약 5년)뿐이라 2019-11 이전에는 커버가 0%다. 없는 구간을 오늘 주식수로 메우면 "
            "오늘의 승자를 과거에 심는 것이라 하지 않았다. 73개월은 코로나 이후 메가캡 구간에 "
            "치우쳐 있으므로 그 결과를 13년짜리와 나란히 읽으면 안 된다 — 그래서 13F만으로 "
            "매길 수 있는 '겹친 운용사 수 상위 10'을 같은 규칙·전 구간으로 함께 싣는다.",
        ],
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "span": {"start": months[0], "end": months[-1]},
        "ks": KS, "k_requested": 2, "topn": TOPN,
        "tops": tops,
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
