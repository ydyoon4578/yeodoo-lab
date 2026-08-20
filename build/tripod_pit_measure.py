# -*- coding: utf-8 -*-
"""build/tripod_pit_measure.py — 삼각대 차단 관문 해소: PIT 직접 측정 → data/tripod_pit.json

규약: build/PREREG-2026-08-19-TRIPOD.md 의 차단 관문 — «pit_backtest 가 슬리브별 PIT
시계열을 내면 G4(근사 t̂ 2.43 · 가정: 초과 상관이 PIT 에서도 유사)를 실측으로 대체한다.
그 전 편입 검토 없음.» 2026-08-20 pit_backtest(다른 세션)가 chart.monthly 를 반출해
재료가 생겼다 — 이 스크립트가 그 관문 측정이다. 문턱은 등록 그대로 t ≥ 2.0.

  입력: data/pit_strategies.json 슬리브 3종(chart.monthly: m·r(전략%)·b(벤치%))
  측정: 슬리브별 월간 PIT 초과(r−b) → 쌍상관·ρ̄ → 동일가중 혼합의 t (직접)
  비교: G4 근사식 t̂ = t̄·√(3/(1+2ρ̄)) 이 실측과 얼마나 어긋났나

    python build/tripod_pit_measure.py
"""
from __future__ import annotations
import datetime as dt
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "tripod_pit.json")
SLEEVES = ["x-dist200-mcf", "x-archlm", "x-guruacc"]
GATE_T = 2.0            # 등록 G4 문턱 그대로 — 바꾸지 않는다


def tstat(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, sd, (m / (sd / math.sqrt(n)) if sd > 0 else None)


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    ca = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return ca / (sa * sb) if sa and sb else None


def main() -> int:
    # 🚨 동결 가드 — 관문 측정도 한 번 재면 기록이다.
    if os.path.exists(OUT) and "--refreeze" not in sys.argv:
        raise SystemExit("%s 가 이미 있다 — 얼린 측정이다. 재동결은 --refreeze 로만." % OUT)
    d = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    by = {x["sid"]: x for x in (d.get("strategies") or [])}
    ex, meta = {}, {}
    grid = None
    for sid in SLEEVES:
        x = by.get(sid)
        if not x:
            raise SystemExit("슬리브 %s 가 pit_strategies 에 없다 — 관문 재료 미충족." % sid)
        mo = (x.get("chart") or {}).get("monthly") or []
        ms = [row["m"] for row in mo]
        if grid is None:
            grid = ms
        elif ms != grid:
            raise SystemExit("월 격자가 다르다(%s) — 같은 격자가 아니면 섞을 수 없다." % sid)
        ex[sid] = [(row["r"] - row["b"]) / 100.0 for row in mo]   # 월간 PIT 초과(소수)
        meta[sid] = {"t_pub": x.get("t"), "n": len(mo)}
    n = len(grid)

    single = {}
    for sid in SLEEVES:
        m, sd, t = tstat(ex[sid])
        single[sid] = {"ann_pp": round(m * 12 * 100, 2), "t": round(t, 2),
                       "t_pub": meta[sid]["t_pub"]}
    import itertools
    cors = {}
    for a, b in itertools.combinations(SLEEVES, 2):
        cors["%s×%s" % (a.split("-")[1], b.split("-")[1])] = round(corr(ex[a], ex[b]), 3)
    rho = sum(cors.values()) / len(cors)

    blend = [sum(ex[s][i] for s in SLEEVES) / 3 for i in range(n)]
    mb_, sdb, tb = tstat(blend)
    # 등록 당시 근사(기록 그대로): t̄=1.68 · ρ̄=0.214 → t̂ 2.43
    t_bar = sum(v["t"] for v in single.values()) / 3
    t_formula = t_bar * math.sqrt(3 / (1 + 2 * rho))

    gate_pass = bool(tb is not None and tb >= GATE_T)
    verdict = ("관문 통과 — G4 근사를 실측이 대체: 혼합 PIT t %.2f ≥ %.1f. "
               "삼각대는 «후보» 지위 유지(게시·편입은 사용자 결정)." % (tb, GATE_T)
               ) if gate_pass else (
               "관문 미달 — 혼합 PIT t %.2f < %.1f. 등록 규칙대로 삼각대는 기각으로 전환." % (tb, GATE_T))

    print("삼각대 PIT 직접 측정 · 월간 %d개 (%s ~ %s)" % (n, grid[0], grid[-1]))
    for sid in SLEEVES:
        v = single[sid]
        print("  %-14s PIT t %.2f (연 초과 %+.2f%%p · 공표 t %s)" % (sid, v["t"], v["ann_pp"], v["t_pub"]))
    print("쌍상관:", cors, "· ρ̄ %.3f" % rho)
    print("혼합(동일가중) t %.2f · 연 초과 %+.2f%%p" % (tb, mb_ * 12 * 100))
    print("근사식 재계산 t̂ %.2f (등록 당시 근사 2.43 — 가정 검증: 상관이 %s)" %
          (t_formula, "유사" if abs(rho - 0.214) < 0.15 else "달랐다(%.3f vs 0.214)" % rho))
    print("판정:", verdict)

    doc = {
        "note": "삼각대 차단 관문 해소 — PIT 슬리브 월간 시계열 직접 측정으로 G4 근사(t̂ 2.43 · "
                "상관 이월 가정)를 대체. 문턱은 등록 그대로 t ≥ 2.0, 결과 보고 바꾸지 않았다. "
                "재료는 pit_backtest(2026-08-20 반출) chart.monthly.",
        "prereg": "build/PREREG-2026-08-19-TRIPOD.md (차단 관문)",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid": {"n": n, "start": grid[0], "end": grid[-1]},
        "single": single, "corr": cors, "rho_bar": round(rho, 3),
        "blend": {"t": round(tb, 2), "ann_pp": round(mb_ * 12 * 100, 2)},
        "formula_recheck": {"t_hat": round(t_formula, 2), "t_hat_registered": 2.43,
                            "rho_assumed": 0.214},
        "gate_t": GATE_T, "gate_pass": gate_pass, "verdict": verdict,
        "monthly": {"m": grid, **{s: [round(x, 6) for x in ex[s]] for s in SLEEVES},
                    "blend": [round(x, 6) for x in blend]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
