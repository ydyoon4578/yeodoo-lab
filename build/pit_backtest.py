# -*- coding: utf-8 -*-
"""build/pit_backtest.py — 시점정확(PIT) 멤버십으로 다시 돌린 종목선택 백테스트.

무엇을 푸는가.
  랩 본편(tech_backtest.py)은 **오늘의 유니버스를 과거에 소급**한다. 그 사이 지수에서 빠진
  회사가 하나도 없어 모든 수치가 실제보다 좋게 나온다. 여기서는 매월말 **그때 실제로 지수에
  있던 종목만** 후보로 두고 같은 규칙을 다시 돌린다. 두 결과의 차이가 생존편향의 크기다.

데이터 출처가 둘인 이유.
  · 멤버십 — 사내 DB `public.index_constituents` (SPX 2020-09~, NDX 2014-06~).
             둘의 합집합을 쓰므로 늦은 쪽(2020-09)에 맞춘다.
  · 가격  — **yfinance**. 오늘의 유니버스는 랩이 이미 받아 둔 data/sd/*.json 을 그대로 쓰고,
             그 사이 지수에서 빠진 종목만 따로 받아 data/_pit_px_cache.json 에 캐시한다.
             (사내 DB의 ohlcv 는 쓰지 않는다 — 사용자 결정.)

  편출 종목의 가격이 왜 대체로 있나. 지수에서 빠지는 사유의 대부분은 '작아져서'이고 그 회사들은
  **여전히 상장돼 거래된다.** yfinance 가 못 주는 것은 인수·합병·상장폐지·심볼 인계된 경우다.
  ⚠ 그 결손이 '방향이 반대라 안전하다'고 생각하기 쉬운데 실측은 반대다 — 받아 온 종목은 전부
  오늘까지 살아 있고, 누락분을 되돌리면 초과수익은 줄어든다. 이 표도 편향을 다 걷어내지 못한다.

  python build/pit_backtest.py
"""
from __future__ import annotations

import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 ⚠·— 출력 시 죽지 않게
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tech_backtest as TB          # noqa: E402  지표·통계를 다시 구현하지 않는다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "_pit_px_cache.json")
OUT = os.path.join(DATA, "pit_strategies.json")
MEMB = os.path.join(DATA, "pit_members.json")

START = "2020-09-01"
TOPN = TB.TOPN

# 가격·거래량만으로 정의되는 규칙. 펀더멘털 규칙은 시점별 재무·주식수가 없어 제외한다 —
# 반쪽만 PIT 로 바꾸면 비교가 성립하지 않는다.
PRICE_SIDS = ["x-mom12", "x-lowvol", "x-rev1m", "x-52wh", "x-dist200",
              "x-mom-trend", "x-rev1w", "x-minvar", "x-riskbudget", "x-lowbeta",
              "x-snapback", "x-maxlow", "x-max5low", "x-recency", "x-ivol"]
# x-volsurge 는 뺐다. 거래량이 랩 파일(오늘의 유니버스)에만 있어 편출 85종의 채점률이 정확히
# 0%다 — 후보가 100% 생존자인 채로 편출종목을 포함한 대조군과 겨루게 되어, 이 파일이 없애려는
# 바로 그 선견이 규칙 하나에만 남는다. 거래량을 편출종목까지 받으면 되살릴 수 있다.
EXCLUDED_SIDS = {"x-volsurge": "편출 종목 거래량 부재 — 후보가 생존자로만 좁혀져 PIT 이 성립 안 함"}


def fetch_members():
    """월말 멤버십을 사내 DB에서 받아 data/pit_members.json 에 캐시한다.

    DB 는 사내망에서만 닿는다(CI 러너는 못 간다). 한 번 받아 두면 이후 실행은 캐시로 돈다.
    """
    if os.path.exists(MEMB):
        d = json.load(io.open(MEMB, encoding="utf-8"))
        print("  멤버십 캐시 사용 — %d개월" % len(d["members"]))
        return d["members"]
    sys.path.insert(0, r"C:\Projects\Yeouido\strategy")
    from _common import conn                       # noqa: E402
    import pandas as pd
    c = conn()
    df = pd.read_sql(
        """
        -- ⚠ max(dt) 를 두 지수 **합쳐서** 뽑으면 안 된다. 지수마다 그 달 마지막 dt 가 달라
        --   한쪽만 남는 달이 생긴다(실측: 2026-08 에 NDX 0행 → 15종이 조용히 증발).
        --   그리고 DB 는 미래 일자 행을 들고 있어(오늘 이후) 상한을 걸지 않으면 그게 뽑힌다.
        WITH me AS (
          SELECT index, date_trunc('month', dt) mon, max(dt) dt
          FROM public.index_constituents
          WHERE index IN ('SPX Index','NDX Index') AND dt >= %s AND dt <= CURRENT_DATE
          GROUP BY index, date_trunc('month', dt)
        )
        SELECT DISTINCT to_char(ic.dt,'YYYY-MM') ym,
               replace(replace(coalesce(bb_ticker, ticker),' US EQUITY',''),' US','') t
        FROM public.index_constituents ic
        JOIN me ON ic.index = me.index AND ic.dt = me.dt
        """, c, params=(START,))
    df["t"] = df["t"].str.strip().str.strip("$")
    df = df[(df["t"].str.len() > 0) & (~df["t"].str.contains(r"[/_]", regex=True))]
    mem = {ym: sorted(set(g["t"])) for ym, g in df.groupby("ym")}
    json.dump({"note": "월말 지수 편입 종목(SPX ∪ NDX). 사내 DB public.index_constituents 에서 "
                       "받아 캐시한 것 — 원천은 라이선스라 이 파일만 저장소에 둔다.",
               "source": "public.index_constituents", "start": START, "members": mem},
              io.open(MEMB, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("  멤버십 %d개월 받아 캐시 (%s)" % (len(mem), MEMB))
    return mem


def load_prices(need, MEMBER_SPAN):
    """티커→{날짜:종가}. 오늘의 유니버스는 랩 파일, 편출 종목은 캐시에서."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    pdates = st["pxd_dates"]
    px = {}
    for s in st["stocks"]:
        t = s["t"]
        if t not in need:
            continue
        p = os.path.join(DATA, "sd", t + ".json")
        if not os.path.exists(p):
            continue
        a = json.load(io.open(p, encoding="utf-8")).get("pxd") or []
        if len(a) == len(pdates):
            px[t] = {d: v for d, v in zip(pdates, a) if v is not None}
    n_lab = len(px)
    if not os.path.exists(CACHE):
        # ⚠ 조용히 넘어가면 안 된다. 캐시가 없으면 후보가 '오늘 살아남은 종목'만 남아
        #   생존자 전용 백테스트가 되는데, 파일 이름과 문구는 그대로 'PIT' 라 더 나쁘다.
        sys.exit("편출 종목 가격 캐시가 없다(%s) — `python build/pit_backtest.py --fetch-cache` 로 "
                 "먼저 받을 것. 없이 돌리면 생존자 전용 결과에 PIT 라벨이 붙는다." % CACHE)
    cache = json.load(io.open(CACHE, encoding="utf-8"))
    bad_reuse = []
    for t, ser in cache.items():
        if t not in need or t in px or not ser:
            continue
        # 티커 재사용 방어 — 캐시 계열이 '그 티커가 멤버였던 기간'과 안 겹치면 다른 회사다.
        # 실측 사례: FB 캐시는 ProShares ETF(2025-06~), 멤버십의 FB 는 2020~2022 의 메타.
        ks = sorted(ser)
        lo, hi = MEMBER_SPAN.get(t, ("9999-99", "0000-00"))
        if ks[-1][:7] < lo or ks[0][:7] > hi:
            bad_reuse.append(t); continue
        px[t] = ser
    if bad_reuse:
        print("  ⚠ 티커 재사용 의심 %d종 제외(계열 기간이 멤버 기간과 안 겹침): %s"
              % (len(bad_reuse), ", ".join(sorted(bad_reuse))))
    print("  가격 %d종 (랩 %d + 편출캐시 %d)" % (len(px), n_lab, len(px) - n_lab))
    return px


def main():
    print("PIT 백테스트 — 매월말 실제 편입 종목만 후보 (SPX ∪ NDX, %s~)" % START)
    mem = fetch_members()
    need = set()
    for v in mem.values():
        need |= set(v)
    # 티커별 '멤버였던 기간' — 재사용 티커를 걸러내는 데 쓴다
    span = {}
    for ym, lst in mem.items():
        for t in lst:
            a, b = span.get(t, (ym, ym))
            span[t] = (min(a, ym), max(b, ym))
    px_map = load_prices(need, span)

    # 거래일 격자 — 랩과 같은 격자를 쓴다(랩이 이미 yfinance 거래일로 만들어 둔 것).
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = [d for d in st["pxd_dates"]]
    n = len(dates)
    tickers = sorted(px_map)
    px = {t: [px_map[t].get(d) for d in dates] for t in tickers}
    vlm = {}
    for t in tickers:                              # 거래량은 랩 파일에만 있다(편출분은 없음)
        p = os.path.join(DATA, "sd", t + ".json")
        if os.path.exists(p):
            v = json.load(io.open(p, encoding="utf-8")).get("vd")
            vlm[t] = v if isinstance(v, list) and len(v) == n else None
        else:
            vlm[t] = None

    R = TB.daily_rets(px)
    me = set(TB.month_ends(dates))
    # ⚠ i0 를 START 직후 아무 날로 잡으면 안 된다. 전략은 첫 월말 리밸까지 보유가 없어 수익 0인데
    #   대조군은 그날부터 만기 투자다 — 그 20거래일에 대조군이 −2.77% 빠지면서 16종 전부가
    #   공짜 초과수익을 얻는다(대조군 CAGR 도 0.76%p 낮게 잡힌다). 첫 월말에서 같이 출발시킨다.
    _s0 = next(i for i in range(n) if dates[i] >= START)
    i0 = min(i for i in me if i >= _s0)

    def members_at(i):
        return set(mem.get(dates[i][:7]) or [])

    # 대조군도 PIT 여야 한다 — 전략만 PIT 이고 벤치가 소급이면 초과수익이 엉뚱해진다.
    ixr = [None] * n
    cur = members_at(i0) & set(tickers)
    for i in range(1, n):
        if (i - 1) in me:
            m = members_at(i - 1) & set(tickers)
            if m:
                cur = m
        rs = [R[t][i] for t in cur if R[t][i] is not None]
        ixr[i] = sum(rs) / len(rs) if rs else 0.0
    ixvol = [TB.vol(ixr, i, 20) for i in range(n)]

    rf = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8")).get("monthly") or {}
    rf = {k: v for k, v in rf.items() if k >= dates[i0][:7]}

    TB.build_strats()
    BY = {s["sid"]: s for s in TB.STRATS}
    C = {"px": px, "vlm": vlm, "R": R, "ixr": ixr, "ixvol": ixvol}

    # 커버리지 — 매월말 '멤버인데 가격이 없는' 비율. 남은 편향의 크기를 정직하게 싣는다.
    cov = []
    for i in sorted(me):
        if i < i0:
            continue
        m = members_at(i)
        if m:
            cov.append(len(m & set(tickers)) / len(m))
    cov_min, cov_med = (min(cov), sorted(cov)[len(cov) // 2]) if cov else (0, 0)
    print("  멤버 대비 가격 보유율: 최저 %.1f%% · 중앙 %.1f%%" % (100 * cov_min, 100 * cov_med))

    out = []
    for sid in PRICE_SIDS:
        S = BY.get(sid)
        if not S:
            continue
        hold, nav, srets, turns = [], [100.0], [], 0
        for i in range(i0 + 1, n):
            if (i - 1) in me:
                pool = members_at(i - 1)
                sc = []
                for t in tickers:
                    if t not in pool:              # ★ PIT 마스킹
                        continue
                    v = score(S, t, i - 1, C)
                    if v is not None and v == v:
                        sc.append((v, t))
                sc.sort(reverse=True)
                new = [t for _v, t in sc[:TOPN]]
                if new:
                    turns += (len(set(new) ^ set(hold)) / (2 * TOPN)) if hold else 1.0
                    hold = new
            rs = [R[t][i] for t in hold if R[t][i] is not None]
            srets.append(sum(rs) / len(rs) if rs else 0.0)
            nav.append(nav[-1] * (1 + srets[-1]))
        bnav = [100.0]
        for i in range(i0 + 1, n):
            bnav.append(bnav[-1] * (1 + (ixr[i] or 0.0)))
        d2 = dates[i0:]
        stt, bs = TB.ann_stats(nav, d2, rf), TB.ann_stats(bnav, d2, rf)
        out.append({
            "sid": sid, "name": S["name"], "metrics": stt, "bench": bs,
            "excess_cagr": round(stt.get("cagr", 0) - bs.get("cagr", 0), 2),
            "d_sharpe": round((stt.get("sharpe") or 0) - (bs.get("sharpe") or 0), 3),
            "t": TB.tstat(srets, ixr[i0 + 1:]),
            "turnover": round(turns / max(1, (n - i0) / 252), 2),
            "holdings": {"kind": "xsec", "as_of": dates[-1], "n": len(hold), "tickers": sorted(hold)},
        })
        print("  %-28s CAGR %7.2f (대조군 %6.2f) · Sharpe %5.2f · t %5.2f"
              % (S["name"][:28], stt.get("cagr", 0), bs.get("cagr", 0),
                 stt.get("sharpe") or 0, out[-1]["t"] or 0))

    doc = {
        "note": "매월말 실제 지수 편입 종목만 후보로 두고 다시 돌린 결과. 랩 본편(오늘의 유니버스를 "
                "과거로 소급)과의 차이가 생존편향의 크기다.",
        "start": dates[i0], "as_of": dates[-1], "n_days": n - i0,
        "span_years": round((n - i0) / 252.0, 1),
        "universe": "SPX ∪ NDX · 매월말 실제 편입(public.index_constituents) · 가격은 yfinance",
        "coverage": {"min": round(cov_min, 4), "median": round(cov_med, 4)},
        "limits": [
            "구간이 %s부터다 — SPX 멤버십이 그때부터만 있어 합집합을 거기 맞췄다." % START,
            # ⚠ 예전엔 "누락은 프리미엄 받고 사라진 쪽이라 방향이 반대"라고 적었다. 실측으로 반증됐다 —
            #   캐시 종목은 전부 오늘까지 살아 있고 보유율은 2020-09 91.8%→최근 100%로 단조 상승한다.
            #   즉 결손은 '오늘까지 못 살아남음' 그 자체이고, 누락분을 되돌리면 초과수익은 **줄어든다**
            #   (누락 기전 재현 실험: 대조군 +2.28%p, 전략 초과 중앙 +1.27%p, 모멘텀·반전 계열 전부 +).
            "월말 멤버 중 가격을 못 구한 종목이 있다(보유율 최저 %.1f%% · 중앙 %.1f%%). 이 결손은 "
            "중립이 아니다 — 남은 종목은 전부 오늘까지 살아 있고 보유율이 시간에 따라 100%%로 오른다. "
            "누락분을 되돌리면 여기 초과수익은 더 줄어든다(재현 실험상 중앙 1.3%%p). 즉 이 표조차 "
            "생존편향을 완전히 걷어내지 못했고, 남은 방향은 여전히 낙관 쪽이다."
            % (100 * cov_min, 100 * cov_med),
            "'거래량 급증' 규칙은 아예 뺐다 — 거래량이 오늘의 유니버스에만 있어 후보가 100%% "
            "생존자로 좁혀지는데, 대조군에는 편출 종목이 들어가 비교가 성립하지 않는다.",
            "t 는 이 표본(%d거래일·규칙 %d종)에서 계산한 값이다. 랩 본편의 본페로니 임계(표본 "
            "2252일·규칙 51종 기준)를 그대로 들이대면 잣대가 어긋난다 — 여기서는 문턱을 넘고 말고가 "
            "아니라 '소급 표본 대비 t 가 얼마나 무너지는가'로 읽어야 한다." % (n - i0, len(PRICE_SIDS)),
            "가격·거래량 규칙 %d종만 다룬다. 펀더멘털 규칙은 시점별 재무·주식수가 없어 제외." % len(PRICE_SIDS),
            "비용 0(gross) · 신호는 당일 종가로 계산해 다음 거래일부터 적용(선견 없음).",
        ],
        "strategies": out,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("\n→ %s · %d종 · %s ~ %s (%s년)"
          % (OUT, len(out), doc["start"], doc["as_of"], doc["span_years"]))
    return 0


def score(S, t, j, C):
    """tech_backtest 의 횡단면 점수 갈래(가격·거래량 규칙만)를 그대로 옮긴 것."""
    sid = S["sid"]
    P = C["px"][t]
    R, ixr, ixvol = C["R"], C["ixr"], C["ixvol"]
    if sid == "x-52wh":
        win = [x for x in P[max(0, j - 251):j + 1] if x]
        hi = max(win) if win else None
        return (P[j] / hi) if (hi and P[j]) else None
    if sid == "x-dist200":
        m = TB.sma(P, j, 200)
        return (P[j] / m - 1) if (m and P[j]) else None
    if sid == "x-mom-trend":
        m200 = TB.sma(P, j, 200)
        if not m200 or not P[j] or P[j] <= m200:
            return None
        return (TB.ret(P, j, 252) or -9) - (TB.ret(P, j, 21) or 0)
    if sid == "x-rev1w":
        return -(TB.ret(P, j, 5) or 9)
    if sid == "x-minvar":
        sv, mv = TB.vol(R[t], j, 120), ixvol[j]
        return -(0.5 * sv + 0.5 * mv) if (sv and mv) else None
    if sid == "x-riskbudget":
        sv = TB.vol(R[t], j, 60)
        return (1.0 / sv) if sv and sv > 0 else None
    if sid == "x-lowbeta":
        b = TB.beta(R[t], ixr, j, 120)
        return -b if b is not None else None
    if sid == "x-ivol":
        iv = TB.idio_vol(R[t], ixr, j, 120)
        return -iv if iv is not None else None
    if sid == "x-snapback":
        m200 = TB.sma(P, j, 200)
        if not m200 or not P[j] or P[j] <= m200:
            return None
        rv = TB.rsi(P, j)
        return -rv if rv is not None else None
    if sid == "x-volsurge":
        V = C["vlm"].get(t)
        m200 = TB.sma(P, j, 200)
        if not V or not m200 or not P[j] or P[j] <= m200:
            return None
        a, b = TB.sma(V, j, 20), TB.sma(V, j, 60)
        return (a / b) if (a and b and b > 0) else None
    return S["fn"](t, j, P, R[t], TB.vol(R[t], j, 60))


def fetch_cache():
    """편출 종목 가격을 yfinance 로 받아 캐시한다 — 저장소에 만드는 코드가 있어야 재현이 된다.

    오늘의 랩 유니버스에 없는 과거 멤버만 받는다. 지수에서 '작아져서' 빠진 회사는 대개
    아직 상장돼 있어 대부분 받아진다. 인수·상폐분은 못 받고, 그 결손의 방향은 limits 에 적는다.
    """
    import time
    import yfinance as yf
    mem = fetch_members()
    need = set()
    for v in mem.values():
        need |= set(v)
    lab = {s["t"] for s in json.load(io.open(os.path.join(DATA, "stocks.json"),
                                             encoding="utf-8"))["stocks"]}
    want = sorted(t for t in need - lab if t.isalpha() or "." in t)
    print("편출 종목 %d종 가격 수집 (yfinance)" % len(want))
    out = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    got = 0
    for i in range(0, len(want), 25):
        ch = [t for t in want[i:i + 25] if t not in out]
        if not ch:
            continue
        try:
            d = yf.download(ch, period="10y", auto_adjust=True, progress=False, threads=False)["Close"]
        except Exception as e:
            print("  [yf] 배치 실패:", str(e)[:60]); continue
        for t in ch:
            if t in d:
                ser = d[t].dropna()
                if len(ser) > 200:
                    out[t] = {str(k.date()): round(float(v), 4) for k, v in ser.items()}
                    got += 1
        time.sleep(2)
    json.dump(out, io.open(CACHE, "w", encoding="utf-8"), separators=(",", ":"))
    print("→ %s · %d종 (이번에 %d종 추가) · 못 받은 %d종은 인수·상폐로 보인다"
          % (CACHE, len(out), got, len(want) - len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(fetch_cache() if "--fetch-cache" in sys.argv else main())
