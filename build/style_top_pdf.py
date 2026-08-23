# -*- coding: utf-8 -*-
"""build/style_top_pdf.py — 스타일 상위 10종목 전략 PDF → data/style_strategies.pdf

무엇을. build/style_top.py 가 '오늘 무엇을 담나'를 낸다면, 여기서는 그 규칙을 **과거로 되돌려
매월 다시 골라** 최근 1년 성과를 잰다. 요약 1쪽 + 한 쪽에 전략 두 개.

규칙 — 여섯 스타일 공통
  후보     유니버스 518종목(S&P 500 ∪ NASDAQ 100)
  선정     그 시점 점수 상위 10종목, 동일가중
  리밸런스  월말. 사이에는 표류(매수후보유)
  구간     최근 1년 — 월말에서 열어 온전한 12개월
  대조군    S&P 500(PR) · NASDAQ 100(PR) — 둘 다 가격지수
  비용     0(gross)

포트폴리오는 두 벌을 나란히 싣는다.
  · 전월말 기준 — 이번 달 내내 실제로 들고 있는 명단
  · 금일 기준   — 같은 규칙을 오늘 다시 돌린 결과, 즉 다음 리밸런스 후보

시점 정확성 — **재무는 시점, 유니버스는 아니다.** 이 구분을 흐리면 안 된다.
  · 재무는 **기간종료일 + 45일**이 지난 것만 쓴다(Panel.asof). 분기 재무는 분기가 끝난 날
    바로 공개되지 않는다. 안 자르면 없던 정보를 쓰는 것이 된다.
  · 가격은 그날 종가로 만든다.
  · 🚨 **유니버스는 오늘의 518종목을 과거로 소급한다 = 생존편향.** 이 랩에는 선정 시점
    멤버십(data/index_history.json, 위키 과거 리비전, 2014-06~ 월말)이 있고
    이 창을 100% 덮는데도 여기서 읽지 않는다. 읽는 곳은 build/pit_backtest.py 하나이고
    거기엔 마스크가 있다(:242 `if t not in pool: continue`). 여기엔 없다.
    2026-07-29 실측: 창 시작(2025-07-31) 멤버 517종 중 **29종이 오늘 유니버스에 없다**
    (4종은 티커 개명이라 실질 이탈 25종). 창 전체 합집합 550종 중 32종. 편향은 창 앞부분에
    몰려 있다(2025-07 29종 → 2026-06 0종).
  · 🚨 배선만 하면 되는 것도 아니다. 종목 축은 매 갱신마다 **능동적으로 잘린다** —
    refresh_stocks.py:1447-1449 가 오늘 유니버스에 없는 data/sd/*.json 을 지운다.
    편출 29종 가격은 19종만 _pit_px_cache.json 에 있고, **재무는 0/29** 다(data/fx 는 전부
    오늘의 유니버스). 그래서 모멘텀·저변동·고베타는 오늘 저장소 파일만으로 PIT 화가 가능하지만
    퀄리티·가치·성장은 시점별 재무가 없어 불가하다 — pit_backtest.py 가 가격 규칙 16종만
    다루는 이유가 같다.

## ⚠ 사이트(style_top.py)와 종목이 갈리는 스타일이 있다 — 버그가 아니다

여섯 중 셋(모멘텀·저변동·고베타)은 마지막 날 상위 10이 사이트와 **정확히 같다**.
나머지 셋(퀄리티·가치·성장)은 7/10 만 겹치는데, 원인이 둘이고 **둘 다 이 문서가 백테스트
이기 때문에 생기는 필연**이다.

  ① 데이터 출처. 사이트는 stocks.json 의 **벤더 비율**(fund.roe·pb·tpe·ps)을 그대로 쓴다.
     그 값은 **오늘치만** 있어서 과거 시점으로 되돌릴 수 없다 — 그래서 이 문서는 SEC 재무에서
     직접 만든다(ROE=TTM순이익/자기자본, B/P=주당순자산/주가 …).
     P/B 는 두 출처가 거의 같다(배수 1.00~1.06). ROE 는 **레벨이 다르지만 순위는 대체로 같다** —
        스피어만 0.91, 피어슨 0.628(461종목). 피어슨이 낮은 것은 자기자본이 거의 없는 몇 종목
        때문이다(IT 1119% · CL 1941%). 스타일은 z 로 순위를 매기고 윈저화가 극단을 자르므로
        **판정에 쓰이는 것은 순위 쪽**이다.
     ⚠ 분모 정의는 **같아졌다**(2026-07-29 사용자 결정 — avg_eq()). 야후도 여기도 평균
        자기자본이고, 그것이 교과서 정의다.
        🚨 2026-08-05 — 이 자리에 "야후는 평균, 여기서는 최신 분기"라는 **옛 설명이 남아
          있었다.** 정의를 바꾼 커밋(64b460b0)의 바로 앞 커밋(7034fc74)이 이 머리말을
          손댔는데, 정작 정의가 바뀐 사실은 반영하지 않았다 — 코드는 고치고 설명은 안 고친
          전형이다. 아래 배율(1.21 · 0.85)은 **교체 전 '최신 분기'판의 값**이므로 지금
          코드의 성질이 아니다. 남기는 이유는 왜 바꿨는지의 근거이기 때문이다.
          바꿀 때의 기준도 그대로 남긴다 — 성과(퀄리티 1년 +9.64% → +25.85%)를 보고 고르면
          그게 곧 과적합이므로, 정의 근거로만 결정했다.
  ② 45일 지연. 사이트는 최신 보고치를 그대로 쓰고 여기서는 45일이 지난 것만 쓴다.
     성장은 지연을 0 으로 두면 7/10 → 9/10 이 되어 이 몫이 확인된다.

→ 두 문서가 같은 종목을 가리키게 만들려면 벤더 비율을 시점별로 보관해야 한다. 그 전에는
  **이 차이를 없애려 하지 말 것** — 없애는 방법은 백테스트에 오늘 값을 쓰는 것뿐이다.

  python build/style_top_pdf.py
"""
from __future__ import annotations
import io, json, os, sys, datetime as dt

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# matplotlib 은 **그릴 때만** 필요하다. 계산(백테스트 → data/style_*.json)에는 numpy 와
# 표준라이브러리뿐이라, 없는 기계에서도 --json 은 돌아야 한다. 러너(ubuntu)에 이것을 깔지
# 않으려고 세운 벽이다 — 깔면 한글 폰트까지 같이 얹어야 하고, 그러면 JSON 한 줄 뽑자고
# CI 에 폰트 패키지를 물리게 된다. 실패는 **그리려 할 때** 크게 낸다(new_page 참조).
try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager, rcParams
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    HAVE_MPL = True
except Exception as _e:                     # noqa: BLE001 — 무엇이 없든 계산은 계속한다
    HAVE_MPL, _MPL_ERR = False, str(_e)
    font_manager = rcParams = Line2D = Rectangle = plt = PdfPages = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "style_strategies.pdf")

TOPN = 10
LAG_DAYS = 45          # 분기 재무 공시 지연(10-Q 마감 40일 기준)
# 연간 재무 공시 지연. 10-K 마감은 회계연도 종료 후 60~75일이라 45일로는 아직 세상에 없는
# 수치를 쓰게 된다. 연간(a) 버킷을 탈 수 있는 경로(Panel.ttm12)는 전부 이 값을 쓴다.
ANN_LAG_DAYS = 90
WINDOW = 252           # 성과·차트 구간 — 최근 1년
# 🚨 홈 「기간별 수익률」의 샤프만 **5년**으로 잰다(사용자 요청 2026-08-12).
#   위 WINDOW 는 안 건드린다 — 그 값은 스타일 랩 본편(PDF·style.html·수익률 7칸)의 창이라
#   같이 늘리면 화면 전체가 다른 것을 말하게 된다. 그래서 같은 코드를 창만 바꿔 한 번 더 돌린다.
# ⚠ 한 열에 두 창이 섞이면 안 되므로 ETF 행과 지수 방법론 행을 **같은 5년 창**으로 함께 잰다.
# ⚠ 1260(=5년)이 아니라 1290 이다. 창 시작을 **월말로 스냅**하므로 1260 을 그대로 두면
#   실제 길이가 1245일로 줄어 5년 칸이 통째로 빈다(실측). 여유를 두고, 아래에서 정확히
#   1260일(3년은 756일)을 뒤로 본다.
WINDOW5 = 1290
# 홈 표 ETF 행에 샤프를 적는 대상. 1년·5년 두 곳에서 같은 목록을 써야 한 열이 성립한다 —
# 손으로 두 번 적으면 조용히 갈린다.
ETF_SHARPE_TK = ("SPY", "QQQ", "DIA", "IWM",
                 # 스타일 8종(2026-08-13 정리). 홈 표의 그 묶음과 **같은 목록**이어야 한다 —
                 #   이 열이 그 묶음의 정렬 기준이라, 여기 없는 줄은 맨 밑에 깔린다.
                 "SPMO", "IVW", "IVE", "QUAL", "SPLV", "SCHD", "SDY", "RSP")
MIN_NAMES = 100        # 후보가 이보다 적은 달은 그 규칙의 자료가 아직 얕은 것으로 본다
SP_WP, MSCI_WP = 10.0, 2.5
WIN = 3.0

# 한글 폰트 — Windows(맑은 고딕)에서 만들던 문서라 mac/리눅스에도 같은 꼴이 나오게 고른다.
#   ⚠ 전에는 rcParams 에 "Malgun Gothic" 을 그냥 박아 뒀다. 그 폰트가 없는 기계(mac·리눅스·CI)
#     에서 돌리면 matplotlib 이 조용히 대체 폰트로 떨어지고 **한글이 전부 두부(□)로 나온다.**
#     경고는 findfont 한 줄뿐이라 로그를 안 보면 모른 채 배포된다(실제로 그렇게 한 번 나갔다).
#     그래서 후보를 훑어 고르고, 하나도 없으면 그리지 말고 멈춘다.
#     ⚠ 폰트가 없을 때 **여기서** 멈추면 안 된다. 이 모듈은 계산 전용(--json)으로도 불리고
#       다른 PDF 생성기 넷이 판형·색 정본으로 import 한다 — import 시점에 죽이면 그 전부가
#       폰트 없는 기계에서 못 돌아간다. 그래서 여기서는 고르기만 하고, 실제로 못 그리는 순간
#       (new_page)에 크게 실패한다. '조용히 두부로 배포'는 여전히 막는다.
KFONT = None
if HAVE_MPL:
    for _p in (r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf",
               "/System/Library/Fonts/AppleSDGothicNeo.ttc",
               "/Library/Fonts/NanumGothic.ttf",
               "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"):
        if os.path.exists(_p):
            try: font_manager.fontManager.addfont(_p)
            except Exception: pass
    KFONT = next((n for n in ("Malgun Gothic", "Apple SD Gothic Neo", "NanumGothic",
                              "Nanum Gothic", "Noto Sans CJK KR")
                  if n in {f.name for f in font_manager.fontManager.ttflist}), None)
    if KFONT:
        rcParams["font.family"] = KFONT
        rcParams["axes.unicode_minus"] = False


def require_draw():
    """그리기에 필요한 것이 갖춰졌는지 — 갖춰지지 않았으면 여기서 크게 죽는다."""
    if not HAVE_MPL:
        raise SystemExit("matplotlib 이 없다(%s) — 그림 없이 JSON 만 뽑으려면 --json 을 쓴다." % _MPL_ERR)
    if not KFONT:
        raise SystemExit("한글 폰트를 찾지 못했다 — 맑은 고딕·애플 SD 고딕·나눔고딕 중 하나가 필요하다. "
                         "없이 그리면 문서 전체가 두부(□)로 나온다.")

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

# 요약 쪽 제목 — 이 모듈을 import 해 쓰는 다른 문서가 갈아 끼운다(기본값은 이 문서 것).
TITLE = "스타일 상위 10종목 전략"
SUBTITLE = "최근 1년 요약"


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


def load_ccy():
    """티커 → 재무제표 보고통화. data/fx 태그의 단위(u)에서 읽는다.

    ⚠ 왜 필요한가 — data/fx 는 원문서 통화를 그대로 싣는다. 실측 3종이 EUR 이다
      (ASML · CCEP · FER). 주가는 USD 이므로 '재무 흐름 ÷ 주가×주식수' 로 수익률을 만드는
      규칙(자사주·FCF·주주환원)에서 EUR 분자를 USD 분모로 나누게 되고, 그 종목만 조용히
      1.1배쯤 어긋난다. 배당수익률도 dps 가 EUR/shares 라 같은 문제다.
      환율 이력을 들일 수는 없으니 **그 종목을 뺀다** — 셋을 섞느니 세 자리를 비우는 편이 낫다.
      (z 로 표준화하는 기존 스타일들은 비율·주가 기반이라 이 문제를 타지 않는다.)
    """
    out = {}
    d = os.path.join(DATA, "fx")
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            j = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (j.get("tags") or {}).values():
            u = (v or {}).get("u") or ""
            if u and u != "shares":
                out[j.get("t") or fn[:-5]] = u.split("/")[0]
                break
    return out


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
        self.A = A                              # ETF 샤프를 같은 창으로 재려고 들고 있는다
        self.spy = self._align(A, "SPY")
        self.gspc = self._align(A, "^GSPC")     # S&P 500 가격지수(PR)
        self.ndx = self._align(A, "^NDX")       # NASDAQ 100 가격지수(PR)
        import importlib.util
        sp = importlib.util.spec_from_file_location("_tb", os.path.join(HERE, "tech_backtest.py"))
        tb = importlib.util.module_from_spec(sp); sp.loader.exec_module(tb)
        self.fx = tb.load_fund()
        self.tb = tb                      # ttm2(주기 판정)를 빌려 쓴다 — ttm12 참조
        self.ccy = load_ccy()
        # 진짜 월말만. 마지막 거래일은 리밸런스가 아니라 '금일 기준' 자리라 따로 둔다.
        self.me = [i for i in range(len(self.dates) - 1)
                   if self.dates[i][:7] != self.dates[i + 1][:7]]

    def usd(self, t):
        """재무제표가 달러로 적혀 있나. 금액÷시가총액 규칙은 아니면 그 종목을 뺀다(load_ccy)."""
        return self.ccy.get(t, "USD") == "USD"

    def ttm12(self, t, key, i, ann=None, lag=None):
        """진짜 12개월치. **관측 4개를 그냥 더하면 안 된다** — 현금흐름 계열(cfo·capex·bb)은
        10-Q 가 YTD 누적이라 q 버킷에 Q1 만 남고, 그러면 '최근 4개 합'이 실제의 1/4 이 된다
        (tech_backtest.ttm2 독스트링의 🚨 · 전수 비율 중앙 bb 0.27 · cfo 0.19).
        그 주기 판정을 여기서 다시 짜지 않고 그 함수를 그대로 부른다.

        🚨 지연 기본값이 **90일**(ANN_LAG_DAYS)이다. 이 파일의 LAG_DAYS 45일이 아니다.
          45일은 10-Q 마감(대형가속신고자 40일)에 맞춘 값인데, 이 경로는 연간(a) 버킷으로
          떨어질 수 있고 **10-K 마감은 회계연도 종료 후 60~75일**이다. 45일을 쓰면 아직
          제출되지 않은 연간 수치를 그 시점에 알았다고 가정하게 된다 — 룩어헤드다.
          실측으로 그 차이가 작지 않았다: 잉여현금흐름 규칙의 1년 수익률이 45일에서
          +101.61%(샤프 3.59 · MDD -9.4%)였다. 분기 재무만 쓰는 기존 여섯 스타일은
          LAG_DAYS 를 그대로 쓴다 — 그쪽은 연간 버킷을 타지 않는다."""
        f = self.fx.get(t) or {}
        return self.tb.ttm2(f.get(key) or [], (f.get(ann) if ann else None),
                            self.dates[i], ANN_LAG_DAYS if lag is None else lag)

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
        # 🚨 3년 = 756거래일이므로 i-755 부터다. i-756 으로 잡으면 757개가 되고,
        #   [::5] 가 5개씩 건너뛰며 **표본이 하루 앞당겨져 오늘이 창에서 빠진다.**
        #   그 한 칸 차이가 sigma 를 바꾸고, 모멘텀 상위는 윈저화로 통째로 동점인 구간이라
        #   순위가 뒤집힌다 — 실측: 이것 때문에 사이트에는 TER 이, PDF 에는 KLAC 이 있었다.
        #   고치면 두 문서의 상위 10이 정확히 같아진다.
        w = a[max(0, i - 252 * 3 + 1):i + 1][::5]
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


def avg_eq(P, t, i):
    """ROE 의 분모 — **평균 자기자본**. 분자가 TTM(4분기)이므로 기초·기말의 평균이다.

    교과서 정의가 이것이고 DuPont 분해도 평균을 쓴다. 최신 분기 하나로 나누면 기간이
    어긋나 자기자본이 변한 기업이 체계적으로 왜곡된다 — 실측(2026-07-29, 461종목):
    자사주 매입으로 자본이 15%↑ 줄어든 종목은 벤더 ROE 대비 중위 1.21배로 부풀고,
    증자·유보로 10%↑ 늘어난 종목은 0.85배로 눌렸다.
    ⚠ 분기 관측이 5개 미만이면 최신값으로 물러선다(평균을 만들 기간이 없다).
    """
    eqs = P.asof(t, "eq", i, 5)
    if not eqs:
        return None
    base = (eqs[0] + eqs[4]) / 2 if len(eqs) >= 5 else eqs[0]
    return base if base > 0 else None


def _qual_raw(P, i):
    """MSCI Quality 의 세 축 원시값 — ROE(+) · 부채비율 D/E(−) · 이익변동성(−).

    sc_qual 과 sc_snqual(섹터 중립)이 **같은 원시값**을 쓴다. 두 곳에 적으면 '섹터 안에서
    잰 퀄리티'와 '전체에서 잰 퀄리티'가 다른 지표를 뜻하게 되고, 두 줄을 나란히 놓은
    화면에서 그 차이가 섹터 중립 때문인지 정의 때문인지 알 수 없게 된다.
    """
    roe, de, ev = {}, {}, {}
    for t in P.uni:
        ni, eq, li = P.ttm(t, "ni", i), P.last(t, "eq", i), P.last(t, "liab", i)
        aeq = avg_eq(P, t, i)
        if ni is not None and aeq:
            roe[t] = ni / aeq * 100                  # 분모는 평균, D/E 는 시점값 그대로
        if li is not None and eq and eq > 0:
            de[t] = -(li / eq * 100)
        eps = P.asof(t, "eps", i, 20)
        g = [(eps[k] - eps[k + 4]) / abs(eps[k + 4])
             for k in range(len(eps) - 4) if eps[k + 4] and abs(eps[k + 4]) > 1e-9]
        if len(g) >= 8:
            ev[t] = -float(np.std(np.array(g, float), ddof=1))
    return roe, de, ev


def sc_qual(P, i):
    roe, de, ev = _qual_raw(P, i)
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
                # 🚨 밑이 음수면 분수 거듭제곱이 **복소수**가 되고 zs() 의 float() 에서 죽는다.
                #   b_ 의 부호는 아래에서 abs 로 이미 다루는데 a_ 는 안 보고 있었다 —
                #   1년 창에서는 안 걸리다가 5년 창을 돌리자 났다(2026-08-12 실측).
                #   주당매출이 음수인 시점은 성장률이 정의되지 않는다 → 다음 b 로 넘긴다.
                if a_ <= 0:
                    continue
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


# ── 공개 산식 지수 다섯 ──────────────────────────────────────────────────────
# 2026-08-02 사용자 요청 — "공개 산식이 있는 지수·ETF 를 더 찾아 같은 방식으로".
# 고른 잣대는 하나다: **산식이 공개돼 있고, 이 저장소의 자료로 그 산식을 그대로 계산할 수
# 있는가.** 근사가 필요한 곳은 STYLES 의 substitution 에 적었다.
#
# ⚠ 넣지 않은 것과 그 이유 — 흉내만 낸 지수는 이름만 지수인 다른 규칙이 되기 때문이다.
#     S&P 500 배당귀족  25년 연속 증배가 조건이다. ⚠ 예전 사유("data/fx 배당 이력이 중앙값
#                       20분기=5년")는 2026-08-03 보관 깊이를 늘리면서 **틀린 말이 됐다** —
#                       지금 dps 는 중앙값 2010-03 부터 약 16년치가 있다. 그래도 25년에는
#                       9년 모자란다. 못 하는 이유가 바뀐 것이지 할 수 있게 된 게 아니다.
#     DJ US Dividend 100  SCHD 다. 만들어 돌려 보고 뺐다 — **백테스트가 안 된다.** 복합점수에
#     (SCHD)            5년 배당성장률이 들어가는데, 1년 전 월말에서 그 값을 만들려면 6년 전
#                       배당이 필요하다. 오늘은 118종이 채점되지만 13개월 전에는 20종으로
#                       주저앉아 MIN_NAMES(100)에 못 미친다(실측). 10년 연속 배당이라는
#                       자격 관문도 해당 종목이 28종뿐이라 5년으로 낮춰야 했다 — 관문·성장
#                       기간·총부채까지 셋을 갈면 이름만 SCHD 인 다른 규칙이 된다.
#                       ⚠ 이 셋 다 배당 이력 길이가 원인이었다. 위 보관 깊이 확장 뒤 다시
#                       재 볼 값이 있다 — 아직 재지 않았으므로 '된다'고 적지 않는다.
#     MSCI USA 최소분산  공분산행렬 최적화라 '상위 10종목'이라는 형태가 성립하지 않는다.
#                       (저변동 lowvol 이 규칙 기반 사촌이고 이미 있다.)
#     동일가중·매출가중   선택 규칙이 아니라 **가중 방식**이다. 상위 10종목이 없다(RSP 를
#                       ETF 표에서 뺀 것과 같은 이유).
#     S&P 500 순수가치   style_top.py 에 PURE_V 가 이미 계산돼 있지만, 모지수 스타일점수
#                       machinery 를 이쪽에도 옮겨야 해 이번 범위 밖으로 둔다.
#     주주환원(SYLD)     만들어 돌려 보고 뺐다. 정의상 배당수익률 + 자사주매입률이라 새 축이
#                       아니고, 실측(2026-07-31) 상위 10종 중 8종이 자사주매입 줄과 같았다
#                       (CHTR·CRM·IT·LUV·TTD·AIG·GDDY 그대로). 바로 윗줄과 같은 티커를
#                       보여 주는 줄은 독자에게 정보가 아니다. 규칙이 나빠서가 아니라
#                       **화면에서 겹쳐서** 뺀 것이다 — 되살리려면 sc_div·sc_buyback 을
#                       더하는 함수 하나면 된다.


def mcap(P, t, i):
    """시가총액(백만달러) — 주가 × 희석주식수.

    data/fx 의 sh 는 **백만주**(태그 s=m)이고 금액 태그도 백만달러라 그대로 약분된다.
    실측 대조(2026-07-31, 496종): 벤더 시총 대비 배율 중앙 1.00.
    """
    a = P.px.get(t)
    sh = P.last(t, "sh", i)
    if a is None or np.isnan(a[i]) or a[i] <= 0 or not sh or sh <= 0:
        return None
    return a[i] * sh


def sc_size(P, i):
    """MSCI USA Size (Mid Cap) — 시가총액이 작은 순.

    🚨 2026-08-10 추가. 이 스타일은 style_top.py 에만 있어 **상위 10종목은 뽑히는데
      백테스트 곡선이 없었다.** 그래서 홈 표에서 ST_HIDE 로 숨겨져 있었고(2026-08-02
      사용자 결정), 숨긴 이유가 '반쪽이라서'였다. 반쪽을 채워 되살린다.
    ⚠ 이 유니버스(S&P 500 ∪ NASDAQ 100)에는 진짜 중형주가 없다 — 가장 작은 10종도
      대형주다. 정본 MSCI Size 와 같은 것을 재지 않는다는 뜻이고, 그 한계는 아래
      설명문에 적는다. 그래도 '유니버스 안에서 작은 쪽'이라는 축은 성립한다.
    """
    d = {}
    for t in P.uni:
        m = mcap(P, t, i)
        if m and m > 0:
            d[t] = -m                 # 작을수록 상위 — 부호만 뒤집는다
    return d, d                       # 연속값이라 동점이 없다


def sc_div(P, i):
    """S&P 500 High Dividend — 배당수익률이 높은 순(정본은 상위 80종, 여기서는 10종)."""
    d = {}
    for t in P.uni:
        a = P.px.get(t)
        if not P.usd(t) or a is None or np.isnan(a[i]) or a[i] <= 0:
            continue
        # 🚨 2026-08-05 — 연간 버킷을 안 넘기고 있었다. 같은 날 tech_backtest.ttm2 에
        #   **인접 관측 연속성** 게이트를 넣었는데(회계 4분기가 q 버킷에 안 남아 '12개월 합'이
        #   실은 15개월 창이던 것을 막는 고침), dps 는 그 결측이 78.9% 라 분기 경로가 대부분
        #   막히고 ann=None 이면 폴백이 없다. 실측(2026-06-30): 82종 → 연간 버킷을 넘기면 356종.
        #   그래서 고배당·고배당저변동 두 스타일이 '자료 부족'으로 통째로 빠져 있었다.
        v = P.ttm12(t, "dps", i, ann="dps_a")
        if v and v > 0:
            d[t] = v / a[i] * 100
    return d, d                                   # 연속값이라 동점이 없다


def sc_buyback(P, i):
    """S&P 500 Buyback — 최근 1년 자사주 매입액 ÷ 시가총액이 큰 순(정본 100종)."""
    d = {}
    for t in P.uni:
        mc = mcap(P, t, i)
        if not P.usd(t) or not mc:
            continue
        v = P.ttm12(t, "bb", i, "bb_a")
        if v and v > 0:
            d[t] = v / mc * 100
    return d, d


# COWZ 가 유니버스에서 빼는 업종. 은행·보험의 영업활동현금흐름은 예금·보험부채의 증감을
# 담고 설비투자는 거의 없어 'FCF 수익률'이 사업의 현금창출력을 뜻하지 않는다. 리츠도
# 감가상각이 커 같은 이유로 왜곡된다. 정본이 이 둘을 제외하는 이유이고, 안 빼면 실제로
# 상위 20종 중 9종이 금융이 된다(실측 2026-07-31).
FCF_EXCL = {"Financials", "Real Estate"}


def sc_fcfy(P, i):
    """Pacer US Cash Cows 100(COWZ) — 잉여현금흐름 수익률이 높은 순(정본 100종).

    ⚠ 정본의 분모는 **기업가치(EV)** 다. 여기서는 시가총액을 쓴다 — data/fx 에 순부채를
      만들 태그가 없다(liab 는 매입채무까지 포함한 부채총계라 차입금이 아니다).
      부채가 큰 회사가 정본보다 좋게 나오는 방향의 이탈이라, substitution 에 적는다.
    """
    d = {}
    for t in P.uni:
        if (P.uni[t].get("sector") or "") in FCF_EXCL:
            continue
        mc = mcap(P, t, i)
        if not P.usd(t) or not mc:
            continue
        v = P.ttm12(t, "fcf", i, "fcf_a")
        if v is not None:
            d[t] = v / mc * 100
    return d, d


def sc_divlv(P, i):
    """S&P 500 Low Volatility High Dividend(SPHD) — 배당 상위를 거른 뒤 변동성이 낮은 순.

    정본은 두 단계다. ① 12개월 배당수익률 상위 75종 ② 그중 252거래일 실현변동성이 가장 낮은
    50종. 여기서는 ①을 **비율(상위 15% = 75/500)** 로 옮기고 ②는 상위 10종목만 세운다.
    개수를 고정하면 채점 가능 종목이 달마다 달라 관문이 어떤 달은 상위 15%, 어떤 달은 25%가 된다.
    """
    dy, _ = sc_div(P, i)
    if not dy:
        return {}, {}
    v, _b = _vol_beta(P, i)
    pool = sorted((t for t in dy if t in v), key=lambda t: -dy[t])
    if len(pool) < 100:                           # 배당 지급 종목이 이보다 적으면 자료가 얕다
        return {}, {}
    gate = pool[:max(30, int(round(len(pool) * 0.15)))]
    d = {t: -v[t] for t in gate}                  # 변동성은 낮을수록 상위
    return d, d


sc_divlv.min_names = 30                            # 관문이 스스로 좁힌다(355종의 15% ≈ 53)


def _sh_change(P, t, i):
    """주식수 순감소율 % — 1년 전 대비. 늘었으면 음수. 잴 수 없으면 None.

    🚨 여기서 쓰는 계열은 sh 가 아니라 **sh_u** 다. sh 는 분할기준이 섞인 관측을 잘라낸
      계열인데, 그 자르기를 '주식수 변화 자체를 신호로 쓰는 규칙'에 그대로 쓰면 신호를
      거세한다 — tech_backtest.split_trim 의 🚨 참조(OMC 는 20개 관측 중 19개가 삭제됐고
      그 단절의 정체는 분할이 아니라 합병 대가 주식발행 +53% 였다. MSTR 도 대량발행으로
      12/20 삭제). 즉 이 규칙이 겨냥해야 할 가장 전형적인 사건이 일어난 종목이 꼴찌가
      아니라 **후보에서 사라진다.**
      대신 그 함수가 함께 돌려주는 이음매(sh_seam)를 **건너뛰는 짝만** 배제한다.
    """
    f = P.fx.get(t) or {}
    cut = (dt.date.fromisoformat(P.dates[i]) - dt.timedelta(days=LAG_DAYS)).isoformat()
    obs = [(d, v) for d, v in (f.get("sh_u") or []) if d <= cut and v and v > 0]
    if len(obs) < 2:
        return None
    d0, v0 = obs[0]
    for d1, v1 in obs[1:]:
        gap = (dt.date.fromisoformat(d0) - dt.date.fromisoformat(d1)).days
        if gap < 300:
            continue
        if gap > 430:
            return None                           # 1년짜리 짝이 없다
        seam = f.get("sh_seam")
        if seam and d1 <= seam <= d0:
            return None                           # 이음매를 건너뛰는 짝은 쓰지 않는다
        return (v1 - v0) / v1 * 100
    return None


def sc_netbuy(P, i):
    """Nasdaq US Buyback Achievers(PKW) — 최근 1년 발행주식수 **순감소율**이 큰 순.

    정본은 '순감소 5% 이상'을 자격으로 두고 시총가중한다. 여기서는 상위 10종목을 세우는
    형태라 자격을 문턱이 아니라 **순위**로 옮긴다(5% 문턱은 상위 10종이면 언제나 넘는다).
    ⚠ 자사주매입(sc_buyback)과 다른 축이다. 저쪽은 '얼마를 썼나'(매입액÷시총)이고 이쪽은
      '실제로 주식수가 줄었나'다. 스톡옵션·전환사채로 발행이 그만큼 늘면 매입액이 커도
      순감소는 0 이라, 두 줄의 명단이 갈린다.
    """
    d = {}
    for t in P.uni:
        v = _sh_change(P, t, i)
        if v is not None:
            d[t] = v
    return d, d


def sc_spmo(P, i):
    """S&P 500 Momentum(SPMO) — 최근 1개월을 뺀 **12개월** 위험조정 모멘텀의 z.

    위 모멘텀(MSCI)과 원시값의 정의는 같고, MSCI 가 6개월 축을 함께 평균하는 데 비해
    이쪽은 12개월 하나만 본다. 그래서 최근 반년의 반전을 덜 타고 더 오래 붙어 있는다.
    ⚠ 오늘 상위 10종 중 7종이 모멘텀(MSCI) 줄과 같다(실측 2026-07-31). 산식이 사촌이라
      명단이 겹치는 것은 당연하고, 그럼에도 싣는 것은 **6개월 축 하나가 순위를 얼마나
      바꾸는가**가 이 표에서 답할 수 있는 질문이기 때문이다. 겹치는 것이 싫으면 이 줄을
      먼저 뺄 것.
    """
    if i < 252 * 3 + 22:
        return {}, {}
    m12 = {}
    for t, a in P.px.items():
        w = a[max(0, i - 252 * 3 + 1):i + 1][::5]
        w = w[~np.isnan(w)]
        if len(w) < 100:
            continue
        sig = float(np.std(rets(w), ddof=1)) * np.sqrt(52)
        p1, p13 = a[i - 21], a[i - 21 - 252]
        if sig <= 0 or np.isnan(p1) or np.isnan(p13) or p13 <= 0:
            continue
        m12[t] = (p1 / p13 - 1) / sig
    return zs(m12, MSCI_WP)


def sc_snqual(P, i):
    """MSCI USA Sector Neutral Quality — 퀄리티 z 를 **섹터 안에서** 매긴다.

    퀄리티(MSCI) 줄과 원시값은 같고 표준화 모집단만 다르다. 전체에서 재면 구조적으로 ROE 가
    높은 업종(IT·헬스케어)이 통째로 상위를 먹는데, 섹터 안에서 재면 '같은 업종에서 좋은
    회사'가 남는다 — 팩터를 사려다 업종을 사는 일을 막자는 것이 이 지수의 취지다.
    ⚠ 얇은 섹터는 통째로 빠진다. zs 는 관측 20종 미만이면 빈 dict 를 돌려주므로
      유틸리티·소재처럼 유니버스에 30종 안팎인 업종은 결측이 몇만 생겨도 사라진다.
    """
    roe, de, ev = _qual_raw(P, i)
    secs = {}
    for t in P.uni:
        secs.setdefault(P.uni[t].get("sector") or "", []).append(t)
    cl, un = {}, {}
    for _s, ts in secs.items():
        keep = set(ts)
        c, u = zavg([zs({t: d[t] for t in d if t in keep}, MSCI_WP) for d in (roe, de, ev)])
        cl.update(c); un.update(u)
    return cl, un


def sc_qvm(P, i):
    """S&P 500 Quality, Value & Momentum Multi-Factor(QVML) — 세 팩터 점수의 평균 상위.

    정본은 상위 20% 를 담고 float 시총 × 멀티팩터점수로 가중한다. 여기서는 상위 10종목이다.
    ⚠ 세 점수는 이 파일의 sc_qual · sc_val · sc_mom 을 **그대로** 쓴다. 정본의 세부 정의와
      완전히 같지는 않지만, 같은 표의 퀄리티·가치·모멘텀 줄과 산식이 같아야 '그 셋을
      평균한 줄'이라는 말이 성립한다. 다른 정의를 쓰면 세 줄과 이 줄이 서로를 설명하지 못한다.
    ⚠ 세 팩터를 **모두** 가진 종목만 남는다(zavg 규약). 하나라도 결측이면 두 개 평균으로
      상위에 오르는 일이 없다 — 그건 다른 규칙이다.
    """
    q, qu = sc_qual(P, i)
    v, vu = sc_val(P, i)
    m, mu = sc_mom(P, i)
    common = set(q) & set(v) & set(m)
    if len(common) < MIN_NAMES:
        return {}, {}
    return ({t: (q[t] + v[t] + m[t]) / 3.0 for t in common},
            {t: (qu[t] + vu[t] + mu[t]) / 3.0 for t in common})


def sc_squal(P, i):
    """S&P 500 Quality(SPHQ) — ROE · 발생액비율 · 재무레버리지의 z 평균 상위.

    MSCI 퀄리티(sc_qual)와 **다른 규칙이다.** 저쪽 셋은 ROE·D/E·이익변동성이고 이쪽은
    ROE·**발생액비율**·재무레버리지다. 가르는 것은 발생액비율 — 순이익이 영업현금흐름에서
    얼마나 멀어졌는가로, 회계이익만 좋아 보이는 회사를 잡아내는 자리다.
      발생액비율 = (순이익 − 영업활동현금흐름) ÷ 평균 총자산. 낮을수록 좋다.
    ⚠ 재무레버리지 자리에 부채총계÷자기자본을 쓴다 — data/fx 에 차입금 태그가 없다.
    """
    roe, acc, lev = {}, {}, {}
    for t in P.uni:
        ni, cfo = P.ttm12(t, "ni", i, "ni_a"), P.ttm12(t, "cfo", i, "cfo_a")
        aeq = avg_eq(P, t, i)
        if ni is not None and aeq:
            roe[t] = ni / aeq * 100
        aset = P.asof(t, "asset", i, 5)
        if ni is not None and cfo is not None and aset:
            base = (aset[0] + aset[4]) / 2 if len(aset) >= 5 else aset[0]
            if base > 0:
                acc[t] = -((ni - cfo) / base * 100)     # 발생액은 낮을수록 상위
        eq, li = P.last(t, "eq", i), P.last(t, "liab", i)
        if li is not None and eq and eq > 0:
            lev[t] = -(li / eq)
    return zavg([zs(roe, SP_WP), zs(acc, SP_WP), zs(lev, SP_WP)])


# 순수 계열(S&P 500 Pure Growth / Pure Value)의 바스켓 규칙. 방법론 문서 p6~p9.
#   ① 성장점수 높은 순 = 성장랭크 1위 · 가치점수 높은 순 = 가치랭크 1위
#   ② 성장랭크÷가치랭크 오름차순 — 위쪽이 순수성장, 아래쪽이 순수가치
#   ③ 시가총액 누적 33%까지가 각 바스켓
#   ④ 그중 점수가 (전체 평균 + 0.25)를 넘는 것만 '순수'로 남긴다
# ⚠ 정본은 S&P Total Market 에서 표준화하고 모지수에서 랭크한다 — 여기서는 둘 다 유니버스
#   518종목이다. build/style_top.py 가 오늘 명단에 대해 이미 하던 계산을 그대로 옮겼다.
PURE_BASKET, PURE_MIN = 1 / 3.0, 0.25


def _pure(P, i, value_side):
    g, _gu = sc_grow(P, i)
    v, _vu = sc_val(P, i)
    common = sorted(set(g) & set(v))
    if len(common) < MIN_NAMES:
        return {}, {}
    gr = {t: k + 1 for k, t in enumerate(sorted(common, key=lambda x: -g[x]))}
    vr = {t: k + 1 for k, t in enumerate(sorted(common, key=lambda x: -v[x]))}
    ratio = {t: gr[t] / vr[t] for t in common}
    order = sorted(common, key=lambda t: ratio[t])
    mcv = {t: (mcap(P, t, i) or 0.0) for t in common}
    tot = sum(mcv.values()) or 1.0
    gmean, vmean = float(np.mean([g[t] for t in common])), float(np.mean([v[t] for t in common]))
    out, a = {}, 0.0
    for t in (reversed(order) if value_side else order):
        if a / tot >= PURE_BASKET:
            break
        a += mcv[t]
        if value_side:
            if v[t] > vmean + PURE_MIN:
                out[t] = ratio[t]                    # 가치 쪽은 비율이 클수록 순수하다
        else:
            if g[t] > gmean + PURE_MIN:
                out[t] = -ratio[t]
    return out, out


def sc_puregrow(P, i):
    """S&P 500 Pure Growth — 성장은 높고 가치는 낮은 쪽, 시총 33% 바스켓 안에서."""
    return _pure(P, i, False)


def sc_purevalue(P, i):
    """S&P 500 Pure Value — 가치는 높고 성장은 낮은 쪽, 시총 33% 바스켓 안에서."""
    return _pure(P, i, True)


# 바스켓 규칙이 후보를 스스로 좁힌다(실측 순수성장 50종). MIN_NAMES 100 을 그대로 걸면
# 규칙이 통째로 건너뛰어진다 — backtest.pick 의 주석 참조.
sc_puregrow.min_names = 30
sc_purevalue.min_names = 30


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
    # 점수를 만든 것과 **같은 정의**로 적는다 — 표의 숫자와 순위가 어긋나면 못 읽는다.
    ni, aeq = P.ttm(t, "ni", i), avg_eq(P, t, i)
    if ni is None or not aeq:
        return "—"
    return "%.1f" % (ni / aeq * 100)


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
    # ── 여기부터 다섯은 2026-08-02 에 더했다(위 '공개 산식 지수 다섯' 주석 참조) ──
    ("div", "고배당", "S&P 500 High Dividend", sc_div, "배당수익률 %",
     lambda P, i, t, s, u: "%.2f" % s,
     "최근 1년 주당배당금(선언 기준)을 주가로 나눈 배당수익률이 가장 높은 10종목. 정본은 상위 80종을 담는다.\n"
     "유틸리티·리츠·필수소비에 쏠린다. 수익률이 높은 이유가 배당이 커서가 아니라 주가가 빠져서인 경우가 섞이므로 함정이 있다."),
    ("buyback", "자사주매입", "S&P 500 Buyback", sc_buyback, "매입률 %",
     lambda P, i, t, s, u: "%.2f" % s,
     "최근 1년 자사주 매입액을 시가총액으로 나눈 비율이 가장 높은 10종목. 정본은 상위 100종을 담는다.\n"
     "주식수를 줄여 주당 지분을 키우는 회사를 담는다. 고점에서 사들이는 회사도 함께 걸리므로 밸류에이션을 같이 봐야 한다."),
    ("fcfy", "잉여현금흐름", "Pacer US Cash Cows 100 (COWZ)", sc_fcfy, "FCF수익률 %",
     lambda P, i, t, s, u: "%.2f" % s,
     "영업활동현금흐름에서 설비투자를 뺀 최근 1년 잉여현금흐름을 시가총액으로 나눈 값이 가장 높은 10종목.\n"
     "회계이익이 아니라 실제로 남은 현금을 본다. 경기민감·에너지에 쏠리기 쉽고, 투자를 줄여 현금이 남은 회사도 같이 걸린다."),
    ("spmo", "모멘텀", "S&P 500 Momentum (SPMO)", sc_spmo, "12M 위험조정", d_mom,
     "최근 1개월을 뺀 12개월 수익률을 3년 주간변동성으로 나눈 값의 z 상위 10종목. 정본은 100종을 담는다.\n"
     "위 모멘텀(MSCI)이 6개월 축을 함께 보는 것과 다르다 — 12개월 하나만 보므로 최근 반년의 반전을 덜 타고 더 오래 붙어 있는다."),
    ("qvm", "멀티팩터", "S&P 500 Quality, Value & Momentum (QVML)", sc_qvm, "세 팩터 평균 z",
     lambda P, i, t, s, u: "%.2f" % s,
     "퀄리티 · 가치 · 모멘텀 점수를 평균해 가장 높은 10종목. 정본은 상위 20% 를 담는다.\n"
     "한 팩터만 좋은 종목이 아니라 셋 다 무난한 '올라운더'를 고른다. 어느 하나에서도 1등이 아니라 국면 쏠림이 적은 대신 폭발력도 없다."),
    ("snqual", "퀄리티(섹터중립)", "MSCI USA Sector Neutral Quality", sc_snqual, "합성 z",
     lambda P, i, t, s, u: "%.2f" % s,
     "퀄리티 세 축(ROE · D/E · 이익변동성)의 z 를 **섹터 안에서** 매겨 상위 10종목.\n"
     "전체에서 재면 구조적으로 ROE 가 높은 IT·헬스케어가 상위를 먹는다. 같은 업종에서 좋은 회사를 고르는 규칙이라 업종이 흩어진다."),
    ("squal", "퀄리티", "S&P 500 Quality (SPHQ)", sc_squal, "합성 z",
     lambda P, i, t, s, u: "%.2f" % s,
     "ROE · 발생액비율(낮을수록) · 재무레버리지(낮을수록)의 z 평균 상위 10종목. 정본은 100종을 담는다.\n"
     "위 퀄리티(MSCI)와 가르는 것은 발생액비율이다 — 순이익이 영업현금흐름에서 멀어진 회사, 즉 장부만 좋아 보이는 회사를 걸러낸다."),
    ("puregrow", "순수성장", "S&P 500 Pure Growth", sc_puregrow, "−(성장랭크÷가치랭크)",
     lambda P, i, t, s, u: "%.3f" % (-s),
     "성장랭크÷가치랭크가 가장 작은 쪽(성장은 높고 가치는 낮은 종목) · 시총 33% 바스켓 안에서 성장점수가 평균+0.25 를 넘는 것만.\n"
     "성장과 가치를 섞어 담지 않고 성장 쪽만 순수하게 담는다. 그만큼 쏠림이 크고 국면이 바뀔 때 낙폭도 크다."),
    ("purevalue", "순수가치", "S&P 500 Pure Value", sc_purevalue, "성장랭크÷가치랭크",
     lambda P, i, t, s, u: "%.3f" % s,
     "성장랭크÷가치랭크가 가장 큰 쪽(가치는 높고 성장은 낮은 종목) · 시총 33% 바스켓 안에서 가치점수가 평균+0.25 를 넘는 것만.\n"
     "순수성장의 거울이다. 싼 것을 사되 성장이 약한 쪽만 담으므로 가치함정에 그대로 노출된다."),
    ("divlv", "고배당저변동", "S&P 500 Low Volatility High Dividend (SPHD)", sc_divlv, "변동성 %",
     lambda P, i, t, s, u: "%.1f" % (-s),
     "배당수익률 상위를 거른 뒤 그 안에서 252거래일 실현변동성이 가장 낮은 10종목. 정본은 상위 75종 → 저변동 50종이다.\n"
     "고배당만 보면 주가가 빠져서 수익률이 높아진 종목이 섞인다. 변동성 관문이 그 함정을 거르는 자리다."),
    ("netbuy", "주식수감소", "Nasdaq US Buyback Achievers (PKW)", sc_netbuy, "순감소율 %",
     lambda P, i, t, s, u: "%.2f" % s,
     "최근 1년 발행주식수가 가장 많이 줄어든 10종목. 정본은 순감소 5% 이상을 자격으로 두고 시총가중한다.\n"
     "자사주매입 줄과 다른 축이다 — 저쪽은 얼마를 썼나이고 이쪽은 실제로 주식수가 줄었나다. 옵션·전환사채 발행이 상쇄하면 여기서 빠진다."),
    ("size", "중소형", "MSCI USA Size (Mid Cap)", sc_size, "시가총액 백만$",
     lambda P, i, t, s, u: ("%.0f" % (-s)) if s else "—",   # 점수는 음수로 담긴다(작을수록 상위)
     "시가총액이 가장 작은 10종목. 정본은 대형·중형 지수에서 중형만 떼어 시총가중한다.\n"
     "⚠ 이 유니버스에는 진짜 중형주가 없다 — S&P 500 ∪ NASDAQ 100 이라 가장 작은 10종도 대형주다. "
     "정본과 같은 것을 재지 않으며, 여기서 읽을 수 있는 것은 '이 유니버스 안에서 작은 쪽'이라는 축뿐이다."),
]

SECS = {"Information Technology": "IT", "Health Care": "헬스", "Financials": "금융",
        "Consumer Discretionary": "경소", "Consumer Staples": "필소",
        "Communication Services": "커뮤", "Industrials": "산업", "Energy": "에너",
        "Utilities": "유틸", "Real Estate": "부동", "Materials": "소재"}


# ── 백테스트 ────────────────────────────────────────────────────────────────
def build_issuer(P):
    """티커 → 발행사 키. 클래스 꼬리를 떼어 같은 회사를 묶는다(정의는 style_top.py 가 정본).

    ⚠ 어느 클래스를 남기나 — **클래스 A 를 남긴다**(사용자 결정 2026-07-28).
      style_top.py 는 '점수가 높은 쪽'을 남기는데, 알파벳에서 그 규칙은 GOOG(클래스 C,
      무의결권)를 남기는 날이 생긴다. 둘 중 하나만 실을 거라면 의결권 있는 A 가 맞다.
      정렬 키에 A 우선을 먼저 넣어, 같은 발행사 안에서는 A 가 항상 앞에 오게 한다.
    ⚠ S&P 정본은 복수 클래스를 둘 다 편입한다 — 이건 10칸 목록에서 한 회사가 두 칸을
      먹지 않게 하려는 표시 목적의 의도적 이탈이다. 유니버스에서 걸리는 것은 셋뿐이다
      (알파벳·폭스·뉴스코프, 실측).
    """
    import re as _re
    out = {}
    for t, u in P.uni.items():
        n = (u.get("name") or "").upper().strip()
        n = _re.sub(r"\s*-\s*(CL|CLASS|SER|SERIES)\s+[A-Z0-9]+$", "", n)
        n = _re.sub(r"\s*-\s*[A-Z]$", "", n)
        out[t] = _re.sub(r"[^A-Z0-9]", "", n) or t
    return out


def iss_of(P):
    """발행사 맵을 Panel 에 캐시한다. 전역에 두고 main() 에서만 채우면, 다른 진입점(예:
    build/guru_top_pdf.py 가 ST.Panel() 만 쓰는 경우)에서 빈 채로 남아 통합이 조용히 꺼진다."""
    m = getattr(P, "_iss", None)
    if m is None:
        m = build_issuer(P)
        P._iss = m
    return m


def is_class_a(P, t):
    """이름이 클래스 A 라고 말하는가. 이름에 클래스 표기가 없으면 단일 클래스로 본다."""
    n = (((P.uni.get(t) or {}).get("name")) or "").upper()
    return bool(__import__("re").search(r"-\s*(CL|CLASS)?\s*A\b|\bCLASS A\b", n))


def bt(P, fn, **kw):
    """배포용 백테스트 — **언제나 PIT** 다(2026-08-23 사용자 지시).

    P._pit_at 가 붙어 있으면 그 시점 멤버로 pool 과 **채점 모집단**을 같이 좁힌다.
    ⚠ 안 붙어 있으면 죽는다. 조용히 소급으로 되돌아가는 것이 이 변경이 막으려던 바로
      그 실패다 — 'PIT' 라고 적힌 생존자 백테스트를 내보내지 않는다.
    """
    at = getattr(P, "_pit_at", None)
    if at is None:
        raise SystemExit("P._pit_at 가 없다 — PIT 패널을 준비하지 않고 배포 백테스트를 "
                         "부르고 있다(build/style_pit_panel.prepare/inject 를 먼저 부를 것)")
    import style_pit_panel as SPP               # noqa: E402
    return backtest(P, SPP.narrowed(fn, at), pool_of=at, **kw)


def backtest(P, fn, pool_of=None):
    """최근 1년. 월말 리밸런스 · 상위 10 동일가중 · 사이에는 표류.

    구간 시작 시점의 보유는 그 이전 마지막 월말 선정이다. 그래야 창 첫날부터 진짜 포트폴리오다.

    pool_of — 선택 시점 i 를 받아 그날 고를 수 있는 티커 집합을 주는 함수. None 이면 제한이
      없다(=기본 동작, 오늘의 유니버스 전체 = 생존편향). build/style_pit.py 가 선정 시점
      멤버십을 넘겨 편향 크기를 재는 데 쓴다. **훅을 여기 둔 이유**: 백테스트를 두 벌로
      만들면 반드시 어긋나고, 그때 '편향을 재는 쪽'이 틀렸는지 '배포하는 쪽'이 틀렸는지
      알 수 없게 된다. 같은 코드가 두 경우를 다 돌아야 차이가 곧 편향이다.
    """
    end = len(P.dates) - 1
    # 창 시작을 **월말**로 맞춘다. 252거래일을 그냥 빼면 월 중간(예: 07-25)에서 시작해
    # 첫 달이 부분 월이 되고 표에 13개월이 찍힌다. 그 달은 며칠치라 다른 달과 같은 자로
    # 읽을 수 없다 — 시작을 그 다음 월말로 밀어 온전한 12개월만 남긴다.
    start = next((i for i in P.me if i >= max(0, end - WINDOW)), max(0, end - WINDOW))
    rebal = [i for i in P.me if start < i < end]

    cache = {}

    def pick(i):
        """그 시점 상위 10종목 → [(티커, 점수, 동점가르개)]. 자료가 얕으면 None."""
        if i in cache:
            return cache[i]
        s, tie = fn(P, i)
        out = None
        # MIN_NAMES 는 '그 규칙의 자료가 아직 얕은가'를 보는 관문이지 규칙 설계를 재는 자가
        # 아니다. **관문을 스스로 좁히는 규칙**(순수성장·순수가치·GARP·고배당저변동)은
        # 설계상 후보가 100종에 못 미친다 — 실측으로 순수성장은 50종이라 통째로 건너뛰어졌다.
        # 그래서 규칙이 자기 최소치를 말할 수 있게 한다(sc_*.min_names). 안 적은 규칙은 종전대로.
        if len(s) >= getattr(fn, "min_names", MIN_NAMES):
            # 마스크는 pit_backtest.py:242 와 같은 자리에 둔다 — 채점은 그대로 하고
            # **후보에서 거른다**. 채점 단계에서 거르면 z 표준화의 모집단이 달라져
            # 편향 측정이 아니라 다른 규칙이 된다.
            pool = pool_of(i) if pool_of else None
            ok = [t for t in s if t in P.px and not np.isnan(P.px[t][i])
                  and (pool is None or t in pool)]
            ok.sort(key=lambda t: (-s[t], -tie.get(t, 0.0), t))
            # 같은 발행사의 다른 클래스는 하나만 — 밀려난 자리는 다음 순위가 채운다.
            #   실측(성장): GOOG·GOOGL 이 둘 다 들어와 알파벳 한 회사가 10칸 중 2칸(20%)이었다.
            #   분산이 아니라 착시다. build/style_top.py 가 홈 JSON 에서 이미 하던 것을 PDF 도 한다.
            #
            #   순위는 그 발행사의 **최고 점수**로 정하고(자리를 잃지 않는다), 그 자리에 실을
            #   티커는 **클래스 A**를 쓴다(사용자 결정). 둘을 갈라 두지 않으면, A 의 점수가 조금
            #   낮은 날 알파벳이 통째로 뒤로 밀리거나 C 가 실린다.
            _iss = iss_of(P)
            seen, ded = set(), []
            for t in ok:
                k = _iss.get(t, t)
                if k in seen:
                    continue
                seen.add(k)
                same = [x for x in ok if _iss.get(x, x) == k]
                a_ = next((x for x in same if is_class_a(P, x)), None)
                ded.append(a_ or t)
            if len(ded) >= TOPN:
                out = [(t, s[t], tie.get(t, s[t])) for t in ded[:TOPN]]
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


_RFD = None            # 일할 무위험(하루). 처음 쓸 때 한 번 읽는다.
_SKIPPED = {}          # 자료 부족으로 못 낸 스타일 — 채우는 곳과 싣는 곳이 다른 함수라 모듈에 둔다


def _rfd():
    """무위험 일할 수익 — 랩 전체가 쓰는 data/rf_monthly.json 그대로.

    🚨 2026-08-05 — 이 파일의 metrics() 만 **무위험을 안 빼고** 있었다(rf=0). 그 값이
      style_perf.json·style_trails.json 을 거쳐 홈의 샤프 열이 되고, 홈은 그 열로 17줄을
      **정렬한다**(index.html). 왜곡폭이 rf/vol 이라 저변동 규칙일수록 부당하게 유리해진다.
      같은 저장소의 tech_backtest.ann_stats · asset_backtest · guru17_backtest.ann_from_monthly
      · strategy_metrics 는 전부 초과수익 기준이고, strategy_metrics 머리말 1번이 정확히 이
      결함을 '엔진을 다시 만든 이유'로 적어 두었다("Sharpe가 초과수익이 아니었다 … 저변동
      전략일수록 부당하게 유리"). 한쪽만 고쳐진 두 벌이었다.
    """
    global _RFD
    if _RFD is None:
        try:
            _m = json.load(io.open(os.path.join(DATA, "rf_monthly.json"),
                                   encoding="utf-8")).get("monthly") or {}
            _RFD = (sum(_m.values()) / len(_m) / 21) if _m else 0.0
        except Exception:
            _RFD = 0.0
    return _RFD


def metrics(nav):
    r = rets(nav)
    yrs = len(r) / 252.0
    sd = float(np.std(r, ddof=1))
    return {"ret": (nav[-1] ** (1 / yrs) - 1) * 100 if yrs > 0 and nav[-1] > 0 else None,
            "vol": sd * np.sqrt(252) * 100,
            "sharpe": ((float(np.mean(r)) - _rfd()) / sd * np.sqrt(252)) if sd > 0 else None,
            "mdd": float(np.min(nav / np.maximum.accumulate(nav) - 1)) * 100}


# ⚠ 여기 라벨은 홈(index.html)의 ST_TR 매핑과 짝이다 — 한쪽만 바꾸면 그 칸이 조용히
#   빈다(build/validate_site.py 가 대조한다).
TRAIL = [("1일", 1), ("1주", 5), ("1개월", 21), ("3개월", 63), ("6개월", 126), ("1년", 252)]


def trails(nav, dates, start):
    """기간별 수익률 %. 창보다 긴 구간은 창 시작으로 자른다.

    ⚠ 창을 월말에 맞추면서 길이가 252일에서 251일로 줄었다. 그대로 두면 '1년' 칸이
      범위를 벗어나 전부 '—' 로 비었다 — 창 자체가 최근 1년이므로 시작점으로 자른다.
      전략과 대조군이 같은 창이라 비교는 그대로 성립한다.
    """
    out = {}
    for lab, n in TRAIL:
        out[lab] = ((nav[-1] / nav[max(len(nav) - 1 - n, 0)] - 1) * 100
                    if len(nav) > 1 else None)
    y0 = dates[-1][:4] + "-01-01"                 # YTD — 전년 마지막 거래일 대비
    j = None
    for k in range(len(nav)):
        if dates[start + k] >= y0:
            j = k
            break
    out["YTD"] = ((nav[-1] / nav[j - 1] - 1) * 100) if (j and j >= 1) else None
    return out


def monthly(nav, dates, start):
    """달마다의 수익률 %.

    창이 월말에서 열리므로 시작 달은 그날 하루뿐이라 수익률이 없다 — 그 달은 목록에서
    뺀다. 남는 것은 전부 온전한 달이다(마지막 달만 오늘까지의 진행 중인 달이다).
    """
    lastk = {}
    for k in range(len(nav)):
        lastk[dates[start + k][:7]] = k
    out, prev = {}, 0
    for m in sorted(lastk):
        k = lastk[m]
        out[m] = (nav[k] / nav[prev] - 1) * 100 if k > prev else None
        prev = k
    ms = [m for m in sorted(out) if out[m] is not None]
    return ms, out


def win_rate(nav, bench, dates, start):
    """전략이 지수를 이긴 달 수와 비교한 달 수 → (이긴 달, 전체 달).

    같은 창·같은 월말 경계로 자른 월 수익률끼리 비교한다. 창이 월말에서 열리므로
    전부 온전한 달이다. 무승부(정확히 동률)는 이긴 것으로 세지 않는다.
    """
    if bench is None:
        return None, 0
    ms, a = monthly(nav, dates, start)
    _, b = monthly(bench, dates, start)
    pair = [(a[m], b[m]) for m in ms if a.get(m) is not None and b.get(m) is not None]
    if not pair:
        return None, 0
    return sum(1 for x, y in pair if x > y), len(pair)


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
    s = ("%+." + str(d) + "f") % v if sign else ("%." + str(d) + "f") % v
    # 표시 자리에서 0 으로 반올림되면 부호를 아예 뗀다 — '-0.0' 도 '+0.0' 도 없는 방향을
    # 주장한다. (1일 수익률처럼 작은 값을 1자리로 낼 때 생긴다. index.html stCell 도 같은 규칙.)
    if s.lstrip("+-").strip("0.") == "":
        s = s.lstrip("+-")
    return s


def footer(fig, page, total):
    hline(fig, X0, X1, .034, LINE, .6)
    # 생존편향을 각주에 박는다 — 유니버스가 소급이라는 사실 없이 +137% 를 내보내면 안 된다.
    tx(fig, X0, .026, "스타일 상위 10종목 전략 · 지수 SPX = S&P 500 단독 · "
                      "NDX = NASDAQ 100 단독 · 공통 = 양쪽 모두 · 대조군은 가격지수(PR) · 비용 0",
       fontsize=6.4, color=MUTED)
    # 한 줄에서 넘치지 않게 짧게 — 렌더해 보고 오른쪽이 잘려 줄였다. 자세한 것은 style.html.
    #   ⚠ '대부분 선견이다' 를 손으로 붙였다가 지웠다 — 가치는 반대로 편출 누락이 전부인데
    #     각주가 가치 블록 바로 아래에 놓인다(적대감사가 잡았다). 채널은 자료에서 파생한다.
    tx(fig, X0, .0175, "유니버스 편향(실측) — 선정 시점 구성으로 다시 재면 "
                       + pit_caveat(short=True) + ". " + pit_channel_line(),
       fontsize=6.0, color=NEG)
    tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
       fontsize=6.4, color=MUTED, ha="right")


def new_page():
    require_draw()
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
    # 이 줄만 성격이 다르다 — 지수의 수치가 아니라 '그 지수를 이긴 달의 비율'이다.
    wg, nwin = win_rate(nav, gn, P.dates, R["start"])
    wn, _ = win_rate(nav, nn, P.dates, R["start"])
    WR = len(rows)
    rows.append(["이긴 달", "—",
                 "—" if wg is None else "%d/%d" % (wg, nwin),
                 "—" if wn is None else "%d/%d" % (wn, nwin)])

    def cc(r, c):
        if c == 0:
            return INK
        if c == 1:
            v = rows[r][1]
            if r in (0, 2) and v != "—":
                return POS if not v.startswith("-") else NEG
            return INK
        if r == WR:                       # 승률은 전략의 성적이므로 대조군 색으로 죽이지 않는다
            w = (wg if c == 2 else wn)
            return MUTED if w is None else (POS if w * 2 > nwin else NEG)
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

    y3 = table(fig, X0, y2 - .0132, [.117] + [.315 / len(labs)] * len(labs), [""] + labs, prow,
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

    # MTD — 직전 월말 종가 대비 오늘까지. 종목의 성질이라 두 표에 같은 값이 들어간다:
    # 왼쪽 표에서는 이번 달 실제 기여분이고, 오른쪽 표에서는 후보가 이번 달 어땠는지다.
    mtd_i = max([j for j in P.me if j < R["end"]] or [R["start"]])

    def mtd(t):
        a = P.px.get(t)
        if a is None or np.isnan(a[mtd_i]) or a[mtd_i] <= 0 or np.isnan(a[R["end"]]):
            return "—"
        return num((a[R["end"]] / a[mtd_i] - 1) * 100, 1)

    def pf(x0, at_i, title, sub, items, other, mark_new):
        tx(fig, x0, yt, title, fontsize=7.5, weight="bold")
        tx(fig, x0 + .428, yt, sub, fontsize=6.5, color=MUTED, ha="right")
        rows_, flags = [], []
        for k, (t, sc, un) in enumerate(items):
            u = P.uni.get(t) or {}
            nm = (u.get("name") or "")[:19]
            sec = SECS.get(u.get("sector") or "", "")
            new = t not in other
            flags.append(new)
            rows_.append(["%d" % (k + 1), ("＋" if (new and mark_new) else "") + t, nm, sec,
                          idx_of(P, t), mtd(t), mfmt(P, at_i, t, sc, un)])

        def c3(r, c):
            if c == 4:                       # 소속 지수는 그 자체가 범주라 색을 따로 쓴다
                return IDXC.get(rows_[r][4], MUTED)
            if c == 5:                       # MTD 는 부호가 뜻이라 신규·이탈 색보다 앞선다
                v = rows_[r][5]
                return MUTED if v == "—" else (NEG if v.startswith("-") else POS)
            if c == 0:
                return MUTED
            if flags[r]:
                return POS if mark_new else NEG
            return INK if c in (1, 2) else MUTED

        return table(fig, x0, yt - .0122, [.026, .058, .140, .040, .034, .046, .084],
                     ["#", "티커", "종목명", "섹터", "지수", "MTD %", mlab], rows_,
                     row_h=.0128, fs=6.9, hfs=6.4,
                     aligns=["c", "l", "l", "l", "l", "r", "r"], cell_color=c3,
                     cell_weight=lambda r, c: "bold" if c in (1, 4) else "normal",
                     zebra=True)

    pf(X0, R["prev_i"], "전월말 기준", "%s · 지금 보유 중" % P.dates[R["prev_i"]],
       R["prev"], ns, False)
    pf(X0 + .456, R["today_i"], "금일 기준", "%s · 다음 리밸런스 후보"
       % P.dates[R["today_i"]], R["today"], ps, True)
    keep = len(ps & ns)
    tx(fig, X1, yp + .0012, "교체 %d종목 · 유지 %d종목 · ＋ 신규편입 · 붉은 종목은 금일 기준에서 빠진 자리 · MTD 는 직전 월말 대비"
       % (TOPN - keep, keep), fontsize=6.4, color=MUTED, ha="right")


# ── 요약 쪽 ────────────────────────────────────────────────────────────────
def draw_summary(fig, P, res, order, total):
    d0, d1 = P.dates[res[order[0]]["start"]], P.dates[res[order[0]]["end"]]
    tx(fig, X0, .962, TITLE, fontsize=23, weight="bold")
    tx(fig, X0, .928, SUBTITLE, fontsize=10, color=ACC)
    tx(fig, X1, .932, "%s ~ %s" % (d0, d1), fontsize=8.5, color=MUTED, ha="right")
    hline(fig, X0, X1, .916, RULE, .9)

    y = .895
    tx(fig, X0, y, "최근 1년 성과", fontsize=11.5, weight="bold")
    # 대조군을 맨 위에 둔다 — 전략을 읽기 전에 기준선을 먼저 보라는 뜻이다.
    R0 = res[order[0]]
    rows, colors_ = [], []
    for lab, a in (("S&P 500 PR", P.gspc), ("NASDAQ 100 PR", P.ndx)):
        mb = metrics(bench_nav(P, a, R0["start"], R0["end"]))
        rows.append([lab, "대조군 · 가격지수", num(mb["ret"], 2), num(mb["vol"], 2, False),
                     num(mb["sharpe"], 2), num(mb["mdd"], 2), "—", "—", "—", "—", "—"])
    nB = len(rows)
    for key in order:
        S = next(s for s in STYLES if s[0] == key)
        R = res[key]
        m = metrics(R["nav"])
        mg = metrics(bench_nav(P, P.gspc, R["start"], R["end"]))
        mn = metrics(bench_nav(P, P.ndx, R["start"], R["end"]))
        keep = len(set(t for t, _s, _u in R["prev"]) & set(t for t, _s, _u in R["today"]))
        ix = [idx_of(P, t) for t, _s, _u in R["today"]]
        wg, nwin = win_rate(R["nav"], bench_nav(P, P.gspc, R["start"], R["end"]),
                            P.dates, R["start"])
        wn, _ = win_rate(R["nav"], bench_nav(P, P.ndx, R["start"], R["end"]),
                         P.dates, R["start"])
        rows.append([S[1], S[2].split(" (")[0], num(m["ret"], 2), num(m["vol"], 2, False),
                     num(m["sharpe"], 2), num(m["mdd"], 2),
                     num(m["ret"] - mg["ret"], 2), num(m["ret"] - mn["ret"], 2),
                     "%d/%d·%d/%d" % (wg, nwin, wn, nwin) if wg is not None else "—",
                     "%d" % (TOPN - keep),
                     "%d·%d·%d" % (ix.count("SPX"), ix.count("공통"), ix.count("NDX"))])
        colors_.append(m["ret"])

    def cc(r, c):
        if r < nB:
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
                 [.118, .140, .072, .060, .052, .062, .072, .072, .105, .042, .086],
                 ["전략", "참조 지수", "1년 수익률 %", "변동성 %", "샤프", "MDD %",
                  "vs S&P %p", "vs NDX %p", "이긴 달 S&P·NDX", "교체", "SPX·공통·NDX"],
                 rows, row_h=.0175, fs=7.6, hfs=6.6,
                 aligns=["l", "l", "r", "r", "r", "r", "r", "r", "c", "c", "c"], cell_color=cc,
                 cell_weight=lambda r, c: "bold" if (c == 0 or c == 2) and r >= nB else "normal",
                 zebra=True)
    tx(fig, X0, ytab - .0085,
       "'이긴 달'은 %d개월 중 그 지수를 이긴 달 수다 — 왼쪽이 S&P 500, 오른쪽이 NDX. "
       "1년 수익률 하나로는 크게 몇 번 이긴 것과 꾸준히 이긴 것이 구별되지 않아 같이 싣는다.\n"
       "'교체'는 전월말 기준과 금일 기준 명단의 차이다 — 이 규칙이 달마다 손을 얼마나 대는지를 뜻한다. "
       "맨 오른쪽은 오늘 담은 10종목이 어느 지수 소속인지의 구성이다." % nwin,
       fontsize=6.6, color=MUTED, linespacing=1.55)

    # ② 월별 수익률 — 어느 달에 무엇이 먹혔나. 표의 1년 숫자 하나로는 안 보이는 것이다.
    names = [r[0] for r in rows]
    navs = ([bench_nav(P, P.gspc, R0["start"], R0["end"]),
             bench_nav(P, P.ndx, R0["start"], R0["end"])]
            + [res[k]["nav"] for k in order])          # rows 와 같은 순서라야 라벨이 안 밀린다
    ms, _ = monthly(navs[0], P.dates, R0["start"])
    grid = np.array([[monthly(n, P.dates, R0["start"])[1].get(m, np.nan) for m in ms]
                     for n in navs], float)

    yh = ytab - .034
    tx(fig, X0, yh, "월별 수익률 %", fontsize=11.5, weight="bold")
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
    ax.set_xticklabels([m[2:] for m in ms])
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
                    weight=("bold" if r >= nB else "normal"))

    # ③ 1년 누적 곡선 — 일곱 전략과 두 지수를 한 판에.
    yc = yh - .014 - hm_h - .030
    tx(fig, X0, yc, "1년 누적 곡선 · 시작 = 100", fontsize=11.5, weight="bold")
    ch_h = yc - .014 - .072
    ax2 = fig.add_axes([X0 + .048, yc - .014 - ch_h, X1 - X0 - .058, ch_h])
    ax2.set_facecolor(PAPER)
    xi = np.arange(len(navs[0]))
    ax2.axhline(100, color=LINE, lw=.6)
    for lab, a, col, ls, lw in (("S&P 500(PR)", navs[0], INK, "--", 1.1),
                                ("NASDAQ 100(PR)", navs[1], MUTED, ":", 1.1)):
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


# ── 화면에서 빼는 스타일 ──────────────────────────────────────────────────
# 🚨 정본이 여기다. index.html·style.html 둘 다 이 목록을 읽는다(style_perf/style_trails).
#   종전에는 index.html 의 ST_HIDE 에만 있어 style.html 이 18종을 그대로 냈다.
# ⚠ 뺀 기준 셋. 성적이 낮다는 이유만으로는 안 뺀다(그건 결과지 근거가 아니다):
#   ① 같은 것을 두 번 세는 줄(수익률 상관 0.93 이상) ② 후보가 없어 '상위 10' 이 선택이
#   아니게 된 줄 ③ 시점정확으로 재면 짝보다 나쁜 줄. 아래 넷은 그 밖의 사용자 결정이다.
# ⚠ **자료·빌더는 그대로다.** 여기 키를 지우면 그 줄이 그대로 돌아온다.
HOME_HIDE = {
    "mom": "모멘텀(S&P)와 상관 0.978 · 시점정확 +87.2% vs +97.9% 로 열위 · 편향의 90.5%p 가 사후편입",
    "purevalue": "가치와 상관 0.927 · 5년 수익 111.21 vs 111.07 로 사실상 같다",
    "puregrow": "성장과 상관 0.943 · 후보 48종뿐이라 상위 10이 선택이 아니다 · PIT 못 쟀음",
    "divlv": "후보 53종뿐 · 샤프5 0.45 · PIT 못 쟀음 · 정본의 2단 선별을 재현 못 함",
    "lowvol": "샤프5 0.21 로 18종 최하위 · USMV 실물이 홈 ETF 줄에 있다",
    "snqual": "퀄리티 3종 중 최하위(샤프5 0.53) · 원시값이 퀄리티와 같고 표준화 모집단만 다르다",
    "qual": "S&P 판(퀄리티)만 남긴다 · 샤프5 0.60 < 0.73",
    "buyback": "사용자 결정(2026-08-13) — 자사주·현금흐름 계열 셋을 뺐다 · 샤프5 0.70",
    "fcfy": "사용자 결정(2026-08-13) — 자사주·현금흐름 계열 셋을 뺐다 · 샤프5 0.71",
    "netbuy": "사용자 결정(2026-08-13) — 자사주·현금흐름 계열 셋을 뺐다 · 샤프5 1.15",
}


def main() -> int:
    # --json : 그림 없이 data/style_perf.json · style_trails.json 만 낸다. CI 용 경로다
    #          (matplotlib·한글 폰트 없이 도는 유일한 진입점).
    json_only = "--json" in sys.argv[1:]
    P = Panel()
    print("유니버스 %d · 일별 %d일(%s~%s) · 월말 %d회"
          % (len(P.uni), len(P.dates), P.dates[0], P.dates[-1], len(P.me)))

    # ── 시점정확(PIT) 패널 ──────────────────────────────────────────────────
    # 🚨 2026-08-23 사용자 지시 «스타일 전략들도 pit 으로. 전략 랩처럼 — 그때 실제로
    #   지수에 있던 종목만». 종전 이 파일의 백테스트는 **오늘의 518종을 과거로 소급**해
    #   골랐다. 랩은 그 편향을 build/style_pit.py 로 재고 있었으면서(모멘텀 +88.77%p ·
    #   고베타 +123.55%p) 배포하는 곡선은 소급 그대로였다 — 재 놓고 안 고친 셈이다.
    # ⚠ 준비 코드는 style_pit_panel 한 곳에 있다. 편향을 재는 쪽과 배포하는 쪽이 **같은
    #   함수**를 써야 차이가 곧 편향이고, 두 벌이면 어느 쪽이 틀렸는지 알 수 없다.
    # ⚠ 창은 5년 레그까지 덮어야 한다(WINDOW5). 1년 창으로 준비하면 5년 레그가 창 밖
    #   구간에서 마스크 없이 돌아 조용히 소급으로 되돌아간다.
    import style_pit_panel as SPP                 # noqa: E402  같은 build/ 안
    _prep = SPP.prepare(P=P, ST=sys.modules[__name__], window=max(WINDOW, WINDOW5))
    SPP.inject(_prep)
    PIT_AT = _prep["members_at"]
    print("  [PIT] 편출 %d종 주입 · 그때 지수에 있던 종목만 고른다" % len(_prep["inject"]))

    # 🚨 풀을 **패널에 붙인다.** dump_json 같은 다른 함수도 같은 규약으로 불러야 하는데,
    #   main 안의 지역 함수로 두면 그쪽이 조용히 소급으로 되돌아간다(실제로 그랬다 —
    #   5년 레그가 NameError 로 죽어서 드러났고, 죽지 않았다면 못 봤을 종류다).
    P._pit_at = PIT_AT

    res, order = {}, []
    _SKIPPED.clear()
    for S in STYLES:
        key, label = S[0], S[1]
        R = bt(P, S[3])
        if not R:
            # 🚨 2026-08-05 — 종전에는 그냥 continue 였다. 그러면 그 스타일이 산출물에서
            #   통째로 사라지고, index.html 이 가리키는 랩 키가 매달린 채 그 줄이 화면에서
            #   **조용히 없어진다**(validate_site 가 실제로 잡았다: 'div·divlv 가 없다').
            #   빠진 이유가 자료 쪽인지 규칙 쪽인지도 화면에서 알 수 없다.
            #   실제 사유(2026-08-05 실측): stocks.json 의 배당수익률(dy)이 518종 전부 결측이다.
            #   refresh_stocks 의 단위 가드가 '보정 후 중앙값이 0.3~8% 밖'이면 dy 를 통째로
            #   결측 처리하는데, 그것이 걸렸고 그 사실이 아래로 전달되지 않았다.
            #   → 키는 남기고 '못 쟀다'를 값으로 싣는다. 없는 것과 나쁜 것은 다르다.
            print("  %-5s 건너뜀 — 자료 부족" % label)
            _SKIPPED[key] = {"label": label, "why": "입력 자료 부족 — 이 스타일의 점수를 낼 수 없다"}
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

    if json_only:
        print("--json · PDF 는 건너뛴다")
    else:
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

    # ── 같은 내용을 화면용 JSON 으로도 낸다 ────────────────────────────────
    # PDF 는 수익률 순으로 정렬해 **쪽 번호가 매달 바뀌므로** 사이트에서 #page=N 으로
    # 걸 수 없다. style.html 이 이 파일 하나를 읽어 스타일 한 종을 그린다.
    dump_json(P, res, detail)
    return 0


# ── 모멘텀 변동성 관리 ───────────────────────────────────────────────────────
# 근거: Barroso & Santa-Clara, "Momentum Has Its Moments"(JFE 2015). 모멘텀의 위험은
#   **자기 실현분산으로 예측된다** — 직전 6개월 실현변동성으로 목표에 맞춰 비중을 줄이면
#   크래시가 크게 완화된다. 랩 실측(2026-07-29, 확장창 목표로 룩어헤드 제거, 57개월):
#     원본  CAGR 41.67% · 샤프 1.16 · MDD −30.59%
#     관리  CAGR 38.85% · 샤프 1.22 · MDD −20.13%   (연 2.8%p 를 내주고 꼬리를 10%p 줄인다)
#   ⚠ 이 MDD 개선은 사실상 **크래시 한 번(2026-07)에 기댄다.** 표본이 그것뿐이다.
#     잘 확립된 문헌과 방향이 같다는 것이 이 결과의 값어치이지, 랩이 증명한 것이 아니다.
#   📌 종목 선택은 모멘텀과 **똑같다.** 바뀌는 것은 얼마나 드느냐뿐이다.
#   📌 전략 자체는 이 문서가 아니라 **factor_plus.pdf** 에 실린다(그쪽이 '강화' 문서다).
#      여기에는 두 함수만 남겨 두고 factor_plus 가 import 해 쓴다.
VM_LOOK = 6            # 비중을 정할 때 보는 직전 개월 수(원문과 같다)
VM_WARM = 24           # 목표변동성을 잡기 위한 최소 실적. 그 전에는 비중 1.


def vm_weights(P):
    """월 → 비중. **긴 창으로 모멘텀을 한 번 돌려** 미리 계산한다.

    표시 창이 1년뿐이라 그 안에서는 목표변동성을 잡을 수 없다(직전 6개월조차 창 밖이다).
    목표는 '그 시점까지의 실현변동성'이라 확장창이다 — 전 표본 변동성을 쓰면 룩어헤드다.
    """
    global WINDOW
    old, WINDOW = WINDOW, len(P.dates) - 800
    try:
        R = bt(P, sc_mom)
    finally:
        WINDOW = old
    if not R:
        return {}
    ms, mo = monthly(R["nav"], P.dates, R["start"])
    r = [mo[m] for m in ms if mo.get(m) is not None]
    mk = [m for m in ms if mo.get(m) is not None]
    out = {}
    for i, m in enumerate(mk):
        if i < VM_WARM:
            out[m] = 1.0
            continue
        tgt = float(np.std(np.array(r[:i], float), ddof=1))
        v = float(np.std(np.array(r[i - VM_LOOK:i], float), ddof=1))
        out[m] = 1.0 if v <= 0 else min(1.0, tgt / v)
    return out


def vol_managed(P, R, wmap):
    """모멘텀 결과 R 에 월별 비중을 얹어 NAV 를 다시 만든다.

    남는 비중은 현금(수익 0)이고 레버리지는 쓰지 않는다(비중 상한 1).
    보유 명단은 손대지 않는다 — 고르는 규칙이 아니라 크기 규칙이다.
    """
    nav = R["nav"]
    out = np.ones(len(nav))
    for k in range(1, len(nav)):
        w = wmap.get(P.dates[R["start"] + k][:7], 1.0)
        out[k] = out[k - 1] * (1 + (nav[k] / nav[k - 1] - 1) * w)
    R2 = dict(R)
    R2["nav"] = out
    return R2


def _thin(a, k=140):
    """곡선을 k점으로 줄인다 — 화면 폭이 그보다 촘촘할 이유가 없다(strategy_index 와 같은 규약)."""
    a = [None if (x != x) else round(float(x), 5) for x in a]
    if len(a) <= k:
        return a
    step = (len(a) - 1) / (k - 1)
    out = [a[min(len(a) - 1, round(i * step))] for i in range(k)]
    out[-1] = a[-1]
    return out


def pit_channel_line():
    """채널 지배를 **자료에서** 한 줄로. 손으로 '대부분 선견' 이라 적으면 가치에 거짓이다."""
    try:
        st = json.load(io.open(os.path.join(DATA, "style_pit.json"), encoding="utf-8"))["styles"]
        L = [s["label"] for s in st.values()
             if s["channel"]["lookahead"] >= 1.0
             and s["channel"]["lookahead"] > abs(s["channel"]["survivorship"])]
        S = [s["label"] for s in st.values()
             if abs(s["channel"]["survivorship"]) >= 1.0
             and abs(s["channel"]["survivorship"]) >= s["channel"]["lookahead"]]
        out = []
        if L:
            out.append("사후편입 선견: " + "·".join(L))
        if S:
            out.append("편출 누락: " + "·".join(S))
        return " / ".join(out) if out else "채널 유의미하지 않음"
    except Exception:
        return ""


def pit_caveat(short=False):
    """유니버스 편향 문구를 data/style_pit.json 실측에서 만든다.

    ⚠ '생존편향'이라고만 적으면 안 된다. 채널이 둘이고 **스타일마다 지배 채널이 다르다** —
      고베타·모멘텀·성장은 사후편입 선견(그때 지수에 없던 종목을 미리 고른 것)이 지배하고,
      **가치는 반대로 편출 종목 부재(교과서적 생존편향)가 전부다.** 하나의 이름으로 부르면
      한쪽을 반드시 틀리게 말한다. 그래서 채널 판정을 pit_channel_line() 이 자료에서 뽑는다.
    파일이 없으면(러너 등) 수치 없이 정성 문구만 낸다 — 없는 숫자를 지어내지 않는다.
    """
    try:
        j = json.load(io.open(os.path.join(DATA, "style_pit.json"), encoding="utf-8"))
        u, st = j["universe"], j["styles"]
        hit = [s for s in st.values() if abs(s["bias"]["ret"]) >= 1.0]
        big = sorted(hit, key=lambda s: -abs(s["bias"]["ret"]))
        # ⚠ 표기는 base→pit 이다. published→pit 로 적으면 하니스 몫이 섞인다 —
        #   지금은 좁히기로 base==published 라 같은 값이지만, 계약은 base 로 못 박는다.
        nums = " · ".join("%s %+.0f%% → %+.0f%%" % (s["label"], s["base"]["ret"], s["pit"]["ret"])
                          for s in big[:3])
        if short:
            return nums or "편향 유의미하지 않음"
        # 채널 지배는 **자료에서 판정**한다. '대부분 선견'이라고 못 박으면 안 된다 —
        # 가치는 반대로 생존 채널이 전부다(실측). 스타일마다 다르므로 갈라서 적는다.
        look = [s["label"] for s in big if s["channel"]["lookahead"] > abs(s["channel"]["survivorship"])]
        surv = [s["label"] for s in big if abs(s["channel"]["survivorship"]) >= s["channel"]["lookahead"]]
        ch = ""
        if look:
            ch += "사후편입 선견이 지배하는 것은 " + "·".join(look) + " 이고, "
        if surv:
            ch += "편출 종목 부재(생존편향)가 지배하는 것은 " + "·".join(surv) + " 다. "
        head = ("🚨 유니버스 편향(실측) — 재무는 시점(공시 45일 지연)이지만 유니버스는 아니다. "
                "오늘 %d종목을 과거로 소급해 고르는데, 그중 %d종은 구간 시작 시점에 아직 지수 "
                "비멤버였고(선견), 반대로 그때 멤버 %d종 중 %d종은 오늘 유니버스에 없다(생존). "
                "선정 시점 구성이력으로 다시 재면 %s(%s 기준). %s"
                "자세한 분해는 랩의 유니버스 편향 측정 참조. "
                % (u["today"], u["not_yet_member_at_start"],
                   u["n_members_at_start"], u["gone_at_start"], nums, j["as_of"], ch))
        return head
    except Exception:
        return ("🚨 유니버스 편향 — 재무는 시점(공시 45일 지연)이지만 유니버스는 아니다. "
                "오늘의 종목을 과거로 소급해 고르므로, 그때는 지수에 없던 종목까지 후보가 된다. "
                "지수는 많이 오른 종목을 편입하니 그만큼 수익률이 유리하게 부풀려져 있다. "
                if not short else "측정 파일 없음")


def dump_json(P, res, detail):
    R0 = res[detail[0][0]]
    gn = bench_nav(P, P.gspc, R0["start"], R0["end"])
    nn = bench_nav(P, P.ndx, R0["start"], R0["end"])
    ms, _ = monthly(res[detail[0][0]]["nav"], P.dates, R0["start"])
    doc = {
        "as_of": P.dates[R0["end"]], "start": P.dates[R0["start"]],
        # 🚨 화면에서 뺄 스타일 목록의 **정본**이다(2026-08-13). 종전에는 이 목록이
        #   index.html 의 ST_HIDE 에만 있어서 style.html 은 18종을 다 냈다 — 한 사이트가
        #   같은 질문에 두 답을 했다. 목록을 여기 한 벌만 두고 두 화면이 이것을 읽는다.
        #   ⚠ 사유를 값에 적는다. 되살리려는 사람이 근거를 다시 재지 않아도 되게.
        "hide": HOME_HIDE,
        "note": ("style_strategies.pdf 와 같은 계산이다 — 규칙을 과거로 되돌려 매월 다시 골라 "
                 "최근 1년을 잰 것이다. 상위 10종목 동일가중 · 월말 리밸런스 · 비용 0 · "
                 "대조군은 S&P 500(PR)·NASDAQ 100(PR)."),
        # 유니버스 편향을 caveat 맨 앞에 둔다 — 이 화면은 +137% 를 보여준다. 그 수치를 읽는
        # 사람이 가장 먼저 알아야 하는 것이 '고를 수 있었던 명단이 그때 것이 아니다'라는 사실이다.
        # 수치는 build/style_pit.py 의 실측(data/style_pit.json)에서 **파생**한다 — 손으로 적으면
        # 다음 갱신에 낡는다(이 저장소가 반복해 겪은 라벨 드리프트).
        # ⚠ 화면에 그대로 나가는 문장이다. 마크다운(**)을 쓰지 말 것 — textContent 로 꽂히므로
        #   별표가 글자로 보인다. 사내 DB 테이블명도 적지 말 것(공개 사이트다).
        "caveat": (pit_caveat() +
                   "⚠ 홈 화면의 스타일 구성종목 칩과 명단이 다를 수 있다. 그쪽은 벤더 비율을 "
                   "그대로 쓰고 여기는 백테스트라 SEC 재무를 45일 지연으로 쓴다 — "
                   "모멘텀·저변동·고베타는 같고, 퀄리티·가치·성장은 6~7/10 만 겹친다."),
        "months": ms,
        "bench": {},
        "styles": [],
    }
    for lab, a in (("spx", gn), ("ndx", nn)):
        m = metrics(a)
        _ms, mo = monthly(a, P.dates, R0["start"])
        doc["bench"][lab] = {
            "label": "S&P 500 PR" if lab == "spx" else "NASDAQ 100 PR",
            "metrics": {k: (None if v is None else round(v, 2)) for k, v in m.items()},
            "trails": {k: (None if v is None else round(v, 2))
                       for k, v in trails(a, P.dates, R0["start"]).items()},
            "monthly": [None if mo.get(x) is None else round(mo[x], 1) for x in ms],
            "nav": _thin([x * 100 for x in a]),
        }
    # 홈 표의 ETF 행에도 샤프를 적을 수 있게 **같은 창·같은 metrics** 로 잰다
    # (사용자 요청 2026-08-02 "메인에 샤프도 표시").
    # ⚠ 두 곳에서 따로 계산하면 창이 하루만 어긋나도 같은 열의 두 숫자가 비교 불가능해진다.
    #   이 표의 존재 이유가 비교라 그것만은 막아야 한다 — 그래서 market_board.py 가 아니라
    #   백테스트와 같은 자리에서, 같은 start·end 로 잰다.
    doc["etf_sharpe"] = {}
    # DIA·IWM 은 2026-08-03 에 홈 지수 줄에 더해지면서 함께 잰다(같은 창·같은 metrics).
    # RSP·SDY 는 2026-08-10 에 더했다(사용자 결정). 둘은 랩 방법론과 짝이 없어 홈 표에서
    #   빠져 있었는데, 짝이 없다는 것과 볼 필요가 없다는 것은 다르다 —
    #   🚨 특히 RSP(동일가중 S&P 500)가 중요하다. 이 랩의 종목 규칙은 대조군을 시총가중
    #     S&P 500 으로 두면 이기고 **랩 동일가중 유니버스로 두면 대부분 진다**(vs_traded).
    #     즉 '동일가중이 시총가중을 이겼다'가 성적의 큰 부분인데, 그 잣대의 실제 상품
    #     수익률이 홈 표에 없었다. 읽는 사람이 그 차이를 눈으로 볼 수단이 없었다는 뜻이다.
    for _tk in ETF_SHARPE_TK:
        _nv = bench_nav(P, P._align(P.A, _tk), R0["start"], R0["end"])
        if _nv is None:
            continue
        _sh = metrics(_nv)["sharpe"]
        doc["etf_sharpe"][_tk] = None if _sh is None else round(_sh, 2)

    # ── 5년 창 한 벌 더 ────────────────────────────────────────────────
    # 홈 표의 샤프 열 전용이다. 같은 backtest·같은 metrics 를 창만 바꿔 다시 돌린다 —
    # 여기서 따로 계산하면 ETF 행과 방법론 행이 다른 자로 재진다.
    # ⚠ 5년을 못 채우는 스타일(자료가 얕은 것)은 None 으로 남는다. 화면은 '—' 로 찍는다.
    global WINDOW
    _oldw, WINDOW = WINDOW, WINDOW5
    try:
        _s5, _e5, _tr5, _R5 = {}, {}, {}, None
        for _S in STYLES:
            _r = bt(P, _S[3])
            if not _r:
                continue
            if _R5 is None:
                _R5 = _r
            _m = metrics(_r["nav"])["sharpe"]
            _s5[_S[0]] = None if _m is None else round(_m, 2)
            # 홈 표의 3년·5년 칸도 이 창에서 나온다. 1년 창 산출물에는 있을 수 없는 값이라
            # 여기서만 만든다 — 없으면 그 두 칸이 방법론 줄에서만 통째로 빈다.
            _nv, _t5 = _r["nav"], {}
            for _lab, _n in (("3년", 756), ("5년", 1260)):
                # trails() 와 같은 규약 — 창보다 긴 구간은 창 시작으로 자른다.
                _t5[_lab] = (round((_nv[-1] / _nv[max(len(_nv) - 1 - _n, 0)] - 1) * 100, 2)
                             if len(_nv) > 1 else None)
            _tr5[_S[0]] = _t5
        if _R5 is not None:
            for _tk in ETF_SHARPE_TK:
                _nv = bench_nav(P, P._align(P.A, _tk), _R5["start"], _R5["end"])
                if _nv is None:
                    continue
                _sh = metrics(_nv)["sharpe"]
                _e5[_tk] = None if _sh is None else round(_sh, 2)
            doc["start5"] = P.dates[_R5["start"]]
        doc["style_sharpe5"], doc["etf_sharpe5"] = _s5, _e5
        doc["style_trails5"] = _tr5
        print("  5년 샤프 — 스타일 %d종 · ETF %d종 (창 %s~%s)"
              % (len(_s5), len(_e5), doc.get("start5") or "—", doc["as_of"]))
    finally:
        WINDOW = _oldw
    for S in detail:
        key, label, ref, _fn, mlab, mfmt, desc = S
        R = res[key]
        nav = R["nav"]
        _ms, mo = monthly(nav, P.dates, R["start"])
        wg, nw = win_rate(nav, gn, P.dates, R["start"])
        wn, _ = win_rate(nav, nn, P.dates, R["start"])

        def side(items, at_i, other):
            out = []
            for k, (t, sc, un) in enumerate(items):
                u = P.uni.get(t) or {}
                out.append({"r": k + 1, "t": t, "n": u.get("name") or "",
                            "s": SECS.get(u.get("sector") or "", ""), "idx": idx_of(P, t),
                            "new": t not in other, "mtd": _mtd_of(P, R, t),
                            "v": mfmt(P, at_i, t, sc, un)})
            return out

        ps = {t for t, _s, _u in R["prev"]}
        ns = {t for t, _s, _u in R["today"]}
        doc["styles"].append({
            "key": key, "label": label, "ref": ref, "desc": desc, "mlab": mlab,
            "n_rebal": R["n_rebal"],
            "metrics": {k: (None if v is None else round(v, 2)) for k, v in metrics(nav).items()},
            "trails": {k: (None if v is None else round(v, 2))
                       for k, v in trails(nav, P.dates, R["start"]).items()},
            "win": {"spx": [wg, nw], "ndx": [wn, nw]},
            "monthly": [None if mo.get(x) is None else round(mo[x], 1) for x in ms],
            "nav": _thin([x * 100 for x in nav]),
            "prev": {"d": P.dates[R["prev_i"]], "rows": side(R["prev"], R["prev_i"], ns)},
            "today": {"d": P.dates[R["today_i"]], "rows": side(R["today"], R["today_i"], ps)},
        })
    p = os.path.join(DATA, "style_perf.json")
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("→ %s (%dKB · 스타일 %d종)" % (p, os.path.getsize(p) // 1024, len(doc["styles"])))
    dump_trails(doc)


def dump_trails(doc):
    """홈(index.html)이 ETF 행 옆에 랩 행을 병기하려고 읽는 **슬림** 조각.

    style_perf.json 을 통째로 받게 하면 안 된다 — 28.9KB 중 홈이 쓰는 trails 는 486B(1.7%)
    뿐이고 나머지는 nav 곡선과 보유명단이다(gzip 기준 홈 전송량 +24%). index.html 이 스스로
    적어 둔 기준("4KB라 홈 슬림 묶음에 넣지 않고 직접 받는다")을 지키려면 1KB 짜리가 맞다.
    style.html 은 계속 style_perf.json 전체를 읽는다 — 그쪽은 곡선과 명단이 본문이다.
    """
    # 샤프를 함께 싣는다 — 홈이 이 값으로 지수 방법론 줄을 **정렬**하고 열에 적는다
    # (사용자 요청 2026-08-02). 창은 styles·etf_sharpe 가 전부 같다(start ~ as_of).
    _s5 = doc.get("style_sharpe5") or {}
    slim = {
        "as_of": doc["as_of"], "start": doc["start"],
        # 홈 샤프 열은 5년 창이다(위 WINDOW5). 1년 값도 같이 실어 둔다 — 두 창을 나란히
        # 볼 일이 생겼을 때 다시 굽지 않아도 되고, 5년이 없는 스타일의 물러섬이기도 하다.
        "start5": doc.get("start5"),
        "styles": [{"key": s["key"], "label": s["label"], "trails": s["trails"],
                    "sharpe": (s.get("metrics") or {}).get("sharpe"),
                    "sharpe5": _s5.get(s["key"]),
                    "trails5": (doc.get("style_trails5") or {}).get(s["key"])}
                   for s in doc["styles"]],
        "etf_sharpe": doc.get("etf_sharpe") or {},
        "etf_sharpe5": doc.get("etf_sharpe5") or {},
        # 홈도 같은 목록을 읽는다 — 두 화면이 갈리지 않게(위 HOME_HIDE 주석).
        "hide": doc.get("hide") or {},
    }
    # 유니버스 편향 실측치 몇 개를 여기 태워 보낸다 — 홈이 style_pit.json(5KB)을 따로 받지
    # 않게. 홈 각주가 이 값으로 문장을 만든다. 없으면 홈은 수치 없이 정성 문구만 낸다.
    try:
        j = json.load(io.open(os.path.join(DATA, "style_pit.json"), encoding="utf-8"))
        slim["pit"] = {
            "as_of": j["as_of"], "not_yet": j["universe"]["not_yet_member_at_start"],
            "today": j["universe"]["today"],
            "styles": {k: {"label": s["label"], "pub": s["published"]["ret"],
                           "pit": s["pit"]["ret"], "bias": s["bias"]["ret"],
                           "look": s["channel"]["lookahead"],
                           "surv": s["channel"]["survivorship"]}
                       for k, s in j["styles"].items()},
        }
    except Exception:
        pass
    if _SKIPPED:
        slim["skipped"] = dict(_SKIPPED)     # 화면이 '자료 없음'을 말할 수 있게 — 키가 매달리지 않는다
    p = os.path.join(DATA, "style_trails.json")
    json.dump(slim, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("→ %s (%dB · 스타일 %d종)" % (p, os.path.getsize(p), len(slim["styles"])))


def _mtd_of(P, R, t):
    """직전 월말 대비 오늘까지. draw_block 의 mtd 와 같은 정의다."""
    mi = max([j for j in P.me if j < R["end"]] or [R["start"]])
    a = P.px.get(t)
    if a is None or np.isnan(a[mi]) or a[mi] <= 0 or np.isnan(a[R["end"]]):
        return None
    return round((a[R["end"]] / a[mi] - 1) * 100, 1)


if __name__ == "__main__":
    raise SystemExit(main())
