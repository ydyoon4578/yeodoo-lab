#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""테크니컬 타이밍·횡단면 전략 백테스트 → data/tech_strategies.json

기각 아카이브는 '무엇을 왜 기각했는가'만 적혀 있었다. 그건 결론이지 근거가 아니다.
이 파일은 **규칙을 실제로 돌려 숫자를 내는** 자리다 — 통과든 기각이든 같은 표에서.

🚨 규칙을 새로 추가하기 전에 **build/DATA-FACTS.md 를 먼저 읽을 것.** 이 저장소 자료의
   실측 사실 일곱 개가 거기 있고, 그중 여럿은 규칙을 돌려 보기 전에 그 규칙의 운명을
   정해 버린다(gp 커버 37.7% 는 섹터 선별기 · 매출은 2017 년부터 · 후보 풀 램프 ·
   집중도 신호는 SPY/RSP 가격비와 상관 0.96 · 자카드가 낮아도 초과수익 상관은 높을 수 있다 …).
   사전등록 절차는 build/PREREG-2026-08-04.md 가 본보기다.

── 무엇으로 도는가 ─────────────────────────────────────────────────────
data/sd/<티커>.json 의 종가(pxd)·거래량(vd) 753거래일 × 518종목.
2023-07-25 ~ 2026-07-24. 그 외 자산군(채권·상품·현금성 ETF)은 이 저장소에 없다 —
그래서 여기 실리는 건 **주식만으로 만들 수 있는 규칙**뿐이다.

── 이 백테스트가 못 하는 것(결과보다 먼저 읽어야 한다) ──────────────────
* **생존편향.** 오늘의 518종목을 과거 3년에 그대로 적용한다. 그 사이 편출된 종목은
  아예 없다. 상장폐지·부진 종목이 빠진 표본이라 **모든 수치가 실제보다 좋게 나온다.**
  이 저장소에는 시점별 편입(PIT) 이력이 스냅샷 하나뿐이라 보정할 방법이 없다.
* **표본이 3년뿐이다.** 한 번의 상승장 국면이 결과를 지배할 수 있고, 3년으로는
  국면 전환을 몇 번 못 겪는다. 샤프 1.0이 나와도 그게 실력인지 구간인지 못 가른다.
* **비용 0.** 이 랩의 기본 규약대로 무비용(gross)이다. 회전율이 높은 규칙일수록
  실제와 벌어진다 — 그래서 회전율을 함께 싣는다.
* **다중검정.** 여러 규칙을 한 표본에서 돌리면 그중 최고는 우연히도 좋아 보인다.
  그래서 **돌린 규칙을 하나도 빼지 않고 전부 싣는다.** 좋은 것만 고르면 그게 데이터마이닝이다.

사용: python3 build/tech_backtest.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import math
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_SD = os.path.join(DATA, "sd")
OUT = os.path.join(DATA, "tech_strategies.json")

TOPN = 10          # 횡단면 전략이 들고 갈 종목 수 — 50이면 '고른' 게 아니라 사실상 지수다
MIN_HIST = 260     # 신호 계산에 필요한 최소 과거 길이(약 1년)
XSEC_MIN_POOL = 3 * TOPN   # 채점 후보가 이보다 적은 월말은 무보유로 둔다. sc[:TOPN] 이 후보
                           # 전량을 통과시키면 '선택'이 아니라 '있는 것 전부'이고, 그 구간의
                           # 성과는 규칙이 아니라 데이터 커버리지가 만든 것이다(적대감사 실측).

# ── 거래비용 ────────────────────────────────────────────────────────────
# 🚨 이 랩은 회전율을 **싣기만 하고 한 번도 태우지 않았다.** 그래서 연 0.1회전 규칙과
#   연 82회전 규칙이 같은 표에서 같은 t 로 겨뤘다. 그건 비교가 아니다.
#   실제 크기(2026-08-04 실측): 회전율 상위는 t-disp 82.8 · t-macd 54.8 · t-kama 37.2 ·
#   t-mavote 15.3 · x-rev1w 11.3 · x-snapback 11.6 회/년이다. 편도 10bp 만 태워도
#   x-rev1w 는 연 2.3%p 를 잃는다 — 판정을 바꾸기 충분한 크기다.
#
# ⚠ 수치를 고르지 않는다. 하나를 고르면 '그 답이 나오는 비용'을 고른 셈이 되므로
#   **세 수준을 전부 싣고**(5·10·20bp 편도) 대표값만 정해 둔다. 대표값은 미리 못박은
#   것이지 결과를 보고 정한 것이 아니다.
# ⚠ 이 편도 비용은 반값스프레드 + 수수료 + 소액 충격의 합으로 읽는다. 유니버스가
#   S&P 500 ∪ NASDAQ 100 이라 스프레드는 좁지만, 규칙 대부분이 그 안에서도 작은 쪽을
#   동일가중으로 담는다.
# ⚠ 재조정(유지 종목의 비중 되맞춤)에서 나오는 매매는 안 센다 — 종전 turnover 정의와
#   같은 범위로 두기 위해서다. 즉 여기 net 은 **낙관 쪽**이다.
COST_BPS = (5, 10, 20)     # 편도(one-way). 왕복은 이 값의 두 배다.
COST_BPS_MAIN = 10         # 대표값 — net 블록이 쓰는 값


# ── 유틸 ────────────────────────────────────────────────────────────────
def sma(xs, i, n):
    if i + 1 < n:
        return None
    s = 0.0
    for k in range(i - n + 1, i + 1):
        v = xs[k]
        if v is None:
            return None
        s += v
    return s / n


def ret(xs, i, n):
    """i 시점 기준 최근 n일 수익률."""
    if i - n < 0:
        return None
    a, b = xs[i - n], xs[i]
    if not a or not b or a <= 0:
        return None
    return b / a - 1.0


def vol(rets, i, n):
    """최근 n일 일간수익률 표준편차(연율 아님)."""
    if i + 1 < n:
        return None
    w = [r for r in rets[i - n + 1:i + 1] if r is not None]
    if len(w) < n // 2:
        return None
    m = sum(w) / len(w)
    v = sum((x - m) ** 2 for x in w) / max(1, len(w) - 1)
    return math.sqrt(v)


def rsi(xs, i, n=14):
    if i < n:
        return None
    up = dn = 0.0
    for k in range(i - n + 1, i + 1):
        a, b = xs[k - 1], xs[k]
        if a is None or b is None:
            return None
        d = b - a
        up += max(d, 0.0)
        dn += max(-d, 0.0)
    if up + dn == 0:
        return 50.0
    return 100.0 * up / (up + dn)


def beta(rs, mkt, i, n):
    """i 시점까지 최근 n일 시장 대비 베타."""
    if i + 1 < n:
        return None
    xs, ys = [], []
    for k in range(i - n + 1, i + 1):
        a, b = rs[k], mkt[k]
        if a is None or b is None:
            continue
        xs.append(b)
        ys.append(a)
    if len(xs) < n // 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / max(1, len(xs) - 1)
    var = sum((x - mx) ** 2 for x in xs) / max(1, len(xs) - 1)
    return (cov / var) if var > 0 else None


def maxret(rs, i, n=21, k=1):
    """최근 n거래일 일별 수익 중 상위 k개의 평균 — '복권형 선호'의 대리변수.

    Bali·Cakici·Whitelaw(2011)가 쓴 MAX 지표다. 지난달에 하루라도 크게 튄 종목을 개인
    투자자가 복권처럼 선호해서 값이 비싸지고, 그 다음 달 수익이 낮다는 관찰이다.
    k=1이 원논문이고 k=5는 '하루짜리 우연'을 줄이려고 뒤에 표준이 된 변형이다 —
    둘을 같이 실어야 결과가 우연 한 날에 걸린 것인지 알 수 있다.
    """
    a = [x for x in rs[max(1, i - n + 1):i + 1] if x is not None]
    if len(a) < n // 2:
        return None
    a.sort(reverse=True)
    kk = min(k, len(a))
    return sum(a[:kk]) / kk


def recency_ret(rs, i, n=21):
    """최근 n거래일 수익을 **언제 났는지**로 가중한 평균(최근일수록 큰 가중).

    A Unified Framework for Anomalies based on Daily Returns(2026)의 주장을 그대로 옮긴
    것이다 — 지난달 수익이 얼마나 컸는지보다 그 수익이 월 안에서 언제 났는지가 다음 달
    횡단면을 더 잘 설명하고, 그 하나가 단기 반전·MAX·변동성 계열을 대부분 흡수한다.

    가중을 등가중으로 두면 이 값은 그냥 1개월 수익이 된다. 그래서 이 전략과 x-rev1m의
    차이가 곧 '시점 정보'의 값이다 — 둘이 같이 나오면 시점은 아무것도 더하지 않은 것이다.
    결측일이 종목마다 달라 분모는 실제로 쓴 가중의 합으로 나눈다(창 길이로 나누면
    거래 정지가 있던 종목이 체계적으로 0 쪽으로 당겨진다).
    """
    a = rs[max(1, i - n + 1):i + 1]
    if not a:
        return None
    num = den = 0.0
    cnt = 0
    for k, x in enumerate(a, 1):          # k=1이 가장 오래된 날, k=len(a)가 가장 최근
        if x is None:
            continue
        num += k * x
        den += k
        cnt += 1
    if cnt < n // 2:
        return None
    return num / den


def idio_vol(rs, mkt, i, n=120):
    """시장으로 설명되지 않는 부분의 변동성(특이변동성) — 일간 표준편차.

    이 표에는 저변동성과 저베타가 따로 있는데, 둘 중 무엇이 이상현상의 원인인지 갈리지
    않는다. 시장 성분을 뺀 잔차의 변동만 재면 그 둘을 나눌 수 있다(Ang 외 2006).
    """
    b = beta(rs, mkt, i, n)
    if b is None:
        return None
    res = []
    for k in range(i - n + 1, i + 1):
        a, m = rs[k], mkt[k]
        if a is None or m is None:
            continue
        res.append(a - b * m)
    if len(res) < n // 2:
        return None
    mu = sum(res) / len(res)
    return (sum((x - mu) ** 2 for x in res) / max(1, len(res) - 1)) ** 0.5


def info_discreteness(rs, i, n=252, skip=21):
    """정보 이산성(ID) — Da·Gurun·Warachka(2014, RFS).

        ID = sign(형성기 누적수익) × (%음수일 − %양수일)

    같은 12-1 누적수익이라도 그것이 **작은 변화가 자주** 쌓여 만들어졌으면(연속정보)
    투자자 주의를 덜 끌어 과소반응이 남고, **큰 변화가 드물게**(이산정보) 만들어졌으면
    이미 반영돼 반전 위험이 크다는 것이 원논문의 주장이다. 개구리를 서서히 데우면
    못 느낀다는 비유에서 이름이 왔다.

    ⚠ 창은 모멘텀과 **같은 12-1**(i-252 ~ i-skip)이다. 형성기가 다르면 'ID 가 그 수익을
      어떻게 만들었나'라는 질문 자체가 성립하지 않는다.
    ⚠ 여기서는 부호를 곱하지 않은 (%neg − %pos) 를 돌려준다. 부르는 쪽이 승자(양의 수익)만
      추리므로 sign 이 항상 +1 이고, 곱하면 오히려 '패자에도 쓸 수 있다'는 오해를 남긴다.
      패자까지 다루게 되면 그때 부르는 쪽에서 sign 을 곱할 것.
    ⚠ 무변동일(0%)은 양쪽 어디에도 넣지 않는다 — 원논문의 %pos·%neg 정의 그대로다.
    값이 낮을수록 연속정보다.
    """
    if i + 1 < n:
        return None
    a, b = i - n + 1, i - skip
    if b <= a:
        return None
    pos = neg = tot = 0
    for k in range(a, b + 1):
        v = rs[k] if k < len(rs) else None
        if v is None:
            continue
        tot += 1
        if v > 0:
            pos += 1
        elif v < 0:
            neg += 1
    if tot < (b - a + 1) // 2:          # 절반도 못 채우면 못 쓴다
        return None
    return (neg - pos) / float(tot)


def load_factor_proxies(dates):
    """FF 3팩터의 **무료 대리변수** 일간수익 — dates 격자에 맞춰 {이름: [r…]}.

    🚨 이것은 Fama-French 정본이 아니다. 정본(Ken French 데이터 라이브러리)은 전 상장주를
      시총·장부가로 6분할해 만든 것이고, 여기 쓰는 것은 **ETF 스프레드**다:
          SMB ≈ IWM − SPY   (러셀 2000 − S&P 500)
          HML ≈ IVE  − RPG  (S&P 500 가치 − S&P 500 성장)
      상관은 높지만 같은 계열이 아니다. ETF 는 배당 재투자·운용보수·리밸런스 규약이 섞여
      있다. **'FF 회귀'라고 적지 않는다** — 화면·규칙 문구에 '대리변수'라고 쓴다.
      정본을 붙이기로 하면 이 함수만 갈아 끼우면 된다.

    ⚠ 시장(MKT)은 여기서 만들지 않는다. 이 랩의 시장은 **동일가중 유니버스 지수**(ixr)이고
      그것이 타이밍 전략이 실제로 매매하는 대상이라, 다른 시장 정의를 섞으면 한 표 안에
      두 시장이 공존한다. 잔차 회귀도 그 ixr 을 쓴다.

    못 읽으면 빈 dict — 부르는 쪽이 그 전략만 건너뛴다(다른 전략은 그대로 돈다).
    """
    try:
        A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    except Exception as e:
        print("  [팩터대리] assets.json 없음 — 잔차 모멘텀 생략:", str(e)[:60])
        return {}
    adates = A.get("dates") or []
    pos = {d: i for i, d in enumerate(adates)}
    px = A.get("px") or {}

    def series(tk):
        raw = px.get(tk)
        if not raw:
            return None
        out, last = [], None
        for d in dates:
            i = pos.get(d)
            if i is not None and raw[i] is not None:
                last = float(raw[i])
            out.append(last)
        if sum(1 for x in out if x is not None) < len(dates) * 0.9:
            return None
        r = [0.0] * len(dates)
        for i in range(1, len(dates)):
            a, b = out[i - 1], out[i]
            r[i] = (b / a - 1) if (a and b) else 0.0
        return r

    need = {}
    for tk in ("IWM", "SPY", "IVE", "RPG"):
        s = series(tk)
        if s is None:
            print("  [팩터대리] %s 커버 부족 — 잔차 모멘텀 생략" % tk)
            return {}
        need[tk] = s
    n = len(dates)
    return {"SMB": [need["IWM"][i] - need["SPY"][i] for i in range(n)],
            "HML": [need["IVE"][i] - need["RPG"][i] for i in range(n)]}


def _monthly(rs, me, k, end):
    """월말 인덱스 me 중 end 이하인 마지막 k+1 개 구간에서 **월간 누적수익** k 개.

    일간 수익을 곱해 올린다(로그 근사가 아니라 정확한 복리). 한 달에 관측이 5일 미만이면
    그 창을 통째로 버린다 — 상장 전이거나 자료 구멍이라 회귀에 넣으면 잔차가 거짓이 된다.
    """
    ms = [j for j in me if j <= end]
    if len(ms) < k + 1:
        return None
    ms = ms[-(k + 1):]
    out = []
    for j in range(1, len(ms)):
        a, b = ms[j - 1], ms[j]
        acc, ok = 1.0, 0
        for i in range(a + 1, b + 1):
            v = rs[i] if i < len(rs) else None
            if v is None:
                continue
            acc *= (1.0 + v)
            ok += 1
        if ok < 5:
            return None
        out.append(acc - 1.0)
    return out


def resid_mom(rs, facs, me, end, win=36, look=12, skip=1):
    """잔차 모멘텀 — 팩터 회귀 잔차의 12-1 모멘텀을 잔차 변동성으로 표준화한 값.

    Blitz·Huij·Martens(2011, J. Empirical Finance) 규약을 그대로 옮긴다:
      ① 과거 win(36)개월 월간수익을 팩터에 회귀해 잔차를 얻는다(절편 포함).
      ② 최근 skip(1)개월을 건너뛰고 그 앞 look(12)개월 잔차를 **합**한다.
      ③ 그 합을 같은 창의 잔차 표준편차로 나눈다.
    시장·규모·가치 공통요인을 걷어내므로 종목 특유의 추세만 남고, 요인 노출이 만드는
    시변 베타 스윙을 타지 않는다는 것이 원논문의 주장이다.

    ⚠ facs 는 **대리변수**다(load_factor_proxies 주석). 정본 FF 가 아니다.
    ⚠ 12-1 을 '수익의 차'가 아니라 '잔차의 합'으로 계산한다. 총수익 모멘텀(x-mom12)과
      갈리는 지점이 정확히 여기다 — 같은 12-1 이라도 무엇을 누적하느냐가 다르다.
    ⚠ 표준화 분모는 **창 전체(36개월) 잔차의 표준편차**다. 12개월 구간만으로 재면
      분모가 분자와 같은 표본이라 비율이 압축된다(원논문도 창 전체를 쓴다).
    자료가 모자라거나 회귀가 특이하면 None — 그 종목은 그 시점 후보에서 빠진다.
    """
    ys = _monthly(rs, me, win, end)
    if ys is None:
        return None
    xs = []
    for f in facs:
        m = _monthly(f, me, win, end)
        if m is None:
            return None
        xs.append(m)
    k = len(xs)
    cols = [[1.0] * win] + xs
    p = k + 1
    # 절편 포함 최소자승 — 정규방정식을 가우스 소거(부분 피벗)로 푼다. p<=4 라 안정적이고
    # 외부 의존이 없다. 특이하면 None(팩터가 상수이거나 완전 공선일 때).
    xtx = [[sum(cols[a][i] * cols[b][i] for i in range(win)) for b in range(p)] for a in range(p)]
    xty = [sum(cols[a][i] * ys[i] for i in range(win)) for a in range(p)]
    M = [xtx[r][:] + [xty[r]] for r in range(p)]
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return None
        M[c], M[piv] = M[piv], M[c]
        d = M[c][c]
        for j in range(c, p + 1):
            M[c][j] /= d
        for r in range(p):
            if r == c:
                continue
            f2 = M[r][c]
            if f2:
                for j in range(c, p + 1):
                    M[r][j] -= f2 * M[c][j]
    bet = [M[r][p] for r in range(p)]
    res = [ys[i] - sum(bet[a] * cols[a][i] for a in range(p)) for i in range(win)]
    lo = win - skip - look
    if lo < 0:
        return None
    seg = res[lo:win - skip]
    if len(seg) < look:
        return None
    mu = sum(res) / len(res)
    sd = (sum((x - mu) ** 2 for x in res) / max(1, len(res) - 1)) ** 0.5
    if not sd or sd <= 0:
        return None
    return sum(seg) / sd


def load_index_tr(dates):
    """같은 구간의 지수 일간수익 — dates 격자에 맞춰 반환.

    ⚠ **가격지수(PR)**를 쓴다(사용자 결정 2026-07-28 — TR/PR 두 표기가 헷갈린다는 이유).
    랩 전략 수익은 배당 재투자 기준인데 `^GSPC`·`^NDX`는 배당이 빠져 있어, 2006년 이후
    연 약 2.0%p만큼 **지수가 불리하게** 잡힌다. 즉 이 곡선과의 격차는 그만큼 과장돼 있다 —
    화면·문구에 그 사실을 함께 적어야 오독이 안 생긴다(limits·각주 참조).

    동일가중 S&P 500(RSP)은 생존편향 눈금 전용이라 성격이 다르다(실제 ETF, 배당 재투자).
    지수 비교선으로 쓰지 않고 surv_proxy 계산에만 들어간다.

    못 읽으면 빈 dict — 지수 곡선만 빠지고 카드는 그대로 그려진다.
    """
    try:
        A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    except Exception as e:
        print("  [지수곡선] assets.json 없음 — 지수 곡선 생략:", str(e)[:60])
        return {}
    adates = A.get("dates") or []
    pos = {d: i for i, d in enumerate(adates)}
    out = {}
    for tk, label in (("^GSPC", "S&P 500"), ("^NDX", "NASDAQ 100"), ("RSP", "동일가중 S&P 500")):
        raw = (A.get("px") or {}).get(tk)
        if not raw:
            print("  [지수곡선] %s 없음 — 건너뜀" % tk); continue
        px_al, last = [], None
        for d in dates:
            i = pos.get(d)
            if i is not None and raw[i] is not None:
                last = float(raw[i])
            px_al.append(last)
        if sum(1 for x in px_al if x is not None) < len(dates) * 0.9:
            print("  [지수곡선] %s 커버 부족 — 제외" % tk); continue
        r = [0.0] * len(dates)
        for i in range(1, len(dates)):
            a, b = px_al[i - 1], px_al[i]
            r[i] = (b / a - 1) if (a and b) else 0.0
        out[label] = r
    return out


def curve_pack(dates, nav, bnav, k=110, idx_rets=None, i0=0):
    """카드에 그릴 곡선 묶음 — 날짜·전략·대조군·낙폭·연도별.

    ⚠ 낙폭은 **전체 계열에서 먼저 계산하고** 그 다음에 줄인다. 줄인 곡선에서 낙폭을 다시 재면
      골짜기가 표본에서 빠져 얕아지고, 그러면 그림이 카드에 적힌 MDD와 어긋난다. 줄일 때도
      구간 최소값을 고르므로 최악의 골은 반드시 살아남는다.
    """
    n = min(len(dates), len(nav), len(bnav))
    if n < 3:
        return None
    dates, nav, bnav = dates[:n], nav[:n], bnav[:n]

    def ddser(a):
        out, pk = [], a[0]
        for v in a:
            if v > pk:
                pk = v
            out.append(round((v / pk - 1) * 100, 1) if pk else 0.0)
        return out
    dd, ddb = ddser(nav), ddser(bnav)

    step = max(1, n // k)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    def pick(a, worst=False):
        out = []
        for j, i in enumerate(idx):
            hi = idx[j + 1] if j + 1 < len(idx) else i + 1
            seg = a[i:max(hi, i + 1)]
            out.append(min(seg) if (worst and seg) else a[i])
        return out

    # 연도별 — 그해 첫 관측 대비 마지막 관측. 첫해·마지막해는 부분 연도라 그렇게 표시한다.
    yr = {}
    for d, s_, b_ in zip(dates, nav, bnav):
        y = d[:4]
        if y not in yr:
            yr[y] = [s_, b_, s_, b_]
        yr[y][2], yr[y][3] = s_, b_
    # 키 이름은 배포 원장의 yearly 스키마(r=전략 · b=대조군)에 맞춘다 — 화면의 막대차트가
    # 그 이름을 그대로 읽으므로, 여기서 다른 이름을 쓰면 랩 전용 렌더러를 또 만들어야 한다.
    yearly = [{"y": y, "r": round((v[2] / v[0] - 1) * 100, 2) if v[0] else None,
               "b": round((v[3] / v[1] - 1) * 100, 2) if v[1] else None}
              for y, v in sorted(yr.items())]
    pack = {"dates": [dates[i] for i in idx], "nav": [round(nav[i], 1) for i in idx],
            "bench": [round(bnav[i], 1) for i in idx],
            "dd": pick(dd, True), "dd_b": pick(ddb, True), "yearly": yearly,
            "partial": [yearly[0]["y"], yearly[-1]["y"]] if yearly else []}

    # ── 같은 구간 지수 곡선(PR) ──────────────────────────────────────────
    # S&P 500·NASDAQ 100 을 같이 그린다. ⚠ 가격지수라 배당이 빠져 지수가 연 ~2%p 불리하다 —
    # 판정은 대조군으로 하고, 지수는 '살 수 있는 대안'으로 나란히 둘 뿐이다.
    # 전략 NAV와 같은 시작점(100)·같은 날짜에서 출발시켜야 그림이 비교 가능하다.
    if idx_rets:
        ic, idd, iyr = {}, {}, {}
        for lab, rr in idx_rets.items():
            seq = [100.0]
            for i in range(i0 + 1, i0 + n):
                seq.append(seq[-1] * (1 + (rr[i] if i < len(rr) else 0.0)))
            if len(seq) < n:
                continue
            ic[lab] = [round(seq[i], 1) for i in idx]
            idd[lab] = pick(ddser(seq), True)
            g = {}
            for d, v in zip(dates, seq):
                y = d[:4]
                if y not in g:
                    g[y] = [v, v]
                g[y][1] = v
            iyr[lab] = {y: (round((v[1] / v[0] - 1) * 100, 2) if v[0] else None)
                        for y, v in g.items()}
        if ic:
            pack["idx"] = ic          # {'S&P 500': [...], 'NASDAQ 100': [...]}
            pack["idx_dd"] = idd
            for row in yearly:        # 연도별 막대에도 같은 이름으로 얹는다
                row["i"] = {lab: iyr[lab].get(row["y"]) for lab in iyr}
    return pack


def maxdd(nav):
    peak, mdd = nav[0], 0.0
    for v in nav:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1.0)
    return mdd


def ann_stats(nav, dates, rf_m):
    """연율 수익·변동성·샤프(무위험 차감)·MDD."""
    n = len(nav)
    if n < 2:
        return {}
    yrs = (dt.date.fromisoformat(dates[-1]) - dt.date.fromisoformat(dates[0])).days / 365.25
    cagr = (nav[-1] / nav[0]) ** (1 / yrs) - 1 if yrs > 0 and nav[0] > 0 else None
    rs = [nav[i] / nav[i - 1] - 1 for i in range(1, n) if nav[i - 1] > 0]
    if not rs:
        return {}
    m = sum(rs) / len(rs)
    sd = math.sqrt(sum((x - m) ** 2 for x in rs) / max(1, len(rs) - 1))
    av = sd * math.sqrt(252)
    # 무위험은 월별 값을 일할로 환산해 평균만 쓴다(정밀도보다 일관성)
    rfd = sum(rf_m.values()) / len(rf_m) / 21 if rf_m else 0.0
    sharpe = ((m - rfd) / sd * math.sqrt(252)) if sd > 0 else None
    return {"cagr": round((cagr or 0) * 100, 2), "vol": round(av * 100, 2),
            "sharpe": round(sharpe, 3) if sharpe is not None else None,
            "mdd": round(maxdd(nav) * 100, 2)}


def tstat(a, b):
    """두 일간수익 계열의 차이에 대한 t값(대응표본)."""
    d = [x - y for x, y in zip(a, b)]
    if len(d) < 30:
        return None
    m = sum(d) / len(d)
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / max(1, len(d) - 1))
    return round(m / (sd / math.sqrt(len(d))), 2) if sd > 0 else None


# ── 위험 축 판정 ────────────────────────────────────────────────────────
# 왜 만드나. 기존 판정은 t — 일간 수익률 차의 평균을 본다. 그런데 타이밍 오버레이는
# 설계상 수익을 내주고 위험을 사는 규칙이다. 실측(200일선): 낙폭을 -55.2%에서 -26.8%로
# 절반 넘게 줄이고 샤프도 0.441→0.521 로 올렸는데 t 는 -0.60 이었다. 통과가 안 되는 게
# 아니라 그 축으로는 잴 수가 없다. 그래서 '낙폭을 실제로 줄였나'를 따로 묻는 축을 둔다.
#
# 왜 블록 부트스트랩인가. MDD 는 경로에 의존하는 통계량이고 일간 수익률에는 변동성 군집이
# 있다. 하루씩 섞으면(iid) 그 군집이 깨져 낙폭이 실제보다 얕게 나온다 — 검정이 헐거워진다.
# 블록을 통째로 뽑아 국소 의존구조를 살린다. 블록 63일(한 분기)은 낙폭이 만들어지는
# 시간척도를 담기 위한 값이다.
#
# 왜 짝지어 뽑나. 전략과 대조군에서 같은 시점 블록을 뽑는다. 따로 뽑으면 서로 다른
# 시장을 비교하는 셈이 되어 뜻이 없다 — 국면을 공통으로 묶어야 '같은 장에서 누가 덜 깨졌나'가 된다.
#
# ⚠ 여기 두는 이유. 처음엔 asset_backtest 안에 있었는데 ml_backtest 가 못 써서 ML 여섯 줄이
#   통째로 '판정 불가'였다. 지표 정의는 이 파일 한 곳에만 둔다는 규약(ann_stats·tstat 과 같은
#   결)에 맞춰 옮겼다. 복제하면 두 표의 위험 축이 조용히 갈린다.
BOOT_N, BOOT_BLOCK, BOOT_SEED = 4000, 63, 20260729


def risk_bootstrap(rets, brets, n_boot=BOOT_N, block=BOOT_BLOCK, seed=BOOT_SEED):
    """짝지은 순환 블록 부트스트랩 → 낙폭·CVaR5·Calmar 개선폭과 그 p값.

    반환 d_mdd 는 (전략 MDD − 대조군 MDD)다. 둘 다 음수이므로 양수면 덜 깨졌다는 뜻이다.
    p 는 재표본에서 개선이 사라진 비율(단측) — 작을수록 '우연이 아니다'에 가깝다.
    """
    import numpy as np
    n = min(len(rets), len(brets))
    if n < block * 4:
        return None
    r = np.asarray(rets[:n], float)
    b = np.asarray(brets[:n], float)
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    off = np.arange(block)
    yrs = n / 252.0

    k5 = max(1, int(n * 0.05))                             # 하위 5% 일수

    def paths(src, idx):
        x = src[idx]
        nav = np.cumprod(1.0 + x, axis=1)
        mdd = (nav / np.maximum.accumulate(nav, axis=1) - 1.0).min(axis=1) * 100.0
        # CVaR5 — 그 경로에서 가장 나쁜 5% 일간수익률의 평균(%). 수백 일이 들어가므로
        # MDD 와 달리 재표본마다 안정적이다. '덜 깨진다'를 검정력 있게 재는 쪽이 이것이다.
        cvar = np.partition(x, k5, axis=1)[:, :k5].mean(axis=1) * 100.0
        cagr = np.power(np.maximum(nav[:, -1], 1e-9), 1.0 / yrs) - 1.0
        return mdd, cvar, cagr

    dm, dv, dc = [], [], []
    for c0 in range(0, n_boot, 500):                       # 메모리 상한을 두고 나눠 돈다
        m = min(500, n_boot - c0)
        st = rng.integers(0, n, (m, nb))
        idx = ((st[:, :, None] + off) % n).reshape(m, -1)[:, :n]   # 순환 — 모든 날이 같은 확률
        mr, vr, cr = paths(r, idx)
        mb, vb, cb = paths(b, idx)                         # ★ 같은 idx — 짝지은 재표본
        dm.append(mr - mb)
        dv.append(vr - vb)
        # Calmar 는 |MDD| 가 0에 가까우면 발산한다 — 바닥을 두고 막는다
        dc.append(cr / np.maximum(np.abs(mr) / 100.0, 0.02)
                  - cb / np.maximum(np.abs(mb) / 100.0, 0.02))
    dm, dv, dc = np.concatenate(dm), np.concatenate(dv), np.concatenate(dc)
    return {"d_mdd": round(float(dm.mean()), 2), "p_mdd": round(float((dm <= 0).mean()), 4),
            "d_cvar": round(float(dv.mean()), 3), "p_cvar": round(float((dv <= 0).mean()), 4),
            "d_calmar": round(float(dc.mean()), 3), "p_calmar": round(float((dc <= 0).mean()), 4),
            "n_boot": n_boot, "block": block}


# ── 펀더멘털(XBRL) ───────────────────────────────────────────────────────
# data/fx/<티커>.json 에 SEC EDGAR companyfacts에서 뽑은 분기 시계열이 있다.
# 여기서 쓰는 것: eq(자본총계·시점) · sh(희석주식수) · cfo·capex(현금흐름).
#
# ⚠ 시점 정합(point-in-time). 이 파일이 들고 있는 것은 **회계기간 종료일**이지 공시일이
#   아니다. 4월 말로 끝난 분기는 6월쯤에야 공개되므로, 종료일을 그대로 쓰면 아직 세상에
#   없던 숫자로 종목을 고르게 된다(전형적인 미래참조). 그래서 리밸런스 시점 t에서는
#   **t-LAG일 이전에 끝난 기간**만 쓴다. LAG=90일은 10-Q 제출 기한(대형가속제출자 40일)에
#   여유를 크게 둔 값이다 — 짧게 잡아 성과를 좋게 만들 이유가 없다.
#
# ⚠ 재작성(restatement) 편향은 남는다. refresh_facts.py가 '제출일이 가장 늦은 값'을 저장하므로
#   당시 처음 보고된 값이 아니라 나중에 고쳐진 값이다. 이건 데이터로는 못 없앤다 — 적어 둔다.
FUND_LAG_DAYS = 90


def _shift(d, days):
    y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    import datetime as _dt
    return (_dt.date(y, m, dd) - _dt.timedelta(days=days)).isoformat()


_ORD = {}


def _ord(d):
    """'YYYY-MM-DD' → 서수. 950만 번 호출되던 자리라 사전으로 받는다(날짜 종류는 수천 개뿐)."""
    o = _ORD.get(d)
    if o is None:
        o = _ORD[d] = dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()
    return o


def _days_between(a, b):
    return abs(_ord(a) - _ord(b))


def yoy_pair(series, date, lag=FUND_LAG_DAYS, seam=None):
    """(최신값, 전년 동기값) — 공시지연 컷 뒤 최신 관측과 그 1년 전 관측.

    🚨 **인덱스로 4칸 뒤를 세면 안 된다.** yoy_eps 의 주석과 같은 이유이고, 실측으로도
      확인됐다 — 인덱스 방식이면 6개월·9개월·15개월·18개월, 심지어 94~103개월 간격이
      '전년 동기'로 섞여 들어온다(29,550 관측 중 1,057건 = 3.6%). 날짜로 320~410일 안에서
      가장 가까운 것을 찾고, 못 찾으면 그 분기를 버린다.
    seam 을 주면 그 날짜를 **건너뛰는** 짝은 버린다 — 분할 이음매 양쪽은 기준이 달라 비율이
    분할비를 그대로 뒤집어쓴다(split_trim 참조). 이음매 한쪽 안에서만 짝을 짓는다.
    반환은 (d0, v0, d1, v1) 또는 None.
    """
    ser = asof_all(series, date, lag)
    if not ser:
        return None
    d0, v0 = ser[0]
    if seam and d0 < seam:                 # 최신값이 이미 이음매 이전 = 기준이 오늘과 다르다
        return None
    best = None
    for d1, v1 in ser[1:]:
        gap = _days_between(d0, d1)
        if gap > 410:
            break
        if seam and d1 < seam:             # 짝이 이음매를 건너뛴다
            continue
        if 320 <= gap <= 410 and (best is None or gap < best[0]):
            best = (gap, d1, v1)
    return (d0, v0, best[1], best[2]) if best else None


def asof_all(series, date, lag=FUND_LAG_DAYS):
    """공시지연 컷을 통과한 관측 전체(날짜 내림차순). asof_fund 가 첫 값만 주는 것의 확장.

    🚨 `_shift(d, days)` 는 d **−** days 다(뺀다). 여기에 `-lag` 를 넘겼던 탓에 컷이 90일
      과거가 아니라 90일 **미래**였다 — 적대감사가 잡았다. 실측: 리밸런스 2024-07-31 에서
      AAPL 이 2024-09-28 기간말(실제 제출 2024-11-01)을 썼고, asof_fund 와 첫 값이 갈린
      경우가 69,434 중 64,440(92.8%). 20-F 종목은 최악 180일까지 앞섰다.
      방향 확인: 성과를 부풀리는 게 아니라 x-shiss 를 망치고 있었다(t 1.38 → 2.77).
      그래도 미래정보이므로 이 계열이 내는 수치는 무효다.
    """
    if not series:
        return []
    cut = _shift(date, lag)
    return [(d, v) for d, v in series if d <= cut]


_CS_K = 3 - 2 * math.sqrt(2)
_CS_CACHE = {}


def cs_spread(H, L, tk=""):
    """Corwin–Schultz(JF 2012) 고저가 매수매도 스프레드 추정 — **일별 계열**을 돌려준다.

    사전등록: build/PREREG-2026-08-04-HLSPREAD.md

    왜 이 추정량인가. 이 랩의 유동성 지표는 한 번 죽었다 — Amihud ILLIQ 는 분자가
    **미국 상장분 거래대금**인데 분모(시가총액)가 **전 클래스·전 시장**이라, 회사의 일부만
    미국에서 거래되는 종목을 골라 버렸다(DATA-FACTS 7 · 보유칸 32.7%가 13종). 유통물량으로
    고치는 길은 무료 자료가 깨져 막혀 있다. 이 추정량은 **거래대금도 발행주식수도 안 쓴다** —
    그 종목의 미국 라인이 하루 동안 오간 고가·저가만 본다. 범위 불일치가 애초에 없다.

    ⚠ 야간 갭 보정은 원논문 규약이다(추정량이 '두 날의 참가격이 같다'를 가정하므로, 갭이
      있으면 그만큼 되민다). 새 파라미터가 아니다.
    ⚠ 음수 추정치는 0 으로 둔다 — 이것도 원논문 규약이다(스프레드는 음수일 수 없고,
      2일창 추정은 잡음으로 음수가 자주 나온다).
    """
    key = tk or id(H)
    if key in _CS_CACHE:
        return _CS_CACHE[key]
    n_ = len(H)
    out = [None] * n_
    for i in range(1, n_):
        h0, l0, h1, l1 = H[i - 1], L[i - 1], H[i], L[i]
        if not (h0 and l0 and h1 and l1) or l0 <= 0 or l1 <= 0:
            continue
        if l1 > h0:                      # 갭 상승 — 다음날 봉을 갭만큼 내린다
            g = l1 - h0; h1 -= g; l1 -= g
        elif h1 < l0:                    # 갭 하락 — 올린다
            g = l0 - h1; h1 += g; l1 += g
        if h1 <= 0 or l1 <= 0:
            continue
        b = math.log(h0 / l0) ** 2 + math.log(h1 / l1) ** 2
        hh, ll = max(h0, h1), min(l0, l1)
        if ll <= 0:
            continue
        g2 = math.log(hh / ll) ** 2
        a = (math.sqrt(2 * b) - math.sqrt(b)) / _CS_K - math.sqrt(g2 / _CS_K)
        out[i] = max(0.0, 2 * (math.exp(a) - 1) / (1 + math.exp(a)))
    _CS_CACHE[key] = out
    return out


_CLV_CACHE, _GAP_CACHE = {}, {}


def clv_daily(H, L, C, tk=""):
    """일별 종가 위치(Close Location Value) = (2C − H − L)/(H − L) ∈ [−1, 1].

    사전등록: build/PREREG-2026-08-04-BATCH8.md (x-clv · t-clvgate)
    +1 이면 그날 고가에 마감, −1 이면 저가에 마감이다. '그날의 마지막 힘이 어느 쪽이었나'를
    재는 값이고, 종가만으로는 만들 수 없다 — 2026-08-04 에 고가·저가를 배선하고서야 생겼다.
    """
    if tk and tk in _CLV_CACHE:
        return _CLV_CACHE[tk]
    out = [None] * len(C)
    for i in range(len(C)):
        h, l, c = H[i], L[i], C[i]
        if h is None or l is None or c is None or h <= l:
            continue
        out[i] = (2.0 * c - h - l) / (h - l)
    if tk:
        _CLV_CACHE[tk] = out
    return out


def gap_daily(H, L, C, tk=""):
    """일별 (장외 이동, 실질범위) — 시가가 없어도 H·L·전일종가만으로 정확히 나온다.

    사전등록: build/PREREG-2026-08-04-BATCH8.md (x-ongapd)
    TR = max(H, C₋₁) − min(L, C₋₁) 는 전일종가를 포함한 실질범위이고,
    gap = TR − (H − L) 은 **오늘 범위 밖에 놓인 부분** = 장이 닫혀 있는 동안 벌어진 이동이다.
    """
    if tk and tk in _GAP_CACHE:
        return _GAP_CACHE[tk]
    out = [None] * len(C)
    for i in range(1, len(C)):
        h, l, c0 = H[i], L[i], C[i - 1]
        if h is None or l is None or c0 is None or h < l:
            continue
        tr = max(h, c0) - min(l, c0)
        if tr <= 0:
            continue
        out[i] = (tr - (h - l), tr)
    if tk:
        _GAP_CACHE[tk] = out
    return out


def _ols(y, X):
    """절편 포함 최소제곱 — (계수들, R²). X 는 열 리스트. 작은 k 라 가우스-조던으로 충분하다."""
    n = len(y)
    k = len(X) + 1
    if n <= k:
        return None, None
    M = [[1.0] + [X[j][i] for j in range(len(X))] for i in range(n)]
    A = [[sum(M[i][a] * M[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    rhs = [sum(M[i][a] * y[i] for i in range(n)) for a in range(k)]
    G = [A[i][:] + [rhs[i]] for i in range(k)]
    for c in range(k):
        p = max(range(c, k), key=lambda z: abs(G[z][c]))
        if abs(G[p][c]) < 1e-14:
            return None, None
        G[c], G[p] = G[p], G[c]
        pv = G[c][c]
        G[c] = [v / pv for v in G[c]]
        for r in range(k):
            if r != c and G[r][c]:
                f = G[r][c]
                G[r] = [G[r][j] - f * G[c][j] for j in range(k + 1)]
    beta = [G[i][k] for i in range(k)]
    my = sum(y) / n
    sst = sum((v - my) ** 2 for v in y)
    sse = sum((y[i] - sum(beta[a] * M[i][a] for a in range(k))) ** 2 for i in range(n))
    return beta, ((1.0 - sse / sst) if sst > 0 else None)


def xsec_resid(rows):
    """횡단면 OLS 잔차 — rows=[(티커, y, x)…] → {티커: 잔차}.

    이 랩의 중립화는 전부 이 모양이다(x-illiq 사이즈 중립 · x-hlspread 변동성 중립 ·
    x-clv 수익 중립 · x-delay R² 중립 · x-volvol 변동성 중립 · x-peerlag 자기수익 중립).
    같은 일을 여섯 번 다시 쓰면 한 곳만 고쳐지는 사고가 난다 — 한 자리에 둔다.
    """
    if len(rows) < 2:
        return {}
    xs = [r[2] for r in rows]
    ys = [r[1] for r in rows]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx) if sxx > 0 else 0.0
    a = my - b * mx
    return {rows[i][0]: ys[i] - (a + b * xs[i]) for i in range(len(rows))}


def vol_resolved(V, i, n=60, min_distinct=10, max_zero=0.20):
    """거래량 계열이 그 창에서 **신호를 만들 만한 해상도를 갖는가.**

    🚨 vd 는 2026-08-04 까지 백만주 **정수**로 저장됐다. 그래서 일평균 거래량이 100만주
      미만인 종목은 0/1 만 찍는 이진열이 되고, 20일평균÷60일평균은 '급증'이 아니라
      '어느 날이 우연히 1로 반올림됐는가'가 된다. 실측: x-volsurge 가 고른 종목의 60일
      평균 vd 가 중앙 0.3(백만주)이고, 창 안 서로 다른 값이 중앙 3개뿐이었다.
      저장 단위는 천주로 고쳤지만 **이미 저장된 이력은 다음 수집 때까지 그대로**다.
      틀린 채로 재느니 안 재는 것이 낫다 — 해상도가 모자라면 후보에서 뺀다.
    ⚠ 이것은 파라미터 조정이 아니라 **후보 자격**이다($5 필터·XSEC_MIN_POOL 과 같은 층이다).
      신호를 정의할 수 없는 입력을 걸러내는 것이지 좋은 쪽을 고르는 것이 아니다.
    """
    if not V:
        return False
    w = [x for x in V[max(0, i - n + 1):i + 1] if x is not None]
    if len(w) < n * 0.8:
        return False
    if sum(1 for x in w if x == 0) / len(w) > max_zero:
        return False
    return len(set(w)) >= min_distinct


def _stall(rs, i, n=252, cap=0.10):
    """정지가격 게이트 — 창 안 일간수익이 정확히 0인 날이 cap 을 넘으면 True(후보 제외).

    거래가 사실상 멈춘 종목은 베타·상관·변동성이 전부 아래로 치우친다. 사전등록 넷
    (x-delay · x-peerlag · x-updown · x-volvol)이 같은 게이트를 쓴다.
    """
    w = rs[max(0, i - n + 1):i + 1]
    v = [x for x in w if x is not None]
    if not v:
        return True
    return (sum(1 for x in v if x == 0.0) / len(v)) > cap


def mkt_corr(rs, mkt, i, n=252):
    """종목 수익률과 시장 수익률의 상관 — 베타를 ρ×(σi/σm)로 쪼갠 것 중 **ρ 성분**.

    Frazzini·Pedersen(JFE 2014)이 베타를 이렇게 분해한다. 이 표의 저베타는 두 성분이 섞여
    있어 '시장과 덜 움직인다'와 '덜 흔들린다'가 구별되지 않는다 — ρ 만 보면 변동성 크기를
    빼고 동조 여부만 남는다. 유효 관측이 n의 8할 미만이면 None(짧은 이력이 상관을 왜곡한다).
    """
    xs, ys = [], []
    for k in range(max(0, i - n + 1), i + 1):
        a, b = rs[k] if k < len(rs) else None, mkt[k] if k < len(mkt) else None
        if a is not None and b is not None:
            xs.append(a); ys.append(b)
    if len(xs) < int(n * 0.8):
        return None
    m1, m2 = sum(xs) / len(xs), sum(ys) / len(ys)
    s1 = math.sqrt(sum((x - m1) ** 2 for x in xs))
    s2 = math.sqrt(sum((y - m2) ** 2 for y in ys))
    if not s1 or not s2:
        return None
    return sum((x - m1) * (y - m2) for x, y in zip(xs, ys)) / (s1 * s2)


def updown(rs, i, n=231):
    """(오른 날 − 내린 날) ÷ 유효일수. 수익률 **크기를 버리고 부호 개수만** 센다.

    Da·Gurun·Warachka(RFS 2014)의 정보 이산성(information discreteness)에서 쓰는 성분이다.
    이 표의 모멘텀·반전은 전부 수익률 크기로 만들어져 있어, '같은 12개월 수익이라도 잘게
    꾸준히 올랐나 한 번에 튀었나'는 재지 못한다.
    """
    w = [r for r in rs[max(0, i - n + 1):i + 1] if r is not None]
    if len(w) < int(n * 0.8):
        return None
    up = sum(1 for r in w if r > 0)
    dn = sum(1 for r in w if r < 0)
    return (up - dn) / len(w)


def coskew(rs, mkt, i, n=252):
    """공편왜도 — E[(ri−μi)(rm−μm)²] / (sd(ri)·var(rm)). Ang·Chen·Xing(RFS 2006) 식(6).

    시장이 크게 움직일 때 같이 무너지는 정도를 3차 모멘트로 잰다. 이 표에는 저베타·특이변동성
    (둘 다 2차 모멘트)이 있는데, 꼬리의 **비대칭**은 그 둘이 못 재는 축이다.
    """
    xs, ys = [], []
    for k in range(max(0, i - n + 1), i + 1):
        a, m = rs[k], mkt[k]
        if a is None or m is None:
            continue
        xs.append(a); ys.append(m)
    if len(xs) < 200:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    n2 = len(xs)
    vx = sum((x - mx) ** 2 for x in xs) / max(1, n2 - 1)
    vy = sum((y - my) ** 2 for y in ys) / max(1, n2 - 1)
    if vx <= 0 or vy <= 0:
        return None
    num = sum((x - mx) * (y - my) ** 2 for x, y in zip(xs, ys)) / n2
    return num / (vx ** 0.5 * vy)


def same_month_avg(P, i, dates, me, lags=(23, 35, 47, 59)):
    """같은 달 계절성 — 다음 달과 같은 달의 과거 2~5년 월수익 평균.

    Heston·Sadka(2008). OSAP MomSeason 의 lag 목록(23·35·47·59개월)을 그대로 쓴다 —
    i 가 월말이면 t+1 이 다음 달이고, 그 달과 같은 달이 23·35·47·59 개월 전이다.
    결측은 제외하고 남은 것의 산술평균. 하나도 없으면 None.

    ⚠ 월수익은 랩의 month_ends 격자로 만든다. 달력 월말이 아니라 **거래일 월말**이어야
      다른 규칙과 같은 시점을 본다.
    """
    ends = [j for j in me if j <= i]
    if len(ends) < max(lags) + 2:
        return None
    pos = len(ends) - 1                          # ends[pos] == i (월말이면)
    vals = []
    for L in lags:
        a, b = pos - L, pos - L - 1
        if b < 0:
            continue
        j1, j0 = ends[a], ends[b]
        p1, p0 = P[j1], P[j0]
        if p1 and p0 and p0 > 0:
            vals.append(p1 / p0 - 1.0)
    return (sum(vals) / len(vals)) if vals else None


def yoy_eps(series):
    """[(기간종료일, 전년 동기 대비 EPS 변화)] — 날짜 내림차순.

    왜 '전년 동기'인가. 이익에는 계절성이 있어서 직전 분기와 비교하면 계절성만 재게 된다.
    표준 SUE(Foster·Olsen·Shevlin 1984)가 전년 동기를 기준으로 잡는 이유다.

    전년 동기는 **인덱스로 4칸 뒤**가 아니라 날짜로 찾는다. 이유가 둘이다 —
      ① 이 데이터에는 4분기(연간 보고에 흡수되는 분기)가 빠진 종목이 많아 칸 수가 안 맞는다.
      ② 52/53주 회계연도를 쓰는 회사는 분기말이 해마다 며칠씩 움직인다.
    그래서 1년 전에 가장 가까운 관측을 ±45일 안에서 찾는다. 못 찾으면 그 분기는 버린다.
    """
    out = []
    for i, (d, v) in enumerate(series):
        best = None
        for d2, v2 in series[i + 1:]:
            gap = _days_between(d, d2)
            if gap > 410:
                break                       # 내림차순이므로 더 보면 더 멀어진다
            if 320 <= gap <= 410 and (best is None or gap < best[0]):
                best = (gap, v2)
        if best is not None:
            out.append((d, v - best[1]))
    return out


def sue(series, date, lag=FUND_LAG_DAYS, win=8):
    """표준화 이익 서프라이즈 — date 시점에 공개돼 있던 가장 최근 분기 기준.

    (이번 분기 EPS − 전년 동기 EPS) ÷ 그 종목의 최근 변화 표준편차.
    분모로 나누는 이유는 EPS 절대 단위가 종목마다 달라 그대로 두면 주당이익이 큰 회사가
    무조건 위로 오기 때문이다. '이 회사 기준으로 얼마나 놀라운가'를 재는 것이다.
    """
    ys = yoy_eps(series)
    if len(ys) < win + 1:
        return None
    cut = _shift(date, lag)
    k = next((i for i, (d, _v) in enumerate(ys) if d <= cut), None)
    if k is None or len(ys) < k + win + 1:
        return None
    cur = ys[k][1]
    hist = [v for _d, v in ys[k + 1:k + 1 + win]]
    m = sum(hist) / len(hist)
    sd = (sum((x - m) ** 2 for x in hist) / max(1, len(hist) - 1)) ** 0.5
    return (cur / sd) if sd > 1e-9 else None


def eps_accel(series, date, lag=FUND_LAG_DAYS):
    """이익 개선의 **가속** — 이번 분기 전년비 변화 − 직전 분기 전년비 변화. 주당 금액.

    SUE의 짝으로 둔다. SUE는 종목별 표준편차로 나누는데, 그 분모가 작은 회사(이익이 매우
    안정적인 회사)가 위로 몰리는 성질이 있다. 이건 나누지 않으므로, 둘이 같은 결과를 내면
    표준화가 결과를 만든 게 아니라는 뜻이고 갈리면 그 반대다 — MAX와 MAX(5)를 같이 실은 것과
    같은 이유다. 절대 금액이므로 쓰는 쪽에서 주가로 나눈다(그래야 종목 간 비교가 된다).
    """
    ys = yoy_eps(series)
    cut = _shift(date, lag)
    k = next((i for i, (d, _v) in enumerate(ys) if d <= cut), None)
    if k is None or len(ys) < k + 2:
        return None
    return ys[k][1] - ys[k + 1][1]


def ttm(series, date, lag=FUND_LAG_DAYS):
    """최근 12개월치 — date 시점에 공개돼 있던 것만. 매출·순이익·배당 같은 **기간 누적값**용.

    한 분기만 보면 계절성에 휘둘리므로 1년을 봐야 한다. 그런데 이 자료는 종목마다 주기가
    다르다 — 4분기가 연간 보고에 흡수돼 사라진 종목이 많고, 현금흐름은 아예 연 단위로만
    들어오는 종목이 있다. 그래서 **관측 간격으로 주기를 판정**한다.
      · 간격이 300일 이상이면 연 단위 보고다 → 가장 최근 하나가 곧 1년치다.
      · 아니면 분기 보고다 → 최근 4개를 더하되, 그 4개가 400일 안에 들어올 때만 인정한다.
    못 채우면 None을 돌려주고 그 종목은 그 달 순위에서 빠진다. 분기 보고 종목과 연간 보고
    종목을 같은 잣대 없이 섞으면 연간 쪽 값이 4배로 커져 순위가 통째로 뒤집힌다.

    ⚠ 잔고 항목(자본·자산·부채·주식수)에는 쓰면 안 된다 — 그건 시점 값이라 더하면 4배가 된다.
      그쪽은 asof_fund를 쓴다.

    🚨 **간격이 1년이라고 그 관측이 1년치인 것은 아니다** — 현금흐름표에서 이 가정이 깨진다.
      10-Q 의 현금흐름표는 **YTD 누적**이라 기간이 3·6·9개월이고, refresh_facts.pick() 이
      80~100일(분기)과 350~380일(연간)만 남기고 6·9개월은 버리므로 q 버킷에 **Q1 만** 남는다.
      그러면 관측 간격은 371일인데 각 값은 90일치다 — 위의 '간격 300일 = 연간' 규칙이
      Q1 한 분기를 1년치로 반환한다.
        실측(KO): capex q=[2026-04-03 266, 2025-03-28 309, 2024-03-29 370] 인데 a=[2025 2112].
                  ttm 이 266 을 돌려줬다 — 실제의 1/8. cfo 도 2021 vs 7408(1/3.7)이고,
                  KO 2025 Q1 cfo 는 **−5202** 로 음수라 계절 왜곡까지 탄다.
        전수: 같은 기간 a 값 대비 q-ttm 비율 중앙 cfo 0.19 · capex 0.22 · bb 0.27.
             손익계산서 태그는 정상(rev·ni·opinc 0.98, cogs·gp 0.97) — 그쪽은 기간이 분기다.
      그래서 **연간(a) 버킷을 같이 받아** 4분기 합이 안 되면 a 를 쓴다. a 도 없을 때만 종전처럼
      최근 하나를 1년치로 본다(진짜 연 1회 보고 종목).
      ⚠ 이 결함은 배포 목록의 x-fcfy(잉여현금흐름 수익률)를 그대로 관통하고 있었다.
    """
    return ttm2(series, None, date, lag)


def ttm2(series, annual, date, lag=FUND_LAG_DAYS):
    """ttm 의 본체 — 분기 계열과 연간(a) 계열을 함께 받는다. 위 독스트링 참조."""
    cut = _shift(date, lag)
    got = [(d, v) for d, v in (series or []) if d <= cut]
    # ① 진짜 분기 보고 — 최근 4개가 400일 안에 들어오고 **가운데가 안 벌어졌을 때만** 더한다.
    #   🚨 2026-08-04 버그 수정. 종전에는 양 끝 간격(got[0]~got[3])만 봤다. 그런데 대부분의
    #     발행인은 회계 4분기를 10-K 에 흡수시켜 q 버킷에 안 남기므로, 최근 4개가
    #     (Q3, Q2, Q1, 전년 Q3) 처럼 **가운데가 ~182일 벌어진 채** 365일 안에 들어온다.
    #     그러면 합계는 12개월이 아니라 **Q4 를 빼고 1년 전 같은 분기를 대신 넣은 15개월 창**이다.
    #     실측(채점칸 기준 인접 간격 120일 초과 비율): dps 78.9% · rev 59.4% · eps 54.8% ·
    #     ni 48.9%. 초과분은 거의 전부 180~210일(분기 하나 결측)이다.
    #     오차 크기: 연간 버킷으로 결측 분기를 복원해 대면 eps 는 |오차|>10% 인 칸이 30.6%다.
    #   → 인접 간격이 전부 120일 이하일 때만 ①로 인정하고, 아니면 ②(연간 버킷)로 내린다.
    #     연간 버킷은 정의상 12개월치라 이 함정이 없다.
    if (len(got) >= 4 and _days_between(got[0][0], got[3][0]) <= 400
            and all(_days_between(got[k][0], got[k + 1][0]) <= 120 for k in range(3))):
        return sum(v for _d, v in got[:4])
    # ② 연간 버킷이 있으면 그것이 정답이다 — 간격만 보고 Q1 을 1년치로 읽는 함정을 여기서 막는다
    ann = [(d, v) for d, v in (annual or []) if d <= cut]
    if ann:
        return ann[0][1]
    # ③ 연 1회만 보고하는 종목 — 종전 동작
    if len(got) >= 2 and _days_between(got[0][0], got[1][0]) >= 300:
        return got[0][1]
    return None


def z_of(p):
    """양측 p 에 대응하는 정규 임계값. 이분법 — 의존성 없이 재현되게.

    모듈 레벨에 둔다 — 전에는 판정 루프 안에 갇혀 있어서 다른 생성기(pit_backtest)가
    문턱을 **손으로 적었다**. 손으로 적은 임계는 규칙 수가 바뀌면 조용히 낡는다
    (실측 사고: pit_strategies.json 이 27종인데 문턱을 16종 시절 값 2.9 로 적어,
     하필 그 값만이 고배당 t 2.94 를 '통과' 로 만들었다).
    """
    lo, hi = 0.0, 10.0
    for _ in range(200):
        m = (lo + hi) / 2
        cdf = 0.5 * (1 + math.erf(m / math.sqrt(2)))
        if 1 - cdf > p / 2:
            lo = m
        else:
            hi = m
    return round((lo + hi) / 2, 2)


def z_crit(n, alpha=0.05):
    """규칙 n 종을 같은 표본에서 돌렸을 때의 본페로니 임계."""
    return z_of(alpha / max(1, n))


def _pool_limit(rows):
    """횡단면 규칙의 **후보 풀 램프**를 한 줄로 — 숫자는 여기서 세고 문장은 그것을 읽는다.

    얇은 달(n_thin)은 후보가 30 미만인 달만 센다. 그런데 후보가 67 → 505 로 불어나면
    게이트는 한 번도 안 걸리면서도 앞구간의 '상위 10'과 뒷구간의 '상위 10'이 서로 다른
    선택이 된다 — 앞에서는 유니버스의 13% 안에서 고른 것이기 때문이다. 그 사실을 적는다.
    """
    xs = [r for r in rows if r.get("pool")]
    if not xs:
        return "후보 풀 기록 없음(횡단면 규칙이 없다)."
    hit = [r for r in xs if r["pool"]["narrow"] > 0]
    if not hit:
        return ("후보 풀 — 횡단면 %d규칙 모두 매 월말 유니버스의 1/4 이상을 채점했다. "
                "'상위 10'이 좁은 후보 안에서 나온 구간은 없다." % len(xs))
    hit.sort(key=lambda r: -r["pool"]["narrow"])
    w = hit[0]["pool"]
    tot = sum(r["pool"]["narrow"] for r in hit)
    # ⚠ 여기 마크다운(**·`)을 쓰지 않는다 — limits 는 화면에서 esc() 를 거치므로 기호가
    #   글자 그대로 찍힌다(validate_site 가 잡는다).
    return ("후보 풀이 표본 앞구간에서 얇다 — 횡단면 %d규칙 중 %d규칙에서, 그 규칙 자신의 "
            "평소 후보 수(중앙값) 절반에도 못 미친 월말이 합계 %d번 있었다(최대 %s: %d개월 · "
            "평소 %d종인데 최소 %d종까지 내려갔다 · %s 시작). 재무 태그가 과거로 갈수록 "
            "얇아지기 때문이다. 🚨 얇은 달 게이트(후보 30 미만)는 이걸 못 잡는다 — 평소의 "
            "절반 안에서 고른 '상위 10'은 전체에서 고른 '상위 10'과 같은 선택이 아니고, "
            "그만큼 앞구간 성과에는 규칙이 아니라 커버리지가 만든 몫이 섞여 있다."
            % (len(xs), len(hit), tot, hit[0]["name"], w["narrow"], w["med"], w["min"], w["d0"]))


RETIRED_RECS = []       # 목록에서 뺀 규칙의 기록(arch 태그 보존용) — build_strats 가 채운다
_CLASSMATE = None       # 티커 → 같은 회사(같은 CIK)의 티커 묶음. 아래 load_classmates 가 채운다
DUAL_SKIPS = {}         # sid → 이중클래스라서 건너뛴 선택 횟수. 로그·limits 에 싣는다


def load_classmates():
    """티커 → 같은 회사의 티커들(자기 자신 포함). 판정은 **CIK** 로 한다.

    🚨 티커 모양으로 추측하지 않는다. GOOG/GOOGL 은 접두사가 같지만 BRK.B/BF.B 는
      아무 관계도 없고, 반대로 NWS/NWSA 처럼 접미 한 글자만 다른 진짜 쌍도 있다.
      SEC 가 부여한 CIK 가 '같은 발행인'의 정본이다(data/cik_map.json).
    """
    global _CLASSMATE
    if _CLASSMATE is None:
        _CLASSMATE = {}
        try:
            co = json.load(io.open(os.path.join(DATA, "cik_map.json"),
                                   encoding="utf-8")).get("co") or {}
        except Exception:
            return _CLASSMATE
        by = {}
        for t, c in co.items():
            if c:
                by.setdefault(c, []).append(t)
        for ts in by.values():
            if len(ts) > 1:
                for t in ts:
                    _CLASSMATE[t] = set(ts)
    return _CLASSMATE


def pick_top(sc, sid="", topn=None):
    """점수순 후보 sc=[(점수, 티커)…] 에서 상위 TOPN — **한 회사는 한 번만** 담는다.

    🚨 사용자 결정 2026-08-04: "전략들에 두 종목이 같이 들어가면 안 된다."
      알파벳(GOOG·GOOGL)·폭스(FOX·FOXA)·뉴스코프(NWS·NWSA)는 같은 회사의 다른 클래스라
      둘 다 담으면 10종 바스켓이 아니라 **한 회사에 두 칸을 준 9종 바스켓**이 된다.
      두 클래스는 재무가 같고 주가도 거의 같이 움직여서, 어떤 규칙이든 하나가 뽑히면
      다른 하나도 바로 옆 순위에 선다 — 우연이 아니라 구조적으로 겹친다.
    남기는 쪽은 **점수가 높은 클래스**다. 규칙을 하나 더 만들지 않으려는 것이다
    (거래대금이 큰 쪽·먼저 상장된 쪽 같은 기준을 넣으면 그 자체가 새 파라미터가 된다).
    ⚠ 지수 복제(build/style_top*.py)에는 쓰지 않는다. 실제 지수는 두 클래스를 **둘 다**
      담으므로, 거기서 하나를 빼면 복제가 아니라 다른 규칙이 된다.
    """
    cm = load_classmates()
    n = TOPN if topn is None else topn
    out, used, skipped = [], set(), 0
    for _v, t in sc:
        if len(out) >= n:
            break                          # 바스켓이 찬 뒤의 후보는 애초에 안 뽑힌다
        if t in used:
            skipped += 1                   # 이 순위면 뽑혔을 자리인데 같은 회사가 이미 있다
            continue
        out.append(t)
        mates = cm.get(t)
        if mates:
            used |= mates                  # 같은 회사의 다른 클래스는 이후 순위에서 제외
    if skipped and sid:
        DUAL_SKIPS[sid] = DUAL_SKIPS.get(sid, 0) + skipped
    return out
SPLIT_TRIMMED = {}      # 티커 → (자른 날짜, 배수). 얼마나 잘랐는지 로그·limits 에 싣는다
SPLIT_REBASED = {}      # 티커 → 되맞춘 관측 수. 자르는 대신 살린 양을 로그·limits 에 싣는다
_SPLITS = None          # 티커 → [(날짜, 분할비)] — data/splits.json. 없으면 {} 로 남는다
_CCONC = None           # 티커 → [(제출일, 집중도%)] — data/cust_conc.json


def load_custconc():
    """고객 집중도(단일 고객 매출 비중). 파일이 없으면 빈 지도 — 그 규칙만 후보 0 이 된다.

    규약은 build/PREREG-2026-08-04-CUSTCONC.md 에 **수집 전에** 확정해 커밋했다.
    """
    global _CCONC
    if _CCONC is None:
        _CCONC = {}
        try:
            co = json.load(io.open(os.path.join(DATA, "cust_conc.json"),
                                   encoding="utf-8")).get("co") or {}
        except Exception:
            return _CCONC
        for t, rows in co.items():
            ser = sorted(((r[0], float(r[1])) for r in rows if r and r[1] is not None),
                         reverse=True)          # 날짜 내림차순 — asof_fund 와 같은 모양
            if ser:
                _CCONC[t] = ser
    return _CCONC


def custconc_asof(t, date, stale_days=540):
    """date 시점에 **이미 공시돼 있던** 가장 최근 집중도. 없거나 너무 낡으면 None.

    🚨 여기에는 FUND_LAG_DAYS 를 더 빼지 않는다. 재무 태그는 기준이 '기간말'이라 공시까지의
      시차를 빼야 했지만, 이 값은 기준이 **이미 제출일**이다. 한 번 더 빼면 이미 공개된 정보를
      안 쓰는 셈이 되고 규약과도 달라진다.
    ⚠ 540일(약 18개월)보다 오래된 값은 안 쓴다(규약). 공시를 멈춘 회사의 옛 수치를 현재값인
      척 들고 있지 않는다 — refresh_facts 의 450일 규칙과 같은 취지다.
    """
    for d, v in (load_custconc().get(t) or []):
        if d <= date:
            return v if _days_between(date, d) <= stale_days else None
    return None


def load_splits():
    """분할 이력을 한 번만 읽는다. 파일이 없으면 빈 지도 — 되맞추기가 꺼지고 옛 동작(자르기)."""
    global _SPLITS
    if _SPLITS is None:
        p = os.path.join(DATA, "splits.json")
        try:
            _SPLITS = json.load(io.open(p, encoding="utf-8")).get("co") or {}
        except Exception:
            _SPLITS = {}
    return _SPLITS


_SHYF = None            # 티커 → [(날짜, 백만주)] — data/shares_yf.json(SEC 에 없는 종목만)


def load_shares_yf():
    """SEC 로 못 만드는 종목의 보완 주식수. 없으면 빈 지도 — 그 종목은 예전처럼 빠진다."""
    global _SHYF
    if _SHYF is None:
        p = os.path.join(DATA, "shares_yf.json")
        try:
            _SHYF = json.load(io.open(p, encoding="utf-8")).get("co") or {}
        except Exception:
            _SHYF = {}
    return _SHYF


def shares_yf(tk):
    """보완 주식수를 **오늘 기준으로 정확히** 되맞춰 돌려준다(날짜 내림차순).

    🚨 여기서는 _rebase 의 '매끄러움' 추정을 쓰지 않는다. 쓸 필요가 없다 — 이 계열은
      날짜별 기말 발행주식수라 관측 하나하나가 그 날의 실제 보고치다. 그래서 그 날짜
      **이후 분할들의 곱**을 그대로 곱하면 끝이다(추정 없음). SEC 계열이 어려웠던 이유는
      기간말마다 소급 여부가 달라 '어느 제출본인지'를 몰랐기 때문인데, 여기엔 그 문제가 없다.
    """
    ser = load_shares_yf().get(tk) or []
    if not ser:
        return []
    spl = load_splits().get(tk) or []
    out = []
    for d, v in ser:
        f = 1.0
        for sd, r in spl:
            if sd > d:
                f *= r
        out.append((d, v * f))
    out.sort(reverse=True)
    return out


def _rebase(ok, splits):
    """당시 보고 주식수를 **오늘 기준**으로 되맞춘다. → (되맞춘 계열, 배수 적용 횟수)

    ok 는 날짜 내림차순, 단위오류를 이미 뺀 계열이다.

    🚨 왜 '한 번 자르기'로는 안 되는가. 기준이 한 지점에서 바뀌는 게 아니라 관측마다
      **따로** 바뀐다. refresh_facts.pick() 이 기간말마다 제출일 최신본을 남기는데,
      어떤 기간은 분할 뒤 비교표시로 다시 실려 소급되고 어떤 기간은 아직 안 실렸다.
      실측(NFLX, 2025-11-17 ×10 분할): 2026-03 소급됨 · 2025-09 아직 아님 ·
      2025-06 소급됨 — 오르내린다. 그래서 관측 하나하나를 분류한다.

    후보는 추정치가 아니라 **그 날짜 이후 실제 분할들의 접미 곱**이다(0개 반영 = 이미
    오늘 기준, k개 반영 = 최근 k개만 소급된 상태). 그중 직전(이미 확정된) 관측과 가장
    매끄럽게 이어지는 것을 고르고, 어느 후보로도 1.5배 안에 못 들어오면 되맞추기를
    포기한다 — 거기서부터는 호출부가 예전처럼 자른다.
    """
    if len(ok) < 2:
        return list(ok), 0
    # 🚨 닻(최신 관측)이 반드시 오늘 기준인 것은 아니다. 마지막 제출 **뒤에** 분할이 있으면
    #   계열 전체가 분할 전 기준으로 남는다. 이 경우 예전 코드는 단절이 없어 아무 일도
    #   하지 않았고(그래서 조용히 틀렸다), 되맞추기도 닻을 그대로 믿으면 같이 틀린다.
    #   실측(2026-08-04): KLAC 2026-06-12 ×10 분할, 최신 관측은 2026-03-31 —
    #   주식수 131.75M(분할 전)에 분할조정 주가를 물려 E/P 가 10배로 나오고 있었다.
    #   가르는 법: 최신이 **이미 소급됐다면** 바로 아래 관측과 분할비만큼 벌어져 있다.
    #   실측 5종이 깨끗이 갈렸다 — BKNG 점프 24.386(≈×25, 이미 반영) vs
    #   CRWD 1.026 · DD 0.983 · FDX 1.013 · KLAC 0.998(전 구간 분할 전).
    f0, used = 1.0, 0
    aft = [r for sd, r in splits if sd > ok[0][0]]
    if aft:
        pr = 1.0
        for r in aft:
            pr *= r
        jump = (ok[0][1] / ok[1][1]) if ok[1][1] else None
        if jump is None or abs(jump - pr) / pr > 0.05:
            f0, used = pr, 1
    out = [(ok[0][0], ok[0][1] * f0)]
    prev = ok[0][1] * f0
    for d, v in ok[1:]:
        cands, f = [1.0], 1.0
        for _sd, r in reversed([s for s in splits if s[0] > d]):
            f *= r
            cands.append(f)
        best = bestk = None
        for k in cands:
            j = (v * k) / prev if prev else 0
            if j <= 0:
                continue
            dev = max(j, 1.0 / j)
            if best is None or dev < best:
                best, bestk = dev, k
        if best is None or best >= 1.5:
            break                        # 분할로 설명 안 되는 단절 — 여기서 멈춘다
        if bestk != 1.0:
            used += 1
        prev = v * bestk
        out.append((d, prev))
    return out, used


def split_trim(sh, eps, dps, tk="", eps_a=None, dps_a=None):
    """🚨 분할 기준 불일치 관측을 잘라낸다 — 안 자르면 순수 선견이 된다.

    주가는 **분할조정본**(auto_adjust=True)이라 전 구간이 오늘 기준이다. 그런데 SEC 주당지표
    (eps·dps)와 주식수(sh)는 **당시 보고치**다. refresh_facts.pick() 이 같은 기간의 중복
    보고 중 filed 최신본을 남기는데, SEC 의 소급재작성은 뒤 제출본에 비교표시로 다시 실린
    기간까지만 닿는다 — 그래서 한 계열 안에서 분할 전·후 기준이 **섞인다**.
      실측(data/fx/CMG.json): sh 2023-06-30 = 1387.37, 2023-03-31 = 27.79(×49.92).
      그 시점 E/P 가 112.5%(실제 ~1.7%)로 나와 x-ep 이 CMG 를 70개 월말 중 42회 담았다.
      분할비는 미래 정보이므로 이것은 편향이 아니라 **선견**이다.

    🚨 2026-08-04 — **먼저 되맞추고, 안 되는 것만 자른다.** 예전에는 무조건 잘랐고 그 이유는
    하나였다: "배수를 도출해 재계산하려면 실제 증자·합병(PCG 4.05배 파산탈출 증자 등)과
    분할을 **비율만으로** 구별해야 하고 그 판단이 틀리면 없던 숫자를 만든다."
      그 전제가 사라졌다. data/splits.json(build/refresh_splits.py)이 분할 이력을 **코퍼릿
      액션 그대로** 싣는다 — 비율을 추정하는 게 아니라 회사가 공시한 사실을 읽는다.
      실측(2026-08-04): 이음매 비율과 실제 분할비가 CMG 49.923 vs ×50 · NVDA 10.038 vs ×10
      · AMZN 20.051 vs ×20 · WMT 2.992 vs ×3 으로 맞물렸고, OMC 1.535(IPG 합병 신주)·
      MSTR 8.838(ATM 대량발행)은 어느 분할과도 맞지 않았다. 즉 구별이 된다.
      효과: 버리는 관측이 3,575 → 1,215(전체의 15.0% → 5.1%), 100종이 좋아졌다.
      독립 검산 — 되맞춘 주식수 × 분할조정 주가로 시가총액을 다시 만들어 봤다. CMG 2009-06
      26억$ · NFLX 2009-03 26억$ · AAPL 2009-03 809억$ 로 실제와 맞고, 최신 관측은 랩이
      아는 오늘 시총과 −11%~+19%(분기 시차만큼) 안에 들었다.
    ⚠ 분할이 **설명하지 못하는** 단절은 예전처럼 자른다. 그쪽은 실제 자본거래(합병·대량발행)
      이거나 우리가 모르는 기준 변화인데, 둘을 여기서 가를 근거가 여전히 없기 때문이다.
      남은 1,215개가 그것이다(HON·OMC·EXE·O·PCG·TFC·IFF·LHX·KDP — 전부 합병·증자 이력).
    ⚠ 총액 항목(rev·ni·eq·liab·cfo·capex)은 달러라 분할과 무관하다 — 건드리지 않는다.
    두 단계로 나눈다 — 섞이는 사유가 둘이고 정답 기준이 서로 다르기 때문이다.
      ① 단위 오류(천주 vs 백만주) — 소수의 관측만 어긋난다. 정답은 **다수**다.
         실측: WAT sh 59.76 옆에 82139.0(×1380) · ROL ×3273 · COP ×1134 · TER ×978.
         분할비는 아무리 커도 50 정도이므로 100배 넘는 것은 분할이 아니라 단위다.
      ② 분할 기준 — 절반 넘게 어긋날 수 있다. 정답은 **최신**이다(조정주가가 오늘 기준이므로).
         🚨 여기서 다수결을 쓰면 거꾸로 간다 — CMG 는 분할 전 관측이 11개로 다수라
           중앙값 규칙이 분할 전(27.79)을 남겼다. 최신에서 거슬러 올라가며 자른다.

    🚨 단계 ②를 **주식수 변화 자체를 신호로 쓰는 규칙**(x-shiss)에 그대로 적용하면 신호를
    거세한다 — 적대감사 실측: OMC 20개 관측 중 19개 삭제(단절 1.53배의 정체는 분할이 아니라
    IPG 합병 대가 주식발행 +53%), MSTR 12/20 삭제(ATM 대량발행). 즉 순주식발행 회피가
    겨냥해야 하는 가장 전형적인 사건이 일어나면 그 종목은 꼴찌가 아니라 **후보에서 사라진다**.
    그래서 이음매 날짜를 함께 돌려준다. 주당지표는 지금처럼 자르고(기준이 섞이면 답이 없다),
    주식수 성장률은 ①만 적용한 계열에서 **이음매를 건너뛰는 짝만** 배제한다 — 이음매 양쪽은
    각각 내부적으로 일관되므로 잘못된 값은 이음매를 지나는 비율 하나뿐이다.
    ⚠ 비율만으로 분할과 증자를 구별하려는 시도는 하지 않는다: 인접 분기 |>1.2배| 168건 중
      단순 분할비(±2%) 근접은 67건뿐이고 나머지는 단위오류(1000배대)와 실제 자본거래다.
    """
    if not sh or len(sh) < 3:
        return sh, eps, dps, sh, None, eps_a, dps_a
    vs = sorted(v for _d, v in sh if v and v > 0)
    if not vs:
        return sh, eps, dps, sh, None, eps_a, dps_a
    med = vs[len(vs) // 2]
    # ① 단위 오류 — 100배 넘게 벗어난 관측(분할로는 설명 안 되는 크기)
    bad = {d for d, v in sh if not v or v <= 0 or v / med > 100 or med / v > 100}
    ok = [(d, v) for d, v in sh if d not in bad]
    # ② 되맞추기 — 분할 이력으로 관측마다 기준을 오늘로 맞춘다(_rebase 참조).
    #    splits.json 이 없으면 _rebase 가 첫 단절에서 바로 멈춰 예전 '자르기'와 같아진다.
    reb, used = _rebase(ok, load_splits().get(tk) or [])
    fac = {d: (v / raw) for (d, v), (_d0, raw) in zip(reb, ok) if raw}   # 날짜 → 적용 배수
    unit = list(reb)                       # ①+② 계열(주식수 성장률용 — 자르지 않는다)
    if used:
        SPLIT_REBASED[tk] = used
    # ③ 되맞추기가 멈춘 지점부터 자른다 — 분할이 설명하지 못한 단절이다.
    seam = None
    if len(reb) < len(ok):
        seam = reb[-1][0]
        bad |= {d for d, _v in sh if d < seam}
    # ⚠ '버릴 게 없으면 그냥 돌려준다'는 지름길을 두지 않는다. 자를 게 없어도 되맞춤
    #   배수는 적용해야 한다 — 실측으로 한 번 틀렸다(NFLX 는 버릴 관측이 0이라 조기
    #   반환에 걸려 주식수만 70배로 고쳐지고 EPS 는 분할 전 값 그대로 남았고,
    #   그 결과 2012년 E/P 가 463% 로 나왔다).
    if bad:
        worst = max((max(v / med, med / v) for d, v in sh if d in bad and v and v > 0), default=0)
        SPLIT_TRIMMED[tk] = (min(bad), round(worst, 2), len(bad), len(sh))
    keep = lambda ser: [(d, v) for d, v in (ser or []) if d not in bad]
    # 🚨 주당지표는 주식수와 **반대로** 움직인다. 분할 전 기준이면 주식수는 k 배 작고
    #   EPS·DPS 는 k 배 크다 — 그래서 같은 배수로 나눈다. 기준은 '어느 제출본에서 왔나'라
    #   항목이 아니라 기간말이 정하므로, 주식수에서 얻은 날짜별 배수를 그대로 쓴다.
    #   🚨 sh 격자에 없는 날짜는 배수를 못 정한다. 예전에는 그대로 뒀는데, 되맞추기를
    #   넣은 뒤로는 그러면 안 된다 — 옆의 주식수는 오늘 기준으로 고쳐졌는데 이 주당지표만
    #   분할 전 기준으로 남으면 정확히 이 함수가 막으려던 선견이 되살아난다.
    #   그래서 **그 날짜 뒤에 분할이 있는** 무배수 관측만 버린다(뒤에 분할이 없으면
    #   기준이 흔들릴 수 없으므로 예전처럼 남긴다).
    #   총액 항목 rev·ni·eq·liab·cfo·capex 는 달러라 애초에 분할과 무관하다.
    spl = load_splits().get(tk) or []

    def persh(ser):
        out = []
        for d, v in keep(ser):
            if d in fac:
                out.append((d, (v / fac[d]) if (fac[d] and v is not None) else v))
            elif not any(sd > d for sd, _r in spl):
                out.append((d, v))
        return out

    # 🚨 2026-08-05 — **연간 버킷도 같은 배수를 태운다.** 하루 전에 ttm2 의 연간 폴백을
    #   x-ep·x-dy·x-payout 에 이었는데, 그 폴백이 집는 eps_a·dps_a 가 여기를 안 거치고 있었다.
    #   그러면 분자만 분할 전 기준·분모(주가)만 분할 후 기준이 되어 이 함수가 막으려는 선견이
    #   정확히 되살아난다. 실측(적대감사): x-ep 보유칸 1,990개 중 1,503개(75.5%)가 '그 달
    #   이후 실제로 분할한 종목'이었고, 이익수익률 30% 초과(현실 불가) 칸이 82.9% 였다.
    #   NVDA 2019-06-28 — 분할조정 주가 4.08 · 연간 EPS 6.63(2021 ×4 · 2024 ×10 전 보고치)
    #   → E/P 162.5%. 그날 상위 10종이 10/10 나중에 분할한 종목이었다.
    #   ⚠ 배수를 못 정하는 날짜(sh 격자 밖)는 persh 가 '뒤에 분할이 있으면' 버린다 —
    #     연간 관측은 회계연도말이라 sh 격자와 자주 어긋나므로 이 경로가 실제로 작동한다.
    return keep(reb), persh(eps), persh(dps), unit, seam, persh(eps_a), persh(dps_a)


def load_fund(extra_dirs=()):
    """티커 → {'eq': [(기간종료일, 값)…], 'sh': …, 'fcf': …}. 전부 날짜 내림차순.

    extra_dirs — data/fx 말고 더 훑을 디렉터리. 기본은 없음(=기존 동작 그대로).
      build/style_pit.py 가 data/fx_pit(지수에서 빠진 종목의 재무)을 얹어 PIT 백테스트를
      돌릴 때 쓴다. **왜 별 디렉터리인가**: refresh_facts.py:551 이 오늘 유니버스에 없는
      data/fx/*.json 을 지운다 — 편출 종목 재무를 fx 에 넣으면 다음 주 갱신에 사라진다.
    """
    out = {}
    dirs = [os.path.join(DATA, "fx")] + [d for d in extra_dirs]
    files = []
    for d in dirs:
        if os.path.isdir(d):
            files += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".json")]
    for path in files:
        try:
            j = json.load(io.open(path, encoding="utf-8"))
        except Exception:
            continue
        fn = os.path.basename(path)
        tg = j.get("tags") or {}

        def _clean(a):
            return [(x[0], x[1]) for x in (a or []) if isinstance(x, list) and len(x) == 2
                    and isinstance(x[1], (int, float))]

        def series(key):
            v = tg.get(key) or {}
            return _clean(v.get("i") or v.get("q"))

        def annual(key):
            """연간(a) 버킷만. 🚨 흐름 항목은 q 버킷이 Q1 만 남아 있을 수 있어 이것이 정답이다
            (ttm2 참조). 커버리지: ni 510 · cfo 510 · rev 505 · capex 432 · bb 414종."""
            return _clean((tg.get(key) or {}).get("a"))

        eq, ep = series("eq"), series("eps")
        # 주식수는 세 벌을 차례로 본다. 셋 다 없어 통째로 빠지던 회사가 18종이었다
        # (실측 2026-08-04). 순서에 이유가 있다 —
        #   ① sh(가중평균 희석, 분기/시점) — EPS 의 분모와 같은 정의라 1순위다.
        #   ② sh 의 연간 버킷 — 20-F 로 연 1회만 내는 외국 발행인(ARM·ASML·NBIS·PDD)은
        #      분기 버킷이 비어 있다. 주식수는 **잔고 항목**이라 asof_fund 로 시점을 집으므로
        #      연간 관측이어도 맞다(흐름 항목이었다면 이렇게 못 섞는다 — ttm 이 4년을 더한다).
        #   ③ sho(기말 발행주식수) — 희석주식수를 아예 안 내는 회사(HSY·KKR·LYB·SJM).
        #      정의가 달라(가중평균 아님, 희석 아님) 마지막이다.
        #   ④ shares_yf(SEC 로는 못 만드는 다중클래스 6종 — ARES·BKR·BRK.B·ERIE·STZ·V).
        #      출처가 다르므로 정말 마지막이다.
        _tk = j.get("t") or fn[:-5]
        rev, ni, dps = series("rev"), series("ni"), series("dps")
        sh = series("sh") or annual("sh") or series("sho")
        ep_a0, dp_a0 = annual("eps"), annual("dps")
        sh, ep, dps, sh_u, seam, ep_a, dp_a = split_trim(sh, ep, dps, _tk, ep_a0, dp_a0)
        if not sh:
            # 🚨 이 계열에는 split_trim 을 태우지 않는다. 되맞춤이 이미 정확하고
            #   (shares_yf 참조 — 추정이 아니라 날짜별 분할 곱), 그 위에 '매끄러움' 규칙을
            #   또 걸면 **진짜 자본거래를 분할로 착각해 자른다**. 실측: ARES 는 345행이
            #   251행으로 줄고 시작이 2015-11 → 2022-04 이 됐다(ARES 는 분할 이력이 없다).
            sh = sh_u = shares_yf(_tk)
            seam = None
            # 주당지표는 여전히 SEC 의 당시 보고치다. 이 종목들은 배수를 정할 주식수
            # 계열이 SEC 에 없어 되맞출 수 없다 — 마지막 분할 이전은 **자른다**(옛 방침).
            # 해당은 둘뿐이다(BRK.B 2010-01-21 ×50 · V 2015-03-19 ×4). 나머지 넷은 분할이 없다.
            _sp = load_splits().get(_tk) or []
            if sh and _sp:
                _cut = max(d for d, _r in _sp)
                ep = [(d, v) for d, v in (ep or []) if d >= _cut]
                dps = [(d, v) for d, v in (dps or []) if d >= _cut]
        asset, liab = series("asset"), series("liab")
        cfo_s, capex_s = series("cfo"), series("capex")
        cfo, capex = dict(cfo_s), dict(capex_s)
        # 🚨 잉여현금흐름은 **연간 버킷으로** 만든다. q 버킷은 Q1 만 남아(refresh_facts.pick 이
        #   6·9개월 YTD 를 버린다) 같은 기간말 교집합을 잡아도 'Q1 cfo − Q1 capex' 가 되고,
        #   ttm 이 그걸 1년치로 읽어 x-fcfy 가 실제의 1/3~1/8 을 쓰고 있었다(KO 1755 vs 5296).
        #   연간이 없는 종목만 종전 경로로 남긴다.
        cfo_a, capex_a = dict(annual("cfo")), dict(annual("capex"))
        fcf_a = sorted(((k, cfo_a[k] - capex_a[k]) for k in cfo_a if k in capex_a), reverse=True)
        # 미개척 태그 — 수익성(gp·cogs·opinc)·환원(bb)·현금흐름(cfo) 축을 열어 둔다.
        # 🚨 전부 **기간 흐름** 항목이므로 쓰는 쪽에서 반드시 ttm() 을 거칠 것. asof_fund 로 읽으면
        #   종목마다 보고 주기가 달라 그대로 깨진다 — 실측(515종): cfo 는 연간형 467 대 분기형 12,
        #   capex 342 대 21, bb 317 대 11 인데 opinc 은 분기형 389 대 연간형 1, cogs 295 대 1 이다.
        #   즉 같은 '흐름'인데도 태그마다 지배적 주기가 반대라, 섞으면 연간 쪽이 4배로 부푼다.
        #   (ttm() 이 관측 간격 300일로 주기를 판정해 이 문제를 이미 처리한다.)
        # ⚠ 커버리지는 series() 기준 gp 38% · cogs 58% · opinc 76% · bb 78% · iss 19% 다.
        #   바스켓 10종에 XSEC_MIN_POOL(30) 게이트가 걸리므로 gp 단독은 아슬아슬하다 —
        #   rev−cogs 폴백을 쓰면 늘지만 업종 왜곡이 따라온다(건보사 benefit expense 미태깅).
        # 잉여현금흐름은 같은 기간종료일에 둘 다 있을 때만 만든다. capex가 없는 종목을
        # cfo만으로 채우면 자본지출이 큰 업종이 통째로 좋아 보인다.
        fcf = sorted(((k, cfo[k] - capex[k]) for k in cfo if k in capex), reverse=True)
        if eq or sh or fcf or ep:
            out[j.get("t") or fn[:-5]] = {"eq": eq, "sh": sh, "fcf": fcf, "eps": ep,
                                          "rev": rev, "ni": ni, "dps": dps,
                                          "asset": asset, "liab": liab,
                                          # 현금은 총액(달러)이라 분할과 무관 — split_trim 대상 아님.
                                          "cash": series("cash"),
                                          # 🚨 2026-08-04 에 수집을 시작한 다섯. **여기 안 실으면
                                          #   화면에도 백테스트에도 없는 것과 같다.** 실측으로 걸렸다 —
                                          #   이 다섯을 쓰는 규칙을 시험 삼아 돌리니 198개월 전부
                                          #   후보 0 이었고, 원인이 규칙이 아니라 이 줄의 누락이었다.
                                          #   수집(refresh_facts)과 배선(여기)은 다른 일이다.
                                          "ca": series("ca"), "cl": series("cl"),
                                          "debt": series("debt"), "re": series("re"),
                                          "dep": series("dep"), "dep_a": annual("dep"),
                                          # 주식수 성장률용: 단위오류만 교정, 분할 이음매는 날짜로 표시
                                          "sh_u": sh_u, "sh_seam": seam,
                                          # 흐름 항목 — 쓰는 쪽에서 ttm2(q, a) 를 쓸 것.
                                          # q 만 쓰면 현금흐름 계열이 Q1 하나로 1년을 주장한다.
                                          "cfo": cfo_s, "capex": capex_s, "gp": series("gp"),
                                          "cogs": series("cogs"), "opinc": series("opinc"),
                                          "bb": series("bb"), "fcf_a": fcf_a,
                                          "cfo_a": annual("cfo"), "capex_a": annual("capex"),
                                          "bb_a": annual("bb"), "ni_a": annual("ni"),
                                          "rev_a": annual("rev"), "gp_a": annual("gp"),
                                          # 🚨 2026-08-04 추가. ttm2 의 연간 폴백은 연간 버킷이
                                          #   있어야 작동한다 — 없으면 분기 결측 종목이 조용히
                                          #   후보에서 빠진다(연차보고 외국 발행인이 정확히
                                          #   그 집단이고, DATA-FACTS 7 이 지목한 무리와 겹친다).
                                          "eps_a": ep_a, "dps_a": dp_a,
                                          "cogs_a": annual("cogs"), "opinc_a": annual("opinc")}
    # 분할 기준 처리 결과를 **로그로 남긴다.** 조용히 자르면 표본이 왜 짧은지 아무도 모른다
    # (실제로 그랬다 — SPLIT_TRIMMED 를 모으기만 하고 찍는 곳이 없었다).
    if SPLIT_REBASED or SPLIT_TRIMMED:
        nre = sum(SPLIT_REBASED.values())
        ntr = sum(v[2] for v in SPLIT_TRIMMED.values())
        print("  [분할 기준] 되맞춤 %d관측/%d종 · 자름 %d관측/%d종%s"
              % (nre, len(SPLIT_REBASED), ntr, len(SPLIT_TRIMMED),
                 "" if load_splits() else "  ⚠ data/splits.json 없음 — 되맞추기 꺼짐"))
    return out


def asof_fund(series, date, lag=FUND_LAG_DAYS):
    """date 시점에 **이미 공개돼 있었을** 가장 최근 값. 없으면 None."""
    if not series:
        return None
    cut = _shift(date, lag)
    for d, v in series:          # 날짜 내림차순
        if d <= cut:
            return v
    return None


# ── 데이터 ──────────────────────────────────────────────────────────────
def load():
    """일봉을 읽는다 → dates, 종가, 거래량, **고가·저가**, 메타, 무위험이자율.

    🚨 고가(hd)·저가(ld)는 2026-08-04 까지 **읽는 쪽이 없었다.** refresh_stocks.py:1693 이
      종목당 4,422일치를 꼬박꼬박 써 두고 있었는데 여기서 pxd·vd 만 집어 갔다 — 즉 랩의
      모든 규칙이 종가와 거래량만 볼 수 있었고, 일중 범위를 쓰는 규칙은 '나쁘다'가 아니라
      **만들 수 없었다.** 재무 태그 다섯(ca·cl·debt·re·dep)에서 이미 두 번 난 사고와
      같은 유형이고(수집≠배선), 그때 만든 validate_site 의 배선 검사는 재무 태그만 보고
      일봉 계열은 안 봤다. 그 검사도 함께 넓혔다.
      자료 상태 실측(2026-08-04): 518종 전부 hd·ld 가 pxd 와 같은 길이(4,422)이고,
      2,112,332 봉 전수에서 ld ≤ pxd ≤ hd 위반이 **0건**이다 — 분할조정 기준이 종가와 같다.
    """
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        st = json.load(f)
    dates = st["pxd_dates"]
    n = len(dates)
    px, vlm, hi, lo, meta = {}, {}, {}, {}, {}
    for s in st["stocks"]:
        t = s["t"]
        p = os.path.join(DIR_SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        a, v = d.get("pxd"), d.get("vd")
        if not isinstance(a, list) or len(a) != n:
            continue
        px[t] = a
        vlm[t] = v if isinstance(v, list) and len(v) == n else None
        # 길이가 안 맞으면 None 으로 둔다 — 짧은 계열을 그대로 태우면 날짜가 밀린 채
        # 조용히 다른 날의 범위를 읽는다(종가와 달리 이건 눈에 안 띈다).
        _h, _l = d.get("hd"), d.get("ld")
        hi[t] = _h if isinstance(_h, list) and len(_h) == n else None
        lo[t] = _l if isinstance(_l, list) and len(_l) == n else None
        meta[t] = {"name": s.get("name") or "", "sector": s.get("sector") or ""}
    rf = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8")).get("monthly") or {}
    rf = {k: v for k, v in rf.items() if k >= dates[0][:7]}
    return dates, px, vlm, hi, lo, meta, rf


def daily_rets(px):
    out = {}
    for t, a in px.items():
        r = [None]
        for i in range(1, len(a)):
            p0, p1 = a[i - 1], a[i]
            r.append((p1 / p0 - 1.0) if (p0 and p1 and p0 > 0) else None)
        out[t] = r
    return out


def month_ends(dates):
    """월말 인덱스(다음 날의 월이 다르면 그 날이 월말)."""
    idx = []
    for i in range(len(dates) - 1):
        if dates[i][:7] != dates[i + 1][:7]:
            idx.append(i)
    return idx


# ── 전략 정의 ───────────────────────────────────────────────────────────
# 각 전략은 (시점 i, 상태) → 목표 비중을 준다.
#   kind='timing'  : 시장(동일가중 유니버스) 노출 0~1 — 매매 대상은 동일가중, 판정 대조군은 SPX
#   kind='xsec'    : 종목 선택 — 상위 TOPN 동일가중
STRATS = []


def timing(sid, name, rule, fn, why, arch=None):
    STRATS.append({"sid": sid, "name": name, "kind": "timing", "rule": rule, "why": why, "fn": fn, "arch": arch})


def z_composite(rows):
    """월말 단면 z-점수 컴포지트 — rows=[(티커, {지표명: 값})…] → {티커: 평균 z}.

    🚨 2026-08-06 · E30(섹터 중립 밸류 컴포지트) 재현용. 카드가 지정한 컴포지트는
      "네 지표를 표준화 점수로 환산해 평균"인데, 지표마다 결측 종목이 다르다.
      **결측을 0 으로 채우면 안 된다** — 0 은 z 척도에서 '평균'이라, 자료가 없는 종목이
      중간 순위를 공짜로 받는다. 있는 지표만으로 평균하고, 전부 없으면 뺀다.
    ⚠ 표준화는 평균·표준편차 z 다(MAD 가 아니다). 이 랩의 xsec_resid·x-* 규칙들이 쓰는
      방식과 같게 둔다 — 두 벌을 두면 한쪽만 고쳐진다.
    ⚠ 꼬리를 자르지 않는다. 자르는 폭이 곧 자유도다.
    """
    keys = set()
    for _t, m in rows:
        keys |= {k for k, v in m.items() if v is not None and v == v}
    zs = {}
    for k in keys:
        vs = [(t, m[k]) for t, m in rows if m.get(k) is not None and m[k] == m[k]]
        if len(vs) < 2:
            continue
        xs = [v for _t, v in vs]
        mu = sum(xs) / len(xs)
        sd = (sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
        if sd <= 0:
            continue
        for t, v in vs:
            zs.setdefault(t, []).append((v - mu) / sd)
    return {t: sum(a) / len(a) for t, a in zs.items() if a}


def pick_sector_neutral(sc, sec_of, mcap_of, per=1):
    """섹터 중립 바스켓 — 각 섹터에서 점수 상위 `per` 종, 비중은 **유니버스 섹터 시총 비중**.

    🚨 E30 카드의 규정 그대로다: "섹터마다 점수 상위 종목을 같은 수씩 뽑아 섹터 배분이
      지수와 같아지게 하고, 섹터 안에서는 동일가중."
    ⚠ per=1 로 박는다(사전등록 §3). 카드가 수를 정하지 않아 자유롭게 고르면 그 순간
      자유도가 생긴다. 11섹터 × 1 = 11 이 이 랩의 TOPN(10)에 가장 가깝다.
    ⚠ 섹터를 모르는 종목(sector 빈 문자열)은 **뺀다.** '기타' 칸을 만들면 그 칸이
      중립의 예외가 되어, 중립이 유지되는지 확인할 수 없다.
    돌려주는 것 — [(티커, 비중)…]. 비중 합은 1.
    """
    by = {}
    for v, t in sc:                       # sc 는 점수 내림차순
        g = (sec_of.get(t) or "").strip()
        if g:
            by.setdefault(g, []).append(t)
    if not by:
        return []
    # 섹터 비중 = 그 시점 **유니버스 전체**의 섹터 시총 비중(고른 종목의 시총이 아니다).
    # 고른 것으로 재면 그건 벤치마크가 아니라 자기 자신이다.
    w_sec, tot = {}, 0.0
    for t, mc in mcap_of.items():
        g = (sec_of.get(t) or "").strip()
        if g and g in by and mc and mc > 0:
            w_sec[g] = w_sec.get(g, 0.0) + mc
            tot += mc
    if tot <= 0:
        return []
    out = []
    for g, ts in by.items():
        w = w_sec.get(g, 0.0) / tot
        if w <= 0:
            continue
        picks = ts[:per]
        for t in picks:
            out.append((t, w / len(picks)))
    s = sum(w for _t, w in out)
    return [(t, w / s) for t, w in out] if s > 0 else []


def xsec(sid, name, rule, fn, why, arch=None):
    STRATS.append({"sid": sid, "name": name, "kind": "xsec", "rule": rule, "why": why, "fn": fn, "arch": arch})


# 펀더멘털이 필요한 전략들 — 점수 루프가 람다 대신 갈래로 처리한다(날짜·주식수·주가가 필요).
FUND_SIDS = {"x-custconc",                     # 2026-08-04 사전등록(PREREG-…-CUSTCONC.md)
             "x-btp", "x-fcfy", "x-ep", "x-sp", "x-roe", "x-npm",
             # E30 밸류 컴포지트 둘 — 사전등록 PREREG-2026-08-06-E30VALUE.md
             "x-valcomp", "x-valcomp-sn",
             "x-rgrow", "x-lowde", "x-dy", "x-small",
             # 2026-07-30 추가 — 전부 총액 항목(달러)만 쓰므로 분할과 무관하다.
             "x-agrow", "x-shiss", "x-cash",
             # 2026-07-31 추가 — 흐름 항목은 반드시 ttm2(q, a) 로 읽는다(ttm 독스트링 참조).
             "x-poacc", "x-gpa", "x-ocfp", "x-aci", "x-payout"}


def build_strats():
    # ── 타이밍: 시장 노출을 0/1(또는 연속)으로 조절 ──
    timing("t-sma200", "200일 이동평균 타이밍",
           "동일가중 지수가 200일 단순이동평균 위면 100% 편입, 아래면 현금(무위험).",
           lambda ix, i, R, V: 1.0 if (sma(ix, i, 200) is not None and ix[i] > sma(ix, i, 200)) else 0.0,
           "가장 오래되고 가장 많이 인용되는 추세 필터. 기준선이 되라고 넣는다.")
    timing("t-cross", "50/200 골든크로스",
           "50일선이 200일선 위면 편입, 아래면 현금.",
           lambda ix, i, R, V: 1.0 if (sma(ix, i, 50) is not None and sma(ix, i, 200) is not None
                                       and sma(ix, i, 50) > sma(ix, i, 200)) else 0.0,
           "같은 추세 개념을 두 이동평균의 관계로 바꾼 것. 200일선 단독과 얼마나 다른지 본다.")
    timing("t-tsmom", "절대 모멘텀 (12-1)",
           "최근 12개월 수익에서 마지막 1개월을 뺀 값이 양수면 편입, 아니면 현금.",
           lambda ix, i, R, V: 1.0 if ((ret(ix, i, 252) or -1) - (ret(ix, i, 21) or 0) > 0) else 0.0,
           "시계열 모멘텀(CTA 계열)의 주식 단독 버전. 마지막 1개월 제외는 단기 반전을 피하려는 관례다.")
    timing("t-voltgt", "변동성 타깃팅 (연 12%)",
           "최근 20일 실현변동성으로 목표 연 12%에 맞춰 노출을 0~1로 조절(레버리지 없음).",
           lambda ix, i, R, V: (min(1.0, 0.12 / (V * math.sqrt(252))) if (V and V > 0) else 0.0),
           "수익률이 아니라 위험을 목표로 잡는 규칙. 상승장에서 뒤처지고 급락장에서 덜 맞는다.")
    timing("t-rsi", "RSI 과매도 반등",
           "RSI(14)가 30 아래로 내려가면 편입, 60 위로 올라오면 현금(히스테리시스).",
           None, "역추세 규칙. 이 랩은 종목 신호에서 역추세를 이미 폐기했다 — 시장 단위에서도 같은지 본다.")
    timing("t-donch", "돈치안 20일 돌파",
           "20일 최고가를 넘으면 편입, 20일 최저가를 깨면 현금.",
           None, "가격 돌파만 쓰는 고전 추세 규칙. 이동평균과 무엇이 다른지 본다.",
           arch="donchian-breakout")
    timing("t-macd", "MACD 신호선 교차",
           "MACD(12,26)가 신호선(9) 위면 편입, 아래면 현금.",
           None, "이동평균의 변화율을 보는 규칙. 전환이 이동평균보다 빠른 대신 잦다.")
    timing("t-volreg", "저변동성 국면만 편입",
           "최근 20일 실현변동성이 과거 1년 중앙값보다 낮으면 편입, 높으면 현금.",
           None, "변동성 자체를 국면 신호로 쓴다. 변동성 군집이 실제로 수익과 이어지는지 본다.")

    # ── 타이밍 2차 묶음 ────────────────────────────────────────────────
    # 앞의 8개는 전부 '지수 가격 하나'를 본다. 그래서 서로 비슷하게 움직이고,
    # 하나가 지면 대체로 같이 진다. 아래는 일부러 **다른 축**을 건드린다 —
    # 파라미터 위험(합의), 시장 내부(폭), 경로(드로다운·추격 손절), 외부 게이지(심리).
    timing("t-mavote", "이동평균 합의 (20·50·100·200)",
           "네 이동평균 중 현재가가 위에 있는 개수 비율만큼 편입(0·25·50·75·100%).",
           None, "'200일'이라는 숫자 하나에 결과가 걸리는 것이 단일 이동평균 규칙의 약점이다. "
                 "파라미터를 하나 고르는 대신 평균을 내면 그 위험이 줄어드는지 본다.")
    timing("t-tsmom6", "절대 모멘텀 (6개월)",
           "최근 6개월 수익이 양수면 편입, 아니면 현금.",
           lambda ix, i, R, V: 1.0 if ((ret(ix, i, 126) or -1) > 0) else 0.0,
           "12-1과 규칙은 같고 되돌아보는 길이만 다르다. 같은 아이디어가 파라미터에 얼마나 "
           "민감한지 재는 대조군이다 — 둘의 결과가 크게 갈리면 그건 발견이 아니라 과최적화 신호다.")
    timing("t-tsmomc", "연속 시계열 모멘텀",
           "12-1 모멘텀을 0~20% 구간에 대응시켜 노출을 0~1로 비례 배분(문턱 없음).",
           None, "0/1 스위치는 문턱 근처에서 결과가 요동친다. 같은 신호를 연속으로 쓰면 "
                 "그 요동이 줄어드는지, 아니면 스위치가 주던 상승분까지 깎이는지 본다.")
    timing("t-mhvote", "다기간 모멘텀 합의 (1·3·6·12개월)",
           "네 구간 수익 중 양수인 개수 비율만큼 편입.",
           None, "되돌아보는 길이를 하나 고르지 않고 넷에 투표시킨다. 이동평균 합의와 같은 발상을 "
                 "가격이 아니라 수익률에 적용한 것 — 둘이 같은 결과면 축이 하나라는 뜻이다.")
    timing("t-breadth", "시장 폭 게이트 (200일선 위 비율)",
           "유니버스에서 자기 200일선 위에 있는 종목 비율이 50%를 넘으면 편입, 아니면 현금.",
           None, "여기서 처음으로 '지수 가격이 아닌 것'을 본다. 지수는 대형주 몇 개로 버틸 수 있어서 "
                 "속으로 무너지는 국면을 못 잡는다. 시장 내부가 그걸 먼저 알려주는지 확인한다.")
    timing("t-breadthc", "시장 폭 비례 노출",
           "200일선 위 종목 비율을 그대로 노출로 쓴다(30% 미만은 0으로 절사).",
           None, "같은 폭 지표를 문턱 없이 쓴다. 게이트판과 비교해 문턱이 값을 더하는지 빼는지 가른다.")
    timing("t-ddgate", "드로다운 게이트 (−10%)",
           "직전 고점 대비 −10%를 밑돌면 현금, 고점 대비 −3% 안으로 회복하면 다시 편입.",
           None, "가격 수준이 아니라 '경로'를 보는 규칙. 손실 통제를 규칙으로 못 박으면 "
                 "MDD가 실제로 줄어드는지, 그 대가로 수익을 얼마나 내주는지 본다.")
    timing("t-chand", "변동성 추격 손절 (샹들리에)",
           "진입 후 고점에서 20일 변동성의 3배만큼 떨어지면 현금, 50일선을 되찾으면 재진입.",
           None, "손절 폭을 고정 %가 아니라 그때의 변동성으로 잡는다. 조용한 장에선 좁게, "
                 "거친 장에선 넓게 — 고정 −10%보다 덜 털리는지 본다.")
    timing("t-chan", "52주 채널 위치 비례",
           "현재가가 52주 최저~최고 구간에서 차지하는 위치를 그대로 노출로 쓴다.",
           None, "돈치안 돌파를 연속으로 편 것. 신고가에서 100%, 신저가에서 0%가 되므로 "
                 "'돌파'라는 이벤트 없이도 같은 정보를 쓸 수 있는지 본다.")
    timing("t-kama", "적응형 이동평균 (효율성 비율)",
           "10일 효율성 비율로 이동평균 속도를 조절(2~30일)하고, 현재가가 그 위면 편입.",
           None, "추세가 곧을 때는 빠르게, 톱니처럼 오갈 때는 느리게 따라간다. "
                 "이동평균의 고질병인 '횡보장 잦은 전환'을 규칙 안에서 고칠 수 있는지 본다.")
    timing("t-semivol", "하방 변동성 타깃 (연 9%)",
           "최근 60일 하락일만의 변동성으로 목표 연 9%에 맞춰 노출을 0~1로 조절.",
           None, "일반 변동성 타깃은 급등도 위험으로 세어 상승장에서 노출을 깎는다. "
                 "하락만 세면 그 손해가 사라지는지 본다.")
    timing("t-gapcap", "과열 차단 (200일선 이격 상한)",
           "200일선 위이면 편입하되, 이격도가 과거 1년 상위 10%를 넘으면 절반만 편입.",
           None, "추세는 따르되 과열 구간에서만 발을 뺀다. 추세추종의 약점인 "
                 "'고점에서 최대 노출'을 규칙으로 눌러도 성과가 남는지 본다.")
    timing("t-sentgate", "시장 심리 게이트 (공포 매수)",
           "이 사이트의 심리 지수(VIX·기간구조·MOVE 합성)가 1년 중앙값보다 낮으면(공포) 편입.",
           None, "유일하게 가격 밖에서 오는 입력이다. 이 랩은 종목 단위 역추세를 이미 폐기했는데, "
                 "시장 단위에서 외부 공포 게이지로는 다른 답이 나오는지 확인한다. "
                 "아카이브의 'VIX 기간구조'와는 다른 규칙이다 — 그쪽은 기간구조 단독, 이쪽은 "
                 "VIX 수준·기간구조·MOVE 합성이라 이전 판정을 그대로 가져다 붙이지 않는다.")

    # ── 횡단면: 상위 TOPN 동일가중, 월말 리밸런스 ──
    xsec("x-mom12", "12-1 모멘텀 상위 %d" % TOPN,
         "최근 12개월 수익 − 최근 1개월 수익 상위 %d종목 동일가중, 월말 리밸런스." % TOPN,
         lambda t, i, P, R, V: ((ret(P, i, 252) or -9) - (ret(P, i, 21) or 0)),
         "횡단면 모멘텀의 표준형. 이 표에서 기준선 역할을 한다.")
    # 잔차 모멘텀 — 전략 탐색 풀 B4 를 그대로 구현한다(사용자 요청 2026-08-03).
    #   ⚠ 이 표에 x-mom12 가 이미 있으므로 **증분이 있는지**가 판정의 핵심이다. 원논문 주장이
    #     '총수익 모멘텀보다 위험조정 수익 2배'이니, 그 주장이 이 유니버스·이 창에서도 서는지를
    #     같은 잣대로 본다. 상관이 0.99 를 넘으면 이름만 다른 같은 규칙이다(x-mom-trend 선례).
    xsec("x-residmom", "잔차 모멘텀 상위 %d" % TOPN,
         "과거 36개월 월간수익을 시장·규모·가치에 회귀한 잔차의 12-1개월 합을 잔차 "
         "표준편차로 나눠 상위 %d종목 동일가중, 월말 리밸런스. 직전 1개월은 건너뛴다. "
         "규모·가치는 ETF 스프레드 대리변수(IWM−SPY, IVE−RPG)이고 시장은 동일가중 "
         "유니버스다 — Fama-French 정본이 아니다." % TOPN,
         None,          # 팩터 수익이 필요해 람다로 못 준다 — 점수 루프의 갈래에서 계산한다
         "Blitz·Huij·Martens(2011)는 공통요인 노출을 걷어낸 잔차의 모멘텀이 총수익 모멘텀보다 "
         "위험조정 수익이 높고 모멘텀 크래시가 완만하다고 보고했다. 이 표에는 총수익 모멘텀"
         "(x-mom12)이 이미 있으므로, 여기서 묻는 것은 더 좋은가가 아니라 그 둘이 다른 "
         "규칙인가 다 — 상관과 증분 알파로 가른다. "
         "⚠ 풀 항목이 인용한 '크래시를 피한다'는 설명은 최근 연구(2025)가 그 전제를 되묻고 "
         "있어, 이 표는 크래시 회피를 근거로 삼지 않고 수치만 낸다.")
    # 프로그인더팬 — 전략 탐색 풀 B5 를 그대로 구현한다(사용자 요청 2026-08-03).
    xsec("x-fip", "프로그인더팬 (연속정보 모멘텀 상위 %d)" % TOPN,
         "12-1 모멘텀 상위 5분위에서 정보 이산성 ID 가 가장 낮은 %d종목 동일가중, 월말 "
         "리밸런스. ID = (형성기 음수일 비율 − 양수일 비율)이고 같은 12-1 창에서 잰다. "
         "값이 낮을수록 작은 변화가 자주 쌓인 연속정보다." % TOPN,
         None,          # 모멘텀 상위 5분위 컷이 횡단면이라 람다(종목 하나)로는 못 준다
         "Da·Gurun·Warachka(2014)는 같은 누적수익이라도 연속정보로 만들어진 추세가 과소반응을 "
         "남겨 오래 가고, 이산정보로 만들어진 추세는 이미 반영돼 반전한다고 보고했다"
         "(연속 5.94% vs 이산 −2.07%). "
         "⚠ 이 표에는 ID 와 사실상 같은 지표가 이미 있다 — 경로 일관성(x-cntd)의 "
         "'최근 231거래일 (오른 날 − 내린 날) ÷ 유효일수'는 창도 정의도 이 ID 와 부호만 "
         "반대다. 그래서 이 규칙이 그것과 갈리는 지점은 ID 자체가 아니라 모멘텀 상위 "
         "5분위로 먼저 좁힌다는 것 하나뿐이다. 여기서 묻는 것은 그 사전 필터가 무엇을 "
         "더하는가이고, 증분으로 가른다. "
         "⚠ 2024년 확장연구(Finance Research Letters)는 이 단조 음관계가 상승 국면에서만 "
         "성립하고 하락 국면에선 성립하지 않는다고 보고했다. 그래서 이 표는 FIP 를 국면 무관 "
         "필터로 적지 않는다 — 전 구간 한 줄로만 내고 국면별 주장은 하지 않는다.")
    xsec("x-lowvol", "저변동성 상위 %d" % TOPN,
         "최근 60일 실현변동성이 가장 낮은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         lambda t, i, P, R, V: (-(V or 9)),
         "저변동성 이상현상. 위험을 덜 지고 더 벌 수 있는가를 이 표본에서 본다.")
    xsec("x-rev1m", "단기 반전 (1개월 최하위 %d)" % TOPN,
         "최근 1개월 수익이 가장 낮은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         lambda t, i, P, R, V: (-(ret(P, i, 21) or 9)),
         "단기 반전. 모멘텀과 정반대 방향이라 둘을 같은 표에 두면 서로의 대조군이 된다.",
         arch="smallcap-monthly-reversal")
    xsec("x-52wh", "52주 신고가 근접 %d" % TOPN,
         "현재가가 52주 최고가에 가장 가까운 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "고점 근접을 추세의 대리변수로 쓴다. 12-1 모멘텀과 얼마나 겹치는지 본다.")
    xsec("x-dist200", "200일선 이격도 상위 %d" % TOPN,
         "현재가가 200일선 위로 가장 많이 벌어진 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "추세 강도를 이격도로 재는 규칙. 과열과 강세를 구분하지 못한다는 비판이 있다.")
    xsec("x-volsurge", "거래량 급증 + 추세 %d" % TOPN,
         "20일 평균거래량이 60일 평균 대비 가장 크게 늘고 200일선 위인 %d종목, 월말 리밸런스." % TOPN,
         None, "가격에 거래량을 더한다. 거래량이 정보 유입의 대리변수라는 가정을 시험한다.")

    # ── 기각 아카이브에 있던 규칙들 — 결론만 있고 숫자가 없던 것을 여기서 돌린다 ──
    # arch: archive.html의 sid와 잇는다. 이 저장소의 데이터(주식 종가·거래량)로 만들 수 있는 것만.
    xsec("x-mom-trend", "대형주 모멘텀 + 200일선 추세",
         "12-1 모멘텀 상위 중 200일선 위인 종목만 %d개 동일가중, 월말 리밸런스." % TOPN,
         None, "모멘텀에 추세 필터를 덧대면 낙폭이 줄어드는지 본다. 아카이브의 '대형주 횡단면 모멘텀·200일선 추세'.",
         arch="largecap-momentum-200dma")
    xsec("x-rev1w", "주간 반전 (1주 최하위 %d)" % TOPN,
         "최근 5거래일 수익이 가장 낮은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "반전을 월이 아니라 주 단위로 잡는다. 아카이브의 '소형주 단기 반전 롱숏(Weekly)'을 롱온리로 옮긴 것.",
         arch="smallcap-weekly-reversal")
    xsec("x-minvar", "최소분산 (축소추정)",
         "최근 120일 공분산을 대각으로 축소(λ=0.5)해 분산이 가장 낮아지는 %d종목을 역분산 가중." % TOPN,
         None, "완전한 최적화 대신 축소추정 역분산으로 근사한다. 아카이브의 '축소추정 최소분산 배분'.",
         arch="min-variance-lw")
    xsec("x-riskbudget", "리스크 버짓 (역변동성)",
         "60일 실현변동성의 역수로 가중한 상위 %d종목(변동성 낮은 순), 월말 리밸런스." % TOPN,
         None, "위험을 균등하게 나눠 갖는다는 발상. 아카이브의 '리스크 버짓 배분'.",
         arch="risk-budgeting")
    xsec("x-lowbeta", "저베타 틸트",
         "동일가중 지수 대비 120일 베타가 가장 낮은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "저변동성과 저베타는 다르다 — 둘을 같은 표에 두고 갈라 본다. 아카이브의 '저베타 비중 틸트'.",
         arch="low-beta-weight-tilt")
    xsec("x-snapback", "추세정렬 과매도 반등",
         "200일선 위이면서 RSI(14)가 가장 낮은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "추세는 살아 있는데 단기만 눌린 종목. 이 랩이 종목 신호에서 역추세를 폐기하며 남긴 유일한 형태다.",
         arch="trend-aligned-oversold-snapback")
    # ── 논문에서 옮겨 온 횡단면 4종 ──────────────────────────────────
    # 앞의 12개는 전부 '가격이 어디에 있나'(모멘텀·이격·변동성)를 본다. 아래 넷은 다른 것을
    # 묻는다 — 지난달 수익의 **분포 꼬리**(MAX), **시점**(언제 났나), **시장을 뺀 나머지**(특이변동성).
    # 셋 다 이 표의 기존 지표와 겹칠 가능성이 큰데, 겹치는지 아닌지가 곧 확인할 내용이다.
    xsec("x-maxlow", "복권형 회피 (MAX 최하위 %d)" % TOPN,
         "최근 1개월 일별 수익의 최댓값이 가장 작은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         lambda t, i, P, R, V: (lambda m: (-m) if m is not None else None)(maxret(R, i, 21, 1)),
         "Bali·Cakici·Whitelaw(2011). 지난달에 하루 크게 튄 종목은 복권처럼 선호돼 값이 비싸지고 "
         "다음 달 수익이 낮다는 관찰. 저변동성과 얼마나 겹치는지가 이 표에서 갈린다. "
         "⚠ 원논문의 효과는 하락 구간에서 주로 나온다. 이 표본에는 그 구간이 없으므로 여기 열위는 "
         "반증이 아니라 검정 불능에 가깝다 — 판정은 규칙대로 두되 그대로 읽지 말 것.")
    xsec("x-max5low", "복권형 회피 — MAX(5) 최하위 %d" % TOPN,
         "최근 1개월 일별 수익 중 상위 5일 평균이 가장 작은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         lambda t, i, P, R, V: (lambda m: (-m) if m is not None else None)(maxret(R, i, 21, 5)),
         "MAX를 하루가 아니라 다섯 날로 재는 표준 변형. 단일 MAX와 결과가 크게 갈리면 그건 "
         "발견이 아니라 하루짜리 우연에 걸린 것이다 — 그 판정을 위해 둘을 같이 싣는다. "
         "실제로 둘의 샤프가 0.79와 0.19로 크게 갈렸다. 같은 개념인데 이만큼 벌어졌다는 것은 "
         "이 표본에서 둘 다 신뢰할 수 없다는 뜻이다.")
    xsec("x-recency", "월내 시점 가중 반전 (최하위 %d)" % TOPN,
         "최근 1개월 일별 수익을 최근일수록 크게 가중한 평균이 가장 낮은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         lambda t, i, P, R, V: (lambda m: (-m) if m is not None else None)(recency_ret(R, i, 21)),
         "A Unified Framework for Anomalies based on Daily Returns(2026) — 지난달 수익이 얼마나 "
         "컸는지보다 월 안에서 언제 났는지가 다음 달을 더 잘 설명한다는 주장. 가중을 등가중으로 "
         "두면 이 값은 그냥 1개월 수익이므로, 단기 반전(x-rev1m)과의 차이가 곧 시점 정보의 값이다. "
         "이 표본에서는 샤프 0.25 대 0.09 — 시점 가중이 단순 반전보다 낫긴 했으나 둘 다 대조군에 "
         "크게 못 미쳐, 순위만 바뀌었을 뿐 어느 쪽도 쓸 수 있는 수준이 아니다.")
    xsec("x-ivol", "특이변동성 최하위 %d" % TOPN,
         "동일가중 지수로 설명되지 않는 잔차의 120일 변동성이 가장 낮은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None,
         "Ang 외(2006). 이 표에는 저변동성과 저베타가 따로 있는데 둘 중 무엇이 원인인지 갈리지 "
         "않는다. 시장 성분을 뺀 나머지만 재면 그 둘을 나눌 수 있다. 이 표본에서 특이변동성(샤프 0.40)은 "
         "저변동성(0.33)·저베타(0.59) 사이에 놓였다 — 셋이 서로 다른 것을 재고 있다는 뜻이지만, "
         "강세장 2년으로는 어느 쪽이 옳은지 가릴 수 없다.")

    # ── 펀더멘털 2종 ────────────────────────────────────────────────
    # 배포 원장에는 같은 팩터가 'SPX Top 10'으로 올라 있다. 그 숫자는 사내 리서치 DB에서
    # 나온 것이라 여기서 다시 돌릴 수 없다. 대신 **같은 팩터를 무료 공개 데이터로,
    # 지수 구분 없이 전체 유니버스에** 얹은 판을 따로 싣는다 — 지수를 나눌 이유가 팩터에
    # 있는 게 아니라 원본 백테스트가 그 유니버스로 돌았을 뿐이기 때문이다.
    # ── 이익 서프라이즈 2종 ─────────────────────────────────────────
    # 배포 원장의 '이익추정 리비전 드리프트'는 애널리스트가 전망을 올린 종목을 산다. 그 전망은
    # 유료 데이터라 무료로는 과거를 못 구한다(저장소가 지금 직접 쌓는 중인데 25일치뿐이다).
    # 대신 **같은 현상을 애널리스트 없이** 잰다 — 실제 보고된 이익이 순진한 기준선을 얼마나
    # 넘었나(서프라이즈)와 그 개선이 가속하고 있나. 리비전 드리프트와 PEAD는 '이익 소식이
    # 한 번에 반영되지 않고 몇 달에 걸쳐 스며든다'는 같은 현상의 두 측정이다.
    # ⚠ 같은 전략이 아니다. 이쪽은 발표된 숫자를, 저쪽은 앞으로의 전망을 본다.
    xsec("x-sue", "이익 서프라이즈 (SUE 상위 %d)" % TOPN,
         "직전 공개 분기의 전년 동기 대비 EPS 변화를 그 종목의 변화 표준편차로 나눈 값이 "
         "가장 큰 %d종목 동일가중, 월말 리밸런스. 지수 구분 없이 전체 유니버스." % TOPN,
         None,
         "Foster·Olsen·Shevlin(1984)의 표준화 이익 서프라이즈. 배포 원장의 '이익추정 리비전 "
         "드리프트'가 노리는 것과 같은 현상(이익 소식이 몇 달에 걸쳐 주가에 스며든다)을 "
         "애널리스트 전망 없이 재는 방법이다. 전망 데이터는 유료라 과거를 못 구한다 — "
         "저장소가 지금 직접 쌓고 있으나 아직 25일치뿐이다. 회계 숫자는 기간 종료 90일 뒤에만 쓴다.")
    xsec("x-epsacc", "이익 개선 가속 상위 %d" % TOPN,
         "전년 동기 대비 EPS 변화가 직전 분기보다 얼마나 더 커졌는지를 주가로 나눈 값이 "
         "가장 큰 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None,
         "SUE의 짝. SUE는 종목별 표준편차로 나누는데 그 분모가 작은 회사(이익이 매우 안정적인 "
         "회사)가 위로 몰리는 성질이 있다. 이건 나누지 않으므로, 둘이 같은 결과면 표준화가 "
         "결과를 만든 게 아니고 갈리면 그 반대다. '좋아지는 중'을 본다는 점에서 리비전 쪽에 "
         "더 가까운 측정이기도 하다.")

    # ── 팩터 상위 10 목록 8종 ────────────────────────────────────────
    # "이 지표로 뽑으면 어떤 종목이 나오나"를 지표마다 보고 싶다는 요청. 목록만 만들면 그
    # 목록이 좋은지 알 수 없으므로, **목록 자체를 월말 리밸런스 전략으로 돌린다** — 그러면
    # 카드의 '지금 보유'가 곧 그 지표의 상위 10 목록이고, 옆에 성적이 붙는다.
    # 회계 숫자는 전부 기간 종료 90일 뒤에만 쓰고(공시 전 숫자로 고르지 않는다), 잔고는
    # 시점 값, 매출·이익·배당은 12개월 누적을 쓴다.
    xsec("x-ep", "저PER (이익수익률 상위 %d)" % TOPN,
         "12개월 주당순이익 ÷ 주가가 가장 큰 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "PER의 역수로 줄을 세운다. 역수를 쓰는 이유는 적자 기업의 PER이 음수가 되면서 "
               "'가장 싼 종목'으로 둔갑하는 것을 막기 위해서다 — 이익수익률은 적자면 그냥 음수라 "
               "자연히 꼴찌로 간다.")
    xsec("x-sp", "저PSR (매출수익률 상위 %d)" % TOPN,
         "12개월 매출 ÷ 시가총액이 가장 큰 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "이익이 아직 안 나는 회사도 줄을 세울 수 있는 밸류 지표. 이익률이 낮은 업종이 "
               "구조적으로 위로 몰리므로 섹터 편중을 보고 읽어야 한다.")
    xsec("x-roe", "고ROE 상위 %d" % TOPN,
         "12개월 순이익 ÷ 자본총계가 가장 큰 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "퀄리티 팩터의 대표. 자본이 적은 회사(자사주를 많이 산 회사)가 위로 오는 성질이 "
               "있어, 부채를 많이 쓴 회사와 진짜 고수익 회사가 섞인다 — 저부채 목록과 겹쳐 보면 갈린다.")
    xsec("x-npm", "고순이익률 상위 %d" % TOPN,
         "12개월 순이익 ÷ 12개월 매출이 가장 큰 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "ROE와 달리 자본 구조에 안 휘둘리는 수익성 지표. 둘을 같이 두면 'ROE가 높은 이유가 "
               "장사를 잘해서인지 빚을 써서인지'가 갈린다.")
    xsec("x-rgrow", "고매출성장 상위 %d" % TOPN,
         "12개월 매출이 1년 전 12개월 매출보다 많이 늘어난 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "성장 팩터. 이익이 아니라 매출로 재는 이유는 이익이 회계 처리에 더 많이 휘둘리기 "
               "때문이다. 인수합병으로 늘어난 매출도 그대로 잡힌다 — 이 표는 그것을 구분하지 못한다.")
    xsec("x-lowde", "저부채 상위 %d" % TOPN,
         "부채 ÷ 자본총계가 가장 낮은 %d종목 동일가중, 월말 리밸런스(자본잠식 종목 제외)." % TOPN,
         None, "재무 안정성 팩터. 부채 태그가 없는 종목은 자산 − 자본으로 메운다(태그 보유 365종목 "
               "→ 507종목). 금리가 오르는 국면에서만 값을 한다는 비판이 있어 구간을 봐야 한다.")
    xsec("x-dy", "고배당수익률 상위 %d" % TOPN,
         "12개월 주당배당 ÷ 주가가 가장 큰 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "배당 팩터. 배당을 선언하지 않는 종목(유니버스의 약 30%)은 애초에 순위에 없다. "
               "감액 직전에 수익률이 가장 높아 보이는 함정이 있다 — 이 표는 그것을 걸러내지 않는다.")
    xsec("x-small", "소형주 상위 %d" % TOPN,
         "시가총액(주가 × 희석주식수)이 가장 작은 %d종목 동일가중, 월말 리밸런스." % TOPN,
         None, "규모 팩터(SMB). 다만 이 유니버스는 S&P 500 ∪ NASDAQ 100이라 '소형'이라 해도 대형주 "
               "안에서 작은 쪽일 뿐이다 — 원논문의 소형주 효과와 같은 것을 재고 있지 않다. "
               "⚠ 이 표에서 유일하게 다중검정 문턱을 넘었지만(t 4.09), 그 숫자를 그대로 믿으면 안 된다. "
               "이 랩의 생존편향이 정확히 이 전략에 가장 세게 걸린다 — 유니버스가 '오늘의 518종목'이라 "
               "그 사이 지수에서 빠진 회사가 하나도 없다. 지수에서 빠지는 것은 대개 작아진 회사이므로, "
               "'가장 작은 10종목'은 사실상 '작아졌다가 살아남아 되돌아온 10종목'만 고른 것이 된다. "
               "편출 이력이 이 저장소에 없어 보정할 수 없다. 판정은 규칙대로 두되 근거로 쓰지 말 것.")

    xsec("x-btp", "장부가 대비 저평가 (Book-to-Price 상위 %d)" % TOPN,
         "주당순자산(SEC XBRL 자본총계 ÷ 희석주식수)을 주가로 나눈 값이 가장 큰 %d종목 "
         "동일가중, 월말 리밸런스. 지수 구분 없이 전체 유니버스." % TOPN,
         None,
         "Fama-French 밸류(HML)의 단변량판. 배포 원장의 'Book-to-Price · SPX Top 10'과 같은 "
         "팩터를 NASDAQ 100까지 합친 유니버스에 얹은 것이다. 회계 숫자는 기간 종료일로부터 "
         "90일이 지난 뒤에만 쓴다(공시 전 숫자로 고르지 않기 위해). 다만 저장된 값은 재작성 "
         "이후의 값이라 그 편향은 남는다.")
    # ── E30 섹터 중립 밸류 컴포지트 (사전등록 PREREG-2026-08-06-E30VALUE.md) ──
    # 🚨 카드가 판정 방식을 스스로 규정했다 — "(a)단순 장부가 밸류 · (b)섹터 제약 없는
    #   컴포지트 · (c)섹터 중립 컴포지트 3자 비교". (a)는 위 x-btp 다(t 2.72 · 구별 불가).
    #   묻는 것은 "밸류가 돈이 되는가"가 아니라 **"x-btp 의 실패가 종목선택 실패였나
    #   업종 베팅 실패였나"** 이고, 답은 (c)−(b) 가 한다.
    # 🚨 카드가 지정한 네 지표 중 **예상 FCF/P 는 원리적으로 불가능**하다 — 애널리스트
    #   추정은 스냅샷만 있고 과거 시점 값이 없다(data/asof.json 의 선행 컨센서스 축이
    #   스스로 "백테스트에 못 쓴다"고 적어 두었다). 셋만 쓴다.
    _E30_MET = "장부가/주가 · 잉여현금흐름/주가 · 장부가/기업가치(총부채 근사) 세 지표를 "                "월말 단면 z-점수로 바꿔 단순평균한 밸류 종합점수"
    _E30_WHY = ("AQR 이 밸류를 '산업 내' 정의로 구성하는 논리 — 제약 없는 밸류 스크린은 회계상 " 
                "싸 보이는 금융·에너지를 과대편입하고 기술주를 과소편입해, 성패가 종목선택이 " 
                "아니라 업종 방향에 좌우된다. 업종마다 회계 구조와 정상 밸류에이션 수준이 달라 " 
                "같은 업종 안에서 비교해야 순수한 상대 저평가 정보가 남는다는 것이다. "
                "이 랩의 x-btp 기각이 업종 베팅 탓이었는지를 가린다.")
    xsec("x-valcomp", "밸류 컴포지트 상위 %d (섹터 제약 없음)" % TOPN,
         _E30_MET + "가 가장 큰 %d종목 동일가중, 월말 리밸런스. 지수 구분 없이 전체 유니버스." % TOPN,
         None, _E30_WHY,
         arch="within-industry-value")
    xsec("x-valcomp-sn", "섹터 중립 밸류 컴포지트 (GICS 11섹터 × 1종)",
         _E30_MET + "를 각 GICS 섹터 안에서 매겨 섹터별 1위 1종목씩 담는다(11종). "
         "섹터 비중은 그 시점 유니버스의 섹터 시총 비중에 맞춘다 — 섹터 배분이 지수와 "
         "같아지므로 업종 베팅이 제거되고 섹터 내 상대가치만 남는다. 월말 리밸런스.",
         None, _E30_WHY,
         arch="within-industry-value")
    xsec("x-fcfy", "잉여현금흐름 수익률 상위 %d" % TOPN,
         "주당 잉여현금흐름(영업현금흐름 − 자본지출)을 주가로 나눈 값이 가장 큰 %d종목 "
         "동일가중, 월말 리밸런스. 지수 구분 없이 전체 유니버스." % TOPN,
         None,
         "배포 원장에는 이 팩터가 '개선분(ΔFCF Yield)'으로 올라 있는데, 무료 데이터로는 "
         "그 변화량을 같은 품질로 못 만든다 — 자본지출 태그가 515종목 중 433종목에만 있고 "
         "현금흐름이 분기가 아니라 연 단위로만 들어오는 종목이 많아, 차분을 내면 1년 간격이 된다. "
         "그래서 변화가 아니라 수준(레벨)으로 싣고 이름도 그렇게 붙였다. 원장의 개선분판과 같은 "
         "전략이 아니다.")

    timing("t-disp", "횡단면 분산도 게이트",
           "종목 간 수익률 분산(횡단면 표준편차)이 과거 1년 중앙값보다 낮으면 편입, 높으면 현금.",
           None, "분산도가 높을 때가 위험 국면이라는 가설. 아카이브의 '횡단면 분산도 리스크 게이트'.",
           arch="cross-sectional-dispersion-gate")
    timing("t-kelly", "켈리 스케일링 (레버리지 없음)",
           "최근 120일 평균수익/분산으로 켈리 비중을 계산해 0~1로 자른다.",
           None, "기대수익과 위험을 한 식에 넣는다. 레버리지를 안 쓰므로 상한 1에서 잘린다. 아카이브의 '켈리 기준 레버리지 스케일링'.",
           arch="kelly-scaling")

    # ── 2026-07-31 웹·GitHub·논문 리서치로 추가한 5종 ──────────────────────
    # 선정 기준을 바꿨다. 지난 6종은 '랩에 없는 축'이면 넣었는데, 이번에는 JKP(Jensen·Kelly·
    # Pedersen, JF 2023)의 **13개 테마 분류표**에 랩 34종을 매핑해 **0개짜리 칸**부터 메웠다.
    # 이유는 실측이다 — 붐비는 칸에 하나 더 얹으면 새 정보 없이 다중검정 족 수만 늘어난다
    # (지난번 에코 모멘텀이 그랬다: 12-1 대비 증분 알파 t 1.01).
    #   빈 칸이었던 것: Accruals(0) · Quality의 총이익축(0) · Profitability의 현금축(0) ·
    #                  Investment의 비정상투자축(0) · Long-Term Reversal(0)
    #   일부러 안 넣은 것: 저상관(BAC)·경로일관성(CNTD) — 각각 저위험 7종·모멘텀 4종이라는
    #     가장 붐비는 칸의 8번째·5번째다. 적대감사가 ρ(BAC, 베타)=0.390 · ρ(CNTD, 12-1)=0.605 를
    #     실측했고, 넣으려면 단독 판정이 아니라 기존 규칙 대비 증분 알파로 걸러야 한다.
    xsec("x-poacc", "퍼센트 영업발생액 회피 (이익의 현금 뒷받침)",
         "(순이익 − 영업현금흐름) ÷ |순이익| 이 가장 낮은 %d종목 동일가중, 월말 리밸런스. "
         "둘 다 최근 12개월치를 쓴다." % TOPN,
         None,
         "Sloan(1996) 발생액 이상현상의 Hafzalla·Lundholm·Van Winkle(2011) 퍼센트 판이다. "
         "이익이 현금으로 뒷받침되지 않는 회사가 이후 부진하다는 것으로, 이 랩의 34종에 "
         "발생액 축이 통째로 없었다(JKP 13개 테마 중 0개짜리 칸). "
         "분모를 자산이 아니라 |순이익|으로 두는 판을 고른 이유가 데이터에 있다 — 자산(잔고) 태그는 "
         "KEEP_I=20 절단 탓에 2021-06 부터라 자산분모 규칙은 표본이 4.9년으로 잘리는데, "
         "이 판은 손익·현금흐름만 써서 2018-10 부터 7.8년을 쓴다. "
         "⚠ 순이익이 0 근처면 비율이 폭발하므로 |순이익|이 매출의 1% 미만인 관측은 뺀다.")
    xsec("x-gpa", "총이익 자산대비 (Gross Profitability)",
         "(매출총이익 ÷ 총자산)이 가장 큰 %d종목 동일가중, 월말 리밸런스. 금융업 제외." % TOPN,
         None,
         "Novy-Marx 'The Other Side of Value'(JFE 2013). 순이익보다 총이익이 미래 수익성을 "
         "더 잘 예측한다는 것이다 — 판관비·감가상각·이자는 회계 재량이 크게 섞이는데 총이익은 덜하다. "
         "이 랩의 수익성 축은 고ROE(순이익/자본)와 고순이익률(순이익/매출)뿐이라 둘 다 순이익 기반이고 "
         "자산 분모가 없었다. "
         "🚨 gp 태그가 38%%뿐이라 매출−매출원가 폴백을 쓰는데, 그대로 두면 건강보험사가 상위를 "
         "차지한다(benefit expense 를 매출원가로 태깅하지 않아 총이익이 과대계상된다). 그래서 "
         "(1) 금융업 제외 (2) gp·cogs 가 둘 다 있으면 |gp+cogs−rev|/rev < 1%% 정합성 검사를 "
         "통과한 것만 쓴다. 적대감사 실측으로 이 검사가 180종 중 16종(CMI 2.99·ABBV 0.52 등)을 걸러낸다.")
    xsec("x-ocfp", "현금기반 수익성 (영업현금흐름 ÷ 총자산)",
         "최근 12개월 영업현금흐름을 총자산으로 나눈 값이 가장 큰 %d종목 동일가중, 월말 리밸런스. "
         "금융업 제외." % TOPN,
         None,
         "Ball·Gerakos·Linnainmaa·Nikolaev 'Deflating Profitability'(JFE 2016)의 현금 기반 "
         "수익성 축약판이다. 발생액을 걷어낸 수익성이 발생액이 섞인 수익성보다 낫다는 것으로, "
         "위 발생액 규칙과 같은 관찰의 다른 쪽 끝이다(그쪽은 발생액을 벌하고 이쪽은 현금을 상준다). "
         "cfo·자산 커버리지가 각각 100%%라 이 랩의 수익성 후보 중 데이터가 가장 좋다. "
         "⚠ 원식의 분자는 운전자본 변동까지 조정한 것인데 이 랩엔 그 태그(rect·invt·ap)가 없어 "
         "영업현금흐름 자체를 쓴다 — 원논문 t 를 그대로 기대치로 읽지 말 것.")
    xsec("x-aci", "비정상 자본투자 회피 (설비투자 급증 회피)",
         "설비투자÷매출이 직전 3개 회계연도 평균 대비 가장 낮은 %d종목 동일가중, 월말 리밸런스. "
         "금융업 제외." % TOPN,
         None,
         "Titman·Wei·Xie 'Capital Investments and Stock Returns'(JFQA 2004). 자기 과거 대비 "
         "설비투자를 갑자기 늘린 회사가 이후 부진하다는 것이다. 이 랩에 자산성장 회피(총자산 증가율)는 "
         "있지만 그건 인수·운전자본까지 섞인 총량이고, 이쪽은 설비투자만 자기 과거와 견준다. "
         "🚨 4개 회계연도가 필요한데 분기(q) 버킷의 설비투자는 Q1 만 남아 있어 쓸 수 없다 — "
         "연간(a) 버킷으로 계산한다(ttm 독스트링의 현금흐름표 함정 참조). "
         "⚠ 매출이 0 이하인 해와 비율이 ±300%%를 벗어나는 관측은 뺀다.")
    xsec("x-ltrev", "장기 반전 (5년 전 ~ 1년 전)",
         "5년 전부터 1년 전까지의 누적수익률이 가장 낮은 %d종목 동일가중, 월말 리밸런스"
         "(최근 1년은 통째로 제외 — 모멘텀 구간과 겹치지 않게)." % TOPN,
         lambda t, i, P, Rt, V: (lambda r: (-r) if r is not None else None)(ret(P, i - 252, 1008)),
         "De Bondt·Thaler(1985) 과잉반응 가설. 오래 진 종목이 이후 이긴다는 것으로, 발표된 이상현상 "
         "중 가장 오래된 축에 든다. 이 랩의 반전 축은 1주·1개월·월내 시점가중 셋 다 단기이고 "
         "모멘텀은 12-1·에코로 중기라, 3~5년 지평은 통째로 비어 있었다. "
         "⚠ 룩백이 1260거래일이라 10년 패널에서 유효 구간이 절반으로 줄고, 커버리지 게이트가 "
         "그때까지 무보유로 두므로 시작일이 자동으로 늦춰진다(그 편이 정직하다).")

    # ── 2026-07-31 2차: 붐비는 칸의 후보 3종 — 사전등록한 게이트로 판정한다 ────────
    # 이 셋은 어제 리서치에서 '실현가능성은 통과했는데 붐비는 칸이라 단독 t 로는 판단 불가'로
    # 보류했던 것이다(저위험 7종·모멘텀 4종·환원 1종). 이제 증분 알파 기계가 있으므로 넣는다.
    #
    # 🚨 **판정 기준을 돌리기 전에 못박는다** — '가장 닮은 기존 규칙 대비 증분 알파 |t| ≥ 2'.
    #   돌려 보고 기준을 정하면 그건 검정이 아니다. 그리고 **떨어져도 지우지 않는다** —
    #   진 것을 지우면 다중검정 족 수가 줄어 남은 규칙이 쉽게 통과한다(이 랩이 피해 온 방향).
    #   결과는 카드의 '증분 알파' 줄에 그대로 나오고, 통과 여부는 독자가 그 줄로 읽으면 된다.
    xsec("x-payout", "총주주환원수익률 (배당 + 자사주매입)",
         "최근 12개월 배당총액과 자사주매입액을 더해 시가총액으로 나눈 값이 가장 큰 %d종목 "
         "동일가중, 월말 리밸런스." % TOPN,
         None,
         "Boudoukh·Michaely·Richardson·Roberts(JF 2007). 배당만 보면 환원의 절반을 놓친다는 "
         "것이다 — 미국 기업의 주주환원은 2000년대 이후 자사주매입이 배당을 넘었다. "
         "이 표의 환원 축은 고배당수익률 하나뿐이라 자사주가 통째로 빠져 있었다. "
         "🚨 자사주(bb) 태그는 분기 버킷에 Q1 만 남아 있어(현금흐름표가 YTD 누적이다) "
         "연간 버킷으로 읽는다 — 그러지 않으면 환원율이 4배 과소된다(ttm 독스트링 참조). "
         "⚠ 고배당수익률과 겹치는 축이므로 단독 t 가 아니라 그 규칙 대비 증분 알파로 읽을 것.")
    xsec("x-lowcorr", "시장 저상관 (베타의 상관 성분만)",
         "최근 252거래일 일간수익률과 동일가중 지수의 상관이 가장 낮은 %d종목 동일가중, "
         "월말 리밸런스(유효관측 80%% 이상)." % TOPN,
         None,
         "Frazzini·Pedersen(JFE 2014)은 베타를 ρ×(σ종목/σ시장)으로 쪼갠다. 이 표의 저베타는 "
         "두 성분이 섞여 있어 '시장과 덜 움직인다'와 '덜 흔들린다'가 구별되지 않는다 — "
         "여기서는 변동성 크기를 빼고 동조 여부만 본다. "
         "⚠ 이 표의 저위험 칸은 이미 7종(저변동성·특이변동성·저베타·최소분산·리스크버짓·"
         "복권형 둘)으로 가장 붐빈다. 리서치 감사가 ρ(이 규칙, 저베타)=0.39 를 실측했다 — "
         "단독 t 로 판단하면 안 되고 증분 알파로 걸러야 한다.")
    xsec("x-cntd", "경로 일관성 (오른 날 − 내린 날)",
         "최근 231거래일 중 (오른 날 − 내린 날) ÷ 유효일수가 가장 큰 %d종목 동일가중, "
         "월말 리밸런스." % TOPN,
         lambda t, i, P, Rt, V: updown(Rt, i, 231),
         "Da·Gurun·Warachka(RFS 2014)의 정보 이산성에서 쓰는 성분이다. 이 표의 모멘텀·반전은 "
         "전부 수익률 크기로 만들어져 있어, 같은 12개월 수익이라도 잘게 꾸준히 올랐는지 "
         "한 번에 튀었는지는 재지 못한다. 부호 개수만 세면 그 축이 분리된다. "
         "🚨 원 논문의 신호는 이것 단독이 아니라 '모멘텀과 곱한 조건부 신호'다. 단독 정렬로 "
         "바꾼 것이므로 원 논문의 t 를 이 규칙의 기대치로 읽으면 안 된다. "
         "⚠ 리서치 감사 실측 ρ(이 규칙, 12-1 모멘텀)=0.605 — 증분 알파로 걸러야 한다.")

    # ── 2026-07-30 웹 리서치로 추가한 6종 ─────────────────────────────────
    # 출처는 Chen·Zimmermann Open Source Asset Pricing(github.com/OpenSourceAP/CrossSection)의
    # 신호 정의 코드와 원논문이다. 그 저장소는 ~300개 신호를 파이썬으로 공개해 계산식·창 길이·
    # 부호를 코드로 확인할 수 있다 — 이 랩이 필요한 '숫자로 된 정의'를 그대로 준다.
    #   ⚠ 랩에 이미 있는 축(모멘텀·저변동·밸류·수익성)과 겹치지 않는 것만 골랐고, 선별 단계에서
    #     실측으로 걸러 낸 함정을 각 구현에 반영했다(아래 주석).
    xsec("x-echo", "에코 모멘텀 (12~7개월 전 구간)",
         "최근 6개월을 완전히 무시하고 12개월 전~7개월 전 6개월 누적수익률이 가장 큰 %d종목 "
         "동일가중, 월말 리밸런스." % TOPN,
         lambda t, i, P, Rt, V: ret(P, i - 126, 126),
         "Novy-Marx 'Is momentum really momentum?'(JFE 2012). 모멘텀의 예측력이 최근 6개월이 "
         "아니라 그보다 앞선 중기 구간에서 온다는 주장이다. 이 표의 12-1 모멘텀은 최근 1개월만 "
         "빼는데, 여기서는 최근 6개월을 통째로 뺀다. "
         "🚨 처음 이 자리에 '창이 겹치지 않으므로 어느 구간이 일하는지 갈라 볼 수 있다'고 적었는데 "
         "사실이 아니다 — 12-1 은 ret(252)−ret(21) 이고 그 252일 성분이 에코 창을 전부 포함한다. "
         "월별 보유 교집합 중앙이 0.50 이고, 12-1 을 이미 들고 있으면 이 규칙이 추가로 주는 것이 "
         "있는지는 아래 '증분 알파' 줄에서 확인할 것(그 값은 매 실행 도출된다 — 여기 손으로 적었던 "
         "수치는 표본이 바뀌면 조용히 낡는다). 별개 축으로 세지 말 것(다중검정 족 수를 부풀린다).")
    xsec("x-season", "동월 계절성 (같은 달 과거 2~5년 평균)",
         "다음 달과 같은 달의 과거 2·3·4·5년 전 월수익률 평균이 가장 큰 %d종목 동일가중, "
         "월말 리밸런스(결측 연도는 제외하고 남은 것의 평균)." % TOPN,
         None,
         "Heston·Sadka(2008). 종목마다 특정 달에 강한 경향이 있다는 주장이다. 이 랩에 있는 "
         "계절성은 '11~4월만 보유'(시장 전체)뿐이고 종목별 달력 축은 없었다. "
         "⚠ 5년 룩백이라 10년 패널에서 유효 구간이 절반으로 줄고, 관측이 종목당 최대 4개뿐이라 "
         "평균이 잡음에 약하다. 계절성은 원래 데이터 스누핑에 가장 취약한 축이다.")
    xsec("x-coskew", "공편왜도 최저 (가장 음의 꼬리 동조)",
         "최근 252거래일 일별수익으로 공편왜도 E[(ri−μi)(rm−μm)²]/(sd(ri)·var(rm))를 구해 "
         "가장 음인 %d종목 동일가중, 월말 리밸런스(유효관측 200일 이상)." % TOPN,
         None,
         "Ang·Chen·Xing 'Downside Risk'(RFS 2006) 식(6). 시장이 크게 흔들릴 때 같이 무너지는 "
         "종목은 그 위험의 대가로 더 높은 수익을 요구받는다는 것이다. 이 표의 저베타·특이변동성은 "
         "둘 다 2차 모멘트이고, 꼬리의 비대칭은 그것들이 못 재는 축이다.")
    xsec("x-agrow", "자산성장 회피 (총자산 증가 최저)",
         "총자산의 전년 동기 대비 증가율이 가장 낮은 %d종목 동일가중, 월말 리밸런스. "
         "총자산이 0 이하인 분기는 제외하고, 증가율은 ±200%%로 자른다." % TOPN,
         None,
         "Cooper·Gulen·Schill(JF 2008). 자산을 빠르게 늘린 회사가 이후 부진하다는 것으로, "
         "투자(investment) 팩터의 대표 대리변수다. 이 표에 자산 규모(소형주)는 있지만 "
         "그 변화율 축은 없었다. "
         "⚠ 총자산이 0 으로 들어온 분기가 실제로 있다(PSKY 2025-03·06, SW 2024-03). 분자가 0 이면 "
         "증가율이 −100%로 1등이 되어 자료 구멍이 편입된다 — 그래서 0 이하를 먼저 뺀다.")
    xsec("x-shiss", "순주식발행 회피 (희석주식수 증가 최저)",
         "가중평균 희석주식수의 전년 동기 대비 증가율이 가장 낮은(자사주 소각) %d종목 동일가중, "
         "월말 리밸런스. 증가율 절대값이 50%%를 넘으면 제외." % TOPN,
         None,
         "Pontiff·Woodgate(JF 2008). 주식을 새로 찍는 회사는 부진하고 줄이는 회사는 낫다는 것이다. "
         "이 표의 총주주환원 축은 배당(고배당수익률)뿐이고 주식수 축은 없었다. "
         "🚨 적대감사가 이 규칙의 첫 구현을 무효로 만들었다. split_trim 이 분할 이음매 이전 이력을 "
         "전부 지우는데, 대규모 발행이야말로 이음매로 잡힌다 — OMC 20개 관측 중 19개 삭제(단절의 "
         "정체는 분할이 아니라 IPG 합병 대가 발행 +53%), MSTR 12/20 삭제(ATM 대량발행). 즉 이 규칙이 "
         "벌해야 하는 종목이 꼴찌가 아니라 후보에서 사라졌다. 지금은 단위오류만 교정한 계열을 쓰고 "
         "이음매를 건너뛰는 짝만 버린다. 문서의 절대값 50% 컷은 실측 0.2%만 걸러 사실상 무해했다. "
         "⚠ 태그는 가중평균 '희석' 주식수다(시점 잔고가 아니라 기간 평균). 옵션·전환권 희석이 "
         "섞이고 소각 반영이 최대 1분기 늦다 — 원논문의 순발행과 같지 않다.")
    # 규약은 build/PREREG-2026-08-04-CUSTCONC.md 에 **자료를 모으기 전에** 확정해 커밋했다.
    # 게시 기준도 거기 셋으로 적어 뒀다 — 단독 t 임계 · incr5.t ≥ 2.0 · PIT 레그도 통과.
    xsec("x-custconc", "고객 집중도 상위 10 (단일 고객 매출 비중)",
         "10-K·20-F 원문에 공시된 단일 고객 매출 비중이 가장 높은 %d종목 동일가중, "
         "월말 리밸런스. 값은 그 10-K 제출일부터 쓰고 다음 10-K 까지 유지하며, "
         "540일보다 오래되면 없는 것으로 둔다." % TOPN,
         None,
         "Dhaliwal·Judd·Serfling·Shaikh(2016, JAE)와 Campello·Gao(2017, JFE). 고객 집중이 높은 "
         "기업은 협상력 열위·수요 충격 노출을 지고 자본시장이 그것을 요구수익률에 반영한다 — "
         "자기자본비용이 높고 대출 스프레드가 넓다. 그렇다면 기대수익도 높아야 한다. "
         "⚠ 반대 방향 문헌도 있다(Patatoukas 2012 — 집중이 운영 효율을 높인다). 방향은 결과 보기 "
         "전에 자본비용 계열을 따라 고집중 롱으로 고정했다. "
         "🚨 이 값은 XBRL 이 아니라 원문 텍스트에서 뽑는다(SEC companyfacts 는 고객 집중이 "
         "붙는 차원을 걷어낸다). 추출은 브리틀해서 만드는 동안 다섯 번 틀렸고 표본 검산으로 "
         "잡았다 — 부정문('does not have … 10 percent or more')을 집중 10%로 읽던 것, "
         "'10 percent or more' 의 문턱 숫자를 값으로 쓰던 것, 마침표로 문장을 잘라 소수점에서 "
         "끊기던 것, %% 뒤의 단어경계 때문에 백분율이 하나도 안 잡히던 것, 창 안 최댓값을 "
         "집어 무관한 수를 달던 것. 지금은 '단일고객 표지 → customer → 서술어 → 백분율' "
         "순서를 강제하고 뽑은 문장을 함께 저장한다(data/cust_conc.json). "
         "🚨 2026-08-05 자료 타당성 기각 — 그 다섯 번의 검산이 여섯 번째를 못 잡았다. "
         "추출기가 백분율의 주어를 확인하지 않아, 고객이 아닌 것의 비중이 그대로 실렸다. "
         "적대감사 실측(보유칸 1,990개 전수 분류): 약 46%가 단일고객 매출 비중이 아니다 — "
         "제품믹스 246 · 지역/부문 251 · 채널 120 · 비용 86 · 조달 54 · 복수고객 합산 66. "
         "실제 저장된 문장: UNH 99.0 은 미국 지역 매출, PGR 95.0 은 개인차량 제품군, "
         "ECHO 61.7 은 원가율, SO 53.7 은 자기자본비율이다(게다가 3.49%를 49.0 으로 읽던 "
         "백분율 경계 버그도 있었다). 199개 월말 전부가 최소 2칸 오염이고, 마지막 바스켓 "
         "10종 중 6종이 그 목록이다. 즉 t 4.02 는 절반이 다른 것으로 채워진 계열의 수치다. "
         "x-illiq 과 같은 자리다 — 숫자가 기준을 넘었는지가 아니라 그 숫자가 재려던 것이 "
         "아니었다. "
         "🚨 2026-08-05 재수집 결과 — 더 큰 것이 나왔다. 고친 추출기로 8,798건을 다시 훑어 "
         "2,987관측을 받았는데, 이번에는 문맥을 31자가 아니라 160자로 저장했다. 그 넓힌 창이 "
         "뜻이 정반대인 문장을 드러냈다. 부정 검사를 매치 구간 안에서만 하고 있었는데 "
         "TIGHT2 는 `customer` 낱말에서 매치가 시작한다 — 부정어는 그 앞에 온다. "
         "'No single customer accounted for more than 10%%' 에서 'No single' 이 검사 밖이라 "
         "어떤 고객도 10%%를 넘지 않았다는 진술이 집중도 10%%로 기록됐다. 결측보다 나쁘다: "
         "집중이 낮다는 사실이 높다는 값으로 뒤집혀 들어간다. 저장된 문맥으로 전수 재판정하면 "
         "2,987 중 1,752건(58.7%%)이 부정문·문턱문구·복수고객 합산이다(NEG 1,583 · MANY 158 · "
         "THRESH 11). 값이 정확히 10.0 인 관측이 전체의 57.2%% 인데, 10%%는 SEC 공시 문턱이지 "
         "측정된 집중도가 아니다. 이전본이 이 오염을 안 보여 준 것은 고쳐져서가 아니라 "
         "저장 문맥이 31자여서 부정어가 잘려 나갔기 때문이다 — 값과 날짜는 이전본과 같다. "
         "고친 것: 부정·문턱·복수 검사를 문장 경계까지 넓히고(앞 220자·뒤 40자), "
         "NEG 에 'no {형용사} customer'(no individual/other/nonaffiliated/end-customer)를, "
         "THRESH 에 어순이 뒤집힌 'more than 10 percent' 를 넣었다. "
         "⚠ data/_custconc_raw.json 은 이름과 달리 원문이 아니라 재개용 결과 체크포인트다 — "
         "오프라인 재추출은 불가능해 EDGAR 8,798건을 다시 받았다. "
         "🚨 2026-08-05 재수집·재측정 완료 — 자료를 고치니 수치가 무너졌다. "
         "깨끗해진 자료는 158사·993관측이다(오염본 322사·3,285관측). 잔여 오염은 추출기와 "
         "같은 문장 경계 규약으로 재면 993건 중 1건(0.1%%)이고, 그 하나도 부정문이 아니라 "
         "세그먼트 단위 집중도다(GLW 2015 'In the Optical Communications segment'). "
         "사라진 2,292관측의 대부분이 '어떤 고객도 10%%를 넘지 않았다'였다 — 집중이 낮은 "
         "기업들이 상위 바스켓을 채우고 있었다는 뜻이다. "
         "t 4.09 → 2.78 · incr5 알파 8.31 → 5.68(t 2.78). 임계 3.36 아래다. "
         "그리고 이웃이 통째로 바뀌었다: 예전엔 '고매출성장 상위 10'과 겹쳤는데 지금은 "
         "저변동성·저베타·복권형 회피·시장 저상관과 겹친다(incr 상대 저변동성 corr 0.363). "
         "즉 깨끗한 고객집중 상위 바스켓은 성장주 묶음이 아니라 저변동 묶음이다 — "
         "규칙이 무엇을 사고 있었는지 자체가 달랐다. 매매대상 대비로는 t 0.24 로 사실상 0. "
         "커버리지는 규칙을 돌리기에 부족하지 않다(월말 유효값 중앙 59종·최소 39종). "
         "자료가 모자라 못 재는 것이 아니라, 제대로 재니 없더라는 결론이다.")
    xsec("x-cash", "현금성자산 비율 상위 (현금및현금성자산 ÷ 총자산)",
         "최신 분기 현금및현금성자산을 총자산으로 나눈 값이 가장 큰 %d종목 동일가중, "
         "월말 리밸런스." % TOPN,
         None,
         "Palazzo(JFE 2012). 현금을 많이 쥔 회사가 위험이 커질 때 더 잘 버틴다는 것이다. "
         "이 표의 재무구조 축은 부채(저부채)뿐이고 자산 쪽 현금 축은 없었다. "
         "🚨 원논문의 분자는 '현금+단기투자'인데 이 랩의 cash 태그는 현금및현금성자산만이다. "
         "이탈이 순위에 결정적이라는 것이 실측으로 확인됐다 — 현금부자 대형주 6종(AAPL·MSFT·GOOGL·"
         "META·NVDA·AMZN)의 편입 횟수가 107회 중 전원 0회다. 유동성을 유가증권으로 굴리는 "
         "회사가 구조적으로 전부 빠지므로, 이것은 '현금비율 상위'가 아니라 '현금을 유가증권으로 "
         "안 굴리는 회사 상위'다. 그래서 이름도 그렇게 고쳤다. 은행은 CashAndDueFromBanks 를 써서 "
         "금융 76종 중 34종이 태그 결측이다. 원논문 t 를 이 표의 기대치로 읽지 말 것.")
    xsec("x-hlspread", "고저가 스프레드 상위 %d (변동성 중립)" % TOPN,
         "각 종목의 최근 252거래일 Corwin-Schultz 고저가 스프레드 추정치(일별, 야간 갭 보정, "
         "음수는 0) 평균을 낸다. 유효일 126일 미만·월말 주가 $5 미만은 제외. 그 달 후보 전체에 "
         "대해 log(스프레드)를 log(252일 실현변동성)에 횡단면 회귀하고 그 잔차 상위 %d종을 "
         "동일가중으로 산다. 월말 리밸런스." % TOPN,
         None,
         "Corwin·Schultz(JF 2012). 사전등록: build/PREREG-2026-08-04-HLSPREAD.md. "
         "🚨 이 랩의 유동성 축은 한 번 죽었다 — Amihud ILLIQ(x-illiq)는 t 5.31·증분 t 3.20 으로 "
         "게시 기준을 둘 다 넘고도 기각됐다. 분자가 미국 상장분 거래대금인데 분모(시가총액)가 "
         "전 클래스·전 시장이라, 재고 있던 것이 '거래가 어려운 회사'가 아니라 '미국에서 일부만 "
         "거래되는 회사'였기 때문이다(보유칸 32.7%가 13종). 유통물량으로 고치는 길은 무료 자료가 "
         "깨져 막혀 있다(27종이 유통물량 > 발행주식수). 고저가 스프레드는 거래대금도 "
         "발행주식수도 안 쓴다 — 그 함정을 정의상 밟지 않는다. 실측으로도 그렇다: x-illiq 이 "
         "과다 선택하던 11종이 여기서는 보유칸의 2.0%다(ASML·BF.B·CCEP·FOXA·FER 는 0칸). "
         "⚠ 변동성 중립화는 선택이 아니다 — 원신호는 실현변동성과 횡단면 상관 중앙 0.816 이라 "
         "중립화 없이 쓰면 저변동성 계열을 뒤집어 다시 파는 것이 된다. 원신호판은 등록하지 않았다. "
         "⚠ 그래도 집중은 남는다 — 상위 13종이 보유칸의 32.0%다(CBOE 38% · ERIE 33% · TECH 27% …). "
         "유형이 다르다: 외국 발행인·이중클래스가 아니라 유통물량이 적고 주가가 높은 미국 회사다. "
         "스프레드가 실제로 넓은 종목이 뽑히는 것이므로 인공물이라 단정하지 않지만, 그 종목들을 "
         "실제로 사려면 비용이 크다는 뜻이기도 하다 — net 열을 함께 볼 것. "
         "🚨 PIT 레그가 없다. data/_pit_px_cache.json 이 편출 종목의 종가만 갖고 있어 "
         "고가·저가가 필요한 이 규칙은 시점정확으로 다시 못 돌린다. 사전등록 4종이 죽은 사유가 "
         "정확히 그것이었으므로, 게시 기준을 넘어도 이번에는 게시하지 않는다(기록용). "
         "🚨 그리고 넘지 못했다 — 사전등록 게이트 미달로 기각한다. 한 번 돌린 결과: "
         "단독 t 4.86(임계 3.33 통과) · 비용 후 t 4.73(편도 10bp, 매매대금 연 5.6배라 "
         "비용이 거의 안 문다) · 이웃 하나 통제 증분 t 2.80 — 여기까지는 다 넘는다. "
         "그런데 이웃 5개 동시 통제 증분 t 는 1.11 로 게이트(2.0)에 못 미친다. "
         "가장 닮은 이웃이 에코 모멘텀(ρ 0.468)인데, 하나만 떼면 남아 보이고 다섯을 떼면 "
         "사라진다 — 붐비는 축이라는 뜻이다. 규칙은 결과를 보고 고치지 않았다. "
         "살리려면 새 사전등록이 필요하다.")

    # ── 사전등록 8종 (build/PREREG-2026-08-04-BATCH8.md) ──────────────────
    # 규약은 돌리기 전에 확정해 커밋했다. 앞의 넷은 2026-08-04 에 배선한 고가·저가를 처음
    # 쓰는 규칙이고, 뒤의 넷은 종가만 써서 PIT 레그를 붙일 수 있다.
    xsec("x-clv", "종가 위치 상위 %d (마감 압력 · 1개월 수익 중립)" % TOPN,
         "일별 종가위치 CLV=(2C−H−L)/(H−L) 의 최근 21거래일 평균을 낸다(유효 11일 미만 제외, "
         "월말 종가 $5 이상). 그 달 후보 전체에서 원신호를 최근 21일 로그수익에 횡단면 회귀하고 "
         "그 잔차가 가장 낮은 %d종을 동일가중으로 산다. 월말 리밸런스." % TOPN,
         None,
         "Lou·Polk·Skouras(RFS 2019) 'tug of war'. 수익의 야간 성분은 이어지고 일중 성분은 "
         "되돌린다. 수익을 같게 통제하면 잔차 CLV 는 '그 수익을 일중에 벌었나'의 대용이므로 "
         "일중 성분이 작은 쪽을 산다. 🚨 중립화는 선택이 아니다 — 원신호와 21일 로그수익의 "
         "횡단면 스피어만이 중앙 +0.550 이라, 중립화 없이 쓰면 1개월 반전을 뒤집어 다시 파는 "
         "것이 된다. 업종·변동성 중립화는 하지 않는다(잔차 vs log 252일 변동성 중앙 −0.121 — "
         "필요 없다는 것이 실측이다). ⚠ PIT 레그가 없다 — 편출 종목 가격 캐시에 고가·저가가 "
         "없어 시점정확으로 못 돌린다. "
         "🚨 위 자동 판정('통과 후보')을 그대로 읽지 말 것 — 자동 판정기는 단독 t 와 Δ샤프만 "
         "본다. 사전등록 게이트로는 기각이다. 한 번 돌린 결과: 단독 t 4.05(임계 3.37 통과) · "
         "incr5 2.27(게이트 2.0 통과) · 자기가 사는 것 대비 t 2.33(양수 — 이 표에서 드물다). "
         "그런데 비용 후 t 가 3.32 로 임계 3.37 에 0.05 못 미친다. 연 매매대금이 NAV 의 "
         "23.0배라 편도 10bp 가 그만큼을 먹는다. 셋 중 둘을 넘고 셋째를 0.05 로 놓쳤다 — "
         "게이트는 미리 못박은 것이고 반올림해서 통과시키지 않는다. 이 규칙은 오늘 비용 레그가 "
         "없었다면 게시 후보로 올라갔을 것이다(그것이 비용 레그를 넣은 이유다). "
         "살리려면 새 사전등록이 필요하다 — 회전을 줄인 판은 다른 전략이다.")
    xsec("x-ongapd", "야간 갭 비중 확대 상위 %d" % TOPN,
         "전일종가를 포함한 실질범위 TR 중 장외에서 벌어진 몫(gap)의 비중을 63일창과 252일창에서 "
         "각각 재고 그 차이가 가장 큰 %d종을 동일가중으로 산다. 월말 리밸런스." % TOPN,
         None,
         "정보가 장중에 오느냐 장외에 오느냐가 옮겨 가는 것을 잡는다. 시가가 없어도 고가·저가와 "
         "전일종가만으로 장외 이동이 정확히 나온다. ⚠ 중립화 없음 — 실측이 정했다(점수 vs "
         "log 변동성 ρ 중앙 +0.002 · vs 갭비중 수준 −0.031 · vs 12−1 모멘텀 −0.020). "
         "x-hlspread 가 중립화를 강제한 근거가 ρ 0.816 이었으므로 여기서 붙이면 근거 없는 "
         "파라미터가 하나 늘 뿐이다. 수준판은 등록하지 않았다. ⚠ PIT 레그 없음(고가 부재). "
         "⚠ 실적 발표 달력의 인공물일 수 있다 — 63일창에는 실적이 대개 한 번, 252일창에는 "
         "네 번 들어간다.")
    xsec("x-lshock", "고저가 스프레드 급확대 상위 %d (유동성 충격)" % TOPN,
         "Corwin-Schultz 고저가 스프레드의 최근 63일 평균을 그 앞 231일 평균으로 나눈 로그비가 "
         "가장 큰 %d종을 동일가중으로 산다. 월말 리밸런스." % TOPN,
         None,
         "Amihud(2002)의 '비유동성 충격은 동시대 가격을 눌러 이후 수익을 높인다'를 횡단면으로 "
         "옮긴 것이다. 수준이 아니라 자기 평소 대비 변화를 보므로 x-hlspread(수준)와 축이 "
         "다르다(점수 vs 스프레드 수준 ρ 중앙 −0.029). ⚠ 중립화 없음(vs Δlog변동성 +0.119). "
         "⚠ 추정량이 잡음 바닥에 걸려 있다 — CS 일별 추정치의 45.1%가 0 으로 잘리므로 창 평균은 "
         "'스프레드 크기'와 '추정치가 양수였던 빈도'가 섞인 값이다. ⚠ PIT 레그 없음(고가 부재).")
    timing("t-clvgate", "시장 마감압력 게이트 (지수 CLV)",
           "매일 전 종목의 종가위치를 동일가중 평균해 시장 마감압력을 만들고, 그 20일 평균이 "
           "0보다 크면 편입, 아니면 현금(무위험).",
           None,
           "타이밍 20종이 전부 지수 '가격'을 본다. 이쪽은 같은 가격에서 일중 어디에 마감했나만 "
           "뽑아내므로 수준·추세와 축이 다르다. 문턱 0 은 '종가가 그날 범위 한가운데 = 순 마감압력 "
           "없음'이라는 정의상의 값이고 조정하지 않았다. ⚠ PIT 레그 없음(고가 부재).")
    xsec("x-delay", "시장정보 반영 지연도 상위 %d (Hou-Moskowitz)" % TOPN,
         "최근 252거래일 일간수익을 시장수익에 회귀하되, 시장의 1~4일 전 값을 넣은 모형과 "
         "당일만 넣은 모형의 설명력 차이를 지연도로 쓴다. 그 달 후보 전체에서 지연도를 "
         "log 설명력에 횡단면 회귀한 잔차 상위 %d종을 동일가중으로 산다. 월말 리밸런스." % TOPN,
         None,
         "Hou·Moskowitz(RFS 2005). 시장 정보가 늦게 반영되는 종목이 그 대가로 프리미엄을 "
         "받는다는 것이다. 시장은 랩 동일가중 유니버스를 쓴다(판정 대조군 SPX 가 아니다 — "
         "지연을 재는 대상은 이 규칙이 사는 모집단이다). 🚨 D1 은 비율통계라 분모가 작으면 "
         "식별되지 않는다 — 비제한 R² 가 0.01 초과이고 그 달 후보의 20 백분위 이상인 종목만 "
         "후보로 두고, 그 위에 log R² 중립화를 건다. 정지가격 게이트(일간수익 0인 날 10% 초과 "
         "제외)도 함께 건다. 산업·사이즈 중립화는 하지 않는다(하면 규칙이 둘이 된다).")
    xsec("x-peerlag", "상관이웃 선도-지연 상위 %d (자기수익 중립)" % TOPN,
         "종목마다 최근 252일 일간수익 상관이 가장 높은 이웃 20종을 찾고, 그 이웃들의 최근 "
         "21일 수익 평균을 자기 자신의 21일 수익에 횡단면 회귀한 잔차 상위 %d종을 동일가중으로 "
         "산다. 월말 리밸런스." % TOPN,
         None,
         "정보확산 지연(lead-lag). 이웃이 먼저 움직였는데 나는 아직이면 따라잡힌다는 가설이다. "
         "이 랩의 다른 규칙은 전부 종목 하나를 보는데 이것만 종목쌍을 본다. "
         "🚨 계산 비용을 미리 적어 둔다 — 이 랩은 무의존(stdlib only)이라 상관행렬을 순수 "
         "파이썬으로 만든다. 월말당 513종·131,328쌍, 쌍당 20.1µs → 월말당 2.6초 → 199개 월말에 "
         "8.8분이다. 같은 회사의 다른 클래스는 이웃에서 뺀다(안 빼면 자기 자신을 이웃으로 "
         "삼는다). ⚠ '이웃 − 자기' 단순 차분판과 '이웃 수익만' 판은 등록하지 않았다.")
    xsec("x-updown", "상하방 베타 비대칭 상위 %d" % TOPN,
         "최근 252거래일을 시장이 평균보다 내린 날과 오른 날로 갈라 각각 베타를 재고, "
         "그 차이를 두 베타 크기의 합으로 나눈 값이 가장 큰 %d종을 동일가중으로 산다. "
         "월말 리밸런스." % TOPN,
         None,
         "Ang·Chen·Xing(RFS 2006) 하방위험 프리미엄 — 시장이 내릴 때 더 크게 내리는 종목은 "
         "위험보상을 요구받는다. 원차분(β⁻ − β⁺) 대신 비율형을 쓴 이유는 규모 무관하게 "
         "만들기 위해서다(분모 0.2 미만은 제외 — 시장과 사실상 안 움직이는 종목에서 비율이 "
         "폭주한다). 원차분판·β 중립판은 등록하지 않았다. ⚠ 표본에 하락 국면이 2020·2022 "
         "둘뿐이다. 하방위험 프리미엄은 정의상 시장이 내릴 때 실현되므로, 여기 열위는 "
         "반증이 아니라 검정 불능에 가깝다(x-maxlow 카드와 같은 사유).")
    xsec("x-volvol", "변동성의 변동성 최하위 %d (변동성 수준 중립)" % TOPN,
         "최근 252거래일을 21일 블록 12개로 잘라 블록별 실현변동성을 내고, 그 변동계수를 "
         "변동성 수준에 횡단면 회귀한 잔차가 가장 낮은 %d종을 동일가중으로 산다. "
         "월말 리밸런스." % TOPN,
         None,
         "Baltussen·van Bekkum·van der Grient(JFQA 2018). 위험의 크기가 아니라 위험이 "
         "얼마나 불확실한가를 재고, 그런 종목은 저평가가 아니라 고평가된다는 것이다. "
         "방향은 결과 보기 전에 그 논문을 따라 고정했다. 🚨 변동성 수준 중립화가 핵심이다 — "
         "이 랩에는 이미 저변동성 계열이 넷 있어(x-lowvol·x-ivol·x-lowbeta …) 중립화 없이 "
         "쓰면 그 축을 다시 파는 것이 된다. 중첩 롤링창판·고 VoV 롱판은 등록하지 않았다.")

    # ── 목록에서 뺀 규칙(2026-07-31, 사용자 결정) ───────────────────────────
    # 여기서 걸러진 규칙은 STRATS 에 들어가지 않는다 — 산출물·다중검정 족 수·PIT·화면 어디에도
    # 안 나온다. 정의(위 등록 코드)는 남긴다. 무엇을 시도했는지가 기록이고, 되살리려면 sid 를
    # 이 집합에서 빼면 된다.
    #
    # 사유는 둘이고 성격이 다르다 — 섞어 읽지 말 것.
    #   ① 중복 — 족 수를 **바로잡는다.** 애초에 독립 검정이 아니었으므로 빼는 것이 정확하다.
    #      · x-riskbudget(역변동성) = x-lowvol(저변동성)  초과수익 상관 **1.000**.
    #        동일가중 상위10을 뽑는 순간 역변동성 가중이 사라져 같은 바스켓이 된다.
    #        PIT 레그에서도 수치가 완전히 같았다(소급 +9.51 → PIT +9.57).
    #      · x-mom-trend(대형주 모멘텀+200일선) ≈ x-mom12  상관 **0.997** · 증분 알파 t −0.38.
    #   ② 열위 — 대조군보다 나빴던 규칙(Δ샤프 전부 음수). 이쪽은 성과를 보고 빼는 것이므로
    #      **임계가 자기에게 유리해지는 방향**이다. 그래서 크기를 재서 남긴다:
    #        65 → 54종 · t_crit 3.36 → 3.31. 이 이동으로 판정이 바뀐 규칙은 0종이다.
    #      🚨 어디까지가 안전한가도 재 뒀다 — **32종까지 줄이면 t_crit 이 3.16 이 되어
    #        잉여현금흐름(PIT t 3.16)이 '통과'로 바뀐다.** 그 선을 넘으면 목록을 줄여서
    #        통과를 만드는 것이 된다. 지금 54종은 거기 한참 못 미친다.
    #      ⚠ x-gpa·x-ocfp 는 어제 JKP 빈 칸(Quality·Profitability 현금축)을 메우려고 넣은 것인데
    #        열위로 빠지면서 그 칸이 다시 빈다. 축이 비었다는 사실과 그 축이 이 표본에서
    #        졌다는 사실은 둘 다 참이다.
    RETIRED = {
        "x-riskbudget": "저변동성과 초과수익 상관 1.000 — 같은 규칙이다(①중복)",
        "x-mom-trend": "12-1 모멘텀과 상관 0.997 · 증분 알파 t −0.38(①중복)",
        "t-rsi": "열위 — Δ샤프 −0.046",
        "x-recency": "열위 — Δ샤프 −0.053",
        "t-tsmomc": "열위 — Δ샤프 −0.055",
        "x-gpa": "열위 — Δ샤프 −0.089",
        "x-ocfp": "열위 — Δ샤프 −0.090",
        "x-minvar": "열위 — Δ샤프 −0.095(저변동성과 상관 0.934 이기도 하다)",
        "x-roe": "열위 — Δ샤프 −0.140",
        "x-npm": "열위 — Δ샤프 −0.141",
        "t-sentgate": "열위 — Δ샤프 −0.169",
        # ③ 운영 비용 — 이 사유는 위 둘과 성격이 다르다(2026-08-04 사용자 결정).
        #   성적을 보고 뺀 것이 아니라 **계산 시간**을 보고 뺐다. x-peerlag 은 이 랩에서
        #   유일하게 종목쌍(상관행렬)을 보는 규칙이고, 무의존 규약(refresh-tech.yml 에
        #   pip install 이 없다) 때문에 131,328쌍 × 199개 월말을 순수 파이썬으로 돈다 —
        #   실측으로 전체 실행이 1분 40초 → 7분 16초가 됐다.
        #   ⚠ 그래도 임계는 내려간다(66 → 65종). 성과 기반이 아니어도 남은 규칙에 유리한
        #     방향인 것은 같으므로, 그 크기를 재서 아래 출력에 남긴다.
        #   ⚠ 정의(등록 코드·사전 패스)는 지우지 않는다. 되살리려면 이 줄만 빼면 된다.
        "x-peerlag": "운영 비용 — 상관행렬로 전체 실행이 1m40s → 7m16s (성과 사유 아님. "
                     "단독 t 1.54 · incr5 0.24)",
        "x-delay": "운영 비용 — 종목당 5회귀 × 199개월로 약 2분 (성과 사유 아님. "
                   "단독 t 1.36 · incr5 0.39)",
    }
    # ⚠ 뺀 규칙의 기록은 들고 나간다. 셋(x-mom-trend·x-minvar·x-riskbudget)이 아카이브 항목을
    #   '이 규칙으로 재현했다'고 가리키는 arch 태그를 달고 있어, 그냥 지우면 그 아카이브 항목이
    #   화면에서 조용히 사라진다(validate 가 잡아 줬다). 재현은 실제로 했으므로 사실이 아니다.
    RETIRED_RECS[:] = [{"sid": s["sid"], "name": s["name"], "arch": s.get("arch"),
                        "kind": s["kind"], "why": RETIRED[s["sid"]]}
                       for s in STRATS if s["sid"] in RETIRED]
    _before = len(STRATS)
    STRATS[:] = [s for s in STRATS if s["sid"] not in RETIRED]
    if _before != len(STRATS):
        print("  목록 제외 %d종(중복 2 · 열위 9 · 운영비용 2) — %d → %d종  ⚠ 임계 %.2f → %.2f"
              % (_before - len(STRATS), _before, len(STRATS),
                 z_crit(_before), z_crit(len(STRATS))))


# ── 증분 알파 계산기 (모듈 레벨 — 랩 셋이 같은 것을 쓴다) ──────────────────
# 🚨 2026-08-05: run() 안의 중첩 함수였다. 그래서 ml_backtest·asset_backtest 는 이 검정을
#   아예 못 썼고, ML 5종이 서로 초과수익 상관 0.86~0.93 인 채로 "통과 후보" 배지를 달고
#   있었다 — 이 랩이 DATA-FACTS 6·8 에서 중복 판정의 잣대라고 못박은 검정을 한 번도 안 받았다.
#   다시 구현하지 않고 여기서 꺼내 쓴다. 같은 일을 두 벌 두면 한쪽만 고쳐진다는 것이
#   오늘 하루의 교훈이다(x-52wh 가 tech 에서만 고쳐지고 pit 에 남아 있었다).
def nav_rets(r):
    v = r.get("nav") or []
    return [v[i] / v[i - 1] - 1 for i in range(1, len(v))] if len(v) > 2 else []

def corr_of(a, b):
    if len(a) != len(b) or not a:
        return None
    m1, m2 = sum(a) / len(a), sum(b) / len(b)
    s1 = math.sqrt(sum((x - m1) ** 2 for x in a))
    s2 = math.sqrt(sum((y - m2) ** 2 for y in b))
    if not s1 or not s2:
        return None
    return sum((x - m1) * (y - m2) for x, y in zip(a, b)) / (s1 * s2)

def _align_grid(maps):
    """날짜 격자가 섞여 있으면 **거친 쪽(월말)으로 전원을 내린다.**

    🚨 2026-08-05 — 자산 랩의 세 규칙(guru-clone·regime-switch·hrp-sleeve)은 날짜를
      '2013-08'(월 라벨)로 내고 나머지는 '2013-08-20'(일 라벨)로 낸다. 교집합이 0 이라
      이웃이 하나도 안 잡혔고, 이웃 5개를 못 채우니 incr5 가 None 이 됐다. 그리고 중복
      게이트가 `i5 is None` 을 통과로 취급했다 — **못 잰 것이 넘은 것과 같아졌다.**

    ⚠ 잣대를 두 벌로 만들지 않는다. 한쪽이라도 월이면 **전원** 월말로 내린다. 쌍 비교
      (paired_excess)와 다중 회귀(incr_multi)가 같은 함수를 쓰게 한 이유가 이것이다 —
      한쪽만 고치면 쌍에서는 이웃으로 뽑히고 다중에서는 교집합이 무너져 incr5 가 오히려
      더 많이 None 이 된다(실제로 3종 → 8종으로 늘렸다가 되돌렸다).
    ⚠ 전원 일간이면 아무것도 하지 않는다 — 종전과 완전히 같은 값이 나온다.
    """
    if not maps or not all(maps):
        return maps
    if all(all(len(k) == 7 for k in m) for m in maps):
        return maps                                   # 전원 월간
    if all(all(len(k) == 10 for k in m) for m in maps):
        return maps                                   # 전원 일간 — 손대지 않는다
    out = []
    for m in maps:
        if all(len(k) == 7 for k in m):
            out.append(m)
        else:
            g = {}
            for k in sorted(m):                       # 정렬이라 그 달의 마지막 관측이 남는다
                g[k[:7]] = m[k]
            out.append(g)
    return out


def paired_excess(r1, r2):
    """두 규칙의 **공통 날짜**에서 초과수익(전략−대조군) 두 계열을 만든다.

    🚨 날짜로 맞춰야 한다. 보유시작 재기준·커버리지 게이트 때문에 규칙마다 구간이 다르고
      (발생액 2018-12 · 장기반전 2021-08 · 총이익 2021-09), 길이만 보고 자르면 서로 다른
      시점을 겹쳐 놓게 된다. 종전 타이밍 중복표는 전부 같은 구간이라 이 문제가 없었다.
    """
    def ex(r):
        d, nv, bv = r.get("dates") or [], r.get("nav") or [], r.get("bnav") or []
        if not (len(d) == len(nv) == len(bv)):
            return {}
        return {d[i]: (nv[i], bv[i]) for i in range(len(d))}
    e1, e2 = _align_grid([ex(r1), ex(r2)])       # 격자 정규화는 한 곳에서만 한다
    ds = sorted(set(e1) & set(e2))
    xs, ys, prev = [], [], None
    for d in ds:
        if prev is not None:
            a1, b1 = e1[d]; a0, b0 = e1[prev]
            a2, b2 = e2[d]; c0, d0 = e2[prev]
            if a0 and b0 and c0 and d0:
                xs.append((a1 / a0 - 1) - (b1 / b0 - 1))
                ys.append((a2 / c0 - 1) - (b2 / d0 - 1))
        prev = d
    return xs, ys

def incr_multi(r, others):
    """후보를 이웃 **여럿에 동시에** 회귀 — 절편의 t 를 돌려준다.

    _incr(이웃 하나)로는 붐비는 축을 못 걷는다. 이웃이 여럿이면 하나만 빼도 남는 것이
    있어 보이기 때문이다. 실측은 위 호출부 주석에 있다.
    🚨 날짜로 맞춘다. 규칙마다 구간이 다르므로(재기준·커버리지 게이트) **전원의 공통
      날짜**에서만 회귀한다 — 길이로 자르면 서로 다른 시점을 겹쳐 놓게 된다.
    """
    def ser(x):
        d, nv, bv = x.get("dates") or [], x.get("nav") or [], x.get("bnav") or []
        if not (len(d) == len(nv) == len(bv)):
            return {}
        return {d[i]: (nv[i], bv[i]) for i in range(len(d))}
    maps = [ser(r)] + [ser(o) for o in others]
    if not all(maps):
        return None
    maps = _align_grid(maps)                     # 쌍 비교와 **같은** 규약을 쓴다
    ds = sorted(set.intersection(*[set(m) for m in maps]))
    cols, prev = [[] for _ in maps], None
    for d in ds:
        if prev is not None and all((m[prev][0] and m[prev][1]) for m in maps):
            for k, m in enumerate(maps):
                a1, b1 = m[d]; a0, b0 = m[prev]
                cols[k].append((a1 / a0 - 1) - (b1 / b0 - 1))
        prev = d
    y, X = cols[0], cols[1:]
    n, k = len(y), len(X) + 1
    if n < 60 + k:
        return None
    M = [[1.0] + [X[j][i] for j in range(len(X))] for i in range(n)]
    XtX = [[sum(M[i][a] * M[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(M[i][a] * y[i] for i in range(n)) for a in range(k)]

    def solve(A, rhs):                     # 가우스-조던(작은 k 라 충분하다)
        G = [A[i][:] + [rhs[i]] for i in range(k)]
        for c in range(k):
            p = max(range(c, k), key=lambda z: abs(G[z][c]))
            if abs(G[p][c]) < 1e-14:
                return None
            G[c], G[p] = G[p], G[c]
            pv = G[c][c]
            G[c] = [v / pv for v in G[c]]
            for rr in range(k):
                if rr != c and G[rr][c]:
                    f = G[rr][c]
                    G[rr] = [G[rr][j] - f * G[c][j] for j in range(k + 1)]
        return [G[i][k] for i in range(k)]
    beta = solve(XtX, Xty)
    if beta is None:
        return None
    res = [y[i] - sum(beta[a] * M[i][a] for a in range(k)) for i in range(n)]
    s2 = sum(x * x for x in res) / (n - k)
    e0 = solve(XtX, [1.0] + [0.0] * (k - 1))   # (X'X)^-1 의 첫 열
    if e0 is None or s2 <= 0 or e0[0] <= 0:
        return None
    se = math.sqrt(s2 * e0[0])
    return {"alpha": round(beta[0] * (252 / 5) * 100, 2),
            "t": round(beta[0] / se, 2) if se else None, "n": n}

def incr1(a, b):
    """a(후보 초과수익)를 b(기존 규칙 초과수익)에 회귀 — 절편이 증분 알파다.

    붐비는 축에 규칙을 하나 더 얹을 때 '단독 t'는 답이 못 된다. 이미 들고 있는 규칙이
    설명하고 남는 것이 있느냐가 질문이고, 그 답이 절편이다. 실측 사례: 에코 모멘텀은
    단독 t 3.80 인데 12-1 대비 증분 알파 t 는 1.01 이었다 — 별개 축이 아니었다.
    """
    n = len(a)
    if n < 60 or len(b) != n:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sbb = sum((x - mb) ** 2 for x in b)
    if sbb <= 0:
        return None
    beta = sum((x - mb) * (y - ma) for x, y in zip(b, a)) / sbb
    alpha = ma - beta * mb
    res = [y - (alpha + beta * x) for x, y in zip(b, a)]
    s2 = sum(r * r for r in res) / max(1, n - 2)
    se = math.sqrt(s2 * (1.0 / n + mb * mb / sbb)) if s2 > 0 else 0.0
    # nav 는 5거래일 간격 표본이므로 연율화 배수는 252/5
    return {"alpha": round(alpha * (252 / 5) * 100, 2),
            "t": round(alpha / se, 2) if se else None,
            "beta": round(beta, 3), "n": n}


# ── 실행 ────────────────────────────────────────────────────────────────
def run():
    dates, px, vlm, hid, lod, meta, rf = load()
    FU = load_fund()          # 티커 → eq·sh·fcf 분기 시계열(시점 정합은 asof_fund가 맡는다)
    n = len(dates)
    tickers = sorted(px)
    R = daily_rets(px)
    me_list = month_ends(dates)
    me = set(me_list)
    # 잔차 모멘텀용 팩터 대리변수 — 못 읽으면 빈 dict 이고 그 전략만 후보 0 으로 빠진다.
    FACP = load_factor_proxies(dates)

    # 동일가중 유니버스 지수(일간 리밸런스) — **타이밍 전략이 실제로 매매하는 대상**이자
    #   ixvol·ixgap·disp 등 지표의 입력이다. 대조군으로는 더 이상 쓰지 않는다(아래 bxr).
    #   ⚠ 사용자 결정(2026-07-28): 판정 대조군을 S&P 500(PR)로 바꾼다. 매매 대상은 그대로 둔다 —
    #     대상까지 바꾸면 33종이 전부 다른 전략이 되어 과거 수치와 비교가 끊긴다.
    ix = [100.0]
    ixr = [None]
    for i in range(1, n):
        rs = [R[t][i] for t in tickers if R[t][i] is not None]
        r = sum(rs) / len(rs) if rs else 0.0
        ixr.append(r)
        ix.append(ix[-1] * (1 + r))

    ixvol = [vol(ixr, i, 20) for i in range(n)]
    # 지수의 200일선 이격 — t-gapcap 이 매 시점 직전 252일치를 다시 만드느라
    # sma(ix, j, 200) 를 i마다 252번(각 200회 덧셈) 돌렸다. 규칙과 무관하게 ix 에만
    # 의존하므로 한 번만 만들어 둔다: 252×200×n → n×200.
    ixgap = [((ix[i] / _m - 1) if (_m := sma(ix, i, 200)) else None) for i in range(n)]

    # 횡단면 분산도 — 그날 종목 수익률의 표준편차(국면 대리변수)
    disp = [None] * n
    for i in range(1, n):
        rs = [R[t][i] for t in tickers if R[t][i] is not None]
        if len(rs) > 50:
            m = sum(rs) / len(rs)
            disp[i] = math.sqrt(sum((x - m) ** 2 for x in rs) / (len(rs) - 1))
    # 시장 마감압력 — 그날 전 종목의 종가위치(CLV)를 동일가중 평균한 것. 사전등록 t-clvgate.
    # 같은 지수 '가격'에서 **일중 어디에 마감했나**만 뽑아낸다 — 수준·추세와 축이 다르다.
    # 2026-08-04 에 고가·저가를 배선하고서야 만들 수 있게 된 계열이다.
    mclv = [None] * n
    _clvs = {t: clv_daily(hid[t], lod[t], px[t], t) for t in tickers if hid.get(t) and lod.get(t)}
    for i in range(n):
        vs = [c[i] for c in _clvs.values() if c[i] is not None]
        if len(vs) > 50:
            mclv[i] = sum(vs) / len(vs)

    # 시장 폭 — 그날 '자기 200일선 위'인 종목의 비율. 지수 가격에는 안 보이는 내부 상태다.
    # 종목마다 200일 이동평균을 매일 다시 더하면 O(종목×일×200)이라 느리다 → 누적합으로 O(1).
    brd = [None] * n
    above = [0] * n
    cnt = [0] * n
    for t in tickers:
        a = px[t]
        # 결측일(거래정지·상장 전)이 섞여 있다. 이동평균은 직전 유효가를 끌어와 계산하되,
        # **그날 값이 없는 종목은 그날의 분모에서 뺀다** — 없는 종목을 '200일선 아래'로
        # 세면 폭이 실제보다 나빠 보인다.
        f = [None] * n
        last = None
        for i in range(n):
            if a[i] is not None:
                last = a[i]
            f[i] = last
        st_ = next((i for i in range(n) if f[i] is not None), None)
        if st_ is None:
            continue
        c = [0.0] * (n + 1)          # c[k] = f[0..k-1] 합(결측 채운 값)
        for i in range(n):
            c[i + 1] = c[i] + (f[i] if f[i] is not None else 0.0)
        for i in range(max(200, st_ + 200), n):
            if a[i] is None:
                continue
            m200 = (c[i] - c[i - 200]) / 200.0     # 당일 제외 200일 평균(선견 없음)
            cnt[i] += 1
            if a[i] > m200:
                above[i] += 1
    for i in range(n):
        if cnt[i] > 50:
            brd[i] = above[i] / cnt[i]

    # 심리 지수 — 이 사이트가 따로 굽는 유일한 '가격 밖' 입력(VIX·기간구조·MOVE 합성).
    # 날짜로 맞춰 붙이고, 없는 날은 직전 값을 끌고 간다(발표 지연을 앞당겨 쓰지 않는다).
    sent = [None] * n
    try:
        _sh = json.load(io.open(os.path.join(DATA, "sentiment.json"), encoding="utf-8")).get("history") or []
        _sm = {r["dt"]: r["score"] for r in _sh if r.get("score") is not None}
        _last = None
        for i, d_ in enumerate(dates):
            if d_ in _sm:
                _last = _sm[d_]
            sent[i] = _last
    except Exception:
        pass

    rfd = (sum(rf.values()) / len(rf) / 21) if rf else 0.0
    # 현금 수익은 **그 시점의** 금리로 준다. 상수 하나로 뭉개면 구간이 길수록 거짓말이 커진다 —
    # 10년 구간의 실제 3M 금리는 0.02~5.60% 라 연도별 오차가 -2.86%p(2023)~+2.37%p(2021)다.
    # 그러면 현금을 쥐는 방어형 규칙이 2016~2021 에 가공의 이자를 받아, 하필 '하락 방어를
    # 처음 검증한다'는 확장의 목적을 정면으로 오염시킨다. rf_monthly.json 은 1981-09 부터 있다.
    rfd_d = [((rf.get(d[:7]) / 21) if rf.get(d[:7]) is not None else rfd) for d in dates]
    _rf_miss = sum(1 for d in dates if rf.get(d[:7]) is None)
    if _rf_miss:
        print("  [무위험] %d/%d일이 rf_monthly 에 없어 구간평균으로 대체" % (_rf_miss, len(dates)))

    build_strats()
    out = []
    bench_r = ixr[MIN_HIST:]
    IDXR = load_index_tr(dates)      # 같은 구간 지수(PR) — 카드에 나란히 그린다
    # 판정 대조군 = S&P 500(PR). assets.json 에서 못 읽으면 판정 근거가 통째로 사라지므로 멈춘다
    #   — 조용히 동일가중으로 되돌아가면 화면은 'SPX 기준'이라 적힌 채 다른 숫자를 싣게 된다.
    bxr = IDXR.get("S&P 500")
    if not bxr:
        raise SystemExit("대조군(S&P 500 PR)을 assets.json 에서 읽지 못했다 — 판정을 낼 수 없다.")

    # ⚠ 생존편향 눈금은 **랩의 동일가중 유니버스**(오늘 명단을 과거로 소급)를 실제 RSP 와
    #   견주는 것이다. 판정 대조군이 SPX 로 바뀐 뒤에도 이 눈금은 동일가중이어야 한다 —
    #   bnav_ref 를 그대로 쓰면 'SPX vs RSP' 를 재고 그걸 생존편향이라 부르게 된다.
    ewnav_ref = [100.0]
    for _i in range(MIN_HIST + 1, n):
        ewnav_ref.append(ewnav_ref[-1] * (1 + ixr[_i]))
    for S in STRATS:
        w = [0.0] * n
        if S["kind"] == "timing":
            state = 0.0
            peak = 0.0          # 샹들리에: 진입 후 고점
            kama_prev = None    # 적응형 이동평균: 직전 값(재귀식이라 이어져야 한다)
            macd_sig = None     # MACD 신호선(9기간 EMA): 같은 사유로 상태를 이어 간다
            ddpk = None         # t-ddgate: MIN_HIST 이후 지수 고점(러닝 맥스 — 아래 설명)
            for i in range(n):
                if i < MIN_HIST:
                    continue
                sid = S["sid"]
                if sid == "t-rsi":
                    v = rsi(ix, i)
                    if v is not None:
                        if v < 30:
                            state = 1.0
                        elif v > 60:
                            state = 0.0
                    w[i] = state
                elif sid == "t-donch":
                    hi = max(ix[i - 20:i]) if i >= 20 else None
                    lo = min(ix[i - 20:i]) if i >= 20 else None
                    if hi and ix[i] > hi:
                        state = 1.0
                    elif lo and ix[i] < lo:
                        state = 0.0
                    w[i] = state
                elif sid == "t-macd":
                    def ema(xs, i, n_, cache={}):
                        k = 2 / (n_ + 1)
                        e = xs[max(0, i - n_ * 3)]
                        for j in range(max(0, i - n_ * 3) + 1, i + 1):
                            e = xs[j] * k + e * (1 - k)
                        return e
                    # 🚨 2026-08-04 버그 수정. 종전 `sig = m*0.2 + prev*0.8` 의 prev 는
                    #   전날의 **신호선**이 아니라 전날의 **MACD** 였다. 그러면
                    #     m > sig ⟺ 0.8·m > 0.8·prev ⟺ m > prev
                    #   가 되어, 9기간 EMA 교차가 아니라 **MACD 의 1일 차분 부호**를 본다.
                    #   화면 카드에 적힌 규칙("MACD(12,26)가 신호선(9) 위면 편입")과 실제로
                    #   돌린 규칙이 달랐고, 그 차이가 성적에 그대로 나왔다 — 종전 구현의
                    #   연회전율 54.9 는 규칙의 성질이 아니라 이 버그의 산물이다(정본은 21 안팎).
                    #   신호선은 누적이므로 매 시점 다시 만들 수 없다. 상태로 이어 간다.
                    m = ema(ix, i, 12) - ema(ix, i, 26)
                    if macd_sig is None:
                        macd_sig = m
                    else:
                        macd_sig = m * (2 / 10.0) + macd_sig * (1 - 2 / 10.0)   # 9기간 EMA
                    w[i] = 1.0 if m > macd_sig else 0.0
                elif sid == "t-disp":
                    hist = [x for x in disp[max(0, i - 252):i] if x]
                    cur = disp[i]
                    if cur and hist:
                        med = sorted(hist)[len(hist) // 2]
                        w[i] = 1.0 if cur < med else 0.0
                elif sid == "t-kelly":
                    win = [x for x in ixr[max(0, i - 120):i + 1] if x is not None]
                    if len(win) > 30:
                        m = sum(win) / len(win)
                        v2 = sum((x - m) ** 2 for x in win) / max(1, len(win) - 1)
                        w[i] = max(0.0, min(1.0, m / v2)) if v2 > 0 else 0.0
                elif sid == "t-mavote":
                    ms = [sma(ix, i, k) for k in (20, 50, 100, 200)]
                    ok = [m for m in ms if m is not None]
                    w[i] = (sum(1 for m in ok if ix[i] > m) / len(ok)) if ok else 0.0
                elif sid == "t-tsmomc":
                    m = (ret(ix, i, 252) or -1) - (ret(ix, i, 21) or 0)
                    w[i] = max(0.0, min(1.0, m / 0.20))     # 0~20% 구간을 0~1로
                elif sid == "t-mhvote":
                    rs = [ret(ix, i, k) for k in (21, 63, 126, 252)]
                    ok = [x for x in rs if x is not None]
                    w[i] = (sum(1 for x in ok if x > 0) / len(ok)) if ok else 0.0
                elif sid == "t-breadth":
                    b = brd[i]
                    w[i] = 1.0 if (b is not None and b > 0.5) else 0.0
                elif sid == "t-breadthc":
                    b = brd[i]
                    w[i] = (b if (b is not None and b >= 0.30) else 0.0)
                elif sid == "t-ddgate":
                    # i 는 단조 증가하고 고점은 줄지 않는다 → 매번 구간 전체를 훑을 이유가 없다.
                    # 이 랩에서 유일한 진짜 O(n²)였다(3년에선 안 보였고 10년에서 드러났다).
                    # 러닝 맥스는 max(ix[MIN_HIST:i+1]) 과 값이 정확히 같다.
                    ddpk = ix[i] if ddpk is None else max(ddpk, ix[i])
                    dd = ix[i] / ddpk - 1
                    if dd < -0.10:
                        state = 0.0
                    elif dd > -0.03:
                        state = 1.0
                    w[i] = state
                elif sid == "t-chand":
                    # 진입 뒤 고점을 따라다니는 손절선. 폭은 그때의 변동성(20일)으로 잡는다.
                    v = ixvol[i]
                    if state > 0:
                        peak = max(peak, ix[i])
                        if v and ix[i] < peak * (1 - 3 * v * math.sqrt(20)):
                            state = 0.0
                    else:
                        m50 = sma(ix, i, 50)
                        if m50 is not None and ix[i] > m50:
                            state = 1.0
                            peak = ix[i]
                    w[i] = state
                elif sid == "t-chan":
                    win = ix[max(0, i - 252):i + 1]
                    hi, lo = max(win), min(win)
                    w[i] = ((ix[i] - lo) / (hi - lo)) if hi > lo else 0.0
                elif sid == "t-kama":
                    if i >= 30:
                        chg = abs(ix[i] - ix[i - 10])
                        vol_ = sum(abs(ix[j] - ix[j - 1]) for j in range(i - 9, i + 1))
                        er = (chg / vol_) if vol_ > 0 else 0.0
                        sc = (er * (2 / 3 - 2 / 31) + 2 / 31) ** 2      # 효율성 → 평활상수
                        kama = kama_prev if kama_prev is not None else ix[i - 1]
                        kama = kama + sc * (ix[i] - kama)
                        kama_prev = kama
                        w[i] = 1.0 if ix[i] > kama else 0.0
                elif sid == "t-semivol":
                    win = [x for x in ixr[max(0, i - 60):i + 1] if x is not None and x < 0]
                    if len(win) > 5:
                        dv = math.sqrt(sum(x * x for x in win) / len(win))
                        w[i] = min(1.0, 0.09 / (dv * math.sqrt(252))) if dv > 0 else 0.0
                elif sid == "t-gapcap":
                    gap = ixgap[i]
                    if gap is not None:
                        hist = sorted(g for g in ixgap[max(MIN_HIST, i - 252):i] if g is not None)
                        cap = hist[int(len(hist) * 0.9)] if hist else None
                        w[i] = 0.0 if gap <= 0 else (0.5 if (cap is not None and gap > cap) else 1.0)
                elif sid == "t-sentgate":
                    hist = [x for x in sent[max(0, i - 252):i] if x is not None]
                    cur = sent[i]
                    if cur is not None and hist:
                        med = sorted(hist)[len(hist) // 2]
                        w[i] = 1.0 if cur < med else 0.0
                elif sid == "t-clvgate":
                    # 문턱 0 은 '종가가 그날 범위 한가운데 = 순 마감압력 없음'이라는 정의상의
                    # 값이다(사전등록에 그렇게 못박았다 — 조정하지 않는다).
                    win = [x for x in mclv[max(0, i - 19):i + 1] if x is not None]
                    if len(win) >= 10:
                        w[i] = 1.0 if (sum(win) / len(win)) > 0 else 0.0
                elif sid == "t-volreg":
                    hist = [v for v in ixvol[max(0, i - 252):i] if v]
                    cur = ixvol[i]
                    if cur and hist:
                        med = sorted(hist)[len(hist) // 2]
                        w[i] = 1.0 if cur < med else 0.0
                else:
                    w[i] = S["fn"](ix, i, R, ixvol[i])
            # 신호는 당일 종가로 계산 → 다음 날부터 적용(선견 방지)
            nav = [100.0]
            srets = []
            traded = []          # 그날 실제로 오간 금액(NAV 대비) — 비용은 이것에 붙는다
            for i in range(MIN_HIST + 1, n):
                e = w[i - 1]
                r = e * ixr[i] + (1 - e) * rfd_d[i]
                srets.append(r)
                # i 일에 적용되는 노출은 w[i-1], 그 전날 적용분은 w[i-2]. 차이만큼 i 일 시작에
                # 매매한다. 첫날은 무에서 e 만큼 사는 것이므로 e 그대로다.
                traded.append(abs(e - w[i - 2]) if i - 2 >= MIN_HIST else abs(e))
                nav.append(nav[-1] * (1 + r))
            turn = sum(abs(w[i] - w[i - 1]) for i in range(MIN_HIST + 1, n)) / max(1, (n - MIN_HIST) / 252)
            expo = sum(w[MIN_HIST:]) / max(1, n - MIN_HIST)
            # 지금 이 규칙이 어떤 상태인지 — 타이밍은 '얼마나 들고 있나'가 곧 구성이다
            start_i = MIN_HIST + 1
            hold_now = {"kind": "timing", "as_of": dates[-1],
                        "exposure_now": round(w[n - 1] * 100, 1),
                        "note": "노출 %d%%는 동일가중 유니버스 전체를 그 비율로 보유한다는 뜻이다. "
                                "나머지는 무위험(현금)." % round(w[n - 1] * 100)}
        else:
            # 횡단면 — 월말에만 순위를 다시 매기고 그 사이는 보유
            hold = []
            hw = None                      # 보유 비중(None 이면 동일가중 — 종전 경로)
            nav = [100.0]
            srets = []
            traded = []          # 그날 실제로 오간 금액(NAV 대비) — 비용은 이것에 붙는다
            turns = 0
            thin = 0             # 후보가 얇아 무보유로 둔 월말 수(커버리지 게이트)
            # 🚨 얇은 달(<30)만 세는 것으로는 **커버리지 램프**를 못 본다. 후보가 67 → 505 로
            #   불어나도 게이트는 한 번도 안 걸리는데, 앞구간의 '상위 10'은 유니버스의 13%
            #   안에서 고른 것이라 뒷구간의 '상위 10'과 같은 선택이 아니다 — 순위가 아니라
            #   커버리지가 고른 셈이다. 2026-08-04 에 실측으로 걸렸다(사전등록 후보 x-dato:
            #   전 구간 t 3.61 인데 2015 년 이후로 자르면 1.78 이었고, 차이를 만든 것이
            #   앞구간의 후보 풀 67~128종이었다). 월말마다 후보 수를 남겨 규칙마다 보고한다.
            pool_hist = []
            first_i = None       # 실제로 무언가를 보유하기 시작한 시점
            _tr = 0.0            # 그날 오간 금액(리밸런스 날에만 0 이 아니다)
            for i in range(MIN_HIST + 1, n):
                # `or not hold` 를 붙여 두었었다. 후보가 비면 다음 월말까지 기다리지 않고
                # 매일 전 종목을 다시 채점한다 — 규칙이 스스로 내건 '월말 리밸런스'를 어기는
                # 데다, 펀더멘털이 늦게 채워지는 전략(x-roe 등)은 초기 수년간 매일 재채점해
                # 10년 구간에서 899회(월말이면 106회) 돌았다. 규약대로 월말에만 다시 뽑는다.
                # 결과: 첫 월말 전까지는 후보가 없으므로 현금이다(선견 없이 정직한 상태다).
                if (i - 1) in me:
                    sc = []
                    comp_raw = {}          # E30 컴포지트 원지표 — 단면이 다 모여야 z 를 낸다
                    # 프로그인더팬은 **2단 선별**이라 종목 하나만 보는 채점으로는 못 만든다.
                    # 원논문은 모멘텀 5분위 × ID 5분위 이중정렬이므로, 여기서도 먼저 그 시점
                    # 모멘텀 상위 5분위 컷을 구한 뒤 아래 갈래에서 그 안에서만 ID 로 고른다.
                    #   ⚠ 컷을 고정 종목수가 아니라 **분위**로 잡는다. 유니버스가 커버 사정으로
                    #     흔들려도 '상위 20%'라는 규약이 그대로 유지된다.
                    #   ⚠ ret() 은 O(1) 이라 이 사전 패스는 월말당 518×2 회로 가볍다.
                    fip_ok = None
                    if S["sid"] == "x-fip":
                        _m = []
                        for t2 in tickers:
                            a2 = ret(px[t2], i - 1, 252)
                            if a2 is None:
                                continue
                            b2 = ret(px[t2], i - 1, 21)
                            _m.append((a2 - (b2 or 0), t2))
                        _m.sort(reverse=True)
                        _k = max(TOPN, int(len(_m) * 0.2))     # 상위 5분위(최소 TOPN)
                        # 승자만 남긴다 — 형성기 수익이 음수면 ID 의 sign 규약이 뒤집힌다.
                        fip_ok = {t2 for v2, t2 in _m[:_k] if v2 > 0}
                    # 고저가 스프레드도 2단이다 — 중립화가 **횡단면 회귀**라 종목 하나만
                    # 보는 채점으로는 못 만든다. 사전등록 문서의 규약 그대로:
                    #   log(252일 평균 CS 스프레드) 를 log(252일 실현변동성) 에 회귀 → 잔차.
                    # 근거: 원신호와 변동성의 횡단면 스피어만 상관이 중앙 0.816 이라,
                    #   중립화 없이 쓰면 저변동성 계열을 뒤집어 다시 파는 것이 된다.
                    hls = None
                    if S["sid"] == "x-hlspread":
                        rows = []
                        for t2 in tickers:
                            H2, L2 = hid.get(t2), lod.get(t2)
                            if not (H2 and L2):
                                continue
                            w2 = [x for x in cs_spread(H2, L2, t2)[max(0, i - 252):i] if x is not None]
                            if len(w2) < 126:              # 유효일 126일 미만은 후보 아님
                                continue
                            p2 = px[t2][i - 1]
                            if not p2 or p2 < 5.0:         # 페니주 차단
                                continue
                            s2 = sum(w2) / len(w2)
                            v2 = vol(R[t2], i - 1, 252)
                            if s2 <= 0 or not v2 or v2 <= 0:
                                continue
                            rows.append((t2, math.log(s2), math.log(v2)))
                        hls = {}
                        if len(rows) >= 2:
                            xs2 = [r2[2] for r2 in rows]; ys2 = [r2[1] for r2 in rows]
                            mx2 = sum(xs2) / len(xs2); my2 = sum(ys2) / len(ys2)
                            sxx = sum((x - mx2) ** 2 for x in xs2)
                            bb = (sum((x - mx2) * (y - my2) for x, y in zip(xs2, ys2)) / sxx) if sxx > 0 else 0.0
                            aa = my2 - bb * mx2
                            hls = {rows[k2][0]: ys2[k2] - (aa + bb * xs2[k2]) for k2 in range(len(rows))}
                    # ── 사전등록 8종 중 횡단면 중립화가 필요한 넷 ────────────────
                    # 중립화는 그 달 후보 전체를 봐야 하므로 종목 하나만 받는 채점으로는 못 만든다.
                    # x-hlspread·x-fip 과 같은 2단 구조다. 잔차 계산은 xsec_resid() 한 자리에 모았다.
                    xsr = None
                    _sid0 = S["sid"]
                    if _sid0 == "x-clv":
                        rows = []
                        for t2 in tickers:
                            H2, L2 = hid.get(t2), lod.get(t2)
                            if not (H2 and L2):
                                continue
                            p2 = px[t2][i - 1]
                            if not p2 or p2 < 5.0:
                                continue
                            w2 = [x for x in clv_daily(H2, L2, px[t2], t2)[max(0, i - 21):i] if x is not None]
                            if len(w2) < 11:
                                continue
                            p0 = px[t2][max(0, i - 22)]
                            if not p0 or p0 <= 0:
                                continue
                            rows.append((t2, sum(w2) / len(w2), math.log(p2 / p0)))
                        # 방향: 잔차 **하위** 10종 롱 → 부호를 뒤집어 넣는다(정렬은 내림차순).
                        xsr = {k2: -v2 for k2, v2 in xsec_resid(rows).items()}
                    elif _sid0 == "x-volvol":
                        rows = []
                        for t2 in tickers:
                            rs2 = R[t2]
                            if _stall(rs2, i - 1):
                                continue
                            sig = []
                            for b in range(12):        # 21일 비중첩 블록 12개
                                e = i - 1 - 21 * b
                                w2 = [x for x in rs2[max(0, e - 20):e + 1] if x is not None]
                                if len(w2) < 15:
                                    continue
                                m2 = sum(w2) / len(w2)
                                sig.append(math.sqrt(sum((x - m2) ** 2 for x in w2) / (len(w2) - 1)))
                            if len(sig) < 10:
                                continue
                            ms = sum(sig) / len(sig)
                            if ms <= 0:
                                continue
                            sd = math.sqrt(sum((x - ms) ** 2 for x in sig) / (len(sig) - 1))
                            v2 = vol(rs2, i - 1, 252)
                            if sd <= 0 or not v2 or v2 <= 0:
                                continue
                            rows.append((t2, math.log(sd / ms), math.log(v2)))
                        # 방향: 잔차 **하위** 10종 롱(고평가 가설) → 부호를 뒤집는다.
                        xsr = {k2: -v2 for k2, v2 in xsec_resid(rows).items()}
                    elif _sid0 == "x-delay":
                        rows = []
                        for t2 in tickers:
                            rs2 = R[t2]
                            if _stall(rs2, i - 1):
                                continue
                            y, m0, m1, m2_, m3, m4 = [], [], [], [], [], []
                            for k2 in range(max(4, i - 252), i):
                                a2 = rs2[k2]
                                if a2 is None or any(ixr[k2 - z] is None for z in range(5)):
                                    continue
                                y.append(a2); m0.append(ixr[k2]); m1.append(ixr[k2 - 1])
                                m2_.append(ixr[k2 - 2]); m3.append(ixr[k2 - 3]); m4.append(ixr[k2 - 4])
                            if len(y) < 126:
                                continue
                            _b, r2r = _ols(y, [m0])
                            _b, r2u = _ols(y, [m0, m1, m2_, m3, m4])
                            if r2r is None or r2u is None or r2u <= 0.01:
                                continue
                            rows.append((t2, 1.0 - r2r / r2u, math.log(r2u)))
                        # 🚨 D1 은 비율통계라 분모(비제한 R²)가 작으면 식별되지 않는다.
                        #   그 달 후보의 20 백분위 미만은 규약대로 통째로 뺀다.
                        if rows:
                            cut = sorted(r2[2] for r2 in rows)[int(len(rows) * 0.20)]
                            rows = [r2 for r2 in rows if r2[2] >= cut]
                        xsr = xsec_resid(rows)          # 방향: 잔차 상위 10종 롱
                    elif _sid0 == "x-peerlag":
                        # 종목쌍을 보는 유일한 규칙 — 상관행렬이 필요하다. 비용은 사전등록에
                        # 실측으로 적어 뒀다(월말당 2.6초 · 199개 월말에 8.8분).
                        zs, names = [], []
                        for t2 in tickers:
                            rs2 = R[t2]
                            w2 = rs2[i - 252:i]
                            if len(w2) < 252 or any(x is None for x in w2):
                                continue
                            if _stall(rs2, i - 1):
                                continue
                            m2 = sum(w2) / len(w2)
                            sd = math.sqrt(sum((x - m2) ** 2 for x in w2))
                            if sd <= 0:
                                continue
                            zs.append([(x - m2) / sd for x in w2]); names.append(t2)
                        cm = load_classmates()
                        NB = len(names)
                        C2 = [[0.0] * NB for _ in range(NB)]
                        for a2 in range(NB):
                            za = zs[a2]
                            for b2 in range(a2 + 1, NB):
                                zb = zs[b2]
                                s2 = 0.0
                                for k2 in range(252):
                                    s2 += za[k2] * zb[k2]
                                C2[a2][b2] = s2; C2[b2][a2] = s2
                        rows = []
                        for a2 in range(NB):
                            t2 = names[a2]
                            mates = cm.get(t2) or set()
                            nb = sorted(((C2[a2][b2], names[b2]) for b2 in range(NB)
                                         if b2 != a2 and names[b2] not in mates), reverse=True)[:20]
                            if len(nb) < 20:
                                continue
                            own = ret(px[t2], i - 1, 21)
                            if own is None:
                                continue
                            prs = [ret(px[z2], i - 1, 21) for _c2, z2 in nb]
                            prs = [x for x in prs if x is not None]
                            if len(prs) < 20:
                                continue
                            rows.append((t2, sum(prs) / len(prs), own))
                        xsr = xsec_resid(rows)          # 방향: 잔차 상위 10종 롱
                    for t in tickers:
                        P = px[t]
                        sid = S["sid"]
                        if sid == "x-52wh":
                            # 🚨 2026-08-04 버그 수정. 종전에는 분모가 **종가의 최대**였다.
                            #   그런데 창(P[i-252:i])이 신호일 i-1 을 포함하므로, 그날 종가가
                            #   창 최대인 종목은 점수가 정확히 1.0 이 된다 — 점수에 천장이 생긴다.
                            #   실측: 199개 월말 중 **149개(75%)에서 1.0 동점이 10종 이상**이었고
                            #   (동점 중앙 25종·최대 146종), sc.sort(reverse=True) 가 (점수, 티커)
                            #   튜플을 정렬하므로 그 10칸은 **티커 알파벳 역순(Z→A)** 으로 채워졌다.
                            #   즉 이 규칙은 '고점에 가장 가까운 10종'이 아니라 '신고가 종목 중
                            #   티커가 Z 에 가까운 10종'을 사고 있었다.
                            #   고치는 방향은 규칙문 그대로다 — 규칙문은 '52주 **최고가**'라고
                            #   적는데 구현이 종가 최대를 쓰고 있었다. 실제 일중 고가(hd)는 같은
                            #   저장소에 4,422일치 있고(2026-08-04 배선), 종가와 분할조정 기준이
                            #   같다는 것을 전수 확인했다(ld ≤ pxd ≤ hd 위반 0/2,112,332).
                            #   고가를 쓰면 종가가 그 창의 최대와 같아지는 일이 사실상 없어져
                            #   천장도 동점도 자연히 사라진다 — 동점을 깨는 새 파라미터를 넣는 것이
                            #   아니라 원래 재려던 것을 재는 것이다.
                            H = hid.get(t)
                            win = [x for x in (H or P)[max(0, i - 252):i] if x]
                            hi = max(win) if win else None
                            v = (P[i - 1] / hi) if (hi and P[i - 1]) else None
                        elif sid == "x-hlspread":
                            # 사전 패스가 만든 잔차를 그대로 쓴다(값이 없으면 후보 아님).
                            v = hls.get(t) if hls else None
                        elif sid in ("x-clv", "x-volvol", "x-delay", "x-peerlag"):
                            # 위 사전 패스가 중립화 잔차를 이미 만들어 뒀다.
                            v = xsr.get(t) if xsr else None
                        elif sid == "x-ongapd":
                            H2, L2 = hid.get(t), lod.get(t)
                            p2 = P[i - 1]
                            if not (H2 and L2) or not p2 or p2 < 5.0:
                                v = None
                            else:
                                g = gap_daily(H2, L2, P, t)

                                def _share(w):
                                    a = b = 0.0
                                    c = 0
                                    for k2 in range(max(0, i - w), i):
                                        x = g[k2]
                                        if x is None:
                                            continue
                                        a += x[0]; b += x[1]; c += 1
                                    return (a / b, c) if b > 0 else (None, c)
                                s63, n63 = _share(63)
                                s252, n252 = _share(252)
                                v = (s63 - s252) if (s63 is not None and s252 is not None
                                                     and n63 >= 32 and n252 >= 126) else None
                        elif sid == "x-lshock":
                            H2, L2 = hid.get(t), lod.get(t)
                            p2 = P[i - 1]
                            if not (H2 and L2) or not p2 or p2 < 5.0:
                                v = None
                            else:
                                S2 = cs_spread(H2, L2, t)
                                a = [x for x in S2[max(0, i - 63):i] if x is not None]
                                b = [x for x in S2[max(0, i - 252):max(0, i - 63)] if x is not None]
                                if len(a) < 32 or len(b) < 95:
                                    v = None
                                else:
                                    sa, sb = sum(a) / len(a), sum(b) / len(b)
                                    v = math.log(sa / sb) if (sa > 0 and sb > 0) else None
                        elif sid == "x-updown":
                            rs2 = R[t]
                            if _stall(rs2, i - 1):
                                v = None
                            else:
                                w2 = [(rs2[k2], ixr[k2]) for k2 in range(max(0, i - 252), i)
                                      if rs2[k2] is not None and ixr[k2] is not None]
                                mu = (sum(z[1] for z in w2) / len(w2)) if w2 else 0.0
                                dn = [z for z in w2 if z[1] < mu]
                                up = [z for z in w2 if z[1] >= mu]
                                if len(dn) < 40 or len(up) < 40:
                                    v = None
                                else:
                                    def _beta(pairs):
                                        mx2 = sum(z[1] for z in pairs) / len(pairs)
                                        my2 = sum(z[0] for z in pairs) / len(pairs)
                                        sxx = sum((z[1] - mx2) ** 2 for z in pairs)
                                        if sxx <= 0:
                                            return None
                                        return sum((z[1] - mx2) * (z[0] - my2) for z in pairs) / sxx
                                    bd, bu = _beta(dn), _beta(up)
                                    den = (abs(bd) + abs(bu)) if (bd is not None and bu is not None) else None
                                    v = ((bd - bu) / den) if (den and den >= 0.2) else None
                        elif sid == "x-dist200":
                            m = sma(P, i - 1, 200)
                            v = (P[i - 1] / m - 1) if (m and P[i - 1]) else None
                        elif sid == "x-mom-trend":
                            m200 = sma(P, i - 1, 200)
                            if not m200 or not P[i - 1] or P[i - 1] <= m200:
                                v = None
                            else:
                                v = (ret(P, i - 1, 252) or -9) - (ret(P, i - 1, 21) or 0)
                        elif sid == "x-rev1w":
                            v = -(ret(P, i - 1, 5) or 9)
                        elif sid == "x-minvar":
                            # 완전 최적화 대신 축소추정 역분산 — 개별 분산을 시장분산 쪽으로 반씩 당긴다
                            sv = vol(R[t], i - 1, 120)
                            mv = ixvol[i - 1]
                            v = -(0.5 * sv + 0.5 * mv) if (sv and mv) else None
                        elif sid == "x-riskbudget":
                            sv = vol(R[t], i - 1, 60)
                            v = (1.0 / sv) if sv and sv > 0 else None
                        elif sid == "x-lowbeta":
                            b = beta(R[t], ixr, i - 1, 120)
                            v = -b if b is not None else None
                        elif sid == "x-sue":
                            v = sue((FU.get(t) or {}).get("eps") or [], dates[i - 1])
                        elif sid == "x-epsacc":
                            e = eps_accel((FU.get(t) or {}).get("eps") or [], dates[i - 1])
                            p0 = P[i - 1]
                            v = (e / p0) if (e is not None and p0 and p0 > 0) else None
                        elif sid in FUND_SIDS:
                            # 펀더멘털은 종목 하나만 받는 람다로 못 준다 — 날짜·주식수·주가가 필요하다.
                            # 잔고 항목은 asof_fund(시점 값), 기간 누적값은 ttm(12개월)을 쓴다.
                            f = FU.get(t) or {}
                            dt_ = dates[i - 1]
                            sn = asof_fund(f.get("sh"), dt_)
                            p0 = P[i - 1]
                            mcap = (sn * p0) if (sn and p0 and sn > 0 and p0 > 0) else None
                            v = None
                            if sid == "x-btp":
                                e = asof_fund(f.get("eq"), dt_)
                                # 주당순자산 ÷ 주가. 자본잠식(음수)은 자연히 꼴찌로 간다.
                                v = (e / sn / p0) if (e is not None and mcap) else None
                            elif sid in ("x-valcomp", "x-valcomp-sn"):
                                # 🚨 여기서는 **원지표 셋을 모아 두기만** 한다. z-점수는 단면이
                                #   다 모여야 낼 수 있으므로 아래 루프 밖에서 z_composite 가 만든다.
                                e = asof_fund(f.get("eq"), dt_)
                                fc = ttm2(f.get("fcf"), f.get("fcf_a"), dt_)
                                lb = asof_fund(f.get("liab"), dt_)
                                cs = asof_fund(f.get("cash"), dt_)
                                m = {}
                                if e is not None and mcap:
                                    m["bp"] = e / mcap                     # 장부가/시총 = B/P
                                if fc is not None and mcap:
                                    m["fcfp"] = fc / mcap                  # FCF/시총
                                if e is not None and mcap and lb is not None:
                                    # ⚠ 기업가치 근사 — 이자부부채가 없어 총부채를 쓴다.
                                    #   매입채무·이연법인세까지 들어가 자본집약 업종의 EV 가 부푼다.
                                    #   섹터 중립판에서는 섹터 안에서 상쇄되지만 제약 없는 판에서는
                                    #   안 된다(사전등록 §2·실패 시나리오 ②).
                                    ev = mcap + lb - (cs or 0.0)
                                    if ev > 0:
                                        m["bev"] = e / ev
                                if m:
                                    comp_raw.setdefault(sid, []).append((t, m))
                                v = None                                   # 점수는 나중에 붙인다
                            elif sid == "x-fcfy":
                                fc = ttm2(f.get("fcf"), f.get("fcf_a"), dt_)
                                v = (fc / mcap) if (fc is not None and mcap) else None
                            elif sid == "x-payout":
                                # 환원총액 = 배당총액(주당배당 × 주식수) + 자사주매입액.
                                # 🚨 bb 는 연간 버킷으로 읽어야 한다(분기엔 Q1 만 남는다).
                                dp = ttm2(f.get("dps"), f.get("dps_a"), dt_)
                                bbv = ttm2(f.get("bb"), f.get("bb_a"), dt_)
                                if mcap and (dp is not None or bbv is not None):
                                    tot = (dp * sn if dp is not None else 0.0) + (bbv or 0.0)
                                    # 자사주는 유출액이라 양수다. 음수(순발행)면 환원이 아니다.
                                    v = (tot / mcap) if tot >= 0 else None
                            elif sid == "x-poacc":
                                # 퍼센트 영업발생액 = (순이익 − 영업현금흐름) ÷ |순이익|. 낮을수록 위.
                                # 분모가 자산이 아니라 |순이익|이라 잔고 태그의 2021-06 절벽을 안 탄다.
                                # 🚨 두 항을 각자 ttm2 로 읽으면 안 된다 — 순이익은 분기합산(최근 분기말
                                #   기준 12개월)이 되고 현금흐름은 연간버킷(직전 회계연도)이 되어 창이
                                #   최대 3분기 어긋난다. **같은 회계연도 기간말**에서 둘 다 뽑는다.
                                cut_ = _shift(dt_, FUND_LAG_DAYS)
                                nim = dict(f.get("ni_a") or [])
                                cfm = dict(f.get("cfo_a") or [])
                                rvm = dict(f.get("rev_a") or [])
                                d_ = next((d for d, _x in (f.get("ni_a") or [])
                                           if d <= cut_ and d in cfm), None)
                                if d_:
                                    ni_, cf_, rv_ = nim[d_], cfm[d_], rvm.get(d_)
                                    # 🚨 순이익이 0 근처면 비율이 폭발한다 — 매출의 1% 미만이면 뺀다.
                                    if rv_ and rv_ > 0 and abs(ni_) >= 0.01 * rv_:
                                        v = -((ni_ - cf_) / abs(ni_))
                            elif sid in ("x-gpa", "x-ocfp", "x-aci"):
                                # 금융업은 자산의 뜻이 달라(예대 잔고) 자산분모 수익성이 성립하지 않는다.
                                if (meta.get(t) or {}).get("sector") == "Financials":
                                    v = None
                                else:
                                    at = asof_fund(f.get("asset"), dt_)
                                    if sid == "x-ocfp":
                                        cf_ = ttm2(f.get("cfo"), f.get("cfo_a"), dt_)
                                        v = (cf_ / at) if (cf_ is not None and at and at > 0) else None
                                    elif sid == "x-gpa":
                                        g = ttm2(f.get("gp"), f.get("gp_a"), dt_)
                                        rv_ = ttm2(f.get("rev"), f.get("rev_a"), dt_)
                                        cg = ttm2(f.get("cogs"), f.get("cogs_a"), dt_)
                                        # 🚨 gp·cogs 가 둘 다 있으면 정합성부터 본다. 안 맞으면 그 종목의
                                        #   태깅을 믿을 수 없다(건보사 유형) → 후보에서 뺀다.
                                        if g is not None and cg is not None and rv_ and rv_ > 0:
                                            if abs(g + cg - rv_) / rv_ > 0.01:
                                                g = None
                                        if g is None and rv_ is not None and cg is not None:
                                            g = rv_ - cg              # 태그가 없을 때만 폴백
                                        v = (g / at) if (g is not None and at and at > 0) else None
                                    else:                              # x-aci
                                        # 설비투자÷매출을 연간 격자에서 4개 뽑아 최근/직전3년평균 −1.
                                        cx = [(d, x) for d, x in (f.get("capex_a") or [])
                                              if d <= _shift(dt_, FUND_LAG_DAYS)]
                                        rvm = dict(f.get("rev_a") or [])
                                        rat = []
                                        for d, x in cx[:4]:
                                            r_ = rvm.get(d)
                                            if r_ and r_ > 0 and x is not None:
                                                rat.append(x / r_)
                                        if len(rat) == 4 and sum(rat[1:]) > 0:
                                            base = sum(rat[1:]) / 3.0
                                            ci = rat[0] / base - 1.0
                                            v = -ci if abs(ci) <= 3.0 else None
                            elif sid == "x-ep":
                                ep_ = ttm2(f.get("eps"), f.get("eps_a"), dt_)
                                v = (ep_ / p0) if (ep_ is not None and p0 and p0 > 0) else None
                            elif sid == "x-sp":
                                rv = ttm2(f.get("rev"), f.get("rev_a"), dt_)
                                v = (rv / mcap) if (rv is not None and mcap) else None
                            elif sid == "x-roe":
                                nn, e = ttm2(f.get("ni"), f.get("ni_a"), dt_), asof_fund(f.get("eq"), dt_)
                                v = (nn / e) if (nn is not None and e and e > 0) else None
                            elif sid == "x-npm":
                                nn, rv = ttm2(f.get("ni"), f.get("ni_a"), dt_), ttm2(f.get("rev"), f.get("rev_a"), dt_)
                                v = (nn / rv) if (nn is not None and rv and rv > 0) else None
                            elif sid == "x-rgrow":
                                a1, a0 = (ttm2(f.get("rev"), f.get("rev_a"), dt_),
                                          ttm2(f.get("rev"), f.get("rev_a"), _shift(dt_, 365)))
                                v = (a1 / a0 - 1) if (a1 is not None and a0 and a0 > 0) else None
                            elif sid == "x-lowde":
                                e = asof_fund(f.get("eq"), dt_)
                                lb = asof_fund(f.get("liab"), dt_)
                                if lb is None:
                                    at = asof_fund(f.get("asset"), dt_)
                                    lb = (at - e) if (at is not None and e is not None) else None
                                # 부채가 적을수록 위. 자본잠식(e<=0)은 비율이 무의미해 뺀다.
                                v = -(lb / e) if (lb is not None and e and e > 0) else None
                            elif sid == "x-dy":
                                dp = ttm2(f.get("dps"), f.get("dps_a"), dt_)
                                v = (dp / p0) if (dp is not None and p0 and p0 > 0) else None
                            elif sid == "x-small":
                                v = -mcap if mcap else None
                            elif sid == "x-agrow":
                                # 🚨 0 이하를 **분자·분모 둘 다** 뺀다. 분자가 0 이면 증가율이
                                #   −100% 로 1등이 되어 자료 구멍이 편입된다(실측 PSKY·SW).
                                pr = yoy_pair(f.get("asset"), dt_)
                                if pr and pr[1] > 0 and pr[3] > 0:
                                    g = pr[1] / pr[3] - 1.0
                                    v = -max(-2.0, min(2.0, g))     # 낮을수록 위
                            elif sid == "x-shiss":
                                # 🚨 split_trim 을 거친 sh 가 아니라 단위오류만 교정한 sh_u +
                                #   이음매를 쓴다(안 그러면 대규모 발행 종목이 후보에서 사라진다).
                                pr = yoy_pair(f.get("sh_u") or f.get("sh"), dt_,
                                              seam=f.get("sh_seam"))
                                if pr and pr[1] > 0 and pr[3] > 0:
                                    g = pr[1] / pr[3] - 1.0
                                    v = -g if abs(g) <= 0.5 else None
                            elif sid == "x-custconc":
                                # 규약 그대로: build/PREREG-2026-08-04-CUSTCONC.md
                                # 단일 고객 매출 비중이 **높을수록** 위(고집중 롱).
                                v = custconc_asof(t, dt_)
                            elif sid == "x-cash":
                                ch = asof_fund(f.get("cash"), dt_)
                                at = asof_fund(f.get("asset"), dt_)
                                v = (ch / at) if (ch is not None and at and at > 0) else None
                        elif sid == "x-ivol":
                            # 시장 수익이 필요해 람다(종목 하나만 받는다)로는 못 준다
                            iv = idio_vol(R[t], ixr, i - 1, 120)
                            v = -iv if iv is not None else None
                        elif sid == "x-fip":
                            # 모멘텀 상위 5분위 밖이면 후보가 아니다(교집합 규약).
                            # ID 는 낮을수록 연속정보이므로 부호를 뒤집어 넣는다(정렬 내림차순).
                            # 🚨 v 는 이 루프에서 **초기화되지 않는다** — 갈래마다 반드시 대입해야
                            #   한다. 안 그러면 직전 종목 점수가 그대로 남아 엉뚱한 종목이 뽑힌다
                            #   (실측으로 걸렸다: 보유가 알파벳으로 뭉쳐 나왔다).
                            _id = (info_discreteness(R[t], i - 1)
                                   if (fip_ok is not None and t in fip_ok) else None)
                            v = -_id if _id is not None else None
                        elif sid == "x-residmom":
                            # 팩터 수익 셋이 필요하다(시장 + 규모·가치 대리변수). 대리변수를
                            # 못 읽었으면 후보가 0 이 되고, 그때는 XSEC_MIN_POOL 가드가 잡는다 —
                            # 조용히 '있는 것 전부'를 고르는 일이 없게 그 경로에 맡긴다.
                            v = (resid_mom(R[t], [ixr, FACP["SMB"], FACP["HML"]], me_list, i - 1)
                                 if FACP else None)
                        elif sid == "x-coskew":
                            # 같은 사유(시장 수익 필요). 정렬이 내림차순이므로 '가장 음인 것'을
                            # 뽑으려면 부호를 뒤집어 넣는다.
                            ck = coskew(R[t], ixr, i - 1, 252)
                            v = -ck if ck is not None else None
                        elif sid == "x-lowcorr":
                            # 같은 사유. '가장 낮은 상관'을 뽑으므로 부호를 뒤집는다.
                            cr = mkt_corr(R[t], ixr, i - 1, 252)
                            v = -cr if cr is not None else None
                        elif sid == "x-season":
                            # 월말 격자가 필요해 람다로는 못 준다.
                            v = same_month_avg(P, i - 1, dates, sorted(me))
                        elif sid == "x-snapback":
                            m200 = sma(P, i - 1, 200)
                            if not m200 or not P[i - 1] or P[i - 1] <= m200:
                                v = None
                            else:
                                rv = rsi(P, i - 1)
                                v = -rv if rv is not None else None
                        elif sid == "x-volsurge":
                            V = vlm[t]
                            m200 = sma(P, i - 1, 200)
                            # 🚨 해상도 게이트(vol_resolved 참조). 거래량이 백만주 정수로
                            #   저장돼 있던 탓에 이 규칙이 반올림 잡음을 순위로 쓰고 있었다.
                            if (not V or not m200 or not P[i - 1] or P[i - 1] <= m200
                                    or not vol_resolved(V, i - 1)):
                                v = None
                            else:
                                a = sma(V, i - 1, 20)
                                b = sma(V, i - 1, 60)
                                v = (a / b) if (a and b and b > 0) else None
                        else:
                            v = S["fn"](t, i - 1, P, R[t], vol(R[t], i - 1, 60))
                        if v is not None and v == v:
                            sc.append((v, t))
                    # 🚨 E30 — z-점수는 단면이 다 모여야 낼 수 있다. 위 루프에서 원지표만
                    #   모아 두었고 여기서 컴포지트를 만든다. 지표별로 결측 종목이 다르므로
                    #   z_composite 가 있는 지표만으로 평균한다(0 으로 채우지 않는다 —
                    #   0 은 z 척도에서 '평균'이라 자료 없는 종목이 중간 순위를 공짜로 받는다).
                    if S["sid"] in comp_raw:
                        sc = [(z, t) for t, z in z_composite(comp_raw[S["sid"]]).items()]
                    sc.sort(reverse=True)
                    pool_hist.append((dates[i - 1], len(sc)))
                    if S["sid"] == "x-valcomp-sn":
                        # 🚨 섹터 중립 — 각 섹터 1위 1종, 비중은 **유니버스 섹터 시총 비중**.
                        #   이 엔진은 원래 동일가중 전제라 비중을 실을 자리가 없었다(아래 hw).
                        _sec = {t: (meta.get(t) or {}).get("sector") or "" for _v, t in sc}
                        _mc = {}
                        for _v, t in sc:
                            _f = FU.get(t) or {}
                            _sn = asof_fund(_f.get("sh"), dates[i - 1])
                            _p0 = px[t][i - 1] if px.get(t) else None
                            if _sn and _p0 and _sn > 0 and _p0 > 0:
                                _mc[t] = _sn * _p0
                        _pw = pick_sector_neutral(sc, _sec, _mc, per=1)
                        new = [t for t, _w in _pw]
                        new_w = {t: w for t, w in _pw}
                    else:
                        new = pick_top(sc, S["sid"])
                        new_w = None
                    if len(sc) < XSEC_MIN_POOL:
                        # 🚨 후보가 바스켓 대비 얇으면 이것은 '선택'이 아니라 '있는 것 전부'다.
                        #   적대감사 실측: asset·cash·eq 태그는 KEEP_I=20분기 절단 탓에 최초 관측
                        #   중앙값이 2021-06-30 인데 백테스트는 2017-08 에 시작한다. 그 사이 x-agrow
                        #   후보는 2~5종이었고 전부 외국 연차보고(20-F) 발행인이었다(ASML·NBIS·SHOP·
                        #   CCEP·TRI·PDD — KEEP_I 가 분기제출자만 5년으로 자르기 때문). x-agrow 와
                        #   x-cash 의 상위10 바스켓 자카드가 그 구간 평균 0.83, 즉 서로 다른 축이라던
                        #   두 규칙이 같은 6종을 들고 있었다. sc[:TOPN] 이 후보 전량을 통과시키므로
                        #   순위가 아무 일도 하지 않는다.
                        #   후보가 0 이 아니라 3~7개라서 기존 first_i 재기준도 발동하지 않아
                        #   start=2017-08 · n_days=2238 이 그대로 보고됐다.
                        #
                        #   ⚠ 위 진단의 **원인 쪽은 2026-08-03 에 고쳤다** — refresh_facts.py 의
                        #   KEEP_Q/A/I 를 20/8/20(5년)에서 72/20/72(18년)로 늘렸다. 그 결과
                        #   얇은 달이 전 전략 합계 2,234 → 177 로 줄고 x-agrow·x-cash 를 포함한
                        #   12개 규칙이 **0** 이 됐다(실측). 남은 177 달은 절단이 아니라 규칙
                        #   자체의 준비기간이다(x-season·x-ltrev 각 48, x-residmom 24 …).
                        #   이 가드는 그대로 둔다. 원인이 하나 사라졌을 뿐, '있는 것 전부를
                        #   고른 것처럼 보고하지 않는다'는 성질은 규칙 추가마다 다시 필요하다.
                        thin += 1
                        # 들고 있던 것을 전부 판다 — 그것도 매매다(종전 turns 는 이걸 안 셌다).
                        _tr += 1.0 if hold else 0.0
                        hold = []; hw = None           # → 무보유. 재기준이 시작일을 정직하게 잡는다
                    elif new:
                        turns += len(set(new) ^ set(hold)) / (2 * TOPN) if hold else 1.0
                        # 오간 금액 = 대칭차 ÷ TOPN (판 것 + 산 것). turns 의 정의(교체 횟수)와
                        # 분모가 2배 다르다 — 타이밍의 Σ|Δw| 와 눈금을 맞추려면 이쪽이다.
                        _tr += (len(set(new) ^ set(hold)) / TOPN) if hold else 1.0
                        hold = new
                        hw = new_w                     # None 이면 동일가중(종전과 같다)
                if hold and first_i is None:
                    first_i = i
                if hw:
                    # 가중 바스켓. 결측 종목은 빼고 남은 비중을 되정규화한다 —
                    # 0 으로 두면 그날 현금을 든 것이 되어 섹터 중립이 조용히 깨진다.
                    _pairs = [(hw[t], R[t][i]) for t in hold if R[t][i] is not None and t in hw]
                    _sw = sum(w for w, _x in _pairs)
                    r = (sum(w * x for w, x in _pairs) / _sw) if _sw > 0 else 0.0
                else:
                    rs = [R[t][i] for t in hold if R[t][i] is not None]
                    r = sum(rs) / len(rs) if rs else 0.0
                srets.append(r)
                traded.append(_tr)
                _tr = 0.0
                nav.append(nav[-1] * (1 + r))
            turn = turns / max(1, (n - MIN_HIST) / 252)
            expo = 1.0
            start_i = first_i
            hold_now = {"kind": "xsec", "as_of": dates[-1], "n": len(hold),
                        "tickers": sorted(hold),
                        # 이름을 같이 실어야 화면에서 티커에 커서를 올렸을 때 회사명이 뜬다
                        "names": {t: (meta.get(t) or {}).get("name") or t for t in sorted(hold)},
                        "note": "마지막 월말 리밸런스에서 고른 %d종목을 동일가중으로 보유 중이다. "
                                "다음 월말에 다시 뽑는다." % len(hold)}

        bnav = [100.0]
        for i in range(MIN_HIST + 1, n):
            bnav.append(bnav[-1] * (1 + bxr[i]))
        d2 = dates[MIN_HIST:]

        # ── 실제 시작일에 맞춰 전부 다시 세운다 ────────────────────────────
        # 펀더멘털이 늦게 채워지는 규칙은 한동안 후보가 없어 현금으로 앉아 있다(고ROE 는 3.4년,
        # 장부가대비저평가는 2.7년). 그 구간에서 전략 NAV 는 100 에 고정인데 대조군·지수는
        # 계속 복리로 오른다 — 그대로 두면 차트가 '깨져' 보이고 CAGR·샤프·초과수익이 전부
        # 죽은 구간에 끌려 내려간다. 비교는 **같은 날에서 함께 출발**해야 성립한다.
        _k = max(0, (start_i or (MIN_HIST + 1)) - (MIN_HIST + 1))
        if _k:
            nav = [x / nav[_k] * 100 for x in nav[_k:]]
            bnav = [x / bnav[_k] * 100 for x in bnav[_k:]]
            srets = srets[_k:]
            traded = traded[_k:]
            d2 = d2[_k:]
        st = ann_stats(nav, d2, rf)
        bs = ann_stats(bnav, d2, rf)

        # ── 비용을 태운다 ──────────────────────────────────────────────────
        # 회전율을 싣기만 하고 한 번도 안 태우던 것을 여기서 태운다(COST_BPS 주석 참조).
        # 대조군은 매수후보유라 비용이 사실상 없다 — 그래서 비용은 전략에만 붙는다.
        _bx = bxr[(start_i or (MIN_HIST + 1)):]
        _yrs = max(1e-9, len(srets) / 252.0)
        net_sens, _mstats = {}, None
        for _bps in COST_BPS:
            _c = _bps / 10000.0
            _sn = [srets[i] - _c * traded[i] for i in range(len(srets))]
            _nv = [100.0]
            for _r in _sn:
                _nv.append(_nv[-1] * (1 + _r))
            _ns = ann_stats(_nv, d2[:len(_nv)], rf)
            net_sens[str(_bps)] = {
                "cagr": _ns.get("cagr"), "sharpe": _ns.get("sharpe"),
                "excess_cagr": round((_ns.get("cagr", 0) - bs.get("cagr", 0)), 2),
                "d_sharpe": round((_ns.get("sharpe") or 0) - (bs.get("sharpe") or 0), 3),
                "t": tstat(_sn, _bx),
            }
            if _bps == COST_BPS_MAIN:
                _mstats = _ns
        _main = net_sens[str(COST_BPS_MAIN)]
        net = dict(_main, bps=COST_BPS_MAIN,
                   # 연 매매대금(NAV 배). turnover 와 달리 **두 족이 같은 눈금**이다 —
                   # 종목선택의 turnover 는 '바스켓 교체 횟수'(대칭차÷2·TOPN)이고
                   # 타이밍의 turnover 는 Σ|Δw| 라 같은 매매량이 2배 다르게 찍혀 있었다.
                   traded=round(sum(traded) / _yrs, 2),
                   drag=round((st.get("cagr", 0) - (_main.get("cagr") or 0)), 2),
                   sens=net_sens)
        # 자산 랩·ML 랩과 **같은 필드 이름**으로도 낸다. 셋이 같은 표(strategy_index)로 들어가는데
        # 종목 랩만 이름이 다르면 화면이 종목 랩의 비용만 못 그린다 — 실제로 그랬다:
        # explorer 의 '비용 후' 줄은 metrics_net·cost_bp 를 읽는데 종목 랩은 그 필드를
        # 아예 안 냈고, 그래서 57종 전부 비용 표시가 없었다. asset_backtest 머리말이
        # "이 수치를 종목 전략에 그대로 옮기면 안 된다(개별주 10종목 포트라면 더 물어야 한다)"
        # 라고 적어 둔 그 자리가 비어 있던 셈이다.
        # ⚠ 단위가 다르다 — 자산 랩의 cost_bp 는 **왕복**이고 COST_BPS 는 **편도**다.
        #   같은 필드에 실을 때는 왕복으로 환산한다(편도 10bp = 왕복 20bp). 자산 랩은 왕복 5bp 라
        #   같은 열에 놓고 크기를 비교하면 안 된다 — 대상이 ETF 냐 개별주 10종이냐가 다르다.
        # ⚠ 대조군(bench_net)은 매수후보유라 회전이 0 이다 → 비용도 0. 자산 랩은 대조군도
        #   물리지만(60/40 은 리밸런싱한다) 여기 대조군은 정말로 매매를 안 한다.
        # 얇게 만들 때 쓸 절대 위치 색인 — d2[i] 의 전체 격자 위치가 5의 배수인 것만 남긴다.
        _off = MIN_HIST + max(0, (start_i or (MIN_HIST + 1)) - (MIN_HIST + 1))
        _keep5 = [_i for _i in range(min(len(d2), len(nav), len(bnav))) if (_off + _i) % 5 == 0]
        if len(_keep5) < 60:                 # 너무 짧아지면 그대로 둔다(회귀가 아예 안 도는 것보다 낫다)
            _keep5 = list(range(min(len(d2), len(nav), len(bnav))))
        # 🚨 끝점은 반드시 **실제 마지막 값**이어야 한다. 절대 격자로 자르면 마지막 인덱스가
        #   5의 배수가 아닐 때 빠지고, 그러면 스파크라인이 최신 수익률을 안 보여주며
        #   상세차트와 카드의 끝 날짜가 어긋난다(validate_site 가 실제로 잡았다).
        #   strategy_index.thin() 도 같은 이유로 끝점을 강제한다.
        _last = min(len(d2), len(nav), len(bnav)) - 1
        if _keep5 and _keep5[-1] != _last:
            _keep5.append(_last)

        cost_extra = {
            "cost_bp": round(COST_BPS_MAIN * 2, 1),
            "metrics_net": _mstats or {}, "bench_net": bs,
            "cost_drag": net["drag"],
            "cost_kill": bool(((st.get("sharpe") or 0) - (bs.get("sharpe") or 0)) > 0
                              and ((_main.get("sharpe") or 0) - (bs.get("sharpe") or 0)) <= 0),
            "cost_sensitive": bool(net["drag"] >= 0.5),
        }

        # ── 🚨 매매 대상 대비 성적 ─────────────────────────────────────────
        # 판정 대조군은 S&P 500(PR)이다(사용자 결정 2026-07-28). 그런데 **타이밍 규칙이
        # 실제로 사는 것은 랩 동일가중 유니버스**이고 그 둘은 같은 자산이 아니다 —
        # 동일가중 매수후보유 CAGR 18.66% · 샤프 0.965 대 S&P 500(PR) 12.10% · 0.669.
        # 그래서 **노출을 1.0 으로 고정한 '타이밍을 전혀 하지 않는 규칙'** 을 같은 판정기에
        # 넣으면 Δ샤프 +0.296 · 초과 +6.56%p · **t 4.90** 이 나온다(실측). 임계 3.33 을
        # 그냥 넘는다. 즉 타이밍 20종의 t 에는 '타이밍 실력'이 아닌 몫
        # (동일가중 vs 시총가중 + TR vs PR + 생존편향)이 통째로 들어 있다.
        #
        # 대조군은 바꾸지 않는다(사용자 결정을 코드가 되돌리면 안 된다). 대신 **자기가 사는
        # 것 대비** 값을 나란히 싣는다 — 이 열에서 0 근처면 그 규칙은 아무 일도 안 한 것이다.
        # ⚠ 종목선택 규칙에도 같이 싣는다. 이쪽에서는 이것이 **예전 대조군**(같은 유니버스
        #   동일가중)이라, 문턱이 내려가기 전의 잣대로 다시 읽는 열이 된다.
        _ewx = ixr[(start_i or (MIN_HIST + 1)):]
        _ewnav = [100.0]
        for _r in _ewx:
            _ewnav.append(_ewnav[-1] * (1 + (_r or 0.0)))
        _ews = ann_stats(_ewnav, d2[:len(_ewnav)], rf)
        vs_traded = {
            "label": "랩 동일가중 유니버스 매수후보유",
            "cagr": _ews.get("cagr"), "sharpe": _ews.get("sharpe"),
            "excess_cagr": round((st.get("cagr", 0) - _ews.get("cagr", 0)), 2),
            "d_sharpe": round((st.get("sharpe") or 0) - (_ews.get("sharpe") or 0), 3),
            "t": tstat(srets, [(x or 0.0) for x in _ewx]),
            "t_net": tstat([srets[i] - (COST_BPS_MAIN / 10000.0) * traded[i]
                            for i in range(len(srets))], [(x or 0.0) for x in _ewx]),
            "note": ("타이밍 규칙이 실제로 매매하는 대상이다. 판정 대조군(S&P 500 PR)과 다른 자산이라, "
                     "여기 t 가 0 근처면 그 규칙은 대조군 격차를 재고 있었던 것이다."
                     if S["kind"] == "timing" else
                     "2026-07-28 이전의 대조군이다. 지금 대조군(S&P 500 PR)보다 연 6%p 이상 높아 "
                     "문턱이 그만큼 높았다 — 예전 잣대로 다시 읽는 열이다."),
        }
        out.append({
            "sid": S["sid"], "name": S["name"], "kind": S["kind"], "arch": S.get("arch"),
            # 성격 — 통합 목록에서 '무엇을 하는 전략인가'로 묶는 축(strategy_kinds.json 어휘).
            # 파일 출처가 아니라 역할로 나눠야 읽는 사람이 비교할 수 있다.
            "role": ("수익엔진" if S["kind"] == "xsec" else "타이밍오버레이"),
            "rule": S["rule"], "why": S["why"],
            "metrics": st, "bench": bs,
            "excess_cagr": round((st.get("cagr", 0) - bs.get("cagr", 0)), 2),
            "d_sharpe": round((st.get("sharpe") or 0) - (bs.get("sharpe") or 0), 3),
            "t": tstat(srets, bxr[(start_i or (MIN_HIST + 1)):]),
            # 🚨 비용 뒤 성적. 위 t·excess_cagr 는 전부 **무비용(gross)** 이다 —
            #   이 랩이 회전율을 싣기만 하고 안 태우던 것을 2026-08-04 에 태우기 시작했다.
            #   net.t 는 편도 10bp 기준이고, net.sens 에 5·10·20bp 를 전부 싣는다.
            "net": net, **cost_extra, "vs_traded": vs_traded,
            "turnover": round(turn, 2), "exposure": round(expo * 100, 1),
            "start": d2[0], "n_days": len(d2),
            # 커버리지 게이트가 무보유로 둔 월말 수. 0 이 아니면 그 규칙의 표본은 화면에 적힌
            # 기간보다 짧다 — 시작일(start)이 이미 재기준돼 있으므로 여기서는 사유만 남긴다.
            "n_thin": (thin if S["kind"] == "xsec" else 0),
            # 후보 풀의 처음·끝·최소·중앙. 램프가 크면 '앞구간의 상위 10'과 '뒷구간의 상위 10'이
            # 같은 선택이 아니라는 뜻이고, 그 사실을 규칙마다 싣는다(위 pool_hist 주석 참조).
            # ⚠ 기준점은 '첫 월말'이 아니라 **후보가 처음 생긴 월말**이다. 규칙마다 준비기간이
            #   달라(동월 계절성은 월말 61개, 잔차 모멘텀은 36개월) 첫 월말은 후보 0 인 경우가
            #   많고, 그걸 분모로 삼으면 램프가 아니라 준비기간을 재게 된다.
            #   ⚠ 그리고 '첫 달 대비 몇 배'로 재지 않는다. 그 값은 후보가 2종이던 한 달이
            #     지배해 버려서(실측 x-rgrow 2 → 491 = 245배) 규칙의 성질이 아니라 가장자리를
            #     재게 된다. 유니버스 대비 비율로 재도 안 된다 — x-fip 은 정의상 모멘텀 상위
            #     5분위만 보므로 늘 좁고(후보 중앙 96종·최소 84), 그건 결함이 아니라 규약이다.
            #     그래서 **그 규칙 자신의 중앙값 대비 절반에 못 미친 달**을 센다. 재는 것이
            #     '좁다'가 아니라 '평소보다 얇았다' 여야 커버리지 램프만 잡힌다.
            "pool": ((lambda nz: {"first": nz[0][1], "last": nz[-1][1],
                                  "min": min(x[1] for x in nz),
                                  "med": sorted(x[1] for x in nz)[len(nz) // 2],
                                  "narrow": (lambda m: sum(1 for x in nz if x[1] < m * 0.5))(
                                      sorted(x[1] for x in nz)[len(nz) // 2]),
                                  "d0": nz[0][0], "n": len(nz)})(
                         [x for x in pool_hist if x[1] > 0])
                     if (S["kind"] == "xsec" and any(x[1] > 0 for x in pool_hist)) else None),
            "holdings": hold_now,
            # 🚨 2026-08-05 — `[::5]` 는 **그 규칙 자신의 시작점**부터 5칸씩 센다. 규칙마다
            #   시작일이 다르므로(재기준·커버리지 게이트) 남는 날짜 격자가 서로 어긋나고,
            #   incr5(6계열 공통 날짜 회귀)가 계산 자체를 못 한다 — 실측으로 3규칙
            #   (x-season·x-aci·x-ltrev)이 그래서 incr5 가 None 이었다. 자산 랩에서 같은
            #   원인으로 43종이 통째로 못 돌던 것과 같다(gthin 참조).
            #   → 전체 격자의 **절대 위치**로 자른다. 어느 규칙이든 서로의 부분집합이 되어
            #     교집합이 짧은 쪽 길이만큼 남는다.
            "nav": [round(nav[_i], 2) for _i in _keep5],
            "bnav": [round(bnav[_i], 2) for _i in _keep5],
            "dates": [d2[_i] for _i in _keep5],
            # 카드에 그릴 곡선 묶음 — 낙폭·연도별을 전체 계열에서 계산해 둔다.
            # 화면이 줄인 곡선에서 다시 재면 카드에 적힌 MDD와 그림이 어긋난다.
            "chart": curve_pack(d2, nav, bnav, idx_rets=IDXR,
                                i0=(start_i or (MIN_HIST + 1)) - 1),
        })
        # 입력이 격자를 못 덮으면 그 규칙은 '못한' 게 아니라 '못 잰' 것이다.
        # 심리 게이트가 정확히 그랬다 — sentiment.json 이 3년뿐이라 10년 격자 앞부분에서
        # 신호가 없어 계속 현금이 됐고, 노출이 반토막 나 판정이 뒤집혔다. 결손을 실력으로
        # 읽지 않도록 커버리지를 재서 모자라면 판정을 보류한다(뒤 verdict 루프가 존중한다).
        if S["sid"] == "t-sentgate":
            _cov = sum(1 for i in range(MIN_HIST, n) if sent[i] is not None) / max(1, n - MIN_HIST)
            out[-1]["input_cov"] = round(_cov * 100, 1)
            if _cov < 0.90:
                out[-1]["cov_short"] = True
                print("  [심리게이트] 입력 커버리지 %.1f%% — 판정 보류(규칙이 아니라 데이터가 없다)"
                      % (_cov * 100))

    # ── 다중검정 임계 ────────────────────────────────────────────────
    # 규칙 N개를 같은 표본에서 돌렸다. |t|>2 라는 관례는 검정이 하나일 때 이야기다.
    # 본페로니(α=0.05/N)로 임계를 올린다 — Harvey·Liu·Zhu(2016)가 발표된 이상현상에
    # 권고한 |t|≈3.0과도 대체로 같은 자리에 온다.
    N = len(out)
    alpha = 0.05 / max(1, N)
    tcrit = z_of(alpha)      # 모듈 레벨 함수 — pit_backtest 도 z_crit() 으로 같은 것을 쓴다
    for r in out:
        t = r["t"]
        if r.get("cov_short"):
            # 입력이 구간을 못 덮은 규칙 — 성과 숫자는 싣되 판정은 하지 않는다.
            r["verdict"] = "판정 불가"
            r["why"] = (r["why"] + " ⚠ 이 구간에서 입력(심리지수)이 %.1f%%만 존재해 "
                        "나머지 기간이 자동으로 현금 처리됐다. 여기 성과는 규칙의 실력이 아니다."
                        % (r.get("input_cov") or 0))
        elif t is None:
            r["verdict"] = "판정 불가"
        elif r["d_sharpe"] <= 0:
            r["verdict"] = "열위"
        elif abs(t) >= tcrit:
            r["verdict"] = "통과 후보"
        else:
            r["verdict"] = "구별 불가"

    # ── 생존편향 실측 반영 ──────────────────────────────────────────────
    # 위 판정은 전부 '오늘의 유니버스를 과거로 소급한' 표본에서 나온다. 2026-07-27 에
    # 시점별 편입 이력으로 같은 구간을 다시 돌려 재 보니(창은 2026-08-04 에 2015-01~ 로 넓혔다)
    # t 가 통째로 무너졌다. 소급 표본에서 문턱을 넘었다는 사실만으로 '통과 후보'를 유지하면
    # **편향을 발견으로 인증**하게 된다 — 실측이 있는 규칙은 그 값으로 다시 건다.
    #
    # 1회 교정 측정이라 코드에 상수로 박는다(상시 산출은 불가: 원천이 라이선스이고
    # CI 러너가 사내망에 못 닿으며, yfinance 는 편출·상폐 종목을 주지 않는다).
    # 재측정하면 이 표를 갱신할 것. (sid: PIT CAGR%, PIT Sharpe, PIT t)
    # 값은 **build/pit_backtest.py 가 만든 data/pit_strategies.json 에서 읽는다.** 예전엔 상수표로
    # 박아 뒀는데(사내 DB 가격을 쓰던 시절엔 재현이 안 돼 그럴 수밖에 없었다), 지금은 가격을
    # yfinance 로 받아 누구나 다시 돌릴 수 있으므로 산출물을 단일 출처로 둔다.
    # ⚠ 파일이 없으면 **조용히 넘어가지 않는다** — 그러면 판정이 소급 기준으로 슬그머니 되돌아간다.
    PIT_MEASURED, PIT_WINDOW, PIT_BENCH, PIT_ASOF, PIT_DOC = {}, None, None, None, {}
    try:
        _pj = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
        PIT_ASOF = _pj["as_of"]
        PIT_WINDOW = "%s~%s" % (_pj["start"][:7], PIT_ASOF[:7])
        PIT_DOC = _pj
        for _r in _pj.get("strategies") or []:
            _m, _b = _r.get("metrics") or {}, _r.get("bench") or {}
            # retro = **같은 창의 소급 레그**. 이것과의 차이가 유니버스 편향이다 —
            # 랩 본편(2252일)과 직접 빼면 구간 차이가 섞여 편향이 아니게 된다.
            _rt = _r.get("retro") or {}
            PIT_MEASURED[_r["sid"]] = (_m.get("cagr"), _m.get("sharpe"), _r.get("t"),
                                       _r.get("bias_excess"), _rt.get("excess_cagr"),
                                       _rt.get("t"), _r.get("bias_cagr"),
                                       (_rt.get("metrics") or {}).get("cagr"),
                                       _r.get("bench_bias_cagr"),
                                       # 🚨 대조군·창을 전략별로 받는다. 전에는 마지막 전략의
                                       #   bench 를 전 규칙 공통으로 썼는데, 보유시작 재기준으로
                                       #   창이 갈리는 규칙(x-season 은 231거래일 늦게 시작)에서
                                       #   초과수익이 이중으로 어긋났다(적대감사).
                                       _b.get("cagr"), _r.get("start"), _r.get("n_days"))
            PIT_BENCH = _b.get("cagr")
        print("  [PIT] %s 에서 %d종 읽음 (%s · 대조군 CAGR %.2f%%)"
              % ("pit_strategies.json", len(PIT_MEASURED), PIT_WINDOW, PIT_BENCH or 0))
    except FileNotFoundError:
        print("⚠ [PIT] data/pit_strategies.json 이 없다 — 생존편향 반영 없이 소급 기준 판정이 나간다. "
              "사내망 PC에서 `python build/pit_backtest.py` 를 돌릴 것.")
    except Exception as _e:
        print("⚠ [PIT] pit_strategies.json 을 못 읽었다(%s) — 소급 기준 판정이 나간다." % str(_e)[:60])

    _dg = []
    for r in out:
        m = PIT_MEASURED.get(r["sid"])
        if not m:
            continue
        pc, ps, pt, pbias, prx, prt, pbc, prc, pbb, pbn, pst, pnd = m
        if pt is None:
            continue
        _bn = pbn if pbn is not None else PIT_BENCH
        _win = ("%s~%s" % (pst[:7], PIT_ASOF[:7])) if (pst and PIT_ASOF) else PIT_WINDOW
        r["pit"] = {"window": _win, "cagr": pc, "sharpe": ps, "t": pt,
                    "n_days": pnd,
                    # 다중검정 문턱은 화면이 손으로 적지 않게 여기서 실어 보낸다 — explorer 에
                    # '27종·3.11·랩 51종·3.30' 이 박혀 있었고 실제(33·57)와 어긋났다.
                    "n_rules": len(PIT_MEASURED), "t_crit": PIT_DOC.get("t_crit"),
                    "n_family_lab": PIT_DOC.get("n_family_lab"),
                    "t_crit_lab": PIT_DOC.get("t_crit_lab"),
                    "n_over": sum(1 for _v in PIT_MEASURED.values()
                                  if _v[2] is not None
                                  and abs(_v[2]) >= (PIT_DOC.get("t_crit_lab") or 99)),
                    "t_max": PIT_DOC.get("t_max"),
                    "bench_cagr": _bn, "excess_cagr": round(pc - _bn, 2),
                    # 같은 창의 소급 레그와 그 차이 — 화면이 '편향이 얼마였나'를 적을 수 있게.
                    # 🚨 bias_cagr(전략 CAGR 기준)가 편향의 본체다. bias_excess 는 두 레그의
                    #   대조군이 각자의 동일가중 지수라 벤치 편향이 상쇄돼 항상 그만큼 깎인다.
                    "retro_excess": prx, "retro_t": prt, "bias_excess": pbias,
                    "retro_cagr": prc, "bias_cagr": pbc, "bench_bias_cagr": pbb}
        if r["verdict"] == "통과 후보" and abs(pt) < tcrit:
            _dg.append((r["name"], r["t"], pt))
            r["verdict"] = "구별 불가"
            r["why"] += (" ⚠ 시점정확(PIT) 재측정에서 이 규칙의 t는 %.2f로 다중검정 문턱(%.2f)에 "
                         "한참 못 미친다(소급 표본에서는 %.2f였다). 소급 표본의 통과는 편향이 만든 "
                         "것으로 보아 판정을 내렸다." % (pt, tcrit, r["t"] or 0))
    if _dg:
        print("  [PIT 반영] 통과 후보 → 구별 불가 %d종:" % len(_dg))
        for nm, t0, t1 in _dg:
            print("    · %-28s t %.2f → %.2f" % (nm[:28], t0 or 0, t1))
    # ── 타이밍 재판정 — 자기가 사는 것을 못 이기면 그 t 는 대조군 격차다 ──────
    # 🚨 PIT 강등과 같은 자리에 같은 모양으로 건다(2026-08-04). 사유는 DATA-FACTS 12 다 —
    #   타이밍 규칙은 랩 동일가중 유니버스를 사는데 판정 대조군은 S&P 500(PR)이라, 노출을
    #   1.0 으로 고정한 '아무것도 안 하는 규칙'조차 t 4.90 을 받는다. 그 t 로 '통과 후보'를
    #   주면 대조군 격차를 타이밍 실력으로 게시하는 것이다.
    #   ⚠ 대조군은 바꾸지 않는다(2026-07-28 사용자 결정). 등급만 강등한다 — 수치는 그대로 두고
    #     '그 수치를 이렇게 읽어야 한다'를 판정에 반영하는 것이다. PIT 강등과 같은 방침이다.
    _tg = []
    for r in out:
        if r["kind"] != "timing" or r["verdict"] != "통과 후보":
            continue
        vt = (r.get("vs_traded") or {}).get("t")
        if vt is None or vt > 0:
            continue
        _tg.append((r["name"], r["t"], vt))
        r["verdict"] = "구별 불가"
        r["why"] += (" ⚠ 자기가 실제로 매매하는 것(랩 동일가중 유니버스) 대비로는 t가 %.2f다 — "
                     "단독 t %.2f는 판정 대조군(S&P 500 PR)이 매매 대상과 다른 자산이라 생긴 "
                     "격차를 대부분 담고 있다. 노출을 1.0으로 고정한 '타이밍을 전혀 하지 않는 "
                     "규칙'도 같은 판정기에서 t 4.90을 받는다. 그래서 판정을 내렸다."
                     % (vt, r["t"] or 0))
    if _tg:
        print("  [매매대상 반영] 통과 후보 → 구별 불가 %d종:" % len(_tg))
        for nm, t0, t1 in _tg:
            print("    · %-28s t %.2f → 매매대상 대비 %.2f" % (nm[:28], t0 or 0, t1))

    # 실측이 없는 규칙에도 같은 편향이 걸려 있다. 특히 소형주 계열은 편출이 곧 '작아진 회사'라
    # 가장 세게 걸리는데, 시점별 재무·주식수가 없어 재지 못했다 — 침묵하지 말고 적어 둔다.
    # 🚨 종전에는 `sid in ("x-small","x-btp")` 로 손으로 박혀 있었다. 그런데 그 둘은 지금 PIT
    #   표에 **있고**(x-small t 0.98 · x-btp 1.34), 그래서 같은 카드에 'PIT 재측정에서 t는
    #   0.98' 과 'PIT 재측정 대상이 아니었다' 가 나란히 실렸다. 정작 진짜 미측정인 규칙에는
    #   아무 표시가 없었다. 손으로 적은 목록이 자료와 어긋난 것이므로 **자료에서 뽑는다.**
    for r in out:
        if r.get("pit") or r["verdict"] not in ("통과 후보", "구별 불가"):
            continue
        if r["kind"] == "timing":
            r["why"] += (" ⚠ 이 규칙은 PIT(생존편향) 재측정 대상이 아니다 — 그 레그는 종목선택 "
                         "규칙만 돈다. 그런데 타이밍 규칙은 종목을 고르지 않고 오늘의 518종 "
                         "동일가중 유니버스를 통째로 사므로 생존편향을 100% 그대로 받는다. "
                         "덜 받는 것이 아니라 더 받는 쪽이고, 여기 판정은 그 보정 없이 나온 값이다.")
        else:
            r["why"] += (" ⚠ 이 규칙은 PIT 재측정 대상이 아니었다(시점별 자료 부재). 지수에서 "
                         "빠지는 것이 대개 '작아진 회사'라 생존편향이 세게 걸리는 계열이므로, "
                         "여기 판정은 측정으로 뒷받침되지 않았다.")

    out.sort(key=lambda x: -(x["d_sharpe"] or -9))

    # ── 중복도 ──────────────────────────────────────────────────────────
    # 규칙을 늘리면 '더 많이 검증했다'는 착각이 생긴다. 하지만 24개 타이밍 규칙이 전부
    # 같은 지수 가격에서 나오면 서로 다른 베팅이 아니라 같은 베팅 24개다. 실제로 얼마나
    # 겹치는지 재서 그대로 싣는다 — 본페로니는 검정이 독립일 때의 보정이라, 겹칠수록
    # 필요 이상으로 보수적이 된다(임계를 낮추지는 않는다. 재량이 들어가는 순간 검정이 아니게 된다).
    # 계산기 자체는 모듈 레벨에 있다(ml·asset 랩이 같은 것을 쓰기 위해). 여기서는 옛 이름으로 잇는다.
    _rets, _corr = nav_rets, corr_of
    _paired_excess, _incr, _incr_multi = paired_excess, incr1, incr_multi
    # ── 표본 구간의 성격 ────────────────────────────────────────────────
    # 결과가 '타이밍은 안 통한다'로 읽히기 쉽다. 하지만 이 표본에서 벤치마크 자체가
    # 연 22%·샤프 1.08이면, 어느 날이든 현금을 쥔 규칙은 구조적으로 진다. 그건 규칙의
    # 실력이 아니라 구간의 성질이다 — 수치로 적어 독자가 과대해석하지 않게 한다.
    _up = _dn = 0
    for i in range(MIN_HIST, n):
        m200 = sma(ix, i, 200)
        if m200 is None:
            continue
        if ix[i] > m200:
            _up += 1
        else:
            _dn += 1
    _pk = ix[MIN_HIST]
    _dds = []
    _cur = 0.0
    for i in range(MIN_HIST, n):
        _pk = max(_pk, ix[i])
        _cur = min(_cur, ix[i] / _pk - 1)
        _dds.append(ix[i] / _pk - 1)
    _big = 0
    _inside = False
    for x in _dds:                       # -10%를 밑돈 국면이 몇 번 있었나(고점 회복으로 리셋)
        if x < -0.10 and not _inside:
            _big += 1
            _inside = True
        elif x > -0.02:
            _inside = False
    regime = {
        "up_days": _up, "down_days": _dn,
        "up_share": round(_up / max(1, _up + _dn), 3),
        "n_dd10": _big,
        "note": "표본 구간에서 지수가 200일선 위에 있던 날이 %.0f%%(%d일 중 %d일)이고, "
                "고점 대비 -10%%를 밑돈 국면은 %d번뿐이었다. 현금을 쥐는 규칙은 이런 구간에서 "
                "구조적으로 진다 — 여기 '열위'가 많은 것은 규칙의 실력만이 아니라 구간의 성질이기도 하다. "
                "반대로 이 표본은 하락 방어 능력을 사실상 검증하지 못한다."
                % (100 * _up / max(1, _up + _dn), _up + _dn, _up, _big),
    }

    _tm = [r for r in out if r["kind"] == "timing"]
    _rr = {r["sid"]: _rets(r) for r in _tm}
    # 원수익률 상관 — 종전부터 싣던 값. 남겨 두되 **판정에는 쓰지 않는다**: 타이밍 규칙은
    # 대부분의 날을 100% 편입으로 보내므로 원수익률끼리는 구조적으로 높게 나오고,
    # 그 높음은 '같은 베팅'이 아니라 '둘 다 대체로 들고 있었다'는 뜻이기도 하다.
    _pairs_raw = []
    for _i in range(len(_tm)):
        for _j in range(_i + 1, len(_tm)):
            c = _corr(_rr[_tm[_i]["sid"]], _rr[_tm[_j]["sid"]])
            if c is not None:
                _pairs_raw.append({"a": _tm[_i]["name"], "b": _tm[_j]["name"], "c": round(c, 3)})
    _pairs_raw.sort(key=lambda x: -x["c"])
    _cs_raw = sorted(x["c"] for x in _pairs_raw)

    # 🚨 **초과수익 상관으로 다시 잰다.** 종전에는 타이밍만 원수익률로, 종목선택만 초과수익으로
    #   쟀다 — 같은 표의 두 족을 서로 다른 자로 잰 것이고, 그래서 나란히 못 놓는 숫자였다.
    #   실측(2026-08-04, 타이밍 20종 190쌍): 초과수익 기준 중앙 0.713 · **0.80 이상이 69쌍**.
    #   종목선택은 중앙 0.091 · 0.80 이상 3쌍이다. 즉 **훨씬 더 붐비는 쪽은 타이밍인데**
    #   증분 알파 게이트는 종목선택에만 걸려 있었다.
    _pairs = []
    for _i in range(len(_tm)):
        for _j in range(_i + 1, len(_tm)):
            a, b = _paired_excess(_tm[_i], _tm[_j])
            c = _corr(a, b)
            if c is not None:
                _pairs.append({"a": _tm[_i]["name"], "b": _tm[_j]["name"],
                               "c": round(c, 3), "n": len(a)})
    _pairs.sort(key=lambda x: -x["c"])
    _cs = sorted(x["c"] for x in _pairs)

    # ── 종목선택 규칙의 중복도 + 증분 알파 ───────────────────────────────
    # 🚨 종전에는 타이밍 23종만 쟀다. 그런데 본페로니 족은 xsec 을 **독립 검정으로 세고 있었고**,
    #   실제로는 안 그랬다 — 에코 모멘텀이 12-1 과 상관 0.888·보유 교집합 0.50 인데도 별개로
    #   세어졌다. 적대감사가 두 번 권고한 확장이다. 임계를 낮추지는 않는다(재량이 들어가면
    #   검정이 아니게 된다). 대신 '몇 개를 검증했는가'를 독자가 깎아 읽을 수 있게 싣는다.
    _xs = [r for r in out if r["kind"] == "xsec"]
    _xpairs = []
    for _i in range(len(_xs)):
        for _j in range(_i + 1, len(_xs)):
            a, b = _paired_excess(_xs[_i], _xs[_j])
            c = _corr(a, b)
            if c is not None:
                _xpairs.append({"a": _xs[_i]["name"], "b": _xs[_j]["name"],
                                "c": round(c, 3), "n": len(a)})
    _xpairs.sort(key=lambda x: -x["c"])
    _xcs = sorted(x["c"] for x in _xpairs)

    # 규칙마다 '가장 닮은 기존 규칙'을 찾아 그것 대비 증분 알파를 잰다.
    #
    # 🚨 **두 족 모두에 건다**(2026-08-04). 종전에는 _xs(종목선택)에만 걸려 있었다. 그 결과
    #   PIT 강등 뒤 종목 랩에 하나 남은 '통과 후보'가 하필 **타이밍 규칙(t-chand, 단독 t 4.7)**
    #   이었는데, 그 규칙만 이 랩의 두 관문(PIT·증분알파)을 **둘 다 안 거친** 상태였다 —
    #   PIT 는 xsec 만 돌리고, 증분 알파도 xsec 만 쟀기 때문이다. 붐빔은 타이밍이 더 심한데
    #   (초과수익 상관 중앙 0.713 대 0.091) 게이트는 반대쪽에만 있었다.
    #   ⚠ 이웃은 **같은 족 안에서만** 고른다. 종목선택 규칙을 시장 오버레이로 통제하는 것은
    #     '이미 들고 있는 사람에게 새로 주는 것이 있느냐'라는 이 검정의 질문과 맞지 않는다.
    _byname = {r["name"]: r for r in _xs}
    for _fam in (_xs, _tm):
        for r in _fam:
            best = None
            for r2 in _fam:
                if r2 is r:
                    continue
                a, b = _paired_excess(r, r2)
                c = _corr(a, b)
                if c is None:
                    continue
                if best is None or c > best[0]:
                    best = (c, r2["name"], a, b)
            if not best:
                continue
            inc = _incr(best[2], best[3])
            if inc:
                r["incr"] = {"vs": best[1], "corr": round(best[0], 3),
                             "alpha": inc["alpha"], "t": inc["t"], "beta": inc["beta"]}
            # 🚨 '가장 닮은 이웃 하나'만 통제하면 문턱이 너무 무르다. 실측(2026-08-04, 게시 56종):
            #   이웃 1개 → 5개로 바꾸면 증분 t 가 중앙 0.35 내리고 최악은 2.72 내린다.
            #   **증분 t ≥ 2 를 넘던 13종 중 5종이 5개 통제에서 떨어진다**
            #   (x-season 2.54→0.87 · x-payout 2.35→0.76 · x-residmom 2.78→1.58 · x-fcfy 3.71→2.10).
            #   붐비는 축은 이웃이 여럿이라 하나만 빼서는 남는 것이 있어 보인다.
            #   → 상위 5 이웃 **동시** 통제값을 함께 싣는다. 사전등록 게이트는 이쪽을 쓸 것.
            nb = sorted(((abs(_corr(*_paired_excess(r, r2)) or 0), r2["name"], r2)
                         for r2 in _fam if r2 is not r), key=lambda z: -z[0])[:5]
            if len(nb) == 5:
                m5 = _incr_multi(r, [z[2] for z in nb])
                if m5:
                    r["incr5"] = dict(m5, vs=[z[1] for z in nb])
    # 🚨 '증분 알파 없음'을 그대로 세면 안 된다 — 두 가지가 섞인다.
    #   (a) 이웃이 설명하고 남는 게 없다(진짜 중복)  (b) 애초에 단독으로도 알파가 없다.
    #   이 표는 통과 후보가 0종이라 대부분이 (b)다. 정보가 있는 것은 **단독으로는 세 보이는데
    #   이웃 대비로는 사라지는** 규칙이므로, 단독 |t|≥2 인 것만 센다(에코 모멘텀이 그 사례다).
    # ── 사전등록 게이트 반영 — 판정기가 문서와 다른 말을 하지 않게 ─────────────
    # 🚨 자동 판정기는 단독 t 와 Δ샤프만 본다. 그런데 이 랩의 사전등록 게이트는 셋이다
    #   (단독 t ≥ 임계 · incr5.t ≥ 2.0 · 비용 후 t ≥ 임계). 그래서 사전등록 문서가
    #   '기각'이라 적은 규칙에 표는 '통과 후보' 배지를 달고 있었다 — 2026-08-04 에 실제로
    #   두 건이 그랬다(x-hlspread incr5 1.11 · x-clv 비용 후 3.32).
    #   문서와 표가 갈리면 읽는 사람은 표를 믿는다. 게이트를 판정기에 그대로 건다.
    #   ⚠ 강등만 한다. 게이트를 넘었다고 등급을 올리지는 않는다 — 올리는 판단에는 PIT 레그와
    #     사전등록 여부가 더 필요하고, 그건 사람이 문서로 한다.
    _pg = []
    for r in out:
        if r["verdict"] != "통과 후보":
            continue
        i5 = (r.get("incr5") or {}).get("t")
        nt = ((r.get("net") or {}).get("sens") or {}).get("10", {}).get("t")
        bad = []
        if i5 is not None and abs(i5) < 2.0:
            bad.append("증분 알파(이웃 5개 동시 통제) t %.2f < 2.0" % i5)
        if nt is not None and abs(nt) < tcrit:
            bad.append("비용 후(편도 10bp) t %.2f < 임계 %.2f" % (nt, tcrit))
        if not bad:
            continue
        _pg.append((r["name"], r["t"], "; ".join(bad)))
        r["verdict"] = "구별 불가"
        r["why"] += (" ⚠ 사전등록 게이트 미달로 판정을 내렸다 — %s. 단독 t %.2f 만 보면 문턱을 "
                     "넘지만, 이 랩의 게시 기준은 셋을 전부 넘을 것을 요구한다."
                     % (" · ".join(bad), r["t"] or 0))
    if _pg:
        print("  [사전등록 게이트] 통과 후보 → 구별 불가 %d종:" % len(_pg))
        for nm, t0, why in _pg:
            print("    · %-28s t %.2f — %s" % (nm[:28], t0 or 0, why))

    # 🚨 이 블록은 **증분 알파(incr5) 계산 뒤**에 있어야 한다. 처음에 판정 직후에 뒀다가
    #   incr5 가 아직 None 이라 그 조건이 통째로 건너뛰어졌다(x-hlspread incr5 1.11 이
    #   그대로 통과 후보로 남았다). 판정 순서가 곧 게이트의 유효 범위다.
    def _absorbed(fam):
        _nz = [r for r in fam if r.get("incr") and r["incr"].get("t") is not None]
        return sorted((r for r in _nz if abs(r["incr"]["t"]) < 2.0 and abs(r.get("t") or 0) >= 2.0),
                      key=lambda r: -(r["incr"]["corr"]))
    _weak = _absorbed(_xs)
    _tweak = _absorbed(_tm)
    # 사실상 같은 규칙(ρ≥0.99) — 족 수를 부풀리는 가장 뚜렷한 형태다.
    _twins = [p for p in _xpairs if p["c"] >= 0.99]

    dup = {
        "n_timing": len(_tm),
        "median": round(_cs[len(_cs) // 2], 3) if _cs else None,
        "n_over_95": sum(1 for c in _cs if c >= 0.95),
        "n_over_80": sum(1 for c in _cs if c >= 0.80),
        "top": _pairs[:6],
        # 종전에 싣던 원수익률 상관 — 비교용으로만 남긴다(위 주석 참조).
        "median_raw": round(_cs_raw[len(_cs_raw) // 2], 3) if _cs_raw else None,
        "n_over_95_raw": sum(1 for c in _cs_raw if c >= 0.95),
        # 타이밍도 증분 알파를 받는다(2026-08-04부터).
        "timing_n_absorbed": len(_tweak),
        "timing_absorbed": [{"name": r["name"], "vs": r["incr"]["vs"], "corr": r["incr"]["corr"],
                             "t_solo": r.get("t"), "t_incr": r["incr"]["t"]} for r in _tweak[:8]],
        "n_xsec": len(_xs),
        "xsec_median": round(_xcs[len(_xcs) // 2], 3) if _xcs else None,
        "xsec_n_over_80": sum(1 for c in _xcs if c >= 0.80),
        "xsec_top": _xpairs[:6],
        # 단독으로는 세 보이는데 이웃 대비로는 사라지는 규칙(단독 |t|≥2 · 증분 |t|<2).
        "xsec_n_absorbed": len(_weak),
        "xsec_absorbed": [{"name": r["name"], "vs": r["incr"]["vs"], "corr": r["incr"]["corr"],
                           "t_solo": r.get("t"), "t_incr": r["incr"]["t"]} for r in _weak[:8]],
        "xsec_n_twins": len(_twins),
        "xsec_twins": _twins[:4],
        "xsec_note": "종목선택 규칙끼리의 초과수익 상관(공통 날짜에서만 계산 — 규칙마다 구간이 "
                     "다르다)과, 가장 닮은 규칙 대비 증분 알파. 증분 알파는 후보 초과수익을 "
                     "이웃 초과수익에 회귀한 절편이다 — 이웃을 이미 들고 있는 사람에게 새로 "
                     "주는 것이 있느냐를 묻는다. ⚠ 증분 알파가 없다고 다 중복인 것은 아니다. "
                     "이 표는 통과 후보가 0종이라 대부분은 애초에 단독 알파가 없어서다. "
                     "그래서 '흡수됨'은 단독 |t|≥2 인 규칙만 센다.",
        "note": "타이밍 규칙끼리의 **초과수익** 상관(2026-08-04부터 — 그 전에는 원수익률로 쟀다). "
                "두 족을 같은 자로 재야 나란히 놓을 수 있기 때문이다. 원수익률 상관은 "
                "median_raw 로 함께 남긴다. 0.95를 넘으면 이름만 다른 같은 베팅에 가깝고, "
                "규칙 수가 늘어도 실제로 검증한 '서로 다른 아이디어' 수는 그만큼 늘지 않는다.",
    }

    # 생존편향 실측 한 줄을 **데이터에서** 만든다. 숫자를 문장에 박으면 재측정할 때마다 거짓말이 된다.
    _pit_limit = None
    if PIT_MEASURED and PIT_BENCH is not None:
        _w0, _w1 = PIT_WINDOW.split("~")
        _idx = [i for i, d in enumerate(dates[MIN_HIST:]) if _w0 <= d[:7] <= _w1]
        _lab_bench = None
        if len(_idx) > 60:
            _i, _j = _idx[0], _idx[-1]
            _bn = [100.0]
            for k in range(MIN_HIST + 1, n):
                _bn.append(_bn[-1] * (1 + ixr[k]))
            if _bn[_i] > 0:
                _yrs = (_j - _i) / 252.0
                _lab_bench = ((_bn[_j] / _bn[_i]) ** (1 / _yrs) - 1) * 100 if _yrs > 0 else None
        # ⚠ 전 구간 CAGR 과 PIT CAGR 을 그냥 빼면 안 된다. 창이 달라 그 차이의 상당 부분이
        #   생존편향이 아니라 구간이 달라서 생긴다. 랩 쪽도 PIT 창으로 잘라 같은 구간끼리 뺀다.
        _ov = []
        for _r in out:
            _m = PIT_MEASURED.get(_r["sid"])
            if not (_m and _m[0] is not None):
                continue
            _nv, _dd = _r.get("nav") or [], _r.get("dates") or []
            _k = [q for q, dd in enumerate(_dd) if _w0 <= dd[:7] <= _w1]
            if len(_k) < 20 or not _nv[_k[0]]:
                continue
            _yr = (_k[-1] - _k[0]) * 5 / 252.0          # nav 는 5거래일 간격 표본
            if _yr <= 0:
                continue
            _labc = ((_nv[_k[-1]] / _nv[_k[0]]) ** (1 / _yr) - 1) * 100
            _ov.append(_labc - _m[0])
        _ov.sort()
        _med = _ov[len(_ov) // 2] if _ov else None
        _pit_limit = (
            "생존편향의 크기(실측) — 매월말 그때 실제로 지수에 있던 종목만 후보로 두고 같은 구간"
            "(%s)을 다시 돌린 결과다. 대조군 CAGR이 %s%.2f%%로, 가격·거래량 규칙 %d종의 CAGR은 "
            "중앙값 %.1f%%p 과대로 나온다. 모멘텀 계열이 가장 심해 t가 3.4 안팎에서 1.5 미만으로 "
            "내려앉는다 — 다만 t 하락분 전부가 편향은 아니다. PIT 표본이 짧아(1461일 대 2252일) "
            "그중 3분의 1가량은 구간 단축에서 온다. 그래도 남는 하락이 커서 '통과'는 유지되지 않는다. "
            "산출: build/pit_backtest.py (멤버십은 사내 DB, 가격은 yfinance)."
            % (PIT_WINDOW,
               ("%.2f%%→" % _lab_bench) if _lab_bench else "",
               PIT_BENCH, len(PIT_MEASURED), _med if _med is not None else 0))

    # 표본 길이를 사람이 읽는 말로 — 문장에 '3년'을 박아 두면 구간을 바꿀 때마다 거짓말이 된다.
    _yrs = (n - MIN_HIST) / 252.0
    _span_txt = ("%.1f년" % _yrs) if _yrs < 10 else ("%d년" % round(_yrs))

    # ── 생존편향 눈금: 랩 대조군 vs 현실의 동일가중 지수(RSP) ──────────────
    # 랩 대조군은 '오늘의 518종목'을 과거에 소급한 동일가중이라 그 사이 지수에서 빠진
    # 회사가 하나도 없다. RSP 는 같은 기간을 실제로 굴린 동일가중 S&P 500 ETF다 —
    # 편출·편입이 실제로 일어났고 보수도 뺀 값이다. 둘의 격차를 상시로 싣는다.
    #
    # ⚠ 이 격차를 생존편향 하나로 읽으면 안 된다. 세 가지가 같은 방향으로 섞여 있다.
    #   ① 생존편향(랩이 유리)  ② 유니버스 차이 — 랩은 NASDAQ 100 전용 종목까지 포함해
    #   이 구간 기술주 강세를 더 받는다(랩이 유리)  ③ RSP 보수 0.20%(RSP가 불리).
    #   따라서 이 값은 '생존편향의 상한'이자 '생존편향+틸트 합의 추정치'다.
    #   그래도 눈금이 없는 것보다 낫다 — 지금까지는 비교 대상 자체가 없었다.
    # 지수 자체의 Sharpe — 전략과 **같은 잣대**(같은 구간·같은 rf·ann_stats)로 잰다.
    # 화면·리포트가 '지수보다 나은가'를 물을 때 이 값을 단일 출처로 쓴다(각자 계산하면 갈라진다).
    idx_sh = {}
    for _lab, _rr in (IDXR or {}).items():
        _nv2 = [100.0]
        for i in range(MIN_HIST + 1, n):
            _nv2.append(_nv2[-1] * (1 + _rr[i]))
        _st2 = ann_stats(_nv2, dates[MIN_HIST:], rf)
        idx_sh[_lab] = {"cagr": _st2.get("cagr"), "sharpe": _st2.get("sharpe"),
                        "mdd": _st2.get("mdd")}
    if idx_sh:
        print("  [지수 잣대] " + " · ".join(
            "%s CAGR %.2f%% Sharpe %.3f" % (k, v["cagr"], v["sharpe"])
            for k, v in idx_sh.items() if v.get("sharpe") is not None))

    surv = None
    _rsp = (IDXR or {}).get("동일가중 S&P 500")
    if _rsp:
        _nv = [100.0]
        for i in range(MIN_HIST + 1, n):
            _nv.append(_nv[-1] * (1 + _rsp[i]))
        _rs = ann_stats(_nv, dates[MIN_HIST:], rf)
        _bs = ann_stats(ewnav_ref, dates[MIN_HIST:], rf) if ewnav_ref else {}
        if _rs.get("cagr") is not None and _bs.get("cagr") is not None:
            surv = {
                "lab_bench_cagr": _bs["cagr"], "rsp_cagr": _rs["cagr"],
                "gap_cagr": round(_bs["cagr"] - _rs["cagr"], 2),
                "lab_bench_sharpe": _bs.get("sharpe"), "rsp_sharpe": _rs.get("sharpe"),
                "note": "랩 대조군(오늘의 %d종목 동일가중을 과거로 소급)이 같은 기간 실제 "
                        "동일가중 S&P 500(RSP·보수 후)보다 연 %+.2f%%p 앞선다. 생존편향과 "
                        "유니버스 틸트(NASDAQ 100 전용 종목 포함)가 함께 만든 격차이며, "
                        "생존편향 단독의 상한으로 읽어야 한다."
                        % (len(tickers), _bs["cagr"] - _rs["cagr"]),
            }
            print("  [생존편향 눈금] 랩 동일가중 유니버스 %.2f%% vs RSP %.2f%% → 격차 %+.2f%%p"
                  % (_bs["cagr"], _rs["cagr"], _bs["cagr"] - _rs["cagr"]))

    doc = {
        "note": "테크니컬 규칙을 실제로 돌린 결과. 좋은 것만 고르지 않고 돌린 규칙을 전부 싣는다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": dates[-1], "start": dates[MIN_HIST], "n_days": n - MIN_HIST,
        "n_stocks": len(tickers), "topn": TOPN,
        "bench_label": "S&P 500(PR) 매수후보유",
        "span_years": round((n - MIN_HIST) / 252.0, 1),
        "surv_proxy": surv,
        "idx_stats": idx_sh,
        "t_crit": tcrit,
        "t_crit_note": "규칙 %d개를 같은 표본에서 돌렸으므로 본페로니(α=0.05/%d)로 임계를 올렸다. "
                       "검정이 하나일 때의 관례 |t|>2 를 그대로 쓰면 우연을 발견으로 읽는다." % (N, N),
        "rf_note": "샤프는 FRED DGS3MO 월평균을 일할로 환산해 차감",
        "limits": [
            # ⚠ 기간을 숫자로 박지 말 것. 예전엔 '3년'이 문장에 박혀 있어 구간을 늘린 뒤에도
            #   "표본이 3년(2254거래일)뿐이다"라는 자기모순을 그대로 출력했다. 표본에서 파생한다.
            "생존편향 — 오늘의 %d종목을 과거 %s에 그대로 적용한다. 그 사이 편출된 종목이 없어 "
            "모든 수치가 실제보다 좋게 나온다. 이 저장소에 시점별 편입 이력이 없어 보정할 수 없다. "
            "구간이 길수록 누락된 편출 종목이 쌓여 이 왜곡은 더 커진다." % (len(tickers), _span_txt),
            # 실측 한 줄은 build/pit_backtest.py 산출물에서 만든다(위 _pit_limit).
            # 구간을 안 맞추면 2017~2020 강세장이 섞여 편향이 과대평가된다 — 그래서 같은 구간으로 잰다.
        ] + ([_pit_limit] if _pit_limit else
             ["생존편향의 크기 — 아직 재지 못했다. 사내망 PC에서 build/pit_backtest.py 를 돌리면 "
              "매월말 실제 편입 종목 기준으로 다시 재서 이 자리에 수치가 들어온다."]) + ([

            # 보정은 못 해도 크기는 잴 수 있다. 눈금이 없으면 독자가 스스로 할인할 방법이 없다.
            # ⚠ 이 값은 '수준이 얼마나 부풀려졌나'다. 초과수익이 넘어야 할 문턱이 **아니다** —
            #   초과는 전략−대조군인데 둘 다 같은 편향된 유니버스에서 나와 대체로 상쇄된다.
            #   예전엔 여기에 "초과가 이 안쪽이면 실력이 아니다"라고 적었다(잘못).
            surv["note"] + " 전략 수익은 그만큼 부푼 세계의 숫자다. ⚠ 대조군을 S&P 500(PR)으로 "
            "바꾼 뒤로는 이 편향이 초과수익에서 상쇄되지 않는다 — 예전 대조군(같은 유니버스 "
            "동일가중)은 같은 편향을 태우고 있어 대체로 상쇄됐지만, 지수는 그렇지 않다. "
            "즉 여기 초과수익·ΔSharpe·t 는 실제보다 좋게 나온 값이다.",
        ] if surv else []) + [
            # 대조군을 바꾼 사실과 그 크기를 숫자로 남긴다. 이걸 안 적으면 예전 결과와 나란히
            #   놓고 '전략이 좋아졌다'로 읽게 된다 — 좋아진 것은 전략이 아니라 문턱이다.
            "⚠ 대조군을 바꿨다(2026-07-28 사용자 결정) — 예전에는 같은 유니버스 동일가중 "
            "매수후보유였고 지금은 S&P 500(PR)이다. 동일가중 유니버스는 오늘 명단을 과거로 "
            "소급한 것이라 실제 동일가중 S&P 500(RSP)보다 연 %+.2f%%p 높았다. 즉 예전 문턱이 "
            "그만큼 높았다. 같은 규칙인데 ΔSharpe 가 전반적으로 올라간 것은 규칙이 좋아져서가 "
            "아니라 문턱이 내려갔기 때문이다. 예전 판정과 나란히 놓고 비교하지 말 것."
            % (surv.get("gap_cagr") if surv and surv.get("gap_cagr") is not None else 0.0),
            "표본이 %s(%d거래일)이다. 이 구간이 겪은 국면이 결과를 지배할 수 있어, 좋은 샤프가 "
            "실력인지 구간인지 가리려면 구간 밖 검증이 따로 필요하다." % (_span_txt, n - MIN_HIST),
            "비용 0(gross). 회전율이 높은 규칙일수록 실제와 벌어지므로 연 회전율을 함께 싣는다.",
            # 지수를 PR 로 바꾼 이상(사용자 결정), 그 격차가 과장이라는 사실을 반드시 함께 적는다.
            "차트의 S&P 500·NASDAQ 100 은 가격지수다 — 배당이 빠져 있다. 전략 수익은 배당을 "
            "재투자한 기준이라, 지수가 연 약 2%p 불리하게 잡힌다. 지수와의 격차는 그만큼 과장된 "
            "값이므로 '지수를 이겼다'를 그대로 읽지 말 것.",
            "다중검정 — 규칙 %d개를 같은 표본에서 돌렸다. 그중 최고는 우연히도 좋아 보인다. "
            "그래서 하나도 빼지 않고 전부 싣는다." % len(STRATS),
            "신호는 당일 종가로 계산해 다음 거래일부터 적용한다(선견 없음). 횡단면은 월말 리밸런스.",
            "종목 전략은 상위 10종목만 들고 간다. 50종목은 사실상 지수라 규칙이 고르는 게 없다시피 하고, 화면에서 '지금 무엇을 들고 있나'도 읽히지 않는다. 대신 10종목은 표본이 얇아 결과가 더 시끄럽다 — 개별 성과보다 판정(구별 가능한가)을 먼저 볼 것.",
            regime["note"],
            "규칙끼리 많이 겹친다 — 타이밍 규칙 쌍의 상관 중앙값이 %s이고 %d쌍은 0.95를 넘는다. "
            "규칙 수가 곧 검증한 아이디어 수는 아니다." % (dup["median"], dup["n_over_95"]),
            # 🚨 2026-08-04 추가. 얇은 달(<30) 카운트로는 안 보이던 것을 드러낸다.
            _pool_limit(out),
            "이중클래스 — 같은 회사의 두 클래스(GOOG·GOOGL 등)를 한 바스켓에 담지 않는다"
            "(2026-08-04 사용자 결정). 담으면 10종이 아니라 한 회사에 두 칸을 준 9종 바스켓이 "
            "되기 때문이다. 실측 %d회·%d규칙에서 걸렸고, 그 자리는 다음 순위 종목이 채웠다."
            % (sum(DUAL_SKIPS.values()), len(DUAL_SKIPS)),
        ],
        "dup": dup, "regime": regime,
        # 목록에서 뺀 규칙 — 아카이브 재현 링크(arch)를 잃지 않으려고 남긴다.
        "retired": RETIRED_RECS,

        "strategies": out,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    # 이중클래스 배제가 실제로 몇 번 걸렸는지 남긴다. 0 이면 규칙이 놀고 있다는 뜻이고,
    # 그것도 알아야 한다(cik_map.json 이 없으면 조용히 0 이 된다).
    if DUAL_SKIPS:
        _tp = sorted(DUAL_SKIPS.items(), key=lambda kv: -kv[1])[:5]
        print("이중클래스 배제: %d회 · %d규칙 (같은 회사의 다른 클래스가 상위에 같이 선 자리) — %s"
              % (sum(DUAL_SKIPS.values()), len(DUAL_SKIPS),
                 " · ".join("%s %d" % (k, v) for k, v in _tp)))
    else:
        print("이중클래스 배제: 0회 — data/cik_map.json 이 없거나 겹친 적이 없다")
    print("다중검정 임계 |t| ≥ %.2f (본페로니 α=0.05/%d)" % (tcrit, N))
    import collections as _c
    print("판정:", dict(_c.Counter(r["verdict"] for r in out)))
    print("전략 %d개 · %s ~ %s (%d거래일) · %d종목 · %.0fKB"
          % (len(out), doc["start"], doc["as_of"], doc["n_days"], len(tickers),
             os.path.getsize(OUT) / 1024))
    print("벤치마크(동일가중): CAGR %.2f%% · 샤프 %s · MDD %.2f%%"
          % (bs.get("cagr", 0), bs.get("sharpe"), bs.get("mdd", 0)))
    print()
    print("%-26s %7s %7s %7s %7s %6s %6s" % ("전략", "CAGR", "샤프", "MDD", "Δ샤프", "t", "회전"))
    for r in out:
        m = r["metrics"]
        print("%-26s %7.2f %7s %7.2f %7.3f %6s %6.1f"
              % (r["name"][:24], m.get("cagr", 0), m.get("sharpe"), m.get("mdd", 0),
                 r["d_sharpe"], r["t"], r["turnover"]))
    return 0


if __name__ == "__main__":
    sys.exit(run())
