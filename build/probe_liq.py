# -*- coding: utf-8 -*-
"""build/probe_liq.py — 유동성 수준 두 축 + 월말 효과의 **후보 밀도만** 잰다(2026-08-12).

🚨 수익률 코드가 한 줄도 없다. 재고 → 확정해 커밋하고 → 그다음 돌린다.
🚨 1차 배치(INCOME-LINES)에서 낸 사고를 되풀이하지 않는다 — **한 시점이 아니라 월별
   시계열로** 센다. 그 사고: 한 시점 커버 294종이라 적었는데 이력 중앙은 19종이었다.

재는 것:
  x-amihud  Amihud(2002) 비유동성   |일간수익률| ÷ 거래대금   ← px·vd 만 쓴다(램프 없어야 정상)
  x-turn    저회전율               거래량 ÷ 주식수          ← **sh 를 쓰므로 램프 위험 있다**
  t-tom     월말 효과              달력만                  ← 노출 비율만 본다

  python build/probe_liq.py
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tech_backtest as TB          # 채점기는 여기 하나뿐이다


AM_WIN = 60          # Amihud 평균 창(거래일). 원논문은 연 단위지만 이 랩의 다른 규칙과 맞춘다
TURN_WIN = 60


def amihud(P, V, i, win=AM_WIN):
    """|일간수익률| ÷ 거래대금(달러)의 win 일 평균. 클수록 비유동적.

    Amihud(2002). 거래대금이 0 인 날은 버린다 — 0 으로 나누면 무한이 된다.
    ⚠ 유효일이 창의 80% 미만이면 None(이 랩의 sma 규약과 같다).
    """
    if i < win:
        return None
    xs = []
    for j in range(i - win + 1, i + 1):
        a, b, v = P[j - 1], P[j], V[j]
        if not (a and b and v and a > 0 and v > 0):
            continue
        xs.append(abs(b / a - 1.0) / (v * b))
    return (sum(xs) / len(xs)) if len(xs) >= win * 0.8 else None


def turnover(V, sh, i, win=TURN_WIN):
    """거래량 ÷ 발행주식수의 win 일 평균. 작을수록 저회전."""
    if i < win or not sh or sh <= 0:
        return None
    xs = [V[j] for j in range(i - win + 1, i + 1) if V[j]]
    return (sum(xs) / len(xs) / sh) if len(xs) >= win * 0.8 else None


def main() -> int:
    print("=" * 74)
    print("유동성·달력 후보 프로브 — 수익률 코드 없음 · 월별 시계열")
    print("=" * 74)
    dates, px, vlm, hi, lo, meta, rf = TB.load()[:7]
    FU = TB.load_fund()
    me = TB.month_ends(dates)
    floor = TB.XSEC_MIN_POOL
    print("월말 %d개 · %s ~ %s · 문턱 %d · 종목 %d"
          % (len(me), dates[me[0]], dates[me[-1]], floor, len(px)))
    print()

    rows_a, rows_t = [], []
    for k in me:
        na = nt = 0
        for t, P in px.items():
            V = vlm.get(t)
            if not V:
                continue
            if amihud(P, V, k) is not None:
                na += 1
            sn = TB.asof_fund((FU.get(t) or {}).get("sh"), dates[k])
            if turnover(V, sn, k) is not None:
                nt += 1
        rows_a.append((dates[k][:7], na))
        rows_t.append((dates[k][:7], nt))

    for nm, rows in (("x-amihud", rows_a), ("x-turn", rows_t)):
        ns = [n for _m, n in rows]
        srt = sorted(ns)
        thin = sum(1 for n in ns if n < floor)
        first_ok = next((m for m, n in rows if n >= floor), None)
        a = next((n for _m, n in rows if n > 0), 0)
        b = rows[-1][1]
        print("  %-9s 중앙 %4d · 최소 %4d · 최대 %4d · 문턱 미만 %d/%d달 · 처음 도는 달 %s"
              % (nm, srt[len(srt)//2], srt[0], srt[-1], thin, len(ns), first_ok))
        print("            %s %d → %s %d%s" % (rows[0][0], rows[0][1], rows[-1][0], b,
              ("   🚨 램프 %.0f배" % (b / a)) if a and b >= a * 3 else "   (램프 없음)"))
        print("            %s" % " ".join("%s:%d" % (m[2:], n) for m, n in rows[::max(1, len(rows)//12)]))
        print()

    # t-tom — 달력만 쓰므로 후보가 아니라 **노출 비율**이 관건이다
    n = len(dates)
    mset = set(me)
    win = [False] * n
    for k in me:
        win[k] = True                       # 월 마지막 거래일
        for d in range(1, 4):               # 다음 달 첫 3거래일
            if k + d < n:
                win[k + d] = True
    expo = sum(1 for x in win if x) / n
    print("  t-tom     창 = 월 마지막 거래일 + 다음 달 첫 3거래일")
    print("            노출 %.1f%% (거래일 %d/%d) — 나머지는 현금"
          % (100 * expo, sum(1 for x in win if x), n))
    print("            ⚠ vs_traded(동일가중 매수후보유) 대비로 판정되므로, 노출 %.0f%% 로 "
          "매수후보유를" % (100 * expo))
    print("               **따라잡으면** 그것이 이 규칙의 주장이다(McConnell·Xu 2008).")
    print("            ⚠ 달력은 미리 공표되므로 다음 거래일이 창인지 아는 것은 선견이 아니다.")
    print("               가정은 '예정에 없던 휴장이 없다' 하나다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
