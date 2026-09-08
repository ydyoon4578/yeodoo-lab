# -*- coding: utf-8 -*-
"""build/pure25.py — 20종 스타일 로테이션을 **다리당 25종**으로 넓힌다 → data/_pure25.json

규약: build/PREREG-2026-09-08-PURE25.md (계산 전 커밋 be6a8414).

  x-pure10 에서 **K = 10 → 25** 하나만 바꾼다. 정렬·가중·신호·문턱·틸트·주기·
  PIT 유니버스·비용 전부 그대로다.

  겨냥: 변동성 23.95% = √(20.59²(시장) + 12.24²(고유)). 고유위험은 수익을 안 준다.
        1/√N 로 줄면 K=25 에서 고유 7.74%p · 변동성 22.00% · 초과샤프 0.821 이 된다.
        🚨 「평균 수익이 유지된다」가 가정이고 그것이 이 등록의 진짜 물음이다.

🚨 판정은 초과 샤프(무위험이자를 뺀 것)로 한다 — PURELS §1-4 규약.
🚨 후보가 25종 미만이면 있는 만큼 담는다(2020-09·10 두 달). 달을 빼지 않는다.
🚨 x-pure10 과 «나란히» 싣는다. 좋은 쪽만 싣지 않는다(등록 §0-1 · §7).
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/pure25.py
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
OUT = os.path.join(DATA, "_pure25.json")
sys.path.insert(0, HERE)

TH = 0.20
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}
COST_RT = 0.0020
KS = (10, 25)                   # 🚨 둘을 «나란히» 낸다. 좋은 쪽만 싣지 않는다


def sd(v):
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def stat(v, rf):
    n = len(v)
    m = sum(v) / n
    s = sd(v)
    p = 1.0
    for x in v:
        p *= 1 + x
    cur = peak = 1.0
    mdd = 0.0
    for x in v:
        cur *= 1 + x
        peak = max(peak, cur)
        mdd = min(mdd, cur / peak - 1)
    return dict(cagr=(p ** (12 / n) - 1) * 100, vol=s * math.sqrt(12) * 100,
                sharpe=(m * 12) / (s * math.sqrt(12)) if s else 0.0,
                exsharpe=((m - sum(rf) / n) * 12) / (s * math.sqrt(12)) if s else 0.0,
                mdd=mdd * 100)


def tt(a, b):
    d = [a[i] - b[i] for i in range(len(a))]
    m = sum(d) / len(d)
    s = sd(d)
    return m * 12 * 100, m / (s / math.sqrt(len(d)))


def beta_of(r, s):
    n = len(r)
    mr, ms = sum(r) / n, sum(s) / n
    b = sum((s[i] - ms) * (r[i] - mr) for i in range(n)) / sum((x - ms) ** 2 for x in s)
    res = [r[i] - b * s[i] for i in range(n)]
    a = mr - b * ms
    return b, a * 12 * 100, a / (sd(res) / math.sqrt(n))


def main():
    import tech_backtest as TB

    SS = json.load(io.open(os.path.join(DATA, "_style_score.json"), encoding="utf-8"))
    panel, ms = SS["panel"], SS["months"]
    IH = json.load(io.open(os.path.join(DATA, "index_history.json"),
                           encoding="utf-8"))["months"]
    dates, px, vlm, hid, lod, meta, rf_ = TB.load(full=True)
    di = {d: i for i, d in enumerate(dates)}
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    ad = {d: i for i, d in enumerate(A["dates"])}
    RY = {k: v for k, v in (A["macro"].get("DFII10") or {}).items() if v is not None}
    CB = {k: v for k, v in (A["macro"].get("DGS3MO") or {}).items() if v is not None}
    _rk, _ck = sorted(RY), sorted(CB)

    def asof(m, ks, d):
        k = None
        for key in ks:
            if key <= d:
                k = key
            else:
                break
        return m.get(k) if k else None

    def shift(d, b):
        y, mo = int(d[:4]), int(d[5:7]) - b
        y += (mo - 1) // 12
        mo = (mo - 1) % 12 + 1
        return "%04d-%02d-%s" % (y, mo, d[8:10])

    FU = TB.load_fund()
    rows, thin = [], []
    for k in range(len(ms) - 1):
        d, d1 = ms[k], ms[k + 1]
        if d not in di or d1 not in di:
            continue
        x = IH.get(d[:7])
        if not x:
            continue
        U = set(x.get("spx") or []) | set(x.get("ndx") or [])
        i, i1 = di[d], di[d1]
        P = panel[d]
        SV, SG = P["SV"], P["SG"]
        okset = set()
        for t in SV:
            if t not in U:
                continue
            if not (px.get(t) and px[t][i] and px[t][i1] and px[t][i] > 0):
                continue
            f = FU.get(t)
            if not f:
                continue
            eq = TB.asof_fund(f.get("eq"), d)
            sn = TB.asof_fund(f.get("sh"), d)
            if eq is None or not sn or sn <= 0 or eq / (sn * px[t][i]) <= 0:
                continue
            okset.add(t)
        if len(okset) < 100:
            continue
        pv = [t for t in P["pv"] if t in okset]
        pg = [t for t in P["pg"] if t in okset]
        if len(pv) < min(KS) or len(pg) < min(KS):
            continue
        now, p3 = asof(RY, _rk, d), asof(RY, _rk, shift(d, 3))
        ch = None if (now is None or p3 is None) else now - p3
        g = "중립" if ch is None else ("가치" if ch >= TH else "성장" if ch <= -TH else "중립")
        w = W[g]

        def r1(t):
            return px[t][i1] / px[t][i] - 1

        vs = sorted(pv, key=lambda t: -SV[t])
        gs = sorted(pg, key=lambda t: -SG[t])
        s = A["px"]["SPY"]
        rec = dict(m=dates[i1][:7], reg=g, w=w, npv=len(pv), npg=len(pg),
                   spy=(s[ad[d1]] / s[ad[d]] - 1) if (d in ad and d1 in ad) else 0.0,
                   cash=(asof(CB, _ck, d) or 0.0) / 100 / 12)
        for K in KS:
            V, G = vs[:K], gs[:K]
            if len(G) < K or len(V) < K:
                thin.append((dates[i1][:7], K, len(V), len(G)))
            rv = sum(r1(t) for t in V) / len(V)
            rg = sum(r1(t) for t in G) / len(G)
            rec[K] = dict(rv=rv, rg=rg, r=w * rv + (1 - w) * rg,
                          base=.5 * rv + .5 * rg, V=set(V), G=set(G))
        rows.append(rec)

    n = len(rows)
    CASH = [x["cash"] for x in rows]
    SP = [x["spy"] for x in rows]
    R = {K: [x[K]["r"] for x in rows] for K in KS}

    print("측정 %s ~ %s · %d개월" % (rows[0]["m"], rows[-1]["m"], n))
    if thin:
        print("⚠ 후보가 K 미만이라 있는 만큼 담은 달 %d개: %s"
              % (len(thin), " · ".join("%s K=%d 가치%d/성장%d" % z for z in thin)))
    else:
        print("   모든 달에서 두 K 를 다 채웠다")

    # 비용
    def costs(K):
        prev, out = {}, []
        for x in rows:
            wt = {}
            for t in x[K]["V"]:
                wt[t] = wt.get(t, 0.0) + x["w"] / len(x[K]["V"])
            for t in x[K]["G"]:
                wt[t] = wt.get(t, 0.0) + (1 - x["w"]) / len(x[K]["G"])
            out.append(COST_RT * 0.5 * sum(abs(wt.get(t, 0.0) - prev.get(t, 0.0))
                                           for t in set(wt) | set(prev)))
            prev = wt
        return out, [0.5 * sum(abs(wt.get(t, 0.0) - prev.get(t, 0.0))
                               for t in set(wt) | set(prev))]

    C = {K: costs(K)[0] for K in KS}

    print()
    print("%-30s %8s %8s %9s %10s %8s"
          % ("", "CAGR", "변동성", "랩 샤프", "초과 샤프", "MDD"))
    S = {}
    for K in KS:
        S[K] = stat(R[K], CASH)
        print("%-30s %7.2f%% %7.2f%% %9.3f %10.3f %7.2f%%"
              % ("x-pure%d (다리당 %d종)" % (K, K), S[K]["cagr"], S[K]["vol"],
                 S[K]["sharpe"], S[K]["exsharpe"], S[K]["mdd"]))
    ss = stat(SP, CASH)
    print("%-30s %7.2f%% %7.2f%% %9.3f %10.3f %7.2f%%"
          % ("S&P 500 TR (SPY)", ss["cagr"], ss["vol"], ss["sharpe"],
             ss["exsharpe"], ss["mdd"]))
    b25 = stat([x[25]["base"] for x in rows], CASH)
    print("%-30s %7.2f%% %7.2f%% %9.3f %10.3f %7.2f%%"
          % ("틸트 없는 50/50 (25종씩)", b25["cagr"], b25["vol"], b25["sharpe"],
             b25["exsharpe"], b25["mdd"]))

    print()
    print("── 판정 ──────────────────────────────────────────────────")
    d1 = S[25]["exsharpe"] - S[10]["exsharpe"]
    a1, t1 = tt(R[25], R[10])
    print("F1 🚨 x-pure25 − x-pure10  Δ초과샤프 %+.3f (%.3f vs %.3f) · 연 %+.2f%%p · t %.2f → %s"
          % (d1, S[25]["exsharpe"], S[10]["exsharpe"], a1, t1, "통과" if d1 > 0 else "기각"))
    d2 = S[25]["exsharpe"] - ss["exsharpe"]
    print("F2 🚨 x-pure25 − SPY       Δ%+.3f (%.3f vs %.3f)                        → %s"
          % (d2, S[25]["exsharpe"], ss["exsharpe"],
             "넘음" if d2 > 0 else "🚨 못 넘음 — 첫 줄에 적는다"))
    print("F3 🚨 산수 검증 — 변동성 %.2f%% (예측 22.00%% · 문턱 22.5%%)              → %s"
          % (S[25]["vol"], "통과" if S[25]["vol"] < 22.5 else "🚨 산수가 안 맞았다"))
    b10, al10, at10 = beta_of(R[10], SP)
    b25b, al25, at25 = beta_of(R[25], SP)
    idio10 = math.sqrt(max(0, S[10]["vol"] ** 2 - (b10 * ss["vol"]) ** 2))
    idio25 = math.sqrt(max(0, S[25]["vol"] ** 2 - (b25b * ss["vol"]) ** 2))
    print("      고유위험 %.2f%%p → %.2f%%p  (예측 12.24 → 7.74 · 실제 비율 %.3f · 산수 0.632)"
          % (idio10, idio25, idio25 / idio10 if idio10 else 0))
    e25 = stat([R[25][i] - C[25][i] for i in range(n)], CASH)["exsharpe"]
    e10 = stat([R[10][i] - C[10][i] for i in range(n)], CASH)["exsharpe"]
    print("F4    비용 뒤 %.3f vs %.3f (Δ%+.3f)                                  → %s"
          % (e25, e10, e25 - e10, "통과" if e25 > e10 else "기각"))
    print("F5 🚨 희석 — CAGR %.2f%% → %.2f%% (%+.2f%%p · 문턱 15.5%%)              → %s"
          % (S[10]["cagr"], S[25]["cagr"], S[25]["cagr"] - S[10]["cagr"],
             "🚨 너무 씻긴다 — 첫 줄에 적는다" if S[25]["cagr"] < 15.5 else "통과"))
    print("F6    베타 %.2f → %.2f · 알파 연 %+.2f%%p → %+.2f%%p · 알파 t %.2f → %.2f"
          % (b10, b25b, al10, al25, at10, at25))
    print("F7    후보수 중앙  가치 %d · 성장 %d"
          % (sorted(x["npv"] for x in rows)[n // 2], sorted(x["npg"] for x in rows)[n // 2]))

    print()
    print("── 예측 판정 ─────────────────────────────────────────────")
    print("P1 변동성 21.0~22.5%%   실측 %.2f%%   %s"
          % (S[25]["vol"], "맞음" if 21.0 <= S[25]["vol"] <= 22.5 else "빗나감"))
    print("P2 CAGR 16~19%%        실측 %.2f%%   %s"
          % (S[25]["cagr"], "맞음" if 16 <= S[25]["cagr"] <= 19 else "빗나감"))
    print("P3 초과샤프 0.78~0.86  실측 %.3f    %s"
          % (S[25]["exsharpe"], "맞음" if 0.78 <= S[25]["exsharpe"] <= 0.86 else "빗나감"))
    print("P4 베타 1.20~1.30      실측 %.2f     %s"
          % (b25b, "맞음" if 1.20 <= b25b <= 1.30 else "빗나감"))
    print("P5 알파 t 0.40~0.80    실측 %.2f     %s (1.5 미만 %s)"
          % (at25, "맞음" if 0.40 <= at25 <= 0.80 else "빗나감",
             "맞음" if at25 < 1.5 else "빗나감"))
    trn = {K: sorted(C[K][i] / COST_RT for i in range(n))[n // 2] for K in KS}
    print("P6 회전율 20%% 아래     실측 %.0f%% → %.0f%%   %s"
          % (100 * trn[10], 100 * trn[25], "맞음" if trn[25] < 0.20 else "빗나감"))

    print()
    print("── 참고 (판정에 안 쓴다) ─────────────────────────────────")
    for g in ("가치", "중립", "성장"):
        idx = [i for i in range(n) if rows[i]["reg"] == g]
        def cg(v):
            p = 1.0
            for i in idx:
                p *= 1 + v[i]
            return (p ** (12 / len(idx)) - 1) * 100
        print("  %-4s %3d개월 · 10종 %+6.2f%% · 25종 %+6.2f%% · SPY %+6.2f%%"
              % (g, len(idx), cg(R[10]), cg(R[25]), cg(SP)))
    wr = {K: 100 * sum(1 for i in range(n) if R[K][i] > SP[i]) / n for K in KS}
    print("  월 승률 vs SPY   10종 %.1f%% · 25종 %.1f%%" % (wr[10], wr[25]))

    doc = {"note": "다리당 25종판. 규약 PREREG-2026-09-08-PURE25.md. 얼린 측정. "
                   "🚨 x-pure10 과 나란히 싣는다.",
           "prereg": "be6a8414", "n": n, "window": [rows[0]["m"], rows[-1]["m"]],
           "thin": thin, "stats": {str(K): S[K] for K in KS}, "spy": ss,
           "f1": [d1, a1, t1], "f2": d2, "f3": {"vol": S[25]["vol"],
                                                "idio": [idio10, idio25]},
           "f4": [e25, e10], "f5": [S[10]["cagr"], S[25]["cagr"]],
           "f6": {"beta": [b10, b25b], "alpha": [al10, al25], "alpha_t": [at10, at25]},
           "winrate": wr, "turnover": trn,
           "rows": [{"m": x["m"], "reg": x["reg"],
                     "k10": round(x[10]["r"], 6), "k25": round(x[25]["r"], 6),
                     "spy": round(x["spy"], 6), "cash": round(x["cash"], 6)}
                    for x in rows]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
