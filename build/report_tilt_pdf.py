# -*- coding: utf-8 -*-
"""build/report_tilt_pdf.py — 틸트 전략 설명서 → build/REPORT-2026-08-20-TILT.pdf

얼린 측정(data/tilt.json · PREREG-2026-08-20-TILT)의 설명 문서다. 곡선은 엔진
재실행(결정적 · 비중 캐시 필요)으로 그리되 정본과 어긋나면 빌드가 죽는다(대조 가드).
🚨 종목별 벤더 비중은 문서에 싣지 않는다(커밋 금지 규약) — 예시는 가상 숫자다.

    python build/report_tilt_pdf.py
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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(HERE, "REPORT-2026-08-20-TILT.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST
from style_top_pdf import tx, hline, box, table
from aegis_backtest import week_ends, Sig, metrics, bench_track
import tilt_backtest as TB

ST.require_draw()
X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2
CHAMP, RP, MARG, GROUND = ST.CHAMP, ST.RP, ST.MARG, ST.GROUND
C_T, C_R, C_B = ST.POS, ST.ACC, ST.RP        # 틸트 · 복제 · ^NDX
TOTAL = 4


def footer(fig, page):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .027, "틸트 전략 설명서 · 사전등록 PREREG-2026-08-20-TILT(계산 전 커밋) · "
                      "기준 비중은 벤더 정본(DB · 원자료 커밋 금지) · 비용 편도 5bp x 실회전",
       fontsize=6.4, color=MUTED)
    tx(fig, X0, .019, "구간 2017-04~ (그 이전은 편출종목 가격 탈락 10~15%로 재현 불가) · "
                      "탈락비중 평균 2.5%는 생존편향 채널 — 본문 분해표 참조 · 전방 기록 0건",
       fontsize=6.0, color=NEG)
    tx(fig, X1, .027, "%d / %d · %s" % (page, TOTAL, dt.date.today().isoformat()),
       fontsize=6.4, color=MUTED, ha="right")


def new_page():
    return plt.figure(figsize=(8.27, 11.69))


def main() -> int:
    J = json.load(io.open(os.path.join(DATA, "tilt.json"), encoding="utf-8"))
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    end = J["span"][1]
    dts = [d for d in st["pxd_dates"] if d <= end]
    # 가격·비중·엔진 — tilt_backtest 그대로(결정적)
    sys.argv = [sys.argv[0]]
    from aegis_backtest import load_px
    dts_full, px, bench = load_px()
    dts_full = dts_full[:len(dts)]
    for t in px:
        px[t] = px[t][:len(dts)]
    bench = {k: v[:len(dts)] for k, v in bench.items()}
    W = TB.load_weights()
    AL = TB.alias_map()
    sig = Sig(px, len(dts))
    we_idx = week_ends(dts)
    daily_d, dv_t, dv_r, wk = TB.run(dts, px, sig, W, AL, we_idx)
    m_t = metrics(daily_d, dv_t, wk["rt"])
    if abs(m_t["cagr"] - J["strat"]["cagr"]) > .005:
        raise SystemExit("재계산이 정본과 어긋난다: %.2f vs %.2f" % (m_t["cagr"], J["strat"]["cagr"]))
    m_r = metrics(daily_d, dv_r, wk["rr"])
    ndx_ff, last = [], None
    for v in bench["ndx"]:
        if v is not None:
            last = v
        ndx_ff.append(last)
    dd_b, dv_b, _ = bench_track(dts, {"ndx": ndx_ff}, "ndx", daily_d, we_idx)
    m_b = dict(J["bench"])
    XD = [dt.date.fromisoformat(d) for d in daily_d]
    A = J["active"]; RC = J["replica_check"]; G = J["gates"]

    with PdfPages(OUT) as pdf:
        # ── 1쪽 — 표지·요약 ────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "틸트 (TILT)", fontsize=17, fontweight="bold")
        tx(fig, X0, .932, "나스닥100 종목별 비중 틸팅 — 지수를 들고, 추세가 좋은 종목만 조금 더 든다",
           fontsize=10, color=INK2)
        tx(fig, X1, .955, "2017-04 ~ 2026-08 · 주간 · 사전등록 측정", fontsize=7.5,
           color=MUTED, ha="right")
        hline(fig, X0, X1, .922, RULE, 1.0)

        box(fig, X0, .765, X1 - X0, .145, GROUND, ec=LINE, lw=.8)
        tx(fig, X0 + .012, .898, "규칙은 두 줄이다", fontsize=9.5, fontweight="bold")
        tx(fig, X0 + .012, .878, "①  나스닥100 을 벤더 정본 비중대로 전부 든다 — 공매도 없음 · 현금 없음 · 상시 100%.",
           fontsize=8.2)
        tx(fig, X0 + .012, .860, "②  매주 금요일 종가에 각 종목의 dist200(종가/200일선-1)을 z-점수로 세워,",
           fontsize=8.2)
        tx(fig, X0 + .030, .843, "비중을 w' ∝ w x (1 + 0.3xz) 로 기울인다 (z 는 ±2 에서 자름 → 상대 틸트 최대 ±60%).",
           fontsize=8.2)
        tx(fig, X0 + .012, .820, "추세 상위면 지수보다 조금 더, 하위면 조금 덜 — 지수에서 멀리 가지 않는다(추적오차 2.2%p).",
           fontsize=8.2, color=INK2)
        tx(fig, X0 + .012, .797, "실물 구현: 인핸스드 인덱스 펀드의 표준 구조 그대로 — 지수 복제 포트에서 주 1회 비중만 조정.",
           fontsize=7.4, color=MUTED)

        tx(fig, X0, .742, "성과 한눈 (2017-04 ~ 2026-08 · 489주 · 평균 95종)", fontsize=10.5, fontweight="bold")
        hdr = ["", "CAGR", "샤프", "MDD", "추적오차", "월 승률"]
        rows = [["틸트", "%.2f%%" % m_t["cagr"], "%.2f" % m_t["sharpe"], "%.2f%%" % m_t["mdd"],
                 "%.2f%%p" % A["te_pp"], "%.1f%%" % J["monthly_winrate_pct"]],
                ["복제(벤더 비중 그대로)", "%.2f%%" % m_r["cagr"], "%.2f" % m_r["sharpe"],
                 "%.2f%%" % m_r["mdd"], "-", "-"],
                ["^NDX 실지수", "%.2f%%" % m_b["cagr"], "%.2f" % m_b["sharpe"],
                 "%.2f%%" % m_b["mdd"], "-", "-"]]

        def cc(r, c):
            return {0: C_T, 1: C_R, 2: C_B}[r] if c == 0 else INK
        table(fig, X0, .730, [.24, .11, .09, .11, .11, .10], hdr, rows, row_h=.0175,
              fs=7.8, hfs=7.2, aligns=["l", "r", "r", "r", "r", "r"], cell_color=cc)

        tx(fig, X0, .630, "판정 — 사용자 3문 (vs 나스닥100)", fontsize=10.5, fontweight="bold")
        g_rows = [["U1 수익", "%.2f%% > %.2f%% (배당보정 %.2f%% 도 초과)" %
                   (G["U1_cagr"]["strat"], G["U1_cagr"]["bm"], G["U1_cagr"]["bm_div_adj"]), "통과"],
                  ["U2 샤프", "%.2f > %.2f" % (G["U2_sharpe"]["strat"], G["U2_sharpe"]["bm"]), "통과"],
                  ["U3 MDD", "%.2f%% < %.2f%%" % (G["U3_mdd"]["strat"], G["U3_mdd"]["bm"]), "통과"]]
        table(fig, X0, .618, [.12, .48, .10], ["문", "실측", "판정"], g_rows, row_h=.0175,
              fs=7.8, hfs=7.2, aligns=["l", "l", "c"],
              cell_color=lambda r, c: POS if c == 2 else INK)
        tx(fig, X0, .540, "3/3 통과 — 단, 아래 분해표가 이 문서에서 가장 중요한 표다.", fontsize=8,
           color=INK2, fontweight="bold")

        tx(fig, X0, .512, "«지수 대비 +2.7%p» 의 정체 — 정직한 분해", fontsize=10.5, fontweight="bold")
        d_rows = [["배당 재투자", "~ +0.8%p", "실재 — 실물 포트도 받는다 (^NDX 는 가격지수라 배당이 없다)"],
                  ["생존 틸트", "~ +0.9%p", "편향 — 가격 인프라 밖 편출종목(탈락비중 평균 2.5%)이 복제에서 빠진 몫"],
                  ["틸트 알파", "+0.79%p", "신호의 몫 — 같은 기저·같은 비용의 복제 대비라 위 둘이 상쇄된 유일한 순수 줄"]]
        table(fig, X0, .500, [.16, .12, .56], ["몫", "크기", "성격"], d_rows, row_h=.020,
              fs=7.6, hfs=7.2, aligns=["l", "r", "l"],
              cell_color=lambda r, c: (NEG if r == 1 else POS if r == 2 else INK) if c == 1 else INK)
        tx(fig, X0, .418, "틸트 알파의 통계: 연 +0.79%p · IR 0.37 · t 1.22 — 방향은 안정적(민감도 4종 전부 +0.4~+1.2%p)이나",
           fontsize=7.6, color=INK2)
        tx(fig, X0, .404, "관행 문턱(t≥2)에는 못 미친다. 단일 신호 인핸스드 인덱싱의 문헌 관행 IR(0.3~0.5) 한복판이다.",
           fontsize=7.6, color=INK2)

        tx(fig, X0, .368, "계보 — 논문 재현이 아니라 조립이다", fontsize=10.5, fontweight="bold")
        for j, s in enumerate([
            "· 틀: Grinold (1989) 「The Fundamental Law of Active Management」 · Grinold & Kahn 「Active Portfolio",
            "  Management」 — IR ~ IC x √(독립 베팅 수). 제약(롱온리)의 IR 손실은 Clarke, de Silva & Thorley (2002).",
            "· 신호: 모멘텀 계보 — Jegadeesh & Titman (1993) · George & Hwang (2004) 52주 신고가 · Han, Yang &",
            "  Zhou (2013) 이동평균 거리의 횡단면. 단, dist200 자체는 이 랩이 등록·검증한 게시 규칙의 재사용이다.",
            "· 조립: w' ∝ w x (1+K·z) 는 실무 관행 구조 — K=0.3·클립 ±2 는 «추적오차 2~3%p» 관행 목표의 상수다.",
        ]):
            tx(fig, X0, .350 - j * .0145, s, fontsize=7.2, color=INK2)
        footer(fig, 1)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 2쪽 — 작동 원리 ────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "작동 원리 — 한 주의 순서", fontsize=13, fontweight="bold")
        steps = [
            ("① 기준 비중", "그 주말의 벤더 나스닥100 지수 비중을 받는다(정본). 유효 가격이 없는 종목은 빼고 재정규화 — 뺀 비중 크기를 매주 기록한다(평균 2.5%)."),
            ("② 신호", "종목마다 dist200 = 종가/200일선 - 1. 200일선은 유효 종가 160일 이상일 때만 — 신입 종목은 신호가 설 때까지 틸트 없이 벤치 비중 그대로."),
            ("③ 표준화", "그 주 유니버스 안에서 dist200 을 z-점수로 — 시장 전체가 다 오른 주엔 아무도 특별하지 않다. ±2 에서 자른다."),
            ("④ 틸트", "w' = w x (1 + 0.3 x z), 합이 100% 되게 재정규화. z=+2 면 벤치의 1.6배, z=-2 면 0.4배 — 공매도도 현금도 없다."),
            ("⑤ 체결·비용", "주말 종가 체결. 비용 편도 5bp x 실회전(드리프트 보정) — 실측 4.4%/주. 비용을 20bp 로 올려도 초과 +0.48%p 로 살아남는다."),
        ]
        yy = .920
        for tt, body in steps:
            tx(fig, X0, yy, tt, fontsize=9, fontweight="bold", color=ST.CHAMP)
            tx(fig, X0 + .105, yy, body, fontsize=7.6, color=INK2, wrap=True)
            yy -= .043

        tx(fig, X0, .690, "틸트 함수 — 신호가 비중을 얼마나 움직이나", fontsize=10, fontweight="bold")
        ax = fig.add_axes([X0 + .02, .46, .40, .20])
        zs = [x / 50.0 for x in range(-150, 151)]
        mult = [1 + 0.3 * max(-2, min(2, z)) for z in zs]
        ax.plot(zs, mult, color=C_T, lw=1.6)
        ax.axhline(1.0, color=RULE, lw=.7, ls="--")
        ax.axvline(0, color=RULE, lw=.7, ls="--")
        ax.fill_between(zs, mult, 1.0, where=[m > 1 for m in mult], color=POS, alpha=.10)
        ax.fill_between(zs, mult, 1.0, where=[m < 1 for m in mult], color=NEG, alpha=.10)
        ax.set_xlim(-3, 3); ax.set_ylim(0.2, 1.8)
        ax.set_xlabel("dist200 z-점수", fontsize=7); ax.set_ylabel("벤치 비중 대비 배율", fontsize=7)
        ax.tick_params(labelsize=6.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(LINE)
        ax.set_facecolor(PAPER)
        ax.text(2.1, 1.62, "+60% 상한", fontsize=6.5, color=POS)
        ax.text(-2.9, 0.34, "-60% 하한", fontsize=6.5, color=NEG)

        tx(fig, X0 + .47, .690, "가상 예시 — 5종목 지수라면", fontsize=10, fontweight="bold")
        tx(fig, X0 + .47, .674, "(실제 벤더 비중은 문서에 싣지 않는다 — 커밋 금지 규약)", fontsize=6.6, color=MUTED)
        hdr = ["종목", "벤치", "z", "x배율", "틸트 후"]
        ex = [["A (강한 추세)", "30%", "+1.5", "1.45", "36.9%"],
              ["B (완만)", "25%", "+0.5", "1.15", "24.4%"],
              ["C (중립)", "20%", "0.0", "1.00", "17.0%"],
              ["D (약세)", "15%", "-1.0", "0.70", "8.9%"],
              ["E (급락 후)", "10%", "-2.0", "0.40", "3.4%"],
              ["합", "100%", "", "", "90.6→100%"],
        ]
        table(fig, X0 + .47, .660, [.14, .07, .06, .07, .09], hdr, ex, row_h=.0165,
              fs=7.2, hfs=6.9, aligns=["l", "r", "r", "r", "r"])
        tx(fig, X0 + .47, .535, "틸트 후 합(90.6%)을 100% 로 재정규화한 값이", fontsize=6.8, color=MUTED)
        tx(fig, X0 + .47, .524, "마지막 열이다 — 현금이 생기지 않는 구조.", fontsize=6.8, color=MUTED)

        tx(fig, X0, .418, "왜 «조금만» 기울이나 — Grinold 의 산수", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 신호의 질(IC)이 정해져 있으면 초과수익은 추적오차에 비례해서만 커진다 — 세게 기울이면 초과도 위험도",
            "  같이 커져 IR(초과/추적오차)은 그대로다. 실측이 그 산수 그대로다: K 를 0.15→0.3→0.5 로 올리면",
            "  초과 +0.42→+0.79→+1.21%p 로 늘지만 t 는 1.25→1.22→1.18 로 오히려 미세하게 준다(비용이 갉아서).",
            "· IR 을 올리는 유일한 정공법은 서로 안 겹치는 신호를 «더하는» 것이다(IR ~ IC x √베팅수) — 이 랩의",
            "  삼각대 측정(상관 0.2 인 세 축 → 혼합 t 가 최고 단독을 초과)이 같은 산수의 수익률 버전이다.",
            "· 그래서 이 전략의 다음 판은 «K 를 키우는 것»이 아니라 «변동성 군집·거장 매집을 틸트 축으로 더하는",
            "  것»이다 — 그건 새 사전등록으로만 간다.",
        ]):
            tx(fig, X0, .400 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .282, "무엇이 이 설계를 지수 펀드 실무에 맞게 하나", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 벤치에서 멀리 못 간다: 추적오차 2.16%p — 인핸스드 인덱스 관행(2~3%p) 안. 최악의 해에도 지수와",
            "  ±3%p 안에서 움직였다(연도표 3쪽). 심리적으로도 규정상으로도 «지수 펀드»의 자리를 벗어나지 않는다.",
            "· 회전 4.4%/주 · 비용 민감도 낮음(20bp 에도 생존) · 종목 수 ~100 · 리밸 주 1회 — 운용 부담이 작다.",
            "· 신호가 전부 공개 가격에서 나온다 — 재무 지연·공시 시차 같은 시점 함정이 없는 축이다.",
        ]):
            tx(fig, X0, .264 - j * .0145, s, fontsize=7.2, color=INK2)
        footer(fig, 2)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 3쪽 — 성과 상세 ────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "성과 상세", fontsize=13, fontweight="bold")
        tx(fig, X0, .936, "누적 성과 (로그 · 100 출발)", fontsize=8, color=MUTED)
        ax = fig.add_axes([X0, .60, X1 - X0, .32])
        for vals, col, lab, lw in ((dv_b, C_B, "^NDX 실지수", .9),
                                   (dv_r, C_R, "복제(벤더 비중)", 1.0),
                                   (dv_t, C_T, "틸트", 1.5)):
            base = vals[0]
            ax.plot(XD, [v / base * 100 for v in vals], color=col, lw=lw, label=lab)
        ax.set_yscale("log")
        from matplotlib.ticker import NullFormatter
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_yticks([100, 200, 400, 800])
        ax.set_yticklabels(["100", "200", "400", "800"], fontsize=7)
        ax.tick_params(axis="x", labelsize=7)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(LINE)
        ax.grid(axis="y", color=LINE, lw=.5, alpha=.7)
        ax.legend(loc="upper left", fontsize=7.5, frameon=False)
        ax.set_facecolor(PAPER)

        tx(fig, X0, .555, "누적 틸트 효과 — 틸트/복제 비율(%) · 배당·생존편향이 상쇄된 순수 신호의 몫", fontsize=8,
           fontweight="bold")
        ax2 = fig.add_axes([X0, .40, X1 - X0, .14])
        ratio = [(t / r - 1) * 100 for t, r in zip(dv_t, dv_r)]
        ax2.plot(XD, ratio, color=C_T, lw=1.2)
        ax2.axhline(0, color=RULE, lw=.7)
        ax2.fill_between(XD, ratio, 0, color=C_T, alpha=.10)
        ax2.tick_params(labelsize=6.8)
        for sp in ("top", "right"):
            ax2.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax2.spines[sp].set_color(LINE)
        ax2.set_facecolor(PAPER)
        tx(fig, X0, .372, "9.4년 누적 +%.1f%% (연 +0.79%%p). 꾸준한 우상향이 아니라 구간별로 벌고 되돌린다 — "
                          "모멘텀 크래시(2022 초·2025 봄)가 이 신호의 약한 자리다." % ratio[-1],
           fontsize=7.0, color=INK2)

        Yt, Yr, Yb = J["years"]["tilt"], J["years"]["replica"], J["years"]["ndx"]
        years = sorted(Yb)
        tx(fig, X0, .344, "연도별 수익률(%) — 2017 은 4월부터 · 2026 은 8월까지", fontsize=10, fontweight="bold")
        hdr = ["연도"] + years
        rows = [["틸트"] + ["%+.0f" % Yt[y] for y in years],
                ["복제"] + ["%+.0f" % Yr[y] for y in years],
                ["^NDX"] + ["%+.0f" % Yb[y] for y in years],
                ["틸트-복제"] + ["%+.1f" % (Yt[y] - Yr[y]) for y in years]]

        def cc3(r, c):
            if c == 0:
                return {0: C_T, 1: C_R, 2: C_B, 3: INK}[r]
            v = float(rows[r][c])
            return NEG if v < 0 else (POS if r == 3 else INK)
        w0 = .10
        table(fig, X0, .332, [w0] + [(X1 - X0 - w0) / len(years)] * len(years), hdr, rows,
              row_h=.0165, fs=6.9, hfs=6.6, aligns=["l"] + ["r"] * len(years), cell_color=cc3)

        tx(fig, X0, .240, "민감도 — 상수 하나에 매달린 결과가 아닌가", fontsize=10, fontweight="bold")
        hdr = ["변형", "CAGR", "틸트-복제", "t", "MDD"]
        sl = [["기본 (K=0.3 · 주간 · 5bp)", "%.2f" % m_t["cagr"], "%+.2f%%p" % A["ann_pp"],
               "%.2f" % A["t"], "%.2f" % m_t["mdd"]]]
        for nm, lab in (("K015", "K=0.15 (절반)"), ("K050", "K=0.5 (1.7배)"),
                        ("monthly", "월간 리밸"), ("cost20", "비용 20bp")):
            v = J["sens"][nm]
            sl.append([lab, "%.2f" % v["cagr"], "%+.2f%%p" % v["active_pp"],
                       "%.2f" % v["t_active"], "%.2f" % v["mdd"]])
        table(fig, X0, .228, [.26, .10, .12, .08, .10], hdr, sl, row_h=.0165,
              fs=7.2, hfs=6.9, aligns=["l", "r", "r", "r", "r"])
        tx(fig, X0, .128, "네 변형 전부 초과 +0.4~+1.2%p · t 0.8~1.5 — 방향은 상수 선택과 무관하게 안정적이고,",
           fontsize=7.0, color=INK2)
        tx(fig, X0, .116, "크기는 어느 설정에서도 t>=2 에 못 미친다. 월간 리밸(t 1.51)이 주간보다 낫다 — 주간은 노이즈 매매다.",
           fontsize=7.0, color=INK2)
        footer(fig, 3)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 4쪽 — 정직성·전방 ──────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "정직성과 한계 — 이 문서가 말하지 않는 것", fontsize=13, fontweight="bold")
        for j, s in enumerate([
            "· 순수 틸트 효과 t 1.22 는 «우연이 아니라고 말하기엔 부족» 한 크기다. 사용자 3문(수익·샤프·MDD)은",
            "  통과했지만, 그 통과분의 절반 이상이 배당 기저(+0.8%p)와 생존 틸트(+0.9%p)다 — 1쪽 분해표.",
            "· 구간이 등록(2014-07)보다 짧다(2017-04~). 그 이전은 편출종목(CELG·PCLN·YHOO 등) 가격이 없어",
            "  «기준을 못 맞추면 안 넣는다» 규칙에 걸린다. 남은 구간에도 탈락비중 평균 2.5%가 있다 — 빠진 것은",
            "  대부분 «이후 인수·퇴출된 종목»이라 복제·틸트 양쪽을 같은 방향으로 부풀린다(상대 비교에선 상쇄).",
            "· 신호(dist200)의 강도는 이 표본에서 이미 측정된 값의 재사용이다 — 완전한 표본 외 검증이 아니다.",
            "· 2022 초·2025 봄의 모멘텀 크래시 구간에서 틸트가 복제에 진다(3쪽 비율 곡선) — 이 신호의 구조적",
            "  약점이고, 축 추가(신호 분산) 없이는 사라지지 않는다.",
            "· 기준 비중이 사내 DB(커밋 금지)라 CI 러너가 이 측정을 재생산할 수 없다 — 얼린 측정이며, 라이브로",
            "  가려면 로컬 잡 + 주간 비중 갱신 경로가 필요하다.",
            "· 전방 기록 0건. 백테스트가 좋다는 것과 다음 분기에 좋다는 것 사이의 거리가 이 랩의 존재 이유다.",
        ]):
            tx(fig, X0, .930 - j * .0155, s, fontsize=7.4, color=INK2)

        tx(fig, X0, .755, "예측 채점 — 계산 전에 적은 5건", fontsize=10.5, fontweight="bold")
        P = J["predictions"]
        pr = [["P1 틸트효과 +0.3~2.0%p · t 0.8~2.5", "+0.79%p · t 1.22", "적중"],
              ["P2 TE 1.5~4%p · IR 0.2~0.8", "%.2f%%p · %.2f" % (P["P2_te_ir"]["te_pp"], P["P2_te_ir"]["ir"]), "적중"],
              ["P3 3문 중 2~3 통과", "3/3", "적중"],
              ["P4 월 승률 52~60%", "%.1f%%" % P["P4_winrate"]["pct"], "초과(빗나감)"],
              ["P5 복제-지수 +0.4~1.2%p", "%+.2f%%p — 생존 틸트 몫" % P["P5_replica"]["ann_pp"], "빗나감"]]
        table(fig, X0, .742, [.36, .26, .12], ["예측", "실측", "판정"], pr, row_h=.0175,
              fs=7.2, hfs=6.9, aligns=["l", "l", "c"],
              cell_color=lambda r, c: (POS if "적중" == pr[r][2] else NEG) if c == 2 else INK)
        tx(fig, X0, .630, "P5 의 빗나감이 이 측정의 가장 유익한 발견이다 — 복제가 지수를 +1.73%p 이기는 것을",
           fontsize=7.0, color=MUTED)
        tx(fig, X0, .618, "보고서야 탈락비중 2.5%의 생존 틸트가 +0.9%p 짜리라는 것을 쟀다. 1쪽 분해표는 그 산물이다.",
           fontsize=7.0, color=MUTED)

        tx(fig, X0, .585, "다음 손잡이 — 순서대로", fontsize=10.5, fontweight="bold")
        for j, s in enumerate([
            "① 신호 분산(2판): 변동성 군집(x-archlm 축) · 거장 매집(x-guruacc 축)을 틸트로 이식해 IR 0.37 이",
            "   Grinold 산수(√k 근방)대로 오르는지 — 새 사전등록으로만. 삼각대의 수익률 실험을 비중으로 반복하는 것.",
            "② 월간 리밸 채택 검토: 민감도에서 t 1.51 로 주간보다 낫다 — 단 이것도 «민감도를 보고 고르는 것»이라",
            "   2판 등록에 주 리밸 주기를 월간으로 박고 전방으로 확인하는 게 규율에 맞다.",
            "③ 상장폐지 조정가 벤더(EODHD): 2014-16 구간 복원 + 탈락비중 2.5% 제거 — 생존 틸트 몫을 0 에 붙인다.",
            "④ 전방 기록: 주간 시계열이 data/tilt.json 에 남는다 — 20주 쌓이면 백테스트와 첫 대조.",
        ]):
            tx(fig, X0, .567 - j * .0155, s, fontsize=7.4, color=INK2)
        footer(fig, 4)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
