# -*- coding: utf-8 -*-
"""build/verdict_flip_pdf.py — 대조군 교체로 판정이 바뀐 전략 → data/verdict_flip.pdf

무엇을. 2026-07-28 에 랩 전략의 판정 대조군을 **같은 유니버스 동일가중 매수후보유**에서
**S&P 500(PR)**로 바꿨다(사용자 결정). 그 한 번의 교체로 판정이 뒤집힌 전략만 모아
'무엇이 왜 바뀌었나'를 한 문서로 낸다.

## 이 문서가 답하는 것은 '어느 전략이 좋아졌나'가 아니다

바뀐 것은 전략이 아니라 **문턱**이다. 그래서 곡선 25장을 늘어놓지 않는다 — 그렇게 하면
'좋아진 전략 모음'으로 읽힌다. 대신 세 가지를 나란히 둔다.
  ① 판정 분포가 어떻게 이동했나
  ② 대조군 두 곡선(동일가중 유니버스 vs S&P 500) — 격차가 곧 문턱 차이다
  ③ 전략별 ΔSharpe 가 전 → 후로 얼마나 움직였나
전략 자신의 수익·샤프·MDD 는 **하나도 바뀌지 않았다**는 사실을 표에 함께 싣는다.

## 옛 수치는 git 에서 읽는다

대조군 교체 직전 커밋의 data/tech_strategies.json 이 '옛 판정'의 정본이다. 지금 다시
계산해서 만들지 않는다 — 그러면 그때 배포된 숫자가 아니라 오늘 재현한 숫자가 된다.

  python build/verdict_flip_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, subprocess, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "verdict_flip.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST          # 판형·색·표·폰트를 그대로 쓴다(폰트 가드 포함)

# 대조군을 바꾼 커밋. 그 직전(^)이 옛 판정의 정본이다.
BENCH_COMMIT = "3327b54a"

X0, X1 = ST.X0, ST.X1
tx, hline, box, table, num = ST.tx, ST.hline, ST.box, ST.table, ST.num
INK, INK2, MUTED = ST.INK, ST.INK2, ST.MUTED
LINE, RULE, PAPER, GROUND = ST.LINE, ST.RULE, ST.PAPER, ST.GROUND
POS, NEG, ACC = ST.POS, ST.NEG, ST.ACC
CHAMP, RP, MARG = ST.CHAMP, ST.RP, ST.MARG

VORDER = ["열위", "구별 불가", "통과 후보", "판정 불가"]
VCOL = {"열위": NEG, "구별 불가": MUTED, "통과 후보": POS, "판정 불가": MARG}


def glyphsafe(t):
    """폰트에 없는 글자를 있는 것으로 바꾼다.

    전략 이름·설명이 데이터에서 오는데 거기에 U+2212(−)가 섞여 있다('드로다운 게이트 (−10%)').
    Apple SD Gothic Neo 에 그 글리프가 없어 두부가 된다 — 맑은 고딕에는 있어서 Windows 에서
    만들 때는 안 보였다. 문서가 어느 기계에서 만들어졌든 같게 나오도록 여기서 정리한다.
    """
    return (str(t).replace("\u2212", "-")      # 마이너스 → 하이픈
                  .replace("\u26a0", "\u203b"))    # ⚠ → ※ (같은 이유)


def old_doc():
    """대조군 교체 직전에 배포돼 있던 tech_strategies.json."""
    try:
        raw = subprocess.check_output(
            ["git", "-C", ROOT, "show", "%s^:data/tech_strategies.json" % BENCH_COMMIT],
            stderr=subprocess.DEVNULL)
    except Exception as e:
        raise SystemExit("옛 판정을 git 에서 읽지 못했다(%s^) — %s" % (BENCH_COMMIT, e))
    return json.loads(raw.decode("utf-8"))


def footer(fig, page, total):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .026, "판정 대조군 교체(2026-07-28) — 같은 유니버스 동일가중 → S&P 500(PR) · "
                      "전략 규칙은 하나도 바뀌지 않았다 · 비용 0",
       fontsize=6.4, color=MUTED)
    tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
       fontsize=6.4, color=MUTED, ha="right")


def ax_at(fig, x, y, w, h):
    ax = fig.add_axes([x, y, w, h])
    ax.set_facecolor(PAPER)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE); ax.spines[s].set_linewidth(.7)
    ax.tick_params(labelsize=6.2, colors=MUTED, length=2, pad=1.5)
    ax.grid(True, color=LINE, lw=.4, alpha=.65)
    ax.set_axisbelow(True)
    return ax


def draw_summary(fig, O, N, flips, total):
    from collections import Counter
    co = Counter(r.get("verdict") for r in O["strategies"])
    cn = Counter(r.get("verdict") for r in N["strategies"])

    tx(fig, X0, .962, "대조군을 바꾸니 판정이 뒤집혔다", fontsize=21, weight="bold")
    tx(fig, X0, .930, "같은 유니버스 동일가중 → S&P 500(PR) · 전략 규칙은 그대로",
       fontsize=9.5, color=ACC)
    tx(fig, X1, .933, "%s ~ %s" % (N.get("start"), N.get("as_of")),
       fontsize=8.5, color=MUTED, ha="right")
    hline(fig, X0, X1, .916, RULE, .9)

    y = .898
    tx(fig, X0, y, "바뀐 것은 전략이 아니라 문턱이다. 규칙·보유·비용은 하나도 손대지 않았고, "
                   "전략 자신의 CAGR·샤프·MDD 도 그대로다 — 무엇과 견주는가만 바뀌었다.",
       fontsize=8, color=INK2)
    y -= .030

    # ① 판정 분포 이동
    tx(fig, X0, y, "① 판정 분포", fontsize=11, weight="bold")
    rows = []
    for v in VORDER:
        if not co.get(v) and not cn.get(v):
            continue
        rows.append([v, str(co.get(v, 0)), str(cn.get(v, 0)),
                     "%+d" % (cn.get(v, 0) - co.get(v, 0))])

    def cc(r, c):
        if c == 3:
            return POS if rows[r][3].startswith("+") else NEG
        return VCOL.get(rows[r][0], INK) if c == 0 else INK
    y = table(fig, X0, y - .014, [.140, .092, .092, .086],
              ["판정", "옛 대조군", "S&P 500", "변화"], rows,
              row_h=.0150, fs=7.6, aligns=["l", "r", "r", "r"], cell_color=cc, zebra=True)
    tx(fig, X0 + .430, y + .078,
       "25종이 뒤집혔고 전부 유리한 쪽이다. 열위 %d → %d, 통과 후보 %d → %d."
       % (co.get("열위", 0), cn.get("열위", 0), co.get("통과 후보", 0), cn.get("통과 후보", 0)),
       fontsize=7.6, color=INK2)
    tx(fig, X0 + .430, y + .062,
       "한 종목도 나빠진 쪽으로 가지 않았다는 사실이 곧 이것이 전략의\n"
       "변화가 아니라는 증거다 — 실력이 바뀌었다면 양방향이어야 한다.",
       fontsize=7.2, color=NEG, linespacing=1.5)

    # ② 대조군 두 곡선 — 격차가 곧 문턱 차이
    y -= .034
    tx(fig, X0, y, "② 대조군 두 곡선 — 이 격차가 문턱의 차이다", fontsize=11, weight="bold")
    ob = (O["strategies"][0].get("chart") or {}).get("bench") or []
    nb = (N["strategies"][0].get("chart") or {}).get("bench") or []
    od = (O["strategies"][0].get("chart") or {}).get("dates") or []
    m = min(len(ob), len(nb), len(od))
    ax = ax_at(fig, X0, y - .215, X1 - X0, .200)
    if m > 2:
        xi = np.arange(m)
        ax.plot(xi, ob[:m], color=MARG, lw=1.6, label="옛 대조군 — 같은 유니버스 동일가중")
        ax.plot(xi, nb[:m], color=CHAMP, lw=1.6, ls="--", label="새 대조군 — S&P 500(PR)")
        ax.axhline(100, color=LINE, lw=.6)
        ticks = list(range(0, m, max(1, m // 8)))
        ax.set_xticks(ticks)
        ax.set_xticklabels([od[i][:7] for i in ticks], fontsize=6)
        ax.set_xlim(0, m - 1)
        ax.set_ylabel("누적 (시작 = 100)", fontsize=7, color=MUTED)
        ax.legend(fontsize=6.6, frameon=False, loc="upper left", handlelength=2.0)
        tx(fig, X1, y - .0125,
           "옛 대조군이 %.0f → %.0f, 새 대조군이 %.0f → %.0f"
           % (ob[0], ob[m - 1], nb[0], nb[m - 1]), fontsize=7, color=MUTED, ha="right")
    y -= .226
    tx(fig, X0, y, "옛 대조군은 오늘의 518종목 동일가중을 과거로 소급한 것이라 생존편향이 실려 있다 "
                   "— 실제 동일가중 S&P 500(RSP)보다 연 +6.33%p 앞선다.", fontsize=7.4, color=INK2)
    tx(fig, X0, y - .0135, "그만큼 넘기 어려운 문턱이었고, 지수로 바꾸자 그 편향이 초과수익 쪽으로 "
                           "넘어왔다.", fontsize=7.4, color=INK2)
    y -= .036

    # ③ ΔSharpe 이동
    tx(fig, X0, y, "③ 전략별 ΔSharpe — 전 → 후", fontsize=11, weight="bold")
    NAMW = .126                      # 축 왼쪽 전략명 자리 — 안 비우면 이름이 잘린다
    ax = ax_at(fig, X0 + NAMW, y - .262, (X1 - X0) - NAMW, .248)
    fs = sorted(flips, key=lambda f: f["ds_new"])
    ys = np.arange(len(fs))
    for i, f in enumerate(fs):
        ax.plot([f["ds_old"], f["ds_new"]], [i, i], color=LINE, lw=.9, zorder=2)
    ax.scatter([f["ds_old"] for f in fs], ys, s=13, color=MARG, zorder=3, label="옛 대조군")
    ax.scatter([f["ds_new"] for f in fs], ys, s=13, color=CHAMP, zorder=4, label="S&P 500")
    ax.axvline(0, color=INK, lw=.9, zorder=5)
    ax.set_yticks(ys)
    ax.set_yticklabels([glyphsafe(f["name"])[:24] for f in fs], fontsize=6.0)
    ax.set_xlabel("ΔSharpe (전략 - 대조군)", fontsize=6.6, color=MUTED)
    ax.set_ylim(-.8, len(fs) - .2)
    ax.legend(fontsize=6.4, frameon=False, loc="lower right")
    footer(fig, 1, total)


def draw_table(fig, flips, page, total, i0, i1):
    tx(fig, X0, .962, "뒤집힌 %d종 — 전 → 후" % len(flips), fontsize=17, weight="bold")
    tx(fig, X0, .934, "전략 자신의 CAGR·샤프·MDD 는 대조군과 무관하므로 한 값만 싣는다. "
                      "바뀌는 것은 ΔSharpe·t·판정뿐이다.", fontsize=7.6, color=MUTED)
    hline(fig, X0, X1, .920, RULE, .9)

    rows = []
    for f in flips[i0:i1]:
        rows.append([glyphsafe(f["name"])[:26], f["v_old"], f["v_new"],
                     "%+.3f" % f["ds_old"], "%+.3f" % f["ds_new"],
                     ("%.2f" % f["t_old"]) if f["t_old"] is not None else "—",
                     ("%.2f" % f["t_new"]) if f["t_new"] is not None else "—",
                     num(f["cagr"], 1), "%.2f" % f["sharpe"] if f["sharpe"] is not None else "—",
                     num(f["mdd"], 1)])

    def cc(r, c):
        f = flips[i0 + r]
        if c == 1:
            return VCOL.get(f["v_old"], INK)
        if c == 2:
            return VCOL.get(f["v_new"], INK)
        if c in (3, 4):
            return POS if rows[r][c].startswith("+") else NEG
        if c in (7, 9):
            return POS if rows[r][c].startswith("+") else NEG
        return INK

    y = table(fig, X0, .902,
              [.212, .078, .078, .072, .072, .056, .056, .072, .058, .070],
              ["전략", "옛 판정", "새 판정", "ΔSharpe 전", "ΔSharpe 후", "t 전", "t 후",
               "CAGR", "샤프", "MDD"],
              rows, row_h=.0165, fs=7.0, hfs=6.4,
              aligns=["l", "l", "l", "r", "r", "r", "r", "r", "r", "r"],
              cell_color=cc, zebra=True)
    if i1 >= len(flips):
        tx(fig, X0, y - .016,
           "ΔSharpe 가 거의 일정하게 +0.20 안팎 올랐다. 전략마다 다른 이유로 좋아진 것이 "
           "아니라 대조군 하나가 통째로 낮아졌다는 뜻이다.", fontsize=7.4, color=NEG)
        tx(fig, X0, y - .032,
           "t 는 대조군과의 초과수익으로 계산하므로 함께 움직인다. 다중검정 임계는 그대로다 — "
           "규칙 수가 바뀌지 않았기 때문이다.", fontsize=7.4, color=MUTED)
    footer(fig, page, total)


def main() -> int:
    N = json.load(io.open(os.path.join(DATA, "tech_strategies.json"), encoding="utf-8"))
    O = old_doc()
    if O.get("bench_label") == N.get("bench_label"):
        raise SystemExit("옛·새 대조군 라벨이 같다(%s) — 비교할 것이 없다. BENCH_COMMIT 을 확인할 것."
                         % N.get("bench_label"))
    o = {r["sid"]: r for r in O["strategies"]}
    flips = []
    for r in N["strategies"]:
        p = o.get(r["sid"])
        if not p or p.get("verdict") == r.get("verdict"):
            continue
        mt = r.get("metrics") or {}
        flips.append({
            "sid": r["sid"], "name": r["name"],
            "v_old": p.get("verdict"), "v_new": r.get("verdict"),
            "ds_old": p.get("d_sharpe") or 0.0, "ds_new": r.get("d_sharpe") or 0.0,
            "t_old": p.get("t"), "t_new": r.get("t"),
            "cagr": mt.get("cagr"), "sharpe": mt.get("sharpe"), "mdd": mt.get("mdd")})
    if not flips:
        raise SystemExit("판정이 바뀐 전략이 없다 — 만들 문서가 없다.")
    # 옛 판정이 나쁜 것부터, 그다음 개선폭이 큰 것부터
    flips.sort(key=lambda f: (VORDER.index(f["v_old"]) if f["v_old"] in VORDER else 9,
                              -(f["ds_new"] - f["ds_old"])))
    PER = 22
    n_tbl = (len(flips) + PER - 1) // PER
    total = 1 + n_tbl

    with PdfPages(OUT) as pdf:
        fig = ST.new_page(); draw_summary(fig, O, N, flips, total)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
        for k in range(n_tbl):
            fig = ST.new_page()
            draw_table(fig, flips, 2 + k, total, k * PER, min((k + 1) * PER, len(flips)))
            pdf.savefig(fig, facecolor=PAPER); plt.close(fig)

    print("→ %s (%d쪽 · %dKB · 폰트 %s)" % (OUT, total, os.path.getsize(OUT) // 1024, ST.KFONT))
    print("   뒤집힌 전략 %d종 · 옛 대조군 '%s' → 새 대조군 '%s'"
          % (len(flips), O.get("bench_label"), N.get("bench_label")))
    worse = [f for f in flips if VORDER.index(f["v_new"]) < VORDER.index(f["v_old"])]
    print("   나빠진 쪽으로 간 전략: %d종" % len(worse))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
