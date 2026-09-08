# -*- coding: utf-8 -*-
"""build/purevm.py — 20종 스타일 로테이션 + 변동성 관리 → data/_purevm.json

규약: build/PREREG-2026-09-08-PUREVM.md (계산 전 커밋 9acae0d0).

  기준선  x-pure10 의 **선견 보정 레그** — 그 시점 SPX ∪ NDX 멤버만 후보로 쓴다
  얹는 것 w = min(1, 확장창 목표변동성 ÷ 직전 6개월 실현변동성) · 상한 1.0(레버리지 없음)
          출처 Barroso & Santa-Clara (JFE 2015) · 구현 style_top_pdf.VM_LOOK/VM_WARM

🚨 목표·직전창 둘 다 m «미만» 까지만 본다 — m 달 비중이 m−1 달까지의 자료로 정해진다.
  목표를 전 표본으로 잡으면 그것이 선견이고, Liu·Tang·Zhou(2019)가 지적한 함정이 그것이다.
🚨 고르는 규칙은 한 글자도 안 바꾼다. 이 파일은 **크기만** 만진다.
🚨 얼린 측정 — 입력(_style_score.json)이 커밋 금지라 러너가 재생산 못 한다. 자동 재굽기 금지.

    python build/purevm.py
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
OUT = os.path.join(DATA, "_purevm.json")
sys.path.insert(0, HERE)

TH = 0.20                       # DFII10 3개월 문턱(%p) — D13 카드
W = {"가치": 0.7, "중립": 0.5, "성장": 0.3}
COST_RT = 0.0020                # 왕복 20bp — PURE10 과 같은 값
K = 10                          # 다리당 종목수 — PURE10 §0-1
VM_LOOK = 6                     # 직전 개월 수 — style_top_pdf.py:1757 의 값
VM_WARM = 24                    # 최소 실적. 그 전에는 비중 1 — style_top_pdf.py:1758


def sd(v):
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def stat(v):
    m = sum(v) / len(v)
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
    return dict(cagr=(p ** (12 / len(v)) - 1) * 100, vol=s * math.sqrt(12) * 100,
                sharpe=(m * 12) / (s * math.sqrt(12)), mdd=mdd * 100)


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
    a = (mr - b * ms)
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

    # ── 1. 기준선(선견 보정 레그)을 다시 만든다 ─────────────────────────
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
        w = W[g]

        def r1(t):
            return px[t][i1] / px[t][i] - 1

        V = sorted(pv, key=lambda t: -SV[t])[:K]
        G = sorted(pg, key=lambda t: -SG[t])[:K]
        rv = sum(r1(t) for t in V) / K
        rg = sum(r1(t) for t in G) / K
        s = A["px"]["SPY"]
        spy = s[ad[d1]] / s[ad[d]] - 1 if (d in ad and d1 in ad) else 0.0
        rc = (asof(CB, _ck, d) or 0.0) / 100 / 12
        rows.append(dict(m=dates[i1][:7], d=d, reg=g, tw=w, V=V, G=G,
                         r=w * rv + (1 - w) * rg, base=.5 * rv + .5 * rg,
                         spy=spy, cash=rc))

    n = len(rows)
    R0 = [x["r"] for x in rows]
    B0 = [x["base"] for x in rows]
    SP = [x["spy"] for x in rows]
    CASH = [x["cash"] for x in rows]

    # ── 2. 변동성 관리 비중 ───────────────────────────────────────────
    def vm_w(r):
        out = []
        for i in range(len(r)):
            if i < VM_WARM:
                out.append(1.0)
                continue
            tgt = sd(r[:i])
            v = sd(r[i - VM_LOOK:i])
            out.append(1.0 if v <= 0 else min(1.0, tgt / v))
        return out

    WV = vm_w(R0)
    WB = vm_w(B0)
    for i, x in enumerate(rows):
        x["w"] = WV[i]

    def apply(r, w, cash0=True):
        return [w[i] * r[i] + (0.0 if cash0 else (1 - w[i]) * CASH[i]) for i in range(n)]

    RVM = apply(R0, WV, True)
    RVM_C = apply(R0, WV, False)          # 현금에 DGS3MO — 참고판(등록 §1-4)
    BVM = apply(B0, WB, True)

    # ── 3. 비용 — 명단 교체분 + 비중 변화분 ───────────────────────────
    def costs(useW):
        prev, out = {}, []
        for i, x in enumerate(rows):
            w = x["w"] if useW else 1.0
            wt = {}
            for t in x["V"]:
                wt[t] = wt.get(t, 0.0) + w * x["tw"] / K
            for t in x["G"]:
                wt[t] = wt.get(t, 0.0) + w * (1 - x["tw"]) / K
            out.append(COST_RT * 0.5 * sum(abs(wt.get(t, 0.0) - prev.get(t, 0.0))
                                           for t in set(wt) | set(prev)))
            prev = wt
        return out

    C1, C0 = costs(True), costs(False)
    RVM_N = [RVM[i] - C1[i] for i in range(n)]
    R0_N = [R0[i] - C0[i] for i in range(n)]

    # ── 4. 대조군 — 베타 맞춘 레버리지 SPY ────────────────────────────
    b0, a0, t0 = beta_of(R0, SP)
    LEV = [b0 * SP[i] - (b0 - 1) * CASH[i] for i in range(n)]

    print("측정 %s ~ %s · %d개월 (앞 %d달은 w=1 · 관리 구간 %d달)"
          % (rows[0]["m"], rows[-1]["m"], n, VM_WARM, n - VM_WARM))
    print()
    print("%-30s %8s %8s %8s %8s" % ("", "CAGR", "변동성", "샤프", "MDD"))
    S = {}
    for lab, key, v in (("x-pure10-vm (변동성 관리)", "vm", RVM),
                        ("x-pure10 (관리 없음 · 기준선)", "base", R0),
                        ("SPY × %.2f 조달비용 뺌 (베타 일치)" % b0, "lev", LEV),
                        ("S&P 500 TR (SPY)", "spy", SP),
                        ("틸트 없는 50/50 + 관리", "nt", BVM),
                        ("[참고] 현금 = DGS3MO 판", "vmc", RVM_C)):
        s = stat(v)
        S[key] = s
        print("%-30s %7.2f%% %7.2f%% %8.3f %7.2f%%"
              % (lab, s["cagr"], s["vol"], s["sharpe"], s["mdd"]))

    print()
    print("── 판정 ──────────────────────────────────────────────────")
    d1 = S["vm"]["sharpe"] - S["base"]["sharpe"]
    d2 = S["vm"]["sharpe"] - S["lev"]["sharpe"]
    d3 = S["vm"]["sharpe"] - S["spy"]["sharpe"]
    a, t = tt(RVM, R0)
    print("F1  관리 − 기준선  Δ샤프 %+.3f  (%.3f vs %.3f) · 연 %+.2f%%p · t %.2f  → %s"
          % (d1, S["vm"]["sharpe"], S["base"]["sharpe"], a, t, "통과" if d1 > 0 else "기각"))
    print("F2  관리 − 레버리지SPY Δ샤프 %+.3f  (%.3f vs %.3f)          → %s"
          % (d2, S["vm"]["sharpe"], S["lev"]["sharpe"], "통과" if d2 > 0 else "기각"))
    print("F3  관리 − SPY      Δ샤프 %+.3f  (%.3f vs %.3f)          → %s"
          % (d3, S["vm"]["sharpe"], S["spy"]["sharpe"],
             "넘음" if d3 > 0 else "🚨 못 넘음 — 첫 줄에 적는다"))
    sn = stat(RVM_N)["sharpe"]
    bn = stat(R0_N)["sharpe"]
    print("F4  비용 뒤  관리 %.3f vs 기준선 %.3f (Δ%+.3f)             → %s"
          % (sn, bn, sn - bn, "통과" if sn > bn else "기각"))
    b1, a1, t1 = beta_of(RVM, SP)
    print("F5  베타 %.2f → %.2f (문턱 1.10)                            → %s"
          % (b0, b1, "통과" if b1 < 1.10 else "🚨 시장 노출을 못 줄였다"))
    print("    알파 연 %+.2f%%p → %+.2f%%p · t %.2f → %.2f" % (a0, a1, t0, t1))

    imp = [RVM[i] - R0[i] for i in range(n)]
    tot = sum(imp)
    top3 = sorted(range(n), key=lambda i: -imp[i])[:3]
    sh = sum(imp[i] for i in top3) / tot if tot else float("nan")
    print("F6  개선분 누적 %+.2f%%p · 상위 3개월이 %.0f%% (%s)         → %s"
          % (100 * tot, 100 * sh, " ".join(rows[i]["m"] for i in top3),
             "통과" if sh <= 0.5 else "🚨 몇 달이 다 한다 — 첫 줄에 적는다"))
    mg = [x["w"] for x in rows[VM_WARM:]]
    one = sum(1 for w in mg if w >= 0.999)
    print("F7  관리 구간에서 w=1 인 달 %d/%d (%.0f%%) · w 중앙 %.2f · 최소 %.2f  → %s"
          % (one, len(mg), 100 * one / len(mg), sorted(mg)[len(mg) // 2], min(mg),
             "통과" if one / len(mg) <= 0.8 else "🚨 사실상 작동 안 함"))

    print()
    print("── 예측 판정 ─────────────────────────────────────────────")
    print("P1 변동성 18~21%%   실측 %.2f%%   %s"
          % (S["vm"]["vol"], "맞음" if 18 <= S["vm"]["vol"] <= 21 else "빗나감"))
    print("P2 CAGR 16~18%%    실측 %.2f%%   %s"
          % (S["vm"]["cagr"], "맞음" if 16 <= S["vm"]["cagr"] <= 18 else "빗나감"))
    print("P3 샤프 0.90~1.00  실측 %.3f    %s"
          % (S["vm"]["sharpe"], "맞음" if 0.90 <= S["vm"]["sharpe"] <= 1.00 else "빗나감"))
    print("P4 F2 는 예측 안 함 — 실측 %s" % ("통과" if d2 > 0 else "기각"))
    print("P5 개선이 2020-03·2022 상반기에 몰릴 것 — 상위 3개월 %s"
          % " ".join(rows[i]["m"] for i in top3))
    print("P6 베타 1.05~1.15   실측 %.2f    %s"
          % (b1, "맞음" if 1.05 <= b1 <= 1.15 else "빗나감"))

    print()
    print("── 참고 (판정에 안 쓴다) ─────────────────────────────────")
    s76 = stat(RVM[VM_WARM:])
    b76 = stat(R0[VM_WARM:])
    print("관리 구간 76개월만  관리 %.2f%%/%.3f · 기준선 %.2f%%/%.3f · SPY %.2f%%/%.3f"
          % (s76["cagr"], s76["sharpe"], b76["cagr"], b76["sharpe"],
             stat(SP[VM_WARM:])["cagr"], stat(SP[VM_WARM:])["sharpe"]))
    print("현금 = DGS3MO 판    %.2f%% / 샤프 %.3f  (현금 0 판은 %.2f%% / %.3f)"
          % (S["vmc"]["cagr"], S["vmc"]["sharpe"], S["vm"]["cagr"], S["vm"]["sharpe"]))
    lo = sorted(rows[VM_WARM:], key=lambda x: x["w"])[:6]
    print("w 가 가장 낮았던 달:", " · ".join("%s %.2f" % (x["m"], x["w"]) for x in lo))

    doc = {"note": "20종 스타일 로테이션 + 변동성 관리. 규약 PREREG-2026-09-08-PUREVM.md. 얼린 측정.",
           "prereg": "9acae0d0", "window": [rows[0]["m"], rows[-1]["m"]], "n": n,
           "vm": {"look": VM_LOOK, "warm": VM_WARM, "cap": 1.0},
           "stats": S, "f1": [d1, a, t], "f2": d2, "f3": d3, "f4": [sn, bn],
           "f5": {"beta": [b0, b1], "alpha": [a0, a1], "alpha_t": [t0, t1]},
           "f6": {"total": tot, "top3_share": sh, "months": [rows[i]["m"] for i in top3]},
           "f7": {"w_one": one, "n_managed": len(mg), "w_med": sorted(mg)[len(mg) // 2],
                  "w_min": min(mg)},
           "rows": [{"m": x["m"], "reg": x["reg"], "w": round(x["w"], 4),
                     "base": round(R0[i], 6), "vm": round(RVM[i], 6),
                     "lev": round(LEV[i], 6), "spy": round(SP[i], 6)}
                    for i, x in enumerate(rows)]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
