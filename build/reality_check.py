# -*- coding: utf-8 -*-
"""시행 다중검정 진단 — 「우리 최고 t 는 운으로 나올 수 있는 크기인가」.

🚨 **이것은 문턱이 아니다.** 이 랩은 2026-08-13 사용자 지시로 관문·문턱을 전부 걷었고
  그 결정을 되돌리지 않는다. 여기서 하는 것은 «선을 긋는 것» 이 아니라
  **잰 값을 잡음의 분포에 대고 보여 주는 것**이다. 통과/탈락을 내지 않는다.

왜 필요한가. 이 랩은 한 창(2016-08~)에서 시행을 수백 번 돌렸다(그 수는 `trials.n` 이
세어 싣는다 — ⚠ 여기 손으로 안 적는다. 손으로 적은 수는 낡고, 이 저장소가 되풀이
밟는 결함이 정확히 그것이다). 그런데 **그 시행들의 t 가 전부 잡음이었다면 어떻게
생겼을지**는 아무 데도 안 적혀 있었다.
그 비교가 없으면 「최고 t 가 3.1 이다」가 큰 수인지 흔한 수인지 알 수 없다.

방법 — **계산 전에 여기 적는다**(결과를 보고 고르면 그것도 훑는 것이다).

  ① 대상: `data/pit_strategies.json` 의 월별 계열. **판정 레그(PIT)** 를 쓴다 —
     소급으로 재면 부풀림이 섞여 잡음 분포까지 부풀어 진단이 헐거워진다.
  ② 초과수익: **두 벌을 낸다.**
     · (A) 그 달 전략수익 − **그 규칙의 PIT 대조군**(`b`). 산출물·화면의 `t` 가 재는 것과
       **같은 잣대**다. 🚨 **이쪽이 주된 값이다** — 진단은 자기가 진단하는 t 와 같은 벤치를
       써야 한다. 다른 벤치로 만든 잡음 분포에 대고 보면 비교 자체가 뜻이 없다.
     · (B) 그 달 전략수익 − **S&P 500(PR)**. 사용자가 2026-07-28 에 정한 판정선이다.
     ⚠ **처음에 (B)만 냈다가 (A)를 더했다.** (B)에서 최고 t 가 5.95 로 나왔는데 같은 규칙의
       산출물 t 는 1.66 이었다 — 잣대가 다르면 3.6배까지 벌어진다. 그 사실을 숨기지 않는다.
     ⚠ (B)의 상위는 `x-cap*` 무리다. 그것은 종목을 고르는 규칙이 아니라 **랩 유니버스를
       시총가중한 것**이라, S&P 500 대비 초과는 «신호» 가 아니라 **유니버스 구성 차이**다.
  ③ 창: 규칙마다 시작이 다르므로 창을 정해야 한다.
     🚨 **전 규칙의 교집합을 쓰면 안 된다.** 처음에 그렇게 짰더니 74개월짜리 규칙 하나가
       전원의 창을 121 → **74개월**로 끌어내렸다(자료의 39%를 버린다).
     그래서 **커버리지 기준**으로 정한다 — 「규칙의 95% 이상이 통째로 덮는 가장 긴 창」.
     ⚠ 이 기준은 **결과를 안 본다.** p값이 좋아지는 창을 고르면 그것이 곧 훑기다.
       창 길이별 «남는 규칙 수» 표(frontier)를 산출물에 실어 그 선택을 드러낸다.
     ⚠ 교집합판(74개월)의 결과도 **같이 싣는다** — 그것을 먼저 계산했다는 사실까지 적는다.
     창을 못 덮는 규칙은 사유와 함께 뺀다(조용히 빼지 않는다).
  ④ 귀무가설: 각 규칙의 초과수익 계열을 **평균 제거**한다 = 「기대 초과수익 0」.
  ⑤ 재표집: **원형 블록 부트스트랩**. 블록 길이 **3개월**(= 63거래일, 이 랩이 낙폭
     부트스트랩에 이미 쓰는 «한 분기» 규약과 같다 — 내가 새로 고른 수가 아니다).
     🚨 **시간 인덱스를 전 규칙에 «똑같이» 적용한다.** 규칙마다 따로 섞으면 규칙 사이의
       상관이 깨져 «독립 시행 수백 회» 처럼 보이고, 그러면 잡음의 최고 t 가 과대평가된다.
       이 랩의 규칙들은 실제로 서로 매우 닮았다(산출물 `dup.median` 0.789).
  ⑥ 통계량: 각 재표집마다 전 규칙의 t 를 내고 그중 **최댓값**을 취한다. 그 분포가
     「잡음만으로 얻을 수 있는 최고 t」다. 실측 최고 t 가 그 분포의 어디에 서는지를 적는다
     (= White 의 Reality Check p값).
  ⑦ 반복 **2,000회**.

⚠ **이 진단은 `trials.n` 이 아니라 M 개를 덮는다.** 원장·아카이브에 든 시행은 계열이 안
  남아 있어 재표집할 수 없다. M 이 그보다 적으면 잡음의 최고 t 가 **과소평가**되고, 그만큼 이 진단은
  실측에 **유리한 쪽으로 치우친다.** 그 사실을 산출물에 수로 적는다.
⚠ t 는 월별로 잰다. 일별 t 와 눈금이 거의 같다(집계해도 t 는 대체로 불변) — 산출물이
  두 값을 나란히 실어 그 사실을 확인할 수 있게 한다.
"""
import io
import json
import os
import random
import sys

try:                                  # cp949 콘솔에서 print 가 죽지 않게(랩 공통 프렐류드)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
sys.path.insert(0, HERE)
import tech_backtest as TB          # noqa: E402  지표 정의는 그 파일 한 곳에만 둔다

BLOCK_M = 3            # 블록 길이(개월) = 한 분기. 랩의 낙폭 부트스트랩 규약과 같다.
REPS = 2000            # 재표집 횟수
BENCH = "S&P 500"      # 랩의 공식 판정선(PR)
SEED = 20260907        # 재현 가능하게 고정한다
COVER = 0.95           # 창 선택 기준 — 규칙의 이 비율 이상이 통째로 덮는 가장 긴 창(§③)


def load_rows(mode="own"):
    """PIT 월별 초과수익 — {sid: {ym: 초과수익}}. 계열이 없는 규칙은 사유와 함께 뺀다."""
    d = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    rows, dropped = {}, {}
    for s in d["strategies"]:
        mon = (s.get("chart") or {}).get("monthly") or []
        if not mon:
            dropped[s["sid"]] = "월별 계열이 없다"
            continue
        e = {}
        for m in mon:
            b = (m.get("b") if mode == "own" else (m.get("i") or {}).get(BENCH))
            if m.get("r") is None or b is None:
                continue
            e[m["m"]] = (m["r"] - b) / 100.0
        if len(e) < 24:
            dropped[s["sid"]] = "공통 구간에 쓸 관측이 24개월 미만이다(%d)" % len(e)
            continue
        rows[s["sid"]] = e
    return d, rows, dropped


def tstat(v):
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5
    return (m / (sd / len(v) ** 0.5)) if sd > 0 else 0.0


def _demean(v):
    mu = sum(v) / len(v)
    return [x - mu for x in v]


def bootstrap(X, C):
    """⑤⑥⑦ 원형 블록 부트스트랩 — **시간 인덱스를 전 규칙에 똑같이** 적용한다.

    🚨 규칙마다 따로 섞으면 규칙 사이의 상관이 깨져 독립 시행처럼 보이고, 그러면 잡음의
      최고 t 가 과대평가된다. 이 랩 규칙들의 상관 중앙값은 0.789다.
    ⚠ 두 창(고른 창 · 교집합판)이 이 함수를 같이 부른다 — 두 벌로 적으면 갈린다.
    """
    sids = sorted(X)
    n = len(X[sids[0]])
    rnd = random.Random(SEED)
    nb = (n + BLOCK_M - 1) // BLOCK_M
    null_max, null_over2, argmax = [], [], {}
    for _ in range(REPS):
        idx = []
        for _b in range(nb):
            st = rnd.randrange(n)
            idx.extend((st + k) % n for k in range(BLOCK_M))
        idx = idx[:n]
        mx, o2, arg = -1e9, 0, None
        for sid in sids:
            c = C[sid]
            t = tstat([c[j] for j in idx])
            if t > mx:
                mx, arg = t, sid
            if abs(t) >= 2.0:
                o2 += 1
        null_max.append(mx)
        null_over2.append(o2)
        argmax[arg] = argmax.get(arg, 0) + 1
    null_max.sort()
    return {"null_max": null_max, "null_over2": null_over2, "argmax": argmax}


def run_one(mode):
    """한 벤치로 진단 한 벌. mode="own"(그 규칙의 PIT 대조군) 또는 "spx"(S&P 500 PR)."""
    doc, rows, dropped = load_rows(mode)
    if not rows:
        raise SystemExit("PIT 월별 계열을 하나도 못 읽었다 — 진단을 낼 수 없다.")

    # ③ 창 선택 — **커버리지 기준**(§③). 결과를 안 보고 정한다.
    allm = sorted({m for e in rows.values() for m in e})
    end = allm[-1]
    frontier = []
    for si in range(len(allm)):
        win = allm[si:]
        keep = [sid for sid, e in rows.items() if all(m in e for m in win)]
        frontier.append({"from": win[0], "to": end, "n_months": len(win),
                         "n_rules": len(keep),
                         "share": round(len(keep) / len(rows), 3)})
    ok = [f for f in frontier if f["share"] >= COVER]
    if not ok:
        raise SystemExit("규칙의 %d%% 이상이 덮는 창이 없다 — 진단을 낼 수 없다." % (COVER * 100))
    pick = max(ok, key=lambda f: f["n_months"])           # 조건을 만족하는 **가장 긴** 창
    months = allm[allm.index(pick["from"]):]
    n = len(months)
    if n < 36:
        raise SystemExit("고른 창이 %d개월뿐이다 — 진단이 뜻을 갖기 어렵다." % n)
    X, lost = {}, {}
    for sid, e in rows.items():
        if all(m in e for m in months):
            X[sid] = [e[m] for m in months]
        else:
            lost[sid] = "고른 창(%s~%s)을 통째로 못 덮는다(%d/%d개월)" % (
                months[0], months[-1], sum(1 for m in months if m in e), n)
    sids = sorted(X)
    M = len(sids)

    # ④ 평균 제거 = 귀무가설(기대 초과수익 0)을 계열에 새긴다.
    C = {sid: _demean(X[sid]) for sid in sids}

    actual = {sid: tstat(X[sid]) for sid in sids}
    a_max = max(actual.values())
    a_min = min(actual.values())
    a_top = sorted(actual.items(), key=lambda kv: -kv[1])[:10]
    res = bootstrap(X, C)
    null_max, null_over2 = res["null_max"], res["null_over2"]
    # 🚨 잡음의 최고 t 를 «누가» 만드는지 센다. 초과수익의 분산이 거의 0 인 규칙(대조군이
    #   현금성인 타이밍 규칙 등)은 t 의 분모가 작아 재표집에서 큰 값을 자주 낸다 —
    #   그러면 잡음 분포의 꼬리가 두꺼워지고, 그만큼 이 진단은 **실측에 불리해진다**.
    #   ⚠ 그 규칙들을 빼지 않는다(결과를 보고 빼면 그것이 훑기다). 대신 누가 만드는지 적는다.
    sd = {sid: (sum((x - sum(X[sid]) / n) ** 2 for x in X[sid]) / (n - 1)) ** 0.5
          for sid in sids}
    hog = sorted(res["argmax"].items(), key=lambda kv: -kv[1])[:5]

    def q(p):
        return round(null_max[min(len(null_max) - 1, int(p * len(null_max)))], 3)

    # White 의 Reality Check p값 — 잡음의 최고 t 가 실측 최고 t 이상인 비율.
    pval = sum(1 for x in null_max if x >= a_max) / len(null_max)
    over2_actual = sum(1 for t in actual.values() if abs(t) >= 2.0)

    # ⚠ 교집합판도 같이 낸다(§③) — 창 선택이 결과를 얼마나 움직이는지 드러낸다.
    inter = None
    common = None
    for e in rows.values():
        common = set(e) if common is None else (common & set(e))
    im = sorted(common)
    if len(im) >= 36 and len(im) != n:
        IX = {sid: [e[m] for m in im] for sid, e in rows.items()}
        IC = {sid: _demean(v) for sid, v in IX.items()}
        ia = {sid: tstat(v) for sid, v in IX.items()}
        ires = bootstrap(IX, IC)
        inm = ires["null_max"]
        iam = max(ia.values())
        inter = {
            "why": ("전 규칙 교집합판이다. **이것을 먼저 계산했다** — 74개월로 쪼그라드는 것을 "
                    "보고 창 기준을 커버리지로 바꿨다(§③). 고른 창과 나란히 둬서 그 선택이 "
                    "결과를 얼마나 움직이는지 드러낸다."),
            "window": {"from": im[0], "to": im[-1], "n_months": len(im)},
            "n_rules": len(IX), "actual_max_t": round(iam, 3),
            "null_max_t_median": round(inm[len(inm) // 2], 3),
            "reality_check_p": round(sum(1 for x in inm if x >= iam) / len(inm), 4)}
    trials_n = None
    try:
        si = json.load(io.open(os.path.join(DATA, "strategy_index.json"), encoding="utf-8"))
        trials_n = (si.get("trials") or {}).get("n")
    except Exception:
        pass

    out = {
        "note": ("시행 다중검정 진단 — 잰 t 를 «잡음이었다면 어떻게 생겼을지» 에 대고 본다. "
                 "🚨 문턱이 아니다. 통과/탈락을 내지 않는다(관문·문턱은 2026-08-13 에 걷었다)."),
        "method": ("PIT 월별 초과수익(vs %s)을 평균 제거해 귀무가설을 새기고, 원형 블록 "
                   "부트스트랩(블록 %d개월 = 한 분기 · 랩의 낙폭 부트스트랩과 같은 규약)으로 "
                   "%d회 재표집한다. 🚨 시간 인덱스를 전 규칙에 «똑같이» 적용해 규칙 사이의 "
                   "상관을 보존한다 — 따로 섞으면 독립 시행처럼 보여 잡음의 최고 t 가 "
                   "과대평가된다(이 랩 규칙들의 상관 중앙값은 0.789다)." % (BENCH, BLOCK_M, REPS)),
        "as_of": doc.get("as_of"), "bench": BENCH,
        "window": {"from": months[0], "to": months[-1], "n_months": n},
        "n_rules": M, "trials_n": trials_n,
        "coverage_note": (
            "이 진단이 덮는 것은 계열이 남아 있는 %d종이고 시행 분모는 %s다. "
            "원장·아카이브의 시행은 계열이 없어 재표집할 수 없다. "
            "🚨 덮는 수가 적을수록 잡음의 최고 t 가 **과소평가**되므로 이 진단은 "
            "실측에 **유리한 쪽으로 치우쳐 있다** — 즉 여기서도 못 넘으면 확실히 못 넘는다."
            % (M, trials_n)),
        "actual": {"max_t": round(a_max, 3), "min_t": round(a_min, 3),
                   "n_over_2": over2_actual,
                   "top": [{"sid": s, "t": round(t, 3)} for s, t in a_top]},
        "null_max_t": {"median": q(0.5), "p90": q(0.9), "p95": q(0.95), "p99": q(0.99),
                       "max": round(null_max[-1], 3)},
        "null_n_over_2": {"mean": round(sum(null_over2) / len(null_over2), 1),
                          "max": max(null_over2)},
        "reality_check_p": round(pval, 4),
        "reading": None,
        "block_months": BLOCK_M, "reps": REPS, "seed": SEED, "cover": COVER,
        "dropped": dropped,
        "excluded_by_window": lost,
        # 창을 어떻게 골랐는지 드러낸다 — 창이 길수록 남는 규칙이 준다는 맞바꿈이 여기 있다.
        #   ⚠ p값이 좋아지는 창을 고르지 않았다. 기준은 커버리지(COVER)이고 결과를 안 본다.
        "window_frontier": [f for f in frontier
                            if f["n_months"] in (len(allm), n, len(im) if im else -1)
                            or f["share"] in (1.0,)][:12],
        "intersection_variant": inter,
        # 잡음의 최고 t 를 누가 만드는가 — 꼬리가 두꺼우면 대개 저분산 규칙 몇이 만든다.
        "null_argmax_top": [{"sid": k, "share": round(v / REPS, 3),
                             "excess_sd_m": round(sd.get(k, 0) * 100, 3)} for k, v in hog],
        "excess_sd_note": ("초과수익 월 표준편차(퍼센트). 값이 작을수록 t 의 분모가 작아 "
                           "재표집에서 큰 t 가 자주 나온다 — 잡음 꼬리를 두껍게 만든다."),
    }
    out["reading"] = (
        "실측 최고 t %.2f · 잡음의 최고 t 중앙값 %.2f(95%% %.2f). Reality Check p = %.3f — "
        "잡음만으로 이만한 최고 t 가 나올 확률이 그만큼이다. "
        "⚠ 이 수는 판정이 아니라 «어디쯤인가» 다."
        % (a_max, out["null_max_t"]["median"], out["null_max_t"]["p95"], pval))

    print("  [%s] 대상 %d종 · 창 %d개월(%s~%s)" % (mode, M, n, months[0], months[-1]))
    print("        실측 최고 t %.3f · |t|≥2 인 규칙 %d종 (잡음 평균 %.1f)"
          % (a_max, over2_actual, out["null_n_over_2"]["mean"]))
    print("        잡음의 최고 t — 중앙 %.3f · 95%% %.3f · 99%% %.3f"
          % (q(0.5), q(0.95), q(0.99)))
    print("        🚨 Reality Check p = %.4f" % pval)
    return out


def main():
    """두 벤치로 각각 낸다(§②). 주된 값은 «그 규칙의 PIT 대조군» 쪽이다."""
    own = run_one("own")
    spx = run_one("spx")
    # 산출물의 t 와 눈금이 맞는지 스스로 확인한다 — 월별 t 와 일별 t 는 대체로 같아야 한다.
    pd = json.load(io.open(os.path.join(DATA, "pit_strategies.json"), encoding="utf-8"))
    P = {s["sid"]: s for s in pd["strategies"]}
    chk = []
    for r in own["actual"]["top"][:10]:
        pt = P.get(r["sid"], {}).get("t")
        if pt is not None:
            chk.append({"sid": r["sid"], "monthly_t": r["t"], "record_t": pt,
                        "diff": round(r["t"] - pt, 2)})
    doc = {
        "note": own["note"],
        "as_of": own["as_of"],
        "self_check": {
            "why": ("월별로 잰 t 가 산출물의 일별 t 와 눈금이 맞는지 스스로 본다. "
                    "집계해도 t 는 대체로 불변이라 크게 벌어지면 어느 한쪽이 틀린 것이다."),
            "rows": chk,
            "max_abs_diff": (max(abs(c["diff"]) for c in chk) if chk else None)},
        "primary": own,
        "vs_spx": spx,
        "reading": (
            "주된 값(그 규칙의 PIT 대조군 기준): 실측 최고 t %.2f · 잡음의 최고 t 중앙 %.2f "
            "(95%% %.2f) · Reality Check p = %.3f. "
            "⚠ S&P 500 기준으로 재면 최고 t 가 %.2f 로 뛰는데, 그 상위는 종목을 고르는 규칙이 "
            "아니라 랩 유니버스를 시총가중한 x-cap* 무리다 — 신호가 아니라 유니버스 구성 차이다."
            % (own["actual"]["max_t"], own["null_max_t"]["median"],
               own["null_max_t"]["p95"], own["reality_check_p"],
               spx["actual"]["max_t"])),
    }
    p = os.path.join(DATA, "reality_check.json")
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→ %s" % p)
    print("  자기검사 — 월별 t vs 산출물 t 최대 차이 %s" % doc["self_check"]["max_abs_diff"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
