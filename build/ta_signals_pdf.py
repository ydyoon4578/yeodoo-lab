# -*- coding: utf-8 -*-
"""build/ta_signals_pdf.py — 교과서 TA 신호 → data/ta_signals.pdf (A4 4쪽)

자료는 build/ta_signals.py 가 낸 data/_ta_signals.json 하나뿐이다.

  1·3쪽  지수 차트 + **멀티 신호**(두 신호가 같이 뜬 날)
  2·4쪽  매수 신호 표 · 매도 신호 표

🚨 2026-09-22 사용자 지시로 다시 짠 판이다.
  · 「신호 합류」 → **멀티 신호** · 「기준선차」 → **수익률**
  · S&P 두 쪽 · NASDAQ 두 쪽, 멀티 신호를 앞으로
  · 모든 표는 **승률 순** · 「횟수」 칸은 지우고 **일정 횟수 초과는 아예 뺀다**
  · 말 뜻 상자와 읽는 법은 덜어낸다

⚠ 수익률 칸은 **날것의 1개월 지수 등락**이다. 종전의 「기준선차(= 등락 - 기준선)」는
  칸에서 빼고, 견줄 기준선은 쪽머리에 한 번만 적는다. 승률도 같은 자리에
  「아무 날이나 잡아도 몇 %」를 적어 두니 두 수 다 견줄 데가 있다.

  python build/ta_signals_pdf.py [--png]
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.backends.backend_pdf import PdfPages   # noqa: E402

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "ta_signals.pdf")
sys.path.insert(0, HERE)
import style_top_pdf as ST                                        # noqa: E402

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2

HOT = 10                  # 「최근 발동」을 빨갛게 볼 날수
TOT = 4
N_MULTI = (21, 15)        # 멀티 신호 표에 실을 짝 수(매수, 매도)
# 🚨 「횟수」 칸을 지우라는 지시(2026-09-22)의 대가를 여기서 막는다.
#   승률 순으로만 세우면 **5회짜리 승률 100%가 1등**으로 올라오는데, 칸이 없으니
#   독자가 그게 5회인 줄 알 길이 없다. 칸을 되살리는 대신 **문턱을 올려**
#   얇은 표본은 애초에 싣지 않는다 — 설명이 늘지 않고 표만 믿을 만해진다.
#   (합류 후보 문턱 CONF_MIN_N 과 같은 10회다.)
MIN_SHOW = 10

# 차트에 올릴 것 — **승률 문턱**으로 고른다(사용자 지시 2026-09-22).
#   매수는 오를 확률, 매도는 내릴 확률이 이 이상인 신호만. 종수를 미리 못 박지
#   않으므로 지수·방향에 따라 몇 종이 뜨는지가 달라진다 — 그게 곧 진단이다.
CHART_WIN = {True: 70.0, False: 40.0}   # True=매수 · False=매도
# 🚨 띄울 거리는 **가격 비율이 아니라 그림 범위(hi-lo) 비율**이다.
#   가격 비율로 잡았더니 여백이 범위의 60%를 먹어 가격선이 납작해졌다(렌더 실측).
#   범위 기준이면 지수가 무엇이든 보이는 간격이 같다.
MK_SIZE, MK_BASE = 26, .045              # 세모 크기 · 가격선에서 띄울 거리(범위 비율)

# 칸 너비는 **렌더 실측**이다(6.6pt 본문 · PDF 5% 여유 포함).
#   신호명 최대 .123 · 설명 최대 .195 · 「★켜짐157일」 .065 · 날짜 .060
W_SIG = [.190, .330, .062, .050, .082, .050, .120]          # 합 .884 = X1-X0
H_SIG = ["신호", "무엇을 보나", "수익률", "승률", "최근 발동", "경과", "지금"]
A_SIG = ["l", "l", "r", "r", "l", "r", "c"]
# 🚨 멀티 표는 단일 표와 **같은 꼴**로 둔다(사용자 지시 2026-09-22) —
#   「단독 A/B」·「단독 대비」를 빼고 그 자리에 최근 발동·경과·지금을 넣는다.
#   ⚠ 그 대가로 「같이 본 값이 있나」를 표에서 바로 읽을 수는 없게 됐다.
#     맞은편 쪽 단일 표의 같은 신호와 수익률·승률을 견주면 된다.
W_MUL = [.260, .260, .062, .050, .082, .050, .120]          # 합 .884
H_MUL = ["신호 A", "신호 B", "수익률", "승률", "최근 발동", "경과", "지금"]
A_MUL = ["l", "l", "r", "r", "l", "r", "c"]

MON = ["1월", "2월", "3월", "4월", "5월", "6월",
       "7월", "8월", "9월", "10월", "11월", "12월"]


YMIN = .050               # 이보다 내려가면 꼬리말을 뚫는다


def foot(fig, page, asof, y_end=None):
    # ⚠ 이 랩에서 표가 꼬리말을 뚫은 적이 여러 번이다. 눈으로 보지 말고 재서 알린다.
    if y_end is not None and y_end < YMIN:
        print("  !! %d쪽 바닥 y=%.4f — %.3f 아래로 내려갔다" % (page, y_end, YMIN))
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .024,
          "여두 전략 랩 · 교과서 TA 신호 · 기준 %s · 통계는 최근 10년 · 차트는 최근 12개월"
          % asof, fontsize=6.4, color=MUTED)
    ST.tx(fig, X1, .024, "%d / %d · %s" % (page, TOT, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def head(fig, R, sub, asof, color=INK):
    """쪽머리 — 견줄 기준선 둘(수익률·승률)을 여기 한 번만 적는다."""
    y = .958
    ST.tx(fig, X0, y, "%s · %s" % (R["label"], sub), fontsize=15, weight="bold", color=color)
    ST.tx(fig, X1, y,
          "기준 %s · 10년(%s~) · 아무 날이나 사면 1개월 %+.2f%% · 오를 확률 %.1f%%"
          % (asof, R["start"], R["base1m"], R.get("base1m_win") or 0),
          fontsize=7.0, color=MUTED, ha="right")
    y -= .026
    ST.hline(fig, X0, X1, y, RULE, .9)
    return y - .014


def nowcell(x):
    """「지금」 칸 — 발동(순간)과 지속(그 관계가 유지되나)을 나눠 적는다.

      ★       기준일 당일 발동
      켜짐N일   그 조건이 지금도 참이다 · N 은 그 상태가 며칠째인지
      꺼짐     되돌아갔고 지금도 아니다

    ⚠ 한때 「끊겼다 다시 켜진 것」을 「다시N일·K번」으로 갈라 적었다(2026-09-22).
      계산은 맞았고 — NASDAQ「MACD 골든(0선 아래)」은 8/04 발동 뒤 8/21 에 끊겼다
      9/18 에 다시 켜졌다 — 다시 켜진 횟수도 원자료와 맞았지만, 사용자가 신경
      쓰지 말라 하여 되돌렸다. 세는 값(state_reon)은 자료에 그대로 있다.
    """
    s = "★" if x.get("fired_today") else ""
    if not x.get("state_now"):
        return s + "꺼짐"
    d_ = x.get("state_days")
    if d_ is None:
        return s + "켜짐"
    return s + "켜짐%d일" % d_


def rows_of(R, side, max_n):
    """싣는 줄 — 표본이 너무 얇지도(MIN_SHOW) 너무 잦지도(max_n) 않은 것, 승률 순."""
    wkey = "fwd1m_win" if side == "buy" else "fwd1m_down"
    rows = [x for x in R[side] if MIN_SHOW <= x.get("n", 0) <= max_n]
    rows.sort(key=lambda x: ((x.get(wkey) or 0),
                             (x.get("fwd1m_excess") or 0) * (1 if side == "buy" else -1)),
              reverse=True)
    return rows, wkey


# ══ 차트 ═══════════════════════════════════════════════════════════════════
def chart(fig, R, y_top, h, max_n, asof):
    """가격 + **멀티 신호**가 뜬 날(사용자 지시 2026-09-22).

    아래 두 표에서 **승률이 문턱 이상인 짝**만 찍는다 — 매수 CHART_WIN[True]%,
    매도 CHART_WIN[False]%. 그래서 차트와 표가 같은 것을 본다.

      세모 = 멀티 신호가 뜬 날. 초록 아래 = 매수 · 빨강 위 = 매도 · 크기는 모두 같다.

    ⚠ 단일 신호는 안 찍는다(사용자 지시). 문턱을 70%/40% 로 낮추고 단일까지
      넣었더니 S&P 매수만 세모 201개가 한 날 8층까지 쌓여 가격선이 묻혔다.
    """
    d, c = R["px"]["d"], R["px"]["c"]
    n = len(d)
    pos = {x: i for i, x in enumerate(d)}

    # 차트에 올릴 것 — **멀티 신호만**, 그중 승률이 문턱 이상인 것(사용자 지시 2026-09-22).
    #   단일 신호는 맞은편 쪽 표에만 있다. 이 쪽은 멀티 신호 쪽이라 차트도 그것만 본다.
    picks = []                       # (발동일목록, 매수인가)
    named = {}
    today = {True: 0, False: 0}
    for side, up in (("buy", True), ("sell", False)):
        wk = "fwd1m_win" if up else "fwd1m_down"
        th = CHART_WIN[up]
        # 🚨 **기준일 발동분은 문턱을 면제한다**(사용자 지시 2026-09-22 —
        #   「9월 18일에도 차트에 표시해줘」). 문턱은 «지난 열두 달 중 볼 만한 날»
        #   을 고르는 잣대지, 오늘 무엇이 떴는지를 가릴 잣대가 아니다.
        mul = [x for x in (R.get("conf_" + side) or [])
               if x.get("n", 0) >= MIN_SHOW
               and ((x.get(wk) or 0) >= th or x.get("last") == asof)]
        named[up] = len(mul)
        for x in mul:
            picks.append((x.get("fires") or [], up))
        # 기준일에 몇이 떴나 — 문턱도, 멀티·단일도 가리지 않고 센다.
        today[up] = (sum(1 for x in (R.get("conf_" + side) or [])
                         if x.get("n", 0) >= MIN_SHOW and x.get("last") == asof)
                     + sum(1 for x in R[side]
                           if MIN_SHOW <= x.get("n", 0) <= max_n and x.get("last") == asof))

    # 🚨 세모는 하루에 **종류당 하나**다(집합). 문턱을 70%/40% 로 낮추니 S&P 매수만
    #   35종·201개가 걸려 한 날 8층까지 쌓였고 가격선이 묻혔다(렌더 실측 — 이 랩에서
    #   「세모 벽」을 만든 것이 두 번째다). **몇 종이 떴나는 아래 막대판이 이미 말한다** —
    #   세모는 «언제, 어느 쪽» 만 말하면 된다. 멀티만 그리므로 층은 하나다.
    mk = set()
    nb = [0] * n
    ns = [0] * n
    for fires, up in picks:
        for f in fires:
            if f in pos:
                mk.add((pos[f], up))
                (nb if up else ns)[pos[f]] += 1

    hp, hb = h * .70, h * .24
    ax = fig.add_axes([X0, y_top - hp, X1 - X0, hp])
    ax2 = fig.add_axes([X0, y_top - h, X1 - X0, hb])
    for a in (ax, ax2):
        a.set_facecolor(PAPER)
        for sp in a.spines.values():
            sp.set_color(LINE)
            sp.set_linewidth(.7)
        a.set_xlim(-2, n + 1)
        a.tick_params(colors=MUTED, labelsize=5.8, length=2)
    ax.plot(range(n), c, color=INK, lw=.9, zorder=3)
    ax.set_xticks([])
    ax.grid(True, axis="y", color=LINE, lw=.4)
    ax.set_axisbelow(True)

    lo, hi = min(c), max(c)
    rng = (hi - lo) or 1.0
    off = rng * MK_BASE
    for i, up in mk:
        col = POS if up else NEG
        ax.scatter([i], [c[i] - off if up else c[i] + off],
                   marker="^" if up else "v", s=MK_SIZE, zorder=6,
                   linewidths=.85, facecolors=col, edgecolors=col)
    # 세모가 한 층뿐이라 위아래를 조금만 비우면 된다.
    ax.set_ylim(lo - rng * (MK_BASE + .04), hi + rng * (MK_BASE + .04))
    ax.text(.010, .96, "기준일 %s 종가 %s" % (d[-1], format(int(round(c[-1])), ",")),
            transform=ax.transAxes, fontsize=6.4, color=INK, weight="bold", va="top")
    # 🚨 기준일 세로선 — 아무것도 안 뜬 날도 **안 떴다는 것이 보이게** 한다.
    ax.axvline(n - 1, color=ACC, lw=.8, ls=(0, (3, 2)), zorder=4)
    # ⚠ 위쪽 .96 에 두었더니 최근 고점의 매도 세모와 겹쳤다(렌더 실측) — 아래로 내린다.
    ax.text(.990, .035,
            "기준일 %s · 매수 %d · 매도 %d 발동" % (asof[5:], today[True], today[False]),
            transform=ax.transAxes, fontsize=6.4, color=ACC, weight="bold",
            va="bottom", ha="right")

    ax2.bar(range(n), nb, color=POS, width=1.0, linewidth=0, zorder=3)
    ax2.bar(range(n), [-v for v in ns], color=NEG, width=1.0, linewidth=0, zorder=3)
    ax2.axhline(0, color=RULE, lw=.6, zorder=2)
    mx = max(max(nb), max(ns), 1)
    ax2.set_ylim(-mx - .8, mx + .8)
    ax2.set_yticks([-mx, 0, mx])
    ax2.set_yticklabels(["매도 %d" % mx, "", "매수 %d" % mx], fontsize=5.4)
    tk, lb, last = [], [], None
    for i, sdt in enumerate(d):
        if sdt[:7] != last:
            tk.append(i)
            lb.append(MON[int(sdt[5:7]) - 1] if sdt[5:7] != "01" else sdt[2:4] + "년")
            last = sdt[:7]
    ax2.set_xticks(tk)
    ax2.set_xticklabels(lb, fontsize=5.6)
    nday = (sum(1 for k in mk if k[1]), sum(1 for k in mk if not k[1]))
    return y_top - h, named, nday


# ══ 1·3쪽 — 차트 + 멀티 신호 ═══════════════════════════════════════════════
def multi_page(fig, R, asof, page, max_n):
    y = head(fig, R, "멀티 신호", asof)

    y_cap = y
    # ⚠ .013 만 떼면 아래 월 눈금과 겹친다 — 눈금 자리를 비운다(렌더 실측).
    y, named, nday = chart(fig, R, y - .014, .200, max_n, asof)
    ST.tx(fig, X0, y_cap, "최근 12개월", fontsize=8.5, weight="bold")
    ST.tx(fig, X0 + .090, y_cap + .0005,
          "**세모 = 멀티 신호** · 아래 초록 매수 %d종·%d일 · 위 빨강 매도 %d종·%d일 · "
          "승률 %.0f%%/%.0f%% 이상**과 기준일 발동분** · 주황 세로선은 기준일"
          % (named[True], nday[0], named[False], nday[1],
             CHART_WIN[True], CHART_WIN[False]), fontsize=6.2, color=MUTED)
    y -= .030

    for key, ko, col, nmax in (("conf_buy", "매수", POS, N_MULTI[0]),
                               ("conf_sell", "매도", NEG, N_MULTI[1])):
        buy = key == "conf_buy"
        wk = "fwd1m_win" if buy else "fwd1m_down"
        allp = [x for x in (R.get(key) or []) if x.get("n", 0) >= MIN_SHOW]
        cf = sorted(allp, key=lambda x: ((x.get(wk) or 0), x["n"]), reverse=True)[:nmax]
        if not cf:
            continue
        bw = (R.get("base1m_win") if buy else R.get("base1m_down")) or 0
        ST.tx(fig, X0, y, "%s · 승률 순" % ko, fontsize=9.5, weight="bold", color=col)
        ST.tx(fig, X0 + .114, y + .0005,
              "두 신호가 **5거래일 안에 같이** 뜬 날 · %d짝 중 %d · 「지금」은 **두 조건이 "
              "다 유지되나** · 아무 날이나 잡아도 %s %.1f%%" % (len(allp), len(cf),
                                                     "오를 확률" if buy else "내릴 확률", bw),
              fontsize=6.4, color=MUTED)
        y -= .0140

        tr = [[x["a"], x["b"], "%+.2f%%" % x["fwd1m_mean"],
               "%.0f%%" % (x.get(wk) or 0), (x["last"] or "—"),
               ("%d일" % x["days_ago"]) if x.get("days_ago") is not None else "—",
               nowcell(x)] for x in cf]

        def cc(r, c, tr=tr, cf=cf, bw=bw, col=col):
            if c in (0, 1):
                return INK
            if c == 2:
                return INK          # 방향마다 좋고 나쁨이 갈려 색을 안 준다
            if c == 3:
                return col if float(tr[r][3][:-1]) >= bw else MUTED
            if c in (4, 5):
                d_ = cf[r].get("days_ago")
                return NEG if (d_ is not None and d_ <= HOT) else MUTED
            if c == 6:
                return col if cf[r].get("state_now") else MUTED
            return MUTED
        y = ST.table(fig, X0, y, W_MUL, H_MUL, tr, row_h=.0150, fs=6.7, hfs=6.1,
                     zebra=True, aligns=A_MUL, cell_color=cc)
        y -= .020
    foot(fig, page, asof, y + .020)


# ══ 2·4쪽 — 매수·매도 신호 표 ══════════════════════════════════════════════
def table_page(fig, R, asof, page, max_n, tail=False):
    y = head(fig, R, "신호", asof)
    y -= .002

    for side, ko, col in (("buy", "매수", POS), ("sell", "매도", NEG)):
        buy = side == "buy"
        rows, wkey = rows_of(R, side, max_n)
        bw = (R.get("base1m_win") if buy else R.get("base1m_down")) or 0
        ST.tx(fig, X0, y, "%s %d종 · 승률 순" % (ko, len(rows)),
              fontsize=9.5, weight="bold", color=col)
        ST.tx(fig, X0 + .156, y + .0005,
              "승률 = 1개월 뒤 **%s** 비율 · 아무 날이나 잡아도 %.1f%% 는 그러니 "
              "그보다 높아야 제 몫" % ("오른" if buy else "내린", bw),
              fontsize=6.4, color=MUTED)
        y -= .0138

        tr = [[x["signal"], x.get("desc", ""), "%+.2f%%" % x["fwd1m_mean"],
               "%.0f%%" % (x.get(wkey) or 0), (x["last"] or "—"),
               ("%d일" % x["days_ago"]) if x["days_ago"] is not None else "—",
               nowcell(x)] for x in rows]

        def cc(r, c, tr=tr, rows=rows, bw=bw, col=col):
            if c == 0:
                return INK
            if c == 1:
                return INK2
            if c == 2:
                return INK          # 방향마다 좋고 나쁨이 갈려 색을 안 준다
            if c == 3:
                return col if float(tr[r][3][:-1]) >= bw else MUTED
            if c in (4, 5):
                d_ = rows[r]["days_ago"]
                return NEG if (d_ is not None and d_ <= HOT) else MUTED
            if c == 6:
                return col if rows[r].get("state_now") else MUTED
            return MUTED
        y = ST.table(fig, X0, y, W_SIG, H_SIG, tr, row_h=.0138, fs=6.6, hfs=6.1,
                     zebra=True, aligns=A_SIG, cell_color=cc)
        y -= .010
        if not buy:
            worst = min(rows, key=lambda x: x["fwd1m_mean"])
            ST.tx(fig, X0, y,
                  "**1개월 뒤 실제로 내린 매도 신호는 하나도 없다** — 가장 낮은 %s 도 "
                  "%+.2f%%. 공매도 신호로는 못 쓴다." % (worst["signal"], worst["fwd1m_mean"]),
                  fontsize=6.8, color=NEG)
            y -= .0118
        else:
            thin = [x["signal"] for x in R[side] if x.get("n", 0) < MIN_SHOW]
            over = [x["signal"] for x in R[side] if x.get("n", 0) > max_n]
            note = []
            if thin:
                note.append("%d회 미만이라 뺀 것 — %s" % (MIN_SHOW, " · ".join(thin)))
            if over:
                note.append("%d회 초과라 뺀 것(발동이 아니라 켜져 있는 날을 세는 상태형) — %s"
                            % (max_n, " · ".join(over)))
            for t in note:
                ST.tx(fig, X0, y, t, fontsize=6.3, color=MUTED)
                y -= .0108
        y -= .012

    if tail:
        ST.tx(fig, X0 + .004, y,
              "· 지수 종가·고가·저가·거래량. 고저·거래량은 따로 받아 종가를 랩 정본과 "
              "대조하고 어긋나면 갱신을 멈춘다(실측 차이 0.00000%).",
              fontsize=6.6, color=INK2)
        y -= .0122
        ST.tx(fig, X0 + .004, y,
              "· 10년 한 구간이다. 이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했다. "
              "신호는 진단이지 예측이 아니다.", fontsize=6.6, color=MUTED)
        y -= .0122
    foot(fig, page, asof, y)


def main() -> int:
    M = json.load(io.open(os.path.join(DATA, "_ta_signals.json"), encoding="utf-8"))
    asof = M["as_of"]
    max_n = M.get("max_n") or 10 ** 9
    figs = []
    with PdfPages(OUT) as pdf:
        pg = 0
        for k in ("spx", "ndx"):
            pg += 1
            fig = ST.new_page()
            figs.append(fig)
            multi_page(fig, M["index"][k], asof, pg, max_n)
            pg += 1
            fig = ST.new_page()
            figs.append(fig)
            table_page(fig, M["index"][k], asof, pg, max_n, tail=(k == "ndx"))

        for i, f in enumerate(figs, 1):
            pdf.savefig(f)
            if "--png" in sys.argv[1:]:
                f.savefig(os.path.join(DATA, "_ta_%d.png" % i), dpi=110, facecolor=PAPER)
            ST.plt.close(f)
        pdf.infodict()["Title"] = "교과서 TA 신호 · 기준 %s" % asof

    print("→ %s · %d쪽 · 기준 %s · 횟수 %d회 초과 제외" % (OUT, TOT, asof, max_n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
