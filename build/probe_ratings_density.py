# -*- coding: utf-8 -*-
"""등급 리비전 신호가 **월말에 순위를 만들 만큼 두꺼운가**만 잰다 — 성과는 재지 않는다.

왜 이걸 먼저 재나 — 60종목 표본에서 방향 전환(up/down)은 전체 이벤트의 17%뿐이었다
(main 이 74%). 종목당 연 4건꼴이면 21영업일 창에서는 대부분의 종목이 0이 된다.
그러면 상위 10 을 고르는 것이 순위가 아니라 **동점 뭉치에서 아무거나 집는 일**이 된다.
이 랩에는 이미 같은 사고가 있었다(x-agrow — 후보가 3~7종이라 sc[:TOPN] 이 전량 통과).

🚨 여기서 고르는 것은 창 길이(W)와 신호 정의다. 그 선택은 **밀도로만** 한다.
  성과를 보고 W 를 고르면 그건 사전등록이 아니라 사후 맞춤이다. 그래서 이 파일에는
  수익률이 한 줄도 없다.

재는 것 —
  ① 커버 종목 수: 최근 12개월에 이벤트가 하나라도 있는 종목
  ② 비영 비율: 신호가 0이 아닌 종목 비율 (동점 뭉치의 크기)
  ③ 상위 동점: 최댓값을 공유하는 종목 수. 10보다 크면 바스켓이 임의로 정해진다
  ④ 세 가지 신호 정의를 나란히 — 등급방향 / 등급점수차 / 목표주가
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
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "_ratings_cache.json")

# 행 = [일자, From점수, To점수, 액션코드, 목표주가전, 목표주가후]
D, FS, TS, AC, P0, P1 = 0, 1, 2, 3, 4, 5
UP, DOWN, INIT, MAIN, REIT = 1, 2, 3, 4, 5


def sig_dir(evs):
    """① 등급 방향 — Action 이 up/down 인 건만 ±1. E21 카드의 정의에 가장 가깝다."""
    n = 0
    for e in evs:
        if e[AC] == UP:
            n += 1
        elif e[AC] == DOWN:
            n -= 1
    return n


def sig_delta(evs):
    """② 등급 점수차 — From·To 를 5→1 척도로 옮겨 차를 더한다. 2단계 상향을 1로 세지 않는다.
    ⚠ From 이 비면(초기 커버리지 등) 이 건은 못 센다. 표본에서 등급칸의 21%가 빈칸이었다."""
    s = 0.0
    for e in evs:
        if e[FS] is not None and e[TS] is not None:
            s += (e[TS] - e[FS])
    return s


def sig_pt(evs):
    """③ 목표주가 — 올렸으면 +, 내렸으면 −. Action=main(유지) 도 목표주가는 자주 움직이므로
    이쪽이 훨씬 두껍다. 다만 이건 '등급 리비전'이 아니라 다른 신호다 — 섞지 않고 따로 센다."""
    n = 0
    for e in evs:
        a, b = e[P0], e[P1]
        if a and b:
            if b > a * 1.001:
                n += 1
            elif b < a * 0.999:
                n -= 1
    return n


# ── 커버 수로 나눈 판 ─────────────────────────────────────────────
# 🚨 E21 카드의 정의는 순계가 아니라 **(상향 − 하향) ÷ 커버 수**다. 처음 잰 판은 이 분모를
#   빠뜨렸고, 그래서 신호가 작은 정수(…−1, 0, 1, 2…)가 되어 10위 경계에 39종이 몰렸다.
#   분모를 넣으면 값이 연속이 되어 동점이 흩어진다. 이건 동점을 피하려는 잔꾀가 아니라
#   원래 정의로 돌아가는 것이다 — 애널리스트 20명이 보는 종목의 +1 과 3명이 보는 종목의
#   +1 은 같은 소식이 아니다.
def _mk_norm(fn):
    def g(evs, ncov):
        v = fn(evs)
        return (v / ncov) if ncov else None
    return g


SIGS = [("등급방향", sig_dir), ("등급점수차", sig_delta), ("목표주가", sig_pt)]
NSIGS = [("등급방향÷커버", _mk_norm(sig_dir)),
         ("등급점수차÷커버", _mk_norm(sig_delta)),
         ("목표주가÷커버", _mk_norm(sig_pt))]
WINS = [(21, 30), (63, 91), (126, 182)]        # (영업일 이름, 실제 달력일)


def main():
    import datetime as dt
    if not os.path.exists(CACHE):
        print("캐시가 없다 — build/fetch_ratings.py 를 먼저 돌린다.")
        return 1
    j = json.load(io.open(CACHE, encoding="utf-8"))
    rows = j["rows"]
    ep = dt.date(1970, 1, 1)

    # 월말 목록 — 이 랩의 종목 백테스트 구간(2017-08~)에 맞춘다
    ends = []
    y, m = 2017, 8
    while (y, m) <= (2026, 7):
        nx = dt.date(y + (m == 12), (m % 12) + 1, 1)
        ends.append((nx - dt.timedelta(days=1)))
        y, m = (y + (m == 12), (m % 12) + 1)

    print("종목 %d · 월말 %d회 (%s ~ %s)"
          % (len(rows), len(ends), ends[0], ends[-1]))
    print()
    # 🚨 동점은 **최댓값이 아니라 10위 경계**에서 본다. 1등이 유일해도 10위 값을 20종이
    #   공유하면 바스켓의 나머지 자리는 순위가 아니라 정렬 순서(=티커 알파벳)가 정한다.
    print("%-12s %-6s %8s %8s %9s %9s %9s" %
          ("신호", "창", "커버종목", "비영비율", "10위값", "경계동점", "임의비율"))
    print("-" * 66)

    for nm, fn in SIGS + NSIGS:
        norm = any(nm == x[0] for x in NSIGS)
        for bd, cd in WINS:
            cov_l, nz_l, cut_l, tie_l, arb_l = [], [], [], [], []
            for e in ends:
                de = (e - ep).days
                lo = de - cd
                cov = nzn = 0
                vals = []
                for t, evs in rows.items():
                    # 커버 판정 — 최근 12개월에 이벤트가 있어야 '애널리스트가 보는 종목'이다.
                    #   커버 수는 그 12개월에 이 종목을 건드린 **서로 다른 증권사 수**가 아니라
                    #   이벤트 건수로 센다 — 캐시에 증권사명을 담지 않았다. 둘은 비례하고,
                    #   여기서 재는 것은 동점 여부지 수준이 아니다.
                    recent = [x for x in evs if de - 365 <= x[D] <= de]
                    if not recent:
                        continue
                    cov += 1
                    win = [x for x in evs if lo < x[D] <= de]
                    v = fn(win, len(recent)) if norm else fn(win)
                    if v is None:
                        continue
                    vals.append(v)
                    if v:
                        nzn += 1
                if len(vals) < 10:
                    continue
                if cov < 5:
                    continue
                cov_l.append(cov)
                nz_l.append(100.0 * nzn / cov)
                # 10위 경계 — 그 값을 몇 종이 공유하나. 자리는 10인데 동점자가 더 많으면
                # 초과분은 무엇으로도 가릴 수 없다(그 자리는 정렬 순서가 정한다).
                sv = sorted(vals, reverse=True)
                cut = sv[9] if len(sv) >= 10 else sv[-1]
                nabove = sum(1 for v in vals if v > cut)     # 확실히 들어가는 종목
                ntie = sum(1 for v in vals if v == cut)      # 경계 동점자
                cut_l.append(cut)
                tie_l.append(ntie)
                arb_l.append(100.0 * max(0, 10 - nabove) / 10.0 if ntie > 1 else 0.0)
            if not cov_l:
                continue
            md = lambda a: sorted(a)[len(a) // 2]
            print("%-12s %-6s %8d %7.0f%% %9.1f %9d %8.0f%%"
                  % (nm, "%d일" % bd, md(cov_l), md(nz_l),
                     md(cut_l), md(tie_l), md(arb_l)))

    print()
    print("읽는 법 — '임의비율'은 상위 10 자리 중 **동점이라 순위로 못 가리는 자리**의 비율이다.")
    print("           0%면 10자리가 다 순위로 정해진다. 50%면 절반이 정렬 순서로 채워진다.")

    # ── 비율 신호가 '얇게 커버되는 종목'만 뽑는지 ────────────────────────
    # 🚨 분모로 나누면 동점은 풀리지만 대신 **분모가 작은 종목이 위로 온다**(1/3=0.33 이
    #   3/25=0.12 를 이긴다). 그러면 이 규칙은 리비전이 아니라 '커버가 얇음'을 사는 것이 된다.
    #   최소 커버 필터를 걸지 말지는 여기서 정한다 — 성과가 아니라 구성으로.
    print()
    print("── 상위 10의 커버 두께 (분모가 작은 종목만 뽑히나) ──")
    print("%-16s %-6s %10s %10s %8s" % ("신호", "창", "상위10커버", "유니버스", "하위25%비율"))
    print("-" * 56)
    for nm, fn in NSIGS:
        for bd, cd in WINS:
            top_c, uni_c, thin_share = [], [], []
            for e in ends:
                de = (e - ep).days
                lo = de - cd
                cand = []
                for t, evs in rows.items():
                    recent = [x for x in evs if de - 365 <= x[D] <= de]
                    if not recent:
                        continue
                    v = fn([x for x in evs if lo < x[D] <= de], len(recent))
                    if v is not None:
                        cand.append((v, len(recent)))
                if len(cand) < 10:
                    continue
                cand.sort(key=lambda x: -x[0])
                covs = sorted(c for _v, c in cand)
                q1 = covs[len(covs) // 4]           # 유니버스 커버 하위 25% 경계
                top = [c for _v, c in cand[:10]]
                top_c.append(sorted(top)[len(top) // 2])
                uni_c.append(covs[len(covs) // 2])
                thin_share.append(100.0 * sum(1 for c in top if c <= q1) / 10.0)
            if not top_c:
                continue
            md = lambda a: sorted(a)[len(a) // 2]
            print("%-16s %-6s %10d %10d %7.0f%%"
                  % (nm, "%d일" % bd, md(top_c), md(uni_c), md(thin_share)))
    print()
    print("'하위25%비율' — 상위 10 중 커버가 유니버스 하위 25%인 종목의 비율. 25%면 중립,")
    print("그보다 크게 높으면 이 규칙은 리비전이 아니라 '얇게 커버됨'을 사고 있는 것이다.")
    print("⚠ 위에 성과는 없다. 창과 신호 정의는 밀도로만 고른다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
