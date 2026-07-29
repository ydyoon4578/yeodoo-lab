# -*- coding: utf-8 -*-
"""build/style_plus_pdf.py — 스타일 8종 전략 PDF → data/style_strategies_8factors.pdf

무엇을. build/style_top_pdf.py 가 여섯 스타일을 과거로 되돌려 재는 문서라면, 여기서는
build/style_top.py 의 스타일 중 **백테스트가 성립하는 여덟**을 같은 자로 잰다.
판형·색·표·지표·대조군·백테스트는 style_top_pdf 를 그대로 import 해서 쓴다.

  여섯은 그대로   모멘텀 · 퀄리티 · 가치(S&P) · 저변동 · 성장(S&P) · 고베타
  둘을 더한다     배당성장 · 순수가치

  🚨 **중소형·순수성장은 싣지 않는다.** 처음엔 열로 만들었다가 감사에서 걷어냈다.
    중소형 — 시총을 '조정종가 x 공시주식수'로 만들면 기준이 어긋나 종목별로 최대 1000배
      틀린다(ECHO 는 주식수가 289.01 과 0.29 를 오간다). '가장 작은 시총을 고른다'는 규칙은
      그 오류를 정확히 골라낸다. _mcap 을 벤더 기준으로 고쳐도 PIT 로 재구성하면
      +94.77% → +24.01% · 샤프 3.07 → 1.08(SPX 1.25 미만)이라 남길 것이 없다.
    순수성장 — 바스켓이 100종목에 못 미쳐 backtest 의 MIN_NAMES 게이트에 걸린다.
      12번 중 9번 리밸런스가 조용히 생략됐고, 그 +2.34%는 성과가 아니라 생략의 결과였다.

규칙·구간·대조군은 여섯짜리 문서와 같다(상위 10종목 동일가중 · 월말 리밸런스 ·
최근 252거래일 · S&P 500(PR)·NASDAQ 100(PR) · 비용 0). 같은 자를 써야 두 문서를
나란히 놓을 수 있다.

## 더한 넷의 시점 규약 — 여기가 이 파일의 전부다

  순수가치
            S&P U.S. Style 의 바스켓 규칙(문서 p6~p9)을 그 시점 값으로 다시 돌린다 —
            성장랭크÷가치랭크로 세우고, 시총 누적 33% 안에서 점수가 평균+0.25 를
            넘는 것만 남긴다. 랭크·평균·시총이 전부 그 시점 것이라야 한다.
  배당성장  연간 주당배당 5년(연속) · 분할보정 · 감배 0회 · 한 해 2배 초과 급증 제외.
            정의는 style_top.py 와 같다.
            🚨 **연간 재무는 45일이 아니라 90일 지연을 쓴다.** 10-K 는 대형 신속제출자도
              마감이 회계연도 종료 후 60일이다. 45일로 잡으면 아직 공시되지 않은 연간
              배당을 그 달에 이미 아는 것이 된다 — 랩의 다른 곳이 45일을 쓰는 것은
              분기(10-Q, 마감 40일) 기준이라 그대로 가져오면 안 된다.

  python build/style_plus_pdf.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

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
OUT = os.path.join(DATA, "style_strategies_8factors.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST          # 판형·색·표·지표·대조군·백테스트를 그대로 쓴다

zs, zavg, TOPN = ST.zs, ST.zavg, ST.TOPN
SP_WP = ST.SP_WP

BASKET = 0.33          # 성장·가치 바스켓은 각각 시가총액 33%까지(S&P 정본 p6)
PURE_MIN = 0.25        # '순수'는 점수가 전체 평균 + 0.25 를 넘어야 한다(정본 p9)
ANN_LAG = 90           # 연간 재무 공시 지연(10-K 마감 60일 + 여유). 분기용 45일과 다르다
DIVG_YEARS = 5
DIVG_SPLIT = 1.5
DIVG_SPLIT_TOL = .4
DIVG_JUMP = 2.0


# ── 연간 버킷 ────────────────────────────────────────────────────────────────
# style_top_pdf.Panel 은 tech_backtest.load_fund() 를 쓰는데 그쪽은 i·q(시점·분기)만 읽는다.
# 배당성장은 연간(a) 이 필요해 여기서 직접 읽는다 — 분기로 읽으면 회사마다 분기값과 연
# 누적값이 섞여 성장률이 튄다(build/style_top.py 의 같은 주석 참조).
_ANN: dict[str, dict[str, list]] = {}


def _load_ann():
    if _ANN:
        return
    d = os.path.join(DATA, "fx")
    if not os.path.isdir(d):
        return
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            j = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        except Exception:
            continue
        tags = j.get("tags") or {}
        rec = {}
        for k in ("dps", "sh"):
            rows = ((tags.get(k) or {}).get("a") or [])
            rec[k] = [(e, float(v)) for e, v in rows
                      if v is not None and isinstance(v, (int, float)) and float(v) > 0]
        if rec.get("dps"):
            _ANN[j.get("t") or fn[:-5]] = rec


def ann_asof(t, key, date):
    """기간종료일 + ANN_LAG 이 date 이전인 연간 관측 → {연도: 값}."""
    cut = (dt.date.fromisoformat(date) - dt.timedelta(days=ANN_LAG)).isoformat()
    return {e[:4]: v for e, v in (_ANN.get(t) or {}).get(key, []) if e <= cut}


def divg_split_adjust(win, dps, sh):
    """연도 목록(오래된→최신)의 주당배당을 분할만 되돌린다.

    분할 판별은 style_top.py 와 같다 — 주식수가 r 배 되는 **동시에** 주당배당이 1/r 배가
    된 경우만. 주식수만 보면 VICI 의 인수 증자(1.52배)를 분할로 오인해 과거 배당을
    깎고 성장률을 6%→18% 로 부풀린다.
    """
    raw = [dps[y] for y in win]
    adj, f = list(raw), 1.0
    for i in range(len(win) - 1, 0, -1):
        a, b = win[i - 1], win[i]
        if a in sh and b in sh and sh[a] > 0 and raw[i - 1] > 0:
            r = sh[b] / sh[a]
            if (r > DIVG_SPLIT or r < 1 / DIVG_SPLIT) and abs(raw[i] / raw[i - 1] * r - 1.0) < DIVG_SPLIT_TOL:
                f *= r
        adj[i - 1] = raw[i - 1] / f
    return adj


def divg_ever_cut(t, date):
    """그 시점에 **볼 수 있는 연간 이력 전체**(최대 8년)에 감배가 있었나.

    🚨 5년 창 안만 보면 안 된다. 원지수가 20년을 요구하는 이유가 이것이다 —
      WFC 는 2019 1.92 → 2020 1.22 → 2021 0.60 으로 잘랐는데, 그 감배가 창(2021~2025)
      **바로 밖**이라 5년만 보면 '5년 연속 증배'로 보인다. 회복 첫 해 0.60→1.10 은
      1.83배라 급증 문턱(2.0)도 아슬하게 피한다. 문턱을 만지는 대신 이력을 더 본다.
    ⚠ 관측이 빠진 해가 있으면 그 구간 안은 못 본다 — 인접 관측끼리만 비교한다.
    """
    dps, sh = ann_asof(t, "dps", date), ann_asof(t, "sh", date)
    ys = sorted(dps)
    if len(ys) < 2:
        return False
    a = divg_split_adjust(ys, dps, sh)
    return any(a[i] < a[i - 1] * .999 for i in range(1, len(a)))


def divg_window(t, date):
    """date 시점에 알 수 있는 최신 5개 **연속** 회계연도의 분할보정 주당배당.

    분할 판별은 style_top.py 와 같다 — 주식수가 r 배 되는 **동시에** 주당배당이 1/r 배가
    된 경우만. 주식수만 보면 VICI 의 인수 증자(1.52배)를 분할로 오인해 과거 배당을
    깎고 성장률을 6%→18% 로 부풀린다.
    """
    dps, sh = ann_asof(t, "dps", date), ann_asof(t, "sh", date)
    ys = sorted(dps, reverse=True)
    if len(ys) < DIVG_YEARS:
        return None
    win = sorted(ys[:DIVG_YEARS])
    if int(win[-1]) - int(win[0]) != DIVG_YEARS - 1:
        return None
    return divg_split_adjust(win, dps, sh)


# ── 더한 넷의 점수 ───────────────────────────────────────────────────────────
def sc_divg(P, i):
    """배당성장 — 5년 연속 무감배 종목을 배당성장률·배당수익률의 z 평균으로."""
    _load_ann()
    date = P.dates[i]
    bad = _scale_bad(P)
    cagr, dy = {}, {}
    for t in P.uni:
        if t in bad:
            continue          # 주당배당(공시 기준)과 종가(조정)의 기준이 어긋난 종목
        adj = divg_window(t, date)
        if adj is None:
            continue
        if any(adj[k] < adj[k - 1] * .999 for k in range(1, len(adj))):
            continue                                   # 창 안의 감배
        if divg_ever_cut(t, date):
            continue                                   # 창 밖의 감배 (WFC 형)
        if any(adj[k] > adj[k - 1] * DIVG_JUMP for k in range(1, len(adj))):
            continue                                   # 감배 후 복원·신규 개시
        a = P.px.get(t)
        if a is None or np.isnan(a[i]) or a[i] <= 0:
            continue
        cagr[t] = (adj[-1] / adj[0]) ** (1 / (len(adj) - 1)) - 1
        dy[t] = adj[-1] / float(a[i]) * 100
    # ⚠ 윈저화는 **2.5퍼센타일**이다. style_top.py 의 zs(wp=None) 은 기본값 WINSOR_P=2.5 로
    #   떨어지지 S&P 계열의 10 이 아니다. 10 으로 자르면 성장 상위가 통째로 동점이 되어
    #   순위가 배당수익률만으로 갈린다(실측: WFC·DPZ 가 빠지고 COP·HPQ 가 올라왔다).
    #   두 문서가 같은 종목을 가리켜야 대조가 된다.
    return zavg([zs(cagr, ST.MSCI_WP), zs(dy, ST.MSCI_WP)])


_BAD: set = set()
_BAD_DONE = [False]


def _scale_bad(P):
    """scale_broken 을 한 번만 세어 캐시한다 — 유니버스는 창 내내 같다."""
    if not _BAD_DONE[0]:
        _BAD.update(scale_broken(P))
        _BAD_DONE[0] = True
    return _BAD


def scale_broken(P):
    """주식수와 종가의 분할 기준이 어긋난 종목 — 후보에서 뺀다.

    🚨 `그 시점 종가 x 공시 주식수` 로 시총을 만들면 안 된다. P.px 는 **소급 분할보정된**
      종가인데 fx 의 주식수는 **공시 당시 그대로**라 기준이 다르다. 실측(2026-07-28,
      495종목): 벤더 fund.mc 대비 KLAC 0.10배 · CRWD 0.25배 · WAT 836배.
      게다가 fx 의 주식수는 한 종목 안에서 단위가 뒤집히기도 한다 —
      ECHO 는 289.01 과 0.29 를, WAT 은 82139.0 과 59.76 을 오간다.
      '가장 작은 시총을 고른다'는 규칙은 이 오류를 정확히 골라낸다(그래서 샤프 3.07 이 났다).
    → 시총 자체는 아래 _mcap 이 벤더 값을 기준으로 만들고, 여기서는 **주당배당처럼
      공시 기준 값을 종가와 함께 쓰는 곳**을 위해 어긋난 종목을 걸러낸다.
    """
    bad = set()
    for t in P.uni:
        a, mc = P.px.get(t), (P.uni[t].get("fund") or {}).get("mc")
        sh = P.last(t, "sh", len(P.dates) - 1)
        if a is None or np.isnan(a[-1]) or a[-1] <= 0 or not mc or not sh or sh <= 0:
            bad.add(t)
            continue
        r = (float(a[-1]) * sh / 100.0) / mc           # 백만$ → 억$
        if not (.8 <= r <= 1.25):
            bad.add(t)
    return bad


def _mcap(P, i):
    """그 시점 시가총액(억$) — **벤더 fund.mc 를 조정종가 비율로 되돌린다.**

    px 가 전 구간 같은 기준으로 조정돼 있으므로 mc_t = mc_today x px_t / px_today 는
    분할과 무관하게 성립한다. 자사주 매입·증자로 인한 주식수 변화는 반영되지 않지만,
    최근 1년 창에서 그 오차는 몇 % 이고 공시 주식수를 쓰다 1000배 틀리는 것보다 낫다.
    """
    out = {}
    for t in P.uni:
        a, mc = P.px.get(t), (P.uni[t].get("fund") or {}).get("mc")
        if a is None or not mc or np.isnan(a[i]) or a[i] <= 0 or np.isnan(a[-1]) or a[-1] <= 0:
            continue
        out[t] = float(mc) * float(a[i]) / float(a[-1])
    return out


def _pure(P, i):
    """그 시점의 (성장랭크÷가치랭크, 순수성장 집합, 순수가치 집합, 성장z, 가치z, 시총)."""
    g, _gu = ST.sc_grow(P, i)
    v, _vu = ST.sc_val(P, i)
    common = sorted(set(g) & set(v))
    if len(common) < 50:
        return {}, [], [], g, v, {}
    gr = {t: k + 1 for k, t in enumerate(sorted(common, key=lambda x: -g[x]))}
    vr = {t: k + 1 for k, t in enumerate(sorted(common, key=lambda x: -v[x]))}
    ratio = {t: gr[t] / vr[t] for t in common}
    order = sorted(common, key=lambda t: ratio[t])
    mcv = _mcap(P, i)
    mcv = {t: mcv.get(t, 0.0) for t in common}
    tot = sum(mcv.values()) or 1.0
    gmean = float(np.mean([g[t] for t in common]))
    vmean = float(np.mean([v[t] for t in common]))
    PG, PV, acc = [], [], 0.0
    for t in order:                                    # 위에서부터 시총 33% = 성장 바스켓
        if acc / tot >= BASKET:
            break
        acc += mcv[t]
        if g[t] > gmean + PURE_MIN:
            PG.append(t)
    acc = 0.0
    for t in reversed(order):                          # 아래에서부터 시총 33% = 가치 바스켓
        if acc / tot >= BASKET:
            break
        acc += mcv[t]
        if v[t] > vmean + PURE_MIN:
            PV.append(t)
    return ratio, PG, PV, g, v, mcv


def sc_pureval(P, i):
    ratio, _PG, PV, _g, _v, _m = _pure(P, i)
    d = {t: ratio[t] for t in PV}                      # 비율이 클수록 순수가치
    return d, dict(d)


# ── 보유 표 마지막 칸 ────────────────────────────────────────────────────────
def d_divg(P, i, t, sc, un):
    _load_ann()
    adj = divg_window(t, P.dates[i])
    if not adj or adj[0] <= 0:
        return "—"
    return "%.1f" % (((adj[-1] / adj[0]) ** (1 / (len(adj) - 1)) - 1) * 100)


def d_ratio(P, i, t, sc, un):
    return "%.2f" % abs(sc)


STYLES10 = list(ST.STYLES) + [
    # 참조 지수 이름은 요약표에서 " (" 앞까지만 쓴다(draw_summary 규약) — 원명 그대로 두면
    # 35자라 수익률 칸을 침범한다. 전략별 쪽에는 괄호까지 전부 나온다.
    ("divg", "배당성장", "S&P Dividend Aristocrats (High Yield)", sc_divg, "배당성장률 %", d_divg,
     "연간 주당배당이 5년 연속 회계연도에 줄지 않은 종목을 배당성장률과 배당수익률의 z 평균으로 세운다.\n"
     "원지수는 20년 연속 증배가 조건이라 이것은 5년 대용이다 — 창 밖의 감배가 안 보이므로 한 해 2배 초과 급증은 제외한다."),
    ("pureval", "순수가치", "S&P 500 Pure Value", sc_pureval, "성장랭크÷가치랭크", d_ratio,
     "성장랭크÷가치랭크가 가장 큰 쪽(가치는 높고 성장은 낮은 종목) 중 시총 누적 33% 바스켓 안에서\n"
     "가치점수가 평균+0.25 를 넘는 것만. 순수성장의 반대쪽 끝이라 둘은 겹치지 않는다."),
]


def footer(fig, page, total):
    ST.hline(fig, ST.X0, ST.X1, .034, ST.LINE, .6)
    ST.tx(fig, ST.X0, .026,
          "스타일 8종 전략 · 지수 SPX = S&P 500 단독 · NDX = NASDAQ 100 단독 · 공통 = 양쪽 · "
          "대조군은 가격지수(PR) · 비용 0 · 연간 재무는 90일 지연",
          fontsize=6.2, color=ST.MUTED)
    ST.tx(fig, ST.X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=ST.MUTED, ha="right")


def main() -> int:
    print("가격·재무 패널을 연다…")
    P = ST.Panel()
    _load_ann()
    print("  연간 버킷 %d종목" % len(_ANN))
    ST.STYLES = STYLES10
    ST.footer = footer
    ST.TITLE = "스타일 8종 전략"
    ST.SUBTITLE = "최근 1년 요약 · 백테스트가 성립하는 여덟 가지"
    ST.SCOL = dict(ST.SCOL)
    ST.SCOL.update({"divg": ST.POS, "pureval": "#7A4B3B"})
    miss = [k for k, *_ in STYLES10 if k not in ST.SCOL]
    if miss:
        raise SystemExit("곡선 색이 없는 전략: %s" % miss)

    res, order = {}, []
    for S in STYLES10:
        R = ST.backtest(P, S[3])
        if not R:
            print("  건너뜀 %s — 후보가 얕아 상위 10을 못 채운 달이 많다" % S[1])
            continue
        res[S[0]] = R
        order.append(S[0])
        m = ST.metrics(R["nav"])
        wg, n_ = ST.win_rate(R["nav"], ST.bench_nav(P, P.gspc, R["start"], R["end"]),
                             P.dates, R["start"])
        wn, _ = ST.win_rate(R["nav"], ST.bench_nav(P, P.ndx, R["start"], R["end"]),
                            P.dates, R["start"])
        print("  %-5s 1년 %+8.2f%% · 샤프 %5.2f · MDD %7.2f%% · 이긴 달 %d/%d·%d/%d"
              % (S[1], m["ret"], m["sharpe"], m["mdd"], wg, n_, wn, n_))
    if not res:
        raise SystemExit("돌아간 전략이 없다 — 입력 패널을 확인할 것.")
    order.sort(key=lambda k: -(ST.metrics(res[k]["nav"])["ret"] or -1e9))
    total = 1 + (len(order) + 1) // 2

    with PdfPages(OUT) as pdf:
        fig = ST.new_page(); ST.draw_summary(fig, P, res, order, total)
        pdf.savefig(fig, facecolor=ST.PAPER); plt.close(fig)
        page = 2
        for i in range(0, len(order), 2):
            fig = ST.new_page()
            for k, key in enumerate(order[i:i + 2]):
                S = next(s for s in STYLES10 if s[0] == key)
                ST.draw_block(fig, P, ST.BLOCK_TOPS[k], S[:7], res[key])
            footer(fig, page, total)
            pdf.savefig(fig, facecolor=ST.PAPER); plt.close(fig)
            page += 1

    print("→ %s · %d쪽 · %dKB" % (OUT, total, os.path.getsize(OUT) // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
