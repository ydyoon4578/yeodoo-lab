# -*- coding: utf-8 -*-
"""build/report_aegis_pdf.py — 이지스 방패·돛 전략 보고서 → build/REPORT-2026-08-20-AEGIS.pdf

이름 확정(2026-08-20 사용자 지시 «특성을 살려서 이름 제대로»):
  이지스 방패(AEGIS Shield) = 2판 — 200일선 아래 편입 50%. 하락월에 이기는 방어형.
  이지스 돛(AEGIS Sail)     = 3판 — 편입비 밴드 110/90. 상승월에 이기는 순풍형.

얼린 측정(data/aegis2.json·aegis3.json · PREREG-2026-08-19-AEGIS2/3)의 보고서다 —
수치는 엔진 재실행(결정적)으로 파생하고, 관문·예측·민감도는 얼린 JSON 에서 그대로 읽는다.
판형·색·폰트는 style_top_pdf 를 따른다.

    python build/report_aegis_pdf.py
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
OUT = os.path.join(HERE, "REPORT-2026-08-20-AEGIS.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST
from style_top_pdf import tx, hline, box, table
from aegis_backtest import week_ends, Sig, metrics, bench_track
from aegis2_backtest import engine2
from aegis3_backtest import engine3, load_rf

ST.require_draw()
X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2
CHAMP, RP, MARG, GROUND = ST.CHAMP, ST.RP, ST.MARG, ST.GROUND

C_SH, C_SA, C_SPX, C_NDX = POS, MARG, CHAMP, RP     # 방패·돛·SPX·NDX
TOTAL = 5


def light_load(end):
    """얼린 측정과 같은 격자 — end(정본 span 끝) 이후는 자른다. 밤새 하루가 더
    붙은 격자로 다시 재면 보고서 수치가 정본과 어긋난다(실제로 그랬다)."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dts = [d for d in st["pxd_dates"] if d <= end]
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bench = {}
    for key in ("spx", "ndx"):
        bmap = dict(zip(B["dates"], B["series"][key]["px"]))
        bench[key] = [bmap.get(d) for d in dts]
    return dts, bench


def footer(fig, page):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .027, "이지스 전략 보고서 · 사전등록 PREREG-2026-08-19-AEGIS2/3(계산 전 커밋) · "
                      "대조군은 가격지수(PR) · 비용 편도 5bp · 조달 실측 rf(FRED DGS3MO)",
       fontsize=6.4, color=MUTED)
    tx(fig, X0, .019, "종목·지수 배당 기저 차이는 본문 배당보정행 참조 · 현금 수익 0% 보수 가정 · "
                      "전 구간 백테스트 — 전방 기록 0건이라는 사실이 이 문서에서 가장 중요한 한 줄이다",
       fontsize=6.0, color=NEG)
    tx(fig, X1, .027, "%d / %d · %s" % (page, TOTAL, dt.date.today().isoformat()),
       fontsize=6.4, color=MUTED, ha="right")


def new_page():
    return plt.figure(figsize=(8.27, 11.69))


def monthly_of(DD, vals):
    last = {}
    for d, v in zip(DD, vals):
        last[d[:7]] = v
    ms = sorted(last)
    return {b: last[b] / last[a] - 1 for a, b in zip(ms, ms[1:])}


def yearly_of(DD, vals):
    last = {}
    for d, v in zip(DD, vals):
        last[d[:4]] = v
    ys = sorted(last)
    out, prev = {}, vals[0]
    for y in ys:
        out[y] = (last[y] / prev - 1) * 100
        prev = last[y]
    return out


def dd_series(vals):
    peak, out = vals[0], []
    for v in vals:
        peak = max(peak, v)
        out.append((v / peak - 1) * 100)
    return out


def main() -> int:
    J2 = json.load(io.open(os.path.join(DATA, "aegis2.json"), encoding="utf-8"))
    J3 = json.load(io.open(os.path.join(DATA, "aegis3.json"), encoding="utf-8"))
    dts, bench = light_load(J2["span"][1])
    we = week_ends(dts)
    bsig = Sig(bench, len(dts))
    rf = load_rf()
    V2 = engine2(dts, bench, we, bsig)
    V3 = engine3(dts, bench, we, bsig, rf)
    for tag, V, J in (("방패", V2, J2), ("돛", V3, J3)):
        m_chk = metrics(V["daily_d"], V["daily_v"], V["wk_ret"])
        if abs(m_chk["cagr"] - J["strat"]["cagr"]) > .005:
            raise SystemExit("%s 재계산이 정본과 어긋난다: %.2f vs %.2f — 격자 절단을 확인하라"
                             % (tag, m_chk["cagr"], J["strat"]["cagr"]))

    DD = V2["daily_d"]
    d2i = {d: i for i, d in enumerate(dts)}
    NAV = {"sh": V2["daily_v"], "sa": V3["daily_v"],
           "spx": [bench["spx"][d2i[d]] for d in DD],
           "ndx": [bench["ndx"][d2i[d]] for d in DD]}
    XD = [dt.date.fromisoformat(d) for d in DD]

    MET = {"sh": metrics(DD, NAV["sh"], V2["wk_ret"]),
           "sa": metrics(DD, NAV["sa"], V3["wk_ret"])}
    for key in ("spx", "ndx"):
        dd_, dv_, wk_ = bench_track(dts, bench, key, DD, we)
        MET[key] = metrics(dd_, dv_, wk_)

    M = {k: monthly_of(DD, v) for k, v in NAV.items()}
    months = sorted(M["ndx"])
    Y = {k: yearly_of(DD, v) for k, v in NAV.items()}
    years = sorted(Y["ndx"])

    def winrate(s, b):
        w = sum(1 for m in months if M[s][m] >= M[b][m])
        dn = [m for m in months if M[b][m] < 0]
        up = [m for m in months if M[b][m] >= 0]
        wd = sum(1 for m in dn if M[s][m] >= M[b][m])
        wu = sum(1 for m in up if M[s][m] >= M[b][m])
        return (100.0 * w / len(months), 100.0 * wd / len(dn), 100.0 * wu / len(up))

    WR = {(s, b): winrate(s, b) for s in ("sh", "sa") for b in ("spx", "ndx")}

    def locate(w0, w1):
        idx = [i for i, d in enumerate(DD) if w0 <= d <= w1]
        tr = min(idx, key=lambda i: NAV["ndx"][i])
        pk = max([i for i in idx if i <= tr], key=lambda i: NAV["ndx"][i])
        return pk, tr

    seg = lambda k, a, b: (NAV[k][b] / NAV[k][a] - 1) * 100
    EP = [("2015 위안화 쇼크", "2015-07-01", "2015-10-01"),
          ("2018 Q4 긴축발작", "2018-09-01", "2018-12-31"),
          ("2020 코로나 급락", "2020-02-01", "2020-04-01"),
          ("2022 약세장", "2021-11-01", "2023-01-05"),
          ("2025 관세 쇼크", "2025-02-01", "2025-06-01"),
          ("2026 조정", "2026-01-01", "2026-05-31")]
    ep_rows = []
    ep_ix = {}
    for name, w0, w1 in EP:
        pk, tr = locate(w0, w1)
        ep_ix[name] = (pk, tr)
        ep_rows.append([name, "%s ~ %s" % (DD[pk], DD[tr])]
                       + ["%+.1f" % seg(k, pk, tr) for k in ("ndx", "spx", "sh", "sa")])
    REC = [("코로나 회복", "2020 코로나 급락", "2020-12-31"),
           ("2022 저점 이후", "2022 약세장", "2023-12-29"),
           ("2025 저점 이후", "2025 관세 쇼크", "2025-12-31"),
           ("2026 저점 이후", "2026 조정", "2026-08-18")]
    rec_rows = []
    for name, epn, end in REC:
        _pk, tr = ep_ix[epn]
        ie = max(i for i, d in enumerate(DD) if d <= end)
        rec_rows.append([name, "%s ~ %s" % (DD[tr], DD[ie])]
                        + ["%+.1f" % seg(k, tr, ie) for k in ("ndx", "spx", "sh", "sa")])

    dn2 = J2["half_periods"]

    with PdfPages(OUT) as pdf:
        # ── 1쪽 — 표지·요약 ────────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "이지스 전략 보고서", fontsize=17, fontweight="bold")
        tx(fig, X0, .932, "방패(Shield) · 돛(Sail) — NDX 코어 x 200일선 레짐의 두 변형",
           fontsize=10, color=INK2)
        tx(fig, X1, .955, "2015-01 ~ 2026-08 · 주간 판정 · 사전등록 측정", fontsize=7.5,
           color=MUTED, ha="right")
        hline(fig, X0, X1, .922, RULE, 1.0)

        cw = (X1 - X0 - .02) / 2
        for i, (key, nm, sub, col, jd) in enumerate((
                ("sh", "이지스 방패  AEGIS Shield", "200일선 아래면 편입 50% — 낙폭을 접는 방어형", C_SH, J2),
                ("sa", "이지스 돛  AEGIS Sail", "편입비 밴드 110/90 — 순풍에 돛을 더 펴는 공격형", C_SA, J3))):
            x = X0 + i * (cw + .02)
            box(fig, x, .715, cw, .195, GROUND, ec=LINE, lw=.8)
            box(fig, x, .895, cw, .015, col, z=1)
            tx(fig, x + .012, .885, nm, fontsize=11, fontweight="bold")
            tx(fig, x + .012, .864, sub, fontsize=7.4, color=INK2)
            m = MET[key]
            rows = [("CAGR", "%.2f%% (배당보정 %.2f)" % (m["cagr"], jd["strat"]["cagr_div_adj"] if "strat" in jd else m["cagr"])),
                    ("샤프", "%.2f" % m["sharpe"]),
                    ("최대낙폭", "%.2f%%" % m["mdd"]),
                    ("연변동성", "%.2f%%" % m["vol"])]
            yy = .845
            for lab, val in rows:
                tx(fig, x + .012, yy, lab, fontsize=7.6, color=MUTED)
                tx(fig, x + .095, yy, val, fontsize=7.6, fontweight="bold")
                yy -= .0165
            verd = ("선언 BM(S&P500) 3문 전부 통과 - MDD -25%의 방어" if key == "sh"
                    else "나스닥100 상대 3문 전부 통과 - CAGR +1.06%p")
            tx(fig, x + .012, .776, "판정(사용자 6문)", fontsize=7.2, color=MUTED)
            tx(fig, x + .012, .762, verd, fontsize=7.6, color=col, fontweight="bold")
            wr_n = WR[(key, "ndx")]
            tx(fig, x + .012, .744, "월별 승률(vs NDX): 전체 %.0f%% · 하락월 %.0f%% · 상승월 %.0f%%"
               % wr_n, fontsize=7.2, color=INK2)

        tx(fig, X0, .700, "무엇이 다른가", fontsize=10.5, fontweight="bold")
        hdr = ["", "이지스 방패 (2판)", "이지스 돛 (3판)"]
        rows = [
            ["보유 코어", "^NDX (실물 QQQ)", "^NDX (실물 QQQ + 선물 오버레이)"],
            ["200일선 위", "편입 100%", "편입 110% (조달 실측 rf 차감)"],
            ["200일선 아래", "편입 50%", "편입 90%"],
            ["성격", "하락월에 이긴다 (vs NDX 68%)", "상승월에 이긴다 (vs NDX 82%)"],
            ["급락장", "낙폭 5~11%p 완충", "지수보다 0.3~0.6%p 더 아프다"],
            ["회복장", "10~15%p 지각", "네 번의 회복 전부 지수 이상"],
            ["선언 BM 판정", "S&P500 상대 3/3 통과", "나스닥100 상대 3/3 통과"],
            ["전체 6문", "5/6 (CAGR>NDX 미달 -1.35%p)", "5/6 (MDD<SPX 미달 0.41%p)"],
        ]
        table(fig, X0, .688, [.16, .36, .36], hdr, rows, row_h=.0175, fs=7.4, hfs=7.2,
              aligns=["l", "l", "l"], zebra=True)

        tx(fig, X0, .512, "정직성 — 계산 전에 등록한 것들", fontsize=10.5, fontweight="bold")
        for j, s in enumerate([
            "· 채점 기준은 사용자 정의(2026-08-19): BM 대비 수익·샤프·MDD. 규칙·예측·민감도를 계산 전에 커밋했다",
            "  (PREREG-2026-08-19-AEGIS2/3). 예측 적중 — 방패 4/5 · 돛 4/5. 미달 문은 그대로 실었고 재채점하지 않았다.",
            "· 사용자 기준으로 3번째 시도까지 갔다(1판 기각 포함) — 다중검정 부담은 세 번째 목록(e-aegis1~3)에 기록.",
            "· 이것은 알파가 아니라 배분 설계다: 방패의 vs NDX 주간 초과 t -0.94, 돛 +1.68. 성과의 원천은 NDX 의",
            "  성장 기울기와 꼬리 절단이지 종목 선택이 아니다 (1판 분해에서 선택 다리의 PIT 우위 없음을 확인).",
            "· 200일선 방패는 3주짜리 급락(코로나)을 못 피한다 — 값어치는 긴 약세장(2022)과 회복 구간에서 나온다.",
            "· 배당 기저: 대조군은 가격지수라 SPX +1.8%p/yr · NDX +0.8%p/yr 과소 — 배당보정 후에도 판정 동일.",
            "· 6/6 경계선은 두 판 사이를 지난다(방어만 100/90: U3 통과·U4 -0.23%p 미달) — 그 사이 상수를 표본을",
            "  보고 고르는 것은 조율이라 하지 않았다. 전방 기록이 진짜 판정이다.",
        ]):
            tx(fig, X0, .494 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .340, "한눈 성과표", fontsize=10.5, fontweight="bold")
        hdr = ["", "CAGR", "배당보정", "샤프", "MDD", "연변동성"]
        rows = [["이지스 방패", "%.2f%%" % MET["sh"]["cagr"], "%.2f%%" % J2["strat"]["cagr_div_adj"],
                 "%.2f" % MET["sh"]["sharpe"], "%.2f%%" % MET["sh"]["mdd"], "%.2f%%" % MET["sh"]["vol"]],
                ["이지스 돛", "%.2f%%" % MET["sa"]["cagr"], "%.2f%%" % J3["strat"]["cagr_div_adj"],
                 "%.2f" % MET["sa"]["sharpe"], "%.2f%%" % MET["sa"]["mdd"], "%.2f%%" % MET["sa"]["vol"]],
                ["S&P500", "%.2f%%" % MET["spx"]["cagr"], "%.2f%%" % J2["bench"]["spx"]["cagr_div_adj"],
                 "%.2f" % MET["spx"]["sharpe"], "%.2f%%" % MET["spx"]["mdd"], "%.2f%%" % MET["spx"]["vol"]],
                ["나스닥100", "%.2f%%" % MET["ndx"]["cagr"], "%.2f%%" % J2["bench"]["ndx"]["cagr_div_adj"],
                 "%.2f" % MET["ndx"]["sharpe"], "%.2f%%" % MET["ndx"]["mdd"], "%.2f%%" % MET["ndx"]["vol"]]]

        def cc(r, c):
            return {0: C_SH, 1: C_SA, 2: C_SPX, 3: C_NDX}[r] if c == 0 else INK
        table(fig, X0, .328, [.16, .12, .13, .10, .11, .12], hdr, rows, row_h=.0165,
              fs=7.6, hfs=7.2, aligns=["l", "r", "r", "r", "r", "r"], cell_color=cc)
        tx(fig, X0, .238, "현재 상태(2026-08-14 주말): 200일선 위 — 방패 100% · 돛 110%",
           fontsize=7.6, color=INK2)
        footer(fig, 1)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 2쪽 — 누적 성과·낙폭 ──────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "누적 성과와 낙폭", fontsize=13, fontweight="bold")
        tx(fig, X0, .936, "음영 = 200일선 아래(방어 구간) · 세로축 로그 · 100 에서 출발",
           fontsize=7.4, color=MUTED)
        ax = fig.add_axes([X0, .55, X1 - X0, .36])
        for k, col, lab, lw in (("spx", C_SPX, "S&P500", .9), ("ndx", C_NDX, "나스닥100", .9),
                                ("sh", C_SH, "이지스 방패", 1.5), ("sa", C_SA, "이지스 돛", 1.5)):
            base = NAV[k][0]
            ax.plot(XD, [v / base * 100 for v in NAV[k]], color=col, lw=lw, label=lab)
        for a, b in dn2:
            b2 = b[:-1] if b.endswith("~") else b
            ax.axvspan(dt.date.fromisoformat(a), dt.date.fromisoformat(b2),
                       color=NEG, alpha=.06, lw=0)
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

        tx(fig, X0, .50, "고점 대비 낙폭(%)", fontsize=9.5, fontweight="bold")
        ax2 = fig.add_axes([X0, .16, X1 - X0, .30])
        for k, col, lab, lw in (("ndx", C_NDX, "나스닥100", .8), ("spx", C_SPX, "S&P500", .8),
                                ("sa", C_SA, "이지스 돛", 1.3), ("sh", C_SH, "이지스 방패", 1.3)):
            ax2.plot(XD, dd_series(NAV[k]), color=col, lw=lw, label=lab)
        ax2.axhline(MET["spx"]["mdd"], color=C_SPX, lw=.6, ls=":", alpha=.8)
        ax2.axhline(MET["ndx"]["mdd"], color=C_NDX, lw=.6, ls=":", alpha=.8)
        ax2.tick_params(labelsize=7)
        for sp in ("top", "right"):
            ax2.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax2.spines[sp].set_color(LINE)
        ax2.grid(axis="y", color=LINE, lw=.5, alpha=.7)
        ax2.legend(loc="lower left", fontsize=7.5, frameon=False, ncol=4)
        ax2.set_facecolor(PAPER)
        tx(fig, X0, .112, "점선 = 두 지수의 전 구간 최대낙폭(SPX -33.9 · NDX -35.6). 방패의 골(-25.3)은 "
                          "두 선 위에 뜨고, 돛(-34.3)은 SPX 선을 0.4%p 만큼 뚫는다 — 그게 6문 중 남은 한 문이다.",
           fontsize=7.0, color=INK2)
        footer(fig, 2)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 3쪽 — 연도별·월별 ─────────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "연도별 수익률과 월별 승률", fontsize=13, fontweight="bold")
        ax = fig.add_axes([X0, .64, X1 - X0, .27])
        import numpy as np
        xs = np.arange(len(years))
        wdt = .2
        for j, (k, col, lab) in enumerate((("sh", C_SH, "방패"), ("sa", C_SA, "돛"),
                                           ("spx", C_SPX, "S&P500"), ("ndx", C_NDX, "나스닥100"))):
            ax.bar(xs + (j - 1.5) * wdt, [Y[k][y] for y in years], wdt,
                   color=col, label=lab, zorder=2)
        ax.set_xticks(xs)
        ax.set_xticklabels([y[2:] for y in years], fontsize=7.5)
        ax.tick_params(axis="y", labelsize=7)
        ax.axhline(0, color=RULE, lw=.8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(LINE)
        ax.grid(axis="y", color=LINE, lw=.5, alpha=.7)
        ax.legend(loc="upper left", fontsize=7.5, frameon=False, ncol=4)
        ax.set_facecolor(PAPER)
        tx(fig, X0, .935, "연도별 수익률(%) — 2026 은 8월 18일까지", fontsize=7.4, color=MUTED)

        hdr = ["연도"] + [y for y in years]
        rows = []
        for k, nm in (("sh", "방패"), ("sa", "돛"), ("spx", "S&P500"), ("ndx", "나스닥100")):
            rows.append([nm] + ["%+.0f" % Y[k][y] for y in years])

        def cc3(r, c):
            if c == 0:
                return {0: C_SH, 1: C_SA, 2: C_SPX, 3: C_NDX}[r]
            v = float(rows[r][c])
            return NEG if v < 0 else INK
        w0 = .085
        table(fig, X0, .615, [w0] + [(X1 - X0 - w0) / len(years)] * len(years), hdr, rows,
              row_h=.0165, fs=6.7, hfs=6.4, aligns=["l"] + ["r"] * len(years), cell_color=cc3)

        tx(fig, X0, .50, "월별 승률 — 139개월 (2015-02 ~ 2026-08)", fontsize=10.5, fontweight="bold")
        hdr = ["", "vs S&P500 전체", "하락월", "상승월", "vs 나스닥100 전체", "하락월", "상승월"]
        rows = []
        for k, nm in (("sh", "이지스 방패"), ("sa", "이지스 돛")):
            a = WR[(k, "spx")]; b = WR[(k, "ndx")]
            rows.append([nm, "%.0f%%" % a[0], "%.0f%%" % a[1], "%.0f%%" % a[2],
                         "%.0f%%" % b[0], "%.0f%%" % b[1], "%.0f%%" % b[2]])
        table(fig, X0, .488, [.16, .15, .10, .10, .17, .10, .10], hdr, rows,
              row_h=.018, fs=7.6, hfs=6.8, aligns=["l"] + ["r"] * 6)

        tx(fig, X0, .425, "vs 나스닥100 승률 프로필", fontsize=8.5, fontweight="bold")
        tx(fig, X0, .410, "같은 코어·같은 신호인데 버는 달이 정반대다 — 방패는 지수가 빠지는 달의 68%를, "
                          "돛은 오르는 달의 82%를 이긴다. 진한 막대가 각 전략의 주특기다.",
           fontsize=7.2, color=INK2)
        ax3 = fig.add_axes([X0, .155, X1 - X0, .225])
        cats = ["방패 vs NDX\n하락월", "방패 vs NDX\n상승월", "돛 vs NDX\n하락월", "돛 vs NDX\n상승월"]
        vals = [WR[("sh", "ndx")][1], WR[("sh", "ndx")][2], WR[("sa", "ndx")][1], WR[("sa", "ndx")][2]]
        cols = [C_SH, C_SH, C_SA, C_SA]
        bars = ax3.bar(range(4), vals, .55, color=cols, zorder=2)
        bars[1].set_alpha(.45); bars[2].set_alpha(.45)
        ax3.axhline(50, color=RULE, lw=.8, ls="--")
        for i2, v in enumerate(vals):
            ax3.text(i2, v + 1.5, "%.0f%%" % v, ha="center", fontsize=8.5, fontweight="bold")
        ax3.set_xticks(range(4))
        ax3.set_xticklabels(cats, fontsize=8)
        ax3.set_ylim(0, 100)
        ax3.tick_params(axis="y", labelsize=7)
        for sp in ("top", "right"):
            ax3.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax3.spines[sp].set_color(LINE)
        ax3.set_facecolor(PAPER)

        footer(fig, 3)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 4쪽 — 위기·회복·편입비 ────────────────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "특이 시점 상대 성과", fontsize=13, fontweight="bold")
        tx(fig, X0, .936, "구간은 창 안에서 나스닥100 의 실제 고점-저점을 데이터로 특정 · 단위 %",
           fontsize=7.4, color=MUTED)
        hdr = ["급락 구간", "날짜(고점~저점)", "나스닥100", "S&P500", "방패", "돛"]

        def cc4(r, c):
            if c < 2:
                return INK
            try:
                return NEG if float(ep_rows[r][c]) < 0 else POS
            except ValueError:
                return INK
        y_end = table(fig, X0, .924, [.20, .26, .105, .105, .105, .105], hdr, ep_rows,
                      row_h=.0185, fs=7.4, hfs=6.9, aligns=["l", "l", "r", "r", "r", "r"],
                      cell_color=cc4, zebra=True)

        hdr = ["회복 구간(저점 이후)", "날짜", "나스닥100", "S&P500", "방패", "돛"]

        def cc5(r, c):
            if c < 2:
                return INK
            try:
                return NEG if float(rec_rows[r][c]) < 0 else POS
            except ValueError:
                return INK
        table(fig, X0, y_end - .028, [.20, .26, .105, .105, .105, .105], hdr, rec_rows,
              row_h=.0185, fs=7.4, hfs=6.9, aligns=["l", "l", "r", "r", "r", "r"],
              cell_color=cc5, zebra=True)
        yc = y_end - .155
        for j, sline in enumerate([
            "방패의 값어치는 급락의 한복판에 있다 — 코로나 -22.9 로 두 지수보다 얕고, 2022 에 +11.2%p, 관세 쇼크에 +6.8%p.",
            "돛은 급락에선 지수보다 조금 더 아프다(110% 진입분). 값어치는 회복 구간에서 나온다 — 네 번의 회복 전부 지수 이상.",
            "참고: 코로나 급락에선 S&P500(-31.9)이 나스닥100(-28.0)보다 더 빠졌다 — 위기의 종류에 따라 두 지수의 역할이 뒤집힌다.",
        ]):
            tx(fig, X0, yc - j * .0145, sline, fontsize=7.2,
               color=(MUTED if j == 2 else INK2))

        tx(fig, X0, .47, "편입비 타임라인", fontsize=10.5, fontweight="bold")
        for j, (V, col, nm, ylo, yhi, yt) in enumerate((
                (V2, C_SH, "이지스 방패 (100 / 50)", 30, 120, [50, 100]),
                (V3, C_SA, "이지스 돛 (110 / 90)", 80, 120, [90, 110]))):
            axp = fig.add_axes([X0, .31 - j * .125, X1 - X0, .105])
            wd = [dt.date.fromisoformat(d) for d in V["wk_d"]]
            ee = [x * 100 for x in V["wk_e"]]
            axp.step(wd, ee, where="post", color=col, lw=1.1)
            axp.fill_between(wd, ee, ylo, step="post", color=col, alpha=.10)
            axp.set_ylim(ylo, yhi)
            axp.set_yticks(yt)
            axp.set_yticklabels(["%d%%" % v for v in yt], fontsize=6.6)
            axp.tick_params(axis="x", labelsize=6.6)
            if j == 0:
                axp.set_xticklabels([])
            for sp in ("top", "right"):
                axp.spines[sp].set_visible(False)
            for sp in ("left", "bottom"):
                axp.spines[sp].set_color(LINE)
            axp.set_facecolor(PAPER)
            axp.text(.005, .84, nm, transform=axp.transAxes, fontsize=7.4,
                     color=col, fontweight="bold")
        tx(fig, X0, .165, "스위치는 11.5년에 12번 — 2022 는 1년 내내 방어(2022-01 ~ 2023-01), 코로나는 4주뿐이다. "
                          "200일선은 긴 약세장을 잡는 신호지 3주 급락을 잡는 신호가 아니다.",
           fontsize=7.2, color=INK2)
        footer(fig, 4)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

        # ── 5쪽 — 방법·사전등록 궤적·민감도 ──────────────────────────
        fig = new_page()
        tx(fig, X0, .955, "방법과 사전등록 궤적", fontsize=13, fontweight="bold")
        tx(fig, X0, .930, "규칙 전문", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 판정·체결: 매주 마지막 거래일 종가(close-to-close · 랩 전역 관행). 신호는 ^NDX 종가 vs 200거래일 단순평균.",
            "· 방패: 200일선 위 100% / 아래 50%. 돛: 위 110% / 아래 90% — 초과분 10%엔 실측 rf(FRED DGS3MO,",
            "  월복리를 주 단위 환산)를 조달비로 차감(측정 결과 연 0.17%p). 90% 구간의 현금 10%는 0%로 논다(보수 방향).",
            "· 비용: 편도 5bp x 노출 변경분. 스위치 12번/11.5년이라 비용을 20bp 로 올려도 판정이 안 바뀐다.",
            "· NAV 일간 계산 · 샤프 = 주간수익 연율화(rf 0 양쪽 동일) · MDD = 일간 종가 기준.",
        ]):
            tx(fig, X0, .912 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .825, "세 번의 등록 — 미달 기록까지 전부", fontsize=10, fontweight="bold")
        hdr = ["판", "규칙", "판정(사용자 6문)", "기록"]
        rows = [
            ["1판", "dist200 상위25 EW x 전량 이탈", "2/6 기각", "선택 다리 PIT 우위 없음 · 전량 이탈은 V-회복에 연 3.8%p"],
            ["2판 = 방패", "NDX x 200일선 아래 50%", "5/6 · S&P500 상대 3/3", "예측 4/5 적중 · U4(CAGR>NDX) -1.35%p 미달"],
            ["3판 = 돛", "NDX x 편입비 110/90", "5/6 · 나스닥100 상대 3/3", "예측 4/5 적중 · U3(MDD<SPX) 0.41%p 미달"],
        ]
        y_end = table(fig, X0, .812, [.07, .25, .19, .37], hdr, rows, row_h=.0185,
                      fs=7.2, hfs=6.9, aligns=["l", "l", "l", "l"], zebra=True)
        tx(fig, X0, y_end - .008, "세 판 모두 규칙·채점·예측을 계산 전에 커밋했고(사전등록), 결과가 나온 뒤 문턱이나 "
                                  "상수를 바꾼 적이 없다. 기각된 1판도 세 번째 목록(e-aegis1)에 남긴다.",
           fontsize=7.0, color=MUTED)

        tx(fig, X0, .700, "민감도 — 상수 하나에 매달린 결과가 아닌가", fontsize=10, fontweight="bold")
        hdr = ["변형", "CAGR", "샤프", "MDD"]
        r2 = [["방패 기본 (100/50 · 주간 · 5bp)", "%.2f" % MET["sh"]["cagr"],
               "%.2f" % MET["sh"]["sharpe"], "%.2f" % MET["sh"]["mdd"]]]
        for nm, lab in (("floor0", "바닥 0% (Faber 원형)"), ("floor25", "바닥 25%"),
                        ("monthly", "월간 판정"), ("shield_spx", "신호 ^GSPC"),
                        ("cost20", "비용 20bp")):
            v = J2["sens"][nm]
            r2.append([lab, "%.2f" % v["cagr"], "%.2f" % v["sharpe"], "%.2f" % v["mdd"]])
        y_end = table(fig, X0, .688, [.24, .065, .065, .065], hdr, r2, row_h=.0155,
                      fs=6.8, hfs=6.6, aligns=["l", "r", "r", "r"])
        r3 = [["돛 기본 (110/90 · 주간 · 5bp)", "%.2f" % MET["sa"]["cagr"],
               "%.2f" % MET["sa"]["sharpe"], "%.2f" % MET["sa"]["mdd"]]]
        for nm, lab in (("defense_only", "방어만 (100/90)"), ("lever_only", "레버리지만 (110/100)"),
                        ("monthly", "월간 판정"), ("shield_spx", "신호 ^GSPC"),
                        ("cost20", "비용 20bp"), ("fin_x2", "조달 2배")):
            v = J3["sens"][nm]
            r3.append([lab, "%.2f" % v["cagr"], "%.2f" % v["sharpe"], "%.2f" % v["mdd"]])
        table(fig, X0 + .465, .688, [.21, .065, .065, .065], hdr, r3, row_h=.0155,
              fs=6.8, hfs=6.6, aligns=["l", "r", "r", "r"])

        tx(fig, X0, .50, "한계 — 이 문서가 말하지 않는 것", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 전방 기록이 0건이다. 2015~2026 은 NDX 의 황금기였고, 성장주 장기 침체(2000~2013 같은)가 오면",
            "  NDX 코어라는 선택 자체가 벌을 받는다 — 200일선 방패가 완충하지만 코어의 기울기는 못 바꾼다.",
            "· 방패는 알파가 아니다(vs NDX 주간 t -0.94). 돛의 틸트는 양의 결이 있으나(t +1.68) 관행 문턱(2) 미만.",
            "· 급락 인식이 주 단위라 갭 하락은 그대로 맞는다. 체결을 다음 주 시가로 늦추면 미끄러짐이 더해진다.",
            "· 90% 구간 현금의 기회수익(2022 이후 rf 4~5%)을 0 으로 눌렀다 — 실전이 백테스트보다 유리한 방향.",
            "· 6/6(두 지수 동시 석권)은 이 십년에선 두 판 사이 어딘가의 상수를 요구한다 — 그 상수를 표본에서",
            "  고르면 숫자는 나오지만 의미가 없다. 필요하면 전방에서 판정할 새 등록으로만 간다.",
        ]):
            tx(fig, X0, .482 - j * .0145, s, fontsize=7.2, color=INK2)

        tx(fig, X0, .360, "쓰임새 제안", fontsize=10, fontweight="bold")
        for j, s in enumerate([
            "· 폭락을 견디는 것이 우선인 계좌(인출이 있는 계좌·심리적 손절 위험) → 방패.",
            "· 지수를 놓치지 않는 것이 우선인 계좌(장기 적립·추적오차 허용) → 돛.",
            "· 반반 배분 시 산술 평균으로 CAGR ~18% · MDD ~-30% 근방이 기대되나, 이 조합은 별도 등록 없이는",
            "  공식 수치로 말하지 않는다 — 지금까지의 규율 그대로다.",
        ]):
            tx(fig, X0, .342 - j * .0145, s, fontsize=7.2, color=INK2)
        footer(fig, 5)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
