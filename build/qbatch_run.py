# -*- coding: utf-8 -*-
"""build/qbatch_run.py — 배치 Q 한 번 굽기 러너: 카드 모듈 run() → 부류별 주 통계 · 다중성(Bretz 그래프 · BH) · 관문 G2~G6 · 판정 → data/_qbatch.json

사전등록: build/PREREG-2026-09-25-QBATCH.md (관문 · 다중성 · 판정 표는 그 문서 §4~§5 와 이 파일이 같다).
카드 모듈은 계열 · 대조 · 위약 · 카드 고유 G4 만 낸다(scratchpad 계약) — 판정은 여기서 한 벌로 한다.

  python build/qbatch_run.py --dry           # 구조 점검: 모듈 selftest · dry · 그래프 재현(Holm 과 같은가) — 수익 없음
  QBATCH_COMMIT=<커밋> python build/qbatch_run.py
"""
from __future__ import annotations
import hashlib, importlib, io, json, math, os, subprocess, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q              # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_qbatch.json")
MARK = os.path.join(DATA, "_qbatch.started")
PREREG = "build/PREREG-2026-09-25-QBATCH.md"
MODULES = ["q_qmj", "q_riegk", "q_bmrot_leg", "q_switch", "q_jump", "q_absorb", "q_corrsurp", "q_vrp", "q_tsfm", "q_season",
           "q_eap", "q_ltd", "q_netper", "q_lib"]
RUN_MODULES = ["q_qmj", "q_riegk", "q_jump", "q_absorb", "q_corrsurp", "q_vrp", "q_tsfm", "q_season", "q_eap", "q_ltd", "q_netper", "q_lib"]
FROZEN = tuple("build/%s.py" % m for m in MODULES) + (
    "build/qbatch_core.py", "build/qbatch_run.py", PREREG, "build/PREREG-2026-09-25-QBATCH-CARDS.md", "build/eg30plus.py", "build/qg_lab.py", "build/pit_panel.py",
    "build/pit_quarantine.py", "build/stoploss.py", "build/tech_backtest.py", "build/rally_pattern.py", "build/index_members.py",
    "build/lib_loader.py", "build/lib_meta.py", "build/pit_backtest.py", "build/ml_core.py", "build/rrg.py",
    "data/pit_gics_sectors.json", "data/_eg_q5_scores_pitgics.json", "data/_eg_q5_scores_pitgics_pre.json", "data/_eg_q5_scores.json",
    "data/mech_episodes.json", "data/_eg_best.json", "data/_eg30plus.json", "data/_q07_ltd_fits.json")
SNAP, SNAP_FILES = "940f0bda", ("data/stocks.json", "data/pit_px.json", "data/sd")
SNAP_BASE = "bef4eea8"
BASE_FILES = ("data/bench_px.json", "data/rf_monthly.json", "data/index_history.json", "data/index_ledger.json",
              "data/pit_universe.json", "data/pit_reuse.json", "data/fx", "data/fx_pit", "data/assets.json",
              "data/splits.json", "data/shares_yf.json", "data/earn_dates.json", "data/strategy_charts.json", "data/strategy_index.json",
              "data/_pit_px_cache.json", "data/_pit_hl_cache.json")   # _pit_hl_cache: pit_backtest 가져올 때 읽는다(x-bmrot 과 무관 · 고정만)          # x-bmrot 수비 다리 가격 지도(pit_backtest.load_prices · blob f8c1a16b · q_bmrot_leg.verify_pins 도 단언)
ALPHA_LABEL, Q_BH = 0.025, 0.10

# ── F-Q 다중성 (사전등록 §5) ─────────────────────────────────────────────
PRIMARIES = ["Q01", "Q04", "Q05", "Q11", "Q16", "Q02", "Q07", "Q08", "Q03", "Q10"]
CHILDREN = {"Q13": "Q02"}                    # Q12 는 측정만(§6 — 목표 회전 10.76배/년이 G5 의 10배 상한을 넘는다는 것을 등록 전에 안다)
MEASURED_CHILD = {"Q12": "Q05"}               # 측정만 자식 — 카드의 짝 통계는 보고만
W0 = {"Q01": 1 / 8, "Q04": 1 / 8, "Q05": 1 / 8, "Q11": 1 / 8, "Q16": 1 / 8, "Q02": 1 / 8,
      "Q07": 1 / 16, "Q08": 1 / 16, "Q03": 1 / 16, "Q10": 1 / 16, "Q13": 0.0}
CLS = {"Q01": "A", "Q04": "A", "Q05": "A", "Q11": "A", "Q16": "S", "Q02": "B", "Q07": "B", "Q08": "B", "Q03": "S", "Q10": "S",
       "Q12": "M", "Q13": "C", "Q06": "M", "Q09": "M", "Q14": "D", "Q15": "D"}
NPERM_MIN = {"perm": 10000, "placebo": 1000}   # 굽기에서 뽑기 수가 이보다 적으면 멈춘다(연기 시험 덮어쓰기가 새지 않게)
SWITCH_COST_FLOOR = ("Q03", "Q10")            # 회전 10배 상한 대신 비용 끌림 바닥을 쓰는 교체(Q16 은 10배 상한을 그대로 받는다)
PASS_V = ("전방 진입", "in-sample 통과")
YEARS_MIN = {"A": 6, "B": 8}                 # G6 — 부류 A · Q16 은 6/11 · 부류 B · Q03 · Q10 은 8/11(V0 의 수)


def transitions():
    """Bretz 그래프 전이 행렬 — 문서 §5 그대로(자기 자신 0 · 행 합 1)."""
    nodes = PRIMARIES + list(CHILDREN)
    G = {i: {j: 0.0 for j in nodes} for i in nodes}
    for i in ("Q01", "Q04", "Q05", "Q11", "Q16"):
        for j in PRIMARIES:
            if j != i:
                G[i][j] = 1 / 9
    G["Q02"]["Q13"] = 1.0
    for ch, par in CHILDREN.items():
        for j in PRIMARIES:
            if j != par:
                G[ch][j] = 1 / 9
    for a, b in (("Q07", "Q08"), ("Q08", "Q07"), ("Q03", "Q10"), ("Q10", "Q03")):
        G[a][b] = 0.5
        others = [j for j in PRIMARIES if j not in (a, b)]
        for j in others:
            G[a][j] = 0.5 / len(others)
    for i in nodes:
        s = sum(G[i].values())
        assert abs(s - 1.0) < 1e-12 and G[i][i] == 0.0, (i, s)
    return G


def bretz(p, alpha=ALPHA_LABEL, w0=None, G=None):
    """Bretz · Maurer · Brannath · Posch (2009) 알고리즘 1 — 고정 행렬 · 가중 본페로니. p: {가설: 한쪽 p}. 돌려준다: 기각된 가설 순서 · 단계 기록."""
    w = dict(w0 or W0)
    G = {i: dict(r) for i, r in (G or transitions()).items()}
    live = [h for h in w if h in p and p[h] is not None]
    for h in list(w):
        if h not in live:                       # p 가 없는 가설(측정 불가)은 기각될 수 없다 — 무게는 남겨 두지 않고 그대로 둔다
            pass
    rejected, steps = [], []
    while True:
        cand = sorted([h for h in live if h not in rejected and w[h] > 0 and p[h] <= w[h] * alpha + 1e-15], key=lambda h: (p[h] / w[h], h))
        if not cand:
            break
        i = cand[0]
        rejected.append(i)
        steps.append({"reject": i, "p": p[i], "w": w[i], "alpha_i": w[i] * alpha})
        rest = [j for j in w if j != i and j not in rejected]
        nw = {j: w[j] + w[i] * G[i].get(j, 0.0) for j in rest}
        nG = {}
        for j in rest:
            nG[j] = {}
            for k in rest:
                if j == k:
                    nG[j][k] = 0.0
                    continue
                den = 1.0 - G[j].get(i, 0.0) * G[i].get(j, 0.0)
                nG[j][k] = (G[j].get(k, 0.0) + G[j].get(i, 0.0) * G[i].get(k, 0.0)) / den if den > 1e-15 else 0.0
        w = {**{h: 0.0 for h in rejected}, **nw}
        G = {**{h: {} for h in rejected}, **nG}
    return rejected, steps


def bh(p, q=Q_BH, family=PRIMARIES):
    """Benjamini–Hochberg(한쪽 p · q 0.10) — 1차 가설 10개. 돌려준다: 들어온 가설 집합 · k."""
    ps = sorted((p[h], h) for h in family if p.get(h) is not None)
    m = len(family)
    k = 0
    for r, (pv, h) in enumerate(ps, 1):
        if pv <= q * r / m + 1e-15:
            k = r
    return {h for _, h in ps[:k]}, k


# ── 통계 ─────────────────────────────────────────────────────────────────
def one_sided_p(t, df):
    from scipy.stats import t as T
    return None if t is None else float(T.sf(t, df))


def rf_pct(G, hold):
    return np.array([float(G.RF.get(h, 0.0)) * 100 for h in hold])


def sleeve_beta(fr):
    return float(np.cov(fr["index"], fr["basket"], ddof=1)[0, 1] / np.var(fr["index"], ddof=1))


def dbeta(fr, ref, G):
    """Δβ_t = (X_rule − X_ref) − 0.1 (β̂_rule − β̂_ref)(SPYTR − rf) — β̂ 는 120개월 슬리브 월 수익의 SPY 총수익 기울기."""
    rf = rf_pct(G, fr["hold"])
    return (fr["ex"] - ref["ex"]) - 0.1 * (sleeve_beta(fr) - sleeve_beta(ref)) * (fr["index"] - rf)


def hedged(fr, G):
    """H_t = X_t − 0.1 (β̂_s − 1)(SPYTR − rf)."""
    rf = rf_pct(G, fr["hold"])
    return fr["ex"] - 0.1 * (sleeve_beta(fr) - 1.0) * (fr["index"] - rf)


def halves_blocks(x, mask=None):
    """주 통계가 두 반 · 30개월 네 토막에서 > 0 인지(부류 B 는 하락월 안 평균)."""
    x = np.asarray(x, float)
    n = len(x)
    m = np.ones(n, bool) if mask is None else np.asarray(mask, bool)
    h1 = np.arange(n) < 60
    blk = np.arange(n) // 30
    mean = lambda sel: float(x[sel & m].mean()) if (sel & m).any() else None
    halves = [mean(h1), mean(~h1)]
    blocks = [mean(blk == q) for q in range(4)]
    ok = all(v is not None and v > 0 for v in halves) and sum(1 for v in blocks if v is not None and v > 0) >= 3
    return {"halves": halves, "blocks": blocks, "ok": ok}


def both_side(ex, hold):
    ME = Q.load("mech_episodes.json")
    pos = {h: j for j, h in enumerate(hold)}
    cm = [pos[m] for m in ME["months"]["crash_m"] if m in pos]
    sm = [pos[m] for m in ME["months"]["surge_m"] if m in pos]
    c, s = float(np.mean(ex[cm])), float(np.mean(ex[sm]))
    lab = "양면" if (c > 0 and s > 0) else ("급락형" if c > 0 else ("급등형" if s > 0 else "없음"))
    return {"crash_m": c, "surge_m": s, "label": lab}


def years_won(fr):
    yrs = {}
    for h, a, b in zip(fr["hold"], fr["fund"], fr["index"]):
        y = yrs.setdefault(h[:4], [1.0, 1.0])
        y[0] *= 1 + a / 100; y[1] *= 1 + b / 100
    ys = {y: (v[0] - v[1]) * 100 for y, v in sorted(yrs.items())}
    return int(sum(v > 0 for v in ys.values())), len(ys), ys


def dsr(ex, n_trials):
    """Deflated Sharpe(Bailey–López de Prado 2014) — 월 초과의 샤프 · 왜도 · 첨도 · 시행 수 N · 시행 간 SR 분산 ≈ 1/(T−1)(귀무 근사 · 보고만)."""
    from scipy.stats import norm, skew, kurtosis
    x = np.asarray(ex, float)
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    g3, g4 = float(skew(x)), float(kurtosis(x, fisher=False))
    emc = 0.5772156649
    v = 1.0 / (T - 1)
    sr0 = math.sqrt(v) * ((1 - emc) * norm.ppf(1 - 1.0 / n_trials) + emc * norm.ppf(1 - 1.0 / (n_trials * math.e))) if n_trials > 1 else 0.0
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr * sr))
    return {"N": n_trials, "sr_m": float(sr), "sr0": float(sr0), "dsr": float(norm.cdf((sr - sr0) * math.sqrt(T - 1) / den))}


def lite(fr, G):
    """fr → 싣는 모양(일간 경로 없이) + evaluate 지표."""
    ev = Q.evaluate(G, fr)
    return {"eval": ev, "ex": [round(float(v), 6) for v in fr["ex"]], "basket": [round(float(v), 6) for v in fr["basket"]],
            "index": [round(float(v), 6) for v in fr["index"]], "hold": fr["hold"], "turn": fr.get("turn")}


# ── 카드 판정 ─────────────────────────────────────────────────────────────
def judge_card(code, R, ctx, V0, V0_20, cards):
    """카드 하나의 주 통계 · p · 관문 G2~G6 — 문서 §3~§4."""
    cls = CLS.get(code, R.get("cls"))
    fr = R["fr"]
    G = ctx.A if fr.get("IX") is ctx.A.IX_TR or len(fr["IX"]) == len(ctx.A.dates) else ctx.G
    hold = fr["hold"]
    assert hold == V0["hold"], "%s 보유월이 V0 와 다르다" % code
    dm = ctx.dmask(hold)
    nd = int(dm.sum())
    ex = fr["ex"]
    out = {"code": code, "cls": cls, "n_down": nd}
    # 주 통계
    import eg30plus as E
    if cls == "A":
        t = E.nw_t(ex)
        out.update({"stat": "all-month mean X", "value": float(ex.mean()), "t": t, "df": len(ex) - 1, "p": one_sided_p(t, len(ex) - 1)})
        prim, pmask = ex, None
    elif cls == "B":
        import eg30plus as E
        d = dbeta(fr, V0, G)
        t = E.down_t(d, dm)
        out.update({"stat": "down-month mean Δβ(rule − V0)", "value": float(d[dm].mean()), "t": t, "df": nd - 1, "p": one_sided_p(t, nd - 1)})
        prim, pmask = d, dm
    elif cls == "S":
        D = R["controls"]["D"]
        d = ex - D["ex"]
        import eg30plus as E
        out.update({"stat": "all-month mean Δ^D (rule − D)", "value": float(d.mean()), "t": E.nw_t(d), "p": R.get("perm", {}).get("p"),
                    "p_source": "segment-shuffle permutation"})
        prim, pmask = d, None
    elif cls == "C":                                        # Q13 — Q02 대비 하락월 Δβ
        par = cards[CHILDREN[code]]["fr"]
        d = dbeta(fr, par, G)
        t = E.down_t(d, dm)
        out.update({"stat": "down-month mean Δβ(Q13 − Q02)", "value": float(d[dm].mean()), "t": t, "df": nd - 1, "p": one_sided_p(t, nd - 1)})
        prim, pmask = d, dm
    else:
        out.update({"stat": "측정만", "value": float(ex.mean()), "p": None})
        if cls == "M" and isinstance(R.get("log", {}).get("measured"), dict):
            out["measured"] = R["log"]["measured"]              # Q06 — Δ^D 전 월 · 하락월 · 규칙 − T1 · T2 · 순열 p · 위약(보고만)
        if code in MEASURED_CHILD:                              # Q12 — 카드의 짝 통계(Q05 대비 전체 월 Δ)를 보고만
            par = cards[MEASURED_CHILD[code]]["fr"]
            dd = ex - par["ex"]
            tt = E.nw_t(dd)
            out["measured_child"] = {"stat": "all-month mean Δ(Q12 − Q05)", "value": float(dd.mean()), "t": tt, "p": one_sided_p(tt, len(dd) - 1)}
        prim, pmask = ex, None
    # G2 양면(X) · 교체는 REBOUND-MISS(카드 모듈이 log.rebound_miss{months, n, mean_dD, applies, ok} 로 낸다 · 3달 미만이면 보고만)
    g2 = both_side(ex, hold)
    rm = R.get("log", {}).get("rebound_miss")
    if cls == "S" and isinstance(rm, dict):
        g2["rebound_miss"] = {"n": rm.get("n"), "mean_dD": rm.get("mean_dD"), "applies": bool(rm.get("applies"))}
        if rm.get("applies"):
            g2["rebound_miss_ok"] = bool(rm.get("ok"))
    out["G2"] = g2
    # G3 방어
    import eg30plus as E
    down_x = float(ex[dm].mean())
    g3 = {}
    if cls == "A" or code == "Q12":
        g3 = {"down_X_ge0": down_x >= 0, "down_H_gt0": float(hedged(fr, G)[dm].mean()) > 0}
    if code == "Q13":                                       # 카드: M1 = FE1(Q02) 을 Q13 의 연 초과로 희석한 판 대비 하락월(점) — 그 밖의 G3 없음
        _, dil = E.dilution(cards["Q02"]["fr"]["ex"], ex)
        g3 = {"M1": down_x > float(dil[dm].mean())}
    elif cls == "B" or code in ("Q03", "Q10"):
        ref_ex = V0["ex"]
        c, dil = E.dilution(ref_ex, ex)
        ev = Q.evaluate(G, fr)
        ev0 = Q.evaluate(G, V0)
        g3["M1"] = down_x > float(dil[dm].mean())
        g3["floor_ir"] = (ev["ir"] or -9) >= ev0["ir"] - 0.10
        g3["floor_ex"] = ev["ann_ex"] >= 0.5 * ev0["ann_ex"]
        g3["floor_te"] = ev["te"] <= 1.20
        if code in ("Q03", "Q10"):
            d = ex - R["controls"]["D"]["ex"]
            g3["down_dD_gt0"] = float(d[dm].mean()) > 0
            cd = R.get("log", {}).get("cost_drag")              # 슬리브 연 비용 끌림(소수 · 교체 비용 포함) — q_switch.class_s
            cd0 = R.get("log", {}).get("v0_cost_drag")          # 같은 장부 분해의 V0(소수 · 첫 매수 미과금 — 규칙과 같은 기준)
            if cd0 is None:
                cd0 = 2 * (V0.get("turn") or 0) * Q.COST        # 대체: V0 회전 기준(첫 매수 1회를 더 센다 · 연 0.01%p)
            g3["cost_drag"] = (cd is not None) and cd <= 2 * cd0
            g3["cost_drag_vals"] = {"rule": cd, "v0": cd0}      # 불리언이 아니라 gates_pass 가 세지 않는다
        else:
            g3["raw_down_ge0"] = float((ex - V0["ex"])[dm].mean()) >= 0
            g3["floor_turn"] = (fr.get("turn") is not None) and fr["turn"] <= 2 * (V0.get("turn") or 0)
    if code == "Q16":
        d = ex - R["controls"]["D"]["ex"]
        g3 = {"down_X_ge0": down_x >= 0, "down_dD_gt0": float(d[dm].mean()) > 0}
    for k, v in g3.items():                                 # 닫힌 실패 — 불리언이 아닌 관문 값은 멈춘다(*_vals 기록만 예외)
        if not k.endswith("_vals") and type(v) is not bool:
            raise SystemExit("🚨 %s G3[%s] 가 불리언이 아니다(%r)." % (code, k, v))
    out["G3"] = g3
    # G4 카드 고유
    out["G4"] = dict(R.get("g4", {}))
    for k, v in out["G4"].items():
        if type(v) is not bool:
            raise SystemExit("🚨 %s G4[%s] 가 불리언이 아니다(%r)." % (code, k, v))
    # G5 강건
    hb = halves_blocks(prim, pmask)
    f20 = R.get("fr20")
    if f20 is None and cls not in ("M", "D"):
        raise SystemExit("🚨 %s 에 20bp 판(fr20)이 없다." % code)
    g5 = {"halves_blocks": hb, "p20_gt0": False, "G2_20": False}
    if f20 is not None:
        if cls == "A":
            p20 = float(f20["ex"].mean())
        elif cls == "B":
            p20 = float(dbeta(f20, V0_20, G)[dm].mean())
        elif cls == "S":
            p20 = float((f20["ex"] - R["controls"]["D20"]["ex"]).mean())
        elif code == "Q13":
            p20 = float(dbeta(f20, cards["Q02"]["fr20"], G)[dm].mean())
        else:
            p20 = None
        g5["p20_gt0"] = (p20 is not None and p20 > 0)
        g5["p20"] = p20
        g5["G2_20"] = both_side(f20["ex"], hold)["label"] == g2["label"] if g2["label"] == "양면" else True
    turn = fr.get("turn")
    g5["turn_le_10x"] = (code in SWITCH_COST_FLOOR) or (turn is not None and turn <= 10.0)
    if code in ("Q01", "Q12"):
        g5["pff"] = R.get("log", {}).get("pff_same_sign", "pending")
    out["G5"] = g5
    # G6 해마다
    won, ny, ys = years_won(fr)
    need = YEARS_MIN["A"] if (cls == "A" or code in ("Q16", "Q12")) else YEARS_MIN["B"]
    if cls == "S" and R.get("perm"):                          # 러너의 t 와 모듈 순열의 t_obs 가 같은 Δ^D 인지(기록 · 1e-4 넘으면 등록 오류로 보고)
        out["perm_t_check"] = {"runner_t": out.get("t"), "module_t_obs": R["perm"].get("t_obs"),
                               "ok": (out.get("t") is not None and R["perm"].get("t_obs") is not None and abs(out["t"] - R["perm"]["t_obs"]) < 1e-4)}
    out["G6"] = {"won": won, "n": ny, "need": need, "ok": won >= need, "years": ys}
    out["f0"] = R.get("f0", {"ok": True})
    for k, v in R.get("label_caps", {}).items():
        if not isinstance(v, (bool, np.bool_)):
            raise SystemExit("🚨 %s label_caps[%s] 가 불리언이 아니다(%r)." % (code, k, v))
    out["label_caps"] = {k: bool(v) for k, v in R.get("label_caps", {}).items()}
    if R.get("log", {}).get("label_if_capped"):
        out["label_if_capped"] = R["log"]["label_if_capped"]
    return out


def gates_pass(j):
    """G3 · G4 · G5 · G6 가 모두 참인가(G2 는 따로)."""
    def allv(d):
        return all(v for k, v in d.items() if isinstance(v, bool))
    g5 = j["G5"]
    g5ok = g5["halves_blocks"]["ok"] and g5["p20_gt0"] and g5["G2_20"] and g5["turn_le_10x"] and g5.get("pff", True) is not False
    return allv(j["G3"]) and allv(j["G4"]) and g5ok and j["G6"]["ok"]


def verdicts(J, rejected, admitted):
    for code, j in J.items():
        if j["cls"] == "M" and not j["f0"].get("ok", True):
            j["verdict"] = "측정 불가"
            continue
        if j["cls"] in ("M", "D"):
            j["verdict"] = "측정만" if j["cls"] == "M" else "오염 측정(F-LIB 전방 판정)"
            continue
        if not j["f0"].get("ok", True):
            j["verdict"] = "측정 불가"
            continue
        sig_label, sig_fwd = code in rejected, code in admitted
        g2 = j["G2"]["label"]
        g2ok = (g2 == "양면") and j["G2"].get("rebound_miss_ok", True)
        rest = gates_pass(j)
        cap = any(j["label_caps"].values())
        if (sig_label or sig_fwd) and not g2ok and g2 in ("급락형", "급등형"):
            v = "한쪽형 — 측정만"
        elif sig_label and g2ok and rest:
            v = "in-sample 통과(측정만·전방 대기)"
        elif sig_fwd and g2ok and rest:
            v = "전방 진입"
        else:
            v = "기각"
        if cap and v in ("in-sample 통과(측정만·전방 대기)", "전방 진입"):
            v = (j["label_if_capped"] + " — 측정만") if j.get("label_if_capped") else "측정만(재포장 표시)"
        if v in ("in-sample 통과(측정만·전방 대기)", "전방 진입") and j["G5"].get("pff") == "pending":
            v += " — 최초 제출본 재실행이 같은 부호일 때만 전방 원장에 든다"
        if code == "Q02" and not j["G3"].get("floor_turn", True):
            v = "기각"
        if code in CHILDREN and v.startswith(PASS_V) and not J[CHILDREN[code]].get("verdict", "").startswith(PASS_V):
            v = "기각 — 부모가 통과하지 못했다"
        j["verdict"] = v
        j["sig"] = {"graph": sig_label, "bh": sig_fwd}


# ── 얼린 판 점검 ─────────────────────────────────────────────────────────
def _git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True)


def frozen_check():
    c = os.environ.get("QBATCH_COMMIT")
    if not c:
        raise SystemExit("🚨 QBATCH_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --dry 만 된다.")
    full = _git("rev-parse", c + "^{commit}").stdout.strip()
    added = _git("log", "--format=%H", "--diff-filter=A", full, "--", PREREG).stdout.split()
    if not added or added[-1] != full:
        raise SystemExit("🚨 %s 는 사전등록 문서를 처음 더한 커밋이 아니다." % full[:8])
    if _git("merge-base", "--is-ancestor", full, "origin/main").returncode != 0:
        raise SystemExit("🚨 사전등록 커밋이 origin/main 에 없다 — 먼저 푸시.")
    added_c = _git("log", "--format=%H", "--diff-filter=A", full, "--", "build/PREREG-2026-09-25-QBATCH-CARDS.md").stdout.split()
    if not added_c or added_c[-1] != full:
        raise SystemExit("🚨 카드 원문이 사전등록과 같은 커밋에 처음 들어가지 않았다.")
    rerun = os.environ.get("QBATCH_RERUN") or os.environ.get("QBATCH_RESUME")
    # 산출물이 한 번이라도 쓰였으면(여기든 origin 이든) 어떤 사유로도 다시 돌지 않는다 — 재실행 · 이어하기는 산출 전 기술적 중단에만
    if os.path.exists(OUT):
        raise SystemExit("🚨 산출물이 이미 있다 — 한 번 굽는 측정이다(다시 굽기는 새 등록).")
    for ref in ("origin/main:data/_qbatch.json", "origin/main:build/PREREG-2026-09-25-QBATCH-RESULT.md"):
        if _git("cat-file", "-e", ref).returncode == 0:
            raise SystemExit("🚨 %s 가 이미 커밋돼 있다 — 다시 굽기는 새 등록." % ref)
    if os.path.exists(MARK) and not rerun:
        raise SystemExit("🚨 시작 표식이 있다 — 산출 전 중단이면 QBATCH_RESUME(검문점 이어하기) 또는 QBATCH_RERUN(처음부터)=사유.")
    if rerun and not os.path.exists(MARK):
        raise SystemExit("🚨 재실행 · 이어하기는 시작 표식(산출 전 중단)이 있을 때만이다.")
    if rerun and not io.open(MARK, encoding="utf-8").read().startswith(full):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    if _git("diff", "--quiet", SNAP, "--", *SNAP_FILES).returncode != 0:
        raise SystemExit("🚨 가격 판이 %s 가 아니다." % SNAP)
    if _git("diff", "--quiet", SNAP_BASE, "--", *BASE_FILES).returncode != 0:
        raise SystemExit("🚨 가격 밖 입력이 %s 와 다르다." % SNAP_BASE)
    for p in FROZEN:
        if not os.path.exists(os.path.join(ROOT, p)):
            raise SystemExit("🚨 %s 가 없다." % p)
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True).stdout
        have = open(os.path.join(ROOT, p), "rb").read()
        if want.replace(b"\r\n", b"\n") != have.replace(b"\r\n", b"\n"):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    import scipy
    if scipy.__version__ != "1.18.1" or np.__version__ != "2.5.3":
        raise SystemExit("🚨 scipy/numpy 판이 다르다.")
    if os.environ.get("PYTHONHASHSEED") != "0" or os.environ.get("OPENBLAS_NUM_THREADS") != "1":
        raise SystemExit("🚨 PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 로 돌려라(부동소수 합 순서 · BLAS 스레드 고정 — 사전등록 §11).")
    return full


def _js(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o.item() if hasattr(o, "item") else (sorted(o) if isinstance(o, set) else (list(o) if isinstance(o, tuple) else str(o)))


def _sha_lf(path):
    return hashlib.sha256(open(path, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def dry() -> int:
    """구조 점검 — 그래프가 동일가중일 때 Holm 과 같은가 · 모듈 selftest · V0 재현(수익 수준은 공개 판만). 모듈 dry 는 각 모듈에서 따로."""
    # 그래프 단위 시험: 가중 동일 · 전이 균등이면 Holm 과 같다
    hs = ["H%d" % i for i in range(5)]
    Gm = {i: {j: (0.0 if i == j else 1 / 4) for j in hs} for i in hs}
    w = {h: 1 / 5 for h in hs}
    ok_all = True
    for trial in range(200):
        rng = np.random.default_rng(Q.SEED + trial)
        p = {h: float(x) for h, x in zip(hs, rng.uniform(0, 0.06, 5))}
        rej, _ = bretz(p, 0.05, w, Gm)
        srt = sorted(hs, key=lambda h: p[h])
        holm = []
        for r, h in enumerate(srt):
            if p[h] <= 0.05 / (5 - r):
                holm.append(h)
            else:
                break
        ok_all &= set(rej) == set(holm)
    print("그래프 = Holm(동일가중 · 균등 전이) 200회: %s" % ok_all)
    transitions()
    ctx = Q.Ctx()
    E = __import__("eg30plus")
    v0 = ctx.V0()
    q = E.quick(ctx.Wd, ctx.V0_targets)
    print("V0 재현(ctx ↔ eg30plus.quick) 월 최대 차 %.1e" % float(np.max(np.abs(v0["ex"] - q["ex"]))))
    bad = 0
    for m in MODULES:
        try:
            mod = importlib.import_module(m)
        except Exception as e:
            print("  ✗ %s 가져오기 실패: %s" % (m, e)); bad += 1; continue
        st = mod.selftest() if hasattr(mod, "selftest") else {"ok": None}
        print("  %s selftest %s" % (m, st.get("ok")))
        bad += st.get("ok") is False
    return 0 if (ok_all and bad == 0) else 1


def main() -> int:
    t0 = time.time()
    commit = frozen_check()
    resume = os.environ.get("QBATCH_RESUME")
    if os.environ.get("QBATCH_RERUN") or resume:
        started = io.open(MARK, encoding="utf-8").read().strip()           # 처음 시작 시각을 그대로
    else:
        started = "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
        io.open(MARK, "w", encoding="utf-8").write(started + "\n")       # 무엇보다 먼저 — 도중에 죽어도 한 번 굽기가 지켜진다
    import eg30plus as E
    ctx = Q.Ctx()
    V0 = ctx.V0()
    V0_20 = ctx.V0(cost=0.0020)
    dm0 = ctx.dmask(V0["hold"])                                          # 하락월 집합 재확인(등록 값)
    hb0 = halves_blocks(np.ones(len(dm0)), dm0)
    cnt = lambda sel: int((sel & dm0).sum())
    n = len(dm0)
    if not (int(dm0.sum()) == 39 and [cnt(np.arange(n) < 60), cnt(np.arange(n) >= 60)] == [15, 24]
            and [cnt((np.arange(n) // 30) == q) for q in range(4)] == [7, 8, 13, 11]):
        raise SystemExit("🚨 하락월 집합이 등록 값(39 · 15/24 · 7/8/13/11)과 다르다.")
    # 고정 대조를 긴 계산 전에 — 모듈 가져오기(q_lib DEP_SHA) · x-bmrot 핀 · Q07 적합 지문
    mods = {m: importlib.import_module(m) for m in RUN_MODULES}
    import q_bmrot_leg, q_ltd
    q_bmrot_leg.verify_pins(ctx)
    pin = q_ltd._pinned()
    if pin is None or q_ltd.manifest(pin) != q_ltd.FITS_MANIFEST:
        raise SystemExit("🚨 Q07 얼린 적합 파일의 지문이 다르다.")
    for m, mod in mods.items():
        if hasattr(mod, "NPERM") and mod.NPERM and mod.NPERM < (NPERM_MIN["perm"] if m in ("q_jump", "q_absorb", "q_corrsurp", "q_vrp") else NPERM_MIN["placebo"]):
            raise SystemExit("🚨 %s.NPERM = %s — 등록 값보다 적다." % (m, mod.NPERM))
    pub = json.load(io.open(os.path.join(DATA, "_eg30plus.json"), encoding="utf-8"))["results_TR"]["V0"]["monthly_ex"]
    gap = float(np.max(np.abs(np.array(pub) - V0["ex"])))
    if gap > 1e-4:
        raise SystemExit("🚨 V0 가 공개 EG30+ V0 를 재현하지 못했다(월 최대 차 %.2e)." % gap)
    cards, mods_log = {}, {}
    import pickle
    import shutil
    ck = os.environ.get("QBATCH_CKPT_DIR") or os.path.join(os.environ.get("TEMP", DATA), "qbatch_ckpt", commit[:12])
    #   모듈 결과 검문점 — 산출 전 기술적 중단에서만 QBATCH_RESUME=사유 로 다시 쓴다(머리: 커밋 · 모듈 sha · NPERM · 해시 씨앗 · BLAS · JSON 에 남는다)
    if not resume and os.path.isdir(ck):
        shutil.rmtree(ck)
    os.makedirs(ck, exist_ok=True)
    for m in RUN_MODULES:
        t1 = time.time()
        mod = mods[m]
        f = os.path.join(ck, m + ".pkl")
        hdr = {"commit": commit, "sha": _sha_lf(os.path.join(HERE, m + ".py")), "nperm": getattr(mod, "NPERM", None),
               "hashseed": os.environ.get("PYTHONHASHSEED"), "blas": os.environ.get("OPENBLAS_NUM_THREADS")}
        if resume and os.path.exists(f):
            blob = pickle.load(open(f, "rb"))
            if blob.get("hdr") != hdr:
                raise SystemExit("🚨 %s 검문점 머리가 지금과 다르다(%s ≠ %s)." % (m, blob.get("hdr"), hdr))
            R = blob["R"]
            mods_log[m] = {"sec": 0.0, "cards": sorted(R), "resumed": True}
        else:
            R = mod.run(ctx)
            pickle.dump({"hdr": hdr, "R": R}, open(f + ".tmp", "wb"), protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(f + ".tmp", f)
            mods_log[m] = {"sec": round(time.time() - t1, 1), "cards": sorted(R)}
        for code, r in R.items():
            if code in cards:
                raise SystemExit("🚨 %s 를 두 모듈이 냈다." % code)
            cards[code] = r
        print("  %s → %s (%.0f초)" % (m, sorted(R), time.time() - t1), flush=True)
    if set(cards) != set(CLS):
        raise SystemExit("🚨 카드 집합이 등록과 다르다: 빠짐 %s · 더함 %s" % (sorted(set(CLS) - set(cards)), sorted(set(cards) - set(CLS))))
    for code, R in cards.items():                              # 뽑기 수 — 연기 시험 덮어쓰기가 굽기로 새지 않게
        if CLS[code] == "D":
            continue
        pm = R.get("perm") or {}
        if CLS[code] == "S" and not (pm.get("n", 0) >= NPERM_MIN["perm"] and len(pm.get("t_perm") or []) >= NPERM_MIN["perm"]):
            raise SystemExit("🚨 %s 순열 뽑기 수가 %s 다." % (code, pm.get("n")))
        for nm, pl in (R.get("placebo") or {}).items():
            if isinstance(pl, dict) and pl.get("draws") is not None and len(pl["draws"]) < NPERM_MIN["placebo"]:
                raise SystemExit("🚨 %s 위약 %s 뽑기 수가 %d 다." % (code, nm, len(pl["draws"])))
    J = {}
    for code in sorted(cards):
        if CLS.get(code) == "D":
            J[code] = {"code": code, "cls": "D", "lib": cards[code].get("lib"), "f0": cards[code].get("f0", {"ok": True}), "label_caps": {}}
            continue
        J[code] = judge_card(code, cards[code], ctx, V0, V0_20, cards)
    p = {c: J[c].get("p") for c in PRIMARIES + list(CHILDREN) if c in J}
    for c in list(p):                                    # F0 미달(측정 불가) 카드는 그래프 · BH 에 들지 않는다(BH 의 m 은 10 그대로)
        if not J[c]["f0"].get("ok", True):
            p[c] = None
    rejected, steps = bretz({c: v for c, v in p.items() if v is not None})
    admitted, kbh = bh(p)
    verdicts(J, set(rejected), admitted)
    for ch, par in CHILDREN.items():                    # 자식의 전방 진입 — 부모의 판정이 통과이고 자식 p ≤ 0.10 이고 관문 통과(고정 순서)
        if ch in J and J[par]["verdict"].startswith(PASS_V) and (p.get(ch) is not None and p[ch] <= Q_BH) and gates_pass(J[ch]):
            admitted.add(ch)
    verdicts(J, set(rejected), admitted)
    for code, j in J.items():
        if j["cls"] not in ("D",):
            fr = cards[code]["fr"]
            j["dsr"] = [dsr(fr["ex"], n) for n in (10, 45, 700)]
    G_of = lambda fr: ctx.A if len(fr["IX"]) == len(ctx.A.dates) else ctx.G
    store = {}
    for code, R in cards.items():
        if CLS.get(code) == "D":
            store[code] = {k: v for k, v in R.items() if k not in ("fr", "fr_pr", "fr20", "controls", "arms")}
            continue
        store[code] = {"rule": lite(R["fr"], G_of(R["fr"])), "rule_pr": lite(R["fr_pr"], G_of(R["fr_pr"])) if R.get("fr_pr") else None,
                       "rule_20bp": lite(R["fr20"], G_of(R["fr20"])) if R.get("fr20") else None,
                       "controls": {k: lite(v, G_of(v)) for k, v in R.get("controls", {}).items()},
                       "arms": {k: lite(v, G_of(v)) for k, v in R.get("arms", {}).items()},
                       "placebo": R.get("placebo"), "perm": R.get("perm"),
                       "g4": R.get("g4"), "label_caps": R.get("label_caps"), "f0": R.get("f0"), "targets_hash": R.get("targets_hash"),
                       "log": R.get("log")}
    import pandas, scipy
    out = {"prereg": PREREG, "prereg_commit": commit, "started": started, "rerun": os.environ.get("QBATCH_RERUN"), "resume": os.environ.get("QBATCH_RESUME"),
           "versions": {"numpy": np.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__},
           "data_snapshot": SNAP, "data_base": SNAP_BASE, "v0_gap": gap, "modules": mods_log,
           "env": {"PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"), "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS")},
           "p": p, "graph": {"alpha": ALPHA_LABEL, "rejected": rejected, "steps": steps, "w0": W0},
           "bh": {"q": Q_BH, "k": kbh, "admitted": sorted(admitted)}, "judged": J, "cards": store,
           "V0": lite(V0, ctx.G)}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=_js) + "\n")
    print("\n카드 | 부류 | 주 통계 | 값 | t | p | 양면 | 판정")
    for code in sorted(J):
        j = J[code]
        if j["cls"] == "D":
            print("%s | D | 라이브러리(오염 측정) | — | — | — | — | %s" % (code, j.get("verdict")))
            continue
        print("%s | %s | %s | %+.4f | %s | %s | %s | %s" % (code, j["cls"], j["stat"], j["value"], "%.2f" % j["t"] if j.get("t") is not None else "—",
                                                       "%.4f" % j["p"] if j.get("p") is not None else "—", j["G2"]["label"], j.get("verdict")))
    print("그래프 기각 %s · BH k=%d 진입 %s (%.0f초)" % (rejected, kbh, sorted(admitted), time.time() - t0))
    return 0


if __name__ == "__main__":
    if "--dry" in sys.argv:
        sys.exit(dry())
    sys.exit(main())
