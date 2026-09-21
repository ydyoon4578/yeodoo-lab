# -*- coding: utf-8 -*-
"""build/ta_signals_pdf.py — 교과서 TA 신호 검증 → data/ta_signals.pdf

자료는 build/ta_signals.py 가 낸 data/_ta_signals.json 하나뿐이다.
쪽 구성: 지수마다 매수 한 쪽·매도 한 쪽 + 합류·읽는 법 한 쪽 = 5쪽.

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
TOT = 5
W = [.128, .268, .040, .054, .044, .058, .076, .042, .030]
HEAD = ["신호", "무엇을 보나", "횟수", "1개월", "승률", "초과", "최근 발동", "경과", ""]


def foot(fig, page, asof):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .024,
          "여두 전략 랩 · 교과서 TA 신호 · 기준 %s · 10년 · S&P 500 / NASDAQ 100 가격지수"
          % asof, fontsize=6.4, color=MUTED)
    ST.tx(fig, X1, .024, "%d / %d · %s" % (page, TOT, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def legend(fig, y, base1m):
    """말 뜻 — 이 문서에서 헷갈릴 만한 넷을 맨 앞에 박는다."""
    items = [
        ("초과", "신호가 난 뒤 1개월 수익 - **아무 날이나 샀을 때**의 1개월 수익(%+.2f%%)"
                 % base1m),
        ("횟수", "신호가 **처음 켜진 날**을 센 것. 「상태」 줄만 켜져 있는 **모든 날**을 센다"),
        ("상태", "켜졌다 꺼지는 사건이 아니라 **조건이 유지되는 구간**. 횟수가 수천이 된다"),
        ("★", "기준일에 그 조건이 **아직 켜져 있다**"),
    ]
    # ⚠ 상자 높이를 .052 로 뒀더니 넷째 줄이 밖으로 나가 아래 제목과 겹쳤다(렌더 실측).
    #   줄 간격 .0108 × 4 + 머리 .026 = .069.
    bh = .026 + .0108 * len(items)
    ST.box(fig, X0, y - bh, X1 - X0, bh, PANEL2, z=0)
    ST.tx(fig, X0 + .008, y - .011, "말 뜻", fontsize=8.5, weight="bold")
    for i, (k, v) in enumerate(items):
        yy = y - .0265 - i * .0108
        ST.tx(fig, X0 + .010, yy, k, fontsize=6.8, weight="bold", color=ACC)
        ST.tx(fig, X0 + .048, yy, v, fontsize=6.8, color=INK2)
    return y - bh - .012


def side_page(fig, R, side, asof, page):
    buy = side == "buy"
    y = .958
    ST.tx(fig, X0, y, "%s · %s 신호" % (R["label"], "매수" if buy else "매도"),
          fontsize=15, weight="bold", color=POS if buy else NEG)
    ST.tx(fig, X1, y, "기준 %s · 최근 10년(%s~) · %d거래일"
          % (asof, R["start"], R["n_days"]), fontsize=7.2, color=MUTED, ha="right")
    y -= .026
    ST.hline(fig, X0, X1, y, RULE, .9)
    y -= .016

    y = legend(fig, y, R["base1m"])

    hot = sorted([x for x in R[side] if x["days_ago"] is not None and x["days_ago"] <= HOT],
                 key=lambda z: z["days_ago"])
    # ⚠ 9pt 한글은 글자당 약 .0161 — «최근 10일 안에 발동» 이 .177 이라 .110 으로는 먹었다.
    ST.tx(fig, X0, y, "최근 %d일 안에 발동" % HOT, fontsize=9, weight="bold")
    ST.tx(fig, X0 + .190, y + .0005, "%d종" % len(hot), fontsize=7.4,
          color=POS if buy else NEG)
    y -= .0140
    items = ["%s %s" % (x["signal"], x["last"][5:]) for x in hot] or ["없음"]
    lines, cur = [], ""
    for it in items:
        nxt = (cur + "   ·   " + it) if cur else it
        if len(nxt) > 110 and cur:
            lines.append(cur); cur = it
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    for ln in lines[:3]:
        ST.tx(fig, X0 + .004, y, ln, fontsize=6.8, color=POS if buy else NEG)
        y -= .0118
    y -= .008

    ST.tx(fig, X0, y, "전체 · 초과 %s 순" % ("높은" if buy else "낮은"),
          fontsize=9, weight="bold")
    ST.tx(fig, X0 + .180, y + .0005,
          ("초과가 클수록 기준선보다 더 올랐다" if buy else
           "매도 신호는 **초과가 음수일수록** 제 몫을 한 것 — 색은 부호를 따른다"),
          fontsize=6.6, color=MUTED)
    y -= .0140

    rows = [x for x in R[side] if x.get("n", 0) >= 5]
    rows.sort(key=lambda x: (x.get("fwd1m_excess") or 0), reverse=buy)
    tr = [[x["signal"][:16], x.get("desc", ""), str(x["n"]),
           "%+.2f%%" % x["fwd1m_mean"], "%.0f%%" % x["fwd1m_win"],
           "%+.2f%%p" % x["fwd1m_excess"], (x["last"] or "—"),
           ("%d일" % x["days_ago"]) if x["days_ago"] is not None else "—",
           ("상태" if x["kind"] == "state" else "") + ("★" if x["on_now"] else "")]
          for x in rows]

    def cc(r, c, tr=tr, rows=rows):
        if c == 0:
            return INK
        if c == 1:
            return INK2
        if c == 5:
            return POS if not tr[r][5].startswith("-") else NEG
        if c in (6, 7):
            d = rows[r]["days_ago"]
            return NEG if (d is not None and d <= HOT) else MUTED
        if c == 8:
            return ACC
        return MUTED
    y = ST.table(fig, X0, y, W, HEAD, tr, row_h=.0158, fs=6.8, hfs=6.2, zebra=True,
                 aligns=["l", "l", "r", "r", "r", "r", "l", "r", "c"], cell_color=cc)

    thin = [x["signal"] for x in R[side] if x.get("n", 0) < 5]
    if thin:
        y -= .012
        ST.tx(fig, X0, y, "횟수가 5회 미만이라 통계를 안 낸 것 — %s" % " · ".join(thin),
              fontsize=6.4, color=MUTED)
    if not buy:
        y -= .018
        worst = min(rows, key=lambda x: x["fwd1m_mean"])
        neg = sum(1 for x in rows if x["fwd1m_excess"] < 0)
        ST.tx(fig, X0, y,
              "매도 신호 %d종 가운데 기준선보다 덜 오른 것은 %d종이고, **1개월 뒤 실제로 "
              "내린 것은 하나도 없다**(가장 낮은 %s 도 %+.2f%%)."
              % (len(rows), neg, worst["signal"], worst["fwd1m_mean"]),
              fontsize=7.0, color=NEG)
        y -= .0125
        ST.tx(fig, X0, y,
              "그래서 **공매도 신호로는 못 쓴다.** 차익실현·신규매수 자제로만 읽는다.",
              fontsize=7.0, color=NEG)
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
                side_page(fig, M["index"][k], side, asof, pg)

        pg += 1
        fig = ST.new_page(); figs.append(fig)
        y = .958
        ST.tx(fig, X0, y, "신호 합류 · 이 표를 어떻게 읽나", fontsize=15, weight="bold")
        ST.tx(fig, X1, y, "기준 %s" % asof, fontsize=7.4, color=MUTED, ha="right")
        y -= .026
        ST.hline(fig, X0, X1, y, RULE, .9)
        y -= .018
        ST.tx(fig, X0, y,
              "지표 하나만 보지 말라는 것이 이 카탈로그의 첫째 원칙이다. 두 신호가 "
              "**5거래일 안에 같이** 발동한 날만 세면 단독보다 낫다.",
              fontsize=7.2, color=INK2)
        y -= .022
        for k, ko in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
            R = M["index"][k]
            cf = sorted([x for x in R["confluence"] if x.get("n", 0) >= 5],
                        key=lambda x: -(x.get("fwd1m_excess") or -99))
            ST.tx(fig, X0, y, ko, fontsize=11, weight="bold")
            ST.tx(fig, X0 + .150, y + .001,
                  "기준선 %+.2f%% (아무 날이나 샀을 때 1개월)" % R["base1m"],
                  fontsize=6.6, color=MUTED)
            y -= .0140
            tr = [[x["pair"][:34], str(x["n"]), "%+.2f%%" % x["fwd1m_mean"],
                   "%.0f%%" % x["fwd1m_win"], "%+.2f%%p" % x["fwd1m_excess"],
                   x["last"] or "—"] for x in cf]

            def cc2(r, c, tr=tr):
                if c == 4:
                    return POS if not tr[r][4].startswith("-") else NEG
                return INK if c == 0 else MUTED
            y = ST.table(fig, X0, y, [.245, .050, .070, .055, .075, .086],
                         ["짝", "횟수", "1개월", "승률", "초과", "최근 발동"], tr,
                         row_h=.0165, fs=7.0, hfs=6.3, zebra=True,
                         aligns=["l", "r", "r", "r", "r", "l"], cell_color=cc2)
            thin = [x for x in R["confluence"] if x.get("n", 0) < 5]
            if thin:
                y -= .011
                ST.tx(fig, X0, y, "횟수 5회 미만이라 통계를 안 낸 짝 %d개" % len(thin),
                      fontsize=6.4, color=MUTED)
            y -= .024

        ST.tx(fig, X0, y, "읽는 법", fontsize=11, weight="bold")
        y -= .0155
        for ln, col in (
            ("**신호는 진단이지 예측이 아니다.** 지금 무엇이 극단인지를 보는 것이다.", INK2),
            ("**매도 신호는 공매도 신호가 아니다.** 양 지수 모두, 1개월 뒤 실제로 내린 "
             "매도 신호가 하나도 없다.", NEG),
            ("**Donchian 하단 이탈은 이름만 매도다.** 초과 +1.71%p 로 매수 쪽에 가깝다.", NEG),
            ("**횟수를 먼저 보라.** 10~20회짜리는 초과가 커 보여도 운일 수 있다.", MUTED),
            ("**「상태」 줄은 무게가 다르다.** 켜져 있는 모든 날을 세서 횟수가 수천이고, "
             "관측이 서로 겹친다.", MUTED),
            ("**10년 한 구간이다.** 이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했다.", MUTED),
        ):
            ST.tx(fig, X0 + .004, y, "· " + ln, fontsize=7.0, color=col)
            y -= .0135
        y -= .012

        ST.tx(fig, X0, y, "자료", fontsize=11, weight="bold")
        y -= .0155
        for ln in (
            "지수 종가·고가·저가·거래량을 쓴다. 고저·거래량은 따로 받아 종가를 랩 정본과 "
            "대조하고, 어긋나면 갱신을 멈춘다(실측 차이 0.00000%).",
            "기준일은 랩 격자로 자른다 — 수집기가 하루이틀 더 받아 와도 그 뒤는 버린다.",
            "사후수익은 달력 +7일 / +30일. 신호가 난 날 종가에 사서 그날까지 든 것이다.",
        ):
            ST.tx(fig, X0 + .004, y, "· " + ln, fontsize=7.0, color=INK2)
            y -= .0135
        foot(fig, pg, asof)

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
