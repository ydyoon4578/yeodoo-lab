# -*- coding: utf-8 -*-
"""build/rally_pattern.py — 본격 상승 직전의 패턴(사건 연구) → data/_rally.json

사전등록: build/PREREG-2026-09-24-RALLY.md (계산 전 커밋 75d72ddd)

매주 마지막 거래일, 그때의 S&P 500 · NASDAQ 100 구성 종목(편출 종목 포함 · 전달 말 명단)마다 특징 여섯을 재고,
다음 13주(65거래일) 자기 지수 대비 초과가 그 주 상위 10%(큰 상승)·하위 10%(큰 하락)에 드는지를 본다.
«패턴이 있을 때 큰 상승 확률이 기준(10%)보다 얼마나 오르나» 와 «큰 하락 확률은 얼마나 오르나» 를 같이 잰다.

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
⚠ 사전등록이 정하지 않은 구현 세부는 결과 문서 «정하지 않은 자리» 에 적는다(여기 주석에도 «정하지 않은 자리» 로 표시).

  python build/rally_pattern.py
"""
from __future__ import annotations
import datetime as dt
import io, json, math, os, sys, time

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402  시점정확 패널 정본(가격·명단·이중클래스·재배정)

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_rally.json")

W0, W1, HALF = "2014-07", "2026-06", "2020-07"      # 사전등록 §1 · §4
H13, H26 = 65, 130                                   # 앞 창(거래일) — 13주 · 서술 26주
TOP, BOT, QUINT = 0.90, 0.10, 0.20
NW_LAG = 13
FEATS = ["RVOL", "UPVOL", "BRKVOL", "HI52", "VCON", "MOM"]
VOLUME3 = ["RVOL", "UPVOL", "BRKVOL"]               # 머리 판정(사전등록 §5)
LOW_SIDE = {"VCON"}                                  # 패턴 쪽이 하위 20%
EVENT = {"BRKVOL"}                                   # 사건(예/아니오)
IX = (("spx", "SPX", "S&P 500"), ("ndx", "NDX", "NASDAQ 100"))


def nw_t(x, lag=NW_LAG):
    """평균의 Newey-West t(Bartlett). x 는 결측 없는 1차원."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return None
    m = x.mean()
    e = x - m
    s = (e @ e) / n
    for L in range(1, min(lag, n - 1) + 1):
        w = 1.0 - L / (lag + 1.0)
        s += 2.0 * w * (e[L:] @ e[:-L]) / n
    return float(m / math.sqrt(s / n)) if s > 0 else None


def p2(t):
    return None if t is None else float(math.erfc(abs(t) / math.sqrt(2.0)))


def features(p, v):
    """한 종목의 일간 가격·거래량 → 특징 여섯(길이 D 배열). 사전등록 §3 의 창·최소 자료 그대로."""
    s = pd.Series(p)
    vv = pd.Series(v)
    vv = vv.where((vv > 0) & s.notna())                       # 거래량 0 · 가격 없는 날의 거래량은 결측
    out = {}
    # MOM — 21거래일 전 ÷ 252거래일 전 − 1 (정확한 자리 · 결측이면 결측)
    out["MOM"] = (s.shift(21) / s.shift(252) - 1.0).values
    # HI52 — 종가 ÷ 최근 252일 최고 종가(200일 이상 유효)
    out["HI52"] = (s / s.rolling(252, min_periods=200).max()).values
    # RVOL — 최근 20일 평균(15일) ÷ 그 앞 250일 평균(200일)
    out["RVOL"] = (vv.rolling(20, min_periods=15).mean()
                   / vv.shift(20).rolling(250, min_periods=200).mean()).values
    # UPVOL — 최근 50일 오른 날 거래량 ÷ (오른 날 + 내린 날) 거래량 · 유효 쌍 40 이상
    d = s - s.shift(1)
    ok = d.notna() & vv.notna()
    up = vv.where(ok & (d > 0), 0.0)
    dn = vv.where(ok & (d < 0), 0.0)
    su = up.rolling(50, min_periods=1).sum()
    sdn = dn.rolling(50, min_periods=1).sum()
    npair = ok.astype(float).rolling(50, min_periods=1).sum()
    upv = su / (su + sdn)
    out["UPVOL"] = upv.where((npair >= 40) & ((su + sdn) > 0)).values
    # VCON — 최근 20일 로그수익 표준편차(15) ÷ 최근 250일(200)
    r = np.log(s / s.shift(1))
    out["VCON"] = (r.rolling(20, min_periods=15).std(ddof=1)
                   / r.rolling(250, min_periods=200).std(ddof=1)).values
    # BRKVOL — 종가 ≥ 앞 251일 최고 종가(200일) 그리고 최근 5일 평균(4일 · 정하지 않은 자리) ≥ 앞 250일 평균(200일) × 1.5
    prior_hi = s.shift(1).rolling(251, min_periods=200).max()
    v5 = vv.rolling(5, min_periods=4).mean()
    v250 = vv.shift(5).rolling(250, min_periods=200).mean()
    comp = prior_hi.notna() & v5.notna() & v250.notna() & s.notna()
    ev = (s >= prior_hi) & (v5 >= 1.5 * v250)
    out["BRKVOL"] = np.where(comp.values, ev.values.astype(float), np.nan)
    return out


def fwd_excess(p, B, i, h, D):
    """신호일 i → 다음 거래일(없으면 5일 안의 첫 유효일) 부터 h 거래일. 끊기면 마지막 가격까지의 초과."""
    st = None
    for j in range(i + 1, min(i + 6, D)):
        if p[j] == p[j] and p[j] > 0:
            st = j
            break
    if st is None:
        return None
    end = st + h
    if end > D - 1:
        return None                                  # 앞 창이 자료 밖이다 — 그 주는 표본이 아니다
    seg = p[st:end + 1]
    okj = np.where(seg == seg)[0]
    e = st + int(okj[-1])
    if not (B[e] == B[e] and B[st] == B[st]):
        return None
    return (p[e] / p[st]) / (B[e] / B[st]) - 1.0


def week_ends(dates):
    """ISO 주마다 마지막 거래일의 인덱스."""
    last = {}
    for i, d in enumerate(dates):
        y, w, _ = dt.date.fromisoformat(d).isocalendar()
        last[(y, w)] = i
    return sorted(last.values())


def pct_rank(x):
    """한 주 안의 백분위(0~100) — 평균 순위 방식."""
    return pd.Series(x).rank(pct=True, method="average").values * 100.0


def main() -> int:
    t0 = time.time()
    Wd = PP.load_world()
    dates, D, PX = Wd["dates"], Wd["D"], Wd["PX"]
    today = Wd["today"]

    # ── 거래량: 오늘 종목 sd.vd · 편출 종목 _pit_vol_cache.json(날짜 사전) ─────────────
    didx = {d: i for i, d in enumerate(dates)}
    VO = {}
    for t in today:
        d = json.load(io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8"))
        VO[t] = np.array([np.nan if x is None else float(x) for x in d["vd"]])
    voc = json.load(io.open(os.path.join(DATA, "_pit_vol_cache.json"), encoding="utf-8"))
    for t in PX:
        if t in VO:
            continue
        a = np.full(D, np.nan)
        for k, x in (voc.get(t) or {}).items():
            j = didx.get(k)
            if j is not None and x is not None:
                a[j] = float(x)
        VO[t] = a

    # ── 지수(PR) — bench_px 를 종목 격자에 맞춘다(없는 날은 앞 값) ─────────────────
    Bj = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    bidx = {d: i for i, d in enumerate(Bj["dates"])}
    BEN = {}
    for ix, *_ in IX:
        src = Bj["series"][ix]["px"]
        a = np.array([np.nan if (bidx.get(d) is None or src[bidx[d]] is None) else float(src[bidx[d]])
                      for d in dates])
        BEN[ix] = pd.Series(a).ffill().values

    # ── 특징(종목마다 한 번) ──────────────────────────────────────────────────
    FT = {k: features(PX[k], VO[k]) for k in PX}
    print("특징 %d종 (%.0fs)" % (len(FT), time.time() - t0))

    wk_all = week_ends(dates)
    weeks = [i for i in wk_all if W0 <= dates[i][:7] <= W1 and i + 1 + H13 <= D - 1]
    print("신호 주 %d (%s ~ %s)" % (len(weeks), dates[weeks[0]], dates[weeks[-1]]))

    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    today_idx = {s["t"]: (s.get("idx") or []) for s in S["stocks"]}

    def members_pit(ix, i):
        """전달 말 명단 → 이중클래스 하나 · 재배정 마지막 달 제외 → [(명단 티커, 가격 키)]."""
        m = dates[i][:7]
        pm = PP.mshift(m, -1)
        mem = Wd["lists"][ix].get(pm) or []
        by_cik = {}
        for t in mem:
            c = Wd["cikmap"].get(t) or Wd["cikmap"].get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        keep = []
        for c, ts in by_cik.items():
            if len(ts) == 1 or c.startswith("_"):
                keep.extend(ts)
                continue
            k_ = [t for t in ts if t in PP.KEEP_DUAL]
            keep.append(k_[0] if k_ else sorted(ts)[0])
        out = []
        for t in sorted(keep):
            if t in Wd["reassigned"] and pm >= Wd["reassigned"][t].get("last", "9999"):
                continue
            out.append((t, PP._key(Wd, t)))
        return out, len(keep)

    def members_today(ix_code):
        """생존 편향 측정용 — 오늘 명단(stocks.json idx) · sd 자료만. 이중클래스는 같은 규칙으로 하나."""
        ts = [t for t, ixs in today_idx.items() if ix_code in ixs]
        by_cik = {}
        for t in ts:
            c = Wd["cikmap"].get(t) or Wd["cikmap"].get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        keep = []
        for c, g in by_cik.items():
            if len(g) == 1 or c.startswith("_"):
                keep.extend(g)
                continue
            k_ = [t for t in g if t in PP.KEEP_DUAL]
            keep.append(k_[0] if k_ else sorted(g)[0])
        return [(t, t) for t in sorted(keep)]

    def panel(ix, mode):
        """주마다 표본 행렬 → 목록. mode = 'pit' | 'today'."""
        B = BEN[ix]
        code = dict((a, b) for a, b, _ in IX)[ix]
        tod = members_today(code) if mode == "today" else None
        rows, cov, ew = [], [], []
        prev_sample = None
        for i in weeks:
            if mode == "pit":
                mem, n_mem = members_pit(ix, i)
            else:
                mem, n_mem = tod, len(tod)
            X = {f: [] for f in FEATS}
            ex13, ex26, keys = [], [], []
            for t, k in mem:
                if k is None:
                    continue
                p = PX[k]
                if not (p[i] == p[i] and p[i] > 0):
                    continue
                fv = [FT[k][f][i] for f in FEATS]
                if any(x != x for x in fv):
                    continue                                 # 공통 표본 — 여섯이 전부 서야 든다
                e13 = fwd_excess(p, B, i, H13, D)
                if e13 is None:
                    continue
                e26 = fwd_excess(p, B, i, H26, D)
                for f, x in zip(FEATS, fv):
                    X[f].append(x)
                ex13.append(e13)
                ex26.append(np.nan if e26 is None else e26)
                keys.append(k)
            n = len(ex13)
            cov.append(n / max(1, n_mem))
            if n < 30:
                continue
            row = {"i": i, "d": dates[i], "n": n, "X": {f: np.array(X[f]) for f in FEATS},
                   "e13": np.array(ex13), "e26": np.array(ex26), "keys": keys}
            rows.append(row)
            # F0(가) — 직전 주 표본의 이번 주 동일가중 수익 vs 지수
            if prev_sample is not None:
                pi, pk = prev_sample
                rr = [PX[k][i] / PX[k][pi] - 1 for k in pk if PX[k][i] == PX[k][i] and PX[k][pi] == PX[k][pi] and PX[k][pi] > 0]
                if rr:
                    ew.append((float(np.mean(rr)), B[i] / B[pi] - 1))
            prev_sample = (i, keys)
        return rows, cov, ew

    def labels(e):
        """그 주 표본 안의 상위·하위 10% — 결측(26주 창 밖)은 빼고 가른다."""
        ok = np.isfinite(e)
        top = np.zeros(len(e), bool)
        bot = np.zeros(len(e), bool)
        if ok.sum() >= 20:
            hi, lo = np.quantile(e[ok], TOP), np.quantile(e[ok], BOT)
            top = ok & (e >= hi)
            bot = ok & (e <= lo)
        return top, bot, ok

    def pattern(f, x):
        if f in EVENT:
            return x > 0.5
        if f in LOW_SIDE:
            return x <= np.quantile(x, QUINT)
        return x >= np.quantile(x, 1.0 - QUINT)

    def measure(rows, horizon="e13", ctrl=True, backward=True):
        res = {}
        for f in FEATS:
            H_, B_, C_, CB_, dd, spread, halves = [], [], [], [], [], [], {"a": [[], []], "b": [[], []]}
            cq_h, cq_b, cq_d = [], [], []
            back_top, back_bot, ev_top, ev_bot, ev_all = [], [], [], [], []
            for r in rows:
                e = r[horizon]
                top, bot, ok = labels(e)
                if ok.sum() < 20:
                    continue
                x = r["X"][f]
                P = pattern(f, x) & ok
                A = ok
                if P.sum() == 0:
                    continue
                h, b = top[P].mean(), top[A].mean()
                c, cb = bot[P].mean(), bot[A].mean()
                H_.append(h); B_.append(b); C_.append(c); CB_.append(cb); dd.append(h - b)
                spread.append(np.nanmean(e[P]) - np.nanmean(e[A]))
                hk = "a" if r["d"][:7] < HALF else "b"
                halves[hk][0].append(h); halves[hk][1].append(b)
                if ctrl and f != "MOM":
                    mom = r["X"]["MOM"]
                    qs = np.quantile(mom[A], [0.2, 0.4, 0.6, 0.8])
                    qq = np.searchsorted(qs, mom, side="right")
                    hs, bs = [], []
                    for q in range(5):
                        Aq = A & (qq == q)
                        if Aq.sum() < 5:
                            continue
                        xq = x[Aq]
                        if f in EVENT:
                            Pq = Aq & (x > 0.5)
                        elif f in LOW_SIDE:
                            Pq = Aq & (x <= np.quantile(xq, QUINT))
                        else:
                            Pq = Aq & (x >= np.quantile(xq, 1.0 - QUINT))
                        if Pq.sum() == 0:
                            continue
                        hs.append(top[Pq].mean()); bs.append(top[Aq].mean())
                    if hs:
                        cq_h.append(np.mean(hs)); cq_b.append(np.mean(bs)); cq_d.append(np.mean(hs) - np.mean(bs))
                if backward:
                    pr = pct_rank(x[A]) if f not in EVENT else None
                    tA, bA = top[A], bot[A]
                    if pr is not None:
                        back_top.extend(pr[tA].tolist()); back_bot.extend(pr[bA].tolist())
                    else:
                        xa = x[A] > 0.5
                        ev_top.append(xa[tA].mean() if tA.any() else np.nan)
                        ev_bot.append(xa[bA].mean() if bA.any() else np.nan)
                        ev_all.append(xa.mean())
            if not H_:
                res[f] = None
                continue
            lt = float(np.sum(H_) / np.sum(B_))
            lb = float(np.sum(C_) / np.sum(CB_))
            t = nw_t(dd)
            o = {"weeks": len(H_), "lift_top": lt, "lift_bot": lb, "ratio": lt / lb if lb > 0 else None,
                 "t": t, "p": p2(t), "hit_top": float(np.mean(H_)), "base": float(np.mean(B_)),
                 "spread_pp": float(np.mean(spread) * 100), "spread_t": nw_t(spread),
                 "halves": {k: (float(np.sum(v[0]) / np.sum(v[1])) if v[1] else None) for k, v in halves.items()},
                 "halves_weeks": {k: len(v[0]) for k, v in halves.items()}}
            if cq_h:
                o["ctrl_lift"] = float(np.sum(cq_h) / np.sum(cq_b))
                o["ctrl_t"] = nw_t(cq_d)
            if backward:
                if back_top:
                    o["back_pct_top"] = float(np.mean(back_top))
                    o["back_pct_bot"] = float(np.mean(back_bot))
                if ev_all:
                    o["event_share_all"] = float(np.nanmean(ev_all))
                    o["event_share_top"] = float(np.nanmean(ev_top))
                    o["event_share_bot"] = float(np.nanmean(ev_bot))
            res[f] = o
        return res

    RESULT = {"prereg": "build/PREREG-2026-09-24-RALLY.md", "prereg_commit": "75d72ddd",
              "window": [dates[weeks[0]], dates[weeks[-1]]], "n_weeks": len(weeks), "half": HALF,
              "h13": H13, "h26": H26, "idx": {}}
    tests = []
    for ix, code, lab in IX:
        rows, cov, ew = panel(ix, "pit")
        a = np.array(ew)
        corr = float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]) if len(a) > 10 else None
        cov_med = float(np.median(cov)) if cov else 0.0
        f0 = bool(corr is not None and corr >= 0.90 and cov_med >= 0.90)
        big = []
        for r in rows:                                   # 위생 — 13주 초과가 +300% 넘는 종목-주(서술)
            for k, e in zip(r["keys"], r["e13"]):
                if e > 3.0:
                    big.append((r["d"], k, round(float(e) * 100, 1)))
        m13 = measure(rows, "e13")
        m26 = measure(rows, "e26", ctrl=False, backward=False)
        srows, scov, _ = panel(ix, "today")
        ms = measure(srows, "e13", ctrl=False, backward=False)
        n_sw = int(sum(r["n"] for r in rows))
        RESULT["idx"][ix] = {"label": lab, "f0": {"ok": f0, "ew_corr": corr, "coverage_med": cov_med,
                                                  "coverage_min": float(min(cov)) if cov else None},
                             "n_weeks": len(rows), "n_stock_weeks": n_sw,
                             "n_med": float(np.median([r["n"] for r in rows])) if rows else None,
                             "outliers_300": big[:20], "n_outliers_300": len(big),
                             "feat": m13, "feat26": m26,
                             "surv": {f: (ms[f] or {}).get("lift_top") for f in FEATS},
                             "surv_n_med": float(np.median([r["n"] for r in srows])) if srows else None}
        for f in FEATS:
            o = m13.get(f)
            tests.append((ix, f, (o or {}).get("p")))
        print("%s: 주 %d · 종목-주 %d · F0 상관 %.3f 커버 %.3f" % (lab, len(rows), n_sw, corr or float("nan"), cov_med))

    # ── Holm (12칸) ──────────────────────────────────────────────────────────
    ps = sorted([(p if p is not None else 1.0, ix, f) for ix, f, p in tests])
    m = len(ps)
    holm = {}
    stop = False
    for k, (p, ix, f) in enumerate(ps):
        rej = (not stop) and p < 0.05 / (m - k)
        if not rej:
            stop = True
        holm[(ix, f)] = bool(rej)

    verdict_cells = {}
    for ix, code, lab in IX:
        R = RESULT["idx"][ix]
        for f in FEATS:
            o = R["feat"].get(f)
            if not o:
                continue
            F1 = bool(o["lift_top"] >= 1.20 and holm[(ix, f)])
            hv = o["halves"]
            F2 = bool(hv.get("a") is not None and hv.get("b") is not None and hv["a"] >= 1.10 and hv["b"] >= 1.10)
            F4 = None if f == "MOM" else bool((o.get("ctrl_lift") or 0) >= 1.10 and (o.get("ctrl_t") or 0) >= 2.0)
            F5 = bool(o["ratio"] is not None and o["ratio"] >= 1.20)
            if F1 and F2 and F5 and (F4 is None or F4):
                cls = "방향 패턴"
            elif F1 and F2 and not F5:
                cls = "양쪽 꼬리(변동성)"
            elif F1 and F2 and F5 and F4 is False:
                cls = "모멘텀의 다른 얼굴"
            else:
                cls = "구별 안 됨"
            o.update({"holm": holm[(ix, f)], "F1": F1, "F2": F2, "F4": F4, "F5": F5, "class": cls})
            verdict_cells[(ix, f)] = cls
    f0_all = all(RESULT["idx"][ix]["f0"]["ok"] for ix, *_ in IX)
    dirp = {f: [ix for ix, *_ in IX if verdict_cells.get((ix, f)) == "방향 패턴"] for f in FEATS}
    if not f0_all:
        verdict = "판정 불가(F0)"
    elif any(len(dirp[f]) == 2 for f in VOLUME3):
        verdict = "게시 후보"
    elif any(len(dirp[f]) == 1 for f in VOLUME3):
        verdict = "보류"
    else:
        verdict = "기각"
    RESULT["verdict"] = verdict
    RESULT["direction_pattern"] = dirp
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(RESULT, ensure_ascii=False, indent=1,
                   default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")

    for ix, code, lab in IX:
        R = RESULT["idx"][ix]
        print("\n== %s  (F0 %s · 상관 %.3f · 커버 %.1f%% · 종목-주 %d)" % (lab, R["f0"]["ok"], R["f0"]["ew_corr"],
              R["f0"]["coverage_med"] * 100, R["n_stock_weeks"]))
        print("  %-7s %6s %6s %6s %6s %7s %7s %7s %7s %6s  %s" % ("특징", "상승×", "하락×", "비", "t", "반기a", "반기b",
              "통제×", "통제t", "생존×", "분류"))
        for f in FEATS:
            o = R["feat"].get(f) or {}
            hv = o.get("halves") or {}
            fmt = lambda v, d=2: "—" if v is None else ("%.*f" % (d, v))
            print("  %-7s %6s %6s %6s %6s %7s %7s %7s %7s %6s  %s" % (
                f, fmt(o.get("lift_top")), fmt(o.get("lift_bot")), fmt(o.get("ratio")), fmt(o.get("t")),
                fmt(hv.get("a")), fmt(hv.get("b")), fmt(o.get("ctrl_lift")), fmt(o.get("ctrl_t")),
                fmt(R["surv"].get(f)), o.get("class")))
    print("\n머리 판정(거래량 셋):", verdict, "· 방향 패턴:", dirp)
    print("→ %s (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
