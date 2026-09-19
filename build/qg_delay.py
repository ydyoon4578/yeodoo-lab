# -*- coding: utf-8 -*-
"""qg_delay.py — 우량성장 30 의 진입 시점 미루기 (PREREG-2026-09-20-QGDELAY · 3621d32)

  형성월에 가격 축 z(Mom · negOsc · negResid)가 그 달 유니버스 **하위 십분위**인
  보유 종목을 **1개월 미뤄서** 산다. 빼는 것이 아니다.

🚨 F3 셔플이 본체 — 같은 분기에 같은 개수를 무작위로 미룬 판과 겨룬다.

  python qg_delay.py
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "yeodoo-lab")
D18 = r"C:\Users\Win10\Documents\여두_20260918"
DATA = os.path.join(LAB, "data")
SRC = os.path.join(D18, r"02_우량성장_최소구성\qg_monthly.pkl")
SRC_IX = os.path.join(D18, r"02_우량성장_최소구성\qg_index.pkl")
SRC_DIV = os.path.join(D18, r"01_이관묶음\01_우량성장선별_산출물\idx_div_monthly_20260918.csv")
HOLD0, HOLD1 = "2014-07", "2026-08"
COST, NSHUF, SEED = 0.0025, 200, 20260920


def ym_add(ym, k):
    t = int(ym[:4]) * 12 + int(ym[5:7]) - 1 + k
    return "%04d-%02d" % (t // 12, t % 12 + 1)


def price_axis():
    """그 달 유니버스의 가격 축 z (섹터중립 · Mom·negOsc·negResid 평균)."""
    sys.path.insert(0, os.path.join(LAB, "build"))
    from refresh_stocks import rsi as _rsi, boll as _boll      # noqa: E402
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    px = {}
    for s in st["stocks"]:
        p = os.path.join(DATA, "sd", "%s.json" % s["t"])
        if os.path.exists(p):
            v = json.load(io.open(p, encoding="utf-8")).get("pxd")
            if isinstance(v, list) and len(v) == len(dates):
                px[s["t"]] = v
    pit = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))
    for t, v in pit["px"].items():
        if t in px or not isinstance(v, dict):
            continue
        arr = [np.nan] * len(dates)
        i0, pp = int(v.get("i0") or 0), (v.get("p") or [])
        for k, val in enumerate(pp):
            if 0 <= i0 + k < len(dates) and val is not None:
                arr[i0 + k] = float(val)
        px[t] = arr
    P = pd.DataFrame(px, index=pd.to_datetime(dates))
    M = P.resample("M").last(); M.index = M.index.to_period("M")
    MR = M.pct_change()
    MOM = M.shift(1) / M.shift(13) - 1
    NEGRES = -(MR.sub(MR.mean(axis=1), axis=0))
    zs = []
    for fn in (lambda c: _rsi(c), lambda c: _boll(c)[3]):
        X = P.apply(fn, axis=0)
        zs.append(((X.sub(X.mean(axis=1), axis=0))
                   .div(X.std(axis=1).replace(0, np.nan), axis=0)).clip(-3, 3))
    NEGOSC = -(sum(zs) / len(zs)).resample("M").last()
    NEGOSC.index = NEGOSC.index.to_period("M")

    mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
    hist = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
    hsec = hist.get("sector") or {}
    months = hist["months"]

    Z = {}
    for m in M.index:
        v = months.get(str(m)) or {}
        uni = set(v.get("spx") or []) | set(v.get("ndx") or [])
        uni = [t for t in uni if t in M.columns and pd.notna(M.at[m, t])]
        if len(uni) < 50:
            continue
        rec = []
        for t in uni:
            rec.append({"t": t, "s": sect.get(t) or hsec.get(t) or "?",
                        "Mom": MOM.at[m, t] if t in MOM.columns else np.nan,
                        "negOsc": NEGOSC.at[m, t] if (m in NEGOSC.index and t in NEGOSC.columns) else np.nan,
                        "negResid": NEGRES.at[m, t] if t in NEGRES.columns else np.nan})
        g = pd.DataFrame(rec)
        for c in ("Mom", "negOsc", "negResid"):
            g[c] = g.groupby("s")[c].transform(
                lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * 0).clip(-3, 3)
        g = g.dropna(subset=["Mom", "negOsc", "negResid"])
        if len(g) < 50:
            continue
        g["z"] = g[["Mom", "negOsc", "negResid"]].mean(axis=1)
        cut = g.z.quantile(0.10)                     # 하위 십분위 경계
        Z[str(m)] = {"z": dict(zip(g.t, g.z)), "cut": float(cut)}
    return Z


def backtest(sel, ret, forms, delay_of):
    """delay_of[f] = 그 형성월에 1개월 미룰 종목 집합."""
    out, prev = {}, {}
    for f in forms:
        w0 = sel.get(f)
        if not w0:
            continue
        dl = delay_of.get(f, set())
        w1 = {t: v for t, v in w0.items() if t not in dl}      # 1개월차
        if not w1:
            w1 = dict(w0); dl = set()
        s1 = sum(w1.values()); w1 = {t: v / s1 for t, v in w1.items()}
        w = w1
        for k in (1, 2, 3):
            hm = ym_add(f, k)
            if not (HOLD0 <= hm <= HOLD1):
                continue
            if k == 2 and dl:
                # 미룬 종목을 원래 목표 비중으로 편입하고 전체를 1 로
                add = {t: w0[t] for t in dl}
                merged = dict(w)
                sc = 1.0 - sum(add.values())
                if sc > 0:
                    merged = {t: v * sc for t, v in merged.items()}
                    merged.update(add)
                    z = sum(merged.values())
                    w = {t: v / z for t, v in merged.items()}
            trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
            r = ret.get(ym_add(f, k - 1), {})
            ok = {t: v for t, v in w.items() if t in r}
            s = sum(ok.values())
            if s <= 0:
                continue
            gross = sum(v / s * r[t] for t, v in ok.items())
            out[hm] = (gross, trade * COST, trade)
            w = {t: (v / s) * (1 + r[t]) for t, v in ok.items()}
            z = sum(w.values()); w = {t: v / z for t, v in w.items()}
            prev = w
    return out


def stats(ex):
    a = float(np.mean(ex)) * 12 * 100
    te = float(np.std(ex, ddof=1)) * np.sqrt(12) * 100
    return {"ann": a, "ir": a / te}


def main():
    Z = price_axis()
    print("가격 축 z — 월 %d개 (%s ~ %s)" % (len(Z), min(Z), max(Z)))

    qg = pd.read_pickle(SRC)
    idx = pd.read_pickle(SRC_IX)
    idx_pr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(SRC_DIV)
    idx_div = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in qg.groupby("ym")}
    sel, forms = {}, []
    for f, g in qg[qg.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) in (3, 6, 9, 12):
            sel[f] = dict(zip(g.tkr, g.wtgt / 100.0)); forms.append(f)
    forms = sorted(forms)

    def legs(delay_of):
        H = backtest(sel, ret, forms, delay_of)
        ms = sorted(m for m in H if m in idx_pr and m in idx_div and pd.notna(idx_pr[m]))
        B = np.array([H[m][0] - H[m][1] - (idx_pr[m] + idx_div[m]) for m in ms])
        turn = sum(H[m][2] for m in ms) / (len(ms) / 12.0) / 2 * 100
        return ms, B, turn

    ms0, B0, t0 = legs({})
    s0 = stats(B0)
    print("확정안 재현 — 연 초과 %+.2f%%p · IR %.3f · 회전 %.0f%% (사전등록 8.15·0.987·116)"
          % (s0["ann"], s0["ir"], t0))

    # 미루는 대상
    dmain, cnt, miss = {}, [], 0
    for f in forms:
        zz = Z.get(f)
        if not zz:
            miss += 1; dmain[f] = set(); cnt.append(0); continue
        held = list(sel[f])
        d = {t for t in held if t in zz["z"] and zz["z"][t] <= zz["cut"]}
        dmain[f] = d; cnt.append(len(d))
    cnt = np.array(cnt)
    print("\n미루는 종목 — 분기당 평균 %.2f종 (최대 %d · 0종 분기 %d/%d · z 없는 분기 %d)"
          % (cnt.mean(), cnt.max(), int((cnt == 0).sum()), len(cnt), miss))

    ms1, B1, t1 = legs(dmain)
    s1 = stats(B1)

    def yr(ms, B):
        y = {}
        for m, e in zip(ms, B):
            y.setdefault(m[:4], []).append(e)
        return {k: (float(np.prod(1 + np.array(v))) - 1) * 100 for k, v in y.items()}

    def ex16(ms, B):
        m = np.array([x[:4] != "2016" for x in ms])
        return stats(B[m])["ann"]

    print("\n■ 결과")
    print("   %-18s %10s %8s %9s %11s %9s" % ("", "연 초과", "IR", "회전율", "2016 제외", "2016"))
    for nm, mss, BB, tt in (("확정안", ms0, B0, t0), ("미루기", ms1, B1, t1)):
        print("   %-18s %+9.2f %8.3f %8.0f%% %+10.2f %+9.2f"
              % (nm, stats(BB)["ann"], stats(BB)["ir"], tt, ex16(mss, BB), yr(mss, BB)["2016"]))

    print("\n■ F3 셔플 %d회 — 같은 분기에 같은 개수를 무작위로 미룬다" % NSHUF)
    rng = np.random.default_rng(SEED)
    sh = np.empty(NSHUF)
    for q in range(NSHUF):
        dd = {}
        for f in forms:
            k = len(dmain[f]); h = list(sel[f])
            dd[f] = set(rng.choice(h, min(k, len(h)), replace=False)) if k else set()
        sh[q] = stats(legs(dd)[1])["ann"]
        if (q + 1) % 50 == 0:
            print("   ... %d회" % (q + 1))
    pct = float((sh < s1["ann"]).mean()) * 100
    print("   실측 %+.2f · 무작위 평균 %+.2f (sd %.2f) · 백분위 %.1f"
          % (s1["ann"], sh.mean(), sh.std(ddof=1), pct))

    F = {"F1 확정안보다 낮음": s1["ann"] <= s0["ann"],
         "F2 2016 제외해도 확정안 이하": ex16(ms1, B1) <= ex16(ms0, B0),
         "F3 셔플 상위 5% 밖": pct < 95.0,
         "F4 회전율 1.5배 초과": t1 > t0 * 1.5}
    print("\n■ 기각 조건")
    for k, v in F.items():
        print("   %s  %s" % ("❌ 걸림" if v else "✅ 통과", k))
    verdict = "기각" if any(F.values()) else "채택(워크포워드 필요)"
    print("\n→ 판정: %s" % verdict)
    print("   (등록서 §4 예측 ①: F3 에서 걸릴 것 — %s)"
          % ("맞음" if F["F3 셔플 상위 5% 밖"] else "틀림"))

    io.open(os.path.join(HERE, "qg_delay_result.json"), "w", encoding="utf-8").write(
        json.dumps({"prereg": "PREREG-2026-09-20-QGDELAY", "commit": "3621d32",
                    "base": dict(s0, turn=t0, ex2016=ex16(ms0, B0), y2016=yr(ms0, B0)["2016"]),
                    "delay": dict(s1, turn=t1, ex2016=ex16(ms1, B1), y2016=yr(ms1, B1)["2016"]),
                    "n_delayed": {"mean": float(cnt.mean()), "max": int(cnt.max()),
                                  "zero_q": int((cnt == 0).sum()), "n_q": len(cnt)},
                    "shuffle": {"n": NSHUF, "seed": SEED, "mean": float(sh.mean()),
                                "sd": float(sh.std(ddof=1)), "pctile": pct},
                    "by_year": yr(ms1, B1),
                    "fails": {k: bool(v) for k, v in F.items()}, "verdict": verdict},
                   ensure_ascii=False, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
