# -*- coding: utf-8 -*-
"""build/purels.py — 20종 스타일 로테이션의 롱숏판 → data/_purels.json

규약: build/PREREG-2026-09-08-PURELS.md (계산 전 커밋 b9175b27).

  고르는 규칙은 x-pure10 그대로(선견 보정 레그 — 그 시점 SPX ∪ NDX 멤버만).
  바꾸는 것은 배분을 «순노출» 로 읽는 것뿐이다 —

    DFII10 3개월 ≥+20bp → 순노출 +0.40  (가치 롱 40% · 성장 숏 40%)
    그 사이            →         0     (포지션 없음 · 현금)
    DFII10 3개월 ≤−20bp → 순노출 −0.40

  월수익 = 순노출 × (r_가치 − r_성장) + 현금(DGS3MO/12)

🚨 판정은 «초과 샤프»(무위험이자를 뺀 것)로 한다. 랩의 stat() 은 안 빼는데, 그 식으로
  롱온리와 롱숏을 나란히 놓으면 롱숏이 부당하게 유리하다(등록 §1-4).
🚨 대차료를 안 문다(랩 전체 관례). 대신 **손익분기 대차료**를 낸다 — F5.
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/purels.py
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
OUT = os.path.join(DATA, "_purels.json")
sys.path.insert(0, HERE)

TH = 0.20                       # DFII10 3개월 문턱(%p) — D13 카드
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}
NET = {g: 2 * w - 1 for g, w in W.items()}      # 0.4 / 0.0 / −0.4 — 등록 §1-2
COST_RT = 0.0020                # 왕복 20bp — 앞의 두 등록과 같은 값
K = 10


def sd(v):
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def stat(v, rf=None):
    """랩 관례 샤프와 초과 샤프를 같이 낸다(등록 §1-4)."""
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
    ex = None if rf is None else ((m - sum(rf) / n) * 12) / (s * math.sqrt(12))
    return dict(cagr=(p ** (12 / n) - 1) * 100, vol=s * math.sqrt(12) * 100,
                sharpe=(m * 12) / (s * math.sqrt(12)), exsharpe=ex, mdd=mdd * 100)


def tstat(v):
    return (sum(v) / len(v)) / (sd(v) / math.sqrt(len(v)))


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

    dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
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

    def shift(d, back):
        y, mo = int(d[:4]), int(d[5:7]) - back
        y += (mo - 1) // 12
        mo = (mo - 1) % 12 + 1
        return "%04d-%02d-%s" % (y, mo, d[8:10])

    FU = TB.load_fund()
    rows = []
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
        cand, bm = [], {}
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
            if eq is None or not sn or sn <= 0:
                continue
            v = eq / (sn * px[t][i])
            if v <= 0:
                continue
            bm[t] = v
            cand.append(t)
        if len(cand) < 100:
            continue
        pv = [t for t in P["pv"] if t in bm]
        pg = [t for t in P["pg"] if t in bm]
        if len(pv) < K or len(pg) < K:
            continue
        now, p3 = asof(RY, _rk, d), asof(RY, _rk, shift(d, 3))
        ch = None if (now is None or p3 is None) else now - p3
        g = "중립" if ch is None else ("가치" if ch >= TH else "성장" if ch <= -TH else "중립")

        def r1(t):
            return px[t][i1] / px[t][i] - 1

        V = sorted(pv, key=lambda t: -SV[t])[:K]
        G = sorted(pg, key=lambda t: -SG[t])[:K]
        rv = sum(r1(t) for t in V) / K
        rg = sum(r1(t) for t in G) / K
        s = A["px"]["SPY"]
        spy = s[ad[d1]] / s[ad[d]] - 1 if (d in ad and d1 in ad) else 0.0
        rows.append(dict(m=dates[i1][:7], reg=g, net=NET[g], V=V, G=G, rv=rv, rg=rg,
                         lo=W[g] * rv + (1 - W[g]) * rg,      # 롱온리 기준선
                         spy=spy, cash=(asof(CB, _ck, d) or 0.0) / 100 / 12))

    n = len(rows)
    SPD = [x["net"] * (x["rv"] - x["rg"]) for x in rows]     # 스프레드(현금 제외)
    CASH = [x["cash"] for x in rows]
    LS = [SPD[i] + CASH[i] for i in range(n)]
    LO = [x["lo"] for x in rows]
    SP = [x["spy"] for x in rows]

    # 비용 — 총노출 회전율(롱·숏 다리 교체 + 순노출 변화 전부)
    prev, CST = {}, []
    for x in rows:
        wt = {}
        for t in x["V"]:
            wt[t] = wt.get(t, 0.0) + x["net"] / K
        for t in x["G"]:
            wt[t] = wt.get(t, 0.0) - x["net"] / K
        CST.append(COST_RT * 0.5 * sum(abs(wt.get(t, 0.0) - prev.get(t, 0.0))
                                       for t in set(wt) | set(prev)))
        prev = wt
    SPD_N = [SPD[i] - CST[i] for i in range(n)]
    LS_N = [LS[i] - CST[i] for i in range(n)]

    flat = sum(1 for x in rows if x["net"] == 0)
    print("측정 %s ~ %s · %d개월 (포지션 없는 달 %d = %.0f%%)"
          % (rows[0]["m"], rows[-1]["m"], n, flat, 100 * flat / n))
    print()
    print("%-30s %8s %8s %9s %9s %8s"
          % ("", "CAGR", "변동성", "랩 샤프", "초과 샤프", "MDD"))
    S = {}
    for lab, key, v in (("x-pure10-ls (롱숏 + 현금)", "ls", LS),
                        ("  └ 스프레드만 (현금 제외)", "spd", SPD),
                        ("x-pure10 (롱온리 · 기준선)", "lo", LO),
                        ("S&P 500 TR (SPY)", "spy", SP),
                        ("현금 (DGS3MO)", "cash", CASH)):
        s = stat(v, CASH)
        S[key] = s
        print("%-30s %7.2f%% %7.2f%% %9.3f %9.3f %7.2f%%"
              % (lab, s["cagr"], s["vol"], s["sharpe"], s["exsharpe"], s["mdd"]))

    print()
    print("── 판정 ──────────────────────────────────────────────────")
    b, al, at = beta_of(LS, SP)
    b0, al0, at0 = beta_of(LO, SP)
    print("F1  베타 |%.3f| < 0.30 ?   (롱온리 기준선은 %.2f)              → %s"
          % (b, b0, "통과" if abs(b) < 0.30 else "🚨 기각 — 시장을 여전히 진다"))
    t2 = tstat(SPD)
    print("F2 🚨 스프레드 평균 연 %+.2f%%p · t %.2f  (문턱 1.5)          → %s"
          % (1200 * sum(SPD) / n, t2, "통과" if t2 >= 1.5 else "기각"))
    d3 = S["ls"]["exsharpe"] - S["lo"]["exsharpe"]
    print("F3  초과 샤프 %.3f vs 기준선 %.3f (Δ%+.3f)                   → %s"
          % (S["ls"]["exsharpe"], S["lo"]["exsharpe"], d3, "통과" if d3 > 0 else "기각"))
    t4 = tstat(SPD_N)
    print("F4  비용 뒤 연 %+.2f%%p · t %.2f                              → %s"
          % (1200 * sum(SPD_N) / n, t4, "통과" if t4 >= 1.5 else "기각"))

    # F5 손익분기 대차료 — 숏 다리 평잔에 연율 f 를 물리면 t 가 1.5 가 되는 f
    grs = [abs(x["net"]) for x in rows]              # 숏 다리 평잔(자기자본 대비)
    mg = sum(grs) / n
    m5, s5 = sum(SPD) / n, sd(SPD)
    need = m5 - 1.5 * s5 / math.sqrt(n)              # t=1.5 가 되는 평균
    fee = (m5 - need) / mg * 12 * 100 if mg > 0 else float("nan")
    fee0 = m5 / mg * 12 * 100 if mg > 0 else float("nan")   # 평균이 0 이 되는 대차료
    print("F5 🚨 손익분기 대차료 — 연 %.2f%% 를 물면 t 가 1.5 로 떨어지고, "
          "연 %.2f%% 면 평균이 0 이 된다" % (max(0.0, fee), max(0.0, fee0)))
    print("      (숏 다리 평잔 %.0f%% · 문턱 연 1%%)                        → %s"
          % (100 * mg, "통과" if fee >= 1.0 else "🚨 발동 — 실행 불가에 가깝다"))
    print("F6 🚨 포지션 없는 달 %d/%d (%.0f%%) — 그 달은 현금만 번다"
          % (flat, n, 100 * flat / n))

    # F7 국면별 기여
    print("F7  국면별 스프레드 기여")
    tot = sum(SPD)
    for g in ("가치", "중립", "성장"):
        v = [i for i in range(n) if rows[i]["reg"] == g]
        c = sum(SPD[i] for i in v)
        print("      %-4s %3d개월 · 순노출 %+.1f · 누적 %+6.2f%%p = 전체의 %5.1f%% "
              "· 다리차 평균 %+.2f%%/월"
              % (g, len(v), NET[g], 100 * c, 100 * c / tot if tot else 0,
                 100 * sum(rows[i]["rv"] - rows[i]["rg"] for i in v) / max(1, len(v))))
    mx = max(abs(sum(SPD[i] for i in range(n) if rows[i]["reg"] == g)) for g in ("가치", "성장"))
    print("      한 국면이 70%% 넘게 만드는가 → %s"
          % ("🚨 그렇다" if tot and mx / abs(tot) > 0.7 else "아니다"))
    t8 = tstat([SPD[i] - CASH[i] for i in range(n)])
    print("F8  스프레드 − 현금 : 연 %+.2f%%p · t %.2f                    → %s"
          % (1200 * (sum(SPD) - sum(CASH)) / n, t8,
             "통과" if sum(SPD) > sum(CASH) else "🚨 기각 — 현금만도 못하다"))

    print()
    print("── 예측 판정 ─────────────────────────────────────────────")
    print("P1 베타 |0.15| 아래       실측 %+.3f   %s"
          % (b, "맞음" if abs(b) < 0.15 else "빗나감"))
    print("P2 F2 를 못 넘는다 (t 0.3~1.2)  실측 t %.2f   %s"
          % (t2, "맞음" if t2 < 1.5 else "빗나감 — 예상보다 좋다"))
    print("P3 성장 국면이 대부분을 만든다  → §F7 참조")
    print("P4 CAGR 5~9%%             실측 %.2f%%   %s"
          % (S["ls"]["cagr"], "맞음" if 5 <= S["ls"]["cagr"] <= 9 else "빗나감"))
    print("P5 손익분기 대차료 연 3%% 미만  실측 %.2f%%   %s"
          % (max(0.0, fee), "맞음" if fee < 3.0 else "빗나감"))

    print()
    print("── 참고 (판정에 안 쓴다) ─────────────────────────────────")
    idx = [i for i in range(n) if rows[i]["net"] != 0]
    s59 = stat([LS[i] for i in idx], [CASH[i] for i in idx])
    print("포지션 있는 %d개월만  CAGR %.2f%% · 변동성 %.2f%% · 초과 샤프 %.3f"
          % (len(idx), s59["cagr"], s59["vol"], s59["exsharpe"]))
    ws = sorted(range(n), key=lambda i: SPD[i])
    print("최악 3개월:", " · ".join("%s %+.1f%%(%s)" % (rows[i]["m"], 100 * SPD[i], rows[i]["reg"])
                                    for i in ws[:3]))
    print("최고 3개월:", " · ".join("%s %+.1f%%(%s)" % (rows[i]["m"], 100 * SPD[i], rows[i]["reg"])
                                    for i in ws[-3:]))
    print("월 승률(스프레드 > 0) %.0f%% · 포지션 있는 달만 %.0f%%"
          % (100 * sum(1 for x in SPD if x > 0) / n,
             100 * sum(1 for i in idx if SPD[i] > 0) / len(idx)))

    doc = {"note": "20종 스타일 로테이션 롱숏판. 규약 PREREG-2026-09-08-PURELS.md. 얼린 측정.",
           "prereg": "b9175b27", "window": [rows[0]["m"], rows[-1]["m"]], "n": n,
           "net": NET, "flat_months": flat, "stats": S,
           "f1": {"beta": b, "beta_lo": b0}, "f2": [1200 * sum(SPD) / n, t2],
           "f3": [S["ls"]["exsharpe"], S["lo"]["exsharpe"]],
           "f4": [1200 * sum(SPD_N) / n, t4],
           "f5": {"fee_t15": fee, "fee_zero": fee0, "gross_short": mg},
           "f6": flat, "f8": t8, "alpha": [al, at],
           "rows": [{"m": rows[i]["m"], "reg": rows[i]["reg"], "net": rows[i]["net"],
                     "spd": round(SPD[i], 6), "ls": round(LS[i], 6),
                     "lo": round(LO[i], 6), "spy": round(SP[i], 6),
                     "cash": round(CASH[i], 6)} for i in range(n)]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
