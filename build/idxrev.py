# -*- coding: utf-8 -*-
"""build/idxrev.py — 지수 강화 + 리비전 드리프트 → data/_idxrev.json

규약: build/PREREG-2026-09-16-IDXREV.md (계산 전 커밋 8a75447d6).

  2×2 를 **같은 패널에서** 돌린다 — 한 칸만 보면 신호 탓인지 제약 탓인지 못 가른다.

                  ±1%p 절대한도        비중비례 한도(|Δw| ≤ w_b)
    교과서 7팩터    대조군(재현)          대조군
    리비전 드리프트  판정 ①               판정 ②

🚨 계산을 복사하지 않는다 — `idxtilt.py` 가 얼려 둔 월별 패널
   `data/_idxtilt_panel_{spx,ndx}.json`(벤치 비중·섹터·월수익·현금·7팩터 z)을 읽고,
   상수·헬퍼(sd·zs·CAP·COST)는 `idxtilt` 모듈에서 그대로 가져온다.
🚨 신호는 TB.rat_signal — `x-revdrift` 가 쓰는 바로 그 함수다. 채점기 사본 없음.
🚨 얼린 측정 — 산출물은 밑줄 접두. 자동 재굽기 금지.

    python build/idxrev.py
"""
from __future__ import annotations
import collections
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_idxrev.json")
sys.path.insert(0, HERE)

import idxtilt as IT                       # sd·zs·CAP_SEC·TE_*·COST_RT 정본
import tech_backtest as TB                 # rat_signal·load_ratings 정본

BAND = TB.BAND                             # 2.0 — tech_backtest 의 값을 그대로 쓴다
REV_DAYS = 30                              # 등록 §1 — x-revdrift 21일판과 같은 달력 30일
JUDGE_START = "2018-07"                    # 등록 §1-1 — IDXTILT 와 같은 창
RAT_END = "2026-07"                        # 캐시가 2026-08-11 까지 → 마지막 부분월 제외
COV_LONG = 0.70                            # §3-1 긴 창: 벤치 시총 커버리지 70% 도달부터

# IDXTILT 공표값(2026-09-09) — F0 재현 관문의 비교 대상
PUB = {"spx": -0.161, "ndx": -0.575}


def zsec(raw, sec, names):
    """섹터 내 z — idxtilt 와 같은 처리(섹터당 5종 이상일 때만, 아니면 0)."""
    bysec = collections.defaultdict(dict)
    for t, v in raw.items():
        bysec[sec.get(t, "?")][t] = v
    z = {}
    for s, dd in bysec.items():
        z.update(IT.zs(dd) if len(dd) >= 5 else {t: 0.0 for t in dd})
    return z


def build(idx):
    """패널 + 리비전 z 를 얹은 행 목록."""
    p = os.path.join(DATA, "_idxtilt_panel_%s.json" % idx)
    if not os.path.exists(p):
        raise SystemExit("❌ %s 없음 — python build/idxtilt.py 를 먼저 돌릴 것" % p)
    P = json.load(io.open(p, encoding="utf-8"))
    rows = P["rows"]
    # 신호 시점 = 그 행의 수익월 바로 앞 달의 **마지막 거래일**(idxtilt 의 i 와 같은 칸)
    mend = {}
    for d in DATES:
        mend[d[:7]] = d
    def prev_month(mm):
        y, k = int(mm[:4]), int(mm[5:7])
        return "%04d-%02d" % ((y - 1, 12) if k == 1 else (y, k - 1))
    out = []
    for x in rows:
        sm = prev_month(x["m"])
        d = mend.get(sm)
        if not d:
            continue
        names = sorted(x["wb"])
        raw = {}
        for t in names:
            v = TB.rat_signal(t, d, REV_DAYS)
            if v is not None:
                raw[t] = v
        x["rev_d"] = d
        x["Z"]["rev"] = zsec(raw, x["sec"], names)
        x["cov"]["rev"] = sum(x["wb"][t] for t in raw)
        x["names"] = names
        out.append(x)
    return P, out


def run(rows, j0, signal, cap_mode, te_target, flip=False, lam_mult=None, band=False):
    """signal: 'rev' | 'erc7'  ·  cap_mode: 'abs' | 'prop'

    lam_mult 를 주면 원 λ 에 그 배수를 곱한다(부칙 A2 의 이분탐색이 쓴다).
    None 이면 **원 등록 그대로**(idxtilt 의 λ 를 그대로) 돌린다.

    band=True 는 PREREG-2026-09-16-IDXREVBAND.md(계산 전 커밋 f0d0cae69) §1 —
    능동비중 무거래 밴드. 직전에 들고 있던 능동비중의 **절반~두 배** 안이고 부호가 같으면
    그대로 들고, 아니면 새 목표로 갈아탄다. 비(BAND)는 tech_backtest 의 값을 그대로 쓴다.
    🚨 band=False 경로는 한 줄도 안 바뀐다 — IDXREV 의 수가 그대로 재현돼야 한다.

    idxtilt.run 과 같은 산식. 다른 것은 «점수를 무엇으로 내나»와 «개별 한도»뿐이다.
    ⚠ erc7 은 패널에 얼려 둔 7팩터 z 를 **동일가중**으로 합친다 — 롤링 ERC 가중을 다시
      뽑으려면 48개월 warm 과 스프레드 계산이 필요하고, 그것은 idxtilt 가 이미 낸 수다.
      여기 erc7 은 «같은 제약에서 교과서 팩터가 어떻게 되나» 를 보는 대조군이므로
      IDXTILT 의 «동일가중 1/7» 줄과 짝이 맞는다(그 줄도 등록에 실려 있다).
    """
    out, prevw, binds, acts = [], None, [0, 0], []
    capw = [0.0, 0.0]                  # [한도에 붙은 |Δw| 합, 전체 |Δw| 합] — 부칙 A3
    aprev = {}                         # 티커 → 직전에 «실제로 들고 있던» 능동비중(밴드용)
    held = [0, 0]                      # [밴드가 잡아 안 갈아탄 횟수, 전체]
    for j in range(j0, len(rows)):
        x = rows[j]
        names, wb = x["names"], x["wb"]
        sc = {}
        for t in names:
            if signal == "rev":
                v = x["Z"]["rev"].get(t)
                sc[t] = (0.0 if v is None else (-v if flip else v))
            else:
                s_, n_ = 0.0, 0
                for k in IT.FACTORS:
                    v = x["Z"][k].get(t)
                    if v is not None:
                        s_ += v
                        n_ += 1
                sc[t] = (s_ / n_) if n_ else 0.0
        mu = sum(wb[t] * sc[t] for t in names)
        tl = {t: sc[t] - mu for t in names}
        ss = math.sqrt(sum(wb[t] * tl[t] ** 2 for t in names)) or 1e-9
        lam = te_target / (ss * 0.18)
        if lam_mult is not None:
            lam *= lam_mult
        w = {}
        for t in names:
            cap = IT.CAP_NAME if cap_mode == "abs" else wb[t]
            a_ = max(-cap, min(cap, lam * tl[t]))
            if band:
                held[1] += 1
                ap = aprev.get(t)
                if ap:                                   # 0·None 이면 밴드가 정의되지 않는다
                    if a_ and (a_ > 0) == (ap > 0) \
                            and abs(ap) / BAND <= abs(a_) <= BAND * abs(ap):
                        a_ = ap                          # 절반~두 배 안 · 같은 부호 → 그대로
                        held[0] += 1
                a_ = max(-cap, min(cap, a_))             # 그 달 한도로 다시 자른다
            if cap > 0 and abs(a_) >= cap - 1e-12:
                binds[0] += 1
                capw[0] += abs(a_)
            binds[1] += 1
            capw[1] += abs(a_)
            w[t] = max(0.0, wb[t] + a_)
        bysec = collections.defaultdict(list)
        for t in names:
            bysec[x["sec"].get(t, "?")].append(t)
        for s, ts in bysec.items():
            da = sum(w[t] - wb[t] for t in ts)
            if abs(da) > IT.CAP_SEC:
                k_ = IT.CAP_SEC / abs(da)
                for t in ts:
                    w[t] = max(0.0, wb[t] + (w[t] - wb[t]) * k_)
        z = sum(w.values())
        w = {t: w[t] / z for t in w}
        if band:
            # «직전에 들고 있던 능동비중» = 제약·정규화를 다 거친 뒤 실제로 든 것
            aprev = {t: w[t] - wb[t] for t in names}
        acts.append(0.5 * sum(abs(w[t] - wb[t]) for t in names))
        rp = sum(w[t] * x["r"][t] for t in names)
        rb = sum(wb[t] * x["r"][t] for t in names)
        c = 0.0
        if prevw is not None:
            c = IT.COST_RT * 0.5 * sum(abs(w.get(t, 0.0) - prevw.get(t, 0.0))
                                       for t in set(w) | set(prevw))
        prevw = w
        out.append(dict(m=x["m"], p=rp, b=rb, cost=c))
    binds.append(capw[0] / capw[1] if capw[1] else 0.0)     # binds[2] = 능동비중 가중 걸림
    binds.append(held[0] / held[1] if held[1] else 0.0)     # binds[3] = 밴드가 잡은 비율
    return out, binds, acts, prevw


def solve(rows, j0, signal, cap_mode, te_target, flip=False, band=False):
    """부칙 A2 — 실현 TE 가 목표와 같아지는 λ 배수를 이분탐색으로 «푼다».

    손잡이가 아니다: 목표를 주면 답이 하나다(TE 는 λ 에 단조 증가, 한도에서 포화).
    포화해서 목표에 못 닿으면 최대치를 돌려주고 saturated=True 를 함께 준다.
    """
    def te_of(mult):
        return ev(run(rows, j0, signal, cap_mode, te_target, flip, mult, band)[0])["te"]
    lo, hi = 1e-4, 1.0
    if te_of(hi) < te_target * 100:                 # 위로 못 닿으면 배수를 키워 본다
        for _ in range(24):
            hi *= 2
            if te_of(hi) >= te_target * 100 or hi > 1e6:
                break
    if te_of(hi) < te_target * 100:
        o, b, a, lw = run(rows, j0, signal, cap_mode, te_target, flip, hi, band)
        return o, b, a, lw, hi, True
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if te_of(mid) < te_target * 100:
            lo = mid
        else:
            hi = mid
        if hi / lo < 1.0001:
            break
    o, b, a, lw = run(rows, j0, signal, cap_mode, te_target, flip, hi, band)
    return o, b, a, lw, hi, False


def ev(o):
    ex = [z["p"] - z["b"] for z in o]
    exn = [z["p"] - z["b"] - z["cost"] for z in o]
    te = IT.sd(ex) * math.sqrt(12) * 100
    mu = sum(ex) / len(ex) * 12 * 100
    mun = sum(exn) / len(exn) * 12 * 100
    t = (sum(ex) / len(ex)) / (IT.sd(ex) / math.sqrt(len(ex))) if IT.sd(ex) else 0
    tn = (sum(exn) / len(exn)) / (IT.sd(exn) / math.sqrt(len(exn))) if IT.sd(exn) else 0
    def cg(key):
        p = 1.0
        for z in o:
            p *= 1 + z[key]
        return (p ** (12 / len(o)) - 1) * 100
    return dict(n=len(o), ex=mu, ex_net=mun, te=te,
                ir=(mu / te if te else 0), ir_net=(mun / te if te else 0),
                t=t, t_net=tn, cagr=cg("p"), bcagr=cg("b"),
                win=100 * sum(1 for z in o if z["p"] > z["b"]) / len(o))


def main():
    global DATES
    print("자료를 읽는다 — 가격 격자와 투자의견 이력")
    DATES = TB.load(full=True)[0]
    TB._RAT = TB.load_ratings()
    print("  격자 %s ~ %s · 투자의견 %d종 %d건"
          % (DATES[0], DATES[-1], len(TB._RAT),
             sum(len(v[0]) for v in TB._RAT.values())))

    RESULT = {"prereg": "build/PREREG-2026-09-16-IDXREV.md",
              "prereg_commit": "8a75447d6", "rev_days": REV_DAYS,
              "judge_start": JUDGE_START, "rat_end": RAT_END, "idx": {}}

    for idx, lab in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        print("\n" + "=" * 74)
        print("══ %s (%s) ══" % (lab, idx.upper()))
        P, rows = build(idx)
        rows = [x for x in rows if x["m"] <= RAT_END]
        j0 = next((k for k, x in enumerate(rows) if x["m"] >= JUDGE_START), None)
        if j0 is None:
            raise SystemExit("❌ 판정 창 없음")
        n = len(rows) - j0
        print("판정 창 %s ~ %s · %d개월 (패널 %s ~ %s)"
              % (rows[j0]["m"], rows[-1]["m"], n, rows[0]["m"], rows[-1]["m"]))
        covs = [x["cov"]["rev"] for x in rows[j0:]]
        print("리비전 커버리지(벤치 시총) 중앙 %.0f%% · 최저 %.0f%% · 최고 %.0f%%"
              % (100 * sorted(covs)[n // 2], 100 * min(covs), 100 * max(covs)))

        TE = IT.TE_JUDGE
        CELLS = [("rev", "abs"), ("rev", "prop"), ("erc7", "abs"), ("erc7", "prop"),
                 ("rev_flip", "abs"), ("rev_flip", "prop")]
        LAB = {("rev", "abs"): "판정① 리비전 · ±1%p",
               ("rev", "prop"): "판정② 리비전 · 비중비례",
               ("erc7", "abs"): "대조 교과서7 · ±1%p",
               ("erc7", "prop"): "대조 교과서7 · 비중비례",
               ("rev_flip", "abs"): "위약 반전 · ±1%p",
               ("rev_flip", "prop"): "위약 반전 · 비중비례"}

        def cell(sig, cap, te, solved):
            fl = sig == "rev_flip"
            sg = "rev" if fl else sig
            if solved:
                o, b, a, lw, mult, sat = solve(rows, j0, sg, cap, te, fl)
            else:
                o, b, a, lw = run(rows, j0, sg, cap, te, fl)
                mult, sat = 1.0, False
            return (ev(o), b, a, o, lw, mult, sat)

        RAW = {c: cell(c[0], c[1], TE, False) for c in CELLS}     # 원 등록 그대로(λ 안 품)
        R = {c: cell(c[0], c[1], TE, True) for c in CELLS}        # 부칙 A2 — TE 를 맞춘 판

        for title, TBL in (("원 등록 그대로 (λ 를 안 푼다 · 부칙 A3 이 «지우지 않는다» 고 한 판)", RAW),
                           ("🚨 판정 대상 — TE 2.0% 를 실제로 맞춘 판 (부칙 A2)", R)):
            print()
            print("── %s" % title)
            print("%-28s %9s %8s %8s %7s %7s %8s %8s"
                  % ("", "초과수익", "추적오차", "IR", "t", "월승률", "걸림(수)", "걸림(비중)"))
            for c in CELLS:
                s, b, a, _o, _w, mult, sat = TBL[c]
                print("%-28s %+8.2f%%p %7.2f%% %+8.3f %7.2f %6.1f%% %7.1f%% %7.1f%%%s"
                      % (LAB[c], s["ex"], s["te"], s["ir"], s["t"], s["win"],
                         100 * b[0] / max(1, b[1]), 100 * b[2],
                         " ⚠포화" if sat else ""))
            print("   벤치 CAGR %.2f%%" % TBL[("rev", "abs")][0]["bcagr"])

        print()
        print("── 판정 ──────────────────────────────────────────────")
        V = {}
        for key in CELLS[:2]:
            nm = LAB[key]
            s, b, a, _o, _w, _mult, _sat = R[key]
            bind = 100 * b[0] / max(1, b[1])
            f1 = (s["ir"] > 0 and s["t"] >= 1.5)
            f2 = (s["ir_net"] > 0 and s["t_net"] >= 1.5)
            f3 = abs(s["te"] - 2.0) <= 1.0
            f4 = bind < 50.0
            fk = ("rev_flip", key[1])
            f5 = (R[fk][0]["ir"] * s["ir"] < 0)
            f6 = s["win"] > 50.0
            print("%s" % nm)
            print("   F1 IR %+.3f · t %.2f            → %s" % (s["ir"], s["t"], "통과" if f1 else "기각"))
            print("   F2 비용 뒤 IR %+.3f · t %.2f     → %s" % (s["ir_net"], s["t_net"], "통과" if f2 else "기각"))
            print("   F3 실현 TE %.2f%%                → %s" % (s["te"], "통과" if f3 else "기각"))
            print("   F4 한도걸림 %.1f%% (비중 %.1f%%)   → %s"
                  % (bind, 100 * b[2], "통과" if f4 else "🚨 기각 — 한도가 정했다"))
            print("   F5 위약 IR %+.3f                → %s" % (R[fk][0]["ir"], "통과" if f5 else "기각"))
            print("   F6 월승률 %.1f%%                 → %s" % (s["win"], "통과" if f6 else "기각"))
            print("   능동비중 중앙 %.1f%%" % (100 * sorted(a)[len(a) // 2]))
            V[nm] = dict(metrics=s, bind=bind, bind_w=round(100 * b[2], 2),
                         f1=f1, f2=f2, f3=f3, f4=f4, f5=f5, f6=f6,
                         active=round(100 * sorted(a)[len(a) // 2], 2),
                         placebo_ir=round(R[fk][0]["ir"], 3))

        print()
        print("── 측정만 (판정에 안 씀) ──────────────────────────────")
        for te in IT.TE_TARGETS:
            o, b, a, _lw, _m, sat = solve(rows, j0, "rev", "prop", te)
            s = ev(o)
            print("   리비전 · 비중비례 · TE %.0f%%   실현 %.2f%% · IR %+.3f · t %.2f%s"
                  % (te * 100, s["te"], s["ir"], s["t"], " ⚠포화" if sat else ""))
        # 긴 창
        jl = next((k for k, x in enumerate(rows) if x["cov"]["rev"] >= COV_LONG), None)
        if jl is not None and len(rows) - jl > n + 6:
            for cap in ("abs", "prop"):
                o, b, a, _lw, _m, _sat = solve(rows, jl, "rev", cap, TE)
                s = ev(o)
                print("   긴 창 %s ~ %s (%d개월) · %s   IR %+.3f · t %.2f"
                      % (rows[jl]["m"], rows[-1]["m"], s["n"],
                         "±1%p" if cap == "abs" else "비중비례", s["ir"], s["t"]))
                V["긴창 " + cap] = dict(start=rows[jl]["m"], n=s["n"],
                                        ir=round(s["ir"], 3), t=round(s["t"], 2))
        # 지금 능동 상·하위
        _s, _b, _a, _o, lastw, _m, _sat = R[("rev", "prop")]
        x = rows[-1]
        act = sorted(((t, lastw.get(t, 0.0) - x["wb"][t]) for t in x["names"]),
                     key=lambda z: -z[1])
        print("   지금(%s 신호) 능동 상위: %s" % (x["rev_d"],
              " · ".join("%s %+.2f%%p" % (t, 100 * v) for t, v in act[:8])))
        print("   지금            능동 하위: %s"
              % " · ".join("%s %+.2f%%p" % (t, 100 * v) for t, v in act[-8:]))

        RESULT["idx"][idx] = {
            "label": lab, "months": n,
            "window": [rows[j0]["m"], rows[-1]["m"]],
            "cov_rev_median": round(sorted(covs)[n // 2], 4),
            "published_ir": PUB[idx],
            "cells_te_solved": {"%s|%s" % c: dict(R[c][0], lam_mult=round(R[c][5], 4),
                                                  saturated=R[c][6],
                                                  bind_n=round(100 * R[c][1][0]
                                                               / max(1, R[c][1][1]), 2),
                                                  bind_w=round(100 * R[c][1][2], 2))
                                for c in CELLS},
            "cells_raw_lambda": {"%s|%s" % c: dict(RAW[c][0],
                                                   bind_n=round(100 * RAW[c][1][0]
                                                                / max(1, RAW[c][1][1]), 2),
                                                   bind_w=round(100 * RAW[c][1][2], 2))
                                 for c in CELLS},
            "verdicts": V,
            "now": {"as_of": x["rev_d"],
                    "over": [[t, round(100 * v, 3)] for t, v in act[:10]],
                    "under": [[t, round(100 * v, 3)] for t, v in act[-10:]]}}

    json.dump(RESULT, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
