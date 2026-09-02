# -*- coding: utf-8 -*-
"""build/ssrot.py — S&P 스타일 점수로 금리 국면 로테이션 → data/_ssrot.json

규약: build/PREREG-2026-09-03-SSROT.md (계산 전 커밋 0e0ba241f).

  x-ssrot  스타일 점수의 가치배분 WV 중앙값으로 반씩 → 가치·성장 다리(동일가중)
           DFII10 3개월 변화 ≥+20bp → 가치 70/성장 30 · ≤−20bp → 30/70 · 사이 50/50
  x-bmrot  같은 규칙을 **B/M** 으로. 정렬 기준만 다르다. ← 1번 대조군

🚨 «중앙값 분할·동일가중» 은 대조군과 맞추려는 것이다(등록 §1-1). S&P 실제 지수는 WV 를
  시총에 곱하지만, 가중을 바꾸면 차이가 신호 때문인지 가중 때문인지 못 가른다.
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/ssrot.py
"""
from __future__ import annotations
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_ssrot.json")
sys.path.insert(0, HERE)

TH = 0.20               # DFII10 3개월 변화 문턱(%p) — D13 카드의 수
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}
COST_RT = 0.0020        # 왕복 20bp — F3


def main():
    import tech_backtest as TB

    SS = json.load(io.open(os.path.join(DATA, "_style_score.json"), encoding="utf-8"))
    panel, ms = SS["panel"], SS["months"]

    dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
    di = {d: i for i, d in enumerate(dates)}
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    ad = {d: i for i, d in enumerate(A["dates"])}
    RY = {k: v for k, v in (A["macro"].get("DFII10") or {}).items() if v is not None}
    _rk = sorted(RY)

    def ry(d):
        k = None
        for key in _rk:
            if key <= d:
                k = key
            else:
                break
        return RY.get(k) if k else None

    def back3(d):
        y, m = int(d[:4]), int(d[5:7]) - 3
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        return ry("%04d-%02d-%s" % (y, m, d[8:10]))

    def spy(d0, d1):
        s = A["px"]["SPY"]
        if d0 in ad and d1 in ad and s[ad[d0]] and s[ad[d1]]:
            return s[ad[d1]] / s[ad[d0]] - 1
        return None

    # B/M 은 스타일 점수 패널에 없다 — 여기서 다시 낸다(같은 시점·같은 후보로).
    FU = TB.load_fund()

    def bm_of(t, d, i):
        f = FU.get(t)
        if not f:
            return None
        eq = TB.asof_fund(f.get("eq"), d)
        sn = TB.asof_fund(f.get("sh"), d)
        p = px[t][i]
        if not (eq and sn and p and sn > 0 and p > 0):
            return None
        return eq / (sn * p)

    rows, prevv = [], {}
    for k in range(len(ms) - 1):
        d, d1 = ms[k], ms[k + 1]
        if d not in di or d1 not in di:
            continue
        i, i1 = di[d], di[d1]
        P = panel[d]
        WV = P["WV"]
        now, p3 = ry(d), back3(d)
        ch = None if (now is None or p3 is None) else now - p3
        g = "중립" if ch is None else ("가치" if ch >= TH else "성장" if ch <= -TH else "중립")

        # 두 정렬이 **같은 후보 집합**을 써야 신호만 비교된다
        cand = [t for t in WV
                if px.get(t) and px[t][i] and px[t][i1] and px[t][i] > 0]
        bm = {t: bm_of(t, d, i) for t in cand}
        cand = [t for t in cand if bm[t] is not None]
        if len(cand) < 100:
            continue
        h = len(cand) // 2

        def legs(key):
            if key == "ss":
                srt = sorted(cand, key=lambda t: -WV[t])     # WV 큰 쪽 = 가치
            else:
                srt = sorted(cand, key=lambda t: -bm[t])     # B/M 큰 쪽 = 가치
            return set(srt[:h]), set(srt[h:])                # (가치, 성장)

        def bret(bk):
            rs = [px[t][i1] / px[t][i] - 1 for t in bk]
            return sum(rs) / len(rs) if rs else 0.0

        out = {}
        for key in ("ss", "bm"):
            val, grw = legs(key)
            w = W[g]
            r = w * bret(val) + (1 - w) * bret(grw)
            base = .5 * bret(val) + .5 * bret(grw)
            pv = prevv.get(key)
            tc = 0.0
            if pv is not None:
                same = len(pv[0] & val) / max(1, len(pv[0] | val))
                tc = COST_RT * (abs(w - pv[1]) + (1 - same))
            prevv[key] = (val, w)
            out[key] = dict(r=r, base=base, cost=tc, val=val)
        rows.append(dict(m=dates[i1][:7], reg=g, n=len(cand),
                         ss=out["ss"], bm=out["bm"], spy=spy(d, d1) or 0.0,
                         up10=_up(A, d, "DGS10"), up2=_up(A, d, "DGS2")))

    n = len(rows)
    print("측정 %s ~ %s · %d개월 · 후보 중앙 %d종"
          % (rows[0]["m"], rows[-1]["m"], n, sorted(r["n"] for r in rows)[n // 2]))

    def stat(v):
        m = sum(v) / len(v)
        sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
        p = 1.0
        for x in v:
            p *= 1 + x
        return ((p ** (12 / len(v)) - 1) * 100, sd * math.sqrt(12) * 100,
                (m * 12) / (sd * math.sqrt(12)))

    def tt(a, b):
        d = [a[i] - b[i] for i in range(len(a))]
        m = sum(d) / len(d)
        sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1))
        return m * 12 * 100, m / (sd / math.sqrt(len(d)))

    ss = [r["ss"]["r"] for r in rows]
    bmr = [r["bm"]["r"] for r in rows]
    ssn = [r["ss"]["r"] - r["ss"]["cost"] for r in rows]
    bmn = [r["bm"]["r"] - r["bm"]["cost"] for r in rows]
    sp = [r["spy"] for r in rows]
    base = [r["ss"]["base"] for r in rows]

    print()
    print("%-24s %8s %8s %8s" % ("", "CAGR", "변동성", "샤프"))
    for lab, v in (("x-ssrot (스타일 점수)", ss), ("x-bmrot (B/M · 대조군)", bmr),
                   ("틸트 없는 50/50", base), ("S&P 500 TR (SPY)", sp)):
        c, vo, s = stat(v)
        print("%-24s %7.2f%% %7.2f%% %8.3f" % (lab, c, vo, s))

    a, t = tt(ss, bmr)
    an, tn = tt(ssn, bmn)
    print()
    print("F1·F2 — 스타일 − B/M : 연 %+.2f%%p · t %.2f   (비용 뒤 %+.2f%%p · t %.2f)"
          % (a, t, an, tn))
    a2, t2 = tt(ss, sp)
    a3, t3 = tt(bmr, sp)
    print("        스타일 − SPY  : 연 %+.2f%%p · t %.2f" % (a2, t2))
    print("        B/M    − SPY  : 연 %+.2f%%p · t %.2f" % (a3, t3))

    m1, m2 = sum(ss) / n, sum(bmr) / n
    s1 = math.sqrt(sum((x - m1) ** 2 for x in ss))
    s2 = math.sqrt(sum((x - m2) ** 2 for x in bmr))
    rho = sum((ss[i] - m1) * (bmr[i] - m2) for i in range(n)) / ((s1 * s2) or 1e-12)
    ov = sorted(len(rows[i]["ss"]["val"] & rows[i]["bm"]["val"])
                / max(1, len(rows[i]["ss"]["val"] | rows[i]["bm"]["val"])) for i in range(n))
    sw = sum(1 for i in range(1, n) if rows[i]["reg"] != rows[i - 1]["reg"])
    ex = [ss[i] - bmr[i] for i in range(n)]
    tot = sum(ex)
    mx = max(ex, key=abs)
    print()
    print("F6 두 수익 상관 %.4f (>0.99 면 «같은 것의 다른 이름»)" % rho)
    print("F4 국면 전환 %d회 · 가치 다리 종목 겹침 중앙 %.1f%%" % (sw, 100 * ov[n // 2]))
    print("F5 |초과| 최대 한 달이 누적의 %.0f%%" % (100 * abs(mx / tot) if tot else 0))

    print()
    print("금리 인상 구간 × SPY 대비 (참고 — F1 은 전 구간에서 판정한다)")
    for lab, sel in (("10년물 +25bp", lambda r: r["up10"]),
                     ("2년물 +25bp", lambda r: r["up2"]),
                     ("둘 다", lambda r: r["up10"] and r["up2"]),
                     ("인상기 아님", lambda r: not (r["up10"] or r["up2"]))):
        v = [r for r in rows if sel(r)]
        if len(v) < 8:
            continue
        aa, ta = tt([x["ss"]["r"] for x in v], [x["spy"] for x in v])
        bb, tb = tt([x["bm"]["r"] for x in v], [x["spy"] for x in v])
        print("  %-14s %3d개월 · 스타일 %+6.2f%%p(t %5.2f) · B/M %+6.2f%%p(t %5.2f)"
              % (lab, len(v), aa, ta, bb, tb))

    doc = {"note": "S&P 스타일 점수 금리 로테이션. 규약 PREREG-2026-09-03-SSROT.md. 얼린 측정.",
           "prereg": "0e0ba241f", "window": [rows[0]["m"], rows[-1]["m"]], "n": n,
           "f1": [a, t], "f1_net": [an, tn], "f6_rho": rho, "switches": sw,
           "overlap_med": ov[n // 2],
           "rows": [{"m": r["m"], "reg": r["reg"], "n": r["n"],
                     "ss": round(r["ss"]["r"], 6), "bm": round(r["bm"]["r"], 6),
                     "spy": round(r["spy"], 6)} for r in rows]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


def _up(A, d, sid):
    m = A["macro"].get(sid) or {}
    def asof(x):
        k = None
        for key in sorted(m):
            if key <= x:
                k = key
            else:
                break
        return m.get(k) if k else None
    y, mo = int(d[:4]), int(d[5:7]) - 6
    y += (mo - 1) // 12
    mo = (mo - 1) % 12 + 1
    n0, p6 = asof(d), asof("%04d-%02d-%s" % (y, mo, d[8:10]))
    return n0 is not None and p6 is not None and n0 - p6 > 0.25


if __name__ == "__main__":
    main()
