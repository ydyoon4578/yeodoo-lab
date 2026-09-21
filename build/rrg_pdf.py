# -*- coding: utf-8 -*-
"""build/rrg_pdf.py — RRG 4분면 그림 → data/rrg.pdf

자료는 build/rrg.py 가 낸 data/_rrg.json 하나뿐이다. 여기서 아무것도 계산하지 않는다.

🚨 이 그림은 **기각된 것**이다(PREREG-2026-09-22-RRG-RESULT · F3).
  회전이 산식의 성질이라는 사실을 그림 위에 크게 적는다 — 안 적으면 로테이션 규칙으로 읽힌다.

⚠ 맑은 고딕에 없는 글자: ✓ ✗ ⚠ 🚨 U+2212(진짜 빼기표). «!!» 와 하이픈으로 눕힌다.
  있는 글자: ▲ ▼ → ← · — ± ≥ ≤ « »

  python build/rrg_pdf.py [--png]
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import matplotlib
matplotlib.use("Agg")
# 🚨 축 눈금의 음수는 matplotlib 이 기본으로 U+2212(진짜 빼기표)로 찍는다 — 맑은 고딕에
#   그 글자가 없어 두부가 된다. 하이픈으로 돌린다. (이 판은 축이 98~102 라 음수가 안 나오지만,
#   범위가 바뀌면 바로 터지는 자리라 먼저 막아 둔다.)
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.backends.backend_pdf import PdfPages

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "rrg.pdf")
sys.path.insert(0, HERE)
import style_top_pdf as ST                                        # noqa: E402

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2
BLU = "#3A6EA5"

QC = {"주도": POS, "약화": ACC, "부진": NEG, "회복": BLU}
QPOS = {"주도": (.97, .97, "right", "top"), "약화": (.97, .03, "right", "bottom"),
        "부진": (.03, .03, "left", "bottom"), "회복": (.03, .97, "left", "top")}


def main() -> int:
    R = json.load(io.open(os.path.join(DATA, "_rrg.json"), encoding="utf-8"))
    P = R["positions"]
    Q = ["회복", "주도", "약화", "부진"]

    with PdfPages(OUT) as pdf:
        fig = ST.new_page()
        y = .958
        ST.tx(fig, X0, y, "팩터 로테이션 — RRG 4분면", fontsize=21, weight="bold")
        ST.tx(fig, X1, y, "기준 %s · 팩터 %d종" % (R["as_of"], R["n_factors"]),
              fontsize=7.4, color=MUTED, ha="right")
        y -= .030
        ST.hline(fig, X0, X1, y, RULE, .9)
        y -= .012

        # 🚨 판정을 그림 **위**에 둔다. 밑에 두면 그림만 보고 덮는다.
        ST.box(fig, X0, y - .050, X1 - X0, .050, PANEL2, z=0)
        ST.tx(fig, X0 + .008, y - .010, "!! 이 그림은 기각됐습니다 - 회전은 시장이 아니라 산식이 만듭니다",
              fontsize=10.5, weight="bold", color=NEG)
        f3 = R["f3"]
        ST.tx(fig, X0 + .008, y - .026,
              "월수익을 통째로 뒤섞어 아무 로테이션도 없게 만든 뒤 같은 산식으로 다시 그려도 "
              "시계 방향이 %.1f%% 나옵니다. 실제는 %.1f%% - 사실상 같습니다."
              % ((f3["null_median"] or 0) * 100, (f3["real"] or 0) * 100),
              fontsize=7.4, color=INK2)
        ST.tx(fig, X0 + .008, y - .039,
              "세로축(기울기)이 가로축(수준)의 차분이라, 수준이 오르는 중이면 기울기는 양수일 "
              "수밖에 없습니다. 그래서 점은 구성상 시계로 돕니다.", fontsize=7.0, color=MUTED)
        y -= .062

        # ── 산점도 ──────────────────────────────────────────────────────
        # 🚨 꼬리를 110개 다 그렸더니 스파게티가 돼 아무것도 안 보였다(렌더 실측).
        #   사분면마다 «중심에서 가장 먼 둘» 여덟 개만 꼬리를 달고 이름도 그 여덟에만 단다.
        #   ⚠ 축 범위도 그 여덟의 꼬리까지만 넣는다 — 110개 꼬리를 다 넣으면 축이 벌어져
        #     점들이 한가운데 뭉친다.
        SHOW = []
        for q in Q:
            SHOW += sorted([p for p in P if p["q"] == q],
                           key=lambda p: -((p["ratio"] - 100) ** 2 + (p["mom"] - 100) ** 2))[:2]
        xs = [p["ratio"] for p in P]; ys = [p["mom"] for p in P]
        for p in SHOW:
            for t in (p.get("tail") or []):
                xs.append(t["x"]); ys.append(t["y"])
        pad = .35
        x0, x1 = min(xs) - pad, max(xs) + pad
        y0, y1 = min(ys) - pad, max(ys) + pad
        # 100 이 한가운데 오도록 넓은 쪽에 맞춘다 — 안 그러면 4분면 크기가 달라 보여 오해한다
        rx = max(100 - x0, x1 - 100); ry = max(100 - y0, y1 - 100)
        x0, x1, y0, y1 = 100 - rx, 100 + rx, 100 - ry, 100 + ry

        H = .455
        ax = fig.add_axes([X0, y - H, X1 - X0, H])
        ax.set_facecolor(PAPER)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        for s in ax.spines.values():
            s.set_color(LINE); s.set_linewidth(.7)
        ax.tick_params(colors=MUTED, labelsize=6.4, length=2.5)
        ax.axhline(100, color=RULE, lw=.9, zorder=1)
        ax.axvline(100, color=RULE, lw=.9, zorder=1)
        # 사분면 이름
        for q, (fx, fy, ha, va) in QPOS.items():
            ax.text(x0 + fx * (x1 - x0), y0 + fy * (y1 - y0),
                    "%s  %s" % (q, R["quadrants"][q]["en"]),
                    ha=ha, va=va, fontsize=10, weight="bold", color=QC[q], alpha=.55)
        # 꼬리(6개월 경로) — 보여 줄 여덟에만. 끝점에 방향 표시를 찍어 어디가 «지금» 인지 밝힌다.
        for p in SHOW:
            t = p.get("tail") or []
            if len(t) > 1:
                ax.plot([z["x"] for z in t], [z["y"] for z in t],
                        color=QC[p["q"]], lw=.8, alpha=.42, zorder=2, solid_capstyle="round")
                ax.scatter([t[0]["x"]], [t[0]["y"]], s=7, color=QC[p["q"]],
                           alpha=.35, linewidths=0, zorder=2)
        for q in Q:
            g = [p for p in P if p["q"] == q]
            ax.scatter([p["ratio"] for p in g], [p["mom"] for p in g], s=16,
                       color=QC[q], alpha=.72, linewidths=0, zorder=3)
        for p in SHOW:                      # 이름은 꼬리를 단 여덟에만
            ax.annotate(p["name"][:20], (p["ratio"], p["mom"]),
                        textcoords="offset points", xytext=(5, 3),
                        fontsize=5.6, color=INK2, zorder=4)
        ax.set_xlabel("가로축 — S&P 500 보다 얼마나 앞서 있나 (수준)",
                      fontsize=7, color=MUTED, labelpad=2)
        ax.set_ylabel("세로축 — 그 앞섬이 커지는 중인가 (기울기)",
                      fontsize=7, color=MUTED, labelpad=2)
        # ⚠ .022 만 뗐더니 x축 라벨이 아래 표 제목을 먹었다(렌더 실측) — .040 으로 뗀다.
        y -= H + .040

        # ── 사분면 표 ───────────────────────────────────────────────────
        ST.tx(fig, X0, y, "사분면마다 다음 달이 어땠나", fontsize=10, weight="bold")
        ST.tx(fig, X0 + .230, y, "기준선 %+.3f%% (전 관측 평균)" % R["base_mean"],
              fontsize=6.6, color=MUTED)
        y -= .0140
        cur = {}
        for p in P:
            cur[p["q"]] = cur.get(p["q"], 0) + 1
        rows = []
        for q in Q:
            s = R["quadrants"][q]
            rows.append([q, s["en"], "%d" % s["n"], "%+.3f%%" % s["mean"],
                         "%.0f%%" % s["win"], "%+.3f%%p" % s["lift"],
                         "%d종" % cur.get(q, 0)])

        def cq(r, c, rows=rows):
            if c == 0:
                return QC[rows[r][0]]
            if c == 5:
                return POS if not rows[r][5].startswith("-") else NEG
            return INK if c == 1 else MUTED
        y = ST.table(fig, X0, y, [.080, .110, .076, .090, .070, .100, .070],
                     ["사분면", "", "관측", "다음 달", "승률", "기준선차", "지금"], rows,
                     row_h=.0180, fs=7.4, hfs=6.6, zebra=True,
                     aligns=["l", "l", "r", "r", "r", "r", "r"], cell_color=cq)
        y -= .016

        f1, f2, f5 = R["f1"], R["f2"], R["f5"]
        ST.tx(fig, X0, y,
              "!! **주도 사분면이 제일 좋은 칸이 아닙니다.** 기준선보다 %+.3f%%p 로 오히려 "
              "아래입니다. 제일 좋은 칸은 **회복**(약한데 돌아서는 중)입니다."
              % R["quadrants"]["주도"]["lift"], fontsize=6.8, color=NEG)
        y -= .0118
        ST.tx(fig, X0, y,
              "!! 유일하게 음수인 칸은 **부진**입니다. 건질 게 있다면 «주도를 사라» 가 아니라 "
              "«부진을 피하라» 쪽인데 - 그것도 아래에서 무너집니다.", fontsize=6.8, color=NEG)
        y -= .0118
        # ⚠ 한 줄에 다 넣었더니 오른쪽으로 잘렸다(렌더 실측) — 두 줄로 나눈다.
        ST.tx(fig, X0, y,
              "!! 같은 달의 팩터 %d종은 같은 시장을 탑니다. 독립으로 세면 관측이 %s개처럼 "
              "보이지만 실제 독립 단위는 **%d개월**입니다."
              % (R["n_factors"], format(R["n_obs"], ","), f5["n_months"]),
              fontsize=6.8, color=NEG)
        y -= .0118
        ST.tx(fig, X0, y,
              "   달로 묶으면 주도-부진 차이의 t 가 **%.2f → %.2f** - 8%% 로 줄면서 "
              "**부호까지 뒤집힙니다.**" % (f2["t_pooled"], f5["t_clustered"]),
              fontsize=6.8, color=NEG)
        y -= .0118
        ST.tx(fig, X0, y,
              "되돌아보기가 12개월이라 이 그림은 **최근 한 달의 변화를 못 봅니다.** 지금처럼 "
              "시장 폭이 급히 무너진 국면에서 가장 알고 싶은 것을 바로 이 그림이 못 보여 줍니다.",
              fontsize=6.6, color=MUTED)
        y -= .0118
        ST.tx(fig, X0, y, "축 정의 - %s" % R["axis_note"], fontsize=6.2, color=MUTED)

        ST.hline(fig, X0, X1, .034, LINE, .6)
        ST.tx(fig, X0, .026,
              "여두 전략 랩 · RRG 4분면 팩터 로테이션 · 사전등록 PREREG-2026-09-22-RRG "
              "(계산 전 커밋 6ea920f) · 판정 **기각**", fontsize=6.4, color=MUTED)
        ST.tx(fig, X0, .0175,
              "!! 110종 전부 실었습니다 - 고른 팩터가 없습니다. 되돌아보기·컷·산식 판은 "
              "사전등록 값 그대로이고 하나도 안 움직였습니다.", fontsize=6.0, color=NEG)
        ST.tx(fig, X1, .026, "1 / 1 · %s" % dt.datetime.now().strftime("%Y-%m-%d"),
              fontsize=6.4, color=MUTED, ha="right")
        pdf.savefig(fig)
        if "--png" in sys.argv:
            fig.savefig(os.path.join(DATA, "_rrg.png"), dpi=110, facecolor=PAPER)
        ST.plt.close(fig)

    print("팩터 %d종 · 지금 %s" % (R["n_factors"],
          " · ".join("%s %d" % (q, sum(1 for p in P if p["q"] == q)) for q in Q)))
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
