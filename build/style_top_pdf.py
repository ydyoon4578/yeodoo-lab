# -*- coding: utf-8 -*-
"""build/style_top_pdf.py — 스타일 상위 10종목 전략 PDF → data/top10_strategies.pdf

무엇을. build/style_top.py 가 '오늘 무엇을 담나'를 낸다면, 여기서는 그 규칙을 **과거로 되돌려
매월 다시 골라** 최근 1년 성과를 잰다. 요약 1쪽 + 한 쪽에 전략 두 개.

규칙 — 여섯 스타일 공통
  후보     유니버스 518종목(S&P 500 ∪ NASDAQ 100)
  선정     그 시점 점수 상위 10종목, 동일가중
  리밸런스  월말. 사이에는 표류(매수후보유)
  구간     최근 252거래일(1년)
  대조군    S&P 500(PR) · NASDAQ 100(PR) — 둘 다 가격지수
  비용     0(gross)

포트폴리오는 두 벌을 나란히 싣는다.
  · 전월말 리밸런스 — 이번 달 내내 실제로 들고 있는 명단
  · 오늘 재산출     — 같은 규칙을 오늘 다시 돌린 결과, 즉 다음 리밸런스 후보

시점 정확성.
  · 재무는 **기간종료일 + 45일**이 지난 것만 쓴다. 분기 재무는 분기가 끝난 날 바로 공개되지
    않는다. 안 자르면 없던 정보를 쓰는 것이 된다.
  · 가격은 그날 종가로 만든다.

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
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "top10_strategies.pdf")

TOPN = 10
LAG_DAYS = 45          # 분기 재무 공시 지연
WINDOW = 252           # 성과·차트 구간 — 최근 1년
MIN_NAMES = 100        # 후보가 이보다 적은 달은 그 규칙의 자료가 아직 얕은 것으로 본다
SP_WP, MSCI_WP = 10.0, 2.5
WIN = 3.0

for p in (r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf"):
    if os.path.exists(p):
        font_manager.fontManager.addfont(p)
rcParams["font.family"] = "Malgun Gothic"
rcParams["axes.unicode_minus"] = False

# 색은 사이트(index.html)의 밝은 테마를 그대로 가져온다 — 따뜻한 종이 바탕에 같은 강조색.
#   --panel #FFFDF5 · --ground #FAF7EC · --panel-2 #F3EFE1 · --line #E4DFD0
#   --ink #14181D · --ink-2 #3C444D · --muted #6A737D
#   --accent #8A6B00 · --deploy #0E8A54 · --hot #A64B3B · --champ #2C6E8F
#   --rp #7A5AA6 · --marg #B25E12
PAPER, GROUND, PANEL2 = "#FFFDF5", "#FAF7EC", "#F3EFE1"
INK, INK2, MUTED = "#14181D", "#3C444D", "#6A737D"
LINE, RULE = "#E4DFD0", "#C8C0AC"        # RULE 은 --line 을 한 단계 눌러 만든 굵은 선
POS, NEG, ACC = "#0E8A54", "#A64B3B", "#8A6B00"
CHAMP, RP, MARG = "#2C6E8F", "#7A5AA6", "#B25E12"
HEAD_BG, ZEBRA = PANEL2, GROUND
BM1, BM2 = CHAMP, RP                     # S&P 500(PR) · NASDAQ 100(PR)
SCOL = {"mom": ACC, "qual": POS, "val": NEG,
        "lowvol": CHAMP, "grow": RP, "hbeta": MARG}     # 요약 곡선용
IDXC = {"SPX": CHAMP, "NDX": RP, "공통": ACC}           # 소속 지수 구분색

X0, X1 = .058, .942                       # 본문 좌·우 경계


def idx_of(P, t):
    """그 종목이 어느 지수 소속인가 — 'SPX' 단독 · 'NDX' 단독 · '공통'(양쪽 모두)."""
    v = set((P.uni.get(t) or {}).get("idx") or [])
    if "SPX" in v and "NDX" in v:
        return "공통"
    return "NDX" if "NDX" in v else ("SPX" if "SPX" in v else "—")


def load(fn):
    p = os.path.join(DATA, fn)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def zs(d, wp):
    """원시값을 wp 백분위로 윈저화·표준화하고 z 를 ±3 으로 자른다(style_top.py 와 같은 규약).

    → (자른 z, 안 자른 z) 두 벌. 윈저화 구간 밖은 **전부 같은 값**이 되므로 자른 z 만으로는
    상위권이 통째로 동점이 된다(모멘텀이 실제로 그렇다). 순위는 자른 z 로, 동점은 안 자른 z 로
    가른다 — 안 그러면 상위 10종목이 사전순·입력순 같은 우연으로 정해진다.
    """
    ks = [k for k, v in d.items() if v is not None and v == v and abs(v) != float("inf")]
    if len(ks) < 20:
        return {}, {}
    a = np.array([d[k] for k in ks], float)
    lo, hi = np.percentile(a, wp), np.percentile(a, 100 - wp)
    aw = np.clip(a, lo, hi)
    mu, sd = float(aw.mean()), float(aw.std(ddof=1))
    if sd <= 0:
        return {}, {}
    cl = {k: float(np.clip((min(max(d[k], lo), hi) - mu) / sd, -WIN, WIN)) for k in ks}
    un = {k: float((d[k] - mu) / sd) for k in ks}
    return cl, un


def zavg(parts):
    """parts: [(자른 z, 안 자른 z), ...] → 공통 티커의 (평균, 평균) 두 벌."""
    parts = [p for p in parts if p[0]]
    if not parts:
        return {}, {}
    common = set(parts[0][0])
    for p in parts[1:]:
        common &= set(p[0])
    return ({k: float(np.mean([p[0][k] for p in parts])) for k in common},
            {k: float(np.mean([p[1][k] for p in parts])) for k in common})


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
        self.spy = self._align(A, "SPY")
        self.gspc = self._align(A, "^GSPC")     # S&P 500 가격지수(PR)
        self.ndx = self._align(A, "^NDX")       # NASDAQ 100 가격지수(PR)
        import importlib.util
        sp = importlib.util.spec_from_file_location("_tb", os.path.join(HERE, "tech_backtest.py"))
        tb = importlib.util.module_from_spec(sp); sp.loader.exec_module(tb)
        self.fx = tb.load_fund()
        # 진짜 월말만. 마지막 거래일은 리밸런스가 아니라 '오늘 재산출' 자리라 따로 둔다.
        self.me = [i for i in range(len(self.dates) - 1)
                   if self.dates[i][:7] != self.dates[i + 1][:7]]

    def _align(self, A, tk):
        """assets.json 격자를 종목 가격 격자에 맞춘다. 빈 날은 직전 값으로 채운다."""
        m = {d: p for d, p in zip(A.get("dates") or [], (A.get("px") or {}).get(tk) or [])
             if p is not None}
        out, last = [], np.nan
        for d in self.dates:
            v = m.get(d)
            if v is not None:
                last = float(v)
            out.append(last)
        return np.array(out, float)

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


def rets(a):
    return a[1:] / a[:-1] - 1.0


# ── 스타일 점수 ── 전부 (패널, 날짜인덱스) → ({티커: 점수}, {티커: 동점가르개}).
#    점수가 큰 쪽이 상위. 동점가르개는 같은 점수끼리의 순서를 정한다.
def sc_mom(P, i):
    if i < 252 * 3 + 22:
        return {}, {}
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
    d = {t: -x for t, x in v.items()}             # 낮을수록 상위
    return d, d                                   # 연속값이라 동점이 없다


def sc_hbeta(P, i):
    _, b = _vol_beta(P, i)
    return b, b


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


# ── 보유 표의 마지막 칸 ──────────────────────────────────────────────────────
# 점수를 그대로 적으면 못 읽는다. 자른 z 는 상위권이 통째로 동점이고(모멘텀), 안 자른 z 는
# 순위와 어긋난다(퀄리티에서 MA 가 그렇다 — ROE 가 압도적이라 안 자른 z 는 1등인데 D/E 때문에
# 자른 합성점수로는 10등이다). 그래서 그 스타일이 실제로 보는 값을 그 스타일의 단위로 적는다.
def d_mom(P, i, t, sc, un):
    a = P.px[t]
    if i < 21 + 252:
        return "—"
    p1, p13 = a[i - 21], a[i - 21 - 252]
    if np.isnan(p1) or np.isnan(p13) or p13 <= 0:
        return "—"
    return "%+.0f" % ((p1 / p13 - 1) * 100)


def d_qual(P, i, t, sc, un):
    ni, eq = P.ttm(t, "ni", i), P.last(t, "eq", i)
    if ni is None or not eq or eq <= 0:
        return "—"
    return "%.1f" % (ni / eq * 100)


def d_val(P, i, t, sc, un):
    p = P.px[t][i]
    eps = P.ttm(t, "eps", i)
    if eps is None or np.isnan(p):
        return "—"
    return "적자" if eps <= 0 else "%.1f" % (p / eps)


def d_grow(P, i, t, sc, un):
    rv, shs = P.asof(t, "rev", i, 16), P.asof(t, "sh", i, 16)
    for b in (12, 8, 4):
        if len(rv) > b and len(shs) > b and shs[0] > 0 and shs[b] > 0 and rv[b] != 0:
            a_, b_ = rv[0] / shs[0], rv[b] / shs[b]
            g = ((a_ / abs(b_)) ** (4.0 / b) - 1.0) if b_ > 0 else -(((a_ / abs(b_)) ** (4.0 / b)) - 1.0)
            return "%+.1f" % (g * 100)
    return "—"


# ── 스타일 정의 ─────────────────────────────────────────────────────────────
#   desc  전략 이름 바로 아래에 두 줄. 첫 줄은 '무엇을 어떻게 계산하나',
#         둘째 줄은 '그래서 어떤 종목이 담기고 언제 약한가'.
#   mlab/mfmt  보유 표의 마지막 칸. mfmt(패널, 날짜인덱스, 티커, 점수, 동점가르개) → 문자열.
STYLES = [
    ("mom", "모멘텀", "MSCI USA Momentum", sc_mom, "12M 수익률 %", d_mom,
     "최근 1개월을 뺀 6개월·12개월 수익률을 각각 3년 주간 변동성으로 나눠 위험조정 모멘텀을 만들고, 두 값의 z 를 평균한다.\n"
     "직전 1개월을 빼는 것은 단기 반전을 피하려는 것이다. 추세가 살아 있는 종목에 붙어 오래 타므로 국면이 꺾이는 순간 가장 취약하다."),
    ("qual", "퀄리티", "MSCI Quality", sc_qual, "ROE %", d_qual,
     "ROE(＋) · 부채비율 D/E(－) · 이익 변동성(－) 세 축의 z 평균. 재무는 기간종료일 + 45일이 지나 실제로 공시된 것만 쓴다.\n"
     "돈을 잘 벌고 빚이 적고 이익이 들쭉날쭉하지 않은 회사를 담는다. 하락장에 방어적인 대신 강세장 후반에는 뒤처지기 쉽다."),
    ("val", "가치", "S&P 500 Value (S&P U.S. Style)", sc_val, "PER", d_val,
     "주당순자산÷주가(B/P) · 주당순이익÷주가(E/P) · 주당매출÷주가(S/P) 의 z 평균. 원시값은 상·하위 10퍼센타일에서 윈저화한다.\n"
     "같은 자산·이익·매출을 더 싸게 사는 규칙이다. 금리 상승·경기 회복 국면에 강하고, 성장주 랠리에서는 오래 눌린다."),
    ("lowvol", "저변동", "S&P 500 Low Volatility", sc_lowvol, "변동성 %", lambda P, i, t, s, u: "%.1f" % (-s),
     "최근 252거래일 일간수익률의 표준편차가 가장 작은 10종목. 점수는 연율 변동성의 부호를 뒤집은 값이다.\n"
     "유틸리티·필수소비 같은 방어 업종에 쏠리기 쉽다. 절대수익보다 샤프와 MDD 로 판단해야 하는 규칙이다."),
    ("grow", "성장", "S&P 500 Growth (S&P U.S. Style)", sc_grow, "3Y 매출성장 %", d_grow,
     "3년 주당매출 성장률 · 3년 주당이익 변화÷주가 · 12개월 모멘텀의 z 평균. 매출과 이익이 함께 늘어나는 속도를 본다.\n"
     "모멘텀과 담는 종목이 겹치지만 출발점이 가격이 아니라 펀더멘털이다. 실적 추정이 꺾이는 국면에서 낙폭이 크다."),
    ("hbeta", "고베타", "S&P 500 High Beta", sc_hbeta, "베타", lambda P, i, t, s, u: "%.2f" % s,
     "최근 252거래일 일간수익률을 S&P 500 에 회귀했을 때 베타가 가장 큰 10종목. 공분산÷시장분산으로 직접 계산한다.\n"
     "시장이 오르면 더 오르고 내리면 더 내리는 증폭 장치다. 초과수익 규칙이라기보다 방향성 베팅이라 MDD 를 같이 봐야 한다."),
]

SECS = {"Information Technology": "IT", "Health Care": "헬스", "Financials": "금융",
        "Consumer Discretionary": "경소", "Consumer Staples": "필소",
        "Communication Services": "커뮤", "Industrials": "산업", "Energy": "에너",
        "Utilities": "유틸", "Real Estate": "부동", "Materials": "소재"}


# ── 백테스트 ────────────────────────────────────────────────────────────────
def backtest(P, fn):
    """최근 1년. 월말 리밸런스 · 상위 10 동일가중 · 사이에는 표류.

    구간 시작 시점의 보유는 그 이전 마지막 월말 선정이다. 그래야 창 첫날부터 진짜 포트폴리오다.
    """
    end = len(P.dates) - 1
    start = max(0, end - WINDOW)
    rebal = [i for i in P.me if start < i < end]

    cache = {}

    def pick(i):
        """그 시점 상위 10종목 → [(티커, 점수, 동점가르개)]. 자료가 얕으면 None."""
        if i in cache:
            return cache[i]
        s, tie = fn(P, i)
        out = None
        if len(s) >= MIN_NAMES:
            ok = [t for t in s if t in P.px and not np.isnan(P.px[t][i])]
            ok.sort(key=lambda t: (-s[t], -tie.get(t, 0.0), t))
            if len(ok) >= TOPN:
                out = [(t, s[t], tie.get(t, s[t])) for t in ok[:TOPN]]
        cache[i] = out
        return out

    init = None                                   # 창 시작 시점에 들고 있던 명단
    for i in [j for j in P.me if j <= start][::-1][:14]:
        init = pick(i)
        if init:
            init_i = i
            break
    if not init:
        return None
    picks = {}
    for i in rebal:
        p = pick(i)
        if p:
            picks[i] = p                          # 못 고른 달은 리밸런스를 거르고 그대로 표류한다
    today = pick(end)
    if not today:
        return None

    nav = np.ones(end - start + 1)
    w = {t: 1.0 / TOPN for t, _s, _u in init}
    for k, i in enumerate(range(start + 1, end + 1), start=1):
        g, tot = 0.0, 0.0
        for t, x in w.items():
            a = P.px[t]
            if np.isnan(a[i]) or np.isnan(a[i - 1]) or a[i - 1] <= 0:
                continue
            g += x * (a[i] / a[i - 1]); tot += x
        nav[k] = nav[k - 1] * (g / tot if tot > 0 else 1.0)
        nw, s2 = {}, 0.0                          # 표류 — 비중이 그달 수익률만큼 자란다
        for t, x in w.items():
            a = P.px[t]
            r = (a[i] / a[i - 1]) if (not np.isnan(a[i]) and not np.isnan(a[i - 1])
                                      and a[i - 1] > 0) else 1.0
            nw[t] = x * r; s2 += x * r
        if s2 > 0:
            w = {t: v / s2 for t, v in nw.items()}
        if i in picks:                            # 월말에 다시 고른다
            w = {t: 1.0 / TOPN for t, _s, _u in picks[i]}

    prev_i = max(picks) if picks else init_i
    return {"nav": nav, "start": start, "end": end,
            "prev_i": prev_i, "prev": picks.get(prev_i) or init,
            "today_i": end, "today": today,
            "n_rebal": len(picks), "init_i": init_i}


def bench_nav(P, a, start, end):
    """지수 가격을 창 시작 = 1 로 되돌린 일별 곡선."""
    base = a[start]
    if np.isnan(base) or base <= 0:
        return None
    out = a[start:end + 1] / base
    return np.where(np.isnan(out), 1.0, out)


def metrics(nav):
    r = rets(nav)
    yrs = len(r) / 252.0
    sd = float(np.std(r, ddof=1))
    return {"ret": (nav[-1] ** (1 / yrs) - 1) * 100 if yrs > 0 and nav[-1] > 0 else None,
            "vol": sd * np.sqrt(252) * 100,
            "sharpe": (float(np.mean(r)) / sd * np.sqrt(252)) if sd > 0 else None,
            "mdd": float(np.min(nav / np.maximum.accumulate(nav) - 1)) * 100}


TRAIL = [("1주", 5), ("1개월", 21), ("3개월", 63), ("6개월", 126), ("1년", 252)]


def trails(nav, dates, start):
    out = {}
    for lab, n in TRAIL:
        out[lab] = (nav[-1] / nav[-1 - n] - 1) * 100 if len(nav) > n else None
    y0 = dates[-1][:4] + "-01-01"                 # YTD — 전년 마지막 거래일 대비
    j = None
    for k in range(len(nav)):
        if dates[start + k] >= y0:
            j = k
            break
    out["YTD"] = ((nav[-1] / nav[j - 1] - 1) * 100) if (j and j >= 1) else None
    return out


def monthly(nav, dates, start):
    """달마다의 수익률 %. 첫 달은 창이 열린 날부터라 부분 월이다(표에 * 로 적는다)."""
    lastk = {}
    for k in range(len(nav)):
        lastk[dates[start + k][:7]] = k
    ms = sorted(lastk)
    out, prev = {}, 0
    for m in ms:
        k = lastk[m]
        out[m] = (nav[k] / nav[prev] - 1) * 100 if k > prev else None
        prev = k
    return ms, out


# ── 그리기 도구 ─────────────────────────────────────────────────────────────
def tx(fig, x, y, s, **kw):
    kw.setdefault("color", INK); kw.setdefault("fontsize", 8)
    kw.setdefault("va", "top"); kw.setdefault("ha", "left")
    return fig.text(x, y, s, **kw)


def hline(fig, x0, x1, y, color=LINE, lw=.7):
    fig.add_artist(Line2D([x0, x1], [y, y], color=color, lw=lw, transform=fig.transFigure,
                          zorder=3))


def vline(fig, x, y0, y1, color=LINE, lw=.6):
    fig.add_artist(Line2D([x, x], [y0, y1], color=color, lw=lw, transform=fig.transFigure,
                          zorder=3))


def box(fig, x, y, w, h, fc, ec="none", lw=0, z=0):
    fig.add_artist(Rectangle((x, y), w, h, transform=fig.transFigure, facecolor=fc,
                             edgecolor=ec, lw=lw, zorder=z))


def table(fig, x0, y_top, widths, header, rows, *, row_h=.0148, fs=7.2, hfs=6.8,
          aligns=None, cell_color=None, cell_weight=None, vgrid=True, zebra=False,
          label_color=INK):
    """머리글 + 본문을 선까지 그린 표. 반환은 표 아래쪽 y.

    widths  칸 너비(그림 비율) 목록 · aligns  'l'/'r'/'c' 목록
    cell_color(r, c) · cell_weight(r, c)  칸별 색·굵기를 정하는 콜백(없으면 기본)
    """
    n = len(widths)
    aligns = aligns or (["l"] + ["r"] * (n - 1))
    xs, acc = [], x0
    for w in widths:
        xs.append(acc); acc += w
    tot = acc - x0
    nrow = len(rows)
    y_head = y_top - row_h
    y_bot = y_head - nrow * row_h
    pad = .0045

    box(fig, x0, y_head, tot, row_h, HEAD_BG, z=0)
    if zebra:
        for r in range(nrow):
            if r % 2 == 1:
                box(fig, x0, y_head - (r + 1) * row_h, tot, row_h, ZEBRA, z=0)

    def put(cx, w, y, s, align, **kw):
        if align == "r":
            tx(fig, cx + w - pad, y, s, ha="right", va="center", **kw)
        elif align == "c":
            tx(fig, cx + w / 2, y, s, ha="center", va="center", **kw)
        else:
            tx(fig, cx + pad, y, s, ha="left", va="center", **kw)

    for c, h in enumerate(header):
        put(xs[c], widths[c], y_head + row_h / 2, h, aligns[c], fontsize=hfs, color=MUTED)
    for r, row in enumerate(rows):
        yc = y_head - r * row_h - row_h / 2
        for c, v in enumerate(row):
            col = cell_color(r, c) if cell_color else (label_color if c == 0 else INK)
            wt = cell_weight(r, c) if cell_weight else "normal"
            put(xs[c], widths[c], yc, v, aligns[c], fontsize=fs, color=col, weight=wt)

    hline(fig, x0, x0 + tot, y_top, RULE, .8)                 # 표 위
    hline(fig, x0, x0 + tot, y_head, RULE, .8)                # 머리글 아래
    for r in range(1, nrow):
        hline(fig, x0, x0 + tot, y_head - r * row_h, LINE, .5)
    hline(fig, x0, x0 + tot, y_bot, RULE, .8)                 # 표 아래
    if vgrid:
        for c in range(n + 1):
            vline(fig, x0 + sum(widths[:c]), y_bot, y_top, LINE, .5)
    else:
        vline(fig, x0, y_bot, y_top, RULE, .8)
        vline(fig, x0 + tot, y_bot, y_top, RULE, .8)
    return y_bot


def num(v, d=2, sign=True):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return ("%+." + str(d) + "f") % v if sign else ("%." + str(d) + "f") % v


def footer(fig, page, total):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .026, "스타일 상위 10종목 전략 · 지수 SPX = S&P 500 단독 · "
                      "NDX = NASDAQ 100 단독 · 공통 = 양쪽 모두 · 대조군은 가격지수(PR) · 비용 0",
       fontsize=6.4, color=MUTED)
    tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
       fontsize=6.4, color=MUTED, ha="right")


def new_page():
    fig = plt.figure(figsize=(8.27, 11.69))       # A4
    fig.patch.set_facecolor(PAPER)
    return fig


# ── 전략 한 블록(반 쪽) ──────────────────────────────────────────────────────
BLOCK_TOPS = (.960, .502)


def draw_block(fig, P, top, S, R):
    key, label, ref, _fn, mlab, mfmt, desc = S
    d0, d1 = P.dates[R["start"]], P.dates[R["end"]]
    nav = R["nav"]
    gn = bench_nav(P, P.gspc, R["start"], R["end"])
    nn = bench_nav(P, P.ndx, R["start"], R["end"])
    m, mg, mn = metrics(nav), metrics(gn), metrics(nn)
    tr, tg, tn = (trails(nav, P.dates, R["start"]), trails(gn, P.dates, R["start"]),
                  trails(nn, P.dates, R["start"]))

    y = top
    tx(fig, X0, y, label, fontsize=15.5, weight="bold")
    tx(fig, X1, y + .0015, ref, fontsize=8, color=ACC, ha="right")
    tx(fig, X1, y - .0100, "%s ~ %s · 월말 %d회 리밸런스 · 상위 10종목 동일가중 · 비용 0"
       % (d0, d1, R["n_rebal"]), fontsize=6.6, color=MUTED, ha="right")
    y -= .0205
    hline(fig, X0, X1, y, RULE, .9)
    y -= .008
    tx(fig, X0, y, desc, fontsize=7.1, color=INK2, linespacing=1.58)
    y -= .0285

    # ① 최근 1년 성과 ─ 왼쪽 위
    LW = .432
    tx(fig, X0, y, "최근 1년 성과", fontsize=9.2, weight="bold")
    t_top = y - .0135
    rows = []
    for lab, k, d, sg in (("수익률 %", "ret", 2, True), ("변동성 %", "vol", 2, False),
                          ("샤프", "sharpe", 2, True), ("MDD %", "mdd", 2, True)):
        rows.append([lab, num(m.get(k), d, sg), num(mg.get(k), d, sg), num(mn.get(k), d, sg)])

    def cc(r, c):
        if c == 0:
            return INK
        if c == 1:
            v = rows[r][1]
            if r in (0, 2) and v != "—":
                return POS if not v.startswith("-") else NEG
            return INK
        return MUTED

    y1 = table(fig, X0, t_top, [.132, .102, .099, .099], ["지표", "전략", "S&P 500 PR", "NDX PR"],
               rows, row_h=.0140, cell_color=cc,
               cell_weight=lambda r, c: "bold" if c == 1 else "normal")

    # ② 기간별 수익률 ─ 왼쪽 아래
    y2 = y1 - .015
    tx(fig, X0, y2, "기간별 수익률 %", fontsize=9.2, weight="bold")
    labs = [l for l, _ in TRAIL] + ["YTD"]
    prow = [["전략"] + [num(tr.get(l), 1) for l in labs],
            ["S&P 500 PR"] + [num(tg.get(l), 1) for l in labs],
            ["NDX PR"] + [num(tn.get(l), 1) for l in labs],
            ["초과(vs S&P)"] + [("—" if (tr.get(l) is None or tg.get(l) is None)
                                 else num(tr[l] - tg[l], 1)) for l in labs]]

    def cc2(r, c):
        if c == 0:
            return INK if r in (0, 3) else MUTED
        v = prow[r][c]
        if r in (0, 3) and v != "—":
            return POS if not v.startswith("-") else NEG
        return MUTED

    y3 = table(fig, X0, y2 - .0132, [.117] + [.0525] * 6, [""] + labs, prow,
               row_h=.0140, cell_color=cc2,
               cell_weight=lambda r, c: "bold" if (r == 0 and c > 0) else "normal")

    # ③ 누적 곡선 ─ 오른쪽. 표 두 개가 차지한 높이를 그대로 쓴다.
    cx0, cw = X0 + LW + .052, X1 - (X0 + LW + .052)
    ch_top, ch_bot = t_top, y3
    ax = fig.add_axes([cx0, ch_bot, cw, ch_top - ch_bot])
    ax.set_facecolor(PAPER)
    xi = np.arange(len(nav))
    ax.axhline(100, color=LINE, lw=.6)
    ax.plot(xi, gn * 100, color=BM1, lw=1.0, ls="--", label="S&P 500(PR)")
    ax.plot(xi, nn * 100, color=BM2, lw=1.0, ls=":", label="NASDAQ 100(PR)")
    ax.plot(xi, nav * 100, color=ACC, lw=1.7, label="전략")
    ax.set_ylabel("누적 (시작 = 100)", fontsize=6.8, color=MUTED, labelpad=2)
    ticks, seen = [], set()
    for k in range(len(xi)):
        mth = P.dates[R["start"] + k][:7]
        if mth not in seen:
            seen.add(mth); ticks.append(k)
    ticks = ticks[::2]
    ax.set_xticks(ticks)
    ax.set_xticklabels([P.dates[R["start"] + k][2:7] for k in ticks])
    ax.set_xlim(0, len(xi) - 1)
    ax.tick_params(labelsize=6.3, colors=MUTED, length=2, pad=1.5)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.grid(True, color=LINE, lw=.4, alpha=.65)
    ax.set_axisbelow(True)
    h, l = ax.get_legend_handles_labels()           # 전략을 맨 앞으로 — 그린 순서는 겹침 때문이다
    ax.legend(h[2:] + h[:2], l[2:] + l[:2], fontsize=6.3, frameon=False, loc="upper left",
              handlelength=1.8, borderpad=.1, labelspacing=.25)

    # ④ 포트폴리오 두 벌
    yp = y3 - .018
    tx(fig, X0, yp, "포트폴리오", fontsize=9.2, weight="bold")
    yt = yp - .0142
    prev_t = [t for t, _s, _u in R["prev"]]
    now_t = [t for t, _s, _u in R["today"]]
    ps, ns = set(prev_t), set(now_t)

    def pf(x0, at_i, title, sub, items, other, mark_new):
        tx(fig, x0, yt, title, fontsize=7.5, weight="bold")
        tx(fig, x0 + .428, yt, sub, fontsize=6.5, color=MUTED, ha="right")
        rows_, flags = [], []
        for k, (t, sc, un) in enumerate(items):
            u = P.uni.get(t) or {}
            nm = (u.get("name") or "")[:24]
            sec = SECS.get(u.get("sector") or "", "")
            new = t not in other
            flags.append(new)
            rows_.append(["%d" % (k + 1), ("＋" if (new and mark_new) else "") + t, nm, sec,
                          idx_of(P, t), mfmt(P, at_i, t, sc, un)])

        def c3(r, c):
            if c == 4:                       # 소속 지수는 그 자체가 범주라 색을 따로 쓴다
                return IDXC.get(rows_[r][4], MUTED)
            if c == 0:
                return MUTED
            if flags[r]:
                return POS if mark_new else NEG
            return INK if c in (1, 2) else MUTED

        return table(fig, x0, yt - .0122, [.026, .058, .180, .044, .036, .084],
                     ["#", "티커", "종목명", "섹터", "지수", mlab], rows_,
                     row_h=.0128, fs=6.9, hfs=6.4,
                     aligns=["c", "l", "l", "l", "l", "r"], cell_color=c3,
                     cell_weight=lambda r, c: "bold" if c in (1, 4) else "normal",
                     zebra=True)

    pf(X0, R["prev_i"], "전월말 리밸런스", "%s · 지금 보유 중" % P.dates[R["prev_i"]],
       R["prev"], ns, False)
    pf(X0 + .456, R["today_i"], "오늘 재산출", "%s · 다음 리밸런스 후보"
       % P.dates[R["today_i"]], R["today"], ps, True)
    keep = len(ps & ns)
    tx(fig, X1, yp + .0012, "교체 %d종목 · 유지 %d종목 · ＋ 신규편입 · 붉은 종목은 이번 재산출에서 빠진 자리"
       % (TOPN - keep, keep), fontsize=6.4, color=MUTED, ha="right")


# ── 요약 쪽 ────────────────────────────────────────────────────────────────
def draw_summary(fig, P, res, order, total):
    d0, d1 = P.dates[res[order[0]]["start"]], P.dates[res[order[0]]["end"]]
    tx(fig, X0, .962, "스타일 상위 10종목 전략", fontsize=23, weight="bold")
    tx(fig, X0, .928, "최근 1년 요약", fontsize=10, color=ACC)
    tx(fig, X1, .932, "%s ~ %s" % (d0, d1), fontsize=8.5, color=MUTED, ha="right")
    hline(fig, X0, X1, .916, RULE, .9)

    y = .895
    tx(fig, X0, y, "최근 1년 성과", fontsize=11.5, weight="bold")
    rows, colors_ = [], []
    for key in order:
        S = next(s for s in STYLES if s[0] == key)
        R = res[key]
        m = metrics(R["nav"])
        mg = metrics(bench_nav(P, P.gspc, R["start"], R["end"]))
        mn = metrics(bench_nav(P, P.ndx, R["start"], R["end"]))
        keep = len(set(t for t, _s, _u in R["prev"]) & set(t for t, _s, _u in R["today"]))
        ix = [idx_of(P, t) for t, _s, _u in R["today"]]
        rows.append([S[1], S[2].split(" (")[0], num(m["ret"], 2), num(m["vol"], 2, False),
                     num(m["sharpe"], 2), num(m["mdd"], 2),
                     num(m["ret"] - mg["ret"], 2), num(m["ret"] - mn["ret"], 2),
                     "%d" % (TOPN - keep),
                     "%d·%d·%d" % (ix.count("SPX"), ix.count("공통"), ix.count("NDX"))])
        colors_.append(m["ret"])
    R0 = res[order[0]]
    for lab, a in (("S&P 500 PR", P.gspc), ("NASDAQ 100 PR", P.ndx)):
        mb = metrics(bench_nav(P, a, R0["start"], R0["end"]))
        rows.append([lab, "대조군 · 가격지수", num(mb["ret"], 2), num(mb["vol"], 2, False),
                     num(mb["sharpe"], 2), num(mb["mdd"], 2), "—", "—", "—", "—"])
    nS = len(order)

    def cc(r, c):
        if r >= nS:
            return MUTED
        if c == 0:
            return INK
        if c == 1:
            return MUTED
        v = rows[r][c]
        if c in (2, 4, 6, 7) and v != "—":
            return POS if not v.startswith("-") else NEG
        return INK

    ytab = table(fig, X0, y - .017,
                 [.118, .152, .084, .072, .062, .072, .082, .082, .046, .090],
                 ["전략", "참조 지수", "1년 수익률 %", "변동성 %", "샤프", "MDD %",
                  "vs S&P %p", "vs NDX %p", "교체", "SPX·공통·NDX"],
                 rows, row_h=.0175, fs=7.6, hfs=6.6,
                 aligns=["l", "l", "r", "r", "r", "r", "r", "r", "c", "c"], cell_color=cc,
                 cell_weight=lambda r, c: "bold" if (c == 0 or c == 2) and r < nS else "normal",
                 zebra=True)
    tx(fig, X0, ytab - .0085,
       "'교체'는 전월말 명단과 오늘 재산출 명단의 차이다 — 이 규칙이 달마다 손을 얼마나 대는지를 뜻한다. "
       "맨 오른쪽은 오늘 담은 10종목이 어느 지수 소속인지의 구성이다.",
       fontsize=6.6, color=MUTED)

    # ② 월별 수익률 — 어느 달에 무엇이 먹혔나. 표의 1년 숫자 하나로는 안 보이는 것이다.
    names = [r[0] for r in rows]
    navs = ([res[k]["nav"] for k in order]
            + [bench_nav(P, P.gspc, R0["start"], R0["end"]),
               bench_nav(P, P.ndx, R0["start"], R0["end"])])
    ms, _ = monthly(navs[0], P.dates, R0["start"])
    grid = np.array([[monthly(n, P.dates, R0["start"])[1].get(m, np.nan) for m in ms]
                     for n in navs], float)

    yh = ytab - .034
    tx(fig, X0, yh, "월별 수익률 %", fontsize=11.5, weight="bold")
    tx(fig, X1, yh + .001, "* 는 구간이 열린 %s 부터의 부분 월" % P.dates[R0["start"]],
       fontsize=6.6, color=MUTED, ha="right")
    hm_h = .0145 * len(names) + .016
    lw_ = .085                                       # 행 이름 칸
    ax = fig.add_axes([X0 + lw_, yh - .014 - hm_h, X1 - X0 - lw_, hm_h])
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list(       # 중앙은 종이색 — 사이트 톤에 맞춘다
        "rg", ["#8E3F2F", "#BE8878", "#EADAD2", PAPER, "#D9E9DF", "#7CB697", "#0E7A4A"])
    cmap.set_bad(PANEL2)
    lim = float(np.nanpercentile(np.abs(grid), 92)) or 1.0
    ax.imshow(np.ma.masked_invalid(grid), cmap=cmap, vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(len(ms)))
    ax.set_xticklabels([("%s*" % m[2:] if j == 0 else m[2:]) for j, m in enumerate(ms)])
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7)
    ax.tick_params(labelsize=6.4, colors=MUTED, length=0)
    ax.set_xticks(np.arange(-.5, len(ms), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(names), 1), minor=True)
    ax.grid(which="minor", color="white", lw=1.1)
    ax.tick_params(which="minor", length=0)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    for r in range(grid.shape[0]):
        for c in range(grid.shape[1]):
            v = grid[r, c]
            if v != v:
                continue
            ax.text(c, r, "%+.1f" % v, ha="center", va="center", fontsize=5.9,
                    color=("white" if abs(v) > lim * .62 else INK),
                    weight=("bold" if r < nS else "normal"))

    # ③ 1년 누적 곡선 — 일곱 전략과 두 지수를 한 판에.
    yc = yh - .014 - hm_h - .030
    tx(fig, X0, yc, "1년 누적 곡선 · 시작 = 100", fontsize=11.5, weight="bold")
    ch_h = yc - .014 - .072
    ax2 = fig.add_axes([X0 + .048, yc - .014 - ch_h, X1 - X0 - .058, ch_h])
    ax2.set_facecolor(PAPER)
    xi = np.arange(len(navs[0]))
    ax2.axhline(100, color=LINE, lw=.6)
    for lab, a, col, ls, lw in (("S&P 500(PR)", navs[nS], INK, "--", 1.1),
                                ("NASDAQ 100(PR)", navs[nS + 1], MUTED, ":", 1.1)):
        ax2.plot(xi, a * 100, color=col, ls=ls, lw=lw, label=lab, zorder=2)
    for k in order:
        ax2.plot(xi, res[k]["nav"] * 100, color=SCOL[k], lw=1.35, zorder=3,
                 label=next(s[1] for s in STYLES if s[0] == k))
    ax2.set_xlim(0, len(xi) - 1)
    ticks, seen = [], set()
    for k in range(len(xi)):
        mth = P.dates[R0["start"] + k][:7]
        if mth not in seen:
            seen.add(mth); ticks.append(k)
    if len(ticks) > 1 and ticks[1] - ticks[0] < 8:
        ticks = ticks[1:]          # 창 첫 달은 며칠뿐이라 다음 눈금과 겹친다
    ax2.set_xticks(ticks)
    ax2.set_xticklabels([P.dates[R0["start"] + k][2:7] for k in ticks])
    ax2.tick_params(labelsize=6.4, colors=MUTED, length=2, pad=1.5)
    for sp in ax2.spines.values():
        sp.set_color(LINE)
    ax2.grid(True, color=LINE, lw=.4, alpha=.65)
    ax2.set_axisbelow(True)
    h, l = ax2.get_legend_handles_labels()
    ax2.legend(h[2:] + h[:2], l[2:] + l[:2], fontsize=6.4, frameon=False, ncol=3,
               loc="upper left", handlelength=1.9, columnspacing=1.2, labelspacing=.3)
    footer(fig, 1, total)


def main() -> int:
    P = Panel()
    print("유니버스 %d · 일별 %d일(%s~%s) · 월말 %d회"
          % (len(P.uni), len(P.dates), P.dates[0], P.dates[-1], len(P.me)))

    res, order = {}, []
    for S in STYLES:
        key, label = S[0], S[1]
        R = backtest(P, S[3])
        if not R:
            print("  %-5s 건너뜀 — 자료 부족" % label)
            continue
        res[key] = R
        order.append(key)
        m = metrics(R["nav"])
        mg = metrics(bench_nav(P, P.gspc, R["start"], R["end"]))
        mn = metrics(bench_nav(P, P.ndx, R["start"], R["end"]))
        print("  %-5s %s~%s · 1년 %+7.2f%% (S&P %+6.2f · NDX %+6.2f) · 샤프 %5.2f · MDD %7.2f%%"
              % (label, P.dates[R["start"]], P.dates[R["end"]], m["ret"], mg["ret"], mn["ret"],
                 m["sharpe"], m["mdd"]))
    if not order:
        print("낼 수 있는 전략이 없다"); return 1

    order.sort(key=lambda k: -metrics(res[k]["nav"])["ret"])       # 요약은 1년 수익률 순
    detail = [S for S in STYLES if S[0] in res]                    # 본문은 정의 순서 그대로
    total = 1 + (len(detail) + 1) // 2

    with PdfPages(OUT) as pdf:
        fig = new_page()
        draw_summary(fig, P, res, order, total)
        pdf.savefig(fig); plt.close(fig)

        for pi in range(0, len(detail), 2):
            fig = new_page()
            for bi, S in enumerate(detail[pi:pi + 2]):
                draw_block(fig, P, BLOCK_TOPS[bi], S, res[S[0]])
            if pi + 1 < len(detail):
                hline(fig, X0, X1, .524, LINE, .8)
            footer(fig, 2 + pi // 2, total)
            pdf.savefig(fig); plt.close(fig)

        d = pdf.infodict()
        d["Title"] = "스타일 상위 10종목 전략(최근 1년)"
    print("→ %s · %d쪽 · %dKB" % (OUT, total, os.path.getsize(OUT) // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
