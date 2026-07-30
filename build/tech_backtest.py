#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""테크니컬 타이밍·횡단면 전략 백테스트 → data/tech_strategies.json

기각 아카이브는 '무엇을 왜 기각했는가'만 적혀 있었다. 그건 결론이지 근거가 아니다.
이 파일은 **규칙을 실제로 돌려 숫자를 내는** 자리다 — 통과든 기각이든 같은 표에서.

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
    """
    if not series:
        return None
    cut = _shift(date, lag)
    got = [(d, v) for d, v in series if d <= cut]
    if not got:
        return None
    if len(got) >= 2 and _days_between(got[0][0], got[1][0]) >= 300:
        return got[0][1]
    if len(got) < 4 or _days_between(got[0][0], got[3][0]) > 400:
        return None
    return sum(v for _d, v in got[:4])


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


SPLIT_TRIMMED = {}      # 티커 → (자른 날짜, 배수). 얼마나 잘랐는지 로그·limits 에 싣는다


def split_trim(sh, eps, dps, tk=""):
    """🚨 분할 기준 불일치 관측을 잘라낸다 — 안 자르면 순수 선견이 된다.

    주가는 **분할조정본**(auto_adjust=True)이라 전 구간이 오늘 기준이다. 그런데 SEC 주당지표
    (eps·dps)와 주식수(sh)는 **당시 보고치**다. refresh_facts.pick() 이 같은 기간의 중복
    보고 중 filed 최신본을 남기는데, SEC 의 소급재작성은 뒤 제출본에 비교표시로 다시 실린
    기간까지만 닿는다 — 그래서 한 계열 안에서 분할 전·후 기준이 **섞인다**.
      실측(data/fx/CMG.json): sh 2023-06-30 = 1387.37, 2023-03-31 = 27.79(×49.92).
      그 시점 E/P 가 112.5%(실제 ~1.7%)로 나와 x-ep 이 CMG 를 70개 월말 중 42회 담았다.
      분할비는 미래 정보이므로 이것은 편향이 아니라 **선견**이다.

    되돌리지 않고 **자른다.** 배수를 도출해 재계산하려면 실제 증자·합병(PCG 4.05배 파산탈출
    증자 등)과 분할을 비율만으로 구별해야 하고 그 판단이 틀리면 없던 숫자를 만든다.
    자르면 그 시점 후보에서 빠질 뿐이다(적대감사가 두 방식을 다 재서 같은 답을 확인했다).
    ⚠ 총액 항목(rev·ni·eq·liab·cfo·capex)은 달러라 분할과 무관하다 — 건드리지 않는다.
    두 단계로 나눈다 — 섞이는 사유가 둘이고 정답 기준이 서로 다르기 때문이다.
      ① 단위 오류(천주 vs 백만주) — 소수의 관측만 어긋난다. 정답은 **다수**다.
         실측: WAT sh 59.76 옆에 82139.0(×1380) · ROL ×3273 · COP ×1134 · TER ×978.
         분할비는 아무리 커도 50 정도이므로 100배 넘는 것은 분할이 아니라 단위다.
      ② 분할 기준 — 절반 넘게 어긋날 수 있다. 정답은 **최신**이다(조정주가가 오늘 기준이므로).
         🚨 여기서 다수결을 쓰면 거꾸로 간다 — CMG 는 분할 전 관측이 11개로 다수라
           중앙값 규칙이 분할 전(27.79)을 남겼다. 최신에서 거슬러 올라가며 자른다.
    """
    if not sh or len(sh) < 3:
        return sh, eps, dps
    vs = sorted(v for _d, v in sh if v and v > 0)
    if not vs:
        return sh, eps, dps
    med = vs[len(vs) // 2]
    # ① 단위 오류 — 100배 넘게 벗어난 관측(분할로는 설명 안 되는 크기)
    bad = {d for d, v in sh if not v or v <= 0 or v / med > 100 or med / v > 100}
    ok = [(d, v) for d, v in sh if d not in bad]
    # ② 분할 기준 — 최신부터 거슬러 올라가 첫 단절 이전을 전부 버린다
    for i in range(len(ok) - 1):
        a, b = ok[i][1], ok[i + 1][1]
        if a and b and b > 0 and (a / b >= 1.5 or a / b <= 1 / 1.5):
            bad |= {d for d, _v in sh if d < ok[i][0]}
            break
    if not bad:
        return sh, eps, dps
    worst = max((max(v / med, med / v) for d, v in sh if d in bad and v and v > 0), default=0)
    SPLIT_TRIMMED[tk] = (min(bad), round(worst, 2), len(bad), len(sh))
    keep = lambda ser: [(d, v) for d, v in (ser or []) if d not in bad]
    # eps·dps 는 sh 와 같은 기간말 격자를 쓰므로 같은 날짜를 뺀다. 격자가 어긋난 관측은
    # 판정할 근거가 없어 남긴다(총액 항목은 애초에 분할과 무관하다).
    return keep(sh), keep(eps), keep(dps)


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

        def series(key):
            v = tg.get(key) or {}
            a = v.get("i") or v.get("q") or []
            return [(x[0], x[1]) for x in a if isinstance(x, list) and len(x) == 2
                    and isinstance(x[1], (int, float))]

        eq, sh, ep = series("eq"), series("sh"), series("eps")
        rev, ni, dps = series("rev"), series("ni"), series("dps")
        sh, ep, dps = split_trim(sh, ep, dps, j.get("t") or fn[:-5])
        asset, liab = series("asset"), series("liab")
        cfo, capex = dict(series("cfo")), dict(series("capex"))
        # 잉여현금흐름은 같은 기간종료일에 둘 다 있을 때만 만든다. capex가 없는 종목을
        # cfo만으로 채우면 자본지출이 큰 업종이 통째로 좋아 보인다.
        fcf = sorted(((k, cfo[k] - capex[k]) for k in cfo if k in capex), reverse=True)
        if eq or sh or fcf or ep:
            out[j.get("t") or fn[:-5]] = {"eq": eq, "sh": sh, "fcf": fcf, "eps": ep,
                                          "rev": rev, "ni": ni, "dps": dps,
                                          "asset": asset, "liab": liab}
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
    with io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8") as f:
        st = json.load(f)
    dates = st["pxd_dates"]
    n = len(dates)
    px, vlm, meta = {}, {}, {}
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
        meta[t] = {"name": s.get("name") or "", "sector": s.get("sector") or ""}
    rf = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8")).get("monthly") or {}
    rf = {k: v for k, v in rf.items() if k >= dates[0][:7]}
    return dates, px, vlm, meta, rf


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


def xsec(sid, name, rule, fn, why, arch=None):
    STRATS.append({"sid": sid, "name": name, "kind": "xsec", "rule": rule, "why": why, "fn": fn, "arch": arch})


# 펀더멘털이 필요한 전략들 — 점수 루프가 람다 대신 갈래로 처리한다(날짜·주식수·주가가 필요).
FUND_SIDS = {"x-btp", "x-fcfy", "x-ep", "x-sp", "x-roe", "x-npm",
             "x-rgrow", "x-lowde", "x-dy", "x-small"}


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


# ── 실행 ────────────────────────────────────────────────────────────────
def run():
    dates, px, vlm, meta, rf = load()
    FU = load_fund()          # 티커 → eq·sh·fcf 분기 시계열(시점 정합은 asof_fund가 맡는다)
    n = len(dates)
    tickers = sorted(px)
    R = daily_rets(px)
    me = set(month_ends(dates))

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
                    m = ema(ix, i, 12) - ema(ix, i, 26)
                    prev = ema(ix, i - 1, 12) - ema(ix, i - 1, 26) if i > 0 else m
                    sig = m * 0.2 + prev * 0.8
                    w[i] = 1.0 if m > sig else 0.0
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
            for i in range(MIN_HIST + 1, n):
                e = w[i - 1]
                r = e * ixr[i] + (1 - e) * rfd_d[i]
                srets.append(r)
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
            nav = [100.0]
            srets = []
            turns = 0
            first_i = None       # 실제로 무언가를 보유하기 시작한 시점
            for i in range(MIN_HIST + 1, n):
                # `or not hold` 를 붙여 두었었다. 후보가 비면 다음 월말까지 기다리지 않고
                # 매일 전 종목을 다시 채점한다 — 규칙이 스스로 내건 '월말 리밸런스'를 어기는
                # 데다, 펀더멘털이 늦게 채워지는 전략(x-roe 등)은 초기 수년간 매일 재채점해
                # 10년 구간에서 899회(월말이면 106회) 돌았다. 규약대로 월말에만 다시 뽑는다.
                # 결과: 첫 월말 전까지는 후보가 없으므로 현금이다(선견 없이 정직한 상태다).
                if (i - 1) in me:
                    sc = []
                    for t in tickers:
                        P = px[t]
                        sid = S["sid"]
                        if sid == "x-52wh":
                            # 종가가 통째로 비는 구간이 있는 종목이 있다(부분 상장 등) — 빈 창은 건너뛴다
                            win = [x for x in P[max(0, i - 252):i] if x]
                            hi = max(win) if win else None
                            v = (P[i - 1] / hi) if (hi and P[i - 1]) else None
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
                            elif sid == "x-fcfy":
                                fc = ttm(f.get("fcf"), dt_)
                                v = (fc / mcap) if (fc is not None and mcap) else None
                            elif sid == "x-ep":
                                ep_ = ttm(f.get("eps"), dt_)
                                v = (ep_ / p0) if (ep_ is not None and p0 and p0 > 0) else None
                            elif sid == "x-sp":
                                rv = ttm(f.get("rev"), dt_)
                                v = (rv / mcap) if (rv is not None and mcap) else None
                            elif sid == "x-roe":
                                nn, e = ttm(f.get("ni"), dt_), asof_fund(f.get("eq"), dt_)
                                v = (nn / e) if (nn is not None and e and e > 0) else None
                            elif sid == "x-npm":
                                nn, rv = ttm(f.get("ni"), dt_), ttm(f.get("rev"), dt_)
                                v = (nn / rv) if (nn is not None and rv and rv > 0) else None
                            elif sid == "x-rgrow":
                                a1, a0 = ttm(f.get("rev"), dt_), ttm(f.get("rev"), _shift(dt_, 365))
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
                                dp = ttm(f.get("dps"), dt_)
                                v = (dp / p0) if (dp is not None and p0 and p0 > 0) else None
                            elif sid == "x-small":
                                v = -mcap if mcap else None
                        elif sid == "x-ivol":
                            # 시장 수익이 필요해 람다(종목 하나만 받는다)로는 못 준다
                            iv = idio_vol(R[t], ixr, i - 1, 120)
                            v = -iv if iv is not None else None
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
                            if not V or not m200 or not P[i - 1] or P[i - 1] <= m200:
                                v = None
                            else:
                                a = sma(V, i - 1, 20)
                                b = sma(V, i - 1, 60)
                                v = (a / b) if (a and b and b > 0) else None
                        else:
                            v = S["fn"](t, i - 1, P, R[t], vol(R[t], i - 1, 60))
                        if v is not None and v == v:
                            sc.append((v, t))
                    sc.sort(reverse=True)
                    new = [t for _v, t in sc[:TOPN]]
                    if new:
                        turns += len(set(new) ^ set(hold)) / (2 * TOPN) if hold else 1.0
                        hold = new
                if hold and first_i is None:
                    first_i = i
                rs = [R[t][i] for t in hold if R[t][i] is not None]
                r = sum(rs) / len(rs) if rs else 0.0
                srets.append(r)
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
            d2 = d2[_k:]
        st = ann_stats(nav, d2, rf)
        bs = ann_stats(bnav, d2, rf)
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
            "turnover": round(turn, 2), "exposure": round(expo * 100, 1),
            "start": d2[0], "n_days": len(d2),
            "holdings": hold_now,
            "nav": [round(x, 2) for x in nav[::5]],
            "bnav": [round(x, 2) for x in bnav[::5]],
            "dates": d2[::5],
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
    # 사내 DB의 시점별 편입 이력으로 같은 구간(2020-09~2026-07)을 다시 돌려 재 보니
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
    PIT_MEASURED, PIT_WINDOW, PIT_BENCH = {}, None, None
    try:
        _pj = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
        PIT_WINDOW = "%s~%s" % (_pj["start"][:7], _pj["as_of"][:7])
        for _r in _pj.get("strategies") or []:
            _m, _b = _r.get("metrics") or {}, _r.get("bench") or {}
            # retro = **같은 창의 소급 레그**. 이것과의 차이가 유니버스 편향이다 —
            # 랩 본편(2252일)과 직접 빼면 구간 차이가 섞여 편향이 아니게 된다.
            _rt = _r.get("retro") or {}
            PIT_MEASURED[_r["sid"]] = (_m.get("cagr"), _m.get("sharpe"), _r.get("t"),
                                       _r.get("bias_excess"), _rt.get("excess_cagr"),
                                       _rt.get("t"), _r.get("bias_cagr"),
                                       (_rt.get("metrics") or {}).get("cagr"),
                                       _r.get("bench_bias_cagr"))
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
        pc, ps, pt, pbias, prx, prt, pbc, prc, pbb = m
        if pt is None:
            continue
        r["pit"] = {"window": PIT_WINDOW, "cagr": pc, "sharpe": ps, "t": pt,
                    "bench_cagr": PIT_BENCH, "excess_cagr": round(pc - PIT_BENCH, 2),
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
    # 실측이 없는 규칙에도 같은 편향이 걸려 있다. 특히 소형주 계열은 편출이 곧 '작아진 회사'라
    # 가장 세게 걸리는데, 시점별 재무·주식수가 없어 재지 못했다 — 침묵하지 말고 적어 둔다.
    for r in out:
        if r["sid"] in ("x-small", "x-btp") and r["verdict"] in ("통과 후보", "구별 불가"):
            r["why"] += (" ⚠ 이 규칙은 PIT 재측정 대상이 아니었다(시점별 재무·주식수 부재). "
                         "지수에서 빠지는 것이 대개 '작아진 회사'라 생존편향이 가장 세게 걸리는 "
                         "계열이므로, 여기 판정은 측정으로 뒷받침되지 않았다.")

    out.sort(key=lambda x: -(x["d_sharpe"] or -9))

    # ── 중복도 ──────────────────────────────────────────────────────────
    # 규칙을 늘리면 '더 많이 검증했다'는 착각이 생긴다. 하지만 24개 타이밍 규칙이 전부
    # 같은 지수 가격에서 나오면 서로 다른 베팅이 아니라 같은 베팅 24개다. 실제로 얼마나
    # 겹치는지 재서 그대로 싣는다 — 본페로니는 검정이 독립일 때의 보정이라, 겹칠수록
    # 필요 이상으로 보수적이 된다(임계를 낮추지는 않는다. 재량이 들어가는 순간 검정이 아니게 된다).
    def _rets(r):
        v = r.get("nav") or []
        return [v[i] / v[i - 1] - 1 for i in range(1, len(v))] if len(v) > 2 else []

    def _corr(a, b):
        if len(a) != len(b) or not a:
            return None
        m1, m2 = sum(a) / len(a), sum(b) / len(b)
        s1 = math.sqrt(sum((x - m1) ** 2 for x in a))
        s2 = math.sqrt(sum((y - m2) ** 2 for y in b))
        if not s1 or not s2:
            return None
        return sum((x - m1) * (y - m2) for x, y in zip(a, b)) / (s1 * s2)

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
    _pairs = []
    for _i in range(len(_tm)):
        for _j in range(_i + 1, len(_tm)):
            c = _corr(_rr[_tm[_i]["sid"]], _rr[_tm[_j]["sid"]])
            if c is not None:
                _pairs.append({"a": _tm[_i]["name"], "b": _tm[_j]["name"], "c": round(c, 3)})
    _pairs.sort(key=lambda x: -x["c"])
    _cs = sorted(x["c"] for x in _pairs)
    dup = {
        "n_timing": len(_tm),
        "median": round(_cs[len(_cs) // 2], 3) if _cs else None,
        "n_over_95": sum(1 for c in _cs if c >= 0.95),
        "top": _pairs[:6],
        "note": "타이밍 규칙끼리의 일간 수익률 상관. 0.95를 넘으면 이름만 다른 같은 베팅에 가깝다. "
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
        # ⚠ 전 구간 CAGR(2017-08~) 과 PIT CAGR(2020-09~) 을 빼면 안 된다. 그 차이의 상당 부분이
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
        ],
        "dup": dup, "regime": regime,
        "strategies": out,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
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
