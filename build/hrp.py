# -*- coding: utf-8 -*-
"""계층적 위험 패리티(HRP) — 계층 구조가 «비중» 에 정보를 주는가.

규약 build/PREREG-2026-09-11-HRP.md · 계산 전 커밋 e90ba5e87.
López de Prado (2016), *Building Diversified Portfolios that Outperform Out-of-Sample*.

🚨 성과 문턱이 없다(등록 §0·§3-1). 판정하는 것은 V1·V2 —
   V1 표본 밖 분산화 비율에서 동일가중을 넘는가(트리가 일을 했나)
   V2 HRP 비중이 역분산 비중과 거의 같은가(트리가 장식인가)
   성적은 여섯 판 전부 싣되 등급을 매기지 않는다.

🚨 채점기 사본을 안 만든다 — 군집은 ml_core._avg_linkage 한 곳에서 낸다.
   그 함수를 떼어내며 corr_clusters 의 라벨이 안 바뀌는지 무작위 400판으로 대조했다
   (n 5~60 · k 2~12 · 군집 구조 있는 판 섞음): **불일치 0건**.

산출 data/_hrp.json (얼린 측정 · 커밋 안 함).
"""
from __future__ import annotations
import io
import json
import math
import os
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA = os.path.join(os.path.dirname(HERE), "data")

WIN = 504                 # 상관·분산 추정창 — 504거래일(2년). 등록 §1
KCUT = 10                 # V3 자카드용 절단 수(= m-clust 과 같게)
COST_RT = 0.0020          # 왕복 20bp
START = "2014-06"         # PIT 명단 시작
END = "2026-08"


def cluster_var(cov, idx):
    """덩이의 분산 — 역분산 가중으로 묶었을 때. HRP 재귀 이분할의 판정량."""
    sub = cov[np.ix_(idx, idx)]
    d = np.diag(sub).copy()
    d[d <= 0] = np.nan
    iv = 1.0 / d
    if not np.all(np.isfinite(iv)):
        iv = np.nan_to_num(iv, nan=0.0)
    s = iv.sum()
    if s <= 0:
        iv = np.ones(len(idx)) / len(idx)
    else:
        iv = iv / s
    return float(iv @ sub @ iv)


def hrp_weights(cov, corr):
    """① 트리 → ② 준대각화 → ③ 재귀 이분할. 등록 §1."""
    import ml_core as MC
    n = cov.shape[0]
    order = MC.corr_leaf_order(corr)          # ← 군집은 여기 한 곳에서만 난다
    w = np.ones(n, float)
    clusters = [list(order)]
    while clusters:
        nxt = []
        for c in clusters:
            if len(c) <= 1:
                continue
            h = len(c) // 2
            L, R = c[:h], c[h:]
            vL, vR = cluster_var(cov, L), cluster_var(cov, R)
            a = 1.0 - vL / (vL + vR) if (vL + vR) > 0 else 0.5
            for x in L:
                w[x] *= a
            for x in R:
                w[x] *= (1.0 - a)
            nxt.append(L)
            nxt.append(R)
        clusters = nxt
    s = w.sum()
    return w / s if s > 0 else np.ones(n) / n


def ivp_weights(cov):
    """역분산 — 🚨 HRP 에서 «트리만» 뺀 것. 둘의 차이가 트리의 몫이다(등록 §2)."""
    d = np.diag(cov).copy()
    d[d <= 0] = np.nan
    iv = 1.0 / d
    iv = np.nan_to_num(iv, nan=0.0)
    s = iv.sum()
    return iv / s if s > 0 else np.ones(len(d)) / len(d)


def maxdd(nav):
    pk, mx = nav[0], 0.0
    for v in nav:
        pk = max(pk, v)
        mx = min(mx, v / pk - 1.0)
    return mx


def main():
    import tech_backtest as TB
    import ml_core as MC

    IH = json.load(io.open(os.path.join(DATA, "index_history.json"),
                           encoding="utf-8"))["months"]
    dates, px, vlm, hid, lod, meta, rf_ = TB.load(full=True)
    FU = TB.load_fund()
    n = len(dates)

    # 분기말 — 가격 격자에서 각 분기의 마지막 거래일
    qe, seen = [], {}
    for i, d in enumerate(dates):
        q = (d[:4], (int(d[5:7]) - 1) // 3)
        seen[q] = i
    qe = [seen[k] for k in sorted(seen)]
    qe = [i for i in qe if START <= dates[i][:7] <= END and i >= WIN]

    R = TB.daily_rets(px)
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    ad = {d: k for k, d in enumerate(A["dates"])}
    spx = A["px"]["^GSPC"]

    LEGS = ("hrp", "ivp", "erc", "ew", "cap")
    ret = {k: [0.0] * n for k in LEGS}
    diag, prev_w, prev_lab = [], {k: {} for k in LEGS}, None
    turn = {k: [] for k in LEGS}

    for qi in range(len(qe) - 1):
        i, i1 = qe[qi], qe[qi + 1]
        mm = dates[i][:7]
        hist = IH.get(mm)
        if not hist:
            continue
        pool = sorted(set(hist.get("spx") or []) | set(hist.get("ndx") or []))
        names, rows = [], []
        for t in pool:
            a = R.get(t)
            if not a:
                continue
            w = a[i - WIN + 1:i + 1]
            if len(w) == WIN and all(x is not None for x in w) and px[t][i]:
                names.append(t)
                rows.append(w)
        dropped = len(pool) - len(names)
        if len(names) < 50:
            continue
        M = np.array(rows, float)
        C = np.corrcoef(M)
        V = np.cov(M)
        if not (np.all(np.isfinite(C)) and np.all(np.isfinite(V))):
            continue

        W = {}
        W["hrp"] = hrp_weights(V, C)
        W["ivp"] = ivp_weights(V)
        e = MC.erc_weights(V)
        W["erc"] = np.asarray(e, float) if e is not None else W["ivp"].copy()
        W["ew"] = np.ones(len(names)) / len(names)
        mc = np.zeros(len(names))
        for k, t in enumerate(names):
            f = FU.get(t)
            sh = TB.asof_fund(f.get("sh"), mm + "-28") if f else None
            if sh and sh > 0:
                mc[k] = sh * px[t][i]
        W["cap"] = mc / mc.sum() if mc.sum() > 0 else W["ew"].copy()

        # 표본 밖 — 다음 분기까지 보유(비중은 그대로 흘러간다)
        fwd = np.array([[R[t][j] if R[t][j] is not None else 0.0
                         for j in range(i + 1, i1 + 1)] for t in names], float)
        sig_f = fwd.std(axis=1, ddof=1) * math.sqrt(252)
        row = {"q": dates[i][:10], "n": len(names), "dropped": dropped,
               "corr_hrp_ivp": float(np.corrcoef(W["hrp"], W["ivp"])[0, 1]),
               "w_max": float(W["hrp"].max()),
               "w_top10": float(np.sort(W["hrp"])[-10:].sum())}
        for k in LEGS:
            cur = W[k].copy()
            # 회전율 — 직전 분기말 «흘러간» 비중 대비
            pw = prev_w[k]
            if pw:
                tv = sum(abs(cur[x] - pw.get(names[x], 0.0)) for x in range(len(names)))
                tv += sum(v for t, v in pw.items() if t not in set(names))
                turn[k].append(tv / 2.0)
            nav, w = 1.0, cur.copy()
            for c in range(fwd.shape[1]):
                r = float(w @ fwd[:, c])
                ret[k][i + 1 + c] = r
                w = w * (1.0 + fwd[:, c])
                s = w.sum()
                w = w / s if s > 0 else cur
            prev_w[k] = {names[x]: float(w[x]) for x in range(len(names))}
            pr = np.array([ret[k][j] for j in range(i + 1, i1 + 1)])
            sp = pr.std(ddof=1) * math.sqrt(252)
            row["dr_" + k] = float((cur @ sig_f) / sp) if sp > 0 else None
        lab = MC.corr_clusters(C, KCUT)
        cur_lab = {}
        for t, c in zip(names, lab):
            cur_lab.setdefault(int(c), set()).add(t)
        if prev_lab:
            js = []
            for a_ in cur_lab.values():
                js.append(max((len(a_ & b_) / len(a_ | b_)) for b_ in prev_lab.values()))
            row["jaccard"] = float(np.mean(js))
        prev_lab = cur_lab
        diag.append(row)

    lo, hi = qe[0] + 1, qe[-1]
    out = {"note": "HRP — 계층 구조가 비중에 정보를 주는가. 규약 PREREG-2026-09-11-HRP.md. 얼린 측정.",
           "prereg": "e90ba5e87", "win": WIN, "start": dates[lo][:10], "end": dates[hi][:10],
           "n_quarters": len(diag), "quarters": diag, "legs": {}}

    bx = []
    for j in range(lo, hi + 1):
        d = dates[j]
        k0, k1 = ad.get(dates[j - 1]), ad.get(d)
        bx.append(spx[k1] / spx[k0] - 1 if (k0 is not None and k1 is not None
                                            and spx[k0] and spx[k1]) else 0.0)
    bx = np.array(bx) + 0.0200 / 252            # 배당보정 연 2.00%p (UNION §1-2 규약)
    yrs = (hi - lo + 1) / 252.0
    for k in LEGS:
        r = np.array([ret[k][j] for j in range(lo, hi + 1)])
        rn = r.copy()
        for x, t_ in zip(range(len(turn[k])), turn[k]):
            pass
        nav = np.cumprod(1 + r)
        navb = np.cumprod(1 + bx)
        tv = float(np.mean(turn[k])) * 4 if turn[k] else 0.0
        drag = tv * COST_RT
        out["legs"][k] = {
            "cagr": float(nav[-1] ** (1 / yrs) - 1) * 100,
            "vol": float(r.std(ddof=1) * math.sqrt(252)) * 100,
            "mdd": maxdd(nav) * 100,
            "turnover_yr": tv,
            "cagr_net": float((nav[-1] ** (1 / yrs) - 1) - drag) * 100,
            "dr": float(np.nanmean([q["dr_" + k] for q in diag if q.get("dr_" + k)])),
            "excess_cagr": float((nav[-1] ** (1 / yrs)) - (navb[-1] ** (1 / yrs))) * 100,
        }
        d2 = r - bx
        out["legs"][k]["t_excess"] = float(d2.mean() / (d2.std(ddof=1) / math.sqrt(len(d2))))
    out["legs"]["bench"] = {"cagr": float(np.cumprod(1 + bx)[-1] ** (1 / yrs) - 1) * 100,
                            "vol": float(bx.std(ddof=1) * math.sqrt(252)) * 100,
                            "mdd": maxdd(np.cumprod(1 + bx)) * 100}
    out["v1"] = out["legs"]["hrp"]["dr"] > out["legs"]["ew"]["dr"]
    out["v2_corr_median"] = float(np.median([q["corr_hrp_ivp"] for q in diag]))
    out["v3_jaccard"] = float(np.mean([q["jaccard"] for q in diag if "jaccard" in q]))
    out["daily"] = {k: [float(ret[k][j]) for j in range(lo, hi + 1)] for k in LEGS}
    out["daily"]["bench"] = [float(x) for x in bx]
    out["daily_dates"] = [dates[j] for j in range(lo, hi + 1)]

    with open(os.path.join(DATA, "_hrp.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    print("분기 %d회 · %s ~ %s · 종목 중앙 %d (제외 중앙 %d)"
          % (len(diag), out["start"], out["end"],
             int(np.median([q["n"] for q in diag])),
             int(np.median([q["dropped"] for q in diag]))))
    print("%-6s %8s %8s %8s %9s %8s %9s %7s" %
          ("", "CAGR", "변동성", "MDD", "분산화DR", "회전/년", "초과CAGR", "t"))
    for k in LEGS + ("bench",):
        g = out["legs"][k]
        print("%-6s %7.2f%% %7.2f%% %7.1f%% %9s %8s %9s %7s" %
              (k, g["cagr"], g["vol"], g["mdd"],
               ("%.3f" % g["dr"]) if "dr" in g else "—",
               ("%.2f" % g["turnover_yr"]) if "turnover_yr" in g else "—",
               ("%+.2f%%p" % g["excess_cagr"]) if "excess_cagr" in g else "—",
               ("%+.2f" % g["t_excess"]) if "t_excess" in g else "—"))
    print()
    print("V1 분산화 비율 HRP %.3f vs 동일가중 %.3f → %s"
          % (out["legs"]["hrp"]["dr"], out["legs"]["ew"]["dr"],
             "트리가 일했다" if out["v1"] else "🚨 트리가 일을 안 했다"))
    print("V2 HRP↔역분산 비중 상관 중앙 %.3f → %s"
          % (out["v2_corr_median"],
             "🚨 트리가 장식이다" if out["v2_corr_median"] > 0.95 else "구별된다"))
    print("V3 군집 라벨 분기별 자카드 %.3f%s"
          % (out["v3_jaccard"], "  🚨 0.9 초과 — 분기 리밸이 과하다"
             if out["v3_jaccard"] > 0.9 else ""))
    print("   HRP 최대 비중 중앙 %.3f · 상위10 비중합 중앙 %.3f"
          % (np.median([q["w_max"] for q in diag]),
             np.median([q["w_top10"] for q in diag])))


if __name__ == "__main__":
    main()
