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
K2 = 20        # 1단에서 이만큼 뽑고 2단으로 좁힌다(KBAM 모니터가 20개를 쓴다)

# ── 2단 «신호군 밖 차원» ────────────────────────────────────────────────
# 🚨 사용자 제공 자료(KBAM 시장 국면 모니터 2026-07-09 ⑤)의 설계를 가져왔다 —
#   «신호 점수가 비슷해도 눌림목이었는지 천장이었는지는 이 차원들이 가른다».
#   1단(시장상태 6변수)만으로는 2016-10(다음 달 +1.8%)과 2026-01(-5.1%)이 나란히
#   이웃으로 나온다. 실제로 내 첫 판이 그랬고 그것이 안 선 이유다.
# ⚠ «참고» 는 그 모니터의 규약을 그대로 따른다 — 천천히 변하는 배경값(금리 수준·
#   1년 수익 등)은 **표에 보여주기만 하고 날짜 선정에는 안 쓴다.** 안 그러면
#   «최근 날짜만 비슷해 보이는» 편향이 생긴다.
# ⚠ 그 모니터의 14개 중 랩에 없는 넷(선행 PER · VIX 기간구조 · EPS 리비전 · MOVE)은
#   **뺀다. 지어 채우지 않는다.**
OUT2 = [  # (키, 이름, 선정에 쓰나)
    ("d10y3m",  "10Y 금리 3개월 변화(%p)", True),
    ("hy",      "하이일드 스프레드(%)", True),
    ("vix",     "VIX", True),
    ("hi52",    "52주고점 이격(%)", True),
    ("dxy3m",   "달러 3개월 변화(%)", True),
    ("rsi14",   "RSI(14)", True),
    ("ma50",    "MA50 이격(%)", True),
    ("y10",     "10Y 금리 수준(%)", False),     # 참고 — 저금리/고금리 시대 구분
    ("t102",    "장단기 금리차(bp)", False),     # 참고
    ("r12m",    "직전 1년 수익(%)", False),      # 참고 — 과열 누적
]
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


def build_out2(months):
    """2단 차원을 달마다 만든다 — 월말 값. 없는 달은 그 칸만 None."""
    import statistics as _st
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    mac = A.get("macro") or {}
    bd, bpx = B["dates"], (B["series"]["spx"]["px"])

    def last_on_or_before(series, ym):
        """그달 말까지의 마지막 값. series 는 {날짜: 값}."""
        ks = [k for k in series if k[:7] <= ym and series[k] is not None]
        return series[max(ks)] if ks else None

    def mval(code, ym, back=0):
        s = mac.get(code) or {}
        if not back:
            return last_on_or_before(s, ym)
        y, m = int(ym[:4]), int(ym[5:7]) - back
        while m <= 0:
            m += 12; y -= 1
        return last_on_or_before(s, "%04d-%02d" % (y, m))

    # 가격 — 월말 인덱스
    me = {}
    for i, d in enumerate(bd):
        if bpx[i] is not None:
            me[d[:7]] = i
    out = {}
    for ym in months:
        i = me.get(ym)
        row = {}
        a, b = mval("DGS10", ym), mval("DGS10", ym, 3)
        row["d10y3m"] = (a - b) if (a is not None and b is not None) else None
        row["y10"] = a
        row["hy"] = mval("BAMLH0A0HYM2", ym)
        row["t102"] = (mval("T10Y2Y", ym) or 0) * 100 if mval("T10Y2Y", ym) is not None else None
        row["vix"] = mval("VIXCLS", ym)
        d0, d3 = mval("DTWEXBGS", ym), mval("DTWEXBGS", ym, 3)
        row["dxy3m"] = ((d0 / d3 - 1) * 100) if (d0 and d3) else None
        if i is not None:
            px = [v for v in bpx[max(0, i - 252):i + 1] if v is not None]
            row["hi52"] = (bpx[i] / max(px) - 1) * 100 if px else None
            row["r12m"] = (bpx[i] / px[0] - 1) * 100 if len(px) > 200 else None
            j = max(0, i - 50)
            w = [v for v in bpx[j:i + 1] if v is not None]
            row["ma50"] = (bpx[i] / (sum(w) / len(w)) - 1) * 100 if w else None
            # RSI(14) — 일간 종가
            k0 = max(0, i - 14)
            dd = [bpx[t] - bpx[t - 1] for t in range(k0 + 1, i + 1)
                  if bpx[t] is not None and bpx[t - 1] is not None]
            up = _st.mean([x for x in dd if x > 0]) if any(x > 0 for x in dd) else 0.0
            dn = -_st.mean([x for x in dd if x < 0]) if any(x < 0 for x in dd) else 0.0
            row["rsi14"] = 100 - 100 / (1 + up / dn) if dn else (100.0 if up else None)
        out[ym] = row
    return out


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

    # ── 2단 차원 ────────────────────────────────────────────────────────
    O2 = build_out2([r["m"] for r in rows])
    SEL2 = [k for k, _ko, use in OUT2 if use]
    Z2 = {}
    for k in SEL2:
        v = [O2[r["m"]].get(k) for r in rows if O2[r["m"]].get(k) is not None]
        Z2[k] = (st.mean(v), st.pstdev(v) or 1.0) if len(v) > 12 else (0.0, 1.0)

    def d2(i, j):
        """2단 거리 — 선정에 쓰는 칸만. 결측은 그 칸을 건너뛴다."""
        s, c = 0.0, 0
        for k in SEL2:
            a, b = O2[rows[i]["m"]].get(k), O2[rows[j]["m"]].get(k)
            if a is None or b is None:
                continue
            m_, sd = Z2[k]
            s += ((a - m_) / sd - (b - m_) / sd) ** 2
            c += 1
        return (s / c) ** .5 if c else None

    # ── 지금 창의 이웃 ──────────────────────────────────────────────────
    cur = n - 1
    cand = [(dist(V[cur], V[j]), j) for j in range(n)
            if V[j] is not None and j <= cur - W]       # 창이 안 겹치게
    cand.sort()
    # 🚨 2단 — 1단으로 K2 개를 뽑고, 그중 «신호군 밖 차원» 이 가장 가까운 k 개로 좁힌다.
    wide = cand[:K2]
    ref = sorted(((d2(cur, j) if d2(cur, j) is not None else 9e9, j) for _d, j in wide))
    near2 = []
    for dd2, j in ref[:k_arg]:
        nxt = rows[j + 1] if j + 1 < n else None
        near2.append({"m": rows[j]["m"], "d2": round(dd2, 3),
                      "d1": round(next(d for d, jj in wide if jj == j), 3),
                      "window": [rows[j - 2]["m"], rows[j - 1]["m"], rows[j]["m"]],
                      "next_m": nxt["m"] if nxt else None,
                      "next_spx": nxt["spx"] if nxt else None,
                      "out2": {k: O2[rows[j]["m"]].get(k) for k, _ko, _u in OUT2}})

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

    # ── 🚨 2단이 실제로 나아지게 하나 ───────────────────────────────────
    # KBAM 모니터의 주장은 «신호군 밖 차원이 천장/눌림목을 가른다» 다. 그렇다면 2단으로
    # 좁힌 이웃의 다음 달 수익이 **덜 흩어져야** 한다(같은 종류의 달만 남으므로).
    # 그것을 잰다 — 1단 K2개의 흩어짐 vs 2단 k개의 흩어짐, 그리고 방향 적중.
    sd1, sd2, ok1, ok2, c2 = [], [], 0, 0, 0
    for t in range(W + 12, n):
        if V[t] is None or rows[t].get("spx") is None:
            continue
        pool = sorted((dist(V[t], V[j]), j) for j in range(n)
                      if V[j] is not None and j + 1 < t and j <= t - W)
        if len(pool) < K2:
            continue
        w = pool[:K2]
        nx1 = [rows[j + 1]["spx"] for _d, j in w if rows[j + 1].get("spx") is not None]
        rf = sorted(((d2(t, j) if d2(t, j) is not None else 9e9, j) for _d, j in w))
        nx2 = [rows[j + 1]["spx"] for _d, j in rf[:k_arg] if rows[j + 1].get("spx") is not None]
        if len(nx1) < 8 or len(nx2) < 3:
            continue
        sd1.append(st.pstdev(nx1)); sd2.append(st.pstdev(nx2))
        act = rows[t]["spx"]
        if (st.mean(nx1) >= 0) == (act >= 0):
            ok1 += 1
        if (st.mean(nx2) >= 0) == (act >= 0):
            ok2 += 1
        c2 += 1
    test["stage2"] = {
        "n": c2,
        "sd_1stage": st.mean(sd1) if sd1 else None,
        "sd_2stage": st.mean(sd2) if sd2 else None,
        "dir_1stage": ok1 / c2 if c2 else None,
        "dir_2stage": ok2 / c2 if c2 else None,
    }

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
           "near": near, "near2": near2, "out2_now": O2[rows[cur]["m"]],
           "out2_cols": [{"k": k, "ko": ko, "use": u} for k, ko, u in OUT2],
           "test": test}
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

    s2 = test["stage2"]
    print("\n🚨 2단 — «신호군 밖 차원» 이 천장/눌림목을 가르나 (달 %d개)" % s2["n"])
    print("  1단 %d개 이웃의 다음 달 수익 흩어짐(표준편차)  %.2f%%p" % (K2, s2["sd_1stage"]))
    print("  2단 %d개로 좁힌 뒤                          %.2f%%p  (%+.2f)"
          % (k_arg, s2["sd_2stage"], s2["sd_2stage"] - s2["sd_1stage"]))
    print("  방향 적중 — 1단 %.1f%% → 2단 %.1f%%  (기준선 %.1f%%)"
          % (s2["dir_1stage"] * 100, s2["dir_2stage"] * 100, test["dir_base"] * 100))
    print("  → %s" % ("2단이 좁힌다 — 같은 종류의 달만 남는다"
                     if s2["sd_2stage"] < s2["sd_1stage"] else
                     "**2단이 오히려 더 흩어진다** — 이 자료에서는 안 가른다"))

    print("\n── 2단으로 고른 이웃(지금 창) ──")
    for z in near2:
        print("  %s  1단거리 %.2f → 2단 %.2f   다음 달 %s %+.1f%%"
              % (" → ".join(z["window"]), z["d1"], z["d2"], z["next_m"], z["next_spx"]))

    print("\n── 지금의 «신호군 밖 차원» ──")
    for k, ko_, use in OUT2:
        v = doc["out2_now"].get(k)
        print("  %-24s %8s   %s" % (ko_, "—" if v is None else "%.2f" % v,
                                    "" if use else "(참고 · 선정에 안 씀)"))

    print("\n⚠ 이웃이 «가깝기는 한가» — 거리 분포(지금 창 기준)")
    print("  가장 가까운 %.2f · 하위 10%% 경계 %.2f · 중앙 %.2f"
          % (test["dist_near"], test["dist_p10"], test["dist_median"]))
    print("  (21차원 z-점수 공간이다. 가장 가까운 것이 중앙의 절반도 안 되면 «닮았다»고 "
          "부를 만하고, 비슷하면 그냥 «덜 먼» 것이다.)")
    print("\n→ %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
