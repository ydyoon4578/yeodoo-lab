# -*- coding: utf-8 -*-
"""build/fleet_backtest.py — 함대(무선별 6축 틸트 배치 + 앙상블) → data/fleet.json

규약: build/PREREG-2026-08-20-FLEET.md (계산 전 커밋 · 적대 검토 wf_3819dc73 반영).
주 판정: ΔIR = IR(V_ENS) − IR(V_MOM · 사전 지명 챔피언), 블록 부트스트랩 p̂.

  축(전부 랭크-z · 공통 엔터티 게이트 선행): MOM STR LOWVOL W52H AMAX KURT
  변형: R + 축별 6판 + ENS + FLAG(밴드) + 앵커(MOM 원값z) + LOO 6판 + 민감도.
  신호 패널 1회 선계산 공유 · 항등 검증 실패 시 산출물 불사용.

    python build/fleet_backtest.py
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
OUT = os.path.join(DATA, "fleet.json")
sys.path.insert(0, HERE)
from aegis_backtest import load_px, week_ends, Sig, metrics, tstat         # noqa: E402
from tilt_backtest import load_weights, alias_map                          # noqa: E402
from aegis3_backtest import load_rf                                        # noqa: E402
from wvane_backtest import (RetSig, rf_weekly, build_weeks,               # noqa: E402
                            MIN_PAIRS, ZERO_FRAC_MAX, JUMP_MAX)

K_TILT = 0.3
Z_CLIP = 2.0
COST = 0.0005
E_UP, E_DN = 1.10, 0.90
START = "2017-04"
AXES = ("MOM", "STR", "LOWVOL", "W52H", "AMAX", "KURT")
MIN_AXES = 4                 # ENS — 유효 축 미달 시 완전 중립(§1)
SEED = 20260820
ND = NormalDist()


def load_hi(dts):
    """일중 고가 채널 — sd/*.json hd + 편출종목 _pit_hl_cache. 부재 티커는 None(폴백은 신호부)."""
    n = len(dts)
    hi = {}
    sd = os.path.join(DATA, "sd")
    for fn in os.listdir(sd):
        if fn.endswith(".json"):
            d = json.load(io.open(os.path.join(sd, fn), encoding="utf-8")) or {}
            a = d.get("hd") or []
            if a:
                hi[fn[:-5]] = (a + [None] * (n - len(a)))[:n]
    p = os.path.join(DATA, "_pit_hl_cache.json")
    if os.path.exists(p):
        try:
            hl = json.load(io.open(p, encoding="utf-8"))
            ds2 = hl.get("dates") or []
            d2i = {d: i for i, d in enumerate(dts)}
            for t, v in (hl.get("h") or {}).items():
                if t in hi:
                    continue
                a = [None] * n
                arr = v.get("p") if isinstance(v, dict) else v
                i0 = v.get("i0", 0) if isinstance(v, dict) else 0
                if arr:
                    for k, x in enumerate(arr):
                        if x is not None and i0 + k < len(ds2):
                            j = d2i.get(ds2[i0 + k])
                            if j is not None:
                                a[j] = x
                    hi[t] = a
        except Exception as e:
            print("⚠ HL 캐시 읽기 실패(%s) — 편출종목 W52H 는 종가 폴백으로 감" % str(e)[:50])
    return hi


class HiSig:
    """rollmax252(일중 고가) + 유효 고가 관측 prefix — 단조 데크 한 패스."""
    def __init__(self, hi, n):
        self.hi, self.n, self.c = hi, n, {}

    def _roll(self, t):
        pr = self.c.get(t)
        if pr is None:
            a = self.hi.get(t)
            if a is None:
                pr = self.c[t] = None
                return None
            n = self.n
            rm = [None] * n
            cnt = [0] * (n + 1)
            from collections import deque
            dq = deque()               # (idx, val) 단조 감소
            for i in range(n):
                cnt[i + 1] = cnt[i] + (1 if a[i] else 0)
                if a[i]:
                    while dq and dq[-1][1] <= a[i]:
                        dq.pop()
                    dq.append((i, a[i]))
                while dq and dq[0][0] <= i - 252:
                    dq.popleft()
                rm[i] = dq[0][1] if dq else None
            pr = self.c[t] = (rm, cnt)
        return pr

    def w52h(self, t, i, px_close):
        pr = self._roll(t)
        p = px_close[t][i] if px_close.get(t) else None
        if not p:
            return None, False
        if pr is None:                              # HL 부재 — 게시 규칙의 종가 폴백(수 기록)
            return None, True
        rm, cnt = pr
        if cnt[i + 1] - cnt[max(0, i - 251)] < 200 or not rm[i]:
            return None, False
        return p / rm[i], False


def kurt_win(px, t, i, vsig, win=252, min_n=202):
    """초과첨도 — 게시 excess_kurt 자구(2-pass · 모집단 적률 · v 바닥 가드)."""
    a = px.get(t)
    if not a or i < win:
        return None
    xs = []
    for k in range(i - win + 1, i + 1):
        if a[k] and a[k - 1]:
            xs.append(a[k] / a[k - 1] - 1)
    if len(xs) < min_n:
        return None
    n = len(xs)
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / n
    if v <= 1e-10:
        return None
    return sum((x - m) ** 4 for x in xs) / n / (v * v) - 3.0


def amax_win(px, t, i, win=21, min_n=10):
    a = px.get(t)
    if not a or i < win:
        return None
    best, n = None, 0
    for k in range(i - win + 1, i + 1):
        if a[k] and a[k - 1]:
            r = a[k] / a[k - 1] - 1
            n += 1
            if best is None or r > best:
                best = r
    return best if n >= min_n else None


def rank_z(vals):
    """랭크-z(백분위→정규분위) 후 클립 — §1 새 선택. vals: {t: raw or None}"""
    xs = [(t, v) for t, v in vals.items() if v is not None]
    n = len(xs)
    if n < 30:
        return {}
    xs.sort(key=lambda kv: kv[1])
    out = {}
    for r, (t, _v) in enumerate(xs):
        q = (r + 0.5) / n
        out[t] = max(-Z_CLIP, min(Z_CLIP, ND.inv_cdf(q)))
    return out


def raw_z(vals):
    """원값-z(틸트1 자구) — 앵커 판 전용."""
    xs = [v for v in vals.values() if v is not None]
    if len(xs) < 30:
        return {}
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    if sd <= 0:
        return {}
    return {t: max(-Z_CLIP, min(Z_CLIP, (v - m) / sd))
            for t, v in vals.items() if v is not None}


def build_panel(dts, px, weeks, sig, vsig, hsig):
    """신호 원값 패널 — (주, 축) → {t: raw}. 전 변형 공유(§1 경로 이원화 금지)."""
    panel = []
    fb_total = 0
    for w in weeks:
        i0 = w["i0"]
        row = {ax: {} for ax in AXES}
        fb = 0
        for t in w["base"]:
            # 공통 엔터티 게이트: RetSig 위생(페어·0%·점프) — sigma 가 None 인 사유가
            # 게이트인지 창 부족인지 구분해야 하므로 직접 검사한다. 상수는 wvane 정본.
            s1, s2, pc, zc, jc = vsig._pref(t)
            lo = max(0, i0 + 1 - 252)
            np_ = pc[i0 + 1] - pc[lo]
            ent_ok = (np_ >= MIN_PAIRS and (zc[i0 + 1] - zc[lo]) <= ZERO_FRAC_MAX * max(1, np_)
                      and (jc[i0 + 1] - jc[lo]) <= JUMP_MAX)
            if not ent_ok:
                continue                                    # 전 축 무효(§1 공통 선행)
            d = sig.dist(t, i0)
            if d is not None:
                row["MOM"][t] = d
            if i0 >= 21 and px[t][i0] and px[t][i0 - 21]:
                row["STR"][t] = -(px[t][i0] / px[t][i0 - 21] - 1)
            s_ = vsig.sigma(t, i0)
            if s_ is not None:
                row["LOWVOL"][t] = -s_
            v52, fell = hsig.w52h(t, i0, px)
            if fell:
                fb += 1                                     # 종가 폴백 대상(게시 규칙 허용) —
                a = px.get(t)                               # 분모를 종가 최대로
                if a and i0 >= 251:
                    win = [a[k] for k in range(i0 - 251, i0 + 1) if a[k]]
                    if len(win) >= 200 and a[i0]:
                        row["W52H"][t] = a[i0] / max(win)
            elif v52 is not None:
                row["W52H"][t] = v52
            m_ = amax_win(px, t, i0)
            if m_ is not None:
                row["AMAX"][t] = -m_
            k_ = kurt_win(px, t, i0, vsig)
            if k_ is not None:
                row["KURT"][t] = -k_
        panel.append(row)
        fb_total += fb
    return panel, fb_total


def zpanel(panel, weeks, scaling=rank_z):
    """축별 z 패널 + 주별 무효 수. z[w][ax] = {t: z}"""
    Z, dead = [], {ax: 0 for ax in AXES}
    for row, w in zip(panel, weeks):
        zr = {}
        for ax in AXES:
            vals = {t: row[ax].get(t) for t in w["base"]}
            z = scaling(vals)
            if not z:
                dead[ax] += 1
            zr[ax] = z
        Z.append(zr)
    return Z, dead


def run(dts, px, weeks, Z, rf, last_ym, axw, band=False, fin_on=False,
        k_tilt=K_TILT, cost=COST, monthly=False):
    """axw: {축: 가중} — 단일축=원핫 · ENS=동일가중 · LOO=한 칸 0. 단일 경로(§1)."""
    nav = 100.0
    prev_w, prev_p0, prev_e, prev_fin = None, None, 0.0, 0.0
    held = None
    daily_d, dv = [], []
    wk = {"ret": [], "neut": []}
    use_axes = [ax for ax, g in axw.items() if g > 0]
    for j, w in enumerate(weeks):
        i0, i1 = w["i0"], w["i1"]
        base = w["base"]
        upd = (held is None) or (not monthly) or (dts[i1][:7] != w["d0"][:7])
        if upd:
            e = ((E_UP if w["on"] else E_DN) if band else 1.0)
            held = e
        e = held
        # 합성 z — 유효 축 평균(<MIN_AXES 중립) → 재-랭크z(§1)
        comp = {}
        n_neut = 0
        if len(use_axes) == 1:
            comp = dict(Z[j][use_axes[0]])
        else:
            for t in base:
                zs = [Z[j][ax][t] for ax in use_axes if t in Z[j][ax]]
                if len(zs) >= MIN_AXES:
                    comp[t] = sum(zs) / len(zs)
                else:
                    n_neut += 1
            comp = rank_z(comp)
        if k_tilt == 0 or not comp:
            wt = dict(base)
        else:
            wt = {t: b * (1 + k_tilt * comp.get(t, 0.0)) for t, b in base.items()}
            sw = sum(wt.values())
            wt = {t: v / sw for t, v in wt.items()}
        fin = max(0.0, e - 1.0) * rf_weekly(rf, w["d0"][:7], last_ym) if fin_on else 0.0
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
        wk["neut"].append(n_neut)
        nav = nn
        prev_w, prev_p0, prev_e, prev_fin = wt, p0, e, fin
    return {"daily_d": daily_d, "dv": dv, "wk": wk}


def ir_of(vd, yrs):
    m = sum(vd) / len(vd)
    sd = math.sqrt(sum((x - m) ** 2 for x in vd) / (len(vd) - 1))
    te = sd * math.sqrt(52)
    annv = sum(vd) / yrs
    return (annv / te if te > 0 else 0.0), annv, te


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
    hsig = HiSig(load_hi(dts), len(dts))
    we_idx = week_ends(dts)
    weeks, skipped = build_weeks(dts, px, W, AL, we_idx, bsig)
    print("채택 주 %d · 건너뜀 %d" % (len(weeks), len(skipped)))
    panel, fb = build_panel(dts, px, weeks, sig, vsig, hsig)
    Z, dead = zpanel(panel, weeks)
    print("신호 패널 — 축 사멸 주:", dead, "· W52H 종가 폴백 %d종-주" % fb)

    one = lambda ax: {a: (1.0 if a == ax else 0.0) for a in AXES}
    ens_w = {a: 1.0 for a in AXES}
    V = {"R": run(dts, px, weeks, Z, rf, last_ym, {a: 0.0 for a in AXES}, k_tilt=0.0)}
    for ax in AXES:
        V[ax] = run(dts, px, weeks, Z, rf, last_ym, one(ax))
    V["ENS"] = run(dts, px, weeks, Z, rf, last_ym, ens_w)
    V["FLAG"] = run(dts, px, weeks, Z, rf, last_ym, ens_w, band=True, fin_on=True)
    Zraw, _ = zpanel(panel, weeks, scaling=raw_z)
    V["ANCHOR"] = run(dts, px, weeks, Zraw, rf, last_ym, one("MOM"))

    # 항등 검증(§2)
    idc = {}
    c0 = run(dts, px, weeks, Z, rf, last_ym, one("MOM"), k_tilt=0.0)
    idc["k0_eq_R"] = max(abs(a - b) for a, b in zip(c0["dv"], V["R"]["dv"])) < 1e-9
    oh = run(dts, px, weeks, Z, rf, last_ym,
             {a: (1.0 if a == "STR" else 0.0) for a in AXES})
    idc["onehot_eq_single"] = max(abs(a - b) for a, b in zip(oh["dv"], V["STR"]["dv"])) < 1e-9
    fb2 = run(dts, px, weeks, Z, rf, last_ym, ens_w, band=False, fin_on=False)
    idc["flag_noband_eq_ENS"] = max(abs(a - b) for a, b in zip(fb2["dv"], V["ENS"]["dv"])) < 1e-9
    if not all(idc.values()):
        raise SystemExit("항등 검증 실패 %s — 산출물을 쓰지 않는다(§2)" % idc)

    DD = V["R"]["daily_d"]
    yrs = (dt.date.fromisoformat(DD[-1]) - dt.date.fromisoformat(DD[0])).days / 365.25
    Vd = {k: [a - b for a, b in zip(V[k]["wk"]["ret"], V["R"]["wk"]["ret"])]
          for k in list(AXES) + ["ENS", "ANCHOR"]}
    stats = {}
    for k, vd in Vd.items():
        irr, annv, te = ir_of(vd, yrs)
        _m, t = tstat(vd)
        stats[k] = {"ann_pp": round(annv * 100, 2), "t": round(t, 2),
                    "te_pp": round(te * 100, 2), "ir": round(irr, 2)}

    # 주 판정 — ΔIR + 블록 부트스트랩(§2)
    d_ir = stats["ENS"]["ir"] - stats["MOM"]["ir"]
    rng = random.Random(SEED)
    n = len(Vd["ENS"])
    blocks = [(s, min(s + 52, n)) for s in range(0, n, 52)]
    wins = 0
    B = 2000
    for _b in range(B):
        idx = []
        while len(idx) < n:
            s, e_ = blocks[rng.randrange(len(blocks))]
            idx.extend(range(s, e_))
        idx = idx[:n]
        ve = [Vd["ENS"][i] for i in idx]
        vm = [Vd["MOM"][i] for i in idx]
        ie_, _a, _t2 = ir_of(ve, yrs)
        im_, _a2, _t3 = ir_of(vm, yrs)
        if ie_ > im_:
            wins += 1
    p_hat = wins / B
    t_ens = stats["ENS"]["t"]
    if d_ir > 0 and t_ens >= 2:
        cell = "① 분산 이득 후보"
    elif d_ir > 0:
        cell = "② 방향만 — 선택과 구별 불가"
    else:
        cell = None                     # LOO 뒤 확정

    # LOO 6판
    loo = {}
    for ax in AXES:
        w_ = {a: (0.0 if a == ax else 1.0) for a in AXES}
        r_ = run(dts, px, weeks, Z, rf, last_ym, w_)
        vd = [a - b for a, b in zip(r_["wk"]["ret"], V["R"]["wk"]["ret"])]
        irr, annv, _te = ir_of(vd, yrs)
        loo[ax] = {"ann_pp": round(annv * 100, 2), "ir": round(irr, 2),
                   "d_ir_vs_mom": round(irr - stats["MOM"]["ir"], 2)}
    if cell is None:
        if loo["STR"]["d_ir_vs_mom"] > 0 or loo["W52H"]["d_ir_vs_mom"] > 0:
            cell = "③ 상쇄/중복 희석 — 분산 가설 미판정"
        else:
            cell = "④ 무선별 분산 기각(메뉴 질 반영)"

    # 예측 채점(§3)
    import statistics as st_
    def spear_wk(axa, axb):
        cs = []
        for j in range(len(weeks)):
            za, zb = Z[j][axa], Z[j][axb]
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

    c_wm = spear_wk("W52H", "MOM")
    pairs = []
    ks = list(AXES)
    for i2 in range(len(ks)):
        for j2 in range(i2 + 1, len(ks)):
            a_, b_ = Vd[ks[i2]], Vd[ks[j2]]
            ma, mb = sum(a_) / n, sum(b_) / n
            ca = sum((x - ma) * (y - mb) for x, y in zip(a_, b_))
            sa = math.sqrt(sum((x - ma) ** 2 for x in a_))
            sb = math.sqrt(sum((y - mb) ** 2 for y in b_))
            if sa > 0 and sb > 0:
                pairs.append(ca / (sa * sb))
    rho_bar = sum(pairs) / len(pairs)
    d_em = stats["ENS"]["ann_pp"] - stats["MOM"]["ann_pp"]
    pred = {
        "P1": {"pred": "corr(W52H,MOM) ∈ [0.5,0.9]", "got": round(c_wm, 3),
               "pass": bool(c_wm is not None and 0.5 <= c_wm <= 0.9)},
        "P2": {"pred": "ρ̄(V 15쌍) ∈ [−0.1,+0.4]", "got": round(rho_bar, 3),
               "pass": bool(-0.1 <= rho_bar <= 0.4)},
        "P3": {"pred": "V_ENS−V_MOM ∈ [−0.9,+0.1]%p", "got": round(d_em, 2),
               "pass": bool(-0.9 <= d_em <= 0.1)},
        "P4": {"pred": "ΔIR ∈ [−0.15,+0.15]", "got": round(d_ir, 3),
               "pass": bool(-0.15 <= d_ir <= 0.15)},
        "P5": {"pred": "V_AMAX ∈ [−0.6,+0.4]%p", "got": stats["AMAX"]["ann_pp"],
               "pass": bool(-0.6 <= stats["AMAX"]["ann_pp"] <= 0.4)},
    }

    sens = {}
    for name, kw in (("K015", {"k_tilt": 0.15}), ("monthly", {"monthly": True}),
                     ("cost20", {"cost": 0.0020})):
        r_ = run(dts, px, weeks, Z, rf, last_ym, ens_w, **kw)
        vd = [a - b for a, b in zip(r_["wk"]["ret"], V["R"]["wk"]["ret"])]
        irr, annv, _te = ir_of(vd, yrs)
        _m3, t3 = tstat(vd)
        sens[name] = {"ann_pp": round(annv * 100, 2), "ir": round(irr, 2), "t": round(t3, 2)}
    # Newey-West t(랙4) — ENS 전용(§5)
    vd = Vd["ENS"]
    mu = sum(vd) / n
    e0 = [x - mu for x in vd]
    g0 = sum(x * x for x in e0) / n
    nw = g0
    for L in range(1, 5):
        gl = sum(e0[i] * e0[i - L] for i in range(L, n)) / n
        nw += 2 * (1 - L / 5) * gl
    t_nw = mu / math.sqrt(nw / n)
    sens["NW_t_lag4"] = {"t": round(t_nw, 2)}

    verdict = ("주 판정: ΔIR %+.3f · 부트스트랩 p̂ %.2f · t(ENS) %.2f → %s"
               % (d_ir, p_hat, t_ens, cell))
    print()
    print("%-8s %8s %8s %8s %8s" % ("", "V연%p", "t", "TE%p", "IR"))
    for k in list(AXES) + ["ENS", "ANCHOR"]:
        s_ = stats[k]
        print("%-8s %8.2f %8.2f %8.2f %8.2f" % (k, s_["ann_pp"], s_["t"], s_["te_pp"], s_["ir"]))
    print(verdict)
    print("LOO(각 축 제외 ENS): ", {k: v["d_ir_vs_mom"] for k, v in loo.items()})
    print("예측 채점:")
    for k, v in pred.items():
        print("  %s %s %s" % (k, "✅" if v["pass"] else "❌", {a: b for a, b in v.items() if a != "pass"}))
    print("민감도:", sens)
    print("항등 검증:", idc)

    doc = {
        "note": "함대 — 무선별 6축 비중 틸트 배치(랭크-z·공통 엔터티 게이트·신호 패널 공유). "
                "주 판정은 사전 지명 챔피언(MOM) 대비 ΔIR + 블록 부트스트랩. "
                "PREREG-2026-08-20-FLEET.md 에 MC 기준선·검정력·가족 12건과 함께 계산 전 커밋. "
                "기준 비중 DB(커밋 금지) — 러너 재생산 불가(얼린 측정).",
        "prereg": "build/PREREG-2026-08-20-FLEET.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"k": K_TILT, "clip": Z_CLIP, "cost": COST, "min_axes": MIN_AXES,
                   "seed": SEED, "start": START, "scaling": "rank-z(전 축 · §1 새 선택)"},
        "span": [DD[0], DD[-1]], "weeks": len(weeks),
        "identity_checks": idc, "axis_dead_weeks": dead, "w52h_close_fallback": fb,
        "axes": {k: stats[k] for k in AXES}, "ens": stats["ENS"], "anchor_mom_rawz": stats["ANCHOR"],
        # 2026-08-20 점검 — R(순복제)·주요 판의 절대 지표를 저장한다. 종전엔 콘솔에만 있어
        #   web 의 교차 항등(I1)이 열쇠 부재로 공허 통과했다.
        "decomp": {"R": metrics(V["R"]["daily_d"], V["R"]["dv"], V["R"]["wk"]["ret"]),
                   "ENS": metrics(V["ENS"]["daily_d"], V["ENS"]["dv"], V["ENS"]["wk"]["ret"])},
        "main": {"d_ir": round(d_ir, 3), "boot_p": round(p_hat, 3), "t_ens": round(t_ens, 2),
                 "cell": cell, "verdict": verdict},
        "loo": loo, "predictions": pred, "sens": sens,
        "rho_bar_V": round(rho_bar, 3), "corr_w52h_mom": round(c_wm, 3),
        "flag_ref": metrics(V["FLAG"]["daily_d"], V["FLAG"]["dv"], V["FLAG"]["wk"]["ret"]),
        "weekly": {"d": [w["d0"] for w in weeks],
                   **{k: [round(x, 6) for x in Vd[k]] for k in list(AXES) + ["ENS"]}},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
