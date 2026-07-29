# -*- coding: utf-8 -*-
"""build/strategy_book_pdf.py — 랩의 전 전략 총람 → data/strategy_book.pdf

무엇을. explorer.html 이 화면으로 보여주는 것(data/strategy_index.json)을 종이 한 벌로
옮긴다. 랩이 지금까지 잰 전략 전부다 — 이긴 것도 진 것도 같이 싣는다.
판형·색·표는 build/style_top_pdf.py 를 import 해서 쓴다.

🚨 이 문서에서 **세로로 비교하면 안 된다.** 세 가지가 전략마다 다르다.
  ① 구간   2006년부터 잰 것과 2년치가 같은 표에 있다. CAGR 을 나란히 놓으면 안 된다.
  ② 대조군  동일가중 유니버스·SPY·60/40·모전략·현금이 섞여 있다. 초과수익의 뜻이 다르다.
  ③ 눈금   성격마다 봐야 할 축이 다르다 —
             수익엔진은 수익, 배분기는 샤프, 타이밍오버레이·위험감축은 낙폭이다.
           위험감축을 상시보유와 CAGR 로 겨루면 지는 게 정상이고 그것은 실패가 아니다.
  그래서 표를 성격으로 나누고, 대조군을 나란히 볼 수 없는 전략에는 그 사유를 적는다.

  python build/strategy_book_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys
from collections import Counter

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_book.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER = ST.POS, ST.NEG, ST.ACC, ST.PAPER

# 등급 색 — 배포·제한적 유효만 살리고 나머지는 눌러 둔다. '진 것'을 붉게 칠해 겁주지 않는다.
GCOL = {"배포": POS, "제한적 유효": ACC, "통과 후보": ST.CHAMP}
# 한 쪽에 담기는 '행 수' 예산. 성격 제목은 2행어치를 먹는다.
# 성격마다 새 쪽으로 넘기면 배분기(8종) 하나가 한 쪽을 통째로 쓴다 — 흘려 담는다.
CAP_P1, CAP_PN, HEAD_COST = 46, 62, 2


def load():
    p = os.path.join(DATA, "strategy_index.json")
    return json.load(io.open(p, encoding="utf-8"))


def safe(s):
    """맑은 고딕에 없는 글자를 바꾼다.

    🚨 원본(strategy_index.json)의 이름·대조군 라벨에 U+2212(−)가 섞여 있다. 그대로 그리면
      두부(□)로 나가고 경고는 stderr 한 줄뿐이라 로그를 안 보면 모른 채 배포된다.
      같은 이유로 ⚠(U+26A0)·화살표도 ASCII 로 눕힌다.
    """
    if not s:
        return s
    for a, b in (("−", "-"), ("⚠", "!"), ("→", "->"), ("←", "<-"),
                 ("≤", "<="), ("≥", ">=")):
        s = s.replace(a, b)
    return s


def _cut(s, n):
    """잘렸다는 것이 보이게 말줄임을 붙인다 — 그냥 자르면 이름이 원래 그런 줄 안다."""
    return s if len(s) <= n else s[: n - 1] + "…"


def bench_short(lab):
    """대조군 라벨을 칸에 맞춘다.

    원본은 'S&P 500(PR) 매수후보유'처럼 길다. 13자로 그냥 자르면 'S&P 500(PR) 매'가 되어
    잘린 티가 나므로, 흔한 꼬리를 먼저 떼고 그래도 길면 말줄임을 붙인다.
    """
    if not lab:
        return "—"
    s = safe(lab)
    for tail in (" 매수후보유", " (타이밍 없는 원계열)", " 매수 후 보유"):
        if s.endswith(tail):
            s = s[: -len(tail)]
    return _cut(s, 13)


def short(d):
    return (d or "")[2:7].replace("-", "-") if d else "—"


def num(v, d=2, sign=True):
    if v is None:
        return "—"
    s = "%+.*f" % (d, v) if sign else "%.*f" % (d, v)
    return s


def rows_of(items, role):
    """한 성격의 표 행. 등급 순 → 그 안에서 수익 순."""
    go = {g: i for i, g in enumerate(
        ["배포", "제한적 유효", "통과 후보", "역방향 유의", "구별 불가",
         "소수 사건 의존", "열위", "미채택", "판정 불가"])}
    sel = [x for x in items if x.get("role") == role]
    sel.sort(key=lambda x: (go.get(x.get("grade"), 99),
                            -((x.get("metrics") or {}).get("cagr") or -1e9)))
    out = []
    for x in sel:
        m, b = x.get("metrics") or {}, x.get("bench") or {}
        dc = (m.get("cagr") - b.get("cagr")) if (m.get("cagr") is not None
                                                 and b.get("cagr") is not None) else None
        ds = (m.get("sharpe") - b.get("sharpe")) if (m.get("sharpe") is not None
                                                     and b.get("sharpe") is not None) else None
        ok = x.get("cmp_ok")
        out.append({
            "x": x,
            "c": [_cut(safe(x.get("name") or ""), 34),
                  "%s~%s" % (short(x.get("start")), short(x.get("end"))),
                  num(m.get("cagr"), 1), num(m.get("sharpe"), 2), num(m.get("mdd"), 1),
                  bench_short(b.get("label")),
                  num(dc, 1) if ok else "·", num(ds, 2) if ok else "·",
                  safe(x.get("grade")) or "—", x.get("holds") or "—"],
        })
    return out


W = [.300, .078, .052, .048, .056, .092, .058, .050, .076, .044]
H = ["전략", "구간", "CAGR %", "샤프", "MDD %", "대조군", "Δ CAGR", "Δ샤프", "판정", "보유"]
AL = ["l", "c", "r", "r", "r", "l", "r", "r", "l", "c"]


def draw_table(fig, y, rs, title, sub=None):
    ST.tx(fig, X0, y, title, fontsize=11, weight="bold")
    if sub:
        ST.tx(fig, X1, y + .001, sub, fontsize=6.6, color=MUTED, ha="right")
    body = [r["c"] for r in rs]

    def cc(r, c):
        x = rs[r]["x"]
        if c == 0:
            return INK
        if c == 8:
            return GCOL.get(x.get("grade"), MUTED)
        if c in (2, 6, 7):
            v = body[r][c]
            if v in ("—", "·"):
                return MUTED
            return POS if not v.startswith("-") else NEG
        return MUTED
    return ST.table(fig, X0, y - .014, W, H, body, row_h=.0132, fs=6.8, hfs=6.4,
                    aligns=AL, cell_color=cc,
                    cell_weight=lambda r, c: "bold" if c == 0 else "normal", zebra=True)


def footer(fig, page, total, as_of):
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .026,
          "전략 총람 · 구간·대조군·눈금이 전략마다 다르다 — 세로로 비교하지 말 것 · "
          "Δ 는 그 전략의 대조군 대비이고, · 는 나란히 볼 수 없는 경우다",
          fontsize=6.2, color=MUTED)
    ST.tx(fig, X1, .026, "%d / %d · 기준 %s" % (page, total, as_of),
          fontsize=6.4, color=MUTED, ha="right")


def main() -> int:
    D = load()
    items = D.get("items") or []
    if not items:
        raise SystemExit("data/strategy_index.json 에 전략이 없다 — 먼저 build/strategy_index.py")
    as_of = D.get("as_of") or "—"
    roles = [r for r in (D.get("role_order") or []) if any(x.get("role") == r for x in items)]

    # 쪽 채우기 — 한 쪽에 여러 성격이 들어갈 수 있다
    pages, cur, left = [], [], CAP_P1
    for role in roles:
        rs, first = rows_of(items, role), True
        while rs:
            room = left - HEAD_COST
            if room < 3:                       # 제목만 넣고 끝날 자리면 다음 쪽으로
                pages.append(cur); cur, left = [], CAP_PN
                room = left - HEAD_COST
            take, rs = rs[:room], rs[room:]
            cur.append((role, take, not first))
            left -= HEAD_COST + len(take)
            first = False
            if rs:
                pages.append(cur); cur, left = [], CAP_PN
    if cur:
        pages.append(cur)
    total = len(pages)

    with PdfPages(OUT) as pdf:
        for pi, blocks in enumerate(pages):
            fig = ST.new_page()
            y = .960
            if pi == 0:
                ST.tx(fig, X0, y, "전략 총람", fontsize=23, weight="bold")
                ST.tx(fig, X0, y - .034, "이 랩이 지금까지 잰 전략 전부 — 이긴 것도 진 것도",
                      fontsize=10, color=ACC)
                ST.tx(fig, X1, y - .030, "%d종 · 기준 %s" % (len(items), as_of),
                      fontsize=8.5, color=MUTED, ha="right")
                ST.hline(fig, X0, X1, y - .046, RULE, .9)
                y -= .060
                # 성격 × 판정 교차표
                gs = [g for g in (D.get("grade_order") or []) if any(x.get("grade") == g for x in items)]
                cnt = Counter((x.get("role"), x.get("grade")) for x in items)
                body = [[safe(r)] + ["%d" % cnt[(r, g)] if cnt[(r, g)] else "·" for g in gs]
                        + ["%d" % sum(1 for x in items if x.get("role") == r)] for r in roles]
                body.append(["합계"] + ["%d" % sum(1 for x in items if x.get("grade") == g) for g in gs]
                            + ["%d" % len(items)])
                w2 = [.150] + [(.884 - .150 - .060) / len(gs)] * len(gs) + [.060]
                y = ST.table(fig, X0, y, w2, ["성격"] + [safe(g) for g in gs] + ["계"], body,
                             row_h=.0165, fs=7.4, hfs=6.6,
                             aligns=["l"] + ["c"] * (len(gs) + 1), zebra=True,
                             cell_color=lambda r, c: (INK if c == 0 else
                                                      (GCOL.get(gs[c - 1], MUTED) if 0 < c <= len(gs) else INK)))
                ST.tx(fig, X0, y - .009,
                      "판정은 그 전략의 대조군 대비다. %s "
                      "· 목록에서 뺀 %d종은 여기에도 없다(측정 기록은 원본에 남는다)."
                      % (safe((D.get("cmp_note") or "").split(".")[0] + "." if D.get("cmp_note") else ""),
                         D.get("n_hidden") or 0),
                      fontsize=6.6, color=MUTED)
                y -= .030
            for role, rs, cont in blocks:
                ttl = safe(role) + (" (이어짐)" if cont else "")
                sub = None
                if not cont:
                    tot_r = sum(1 for x in items if x.get("role") == role)
                    n_ok = sum(1 for x in items if x.get("role") == role and x.get("cmp_ok"))
                    sub = "%d종 · 대조군 비교 가능 %d" % (tot_r, n_ok)
                y = draw_table(fig, y, rs, ttl, sub) - .026
            footer(fig, pi + 1, total, as_of)
            pdf.savefig(fig, facecolor=PAPER); plt.close(fig)
        d = pdf.infodict()
        d["Title"] = "여두 전략 랩 — 전략 총람"

    print("→ %s · %d쪽 · %dKB · 전략 %d종(제외 %d)"
          % (OUT, total, os.path.getsize(OUT) // 1024, len(items), D.get("n_hidden") or 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
