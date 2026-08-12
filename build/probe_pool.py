# -*- coding: utf-8 -*-
"""build/probe_pool.py — 횡단면 규칙의 **월별 후보 수 시계열**을 낸다. 공용 프로브.

🚨 왜 이 파일이 생겼나 — 2026-08-12 에 내가 낸 사고 때문이다.
   `probe_batch12.py` 는 "rev·cogs 태그가 둘 다 있는 **파일** 수"를 세고 294종이라 적었다.
   백테스트가 묻는 것은 "그 **월말**에, 그때까지 공개된 자료로 채점 가능한 종목 수"다.
   2019 년부터 태그가 시작한 종목이 2012 년 후보로 셈됐고, 그래서 사전등록에 적은 커버리지가
   실제와 34배 어긋났다(x-sugp 실측: 2012-06 8종 → 2026-06 276종).
   결과: 그 규칙은 16.6년이 아니라 6.1년만 돌았는데 등록 문서는 그 사실을 몰랐다.
   → `build/PREREG-2026-08-12-INCOME-LINES-RESULT.md` §3 · `DATA-FACTS.md` #3

🚨 이 파일에는 **수익률 코드가 한 줄도 없다.** 후보 수만 센다.
   사전등록 규약: 재고 → 규칙을 확정해 커밋하고 → 그다음 돌린다.

⚠ 채점기를 두 벌 만들지 않는다. 월말 격자·재무 로드·신호 함수를 전부 tech_backtest 에서
  **import 해서 그대로** 쓴다. 여기서 다시 구현하면 프로브가 통과시킨 규칙이 백테스트에서
  다르게 도는 일이 생긴다.

사용:
    python build/probe_pool.py                 # 등록된 후보 전부
    python build/probe_pool.py x-sugp x-sur    # 골라서
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tech_backtest as TB           # noqa: E402  채점기는 여기 하나뿐이다


# ── 후보 신호들 ──────────────────────────────────────────────────────────
# 각 항목은 (이름, 함수(f, dt) → 값 or None). f 는 그 종목의 재무 묶음이다.
# 🚨 가격만 쓰는 규칙은 여기 넣지 않는다 — 가격은 518종 전부 4428일이 다 있어서
#   후보 램프 문제가 애초에 없다(그게 이 프로브가 답하는 질문이다).
CAND = {
    # 이미 등록·기각된 것들 — 이 프로브가 그때 있었으면 잡았을 것들이라 대조군으로 남긴다
    "x-sue":   lambda f, d: TB.sue(f.get("eps") or [], d),
    "x-sur":   lambda f, d: TB.sue(f.get("rev") or [], d),
    "x-sugp":  lambda f, d: TB.sue(TB.gp_series(f), d),
    "x-cdisc": lambda f, d: TB.cost_disc(f, d),
}


def sweep(fn, FU, dts):
    """월말마다 신호가 나오는 종목 수. [(YYYY-MM, n)]"""
    out = []
    for d in dts:
        n = 0
        for f in FU.values():
            try:
                if fn(f, d) is not None:
                    n += 1
            except Exception:
                pass
        out.append((d[:7], n))
    return out


def report(name, rows, floor):
    ns = [n for _m, n in rows]
    if not ns:
        print("  %-10s 후보 없음" % name); return
    srt = sorted(ns)
    med = srt[len(srt) // 2]
    thin = sum(1 for n in ns if n < floor)
    # 실제로 규칙이 '돌기 시작한' 달 — 문턱 이상이 처음 나온 지점
    first_ok = next((m for m, n in rows if n >= floor), None)
    print("  %-10s 중앙 %4d · 최소 %4d · 최대 %4d · **문턱(%d) 미만 %d/%d달** · 처음 도는 달 %s"
          % (name, med, srt[0], srt[-1], floor, thin, len(ns), first_ok or "없음"))
    # 램프 — 첫 관측 대비 마지막 관측이 몇 배인가. 이것이 1차 배치에서 놓친 바로 그 수치다.
    a = next((n for _m, n in rows if n > 0), 0)
    b = rows[-1][1] if rows else 0
    if a:
        flag = "  🚨 램프 %.0f배" % (b / a) if b >= a * 3 else ""
        print("             %s %d → %s %d%s" % (rows[0][0], rows[0][1], rows[-1][0], b, flag))
    print("             %s" % " ".join("%s:%d" % (m[2:], n) for m, n in rows[::max(1, len(rows)//12)]))


def main() -> int:
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or sorted(CAND)
    bad = [w for w in want if w not in CAND]
    if bad:
        raise SystemExit("모르는 후보: %s · 아는 것: %s" % (bad, sorted(CAND)))

    print("=" * 74)
    print("후보 풀 시계열 프로브 — 수익률 코드 없음 · 채점기는 tech_backtest 하나")
    print("=" * 74)
    FU = TB.load_fund()
    dates = TB.load_dates() if hasattr(TB, "load_dates") else None
    if not dates:
        S = json.load(io.open(os.path.join(HERE, "..", "data", "stocks.json"), encoding="utf-8"))
        dates = S["pxd_dates"]
    me = TB.month_ends(dates)
    dts = [dates[i] for i in me]
    floor = TB.XSEC_MIN_POOL
    print("월말 %d개 · %s ~ %s · 문턱 XSEC_MIN_POOL=%d · 재무 %d종"
          % (len(dts), dts[0], dts[-1], floor, len(FU)))
    print()
    for w in want:
        report(w, sweep(CAND[w], FU, dts), floor)
    print()
    print("⚠ '문턱 미만인 달'은 그 규칙이 **무보유**로 보내는 달이다. 그 달들은 창에서 빠지므로")
    print("  규칙의 실제 검정 기간은 위 '처음 도는 달' 부터다 — 등록 문서에 그 날짜를 적을 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
