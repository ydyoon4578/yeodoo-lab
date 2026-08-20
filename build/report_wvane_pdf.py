# -*- coding: utf-8 -*-
"""build/report_wvane_pdf.py — 풍향계 전략 보고서 → build/REPORT-2026-08-20-WVANE.pdf

얼린 측정(data/wvane.json · PREREG-2026-08-20-WVANE)의 보고서다. 곡선은 엔진
재실행(결정적 · 비중 캐시 필요)으로 그리되 정본과 어긋나면 빌드가 죽는다(대조 가드).

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
    tx(fig, X0, .027, "풍향계 전략 보고서 · 사전등록 PREREG-2026-08-20-WVANE(계산 전 커밋 · 적대 검토 4렌즈 반영) · "
                      "기준 비중은 벤더 정본(DB · 원자료 커밋 금지) · 비용 편도 5bp 순액식",
       fontsize=6.4, color=MUTED)
    tx(fig, X0, .019, "주 판정은 «회전의 몫»(증분) — 사용자 3문 통과는 부품(밴드)에서 승계된 것이라 판정에 쓰지 않았다 · "
                      "사용자-기준 계열 5번째 시도 · 전방 기록 0건",
       fontsize=6.0, color=NEG)
    tx(fig, X1, .027, "%d / %d · %s" % (page, TOTAL, dt.date.today().isoformat()),
       fontsize=6.4, color=MUTED, ha="right")


def new_page():
    return plt.figure(figsize=(8.27, 11.69))


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
    DEC = J["decomp"]; G = J["contrasts"]; P = J["predictions"]; SEN = J["sens"]
    mb = J["bench"]

    # 오프 구간 음영(주 단위)
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
        # ── 1쪽 — 표지·판정 ───────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "풍향계 (WEATHERVANE)", fontsize=17, fontweight="bold")
        tx(fig, X0, .932, "레짐 조건부 팩터 틸트 — «타이밍 x 팩터» 결합의 사전등록 검증",
           fontsize=10, color=INK2)
        tx(fig, X1, .955, "2017-04 ~ 2026-08 · 489주 · 5번째 사용자-기준 시도", fontsize=7.5,
           color=MUTED, ha="right")
        hline(fig, X0, X1, .922, RULE, 1.0)

        box(fig, X0, .800, X1 - X0, .110, GROUND, ec=LINE, lw=.8)
        tx(fig, X0 + .012, .898, "규칙", fontsize=9.5, fontweight="bold")
        tx(fig, X0 + .012, .878, "나스닥100 을 벤더 비중대로 들고, ^NDX 가 200일선 위면 «모멘텀 틸트 + 편입비 110%»,",
           fontsize=8.2)
        tx(fig, X0 + .012, .861, "아래면 «저변동 틸트 + 편입비 90%» — 레짐이 팩터와 편입비를 동시에 돌린다.",
           fontsize=8.2)
        tx(fig, X0 + .012, .840, "틸트 w' ∝ w x (1 + 0.3xz), z 클립 ±2 · 주간 · 비용 5bp 순액식 · 조달 실측 rf · 신호무효 위생 관문.",
           fontsize=7.4, color=INK2)
        tx(fig, X0 + .012, .820, "등록 전에 적대 검토 패널 4렌즈(과최적화·자료·구현·문헌)를 돌려 판정 설계를 고쳤다 — 2쪽.",
           fontsize=7.4, color=MUTED)

        tx(fig, X0, .775, "판정 — 증분 3대비 (계산 전에 얼린 주 판정)", fontsize=10.5, fontweight="bold")
        vr = [["V1  회전의 몫 (C - 상시모멘텀)", "%+.2f%%p · t %.2f" % (G["V1_rotation"]["ann_pp"], G["V1_rotation"]["t"]),
               "기각"],
              ["V2  틸트의 몫 (C - 밴드만)", "%+.2f%%p · t %.2f" % (G["V2_tilt_over_band"]["ann_pp"], G["V2_tilt_over_band"]["t"]),
               "통과"],
              ["V3  상호작용 (서로 갉나)", "%+.2f%%p" % G["V3_interaction"]["ann_pp"], "통과"]]
        table(fig, X0, .763, [.30, .24, .10], ["대비", "실측", "판정"], vr, row_h=.019,
              fs=7.8, hfs=7.2, aligns=["l", "l", "c"],
              cell_color=lambda r, c: (NEG if r == 0 else POS) if c == 2 else INK)
        tx(fig, X0, .676, "«멋있는 층»(레짐 회전)은 자기 시험에서 죽었다 — 상시 모멘텀 위에 연 -0.05%p. "
                          "살아남은 것은 결합 그 자체(모멘텀 틸트 x 편입비 밴드)다.",
           fontsize=8, color=INK2, fontweight="bold")

        tx(fig, X0, .655, "분해 — 어느 층이 뭘 보태나 (같은 격자·같은 기저·같은 비용)", fontsize=10.5, fontweight="bold")
        hdr = ["", "CAGR", "샤프", "MDD", "층의 뜻"]
        rows = [["R  순복제", "%.2f" % DEC["R"]["cagr"], "%.2f" % DEC["R"]["sharpe"], "%.2f" % DEC["R"]["mdd"], "출발점 — 벤더 비중 그대로"],
                ["B  밴드만", "%.2f" % DEC["B"]["cagr"], "%.2f" % DEC["B"]["sharpe"], "%.2f" % DEC["B"]["mdd"], "타이밍 층 (+1.50%p)"],
                ["NR 모멘텀틸트+밴드", "%.2f" % DEC["NR"]["cagr"], "%.2f" % DEC["NR"]["sharpe"], "%.2f" % DEC["NR"]["mdd"], "+ 팩터 층 (+1.12%p) — 회전만 뺀 판"],
                ["C  풍향계(회전 포함)", "%.2f" % DEC["C"]["cagr"], "%.2f" % DEC["C"]["sharpe"], "%.2f" % DEC["C"]["mdd"], "+ 회전 층 (-0.02%p) — 보탬 없음"],
                ["^NDX 실지수", "%.2f" % mb["cagr"], "%.2f" % mb["sharpe"], "%.2f" % mb["mdd"], "(배당보정 %.2f)" % mb["cagr_div_adj"]]]

        def cc(r, c):
            return {0: C_R, 1: C_B, 2: C_NR, 3: C_C, 4: C_BM}[r] if c == 0 else INK
        table(fig, X0, .643, [.20, .09, .08, .09, .38], hdr, rows, row_h=.0185,
              fs=7.6, hfs=7.2, aligns=["l", "r", "r", "r", "l"], cell_color=cc)

        tx(fig, X0, .530, "왜 «지수 대비 3문 통과»가 헤드라인이 아닌가", fontsize=10.5, fontweight="bold")
        for j, s in enumerate([
            "· C 는 3문(수익·샤프·MDD vs 나스닥100)을 전부 통과했다 — U1 은 배당보정행 기준으로도. 그러나 그 통과는",
            "  부품(밴드 = 이지스3)이 이미 예약해 둔 것이라 «B 승계 통과» 라벨이 붙는다 — 적대 검토가 등록 전에 지적했고,",
            "  이 가족(5회 시도)의 기저율은 «3회가 어떤 BM 읽기로든 3/3 통과»다. 통과 자체의 정보가치가 낮다.",
            "· 그래서 주 판정을 «이번 등록의 유일한 새 주장 = 회전이 뭘 보태나»로 얼렸고, 답은 «아무것도»였다.",
            "· V2 의 t 1.25 는 가족 보정 기준(본페로니 5건 = 2.58) 미달 — «선택과 구별 불가» 라벨. 방향만 믿는다.",
        ]):
            tx(fig, X0, .512 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .420, "예측 채점 — 계산 전에 적은 닫힌 구간 5건 중 2건 적중", fontsize=10.5, fontweight="bold")
        pr = [["P1 회전의 몫 ∈ [+0.10,+1.50]%p", "%+.2f%%p" % P["P1"]["got"], "빗나감 → 회전 기각"],
              ["P2 틸트의 몫 ∈ [+0.40,+2.00]%p", "%+.2f%%p" % P["P2"]["got"], "적중 (틸트1판 +0.79 와 정합)"],
              ["P3 오프 주 방어 ∈ [+2,+30]bp/주", "%.1fbp" % P["P3"]["got"], "빗나감 — 저변동 회전이 방어 국면에서 오히려 잃음"],
              ["P4 재진입 4주 누적 음수", "%+.1fbp (8회)" % P["P4"]["got"], "빗나감 — «꼭대기 매수» 기전이 틸트에선 재현 안 됨"],
              ["P5 상호작용 ≥ 0", "%+.2f%%p" % P["P5"]["got"], "적중 — 두 층이 서로 안 갉는다"]]
        table(fig, X0, .408, [.28, .13, .40], ["예측", "실측", "해석(등록에 미리 적은 문장)"], pr,
              row_h=.0185, fs=7.2, hfs=6.9, aligns=["l", "r", "l"],
              cell_color=lambda r, c: ((POS if r in (1, 4) else NEG) if c == 1 else INK))
        tx(fig, X0, .284, "P3·P4 의 빗나감이 이 측정의 수확이다: 저변동 «방어»는 하락장 한복판(2022)에서 밴드만 못했고,",
           fontsize=7.0, color=INK2)
        tx(fig, X0, .271, "재진입 창의 모멘텀 재매수는 비중 틸트에선 해롭지 않았다 — 둘 다 다음 설계의 입력이다.",
           fontsize=7.0, color=INK2)
        footer(fig, 1)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 2쪽 — 적대 검토와 위생 관문 ───────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "등록 전 적대 검토 — 4렌즈 병렬 패널이 설계를 고쳤다", fontsize=13, fontweight="bold")
        tx(fig, X0, .934, "5번째 시도라 과최적화 위험이 실재했다. 계산 전에 독립 검토자 4명(과최적화·자료·구현·문헌)을 병렬로 돌렸고, "
                          "치명 지적 전부를 등록에 반영한 뒤에야 얼렸다.", fontsize=7.6, color=INK2)
        rows2 = [
            ["과최적화", "«3문 통과는 부품이 예약해 둔 것 — 주 판정을 증분(회전의 몫)으로 옮겨라»",
             "판정 구조 교체 (V1/V2/V3)"],
            ["", "«위험-오프는 90주·사실상 2022 하나 — 오프 레그 단독 판정 금지, 상시-저변동 대조 추가»", "§0 명기 + LV 민감도"],
            ["자료", "«pit_px 엔터티 오염(LCID 상장 전 유사-정지가) — σ 눌려 저변동 최상위 둔갑»",
             "위생 관문: 0%비율·점프 → 신호 무효"],
            ["", "«σ 는 인접 페어만, 페어 ≥160 — 0% 채움·갭 넘김 금지(규칙에 따라 σ 4배 갈림)»", "§1 명문화 + 커버리지 로그"],
            ["구현", "«비용은 순액식 Σ|Δ(e·w)| — 분해식은 전환 주 과대계상» · «항등 3종을 assert 로»",
             "순액식 채택 · K=0⇒C≡B 등 3종 통과"],
            ["문헌", "«D-M 오적용 — 크래시는 숏 레그(우리엔 없음)·처방은 연속 스케일링»",
             "닻 재작성 + Asness 회의론 선등록"],
        ]
        table(fig, X0, .912, [.09, .52, .23], ["렌즈", "치명 지적(요지)", "반영"], rows2,
              row_h=.030, fs=6.9, hfs=6.9, aligns=["l", "l", "l"], zebra=True)

        tx(fig, X0, .690, "레짐 상태도", fontsize=10, fontweight="bold")
        for i2, (lab, col, y) in enumerate((("위험-온: ^NDX ≥ 200일선  →  모멘텀 틸트 + 편입비 110% (조달 rf)", POS, .664),
                                            ("위험-오프: ^NDX < 200일선  →  저변동 틸트 + 편입비 90% (현금 0%)", NEG, .642))):
            box(fig, X0, y - .004, .012, .014, col)
            tx(fig, X0 + .020, y + .008, lab, fontsize=7.8)
        tx(fig, X0, .620, "상태(레짐·팩터·편입비)는 한 함수에서 원자적으로 갱신 — 셋이 어긋나는 주가 없다. 전환 18회 · "
                          "전환 주 평균 회전 27% · 평시 4.1%.", fontsize=7.2, color=MUTED)

        tx(fig, X0, .586, "정직성 — 이 문서가 말하지 않는 것", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 위험-오프 표본은 90주/489주, 사실상 2022 한 에피소드가 지배한다 — 오프 레그의 어떤 결론도 약하다.",
            "· MOM↔온 / LOWVOL↔오프 배정은 2x2 조합 중 이 표본이 보상한 유일한 조합이었다 — 그래서 회전 기각이",
            "  «배정이 틀렸다»인지 «회전 자체가 무익하다»인지는 이 표본으로 못 가른다. Asness 회의론은 후자를 지지한다.",
            "· U1 저울은 생존 틸트 ~+0.9%p + 배당 기저 +0.8%p 만큼 우리 쪽으로 기울어 있다(승계 — 분해표는 상쇄됨).",
            "· 문헌 닻의 정확한 위치: D-M(2016)의 크래시는 12-2 WML 숏 레그의 옵션성 — 롱온리 틸트는 그 채널에 직접",
            "  노출되지 않는다. B-S(2015)의 처방은 연속 변동성 스케일링. 회전을 되살릴 길은 그 이식이지 MA200 이진이 아니다.",
            "· 기준 비중이 사내 DB(커밋 금지)라 러너가 재생산할 수 없다 — 얼린 측정. 전방 기록 0건.",
        ]):
            tx(fig, X0, .568 - j * .0138, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .460, "민감도 — 어느 설정에서도 그림이 같다", fontsize=10, fontweight="bold")
        hdr = ["변형", "CAGR", "샤프", "MDD", "vs 상시모멘텀"]
        sl = [["풍향계 기본", "%.2f" % DEC["C"]["cagr"], "%.2f" % DEC["C"]["sharpe"], "%.2f" % DEC["C"]["mdd"], "-0.05%p"]]
        for nm, lab in (("LV_always", "상시 저변동(회전 반대편)"), ("K015", "K=0.15"),
                        ("sig126", "σ창 126일"), ("monthly", "월간 리밸"),
                        ("cost20", "비용 20bp"), ("rf_p50", "조달 rf+50bp"), ("delay1", "체결 1일 지연")):
            v = SEN[nm]
            sl.append([lab, "%.2f" % v["cagr"], "%.2f" % v["sharpe"], "%.2f" % v["mdd"],
                       "%+.2f%%p" % v["vsNR_pp"]])
        table(fig, X0, .448, [.26, .09, .08, .09, .13], hdr, sl, row_h=.0165,
              fs=7.0, hfs=6.8, aligns=["l", "r", "r", "r", "r"])
        tx(fig, X0, .284, "8개 설정 전부에서 회전의 몫은 -2.84 ~ +0.27%p — σ창을 반으로 줄여도(+0.27) 회전이 살아나지 않는다.",
           fontsize=7.0, color=INK2)
        tx(fig, X0, .271, "상시 저변동(-2.84%p)은 명백히 나쁘다: 이 유니버스의 일꾼은 모멘텀이다.",
           fontsize=7.0, color=INK2)

        tx(fig, X0, .250, "이 검증 과정이 산 것", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 복잡한 층 하나(회전)를 실제 돈이 걸리기 전에 기각했다 — 백테스트가 좋아 보이는 조립을 걸러내는 것이",
            "  이 랩의 존재 이유고, 이번엔 등록 전 적대 검토가 판정 설계까지 고쳐 «가짜 통과»를 미리 차단했다.",
            "· 부산물 셋: pit_px 엔터티 오염 발견(위생 관문 신설) · 순액식 비용 규약 · 항등 검증 3종 — 이후 모든",
            "  비중 계열 측정의 기반이 된다.",
        ]):
            tx(fig, X0, .232 - j * .0145, s, fontsize=7.2, color=INK2)
        footer(fig, 2)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 3쪽 — 곡선 ────────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "성과 상세", fontsize=13, fontweight="bold")
        tx(fig, X0, .936, "누적 성과 (로그 · 100 출발) · 음영 = 위험-오프(200일선 아래)", fontsize=8, color=MUTED)
        ax = fig.add_axes([X0, .60, X1 - X0, .32])
        for key, vals, col, lab, lw in (("bm", dv_bm, C_BM, "^NDX 실지수", .9),
                                        ("R", V["R"]["dv"], C_R, "순복제", .8),
                                        ("B", V["B"]["dv"], C_B, "밴드만", 1.0),
                                        ("NR", V["NR"]["dv"], C_NR, "모멘텀틸트+밴드(회전 없음)", 1.4),
                                        ("C", V["C"]["dv"], C_C, "풍향계(회전 포함)", 1.4)):
            base = vals[0]
            ax.plot(XD, [v / base * 100 for v in vals], color=col, lw=lw, label=lab)
        for a, b in off_spans:
            ax.axvspan(dt.date.fromisoformat(a), dt.date.fromisoformat(b), color=NEG, alpha=.06, lw=0)
        ax.set_yscale("log")
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_yticks([100, 200, 400, 800])
        ax.set_yticklabels(["100", "200", "400", "800"], fontsize=7)
        ax.tick_params(axis="x", labelsize=7)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(LINE)
        ax.grid(axis="y", color=LINE, lw=.5, alpha=.7)
        ax.legend(loc="upper left", fontsize=7.2, frameon=False)
        ax.set_facecolor(PAPER)
        tx(fig, X0, .930, "", fontsize=6)

        tx(fig, X0, .555, "두 비율 곡선 — 이 보고서의 결론이 그림 두 장이다", fontsize=9, fontweight="bold")
        ax2 = fig.add_axes([X0, .40, X1 - X0, .135])
        r1 = [(c / n - 1) * 100 for c, n in zip(V["C"]["dv"], V["NR"]["dv"])]
        ax2.plot(XD, r1, color=C_C, lw=1.1)
        ax2.axhline(0, color=RULE, lw=.7)
        ax2.fill_between(XD, r1, 0, color=C_C, alpha=.10)
        ax2.tick_params(labelsize=6.6)
        for sp in ("top", "right"):
            ax2.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax2.spines[sp].set_color(LINE)
        ax2.set_facecolor(PAPER)
        ax2.text(.008, .82, "회전의 몫: 풍향계/상시모멘텀 (%)", transform=ax2.transAxes,
                 fontsize=7.2, color=C_C, fontweight="bold")
        tx(fig, X0, .376, "2020~22 에 +2.7%%p 벌었다가 2025~26 휩쏘에서 전부 뱉었다 — 끝값 %.1f%%, 순효과 연 -0.05%%p. "
                          "회전이 «가끔 맞는» 것과 «보태는» 것은 다르다." % r1[-1], fontsize=7.0, color=INK2)

        ax3 = fig.add_axes([X0, .21, X1 - X0, .135])
        r2 = [(n / b - 1) * 100 for n, b in zip(V["NR"]["dv"], V["B"]["dv"])]
        ax3.plot(XD, r2, color=C_NR, lw=1.1)
        ax3.axhline(0, color=RULE, lw=.7)
        ax3.fill_between(XD, r2, 0, color=C_NR, alpha=.10)
        ax3.tick_params(labelsize=6.6)
        for sp in ("top", "right"):
            ax3.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax3.spines[sp].set_color(LINE)
        ax3.set_facecolor(PAPER)
        ax3.text(.008, .82, "팩터 층의 몫: (모멘텀틸트+밴드)/밴드만 (%)", transform=ax3.transAxes,
                 fontsize=7.2, color=C_NR, fontweight="bold")
        tx(fig, X0, .186, "이쪽은 우상향 — 끝값 %.1f%%(연 ~+1.0%%p). 팩터 틸트는 일하고, 회전은 일하지 않았다. "
                          "2022 초·2025 봄의 되돌림(모멘텀 크래시)이 이 층의 구조적 약점으로 남는다." % r2[-1],
           fontsize=7.0, color=INK2)
        footer(fig, 3)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 4쪽 — 참고 3문·계보·다음 ──────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "참고 판정과 다음", fontsize=13, fontweight="bold")
        tx(fig, X0, .930, "사용자 3문 (vs 나스닥100 · 참고 — «B 승계 통과» 라벨)", fontsize=10, fontweight="bold")
        u = J["user3_ref"]
        ur = [["U1 수익(배당보정행 판정)", "%.2f%% > %.2f%%" % (u["U1_cagr_div_adj"]["strat"], u["U1_cagr_div_adj"]["bm_div_adj"]), "통과"],
              ["U2 샤프", "%.2f > %.2f" % (u["U2_sharpe"]["strat"], u["U2_sharpe"]["bm"]), "통과"],
              ["U3 MDD", "%.2f%% < %.2f%%" % (u["U3_mdd"]["strat"], u["U3_mdd"]["bm"]), "통과"]]
        table(fig, X0, .918, [.22, .30, .10], ["문", "실측", "판정"], ur, row_h=.018,
              fs=7.6, hfs=7.2, aligns=["l", "l", "c"],
              cell_color=lambda r, c: POS if c == 2 else INK)
        tx(fig, X0, .842, "통과는 사실이다 — 그러나 밴드(이지스3)가 이미 통과해 둔 문이라, 이 통과가 «회전이 좋다»의",
           fontsize=7.2, color=MUTED)
        tx(fig, X0, .829, "증거가 되지 않는다. 가족 기저율(5회 중 3회 통과)을 붙여 읽는 것이 등록의 약속이었다.",
           fontsize=7.2, color=MUTED)

        tx(fig, X0, .800, "계보 — 정확한 위치", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 직접 선행: Polk, Haghbin & de Longis (2020, JOIM) — 경기 레짐 기반 롱온리 5팩터 회전. 단 레짐 정의(거시지표)가",
            "  본 설계(가격 MA200)와 다르고 실무 연계 연구라 독립 검증이 얇다.",
            "· 완화 원용: Daniel & Moskowitz (2016) — 크래시는 WML 숏 레그의 옵션성(본 설계 미노출) · 상태변수는 24개월",
            "  약세 더미+사전분산(MA200 아님). Barroso & Santa-Clara (2015) — 처방은 연속 변동성 스케일링(본 설계 미채택).",
            "· Blitz & van Vliet (2007) — 저변동은 무조건부 이상현상 · 하락월 비대칭은 방향 근거일 뿐 조건부 회전 검증 아님.",
            "· 반대 문헌(선등록): Asness (2016) «Siren Song of Factor Timing» · Asness 외 (2017) — 이번 기각은 이 회의론과",
            "  정합하는 결과로 기록한다. (주: 본 설계의 MOM 은 dist200 — 문헌의 12-2 모멘텀과 동일하지 않다.)",
        ]):
            tx(fig, X0, .782 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .650, "그래서 지금 뭘 들 것인가", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 이 계열의 정직한 최종형은 «NR = 모멘텀 틸트 x 편입비 밴드»다 — CAGR 24.16 · 샤프 1.09 · MDD -34.2",
            "  (지수 19.80/0.96/-35.6). 이것이 «타이밍 x 팩터»의 검증된 조합이고, 회전이라는 장식만 뺀 것이다.",
            "· 단 이 수치도 승계 저울(생존 틸트 ~0.9%p·배당 0.8%p) 위에 있고, 팩터 층의 t(1.25)는 가족 보정 미달이다 —",
            "  전방 기록이 쌓이기 전까지 «후보»다.",
        ]):
            tx(fig, X0, .632 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .555, "다음 손잡이 — 순서대로", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "① 회전을 되살릴 유일한 정공법: 문헌 처방 그대로 «연속 변동성 스케일링»(B-S 2015)을 틸트 강도에 이식 —",
            "   이진 스위치가 아니라 K 를 실현변동성에 반비례시키는 것. 새 등록으로만, Asness 회의론 선반영.",
            "② 팩터 층의 t 를 올리는 정공법: 서로 안 겹치는 둘째 틸트 축(거장 매집 등) 추가 — Grinold 산수. 새 등록.",
            "③ 전방 기록: 주간 시계열이 data/wvane.json 에 남는다 — 다음 재진입 이벤트가 P4 의 표본 외 시험이 된다.",
            "④ 상장폐지 조정가 벤더(EODHD)로 생존 틸트 0.9%p 를 0 에 붙이는 것 — 계열 전체의 저울을 바로잡는다.",
        ]):
            tx(fig, X0, .537 - j * .0145, s, fontsize=7.2, color=INK2)
        footer(fig, 4)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
