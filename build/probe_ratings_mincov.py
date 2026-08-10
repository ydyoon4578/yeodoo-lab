# -*- coding: utf-8 -*-
"""최소 커버 문턱을 **구성으로만** 고른다 — 성과는 재지 않는다.

앞 프로브에서 나온 문제 — (상향−하향)÷커버 로 줄을 세우면 상위 10의 70%가 커버 최하위
25% 종목이었다(중립이면 25%). 분모가 작으면 이벤트 하나가 큰 값을 만들기 때문이다.
그러면 이 규칙이 사는 것은 '리비전이 강한 종목'이 아니라 '아무도 안 보는 종목'이다.

문턱을 어디서 끊나 — 세 값을 같이 본다. 셋은 서로 반대로 움직인다:
  · 후보 수      문턱을 올리면 준다. XSEC_MIN_POOL(30) 밑으로 가면 그 달은 무보유다.
  · 하위25%비율  문턱을 올리면 25%(중립)로 내려온다. 이게 고치려는 병이다.
  · 임의비율     문턱을 올리면 는다. 후보가 줄면 동점이 상대적으로 커진다.

🚨 성과로 고르지 않는다. 이 파일에도 수익률이 없다.
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
D, FS, TS, AC, P0, P1 = 0, 1, 2, 3, 4, 5
UP, DOWN = 1, 2
MINS = [0, 4, 8, 12, 16, 24]
WINS = [(21, 30), (63, 91), (126, 182)]


def main():
    import datetime as dt
    j = json.load(io.open(CACHE, encoding="utf-8"))
    rows = j["rows"]
    ep = dt.date(1970, 1, 1)
    ends, y, m = [], 2017, 8
    while (y, m) <= (2026, 7):
        nx = dt.date(y + (m == 12), (m % 12) + 1, 1)
        ends.append(nx - dt.timedelta(days=1))
        y, m = (y + (m == 12), (m % 12) + 1)

    # 12개월 커버 수와 창별 순계를 월말마다 한 번만 만든다(문턱 6개를 다시 돌지 않게)
    print("월말 %d회 · 종목 %d — 사전집계 중" % (len(ends), len(rows)))
    snap = []
    for e in ends:
        de = (e - ep).days
        cur = []
        for t, evs in rows.items():
            ncov = 0
            nets = [0] * len(WINS)
            for x in evs:
                d = x[D]
                if d > de or d < de - 365:
                    continue
                ncov += 1
                if x[AC] in (UP, DOWN):
                    s = 1 if x[AC] == UP else -1
                    for k, (_bd, cd) in enumerate(WINS):
                        if d > de - cd:
                            nets[k] += s
            if ncov:
                cur.append((ncov, nets))
        snap.append(cur)

    print()
    print("%-6s %-6s %8s %9s %9s %9s" %
          ("창", "최소커버", "후보수", "하위25%", "임의비율", "무보유월"))
    print("-" * 52)
    md = lambda a: sorted(a)[len(a) // 2] if a else 0
    for k, (bd, _cd) in enumerate(WINS):
        for mn in MINS:
            pool, thin, arb, none_m = [], [], [], 0
            for cur in snap:
                cand = [(nets[k] / float(ncov), ncov) for ncov, nets in cur if ncov >= mn]
                if len(cand) < 30:
                    none_m += 1                      # XSEC_MIN_POOL 가드에 걸리는 달
                if len(cand) < 10:
                    continue
                pool.append(len(cand))
                cand.sort(key=lambda x: -x[0])
                covs = sorted(c for _v, c in cand)
                q1 = covs[len(covs) // 4]
                top = cand[:10]
                thin.append(100.0 * sum(1 for _v, c in top if c <= q1) / 10.0)
                cut = top[-1][0]
                nab = sum(1 for v, _c in cand if v > cut)
                nti = sum(1 for v, _c in cand if v == cut)
                arb.append(100.0 * max(0, 10 - nab) / 10.0 if nti > 1 else 0.0)
            print("%-6s %-8d %8d %8.0f%% %8.0f%% %9d"
                  % ("%d일" % bd, mn, md(pool), md(thin), md(arb), none_m))
        print()
    print("고르는 법 — 하위25%가 25 근처로 내려오면서 후보가 30 밑으로 안 가는 가장 낮은 문턱.")
    print("⚠ 위에 성과는 없다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
