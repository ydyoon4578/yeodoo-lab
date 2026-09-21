# -*- coding: utf-8 -*-
"""build/style8_pdf.py — 스타일 10종 한눈에 → data/style8.pdf (A4 5쪽)

무엇을. 홈 화면에 실리는 **스타일 10종**을 A4 다섯 쪽으로 뽑는다.
  ⚠ 파일 이름은 style8 그대로다 — 러너 잡과 얼린 사전등록이 그 이름을 부른다.
  1쪽  종합 ① 스타일 성과 — 기간별 수익률 표 · 월별 수익률 · 위험과 수익
  2쪽  종합 ② 기간별 수익률 1개월 — 위에서 아래로 넷: 지수 · 섹터 · 산업그룹 · **내 스타일 8종**(하이라이트)
        네 판은 같은 날짜 축(공통 구간) · 꼬리말 없음
  3~5쪽 스타일별 구성종목 (쪽당 넷 · 10종이면 4+4+2)

`style_top_pdf.py` 가 «오늘 무엇을 담나» 를 전략별 반 쪽으로 싣는다면, 이 문서는
**열 줄을 한 화면에 놓고 견주는** 자리다. 회의에 들고 갈 몇 장이 필요해서 만들었다.

판 이력(사용자 지시)
  2026-09-17  A4 2쪽(표 + 보유)
  2026-09-18  «기간별 수익률 차트도 넣고 정보 추가해서 4페이지로 구성해줘» → 4쪽
  2026-09-18  «기간별 수익률차트, 장기 성과, 누적수익률, 여러 스타일이 같이 든 종목, 섹터구성
              빼고 대신에 index.html 에 있는 기간별 수익률 4개 차트를 포함해줘. 1,2페이지는
              종합정보로 잘 구성하고, 3,4페이지는 스타일별 구성종목만» → 1·2쪽 종합 + 3·4쪽 구성종목
  2026-09-18  «2페이지 차트 기간 3개월로 해주고, 차트 위에서 하나씩 총 4개 만들어. 그리고 스타일
              빼고 내 스타일 8종으로 대체하고 하이라이트 표시해» → 2쪽 세로 4단
  2026-09-18  «4개 차트 다 일치해야해» → 네 판 공통 구간(_align)
  2026-09-22  «지수 방법론 8종에 고베타·성장 두 개 추가해서 10종으로» → KEYS 10 · 3~5쪽
  2026-09-18  «기간별 수익률은 1개월로 하자. 그리고 내 스타일 8종을 산업그룹 아래 배치해.
              아래 주석들은 다 삭제해 지저분해» → 지금 판

자료 — **계산하지 않는다.** 이미 구워진 파일을 그린다(숫자를 두 번 계산하면 조용히 갈린다).
  · data/style_perf.json      ← build/style_top_pdf.py --json   (1·3·4쪽 · 2쪽 내 스타일 = path)
  · data/home_perf.json       ← build/home_perf.py              (2쪽 — 홈 «기간별 수익률» 시계열)
  · data/home_ind_perf.json   ← 1일 밖 구간의 산업그룹 경로       (2쪽)
  🚨 2쪽은 홈과 **같은 자료·같은 규칙**이다(index.html drawStChart 를 옮겼다).
    지수는 고정색(CIX) · 섹터와 스타일은 끝값 순으로 11색을 돌려 쓰고 · 산업그룹은 **부모 섹터의
    색 + 선 모양**으로 가른다(반도체가 IT 색이라 옆 섹터 판과 같이 읽힌다). 선 끝에 «이름 값».
    산업그룹 축이 다르면(1일 분봉 ↔ 일간) 그 판을 뺀다 — 다른 잣대를 나란히 놓지 않는다.
  ⚠ 기본 구간은 **1개월**(사용자 지시 2026-09-18). 그 구간이 자료에 없으면 1주로 내려가고
    머리에 그렇게 적는다. `--horizon` 으로 바꿀 수 있다(내 스타일 판은 1주·1개월·3개월·6개월만).
  ⚠ 내 스타일 10종 판은 style_perf.json 의 path(날짜 붙은 원해상도 일별, 최근 1년)를 쓴다 —
    nav(140점 표시용 표본)는 날짜가 없어 못 쓴다. 끝값이 1쪽 표의 같은 칸과 같다.
    색은 줄마다 고정(MYCOL) · 벤치마크(S&P 500·NASDAQ 100 가격지수)는 회색.
  ⚠ 두 파일은 기준일이 다를 수 있다(러너가 따로 굽는다). 1쪽·2쪽 머리에 **각자의 기준일**을
    적는다 — 한 날짜로 뭉개지 않는다.
  ⚠ 산업그룹 이름은 영문 GICS(최장 47자)라 A4 반 폭에 안 들어간다 — GICS 한글명으로 적는다
    (옆 섹터 판이 한글이다). 표에 없는 이름은 영문 그대로.

판형·색·폰트·표는 `style_top_pdf.py` 에서 **그대로 가져온다**(그쪽이 정본이다).
2쪽 선 색만 홈 화면의 밝은 테마 토큰을 쓴다 — 같은 그림으로 읽히게. 홈 팔레트 뒤쪽 여섯
색(#7aa2f7 …)은 크림색 종이에서 흐리게 떠서 인쇄용으로 한 단계 진하게 눌렀다.

보유 표 — 전월말과 금일을 **한 표에 나란히** 둔다. style.html 과 같은 열이다.
  -티커 = 다음 재선정에서 빠지는 종목 · +티커 = 새로 들어오는 종목

    python build/style8_pdf.py                                  # data/ → data/style8.pdf
    python build/style8_pdf.py --horizon 3M                     # 2쪽 구간 바꾸기(기본 1M)
    python build/style8_pdf.py --src A --perf B --ind C --out D
      (매일 아침 작업이 origin/main 의 자료를 작업 트리 밖에서 읽어 공유폴더로 낼 때 쓴다 —
       ops/style8_daily/style8_daily.py)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 · 와 ⚠ 를 찍다 죽지 않게
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

from style_top_pdf import (ACC, INK, INK2, LINE, MUTED, NEG, PAPER, POS, RULE,  # noqa: E402
                           X0, X1, hline, new_page, require_draw, table, tx)

try:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.lines import Line2D
    import matplotlib.pyplot as plt
except Exception as e:                                        # pragma: no cover
    raise SystemExit("matplotlib 이 필요하다 — %s" % e)

SRC = os.path.join(DATA, "style_perf.json")
PERF = os.path.join(DATA, "home_perf.json")
IND = os.path.join(DATA, "home_ind_perf.json")
OUT = os.path.join(DATA, "style8.pdf")

# 홈 화면에 보이는 줄. style_perf.json 의 hide 목록 밖이 이것들이다 —
# 손으로 두 번 적지 않도록 여기서 한 번만 적고 아래에서 대조한다.
# 🚨 2026-09-21 사용자 결정 — 「표준 8종」으로 갈았다(build/style_top_pdf.py HOME_HIDE 주석).
#   나간 셋 qvm·grow·hbeta ← 들어온 셋 lowvol·fcfy·netbuy.
# 🚨 2026-09-22 사용자 결정 — **고베타·성장을 더해 10종.** 지시: *"지수 방법론 8종에
#   고베타 s&p500 high beta 랑 성장 s&p 500 growth(S&P U.S Style) 두개 추가해서 10종으로"*
#   ⚠ 파일 이름(style8_pdf.py · style8.pdf · style8.html)은 **안 바꾼다.** 러너 잡과
#     ops/style8_daily 가 그 이름을 부르고, PREREG-2026-09-18-STYLE8W·STYLE8ROT 가
#     그 이름으로 얼려 있다. 이름은 굳고 내용이 움직이는 것이 이 랩의 규약이다.
#   ⚠ 짝을 **나란히** 둔다 — val↔grow(같은 축 반대편) · lowvol↔hbeta(같은 축 반대편).
#     흩어 놓으면 둘이 한 축이라는 사실이 표에서 안 보인다.
KEYS = ["div", "val", "grow", "lowvol", "hbeta", "spmo", "size", "fcfy", "netbuy", "squal"]
TR = ["1일", "1주", "1개월", "3개월", "6개월", "1년", "YTD"]

# 섹터 약어를 펴서 쓴다 — 두 글자로는 회의에서 안 읽힌다.
SECTOR = {"부동": "부동산", "소재": "소재", "금융": "금융", "필소": "필수소비", "산업": "산업재",
          "유틸": "유틸리티", "헬스": "헬스케어", "커뮤": "커뮤니케이션", "경소": "경기소비",
          "에너": "에너지", "IT": "IT"}

# 방법론 한 줄 아래에 붙이는 산식. build/style_top_pdf.py 의 sc_* 함수에서 옮겼다.
#   ⚠ 지어내지 않는다. 산식이 바뀌면 그쪽을 고치고 여기를 따라 고친다.
GLOSS = {
    "div": "배당수익률 = 최근 4분기 주당배당금(선언 기준) ÷ 현재 주가",
    "val": "B/P = 주당순자산 ÷ 주가   E/P = 주당순이익(최근 4분기) ÷ 주가   "
           "S/P = 주당매출(최근 4분기) ÷ 주가 — 셋의 z 를 평균",
    "qvm": "퀄리티·가치·모멘텀 z 점수의 단순 평균 · 셋을 모두 가진 종목만 남긴다   "
           "여기 퀄리티는 MSCI 정의(ROE·부채비율·이익변동성)라 아래 퀄리티 줄과 다르다",
    "spmo": "(1개월 전 주가 ÷ 13개월 전 주가 - 1) ÷ 3년 주간수익률 표준편차   "
            "최근 1개월을 빼는 이유는 단기 반전을 피하려는 것",
    "size": "시가총액 = 주식수 × 주가 · 작을수록 상위",
    # ── 2026-09-21 표준 8종 교체로 들어온 셋 ──────────────────────────────
    "lowvol": "변동성 = 최근 252거래일 일간수익률 표준편차 × √252 · 낮을수록 상위   "
              "연속값이라 동점이 없다",
    "fcfy": "FCF수익률 = 최근 4분기 잉여현금흐름 ÷ 시가총액   "
            "※ 정본(COWZ)의 분모는 기업가치(EV)다 — 순부채 태그가 없어 시가총액을 쓴다",
    "netbuy": "순감소율 = (1년 전 주식수 ÷ 현재 주식수 - 1) · 늘었으면 음수   "
              "※ 분할 자르기 전 계열(sh_u)을 쓴다 — 대량발행 종목이 후보에서 사라지지 않게",
    # ── 2026-09-21 에 화면에서 빠진 셋. 산식은 남겨 둔다(자료·빌더는 그대로다) ──
    "grow": "3년 주당매출 연평균 성장률   3년 주당순이익 변화 ÷ 주가   12개월 모멘텀 — 셋의 z 를 평균",
    "hbeta": "베타 = 최근 252거래일 일간수익률의 시장과의 공분산 ÷ 시장 분산",
    "squal": "발생액비율 = (순이익 - 영업활동현금흐름) ÷ 평균 총자산 · 최근 4분기 합 기준   "
             "재무레버리지 = 부채총계 ÷ 자기자본",
}

# 보유 블록 — 3·4쪽이 구성종목만 싣게 되면서(섹터 구성·겹침 표를 뺐다) 남는 자리를 줄 높이로 돌렸다.
ROW_H = 0.0148         # 보유 표 한 줄(종전 .01175)
BLK_PER_PAGE = 4
BENCH_C = "#8C949C"    # 벤치마크 — 비교 대상이라 색을 빼고 회색으로(강조가 아니라 맥락)

# ── 2쪽 — 홈 «기간별 수익률» 판의 색(index.html 밝은 테마 토큰) ─────────────────
_ACC, _HOT, _DEP, _MARG, _CHAMP, _RP = "#816400", "#A64B3B", "#0C7A4A", "#A35510", "#2C6E8F", "#7A5AA6"
CIX = {"S&P 500": _ACC, "나스닥 100": _CHAMP, "다우존스 30": _MARG, "러셀 2000": _DEP}
# 홈 SECPAL 과 같은 순서. 뒤 여섯은 홈 값(#7aa2f7 #e0af68 #9ece6a #bb9af7 #2ac3de #f7768e)을
#   인쇄용으로 한 단계 진하게 눌렀다 — 화면 값 그대로면 크림색 종이에서 흐리게 뜬다.
SECPAL = [_ACC, _HOT, _DEP, _MARG, _CHAMP, "#4F74C9", "#A9782A", "#5E8F2F", "#7E5DB5", "#1B8AA1", "#C24F66"]
DASH = ["-", (0, (5, 2.5)), (0, (2, 2)), (0, (7, 2, 1.5, 2))]   # 같은 섹터 안 산업그룹을 가르는 선 모양
HZL = {"1D": "1일", "1W": "1주", "1M": "1개월", "3M": "3개월", "6M": "6개월", "12M": "1년", "YTD": "올해"}
PT = 1 / (11.69 * 72)  # 1pt 를 그림 세로 비율로
# 내 스타일 8종 — **줄마다 고정색**(끝값 순으로 돌리면 날마다 색이 바뀌어 매일 받는 문서에서 못 따라간다).
MYCOL = {"div": "#0C7A4A", "val": "#2C6E8F", "qvm": "#7E5DB5", "spmo": "#A64B3B",
         "size": "#A35510", "grow": "#4F74C9", "hbeta": "#816400", "squal": "#C24F66"}
HL = "#FFF4CC"         # 하이라이트 바탕(형광펜) — 내 스타일 판을 시장판 셋과 가른다
# 내 스타일 경로를 자르는 거래일 수 — build/style_top_pdf.py TRAIL 과 같다(그래야 끝값이 1쪽 표의 칸과 같다)
HN = {"1W": 5, "1M": 21, "3M": 63, "6M": 126}
TRL = {"1W": "1주", "1M": "1개월", "3M": "3개월", "6M": "6개월"}   # 1쪽 표의 칸 이름
# GICS 산업그룹 한글명 — 영문(최장 47자)은 A4 반 폭에 안 들어간다.
IND_KO = {
    "Energy": "에너지", "Materials": "소재", "Capital Goods": "자본재",
    "Commercial & Professional Services": "상업·전문 서비스", "Transportation": "운송",
    "Automobiles & Components": "자동차·부품", "Consumer Durables & Apparel": "내구소비재·의류",
    "Consumer Services": "소비자 서비스",
    "Consumer Discretionary Distribution & Retail": "경기소비 유통·소매",
    "Consumer Staples Distribution & Retail": "필수소비 유통·소매",
    "Food, Beverage & Tobacco": "식품·음료·담배", "Household & Personal Products": "가정·개인용품",
    "Health Care Equipment & Services": "헬스케어 장비·서비스",
    "Pharmaceuticals, Biotechnology & Life Sciences": "제약·바이오·생명과학",
    "Banks": "은행", "Financial Services": "금융 서비스", "Insurance": "보험",
    "Software & Services": "소프트웨어·서비스", "Technology Hardware & Equipment": "기술 하드웨어·장비",
    "Semiconductors & Semiconductor Equipment": "반도체·장비",
    "Telecommunication Services": "통신 서비스", "Media & Entertainment": "미디어·엔터테인먼트",
    "Utilities": "유틸리티", "Equity Real Estate Investment Trusts (REITs)": "리츠",
    "Real Estate Management & Development": "부동산 관리·개발",
}


def sgn(v, d=1):
    return "—" if v is None else ("%+.*f" % (d, v))


def ind_name(s):
    """산업그룹 영문 → 한글. 자료에 공백이 두 칸 든 이름이 있어(Biotechnology  &) 접고 찾는다."""
    k = " ".join(str(s).split())
    return IND_KO.get(k, k)


def _ax(fig, x, y, w, h):
    """그림 좌표(0~1)에 축을 하나 얹고 랩 판형에 맞게 가라앉힌다(격자·눈금은 뒤로)."""
    ax = fig.add_axes([x, y, w, h])
    ax.set_facecolor(PAPER)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
        ax.spines[s].set_linewidth(.6)
    ax.tick_params(colors=MUTED, labelsize=5.6, length=2, width=.5, pad=1.5)
    return ax


def section(fig, y, title, note=""):
    """쪽 안의 절 제목 + 오른쪽 작은 설명. 반환은 제목 아래 y."""
    tx(fig, X0, y, title, fontsize=10.5, weight="bold")
    if note:
        tx(fig, X1, y, note, fontsize=6.3, color=MUTED, ha="right")
    return y - .013


# ── 1쪽 · 종합 ① 스타일 성과 ──────────────────────────────────────────────────
def perf_rows(P, S):
    """기간별 수익률 표의 행 — 벤치마크 먼저, 그다음 샤프 내림차순. 월별·산점도도 이 순서를 쓴다."""
    rows, kinds, keys = [], [], []
    for bk, bx in (P.get("bench") or {}).items():
        bm, bt = bx.get("metrics") or {}, bx.get("trails") or {}
        rows.append([bx.get("label", bk), "벤치마크", "%.2f" % bm.get("sharpe", 0),
                     "%.1f" % bm.get("mdd", 0), "·"] + [sgn(bt.get(c)) for c in TR])
        kinds.append("b"); keys.append(bk)
    for k in sorted(KEYS, key=lambda z: -S[z]["metrics"]["sharpe"]):
        x, m, t = S[k], S[k]["metrics"], S[k]["trails"]
        w = (x.get("win") or {}).get("spx") or [0, 12]
        rows.append([x["label"], x["ref"].replace("S&P 500 ", "").replace("MSCI USA ", ""),
                     "%.2f" % m["sharpe"], "%.1f" % m["mdd"], "%d/%d" % (w[0], w[1])]
                    + [sgn(t.get(c)) for c in TR])
        kinds.append("s"); keys.append(k)
    return rows, kinds, keys


def draw_perf_table(fig, y, rows, kinds, row_h=.0152):
    # ⚠ 앞 두 열을 넓혔다(2026-09-18). 종전 .085·.175 에서 «NASDAQ 100 PR»(굵게)과
    #   «Quality, Value & Momentum (QVML)» 이 옆 칸 숫자 위로 넘쳤다. 합은 그대로 .884.
    W = [.108, .206, .053, .053, .054] + [.0586] * 7
    head = ["스타일", "지수", "샤프", "MDD", "이긴달"] + TR

    def pcol(r, c):
        if kinds[r] == "b" or c == 1:
            return MUTED
        if c == 3:
            return NEG
        if c >= 5:
            v = rows[r][c]
            return POS if v.startswith("+") else (NEG if v.startswith("-") else INK)
        return INK

    def pw(r, c):
        return "bold" if (kinds[r] == "b" and c == 0) or c == 2 else "normal"

    return table(fig, X0, y, W, head, rows, row_h=row_h, fs=7.4, hfs=6.8,   # ⚠ 7.8 이면 굵은 «NASDAQ 100 PR» 이 옆 칸을 밟는다
                 aligns=["l", "l"] + ["r"] * 10, cell_color=pcol, cell_weight=pw)


def draw_monthly(fig, y_top, P, S, keys, kinds, rh=.0158):
    """월별 수익률 히트맵 — 행 = 벤치 + 스타일(표와 같은 순서), 열 = 월.

    색은 **부호와 크기**(발산형: 빨강 − · 종이색 0 · 초록 +). 눈금은 ±10%p 에서 포화한다 —
    한두 달의 큰 값이 나머지를 다 옅게 만들지 않게. 숫자는 칸마다 적는다(색만으로 안 가른다).
    ⚠ 마지막 달은 기준일까지의 **진행 중** 수익이다.
    """
    months = P.get("months") or []
    n = len(months)
    lab_w = .118
    cw_ = (X1 - X0 - lab_w) / max(1, n)
    cmap = LinearSegmentedColormap.from_list("pn", [NEG, PAPER, POS])
    VMAX = 10.0
    y = y_top
    for c, mth in enumerate(months):
        lab = "%s/%s" % (mth[2:4], mth[5:7]) + ("*" if c == n - 1 else "")
        tx(fig, X0 + lab_w + c * cw_ + cw_ / 2, y - rh / 2, lab, fontsize=6.3,
           color=MUTED, ha="center", va="center")
    y -= rh
    hline(fig, X0, X1, y, RULE, .8)
    for i, k in enumerate(keys):
        src = P["bench"][k] if kinds[i] == "b" else S[k]
        mo = src.get("monthly") or []
        tx(fig, X0 + .004, y - rh / 2, src.get("label", k), fontsize=7.0, va="center",
           color=MUTED if kinds[i] == "b" else INK,
           weight="normal" if kinds[i] == "b" else "bold")
        for c in range(n):
            v = mo[c] if c < len(mo) else None
            x0 = X0 + lab_w + c * cw_
            if v is None:
                continue
            f = max(-1.0, min(1.0, v / VMAX))
            col = cmap((f + 1) / 2)
            fig.patches.append(plt.Rectangle((x0 + .0008, y - rh + .0008), cw_ - .0016, rh - .0016,
                                             transform=fig.transFigure, facecolor=col,
                                             edgecolor="none", zorder=1))
            tcol = PAPER if abs(f) > .55 else INK
            tx(fig, x0 + cw_ / 2, y - rh / 2, "%+.1f" % v, fontsize=6.3, color=tcol,
               ha="center", va="center")
        y -= rh
        if i == 1:
            hline(fig, X0, X1, y, RULE, .6)      # 벤치 둘과 스타일 여덟 사이
    hline(fig, X0, X1, y, RULE, .8)
    return y


def draw_risk_return(fig, y_top, h, P, S, keys, kinds):
    """위험과 수익 — 가로 = 1년 변동성, 세로 = 1년 수익률(둘 다 metrics, 같은 창).

    원점에서 벤치(S&P)를 지나는 점선 = «S&P 와 같은 샤프». 그 선보다 위면 위험 한 단위에
    더 벌었다는 뜻이다(무위험 차감 전이라 근사 — 표의 샤프가 정본이다).
    """
    ax = _ax(fig, X0 + .045, y_top - h, X1 - X0 - .060, h - .010)
    pts = []
    for i, k in enumerate(keys):
        src = P["bench"][k] if kinds[i] == "b" else S[k]
        m = src.get("metrics") or {}
        pts.append((m.get("vol"), m.get("ret"), src.get("label", k), kinds[i]))
    vx = [p[0] for p in pts if p[0] is not None]
    vy = [p[1] for p in pts if p[1] is not None]
    xmax, ymax = max(vx) * 1.12, max(vy) * 1.18
    ymin = min(0, min(vy)) - 2
    sp = next((p for p in pts if p[3] == "b"), None)
    if sp and sp[0]:
        slope = sp[1] / sp[0]
        ax.plot([0, xmax], [0, slope * xmax], color=BENCH_C, lw=.7, ls=(0, (3, 2)), zorder=1)
        # 글씨는 선의 60% 지점 **아래**에 — 오른쪽 끝에 두면 고수익 스타일 라벨과 겹친다
        ax.text(xmax * .60, slope * xmax * .60 - (ymax - ymin) * .035, "S&P 와 같은 수익/위험",
                fontsize=5.8, color=MUTED, ha="left", va="top")
    # 🚨 이름표를 전부 점 오른쪽 같은 높이에 두면 y 가 가까운 것끼리 겹친다. 8종일 때도
    #   빽빽했고 10종이 되자 «주식수감소·중소형·NASDAQ 100 PR» 셋이 한 덩어리로 뭉갰다.
    #   아래에서 위로 훑으며 최소 간격을 못 지키면 **위로 밀어낸다**. 많이 밀린 것은
    #   점과 글씨를 가는 선으로 잇는다 — 어느 점의 이름인지 잃지 않게.
    okp = [p for p in pts if p[0] is not None and p[1] is not None]
    for vol, ret, lab, kd in okp:
        ax.scatter([vol], [ret], s=30 if kd == "s" else 22, zorder=3,
                   color=(BENCH_C if kd == "b" else ACC), edgecolor=PAPER, linewidth=.8)
    gap = (ymax - ymin) * .042          # 6.8pt 글씨 한 줄 높이(실측으로 맞춘 눈금)
    last = None
    for vol, ret, lab, kd in sorted(okp, key=lambda p: p[1]):
        ly = ret if last is None else max(ret, last + gap)
        if ly - ret > gap * .35:        # 눈에 띄게 밀렸으면 점과 잇는다
            ax.plot([vol, vol + xmax * .010], [ret, ly], color=LINE, lw=.5, zorder=2)
        ax.text(vol + xmax * .012, ly, lab, fontsize=6.8, va="center",
                color=MUTED if kd == "b" else INK, weight="normal" if kd == "b" else "bold")
        last = ly
    ax.set_xlim(0, xmax)
    ax.set_ylim(ymin, ymax)
    ax.grid(True, color=LINE, lw=.4, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=6.0)
    ax.set_xlabel("1년 변동성 (%)", fontsize=6.5, color=MUTED, labelpad=2)
    ax.set_ylabel("1년 수익률 (%)", fontsize=6.5, color=MUTED, labelpad=2)
    return y_top - h


# ── 2쪽 · 종합 ② 홈 «기간별 수익률» 네 판 ──────────────────────────────────────
def _last(v):
    """마지막 유효값과 그 자리. 없으면 (None, None)."""
    for i in range(len(v or []) - 1, -1, -1):
        if v[i] is not None:
            return v[i], i
    return None, None


def _ranked(d):
    """끝값 내림차순 — 홈 JS 의 sort(b.last - a.last). 끝값이 없으면 맨 뒤."""
    return sorted((d or {}).items(),
                  key=lambda kv: -(_last(kv[1])[0] if _last(kv[1])[0] is not None else -1e9))


def _em(s):
    """글자 폭 어림(em) — 한글 1 · 빈칸 .3 · 그 밖 .55. 제목 옆 글씨를 제목 끝에 붙이는 데만 쓴다."""
    return sum(1.0 if ord(c) >= 0x2E80 else (.3 if c == " " else .55) for c in s)


def _nice_step(span):
    """y 눈금 간격 — 홈과 같은 규칙(범위/5 에 가장 가까운 1·2·2.5·5·10 × 10^k)."""
    import math
    raw = span / 5
    mag = 10 ** math.floor(math.log10(raw))
    return min((1, 2, 2.5, 5, 10), key=lambda b: abs(b * mag - raw)) * mag


def _xticks(dates, intraday):
    """x 눈금 — 홈 규칙(달이 바뀌는 날 · 분봉은 시가 바뀌는 때 중 고르게 넷).

    ⚠ 1주·1개월은 달이 한 번도 안 바뀌어 눈금이 하나뿐이 된다(홈 화면도 그렇다). 종이에서는
      날짜를 못 짚으므로 그때만 고르게 넷을 찍고 월/일로 적는다.
    """
    n = len(dates)
    mk, pm = [], None
    for i, d in enumerate(dates):
        m = str(d)[:2] if intraday else str(d)[:7]
        if m != pm:
            mk.append(i); pm = m
    want = min(4, len(mk))
    pick = sorted({mk[int(q * (len(mk) - 1) / max(1, want - 1) + .5)] for q in range(want)})
    # 첫 눈금이 둘째와 너무 붙으면(3개월: 06-18 다음 07-01) 글씨가 겹친다 — 첫 것을 뺀다
    if len(pick) >= 3 and pick[1] - pick[0] < n * .18:
        pick = pick[1:]
    if intraday:
        return pick, [str(dates[i]) for i in pick]
    if len(pick) >= 3:
        return pick, [str(dates[i])[2:7] for i in pick]
    pick = sorted({0, n // 3, (2 * n) // 3, n - 1}) if n > 3 else list(range(n))
    return pick, ["%s/%s" % (str(dates[i])[5:7], str(dates[i])[8:10]) for i in pick]


def draw_home_panel(fig, cx, top, cw, h, title, dates, series, intraday, lab_w, dashes=False, fx=None,
                    right="", count=None, title_color=INK, face=PAPER):
    """판 하나. series = [(이름, 값[], 색, 선모양[, 'b'])] — 끝값 내림차순으로 이미 정렬돼 있다.

    홈 JS chart() 와 같은 요소: y 눈금(보기 좋은 간격) · x 눈금 넷 · 0 아래 옅은 바탕 · 끝점 ·
    선 끝 «이름 값» 라벨(겹치면 민다 · 민 만큼 가는 선으로 끝점과 잇는다) · 산업그룹은 라벨 앞에
    선 모양 견본. 라벨 글씨는 선 색이다(홈과 같다 — 여기서는 색이 곧 개체다).
    다섯째 칸이 'b' 인 줄은 벤치마크다 — 회색 가는 선 · 보통 굵기 라벨(비교 대상이지 주인공이 아니다).
    right = 판 오른쪽 위 글씨(구간) · count = 제목 옆 회색 글씨(없으면 «· N개»).
    """
    import math
    n = len(dates)
    lots = len(series) > 12
    cnt = ("· %d개" % len(series)) if count is None else count
    tw = _em(title) * 8.8 / 595 + .006                      # 제목 폭(그림 비율) + 사이
    tx(fig, cx, top + .0035, title, fontsize=8.8, weight="bold", va="bottom", color=title_color)
    tx(fig, cx + tw, top + .0038, cnt, fontsize=6.4, color=MUTED, va="bottom")
    if right:
        tx(fig, cx + cw, top + .0038, right, fontsize=6.3, va="bottom", ha="right",
           color=MUTED if title_color == INK else title_color)
    ax_x = cx + .030                                         # 왼쪽 y 눈금 자리
    ax_w = cw - .030 - lab_w
    y0 = top - h
    ax = fig.add_axes([ax_x, y0, ax_w, h])
    ax.set_facecolor(face)
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=5.7, length=0, pad=2.5)

    allv = [v for t in series for v in t[1] if v is not None]
    lo, hi = min(0.0, min(allv, default=0.0)), max(0.0, max(allv, default=0.0))
    if hi - lo < 1:
        hi += .5; lo -= .5
    pad = (hi - lo) * .08
    hi += pad; lo -= pad
    ax.set_xlim(0, max(1, n - 1))
    ax.set_ylim(lo, hi)

    st = _nice_step(hi - lo)
    t = math.ceil(lo / st) * st
    ticks = []
    while t <= hi + 1e-9:
        z = abs(t) < 1e-9
        ax.axhline(t, color=RULE if z else LINE, lw=.8 if z else .5, zorder=1)
        ticks.append(0.0 if z else t)
        t += st
    ax.set_yticks(ticks)
    # ⚠ 간격이 2.5 면 정수로 찍을 수 없다(홈 JS 는 Math.round 라 +2.5 가 +3 으로 찍힌다 — 따라 하지 않는다)
    frac = abs(st - round(st)) > 1e-9
    ax.set_yticklabels([("+" if v > 0 else "") + (("%.1f" % v) if frac else ("%d" % round(v)))
                        for v in ticks])
    ax.axhspan(lo, 0, color=_HOT, alpha=.05, lw=0, zorder=0)       # 0 아래 = 손실 구간
    xt, xl = _xticks(dates, intraday)
    for i in xt:
        ax.axvline(i, color=LINE, lw=.5, alpha=.8, zorder=1)
    ax.set_xticks(xt)
    ax.set_xticklabels(xl, fontsize=5.7)

    if fx and len(fx) == n:                                  # 원/달러 배경선(지수 판만 · 1일엔 없다)
        fv = [v for v in fx if v is not None]
        if len(fv) > 1:
            ax2 = ax.twinx()
            for sp_ in ax2.spines.values():
                sp_.set_visible(False)
            b_lo, b_hi = min(fv), max(fv)
            if b_hi - b_lo < 1:
                b_hi += 1; b_lo -= 1
            bp = (b_hi - b_lo) * .30
            ax2.set_ylim(b_lo - bp, b_hi + bp)
            ax2.plot(range(n), fx, color=_RP, lw=1.0, alpha=.3, zorder=0)
            ax2.set_yticks([])
            # 글씨는 판 제목 바로 뒤에 — 오른쪽 끝에 두면 구간 글씨를 밟는다
            tx(fig, cx + tw + _em(cnt) * 6.4 / 595 + .014, top + .0038,
               "배경 = 원/달러  %s → %s" % (format(round(fv[0], 1), ",.1f"), format(round(fv[-1], 1), ",.1f")),
               fontsize=5.8, color=_RP, va="bottom")

    labs = []
    for t in series:
        nm, vals, col, ls = t[:4]
        bench = len(t) > 4 and t[4] == "b"
        xs = [i for i, v in enumerate(vals) if v is not None]
        ys = [v for v in vals if v is not None]
        if not xs:
            continue
        ax.plot(xs, ys, color=col, lw=.8 if bench else (.85 if lots else 1.15), ls=ls,
                alpha=.92 if lots else 1, zorder=2 if bench else 3,
                solid_capstyle="round", solid_joinstyle="round")
        ax.scatter([xs[-1]], [ys[-1]], s=4 if lots else 7, color=col, zorder=4, lw=0)
        yf = y0 + h * (ys[-1] - lo) / (hi - lo)
        xf = ax_x + ax_w * (xs[-1] / max(1, n - 1))
        labs.append({"nm": nm, "v": ys[-1], "col": col, "ls": ls, "x": xf, "y": yf, "b": bench})

    # 🚨 라벨 겹침 — 홈과 같은 세 단계: ① 위에서부터 최소 간격만큼 아래로 민다 ② 바닥을 넘으면
    #   뭉치를 통째로 올린다 ③ 그래도 위를 넘으면 위 경계에서 멈춘다(잘리느니 겹치는 편이 낫다).
    fs = 5.6 if lots else 6.6
    topl, botl = top - .002, y0 + .002
    gap = fs * 1.22 * PT
    if len(labs) > 1:
        gap = max(fs * .98 * PT, min(gap, (topl - botl) / (len(labs) - 1)))
    labs.sort(key=lambda L: -L["y"])
    prev = 1e9
    for L in labs:
        L["ly"] = min(L["y"], prev - gap); prev = L["ly"]
    if labs and labs[-1]["ly"] < botl:
        over = botl - labs[-1]["ly"]
        for L in labs:
            L["ly"] += over
    if labs and labs[0]["ly"] > topl:
        up = labs[0]["ly"] - topl
        room = labs[-1]["ly"] - botl
        mv = min(up, max(0, room))
        for L in labs:
            L["ly"] = min(L["ly"] - mv, topl)
    rx = ax_x + ax_w
    for L in labs:
        fig.add_artist(Line2D([L["x"] + .002, rx + .007], [L["y"], L["ly"]], color=L["col"], lw=.45,
                              alpha=.5, transform=fig.transFigure, zorder=2))
        tx0 = rx + .010
        if dashes:                                           # 같은 색이 여럿 — 선 모양 견본으로 짝짓기
            fig.add_artist(Line2D([rx + .009, rx + .027], [L["ly"], L["ly"]], color=L["col"], lw=1.1,
                                  ls=L["ls"], transform=fig.transFigure, zorder=3))
            tx0 = rx + .031
        tx(fig, tx0, L["ly"], "%s  %+.2f" % (L["nm"], L["v"]), fontsize=fs, color=L["col"],
           va="center", weight="normal" if L["b"] else "bold")
    return ax


def my_styles(P, hz):
    """내 스타일 8종 + 벤치마크 둘 — style_perf.json 의 path(날짜 붙은 원해상도 일별)에서.

    반환 (rows, dates, lab) · 못 그리면 (None, 사유, None).
      rows = {이름: (값[] — 경로 첫날 0 인 누적 %, 색, 선모양, 벤치마크인가)} — 스타일 여덟만 · 경로 전체
      lab  = (시작, 끝) — 1쪽 표의 같은 칸(trails)이 재는 구간. 2쪽 공통 구간과 견주는 데 쓴다.
    ⚠ nav(140점 표시용 표본)를 쓰지 않는다 — 날짜가 없어 «3개월 전 그날» 을 못 짚는다.
    """
    n = HN.get(hz)
    pdts = (P or {}).get("path_dates") or []
    if not n:
        return None, "%s 구간은 내 스타일 일별 경로가 없다(최근 1년까지 싣는다)" % HZL.get(hz, hz), None
    if len(pdts) < n + 1:
        return None, ("style_perf.json 에 %s 치 일별 경로(path)가 아직 없다 — 러너가 다음에 구울 때 실린다"
                      % HZL.get(hz, hz)), None
    S = {x["key"]: x for x in P.get("styles") or []}

    def seg(p):
        # 경로 **전체**(최근 1년 · 2026-09-21 에 126→252거래일로 늘렸다)를 첫 점 대비 누적 % 로 넘긴다 — 몇 거래일로 자를지는 _align 이
        #   네 판 공통 날짜 격자에서 정한다(여기서 자르면 판마다 기준일이 갈린다).
        if not p or len(p) < n + 1 or not p[0]:
            return None
        return [None if v is None else (v / p[0] - 1) * 100 for v in p]

    rows = {}
    for k in KEYS:
        v = seg((S.get(k) or {}).get("path"))
        if v is None:
            return None, "%s 의 일별 경로가 자료에 없다" % ((S.get(k) or {}).get("label", k)), None
        rows[S[k]["label"]] = (v, MYCOL.get(k, _ACC), "-", False)
    # ⚠ 벤치마크(회색)는 여기서 싣지 않는다 — style_perf 의 bench 는 ^GSPC·^NDX **가격지수**라
    #   바로 위 지수 판(SPY·QQQ, 홈과 같은 원자료)과 같은 구간에서도 값이 갈린다
    #   (09-18 실측 06-18~09-16: 가격지수 +0.68 vs 지수 판 +0.98 — 6월 배당락 몫).
    #   한 쪽 안에 «S&P 500» 이 두 값이면 안 된다 → draw_home_page 가 지수 판의 선을 그대로 옮긴다.
    return rows, pdts, (pdts[-(n + 1)], pdts[-1])


def _align(panels, n=None):
    """네 판을 **같은 날짜 축**으로 — panels = {판: (날짜[], {줄: 값[]})} (값 = 그 판 첫날 대비 누적 %).

    공통 구간 = [가장 늦은 시작, 가장 이른 끝] 안에서 **모든 판에 있는 날짜**만 남기고,
    그 첫날을 0 으로 다시 잰다: (1 + v/100) ÷ (1 + v_첫날/100) − 1. 누적 % 라 나눗셈 하나로 끝난다
    (새로 계산하는 것이 아니라 같은 곡선의 기준점만 옮긴다).
    n 을 주면 공통 날짜의 **마지막 n+1 개**만 쓴다 = 끝날에서 n 거래일 수익률. 1쪽 표(trails)와 같은
    규약이라, 격자가 같으면 내 스타일 끝값이 1쪽 표의 같은 칸과 **같다**(09-18 실측: 하루 어긋나면
    모멘텀 1개월이 -15.17 vs -8.31 — 08-18 하루 -7.47% 가 통째로 빠진다). 공통 날짜가 n+1 에
    못 미치면 있는 만큼(가장 늦은 시작부터) 쓴다.
    반환 (맞춘 panels, 공통 날짜[]) — 맞출 수 없으면(겹치는 날 < 2) 원래 것을 그대로.
    """
    S = max(d[0] for d, _ in panels.values())
    E = min(d[-1] for d, _ in panels.values())
    common = set.intersection(*[{x for x in d if S <= x <= E} for d, _ in panels.values()])
    cd = sorted(common)
    if n and len(cd) > n + 1:
        cd = cd[-(n + 1):]
    if len(cd) < 2:
        return panels, None
    out = {}
    for nm, (d, rows) in panels.items():
        pos = {x: i for i, x in enumerate(d)}
        ii = [pos[x] for x in cd]
        new = {}
        for k, vals in rows.items():
            v = [vals[i] if i < len(vals) else None for i in ii]
            b = v[0]
            new[k] = ([None] * len(v) if b is None else
                      [None if x is None else ((1 + x / 100) / (1 + b / 100) - 1) * 100 for x in v])
        out[nm] = (cd, new)
    return out, cd


def draw_home_page(fig, HP, IP, P, horizon):
    """2쪽 — 판 넷을 **위에서 아래로 한 줄씩**(사용자 지시 2026-09-18 «차트 위에서 하나씩 총 4개»).

    지수 → **내 스타일 8종**(하이라이트) → 섹터 → 산업그룹. 홈의 «스타일»(스타일 ETF) 판은 뺐다
    (같은 지시 «스타일 빼고 내 스타일 8종으로 대체하고 하이라이트 표시해»).
    🚨 네 판은 **같은 날짜 축**이다(같은 날 지시 «4개 차트 다 일치해야해»). 자료가 셋이라 끝날과
      시작날이 갈린다 —
        · 끝날: 지수·섹터는 자산 패널(assets.json), 내 스타일·산업그룹은 **종목 가격 패널**
          (stocks.json)에서 나온다. 종목 패널이 그날 봉을 못 받으면 하루 뒤처진다
          (09-18 실측: 지수·섹터 09-17 · 내 스타일·산업그룹 09-16 — 06:50 KST 갱신이 09-17 을 못 받았다).
        · 시작날: 홈 3개월은 달력 91일 전(market_board._base_dates), 랩 3개월은 63거래일 전
          (style_top_pdf.TRAIL) — 같은 «3개월» 이 하루 이틀 다르다.
      → _align 으로 공통 구간에 맞추고 첫날을 0 으로 다시 잰다. 잘린 판이 있으면 꼬리말에 붉게 적는다.
    ⚠ 1일(분봉)은 내 스타일이 없고 나머지 셋은 같은 분봉 격자라 맞추지 않는다.
    판 폭·라벨 칸을 전부 같게 둬 네 판의 x 축이 세로로 맞는다.
    """
    series = HP.get("series") or {}
    hz = horizon if horizon in series else ("1W" if "1W" in series else next(iter(series), None))
    y = .962
    tx(fig, X0, y, "기간별 수익률 · %s" % HZL.get(hz, hz or "—"), fontsize=17, weight="bold")
    tx(fig, X1, y + .002, "여두 전략 랩 · 홈 화면 차트 + 내 스타일 10종", fontsize=8, color=ACC, ha="right")
    if hz is None:
        tx(fig, X0, .9, "기간별 수익률 시계열(home_perf.json)에 구간이 하나도 없다", fontsize=9, color=NEG)
        return
    blk = series[hz]
    intraday = bool(blk.get("intraday"))
    # 🚨 1주·1개월·3개월은 **일간 3개월 계열**(솎지 않은 63점)에서 자른다. 홈의 1개월 계열은 홈 기준일에서
    #   달력 30일 전부터라, 종목 패널이 하루 늦은 날엔 공통 구간이 1쪽 표의 «1개월»(21거래일)보다 하루
    #   짧아진다. 더 긴 일간 계열을 받아 두면 _align 이 공통 격자에서 정확히 n 거래일을 잘라 낸다.
    #   ⚠ 6개월 이상은 홈 계열이 90점으로 솎여 있어 그 구간 자체 계열을 쓴다.
    dsrc = hz if (intraday or hz not in ("1W", "1M", "3M") or "3M" not in series) else "3M"
    blk = series[dsrc] if not intraday else blk
    dates = blk.get("dates") or []
    sdates = blk.get("sec_dates") or dates
    y_sub = y - .017
    hline(fig, X0, X1, y_sub - .012, RULE, .9)

    # ── 판별 자료(값 = 그 판 첫날 대비 누적 %) ─────────────────────────────────
    # 산업그룹 — 1일은 blk 안에(ind·ind_sec), 나머지 구간은 별도 파일(home_ind_perf).
    #   축이 다르면(분봉 ↔ 일간) 판을 뺀다 — 홈 iSkip 과 같은 규칙.
    if blk.get("ind"):
        iblk, isec = {"dates": dates, "ind": blk["ind"], "intraday": True}, blk.get("ind_sec") or {}
    else:
        iblk = ((IP or {}).get("series") or {}).get(dsrc) or ((IP or {}).get("series") or {}).get(hz)
        isec = (IP or {}).get("sec") or {}
    iskip = bool(iblk) and bool(iblk.get("intraday")) != intraday
    if iskip:
        iblk = None
    myrows, mdates, mlab = my_styles(P, hz)
    panels = {"지수": (dates, dict(blk.get("ix") or {})), "섹터": (sdates, dict(blk.get("sec") or {}))}
    if myrows:
        panels["내 스타일"] = (mdates, {k: v[0] for k, v in myrows.items()})
    if iblk and iblk.get("ind"):
        panels["산업그룹"] = (iblk.get("dates") or [], dict(iblk["ind"]))
    fx = None if intraday else blk.get("fx")
    cd = None
    if not intraday and len(panels) > 1:
        panels2, cd = _align(panels, HN.get(hz))
        if cd:
            print("  2쪽 공통 구간 %s ~ %s (%d%s)%s" % (
                cd[0], cd[-1], len(cd) - 1, "거래일" if dsrc in ("1W", "1M", "3M") else "구간 · 솎은 계열",
                "" if not mlab else (" · 1쪽 «%s» 칸과 같은 구간" % TRL.get(hz, hz) if mlab == (cd[0], cd[-1])
                                     else " · ⚠ 1쪽 «%s» 칸(%s~%s)과 다른 구간" % (TRL.get(hz, hz), mlab[0], mlab[1]))))
            if fx and len(fx) == len(dates):
                _fp = {x: i for i, x in enumerate(dates)}
                fx = [fx[_fp[x]] for x in cd]            # 지수 판과 같은 칸만
            panels = panels2
    pdates = {nm: d for nm, (d, _) in panels.items()}

    # ── 판별 줄 세우기·색 — 맞춘 **뒤**에 한다(끝값 순이 바뀔 수 있다 · 섹터·산업그룹 색은 끝값 순) ─
    def _rank(rows):
        return sorted(rows.items(),
                      key=lambda kv: -(_last(kv[1])[0] if _last(kv[1])[0] is not None else -1e9))
    ix = [(k, v, CIX.get(k, _ACC), "-") for k, v in _rank(panels["지수"][1])]
    sec = [(k, v, SECPAL[i % len(SECPAL)], "-") for i, (k, v) in enumerate(_rank(panels["섹터"][1]))]
    csec = {k: c for k, _v, c, _ls in sec}
    ind, seen = [], {}
    if "산업그룹" in panels:
        for i, (k, v) in enumerate(_rank(panels["산업그룹"][1])):
            parent = isec.get(k)
            key = parent or ("_%d" % i)
            j = seen.get(key, 0); seen[key] = j + 1
            ind.append((ind_name(k), v, csec.get(parent) or SECPAL[i % len(SECPAL)], DASH[j % len(DASH)]))
    mys = None
    if "내 스타일" in panels:
        rows_ = dict(panels["내 스타일"][1])
        # 회색 기준선 = **바로 위 지수 판의 선 그대로**(같은 날짜 축에 맞춘 뒤라 값이 한 치도 안 다르다)
        if cd:
            for nm_, ls_ in (("S&P 500", "-"), ("나스닥 100", (0, (4, 2)))):
                if nm_ in panels["지수"][1]:
                    rows_[nm_] = panels["지수"][1][nm_]
                    myrows[nm_] = (None, BENCH_C, ls_, True)
        mys = [(k, v, myrows[k][1], myrows[k][2]) + (("b",) if myrows[k][3] else ())
               for k, v in _rank(rows_)]

    def rng(ds):
        return (("%s ~ %s ET" if intraday else "%s ~ %s") % (ds[0], ds[-1])) if ds else ""

    # ── 머리 한 줄 — 공통 구간을 적는다 ─────────────────────────────────────
    if cd:
        head = "%s ~ %s · 네 판 같은 날짜 · 달러 기준 · 선 끝 숫자 = 누적 수익률(%%)" % (cd[0], cd[-1])
    else:
        head = (("1일 = 전일 종가 대비 · 미 동부 분봉 · " if intraday else "")
                + "달러 기준 · 선 끝 숫자 = 구간 누적 수익률(%)")
    tx(fig, X0, y_sub, head, fontsize=6.8, color=MUTED)
    if hz != horizon:
        tx(fig, X1, y_sub, "※ %s 구간이 아직 자료에 없어 대신 %s 구간을 그렸다" % (HZL.get(horizon, horizon), HZL.get(hz, hz)),
           fontsize=6.8, color=NEG, ha="right")

    W = X1 - X0
    LAB = .170          # 라벨 칸 — 가장 긴 산업그룹명(선 모양 견본 포함)이 들어가는 폭을 네 판이 같이 쓴다
    # 판 순서(사용자 지시 2026-09-18 «내 스타일 8종을 산업그룹 아래 배치해»): 지수 · 섹터 · 산업그룹 · 내 스타일
    # ⚠ 꼬리말은 없다(같은 지시 «아래 주석들은 다 삭제해 지저분해»). 그 자리를 판 높이로 돌렸다.
    H = (.133, .172, .222, .197)
    GAP = .041          # 판 사이 = x 눈금 글씨 .013 + 여백 .012 + 다음 판 제목 .016
    top = .905
    # ① 지수 — 원/달러 배경선(일간 구간만)
    draw_home_panel(fig, X0, top, W, H[0], "지수", pdates["지수"], ix, intraday, LAB,
                    fx=fx, right=rng(pdates["지수"]))
    top -= H[0] + GAP
    # ② 섹터
    draw_home_panel(fig, X0, top, W, H[1], "섹터", pdates["섹터"], sec, intraday, LAB, right=rng(pdates["섹터"]))
    top -= H[1] + GAP
    # ③ 산업그룹
    if ind:
        draw_home_panel(fig, X0, top, W, H[2], "산업그룹", pdates["산업그룹"], ind, intraday, LAB,
                        dashes=True, right=rng(pdates["산업그룹"]))
    else:
        tx(fig, X0, top + .0035, "산업그룹", fontsize=8.8, weight="bold", va="bottom")
        tx(fig, X0, top - .02, ("1일은 분봉 경로라 일간 산업그룹 판을 나란히 놓지 않는다(홈과 같은 규칙)"
                                if iskip else "이 구간의 산업그룹 경로가 자료에 없다"),
           fontsize=6.6, color=MUTED)
    top -= H[2] + GAP
    # ④ 내 스타일 8종 — 하이라이트: 형광 바탕 + 왼쪽 굵은 띠 + 제목·구간 글씨를 랩 색으로
    b0, b1 = top - H[3] - .019, top + .021
    # ⚠ zorder 는 축(0)보다 낮게 — 같은 0 이면 그림이 축을 먼저 그리고 바탕을 위에 덮는다(실측: 판이 통째로 가려졌다)
    fig.patches.append(plt.Rectangle((X0 - .014, b0), W + .020, b1 - b0, transform=fig.transFigure,
                                     facecolor=HL, edgecolor="none", zorder=-1))
    fig.add_artist(Line2D([X0 - .014, X0 - .014], [b0, b1], color=ACC, lw=3.2, solid_capstyle="butt",
                          transform=fig.transFigure, zorder=1))
    if mys:
        draw_home_panel(fig, X0, top, W, H[3], "내 스타일 10종", pdates["내 스타일"], mys, False, LAB,
                        right=rng(pdates["내 스타일"]), count="· 회색 = 지수 판의 S&P 500·나스닥 100",
                        title_color=ACC, face=HL)
    else:
        tx(fig, X0, top + .0035, "내 스타일 10종", fontsize=8.8, weight="bold", va="bottom", color=ACC)
        tx(fig, X0, top - .02, mdates, fontsize=6.8, color=NEG)


# ── 3·4쪽 · 스타일별 구성종목 ─────────────────────────────────────────────────
def draw_block(fig, x, key, y, HW):
    """스타일 한 블록 — 제목 · 방법론 · 산식 · 전월말/금일 한 표. 반환은 다음 y."""
    pv, td = (x.get("prev") or {}), (x.get("today") or {})
    pr, tr_ = pv.get("rows") or [], td.get("rows") or []
    pvt, tdt = {r["t"] for r in pr}, {r["t"] for r in tr_}
    nin = len([r for r in tr_ if r["t"] not in pvt])

    tx(fig, X0, y, x["label"], fontsize=11, weight="bold")
    # ⚠ 지수명 자리를 제목 글자 수로 민다 — «멀티팩터»(4자)가 고정 .072 에서 겹쳤다
    tx(fig, X0 + max(.072, .024 + .0165 * len(x["label"])), y, x["ref"], fontsize=7.2, color=ACC)
    tx(fig, X1, y, "교체 %d종" % nin if nin else "교체 없음", fontsize=6.4,
       color=MUTED, ha="right")
    y -= .0098
    hline(fig, X0, X1, y, RULE, .8)
    y -= .0090
    desc = [l.strip() for l in x["desc"].split("\n") if l.strip()]
    first = desc[0] if desc else ""
    i = first.find(". ")
    tx(fig, X0, y, first[:i + 1] if i > 0 else first, fontsize=7.0, color=INK2)
    y -= .0104          # 종전 .0082·.0092 — 설명과 산식이 붙어 보였다(글씨 높이만 .0090)
    if key in GLOSS:
        tx(fig, X0, y, GLOSS[key], fontsize=6.0, color=MUTED)
        y -= .0100      # 종전 .0078·.0092 — 산식과 «전월말 기준» 줄이 맞닿아 있었다

    mlab = x.get("mlab", "")
    tx(fig, X0 + .026 + .163, y, "전월말 기준 %s" % pv.get("d", ""), fontsize=6.5,
       color=INK2, ha="center")
    tx(fig, X0 + .026 + .419 + .020 + .163, y, "금일 기준 %s" % td.get("d", ""),
       fontsize=6.5, color=INK2, ha="center")
    y -= .0098          # ⚠ 글씨가 va=top 이라 높이(.0086)보다 덜 내리면 표 윗선을 밟는다(종전 .0062)

    head = ["#", "티커", "섹터", "지수", "MTD %", mlab, "", "티커", "섹터", "지수", "MTD %", mlab]
    rows, marks = [], []
    for i in range(10):
        a = pr[i] if i < len(pr) else None
        b = tr_[i] if i < len(tr_) else None

        def side(r, other, mark):
            if not r:
                return ["", "", "", "", ""]
            ch = r["t"] not in other
            return [(mark + r["t"]) if ch else r["t"],
                    SECTOR.get(r.get("s"), r.get("s") or ""), r.get("idx", ""),
                    sgn(r.get("mtd")), str(r.get("v", ""))]
        L, R = side(a, tdt, "-"), side(b, pvt, "+")
        rows.append([str(i + 1)] + L + [""] + R)
        marks.append((bool(a) and a["t"] not in tdt, bool(b) and b["t"] not in pvt))

    def cc(r, c):
        if c == 0:
            return MUTED
        if c in (1, 7):
            out_, in_ = marks[r]
            if c == 1 and out_:
                return "#2C6E8F"
            if c == 7 and in_:
                return NEG
            return INK
        if c in (3, 9):
            return MUTED
        if c in (4, 10):
            v = rows[r][c]
            return POS if v.startswith("+") else (NEG if v.startswith("-") else INK)
        return INK2

    def cw(r, c):
        return "bold" if c in (1, 7) else "normal"

    y = table(fig, X0, y, HW, head, rows, row_h=ROW_H, fs=7.0, hfs=6.2,
              aligns=["r", "l", "l", "c", "r", "r", "c", "l", "l", "c", "r", "r"],
              cell_color=cc, cell_weight=cw)
    return y - .018


# ── 조립 ─────────────────────────────────────────────────────────────────────
def _load(path, what, required=True):
    if not os.path.exists(path):
        if required:
            raise SystemExit("%s 가 없다(%s)." % (path, what))
        print("  ⚠ %s 가 없다(%s) — 그 판을 빼고 그린다" % (path, what))
        return None
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description="스타일 10종 A4 5쪽")
    ap.add_argument("--src", default=SRC, help="style_perf.json 경로(기본 data/)")
    ap.add_argument("--perf", default=PERF, help="home_perf.json 경로(기본 data/)")
    ap.add_argument("--ind", default=IND, help="home_ind_perf.json 경로(기본 data/)")
    ap.add_argument("--horizon", default="1M", choices=list(HZL), help="2쪽 구간(기본 1M — 사용자 지시 2026-09-18)")
    ap.add_argument("--out", default=OUT, help="PDF 경로(기본 data/style8.pdf)")
    ap.add_argument("--png", action="store_true",
                    help="쪽마다 data/_s8_N.png 도 낸다(판이 넘쳤는지 눈으로 보려는 것)")
    a = ap.parse_args(argv)

    require_draw()
    P = _load(a.src, "먼저 `python build/style_top_pdf.py --json`")
    HP = _load(a.perf, "홈 기간별 수익률 시계열 — build/home_perf.py", required=False)
    IP = _load(a.ind, "산업그룹 시계열 — build/home_perf.py", required=False)
    S = {x["key"]: x for x in P["styles"]}
    miss = [k for k in KEYS if k not in S]
    if miss:
        raise SystemExit("style_perf.json 에 없는 스타일: %s" % ", ".join(miss))
    hid = [k for k in KEYS if k in (P.get("hide") or {})]
    if hid:
        print("  ⚠ 숨김 목록에 든 스타일이 섞였다: %s — 홈 화면과 갈린다" % ", ".join(hid))
    asof, start = P["as_of"], P.get("start", "")
    nreb = S[KEYS[0]].get("n_rebal", 11)
    rows, kinds, keys = perf_rows(P, S)
    figs = []

    # ── 1쪽 · 종합 ① 스타일 성과 ─────────────────────────────────────────
    fig = new_page(); figs.append(fig)
    y = .962
    tx(fig, X0, y, "스타일 10종", fontsize=17, weight="bold")
    tx(fig, X1, y + .002, "여두 전략 랩", fontsize=8, color=ACC, ha="right")
    y -= .017
    tx(fig, X0, y, "기준일 %s · %s ~ %s · 월말 %d회 리밸런스 · 상위 10종목 동일가중 · 비용 0"
       % (asof, start, asof, nreb), fontsize=6.8, color=MUTED)
    y -= .012
    hline(fig, X0, X1, y, RULE, .9)
    y -= .016
    y = section(fig, y, "기간별 수익률",
                "%%  ·  샤프·MDD·이긴달은 %s 이후  ·  이긴달 = S&P 500 을 이긴 달  ·  샤프 내림차순" % start)
    y = draw_perf_table(fig, y, rows, kinds, row_h=.0190)
    y -= .028
    y = section(fig, y, "월별 수익률",
                "%  ·  초록 +  빨강 -  (±10%p 에서 가장 진함)  ·  * 진행 중인 달(기준일까지)")
    y = draw_monthly(fig, y, P, S, keys, kinds, rh=.0200)
    y -= .028
    y = section(fig, y, "위험과 수익",
                "1년 변동성 대비 1년 수익률  ·  점선보다 위 = S&P 보다 위험 한 단위에 더 벌었다")
    # ⚠ 2026-09-18 — 여기 있던 «유니버스 편향» 각주(style_perf.json caveat)를 뺐다. 그 문장은
    #   «유니버스는 소급이다» 라고 적는데, 이 표의 수치는 이미 **선정 시점 구성(PIT)** 값이다
    #   (style_pit.json 의 pit 과 소수 둘째 자리까지 같다 — 고베타 27.83 · 소급이면 117.13).
    #   문장이 2026-08-23 PIT 전환 전 것으로 남아 있다. 고치기 전까지 싣지 않는다.
    # 축 아래 .088 = 눈금 글씨 + «1년 변동성» 축 이름 + 꼬리말 자리
    draw_risk_return(fig, y - .002, (y - .002) - .088, P, S, keys, kinds)

    # ── 2쪽 · 종합 ② 홈 기간별 수익률 네 판 ────────────────────────────────
    fig = new_page(); figs.append(fig)
    if HP:
        draw_home_page(fig, HP, IP, P, a.horizon)
    else:
        tx(fig, X0, .962, "기간별 수익률", fontsize=17, weight="bold")
        tx(fig, X0, .92, "시계열(home_perf.json)이 없어 이 쪽을 비웠다", fontsize=9, color=NEG)

    # ── 3·4쪽 · 스타일별 구성종목 ───────────────────────────────────────────
    HW = [.026] + [.082, .110, .055, .078, .094] + [.020] + [.082, .110, .055, .078, .094]
    # 🚨 종전에는 «앞 4 · 나머지» 두 쪽으로 못박혀 있었다. 10종이 되면 뒤쪽이 6블록이 돼
    #   각주를 뚫는다. 쪽 수를 키 수에서 뽑는다 — 10종이면 4+4+2 로 세 쪽이다.
    _chunks = [KEYS[i:i + BLK_PER_PAGE] for i in range(0, len(KEYS), BLK_PER_PAGE)]
    for pi, chunk in enumerate(_chunks):
        fig = new_page(); figs.append(fig)
        y = .962
        if pi == 0:
            tx(fig, X1, y + .014, "-티커 = 다음 재선정에서 빠짐  ·  +티커 = 새로 들어옴",
               fontsize=6.4, color=MUTED, ha="right")
        for k in chunk:
            y = draw_block(fig, S[k], k, y, HW)

    for i, f in enumerate(figs, 1):
        tx(f, X0, .022, "스타일 10종 · 기준일 %s · 여두 전략 랩" % asof, fontsize=6, color=MUTED)
        tx(f, X1, .022, "%d / %d" % (i, len(figs)), fontsize=6, color=MUTED, ha="right")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    # --png : 쪽마다 PNG 도 같이 낸다. **판이 넘쳤는지 눈으로 보려는 것**이다 —
    #   이 PC 에 PDF 를 그림으로 여는 수단이 없어 종이를 못 봤다. 다른 빌더(month_map_pdf ·
    #   rrg_pdf)가 쓰는 것과 같은 장치다. 산출물은 data/_s8_1.png … 로, 커밋하지 않는다.
    _png = bool(getattr(a, "png", False))
    with PdfPages(a.out) as pdf:
        for i, f in enumerate(figs, 1):
            pdf.savefig(f)
            if _png:
                f.savefig(os.path.join(DATA, "_s8_%d.png" % i), dpi=110, facecolor=PAPER)
            plt.close(f)
        d = pdf.infodict()
        d["Title"] = "스타일 10종 · 기준일 %s" % asof
    print("저장: %s · %d쪽 · 기준일 %s · 2쪽 기준일 %s"
          % (a.out, len(figs), asof, (HP or {}).get("as_of", "—")))
    return asof


if __name__ == "__main__":
    main()
