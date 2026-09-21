# -*- coding: utf-8 -*-
"""build/analog.py — 지금과 «흐름이 닮은» 과거 달을 찾는다 → data/_analog.json

무엇을. 한 달의 상태가 아니라 **3개월 궤적**(전전달·전달·이번달)으로 닮은 달을 찾는다.
  «지금 유가가 오르고 금리가 오르고 변동성은 낮다» 같은 이야기를 한 점이 아니라
  선(線)으로 맞춰 보는 것이다.

🚨 그리고 **닮은 달을 찾는 것만으로는 아무 값이 없다.** 그래서 같은 파일에서 검정한다 —
   「닮은 달들의 다음 달에 잘 갔던 전략」이 실제 다음 달을 맞히나?
   대조군은 **그냥 전 구간 최다 진입 전략**이다(아무 정보도 안 쓰는 쪽).
   그것을 못 이기면 유사도 검색은 이야기일 뿐이다.

⚠ 선견 금지 — 달 t 의 이웃은 **t 보다 앞선 창**에서만 찾고, 그 이웃의 «다음 달»도
   t 보다 앞이어야 한다. 안 그러면 미래를 보고 이웃을 고르게 된다.
⚠ 여기서 백테스트를 다시 돌리지 않는다. data/_month_map.json 하나만 읽는다.

  python build/analog.py
  python build/analog.py --k 8
"""
from __future__ import annotations
import io, json, os, statistics as st, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_analog.json")

W = 3          # 창 길이(개월) — 전전달·전달·이번달
K = 5          # 이웃 수
# 궤적을 만들 변수. 🚨 수준(level)과 변화(change)를 섞는다 — 둘 다 흐름의 일부다.
FEAT = [("spx", "S&P 월수익"), ("ndx", "NDX 월수익"), ("vol", "변동성"),
        ("disp", "종목 분산"), ("rate12", "금리 12M 변화"),
        ("breadth12", "시장 폭"), ("dconc12", "집중 12M 변화")]


def zscore(rows, key):
    v = [r.get(key) for r in rows if r.get(key) is not None]
    if len(v) < 12:
        return None, None
    m = st.mean(v)
    s = st.pstdev(v) or 1.0
    return m, s


def vec(rows, i, Z):
    """달 i 로 끝나는 W개월 창의 z-점수 벡터. 결측이 있으면 None."""
    out = []
    for k in range(i - W + 1, i + 1):
        if k < 0:
            return None
        for key, _ko in FEAT:
            v = rows[k].get(key)
            if v is None:
                return None
            m, s = Z[key]
            out.append((v - m) / s)
    return out


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** .5


def main() -> int:
    k_arg = K
    if "--k" in sys.argv:
        k_arg = int(sys.argv[sys.argv.index("--k") + 1])
    D = json.load(io.open(os.path.join(DATA, "_month_map.json"), encoding="utf-8"))
    rows = D["months"]
    n = len(rows)
    Z = {key: zscore(rows, key) for key, _ in FEAT}
    if any(v[0] is None for v in Z.values()):
        raise SystemExit("표본이 모자라 z-점수를 못 낸다")
    V = [vec(rows, i, Z) for i in range(n)]

    # ── 지금 창의 이웃 ──────────────────────────────────────────────────
    cur = n - 1
    cand = [(dist(V[cur], V[j]), j) for j in range(n)
            if V[j] is not None and j <= cur - W]       # 창이 안 겹치게
    cand.sort()
    near = []
    for d, j in cand[:k_arg]:
        nxt = rows[j + 1] if j + 1 < n else None
        near.append({
            "m": rows[j]["m"], "dist": round(d, 3),
            "window": [rows[j - 2]["m"], rows[j - 1]["m"], rows[j]["m"]],
            "spx3": [rows[j - 2]["spx"], rows[j - 1]["spx"], rows[j]["spx"]],
            "label": rows[j]["label"],
            "next_m": nxt["m"] if nxt else None,
            "next_spx": nxt["spx"] if nxt else None,
            "next_top": [z["name"] for z in (nxt["top"] if nxt else [])[:5]],
        })

    # ── 🚨 검정 — 이웃이 다음 달을 맞히나 ───────────────────────────────
    # 달 t 마다: t 보다 앞선 창에서 이웃 k 개를 찾고, 그 이웃들의 «다음 달 상위5» 를
    # 모아 가장 자주 나온 5개를 뽑는다. 그것이 t 의 실제 상위5 와 몇 개 겹치나.
    # 대조군 ①: 전 구간 최다 진입 5개(아무 정보도 안 씀 · 단 t 이전만 센다)
    # 대조군 ②: 무작위 5개
    hit_a, hit_b, hit_r, cnt = 0, 0, 0, 0
    for t in range(W + 12, n):
        if V[t] is None:
            continue
        pool = [(dist(V[t], V[j]), j) for j in range(n)
                if V[j] is not None and j + 1 < t and j <= t - W]
        if len(pool) < k_arg:
            continue
        pool.sort()
        cA = {}
        for _d, j in pool[:k_arg]:
            for z in rows[j + 1]["top"][:5]:
                cA[z["sid"]] = cA.get(z["sid"], 0) + 1
        pickA = {s for s, _ in sorted(cA.items(), key=lambda z: -z[1])[:5]}
        cB = {}
        for j in range(t):
            for z in rows[j]["top"][:5]:
                cB[z["sid"]] = cB.get(z["sid"], 0) + 1
        pickB = {s for s, _ in sorted(cB.items(), key=lambda z: -z[1])[:5]}
        act = {z["sid"] for z in rows[t]["top"][:5]}
        hit_a += len(pickA & act); hit_b += len(pickB & act)
        hit_r += 5 * 5 / max(1, rows[t]["n"])          # 무작위 기대 겹침
        cnt += 1

    test = {"n_months": cnt, "k": k_arg,
            "analog_hit": hit_a / cnt if cnt else None,
            "always_hit": hit_b / cnt if cnt else None,
            "random_hit": hit_r / cnt if cnt else None}

    # ── 둘째 질문 — 이웃이 **시장 방향**은 맞히나 ─────────────────────────
    # 🚨 위 검정과 다른 질문이다(전략이 아니라 지수). 유사도 검색의 표준 용법이라
    #   한 번은 봐야 공정하다. 문턱을 뒤에 고치지 않는다 — 부호 적중률과 기준선만 본다.
    sgn_ok, sgn_n, base_up, errs = 0, 0, 0, []
    for t in range(W + 12, n):
        if V[t] is None or rows[t].get("spx") is None:
            continue
        pool = [(dist(V[t], V[j]), j) for j in range(n)
                if V[j] is not None and j + 1 < t and j <= t - W]
        if len(pool) < k_arg:
            continue
        pool.sort()
        pred = st.mean([rows[j + 1]["spx"] for _d, j in pool[:k_arg]
                        if rows[j + 1].get("spx") is not None])
        act = rows[t]["spx"]
        sgn_n += 1
        if (pred >= 0) == (act >= 0):
            sgn_ok += 1
        if act >= 0:
            base_up += 1
        errs.append(abs(pred - act))
    test["dir_acc"] = sgn_ok / sgn_n if sgn_n else None
    test["dir_base"] = max(base_up, sgn_n - base_up) / sgn_n if sgn_n else None
    test["dir_mae"] = st.mean(errs) if errs else None
    test["dir_n"] = sgn_n

    # ── 이웃이 «가깝기는 한가» — 거리 분포 ───────────────────────────────
    alld = sorted(d for d, _j in cand)
    test["dist_near"] = round(alld[0], 3) if alld else None
    test["dist_p10"] = round(alld[len(alld) // 10], 3) if alld else None
    test["dist_median"] = round(alld[len(alld) // 2], 3) if alld else None

    doc = {"note": "3개월 궤적으로 닮은 달을 찾는다. **검정을 같이 싣는다** — "
                   "닮은 달을 찾는 것만으로는 값이 없다.",
           "window": W, "k": k_arg, "feat": [k for k, _ in FEAT],
           "now": {"m": rows[cur]["m"],
                   "window": [rows[cur - 2]["m"], rows[cur - 1]["m"], rows[cur]["m"]],
                   "spx3": [rows[cur - 2]["spx"], rows[cur - 1]["spx"], rows[cur]["spx"]],
                   "label": rows[cur]["label"]},
           "near": near, "test": test}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    nw = doc["now"]
    print("지금 창 %s (S&P %s)" % (" → ".join(nw["window"]),
                                " → ".join("%+.1f" % v for v in nw["spx3"])))
    print("  %s" % nw["label"])
    print("\n══ 흐름이 닮은 과거 %d달 ══" % k_arg)
    for z in near:
        print("\n  ▸ %s  (거리 %.2f)  S&P %s"
              % (" → ".join(z["window"]), z["dist"],
                 " → ".join("%+.1f" % v for v in z["spx3"])))
        print("     %s" % z["label"])
        print("     그 다음 달 %s: S&P %+.1f%%" % (z["next_m"], z["next_spx"]))
        print("       상위: %s" % " · ".join(s[:24] for s in z["next_top"][:3]))

    print("\n" + "=" * 66)
    print("🚨 검정 — 이웃이 다음 달 상위5 를 맞히나 (달 %d개)" % test["n_months"])
    print("  이웃 기반 추천     평균 %.2f / 5 개 적중" % test["analog_hit"])
    print("  전 구간 최다 5개   평균 %.2f / 5 개 적중  ← 아무 정보도 안 쓰는 대조군"
          % test["always_hit"])
    print("  무작위 5개         평균 %.2f / 5 개 적중" % test["random_hit"])
    d = test["analog_hit"] - test["always_hit"]
    print("\n  이웃이 대조군보다 %+.2f 개 더 맞힌다 — %s"
          % (d, "쓸 값이 있다" if d > 0.3 else "**대조군보다 못하다**" if d < 0
             else "**사실상 차이 없다**"))

    print("\n🚨 둘째 질문 — 이웃이 **시장 방향**은 맞히나 (달 %d개)" % test["dir_n"])
    print("  부호 적중 %.1f%%  ·  늘 한 방향으로 찍기 %.1f%%  ·  차이 %+.1f%%p"
          % (test["dir_acc"] * 100, test["dir_base"] * 100,
             (test["dir_acc"] - test["dir_base"]) * 100))
    print("  월수익 예측의 평균 절대오차 %.2f%%p" % test["dir_mae"])

    print("\n⚠ 이웃이 «가깝기는 한가» — 거리 분포(지금 창 기준)")
    print("  가장 가까운 %.2f · 하위 10%% 경계 %.2f · 중앙 %.2f"
          % (test["dist_near"], test["dist_p10"], test["dist_median"]))
    print("  (21차원 z-점수 공간이다. 가장 가까운 것이 중앙의 절반도 안 되면 «닮았다»고 "
          "부를 만하고, 비슷하면 그냥 «덜 먼» 것이다.)")
    print("\n→ %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
