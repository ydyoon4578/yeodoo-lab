# -*- coding: utf-8 -*-
"""build/probe_moments.py — 3차 후보의 밀도 **와 PIT 가능 여부**를 잰다(2026-08-12).

🚨 수익률 코드가 한 줄도 없다. 재고 → 확정해 커밋하고 → 그다음 돌린다.

🚨 2차 배치(LIQ-CAL)의 실패를 되풀이하지 않는다.
   그때는 후보 밀도를 월별로 제대로 쟀는데(1차의 교훈) **PIT 가능 여부를 안 쟀다.**
   그래서 x-amihud 가 ⓐⓑ를 다 통과하고 나서야 "거래량이 편출 종목에 없어 PIT 을 못 잰다"는
   사실이 드러났다 — 등록 문서가 그것을 모른 채 게시 기준에 'PIT 통과'를 적어 두었다.
   → 이 프로브는 **밀도와 PIT 가능 여부를 함께** 낸다. 항목이 하나 늘었다.

PIT 가능 판정 규약(build/pit_backtest.py 의 실제 제약과 같아야 한다):
   ✅ 가능   종가만 쓴다 — 편출 종목도 yfinance 로 받아 두었다(data/_pit_px_cache.json)
   ⚠ 조건부 고가·저가를 쓴다 — data/_pit_hl_cache.json 이 있을 때만
   ❌ 불가   거래량·시점별 재무·투자의견을 쓴다 — 원천이 생존자만 준다

  python build/probe_moments.py
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tech_backtest as TB          # 채점기는 여기 하나뿐이다


# (이름, 입력 종류, 신호 함수). 입력 종류가 곧 PIT 가능 여부를 정한다.
CAND = [
    ("x-mommvol", "종가만", lambda P, Rt, i: TB.mom_vol_scaled(P, Rt, i)),
    ("x-rskew",   "종가만", lambda P, Rt, i: TB.realized_skew(Rt, i)),
]

PIT_OK = {"종가만": "✅ 가능 (편출 종목 종가 캐시 있음)",
          "고가·저가": "⚠ 조건부 (_pit_hl_cache.json 유무)",
          "거래량": "❌ 불가 (원천이 생존자만 준다 — x-volsurge·x-amihud 와 같은 벽)",
          "시점별 재무": "❌ 불가",
          "투자의견": "❌ 불가 (보완 불가)"}


def main() -> int:
    print("=" * 76)
    print("3차 후보 프로브 — 밀도 + PIT 가능 여부 · 수익률 코드 없음")
    print("=" * 76)
    dates, px, vlm, hi, lo, meta, rf = TB.load()[:7]
    R = TB.daily_rets(px)
    me = TB.month_ends(dates)
    floor = TB.XSEC_MIN_POOL
    print("월말 %d개 · %s ~ %s · 문턱 %d · 종목 %d"
          % (len(me), dates[me[0]], dates[me[-1]], floor, len(px)))
    hl = os.path.exists(os.path.join(HERE, "..", "data", "_pit_hl_cache.json"))
    pxc = os.path.exists(os.path.join(HERE, "..", "data", "_pit_px_cache.json"))
    print("PIT 캐시 — 종가 %s · 고저 %s" % ("있음" if pxc else "없음", "있음" if hl else "없음"))
    print()

    for nm, kind, fn in CAND:
        rows = []
        for k in me:
            n = 0
            for t, P in px.items():
                Rt = R.get(t)
                if not Rt:
                    continue
                try:
                    if fn(P, Rt, k) is not None:
                        n += 1
                except Exception:
                    pass
            rows.append((dates[k][:7], n))
        ns = [n for _m, n in rows]
        srt = sorted(ns)
        thin = sum(1 for n in ns if n < floor)
        first_ok = next((m for m, n in rows if n >= floor), None)
        a = next((n for _m, n in rows if n > 0), 0)
        b = rows[-1][1]
        print("  %-11s 입력 %-6s → PIT %s" % (nm, kind, PIT_OK[kind]))
        print("              중앙 %4d · 최소 %4d · 최대 %4d · 문턱 미만 %d/%d달 · 처음 도는 달 %s"
              % (srt[len(srt)//2], srt[0], srt[-1], thin, len(ns), first_ok))
        print("              %s %d → %s %d%s" % (rows[0][0], rows[0][1], rows[-1][0], b,
              ("   🚨 램프 %.0f배" % (b / a)) if a and b >= a * 3 else "   (램프 없음)"))
        print("              %s" % " ".join("%s:%d" % (m[2:], n)
                                            for m, n in rows[::max(1, len(rows)//10)]))
        print()
    print("⚠ PIT '가능'은 **레그를 돌릴 수 있다**는 뜻이지 통과한다는 뜻이 아니다.")
    print("  2차의 교훈은 '못 재는 규칙을 등록하지 말 것'이지 '재면 통과한다'가 아니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
