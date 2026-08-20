# -*- coding: utf-8 -*-
"""build/forward_weekly.py — 틸트 계열 전방 주간 기록 → data/strategy_forward.json

규약: build/RUNBOOK-FORWARD.md. 얼린 정본(data/{tilt,web}.json)은 건드리지 않는다 —
전방 주는 이 별도 파일에 append-only 로 쌓인다(점검 패널 ③-b 의 설계 요건).

  · 로컬 전용 — 비중 캐시(data/_ndx_weights_cache.json · DB 자격)가 전제라 러너에선 못 돈다.
  · 매주 절차: ① 비중 캐시 갱신(런북 1번) ② python build/forward_weekly.py ③ 커밋.
  · 불변 규칙: 이미 기록된 주는 다시 쓰지 않는다. 재계산이 기존 행과 어긋나면(가격 소급
    수정 등) 경고만 내고 원 기록을 지킨다 — 전방 기록은 «그때 그렇게 보였다»의 원장이다.

  트랙: web(거미줄 WEB · 챔피언 NR′ · 순복제 R) + tilt(모멘텀 틸트 · 복제).

    python build/forward_weekly.py
"""
from __future__ import annotations
import datetime as dt
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_forward.json")
sys.path.insert(0, HERE)
from aegis_backtest import load_px, week_ends, Sig                          # noqa: E402
from tilt_backtest import load_weights, alias_map                           # noqa: E402
from aegis3_backtest import load_rf                                          # noqa: E402
from wvane_backtest import RetSig, build_weeks                               # noqa: E402
import tilt_backtest as TB                                                   # noqa: E402
import web_backtest as WB                                                    # noqa: E402

TOL = 5e-6              # 기존 행과의 허용 오차(주간 수익) — 넘으면 소급 수정 경고


def main() -> int:
    frozen_end = {
        "tilt": json.load(io.open(os.path.join(DATA, "tilt.json"), encoding="utf-8"))["span"][1],
        "web": json.load(io.open(os.path.join(DATA, "web.json"), encoding="utf-8"))["span"][1],
    }
    dts, px, bench = load_px()
    W = load_weights()
    AL = alias_map()
    rf = load_rf()
    last_ym = max(rf)
    sig = Sig(px, len(dts))
    vsig = RetSig(px, len(dts))
    bsig = Sig(bench, len(dts))
    we_idx = week_ends(dts)
    weeks, _sk = build_weeks(dts, px, W, AL, we_idx, bsig)

    # web 트랙 — 거미줄·챔피언·복제
    resolve = WB.sector_labels(W, AL)
    lam, _lc = WB.lam_series(bench["ndx"], dts, we_idx)
    P = WB.build_signals(dts, px, weeks, sig, vsig, resolve)
    runs_web = {
        "WEB": WB.run(dts, px, weeks, P, lam, rf, last_ym, use_s=True, k_mode="neutral",
                      use_lambda=True, band=True),
        "NRp": WB.run(dts, px, weeks, P, lam, rf, last_ym, k_mode="global", band=True),
        "R": WB.run(dts, px, weeks, P, lam, rf, last_ym),
    }
    # tilt 트랙 — 모멘텀 틸트·복제 (tilt 엔진 그대로)
    dd_t, dv_t, dv_r, wk_t = TB.run(dts, px, sig, W, AL, we_idx)

    if os.path.exists(OUT):
        doc = json.load(io.open(OUT, encoding="utf-8"))
    else:
        doc = {"note": "틸트 계열 전방 주간 기록 — append-only. 얼린 정본과 분리(런북 참조). "
                       "기록된 주는 불변 — 재계산이 어긋나면 경고만 내고 원 기록을 지킨다.",
               "runbook": "build/RUNBOOK-FORWARD.md",
               "tracks": {"web": {"frozen_end": frozen_end["web"], "rows": []},
                          "tilt": {"frozen_end": frozen_end["tilt"], "rows": []}}}

    added, warned = 0, 0

    def upsert(track, d0, row):
        nonlocal added, warned
        tr = doc["tracks"][track]
        old = next((r for r in tr["rows"] if r["d0"] == d0), None)
        if old is None:
            row["recorded"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            tr["rows"].append(row)
            added += 1
        else:
            for k, v in row.items():
                ov = old.get(k)
                if isinstance(v, float) and isinstance(ov, (int, float)) and abs(v - ov) > TOL:
                    print("⚠ %s %s %s 재계산이 기록과 어긋남(%.6f vs %.6f) — 원 기록 유지"
                          % (track, d0, k, v, ov))
                    warned += 1

    for j, w in enumerate(weeks):
        d0 = w["d0"]
        if d0 > frozen_end["web"]:
            upsert("web", d0, {"d0": d0,
                               "WEB": round(runs_web["WEB"]["wk"]["ret"][j], 6),
                               "NRp": round(runs_web["NRp"]["wk"]["ret"][j], 6),
                               "R": round(runs_web["R"]["wk"]["ret"][j], 6),
                               "on": 1 if w["on"] else 0})
    for j, d0 in enumerate(wk_t["d"]):
        if d0 > frozen_end["tilt"]:
            upsert("tilt", d0, {"d0": d0,
                                "tilt": round(wk_t["rt"][j], 6),
                                "replica": round(wk_t["rr"][j], 6)})

    for k in doc["tracks"]:
        doc["tracks"][k]["rows"].sort(key=lambda r: r["d0"])
        doc["tracks"][k]["n"] = len(doc["tracks"][k]["rows"])
    doc["last_run"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s · 신규 %d행 · 어긋남 경고 %d · 누적 web %d / tilt %d"
          % (os.path.relpath(OUT, ROOT), added, warned,
             doc["tracks"]["web"]["n"], doc["tracks"]["tilt"]["n"]))
    if added == 0:
        print("  (신규 0 = 비중 캐시가 아직 이번 주 스냅샷 전 — 런북 1번을 먼저)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
