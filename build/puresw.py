# -*- coding: utf-8 -*-
"""build/puresw.py — 가중을 원문 방식(스타일 점수 가중)으로 되돌린다 → data/_puresw.json

규약: build/PREREG-2026-09-08-PURESW.md (계산 전 커밋 8d498873).

  PURE25 에서 **가중 하나만** 바꾼다 —
      가치 다리  w(t) ∝ min(SV(t), 2.0)     다리 안에서 정규화
      성장 다리  w(t) ∝ min(SG(t), 2.0)     대칭
  다리 사이 배분(70/50/30)·신호·주기·종목수(다리당 25)·PIT 유니버스·비용은 그대로.

  2.0 캡은 원문의 수다(S&P U.S. Style Indices Methodology · STYLESCORE §3-2 —
  "index constituents are weighted by their Style Scores").

🚨 판정 셀은 K=25 두 칸(동일 vs 점수)이다. K=10 짝은 참고로만 싣는다.
🚨 RSP·QQQ 는 «싣기만» 한다 — 판정 잣대가 아니다(등록 §5).
🚨 이것은 시총가중이 아니다. 초대형주는 여전히 안 들어온다(등록 §0-1).
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/puresw.py
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
OUT = os.path.join(DATA, "_puresw.json")
sys.path.insert(0, HERE)

TH = 0.20
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}
COST_RT = 0.0020
CAP = 2.0                       # 🚨 원문의 수. 결과 보고 안 바꾼다
KS = (10, 25)
CELLS = [(K, w) for K in KS for w in ("ew", "sw")]
LABEL = {(10, "ew"): "10종 · 동일가중", (10, "sw"): "10종 · 점수가중",
         (25, "ew"): "25종 · 동일가중 (기준선)", (25, "sw"): "25종 · 점수가중 (전략)"}


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
    rows, ncap = [], [0, 0]
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
        ok = set()
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
            ok.add(t)
        if len(ok) < 100:
            continue
        pv = [t for t in P["pv"] if t in ok]
        pg = [t for t in P["pg"] if t in ok]
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
        rec = dict(m=dates[i1][:7], reg=g, w=w,
                   spy=(s[ad[d1]] / s[ad[d]] - 1) if (d in ad and d1 in ad) else 0.0,
                   cash=(asof(CB, _ck, d) or 0.0) / 100 / 12)

        def wts(names, S, mode):
            if mode == "ew":
                return {t: 1.0 / len(names) for t in names}
            raw = {}
            for t in names:
                v = min(S[t], CAP)
                if S[t] > CAP:
                    ncap[0] += 1
                ncap[1] += 1
                raw[t] = max(v, 1e-9)
            z = sum(raw.values())
            return {t: raw[t] / z for t in names}

        for K in KS:
            V, G = vs[:K], gs[:K]
            for mode in ("ew", "sw"):
                wv = wts(V, SV, mode)
                wg = wts(G, SG, mode)
                rv = sum(wv[t] * r1(t) for t in V)
                rg = sum(wg[t] * r1(t) for t in G)
                # 포트폴리오 전체 비중 = 다리배분 × 다리내 비중
                port = {}
                for t in V:
                    port[t] = port.get(t, 0.0) + w * wv[t]
                for t in G:
                    port[t] = port.get(t, 0.0) + (1 - w) * wg[t]
                rec[(K, mode)] = dict(
                    r=w * rv + (1 - w) * rg, port=port,
                    effn=1.0 / sum(x * x for x in port.values()),
                    effv=1.0 / sum(x * x for x in wv.values()),
                    mx=max(port.values()))
        rows.append(rec)

    n = len(rows)
    CASH = [x["cash"] for x in rows]
    SP = [x["spy"] for x in rows]
    R = {c: [x[c]["r"] for x in rows] for c in CELLS}

    def bench(t):
        out = []
        for x in rows:
            out.append(None)
        # 월말 쌍을 다시 잡는다
        idx = 0
        for k in range(len(ms) - 1):
            d, d1 = ms[k], ms[k + 1]
            if d not in di or d1 not in di:
                continue
            if idx >= n or dates[di[d1]][:7] != rows[idx]["m"]:
                continue
            s = A["px"].get(t)
            out[idx] = (s[ad[d1]] / s[ad[d]] - 1) if (s and d in ad and d1 in ad
                                                      and s[ad[d]] and s[ad[d1]]) else None
            idx += 1
        return out

    print("측정 %s ~ %s · %d개월 · 캡 %.1f 에 걸린 관측 %d/%d (%.1f%%)"
          % (rows[0]["m"], rows[-1]["m"], n, CAP, ncap[0], ncap[1],
             100 * ncap[0] / ncap[1] if ncap[1] else 0))

    def costs(c):
        prev, out = {}, []
        for x in rows:
            p = x[c]["port"]
            out.append(COST_RT * 0.5 * sum(abs(p.get(t, 0.0) - prev.get(t, 0.0))
                                           for t in set(p) | set(prev)))
            prev = p
        return out

    C = {c: costs(c) for c in CELLS}

    print()
    print("%-30s %8s %8s %10s %8s %7s" % ("", "CAGR", "변동성", "초과 샤프", "MDD", "유효N"))
    S = {}
    for c in CELLS:
        S[c] = stat(R[c], CASH)
        effn = sorted(x[c]["effn"] for x in rows)[n // 2]
        mark = " ←" if c == (25, "sw") else ""
        print("%-30s %7.2f%% %7.2f%% %10.3f %7.2f%% %7.1f%s"
              % (LABEL[c], S[c]["cagr"], S[c]["vol"], S[c]["exsharpe"],
                 S[c]["mdd"], effn, mark))
    B = {}
    for t, lab in (("SPY", "S&P 500 (SPY)"), ("RSP", "S&P 500 동일가중 (RSP)"),
                   ("QQQ", "NASDAQ 100 (QQQ)")):
        v = bench(t)
        if any(z is None for z in v):
            continue
        B[t] = stat(v, CASH)
        print("%-30s %7.2f%% %7.2f%% %10.3f %7.2f%%"
              % (lab, B[t]["cagr"], B[t]["vol"], B[t]["exsharpe"], B[t]["mdd"]))

    E, Sw = (25, "ew"), (25, "sw")
    print()
    print("── 판정 (K=25 두 칸) ─────────────────────────────────────")
    d1 = S[Sw]["exsharpe"] - S[E]["exsharpe"]
    a1, t1 = tt(R[Sw], R[E])
    print("F1 🚨 점수가중 − 동일가중  Δ%+.3f (%.3f vs %.3f) · 연 %+.2f%%p · t %.2f → %s"
          % (d1, S[Sw]["exsharpe"], S[E]["exsharpe"], a1, t1, "통과" if d1 > 0 else "기각"))
    ev = sorted(x[Sw]["effn"] for x in rows)
    evv = sorted(x[Sw]["effv"] for x in rows)
    print("F2 🚨 유효 종목수 중앙 %.1f (동일가중 %.1f) · 가치다리 안 %.1f/25       → %s"
          % (ev[n // 2], sorted(x[E]["effn"] for x in rows)[n // 2], evv[n // 2],
             "🚨 20 아래 — 이름만 25종이다" if ev[n // 2] < 20 else "통과"))
    print("F3    변동성 %.2f%% (동일가중 %.2f%%)" % (S[Sw]["vol"], S[E]["vol"]))
    e1 = stat([R[Sw][i] - C[Sw][i] for i in range(n)], CASH)["exsharpe"]
    e2 = stat([R[E][i] - C[E][i] for i in range(n)], CASH)["exsharpe"]
    trn = {c: 100 * sorted(C[c][i] / COST_RT for i in range(n))[n // 2] for c in (E, Sw)}
    print("F4    비용 뒤 %.3f vs %.3f (Δ%+.3f) · 월 회전 %.0f%% vs %.0f%%          → %s"
          % (e1, e2, e1 - e2, trn[Sw], trn[E], "통과" if e1 > e2 else "기각"))
    print("F5    벤치 대비 초과샤프  SPY %+.3f · RSP %+.3f · QQQ %+.3f"
          % (S[Sw]["exsharpe"] - B["SPY"]["exsharpe"],
             S[Sw]["exsharpe"] - B["RSP"]["exsharpe"],
             S[Sw]["exsharpe"] - B["QQQ"]["exsharpe"]))
    print("      QQQ(%.3f) → %s" % (B["QQQ"]["exsharpe"],
                                    "넘음" if S[Sw]["exsharpe"] > B["QQQ"]["exsharpe"]
                                    else "🚨 못 넘음 — 첫 줄에 적는다"))
    b0, al0, at0 = beta_of(R[E], SP)
    b1, al1, at1 = beta_of(R[Sw], SP)
    print("F6    베타 %.2f → %.2f · 알파 연 %+.2f%%p → %+.2f%%p · 알파 t %.2f → %.2f"
          % (b0, b1, al0, al1, at0, at1))
    big = sum(1 for x in rows if x[Sw]["mx"] > 0.15)
    print("F7    최대비중 15%% 초과인 달 %d/%d (%.0f%%) · 최대비중 중앙 %.1f%%      → %s"
          % (big, n, 100 * big / n,
             100 * sorted(x[Sw]["mx"] for x in rows)[n // 2],
             "🚨 절반 초과 — 적는다" if big > n / 2 else "통과"))

    print()
    print("── 예측 판정 ─────────────────────────────────────────────")
    print("P1 F1 을 못 넘는다        실측 Δ%+.3f   %s" % (d1, "맞음" if d1 <= 0 else "빗나감"))
    print("P2 유효 종목수 18~22      실측 %.1f      %s"
          % (ev[n // 2], "맞음" if 18 <= ev[n // 2] <= 22 else "빗나감"))
    print("P3 변동성 20.0~21.5%%     실측 %.2f%%   %s"
          % (S[Sw]["vol"], "맞음" if 20.0 <= S[Sw]["vol"] <= 21.5 else "빗나감"))
    print("P4 CAGR 방향은 예측 안 함 — 실측 %.2f%% (동일가중 %.2f%%)"
          % (S[Sw]["cagr"], S[E]["cagr"]))
    print("P5 QQQ 를 못 넘는다       실측 %s   %s"
          % ("못 넘음" if S[Sw]["exsharpe"] <= B["QQQ"]["exsharpe"] else "넘음",
             "맞음" if S[Sw]["exsharpe"] <= B["QQQ"]["exsharpe"] else "빗나감"))
    print("P6 회전율 25%% 이상        실측 %.0f%%      %s"
          % (trn[Sw], "맞음" if trn[Sw] >= 25 else "빗나감"))

    print()
    print("── 참고 (판정에 안 쓴다) ─────────────────────────────────")
    print("K=10 짝  동일가중 %.3f · 점수가중 %.3f (Δ%+.3f)"
          % (S[(10, "ew")]["exsharpe"], S[(10, "sw")]["exsharpe"],
             S[(10, "sw")]["exsharpe"] - S[(10, "ew")]["exsharpe"]))
    wr = {c: 100 * sum(1 for i in range(n) if R[c][i] > SP[i]) / n for c in (E, Sw)}
    print("월 승률 vs SPY  동일가중 %.1f%% · 점수가중 %.1f%%" % (wr[E], wr[Sw]))
    for g in ("가치", "중립", "성장"):
        idx = [i for i in range(n) if rows[i]["reg"] == g]
        def cg(v):
            p = 1.0
            for i in idx:
                p *= 1 + v[i]
            return (p ** (12 / len(idx)) - 1) * 100
        print("  %-4s %3d개월 · 동일 %+6.2f%% · 점수 %+6.2f%% · SPY %+6.2f%%"
              % (g, len(idx), cg(R[E]), cg(R[Sw]), cg(SP)))

    doc = {"note": "원문 스타일 점수 가중판. 규약 PREREG-2026-09-08-PURESW.md. 얼린 측정.",
           "prereg": "8d498873", "n": n, "cap": CAP,
           "window": [rows[0]["m"], rows[-1]["m"]],
           "cap_hit": [ncap[0], ncap[1]],
           "stats": {"%d-%s" % c: S[c] for c in CELLS},
           "bench": B, "f1": [d1, a1, t1],
           "f2": {"effn": ev[n // 2], "effn_ew": sorted(x[E]["effn"] for x in rows)[n // 2],
                  "effv": evv[n // 2]},
           "f4": [e1, e2, trn[Sw], trn[E]],
           "f6": {"beta": [b0, b1], "alpha": [al0, al1], "alpha_t": [at0, at1]},
           "f7": {"over15": big, "mx_med": sorted(x[Sw]["mx"] for x in rows)[n // 2]},
           "winrate": {"ew": wr[E], "sw": wr[Sw]},
           "rows": [{"m": rows[i]["m"], "reg": rows[i]["reg"],
                     "ew": round(R[E][i], 6), "sw": round(R[Sw][i], 6),
                     "spy": round(SP[i], 6), "cash": round(CASH[i], 6)}
                    for i in range(n)]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
