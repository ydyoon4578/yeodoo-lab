# -*- coding: utf-8 -*-
"""증분 감사 — «이 규칙이 이미 게시된 나머지에 무엇을 더하나».

배경(2026-09-11 · PREREG-2026-09-11-UNION-RESULT.md):
  §4  관문(샤프 0.5 · 회전율 10배 · 승률 50%)은 **수익을 고르지 유의성을 못 고른다** —
      게시 47종의 알파가 전체 195종의 2.08배인데 t 는 +0.44 밖에 안 오른다.
  §5  그리고 관문이 **«같은 것»을 골라 왔다** — 게시 47종 평균 쌍상관 0.714(유효 베팅 1.4)
      인데 관문에서 떨어진 148종은 0.562(1.77)로 «덜» 닮았다.
  §3  랩이 인용해 온 알파·t 는 **주간 격자·`bnav`(배당 없는 지수)** 로 잰 것이라 위로 치우쳐
      있다. 그래서 여기서는 **월말 격자 · ^GSPC + 배당보정** 만 쓴다.

재는 것 — 게시 규칙 i 마다:

    r_i = α + β·(벤치) + γ·(나머지 게시 규칙 동일가중) + ε

  **α 의 t** 가 「이 규칙이 나머지에 더하는 몫」이다.
  낮으면 그 규칙은 시장과 이미 있는 것들의 조합으로 복제된다 — 즉 **사본**이다.

🚨 **관문이 아니다 — 사용자 결정 2026-09-11: 「매 실행 수치만 로그에 남김」.**
   문턱을 걸지 않고, 목록을 고치지 않고, 잡을 죽이지도 않는다. 수만 남긴다.
   ⚠ 문턱을 걸자는 제안(t ≥ 1.5)은 **소급하면 47종 중 45종이 날아가서** 접었다.
     그리고 이 검정은 구조상 가혹하다 — 게시 47종이 서로 0.714 상관이면 각각은
     나머지로 거의 복제된다(유효 베팅 1.4 의 수학적 귀결). 정확한 독해는
     「45개가 쓸모없다」가 아니라 **「집합은 알파 t 1.83 인데 그 안의 어느 하나도
     집합에 더하지 못한다」** 이다. 그 사실을 매 실행 남겨 두는 것이 이 파일의 전부다.

산출 data/_incr_audit.json (밑줄 = 로컬 전용 · 커밋 금지).
"""
import json
import math
import os
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import union as U                      # 🚨 채점기를 복제하지 않는다 — 모집단·격자·벤치를 그대로 쓴다

MIN_MONTHS = 36                        # 이보다 짧으면 재지 않는다(수가 아니라 잡음이 된다)


def ols3(y, x1, x2):
    """y = a + b·x1 + c·x2. (a, t_a, b, c, 잔차변동성_연) — 표준 라이브러리만."""
    k = len(y)
    X = [[1.0, x1[i], x2[i]] for i in range(k)]
    XtX = [[sum(X[i][a] * X[i][b] for i in range(k)) for b in range(3)] for a in range(3)]
    Xty = [sum(X[i][a] * y[i] for i in range(k)) for a in range(3)]
    # 가우스-조던으로 역행렬과 해를 같이 구한다(3×3 이라 이걸로 충분하다)
    M = [XtX[r][:] + [1.0 if r == c else 0.0 for c in range(3)] + [Xty[r]] for r in range(3)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            return None
        M[col], M[piv] = M[piv], M[col]
        p = M[col][col]
        M[col] = [v / p for v in M[col]]
        for r in range(3):
            if r != col and M[r][col]:
                f = M[r][col]
                M[r] = [v - f * w for v, w in zip(M[r], M[col])]
    beta = [M[r][6] for r in range(3)]
    inv00 = M[0][3]
    res = [y[i] - (beta[0] + beta[1] * x1[i] + beta[2] * x2[i]) for i in range(k)]
    s2 = sum(v * v for v in res) / (k - 3)
    se_a = math.sqrt(s2 * inv00)
    return (beta[0] * 12, beta[0] / se_a, beta[1], beta[2],
            st.stdev(res) * math.sqrt(12))


def main():
    raw = U.gather()
    B = U.bench_monthly()
    grid = [m for m in U.months_between(U.START, U.END) if m in B]
    M = {s: v for s, v in ((s, U.monthly(v["dates"], v["nav"])) for s, v in raw.items()) if v}

    # 🚨 게시 목록의 원천은 data/strategy_index.json 이다 — **커밋되는 파일**.
    #   _winrate_audit.json 은 밑줄(로컬 전용)이라 러너에 없다. 그것을 읽으면 이 감사가
    #   CI 에서 조용히 «게시 0종» 으로 돌아 아무 말도 안 하게 된다.
    ix = U.load("strategy_index.json") or {"items": []}
    NM = {x["sid"]: (x.get("name") or x["sid"], x.get("role") or "") for x in ix["items"]}
    pub = [s for s in sorted(M) if s in NM]
    _absent = [x["sid"] for x in ix["items"] if x["sid"] not in M]

    rows = []
    for s in pub:
        others = [o for o in pub if o != s]
        # 그 규칙에 관측이 있는 달만. 나머지 다리도 «그 달들» 위에서만 만든다.
        ms = [m for m in grid if m in M[s]]
        ms = [m for m in ms if any(m in M[o] for o in others)]
        if len(ms) < MIN_MONTHS:
            rows.append({"sid": s, "name": NM.get(s, (s, ""))[0], "role": NM.get(s, (s, ""))[1],
                         "n": len(ms), "alpha": None, "t": None, "beta": None, "gamma": None,
                         "note": "표본 %d개월 < %d — 재지 않는다" % (len(ms), MIN_MONTHS)})
            continue
        y = [M[s][m] for m in ms]
        xb = [B[m] for m in ms]
        xo = [st.mean([M[o][m] for o in others if m in M[o]]) for m in ms]
        out = ols3(y, xb, xo)
        if out is None:
            rows.append({"sid": s, "name": NM.get(s, (s, ""))[0], "n": len(ms),
                         "alpha": None, "t": None, "note": "특이행렬"})
            continue
        a, ta, b, g, rv = out
        rows.append({"sid": s, "name": NM.get(s, (s, ""))[0], "role": NM.get(s, (s, ""))[1],
                     "n": len(ms), "alpha": a * 100, "t": ta, "beta": b, "gamma": g,
                     "resid_vol": rv * 100, "note": ""})

    rows.sort(key=lambda r: (r["t"] is None, -(r["t"] or 0)))
    res = {"note": "증분 감사 — 게시 규칙이 «나머지 게시 규칙 + 시장» 에 더하는 몫. "
                   "근거 PREREG-2026-09-11-UNION-RESULT.md §4·§5. "
                   "🚨 관문이 아니다 — 사용자 결정 2026-09-11 「매 실행 수치만 로그에 남김」.",
           "spec": "r_i = a + b·(^GSPC+배당보정) + c·(나머지 게시 동일가중), 월말 격자",
           "start": U.START, "end": U.END, "min_months": MIN_MONTHS,
           "n_published": len(pub), "absent": _absent, "rows": rows}
    with open(os.path.join(U.DATA, "_incr_audit.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    ok = [r for r in rows if r["t"] is not None]
    print("게시 %d종 · 잰 것 %d종 (월말 %s ~ %s)" % (len(pub), len(ok), U.START, U.END))
    if _absent:
        print("  ⚠ 수익 계열을 못 찾은 게시 규칙 %d종: %s"
              % (len(_absent), ", ".join(_absent)))
    print("%-20s %7s %7s %7s %7s  %s" % ("sid", "증분α", "t", "β시장", "γ나머지", "이름"))
    for r in ok:
        print("%-20s %+6.2f%%p %7.2f %7.3f %7.3f  %s"
              % (r["sid"], r["alpha"], r["t"], r["beta"], r["gamma"], r["name"][:30]))
    for r in rows:
        if r["t"] is None:
            print("%-20s %s" % (r["sid"], r["note"]))
    ts = sorted(r["t"] for r in ok)
    print("\n증분 t 분포 — 중앙 %.2f · 최고 %.2f · 최저 %.2f" % (ts[len(ts) // 2], ts[-1], ts[0]))
    for th in (1.0, 1.5, 2.0):
        print("   t < %.1f : %d종 / %d" % (th, sum(1 for v in ts if v < th), len(ts)))
    print("  ⚠ 문턱을 걸지 않는다(사용자 결정 2026-09-11) — 이 표는 기록이지 관문이 아니다.")
    print("  ⚠ 낮은 t 는 «그 규칙이 나쁘다» 가 아니라 «나머지로 복제된다» 는 뜻이다.")


if __name__ == "__main__":
    main()
