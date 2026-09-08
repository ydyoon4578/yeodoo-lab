# -*- coding: utf-8 -*-
"""build/purewf.py — 국면별 배분을 자료로 고르되 **워크포워드로만 판정한다** → data/_purewf.json

규약: build/PREREG-2026-09-08-PUREWF.md (계산 전 커밋 306bc92b · 개정본).

이 랩 최초의 **워크포워드 하네스**다. 사용자가 nsel 제약을 명시적으로 풀었으므로
(2026-09-08 「결과를 바탕으로 전략을 수정하는 것 정도는 괜찮아」), 문제는 «고쳐도 되나» 가
아니라 «고친 것이 향후에도 작동하는지 어떻게 아나» 가 됐다. 그 답이 이 파일이다.

  파라미터  국면별 가치 비중 셋 (v_상승 · v_중립 · v_하락) · 0.00~1.00 · 0.05 간격 = 9,261칸
  선택 기준  초과 샤프(무위험이자를 뺀 것)
  워크포워드  warm 36개월 · 확장창 · 매월 t 를 0…t−1 로 고르고 t 에 적용

🚨 밖으로 내보내는 수는 **워크포워드 하나뿐**이다. 표본 내 수(사용자 제안 · 격자 최적)에는
  «성과» 라는 말을 안 붙이고 🟡·🔴 를 그대로 적는다(등록 §3).
🚨 다중검정 분모에 **1건**으로 센다 — 9,261건이 아니다. 탐색이 워크포워드 «안» 에서 일어나고
  밖으로 나가는 계열이 하나이기 때문이다.
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/purewf.py
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
OUT = os.path.join(DATA, "_purewf.json")
sys.path.insert(0, HERE)

TH = 0.20                       # DFII10 3개월 문턱(%p) — D13 카드. 🚨 안 건드린다
COST_RT = 0.0020                # 왕복 20bp
K = 10
WARM = 36                       # 첫 선택 전 최소 실적 — 등록 §2
GRID = [round(0.05 * i, 2) for i in range(21)]      # 0.00 ~ 1.00
REG = ("가치", "중립", "성장")   # v_상승 · v_중립 · v_하락 (국면 라벨은 «기우는 쪽» 이름)
CARD = (0.70, 0.50, 0.30)       # D13 카드 원본
USER = (0.50, 0.50, 0.30)       # 사용자 제안(개정) — 성장 50/50/70


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
            if eq / (sn * px[t][i]) <= 0:
                continue
            bm[t] = 1
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
        s = A["px"]["SPY"]
        rows.append(dict(m=dates[i1][:7], reg=g, gi=REG.index(g),
                         rv=sum(r1(t) for t in V) / K, rg=sum(r1(t) for t in G) / K,
                         V=set(V), G=set(G),
                         spy=(s[ad[d1]] / s[ad[d]] - 1) if (d in ad and d1 in ad) else 0.0,
                         cash=(asof(CB, _ck, d) or 0.0) / 100 / 12))

    n = len(rows)
    GI = [x["gi"] for x in rows]
    RV = [x["rv"] for x in rows]
    RG = [x["rg"] for x in rows]
    CASH = [x["cash"] for x in rows]
    SP = [x["spy"] for x in rows]

    def series(w, lo=0, hi=None):
        hi = n if hi is None else hi
        return [w[GI[i]] * RV[i] + (1 - w[GI[i]]) * RG[i] for i in range(lo, hi)]

    def exsh(v, rfv):
        s = sd(v)
        return 0.0 if s == 0 else ((sum(v) / len(v) - sum(rfv) / len(rfv)) * 12) / (s * math.sqrt(12))

    COMBOS = [(a, b, c) for a in GRID for b in GRID for c in GRID]
    L1 = {w: abs(w[0] - CARD[0]) + abs(w[1] - CARD[1]) + abs(w[2] - CARD[2]) for w in COMBOS}

    print("측정 %s ~ %s · %d개월 · 격자 %d칸 · warm %d"
          % (rows[0]["m"], rows[-1]["m"], n, len(COMBOS), WARM))
    cnt = {g: sum(1 for x in rows if x["reg"] == g) for g in REG}
    print("국면 분포  상승(가치기움) %d · 중립 %d · 하락(성장기움) %d"
          % (cnt["가치"], cnt["중립"], cnt["성장"]))

    # ── 워크포워드 ─────────────────────────────────────────────────
    wf, picks = [], []
    for t in range(WARM, n):
        best, bw = None, None
        rfv = CASH[:t]
        for w in COMBOS:
            v = series(w, 0, t)
            e = exsh(v, rfv)
            if best is None or e > best + 1e-12 or (
                    abs(e - best) <= 1e-12 and (L1[w], -w[0], -w[1], -w[2]) < bw):
                best, bw = e, (L1[w], -w[0], -w[1], -w[2])
                pick = w
        picks.append(pick)
        wf.append(pick[GI[t]] * RV[t] + (1 - pick[GI[t]]) * RG[t])

    oos = slice(WARM, n)
    OC = CASH[oos]
    print("표본 밖 %s ~ %s · %d개월" % (rows[WARM]["m"], rows[-1]["m"], len(wf)))
    ocnt = {g: sum(1 for x in rows[WARM:] if x["reg"] == g) for g in REG}
    print("  그 안의 국면 분포  상승 %d · 중립 %d · 하락 %d"
          % (ocnt["가치"], ocnt["중립"], ocnt["성장"]))

    CARD_O = series(CARD, WARM, n)
    USER_O = series(USER, WARM, n)
    SPY_O = SP[oos]

    print()
    print("🟢 표본 밖 (%d개월) — **이것만 결과다**" % len(wf))
    print("%-34s %8s %8s %10s %8s" % ("", "CAGR", "변동성", "초과 샤프", "MDD"))
    S = {}
    for lab, key, v in (("워크포워드 (자료가 고른 배분)", "wf", wf),
                        ("D13 카드 원본 0.70·0.50·0.30", "card", CARD_O),
                        ("S&P 500 TR", "spy", SPY_O),
                        ("🟡 사용자 제안 0.50·0.50·0.30", "user", USER_O)):
        s = stat(v, OC)
        S[key] = s
        print("%-34s %7.2f%% %7.2f%% %10.3f %7.2f%%"
              % (lab, s["cagr"], s["vol"], s["exsharpe"], s["mdd"]))

    print()
    print("── 판정 ──────────────────────────────────────────────────")
    d1 = S["wf"]["exsharpe"] - S["card"]["exsharpe"]
    d2 = S["wf"]["exsharpe"] - S["spy"]["exsharpe"]
    print("F1 🚨 워크포워드 − 카드   Δ%+.3f (%.3f vs %.3f)      → %s"
          % (d1, S["wf"]["exsharpe"], S["card"]["exsharpe"], "통과" if d1 > 0 else "기각"))
    print("F2 🚨 워크포워드 − SPY    Δ%+.3f (%.3f vs %.3f)      → %s"
          % (d2, S["wf"]["exsharpe"], S["spy"]["exsharpe"], "통과" if d2 > 0 else "기각"))

    # 표본 내 최적(전 구간) — 🔴 상한선일 뿐이다
    allsh = {}
    bestw, beste = None, None
    for w in COMBOS:
        e = exsh(series(w), CASH)
        allsh[w] = e
        if beste is None or e > beste + 1e-12 or (
                abs(e - beste) <= 1e-12 and L1[w] < L1[bestw]):
            beste, bestw = e, w
    gap = beste - S["wf"]["exsharpe"]
    print("F3 🚨 과최적화 간극 %+.3f  (🔴 표본 내 최적 %.3f · %s → 워크포워드 %.3f)  → %s"
          % (gap, beste, "·".join("%.2f" % x for x in bestw), S["wf"]["exsharpe"],
             "🚨 0.3 초과 — 첫 줄에 적는다" if gap > 0.3 else "0.3 이하"))
    chg = sum(1 for i in range(1, len(picks)) if picks[i] != picks[i - 1])
    uniq = len(set(picks))
    print("F4 🚨 선택이 %d번 바뀜 · 서로 다른 배분 %d가지                → %s"
          % (chg, uniq, "🚨 20회 초과 — 잡음을 좇는다" if chg > 20 else "통과"))

    # 비용 — 명단 교체 + 비중 변화
    def net_cost(wseq):
        prev, out = {}, []
        for j, t in enumerate(range(WARM, n)):
            w = wseq[j][GI[t]]
            wt = {}
            for tk in rows[t]["V"]:
                wt[tk] = wt.get(tk, 0.0) + w / K
            for tk in rows[t]["G"]:
                wt[tk] = wt.get(tk, 0.0) + (1 - w) / K
            out.append(COST_RT * 0.5 * sum(abs(wt.get(tk, 0.0) - prev.get(tk, 0.0))
                                           for tk in set(wt) | set(prev)))
            prev = wt
        return out
    cw = net_cost(picks)
    cc = net_cost([CARD] * len(wf))
    wfn = [wf[i] - cw[i] for i in range(len(wf))]
    cdn = [CARD_O[i] - cc[i] for i in range(len(wf))]
    e1, e2 = stat(wfn, OC)["exsharpe"], stat(cdn, OC)["exsharpe"]
    print("F5    비용 뒤  워크포워드 %.3f vs 카드 %.3f (Δ%+.3f)          → %s"
          % (e1, e2, e1 - e2, "통과" if e1 > e2 else "기각"))
    lo, hi = min(allsh.values()), max(allsh.values())
    print("F6 🚨 격자 폭 %.3f (최저 %.3f ~ 최고 %.3f)                    → %s"
          % (hi - lo, lo, hi,
             "평평하지 않다 — 과최적화 위험이 크다" if hi - lo >= 0.2 else
             "🚨 0.2 미만 — 어느 칸을 골라도 비슷하다 = 고를 값이 없다"))
    uc, cc_ = allsh[USER], allsh[CARD]
    print("F7 🟡 전 구간 표본 내  사용자 제안 %.3f vs 카드 %.3f (Δ%+.3f)  → %s"
          % (uc, cc_, uc - cc_, "제안이 낫다" if uc > cc_ else "🚨 제안이 카드를 못 넘는다"))

    print()
    print("── 예측 판정 ─────────────────────────────────────────────")
    print("P1 제안이 표본 내에서도 카드를 못 넘는다 (Δ 0.00~−0.10)  실측 Δ%+.3f  %s"
          % (uc - cc_, "맞음" if uc <= cc_ else "빗나감"))
    print("P2 워크포워드가 카드를 못 넘는다                          실측 Δ%+.3f  %s"
          % (d1, "맞음" if d1 <= 0 else "빗나감"))
    print("P3 과최적화 간극 0.4 초과                                실측 %+.3f  %s"
          % (gap, "맞음" if gap > 0.4 else "빗나감"))
    print("P4 선택이 20회 넘게 바뀐다                               실측 %d회   %s"
          % (chg, "맞음" if chg > 20 else "빗나감"))
    print("P5 격자 폭 0.7 초과                                      실측 %.3f  %s"
          % (hi - lo, "맞음" if hi - lo > 0.7 else "빗나감"))

    print()
    print("── 참고 (판정에 안 쓴다) ─────────────────────────────────")
    print("🟡 사용자 제안 — 전 구간 100개월 (표본 내이므로 «성과» 가 아니다)")
    su = stat(series(USER), CASH)
    sc = stat(series(CARD), CASH)
    print("   제안 CAGR %.2f%% · 초과샤프 %.3f  |  카드 CAGR %.2f%% · 초과샤프 %.3f"
          % (su["cagr"], su["exsharpe"], sc["cagr"], sc["exsharpe"]))
    print("🔴 표본 내 최적 %s — 초과샤프 %.3f · CAGR %.2f%% (상한선일 뿐이다)"
          % ("·".join("%.2f" % x for x in bestw), beste, stat(series(bestw), CASH)["cagr"]))
    from collections import Counter
    top = Counter(picks).most_common(5)
    print("워크포워드가 고른 배분 상위:")
    for w, c in top:
        print("   %s  %d개월 (%.0f%%) · 성장비중 %s"
              % ("·".join("%.2f" % x for x in w), c, 100 * c / len(picks),
                 "·".join("%.2f" % (1 - x) for x in w)))
    print("첫 선택 %s → 마지막 선택 %s"
          % ("·".join("%.2f" % x for x in picks[0]), "·".join("%.2f" % x for x in picks[-1])))

    doc = {"note": "국면별 배분의 워크포워드. 규약 PREREG-2026-09-08-PUREWF.md. 얼린 측정. "
                   "🚨 표본 내 수(user·best)는 결과가 아니다.",
           "prereg": "306bc92b", "n": n, "warm": WARM, "grid": len(COMBOS),
           "oos_window": [rows[WARM]["m"], rows[-1]["m"]], "n_oos": len(wf),
           "card": list(CARD), "user": list(USER), "best_is": list(bestw),
           "stats_oos": S, "f1": d1, "f2": d2, "f3_gap": gap, "f4_changes": chg,
           "f4_unique": uniq, "f5_net": [e1, e2], "f6_span": [lo, hi],
           "f7_insample": [uc, cc_],
           "picks": [list(w) for w in picks],
           "rows": [{"m": rows[WARM + i]["m"], "reg": rows[WARM + i]["reg"],
                     "wf": round(wf[i], 6), "card": round(CARD_O[i], 6),
                     "user": round(USER_O[i], 6), "spy": round(SPY_O[i], 6),
                     "cash": round(OC[i], 6)} for i in range(len(wf))]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
