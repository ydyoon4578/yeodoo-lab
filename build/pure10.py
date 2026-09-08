# -*- coding: utf-8 -*-
"""build/pure10.py — 금리 국면 스타일 로테이션을 20종으로 좁힌다 → data/_pure10.json

규약: build/PREREG-2026-09-08-PURE10.md (계산 전 커밋 c1c8ac20).

  x-pure10  S&P Pure 규칙(WV=1 ∧ SV>mean+0.2) 안에서 SV·SG **상위 10씩**, 동일가중
  x-bm10    같은 후보에서 B/M 상위 10 = 가치 · 하위 10 = 성장  ← 1번 대조군
  넓은 판   같은 후보를 중앙값에서 반씩(= x-ssrot·x-bmrot 재현). 좁힘 효과를 재려는 것

  신호는 넷 다 같다 — DFII10 3개월 변화 ≥+20bp → 가치 70/성장 30 · ≤−20bp → 30/70 · 사이 50/50

🚨 B/M ≤ 0 을 공통 후보에서 뺀다(등록 §1-3). B/M 하위 10 의 90칸 중 85칸이 자본잠식이라
  대조군의 성장 다리가 「성장주」가 아니라 「장부가가 음수인 회사」가 된다.
🚨 WV 가 아니라 SV·SG 로 줄 세운다(등록 §1-2). WV 는 0/1 배분 비중이라 정렬을 못 한다.
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/pure10.py
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
OUT = os.path.join(DATA, "_pure10.json")
sys.path.insert(0, HERE)

TH = 0.20                       # DFII10 3개월 변화 문턱(%p) — D13 카드의 수
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}
COST_RT = 0.0020                # 왕복 20bp — F3. x-ssrot 과 같은 값
K = 10                          # 다리당 종목수 — 등록 §0-1. **한 크기만 돌린다**

RULES = ("pure10", "bm10", "ssrot", "bmrot")
LABEL = {"pure10": "x-pure10 (Pure 상위10)", "bm10": "x-bm10 (B/M 상위10 · 대조군)",
         "ssrot": "x-ssrot 재현 (넓은 판)", "bmrot": "x-bmrot 재현 (넓은 판)"}


def stat(v):
    m = sum(v) / len(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
    p = 1.0
    for x in v:
        p *= 1 + x
    cur = peak = 1.0
    mdd = 0.0
    for x in v:
        cur *= 1 + x
        peak = max(peak, cur)
        mdd = min(mdd, cur / peak - 1)
    return dict(cagr=(p ** (12 / len(v)) - 1) * 100, vol=sd * math.sqrt(12) * 100,
                sharpe=(m * 12) / (sd * math.sqrt(12)), mdd=mdd * 100)


def tt(a, b):
    d = [a[i] - b[i] for i in range(len(a))]
    m = sum(d) / len(d)
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1))
    return m * 12 * 100, m / (sd / math.sqrt(len(d)))


def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / ((sa * sb) or 1e-12)


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
    _rk = sorted(RY)

    def ry(d):
        k = None
        for key in _rk:
            if key <= d:
                k = key
            else:
                break
        return RY.get(k) if k else None

    def shift(d, back):
        y, m = int(d[:4]), int(d[5:7]) - back
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        return "%04d-%02d-%s" % (y, m, d[8:10])

    def aret(sid, d0, d1):
        s = A["px"].get(sid)
        if s and d0 in ad and d1 in ad and s[ad[d0]] and s[ad[d1]]:
            return s[ad[d1]] / s[ad[d0]] - 1
        return None

    def up(d, sid):
        m = A["macro"].get(sid) or {}
        ks = sorted(m)

        def asof(x):
            k = None
            for key in ks:
                if key <= x:
                    k = key
                else:
                    break
            return m.get(k) if k else None
        n0, p6 = asof(d), asof(shift(d, 6))
        return n0 is not None and p6 is not None and n0 - p6 > 0.25

    FU = TB.load_fund()

    def bm_of(t, d, i):
        f = FU.get(t)
        if not f:
            return None
        eq = TB.asof_fund(f.get("eq"), d)
        sn = TB.asof_fund(f.get("sh"), d)
        p = px[t][i]
        if eq is None or not sn or not p or sn <= 0 or p <= 0:
            return None
        return eq / (sn * p)

    rows, prevw = [], {r: {} for r in RULES}
    contrib = {r: collections.Counter() for r in RULES}
    secmon = []                                  # 가치 다리 섹터 쏠림(F7)
    legvol = {"v": [], "g": []}                  # 다리별 수익(P4)
    nshort = 0

    for k in range(len(ms) - 1):
        d, d1 = ms[k], ms[k + 1]
        if d not in di or d1 not in di:
            continue
        i, i1 = di[d], di[d1]
        P = panel[d]
        SV, SG = P["SV"], P["SG"]

        # ── 공통 후보: 그 달 채점 가능 · 두 시점 가격 있음 · B/M > 0 (등록 §1-3)
        cand, bm = [], {}
        for t in SV:
            if not (px.get(t) and px[t][i] and px[t][i1] and px[t][i] > 0):
                continue
            v = bm_of(t, d, i)
            if v is None or v <= 0:
                continue
            bm[t] = v
            cand.append(t)
        if len(cand) < 100:
            continue
        pv = [t for t in P["pv"] if t in bm]
        pg = [t for t in P["pg"] if t in bm]
        if len(pv) < K or len(pg) < K:
            nshort += 1
            continue

        now, p3 = ry(d), ry(shift(d, 3))
        ch = None if (now is None or p3 is None) else now - p3
        g = "중립" if ch is None else ("가치" if ch >= TH else "성장" if ch <= -TH else "중립")
        w = W[g]
        h = len(cand) // 2

        legs = {
            "pure10": (sorted(pv, key=lambda t: -SV[t])[:K],
                       sorted(pg, key=lambda t: -SG[t])[:K]),
            "bm10": (sorted(cand, key=lambda t: -bm[t])[:K],
                     sorted(cand, key=lambda t: bm[t])[:K]),
            "ssrot": (sorted(cand, key=lambda t: -SV[t])[:h],
                      sorted(cand, key=lambda t: -SG[t])[:h]),
            "bmrot": (sorted(cand, key=lambda t: -bm[t])[:h],
                      sorted(cand, key=lambda t: bm[t])[:h]),
        }

        def r1(t):
            return px[t][i1] / px[t][i] - 1

        out = {}
        for r in RULES:
            val, grw = legs[r]
            rv = sum(r1(t) for t in val) / len(val)
            rg = sum(r1(t) for t in grw) / len(grw)
            wt = {}
            for t in val:
                wt[t] = wt.get(t, 0.0) + w / len(val)
            for t in grw:
                wt[t] = wt.get(t, 0.0) + (1 - w) / len(grw)
            old = prevw[r]
            trn = 0.5 * sum(abs(wt.get(t, 0.0) - old.get(t, 0.0))
                            for t in set(wt) | set(old))
            prevw[r] = wt
            for t in val:
                contrib[r][t] += w * r1(t) / len(val)
            for t in grw:
                contrib[r][t] += (1 - w) * r1(t) / len(grw)
            out[r] = dict(r=w * rv + (1 - w) * rg, base=.5 * rv + .5 * rg,
                          cost=COST_RT * trn, val=set(val), grw=set(grw),
                          rv=rv, rg=rg, trn=trn)

        legvol["v"].append(out["pure10"]["rv"])
        legvol["g"].append(out["pure10"]["rg"])
        sc = collections.Counter((meta.get(t) or {}).get("sector") or "?"
                                 for t in legs["pure10"][0])
        secmon.append((sc.most_common(1)[0][0], sc.most_common(1)[0][1] / K))

        rows.append(dict(m=dates[i1][:7], d=d, reg=g, n=len(cand), npv=len(pv), npg=len(pg),
                         spy=aret("SPY", d, d1) or 0.0,
                         rpv=aret("RPV", d, d1), rpg=aret("RPG", d, d1),
                         up10=up(d, "DGS10"), up2=up(d, "DGS2"),
                         **{r: out[r] for r in RULES}))

    n = len(rows)
    print("측정 %s ~ %s · %d개월 · 공통 후보 중앙 %d종 (Pure 후보 중앙 가치 %d · 성장 %d)"
          % (rows[0]["m"], rows[-1]["m"], n, sorted(r["n"] for r in rows)[n // 2],
             sorted(r["npv"] for r in rows)[n // 2], sorted(r["npg"] for r in rows)[n // 2]))
    if nshort:
        print("⚠ Pure 후보가 %d종 미만이라 건너뛴 달 %d" % (K, nshort))

    R = {r: [x[r]["r"] for x in rows] for r in RULES}
    N = {r: [x[r]["r"] - x[r]["cost"] for x in rows] for r in RULES}
    sp = [x["spy"] for x in rows]
    base10 = [x["pure10"]["base"] for x in rows]
    pure_ew = [.5 * ((x["rpv"] or 0) + (x["rpg"] or 0)) for x in rows
               if x["rpv"] is not None and x["rpg"] is not None]

    print()
    print("%-26s %8s %8s %8s %8s %8s" % ("", "CAGR", "변동성", "샤프", "MDD", "월승률"))

    def line(lab, v):
        s = stat(v)
        wr = 100 * sum(1 for i in range(len(v)) if v[i] > sp[i]) / len(v)
        print("%-26s %7.2f%% %7.2f%% %8.3f %7.1f%% %7.1f%%"
              % (lab, s["cagr"], s["vol"], s["sharpe"], s["mdd"], wr))
        return s

    S = {}
    for r in RULES:
        S[r] = line(LABEL[r], R[r])
    line("틸트 없는 50/50 (20종)", base10)
    line("S&P 500 TR (SPY)", sp)
    if len(pure_ew) == n:
        line("RPV·RPG 50/50 (실제 지수)", pure_ew)

    print()
    print("── 판정 ──────────────────────────────────────────────")
    a, t = tt(R["pure10"], R["bm10"])
    an, tn = tt(N["pure10"], N["bm10"])
    print("F1  x-pure10 − x-bm10 샤프 : %+.3f  (%.3f vs %.3f)"
          % (S["pure10"]["sharpe"] - S["bm10"]["sharpe"],
             S["pure10"]["sharpe"], S["bm10"]["sharpe"]))
    print("F4  초과 연 %+.2f%%p · t %.2f" % (a, t))
    print("F3  비용 뒤 연 %+.2f%%p · t %.2f  (샤프 %.3f vs %.3f)"
          % (an, tn, stat(N["pure10"])["sharpe"], stat(N["bm10"])["sharpe"]))

    rho10 = corr(R["pure10"], R["bm10"])
    rhow = corr(R["ssrot"], R["bmrot"])
    print()
    print("F2 🚨 좁힌 판 두 수익 상관  %.4f   (>0.99 면 «좁혀도 안 갈린다»)" % rho10)
    print("   넓은 판 두 수익 상관     %.4f   ← 원문서 실측 0.9993" % rhow)
    ov10 = sorted(len(x["pure10"]["val"] & x["bm10"]["val"]) / K for x in rows)
    ovw = sorted(len(x["ssrot"]["val"] & x["bmrot"]["val"]) /
                 max(1, len(x["ssrot"]["val"] | x["bmrot"]["val"])) for x in rows)
    print("   가치 다리 명단 겹침  좁힌 판 중앙 %.0f%% · 넓은 판 중앙 %.0f%%"
          % (100 * ov10[n // 2], 100 * ovw[n // 2]))

    sw = sum(1 for i in range(1, n) if rows[i]["reg"] != rows[i - 1]["reg"])
    print()
    print("F5  국면 전환 %d회 (>6 이어야 한다)" % sw)
    cnt = collections.Counter(x["reg"] for x in rows)
    print("    국면 분포  " + " · ".join("%s %d개월(%.0f%%)" % (g, c, 100 * c / n)
                                          for g, c in cnt.most_common()))

    tot = sum(contrib["pure10"].values())
    top = contrib["pure10"].most_common(5)
    print()
    print("F6  한 종목 쏠림 — 누적 기여 상위 (전체 누적 산술합 %.1f%%)" % (100 * tot))
    for tk, c in top:
        print("      %-6s %+6.1f%%p  = 누적의 %5.1f%%"
              % (tk, 100 * c, 100 * c / tot if tot else 0))
    f6 = 100 * top[0][1] / tot if tot else 0

    big = sum(1 for _s, f in secmon if f > 0.5)
    sc = collections.Counter(s for s, _f in secmon)
    print()
    print("F7  가치 다리 섹터 쏠림 — 한 섹터 50%% 초과인 달 %d/%d (%.0f%%)"
          % (big, n, 100 * big / n))
    print("      최대섹터 분포  " + " · ".join("%s %d" % (s, c) for s, c in sc.most_common(4)))

    ex = [R["pure10"][i] - R["bm10"][i] for i in range(n)]
    tote = sum(ex)
    mx = max(ex, key=abs)
    f8 = 100 * abs(mx / tote) if tote else 0
    print()
    print("F8  |초과| 최대 한 달이 누적의 %.0f%%   (누적 초과 연 %+.2f%%p — |0.5| 미만이면 안 읽는다)"
          % (f8, a))

    print()
    print("P3·P4 검증")
    sv_ = stat(legvol["v"])
    sg_ = stat(legvol["g"])
    print("      가치 다리 단독 변동성 %.2f%% · 성장 다리 단독 변동성 %.2f%%  → %s"
          % (sv_["vol"], sg_["vol"],
             "성장이 더 크다(P4 맞음)" if sg_["vol"] > sv_["vol"] else "가치가 더 크다(P4 빗나감)"))
    print("      x-pure10 변동성 %.2f%% (P3: 22%% 이상 예측) · 넓은 판 %.2f%%"
          % (S["pure10"]["vol"], S["ssrot"]["vol"]))
    print("      월 회전율 중앙  x-pure10 %.0f%% · x-bm10 %.0f%%"
          % (100 * sorted(x["pure10"]["trn"] for x in rows)[n // 2],
             100 * sorted(x["bm10"]["trn"] for x in rows)[n // 2]))

    print()
    print("금리 인상 구간 × SPY 대비 (참고 — 판정은 전 구간에서 했다)")
    for lab, sel in (("10년물 +25bp", lambda r: r["up10"]),
                     ("2년물 +25bp", lambda r: r["up2"]),
                     ("둘 다", lambda r: r["up10"] and r["up2"]),
                     ("인상기 아님", lambda r: not (r["up10"] or r["up2"]))):
        v = [x for x in rows if sel(x)]
        if len(v) < 8:
            continue
        aa, ta = tt([x["pure10"]["r"] for x in v], [x["spy"] for x in v])
        bb, tb = tt([x["bm10"]["r"] for x in v], [x["spy"] for x in v])
        print("  %-14s %3d개월 · pure10 %+7.2f%%p(t %5.2f) · bm10 %+7.2f%%p(t %5.2f)"
              % (lab, len(v), aa, ta, bb, tb))

    # ── 🚨 선견 보정 레그 — 등록 §6 이 예고한 한계를 실측한다 ──────────────
    #   그 시점 SPX ∪ NDX 멤버가 아니었던 종목을 후보에서 뺀다. **선견만** 지운다 —
    #   생존(지수에서 빠져 오늘 518종에 없는 종목)은 가격이 없어 못 지운다.
    #   ⚠ 이것은 판정 레그가 아니다. 판정은 위의 등록한 레그에서 이미 났다.
    def memb(mm):
        x = IH.get(mm[:7])
        return (set(x.get("spx") or []) | set(x.get("ndx") or [])) if x else None

    look = {"pure10": [0, 0], "bm10": [0, 0]}
    lookleg = {"pure10_v": [0, 0], "pure10_g": [0, 0], "bm10_v": [0, 0], "bm10_g": [0, 0]}
    for x in rows:
        U = memb(x["d"])
        if U is None:
            continue
        for r in ("pure10", "bm10"):
            for side, names in (("v", x[r]["val"]), ("g", x[r]["grw"])):
                ok = sum(1 for _t in names if _t in U)
                lookleg["%s_%s" % (r, side)][0] += ok
                lookleg["%s_%s" % (r, side)][1] += len(names)
                look[r][0] += ok
                look[r][1] += len(names)
    print()
    print("── 선견 보정 (등록 §6 · 판정 레그가 아니다) ──────────────────")
    print("    그 시점 지수 «밖» 이었던 칸")
    for key in ("pure10_v", "pure10_g", "bm10_v", "bm10_g"):
        ok, tot_ = lookleg[key]
        if tot_:
            print("      %-10s %4d / %4d = 선견 %5.1f%%"
                  % (key, tot_ - ok, tot_, 100 * (1 - ok / tot_)))

    PR, PB, PBASE, PSP, PV, PG = [], [], [], [], [], []
    for k in range(len(ms) - 1):
        d, d1 = ms[k], ms[k + 1]
        if d not in di or d1 not in di:
            continue
        U = memb(d)
        if U is None:
            continue
        i, i1 = di[d], di[d1]
        P = panel[d]
        SV, SG = P["SV"], P["SG"]
        cand, bm = [], {}
        for _q in SV:
            if _q not in U:
                continue
            if not (px.get(_q) and px[_q][i] and px[_q][i1] and px[_q][i] > 0):
                continue
            v = bm_of(_q, d, i)
            if v is None or v <= 0:
                continue
            bm[_q] = v
            cand.append(_q)
        if len(cand) < 100:
            continue
        pv = [_q for _q in P["pv"] if _q in bm]
        pg = [_q for _q in P["pg"] if _q in bm]
        if len(pv) < K or len(pg) < K:
            continue
        now, p3 = ry(d), ry(shift(d, 3))
        ch = None if (now is None or p3 is None) else now - p3
        g = "중립" if ch is None else ("가치" if ch >= TH else "성장" if ch <= -TH else "중립")
        w = W[g]

        def rr(_q):
            return px[_q][i1] / px[_q][i] - 1

        def lg(ns):
            return sum(rr(_q) for _q in ns) / len(ns)

        rv = lg(sorted(pv, key=lambda z: -SV[z])[:K])
        rg = lg(sorted(pg, key=lambda z: -SG[z])[:K])
        PR.append(w * rv + (1 - w) * rg)
        PBASE.append(.5 * rv + .5 * rg)
        PV.append(rv)
        PG.append(rg)
        PB.append(w * lg(sorted(cand, key=lambda z: -bm[z])[:K])
                  + (1 - w) * lg(sorted(cand, key=lambda z: bm[z])[:K]))
        PSP.append(aret("SPY", d, d1) or 0.0)

    pa, pb = stat(PR), stat(PB)
    pex, pt = tt(PR, PB)
    sx, st_ = tt(PR, PSP)
    ox, ot = tt(R["pure10"], sp)
    bx, bt = tt(PBASE, PR)
    print()
    print("    %-22s %8s %8s %8s" % ("", "CAGR", "변동성", "샤프"))
    print("    %-22s %7.2f%% %7.2f%% %8.3f  ← 등록한 레그 %.2f%% / %.3f"
          % ("x-pure10 (선견보정)", pa["cagr"], pa["vol"], pa["sharpe"],
             S["pure10"]["cagr"], S["pure10"]["sharpe"]))
    print("    %-22s %7.2f%% %7.2f%% %8.3f  ← 등록한 레그 %.2f%% / %.3f"
          % ("x-bm10  (선견보정)", pb["cagr"], pb["vol"], pb["sharpe"],
             S["bm10"]["cagr"], S["bm10"]["sharpe"]))
    print("    F1 Δ샤프 %+.3f → **%+.3f** · F4 t %.2f → **%.2f**"
          % (S["pure10"]["sharpe"] - S["bm10"]["sharpe"], pa["sharpe"] - pb["sharpe"], t, pt))
    print("    SPY 대비 연 %+.2f%%p(t %.2f) → **%+.2f%%p(t %.2f)**" % (ox, ot, sx, st_))
    print("    F2 상관 %.4f → %.4f  (유지되면 §3 의 결론은 안 흔들린다)"
          % (rho10, corr(PR, PB)))
    pv_, pg_ = stat(PV), stat(PG)
    print("    다리별 CAGR  가치 %.2f%% → %.2f%% · 성장 %.2f%% → %.2f%%"
          % (stat(legvol["v"])["cagr"], pv_["cagr"], stat(legvol["g"])["cagr"], pg_["cagr"]))
    print("    다리별 변동성 가치 %.2f%% · 성장 %.2f%%  (등록 레그는 %.2f%% · %.2f%%)"
          % (pv_["vol"], pg_["vol"], sv_["vol"], sg_["vol"]))
    tb_, tbt = tt(R["pure10"], base10)
    print("    틸트가 버는 것  등록 레그 %+.2f%%p(t %.2f) → 보정 %+.2f%%p(t %.2f)"
          % (tb_, tbt, -bx, -bt))

    doc = {"note": "금리 국면 스타일 로테이션 20종판. 규약 PREREG-2026-09-08-PURE10.md. 얼린 측정.",
           "prereg": "c1c8ac20", "window": [rows[0]["m"], rows[-1]["m"]], "n": n, "k": K,
           "f1_sharpe": [S["pure10"]["sharpe"], S["bm10"]["sharpe"]],
           "f2_rho_narrow": rho10, "f2_rho_wide": rhow,
           "f3_net": [an, tn], "f4": [a, t], "f5_switches": sw,
           "f6_top": [[x, y] for x, y in top], "f6_pct": f6,
           "f7_months_over50": big, "f8_pct": f8,
           "leg_vol": [sv_["vol"], sg_["vol"]],
           "lookahead": {k: [v[1] - v[0], v[1]] for k, v in lookleg.items()},
           "pit": {"n": len(PR), "pure10": pa, "bm10": pb,
                   "f1_dsharpe": pa["sharpe"] - pb["sharpe"], "f4_t": pt,
                   "vs_spy": [sx, st_], "rho": corr(PR, PB),
                   "leg_cagr": [pv_["cagr"], pg_["cagr"]],
                   "leg_vol": [pv_["vol"], pg_["vol"]],
                   "tilt": [-bx, -bt]},
           "stats": {r: S[r] for r in RULES},
           "rows": [{"m": x["m"], "reg": x["reg"],
                     **{r: round(x[r]["r"], 6) for r in RULES},
                     "spy": round(x["spy"], 6)} for x in rows]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
