# -*- coding: utf-8 -*-
"""build/ta_signals_pdf.py — 교과서 TA 신호 → data/ta_signals.pdf (A4 6쪽)

자료는 build/ta_signals.py 가 낸 data/_ta_signals.json 하나뿐이다.

  1·3쪽  지수 차트(가격 + 날짜별 신호 수) + 매수 표
  2·4쪽  매도 표 + 말 뜻
  5·6쪽  신호 합류(지수별) · 읽는 법

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

HOT = 10
TOT = 6
W = [.122, .236, .036, .050, .040, .054, .072, .036, .092]
HEAD = ["신호", "무엇을 보나", "횟수", "1개월", "승률", "기준선차", "최근 발동", "경과", "지금"]
MON = ["1월", "2월", "3월", "4월", "5월", "6월",
       "7월", "8월", "9월", "10월", "11월", "12월"]


def foot(fig, page, asof):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .024,
          "여두 전략 랩 · 교과서 TA 신호 · 기준 %s · 통계는 최근 10년 · 차트는 최근 12개월"
          % asof, fontsize=6.4, color=MUTED)
    ST.tx(fig, X1, .024, "%d / %d · %s" % (page, TOT, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


CIRC = "①②③④⑤⑥⑦⑧⑨⑩"
# 🚨 차트 표기 규칙 — 사용자 지시 2026-09-22.
#   「신호합류 말고 아무 단일 시그널 두개 뜨면 차트 표시인건 어때.
#     근데 1개월 성과 더 좋은거로만 두개 이상」
#   짝을 미리 정해 두는 합류(conf_buy/conf_sell) 대신, **그날 좋은 신호가 몇 개 켜졌나**
#   로 본다. 짝 목록에 없는 조합도 잡히고, 규칙이 한 줄로 설명된다.
#   · 「좋은 것」 = 1개월 기준선차가 제 방향인 신호(매수 >0 · 매도 <0)
#   · 그런 신호가 **MIN_STACK 개 이상** 켜진 날만 찍는다
MIN_STACK = 2


def chart(fig, R, y_top, h):
    """가격 + 신호 표기 — 원본 ta_lab/swing_panel 방식(가격의 ±% 자리에 ^ / v).

      작은 세모   단일 신호 한 건. 아래 초록 ^ = 매수 · 위 빨강 v = 매도
      속 빈 세모  1개월 **기준선차가 기대와 반대**(매수인데 음수 · 매도인데 양수)
      큰 세모+번호 합류(두 신호가 5일 안에 같이) — 번호는 차트 아래 표와 짝짓는다
    """
    d, c = R["px"]["d"], R["px"]["c"]
    n = len(d)
    pos = {x: i for i, x in enumerate(d)}
    nb = [0] * n; ns = [0] * n
    # 아래 막대판은 **전부** 센다 — 그날 얼마나 시끄러웠나.
    for x in R["buy"]:
        for f in x.get("fires") or []:
            if f in pos:
                nb[pos[f]] += 1
    for x in R["sell"]:
        for f in x.get("fires") or []:
            if f in pos:
                ns[pos[f]] += 1

    # 🚨 세모는 **「좋은 신호가 그날 MIN_STACK 개 이상 켜진 날」** 에만 찍는다.
    #   좋은 것 = 1개월 기준선차가 제 방향(매수 >0 · 매도 <0).
    cg, cm = {}, {}
    nB = nS = 0
    for side, tag, good in (("buy", "매수", lambda e: e > 0),
                            ("sell", "매도", lambda e: e < 0)):
        for x in R[side]:
            if x.get("n", 0) < 5 or not good(x.get("fwd1m_excess") or 0):
                continue
            if tag == "매수":
                nB += 1
            else:
                nS += 1
            for f in (x.get("fires") or []):
                if f in pos:
                    cg.setdefault((f, tag), []).append(x["signal"])
                    cm.setdefault((f, tag), []).append(
                        (x["fwd1m_mean"], x["fwd1m_excess"]))
    cg = {k: v for k, v in cg.items() if len(v) >= MIN_STACK}
    cm = {k: v for k, v in cm.items() if k in cg}
    keys = sorted(cg, reverse=True)

    hp, hb = h * .70, h * .24
    ax = fig.add_axes([X0, y_top - hp, X1 - X0, hp])
    ax2 = fig.add_axes([X0, y_top - h, X1 - X0, hb])
    for a in (ax, ax2):
        a.set_facecolor(PAPER)
        for s in a.spines.values():
            s.set_color(LINE); s.set_linewidth(.7)
        a.set_xlim(-2, n + 1)
        a.tick_params(colors=MUTED, labelsize=5.8, length=2)
    ax.plot(range(n), c, color=INK, lw=.9, zorder=3)
    ax.set_xticks([])
    ax.grid(True, axis="y", color=LINE, lw=.4)
    ax.set_axisbelow(True)

    # 🚨 라벨은 **겹친 개수에 따른 실측 기대수익**이다(ta_signals 의 stack).
    #   종전에 「그날 켜진 신호들의 1개월 평균」을 적었더니 매도가 구조상 음수가 될 수
    #   없었다 — 단일 매도가 전부 양수라 그 평균도 늘 양수다. 겹친 날을 사건으로 놓고
    #   그날부터의 사후수익을 직접 잰 수를 쓴다.
    ER = {}
    for side, tag in (("buy", "매수"), ("sell", "매도")):
        for x in (R.get("stack") or {}).get(side) or []:
            if x.get("n", 0) >= 5:
                ER[(tag, x["k"])] = x["fwd1m_mean"]
    ev = []
    for (fd, tag) in cg:
        kk = len(cm[(fd, tag)])
        er = ER.get((tag, 3)) if kk >= 3 else ER.get((tag, 2))
        ev.append((pos[fd], tag == "매수", er, 0.0, kk))
    # 🚨 63건을 전부 라벨 달았더니 수치가 서로 뭉갰다(렌더 실측). 세모는 다 찍고
    #   **라벨은 간격을 둔다** — 기대수익이 큰 것부터 10봉 이상 떨어진 것만, 최대 10개.
    #   ⚠ 한 통에 담아 고르면 라벨이 매수 쪽에 다 간다 — **방향별로 따로** 다섯씩.
    lab = set()
    for side in (True, False):
        taken = []
        for i, up, er, _ex, _k in sorted((z for z in ev if z[1] is side),
                                         key=lambda z: (-z[4], -z[0])):
            if all(abs(i - j) >= 12 for j in taken):
                lab.add((i, up)); taken.append(i)
            if len(taken) >= 5:
                break
    for i, up, er, _ex, kk in ev:
        col = POS if up else NEG
        yy = c[i] * (.972 if up else 1.028)
        ax.scatter([i], [yy], marker="^" if up else "v", s=10 + 8 * (kk - 1),
                   zorder=6, linewidths=.55, facecolors=col, edgecolors=PAPER)
        if (i, up) in lab and er is not None:
            ax.annotate("%d개 %+.1f%%" % (kk, er), (i, yy),
                        textcoords="offset points", xytext=(0, -9 if up else 5),
                        ha="center", fontsize=5.5, color=col, weight="bold", zorder=7)
    lo, hi = min(c), max(c)
    ax.set_ylim(lo - (hi - lo) * .18, hi + (hi - lo) * .18)
    ax.text(.010, .96, "기준일 %s 종가 %s" % (d[-1], format(int(round(c[-1])), ",")),
            transform=ax.transAxes, fontsize=6.4, color=INK, weight="bold", va="top")

    ax2.bar(range(n), nb, color=POS, width=1.0, linewidth=0, zorder=3)
    ax2.bar(range(n), [-v for v in ns], color=NEG, width=1.0, linewidth=0, zorder=3)
    ax2.axhline(0, color=RULE, lw=.6, zorder=2)
    mx = max(max(nb), max(ns), 1)
    ax2.set_ylim(-mx - .8, mx + .8)
    ax2.set_yticks([-mx, 0, mx])
    ax2.set_yticklabels(["매도 %d" % mx, "", "매수 %d" % mx], fontsize=5.4)
    tk, lb, last = [], [], None
    for i, s in enumerate(d):
        m = s[:7]
        if m != last:
            tk.append(i); lb.append(MON[int(s[5:7]) - 1] if s[5:7] != "01" else s[2:4] + "년")
            last = m
    ax2.set_xticks(tk); ax2.set_xticklabels(lb, fontsize=5.6)
    leg = [(k[0], k[1], sum(a for a, _ in cm[k]) / len(cm[k]), cg[k]) for k in keys]
    nday = (sum(1 for k in cg if k[1] == "매수"), sum(1 for k in cg if k[1] == "매도"))
    return y_top - h, leg, (nB, len(R["buy"]), nS, len(R["sell"]), nday)


def side_page(fig, R, side, asof, page, with_chart, with_legend):
    buy = side == "buy"
    y = .958
    ST.tx(fig, X0, y, "%s · %s 신호" % (R["label"], "매수" if buy else "매도"),
          fontsize=15, weight="bold", color=POS if buy else NEG)
    ST.tx(fig, X1, y, "기준 %s · 통계 10년(%s~) · 기준선 %+.2f%%"
          % (asof, R["start"], R["base1m"]), fontsize=7.2, color=MUTED, ha="right")
    y -= .026
    ST.hline(fig, X0, X1, y, RULE, .9)
    y -= .014

    if with_chart:
        ST.tx(fig, X0, y, "최근 12개월 — 가격과 신호", fontsize=8.5, weight="bold")
        ST.tx(fig, X0 + .200, y + .0005,
              "세모 = **성과 좋은 신호가 그날 %d개 이상** 켜진 날 · 크기는 그 개수 · "
              "옆 수는 **그 개수일 때의 실측 1개월 수익**" % MIN_STACK,
              fontsize=6.2, color=MUTED)
        y -= .014
        y, legend, (nB, tB, nS, tS, nday) = chart(fig, R, y, .200)
        # ⚠ .013 만 뗐더니 아래 월 눈금(막대판 x축)과 겹쳤다 — 눈금 자리를 비운다.
        y -= .026
        ST.tx(fig, X0 + .004, y,
              "**성과 좋은 신호** = 기준선차가 제 방향인 것(매수 양수 %d/%d종 · "
              "매도 음수 %d/%d종). 그중 %d개 이상 겹친 날이 **매수 %d일 · 매도 %d일**."
              % (nB, tB, nS, tS, MIN_STACK, nday[0], nday[1]), fontsize=6.6, color=INK2)
        y -= .0112
        y -= .0006
        # 🚨 이 규칙 자체를 사건으로 재면 얼마인가 — 라벨에 쓴 수의 출처다.
        # ⚠ 루프 변수를 `side` 로 두었다가 **함수 인자 `side` 를 덮어** 매수 쪽에 매도 표가
        #   찍혔다. 이 랩에서 두 번째로 밟은 같은 함정이다(앞서 `ko` 도 그랬다). `sd` 로 쓴다.
        for sd, tag in (("buy", "매수"), ("sell", "매도")):
            xs = [x for x in (R.get("stack") or {}).get(sd) or [] if x.get("n", 0) >= 5]
            if not xs:
                continue
            ST.tx(fig, X0 + .004, y,
                  "**%s** — " % tag + " · ".join(
                      "%d개↑ %d회 **%+.2f%%** (승률 %.0f%% · 기준선차 %+.2f%%p)"
                      % (x["k"], x["n"], x["fwd1m_mean"],
                         (x.get("fwd1m_down") if sd == "sell" else x.get("fwd1m_win")) or 0,
                         x["fwd1m_excess"])
                      for x in xs),
                  fontsize=6.5, color=POS if sd == "buy" else NEG)
            y -= .0110
        ST.tx(fig, X0 + .004, y,
              "아래 막대는 거른 것 없이 그날 켜진 신호를 다 센다. !! 「좋은 신호」를 기준선차 "
              "부호로 고른 것 자체가 전 구간을 본 선택이라 이 수는 **설명용**이다.",
              fontsize=6.4, color=MUTED)
        y -= .0112
        y -= .004
        # 최근 셋은 어떤 신호들이 겹쳤는지 적는다.
        #   ⚠ 넷이면 각주가 꼬리말을 뚫는다(렌더 실측) — 실측 요약 두 줄이 늘어난 몫이다.
        for fd, tag, er, sigs in legend[:3]:
            ST.tx(fig, X0 + .004, y, "%s %s %d개 %+.1f%%" % (fd[5:], tag, len(sigs), er),
                  fontsize=6.4, weight="bold", color=POS if tag == "매수" else NEG)
            ST.tx(fig, X0 + .116, y, " · ".join(sorted(set(sigs)))[:98],
                  fontsize=6.4, color=INK2)
            y -= .0108
        if len(legend) > 3:
            ST.tx(fig, X0 + .004, y, "그 밖 %d일" % (len(legend) - 3),
                  fontsize=6.2, color=MUTED)
            y -= .0108
        y -= .012

    # 🚨 승률의 뜻이 방향마다 다르다(사용자 지적 2026-09-22) — 매수는 **오른** 비율,
    #   매도는 **내린** 비율. 그래야 양쪽 다 «높을수록 제 몫» 이라 둘 다 높은 순으로 선다.
    wkey = "fwd1m_win" if buy else "fwd1m_down"
    bwin = (R.get("base1m_win") if buy else R.get("base1m_down")) or 0
    ST.tx(fig, X0, y, "전체 · 승률 높은 순", fontsize=9, weight="bold")
    # ⚠ 9pt 한글 9자는 .145 다 — .132 로는 부제를 먹었다(렌더 실측).
    ST.tx(fig, X0 + .160, y + .0005,
          "승률 = 1개월 뒤 **%s** 비율 · 아무 날이나 잡아도 **%.1f%%** 는 그러니 "
          "그보다 높아야 제 몫" % ("오른" if buy else "내린", bwin),
          fontsize=6.6, color=MUTED)
    y -= .0140

    rows = [x for x in R[side] if x.get("n", 0) >= 5]
    #   동률은 기준선차로 가른다(매수는 큰 것, 매도는 작은 것이 위).
    rows.sort(key=lambda x: ((x.get(wkey) or 0),
                             (x.get("fwd1m_excess") or 0) * (1 if buy else -1)),
              reverse=True)
    # 🚨 「지금」 칸 — 발동(순간)과 **지속**(그 관계가 유지되나)을 나눠 적는다.
    #   교차 신호가 45일 전에 났어도 이미 되돌아갔으면 «꺼짐» 이다. 그게 알고 싶은 것이다.
    def nowcell(x):
        s = "★" if x.get("fired_today") else ""
        if x.get("state_now"):
            d_ = x.get("state_days")
            return s + ("켜짐%d일" % d_ if d_ is not None else "켜짐")
        return s + "꺼짐"
    tr = [[x["signal"][:16], x.get("desc", ""), str(x["n"]),
           "%+.2f%%" % x["fwd1m_mean"], "%.0f%%" % (x.get(wkey) or 0),
           "%+.2f%%p" % x["fwd1m_excess"], (x["last"] or "—"),
           ("%d일" % x["days_ago"]) if x["days_ago"] is not None else "—",
           nowcell(x)] for x in rows]

    def cc(r, c, tr=tr, rows=rows):
        if c == 0:
            return INK
        if c == 1:
            return INK2
        if c == 2:
            # 횟수가 주황이면 «켜져 있는 모든 날» 을 센 줄이다(상태형).
            return ACC if rows[r]["kind"] == "state" else MUTED
        if c == 5:
            return POS if not tr[r][5].startswith("-") else NEG
        if c in (6, 7):
            d_ = rows[r]["days_ago"]
            return NEG if (d_ is not None and d_ <= HOT) else MUTED
        if c == 8:
            return (POS if buy else NEG) if rows[r].get("state_now") else MUTED
        return MUTED
    y = ST.table(fig, X0, y, W, HEAD, tr, row_h=.0144, fs=6.6, hfs=6.1, zebra=True,
                 aligns=["l", "l", "r", "r", "r", "r", "l", "r", "c"], cell_color=cc)
    thin = [x["signal"] for x in R[side] if x.get("n", 0) < 5]
    if thin:
        y -= .011
        ST.tx(fig, X0, y, "횟수 5회 미만이라 통계를 안 낸 것 — %s" % " · ".join(thin),
              fontsize=6.3, color=MUTED)
    if not buy:
        y -= .016
        worst = min(rows, key=lambda x: x["fwd1m_mean"])
        neg = sum(1 for x in rows if x["fwd1m_excess"] < 0)
        ST.tx(fig, X0, y,
              "매도 %d종 중 기준선보다 덜 오른 것은 %d종이고, **1개월 뒤 실제로 내린 것은 "
              "하나도 없다**(가장 낮은 %s 도 %+.2f%%). 공매도 신호로는 못 쓴다."
              % (len(rows), neg, worst["signal"], worst["fwd1m_mean"]),
              fontsize=6.9, color=NEG)
    if with_legend:
        y -= .024
        ST.tx(fig, X0, y, "말 뜻", fontsize=9, weight="bold")
        y -= .0135
        # ⚠ 한 줄짜리로 두었다가 「기준선차」 설명이 길어져 오른쪽으로 넘쳤다(렌더 실측).
        #   값이 여러 줄이면 그대로 이어 적는다. 라벨 폭도 .044 → .058 로 넓힌다.
        for k, vs in (
            ("기준선차", ["신호가 난 뒤 1개월 **지수 수익** - **아무 날이나 샀을 때**의 "
                        "1개월 지수 수익(%s %+.2f%%)" % (R["label"], R["base1m"]),
                        "**둘 다 같은 지수의 등락이다.** 다른 것을 견준 «초과수익» 이 아니라 "
                        "«이 신호가 붙는 날이 보통 날과 다른가» 를 재는 것이다"]),
            ("승률", ["매수는 1개월 뒤 **오른** 비율, 매도는 **내린** 비율이다. 양쪽 다 "
                     "**높을수록 제 몫을 한 것**이라 둘 다 높은 순으로 놓았다",
                     "아무 날이나 잡아도 오를 확률이 %.1f%% · 내릴 확률이 %.1f%% 다 — "
                     "그 수가 중립이지 50%% 가 아니다"
                     % (R.get("base1m_win") or 0, R.get("base1m_down") or 0)]),
            ("횟수", ["신호가 **처음 켜진 날**을 센 것. **주황색**은 켜져 있는 모든 날을 센 줄"]),
            ("지금", ["**켜짐** = 그 조건이 지금도 유지된다(교차 신호는 교차 뒤에도 그 위/아래에 "
                     "있다는 뜻). 뒤의 날수는 그 상태가 며칠째인지다"]),
            ("꺼짐", ["발동은 했지만 **이미 되돌아갔다.** 45일 전 상향교차가 꺼짐이면 그 사이에 "
                     "다시 아래로 내려온 것이다"]),
            ("★", ["기준일 **그날** 발동했다"]),
        ):
            ST.tx(fig, X0 + .006, y, k, fontsize=6.8, weight="bold", color=ACC)
            for v in vs:
                ST.tx(fig, X0 + .058, y, v, fontsize=6.8, color=INK2)
                y -= .0110
    foot(fig, page, asof)


def conf_page(fig, R, asof, page, tail=False):
    y = .958
    ST.tx(fig, X0, y, "%s · 신호 합류" % R["label"], fontsize=15, weight="bold")
    ST.tx(fig, X1, y, "기준 %s · 기준선 %+.2f%%" % (asof, R["base1m"]),
          fontsize=7.2, color=MUTED, ha="right")
    y -= .026
    ST.hline(fig, X0, X1, y, RULE, .9)
    y -= .016
    ST.tx(fig, X0, y,
          "두 신호가 **5거래일 안에 같이** 발동한 날만 센 것이다. «단독» 은 그 신호 혼자일 "
          "때의 기준선차 — 합류가 그보다 크면 «같이 보는 것»이 값을 한 것이다.",
          fontsize=7.0, color=INK2)
    y -= .020

    for side, ko, nmax, rev in (("conf_buy", "매수 합류", 20, True),
                                ("conf_sell", "매도 합류", 11, False)):
        cf = sorted(R.get(side) or [], key=lambda x: x["fwd1m_excess"], reverse=rev)[:nmax]
        if not cf:
            continue
        ST.tx(fig, X0, y, ko, fontsize=10, weight="bold", color=POS if rev else NEG)
        ST.tx(fig, X0 + .090, y + .0005,
              "%d짝 중 상위 %d · 기준선차 %s 순" % (len(R[side]), len(cf), "높은" if rev else "낮은"),
              fontsize=6.4, color=MUTED)
        # 🚨 이 줄은 **y 를 내리기 전에** 그린다. 뒤로 옮겼다가 표 머리글 위에 찍혔다(렌더 실측).
        ST.tx(fig, X0 + .300, y + .0005,
              "「단독 대비」 = 합류 기준선차 - 나은 쪽 단독 기준선차 · **%s가 같이 본 값**"
              % ("양수" if rev else "음수"), fontsize=6.4, color=MUTED)
        y -= .0135
        # 🚨 「단독 대비」도 **기준선차와 같은 부호 규약**이다.
        #   매수는 양수가, 매도는 음수가 «같이 보는 것이 값을 했다» 는 뜻이다.
        #   종전에 «더 나아진 것» 이라 이름 붙였다가 매도 표에서 음수가 좋은 것이 되어
        #   또 어긋났다 — 이름을 중립으로 바꾸고 표마다 한 줄로 밝힌다.
        tr = []
        for x in cf:
            sa, sb = x.get("solo_a") or 0, x.get("solo_b") or 0
            best = max(sa, sb) if rev else min(sa, sb)
            tr.append([x["a"][:17], x["b"][:17], str(x["n"]),
                       "%+.2f%%" % x["fwd1m_mean"],
                       "%.0f%%" % ((x.get("fwd1m_win") if rev
                                    else x.get("fwd1m_down")) or 0),
                       "%+.2f%%p" % x["fwd1m_excess"],
                       "%+.2f / %+.2f" % (sa, sb),
                       "%+.2f%%p" % (x["fwd1m_excess"] - best), x["last"]])

        def cc(r, c, tr=tr):
            if c in (0, 1):
                return INK
            if c in (5, 7):
                return POS if not tr[r][c].startswith("-") else NEG
            return MUTED
        y = ST.table(fig, X0, y,
                     [.158, .158, .038, .052, .042, .058, .098, .062, .074],
                     ["신호 A", "신호 B", "횟수", "1개월", "승률", "합류 기준선차",
                      "단독 기준선차 A/B", "단독 대비", "최근"], tr,
                     row_h=.0158, fs=6.7, hfs=6.1, zebra=True,
                     aligns=["l", "l", "r", "r", "r", "r", "r", "r", "l"], cell_color=cc)
        y -= .020

    if tail:
        ST.tx(fig, X0, y, "읽는 법", fontsize=10, weight="bold")
        y -= .0150
        for ln, col in (
            ("**신호는 진단이지 예측이 아니다.** 지금 무엇이 극단인지를 보는 것이다.", INK2),
            ("**매도 신호는 공매도 신호가 아니다.** 양 지수 모두, 1개월 뒤 실제로 내린 "
             "매도 신호가 하나도 없다.", NEG),
            ("**Donchian 하단 이탈은 이름만 매도다.** 기준선차가 양수로 매수 쪽에 가깝다.", NEG),
            ("**횟수를 먼저 보라.** 10~20회짜리는 기준선차가 커 보여도 운일 수 있다.", MUTED),
            ("**「단독 대비」가 0 쪽이면 합류가 헛것이다** — 둘 중 나은 신호 혼자로 충분하다는 "
             "뜻이다. 매수는 양수, 매도는 음수일 때만 같이 본 값이 있다.", MUTED),
            ("**10년 한 구간이다.** 이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했다.", MUTED),
        ):
            ST.tx(fig, X0 + .004, y, "· " + ln, fontsize=6.9, color=col)
            y -= .0128
        y -= .010
        ST.tx(fig, X0, y, "자료", fontsize=10, weight="bold")
        y -= .0150
        for ln in ("지수 종가·고가·저가·거래량. 고저·거래량은 따로 받아 종가를 랩 정본과 "
                   "대조하고 어긋나면 갱신을 멈춘다(실측 차이 0.00000%).",
                   "기준일은 랩 격자로 자른다. 사후수익은 달력 +7일 / +30일 — 신호가 난 날 "
                   "종가에 사서 그날까지 든 것이다."):
            ST.tx(fig, X0 + .004, y, "· " + ln, fontsize=6.9, color=INK2)
            y -= .0128
    foot(fig, page, asof)


def main() -> int:
    M = json.load(io.open(os.path.join(DATA, "_ta_signals.json"), encoding="utf-8"))
    asof = M["as_of"]
    figs = []
    with PdfPages(OUT) as pdf:
        pg = 0
        for k in ("spx", "ndx"):
            for side in ("buy", "sell"):
                pg += 1
                fig = ST.new_page(); figs.append(fig)
                side_page(fig, M["index"][k], side, asof, pg,
                          with_chart=(side == "buy"), with_legend=(side == "sell"))
        for i, k in enumerate(("spx", "ndx")):
            pg += 1
            fig = ST.new_page(); figs.append(fig)
            conf_page(fig, M["index"][k], asof, pg, tail=(i == 1))

        for i, f in enumerate(figs, 1):
            pdf.savefig(f)
            if "--png" in sys.argv[1:]:
                f.savefig(os.path.join(DATA, "_ta_%d.png" % i), dpi=110, facecolor=PAPER)
            ST.plt.close(f)
        pdf.infodict()["Title"] = "교과서 TA 신호 · 기준 %s" % asof

    print("→ %s · %d쪽 · 기준 %s" % (OUT, TOT, asof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
