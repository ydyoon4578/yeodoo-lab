# -*- coding: utf-8 -*-
"""build/swing_diag.py — SWING1020 이 왜 죽었나. **계측이지 전략이 아니다.**

SWING1020 은 F2·F3·F4 로 기각됐다. 죽인 것으로 지목된 두 가지를 수로 확인한다.
  ① 회전율   — 신호의 반감기가 한 달보다 길면 분기 리밸런스가 산다.
  ② 후반 소멸 — 2018 이후가 정말 0 인가, 구간을 반으로 가른 탓인가.
그리고 셋째를 함께 본다.
  ③ 폭(breadth) — 10종목은 518 중 2%다. 십분위(약 52종목)로 넓히면 남는가.

🚨 여기서 나오는 수치로 전략을 고르지 않는다. 다음 사전등록의 «무엇을 걸 것인가»를
   정하는 데만 쓴다. 고른 것은 사전등록 문서에 적고, 그 문서를 커밋한 뒤에 돌린다.

  python build/swing_diag.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swing1020 import load, score, WARMUP, nw_t                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "_swing_diag.json")
HOR = (1, 2, 3, 5, 10, 21, 42, 63)


def rank_ic(sv, fwd, mask):
    """횡단면 순위상관. sv 는 과매수 점수 → 부호를 뒤집어 «과매도일수록 +» 로 본다."""
    a, b = sv[mask], fwd[mask]
    if len(a) < 30:
        return np.nan
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float(-(ra @ rb) / d) if d > 0 else np.nan


def main():
    dates, tick, (P, H, L) = load()
    n = len(dates)
    S, _ = score(P, H, L, tick)
    Sv = S.to_numpy()
    PX = P.to_numpy()
    month_end = [i for i in range(WARMUP, n - 1) if dates[i][:7] != dates[i + 1][:7]]
    print("종목 %d · 형성 %d회 · %s ~ %s\n" % (len(tick), len(month_end),
                                             dates[month_end[0]], dates[month_end[-1]]))

    # ── ① 신호 반감기 — 지평선별 순위 IC ──────────────────────────────────
    # 진입은 m+1 종가. 지평선 h 수익 = 종가(m+1) → 종가(m+1+h).
    print("■ ① 신호 반감기 — 형성월 점수 vs 이후 수익의 순위 IC (월 표본)")
    print("   %-6s %8s %8s %8s %8s   %s" % ("지평선", "평균IC", "t", "전반", "후반", ""))
    ic_all, ic_tbl = {}, {}
    half = len(month_end) // 2
    for h in HOR:
        ser = []
        for k, i in enumerate(month_end):
            if i + 1 + h >= n:
                ser.append(np.nan); continue
            fwd = PX[i + 1 + h] / PX[i + 1] - 1
            m = ~np.isnan(Sv[i]) & ~np.isnan(fwd)
            ser.append(rank_ic(Sv[i], fwd, m))
        ser = np.array(ser, float)
        v = ser[~np.isnan(ser)]
        t = nw_t(v, lag=3)
        f, s = np.nanmean(ser[:half]), np.nanmean(ser[half:])
        ic_all[h] = ser.tolist()
        ic_tbl[h] = {"mean": round(float(np.nanmean(ser)), 4), "t": t,
                     "first": round(float(f), 4), "second": round(float(s), 4)}
        bar = "█" * max(0, int(round(np.nanmean(ser) * 400)))
        print("   %-6s %8.4f %8s %8.4f %8.4f   %s" % ("%d일" % h, np.nanmean(ser), t, f, s, bar))
    print("   → IC 가 지평선이 길어져도 안 줄면 분기 리밸런스가 산다. 1~5일에만 있으면 죽는다.")

    # ── ② 후반 소멸 — 롤링 3년 ─────────────────────────────────────────────
    print("\n■ ② 21일 IC 의 롤링 3년 평균 (36개월 창)")
    s21 = pd.Series(ic_all[21], index=[dates[i][:7] for i in month_end])
    roll = s21.rolling(36, min_periods=24).mean()
    shown = [x for x in roll.dropna().index if x[5:7] in ("06", "12")]
    for ym in shown:
        v = roll[ym]
        if isinstance(v, pd.Series):
            v = float(v.iloc[0])
        b = int(round(abs(v) * 500))
        print("   %s %+7.4f %s%s" % (ym, v, " " * (12 - min(12, b)) if v < 0 else " " * 12,
                                     ("◄" * b) if v < 0 else ("█" * b)))
    print("   → 왼쪽(◄)이 음수. 0 근처를 오가면 구간 문제, 계속 음수면 소멸이다.")

    # ── ③ 폭 — 분위 수별 스프레드 ─────────────────────────────────────────
    print("\n■ ③ 폭 — 상·하위 N종목 스프레드의 21일 수익 (월 표본 평균 %p · 무비용)")
    print("   %-8s %9s %9s %9s %8s %8s" % ("N", "롱", "숏", "스프레드", "t", "후반"))
    br = {}
    for N in (10, 20, 30, 52, 104):
        sp, lo_, sh_ = [], [], []
        for i in month_end:
            if i + 22 >= n:
                continue
            fwd = PX[i + 22] / PX[i + 1] - 1
            m = ~np.isnan(Sv[i]) & ~np.isnan(fwd)
            if m.sum() < N * 2:
                continue
            o = np.where(m)[0][np.argsort(Sv[i][m])]
            a, b = float(fwd[o[:N]].mean()), float(fwd[o[-N:]].mean())
            lo_.append(a); sh_.append(b); sp.append(a - b)
        sp = np.array(sp)
        hf = len(sp) // 2
        br[N] = {"long": round(float(np.mean(lo_)) * 100, 3),
                 "short": round(float(np.mean(sh_)) * 100, 3),
                 "spread": round(float(sp.mean()) * 100, 3), "t": nw_t(sp, lag=3),
                 "second": round(float(sp[hf:].mean()) * 100, 3), "n": len(sp)}
        print("   %-8s %8.3f%% %8.3f%% %8.3f%% %8s %7.3f%%"
              % ("%d종목" % N, br[N]["long"], br[N]["short"], br[N]["spread"],
                 br[N]["t"], br[N]["second"]))
    print("   → 넓힐수록 스프레드는 줄지만 t 가 오르면 «10종목이 너무 좁았다»는 뜻이다.")

    # ── ④ 헛회전 — 순위의 달간 지속성 ──────────────────────────────────────
    print("\n■ ④ 순위 지속성 — 이번 달 상위 N 이 다음 달에도 상위 N 에 남는 비율")
    for N in (10, 30, 52):
        keep = []
        for a, b in zip(month_end[:-1], month_end[1:]):
            for sgn in (1, -1):
                ma = ~np.isnan(Sv[a]); mb = ~np.isnan(Sv[b])
                if ma.sum() < N or mb.sum() < N:
                    continue
                oa = np.where(ma)[0][np.argsort(sgn * Sv[a][ma])][:N]
                ob = set(np.where(mb)[0][np.argsort(sgn * Sv[b][mb])][:N].tolist())
                keep.append(len(set(oa.tolist()) & ob) / N)
        print("   %-8s %5.1f%%  (무작위면 %.1f%%)" % ("%d종목" % N, np.mean(keep) * 100,
                                                    N / len(tick) * 100))
    print("   → 잔류율이 낮을수록 매달 통째로 갈아타는 것이고, 그것이 회전율 1172%%의 정체다.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"ic": ic_tbl, "breadth": br, "note": "계측 전용 — 전략 선택 근거가 아니다"},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
