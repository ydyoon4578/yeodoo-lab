# -*- coding: utf-8 -*-
"""build/momtiming_diag.py — 타점 신호를 «무엇을»이 아니라 «언제»로 쓰면. **계측이다.**

앞선 두 판이 같은 말을 했다.
  SWING1020·SWING2 — 진동자로 종목을 고르면 알파가 우연과 구분되지 않는다.
  resrev_diag      — 잔차 역추세로 골라도 없다(십분위 스프레드가 음수).

둘 다 «과매도를 **선별 신호**로 썼다». 그런데 타점 신호가 실제로 쓰이는 자리는
**이미 사기로 한 것을 언제 사느냐**다. 그 용법을 잰다.

  바탕 = 12-1 모멘텀 십분위(52종) — 랩에 이미 게시된 x-mom12-n52 와 같은 신호.
        ⚠ 여기서는 랩 산출물이 아니라 이 패널에서 다시 만든다. 성적을 랩 표와
          견주려는 것이 아니라 «진동자를 얹으면 달라지나»만 보기 때문이다.

재는 것
  ① 바탕 모멘텀이 이 패널에서 살아 있나 (없으면 얹을 자리가 없다)
  ② 모멘텀 십분위 안에서 진동자 점수로 갈랐을 때 이후 수익이 갈리나
  ③ 갈린다면 어느 쪽인가 — 과매도가 좋은가(역추세), 과매수가 좋은가(추세)
  ④ 얹었을 때 회전율이 얼마나 느나

  python build/momtiming_diag.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swing1020 import load, score, WARMUP, nw_t                     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "_momtiming_diag.json")
DEC = 52
SKIP = 21          # 12-1 — 최근 1개월을 건너뛴다(Jegadeesh·Titman 규약)
LOOK = 252


def main():
    dates, tick, (P, H, L) = load()
    n = len(dates)
    S, _ = score(P, H, L, tick)          # 과매수 점수 — 높을수록 과매수
    Sv = S.to_numpy()
    PX = P.to_numpy()
    LP = np.log(np.where(PX > 0, PX, np.nan))
    Rdf = P.pct_change()
    bench = Rdf.mean(axis=1).fillna(0.0).to_numpy()
    month_end = [i for i in range(max(WARMUP, LOOK + 5), n - 1)
                 if dates[i][:7] != dates[i + 1][:7]]
    print("종목 %d · 형성 %d회 · %s ~ %s" % (len(tick), len(month_end),
                                            dates[month_end[0]], dates[month_end[-1]]))

    def fwd21(i):
        return PX[i + 22] / PX[i + 1] - 1 if i + 22 < n else None

    # ── ① 바탕 모멘텀 ──────────────────────────────────────────────────────
    print("\n■ ① 12-1 모멘텀 십분위(%d종) — 이 패널에서 살아 있나" % DEC)
    sp, lo_, sh_, bch = [], [], [], []
    keep_all = []
    prev = None
    for i in month_end:
        f = LP[i - SKIP] - LP[i - LOOK]
        fwd = fwd21(i)
        if fwd is None:
            continue
        m = ~np.isnan(f) & ~np.isnan(fwd)
        if m.sum() < DEC * 2:
            continue
        o = np.where(m)[0][np.argsort(f[m])]
        win, los = o[-DEC:], o[:DEC]
        lo_.append(float(fwd[win].mean())); sh_.append(float(fwd[los].mean()))
        sp.append(lo_[-1] - sh_[-1]); bch.append(float(fwd[m].mean()))
        if prev is not None:
            keep_all.append(len(set(win.tolist()) & prev) / DEC)
        prev = set(win.tolist())
    sp = np.array(sp); h = len(sp) // 2
    print("   승자 %.3f%%/월 · 패자 %.3f%%/월 · 유니버스 %.3f%%/월"
          % (np.mean(lo_) * 100, np.mean(sh_) * 100, np.mean(bch) * 100))
    print("   스프레드 %.3f%%/월 · NW t %s · 전반 %.3f%% · 후반 %.3f%% · 잔류율 %.1f%%"
          % (sp.mean() * 100, nw_t(sp, lag=3), sp[:h].mean() * 100, sp[h:].mean() * 100,
             np.mean(keep_all) * 100))
    base_ok = sp.mean() > 0
    print("   → %s" % ("바탕이 있다. ②로 간다." if base_ok
                       else "🚨 바탕 자체가 없다 — 얹을 자리가 없다."))

    # ── ②③ 모멘텀 승자 안에서 진동자로 가르기 ─────────────────────────────
    print("\n■ ② 모멘텀 승자 십분위 %d종을 진동자 점수로 반 가르기" % DEC)
    print("   (승자는 대개 과매수다 — 그중 «덜 과매수인 쪽»이 좋은지 본다)")
    rows = {}
    for tagname, side in (("승자(롱)", "win"), ("패자(숏)", "los")):
        A, Bc, univ = [], [], []
        for i in month_end:
            f = LP[i - SKIP] - LP[i - LOOK]
            fwd = fwd21(i)
            if fwd is None:
                continue
            m = ~np.isnan(f) & ~np.isnan(fwd) & ~np.isnan(Sv[i])
            if m.sum() < DEC * 2:
                continue
            o = np.where(m)[0][np.argsort(f[m])]
            grp = o[-DEC:] if side == "win" else o[:DEC]
            s = Sv[i][grp]
            k = np.argsort(s)
            half = len(grp) // 2
            A.append(float(fwd[grp[k[:half]]].mean()))       # 덜 과매수(과매도 쪽)
            Bc.append(float(fwd[grp[k[half:]]].mean()))      # 더 과매수
            univ.append(float(fwd[m].mean()))
        A, Bc = np.array(A), np.array(Bc)
        d = A - Bc
        hh = len(d) // 2
        rows[side] = {"low": float(A.mean()) * 100, "high": float(Bc.mean()) * 100,
                      "diff": float(d.mean()) * 100, "t": nw_t(d, lag=3),
                      "first": float(d[:hh].mean()) * 100, "second": float(d[hh:].mean()) * 100}
        r = rows[side]
        print("   %-9s 과매도쪽 %.3f%%  과매수쪽 %.3f%%  차 %+.3f%%  t %-5s  전 %+.3f / 후 %+.3f"
              % (tagname, r["low"], r["high"], r["diff"], r["t"], r["first"], r["second"]))
    print("   → 승자에서 차가 + 면 «오른 종목 중 덜 과매수인 것을 사라»가 성립한다.")

    # ── ④ 결합 규칙의 회전율 ───────────────────────────────────────────────
    print("\n■ ③ 결합 — 모멘텀 승자 %d 중 진동자 하위 %d (덜 과매수) 롱" % (DEC, DEC // 2))
    hold, keep2, rets, brets = None, [], [], []
    for i in month_end:
        f = LP[i - SKIP] - LP[i - LOOK]
        fwd = fwd21(i)
        if fwd is None:
            continue
        m = ~np.isnan(f) & ~np.isnan(fwd) & ~np.isnan(Sv[i])
        if m.sum() < DEC * 2:
            continue
        o = np.where(m)[0][np.argsort(f[m])]
        win = o[-DEC:]
        pick = win[np.argsort(Sv[i][win])[:DEC // 2]]
        if hold is not None:
            keep2.append(len(set(pick.tolist()) & hold) / len(pick))
        hold = set(pick.tolist())
        rets.append(float(fwd[pick].mean())); brets.append(float(fwd[m].mean()))
    rets, brets = np.array(rets), np.array(brets)
    ex = rets - brets
    hh = len(ex) // 2
    print("   월 %.3f%% · 유니버스 %.3f%% · 초과 %+.3f%%/월 (연 %+.2f%%p) · NW t %s"
          % (rets.mean() * 100, brets.mean() * 100, ex.mean() * 100, ex.mean() * 1200,
             nw_t(ex, lag=3)))
    print("   전반 %+.3f%% · 후반 %+.3f%% · 잔류율 %.1f%% (월 편도 회전 약 %.0f%%/년)"
          % (ex[:hh].mean() * 100, ex[hh:].mean() * 100, np.mean(keep2) * 100,
             (1 - np.mean(keep2)) * 12 * 100))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps({
        "mom_base": {"spread_pm": float(sp.mean()) * 100, "t": nw_t(sp, lag=3),
                     "first": float(sp[:h].mean()) * 100, "second": float(sp[h:].mean()) * 100,
                     "keep": float(np.mean(keep_all)) * 100},
        "split": rows,
        "combo": {"excess_pm": float(ex.mean()) * 100, "t": nw_t(ex, lag=3),
                  "first": float(ex[:hh].mean()) * 100, "second": float(ex[hh:].mean()) * 100,
                  "keep": float(np.mean(keep2)) * 100},
        "note": "계측 전용", "dec": DEC}, ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
