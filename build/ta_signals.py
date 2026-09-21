# -*- coding: utf-8 -*-
"""build/ta_signals.py — 교과서 TA 신호 검증(매수·매도) → data/_ta_signals.json

설계 출처는 사용자 제공 사내 `ta_lab`(backtest_signals.py · indicators.py)이다.
**산식과 발동 조건만** 가져왔다 — 사내 DB·경로·티커 화이트리스트는 안 옮긴다.

자료
  · `data/bench_px.json`   — 종가 정본. **기준일을 여기서 가져온다.**
  · `data/bench_ohlc.json` — 고가·저가·거래량(build/bench_ohlc.py). 있으면 37종 전부,
    없으면 종가로 낼 수 있는 27종만 낸다(그 사실을 산출물에 적는다).

무엇을. 10년 구간에서 신호마다
  · 처음 켜진 날(이벤트) 종가 진입 → 달력 +7일 / +30일 사후수익
  · 무조건부 기준선 대비 초과
  · **최근 발동일과 경과일**  ← 원본 CSV 에 없던 것. 사용자 요청 2026-09-22.
  · 지금 켜져 있나
매수·매도 양쪽을 다 낸다.

🚨 **기준일은 bench_px 의 as_of 로 자른다.** 수집기가 하루이틀 더 받아 올 수 있는데,
   그러면 「최근 발동일」이 랩의 다른 화면과 어긋난다. 랩 격자가 정본이다.
⚠ 이 파일은 새 주장을 만들지 않는다. 원본이 이미 낸 결론(매도 신호는 숏이 아니다 ·
  단일 지표 의존 금지)을 이 랩 자료로 다시 재는 것이다.

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

# ══ 지표 — ta_lab/indicators.py 에서 **그대로** 옮긴다 ════════════════════
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
    return pd.DataFrame({"up": up, "lo": lo, "pb": (c - lo) / (up - lo), "bw": (up - lo) / mid})


def disparity(c, n=20):
    return c / sma(c, n) * 100


def trix(c, n=15, sig=9):
    e = ema(ema(ema(c, n), n), n)
    t = e.pct_change() * 100
    return pd.DataFrame({"trix": t, "signal": ema(t, sig)})


def sroc(c, n=12, m=13):
    return roc(ema(c, m), n)


def td_setup(c):
    diff = (c - c.shift(4)).to_numpy()
    cnt = np.zeros(len(c))
    for i in range(4, len(c)):
        if diff[i] < 0:
            cnt[i] = cnt[i - 1] + 1 if cnt[i - 1] > 0 else 1
        elif diff[i] > 0:
            cnt[i] = cnt[i - 1] - 1 if cnt[i - 1] < 0 else -1
    return pd.Series(cnt, index=c.index)


def rvi_vol(c, n=10, m=14):
    sd = c.rolling(n).std()
    up = pd.Series(np.where(c.diff() > 0, sd, 0.0), index=c.index).ewm(span=m, adjust=False).mean()
    dn = pd.Series(np.where(c.diff() < 0, sd, 0.0), index=c.index).ewm(span=m, adjust=False).mean()
    return 100 * up / (up + dn)


# ── 고가·저가·거래량이 필요한 것 ──────────────────────────────────────────
def tr(h, l, c):
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def atr(h, l, c, n=14):
    return tr(h, l, c).ewm(alpha=1 / n, adjust=False).mean()


def stoch(h, l, c, k=14, d=3, slow=3):
    lo, hi = l.rolling(k).min(), h.rolling(k).max()
    slow_k = (100 * (c - lo) / (hi - lo)).rolling(slow).mean()
    return pd.DataFrame({"k": slow_k, "d": slow_k.rolling(d).mean()})


def cci(h, l, c, n=20):
    tp = (h + l + c) / 3
    ma = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - ma) / (0.015 * md)


def williams_r(h, l, c, n=14):
    hi, lo = h.rolling(n).max(), l.rolling(n).min()
    return (hi - c) / (hi - lo) * -100


def ultimate_osc(h, l, c, n1=7, n2=14, n3=28):
    pc = c.shift(1)
    bp = c - pd.concat([l, pc], axis=1).min(axis=1)
    t_ = tr(h, l, c)
    a = [bp.rolling(n).sum() / t_.rolling(n).sum() for n in (n1, n2, n3)]
    return 100 * (4 * a[0] + 2 * a[1] + a[2]) / 7


def keltner(h, l, c, n=20, mult=2.0):
    mid, a = ema(c, n), atr(h, l, c, n)
    return pd.DataFrame({"up": mid + mult * a, "lo": mid - mult * a})


def mfi(h, l, c, v, n=14):
    tp = (h + l + c) / 3
    mf = tp * v
    pos = pd.Series(np.where(tp.diff() > 0, mf, 0.0), index=c.index).rolling(n).sum()
    neg = pd.Series(np.where(tp.diff() < 0, mf, 0.0), index=c.index).rolling(n).sum()
    return 100 - 100 / (1 + pos / neg)


def mass_index(h, l, n=9, total=25):
    r = (h - l).ewm(span=n, adjust=False).mean()
    return (r / r.ewm(span=n, adjust=False).mean()).rolling(total).sum()


def psar(h, l, af0=0.02, af_step=0.02, af_max=0.2):
    n = len(h)
    trend = np.zeros(n)
    if n < 3:
        return pd.Series(trend, index=h.index)
    up, af, ep, s = True, af0, h.iloc[0], l.iloc[0]
    hv, lv = h.to_numpy(), l.to_numpy()
    for i in range(1, n):
        s = s + af * (ep - s)
        if up:
            s = min(s, lv[i - 1], lv[max(i - 2, 0)])
            if lv[i] < s:
                up, s, ep, af = False, ep, lv[i], af0
            elif hv[i] > ep:
                ep, af = hv[i], min(af + af_step, af_max)
        else:
            s = max(s, hv[i - 1], hv[max(i - 2, 0)])
            if hv[i] > s:
                up, s, ep, af = True, ep, hv[i], af0
            elif lv[i] < ep:
                ep, af = lv[i], min(af + af_step, af_max)
        trend[i] = 1 if up else -1
    return pd.Series(trend, index=h.index)


def supertrend(h, l, c, n=10, mult=3.0):
    mid = (h + l) / 2
    a = atr(h, l, c, n)
    ub, lb, cl = (mid + mult * a).to_numpy(), (mid - mult * a).to_numpy(), c.to_numpy()
    trend = np.ones(len(cl)); fub, flb = ub.copy(), lb.copy()
    for i in range(1, len(cl)):
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or cl[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or cl[i - 1] < flb[i - 1]) else flb[i - 1]
        trend[i] = (-1 if cl[i] < flb[i] else 1) if trend[i - 1] == 1 else (1 if cl[i] > fub[i] else -1)
    return pd.Series(trend, index=c.index)


def donchian(h, l, n=20):
    return pd.DataFrame({"up": h.rolling(n).max(), "lo": l.rolling(n).min()})


def aroon(h, l, n=25):
    up = h.rolling(n + 1).apply(lambda x: 100 * float(np.argmax(x)) / n, raw=True)
    dn = l.rolling(n + 1).apply(lambda x: 100 * float(np.argmin(x)) / n, raw=True)
    return pd.DataFrame({"up": up, "down": dn})


def ichimoku(h, l):
    conv = (h.rolling(9).max() + l.rolling(9).min()) / 2
    base = (h.rolling(26).max() + l.rolling(26).min()) / 2
    return pd.DataFrame({"span_a": ((conv + base) / 2).shift(26),
                         "span_b": ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)})


def adx(h, l, c, n=14):
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=h.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=h.index)
    a = atr(h, l, c, n)
    pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False).mean() / a
    mdi = 100 * mdm.ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return pd.DataFrame({"pdi": pdi, "mdi": mdi, "adx": dx.ewm(alpha=1 / n, adjust=False).mean()})


def rwi(h, l, c, n=14):
    a = atr(h, l, c, 14)
    hi = pd.Series(0.0, index=c.index)
    for k in range(2, n + 1):
        hi = pd.concat([hi, (h - l.shift(k)) / (a * np.sqrt(k))], axis=1).max(axis=1)
    return hi


def vwap_roll(h, l, c, v, n=20):
    tp = (h + l + c) / 3
    return (tp * v).rolling(n).sum() / v.rolling(n).sum()


def nvi(c, v):
    r = c.pct_change().fillna(0)
    return (1 + pd.Series(np.where(v < v.shift(1), r, 0.0), index=c.index)).cumprod() * 1000


def pvi(c, v):
    r = c.pct_change().fillna(0)
    return (1 + pd.Series(np.where(v > v.shift(1), r, 0.0), index=c.index)).cumprod() * 1000


def elder_ray(h, l, c, n=13):
    e = ema(c, n)
    return pd.DataFrame({"bull": h - e, "bear": l - e})


def force_index(c, v, n=13):
    return (c.diff() * v).ewm(span=n, adjust=False).mean()


def ad_line(h, l, c, v):
    clv = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    return (clv.fillna(0) * v).cumsum()


def chaikin_osc(h, l, c, v, fast=3, slow=10):
    a = ad_line(h, l, c, v)
    return ema(a, fast) - ema(a, slow)


def obv_osc(c, v, fast=3, slow=10):
    o = (np.sign(c.diff()).fillna(0) * v).cumsum()
    return ema(o, fast) - ema(o, slow)


def eom(h, l, v, n=14, scale=1e8):
    box = (v / scale) / (h - l).replace(0, np.nan)
    return (((h + l) / 2).diff() / box).rolling(n).mean()


CONF_TOP = ["RSI14<30", "TEMA20>SMA50 교차", "TD BuySetup9", "BB %b<0", "MACD 0선 상향"]


def build_signals(c, h=None, l=None, v=None):
    """반환: (매수, 매도, 종류). h/l/v 가 없으면 종가 전용 27종만."""
    bb, m, tx = bollinger(c), macd(c), trix(c)
    td, dsp, sr = td_setup(c), disparity(c), sroc(c)
    bw_low = bb["bw"].rolling(126).min()
    z = pd.Series(0.0, index=c.index)
    up = lambda a, b: (a > b) & (a.shift(1) <= b.shift(1))
    dn = lambda a, b: (a < b) & (a.shift(1) >= b.shift(1))
    kind = {}
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
    for k in list(buy) + list(sell):
        kind[k] = "event"
    buy["RVI(변동성)>50"] = rvi_vol(c) > 50
    kind["RVI(변동성)>50"] = "state"

    if h is None:
        return buy, sell, kind

    st, ax = stoch(h, l, c), adx(h, l, c)
    kc, dc, ar, ich = keltner(h, l, c), donchian(h, l), aroon(h, l), ichimoku(h, l)
    er, ps, sp = elder_ray(h, l, c), psar(h, l), supertrend(h, l, c)
    mi, nv, pv = mass_index(h, l), nvi(c, v), pvi(c, v)
    cloud_hi = pd.concat([ich["span_a"], ich["span_b"]], axis=1).max(axis=1)
    cloud_lo = pd.concat([ich["span_a"], ich["span_b"]], axis=1).min(axis=1)
    buy.update({
        "Stoch %K<20 골든": up(st["k"], st["d"]) & (st["k"] < 25),
        "CCI<-100": cci(h, l, c) < -100,
        "Williams%R<-80": williams_r(h, l, c) < -80,
        "UltimateOsc<30": ultimate_osc(h, l, c) < 30,
        "Keltner 하단 이탈": c < kc["lo"],
        "MFI<20": mfi(h, l, c, v) < 20,
        "MassIndex 반전벌지": (mi.shift(1) > 27) & (mi < 26.5),
        "PSAR 상승 전환": (ps == 1) & (ps.shift(1) == -1),
        "SuperTrend 상승 전환": (sp == 1) & (sp.shift(1) == -1),
        "Donchian20 상단 돌파": c >= dc["up"].shift(1),
        "Aroon 업 교차": up(ar["up"], ar["down"]),
        "일목 구름 상향 돌파": up(c, cloud_hi),
        "ElderRay 강세셋업": (er["bear"] < 0) & (er["bear"].diff(3) > 0) & (c > ema(c, 50)),
        "ForceIndex2 매수딥": (force_index(c, v, 2) < 0) & (c > ema(c, 22)),
        "ChaikinOsc 0선 상향": up(chaikin_osc(h, l, c, v), z),
        "OBV Osc 0선 상향": up(obv_osc(c, v), z),
        "EOM 0선 상향": up(eom(h, l, v), z),
    })
    for k in ("Stoch %K<20 골든", "CCI<-100", "Williams%R<-80", "UltimateOsc<30",
              "Keltner 하단 이탈", "MFI<20", "MassIndex 반전벌지", "PSAR 상승 전환",
              "SuperTrend 상승 전환", "Donchian20 상단 돌파", "Aroon 업 교차",
              "일목 구름 상향 돌파", "ElderRay 강세셋업", "ForceIndex2 매수딥",
              "ChaikinOsc 0선 상향", "OBV Osc 0선 상향", "EOM 0선 상향"):
        kind[k] = "event"
    for k, cond in (("ADX>25 & +DI>-DI", (ax["adx"] > 25) & (ax["pdi"] > ax["mdi"])),
                    ("RWI High>1", rwi(h, l, c) > 1),
                    ("가격>VWAP20", c > vwap_roll(h, l, c, v)),
                    ("NVI>1년MA", nv > nv.rolling(252).mean()),
                    ("PVI>1년MA", pv > pv.rolling(252).mean())):
        buy[k] = cond
        kind[k] = "state"
    sell.update({
        "Stoch %K>80 데드": dn(st["k"], st["d"]) & (st["k"] > 75),
        "CCI>+100": cci(h, l, c) > 100,
        "Williams%R>-20": williams_r(h, l, c) > -20,
        "UltimateOsc>70": ultimate_osc(h, l, c) > 70,
        "Keltner 상단 돌파": c > kc["up"],
        "MFI>80": mfi(h, l, c, v) > 80,
        "PSAR 하락 전환": (ps == -1) & (ps.shift(1) == 1),
        "SuperTrend 하락 전환": (sp == -1) & (sp.shift(1) == 1),
        "Donchian20 하단 이탈": c <= dc["lo"].shift(1),
        "Aroon 다운 교차": dn(ar["up"], ar["down"]),
        "일목 구름 하향 이탈": dn(c, cloud_lo),
    })
    for k in ("Stoch %K>80 데드", "CCI>+100", "Williams%R>-20", "UltimateOsc>70",
              "Keltner 상단 돌파", "MFI>80", "PSAR 하락 전환", "SuperTrend 하락 전환",
              "Donchian20 하단 이탈", "Aroon 다운 교차", "일목 구름 하향 이탈"):
        kind[k] = "event"
    return buy, sell, kind


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
        # 🚨 매도는 «덜 올랐나» 로 본다 — 숏 진입 신호가 아니라 차익실현 신호라서.
        r["fwd1m_down"] = round(float((r1m < 0).mean()) * 100, 0)
        r["edge_vs_base"] = round((base1m - float(r1m.mean())) * 100, 2)
    else:
        r["fwd1m_excess"] = round((float(r1m.mean()) - base1m) * 100, 2)
    return r


def main() -> int:
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    asof = B["as_of"]                      # 🚨 랩 격자가 정본 — 여기서 자른다
    OH = None
    p = os.path.join(DATA, "bench_ohlc.json")
    if os.path.exists(p):
        OH = json.load(io.open(p, encoding="utf-8"))

    out = {"note": "교과서 TA 신호 검증. 설계 출처는 사용자 제공 사내 ta_lab "
                   "(backtest_signals.py · indicators.py) — **산식과 발동 조건만** 가져왔다.",
           "as_of": asof, "years": YEARS, "basis": B.get("basis"),
           "src": ("bench_ohlc.json(고가·저가·거래량) + bench_px.json(기준일)" if OH
                   else "bench_px.json(종가만) — 고가·저가·거래량이 없어 27종만 낸다"),
           "full": bool(OH), "index": {}}

    for key, _lab in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        if OH:
            s = OH["series"][key]
            idx = pd.to_datetime(s["dates"])
            keep = idx <= pd.Timestamp(asof)          # 기준일 초과분은 버린다
            idx = idx[keep]
            c_all = pd.Series(np.array(s["c"])[keep], index=idx)
            h_all = pd.Series(np.array(s["h"])[keep], index=idx)
            l_all = pd.Series(np.array(s["l"])[keep], index=idx)
            v_all = pd.Series(np.array(s["v"], dtype=float)[keep], index=idx)
            label, ticker = s["label"], s["ticker"]
        else:
            idx = pd.to_datetime(B["dates"])
            c_all = pd.Series(B["series"][key]["px"], index=idx).dropna()
            h_all = l_all = v_all = None
            label, ticker = B["series"][key]["label"], B["series"][key]["ticker"]

        start = c_all.index[-1] - pd.DateOffset(years=YEARS)
        c = c_all[c_all.index >= start]
        fwd = fwd_returns(c)
        base1m = float(np.nanmean(fwd["1m"]))
        buy, sell, kind = build_signals(c_all, h_all, l_all, v_all)

        rec = {"label": label, "ticker": ticker, "n_days": len(c),
               "start": str(c.index[0].date()), "base1m": round(base1m * 100, 2),
               "buy": [], "sell": []}
        ev_cache = {}
        for side, dct, is_sell in (("buy", buy, False), ("sell", sell, True)):
            for nm, cond in dct.items():
                cond = cond.reindex(c.index).fillna(False).astype(bool)
                mask = cond if kind[nm] == "state" else \
                    (cond & ~cond.shift(1, fill_value=False))
                ev_cache[nm] = cond & ~cond.shift(1, fill_value=False)
                r = {"signal": nm, "kind": kind[nm],
                     **_stat(mask, fwd, base1m, sell=is_sell)}
                fired = c.index[ev_cache[nm]]
                r["last"] = str(fired[-1].date()) if len(fired) else None
                r["days_ago"] = int((c.index[-1] - fired[-1]).days) if len(fired) else None
                r["on_now"] = bool(cond.iloc[-1])
                rec[side].append(r)

        conf = []
        for i in range(len(CONF_TOP)):
            for j in range(i + 1, len(CONF_TOP)):
                a, b = CONF_TOP[i], CONF_TOP[j]
                ea, eb, w = ev_cache[a], ev_cache[b], 5
                both = (ea & eb.rolling(w, min_periods=1).max().astype(bool)) | \
                       (eb & ea.rolling(w, min_periods=1).max().astype(bool))
                both = both & ~both.shift(1, fill_value=False)
                fired = c.index[both]
                conf.append({"pair": "%s ∧ %s" % (a, b), **_stat(both, fwd, base1m),
                             "last": str(fired[-1].date()) if len(fired) else None})
        rec["confluence"] = conf
        out["index"][key] = rec

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    for key in ("spx", "ndx"):
        r = out["index"][key]
        print("\n" + "═" * 98)
        print("%s (%s) · %s ~ %s · %d거래일 · 기준선 1개월 %+.2f%%  [매수 %d · 매도 %d]"
              % (r["label"], r["ticker"], r["start"], asof, r["n_days"], r["base1m"],
                 len(r["buy"]), len(r["sell"])))
        print("═" * 98)
        for side, ko in (("buy", "매수"), ("sell", "매도")):
            rows = [x for x in r[side] if x.get("n", 0) >= MIN_N]
            kf = (lambda x: -(x.get("fwd1m_excess") or -99)) if side == "buy" \
                else (lambda x: -(x.get("edge_vs_base") or -99))
            rows.sort(key=kf)
            print("\n  ── %s %d종 ──   %-22s %4s %8s %7s %8s %7s %8s  %-11s %6s"
                  % (ko, len(rows), "신호", "횟수", "1주", "1주승", "1개월", "1개월승",
                     "초과" if side == "buy" else "덜오름", "최근 발동", "며칠전"))
            for x in rows:
                ex = x.get("fwd1m_excess") if side == "buy" else x.get("edge_vs_base")
                print("      %-24s %-4s %4d %7.2f%% %6.0f%% %7.2f%% %6.0f%% %7.2f%%p  %-11s %5s일 %s"
                      % (x["signal"][:24], "상태" if x["kind"] == "state" else "",
                         x["n"], x["fwd1w_mean"], x["fwd1w_win"], x["fwd1m_mean"],
                         x["fwd1m_win"], ex, x["last"] or "—",
                         x["days_ago"] if x["days_ago"] is not None else "—",
                         "★ 켜짐" if x["on_now"] else ""))
            thin = [x["signal"] for x in r[side] if x.get("n", 0) < MIN_N]
            if thin:
                print("      표본 %d회 미만: %s" % (MIN_N, " · ".join(thin)))
    print("\n자료: %s" % out["src"])
    print("→ _ta_signals.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
