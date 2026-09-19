# -*- coding: utf-8 -*-
"""build/swing_beta.py — SWING1020 스프레드에 순베타가 남아 있나. **계측이다.**

시장중립이라 부른 책의 MDD 가 −47% 였다. 1:1 달러중립은 **달러**중립이지
**위험**중립이 아니다. 과매도 쪽이 고베타로 몰리면 스프레드가 통째로 시장 베팅이 된다.

  python build/swing_beta.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swing1020 import load, score, simulate, WARMUP, TOPN, ann, nw_t     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "_swing_beta.json")
BETA_WIN = 120


def main():
    dates, tick, (P, H, L) = load()
    n = len(dates)
    S, _ = score(P, H, L, tick)
    Sv = S.to_numpy()
    R = P.pct_change().fillna(0.0)
    bench = R.mean(axis=1)
    Rn = R.to_numpy()
    bn = bench.to_numpy()

    # 그 시점까지의 120일 롤링 β (선견 없음)
    bvar = bench.rolling(BETA_WIN, min_periods=60).var()
    B = R.rolling(BETA_WIN, min_periods=60).cov(bench).div(bvar, axis=0).clip(0, 3).to_numpy()

    month_end = [i for i in range(WARMUP, n - 1) if dates[i][:7] != dates[i + 1][:7]]
    sel, bl, bs = {}, [], []
    for i in month_end:
        row = Sv[i]
        good = np.where(~np.isnan(row))[0]
        if len(good) < TOPN * 2:
            continue
        o = good[np.argsort(row[good])]
        sel[i] = (o[:TOPN], o[-TOPN:])
        bl.append(np.nanmean(B[i][o[:TOPN]]))
        bs.append(np.nanmean(B[i][o[-TOPN:]]))

    print("■ 형성 시점의 사전 β (그 시점까지 120일)")
    print("   롱(과매도10) %.3f  ·  숏(과매수10) %.3f  ·  차 %+.3f"
          % (np.nanmean(bl), np.nanmean(bs), np.nanmean(bl) - np.nanmean(bs)))
    print("   → 차가 0 이 아니면 1:1 달러중립 스프레드에 그만큼 시장이 남는다.")

    sr, lr, shr, traded = simulate(sel, R.to_numpy(), n, delay=2)
    b = bn[WARMUP + 1:n]

    # 실현 β — 스프레드를 유니버스에 회귀
    def reg(y, x):
        x = np.asarray(x, float); y = np.asarray(y, float)
        xm, ym = x.mean(), y.mean()
        be = float(((x - xm) @ (y - ym)) / ((x - xm) @ (x - xm)))
        al = ym - be * xm
        return be, al * 252 * 100

    be_sp, al_sp = reg(sr, b)
    be_l, al_l = reg(lr, b)
    be_s, al_s = reg(shr, b)
    print("\n■ 실현 β 와 연 알파 (유니버스 동일가중 기준)")
    print("   %-14s %8s %10s" % ("", "β", "α(연%)"))
    print("   %-14s %8.3f %9.2f%%" % ("롱", be_l, al_l))
    print("   %-14s %8.3f %9.2f%%" % ("숏", be_s, al_s))
    print("   %-14s %8.3f %9.2f%%" % ("스프레드", be_sp, al_sp))

    m_raw = ann(sr)
    print("\n   스프레드 원 수익 연 %+.2f%% = 시장 몫 %+.2f%% + 알파 %+.2f%%"
          % (m_raw["cagr"], be_sp * float(np.mean(b)) * 252 * 100, al_sp))

    # β중립 스프레드 — 숏 다리를 β비율로 키운다
    k = be_l / be_s if be_s else 1.0
    srn = lr - k * shr
    m_n = ann(srn)
    be_n, al_n = reg(srn, b)
    print("\n■ β중립판 (숏 다리를 %.3f배로 — 롱 β / 숏 β)" % k)
    print("   연 %+.2f%% · 변동성 %.2f%% · 샤프 %s · MDD %.2f%% · NW t %s · 잔존 β %.3f"
          % (m_n["cagr"], m_n["vol"], m_n["sharpe"], m_n["mdd"], nw_t(srn), be_n))

    half = len(srn) // 2
    print("   전반 %+.2f%%  ·  후반 %+.2f%%"
          % (ann(srn[:half])["cagr"], ann(srn[half:])["cagr"]))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "beta_form": {"long": float(np.nanmean(bl)), "short": float(np.nanmean(bs))},
        "realized": {"long": [be_l, al_l], "short": [be_s, al_s], "spread": [be_sp, al_sp]},
        "neutral": dict(m_n, k=k, resid_beta=be_n, t=nw_t(srn)),
        "note": "계측 전용",
    }, ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
