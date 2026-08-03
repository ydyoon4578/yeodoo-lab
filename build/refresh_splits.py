#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주식분할 이력 수집 → data/splits.json

**무엇을 푸는가.** 가격은 분할조정본(auto_adjust=True)이라 전 구간이 오늘 기준인데,
SEC 가 보고하는 주식수·EPS·DPS 는 **당시 보고치**다. 그래서 한 계열 안에서 분할 전·후
기준이 섞이고, 그대로 쓰면 E/P 가 112%로 나오는 식의 **선견**이 된다.

지금까지 이 랩은 그 구간을 **잘라서** 피했다(tech_backtest.split_trim). 안전하지만 비쌌다 —
실측 2026-08-04: 205종 · 주식수 관측 3,575/9,576(37%)을 버리고 있었다. 자른 이유는 하나였다:
  "비율만으로 분할과 증자를 구별해야 하고, 그 판단이 틀리면 없던 숫자를 만든다."

이 파일이 그 전제를 없앤다. **비율을 추정하는 게 아니라 코퍼릿액션을 읽는다.**
분할비는 회사가 공시한 사실이고 yfinance 가 전 이력을 무료로 준다. 실측으로 확인했다 —
이음매 비율과 실제 분할비가 CMG 49.923 vs ×50 · NVDA 10.038 vs ×10 · AMZN 20.051 vs ×20
· WMT 2.992 vs ×3 으로 맞물렸고, 반대로 OMC 1.535(IPG 합병 신주)·MSTR 8.838(ATM 대량발행)은
어느 분할과도 맞지 않았다. 즉 **구별이 된다.** 되는 것만 되맞추고 나머지는 그대로 자른다.

⚠ 여기서 하지 않는 것 — 이 파일은 분할비만 싣는다. 되맞추기는 쓰는 쪽(tech_backtest)이
  한다. 수집기가 값을 고쳐 저장하면 원본이 사라져 나중에 검산할 수 없다.

사용: python3 build/refresh_splits.py
"""
from __future__ import annotations

import datetime as dt
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
OUT = os.path.join(DATA, "splits.json")

# 가격 격자가 2009-01-02 에서 시작한다. 그보다 오래된 분할은 조정할 대상이 없다.
# 여유를 두 해 준다 — 2009 년 초 관측을 손보려면 그 직후 분할까지 알아야 한다.
START = "2007-01-01"
# 분할로 볼 최소 크기. 1.0 근처의 미세 비율은 주식배당(HON 2018-10-01 ×1.011 등)이라
# 기준을 흔들지 않는다. 이음매(1.5배) 판정에 걸릴 일도 없으므로 싣지 않는다.
MIN_RATIO = 1.2


def load_universe():
    d = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    ts = [s["t"] for s in (d.get("stocks") or []) if s.get("t")]
    if not ts:                                   # 슬림 포맷 대비
        ts = sorted(f[:-5] for f in os.listdir(os.path.join(DATA, "sd"))
                    if f.endswith(".json"))
    return sorted(set(ts))


def main() -> int:
    import yfinance as yf
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from refresh_stocks import _yf_sym          # 점→하이픈 변환은 한 벌만 둔다

    uni = load_universe()
    print("유니버스 %d종" % len(uni))

    def one(t):
        try:
            s = yf.Ticker(_yf_sym(t)).splits
        except Exception:
            return t, None
        if s is None or not len(s):
            return t, []
        out = []
        for idx, v in s.items():
            d = str(idx.date())
            try:
                r = float(v)
            except (TypeError, ValueError):
                continue
            if d >= START and r > 0 and (r >= MIN_RATIO or r <= 1.0 / MIN_RATIO):
                out.append([d, round(r, 6)])
        out.sort()
        return t, out

    from concurrent.futures import ThreadPoolExecutor
    rows, miss = {}, []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, (t, r) in enumerate(ex.map(one, uni), 1):
            if r is None:
                miss.append(t)
            elif r:
                rows[t] = r
            if i % 100 == 0:
                print("  … %d/%d" % (i, len(uni)))

    # 🚨 실패를 성공으로 착각하지 않는다. yfinance 는 분할이 없는 회사와 조회 실패를
    #   똑같이 '빈 계열'로 돌려줄 수 있다. 그래서 예외만 miss 로 세고, 그 수가 크면
    #   덮어쓰지 않는다 — 반쪽 파일로 갈아치우면 되맞추기가 조용히 꺼진다.
    if len(miss) > len(uni) * 0.05:
        print("❌ 조회 실패 %d종(>5%%) — 갱신 중단(이전본 유지): %s"
              % (len(miss), ", ".join(miss[:10])))
        return 1

    n_sp = sum(len(v) for v in rows.values())
    doc = {
        "note": "주식분할 이력(yfinance). 값은 분할비다 — 2:1 분할이면 2.0. "
                "%s 이후, 비율 %.1f배 이상만 싣는다(그 아래는 주식배당이라 기준을 흔들지 않는다). "
                "쓰는 쪽이 '당시 보고 주식수 → 오늘 기준'으로 되맞추는 데 쓴다." % (START, MIN_RATIO),
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start": START,
        "min_ratio": MIN_RATIO,
        "n_co": len(rows),
        "n": n_sp,
        "co": rows,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    print("분할 이력: %d사 · %d건 · %.0fKB (분할 있는 회사만 싣는다)"
          % (len(rows), n_sp, os.path.getsize(OUT) / 1024))
    if miss:
        print("⚠ 조회 실패 %d종: %s" % (len(miss), ", ".join(miss[:10])))
    big = sorted(((r, t, d) for t, v in rows.items() for d, r in v), reverse=True)[:5]
    print("가장 큰 분할: %s" % " · ".join("%s %s ×%g" % (t, d, r) for r, t, d in big))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
