# -*- coding: utf-8 -*-
"""build/puregp.py — 가치 다리에 수익성 관문(Novy-Marx) → data/_puregp.json

규약: build/PREREG-2026-09-08-PUREGP.md (계산 전 커밋 f4a2cff5).

  ① x-pure10      가치 다리 = Pure Value 후보 «전부» 중 SV 상위 10        (현행)
  ② x-pure10-nf   가치 다리 = 그중 **GP/자산 채점 가능한 것만** 중 SV 상위 10  ← 1번 대조군
  ③ x-pure10-gp   가치 다리 = 같은 후보 중 **GP/자산 상위 10**              ← 전략

  ② − ① = 후보를 좁힌 효과(사실상 금융·통신·유틸리티 제외)
  ③ − ② = 수익성으로 정렬한 효과  ← 이 등록이 묻는 것

🚨 ②와 ③은 후보 집합이 완전히 같고 정렬 기준만 다르다. ③이 ①을 이겼다고
  «수익성이 먹혔다» 고 말하지 않는다 — 그 답은 ③ − ② 다(등록 §2-1).
🚨 성장 다리는 안 건드린다. 신호·틸트·주기·PIT 유니버스·비용 전부 x-pure10 그대로.
🚨 수익성은 랩에 이미 있는 tech_backtest._gross_profit 를 부른다 — 두 벌로 만들지 않는다.
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/puregp.py
"""
from __future__ import annotations
import collections
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
OUT = os.path.join(DATA, "_puregp.json")
sys.path.insert(0, HERE)

TH = 0.20
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}
COST_RT = 0.0020
K = 10
LEGS = ("orig", "nf", "gp")
LABEL = {"orig": "① x-pure10 (현행 · SV 전체)",
         "nf": "② x-pure10-nf (채점가능 · SV)",
         "gp": "③ x-pure10-gp (채점가능 · GP/자산)"}


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
    nbad = [0]

    def gpa(t, d):
        """매출총이익(TTM) ÷ 총자산(시점). 원문 §2 의 정의 그대로."""
        f = FU.get(t)
        if not f:
            return None
        g, _rv = TB._gross_profit(f, d)
        a = TB.asof_fund(f.get("asset"), d)
        if g is None:
            nbad[0] += 1
            return None
        if not a or a <= 0:
            return None
        return g / a

    rows, skipped = [], []
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
            if eq is None or not sn or sn <= 0 or eq / (sn * px[t][i]) <= 0:
                continue
            bm[t] = 1
            cand.append(t)
        if len(cand) < 100:
            continue
        pv = [t for t in P["pv"] if t in bm]
        pg = [t for t in P["pg"] if t in bm]
        if len(pv) < K or len(pg) < K:
            continue
        # 🚨 GP/자산 채점 가능한 후보 — ②·③ 이 공유한다
        G = {t: gpa(t, d) for t in pv}
        sc = [t for t in pv if G[t] is not None]
        if len(sc) < K:
            skipped.append((dates[i1][:7], len(sc)))
            continue

        now, p3 = asof(RY, _rk, d), asof(RY, _rk, shift(d, 3))
        ch = None if (now is None or p3 is None) else now - p3
        g = "중립" if ch is None else ("가치" if ch >= TH else "성장" if ch <= -TH else "중립")
        w = W[g]

        def r1(t):
            return px[t][i1] / px[t][i] - 1

        V = {"orig": sorted(pv, key=lambda t: -SV[t])[:K],
             "nf": sorted(sc, key=lambda t: -SV[t])[:K],
             "gp": sorted(sc, key=lambda t: -G[t])[:K]}
        GL = sorted(pg, key=lambda t: -SG[t])[:K]
        rg = sum(r1(t) for t in GL) / K
        s = A["px"]["SPY"]
        rec = dict(m=dates[i1][:7], d=d, reg=g, w=w, rg=rg, G=set(GL), nsc=len(sc),
                   spy=(s[ad[d1]] / s[ad[d]] - 1) if (d in ad and d1 in ad) else 0.0,
                   cash=(asof(CB, _ck, d) or 0.0) / 100 / 12)
        for key in LEGS:
            rv = sum(r1(t) for t in V[key]) / K
            rec[key] = dict(rv=rv, r=w * rv + (1 - w) * rg, V=set(V[key]))
        rows.append(rec)

    n = len(rows)
    CASH = [x["cash"] for x in rows]
    SP = [x["spy"] for x in rows]
    R = {key: [x[key]["r"] for x in rows] for key in LEGS}
    LV = {key: [x[key]["rv"] for x in rows] for key in LEGS}

    print("측정 %s ~ %s · %d개월" % (rows[0]["m"], rows[-1]["m"], n))
    if skipped:
        print("⚠ 채점 가능 후보 10종 미만이라 뺀 달 %d개: %s"
              % (len(skipped), " · ".join("%s(%d종)" % z for z in skipped)))
    nsc = sorted(x["nsc"] for x in rows)
    print("   채점 가능 후보수 중앙 %d · 최소 %d · 최대 %d"
          % (nsc[n // 2], nsc[0], nsc[-1]))
    print("   매출총이익을 못 낸 관측 %d건 (태그 없음 + gp+cogs≠rev 태깅 불신)" % nbad[0])

    # 비용
    def costs(key):
        prev, out = {}, []
        for x in rows:
            wt = {}
            for t in x[key]["V"]:
                wt[t] = wt.get(t, 0.0) + x["w"] / K
            for t in x["G"]:
                wt[t] = wt.get(t, 0.0) + (1 - x["w"]) / K
            out.append(COST_RT * 0.5 * sum(abs(wt.get(t, 0.0) - prev.get(t, 0.0))
                                           for t in set(wt) | set(prev)))
            prev = wt
        return out

    print()
    print("%-32s %8s %8s %10s %8s" % ("", "CAGR", "변동성", "초과 샤프", "MDD"))
    S, SL = {}, {}
    for key in LEGS:
        S[key] = stat(R[key], CASH)
        SL[key] = stat(LV[key], CASH)
        print("%-32s %7.2f%% %7.2f%% %10.3f %7.2f%%"
              % (LABEL[key], S[key]["cagr"], S[key]["vol"],
                 S[key]["exsharpe"], S[key]["mdd"]))
    ss = stat(SP, CASH)
    print("%-32s %7.2f%% %7.2f%% %10.3f %7.2f%%"
          % ("S&P 500 TR (SPY)", ss["cagr"], ss["vol"], ss["exsharpe"], ss["mdd"]))

    print()
    print("── 판정 ──────────────────────────────────────────────────")
    d1 = S["gp"]["exsharpe"] - S["nf"]["exsharpe"]
    a1, t1 = tt(R["gp"], R["nf"])
    print("F1 🚨 ③ − ② (수익성의 순효과)  Δ샤프 %+.3f · 연 %+.2f%%p · t %.2f  → %s"
          % (d1, a1, t1, "통과" if d1 > 0 else "기각"))
    print("F2    가치 다리 단독  ③ %.2f%%/%.3f/MDD %.2f%%  vs  ② %.2f%%/%.3f/MDD %.2f%%  → %s"
          % (SL["gp"]["cagr"], SL["gp"]["exsharpe"], SL["gp"]["mdd"],
             SL["nf"]["cagr"], SL["nf"]["exsharpe"], SL["nf"]["mdd"],
             "통과" if SL["gp"]["exsharpe"] > SL["nf"]["exsharpe"] else "기각"))

    dn = [i for i in range(n) if rows[i]["reg"] == "성장"]
    def cg(v, idx):
        p = 1.0
        for i in idx:
            p *= 1 + v[i]
        return (p ** (12 / len(idx)) - 1) * 100
    print("F3 🚨 금리 하락 국면 %d개월 가치 다리 CAGR — ③ %+.2f%% (① %+.2f%% · ② %+.2f%%)  → %s"
          % (len(dn), cg(LV["gp"], dn), cg(LV["orig"], dn), cg(LV["nf"], dn),
             "통과" if cg(LV["gp"], dn) > cg(LV["orig"], dn) else "기각"))

    cah = {key: sum(1 for x in rows if "CAH" in x[key]["V"]) for key in LEGS}
    ov = sorted(len(rows[i]["gp"]["V"] & rows[i]["nf"]["V"]) / K for i in range(n))
    print("F4 🚨 관문이 일을 했나 — CAH 상주 ① %d/%d → ③ %d/%d · ③∩② 겹침 중앙 %.0f%%  → %s"
          % (cah["orig"], n, cah["gp"], n, 100 * ov[n // 2],
             "🚨 아무것도 안 했다" if (cah["gp"] > cah["orig"] / 2 and ov[n // 2] > 0.7)
             else "통과"))

    cg_, cn_ = costs("gp"), costs("nf")
    e1 = stat([R["gp"][i] - cg_[i] for i in range(n)], CASH)["exsharpe"]
    e2 = stat([R["nf"][i] - cn_[i] for i in range(n)], CASH)["exsharpe"]
    print("F5    비용 뒤 ③ %.3f vs ② %.3f (Δ%+.3f)                        → %s"
          % (e1, e2, e1 - e2, "통과" if e1 > e2 else "기각"))

    ch1 = S["nf"]["exsharpe"] - S["orig"]["exsharpe"]
    print("F6 🚨 채널 분해   ② − ① (후보 제한) %+.3f   |   ③ − ② (수익성) %+.3f"
          % (ch1, d1))
    print("      → %s" % ("🚨 변화의 대부분이 «섹터 제외» 다 — 첫 줄에 적는다"
                          if abs(ch1) > abs(d1) else "수익성 쪽이 더 크다"))

    print("F7    가치 다리 섹터 (종목-월 비중)")
    for key in ("orig", "gp"):
        c = collections.Counter((meta.get(t) or {}).get("sector") or "?"
                                for x in rows for t in x[key]["V"])
        tot = sum(c.values())
        print("      %-6s %s" % (key, " · ".join("%s %.0f%%" % (s, 100 * v / tot)
                                                 for s, v in c.most_common(5))))
    print("F8    ③ − SPY 초과샤프 %+.3f  → %s"
          % (S["gp"]["exsharpe"] - ss["exsharpe"],
             "넘음" if S["gp"]["exsharpe"] > ss["exsharpe"] else "🚨 못 넘음 — 첫 줄에 적는다"))

    print()
    print("── 예측 판정 ─────────────────────────────────────────────")
    print("P1 F1 을 못 넘는다            실측 Δ%+.3f  %s" % (d1, "맞음" if d1 <= 0 else "빗나감"))
    fin = {key: 100 * sum(1 for x in rows for t in x[key]["V"]
                          if (meta.get(t) or {}).get("sector") == "Financials")
           / (n * K) for key in ("orig", "gp")}
    print("P2 금융 29.8%% → 3%% 아래      실측 %.1f%% → %.1f%%  %s"
          % (fin["orig"], fin["gp"], "맞음" if fin["gp"] < 3 else "빗나감"))
    print("P3 가치 다리 MDD 개선         실측 %.2f%% → %.2f%%  %s"
          % (SL["orig"]["mdd"], SL["gp"]["mdd"],
             "맞음" if SL["gp"]["mdd"] > SL["orig"]["mdd"] else "빗나감"))
    print("P4 ③∩② 겹침 50%% 미만        실측 %.0f%%  %s"
          % (100 * ov[n // 2], "맞음" if ov[n // 2] < 0.5 else "빗나감"))
    print("P5 |②−①| > |③−②|            실측 %.3f vs %.3f  %s"
          % (abs(ch1), abs(d1), "맞음" if abs(ch1) > abs(d1) else "빗나감"))

    print()
    print("── 참고 (판정에 안 쓴다) ─────────────────────────────────")
    top = collections.Counter(t for x in rows for t in x["gp"]["V"]).most_common(8)
    print("③ 가치 다리 단골:", " · ".join("%s(%d)" % z for z in top))
    print("① 가치 다리 단골:",
          " · ".join("%s(%d)" % z for z in
                     collections.Counter(t for x in rows for t in x["orig"]["V"]).most_common(8)))

    doc = {"note": "가치 다리 수익성 관문. 규약 PREREG-2026-09-08-PUREGP.md. 얼린 측정.",
           "prereg": "f4a2cff5", "n": n, "window": [rows[0]["m"], rows[-1]["m"]],
           "skipped": skipped, "nbad_gp": nbad[0],
           "stats": S, "leg_stats": SL, "spy": ss,
           "f1": [d1, a1, t1], "f3_down": {k: cg(LV[k], dn) for k in LEGS},
           "f4": {"cah": cah, "overlap_med": ov[n // 2]}, "f5": [e1, e2],
           "f6": {"pool": ch1, "profit": d1}, "fin_share": fin,
           "rows": [{"m": x["m"], "reg": x["reg"],
                     **{k: round(x[k]["r"], 6) for k in LEGS},
                     "spy": round(x["spy"], 6), "cash": round(x["cash"], 6),
                     "nsc": x["nsc"]} for x in rows]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
