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
# 🚨 2026-09-21 — 랩 전 전략으로 넓히면서 이름을 바꿨다(종전 top10_strategies.pdf).
#   같은 이름을 두면 «10종목만» 이라고 읽힌다. strategy_book.pdf 는 **성격**으로 묶은
#   총람이고 이것은 **주기**로 묶은 총람이다 — 렌즈가 다르다.
OUT = os.path.join(DATA, "strategy_by_period.pdf")

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


# 빠른 주기부터 — 「얼마나 자주 손대나」 순서다. 성적 순이 아니다.
REB_ORDER = ["we", "me", "qe", "h", "y6"]
# 주기가 원천에 없는 것들 — 주기 뒤에 **성격**으로 이어 붙인다(사용자 요청 2026-09-21).
#   ⚠ 이 칸의 이름은 '주기'가 아니라 그 전략이 무엇인가다. 주기를 지어내지 않는다.
NOREB_ORDER = ["타이밍 오버레이", "자산배분", "거장 겹침", "페어 트레이딩", "미분류"]
REB_NOTE = {
    "we": "주마다 다시 고른다. 신호 수명이 짧은 규칙들이고, 회전이 가장 크다.",
    "me": "월말에 다시 고른다. 이 랩의 기본 주기이고 대부분이 여기 있다.",
    "qe": "분기말에 다시 고른다. 재무 공시 주기를 따르는 규칙들이라 회전이 가장 작다.",
    "h": "반기마다 다시 고른다.",
    "y6": "연 1회 t년 6월말에 다시 고른다(Fama-French 컨벤션).",
    "타이밍 오버레이": "고정 주기가 없다 — 신호가 바뀔 때 들어가고 나온다.",
    "자산배분": "자산 단위로 담는다. 주기는 규칙마다 원천에 따로 있다.",
    "거장 겹침": "13F 공시 주기(분기)를 따른다. 원천이 주기 칸을 안 싣는다.",
    "페어 트레이딩": "고정 주기가 없다 — 쌍이 벌어지면 들어가고 수렴하면 나온다.",
    "미분류": "주기가 원천에 없다. 없는 것을 지어 채우지 않았다.",
}


def noreb_of(x):
    """주기가 없는 전략의 성격 칸."""
    h = x.get("holdings") or {}
    if h.get("kind") == "timing" or x.get("role") == "타이밍오버레이":
        return "타이밍 오버레이"
    s = x.get("src")
    if s in ("자산배분", "거장 겹침", "페어 트레이딩"):
        return s
    return "미분류"


def reb_of(x):
    """주기 한 낱말. 모르면 빈 문자열 — **지어내지 않는다.**"""
    return REB_KO.get(x.get("reb") or "", "")


def by_reb(items):
    """주기별로 가른다 — 빠른 것부터. 주기 안에서는 t 순.

    🚨 주기를 섞어 한 줄에 세우면 안 되는 이유 — 회전이 주기로 거의 정해지고(주간 8종은
      연 10~28배, 분기 12종은 0.5~2배), 비용 후 성적이 그만큼 갈린다. 같은 표에 놓으면
      총수익만 보고 «주간이 낫다» 로 읽게 된다.
    """
    g = {}
    for x in items:
        g.setdefault(x.get("reb") or noreb_of(x), []).append(x)
    out = []
    for k in REB_ORDER + NOREB_ORDER:
        if g.get(k):
            out.append((k, REB_KO.get(k, k), sorted(g[k], key=lambda z: -(z.get("t") or -99))))
    for k, v in g.items():                      # 표에 없는 칸이 생기면 맨 뒤에 그대로 싣는다
        if k not in REB_ORDER and k not in NOREB_ORDER:
            out.append((k, str(k), sorted(v, key=lambda z: -(z.get("t") or -99))))
    return out


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


def idx_cagr(cc, key):
    """그 전략의 **자기 창**에서 지수 CAGR. chart.idx 의 NAV 를 쓴다.

    🚨 사용자 요청 2026-09-21 「bm 에 S&P 랑 나스닥 둘다 넣어 모든 전략에」.
    ⚠ 규칙마다 창이 다르므로 지수 CAGR 도 규칙마다 다르다 — 한 값을 전부에 쓰면 안 된다.
      (실측: 같은 'S&P 500(PR)' 라벨인데 원천의 BM CAGR 이 15가지였다.)
    ⚠ 이것은 **참고 열**이다. 초과%p 는 그 규칙에 배정된 대조군 대비로 그대로 둔다 —
      판정의 근거를 화면에서 바꾸지 않는다(거장겹침은 같은 풀 동일가중, 페어는 현금이다).
    """
    v = ((cc or {}).get("idx") or {}).get(key) or []
    d = (cc or {}).get("dates") or []
    if len(v) < 24 or len(d) < 24 or not v[0]:
        return None
    try:
        y0, y1 = int(str(d[0])[:4]), int(str(d[-1])[:4])
        m0, m1 = int(str(d[0])[5:7]), int(str(d[-1])[5:7])
        yrs = ((y1 - y0) * 12 + (m1 - m0)) / 12.0
        if yrs <= 0:
            return None
        return ((v[-1] / v[0]) ** (1.0 / yrs) - 1.0) * 100
    except Exception:
        return None


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
    # 🚨 2026-09-21 — 랩 **전 전략**으로 넓혔다(사용자 요청 «연1회도 이어붙이고 아래
    #   이어서 타이밍 오버레이 등 이어서 붙여»). 종전에는 10종목 판 66종뿐이었다.
    items = list(idx.get("items") or [])

    # ── «· 밴드 보유» 짝 정리 ────────────────────────────────────────────
    # 🚨 사용자 요청 2026-09-21 「밴드 보유랑 아닌데 이름 같은 전략은 하나로, 더 나은 쪽으로」.
    #   ⚠ **성적으로 고르지 않는다.** 그것은 2026-08-29 에 폐기한 nsel(성적을 보고
    #     손잡이를 고르던 절차)과 같은 일이다. 대신 그 변형의 **설계 목적**으로 고른다 —
    #     밴드(히스테리시스)는 «회전을 줄이려고» 붙인 것이고(tech_backtest: 저회전 변형),
    #     목적이 달성됐으면 그것을 남긴다.
    #   실측 2026-09-21: **12쌍 전부 회전이 줄었다**(예: 복권형 MAX 28.0 → 20.9배).
    #     t 는 8/12 에서 올랐고 내려간 넷은 전부 이미 0 언저리이거나 음수다.
    #     즉 이 기준으로 고르면 «더 나은 쪽»과 대체로 같지만, 고른 근거는 성적이 아니다.
    #   🚨 랩에는 **둘 다 남는다.** 여기서 빼는 것은 이 리포트 한 벌뿐이고,
    #     strategy_index·explorer 는 그대로다 — 측정 기록을 지우지 않는다.
    #   🚨 2026-09-21 — 그런데 **측정 품질이 회전보다 먼저다.** 한쪽에만 시점정확(PIT)
    #     레그가 있으면 그쪽을 남긴다. 실측으로 9쌍 중 8쌍은 둘 다 PIT 가 있어 상관없었지만,
    #     투자의견 리비전 드리프트(21일)만 **원 규칙에 PIT 가 있고 밴드판에 없었다.**
    #     처음 쓴 규칙은 그 쌍에서 소급 성적만 남은 밴드판을 남기고 PIT 판을 버렸다 —
    #     소급 샤프 0.788 이 PIT 0.690 보다 좋아 보이는 것은 생존편향이다.
    SUF = " · 밴드 보유"
    BYN = {x.get("name"): x for x in items}
    drop = set()
    for x in items:
        nm = x.get("name") or ""
        if nm.endswith(SUF):
            continue                              # 짝 판단은 원 규칙 쪽에서 한 번만 한다
        band = BYN.get(nm + SUF)
        if band is None:
            continue                              # 짝이 없다
        if x.get("pit") and not band.get("pit"):
            drop.add(band["name"])                # PIT 가 있는 원 규칙을 남긴다
        else:
            drop.add(nm)                          # 밴드판을 남긴다(회전 감축 목적 달성)
    dropped = [x for x in items if x.get("name") in drop]
    items = [x for x in items if x.get("name") not in drop]

    items.sort(key=lambda z: -(z.get("t") if z.get("t") is not None else -99))
    return idx, items, ch, mono, dropped


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
    cc_ = ch.get(x["sid"]) or {}          # 곡선·지수 — 표에서도 쓰므로 앞에서 잡는다

    y = top
    # ⚠ 제목이 길면 오른쪽 정보줄(ha=right) 아래로 파고든다. 글자수로 먼저 줄이고,
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
    # 두 지수를 그 규칙의 자기 창으로 같이 싣는다(사용자 요청 2026-09-21).
    _sp, _nd = idx_cagr(cc_, "S&P 500"), idx_cagr(cc_, "NASDAQ 100")
    rows = [
        ["CAGR %", num(m.get("cagr")), num(b.get("cagr")), num(x.get("excess_cagr"), 2, True)],
        ["  S&P 500 / NDX", "%s / %s" % (num(_sp, 1), num(_nd, 1)), "—", "—"],
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
        # ⚠ «S&P/NDX» 줄이 1행에 끼면서 아래가 한 칸씩 밀렸다.
        #   0 CAGR · 1 지수 · 2 변동성 · 3 샤프 · 4 MDD · 5 t · 6 비용후 · 7 이긴달
        if c == 1 and r in (0, 3, 5, 6) and v != "—":
            return POS if not v.startswith("-") else NEG
        if c == 1 and r == 1:
            return MUTED                     # 지수 줄은 전략 성적이 아니다
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
        # 두 지수를 같이 그린다(사용자 요청 2026-09-21) — 배정된 대조군이 지수가 아닌
        #   규칙(거장겹침·페어)도 지수 대비 위치를 볼 수 있어야 한다.
        _ix = cc_.get("idx") or {}
        for _k, _c, _ls in (("S&P 500", BM1, "--"), ("NASDAQ 100", BM2, ":")):
            _v = _ix.get(_k)
            if _v and len(_v) == len(nav):
                ax.plot(xi, _v, color=_c, lw=.9, ls=_ls, label=_k)
        # 배정된 대조군이 지수와 다르면 그것도 그린다(같은 풀 동일가중·현금 등).
        if bn and len(bn) == len(nav) and not (x.get("bench_label") or "").startswith("S&P"):
            ax.plot(xi, bn, color=MUTED, lw=.9, ls="-.",
                    label=cut(x.get("bench_label") or "대조군", 14))
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
    tks = h.get("tickers") or []
    # ⚠ 랩 전체로 넓히면서 10종이 아닌 규칙이 들어온다 — 실제 수를 적는다.
    _n = h.get("n") or len(tks)
    ST.tx(fig, X0, yp, "지금 담는 %s" % ("%d종목" % _n if _n else "것"),
          fontsize=9.0, weight="bold")
    ST.tx(fig, X0 + .140, yp, "기준 %s%s" % (h.get("as_of") or "—",
          "  (앞 10개만)" if len(tks) > 10 else ""), fontsize=6.4, color=MUTED)
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
          "여두 전략 랩 · 리밸런스 주기별 총람 · 지수는 규칙마다 자기 창으로 다시 잰 값 "
          "(S&P 500 PR · NASDAQ 100 PR) · 기준 %s" % as_of,
          fontsize=6.4, color=MUTED)
    ST.tx(fig, X0, .0175,
          "!! 구획을 넘어 세로로 비교하지 말 것 - 창·대조군·회전이 규칙마다 다르다. "
          "초과%p 는 그 규칙에 **배정된** 대조군 대비이고 S&P 가 아닌 것이 17종 있다(이름 끝 표시).",
          fontsize=6.0, color=NEG)
    ST.tx(fig, X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def main() -> int:
    idx, items, ch, mono, dropped = load()
    if not items:
        raise SystemExit("10종목 전략을 못 찾았다 — 먼저 build/strategy_index.py")
    as_of = idx.get("as_of") or "—"
    if dropped:
        print("  밴드 짝 정리 — %d종을 뺐다:" % len(dropped))
        for x in dropped:
            band = (x.get("name") or "").endswith(" · 밴드 보유")
            print("    · %-40s %s" % (x["name"][:40],
                  "밴드판을 뺐다 — 원 규칙에만 PIT 레그가 있다(측정 품질 우선)" if band
                  else "원 규칙을 뺐다 — 밴드판이 회전을 줄였다"))

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
    # 🚨 사용자 요청 2026-09-21 「주간 월간 분기 등 기간별로 전략은 분리해줘」.
    #   주기별로 가르고 본문은 **주기마다 새 쪽**에서 시작한다. 섞어 놓으면 회전이
    #   10배 다른 규칙이 한 표에 서서 총수익만 보고 비교하게 된다.
    G = by_reb(items)
    nblk = sum((len(v) + per - 1) // per for _k, _lab, v in G)

    # ── 요약 쪽 짜기 — 구획이 쪽을 넘어가면 «(이어서)» 로 잇는다 ──────────
    ROW_H, Y_TOP0, Y_TOPN, Y_END = .0110, .903, .944, .086
    seg = []                                  # (gk, glab, 부분, 이어짐?)
    for gk, glab, gv in G:
        i = 0
        while i < len(gv):
            seg.append([gk, glab, gv, i, i > 0])
            i += 1                            # 자리는 아래에서 다시 센다
    pages, cur, y_avail, first = [], [], Y_TOP0 - Y_END, True
    for gk, glab, gv in G:
        rest, cont = gv, False
        while rest:
            room = int((y_avail - .0130 - ROW_H) / ROW_H)   # 구획제목 + 표머리글
            if room < 3:
                pages.append(cur); cur = []
                y_avail = Y_TOPN - Y_END; first = False
                room = int((y_avail - .0130 - ROW_H) / ROW_H)
            take, rest = rest[:room], rest[room:]
            cur.append((gk, glab, take, cont, len(gv)))
            y_avail -= .0130 + ROW_H * (len(take) + 1) + .0130
            cont = True
    if cur:
        pages.append(cur)
    nsum = len(pages)
    total = nsum + nblk
    print("전략 %d종 — %s"
          % (len(items), " · ".join("%s %d" % (lab, len(v)) for _k, lab, v in G)))
    print("요약 %d쪽 + 본문 %d쪽 = %d쪽" % (nsum, nblk, total))

    W = [.268, .062, .062, .062, .066, .058, .064, .058, .064, .060]
    HD = ["전략", "CAGR%", "S&P%", "NDX%", "초과%p", "t", "샤프", "회전", "단조%", "팩터t"]

    with PdfPages(OUT) as pdf:
        # ── 요약 ────────────────────────────────────────────────────────
        for pi, blocks in enumerate(pages):
            fig = ST.new_page()
            if pi == 0:
                y = .958
                ST.tx(fig, X0, y, "여두 전략 랩 — 주기별 총람", fontsize=23, weight="bold")
                ST.tx(fig, X0, y - .034,
                      "리밸런스 주기로 나눠 싣는다 - 주기가 없는 것은 성격으로. 구획 안에서는 t 순",
                      fontsize=10, color=ACC)
                ST.tx(fig, X1, y - .030, "%d종 · 기준 %s" % (len(items), as_of),
                      fontsize=8.5, color=MUTED, ha="right")
                ST.hline(fig, X0, X1, y - .046, RULE, .9)
                y = Y_TOP0
            else:
                y = Y_TOPN
            for gk, glab, part, cont, gn in blocks:
                trn = [z.get("turnover") for z in part if z.get("turnover") is not None]
                ST.tx(fig, X0, y, "%s  %d종%s" % (glab, gn, " (이어서)" if cont else ""),
                      fontsize=10.5, weight="bold")
                if trn:
                    ST.tx(fig, X0 + .120, y, "회전 연 %.1f~%.1f회" % (min(trn), max(trn)),
                          fontsize=6.5, color=MUTED)
                if not cont:
                    ST.tx(fig, X1, y, cut(REB_NOTE.get(gk, ""), 58), fontsize=6.3,
                          color=MUTED, ha="right")
                y -= .0130
                rows = []
                for x in part:
                    m = x.get("metrics") or {}
                    cc_ = ch.get(x["sid"]) or {}
                    mo = mono.get(x["sid"]) or {}
                    # 🚨 초과가 없는 규칙이 많다 — 이 랩은 **시점정확 레그가 있을 때만**
                    #   초과를 싣기 때문이다(소급 초과는 생존편향이라 안 옮긴다).
                    #   그래서 CAGR 과 두 지수를 왼쪽에 같이 둔다. 빈칸이 «0» 으로 읽히면 안 된다.
                    # ⚠ 배정된 대조군이 S&P 가 아닌 규칙은 이름 끝에 표시한다 —
                    #   그 줄의 초과%p 는 S&P 대비가 아니다.
                    _bl = x.get("bench_label") or ""
                    _tag = ("" if _bl.startswith("S&P") else
                            (" [동일가중]" if "동일가중" in _bl else
                             (" [현금]" if "현금" in _bl else
                              (" [NDX]" if "NASDAQ" in _bl else " [*]"))))
                    rows.append([cut(x.get("name"), 30) + _tag,
                                 num(m.get("cagr"), 1),
                                 num(idx_cagr(cc_, "S&P 500"), 1),
                                 num(idx_cagr(cc_, "NASDAQ 100"), 1),
                                 num(x.get("excess_cagr"), 1, True), num(x.get("t")),
                                 num(m.get("sharpe"), 3), num(x.get("turnover"), 1),
                                 num(mo.get("mono_pct"), 1) if mo else "—",
                                 num(mo.get("ls_t")) if mo else "—"])

                def cs(r, c, rows=rows):
                    if c == 0:
                        return INK
                    v = rows[r][c]
                    if c in (2, 3):
                        return MUTED                      # 지수는 눌러 둔다
                    if c in (4, 5, 9) and v != "—":
                        return POS if not v.startswith("-") else NEG
                    return INK if c in (1, 6) else MUTED
                y = ST.table(fig, X0, y, W, HD, rows, row_h=ROW_H, fs=6.4, hfs=6.0,
                             zebra=True, aligns=["l"] + ["r"] * 9, cell_color=cs)
                y -= .0130
            if pi == nsum - 1:
                ST.tx(fig, X0, y,
                      "단조% = 매월 점수 5분위로 갈라 Q1<=Q2<=..<=Q5 로 줄이 선 달의 비율이다"
                      "(무작위면 0.83%). 높을수록 점수가 «전체를 줄 세운다». "
                      "팩터t = Q5-Q1 의 t - 양 끝 차이의 세기.",
                      fontsize=6.3, color=MUTED)
                ST.tx(fig, X0, y - .0110,
                      "초과%p 빈칸은 0 이 아니라 **안 실었다**는 뜻이다 - 이 랩은 시점정확(PIT) "
                      "레그가 있을 때만 초과를 싣는다(소급 초과는 생존편향이라 안 옮긴다). "
                      "그래서 CAGR·BM 을 왼쪽에 같이 뒀다.",
                      fontsize=6.3, color=MUTED)
                ST.tx(fig, X0, y - .0220,
                      "!! BM 은 넷이다 - S&P 500(PR) 184 · 같은 풀 동일가중 10(거장겹침) · "
                      "현금 6(달러중립 페어) · NDX 1. 같은 라벨이어도 규칙마다 창이 달라 BM CAGR 이 "
                      "15가지다. 구획·BM 을 넘어 세로로 비교하지 말 것.",
                      fontsize=6.3, color=NEG)
            footer(fig, pi + 1, total, as_of)
            pdf.savefig(fig)
            if "--png" in sys.argv and pi == 0:
                fig.savefig(os.path.join(DATA, "_top10_summary.png"), dpi=110, facecolor=PAPER)
            ST.plt.close(fig)

        # ── 본문 ────────────────────────────────────────────────────────
        pg = nsum
        for gk, glab, gv in G:
            for bi in range((len(gv) + per - 1) // per):
                fig = ST.new_page()
                for k, top in enumerate(BLOCK_TOPS):
                    j = bi * per + k
                    if j >= len(gv):
                        break
                    draw_block(fig, top, gv[j], ch, mono)
                    if k == 0 and j + 1 < len(gv):
                        ST.hline(fig, X0, X1, .524, LINE, .6)
                # 구획 꼬리표 — 이 쪽이 어느 주기인지 종이에서 바로 보이게 한다.
                ST.tx(fig, X1, .9765, "%s · %d종 중 %d~%d"
                      % (glab, len(gv), bi * per + 1, min((bi + 1) * per, len(gv))),
                      fontsize=7.4, color=ACC, ha="right", weight="bold")
                pg += 1
                footer(fig, pg, total, as_of)
                pdf.savefig(fig)
                # ⚠ 눈으로 확인할 쪽만 PNG 로도 남긴다 — 넘침·겹침은 수로 못 잡고 봐야 잡힌다.
                #   (스타일 리포트가 각주 길이를 «그려서 재고» 줄인 것과 같은 취지다.)
                if "--png" in sys.argv and pg == nsum + 1:
                    fig.savefig(os.path.join(DATA, "_top10_body.png"), dpi=110,
                                facecolor=PAPER)
                ST.plt.close(fig)

    print("→ %s (%.1fMB)" % (OUT, os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
