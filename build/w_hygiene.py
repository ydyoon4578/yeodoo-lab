# -*- coding: utf-8 -*-
"""build/w_hygiene.py — 배치 W 굽기 전 위생 다섯(명세 evaluation.hygiene_before_bake · D11): 눈가림 연기 · 라벨 섞기 누수 · 심은 신호 복원 ·
선견 이동 검사 · 커버리지 F0(개수만) — 모두 fail-closed 묶음(run_all).

설계 원본(구속): wbatch_research.json final.evaluation.hygiene_before_bake ·
  «눈가림 연기: y 를 씨앗 잡음으로 바꿔 구조 · 시점만» ·
  «라벨 섞기 누수: 달 안 y 섞기 200회 · |t| ≥ 1.96 이 19회 이상이면 실패(깨끗한 파이프라인 오경보 0.6% · 옛 20회 중 19회 규칙은 23% 오경보)» ·
  «심은 신호 복원: 같은 차원의 합성 y 에만 IC 0.02 를 심고 20회 중 16회 이상 t ≥ 1.645» ·
  «선견 이동 검사: 결정 200개에서 t 로 자른 자료의 신호 = 전체 자료의 신호(V 방식)» ·
  data_plan.coverage_gates_F0 «W 달 커버리지(시총 · 가격 ≥ 0.95)» · common_frame.tier1_months(배치 R 목록 T 117 · 2016-08 · 2018-02 · 2018-05 빠짐과의 일치 보고).

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  H1 눈가림: y 의 결측 자리는 그대로 두고 선 자리만 N(0, scale²) 씨앗 잡음으로 바꾼다(scale 기본 8 = %/월 단위 · 배치 R 연기와 같다) ·
     실행 함수는 산출을 저장소 밖 임시 폴더(캐시 blind/)에만 쓰고, 연기는 그 파일을 **열지 않고** 이름 · 크기만 센 뒤 지운다 ·
     돌려받은 값은 형(type) 이름만 적는다(값을 읽지 않는다).
  H2 라벨 섞기: 달마다 y 가 선 행끼리만 섞는다(결측 자리 유지) · 씨앗 default_rng(seed + i) · 통계 함수가 None 을 주면 그 회는 «적중 아님»이 아니라
     실패로 센다(fail-closed · 통계가 서지 않는 파이프라인은 위생을 못 넘는다).
     🔁 등록 전 보정(비평 1 C1 · H3): 통계 함수가 dict 를 주면 **적중 = 그 회의 두쪽 야생 부트스트랩 p(w_stagem S11 · B 999) < 0.05** — 명세 «|t| ≥ 1.96 이
     200 회 중 19 회 이상이면 실패 · 깨끗한 파이프라인 오경보 0.6%» 는 회마다 크기가 정확히 5% 라는 가정이다. NW(3) t 를 1.96 에 대면 T 119 에서 크기가
     6.2%(FM) · 7.5 ~ 8.0%(W10m 교차항) · 11.6 ~ 17.3%(W11 교차항)라 깨끗한 파이프라인이 4 ~ 99.9% 로 멈춘다 — 부트스트랩 p 로 회마다 크기를 5% 로 맞춘다
     (문턱 200 · 19 · 0.05 는 명세 그대로). 숫자를 주는 옛 통계 함수는 |t| ≥ crit(selftest 호환).
  H3 심은 신호: y_i = d·IC·u_i + √(1 − IC²)·e_i · u = 신호 순위의 정규 점수(Φ⁻¹((r + ½)/n)) · e ~ N(0, 1) · 신호 값만 쓰고 실제 수익은 읽지 않는다.
     🔁 등록 전 보정(비평 1 H3): resid_of 를 주면 u 를 **그 카드 FM 의 통제 기저로 잔차화한 뒤 단위 분산으로** 심는다(u⊥ · 설계 밖 행 0) — 명세 «같은 차원의
     합성 y 에 IC 0.02» 를 FM γ 가 실제로 재는 방향(통제로 설명되지 않는 몫)에 심는다. 원 u 에 심으면 t 가 √(1 − R²) 로 줄어(통제와의 R² 0.7 · 0.8 · 0.85 에서
     20 회 중 16 회 통과 확률 0.58 · 0.10 · 0.01) 깨끗한 파이프라인이 멈춘다. 통과 규칙(20 회 중 16 회 · d·t ≥ 1.645)은 명세 그대로.
  H6 🔁 카드 범위(등록 전 · 비평 1 H3): 라벨 섞기 · 심은 신호는 카드마다 판정한다 — 한 카드가 못 넘으면 **그 카드**의 가족 p 는 없음(분모에 남는다 · 기각 · 표시 없음) ·
     파이프라인 전체 검사(눈가림 · 선견 · 커버리지 F0)가 못 넘으면 굽기 전체가 멈춘다(run_all_scoped).
  H4 선견: 결정 달을 씨앗으로 min(200, 전부) 개 고르고(정렬) · 두 신호의 NaN 자리 같고 값 차이 ≤ tol(기본 0 = 비트까지 같다).
  H5 커버리지: 달마다 가격 · 시총이 선 멤버 몫(개수) ≥ 0.95 ∧ 덮인 시총 몫 ≥ 0.95 — 개수 · 비율만(수익 없음).

🚨 실자료 y 가 드는 검사(라벨 섞기 누수)는 kind 를 받아 w_core.assert_kind_allowed 를 지난다 — 등록 커밋 전에는 synth · blind 만.
   눈가림 연기 · 심은 신호 · 선견 · 커버리지는 실제 수익을 읽지 않는다.

  python build/w_hygiene.py --selftest
"""
from __future__ import annotations

import copy
import math
import os
import shutil
import sys
import tempfile
import time
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import w_core as WC          # noqa: E402

LEAK_N, LEAK_CRIT, LEAK_FAIL_HITS = 200, 1.96, 19
LEAK_P, LEAK_B = 0.05, 999                            # H2 🔁 회마다 두쪽 야생 부트스트랩 p < 0.05 · 반복 999
PLANT_IC, PLANT_REPS, PLANT_NEED, PLANT_T = 0.02, 20, 16, 1.645
LOOKAHEAD_N = 200
COV_THR = 0.95
R_TIER1_FAIL = ("2016-08", "2018-02", "2018-05")        # 배치 R 커버리지 F0 에서 빠진 결정 달(비교 보고)
BLIND_SCALE = 8.0


# ══════════════════════════════════════════════════════════════════════════
#  H1 눈가림 연기
# ══════════════════════════════════════════════════════════════════════════
def blind_panel(panel, seed, scale=BLIND_SCALE):
    """panel = {"kind", "months": [...], "m": {달: {"y": 배열, …}}} → y 를 씨앗 잡음으로 바꾼 사본(kind = "blind")."""
    rng = np.random.default_rng(seed)
    out = {k: v for k, v in panel.items() if k != "m"}
    out["m"] = {}
    for m in panel["months"]:
        D = panel["m"].get(m)
        if D is None:
            continue
        y = np.asarray(D["y"], float)
        ok = np.isfinite(y)
        yb = np.full(len(y), np.nan)
        yb[ok] = rng.normal(0.0, scale, int(ok.sum()))
        E = dict(D)
        E["y"] = yb
        out["m"][m] = E
    out["kind"] = "blind"
    out["blind_seed"] = seed
    return out


def blind_smoke(run, panel, seed, scale=BLIND_SCALE):
    """눈가림 연기 — run(blind_panel, out_dir) 을 끝까지 돌리고 산출을 열지 않고 지운다. 돌려주는 것 {ok, sec, n_files, bytes, deleted, err, returned}."""
    base = WC.cache_dir("blind")
    tmp = tempfile.mkdtemp(prefix="wb_blind_", dir=base)
    t0 = time.time()
    err, rtype = None, None
    try:
        pb = blind_panel(panel, seed, scale)
        r = run(pb, tmp)
        rtype = type(r).__name__
        del r
    except SystemExit as e:
        err = "SystemExit: %s" % str(e)[:300]
    except Exception as e:                                                   # noqa: BLE001
        err = "%s: %s" % (type(e).__name__, str(e)[:300])
    n_files, n_bytes = 0, 0
    for dp, _, fns in os.walk(tmp):
        for fn in fns:
            n_files += 1
            n_bytes += os.path.getsize(os.path.join(dp, fn))              # 크기만 — 열지 않는다
    shutil.rmtree(tmp, ignore_errors=True)
    deleted = not os.path.exists(tmp)
    return {"ok": err is None and deleted, "sec": round(time.time() - t0, 2), "n_files": n_files, "bytes": n_bytes, "deleted": deleted,
            "err": err, "returned": rtype, "rule": "y → 씨앗 잡음 · 산출은 열지 않고 지운다"}


# ══════════════════════════════════════════════════════════════════════════
#  H2 라벨 섞기 누수
# ══════════════════════════════════════════════════════════════════════════
def shuffle_y(panel, rng):
    out = {k: v for k, v in panel.items() if k != "m"}
    out["m"] = {}
    for m in panel["months"]:
        D = panel["m"].get(m)
        if D is None:
            continue
        y = np.asarray(D["y"], float).copy()
        ok = np.flatnonzero(np.isfinite(y))
        y[ok] = y[ok[rng.permutation(len(ok))]]
        E = dict(D)
        E["y"] = y
        out["m"][m] = E
    return out


def label_shuffle_leak(stat, panel, seed, n=LEAK_N, crit=LEAK_CRIT, fail_hits=LEAK_FAIL_HITS):
    """stat(panel) → 주 통계 t(파이프라인 전체 · 신호 · 설계 · FM · NW). 달 안 y 섞기 n 회에서 |t| ≥ crit 가 fail_hits 번 이상이면 실패.
    패널 kind 로 자물쇠(실자료는 등록 커밋 뒤)."""
    WC.assert_kind_allowed(panel.get("kind"), "w_hygiene.label_shuffle_leak")
    hits, none, mode = 0, 0, None
    for i in range(n):
        r = stat(shuffle_y(panel, np.random.default_rng(seed + i)))
        if isinstance(r, dict):                                          # H2 🔁 부트스트랩 p
            mode = "p"
            p = r.get("p_wild_two")
            if p is None or not (p == p):
                none += 1
            elif p < LEAK_P:
                hits += 1
            continue
        mode = mode or "t"
        t = r
        if t is None or not (t == t):
            none += 1
        elif abs(t) >= crit:
            hits += 1
    ok = hits < fail_hits and none == 0
    if mode == "p":
        rule = "달 안 y 섞기 %d회 · 두쪽 야생 부트스트랩 p < %.2f 가 %d회 이상이면 실패 · p 가 서지 않는 회가 있으면 실패" % (n, LEAK_P, fail_hits)
    else:
        rule = "달 안 y 섞기 %d회 · |t| ≥ %.2f 가 %d회 이상이면 실패 · t 가 서지 않는 회가 있으면 실패" % (n, crit, fail_hits)
    return {"ok": ok, "hits": hits, "none": none, "n": n, "crit": crit, "fail_hits": fail_hits, "mode": mode, "rule": rule}


# ══════════════════════════════════════════════════════════════════════════
#  H3 심은 신호 복원
# ══════════════════════════════════════════════════════════════════════════
def normal_scores(z):
    from scipy.stats import norm
    z = np.asarray(z, float)
    out = np.full(len(z), np.nan)
    ok = np.flatnonzero(np.isfinite(z))
    if len(ok):
        r = np.empty(len(ok))
        r[np.argsort(z[ok], kind="stable")] = np.arange(len(ok))
        out[ok] = norm.ppf((r + 0.5) / len(ok))
    return out


def plant_panel(panel, signal_key, ic, direction, rng, resid_of=None):
    """합성 y 패널 — 같은 달 · 같은 행 · 같은 신호(signal_key) · y 만 심은 신호 + 잡음(실제 수익은 읽지 않는다).
    resid_of(m, D, u) → 통제로 잔차화한 단위 분산 u⊥(H3 🔁 · 설계 밖 행 0)."""
    out = {k: v for k, v in panel.items() if k != "m"}
    out["m"] = {}
    for m in panel["months"]:
        D = panel["m"].get(m)
        if D is None:
            continue
        u = normal_scores(D[signal_key])
        if resid_of is not None:
            u = resid_of(m, D, u)
        e = rng.normal(0.0, 1.0, len(u))
        y = direction * ic * np.nan_to_num(u) + math.sqrt(1 - ic * ic) * e
        E = dict(D)
        E["y"] = y
        out["m"][m] = E
    out["kind"] = "synth"
    return out


def planted_recovery(stat, panel, signal_key, direction, seed, ic=PLANT_IC, reps=PLANT_REPS, need=PLANT_NEED, t_min=PLANT_T, resid_of=None):
    """심은 신호 — reps 회 가운데 d·t ≥ t_min 이 need 회 이상이면 통과. stat(panel) → 주 통계 t(또는 {"t": …}) · resid_of = H3 🔁 잔차화 심기."""
    good, ts = 0, []
    for i in range(reps):
        r = stat(plant_panel(panel, signal_key, ic, direction, np.random.default_rng(seed + i), resid_of=resid_of))
        t = r.get("t") if isinstance(r, dict) else r
        ts.append(t)
        if t is not None and t == t and direction * t >= t_min:
            good += 1
    how = "통제로 잔차화한 방향" if resid_of is not None else "원 신호"
    return {"ok": good >= need, "good": good, "reps": reps, "need": need, "ic": ic, "direction": direction, "residualized": resid_of is not None,
            "rule": "합성 y 에 IC %.3f 를 심고(%s) %d회 중 %d회 이상 방향 t ≥ %.3f" % (ic, how, reps, need, t_min)}


def residualizer(design_of):
    """H3 🔁 — design_of(m, D) → 그달 FM 설계(w_stagem.design 꼴: ctrl · idx) | None · 돌려주는 resid_of(m, D, u) 는 u 를 통제 기저로 잔차화해
    단위 분산으로(설계 밖 행 0)."""
    def resid_of(m, D, u):
        import w_stagem as S
        d = design_of(m, D)
        out = np.zeros(len(u))
        if d is None or len(d["idx"]) < 3:
            return out
        Q, _, _ = S.basis(d["ctrl"])
        v = np.nan_to_num(np.asarray(u, float)[d["idx"]])
        r = v - Q @ (Q.T @ v)
        sd = float(r.std())
        if sd > 0:
            out[d["idx"]] = r / sd
        return out
    return resid_of


# ══════════════════════════════════════════════════════════════════════════
#  H4 선견 이동 검사
# ══════════════════════════════════════════════════════════════════════════
def _same(a, b, tol):
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k], tol) for k in a)
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        return False
    na, nb = np.isnan(a), np.isnan(b)
    if not (na == nb).all():
        return False
    d = np.abs(a[~na] - b[~nb])
    return bool((d <= tol).all()) if d.size else True


def lookahead_shift(signal_at, data, truncate, decisions, seed, n=LOOKAHEAD_N, tol=0.0):
    """결정 t 마다 signal_at(truncate(data, t), t) == signal_at(data, t). decisions 에서 씨앗으로 min(n, 전부) 개(정렬)."""
    ds = sorted(decisions)
    if len(ds) > n:
        rng = np.random.default_rng(seed)
        ds = sorted(rng.choice(ds, n, replace=False).tolist())
    bad = []
    for t in ds:
        a = signal_at(truncate(data, t), t)
        b = signal_at(data, t)
        if not _same(a, b, tol):
            bad.append(t)
    return {"ok": not bad and len(ds) > 0, "n": len(ds), "n_bad": len(bad), "bad": bad[:5],
            "rule": "결정 %d개 · t 로 자른 자료의 신호 = 전체 자료의 신호(허용 %g)" % (len(ds), tol)}


# ══════════════════════════════════════════════════════════════════════════
#  H5 커버리지 F0(개수 · 비율만)
# ══════════════════════════════════════════════════════════════════════════
def coverage_f0(rows, thr=COV_THR, r_fail=R_TIER1_FAIL, window=None):
    """rows = {결정 달: {"n": 멤버 수, "n_px": 가격 · 시총이 선 멤버 수, "cap": 덮개 시총(이음 포함), "cap_px": 덮인 시총}}.
    달 판정 = n_px/n ≥ thr ∧ cap_px/cap ≥ thr. 돌려주는 것 {months, fail, T, by_month(비율), vs_R}."""
    use, fail, by = [], [], {}
    for m in sorted(rows):
        if window and not (window[0] <= m <= window[1]):
            continue
        r = rows[m]
        cn = (r["n_px"] / r["n"]) if r.get("n") else None
        cc = (r["cap_px"] / r["cap"]) if r.get("cap") else None
        ok = cn is not None and cc is not None and cn >= thr and cc >= thr
        by[m] = {"cov_n": cn, "cov_cap": cc, "use": ok}
        (use if ok else fail).append(m)
    rs = sorted(set(r_fail) & set(by))
    return {"months": use, "fail": fail, "T": len(use), "by_month": by, "thr": thr,
            "vs_R": {"R_fail": list(r_fail), "same_fail": sorted(fail) == rs, "only_W": sorted(set(fail) - set(r_fail)),
                     "only_R": sorted(set(rs) - set(fail))}}


# ══════════════════════════════════════════════════════════════════════════
#  묶음(fail-closed)
# ══════════════════════════════════════════════════════════════════════════
PIPELINE_GATES = ("blind_smoke", "lookahead_shift", "coverage_f0")
CARD_GATES = ("label_shuffle_leak", "planted_recovery")


def run_all_scoped(results, cards):
    """H6 🔁 — 파이프라인 검사(눈가림 · 선견 · 커버리지)는 굽기 전체 · 카드 검사(라벨 섞기 · 심은 신호 — results[이름][카드])는 그 카드만.
    돌려주는 것 {ok(파이프라인), missing, failed, card_ok{카드: bool}, card_failed{카드: [검사]}}."""
    miss = [k for k in PIPELINE_GATES + CARD_GATES if k not in results]
    bad = [k for k in PIPELINE_GATES if k in results and (results[k] or {}).get("ok") is not True]
    card_ok, card_bad = {}, {}
    for c in cards:
        fb = [g for g in CARD_GATES if ((results.get(g) or {}).get(c) or {}).get("ok") is not True]
        card_ok[c] = not fb and not miss
        if fb:
            card_bad[c] = fb
    return {"ok": not miss and not bad, "missing": miss, "failed": bad, "card_ok": card_ok, "card_failed": card_bad,
            "n": len(PIPELINE_GATES) + len(CARD_GATES), "rule": "H6 — 파이프라인 검사 실패 = 굽기 멈춤 · 카드 검사 실패 = 그 카드 p 없음"}


def run_all(results):
    """위생 결과 {이름: {ok, …}} → 모두 참이어야 굽는다. 빠진 검사는 실패(다섯 모두 있어야 한다)."""
    need = ("blind_smoke", "label_shuffle_leak", "planted_recovery", "lookahead_shift", "coverage_f0")
    miss = [k for k in need if k not in results]
    bad = [k for k in need if k in results and (results[k] or {}).get("ok") is not True]
    return {"ok": not miss and not bad, "missing": miss, "failed": bad, "n": len(need)}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 자료만)
# ══════════════════════════════════════════════════════════════════════════
def _synth_panel(seed, T=60, n=300, beta=0.0, kind="synth"):
    rng = np.random.default_rng(seed)
    months = WC.months_between("2016-08", WC.mshift("2016-08", T - 1))
    P = {"kind": kind, "months": months, "m": {}}
    for m in months:
        sec = np.array(["S%d" % (i % 8) for i in range(n)], object)
        z = rng.normal(0, 1, n)
        y = beta * z + rng.normal(0, 8, n)
        y[rng.random(n) < 0.02] = np.nan
        P["m"][m] = {"y": y, "z": z, "sec": sec, "log_me": rng.normal(10, 1, n), "r1": rng.normal(0, 8, n), "mom": rng.normal(0, 20, n),
                     "val": rng.normal(0, 1, n)}
    return P


def _stat_fm(P):
    import w_stagem as S
    res = S.fm(P["months"], lambda m: [S.stage_m_w_design(P["m"][m], [("z", P["m"][m]["z"])])], ["z"], P["kind"])
    return S.summarize(res["months"], res["g"]["z"], +1)["nw_t"]


def _stat_leaky(P):
    """누수 파이프라인 — 신호를 y 로 만든다(섞인 y 를 그대로 신호로 써서 섞어도 t 가 크다)."""
    import w_stagem as S
    res = S.fm(P["months"], lambda m: [S.stage_m_w_design(P["m"][m], [("z", np.nan_to_num(P["m"][m]["y"]) + P["m"][m]["z"])])], ["z"], P["kind"])
    return S.summarize(res["months"], res["g"]["z"], +1)["nw_t"]


def _st_blind():
    P = _synth_panel(WC.SEED, T=24)

    def run(pb, out):
        assert pb["kind"] == "blind"
        with open(os.path.join(out, "x.json"), "w", encoding="utf-8") as f:
            f.write('{"t": %r}' % _stat_fm(pb))
        return {"t": 1.0}
    r = blind_smoke(run, P, WC.SEED)
    assert r["ok"] and r["n_files"] == 1 and r["deleted"] and r["returned"] == "dict", r
    pb = blind_panel(P, WC.SEED)
    m0 = P["months"][0]
    assert np.array_equal(np.isnan(pb["m"][m0]["y"]), np.isnan(P["m"][m0]["y"]))
    assert not np.allclose(np.nan_to_num(pb["m"][m0]["y"]), np.nan_to_num(P["m"][m0]["y"]))
    assert np.array_equal(pb["m"][m0]["z"], P["m"][m0]["z"]) and P["kind"] == "synth"      # 원본은 그대로
    pb2 = blind_panel(P, WC.SEED)
    assert np.array_equal(np.nan_to_num(pb["m"][m0]["y"]), np.nan_to_num(pb2["m"][m0]["y"]))

    def boom(pb, out):
        raise RuntimeError("부러짐")
    r2 = blind_smoke(boom, P, WC.SEED)
    assert not r2["ok"] and "RuntimeError" in r2["err"] and r2["deleted"]
    # 실자료 패널도 눈가림 뒤에는 kind = blind(자물쇠를 지난다)
    Pr = dict(P, kind="real")
    r3 = blind_smoke(lambda pb, out: _stat_fm(pb), Pr, WC.SEED)
    assert r3["ok"], r3
    return "y → 씨앗 잡음(결측 자리 유지 · 재현) · 산출 열지 않고 삭제 · 오류 잡음 · 실자료 → blind 자물쇠 통과"


def _st_leak():
    P = _synth_panel(WC.SEED + 1, T=48, beta=0.0)
    r = label_shuffle_leak(_stat_fm, P, WC.SEED, n=60)
    assert r["ok"] and r["hits"] < 10, r
    r2 = label_shuffle_leak(_stat_leaky, P, WC.SEED, n=30, fail_hits=19)
    assert not r2["ok"] and r2["hits"] >= 19, r2
    r3 = label_shuffle_leak(lambda P: None, P, WC.SEED, n=3)
    assert not r3["ok"] and r3["none"] == 3
    try:
        label_shuffle_leak(_stat_fm, dict(P, kind="real"), WC.SEED, n=1)
        raise AssertionError("등록 전 실자료 누수 검사 통과")
    except SystemExit:
        pass
    # 섞기는 결측 자리를 지키고 값 집합을 보존
    s = shuffle_y(P, np.random.default_rng(1))
    m0 = P["months"][0]
    a, b = P["m"][m0]["y"], s["m"][m0]["y"]
    assert np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(np.sort(a[~np.isnan(a)]), np.sort(b[~np.isnan(b)]))
    # 규칙 오경보(이항 · 명세 0.6%)
    from scipy.stats import binom
    assert abs(binom.sf(18, 200, 0.05) - 0.006) < 0.003
    return "깨끗한 파이프라인 통과 · 누수 파이프라인 적발(≥ 19) · t 없음 = 실패 · 실자료 자물쇠 · 섞기 보존 · 규칙 오경보 %.4f" % binom.sf(18, 200, 0.05)


def _st_plant():
    P = _synth_panel(WC.SEED + 2, T=117, n=450)                               # 명세 차원(T 117 · 약 450종)
    r = planted_recovery(_stat_fm, P, "z", +1, WC.SEED)                       # 명세 규칙 그대로: 20회 중 16회
    assert r["ok"] and r["reps"] == 20 and r["need"] == 16, r
    rn = planted_recovery(_stat_fm, P, "z", -1, WC.SEED, reps=6, need=5)      # 방향 인자
    assert rn["ok"], rn

    def broken(Pp):                                                          # 신호를 한 달 밀어 쓰는 깨진 파이프라인 → 복원 못 함
        import w_stagem as S
        ms = Pp["months"]
        res = S.fm(ms[1:], lambda m: [S.stage_m_w_design(dict(Pp["m"][m], z=Pp["m"][WC.mshift(m, -1)]["z"]),
                                                          [("z", Pp["m"][WC.mshift(m, -1)]["z"])])], ["z"], Pp["kind"])
        return S.summarize(res["months"], res["g"]["z"], +1)["nw_t"]
    rb = planted_recovery(broken, P, "z", +1, WC.SEED, reps=6, need=5)
    assert not rb["ok"], rb
    u = normal_scores([3.0, 1.0, np.nan, 2.0])
    assert np.isnan(u[2]) and u[1] < u[3] < u[0]
    # 심은 IC 가 실제로 ≈ 0.02
    import w_stagem as S
    pp = plant_panel(P, "z", 0.02, +1, np.random.default_rng(3))
    ics = [S.rank_ic(pp["m"][m]["z"], pp["m"][m]["y"]) for m in P["months"]]
    assert abs(np.mean(ics) - 0.02) < 0.012, np.mean(ics)
    return "심은 IC 0.02 복원(방향 ±) · 깨진(한 달 밀린) 파이프라인 적발 · 정규 점수 · 심은 IC 크기"


def _st_lookahead():
    rng = np.random.default_rng(WC.SEED + 3)
    months = WC.months_between("2009-01", "2026-08")
    px = {m: rng.normal(0, 0.05, 50) for m in months}

    def trunc(d, t):
        return {m: v for m, v in d.items() if m <= t}

    def good(d, t):                                                          # 12-2 모멘텀(t 까지 자료)
        ms = [WC.mshift(t, -k) for k in range(2, 13)]
        if not all(m in d for m in ms):
            return np.full(50, np.nan)
        return np.sum([d[m] for m in ms], axis=0)

    def leaky(d, t):                                                         # t+1 을 들여다본다
        n1 = WC.mshift(t, 1)
        return good(d, t) + (d[n1] if n1 in d else 0.0)
    dec = months[:-1]
    r = lookahead_shift(good, px, trunc, dec, WC.SEED)
    assert r["ok"] and r["n"] == 200, r
    r2 = lookahead_shift(leaky, px, trunc, dec, WC.SEED)
    assert not r2["ok"] and r2["n_bad"] >= 180, r2                             # 이력이 모자란 앞 달(둘 다 NaN)만 같다
    r3 = lookahead_shift(lambda d, t: {"a": good(d, t), "b": np.array([1.0])}, px, trunc, dec, WC.SEED, n=20)
    assert r3["ok"]
    assert not lookahead_shift(good, px, trunc, [], WC.SEED)["ok"]            # 결정이 없으면 통과가 아니다
    return "결정 200 · 깨끗한 신호 통과 · t+1 엿봄 적발(%d/200) · dict 신호 · 빈 결정 = 실패" % r2["n_bad"]


def _st_coverage():
    rows = {}
    for m in WC.months_between("2016-08", "2026-07"):
        rows[m] = {"n": 500, "n_px": 490, "cap": 100.0, "cap_px": 99.0}
    for m in R_TIER1_FAIL:
        rows[m] = {"n": 500, "n_px": 400, "cap": 100.0, "cap_px": 99.0}
    c = coverage_f0(rows)
    assert c["T"] == 117 and c["vs_R"]["same_fail"] and c["fail"] == list(R_TIER1_FAIL)
    rows["2020-03"] = {"n": 500, "n_px": 490, "cap": 100.0, "cap_px": 90.0}
    c2 = coverage_f0(rows)
    assert c2["T"] == 116 and not c2["vs_R"]["same_fail"] and c2["vs_R"]["only_W"] == ["2020-03"]
    rows["2021-01"] = {"n": 0, "n_px": 0, "cap": 0, "cap_px": 0}
    assert "2021-01" in coverage_f0(rows)["fail"]
    agg = run_all({"blind_smoke": {"ok": True}, "label_shuffle_leak": {"ok": True}, "planted_recovery": {"ok": True},
                   "lookahead_shift": {"ok": True}, "coverage_f0": {"ok": True}})
    assert agg["ok"]
    assert not run_all({"blind_smoke": {"ok": True}})["ok"] and not run_all(dict.fromkeys(
        ("blind_smoke", "label_shuffle_leak", "planted_recovery", "lookahead_shift"), {"ok": True}) | {"coverage_f0": {"ok": None}})["ok"]
    return "커버리지 0.95 두 축(개수 · 시총) · R 목록(T 117 · 3달) 일치 보고 · 빈 달 실패 · 묶음 fail-closed(빠짐 · None)"


def _st_scoped():
    """H2 · H3 · H6 🔁 — 부트스트랩 p 모드 누수(깨끗 통과 · 누수 적발) · 잔차화 심기(통제와 겹친 신호도 복원) · 카드 범위 묶음."""
    import w_stagem as S
    P = _synth_panel(WC.SEED + 5, T=60, n=300)

    def stat_p(Pp):
        res = S.fm(Pp["months"], lambda m: [S.stage_m_w_design(Pp["m"][m], [("z", Pp["m"][m]["z"])])], ["z"], Pp["kind"])
        return S.family_fm(res["months"], res["g"]["z"], +1, 199, WC.SEED)

    def stat_leaky_p(Pp):
        res = S.fm(Pp["months"], lambda m: [S.stage_m_w_design(Pp["m"][m], [("z", np.nan_to_num(Pp["m"][m]["y"]) + Pp["m"][m]["z"])])], ["z"], Pp["kind"])
        return S.family_fm(res["months"], res["g"]["z"], +1, 199, WC.SEED)
    r = label_shuffle_leak(stat_p, P, WC.SEED, n=40, fail_hits=19)
    assert r["ok"] and r["mode"] == "p" and r["hits"] < 8, r
    r2 = label_shuffle_leak(stat_leaky_p, P, WC.SEED, n=20, fail_hits=15)
    assert not r2["ok"] and r2["hits"] >= 15, r2
    # 잔차화 심기: 신호 z 가 통제 mom 과 거의 같은 경우(R² ≈ 0.9) — 원 u 심기는 t 가 작고 잔차화 심기는 크다
    Q = copy.deepcopy(P)
    rng = np.random.default_rng(WC.SEED + 6)
    for m in Q["months"]:
        D = Q["m"][m]
        D["z"] = D["mom"] / 20.0 + rng.normal(0, 0.33, len(D["mom"]))
    des = lambda m, D: S.stage_m_w_design(D, [("z", D["z"])])
    stat_t = lambda Pp: S.summarize(*(lambda res: (res["months"], res["g"]["z"]))(
        S.fm(Pp["months"], lambda m: [S.stage_m_w_design(Pp["m"][m], [("z", Pp["m"][m]["z"])])], ["z"], Pp["kind"])), +1)["nw_t"]
    t_raw = stat_t(plant_panel(Q, "z", 0.02, +1, np.random.default_rng(1)))
    t_res = stat_t(plant_panel(Q, "z", 0.02, +1, np.random.default_rng(1), resid_of=residualizer(des)))
    assert t_res > t_raw + 1.0 and t_res > 2.0, (t_raw, t_res)
    pr = planted_recovery(stat_t, Q, "z", +1, WC.SEED, reps=6, need=5, resid_of=residualizer(des))
    assert pr["ok"] and pr["residualized"], pr
    # 카드 범위 묶음
    good = {"ok": True}
    rs = run_all_scoped({"blind_smoke": good, "lookahead_shift": good, "coverage_f0": good,
                         "label_shuffle_leak": {"A1": good, "A2": {"ok": False}}, "planted_recovery": {"A1": good, "A2": good}}, ("A1", "A2"))
    assert rs["ok"] and rs["card_ok"] == {"A1": True, "A2": False} and rs["card_failed"] == {"A2": ["label_shuffle_leak"]}, rs
    rs2 = run_all_scoped({"blind_smoke": {"ok": False}, "lookahead_shift": good, "coverage_f0": good,
                          "label_shuffle_leak": {"A1": good}, "planted_recovery": {"A1": good}}, ("A1",))
    assert not rs2["ok"] and rs2["failed"] == ["blind_smoke"]
    assert not run_all_scoped({"blind_smoke": good}, ("A1",))["ok"]
    return "부트스트랩 p 모드 누수(깨끗 %d/40 · 누수 %d/20 적발) · 잔차화 심기 t %.1f(원 %.1f · 통제 R² ≈ 0.9) · 카드 범위 묶음(파이프라인 멈춤 · 카드 p 없음)" % (
        r["hits"], r2["hits"], t_res, t_raw)


def selftest():
    res, ok = [], True
    for fn in (_st_blind, _st_leak, _st_plant, _st_lookahead, _st_coverage, _st_scoped):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_hygiene selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
