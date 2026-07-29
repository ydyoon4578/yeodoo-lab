# -*- coding: utf-8 -*-
"""build/momentum_vol_pdf.py — 모멘텀 변동성 관리 한 주제 → data/momentum_vol.pdf

무엇을. "모멘텀의 위험은 자기 실현분산으로 예측된다"는 주장 하나를 이 랩의 자료로 다시 재고
그 결과를 한 쪽에 담는다. 남의 결론을 옮겨 적는 문서가 아니라 **같은 규칙을 우리 표본에
돌려 본 기록**이다.

출처. Pedro Barroso · Pedro Santa-Clara, "Momentum has its moments,"
      Journal of Financial Economics 116(1), 2015, pp.111-120.
      보고값: 직전 6개월 실현변동성으로 목표변동성에 맞춰 스케일하면
      샤프 0.53 -> 0.97, 초과첨도 18.24 -> 2.68, 왜도 -2.47 -> -0.42.
      ⚠ 그쪽은 **롱숏 모멘텀 팩터**이고 여기는 **롱온리 상위 10종목 동일가중**이다.
        손익 구조가 다르므로 수치가 같게 나올 이유가 없다 — 방향만 본다.

랩 규약. 목표변동성은 **그 시점까지의 실현변동성**으로 잡는다(확장창). 전 표본 표준편차로
      잡으면 미래를 쓰는 것이고, 그 룩어헤드는 이 계열 연구의 알려진 함정이다
      (Liu·Tang·Zhou 2019 가 Moreira-Muir 계열에 대해 지적한 것과 같은 문제).

  python build/momentum_vol_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, math, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
OUT = os.path.join(DATA, "momentum_vol.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER = ST.POS, ST.NEG, ST.ACC, ST.PAPER

LOOK, WARM = ST.VM_LOOK, ST.VM_WARM


def monthly_of(P, fn):
    """긴 창으로 한 스타일을 돌려 월별 수익률(%)을 얻는다."""
    old, ST.WINDOW = ST.WINDOW, len(P.dates) - 800
    try:
        R = ST.backtest(P, fn)
    finally:
        ST.WINDOW = old
    if not R:
        return None, None
    ms, mo = ST.monthly(R["nav"], P.dates, R["start"])
    mk = [m for m in ms if mo.get(m) is not None]
    return mk, [mo[m] for m in mk]


def scale_path(r):
    """확장창 목표 · 직전 LOOK 개월 변동성으로 비중. → (비중, 원본, 관리) 각 WARM 이후."""
    w, a, b = [], [], []
    for i in range(WARM, len(r)):
        tgt = float(np.std(np.array(r[:i], float), ddof=1))
        v = float(np.std(np.array(r[i - LOOK:i], float), ddof=1))
        x = 1.0 if v <= 0 else min(1.0, tgt / v)
        w.append(x); a.append(r[i]); b.append(r[i] * x)
    return w, a, b


def perf(r):
    x = np.array(r, float) / 100.0
    nav = np.cumprod(1 + x)
    sd = float(x.std(ddof=1))
    dd = nav / np.maximum.accumulate(nav) - 1
    return {"cagr": (nav[-1] ** (12 / len(x)) - 1) * 100, "vol": sd * math.sqrt(12) * 100,
            "sharpe": float(x.mean()) / sd * math.sqrt(12), "mdd": float(dd.min()) * 100,
            "worst": float(x.min()) * 100, "nav": nav}


def num(v, d=2, sign=True):
    if v is None:
        return "—"
    return ("%+.*f" if sign else "%.*f") % (d, v)


def main() -> int:
    print("패널을 연다…")
    P = ST.Panel()
    ms, r = monthly_of(P, ST.sc_mom)
    if not ms:
        raise SystemExit("모멘텀을 못 돌렸다 — 패널을 확인할 것")
    w, base, scal = scale_path(r)
    pb, ps = perf(base), perf(scal)
    print("  모멘텀 %s~%s · %d개월 · 관리구간 %d개월" % (ms[0], ms[-1], len(ms), len(base)))

    # ① 자기 변동성 상태별 — 평균은 높은데 꼬리가 다른가
    rows_state, med = [], None
    v6 = [float(np.std(np.array(r[i - LOOK:i], float), ddof=1)) for i in range(LOOK, len(r))]
    nxt = r[LOOK:]
    med = float(np.median(v6))
    for lab, sel in (("직전 변동성 낮음", [x for v, x in zip(v6, nxt) if v <= med]),
                     ("직전 변동성 높음", [x for v, x in zip(v6, nxt) if v > med])):
        a = np.array(sel, float)
        rows_state.append([lab, "%d" % len(a), num(float(a.mean()), 2), "%.0f%%" % ((a > 0).mean() * 100),
                           num(float(a.min()), 2)])

    # ② 다른 스타일에도 통하나
    rows_other, dmdd = [], {}
    for fn, lab in ((ST.sc_mom, "모멘텀"), (ST.sc_grow, "성장"), (ST.sc_hbeta, "고베타")):
        mm, rr = monthly_of(P, fn)
        if not mm:
            continue
        _w2, b2, s2 = scale_path(rr)
        p1, p2 = perf(b2), perf(s2)
        dmdd[lab] = p2["mdd"] - p1["mdd"]
        rows_other.append([lab, num(p1["cagr"], 2), num(p2["cagr"], 2),
                           num(p2["cagr"] - p1["cagr"], 2),
                           num(p1["sharpe"], 2, False), num(p2["sharpe"], 2, False),
                           num(p1["mdd"], 2), num(p2["mdd"], 2), num(dmdd[lab], 2)])
        print("  %-5s 원본 CAGR %.2f -> 관리 %.2f · MDD %.2f -> %.2f"
              % (lab, p1["cagr"], p2["cagr"], p1["mdd"], p2["mdd"]))

    # ③ 최악의 달 - 그 자리에서 실제로 얼마를 덜 맞았나
    order = sorted(range(len(base)), key=lambda i: base[i])[:6]
    rows_worst = [[ms[WARM + i], num(w[i] * 100, 0, False) + "%", num(base[i], 2),
                   num(scal[i], 2), num(scal[i] - base[i], 2)] for i in sorted(order)]

    with PdfPages(OUT) as pdf:
        fig = ST.new_page()
        y = .960
        ST.tx(fig, X0, y, "모멘텀 변동성 관리", fontsize=23, weight="bold")
        ST.tx(fig, X0, y - .034,
              "모멘텀의 위험은 자기 실현분산으로 예측되는가 — 랩 자료로 다시 재다",
              fontsize=10, color=ACC)
        ST.tx(fig, X1, y - .030, "%s ~ %s · %d개월" % (ms[0], ms[-1], len(ms)),
              fontsize=8.5, color=MUTED, ha="right")
        ST.hline(fig, X0, X1, y - .046, RULE, .9)
        y -= .062

        ST.tx(fig, X0, y, "무엇을 검증하나", fontsize=11.5, weight="bold")
        ST.tx(fig, X0, y - .016,
              "Barroso & Santa-Clara(JFE 2015)는 모멘텀의 위험이 자기 실현분산으로 예측되며, 직전 6개월 실현변동성으로\n"
              "목표변동성에 맞춰 스케일하면 크래시가 사실상 사라지고 샤프가 0.53에서 0.97로 오른다고 보고했다.\n"
              "그쪽은 롱숏 모멘텀 팩터이고 이 랩은 롱온리 상위 10종목 동일가중이라 손익 구조가 다르다 - 수치가 같을\n"
              "이유가 없으므로 방향만 본다. 목표변동성은 그 시점까지의 실적으로만 잡는다(전 표본을 쓰면 룩어헤드다).",
              fontsize=7.4, color=INK2, linespacing=1.62)
        y -= .086

        ST.tx(fig, X0, y, "① 자기 변동성이 높을 때 무슨 일이 생기나", fontsize=11.5, weight="bold")
        ST.tx(fig, X1, y + .001, "직전 %d개월 변동성 중앙값 %.2f%%p 로 가른다" % (LOOK, med),
              fontsize=6.6, color=MUTED, ha="right")
        y = ST.table(fig, X0, y - .015, [.170, .060, .110, .080, .110],
                     ["상태", "개월", "월평균 %", "승률", "최악의 달 %"], rows_state,
                     row_h=.017, fs=7.6, hfs=6.8, aligns=["l", "r", "r", "r", "r"],
                     cell_color=lambda i, c: (INK if c == 0 else
                                              (NEG if c == 4 else (MUTED if c in (1, 3) else INK))),
                     zebra=True)
        ST.tx(fig, X0, y - .010,
              "평균은 오히려 높은데 최악의 달만 벌어진다 - 위험이 커진 것이지 기대수익이 나빠진 것이 아니다.",
              fontsize=7.0, color=INK2)
        y -= .034

        ST.tx(fig, X0, y, "② 비중을 그 위험에 맞추면", fontsize=11.5, weight="bold")
        ST.tx(fig, X1, y + .001, "비중 = min(1, 목표 ÷ 직전 %d개월 변동성) · 평균 %.0f%% (최저 %.0f%%)"
              % (LOOK, np.mean(w) * 100, min(w) * 100), fontsize=6.6, color=MUTED, ha="right")
        y = ST.table(fig, X0, y - .015,
                     [.104, .078, .078, .066, .062, .062, .078, .078, .070],
                     ["스타일", "CAGR 원본", "CAGR 관리", "ΔCAGR", "샤프 원본", "샤프 관리",
                      "MDD 원본", "MDD 관리", "ΔMDD"], rows_other,
                     row_h=.017, fs=7.6, hfs=6.4,
                     aligns=["l"] + ["r"] * 8,
                     cell_color=lambda i, c: (INK if c == 0 else
                                              (NEG if c == 3 else
                                               (POS if c == 8 else MUTED))),
                     zebra=True)
        ST.tx(fig, X0, y - .010,
              "셋 다 CAGR 은 내준다 - 남는 비중이 현금이니 당연하다. 갈리는 곳은 그 대가로 무엇을 사느냐다. "
              "모멘텀은 낙폭 %.1f%%p 를,\n고베타는 %.1f%%p 를 산다. 같은 규칙이 아무 데나 통하지 않는다는 뜻이고, "
              "크래시가 모멘텀 고유 현상이라는 문헌과 방향이 같다."
              % (abs(dmdd.get("모멘텀", 0)), abs(dmdd.get("고베타", 0))),
              fontsize=7.0, color=INK2, linespacing=1.55)
        y -= .046

        ST.tx(fig, X0, y, "③ 최악의 달에 실제로 얼마를 덜 맞았나", fontsize=11.5, weight="bold")
        ST.tx(fig, X1, y + .001, "원본 기준 하위 6개월", fontsize=6.6, color=MUTED, ha="right")
        y = ST.table(fig, X0, y - .015, [.086, .066, .092, .092, .080],
                     ["월", "그달 비중", "원본 %", "관리 %", "차이"], rows_worst,
                     row_h=.0165, fs=7.6, hfs=6.8, aligns=["l", "r", "r", "r", "r"],
                     cell_color=lambda i, c: (INK if c == 0 else
                                              (POS if c == 4 else (MUTED if c == 1 else NEG))),
                     zebra=True)
        n_full = sum(1 for i in order if w[i] > .995)
        ST.tx(fig, X0, y - .010,
              "%d개월은 비중이 100%%였다 - 직전 변동성이 낮은 상태에서 온 급락은 이 규칙이 못 막는다. "
              "실제로 벌어 준 자리는 %d개월뿐이고,\n낙폭 개선 %.1f%%p 는 사실상 2026-07 한 달에서 나온 것이다."
              % (n_full, len(order) - n_full, abs(dmdd.get("모멘텀", 0))),
              fontsize=7.0, color=INK2, linespacing=1.55)
        y -= .050

        # 누적 곡선
        ST.tx(fig, X0, y, "④ 누적 곡선 · 시작 = 100", fontsize=11.5, weight="bold")
        ch = .118
        ax = fig.add_axes([X0 + .046, y - .014 - ch, X1 - X0 - .056, ch])
        ax.set_facecolor(PAPER)
        xi = np.arange(len(base))
        ax.plot(xi, pb["nav"] * 100, color=MUTED, lw=1.2, label="원본")
        ax.plot(xi, ps["nav"] * 100, color=ACC, lw=1.8, label="변동성 관리")
        ax.set_xlim(0, len(xi) - 1)
        tk = list(range(0, len(base), 6))
        ax.set_xticks(tk)
        ax.set_xticklabels([ms[WARM + k][2:] for k in tk])
        ax.tick_params(labelsize=6.3, colors=MUTED, length=2, pad=1.5)
        for sp in ax.spines.values():
            sp.set_color(LINE)
        ax.grid(True, color=LINE, lw=.4, alpha=.65); ax.set_axisbelow(True)
        ax.legend(fontsize=6.6, frameon=False, loc="upper left", handlelength=1.8,
                  borderpad=.1, labelspacing=.25)
        y = y - .014 - ch - .020

        ST.tx(fig, X0, y, "⑤ 한계 - 이 표가 증명하지 못하는 것", fontsize=11.5, weight="bold")
        ST.tx(fig, X0, y - .016,
              "· 낙폭 개선의 근거가 사실상 크래시 한 번(2026-07)에 기댄다. 랩 표본에 그것뿐이다.\n"
              "· 그 달은 Daniel & Moskowitz(JFE 2016)가 말한 패닉형 크래시가 아니다 - 진입 직전 시장은\n"
              "  200일선 위였고 VIX 는 16 대였다. 시장 상태를 보는 규칙이었다면 줄이지 못했을 자리다.\n"
              "· 롱온리라 남는 비중은 현금이고 레버리지는 쓰지 않는다. 상방을 그만큼 내준다.\n"
              "· 잘 확립된 문헌과 방향이 같다는 것이 이 결과의 값어치이지, 이 표본이 증명한 것이 아니다.",
              fontsize=7.4, color=INK2, linespacing=1.62)
        y -= .100

        ST.hline(fig, X0, X1, y + .012, RULE, .9)
        ST.tx(fig, X0, y - .008, "그래서 무엇을 하나", fontsize=11.5, weight="bold")
        ST.tx(fig, X0, y - .028,
              "이 규칙은 언제 팔지를 맞히지 않는다. 이미 흔들리고 있는 계열의 크기만 줄인다 - 그래서 예측이 필요 없고,\n"
              "그 점이 스타일 로테이션과 다르다. 대가는 분명하다. CAGR %.1f%%p 를 내주고 낙폭 %.1f%%p 를 산다.\n"
              "그 교환이 남는 장사인지는 이 표본이 답해 주지 못한다 - 크래시가 한 번뿐이기 때문이다. "
              "랩은 이것을 진단 지표로 두고 배포 알파로 취급하지 않는다."
              % (abs(ps["cagr"] - pb["cagr"]), abs(dmdd.get("모멘텀", 0))),
              fontsize=7.4, color=INK2, linespacing=1.62)

        ST.hline(fig, X0, X1, .034, LINE, .6)
        ST.tx(fig, X0, .026,
              "출처 Barroso & Santa-Clara, \"Momentum has its moments\", JFE 116(1), 2015 · "
              "랩 재현은 상위 10종목 동일가중 · 월말 리밸런스 · 비용 0",
              fontsize=6.2, color=MUTED)
        ST.tx(fig, X1, .026, "1 / 1 · %s" % dt.datetime.now().strftime("%Y-%m-%d"),
              fontsize=6.4, color=MUTED, ha="right")
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
        pdf.infodict()["Title"] = "모멘텀 변동성 관리"

    print("→ %s · %dKB" % (OUT, os.path.getsize(OUT) // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
