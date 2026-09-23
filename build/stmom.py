# -*- coding: utf-8 -*-
"""build/stmom.py — 단기 모멘텀(Medhat·Schmeling, RFS 2022) 시점정확 검정 → data/_stmom.json

사전등록: build/PREREG-2026-09-23-STMOM.md (계산 전 커밋 7b6b54db)

원문 표 III 패널 C 를 랩 PIT 유니버스로 옮긴다 —
  매월 말, 그때의 S&P 500 ∪ NASDAQ 100 멤버(금융 제외 · 이중클래스 회사당 하나) 중 자격 있는 종목을
  지난달 수익률 r 과 지난달 회전율 TO 로 각각 중앙값에서 갈라 2×2 독립 정렬하고, 시총가중으로
  STMOM = 고회전·승자 − 고회전·패자 · STREV* = 저회전·승자 − 저회전·패자 를 다음 달 한 달 든다.

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
⚠ 사전등록이 정하지 않은 구현 세부는 결과 문서 «정하지 않은 자리» 에 적는다(여기 주석에도 표시).

  python build/stmom.py
"""
from __future__ import annotations
import io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import index_members as IM            # noqa: E402  멤버십 정본
import tech_backtest as TB            # noqa: E402  주식수 정본(load_fund)·공시 지연(asof_all)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_stmom.json")

F0, F1_ = "2016-08", "2026-07"        # 형성월 창 — 사전등록 고정(보유 2016-09 ~ 2026-08)
POST = "2019-01"                       # 발표 후 보유월 시작
MIN_DAYS = 15                          # 원문 15일 규칙
COST = 0.0010                          # 편도 10bp
F_T = 1.5
KEEP_DUAL = {"GOOGL", "FOXA", "NWSA"}  # 사전등록 §1 — 회사당 하나


def tstat(v):
    v = np.asarray(v, dtype=float)
    if len(v) < 2 or v.std(ddof=1) == 0:
        return None
    return float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v))))


def nw_t(v, lag=6):
    """Newey-West t (서술용) — 판정은 단순 t(랩 관례)."""
    v = np.asarray(v, dtype=float)
    n = len(v)
    e = v - v.mean()
    s = (e @ e) / n
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    se = math.sqrt(s / n) if s > 0 else None
    return float(v.mean() / se) if se else None


def ols_alpha_t(y, X):
    """y = a + Xb + e 의 a 와 그 t(보통 OLS 표준오차)."""
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    dof = len(y) - X.shape[1]
    s2 = (e @ e) / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    return float(b[0]), float(b[0] / math.sqrt(cov[0, 0]))


def main() -> int:
    t0 = time.time()
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = S["pxd_dates"]
    D = len(dates)
    didx = {d: i for i, d in enumerate(dates)}
    sector_now = {s["t"]: s.get("sector") for s in S["stocks"]}

    # ── 일간 격자: 오늘 유니버스(sd) + 편출 캐시 ─────────────────────────────
    PX, VO = {}, {}
    for t in sector_now:
        d = json.load(io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8"))
        PX[t] = np.array([np.nan if v is None else float(v) for v in d["pxd"]])
        VO[t] = np.array([np.nan if v is None else float(v) for v in d["vd"]])
    # 🚨 2026-09-23 정정 — 편출 가격은 **정리본 data/pit_px.json** 을 쓴다(격리·합병 보정 반영).
    #   처음에는 원시 캐시 _pit_px_cache.json 을 읽었는데, 그 안의 PARA 는 랩이 2026-09-14 에 격리한
    #   «다른 증권» 계열이다(주당 57~113,900달러). 그 한 종목이 시총가중을 지배해 Eg 첫 판을 오염시켰다.
    #   정리본은 157종으로 원시 캐시(122종)보다 넓다 — 인수된 36종이 더 들어 있다.
    pxc = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))["px"]
    voc = json.load(io.open(os.path.join(DATA, "_pit_vol_cache.json"), encoding="utf-8"))

    def grid(dct):
        a = np.full(D, np.nan)
        for k, v in dct.items():
            i = didx.get(k)
            if i is not None and v is not None:
                a[i] = float(v)
        return a

    def unpack(obj):
        # pit_px.json 의 한 종목 = {i0: 격자 시작 인덱스, p: 가격 배열} (날짜 사전이 아니다)
        a = np.full(D, np.nan)
        i0, arr = int(obj.get("i0") or 0), obj.get("p") or []
        for j, v in enumerate(arr):
            if v is not None and 0 <= i0 + j < D:
                a[i0 + j] = float(v)
        return a

    for t, obj in pxc.items():
        if t not in PX:
            PX[t] = unpack(obj)
            VO[t] = grid(voc.get(t) or {})
    PU = json.load(io.open(os.path.join(DATA, "pit_universe.json"), encoding="utf-8"))
    splice = PU.get("cik_spliced") or {}
    REU = json.load(io.open(os.path.join(DATA, "pit_reuse.json"), encoding="utf-8"))
    reassigned = REU.get("reassigned") or {}
    LED = json.load(io.open(os.path.join(DATA, "index_ledger.json"), encoding="utf-8"))
    meta = LED.get("meta") or {}
    H = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    cikmap = H.get("cik") or {}

    FUND = TB.load_fund(extra_dirs=[os.path.join(DATA, "fx_pit")])

    def key(t):
        """멤버 티커 → 가격 계열 키. 오늘 이름 → 편출 캐시 → cik_spliced(옛 → 새) 순."""
        if t in PX:
            return t
        n = splice.get(t)
        if n and n in PX:
            return n
        return None

    def sector(t, k):
        s = sector_now.get(k) or sector_now.get(t)
        if s:
            return s
        m = meta.get(t) or meta.get(k)
        return m[1] if (m and len(m) > 1) else None

    def shares(t, k, d):
        for c in (k, t):
            f = FUND.get(c) or {}
            sh = f.get("sh")
            if sh:
                obs = TB.asof_all(sh, d)          # 90일 공시 지연 컷을 통과한 관측(최신순) — 첫 값이 그때 알 수 있던 주식수
                if obs and obs[0][1]:
                    return obs[0][1]
        return None

    mem, _car = IM.load(F0)
    months = [m for m in sorted(mem) if F0 <= m <= F1_]
    # 월말 거래일 인덱스
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i

    def prevm(ym):
        y, mo = int(ym[:4]), int(ym[5:7])
        return "%04d-%02d" % (y - (mo == 1), 12 if mo == 1 else mo - 1)

    def nextm(ym):
        y, mo = int(ym[:4]), int(ym[5:7])
        return "%04d-%02d" % (y + (mo == 12), 1 if mo == 12 else mo + 1)

    rows, cover, drops = [], [], {"no_px": 0, "fin": 0, "dual": 0, "thin": 0, "no_sh": 0, "reuse": 0}
    prev_w = {}
    for m in months:
        e1, e0, e2 = me[m], me[prevm(m)], me.get(nextm(m))
        if e2 is None:
            raise SystemExit("🚨 %s 의 다음 달 말이 격자에 없다" % m)
        members = mem[m]
        # 이중클래스 — 같은 CIK 가 둘이면 하나만(사전등록 KEEP_DUAL, 그 밖은 사전순 첫째 · 정하지 않은 자리)
        by_cik = {}
        for t in members:
            c = cikmap.get(t) or cikmap.get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        keep = set()
        for c, ts in by_cik.items():
            if len(ts) == 1 or c.startswith("_"):
                keep.update(ts)
                continue
            k_ = [t for t in ts if t in KEEP_DUAL]
            keep.add(k_[0] if k_ else sorted(ts)[0])
            drops["dual"] += len(ts) - 1
        n_mem = len(members)
        have_px = 0
        cand = []
        for t in sorted(keep):
            k = key(t)
            if k is None or not (PX[k][e1] == PX[k][e1]):
                drops["no_px"] += 1
                continue
            have_px += 1
            if (sector(t, k) or "").strip() == "Financials":
                drops["fin"] += 1
                continue
            if t in reassigned and m >= reassigned[t].get("last", "9999"):
                drops["reuse"] += 1          # 정하지 않은 자리 — 재배정 티커의 마지막 멤버월은 뺀다
                continue
            p = PX[k]
            v = VO[k]
            seg = range(e0 + 1, e1 + 1)
            nret = sum(1 for j in seg if p[j] == p[j] and p[j - 1] == p[j - 1] and p[j - 1] > 0)
            nvol = sum(1 for j in seg if v[j] == v[j] and v[j] > 0)
            if nret < MIN_DAYS or nvol < MIN_DAYS or not (p[e0] == p[e0] and p[e0] > 0):
                drops["thin"] += 1
                continue
            sh = shares(t, k, dates[e1])
            if not sh or sh <= 0:
                drops["no_sh"] += 1
                continue
            vol_sum = float(np.nansum(v[e0 + 1:e1 + 1]))
            r = p[e1] / p[e0] - 1
            to = vol_sum / sh
            mcap = p[e1] * sh
            # 보유월 수익 — 다음 달 말 가격, 없으면 그 사이 마지막 가격(상장폐지·인수)
            seg2 = p[e1 + 1:e2 + 1]
            ok = np.where(seg2 == seg2)[0]
            rn = (seg2[ok[-1]] / p[e1] - 1) if len(ok) else 0.0
            # 형성월 마지막 3거래일을 뺀 판(서술)
            e1x = e1 - 3
            r_x = p[e1x] / p[e0] - 1 if (p[e1x] == p[e1x]) else float("nan")
            to_x = float(np.nansum(v[e0 + 1:e1x + 1])) / sh
            cand.append({"t": t, "k": k, "r": r, "to": to, "mc": mcap, "rn": rn, "rx": r_x, "tox": to_x})
        # 커버리지 분모는 이중클래스를 정리한 뒤의 회사 수다(같은 회사를 두 번 세지 않는다)
        cover.append({"m": m, "members": n_mem, "kept": len(keep), "px": have_px,
                      "share": have_px / len(keep) if keep else None, "eligible": len(cand)})
        if len(cand) < 40:
            raise SystemExit("🚨 %s 자격 종목 %d — 너무 얇다" % (m, len(cand)))

        def legs(rk, tk):
            rs = np.array([c[rk] for c in cand], float)
            ts_ = np.array([c[tk] for c in cand], float)
            okm = ~np.isnan(rs)
            rmed = np.median(rs[okm])
            tmed = np.median(ts_[okm])
            out = {}
            for nm, fn in (("HW", lambda c: c[rk] > rmed and c[tk] > tmed),
                           ("HL", lambda c: c[rk] <= rmed and c[tk] > tmed),
                           ("LW", lambda c: c[rk] > rmed and c[tk] <= tmed),
                           ("LL", lambda c: c[rk] <= rmed and c[tk] <= tmed)):
                g = [c for c in cand if c[rk] == c[rk] and fn(c)]      # NaN(가격 빈 칸)은 어느 칸에도 안 든다
                wsum = sum(c["mc"] for c in g)
                out[nm] = {"n": len(g), "ret": sum(c["mc"] * c["rn"] for c in g) / wsum if wsum else 0.0,
                           "w": {c["t"]: c["mc"] / wsum for c in g} if wsum else {}}
            return out

        L = legs("r", "to")
        Lx = legs("rx", "tox")
        wu = sum(c["mc"] for c in cand)
        univ = sum(c["mc"] * c["rn"] for c in cand) / wu
        rn_map = {c["t"]: c["rn"] for c in cand}
        # 다리별 회전 — 직전 비중을 그 달 수익으로 굴린 뒤 새 비중과의 차이(편도 = ½Σ|Δw|)
        turns = {}
        for nm in ("HW", "HL", "LW", "LL"):
            pw = prev_w.get(nm) or {}
            if pw:
                drift = {t: w * (1 + prev_rn.get(t, 0.0)) for t, w in pw.items()}
                s_ = sum(drift.values()) or 1.0
                drift = {t: w / s_ for t, w in drift.items()}
            else:
                drift = {}
            nw = L[nm]["w"]
            names = set(drift) | set(nw)
            turns[nm] = 0.5 * sum(abs(nw.get(t, 0.0) - drift.get(t, 0.0)) for t in names) if pw else None
            prev_w[nm] = nw
        prev_rn = rn_map
        rows.append({"m": nextm(m), "form": m,
                     "stmom": (L["HW"]["ret"] - L["HL"]["ret"]) * 100,
                     "strev": (L["LW"]["ret"] - L["LL"]["ret"]) * 100,
                     "stmom_x": (Lx["HW"]["ret"] - Lx["HL"]["ret"]) * 100,
                     "hw_minus_univ": (L["HW"]["ret"] - univ) * 100, "univ": univ * 100,
                     "n": {k_: L[k_]["n"] for k_ in L}, "turn": turns})
    dt = time.time() - t0

    # ── 집계 ──────────────────────────────────────────────────────────────
    st = np.array([r["stmom"] for r in rows])
    sr = np.array([r["strev"] for r in rows])
    sx = np.array([r["stmom_x"] for r in rows])
    lo = np.array([r["hw_minus_univ"] for r in rows])
    post = np.array([r["stmom"] for r in rows if r["m"] >= POST])
    pre = np.array([r["stmom"] for r in rows if r["m"] < POST])
    tw = [(r["turn"]["HW"], r["turn"]["HL"]) for r in rows if r["turn"]["HW"] is not None]
    cost = np.array([0.0] + [COST * (a + b) * 100 for a, b in tw])        # 첫 달은 비교 대상 없음 — 0(정하지 않은 자리)
    cost2 = cost * 2                                                      # 양방향 계산(서술 · 보수)
    st_net = st - cost
    st_net2 = st - cost2
    cov_min = min(c["share"] for c in cover)
    cov_med = float(np.median([c["share"] for c in cover]))

    # ── 위생 — 모집단 시총가중 vs S&P 500(PR) ───────────────────────────────
    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))
    spx = CH["idx_monthly"]["S&P 500"]
    uu = [(r["univ"], spx[r["m"]]) for r in rows if r["m"] in spx]
    corr_spx = float(np.corrcoef([a for a, b in uu], [b for a, b in uu])[0, 1])
    gap_spx = float(np.mean([a - b for a, b in uu]))

    # ── F6 — 증분(랩 종목 수익엔진 110종 중 상관 상위 5 동시 통제) ─────────────
    IX = {s["sid"]: s for s in json.load(io.open(os.path.join(DATA, "strategy_index.json"), encoding="utf-8"))["items"]}
    mset = [r["m"] for r in rows]
    pool = []
    for sid, c in CH["charts"].items():
        s = IX.get(sid)
        mo = c.get("monthly") or []
        if not s or s.get("src") != "종목 전략" or s.get("role") != "수익엔진" or len(mo) < 100:
            continue
        ex = {x["m"]: x["r"] - x["b"] for x in mo if x.get("r") is not None and x.get("b") is not None}
        if all(m_ in ex for m_ in mset):
            pool.append((sid, s.get("name"), np.array([ex[m_] for m_ in mset])))
    cors = sorted(((abs(np.corrcoef(st, v)[0, 1]), float(np.corrcoef(st, v)[0, 1]), sid, nm, v) for sid, nm, v in pool),
                  key=lambda x: -x[0])
    # 상관 상위 5 — 서로 사실상 같은 계열(상관 0.999 초과, 예: 밴드판 = 원판)은 하나만 남긴다(eg_q5 와 같은 규칙)
    top5 = []
    for x in cors:
        if all(abs(np.corrcoef(x[4], y[4])[0, 1]) < 0.999 for y in top5):
            top5.append(x)
        if len(top5) == 5:
            break
    a6, t6 = ols_alpha_t(st, np.column_stack([x[4] for x in top5]))

    f1 = float(st.mean()); t_ = tstat(st)
    res = {
        "f1": {"hit": not (f1 > 0), "mean_pm": f1},
        "f2": {"hit": not (t_ is not None and t_ >= F_T), "t": t_, "t_nw6": nw_t(st), "문턱": F_T},
        "f3": {"hit": not (post.mean() > 0), "post_mean_pm": float(post.mean()), "post_t": tstat(post), "n_post": len(post),
               "pre_mean_pm": float(pre.mean()), "pre_t": tstat(pre), "n_pre": len(pre)},
        "f4": {"hit": cov_min < 0.80, "cover_min": cov_min, "cover_med": cov_med},
        "f5": {"hit": not (st_net.mean() > 0), "net_mean_pm": float(st_net.mean()), "net_t": tstat(st_net),
               "cost_mean_pm": float(cost.mean()), "net2_mean_pm": float(st_net2.mean()), "net2_t": tstat(st_net2)},
        "f6": {"hit": not (t6 >= F_T), "alpha_pm": a6, "t": t6, "n_pool": len(pool),
               "top5": [{"sid": x[2], "name": x[3], "corr": x[1]} for x in top5]},
    }
    verdict = ("기각" if (res["f1"]["hit"] or res["f2"]["hit"] or res["f3"]["hit"] or res["f5"]["hit"]) else
               "보류" if (res["f4"]["hit"] or res["f6"]["hit"]) else "게시 후보")
    avg_turn = {nm: float(np.mean([r["turn"][nm] for r in rows if r["turn"][nm] is not None])) for nm in ("HW", "HL", "LW", "LL")}
    avg_n = {nm: float(np.mean([r["n"][nm] for r in rows])) for nm in ("HW", "HL", "LW", "LL")}
    doc = {"note": "단기 모멘텀 PIT 검정. 사전등록 PREREG-2026-09-23-STMOM(계산 전 커밋 7b6b54db) 값 그대로.",
           "prereg": "build/PREREG-2026-09-23-STMOM.md", "commit": "7b6b54db",
           "window": "보유 %s ~ %s (%d개월) · 발표 후 %s~" % (rows[0]["m"], rows[-1]["m"], len(rows), POST),
           "summary": {"stmom_mean_pm": f1, "stmom_t": t_, "strev_mean_pm": float(sr.mean()), "strev_t": tstat(sr),
                       "stmom_skipEOM_mean_pm": float(sx.mean()), "stmom_skipEOM_t": tstat(sx),
                       "longonly_hw_minus_univ_pm": float(lo.mean()), "longonly_t": tstat(lo),
                       "avg_turnover_oneway": avg_turn, "avg_n": avg_n},
           "sanity": {"univ_vs_spx_corr": corr_spx, "univ_minus_spx_pm": gap_spx},
           "drops": drops, "coverage": cover, **res, "verdict": verdict,
           "monthly": [{"m": r["m"], "stmom": round(r["stmom"], 4), "strev": round(r["strev"], 4),
                        "stmom_x": round(r["stmom_x"], 4), "lo": round(r["hw_minus_univ"], 4)} for r in rows]}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("보유 %s ~ %s · %d개월 · %.0f초" % (rows[0]["m"], rows[-1]["m"], len(rows), dt))
    print("위생: 모집단 시총가중 vs S&P 500(PR) 상관 %.3f · 차이 월 %+.3f%%p (배당·금융 제외 몫)" % (corr_spx, gap_spx))
    print("커버리지(멤버 중 가격 있음): 최저 %.1f%% · 중앙 %.1f%% · 제외 %s" % (cov_min * 100, cov_med * 100, drops))
    print("평균 종목 수 %s · 편도 회전(월) %s" % ({k: round(v, 1) for k, v in avg_n.items()}, {k: round(v, 2) for k, v in avg_turn.items()}))
    print("\n  STMOM   월 %+.3f%% · t %.2f (NW6 %.2f)" % (f1, t_, nw_t(st)))
    print("  STREV*  월 %+.3f%% · t %.2f   (서술)" % (sr.mean(), tstat(sr)))
    print("  STMOM 월말 3일 제외  월 %+.3f%% · t %.2f   (서술)" % (sx.mean(), tstat(sx)))
    print("  롱온리 고회전 승자 − 모집단  월 %+.3f%% · t %.2f   (서술)" % (lo.mean(), tstat(lo)))
    print("\n🚨 실패 조건")
    print("  F1 평균 %+.3f%% → %s" % (f1, "걸림 ✗" if res["f1"]["hit"] else "통과"))
    print("  F2 t %.2f (문턱 %.1f) → %s" % (t_, F_T, "구별 불가 ✗" if res["f2"]["hit"] else "통과"))
    print("  F3 발표 후 %d개월 월 %+.3f%% · t %.2f  (앞 %d개월 %+.3f%% · t %.2f) → %s"
          % (len(post), post.mean(), tstat(post), len(pre), pre.mean(), tstat(pre), "걸림 ✗" if res["f3"]["hit"] else "통과"))
    print("  F4 커버리지 최저 %.1f%% → %s" % (cov_min * 100, "보류 ✗" if res["f4"]["hit"] else "통과"))
    print("  F5 편도 10bp 뒤 월 %+.3f%% · t %.2f (비용 월 %.3f%%) · 양방향 계산 %+.3f%% → %s"
          % (st_net.mean(), tstat(st_net), cost.mean(), st_net2.mean(), "걸림 ✗" if res["f5"]["hit"] else "통과"))
    print("  F6 증분(상관 상위 5종 통제) 알파 월 %+.3f%% · t %.2f → %s" % (a6, t6, "보류 ✗" if res["f6"]["hit"] else "통과"))
    for x in top5:
        print("       %+.3f  %s  %s" % (x[1], x[2], x[3]))
    print("\n판정: **%s**" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
