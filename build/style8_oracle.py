# -*- coding: utf-8 -*-
"""build/style8_oracle.py — 스타일 8종 로테이션의 **천장을 먼저 잰다** → data/_style8_oracle.json

## 왜 성적보다 천장을 먼저 재나

`PREREG-2026-09-09-FACROT-RESULT.md` 가 국면 로테이션을 기각하며 남긴 것:
조건부가 무조건보다 **나빴고**(ΔIR −0.005 / −0.104), 무작위 상태 셔플의 한가운데였다
(SPX 54.0% · NDX 18.5%). `REGIME0` 도 50.9% 였다. 이 랩이 국면·로테이션을 **여섯 번**
재고 여섯 번 기각했다.

그래서 일곱 번째를 만들기 전에 묻는다 — **매달 1등 스타일을 미리 안다고 치면 얼마인가.**
그 천장이 낮으면 규칙을 만들 필요가 없다. 천장이 높으면 죽는 자리는 상한이 아니라
**효과크기**이고, 그때 물을 것은 「월 랭크 IC 가 얼마여야 게이트를 넘나」다.
`LAB-USAGE-MAP` §5 가 섹터에서 이미 한 계산이다(오라클 t 15.33 · 필요 IC 0.13~0.22 ·
문헌 최고 IR 0.4~0.5 → t 1.62~2.04 → 효과크기에서 죽는다).

## 🚨 이 랩에 5년 PIT 스타일 계열이 없다 — 그래서 여기서 만든다

실측(2026-09-18):
  · `data/style_pit.json` 의 세 레그는 전부 **12개월**이다(`n_rebal=11` · ret≈total).
    `start 2021-07-30 · n_days 1288` 은 **패널 준비 구간**(WINDOW5)이지 백테스트 창이 아니다.
  · `data/style_perf.json` 의 5년 칸은 **소급 레그**다 — style_top_pdf.py:1963 이
    `global WINDOW; WINDOW = WINDOW5` 로 창만 바꿔 돌린 것이라 PIT 마스크가 안 걸린다.
  → 있는 것은 「PIT 인데 1년」과 「5년인데 소급」뿐이다. 필요한 것은 「PIT 이고 5년」이다.

**새 백테스트를 짜지 않는다.** 두 벌로 만들면 반드시 어긋나고, 그때 어느 쪽이 틀렸는지
알 수 없게 된다(style_pit.py 가 못박은 규약). 같은 `ST.backtest` 에 창만 바꿔 부른다.

## 앵커 — 계산을 바꾼 것이 아님을 증명한다

새로 만든 5년 PIT 레그의 **마지막 12개월**이 `style_pit.json` 의 `pit` 레그와 일치해야
한다. 어긋나면 편향을 잰 것이 아니라 내가 계산을 바꾼 것이다. `--check-anchor` 가
그것을 보고, 허용 오차를 넘으면 종료코드 1 로 죽는다.

## 무엇을 내나 — 전부 «천장» 이고 어느 것도 게시용 규칙이 아니다

    oracle      매월 그 달 1등 스타일을 **미리 알고** 담는다 — 실시간에 불가능하다
    anti        매월 꼴등을 담는다 — 바닥
    ew          8종 동일가중 · 월말 리밸런스 — 🚨 로테이션이 넘어야 할 진짜 상대
    best1/worst1 사후 최고·최저 단일 스타일 — 참고
    bench       그 달 PIT 지수

    need_ic     월 랭크 IC 를 0부터 올려 가며 top-1 로테이션을 모의해, EW 대비 초과의
                t 가 문턱(1.5 · 3.30)을 넘는 지점을 찾는다.

    python build/style8_oracle.py
    python build/style8_oracle.py --check-anchor    # 앵커 어긋나면 종료코드 1
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_style8_oracle.json")     # data/_* = 로컬 산출물 관례(커밋 안 함)

sys.path.insert(0, HERE)
import style_top_pdf as ST                           # noqa: E402
import style_pit_panel as SPP                        # noqa: E402

# 화면 style8.html 에 서 있는 여덟. 🚨 숨김 8종을 넣지 않는다 — 등록서 §6.
E8 = ("val", "grow", "hbeta", "div", "spmo", "qvm", "squal", "size")

ANCHOR_TOL_PP = 0.50        # 앵커 허용 오차(총수익 %p). 창 경계 하루 차이만 허용한다.
IC_GRID = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80, 1.0]
N_SIM = 500
SEED = 20260918
GATES = (1.5, 3.30)         # 등록서 F2 · LAB-USAGE-MAP 게이트


def build_legs(P, pool_of, keys=E8, say=print):
    """8종 레그를 **창을 WINDOW5 로 바꿔** 같은 ST.backtest 로 만든다 → {key: R}.

    🚨 백테스트를 다시 짜지 않는다. 창만 바꿔 같은 함수를 부른다(style_pit.py 규약).
      build/style8w.py 도 이 함수를 쓴다 — 레그를 두 벌로 만들면 반드시 어긋난다.
    """
    fn_of = {s[0]: (s[1], s[3]) for s in ST.STYLES}
    miss = [k for k in keys if k not in fn_of]
    if miss:
        raise SystemExit("ST.STYLES 에 없는 스타일: %s" % miss)
    legs, spans = {}, {}
    old = ST.WINDOW
    try:
        ST.WINDOW = ST.WINDOW5
        for k in keys:
            label, fn = fn_of[k]
            R = ST.backtest(P, SPP.narrowed(fn, pool_of), pool_of=pool_of)
            if not R:
                raise SystemExit("%s(%s) 레그 산출 실패 — 후보가 문턱에 못 닿는다" % (k, label))
            legs[k] = R
            spans[k] = (R["start"], R["end"])
    finally:
        ST.WINDOW = old
    s0 = {v[0] for v in spans.values()}
    e0 = {v[1] for v in spans.values()}
    if len(s0) != 1 or len(e0) != 1:
        raise SystemExit("레그마다 창이 다르다 — 비교가 성립하지 않는다: %s" % spans)
    return legs, s0.pop(), e0.pop()


def month_ends(dates, start, end):
    """[start, end] 안의 월말 인덱스 — 달이 바뀌는 직전 거래일."""
    out = [k for k in range(start + 1, end + 1) if dates[k][:7] != dates[k - 1][:7]]
    return [k - 1 for k in out] + [end]


def seg_rets(nav, idx, base):
    """월말 인덱스 사이의 구간 수익률(비율). nav 는 base 에서 시작하는 일별 곡선.

    🚨 창 시작이 월말이라 첫 월말이 시작점과 같은 날인 경우가 있다. 그 자리를 1.0 으로
      채우면 **가짜 무수익 달**이 하나 생겨 변동성과 평균을 둘 다 낮춘다(63개월 중 1개월).
      구간이 아닌 것은 만들지 않고 건너뛴다.
    """
    out, prev = [], 0
    for k in idx:
        j = k - base
        if j <= prev:
            continue
        out.append(nav[j] / nav[prev] if nav[prev] > 0 else 1.0)
        prev = j
    return np.asarray(out, float)


def tstat(x):
    x = np.asarray(x, float)
    sd = float(np.std(x, ddof=1))
    return float(np.mean(x) / sd * np.sqrt(len(x))) if sd > 0 and len(x) > 1 else float("nan")


def ann(monthly_ratio):
    """월별 비율에서 연율 수익·변동성·샤프.

    🚨 `ST.metrics` 는 일별 전용이라 그대로 못 쓴다 — 산식을 두 벌 두는 것이 아니라
      **주기가 다른 것**이다. 대신 두 가지를 반드시 맞춘다:
        ① 총수익은 일별 곡선과 같아야 한다(호출부가 앵커로 대조한다).
        ② 🚨 **샤프는 초과수익 기준이다.** `ST._rfd()` 가 유일한 무위험 출처이고
           그것은 일할이므로 ×21 로 월할로 되돌린다. 이것을 빼먹으면 저변동 규칙이
           부당하게 유리해진다 — `style_top_pdf.py:1130` 이 정확히 그 결함을 적어 두었고
           2026-08-05 에 고친 자리다. 여기서 같은 실수를 되풀이하지 않는다.
    """
    r = np.asarray(monthly_ratio, float) - 1.0
    n = len(r)
    rf_m = ST._rfd() * 21.0                      # 일할 → 월할. 출처는 data/rf_monthly.json 하나
    tot = float(np.prod(1 + r) - 1)
    sd = float(np.std(r, ddof=1)) if n > 1 else 0.0
    return {"total": tot * 100,
            "cagr": ((1 + tot) ** (12.0 / n) - 1) * 100 if n > 0 else None,
            "vol": sd * np.sqrt(12) * 100,
            "sharpe": ((float(np.mean(r)) - rf_m) / sd * np.sqrt(12)) if sd > 0 else None,
            "rf_m_pct": round(rf_m * 100, 4),
            "n_months": n}


def need_ic(R, rng):
    """월 랭크 IC 를 올려 가며 top-1 로테이션을 모의한다.

    각 달의 8종 실현수익을 정규점수 z_true 로 바꾸고,
        z_pred = rho*z_true + sqrt(1-rho^2)*eps
    로 예측을 만든다. argmax(z_pred) 를 그 달에 담는다. EW 대비 초과의 t 를 본다.
    🚨 rho 는 피어슨이라 그대로 «랭크 IC» 가 아니다 — 모의에서 실현된 스피어만을 같이 재서
      그 값으로 보고한다. 근사로 부르지 않는다.
    """
    n_m, n_s = R.shape
    ew = R.mean(axis=1)
    # 실현수익의 월별 정규점수
    order = np.argsort(np.argsort(R, axis=1), axis=1)            # 0..7 랭크
    z_true = np.zeros_like(R)
    from math import sqrt
    for m in range(n_m):
        u = (order[m] + 0.5) / n_s
        # 역정규 근사 없이 표준정규 분위를 직접 쓴다
        z_true[m] = np.sqrt(2) * _erfinv(2 * u - 1)
    rows = []
    for rho in IC_GRID:
        ts, ics, exc = [], [], []
        for _ in range(N_SIM):
            eps = rng.standard_normal(R.shape)
            zp = rho * z_true + sqrt(max(0.0, 1 - rho * rho)) * eps
            pick = np.argmax(zp, axis=1)
            got = R[np.arange(n_m), pick]
            d = got - ew
            ts.append(tstat(d)); exc.append(float(np.mean(d)))
            # 실현 스피어만(월별 평균)
            pr = np.argsort(np.argsort(zp, axis=1), axis=1).astype(float)
            tr = order.astype(float)
            c = [np.corrcoef(pr[m], tr[m])[0, 1] for m in range(n_m)]
            ics.append(float(np.mean(c)))
        rows.append({"rho": rho,
                     "realized_rank_ic": round(float(np.mean(ics)), 4),
                     "t_mean": round(float(np.mean(ts)), 3),
                     "t_p05": round(float(np.percentile(ts, 5)), 3),
                     "t_p95": round(float(np.percentile(ts, 95)), 3),
                     "excess_pp_mo": round(float(np.mean(exc)) * 100, 3)})
    return rows


def _erfinv(y):
    """표준정규 분위를 쓰려고 erfinv 를 근사한다(Winitzki). scipy 를 끌어오지 않는다."""
    y = np.clip(np.asarray(y, float), -0.999999, 0.999999)
    a = 0.147
    ln = np.log(1 - y * y)
    t1 = 2 / (np.pi * a) + ln / 2
    return np.sign(y) * np.sqrt(np.sqrt(t1 * t1 - ln / a) - t1)


def main() -> int:
    check_anchor = "--check-anchor" in sys.argv

    print("① 5년 PIT 패널 준비")
    prep = SPP.prepare(ST, window=max(ST.WINDOW, ST.WINDOW5))
    P = prep["P"]
    members_at = prep["members_at"]
    SPP.inject(prep)
    print("   주입 %d종 · 미확보 %d종" % (len(prep["inject"]), len(prep.get("missing") or [])))

    # 🚨 두 레그를 같이 돌린다. 판정은 pit 으로만 하지만, 등록서 F7 이 «두 레그의 판정이
    #   갈리면 첫 줄에 적는다» 를 요구한다. 소급 레그를 안 돌리면 그 조건을 못 잰다.
    today = prep["today"]
    LEGS = (("pit", members_at),                 # 그때 멤버 전부(편출 포함) — 판정 레그
            ("base", lambda i: today))           # 오늘의 유니버스로만 = 소급 — 참고 레그
    print("② 8종 레그 — 창을 WINDOW5 로 바꿔 같은 backtest 를 두 레그로 부른다")
    legs, spans, start, end = {}, {}, None, None
    for tag, po in LEGS:
        lg, s, e = build_legs(P, po)
        for k in E8:
            legs[(tag, k)] = lg[k]
        if start is None:
            start, end = s, e
        elif (s, e) != (start, end):
            raise SystemExit("레그 창이 갈린다: %s vs %s" % ((s, e), (start, end)))
        print("   %-5s 레그 8종 완료 · %s ~ %s · 리밸 %d"
              % (tag, P.dates[s], P.dates[e], lg[E8[0]]["n_rebal"]))

    print("③ 앵커 — 마지막 12개월이 style_pit.json 의 pit 레그와 맞나")
    anchor, worst = {}, 0.0
    try:
        sp = json.load(io.open(os.path.join(DATA, "style_pit.json"), encoding="utf-8"))
    except Exception as e:
        sp = None
        print("   ⚠ style_pit.json 을 못 읽었다(%s) — 앵커 검증 건너뜀" % e)
    if sp:
        me = month_ends(P.dates, start, end)
        for k in E8:
            ref = (sp.get("styles", {}).get(k) or {}).get("pit")
            if not ref:
                anchor[k] = {"ref": None, "note": "style_pit.json 에 pit 레그 없음"}
                continue
            nav = legs[("pit", k)]["nav"]
            idx12 = me[-13:]                              # 12개월 = 월말 13점
            j0, j1 = idx12[0] - start, idx12[-1] - start
            got = (nav[j1] / nav[j0] - 1) * 100
            gap = got - ref["total"]
            worst = max(worst, abs(gap))
            anchor[k] = {"ref_total": round(ref["total"], 2),
                         "got_total": round(float(got), 2), "gap_pp": round(float(gap), 2)}
            print("   %-6s 기존 %8.2f%%  새 %8.2f%%  차 %+6.2f%%p" % (k, ref["total"], got, gap))
        print("   최대 차 %.2f%%p (허용 %.2f)" % (worst, ANCHOR_TOL_PP))
        if check_anchor and worst > ANCHOR_TOL_PP:
            print("🚨 앵커 불일치 — 편향을 잰 것이 아니라 계산이 바뀐 것이다.")
            return 1

    print("④ 월별 수익 행렬 · 두 레그")
    me = month_ends(P.dates, start, end)
    months = [P.dates[i][:7] for i in me]
    RM = {tag: np.column_stack([seg_rets(legs[(tag, k)]["nav"], me, start) for k in E8])
          for tag, _ in LEGS}
    bnav = ST.bench_nav(P, P.gspc, start, end)
    bm = seg_rets(bnav, me, start) if bnav is not None else None
    print("   월 %d개 (%s ~ %s)" % (len(months), months[0], months[-1]))

    print("⑤ 천장 — 레그마다")
    summ, vs = {}, {}
    for tag, _ in LEGS:
        Rm = RM[tag]
        ew, orc, anti = Rm.mean(axis=1), Rm.max(axis=1), Rm.min(axis=1)
        tot = np.prod(Rm, axis=0)
        b1, w1 = int(np.argmax(tot)), int(np.argmin(tot))
        cur = {"oracle": orc, "anti": anti, "ew": ew,
               "best1_expost": Rm[:, b1], "worst1_expost": Rm[:, w1]}
        summ[tag] = {n: ann(v) for n, v in cur.items()}
        summ[tag]["_best1"], summ[tag]["_worst1"] = E8[b1], E8[w1]
        for k in E8:
            summ[tag]["style_" + k] = ann(Rm[:, E8.index(k)])
        spread = (orc - anti) * 100
        vs[tag] = {"oracle_t": round(tstat(orc - ew), 3),
                   "oracle_excess_pp_mo": round(float(np.mean(orc - ew)) * 100, 3),
                   "spread_mean_pp": round(float(np.mean(spread)), 2),
                   "spread_med_pp": round(float(np.median(spread)), 2),
                   "ew_beats_bench": (bool(summ[tag]["ew"]["sharpe"] > ann(bm)["sharpe"])
                                      if bm is not None else None)}
        print("   [%s] %-14s %10s %9s %8s %8s" % (tag, "", "총수익", "연율", "변동성", "샤프"))
        for n in ("oracle", "ew", "anti", "best1_expost", "worst1_expost"):
            m = summ[tag][n]
            print("        %-14s %9.1f%% %8.1f%% %7.1f%% %8.2f"
                  % (n, m["total"], m["cagr"], m["vol"], m["sharpe"] or float("nan")))
        print("        최고단일 %s · 최저단일 %s · 오라클-EW 월 %+.2f%%p (t %.2f)"
              % (summ[tag]["_best1"], summ[tag]["_worst1"],
                 vs[tag]["oracle_excess_pp_mo"], vs[tag]["oracle_t"]))
    if bm is not None:
        summ["bench"] = ann(bm)
        m = summ["bench"]
        print("   [bench] %9.1f%% %8.1f%% %7.1f%% %8.2f"
              % (m["total"], m["cagr"], m["vol"], m["sharpe"]))

    # F7 — 두 레그의 스타일 순위가 갈리나
    def rank(tag):
        return [k for k, _ in sorted(((k, summ[tag]["style_" + k]["sharpe"]) for k in E8),
                                     key=lambda x: -(x[1] or -9))]
    r_pit, r_base = rank("pit"), rank("base")
    f7 = {"pit_order": r_pit, "base_order": r_base, "same": r_pit == r_base}
    print("   F7 순위 — pit  %s" % " > ".join(r_pit))
    print("            base %s" % " > ".join(r_base))
    print("            일치: %s" % ("예" if f7["same"] else "🚨 아니오 — 결과 첫 줄에 적을 것"))

    print("⑥ 필요 랭크 IC — pit 레그 · top-1 로테이션 모의 %d회" % N_SIM)
    rng = np.random.default_rng(SEED)
    rows = need_ic(RM["pit"], rng)
    Rm = RM["pit"]
    vs_ew = vs["pit"]
    print("   %8s %10s %8s %8s %8s %10s" % ("rho", "랭크IC", "t평균", "t5%", "t95%", "월초과"))
    for r in rows:
        print("   %8.2f %10.3f %8.2f %8.2f %8.2f %9.2f%%p"
              % (r["rho"], r["realized_rank_ic"], r["t_mean"], r["t_p05"], r["t_p95"],
                 r["excess_pp_mo"]))
    need = {}
    for g in GATES:
        hit = next((r for r in rows if r["t_mean"] >= g), None)
        need["t_%.2f" % g] = (hit["realized_rank_ic"] if hit else None)
        print("   t ≥ %.2f 를 넘으려면 월 랭크 IC ≈ %s"
              % (g, ("%.3f" % hit["realized_rank_ic"]) if hit else "격자 안에서 도달 못 함"))

    out = {
        "note": "🚨 게시용 규칙이 아니다 — oracle 은 완전 예지를 쓴다. 로테이션을 만들기 전에 "
                "천장을 재는 진단이다. PREREG-2026-09-18-STYLE8W.md §7 참조.",
        "as_of": P.dates[end],
        "window": {"from": P.dates[start], "to": P.dates[end],
                   "n_days": end - start, "n_months": len(months)},
        "legs": {"pit": "선정 시점 멤버 전부(편출 포함) · 채점 모집단까지 좁힘 — 🚨 판정 레그",
                 "base": "오늘의 유니버스로만 = 소급 — 참고 레그"},
        "styles": list(E8),
        "months": months,
        "anchor": {"tol_pp": ANCHOR_TOL_PP, "worst_gap_pp": round(worst, 3), "per_style": anchor},
        "summary": {tag: {k: ({kk: (round(vv, 4) if isinstance(vv, float) else vv)
                               for kk, vv in v.items()} if isinstance(v, dict) else v)
                          for k, v in summ[tag].items()} for tag, _ in LEGS},
        "bench": summ.get("bench"),
        "rank_f7": f7,
        "oracle_vs_ew": vs,
        "need_ic": {"grid": rows, "gates": need, "n_sim": N_SIM, "seed": SEED},
        "caveat": "월 %d개뿐이다(랩 표준 120개월의 절반 아래). 그리고 oracle 은 상한이지 "
                  "달성 가능한 값이 아니다 — FACROT 이 남긴 대로, 상태가 무작위여도 "
                  "IR 이 양수로 나올 수 있으므로 이 표의 어느 수도 «성적» 으로 읽지 않는다."
                  % len(months),
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
