# -*- coding: utf-8 -*-
"""build/v_audit.py — 배치 V 허용 목록 감사(별도 프로세스): 엔진의 복사 부품 ↔ 원본 짝맞춤(합성 입력 · 1e−12).

설계 원본(구속): vbatch_research.json final.build_plan.modules[v_audit](«허용 목록: 복사 부품 ↔ 원본 짝맞춤(합성 입력 · 1e−12) · R1/R2 개수 짝맞춤 ·
  별도 프로세스 · 굽기 전에 한 번») · no_import_rule(원본 짝맞춤은 허용 목록의 별도 감사 프로세스에서만) · D22 · estimator.selftests(«u_core 복사 부품의 원본 짝맞춤»).

이 프로세스만 원본(u_core · u_tests · t_core · eg30plus · qbatch_run)을 부른다 — 굽기 · 연기 프로세스는 부르지 않는다(v_guard G-NoEG 가 대상 폐포에서 본다).
  u_core · u_tests 는 저장소에 없다(배치 U 작업 사본 · 취소된 EG30 계보) → 파일 경로로 불러 SHA 를 적는다($VBATCH_U_SRC · 없으면 %TEMP%/ubatch_wt/build).
  원본이 합성 입력에서 부르는 경로에 EG 계보가 끼어 있어도(t_core.h1 → eg30plus.nw_t) 이 프로세스 안에서만이다.
짝맞춤 범위(이번 판): v_core(slope_path · pi_matrix · lw_corr · _lw_corr_batch · rhat_series · band · direction_eval[R2 끔 · 가닥 = 군] · proj_box_sum0 · lw_cc_cov ·
  sigma_series · execute_a · drift · a_path · pct01 · _group_cap · cap_book · net_book · no_derivative_positions · fund_x · cost_rate · _turn_arrays) ·
  v_tests(nw_t · h1 · by_info · year_table · blocks4 · bundle 공통 칸 · dsr). 🔎 R1/R2 개수 짝맞춤(v_ins ↔ r_r1_flags · v_ear ↔ r_r2flags)은 **짓지 않았다**
  (배치 R 빌더 · 중간 자료를 굽기 전에 다시 돌려야 해 이 등록 범위 밖 — 공개). 그래서 등록은 «INS 의 OS · EAR 의 CH 는 R1 · R2 와 한 번만 센다» 를 주장하지 않고
  V04 · V05 팔을 누적 N 에 따로 센다(보수 · 등록 §2.3 · §8.4).

  python build/v_audit.py            짝맞춤 전부(합성 입력만 · 실자료 없음)
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import math
import os
import sys
import tempfile
import traceback

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
U_SRC = os.environ.get("VBATCH_U_SRC") or os.path.join(tempfile.gettempdir(), "ubatch_wt", "build")
TOL = 1e-12


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _eq(a, b, tol=TOL):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        return False
    na, nb = np.isnan(a), np.isnan(b)
    return bool((na == nb).all() and np.allclose(a[~na], b[~nb], atol=tol, rtol=0))


def audit():
    sys.path.insert(0, U_SRC)
    uc = _load("u_core", os.path.join(U_SRC, "u_core.py"))
    import v_core as C
    import v_tests as VT
    rows = []
    rng = np.random.default_rng(20260925)

    def chk(name, fn):
        try:
            ok = bool(fn())
            rows.append((name, ok, None))
        except Exception as e:
            rows.append((name, False, "%s: %s" % (type(e).__name__, str(e)[:160])))

    T = 400
    z = np.full(T, np.nan)
    z[12:] = np.clip(rng.normal(0, 1, T - 12), -2, 2)
    y = rng.normal(0, 0.04, T)
    y[:5] = np.nan

    def c_slope():
        for kw in ({}, {"wls": False}, {"stambaugh": False}, {"shrink": False, "trunc": False}, {"min_pairs": 240, "nw_lag": 12}):
            a, b = C.slope_path(z, y, +1, **kw), uc.slope_path(z, y, +1, **kw)
            if not all(_eq(a[k], b[k]) for k in ("n", "b_hat", "b_corr", "se", "b_shr", "b_c")):
                return False
        return True
    chk("slope_path", c_slope)
    act = rng.random((50, 5)) > 0.3
    fam = ["a", "a", "b", "c", "c"]
    chk("pi_matrix", lambda: all(_eq(C.pi_matrix(act, fam, ["char"] * 5, md), uc.pi_matrix(act, fam, ["char"] * 5, md)) for md in ("family", "flat")))
    X = rng.standard_normal((120, 4))
    chk("lw_corr", lambda: _eq(C.lw_corr(X)[0], uc.lw_corr(X)[0]) and abs(C.lw_corr(X)[1] - uc.lw_corr(X)[1]) <= TOL)
    chk("_lw_corr_batch", lambda: _eq(C._lw_corr_batch(X[None]), uc._lw_corr_batch(X[None])))
    Z = rng.standard_normal((300, 3))
    Z[:40, 2] = np.nan
    A3 = np.isfinite(Z)
    chk("rhat_series", lambda: _eq(C.rhat_series(Z, A3), uc.rhat_series(Z, A3)))
    uu = rng.normal(0, 1.5, 200)
    chk("band", lambda: _eq(C.band(uu), uc.band(uu)))

    def c_dir():
        Zf = np.clip(rng.normal(0, 1, (120, 4)), -2, 2)
        Bc = np.abs(rng.normal(0.05, 0.03, (120, 4))) * np.array([1, -1, 1, 1])
        ac = rng.random((120, 4)) > 0.2
        sg = [1, -1, 1, 1]
        fm = ["a", "b", "b", "c"]
        a = C.direction_eval(Zf, Bc, ac, sg, fm, [0, 1, 2, 3], r2="off")
        b = uc.direction_eval(Zf, Bc, ac, sg, fm, ["char"] * 4, r2=False)
        ok = _eq(a["u"], b["u"]) and _eq(a["v"], b["v"]) and _eq(a["D"], b["D"])
        # 가닥마다 제 군 · 활성 가닥 ≥ 2 인 달은 군 R2 = 옛 가닥 R2(설계대로 다른 것은 활성 1 인 달뿐 — 절반 강도)
        a2 = C.direction_eval(Zf, Bc, ac, sg, fm, [0, 1, 2, 3], r2="cluster")
        b2 = uc.direction_eval(Zf, Bc, ac, sg, fm, ["char"] * 4, r2=True)
        m2 = a2["n_clusters_act"] >= 2
        return ok and _eq(a2["v"][m2], b2["v"][m2])
    chk("direction_eval(R2 끔 · 가닥 = 군)", c_dir)
    xx = rng.normal(0, 0.1, 6)
    chk("proj_box_sum0", lambda: _eq(C.proj_box_sum0(xx, 0.075), uc.proj_box_sum0(xx, 0.075)))
    chk("lw_cc_cov", lambda: _eq(C.lw_cc_cov(X)[0], uc.lw_cc_cov(X)[0]))
    L4 = rng.normal(0, 0.03, (200, 4))
    chk("sigma_series", lambda: _eq(C.sigma_series(L4), uc.sigma_series(L4)))
    w5 = np.array([0.6, 0.1, 0.1, 0.1, 0.1])
    wd = np.array([0.55, 0.12, 0.08, 0.13, 0.12])
    tg = np.array([0.62, 0.05, 0.13, 0.12, 0.08])
    chk("execute_a", lambda: all(_eq(C.execute_a(wd, tg, w5, trade_max=tm)[0], uc.execute_a(wd, tg, w5, trade_max=tm)[0]) for tm in (0.2, 0.01)))
    rr = rng.normal(0, 0.05, 5)
    chk("drift", lambda: _eq(C.drift(w5, rr)[0], uc.drift(w5, rr)[0]) and abs(C.drift(w5, rr)[1] - uc.drift(w5, rr)[1]) <= TOL)
    TG = np.tile(tg, (30, 1))
    TG[10] = np.nan
    RR = rng.normal(0, 0.04, (30, 5))
    chk("a_path", lambda: all(_eq(C.a_path(TG, RR, w5)[k], uc.a_path(TG, RR, w5)[k]) for k in ("w", "S", "traded")))
    vals = {str(i): (None if i % 7 == 0 else float(v)) for i, v in enumerate(rng.integers(0, 5, 40))}
    chk("pct01", lambda: C.pct01(vals) == uc.pct01(vals))
    ww = rng.dirichlet(np.ones(12))
    gg = np.array([0, 0, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    chk("_group_cap", lambda: _eq(C._group_cap(ww, np.zeros(12), gg, 0.1)[0], uc._group_cap(ww, np.zeros(12), gg, 0.1)[0]))
    N = {"k%d" % i: float(v) for i, v in enumerate(ww)}
    chk("cap_book", lambda: C.cap_book(N, lambda k: k, cap=0.1) == uc.cap_book(N, lambda k: k, cap=0.1))
    holds = [({"a": 0.5, "b": 0.5}, 0.0), ({"b": 0.3, "c": 0.7}, 0.0)]
    chk("net_book", lambda: C.net_book([0.4, 0.6], holds, lambda k: k, cap=0.1) == uc.net_book([0.4, 0.6], holds, lambda k: k, cap=0.1))
    pos = [("stock", "AAPL"), ("stock", "ES=F"), ("french_leg", "x"), ("cash", "RF"), ("stock", "SPY251219C00600000")]
    chk("no_derivative_positions", lambda: C.no_derivative_positions(pos)[0] == uc.no_derivative_positions(pos)[0] and
        C.no_derivative_positions(pos)[1] == uc.no_derivative_positions(pos)[1])
    ut = _load("u_tests", os.path.join(U_SRC, "u_tests.py"))
    import t_core as TC
    import eg30plus as E
    import qbatch_run as QR
    idx = pd.period_range("1990-01", periods=240, freq="M")
    S = pd.Series(rng.normal(0.008, 0.05, 240), index=idx)
    B = pd.Series(rng.normal(0.008, 0.045, 240), index=idx)
    tr = pd.Series(np.abs(rng.normal(0.2, 0.1, 240)), index=idx)
    rate = pd.Series(TC.cost_rate(idx), index=idx)
    chk("fund_x", lambda: _eq(C.fund_x(S, B, rate, tr), ut.fund_x(S, B, rate, tr)) and _eq(C.fund_x(S, B, rate, tr, mult=2.0), ut.fund_x(S, B, rate, tr, mult=2.0)))
    chk("cost_rate", lambda: _eq(C.cost_rate_L(pd.period_range("1970-01", "2026-08", freq="M")), TC.cost_rate(pd.period_range("1970-01", "2026-08", freq="M"))))
    Wm = rng.dirichlet(np.ones(3), 50)
    R0 = rng.normal(0, 0.04, (50, 3))
    val = rng.random(50) > 0.1
    chk("_turn_arrays", lambda: _eq(C._turn_arrays(Wm, R0, val), TC._turn_arrays(Wm, R0, val, np.ones(3, bool), np.ones(3, bool), np.zeros(3, bool))[0]))
    x = S.to_numpy()
    chk("nw_t", lambda: all(abs(VT.nw_t(x, L) - E.nw_t(x, L)) <= TOL for L in (3, 6, 12)))
    chk("h1", lambda: all((VT.h1(S)[k] == TC.h1(S)[k]) or abs(VT.h1(S)[k] - TC.h1(S)[k]) <= TOL for k in ("n", "mean", "t", "t12", "p")))
    pv = {"a": 0.001, "b": 0.02, "c": None, "d": 0.3}
    chk("by_info", lambda: VT.by_info(pv)["admitted"] == TC.by_info(pv, m=len(pv))["admitted"])
    chk("year_table", lambda: VT.year_table(S - B, B) == TC.year_table(S - B, B))
    chk("blocks4", lambda: VT.blocks4(S) == TC.blocks4(S))

    def c_bundle():
        sig = float(B.std())
        f = (lambda i, _b=None: (B.reindex(i) < 0).to_numpy(), lambda i, _b=None: (B.reindex(i) <= -sig).to_numpy(),
             lambda i, _b=None: (B.reindex(i) >= sig).to_numpy())
        legs = [{"side": "crash", "a": "1995-03-01", "b": "1995-09-30", "months": VT._months_between("1995-03-01", "1995-09-30")}]
        reb = [{"a": "1996-01-01", "b": "1996-04-30", "months": VT._months_between("1996-01-01", "1996-04-30")}]
        ev_v = VT.Events("F", *f, legs, reb, sig)
        ev_t = TC.Events("F", *f, legs, reb, [], sig)
        a, b = VT.bundle(S - B, B, ev_v), TC.bundle(S - B, B, ev_t)
        keys = ("down", "up", "crash_m", "surge_m", "named", "years", "roll36_neg", "blocks4", "universe_breaks")
        ok = all(a[k] == b[k] for k in keys)
        ok &= all(a["h1"][k] == b["h1"][k] or abs(a["h1"][k] - b["h1"][k]) <= TOL for k in ("n", "mean", "t", "p"))
        ok &= a["crash_legs"]["n"] == b["crash_legs"]["n"] and a["rebounds"]["n"] == b["rebounds"]["n"]
        return ok
    chk("bundle(공통 칸)", c_bundle)
    chk("dsr", lambda: abs(VT.dsr(x, 963)["dsr"] - QR.dsr(x, 963)["dsr"]) <= TOL)
    return rows, {"u_core": _sha(os.path.join(U_SRC, "u_core.py")), "u_tests": _sha(os.path.join(U_SRC, "u_tests.py"))}


def main():
    rows, shas = audit()
    for nm, ok, err in rows:
        print("  %s %-34s %s" % ("✓" if ok else "✗", nm, err or ""))
    print("원본 SHA: %s" % json.dumps({k: v[:12] for k, v in shas.items()}, ensure_ascii=False))
    n_ok = sum(1 for r in rows if r[1])
    print("v_audit 짝맞춤 %d/%d(허용 목록 별도 프로세스 · 합성 입력 · 1e−12)" % (n_ok, len(rows)))
    return 0 if n_ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
