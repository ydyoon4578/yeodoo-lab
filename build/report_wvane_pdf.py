# -*- coding: utf-8 -*-
"""build/report_wvane_pdf.py — 풍향계 전략 보고서(입문자판) → build/REPORT-2026-08-20-WVANE.pdf

2026-08-20 사용자 지시로 전면 재작성: «아무것도 모르는 사람이라고 생각하고 쉽게,
자세하게, 스텝바이스텝». 수치는 얼린 측정(data/wvane.json)과 대조 가드로 일치 보장.

    python build/report_wvane_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import NullFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(HERE, "REPORT-2026-08-20-WVANE.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST
from style_top_pdf import tx, hline, box, table
from aegis_backtest import load_px, week_ends, Sig, metrics
from tilt_backtest import load_weights, alias_map
from aegis3_backtest import load_rf
import wvane_backtest as WV

ST.require_draw()
X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2
CHAMP, RP, MARG, GROUND = ST.CHAMP, ST.RP, ST.MARG, ST.GROUND
C_C, C_NR, C_B, C_R, C_BM = POS, MARG, ACC, MUTED, RP
TOTAL = 4


def footer(fig, page):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .027, "풍향계 전략 보고서(입문자판) · 모든 숫자는 사전등록 측정(PREREG-2026-08-20-WVANE · "
                      "규칙과 예상을 계산 전에 기록하고 고정)에서 그대로 옮겼습니다",
       fontsize=6.4, color=MUTED)
    tx(fig, X0, .019, "과거 시험(백테스트) 결과입니다 — 미래 수익을 약속하지 않으며, 실제 운용 기록은 아직 0건입니다",
       fontsize=6.0, color=NEG)
    tx(fig, X1, .027, "%d / %d · %s" % (page, TOTAL, dt.date.today().isoformat()),
       fontsize=6.4, color=MUTED, ha="right")


def new_page():
    return plt.figure(figsize=(8.27, 11.69))


def para(fig, x, y, lines, dy=.0145, fs=7.6, color=INK2):
    for j, s in enumerate(lines):
        tx(fig, x, y - j * dy, s, fontsize=fs, color=color)
    return y - len(lines) * dy


def main() -> int:
    J = json.load(io.open(os.path.join(DATA, "wvane.json"), encoding="utf-8"))
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    end = J["span"][1]
    dts_all, px, bench = load_px()
    n_keep = len([d for d in st["pxd_dates"] if d <= end])
    dts = dts_all[:n_keep]
    for t in px:
        px[t] = px[t][:n_keep]
    bench = {k: v[:n_keep] for k, v in bench.items()}
    W = load_weights()
    AL = alias_map()
    rf = load_rf()
    last_ym = max(rf)
    sig = Sig(px, len(dts))
    vsig = WV.RetSig(px, len(dts))
    bsig = Sig(bench, len(dts))
    we_idx = week_ends(dts)
    weeks, _sk = WV.build_weeks(dts, px, W, AL, we_idx, bsig)
    V = {m: WV.run(dts, px, weeks, sig, vsig, rf, last_ym, mode=m)
         for m in ("R", "B", "C", "NR")}
    m_c = metrics(V["C"]["daily_d"], V["C"]["dv"], V["C"]["wk"]["ret"])
    if abs(m_c["cagr"] - J["decomp"]["C"]["cagr"]) > .005:
        raise SystemExit("재계산이 정본과 어긋난다: %.2f vs %.2f"
                         % (m_c["cagr"], J["decomp"]["C"]["cagr"]))
    DD = V["C"]["daily_d"]
    XD = [dt.date.fromisoformat(d) for d in DD]
    d2i = {d: i for i, d in enumerate(dts)}
    ndx_ff, last = [], None
    for v in bench["ndx"]:
        if v is not None:
            last = v
        ndx_ff.append(last)
    ib0 = d2i[DD[0]]
    dv_bm = [100.0 * ndx_ff[d2i[d]] / ndx_ff[ib0] for d in DD]
    DEC = J["decomp"]
    mb = J["bench"]

    off_spans, s0 = [], None
    wkd = J["weekly"]["d"]; ons = J["weekly"]["on"]
    for d, on in zip(wkd, ons):
        if not on and s0 is None:
            s0 = d
        elif on and s0 is not None:
            off_spans.append((s0, d)); s0 = None
    if s0 is not None:
        off_spans.append((s0, wkd[-1]))

    with PdfPages(OUT) as pdf:
        # ── 1쪽 — 이 전략이 뭘 하는 건가요 ─────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "풍향계 (WEATHERVANE)", fontsize=17, fontweight="bold")
        tx(fig, X0, .932, "나스닥100 을 그대로 들고, 시장의 «날씨»에 따라 두 가지만 조절하는 전략",
           fontsize=10, color=INK2)
        tx(fig, X1, .955, "입문자판 · 2017-04 ~ 2026-08 과거 시험", fontsize=7.5, color=MUTED, ha="right")
        hline(fig, X0, X1, .922, RULE, 1.0)

        tx(fig, X0, .905, "한 문장으로", fontsize=10.5, fontweight="bold")
        box(fig, X0, .845, X1 - X0, .048, GROUND, ec=LINE, lw=.8)
        tx(fig, X0 + .012, .885, "나스닥100 에 든 100개 종목을 공식 비율대로 전부 사되, 매주 금요일에 ① 시장 날씨를 확인해",
           fontsize=8.4)
        tx(fig, X0 + .012, .868, "주식에 넣을 돈의 비율을 정하고(110% 또는 90%), ② 그 날씨에 맞는 종목을 «조금만 더» 삽니다.",
           fontsize=8.4)

        tx(fig, X0, .828, "먼저, 용어 6개만 알면 됩니다", fontsize=10.5, fontweight="bold")
        terms = [
            ["나스닥100", "미국 나스닥 시장의 대형주 100개를 모은 지수. 애플·마이크로소프트·엔비디아 같은 회사들입니다."],
            ["공식 비율(벤더 비중)", "지수 회사가 정해 둔 각 종목의 비율. 예: 애플 10%, 마이크로소프트 9%… 지수를 «그대로 산다»는 건 이 비율대로 산다는 뜻입니다."],
            ["200일선", "최근 200거래일(약 10개월) 종가의 평균값. 지수가 이 평균보다 위면 «상승 추세», 아래면 «하락 추세» — 장기 체온계입니다."],
            ["편입비", "내 돈 중 주식에 넣은 비율. 100%가 기본, 110%는 조금 빌려서 더 산 것, 90%는 10%를 현금으로 뺀 것입니다."],
            ["틸트(기울이기)", "공식 비율에서 조금만 벗어나는 것. 애플이 좋아 보이면 10% 대신 11%를 사는 식 — 확 바꾸는 게 아니라 «기울이는» 겁니다."],
            ["z-점수", "반에서 몇 등인지를 숫자로 바꾼 것. 100개 종목 중 딱 중간이면 0, 최상위권이면 +2, 최하위권이면 -2 근처가 됩니다."],
        ]
        table(fig, X0, .816, [.15, .69], ["용어", "뜻"], terms, row_h=.0300, fs=7.2, hfs=7.0,
              aligns=["l", "l"], zebra=True)

        tx(fig, X0, .590, "매주 금요일 장 마감 후, 이 순서대로 합니다", fontsize=10.5, fontweight="bold")
        steps = [
            ("STEP 1  날씨 확인", "나스닥100 지수가 자기 200일선 위에 있나요? 위면 «맑음(위험-온)», 아래면 «흐림(위험-오프)»입니다. 확인은 이것 하나뿐입니다."),
            ("STEP 2  돈의 양 결정", "맑음이면 편입비 110% (조금 빌려서 더 삽니다 — 이자는 실제 단기금리로 계산), 흐림이면 90% (10%는 현금으로 피신)."),
            ("STEP 3  종목 점수 매기기", "맑음일 땐 «모멘텀 점수»: 각 종목의 현재가가 자기 200일선보다 몇 % 위인가 — 추세가 좋은 종목이 높은 점수. 흐림일 땐 «저변동 점수»: 지난 1년 하루하루 가격이 얼마나 잔잔했나 — 얌전한 종목이 높은 점수."),
            ("STEP 4  비중 기울이기", "점수를 z-점수(등수)로 바꾸고, 공식 비율 × (1 + 0.3 × z) 로 조절합니다. 1등급(+2)이면 공식 비율의 1.6배, 꼴찌급(-2)이면 0.4배 — 어떤 종목도 빼거나 공매도하지 않습니다."),
            ("STEP 5  주문", "새 비율대로 사고팝니다. 거래비용은 사고판 금액의 0.05%(1만원 거래에 5원)로 계산에 넣었습니다."),
        ]
        yy = .572
        for tt, body in steps:
            tx(fig, X0, yy, tt, fontsize=8.6, fontweight="bold", color=CHAMP)
            yy = para(fig, X0 + .022, yy - .017, _wrap(body, 88), dy=.0135, fs=7.4) - .011
        yy -= .010
        tx(fig, X0, yy, "이게 전부입니다. 판단은 «200일선 위냐 아래냐» 하나, 조절은 «돈의 양»과 «종목 기울기» 둘.",
           fontsize=8.2, fontweight="bold", color=INK2)
        tx(fig, X0, yy - .022, "이 규칙과 «이렇게 나올 것»이라는 예상 5개를 시험 계산 전에 먼저 기록해 고정했습니다(사전등록) —",
           fontsize=7.4, color=MUTED)
        tx(fig, X0, yy - .036, "결과를 본 뒤 규칙을 슬쩍 바꾸는 것을 막기 위해서입니다. 결과는 3쪽에 있습니다.",
           fontsize=7.4, color=MUTED)
        footer(fig, 1)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 2쪽 — 예시로 따라가기 ─────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "예시로 따라가 봅시다", fontsize=13, fontweight="bold")
        tx(fig, X0, .934, "종목이 5개뿐인 가상의 지수라고 하겠습니다. (실제 공식 비율은 문서에 싣지 않는 계약이라 숫자는 가상입니다)",
           fontsize=7.6, color=MUTED)

        tx(fig, X0, .905, "어느 맑은 금요일 (지수가 200일선 위 → 모멘텀 점수 사용 · 편입비 110%)", fontsize=9.5, fontweight="bold")
        hdr = ["종목", "공식 비율", "상태", "z-점수(등수)", "x 배율", "기울인 비율"]
        ex = [["A", "30%", "추세 강함 (200일선보다 +25%)", "+1.5", "1.45", "36.9%"],
              ["B", "25%", "추세 조금 (+8%)", "+0.5", "1.15", "24.4%"],
              ["C", "20%", "평범 (딱 평균)", "0.0", "1.00", "17.0%"],
              ["D", "15%", "약세 (-5%)", "-1.0", "0.70", "8.9%"],
              ["E", "10%", "급락 후 (-20%)", "-2.0", "0.40", "3.4%"],
              ["합계", "100%", "", "", "", "100%"]]
        table(fig, X0, .893, [.08, .10, .28, .12, .08, .12], hdr, ex, row_h=.0185,
              fs=7.4, hfs=7.0, aligns=["l", "r", "l", "r", "r", "r"], zebra=True)
        yy = para(fig, X0, .750, [
            "· 읽는 법: A 는 추세 1등급이라 공식 30% 대신 36.9%를 삽니다. E 는 꼴찌급이라 10% 대신 3.4%만 삽니다.",
            "· «기울인 비율» 열의 합이 100%가 되도록 마지막에 전체를 한 번 눌러 맞춥니다 — 현금이 생기지 않습니다.",
            "· 그리고 편입비 110%: 위 비율로 산 주식이 내 돈의 110%가 되게 삽니다(10%는 단기금리로 빌림).",
        ], dy=.0148, fs=7.4)

        tx(fig, X0, .672, "몇 주 뒤, 지수가 200일선 아래로 (흐림 → 저변동 점수로 교체 · 편입비 90%)", fontsize=9.5, fontweight="bold")
        yy = para(fig, X0, .652, [
            "이번엔 점수의 «과목»이 바뀝니다. 추세가 아니라 «얼마나 잔잔한가»로 등수를 다시 매깁니다 —",
            "잔잔한 우량주(예: 코스트코 같은)가 1등급이 되어 공식 비율보다 많이 담기고, 출렁이는 종목은 줄입니다.",
            "동시에 주식을 내 돈의 90%로 줄여 10%는 현금으로 피신합니다. 지수가 다시 200일선 위로 올라오면",
            "과목을 모멘텀으로 되돌리고 110%로 복귀합니다. 이 «과목 교체»가 풍향계라는 이름의 이유입니다.",
        ], dy=.0148, fs=7.6)

        tx(fig, X0, .565, "얼마나 자주 바뀌었나요?", fontsize=9.5, fontweight="bold")
        yy = para(fig, X0, .545, [
            "9.4년(489주) 동안 맑음↔흐림 전환은 18번뿐입니다. 흐림이었던 기간은 전체의 18%(90주)로,",
            "대부분 2022년 약세장 한 해에 몰려 있습니다. 평상시 한 주의 매매 규모는 포트의 4% 정도,",
            "전환이 있는 주에만 27% 정도로 커집니다(과목이 통째로 바뀌니까요). 이 비용까지 전부 계산에 넣었습니다.",
        ], dy=.0148, fs=7.6)

        tx(fig, X0, .465, "잠깐 — 왜 «조금만» 기울이나요?", fontsize=9.5, fontweight="bold")
        yy = para(fig, X0, .445, [
            "점수가 좋다고 한 종목에 몰면 지수와 전혀 다른 물건이 되고, 예측이 틀렸을 때 크게 다칩니다.",
            "이 전략은 지수에서 최대 ±60%(비율 기준)까지만 벗어나게 설계돼, 무슨 일이 있어도 «나스닥100 과",
            "비슷하게 움직이되 조금 다른» 상태를 유지합니다. 실제로 지수와의 연간 차이(추적오차)는 2%p 안팎입니다.",
        ], dy=.0148, fs=7.6)

        tx(fig, X0, .360, "이 시험에서 지킨 안전장치들", fontsize=9.5, fontweight="bold")
        rows2 = [
            ["규칙 먼저, 계산 나중", "규칙·예상을 먼저 기록해 고정한 뒤 계산했습니다. 결과 보고 규칙을 바꾸는 «후출제»를 차단."],
            ["데이터 청소", "합병·상장폐지로 가격이 엉킨 종목(예: 상장 전 가격이 남아 있던 종목)은 점수 계산에서 자동 제외."],
            ["비용·이자 반영", "거래비용 0.05%, 110% 구간의 차입이자(실제 미국 단기금리), 90% 구간의 현금은 이자 0%로 보수적으로."],
            ["검산 장치", "«기울기를 끄면 지수 복제와 완전히 같아지는가» 같은 자기 검산 3종이 어긋나면 결과를 폐기하도록 설계."],
        ]
        table(fig, X0, .348, [.19, .65], ["장치", "내용"], rows2, row_h=.0255, fs=7.2, hfs=7.0,
              aligns=["l", "l"], zebra=True)
        footer(fig, 2)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 3쪽 — 결과 ────────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "결과 — 과거 9.4년으로 시험해 보니", fontsize=13, fontweight="bold")
        tx(fig, X0, .934, "«백테스트» = 과거 데이터에 규칙을 그대로 적용해 봤다면 어땠을까를 계산한 것. 미래 보장이 아닙니다.",
           fontsize=7.6, color=MUTED)

        tx(fig, X0, .908, "성적표 읽는 법: 연수익률 = 매년 평균 몇 % 불었나 · 샤프 = 위험(출렁임) 대비 수익 점수(높을수록 좋음) · "
                          "최대낙폭 = 최악의 순간 고점 대비 몇 %까지 빠졌었나", fontsize=7.0, color=INK2)
        hdr = ["", "연수익률", "샤프", "최대낙폭"]
        rows = [["나스닥100 그냥 사기", "%.1f%%" % mb["cagr"], "%.2f" % mb["sharpe"], "%.1f%%" % mb["mdd"]],
                ["풍향계", "%.1f%%" % DEC["C"]["cagr"], "%.2f" % DEC["C"]["sharpe"], "%.1f%%" % DEC["C"]["mdd"]]]
        table(fig, X0, .888, [.24, .12, .10, .12], hdr, rows, row_h=.019, fs=8.2, hfs=7.4,
              aligns=["l", "r", "r", "r"],
              cell_color=lambda r, c: (C_BM if r == 0 else C_C) if c == 0 else INK)
        tx(fig, X0, .820, "연 +4.3%p 좋아 보이지만 — 어디서 왔는지 층별로 뜯어 보는 게 이 보고서의 핵심입니다.",
           fontsize=8.0, fontweight="bold")

        # 계단 그림 — 층별 기여
        tx(fig, X0, .790, "층별 분해 — 한 층씩 쌓으며 연수익률이 어떻게 변했나", fontsize=9.5, fontweight="bold")
        ax = fig.add_axes([X0 + .02, .565, X1 - X0 - .06, .195])
        stages = [("지수\n(나스닥100)", mb["cagr"], C_BM),
                  ("+ 지수를 종목으로\n복제(배당 포함)", DEC["R"]["cagr"], C_R),
                  ("+ 편입비 밴드\n(110/90)", DEC["B"]["cagr"], C_B),
                  ("+ 모멘텀 틸트", DEC["NR"]["cagr"], C_NR),
                  ("+ 날씨따라 과목교체\n(= 풍향계)", DEC["C"]["cagr"], C_C)]
        xs = range(len(stages))
        for i2, (lab, v, col) in enumerate(stages):
            ax.bar(i2, v, .58, color=col, zorder=2)
            ax.text(i2, v + .25, "%.1f" % v, ha="center", fontsize=8.5, fontweight="bold")
            if i2 > 0:
                dv_ = v - stages[i2 - 1][1]
                ax.text(i2, v - 2.2, "%+.1f" % dv_, ha="center", fontsize=7.5,
                        color=("white"))
        ax.set_xticks(list(xs))
        ax.set_xticklabels([s[0] for s in stages], fontsize=6.8)
        ax.set_ylim(0, 27)
        ax.tick_params(axis="y", labelsize=7)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(LINE)
        ax.grid(axis="y", color=LINE, lw=.5, alpha=.7)
        ax.set_facecolor(PAPER)
        yy = para(fig, X0, .516, [
            "· 두 번째 층(+1.7)은 전략 실력이 아닙니다 — 지수는 배당을 빼고 계산되는데 실제 주식은 배당을 받는 몫(+0.8)과,",
            "  옛날에 사라진 종목 일부의 가격 자료가 없어 생기는 측정상의 유리함(+0.9)입니다. 정직하게 갈라 둡니다.",
            "· 편입비 밴드가 +1.5, 모멘텀 틸트가 +1.1 을 보탰습니다 — 이 둘이 진짜 일꾼입니다.",
            "· 마지막 층 «날씨따라 과목 교체»는 -0.02, 사실상 0 — 풍향계의 간판 아이디어가 아무것도 못 보탰습니다.",
        ], dy=.0148, fs=7.4)

        tx(fig, X0, .448, "누적 곡선 — 100 이 어떻게 됐나 (음영 = 흐림 구간 · 세로축 로그)", fontsize=9.5, fontweight="bold")
        ax2 = fig.add_axes([X0, .175, X1 - X0, .245])
        for vals, col, lab, lw in ((dv_bm, C_BM, "나스닥100 그냥 사기", .9),
                                   (V["NR"]["dv"], C_NR, "밴드+모멘텀틸트 (과목교체 없음)", 1.3),
                                   (V["C"]["dv"], C_C, "풍향계", 1.3)):
            base = vals[0]
            ax2.plot(XD, [v / base * 100 for v in vals], color=col, lw=lw, label=lab)
        for a, b in off_spans:
            ax2.axvspan(dt.date.fromisoformat(a), dt.date.fromisoformat(b), color=NEG, alpha=.06, lw=0)
        ax2.set_yscale("log")
        ax2.yaxis.set_minor_formatter(NullFormatter())
        ax2.set_yticks([100, 200, 400, 800])
        ax2.set_yticklabels(["100", "200", "400", "800"], fontsize=7)
        ax2.tick_params(axis="x", labelsize=7)
        for sp in ("top", "right"):
            ax2.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax2.spines[sp].set_color(LINE)
        ax2.grid(axis="y", color=LINE, lw=.5, alpha=.7)
        ax2.legend(loc="upper left", fontsize=7.4, frameon=False)
        ax2.set_facecolor(PAPER)
        tx(fig, X0, .148, "초록(풍향계)과 주황(과목교체 없는 판)이 거의 포개져 있습니다 — 과목 교체가 한 일이 없다는 것을",
           fontsize=7.2, color=INK2)
        tx(fig, X0, .135, "그림 하나가 보여 줍니다. 100 에서 출발해 약 7.6배가 된 것은 두 판이 같습니다.",
           fontsize=7.2, color=INK2)
        footer(fig, 3)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 4쪽 — 솔직한 주의사항과 결론 ──────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "솔직한 주의사항 — 이 숫자를 그대로 믿으면 안 되는 이유들", fontsize=13, fontweight="bold")
        cav = [
            ["백미러의 함정", "과거 9.4년은 나스닥100 의 황금기였습니다. 성장주 10년 침체가 오면 «나스닥100» 선택 자체가 벌을 받습니다."],
            ["우연일 가능성", "모멘텀 틸트 +1.1%p 는 «우연치고는 크다» 수준이지 확정 아님. 비슷한 시도를 다섯 번 했으니 더 의심하고 읽어야 합니다."],
            ["측정의 기울어짐", "+1.7%p(배당 + 자료 없는 종목 몫)는 지수 비교에서 저희 쪽에 유리합니다. 층별 비교에서는 상쇄됩니다."],
            ["빠른 폭락엔 무력", "200일선은 느린 신호 — 2020년 코로나(3주 -30%)는 그대로 맞습니다. 도운 것은 2022년의 긴 약세장입니다."],
            ["실전 기록 0건", "모든 숫자는 과거 시험입니다. 실전 기록 0건 — 지금부터 쌓일 주간 기록만이 진짜 성적표입니다."],
        ]
        table(fig, X0, .930, [.16, .68], ["함정", "내용"], cav, row_h=.030, fs=7.2, hfs=7.0,
              aligns=["l", "l"], zebra=True)

        tx(fig, X0, .715, "그래서 결론은?", fontsize=11, fontweight="bold")
        yy = para(fig, X0, .693, [
            "① 풍향계의 간판이었던 «날씨 따라 종목 과목을 갈아타기»는 시험에서 떨어졌습니다 (+0 — 3쪽 계단 그림).",
            "   이 결과는 시험 전에 기록해 둔 «떨어질 수도 있다»는 예상 시나리오 그대로이고, 학계의 회의론",
            "   (팩터 갈아타기는 대개 비용값을 못 한다 — Asness 2016)과도 일치합니다.",
            "② 살아남은 것은 두 층입니다: 편입비 밴드(+1.5%p — 길게 흘러내리는 약세장에서 낙폭을 줄임)와",
            "   모멘텀 틸트(+1.1%p — 추세 좋은 종목을 조금 더 드는 것). 이 둘만 남긴 단순한 판이",
            "   «밴드+모멘텀틸트»이고, 성적은 풍향계와 사실상 같으면서 구조는 더 단순합니다.",
            "③ 즉 이 보고서의 교훈: 복잡한 장식은 시험에서 떨어졌고, 단순한 두 층이 일을 다 했다.",
            "   최종 추천형은 «나스닥100 복제 + 200일선 밴드 + 모멘텀 틸트» 입니다.",
        ], dy=.0155, fs=7.8, color=INK)

        tx(fig, X0, .540, "한 장 요약", fontsize=10, fontweight="bold")
        summ = [
            ["뭘 사나", "나스닥100 전 종목, 공식 비율 기준"],
            ["매주 하는 일", "200일선 확인 → 편입비(110/90) → 종목 점수로 비율 기울이기 → 주문"],
            ["과거 시험 성적", "연 %.1f%% (지수 %.1f%%) · 최악 낙폭 %.1f%% (지수 %.1f%%)" %
             (DEC["C"]["cagr"], mb["cagr"], DEC["C"]["mdd"], mb["mdd"])],
            ["성적의 원천", "밴드 +1.5 · 모멘텀 틸트 +1.1 · 측정 기울어짐 +1.7(전략 아님) · 과목교체 0"],
            ["약점", "빠른 폭락 방어 불가 · 나스닥 장기 침체 시 무력 · 실전 기록 0건"],
            ["추천", "과목교체를 뺀 단순판(밴드+모멘텀틸트)으로 — 성적 같고 구조 단순"],
        ]
        table(fig, X0, .528, [.17, .67], ["항목", "내용"], summ, row_h=.0225, fs=7.4, hfs=7.0,
              aligns=["l", "l"], zebra=True)
        footer(fig, 4)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


def _wrap(s, width):
    out, cur = [], ""
    for word in s.split(" "):
        if len(cur) + len(word) + 1 > width:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        out.append(cur)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
