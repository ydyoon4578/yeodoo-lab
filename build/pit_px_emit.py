# -*- coding: utf-8 -*-
"""build/pit_px_emit.py — 편출 종목 가격 캐시를 **커밋할 수 있는 얇은 기록**으로 옮긴다.

  data/_pit_px_cache.json (10.6MB · gitignore) → data/pit_px.json (3.5MB · 커밋)

## 왜 있나 (2026-08-19 · 사용자 지적)

  "style_pit 은 원본 가격 캐시가 gitignore 라 러너가 못 굽는다" 고 적어 두고 넘어갔는데,
  사용자가 «이거 왜 해결못해» 라고 물었다. 재 보니 **구조가 아니라 형식 문제**였다.

  · 캐시는 편출 종목 **154개**의 일별 가격이다. 무거운 것은 자료가 아니라 형식이었다 —
    티커마다 {날짜: 값} dict 이라 4,427개 날짜 문자열이 154번 되풀이된다.
  · 날짜를 한 번만 적고 값을 배열로 두면 10.6MB → **3.5MB(gzip 1.3MB)** 다.
  · 🚨 그리고 결정적인 것 — **편출된 종목의 과거 가격은 앞으로 바뀌지 않는다.**
    한 번 싣고 나면 이후 커밋 비용이 사실상 0 이다(새로 편출된 이름이 생길 때만 는다).
  · 이 저장소는 이미 data/assets.json(4.5MB)과 data/fx_pit/(편출 종목 재무 145파일)을
    커밋한다. 편출 **재무**를 싣으면서 편출 **가격**만 안 싣고 있었던 것이다.

## 왜 러너에서 다시 받지 않나

  받을 수는 있다(154종). 그러나 편출·상장폐지 종목은 yfinance 가 **오늘 준다는 보장이 없다.**
  🚨 그 이름이 하나 사라지면 PIT 레그의 후보가 조용히 생존자 쪽으로 기울고, 그러면
    «생존편향을 재는 표» 가 스스로 생존편향을 갖는다. 이 파일에서 그것은 최악의 실패다.
  그래서 벤더가 계속 준다는 데 기대지 않고 **기록으로 저장소에 남긴다.**

## 언제 다시 돌리나

  새 이름이 편출됐을 때만. 이미 편출된 종목의 값은 안 변한다.
  ⚠ 캐시 자체의 끝날짜가 창 끝보다 이르면 최근 편출분의 꼬리가 빈다 — 그 사실을
    coverage 에 적어 두고 style_pit 이 화면 한계로 옮긴다.

    python build/pit_px_emit.py
"""
from __future__ import annotations
import io
import math
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(DATA, "_pit_px_cache.json")
OUT = os.path.join(DATA, "pit_px.json")


def sig(x, n=6):
    """유효숫자 n자리로 반올림.

    🚨 소수 자리로 자르면 안 된다. 이 캐시의 가격은 $0.015 ~ $113,900 이고 1달러 미만이
      4,028건이다 — 소수 3자리로 자르면 $0.015 짜리는 7% 오차가 된다(비싼 종목은 멀쩡하니
      평균만 보면 안 보인다). 유효숫자로 자르면 전 구간이 같은 상대 정밀도(1e-6)를 갖는다.
    ⚠ 크기 대가는 3.51MB → 3.81MB 뿐이다(실측). 저가 편출주의 정밀도를 그 값에 판다.
    """
    if not x:
        return 0.0
    return round(x, max(0, n - int(math.floor(math.log10(abs(x)))) - 1))


def main() -> int:
    if not os.path.exists(SRC):
        print("❌ %s 가 없다 — 이 스크립트는 캐시가 있는 PC 에서만 돈다." % SRC)
        return 1
    src = json.load(io.open(SRC, encoding="utf-8"))
    dates = sorted({d for v in src.values() for d in v})
    if not dates:
        print("❌ 캐시에 날짜가 없다")
        return 1
    idx = {d: i for i, d in enumerate(dates)}

    px, n_pts = {}, 0
    for t, v in sorted(src.items()):
        a = [None] * len(dates)
        for d, p in v.items():
            a[idx[d]] = None if p is None else sig(float(p))
        lo = next((i for i, x in enumerate(a) if x is not None), None)
        if lo is None:
            continue                       # 값이 하나도 없는 티커는 싣지 않는다
        hi = next(i for i in range(len(a) - 1, -1, -1) if a[i] is not None)
        seg = a[lo:hi + 1]
        n_pts += sum(1 for x in seg if x is not None)
        # i0 = 그 티커의 첫 값이 놓인 dates 색인. 앞뒤 빈 구간을 안 싣는다
        # (편출 종목은 대부분 창의 일부만 산다).
        px[t] = {"i0": lo, "p": seg}

    doc = {
        "note": "편출·상장폐지 종목의 일별 종가 기록. data/_pit_px_cache.json 을 날짜 배열 "
                "한 벌 + 티커별 구간 배열로 옮긴 것이다 — 같은 자료, 3분의 1 크기. "
                "🚨 러너가 style_pit 을 굽게 하려고 커밋한다. 벤더가 편출 종목을 계속 준다는 "
                "보장이 없어 다시 받지 않고 기록으로 남긴다 — 이름 하나가 사라지면 "
                "생존편향을 재는 표가 스스로 생존편향을 갖는다.",
        "source": "data/_pit_px_cache.json (build/pit_backtest.py 가 yfinance 로 채운다)",
        "coverage": {"start": dates[0], "end": dates[-1], "n_dates": len(dates),
                     "n_tickers": len(px), "n_points": n_pts},
        "caveat": "이 기록의 끝날짜(%s)가 랩 격자의 끝보다 이르면, 그 사이에 편출된 종목의 "
                  "꼬리가 비어 있다. 이미 편출된 종목의 값은 바뀌지 않으므로 그 밖의 구간은 "
                  "다시 받을 필요가 없다." % dates[-1],
        "dates": dates,
        "px": px,
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s · 티커 %d · 날짜 %d (%s ~ %s) · 관측 %d · %.1fMB (원본 %.1fMB)"
          % (os.path.relpath(OUT, ROOT), len(px), len(dates), dates[0], dates[-1],
             n_pts, os.path.getsize(OUT) / 1e6, os.path.getsize(SRC) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
