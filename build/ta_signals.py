# -*- coding: utf-8 -*-
"""build/ta_signals.py — 교과서 TA 신호 검증(매수·매도) → data/_ta_signals.json

설계 출처는 사용자 제공 사내 `ta_lab`(backtest_signals.py · indicators.py)이다.
**산식과 발동 조건만** 가져왔다 — 사내 DB·경로·티커 화이트리스트는 안 옮긴다.
자료는 이 랩의 `data/bench_px.json`(S&P 500 PR · NASDAQ 100 PR 종가)만 쓴다.

무엇을. 10년 구간에서 신호마다
  · 처음 켜진 날(이벤트) 종가 진입 → 달력 +7일 / +30일 사후수익
  · 무조건부 기준선 대비 초과
  · **최근 발동일과 경과일**  ← 원본 CSV 에 없던 것. 사용자 요청 2026-09-22.
  · 지금 켜져 있나
매수·매도 양쪽을 다 낸다.

🚨 **종가만 쓴다.** 이 랩의 지수 계열에는 고가·저가·거래량이 없다(bench_px 는 종가 5,210일).
   그래서 원본 37종 중 **고가·저가·거래량이 필요한 것은 뺐다.** 지어 채우지 않는다 —
   Stoch·CCI·Williams%R·UltimateOsc·Keltner·MFI·MassIndex·PSAR·SuperTrend·Donchian·
   Aroon·일목·ADX·RWI·VWAP·NVI·PVI·RVI·ElderRay·ForceIndex·ChaikinOsc·OBV·EOM.
   ⚠ 종가로 비슷하게 흉내 낸 변종을 같은 이름으로 싣지 않는다. 이름이 같으면 같은 것이어야 한다.

⚠ 이 파일은 **새 주장을 만들지 않는다.** 원본이 이미 낸 결론(매도 신호는 숏이 아니다 ·
  단일 지표 의존 금지)을 이 랩 자료로 다시 재는 것이고, 판정은 원본과 같은 어휘로 적는다.

  python build/ta_signals.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_ta_signals.json")

YEARS = 10
MIN_N = 5          # 원본과 같은 문턱 — 이보다 적으면 통계를 안 낸다

# ── 지표 — ta_lab/indicators.py 에서 **그대로** 옮긴다 ──────────────────────
ema = lambda c, n: c.ewm(span=n, adjust=False).mean()
sma = lambda c, n: c.rolling(n).mean()
roc = lambda c, n: c.pct_change(n) * 100


def tema(c, n=20):
    e1 = ema(c, n); e2 = ema(e1, n); e3 = ema(e2, n)
    return 3 * e1 - 3 * e2 + e3


def macd(c, fast=12, slow=26, sig=9):
    line = ema(c, fast) - ema(c, slow)
    return pd.DataFrame({"macd": line, "signal": ema(line, sig)})


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def stoch_rsi(c, n=14, k=14):
    r = rsi(c, n)
    lo, hi = r.rolling(k).min(), r.rolling(k).max()
    return (r - lo) / (hi - lo)


def cmo(c, n=14):
    d = c.diff()
    su = d.clip(lower=0).rolling(n).sum()
    sd = (-d.clip(upper=0)).rolling(n).sum()
    return (su - sd) / (su + sd) * 100


def psy(c, n=12):
    return (c.diff() > 0).rolling(n).mean() * 100


def bollinger(c, n=20, k=2.0):
    mid, sd = sma(c, n), c.rolling(n).std()
    up, lo = mid + k * sd, mid - k * sd
    return pd.DataFrame({"up": up, "lo": lo, "pb": (c - lo) / (up - lo),
                         "bw": (up - lo) / mid})


def disparity(c, n=20):
    return c / sma(c, n) * 100


def trix(c, n=15, sig=9):
    e = ema(ema(ema(c, n), n), n)
    t = e.pct_change() * 100
    return pd.DataFrame({"trix": t, "signal": ema(t, sig)})


def sroc(c, n=12, m=13):
    return roc(ema(c, m), n)


def td_setup(c):
    """Demark TD Setup — 4봉 전 종가 대비 연속 카운트(+매수셋업 / −매도셋업)."""
    diff = (c - c.shift(4)).to_numpy()
    cnt = np.zeros(len(c))
    for i in range(4, len(c)):
        if diff[i] < 0:
            cnt[i] = cnt[i - 1] + 1 if cnt[i - 1] > 0 else 1
        elif diff[i] > 0:
            cnt[i] = cnt[i - 1] - 1 if cnt[i - 1] < 0 else -1
    return pd.Series(cnt, index=c.index)


# 종가로는 못 내는 것 — 지어 채우지 않는다. 화면에 그대로 적는다.
DROPPED = ["Stoch %K", "CCI", "Williams%R", "UltimateOsc", "Keltner", "MFI", "MassIndex",
           "PSAR", "SuperTrend", "Donchian", "Aroon", "일목 구름", "ADX", "RWI", "VWAP",
           "NVI", "PVI", "RVI", "ElderRay", "ForceIndex", "ChaikinOsc", "OBV", "EOM"]

CONF_TOP = ["RSI14<30", "TEMA20>SMA50 교차", "TD BuySetup9", "BB %b<0", "MACD 0선 상향"]


def build_signals(c):
    """반환: ({이름: 불리언}, {이름: 불리언}) = (매수, 매도). 조건은 원본 그대로."""
    bb, m, tx = bollinger(c), macd(c), trix(c)
    td, dsp, sr = td_setup(c), disparity(c), sroc(c)
    bw_low = bb["bw"].rolling(126).min()
    z = pd.Series(0.0, index=c.index)
    up = lambda a, b: (a > b) & (a.shift(1) <= b.shift(1))
    dn = lambda a, b: (a < b) & (a.shift(1) >= b.shift(1))
    buy = {
        "RSI14<30": rsi(c) < 30,
        "StochRSI<0.2": stoch_rsi(c) < 0.2,
        "CMO<-50": cmo(c) < -50,
        "PSY<25": psy(c) < 25,
        "BB %b<0": bb["pb"] < 0,
        "이격도<95": dsp < 95,
        "TD BuySetup9": td >= 9,
        "골든크로스 50/200": up(sma(c, 50), sma(c, 200)),
        "TEMA20>SMA50 교차": up(tema(c, 20), sma(c, 50)),
        "MACD 골든(0선 아래)": up(m["macd"], m["signal"]) & (m["macd"] < 0),
        "MACD 0선 상향": up(m["macd"], z),
        "TRIX 0선 상향": up(tx["trix"], z),
        "S-ROC 0선 상향": up(sr, z),
        "BB 스퀴즈 후 상단 돌파": (bb["bw"].shift(1) <= bw_low.shift(1) * 1.1) & (c > bb["up"]),
    }
    sell = {
        "RSI14>70": rsi(c) > 70,
        "StochRSI>0.8": stoch_rsi(c) > 0.8,
        "CMO>+50": cmo(c) > 50,
        "PSY>75": psy(c) > 75,
        "BB %b>1": bb["pb"] > 1,
        "이격도>105": dsp > 105,
        "TD SellSetup9": td <= -9,
        "데드크로스 50/200": dn(sma(c, 50), sma(c, 200)),
        "TEMA20<SMA50 교차": dn(tema(c, 20), sma(c, 50)),
        "MACD 데드(0선 위)": dn(m["macd"], m["signal"]) & (m["macd"] > 0),
        "MACD 0선 하향": dn(m["macd"], z),
        "TRIX 0선 하향": dn(tx["trix"], z),
        "S-ROC 0선 하향": dn(sr, z),
    }
    return buy, sell


def fwd_returns(c):
    """달력 +7일 / +30일 — 원본과 같다(목표일 이하 마지막 거래일로 스냅)."""
    out = {}
    for lab, days in (("1w", 7), ("1m", 30)):
        tgt = c.index + pd.Timedelta(days=days)
        pos = c.index.searchsorted(tgt, side="right") - 1
        valid = tgt <= c.index[-1]
        f = np.full(len(c), np.nan)
        f[valid] = c.to_numpy()[pos[valid]] / c.to_numpy()[valid] - 1
        out[lab] = pd.Series(f, index=c.index)
    return out


def _stat(mask, fwd, base1m, sell=False):
    n = int(mask.sum())
    r = {"n": n}
    if n < MIN_N:
        return r
    r1w, r1m = fwd["1w"][mask].dropna(), fwd["1m"][mask].dropna()
    r.update({"fwd1w_mean": round(float(r1w.mean()) * 100, 2),
              "fwd1w_win": round(float((r1w > 0).mean()) * 100, 0),
              "fwd1m_mean": round(float(r1m.mean()) * 100, 2),
              "fwd1m_win": round(float((r1m > 0).mean()) * 100, 0)})
    if sell:
        # 🚨 매도 신호는 «내렸나» 로 본다. 원본이 그렇게 잰다 — 숏 진입 신호가 아니라
        #   차익실현 신호라서, 「기준선보다 덜 올랐나」가 묻는 것이다.
        r["fwd1m_down"] = round(float((r1m < 0).mean()) * 100, 0)
        r["edge_vs_base"] = round((base1m - float(r1m.mean())) * 100, 2)
    else:
        r["fwd1m_excess"] = round((float(r1m.mean()) - base1m) * 100, 2)
    return r


def main() -> int:
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    idx = pd.to_datetime(B["dates"])
    asof = B["dates"][-1]
    start = idx[-1] - pd.DateOffset(years=YEARS)

    out = {"note": "교과서 TA 신호 검증. 설계 출처는 사용자 제공 사내 ta_lab "
                   "(backtest_signals.py · indicators.py) — **산식과 발동 조건만** 가져왔고 "
                   "자료는 이 랩의 bench_px.json(종가)만 쓴다.",
           "as_of": asof, "years": YEARS, "basis": B.get("basis"),
           "dropped": DROPPED,
           "dropped_note": "이 랩의 지수 계열에는 고가·저가·거래량이 없다(종가만). "
                           "원본 37종 중 그것이 필요한 %d종을 **뺐다** — 종가로 흉내 낸 "
                           "변종을 같은 이름으로 싣지 않는다." % len(DROPPED),
           "index": {}}

    for key, lab in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        c_all = pd.Series(B["series"][key]["px"], index=idx).dropna()
        c = c_all[c_all.index >= start]
        fwd = fwd_returns(c)
        base1m = float(np.nanmean(fwd["1m"]))
        buy, sell = build_signals(c_all)          # 지표는 전 구간으로 계산(워밍업 확보)
        rec = {"label": B["series"][key]["label"], "ticker": B["series"][key]["ticker"],
               "n_days": len(c), "start": str(c.index[0].date()),
               "base1m": round(base1m * 100, 2), "buy": [], "sell": []}
        ev_cache = {}
        for side, dct, is_sell in (("buy", buy, False), ("sell", sell, True)):
            for nm, cond in dct.items():
                cond = cond.reindex(c.index).fillna(False).astype(bool)
                ev = cond & ~cond.shift(1, fill_value=False)
                ev_cache[nm] = ev
                r = {"signal": nm, **_stat(ev, fwd, base1m, sell=is_sell)}
                # ── 최근 발동일 · 경과일 · 지금 켜져 있나 (사용자 요청) ──
                fired = c.index[ev]
                r["last"] = str(fired[-1].date()) if len(fired) else None
                r["days_ago"] = int((c.index[-1] - fired[-1]).days) if len(fired) else None
                r["on_now"] = bool(cond.iloc[-1])
                r["last3"] = [str(x.date()) for x in fired[-3:]][::-1]
                rec[side].append(r)
        # ── 컨버전스 — 상위 다섯이 전부 종가 전용이라 원본 표를 그대로 낼 수 있다 ──
        conf = []
        for i in range(len(CONF_TOP)):
            for j in range(i + 1, len(CONF_TOP)):
                a, b = CONF_TOP[i], CONF_TOP[j]
                ea, eb = ev_cache[a], ev_cache[b]
                w = 5
                both = ea & (eb.rolling(w, min_periods=1).max().astype(bool))
                both |= eb & (ea.rolling(w, min_periods=1).max().astype(bool))
                both = both & ~both.shift(1, fill_value=False)
                st = _stat(both, fwd, base1m)
                fired = c.index[both]
                conf.append({"pair": "%s ∧ %s" % (a, b), **st,
                             "last": str(fired[-1].date()) if len(fired) else None})
        rec["confluence"] = conf
        out["index"][key] = rec

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    # ── 화면 ──────────────────────────────────────────────────────────
    for key in ("spx", "ndx"):
        r = out["index"][key]
        print("\n" + "═" * 96)
        print("%s (%s) · %s ~ %s · %d거래일 · 기준선 1개월 %+.2f%%"
              % (r["label"], r["ticker"], r["start"], asof, r["n_days"], r["base1m"]))
        print("═" * 96)
        for side, ko in (("buy", "매수"), ("sell", "매도")):
            rows = [x for x in r[side] if x.get("n", 0) >= MIN_N]
            keyf = (lambda x: -(x.get("fwd1m_excess") or -99)) if side == "buy" \
                else (lambda x: -(x.get("edge_vs_base") or -99))
            rows.sort(key=keyf)
            print("\n  ── %s 신호 %d종 ── (%s 순)"
                  % (ko, len(rows), "초과수익" if side == "buy" else "기준선 대비 덜 오름"))
            head = ("  %-22s %4s %8s %7s %8s %7s %8s  %-11s %6s %s"
                    % ("신호", "횟수", "1주", "1주승", "1개월", "1개월승",
                       "초과" if side == "buy" else "덜오름", "최근 발동", "며칠전", "지금"))
            print(head)
            for x in rows:
                ex = x.get("fwd1m_excess") if side == "buy" else x.get("edge_vs_base")
                print("  %-22s %4d %7.2f%% %6.0f%% %7.2f%% %6.0f%% %7.2f%%p  %-11s %5s일 %s"
                      % (x["signal"][:22], x["n"], x["fwd1w_mean"], x["fwd1w_win"],
                         x["fwd1m_mean"], x["fwd1m_win"], ex,
                         x["last"] or "—", x["days_ago"] if x["days_ago"] is not None else "—",
                         "★ 켜짐" if x["on_now"] else ""))
            thin = [x["signal"] for x in r[side] if x.get("n", 0) < MIN_N]
            if thin:
                print("     표본 %d회 미만이라 통계 안 냄: %s" % (MIN_N, " · ".join(thin)))
    print("\n뺀 것(고가·저가·거래량 필요, %d종): %s" % (len(DROPPED), " · ".join(DROPPED)))
    print("→ _ta_signals.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
