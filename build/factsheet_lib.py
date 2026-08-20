# -*- coding: utf-8 -*-
"""build/factsheet_lib.py — 전략 랩(팩트시트) 표준 표현층

보고서 빌더들이 공유하는 성과 표현 도구. 입력은 (일간 날짜, 일간 NAV, 주간 수익,
벤치 동일 격자) — 계산은 전부 여기서, 그리기는 style_top_pdf 문법으로.

  · period_returns: 1M/3M/6M/1Y/3Y/YTD/설정후(연환산)
  · monthly_matrix: 연×월 수익률 표(히트맵 셀 배경)
  · risk_stats: 연수익·연변동성·샤프·MDD·추적오차·IR·연초과
  · draw_cum_dd: 누적(로그)+낙폭 2단 차트
"""
from __future__ import annotations
import datetime as dt
import math
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import style_top_pdf as ST
from style_top_pdf import tx, hline, box

INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, PAPER, GROUND, PANEL2 = ST.POS, ST.NEG, ST.PAPER, ST.GROUND, ST.PANEL2


def _idx_before(daily_d, target):
    lo, hi = 0, len(daily_d) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if daily_d[mid] <= target:
            lo = mid
        else:
            hi = mid - 1
    return lo


def period_returns(daily_d, daily_v):
    """기간별 수익률(%) — 말일 기준. 3Y·설정후는 연환산."""
    n = len(daily_d)
    last = daily_v[-1]
    out = []
    for lab, td in (("1개월", 21), ("3개월", 63), ("6개월", 126), ("1년", 252)):
        if n > td:
            out.append((lab, (last / daily_v[n - 1 - td] - 1) * 100, False))
        else:
            out.append((lab, None, False))
    if n > 756:
        r = (last / daily_v[n - 1 - 756]) ** (1 / 3) - 1
        out.append(("3년(연환산)", r * 100, True))
    y0 = daily_d[-1][:4]
    j = _idx_before(daily_d, "%s-01-01" % y0)
    out.append(("연초이후", (last / daily_v[j] - 1) * 100, False))
    yrs = (dt.date.fromisoformat(daily_d[-1]) - dt.date.fromisoformat(daily_d[0])).days / 365.25
    out.append(("설정후(연환산)", ((last / daily_v[0]) ** (1 / yrs) - 1) * 100, True))
    return out


def monthly_matrix(daily_d, daily_v):
    """{연: {월: 수익률%}} + 연간 합성."""
    last = {}
    for d, v in zip(daily_d, daily_v):
        last[d[:7]] = v
    ms = sorted(last)
    out = {}
    prev = daily_v[0]
    for m in ms:
        y, mm = m[:4], int(m[5:7])
        out.setdefault(y, {})[mm] = (last[m] / prev - 1) * 100
        prev = last[m]
    yr = {y: (math.prod(1 + r / 100 for r in row.values()) - 1) * 100
          for y, row in out.items()}
    return out, yr


def risk_stats(daily_d, daily_v, wk_ret, wk_bench):
    yrs = (dt.date.fromisoformat(daily_d[-1]) - dt.date.fromisoformat(daily_d[0])).days / 365.25
    cagr = ((daily_v[-1] / daily_v[0]) ** (1 / yrs) - 1) * 100
    m = sum(wk_ret) / len(wk_ret)
    sd = math.sqrt(sum((x - m) ** 2 for x in wk_ret) / (len(wk_ret) - 1))
    vol = sd * math.sqrt(52) * 100
    sharpe = m / sd * math.sqrt(52) if sd > 0 else None
    peak, mdd = daily_v[0], 0.0
    for v in daily_v:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    ex = [a - b for a, b in zip(wk_ret, wk_bench)]
    me = sum(ex) / len(ex)
    sde = math.sqrt(sum((x - me) ** 2 for x in ex) / (len(ex) - 1))
    te = sde * math.sqrt(52) * 100
    ir = (me * 52) / (sde * math.sqrt(52)) if sde > 0 else None
    return {"cagr": cagr, "vol": vol, "sharpe": sharpe, "mdd": mdd * 100,
            "te": te, "ir": ir, "ann_ex": me * 52 * 100}


def draw_period_table(fig, x, y, rows_named, width=.40):
    """rows_named: [(라벨, [(기간, 값, is_ann)])] — 전략·벤치 나란히."""
    labs = [p[0] for p in rows_named[0][1]]
    ncol = len(labs) + 1
    cw = width / ncol
    box(fig, x, y - .016, width, .016, ST.HEAD_BG)
    tx(fig, x + .004, y - .003, "기간", fontsize=6.6, color=MUTED)
    for i, lab in enumerate(labs):
        tx(fig, x + cw * (i + 1) + cw - .004, y - .003, lab, fontsize=6.2,
           color=MUTED, ha="right")
    yy = y - .016
    for nm, prs in rows_named:
        yy -= .0155
        tx(fig, x + .004, yy + .0125, nm, fontsize=6.8)
        for i, (_lab, v, _a) in enumerate(prs):
            s = "-" if v is None else "%+.1f%%" % v
            tx(fig, x + cw * (i + 1) + cw - .004, yy + .0125, s, fontsize=6.8,
               ha="right", color=(NEG if (v is not None and v < 0) else INK))
        hline(fig, x, x + width, yy, LINE, .5)
    return yy


def draw_monthly_heat(fig, x, y, mat, yr, width=.86, title="월간 수익률(%)"):
    """연×월 히트맵 표 — 셀 배경 강도는 ±8% 포화."""
    tx(fig, x, y, title, fontsize=8.5, fontweight="bold")
    y -= .014
    years = sorted(mat)
    cw = width / 14
    rh = .0145
    tx(fig, x + .004, y, "연도", fontsize=6.2, color=MUTED)
    for m in range(1, 13):
        tx(fig, x + cw * m + cw * .5, y, "%d" % m, fontsize=6.2, color=MUTED, ha="center")
    tx(fig, x + cw * 13 + cw * .5, y, "연간", fontsize=6.2, color=MUTED, ha="center")
    y -= .008
    for yr_s in years:
        y -= rh
        tx(fig, x + .004, y + rh - .003, yr_s, fontsize=6.6)
        for m in range(1, 13):
            v = mat[yr_s].get(m)
            cx = x + cw * m
            if v is not None:
                a = min(1.0, abs(v) / 8.0)
                col = POS if v >= 0 else NEG
                box(fig, cx, y, cw * .96, rh * .92, _blend(col, a * .45), z=1)
                tx(fig, cx + cw * .48, y + rh - .003, "%+.1f" % v, fontsize=5.8,
                   ha="center", color=INK, zorder=3)
        v = yr.get(yr_s)
        if v is not None:
            cx = x + cw * 13
            box(fig, cx, y, cw * .96, rh * .92, _blend(POS if v >= 0 else NEG, .25), z=1)
            tx(fig, cx + cw * .48, y + rh - .003, "%+.1f" % v, fontsize=6.0,
               ha="center", fontweight="bold", color=INK, zorder=3)
    return y


def _blend(hex_col, alpha):
    """PAPER 위에 alpha 로 얹은 색을 미리 섞는다(투명 박스 대신).

    ⚠ 바탕색은 ST.PAPER 에서 파싱 — 손 RGB 를 박으면 팔레트가 바뀔 때 소리 없이 갈린다."""
    h = hex_col.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    ph = PAPER.lstrip("#")
    pr, pg, pb = int(ph[0:2], 16), int(ph[2:4], 16), int(ph[4:6], 16)
    f = lambda c, p: int(p + (c - p) * alpha)
    return "#%02X%02X%02X" % (f(r, pr), f(g, pg), f(b, pb))


def draw_cum_dd(fig, rect_top, rect_bot, XD, series, off_spans=None):
    """누적(로그)+낙폭 2단. series: [(vals, color, label, lw)]."""
    import matplotlib.pyplot as plt  # noqa: F401
    from matplotlib.ticker import NullFormatter
    ax = fig.add_axes(rect_top)
    for vals, col, lab, lw in series:
        base = vals[0]
        ax.plot(XD, [v / base * 100 for v in vals], color=col, lw=lw, label=lab)
    if off_spans:
        for a, b in off_spans:
            ax.axvspan(dt.date.fromisoformat(a), dt.date.fromisoformat(b),
                       color=NEG, alpha=.06, lw=0)
    ax.set_yscale("log")
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_yticks([100, 200, 400, 800])
    ax.set_yticklabels(["100", "200", "400", "800"], fontsize=6.5)
    ax.tick_params(axis="x", labelsize=6.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(LINE)
    ax.grid(axis="y", color=LINE, lw=.5, alpha=.7)
    ax.legend(loc="upper left", fontsize=6.8, frameon=False)
    ax.set_facecolor(PAPER)

    ax2 = fig.add_axes(rect_bot)
    for vals, col, lab, lw in series:
        peak, ddv = vals[0], []
        for v in vals:
            peak = max(peak, v)
            ddv.append((v / peak - 1) * 100)
        ax2.plot(XD, ddv, color=col, lw=max(.7, lw - .3))
    ax2.tick_params(labelsize=6.5)
    for sp in ("top", "right"):
        ax2.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax2.spines[sp].set_color(LINE)
    ax2.grid(axis="y", color=LINE, lw=.5, alpha=.7)
    ax2.set_facecolor(PAPER)
    return ax, ax2
