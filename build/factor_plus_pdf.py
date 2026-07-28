# -*- coding: utf-8 -*-
"""build/factor_plus_pdf.py — 강화 팩터 전략 → data/factor_plus.pdf

무엇을. build/style_top_pdf.py 의 스타일 6종(모멘텀·퀄리티·가치·저변동·성장·고베타)을
결합·필터·게이트로 강화하고, 여기에 **BK(kb.html #b '전략 B')의 구조 장치 3종**을 이식해
12종을 만든다. 판형·색·표·지표·대조군은 style_top_pdf 를 그대로 import 해서 쓴다 — 같은 자를
써야 두 문서를 나란히 놓을 수 있고, 한쪽만 고쳐져 조용히 달라지는 일이 없다.

  대조군   S&P 500(PR) · NASDAQ 100(PR) 둘 다 (스타일 전략과 같다)
  선정     상위 10종목 동일가중 · 월말 리밸런스 · 사이에는 표류
  구간     최근 252거래일 · 비용 0
  재무     기간종료일 + 45일이 지나 실제로 공시된 것만 (look-ahead 차단은 Panel 이 맡는다)

## 강화의 네 가지 방식 — 지어내지 않고 원래 팩터에서 파생한다

  ① 결합   두 팩터의 z 를 평균한다. 한쪽이 꺾일 때 다른 쪽이 받친다.
  ② 필터   후보를 먼저 거른 뒤 남은 것에서 고른다(예: 적자 기업 제외).
  ③ 게이트  가격 조건을 얹는다(예: 200일선 위인 종목만) — 가치함정·하락추세 회피.
  ④ 정규화 팩터를 위험으로 나눈다(예: 모멘텀 ÷ 변동성).

⚠ 이 12종은 **같은 표본에서 같은 유니버스로 돌린 것**이다. 규칙을 더 만들수록 그중 최고는
  우연히도 좋아 보인다. 그래서 좋은 것만 고르지 않고 12종을 전부 싣는다. 문서 어디에도
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



# ── BK(전략 B) 에서 가져온 장치 ─────────────────────────────────────────────
# 출처: _build/digest_b.md — kb.html #b 탭 'MSCI China A 팩터 파이프라인'.
#   그쪽은 587개 팩터를 매 회차 재선별하는 파이프라인이고 유니버스도 다르다. 여기로 옮길 수
#   있는 것은 **학습 파라미터가 0개인 구조 장치**뿐이다. 팩터 재선별 자체는 옮기지 않았다 —
#   518종목·무료 데이터로는 587개 팩터 풀이 없고, 흉내만 내면 다중검정만 늘고 뜻은 없다.
#
#   ① 섹터 내 순위   업종별로 팩터가 역작동하는 것을 막는다(digest_b ①)
#   ② 섹터 캡        한 업종이 포트를 지배하지 못하게 — 그쪽 '스타일 캡 25%'의 섹터판(⑤)
#   ③ 선정 히스테리시스 기존 보유에 마진을 주어 교체를 억제한다(④ · 실측 턴오버 −64%)
#   ⚠ 그쪽 실측(Sharpe 0.73→0.79 등)은 중국 A주 표본의 값이다. 여기서 재현된다는 보장이 없어
#     그대로 인용하지 않는다 — 이 문서의 숫자는 이 유니버스에서 다시 잰 것이다.

SEC_CAP = 3          # 10종목 중 한 섹터 최대 3 (그쪽 스타일 캡 25%의 섹터판)
HYST = 0.5           # 교체 마진 — 신규가 기존을 이 z 만큼 넘어야 갈아탄다(그쪽 margin 0.5)


def sec_of(P, t):
    return ((P.uni.get(t) or {}).get("sector") or "?")


def sector_neutral(P, d):
    """{티커: 원시값} → 섹터 안에서 표준화한 z. 섹터당 5종목 미만이면 그 섹터는 버린다."""
    by = {}
    for t, v in d.items():
        if v is None or v != v:
            continue
        by.setdefault(sec_of(P, t), {})[t] = v
    out = {}
    for _s, grp in by.items():
        if len(grp) < 5:
            continue
        a = np.array(list(grp.values()), float)
        mu, sd = float(a.mean()), float(a.std(ddof=1))
        if sd <= 0:
            continue
        for t, v in grp.items():
            out[t] = float(np.clip((v - mu) / sd, -ST.WIN, ST.WIN))
    return out, dict(out)


def pick_capped(P, ranked, cap=SEC_CAP, n=None):
    """순위 목록에서 섹터당 cap 개를 넘지 않게 상위 n 을 고른다."""
    n = n or TOPN
    cnt, out = {}, []
    for t in ranked:
        k = sec_of(P, t)
        if cnt.get(k, 0) >= cap:
            continue
        cnt[k] = cnt.get(k, 0) + 1
        out.append(t)
        if len(out) >= n:
            break
    return out


def bt2(P, fn, cap=None, margin=0.0):
    """style_top_pdf.backtest 와 같은 규약(월말 리밸·상위 10 동일가중·사이 표류)에
    **섹터 캡**과 **선정 히스테리시스**를 얹은 판.

    히스테리시스는 경로에 의존한다(직전 보유가 이번 선정에 영향을 준다). 그래서 캐시로
    시점을 건너뛸 수 없고 시간 순서대로 돌린다 — 원본이 pick() 을 캐시하는 것과 다른 점이다.
    """
    end = len(P.dates) - 1
    start = max(0, end - ST.WINDOW)
    _iss = ST.iss_of(P)

    def score(i):
        sc, tie = fn(P, i)
        if len(sc) < ST.MIN_NAMES:
            return None
        ok = [t for t in sc if t in P.px and not np.isnan(P.px[t][i])]
        if not ok:
            return None
        return sc, tie, ok

    def choose(i, held):
        z = score(i)
        if not z:
            return None
        sc, tie, ok = z
        adj = {t: sc[t] + (margin if t in held else 0.0) for t in ok}   # ③ 히스테리시스
        ok.sort(key=lambda t: (-adj[t], -tie.get(t, 0.0), t))
        seen, ded = set(), []                       # 복수 클래스는 한 칸(스타일 전략과 같은 규약)
        for t in ok:
            k = _iss.get(t, t)
            if k in seen:
                continue
            seen.add(k)
            same = [x for x in ok if _iss.get(x, x) == k]
            a_ = next((x for x in same if ST.is_class_a(P, x)), None)
            ded.append(a_ or t)
        sel = pick_capped(P, ded, cap) if cap else ded[:TOPN]           # ② 섹터 캡
        if len(sel) < TOPN:
            return None
        return [(t, sc[t], tie.get(t, sc[t])) for t in sel]

    init, init_i = None, None
    for i in [j for j in P.me if j <= start][::-1][:14]:
        init = choose(i, set())
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
            p_ = choose(i, set(w))
            if p_:
                picks[i] = p_
                w = {t: 1.0 / TOPN for t, _s, _u in p_}
    today = choose(end, set(w))
    if not today:
        return None
    prev_i = max(picks) if picks else init_i
    return {"nav": nav, "start": start, "end": end,
            "prev_i": prev_i, "prev": picks.get(prev_i) or init,
            "today_i": end, "today": today, "n_rebal": len(picks), "init_i": init_i}


# ── 강화 전략 12종 ──────────────────────────────────────────────────────────
# 앞 다섯은 BK 장치를 얹은 것, 뒤 일곱은 스타일 팩터를 결합·필터·게이트로 강화한 것이다.

def sc_multi5(P, i):
    """모멘텀·퀄리티·가치·성장·저변동 다섯 합성점수의 z 평균.

    고베타는 뺐다 — 초과수익 팩터가 아니라 방향성 증폭이라 섞으면 결합의 뜻이 흐려진다.
    아래 BK 장치 계열이 전부 이 결합점수 위에 얹힌다(장치의 효과만 갈라 보려는 것이다).
    """
    return zavg([ST.sc_mom(P, i), ST.sc_qual(P, i), ST.sc_val(P, i),
                 ST.sc_grow(P, i), zs(raw_vol(P, i), MSCI_WP)])


def sc_multi5_sn(P, i):
    """① BK 섹터중립 — 다섯 팩터를 각각 섹터 안에서 표준화한 뒤 평균한다."""
    return zavg([sector_neutral(P, raw_mom(P, i)), sector_neutral(P, raw_roe(P, i)),
                 sector_neutral(P, raw_bp(P, i)), sector_neutral(P, raw_ep(P, i)),
                 sector_neutral(P, raw_vol(P, i))])


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


def raw_mom(P, i):
    """12-1 모멘텀 원시값 — 섹터중립 z 를 만들 때 쓴다."""
    out = {}
    for t, a in P.px.items():
        if i < 252 or np.isnan(a[i]) or np.isnan(a[i - 21]) or np.isnan(a[i - 252]):
            continue
        if a[i - 252] > 0 and a[i - 21] > 0:
            out[t] = a[i - 21] / a[i - 252] - 1.0
    return out


def raw_ep(P, i):
    out = {}
    for t in P.uni:
        p_, eps = _px(P, t, i), P.ttm(t, "eps", i)
        if p_ and eps is not None:
            out[t] = eps / p_
    return out


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


# (키, 이름, 참조, 점수함수, 마지막칸 라벨, 포맷, 설명, 섹터캡, 히스테리시스)
STRATS = [
    ("bk_full", "BK 완본 이식", "kb #b 전략 B 장치 3종", sc_multi5_sn, "합성 z", m_z,
     "5팩터를 각각 섹터 안에서 표준화하고(섹터중립), 한 섹터가 3종목을 넘지 못하게 막고(섹터 캡),\n"
     "기존 보유에 z 0.5 마진을 줘 교체를 억제한다(히스테리시스). BK 의 구조 장치 셋을 한꺼번에 얹은 판이다.",
     SEC_CAP, HYST),
    ("bk_sn", "BK 섹터중립", "kb #b ① 섹터 내 순위", sc_multi5_sn, "합성 z", m_z,
     "5팩터를 섹터 안에서 표준화해 평균한다. 업종 전체가 싸거나 비싼 국면에서 팩터가 업종 베팅으로\n"
     "변질되는 것을 막는다 — BK 가 '업종별 역작동 차단'이라 부른 장치다. 캡·히스테리시스는 없다.",
     None, 0.0),
    ("bk_cap", "BK 섹터 캡", "kb #b ⑤ 스타일 캡의 섹터판", sc_multi5, "합성 z", m_z,
     "일반 5팩터 결합에 섹터당 최대 3종목 제약만 얹는다. 결합점수가 한 업종에 쏠릴 때\n"
     "그 쏠림이 성과의 원인인지 가려 보려는 것이다.", SEC_CAP, 0.0),
    ("bk_hyst", "BK 히스테리시스", "kb #b ④ 선정 히스테리시스", sc_multi5, "합성 z", m_z,
     "일반 5팩터 결합에 교체 마진 z 0.5 만 얹는다. 신규 후보가 기존 보유를 그만큼 넘어야 갈아탄다.\n"
     "BK 실측에서는 턴오버가 64% 줄고 gross 수익이 함께 좋아졌다 — 여기서도 그런지 본다.",
     None, HYST),
    ("multi5", "5팩터 결합", "다중팩터 기본형", sc_multi5, "합성 z", m_z,
     "모멘텀·퀄리티·가치·성장·저변동 다섯 합성점수의 z 평균. 위 세 장치의 대조군이다 —\n"
     "장치를 얹기 전의 값이라 차이가 곧 장치의 몫이다.", None, 0.0),
    ("val_qual", "가치 + 퀄리티", "QARP", sc_val_qual, "PER", ST.d_val,
     "가치(B/P·E/P·S/P)와 퀄리티(ROE·D/E·이익변동성)의 z 평균. '적당한 값에 좋은 회사'.\n"
     "가치의 함정과 퀄리티의 비싼 값을 서로 상쇄시키려는 고전적 결합이다.", None, 0.0),
    ("mom_qual", "모멘텀 + 퀄리티", "모멘텀 강화 ①", sc_mom_qual, "12M 수익률 %", ST.d_mom,
     "위험조정 모멘텀과 퀄리티의 z 평균. 추세를 타되 재무가 받치는 종목만 담는다.\n"
     "모멘텀은 국면 전환에서 한꺼번에 무너지는데, 퀄리티가 그 낙폭을 줄이는지 본다.", None, 0.0),
    ("mom_lv", "모멘텀 ÷ 변동성", "모멘텀 강화 ②", sc_mom_lv, "변동성 %", m_vol,
     "위험조정 모멘텀과 저변동의 z 평균. 같은 추세라면 덜 흔들리는 쪽을 고른다.\n"
     "샤프를 겨냥한 결합이라 절대수익은 순수 모멘텀보다 낮게 나오기 쉽다.", None, 0.0),
    ("grow_prof", "성장 + 수익성", "성장 강화", sc_grow_prof, "ROE %", m_roe,
     "성장(매출성장·EPS변화·모멘텀)에 ROE 를 더한 z 평균. 매출만 늘고 돈은 못 버는 성장을 걸러낸다.\n"
     "실적 추정이 꺾일 때 순수 성장보다 덜 빠지는지 본다.", None, 0.0),
    ("lv_qual", "저변동 + 퀄리티", "방어 강화", sc_lv_qual, "변동성 %", m_vol,
     "252일 변동성(－)과 퀄리티의 z 평균. 조용한 것 중 재무가 받치는 것만 담는다.\n"
     "저변동 단독은 방어 업종에 쏠리는데, 퀄리티를 섞으면 그 쏠림이 줄어드는지 본다.", None, 0.0),
    ("btp", "장부가 + 흑자 + 추세", "Book-to-Price 강화", sc_btp, "B/P", m_bp,
     "장부가÷주가가 큰 종목 중 TTM 순이익이 양(+)이고 200일선 위인 것만 담는다.\n"
     "적자면 자기자본이 녹는 중이라 싼 게 아니고, 하락추세면 아직 칼이 떨어지는 중이다.", None, 0.0),
    ("agg", "공격 결합", "모멘텀+성장+고베타", sc_agg, "합성 z", m_z,
     "모멘텀·성장·고베타의 z 평균. 강세장 증폭이 목적인 규칙이라 절대수익이 아니라\n"
     "MDD 와 함께 읽어야 한다. 이 문서에서 가장 크게 빠질 수 있는 자리다.", None, 0.0),
]


def footer(fig, page, total):
    ST.hline(fig, ST.X0, ST.X1, .034, ST.LINE, .6)
    ST.tx(fig, ST.X0, .026,
          "강화 팩터 전략 12종 · 스타일 6종을 결합·필터·게이트로 강화 + BK(kb #b) 구조 장치 3종 이식 · "
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
    ST.TITLE = "강화 팩터 전략 12종"
    ST.SUBTITLE = "스타일 6종 + BK(kb #b 전략 B) 장치 · 최근 1년 요약"
    # 요약 쪽 곡선 색 표도 갈아 끼운다 — 원본은 스타일 6종 키만 갖고 있어 KeyError 가 난다.
    #   BK 장치 계열은 같은 계열로 읽히게 한 색조(주황)에 명도를 달리하고, 스타일 강화 계열은
    #   원래 스타일 색을 물려받게 둔다 — 두 문서를 나란히 놓았을 때 계열이 눈으로 이어진다.
    ST.SCOL = {
        "bk_full": ST.MARG, "bk_sn": ST.ACC, "bk_cap": "#C98A3A", "bk_hyst": "#8C6B2F",
        "multi5": ST.INK2,
        "val_qual": ST.NEG, "mom_qual": ST.CHAMP, "mom_lv": "#5B8FA8",
        "grow_prof": ST.RP, "lv_qual": ST.POS, "btp": "#7A4B3B", "agg": "#B03A2E",
    }
    miss = [k for k, *_ in STRATS if k not in ST.SCOL]
    if miss:
        raise SystemExit("곡선 색이 없는 전략: %s" % miss)

    res, order = {}, []
    for S in STRATS:
        R = bt2(P, S[3], cap=S[7], margin=S[8])
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
