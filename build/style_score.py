# -*- coding: utf-8 -*-
"""build/style_score.py — S&P 스타일 점수를 랩 유니버스에 적용 → data/_style_score.json

규약: build/PREREG-2026-09-03-STYLESCORE.md (계산 전 커밋 5a95f5495).
원천: S&P U.S. Style Indices Methodology (S&P Dow Jones Indices) — 여섯 요인·표준화·
      바스켓·블렌드 배분·Pure 편입 규칙을 원문 그대로 옮겼다.

  성장 3요인  3년 주당순이익 «변화액» ÷ 주가 · 3년 주당매출 성장률 · 12개월 모멘텀
  가치 3요인  장부가/주가 · 순이익/주가 · 매출/주가
  → 각 요인 z 표준화 → 3요인 단순평균 = SG · SV (가중치 동일, 원문 규정)
  → RG/RV 오름차순 정렬 → 시총 33% 성장 · 34% 블렌드 · 33% 가치
  → 블렌드는 부록 I 거리식으로 시총 배분, 0.8 이상이면 1.0 으로 반올림
  → Pure = W=1 이면서 점수 > 평균+0.2, 점수는 2.0 상한

🚨 이 스크립트는 **분류만 만든다.** 전략이 아니다(등록 §4).
🚨 원문은 S&P TMI(약 3,000종)를 표준화 모집단으로 쓰는데 이 랩에 그 유니버스가 없어
  518종을 쓴다. 그것이 실제 지수와의 가장 큰 차이다(등록 §2). 모집단을 결과 보고
  바꾸지 않는다.
🚨 얼린 측정 — 산출물은 밑줄 접두로 두고 커밋하지 않는다.

    python build/style_score.py
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
OUT = os.path.join(DATA, "_style_score.json")     # 밑줄 = 로컬 전용
sys.path.insert(0, HERE)

# ── 원문의 상수 — 전부 방법론 PDF 의 수다. 결과를 보고 만지지 않는다 ────────
CAP_G = 0.33        # 성장 바스켓 = 시총 상위 33%
CAP_V = 0.33        # 가치 바스켓 = 시총 하위 33%
ROUND_W = 0.80      # 배분 비중이 이 이상이면 1.0 으로 반올림
PURE_MARGIN = 0.20  # Pure 편입 = 점수 > 평균 + 0.2
PURE_CAP = 2.0      # Pure 가중용 점수 상한


def zs(vals):
    """전체 집합 평균·표준편차로 표준화. 원문: standardized by … mean … standard deviation."""
    n = len(vals)
    m = sum(vals) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / n)
    if sd <= 0:
        return [0.0] * n
    return [(v - m) / sd for v in vals]


def main():
    import tech_backtest as TB

    dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
    FU = TB.load_fund()
    tickers = sorted(px)
    me = [i for i in range(len(dates) - 1) if dates[i][:7] != dates[i + 1][:7]]
    me = [i for i in me if dates[i] >= "2016-01-01"]

    def persh(f, key, d, sn):
        """주당 값 — 총액 계열을 그 시점 주식수로 나눈다."""
        v = TB.ttm2(f.get(key), f.get(key + "_a"), d)
        return (v / sn) if (v is not None and sn) else None

    def back_ttm(f, key, d, yrs):
        """yrs 년 전 시점의 12개월 값. _shift 는 **빼는** 함수다."""
        return TB.ttm2(f.get(key), f.get(key + "_a"), TB._shift(d, 365 * yrs))

    panel, drop = {}, {"factor": 0}
    for i in me:
        d = dates[i]
        raw = {}
        for t in tickers:
            f = FU.get(t)
            if not f:
                continue
            sn = TB.asof_fund(f.get("sh"), d)
            p = px[t][i]
            if not (sn and p and sn > 0 and p > 0):
                continue
            mv = sn * p

            # ── 가치 3요인 — 전부 «÷ 주가» 다 ───────────────────────────
            eq = TB.asof_fund(f.get("eq"), d)
            ni = TB.ttm2(f.get("ni"), f.get("ni_a"), d)
            rev = TB.ttm2(f.get("rev"), f.get("rev_a"), d)
            bp = (eq / mv) if eq is not None else None
            ep = (ni / mv) if ni is not None else None
            sp = (rev / mv) if rev is not None else None

            # ── 성장 3요인 ────────────────────────────────────────────
            # ① 3년 주당순이익 «변화액» ÷ 주가.
            #   🚨 «3년 EPS 성장률» 이 아니다 — 원문은 Three-Year Change in EPS **over
            #     Price per Share** 다(등록 §1). 흔한 오독이라 여기 적어 둔다.
            eps0 = TB.ttm2(f.get("eps"), f.get("eps_a"), d)
            g1 = None
            for yrs in (3, 2, 1):        # 원문: 3년이 없으면 2년, 그것도 없으면 1년
                e_b = back_ttm(f, "eps", d, yrs)
                if eps0 is not None and e_b is not None:
                    g1 = (eps0 - e_b) / p
                    break
            # ② 3년 주당매출 성장률(연복리). 같은 3→2→1 폴백.
            g2 = None
            if rev is not None and sn:
                s0 = rev / sn
                for yrs in (3, 2, 1):
                    r_b = back_ttm(f, "rev", d, yrs)
                    sn_b = TB.asof_fund(f.get("sh"), TB._shift(d, 365 * yrs))
                    if r_b is not None and sn_b and sn_b > 0 and r_b > 0:
                        s_b = r_b / sn_b
                        if s_b > 0:
                            g2 = (s0 / s_b) ** (1.0 / yrs) - 1.0
                            break
            # ③ 모멘텀 — 12개월 가격변화율
            g3 = TB.ret(px[t], i, 252)

            if None in (bp, ep, sp, g1, g2, g3):
                drop["factor"] += 1
                continue
            raw[t] = dict(mv=mv, bp=bp, ep=ep, sp=sp, g1=g1, g2=g2, g3=g3)

        if len(raw) < 100:
            continue
        ts = sorted(raw)
        # ── 표준화 → 점수 ──────────────────────────────────────────────
        Z = {k: zs([raw[t][k] for t in ts]) for k in ("bp", "ep", "sp", "g1", "g2", "g3")}
        SG = {t: (Z["g1"][j] + Z["g2"][j] + Z["g3"][j]) / 3 for j, t in enumerate(ts)}
        SV = {t: (Z["bp"][j] + Z["ep"][j] + Z["sp"][j]) / 3 for j, t in enumerate(ts)}

        # ── 순위 → RG/RV 정렬 ─────────────────────────────────────────
        #   원문: 점수가 가장 높은 종목이 1위. 성장순위 낮고 가치순위 높은 것이 «순수 성장».
        RG = {t: r + 1 for r, t in enumerate(sorted(ts, key=lambda x: -SG[x]))}
        RV = {t: r + 1 for r, t in enumerate(sorted(ts, key=lambda x: -SV[x]))}
        order = sorted(ts, key=lambda t: RG[t] / RV[t])      # 오름차순 = 성장 쪽이 앞

        tot = sum(raw[t]["mv"] for t in ts)
        gset, vset, acc = set(), set(), 0.0
        for t in order:                                       # 위에서부터 시총 33% = 성장
            if acc >= CAP_G * tot:
                break
            gset.add(t); acc += raw[t]["mv"]
        acc = 0.0
        for t in reversed(order):                             # 아래에서부터 33% = 가치
            if acc >= CAP_V * tot:
                break
            if t in gset:
                break
            vset.add(t); acc += raw[t]["mv"]
        blend = [t for t in ts if t not in gset and t not in vset]

        # ── 부록 I — 바스켓 중점 넷 ───────────────────────────────────
        def avg(s, sc):
            return (sum(sc[t] for t in s) / len(s)) if s else 0.0
        AVG_, AVV = avg(vset, SG), avg(vset, SV)      # 가치바스켓의 성장·가치 평균
        AGG, AGV = avg(gset, SG), avg(gset, SV)       # 성장바스켓의 성장·가치 평균

        W = {}
        for t in gset:
            W[t] = (0.0, 1.0)                          # (WV, WG)
        for t in vset:
            W[t] = (1.0, 0.0)
        for t in blend:
            sg, sv = SG[t], SV[t]
            if sg >= AGG:
                dg = abs(sv - AGV)
            elif sv <= AGV:
                dg = abs(AGG - sg)
            else:
                dg = math.hypot(sv - AGV, AGG - sg)
            if sv >= AVV:
                dv = abs(sg - AVG_)
            elif sg <= AVG_:
                dv = abs(AVV - sv)
            else:
                dv = math.hypot(sv - AVV, AVG_ - sg)
            s = dg + dv
            wv, wg = (0.5, 0.5) if s <= 0 else (dg / s, dv / s)
            if wv >= ROUND_W:
                wv, wg = 1.0, 0.0
            elif wg >= ROUND_W:
                wv, wg = 0.0, 1.0
            W[t] = (wv, wg)

        # ── Pure ─────────────────────────────────────────────────────
        mSG = sum(SG[t] for t in ts) / len(ts)
        mSV = sum(SV[t] for t in ts) / len(ts)
        pv = [t for t in ts if W[t][0] == 1.0 and SV[t] > mSV + PURE_MARGIN]
        pg = [t for t in ts if W[t][1] == 1.0 and SG[t] > mSG + PURE_MARGIN]

        panel[d] = dict(
            n=len(ts), tot=tot,
            g_cap=sum(raw[t]["mv"] for t in gset) / tot,
            v_cap=sum(raw[t]["mv"] for t in vset) / tot,
            n_g=len(gset), n_v=len(vset), n_b=len(blend),
            n_pv=len(pv), n_pg=len(pg),
            wsum=sum(W[t][0] + W[t][1] for t in ts) / len(ts),
            vcap=sum(raw[t]["mv"] * W[t][0] for t in ts) / tot,
            gcap=sum(raw[t]["mv"] * W[t][1] for t in ts) / tot,
            SG=SG, SV=SV, W=W, pv=pv, pg=pg, mv={t: raw[t]["mv"] for t in ts},
            bp={t: raw[t]["bp"] for t in ts})

    ds = sorted(panel)
    print("월말 %d개 · %s ~ %s · 여섯 요인을 못 낸 종목-월 %d칸"
          % (len(ds), ds[0], ds[-1], drop["factor"]))
    print()

    # ── F1·F2 재현 검증 ──────────────────────────────────────────────
    ws = [panel[d]["wsum"] for d in ds]
    caps = [panel[d]["vcap"] + panel[d]["gcap"] for d in ds]
    gc = [panel[d]["g_cap"] for d in ds]
    vc = [panel[d]["v_cap"] for d in ds]
    print("F1 WV+WG=1 : 종목평균 최소 %.6f · 최대 %.6f" % (min(ws), max(ws)))
    print("F1 시총합   : 가치+성장 ÷ 모지수 최소 %.4f · 최대 %.4f" % (min(caps), max(caps)))
    print("F2 바스켓   : 성장 %.1f~%.1f%% · 가치 %.1f~%.1f%% (목표 33±3)"
          % (100 * min(gc), 100 * max(gc), 100 * min(vc), 100 * max(vc)))
    npv = [panel[d]["n_pv"] for d in ds]
    npg = [panel[d]["n_pg"] for d in ds]
    print("F3 Pure 종목수: PV 중앙 %d (%d~%d) · PG 중앙 %d (%d~%d)   [실제 RPV≈125 · RPG≈75~80]"
          % (sorted(npv)[len(npv) // 2], min(npv), max(npv),
             sorted(npg)[len(npg) // 2], min(npg), max(npg)))
    nn = [panel[d]["n"] for d in ds]
    print("F5 채점 종목수: 중앙 %d (%d~%d) · 300 미만인 달 %d/%d"
          % (sorted(nn)[len(nn) // 2], min(nn), max(nn),
             sum(1 for x in nn if x < 300), len(nn)))

    # 예측 P1·P2 — 가치점수·RG/RV 가 B/M 과 얼마나 같나
    def rankc(a, b):
        n = len(a)
        ra = {v: r for r, v in enumerate(sorted(range(n), key=lambda k: a[k]))}
        rb = {v: r for r, v in enumerate(sorted(range(n), key=lambda k: b[k]))}
        x = [ra[i] for i in range(n)]
        y = [rb[i] for i in range(n)]
        mx, my = sum(x) / n, sum(y) / n
        sx = math.sqrt(sum((v - mx) ** 2 for v in x))
        sy = math.sqrt(sum((v - my) ** 2 for v in y))
        return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / ((sx * sy) or 1e-12)
    c1, c2 = [], []
    for d in ds:
        P = panel[d]
        ts = sorted(P["SG"])
        bm = [P["bp"][t] for t in ts]
        c1.append(rankc([P["SV"][t] for t in ts], bm))
        c2.append(rankc([-P["W"][t][1] for t in ts], bm))   # 성장 배분이 클수록 «성장»
    print()
    print("P1 가치점수 vs B/M 순위상관 : 중앙 %+.3f (예측 ≥0.85)" % sorted(c1)[len(c1) // 2])
    print("P2 성장배분 vs B/M 순위상관 : 중앙 %+.3f (예측 <0.85 이면 B/M 단독과 다르다)"
          % sorted(c2)[len(c2) // 2])

    doc = {"note": ("S&P 스타일 점수를 랩 518종에 적용한 분류. 규약 "
                    "PREREG-2026-09-03-STYLESCORE.md. 🚨 지수 복제가 아니라 «산식을 매월 "
                    "적용한 분류» 다 — 표준화 모집단이 TMI 가 아니라 랩 유니버스이고, "
                    "원문은 연 1회 리밸런스다. 얼린 측정 · 자동 재굽기 금지."),
           "prereg": "5a95f5495",
           "const": {"cap_g": CAP_G, "cap_v": CAP_V, "round_w": ROUND_W,
                     "pure_margin": PURE_MARGIN, "pure_cap": PURE_CAP},
           "months": ds, "drop_factor": drop["factor"],
           "check": {"wsum": [min(ws), max(ws)], "capsum": [min(caps), max(caps)],
                     "g_cap": [min(gc), max(gc)], "v_cap": [min(vc), max(vc)],
                     "n_pv_med": sorted(npv)[len(npv) // 2],
                     "n_pg_med": sorted(npg)[len(npg) // 2],
                     "rank_sv_bm": sorted(c1)[len(c1) // 2],
                     "rank_wg_bm": sorted(c2)[len(c2) // 2]},
           "panel": {d: {"n": panel[d]["n"], "n_g": panel[d]["n_g"], "n_v": panel[d]["n_v"],
                         "n_b": panel[d]["n_b"], "n_pv": panel[d]["n_pv"],
                         "n_pg": panel[d]["n_pg"],
                         "SG": {t: round(v, 4) for t, v in panel[d]["SG"].items()},
                         "SV": {t: round(v, 4) for t, v in panel[d]["SV"].items()},
                         "WV": {t: round(panel[d]["W"][t][0], 3) for t in panel[d]["W"]},
                         "pv": panel[d]["pv"], "pg": panel[d]["pg"]} for d in ds}}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))

    # 최근 달 예시
    d = ds[-1]
    P = panel[d]
    print()
    print("=== %s 분류 예시 ===" % d)
    print("  성장 %d종 · 블렌드 %d종 · 가치 %d종 · Pure Growth %d · Pure Value %d"
          % (P["n_g"], P["n_b"], P["n_v"], P["n_pg"], P["n_pv"]))
    for t in ("NVDA", "AAPL", "MSFT", "TSLA", "JPM", "XOM", "VZ", "KO"):
        if t in P["SG"]:
            wv = P["W"][t][0]
            lab = "성장" if wv == 0 else ("가치" if wv == 1 else "블렌드")
            pu = " · PureG" if t in P["pg"] else (" · PureV" if t in P["pv"] else "")
            print("  %-5s SG %+6.2f · SV %+6.2f → %s (가치배분 %.0f%%)%s"
                  % (t, P["SG"][t], P["SV"][t], lab, 100 * wv, pu))


if __name__ == "__main__":
    main()
