# -*- coding: utf-8 -*-
"""build/month_map_pdf.py — 달마다의 시장 상황과 그달 잘 간 전략 → data/month_map.pdf

자료는 build/month_map.py 가 낸 data/_month_map.json 하나뿐이다. 여기서 아무것도
계산하지 않는다 — 손으로 적은 수는 낡는다.
판형·색·표는 build/style_top_pdf.py 를 import 해서 쓴다.

🚨 이 문서의 관계는 전부 **동시대**다. «그달 급락이었고 그달 VXZ 가 잘 갔다» 이지
  «급락할 것을 알았다» 가 아니다. 지속성(이달 순위 ↔ 다음 달 순위)이 +0.05 라는 것을
  첫 쪽에 크게 적는다 — 그것을 안 적으면 이 표는 매매 규칙으로 읽힌다.

  python build/month_map_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "month_map.pdf")
sys.path.insert(0, HERE)
import style_top_pdf as ST                                        # noqa: E402
from period_pdf import safe, cut, num                             # noqa: E402

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER = ST.POS, ST.NEG, ST.ACC, ST.PAPER


def footer(fig, page, total, span):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .026,
          "여두 전략 랩 · 달마다의 시장 상황과 그달 잘 간 전략 · %s~%s · "
          "초과 = 그 규칙의 대조군 대비" % (span[0], span[1]), fontsize=6.4, color=MUTED)
    ST.tx(fig, X0, .0175,
          "!! 동시대 관계다 - 「그달 그랬다」이지 「미리 알았다」가 아니다. "
          "이달 순위와 다음 달 순위의 상관은 +0.05 다.", fontsize=6.0, color=NEG)
    ST.tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def main() -> int:
    D = json.load(io.open(os.path.join(DATA, "_month_map.json"), encoding="utf-8"))
    P, K, M = D["persistence"], D["kinds"], D["months"]
    span = D["span"]

    # 쪽 나누기 — 축별 요약은 칸마다 5줄 + 제목 1줄
    AX_PER = 7                      # 한 쪽에 축 칸 7개
    npk = (len(K) + AX_PER - 1) // AX_PER
    ROWS_P = 46                     # 월별 표 한 쪽에 46행
    npm = (len(M) + ROWS_P - 1) // ROWS_P
    total = npk + npm
    print("축 칸 %d개 · 달 %d개 → %d쪽" % (len(K), len(M), total))

    with PdfPages(OUT) as pdf:
        pg = 0
        # ── 축별 요약 ───────────────────────────────────────────────────
        for pi in range(npk):
            fig = ST.new_page()
            y = .958
            if pi == 0:
                ST.tx(fig, X0, y, "달마다의 시장 상황과 그달 잘 간 전략",
                      fontsize=21, weight="bold")
                ST.tx(fig, X0, y - .032,
                      "%s ~ %s · %d개월 · 규칙 중앙 %d종"
                      % (span[0], span[1], D["n_months"], D["n_rules_median"]),
                      fontsize=9.5, color=ACC)
                ST.hline(fig, X0, X1, y - .044, RULE, .9)
                y -= .056
                # 🚨 경고를 맨 위에 — 이걸 안 읽으면 표를 매매 규칙으로 읽는다.
                ST.box(fig, X0, y - .052, X1 - X0, .052, ST.PANEL2, z=0)
                ST.tx(fig, X0 + .008, y - .011, "먼저 읽을 것 - 이 표로 다음 달을 맞힐 수 없다",
                      fontsize=9.5, weight="bold", color=NEG)
                ST.tx(fig, X0 + .008, y - .026,
                      "이달 상위5 가 다음 달에도 상위5 에 남는 비율 %.1f%% (무작위 %.1f%%) · "
                      "이달 순위 ↔ 다음 달 순위 상관 중앙 %+.3f"
                      % (P["top5_carry_pct"], P["random_pct"], P["rank_rho_median"]),
                      fontsize=7.4, color=INK2)
                ST.tx(fig, X0 + .008, y - .040,
                      "여기 나오는 관계는 전부 동시대다 - 「그달 급락이었고 그달 롱볼이 갔다」이지 "
                      "「급락할 것을 알았다」가 아니다. 쓰임은 «내가 든 전략이 어떤 달에 다칠지» 까지다.",
                      fontsize=7.0, color=MUTED)
                y -= .062
            else:
                ST.tx(fig, X0, y, "상황별 (이어서)", fontsize=13, weight="bold")
                y -= .026
            for k in K[pi * AX_PER:(pi + 1) * AX_PER]:
                ST.tx(fig, X0, y, "%s = %s" % (k["axis_ko"], k["level"]),
                      fontsize=10, weight="bold")
                # ⚠ .105 에서는 «= 급락» 꼬리와 겹쳤다(실측). 10pt 제목이 최대 12글자다.
                ST.tx(fig, X0 + .140, y,
                      "%d개월 · S&P 평균 %+.2f%% · 규칙 중앙초과 %+.2f%%"
                      % (k["n_months"], k["spx_mean"], k["med_ex"]),
                      fontsize=6.6, color=MUTED)
                y -= .0125
                rows = [[cut(z["name"], 40), "%.1f%%" % z["in_pct"],
                         "%.1f%%" % z["all_pct"], "%+.1f%%p" % z["lift"]]
                        for z in k["recur"][:5]]

                def cs(r, c, rows=rows):
                    if c == 0:
                        return INK
                    if c == 3:
                        return POS if not rows[r][3].startswith("-") else NEG
                    return MUTED
                y = ST.table(fig, X0, y, [.440, .130, .130, .124],
                             ["규칙", "이 칸 진입률", "전 구간", "리프트"], rows,
                             row_h=.0128, fs=6.8, hfs=6.2,
                             aligns=["l", "r", "r", "r"], cell_color=cs)
                y -= .0105
            pg += 1
            footer(fig, pg, total, span)
            pdf.savefig(fig)
            if "--png" in sys.argv and pi == 0:
                fig.savefig(os.path.join(DATA, "_mm1.png"), dpi=110, facecolor=PAPER)
            ST.plt.close(fig)

        # ── 월별 ────────────────────────────────────────────────────────
        for pi in range(npm):
            fig = ST.new_page()
            y = .958
            ST.tx(fig, X0, y, "월별 — 시장 상황과 그달 상위 3" + (" (이어서)" if pi else ""),
                  fontsize=15 if pi == 0 else 12, weight="bold")
            if pi == 0:
                ST.tx(fig, X1, y, "상위 3 은 그달 초과(그 규칙의 대조군 대비) 순",
                      fontsize=6.6, color=MUTED, ha="right")
            y -= .028
            part = M[pi * ROWS_P:(pi + 1) * ROWS_P]
            rows = []
            for r in part:
                rows.append([r["m"], num(r["spx"], 1), num(r["ndx"], 1),
                             cut(r["label"].replace(" · ", "·"), 26),
                             num(r["med"], 2, True),
                             " · ".join(cut(z["name"], 17) for z in r["top"][:3])])

            def cs2(rr, c, rows=rows):
                if c in (1, 2, 4):
                    v = rows[rr][c]
                    return (POS if not v.startswith("-") else NEG) if v != "—" else MUTED
                return INK if c == 0 else MUTED
            y = ST.table(fig, X0, y, [.062, .046, .046, .176, .052, .502],
                         ["월", "S&P%", "NDX%", "시장 상황", "중앙초과", "그달 상위 3"], rows,
                         row_h=.0182, fs=6.3, hfs=6.0, zebra=True,
                         aligns=["l", "r", "r", "l", "r", "l"], cell_color=cs2)
            pg += 1
            footer(fig, pg, total, span)
            pdf.savefig(fig)
            if "--png" in sys.argv and pi == npm - 1:
                fig.savefig(os.path.join(DATA, "_mm2.png"), dpi=110, facecolor=PAPER)
            ST.plt.close(fig)

    print("→ %s (%.1fMB)" % (OUT, os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
