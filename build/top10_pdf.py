# -*- coding: utf-8 -*-
"""build/top10_pdf.py — 개별종목 **상위 10종목** 전략 총람 → data/top10_strategies.pdf

무엇을. 이 랩의 종목 전략 가운데 **한 번에 10종목만 담는** 규칙 66종을 한 벌로 모은다.
판형·색·표는 build/style_top_pdf.py 를 import 해서 쓴다(스타일 리포트와 같은 판).
자료는 전부 커밋된 산출물에서 온다 — 여기서 백테스트를 다시 돌리지 않는다.
  data/strategy_index.json   지표·기간수익·보유명단·논문
  data/strategy_charts.json  누적 곡선
  data/_monotonicity.json    팩터 단조성(Fan 2026) — 있으면 싣는다

🚨 **세로로 비교하면 안 되는 자리가 있다.**
  · 창은 66종이 모두 같다(2016-08~2026-08 · 랩의 MAX_YEARS=10). 이건 비교해도 된다.
  · 대조군도 S&P 500(PR)로 같다. 이것도 된다.
  · 🚨 그러나 **회전율이 0.5배에서 28배까지 벌어진다.** 비용 20bp 를 물린 뒤의 수는
    metrics_net 에 따로 있고, 회전이 큰 규칙은 그 차이가 크다. 총수익만 보면 안 된다.
  · 🚨 그리고 **10종목은 유니버스 518종의 2%다.** 원 논문이 분위(52~155종)로 말한
    규칙을 10종으로 옮긴 것이 여럿이라, 이 표의 10종판은 «그 논문의 재현»이 아니라
    «그 점수로 가장 집중한 판»이다. 원문 크기 판은 이 문서에 없다(10종이 아니므로).

⚠ 단조성 칸은 **이 문서의 판정이 아니다.** PREREG-2026-09-21-TWOHEADS 가
  「Combined Rank 로 팩터를 고르는 것」을 **측정만**으로 닫았다. 여기 싣는 것은
  «이 10종이 버는 것이 팩터 전체가 듣는 것인가, 꼭짓점만인가» 를 읽는 참고 수치다.

  python build/top10_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "top10_strategies.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST                                       # noqa: E402

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER = ST.POS, ST.NEG, ST.ACC, ST.PAPER
BM1, BM2 = ST.BM1, ST.BM2
TRAILS = ["1W", "1M", "3M", "6M", "12M", "YTD"]
BLOCK_TOPS = (.958, .500)


# 맑은 고딕에 없는 글자 → 눕힌 짝. 그대로 그리면 두부(□)로 나가고 경고는 stderr 한 줄이라
# 로그를 안 보면 모른 채 배포된다(실측: ⟨⟩ 가 규칙 문장에 섞여 있었다).
_SUB = {"−": "-", "⚠": "!", "🚨": "!", "→": "->", "←": "<-", "≤": "<=", "≥": ">=",
        "«": "\"", "»": "\"", "⟨": "<", "⟩": ">", "±": "+/-", "×": "x", "≈": "~",
        "①": "(1)", "②": "(2)", "③": "(3)", "④": "(4)", "⑤": "(5)", "⑥": "(6)",
        "√": "sqrt", "σ": "s", "ρ": "rho", "β": "beta", "α": "alpha", "Δ": "D",
        "…": "...", "—": "-", "–": "-", "“": "\"", "”": "\"", "‘": "'", "’": "'"}


def safe(s):
    """맑은 고딕에 없는 글자를 눕힌다 — 그대로 그리면 두부(□)로 나간다.

    ⚠ 표에 안 적힌 글자가 또 섞일 수 있어 main() 이 **전수로 검사**한다.
      여기 표를 손으로 늘리는 것만으로는 다음번에 또 놓친다.
    """
    if not s:
        return s or ""
    for a, b in _SUB.items():
        s = s.replace(a, b)
    return s


def unmapped(s, font_chars):
    """폰트에 없는데 _SUB 도 못 잡은 글자를 돌려준다."""
    return {c for c in safe(s or "") if ord(c) > 0x7F and c not in font_chars}


def cut(s, n):
    s = safe(s)
    return s if len(s) <= n else s[:n - 1] + "…"


# 리밸 주기 — 원천의 코드로 읽는다(라벨은 «연 1회(6월말)» 처럼 길고 바뀔 수 있다).
#   사용자 요청 2026-09-21: 「전략명 맨뒤에 주간 월간 분기 …」
REB_KO = {"we": "주간", "me": "월간", "qe": "분기", "y6": "연 1회", "h": "반기"}


def reb_of(x):
    """주기 한 낱말. 모르면 빈 문자열 — **지어내지 않는다.**"""
    return REB_KO.get(x.get("reb") or "", "")


def with_reb(x, n=None):
    """이름 + 주기. n 을 주면 이름 쪽만 줄이고 주기는 남긴다(주기가 잘리면 뜻이 없다)."""
    r = reb_of(x)
    nm = safe(x.get("name"))
    if n is not None:
        nm = cut(nm, n - (len(r) + 3 if r else 0))
    return "%s (%s)" % (nm, r) if r else nm


def num(v, d=2, sign=False):
    if v is None:
        return "—"
    return ("%+." + str(d) + "f") % v if sign else ("%." + str(d) + "f") % v


def wrap(s, n):
    """글자 수로 접는다 — 한글은 공백이 드물어 단어 단위로는 안 접힌다."""
    s = safe(s or "")
    out, cur = [], ""
    for ch in s:
        cur += ch
        if len(cur) >= n and ch in " ·,.":
            out.append(cur.strip()); cur = ""
    if cur:
        out.append(cur.strip())
    return out


def load():
    J = lambda n: json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))   # noqa: E731
    idx = J("strategy_index.json")
    ch = (J("strategy_charts.json") or {}).get("charts") or {}
    try:
        mono = {r["sid"]: r for r in (J("_monotonicity.json") or {}).get("rows") or []}
    except Exception:
        mono = {}
    items = [x for x in (idx.get("items") or [])
             if x.get("src") == "종목 전략"
             and (x.get("holdings") or {}).get("kind") == "xsec"
             and ((x.get("holdings") or {}).get("n") == 10
                  or len((x.get("holdings") or {}).get("tickers") or []) == 10)]
    items.sort(key=lambda z: -(z.get("t") if z.get("t") is not None else -99))
    return idx, items, ch, mono


# ── 전략 한 블록(반 쪽) ──────────────────────────────────────────────────
def draw_block(fig, top, x, ch, mono):
    m = x.get("metrics") or {}
    b = x.get("bench") or {}
    mn = x.get("metrics_net") or {}
    tr = x.get("trails") or {}
    tix = x.get("trails_ix") or {}
    h = x.get("holdings") or {}
    pp = (x.get("papers") or [None])[0]
    mo = mono.get(x["sid"])

    y = top
    # ⚠ 제목이 길면 오른쪽 논문 이름과 부딪힌다 — 실측으로 32자에서 멈춘다.
    # ⚠ 제목이 길면 오른쪽 정보줄(ha=right) 아래로 파고든다. 글자수로 먼저 줄이고,
    #   그래도 길면 **크기를 낮춘다** — 자르기만 하면 규칙 이름이 원래 그런 줄 안다.
    _ttl = with_reb(x, 30)
    ST.tx(fig, X0, y, _ttl, fontsize=(14.0 if len(_ttl) <= 22 else
                                      (12.2 if len(_ttl) <= 27 else 10.8)), weight="bold")
    if pp:
        _a = safe(pp.get("a") or "")
        if len(_a) > 20:                      # 저자가 셋 넘으면 첫 이름 + 외
            _a = _a.split("·")[0] + " 외"
        ST.tx(fig, X1, y + .0015, "%s (%s)" % (_a, pp.get("y")),
              fontsize=7.6, color=ACC, ha="right")
    # 주기는 제목에 이미 들어갔다 — 여기서는 «언제» 를 정확히 적는다(월말인지 월중인지).
    ST.tx(fig, X1, y - .0098,
          "%s ~ %s · %s 리밸 · 10종목 동일가중 · 회전 연 %s회 · 비용 %sbp"
          % (x.get("start"), x.get("end"), safe(x.get("reb_label") or "—"),
             num(x.get("turnover"), 1), x.get("cost_bp") or 0),
          fontsize=6.5, color=MUTED, ha="right")
    y -= .0200
    ST.hline(fig, X0, X1, y, RULE, .9)
    y -= .0075
    for ln in wrap(x.get("rule"), 96)[:2]:
        ST.tx(fig, X0, y, ln, fontsize=7.0, color=INK2)
        y -= .0108
    y -= .0075

    LW = .432
    # ① 성과
    ST.tx(fig, X0, y, "성과 (%s)" % safe(x.get("bench_label") or "대조군"),
          fontsize=9.0, weight="bold")
    t_top = y - .0132
    wr = x.get("winrate") or {}
    rows = [
        ["CAGR %", num(m.get("cagr")), num(b.get("cagr")), num(x.get("excess_cagr"), 2, True)],
        ["변동성 %", num(m.get("vol")), num(b.get("vol")), "—"],
        ["샤프", num(m.get("sharpe"), 3), num(b.get("sharpe"), 3), num(x.get("d_sharpe"), 3, True)],
        ["MDD %", num(m.get("mdd")), num(b.get("mdd")), "—"],
        ["t", num(x.get("t")), "—", "—"],
        ["비용 후 CAGR %", num(mn.get("cagr")), "—",
         num((mn.get("cagr") - m["cagr"]) if (mn.get("cagr") is not None
                                             and m.get("cagr") is not None) else None, 2, True)],
        ["이긴 달", "%s/%s" % (int(round((wr.get("win") or 0) * (wr.get("n") or 0) / 100))
                             if wr.get("win") is not None else "—", wr.get("n") or "—"),
         "—", "%s%%" % num(wr.get("win"), 1)],
    ]

    def cc(r, c):
        if c == 0:
            return INK
        if c == 2:
            return MUTED
        v = rows[r][c]
        if c == 3 and v not in ("—",):
            return POS if not v.startswith("-") else NEG
        if c == 1 and r in (0, 2, 4, 5) and v != "—":
            return POS if not v.startswith("-") else NEG
        return INK
    y1 = ST.table(fig, X0, t_top, [.152, .098, .092, .090],
                  ["지표", "전략", "대조군", "차이"], rows, row_h=.0136,
                  cell_color=cc, cell_weight=lambda r, c: "bold" if c == 1 else "normal")

    # ② 기간별 수익률
    y2 = y1 - .0140
    ST.tx(fig, X0, y2, "기간별 수익률 %", fontsize=9.0, weight="bold")
    prow = [["전략"] + [num(tr.get(k), 1) for k in TRAILS],
            ["S&P 500"] + [num((tix.get(k) or {}).get("spx"), 1) for k in TRAILS],
            ["NDX"] + [num((tix.get(k) or {}).get("ndx"), 1) for k in TRAILS],
            ["초과(vs S&P)"] + [num((tr[k] - tix[k]["spx"])
                                   if (tr.get(k) is not None
                                       and (tix.get(k) or {}).get("spx") is not None) else None, 1)
                               for k in TRAILS]]

    def cc2(r, c):
        if c == 0:
            return INK if r in (0, 3) else MUTED
        v = prow[r][c]
        if r in (0, 3) and v != "—":
            return POS if not v.startswith("-") else NEG
        return MUTED
    y3 = ST.table(fig, X0, y2 - .0128, [.122] + [.310 / len(TRAILS)] * len(TRAILS),
                  [""] + TRAILS, prow, row_h=.0136, cell_color=cc2,
                  cell_weight=lambda r, c: "bold" if (r == 0 and c > 0) else "normal")

    # ③ 누적 곡선
    cc_ = ch.get(x["sid"]) or {}
    # 🚨 차트를 왼쪽 표에서 충분히 떼어 놓는다. y축 눈금 글자가 «차이» 칸 위로 올라온다
    #   (실측: .050 간격에서 겹쳤다). 그리고 y라벨은 축 옆이 아니라 **위**에 눕힌다 —
    #   세로로 세우면 그것부터 표를 침범한다.
    cx0 = X0 + LW + .075
    cw = X1 - cx0
    ax = fig.add_axes([cx0, y3, cw, t_top - y3 - .012])
    ax.set_facecolor(PAPER)
    ST.tx(fig, cx0, t_top - .0085, "누적 (시작 = 100 · 로그축)", fontsize=6.4, color=MUTED)
    d, nav, bn = cc_.get("dates") or [], cc_.get("nav") or [], cc_.get("bench") or []
    if nav:
        xi = np.arange(len(nav))
        ax.axhline(100, color=LINE, lw=.6)
        if bn and len(bn) == len(nav):
            ax.plot(xi, bn, color=BM1, lw=1.0, ls="--", label="S&P 500(PR)")
        ax.plot(xi, nav, color=ACC, lw=1.6, label="전략")
        ax.set_yscale("log")
        # ⚠ 로그축 기본 눈금은 «6 x 10^2» 로 찍힌다 — 종이에서 읽히지 않는다. 맨수로 눕힌다.
        from matplotlib.ticker import FuncFormatter, NullFormatter, LogLocator
        ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1., 2., 3., 5.), numticks=8))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: "%g" % v))
        ax.yaxis.set_minor_formatter(NullFormatter())
        tk = list(range(0, len(xi), max(1, len(xi) // 6)))
        ax.set_xticks(tk)
        ax.set_xticklabels([str(d[k])[2:7] for k in tk] if d else [])
        ax.set_xlim(0, len(xi) - 1)
        ax.legend(fontsize=6.2, frameon=False, loc="upper left",
                  handlelength=1.8, borderpad=.1, labelspacing=.25)
    ax.tick_params(labelsize=6.2, colors=MUTED, length=2, pad=1.5)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.grid(True, color=LINE, lw=.4, alpha=.65)
    ax.set_axisbelow(True)

    # ④ 현재 보유 + ⑤ 팩터 단조성
    yp = y3 - .0165
    ST.tx(fig, X0, yp, "지금 담는 10종목", fontsize=9.0, weight="bold")
    # ⚠ .112 에서는 제목 꼬리와 겹쳤다(실측). 제목이 9pt 8글자라 .140 이 필요하다.
    ST.tx(fig, X0 + .140, yp, "기준 %s" % (h.get("as_of") or "—"), fontsize=6.4, color=MUTED)
    tks = h.get("tickers") or []
    ST.tx(fig, X0, yp - .0145, "  ".join(tks[:10]), fontsize=8.2, color=INK, weight="bold")
    nmz = h.get("names") or {}
    ST.tx(fig, X0, yp - .0255,
          cut(" · ".join((nmz.get(t) or t).title() for t in tks[:5]), 78),
          fontsize=6.3, color=MUTED)
    ST.tx(fig, X0, yp - .0345,
          cut(" · ".join((nmz.get(t) or t).title() for t in tks[5:10]), 78),
          fontsize=6.3, color=MUTED)
    if mo:
        ST.tx(fig, cx0, yp, "팩터 단조성 (참고 · 판정 아님)", fontsize=8.2, weight="bold")
        ls_t = mo.get("ls_t")
        ST.tx(fig, cx0, yp - .0145,
              "Q1<=..<=Q5 인 달 %.1f%%  ·  Q5-Q1 %+.1fbp/월  ·  t %s"
              % (mo.get("mono_pct") or 0, mo.get("ls_mean_bp") or 0,
                 "—" if ls_t is None else "%+.2f" % ls_t),
              fontsize=6.8, color=INK2)
        warn = ("!! 팩터는 거꾸로 섰다 - 10종만 번다" if (ls_t or 0) < -1.0 else
                ("팩터 전체가 같은 방향" if (ls_t or 0) > 1.0 else "팩터 자체는 구별 불가"))
        ST.tx(fig, cx0, yp - .0250, warn, fontsize=6.6,
              color=NEG if (ls_t or 0) < -1.0 else (POS if (ls_t or 0) > 1.0 else MUTED))

    # ⑥ 연도별 — 블록 아래 여백을 쓴다. «언제 벌고 언제 잃었나» 가 총수익보다 많이 말한다.
    yr = (cc_.get("yearly") or [])
    if yr:
        yb = yp - .0475
        ST.tx(fig, X0, yb, "연도별 수익률 % (전략 / 대조군)", fontsize=8.2, weight="bold")
        ys = yr[-11:]
        w = (X1 - X0) / max(1, len(ys))
        ax2 = fig.add_axes([X0, yb - .0415, X1 - X0, .0335])
        ax2.set_facecolor(PAPER)
        xs = np.arange(len(ys))
        sv = [(z.get("r") if isinstance(z, dict) else None) for z in ys]
        bv = [(z.get("b") if isinstance(z, dict) else None) for z in ys]
        sv = [0 if v is None else v for v in sv]
        bv = [0 if v is None else v for v in bv]
        ax2.bar(xs - .19, sv, width=.36, color=[POS if v >= 0 else NEG for v in sv])
        ax2.bar(xs + .19, bv, width=.36, color=LINE, edgecolor=RULE, linewidth=.4)
        ax2.axhline(0, color=RULE, lw=.6)
        ax2.set_xticks(xs)
        ax2.set_xticklabels([str((z.get("y") if isinstance(z, dict) else ""))[-4:] for z in ys])
        ax2.tick_params(labelsize=6.0, colors=MUTED, length=0, pad=1.5)
        ax2.set_yticks([])
        for sp in ax2.spines.values():
            sp.set_visible(False)
        for k, v in enumerate(sv):
            ax2.text(k - .19, v + (1.5 if v >= 0 else -1.5), "%.0f" % v, ha="center",
                     va="bottom" if v >= 0 else "top", fontsize=5.4, color=INK2)


def footer(fig, page, total, as_of):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .026,
          "개별종목 상위 10종목 전략 · 유니버스 518종(S&P 500 U NASDAQ 100) · "
          "동일가중 · 대조군 S&P 500(PR) · 창 10년 · 기준 %s" % as_of,
          fontsize=6.4, color=MUTED)
    ST.tx(fig, X0, .0175,
          "!! 10종목은 유니버스의 2%다 - 원 논문이 분위(52~155종)로 말한 규칙을 가장 집중한 판으로 "
          "옮긴 것이 여럿이다. 회전율이 0.5~28배로 벌어지므로 비용 후 수치를 같이 볼 것.",
          fontsize=6.0, color=NEG)
    ST.tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def main() -> int:
    idx, items, ch, mono = load()
    if not items:
        raise SystemExit("10종목 전략을 못 찾았다 — 먼저 build/strategy_index.py")
    as_of = idx.get("as_of") or "—"

    # 🚨 두부(□) 전수 검사 — 그리기 **전에** 잡는다. matplotlib 은 경고 한 줄만 내고
    #   그대로 찍으므로, 로그를 안 보면 네모난 글자가 그대로 배포된다.
    try:
        from matplotlib import font_manager as _fm
        from matplotlib import ft2font as _ft
        _fp = _fm.findfont(_fm.FontProperties(family=ST.plt.rcParams["font.family"]))
        _cs = set(_ft.FT2Font(_fp).get_charmap().keys())
        _have = {chr(c) for c in _cs}
        bad = set()
        for x in items:
            for fld in ("name", "rule", "bench_label", "reb_label"):
                bad |= unmapped(x.get(fld), _have)
            for v in (x.get("holdings") or {}).get("names", {}).values():
                bad |= unmapped(v, _have)
        if bad:
            print("  ⚠ 폰트에 없는 글자 %d개 — _SUB 에 추가할 것: %s"
                  % (len(bad), " ".join(sorted(bad))))
        else:
            print("  ~ 두부 검사 통과(폰트 %s)" % os.path.basename(_fp))
    except Exception as e:
        print("  ⚠ 두부 검사를 못 돌렸다 — %s" % e)

    per = len(BLOCK_TOPS)
    nblk = (len(items) + per - 1) // per
    # 요약 — 66종을 **한 쪽에** 담는다. 나눠 실으면 t 순 비교가 쪽을 넘어가 끊긴다.
    # ⚠ 행높이는 실측으로 맞췄다 — .900 에서 시작해 66행 + 머리글 + 각주 두 줄이
    #   각주선(.034) 위에 들어와야 한다.
    CAP = 70
    nsum = (len(items) + CAP - 1) // CAP
    total = nsum + nblk
    print("10종목 전략 %d종 · 요약 %d쪽 + 본문 %d쪽 = %d쪽" % (len(items), nsum, nblk, total))

    with PdfPages(OUT) as pdf:
        # ── 요약 ────────────────────────────────────────────────────────
        for s in range(nsum):
            fig = ST.new_page()
            y = .958
            if s == 0:
                ST.tx(fig, X0, y, "개별종목 상위 10종목 전략", fontsize=23, weight="bold")
                ST.tx(fig, X0, y - .034,
                      "한 번에 10종목만 담는 규칙 전부 - 이긴 것도 진 것도 같이 싣는다",
                      fontsize=10, color=ACC)
                ST.tx(fig, X1, y - .030, "%d종 · 기준 %s" % (len(items), as_of),
                      fontsize=8.5, color=MUTED, ha="right")
                ST.hline(fig, X0, X1, y - .046, RULE, .9)
                y -= .058
            else:
                ST.tx(fig, X0, y, "개별종목 상위 10종목 전략 (이어서)", fontsize=13, weight="bold")
                y -= .026
            part = items[s * CAP:(s + 1) * CAP]
            rows = []
            for x in part:
                m = x.get("metrics") or {}
                mo = mono.get(x["sid"]) or {}
                rows.append([with_reb(x, 36),
                             num(x.get("excess_cagr"), 1, True), num(x.get("t")),
                             num(m.get("sharpe"), 3), num(x.get("turnover"), 1),
                             num(mo.get("mono_pct"), 1) if mo else "—",
                             num(mo.get("ls_t")) if mo else "—"])

            def cs(r, c, rows=rows):
                if c == 0:
                    return INK
                v = rows[r][c]
                if c in (1, 2, 6) and v != "—":
                    return POS if not v.startswith("-") else NEG
                return INK if c == 3 else MUTED
            y = ST.table(fig, X0, y, [.372, .078, .068, .078, .068, .078, .072],
                         ["전략", "초과%p", "t", "샤프", "회전", "단조%", "팩터t"],
                         rows, row_h=.0119, fs=6.5, hfs=6.1, zebra=True,
                         aligns=["l"] + ["r"] * 6, cell_color=cs)
            if s == nsum - 1:
                ST.tx(fig, X0, y - .012,
                      "단조% = 매월 5분위가 Q1<=..<=Q5 로 선 달의 비율(무작위면 0.83%). "
                      "팩터t = Q5-Q1 의 t. 둘 다 PREREG-2026-09-21-TWOHEADS 의 측정이고 "
                      "판정이 아니다 - 그 등록은 '측정만'으로 닫혔다.",
                      fontsize=6.4, color=MUTED)
                ST.tx(fig, X0, y - .026,
                      "!! 초과%p·샤프는 총수익 기준이다. 회전이 큰 규칙은 비용 후가 크게 다르다 "
                      "- 전략마다의 비용 후 수치는 본문 쪽에 있다.",
                      fontsize=6.4, color=NEG)
            footer(fig, s + 1, total, as_of)
            pdf.savefig(fig)
            if "--png" in sys.argv and s == 0:
                fig.savefig(os.path.join(DATA, "_top10_summary.png"), dpi=110,
                            facecolor=PAPER)
            ST.plt.close(fig)

        # ── 본문 ────────────────────────────────────────────────────────
        for bi in range(nblk):
            fig = ST.new_page()
            for k, top in enumerate(BLOCK_TOPS):
                j = bi * per + k
                if j >= len(items):
                    break
                draw_block(fig, top, items[j], ch, mono)
                if k == 0 and j + 1 < len(items):
                    ST.hline(fig, X0, X1, .524, LINE, .6)
            footer(fig, nsum + bi + 1, total, as_of)
            pdf.savefig(fig)
            # ⚠ 눈으로 확인할 쪽만 PNG 로도 남긴다 — 넘침·겹침은 수로 못 잡고 봐야 잡힌다.
            #   (스타일 리포트가 각주 길이를 «그려서 재고» 줄인 것과 같은 취지다.)
            if "--png" in sys.argv and bi == 0:
                fig.savefig(os.path.join(DATA, "_top10_body.png"), dpi=110,
                            facecolor=PAPER)
            ST.plt.close(fig)

    print("→ %s (%.1fMB)" % (OUT, os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
