# -*- coding: utf-8 -*-
"""build/style8_pdf.py — 스타일 8종 한눈에 → data/style8.pdf (A4 4쪽)

무엇을. 홈 화면에 실리는 **스타일 8종**을 A4 네 쪽으로 뽑는다.
  1쪽  기간별 수익률 표 · 기간별 수익률 차트 · 장기 성과
  2쪽  누적 수익률(최근 1년) · 월별 수익률 · 위험과 수익
  3쪽  스타일 보유 넷 · 섹터 구성
  4쪽  스타일 보유 넷 · 여러 스타일이 같이 든 종목

`style_top_pdf.py` 가 «오늘 무엇을 담나» 를 전략별 반 쪽으로 싣는다면, 이 문서는
**여덟 줄을 한 화면에 놓고 견주는** 자리다. 회의에 들고 갈 몇 장이 필요해서 만들었다.
🚨 2026-09-18 사용자 지시 «기간별 수익률 차트도 넣고 정보 추가해서 4페이지로 구성해줘»
  — 2쪽 판(표 + 보유)에서 차트 넷과 표 셋을 더해 4쪽으로 늘렸다.

자료 — `data/style_perf.json` **하나만** 읽는다. 계산은 하지 않는다.
  그 파일을 만드는 것은 `build/style_top_pdf.py --json` 이고(러너가 매일 굽는다), 이 문서는
  그 결과를 그린다. **숫자를 두 번 계산하지 않는다** — 갈리면 조용히 어긋나기 때문이다.
  더한 것들도 전부 그 파일에 이미 있는 값이다:
    · 기간별 차트  = trails(표와 같은 값)       · 장기 성과 = metrics · style_trails5 · style_sharpe5 · win
    · 누적 곡선    = nav(🚨 표시용 표본 — 모양만) · 월별     = monthly
    · 위험과 수익  = metrics(ret·vol)           · 섹터·겹침 = today.rows 를 세기만 한다
  ⚠ nav 는 252점을 140점으로 솎은 **표시용 표본**이고 날짜가 없다(파일의 series_note).
    그래서 곡선에서 수치를 읽지 않는다 — 끝값 글씨는 trails 의 1년 값을 쓴다.
  ⚠ 3년·5년은 **누적**이다(연율 아님 — 홈 표와 같은 뜻). 벤치마크 행에는 그 값이 파일에
    없다. ETF 샤프(SPY·QQQ)는 총수익 기준이라 가격지수 벤치와 섞지 않고 «—» 로 둔다.

판형·색·폰트·표는 `style_top_pdf.py` 에서 **그대로 가져온다**(그쪽이 정본이다).

보유 표 — 전월말과 금일을 **한 표에 나란히** 둔다. style.html 과 같은 열이다.
  -티커 = 다음 재선정에서 빠지는 종목 · +티커 = 새로 들어오는 종목

    python build/style8_pdf.py                       # data/style_perf.json → data/style8.pdf
    python build/style8_pdf.py --src X.json --out Y.pdf
      (매일 아침 작업이 origin/main 의 자료를 작업 트리 밖에서 읽어 공유폴더로 낼 때 쓴다 —
       ops/style8_daily/style8_daily.bat)
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

from style_top_pdf import (ACC, GROUND, HEAD_BG, INK, INK2, LINE, MUTED, NEG, PANEL2,  # noqa: E402
                           PAPER, POS, RULE, X0, X1, hline, new_page, require_draw, table, tx)

try:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.pyplot as plt
except Exception as e:                                        # pragma: no cover
    raise SystemExit("matplotlib 이 필요하다 — %s" % e)

SRC = os.path.join(DATA, "style_perf.json")
OUT = os.path.join(DATA, "style8.pdf")

# 홈 화면에 보이는 여덟 줄. style_perf.json 의 hide 목록 밖이 이 여덟이다 —
# 손으로 두 번 적지 않도록 여기서 한 번만 적고 아래에서 대조한다.
KEYS = ["div", "val", "qvm", "spmo", "size", "grow", "hbeta", "squal"]
TR = ["1일", "1주", "1개월", "3개월", "6개월", "1년", "YTD"]
# 기간별 차트에 싣는 칸 — 1일·1주는 차트로 보기엔 잡음이라 표에만 둔다.
TR_CHART = ["1개월", "3개월", "6개월", "1년", "YTD"]

# 섹터 약어를 펴서 쓴다 — 두 글자로는 회의에서 안 읽힌다.
SECTOR = {"부동": "부동산", "소재": "소재", "금융": "금융", "필소": "필수소비", "산업": "산업재",
          "유틸": "유틸리티", "헬스": "헬스케어", "커뮤": "커뮤니케이션", "경소": "경기소비",
          "에너": "에너지", "IT": "IT"}
# 섹터 구성 표의 열 순서(GICS 순) — 여기 없는 코드가 오면 끝에 붙인다.
SEC_ORDER = ["IT", "커뮤", "경소", "필소", "헬스", "금융", "산업", "에너", "소재", "유틸", "부동"]
SEC_HEAD = {"IT": "IT", "커뮤": "커뮤", "경소": "경기소비", "필소": "필수소비", "헬스": "헬스",
            "금융": "금융", "산업": "산업재", "에너": "에너지", "소재": "소재", "유틸": "유틸",
            "부동": "부동산"}

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
    "grow": "3년 주당매출 연평균 성장률   3년 주당순이익 변화 ÷ 주가   12개월 모멘텀 — 셋의 z 를 평균",
    "hbeta": "베타 = 최근 252거래일 일간수익률의 시장과의 공분산 ÷ 시장 분산",
    "squal": "발생액비율 = (순이익 - 영업활동현금흐름) ÷ 평균 총자산 · 최근 4분기 합 기준   "
             "재무레버리지 = 부채총계 ÷ 자기자본",
}

ROW_H = 0.01175        # 보유 표 한 줄
BLK_PER_PAGE = 4       # 3·4쪽에 보유 블록 넷씩 — 남는 아래 자리에 요약 표를 싣는다
BENCH_C = "#8C949C"    # 벤치마크 — 비교 대상이라 색을 빼고 회색으로(강조가 아니라 맥락)
BENCH_C2 = "#B9BFC4"   # 둘째 벤치마크(NDX) — 같은 회색 계열의 옅은 판


def sgn(v, d=1):
    return "—" if v is None else ("%+.*f" % (d, v))


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


# ── 1쪽 ──────────────────────────────────────────────────────────────────────
def perf_rows(P, S):
    """기간별 수익률 표의 행 — 벤치마크 먼저, 그다음 샤프 내림차순. 차트도 이 순서를 쓴다."""
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


def draw_perf_table(fig, y, rows, kinds):
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

    return table(fig, X0, y, W, head, rows, row_h=.0152, fs=7.4, hfs=6.6,
                 aligns=["l", "l"] + ["r"] * 10, cell_color=pcol, cell_weight=pw)


def draw_period_chart(fig, y_top, h, P, S, keys, kinds):
    """기간별 수익률 차트 — 기간마다 한 칸(작은 배수). 행 순서는 위 표와 같다.

    ⚠ 칸마다 가로축 눈금이 다르다. 1개월과 1년을 한 눈금에 두면 1개월이 납작해져 안 읽힌다.
      그래서 막대 끝에 값을 적는다 — 눈금이 달라도 숫자는 같은 뜻이다.
    ⚠ 색은 **부호**를 말한다(초록 +, 빨강 −). 벤치마크는 비교 대상이라 회색이다.
    """
    lab_w = .118
    gap = .010
    n = len(TR_CHART)
    pw_ = (X1 - X0 - lab_w - gap * (n - 1)) / n
    nrow = len(keys)
    names = [(P["bench"][k]["label"] if kinds[i] == "b" else S[k]["label"])
             for i, k in enumerate(keys)]
    for c, per in enumerate(TR_CHART):
        vals = []
        for i, k in enumerate(keys):
            src = P["bench"][k] if kinds[i] == "b" else S[k]
            vals.append((src.get("trails") or {}).get(per))
        x = X0 + lab_w + c * (pw_ + gap)
        ax = _ax(fig, x, y_top - h, pw_, h - .012)
        ys = list(range(nrow))[::-1]                 # 첫 행이 맨 위
        cols = [(BENCH_C if kinds[i] == "b" else (POS if (v or 0) >= 0 else NEG))
                for i, v in enumerate(vals)]
        ax.barh(ys, [v or 0 for v in vals], height=.62, color=cols, zorder=2)
        ax.axvline(0, color=INK2, lw=.6, zorder=3)
        lo = min(0, min(v for v in vals if v is not None))
        hi = max(0, max(v for v in vals if v is not None))
        span = (hi - lo) or 1
        ax.set_xlim(lo - span * .30, hi + span * .30)   # 막대 끝 글씨 자리
        ax.set_ylim(-.7, nrow - .3)
        ax.set_yticks([])
        ax.xaxis.grid(True, color=LINE, lw=.4, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", labelsize=5.2)
        for yy, v in zip(ys, vals):
            if v is None:
                continue
            ax.text(v + (span * .03 if v >= 0 else -span * .03), yy, "%+.1f" % v,
                    ha="left" if v >= 0 else "right", va="center", fontsize=5.4, color=INK2)
        tx(fig, x + pw_ / 2, y_top - .004, per, fontsize=7.2, weight="bold", ha="center")
        if c == 0:
            for i, (yy, nm) in enumerate(zip(ys, names)):
                # 행 이름은 축 밖(왼쪽 글자 칸)에 그림 좌표로 적는다 — 칸마다 반복하지 않게
                fy = (y_top - h) + (h - .012) * ((yy + .7) / (nrow - .3 + .7))
                tx(fig, X0 + lab_w - .006, fy, nm, fontsize=6.6, ha="right", va="center",
                   color=MUTED if kinds[i] == "b" else INK,
                   weight="normal" if kinds[i] == "b" else "bold")
    return y_top - h


def draw_longterm(fig, y, P, S, keys, kinds):
    """장기 성과 — 1년 위험지표와 3·5년 누적을 한 줄에. 행 순서는 위와 같다."""
    s5 = P.get("style_sharpe5") or {}
    t5 = P.get("style_trails5") or {}
    head = ["스타일", "1년 수익률", "1년 변동성", "1년 샤프", "1년 MDD", "5년 샤프",
            "3년 누적", "5년 누적", "SPX 대비", "NDX 대비"]
    W = [.130, .084, .084, .076, .076, .076, .084, .084, .095, .095]
    rows, kind = [], []
    for i, k in enumerate(keys):
        if kinds[i] == "b":
            bx = P["bench"][k]
            m = bx.get("metrics") or {}
            rows.append([bx.get("label", k), sgn(m.get("ret")), "%.1f" % m.get("vol", 0),
                         "%.2f" % m.get("sharpe", 0), "%.1f" % m.get("mdd", 0),
                         "—", "—", "—", "·", "·"])
        else:
            x = S[k]
            m = x["metrics"]
            w = x.get("win") or {}
            ws, wn = w.get("spx") or [0, 0], w.get("ndx") or [0, 0]
            tt = t5.get(k) or {}
            rows.append([x["label"], sgn(m.get("ret")), "%.1f" % m.get("vol", 0),
                         "%.2f" % m.get("sharpe", 0), "%.1f" % m.get("mdd", 0),
                         ("%.2f" % s5[k]) if s5.get(k) is not None else "—",
                         sgn(tt.get("3년")), sgn(tt.get("5년")),
                         "%d/%d" % (ws[0], ws[1]), "%d/%d" % (wn[0], wn[1])])
        kind.append(kinds[i])

    def cc(r, c):
        if kind[r] == "b":
            return MUTED
        if c == 4:
            return NEG
        if c in (1, 6, 7):
            v = rows[r][c]
            return POS if v.startswith("+") else (NEG if v.startswith("-") else INK)
        return INK

    def cw(r, c):
        return "bold" if c == 0 and kind[r] == "s" else "normal"

    return table(fig, X0, y, W, head, rows, row_h=.0150, fs=7.2, hfs=6.4,
                 aligns=["l"] + ["r"] * 9, cell_color=cc, cell_weight=cw)


# ── 2쪽 ──────────────────────────────────────────────────────────────────────
def draw_nav_grid(fig, y_top, h, P, S, order):
    """누적 수익률 — 스타일마다 한 칸. 스타일은 진한 선, 벤치는 회색(S&P 실선 · NDX 점선).

    🚨 nav 는 **표시용 표본**이다(252→140점 · 날짜 없음). 모양만 그리고, 끝값 글씨는
      trails 의 1년 값을 쓴다. 곡선 끝을 읽어 숫자를 만들지 않는다.
    ⚠ 여덟 줄을 한 판에 겹치면 서로를 가린다. 한 칸에 하나씩 두고 벤치만 같이 깐다 —
      «이 스타일이 지수 대비 어디 있나» 가 이 절의 물음이다.
    """
    cols, rows_ = 2, 4
    gx, gy = .030, .016
    cw_ = (X1 - X0 - gx * (cols - 1)) / cols
    ch = (h - gy * (rows_ - 1)) / rows_
    spx = (P["bench"].get("spx") or {}).get("nav") or []
    ndx = (P["bench"].get("ndx") or {}).get("nav") or []
    allv = [v for k in order for v in S[k]["nav"]] + list(spx) + list(ndx)
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * .06
    for j, k in enumerate(order):
        r, c = divmod(j, cols)
        x = X0 + c * (cw_ + gx)
        y = y_top - (r + 1) * ch - r * gy
        ax = _ax(fig, x, y, cw_, ch - .012)
        nv = S[k]["nav"]
        xs = range(len(nv))
        ax.axhline(100, color=LINE, lw=.6, zorder=1)
        if ndx:
            ax.plot(range(len(ndx)), ndx, color=BENCH_C2, lw=.7, ls=(0, (2.2, 1.6)), zorder=2)
        if spx:
            ax.plot(range(len(spx)), spx, color=BENCH_C, lw=.8, zorder=3)
        ax.plot(xs, nv, color=ACC, lw=1.4, zorder=4, solid_capstyle="round")
        ax.set_ylim(lo - pad, hi + pad)          # 🚨 여덟 칸 **같은 눈금** — 높이로 견줄 수 있게
        ax.set_xlim(0, len(nv) - 1)
        ax.set_xticks([])
        ax.yaxis.grid(True, color=LINE, lw=.4, zorder=0)
        ax.set_axisbelow(True)
        t1 = (S[k].get("trails") or {}).get("1년")
        tx(fig, x, y + ch - .006, S[k]["label"], fontsize=7.6, weight="bold")
        tx(fig, x + cw_, y + ch - .006, "1년 %s%%" % sgn(t1), fontsize=7.2,
           color=POS if (t1 or 0) >= 0 else NEG, ha="right", weight="bold")
    return y_top - h


def draw_monthly(fig, y_top, P, S, keys, kinds):
    """월별 수익률 히트맵 — 행 = 벤치 + 스타일(표와 같은 순서), 열 = 월.

    색은 **부호와 크기**(발산형: 빨강 − · 종이색 0 · 초록 +). 눈금은 ±10%p 에서 포화한다 —
    한두 달의 큰 값이 나머지를 다 옅게 만들지 않게. 숫자는 칸마다 적는다(색만으로 안 가른다).
    ⚠ 마지막 달은 기준일까지의 **진행 중** 수익이다.
    """
    months = P.get("months") or []
    n = len(months)
    lab_w = .118
    cw_ = (X1 - X0 - lab_w) / max(1, n)
    rh = .0158
    cmap = LinearSegmentedColormap.from_list("pn", [NEG, PAPER, POS])
    VMAX = 10.0
    y = y_top
    for c, mth in enumerate(months):
        lab = "%s/%s" % (mth[2:4], mth[5:7]) + ("*" if c == n - 1 else "")
        tx(fig, X0 + lab_w + c * cw_ + cw_ / 2, y - rh / 2, lab, fontsize=6.0,
           color=MUTED, ha="center", va="center")
    y -= rh
    hline(fig, X0, X1, y, RULE, .8)
    for i, k in enumerate(keys):
        src = P["bench"][k] if kinds[i] == "b" else S[k]
        mo = src.get("monthly") or []
        tx(fig, X0 + .004, y - rh / 2, src.get("label", k), fontsize=6.6, va="center",
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
            tx(fig, x0 + cw_ / 2, y - rh / 2, "%+.1f" % v, fontsize=5.8, color=tcol,
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
                fontsize=5.4, color=MUTED, ha="left", va="top")
    for vol, ret, lab, kd in pts:
        if vol is None or ret is None:
            continue
        ax.scatter([vol], [ret], s=26 if kd == "s" else 20, zorder=3,
                   color=(BENCH_C if kd == "b" else ACC),
                   edgecolor=PAPER, linewidth=.8)
        ax.text(vol + xmax * .012, ret, lab, fontsize=6.2, va="center",
                color=MUTED if kd == "b" else INK, weight="normal" if kd == "b" else "bold")
    ax.set_xlim(0, xmax)
    ax.set_ylim(ymin, ymax)
    ax.grid(True, color=LINE, lw=.4, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel("1년 변동성 (%)", fontsize=6.2, color=MUTED, labelpad=2)
    ax.set_ylabel("1년 수익률 (%)", fontsize=6.2, color=MUTED, labelpad=2)
    return y_top - h


# ── 3·4쪽 요약 ───────────────────────────────────────────────────────────────
def draw_sector_mix(fig, y, S):
    """섹터 구성 — 금일 상위 10종목을 섹터별로 센다(새 계산이 아니라 보유 표를 세기만 한다)."""
    secs = [s for s in SEC_ORDER]
    extra = sorted({r.get("s") for k in KEYS for r in (S[k].get("today") or {}).get("rows") or []}
                   - set(secs) - {None})
    secs += extra
    head = ["스타일"] + [SEC_HEAD.get(s, s) for s in secs] + ["최다 섹터"]
    W = [.098] + [(.884 - .098 - .120) / len(secs)] * len(secs) + [.120]
    rows, cnts = [], []
    for k in KEYS:
        rr = (S[k].get("today") or {}).get("rows") or []
        cnt = {s: 0 for s in secs}
        for r in rr:
            if r.get("s") in cnt:
                cnt[r.get("s")] += 1
        top = max(cnt.items(), key=lambda z: z[1])
        rows.append([S[k]["label"]] + [str(cnt[s]) if cnt[s] else "·" for s in secs]
                    + ["%s %d/10" % (SECTOR.get(top[0], top[0]), top[1]) if top[1] else "—"])
        cnts.append([cnt[s] for s in secs])

    def cc(r, c):
        if c == 0:
            return INK
        if 1 <= c <= len(secs):
            v = cnts[r][c - 1]
            return INK if v >= 4 else (INK2 if v else MUTED)
        return INK2

    def cw(r, c):
        return "bold" if c == 0 or (1 <= c <= len(secs) and cnts[r][c - 1] >= 4) else "normal"

    return table(fig, X0, y, W, head, rows, row_h=.0122, fs=6.6, hfs=5.9,
                 aligns=["l"] + ["c"] * len(secs) + ["l"], cell_color=cc, cell_weight=cw)


def draw_overlap(fig, y, S, limit=10):
    """여러 스타일이 같이 든 종목 — 금일 보유에서 둘 이상의 스타일에 들어간 티커.

    스타일이 달라도 같은 종목을 사면 여덟 개를 들어도 여덟 가지 베팅이 아니다. 그것을 센다.
    """
    seen = {}
    for k in KEYS:
        for r in (S[k].get("today") or {}).get("rows") or []:
            d = seen.setdefault(r["t"], {"n": r.get("n", ""), "s": r.get("s", ""),
                                         "idx": r.get("idx", ""), "mtd": r.get("mtd"), "st": []})
            d["st"].append(S[k]["label"])
    total = sum(len((S[k].get("today") or {}).get("rows") or []) for k in KEYS)
    multi = sorted(((t, d) for t, d in seen.items() if len(d["st"]) >= 2),
                   key=lambda z: (-len(z[1]["st"]), z[0]))
    note = "금일 보유 %d칸 · 서로 다른 종목 %d개 · 둘 이상의 스타일에 든 종목 %d개" % (
        total, len(seen), len(multi))
    head = ["티커", "종목", "섹터", "지수", "스타일 수", "든 스타일", "MTD %"]
    W = [.070, .215, .085, .050, .062, .330, .072]
    rows = []
    for t, d in multi[:limit]:
        rows.append([t, (d["n"] or "")[:30], SECTOR.get(d["s"], d["s"]), d["idx"],
                     "%d" % len(d["st"]), " · ".join(d["st"]), sgn(d["mtd"])])
    if len(multi) > limit:
        rows.append(["", "외 %d종" % (len(multi) - limit), "", "", "", "", ""])

    def cc(r, c):
        if c == 6:
            v = rows[r][c]
            return POS if v.startswith("+") else (NEG if v.startswith("-") else INK)
        if c in (2, 3):
            return MUTED
        return INK

    def cw(r, c):
        return "bold" if c in (0, 4) else "normal"

    yb = table(fig, X0, y, W, head, rows, row_h=.0120, fs=6.5, hfs=5.9,
               aligns=["l", "l", "l", "c", "c", "l", "r"], cell_color=cc, cell_weight=cw)
    return yb, note


# ── 보유 블록(종전과 같다) ────────────────────────────────────────────────────
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
    y -= .0092          # 종전 .0082 — 넉 장이 되며 생긴 자리를 줄 사이에 쓴다(설명과 산식이 붙어 보였다)
    if key in GLOSS:
        tx(fig, X0, y, GLOSS[key], fontsize=6.0, color=MUTED)
        y -= .0092      # 종전 .0078 — 산식과 «전월말 기준» 줄이 맞닿아 있었다

    mlab = x.get("mlab", "")
    tx(fig, X0 + .026 + .163, y, "전월말 기준 %s" % pv.get("d", ""), fontsize=6.3,
       color=INK2, ha="center")
    tx(fig, X0 + .026 + .419 + .020 + .163, y, "금일 기준 %s" % td.get("d", ""),
       fontsize=6.3, color=INK2, ha="center")
    y -= .0062

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

    y = table(fig, X0, y, HW, head, rows, row_h=ROW_H, fs=6.6, hfs=6.0,
              aligns=["r", "l", "l", "c", "r", "r", "c", "l", "l", "c", "r", "r"],
              cell_color=cc, cell_weight=cw)
    return y - .018


# ── 조립 ─────────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description="스타일 8종 A4 4쪽")
    ap.add_argument("--src", default=SRC, help="style_perf.json 경로(기본 data/)")
    ap.add_argument("--out", default=OUT, help="PDF 경로(기본 data/style8.pdf)")
    a = ap.parse_args(argv)

    require_draw()
    if not os.path.exists(a.src):
        raise SystemExit("%s 가 없다 — 먼저 `python build/style_top_pdf.py --json` 을 돌린다." % a.src)
    P = json.load(io.open(a.src, encoding="utf-8"))
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

    # ── 1쪽 ─────────────────────────────────────────────────────────────
    fig = new_page(); figs.append(fig)
    y = .962
    tx(fig, X0, y, "스타일 8종", fontsize=17, weight="bold")
    tx(fig, X1, y + .002, "여두 전략 랩", fontsize=8, color=ACC, ha="right")
    y -= .017
    tx(fig, X0, y, "%s ~ %s · 월말 %d회 리밸런스 · 상위 10종목 동일가중"
       % (start, asof, nreb), fontsize=6.8, color=MUTED)
    y -= .012
    hline(fig, X0, X1, y, RULE, .9)
    y -= .016
    y = section(fig, y, "기간별 수익률",
                "%%  ·  샤프·MDD·이긴달은 %s 이후 구간  ·  샤프 내림차순" % start)
    y = draw_perf_table(fig, y, rows, kinds)
    y -= .024
    y = section(fig, y, "기간별 수익률 차트",
                "%  ·  초록 +  빨강 -  회색 = 벤치마크  ·  행 순서는 위 표와 같다  ·  칸마다 눈금이 다르다")
    y = draw_period_chart(fig, y - .004, .360, P, S, keys, kinds)
    y -= .026
    y = section(fig, y, "장기 성과",
                "1년 = %s 이후  ·  3·5년은 누적(연율 아님)  ·  SPX/NDX 대비 = 지수를 이긴 달" % start)
    y = draw_longterm(fig, y, P, S, keys, kinds)
    y -= .010
    tx(fig, X0, y, "벤치마크의 3·5년 칸은 이 자료에 없다(가격지수 · ETF 샤프는 총수익이라 섞지 않는다). "
       "5년 샤프 구간 %s 이후." % (P.get("start5") or "—"), fontsize=5.8, color=MUTED)

    # ── 2쪽 ─────────────────────────────────────────────────────────────
    fig = new_page(); figs.append(fig)
    y = .962
    y = section(fig, y, "누적 수익률 · 최근 1년",
                "진한 선 = 스타일 · 회색 실선 = S&P 500 · 회색 점선 = NASDAQ 100 · 여덟 칸 같은 눈금 · 100 = 1년 전")
    order = sorted(KEYS, key=lambda z: -S[z]["metrics"]["sharpe"])
    y = draw_nav_grid(fig, y - .004, .392, P, S, order)
    y -= .024
    y = section(fig, y, "월별 수익률",
                "%  ·  초록 +  빨강 -  (±10%p 에서 가장 진함)  ·  * 진행 중인 달(기준일까지)")
    y = draw_monthly(fig, y, P, S, keys, kinds)
    y -= .024
    y = section(fig, y, "위험과 수익",
                "1년 변동성 대비 1년 수익률  ·  점선보다 위 = S&P 보다 위험 한 단위에 더 벌었다")
    draw_risk_return(fig, y - .002, y - .078, P, S, keys, kinds)

    # ── 3·4쪽 ───────────────────────────────────────────────────────────
    HW = [.026] + [.082, .110, .055, .078, .094] + [.020] + [.082, .110, .055, .078, .094]
    for pi, chunk in enumerate((KEYS[:BLK_PER_PAGE], KEYS[BLK_PER_PAGE:])):
        fig = new_page(); figs.append(fig)
        y = .962
        if pi == 0:
            tx(fig, X1, y + .014, "-티커 = 다음 재선정에서 빠짐  ·  +티커 = 새로 들어옴",
               fontsize=6.4, color=MUTED, ha="right")
        for k in chunk:
            y = draw_block(fig, S[k], k, y, HW)
        y += .004
        if pi == 0:
            y = section(fig, y, "섹터 구성",
                        "금일 상위 10종목을 섹터별로 센 것  ·  4종목 이상은 굵게")
            draw_sector_mix(fig, y, S)
        else:
            y = section(fig, y, "여러 스타일이 같이 든 종목", "")
            yb, note = draw_overlap(fig, y, S)
            tx(fig, X1, y + .013, note, fontsize=6.3, color=MUTED, ha="right")

    for i, f in enumerate(figs, 1):
        tx(f, X0, .022, "스타일 8종 · 기준일 %s · 여두 전략 랩" % asof, fontsize=6, color=MUTED)
        tx(f, X1, .022, "%d / %d" % (i, len(figs)), fontsize=6, color=MUTED, ha="right")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with PdfPages(a.out) as pdf:
        for f in figs:
            pdf.savefig(f)
            plt.close(f)
        d = pdf.infodict()
        d["Title"] = "스타일 8종 · 기준일 %s" % asof
    print("저장: %s · %d쪽 · 기준일 %s" % (a.out, len(figs), asof))
    return asof


if __name__ == "__main__":
    main()
