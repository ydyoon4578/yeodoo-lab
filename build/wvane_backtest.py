# -*- coding: utf-8 -*-
"""build/wvane_backtest.py — 풍향계(레짐 조건부 팩터 틸트) → data/wvane.json

규약: build/PREREG-2026-08-20-WVANE.md (계산 전 커밋 · 적대 검토 wf_0b43a432 반영).
판정은 증분 3대비 — V1 = C−NR(회전의 몫·주 판정) · V2 = C−B · V3 = 상호작용.

  변형(전부 같은 채택 주·같은 기저·같은 비용):
    R  순복제(틸트 0 · 밴드 없음 · 조달 0)      A  틸트+회전 · 밴드 없음
    B  틸트 0 · 밴드 110/90 + 조달               C  풍향계 = 틸트+회전 + 밴드 + 조달
    NR 상시 MOM 틸트 + 밴드(회전만 제거)         LV 상시 LOWVOL 틸트 + 밴드(민감도)

  비용 순액식 Σ|e₁w₁ − 드리프트(e₀w₀)| · 항등 검증 3종 실패 시 산출물을 쓰지 않는다.

    python build/wvane_backtest.py
"""
from __future__ import annotations
import datetime as dt
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "wvane.json")
sys.path.insert(0, HERE)
from aegis_backtest import load_px, week_ends, Sig, metrics, tstat        # noqa: E402
from tilt_backtest import load_weights, alias_map, zscores                # noqa: E402
from aegis3_backtest import load_rf                                       # noqa: E402

K_TILT = 0.3
Z_CLIP = 2.0
COST = 0.0005
E_UP, E_DN = 1.10, 0.90
VOL_TD = 252
MIN_PAIRS = 160          # 유효 «페어» 수 — §0 자료 위생
ZERO_FRAC_MAX = 0.30     # 0% 수익 페어 비율 상한(유사-정지 시계열 차단)
JUMP_ABS, JUMP_MAX = 0.35, 2   # |r|>35% 페어 3개 이상이면 엔터티 오염 의심 → 신호 무효
DROP_MAX = 0.10
START = "2017-04"
DIV_NDX = 0.8


class RetSig:
    """인접 거래일 페어 수익률의 창 통계 — Σr·Σr²·페어수·0%수·점프수 prefix."""
    def __init__(self, px, n):
        self.px, self.n, self.c = px, n, {}

    def _pref(self, t):
        pr = self.c.get(t)
        if pr is None:
            a = self.px[t]
            n = self.n
            s1 = [0.0] * (n + 1); s2 = [0.0] * (n + 1)
            pc = [0] * (n + 1); zc = [0] * (n + 1); jc = [0] * (n + 1)
            for i in range(n):
                s1[i + 1], s2[i + 1] = s1[i], s2[i]
                pc[i + 1], zc[i + 1], jc[i + 1] = pc[i], zc[i], jc[i]
                if i > 0 and a[i] and a[i - 1]:          # 인접 페어만 — 갭 넘김 금지(§0)
                    r = a[i] / a[i - 1] - 1
                    s1[i + 1] += r; s2[i + 1] += r * r; pc[i + 1] += 1
                    if r == 0.0:
                        zc[i + 1] += 1
                    if abs(r) > JUMP_ABS:
                        jc[i + 1] += 1
            pr = self.c[t] = (s1, s2, pc, zc, jc)
        return pr

    def sigma(self, t, i, win=VOL_TD):
        """dts[i] 시점 직전 win 거래일 창의 일수익 표준편차 — 위생 관문 통과 시에만."""
        if t not in self.px or i < win:
            return None
        s1, s2, pc, zc, jc = self._pref(t)
        lo = i + 1 - win
        np_ = pc[i + 1] - pc[lo]
        if np_ < MIN_PAIRS:
            return None
        if (zc[i + 1] - zc[lo]) / np_ > ZERO_FRAC_MAX:
            return None                                   # 유사-정지(LCID 류) — 무효
        if (jc[i + 1] - jc[lo]) > JUMP_MAX:
            return None                                   # 엔터티 오염 의심 — 무효
        m = (s1[i + 1] - s1[lo]) / np_
        v = (s2[i + 1] - s2[lo]) / np_ - m * m
        return math.sqrt(max(0.0, v))


def rf_weekly(rf, ym, last_ym, spread_bp=0.0):
    """월복리 rf → 주 환산. 부분월(최신 달)은 직전 완결월로 대체(§1)."""
    use = ym if ym < last_ym else max(k for k in rf if k < last_ym)
    m = rf.get(use) or 0.0
    return (1 + m) ** (12.0 / 52.0) - 1 + spread_bp / 10000.0 / 52.0


def build_weeks(dts, px, W, AL, we_idx, bsig):
    """채택 주 목록 1회 확정 — 전 변형 공통 주입(§1). (i0,i1,base,drop,d200)"""
    d2i = {d: i for i, d in enumerate(dts)}
    out, skipped = [], []
    for j in range(len(we_idx) - 1):
        i0, i1 = we_idx[j], we_idx[j + 1]
        d0 = dts[i0]
        if d0[:7] < START:
            continue
        rows = W["w"].get(d0)
        if not rows:
            skipped.append([d0, "비중 결측"])
            continue
        port, drop = [], 0.0
        for t, w in rows:
            key = None
            if px.get(t) and px[t][i0] and px[t][i1]:
                key = t
            else:
                for a in sorted(AL.get(t, ())):
                    if px.get(a) and px[a][i0] and px[a][i1]:
                        key = a
                        break
            if key is None:
                drop += w
            else:
                port.append((key, w))
        if not port or drop > DROP_MAX:
            skipped.append([d0, "탈락 %.1f%%" % (drop * 100)])
            continue
        s = sum(w for _t, w in port)
        d200 = bsig.dist("ndx", i0)
        out.append({"i0": i0, "i1": i1, "d0": d0, "drop": drop,
                    "base": {t: w / s for t, w in port},
                    "on": bool(d200 is not None and d200 >= 0)})
    return out, skipped


def run(dts, px, weeks, sig, vsig, rf, last_ym,
        mode="C", k_tilt=K_TILT, cost=COST, band=True, fin_on=True,
        monthly=False, vol_td=VOL_TD, spread_bp=0.0, delay=0):
    """mode: R(순복제) A(틸트·밴드없음) B(밴드만) C(전부) NR(상시MOM) LV(상시LOWVOL)."""
    nav = 100.0
    prev_w, prev_p0, prev_e, prev_fin = None, None, 0.0, 0.0
    held = None          # 월간 모드 — (factor, e) 월말 주에만 갱신
    daily_d, dv = [], []
    wk = {"ret": [], "e": [], "on": [], "switch": [], "turn": [], "nsig0": []}
    prev_on = None
    for w in weeks:
        i0, i1 = w["i0"] + delay, w["i1"] + delay
        if i1 >= len(dts):
            break
        base = w["base"]
        # 상태 원자 갱신(§1) — 월간이면 월말 주에만
        upd = (held is None) or (not monthly) or (dts[w["i1"]][:7] != w["d0"][:7])
        if upd:
            on = w["on"]
            factor = "MOM" if on else "LOWVOL"
            e = (E_UP if on else E_DN) if band else 1.0
            held = (on, factor, e)
        on, factor, e = held
        # 틸트 비중
        n_sig0 = 0
        if mode in ("R", "B") or k_tilt == 0:
            wt = dict(base)
        else:
            use_f = {"A": factor, "C": factor, "NR": "MOM", "LV": "LOWVOL"}[mode]
            vals = {}
            for t in base:
                if use_f == "MOM":
                    v = sig.dist(t, w["i0"])
                else:
                    s_ = vsig.sigma(t, w["i0"], vol_td)
                    v = (-s_) if s_ is not None else None
                if v is None:
                    n_sig0 += 1
                vals[t] = v
            z = zscores(vals)
            wt = {t: b * (1 + k_tilt * z.get(t, 0.0)) for t, b in base.items()}
            sw = sum(wt.values())
            wt = {t: v / sw for t, v in wt.items()}
        if mode in ("R", "A"):
            e = 1.0
        fin = (max(0.0, e - 1.0) * 0 if not fin_on else
               max(0.0, e - 1.0) * rf_weekly(rf, w["d0"][:7], last_ym, spread_bp))
        if mode in ("R", "A"):
            fin = 0.0
        # 순액 실회전(§1) — 드리프트의 레버리지 성장 나눗셈은 근사
        if prev_w is None:
            drift = {}
        else:
            g = {}
            for t in prev_w:
                a = px.get(t)
                v = a[i0] if a else None
                if v and prev_p0.get(t):
                    g[t] = v / prev_p0[t]
            port_g = sum(prev_w[t] * g.get(t, 1.0) for t in prev_w)
            nav_g = 1 + prev_e * (port_g - 1) - prev_fin
            drift = {t: prev_e * prev_w[t] * g.get(t, 1.0) / nav_g for t in prev_w}
        turn = sum(abs(e * wt.get(t, 0.0) - drift.get(t, 0.0))
                   for t in set(wt) | set(drift))
        nav0 = nav * (1 - cost * turn) * (1 - fin)
        # 일간 경로 — nav_d = nav0 × (1 + e×(acc−1)), 결측 carry
        p0 = {}
        for t in wt:
            v = px[t][i0]
            if not v:                          # 지연 체결(delay) 결측 방어 — 직전 유효가
                for kk in range(i0 - 1, max(-1, w["i0"] - 2), -1):
                    if px[t][kk]:
                        v = px[t][kk]
                        break
            p0[t] = v
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
            daily_d.append(dts[d])
            dv.append(nav0 * (1 + e * (acc - 1)))
        new_nav = dv[-1]
        wk["ret"].append(new_nav / nav - 1)
        wk["e"].append(e); wk["on"].append(1 if on else 0)
        wk["switch"].append(1 if (prev_on is not None and on != prev_on) else 0)
        wk["turn"].append(turn); wk["nsig0"].append(n_sig0)
        nav = new_nav
        prev_w, prev_p0, prev_e, prev_fin, prev_on = wt, p0, e, fin, on
    return {"daily_d": daily_d, "dv": dv, "wk": wk}


def ann(dd, xs_weekly_diff):
    yrs = (dt.date.fromisoformat(dd[-1]) - dt.date.fromisoformat(dd[0])).days / 365.25
    return sum(xs_weekly_diff) / yrs * 100


def main() -> int:
    dts, px, bench = load_px()
    W = load_weights()
    AL = alias_map()
    rf = load_rf()
    last_ym = max(rf)
    sig = Sig(px, len(dts))
    vsig = RetSig(px, len(dts))
    bsig = Sig(bench, len(dts))
    we_idx = week_ends(dts)
    weeks, skipped = build_weeks(dts, px, W, AL, we_idx, bsig)
    n_off = sum(1 for w in weeks if not w["on"])
    print("채택 주 %d(오프 %d) · 건너뜀 %d %s" % (len(weeks), n_off, len(skipped), skipped[:3]))

    V = {}
    for mode in ("R", "A", "B", "C", "NR", "LV"):
        V[mode] = run(dts, px, weeks, sig, vsig, rf, last_ym, mode=mode)
    # 항등 검증 3종(§2) — 깨지면 쓰지 않는다
    idc = {}
    c_k0 = run(dts, px, weeks, sig, vsig, rf, last_ym, mode="C", k_tilt=0.0)
    idc["k0_eq_B"] = max(abs(a - b) for a, b in zip(c_k0["dv"], V["B"]["dv"])) < 1e-9
    c_nb = run(dts, px, weeks, sig, vsig, rf, last_ym, mode="C", band=False, fin_on=False)
    idc["noband_eq_A"] = max(abs(a - b) for a, b in zip(c_nb["dv"], V["A"]["dv"])) < 1e-9
    sens_nb = run(dts, px, weeks, sig, vsig, rf, last_ym, mode="C", band=False, fin_on=False)
    idc["sens_noband_eq_A"] = max(abs(a - b) for a, b in zip(sens_nb["dv"], V["A"]["dv"])) < 1e-9
    if not all(idc.values()):
        raise SystemExit("항등 검증 실패 %s — 산출물을 쓰지 않는다(§2)" % idc)

    DD = V["C"]["daily_d"]
    M = {m: metrics(V[m]["daily_d"], V[m]["dv"], V[m]["wk"]["ret"]) for m in V}
    # 벤치 — 채택 주 (i0,i1) 정렬(연속 주간 zip 금지)
    ndx_ff, last = [], None
    for v in bench["ndx"]:
        if v is not None:
            last = v
        ndx_ff.append(last)
    wk_b = [ndx_ff[w["i1"]] / ndx_ff[w["i0"]] - 1 for w in weeks]
    d2i = {d: i for i, d in enumerate(dts)}
    ib0, ib1 = d2i[DD[0]], d2i[DD[-1]]
    dv_b = [100.0 * ndx_ff[i] / ndx_ff[ib0] for i in range(ib0, ib1 + 1)]
    m_b = metrics(DD, dv_b, wk_b)
    m_b["cagr_div_adj"] = round(m_b["cagr"] + DIV_NDX, 2)

    # 증분 3대비(§2)
    def contrast(a, b):
        d = [x - y for x, y in zip(V[a]["wk"]["ret"], V[b]["wk"]["ret"])]
        m, t = tstat(d)
        return d, ann(DD, d), t
    dV1, a1, t1 = contrast("C", "NR")
    dV2, a2, t2 = contrast("C", "B")
    v3w = [c - a - b + r for c, a, b, r in zip(
        V["C"]["wk"]["ret"], V["A"]["wk"]["ret"], V["B"]["wk"]["ret"], V["R"]["wk"]["ret"])]
    a3 = ann(DD, v3w)
    off_cb = [d for d, w in zip(dV2, weeks) if not w["on"]]
    p3_bp = sum(off_cb) / max(1, len(off_cb)) * 10000
    # P4 — 재진입(오프→온) 후 4채택주 C−B 누적
    reentry = []
    ons = V["C"]["wk"]["on"]
    for k in range(1, len(weeks)):
        if ons[k] == 1 and ons[k - 1] == 0:
            seg = dV2[k:k + 4]
            if len(seg) == 4:
                reentry.append(sum(seg))
    p4_mean = (sum(reentry) / len(reentry)) if reentry else None

    gates = {
        "V1_rotation": {"ann_pp": round(a1, 2), "t": round(t1, 2),
                        "pass": bool(a1 > 0)},
        "V2_tilt_over_band": {"ann_pp": round(a2, 2), "t": round(t2, 2),
                              "pass": bool(a2 > 0)},
        "V3_interaction": {"ann_pp": round(a3, 2), "pass": bool(a3 >= 0)},
    }
    rot_verdict = "회전 유효" if gates["V1_rotation"]["pass"] else "회전 기각 — 3문과 무관(§2)"

    # 참고 — 사용자 3문(B 승계 라벨), U1 판정행 = 배당보정(§2)
    mc = M["C"]
    u = {"U1_cagr_div_adj": {"strat": mc["cagr"], "bm_div_adj": m_b["cagr_div_adj"],
                             "pass": bool(mc["cagr"] > m_b["cagr_div_adj"])},
         "U2_sharpe": {"strat": mc["sharpe"], "bm": m_b["sharpe"],
                       "pass": bool(mc["sharpe"] > m_b["sharpe"])},
         "U3_mdd": {"strat": mc["mdd"], "bm": m_b["mdd"],
                    "pass": bool(abs(mc["mdd"]) < abs(m_b["mdd"]))},
         "label": "B(밴드) 승계 통과 — 가족 기저율 3/4 하에서 그 자체로는 약한 증거(§0)"}

    pred = {
        "P1": {"pred": "V1 ∈ [+0.10,+1.50]%p", "got": round(a1, 2),
               "pass": bool(0.10 <= a1 <= 1.50)},
        "P2": {"pred": "V2 ∈ [+0.40,+2.00]%p", "got": round(a2, 2),
               "pass": bool(0.40 <= a2 <= 2.00)},
        "P3": {"pred": "오프 주 C−B ∈ [+2,+30]bp/주", "got": round(p3_bp, 1),
               "pass": bool(2 <= p3_bp <= 30)},
        "P4": {"pred": "재진입 4주 C−B 누적 음수", "events": len(reentry),
               "got": (None if p4_mean is None else round(p4_mean * 10000, 1)),
               "pass": bool(p4_mean is not None and p4_mean < 0)},
        "P5": {"pred": "V3 ≥ 0", "got": round(a3, 2), "pass": bool(a3 >= 0)},
    }

    sens = {}
    for name, kw in (("LV_always", {"mode": "LV"}), ("K015", {"k_tilt": 0.15}),
                     ("sig126", {"vol_td": 126}), ("monthly", {"monthly": True}),
                     ("cost20", {"cost": 0.0020}), ("rf_p50", {"spread_bp": 50.0}),
                     ("delay1", {"delay": 1})):
        r = run(dts, px, weeks, sig, vsig, rf, last_ym, mode=kw.pop("mode", "C"), **kw)
        mm = metrics(r["daily_d"], r["dv"], r["wk"]["ret"])
        n_ = min(len(r["wk"]["ret"]), len(V["NR"]["wk"]["ret"]))
        d_ = [x - y for x, y in zip(r["wk"]["ret"][:n_], V["NR"]["wk"]["ret"][:n_])]
        sens[name] = {"cagr": mm["cagr"], "sharpe": mm["sharpe"], "mdd": mm["mdd"],
                      "vsNR_pp": round(ann(r["daily_d"], d_), 2)}

    sw_turns = [t for t, s in zip(V["C"]["wk"]["turn"], V["C"]["wk"]["switch"]) if s]
    nn_turns = [t for t, s in zip(V["C"]["wk"]["turn"][1:], V["C"]["wk"]["switch"][1:]) if not s]
    print("%-4s %8s %8s %8s" % ("", "CAGR%", "Sharpe", "MDD%"))
    for m in ("R", "A", "B", "C", "NR", "LV"):
        print("%-4s %8.2f %8.2f %8.2f" % (m, M[m]["cagr"], M[m]["sharpe"], M[m]["mdd"]))
    print("^NDX %7.2f %8.2f %8.2f (배당보정 %.2f)" % (m_b["cagr"], m_b["sharpe"], m_b["mdd"], m_b["cagr_div_adj"]))
    print("V1(회전) %+.2f%%p t %.2f · V2(틸트) %+.2f%%p t %.2f · V3(상호) %+.2f%%p"
          % (a1, t1, a2, t2, a3))
    print("오프 주 C−B %.1fbp/주 · 재진입 이벤트 %d개 평균 %.1fbp"
          % (p3_bp, len(reentry), (p4_mean or 0) * 10000))
    print("판정: %s" % rot_verdict)
    for k, v in pred.items():
        print("  %s %s %s" % (k, "✅" if v["pass"] else "❌", {a: b for a, b in v.items() if a != "pass"}))
    print("전환 주 %d회 평균 회전 %.0f%% · 평시 %.1f%%" % (len(sw_turns),
          100 * sum(sw_turns) / max(1, len(sw_turns)), 100 * sum(nn_turns) / max(1, len(nn_turns))))
    print("3문(참고·%s): U1(배당보정) %s · U2 %s · U3 %s" % (u["label"][:14],
          "✅" if u["U1_cagr_div_adj"]["pass"] else "❌",
          "✅" if u["U2_sharpe"]["pass"] else "❌", "✅" if u["U3_mdd"]["pass"] else "❌"))
    print("민감도:")
    for k, v in sens.items():
        print("  %-10s CAGR %6.2f · Sharpe %5.2f · MDD %6.2f · vsNR %+5.2f%%p"
              % (k, v["cagr"], v["sharpe"], v["mdd"], v["vsNR_pp"]))
    print("항등 검증:", idc)

    doc = {
        "note": "풍향계 — NDX 벤더비중 위 레짐 조건부 팩터 틸트(위험-온 MOM·110% / 위험-오프 "
                "LOWVOL·90%). 판정은 증분 3대비 — V1(회전)·V2(틸트)·V3(상호작용). 3문은 참고"
                "(B 승계 라벨). 규칙·예측·위생 관문은 PREREG-2026-08-20-WVANE.md 에 계산 전 커밋. "
                "기준 비중은 DB(커밋 금지) — 러너 재생산 불가(얼린 측정). 5번째 사용자-기준 시도.",
        "prereg": "build/PREREG-2026-08-20-WVANE.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"k": K_TILT, "clip": Z_CLIP, "cost": COST, "e": [E_UP, E_DN],
                   "vol_td": VOL_TD, "min_pairs": MIN_PAIRS, "zero_frac_max": ZERO_FRAC_MAX,
                   "jump": [JUMP_ABS, JUMP_MAX], "start": START},
        "span": [DD[0], DD[-1]], "weeks": len(weeks), "off_weeks": n_off,
        "skipped": skipped, "identity_checks": idc,
        "decomp": {m: M[m] for m in ("R", "A", "B", "C", "NR", "LV")},
        "bench": m_b, "contrasts": gates, "rot_verdict": rot_verdict,
        "user3_ref": u, "predictions": pred, "sens": sens,
        "p3_off_bp_wk": round(p3_bp, 1),
        "p4_reentry": {"events": len(reentry),
                       "mean_bp": (None if p4_mean is None else round(p4_mean * 10000, 1)),
                       "each_bp": [round(x * 10000, 1) for x in reentry]},
        "turnover": {"switch_avg_pct": round(100 * sum(sw_turns) / max(1, len(sw_turns)), 1),
                     "normal_avg_pct": round(100 * sum(nn_turns) / max(1, len(nn_turns)), 2),
                     "switches": int(sum(V["C"]["wk"]["switch"]))},
        "sig_invalid_wk_avg": round(sum(V["C"]["wk"]["nsig0"]) / len(weeks), 2),
        "weekly": {"d": [w["d0"] for w in weeks],
                   "C": [round(x, 6) for x in V["C"]["wk"]["ret"]],
                   "NR": [round(x, 6) for x in V["NR"]["wk"]["ret"]],
                   "B": [round(x, 6) for x in V["B"]["wk"]["ret"]],
                   "R": [round(x, 6) for x in V["R"]["wk"]["ret"]],
                   "on": V["C"]["wk"]["on"]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
