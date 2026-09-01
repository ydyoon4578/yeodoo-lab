# -*- coding: utf-8 -*-
"""build/secrev_panel.py — 섹터 × 일자 등급리비전 패널 → data/_secrev_panel.json

규약: build/PREREG-2026-09-01-SECREV.md (계산 전 커밋 308ba91ab · 47823a3dd).

  각 섹터의 신호 = 그 시점 그 섹터 종목의 `rat_signal(t, date, 30)` **동일가중 평균**.
  `rat_signal = (컨센서스 지금 − 30일 전) × √증권사수` — 랩에 이미 있는 함수다.

🚨 **신호를 새로 짜지 않는다.** E21 카드는 「(상향 건수 − 하향 건수) ÷ 커버 수」로 적지만
  그것을 여기서 구현하면 같은 것의 **두 번째 사본**이 되고, 한쪽만 고쳐지는 날이 온다.
  이 저장소가 되풀이 밟은 사고다(등록 §1). 창도 x-revdrift 의 30일을 그대로 쓴다 —
  63일판은 이미 x-revdrift-q 로 따로 있고, 여기서 둘을 다 돌리면 그것이 창 쓸기다.

🚨 **얼린 측정이다.** 입력인 data/_ratings_cache.json 이 gitignore 라 러너가 재생산할 수
  없다(tilt·revscreen·web·wvane 과 같은 사유). 산출물도 밑줄 접두로 두고 커밋하지 않는다.
  자동 재굽기 금지 — 기록이다.

⚠ 섹터 라벨은 **오늘의 GICS** 다. 2018-09 재편 이전에는 ETF 의 실제 구성과 다르다
  (등록 §3-② — 측정 구간의 앞 2.1년이 그 상태다). 랩에 시점별 섹터 이력이 없어 못 고친다.

    python build/secrev_panel.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

OUT = os.path.join(DATA, "_secrev_panel.json")     # 밑줄 = 로컬 전용(커밋 금지)

# ── 등록 §1 의 상수 — 결과를 보고 만지지 않는다 ─────────────────────────────
CAL_DAYS = 30      # x-revdrift 와 같은 창. 새로 고른 값이 아니다.
MIN_COV = 5        # 신호가 나오는 종목이 이보다 적은 섹터는 후보에서 뺀다.
#   ⚠ **안 걸리는 안전장치로 골랐다.** 2016-08~2026-07 분기 표본 40개 시점에서 가장 얇은
#     섹터(커뮤니케이션)의 최소 커버가 14종이고 5종 미만인 시점은 0개다. 성적을 만드는
#     값이 아니라 자료가 무너졌을 때 알아채는 값이다.


def sector_map():
    """티커 → GICS 섹터. data/members.json 이 정본이다."""
    p = os.path.join(DATA, "members.json")
    d = json.load(io.open(p, encoding="utf-8"))
    src = d.get("members") or d.get("rows") or d
    out = {}
    if isinstance(src, dict):
        for t, v in src.items():
            if isinstance(v, dict) and v.get("sector"):
                out[t] = v["sector"]
    elif isinstance(src, list):
        for v in src:
            if isinstance(v, dict) and v.get("t") and v.get("sector"):
                out[v["t"]] = v["sector"]
    if not out:
        raise SystemExit("섹터 라벨을 못 읽었다 — data/members.json 의 구조가 바뀌었나")
    return out


def main():
    import tech_backtest as TB

    if getattr(TB, "_RAT", None) is None:
        TB._RAT = TB.load_ratings()
    if not TB._RAT:
        raise SystemExit(
            "등급 이력이 없다 — data/_ratings_cache.json 을 먼저 만들 것"
            "(build/fetch_ratings.py). 이 패널은 그것 없이는 의미가 없다.")

    sec = sector_map()
    # 격자는 자산 랩과 같은 것을 쓴다 — 규칙이 그 위에서 돈다(격자가 둘이면 어긋난다).
    ast = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    dates = ast["dates"]
    # 월말만 만든다. 규칙이 월말에만 판정하므로 일자 전체를 만들면 파일만 커진다.
    me = [dates[i] for i in range(len(dates) - 1) if dates[i][:7] != dates[i + 1][:7]]
    me.append(dates[-1])

    secs = sorted(set(sec.values()))
    by_sec = {}
    for t, s in sec.items():
        by_sec.setdefault(s, []).append(t)

    panel, cov = {}, {}
    for d in me:
        row, crow = {}, {}
        for s in secs:
            vs = []
            for t in by_sec[s]:
                v = TB.rat_signal(t, d, CAL_DAYS)
                if v is not None:
                    vs.append(v)
            crow[s] = len(vs)
            if len(vs) >= MIN_COV:
                row[s] = sum(vs) / len(vs)
        panel[d] = row
        cov[d] = crow

    # ── 커버 진단 ─────────────────────────────────────────────────────────
    # 🚨 **전 구간 최소로 세면 안 된다.** 이 격자는 자산 랩 것이라 2006 부터인데 등급
    #   이력은 2011-12 부터다 — 앞구간이 커버 0 인 것은 결함이 아니라 «자료가 아직
    #   없는 구간» 이다. 처음에 전 구간 최소를 찍었더니 전 섹터가 0 으로 나와
    #   «문턱이 걸렸다» 로 오독됐다. 규칙이 실제로 서는 구간에서 세야 뜻이 있다.
    # 규칙이 서는 첫 달 = 전 섹터가 문턱을 넘는 첫 월말.
    _ok = [d for d in me if len(panel[d]) == len(secs)]
    live = _ok[0] if _ok else None
    thin = [(d, s, n) for d, c in cov.items() if live and d >= live
            for s, n in c.items() if 0 < n < MIN_COV]
    zero = [(d, s) for d, c in cov.items() if live and d >= live
            for s, n in c.items() if n == 0]

    doc = {
        "note": ("섹터 × 월말 등급리비전 패널. 규약 build/PREREG-2026-09-01-SECREV.md. "
                 "신호 = 그 섹터 종목의 rat_signal(t, date, %d) 동일가중 평균. "
                 "🚨 얼린 측정이다 — 입력(data/_ratings_cache.json)이 커밋 금지라 러너가 "
                 "재생산할 수 없다. 자동 재굽기 금지." % CAL_DAYS),
        "signal": {"fn": "tech_backtest.rat_signal", "cal_days": CAL_DAYS,
                   "agg": "섹터 내 동일가중 평균", "min_cov": MIN_COV},
        "caveat": ["섹터 라벨은 오늘의 GICS 다 — 2018-09 재편 이전에는 ETF 실제 구성과 다르다.",
                   "등급 원천이 살아남은 종목만 준다(생존 채널 보완 불가) — x-revdrift 가 "
                   "PARTIAL_PIT 인 것과 같은 사유."],
        "grid": {"source": "data/assets.json", "month_ends": len(me),
                 "first": me[0], "last": me[-1]},
        # ⚠ 커버 수치는 **규칙이 서는 구간(live~)** 에서만 센다. 그 앞은 등급 이력이
        #   없는 구간이라 0 인 것이 정상이다.
        "live_from": live,
        "coverage": {"min_by_sector": {s: min(cov[d][s] for d in me if live and d >= live)
                                       for s in secs} if live else {},
                     "thin_hits": len(thin), "zero_hits": len(zero),
                     "months_live": sum(1 for d in me if live and d >= live)},
        "panel": panel,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False) + "\n")

    print("섹터 %d개 × 월말 %d개 (%s ~ %s)" % (len(secs), len(me), me[0], me[-1]))
    print("규칙이 서는 첫 달(전 섹터 문턱 통과): %s — 그 앞은 등급 이력이 없는 구간이다"
          % (live or "없음"))
    print("섹터별 최소 커버 종목수(%s~):" % (live or "—"))
    for s in secs:
        print("  %-24s %3d" % (s[:22], min(cov[d][s] for d in me if live and d >= live)
                               if live else 0))
    if thin or zero:
        print("🚨 커버 문턱(%d)이 걸린 자리 %d개 · 커버 0인 자리 %d개 — 등록은 «안 걸린다» 고"
              " 적었다. 결과 문서에 그 사실을 적을 것." % (MIN_COV, len(thin), len(zero)))
    else:
        print("커버 문턱(%d)은 한 번도 안 걸렸다 — 등록의 예상대로다." % MIN_COV)
    print("→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
