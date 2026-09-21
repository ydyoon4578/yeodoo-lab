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
    # 닮은 달 찾기 결과 — 있으면 마지막에 한 쪽 붙인다(없어도 나머지는 그대로 나온다).
    try:
        A = json.load(io.open(os.path.join(DATA, "_analog.json"), encoding="utf-8"))
    except Exception:
        A = None
    try:
        FL = json.load(io.open(os.path.join(DATA, "_flags.json"), encoding="utf-8"))
    except Exception:
        FL = None
    try:
        RO = json.load(io.open(os.path.join(DATA, "_riskonoff.json"), encoding="utf-8"))
    except Exception:
        RO = None
    # 점수밴드 × 추세 15칸 — Risk-On/Off 쪽 바로 뒤에 붙는다(같은 점수를 쓰는 표다).
    try:
        RG = json.load(io.open(os.path.join(DATA, "_regime_grid.json"), encoding="utf-8"))
    except Exception:
        RG = None

    # 쪽 나누기 — 축별 요약은 칸마다 5줄 + 제목 1줄
    # ⚠ 7개면 첫 쪽(범례가 자리를 먹는다)에서 마지막 칸이 각주 위로 넘쳤다 — 실측으로 5로 줄였다.
    AX_PER = 5                      # 한 쪽에 축 칸 5개
    npk = (len(K) + AX_PER - 1) // AX_PER
    ROWS_P = 46                     # 월별 표 한 쪽에 46행
    npm = (len(M) + ROWS_P - 1) // ROWS_P
    total = (npk + npm + (1 if A else 0) + (1 if FL else 0)
             + (1 if RO else 0) + (1 if RG else 0))
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
                # 범례 — 말이 어려우면 표가 안 읽힌다(사용자 지적 2026-09-21).
                ST.tx(fig, X0, y, "표에 나오는 말", fontsize=9.5, weight="bold")
                y -= .0125
                lg = [[z["short"], z["long"]] for z in (D.get("legend") or [])]
                y = ST.table(fig, X0, y, [.150, .734], ["말", "뜻"], lg,
                             row_h=.0132, fs=6.9, hfs=6.2, aligns=["l", "l"],
                             cell_color=lambda r, c: INK if c == 0 else MUTED)
                y -= .0125
                ST.tx(fig, X0, y,
                      "«하 / 중 / 상» 은 이 122개월을 셋으로 나눈 자리다 - 절대 기준이 아니라 "
                      "이 구간 안에서의 위치다.", fontsize=6.4, color=MUTED)
                y -= .018
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

        # ── 종합 Risk-On/Off ───────────────────────────────────────────
        if RO:
            fig = ST.new_page()
            y = .958
            ST.tx(fig, X0, y, "종합 Risk-On/Off", fontsize=15, weight="bold")
            ST.tx(fig, X1, y, "기준 %s" % RO["as_of"], fontsize=7.4, color=MUTED, ha="right")
            # ⚠ 30pt 숫자는 폭이 넓다 — 밴드 라벨을 .085 에 두니 겹쳤다(실측). .125 로 뗀다.
            y -= .026
            bc = NEG if "Off" in RO["band"] else (POS if "On" in RO["band"] else ACC)
            ST.tx(fig, X0, y, "%.1f" % RO["score"], fontsize=30, weight="bold", color=bc)
            ST.tx(fig, X0 + .125, y + .006, RO["band"], fontsize=15, weight="bold", color=bc)
            ST.tx(fig, X0 + .125, y - .008,
                  ">=68 Risk-On · 60~67 준Risk-On · 50~59 중립 · 40~49 준Risk-Off · <40 Risk-Off",
                  fontsize=6.4, color=MUTED)
            y -= .034
            KO = {"trend": "추세·모멘텀", "vol": "변동성 안정도", "breadth": "시장 폭",
                  "macro": "매크로·신용", "sector": "섹터 리더십"}
            gr = [[KO[k], "%.1f" % RO["groups"][k], "%d%%" % RO["weights"][k]]
                  for k in ("trend", "vol", "breadth", "macro", "sector")]
            gr.append(["심리", "—", "10% (자료 없음 · 뺐다)"])

            def cg(r, c, gr=gr):
                if c == 1 and gr[r][1] != "—":
                    v = float(gr[r][1])
                    return NEG if v < 35 else (POS if v > 65 else INK)
                return INK if c == 0 else MUTED
            y = ST.table(fig, X0, y, [.180, .090, .220], ["신호군", "점수", "가중"], gr,
                         row_h=.0170, fs=7.4, hfs=6.6, aligns=["l", "r", "l"], cell_color=cg)
            y -= .016
            ST.tx(fig, X0, y,
                  "!! 이 점수는 그 문서의 점수와 **같은 수가 아니다** - 심리 10%% 가 통째로 없어"
                  "(F&G·풋콜·SKEW·AAII·NAAIM) 나머지 다섯을 90 으로 재정규화했다. "
                  "변동성도 셋 중 하나(VIX)뿐이다.", fontsize=6.4, color=NEG)
            y -= .0110
            ST.tx(fig, X0, y,
                  "산식(각 지표를 «그날까지의» 분포 백분위로 바꿔 신호군 안에서 평균)은 그 문서가 "
                  "안 밝혀 내가 골랐다. 확장창이라 선견은 없다.", fontsize=6.4, color=MUTED)
            y -= .022
            bt = RO["backtest"]
            ST.tx(fig, X0, y, "밴드가 다음 달을 가르나", fontsize=10, weight="bold")
            # ⚠ .130 → .165 로 뗐는데 **그래도 겹쳤다**(렌더 실측: «가르나» 가 «기준선» 을 먹었다).
            #   10pt 한글은 글자당 약 .0179 다 — 11글자면 .197. 여유 두고 .210.
            ST.tx(fig, X0 + .210, y, "기준선 %+.2f%% · 승률 %.0f%% (일 %d)"
                  % (bt["base"]["mean"], bt["base"]["win"], bt["base"]["n"]),
                  fontsize=6.6, color=MUTED)
            y -= .0130
            br = []
            for b_ in ("Risk-On", "준Risk-On", "중립", "준Risk-Off", "Risk-Off"):
                if b_ in bt:
                    v = bt[b_]
                    br.append([b_, str(v["n"]), "%+.2f%%" % v["mean"],
                               "%.0f%%" % v["win"], "%+.2f%%p" % v["lift"]])

            def cb(r, c, br=br):
                if c == 4:
                    return POS if not br[r][4].startswith("-") else NEG
                return INK if c == 0 else MUTED
            y = ST.table(fig, X0, y, [.150, .080, .090, .080, .100],
                         ["밴드", "일수", "1개월", "승률", "기준선차"], br,
                         row_h=.0168, fs=7.2, hfs=6.4,
                         aligns=["l", "r", "r", "r", "r"], cell_color=cb)
            y -= .016
            ST.tx(fig, X0, y,
                  # 🚨 는 맑은 고딕에 없다 — 종이에는 «!!» 로 눕힌다(두부 방지).
                  "!! **거꾸로 선다.** 점수가 높을수록 다음 달이 나쁘다 - Risk-On %+.2f%% vs "
                  "Risk-Off %+.2f%%. 평균회귀이지 «점수 높으면 사라» 가 아니다."
                  % (bt.get("Risk-On", {}).get("mean", 0), bt.get("Risk-Off", {}).get("mean", 0)),
                  fontsize=6.6, color=NEG)
            y -= .0112
            ST.tx(fig, X0, y,
                  "그 문서의 국면표도 같은 방향이다 - 「점수 낮음(<45) +2.1%p / 점수 높음(>=60) "
                  "-0.4%p」. 그쪽도 «설명용·예측 아님» 이라 적어 뒀다.",
                  fontsize=6.4, color=MUTED)
            pg += 1
            footer(fig, pg, total, span)
            pdf.savefig(fig)
            if "--png" in sys.argv:
                fig.savefig(os.path.join(DATA, "_mm5.png"), dpi=110, facecolor=PAPER)
            ST.plt.close(fig)

        # ── 국면 15칸 (점수밴드 × 추세) ─────────────────────────────────
        # ⚠ ▲▼→ 는 맑은 고딕에 **있다**(실측: U+25B2·U+25BC·U+2192 전부 cmap 안).
        #   없는 것은 ✓✗⚠🚨 다 — 그것만 «!!» 로 눕힌다.
        if RG:
            fig = ST.new_page()
            y = .958
            ST.tx(fig, X0, y, "국면 15칸 — 점수밴드 × 추세", fontsize=15, weight="bold")
            ST.tx(fig, X1, y, "기준 %s" % RG["as_of"], fontsize=7.4, color=MUTED, ha="right")
            y -= .020
            ST.tx(fig, X0, y,
                  "앞쪽 Risk-On/Off 밴드가 **거꾸로** 갔다. 그 문서의 국면표는 밴드 하나가 아니라 "
                  "두 축이라, 추세축을 더하면 풀리나 물었다.", fontsize=6.8, color=INK2)
            y -= .0145
            ST.tx(fig, X0, y,
                  "추세 = d5(5거래일 점수 변화) · ▲ +2 이상 · ▼ -2 이하 · → 그 사이. "
                  "**원천 _scell() 값 그대로다** — 컷도 되돌아보기도 안 움직였다.",
                  fontsize=6.8, color=MUTED)
            y -= .0145
            ST.tx(fig, X0, y,
                  "기준선 — 아무 날이나 사서 1개월 들면 %+.2f%% · 승률 %.0f%% (일 %d)."
                  % (RG["base_mean"], RG["base_win"], RG["n_used"]),
                  fontsize=6.8, color=MUTED)
            y -= .020

            TR = RG["trends"]
            gcells, gr2 = {}, []
            for b_ in RG["bands"]:
                row = [b_]
                for t_ in TR:
                    c = RG["grid"]["%s|%s" % (b_, t_)]
                    gcells[(len(gr2), len(row))] = c
                    row += ["—" if not c["n"] else "%+.2f%%" % c["mean"],
                            "—" if not c["n"] else "%d" % c["n"]]
                gr2.append(row)

            def cgr(r, c, gcells=gcells, base=RG["base_mean"]):
                if c == 0:
                    return INK
                if c % 2 == 1:                         # 값 칸 — 기준선 위/아래
                    cell = gcells.get((r, c))
                    if not cell or not cell["n"]:
                        return MUTED
                    return POS if cell["mean"] >= base else NEG
                cell = gcells.get((r, c - 1))          # 일수 칸 — 얇으면 빨갛게
                return NEG if (cell and 0 < cell["n"] < 60) else MUTED
            y = ST.table(fig, X0, y, [.120, .086, .062, .086, .062, .086, .062],
                         ["밴드", TR[0], "일수", TR[1], "일수", TR[2], "일수"], gr2,
                         row_h=.0182, fs=7.4, hfs=6.6, zebra=True,
                         aligns=["l", "r", "r", "r", "r", "r", "r"], cell_color=cgr)
            y -= .018

            f1, f2, f3 = RG["f1"], RG["f2"], RG["f3"]
            f4, f5 = RG["f4"], RG["f5"]
            fr2 = [
                ["F1", "Risk-Off 안에서 ▲ 가 ▼ 보다 큰가",
                 "%+.2f%%p" % f1["diff"] if f1["diff"] is not None else "—",
                 "걸림" if f1["hit"] else "통과"],
                ["F2", "그 차이의 t 가 %.1f 이상인가" % f2["문턱"],
                 "t %.2f" % f2["t_overlap"] if f2["t_overlap"] is not None else "—",
                 "구별 불가" if f2["hit"] else "통과"],
                ["F3", "같은 추세 안에서도 Risk-On 이 Risk-Off 보다 낮은가",
                 "%d / 3" % f3["n_worse"], "걸림" if f3["hit"] else "통과"],
                ["F4", "60일 미만 얇은 칸이 5개 이상인가",
                 "%d개" % len(f4["thin"]), "측정 불가" if f4["hit"] else "통과"],
                ["F5", "중첩과 비중첩의 판정이 갈리나",
                 "t 중앙 %.2f" % f5["t_median"] if f5["t_median"] is not None else "—",
                 "보류" if f5["split"] else "안 갈림"],
            ]

            def cf2(r, c, fr2=fr2):
                if c == 3:
                    return POS if fr2[r][3] in ("통과", "안 갈림") else NEG
                return INK if c == 0 else MUTED
            ST.tx(fig, X0, y, "미리 못박은 실패 조건", fontsize=10, weight="bold")
            y -= .0140
            y = ST.table(fig, X0, y, [.044, .330, .110, .096],
                         ["", "묻는 것", "결과", "판정"], fr2,
                         row_h=.0172, fs=7.0, hfs=6.4,
                         aligns=["l", "l", "r", "l"], cell_color=cf2)
            y -= .016
            ST.tx(fig, X0, y,
                  "!! **역방향은 안 풀렸다.** 세 추세 전부에서 Risk-On 칸이 Risk-Off 칸보다 "
                  "낮다(%d/3). 「밴드 해석 불가」 판정을 유지한다." % f3["n_worse"],
                  fontsize=6.6, color=NEG)
            y -= .0112
            ST.tx(fig, X0, y,
                  "!! 겹침을 빼니 t 가 %.2f → %.2f (%.0f%%) 로 주저앉았다. 21개 위상에서 "
                  "t 가 %.2f ~ %+.2f 로 널뛴다 — **부호조차 안 정해진다.**"
                  % (f2["t_overlap"], f5["t_median"],
                     abs(f5["t_median"]) / abs(f2["t_overlap"]) * 100,
                     f5["t_min"], f5["t_max"]), fontsize=6.6, color=NEG)
            y -= .0112
            ST.tx(fig, X0, y,
                  "일별로 21일 창을 재면 이웃 관측이 20일을 공유한다 — 일수가 875 라도 독립 "
                  "표본은 42 에 가깝다. 위상을 하나 고르지 않고 21개를 전부 돌았다.",
                  fontsize=6.4, color=MUTED)
            y -= .0112
            ST.tx(fig, X0, y,
                  "!! 판정 **%s** — 지금이 어느 칸인지 보는 기술표로만 쓴다. 밴드 방향을 믿거나 "
                  "칸 사이 차이를 «유의하다» 고 말하면 안 된다. "
                  "(PREREG-2026-09-21-REGIMEGRID · 계산 전 커밋 6b120f2)" % RG["verdict"],
                  fontsize=6.4, color=NEG)
            pg += 1
            footer(fig, pg, total, span)
            pdf.savefig(fig)
            if "--png" in sys.argv:
                fig.savefig(os.path.join(DATA, "_mm6.png"), dpi=110, facecolor=PAPER)
            ST.plt.close(fig)

        # ── 극단 플래그 감시 ────────────────────────────────────────────
        if FL:
            fig = ST.new_page()
            y = .958
            ST.tx(fig, X0, y, "극단 플래그 감시", fontsize=15, weight="bold")
            ST.tx(fig, X1, y, "기준 %s · S&P %.0f" % (FL["as_of"], FL["spx"]),
                  fontsize=7.4, color=MUTED, ha="right")
            y -= .020
            ST.tx(fig, X0, y,
                  "설계 출처는 사용자 제공 「시장 국면 모니터」(2026-07-09) ④. 트리거는 그 문서 값 "
                  "그대로 쓰고, **적중률은 이 랩 자료로 다시 쟀다**(창·유니버스가 다르다).",
                  fontsize=6.8, color=INK2)
            y -= .0145
            b = FL["base"]
            ST.tx(fig, X0, y,
                  "기준선 — 아무 날이나 사서 1개월 들면 %+.2f%% · 승률 %.0f%% (n=%d). "
                  "아래 «기준선차» 가 그것을 뺀 값이다."
                  % (b["fwd_mean"], b["win"], b["n"]), fontsize=6.8, color=MUTED)
            y -= .018
            fr = []
            for r in FL["flags"]:
                o = r["ON"]
                fr.append([r["ko"], r["now"], (r["value"] or "")[:20],
                           "—" if o["fwd_mean"] is None else "%+.2f%%" % o["fwd_mean"],
                           "—" if o["win"] is None else "%.0f%%" % o["win"],
                           "—" if o["lift"] is None else "%+.2f%%p" % o["lift"],
                           str(o["n"]), r["trigger"][:26]])

            def cf(rr, c, fr=fr):
                if c == 1:
                    return NEG if fr[rr][1] == "ON" else (ACC if fr[rr][1] == "주의" else MUTED)
                if c == 5 and fr[rr][5] != "—":
                    return POS if not fr[rr][5].startswith("-") else NEG
                return INK if c == 0 else MUTED
            y = ST.table(fig, X0, y, [.150, .048, .130, .076, .054, .076, .046, .304],
                         ["플래그", "상태", "현재값", "ON 1개월", "승률", "기준선차", "횟수",
                          "트리거"], fr, row_h=.0170, fs=6.7, hfs=6.2, zebra=True,
                         aligns=["l", "c", "l", "r", "r", "r", "r", "l"], cell_color=cf)
            y -= .016
            ST.tx(fig, X0, y,
                  "!! 매매 규칙이 아니라 **감시판**이다. 이 랩은 국면 조건부 규칙을 12번 시도해 "
                  "11번 기각했다. 플래그가 켜졌다고 사는 것이 아니라 «지금 무엇이 극단인가» 를 본다.",
                  fontsize=6.4, color=NEG)
            y -= .0110
            ST.tx(fig, X0, y,
                  "!! 그 문서의 16개 중 자료가 없는 다섯은 뺐다(지어 채우지 않는다) — %s."
                  % " · ".join(FL["dropped"]), fontsize=6.4, color=MUTED)
            y -= .0110
            ST.tx(fig, X0, y,
                  # ⚠ 는 맑은 고딕에 없다 — 종이에는 «!!» 로 눕힌다(두부 방지).
                  "!! 처음에 RSI 를 단순 n봉 평균으로 짰다가 잡았다 - n=2 에서 값이 0/100 에 "
                  "몰려 «최근 2일 다 내렸나» 를 재는 이진 지표가 됐다. Wilder 평활로 고쳤다.",
                  fontsize=6.4, color=MUTED)
            pg += 1
            footer(fig, pg, total, span)
            pdf.savefig(fig)
            if "--png" in sys.argv:
                fig.savefig(os.path.join(DATA, "_mm4.png"), dpi=110, facecolor=PAPER)
            ST.plt.close(fig)

        # ── 덧 — 닮은 달 찾기(해 봤고 안 섰다) ──────────────────────────
        if A:
            fig = ST.new_page()
            analog_page(fig, .958, A)
            pg += 1
            footer(fig, pg, total, span)
            pdf.savefig(fig)
            if "--png" in sys.argv:
                fig.savefig(os.path.join(DATA, "_mm3.png"), dpi=110, facecolor=PAPER)
            ST.plt.close(fig)

    print("→ %s (%.1fMB)" % (OUT, os.path.getsize(OUT) / 1e6))
    return 0


def analog_page(fig, y, A):
    """닮은 달 찾기 — **해 봤고 안 섰다.** 그 사실이 이 쪽의 내용이다.

    🚨 이 쪽이 없으면 data/_analog.json 은 «재 놓고 안 실은» 산출물이 된다.
      이 랩은 그것을 «잰 적 없는 것» 으로 친다(audit_unbuilt).
    """
    t, now = A["test"], A["now"]
    ST.tx(fig, X0, y, "덧 — 지금과 «흐름이 닮은» 과거 달 찾기", fontsize=13, weight="bold")
    y -= .020
    ST.tx(fig, X0, y,
          "3개월 궤적(전전달·전달·이번달) x 7변수 = 21차원으로 가장 닮은 창을 찾아봤다. "
          "결론부터: **안 선다.**", fontsize=7.4, color=INK2)
    y -= .016
    rows = [["이웃이 다음 달 상위5 를 맞히나",
             "%.2f / 5" % t["analog_hit"],
             "전 구간 최다 5개 %.2f · 무작위 %.2f" % (t["always_hit"], t["random_hit"]),
             "대조군에 진다"],
            ["이웃이 시장 방향을 맞히나",
             "%.1f%%" % (t["dir_acc"] * 100),
             "늘 한 방향으로 찍기 %.1f%%" % (t["dir_base"] * 100),
             "기준선에 진다"],
            ["이웃이 가깝기는 한가",
             "%.2f" % t["dist_near"],
             "중앙 %.2f · 하위10%% %.2f" % (t["dist_median"], t["dist_p10"]),
             "닮았다기보다 덜 멀다"]]
    y = ST.table(fig, X0, y, [.300, .110, .300, .174],
                 ["물은 것", "값", "대조군", "읽기"], rows,
                 row_h=.0150, fs=7.0, hfs=6.4, aligns=["l", "r", "l", "l"],
                 cell_color=lambda r, c: INK if c == 0 else (NEG if c == 3 else MUTED))
    y -= .014
    ST.tx(fig, X0, y, "지금 창 %s (S&P %s) — 가장 닮은 과거 창"
          % (" -> ".join(now["window"]),
             " -> ".join("%+.1f" % v for v in now["spx3"])),
          fontsize=8.6, weight="bold")
    y -= .0125
    nr = [[" -> ".join(z["window"]), "%.2f" % z["dist"],
           " ".join("%+.1f" % v for v in z["spx3"]),
           "%s %+.1f%%" % (z["next_m"], z["next_spx"])] for z in A["near"]]
    y = ST.table(fig, X0, y, [.290, .080, .190, .150],
                 ["닮은 창", "거리", "그때 S&P 3개월", "그 다음 달"], nr,
                 row_h=.0142, fs=7.0, hfs=6.4, aligns=["l", "r", "l", "l"],
                 cell_color=lambda r, c: INK if c == 0 else MUTED)
    y -= .013
    ST.tx(fig, X0, y,
          "!! 이 표를 «닮았으니 그때처럼 될 것» 으로 읽으면 안 된다 - 위 검정이 바로 그것을 "
          "재서 아니라고 말한다. k 를 바꿔 가며 더 나은 값을 찾지 않았다(그것이 이 랩이 "
          "폐기한 절차다).", fontsize=6.4, color=NEG)
    return y


if __name__ == "__main__":
    raise SystemExit(main())
