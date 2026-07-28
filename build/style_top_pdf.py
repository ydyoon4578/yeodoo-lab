# -*- coding: utf-8 -*-
"""build/style_top_pdf.py — 스타일 상위 10종목 전략 7쪽 PDF → data/top10_strategies.pdf

무엇을. build/style_top.py 가 '오늘 무엇을 담나'를 낸다면, 여기서는 그 규칙을 **과거로 되돌려
매월 다시 골라** 성과를 잰다. 스타일마다 한 쪽씩 일곱 쪽.

규칙 — 일곱 스타일 공통
  후보   유니버스 518종목(S&P 500 ∪ NASDAQ 100)
  선정   그 시점 점수 상위 10종목, 동일가중
  리밸런스 월말. 사이에는 표류(매수후보유)
  대조군 ① 같은 풀 동일가중(월 리밸) ② SPY 총수익
  비용   0(gross)

시점 정확성 — 이 스크립트가 지키는 것과 못 지키는 것.
  · 재무는 **기간종료일 + 45일**이 지난 것만 쓴다. 13F 와 같은 이유로, 분기 재무는 그 분기가
    끝난 날 바로 공개되지 않는다. 안 자르면 없던 정보를 쓰는 것이 된다.
  · 가격·시가총액은 그날 종가와 그때까지 공시된 주식수로 만든다.
  · ⚠ **유니버스는 오늘 스냅샷이다.** 편입·편출 이력이 없어 '지금 살아남아 지수에 있는 518종목'만
    과거로 소급한다. 방향은 위쪽이고, 대조군(같은 풀 동일가중)도 같은 편향을 갖는다 —
    초과수익에서 상당 부분 상쇄되지만 전부는 아니다. 작은 종목을 고르는 규칙일수록 덜 상쇄된다.
  · 구간이 스타일마다 다르다. 재무가 필요한 규칙(퀄리티·가치·성장)과 시점 주식수가 필요한
    규칙(중소형)은 자료가 짧아 늦게 시작한다. 쪽마다 자기 구간을 적는다.

  python build/style_top_pdf.py
"""
from __future__ import annotations
import io, json, os, sys, datetime as dt

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, rcParams
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "top10_strategies.pdf")

TOPN = 10
LAG_DAYS = 45          # 분기 재무 공시 지연
MIN_MONTHS = 36        # 이보다 짧으면 성과를 내지 않는다
MIN_NAMES = 100        # 후보가 이보다 적은 달은 그 규칙의 시작 전으로 본다
SP_WP, MSCI_WP = 10.0, 2.5
WIN = 3.0

for p in (r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf"):
    if os.path.exists(p):
        font_manager.fontManager.addfont(p)
rcParams["font.family"] = "Malgun Gothic"
rcParams["axes.unicode_minus"] = False

INK, MUTED, LINE = "#14181D", "#6A737D", "#D7DBE0"
POS, NEG, ACC = "#0E8A54", "#A64B3B", "#8A6B00"


def load(fn):
    p = os.path.join(DATA, fn)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def zs(d, wp):
    """원시값을 wp 백분위로 자른 뒤 표준화하고 z 를 ±3 으로 자른다(style_top.py 와 같은 규약)."""
    ks = [k for k, v in d.items() if v is not None and v == v and abs(v) != float("inf")]
    if len(ks) < 20:
        return {}
    a = np.array([d[k] for k in ks], float)
    lo, hi = np.percentile(a, wp), np.percentile(a, 100 - wp)
    aw = np.clip(a, lo, hi)
    mu, sd = float(aw.mean()), float(aw.std(ddof=1))
    if sd <= 0:
        return {}
    return {k: float(np.clip((min(max(d[k], lo), hi) - mu) / sd, -WIN, WIN)) for k in ks}


def zavg(parts):
    if not parts:
        return {}
    common = set(parts[0])
    for p in parts[1:]:
        common &= set(p)
    return {k: float(np.mean([p[k] for p in parts])) for k in common}


class Panel:
    """가격·재무를 시점으로 잘라 쓰는 얇은 층."""

    def __init__(self):
        st = load("stocks.json")
        self.dates = st["pxd_dates"]
        self.uni = {s["t"]: s for s in st["stocks"]}
        self.di = {d: i for i, d in enumerate(self.dates)}
        self.px = {}
        for t in self.uni:
            p = os.path.join(DATA, "sd", "%s.json" % t)
            if not os.path.exists(p):
                continue
            v = json.load(io.open(p, encoding="utf-8")).get("pxd")
            if v and len(v) == len(self.dates):
                self.px[t] = np.array([x if x is not None else np.nan for x in v], float)
        A = load("assets.json") or {}
        m = {d: p for d, p in zip(A.get("dates") or [], (A.get("px") or {}).get("SPY") or [])
             if p is not None}
        self.spy = np.array([m.get(d, np.nan) for d in self.dates], float)
        import importlib.util
        sp = importlib.util.spec_from_file_location("_tb", os.path.join(HERE, "tech_backtest.py"))
        tb = importlib.util.module_from_spec(sp); sp.loader.exec_module(tb)
        self.fx = tb.load_fund()
        # 월말 인덱스
        self.me = [i for i in range(len(self.dates) - 1)
                   if self.dates[i][:7] != self.dates[i + 1][:7]] + [len(self.dates) - 1]

    def asof(self, t, key, i, n=1):
        """기간종료일 + LAG_DAYS 가 dates[i] 이전인 관측을 최신 n개. 없으면 []."""
        cut = (dt.date.fromisoformat(self.dates[i]) - dt.timedelta(days=LAG_DAYS)).isoformat()
        ser = (self.fx.get(t) or {}).get(key) or []
        out = [v for d, v in ser if d <= cut][:n]
        return out

    def ttm(self, t, key, i):
        v = self.asof(t, key, i, 4)
        return sum(v) if len(v) == 4 else None

    def last(self, t, key, i):
        v = self.asof(t, key, i, 1)
        return v[0] if v else None

    def mcap(self, t, i):
        sh = self.last(t, "sh", i)
        p = self.px.get(t, np.array([np.nan]))[i] if t in self.px else np.nan
        return None if (sh is None or np.isnan(p)) else sh * p


def rets(a):
    return a[1:] / a[:-1] - 1.0


# ── 스타일 점수 ── 전부 (패널, 날짜인덱스) → {티커: 점수}. 점수가 큰 쪽이 상위다.
def sc_mom(P, i):
    if i < 252 * 3 + 22:
        return {}
    m6, m12 = {}, {}
    for t, a in P.px.items():
        w = a[max(0, i - 252 * 3):i + 1][::5]
        w = w[~np.isnan(w)]
        if len(w) < 100:
            continue
        sig = float(np.std(rets(w), ddof=1)) * np.sqrt(52)
        p1, p7, p13 = a[i - 21], a[i - 21 - 126], a[i - 21 - 252]
        if sig <= 0 or np.isnan(p1) or np.isnan(p7) or np.isnan(p13) or p7 <= 0 or p13 <= 0:
            continue
        m6[t] = (p1 / p7 - 1) / sig
        m12[t] = (p1 / p13 - 1) / sig
    return zavg([zs(m6, MSCI_WP), zs(m12, MSCI_WP)])


def _vol_beta(P, i):
    v, b = {}, {}
    mr = rets(P.spy[max(0, i - 252):i + 1])
    for t, a in P.px.items():
        r = rets(a[max(0, i - 252):i + 1])
        ok = ~(np.isnan(r) | np.isnan(mr))
        if ok.sum() < 200:
            continue
        v[t] = float(np.std(r[ok], ddof=1)) * np.sqrt(252) * 100
        vm = float(np.var(mr[ok], ddof=1))
        if vm > 0:
            b[t] = float(np.cov(r[ok], mr[ok], ddof=1)[0, 1] / vm)
    return v, b


def sc_lowvol(P, i):
    v, _ = _vol_beta(P, i)
    return {t: -x for t, x in v.items()}          # 낮을수록 상위


def sc_hbeta(P, i):
    _, b = _vol_beta(P, i)
    return b


def sc_size(P, i):
    return {t: -m for t in P.uni for m in [P.mcap(t, i)] if m}   # 작을수록 상위


def sc_qual(P, i):
    roe, de, ev = {}, {}, {}
    for t in P.uni:
        ni, eq, li = P.ttm(t, "ni", i), P.last(t, "eq", i), P.last(t, "liab", i)
        if ni is not None and eq and eq > 0:
            roe[t] = ni / eq * 100
        if li is not None and eq and eq > 0:
            de[t] = -(li / eq * 100)
        eps = P.asof(t, "eps", i, 20)
        g = [(eps[k] - eps[k + 4]) / abs(eps[k + 4])
             for k in range(len(eps) - 4) if eps[k + 4] and abs(eps[k + 4]) > 1e-9]
        if len(g) >= 8:
            ev[t] = -float(np.std(np.array(g, float), ddof=1))
    return zavg([zs(roe, MSCI_WP), zs(de, MSCI_WP), zs(ev, MSCI_WP)])


def sc_val(P, i):
    """S&P U.S. Style 의 가치 3요소 — B/P · E/P · S/P."""
    bp, ep, spr = {}, {}, {}
    for t in P.uni:
        p = P.px.get(t, np.array([np.nan]))[i] if t in P.px else np.nan
        sh, eq = P.last(t, "sh", i), P.last(t, "eq", i)
        eps, rev = P.ttm(t, "eps", i), P.ttm(t, "rev", i)
        if np.isnan(p) or p <= 0 or not sh or sh <= 0:
            continue
        if eq is not None:
            bp[t] = (eq / sh) / p
        if eps is not None:
            ep[t] = eps / p
        if rev is not None:
            spr[t] = (rev / sh) / p
    return zavg([zs(bp, SP_WP), zs(ep, SP_WP), zs(spr, SP_WP)])


def sc_grow(P, i):
    """S&P U.S. Style 의 성장 3요소 — 3년 주당매출 성장 · 3년 EPS 변화÷주가 · 12개월 모멘텀."""
    sps, epc, mom = {}, {}, {}
    for t in P.uni:
        p = P.px.get(t, np.array([np.nan]))[i] if t in P.px else np.nan
        if np.isnan(p) or p <= 0:
            continue
        rv, shs, es = P.asof(t, "rev", i, 16), P.asof(t, "sh", i, 16), P.asof(t, "eps", i, 16)
        for b in (12, 8, 4):
            if len(rv) > b and len(shs) > b and shs[0] > 0 and shs[b] > 0 and rv[b] != 0:
                a_, b_ = rv[0] / shs[0], rv[b] / shs[b]
                g = ((a_ / abs(b_)) ** (4.0 / b) - 1.0) if b_ > 0 else -(((a_ / abs(b_)) ** (4.0 / b)) - 1.0)
                sps[t] = g
                break
        else:
            sps[t] = 0.0
        for b in (12, 8, 4):
            if len(es) > b:
                epc[t] = (es[0] - es[b]) * 4 / p
                break
        else:
            epc[t] = 0.0
        a = P.px[t]
        if i >= 252 and not np.isnan(a[i - 252]) and a[i - 252] > 0:
            mom[t] = a[i] / a[i - 252] - 1.0
    return zavg([zs(sps, SP_WP), zs(epc, SP_WP), zs(mom, SP_WP)])


STYLES = [
    ("mom", "모멘텀", "MSCI USA Momentum", sc_mom,
     "최근 1개월을 뺀 6개월·12개월 수익률을 3년 주간변동성으로 나눈 뒤 z 평균."),
    ("qual", "퀄리티", "MSCI Quality", sc_qual,
     "ROE(+) · 부채비율 D/E(−) · 이익변동성(−)의 z 평균. 전부 그때까지 공시된 재무로."),
    ("val", "가치", "S&P 500 Value (S&P U.S. Style)", sc_val,
     "주당순자산÷주가 · 주당이익÷주가 · 주당매출÷주가 의 z 평균(원시값 90퍼센타일 윈저화)."),
    ("lowvol", "저변동", "S&P 500 Low Volatility", sc_lowvol,
     "최근 252거래일 일간수익률의 표준편차가 가장 작은 10종목."),
    ("grow", "성장", "S&P 500 Growth (S&P U.S. Style)", sc_grow,
     "3년 주당이익 변화÷주가 · 3년 주당매출 성장률 · 12개월 모멘텀의 z 평균."),
    ("hbeta", "고베타", "S&P 500 High Beta", sc_hbeta,
     "최근 252거래일 일간수익률의 S&P 500 대비 베타가 가장 큰 10종목."),
    ("size", "중소형", "MSCI USA Size", sc_size,
     "그 시점 시가총액(공시 주식수 × 종가)이 가장 작은 10종목."),
]


def backtest(P, fn):
    """월말 리밸런스 · 상위 10 동일가중 · 사이에는 표류. 반환 dict 또는 None."""
    picks = {}
    for i in P.me:
        s = fn(P, i)
        if len(s) < MIN_NAMES:
            continue                     # 그 규칙의 자료가 아직 얕다 — 시작 전으로 본다
        top = [t for t, _ in sorted(s.items(), key=lambda kv: -kv[1])[:TOPN]]
        top = [t for t in top if t in P.px and not np.isnan(P.px[t][i])]
        if len(top) < TOPN:
            continue
        picks[i] = top
    if not picks:
        return None
    start = min(picks)
    nav = np.ones(len(P.dates) - start)
    w = {t: 1.0 / TOPN for t in picks[start]}
    for k, i in enumerate(range(start + 1, len(P.dates)), start=1):
        g, tot = 0.0, 0.0
        for t, x in w.items():
            a = P.px[t]
            if np.isnan(a[i]) or np.isnan(a[i - 1]) or a[i - 1] <= 0:
                continue
            g += x * (a[i] / a[i - 1]); tot += x
        nav[k] = nav[k - 1] * (g / tot if tot > 0 else 1.0)
        nw, s2 = {}, 0.0                 # 표류 — 비중이 그달 수익률만큼 자란다
        for t, x in w.items():
            a = P.px[t]
            r = (a[i] / a[i - 1]) if (not np.isnan(a[i]) and not np.isnan(a[i - 1])
                                      and a[i - 1] > 0) else 1.0
            nw[t] = x * r; s2 += x * r
        if s2 > 0:
            w = {t: v / s2 for t, v in nw.items()}
        if i in picks:                   # 월말에 다시 고른다
            w = {t: 1.0 / TOPN for t in picks[i]}
    ms = sorted(picks)
    return {"nav": nav, "start": start, "picks": picks, "last_i": ms[-1],
            "last": picks[ms[-1]], "prev": picks[ms[-2]] if len(ms) > 1 else [],
            "n_months": len(ms)}


def size_pct(P, picks):
    """보유 종목이 그 시점 유니버스에서 몇 번째 크기였나(백분위 중앙값).

    왜 재는가 — 유니버스에 편출 이력이 없다. 지수에서 빠지는 건 대개 작아진 회사인데 그 이력이
    없으면, **작은 쪽을 고르는 규칙은 '그때 작았고 지금까지 살아남아 지수에 있는' 종목만 담는다.**
    실측(2026-07-28): 중소형 규칙의 2019-11 편입이 ROL·MSTR·CMG·DECK·ANET·TTD·CSGP 였고
    보유 시총 백분위 중앙값이 1.0% 였다. 그 CAGR 은 전략이 아니라 편향이다 — 그래서 잰다.
    """
    out = []
    for i in sorted(picks):
        mc = {t: v for t in P.uni for v in [P.mcap(t, i)] if v}
        if len(mc) < 100:
            continue
        arr = np.array(sorted(mc.values()))
        for t in picks[i]:
            if t in mc:
                out.append(float((arr < mc[t]).mean()) * 100)
    return float(np.median(out)) if out else None


SIZE_WARN = 33.0        # 보유 시총 백분위 중앙값이 이보다 낮으면 소형 편향으로 표시한다


def bench_nav(P, start, kind):
    """대조군 일별 NAV. kind='ew'(풀 동일가중) 또는 'spy'(총수익 — 조정종가라 배당 포함)."""
    nav = np.ones(len(P.dates) - start)
    for k, i in enumerate(range(start + 1, len(P.dates)), start=1):
        if kind == "spy":
            p0, p1 = P.spy[i - 1], P.spy[i]
            r = (p1 / p0 - 1.0) if (not np.isnan(p0) and not np.isnan(p1) and p0 > 0) else 0.0
        else:
            rs = [a[i] / a[i - 1] - 1.0 for a in P.px.values()
                  if not np.isnan(a[i]) and not np.isnan(a[i - 1]) and a[i - 1] > 0]
            r = float(np.mean(rs)) if rs else 0.0
        nav[k] = nav[k - 1] * (1 + r)
    return nav


def metrics(nav):
    r = rets(nav)
    yrs = len(r) / 252.0
    sd = float(np.std(r, ddof=1))
    return {"cagr": (nav[-1] ** (1 / yrs) - 1) * 100 if yrs > 0 and nav[-1] > 0 else None,
            "vol": sd * np.sqrt(252) * 100,
            "sharpe": (float(np.mean(r)) / sd * np.sqrt(252)) if sd > 0 else None,
            "mdd": float(np.min(nav / np.maximum.accumulate(nav) - 1)) * 100}


TRAIL = [("1주", 5), ("1개월", 21), ("3개월", 63), ("6개월", 126), ("1년", 252)]


def trails(nav, dates, start):
    out = {}
    for lab, n in TRAIL:
        out[lab] = (nav[-1] / nav[-1 - n] - 1) * 100 if len(nav) > n else None
    y0 = dates[-1][:4] + "-01-01"                      # YTD — 전년 마지막 거래일 대비
    j = None
    for k in range(len(nav)):
        if dates[start + k] >= y0:
            j = k
            break
    out["YTD"] = ((nav[-1] / nav[j - 1] - 1) * 100) if (j and j >= 1) else None
    return out


# ── PDF 한 쪽 ───────────────────────────────────────────────────────────────
PAGE = [1]
SECS = {"Information Technology": "IT", "Health Care": "헬스케어", "Financials": "금융",
        "Consumer Discretionary": "경기소비", "Consumer Staples": "필수소비",
        "Communication Services": "커뮤니케이션", "Industrials": "산업재", "Energy": "에너지",
        "Utilities": "유틸리티", "Real Estate": "부동산", "Materials": "소재"}
# 다섯 줄로 줄였다 — 아홉 줄이면 마지막 줄이 푸터를 덮는다(실제로 그랬다).
LIM = ("· 유니버스가 오늘 스냅샷이다 — 편입·편출 이력이 없어 '지금 살아남아 지수에 있는 518종목'을 과거로\n"
       "  소급한다. 방향은 위쪽이고 대조군도 같은 편향을 갖지만 초과수익에서 전부 상쇄되지는 않는다.\n"
       "· 재무는 기간종료일 + 45일이 지난 것만 썼다. 구간이 스타일마다 다른 이유가 이것이다.\n"
       "· 거래비용·세금 0(gross) · 월말 전량 재구성 · 일곱 규칙을 같은 표본에 돌린 다중검정.\n"
       "· 이 랩은 팩터 모멘텀을 '자기 유니버스 대비 구별 불가'로 기각했다 — 상태 정리이고 투자자문이 아니다.")


def page(pdf, P, sd, res, sb, tb, label, ref, rule, spct):
    d0, d1 = P.dates[res["start"]], P.dates[-1]
    m, mb, mt = metrics(res["nav"]), metrics(sb), metrics(tb)
    tr = trails(res["nav"], P.dates, res["start"])
    trb = trails(sb, P.dates, res["start"])
    trt = trails(tb, P.dates, res["start"])

    fig = plt.figure(figsize=(8.27, 11.69))         # A4
    fig.patch.set_facecolor("white")

    def tx(x, y, s, **kw):
        kw.setdefault("color", INK); kw.setdefault("fontsize", 9)
        kw.setdefault("va", "top"); kw.setdefault("ha", "left")
        fig.text(x, y, s, **kw)

    def rule_line(y):
        fig.add_artist(plt.Line2D([.07, .93], [y, y], color=LINE, lw=.8,
                                  transform=fig.transFigure))

    tx(.07, .968, label, fontsize=22, weight="bold")
    tx(.07, .937, ref, fontsize=9.5, color=ACC)
    tx(.93, .968, "%d / %d" % (PAGE[0], len(STYLES)), fontsize=9.5, color=MUTED, ha="right")
    tx(.07, .918, rule, fontsize=8.6, color=MUTED)
    tx(.07, .900, "백테스트 %s ~ %s · 월말 %d회 리밸런스 · 상위 10종목 동일가중 · 비용 0"
       % (d0, d1, res["n_months"]), fontsize=8.4, color=MUTED)
    rule_line(.892)

    # 소형 편향 — 있으면 성과보다 **먼저** 말한다. 아래 숫자를 그대로 읽으면 안 되는 쪽이다.
    ybox = .878
    if spct is not None and spct < SIZE_WARN:
        fig.patches.append(plt.Rectangle((.07, .800), .86, .072, transform=fig.transFigure,
                                         facecolor="#FBEFE9", edgecolor=NEG, lw=.9, zorder=0))
        tx(.083, .866, "※ 이 규칙의 CAGR 은 전략이 아니라 편향이다", fontsize=9.6,
           weight="bold", color=NEG)
        tx(.083, .848,
           ("보유 종목이 그 시점 유니버스에서 하위 %.1f%% 크기였다(중앙값). 이 유니버스엔 편출 이력이 없어\n"
            "작은 쪽을 고르면 '그때 작았고 지금까지 살아남아 지수에 있는' 종목만 담게 된다 — 예: 2019년\n"
            "편입 종목에 MSTR·DECK·ANET·TTD 가 들어 있다. 아래 수익률은 그 결과이지 규칙의 성과가 아니다."
            ) % spct, fontsize=7.5, color=INK, linespacing=1.55)
        ybox = .786

    # ① 성과
    tx(.07, ybox, "성과", fontsize=11.5, weight="bold")
    xs = [.07, .42, .64, .86]
    y = ybox - .020
    tx(xs[0], y, "지표", fontsize=8.2, color=MUTED)
    for j, cl in enumerate(("전략", "같은 풀 동일가중", "SPY 총수익")):
        tx(xs[j + 1], y, cl, fontsize=8.2, color=MUTED, ha="right")
    for lab, k in (("CAGR %", "cagr"), ("변동성 %", "vol"), ("샤프", "sharpe"), ("MDD %", "mdd")):
        y -= .0195
        tx(xs[0], y, lab, fontsize=9)
        for j, src in enumerate((m, mb, mt)):
            v = src.get(k)
            s = "—" if v is None else ("%.2f" % v if k in ("vol", "sharpe") else "%+.2f" % v)
            tx(xs[j + 1], y, s, fontsize=9, ha="right",
               color=(INK if j == 0 else MUTED), weight=("bold" if j == 0 else "normal"))

    # ② 기간별 수익률
    y -= .040
    tx(.07, y, "기간별 수익률 %", fontsize=11.5, weight="bold")
    labs = [l for l, _ in TRAIL] + ["YTD"]
    xw = [.19 + .125 * k for k in range(len(labs))]
    y -= .020
    for k, l in enumerate(labs):
        tx(xw[k], y, l, fontsize=8.2, color=MUTED, ha="right")
    for nm, src, bold in (("전략", tr, True), ("같은 풀 EW", trb, False), ("SPY", trt, False)):
        y -= .0195
        tx(.07, y, nm, fontsize=8.6, color=MUTED)
        for k, l in enumerate(labs):
            v = src.get(l)
            if v is None:
                col = MUTED
            elif bold:
                col = POS if v > 0 else NEG
            else:
                col = MUTED
            tx(xw[k], y, "—" if v is None else "%+.1f" % v, fontsize=8.8, ha="right",
               color=col, weight=("bold" if bold else "normal"))

    # ③ 누적 곡선
    # 차트 위치는 위 블록이 끝난 자리에서 잡는다. 고정하면 경고 박스가 붙은 쪽에서 표를 덮는다
    # (실제로 중소형 쪽이 그랬다 — 박스가 위를 밀어 내렸는데 차트만 제자리였다).
    ch_h = .128 if ybox < .87 else .162          # 박스가 있으면 낮게 — 안 줄이면 보유 목록이 각주를 덮는다
    ch_top = y - .030
    ax = fig.add_axes([.10, ch_top - ch_h, .83, ch_h])
    xi = np.arange(len(res["nav"]))
    ax.plot(xi, res["nav"], color=ACC, lw=1.6, label="전략")
    ax.plot(xi, sb, color=MUTED, lw=1.0, label="같은 풀 동일가중")
    ax.plot(xi, tb, color="#2C6E8F", lw=1.0, ls="--", label="SPY 총수익")
    ax.set_yscale("log")
    # Malgun Gothic 에 U+2212(−)가 없다. 로그축 포매터가 그걸 쓰므로 평문 형식으로 바꾼다.
    from matplotlib.ticker import FuncFormatter, LogLocator
    ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: ("%g" % v)))
    ax.set_ylabel("누적(로그)", fontsize=8, color=MUTED)
    n = len(xi)
    ticks = list(range(0, n, max(1, n // 6)))
    ax.set_xticks(ticks)
    ax.set_xticklabels([P.dates[res["start"] + k][:7] for k in ticks])
    ax.tick_params(labelsize=7.5, colors=MUTED)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.grid(True, color=LINE, lw=.4, alpha=.6)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")

    # ④ 현재 보유
    yh = ch_top - ch_h - .055                    # 차트 아래에서 이어 간다
    tx(.07, yh, "지금 담는 10종목", fontsize=11.5, weight="bold")
    tx(.07, yh - .018, "월말 %s 기준 · ＋ 는 직전 리밸런스에 없던 신규편입"
       % P.dates[res["last_i"]], fontsize=8.2, color=MUTED)
    cur, prev = res["last"], set(res["prev"])
    dmap = {x["t"]: x for x in ((sd or {}).get("top") or [])}
    y = yh - .038
    for k, t in enumerate(cur):
        info = dmap.get(t) or {}
        nm = (info.get("n") or (P.uni.get(t) or {}).get("name") or "")[:28]
        sec = SECS.get(info.get("s") or (P.uni.get(t) or {}).get("sector") or "", "")
        # 지표는 **두 개까지**. 셋을 적으면 A4 오른쪽에서 잘려 뜻이 사라진다(잘린 채로 한 번 냈다).
        _d = [(kk, vv) for kk, vv in (info.get("d") or {}).items() if vv is not None][:2]
        det = " · ".join("%s %s" % (kk, vv) for kk, vv in _d)[:36]
        tx(.07, y, "%2d" % (k + 1), fontsize=8.2, color=MUTED)
        tx(.105, y, ("＋" if t not in prev else "   ") + t, fontsize=9.4, weight="bold")
        tx(.215, y, nm, fontsize=8.3)
        tx(.52, y, sec, fontsize=8.1, color=MUTED)
        tx(.63, y, det, fontsize=7.2, color=MUTED)
        y -= .0166
    gone = [t for t in res["prev"] if t not in cur]
    if gone:
        tx(.105, y - .004, "이탈  " + " ".join(gone), fontsize=8, color=NEG)

    # ⑤ 한계
    rule_line(.132)
    tx(.07, .121, "이 숫자를 읽기 전에", fontsize=9.2, weight="bold")
    tx(.07, .104, LIM, fontsize=6.9, color=MUTED, linespacing=1.45)
    tx(.07, .022, "여두 전략 랩", fontsize=7, color=MUTED)
    tx(.93, .022, "생성 %s" % dt.datetime.now().strftime("%Y-%m-%d"),
       fontsize=7, color=MUTED, ha="right")
    pdf.savefig(fig)
    plt.close(fig)
    PAGE[0] += 1


def main() -> int:
    P = Panel()
    print("유니버스 %d · 일별 %d일(%s~%s) · 월말 %d회"
          % (len(P.uni), len(P.dates), P.dates[0], P.dates[-1], len(P.me)))
    ST = {s["key"]: s for s in ((load("style_top.json") or {}).get("styles") or [])}
    made = 0
    with PdfPages(OUT) as pdf:
        for key, label, ref, fn, rule in STYLES:
            res = backtest(P, fn)
            if not res or res["n_months"] < MIN_MONTHS:
                print("  %-5s 건너뜀 — 표본 부족" % label)
                continue
            sb = bench_nav(P, res["start"], "ew")
            tb = bench_nav(P, res["start"], "spy")
            spct = size_pct(P, res["picks"])
            page(pdf, P, ST.get(key), res, sb, tb, label, ref, rule, spct)
            m, mbb, mtt = metrics(res["nav"]), metrics(sb), metrics(tb)
            print("  %-5s %s~%s %3d개월 · CAGR %7.2f%% (풀 %5.2f · SPY %5.2f) · 샤프 %.2f "
                  "· MDD %7.2f%% · 보유 시총 백분위 %s%s"
                  % (label, P.dates[res["start"]][:7], P.dates[-1][:7], res["n_months"],
                     m["cagr"], mbb["cagr"], mtt["cagr"], m["sharpe"], m["mdd"],
                     "—" if spct is None else "%.1f%%" % spct,
                     "  ※ 소형 편향" if (spct is not None and spct < SIZE_WARN) else ""))
            made += 1
        d = pdf.infodict()
        d["Title"] = "여두 전략 랩 — 스타일 상위 10종목 전략"
        d["Author"] = "여두 전략 랩"
    print("→ %s · %d쪽 · %dKB" % (OUT, made, os.path.getsize(OUT) // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
