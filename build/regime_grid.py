# -*- coding: utf-8 -*-
"""build/regime_grid.py — 점수밴드 × 추세 15칸 표 → data/_regime_grid.json

사전등록: build/PREREG-2026-09-21-REGIMEGRID.md (계산 전 커밋 6b120f2)

무엇을. `_riskonoff.json` 에서 밴드가 **거꾸로** 간다 — Risk-Off +2.02% 인데
  Risk-On +0.34%. 모니터 자신의 국면표도 같은 방향이다. 그런데 그 국면표는
  밴드 하나가 아니라 **점수밴드 × 추세** 두 축이다. Risk-Off 안에 「바닥에서
  올라오는 중」과 「계속 무너지는 중」이 섞여 평균이 뭉개진 것일 수 있다.

⚠ 추세 정의는 **원천 그대로** 가져온다 — d5(5거래일 점수 변화), 컷 ±2점.
   컷도 되돌아보기 길이도 안 움직인다. 움직이면 폐기한 `nsel` 과 같은 자유도다.

🚨 **겹침 보정이 이 검정의 핵심이다.** 일별로 21일 창을 재면 이웃 관측이 20일을
   공유한다 — n=875 라도 독립 표본은 875/21 ≈ 42 에 가깝다. 중첩 t 만 보고
   통과를 선언하면 안 된다. F5 가 그것을 막는다.

⚠ 여기서 점수를 다시 굽지 않는다. `data/_riskonoff_daily.json` 하나만 읽는다.

  python build/regime_grid.py
"""
from __future__ import annotations
import io, json, math, os, statistics as st, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(DATA, "_riskonoff_daily.json")
OUT = os.path.join(DATA, "_regime_grid.json")

LOOK = 5        # 추세 되돌아보기(거래일) — 원천 _scell()
CUT = 2.0       # 추세 컷(점) — 원천 _scell()
FWD = 21        # 사후창(거래일) — riskonoff.py 와 같은 값
BANDS = ["Risk-On", "준Risk-On", "중립", "준Risk-Off", "Risk-Off"]
TRENDS = ["▲ 오름", "→ 옆", "▼ 내림"]
MIN_CELL = 60   # F4 — 이보다 얇은 칸
F4_MAX = 5      # F4 — 얇은 칸이 이만큼이면 측정 불가
F2_T = 1.5      # F2 — 이 랩이 다른 등록에서 쓴 값


def trend_of(d5):
    return TRENDS[0] if d5 >= CUT else (TRENDS[2] if d5 <= -CUT else TRENDS[1])


def agg(v, base=None):
    if not v:
        return {"n": 0, "mean": None, "win": None, "lift": None}
    m = st.mean(v)
    return {"n": len(v), "mean": m,
            "win": sum(1 for x in v if x > 0) / len(v) * 100,
            "lift": (m - base) if base is not None else None}


def welch(a, b):
    """두 표본 평균차의 t. 표본이 얇으면 None."""
    if len(a) < 2 or len(b) < 2:
        return None
    va, vb = st.variance(a), st.variance(b)
    den = math.sqrt(va / len(a) + vb / len(b))
    return (st.mean(a) - st.mean(b)) / den if den > 0 else None


def build(rows, idxs):
    """idxs 가 가리키는 행만으로 15칸을 만든다. 반환: (cells, base_vals)."""
    cells, allv = {}, []
    for i in idxs:
        r = rows[i]
        fv = (rows[i + FWD]["spx"] / r["spx"] - 1) * 100
        cells.setdefault((r["band"], r["tr"]), []).append(fv)
        allv.append(fv)
    return cells, allv


def main() -> int:
    src = json.load(io.open(SRC, encoding="utf-8"))
    rows = src["rows"]
    n = len(rows)

    # 🚨 rows 가 격자상 연속인지 먼저 본다. riskonoff.py 는 사후수익을 «전체 격자»
    #   기준으로 쟀다(di[d] → PX[i+FWD]). 여기서는 행 오프셋을 쓰므로, 행이
    #   중간에 건너뛴 날이 있으면 i+21 이 21거래일 뒤가 아니게 된다.
    #   n - FWD 가 원 산출물의 표본수(3678)와 같으면 연속이다.
    # 🚨 2026-09-24 — 종전에는 «n − FWD == 3678»(원 산출물 표본수)로 쟀다. 그러면 거래일이 하루만
    #   늘어도 연속인데 멈춘다(09-22 복구 뒤 3681 에서 refresh-stocks 가 죽었다).
    #   → 행 날짜가 종목 격자(stocks.json pxd_dates)에서 빈틈없이 이어지는지를 직접 본다.
    grid = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))["pxd_dates"]
    pos = {d: i for i, d in enumerate(grid)}
    idx = [pos.get(r["d"]) for r in rows]
    contiguous = all(x is not None for x in idx) and all(b - a == 1 for a, b in zip(idx, idx[1:]))
    if not contiguous:
        gaps = [rows[j]["d"] for j in range(1, n)
                if idx[j] is None or idx[j - 1] is None or idx[j] - idx[j - 1] != 1][:5]
        print("🚨 행이 격자상 연속이 아니다 (첫 빈틈 %s). 중단한다." % ", ".join(gaps))
        return 1

    for i, r in enumerate(rows):
        r["d5"] = round(r["score"] - rows[i - LOOK]["score"], 1) if i >= LOOK else None
        r["tr"] = trend_of(r["d5"]) if r["d5"] is not None else None

    usable = [i for i in range(n) if i >= LOOK and i + FWD < n]

    # ── 주 표: 일별(중첩) ──────────────────────────────────────────────
    cells, allv = build(rows, usable)
    base = st.mean(allv)
    grid = {}
    for b in BANDS:
        for t in TRENDS:
            grid["%s|%s" % (b, t)] = agg(cells.get((b, t), []), base)

    # ── F5: 21일 간격 비중첩. 위상 하나를 고르지 않고 21개 위상 전부 돈다 ──
    #   ⚠ 이건 자유도를 더하는 게 아니라 **빼는** 것이다 — 어느 위상이 좋은지
    #     고르지 않고 21개 결과를 다 적는다.
    phase = []
    for p in range(FWD):
        idxs = [i for i in range(LOOK + p, n - FWD, FWD)]
        c2, a2 = build(rows, idxs)
        ro_up = c2.get(("Risk-Off", TRENDS[0]), [])
        ro_dn = c2.get(("Risk-Off", TRENDS[2]), [])
        phase.append({"p": p, "n": len(a2),
                      "n_up": len(ro_up), "n_dn": len(ro_dn),
                      "d": (st.mean(ro_up) - st.mean(ro_dn)) if (ro_up and ro_dn) else None,
                      "t": welch(ro_up, ro_dn)})

    # ── 실패 조건 대조 ────────────────────────────────────────────────
    ro_up = cells.get(("Risk-Off", TRENDS[0]), [])
    ro_dn = cells.get(("Risk-Off", TRENDS[2]), [])
    f1_diff = (st.mean(ro_up) - st.mean(ro_dn)) if (ro_up and ro_dn) else None
    f1 = (f1_diff is not None and f1_diff > 0)
    t_ov = welch(ro_up, ro_dn)
    f2 = (t_ov is not None and abs(t_ov) >= F2_T)

    # F3 — 같은 추세 안에서 Risk-On 이 Risk-Off 보다 여전히 낮은가(세 추세 중 둘 이상)
    f3_rows, f3_worse = [], 0
    for t in TRENDS:
        on = grid["Risk-On|%s" % t]["mean"]
        off = grid["Risk-Off|%s" % t]["mean"]
        w = (on is not None and off is not None and on < off)
        f3_worse += 1 if w else 0
        f3_rows.append({"tr": t, "on": on, "off": off, "on_lower": w})
    f3_hit = f3_worse >= 2          # 걸리면 「밴드 해석 불가」 유지

    thin = [k for k, v in grid.items() if v["n"] < MIN_CELL]
    f4_hit = len(thin) >= F4_MAX

    tt = [x["t"] for x in phase if x["t"] is not None]
    dd = [x["d"] for x in phase if x["d"] is not None]
    t_med = st.median(tt) if tt else None
    f5_pass = (t_med is not None and abs(t_med) >= F2_T)
    f5_split = (f2 != f5_pass)      # 중첩과 비중첩 판정이 갈리면 보류

    verdict = ("측정 불가" if f4_hit else
               "기각" if not f1 else
               "보류" if f5_split else
               "측정만")

    doc = {"note": "점수밴드 × 추세 15칸. 사전등록 PREREG-2026-09-21-REGIMEGRID(커밋 6b120f2) "
                   "대로 계산 전에 실패조건을 못박았다. 추세 정의(d5·±2)는 사용자 제공 "
                   "KBAM 국면 모니터의 _scell() 값 그대로다.",
           "as_of": src["as_of"], "look": LOOK, "cut": CUT, "fwd_days": FWD,
           "n_used": len(usable), "base_mean": base,
           "base_win": sum(1 for x in allv if x > 0) / len(allv) * 100,
           "bands": BANDS, "trends": TRENDS, "grid": grid,
           "f1": {"hit": not f1, "diff": f1_diff,
                  "n_up": len(ro_up), "n_dn": len(ro_dn),
                  "말": "Risk-Off 안에서 ▲ 가 ▼ 보다 큰가"},
           "f2": {"hit": not f2, "t_overlap": t_ov, "문턱": F2_T},
           "f3": {"hit": f3_hit, "n_worse": f3_worse, "rows": f3_rows,
                  "말": "같은 추세 안에서도 Risk-On 이 Risk-Off 보다 낮으면 역방향은 안 풀린 것"},
           "f4": {"hit": f4_hit, "thin": thin, "문턱": "%d칸 미만 %d개" % (MIN_CELL, F4_MAX)},
           "f5": {"split": f5_split, "t_median": t_med,
                  "t_min": min(tt) if tt else None, "t_max": max(tt) if tt else None,
                  "d_median": st.median(dd) if dd else None,
                  "n_phase": len(phase), "phase": phase,
                  "말": "21개 위상 전부 돌았다 — 좋은 위상을 고르지 않았다"},
           "verdict": verdict}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    # ── 화면 ──────────────────────────────────────────────────────────
    print("\n기준 %s · 쓴 날 %d · 기준선 %+.2f%% · 승률 %.0f%%"
          % (doc["as_of"], doc["n_used"], base, doc["base_win"]))
    print("추세: d5 = 5거래일 점수 변화 · ▲ ≥ +2 · ▼ ≤ −2 (원천 _scell 그대로)\n")
    print("  %-10s %s" % ("밴드", "".join("%18s" % t for t in TRENDS)))
    for b in BANDS:
        line = "  %-10s" % b
        for t in TRENDS:
            c = grid["%s|%s" % (b, t)]
            line += ("%18s" % "—") if not c["n"] else \
                    ("%10s%8s" % ("%+.2f%%" % c["mean"], "(%d일)" % c["n"]))
        print(line)

    print("\n🚨 실패 조건")
    print("  F1 Risk-Off ▲ − ▼ = %s  (▲ %d일 · ▼ %d일)  → %s"
          % ("%+.2f%%p" % f1_diff if f1_diff is not None else "잴 수 없음",
             len(ro_up), len(ro_dn), "걸림 ✗" if not f1 else "통과"))
    print("  F2 그 차이의 t(중첩) = %s (문턱 %.1f) → %s"
          % ("%.2f" % t_ov if t_ov is not None else "—", F2_T,
             "구별 불가" if not f2 else "통과"))
    print("  F3 같은 추세 안 Risk-On < Risk-Off 인 추세 %d/3 → %s"
          % (f3_worse, "걸림 ✗ 역방향 안 풀림" if f3_hit else "통과"))
    for r in f3_rows:
        print("       %-8s Risk-On %s  vs  Risk-Off %s   %s"
              % (r["tr"], "%+.2f%%" % r["on"] if r["on"] is not None else "—",
                 "%+.2f%%" % r["off"] if r["off"] is not None else "—",
                 "← On 이 낮다" if r["on_lower"] else ""))
    print("  F4 %d일 미만 얇은 칸 %d개 %s → %s"
          % (MIN_CELL, len(thin), ("(" + " · ".join(thin) + ")") if thin else "",
             "측정 불가 ✗" if f4_hit else "통과"))
    print("  F5 비중첩 21위상 t 중앙 %s (최소 %s · 최대 %s) → %s"
          % ("%.2f" % t_med if t_med is not None else "—",
             "%.2f" % min(tt) if tt else "—", "%.2f" % max(tt) if tt else "—",
             "중첩과 갈림 → 보류" if f5_split else "중첩과 같은 판정"))
    if t_ov and t_med:
        print("     중첩 t %.2f → 비중첩 t %.2f  (%.0f%% 로 줄었다)"
              % (t_ov, t_med, abs(t_med) / abs(t_ov) * 100))
    print("\n판정: **%s**" % verdict)
    print("→ _regime_grid.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
