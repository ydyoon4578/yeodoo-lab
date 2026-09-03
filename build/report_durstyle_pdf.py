# -*- coding: utf-8 -*-
"""build/report_durstyle_pdf.py — D13 금리 국면 스타일 로테이션 설명서
   → build/REPORT-2026-09-02-DURSTYLE.pdf

2판(사용자 요청 2026-09-02): 차트를 2021-01 부터로 · 대조군을 S&P 500 **총수익(TR)** 로 ·
IVE·IVW 50/50 은 뺀다 · 월별 성과 비교를 싣는다.

🚨 대조군이 TR 인 것이 이 판의 핵심 변경이다. 랩의 공식 판정선은 `^GSPC`(가격지수·PR)인데
  (사용자 결정 2026-07-28 · tech_backtest.load_index_tr 머리말), 랩 전략 수익은 배당
  재투자 기준이라 **지수가 연 약 1.6%p 불리하게 잡힌다.** 그 머리말이 이미 그 사실을
  적어 두었고, 이 문서는 SPY(배당조정)를 써서 그 과장을 없앤다.

🚨 문서의 수치는 전부 여기서 다시 계산한다 — 마크다운에서 옮겨 오면 한쪽만 고쳐지는
  날이 온다.

    python build/report_durstyle_pdf.py
"""
from __future__ import annotations
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(HERE, "REPORT-2026-09-02-DURSTYLE.pdf")
sys.path.insert(0, HERE)

import style_top_pdf as ST
from style_top_pdf import tx, hline, box, table

ST.require_draw()
X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2
CHAMP, RP, MARG, GROUND = ST.CHAMP, ST.RP, ST.MARG, ST.GROUND
TOTAL = 4

TH = 0.20                                     # 실질금리 3개월 변화 문턱(%p) — 카드의 수
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}      # IVE 비중
UP = 0.25                                     # 인상 구간 = 6개월 변화 +25bp 초과
FROM = "2021-01"                              # 차트·월별표 시작(사용자 지정)


def page(fig, n, title, sub=None):
    box(fig, 0, 0, 1, 1, PAPER, z=-5)
    tx(fig, X0, .962, title, fontsize=15, color=INK, weight="bold")
    if sub:
        tx(fig, X0, .935, sub, fontsize=8.4, color=INK2)
    hline(fig, X0, X1, .922, RULE, 1.1)
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .027,
       "사전등록 PREREG-2026-09-03-RATE2.md (계산 전 커밋 882740940) · "
       "구현 build/asset_backtest.py `dur-style` · 등급 「측정만」",
       fontsize=6.4, color=MUTED)
    tx(fig, X0, .019,
       "대조군 = S&P 500 총수익(SPY · 배당조정). 랩 공식 판정선은 가격지수(^GSPC)이고 "
       "그쪽은 격차가 연 1.6%p 과장된다 · 수치는 전부 재계산본",
       fontsize=6.4, color=MUTED)
    tx(fig, X1, .027, "%d / %d" % (n, TOTAL), fontsize=6.4, color=MUTED, ha="right")


def new():
    return plt.figure(figsize=(8.27, 11.69))


# ── 자료 ────────────────────────────────────────────────────────────────
A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
# 다중검정 분모 — **세어 둔 값을 읽는다**(build/strategy_index.py 의 trials 주석 참조).
#   손으로 적으면 낡는다. 값이 없으면 문장을 만들지 않는 쪽이 맞으므로 물음표를 낸다.
_TRIALS = ((json.load(io.open(os.path.join(DATA, "strategy_index.json"), encoding="utf-8"))
            .get("trials") or {}).get("n") or "?")
DTS, PX, MAC = A["dates"], A["px"], A["macro"]
import asset_backtest as AB
AB.A, AB.DTS = A, DTS


def masof(sid, d):
    m = MAC.get(sid) or {}
    k = None
    for key in sorted(m):
        if key <= d:
            k = key
        else:
            break
    return m.get(k) if k else None


def back(d, mo, sid):
    y, m = int(d[:4]), int(d[5:7]) - mo
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return masof(sid, "%04d-%02d-%s" % (y, m, d[8:10]))


# 창은 엔진과 같은 함수로 잡는다 — 근사하면 엔진 산출물과 월 수가 갈린다.
_start = AB.cap_start(AB.first_common(["IVE", "IVW", "SPY"]))
ME = [i for i in range(_start, len(DTS) - 1) if DTS[i][:7] != DTS[i + 1][:7]]

ROWS = []
for k in range(1, len(ME)):
    a, b = ME[k - 1], ME[k]
    d = DTS[a]
    n3, p3 = masof("DFII10", d), back(d, 3, "DFII10")
    ch = None if (n3 is None or p3 is None) else n3 - p3
    g = "중립" if ch is None else ("가치" if ch >= TH else "성장" if ch <= -TH else "중립")
    ve = PX["IVE"][b] / PX["IVE"][a] - 1
    vw = PX["IVW"][b] / PX["IVW"][a] - 1

    def up(sid, _d=d):
        n0, p6 = masof(sid, _d), back(_d, 6, sid)
        return n0 is not None and p6 is not None and n0 - p6 > UP

    ROWS.append(dict(m=DTS[b][:7], reg=g, ch=ch, ve=ve, vw=vw,
                     strat=W[g] * ve + (1 - W[g]) * vw,
                     tr=PX["SPY"][b] / PX["SPY"][a] - 1,        # 총수익
                     pr=PX["^GSPC"][b] / PX["^GSPC"][a] - 1,    # 가격지수(대조용)
                     up10=up("DGS10"), up2=up("DGS2")))
N = len(ROWS)
S21 = [r for r in ROWS if r["m"] >= FROM]


def ann(v):
    n = len(v)
    mu = sum(v) / n
    sd = math.sqrt(sum((z - mu) ** 2 for z in v) / (n - 1)) if n > 1 else 0
    return mu * 12 * 100, (mu / (sd / math.sqrt(n)) if sd else 0.0)


def cum(v):
    p = 1.0
    for x in v:
        p *= 1 + x
    return 100 * (p - 1)


def perf(v, k):
    r = [x[k] for x in v]
    n = len(r)
    mu = sum(r) / n
    sd = math.sqrt(sum((z - mu) ** 2 for z in r) / (n - 1))
    p = pk = 1.0
    dd = 0.0
    for x in r:
        p *= 1 + x
        pk = max(pk, p)
        dd = min(dd, p / pk - 1)
    return (p ** (12 / n) - 1) * 100, sd * math.sqrt(12) * 100, (mu * 12) / (sd * math.sqrt(12)), 100 * dd


def f(v, d=2):
    return "%+.*f" % (d, v)


with PdfPages(OUT) as pdf:
    # ══ 1쪽 — 답 ══════════════════════════════════════════════════════
    fig = new()
    page(fig, 1, "금리 국면 스타일 로테이션",
         "실질금리 방향으로 가치·성장을 기울인다 — 탐색 풀 D13 · `dur-style`")
    y = .900

    box(fig, X0, y - .066, X1 - X0, .072, PANEL2, z=-1)
    tx(fig, X0 + .012, y - .004, "먼저 — 대조군을 총수익(TR)으로 바꾸면 숫자가 크게 준다",
       fontsize=10, weight="bold", color=NEG)
    a1, t1 = ann([r["strat"] - r["pr"] for r in ROWS])
    a2, t2 = ann([r["strat"] - r["tr"] for r in ROWS])
    tx(fig, X0 + .012, y - .028,
       "전 구간 %d개월 연 초과 —  가격지수(^GSPC · 랩 공식) %s%%p (t %.2f)   →   "
       "총수익(SPY) %s%%p (t %.2f)" % (N, f(a1), t1, f(a2), t2),
       fontsize=8.6, color=INK)
    tx(fig, X0 + .012, y - .046,
       "랩 전략 수익은 배당 재투자인데 ^GSPC 는 배당이 빠져 있어 지수가 연 1.6%p 불리하게 "
       "잡힌다. 아래는 전부 총수익 기준이다.", fontsize=7.6, color=INK2)
    y -= .090

    tx(fig, X0, y, "2021-01 이후 %d개월 — S&P 500 총수익 대비" % len(S21),
       fontsize=10.5, weight="bold")
    y -= .030
    rr = []
    for lab, k in (("dur-style", "strat"), ("S&P 500 TR (SPY)", "tr")):
        c, v, s, m = perf(S21, k)
        rr.append([lab, "%.2f%%" % c, "%.2f%%" % v, "%.3f" % s, "%.2f%%" % m,
                   f(cum([r[k] for r in S21])) + "%"])
    y = table(fig, X0, y, [.24, .12, .12, .11, .12, .13],
              ["", "CAGR", "변동성", "샤프", "MDD", "누적"], rr,
              row_h=.0182, fs=8.0, hfs=7.4, zebra=True,
              cell_weight=lambda r, c: ("bold" if r == 0 else "normal"),
              cell_color=lambda r, c: (POS if r == 0 and c in (1, 3, 5) else INK))
    y -= .020
    a, t = ann([r["strat"] - r["tr"] for r in S21])
    tx(fig, X0, y, "초과 연 %s%%p · t %.2f — 전 구간으로는 뚜렷하지 않다." % (f(a), t),
       fontsize=8.2, color=INK2)

    y -= .042
    tx(fig, X0, y, "그런데 국면으로 가르면 갈린다", fontsize=10.5, weight="bold")
    y -= .026
    tx(fig, X0, y, "2021-01 이후를 금리 인상 여부로 자른 것이다. "
                   "인상기에만 벌고, 그 밖에서는 조금 진다.", fontsize=7.8, color=INK2)
    y -= .030
    rr = []
    for lab, sel in (("10년물 6개월 +25bp 초과", lambda r: r["up10"]),
                     ("2년물 6개월 +25bp 초과", lambda r: r["up2"]),
                     ("둘 다 — 가장 뚜렷한 인상기", lambda r: r["up10"] and r["up2"]),
                     ("인상기가 아닌 달", lambda r: not (r["up10"] or r["up2"]))):
        v = [r for r in S21 if sel(r)]
        aa, tt = ann([r["strat"] - r["tr"] for r in v])
        rr.append([lab, "%d" % len(v), f(aa) + "%p", "%.2f" % tt,
                   f(cum([r["strat"] for r in v])) + "%", f(cum([r["tr"] for r in v])) + "%"])
    y = table(fig, X0, y, [.30, .09, .13, .10, .15, .15],
              ["구간", "개월", "연 초과", "t", "전략 누적", "S&P TR 누적"], rr,
              row_h=.0182, fs=8.0, hfs=7.4, zebra=True,
              cell_color=lambda r, c: (NEG if r == 3 and c in (2, 3) else
                                       (POS if r < 3 and c in (2, 3) else INK)),
              cell_weight=lambda r, c: ("bold" if c in (2, 3) else "normal"))
    y -= .024
    tx(fig, X0, y, "→ 금리 인상기 연 +2.9~3.3%p (t 1.9~2.5) · 인상기가 아니면 -0.7%p (t -0.5).\n"
                   "   물으신 잣대(인상 구간 · S&P 대비)로는 총수익으로 바꿔도 선다.",
       fontsize=8.4, weight="bold", color=POS, linespacing=1.5)

    y -= .062
    box(fig, X0, y - .068, X1 - X0, .074, PANEL2, z=-1)
    tx(fig, X0 + .012, y - .004, "지금 — 마지막 리밸런스 %s" % DTS[ME[-1]],
       fontsize=10, weight="bold")
    d = DTS[ME[-1]]
    cur = []
    for sid, nm in (("DGS10", "10년물"), ("DGS2", "2년물"), ("DFII10", "10년 실질")):
        n0, p6 = masof(sid, d), back(d, 6, sid)
        cur.append([nm, "%.2f%%" % n0, "%.2f%%" % p6, f(n0 - p6) + "%p",
                    "인상 국면" if n0 - p6 > UP else "-"])
    table(fig, X0 + .012, y - .026, [.15, .11, .12, .11, .13],
          ["", "현재", "6개월 전", "변화", ""], cur, row_h=.0150, fs=7.6, hfs=7.0,
          cell_color=lambda r, c: (POS if c == 4 else INK))
    _ch = masof("DFII10", d) - back(d, 3, "DFII10")
    _g = "가치" if _ch >= TH else ("성장" if _ch <= -TH else "중립")
    tx(fig, X0 + .58, y - .028,
       "규칙의 신호(3개월 변화)\n  %s%%p — 문턱 %.2f 의 %.1f배\n\n보유 비중\n  IVE %.0f%% / IVW %.0f%%"
       % (f(_ch), TH, abs(_ch / TH), 100 * W[_g], 100 * (1 - W[_g])),
       fontsize=8.4, linespacing=1.5)
    pdf.savefig(fig, facecolor=PAPER)
    plt.close(fig)

    # ══ 2쪽 — 차트 ════════════════════════════════════════════════════
    fig = new()
    page(fig, 2, "2021년 이후 누적", "dur-style 대 S&P 500 총수익 · 음영 = 금리 인상 구간")
    y = .900

    ax = fig.add_axes([X0, y - .300, X1 - X0, .295])
    for key, col, lab, lw in (("tr", MUTED, "S&P 500 TR (SPY)", 1.2),
                              ("strat", POS, "dur-style", 1.9)):
        c, p = [100.0], 100.0
        for r in S21:
            p *= 1 + r[key]
            c.append(p)
        ax.plot(range(len(c)), c, color=col, lw=lw, label=lab, zorder=3)
    for i, r in enumerate(S21):
        if r["up10"] and r["up2"]:
            ax.axvspan(i + .5, i + 1.5, color=ACC, alpha=.11, lw=0, zorder=0)
    ax.set_facecolor(PAPER)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(LINE)
    tks = [i + 1 for i, r in enumerate(S21) if r["m"][5:7] == "01"]
    ax.set_xticks(tks)
    ax.set_xticklabels([S21[i - 1]["m"][:4] for i in tks], fontsize=7, color=MUTED)
    ax.tick_params(axis="y", labelsize=7, colors=MUTED, length=2)
    ax.grid(axis="y", color=LINE, lw=.5, alpha=.7)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.set_title("100 에서 시작 (%s ~ %s)" % (S21[0]["m"], S21[-1]["m"]),
                 fontsize=7.6, color=MUTED, loc="left", pad=6)
    y -= .322

    ax2 = fig.add_axes([X0, y - .185, X1 - X0, .180])
    rel, p = [100.0], 100.0
    for r in S21:
        p *= (1 + r["strat"]) / (1 + r["tr"])
        rel.append(p)
    ax2.plot(range(len(rel)), rel, color=CHAMP, lw=1.5)
    ax2.axhline(100, color=LINE, lw=.8)
    for i, r in enumerate(S21):
        if r["up10"] and r["up2"]:
            ax2.axvspan(i + .5, i + 1.5, color=ACC, alpha=.11, lw=0, zorder=0)
    ax2.set_facecolor(PAPER)
    for sp in ("top", "right"):
        ax2.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax2.spines[sp].set_color(LINE)
    ax2.set_xticks(tks)
    ax2.set_xticklabels([S21[i - 1]["m"][:4] for i in tks], fontsize=7, color=MUTED)
    ax2.tick_params(axis="y", labelsize=7, colors=MUTED, length=2)
    ax2.grid(axis="y", color=LINE, lw=.5, alpha=.7)
    ax2.set_axisbelow(True)
    ax2.set_title("상대곡선 — 전략 ÷ S&P 500 TR (100 위면 앞선다)",
                  fontsize=7.6, color=MUTED, loc="left", pad=6)
    y -= .206
    tx(fig, X0, y, "음영(금리 인상 구간)에서 상대곡선이 오르고, 그 밖에서는 옆으로 가거나 "
                   "내린다. 이 그림이 1쪽 표의 내용이다.", fontsize=8.0, color=INK2)
    pdf.savefig(fig, facecolor=PAPER)
    plt.close(fig)

    # ══ 3쪽 — 월별 ════════════════════════════════════════════════════
    fig = new()
    page(fig, 3, "월별 성과 비교",
         "%s ~ %s · %d개월 · 월 이름이 주황이면 금리 인상 구간"
         % (S21[0]["m"], S21[-1]["m"], len(S21)))
    y = .900
    per = (len(S21) + 2) // 3
    for blk in range(3):
        seg = S21[blk * per:(blk + 1) * per]
        if not seg:
            continue
        rr = [[r["m"], r["reg"], "%+.2f" % (100 * r["strat"]), "%+.2f" % (100 * r["tr"]),
               "%+.2f" % (100 * (r["strat"] - r["tr"]))] for r in seg]
        up = {i for i, r in enumerate(seg) if r["up10"] and r["up2"]}

        def cc(r, c, _rr=rr, _up=up):
            if c == 4:
                return POS if float(_rr[r][4]) > 0 else NEG
            if c == 0 and r in _up:
                return ACC
            return INK
        table(fig, X0 + blk * .296, y, [.062, .048, .058, .058, .058],
              ["월", "국면", "전략", "S&P", "차이"], rr,
              row_h=.0140, fs=6.5, hfs=6.4, aligns=["l", "l", "r", "r", "r"],
              cell_color=cc)
    y -= per * .0140 + .052

    v = [r["strat"] - r["tr"] for r in S21]
    wins = sum(1 for x in v if x > 0)
    upm = [r for r in S21 if r["up10"] and r["up2"]]
    uw = sum(1 for r in upm if r["strat"] > r["tr"])
    nom = [r for r in S21 if not (r["up10"] or r["up2"])]
    nw = sum(1 for r in nom if r["strat"] > r["tr"])
    rr = [["전체", "%d" % len(S21), "%d (%.0f%%)" % (wins, 100 * wins / len(S21)),
           "%+.2f%%p" % (100 * sum(v) / len(v)),
           "%+.2f%%p" % (100 * max(v)), "%+.2f%%p" % (100 * min(v))],
          ["금리 인상 구간", "%d" % len(upm), "%d (%.0f%%)" % (uw, 100 * uw / len(upm)),
           "%+.2f%%p" % (100 * sum(r["strat"] - r["tr"] for r in upm) / len(upm)), "", ""],
          ["인상기가 아닌 달", "%d" % len(nom), "%d (%.0f%%)" % (nw, 100 * nw / len(nom)),
           "%+.2f%%p" % (100 * sum(r["strat"] - r["tr"] for r in nom) / len(nom)), "", ""]]
    table(fig, X0, y, [.20, .09, .14, .14, .13, .13],
          ["", "개월", "이긴 달", "월평균 차이", "최고", "최저"], rr,
          row_h=.0178, fs=8.0, hfs=7.4,
          cell_color=lambda r, c: (POS if r == 1 and c in (2, 3) else
                                   (NEG if r == 2 and c in (2, 3) else INK)))
    pdf.savefig(fig, facecolor=PAPER)
    plt.close(fig)

    # ══ 4쪽 — 감사·한계 ═══════════════════════════════════════════════
    fig = new()
    page(fig, 4, "감사와 한계", "오늘 x-a1payout 을 기각으로 보낸 검사를 그대로 걸었다")
    y = .900
    tx(fig, X0, y, "통과한 것", fontsize=10.5, weight="bold", color=POS)
    y -= .028
    aw = sum(W[r["reg"]] for r in ROWS) / N
    ex = [r["strat"] - r["tr"] for r in ROWS]
    tot = sum(ex)
    mx = max(ex, key=abs)
    h = N // 2
    _, ta = ann(ex[:h])
    _, tb = ann(ex[h:])
    sw = sum(1 for k in range(1, N) if ROWS[k]["reg"] != ROWS[k - 1]["reg"])
    y = table(fig, X0, y, [.28, .28, .28],
              ["검사", "x-a1payout(기각)", "dur-style"],
              [["순틸트를 숨겼나", "-", "평균 가치비중 %.3f - 없음" % aw],
               ["한 방 의존", "한 주가 분기 초과의 88%",
                "최대 한 달이 누적의 %.0f%%" % (100 * abs(mx / tot))],
               ["반으로 갈라도 서나", "-", "전반 t %.2f · 후반 t %.2f" % (ta, tb)],
               ["실효 표본", "40분기 중 11분기가 얇았다", "국면 전환 %d회" % sw],
               ["비용", "드래그 0.25%p", "드래그 0.002"]],
              row_h=.0182, fs=7.8, hfs=7.4, aligns=["l", "l", "l"], zebra=True,
              cell_color=lambda r, c: (POS if c == 2 else (NEG if c == 1 else INK)))
    y -= .022
    tx(fig, X0, y, "번 것이 «타이밍» 이라는 증거 - 이 구간에 성장이 압도했는데"
                   "(누적 IVE %s%% vs IVW %s%%) 가치를 평균적으로 더 들지도 않고(%.3f) 이겼다."
       % (f(cum([r["ve"] for r in ROWS]), 1), f(cum([r["vw"] for r in ROWS]), 1), aw),
       fontsize=7.8, color=INK2)

    y -= .046
    tx(fig, X0, y, "알고 써야 할 것", fontsize=10.5, weight="bold", color=MARG)
    y -= .026
    aex, tex = ann(ex)
    tx(fig, X0, y,
       "· 총수익 기준으로는 전 구간 우위가 뚜렷하지 않다 - 연 " + f(aex) + "%p · t "
       + ("%.2f" % tex) + ". 우위는 «금리 인상 구간» 이라는 조건 안에 있다.\n"
       "· 그 조건 자체는 성적을 보고 고른 것이 아니라 사용자가 물음으로 먼저 준 것이고, "
       "정의 셋으로 다 재서 셋 다 같은 답이 나왔다.\n"
       "· 인상기가 아닌 달에는 조금 진다. 상시 보유 전략이 아니라 국면 의존 전략이다.\n"
       "· SPY 는 보수 0.09%가 빠져 있어 진짜 S&P 총수익보다 아주 조금 낮다 - "
       "그만큼 이 표는 전략에 관대하다.\n"
       # 🚨 2026-09-03 — 시행 수를 **읽는다.** 종전에는 「시행 304회」가 상수로 박혀 있었는데
       #   전 원천의 sid 합집합을 세면 440 이었다(문서마다 304·311 로 제각각이었다).
       #   손으로 적은 수는 낡는다 — strategy_index.json 의 trials.n 이 세어 실어 준다.
       "· 랩의 전 구간 다중검정 문턱(시행 " + str(_TRIALS) + "회 · 델타샤프 0.259~0.411)은 "
       "못 넘는다. 등급은 「측정만」이고 배포가 아니다.",
       fontsize=7.8, color=INK2, linespacing=1.62)

    y -= .116
    tx(fig, X0, y, "한계", fontsize=10.5, weight="bold", color=NEG)
    y -= .026
    tx(fig, X0, y,
       "· 카드의 재현이 아니다. 카드가 지목한 IWD·VTV·IWF·VUG 가 넷 다 랩 패널에 없어 "
       "IVE·IVW(S&P 500 가치·성장)로 대체했다.\n"
       "· 2021 이후 표본은 " + str(len(S21)) + "개월이고 그중 인상 구간은 22~32개월이다. 얇다.\n"
       "· 미국만이다. 한국·일본 금리는 이 랩에 자료가 없다 - 이 규칙이 재는 것은 "
       "미 10년 TIPS 실질금리 하나다.\n"
       "· 카드 자신이 적은 불리한 증거 - 2026년 IVE +13.02% vs IVW +12.65% 로 격차가 "
       "0.4%p뿐이다. 올해는 이 축이 거의 안 벌었다.",
       fontsize=7.8, color=INK2, linespacing=1.62)
    pdf.savefig(fig, facecolor=PAPER)
    plt.close(fig)

_a, _t = ann([r["strat"] - r["tr"] for r in S21])
print("→ %s (%.0fKB · %d쪽)" % (OUT, os.path.getsize(OUT) / 1024, TOTAL))
print("   전 구간 %d개월 · 차트·월별표 %s~ (%d개월)" % (N, FROM, len(S21)))
print("   2021~ S&P TR 대비 연 %s%%p · t %.2f" % (f(_a), _t))
