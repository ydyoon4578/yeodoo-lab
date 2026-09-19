# -*- coding: utf-8 -*-
"""build/resrev_diag.py — 단기 «잔차» 역추세가 있나. **계측이지 전략이 아니다.**

진동자 계열은 SWING1020·SWING2 로 닫혔다. 재료를 바꾼다.

  과매도를 «진동자가 낮다»가 아니라 «최근 수익이 나빴다»로 정의하되,
  그 수익에서 **시장(β)과 산업**을 걷어낸 나머지만 본다.
  Da·Liu·Schaumburg(2014, RFS) — 날것 단기 역추세는 유동성 보상이라 못 쓰지만
  잔차 역추세는 다르다. 이 랩은 산업잔차 «모멘텀»(x-residind-n52)만 쟀고
  단기 «역추세» 쪽은 안 쟀다.

재는 것
  ① 날것 / β잔차 / 산업잔차 / 둘다 — 어느 것이 예측력이 있나
  ② 형성창 5·10·21·63일 × 보유 5·10·21·63일
  ③ 전반·후반으로 갈라 소멸했는지
  ④ 십분위(52종) 스프레드와 회전율 — 비용을 넘을 수 있나

🚨 여기 수치로 전략을 고르되, 고른 것은 사전등록에 적고 커밋한 뒤에 돌린다.

  python build/resrev_diag.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swing1020 import load, WARMUP, nw_t                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_resrev_diag.json")
BETA_WIN = 120
DEC = 52                      # 십분위 — 518 ÷ 10 (랩 규약 · RESIDIND2 선례)


def sectors(tick):
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    sm = {s["t"]: (s.get("sector") or "?") for s in st["stocks"]}
    lab = sorted({sm.get(t, "?") for t in tick})
    code = {s: j for j, s in enumerate(lab)}
    return np.array([code[sm.get(t, "?")] for t in tick]), lab


def rank_ic(a, b):
    m = ~np.isnan(a) & ~np.isnan(b)
    if m.sum() < 30:
        return np.nan
    ra = pd.Series(a[m]).rank().to_numpy(); rb = pd.Series(b[m]).rank().to_numpy()
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra @ rb) / d) if d > 0 else np.nan


def main():
    dates, tick, (P, H, L) = load()
    n = len(dates)
    sec, slab = sectors(tick)
    print("종목 %d · 섹터 %d종 · %s ~ %s" % (len(tick), len(slab), dates[0], dates[-1]))

    Rdf = P.pct_change()
    bench = Rdf.mean(axis=1)
    bvar = bench.rolling(BETA_WIN, min_periods=60).var()
    BETA = Rdf.rolling(BETA_WIN, min_periods=60).cov(bench).div(bvar, axis=0).clip(0, 3)
    R = Rdf.fillna(0.0).to_numpy()
    BE = BETA.to_numpy()
    bm = bench.fillna(0.0).to_numpy()
    PX = P.to_numpy()
    LP = np.log(np.where(PX > 0, PX, np.nan))
    month_end = [i for i in range(WARMUP, n - 1) if dates[i][:7] != dates[i + 1][:7]]

    def formation(i, w, kind):
        """i 시점까지 w일 수익(로그). kind 에 따라 시장·산업을 걷어낸다."""
        raw = LP[i] - LP[i - w]
        if kind in ("raw",):
            v = raw.copy()
        else:
            v = raw.copy()
            if "b" in kind:                       # 시장 몫 제거
                v = v - BE[i] * float(np.nansum(bm[i - w + 1:i + 1]))
            if "s" in kind:                       # 산업 평균 제거
                out = v.copy()
                for s in range(len(slab)):
                    m = (sec == s) & ~np.isnan(v)
                    if m.sum() >= 5:
                        out[m] = v[m] - v[m].mean()
                v = out
        return v

    KINDS = [("raw", "날것"), ("b", "β잔차"), ("s", "산업잔차"), ("bs", "β+산업잔차")]
    HOLD = (5, 10, 21, 63)
    FORM = (5, 10, 21, 63)

    print("\n■ ① 역추세 IC — 형성창 × 보유창 (부호를 뒤집어 «많이 빠진 것이 오른다»가 +)")
    ic = {}
    for kd, knm in KINDS:
        print("\n   [%s]" % knm)
        print("      %-8s %s" % ("형성\\보유", "".join("%12s" % ("%d일" % h) for h in HOLD)))
        for w in FORM:
            cells = []
            for h in HOLD:
                ser = []
                for i in month_end:
                    if i - w < WARMUP - 60 or i + 1 + h >= n:
                        continue
                    f = formation(i, w, kd)
                    fwd = PX[i + 1 + h] / PX[i + 1] - 1
                    ser.append(-rank_ic(f, fwd))         # 역추세 = 음의 상관이 +
                ser = np.array([x for x in ser if x == x])
                t = nw_t(ser, lag=3)
                ic["%s|%d|%d" % (kd, w, h)] = {"mean": float(ser.mean()), "t": t,
                                               "first": float(ser[:len(ser) // 2].mean()),
                                               "second": float(ser[len(ser) // 2:].mean())}
                cells.append("%7.4f/%-4s" % (ser.mean(), t))
            print("      %-8s %s" % ("%d일" % w, "".join("%12s" % c for c in cells)))
    print("\n   칸은 «평균IC / NW t». 양수면 역추세 방향(많이 빠진 것이 이후 오른다).")

    # ── ③·④ 십분위 스프레드 ──────────────────────────────────────────────
    print("\n■ ② 십분위(%d종) 롱숏 — 형성 21일 · 보유 21일 · 월 표본" % DEC)
    print("   %-12s %9s %9s %8s %9s %9s %8s"
          % ("재료", "스프레드", "t", "후반", "롱", "숏", "잔류율"))
    dec = {}
    for kd, knm in KINDS:
        sp, lo_, sh_, keep, prev = [], [], [], [], None
        for i in month_end:
            if i + 22 >= n:
                continue
            f = formation(i, 21, kd)
            fwd = PX[i + 22] / PX[i + 1] - 1
            m = ~np.isnan(f) & ~np.isnan(fwd)
            if m.sum() < DEC * 2:
                continue
            o = np.where(m)[0][np.argsort(f[m])]
            lg, st_ = o[:DEC], o[-DEC:]          # 많이 빠진 것 롱 · 많이 오른 것 숏
            a, b = float(fwd[lg].mean()), float(fwd[st_].mean())
            lo_.append(a); sh_.append(b); sp.append(a - b)
            if prev is not None:
                keep.append(len(set(lg.tolist()) & prev) / DEC)
            prev = set(lg.tolist())
        sp = np.array(sp); hf = len(sp) // 2
        dec[kd] = {"spread": float(sp.mean()) * 100, "t": nw_t(sp, lag=3),
                   "second": float(sp[hf:].mean()) * 100,
                   "long": float(np.mean(lo_)) * 100, "short": float(np.mean(sh_)) * 100,
                   "keep": float(np.mean(keep)) * 100, "n": len(sp)}
        d = dec[kd]
        print("   %-12s %8.3f%% %9s %7.3f%% %8.3f%% %8.3f%% %7.1f%%"
              % (knm, d["spread"], d["t"], d["second"], d["long"], d["short"], d["keep"]))
    print("   잔류율 = 이번 달 롱 십분위가 다음 달에도 롱 십분위인 비율(무작위면 10.0%).")
    print("   → 잔류율이 높을수록 회전이 낮다. 진동자판은 상위10 잔류 2.4%(무작위 1.9)였다.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"ic": ic, "decile": dec, "dec_n": DEC, "note": "계측 전용"},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
