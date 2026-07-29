# -*- coding: utf-8 -*-
"""build/style_top.py — 스타일별 상위 10종목 → data/style_top.json

무엇을. 유니버스 518종목(S&P 500 ∪ NASDAQ 100)에 **실제 스타일 지수의 산식**을 그대로 적용해
스타일마다 상위 10종목을 뽑는다. 홈 스타일 성과표(ETF 수익률)가 '무엇이 갔나'를 말한다면,
이 목록은 '그 스타일이라면 지금 무엇인가'를 말한다.

출처 — 각 지수의 공개 방법론을 따랐고, 우리 패널에 없는 항목만 대체했다(대체는 전부 아래에 적는다).
  모멘텀   MSCI USA Momentum : 위험조정 6M·12M 가격모멘텀의 z 평균(±3 윈저화)
  퀄리티   MSCI Quality      : ROE(+) · 부채비율 D/E(−) · 이익변동성(−) z 평균
  가치     MSCI Enhanced Value: 선행 E/P · B/P · EBITDA/EV z 평균
  저변동   S&P 500 Low Volatility : 최근 252거래일 일간수익률 표준편차 최소
  성장     S&P 500 Pure Growth: 3년 주당매출 성장 · 3년 주당이익 변화/주가 · 12개월 모멘텀
  고베타   S&P 500 High Beta : 최근 252거래일 일간수익률의 S&P 500 대비 베타 최대
  중소형   MSCI Size         : 시가총액 최소
  배당성장 S&P High Yield Dividend Aristocrats : ⚠ 아래 '대체' 참조

대체한 것 — 숨기지 않고 적는다.
  · 가치의 EV/CFO 를 **EV/EBITDA**로 바꿨다. 랩 패널이 그쪽을 들고 있다(eveb, 커버 93.8%).
  · 이익변동성은 5년 YoY EPS 성장률의 표준편차인데, 랩의 재무 시계열이 분기 20개(약 5년)라
    YoY 관측이 16개다. 정의는 같고 표본이 딱 5년이다.
  · **배당성장은 정의를 못 지킨다.** 원지수는 20년 연속 증배가 조건인데 랩에는 5년치뿐이다.
    5년 연속 회계연도에 감배가 없는 종목을 배당성장률과 배당수익률로 세운 **대용**이며,
    원지수 편입과 다르다. 그렇게 표시한다. 5년으로 줄이며 생기는 함정 셋을 규칙으로 막는다 —
    연도 구멍(관측 5개 ≠ 5년), 액면분할 미반영(주식수로 되돌린다), 그리고 창 밖의 감배를
    못 보는 것(한 해 2배 초과 급증은 복원·신규 개시로 보고 제외).
  · 무위험수익률을 모멘텀 분자에서 빼지 않았다(횡단면 순위에 상수는 영향이 없다).

⚠ 이것은 **오늘의 화면**이지 백테스트가 아니다. 성과를 주장하지 않으며, 이 랩은 팩터 모멘텀을
  '자기 유니버스 대비 구별 불가'로 이미 기각했다. 순위는 상태 표시로만 읽을 것.

  python build/style_top.py
"""
from __future__ import annotations
import io, json, os, sys

import re

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "style_top.json")

TOPN = 10
MIN_DAYS = 252 * 3      # 모멘텀 변동성에 3년이 필요하다
WIN = 3.0               # z 윈저화 한계(MSCI 규약)
SP_WP = 10.0            # S&P U.S. Style 은 원시값을 90퍼센타일로 자른다(정본 p6)
BASKET = 0.33           # 성장·가치 바스켓은 각각 시가총액 33%까지(정본 p6)
PURE_MIN = 0.25         # '순수'는 점수가 전체 평균 + 0.25 를 넘어야 한다(정본 p9)
WINSOR_P = 2.5          # 원시값 윈저화 백분위(양쪽). 표준화 **전에** 자른다 — zs() 주석 참조


def load(fn):
    p = os.path.join(DATA, fn)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def issuer_map(uni):
    """티커 → 발행사 키. 이름에서 클래스 꼬리를 떼어 같은 회사를 묶는다.

    ⚠ S&P 정본은 복수 클래스를 **둘 다** 편입한다(정본 p4). 여기서 하나로 줄이는 것은
      10칸짜리 목록에서 한 회사가 두 칸을 먹지 않게 하려는 **표시 목적의 의도적 이탈**이다.
      유니버스 518종목에서 걸리는 것은 알파벳·폭스·뉴스코프 셋뿐이다.
    """
    out = {}
    for t, s in uni.items():
        n = (s.get("name") or "").upper().strip()
        n = re.sub(r"\s*-\s*(CL|CLASS|SER|SERIES)\s+[A-Z0-9]+$", "", n)
        n = re.sub(r"\s*-\s*[A-Z]$", "", n)
        out[t] = re.sub(r"[^A-Z0-9]", "", n) or t
    return out


def zs(d, wp=None):
    """{티커: 값} → {티커: z}.

    ⚠ **원시값을 먼저 윈저화하고 표준화한다.** MSCI 방법론이 그렇게 적고 있고(outlier
      fundamental variable values are winsorized), 안 하면 한 종목이 분포를 통째로 끈다 —
      실제로 그랬다. 시게이트 ROE 1788%(자기자본이 거의 없어 나온 값)가 평균·표준편차를
      밀어 퀄리티 1위로 올라왔고, 모더나 주당매출 3년 CAGR +218%가 성장 5위를 만들었다.
      z 를 나중에 ±3 으로 잘라도 그때는 이미 나머지 종목의 z 가 0 근처로 눌린 뒤다.
    """
    ks = [k for k, v in d.items() if v is not None and v == v and abs(v) != float("inf")]
    if len(ks) < 20:
        return {}
    a = np.array([d[k] for k in ks], float)
    wp = WINSOR_P if wp is None else wp
    lo, hi = np.percentile(a, wp), np.percentile(a, 100 - wp)
    a = np.clip(a, lo, hi)
    mu, sd = float(a.mean()), float(a.std(ddof=1))
    if sd <= 0:
        return {}
    # (자른 z, 안 자른 z) 쌍을 돌려준다. 앞은 MSCI 규약대로 점수이고, 뒤는 **순위를 가르는 데만**
    # 쓴다 — ±3 에 눌린 종목이 여럿이면 점수가 같아져 상위 10의 순서가 임의로 정해진다.
    # 실측: 모멘텀 상위 6종이 전부 3.0 이었고(원시 위험조정 3.6~5.24) 실행할 때마다 순서가 바뀌었다.
    out = {}
    for k in ks:
        zw = (min(max(d[k], lo), hi) - mu) / sd     # 원시 윈저화 O · z 절단 O → MSCI 점수
        zr = (d[k] - mu) / sd                       # 둘 다 X → 순위만 가르는 값
        out[k] = (float(np.clip(zw, -WIN, WIN)), float(zr))
    return out


def zavg(parts):
    """여러 z 묶음의 평균. **전 항목이 있는 종목만** 남긴다 — 두 개만 가진 종목이
    평균 하나로 상위에 올라오면 그건 다른 규칙이다."""
    if not parts:
        return {}
    common = set(parts[0])
    for p in parts[1:]:
        common &= set(p)
    return {k: (float(np.mean([p[k][0] for p in parts])),
                float(np.mean([p[k][1] for p in parts]))) for k in common}


def series_at(ser, back):
    """날짜 내림차순 시계열에서 back번째 관측. 없으면 None."""
    return ser[back][1] if ser and len(ser) > back else None


DIVG_YEARS = 5          # 배당성장 표본(회계연도). 원지수는 20년이다 — 대용임을 화면에 적는다.
DIVG_SPLIT = 1.5        # 분할 판별 1차 조건 — 주식수가 이 배수를 넘게 변한다
DIVG_SPLIT_TOL = .4     # 2차 조건 — dps 가 그 역수배로 함께 움직였나(이 비율 오차 안)
DIVG_JUMP = 2.0         # 한 해에 이만큼 뛰면 '감배 후 복원·신규 개시'로 보고 제외한다


def ann_bucket(t, key):
    """data/fx/<티커>.json 의 **연간(a)** 버킷 → {연도: 값}.

    tech_backtest.load_fund() 는 i·q(시점·분기)만 보므로 여기서 직접 읽는다.
    dps 를 분기로 읽으면 회사마다 분기값과 연 누적값이 섞여 성장률이 튄다 —
    수집기(refresh_facts.pick)가 350~380일 구간만 담아 둔 a 버킷은 그 문제가 없다.
    """
    p = os.path.join(DATA, "fx", "%s.json" % t)
    if not os.path.exists(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}
    rows = (((d.get("tags") or {}).get(key) or {}).get("a") or [])
    return {e[:4]: float(v) for e, v in rows
            if v is not None and isinstance(v, (int, float)) and float(v) > 0}


def divg_window(t):
    """최신 DIVG_YEARS 개 **연속** 회계연도의 분할보정 주당배당.

    → (연도들, 보정 dps, 원본 dps) 또는 None(자격 미달).

    ⚠ 관측이 5개라고 5년이 아니다 — VTR 은 2023 다음이 2017 이라 그냥 자르면
      9년을 5년으로 착각한다. 그래서 연도 간격을 확인한다.
    ⚠ dps 는 공시된 그대로라 액면분할이 반영돼 있지 않다. AVGO 14.40 → 1.64 는
      감배가 아니라 10:1 분할이다. 분할이면 주식수가 같은 배수로 늘므로 sh 로 되돌린다.
    🚨 **주식수가 늘었다는 것만으로 분할이라 하면 안 된다.** VICI 는 MGP 인수로 주식이
      1.52배 늘었지만 배당은 1.09배 오른 것이라 분할이 아니다. 그런데 분할로 보고 과거
      배당을 1.52 로 나누면 성장률이 6%→18% 로 부풀어 1위로 올라온다(실측으로 잡았다).
      그래서 **주식수가 r 배 되는 동시에 dps 가 대략 1/r 배**가 된 경우만 분할로 본다.
      둘이 어긋나면 손대지 않는다 — 못 고치는 것보다 없는 분할을 만드는 쪽이 나쁘다.
    """
    dps, sh = ann_bucket(t, "dps"), ann_bucket(t, "sh")
    ys = sorted(dps, reverse=True)
    if len(ys) < DIVG_YEARS:
        return None
    win = sorted(ys[:DIVG_YEARS])
    if int(win[-1]) - int(win[0]) != DIVG_YEARS - 1:
        return None                                  # 중간에 빠진 해가 있다
    raw = [dps[y] for y in win]
    adj, f = list(raw), 1.0                          # 최신에서 거꾸로 훑으며 배수를 누적
    for i in range(len(win) - 1, 0, -1):
        a, b = win[i - 1], win[i]
        if a in sh and b in sh and sh[a] > 0 and raw[i - 1] > 0:
            r = sh[b] / sh[a]
            if r > DIVG_SPLIT or r < 1 / DIVG_SPLIT:
                got = raw[i] / raw[i - 1]            # dps 가 실제로 움직인 배수
                if abs(got * r - 1.0) < DIVG_SPLIT_TOL:   # 1/r 배에 가까운가
                    f *= r
        adj[i - 1] = raw[i - 1] / f
    return win, adj, raw


def main() -> int:
    st = load("stocks.json")
    if not st:
        print("❌ data/stocks.json 없음"); return 1
    dates = st["pxd_dates"]
    uni = {s["t"]: s for s in st["stocks"]}
    print("유니버스 %d종목 · 일별 %d일 (%s ~ %s)" % (len(uni), len(dates), dates[0], dates[-1]))

    # ── 일별 종가 ── 종목 파일에서 읽는다(이미 커밋돼 있다. 추가 호출 0회)
    PX = {}
    for t in uni:
        p = os.path.join(DATA, "sd", "%s.json" % t)
        if not os.path.exists(p):
            continue
        try:
            v = json.load(io.open(p, encoding="utf-8")).get("pxd")
        except Exception:
            continue
        if v and len(v) == len(dates):
            PX[t] = np.array([x if x is not None else np.nan for x in v], float)
    print("  일별 종가 %d종목" % len(PX))

    # ── 시장(S&P 500) 일별 — 베타용. assets.json 은 날짜 축이 달라 교집합으로 맞춘다.
    A = load("assets.json") or {}
    adates, aspy = A.get("dates") or [], (A.get("px") or {}).get("SPY") or []
    amap = {d: p for d, p in zip(adates, aspy) if p is not None}
    mkt = np.array([amap.get(d, np.nan) for d in dates], float)

    import importlib.util
    spec = importlib.util.spec_from_file_location("_tb", os.path.join(HERE, "tech_backtest.py"))
    tb = importlib.util.module_from_spec(spec); spec.loader.exec_module(tb)
    FX = tb.load_fund()

    ISS = issuer_map(uni)

    def fund(t, k):
        v = (uni[t].get("fund") or {}).get(k)
        return v if isinstance(v, (int, float)) else None

    def rets(a):
        return a[1:] / a[:-1] - 1.0

    # ── 모멘텀 ── MSCI: 최근 1개월을 제외한 6M·12M 수익률 ÷ 3년 주간변동성
    mom6, mom12, mom12r = {}, {}, {}
    for t, a in PX.items():
        if len(a) < MIN_DAYS or np.isnan(a[-1]):
            continue
        w = a[-(252 * 3):][::5]                      # 주간(5거래일) 표본
        w = w[~np.isnan(w)]
        if len(w) < 100:
            continue
        sig = float(np.std(rets(w), ddof=1)) * np.sqrt(52)
        p1, p7, p13 = a[-22], a[-22 - 126], a[-22 - 252]
        if sig <= 0 or np.isnan(p1) or np.isnan(p7) or np.isnan(p13) or p7 <= 0 or p13 <= 0:
            continue
        mom6[t] = (p1 / p7 - 1.0) / sig
        mom12[t] = (p1 / p13 - 1.0) / sig
        if not np.isnan(a[-252]) and a[-252] > 0:
            mom12r[t] = a[-1] / a[-252] - 1.0        # 성장 점수가 쓰는 '순수' 12개월 수익률
    MOM = zavg([zs(mom6), zs(mom12)])

    # ── 저변동 · 고베타 ── 최근 252거래일 일간수익률
    vol, beta = {}, {}
    mr_all = rets(mkt)
    for t, a in PX.items():
        r = rets(a)[-252:]
        m = mr_all[-252:]
        ok = ~(np.isnan(r) | np.isnan(m))
        if ok.sum() < 200:
            continue
        vol[t] = float(np.std(r[ok], ddof=1)) * np.sqrt(252) * 100
        vm = float(np.var(m[ok], ddof=1))
        if vm > 0:
            beta[t] = float(np.cov(r[ok], m[ok], ddof=1)[0, 1] / vm)

    # ── 퀄리티 ── ROE(+) · D/E(−) · 이익변동성(−)
    evar = {}
    for t, f in FX.items():
        eps = f.get("eps") or []
        g = []
        for i in range(len(eps) - 4):
            a0, a1 = eps[i][1], eps[i + 4][1]
            if a1 and abs(a1) > 1e-9:
                g.append((a0 - a1) / abs(a1))
        if len(g) >= 8:
            evar[t] = float(np.std(np.array(g, float), ddof=1))
    QUAL = zavg([zs({t: fund(t, "roe") for t in uni}),
                 zs({t: -v for t, v in ((t, fund(t, "de")) for t in uni) if v is not None}),
                 zs({t: -v for t, v in evar.items()})])

    # ── 가치 ── 선행 E/P · B/P · EBITDA/EV (역수로 세운다 — 높을수록 싸다)
    def inv(k):
        out = {}
        for t in uni:
            v = fund(t, k)
            if v is None or v == 0:
                continue
            out[t] = 1.0 / v
        return out
    eveb = {}
    for t in uni:
        p = os.path.join(DATA, "sd", "%s.json" % t)
        if not os.path.exists(p):
            continue
        try:
            fxr = (json.load(io.open(p, encoding="utf-8")).get("fundx") or {}).get("eveb")
        except Exception:
            continue
        if fxr and isinstance(fxr[0], (int, float)) and fxr[0] != 0:
            eveb[t] = 1.0 / fxr[0]
    VAL = zavg([zs(inv("fpe")), zs(inv("pb")), zs(eveb)])

    # ── 성장(S&P U.S. Style) ── 3요소 + 문서의 폴백 규칙
    #   · 3년 전 값이 없으면 2년 → 1년 순으로 내려가고, 1년도 없으면 0으로 둔다(문서 p6).
    #   · 주당매출 성장은 **시작값이 음수면 부호를 뒤집는다**(문서 p6).
    #   · 이익 변화는 '현재 주가'로 나눈다 — 분모가 과거 주가가 아니다.
    SP_BACK = [12, 8, 4]          # 분기 수 = 3년 · 2년 · 1년
    sps, epc = {}, {}
    for t, f in FX.items():
        rev, sh, eps = f.get("rev") or [], f.get("sh") or [], f.get("eps") or []
        s0 = series_at(sh, 0)
        for b in SP_BACK:                       # 주당매출 성장률
            r0, rb, sb = series_at(rev, 0), series_at(rev, b), series_at(sh, b)
            if r0 is None or rb is None or not s0 or not sb or s0 <= 0 or sb <= 0:
                continue
            a_, b_ = r0 / s0, rb / sb
            if b_ == 0:
                continue
            g = (a_ / abs(b_)) ** (4.0 / b) - 1.0 if b_ > 0 else None
            if g is None:                       # 시작값이 음수면 부호를 뒤집는다
                g = -(((a_ / abs(b_)) ** (4.0 / b)) - 1.0)
            sps[t] = g
            break
        else:
            sps[t] = 0.0
        px = PX.get(t)
        if px is None or np.isnan(px[-1]) or px[-1] <= 0:
            continue
        for b in SP_BACK:                       # 주당이익 변화 ÷ 현재 주가
            e0, eb = series_at(eps, 0), series_at(eps, b)
            if e0 is None or eb is None:
                continue
            epc[t] = (e0 - eb) * 4 / px[-1]     # 분기 EPS라 연으로 환산해 주가와 맞춘다
            break
        else:
            epc[t] = 0.0
    # S&P 는 원시값을 **90퍼센타일로** 윈저화한다(문서 p6) — MSCI 계열과 지점이 다르다.
    GROWz = [zs(sps, SP_WP), zs(epc, SP_WP), zs(mom12r, SP_WP)]
    GROW = zavg(GROWz)

    # ── 가치(S&P U.S. Style) ── B/P · E/P · S/P. MSCI Enhanced Value(선행 E/P·B/P·EBITDA/EV)와
    #    **다른 지수다** — 그래서 따로 싣는다. 여기 E/P 는 후행(tpe)이다.
    SPVAL = zavg([zs(inv("pb"), SP_WP), zs(inv("tpe"), SP_WP), zs(inv("ps"), SP_WP)])

    # ── 순수성장 · 순수가치 ── 문서 p6~p9의 바스켓 규칙
    #   ① 성장점수 높은 순 = 성장랭크 1위 · 가치점수 높은 순 = 가치랭크 1위
    #   ② 성장랭크/가치랭크 를 오름차순 — 위쪽이 순수성장, 아래쪽이 순수가치
    #   ③ 시가총액 누적 33%까지가 각 바스켓
    #   ④ 그중 점수가 (전체 평균 + 0.25) 를 넘는 것만 '순수'로 남긴다
    common = sorted(set(GROW) & set(SPVAL))
    PURE_G, PURE_V, ratio, GRK, VRK = [], [], {}, {}, {}
    if len(common) >= 50:
        gr = {t: i + 1 for i, t in enumerate(sorted(common, key=lambda x: -GROW[x][0]))}
        vr = {t: i + 1 for i, t in enumerate(sorted(common, key=lambda x: -SPVAL[x][0]))}
        GRK, VRK = gr, vr
        for t in common:
            ratio[t] = gr[t] / vr[t]
        order = sorted(common, key=lambda t: ratio[t])
        mcv = {t: (fund(t, "mc") or 0.0) for t in common}
        tot = sum(mcv.values()) or 1.0
        gmean = float(np.mean([GROW[t][0] for t in common]))
        vmean = float(np.mean([SPVAL[t][0] for t in common]))
        acc = 0.0
        for t in order:                          # 위에서부터 시총 33% = 성장 바스켓
            if acc / tot >= BASKET:
                break
            acc += mcv[t]
            if GROW[t][0] > gmean + PURE_MIN:
                PURE_G.append(t)
        acc = 0.0
        for t in reversed(order):                # 아래에서부터 시총 33% = 가치 바스켓
            if acc / tot >= BASKET:
                break
            acc += mcv[t]
            if SPVAL[t][0] > vmean + PURE_MIN:
                PURE_V.append(t)

    # ── 배당성장 ── 원지수의 20년을 5년으로 줄인 **대용**이다. 원지수 편입과 다르다.
    #   전에는 산출하지 않았다. 근거는 'dps 시계열이 분기값과 누적값이 섞여 성장률이
    #   연 45~78% 로 튄다'였는데, 그건 **분기(q) 버킷** 이야기였다. 연간(a) 버킷은
    #   멀쩡하다(실측 2026-07-29: AMCR 0.4675→0.5075 · PNC 4.80→6.60 · KO 1.68→2.04,
    #   전부 단조 증가). 연간을 그대로 쓰면 4년 CAGR 중위값이 7.4% 로 상식 범위에 든다.
    #
    #   대신 5년으로 줄이면서 생기는 함정 셋을 규칙으로 막는다.
    #     ① 관측 5개 ≠ 5년 연속 — 구멍 있는 37종목을 divg_window() 가 떨군다.
    #     ② 액면분할이 dps 에 없다 — 주식수로 되돌린다. 안 하면 AVGO·LRCX·ODFL 같은
    #        진짜 배당성장주가 '감배'로 탈락한다(실측 8종목).
    #     ③ 20년 조건이 실제로 막아 주던 것은 **감배 후 복원**이다. 5년 창에서는 잘랐던
    #        사실이 창 밖이라 안 보여, OXY(2020년 −98% 후 복원)가 성장률 1위로 올라온다.
    #        한 해에 2배 넘게 뛴 이력이 있으면 제외한다(복원·신규 개시 둘 다 걸린다).
    DIVG, DIVG_D = {}, {}
    _dv_excl = {"gap": 0, "cut": 0, "jump": 0, "nopx": 0}
    for t in uni:
        w = divg_window(t)
        if w is None:
            _dv_excl["gap"] += 1
            continue
        yrs, adj, raw = w
        if any(adj[i] < adj[i - 1] * .999 for i in range(1, len(adj))):
            _dv_excl["cut"] += 1
            continue
        if any(adj[i] > adj[i - 1] * DIVG_JUMP for i in range(1, len(adj))):
            _dv_excl["jump"] += 1
            continue
        px = PX.get(t)
        if px is None or np.isnan(px[-1]) or px[-1] <= 0:
            _dv_excl["nopx"] += 1
            continue
        DIVG[t] = {"cagr": (adj[-1] / adj[0]) ** (1 / (len(adj) - 1)) - 1,
                   "yield": adj[-1] / float(px[-1]) * 100,
                   "yrs": "%s~%s" % (yrs[0], yrs[-1]), "adj": adj, "raw": raw,
                   "split": any(abs(a - r) > 1e-9 for a, r in zip(adj, raw))}
    # 원지수는 배당수익률로 가중한다 — 여기서는 성장률과 수익률의 z 평균으로 세운다.
    DIVG_S = zavg([zs({t: v["cagr"] for t, v in DIVG.items()}),
                   zs({t: v["yield"] for t, v in DIVG.items()})])
    print("  배당성장 %d종목 (제외 — 5년연속 아님 %d · 감배 %d · 급증 %d · 종가없음 %d)"
          % (len(DIVG_S), _dv_excl["gap"], _dv_excl["cut"], _dv_excl["jump"], _dv_excl["nopx"]))

    def pack(key, label, ref, url, rule, sub, score, detail, rev_=False, n_=TOPN, slab="합성 z"):
        # 점수가 (자른 z, 안 자른 z) 쌍이면 둘로 정렬한다 — 앞이 같을 때만 뒤가 순서를 가른다.
        pair = any(isinstance(v, tuple) for v in score.values())
        ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=not rev_)
        rows, seen, dropped = [], set(), []
        for t, v in ranked:
            k = ISS.get(t, t)
            if k in seen:
                dropped.append(t); continue      # 같은 회사의 다른 클래스 — 다음 순위가 채운다
            seen.add(k); rows.append((t, v))
            if len(rows) >= n_:
                break
        return {"key": key, "label": label, "index_ref": ref, "url": url, "rule": rule,
                "substitution": sub, "n_scored": len(score), "score_label": slab,
                "tie_break": ("z 를 ±3 으로 자른 뒤 같아지면, 자르기 전 값으로 순서를 가른다"
                              if pair else None),
                "dedup_dropped": dropped or None,
                "top": [{"t": t, "n": uni[t].get("name"), "s": uni[t].get("sector"),
                         "score": round(v[0] if pair else v, 3),
                         "score_unclipped": (round(v[1], 3) if pair else None),
                         "d": detail(t)} for t, v in rows]}

    R2 = lambda v: None if v is None else round(float(v), 2)
    styles = [
        pack("mom", "모멘텀", "MSCI USA Momentum",
             "https://www.msci.com/indexes/index/703025",
             "최근 1개월을 뺀 6개월·12개월 수익률을 3년 주간변동성으로 나눈 뒤 z 평균(±3 윈저화)",
             None, MOM,
             lambda t: {"6M(위험조정)": R2(mom6.get(t)), "12M(위험조정)": R2(mom12.get(t)),
                        "12M 수익률 %": R2((mom12r.get(t) or 0) * 100) if t in mom12r else None}),
        pack("qual", "퀄리티", "MSCI Quality",
             "https://www.msci.com/indexes/documents/methodology/2_MSCI_Quality_Indexes_Methodology_20231120.pdf",
             "ROE(+) · 부채비율 D/E(−) · 이익변동성(−)의 z 평균",
             "이익변동성 표본이 5년(분기 20개 → YoY 16개)이다", QUAL,
             lambda t: {"ROE %": R2(fund(t, "roe")), "D/E %": R2(fund(t, "de")),
                        "이익변동성": R2(evar.get(t))}),
        pack("val", "가치(MSCI)", "MSCI USA Enhanced Value",
             "https://www.msci.com/indexes/index/705973/msci-usa-enhanced-value-index",
             "선행 E/P · B/P · EBITDA/EV 의 z 평균(전부 높을수록 싸다)",
             "원지수의 EV/CFO 대신 EV/EBITDA 를 썼다 — 랩 패널이 들고 있는 쪽이다", VAL,
             lambda t: {"선행 PER": R2(fund(t, "fpe")), "PBR": R2(fund(t, "pb")),
                        "EV/EBITDA": R2(1 / eveb[t]) if eveb.get(t) else None}),
        pack("lowvol", "저변동", "S&P 500 Low Volatility",
             "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-low-volatility-indices.pdf",
             "최근 252거래일 일간수익률의 표준편차가 가장 작은 순", None, vol,
             lambda t: {"연율 변동성 %": R2(vol.get(t)), "베타": R2(beta.get(t))},
             rev_=True, slab="연율 변동성 %"),
        pack("grow", "성장", "S&P 500 Growth (S&P U.S. Style)",
             "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-style.pdf",
             "3년 주당이익 변화÷현재주가 · 3년 주당매출 성장률 · 12개월 모멘텀의 z 평균"
             "(원시값 90퍼센타일 윈저화 · 3년이 없으면 2년→1년 폴백)", None, GROW,
             lambda t: {"주당매출 3Y CAGR %": R2((sps.get(t) or 0) * 100),
                        "EPS변화/주가 %": R2((epc.get(t) or 0) * 100),
                        "12M 수익률 %": R2((mom12r.get(t) or 0) * 100) if t in mom12r else None}),
        # 홈 스타일표의 '가치' 행이 이것이다(대응 ETF는 IVE). 그래서 라벨이 그냥 '가치'이고,
        #   MSCI 계열 쪽에 (MSCI)를 붙여 구분한다 — 표와 구성종목 목록의 이름을 맞추려는 것이다
        #   (사용자 결정 2026-07-29).
        pack("spval", "가치", "S&P 500 Value (S&P U.S. Style)",
             "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-style.pdf",
             "주당순자산÷주가 · 주당이익÷주가 · 주당매출÷주가 의 z 평균(원시값 90퍼센타일 윈저화)",
             "'가치(MSCI)'는 MSCI Enhanced Value(선행 E/P·B/P·EBITDA/EV)로 **다른 지수**다. "
             "이쪽 E/P 는 후행이다", SPVAL,
             lambda t: {"PBR": R2(fund(t, "pb")), "PER(후행)": R2(fund(t, "tpe")),
                        "PSR": R2(fund(t, "ps"))}),
        pack("puregrow", "순수성장", "S&P 500 Pure Growth",
             "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-style.pdf",
             "성장랭크÷가치랭크가 가장 작은 쪽(성장은 높고 가치는 낮은 종목) · 시총 33% 바스켓 안에서 "
             "성장점수가 평균+0.25 를 넘는 것만",
             "정본은 S&P Total Market 에서 표준화하고 모기업 지수에서 랭크한다 — 여기서는 둘 다 "
             "유니버스 518종목이다", {t: -ratio[t] for t in PURE_G},
             lambda t: {"성장점수": R2(GROW[t][0]), "가치점수": R2(SPVAL[t][0]),
                        "성장랭크": GRK.get(t), "가치랭크": VRK.get(t)},
             slab="−(성장랭크÷가치랭크)"),
        pack("pureval", "순수가치", "S&P 500 Pure Value",
             "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-style.pdf",
             "성장랭크÷가치랭크가 가장 큰 쪽(가치는 높고 성장은 낮은 종목) · 시총 33% 바스켓 안에서 "
             "가치점수가 평균+0.25 를 넘는 것만",
             "정본은 S&P Total Market 에서 표준화하고 모기업 지수에서 랭크한다 — 여기서는 둘 다 "
             "유니버스 518종목이다", {t: ratio[t] for t in PURE_V},
             lambda t: {"가치점수": R2(SPVAL[t][0]), "성장점수": R2(GROW[t][0]),
                        "가치랭크": VRK.get(t), "성장랭크": GRK.get(t)},
             slab="성장랭크÷가치랭크"),
        pack("divg", "배당성장", "S&P High Yield Dividend Aristocrats",
             "https://www.spglobal.com/spdji/en/indices/dividends-factors/sp-high-yield-dividend-aristocrats/",
             "5년 연속 회계연도에 감배가 없는 종목을 배당성장률·배당수익률의 z 평균으로",
             "원지수는 **20년** 연속 증배가 조건인데 랩의 연간 재무는 5년치다. "
             "5년 창에서는 그 이전의 감배가 보이지 않으므로, 한 해에 2배 넘게 뛴 이력이 있으면 "
             "감배 후 복원·신규 개시로 보고 제외한다(원지수 편입 종목과 다르다). "
             "주당배당은 공시 그대로라 액면분할이 반영돼 있지 않다 — 주식수가 r 배 되는 동시에 "
             "주당배당이 1/r 배가 된 경우만 분할로 보고 되돌린다. 둘이 어긋나면 손대지 않으므로, "
             "분할을 주식수로 확증하지 못한 종목은 '감배'로 빠진다(없는 분할을 만드는 것보다 낫다)",
             DIVG_S,
             lambda t: {"배당성장률 %": R2(DIVG[t]["cagr"] * 100),
                        "배당수익률 %": R2(DIVG[t]["yield"]),
                        "구간": DIVG[t]["yrs"],
                        "주당배당": " → ".join("%.3f" % v for v in DIVG[t]["adj"]),
                        "분할보정": "예" if DIVG[t]["split"] else "아니오"}),
        pack("hbeta", "고베타", "S&P 500 High Beta",
             "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-high-beta-indices.pdf",
             "최근 252거래일 일간수익률의 S&P 500 대비 베타가 가장 큰 순", None, beta,
             lambda t: {"베타": R2(beta.get(t)), "연율 변동성 %": R2(vol.get(t))}, slab="베타"),
        pack("size", "중소형", "MSCI USA Size (Mid Cap)",
             "https://www.msci.com/indexes/group/size-indexes",
             "시가총액이 가장 작은 순", None,
             {t: v for t in uni for v in [fund(t, "mc")] if v},
             lambda t: {"시가총액 억$": R2(fund(t, "mc"))}, rev_=True, slab="시가총액 억$"),
    ]

    doc = {
        "note": "스타일별 상위 10종목. 유니버스 518종목(S&P 500 ∪ NASDAQ 100)에 각 스타일 지수의 "
                "공개 방법론을 적용해 이 랩이 직접 계산한 것이며, **해당 지수의 실제 편입 종목이 "
                "아니다.** 지수는 유동시총 가중·상한·회전율 제약·매매 완충구간을 함께 쓰지만 "
                "여기서는 점수 상위 10종목만 그대로 세운다.",
        "warn": "오늘의 화면이지 백테스트가 아니다. 이 랩은 팩터 모멘텀을 '자기 유니버스 대비 "
                "구별 불가'로 기각했다 — 순위를 매수 신호로 읽지 말 것.",
        "as_of": st.get("as_of"), "universe": len(uni), "topn": TOPN,
        "px_window": {"from": dates[0], "to": dates[-1], "n": len(dates)},
        "styles": styles,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s (%dKB)" % (OUT, os.path.getsize(OUT) // 1024))
    for s in styles:
        print("  %-5s %-3d종목 채점 · %s" % (s["label"], s["n_scored"],
                                          " ".join(x["t"] for x in s["top"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
