# -*- coding: utf-8 -*-
"""build/ta_signals_pdf.py — 교과서 TA 신호 검증 → data/ta_signals.pdf

자료는 build/ta_signals.py 가 낸 data/_ta_signals.json 하나뿐이다. 여기서 계산하지 않는다.

쪽 구성 — 지수마다 매수 한 쪽·매도 한 쪽(줄이 35·23 이라 한 쪽에 같이 못 넣는다) + 합류 한 쪽.

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
TOT = 5


def foot(fig, page, asof):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .026,
          "여두 전략 랩 · 교과서 TA 신호 검증 · 기준 %s · 10년 · 설계 출처 ta_lab "
          "(산식·발동조건만) · 자료는 이 랩 계열" % asof, fontsize=6.4, color=MUTED)
    ST.tx(fig, X0, .0175,
          "!! 신호는 진단이지 예측이 아니다. 매도 신호는 **숏 진입 신호가 아니다** - "
          "어느 것도 사후 1개월 평균이 음수가 아니다.", fontsize=6.0, color=NEG)
    ST.tx(fig, X1, .026, "%d / %d · %s" % (page, TOT, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def side_page(fig, R, side, asof, page):
    buy = side == "buy"
    ko = "매수" if buy else "매도"
    y = .958
    ST.tx(fig, X0, y, "%s — %s 신호" % (R["label"], ko), fontsize=15, weight="bold",
          color=POS if buy else NEG)
    ST.tx(fig, X1, y, "기준 %s · %s~ · %d거래일 · 기준선 %+.2f%%"
          % (asof, R["start"], R["n_days"], R["base1m"]), fontsize=7.2, color=MUTED, ha="right")
    y -= .026
    ST.hline(fig, X0, X1, y, RULE, .9)
    y -= .016

    hot = [x for x in R[side] if x["days_ago"] is not None and x["days_ago"] <= HOT]
    hot.sort(key=lambda z: z["days_ago"])
    # ⚠ 한 줄에 132자로 잘랐더니 11종 중 넷만 보였다(렌더 실측) — 세 줄까지 편다.
    #   여기가 이 쪽에서 **제일 먼저 보는 칸**이라 잘리면 안 된다.
    items = ["%s(%s)" % (x["signal"], x["last"]) for x in hot] or ["없음"]
    lines, cur = [], ""
    for it in items:
        nxt = (cur + " · " + it) if cur else it
        if len(nxt) > 126 and cur:
            lines.append(cur); cur = it
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    lines = lines[:3]
    bh = .014 + .0125 * len(lines)
    ST.box(fig, X0, y - bh, X1 - X0, bh, PANEL2, z=0)
    ST.tx(fig, X0 + .008, y - .010, "최근 %d일 안에 발동 — %d종" % (HOT, len(hot)),
          fontsize=9, weight="bold")
    for i, ln in enumerate(lines):
        ST.tx(fig, X0 + .008, y - .0235 - i * .0118, ln, fontsize=6.6,
              color=POS if buy else NEG)
    y -= bh + .012

    # 🚨 매수·매도 **같은 부호 규약**이다(사용자 지시 2026-09-22). 초과 = 사후 − 기준선.
    #   종전에 매도만 «덜 오름»(부호 뒤집기)이라 두 표를 나란히 보면 헷갈렸다.
    ST.tx(fig, X0, y,
          ("초과 = 1개월 평균 - 기준선. **높은 것부터**. «상태» 는 켜져 있는 모든 날을 "
           "센 것이라 횟수가 크다(중첩)." if buy else
           "초과 = 1개월 평균 - 기준선. **매수 표와 같은 부호**다. 매도 신호는 "
           "**음수일수록 제 몫을 한 것**이라 낮은 것부터 놓았다."),
          fontsize=6.6, color=MUTED)
    if not buy:
        # ⚠ 색은 **부호**를 따른다(두 표를 같은 규칙으로 읽게). 그래서 이 표에서는
        #   붉은 것이 제 몫을 한 것이다 — 색만 보고 «나쁘다» 로 읽지 않게 적어 둔다.
        y -= .0118
        ST.tx(fig, X0, y,
              "색은 부호를 따른다(두 표를 같은 규칙으로) — **이 표에서는 붉은 쪽이 "
              "제 몫을 한 것**이다.", fontsize=6.6, color=MUTED)
    y -= .0150

    rows = [x for x in R[side] if x.get("n", 0) >= 5]
    rows.sort(key=lambda x: (x.get("fwd1m_excess") or 0), reverse=buy)
    tr = []
    for x in rows:
        tr.append([x["signal"][:21], "상태" if x["kind"] == "state" else "",
                   str(x["n"]), "%+.2f%%" % x["fwd1w_mean"], "%.0f%%" % x["fwd1w_win"],
                   "%+.2f%%" % x["fwd1m_mean"], "%.0f%%" % x["fwd1m_win"],
                   "%+.2f%%p" % x["fwd1m_excess"], (x["last"] or "—"),
                   ("%d일" % x["days_ago"]) if x["days_ago"] is not None else "—",
                   "★" if x["on_now"] else ""])

    def cc(r, c, tr=tr, rows=rows):
        if c == 0:
            return INK
        if c == 7:
            return POS if not tr[r][7].startswith("-") else NEG
        if c in (8, 9):
            d = rows[r]["days_ago"]
            return NEG if (d is not None and d <= HOT) else MUTED
        if c == 10:
            return NEG
        return MUTED
    y = ST.table(fig, X0, y,
                 [.152, .034, .046, .060, .048, .060, .050, .066, .084, .046, .024],
                 ["신호", "", "횟수", "1주", "승률", "1개월", "승률",
                  "초과", "최근 발동", "경과", ""], tr,
                 row_h=.0158, fs=6.8, hfs=6.1, zebra=True,
                 aligns=["l", "c", "r", "r", "r", "r", "r", "r", "l", "r", "c"],
                 cell_color=cc)
    thin = [x["signal"] for x in R[side] if x.get("n", 0) < 5]
    if thin:
        y -= .012
        ST.tx(fig, X0, y, "표본 5회 미만이라 통계 없음 — %s" % " · ".join(thin),
              fontsize=6.2, color=MUTED)
    if not buy:
        y -= .016
        worst = min(rows, key=lambda x: x["fwd1m_mean"])
        neg = sum(1 for x in rows if x["fwd1m_excess"] < 0)
        ST.tx(fig, X0, y,
              "!! 초과가 음수인 것은 %d/%d 종뿐이고, **사후 1개월 평균이 음수인 것은 하나도 "
              "없다**(최저 %s %+.2f%%)." % (neg, len(rows), worst["signal"], worst["fwd1m_mean"]),
              fontsize=6.8, color=NEG)
        y -= .0118
        ST.tx(fig, X0, y,
              "   숏 진입 신호가 아니라 «차익실현·신규매수 자제» 로만 읽을 것. "
              "원본 ta_lab 의 결론과 같다.", fontsize=6.8, color=NEG)
        dn = [x for x in rows if x.get("fwd1m_down") is not None]
        if dn:
            best = max(dn, key=lambda x: x["fwd1m_down"])
            y -= .0118
            ST.tx(fig, X0, y,
                  "   하락 적중이 가장 높은 것도 **%s %.0f%%** 다 - 절반을 못 넘는다."
                  % (best["signal"], best["fwd1m_down"]), fontsize=6.8, color=MUTED)
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

        # ── 마지막 쪽 — 합류 + 읽는 법 ────────────────────────────────
        pg += 1
        fig = ST.new_page(); figs.append(fig)
        y = .958
        ST.tx(fig, X0, y, "신호 합류 · 이 표를 어떻게 읽나", fontsize=15, weight="bold")
        ST.tx(fig, X1, y, "기준 %s" % asof, fontsize=7.4, color=MUTED, ha="right")
        y -= .026
        ST.hline(fig, X0, X1, y, RULE, .9)
        y -= .018
        ST.tx(fig, X0, y,
              "원본 ta_lab 의 첫째 원칙이 «단일 지표 의존 금지» 다. 두 신호가 **5거래일 안에 "
              "같이** 발동한 날만 세면 단독보다 낫다 — 그것을 이 랩 자료로 다시 쟀다.",
              fontsize=7.2, color=INK2)
        y -= .022
        for k, ko in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
            R = M["index"][k]
            cf = [x for x in R["confluence"] if x.get("n", 0) >= 5]
            cf.sort(key=lambda x: -(x.get("fwd1m_excess") or -99))
            ST.tx(fig, X0, y, ko, fontsize=11, weight="bold")
            ST.tx(fig, X0 + .150, y + .001, "기준선 %+.2f%%" % R["base1m"],
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
                ST.tx(fig, X0, y,
                      "표본 5회 미만이라 통계 없음 — %d짝 (이름은 _ta_signals.json 에)"
                      % len(thin), fontsize=6.2, color=MUTED)
            y -= .022

        ST.tx(fig, X0, y, "자료", fontsize=11, weight="bold")
        y -= .0150
        ST.tx(fig, X0, y, "· " + M["src"], fontsize=6.9, color=INK2)
        y -= .0125
        ST.tx(fig, X0, y,
              "· 고가·저가·거래량은 **따로 받는다**(build/bench_ohlc.py → bench_ohlc.json). "
              "종가는 bench_px 와 대조해 **0.00000%% 차이**를 확인했고, 어긋나면 갱신을 멈춘다 -",
              fontsize=6.9, color=INK2)
        y -= .0115
        ST.tx(fig, X0, y, "  벤치마크 잣대가 둘로 갈리지 않게.", fontsize=6.9, color=INK2)
        y -= .0125
        ST.tx(fig, X0, y,
              "· 기준일은 **랩 격자(bench_px)로 자른다.** 수집기가 하루이틀 더 받아 와도 "
              "그 뒤는 버린다 - 안 그러면 «최근 발동일» 이 다른 화면과 어긋난다.",
              fontsize=6.9, color=INK2)
        y -= .0240
        ST.tx(fig, X0, y, "이 표를 어떻게 읽나", fontsize=11, weight="bold")
        y -= .0150
        for ln, col in (
            ("· 신호는 **진단**이지 예측이 아니다. 원본 ta_lab 의 결론이고 이 랩의 결론과도 같다.", INK2),
            ("· **초과는 매수·매도 같은 부호다**(사후 - 기준선). 매도 신호는 **음수일수록 "
             "제 몫을 한 것**이다 - 그래서 매도 표는 낮은 것부터 놓았다.", INK2),
            ("· **매도 신호는 숏이 아니다.** 양 지수 모두 매도 신호 중 사후 1개월 평균이 "
             "음수인 것은 **하나도 없다**. «기준선보다 덜 올랐다»가 최선이다.", NEG),
            ("· **Donchian 하단 이탈은 오히려 매수 쪽이다** - SPX 초과 **+1.71%p**. "
             "이름이 매도 묶음에 있다고 매도 신호가 아니다.", NEG),
            ("· 횟수가 적은 줄(10~20회)은 **운으로 그 값이 나올 수 있다.** 초과 %p 크기보다 "
             "횟수를 먼저 볼 것.", MUTED),
            ("· «상태» 줄은 켜져 있는 **모든 날**을 센 것이라 횟수가 1,500~2,500 이다. "
             "이벤트 줄과 같은 무게로 읽으면 안 된다 - 관측이 겹친다.", MUTED),
            ("· 10년 한 구간이다. 이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했다 - "
             "신호 하나로 판을 바꾸지 않는다.", MUTED),
        ):
            ST.tx(fig, X0, y, ln, fontsize=6.9, color=col)
            y -= .0125
        foot(fig, pg, asof)

        for i, f in enumerate(figs, 1):
            pdf.savefig(f)
            if "--png" in sys.argv[1:]:
                f.savefig(os.path.join(DATA, "_ta_%d.png" % i), dpi=110, facecolor=PAPER)
            ST.plt.close(f)
        d = pdf.infodict()
        d["Title"] = "교과서 TA 신호 검증 · 기준 %s" % asof

    print("→ %s · %d쪽 · 기준 %s" % (OUT, TOT, asof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
