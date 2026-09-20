# -*- coding: utf-8 -*-
"""build/single_table.py — 단일 신호 여덟을 **제대로** 나란히 잰다.

🚨 combo.py 의 ⓐ 블록에 버그가 있었다. 거기 run() 이

      sc = np.nansum(행 × 가중치) / (그 종목이 가진 신호 수)

  로 점수를 냈는데, **단일 신호를 잴 때도 그 나눗셈이 걸린다.**
  신호 8개를 가진 종목은 자기 값을 8로, 3개인 종목은 3으로 나눈 값으로 정렬된다.
  결합에서는 「평균」이라 맞지만 **단일에서는 횡단면 순위를 통째로 망가뜨린다.**
  실측: 그 방식이 Mom 을 +0.447%/월로 냈는데, 나눗셈 없이 재면 아래 표가 나온다.

여기서는 신호마다 **그 신호를 가진 종목만** 후보로 두고 그 값으로만 정렬한다.
그것이 「단일 신호 성적」의 정의다.

  python build/single_table.py
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
OUT = os.path.join(DATA, "_single_table.json")
MIN_POOL, MIN_N = 30, 10


def main():
    import combo as C
    src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "combo.py"),
                  encoding="utf-8").read()
    body = src.split("    # ── 실행기 ──")[0].split("def main():", 1)[1]
    ns = {k: getattr(C, k) for k in dir(C) if not k.startswith("__")}
    ns.update({"np": np, "pd": pd, "io": io, "json": json, "os": os, "sys": sys,
               "DATA": DATA, "MIN_POOL": MIN_POOL, "MIN_N": MIN_N, "SIGS": C.SIGS,
               "glob": __import__("glob")})
    exec(compile("\n".join(l[4:] if l.startswith("    ") else l for l in body.split("\n")),
                 "panel", "exec"), ns)
    panel, ms, M, MR, CAP = ns["panel"], ns["ms"], ns["M"], ns["MR"], ns["CAP"]

    def tt(x):
        x = x[np.isfinite(x)]
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 3 else np.nan

    def nw(x, lag=6):
        x = np.asarray(x, float); x = x[np.isfinite(x)]
        m = len(x); d = x - x.mean()
        var = float((d * d).sum() / m)
        for k in range(1, min(lag, m - 1) + 1):
            var += 2 * (1 - k / (lag + 1.0)) * float((d[k:] * d[:-k]).sum() / m)
        return float(x.mean() / np.sqrt(var / m)) if var > 0 else np.nan

    def run(col, weight="cap", hold=1, want_months=False):
        ls, pool, mos = [], [], []
        for m in ms:
            g = panel[m].dropna(subset=[col])          # 그 신호를 가진 종목만
            pool.append(len(g))
            if len(g) < MIN_POOL:
                continue
            n = max(MIN_N, int(round(len(g) / 10)))
            hi = list(g.sort_values(col, ascending=False).t.head(n))
            lo = list(g.sort_values(col).t.head(n))
            nx = [x for x in M.index if x > m][:hold]
            if len(nx) < hold:
                break

            def ret(names):
                if weight == "cap":
                    w = CAP.loc[m, names].astype(float)
                    w = w / w.sum() if np.isfinite(w).all() and w.sum() > 0 else \
                        pd.Series(1.0 / len(names), index=names)
                else:
                    w = pd.Series(1.0 / len(names), index=names)
                return float(sum((w * MR.loc[x, names].astype(float).fillna(0)).sum()
                                 for x in nx)) / hold
            ls.append(ret(hi) - ret(lo)); mos.append(str(m))
        return (np.array(ls), np.array(pool), mos) if want_months else (np.array(ls), np.array(pool))

    print("\n■ 단일 신호 여덟 — 시점정확 · 섹터중립 · 그 신호를 가진 종목의 십분위")
    print("   %-9s %9s %7s %7s %9s %9s %7s"
          % ("신호", "월 롱숏", "t", "NW t", "동일가중", "12개월", "후보"))
    res, series = {}, {}
    for c in C.SIGS:
        a, pool, _mo = run(c, want_months=True)
        series[c] = {"months": _mo, "ls": [float(x) for x in a]}
        if len(a) < 10:
            print("   %-9s 측정 불가" % c); continue
        b, _ = run(c, weight="ew")
        d, _ = run(c, hold=12)
        med = int(np.median(pool[pool > 0]))
        res[c] = {"mean_pct": float(a.mean()) * 100, "t": tt(a), "nw_t": nw(a),
                  "ew_pct": float(b.mean()) * 100, "h12_pct": float(d.mean()) * 100,
                  "pool_med": med, "n": len(a)}
        print("   %-9s %+8.3f%% %7.2f %7.2f %+8.3f%% %+8.3f%% %7d"
              % (c, res[c]["mean_pct"], res[c]["t"], res[c]["nw_t"],
                 res[c]["ew_pct"], res[c]["h12_pct"], med))

    pos = [c for c in res if res[c]["mean_pct"] > 0]
    print("\n   양수 %d / %d · t 2 이상 %d개"
          % (len(pos), len(res), sum(1 for c in res if abs(res[c]["t"]) >= 2)))

    # ── 원천 태그 커버리지 ────────────────────────────────────────────────
    # 🚨 이 표의 신호 절반은 어제 새로 받은 SEC 확장 태그(`data/fxe/`)에서 온다.
    #   그 수집의 커버리지 기록이 `data/facts_ext.json` 인데, 판정 스크립트들이
    #   `data/fxe/*.json` 을 직접 읽어서 **그 기록을 아무도 안 보고 있었다**
    #   (`build/audit_unbuilt.py` 가 «읽는 곳 없는 산출물» 로 잡았다).
    #   커버리지는 장식이 아니라 **F6 관문의 눈금**이다 — 실측으로
    #   커버 98.8%(tax) → 섹터차 +2.50%p 통과 · 80.2%(sga) → +4.89%p 걸림이었고,
    #   그 F6 이 실은 섹터를 재고 있었다(AUDIT-2026-09-19-F6SECTOR).
    #   **커버가 낮은 태그는 그 자체로 판정을 흔든다. 그래서 표 옆에 함께 찍는다.**
    cov_ext = {}
    for f, lbl in (("facts_ext.json", "오늘의 518종"), ("facts_ext_pit.json", "편출 종목")):
        try:
            m = json.load(io.open(os.path.join(DATA, f), encoding="utf-8"))
        except Exception:
            continue
        cov_ext[f] = {"cov": m.get("cov") or {}, "labels": m.get("labels") or {},
                      "n_co": m.get("n_co"), "pit_kind": m.get("pit_kind"),
                      "coverage_of_gone": m.get("coverage_of_gone")}
        cv = sorted((m.get("cov") or {}).items(), key=lambda x: x[1])
        print("\n■ 원천 태그 커버 — %s (%s · %d사)" % (lbl, f, m.get("n_co") or 0))
        print("   " + " · ".join("%s %.0f%%" % (k, v) for k, v in cv))
        low = [k for k, v in cv if v < 50]
        if low:
            print("   ⚠ 커버 50%% 미만: %s — 이 태그를 쓰는 규칙은 F6 위험이 크다"
                  % " · ".join(low))
        if m.get("pit_kind") == "partial":
            print("   ⚠ 이 다리는 partial 이다 — 편출 %d종 중 %.0f%%만 덮는다."
                  % (m.get("n_gone") or 0, m.get("coverage_of_gone") or 0))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"note": "단일 신호 성적의 정본. combo.py 의 ⓐ 블록은 신호 수로 나누는 버그가 있었다.",
         "rows": res, "series": series, "tag_coverage": cov_ext},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
