# -*- coding: utf-8 -*-
"""build/style8_pdf.py — 스타일 8종 한눈에 → data/style8.pdf

무엇을. 홈 화면에 실리는 **스타일 8종**을 A4 두 쪽으로 뽑는다.
  1쪽  기간별 수익률(벤치마크 먼저) + 스타일 보유 셋
  2쪽  스타일 보유 다섯

`style_top_pdf.py` 가 «오늘 무엇을 담나» 를 전략별 반 쪽으로 싣는다면, 이 문서는
**여덟 줄을 한 화면에 놓고 견주는** 자리다. 회의에 들고 갈 한두 장이 필요해서 만들었다.

자료 — `data/style_perf.json` **하나만** 읽는다. 계산은 하지 않는다.
  그 파일을 만드는 것은 `build/style_top_pdf.py --json` 이고, 이 문서는 그 결과를 그린다.
  숫자를 두 번 계산하지 않는다 — 갈리면 조용히 어긋나기 때문이다.

판형·색·폰트·표는 `style_top_pdf.py` 에서 **그대로 가져온다**(그쪽이 정본이다).

보유 표 — 전월말과 금일을 **한 표에 나란히** 둔다. style.html 과 같은 열이다.
  -티커 = 다음 재선정에서 빠지는 종목 · +티커 = 새로 들어오는 종목

    python build/style8_pdf.py
"""
from __future__ import annotations

import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 · 와 ⚠ 를 찍다 죽지 않게
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

from style_top_pdf import (ACC, GROUND, HEAD_BG, INK, INK2, LINE, MUTED, NEG, PANEL2,  # noqa: E402
                           POS, RULE, X0, X1, hline, new_page, require_draw, table, tx)

try:
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
except Exception as e:                                        # pragma: no cover
    raise SystemExit("matplotlib 이 필요하다 — %s" % e)

SRC = os.path.join(DATA, "style_perf.json")
OUT = os.path.join(DATA, "style8.pdf")

# 홈 화면에 보이는 여덟 줄. style_perf.json 의 hide 목록 밖이 이 여덟이다 —
# 손으로 두 번 적지 않도록 여기서 한 번만 적고 아래에서 대조한다.
KEYS = ["div", "val", "qvm", "spmo", "size", "grow", "hbeta", "squal"]
TR = ["1일", "1주", "1개월", "3개월", "6개월", "1년", "YTD"]

# 섹터 약어를 펴서 쓴다 — 두 글자로는 회의에서 안 읽힌다.
SECTOR = {"부동": "부동산", "소재": "소재", "금융": "금융", "필소": "필수소비", "산업": "산업재",
          "유틸": "유틸리티", "헬스": "헬스케어", "커뮤": "커뮤니케이션", "경소": "경기소비",
          "에너": "에너지", "IT": "IT"}

# 방법론 한 줄 아래에 붙이는 산식. build/style_top_pdf.py 의 sc_* 함수에서 옮겼다.
#   ⚠ 지어내지 않는다. 산식이 바뀌면 그쪽을 고치고 여기를 따라 고친다.
GLOSS = {
    "div": "배당수익률 = 최근 4분기 주당배당금(선언 기준) ÷ 현재 주가",
    "val": "B/P = 주당순자산 ÷ 주가   E/P = 주당순이익(최근 4분기) ÷ 주가   "
           "S/P = 주당매출(최근 4분기) ÷ 주가 — 셋의 z 를 평균",
    "qvm": "퀄리티·가치·모멘텀 z 점수의 단순 평균 · 셋을 모두 가진 종목만 남긴다   "
           "여기 퀄리티는 MSCI 정의(ROE·부채비율·이익변동성)라 아래 퀄리티 줄과 다르다",
    "spmo": "(1개월 전 주가 ÷ 13개월 전 주가 - 1) ÷ 3년 주간수익률 표준편차   "
            "최근 1개월을 빼는 이유는 단기 반전을 피하려는 것",
    "size": "시가총액 = 주식수 × 주가 · 작을수록 상위",
    "grow": "3년 주당매출 연평균 성장률   3년 주당순이익 변화 ÷ 주가   12개월 모멘텀 — 셋의 z 를 평균",
    "hbeta": "베타 = 최근 252거래일 일간수익률의 시장과의 공분산 ÷ 시장 분산",
    "squal": "발생액비율 = (순이익 - 영업활동현금흐름) ÷ 평균 총자산 · 최근 4분기 합 기준   "
             "재무레버리지 = 부채총계 ÷ 자기자본",
}

ROW_H = 0.01175        # 보유 표 한 줄 — 두 쪽에 여덟 블록이 들어가는 높이다
BLK_H = 0.1730         # 블록 하나가 차지하는 세로(제목·방법론·산식·표)
PAGE1_N = 3            # 1쪽에 수익률 표를 얹고 남는 자리


def sgn(v, d=1):
    return "—" if v is None else ("%+.*f" % (d, v))


def main():
    require_draw()
    if not os.path.exists(SRC):
        raise SystemExit("%s 가 없다 — 먼저 `python build/style_top_pdf.py --json` 을 돌린다." % SRC)
    P = json.load(io.open(SRC, encoding="utf-8"))
    S = {x["key"]: x for x in P["styles"]}
    miss = [k for k in KEYS if k not in S]
    if miss:
        raise SystemExit("style_perf.json 에 없는 스타일: %s" % ", ".join(miss))
    hid = [k for k in KEYS if k in (P.get("hide") or {})]
    if hid:
        print("  ⚠ 숨김 목록에 든 스타일이 섞였다: %s — 홈 화면과 갈린다" % ", ".join(hid))
    asof, start = P["as_of"], P.get("start", "")
    nreb = S[KEYS[0]].get("n_rebal", 11)

    # ── 1쪽 머리 + 기간별 수익률 ────────────────────────────────────────────
    figs = []
    fig = new_page()
    figs.append(fig)
    y = .962
    tx(fig, X0, y, "스타일 8종", fontsize=17, weight="bold")
    tx(fig, X1, y + .002, "여두 전략 랩", fontsize=8, color=ACC, ha="right")
    y -= .017
    tx(fig, X0, y, "%s ~ %s · 월말 %d회 리밸런스 · 상위 10종목 동일가중"
       % (start, asof, nreb), fontsize=6.8, color=MUTED)
    y -= .012
    hline(fig, X0, X1, y, RULE, .9)
    y -= .016

    tx(fig, X0, y, "기간별 수익률", fontsize=10.5, weight="bold")
    tx(fig, X1, y, "%%  ·  샤프·MDD·이긴달은 %s 이후 구간  ·  샤프 내림차순" % start,
       fontsize=6.4, color=MUTED, ha="right")
    y -= .0125

    W = [.085, .175, .058, .058, .060] + [.064] * 7
    head = ["스타일", "지수", "샤프", "MDD", "이긴달"] + TR
    rows, kinds = [], []
    for bk, bx in (P.get("bench") or {}).items():
        bm, bt = bx.get("metrics") or {}, bx.get("trails") or {}
        rows.append([bx.get("label", bk), "벤치마크", "%.2f" % bm.get("sharpe", 0),
                     "%.1f" % bm.get("mdd", 0), "·"] + [sgn(bt.get(c)) for c in TR])
        kinds.append("b")
    for k in sorted(KEYS, key=lambda z: -S[z]["metrics"]["sharpe"]):
        x, m, t = S[k], S[k]["metrics"], S[k]["trails"]
        w = (x.get("win") or {}).get("spx") or [0, 12]
        rows.append([x["label"], x["ref"].replace("S&P 500 ", "").replace("MSCI USA ", ""),
                     "%.2f" % m["sharpe"], "%.1f" % m["mdd"], "%d/%d" % (w[0], w[1])]
                    + [sgn(t.get(c)) for c in TR])
        kinds.append("s")

    def pcol(r, c):
        if kinds[r] == "b":
            return MUTED
        if c == 1:
            return MUTED
        if c == 3:
            return NEG
        if c >= 5:
            v = rows[r][c]
            return POS if v.startswith("+") else (NEG if v.startswith("-") else INK)
        return INK

    def pw(r, c):
        return "bold" if (kinds[r] == "b" and c == 0) or c == 2 else "normal"

    y = table(fig, X0, y, W, head, rows, row_h=.0152, fs=7.4, hfs=6.6,
              aligns=["l", "l"] + ["r"] * 10, cell_color=pcol, cell_weight=pw)
    y -= .019
    tx(fig, X0, y, "스타일별 보유", fontsize=10.5, weight="bold")
    tx(fig, X1, y, "-티커 = 다음 재선정에서 빠짐  ·  +티커 = 새로 들어옴",
       fontsize=6.4, color=MUTED, ha="right")
    y -= .014

    # ── 보유 블록 ──────────────────────────────────────────────────────────
    HW = [.026] + [.082, .110, .055, .078, .094] + [.020] + [.082, .110, .055, .078, .094]
    n_on_page = 0
    for k in KEYS:
        if n_on_page >= (PAGE1_N if len(figs) == 1 else 5):
            fig = new_page()
            figs.append(fig)
            y, n_on_page = .962, 0
        y = draw_block(fig, S[k], k, y, HW)
        n_on_page += 1

    for i, f in enumerate(figs, 1):
        tx(f, X0, .022, "스타일 8종 · 기준일 %s · 여두 전략 랩" % asof, fontsize=6, color=MUTED)
        tx(f, X1, .022, "%d / %d" % (i, len(figs)), fontsize=6, color=MUTED, ha="right")

    with PdfPages(OUT) as pdf:
        for f in figs:
            pdf.savefig(f)
            plt.close(f)
    print("저장: %s · %d쪽 · 기준일 %s" % (OUT, len(figs), asof))


def draw_block(fig, x, key, y, HW):
    """스타일 한 블록 — 제목 · 방법론 · 산식 · 전월말/금일 한 표. 반환은 다음 y."""
    pv, td = (x.get("prev") or {}), (x.get("today") or {})
    pr, tr_ = pv.get("rows") or [], td.get("rows") or []
    pvt, tdt = {r["t"] for r in pr}, {r["t"] for r in tr_}
    nin = len([r for r in tr_ if r["t"] not in pvt])

    tx(fig, X0, y, x["label"], fontsize=11, weight="bold")
    tx(fig, X0 + .072, y, x["ref"], fontsize=7.2, color=ACC)
    tx(fig, X1, y, "교체 %d종" % nin if nin else "교체 없음", fontsize=6.4,
       color=MUTED, ha="right")
    y -= .0098
    hline(fig, X0, X1, y, RULE, .8)
    y -= .0090
    desc = [l.strip() for l in x["desc"].split("\n") if l.strip()]
    first = desc[0] if desc else ""
    i = first.find(". ")
    tx(fig, X0, y, first[:i + 1] if i > 0 else first, fontsize=7.0, color=INK2)
    y -= .0082
    if key in GLOSS:
        tx(fig, X0, y, GLOSS[key], fontsize=6.0, color=MUTED)
        y -= .0078

    mlab = x.get("mlab", "")
    tx(fig, X0 + .026 + .163, y, "전월말 기준 %s" % pv.get("d", ""), fontsize=6.3,
       color=INK2, ha="center")
    tx(fig, X0 + .026 + .419 + .020 + .163, y, "금일 기준 %s" % td.get("d", ""),
       fontsize=6.3, color=INK2, ha="center")
    y -= .0062

    head = ["#", "티커", "섹터", "지수", "MTD %", mlab, "", "티커", "섹터", "지수", "MTD %", mlab]
    rows, marks = [], []
    for i in range(10):
        a = pr[i] if i < len(pr) else None
        b = tr_[i] if i < len(tr_) else None

        def side(r, other, mark):
            if not r:
                return ["", "", "", "", ""]
            ch = r["t"] not in other
            return [(mark + r["t"]) if ch else r["t"],
                    SECTOR.get(r.get("s"), r.get("s") or ""), r.get("idx", ""),
                    sgn(r.get("mtd")), str(r.get("v", ""))]
        L, R = side(a, tdt, "-"), side(b, pvt, "+")
        rows.append([str(i + 1)] + L + [""] + R)
        marks.append((bool(a) and a["t"] not in tdt, bool(b) and b["t"] not in pvt))

    def cc(r, c):
        if c == 0:
            return MUTED
        if c in (1, 7):
            out_, in_ = marks[r]
            if c == 1 and out_:
                return "#2C6E8F"
            if c == 7 and in_:
                return NEG
            return INK
        if c in (3, 9):
            return MUTED
        if c in (4, 10):
            v = rows[r][c]
            return POS if v.startswith("+") else (NEG if v.startswith("-") else INK)
        return INK2

    def cw(r, c):
        return "bold" if c in (1, 7) else "normal"

    y = table(fig, X0, y, HW, head, rows, row_h=ROW_H, fs=6.6, hfs=6.0,
              aligns=["r", "l", "l", "c", "r", "r", "c", "l", "l", "c", "r", "r"],
              cell_color=cc, cell_weight=cw)
    return y - .018


if __name__ == "__main__":
    main()
