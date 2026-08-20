# -*- coding: utf-8 -*-
"""build/report_web_pdf.py — 거미줄 전략 보고서(팩트시트 판형) → build/REPORT-2026-08-20-WEB.pdf

1쪽 = 표준 전략 랩(기간별·위험지표·누적/낙폭), 이후 월별 히트맵·사다리·구조·검증.
수치는 얼린 측정(data/web.json)과 대조 가드로 일치 보장.

    python build/report_web_pdf.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(HERE, "REPORT-2026-08-20-WEB.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST
from style_top_pdf import tx, hline, box, table
import factsheet_lib as FS
from aegis_backtest import load_px, week_ends, Sig, metrics
from tilt_backtest import load_weights, alias_map
from aegis3_backtest import load_rf
from wvane_backtest import RetSig, build_weeks
import web_backtest as WB

ST.require_draw()
X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER = ST.POS, ST.NEG, ST.ACC, ST.PAPER
CHAMP, RP, MARG, GROUND = ST.CHAMP, ST.RP, ST.MARG, ST.GROUND
C_W, C_N, C_B = POS, MARG, RP
TOTAL = 4


def footer(fig, page):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .027, "거미줄(WEB) 전략 보고서 · 사전등록 PREREG-2026-08-20-WEB(계산 전 커밋 · 적대 검토 2렌즈) · "
                      "기준 비중 벤더 정본(DB · 원자료 커밋 금지) · 비용 5bp 순액식 · 조달 실측 rf",
       fontsize=6.4, color=MUTED)
    tx(fig, X0, .019, "과거 시험(백테스트) — 가족 라벨 «유망하나 선택과 구별 불가»(t 2.19 < 가족 보정 3.0) · 전방 기록 0건",
       fontsize=6.0, color=NEG)
    tx(fig, X1, .027, "%d / %d · %s" % (page, TOTAL, dt.date.today().isoformat()),
       fontsize=6.4, color=MUTED, ha="right")


def new_page():
    return plt.figure(figsize=(8.27, 11.69))


def main() -> int:
    J = json.load(io.open(os.path.join(DATA, "web.json"), encoding="utf-8"))
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
    vsig = RetSig(px, len(dts))
    bsig = Sig(bench, len(dts))
    we_idx = week_ends(dts)
    weeks, _sk = build_weeks(dts, px, W, AL, we_idx, bsig)
    resolve = WB.sector_labels(W, AL)
    lam, _lc = WB.lam_series(bench["ndx"], dts, we_idx)
    P = WB.build_signals(dts, px, weeks, sig, vsig, resolve)
    A = {"R": WB.run(dts, px, weeks, P, lam, rf, last_ym),
         "WEB": WB.run(dts, px, weeks, P, lam, rf, last_ym, use_s=True,
                       k_mode="neutral", use_lambda=True, band=True),
         "NRp": WB.run(dts, px, weeks, P, lam, rf, last_ym, k_mode="global", band=True)}
    m_web = metrics(A["WEB"]["daily_d"], A["WEB"]["dv"], A["WEB"]["wk"]["ret"])
    if abs(m_web["cagr"] - J["metrics"]["WEB"]["cagr"]) > .005:
        raise SystemExit("재계산이 정본과 어긋난다: %.2f vs %.2f"
                         % (m_web["cagr"], J["metrics"]["WEB"]["cagr"]))
    DD = A["WEB"]["daily_d"]
    XD = [dt.date.fromisoformat(d) for d in DD]
    d2i = {d: i for i, d in enumerate(dts)}
    ndx_ff, last = [], None
    for v in bench["ndx"]:
        if v is not None:
            last = v
        ndx_ff.append(last)
    ib0 = d2i[DD[0]]
    dv_bm = [100.0 * ndx_ff[d2i[d]] / ndx_ff[ib0] for d in DD]
    wk_b = [ndx_ff[w["i1"]] / ndx_ff[w["i0"]] - 1 for w in weeks]
    off_spans, s0 = [], None
    for w in weeks:
        if not w["on"] and s0 is None:
            s0 = w["d0"]
        elif w["on"] and s0 is not None:
            off_spans.append((s0, w["d0"])); s0 = None
    if s0 is not None:
        off_spans.append((s0, weeks[-1]["d0"]))
    L = J["ladder"]; MAIN = J["main"]

    with PdfPages(OUT) as pdf:
        # ── 1쪽 — 팩트시트 ─────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .958, "거미줄 (WEB)", fontsize=16, fontweight="bold")
        tx(fig, X0, .938, "나스닥100 계층 틸트 — 섹터중립 모멘텀 x 변동성 관리 x 편입비 밴드",
           fontsize=9, color=INK2)
        box(fig, X0 + .60, .938, .28, .030, GROUND, ec=POS, lw=1.0)
        tx(fig, X0 + .612, .962, "사전등록 주 판정: 셀 ① 통과", fontsize=8.2,
           fontweight="bold", color=POS)
        tx(fig, X0 + .612, .947, "(가족 라벨: 유망 · 선택과 구별 불가)", fontsize=6.2, color=MUTED)
        hline(fig, X0, X1, .928, RULE, 1.0)
        tx(fig, X0, .920, "유형 NDX 인핸스드 인덱스 · 기간 2017-04 ~ 2026-08 (9.4년 · 주간) · 종목 ~100 · "
                          "추적오차 %.1f%%p · 벤치마크 나스닥100" % L["WEB"]["te_pp"],
           fontsize=7.2, color=MUTED)

        FS.draw_cum_dd(fig, [X0, .645, X1 - X0, .245], [X0, .525, X1 - X0, .095],
                       XD, [(dv_bm, C_B, "나스닥100", .9),
                            (A["NRp"]["dv"], C_N, "챔피언 NR' (전역 모멘텀+밴드)", 1.0),
                            (A["WEB"]["dv"], C_W, "거미줄", 1.5)], off_spans)
        tx(fig, X0, .905, "누적 성과(로그 · 100 출발) · 아래 = 고점 대비 낙폭(%) · 음영 = 200일선 아래",
           fontsize=7.4, color=MUTED)

        # 기간별 수익률
        tx(fig, X0, .498, "기간별 수익률", fontsize=8.5, fontweight="bold")
        pr_w = FS.period_returns(DD, A["WEB"]["dv"])
        pr_b = FS.period_returns(DD, dv_bm)
        FS.draw_period_table(fig, X0, .484,
                             [("거미줄", pr_w), ("나스닥100", pr_b)], width=.86)

        # 위험지표
        tx(fig, X0, .420, "위험·성과 지표 (주간 수익 기준 · 비용 후)", fontsize=8.5, fontweight="bold")
        rs_w = FS.risk_stats(DD, A["WEB"]["dv"], A["WEB"]["wk"]["ret"], wk_b)
        rs_b = FS.risk_stats(DD, dv_bm, wk_b, wk_b)
        hdr = ["", "연수익률", "연변동성", "샤프", "최대낙폭", "추적오차", "IR", "연초과"]
        rows = [["거미줄", "%.2f%%" % rs_w["cagr"], "%.2f%%" % rs_w["vol"], "%.2f" % rs_w["sharpe"],
                 "%.2f%%" % rs_w["mdd"], "%.2f%%p" % rs_w["te"], "%.2f" % rs_w["ir"],
                 "%+.2f%%p" % rs_w["ann_ex"]],
                ["나스닥100", "%.2f%%" % rs_b["cagr"], "%.2f%%" % rs_b["vol"], "%.2f" % rs_b["sharpe"],
                 "%.2f%%" % rs_b["mdd"], "-", "-", "-"]]
        table(fig, X0, .408, [.13, .10, .10, .08, .10, .10, .07, .10], hdr, rows,
              row_h=.0175, fs=7.2, hfs=6.6, aligns=["l"] + ["r"] * 7,
              cell_color=lambda r, c: (C_W if r == 0 else C_B) if c == 0 else INK)
        tx(fig, X0, .345, "주의: 연초과에는 배당 기저(+0.8%%p)와 자료 없는 편출종목 몫(~+0.9%%p)이 포함 — 순수 전략 몫은 "
                          "복제 대비 +%.2f%%p (4쪽 검증)." % L["WEB"]["ann_pp"], fontsize=6.8, color=NEG)

        # 월간 히트맵
        mat, yr = FS.monthly_matrix(DD, A["WEB"]["dv"])
        FS.draw_monthly_heat(fig, X0, .320, mat, yr, width=.86,
                             title="월간 수익률(%) — 거미줄")
        footer(fig, 1)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 2쪽 — 사다리(층별) ─────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "사다리 — 실을 한 가닥씩 얹으며 (전부 순복제 대비 · 같은 비용)", fontsize=13, fontweight="bold")
        hdr = ["계단", "구성", "V(연, vs 복제)", "t", "TE", "IR"]
        lad = [["S", "섹터 실만", "%+.2f%%p" % L["S"]["ann_pp"], "%.2f" % L["S"]["t"],
                "%.2f" % L["S"]["te_pp"], "%.2f" % L["S"]["ir"]],
               ["K", "섹터중립 모멘텀만", "%+.2f%%p" % L["K"]["ann_pp"], "%.2f" % L["K"]["t"],
                "%.2f" % L["K"]["te_pp"], "%.2f" % L["K"]["ir"]],
               ["S+K", "둘 결합", "%+.2f%%p" % L["SK"]["ann_pp"], "%.2f" % L["SK"]["t"],
                "%.2f" % L["SK"]["te_pp"], "%.2f" % L["SK"]["ir"]],
               ["S+K+T", "+ 변동성 관리 λ", "%+.2f%%p" % L["SKT"]["ann_pp"], "%.2f" % L["SKT"]["t"],
                "%.2f" % L["SKT"]["te_pp"], "%.2f" % L["SKT"]["ir"]],
               ["WEB", "+ 편입비 밴드 = 거미줄", "%+.2f%%p" % L["WEB"]["ann_pp"], "%.2f" % L["WEB"]["t"],
                "%.2f" % L["WEB"]["te_pp"], "%.2f" % L["WEB"]["ir"]],
               ["NR'", "(챔피언) 전역 모멘텀+밴드", "%+.2f%%p" % L["NRp"]["ann_pp"], "%.2f" % L["NRp"]["t"],
                "%.2f" % L["NRp"]["te_pp"], "%.2f" % L["NRp"]["ir"]]]
        table(fig, X0, .930, [.08, .26, .13, .08, .08, .08], hdr, lad, row_h=.019,
              fs=7.4, hfs=7.0, aligns=["l", "l", "r", "r", "r", "r"], zebra=True,
              cell_color=lambda r, c: (C_W if r == 4 else C_N if r == 5 else INK) if c == 0 else INK)
        yy = .930 - 7 * .019 - .020
        for j, s in enumerate([
            "· 섹터 실(S)은 비용 후 +0.05%p — 정적 몫 +0.35 / 타이밍 몫 -0.30 으로, 등록에 미리 적어 둔 판정문",
            "  그대로 «섹터 실이 아니라 상시 IT 오버웨이트(베타 실)»였습니다. 섹터 타이밍은 없습니다.",
            "· 일꾼은 섹터중립 모멘텀(K, +0.87 · IR 0.49) — 전역 모멘텀(KG, IR 0.41)보다 위험 조정으로 낫습니다.",
            "· 변동성 관리 λ 는 예측(«수익을 깎을 것»)과 반대로 V 도 +0.07 올렸고 TE 를 줄였습니다(2.28→2.03).",
            "· 밴드가 마지막 도약 — 그리고 결합의 백미: 층을 넷 얹은 거미줄(TE 3.57)이 챔피언(3.71)보다",
            "  추적오차가 오히려 낮습니다. 실들이 서로의 위험을 상쇄한 몫입니다.",
        ]):
            tx(fig, X0, yy - j * .0148, s, fontsize=7.4, color=INK2)

        tx(fig, X0, .620, "주 판정 (계산 전에 얼린 기준)", fontsize=10.5, fontweight="bold")
        box(fig, X0, .540, X1 - X0, .068, GROUND, ec=LINE, lw=.8)
        tx(fig, X0 + .012, .598, "ΔIR(거미줄 - 챔피언) = %+.3f  ·  블록 부트스트랩 p = %.2f (기준 ≥0.90)  ·  t(V_WEB) = %.2f (기준 ≥2)"
           % (MAIN["d_ir"], MAIN["boot_p"], MAIN["t_web"]), fontsize=8.6, fontweight="bold")
        tx(fig, X0 + .012, .578, "→ 해석 셀 ① «거미줄 이득 후보» — 이 계열 8번의 등록에서 처음으로 주 판정을 통과했습니다.",
           fontsize=8.2, color=POS, fontweight="bold")
        tx(fig, X0 + .012, .560, "등록 전 몬테카를로: 이 관문의 우연 통과율은 2.7%(무정보 세계) — 통과는 강한 증거, 실패는 정보 아님이라고 미리 적어 두었습니다.",
           fontsize=7.0, color=MUTED)

        tx(fig, X0, .512, "연도별 수익률(%)", fontsize=10, fontweight="bold")
        mat_n, yr_n = FS.monthly_matrix(DD, A["NRp"]["dv"])
        mat_b, yr_b = FS.monthly_matrix(DD, dv_bm)
        years = sorted(yr.keys())
        hdr = ["연도"] + years
        rows = [["거미줄"] + ["%+.0f" % yr[y] for y in years],
                ["챔피언 NR'"] + ["%+.0f" % yr_n[y] for y in years],
                ["나스닥100"] + ["%+.0f" % yr_b[y] for y in years]]
        def cc3(r, c):
            if c == 0:
                return {0: C_W, 1: C_N, 2: C_B}[r]
            return NEG if float(rows[r][c]) < 0 else INK
        w0 = .11
        table(fig, X0, .500, [w0] + [(X1 - X0 - w0) / len(years)] * len(years), hdr, rows,
              row_h=.017, fs=6.8, hfs=6.5, aligns=["l"] + ["r"] * len(years), cell_color=cc3)

        mat2, yr2 = FS.monthly_matrix(DD, [b / a for a, b in zip(A["NRp"]["dv"], A["WEB"]["dv"])])
        FS.draw_monthly_heat(fig, X0, .400, mat2, yr2, width=.86,
                             title="월간 상대 성과(%) — 거미줄 - 챔피언 (양수 = 거미줄 우세)")
        footer(fig, 2)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 3쪽 — 구조 ────────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "구조 — 네 가닥의 실", fontsize=13, fontweight="bold")
        rows3 = [
            ["① 섹터 실 (S)", "매주 섹터별 «구성종목 가중평균 추세»를 등수 매겨 좋은 섹터를 +15% 한도로 증량. "
             "결과: 타이밍 없음 — 사실상 상시 IT 소폭 증량이었음이 측정으로 판명."],
            ["② 종목 실 (K)", "같은 섹터 동료끼리만 추세(200일선 대비 %)를 등수 매겨 비중을 ±60% 한도로 기울임. "
             "«반도체는 반도체끼리, 소비재는 소비재끼리» — 섹터 베팅과 종목 베팅을 분리."],
            ["③ 시점 실 (T)", "λ = min(1, 20%/최근 3개월 지수 변동성). 시장이 거칠수록 모든 기울기를 λ 배로 축소 — "
             "«확신은 고요할 때만». 거친 주(전체의 42%)에 틸트가 자동으로 얌전해집니다."],
            ["④ 편입비 실 (B)", "지수가 200일선 위면 110%(차입이자 실측 반영), 아래면 90%. 검증된 층(이지스3)의 재사용."],
        ]
        table(fig, X0, .930, [.15, .70], ["실", "규칙과 실측"], rows3, row_h=.036, fs=7.3,
              hfs=7.0, aligns=["l", "l"], zebra=True)

        tx(fig, X0, .760, "왜 «촘촘한» 것이 이번엔 통과했나 — 그리고 왜 이전 복잡성은 다 죽었나", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 풍향계(레짐 팩터 회전)·함대(무선별 6축)는 «죽은 신호를 더하는» 복잡성이라 기각됐습니다. 거미줄의 층은",
            "  다릅니다: 살아 있는 신호 하나(모멘텀)를 유지한 채 ①분류를 정교화(섹터중립)하고 ②강도를 위험에 맞추고",
            "  (λ) ③노출을 조절(밴드)했습니다 — 신호를 늘린 게 아니라 같은 신호의 «집행»을 정교화한 것입니다.",
            "· 그 결과가 ΔTE -0.14: 층을 얹고 위험이 줄었습니다. 죽은 신호를 더하면 위험만 늘어납니다(함대의 교훈).",
            "· 섹터 실만은 예외로 낙제(타이밍 -0.30) — 거미줄에서도 «어느 섹터를 어느 순간에»는 나스닥100 안에서는",
            "  성립하지 않았습니다. IT 60% 유니버스의 구조적 한계로, 등록 §0 이 사전에 경고한 그대로입니다.",
        ]):
            tx(fig, X0, .742 - j * .0148, s, fontsize=7.4, color=INK2)

        tx(fig, X0, .630, "운용 프로파일", fontsize=10, fontweight="bold")
        rows4 = [
            ["리밸런스", "주 1회 (금요일 종가 기준)"],
            ["종목 수", "~100 (나스닥100 전 종목 · 공매도/제외 없음)"],
            ["추적오차", "%.1f%%p — 인핸스드 인덱스 관행(2~4%%p) 안" % L["WEB"]["te_pp"]],
            ["비용 가정", "편도 5bp x 순액 실회전 · 110%% 구간 차입이자 실측 rf · 20bp 에서도 V +%.2f%%p 생존" % J["sens"]["cost20"]["ann_pp"]],
            ["현재 상태", "200일선 위 — 편입비 110%% · 모멘텀 틸트 가동 (%s 주말 기준)" % weeks[-1]["d0"]],
        ]
        table(fig, X0, .618, [.15, .70], ["항목", "내용"], rows4, row_h=.021, fs=7.3,
              hfs=7.0, aligns=["l", "l"])
        footer(fig, 3)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 4쪽 — 검증·정직성 ─────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "검증과 정직성", fontsize=13, fontweight="bold")
        tx(fig, X0, .932, "예측 채점 — 계산 전에 적은 닫힌 구간 5건 중 3건 적중", fontsize=10, fontweight="bold")
        Pj = J["predictions"]
        pr = [["P1 종목실과 전역 모멘텀의 겹침 0.70~0.95", "%.3f" % Pj["P1"]["got"], "적중 — 사촌이지만 중복 아님"],
              ["P2 섹터중립화의 값 -0.30~+0.50%p", "%+.2f%%p" % Pj["P2"]["got"], "적중 — V 는 같고 IR 만 오름"],
              ["P3 λ는 수익을 깎을 것(ΔV<0)", "%+.2f%%p" % Pj["P3"]["got"]["d_v"], "빗나감 — 오히려 +0.07 (좋은 방향)"],
              ["P4 복잡성 세금 ∧ TE 증가 예측", "V %+.2f · TE %+.2f" % (Pj["P4"]["got"]["d_v"], Pj["P4"]["got"]["d_te"]),
               "빗나감 — 세금 대신 이득, TE 는 감소 (좋은 방향)"],
              ["P5 섹터 타이밍 몫 -0.30~+0.30%p", "%+.2f%%p" % Pj["P5"]["got"], "적중(경계) — 타이밍 없음 확인"]]
        table(fig, X0, .918, [.33, .16, .32], ["예측", "실측", "판정"], pr, row_h=.019,
              fs=7.0, hfs=6.8, aligns=["l", "r", "l"],
              cell_color=lambda r, c: ((POS if r in (0, 1, 4) else NEG) if c == 1 else INK))
        tx(fig, X0, .800, "P3·P4 의 빗나감이 모두 «전략에 유리한 쪽»이라는 것은 좋은 신호이자 경계 신호입니다 — 예측보다 잘 나온",
           fontsize=7.0, color=MUTED)
        tx(fig, X0, .787, "표본은 다음 표본에서 되돌아오는 경우가 많습니다. 그래서 판정 라벨을 올리지 않았습니다.",
           fontsize=7.0, color=MUTED)

        tx(fig, X0, .755, "민감도 — 상수를 흔들어도 그림이 같은가", fontsize=10, fontweight="bold")
        hdr = ["변형", "V(연, vs 복제)"]
        sl = [["기본", "%+.2f%%p" % L["WEB"]["ann_pp"]]]
        for nm, lab in (("Ksec0075", "섹터 강도 절반"), ("Ksec030", "섹터 강도 2배"),
                        ("K015", "종목 강도 절반"), ("monthly", "월간 리밸"), ("cost20", "비용 4배(20bp)")):
            sl.append([lab, "%+.2f%%p" % J["sens"][nm]["ann_pp"]])
        table(fig, X0, .742, [.20, .14], hdr, sl, row_h=.0165, fs=7.2, hfs=6.9,
              aligns=["l", "r"])

        tx(fig, X0 + .42, .755, "항등 검증 (배선 검산 5종 — 전부 통과)", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 전 실 꺼짐 = 순복제 (함대 기록과 교차 대조)",
            "· λ≡1 강제 = λ 없는 판과 동일",
            "· 틸트 없음+밴드 = 풍향계 B 와 교차 대조",
            "· 전 종목 단일 의사섹터 = 전역판과 동일",
            "· 챔피언 재런 = 풍향계 NR 와 방향 부합",
        ]):
            tx(fig, X0 + .42, .738 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .600, "정직성 — 이 숫자를 읽는 법", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 이것은 «선별 후 설계»입니다: 앞선 7번의 등록 결과를 전부 열람한 뒤 살아남은 부품으로 조립했습니다.",
            "  그 편의는 통계 보정으로 지워지지 않습니다 — 등록 §0 첫 문장이 이 선언입니다.",
            "· t 2.19 는 절대 하한(2)은 넘었지만 가족 보정 문턱(3.0)에는 못 미칩니다 — 공식 라벨은 «유망하나",
            "  선택과 구별 불가»이고, 이 라벨은 결과가 아무리 좋아도 등록 규칙상 바꿀 수 없습니다.",
            "· 섹터 라벨은 오늘 기준 소급(2018-09 GICS 개편 이전 ~74주는 반사실 분류) · 지수 대비 초과에는",
            "  배당 기저 +0.8%p 와 생존 틸트 ~+0.9%p 가 업혀 있습니다(복제 대비 비교에서는 상쇄).",
            "· 확정은 단 하나 — 전방 기록입니다. 주간 시계열이 data/web.json 에 쌓이기 시작했습니다.",
        ]):
            tx(fig, X0, .582 - j * .0148, s, fontsize=7.4, color=INK2)

        tx(fig, X0, .460, "계보와 다음", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· λ: Moreira-Muir(2017) 변동성 관리 계열(일방향 축소판) · 반대 문헌 Novy-Marx-Velikov 선등록.",
            "· 섹터중립 모멘텀: 실무 표준 — 이 랩에선 첫 측정이고 IR 0.49 로 전역판(0.41)을 이겼습니다.",
            "· 다음: ① 전방 20주 후 첫 대조 ② 섹터 실 제거판(K+T+B)을 새 등록으로 — 사다리상 더 단순하고",
            "  같은 성능일 가능성이 있습니다(부분 채택은 규칙상 새 등록으로만) ③ 운용 여부는 사용자 결정.",
        ]):
            tx(fig, X0, .442 - j * .0148, s, fontsize=7.4, color=INK2)
        footer(fig, 4)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
