# -*- coding: utf-8 -*-
"""build/strength_table.py — 규칙마다 «무엇을 잘하나» 를 축별로 뽑는다.

왜 있나
   «랩에 전략이 189개» 라는 말은 목록이지 쓸모가 아니다. 성적만 줄 세우면
   한 축(초과수익)으로만 보게 되고, **싸게 굴러가는 것 · 낙폭을 줄이는 것 ·
   생존편향에 강한 것 · 남들과 안 겹치는 것**이 전부 같은 칸에 묻힌다.

   그래서 축을 여섯으로 나눠 각각의 «가장 나은 것» 을 뽑는다.
   ⚠ 이 표는 **추천이 아니다.** 랩의 다중검정 문턱(t 3.3~3.4)을 넘은 규칙은 0개이고,
     여기 나오는 것도 전부 «측정만» 등급이다. 읽는 법은 하나 —
     **«이 축이 필요하면 이 규칙을 먼저 본다»** 는 색인이다.

축 여섯
   ① 초과수익      excess_cagr
   ② 위험조정      d_sharpe(매수후보유 대비 샤프 개선)
   ③ 싸게 굴러감   turnover(낮을수록)
   ④ 낙폭 방어     pit.mdd 가 벤치보다 나은 정도
   ⑤ 생존편향 내성 retro − pit 가 작을수록(부풀림이 적다)
   ⑥ 안 겹침       incr.one.corr 가 낮을수록(가장 가까운 이웃과도 안 닮았다)
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def main():
    rep = json.load(io.open(os.path.join(DATA, "strategy_report.json"), encoding="utf-8"))
    rows = []
    for it in rep["items"]:
        p = (it.get("pit") or {}).get("pit") or {}
        r = (it.get("pit") or {}).get("retro") or {}
        inc = ((it.get("incr") or {}).get("one") or {})
        rows.append({
            "sid": it["sid"], "name": it.get("name") or "", "fam": it.get("family"),
            "role": it.get("role"), "ex": it.get("excess_cagr"), "t": it.get("t"),
            "ds": it.get("d_sharpe"), "turn": it.get("turnover"),
            "pit_ex": p.get("excess"), "pit_t": p.get("t"), "pit_ds": p.get("d_sharpe"),
            "mdd": p.get("mdd"), "bias": (r.get("excess") - p.get("excess"))
                if (r.get("excess") is not None and p.get("excess") is not None) else None,
            "corr": inc.get("corr"), "vs": inc.get("vs"),
        })

    def top(key, n=6, rev=True, need=None, lab=""):
        v = [x for x in rows if isinstance(x.get(key), (int, float))]
        if need:
            v = [x for x in v if need(x)]
        v.sort(key=lambda x: x[key], reverse=rev)
        print("\n■ %s" % lab)
        for x in v[:n]:
            print("   %-15s %-40s %s" % (x["sid"], x["name"][:40], fmt(x, key)))

    def fmt(x, key):
        s = {"ex": "초과 %+.2f%%p · t %s" % (x["ex"] or 0, _t(x["t"])),
             "ds": "Δ샤프 %+.3f · 초과 %+.2f%%p" % (x["ds"] or 0, x["ex"] or 0),
             "turn": "회전 %.2f회 · 초과 %+.2f%%p" % (x["turn"] or 0, x["ex"] or 0),
             "pit_ds": "PIT Δ샤프 %+.3f · PIT 초과 %+.2f%%p (t %s)"
                       % (x["pit_ds"] or 0, x["pit_ex"] or 0, _t(x["pit_t"])),
             "nbias": "부풀림 %+.2f%%p · PIT 초과 %+.2f%%p" % (-(x["bias"] or 0), x["pit_ex"] or 0),
             "ncorr": "이웃 상관 %+.2f (%s)" % (x["corr"] or 0, (x["vs"] or "")[:26])}
        return s.get(key, "")

    print("랩의 살아 있는 규칙 %d개 — 축별로 «무엇을 잘하나»" % len(rows))
    top("ex", 6, True, None, "① 초과수익이 가장 큰 것")
    top("ds", 6, True, None, "② 위험조정(샤프 개선)이 가장 큰 것")
    top("turn", 6, False, lambda x: (x["ex"] or -99) > 0,
        "③ 가장 싸게 굴러가는 것 (초과가 양수인 것 중 회전 최저)")
    top("pit_ds", 6, True, None, "④ 시점정확(PIT)으로도 샤프가 가장 오르는 것")

    v = [x for x in rows if isinstance(x.get("bias"), (int, float))
         and isinstance(x.get("pit_ex"), (int, float)) and x["pit_ex"] > 0]
    v.sort(key=lambda x: x["bias"])
    print("\n■ ⑤ 생존편향에 가장 강한 것 (소급 대비 PIT 이 덜 깎이거나 오히려 나은 것)")
    for x in v[:6]:
        print("   %-15s %-40s %s" % (x["sid"], x["name"][:40], fmt(x, "nbias")))

    v = [x for x in rows if isinstance(x.get("corr"), (int, float))
         and isinstance(x.get("ex"), (int, float)) and x["ex"] > 0]
    v.sort(key=lambda x: abs(x["corr"]))
    print("\n■ ⑥ 가장 안 겹치는 것 (가장 가까운 이웃과도 상관이 낮다)")
    for x in v[:6]:
        print("   %-15s %-40s %s" % (x["sid"], x["name"][:40], fmt(x, "ncorr")))

    print("\n■ 계열·역할별 머릿수")
    agg = {}
    for x in rows:
        agg.setdefault((x["fam"], x["role"]), []).append(x)
    for k, v2 in sorted(agg.items(), key=lambda kv: -len(kv[1])):
        pos = sum(1 for x in v2 if (x["ex"] or 0) > 0)
        print("   %-12s %-12s %3d개 · 초과 양수 %d" % (k[0], k[1], len(v2), pos))
    return 0


def _t(v):
    return "%.2f" % v if isinstance(v, (int, float)) else "—"


if __name__ == "__main__":
    raise SystemExit(main())
