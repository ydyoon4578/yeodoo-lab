# -*- coding: utf-8 -*-
"""build/lsbeta_audit.py — 롱숏 규칙에 시장이 얼마나 남아 있나 (AUDIT-2026-09-19-LSBETA)

🚨 새 규칙도 새 채점기도 만들지 않는다. 이미 산출된 nav·bnav 를 읽어 회귀할 뿐이다.
🚨 nav 는 주간 «표시용 표본»이고 일간 정본은 저장돼 있지 않다(sampling.daily.stored=false).
   그래서 여기 β 는 «0 근처인가»만 묻는 눈금이다. 소수 둘째 자리를 믿지 않는다.

  python build/lsbeta_audit.py
"""
from __future__ import annotations
import io, json, os, re, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_lsbeta.json")
WARN, BAD = 0.15, 0.30        # SWING2 F5 와 같은 값

# 숏 다리를 실제로 드는가 — 문안에서 찾는다(이름으로 고르지 않는다 · 감사 §1)
# 🚨 처음에 「롱숏」을 패턴에 안 넣어 x-subom 을 놓쳤다. 그 규칙의 문안은
#   "위 서브산업 모멘텀과 모든 것이 같고 정렬 축만 …" 이라 **숏을 참조로 물려받는다.**
#   문안만 보고 구조를 고르는 방식의 한계다 — 물려받는 문안은 이름에서만 드러난다.
SHORT_PAT = re.compile(r"롱숏|(를|을)\s*숏|숏\s*한다|숏한다|공매도|하위\s*\d+\s*를?\s*숏")
MIN_BVOL = 5.0      # 벤치 연변동성(%)이 이보다 낮으면 «시장»이 아니다 — β 를 내지 않는다


def beta(y, x):
    y, x = np.asarray(y, float), np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    if len(y) < 30:
        return None, None, 0
    xm = x.mean()
    b = float(((x - xm) @ (y - y.mean())) / ((x - xm) @ (x - xm)))
    # 알파(주간 → 연)
    a = float((y - b * x).mean()) * 52 * 100
    return b, a, len(y)


def main():
    d = json.load(io.open(os.path.join(DATA, "tech_strategies.json"), encoding="utf-8"))
    rows = d["strategies"]
    print("규칙 %d종 · nav 표본 %s\n" % (len(rows), d["sampling"]["nav"]["kind"]))

    # ── 공통 시장 계열 ────────────────────────────────────────────────────
    # 🚨 규칙마다 bnav 가 «그 규칙의 대조군»이라 서로 다르다. 시장중립 규칙의 대조군은
    #   사실상 현금이어서(연변동성 0.3%) 거기에 회귀하면 0 으로 나누는 꼴이 된다 —
    #   실제로 첫 판에서 β 3.8 이 나왔고 상관은 0.045 였다. 그래서 **모든 규칙을 하나의
    #   시장 계열에 회귀한다.** 시장 계열은 벤치 변동성이 정상인 규칙들의 bnav 를
    #   날짜로 맞춰 중앙값으로 모은 것이다(어느 한 규칙에 기대지 않는다).
    mkt = {}
    for r in rows:
        bn, dt = r.get("bnav"), r.get("dates")
        if not (isinstance(bn, list) and isinstance(dt, list) and len(bn) == len(dt) >= 30):
            continue
        rb = np.diff(np.log(np.maximum(bn, 1e-9)))
        if float(np.nanstd(rb, ddof=1)) * np.sqrt(52) * 100 < MIN_BVOL:
            continue
        for day, x in zip(dt[1:], rb):
            if np.isfinite(x):
                mkt.setdefault(day, []).append(float(x))
    MKT = {k: float(np.median(v)) for k, v in mkt.items()}
    mv = np.array(list(MKT.values()))
    print("공통 시장 계열 — %d일(주간) · 연변동성 %.1f%% · 기여 규칙 있음"
          % (len(MKT), mv.std(ddof=1) * np.sqrt(52) * 100))

    out, ls, lo = [], [], []
    for r in rows:
        nav, bnav, dt = r.get("nav"), r.get("bnav"), r.get("dates")
        if not (isinstance(nav, list) and isinstance(bnav, list) and len(nav) == len(bnav)):
            continue
        if not (isinstance(dt, list) and len(dt) == len(nav)):
            continue
        rn_all = np.diff(np.log(np.maximum(nav, 1e-9)))
        # 규칙의 주간 수익과 **공통 시장**을 날짜로 맞춘다
        pair = [(x, MKT[day]) for day, x in zip(dt[1:], rn_all) if day in MKT and np.isfinite(x)]
        if len(pair) < 30:
            continue
        rn = np.array([p[0] for p in pair])
        rb = np.array([p[1] for p in pair])
        b, a, k = beta(rn, rb)
        if b is None:
            continue
        txt = (r.get("rule") or "") + " " + (r.get("name") or "")
        is_ls = bool(SHORT_PAT.search(txt))
        # 검산 — β = corr × (σ규칙 / σ벤치). corr 가 1 을 넘으면 계산이 틀린 것이다.
        m2 = np.isfinite(rn) & np.isfinite(rb)
        corr = float(np.corrcoef(rn[m2], rb[m2])[0, 1])
        rec = {"sid": r["sid"], "name": r.get("name"), "beta": round(b, 3),
               "alpha_yr": round(a, 2), "n": k, "ls": is_ls, "corr": round(corr, 3),
               "vol_w": round(float(rn[m2].std(ddof=1)) * np.sqrt(52) * 100, 1),
               "vol_b": round(float(rb[m2].std(ddof=1)) * np.sqrt(52) * 100, 1),
               "vol_stored": r.get("metrics", {}).get("vol"),
               "sharpe": r.get("metrics", {}).get("sharpe"),
               "verdict": r.get("verdict")}
        out.append(rec)
        (ls if is_ls else lo).append(rec)

    print("■ 숏 다리를 드는 규칙 %d종 — 주간 β" % len(ls))
    print("   %-18s %7s %7s %7s %7s %8s %-8s" % ("sid", "β", "상관", "σ규칙", "σ벤치", "σ저장", "등급"))
    for r in sorted(ls, key=lambda x: -abs(x["beta"])):
        g = "🔴 중립아님" if abs(r["beta"]) >= BAD else ("🟠 주의" if abs(r["beta"]) >= WARN else "🟡")
        r["grade"] = g
        print("   %-18s %7.3f %7.3f %6.1f%% %6.1f%% %7s %-8s"
              % (r["sid"], r["beta"], r["corr"], r["vol_w"], r["vol_b"],
                 r["vol_stored"], g))
        print("      %s" % (r["name"] or ""))
    print("   🚨 σ규칙(주간 표본에서 다시 낸 변동성)과 σ저장(일간 정본으로 낸 값)이 크게")
    print("      다르면, 주간 표본이 그 규칙의 위험을 못 담고 있다는 뜻이다 — β 도 못 믿는다.")

    print("\n■ 대조군 — 숏 없는 규칙 %d종의 β 분포 (감사 §4)" % len(lo))
    bs = np.array([r["beta"] for r in lo])
    for q in (5, 25, 50, 75, 95):
        print("   %2d분위 %.3f" % (q, np.percentile(bs, q)), end="")
    print("\n   평균 %.3f · |β|<0.15 인 것 %d종 (%.0f%%)"
          % (bs.mean(), int((np.abs(bs) < WARN).sum()), (np.abs(bs) < WARN).mean() * 100))
    print("   → 롱온리가 1 근처면 이 측정이 제대로 돈 것이다(검산).")

    if ls:
        a = np.abs([r["beta"] for r in ls])
        print("\n■ 두 집단 비교")
        print("   숏 드는 %d종   |β| 중앙 %.3f · 0.15 이상 %d종 (%.0f%%)"
              % (len(ls), np.median(a), int((a >= WARN).sum()), (a >= WARN).mean() * 100))
        print("   숏 없는 %d종  |β| 중앙 %.3f" % (len(lo), np.median(np.abs(bs))))
        print("   SWING1020 실측 0.238 (일간) — 위 표에서 그 언저리가 몇인지 볼 것")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"warn": WARN, "bad": BAD, "n": len(out), "rows": out,
         "note": "주간 표시용 표본 회귀. 0 근처인가만 묻는다 — 판정이 아니라 재측정 목록."},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
