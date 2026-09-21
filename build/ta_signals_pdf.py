# -*- coding: utf-8 -*-
"""build/ta_signals_pdf.py — 교과서 TA 신호 검증 → data/ta_signals.pdf

자료는 build/ta_signals.py 가 낸 data/_ta_signals.json 하나뿐이다. 여기서 계산하지 않는다.

⚠ 맑은 고딕에 없는 글자: ✓ ✗ ⚠ 🚨 U+2212(진짜 빼기표). «!!» 와 하이픈으로 눕힌다.
  있는 글자: ▲ ▼ → ← · — ± ≥ ≤ « » ★ ∧

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

HOT = 10          # 이 안에 발동했으면 «최근» 으로 본다


def foot(fig, page, total, asof):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .026,
          "여두 전략 랩 · 교과서 TA 신호 검증 · 기준 %s · 10년 · 설계 출처 ta_lab "
          "(산식·발동조건만) · **자료는 이 랩 종가**" % asof, fontsize=6.4, color=MUTED)
    ST.tx(fig, X0, .0175,
          "!! 신호는 진단이지 예측이 아니다. 매도 신호는 **숏 진입 신호가 아니다** - "
          "어느 것도 사후 평균이 음수가 아니다(아래 표).", fontsize=6.0, color=NEG)
    ST.tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def sig_table(fig, y, rows, side):
    """매수/매도 한 표. 최근 발동한 줄은 날짜를 붉게."""
    buy = side == "buy"
    tr = []
    for x in rows:
        ex = x.get("fwd1m_excess") if buy else x.get("edge_vs_base")
        tr.append([x["signal"][:20], str(x["n"]),
                   "%+.2f%%" % x["fwd1w_mean"], "%.0f%%" % x["fwd1w_win"],
                   "%+.2f%%" % x["fwd1m_mean"], "%.0f%%" % x["fwd1m_win"],
                   "%+.2f%%p" % ex,
                   (x["last"] or "—"),
                   ("%d일" % x["days_ago"]) if x["days_ago"] is not None else "—",
                   "★" if x["on_now"] else ""])

    def cc(r, c, tr=tr, rows=rows):
        if c == 0:
            return INK
        if c == 6:
            return POS if not tr[r][6].startswith("-") else NEG
        if c in (7, 8):
            d = rows[r]["days_ago"]
            return NEG if (d is not None and d <= HOT) else MUTED
        if c == 9:
            return NEG
        return MUTED
    head = ["신호", "횟수", "1주", "승률", "1개월", "승률",
            "초과" if buy else "덜 오름", "최근 발동", "경과", ""]
    return ST.table(fig, X0, y, [.148, .046, .062, .050, .062, .050, .068, .086, .048, .026],
                    head, tr, row_h=.0163, fs=6.9, hfs=6.2, zebra=True,
                    aligns=["l", "r", "r", "r", "r", "r", "r", "l", "r", "c"], cell_color=cc)


def index_page(fig, R, asof, page, total):
    y = .958
    ST.tx(fig, X0, y, "%s — 교과서 TA 신호" % R["label"], fontsize=16, weight="bold")
    ST.tx(fig, X1, y, "기준 %s · %s~ · %d거래일"
          % (asof, R["start"], R["n_days"]), fontsize=7.4, color=MUTED, ha="right")
    y -= .026
    ST.hline(fig, X0, X1, y, RULE, .9)
    y -= .016

    # 지금 무엇이 켜졌나 — 이 쪽에서 제일 먼저 보는 것
    hot_b = [x for x in R["buy"] if x["days_ago"] is not None and x["days_ago"] <= HOT]
    hot_s = [x for x in R["sell"] if x["days_ago"] is not None and x["days_ago"] <= HOT]
    ST.box(fig, X0, y - .046, X1 - X0, .046, PANEL2, z=0)
    ST.tx(fig, X0 + .008, y - .010, "최근 %d일 안에 발동한 신호" % HOT,
          fontsize=9.5, weight="bold")
    f = lambda v: " · ".join("%s(%s)" % (x["signal"], x["last"]) for x in
                             sorted(v, key=lambda z: z["days_ago"])) or "없음"
    ST.tx(fig, X0 + .008, y - .024, "매수  " + f(hot_b)[:118], fontsize=7.0, color=POS)
    ST.tx(fig, X0 + .008, y - .036, "매도  " + f(hot_s)[:118], fontsize=7.0, color=NEG)
    y -= .058

    ST.tx(fig, X0, y, "매수 신호", fontsize=11, weight="bold", color=POS)
    ST.tx(fig, X0 + .090, y + .001,
          "초과 = 1개월 평균 - 기준선 %+.2f%% · 초과 순 · 굵은 날짜 = %d일 안"
          % (R["base1m"], HOT), fontsize=6.4, color=MUTED)
    y -= .0140
    rb = [x for x in R["buy"] if x.get("n", 0) >= 5]
    rb.sort(key=lambda x: -(x.get("fwd1m_excess") or -99))
    y = sig_table(fig, y, rb, "buy")
    thin = [x["signal"] for x in R["buy"] if x.get("n", 0) < 5]
    if thin:
        y -= .011
        ST.tx(fig, X0, y, "표본 5회 미만이라 통계 없음 — %s" % " · ".join(thin),
              fontsize=6.2, color=MUTED)
    y -= .022

    ST.tx(fig, X0, y, "매도 신호", fontsize=11, weight="bold", color=NEG)
    ST.tx(fig, X0 + .090, y + .001,
          "«덜 오름» = 기준선 - 1개월 평균. 양수면 기준선보다 **덜 올랐다**는 뜻이다",
          fontsize=6.4, color=MUTED)
    y -= .0140
    rs = [x for x in R["sell"] if x.get("n", 0) >= 5]
    rs.sort(key=lambda x: -(x.get("edge_vs_base") or -99))
    y = sig_table(fig, y, rs, "sell")
    thin = [x["signal"] for x in R["sell"] if x.get("n", 0) < 5]
    if thin:
        y -= .011
        ST.tx(fig, X0, y, "표본 5회 미만이라 통계 없음 — %s" % " · ".join(thin),
              fontsize=6.2, color=MUTED)
    y -= .016
    worst = min(rs, key=lambda x: x["fwd1m_mean"]) if rs else None
    if worst:
        ST.tx(fig, X0, y,
              "!! **매도 신호 %d종 전부 사후 1개월 평균이 양수다**(최저 %s %+.2f%%). "
              "숏 진입 신호가 아니라 «차익실현·신규매수 자제» 로만 읽을 것."
              % (len(rs), worst["signal"], worst["fwd1m_mean"]), fontsize=6.8, color=NEG)
    foot(fig, page, total, asof)


def main() -> int:
    M = json.load(io.open(os.path.join(DATA, "_ta_signals.json"), encoding="utf-8"))
    asof = M["as_of"]
    TOT = 3
    with PdfPages(OUT) as pdf:
        figs = []
        for i, k in enumerate(("spx", "ndx"), 1):
            fig = ST.new_page(); figs.append(fig)
            index_page(fig, M["index"][k], asof, i, TOT)

        # ── 3쪽 — 컨버전스 + 뺀 것 ────────────────────────────────────
        fig = ST.new_page(); figs.append(fig)
        y = .958
        ST.tx(fig, X0, y, "신호 합류 · 그리고 못 낸 것", fontsize=16, weight="bold")
        ST.tx(fig, X1, y, "기준 %s" % asof, fontsize=7.4, color=MUTED, ha="right")
        y -= .026
        ST.hline(fig, X0, X1, y, RULE, .9)
        y -= .018
        ST.tx(fig, X0, y,
              "원본 ta_lab 의 첫째 원칙이 «단일 지표 의존 금지» 다. 두 신호가 **5거래일 안에 같이** "
              "발동한 날만 세면 단독보다 낫다 — 그것을 이 랩 자료로 다시 쟀다.",
              fontsize=7.2, color=INK2)
        y -= .020
        for k, ko in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
            R = M["index"][k]
            cf = [x for x in R["confluence"] if x.get("n", 0) >= 5]
            cf.sort(key=lambda x: -(x.get("fwd1m_excess") or -99))
            # ⚠ .090 은 «S&P 500» 에는 맞았지만 «NASDAQ 100» 을 먹었다(렌더 실측).
            #   11pt 라틴 열 글자면 .13 이 넘는다 — 여유 두고 .150.
            ST.tx(fig, X0, y, ko, fontsize=11, weight="bold")
            ST.tx(fig, X0 + .150, y + .001, "기준선 %+.2f%%" % R["base1m"],
                  fontsize=6.6, color=MUTED)
            y -= .0135
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
            thin = [x["pair"] for x in R["confluence"] if x.get("n", 0) < 5]
            if thin:
                y -= .011
                # ⚠ 짝 이름을 다 적었더니 오른쪽으로 잘렸다(렌더 실측). 수만 적는다 —
                #   이름은 _ta_signals.json 에 다 있다.
                ST.tx(fig, X0, y,
                      "표본 5회 미만이라 통계 없음 — %d짝 (이름은 _ta_signals.json 에)"
                      % len(thin), fontsize=6.2, color=MUTED)
            y -= .022

        ST.tx(fig, X0, y, "못 낸 것 — 왜", fontsize=11, weight="bold", color=NEG)
        y -= .0150
        ST.tx(fig, X0, y,
              "이 랩의 지수 계열에는 **고가·저가·거래량이 없다**(bench_px 는 종가 5,210일). "
              "원본 37종 중 그것이 필요한 %d종을 **뺐다.**" % len(M["dropped"]),
              fontsize=7.2, color=INK2)
        y -= .0130
        ST.tx(fig, X0, y, "  " + " · ".join(M["dropped"][:12]), fontsize=6.8, color=MUTED)
        y -= .0115
        ST.tx(fig, X0, y, "  " + " · ".join(M["dropped"][12:]), fontsize=6.8, color=MUTED)
        y -= .0140
        # ⚠ 한 줄에 다 넣었더니 오른쪽으로 잘렸다(렌더 실측) — 두 줄로 나눈다.
        ST.tx(fig, X0, y,
              "!! 종가로 비슷하게 흉내 낸 변종을 **같은 이름으로 싣지 않는다.** "
              "이름이 같으면 같은 것이어야 한다.", fontsize=6.8, color=NEG)
        y -= .0115
        ST.tx(fig, X0, y,
              "   원본의 RSI 와 이 표의 RSI 는 같지만, 원본의 Keltner 를 종가로 만든 것은 "
              "Keltner 가 아니다.", fontsize=6.8, color=NEG)
        y -= .0240
        ST.tx(fig, X0, y, "이 표를 어떻게 읽나", fontsize=11, weight="bold")
        y -= .0150
        for ln, col in (
            ("· 신호는 **진단**이지 예측이 아니다. 원본 ta_lab 의 결론이고 이 랩의 결론과도 같다.", INK2),
            ("· **매도 신호는 숏이 아니다.** 양 지수 모두 매도 신호 전부가 사후 1개월 평균 양수다. "
             "«덜 올랐다»가 최선이다 - 차익실현·신규매수 자제로만 읽을 것.", NEG),
            ("· 횟수가 적은 줄(10~20회)은 **운으로 그 값이 나올 수 있다.** 초과 %p 크기보다 "
             "횟수를 먼저 볼 것.", MUTED),
            ("· 10년 한 구간이다. 이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했다 - "
             "신호 하나로 판을 바꾸지 않는다.", MUTED),
        ):
            ST.tx(fig, X0, y, ln, fontsize=6.9, color=col)
            y -= .0125
        foot(fig, 3, TOT, asof)

        for i, f in enumerate(figs, 1):
            pdf.savefig(f)
            if "--png" in sys.argv[1:]:
                f.savefig(os.path.join(DATA, "_ta_%d.png" % i), dpi=110, facecolor=PAPER)
            ST.plt.close(f)
        d = pdf.infodict()
        d["Title"] = "교과서 TA 신호 검증 · 기준 %s" % asof

    print("→ %s · 3쪽 · 기준 %s" % (OUT, asof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
