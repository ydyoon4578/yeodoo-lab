# -*- coding: utf-8 -*-
"""build/twoheads_oos.py — Combined Rank 가 OOS 를 맞히나.

사전등록: build/PREREG-2026-09-21-TWOHEADS.md (계산 전 커밋 **93364b3**).
실패 조건 F1~F5 와 예상 넷은 그 문서에 계산 전에 적혀 있다. 여기서 고치지 않는다.

🚨 `data/_monotonicity.json` 을 **안 읽는다.** 그 파일은 전 구간(119개월) 순위라,
   읽으면 OOS 에 IS 밖 정보가 새 나간다. 분위 수익 계열을 처음부터 다시 만든다.
⚠ 채점기는 그대로 tech_backtest.xsec_score_at — 사본을 만들지 않는다.
⚠ tech_strategies.json 을 건드리지 않는다.

  python build/twoheads_oos.py
"""
from __future__ import annotations
import io, json, os, sys, time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_twoheads_oos.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
import monotonicity as MN                                        # noqa: E402
import tech_backtest as TB                                       # noqa: E402

PREREG = "PREREG-2026-09-21-TWOHEADS.md"
COMMIT = "93364b3"
IS_N = 60            # 등록 §1 — 주 분할은 절반(60 / 59)
CUT = 0.30           # 등록 §1 — 상·하위 30%
WF_STEP, WF_MIN = 12, 36   # 등록 §1 — 보조: 확장창 walk-forward


def stats_of(qseries, a, b):
    """구간 [a,b) 의 분위 계열에서 (mono%, ls 평균 bp, ls t) 를 낸다."""
    q = [row[a:b] for row in qseries]
    n = len(q[0])
    if n < 12:
        return None
    mono = sum(1 for k in range(n)
               if all(q[j][k] <= q[j + 1][k] for j in range(4))) / n * 100
    ls = [q[4][k] - q[0][k] for k in range(n)]
    return {"n": n, "mono_pct": mono, "ls_bp": sum(ls) / n * 10000,
            "ls_t": MN.tstat(ls), "ls": ls}


def prank(vals, v):
    return sum(1 for x in vals if x < v) / (len(vals) - 1) * 100 if len(vals) > 1 else 50.0


def pick(rows, key, cut, top=True):
    v = sorted(r[key] for r in rows)
    k = max(1, int(len(v) * cut))
    thr = v[-k] if top else v[k - 1]
    return [r for r in rows if (r[key] >= thr if top else r[key] <= thr)]


def mean_ls(sel, a, b):
    """선택된 팩터들의 구간 [a,b) 월별 Q5−Q1 을 동일가중 평균 → 월 계열."""
    if not sel:
        return []
    n = b - a
    return [sum(r["q"][4][a + k] - r["q"][0][a + k] for r in sel) / len(sel)
            for k in range(n)]


def main() -> int:
    t0 = time.time()
    TB.build_strats()
    TB._RAT = TB.load_ratings()
    dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
    n = len(dates)
    tickers = sorted(px)
    R = TB.daily_rets(px)
    me_list = TB.month_ends(dates)
    me = set(me_list)
    ixr, ix = [None], [100.0]
    for i in range(1, n):
        rs = [R[t][i] for t in tickers if R[t][i] is not None]
        r = sum(rs) / len(rs) if rs else 0.0
        ixr.append(r); ix.append(ix[-1] * (1 + r))
    ixvol = [TB.vol(ixr, i, 20) for i in range(n)]
    X = {"FACP": TB.load_factor_proxies(dates), "FU": TB.load_fund(), "R": R,
         "dates": dates, "hid": hid, "lod": lod, "ixr": ixr, "ixvol": ixvol, "me": me,
         "me_list": me_list, "meta": meta, "px": px, "vlm": vlm, "tickers": tickers,
         "macd10": TB.macro_daily("DGS10", dates),
         "macfx": TB.macro_daily("DTWEXBGS", dates),
         "mac_real": TB.macro_level("DFII10", dates),
         "mac_curve": TB.macro_level("T10Y2Y", dates),
         "mac_usd": TB.macro_level("DTWEXBGS", dates)}
    TB.MIN_HIST = max(TB.WARM0, n - int(TB.MAX_YEARS * 252))
    idx = [i for i in range(len(dates)) if i in me and i >= TB.MIN_HIST]
    pairs = [(idx[k], idx[k + 1]) for k in range(len(idx) - 1)]
    NM = len(pairs)
    print("월 %d개 · %s~%s · 준비 %.0f초" % (NM, dates[pairs[0][0]], dates[pairs[-1][1]],
                                        time.time() - t0))
    if NM < IS_N + 24:
        raise SystemExit("표본 부족 — 월 %d개" % NM)

    # ── 팩터별 분위 월수익 (한 번만 만든다) ─────────────────────────────
    xs = [S for S in TB.STRATS if S["kind"] == "xsec"]
    rows, thin = [], 0
    for z, S in enumerate(xs, 1):
        q = [[None] * NM for _ in range(5)]
        got = 0
        try:
            for k, (i, j) in enumerate(pairs):
                sc, _a, _b = TB.xsec_score_at(S, i + 1, X)
                if len(sc) < MN.MIN_POOL:
                    continue
                ts = [t for _v, t in sc]
                m = len(ts)
                qs, ok = [], True
                for qq in range(5):
                    a2, b2 = int(m * qq / 5), int(m * (qq + 1) / 5)
                    vals = [MN.fwd_ret(R, t, i, j) for t in ts[a2:b2]]
                    vals = [v for v in vals if v is not None]
                    if len(vals) < 3:
                        ok = False; break
                    qs.append(sum(vals) / len(vals))
                if not ok:
                    continue
                qs = qs[::-1]
                for qq in range(5):
                    q[qq][k] = qs[qq]
                got += 1
        except Exception:
            continue
        if got < NM:                      # 구멍이 있으면 구간 통계가 어긋난다
            if got < NM * 0.95:
                thin += 1
                continue
            for qq in range(5):           # 드문 구멍은 그달 0 으로 둔다(양쪽 동일)
                q[qq] = [0.0 if v is None else v for v in q[qq]]
        rows.append({"sid": "t-" + S["sid"], "name": S["name"], "q": q, "got": got})
        if z % 20 == 0:
            print("  [%3d/%d] %.0f초" % (z, len(xs), time.time() - t0))
    print("팩터 %d종 (구멍으로 뺀 것 %d) · %.0f초" % (len(rows), thin, time.time() - t0))

    # ── F5 ──────────────────────────────────────────────────────────────
    oos_n = NM - IS_N
    F5 = thin / max(1, thin + len(rows)) > 0.20 or oos_n < 40
    # ── IS 에서 순위 ────────────────────────────────────────────────────
    for r in rows:
        r["is"] = stats_of(r["q"], 0, IS_N)
        r["oos"] = stats_of(r["q"], IS_N, NM)
    rows = [r for r in rows if r["is"] and r["oos"] and r["is"]["ls_t"] is not None]
    TS = [r["is"]["ls_t"] for r in rows]
    MO = [r["is"]["mono_pct"] for r in rows]
    for r in rows:
        r["r_t"] = prank(TS, r["is"]["ls_t"])
        r["r_m"] = prank(MO, r["is"]["mono_pct"])
        r["comb"] = r["r_t"] + r["r_m"]
    # F4 — IS 두 축 상관
    ma = sum(r["r_t"] for r in rows) / len(rows)
    mb = sum(r["r_m"] for r in rows) / len(rows)
    cov = sum((r["r_t"] - ma) * (r["r_m"] - mb) for r in rows)
    den = (sum((r["r_t"] - ma) ** 2 for r in rows)
           * sum((r["r_m"] - mb) ** 2 for r in rows)) ** 0.5
    rho_is = cov / den if den else 0.0

    # ── 주 결과 ─────────────────────────────────────────────────────────
    res = {}
    for key, lab in (("comb", "Combined"), ("r_t", "t-stat 단독"), ("r_m", "단조성 단독")):
        hi, lo = pick(rows, key, CUT, True), pick(rows, key, CUT, False)
        sh, sl = mean_ls(hi, IS_N, NM), mean_ls(lo, IS_N, NM)
        d = [a - b for a, b in zip(sh, sl)]
        res[key] = {"label": lab, "n_hi": len(hi), "n_lo": len(lo),
                    "oos_hi_bp": sum(sh) / len(sh) * 10000,
                    "oos_lo_bp": sum(sl) / len(sl) * 10000,
                    "diff_bp": (sum(sh) / len(sh) - sum(sl) / len(sl)) * 10000,
                    "diff_t": MN.tstat(d),
                    "hi_names": [r["name"] for r in sorted(hi, key=lambda z: -z[key])[:8]]}

    # ── 보조: 확장창 walk-forward ───────────────────────────────────────
    wf_hi, wf_lo = [], []
    s0 = WF_MIN
    while s0 + WF_STEP <= NM:
        sub = []
        for r in rows:
            a_ = stats_of(r["q"], 0, s0)
            if a_ and a_["ls_t"] is not None:
                sub.append({"r": r, "t": a_["ls_t"], "m": a_["mono_pct"]})
        if sub:
            T_ = [x["t"] for x in sub]; M_ = [x["m"] for x in sub]
            for x in sub:
                x["c"] = prank(T_, x["t"]) + prank(M_, x["m"])
            hi = [x["r"] for x in pick(sub, "c", CUT, True)]
            lo = [x["r"] for x in pick(sub, "c", CUT, False)]
            e_ = min(s0 + WF_STEP, NM)
            wf_hi += mean_ls(hi, s0, e_)
            wf_lo += mean_ls(lo, s0, e_)
        s0 += WF_STEP
    wf = None
    if wf_hi:
        dd = [a - b for a, b in zip(wf_hi, wf_lo)]
        wf = {"n": len(wf_hi), "hi_bp": sum(wf_hi) / len(wf_hi) * 10000,
              "lo_bp": sum(wf_lo) / len(wf_lo) * 10000,
              "diff_bp": (sum(wf_hi) / len(wf_hi) - sum(wf_lo) / len(wf_lo)) * 10000,
              "diff_t": MN.tstat(dd)}

    C = res["comb"]
    verdict = {
        "F1": "기각" if C["diff_bp"] <= 0 else "통과",
        "F2": "구별 불가" if (C["diff_t"] is None or C["diff_t"] < 1.5) else "통과",
        "F3": "결합의 값 없음" if C["oos_hi_bp"] <= res["r_t"]["oos_hi_bp"] else "통과",
        "F4": "전제 깨짐(해석 보류)" if abs(rho_is) > 0.30 else "통과",
        "F5": "측정 불가" if F5 else "통과",
    }
    doc = {"prereg": PREREG, "prereg_commit": COMMIT,
           "window": [dates[pairs[0][0]], dates[pairs[-1][1]]],
           "n_months": NM, "is_n": IS_N, "oos_n": oos_n, "cut": CUT,
           "n_factors": len(rows), "dropped_thin": thin,
           "rho_is": rho_is, "main": res, "walk_forward": wf, "verdict": verdict,
           "rows": [{k: r[k] for k in ("sid", "name", "r_t", "r_m", "comb")}
                    | {"is": {k: r["is"][k] for k in ("mono_pct", "ls_bp", "ls_t")},
                       "oos": {k: r["oos"][k] for k in ("mono_pct", "ls_bp", "ls_t")}}
                    for r in rows]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("\n" + "=" * 68)
    print("IS %d개월 %s~%s  →  OOS %d개월 %s~%s"
          % (IS_N, dates[pairs[0][0]], dates[pairs[IS_N - 1][1]],
             oos_n, dates[pairs[IS_N][0]], dates[pairs[-1][1]]))
    print("팩터 %d종 · IS 두 축 상관 ρ = %+.3f" % (len(rows), rho_is))
    print("\n %-14s %8s %8s %9s %8s" % ("고르는 법", "상위bp", "하위bp", "차이bp", "차이t"))
    for k in ("comb", "r_t", "r_m"):
        v = res[k]
        print(" %-14s %8.1f %8.1f %+9.1f %8s"
              % (v["label"], v["oos_hi_bp"], v["oos_lo_bp"], v["diff_bp"],
                 "—" if v["diff_t"] is None else "%.2f" % v["diff_t"]))
    if wf:
        print("\n 확장창 WF   %8.1f %8.1f %+9.1f %8s"
              % (wf["hi_bp"], wf["lo_bp"], wf["diff_bp"],
                 "—" if wf["diff_t"] is None else "%.2f" % wf["diff_t"]))
    print("\n── 실패 조건 대조 ──")
    for k in ("F1", "F2", "F3", "F4", "F5"):
        print("  %s  %s" % (k, verdict[k]))
    print("\n── IS Combined 상위 8 (이것이 OOS 를 맞혀야 했다) ──")
    for nm in C["hi_names"]:
        print("   · %s" % nm)
    print("\n%.0f초 → %s" % (time.time() - t0, os.path.basename(OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
