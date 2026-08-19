# -*- coding: utf-8 -*-
"""build/tripod_backtest.py — 삼각대(신호 분산 앙상블) → data/tripod.json

규약: build/PREREG-2026-08-19-TRIPOD.md (계산 전 커밋). 규칙은 거기 있다.
슬리브: x-dist200-mcf · x-archlm · x-guruacc — 공표 시계열(nav/bnav)의 동일가중.

    python build/tripod_backtest.py
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
OUT = os.path.join(DATA, "tripod.json")
SLEEVES = ["x-dist200-mcf", "x-archlm", "x-guruacc"]
COST_BP = 5            # 편도 — §2. 민감도 20bp
PIT_T = {"x-dist200-mcf": 1.79, "x-archlm": 1.35, "x-guruacc": 1.90}   # 공표 수치(§1)


def tstat(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, sd, (m / (sd / math.sqrt(n)) if sd > 0 else None)


def main() -> int:
    d = json.load(io.open(os.path.join(DATA, "tech_strategies.json"), encoding="utf-8"))
    S = {s["sid"]: s for s in d["strategies"]}
    for k in SLEEVES:
        if k not in S:
            raise SystemExit("슬리브 %s 가 게시 목록에 없다 — 구성 기준이 깨졌다. 멈춘다." % k)
    dates = S[SLEEVES[0]]["dates"]
    for k in SLEEVES[1:]:
        if S[k]["dates"] != dates:
            raise SystemExit("격자가 다르다(%s) — 같은 격자가 아니면 섞을 수 없다." % k)
    n = len(dates)
    # 간격(연 단위) — 주간 격자라 관측당 드래그를 연 회전에서 환산한다
    d0 = dt.date.fromisoformat(dates[0])
    d1 = dt.date.fromisoformat(dates[-1])
    per_yr = (n - 1) / ((d1 - d0).days / 365.25)

    def sleeve_excess(k, bp):
        s = S[k]
        nav, bn = s["nav"], s["bnav"]
        drag = s["turnover"] * 2 * bp / 10000.0 / per_yr     # 관측당
        return [(nav[i] / nav[i - 1]) - (bn[i] / bn[i - 1]) - drag for i in range(1, n)]

    ex5 = {k: sleeve_excess(k, COST_BP) for k in SLEEVES}
    ex20 = {k: sleeve_excess(k, 20) for k in SLEEVES}
    blend5 = [sum(ex5[k][i] for k in SLEEVES) / 3 for i in range(n - 1)]
    blend20 = [sum(ex20[k][i] for k in SLEEVES) / 3 for i in range(n - 1)]

    m5, sd5, t5 = tstat(blend5)
    _, _, t20 = tstat(blend20)
    single = {}
    for k in SLEEVES:
        mk, sdk, tk = tstat(ex5[k])
        single[k] = {"t": round(tk, 2), "ann_pp": round(mk * per_yr * 100, 2)}
    best_single_t = max(v["t"] for v in single.values())

    half = (n - 1) // 2
    h1 = sum(blend5[:half]) * 100
    h2 = sum(blend5[half:]) * 100
    srt = sorted(blend5)
    top2ex = sum(srt[:-2]) / (len(srt) - 2)

    # 상관 — 슬리브 초과수익(비용 전과 사실상 동일)
    def corr(a, b):
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        ca = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        sa = math.sqrt(sum((x - ma) ** 2 for x in a))
        sb = math.sqrt(sum((y - mb) ** 2 for y in b))
        return ca / (sa * sb) if sa and sb else None
    import itertools
    cors = {"%s×%s" % (a.split('-')[1], b.split('-')[1]): round(corr(ex5[a], ex5[b]), 3)
            for a, b in itertools.combinations(SLEEVES, 2)}
    rho = sum(cors.values()) / len(cors)
    pit_hat = (sum(PIT_T.values()) / 3) * math.sqrt(3 / (1 + 2 * rho))

    g = {
        "G1_blend_gt_best_single": {"blend_t": round(t5, 2), "best_single_t": best_single_t,
                                    "pass": bool(t5 > best_single_t)},
        "G2_halves_pos": {"halves_pp": [round(h1, 2), round(h2, 2)], "pass": bool(h1 > 0 and h2 > 0)},
        "G3_top2_sign": {"top2ex_ann_pp": round(top2ex * per_yr * 100, 2), "pass": bool(top2ex > 0)},
        "G4_pit_approx": {"rho_bar": round(rho, 3), "t_hat": round(pit_hat, 2),
                          "pass": bool(pit_hat >= 2.0),
                          "caveat": "근사 — 초과 상관이 PIT 에서도 유사하다는 검증 불가 가정"},
        "G5_cost20": {"t": round(t20, 2), "pass": bool(t20 >= 2)},
    }
    n_pass = sum(1 for v in g.values() if v["pass"])
    verdict = "후보 — PIT 직접 측정 대기" if n_pass == 5 else "기각 (%d/5)" % n_pass

    print("삼각대 · 관측 %d(주간) · %s ~ %s" % (n - 1, dates[0], dates[-1]))
    for k in SLEEVES:
        print("  %-14s 단독 t %.2f · 연 초과 %+.2f%%p" % (k, single[k]["t"], single[k]["ann_pp"]))
    print("혼합(5bp)  t %.2f · 연 초과 %+.2f%%p" % (t5, m5 * per_yr * 100))
    print("혼합(20bp) t %.2f" % t20)
    print("상관:", cors, "· ρ̄ %.3f · PIT 근사 t̂ %.2f" % (rho, pit_hat))
    for k, v in g.items():
        print("  %-24s %s %s" % (k, "✅" if v["pass"] else "❌",
                                 {a: b for a, b in v.items() if a != "pass"}))
    print("판정: %s" % verdict)

    doc = {
        "note": "삼각대 — 게시 규칙 세 블록 대표(x-dist200-mcf·x-archlm·x-guruacc)의 초과수익 "
                "동일가중 앙상블. 새 신호 없음 — 유일한 새 주장은 «분산이 일한다» 이고 G1 이 "
                "그것을 묻는다. 구성 선택이 표본의 PIT t 를 봤다는 편의와, G4 가 근사라는 "
                "사실은 등록 §0 에 있다.",
        "prereg": "build/PREREG-2026-08-19-TRIPOD.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sleeves": SLEEVES, "pit_t_published": PIT_T, "grid": {"n": n, "start": dates[0], "end": dates[-1]},
        "single": single, "blend": {"t5": round(t5, 2), "ann_pp": round(m5 * per_yr * 100, 2),
                                    "t20": round(t20, 2)},
        "corr": cors, "gates": g, "n_pass": n_pass, "verdict": verdict,
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
