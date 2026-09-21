# -*- coding: utf-8 -*-
"""build/monitor_pdf.py — 시장 국면 모니터 → data/monitor.pdf

자료는 build/monitor.py 가 낸 data/_monitor.json 하나뿐이다. 여기서 아무것도 계산하지 않는다.

⚠ 맑은 고딕에 없는 글자: ✓ ✗ ⚠ 🚨 U+2212(진짜 빼기표). «!!» 와 하이픈으로 눕힌다.
  있는 글자: ▲ ▼ → ← · — ± ≥ ≤ « »

  python build/monitor_pdf.py [--png]
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["axes.unicode_minus"] = False   # 축 음수 U+2212 두부 방지
from matplotlib.backends.backend_pdf import PdfPages   # noqa: E402

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "monitor.pdf")
sys.path.insert(0, HERE)
import style_top_pdf as ST                                        # noqa: E402

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2

NUM = lambda v, d=2, p=False: ("—" if v is None else
                               ("%+.*f%%" % (d, v) if p else "%.*f" % (d, v)))


def foot(fig, page, total, asof):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .026,
          "여두 전략 랩 시장 국면 모니터 · 기준 %s · 설계 출처는 사용자 제공 「시장 국면 "
          "모니터」(2026-07-09) · **자료는 이 랩 것만 썼다**" % asof, fontsize=6.4, color=MUTED)
    ST.tx(fig, X0, .0175,
          "!! 이 모니터는 새 주장을 만들지 않는다 - 판정이 붙은 것을 옮기고, 사실을 적고, "
          "지난달 기록을 센다. 안 선 것은 마지막 칸에 같이 적는다.", fontsize=6.0, color=NEG)
    ST.tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def main() -> int:
    M = json.load(io.open(os.path.join(DATA, "_monitor.json"), encoding="utf-8"))
    s1, s2, s3, s4, s5 = M["s1"], M["s2"], M["s3"], M["s4"], M["s5"]
    TOT = 2

    with PdfPages(OUT) as pdf:
        # ═══ 1쪽 — ① 종합 + ② 지금 시장 ═══════════════════════════════
        fig = ST.new_page()
        y = .958
        ST.tx(fig, X0, y, "시장 국면 모니터", fontsize=21, weight="bold")
        ST.tx(fig, X1, y, "기준 %s · S&P %.0f" % (M["as_of"], M["spx"] or 0),
              fontsize=7.4, color=MUTED, ha="right")
        y -= .030
        ST.hline(fig, X0, X1, y, RULE, .9)
        y -= .018

        # ① 종합 점수
        ST.tx(fig, X0, y, "① 종합 Risk-On/Off", fontsize=13, weight="bold")
        y -= .030
        bc = NEG if "Off" in s1["band"] else (POS if "On" in s1["band"] else ACC)
        ST.tx(fig, X0, y, "%.1f" % s1["score"], fontsize=30, weight="bold", color=bc)
        # ⚠ 밴드(15pt)와 5일변화(8.5pt)를 .006/-.008 로 뒀더니 닿았다(렌더 실측) — 더 뗀다.
        ST.tx(fig, X0 + .125, y + .009, s1["band"], fontsize=15, weight="bold", color=bc)
        dc = NEG if (s1["d5"] or 0) <= -2 else (POS if (s1["d5"] or 0) >= 2 else MUTED)
        ST.tx(fig, X0 + .125, y - .009,
              "5거래일 변화 %+.1f  %s" % (s1["d5"] or 0, s1["trend"]),
              fontsize=8.5, weight="bold", color=dc)
        ST.tx(fig, X0 + .125, y - .020,
              ">=68 Risk-On · 60~67 준Risk-On · 50~59 중립 · 40~49 준Risk-Off · <40 Risk-Off",
              fontsize=6.2, color=MUTED)
        y -= .040

        KO = {"trend": "추세·모멘텀", "vol": "변동성 안정도", "breadth": "시장 폭",
              "macro": "매크로·신용", "sector": "섹터 리더십"}
        gr = [[KO[k], "%.1f" % s1["groups"][k], "%d%%" % s1["weights"][k]]
              for k in ("trend", "vol", "breadth", "macro", "sector")]
        gr.append(["심리", "—", "10% (자료 없음 · 뺐다)"])

        def cg(r, c, gr=gr):
            if c == 1 and gr[r][1] != "—":
                v = float(gr[r][1])
                return NEG if v < 35 else (POS if v > 65 else INK)
            return INK if c == 0 else MUTED
        y = ST.table(fig, X0, y, [.150, .075, .200], ["신호군", "점수", "가중"], gr,
                     row_h=.0165, fs=7.4, hfs=6.6, aligns=["l", "r", "l"], cell_color=cg)
        y -= .014
        b = s1.get("breadth_now") or {}
        if b:
            ST.tx(fig, X0, y,
                  "시장 폭 **7.4** 가 무엇으로 만들어졌나 — 종목 %d개 중 "
                  "**200일선 위 %.0f%%** · 50일선 위 **%.0f%%** · 20일 전보다 오른 종목 "
                  "**%.0f%%** · 52주 신고-신저 **%+.1f%%p**"
                  % (b["n"], b["a200"], b["a50"], b["up20"], b["nhnl"]),
                  fontsize=7.0, color=INK2)
            y -= .0130
            ST.tx(fig, X0, y,
                  "지수는 버티는데 **종목 넷 중 셋이 20일 전보다 아래**입니다. "
                  "신고가보다 신저가가 많습니다.", fontsize=7.0, color=NEG)
            y -= .020

        # ② 지금 시장
        ST.tx(fig, X0, y, "② 지금 시장", fontsize=13, weight="bold")
        ST.tx(fig, X0 + .180, y + .002, "실제 값입니다 - 국면 이름이 아닙니다",
              fontsize=6.6, color=MUTED)
        y -= .020

        def perf_rows(lst):
            return [[r["ko"], NUM(r["1m"], 2, True), NUM(r["3m"], 2, True),
                     NUM(r["12m"], 2, True)] for r in lst]

        def cp(r, c, rows=None):
            if c == 0:
                return INK
            v = rows[r][c]
            return MUTED if v == "—" else (NEG if v.startswith("-") else POS)
        ir = perf_rows(s2["index"])
        ST.tx(fig, X0, y, "지수·스타일", fontsize=9, weight="bold")
        y -= .0125
        y = ST.table(fig, X0, y, [.150, .090, .090, .090], ["", "1개월", "3개월", "12개월"],
                     ir, row_h=.0155, fs=7.2, hfs=6.4, aligns=["l", "r", "r", "r"],
                     cell_color=lambda r, c: cp(r, c, ir))
        y -= .012
        ST.tx(fig, X0, y,
              "**시가총액 가중이 동일가중을 1개월 %+.2f%%p 앞섭니다.** 소수 대형주가 지수를 "
              "떠받치고 있다는 뜻입니다."
              % ((s2["index"][0]["1m"] or 0) - (s2["index"][2]["1m"] or 0)),
              fontsize=7.0, color=NEG)
        y -= .020

        br = perf_rows(s2["bond"])
        ST.tx(fig, X0, y, "채권·금·달러", fontsize=9, weight="bold")
        y -= .0125
        y = ST.table(fig, X0, y, [.150, .090, .090, .090], ["", "1개월", "3개월", "12개월"],
                     br, row_h=.0155, fs=7.2, hfs=6.4, aligns=["l", "r", "r", "r"],
                     cell_color=lambda r, c: cp(r, c, br))
        y -= .020

        mr = [[m["ko"], "%.2f%s" % (m["now"], m["unit"]), NUM(m["d1m"], 2, True),
               NUM(m["d3m"], 2, True), "%.0f%%" % (m["pct"] or 0)] for m in s2["macro"]]

        def cm(r, c, mr=mr, mm=s2["macro"]):
            if c == 4:
                p = mm[r]["pct"] or 50
                return NEG if (p >= 90 or p <= 10) else MUTED
            if c in (2, 3):
                return MUTED if mr[r][c] == "—" else (NEG if mr[r][c].startswith("-") else POS)
            return INK if c == 0 else INK2
        ST.tx(fig, X0, y, "금리·신용·달러·변동성", fontsize=9, weight="bold")
        ST.tx(fig, X0 + .190, y + .001,
              "«역사» = 그 계열 전 기간에서 지금 값의 자리. 90%↑ 나 10%↓ 는 붉게 칠했습니다",
              fontsize=6.4, color=MUTED)
        y -= .0125
        y = ST.table(fig, X0, y, [.170, .090, .080, .080, .070],
                     ["", "지금", "1개월", "3개월", "역사"], mr,
                     row_h=.0155, fs=7.2, hfs=6.4, zebra=True,
                     aligns=["l", "r", "r", "r", "r"], cell_color=cm)
        y -= .014
        rl = next((m for m in s2["macro"] if m["code"] == "DFII10"), None)
        cr = next((m for m in s2["macro"] if m["code"] == "BAA10Y"), None)
        if rl and cr:
            ST.tx(fig, X0, y,
                  "!! **이 조합이 눈에 띕니다** - 실질금리는 역사 **%.0f%%**(거의 최고)인데 "
                  "회사채 가산은 역사 **%.0f%%**(거의 최저)입니다."
                  % (rl["pct"], cr["pct"]), fontsize=7.2, color=NEG)
            y -= .0130
            ST.tx(fig, X0, y,
                  "채권시장은 «돈이 빡빡하다»고 말하는데 신용시장은 «아무 스트레스 없다»고 "
                  "말합니다. 둘 중 하나는 틀렸거나, 아직 안 만났습니다.",
                  fontsize=7.0, color=INK2)
            y -= .018

        foot(fig, 1, TOT, M["as_of"])
        pdf.savefig(fig)
        if "--png" in sys.argv:
            fig.savefig(os.path.join(DATA, "_mon1.png"), dpi=110, facecolor=PAPER)
        ST.plt.close(fig)

        # ═══ 2쪽 — ③ 플래그 · ④ 온도계 · ⑤ 칸 · ⑥ 안 선 것 ═════════════
        fig = ST.new_page()
        y = .958
        ST.tx(fig, X0, y, "시장 국면 모니터 (이어서)", fontsize=15, weight="bold")
        ST.tx(fig, X1, y, "기준 %s" % M["as_of"], fontsize=7.4, color=MUTED, ha="right")
        y -= .030

        sr = [[r["ko"], r["grp"], NUM(r["1m"], 2, True), NUM(r["3m"], 2, True)]
              for r in sorted(s2["sector"], key=lambda x: -(x["1m"] if x["1m"] is not None else -99))]
        ST.tx(fig, X0, y, "섹터", fontsize=9, weight="bold")
        ST.tx(fig, X0 + .070, y + .001,
              "경기민감 %+.2f%% vs 방어 %+.2f%% (1개월 평균)"
              % (s2["cyc_1m"] or 0, s2["def_1m"] or 0), fontsize=6.6, color=MUTED)
        y -= .0125
        y = ST.table(fig, X0, y, [.130, .080, .085, .085], ["", "", "1개월", "3개월"], sr,
                     row_h=.0150, fs=7.0, hfs=6.4, zebra=True,
                     aligns=["l", "l", "r", "r"],
                     cell_color=lambda r, c: (INK if c == 0 else MUTED if c == 1 else
                                              (NEG if sr[r][c].startswith("-") else POS)))
        y -= .020
        nON = sum(1 for f in s3["flags"] if f["now"] == "ON")
        nW = sum(1 for f in s3["flags"] if f["now"] == "주의")
        ST.tx(fig, X0, y, "③ 극단 플래그 감시", fontsize=13, weight="bold")
        ST.tx(fig, X0 + .250, y + .002, "ON %d · 주의 %d / %d개"
              % (nON, nW, len(s3["flags"])), fontsize=7.4, color=(NEG if nON else MUTED))
        y -= .018
        bb = s3["base"]
        ST.tx(fig, X0, y,
              "기준선 - 아무 날이나 사서 1개월 들면 %+.2f%% · 승률 %.0f%% (n=%d). "
              "«기준선차» 가 그것을 뺀 값입니다."
              % (bb["fwd_mean"], bb["win"], bb["n"]), fontsize=6.8, color=MUTED)
        y -= .016
        fr = []
        for f in s3["flags"]:
            o = f["ON"]
            fr.append([f["ko"], f["now"], (f["value"] or "")[:22],
                       "—" if o["fwd_mean"] is None else "%+.2f%%" % o["fwd_mean"],
                       "—" if o["win"] is None else "%.0f%%" % o["win"],
                       "—" if o["lift"] is None else "%+.2f%%p" % o["lift"], str(o["n"])])

        def cf(r, c, fr=fr):
            if c == 1:
                return NEG if fr[r][1] == "ON" else (ACC if fr[r][1] == "주의" else MUTED)
            if c == 5 and fr[r][5] != "—":
                return POS if not fr[r][5].startswith("-") else NEG
            return INK if c == 0 else MUTED
        y = ST.table(fig, X0, y, [.155, .050, .140, .080, .058, .080, .050],
                     ["플래그", "상태", "현재값", "ON 1개월", "승률", "기준선차", "횟수"], fr,
                     row_h=.0165, fs=7.0, hfs=6.3, zebra=True,
                     aligns=["l", "c", "l", "r", "r", "r", "r"], cell_color=cf)
        y -= .013
        ST.tx(fig, X0, y,
              "!! 매매 규칙이 아니라 **감시판**입니다. 플래그가 켜졌다고 사는 것이 아니라 "
              "«지금 무엇이 극단인가»를 봅니다. 자료가 없는 %d개는 뺐습니다."
              % len(s3.get("dropped") or []), fontsize=6.6, color=NEG)
        y -= .022

        ST.tx(fig, X0, y, "④ 랩 전략 온도계", fontsize=13, weight="bold")
        ST.tx(fig, X0 + .225, y + .002,
              "게시 전략 중 S&P 500 을 이긴 비율 · 완전한 달만 · %s 까지" % s4["last_full"],
              fontsize=6.8, color=MUTED)
        y -= .020
        tr = []
        KOH = {"1m": "최근 1개월", "3m": "최근 3개월", "12m": "최근 12개월"}
        for hz in ("1m", "3m", "12m"):
            t = s4["temp"][hz]
            tr.append([KOH[hz], "%d / %d" % (t["beat"], t["n"]), "%.0f%%" % (t["pct"] or 0)])
        y = ST.table(fig, X0, y, [.130, .100, .080], ["", "이긴 전략", "비율"], tr,
                     row_h=.0165, fs=7.4, hfs=6.4, aligns=["l", "r", "r"],
                     cell_color=lambda r, c: (INK if c == 0 else MUTED if c == 1 else
                                              (POS if float(tr[r][2][:-1]) >= 50 else NEG)))
        y -= .014
        rr = sorted(s4["by_role"]["1m"].items(), key=lambda x: -x[1]["pct"])
        rrow = [[r, "%d / %d" % (v["beat"], v["n"]), "%.0f%%" % v["pct"]] for r, v in rr]
        ST.tx(fig, X0, y, "1개월 역할별", fontsize=9, weight="bold")
        y -= .0125
        y = ST.table(fig, X0, y, [.130, .100, .080], ["역할", "이긴 전략", "비율"], rrow,
                     row_h=.0158, fs=7.2, hfs=6.4, aligns=["l", "r", "r"],
                     cell_color=lambda r, c: (INK if c == 0 else MUTED if c == 1 else
                                              (POS if float(rrow[r][2][:-1]) >= 50 else NEG)))
        y -= .013
        ST.tx(fig, X0, y,
              "!! 이것은 **지난달에 이런 일이 있었다**이지 다음 달 예측이 아닙니다. "
              "이 랩은 이달 순위와 다음 달 순위의 상관이 **+0.05** 라고 쟀습니다.",
              fontsize=6.6, color=NEG)
        y -= .022

        ST.tx(fig, X0, y, "⑤ 국면 15칸에서 지금 칸", fontsize=13, weight="bold")
        y -= .020
        cell = s5.get("stat") or {}
        ST.tx(fig, X0, y, s5["cell"], fontsize=15, weight="bold", color=ACC)
        if cell.get("n"):
            ST.tx(fig, X0 + .250, y + .002,
                  "역사적으로 이 칸의 다음 달 **%+.2f%%** (%d일 · 기준선 %+.2f%%)"
                  % (cell["mean"], cell["n"], s5["base_mean"]), fontsize=8, color=INK2)
        y -= .020
        ST.tx(fig, X0, y, "!! " + s5["note"], fontsize=6.8, color=NEG)
        y -= .024

        ST.tx(fig, X0, y, "⑥ 이 랩이 «안 선다»고 잰 것", fontsize=13, weight="bold")
        ST.tx(fig, X0 + .420, y + .002,
              "이 칸이 없으면 위의 다섯 칸이 예언으로 읽힙니다", fontsize=6.8, color=NEG)
        y -= .020
        lr = [[x["무엇"], x["판정"], x["잰 것"][:74]] for x in M["s6"]]
        y = ST.table(fig, X0, y, [.185, .105, .590], ["무엇", "판정", "잰 것"], lr,
                     row_h=.0180, fs=6.8, hfs=6.3, zebra=True,
                     aligns=["l", "l", "l"],
                     cell_color=lambda r, c: (INK if c == 0 else
                                              NEG if c == 1 else MUTED))
        foot(fig, 2, TOT, M["as_of"])
        pdf.savefig(fig)
        if "--png" in sys.argv:
            fig.savefig(os.path.join(DATA, "_mon2.png"), dpi=110, facecolor=PAPER)
        ST.plt.close(fig)

    print("기준 %s · 종합 %.1f %s · 플래그 ON %d · 전략 온도계 1개월 %.0f%%"
          % (M["as_of"], s1["score"], s1["band"], nON, s4["temp"]["1m"]["pct"]))
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
