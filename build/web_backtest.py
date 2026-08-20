# -*- coding: utf-8 -*-
"""build/web_backtest.py — 거미줄(계층 틸트 S×K×T×B) → data/web.json

규약: build/PREREG-2026-08-20-WEB.md (계산 전 커밋 · 적대 검토 wf_6af8d88f 반영).
주 판정: ΔIR(V_WEB − V_NR′) + 블록 부트스트랩 · 절대 하한 t(V_WEB) ≥ 2.

  사다리(순서 고정): R → S → K → S+K → +T(λ) → +B(밴드) = WEB. 챔피언 NR′ 동일 섀시.
  항등 검증 5종 실패 시 산출물 불사용. 완충은 합성 제외 — §5 회계 민감도.

    python build/web_backtest.py
"""
from __future__ import annotations
import datetime as dt
import io
import json
import math
import os
import random
import sys
from statistics import NormalDist

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "web.json")
sys.path.insert(0, HERE)
from aegis_backtest import load_px, week_ends, Sig, metrics, tstat          # noqa: E402
from tilt_backtest import load_weights, alias_map                           # noqa: E402
from aegis3_backtest import load_rf                                          # noqa: E402
from wvane_backtest import (RetSig, rf_weekly, build_weeks,                 # noqa: E402
                            MIN_PAIRS as WV_MIN_PAIRS, ZERO_FRAC_MAX as WV_ZERO_FRAC,
                            JUMP_MAX as WV_JUMP_MAX)

K_SEC, K_STK = 0.15, 0.3
SIG_TGT, SIG_WIN = 0.20, 63
COST = 0.0005
E_UP, E_DN = 1.10, 0.90
START = "2017-04"
SEED = 20260820
MIN_SEC_MEM, MIN_SEC_COVER, MIN_SECTORS = 3, 0.60, 5
ND = NormalDist()


def rank_z(vals, min_n=30, clip=2.0):
    xs = [(t, v) for t, v in vals.items() if v is not None]
    n = len(xs)
    if n < min_n:
        return {}
    xs.sort(key=lambda kv: kv[1])
    out = {}
    for r, (t, _v) in enumerate(xs):
        q = (r + 0.5) / n
        out[t] = max(-clip, min(clip, ND.inv_cdf(q)))
    return out


def sector_labels(W, AL):
    """라벨 해석 체인(§0): 캐시 라벨 → 별칭 라벨 → stocks.json sector → ''."""
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    meta_sec = {}
    for t, m in (st.get("meta") or {}).items():
        if isinstance(m, dict) and m.get("sector"):
            meta_sec[t] = m["sector"]
    by_day = {}
    for d, rows in W["w"].items():
        lab = {}
        for row in rows:
            t = row[0]
            g = row[2] if len(row) > 2 and row[2] else ""
            lab[t] = g
        by_day[d] = lab
    # 별칭 라벨: 같은 CIK 다른 티커의 라벨을 이어 붙인다(그 날 없으면 최근 라벨)
    latest = {}
    for d in sorted(by_day):
        for t, g in by_day[d].items():
            if g:
                latest[t] = g
    def resolve(d, t):
        g = by_day.get(d, {}).get(t) or ""
        if g:
            return g
        for a in sorted(AL.get(t, ())):
            if latest.get(a):
                return latest[a]
        return meta_sec.get(t, "")
    return resolve


def lam_series(bench_ndx, dts, we_idx):
    """λ = min(1, 0.20/σ63연율) — ^NDX 인접 페어. 페어<40 → 직전 λ 이월(§1)."""
    n = len(dts)
    rets = [None] * n
    prev = None
    for i, v in enumerate(bench_ndx):
        if v is not None and prev is not None:
            rets[i] = v / prev - 1
        if v is not None:
            prev = v
    lam = {}
    last_l = 1.0
    carried = 0
    for i0 in we_idx:
        xs = [r for r in rets[max(0, i0 - SIG_WIN + 1):i0 + 1] if r is not None]
        if len(xs) >= 40:
            m = sum(xs) / len(xs)
            sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
            ann = sd * math.sqrt(252)
            last_l = min(1.0, SIG_TGT / ann) if ann > 0 else 1.0
        else:
            carried += 1
        lam[i0] = last_l
    return lam, carried


def build_signals(dts, px, weeks, sig, vsig, resolve):
    """주별 선계산: 게이트 · dist200 · 섹터 라벨 · z 들(§1 규약). 전 변형 공유."""
    P = []
    for w in weeks:
        i0, d0 = w["i0"], w["d0"]
        base = w["base"]
        gate, dist, sec = {}, {}, {}
        for t in base:
            s1, s2, pc, zc, jc = vsig._pref(t)
            lo = max(0, i0 + 1 - 252)
            np_ = pc[i0 + 1] - pc[lo]
            ok = (np_ >= WV_MIN_PAIRS and (zc[i0 + 1] - zc[lo]) <= WV_ZERO_FRAC * max(1, np_)
                  and (jc[i0 + 1] - jc[lo]) <= WV_JUMP_MAX)   # 상수는 wvane 정본(이원화 금지)
            gate[t] = ok
            d_ = sig.dist(t, i0) if ok else None
            dist[t] = d_
            sec[t] = resolve(d0, t)
        # 섹터 원값(§1): 게이트·dist 유효 구성원의 벤더비중 재정규화 가중평균
        agg = {}
        for t, g in sec.items():
            if not g:
                continue
            agg.setdefault(g, [0.0, 0.0, 0.0, 0])   # [유효w·d합, 유효w합, 전체w합, 유효수]
            a = agg[g]
            a[2] += base[t]
            if dist[t] is not None:
                a[0] += base[t] * dist[t]
                a[1] += base[t]
                a[3] += 1
        sec_raw = {}
        for g, (swd, sw, tw, nv) in agg.items():
            if nv >= MIN_SEC_MEM and sw / max(1e-12, tw) >= MIN_SEC_COVER:
                sec_raw[g] = swd / sw
        z_sec_by_g = rank_z(sec_raw, min_n=MIN_SECTORS) if len(sec_raw) >= MIN_SECTORS else {}
        # 종목 z — 섹터중립(동료 간, min 5) · 전역
        z_k_neutral = {}
        by_g = {}
        for t, g in sec.items():
            if g:
                by_g.setdefault(g, {})[t] = dist[t]
        for g, vals in by_g.items():
            z_k_neutral.update(rank_z(vals, min_n=5))
        z_k_global = rank_z({t: dist[t] for t in base}, min_n=30)
        P.append({"z_sec": {t: z_sec_by_g.get(sec[t], 0.0) for t in base},
                  "z_kn": z_k_neutral, "z_kg": z_k_global,
                  "n_sec": len(sec_raw),
                  "unlabeled_w": sum(base[t] for t in base if not sec[t])})
    return P


def run(dts, px, weeks, P, lam, rf, last_ym,
        use_s=False, k_mode="off", use_lambda=False, band=False,
        k_sec=K_SEC, k_stk=K_STK, cost=COST, monthly=False):
    """단일 경로 실행. k_mode: off | neutral | global. (§4 정적판은 main 의 Ps 패널로 구현 —
    static_sec 파라미터·t_sector 스텁은 미사용 죽은 코드라 걷었다. 2026-08-20 점검 패널.)"""
    nav = 100.0
    prev_w, prev_p0, prev_e, prev_fin = None, None, 0.0, 0.0
    held = None
    daily_d, dv = [], []
    wk = {"ret": []}
    for j, w in enumerate(weeks):
        i0, i1 = w["i0"], w["i1"]
        base = w["base"]
        upd = (held is None) or (not monthly) or (dts[i1][:7] != w["d0"][:7])
        if upd:
            held = (E_UP if w["on"] else E_DN) if band else 1.0
        e = held
        lm = lam[i0] if use_lambda else 1.0
        mult = {}
        for t in base:
            m_ = 1.0
            if use_s:
                zs = P[j]["z_sec"].get(t, 0.0)
                m_ *= (1 + k_sec * lm * zs)
            if k_mode == "neutral":
                m_ *= (1 + k_stk * lm * P[j]["z_kn"].get(t, 0.0))
            elif k_mode == "global":
                m_ *= (1 + k_stk * lm * P[j]["z_kg"].get(t, 0.0))
            mult[t] = m_
        if mult and min(mult.values()) <= 0.05:
            raise SystemExit("배율 하한 가드 위반(%.3f) — §1" % min(mult.values()))
        wt = {t: base[t] * mult[t] for t in base}
        sw = sum(wt.values())
        wt = {t: v / sw for t, v in wt.items()}
        fin = max(0.0, e - 1.0) * rf_weekly(rf, w["d0"][:7], last_ym) if band else 0.0
        if prev_w is None:
            drift = {}
        else:
            g = {}
            for t in prev_w:
                a = px.get(t)
                v = a[i0] if a else None
                if v and prev_p0.get(t):
                    g[t] = v / prev_p0[t]
            pg = sum(prev_w[t] * g.get(t, 1.0) for t in prev_w)
            ng = 1 + prev_e * (pg - 1) - prev_fin
            drift = {t: prev_e * prev_w[t] * g.get(t, 1.0) / ng for t in prev_w}
        turn = sum(abs(e * wt.get(t, 0.0) - drift.get(t, 0.0)) for t in set(wt) | set(drift))
        nav0 = nav * (1 - cost * turn) * (1 - fin)
        p0 = {t: px[t][i0] for t in wt}
        cur = dict(p0)
        if not daily_d:
            daily_d.append(dts[i0]); dv.append(nav0)
        for d in range(i0 + 1, i1 + 1):
            acc = 0.0
            for t, ww in wt.items():
                v = px[t][d]
                if v:
                    cur[t] = v
                acc += ww * (cur[t] / p0[t])
            daily_d.append(dts[d]); dv.append(nav0 * (1 + e * (acc - 1)))
        nn = dv[-1]
        wk["ret"].append(nn / nav - 1)
        nav = nn
        prev_w, prev_p0, prev_e, prev_fin = wt, p0, e, fin
    return {"daily_d": daily_d, "dv": dv, "wk": wk}


def ir_of(vd, yrs):
    m = sum(vd) / len(vd)
    sd = math.sqrt(sum((x - m) ** 2 for x in vd) / (len(vd) - 1))
    te = sd * math.sqrt(52)
    annv = sum(vd) / yrs
    return (annv / te if te > 0 else 0.0), annv, te


def vstats(r, R, yrs):
    vd = [a - b for a, b in zip(r["wk"]["ret"], R["wk"]["ret"])]
    irr, annv, te = ir_of(vd, yrs)
    _m, t = tstat(vd)
    return vd, {"ann_pp": round(annv * 100, 2), "t": round(t, 2),
                "te_pp": round(te * 100, 2), "ir": round(irr, 2)}


def main() -> int:
    # 🚨 동결 가드(2026-08-20 점검) — 얼린 사전등록 산출물을 무심코 덮지 못하게 한다.
    #   재동결은 자료 정정 등 사유가 있을 때 --refreeze 로만, 사유는 커밋 메시지·장부에.
    if os.path.exists(OUT) and "--refreeze" not in sys.argv:
        raise SystemExit("%s 가 이미 있다 — 얼린 측정이다. 재동결은 --refreeze 로만." % OUT)
    dts, px, bench = load_px()
    W = load_weights()
    AL = alias_map()
    rf = load_rf()
    last_ym = max(rf)
    sig = Sig(px, len(dts))
    vsig = RetSig(px, len(dts))
    bsig = Sig(bench, len(dts))
    we_idx = week_ends(dts)
    weeks, _sk = build_weeks(dts, px, W, AL, we_idx, bsig)
    resolve = sector_labels(W, AL)
    lam, lam_carried = lam_series(bench["ndx"], dts, we_idx)
    P = build_signals(dts, px, weeks, sig, vsig, resolve)
    n_sec_med = sorted(p["n_sec"] for p in P)[len(P) // 2]
    unl_max = max(p["unlabeled_w"] for p in P)
    print("채택 주 %d · 유효 섹터 중위 %d · 무라벨 최대 %.2f%% · λ이월 %d"
          % (len(weeks), n_sec_med, unl_max * 100, lam_carried))

    A = {}
    A["R"] = run(dts, px, weeks, P, lam, rf, last_ym)
    A["S"] = run(dts, px, weeks, P, lam, rf, last_ym, use_s=True)
    A["K"] = run(dts, px, weeks, P, lam, rf, last_ym, k_mode="neutral")
    A["SK"] = run(dts, px, weeks, P, lam, rf, last_ym, use_s=True, k_mode="neutral")
    A["SKT"] = run(dts, px, weeks, P, lam, rf, last_ym, use_s=True, k_mode="neutral",
                   use_lambda=True)
    A["WEB"] = run(dts, px, weeks, P, lam, rf, last_ym, use_s=True, k_mode="neutral",
                   use_lambda=True, band=True)
    A["NRp"] = run(dts, px, weeks, P, lam, rf, last_ym, k_mode="global", band=True)
    A["KG"] = run(dts, px, weeks, P, lam, rf, last_ym, k_mode="global")

    # 항등 검증(§2)
    idc = {}
    lam1 = {i: 1.0 for i in lam}
    i2 = run(dts, px, weeks, P, lam1, rf, last_ym, use_s=True, k_mode="neutral",
             use_lambda=True)
    idc["I2_lam1"] = max(abs(a - b) for a, b in zip(i2["dv"], A["SK"]["dv"])) < 1e-9
    b_only = run(dts, px, weeks, P, lam, rf, last_ym, band=True)
    FJ = json.load(io.open(os.path.join(DATA, "wvane.json"), encoding="utf-8"))
    idc["I3_B_vs_wvane"] = abs(metrics(b_only["daily_d"], b_only["dv"],
                                       b_only["wk"]["ret"])["cagr"]
                               - FJ["decomp"]["B"]["cagr"]) < 0.05
    FL = json.load(io.open(os.path.join(DATA, "fleet.json"), encoding="utf-8"))
    # 🚨 2026-08-20 점검 — fleet.json 에 decomp 키가 없어 종전 else True 폴백이
    #   공허 통과였다(얼린 web.json 의 I1=true 는 비교 없이 기록된 값 — e-web 에 병기).
    #   교차 열쇠가 없으면 이제 실패로 처리한다.
    fl_r = ((FL.get("decomp") or {}).get("R") or {}).get("cagr")
    idc["I1_R_vs_fleet"] = (abs(metrics(A["R"]["daily_d"], A["R"]["dv"],
                                        A["R"]["wk"]["ret"])["cagr"] - fl_r) < 0.05
                            if fl_r is not None else False)
    # I4 — 단일 의사섹터 ⇒ 섹터중립 = 전역
    P1s = []
    for p in P:
        z_all = dict(p["z_kg"])
        P1s.append({"z_sec": {t: 0.0 for t in p["z_sec"]}, "z_kn": z_all,
                    "z_kg": z_all, "n_sec": 1, "unlabeled_w": 0.0})
    i4 = run(dts, px, weeks, P1s, lam, rf, last_ym, k_mode="neutral")
    idc["I4_pseudosec_eq_global"] = max(abs(a - b) for a, b in zip(i4["dv"], A["KG"]["dv"])) < 1e-9
    idc["I5_NRp_dir_vs_wvane_NR"] = (metrics(A["NRp"]["daily_d"], A["NRp"]["dv"],
                                             A["NRp"]["wk"]["ret"])["cagr"]
                                     - FJ["decomp"]["R"]["cagr"]) > 0
    if not all(idc.values()):
        raise SystemExit("항등 검증 실패 %s — 산출물을 쓰지 않는다(§2)" % idc)

    DD = A["R"]["daily_d"]
    yrs = (dt.date.fromisoformat(DD[-1]) - dt.date.fromisoformat(DD[0])).days / 365.25
    ladder = {}
    Vd = {}
    for k in ("S", "K", "SK", "SKT", "WEB", "NRp", "KG"):
        Vd[k], ladder[k] = vstats(A[k], A["R"], yrs)

    d_ir = ladder["WEB"]["ir"] - ladder["NRp"]["ir"]
    rng = random.Random(SEED)
    n = len(Vd["WEB"])
    blocks = [(s, min(s + 52, n)) for s in range(0, n, 52)]
    wins = 0
    for _b in range(2000):
        idx = []
        while len(idx) < n:
            s0_, e0_ = blocks[rng.randrange(len(blocks))]
            idx.extend(range(s0_, e0_))
        idx = idx[:n]
        iw, _a, _t = ir_of([Vd["WEB"][i] for i in idx], yrs)
        inr, _a2, _t2 = ir_of([Vd["NRp"][i] for i in idx], yrs)
        if iw > inr:
            wins += 1
    p_hat = wins / 2000
    t_web = ladder["WEB"]["t"]
    if d_ir > 0 and t_web >= 2:
        cell = "① 거미줄 이득 후보"
    elif d_ir > 0:
        cell = "② 방향만 — 선택과 구별 불가"
    elif ladder["K"]["ir"] - ladder["NRp"]["ir"] > 0:
        cell = "③ 세금은 S·T 몫 — 부분 채택은 새 등록"
    else:
        cell = "④ 거미줄 기각"

    # S 정적/타이밍 분해(§4) — 표본평균 섹터 배율 고정판
    from collections import defaultdict
    avg_mult = defaultdict(list)
    for j, p in enumerate(P):
        for t, zs in p["z_sec"].items():
            avg_mult[t].append(1 + K_SEC * zs)
    # 정적판: 섹터 z 의 표본평균을 각 주에 고정 적용 — run 을 static 패널로 흉내
    Ps = []
    for p in P:
        Ps.append({"z_sec": {t: (sum(avg_mult[t]) / len(avg_mult[t]) - 1) / K_SEC
                             for t in p["z_sec"]},
                   "z_kn": {}, "z_kg": {}, "n_sec": p["n_sec"], "unlabeled_w": 0.0})
    s_static = run(dts, px, weeks, Ps, lam, rf, last_ym, use_s=True)
    _vd, st_static = vstats(s_static, A["R"], yrs)
    s_timing_pp = round(ladder["S"]["ann_pp"] - st_static["ann_pp"], 2)

    # 예측 채점(§3)
    def spear(a_key, b_key):
        cs = []
        for p in P:
            za, zb = p[a_key], p[b_key]
            common = [t for t in za if t in zb]
            if len(common) < 30:
                continue
            ra = {t: r for r, t in enumerate(sorted(common, key=lambda x: za[x]))}
            rb = {t: r for r, t in enumerate(sorted(common, key=lambda x: zb[x]))}
            n_ = len(common)
            num = sum((ra[t] - (n_ - 1) / 2) * (rb[t] - (n_ - 1) / 2) for t in common)
            den = math.sqrt(sum((ra[t] - (n_ - 1) / 2) ** 2 for t in common)
                            * sum((rb[t] - (n_ - 1) / 2) ** 2 for t in common))
            if den > 0:
                cs.append(num / den)
        return sum(cs) / len(cs) if cs else None

    c_kn_kg = spear("z_kn", "z_kg")
    d_vt = ladder["SKT"]["ann_pp"] - ladder["SK"]["ann_pp"]
    d_irt = ladder["SKT"]["ir"] - ladder["SK"]["ir"]
    d_web_nr = ladder["WEB"]["ann_pp"] - ladder["NRp"]["ann_pp"]
    d_te = ladder["WEB"]["te_pp"] - ladder["NRp"]["te_pp"]
    pred = {
        "P1": {"pred": "corr(z_K중립, z_전역) ∈ [0.70,0.95]", "got": round(c_kn_kg, 3),
               "pass": bool(c_kn_kg is not None and 0.70 <= c_kn_kg <= 0.95)},
        "P2": {"pred": "V_K − V_전역K ∈ [−0.30,+0.50]%p",
               "got": round(ladder["K"]["ann_pp"] - ladder["KG"]["ann_pp"], 2),
               "pass": bool(-0.30 <= ladder["K"]["ann_pp"] - ladder["KG"]["ann_pp"] <= 0.50)},
        "P3": {"pred": "ΔIR_T ∈ [−0.10,+0.10] ∧ ΔV_T<0",
               "got": {"d_ir": round(d_irt, 3), "d_v": round(d_vt, 2)},
               "pass": bool(-0.10 <= d_irt <= 0.10 and d_vt < 0)},
        "P4": {"pred": "V_WEB−V_NR′ ∈ [−0.80,+0.30] ∧ ΔTE ∈ [0,+1.0]",
               "got": {"d_v": round(d_web_nr, 2), "d_te": round(d_te, 2)},
               "pass": bool(-0.80 <= d_web_nr <= 0.30 and 0 <= d_te <= 1.0)},
        "P5": {"pred": "S 타이밍 몫 ∈ [−0.30,+0.30]%p", "got": s_timing_pp,
               "pass": bool(-0.30 <= s_timing_pp <= 0.30)},
    }

    sens = {}
    for name, kw in (("Ksec0075", {"k_sec": 0.075}), ("Ksec030", {"k_sec": 0.30}),
                     ("K015", {"k_stk": 0.15}), ("monthly", {"monthly": True}),
                     ("cost20", {"cost": 0.0020})):
        r_ = run(dts, px, weeks, P, lam, rf, last_ym, use_s=True, k_mode="neutral",
                 use_lambda=True, band=True, **kw)
        _vd2, s_ = vstats(r_, A["R"], yrs)
        sens[name] = s_

    verdict = ("ΔIR(WEB−NR′) %+.3f · p̂ %.2f · t(V_WEB) %.2f → %s"
               % (d_ir, p_hat, t_web, cell))
    print()
    print("%-5s %8s %8s %8s %8s" % ("계단", "V연%p", "t", "TE%p", "IR"))
    for k in ("S", "K", "SK", "SKT", "WEB", "NRp", "KG"):
        s_ = ladder[k]
        print("%-5s %8.2f %8.2f %8.2f %8.2f" % (k, s_["ann_pp"], s_["t"], s_["te_pp"], s_["ir"]))
    print(verdict)
    print("S 분해 — 정적 %+0.2f · 타이밍 %+0.2f" % (st_static["ann_pp"], s_timing_pp))
    for k, v in pred.items():
        print("  %s %s %s" % (k, "✅" if v["pass"] else "❌", {a: b for a, b in v.items() if a != "pass"}))
    print("민감도:", {k: v["ann_pp"] for k, v in sens.items()})
    print("항등 검증:", idc)

    M = {k: metrics(A[k]["daily_d"], A[k]["dv"], A[k]["wk"]["ret"])
         for k in ("R", "WEB", "NRp")}
    doc = {
        "note": "거미줄 — 계층 틸트(섹터 실 × 섹터중립 모멘텀 실 × λ 시점 실 × 밴드 실). "
                "주 판정 ΔIR(WEB−NR′·같은 섀시 챔피언). PREREG-2026-08-20-WEB.md 에 MC 기준선·"
                "기지값·소급 GICS 고지와 함께 계산 전 커밋. DB 비중 — 러너 재생산 불가.",
        "prereg": "build/PREREG-2026-08-20-WEB.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"k_sec": K_SEC, "k_stk": K_STK, "sig_tgt": SIG_TGT, "sig_win": SIG_WIN,
                   "cost": COST, "seed": SEED, "start": START,
                   "sec_gate": [MIN_SEC_MEM, MIN_SEC_COVER, MIN_SECTORS]},
        "span": [DD[0], DD[-1]], "weeks": len(weeks),
        "identity_checks": idc, "lam_carried": lam_carried,
        "n_sec_median": n_sec_med, "unlabeled_w_max_pct": round(unl_max * 100, 2),
        "ladder": ladder, "metrics": M,
        "main": {"d_ir": round(d_ir, 3), "boot_p": round(p_hat, 3), "t_web": round(t_web, 2),
                 "cell": cell, "verdict": verdict},
        "s_decomp": {"static_pp": st_static["ann_pp"], "timing_pp": s_timing_pp},
        "predictions": pred, "sens": sens,
        "weekly": {"d": [w["d0"] for w in weeks],
                   "WEB": [round(x, 6) for x in Vd["WEB"]],
                   "NRp": [round(x, 6) for x in Vd["NRp"]],
                   "ret_WEB": [round(x, 6) for x in A["WEB"]["wk"]["ret"]],
                   "ret_NRp": [round(x, 6) for x in A["NRp"]["wk"]["ret"]],
                   "ret_R": [round(x, 6) for x in A["R"]["wk"]["ret"]],
                   "on": [1 if w["on"] else 0 for w in weeks]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
