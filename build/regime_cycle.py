# -*- coding: utf-8 -*-
"""build/regime_cycle.py — 경기 사이클 곡선 위의 좌표를 굽는다 → data/regime_cycle.json

## 왜 별도 스크립트인가

`refresh_regime.py` 는 FRED_API_KEY 가 있어야 돌고 그 키는 Actions 시크릿에만 있다.
이 파일은 **이미 구워진 data/regime.json 만 읽어** 파생값을 만든다 — 네트워크가 필요 없어
아무 PC 에서나 돌고, 화면을 고칠 때마다 곧바로 다시 구울 수 있다.
⚠ 그래서 refresh-regime 워크플로에서 refresh_regime.py **뒤에** 반드시 같이 돌려야 한다.
  안 그러면 국면은 바뀌었는데 곡선 위 점은 어제 자리에 남는다.

## 곡선 위 위치를 무엇으로 정하나 — 🚨 이건 실측이 아니라 교과서다

성장×물가 3×3 에서 나온 7개 이름을 사이클 한 바퀴에 늘어놓는 순서는 **통념**이다:

    침체(바닥) → 골디락스(확장·저물가) → 회복(확장·물가안정) → 과열(확장·고물가, 정점)
    → 스태그플레이션(둔화·고물가) → 후기사이클(둔화·물가안정) → 연착륙(둔화·저물가) → 다시 바닥

물가가 성장을 뒤따라 오르고 뒤따라 내린다는 전제에서 나온 배열이고, 이 랩이 검정한 것이
아니다. 히어로 카드가 '교과서적 대응'에 이미 같은 딱지를 붙이고 있다(refresh_regime.py MATRIX).

🚨 **이 랩의 212개월은 이 순서대로 돌지 않는다.** 실측:
     · 전이 32건이 순서쌍 14개에 흩어져 있고 가장 많은 쌍이 5건 — 방향을 판정할 표본이 없다
     · 이웃 쌍이 대칭이다: 골디락스↔회복 5:5 · 회복↔후기 4:3
     · 런 33개 중 12개가 1개월, 25개가 6개월 미만
   그래서 이 파일은 곡선을 '경로'로 팔지 않는다. 최근 24개월 점을 **같은 곡선 위에 같이**
   찍어서, 점들이 순서대로 나아가지 않는다는 사실을 그림 안에서 보이게 한다.

## 섹터를 곡선에 못 얹는 이유 (레퍼런스 그림에는 있다)

증권사 도표는 국면마다 유리한 업종을 곡선에 붙인다. 이 랩 자료로 그걸 하면 **잡음을
배치한다** — 11개 섹터 전부 '월평균이 가장 높았던 국면'이 표본 20개월 미만 구간
(연착륙 13개월 · 후기사이클 7개월)에 걸린다. 그래서 섹터 배치는 만들지 않는다.
국면별 성과는 이미 아래 표에 표본 수와 함께 있고, 그게 정직한 자리다.

    python build/regime_cycle.py
"""
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
SRC = os.path.join(DATA, "regime.json")
OUT = os.path.join(DATA, "regime_cycle.json")

# 사이클 한 바퀴에서의 자리(0=바닥, 0.5=정점, 1=다시 바닥).
# ⚠ 이 숫자는 통념이다. 바꾸려면 위 독스트링의 근거부터 바꿀 것.
PHASE = [
    ("Recession",   "침체",       0.00, "성장 CONTRACTION"),
    ("Goldilocks",  "골디락스",    0.16, "확장 · 저물가"),
    ("Recovery",    "회복",       0.32, "확장 · 물가 안정"),
    ("Overheating", "과열",       0.50, "확장 · 고물가"),
    ("Stagflation", "스태그플레이션", 0.64, "둔화 · 고물가"),
    ("LateCycle",   "후기사이클",   0.78, "둔화 · 물가 안정"),
    ("SoftLanding", "연착륙",     0.90, "둔화 · 저물가"),
]
POS = {k: p for k, _ko, p, _d in PHASE}

# 곡선 위 네 구획 — 레퍼런스(침체기·회복기·호황기·후퇴기)와 같은 나눔.
BANDS = [(0.00, 0.24, "침체·바닥"), (0.24, 0.46, "회복"),
         (0.46, 0.70, "확장·정점"), (0.70, 1.00, "둔화·후퇴")]

RECENT = 24


def main():
    if not os.path.exists(SRC):
        print("없음:", SRC)
        return 1
    d = json.load(io.open(SRC, encoding="utf-8"))
    hist = d.get("history") or []
    if not hist:
        print("history 가 비어 있다 — 굽지 않는다")
        return 1

    seq = [x["r"] for x in hist]

    # ── 지금 ────────────────────────────────────────────────────────────
    cur = (d.get("regime") or {}).get("label")
    if cur != seq[-1]:
        # 🚨 히어로와 이력 마지막이 다르면 곡선이 어느 쪽을 가리켜야 할지 알 수 없다.
        #   조용히 한쪽을 고르지 않는다 — 굽기를 멈춘다.
        print("불일치: regime.label=%s 인데 history 마지막=%s — 굽지 않는다" % (cur, seq[-1]))
        return 2
    if cur not in POS:
        print("모르는 국면 이름: %s — PHASE 에 추가할 것" % cur)
        return 2

    # ── 지금 국면이 몇 달째인가 ──────────────────────────────────────────
    run = 1
    for x in reversed(seq[:-1]):
        if x == cur:
            run += 1
        else:
            break

    # ── 최근 N개월의 자리 ────────────────────────────────────────────────
    recent = []
    for i, x in enumerate(hist[-RECENT:]):
        r = x["r"]
        if r not in POS:
            continue
        recent.append({"dt": x["dt"][:7], "r": r, "pos": POS[r],
                       "age": len(hist[-RECENT:]) - 1 - i})   # 0 = 가장 최근

    # ── 이 곡선을 '경로'로 읽으면 안 되는 근거를 같이 굽는다 ──────────────
    trans = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    pairs = {}
    for a, b in zip(seq, seq[1:]):
        if a != b:
            pairs["%s→%s" % (a, b)] = pairs.get("%s→%s" % (a, b), 0) + 1
    runs, c, n = [], seq[0], 1
    for x in seq[1:]:
        if x == c:
            n += 1
        else:
            runs.append(n); c = x; n = 1
    runs.append(n)
    rec = [x["r"] for x in hist[-RECENT:]]
    # 곡선 순서대로 '앞으로' 간 전이가 몇 건인가 — 통념이 맞다면 이 값이 커야 한다.
    fwd = back = 0
    for a, b in zip(seq, seq[1:]):
        if a == b or a not in POS or b not in POS:
            continue
        dp = (POS[b] - POS[a]) % 1.0
        if 0 < dp <= 0.5:
            fwd += 1
        else:
            back += 1

    months = {}
    for x in seq:
        months[x] = months.get(x, 0) + 1

    # 최근 N개월이 각 자리에 몇 번 있었나 — 곡선 위에 겹쳐 찍는 대신 이 수를 뱃지로 낸다.
    # 🚨 점을 겹쳐 찍으면 12개가 한 점으로 보여 '한 자리에 계속 있었다'로 읽힌다.
    #   실제로는 최근 24개월이 여섯 자리에 흩어져 있다 — 그 사실이 이 그림의 요점이다.
    rmonths = {}
    for x in rec:
        rmonths[x] = rmonths.get(x, 0) + 1

    out = {
        "note": ("경기 사이클 곡선 위의 자리. 🚨 곡선의 순서는 통념이고 이 랩이 검정한 것이 아니다 — "
                 "실제 이력은 이 순서대로 돌지 않는다(아래 drift 참조). "
                 "만든 곳 build/regime_cycle.py, 원자료 data/regime.json."),
        "as_of": d.get("as_of"),
        "src_generated": d.get("as_of"),
        "order_basis": "통념(성장×물가 매트릭스의 관용적 배열) — 실측 아님",
        "phases": [{"k": k, "ko": ko, "pos": p, "desc": ds,
                    "months": months.get(k, 0), "recent": rmonths.get(k, 0)}
                   for k, ko, p, ds in PHASE],
        "bands": [{"a": a, "b": b, "ko": ko} for a, b, ko in BANDS],
        "now": {"r": cur, "ko": dict((k, ko) for k, ko, _p, _d in PHASE)[cur],
                "pos": POS[cur], "run": run, "dt": hist[-1]["dt"][:7]},
        "recent": recent,
        "recent_n": len(recent),
        "drift": {
            "trans": trans, "n_months": len(seq),
            "pairs": len(pairs), "pairs_max": max(pairs.values()) if pairs else 0,
            "runs": len(runs), "runs_one": sum(1 for x in runs if x == 1),
            "runs_lt6": sum(1 for x in runs if x < 6),
            "fwd": fwd, "back": back,
            "recent_changes": sum(1 for a, b in zip(rec, rec[1:]) if a != b),
            "recent_labels": len(set(rec)),
        },
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    dr = out["drift"]
    print("→ %s" % OUT)
    print("   지금 %s(%s) · 곡선 위 %.2f · %d개월째" % (cur, out["now"]["ko"], POS[cur], run))
    print("   최근 %d개월 %d개 자리 · 이름 %d종 · 그 사이 전환 %d회"
          % (RECENT, len(recent), dr["recent_labels"], dr["recent_changes"]))
    print("   ⚠ 곡선 순서대로 나아간 전이 %d건 · 거꾸로 간 전이 %d건 — 통념이 이력을 못 설명한다"
          % (dr["fwd"], dr["back"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
