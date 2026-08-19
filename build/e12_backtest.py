# -*- coding: utf-8 -*-
"""build/e12_backtest.py — E12 지수 편입·제외 이벤트 백테스트 → data/e12.json

규약: build/PREREG-2026-08-19-E12.md (수익률을 보기 전에 커밋했다). 규칙은 전부 거기 있다 —
여기서 바꾸지 않는다. 이벤트 목록도 같이 얼렸다(build/e12_events.json).

  갈래 A · 압력 포착: AD+1 종가(= ED−4) 진입 → ED 종가 청산. AD := ED−5거래일 근사.
  갈래 B · 리버설:   ED+21 진입 → 252거래일 보유. 편입 롱 vs 재량 제외 롱.

    python build/e12_backtest.py
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
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(DATA, "e12.json")

COST_BP = 15          # 편도 — 사전등록 §3
COST_SENS = (10, 20)
AD_LAG = 5            # AD := ED − 5거래일 — 사전등록 §2-1
AD_SENS = (3, 7)
ERAS = [("2009-14", "2009", "2015"), ("2015-19", "2015", "2020"), ("2020-26", "2020", "2027")]


def load_px():
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dts = st["pxd_dates"]
    n = len(dts)
    px = {}
    sd = os.path.join(DATA, "sd")
    for fn in os.listdir(sd):
        if fn.endswith(".json"):
            a = (json.load(io.open(os.path.join(sd, fn), encoding="utf-8")) or {}).get("pxd") or []
            px[fn[:-5]] = a + [None] * (n - len(a))
    sl = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))
    ds2 = sl["dates"]
    d2i = {d: i for i, d in enumerate(dts)}
    for t, v in sl["px"].items():
        if t in px:
            continue                       # 오늘 유니버스가 우선(더 신선하다)
        a = [None] * n
        for k, p in enumerate(v["p"]):
            if p is None:
                continue
            i = d2i.get(ds2[v["i0"] + k])
            if i is not None:
                a[i] = p
        px[t] = a
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bench = {}
    for k in ("spx", "ndx"):
        bmap = dict(zip(B["dates"], B["series"][k]["px"]))
        bench[k] = [bmap.get(d) for d in dts]
    return dts, px, bench


def at(a, i):
    return a[i] if a is not None and 0 <= i < len(a) and a[i] is not None else None


def win_ret(a, i0, i1):
    p0, p1 = at(a, i0), at(a, i1)
    if not p0 or not p1:
        return None
    return (p1 / p0 - 1) * 100.0


def stats(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 3:
        return {"n": len(xs), "mean": None, "med": None, "t": None, "top2ex": None}
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    t = m / (sd / math.sqrt(len(xs))) if sd > 0 else None
    srt = sorted(xs)
    med = srt[len(srt) // 2]
    # 사전등록 §4-P4 — 상위 2이벤트 제외 평균(소수 사례 의존 검사)
    ex = srt[:-2] if len(srt) > 4 else srt
    return {"n": len(xs), "mean": round(m, 2), "med": round(med, 2),
            "t": (None if t is None else round(t, 2)),
            "top2ex": round(sum(ex) / len(ex), 2)}


def run_index(tag, events_file, bench_key, dts, px, bench, gi, MA):
    """한 지수의 두 갈래 — §3 규칙 그대로. 대조군만 지수별(§6)."""
    E = json.load(io.open(os.path.join(BUILD, events_file), encoding="utf-8"))
    spx = bench[bench_key]
    n = len(dts)
    press = []
    for e in E:
        t = e.get("add")
        if not t:
            continue
        i = gi(e["d"])
        if i is None or i < AD_LAG + 2:
            continue
        row = {"t": t, "d": e["d"]}
        ok = False
        for lag, key in [(AD_LAG, "x"), (AD_SENS[0], "x3"), (AD_SENS[1], "x7")]:
            i0 = i - (lag - 1)
            r = win_ret(px.get(t), i0, i)
            b = win_ret(spx, i0, i)
            if r is None or b is None:
                row[key] = None
                continue
            row[key] = round(r - b - 2 * COST_BP / 100.0, 2)
            if key == "x":
                row["gross"] = round(r - b, 2)
                ok = True
        if ok:
            press.append(row)
    press_all = stats([r["x"] for r in press])
    press_era = {lab: stats([r["x"] for r in press if lo <= r["d"][:4] < hi])
                 for lab, lo, hi in ERAS}
    press_sens = {
        "ad3": stats([r["x3"] for r in press]),
        "ad7": stats([r["x7"] for r in press]),
        "cost10": stats([(r["gross"] - 0.20) for r in press if r.get("gross") is not None]),
        "cost20": stats([(r["gross"] - 0.40) for r in press if r.get("gross") is not None]),
    }
    print("[%s] 갈래 A · 압력 — %d건 · 평균 %s%%p · t %s" % (tag, press_all["n"], press_all["mean"], press_all["t"]))
    for lab, _l, _h in ERAS:
        st2 = press_era[lab]
        print("   %s  n=%-3s 평균 %s · 중앙 %s · 상위2제외 %s · t %s"
              % (lab, st2["n"], st2["mean"], st2["med"], st2["top2ex"], st2["t"]))
    print("   민감도: AD-3 %s · AD-7 %s" % (press_sens["ad3"]["mean"], press_sens["ad7"]["mean"]))

    ENTRY, HOLD = 21, 252
    rev_add, rev_del = [], []
    for e in E:
        i = gi(e["d"])
        if i is None:
            continue
        i0, i1 = i + ENTRY, i + ENTRY + HOLD
        if i1 >= n:
            continue
        b = win_ret(spx, i0, i1)
        if b is None:
            continue
        if e.get("add"):
            r = win_ret(px.get(e["add"]), i0, i1)
            if r is not None:
                rev_add.append({"t": e["add"], "d": e["d"], "x": round(r - b - 2 * COST_BP / 100.0, 2)})
        t2 = e.get("rem")
        if t2 and not MA.search(e.get("why") or ""):
            r = win_ret(px.get(t2), i0, i1)
            if r is not None:
                rev_del.append({"t": t2, "d": e["d"], "x": round(r - b - 2 * COST_BP / 100.0, 2)})
    sa, sdel = stats([r["x"] for r in rev_add]), stats([r["x"] for r in rev_del])
    spread = (None if (sa["mean"] is None or sdel["mean"] is None)
              else round(sdel["mean"] - sa["mean"], 2))
    print("[%s] 갈래 B · 리버설 — 편입 %d건 평균 %s · 재량 제외 %d건 평균 %s · 스프레드 %s"
          % (tag, sa["n"], sa["mean"], sdel["n"], sdel["mean"], spread))
    return {"press": {"all": press_all, "era": press_era, "sens": press_sens, "rows": press},
            "rev": {"add": sa, "del": sdel, "spread": spread,
                    "rows_add": rev_add, "rows_del": rev_del,
                    "entry_td": ENTRY, "hold_td": HOLD}}


def main() -> int:
    dts, px, bench = load_px()
    n = len(dts)
    print("격자 %d일 · 가격 계열 %d개" % (n, len(px)))

    def gi(d):
        """실효일 → 격자 색인(그 날 또는 다음 거래일)."""
        lo, hi = 0, n - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if dts[mid] < d:
                lo = mid + 1
            else:
                hi = mid
        return lo if dts[lo] >= d else None

    import re
    MA = re.compile(r"acquir|merg|purchas|bought|taken private|bankrupt|chapter|delist|spun|spin", re.I)
    spx_res = run_index("SPX", "e12_events.json", "spx", dts, px, bench, gi, MA)
    ndx_res = run_index("NDX", "e12_events_ndx.json", "ndx", dts, px, bench, gi, MA)

    doc = {
        "note": "E12 지수 편입·제외 이벤트 백테스트. 규칙·예측은 PREREG-2026-08-19-E12.md 에 "
                "돌리기 전에 커밋했다. 이벤트별 원자료를 그대로 싣는다 — 사람이 검산할 수 있게.",
        "prereg": "build/PREREG-2026-08-19-E12.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid": {"start": dts[0], "end": dts[-1], "n": n},
        "cost_bp_oneway": COST_BP, "ad_lag": AD_LAG,
        # §6 부칙 — 두 지수를 같은 규칙으로. 대조군만 지수별(^GSPC / ^NDX).
        "spx": spx_res, "ndx": ndx_res,
        # 하위호환 — 종전 소비자가 press/rev 를 읽는다면 SPX 것을 그대로 둔다.
        "press": spx_res["press"], "rev": spx_res["rev"],
        "limits": [
            "🚨 발표일(AD)은 자료에 없어 ED−5거래일로 근사했다(민감도 −3·−7). 실제 발표가 "
            "이보다 이르면 창이 어긋난다 — 이 근사가 최대 한계다.",
            "⚠ 개장가가 없어 «발표 다음 개장 진입» 을 «AD+1 종가 진입» 으로 바꿨다. 발표 갭은 "
            "그 사이에 실현되므로 갭 이후 성과만 재는 셈이다(카드가 요구한 조건).",
            "⚠ 재량 제외의 12개월 커버는 반쪽이다 — 빠진 이벤트는 그 뒤 인수·상폐로 자료가 "
            "사라진 쪽에 몰릴 수 있어, 남은 표본의 제외종목 성과는 위로 치우칠 수 있다.",
            "⚠ 보유 종가는 배당조정이고 대조군은 PR — 12개월 창의 초과가 최대 약 2%p 후하다. "
            "스프레드(제외−편입)에서는 양쪽에 같이 붙어 대부분 상쇄된다.",
        ],
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
