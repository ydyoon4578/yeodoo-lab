# -*- coding: utf-8 -*-
"""build/combo2.py — 커버를 맞춘 결합 (PREREG-2026-09-19-COMBO2 · 계산 전 a2adc83)

🚨 핵심: 묶음 안 신호를 **하나도 빠짐없이** 가진 종목만 후보로 둔다.
   그러면 모든 종목이 같은 수의 신호를 갖고, 어느 축도 결손으로 목소리를 잃지 않는다.

  ⒜ 가격 Mom · negOsc · negResid
  ⒝ 재무 Cta · OL · TaxSurp · OCAT · negNOA

둘 다 내고 둘 다 판정한다. 어느 쪽이 좋은지 보고 고르지 않는다.

  python build/combo2.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_combo2.json")
MIN_POOL, MIN_N, NRW, SEED = 30, 10, 200, 20260919
GROUPS = {"⒜가격": ["Mom", "negOsc", "negResid"],
          "⒝재무": ["Cta", "OL", "TaxSurp", "OCAT", "negNOA"]}


def main():
    # combo.py 의 패널 구성을 그대로 쓴다 — 두 벌로 만들면 반드시 갈린다.
    import combo as C
    src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "combo.py"),
                  encoding="utf-8").read()
    body = src.split("    # ── 실행기 ──")[0]
    body = body.split("def main():", 1)[1]
    ns = {k: getattr(C, k) for k in dir(C) if not k.startswith("__")}
    ns.update({"np": np, "pd": pd, "io": io, "json": json, "os": os, "sys": sys,
               "DATA": DATA, "MIN_POOL": MIN_POOL, "MIN_N": MIN_N, "SIGS": C.SIGS,
               "glob": __import__("glob")})
    exec(compile("\n".join(l[4:] if l.startswith("    ") else l
                           for l in body.split("\n")), "combo_panel", "exec"), ns)
    panel, ms, M, MR, CAP = ns["panel"], ns["ms"], ns["M"], ns["MR"], ns["CAP"]
    print()

    def tt(x):
        x = x[np.isfinite(x)]
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 3 else np.nan

    def run(cols, w, weight="cap"):
        """묶음 안 신호를 전부 가진 종목만 후보."""
        ls, pool = [], []
        for m in ms:
            g = panel[m].dropna(subset=cols)          # 🚨 전부 가진 종목만
            pool.append(len(g))
            if len(g) < MIN_POOL:
                continue
            sc = (g[cols].to_numpy() * np.asarray(w, float)).sum(axis=1)
            gg = g.assign(sc=sc)
            n = max(MIN_N, int(round(len(gg) / 10)))
            hi = list(gg.sort_values("sc", ascending=False).t.head(n))
            lo = list(gg.sort_values("sc").t.head(n))
            nx = [x for x in M.index if x > m][:1]
            if not nx:
                break

            def ret(names):
                if weight == "cap":
                    ww = CAP.loc[m, names].astype(float)
                    ww = ww / ww.sum() if np.isfinite(ww).all() and ww.sum() > 0 else \
                        pd.Series(1.0 / len(names), index=names)
                else:
                    ww = pd.Series(1.0 / len(names), index=names)
                return float((ww * MR.loc[nx[0], names].astype(float).fillna(0)).sum())
            ls.append(ret(hi) - ret(lo))
        return np.array(ls), np.array(pool)

    out, rng = {}, np.random.default_rng(SEED)
    for gname, cols in GROUPS.items():
        print("■ %s — %s" % (gname, " · ".join(cols)))
        _, pool = run(cols, np.ones(len(cols)))
        med = int(np.median(pool[pool > 0])) if (pool > 0).any() else 0
        print("   후보 중앙 %d종 (30종 미만인 달 %d / %d)"
              % (med, int((pool < MIN_POOL).sum()), len(pool)))
        if med < MIN_POOL:
            print("   → F5 측정 불가\n")
            out[gname] = {"pool_med": med, "verdict": "측정 불가"}
            continue

        # 같은 후보에서 단일 신호 다시
        single = {}
        for j, c in enumerate(cols):
            w = np.zeros(len(cols)); w[j] = 1.0
            a, _ = run(cols, w)
            single[c] = {"mean_pct": float(a.mean()) * 100, "t": tt(a), "n": len(a)}
            print("      단일 %-9s 월 %+6.3f%% (t %5.2f)" % (c, single[c]["mean_pct"], single[c]["t"]))
        best = max(single, key=lambda k: single[k]["mean_pct"])

        a_eq, _ = run(cols, np.ones(len(cols)))
        a_ew, _ = run(cols, np.ones(len(cols)), weight="ew")
        act = float(a_eq.mean()) * 100
        print("      결합(시총가중) 월 %+6.3f%% (t %5.2f · n %d)" % (act, tt(a_eq), len(a_eq)))
        print("      결합(동일가중) 월 %+6.3f%% (t %5.2f)" % (a_ew.mean() * 100, tt(a_ew)))

        rw = np.empty(NRW)
        for q in range(NRW):
            w = rng.normal(size=len(cols))
            w = w / np.linalg.norm(w) * np.sqrt(len(cols))
            rw[q] = run(cols, w)[0].mean() * 100
        pct = float((rw < act).mean()) * 100
        print("      무작위 가중 %d회 평균 %+.3f%% (sd %.3f) · 백분위 %.1f"
              % (NRW, rw.mean(), rw.std(ddof=1), pct))

        F = {"F1 롱숏 ≤ 0": act <= 0,
             "F2 묶음 안 최고 단일을 못 넘음": act <= single[best]["mean_pct"],
             "F3 무작위 가중 상위 5% 밖": pct < 95.0,
             "F4 10bp 후 ≤ 0": act - 0.20 <= 0,
             "F5 후보 중앙 30종 미만": med < MIN_POOL}
        for k, v in F.items():
            print("      %s %s" % ("❌" if v else "✅", k))
        vd = "기각" if any(F.values()) else "채택"
        print("      → %s  (최고 단일 %s %+.3f%%)\n" % (vd, best, single[best]["mean_pct"]))
        out[gname] = {"pool_med": med, "single": single, "best": best,
                      "combo_cap": {"mean_pct": act, "t": tt(a_eq), "n": len(a_eq)},
                      "combo_ew": {"mean_pct": float(a_ew.mean()) * 100, "t": tt(a_ew)},
                      "random_w": {"mean": float(rw.mean()), "sd": float(rw.std(ddof=1)),
                                   "pctile": pct},
                      "fails": {k: bool(v) for k, v in F.items()}, "verdict": vd}

    vds = [v.get("verdict") for v in out.values()]
    print("→ 종합: %s" % (" · ".join("%s %s" % (k, v.get("verdict")) for k, v in out.items())))
    if all(v == "기각" or v == "측정 불가" for v in vds):
        print("   등록서 §7-5 대로 「결합」을 완전히 닫는다.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"prereg": "PREREG-2026-09-19-COMBO2", "commit": "a2adc83",
         "groups": GROUPS, "result": out}, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
