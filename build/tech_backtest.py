#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""테크니컬 타이밍·횡단면 전략 백테스트 → data/tech_strategies.json

기각 아카이브는 '무엇을 왜 기각했는가'만 적혀 있었다. 그건 결론이지 근거가 아니다.
이 파일은 **규칙을 실제로 돌려 숫자를 내는** 자리다 — 통과든 기각이든 같은 표에서.

── 무엇으로 도는가 ─────────────────────────────────────────────────────
data/sd/<티커>.json 의 종가(pxd)·거래량(vd) 753거래일 × 518종목.
2023-07-25 ~ 2026-07-24. 그 외 자산군(채권·상품·현금성 ETF)은 이 저장소에 없다 —
그래서 여기 실리는 건 **주식만으로 만들 수 있는 규칙**뿐이다.

── 이 백테스트가 못 하는 것(결과보다 먼저 읽어야 한다) ──────────────────
* **생존편향.** 오늘의 518종목을 과거 3년에 그대로 적용한다. 그 사이 편출된 종목은
  아예 없다. 상장폐지·부진 종목이 빠진 표본이라 **모든 수치가 실제보다 좋게 나온다.**
  이 저장소에는 시점별 편입(PIT) 이력이 스냅샷 하나뿐이라 보정할 방법이 없다.
* **표본이 3년뿐이다.** 한 번의 상승장 국면이 결과를 지배할 수 있고, 3년으로는
  국면 전환을 몇 번 못 겪는다. 샤프 1.0이 나와도 그게 실력인지 구간인지 못 가른다.
* **비용 0.** 이 랩의 기본 규약대로 무비용(gross)이다. 회전율이 높은 규칙일수록
  실제와 벌어진다 — 그래서 회전율을 함께 싣는다.
* **다중검정.** 여러 규칙을 한 표본에서 돌리면 그중 최고는 우연히도 좋아 보인다.
  그래서 **돌린 규칙을 하나도 빼지 않고 전부 싣는다.** 좋은 것만 고르면 그게 데이터마이닝이다.

사용: python3 build/tech_backtest.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_SD = os.path.join(DATA, "sd")
OUT = os.path.join(DATA, "tech_strategies.json")

TOPN = 50          # 횡단면 전략이 들고 갈 종목 수
MIN_HIST = 260     # 신호 계산에 필요한 최소 과거 길이(약 1년)


# ── 유틸 ────────────────────────────────────────────────────────────────
def sma(xs, i, n):
    if i + 1 < n:
        return None
    s = 0.0
    for k in range(i - n + 1, i + 1):
        v = xs[k]
        if v is None:
            return None
        s += v
    return s / n


def ret(xs, i, n):
    """i 시점 기준 최근 n일 수익률."""
    if i - n < 0:
        return None
    a, b = xs[i - n], xs[i]
    if not a or not b or a <= 0:
        return None
    return b / a - 1.0


def vol(rets, i, n):
    """최근 n일 일간수익률 표준편차(연율 아님)."""
    if i + 1 < n:
        return None
    w = [r for r in rets[i - n + 1:i + 1] if r is not None]
    if len(w) < n // 2:
        return None
    m = sum(w) / len(w)
    v = sum((x - m) ** 2 for x in w) / max(1, len(w) - 1)
    return math.sqrt(v)


def rsi(xs, i, n=14):
    if i < n:
        return None
    up = dn = 0.0
    for k in range(i - n + 1, i + 1):
        a, b = xs[k - 1], xs[k]
        if a is None or b is None:
            return None
        d = b - a
        up += max(d, 0.0)
        dn += max(-d, 0.0)
    if up + dn == 0:
        return 50.0
    return 100.0 * up / (up + dn)


def beta(rs, mkt, i, n):
    """i 시점까지 최근 n일 시장 대비 베타."""
    if i + 1 < n:
        return None
    xs, ys = [], []
    for k in range(i - n + 1, i + 1):
        a, b = rs[k], mkt[k]
        if a is None or b is None:
            continue
        xs.append(b)
        ys.append(a)
    if len(xs) < n // 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / max(1, len(xs) - 1)
    var = sum((x - mx) ** 2 for x in xs) / max(1, len(xs) - 1)
    return (cov / var) if var > 0 else None


def maxdd(nav):
    peak, mdd = nav[0], 0.0
    for v in nav:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1.0)
    return mdd


def ann_stats(nav, dates, rf_m):
    """연율 수익·변동성·샤프(무위험 차감)·MDD."""
    n = len(nav)
    if n < 2:
        return {}
    yrs = (dt.date.fromisoformat(dates[-1]) - dt.date.fromisoformat(dates[0])).days / 365.25
    cagr = (nav[-1] / nav[0]) ** (1 / yrs) - 1 if yrs > 0 and nav[0] > 0 else None
    rs = [nav[i] / nav[i - 1] - 1 for i in range(1, n) if nav[i - 1] > 0]
    if not rs:
        return {}
    m = sum(rs) / len(rs)
    sd = math.sqrt(sum((x - m) ** 2 for x in rs) / max(1, len(rs) - 1))
    av = sd * math.sqrt(252)
    # 무위험은 월별 값을 일할로 환산해 평균만 쓴다(정밀도보다 일관성)
    rfd = sum(rf_m.values()) / len(rf_m) / 21 if rf_m else 0.0
    sharpe = ((m - rfd) / sd * math.sqrt(252)) if sd > 0 else None
    return {"cagr": round((cagr or 0) * 100, 2), "vol": round(av * 100, 2),
            "sharpe": round(sharpe, 3) if sharpe is not None else None,
            "mdd": round(maxdd(nav) * 100, 2)}


def tstat(a, b):
    """두 일간수익 계열의 차이에 대한 t값(대응표본)."""
    d = [x - y for x, y in zip(a, b)]
    if len(d) < 30:
        return None
    m = sum(d) / len(d)
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / max(1, len(d) - 1))
    return round(m / (sd / math.sqrt(len(d))), 2) if sd > 0 else None


# ── 데이터 ──────────────────────────────────────────────────────────────
def load():
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        st = json.load(f)
    dates = st["pxd_dates"]
    n = len(dates)
    px, vlm, meta = {}, {}, {}
    for s in st["stocks"]:
        t = s["t"]
        p = os.path.join(DIR_SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        a, v = d.get("pxd"), d.get("vd")
        if not isinstance(a, list) or len(a) != n:
            continue
        px[t] = a
        vlm[t] = v if isinstance(v, list) and len(v) == n else None
        meta[t] = {"name": s.get("name") or "", "sector": s.get("sector") or ""}
    rf = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8")).get("monthly") or {}
    rf = {k: v for k, v in rf.items() if k >= dates[0][:7]}
    return dates, px, vlm, meta, rf


def daily_rets(px):
    out = {}
    for t, a in px.items():
        r = [None]
        for i in range(1, len(a)):
            p0, p1 = a[i - 1], a[i]
            r.append((p1 / p0 - 1.0) if (p0 and p1 and p0 > 0) else None)
        out[t] = r
    return out


def month_ends(dates):
    """월말 인덱스(다음 날의 월이 다르면 그 날이 월말)."""
    idx = []
    for i in range(len(dates) - 1):
        if dates[i][:7] != dates[i + 1][:7]:
            idx.append(i)
    return idx


# ── 전략 정의 ───────────────────────────────────────────────────────────
# 각 전략은 (시점 i, 상태) → 목표 비중을 준다.
#   kind='timing'  : 시장(동일가중 유니버스) 노출 0~1
#   kind='xsec'    : 종목 선택 — 상위 TOPN 동일가중
STRATS = []


def timing(sid, name, rule, fn, why, arch=None):
    STRATS.append({"sid": sid, "name": name, "kind": "timing", "rule": rule, "why": why, "fn": fn, "arch": arch})


def xsec(sid, name, rule, fn, why, arch=None):
    STRATS.append({"sid": sid, "name": name, "kind": "xsec", "rule": rule, "why": why, "fn": fn, "arch": arch})


def build_strats():
    # ── 타이밍: 시장 노출을 0/1(또는 연속)으로 조절 ──
    timing("t-sma200", "200일 이동평균 타이밍",
           "동일가중 지수가 200일 단순이동평균 위면 100% 편입, 아래면 현금(무위험).",
           lambda ix, i, R, V: 1.0 if (sma(ix, i, 200) is not None and ix[i] > sma(ix, i, 200)) else 0.0,
           "가장 오래되고 가장 많이 인용되는 추세 필터. 기준선이 되라고 넣는다.")
    timing("t-cross", "50/200 골든크로스",
           "50일선이 200일선 위면 편입, 아래면 현금.",
           lambda ix, i, R, V: 1.0 if (sma(ix, i, 50) is not None and sma(ix, i, 200) is not None
                                       and sma(ix, i, 50) > sma(ix, i, 200)) else 0.0,
           "같은 추세 개념을 두 이동평균의 관계로 바꾼 것. 200일선 단독과 얼마나 다른지 본다.")
    timing("t-tsmom", "절대 모멘텀 (12-1)",
           "최근 12개월 수익에서 마지막 1개월을 뺀 값이 양수면 편입, 아니면 현금.",
           lambda ix, i, R, V: 1.0 if ((ret(ix, i, 252) or -1) - (ret(ix, i, 21) or 0) > 0) else 0.0,
           "시계열 모멘텀(CTA 계열)의 주식 단독 버전. 마지막 1개월 제외는 단기 반전을 피하려는 관례다.")
    timing("t-voltgt", "변동성 타깃팅 (연 12%)",
           "최근 20일 실현변동성으로 목표 연 12%에 맞춰 노출을 0~1로 조절(레버리지 없음).",
           lambda ix, i, R, V: (min(1.0, 0.12 / (V * math.sqrt(252))) if (V and V > 0) else 0.0),
           "수익률이 아니라 위험을 목표로 잡는 규칙. 상승장에서 뒤처지고 급락장에서 덜 맞는다.")
    timing("t-rsi", "RSI 과매도 반등",
           "RSI(14)가 30 아래로 내려가면 편입, 60 위로 올라오면 현금(히스테리시스).",
           None, "역추세 규칙. 이 랩은 종목 신호에서 역추세를 이미 폐기했다 — 시장 단위에서도 같은지 본다.")
    timing("t-donch", "돈치안 20일 돌파",
           "20일 최고가를 넘으면 편입, 20일 최저가를 깨면 현금.",
           None, "가격 돌파만 쓰는 고전 추세 규칙. 이동평균과 무엇이 다른지 본다.",
           arch="donchian-breakout")
    timing("t-macd", "MACD 신호선 교차",
           "MACD(12,26)가 신호선(9) 위면 편입, 아래면 현금.",
           None, "이동평균의 변화율을 보는 규칙. 전환이 이동평균보다 빠른 대신 잦다.")
    timing("t-volreg", "저변동성 국면만 편입",
           "최근 20일 실현변동성이 과거 1년 중앙값보다 낮으면 편입, 높으면 현금.",
           None, "변동성 자체를 국면 신호로 쓴다. 변동성 군집이 실제로 수익과 이어지는지 본다.")

    # ── 횡단면: 상위 TOPN 동일가중, 월말 리밸런스 ──
    xsec("x-mom12", "12-1 모멘텀 상위 50",
         "최근 12개월 수익 − 최근 1개월 수익 상위 50종목 동일가중, 월말 리밸런스.",
         lambda t, i, P, R, V: ((ret(P, i, 252) or -9) - (ret(P, i, 21) or 0)),
         "횡단면 모멘텀의 표준형. 이 표에서 기준선 역할을 한다.")
    xsec("x-lowvol", "저변동성 상위 50",
         "최근 60일 실현변동성이 가장 낮은 50종목 동일가중, 월말 리밸런스.",
         lambda t, i, P, R, V: (-(V or 9)),
         "저변동성 이상현상. 위험을 덜 지고 더 벌 수 있는가를 이 표본에서 본다.")
    xsec("x-rev1m", "단기 반전 (1개월 최하위 50)",
         "최근 1개월 수익이 가장 낮은 50종목 동일가중, 월말 리밸런스.",
         lambda t, i, P, R, V: (-(ret(P, i, 21) or 9)),
         "단기 반전. 모멘텀과 정반대 방향이라 둘을 같은 표에 두면 서로의 대조군이 된다.",
         arch="smallcap-monthly-reversal")
    xsec("x-52wh", "52주 신고가 근접 50",
         "현재가가 52주 최고가에 가장 가까운 50종목 동일가중, 월말 리밸런스.",
         None, "고점 근접을 추세의 대리변수로 쓴다. 12-1 모멘텀과 얼마나 겹치는지 본다.")
    xsec("x-dist200", "200일선 이격도 상위 50",
         "현재가가 200일선 위로 가장 많이 벌어진 50종목 동일가중, 월말 리밸런스.",
         None, "추세 강도를 이격도로 재는 규칙. 과열과 강세를 구분하지 못한다는 비판이 있다.")
    xsec("x-volsurge", "거래량 급증 + 추세 50",
         "20일 평균거래량이 60일 평균 대비 가장 크게 늘고 200일선 위인 50종목, 월말 리밸런스.",
         None, "가격에 거래량을 더한다. 거래량이 정보 유입의 대리변수라는 가정을 시험한다.")

    # ── 기각 아카이브에 있던 규칙들 — 결론만 있고 숫자가 없던 것을 여기서 돌린다 ──
    # arch: archive.html의 sid와 잇는다. 이 저장소의 데이터(주식 종가·거래량)로 만들 수 있는 것만.
    xsec("x-mom-trend", "대형주 모멘텀 + 200일선 추세",
         "12-1 모멘텀 상위 중 200일선 위인 종목만 50개 동일가중, 월말 리밸런스.",
         None, "모멘텀에 추세 필터를 덧대면 낙폭이 줄어드는지 본다. 아카이브의 '대형주 횡단면 모멘텀·200일선 추세'.",
         arch="largecap-momentum-200dma")
    xsec("x-rev1w", "주간 반전 (1주 최하위 50)",
         "최근 5거래일 수익이 가장 낮은 50종목 동일가중, 월말 리밸런스.",
         None, "반전을 월이 아니라 주 단위로 잡는다. 아카이브의 '소형주 단기 반전 롱숏(Weekly)'을 롱온리로 옮긴 것.",
         arch="smallcap-weekly-reversal")
    xsec("x-minvar", "최소분산 (축소추정)",
         "최근 120일 공분산을 대각으로 축소(λ=0.5)해 분산이 가장 낮아지는 50종목을 역분산 가중.",
         None, "완전한 최적화 대신 축소추정 역분산으로 근사한다. 아카이브의 '축소추정 최소분산 배분'.",
         arch="min-variance-lw")
    xsec("x-riskbudget", "리스크 버짓 (역변동성)",
         "60일 실현변동성의 역수로 가중한 상위 50종목(변동성 낮은 순), 월말 리밸런스.",
         None, "위험을 균등하게 나눠 갖는다는 발상. 아카이브의 '리스크 버짓 배분'.",
         arch="risk-budgeting")
    xsec("x-lowbeta", "저베타 틸트",
         "동일가중 지수 대비 120일 베타가 가장 낮은 50종목 동일가중, 월말 리밸런스.",
         None, "저변동성과 저베타는 다르다 — 둘을 같은 표에 두고 갈라 본다. 아카이브의 '저베타 비중 틸트'.",
         arch="low-beta-weight-tilt")
    xsec("x-snapback", "추세정렬 과매도 반등",
         "200일선 위이면서 RSI(14)가 가장 낮은 50종목 동일가중, 월말 리밸런스.",
         None, "추세는 살아 있는데 단기만 눌린 종목. 이 랩이 종목 신호에서 역추세를 폐기하며 남긴 유일한 형태다.",
         arch="trend-aligned-oversold-snapback")
    timing("t-ndxvol", "NDX 변동성 타깃 (연 12%)",
           "NDX 편입 종목만의 동일가중 지수에 20일 실현변동성 기준 목표 연 12% 노출.",
           None, "같은 규칙을 좁은 유니버스에 걸면 달라지는지 본다. 아카이브의 '변동성 타깃팅 — NDX 단일자산'.",
           arch="vol-targeting-ndx")
    timing("t-disp", "횡단면 분산도 게이트",
           "종목 간 수익률 분산(횡단면 표준편차)이 과거 1년 중앙값보다 낮으면 편입, 높으면 현금.",
           None, "분산도가 높을 때가 위험 국면이라는 가설. 아카이브의 '횡단면 분산도 리스크 게이트'.",
           arch="cross-sectional-dispersion-gate")
    timing("t-kelly", "켈리 스케일링 (레버리지 없음)",
           "최근 120일 평균수익/분산으로 켈리 비중을 계산해 0~1로 자른다.",
           None, "기대수익과 위험을 한 식에 넣는다. 레버리지를 안 쓰므로 상한 1에서 잘린다. 아카이브의 '켈리 기준 레버리지 스케일링'.",
           arch="kelly-scaling")


# ── 실행 ────────────────────────────────────────────────────────────────
def run():
    dates, px, vlm, meta, rf = load()
    n = len(dates)
    tickers = sorted(px)
    R = daily_rets(px)
    me = set(month_ends(dates))

    # 동일가중 유니버스 지수(일간 리밸런스) — 타이밍 전략의 대상이자 모든 전략의 벤치마크
    ix = [100.0]
    ixr = [None]
    for i in range(1, n):
        rs = [R[t][i] for t in tickers if R[t][i] is not None]
        r = sum(rs) / len(rs) if rs else 0.0
        ixr.append(r)
        ix.append(ix[-1] * (1 + r))

    ixvol = [vol(ixr, i, 20) for i in range(n)]

    # NDX 편입분만의 동일가중 지수 — 같은 규칙을 좁은 유니버스에 걸어보기 위해
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as _f:
        _st = json.load(_f)
    ndx = [s["t"] for s in _st["stocks"] if "NDX" in (s.get("idx") or []) and s["t"] in px]
    ndxr = [None]
    for i in range(1, n):
        rs = [R[t][i] for t in ndx if R[t][i] is not None]
        ndxr.append(sum(rs) / len(rs) if rs else 0.0)
    ndxvol = [vol(ndxr, i, 20) for i in range(n)]

    # 횡단면 분산도 — 그날 종목 수익률의 표준편차(국면 대리변수)
    disp = [None] * n
    for i in range(1, n):
        rs = [R[t][i] for t in tickers if R[t][i] is not None]
        if len(rs) > 50:
            m = sum(rs) / len(rs)
            disp[i] = math.sqrt(sum((x - m) ** 2 for x in rs) / (len(rs) - 1))
    rfd = (sum(rf.values()) / len(rf) / 21) if rf else 0.0

    build_strats()
    out = []
    bench_r = ixr[MIN_HIST:]

    for S in STRATS:
        w = [0.0] * n
        if S["kind"] == "timing":
            state = 0.0
            for i in range(n):
                if i < MIN_HIST:
                    continue
                sid = S["sid"]
                if sid == "t-rsi":
                    v = rsi(ix, i)
                    if v is not None:
                        if v < 30:
                            state = 1.0
                        elif v > 60:
                            state = 0.0
                    w[i] = state
                elif sid == "t-donch":
                    hi = max(ix[i - 20:i]) if i >= 20 else None
                    lo = min(ix[i - 20:i]) if i >= 20 else None
                    if hi and ix[i] > hi:
                        state = 1.0
                    elif lo and ix[i] < lo:
                        state = 0.0
                    w[i] = state
                elif sid == "t-macd":
                    def ema(xs, i, n_, cache={}):
                        k = 2 / (n_ + 1)
                        e = xs[max(0, i - n_ * 3)]
                        for j in range(max(0, i - n_ * 3) + 1, i + 1):
                            e = xs[j] * k + e * (1 - k)
                        return e
                    m = ema(ix, i, 12) - ema(ix, i, 26)
                    prev = ema(ix, i - 1, 12) - ema(ix, i - 1, 26) if i > 0 else m
                    sig = m * 0.2 + prev * 0.8
                    w[i] = 1.0 if m > sig else 0.0
                elif sid == "t-ndxvol":
                    v = ndxvol[i]
                    w[i] = min(1.0, 0.12 / (v * math.sqrt(252))) if (v and v > 0) else 0.0
                elif sid == "t-disp":
                    hist = [x for x in disp[max(0, i - 252):i] if x]
                    cur = disp[i]
                    if cur and hist:
                        med = sorted(hist)[len(hist) // 2]
                        w[i] = 1.0 if cur < med else 0.0
                elif sid == "t-kelly":
                    win = [x for x in ixr[max(0, i - 120):i + 1] if x is not None]
                    if len(win) > 30:
                        m = sum(win) / len(win)
                        v2 = sum((x - m) ** 2 for x in win) / max(1, len(win) - 1)
                        w[i] = max(0.0, min(1.0, m / v2)) if v2 > 0 else 0.0
                elif sid == "t-volreg":
                    hist = [v for v in ixvol[max(0, i - 252):i] if v]
                    cur = ixvol[i]
                    if cur and hist:
                        med = sorted(hist)[len(hist) // 2]
                        w[i] = 1.0 if cur < med else 0.0
                else:
                    w[i] = S["fn"](ix, i, R, ixvol[i])
            # 신호는 당일 종가로 계산 → 다음 날부터 적용(선견 방지)
            nav = [100.0]
            srets = []
            for i in range(MIN_HIST + 1, n):
                e = w[i - 1]
                r = e * ixr[i] + (1 - e) * rfd
                srets.append(r)
                nav.append(nav[-1] * (1 + r))
            turn = sum(abs(w[i] - w[i - 1]) for i in range(MIN_HIST + 1, n)) / max(1, (n - MIN_HIST) / 252)
            expo = sum(w[MIN_HIST:]) / max(1, n - MIN_HIST)
        else:
            # 횡단면 — 월말에만 순위를 다시 매기고 그 사이는 보유
            hold = []
            nav = [100.0]
            srets = []
            turns = 0
            for i in range(MIN_HIST + 1, n):
                if (i - 1) in me or not hold:
                    sc = []
                    for t in tickers:
                        P = px[t]
                        sid = S["sid"]
                        if sid == "x-52wh":
                            # 종가가 통째로 비는 구간이 있는 종목이 있다(부분 상장 등) — 빈 창은 건너뛴다
                            win = [x for x in P[max(0, i - 252):i] if x]
                            hi = max(win) if win else None
                            v = (P[i - 1] / hi) if (hi and P[i - 1]) else None
                        elif sid == "x-dist200":
                            m = sma(P, i - 1, 200)
                            v = (P[i - 1] / m - 1) if (m and P[i - 1]) else None
                        elif sid == "x-mom-trend":
                            m200 = sma(P, i - 1, 200)
                            if not m200 or not P[i - 1] or P[i - 1] <= m200:
                                v = None
                            else:
                                v = (ret(P, i - 1, 252) or -9) - (ret(P, i - 1, 21) or 0)
                        elif sid == "x-rev1w":
                            v = -(ret(P, i - 1, 5) or 9)
                        elif sid == "x-minvar":
                            # 완전 최적화 대신 축소추정 역분산 — 개별 분산을 시장분산 쪽으로 반씩 당긴다
                            sv = vol(R[t], i - 1, 120)
                            mv = ixvol[i - 1]
                            v = -(0.5 * sv + 0.5 * mv) if (sv and mv) else None
                        elif sid == "x-riskbudget":
                            sv = vol(R[t], i - 1, 60)
                            v = (1.0 / sv) if sv and sv > 0 else None
                        elif sid == "x-lowbeta":
                            b = beta(R[t], ixr, i - 1, 120)
                            v = -b if b is not None else None
                        elif sid == "x-snapback":
                            m200 = sma(P, i - 1, 200)
                            if not m200 or not P[i - 1] or P[i - 1] <= m200:
                                v = None
                            else:
                                rv = rsi(P, i - 1)
                                v = -rv if rv is not None else None
                        elif sid == "x-volsurge":
                            V = vlm[t]
                            m200 = sma(P, i - 1, 200)
                            if not V or not m200 or not P[i - 1] or P[i - 1] <= m200:
                                v = None
                            else:
                                a = sma(V, i - 1, 20)
                                b = sma(V, i - 1, 60)
                                v = (a / b) if (a and b and b > 0) else None
                        else:
                            v = S["fn"](t, i - 1, P, R[t], vol(R[t], i - 1, 60))
                        if v is not None and v == v:
                            sc.append((v, t))
                    sc.sort(reverse=True)
                    new = [t for _v, t in sc[:TOPN]]
                    if new:
                        turns += len(set(new) ^ set(hold)) / (2 * TOPN) if hold else 1.0
                        hold = new
                rs = [R[t][i] for t in hold if R[t][i] is not None]
                r = sum(rs) / len(rs) if rs else 0.0
                srets.append(r)
                nav.append(nav[-1] * (1 + r))
            turn = turns / max(1, (n - MIN_HIST) / 252)
            expo = 1.0

        bnav = [100.0]
        for i in range(MIN_HIST + 1, n):
            bnav.append(bnav[-1] * (1 + ixr[i]))
        d2 = dates[MIN_HIST:]
        st = ann_stats(nav, d2, rf)
        bs = ann_stats(bnav, d2, rf)
        out.append({
            "sid": S["sid"], "name": S["name"], "kind": S["kind"], "arch": S.get("arch"),
            "rule": S["rule"], "why": S["why"],
            "metrics": st, "bench": bs,
            "excess_cagr": round((st.get("cagr", 0) - bs.get("cagr", 0)), 2),
            "d_sharpe": round((st.get("sharpe") or 0) - (bs.get("sharpe") or 0), 3),
            "t": tstat(srets, ixr[MIN_HIST + 1:]),
            "turnover": round(turn, 2), "exposure": round(expo * 100, 1),
            "nav": [round(x, 2) for x in nav[::5]],
            "bnav": [round(x, 2) for x in bnav[::5]],
            "dates": d2[::5],
        })

    # ── 다중검정 임계 ────────────────────────────────────────────────
    # 규칙 N개를 같은 표본에서 돌렸다. |t|>2 라는 관례는 검정이 하나일 때 이야기다.
    # 본페로니(α=0.05/N)로 임계를 올린다 — Harvey·Liu·Zhu(2016)가 발표된 이상현상에
    # 권고한 |t|≈3.0과도 대체로 같은 자리에 온다.
    N = len(out)
    alpha = 0.05 / max(1, N)
    # 정규 근사 역함수(Acklam 근사 대신 이분법 — 정확도보다 의존성 없음이 중요하다)
    def z_of(p):
        lo, hi = 0.0, 10.0
        for _ in range(200):
            m = (lo + hi) / 2
            # Φ(m) 를 erf로
            cdf = 0.5 * (1 + math.erf(m / math.sqrt(2)))
            if 1 - cdf > p / 2:
                lo = m
            else:
                hi = m
        return round((lo + hi) / 2, 2)
    tcrit = z_of(alpha)
    for r in out:
        t = r["t"]
        if t is None:
            r["verdict"] = "판정 불가"
        elif r["d_sharpe"] <= 0:
            r["verdict"] = "열위"
        elif abs(t) >= tcrit:
            r["verdict"] = "통과 후보"
        else:
            r["verdict"] = "구별 불가"

    out.sort(key=lambda x: -(x["d_sharpe"] or -9))
    doc = {
        "note": "테크니컬 규칙을 실제로 돌린 결과. 좋은 것만 고르지 않고 돌린 규칙을 전부 싣는다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": dates[-1], "start": dates[MIN_HIST], "n_days": n - MIN_HIST,
        "n_stocks": len(tickers), "topn": TOPN,
        "bench_label": "동일가중 유니버스 매수후보유",
        "t_crit": tcrit,
        "t_crit_note": "규칙 %d개를 같은 표본에서 돌렸으므로 본페로니(α=0.05/%d)로 임계를 올렸다. "
                       "검정이 하나일 때의 관례 |t|>2 를 그대로 쓰면 우연을 발견으로 읽는다." % (N, N),
        "rf_note": "샤프는 FRED DGS3MO 월평균을 일할로 환산해 차감",
        "limits": [
            "생존편향 — 오늘의 %d종목을 과거 3년에 그대로 적용한다. 그 사이 편출된 종목이 없어 "
            "모든 수치가 실제보다 좋게 나온다. 이 저장소에 시점별 편입 이력이 없어 보정할 수 없다." % len(tickers),
            "표본이 3년(%d거래일)뿐이다. 국면 전환을 몇 번 못 겪은 구간이라, 좋은 샤프가 실력인지 "
            "구간인지 가를 수 없다." % (n - MIN_HIST),
            "비용 0(gross). 회전율이 높은 규칙일수록 실제와 벌어지므로 연 회전율을 함께 싣는다.",
            "다중검정 — 규칙 %d개를 같은 표본에서 돌렸다. 그중 최고는 우연히도 좋아 보인다. "
            "그래서 하나도 빼지 않고 전부 싣는다." % len(STRATS),
            "신호는 당일 종가로 계산해 다음 거래일부터 적용한다(선견 없음). 횡단면은 월말 리밸런스.",
        ],
        "strategies": out,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("다중검정 임계 |t| ≥ %.2f (본페로니 α=0.05/%d)" % (tcrit, N))
    import collections as _c
    print("판정:", dict(_c.Counter(r["verdict"] for r in out)))
    print("전략 %d개 · %s ~ %s (%d거래일) · %d종목 · %.0fKB"
          % (len(out), doc["start"], doc["as_of"], doc["n_days"], len(tickers),
             os.path.getsize(OUT) / 1024))
    print("벤치마크(동일가중): CAGR %.2f%% · 샤프 %s · MDD %.2f%%"
          % (bs.get("cagr", 0), bs.get("sharpe"), bs.get("mdd", 0)))
    print()
    print("%-26s %7s %7s %7s %7s %6s %6s" % ("전략", "CAGR", "샤프", "MDD", "Δ샤프", "t", "회전"))
    for r in out:
        m = r["metrics"]
        print("%-26s %7.2f %7s %7.2f %7.3f %6s %6.1f"
              % (r["name"][:24], m.get("cagr", 0), m.get("sharpe"), m.get("mdd", 0),
                 r["d_sharpe"], r["t"], r["turnover"]))
    return 0


if __name__ == "__main__":
    sys.exit(run())
