# -*- coding: utf-8 -*-
"""build/eg_best.py — EG30(금융 판정 시점정확) 기저 · 모멘텀 통합 후보 둘 · 다른 전략과 반반 섞기 넷, 사전등록 선택 규칙 → data/_eg_best.json

사전등록: build/PREREG-2026-09-24-EGBEST.md
엔진: build/qg_lab.py (World · sleeve · evaluate)

🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.
🚨 순서: ① 사전등록 커밋과 이 파일·엔진·등록문·Eg 점수가 같은지 본다(EGBEST_COMMIT) ② 얼린 Eg 로 돌린 EG_FROZEN 이 FUNDMIX 의 E 를
  재현하는지 본다(연 초과·IR ±0.01) — 못 하면 후보를 돌리지 않고 멈춘다 ③ 기저 EG_BASE(시점정확 GICS Eg) · 후보 · 섞기 · 참고.

  돌리는 곳은 자료 판 작업 사본(snap_wt)이다 — 저장소 HEAD 의 stocks.json 은 자료 판이 아니라 ④ 에서 멈춘다.
  사전등록 커밋을 푸시한 뒤 작업 사본에 **그 경로들만** 꺼내 온다(전체 checkout 금지 — 자료 판 파일이 덮인다):
    git -C <snap_wt> checkout <커밋> -- build/PREREG-2026-09-24-EGBEST.md build/eg_best.py build/qg_lab.py build/eg_q5.py
        build/pit_gics.py data/_eg_q5_scores_pitgics.json data/pit_gics.json
    EGBEST_COMMIT=<사전등록 커밋> python build/eg_best.py
"""
from __future__ import annotations
import io, json, math, os, subprocess, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402
import qg_lab as QL                   # noqa: E402
import rally_pattern as RP            # noqa: E402  nw_t

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "_eg_best.json")
MIX = os.path.join(ROOT, "data", "_fund_mix.json")
PREREG = "build/PREREG-2026-09-24-EGBEST.md"
FROZEN = ("build/qg_lab.py", "build/eg_best.py", "build/eg_q5.py", PREREG, "data/_eg_q5_scores_pitgics.json",
          "build/pit_gics.py", "data/pit_gics.json",
          "build/pit_panel.py", "build/pit_quarantine.py", "build/stoploss.py", "build/tech_backtest.py", "build/rally_pattern.py",
          "data/_fund_mix.json", "data/_eg_q5_scores.json")
SNAP = "940f0bda"                                                  # 자료 판(사전등록 §2) — frozen_check 가 실제로 대조한다
SNAP_FILES = ("data/stocks.json", "data/pit_px.json", "data/sd")
SNAP_BASE = "bef4eea8"                                             # 작업 사본의 나머지 입력(가격 밖)이 선 커밋
BASE_FILES = ("data/bench_px.json", "data/rf_monthly.json", "data/index_history.json", "data/index_ledger.json",
              "data/pit_universe.json", "data/pit_reuse.json", "data/fx", "data/fx_pit")
MARK = os.path.join(ROOT, "data", "_eg_best.started")              # 한 번 굽기 표식 — 결과가 찍히기 전에 쓴다
EG = {"signals": ["eg"], "weights": {"eg": 1}, "smooth": 1, "n": 30, "wt": "cap", "cap": 0.20, "reb": 3,
      "index": "union", "ex_fin": False, "eg": "pitgics"}
CHECK = {"EG_FROZEN": dict(EG, mode="base", eg="frozen")}          # 엔진 검사 전용 — FUNDMIX E 와 같은 얼린 Eg
CANDS = {
    "EG_BASE": dict(EG, mode="base"),
    "C1": dict(EG, mode="blend", add="mom", add_w=1 / 3),
    "C2": dict(EG, mode="screen", add="mom", pool=45, drop=15),
}
REF = {"REF_QG": {"signals": ["roe", "eg"], "weights": {"roe": 1, "eg": 1}, "smooth": 6, "n": 30, "wt": "cap", "cap": 0.20,
                  "reb": 3, "index": "spx", "ex_fin": True, "mode": "base"}}
# 반반 섞기 — 바스켓 10% 를 EG30 과 X 가 5%씩(매월 말 되돌림). X 의 월 초과는 FUNDMIX 얼린 값, Q 는 이 실행의 REF_QG.
MIXES = {"P_M": "M", "P_B": "B", "P_A": "A", "P_Q": "Q"}
PARTNER = {"M": "S&P500 12-1 모멘텀 상위 10", "B": "S&P500 B/M 금리 국면 로테이션", "A": "S&P500 알파 개선 상위 10",
           "Q": "우량성장선별 30"}
ELIGIBLE = ("C1", "C2")        # 섞기 넷은 공개 집계만으로 탈락이 정해져 있어 측정만(사전등록 §3-2) — 선택 대상에서 뺀다
T_MIN = 1.96                  # 한쪽 5% · 후보 둘 Bonferroni: z(1 − 0.05/2) = 1.95996
TE_MAX, TURN_X, WORST_BLOCK = 1.2, 2.0, -0.30                     # WORST_BLOCK: 연 %p(펀드)
R3 = "2023-09"


def _git(*a, check=True):
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True, check=check)


def frozen_check():
    """사전등록 커밋과 파일이 같아야 돈다 — 등록 뒤 엔진·검정기·입력을 고친 흔적이 남지 않는 구멍을 막는다.

    ① EGBEST_COMMIT 이 사전등록 문서를 **처음 더한** 커밋이어야 한다(나중 커밋으로 바꿔치기 금지)
    ② 그 커밋이 origin/main 의 조상이어야 한다(먼저 푸시 — 리베이스로 해시가 고아가 되는 사고를 막는다)
    ③ FROZEN 파일이 그 커밋과 바이트 단위로 같아야 한다(CRLF 무시) ④ 자료 판(SNAP)의 가격 파일과 같아야 한다
    ⑤ 이미 구운 산출물이 있으면 멈춘다(한 번 굽는 측정 — 다시 돌리려면 EGBEST_RERUN=사유 를 넘기고 그 사유가 JSON 에 남는다)
    """
    c = os.environ.get("EGBEST_COMMIT")
    if not c:
        raise SystemExit("🚨 EGBEST_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전 실행은 금지다.")
    full = _git("rev-parse", c + "^{commit}").stdout.strip()
    added = _git("log", "--format=%H", "--diff-filter=A", full, "--", PREREG).stdout.split()
    if not added or added[-1] != full:
        raise SystemExit("🚨 %s 는 %s 를 처음 더한 커밋이 아니다 — 멈춘다." % (full[:8], PREREG))
    if _git("merge-base", "--is-ancestor", full, "origin/main", check=False).returncode != 0:
        raise SystemExit("🚨 사전등록 커밋 %s 가 origin/main 에 없다 — 먼저 푸시한다." % full[:8])
    if (os.path.exists(OUT) or os.path.exists(MARK)) and not os.environ.get("EGBEST_RERUN"):
        raise SystemExit("🚨 %s 또는 시작 표식이 이미 있다 — 한 번 굽는 측정이다(다시 돌리려면 EGBEST_RERUN=사유)." % OUT)
    for ref in ("origin/main:data/_eg_best.json", "origin/main:build/PREREG-2026-09-24-EGBEST-RESULT.md"):
        if _git("cat-file", "-e", ref, check=False).returncode == 0 and not os.environ.get("EGBEST_RERUN"):
            raise SystemExit("🚨 %s 가 이미 커밋돼 있다 — 한 번 굽는 측정이다." % ref)
    if _git("diff", "--quiet", SNAP, "--", *SNAP_FILES, check=False).returncode != 0:
        raise SystemExit("🚨 자료 판이 %s 가 아니다(%s) — 멈춘다." % (SNAP, " · ".join(SNAP_FILES)))
    if _git("diff", "--quiet", SNAP_BASE, "--", *BASE_FILES, check=False).returncode != 0:
        raise SystemExit("🚨 가격 밖 입력이 %s 와 다르다(%s) — 멈춘다." % (SNAP_BASE, " · ".join(BASE_FILES)))
    for p in FROZEN:
        if not os.path.exists(os.path.join(ROOT, p)):
            raise SystemExit("🚨 %s 가 없다 — 사전등록 커밋에서 그 경로만 꺼내 온다(독스트링)." % p)
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True, check=True).stdout
        have = open(os.path.join(ROOT, p), "rb").read()
        if want.replace(b"\r\n", b"\n") != have.replace(b"\r\n", b"\n"):
            raise SystemExit("🚨 %s 가 사전등록 커밋 %s 과 다르다 — 멈춘다." % (p, full[:8]))
    return full


def stats(e, hold):
    """펀드 월 초과(%) 계열 → 전체·최근 3년 요약. evaluate 의 block 과 같은 식(연 = 월평균 × 12 · TE = 월 표준편차 × √12)."""
    e = np.asarray(e, float)

    def one(x):
        te = x.std(ddof=1) * math.sqrt(12)
        return {"n": int(len(x)), "ann_ex": float(x.mean() * 12), "te": float(te), "ir": float(x.mean() * 12 / te) if te > 0 else None,
                "t": float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))), "win": float(np.mean(x > 0) * 100)}
    sel3 = np.array([h >= R3 for h in hold])
    return {"all": one(e), "3y": one(e[sel3])}


def line(name, a, a3, turn, t0):
    print("%-8s IR %.2f · t %.2f · 연초과 %+.2f%% · TE %.2f%% · 3y IR %.2f · 회전 %.0f%% (%.0fs)" % (
        name, a["ir"], a["t"], a["ann_ex"], a["te"], a3["ir"], turn * 100, time.time() - t0))


def main() -> int:
    t0 = time.time()
    commit = frozen_check()
    started = "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
    io.open(MARK, "w", encoding="utf-8").write(started + "\n")          # 결과가 찍히기 전에 — 도중에 죽어도 재실행이 막힌다
    W = QL.World()
    last_date = W.dates[-1]
    R = {}
    # ① 엔진 검사 — 얼린 Eg 로 FUNDMIX E 재현
    R["EG_FROZEN"] = W.evaluate(CHECK["EG_FROZEN"], W.sleeve(CHECK["EG_FROZEN"]))
    line("EG_FROZEN", R["EG_FROZEN"]["all"], R["EG_FROZEN"]["3y"], R["EG_FROZEN"]["basket_turn_oneway"], t0)
    FM = json.load(io.open(MIX, encoding="utf-8"))
    E = FM["strategies"]["E"]["all"]
    gap = (abs(R["EG_FROZEN"]["all"]["ann_ex"] - E["ann_ex"]), abs(R["EG_FROZEN"]["all"]["ir"] - E["ir"]))
    print("  FUNDMIX E 재현: 연초과 %+.3f vs %+.3f · IR %.3f vs %.3f" % (R["EG_FROZEN"]["all"]["ann_ex"], E["ann_ex"], R["EG_FROZEN"]["all"]["ir"], E["ir"]))
    if max(gap) > 0.01:
        print("🚨 엔진이 EG30 을 재현하지 못했다(차 %.3f · %.3f) — 후보를 돌리지 않는다." % gap)
        return 1
    hf = R["EG_FROZEN"]["hold_months"]                                   # 창 검사도 결과(기저) 찍기 전에
    assert len(hf) == 120 and hf[0] == FM["window"][0] and hf[-1] == FM["window"][1], (hf[0], hf[-1], FM["window"])
    # ② 기저 — 금융 판정만 시점정확으로 바꾼 Eg
    R["EG_BASE"] = W.evaluate(CANDS["EG_BASE"], W.sleeve(CANDS["EG_BASE"]))
    line("EG_BASE", R["EG_BASE"]["all"], R["EG_BASE"]["3y"], R["EG_BASE"]["basket_turn_oneway"], t0)
    hold = R["EG_BASE"]["hold_months"]
    assert len(hold) == 120 and hold[0] == FM["window"][0] and hold[-1] == FM["window"][1], (hold[0], hold[-1], FM["window"])
    # ③ 통합 후보 · 참고
    for name in ("C1", "C2"):
        R[name] = W.evaluate(CANDS[name], W.sleeve(CANDS[name]))
        line(name, R[name]["all"], R[name]["3y"], R[name]["basket_turn_oneway"], t0)
    for name, c in REF.items():
        R[name] = W.evaluate(c, W.sleeve(c))
        line(name, R[name]["all"], R[name]["3y"], R[name]["basket_turn_oneway"], t0)
    base_ex = np.array(R["EG_BASE"]["monthly_ex"])
    # ④ 반반 섞기 — 펀드가 매월 말 90/10(바스켓 안 5/5)으로 되돌아가므로 월 수익이 구성 바스켓 월 수익에 선형이다:
    #   섞은 펀드 월 초과 = ½ × EG30 펀드 월 초과 + ½ × X 펀드 월 초과(두 바스켓 사이 되돌림 비용만 근사 — 연 0.01%p 미만).
    part_ex = {"M": FM["strategies"]["M"]["monthly_ex"], "B": FM["strategies"]["B"]["monthly_ex"],
               "A": FM["strategies"]["A"]["monthly_ex"], "Q": R["REF_QG"]["monthly_ex"]}
    part_turn = {"M": FM["strategies"]["M"]["basket_turn_oneway"], "B": FM["strategies"]["B"]["basket_turn_oneway"],
                 "A": FM["strategies"]["A"]["basket_turn_oneway"], "Q": R["REF_QG"]["basket_turn_oneway"]}
    MX = {}
    for name, x in MIXES.items():
        ex = 0.5 * base_ex + 0.5 * np.array(part_ex[x], float)
        s = stats(ex, hold)
        MX[name] = {"partner": x, "partner_name": PARTNER[x], "w": 0.5, "all": s["all"], "3y": s["3y"],
                    "partner_stats": stats(part_ex[x], hold),
                    "basket_turn_oneway": 0.5 * (R["EG_BASE"]["basket_turn_oneway"] + part_turn[x]),
                    "monthly_ex": [round(float(v), 5) for v in ex],
                    "corr_partner_base": float(np.corrcoef(np.array(part_ex[x], float), base_ex)[0, 1])}
        line(name, s["all"], s["3y"], MX[name]["basket_turn_oneway"], t0)
    # 섞는 비율 곡선(서술 — 선택에 쓰지 않는다): X 비중 0 ~ 100% (10%p 간격)
    curve = {}
    for x in ("M", "B", "A", "Q"):
        pe = np.array(part_ex[x], float)
        curve[x] = [dict(w=round(w, 1), **stats((1 - w) * base_ex + w * pe, hold)["all"]) for w in np.linspace(0, 1, 11)]
    # ⑤ 선택 규칙
    sel = {}
    for name in ELIGIBLE + tuple(MIXES) + ("REF_QG", "EG_FROZEN"):
        if name in MX:
            x, te, ir, turn = np.array(MX[name]["monthly_ex"]), MX[name]["all"]["te"], MX[name]["all"]["ir"], MX[name]["basket_turn_oneway"]
        else:
            x, te, ir, turn = np.array(R[name]["monthly_ex"]), R[name]["all"]["te"], R[name]["all"]["ir"], R[name]["basket_turn_oneway"]
        d = x - base_ex
        t = RP.nw_t(d, lag=3)
        blocks = [float(d[k * 30:(k + 1) * 30].mean() * 12) for k in range(4)]     # 연 %p
        a = t is not None and t >= T_MIN
        b = sum(v > 0 for v in blocks) >= 3
        c = te <= TE_MAX and turn <= TURN_X * R["EG_BASE"]["basket_turn_oneway"]
        dd = min(blocks) >= WORST_BLOCK
        e_ = ir is not None and ir >= R["EG_BASE"]["all"]["ir"]
        sel[name] = {"d_ann_pp": float(d.mean() * 12), "t_nw3": t, "blocks_ann_pp": blocks,
                     "corr_with_base": float(np.corrcoef(x, base_ex)[0, 1]),
                     "a": bool(a), "b": bool(b), "c": bool(c), "d": bool(dd), "e": bool(e_),
                     "pass": bool(a and b and c and dd and e_), "eligible": name in ELIGIBLE}
    passers = [n for n in ELIGIBLE if sel[n]["pass"]]
    winner = max(passers, key=lambda n: sel[n]["t_nw3"]) if passers else "EG_BASE"
    verdict = "측정만" if passers else "기각"                         # 사전등록 §5 — 규칙: 없음
    # ⑥ 자료 범위(생존 편향 공개용) — 형성월마다 명단 · 가격 키 · 시총 · Eg 가 선 수
    cov = {}
    for m in W.months:
        i = W.me[m]
        n_mem = len(set(W.W["lists"]["spx"].get(m) or []) | set(W.W["lists"]["ndx"].get(m) or []))
        pairs, n_co = PP.union_members(W.W, m, i)
        eg_raw, mom_raw = W.raw("eg", m, "union", False, "pitgics"), W.raw("mom", m, "union", False)
        sc = W.score(CANDS["EG_BASE"], m)
        cov[m] = {"members": n_mem, "companies": n_co, "keyed": len(pairs), "universe": len(W.universe(m, "union", False)),
                  "eg": len(eg_raw), "eg_frozen": len(W.raw("eg", m, "union", False, "frozen")),
                  "eg_mom": len(set(eg_raw) & set(mom_raw)),                  # 모멘텀이 선 Eg 회사(C1 의 모집단)
                  "base30_no_mom": sum(1 for x, _ in sc[:30] if x not in mom_raw),
                  "pool45_no_mom": sum(1 for x, _ in sc[:45] if x not in mom_raw)}             # C2 가 먼저 빼는 수
    out = {"prereg": PREREG, "prereg_commit": commit, "data_snapshot": SNAP, "data_base": SNAP_BASE, "data_last_date": last_date,
           "worktree_head": _git("rev-parse", "HEAD").stdout.strip(), "started": started,
           "rerun": os.environ.get("EGBEST_RERUN"), "cands": CANDS, "check": CHECK, "ref": REF,
           "mixes": {k: {"partner": v, "partner_name": PARTNER[v], "w": 0.5} for k, v in MIXES.items()},
           "rule": {"t_min": T_MIN, "te_max": TE_MAX, "turn_x": TURN_X, "worst_block_ann_pp": WORST_BLOCK, "ir_ge_base": True,
                    "n_eligible": len(ELIGIBLE)},
           "engine_check": {"fundmix_E": {"ann_ex": E["ann_ex"], "ir": E["ir"]}, "gap": list(gap)},
           "results": R, "mix_results": MX, "mix_curve": curve, "selection": sel, "winner": winner, "verdict": verdict,
           "coverage": cov}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    for n, s in sel.items():
        print("%-7s d 연 %+.2f%%p · t %.2f · 토막 %s · 상관 %.2f · (a)%s (b)%s (c)%s (d)%s (e)%s%s" % (
            n, s["d_ann_pp"], s["t_nw3"] if s["t_nw3"] is not None else float("nan"), [round(v, 2) for v in s["blocks_ann_pp"]],
            s["corr_with_base"], s["a"], s["b"], s["c"], s["d"], s["e"], "" if s["eligible"] else "  (참고 — 선택 대상 아님)"))
    c0, c1 = cov[W.months[0]], cov[W.months[-1]]
    print("자료 범위 %s: 명단 %d · 가격 키 %d · 시총 %d · Eg %d  |  %s: %d · %d · %d · %d" % (
        W.months[0], c0["members"], c0["keyed"], c0["universe"], c0["eg"], W.months[-1], c1["members"], c1["keyed"], c1["universe"], c1["eg"]))
    print("⇒ 선택:", winner, "· 판정:", verdict, "(%.0fs)" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
