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

대체한 것 — 숨기지 않고 적는다.
  · 가치의 EV/CFO 를 **EV/EBITDA**로 바꿨다. 랩 패널이 그쪽을 들고 있다(eveb, 커버 93.8%).
  · 이익변동성은 5년 YoY EPS 성장률의 표준편차인데, 랩의 재무 시계열이 분기 20개(약 5년)라
    YoY 관측이 16개다. 정의는 같고 표본이 딱 5년이다.
  · 무위험수익률을 모멘텀 분자에서 빼지 않았다(횡단면 순위에 상수는 영향이 없다).

⚠ 이것은 **오늘의 화면**이지 백테스트가 아니다. 성과를 주장하지 않으며, 이 랩은 팩터 모멘텀을
  '자기 유니버스 대비 구별 불가'로 이미 기각했다. 순위는 상태 표시로만 읽을 것.

⚠ **style_strategies.pdf 와 종목이 다를 수 있다.** 그 문서는 같은 규칙을 과거로 되돌리는
  백테스트라, 오늘치만 있는 벤더 비율(fund.roe·pb·tpe·ps)을 쓸 수 없어 SEC 재무에서 직접
  만든다. 실측(2026-07-29): 모멘텀·저변동·고베타는 상위 10이 정확히 같고, 퀄리티·가치·성장은
  7/10 겹친다. ROE 는 두 출처의 **순위**는 대체로 같지만(스피어만 0.91) **분모 정의가 다르다** —
  야후는 평균 자기자본, 랩은 최신 분기 자기자본이라 자사주 매입 기업의 ROE 가 랩에서 높게
  나온다. 두 문서를 나란히 볼 때는 **재무 기반 스타일의 명단이 갈릴 수 있다는 것을 전제로 읽을 것.**

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

    # 구간 정의(1일·1주·…·1년·YTD)는 style_top_pdf.py 가 정본이다. 여기서 다시 적으면
    # 홈 한 화면 안에서 위 묶음과 아래 묶음의 '3개월'이 다른 날을 가리키는 날이 온다.
    # ⚠ import 만 한다 — 그 모듈은 계산에 numpy 만 쓰고 matplotlib 은 그릴 때만 부른다
    #   (그쪽 파일 머리의 설명). 폰트 없는 러너에서도 이 import 는 안전하다.
    spec2 = importlib.util.spec_from_file_location("_sp", os.path.join(HERE, "style_top_pdf.py"))
    sp = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(sp)

    ISS = issuer_map(uni)

    # ── 랩 스크린 ───────────────────────────────────────────────────
    # 위의 스타일들은 공개 지수 방법론(MSCI·S&P)을 따르지만, 이쪽은 이 랩이 정의한 스크린이다
    # (screener.html). 성격이 달라 홈에서도 따로 묶어 아래에 둔다.
    # ⚠ **점수를 다시 만들지 않는다.** screener.html 이 쓰는 결과가 이미 stocks.json 의
    #   screens 에 구워져 있다(build/screens_apply.py). 산식을 이 파일에 재구현하면
    #   임계·백분위 정의가 갈리는 날 두 화면이 조용히 다른 명단을 말한다.
    # ⚠ 키에 sc_ 를 붙인다. 스크린 키와 스타일 키가 **겹친다** — 스크린 lowvol(저변동 방어주)과
    #   지수 스타일 lowvol(S&P 500 Low Volatility)이 같은 이름이라, 안 붙이면 한쪽이
    #   다른 쪽을 덮어써서 화면에서 조용히 사라진다.
    SCR_DOC = load("screens.json") or {}
    SCR_RES = (st.get("screens") or {})
    SCR_DIR = SCR_DOC.get("dir") or {}
    # 홈의 '상위 10종목' 줄에 싣지 않을 스크린. **스크린을 없애는 것이 아니다** —
    # screener.html 은 screens.json 과 stocks.json 을 직접 읽으므로 그 화면에는 그대로 있다.
    # index.html 의 ST_SCR 과 짝이다. 한쪽만 고치면 style_top.json 에 아무도 안 읽는 줄이
    # 남거나(여기만 두면) 화면에서 조용히 사라진다(저쪽만 빼면).
    SCR_SKIP = {"growth_margin": "자격 통과가 5종뿐이라 10칸 줄에 맞지 않는다"
                                 " — 사용자 결정 2026-08-02"}
    # 스크린이 쓰는 지표의 한글 이름 — 칩 툴팁에 그대로 나간다.
    SCR_LBL = {"fpe": "선행PER", "tpe": "PER", "ps": "PSR", "pb": "PBR", "de": "부채비율 D/E %",
               "beta": "베타", "roe": "ROE %", "pm": "순이익률 %", "rg": "매출성장 %",
               "gr": "선행EPS성장 %", "dy": "배당수익률 %", "fcfy": "FCF수익률 %"}

    def fund(t, k):
        v = (uni[t].get("fund") or {}).get(k)
        return v if isinstance(v, (int, float)) else None

    # 시가총액(억 달러) — 홈의 종목 칩에 마우스를 올렸을 때 이름과 함께 나갈 값이다.
    # 없으면 **None 으로 둔다.** home_flow.py 는 없는 것을 0 으로 채우는데(정렬 키라
    # 숫자여야 한다) 여기는 정렬이 아니라 글로 나가는 자리라, 0 을 쓰면 화면에
    # '시총 0억$' 이라고 적힌 회사가 생긴다. 모르는 것은 그 칸을 빼는 편이 맞다.
    def mc_of(t):
        v = fund(t, "mc")
        return None if v is None else round(float(v))

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

    # ── 스크린 줄의 기간별 수익률 ────────────────────────────────────────────
    # ⚠ 지수 방법론 줄의 수익률(data/style_trails.json)과 **종류가 다른 수치다.**
    #     저쪽 — 월말마다 그 시점 자료로 다시 뽑아 갈아탄 백테스트(style_top_pdf.backtest).
    #     이쪽 — **오늘 뽑힌 열 종목을 1년 전에 사서 그대로 들고 있었다면** 얼마였나.
    #
    #   왜 같은 방식으로 못 하나. 스크린 점수는 벤더 스냅샷 지표(선행PER·선행EPS성장·
    #   배당수익률·FCF수익률 …)의 백분위로 매긴다. 그 값의 **과거 이력이 이 저장소에 없다** —
    #   data/fund_history.json 은 스냅샷이 딱 하나고(2026-07-29) data/estimates.json 도 3일치다.
    #   과거 월말의 점수를 다시 만들 수 없으니 리밸런스를 재현할 방법이 없다.
    #   data/screens.json 의 policy 가 말하는 '사내 PIT 데이터로 돌린 백테스트'가 사내망에만
    #   있는 이유가 정확히 이것이다.
    #
    #   그래서 이 수치는 **룩어헤드다.** 이미 오른 종목이 오늘 스크린에 뽑혔을 수 있고,
    #   그것을 모르는 척 과거로 되돌리는 것이라 좋게 나오게 되어 있다. 숨기지 않는다 —
    #   키 이름을 trails_fixed 로 따로 두고(홈이 백테스트와 다른 꼬리표로 그린다) 문서에
    #   trails_fixed_note 를 함께 싣는다. 같은 이름(trails)을 쓰면 언젠가 둘이 섞인다.
    FIX_WIN = 252

    def fixed_trails(tickers):
        """오늘 명단을 창 시작에 동일가중으로 사서 그대로 둔 곡선의 기간별 수익률 %."""
        end = len(dates) - 1
        start = max(0, end - FIX_WIN)
        rows = []
        for t in tickers:
            a = PX.get(t)
            if a is None:
                continue
            seg = a[start:end + 1]
            if np.isnan(seg[0]) or seg[0] <= 0:
                continue                        # 창 시작에 값이 없으면 그 종목은 뺀다
            rows.append(seg / seg[0])
        if len(rows) < 2:                       # 두 종목 미만이면 '바스켓'이라 부를 수 없다
            return None
        nav = np.nanmean(np.array(rows, float), axis=0)
        # 중간 결측(거래정지 등)은 직전 값으로 끌고 간다. 그대로 두면 그 칸이 NaN 이 되어
        # 뒤의 구간 수익률이 통째로 빈다 — 한 종목의 하루 공백이 1년 칸을 지우면 안 된다.
        for i in range(1, len(nav)):
            if np.isnan(nav[i]):
                nav[i] = nav[i - 1]
        if np.isnan(nav[0]):
            return None
        out = sp.trails(nav, dates, start)
        return {k: (None if v is None or v != v else round(float(v), 2)) for k, v in out.items()}

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
                         "mc": mc_of(t),
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
    # ── 공개 산식 지수 넷 — **정의는 build/style_top_pdf.py 가 정본이다** ─────────────
    # 2026-08-02 사용자 요청("공개 산식이 있는 지수·ETF 를 더 찾아 같은 방식으로").
    # ⚠ 점수 함수를 여기 다시 짜지 않는다. 그 파일의 sc_* 를 **오늘 날짜로 한 번 불러** 쓴다.
    #   산식이 두 곳에 있으면 홈의 10종목과 바로 그 위에 붙는 기간별 수익률이 서로 다른 규칙을
    #   말하는 날이 온다 — 이 파일이 랩 스크린에 대해 이미 지키고 있는 경계와 같은 이유다.
    #   (위 여섯 스타일은 이 파일에 산식이 따로 있다. 그건 이 구조가 생기기 전의 것이고,
    #    합치는 것은 별개의 일이라 여기서 건드리지 않는다.)
    # 방법론 문서 주소만 여기서 준다 — 그쪽 STYLES 는 화면 링크를 들고 있지 않다.
    IDX_URL = {
        "div": "https://www.spglobal.com/spdji/en/indices/dividends-factors/sp-500-high-dividend-index/",
        "buyback": "https://www.spglobal.com/spdji/en/indices/dividends-factors/sp-500-buyback-index/",
        "fcfy": "https://www.paceretfs.com/products/cowz",
        "garp": "https://www.spglobal.com/spdji/en/indices/strategy-indices/sp-500-garp-index/",
    }
    # 정본에서 벗어난 곳. 화면이 칩 옆 ⚠ 로 이것을 낸다 — 근사한 것을 근사했다고 적지 않으면
    # 그냥 그 지수인 척이 된다.
    IDX_SUB = {
        "fcfy": "정본의 분모는 **기업가치(EV)** 인데 여기서는 시가총액을 쓴다 — data/fx 에 "
                "순부채를 만들 태그가 없다(liab 는 매입채무까지 포함한 부채총계다). "
                "금융·부동산 제외는 정본과 같다.",
        "garp": "정본은 성장 상위 150종을 거른 뒤 QV 상위 75종이다. 여기서는 유니버스가 518종이고 "
                "재무 결측으로 채점 가능 종목이 달마다 달라, 개수 대신 **비율(상위 30%)** 로 옮겼다.",
    }
    Pn = sp.Panel()
    ilast = len(Pn.dates) - 1
    for S in sp.STYLES:
        if S[0] not in IDX_URL:
            continue
        key, label, ref, fn, mlab, desc = S[0], S[1], S[2], S[3], S[4], S[6]
        sc, tie = fn(Pn, ilast)
        if not sc:
            print("  ⚠ %s 채점 결과가 없다 — 건너뛴다" % label)
            continue
        styles.append(
            pack(key, label, ref, IDX_URL[key], desc.split("\n")[0], IDX_SUB.get(key),
                 {t: (sc[t], tie.get(t, 0.0)) for t in sc},
                 (lambda d, m: (lambda t: {m: R2(d.get(t))}))(sc, mlab),
                 slab=mlab))

    # 다른 스타일은 공개 지수 방법론을 따르지만 GARP 는 이 랩의 스크린이다 —
    # index_ref 를 지수 이름이 아니라 그 화면으로 적어 출처를 헷갈리지 않게 한다.
    # ⚠ 대응 ETF 가 없다. 홈 성과표는 '랩 규칙 ↔ ETF' 짝만 싣기로 한 화면이라(2026-07-29 결정)
    #   이 스타일은 표에 못 들어가고 구성종목 줄에만 나온다(index.html 의 ST_EXTRA).
    for sk, sc in (SCR_DOC.get("screens") or {}).items():
        if sk in SCR_SKIP:
            print("  · screens.%s 는 홈에 싣지 않는다 — 건너뛴다(%s)" % (sk, SCR_SKIP[sk]))
            continue
        rows = SCR_RES.get(sk) or []
        score = {r["t"]: float(r["s"]) for r in rows
                 if r.get("t") in uni and r.get("s") is not None}
        if not score:
            print("  ⚠ screens.%s 결과가 없다 — 건너뛴다(build/screens_apply.py 가 돌았는지 확인)" % sk)
            continue
        keys = sc.get("keys") or []
        # 조건은 화면과 같은 말로 적는다 — '좋은 쪽 백분위'라는 규약을 여기서 다시 설명하지 않고,
        # 어느 지표가 어느 방향인지만 밝힌다(dir 는 screens.json 이 정본이다).
        cond = " · ".join("%s(%s)" % (SCR_LBL.get(k, k), "낮을수록" if SCR_DIR.get(k) == "low" else "높을수록")
                          for k in keys)
        qual = " · ".join("%s %s" % (SCR_LBL.get(k, k), v)
                          for k, v in (sc.get("qualify") or {}).items())
        qmax = " · ".join("%s %s 이하" % (SCR_LBL.get(k, k), v)
                          for k, v in (sc.get("qualify_max") or {}).items())
        rule = "%s 의 좋은쪽 백분위 평균. 하한 %s 을 넘은 종목만 채점한다." % (cond, qual)
        if qmax:
            rule += " 상한: %s." % qmax
        ent = pack("sc_" + sk, sc.get("name") or sk, "여두 전략 랩 · 스크린",
                   "screener.html#s=" + sk, rule, None, score,
                   (lambda ks: (lambda t: {SCR_LBL.get(k, k): R2(fund(t, k)) for k in ks}))(keys),
                   slab="적합도")
        ent["trails_fixed"] = fixed_trails([x["t"] for x in ent["top"]])
        styles.append(ent)

    doc = {
        "note": "스타일별 상위 10종목. 유니버스 518종목(S&P 500 ∪ NASDAQ 100)에 각 스타일 지수의 "
                "공개 방법론을 적용해 이 랩이 직접 계산한 것이며, **해당 지수의 실제 편입 종목이 "
                "아니다.** 지수는 유동시총 가중·상한·회전율 제약·매매 완충구간을 함께 쓰지만 "
                "여기서는 점수 상위 10종목만 그대로 세운다.",
        "warn": "오늘의 화면이지 백테스트가 아니다. 이 랩은 팩터 모멘텀을 '자기 유니버스 대비 "
                "구별 불가'로 기각했다 — 순위를 매수 신호로 읽지 말 것.",
        "as_of": st.get("as_of"), "universe": len(uni), "topn": TOPN,
        "px_window": {"from": dates[0], "to": dates[-1], "n": len(dates)},
        "trails_fixed_note":
            "스크린 줄에만 있는 trails_fixed 는 **백테스트가 아니다.** 오늘 뽑힌 상위 10종목을 "
            "%d거래일 전에 동일가중으로 사서 그대로 들고 있었다면 얼마였나를 되돌아본 값이다. "
            "종목을 오늘 자료로 골라 놓고 과거를 재므로 **룩어헤드이며 좋게 나오게 되어 있다.** "
            "지수 방법론 줄의 수익률(data/style_trails.json)은 월말마다 그 시점 자료로 다시 뽑는 "
            "백테스트라 종류가 다르다 — 같은 잣대로 비교하지 말 것. 스크린을 같은 방식으로 재려면 "
            "벤더 스냅샷 지표의 과거 이력이 필요한데 이 저장소에는 없다"
            "(data/fund_history.json 스냅샷 1개 · data/estimates.json 3일)." % FIX_WIN,
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
