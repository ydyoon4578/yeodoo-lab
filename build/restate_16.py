# -*- coding: utf-8 -*-
"""build/restate_16.py — 페어 6종·거장겹침 10종을 **10년 창**으로 다시 읽는다(재진술).

🚨 이것은 **새 탐색이 아니다.** 손잡이를 돌려 성적을 올리려는 것이 아니라, 이 랩의
   창 상한(MAX_YEARS = 10 · 사용자 결정 2026-08-13)보다 **앞서 만들어진 두 엔진**의
   결과를 같은 창으로 옮겨 적는 일이다. restate_10y.py 와 같은 성격이다.
   두 엔진은 그동안 숨겨져 있어서 창을 다시 거는 일이 없었다 —
   페어 2010-02~ (16.5년) · 거장겹침 2013-09~ (12.9년).

🚨 **원본을 다시 굽지 않는다.** guru_overlap.json 에는 «손대지 않는다 —
   guru.html#overlap 과 진단물은 그대로다» 가 적혀 있다. 다시 구우면 다른 페이지의
   게시 수치가 바뀐다. 그래서 원본은 읽기만 하고, 이미 실려 있는 **곡선**에서
   창만 잘라 다시 잰다. guru.html#overlap 은 종전 수치를 그대로 쓴다.

⚠ 지표를 **다시 짜지 않는다.** 원 엔진의 함수를 그대로 부른다 —
   거장겹침 guru17_backtest.ann_from_monthly · 페어 pairs_backtest.stats.
   여기서 새로 짜면 같은 수를 두 벌로 계산하게 된다(이 저장소가 되풀이 밟는 결함).

앵커 — 창을 안 자르고 돌리면 원본 metrics 와 같아야 한다. 안 맞으면 소리 내어 죽는다.

  python build/restate_16.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_restate16.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
from maxyears import MAX_YEARS                                   # noqa: E402
from guru17_backtest import ann_from_monthly, capm               # noqa: E402

# 🚨 `t` 의 정의는 엔진마다 다르다. 재진술은 **각자의 정의를 그대로 따른다** —
#   안 그러면 같은 열에 다른 통계량이 섞여 세로로 비교가 안 된다.
#     거장겹침  capm(r, spx, rf) 의 **알파 t** (단순 초과 t 가 아니다)
#     페어      stats()['t_nw'] — 뉴이–웨스트 t. 대조군이 현금(0)이라 초과 = 수익이다.


def load(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


def nav_to_rets(nav, base=100.0):
    """곡선(누적 NAV) → 월(또는 일) 수익. 첫 칸은 base 대비다."""
    a = np.asarray([base] + list(nav), float)
    return a[1:] / a[:-1] - 1.0


# ══ 거장 겹침 ═══════════════════════════════════════════════════════════
def guru_rows():
    g = load("guru_overlap.json")
    RF = (load("rf_monthly.json") or {}).get("monthly") or {}
    out = {}
    for v in (g.get("variants") or []) + (g.get("tops") or []):
        cur = v.get("curve") or {}
        ms, ser = cur.get("m") or [], cur.get("s") or {}
        if not ms or not isinstance(ser, dict) or "s" not in ser:
            continue
        if v.get("rank"):
            sid = "g-overlap-top%d-%s" % (g.get("topn") or 10, v["rank"])
        else:
            _m = v.get("mode") or "eq"
            sid = ("g-overlap-k%d" % v["k"]) if _m == "eq" else ("g-overlap-k%d-%s" % (v["k"], _m))

        r_all = nav_to_rets(ser["s"])
        rf_all = np.array([RF.get(m, 0.0) for m in ms], float)
        # ── 앵커: 안 자르면 원본과 같아야 한다 ──────────────────────────
        full = ann_from_monthly(r_all, rf_all)
        src = v.get("metrics") or {}
        for k in ("cagr", "vol", "sharpe", "mdd"):
            a, b = full.get(k), src.get(k)
            if a is not None and b is not None and abs(float(a) - float(b)) > 0.02:
                raise SystemExit("앵커 실패 %s.%s — 재진술 %.3f vs 원본 %.3f. 곡선에서 "
                                 "수익을 되뽑는 방식이 엔진과 다르다" % (sid, k, a, b))
        # ── 10년 창 ─────────────────────────────────────────────────────
        n = min(len(ms), MAX_YEARS * 12)
        sl = slice(len(ms) - n, len(ms))
        m10, r10, rf10 = ms[sl], r_all[sl], rf_all[sl]
        met = ann_from_monthly(r10, rf10)
        # 원본과 같은 모양(spx/ndx 각각 metrics·alpha·beta·t)으로 낸다.
        leg = {}
        for key, lab in (("spx", "S&P 500(PR) 매수후보유"), ("ndx", "NASDAQ 100(PR) 매수후보유")):
            if key not in ser:
                continue
            b10 = nav_to_rets(ser[key])[sl]
            a, bt, tt, _ = capm(r10, b10, rf10)
            leg[key] = {"metrics": dict(ann_from_monthly(b10, rf10) or {}, label=lab),
                        "alpha": a, "beta": bt, "t": tt}
        sp = leg.get("spx") or {}
        # ── 곡선 — 화면·진단이 쓰는 모양으로 같이 낸다 ──────────────────────
        # ⚠ 여기서 «새로 계산» 하는 것이 아니다. 위 앵커가 이 되뽑기가 엔진과 같음을
        #   이미 증명했고, 자르는 것 말고는 하는 일이 없다.
        _b10 = nav_to_rets(ser["spx"])[sl] if "spx" in ser else None
        _n10 = nav_to_rets(ser["ndx"])[sl] if "ndx" in ser else None
        _mon = []
        for i, mm in enumerate(m10):
            row = {"m": mm, "r": round(float(r10[i]) * 100, 4)}
            if _b10 is not None:
                row["b"] = round(float(_b10[i]) * 100, 4)
                row["i"] = {"S&P 500": row["b"]}
                if _n10 is not None:
                    row["i"]["NASDAQ 100"] = round(float(_n10[i]) * 100, 4)
            _mon.append(row)
        _nav = list(np.cumprod(1.0 + r10) * 100)
        _bnav = list(np.cumprod(1.0 + _b10) * 100) if _b10 is not None else []
        _dd = list(np.asarray(_nav) / np.maximum.accumulate(_nav) - 1.0)
        _ddb = (list(np.asarray(_bnav) / np.maximum.accumulate(_bnav) - 1.0)) if _bnav else []
        chart = {"dates": list(m10),
                 "nav": [round(float(x), 3) for x in _nav],
                 "bench": [round(float(x), 3) for x in _bnav],
                 "dd": [round(float(x) * 100, 3) for x in _dd],
                 "dd_b": [round(float(x) * 100, 3) for x in _ddb],
                 "monthly": _mon}
        out[sid] = {
            "kind": "guru", "chart": chart,
            "start": m10[0], "end": m10[-1], "n_months": int(n),
            "metrics": met, "spx": sp, "ndx": leg.get("ndx"),
            "bench": sp.get("metrics"), "t": sp.get("t"),
            "d_sharpe": (round(met["sharpe"] - sp["metrics"]["sharpe"], 3)
                         if met.get("sharpe") is not None
                         and (sp.get("metrics") or {}).get("sharpe") is not None else None),
            "excess_cagr": (round(met["cagr"] - sp["metrics"]["cagr"], 2)
                            if met.get("cagr") is not None
                            and (sp.get("metrics") or {}).get("cagr") is not None else None),
            "was": {"start": v.get("start"), "end": v.get("end"),
                    "n_months": v.get("n_months"), "metrics": src,
                    "t": (v.get("spx") or {}).get("t")},
        }
    return out


# ══ 페어 트레이딩 ═══════════════════════════════════════════════════════
def pairs_rows():
    import pairs_backtest as PB
    p = load("pairs_strategies.json")
    out = {}
    for s in (p.get("strategies") or []):
        d, nav, bnav = s.get("dates"), s.get("nav"), s.get("bnav")
        if not (d and nav):
            continue
        dr = nav_to_rets(nav)
        # ── 앵커 ────────────────────────────────────────────────────────
        full, _k, _m = PB.stats(dr, d)
        src = s.get("metrics") or {}
        for k in ("cagr", "vol", "mdd"):
            a, b = full.get(k), src.get(k)
            if a is not None and b is not None and abs(float(a) - float(b)) > 0.02:
                raise SystemExit("앵커 실패 %s.%s — 재진술 %.3f vs 원본 %.3f"
                                 % (s["sid"], k, a, b))
        # ── 10년 창 ─────────────────────────────────────────────────────
        end = d[-1]
        y0 = "%04d%s" % (int(end[:4]) - MAX_YEARS, end[4:])
        i0 = next((i for i, x in enumerate(d) if x >= y0), 0)
        d10, r10 = d[i0:], dr[i0:]
        met, _k2, mr = PB.stats(r10, d10)
        # ⚠ 대조군은 **현금(0)** 이다 — 엔진이 bench 를 {cagr:0,vol:0,sharpe:0,mdd:0} 로
        #   싣고 bnav 를 평평한 100 으로 둔다(시장중립 장부라 그렇다). 그래서 초과 = 수익이고
        #   t 는 대조군 대비가 아니라 **자기 수익의 NW t** 다. 엔진 정의를 그대로 따른다.
        # ── 곡선 — 페어는 일간이다. 월별은 stats() 가 이미 접은 그 격자를 쓴다. ──
        _mk = sorted({x[:7] for x in d10})
        _mon = [{"m": k, "r": round(float(v) * 100, 4), "b": 0.0,
                 "i": {"S&P 500": 0.0}} for k, v in zip(_k2, mr)]
        _nav = list(np.cumprod(1.0 + r10) * 100)
        _dd = list(np.asarray(_nav) / np.maximum.accumulate(_nav) - 1.0)
        chart = {"dates": list(d10),
                 "nav": [round(float(x), 3) for x in _nav],
                 "bench": [100.0] * len(d10),
                 "dd": [round(float(x) * 100, 3) for x in _dd],
                 "dd_b": [0.0] * len(d10),
                 "monthly": _mon}
        out[s["sid"]] = {
            "kind": "pairs", "chart": chart,
            "start": d10[0], "end": d10[-1],
            "n_months": int(met.get("n_months") or 0),
            "metrics": {k: (None if met.get(k) is None else round(met[k], 3))
                        for k in ("cagr", "vol", "sharpe", "mdd")},
            "bench": {"cagr": 0.0, "vol": 0.0, "sharpe": 0.0, "mdd": 0.0,
                      "label": s.get("bench_label")},
            "d_sharpe": (round(met["sharpe"], 3) if met.get("sharpe") is not None else None),
            "t": (round(met["t_nw"], 2) if met.get("t_nw") is not None else None),
            "excess_cagr": (round(met["cagr"], 2) if met.get("cagr") is not None else None),
            "was": {"start": s.get("start"), "end": s.get("end"), "metrics": src,
                    "t": s.get("t")},
        }
    return out


def main() -> int:
    rows = {}
    rows.update(guru_rows())
    rows.update(pairs_rows())
    doc = {"note": "페어·거장겹침을 10년 창으로 재진술한 값. **원본은 안 건드린다** — "
                   "guru_overlap.json·pairs_strategies.json 과 guru.html#overlap 은 그대로다. "
                   "strategy_index 가 이 값으로 그 16종의 창·성적을 덮어 싣는다.",
           "max_years": MAX_YEARS, "n": len(rows), "rows": rows}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + chr(10))
    print("재진술 %d종 → %s" % (len(rows), os.path.basename(OUT)))
    print("  %-22s %8s %8s %7s %7s %7s  %s"
          % ("sid", "CAGR%", "초과%p", "샤프", "t", "옛 t", "10년 창"))
    for sid, r in sorted(rows.items(), key=lambda kv: -(kv[1].get("t") or -9)):
        m, w = r["metrics"], r["was"]
        print("  %-22s %8s %8s %7s %7s %7s  %s~%s"
              % (sid,
                 "—" if m.get("cagr") is None else "%.2f" % m["cagr"],
                 "—" if r.get("excess_cagr") is None else "%+.2f" % r["excess_cagr"],
                 "—" if m.get("sharpe") is None else "%.3f" % m["sharpe"],
                 "—" if r.get("t") is None else "%.2f" % r["t"],
                 "—" if w.get("t") is None else "%.2f" % w["t"],
                 r["start"], r["end"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
