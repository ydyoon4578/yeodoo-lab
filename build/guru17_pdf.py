# -*- coding: utf-8 -*-
"""build/guru17_pdf.py — 운용사별 13F 복제 17종 진단 PDF → data/guru17_portfolios.pdf

## 이 문서는 성과 자료가 아니라 진단물이다

build/style_top_pdf.py 와 같은 판형·색·표를 쓰지만 **편집 순서가 반대다.** 저쪽은
전략 자료라 전략부터 펼치지만, 이쪽이 묻는 것은 하나다 —
**"유명 헤지펀드를 따라 사면 되는가."**

그래서 1쪽이 답(결합검정·지속성·사전규칙)이고, 운용사별 순위와 곡선은 그 뒤 **부록**이다.
순서를 뒤집으면 "누가 이겼나" 하이라이트가 되고, 그 순간 이 문서는 사후선택된 명단에서
최고를 골라 자랑하는 물건이 된다. 쪽마다 머리에 '부록'이라 적는 이유도 같다.
(사양·게이트·경고문의 정본은 build/guru17_backtest.py 다. 여기서 다시 쓰지 않는다.)

## 숫자는 어디서 오나 — 두 곳을 섞지 않는다

  표의 모든 수치   data/guru17.json 그대로. 화면(guru17.html)과 한 글자도 다르면 안 되므로
                 이 파일에서 다시 계산하지 않는다.
  곡선의 월별 계열  guru17_backtest.compute() 를 다시 돌려 얻는다. JSON 에는 요약만 있고
                 월별 계열이 없기 때문이다.
  최신 보유       data/guru.json 의 managers[].holds (13F 최신 분기).

  두 소스가 어긋나면(구간·운용사 수가 다르면) 그리지 않고 멈춘다 — 낡은 JSON 위에
  새 곡선을 얹으면 표와 그림이 다른 것을 말하게 된다.

  python build/guru17_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949) 가드
except Exception: pass

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, rcParams
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru17_portfolios.pdf")

sys.path.insert(0, HERE)
import guru17_backtest as GB

TOP_HOLD = 8            # 블록에 적는 최신 보유 상위 종목 수

# 한글 폰트 — Windows(맑은 고딕)에서 만들던 문서라 mac/리눅스에서도 같은 꼴이 나오게 고른다.
#   ⚠ 폰트를 못 찾으면 한글이 전부 두부(□)로 나온다. 조용히 그리지 말고 멈춘다.
_CAND = [r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf",
         "/System/Library/Fonts/AppleSDGothicNeo.ttc",
         "/Library/Fonts/NanumGothic.ttf",
         "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]
for _p in _CAND:
    if os.path.exists(_p):
        try: font_manager.fontManager.addfont(_p)
        except Exception: pass
_HAVE = {f.name for f in font_manager.fontManager.ttflist}
KFONT = next((n for n in ("Malgun Gothic", "Apple SD Gothic Neo", "NanumGothic",
                          "Nanum Gothic", "Noto Sans CJK KR") if n in _HAVE), None)
if not KFONT:
    raise SystemExit("한글 폰트를 찾지 못했다 — 맑은 고딕·애플 SD 고딕·나눔고딕 중 하나가 필요하다. "
                     "없이 그리면 문서 전체가 두부(□)로 나온다.")
rcParams["font.family"] = KFONT
rcParams["axes.unicode_minus"] = False

# 색 — style_top_pdf.py 와 같은 팔레트(사이트 밝은 테마)를 그대로 쓴다.
PAPER, GROUND, PANEL2 = "#FFFDF5", "#FAF7EC", "#F3EFE1"
INK, INK2, MUTED = "#14181D", "#3C444D", "#6A737D"
LINE, RULE = "#E4DFD0", "#C8C0AC"
POS, NEG, ACC = "#0E8A54", "#A64B3B", "#8A6B00"
CHAMP, RP, MARG = "#2C6E8F", "#7A5AA6", "#B25E12"
HEAD_BG, ZEBRA = PANEL2, GROUND
MGR, BEN = ACC, CHAMP                    # 복제 곡선 · 같은 풀 동일가중 대조군

X0, X1 = .058, .942


# ── 그리기 도구 (style_top_pdf.py 와 같은 규약) ──────────────────────────────
def tx(fig, x, y, s, **kw):
    kw.setdefault("color", INK); kw.setdefault("fontsize", 8)
    kw.setdefault("va", "top"); kw.setdefault("ha", "left")
    return fig.text(x, y, s, **kw)


def hline(fig, x0, x1, y, color=LINE, lw=.7):
    fig.add_artist(Line2D([x0, x1], [y, y], color=color, lw=lw,
                          transform=fig.transFigure, zorder=3))


def box(fig, x, y, w, h, fc, ec="none", lw=0, z=0):
    fig.add_artist(Rectangle((x, y), w, h, transform=fig.transFigure, facecolor=fc,
                             edgecolor=ec, lw=lw, zorder=z))


def plain(s):
    """JSON 원문의 **강조** 마크다운을 벗긴다 — matplotlib 은 마크다운을 모른다.

    벗기기만 하고 강조를 다른 표시로 바꾸지 않는다. 이 문서에서 강조가 필요한 자리는
    색(NEG)으로 이미 구분하고 있어, 별표를 기호로 갈아 끼우면 표시가 두 벌이 된다.
    """
    return str(s).replace("**", "")


def wrap(s, n):
    """글자수 기준 줄바꿈. 한글은 단어 경계가 공백과 무관해 폭 기준으로 자른다."""
    out, cur = [], ""
    for w in str(s).split(" "):
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= n:
            cur += " " + w
        else:
            out.append(cur); cur = w
        while len(cur) > n:                 # 공백 없는 긴 한글 덩어리
            out.append(cur[:n]); cur = cur[n:]
    if cur:
        out.append(cur)
    return out


def num(v, d=2, sign=True):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return ("%+." + str(d) + "f") % v if sign else ("%." + str(d) + "f") % v


def table(fig, x0, y_top, widths, header, rows, *, row_h=.0150, fs=7.2, hfs=6.8,
          aligns=None, cell_color=None, zebra=False):
    """머리글 + 본문 표. 반환은 표 아래쪽 y. style_top_pdf.py 의 table() 과 같은 꼴."""
    n = len(widths)
    aligns = aligns or (["l"] + ["r"] * (n - 1))
    xs, acc = [], x0
    for w in widths:
        xs.append(acc); acc += w
    tot = acc - x0

    box(fig, x0, y_top - row_h, tot, row_h, HEAD_BG, z=0)
    for j, h in enumerate(header):
        a = aligns[j]
        px = xs[j] + (.004 if a == "l" else widths[j] - .004)
        tx(fig, px, y_top - .0035, str(h), fontsize=hfs, color=MUTED,
           ha="left" if a == "l" else "right", weight="bold")
    y = y_top - row_h
    hline(fig, x0, x0 + tot, y, RULE, .8)

    for i, r in enumerate(rows):
        if zebra and i % 2 == 1:
            box(fig, x0, y - row_h, tot, row_h, ZEBRA, z=0)
        for j, c in enumerate(r):
            a = aligns[j]
            px = xs[j] + (.004 if a == "l" else widths[j] - .004)
            col = INK
            if cell_color:
                col = (cell_color(i, j, c) or INK)
            tx(fig, px, y - .0035, str(c), fontsize=fs, color=col,
               ha="left" if a == "l" else "right")
        y -= row_h
        hline(fig, x0, x0 + tot, y, LINE, .5)
    return y


def footer(fig, page, total, gen):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .026, "운용사별 13F 복제 진단 · 대조군은 같은 풀 동일가중(월 리밸) · "
                      "비용 0 · 13F는 롱온리·분기말·45일 지연 · 전략이 아니라 진단물이다",
       fontsize=6.4, color=MUTED)
    tx(fig, X1, .026, "%d / %d · %s" % (page, total, gen), fontsize=6.4, color=MUTED, ha="right")


def new_page():
    fig = plt.figure(figsize=(8.27, 11.69))       # A4
    fig.patch.set_facecolor(PAPER)
    return fig


def navs(r):
    """월수익 배열 → 100 기준 NAV."""
    return 100.0 * np.cumprod(1.0 + np.asarray(r, float))


def ax_at(fig, x, y, w, h):
    ax = fig.add_axes([x, y, w, h])
    ax.set_facecolor(PAPER)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE); ax.spines[s].set_linewidth(.7)
    ax.tick_params(labelsize=6, colors=MUTED, length=2, width=.6)
    ax.grid(True, axis="y", color=LINE, lw=.5, alpha=.9)
    ax.set_axisbelow(True)
    return ax


# ── 1쪽: 판정 ────────────────────────────────────────────────────────────────
def draw_verdict(fig, D, total, gen):
    hl = D.get("headline") or {}
    sp = D.get("span") or {}
    y = .960
    tx(fig, X0, y, "유명 헤지펀드를 따라 사면 되는가", fontsize=19, weight="bold")
    y -= .028
    tx(fig, X0, y, "13F 공시로 %s개 운용사 포트폴리오를 복제해 %s ~ %s (%s개월) 측정한 결과다. "
                   "전략이 아니라 진단물이다."
       % (len(D.get("managers") or []), sp.get("start", "—"), sp.get("end", "—"),
          sp.get("n_months", "—")), fontsize=8.4, color=INK2)
    y -= .030

    # ── 세 줄 답 ──────────────────────────────────────────────────────────
    grs, per, pre = hl.get("grs") or {}, hl.get("persistence") or {}, hl.get("prereg_rule") or {}
    mul = hl.get("multiplicity") or {}
    cards = [
        ("① 알파가 전부 0인가 — 결합검정(GRS)",
         "F = %s (df %s, %s) · p = %s" % (grs.get("F", "—"), grs.get("df1", "—"),
                                          grs.get("df2", "—"), grs.get("p", "—")),
         "%s곳 · 공통 %s개월. p가 크면 '알파가 전부 0'을 기각하지 못한다는 뜻이며, "
         "알파가 없다는 증명이 아니다 — 이 표본에는 그것을 가릴 힘이 없다."
         % (grs.get("n_managers", "—"), grs.get("months", "—"))),
        ("② 잘한 곳이 계속 잘하는가 — 지속성",
         "스피어만 %s (p = %s) · 상위군 다음 구간 알파 %s%%p · 하위군 %s%%p"
         % (per.get("spearman", "—"), per.get("spearman_p", "—"),
            num(per.get("top_next"), 2), num(per.get("bottom_next"), 2)),
         "전반기(%s~%s) 알파로 후반기(%s~%s)를 예고할 수 있는지 %s곳으로 잰 것이다."
         % tuple(list(per.get("split") or ["—"] * 4) + [per.get("n", "—")])),
        ("③ 규칙으로 돌리면 되는가 — 사전규칙",
         "%s · 알파 %s%%p · 베타 %s · t = %s"
         % (pre.get("verdict", "—"), num(pre.get("alpha"), 2), pre.get("beta", "—"),
            pre.get("t", "—")),
         "%s (%s ~ %s · %s개월). 매년 명단이 바뀌므로 사후선택이 아니다."
         % (pre.get("rule", "—"), pre.get("start", "—"), pre.get("end", "—"),
            pre.get("n_months", "—"))),
    ]
    for i, (h, big, sub) in enumerate(cards):
        top = y
        box(fig, X0, top - .086, X1 - X0, .086, GROUND, z=0)
        box(fig, X0, top - .086, .0035, .086, ACC, z=1)
        tx(fig, X0 + .014, top - .008, h, fontsize=8.2, weight="bold", color=INK2)
        tx(fig, X0 + .014, top - .028, big, fontsize=12.5, weight="bold", color=INK)
        yy = top - .050
        for ln in wrap(sub, 96):
            tx(fig, X0 + .014, yy, ln, fontsize=7.0, color=MUTED)
            yy -= .0115
        y = top - .096

    # ── 다중검정 ──────────────────────────────────────────────────────────
    y -= .006
    tx(fig, X0, y, "다중검정 — 개별 유의 건수", fontsize=9.5, weight="bold")
    y -= .020
    tx(fig, X0, y, "운용사 %s곳을 한 번에 검정한다. 보정 후 유의: Bonferroni %s건 · Holm %s건 · "
                   "BH(10%%) %s건." % (mul.get("m", "—"), mul.get("bonferroni", "—"),
                                      mul.get("holm", "—"), mul.get("bh10", "—")),
       fontsize=7.6, color=INK2)
    y -= .015
    tx(fig, X0, y, "유의 0건은 예상된 결과이며 알파 부재의 증거가 아니다 — 이 문장은 결과를 "
                   "보기 전에 사양에 적어 둔 것이다.", fontsize=7.6, color=NEG)
    y -= .028

    # ── 알파로 쓰면 안 되는 이유 ───────────────────────────────────────────
    tx(fig, X0, y, "이 표를 알파 발굴로 쓰면 안 되는 이유", fontsize=9.5, weight="bold")
    y -= .022
    for i, s in enumerate(D.get("not_alpha") or []):
        tx(fig, X0 + .004, y, "%d" % (i + 1), fontsize=7.4, color=NEG, weight="bold")
        for ln in wrap(plain(s), 104):
            tx(fig, X0 + .020, y, ln, fontsize=7.0, color=INK2)
            y -= .0118
        y -= .004

    # ── 사양 ──────────────────────────────────────────────────────────────
    y -= .008
    tx(fig, X0, y, "사전 등록 사양 — 결과를 보기 전에 고정했다", fontsize=9.5, weight="bold")
    y -= .020
    SPL = [("리밸런스", "rebalance"), ("룩어헤드", "lookahead_guard"), ("비중", "weights"),
           ("보유", "between"), ("대조군", "bench"), ("무위험", "rf"), ("게이트", "gates")]
    spec = D.get("spec") or {}
    rows = []
    for lab, k in SPL:
        v = spec.get(k)
        if v:
            rows.append((lab, v))
    for lab, v in rows:
        lns = wrap(plain(v), 88)
        tx(fig, X0 + .004, y, lab, fontsize=7.0, color=MUTED, weight="bold")
        for j, ln in enumerate(lns):
            tx(fig, X0 + .085, y, ln, fontsize=7.0, color=INK2)
            y -= .0112
        y -= .002

    # ── 알파 분포와 검정 문턱 ──────────────────────────────────────────────
    # 1쪽 아래가 비어 있었다. 채우려고 넣는 그림이 아니라, '유의 0건'이 무슨 뜻인지는
    # 알파 막대와 문턱선을 나란히 놓아야만 보이기 때문이다 — 표로는 안 보인다.
    live = [m for m in (D.get("managers") or []) if m.get("alpha") is not None]
    if live and y > .200:
        y -= .012
        tx(fig, X0, y, "알파와 검정 문턱 — 왜 유의 0건인가", fontsize=9.5, weight="bold")
        y -= .018
        tx(fig, X0, y, "막대는 운용사별 알파(%p), 가로선은 그 운용사의 표준오차 ±2배다. "
                       "선이 0을 지나면 개별로도 유의하지 않다.", fontsize=7.0, color=MUTED)
        y -= .014
        ch_h = min(.150, y - .075)
        # 축 왼쪽에 운용사 이름이 붙는다 — 그만큼 안으로 들여야 이름이 안 잘린다.
        NAMW = .112
        ax = ax_at(fig, X0 + NAMW, y - ch_h, (X1 - X0) - NAMW, ch_h)
        ax.grid(False)
        ax.grid(True, axis="x", color=LINE, lw=.5)
        vals = [(mm["alpha"], mm["name"], mm.get("t")) for mm in live]
        vals.sort(key=lambda z: z[0])
        ys = np.arange(len(vals))
        ax.barh(ys, [v[0] for v in vals],
                color=[POS if v[0] > 0 else NEG for v in vals], height=.62, zorder=3)
        # 표준오차 = 알파 / t. t 가 0 근처면 발산하므로 그 경우는 막대만 둔다.
        for i, (a_, nm, t_) in enumerate(vals):
            if t_ and abs(t_) > .05:
                se = abs(a_ / t_)
                ax.plot([a_ - 2 * se, a_ + 2 * se], [i, i], color=MUTED, lw=.8, zorder=4)
                ax.plot([a_ - 2 * se, a_ + 2 * se], [i, i], marker="|", ms=3,
                        color=MUTED, lw=0, zorder=4)
        ax.axvline(0, color=INK, lw=.8, zorder=5)
        ax.set_yticks(ys)
        ax.set_yticklabels([v[1][:18] for v in vals], fontsize=5.8)
        ax.set_xlabel("알파 %p (연율, 같은 풀 동일가중 대조군 기준)", fontsize=6, color=MUTED)
        ax.set_ylim(-.7, len(vals) - .3)
    footer(fig, 1, total, gen)


# ── 2쪽: 순위 부록 ───────────────────────────────────────────────────────────
def draw_ranking(fig, D, total, gen, page):
    ms = D.get("managers") or []
    live = [m for m in ms if m.get("alpha") is not None]
    dead = [m for m in ms if m.get("alpha") is None]
    y = .960
    tx(fig, X0, y, "부록 A — 운용사별 순위", fontsize=17, weight="bold")
    y -= .024
    tx(fig, X0, y, "알파 내림차순. ※ 이 명단은 2026년 시점의 유명세로 손으로 고른 것이므로, "
                   "1위가 '가장 잘하는 운용사'라는 뜻이 아니다.", fontsize=7.6, color=NEG)
    y -= .014
    tx(fig, X0, y, "알파·베타·t·p 는 같은 풀 동일가중 대조군에 대한 CAPM 회귀 결과다. "
                   "p 가 작아 보이는 곳도 다중검정 보정 후에는 유의 0건이다(1쪽).",
       fontsize=7.4, color=MUTED)
    y -= .024

    rows = []
    for i, m in enumerate(live):
        mt, bh = m.get("metrics") or {}, m.get("bench") or {}
        rows.append((str(i + 1), m["name"][:22], str(m.get("n_months", "—")),
                     num(m.get("alpha"), 2), num(mt.get("cagr"), 1), num(bh.get("cagr"), 1),
                     "%.3f" % m["beta"] if m.get("beta") is not None else "—",
                     "%.2f" % m["t"] if m.get("t") is not None else "—",
                     "%.4f" % m["p"] if m.get("p") is not None else "—",
                     num(mt.get("mdd"), 1)))

    def cc(i, j, c):
        if j in (3, 4, 5, 9):
            try:
                return POS if float(str(c).replace("%", "")) > 0 else NEG
            except Exception:
                return INK
        return INK

    y = table(fig, X0, y, [.036, .224, .056, .080, .082, .082, .066, .062, .076, .080],
              ["#", "운용사", "개월", "알파%p", "복제 CAGR", "대조군 CAGR", "베타", "t", "p", "MDD"],
              rows, aligns=["r", "l", "r", "r", "r", "r", "r", "r", "r", "r"],
              cell_color=cc, zebra=True)

    y -= .026
    tx(fig, X0, y, "성과를 내지 않은 곳", fontsize=9.5, weight="bold")
    y -= .020
    for m in dead:
        tx(fig, X0 + .004, y, "%s — %s" % (m["name"], m.get("verdict", "—")),
           fontsize=7.6, weight="bold", color=INK2)
        y -= .0130
        for ln in wrap(plain(m.get("why", "")), 100):
            tx(fig, X0 + .020, y, ln, fontsize=7.0, color=MUTED)
            y -= .0112
        y -= .005
    footer(fig, page, total, gen)


# ── 운용사 한 블록(반 쪽) ────────────────────────────────────────────────────
BLOCK_TOPS = (.948, .496)   # 쪽 머리 안내가 세 줄이라 첫 블록을 그만큼 내렸다


def draw_block(fig, top, m, S, HOLD):
    """m = guru17.json 의 운용사 한 건 · S = compute() 의 월별 계열 · HOLD = 최신 보유."""
    mt, bh = m.get("metrics") or {}, m.get("bench") or {}
    tx(fig, X0, top, m["name"], fontsize=14.5, weight="bold")
    tx(fig, X1, top + .0015, "CIK %s" % m["cik"], fontsize=7.4, color=MUTED, ha="right")
    rng = ("%s ~ %s · " % (m["start"], m["end"])) if m.get("start") and m.get("end") else ""
    tx(fig, X1, top - .0095, "%s%s개월 · 분기 %s회"
       % (rng, m.get("n_months", "—"), m.get("n_quarters", "—")),
       fontsize=6.6, color=MUTED, ha="right")

    # ── 곡선 ── 복제 vs 같은 풀 동일가중. 배수 차이가 커서 로그 축으로 그린다.
    CH_H, CH_W = .140, .470
    ch_top = top - .030
    ax = ax_at(fig, X0, ch_top - CH_H, CH_W, CH_H)
    if S:
        n, b_ = navs(S["r"]), navs(S["b"])
        xs = np.arange(len(n))
        ax.plot(xs, n, color=MGR, lw=1.5, zorder=4)
        ax.plot(xs, b_, color=BEN, lw=1.2, zorder=3)
        ax.set_yscale("log")
        ax.axhline(100, color=RULE, lw=.6, zorder=2)
        mm = S["months"]
        step = max(1, len(mm) // 5)
        ticks = list(range(0, len(mm), step))
        ax.set_xticks(ticks)
        ax.set_xticklabels([mm[i][:4] for i in ticks], fontsize=6)
        ax.set_xlim(0, len(mm) - 1)
        ax.set_ylabel("100 = 시작 (로그)", fontsize=6, color=MUTED)
    else:
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(.5, .5, "월별 계열 없음 — 성과를 내지 않은 운용사다", ha="center", va="center",
                fontsize=7.5, color=MUTED, transform=ax.transAxes)

    # 범례는 그림 **안** 왼쪽 위에 둔다. 축 아래에 두면 연도 눈금 글자와 겹쳐 연도가 안 읽힌다.
    if S:
        ax.legend(handles=[Line2D([], [], color=MGR, lw=1.5, label="복제"),
                           Line2D([], [], color=BEN, lw=1.2, label="같은 풀 동일가중(대조군)")],
                  loc="upper left", fontsize=5.8, frameon=True, framealpha=.92,
                  facecolor=PAPER, edgecolor=LINE, borderpad=.35, handlelength=1.6,
                  labelcolor=INK2)

    # ── 오른쪽 지표 ───────────────────────────────────────────────────────
    rx = X0 + .500
    ry = top - .030
    if m.get("alpha") is None:
        box(fig, rx, ry - .086, X1 - rx, .086, GROUND, z=0)
        box(fig, rx, ry - .086, .0030, .086, NEG, z=1)
        tx(fig, rx + .012, ry - .008, m.get("verdict", "—"), fontsize=10, weight="bold", color=NEG)
        yy = ry - .030
        for ln in wrap(plain(m.get("why", "")), 44):
            tx(fig, rx + .012, yy, ln, fontsize=6.8, color=INK2)
            yy -= .0110
    else:
        rows = [("CAGR", num(mt.get("cagr"), 2), num(bh.get("cagr"), 2)),
                ("변동성", num(mt.get("vol"), 2, False), num(bh.get("vol"), 2, False)),
                ("샤프", "%.3f" % mt["sharpe"] if mt.get("sharpe") is not None else "—",
                 "%.3f" % bh["sharpe"] if bh.get("sharpe") is not None else "—"),
                ("MDD", num(mt.get("mdd"), 2), num(bh.get("mdd"), 2))]

        def cc(i, j, c):
            if j == 0:
                return INK2
            try:
                return POS if float(c) > 0 else NEG
            except Exception:
                return INK
        ry = table(fig, rx, ry, [.118, .124, .126], ["지표", "복제", "대조군"], rows,
                   aligns=["l", "r", "r"], cell_color=cc, fs=7.4)
        ry -= .015
        tx(fig, rx, ry, "CAPM (대조군 기준)", fontsize=7.4, weight="bold", color=INK2)
        ry -= .016
        acol = POS if (m.get("alpha") or 0) > 0 else NEG
        tx(fig, rx, ry, "알파", fontsize=7.2, color=MUTED)
        tx(fig, rx + .030, ry, "%s%%p" % num(m.get("alpha"), 2), fontsize=9.5,
           weight="bold", color=acol)
        tx(fig, rx + .118, ry, "베타 %s · t %s · p %s"
           % ("%.3f" % m["beta"] if m.get("beta") is not None else "—",
              "%.2f" % m["t"] if m.get("t") is not None else "—",
              "%.4f" % m["p"] if m.get("p") is not None else "—"),
           fontsize=7.2, color=INK2)
        ry -= .019

        # 연도 집중도 — 알파가 몇 해에 몰려 있나(한 해를 빼서 부호가 뒤집히면 정보량은 사건 한둘이다)
        for lab, dd, key in (("한 해를 빼면", m.get("drop_worst_year"), "year"),
                             ("세 해를 빼면", m.get("drop_worst3_years"), "years")):
            if not dd:
                continue
            ys = dd.get(key)
            ys = "·".join(ys) if isinstance(ys, list) else str(ys)
            tx(fig, rx, ry, lab, fontsize=6.9, color=MUTED)
            tx(fig, rx + .075, ry, "%s 제외 → 알파 %s%%p" % (ys, num(dd.get("alpha"), 2)),
               fontsize=6.9, color=INK2)
            ry -= .0122
    # ── 아래 왼쪽: 최신 13F 보유 ───────────────────────────────────────────
    by = ch_top - CH_H - .034
    if HOLD:
        # ⚠ holds 는 신고 전체(유니버스 밖 포함)다. uni_val 로 나누면 100%를 훌쩍 넘는다
        #   (듀케인 실측: 유니버스 내 10.7% → 상위 종목이 169%로 찍혔다).
        #   분모는 신고 총액(total_val)으로 두고, 유니버스 밖은 '밖'으로 표시한다.
        tot = HOLD.get("total_val") or 0
        upct = HOLD.get("uni_pct")
        rows = []
        for h in (HOLD.get("holds") or [])[:TOP_HOLD]:
            w = (h.get("v") or 0) / tot * 100 if tot else None
            # 티커가 없으면 CUSIP(#8676EP103)이 그대로 온다 — 칸을 넘어 종목명을 덮는다.
            tk = str(h.get("t") or "—")
            if len(tk) > 6:
                tk = tk[:6] + "…"
            rows.append((tk, (h.get("nm") or "")[:22],
                         "%.1f" % w if w is not None else "—",
                         "밖" if h.get("off") else "", h.get("chg") or "—"))

        def hc(i, j, c):
            return MARG if (j == 3 and c) else INK
        tx(fig, X0, by, "최신 13F 보유 상위 %d" % TOP_HOLD, fontsize=7.2, weight="bold", color=INK2)
        tx(fig, X0 + .105, by, "기준일 %s · 신고 총액 대비 비중" % (HOLD.get("_as_of") or "—"),
           fontsize=6.5, color=MUTED)
        table(fig, X0, by - .010, [.052, .186, .050, .028, .054],
              ["티커", "종목", "비중%", "", "직전 대비"], rows,
              aligns=["l", "l", "r", "c", "r"], fs=7.0, hfs=6.5, zebra=True, cell_color=hc)
        if upct is not None:
            tx(fig, X0, by - .010 - .0150 * (len(rows) + 1) - .009,
               "'밖'은 유니버스(518종목) 밖 — 복제에 안 담긴다. 이 운용사는 신고액의 "
               "%.1f%%만 유니버스 안이다." % upct, fontsize=6.4, color=MARG)

    # ── 아래 오른쪽: 자료 품질 + 이 곡선이 무엇이 아닌지 ──────────────────
    # 상황별 — 위 칸에 두면 아래 줄을 침범한다. '월평균이며 서술이다'는 블록마다 같은 말이라
    #   쪽 머리로 올렸다(여기서는 제목에 '월평균'만 남긴다).
    cx = X0 + .395
    cond = (m.get("cond") or {})
    up, dn = cond.get("up") or {}, cond.get("down") or {}
    if up or dn:
        tx(fig, cx, by, "상황별 월평균", fontsize=7.2, weight="bold", color=INK2)
        cy = by - .013
        for lab, c in (("상승월", up), ("하락월", dn)):
            tx(fig, cx, cy, "%s %s개" % (lab, c.get("n", "—")), fontsize=6.8, color=MUTED)
            tx(fig, cx + .205, cy, "복제 %s · 벤치 %s"
               % (num(c.get("r"), 2), num(c.get("b"), 2)), fontsize=6.8, color=INK2, ha="right")
            cy -= .0118

    qx = X0 + .625
    tx(fig, qx, by, "자료 품질", fontsize=7.2, weight="bold", color=INK2)
    yy = by - .013
    for lab, v in (("이월한 분기", m.get("carried")), ("건너뛴 분기", m.get("skipped")),
                   ("룩어헤드로 버린 셀", m.get("lookahead")), ("정지 개월", m.get("paused_months")),
                   ("집중도 게이트 분기", "%.0f%%" % ((m.get("conc_frac") or 0) * 100))):
        tx(fig, qx, yy, lab, fontsize=6.8, color=MUTED)
        tx(fig, qx + .259, yy, str(v if v is not None else "—"), fontsize=6.8,
           color=INK2, ha="right")
        yy -= .0118


# ── 본체 ────────────────────────────────────────────────────────────────────
def main() -> int:
    D = json.load(io.open(os.path.join(DATA, "guru17.json"), encoding="utf-8"))
    G = json.load(io.open(os.path.join(DATA, "guru.json"), encoding="utf-8"))
    gen = (D.get("generated") or "")[:10] or dt.date.today().isoformat()

    print("월별 계열을 얻기 위해 guru17_backtest.compute() 를 다시 돌린다…")
    rows, series, bench, RF, months = GB.compute()

    # 두 소스가 어긋나면 멈춘다 — 낡은 JSON 위에 새 곡선을 얹지 않는다.
    sp = D.get("span") or {}
    if months and (sp.get("start") != months[0] or sp.get("end") != months[-1]):
        raise SystemExit("guru17.json 구간(%s~%s)과 방금 계산한 구간(%s~%s)이 다르다 — "
                         "build/guru17_backtest.py 를 먼저 다시 돌릴 것."
                         % (sp.get("start"), sp.get("end"), months[0], months[-1]))
    if len(rows) != len(D.get("managers") or []):
        raise SystemExit("운용사 수가 다르다(JSON %d · 재계산 %d) — guru17_backtest.py 를 먼저 돌릴 것."
                         % (len(D.get("managers") or []), len(rows)))
    # 구간·운용사 수가 같아도 계열 자체가 다를 수 있다(가격 패널만 갱신된 경우). 곡선에서 되짚은
    # CAGR 이 표의 CAGR 과 어긋나면, 표와 그림이 서로 다른 것을 말하고 있다는 뜻이다 — 멈춘다.
    for m in (D.get("managers") or []):
        S, mt = series.get(m["cik"]), m.get("metrics")
        if not S or not mt or mt.get("cagr") is None:
            continue
        r = np.asarray(S["r"], float)
        if r.size < 2:
            continue
        c = (float(np.prod(1.0 + r)) ** (12.0 / r.size) - 1.0) * 100.0
        if abs(c - mt["cagr"]) > 0.05:
            raise SystemExit("%s — 곡선 CAGR %.2f%% 과 표 CAGR %.2f%% 이 다르다. "
                             "guru17.json 이 낡았다. build/guru17_backtest.py 를 먼저 돌릴 것."
                             % (m["name"], c, mt["cagr"]))

    # 최신 보유 — guru.json 은 cik 가 int, guru17.json 은 str 이다.
    hold = {}
    for g in (G.get("managers") or []):
        h = dict(g); h["_as_of"] = G.get("as_of") or "—"
        hold[str(g.get("cik"))] = h

    ms = D.get("managers") or []
    live = [m for m in ms if m.get("alpha") is not None]
    dead = [m for m in ms if m.get("alpha") is None]
    order = live + dead                        # 성과를 낸 곳 먼저, 그다음 성과를 못 낸 곳
    n_block_pages = (len(order) + 1) // 2
    total = 2 + n_block_pages

    with PdfPages(OUT) as pdf:
        fig = new_page(); draw_verdict(fig, D, total, gen); pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
        fig = new_page(); draw_ranking(fig, D, total, gen, 2); pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
        page = 3
        for i in range(0, len(order), 2):
            fig = new_page()
            tx(fig, X0, .990, "부록 B — 운용사별 상세  (사후선택된 명단이다. 순위가 추천이 아니다.)",
               fontsize=6.8, color=MUTED)
            tx(fig, X0, .978, "곡선은 그 운용사의 수익률이 아니다 — 13F는 롱온리·분기말 스냅샷이고 "
                              "공매도·채권·현금·비상장이 보이지 않는다. 13F로 보이는 부분을 "
                              "유니버스로 잘라 복제한 것이다.", fontsize=6.6, color=MARG)
            tx(fig, X0, .968, "상황별 칸은 구간을 사후에 쪼갠 서술이지 검정이 아니다.",
               fontsize=6.6, color=MARG)
            for k, m in enumerate(order[i:i + 2]):
                draw_block(fig, BLOCK_TOPS[k], m, series.get(m["cik"]), hold.get(str(m["cik"])))
                if k == 0 and len(order[i:i + 2]) > 1:
                    hline(fig, X0, X1, .526, RULE, .8)
            footer(fig, page, total, gen)
            pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
            page += 1

    print("→ %s (%d쪽 · %dKB · 폰트 %s)"
          % (OUT, total, os.path.getsize(OUT) // 1024, KFONT))
    print("   성과 산출 %d곳 · 성과 미산출 %d곳" % (len(live), len(dead)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
