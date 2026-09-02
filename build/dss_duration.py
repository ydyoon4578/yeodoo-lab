# -*- coding: utf-8 -*-
"""build/dss_duration.py — DSS(2004) 내재 듀레이션 로테이션 → data/_dss_duration.json

규약: build/PREREG-2026-09-03-DURATION.md (계산 전 커밋 4bf910d28).

  물음은 「듀레이션 로테이션이 되나」가 아니라 **「B/M 을 통제한 뒤에도 듀레이션에 남는
  정보가 있나」** 다. 듀레이션과 B/M 의 순위상관이 −0.79~−0.89 라 그냥 돌리면 D13 의
  재포장이 된다(등록 §0-1).

  x-durrot  월말 채점 가능 종목을 듀레이션으로 **반씩** 나눠
              단기 절반 = 가치 대용 · 장기 절반 = 성장 대용, 각각 동일가중.
              DFII10 3개월 변화 ≥+20bp → 단기 70/장기 30 · ≤−20bp → 30/70 · 사이 50/50.
  x-bmrot   같은 규칙을 **B/M** 으로(상위 절반 = 가치 대용). ← 1번 대조군.

🚨 얼린 측정이다. 산출물은 밑줄 접두로 두고 커밋하지 않는다(자동 재굽기 금지).

    python build/dss_duration.py
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
OUT = os.path.join(DATA, "_dss_duration.json")     # 밑줄 = 로컬 전용
sys.path.insert(0, HERE)

# ── 등록 §1-1 의 상수 — 전부 DSS(2004) 가 논문에 명시한 값이다 ──────────────
#   🚨 결과를 보고 만지지 않는다. 민감도(등록 §0)는 진단이지 선택지가 아니다.
R = 0.12                    # 자기자본비용
ROE_M, ROE_A = 0.12, 0.57   # ROE 평균회귀 목표 · 자기상관
G_M, G_A = 0.06, 0.24       # 매출성장 평균회귀 목표 · 자기상관
T = 10                      # 명시적 예측 구간(년)
# 등록 §2 의 상수
TH = 0.20                   # DFII10 3개월 변화 문턱(%p) — D13 카드의 수
MIN_COV = 100               # 채점 가능 종목이 이보다 적으면 무보유(반씩 나누려면 양쪽 50종)
W = {"단기": 0.7, "중립": 0.5, "장기": 0.3}    # «가치 대용» 쪽 비중
COST_RT = 0.0020            # 왕복 20bp — F3


def implied_duration(bv, mv, roe0, g0):
    """DSS(2004) 내재 자기자본 듀레이션. 등록 §1-2 의 식 그대로."""
    if not (bv and mv and bv > 0 and mv > 0):
        return None
    roe, g, b = roe0, g0, bv
    pv = wpv = 0.0
    for t in range(1, T + 1):
        roe = ROE_M + ROE_A * (roe - ROE_M)
        g = G_M + G_A * (g - G_M)
        e = roe * b
        b1 = b * (1 + g)
        cf = e - (b1 - b)                     # 순배분 = 이익 − 장부가 증가
        d = cf / (1 + R) ** t
        pv += d
        wpv += t * d
        b = b1
    return wpv / mv + (T + (1 + R) / R) * (mv - pv) / mv


def main():
    import tech_backtest as TB

    dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
    FU = TB.load_fund()
    tickers = sorted(px)
    di = {d: i for i, d in enumerate(dates)}
    me = [i for i in range(len(dates) - 1) if dates[i][:7] != dates[i + 1][:7]]
    me = [i for i in me if dates[i] >= "2016-01-01"]

    def macro(sid, d):
        m = TB.load_macro(sid) if hasattr(TB, "load_macro") else None
        return m

    # DFII10 은 자산 패널에서 읽는다(일간 계열이라 발표시차 문제가 없다).
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    RY = {k: v for k, v in (A["macro"].get("DFII10") or {}).items() if v is not None}
    _rk = sorted(RY)

    def ry_asof(d):
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
        return ry_asof("%04d-%02d-%s" % (y, m, d[8:10]))

    # ── 월말마다 듀레이션·B/M 패널 ─────────────────────────────────────
    panel, negeq = {}, 0
    for i in me:
        d = dates[i]
        row = {}
        for t in tickers:
            f = FU.get(t)
            if not f:
                continue
            bv = TB.asof_fund(f.get("eq"), d)
            if bv is not None and bv <= 0:
                negeq += 1          # 자기자본 음수 — 듀레이션이 뜻을 잃는다(등록 §7)
                continue
            ni = TB.ttm2(f.get("ni"), f.get("ni_a"), d)
            pr = TB.yoy_pair(f.get("rev"), d)
            sn = TB.asof_fund(f.get("sh"), d)
            p = px[t][i]
            if not (bv and ni is not None and pr and sn and p and p > 0):
                continue
            _a, r0, _b, r1 = pr
            if not r1 or r1 <= 0:
                continue
            mv = sn * p
            roe0 = max(-1.0, min(1.0, ni / bv))
            g0 = max(-0.5, min(1.0, r0 / r1 - 1))
            du = implied_duration(bv, mv, roe0, g0)
            if du is None or du != du or not (0 < du < 200):
                continue
            row[t] = (du, bv / mv)
        panel[d] = row

    live = [d for d in sorted(panel) if len(panel[d]) >= MIN_COV]
    print("월말 %d개 · 커버 문턱(%d종) 통과 %d개월 · 첫 달 %s"
          % (len(panel), MIN_COV, len(live), live[0] if live else "없음"))
    print("자기자본 음수로 뺀 종목-월 %d칸" % negeq)

    # ── 두 규칙을 같은 틀로 굴린다 ────────────────────────────────────
    def run(key):
        """key=0 듀레이션(하위 절반=가치 대용) · key=1 B/M(상위 절반=가치 대용)"""
        rows, prev = [], None
        for k in range(len(live) - 1):
            d, d1 = live[k], live[k + 1]
            i, i1 = di[d], di[d1]
            row = panel[d]
            now, p3 = ry_asof(d), back3(d)
            ch = None if (now is None or p3 is None) else now - p3
            g = "중립" if ch is None else ("단기" if ch >= TH else "장기" if ch <= -TH else "중립")
            ts = sorted(row, key=lambda t: row[t][key])
            h = len(ts) // 2
            lo, hi = ts[:h], ts[h:]
            # 「가치 대용」 = 듀레이션이면 하위(lo) · B/M 이면 상위(hi)
            val, grw = (lo, hi) if key == 0 else (hi, lo)
            w = W[g]

            def bret(bk):
                rs = [px[t][i1] / px[t][i] - 1 for t in bk
                      if px[t][i] and px[t][i1] and px[t][i] > 0]
                return sum(rs) / len(rs) if rs else 0.0
            r = w * bret(val) + (1 - w) * bret(grw)
            base = .5 * bret(val) + .5 * bret(grw)
            # 회전 — 바스켓 구성이 바뀐 만큼(비중 변화 + 명단 변화)
            cur = (set(val), w)
            tc = 0.0
            if prev is not None:
                pv, pw = prev
                same = len(pv & cur[0]) / max(1, len(pv | cur[0]))
                tc = COST_RT * (abs(w - pw) + (1 - same))
            prev = cur
            rows.append(dict(m=dates[i1][:7], reg=g, ch=ch, r=r, base=base, cost=tc,
                             n=len(ts), val=set(val)))
        return rows

    DU, BM = run(0), run(1)

    # ── 통계 ─────────────────────────────────────────────────────────
    spy = {}
    for k in range(len(live) - 1):
        i, i1 = di[live[k]], di[live[k + 1]]
        s = A["px"]["SPY"]
        j = min(i, len(s) - 1)
        j1 = min(i1, len(s) - 1)
        spy[dates[i1][:7]] = None
    # SPY 는 자산 패널 격자라 날짜로 맞춘다
    ad = {d: n for n, d in enumerate(A["dates"])}
    for k in range(len(live) - 1):
        d, d1 = live[k], live[k + 1]
        if d in ad and d1 in ad:
            s = A["px"]["SPY"]
            if s[ad[d]] and s[ad[d1]]:
                spy[dates[di[d1]][:7]] = s[ad[d1]] / s[ad[d]] - 1

    def stat(v):
        n = len(v)
        mu = sum(v) / n
        sd = math.sqrt(sum((x - mu) ** 2 for x in v) / (n - 1)) if n > 1 else 0
        p = 1.0
        for x in v:
            p *= 1 + x
        return dict(n=n, cagr=round((p ** (12 / n) - 1) * 100, 2),
                    vol=round(sd * math.sqrt(12) * 100, 2),
                    sharpe=round((mu * 12) / (sd * math.sqrt(12)), 3) if sd else None)

    def tt(a, b):
        d = [a[i] - b[i] for i in range(len(a))]
        n = len(d)
        mu = sum(d) / n
        sd = math.sqrt(sum((x - mu) ** 2 for x in d) / (n - 1))
        return round(mu * 12 * 100, 2), round(mu / (sd / math.sqrt(n)), 2)

    du_r = [x["r"] for x in DU]
    bm_r = [x["r"] for x in BM]
    du_n = [x["r"] - x["cost"] for x in DU]
    bm_n = [x["r"] - x["cost"] for x in BM]
    sp_r = [spy.get(x["m"]) or 0.0 for x in DU]

    print()
    print("=" * 78)
    print("측정 %s ~ %s · %d개월" % (DU[0]["m"], DU[-1]["m"], len(DU)))
    print("=" * 78)
    print("%-22s %8s %8s %8s" % ("", "CAGR", "변동성", "샤프"))
    for lab, v in (("x-durrot (듀레이션)", du_r), ("x-bmrot (B/M · 대조군)", bm_r),
                   ("S&P 500 TR (SPY)", sp_r)):
        s = stat(v)
        print("%-22s %7.2f%% %7.2f%% %8s" % (lab, s["cagr"], s["vol"], s["sharpe"]))
    print()
    a, t = tt(du_r, bm_r)
    an, tn = tt(du_n, bm_n)
    print("F1·F2 — 듀레이션 − B/M : 연 %+.2f%%p · t %.2f   (비용 뒤 %+.2f%%p · t %.2f)"
          % (a, t, an, tn))
    a2, t2 = tt(du_r, sp_r)
    print("     듀레이션 − S&P TR : 연 %+.2f%%p · t %.2f" % (a2, t2))
    a3, t3 = tt(bm_r, sp_r)
    print("     B/M      − S&P TR : 연 %+.2f%%p · t %.2f" % (a3, t3))

    # 예측 P1·P3
    n = len(du_r)
    mu1, mu2 = sum(du_r) / n, sum(bm_r) / n
    s1 = math.sqrt(sum((x - mu1) ** 2 for x in du_r))
    s2 = math.sqrt(sum((x - mu2) ** 2 for x in bm_r))
    rho = sum((du_r[i] - mu1) * (bm_r[i] - mu2) for i in range(n)) / ((s1 * s2) or 1e-12)
    ov = [len(DU[i]["val"] & BM[i]["val"]) / max(1, len(DU[i]["val"] | BM[i]["val"]))
          for i in range(n)]
    sw = sum(1 for i in range(1, n) if DU[i]["reg"] != DU[i - 1]["reg"])
    print()
    print("예측 판정 — P1 두 수익 상관 %.4f (>0.95?) · P3 «가치 대용» 바스켓 겹침 중앙 %.1f%% (>80%%?)"
          % (rho, 100 * sorted(ov)[len(ov) // 2]))
    print("F4 국면 전환 %d회 (>6?) · 바스켓 종목수 중앙 %d"
          % (sw, sorted(x["n"] for x in DU)[n // 2]))

    doc = {"note": ("DSS(2004) 내재 듀레이션 로테이션. 규약 PREREG-2026-09-03-DURATION.md. "
                    "🚨 얼린 측정 — 자동 재굽기 금지."),
           "prereg": "4bf910d28",
           "const": {"r": R, "roe_mean": ROE_M, "roe_ar": ROE_A, "g_mean": G_M,
                     "g_ar": G_A, "T": T, "th": TH, "min_cov": MIN_COV},
           "window": [DU[0]["m"], DU[-1]["m"]], "n_months": len(DU),
           "stats": {"durrot": stat(du_r), "bmrot": stat(bm_r), "spy": stat(sp_r)},
           "f1": {"excess": a, "t": t}, "f1_net": {"excess": an, "t": tn},
           "vs_spy": {"durrot": [a2, t2], "bmrot": [a3, t3]},
           "pred": {"rho": round(rho, 4), "overlap_med": round(sorted(ov)[len(ov) // 2], 4),
                    "switches": sw},
           "rows": [{"m": x["m"], "reg": x["reg"], "n": x["n"],
                     "dur": round(x["r"], 6), "bm": BM[i]["r"] and round(BM[i]["r"], 6)}
                    for i, x in enumerate(DU)]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
