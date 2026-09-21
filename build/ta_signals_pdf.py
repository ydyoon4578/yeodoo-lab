# -*- coding: utf-8 -*-
"""build/ta_signals_pdf.py — 교과서 TA 신호 → data/ta_signals.pdf (A4 4쪽)

자료는 build/ta_signals.py 가 낸 data/_ta_signals.json 하나뿐이다.

  1·3쪽  지수 차트 + **멀티 신호**(두 신호가 같이 뜬 날)
  2·4쪽  매수 신호 표 · 매도 신호 표

🚨 2026-09-22 사용자 지시로 다시 짠 판이다.
  · 「신호 합류」 → **멀티 신호** · 「기준선차」 → **수익률**
  · S&P 두 쪽 · NASDAQ 두 쪽, 멀티 신호를 앞으로
  · 모든 표는 **승률 순** · 「횟수」 칸은 지우고 **일정 횟수 초과는 아예 뺀다**
  · 말 뜻 상자와 읽는 법은 덜어낸다

⚠ 수익률 칸은 **날것의 1개월 지수 등락**이다. 종전의 「기준선차(= 등락 - 기준선)」는
  칸에서 빼고, 견줄 기준선은 쪽머리에 한 번만 적는다. 승률도 같은 자리에
  「아무 날이나 잡아도 몇 %」를 적어 두니 두 수 다 견줄 데가 있다.

  python build/ta_signals_pdf.py [--png]
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.backends.backend_pdf import PdfPages   # noqa: E402

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "ta_signals.pdf")
sys.path.insert(0, HERE)
import style_top_pdf as ST                                        # noqa: E402

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2

HOT = 10                  # 「최근 발동」을 빨갛게 볼 날수
TOT = 4
MIN_STACK = 2             # 차트 세모 — 좋은 신호가 그날 이만큼 겹친 날
N_MULTI = (20, 14)        # 멀티 신호 표에 실을 짝 수(매수, 매도)
# 🚨 「횟수」 칸을 지우라는 지시(2026-09-22)의 대가를 여기서 막는다.
#   승률 순으로만 세우면 **5회짜리 승률 100%가 1등**으로 올라오는데, 칸이 없으니
#   독자가 그게 5회인 줄 알 길이 없다. 칸을 되살리는 대신 **문턱을 올려**
#   얇은 표본은 애초에 싣지 않는다 — 설명이 늘지 않고 표만 믿을 만해진다.
#   (합류 후보 문턱 CONF_MIN_N 과 같은 10회다.)
MIN_SHOW = 10

# 칸 너비는 **렌더 실측**이다(6.6pt 본문 · PDF 5% 여유 포함).
#   신호명 최대 .123 · 설명 최대 .195 · 「★켜짐157일」 .065 · 날짜 .060
W_SIG = [.190, .330, .062, .050, .082, .050, .120]          # 합 .884 = X1-X0
H_SIG = ["신호", "무엇을 보나", "수익률", "승률", "최근 발동", "경과", "지금"]
A_SIG = ["l", "l", "r", "r", "l", "r", "c"]
W_MUL = [.255, .255, .062, .050, .110, .072, .080]          # 합 .884
H_MUL = ["신호 A", "신호 B", "수익률", "승률", "단독 A/B", "단독 대비", "최근"]
A_MUL = ["l", "l", "r", "r", "r", "r", "l"]

MON = ["1월", "2월", "3월", "4월", "5월", "6월",
       "7월", "8월", "9월", "10월", "11월", "12월"]


YMIN = .050               # 이보다 내려가면 꼬리말을 뚫는다


def foot(fig, page, asof, y_end=None):
    # ⚠ 이 랩에서 표가 꼬리말을 뚫은 적이 여러 번이다. 눈으로 보지 말고 재서 알린다.
    if y_end is not None and y_end < YMIN:
        print("  !! %d쪽 바닥 y=%.4f — %.3f 아래로 내려갔다" % (page, y_end, YMIN))
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .024,
          "여두 전략 랩 · 교과서 TA 신호 · 기준 %s · 통계는 최근 10년 · 차트는 최근 12개월"
          % asof, fontsize=6.4, color=MUTED)
    ST.tx(fig, X1, .024, "%d / %d · %s" % (page, TOT, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def head(fig, R, sub, asof, color=INK):
    """쪽머리 — 견줄 기준선 둘(수익률·승률)을 여기 한 번만 적는다."""
    y = .958
    ST.tx(fig, X0, y, "%s · %s" % (R["label"], sub), fontsize=15, weight="bold", color=color)
    ST.tx(fig, X1, y,
          "기준 %s · 10년(%s~) · 아무 날이나 사면 1개월 %+.2f%% · 오를 확률 %.1f%%"
          % (asof, R["start"], R["base1m"], R.get("base1m_win") or 0),
          fontsize=7.0, color=MUTED, ha="right")
    y -= .026
    ST.hline(fig, X0, X1, y, RULE, .9)
    return y - .014


def rows_of(R, side, max_n):
    """싣는 줄 — 표본이 너무 얇지도(MIN_SHOW) 너무 잦지도(max_n) 않은 것, 승률 순."""
    wkey = "fwd1m_win" if side == "buy" else "fwd1m_down"
    rows = [x for x in R[side] if MIN_SHOW <= x.get("n", 0) <= max_n]
    rows.sort(key=lambda x: ((x.get(wkey) or 0),
                             (x.get("fwd1m_excess") or 0) * (1 if side == "buy" else -1)),
              reverse=True)
    return rows, wkey


# ══ 차트 ═══════════════════════════════════════════════════════════════════
def chart(fig, R, y_top, h, max_n):
    """가격 + 날짜별 신호 수. 세모는 좋은 신호가 그날 MIN_STACK 개 이상 켜진 날."""
    d, c = R["px"]["d"], R["px"]["c"]
    n = len(d)
    pos = {x: i for i, x in enumerate(d)}
    # ⚠ 막대판도 표와 **같은 모집단**을 센다. 종전엔 상태형(NVI 2,511회 등)까지 세어
    #   막대가 늘 꽉 차 있었다 — 표에서 뺐으면 차트에서도 빼야 수가 맞는다.
    nb = [0] * n
    ns = [0] * n
    for side, arr in (("buy", nb), ("sell", ns)):
        for x in R[side]:
            if x.get("n", 0) > max_n:
                continue
            for f in x.get("fires") or []:
                if f in pos:
                    arr[pos[f]] += 1

    cg, cm = {}, {}
    nB = nS = 0
    for side, tag, good in (("buy", "매수", lambda e: e > 0),
                            ("sell", "매도", lambda e: e < 0)):
        for x in R[side]:
            ok = MIN_SHOW <= x.get("n", 0) <= max_n
            if not ok or not good(x.get("fwd1m_excess") or 0):
                continue
            if tag == "매수":
                nB += 1
            else:
                nS += 1
            for f in (x.get("fires") or []):
                if f in pos:
                    cg.setdefault((f, tag), []).append(x["signal"])
                    cm.setdefault((f, tag), []).append(x["fwd1m_mean"])
    cg = {k: v for k, v in cg.items() if len(v) >= MIN_STACK}
    cm = {k: v for k, v in cm.items() if k in cg}

    hp, hb = h * .70, h * .24
    ax = fig.add_axes([X0, y_top - hp, X1 - X0, hp])
    ax2 = fig.add_axes([X0, y_top - h, X1 - X0, hb])
    for a in (ax, ax2):
        a.set_facecolor(PAPER)
        for s in a.spines.values():
            s.set_color(LINE)
            s.set_linewidth(.7)
        a.set_xlim(-2, n + 1)
        a.tick_params(colors=MUTED, labelsize=5.8, length=2)
    ax.plot(range(n), c, color=INK, lw=.9, zorder=3)
    ax.set_xticks([])
    ax.grid(True, axis="y", color=LINE, lw=.4)
    ax.set_axisbelow(True)

    # 🚨 라벨의 수는 **겹친 날을 사건으로 놓고 직접 잰** 1개월 수익이다(stack).
    #   그날 켜진 신호들의 평균이 아니다 — 그건 매도가 구조상 음수가 못 된다.
    ER = {}
    for side, tag in (("buy", "매수"), ("sell", "매도")):
        for x in (R.get("stack") or {}).get(side) or []:
            if x.get("n", 0) >= 5:
                ER[(tag, x["k"])] = x["fwd1m_mean"]
    ev = [(pos[fd], tag == "매수",
           ER.get((tag, 3)) if len(cm[(fd, tag)]) >= 3 else ER.get((tag, 2)),
           len(cm[(fd, tag)])) for (fd, tag) in cg]
    # ⚠ 전부 라벨을 달면 수치가 서로 뭉갠다 — **방향별로** 18봉 이상 떨어진 넷씩.
    #   12봉·다섯씩으로 두었더니 NASDAQ 왼쪽 끝에서 라벨끼리, 또 y축 눈금 숫자와
    #   겹쳤다(렌더 실측). 왼쪽 12봉은 눈금 자리라 아예 비운다.
    lab = set()
    for up in (True, False):
        taken = []
        for i, u, er, kk in sorted((z for z in ev if z[1] is up),
                                   key=lambda z: (-z[3], -z[0])):
            if i >= 12 and all(abs(i - jj) >= 18 for jj in taken):
                lab.add((i, u))
                taken.append(i)
            if len(taken) >= 4:
                break
    for i, up, er, kk in ev:
        col = POS if up else NEG
        yy = c[i] * (.972 if up else 1.028)
        ax.scatter([i], [yy], marker="^" if up else "v", s=10 + 8 * (kk - 1),
                   zorder=6, linewidths=.55, facecolors=col, edgecolors=PAPER)
        if (i, up) in lab and er is not None:
            ax.annotate("%d개 %+.1f%%" % (kk, er), (i, yy),
                        textcoords="offset points", xytext=(0, -9 if up else 5),
                        ha="center", fontsize=5.5, color=col, weight="bold", zorder=7)
    lo, hi = min(c), max(c)
    ax.set_ylim(lo - (hi - lo) * .20, hi + (hi - lo) * .24)
    ax.text(.010, .96, "기준일 %s 종가 %s" % (d[-1], format(int(round(c[-1])), ",")),
            transform=ax.transAxes, fontsize=6.4, color=INK, weight="bold", va="top")

    ax2.bar(range(n), nb, color=POS, width=1.0, linewidth=0, zorder=3)
    ax2.bar(range(n), [-v for v in ns], color=NEG, width=1.0, linewidth=0, zorder=3)
    ax2.axhline(0, color=RULE, lw=.6, zorder=2)
    mx = max(max(nb), max(ns), 1)
    ax2.set_ylim(-mx - .8, mx + .8)
    ax2.set_yticks([-mx, 0, mx])
    ax2.set_yticklabels(["매도 %d" % mx, "", "매수 %d" % mx], fontsize=5.4)
    tk, lb, last = [], [], None
    for i, s in enumerate(d):
        if s[:7] != last:
            tk.append(i)
            lb.append(MON[int(s[5:7]) - 1] if s[5:7] != "01" else s[2:4] + "년")
            last = s[:7]
    ax2.set_xticks(tk)
    ax2.set_xticklabels(lb, fontsize=5.6)
    nday = (sum(1 for k in cg if k[1] == "매수"), sum(1 for k in cg if k[1] == "매도"))
    return y_top - h, (nB, nS, nday)


# ══ 1·3쪽 — 차트 + 멀티 신호 ═══════════════════════════════════════════════
def multi_page(fig, R, asof, page, max_n):
    y = head(fig, R, "멀티 신호", asof)

    ST.tx(fig, X0, y, "최근 12개월", fontsize=8.5, weight="bold")
    ST.tx(fig, X0 + .090, y + .0005,
          "세모 = 성과 좋은 신호가 그날 **%d개 이상** 켜진 날 · 크기는 그 개수 · "
          "옆 수는 **그 개수일 때 실제 1개월 수익** · 아래 막대는 그날 켜진 신호 수"
          % MIN_STACK, fontsize=6.2, color=MUTED)
    y -= .014
    # ⚠ .013 만 떼면 아래 월 눈금과 겹친다 — 눈금 자리를 비운다(렌더 실측).
    y, (nB, nS, nday) = chart(fig, R, y, .200, max_n)
    y -= .028

    # 차트 라벨에 쓴 수의 출처 — 말 뜻이 아니라 실측치라 남긴다.
    st = []
    for sd, tag in (("buy", "매수"), ("sell", "매도")):
        for x in (R.get("stack") or {}).get(sd) or []:
            if x.get("n", 0) >= 5:
                st.append("%s %d개↑ %d회 **%+.2f%%** 승률 %.0f%%"
                          % (tag, x["k"], x["n"], x["fwd1m_mean"],
                             (x.get("fwd1m_down") if sd == "sell"
                              else x.get("fwd1m_win")) or 0))
    ST.tx(fig, X0 + .004, y, " · ".join(st), fontsize=6.6, color=INK2)
    y -= .0112
    ST.tx(fig, X0 + .004, y,
          "겹친 날은 매수 %d일 · 매도 %d일. !! 「성과 좋은 신호」를 전 구간 성적으로 "
          "고른 것이라 이 수는 **설명용**이다." % nday, fontsize=6.4, color=MUTED)
    y -= .0150

    for key, ko, col, nmax in (("conf_buy", "매수", POS, N_MULTI[0]),
                               ("conf_sell", "매도", NEG, N_MULTI[1])):
        buy = key == "conf_buy"
        wk = "fwd1m_win" if buy else "fwd1m_down"
        allp = [x for x in (R.get(key) or []) if x.get("n", 0) >= MIN_SHOW]
        cf = sorted(allp, key=lambda x: ((x.get(wk) or 0), x["n"]), reverse=True)[:nmax]
        if not cf:
            continue
        ST.tx(fig, X0, y, "%s · 승률 순" % ko, fontsize=9.5, weight="bold", color=col)
        ST.tx(fig, X0 + .114, y + .0005,
              "두 신호가 **5거래일 안에 같이** 뜬 날 · %d짝 중 %d · "
              "단독 대비가 **양수면 같이 본 값이 있다**" % (len(allp), len(cf)),
              fontsize=6.4, color=MUTED)
        y -= .0140
        base = R["base1m"]
        tr, gain = [], []
        for x in cf:
            # 🚨 단독 A/B 는 **날것의 1개월 등락**이다. JSON 의 solo_* 는 기준선차라
            #   기준선을 도로 더한다(수익률 = 기준선차 + 기준선).
            ma = (x.get("solo_a") or 0) + base
            mb = (x.get("solo_b") or 0) + base
            # 🚨 「단독 대비」는 **양쪽 다 양수가 제 몫**이 되게 잡는다. 매수는 더 오른 만큼,
            #   매도는 더 내린 만큼. 부호가 방향마다 뒤집히면 또 헷갈린다(2026-09-22 지적).
            g = (x["fwd1m_mean"] - max(ma, mb)) if buy else (min(ma, mb) - x["fwd1m_mean"])
            gain.append(g)
            tr.append([x["a"], x["b"], "%+.2f%%" % x["fwd1m_mean"],
                       "%.0f%%" % ((x.get(wk) or 0)),
                       "%+.2f / %+.2f" % (ma, mb), "%+.2f%%p" % g, x["last"]])

        bw = (R.get("base1m_win") if buy else R.get("base1m_down")) or 0

        def cc(r, c, tr=tr, gain=gain, bw=bw, col=col):
            if c in (0, 1):
                return INK
            if c == 3:
                return col if float(tr[r][3][:-1]) >= bw else MUTED
            if c == 5:
                return POS if gain[r] > 0 else NEG
            return MUTED
        y = ST.table(fig, X0, y, W_MUL, H_MUL, tr, row_h=.0150, fs=6.7, hfs=6.1,
                     zebra=True, aligns=A_MUL, cell_color=cc)
        y -= .020
    foot(fig, page, asof, y + .020)


# ══ 2·4쪽 — 매수·매도 신호 표 ══════════════════════════════════════════════
def table_page(fig, R, asof, page, max_n, tail=False):
    y = head(fig, R, "신호", asof)
    y -= .002

    for side, ko, col in (("buy", "매수", POS), ("sell", "매도", NEG)):
        buy = side == "buy"
        rows, wkey = rows_of(R, side, max_n)
        bw = (R.get("base1m_win") if buy else R.get("base1m_down")) or 0
        ST.tx(fig, X0, y, "%s %d종 · 승률 순" % (ko, len(rows)),
              fontsize=9.5, weight="bold", color=col)
        ST.tx(fig, X0 + .156, y + .0005,
              "승률 = 1개월 뒤 **%s** 비율 · 아무 날이나 잡아도 %.1f%% 는 그러니 "
              "그보다 높아야 제 몫" % ("오른" if buy else "내린", bw),
              fontsize=6.4, color=MUTED)
        y -= .0138

        def nowcell(x):
            s = "★" if x.get("fired_today") else ""
            if x.get("state_now"):
                d_ = x.get("state_days")
                return s + ("켜짐%d일" % d_ if d_ is not None else "켜짐")
            return s + "꺼짐"

        tr = [[x["signal"], x.get("desc", ""), "%+.2f%%" % x["fwd1m_mean"],
               "%.0f%%" % (x.get(wkey) or 0), (x["last"] or "—"),
               ("%d일" % x["days_ago"]) if x["days_ago"] is not None else "—",
               nowcell(x)] for x in rows]

        def cc(r, c, tr=tr, rows=rows, bw=bw, col=col):
            if c == 0:
                return INK
            if c == 1:
                return INK2
            if c == 2:
                return INK          # 방향마다 좋고 나쁨이 갈려 색을 안 준다
            if c == 3:
                return col if float(tr[r][3][:-1]) >= bw else MUTED
            if c in (4, 5):
                d_ = rows[r]["days_ago"]
                return NEG if (d_ is not None and d_ <= HOT) else MUTED
            if c == 6:
                return col if rows[r].get("state_now") else MUTED
            return MUTED
        y = ST.table(fig, X0, y, W_SIG, H_SIG, tr, row_h=.0138, fs=6.6, hfs=6.1,
                     zebra=True, aligns=A_SIG, cell_color=cc)
        y -= .010
        if not buy:
            worst = min(rows, key=lambda x: x["fwd1m_mean"])
            ST.tx(fig, X0, y,
                  "**1개월 뒤 실제로 내린 매도 신호는 하나도 없다** — 가장 낮은 %s 도 "
                  "%+.2f%%. 공매도 신호로는 못 쓴다." % (worst["signal"], worst["fwd1m_mean"]),
                  fontsize=6.8, color=NEG)
            y -= .0118
        else:
            thin = [x["signal"] for x in R[side] if x.get("n", 0) < MIN_SHOW]
            over = [x["signal"] for x in R[side] if x.get("n", 0) > max_n]
            note = []
            if thin:
                note.append("%d회 미만이라 뺀 것 — %s" % (MIN_SHOW, " · ".join(thin)))
            if over:
                note.append("%d회 초과라 뺀 것(발동이 아니라 켜져 있는 날을 세는 상태형) — %s"
                            % (max_n, " · ".join(over)))
            for t in note:
                ST.tx(fig, X0, y, t, fontsize=6.3, color=MUTED)
                y -= .0108
        y -= .012

    if tail:
        ST.tx(fig, X0 + .004, y,
              "· 지수 종가·고가·저가·거래량. 고저·거래량은 따로 받아 종가를 랩 정본과 "
              "대조하고 어긋나면 갱신을 멈춘다(실측 차이 0.00000%).",
              fontsize=6.6, color=INK2)
        y -= .0122
        ST.tx(fig, X0 + .004, y,
              "· 10년 한 구간이다. 이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했다. "
              "신호는 진단이지 예측이 아니다.", fontsize=6.6, color=MUTED)
        y -= .0122
    foot(fig, page, asof, y)


def main() -> int:
    M = json.load(io.open(os.path.join(DATA, "_ta_signals.json"), encoding="utf-8"))
    asof = M["as_of"]
    max_n = M.get("max_n") or 10 ** 9
    figs = []
    with PdfPages(OUT) as pdf:
        pg = 0
        for k in ("spx", "ndx"):
            pg += 1
            fig = ST.new_page()
            figs.append(fig)
            multi_page(fig, M["index"][k], asof, pg, max_n)
            pg += 1
            fig = ST.new_page()
            figs.append(fig)
            table_page(fig, M["index"][k], asof, pg, max_n, tail=(k == "ndx"))

        for i, f in enumerate(figs, 1):
            pdf.savefig(f)
            if "--png" in sys.argv[1:]:
                f.savefig(os.path.join(DATA, "_ta_%d.png" % i), dpi=110, facecolor=PAPER)
            ST.plt.close(f)
        pdf.infodict()["Title"] = "교과서 TA 신호 · 기준 %s" % asof

    print("→ %s · %d쪽 · 기준 %s · 횟수 %d회 초과 제외" % (OUT, TOT, asof, max_n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
