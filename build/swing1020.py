# -*- coding: utf-8 -*-
"""build/swing1020.py — 과매도 롱 10 · 과매수 숏 10 (PREREG-2026-09-19-SWING1020)

사전등록 커밋 9e51af0c622aff8f99ac6a22446cc6936ebdb805 (계산 전).
규칙은 그 문서가 정본이다. 여기서 바꾸지 않는다.

  월말 종가로 진동자 5종의 횡단면 z 평균을 내고, 다음 거래일 종가로
  최저 10종목 롱 · 최고 10종목 숏. 동일가중 · 다음 월말까지 표류.

  python build/swing1020.py
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 지표는 화면이 쓰는 것을 그대로 가져온다 — 다시 구현하면 화면과 성적표가 갈린다.
from refresh_stocks import rsi, boll, cci, willr, stoch_k          # noqa: E402
from tech_backtest import COST_BPS, COST_BPS_MAIN                  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_SD = os.path.join(DATA, "sd")
OUT = os.path.join(DATA, "_swing1020.json")

TOPN = 10
WARMUP = 260
ZCLIP = 3.0
NSHUF = 200
SEED = 20260919
PREREG = "PREREG-2026-09-19-SWING1020"
COMMIT = "9e51af0c622aff8f99ac6a22446cc6936ebdb805"


def nw_t(x, lag=21):
    """Newey-West t — signal_lab.newey_west_t 와 같은 식(Bartlett)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    m = len(x)
    if m < 30:
        return None
    d = x - x.mean()
    var = float((d * d).sum() / m)
    for k in range(1, min(lag, m - 1) + 1):
        var += 2 * (1 - k / (lag + 1.0)) * float((d[k:] * d[:-k]).sum() / m)
    return round(float(x.mean() / math.sqrt(var / m)), 2) if var > 0 else None


def ann(rets, per=252):
    r = np.asarray(rets, float)
    nav = np.cumprod(1 + r)
    yrs = len(r) / per
    cagr = (float(nav[-1]) ** (1 / yrs) - 1) * 100
    vol = float(r.std(ddof=1)) * math.sqrt(per) * 100
    mdd = float(np.min(nav / np.maximum.accumulate(nav) - 1)) * 100
    return {"cagr": round(cagr, 2), "vol": round(vol, 2),
            "sharpe": round(cagr / vol, 3) if vol > 0 else None,
            "mdd": round(mdd, 2)}


def load():
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    n = len(dates)
    idx = pd.to_datetime(dates)
    px, hi, lo = {}, {}, {}
    for s in st["stocks"]:
        t = s["t"]
        p = os.path.join(DIR_SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        a, hh, ll = d.get("pxd"), d.get("hd"), d.get("ld")
        if not (isinstance(a, list) and len(a) == n):
            continue
        if not (isinstance(hh, list) and isinstance(ll, list) and len(hh) == n and len(ll) == n):
            continue
        px[t] = pd.Series(a, index=idx, dtype="float64")
        hi[t] = pd.Series(hh, index=idx, dtype="float64")
        lo[t] = pd.Series(ll, index=idx, dtype="float64")
    tick = sorted(px)
    return dates, tick, (pd.DataFrame({t: px[t] for t in tick}),
                         pd.DataFrame({t: hi[t] for t in tick}),
                         pd.DataFrame({t: lo[t] for t in tick}))


def score(P, H, L, tick):
    """과매수 점수 — 높을수록 과매수. 진동자 5종의 횡단면 z 평균."""
    parts = {}
    for nm in ("rsi", "pb", "cci", "wr", "k"):
        parts[nm] = {}
    for t in tick:
        c, h, l = P[t], H[t], L[t]
        _, _bu, _bl, pb, _bw = boll(c)
        parts["rsi"][t] = rsi(c)
        parts["pb"][t] = pb
        parts["cci"][t] = cci(h, l, c)
        parts["wr"][t] = willr(h, l, c)
        parts["k"][t] = stoch_k(h, l, c)
    zs = []
    for nm, dd in parts.items():
        M = pd.DataFrame(dd)
        z = M.sub(M.mean(axis=1), axis=0).div(M.std(axis=1).replace(0, np.nan), axis=0)
        zs.append(z.clip(-ZCLIP, ZCLIP))
    S = sum(zs) / len(zs)
    # 5개 중 3개 미만만 살아 있는 칸은 점수를 안 낸다
    ok = sum(z.notna().astype(int) for z in zs) >= 3
    return S.where(ok), {nm: pd.DataFrame(dd) for nm, dd in parts.items()}


def simulate(sel_by_i, R, n, delay=2):
    """sel_by_i[i] = (롱 인덱스, 숏 인덱스) · i 는 판정일(월말).

    🚨 delay=2 가 사전등록의 규칙이다. 판정일 m 의 종가로 점수를 내고 **다음 거래일
       m+1 의 종가로 진입**하므로, 이 책이 처음 먹는 수익은 R[m+2](= 종가 m+1 → m+2)다.
       처음에 delay=1 로 짰었다 — signal_lab.port() 의 관례를 그대로 옮긴 탓인데,
       그것은 판정한 그 종가에 들어가 R[m+1] 을 먹는다. 하루가 통째로 앞선다.
       진동자는 역추세라 판정 다음날 되돌림이 가장 크다 — 그 하루가 공짜로 들어온다.
    """
    wl = ws = None
    sr, lr, shr, traded = [], [], [], []
    for i in range(WARMUP + 1, n):
        tr = 0.0
        if i - delay in sel_by_i:
            nl, ns = sel_by_i[i - delay]
            new_l = np.zeros(R.shape[1]); new_l[nl] = 1.0 / len(nl)
            new_s = np.zeros(R.shape[1]); new_s[ns] = 1.0 / len(ns)
            tr = (np.abs(new_l - (wl if wl is not None else 0)).sum()
                  + np.abs(new_s - (ws if ws is not None else 0)).sum())
            wl, ws = new_l, new_s
        r = R[i]
        rl = float(wl @ r) if wl is not None else 0.0
        rs = float(ws @ r) if ws is not None else 0.0
        if wl is not None:
            wl = wl * (1 + r); wl = wl / wl.sum()
            ws = ws * (1 + r); ws = ws / ws.sum()
        lr.append(rl); shr.append(rs); sr.append(rl - rs); traded.append(tr)
    return np.array(sr), np.array(lr), np.array(shr), np.array(traded)


def main():
    dates, tick, (P, H, L) = load()
    n = len(dates)
    print("종목 %d · %s ~ %s (%d거래일 · 워밍업 %d)" % (len(tick), dates[0], dates[-1], n, WARMUP))

    S, parts = score(P, H, L, tick)
    R = P.pct_change().fillna(0.0).to_numpy()
    bench = P.pct_change().mean(axis=1).fillna(0.0).to_numpy()
    col = {t: j for j, t in enumerate(tick)}

    month_end = [i for i in range(WARMUP, n - 1) if dates[i][:7] != dates[i + 1][:7]]
    Sv = S.to_numpy()
    sel, n_reb = {}, 0
    for i in dict.fromkeys(month_end):
        row = Sv[i]
        good = np.where(~np.isnan(row))[0]
        if len(good) < TOPN * 2:
            continue
        o = good[np.argsort(row[good])]
        sel[i] = (o[:TOPN], o[-TOPN:])          # 최저=과매도=롱 · 최고=과매수=숏
        n_reb += 1
    print("리밸런스 %d회 (%s ~ %s)" % (n_reb, dates[min(sel)], dates[max(sel)]))

    sr, lr, shr, traded = simulate(sel, R, n)
    b = bench[WARMUP + 1:n]
    yrs = len(sr) / 252.0
    # ⚠ traded 는 두 다리의 |Δw| 합이다. 다리 하나(명목 1)의 편도 회전율로 읽으려면 4로 나눈다
    #   (한 다리를 통째로 갈면 |Δw| = 2 이고 그것이 편도 100% 다).
    turn = float(traded.sum()) / 4 / yrs * 100          # 다리당 연 편도 회전율(%)

    m_sp, m_l, m_s, m_b = ann(sr), ann(lr), ann(shr), ann(b)
    t_sp = nw_t(sr)
    ex_l = float(np.mean(lr - b)) * 252 * 100
    ex_s = float(np.mean(shr - b)) * 252 * 100

    print("\n■ 스프레드 (롱 − 숏 · 무비용)")
    print("   연수익 %+.2f%% · 변동성 %.2f%% · 샤프 %s · MDD %.2f%% · NW t %s"
          % (m_sp["cagr"], m_sp["vol"], m_sp["sharpe"], m_sp["mdd"], t_sp))
    print("   다리당 연 편도 회전율 %.0f%%  (월마다 두 다리를 거의 통째로 간다)" % turn)

    # 하루 일찍 들어가면 — 처음에 실수로 짰던 판. 선견의 크기를 수로 남긴다.
    sr1 = simulate(sel, R, n, delay=1)[0]
    m_sp1 = ann(sr1)
    print("   ⚠ 판정 당일 종가 진입(선견 1일)이면 연 %+.2f%% — 차 %+.2f%%p 가 그 하루에서 온다"
          % (m_sp1["cagr"], m_sp1["cagr"] - m_sp["cagr"]))
    print("\n■ 다리별 (유니버스 동일가중 대비)")
    print("   롱(과매도10)  연 %+6.2f%%  초과 %+6.2f%%p  샤프 %s" % (m_l["cagr"], ex_l, m_l["sharpe"]))
    print("   숏(과매수10)  연 %+6.2f%%  초과 %+6.2f%%p  샤프 %s" % (m_s["cagr"], ex_s, m_s["sharpe"]))
    print("   유니버스      연 %+6.2f%%                  샤프 %s" % (m_b["cagr"], m_b["sharpe"]))

    print("\n■ 비용 민감도 (편도 bp)")
    net = {}
    for bps in COST_BPS:
        nr = sr - (bps / 10000.0) * traded
        net[str(bps)] = dict(ann(nr), t=nw_t(nr))
        print("   %2dbp  연 %+6.2f%%  샤프 %-6s  NW t %s"
              % (bps, net[str(bps)]["cagr"], net[str(bps)]["sharpe"], net[str(bps)]["t"]))

    # ── F4 부분표본 ────────────────────────────────────────────────────────
    half = len(sr) // 2
    h1, h2 = ann(sr[:half]), ann(sr[half:])
    dmid = dates[WARMUP + 1 + half]
    nrm = sr - (COST_BPS_MAIN / 10000.0) * traded
    h1n, h2n = ann(nrm[:half]), ann(nrm[half:])
    print("\n■ 부분표본 (분기점 %s)" % dmid)
    print("   무비용   전반 %+.2f%%  ·  후반 %+.2f%%" % (h1["cagr"], h2["cagr"]))
    print("   %dbp 후  전반 %+.2f%%  ·  후반 %+.2f%%   ← F3 은 전구간 평균으로만 본다"
          % (COST_BPS_MAIN, h1n["cagr"], h2n["cagr"]))

    # ── F2 셔플 ────────────────────────────────────────────────────────────
    print("\n■ 셔플 %d회 — 날짜·종목수·회전 구조는 그대로 두고 «누가 과매도인가»만 무작위" % NSHUF)
    rng = np.random.default_rng(SEED)
    keys = sorted(sel)
    pool = {i: np.where(~np.isnan(Sv[i]))[0] for i in keys}
    shuf = np.empty(NSHUF)
    for q in range(NSHUF):
        ss = {}
        for i in keys:
            pick = rng.choice(pool[i], TOPN * 2, replace=False)
            ss[i] = (pick[:TOPN], pick[TOPN:])
        shuf[q] = ann(simulate(ss, R, n)[0])["cagr"]
        if (q + 1) % 50 == 0:
            print("   ... %d회" % (q + 1))
    pct = float((shuf < m_sp["cagr"]).mean()) * 100
    print("   실측 %+.2f%% · 셔플 평균 %+.2f%% · 상위 %.1f%% (백분위 %.1f)"
          % (m_sp["cagr"], shuf.mean(), 100 - pct, pct))

    # ── 판정 ───────────────────────────────────────────────────────────────
    F = {
        "F1 스프레드 연수익 ≤ 0": m_sp["cagr"] <= 0,
        "F2 셔플 상위 5% 밖": pct < 95.0,
        "F3 10bp 후 연수익 ≤ 0": net[str(COST_BPS_MAIN)]["cagr"] <= 0,
        "F4 부분표본 부호 반전": (h1["cagr"] > 0) != (h2["cagr"] > 0),
        "F5 어느 다리도 안 듦": (ex_l <= 0) and (ex_s >= 0),
    }
    print("\n■ 기각 조건")
    for k, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k))
    verdict = "기각" if any(F.values()) else "채택"
    print("\n→ 판정: %s" % verdict)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "prereg": PREREG, "prereg_commit": COMMIT, "as_of": dates[-1],
        "start": dates[WARMUP], "n_days": len(sr), "n_stocks": len(tick),
        "n_rebal": n_reb, "topn": TOPN, "turnover_yr_pct": round(turn, 1),
        "spread": dict(m_sp, t=t_sp), "long": dict(m_l, excess_pp=round(ex_l, 2)),
        "short": dict(m_s, excess_pp=round(ex_s, 2)), "bench": m_b,
        "net": net, "cost_bps_main": COST_BPS_MAIN,
        "half": {"split": dmid, "first": h1, "second": h2,
                 "first_net": h1n, "second_net": h2n},
        "delay1_cagr": m_sp1["cagr"],
        "shuffle": {"n": NSHUF, "seed": SEED, "mean": round(float(shuf.mean()), 3),
                    "p5": round(float(np.percentile(shuf, 5)), 3),
                    "p95": round(float(np.percentile(shuf, 95)), 3),
                    "pctile_of_actual": round(pct, 1)},
        "fails": {k: bool(v) for k, v in F.items()}, "verdict": verdict,
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
