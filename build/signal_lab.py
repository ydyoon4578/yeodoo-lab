# -*- coding: utf-8 -*-
"""build/signal_lab.py — 지표별 타이밍 신호를 실제로 재서 data/signal_lab.json 을 만든다.

무엇을 푸는가.
  이 사이트는 종목마다 22개 테크니컬 이벤트(RSI 과매도·MACD 골든·돈치안 돌파 …)를 매일
  발동시켜 보여준다. 그런데 **그 신호가 실제로 돈이 됐는지는 아무 데도 없었다.** 쓸 수 있는
  타이밍 신호가 스윙 타점 하나뿐이었던 것도 그래서다 — 나머지는 성적을 몰라 못 쓴다.
  여기서 신호 하나하나를 같은 잣대로 재고, 서로 얼마나 겹치는지까지 낸다.

측정 규약 — 이 랩이 종목 신호에서 이미 데인 함정을 전부 밟지 않도록 짰다.
  · 선견 없음 : 종가로 신호 판정 → **다음 거래일 종가로 진입**.
  · 초과수익  : 종목 수익 − β×(동일가중 유니버스 수익). β는 그 시점까지의 120일로만 추정한다.
                β를 안 빼면 고베타 종목이 많이 걸리는 신호가 전부 좋아 보인다.
  · 에피소드 중복제거 : 같은 종목이 보유기간 안에 다시 발동해도 **한 건으로 센다**. 이걸 안 하면
                한 번의 급등을 수십 건으로 세어 t값이 부풀려진다(실측 3배).
  · 상위 5% 제외 : 소수 대박이 평균을 만드는지 함께 낸다. 둘이 크게 다르면 그 신호는 못 쓴다.
  · 다중검정  : 신호 전부를 같은 표본에서 쟀으므로 본페로니로 임계를 올린다.

한계는 결과와 함께 싣는다(생존편향·3년 표본·비용 0). 좋은 것만 고르지 않고 전부 게시한다.

  python build/signal_lab.py
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 지표 함수는 **게시 파이프라인에서 그대로 가져온다**. 여기서 다시 구현하면 화면에 보이는 신호와
# 여기서 재는 신호가 소리 없이 갈라진다(같은 이름의 다른 규칙이 된다).
from refresh_stocks import rsi, macd, boll, stoch_k, adx, cci, willr, mfi, aroon, sma  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_SD = os.path.join(DATA, "sd")
OUT = os.path.join(DATA, "signal_lab.json")

HOR = (5, 10, 20)      # 보유기간(거래일)
PRIMARY = 20           # 판정에 쓰는 기간
BETA_WIN = 120
MIN_HIST = 260         # 200MA·Aroon 워밍업
MIN_EVENTS = 30        # 이보다 적으면 판정하지 않는다(표본 부족을 '무판정'으로 남긴다)
RECENT = 5             # '오늘 발동' 창(거래일)


def cu(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def cd(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


# ── 신호 정의 ───────────────────────────────────────────────────────────
# fn(h, l, c, v, X) -> bool Series.  X = 미리 계산해 둔 공통 지표 묶음(중복 계산 방지).
# dirn: 'buy'는 초과수익이 +여야 맞는 신호, 'sell'은 −여야 맞는 신호다.
SIGNALS = []


def sig(sid, name, ind, dirn, rule, why, fn, fired=None):
    SIGNALS.append({"sid": sid, "name": name, "ind": ind, "dir": dirn,
                    "rule": rule, "why": why, "fn": fn,
                    "fired": fired or name})


def build_signals():
    # ── 오실레이터: 과매도/과매수 원형 ──
    sig("rsi-os", "RSI 과매도 (<30)", "RSI", "buy",
        "RSI(14)가 30 아래로 내려간 날.",
        "가장 널리 쓰이는 역추세 신호. 이 랩은 종목 신호에서 역추세를 이미 폐기했는데, "
        "지표별로 다시 재면 정말 전부 못 쓰는지 아니면 일부만 그런지 갈린다.",
        lambda h, l, c, v, X: X["rsi"] < 30)
    sig("rsi-ob", "RSI 과매수 (>70)", "RSI", "sell",
        "RSI(14)가 70 위로 올라간 날.",
        "과매수를 팔 자리로 보는 관례. 상승추세에서 RSI는 오래 높게 머문다 — 그게 비용인지 본다.",
        lambda h, l, c, v, X: X["rsi"] > 70)
    sig("rsi-pull", "추세정렬 RSI 눌림 (200MA 위 & RSI<45 반등)", "RSI", "buy",
        "종가가 200일선 위인 상태에서 RSI(14)가 45 아래였다가 3일 전보다 올라선 날.",
        "같은 RSI를 '떨어지는 칼'이 아닌 곳에서만 쓴다. 추세정렬이 역추세를 살리는지 재는 짝.",
        lambda h, l, c, v, X: X["up"] & (X["rsi"] < 45) & (X["rsi"] > X["rsi"].shift(3)))

    # ── MACD ──
    sig("macd-gold", "MACD 골든크로스 (0선 아래)", "MACD", "buy",
        "MACD선이 신호선을 아래에서 위로 뚫었고, 그 자리가 0선 아래인 날.",
        "0선 아래 골든은 '바닥에서의 전환'으로 읽힌다. 0선 위 교차와 갈라 재야 의미가 보인다.",
        lambda h, l, c, v, X: cu(X["ml"], X["ms"]) & (X["ml"] < 0))
    sig("macd-zup", "MACD 0선 상향", "MACD", "buy",
        "MACD선이 0을 위로 통과한 날(중기 추세 전환).",
        "교차보다 늦지만 덜 속는다고 알려진 신호. 늦은 만큼 손해인지 이득인지 잰다.",
        lambda h, l, c, v, X: cu(X["ml"], X["z"]))
    sig("macd-dead", "MACD 데드크로스 (0선 위)", "MACD", "sell",
        "MACD선이 신호선을 위에서 아래로 뚫었고, 그 자리가 0선 위인 날.",
        "고점권 이탈 신호. 상승추세 중 흔들림과 진짜 전환을 가르는지 본다.",
        lambda h, l, c, v, X: cd(X["ml"], X["ms"]) & (X["ml"] > 0))
    sig("macd-zdn", "MACD 0선 하향", "MACD", "sell",
        "MACD선이 0을 아래로 통과한 날.",
        "0선 상향의 대칭. 매수·매도 대칭이 실제로 성립하는지가 관전 포인트다.",
        lambda h, l, c, v, X: cd(X["ml"], X["z"]))

    # ── 스토캐스틱 ──
    sig("stoch-gold", "스토캐스틱 %K<25 골든", "스토캐스틱", "buy",
        "%K가 %D를 상향 돌파했고 %K가 25 아래인 날.",
        "단기 과매도 반등을 잡는 대표 신호. 회전이 매우 잦아 비용에 민감하다.",
        lambda h, l, c, v, X: cu(X["k"], X["kd"]) & (X["k"] < 25))
    sig("stoch-dead", "스토캐스틱 %K>75 데드", "스토캐스틱", "sell",
        "%K가 %D를 하향 돌파했고 %K가 75 위인 날.",
        "위 신호의 대칭판.",
        lambda h, l, c, v, X: cd(X["k"], X["kd"]) & (X["k"] > 75))

    # ── 볼린저 ──
    sig("bb-lower", "볼린저 하단 이탈 (%b<0)", "볼린저", "buy",
        "종가가 볼린저 하단(20일·2σ) 아래로 내려간 날.",
        "밴드 이탈을 되돌림으로 볼 것인가 이탈로 볼 것인가 — 이 표에서 답이 갈린다.",
        lambda h, l, c, v, X: X["pb"] < 0)
    sig("bb-upper", "볼린저 상단 돌파 (%b>1)", "볼린저", "sell",
        "종가가 볼린저 상단 위로 올라간 날.",
        "'과열이니 판다'는 해석과 '강해서 뚫었다'는 해석이 정반대다. 부호로 판정된다.",
        lambda h, l, c, v, X: X["pb"] > 1)
    sig("bb-squeeze", "볼린저 스퀴즈 상단 돌파", "볼린저", "buy",
        "밴드폭이 최근 1년 하위 20%로 좁아진 뒤 종가가 상단을 넘은 날.",
        "변동성 수축 뒤의 팽창을 노리는 규칙. 이탈 방향을 미리 알 수 없다는 게 약점이다.",
        lambda h, l, c, v, X: (X["bw"] <= X["bw"].rolling(252, min_periods=120).quantile(0.20)) & (X["pb"] > 1))

    # ── 나머지 오실레이터 ──
    sig("cci-os", "CCI < −100", "CCI", "buy",
        "CCI(20)가 −100 아래인 날.",
        "RSI·스토캐스틱과 같은 과매도 계열. 세 개가 서로 다른 것을 보는지 중복도에서 드러난다.",
        lambda h, l, c, v, X: X["cci"] < -100)
    sig("cci-ob", "CCI > +100", "CCI", "sell",
        "CCI(20)가 +100 위인 날.", "위의 대칭판.",
        lambda h, l, c, v, X: X["cci"] > 100)
    sig("wr-os", "Williams %R < −80", "Williams %R", "buy",
        "Williams %R(14)이 −80 아래인 날.",
        "사실상 스토캐스틱의 뒤집은 값이다 — 중복도가 그 사실을 드러내는지 본다.",
        lambda h, l, c, v, X: X["wr"] < -80)
    sig("wr-ob", "Williams %R > −20", "Williams %R", "sell",
        "Williams %R(14)이 −20 위인 날.", "위의 대칭판.",
        lambda h, l, c, v, X: X["wr"] > -20)
    sig("mfi-os", "MFI < 20", "MFI", "buy",
        "MFI(14)가 20 아래인 날(거래량 가중 과매도).",
        "가격만 보는 RSI에 거래량을 더한 것. 거래량이 정보를 더하는지가 쟁점이다.",
        lambda h, l, c, v, X: X["mfi"] < 20)
    sig("mfi-ob", "MFI > 80", "MFI", "sell",
        "MFI(14)가 80 위인 날.", "위의 대칭판.",
        lambda h, l, c, v, X: X["mfi"] > 80)

    # ── 추세·돌파 ──
    sig("ma-golden", "골든크로스 (50/200)", "이동평균", "buy",
        "50일선이 200일선을 상향 돌파한 날.",
        "가장 유명한 매수 신호. 유명한 만큼 이미 소진됐는지가 관심사다.",
        lambda h, l, c, v, X: cu(X["s50"], X["s200"]))
    sig("ma-death", "데드크로스 (50/200)", "이동평균", "sell",
        "50일선이 200일선을 하향 돌파한 날.", "위의 대칭판.",
        lambda h, l, c, v, X: cd(X["s50"], X["s200"]))
    sig("ma200-reclaim", "200일선 회복", "이동평균", "buy",
        "종가가 200일선을 아래에서 위로 넘은 날.",
        "골든크로스보다 훨씬 빠르다. 빠른 만큼 속임수도 많은지 잰다.",
        lambda h, l, c, v, X: (c > X["s200"]) & (c.shift(1) <= X["s200"].shift(1)))
    sig("ma200-lose", "200일선 이탈", "이동평균", "sell",
        "종가가 200일선을 위에서 아래로 뚫은 날.", "위의 대칭판.",
        lambda h, l, c, v, X: (c < X["s200"]) & (c.shift(1) >= X["s200"].shift(1)))
    sig("donch-up", "돈치안 20일 상향 돌파", "돈치안", "buy",
        "종가가 직전 20일 최고가 이상으로 마감한 날.",
        "터틀 트레이딩의 원형. 시장 단위 돈치안은 전략 랩에서 열위였다 — 종목 단위는 다른지 본다.",
        lambda h, l, c, v, X: c >= X["dcu"].shift(1))
    sig("donch-dn", "돈치안 20일 하향 이탈", "돈치안", "sell",
        "종가가 직전 20일 최저가 이하로 마감한 날.", "위의 대칭판.",
        lambda h, l, c, v, X: c <= X["dcl"].shift(1))
    sig("aroon-up", "Aroon 업 교차", "Aroon", "buy",
        "Aroon Up이 Aroon Down을 상향 돌파한 날(25일 기준).",
        "고점·저점이 얼마나 최근이었는지만 보는 지표. 가격 수준을 안 보는 점이 다르다.",
        lambda h, l, c, v, X: cu(X["au"], X["ad"]))
    sig("aroon-dn", "Aroon 다운 교차", "Aroon", "sell",
        "Aroon Down이 Aroon Up을 상향 돌파한 날.", "위의 대칭판.",
        lambda h, l, c, v, X: cd(X["au"], X["ad"]))

    # ── 추세 강도·거래량 ──
    sig("adx-trend", "ADX 추세 발화 (상승)", "ADX", "buy",
        "ADX(14)가 25를 위로 넘었고 그날 종가가 200일선 위인 날.",
        "방향이 아니라 '추세가 있는가'를 재는 지표. 방향 필터와 묶어야 뜻이 생긴다.",
        lambda h, l, c, v, X: cu(X["adx"], X["c25"]) & X["up"])
    sig("adx-break", "ADX 추세 발화 (하락)", "ADX", "sell",
        "ADX(14)가 25를 위로 넘었고 그날 종가가 200일선 아래인 날.", "위의 대칭판.",
        lambda h, l, c, v, X: cu(X["adx"], X["c25"]) & (~X["up"]))
    sig("vol-surge", "거래량 급증 + 상승추세", "거래량", "buy",
        "5일 평균거래량이 60일 평균의 2배를 넘었고 종가가 200일선 위인 날.",
        "'무엇이 일어났다'는 신호. 방향은 추세 필터가 준다.",
        lambda h, l, c, v, X: (X["rvol"] > 2.0) & X["up"])
    sig("vol-dry", "거래량 급증 + 하락추세", "거래량", "sell",
        "5일 평균거래량이 60일 평균의 2배를 넘었고 종가가 200일선 아래인 날.", "위의 대칭판.",
        lambda h, l, c, v, X: (X["rvol"] > 2.0) & (~X["up"]))

    # ── 스윙(기존 게시 신호)과의 대조 ──
    sig("hi-52w", "52주 신고가", "가격위치", "buy",
        "종가가 최근 252거래일 최고가 이상인 날.",
        "'신고가는 더 간다' vs '고점이다'가 정면으로 갈리는 자리. 화면의 스윙 타점과 대조군이 된다.",
        lambda h, l, c, v, X: c >= c.rolling(252, min_periods=200).max())
    sig("lo-52w", "52주 신저가", "가격위치", "sell",
        "종가가 최근 252거래일 최저가 이하인 날.", "위의 대칭판.",
        lambda h, l, c, v, X: c <= c.rolling(252, min_periods=200).min())


def prep(h, l, c, v):
    """공통 지표 — 신호마다 다시 계산하면 32번 중복된다."""
    ml, ms, _mh = macd(c)
    _, _bu, _bl, pb, bw = boll(c)
    k = stoch_k(h, l, c)
    ax, _p, _m = adx(h, l, c)
    au, ad = aroon(h, l)
    s200 = sma(c, 200)
    rv = v.rolling(5).mean() / v.rolling(60).mean()
    return {
        "rsi": rsi(c), "ml": ml, "ms": ms, "z": pd.Series(0.0, index=c.index),
        "pb": pb, "bw": bw, "k": k, "kd": k.rolling(3).mean(),
        "cci": cci(h, l, c), "wr": willr(h, l, c), "mfi": mfi(h, l, c, v),
        "s50": sma(c, 50), "s200": s200, "up": c > s200,
        "dcu": h.rolling(20).max(), "dcl": l.rolling(20).min(),
        "au": au, "ad": ad, "adx": ax, "c25": pd.Series(25.0, index=c.index),
        "rvol": rv,
    }


def tstat_p(t, df):
    """양측 p값 근사(정규 근사 — n이 30 이상일 때만 쓴다)."""
    if t is None or t != t:
        return None
    z = abs(t)
    return round(2 * 0.5 * math.erfc(z / math.sqrt(2)), 5)


def z_of(p):
    """양측 p에 대응하는 |z| — 본페로니 임계용."""
    lo, hi = 0.0, 12.0
    for _ in range(200):
        m = (lo + hi) / 2
        if math.erfc(m / math.sqrt(2)) > p:
            lo = m
        else:
            hi = m
    return round((lo + hi) / 2, 2)


def run():
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    n = len(dates)
    idx = pd.to_datetime(dates)

    px, hi, lo, vo, names, sect = {}, {}, {}, {}, {}, {}
    miss_hl = []
    for s in st["stocks"]:
        t = s["t"]
        p = os.path.join(DIR_SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        a, hh, ll, vv = d.get("pxd"), d.get("hd"), d.get("ld"), d.get("vd")
        if not (isinstance(a, list) and len(a) == n):
            continue
        if not (isinstance(hh, list) and isinstance(ll, list) and len(hh) == n and len(ll) == n):
            miss_hl.append(t)
            continue
        px[t] = pd.Series(a, index=idx, dtype="float64")
        hi[t] = pd.Series(hh, index=idx, dtype="float64")
        lo[t] = pd.Series(ll, index=idx, dtype="float64")
        vo[t] = pd.Series(vv if isinstance(vv, list) and len(vv) == n else [np.nan] * n,
                          index=idx, dtype="float64")
        names[t] = s.get("name") or t
        sect[t] = s.get("sector") or ""
    tick = sorted(px)
    if not tick:
        print("❌ 시계열을 읽지 못했다 — data/sd 확인"); return 1
    print("종목 %d · %s ~ %s (%d거래일)%s"
          % (len(tick), dates[0], dates[-1], n,
             ("  · 고저가 없어 제외 %d종목" % len(miss_hl)) if miss_hl else ""))

    P = pd.DataFrame({t: px[t] for t in tick})
    R = P.pct_change()
    bench = R.mean(axis=1)                      # 동일가중 유니버스 일간수익
    bcum = (1 + bench.fillna(0)).cumprod()

    # 롤링 β — 그 시점까지의 120일만 쓴다(선견 없음)
    bvar = bench.rolling(BETA_WIN, min_periods=60).var()
    BETA = {t: (R[t].rolling(BETA_WIN, min_periods=60).cov(bench) / bvar).clip(0.0, 3.0)
            for t in tick}

    build_signals()
    fwd_s = {H: P.shift(-H - 1) / P.shift(-1) - 1 for H in HOR}       # 다음날 진입 → H일 보유
    fwd_b = {H: bcum.shift(-H - 1) / bcum.shift(-1) - 1 for H in HOR}

    # 종목별 신호 발동 행렬
    ev = {S["sid"]: {} for S in SIGNALS}
    for t in tick:
        c, h, l, v = P[t], hi[t], lo[t], vo[t]
        if c.notna().sum() < MIN_HIST:
            continue
        X = prep(h, l, c, v)
        for S in SIGNALS:
            try:
                b = S["fn"](h, l, c, v, X)
            except Exception:
                continue
            b = b.fillna(False).astype(bool)
            b.iloc[:MIN_HIST] = False           # 워밍업 구간은 신호로 세지 않는다
            if b.any():
                ev[S["sid"]][t] = b

    EXC = pd.DataFrame({t: (fwd_s[PRIMARY][t] - BETA[t] * fwd_b[PRIMARY]) * 100 for t in tick})
    EXC.iloc[:MIN_HIST] = np.nan

    # ── 귀무 기준선 ────────────────────────────────────────────────────
    # '아무 날 아무 종목'의 같은 초과수익. 평균은 0 근처지만 **상위 5%를 뺀 평균은 그렇지 않다** —
    # 주식 수익 분포가 오른쪽으로 길어서, 위쪽 꼬리를 자르면 무엇이든 크게 음수가 된다.
    # 그래서 '상위 5% 제외' 값은 이 기준선과 비교해야 뜻이 생긴다. 안 그러면 모든 신호가
    # 엉망으로 보이는데, 그건 신호의 성질이 아니라 자르기의 성질이다.
    _flat = EXC.to_numpy().ravel()
    _flat = _flat[~np.isnan(_flat)]
    _cut0 = np.sort(_flat)[:max(1, int(len(_flat) * 0.95))]
    BASE = {"n": int(len(_flat)),
            "mean": round(float(_flat.mean()), 3),
            "med": round(float(np.median(_flat)), 3),
            "hit": round(100 * float((_flat > 0).mean()), 1),
            "ex_top5": round(float(_cut0.mean()), 3)}
    print("귀무 기준선 — 평균 %+.3f%% · 적중 %.1f%% · 상위5%%제외 %+.3f%% (n=%d)"
          % (BASE["mean"], BASE["hit"], BASE["ex_top5"], BASE["n"]))


    out = []
    firing = {}
    for S in SIGNALS:
        rows = []          # 에피소드 중복제거 후의 사건들
        today = []
        for t, b in ev[S["sid"]].items():
            pos = np.flatnonzero(b.to_numpy())
            if not len(pos):
                continue
            if pos[-1] >= n - RECENT:
                today.append((t, dates[int(pos[-1])], int(n - 1 - pos[-1])))
            last = -10 ** 9
            for i in pos:
                if i - last < PRIMARY:          # ── 에피소드 중복제거 ──
                    continue
                last = i
                bt = BETA[t].iloc[i]
                if bt != bt:
                    continue
                r = {}
                okall = True
                for H in HOR:
                    a = fwd_s[H][t].iloc[i]
                    m = fwd_b[H].iloc[i]
                    if a != a or m != m:
                        okall = False
                        break
                    r[H] = (a - bt * m) * 100    # β조정 초과수익(%)
                if okall:
                    r["i"] = int(i)
                    rows.append(r)
        firing[S["sid"]] = sorted(today, key=lambda x: x[2])

        rec = {"sid": S["sid"], "name": S["name"], "ind": S["ind"], "dir": S["dir"],
               "rule": S["rule"], "why": S["why"], "n": len(rows),
               "n_today": len(today)}
        if len(rows) >= MIN_EVENTS:
            for H in HOR:
                xs = np.array([r[H] for r in rows], float)
                mu = float(xs.mean())
                sd = float(xs.std(ddof=1))
                t_ = mu / (sd / math.sqrt(len(xs))) if sd > 0 else None
                cut = np.sort(xs)[:max(1, int(len(xs) * 0.95))]     # 상위 5% 제외
                rec["h%d" % H] = {
                    "mean": round(mu, 3), "med": round(float(np.median(xs)), 3),
                    "hit": round(100 * float((xs > 0).mean()), 1),
                    "t": round(t_, 2) if t_ is not None else None,
                    "p": tstat_p(t_, len(xs) - 1),
                    "ex_top5": round(float(cut.mean()), 3),
                }
            # ── 서브기간 ── 표본을 반으로 갈라 같은 부호가 두 번 나오는지 본다.
            # 부호가 갈리면 그 신호는 '구간의 성질'이지 신호가 아니다. 특히 아래에서
            # 관례와 반대 방향으로 유의한 신호를 다룰 때, 이 검사 없이는 사후 해석에 불과하다.
            mid = MIN_HIST + (n - MIN_HIST) // 2
            for lab, sel in (("h1", [r for r in rows if r["i"] < mid]),
                             ("h2", [r for r in rows if r["i"] >= mid])):
                if len(sel) < 15:
                    rec[lab] = None
                    continue
                xs = np.array([r[PRIMARY] for r in sel], float)
                sd = float(xs.std(ddof=1))
                tt = float(xs.mean()) / (sd / math.sqrt(len(xs))) if sd > 0 else None
                rec[lab] = {"n": len(sel), "mean": round(float(xs.mean()), 3),
                            "t": round(tt, 2) if tt is not None else None}
        out.append(rec)

    # ── 판정 ──────────────────────────────────────────────────────────
    judged = [r for r in out if ("h%d" % PRIMARY) in r]
    tcrit = z_of(0.05 / max(1, len(judged)))
    for r in out:
        m = r.get("h%d" % PRIMARY)
        if not m:
            r["verdict"] = "표본 부족"
            r["use"] = "판정에 필요한 사건 수(%d건)에 못 미친다 — 쓰지 않는다." % MIN_EVENTS
            continue
        want = 1 if r["dir"] == "buy" else -1
        big = m["t"] is not None and abs(m["t"]) >= tcrit
        agree = m["t"] is not None and (m["t"] * want) > 0
        # 상위 5%를 빼도 **귀무보다 나은 쪽**에 남는가.
        # ⚠ 절대 부호로 보면 안 된다 — 주식 수익은 오른쪽으로 길어서 위 꼬리를 자르면
        #   무엇이든 크게 음수가 된다(귀무 자체가 그렇다). 자르기의 성질을 신호의 결함으로
        #   읽으면 전부 탈락한다. 그래서 귀무의 같은 처리값과 비교한다.
        edge_raw = m["mean"] - BASE["mean"]
        edge_cut = m["ex_top5"] - BASE["ex_top5"]
        m["vs_base"] = round(edge_cut, 3)
        robust = (edge_cut * edge_raw) > 0
        # 서브기간 두 곳에서 같은 부호가 나오는가
        h1, h2 = r.get("h1"), r.get("h2")
        consist = bool(h1 and h2 and (h1["mean"] * h2["mean"]) > 0)
        r["consistent"] = consist
        if big and agree and robust:
            r["verdict"] = "관례대로 유효"
            r["use"] = "관례가 말하는 방향으로 통계 문턱을 넘었다. 그대로 쓴다."
        elif big and agree and not robust:
            r["verdict"] = "소수 사건 의존"
            r["use"] = ("평균은 문턱을 넘지만, 상위 5% 사건을 빼면 귀무보다 나은 쪽에 남지 못한다 "
                        "— 그 몇 건을 못 잡으면 없는 엣지다.")
        elif big and not agree:
            # 관례와 반대로 유의 — 이 랩에서 가장 쓸모 있는 칸이자 가장 위험한 칸이다.
            r["verdict"] = "관례와 반대로 유의"
            r["use"] = ("관례와 '반대 방향'으로 문턱을 넘었다. 뒤집으면 쓸 수 있다는 뜻이지만, "
                        "방향을 결과를 보고 정했으므로 발견이 아니라 가설이다. "
                        + ("표본을 반으로 갈랐을 때 두 구간 모두 같은 부호였다 — 가설이 살아 있다."
                           if consist else
                           "표본을 반으로 가르면 부호가 갈린다 — 구간의 성질일 가능성이 크다."))
        else:
            r["verdict"] = "구별 불가"
            r["use"] = "귀무(아무 날 아무 종목)와 구별되지 않는다. 단독으로는 쓸 근거가 없다."

    # ── 중복도(자카드) ── 같은 (종목, 날짜)에 함께 뜨는 정도. 방향이 같은 신호끼리만 비교한다.
    sets = {}
    for S in SIGNALS:
        s_ = set()
        for t, b in ev[S["sid"]].items():
            for i in np.flatnonzero(b.to_numpy()):
                s_.add((t, int(i)))
        sets[S["sid"]] = s_
    pairs = []
    for i in range(len(SIGNALS)):
        for j in range(i + 1, len(SIGNALS)):
            A, B = SIGNALS[i], SIGNALS[j]
            if A["dir"] != B["dir"]:
                continue
            a, b = sets[A["sid"]], sets[B["sid"]]
            if not a or not b:
                continue
            u = len(a | b)
            if not u:
                continue
            pairs.append({"a": A["name"], "b": B["name"],
                          "j": round(len(a & b) / u, 3)})
    pairs.sort(key=lambda x: -x["j"])

    # ── 합의(동시 발동) ────────────────────────────────────────────────
    # 단독 신호 하나는 원래 약하다. 실제로 쓸 수 있는지는 **여러 신호가 같은 날 같은 종목에
    # 겹칠 때** 갈린다. 매수 신호 수 − 매도 신호 수를 그날 그 종목의 '순합의'로 정의하고,
    # 순합의 구간별로 20일 초과수익을 잰다. 이 표가 단조로우면(합의가 셀수록 좋으면)
    # 신호를 겹쳐 쓰는 게 실제로 뜻이 있다는 말이고, 들쭉날쭉하면 겹쳐도 소용없다는 말이다.
    #
    # t값은 **날짜로 군집화**해서 낸다. 같은 날 여러 종목이 함께 움직이므로 종목 단위로
    # 세면 표본이 실제보다 훨씬 크다고 착각하게 된다. 보유기간 20일이 겹치는 것은
    # Newey-West(lag 20)로 잡는다.
    def newey_west_t(x, lag=PRIMARY):
        x = np.asarray(x, float)
        x = x[~np.isnan(x)]
        m = len(x)
        if m < 30:
            return None
        mu = x.mean()
        d = x - mu
        g0 = float((d * d).sum() / m)
        var = g0
        for k in range(1, min(lag, m - 1) + 1):
            gk = float((d[k:] * d[:-k]).sum() / m)
            var += 2 * (1 - k / (lag + 1)) * gk
        if var <= 0:
            return None
        return round(mu / math.sqrt(var / m), 2)

    BUYS = [S["sid"] for S in SIGNALS if S["dir"] == "buy"]
    SELLS = [S["sid"] for S in SIGNALS if S["dir"] == "sell"]
    zero = pd.Series(0, index=idx, dtype="int16")
    netmat, nbuymat = {}, {}
    for t in tick:
        nb = zero.copy()
        ns = zero.copy()
        for sid in BUYS:
            b = ev[sid].get(t)
            if b is not None:
                nb = nb + b.astype("int16")
        for sid in SELLS:
            b = ev[sid].get(t)
            if b is not None:
                ns = ns + b.astype("int16")
        nbuymat[t] = nb
        netmat[t] = nb - ns
    NET = pd.DataFrame(netmat)
    NB = pd.DataFrame(nbuymat)

    def bucket_table(M, edges, labels):
        rows = []
        for (lo_, hi_), lab in zip(edges, labels):
            sel = (M >= lo_) & (M <= hi_)
            vals = EXC.where(sel)
            daily = vals.mean(axis=1)                      # 날짜별 횡단면 평균(군집화)
            d = daily.dropna()
            # ⚠ 적중률은 **선택된 칸만** 분모로 삼는다. vals에는 미선택 칸이 NaN으로 남아 있고
            #   NaN > 0 은 False라, 전체 칸으로 평균 내면 적중률이 통째로 낮게 나온다(실측 12.6%).
            flat = vals.to_numpy()
            flat = flat[~np.isnan(flat)]
            cnt = int(len(flat))
            rows.append({
                "lab": lab, "n": cnt, "n_days": int(len(d)),
                "mean": round(float(flat.mean()), 3) if cnt else None,
                "t": newey_west_t(d.to_numpy()) if len(d) >= 30 else None,
                "hit": round(100 * float((flat > 0).mean()), 1) if cnt else None,
            })
        return rows

    net_edges = [(-99, -3), (-2, -2), (-1, -1), (0, 0), (1, 1), (2, 2), (3, 3), (4, 99)]
    net_labels = ["−3 이하", "−2", "−1", "0", "+1", "+2", "+3", "+4 이상"]
    buy_edges = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 99)]
    buy_labels = ["0개", "1개", "2개", "3개", "4개 이상"]
    cons = {
        "net": bucket_table(NET, net_edges, net_labels),
        "nbuy": bucket_table(NB, buy_edges, buy_labels),
        "note": "순합의 = 그날 그 종목에서 발동한 매수 신호 수 − 매도 신호 수. "
                "구간별 20일 β조정 초과수익(%%)이다. t는 날짜로 군집화하고 보유기간 겹침을 "
                "Newey-West(lag %d)로 보정했다 — 종목 단위로 세면 표본을 수십 배로 착각한다." % PRIMARY,
    }
    # 오늘의 순합의 상·하위
    last = NET.iloc[-1]
    cons["today"] = {
        "dt": dates[-1],
        "top": [{"t": t, "n": names.get(t, t), "s": sect.get(t, ""), "v": int(last[t]),
                 "b": int(NB.iloc[-1][t])}
                for t in last.sort_values(ascending=False).index[:40] if last[t] >= 2],
        "bot": [{"t": t, "n": names.get(t, t), "s": sect.get(t, ""), "v": int(last[t]),
                 "b": int(NB.iloc[-1][t])}
                for t in last.sort_values().index[:40] if last[t] <= -2],
    }

    # ── 실제 포트폴리오로 확정 ──────────────────────────────────────────
    # 여기까지는 '신호 발동 후 평균'이다. 그건 매매가 아니다. 합의 순위를 실제 포트폴리오로
    # 굴려 본다 — **월말 리밸런스·동일가중·무비용**, 이 랩의 기본 규약 그대로다.
    # 지표 정의(CAGR·샤프·MDD·t)는 build/tech_backtest.py와 같은 식을 쓴다. 다르면 두 표를
    # 나란히 놓고 비교할 수 없다.
    from tech_backtest import ann_stats, tstat as _tstat   # 정의를 복제하지 않는다

    rf_m = json.load(io.open(os.path.join(DATA, "rf_monthly.json"),
                             encoding="utf-8")).get("monthly") or {}
    month_end = [i for i in range(MIN_HIST, n - 1)
                 if dates[i][:7] != dates[i + 1][:7]]
    TOPN = 50

    def port(rank_df, asc, label, rule, why):
        """월말에 rank_df 상위(또는 하위) TOPN을 동일가중 보유."""
        hold, navs, rets, turns = [], [100.0], [], 0
        for i in range(MIN_HIST + 1, n):
            if i - 1 in month_end:
                row = rank_df.iloc[i - 1].dropna()
                if len(row) >= TOPN:
                    new = list(row.sort_values(ascending=asc).index[:TOPN])
                    turns += len(set(new) - set(hold))
                    hold = new
            rs = [R[t].iloc[i] for t in hold if R[t].iloc[i] == R[t].iloc[i]]
            r = sum(rs) / len(rs) if rs else 0.0
            rets.append(r)
            navs.append(navs[-1] * (1 + r))
        bn = [100.0]
        brs = []
        for i in range(MIN_HIST + 1, n):
            r = bench.iloc[i]
            r = 0.0 if r != r else float(r)
            brs.append(r)
            bn.append(bn[-1] * (1 + r))
        dd = dates[MIN_HIST:]
        ms, mb = ann_stats(navs, dd, rf_m), ann_stats(bn, dd, rf_m)
        yrs = max(1e-9, (n - MIN_HIST) / 252)
        return {"name": label, "rule": rule, "why": why,
                "metrics": ms, "bench": mb,
                "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
                "t": _tstat(rets, brs),
                "turnover": round(turns / TOPN / yrs, 1),
                "nav": [round(x, 2) for x in navs[::5]],
                "bnav": [round(x, 2) for x in bn[::5]]}

    ports = [
        port(NET, False, "신호 합의 상위 50 (관례 방향)",
             "월말에 순합의(매수신호 − 매도신호)가 가장 높은 50종목을 동일가중 보유.",
             "교과서대로라면 매수 신호가 몰린 종목이 좋아야 한다. 그 명제를 포트폴리오로 직접 건다."),
        port(NET, True, "신호 합의 하위 50 (역방향)",
             "월말에 순합의가 가장 낮은(매도 신호가 몰린) 50종목을 동일가중 보유.",
             "위와 정반대. 개별 신호 표에서 매수 신호들이 일관되게 음(−)이었으므로, "
             "그 방향이 포트폴리오에서도 살아남는지 본다. ⚠ 방향을 결과를 보고 정했다 — 가설이다."),
        port(NB, False, "매수 신호 최다 50",
             "월말에 매수 신호가 가장 많이 발동한 50종목을 동일가중 보유(매도 신호는 무시).",
             "순합의에서 매도 쪽을 빼면 달라지는지 — '매수 신호만 세는' 흔한 사용법의 검증."),
    ]

    nm = {S["sid"]: S["name"] for S in SIGNALS}
    doc = {
        "note": "지표별 타이밍 신호를 같은 잣대로 잰 결과. 좋은 것만 고르지 않고 전부 싣는다.",
        "as_of": dates[-1], "start": dates[MIN_HIST], "n_days": n, "n_stocks": len(tick),
        "horizons": list(HOR), "primary": PRIMARY, "t_crit": tcrit,
        "bench": "동일가중 유니버스(β조정)",
        "protocol": [
            "종가로 신호를 판정하고 다음 거래일 종가로 진입한다(선견 없음).",
            "초과수익 = 종목 수익 − β×유니버스 수익. β는 그 시점까지의 120일로만 추정한다 — "
            "안 빼면 고베타 종목이 잘 걸리는 신호가 전부 좋아 보인다.",
            "같은 종목이 보유기간(%d거래일) 안에 다시 발동해도 한 건으로 센다. "
            "이 중복제거를 안 하면 한 번의 급등이 수십 건으로 세어져 t값이 부풀려진다." % PRIMARY,
            "상위 5%% 사건을 뺀 평균을 함께 낸다. 부호가 뒤집히면 '소수 사건 의존'으로 판정하고 "
            "통과시키지 않는다.",
            "신호 %d개를 같은 표본에서 쟀으므로 본페로니로 임계를 |t|≥%.2f로 올렸다."
            % (len(judged), tcrit),
            "표본이 %d건 미만이면 판정하지 않고 '표본 부족'으로 남긴다." % MIN_EVENTS,
        ],
        "limits": [
            "생존편향 — 오늘의 %d종목을 과거에 그대로 적용한다. 그 사이 상장폐지·편출된 종목이 "
            "없어 모든 수치가 실제보다 좋게 나온다." % len(tick),
            "표본이 3년뿐이고 그중 대부분이 강세장이다. 매도 신호는 특히 불리한 구간이다.",
            "비용 0(gross). 발동이 잦은 신호일수록 실제와 벌어진다 — 건수를 함께 본다.",
            "여기 수치는 '신호 발동 후 %d거래일 평균'이지 매매 전략의 수익률이 아니다. "
            "언제 팔지는 이 표가 답하지 않는다." % PRIMARY,
        ],
        "signals": out,
        "consensus": cons,
        "portfolios": ports,
        "baseline": dict(BASE, note=(
            "귀무 = 아무 날 아무 종목을 샀을 때의 같은 초과수익(%d건). 평균은 0에 붙어 있어 "
            "부호 판정이 성립한다. 다만 '상위 5%% 제외' 값은 귀무도 %+.3f%%다 — 주식 수익이 "
            "오른쪽으로 길어서 위 꼬리를 자르면 무엇이든 크게 음수가 되기 때문이다. "
            "그 열은 반드시 이 기준선과 비교해서 읽어야 한다." % (BASE["n"], BASE["ex_top5"]))),
        "dup": {"note": "같은 (종목, 날짜)에 함께 뜨는 정도(자카드). 같은 방향 신호끼리만 비교한다. "
                        "0.5를 넘으면 사실상 같은 신호다 — 둘을 같이 봐도 확인이 되지 않는다.",
                "top": pairs[:14], "n_pairs": len(pairs),
                "median": round(float(np.median([p["j"] for p in pairs])), 3) if pairs else None},
        "today": {sid: [{"t": t, "n": names.get(t, t), "s": sect.get(t, ""),
                         "dt": dt, "ago": ago} for t, dt, ago in lst[:60]]
                  for sid, lst in firing.items()},
        "names": nm,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")

    vc = {}
    for r in out:
        vc[r["verdict"]] = vc.get(r["verdict"], 0) + 1
    print("신호 %d개 · 판정 %s · 임계 |t|≥%.2f" % (len(out), vc, tcrit))
    print("%-38s %6s %8s %7s %7s %6s  %s" % ("신호", "건수", "초과%", "적중%", "t", "오늘", "판정"))
    for r in sorted(out, key=lambda x: -(x.get("h%d" % PRIMARY, {}).get("mean") or -99)):
        m = r.get("h%d" % PRIMARY) or {}
        print("%-38s %6d %8s %7s %7s %6d  %s"
              % (r["name"][:38], r["n"], m.get("mean", "—"), m.get("hit", "—"),
                 m.get("t", "—"), r["n_today"], r["verdict"]))
    print("\n순합의(매수신호수 − 매도신호수) 구간별 20일 초과수익")
    print("%-9s %9s %9s %8s %7s" % ("구간", "종목·일", "초과%", "적중%", "t(NW)"))
    for b in cons["net"]:
        print("%-9s %9d %9s %8s %7s" % (b["lab"], b["n"], b["mean"], b["hit"], b["t"]))
    print("\n포트폴리오(월말 리밸런스·동일가중·무비용) — 벤치마크 동일가중 유니버스")
    print("%-28s %8s %8s %9s %8s %7s" % ("전략", "CAGR", "샤프", "MDD", "Δ샤프", "t"))
    for pf in ports:
        m, b = pf["metrics"], pf["bench"]
        print("%-28s %8s %8s %9s %8s %7s"
              % (pf["name"][:28], m.get("cagr"), m.get("sharpe"), m.get("mdd"),
                 pf["d_sharpe"], pf["t"]))
    print("  (벤치마크 CAGR %s · 샤프 %s · MDD %s)"
          % (ports[0]["bench"].get("cagr"), ports[0]["bench"].get("sharpe"),
             ports[0]["bench"].get("mdd")))
    print("오늘 순합의 +2 이상 %d종목 · −2 이하 %d종목"
          % (len(cons["today"]["top"]), len(cons["today"]["bot"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
