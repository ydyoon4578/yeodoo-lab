# -*- coding: utf-8 -*-
"""build/guru_top10_pdf.py — 거장 상위 10종목 전략 PDF → data/guru_top10_portfolios.pdf

build/style_top_pdf.py 와 **같은 양식**이다. 판형·색·표·지표 계산을 베끼지 않고 그 모듈을
그대로 import 해서 쓴다 — 베끼면 한쪽만 고쳐질 때 두 문서가 조용히 달라진다.

## 규칙 — 스타일 전략과 같게 맞춘 것

  후보     유니버스 518종목(S&P 500 ∪ NASDAQ 100). 13F 보유 중 유니버스 밖은 버린다.
  선정     그 운용사의 유니버스 내 보유 중 **비중 상위 10종목**
  비중     그 10종목의 합을 100%로 재정규화 (동일가중이 아니라 **원래 비중의 비율 그대로**)
  대조군   S&P 500(PR) · NASDAQ 100(PR) — 스타일 전략과 같은 가격지수
  구간     최근 252거래일(1년)
  비용     0(gross)

## 13F 때문에 스타일 전략과 다를 수밖에 없는 것

  리밸런스  분기말 + 2개월의 월말. 13F 제출 마감이 분기말+45일이라 그 전에는 명단을 알 수 없다.
            (스타일 전략은 매월 말 다시 고른다 — 이쪽은 분기에 한 번뿐이다.)
  룩어헤드  공시일(filed)이 체결일보다 뒤인 분기는 버린다.
  주식수    분기말 가치를 체결월 가격으로 환산한다(v × P[체결월]/P[분기말]). 분기말 가치를
            그대로 쓰면 그 사이 오른 종목을 팔고 내린 종목을 사는 2개월짜리 역발상 매매를
            공짜로 주입하게 된다.

## ⚠ 대조군을 바꾸면 무엇이 달라지나 — 읽기 전에 알아야 한다

build/guru17_backtest.py 는 대조군을 **같은 풀 동일가중**으로 두었다. 유니버스가 오늘
스냅샷이라 과거 보유 중 '지금 대형주로 살아남은 것'만 남는데, 대조군을 같은 풀에서 뽑으면
그 생존편향이 양쪽에 똑같이 실려 상쇄되기 때문이다.

이 문서는 요청대로 대조군을 SPX·NDX 가격지수로 바꿨다. 그 결과 **생존편향이 더는 상쇄되지
않고 초과수익 쪽으로 전부 흘러든다.** 방향은 명확히 상방이고 크기는 이 저장소 안에서
측정할 수 없다. 여기 초과수익을 알파로 읽으면 안 되는 첫 번째 이유다.

두 번째 이유는 명단이다 — 운용사 18곳은 2026년 시점의 유명세로 손으로 고른 것이라
순위 자체가 사후선택이다. 그래서 이 문서에는 검정(t·p)을 싣지 않는다. 검정이 필요하면
data/guru17_portfolios.pdf(진단물) 쪽을 볼 것.

  python build/guru_top10_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, rcParams
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru_top10_portfolios.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST          # 판형·색·표·지표를 그대로 쓴다(베끼지 않는다)

# style_top_pdf 는 맑은 고딕(Windows)을 잡는다. mac/리눅스에서도 같은 꼴이 나오게 다시 잡는다.
for _p in ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/NanumGothic.ttf",
           "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"):
    if os.path.exists(_p):
        try: font_manager.fontManager.addfont(_p)
        except Exception: pass
_HAVE = {f.name for f in font_manager.fontManager.ttflist}
KFONT = next((n for n in ("Malgun Gothic", "Apple SD Gothic Neo", "NanumGothic",
                          "Nanum Gothic", "Noto Sans CJK KR") if n in _HAVE), None)
if not KFONT:
    raise SystemExit("한글 폰트를 찾지 못했다 — 없이 그리면 문서 전체가 두부(□)로 나온다.")
rcParams["font.family"] = KFONT
rcParams["axes.unicode_minus"] = False

TOPN = 10               # 상위 몇 종목 — 스타일 전략과 같다
LAG_M = 2               # 분기말 → 체결월
WINDOW = ST.WINDOW      # 최근 252거래일
MIN_HOLD = 4            # 유니버스 내 보유가 이보다 적으면 그 분기는 산출하지 않는다

# 이름을 짧게 — 표 칸에 들어가야 한다
X0, X1 = ST.X0, ST.X1
tx, hline, box, table, num = ST.tx, ST.hline, ST.box, ST.table, ST.num
INK, INK2, MUTED = ST.INK, ST.INK2, ST.MUTED
LINE, RULE, PAPER = ST.LINE, ST.RULE, ST.PAPER
POS, NEG, ACC = ST.POS, ST.NEG, ST.ACC
BM1, BM2 = ST.BM1, ST.BM2
IDXC, SECS = ST.IDXC, ST.SECS


def add_months(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m += k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def build_weights(cik, G, P):
    """분기별 13F → {체결 거래일 인덱스: {티커: 비중}}. 상위 10종목을 100%로 재정규화한다.

    반환 (스케줄, 진단). 스케줄은 (거래일 인덱스, 연월, 비중dict) 목록(시간순).
    """
    H, FILED = G["holdings"], (G.get("filed") or {})
    qs = sorted(q for q in H if cik in H[q])
    # 월말 → 그 달의 마지막 거래일 인덱스
    me_by_month = {}
    for i in P.me:
        me_by_month[P.dates[i][:7]] = i
    me_by_month[P.dates[-1][:7]] = max(me_by_month.get(P.dates[-1][:7], -1), len(P.dates) - 1)

    sched, diag = [], {"lookahead": 0, "thin": 0, "nofill": 0}
    for q in qs:
        ex_m = add_months(q[:7] if len(q) >= 7 else q, LAG_M)
        i = me_by_month.get(ex_m)
        if i is None:
            diag["nofill"] += 1
            continue
        # 룩어헤드 — 공시일이 체결일보다 뒤면 그때는 알 수 없던 명단이다
        f = (FILED.get(q) or {}).get(cik)
        if f and f > P.dates[i]:
            diag["lookahead"] += 1
            continue
        raw = H[q][cik] or {}
        # 주식수 고정 환산 — 분기말 가치를 체결월 가격으로 옮긴다
        qi = me_by_month.get(q[:7])
        w = {}
        for t, v in raw.items():
            if t not in P.px or not v or v <= 0:
                continue
            pr = P.px[t][i]
            pq = P.px[t][qi] if qi is not None else None
            if pr is None or pr != pr or pr <= 0:
                continue
            w[t] = v * ((pr / pq) if (pq and pq == pq and pq > 0) else 1.0)
        if len(w) < MIN_HOLD:
            diag["thin"] += 1
            continue
        top = sorted(w.items(), key=lambda kv: -kv[1])[:TOPN]
        s = sum(v for _t, v in top) or 1.0
        sched.append((i, ex_m, {t: v / s for t, v in top}))   # ← 상위 10의 합을 100%로
    sched.sort(key=lambda x: x[0])
    return sched, diag


def backtest(P, sched):
    """리밸런스 사이에는 표류(매수후보유). 반환 (nav, start, end, n_rebal) 또는 None."""
    if not sched:
        return None
    start = sched[0][0]
    end = len(P.dates) - 1
    if end - start < 30:
        return None
    nav = np.ones(end - start + 1, float)
    cur = None                      # {티커: 주식수(정규화)}
    si = 0
    val = 1.0
    for k in range(start, end + 1):
        # 그날이 리밸런스일이면 종가로 비중을 다시 맞춘다
        while si < len(sched) and sched[si][0] == k:
            w = sched[si][2]
            cur = {}
            for t, x in w.items():
                p = P.px[t][k]
                if p is not None and p == p and p > 0:
                    cur[t] = x / p
            si += 1
        if cur:
            v, den = 0.0, 0.0
            for t, sh in cur.items():
                p = P.px[t][k]
                if p is not None and p == p and p > 0:
                    v += sh * p
                    den += 1
            if den:
                if k > start:
                    prev = 0.0
                    for t, sh in cur.items():
                        p = P.px[t][k - 1]
                        if p is not None and p == p and p > 0:
                            prev += sh * p
                    if prev > 0:
                        val *= v / prev
        nav[k - start] = val
    return {"nav": nav, "start": start, "end": end, "n_rebal": len(sched)}


def window(R, P):
    """최근 252거래일로 자르고 시작 = 1 로 되돌린다 — 스타일 전략과 같은 창."""
    nav, s, e = R["nav"], R["start"], R["end"]
    n = min(WINDOW, len(nav) - 1)
    sub = nav[-(n + 1):]
    return {"nav": sub / sub[0], "start": e - n, "end": e,
            "n_rebal": sum(1 for i, _m, _w in R["_sched"] if i >= e - n)}


def pf_rows(P, w):
    """비중 dict → 표 행(비중 내림차순)."""
    out = []
    for k, (t, x) in enumerate(sorted(w.items(), key=lambda kv: -kv[1])):
        u = P.uni.get(t) or {}
        out.append(["%d" % (k + 1), t, (u.get("name") or "")[:24],
                    SECS.get(u.get("sector") or "", ""), ST.idx_of(P, t), "%.1f" % (x * 100)])
    return out


def footer(fig, page, total):
    hline(fig, X0, X1, .034, LINE, .6)
    tx(fig, X0, .026, "거장 상위 10종목 전략 · 13F 보유 중 유니버스 상위 10종목을 원래 비중 비율로 "
                      "100% 환산 · 대조군은 가격지수(PR) · 비용 0 · 명단은 손으로 고른 18곳이다",
       fontsize=6.4, color=MUTED)
    tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
       fontsize=6.4, color=MUTED, ha="right")


# ── 운용사 한 블록(반 쪽) — style_top_pdf.draw_block 과 같은 배치 ────────────
def draw_block(fig, P, top, name, R, prev_w, now_w, now_lab, diag):
    nav = R["nav"]
    d0, d1 = P.dates[R["start"]], P.dates[R["end"]]
    gn = ST.bench_nav(P, P.gspc, R["start"], R["end"])
    nn = ST.bench_nav(P, P.ndx, R["start"], R["end"])
    m, mg, mn = ST.metrics(nav), ST.metrics(gn), ST.metrics(nn)
    tr = ST.trails(nav, P.dates, R["start"])
    tg = ST.trails(gn, P.dates, R["start"])
    tn = ST.trails(nn, P.dates, R["start"])

    y = top
    tx(fig, X0, y, name, fontsize=15.5, weight="bold")
    tx(fig, X1, y + .0015, "13F 복제", fontsize=8, color=ACC, ha="right")
    # 유니버스 내 보유가 10종목이 안 되면 '상위 10종목'이라는 제목이 실제와 다르다 — 실수를
    #   적는다. 별도 줄로 빼면 설명문과 겹치고 높이를 먹는다.
    n_now = len(now_w)
    top1 = max(now_w.values()) * 100 if now_w else 0.0
    hd = ("상위 %d종목" % TOPN) if n_now >= TOPN else ("유니버스 내 %d종목뿐" % n_now)
    tx(fig, X1, y - .0100, "%s ~ %s · 분기 %d회 리밸런스 · %s · 비중 재정규화 · 최대 %.1f%% · 비용 0"
       % (d0, d1, R["n_rebal"], hd, top1), fontsize=6.6,
       color=(NEG if (n_now < TOPN or top1 > 50.0) else MUTED), ha="right")
    y -= .0205
    hline(fig, X0, X1, y, RULE, .9)
    y -= .008
    tx(fig, X0, y, "13F 공시로 이 운용사의 유니버스 내 보유를 읽어 비중 상위 10종목만 남기고, "
                   "그 10종목의 합을 100%로 환산해 담는다. 분기말+2개월의 월말에 다시 맞추고 "
                   "사이에는 표류시킨다.", fontsize=7.1, color=INK2, linespacing=1.58)
    y -= .0285

    LW = .432
    tx(fig, X0, y, "최근 1년 성과", fontsize=9.2, weight="bold")
    t_top = y - .0135
    rows = []
    for lab, k, d, sg in (("수익률 %", "ret", 2, True), ("변동성 %", "vol", 2, False),
                          ("샤프", "sharpe", 2, True), ("MDD %", "mdd", 2, True)):
        rows.append([lab, num(m.get(k), d, sg), num(mg.get(k), d, sg), num(mn.get(k), d, sg)])

    def cc(r, c):
        if c == 0:
            return INK
        if c == 1:
            v = rows[r][1]
            if r in (0, 2) and v != "—":
                return POS if not v.startswith("-") else NEG
            return INK
        return MUTED

    y1 = table(fig, X0, t_top, [.132, .102, .099, .099], ["지표", "복제", "S&P 500 PR", "NDX PR"],
               rows, row_h=.0140, cell_color=cc,
               cell_weight=lambda r, c: "bold" if c == 1 else "normal")

    y2 = y1 - .015
    tx(fig, X0, y2, "기간별 수익률 %", fontsize=9.2, weight="bold")
    labs = [l for l, _ in ST.TRAIL] + ["YTD"]
    prow = [["복제"] + [num(tr.get(l), 1) for l in labs],
            ["S&P 500 PR"] + [num(tg.get(l), 1) for l in labs],
            ["NDX PR"] + [num(tn.get(l), 1) for l in labs],
            ["초과(vs S&P)"] + [("—" if (tr.get(l) is None or tg.get(l) is None)
                                 else num(tr[l] - tg[l], 1)) for l in labs]]

    def cc2(r, c):
        if c == 0:
            return INK if r in (0, 3) else MUTED
        v = prow[r][c]
        if r in (0, 3) and v != "—":
            return POS if not v.startswith("-") else NEG
        return MUTED

    y3 = table(fig, X0, y2 - .0132, [.117] + [.0525] * 6, [""] + labs, prow,
               row_h=.0140, cell_color=cc2,
               cell_weight=lambda r, c: "bold" if (r == 0 and c > 0) else "normal")

    # 누적 곡선 — 표 두 개가 차지한 높이를 그대로 쓴다(스타일 전략과 같다)
    cx0, cw = X0 + LW + .052, X1 - (X0 + LW + .052)
    ax = fig.add_axes([cx0, y3, cw, t_top - y3])
    ax.set_facecolor(PAPER)
    xi = np.arange(len(nav))
    ax.axhline(100, color=LINE, lw=.6)
    ax.plot(xi, gn * 100, color=BM1, lw=1.0, ls="--", label="S&P 500(PR)")
    ax.plot(xi, nn * 100, color=BM2, lw=1.0, ls=":", label="NASDAQ 100(PR)")
    ax.plot(xi, nav * 100, color=ACC, lw=1.7, label="복제")
    ax.set_ylabel("누적 (시작 = 100)", fontsize=6.8, color=MUTED, labelpad=2)
    ticks, seen = [], set()
    for k in range(len(xi)):
        mth = P.dates[R["start"] + k][:7]
        if mth not in seen:
            seen.add(mth); ticks.append(k)
    ticks = ticks[::2]
    ax.set_xticks(ticks)
    ax.set_xticklabels([P.dates[R["start"] + k][2:7] for k in ticks])
    ax.set_xlim(0, len(xi) - 1)
    ax.tick_params(labelsize=6.3, colors=MUTED, length=2, pad=1.5)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.grid(True, color=LINE, lw=.4, alpha=.65)
    ax.set_axisbelow(True)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[2:] + h[:2], l[2:] + l[:2], fontsize=6.3, frameon=False, loc="upper left",
              handlelength=1.8, borderpad=.1, labelspacing=.25)

    # 포트폴리오 두 벌
    yp = y3 - .018
    tx(fig, X0, yp, "포트폴리오", fontsize=9.2, weight="bold")
    yt = yp - .0142
    ps, ns = set(prev_w), set(now_w)

    def pf(x0, title, sub, w, other, mark_new):
        tx(fig, x0, yt, title, fontsize=7.5, weight="bold")
        tx(fig, x0 + .428, yt, sub, fontsize=6.5, color=MUTED, ha="right")
        rows_ = pf_rows(P, w)
        flags = [r[1] not in other for r in rows_]
        for i, r in enumerate(rows_):
            if flags[i] and mark_new:
                r[1] = "＋" + r[1]

        def c3(r, c):
            if c == 4:
                return IDXC.get(rows_[r][4], MUTED)
            if c == 0:
                return MUTED
            if flags[r]:
                return POS if mark_new else NEG
            return INK if c in (1, 2) else MUTED

        return table(fig, x0, yt - .0122, [.026, .058, .180, .044, .036, .084],
                     ["#", "티커", "종목명", "섹터", "지수", "비중%"], rows_,
                     row_h=.0128, fs=6.9, hfs=6.4,
                     aligns=["c", "l", "l", "l", "l", "r"], cell_color=c3,
                     cell_weight=lambda r, c: "bold" if c in (1, 4) else "normal", zebra=True)

    pf(X0, "직전 리밸런스", "%s · 지금 보유 중" % P.dates[R["_prev_i"]], prev_w, ns, False)
    pf(X0 + .456, "오늘 재산출", "%s · 다음 리밸런스 후보" % now_lab, now_w, ps, True)
    keep = len(ps & ns)
    tx(fig, X1, yp + .0012,
       "교체 %d종목 · 유지 %d종목 · ＋ 신규편입 · 붉은 종목은 오늘 재산출에서 빠진 자리 · "
       "룩어헤드로 버린 분기 %d" % (len(ns) - keep, keep, diag.get("lookahead", 0)),
       fontsize=6.4, color=MUTED, ha="right")


# ── 요약 쪽 ─────────────────────────────────────────────────────────────────
def draw_summary(fig, P, res, order, total):
    R0 = res[order[0]]["w"]
    d0, d1 = P.dates[R0["start"]], P.dates[R0["end"]]
    tx(fig, X0, .962, "거장 상위 10종목 전략", fontsize=23, weight="bold")
    tx(fig, X0, .928, "13F 복제 · 최근 1년 요약", fontsize=10, color=ACC)
    tx(fig, X1, .932, "%s ~ %s" % (d0, d1), fontsize=8.5, color=MUTED, ha="right")
    hline(fig, X0, X1, .916, RULE, .9)

    y = .898
    tx(fig, X0, y, "이 명단은 사후선택이다 — 2026년 시점의 유명세로 손으로 고른 18곳이라, "
                   "1위가 '가장 잘하는 운용사'라는 뜻이 아니다.", fontsize=7.4, color=NEG)
    y -= .013
    tx(fig, X0, y, "대조군을 지수(PR)로 두면 유니버스 생존편향이 상쇄되지 않고 초과수익 쪽으로 "
                   "흘러든다. 검정(t·p)은 싣지 않는다 — guru17_portfolios.pdf 를 볼 것.",
       fontsize=7.4, color=MUTED)
    y -= .022

    tx(fig, X0, y, "최근 1년 성과", fontsize=11.5, weight="bold")
    rows = []
    for k in order:
        E = res[k]
        R, m = E["w"], ST.metrics(E["w"]["nav"])
        mg = ST.metrics(ST.bench_nav(P, P.gspc, R["start"], R["end"]))
        mn = ST.metrics(ST.bench_nav(P, P.ndx, R["start"], R["end"]))
        keep = len(set(E["prev"]) & set(E["now"]))
        ix = [ST.idx_of(P, t) for t in E["now"]]
        rows.append([E["name"][:20], "%d종목" % len(E["now"]),
                     num(m["ret"], 2), num(m["vol"], 2, False), num(m["sharpe"], 2),
                     num(m["mdd"], 2), num(m["ret"] - mg["ret"], 2), num(m["ret"] - mn["ret"], 2),
                     "%d" % (len(E["now"]) - keep),
                     "%d·%d·%d" % (ix.count("SPX"), ix.count("공통"), ix.count("NDX"))])
    nS = len(rows)
    for lab, a in (("S&P 500 PR", P.gspc), ("NASDAQ 100 PR", P.ndx)):
        mb = ST.metrics(ST.bench_nav(P, a, R0["start"], R0["end"]))
        rows.append([lab, "대조군 · 가격지수", num(mb["ret"], 2), num(mb["vol"], 2, False),
                     num(mb["sharpe"], 2), num(mb["mdd"], 2), "—", "—", "—", "—"])

    def cc(r, c):
        if r >= nS:
            return MUTED
        if c in (2, 4, 5, 6, 7):
            v = rows[r][c]
            if v != "—":
                return POS if not v.startswith("-") else NEG
        return INK if c == 0 else INK2

    y = table(fig, X0, y - .016,
              [.150, .066, .076, .066, .054, .066, .078, .078, .050, .066],
              ["운용사", "종목", "수익률%", "변동성%", "샤프", "MDD%", "초과 vs S&P",
               "초과 vs NDX", "교체", "SPX·공통·NDX"], rows,
              row_h=.0148, fs=7.0, hfs=6.4,
              aligns=["l", "r", "r", "r", "r", "r", "r", "r", "r", "r"],
              cell_color=cc, zebra=True)

    # 누적 곡선 — 전 운용사 한 장에
    y -= .026
    tx(fig, X0, y, "최근 1년 누적 곡선", fontsize=11.5, weight="bold")
    ax = fig.add_axes([X0, y - .300, X1 - X0, .286])
    ax.set_facecolor(PAPER)
    gn = ST.bench_nav(P, P.gspc, R0["start"], R0["end"])
    nn = ST.bench_nav(P, P.ndx, R0["start"], R0["end"])
    xi = np.arange(len(gn))
    ax.axhline(100, color=LINE, lw=.6)
    for k in order:
        E = res[k]
        ax.plot(xi[:len(E["w"]["nav"])], E["w"]["nav"] * 100, lw=1.0, alpha=.85,
                label=E["name"][:14])
    ax.plot(xi, gn * 100, color=BM1, lw=1.6, ls="--", label="S&P 500(PR)")
    ax.plot(xi, nn * 100, color=BM2, lw=1.6, ls=":", label="NASDAQ 100(PR)")
    ticks, seen = [], set()
    for k in range(len(xi)):
        mth = P.dates[R0["start"] + k][:7]
        if mth not in seen:
            seen.add(mth); ticks.append(k)
    ax.set_xticks(ticks[::2])
    ax.set_xticklabels([P.dates[R0["start"] + k][2:7] for k in ticks[::2]])
    ax.set_xlim(0, len(xi) - 1)
    ax.set_ylabel("누적 (시작 = 100)", fontsize=7, color=MUTED)
    ax.tick_params(labelsize=6.5, colors=MUTED, length=2, pad=1.5)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.grid(True, color=LINE, lw=.4, alpha=.65)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.0, frameon=False, ncol=4, loc="upper left", handlelength=1.6,
              labelspacing=.25, columnspacing=1.1)
    footer(fig, 1, total)


# ── 본체 ────────────────────────────────────────────────────────────────────
def main() -> int:
    print("가격·유니버스 패널을 연다(style_top_pdf.Panel)…")
    P = ST.Panel()
    G = json.load(io.open(os.path.join(DATA, "guru_history.json"), encoding="utf-8"))
    names = G.get("names") or {}
    cov = G.get("coverage") or {}

    res = {}
    for cik in sorted(cov):
        if not (cov[cik] or {}).get("n_q"):
            continue
        sched, diag = build_weights(cik, G, P)
        R = backtest(P, sched)
        if not R:
            print("  건너뜀 %s — 리밸런스가 없거나 구간이 짧다" % (cov[cik].get("name") or cik))
            continue
        R["_sched"] = sched
        W = window(R, P)
        W["_sched"] = sched
        # 직전 리밸런스(지금 보유 중) · 최신 13F(다음 후보)
        prev_i, prev_w = sched[-1][0], sched[-1][2]
        W["_prev_i"] = prev_i
        # '다음 리밸런스 후보' = 같은(최신) 13F 를 **오늘 가격으로 환산**해 다시 고른 것.
        #   ⚠ 최신 분기를 그대로 쓰면 안 된다 — 직전 리밸런스가 이미 그 분기이고, 주식수 환산만
        #     빠져 명단이 조금 달라진다. 그걸 '다음 후보'라 적으면 새 공시가 온 것처럼 읽힌다.
        #     13F 는 분기에 한 번뿐이라 다음 후보는 '같은 명단을 오늘 가격으로 옮긴 것'이 맞다.
        H = G["holdings"]
        qlast = max((q for q in H if cik in H[q]), default=None)
        now_w, now_lab = prev_w, "오늘"
        if qlast:
            raw = H[qlast][cik] or {}
            qi = None
            for i in P.me:
                if P.dates[i][:7] == qlast[:7]:
                    qi = i
                    break
            last = len(P.dates) - 1
            w = {}
            for t, v in (raw or {}).items():
                if t not in P.px or not v or v <= 0:
                    continue
                pr, pq = P.px[t][last], (P.px[t][qi] if qi is not None else None)
                if pr is None or pr != pr or pr <= 0:
                    continue
                w[t] = v * ((pr / pq) if (pq and pq == pq and pq > 0) else 1.0)
            if len(w) >= MIN_HOLD:
                top = sorted(w.items(), key=lambda kv: -kv[1])[:TOPN]
                ssum = sum(v for _t, v in top) or 1.0
                now_w = {t: v / ssum for t, v in top}
                now_lab = "%s 공시 · %s 가격" % (qlast, P.dates[last])
        res[cik] = {"name": (cov[cik].get("name") or names.get(cik) or cik),
                    "full": R, "w": W, "prev": prev_w, "now": now_w,
                    "now_lab": now_lab, "diag": diag}

    if not res:
        raise SystemExit("복제할 운용사가 없다 — guru_history.json 을 확인할 것.")
    # 최근 1년 수익률 내림차순. 순위는 부록이지 추천이 아니라는 문구를 요약 쪽에 적는다.
    order = sorted(res, key=lambda c: -(ST.metrics(res[c]["w"]["nav"])["ret"] or -1e9))
    total = 1 + (len(order) + 1) // 2

    with PdfPages(OUT) as pdf:
        fig = ST.new_page(); draw_summary(fig, P, res, order, total)
        pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
        page = 2
        for i in range(0, len(order), 2):
            fig = ST.new_page()
            for k, cik in enumerate(order[i:i + 2]):
                E = res[cik]
                draw_block(fig, P, ST.BLOCK_TOPS[k], E["name"], E["w"],
                           E["prev"], E["now"], E["now_lab"], E["diag"])
            footer(fig, page, total)
            pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
            page += 1

    print("→ %s (%d쪽 · %dKB · 폰트 %s)" % (OUT, total, os.path.getsize(OUT) // 1024, KFONT))
    print("   운용사 %d곳 · 창 %s ~ %s"
          % (len(order), P.dates[res[order[0]]["w"]["start"]], P.dates[-1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
