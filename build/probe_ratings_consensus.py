# -*- coding: utf-8 -*-
"""컨센서스 평균등급의 **변화**를 신호로 썼을 때의 밀도·커버중립성만 잰다 — 성과는 재지 않는다.

앞의 두 프로브가 버린 것과 왜 —
  · (상향−하향) 순계        정수라 10위 경계에 39종이 몰렸다. 바스켓 40%가 알파벳 순서.
  · (상향−하향)÷커버        동점은 풀렸으나 상위 10의 70%가 커버 최하위 25% 종목이었다
                           (중립 25%). 최소 커버 문턱 24까지 올려도 40~50%였다.

여기서 재는 것 — 증권사별 최신 등급을 이어 붙여(carry-forward) 그 시점의 평균등급을 만들고,
W일 전 평균등급과의 차를 신호로 쓴다. 이러면
  · 값이 연속이다(15~25개 수의 평균) → 동점이 없다
  · 25명이 보는 종목에서 한 명의 변경은 자연히 작게 들어간다 → 분모 편향이 없다
  · '리비전'의 표준 측정이다 — 건수가 아니라 의견 수준이 어디로 움직였나

carry-forward 규약 — 한 증권사의 등급은 마지막 발표일로부터 **12개월**까지만 유효하다.
  그 뒤로 소식이 없으면 커버를 접은 것으로 보고 평균에서 뺀다. 무한히 끌면 2013년에
  Buy 를 낸 뒤 사라진 증권사가 2026년 평균에 남는다.
  ⚠ 이 12개월은 성과를 보고 고른 값이 아니라 시작 전에 정한 값이다.

🚨 이 파일에도 수익률이 없다.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
CACHE = os.path.join(DATA, "_ratings_cache.json")
D, FS, TS, AC, P0, P1, FM = 0, 1, 2, 3, 4, 5, 6
STALE = 365          # 증권사 등급 유효기간(일)
WINS = [21, 63, 126]
CD = {21: 30, 63: 91, 126: 182}


def consensus(evs, asof):
    """asof 시점의 (평균등급, 증권사 수). 증권사별 마지막 유효 등급의 단순평균."""
    last = {}
    for x in evs:
        if x[D] > asof or x[D] < asof - STALE:
            continue
        s = x[TS]
        if s is None:
            continue
        f = x[FM]
        if f not in last or x[D] >= last[f][0]:
            last[f] = (x[D], s)
    if not last:
        return None, 0
    v = [s for _d, s in last.values()]
    return sum(v) / float(len(v)), len(v)


def xsec_resid(rows):
    """횡단면 OLS 잔차 — tech_backtest.xsec_resid 와 같은 식(여기선 캐시만 읽으므로 복제)."""
    if len(rows) < 2:
        return {}
    xs = [r[2] for r in rows]
    ys = [r[1] for r in rows]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx) if sxx > 0 else 0.0
    a = my - b * mx
    return {rows[i][0]: ys[i] - (a + b * xs[i]) for i in range(len(rows))}


def main():
    import datetime as dt
    import math
    j = json.load(io.open(CACHE, encoding="utf-8"))
    rows = j["rows"]
    ep = dt.date(1970, 1, 1)
    ends, y, m = [], 2017, 8
    while (y, m) <= (2026, 7):
        nx = dt.date(y + (m == 12), (m % 12) + 1, 1)
        ends.append(nx - dt.timedelta(days=1))
        y, m = (y + (m == 12), (m % 12) + 1)

    print("월말 %d회 · 종목 %d · 증권사 %d" % (len(ends), len(rows), len(j.get("firms") or [])))
    print()
    print("%-6s %-6s %8s %9s %9s %9s %9s %9s" %
          ("창", "중립화", "후보수", "증권사중앙", "비영비율", "임의비율", "하위25%", "무보유월"))
    print("-" * 72)
    md = lambda a: sorted(a)[len(a) // 2] if a else 0

    # 중립화 방식 넷을 나란히 본다.
    #   원값   Δ평균등급 그대로
    #   잔차   log(커버)에 OLS 잔차 — 이 랩의 관용구지만 **조건부 평균만** 걷어낸다
    #   √n     Δ×√커버 — 편향이 분산에 있으므로(Var∝1/n) 분산을 맞춘다. 이론적 교정
    #   분위z   커버 5분위 안에서 z점수 — 이론 대신 실측 분포로 맞춘다
    for W in WINS:
      for RESID in ("원값", "잔차", "√n", "분위z"):
        cd = CD[W]
        pool, nfm, nz, arb, thin, none_m = [], [], [], [], [], 0
        for e in ends:
            de = (e - ep).days
            cand = []
            for t, evs in rows.items():
                c1, n1 = consensus(evs, de)
                c0, n0 = consensus(evs, de - cd)
                # 양쪽 시점 모두 커버가 있어야 '변했다'고 말할 수 있다. 한쪽이 비면
                # 그건 리비전이 아니라 커버 개시/중단이다 — 다른 사건이므로 뺀다.
                if c1 is None or c0 is None:
                    continue
                cand.append((c1 - c0, n1))
            # 🚨 커버 중립화 — n개의 평균은 흩어짐이 1/√n 이라, 어떤 정의를 쓰든
            #   극단값이 커버 얇은 종목에서 나온다.
            if len(cand) >= 2 and RESID == "잔차":
                rr = xsec_resid([(k, v, math.log(n)) for k, (v, n) in enumerate(cand)])
                cand = [(rr[k], cand[k][1]) for k in range(len(cand))]
            elif RESID == "√n":
                cand = [(v * math.sqrt(n), n) for v, n in cand]
            elif RESID == "분위z" and len(cand) >= 25:
                # 커버 5분위로 나눠 각 분위 안에서 (값−평균)÷표준편차. 분위마다 흩어짐이
                # 다르다는 것을 이론으로 가정하지 않고 그 달 실측으로 맞춘다.
                order = sorted(range(len(cand)), key=lambda k: cand[k][1])
                q = max(1, len(order) // 5)
                out = [None] * len(cand)
                for b in range(0, len(order), q):
                    idx = order[b:b + q]
                    if len(idx) < 2:
                        idx = order[max(0, b - q):b + q]
                    vs = [cand[k][0] for k in idx]
                    mu = sum(vs) / len(vs)
                    sd = (sum((x - mu) ** 2 for x in vs) / len(vs)) ** 0.5
                    for k in order[b:b + q]:
                        out[k] = ((cand[k][0] - mu) / sd) if sd > 0 else 0.0
                cand = [(out[k] if out[k] is not None else 0.0, cand[k][1])
                        for k in range(len(cand))]
            if len(cand) < 30:
                none_m += 1
            if len(cand) < 10:
                continue
            pool.append(len(cand))
            nfm.append(md([n for _v, n in cand]))
            nz.append(100.0 * sum(1 for v, _n in cand if abs(v) > 1e-12) / len(cand))
            cand.sort(key=lambda x: -x[0])
            covs = sorted(n for _v, n in cand)
            q1 = covs[len(covs) // 4]
            top = cand[:10]
            thin.append(100.0 * sum(1 for _v, n in top if n <= q1) / 10.0)
            cut = top[-1][0]
            nab = sum(1 for v, _n in cand if v > cut)
            nti = sum(1 for v, _n in cand if v == cut)
            arb.append(100.0 * max(0, 10 - nab) / 10.0 if nti > 1 else 0.0)
        print("%-6s %-6s %8d %9d %8.0f%% %8.0f%% %8.0f%% %9d"
              % ("%d일" % W, RESID,
                 md(pool), md(nfm), md(nz), md(arb), md(thin), none_m))
      print()

    print()
    print("비교 — 앞 프로브의 (상향−하향)÷커버 는 임의비율 10% · 하위25% 70% 였다.")
    print("       하위25%가 25 근처면 커버 두께에 중립이라는 뜻이다.")
    print("⚠ 위에 성과는 없다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
