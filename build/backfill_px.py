# -*- coding: utf-8 -*-
r"""data/sd/<티커>.json 의 **최근 며칠 빈 칸만** 메운다 — 타깃 백필.

왜 필요한가. 2026-08-12 실측: 격자의 2026-08-11 칸이 **29종에서 비어 있었다**(IQV·PSX·
ABBV·GEHC …). 그날 하루만 비고 그 전후는 멀쩡하다 — yfinance 부분 응답이다. 그런데 홈
히트맵의 기본 기간이 '1일 등락'이라 그 29칸이 통째로 색이 안 칠해진다.

🚨 이 사고가 **조용했다**는 것이 본체다. 갱신 잡은 성공으로 끝났고, 화면은 "518종목"이라
  적으면서 489칸만 칠했다. 그래서 이 스크립트와 함께 두 가지를 더 넣었다 —
  build/home_summary.py 가 결측을 세어 산출물에 싣고, index.html 이 그 수를 부제에 적는다.

무엇을 하나.
  · stocks.json 의 pxd_dates 격자에 대고 각 종목의 최근 N일(기본 10) 빈 칸을 찾는다.
  · 걸린 종목만 yfinance 에서 그 구간을 다시 받아 **빈 칸에만** 써 넣는다.
  · 이미 값이 있는 칸은 절대 건드리지 않는다(재조정으로 과거가 흔들리는 것을 막는다).

🚨 안전장치 — 받아온 종가를 이미 저장된 pxd 와 대조한다. 겹치는 관측 3개 이상에서
  상대오차가 1% 를 넘으면 **그 종목은 건드리지 않고 보고만 한다.** 티커 매핑이 어긋나거나
  (BRK.B → BRK-B) 분할·배당 조정 기준이 다르면 남의 종목 가격을 붙이는 사고가 되기 때문이다.
  backfill_hl.py 가 같은 사유로 같은 방어를 갖고 있다.

  python build/backfill_px.py              # 최근 10일
  python build/backfill_px.py --days 20    # 창 늘리기
  python build/backfill_px.py --dry        # 무엇을 채울지만 보고 쓰지 않는다
"""
from __future__ import annotations

import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SD = os.path.join(DATA, "sd")
FIELDS = (("pxd", "Close"), ("hd", "High"), ("ld", "Low"), ("vd", "Volume"))
TOL = 0.01          # 겹치는 종가의 허용 상대오차 — 넘으면 그 종목은 건드리지 않는다
MIN_OVERLAP = 3     # 대조에 쓸 최소 관측 수


def _yf_sym(t):
    """지수 표기 → yfinance 표기. 클래스주는 점이 아니라 하이픈이다(BRK.B → BRK-B).
    ⚠ refresh_stocks._yf_sym 과 같은 규칙이어야 한다 — 갈리면 남의 종목을 받는다."""
    return t.replace(".", "-")


def main() -> int:
    days = 10
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    dry = "--dry" in sys.argv

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    n = len(dates)
    lo = max(0, n - days)
    win = dates[lo:]

    # ── 어디가 비었나 ─────────────────────────────────────────────────
    todo = {}
    for s in st["stocks"]:
        t = s["t"]
        p = os.path.join(SD, t + ".json")
        if not os.path.exists(p):
            continue
        j = json.load(io.open(p, encoding="utf-8"))
        a = j.get("pxd") or []
        if len(a) != n:
            continue
        miss = [dates[i] for i in range(lo, n) if a[i] is None]
        if miss:
            todo[t] = miss
    if not todo:
        print("최근 %d일에 빈 칸 없음 — 채울 것이 없다." % days)
        return 0
    tot = sum(len(v) for v in todo.values())
    print("빈 칸 %d개 · %d종목 (창 %s ~ %s)" % (tot, len(todo), win[0], win[-1]))
    by_date = {}
    for t, ms in todo.items():
        for d in ms:
            by_date.setdefault(d, []).append(t)
    for d in sorted(by_date):
        v = by_date[d]
        print("  %s  %3d종  %s" % (d, len(v), " ".join(sorted(v)[:12]) + (" …" if len(v) > 12 else "")))
    if dry:
        print("\n--dry — 쓰지 않고 끝낸다.")
        return 0

    import pandas as pd            # noqa: F401  (yfinance 가 요구한다)
    import yfinance as yf

    start = win[0]
    end_d = dates[-1]
    filled = skipped = failed = 0
    fill_by_date = {}
    for t in sorted(todo):
        p = os.path.join(SD, t + ".json")
        j = json.load(io.open(p, encoding="utf-8"))
        try:
            df = yf.download(_yf_sym(t), start=start, end=None, auto_adjust=True,
                             progress=False, threads=False)
        except Exception as e:
            print("  ✗ %-6s 내려받기 실패 — %s" % (t, str(e)[:60]))
            failed += 1
            continue
        if df is None or df.empty:
            print("  ✗ %-6s 빈 응답" % t)
            failed += 1
            continue
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        got = {}
        for d_, row in df.iterrows():
            key = str(d_)[:10]
            got[key] = row

        # 🚨 대조 — 겹치는 종가가 어긋나면 남의 종목이거나 조정 기준이 다르다. 안 건드린다.
        a = j.get("pxd") or []
        ov, bad = 0, 0
        for i in range(lo, n):
            d_ = dates[i]
            if a[i] is None or d_ not in got:
                continue
            v = got[d_].get("Close")
            if v is None or v != v or not (v > 0):
                continue
            ov += 1
            if abs(v / a[i] - 1) > TOL:
                bad += 1
        if ov < MIN_OVERLAP:
            print("  ⚠ %-6s 대조 관측 %d개뿐 — 건드리지 않는다" % (t, ov))
            skipped += 1
            continue
        if bad:
            print("  ⚠ %-6s 겹치는 종가 %d/%d 가 %.0f%% 넘게 어긋남 — 건드리지 않는다"
                  % (t, bad, ov, TOL * 100))
            skipped += 1
            continue

        # ── 빈 칸만 채운다 ────────────────────────────────────────────
        wrote = 0
        for key, col in FIELDS:
            arr = j.get(key)
            if not isinstance(arr, list) or len(arr) != n:
                continue
            for i in range(lo, n):
                if arr[i] is not None:
                    continue                       # 있는 값은 절대 덮지 않는다
                d_ = dates[i]
                if d_ not in got:
                    continue
                v = got[d_].get(col)
                if v is None or v != v:
                    continue
                arr[i] = int(v) if key == "vd" else round(float(v), 4)
                if key == "pxd":
                    wrote += 1
                    fill_by_date[d_] = fill_by_date.get(d_, 0) + 1
        if wrote:
            io.open(p, "w", encoding="utf-8").write(
                json.dumps(j, ensure_ascii=False, separators=(",", ":")) + "\n")
            filled += 1
        print("  %s %-6s 종가 %d칸" % ("✓" if wrote else "·", t, wrote))

    print("\n채운 종목 %d · 건너뜀 %d · 실패 %d" % (filled, skipped, failed))
    for d in sorted(fill_by_date):
        print("  %s  %d칸" % (d, fill_by_date[d]))
    # ⚠ 남은 구멍을 반드시 다시 세어 알린다. '채웠다'로 끝내면 못 채운 것이 조용해진다.
    left = 0
    for t in todo:
        a = json.load(io.open(os.path.join(SD, t + ".json"), encoding="utf-8")).get("pxd") or []
        left += sum(1 for i in range(lo, n) if i < len(a) and a[i] is None)
    print("남은 빈 칸 %d개%s" % (left, " — 상장 전이거나 원천에 없는 날이다." if left else ""))
    if filled:
        print("→ 다음: python build/home_summary.py (홈 묶음 다시 굽기)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
