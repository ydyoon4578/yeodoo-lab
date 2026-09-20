# -*- coding: utf-8 -*-
"""build/audit_shares.py — data/fx 의 주식수에 단위 사고가 있나. 전수로 훑는다.

🚨 왜. 시가총액을 「종가 × 주식수」로 만들다가 2026-06 재구성 지수에서
   **WAT(Waters)가 비중 29.5%** 로 나왔다. 시총 200억$ 대 회사다.
   원인: `sh`(희석 가중평균)가 2025-12 **59.76백만주** → 2026-04 **98,204백만주**
   로 **1,643배** 튀었다. 같은 시점 `sho`(기말 발행주식수)는 98.22백만주로 정상이다.
   **회사가 그 분기에 단위를 바꿔 보고했고(천주 ↔ 주) 스케일 변환이 그것을 못 잡았다.**

여기서 두 가지를 센다.
  ① 시계열 안에서 **10배 넘게 튀는** 관측 — 분할·합병으로는 잘 안 나는 크기
  ② 같은 시점 `sh` 와 `sho` 의 **비율이 10배를 넘는** 관측 — 둘은 정의가 달라도
     자릿수는 같아야 한다

  python build/audit_shares.py
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_audit_shares.json")
JUMP, RATIO = 10.0, 10.0


def ser(tg, k):
    v = (tg or {}).get(k) or {}
    out = {}
    for e, x, *_ in (v.get("i") or v.get("q") or v.get("a") or []):
        out[e] = float(x)
    return out


def main():
    jumps, ratios, n = [], [], 0
    for p in sorted(glob.glob(os.path.join(DATA, "fx", "*.json"))):
        j = json.load(io.open(p, encoding="utf-8"))
        t, tg = j["t"], j.get("tags") or {}
        n += 1
        for key in ("sh", "sho"):
            s = ser(tg, key)
            if len(s) < 3:
                continue
            ks = sorted(s)
            for a, b in zip(ks[:-1], ks[1:]):
                x, y = s[a], s[b]
                if x > 0 and y > 0:
                    r = max(x / y, y / x)
                    if r >= JUMP:
                        jumps.append({"t": t, "key": key, "from": a, "to": b,
                                      "v_from": x, "v_to": y, "ratio": r})
        sh, sho = ser(tg, "sh"), ser(tg, "sho")
        for e in set(sh) & set(sho):
            if sh[e] > 0 and sho[e] > 0:
                r = max(sh[e] / sho[e], sho[e] / sh[e])
                if r >= RATIO:
                    ratios.append({"t": t, "end": e, "sh": sh[e], "sho": sho[e], "ratio": r})
    print("회사 %d개 검사\n" % n)

    print("■ ① 시계열 안에서 %g배 넘게 튄 관측 — %d건" % (JUMP, len(jumps)))
    jumps.sort(key=lambda x: -x["ratio"])
    seen = set()
    for r in jumps[:16]:
        print("   %-6s %-4s %s → %s   %12.2f → %12.2f  (%.0f배)"
              % (r["t"], r["key"], r["from"], r["to"], r["v_from"], r["v_to"], r["ratio"]))
        seen.add(r["t"])
    if len(jumps) > 16:
        print("   … 외 %d건" % (len(jumps) - 16))
    print("   걸린 종목 %d개" % len({r["t"] for r in jumps}))

    print("\n■ ② 같은 시점 sh 와 sho 의 비율이 %g배를 넘는 관측 — %d건" % (RATIO, len(ratios)))
    ratios.sort(key=lambda x: -x["ratio"])
    for r in ratios[:12]:
        print("   %-6s %s  sh %12.2f · sho %10.2f  (%.0f배)"
              % (r["t"], r["end"], r["sh"], r["sho"], r["ratio"]))
    if len(ratios) > 12:
        print("   … 외 %d건" % (len(ratios) - 12))
    bad = {r["t"] for r in ratios}
    print("   걸린 종목 %d개: %s" % (len(bad), " ".join(sorted(bad)[:20])))

    print("\n■ 뜻")
    print("   ②가 특히 나쁘다 — 희석 가중평균과 기말 발행주식수는 정의가 달라도")
    print("   자릿수는 같아야 한다. 10배를 넘으면 단위 사고다.")
    print("   🚨 시가총액을 만드는 곳은 전부 이 종목들을 걸러야 한다.")
    print("      이 랩에서 시총을 쓰는 것: 시총가중 성적 · 지수 재구성 · 규모 팩터.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"n_co": n, "jump_threshold": JUMP, "ratio_threshold": RATIO,
         "jumps": jumps, "sh_sho_ratio": ratios,
         "bad_tickers": sorted({r["t"] for r in jumps} | bad),
         "note": "주식수 단위 사고. 시총을 만드는 코드는 이 목록을 걸러야 한다."},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
