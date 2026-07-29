# -*- coding: utf-8 -*-
"""build/factor_plus_pdf.py — 강화 팩터 전략 → data/factor_plus.pdf

무엇을. build/style_top_pdf.py 의 스타일 6종(모멘텀·퀄리티·가치·저변동·성장·고베타)을
결합·필터·게이트로 강화해 8종을 만든다. 판형·색·표·지표·대조군은 style_top_pdf 를 그대로
import 해서 쓴다 — 같은 자를 써야 두 문서를 나란히 놓을 수 있고, 한쪽만 고쳐져 조용히
달라지는 일이 없다.

  대조군   S&P 500(PR) · NASDAQ 100(PR) 둘 다 (스타일 전략과 같다)
  선정     상위 10종목 동일가중 · 월말 리밸런스 · 사이에는 표류
  구간     최근 1년(월말에서 열어 12개월) · 비용 0
  재무     기간종료일 + 45일이 지나 실제로 공시된 것만 (look-ahead 차단은 Panel 이 맡는다)

## 강화의 네 가지 방식 — 지어내지 않고 원래 팩터에서 파생한다

  ① 결합   두 팩터의 z 를 평균한다. 한쪽이 꺾일 때 다른 쪽이 받친다.
  ② 필터   후보를 먼저 거른 뒤 남은 것에서 고른다(예: 적자 기업 제외).
  ③ 게이트  가격 조건을 얹는다(예: 200일선 위인 종목만) — 가치함정·하락추세 회피.
  ④ 정규화 팩터를 위험으로 나눈다(예: 모멘텀 ÷ 변동성).

⚠ 이 8종은 **같은 표본에서 같은 유니버스로 돌린 것**이다. 규칙을 더 만들수록 그중 최고는
  우연히도 좋아 보인다. 그래서 좋은 것만 고르지 않고 8종을 전부 싣는다. 문서 어디에도
  '통과'라고 적지 않는다 — 이 문서는 성과 표시이지 판정이 아니다. 판정은 다중검정 임계를
  갖춘 build/tech_backtest.py 쪽 일이다.

  python build/factor_plus_pdf.py
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
OUT = os.path.join(DATA, "factor_plus.pdf")

sys.path.insert(0, HERE)
import style_top_pdf as ST          # 판형·색·표·지표·대조군·폰트를 그대로 쓴다

zs, zavg, TOPN = ST.zs, ST.zavg, ST.TOPN
SP_WP, MSCI_WP = ST.SP_WP, ST.MSCI_WP


# ── 원재료 ──────────────────────────────────────────────────────────────────
def _px(P, t, i):
    a = P.px.get(t)
    if a is None:
        return None
    v = a[i]
    return None if (np.isnan(v) or v <= 0) else float(v)


def raw_bp(P, i):
    """장부가 ÷ 주가 (Book-to-Price). 배포 원장의 book-to-price-spx 와 같은 정의다."""
    out = {}
    for t in P.uni:
        p, sh, eq = _px(P, t, i), P.last(t, "sh", i), P.last(t, "eq", i)
        if p and sh and sh > 0 and eq is not None:
            out[t] = (eq / sh) / p
    return out


def raw_roe(P, i):
    out = {}
    for t in P.uni:
        ni, eq = P.ttm(t, "ni", i), P.last(t, "eq", i)
        if ni is not None and eq and eq > 0:
            out[t] = ni / eq * 100
    return out


def raw_de(P, i):
    """부채비율의 부호를 뒤집은 값 — 클수록 좋다(빚이 적다)."""
    out = {}
    for t in P.uni:
        li, eq = P.last(t, "liab", i), P.last(t, "eq", i)
        if li is not None and eq and eq > 0:
            out[t] = -(li / eq * 100)
    return out


def raw_vol(P, i, win=252):
    out = {}
    for t, a in P.px.items():
        if i < win:
            continue
        w = a[i - win + 1:i + 1]
        r = w[1:] / w[:-1] - 1
        r = r[~np.isnan(r)]
        if r.size > win * .6:
            out[t] = -float(np.std(r, ddof=1)) * np.sqrt(252) * 100      # 작을수록 좋다
    return out


def gate_trend(P, i, keep):
    """200일선 위인 종목만 남긴다 — 가치·장부가 계열의 '떨어지는 칼' 회피."""
    out = {}
    for t, v in keep.items():
        a = P.px.get(t)
        if a is None or i < 200:
            continue
        w = a[i - 199:i + 1]
        w = w[~np.isnan(w)]
        if w.size < 150:
            continue
        if not np.isnan(a[i]) and a[i] > float(np.mean(w)):
            out[t] = v
    return out


def filt_profit(P, i, keep):
    """TTM 순이익이 양(+)인 종목만 — 적자 기업의 싼 장부가는 싸다는 뜻이 아니다."""
    return {t: v for t, v in keep.items()
            if (P.ttm(t, "ni", i) or 0) > 0}





def bt2(P, fn):
    """style_top_pdf.backtest 와 같은 규약(월말 리밸·상위 10 동일가중·사이 표류).

    원본과 다른 점은 pick() 을 캐시하지 않고 시간 순서대로 도는 것뿐이다.
    """
    end = len(P.dates) - 1
    # 창 시작을 월말로 맞춘다(style_top_pdf.backtest 와 같은 규약) — 부분 월을 없앤다.
    start = next((i for i in P.me if i >= max(0, end - ST.WINDOW)), max(0, end - ST.WINDOW))
    _iss = ST.iss_of(P)

    def score(i):
        sc, tie = fn(P, i)
        if len(sc) < ST.MIN_NAMES:
            return None
        ok = [t for t in sc if t in P.px and not np.isnan(P.px[t][i])]
        if not ok:
            return None
        return sc, tie, ok

    def choose(i):
        z = score(i)
        if not z:
            return None
        sc, tie, ok = z
        ok.sort(key=lambda t: (-sc[t], -tie.get(t, 0.0), t))
        seen, ded = set(), []                       # 복수 클래스는 한 칸(스타일 전략과 같은 규약)
        for t in ok:
            k = _iss.get(t, t)
            if k in seen:
                continue
            seen.add(k)
            same = [x for x in ok if _iss.get(x, x) == k]
            a_ = next((x for x in same if ST.is_class_a(P, x)), None)
            ded.append(a_ or t)
        sel = ded[:TOPN]
        if len(sel) < TOPN:
            return None
        return [(t, sc[t], tie.get(t, sc[t])) for t in sel]

    init, init_i = None, None
    for i in [j for j in P.me if j <= start][::-1][:14]:
        init = choose(i)
        if init:
            init_i = i
            break
    if not init:
        return None

    nav = np.ones(end - start + 1)
    w = {t: 1.0 / TOPN for t, _s, _u in init}
    picks, rebal = {}, [i for i in P.me if start < i < end]
    for k, i in enumerate(range(start + 1, end + 1), start=1):
        g, tot = 0.0, 0.0
        for t, x in w.items():
            a = P.px[t]
            if np.isnan(a[i]) or np.isnan(a[i - 1]) or a[i - 1] <= 0:
                continue
            g += x * (a[i] / a[i - 1]); tot += x
        nav[k] = nav[k - 1] * (g / tot if tot > 0 else 1.0)
        nw, s2 = {}, 0.0
        for t, x in w.items():
            a = P.px[t]
            r = (a[i] / a[i - 1]) if (not np.isnan(a[i]) and not np.isnan(a[i - 1])
                                      and a[i - 1] > 0) else 1.0
            nw[t] = x * r; s2 += x * r
        if s2 > 0:
            w = {t: v / s2 for t, v in nw.items()}
        if i in rebal:
            p_ = choose(i)
            if p_:
                picks[i] = p_
                w = {t: 1.0 / TOPN for t, _s, _u in p_}
    today = choose(end)
    if not today:
        return None
    prev_i = max(picks) if picks else init_i
    return {"nav": nav, "start": start, "end": end,
            "prev_i": prev_i, "prev": picks.get(prev_i) or init,
            "today_i": end, "today": today, "n_rebal": len(picks), "init_i": init_i}


# ── 강화 전략 8종 ───────────────────────────────────────────────────────────
# 스타일 팩터를 결합·필터·게이트·정규화로 강화한 것들이다.

def sc_multi5(P, i):
    """모멘텀·퀄리티·가치·성장·저변동 다섯 합성점수의 z 평균.

    고베타는 뺐다 — 초과수익 팩터가 아니라 방향성 증폭이라 섞으면 결합의 뜻이 흐려진다.
    """
    return zavg([ST.sc_mom(P, i), ST.sc_qual(P, i), ST.sc_val(P, i),
                 ST.sc_grow(P, i), zs(raw_vol(P, i), MSCI_WP)])


def sc_val_qual(P, i):
    return zavg([ST.sc_val(P, i), ST.sc_qual(P, i)])


def sc_mom_qual(P, i):
    return zavg([ST.sc_mom(P, i), ST.sc_qual(P, i)])


def sc_mom_lv(P, i):
    return zavg([ST.sc_mom(P, i), zs(raw_vol(P, i), MSCI_WP)])


def sc_grow_prof(P, i):
    return zavg([ST.sc_grow(P, i), zs(raw_roe(P, i), MSCI_WP)])


def sc_lv_qual(P, i):
    return zavg([zs(raw_vol(P, i), MSCI_WP), ST.sc_qual(P, i)])


def sc_btp(P, i):
    """장부가 저평가 + 흑자 필터 + 추세 게이트 — 가치함정을 두 겹으로 막는다."""
    return zs(gate_trend(P, i, filt_profit(P, i, raw_bp(P, i))), SP_WP)


def sc_agg(P, i):
    return zavg([ST.sc_mom(P, i), ST.sc_grow(P, i), ST.sc_hbeta(P, i)])


def m_z(P, i, t, sc, un):
    return "%+.2f" % un


def m_roe(P, i, t, sc, un):
    v = raw_roe(P, i).get(t)
    return "%.1f" % v if v is not None else "—"


def m_vol(P, i, t, sc, un):
    v = raw_vol(P, i).get(t)
    return "%.1f" % (-v) if v is not None else "—"


def m_bp(P, i, t, sc, un):
    v = raw_bp(P, i).get(t)
    return "%.3f" % v if v is not None else "—"


# (키, 이름, 참조, 점수함수, 마지막칸 라벨, 포맷, 설명)
STRATS = [
    ("multi5", "5팩터 결합", "다중팩터 기본형", sc_multi5, "합성 z", m_z,
     "모멘텀·퀄리티·가치·성장·저변동 다섯 합성점수의 z 평균. 아래 결합들의 기준점이다 —\n"
     "둘씩 짝지은 결합이 다섯을 한꺼번에 섞는 것보다 나은지 여기에 대어 본다."),
    ("val_qual", "가치 + 퀄리티", "QARP", sc_val_qual, "PER", ST.d_val,
     "가치(B/P·E/P·S/P)와 퀄리티(ROE·D/E·이익변동성)의 z 평균. '적당한 값에 좋은 회사'.\n"
     "가치의 함정과 퀄리티의 비싼 값을 서로 상쇄시키려는 고전적 결합이다."),
    ("mom_qual", "모멘텀 + 퀄리티", "모멘텀 강화 ①", sc_mom_qual, "12M 수익률 %", ST.d_mom,
     "위험조정 모멘텀과 퀄리티의 z 평균. 추세를 타되 재무가 받치는 종목만 담는다.\n"
     "모멘텀은 국면 전환에서 한꺼번에 무너지는데, 퀄리티가 그 낙폭을 줄이는지 본다."),
    ("mom_lv", "모멘텀 ÷ 변동성", "모멘텀 강화 ②", sc_mom_lv, "변동성 %", m_vol,
     "위험조정 모멘텀과 저변동의 z 평균. 같은 추세라면 덜 흔들리는 쪽을 고른다.\n"
     "샤프를 겨냥한 결합이라 절대수익은 순수 모멘텀보다 낮게 나오기 쉽다."),
    ("grow_prof", "성장 + 수익성", "성장 강화", sc_grow_prof, "ROE %", m_roe,
     "성장(매출성장·EPS변화·모멘텀)에 ROE 를 더한 z 평균. 매출만 늘고 돈은 못 버는 성장을 걸러낸다.\n"
     "실적 추정이 꺾일 때 순수 성장보다 덜 빠지는지 본다."),
    ("lv_qual", "저변동 + 퀄리티", "방어 강화", sc_lv_qual, "변동성 %", m_vol,
     "252일 변동성(－)과 퀄리티의 z 평균. 조용한 것 중 재무가 받치는 것만 담는다.\n"
     "저변동 단독은 방어 업종에 쏠리는데, 퀄리티를 섞으면 그 쏠림이 줄어드는지 본다."),
    ("btp", "장부가 + 흑자 + 추세", "Book-to-Price 강화", sc_btp, "B/P", m_bp,
     "장부가÷주가가 큰 종목 중 TTM 순이익이 양(+)이고 200일선 위인 것만 담는다.\n"
     "적자면 자기자본이 녹는 중이라 싼 게 아니고, 하락추세면 아직 칼이 떨어지는 중이다."),
    ("agg", "공격 결합", "모멘텀+성장+고베타", sc_agg, "합성 z", m_z,
     "모멘텀·성장·고베타의 z 평균. 강세장 증폭이 목적인 규칙이라 절대수익이 아니라\n"
     "MDD 와 함께 읽어야 한다. 이 문서에서 가장 크게 빠질 수 있는 자리다."),
]


def footer(fig, page, total):
    ST.hline(fig, ST.X0, ST.X1, .034, ST.LINE, .6)
    ST.tx(fig, ST.X0, .026,
          "강화 팩터 전략 8종 · 스타일 6종을 결합·필터·게이트·정규화로 강화 · "
          "지수 SPX = S&P 500 단독 · NDX = NASDAQ 100 단독 · 공통 = 양쪽 · 대조군은 가격지수(PR) · 비용 0",
          fontsize=6.2, color=ST.MUTED)
    ST.tx(fig, ST.X1, .026, "%d / %d · %s" % (page, total, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=ST.MUTED, ha="right")


def main() -> int:
    print("가격·재무 패널을 연다…")
    P = ST.Panel()
    # 그리기 함수들이 모듈 전역 STYLES 를 본다 — 우리 목록으로 갈아 끼운다(구현은 하나만 둔다).
    ST.STYLES = STRATS
    ST.footer = footer
    ST.TITLE = "강화 팩터 전략 8종"
    ST.SUBTITLE = "스타일 6종을 결합·필터·게이트·정규화로 강화 · 최근 1년 요약"
    # 요약 쪽 곡선 색 표도 갈아 끼운다 — 원본은 스타일 6종 키만 갖고 있어 KeyError 가 난다.
    #   강화 계열은 바탕이 된 스타일 색을 물려받게 둔다 — 두 문서를 나란히 놓았을 때
    #   계열이 눈으로 이어진다.
    ST.SCOL = {
        "multi5": ST.INK2,
        "val_qual": ST.NEG, "mom_qual": ST.CHAMP, "mom_lv": "#5B8FA8",
        "grow_prof": ST.RP, "lv_qual": ST.POS, "btp": "#7A4B3B", "agg": "#B03A2E",
    }
    miss = [k for k, *_ in STRATS if k not in ST.SCOL]
    if miss:
        raise SystemExit("곡선 색이 없는 전략: %s" % miss)

    res, order = {}, []
    for S in STRATS:
        R = bt2(P, S[3])
        if not R:
            print("  건너뜀 %s — 후보가 얕아 상위 10을 못 채운 달이 많다" % S[1])
            continue
        res[S[0]] = R
        order.append(S[0])
        m = ST.metrics(R["nav"])
        print("  %-14s %s~%s · 1년 %+7.2f%% · 샤프 %5.2f · MDD %7.2f%%"
              % (S[1], P.dates[R["start"]], P.dates[R["end"]],
                 m["ret"], m["sharpe"], m["mdd"]))
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
                S = next(s for s in STRATS if s[0] == key)
                ST.draw_block(fig, P, ST.BLOCK_TOPS[k], S[:7], res[key])
            footer(fig, page, total)
            pdf.savefig(fig, facecolor=ST.PAPER); plt.close(fig)
            page += 1

    print("→ %s (%d쪽 · %dKB · 폰트 %s)" % (OUT, total, os.path.getsize(OUT) // 1024, ST.KFONT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
