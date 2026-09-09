# -*- coding: utf-8 -*-
"""build/idxtilt.py — 지수 강화(enhanced index): 벤치 비중에서 팩터로 틸팅 → data/_idxtilt.json

규약: build/PREREG-2026-09-09-IDXTILT.md (계산 전 커밋 bb21306c).

  두 벤치를 «나란히» 돌린다 — SPX 시총가중 · NDX 시총가중 (둘 다 그 달 실제 편입명단).

    w(t) = w_bench(t) + λ · tilt(t)
    tilt = 합성점수의 «섹터 내 z» 를 벤치 비중가중 평균 0 으로 맞춘 것
    제약  롱온리 w ≥ 0 · 개별 능동 ±1.0%p · 섹터 능동 ±3.0%p

  팩터 일곱은 교과서가 정했다(등록 §1-1) — 성적으로 안 골랐다.
  합성 가중은 **진짜 ERC**: 롤링 48개월 팩터 스프레드 공분산 → 대각 0.2 축소 → 고정점 반복.

🚨 판정 지표는 **정보비율 IR = 연 초과수익 ÷ 연 추적오차**. 이 랩이 처음 재는 축이다.
🚨 λ 는 안 고른다. TE 목표 1/2/3% 세 벌을 다 내고 **판정은 2.0% 판**이다(등록 §1-4).
🚨 채점기 사본을 안 만든다 — TB.ttm2·asof_fund·_gross_profit 같은 공유 원시함수로 낸다.
🚨 얼린 측정 — 산출물은 밑줄 접두. 자동 재굽기 금지.

    python build/idxtilt.py
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
OUT = os.path.join(DATA, "_idxtilt.json")
sys.path.insert(0, HERE)

WARM = 48                 # ERC 공분산 롤링 창(개월) — BOK 의 수
SHRINK = 0.2              # 대각 축소 — BOK 의 수
CAP_NAME = 0.010          # 개별 능동 한도 ±1.0%p
CAP_SEC = 0.030           # 섹터 능동 한도 ±3.0%p
TE_TARGETS = (0.01, 0.02, 0.03)
TE_JUDGE = 0.02           # 🚨 판정은 2.0% 판. 계산 전에 정했다
COST_RT = 0.0020
QT = 5                    # 팩터 스프레드용 5분위

# 등록 §1-1 — 부호는 «클수록 좋다» 로 통일한다
FACTORS = ("bm", "gp", "ag", "mom", "lvol", "acc", "shiss")
FLAB = {"bm": "가치 B/M", "gp": "수익성 GP/자산", "ag": "투자(자산성장 역)",
        "mom": "모멘텀 12-1", "lvol": "저변동(60일 역)", "acc": "발생액 역",
        "shiss": "순주식발행 역"}


def sd(v):
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def zs(d):
    """딕셔너리 값을 z 로. 표준편차 0 이면 전부 0."""
    v = list(d.values())
    if len(v) < 3:
        return {k: 0.0 for k in d}
    m = sum(v) / len(v)
    s = sd(v)
    if s <= 0:
        return {k: 0.0 for k in d}
    # 윈저 ±3 — 극단값 하나가 단면을 지배하지 않게(랩 관례)
    return {k: max(-3.0, min(3.0, (x - m) / s)) for k, x in d.items()}


def erc(C, iters=500):
    """동일위험기여 가중. RC_i = w_i·(Cw)_i 가 전부 같아지도록 고정점 반복.

    🚨 Spinu CCD 대신 표준 고정점을 쓴다 — 7×7 이라 수렴이 빠르다(등록 §1-3).
    """
    n = len(C)
    w = [1.0 / n] * n
    for _ in range(iters):
        Cw = [sum(C[i][j] * w[j] for j in range(n)) for i in range(n)]
        nw = []
        for i in range(n):
            x = Cw[i]
            nw.append(w[i] / math.sqrt(x) if x > 1e-14 else w[i])
        z = sum(nw)
        if z <= 0:
            return [1.0 / n] * n
        nw = [x / z for x in nw]
        if max(abs(nw[i] - w[i]) for i in range(n)) < 1e-10:
            w = nw
            break
        w = nw
    return w


def main():
    import tech_backtest as TB

    IH = json.load(io.open(os.path.join(DATA, "index_history.json"),
                           encoding="utf-8"))["months"]
    dates, px, vlm, hid, lod, meta, rf_ = TB.load(full=True)
    di = {d: i for i, d in enumerate(dates)}
    FU = TB.load_fund()
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    ad = {d: i for i, d in enumerate(A["dates"])}
    CB = {k: v for k, v in (A["macro"].get("DGS3MO") or {}).items() if v is not None}
    _ck = sorted(CB)

    # 월말 격자 — 가격 격자에서 각 달의 마지막 거래일
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    months = sorted(me)

    def cashm(mm):
        k = None
        for key in _ck:
            if key <= mm + "-28":
                k = key
            else:
                break
        return (CB.get(k) or 0.0) / 100 / 12 if k else 0.0

    # ── 팩터 산출 — 공유 원시함수만 쓴다(채점기 사본 금지) ──────────────
    def facs(t, i, d):
        """일곱 팩터. 못 내면 None 을 담는다(부분 결측 허용)."""
        f = FU.get(t)
        p = px[t][i] if px.get(t) else None
        if not p or p <= 0:
            return None
        out = {}
        sn = TB.asof_fund(f.get("sh"), d) if f else None
        mc = (sn * p) if (sn and sn > 0) else None
        if f and mc:
            eq = TB.asof_fund(f.get("eq"), d)
            out["bm"] = (eq / mc) if (eq is not None and eq > 0) else None
            g, _rv = TB._gross_profit(f, d)
            at = TB.asof_fund(f.get("asset"), d)
            out["gp"] = (g / at) if (g is not None and at and at > 0) else None
            at3 = TB.asof_fund(f.get("asset"), TB.shift_year(d, 1)) \
                if hasattr(TB, "shift_year") else None
            if at3 is None:
                y = int(d[:4]) - 1
                at3 = TB.asof_fund(f.get("asset"), "%04d%s" % (y, d[4:]))
            out["ag"] = (-(at / at3 - 1)) if (at and at3 and at3 > 0) else None
            ni = TB.ttm2(f.get("ni"), f.get("ni_a"), d)
            cfo = TB.ttm2(f.get("cfo"), f.get("cfo_a"), d)
            out["acc"] = (-((ni - cfo) / at)) if (ni is not None and cfo is not None
                                                 and at and at > 0) else None
            y = int(d[:4]) - 1
            sn1 = TB.asof_fund(f.get("sh"), "%04d%s" % (y, d[4:]))
            out["shiss"] = (-(sn / sn1 - 1)) if (sn1 and sn1 > 0) else None
        else:
            for k in ("bm", "gp", "ag", "acc", "shiss"):
                out[k] = None
        a = px[t]
        j12, j1 = i - 252, i - 21
        out["mom"] = ((a[j1] / a[j12] - 1) if (j12 >= 0 and a[j12] and a[j1]
                                              and a[j12] > 0) else None)
        j60 = i - 60
        if j60 >= 0:
            r = [a[k] / a[k - 1] - 1 for k in range(j60 + 1, i + 1)
                 if a[k] and a[k - 1] and a[k - 1] > 0]
            out["lvol"] = (-sd(r)) if len(r) > 40 else None
        else:
            out["lvol"] = None
        return out

    RESULT = {}
    for IDX, IXLAB in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        print("\n" + "=" * 74)
        print("══ %s (%s) ══" % (IXLAB, IDX.upper()))
        rows = []
        for mi in range(len(months) - 1):
            mm, mm1 = months[mi], months[mi + 1]
            i, i1 = me[mm], me[mm1]
            hist = IH.get(mm)
            if not hist:
                continue
            U = [t for t in (hist.get(IDX) or []) if px.get(t) and px[t][i] and px[t][i1]]
            if len(U) < 50:
                continue
            # 벤치 비중 = 시총가중
            mc = {}
            for t in U:
                f = FU.get(t)
                sn = TB.asof_fund(f.get("sh"), mm + "-28") if f else None
                if sn and sn > 0:
                    mc[t] = sn * px[t][i]
            if len(mc) < 40:
                continue
            zsum = sum(mc.values())
            wb = {t: mc[t] / zsum for t in mc}
            names = sorted(wb)
            # 팩터
            F = {t: facs(t, i, mm + "-28") for t in names}
            sec = {t: ((meta.get(t) or {}).get("sector") or "?") for t in names}
            # 섹터 내 z — 섹터당 3종 이상일 때만, 아니면 전체 z
            Z = {}
            cov = {}
            for k in FACTORS:
                raw = {t: F[t][k] for t in names if F.get(t) and F[t].get(k) is not None}
                cov[k] = sum(wb[t] for t in raw)
                bysec = collections.defaultdict(dict)
                for t, v in raw.items():
                    bysec[sec[t]][t] = v
                z = {}
                for s, dd in bysec.items():
                    z.update(zs(dd) if len(dd) >= 5 else {t: 0.0 for t in dd})
                Z[k] = z
            rows.append(dict(m=mm1, i=i, i1=i1, names=names, wb=wb, sec=sec, Z=Z,
                             cov=cov, cash=cashm(mm1),
                             r={t: px[t][i1] / px[t][i] - 1 for t in names}))
        # ── 🚨 패널을 얼려 내보낸다 — 다음 등록(FACROT)이 «계산을 복사하지 않고» 읽는다.
        #    판정 계산은 안 건드린다(덤프만 추가).
        _pan = os.path.join(DATA, "_idxtilt_panel_%s.json" % IDX)
        io.open(_pan, "w", encoding="utf-8").write(json.dumps(
            {"note": "idxtilt 가 만든 월별 패널(벤치비중·섹터·팩터 z·수익). 얼린 측정.",
             "prereg": "bb21306c", "index": IDX, "factors": list(FACTORS),
             "rows": [{"m": x["m"], "wb": {t: round(v, 8) for t, v in x["wb"].items()},
                       "sec": x["sec"], "cash": x["cash"],
                       "r": {t: round(v, 6) for t, v in x["r"].items()},
                       "cov": x["cov"],
                       "Z": {k: {t: round(v, 4) for t, v in x["Z"][k].items()}
                             for k in FACTORS}} for x in rows]},
            ensure_ascii=False))
        print("   → 패널 덤프 %s (%.0fMB)" % (os.path.basename(_pan),
                                              os.path.getsize(_pan) / 1e6))

        n = len(rows)
        print("월 %d (%s ~ %s) · 벤치 종목수 중앙 %d"
              % (n, rows[0]["m"], rows[-1]["m"],
                 sorted(len(x["names"]) for x in rows)[n // 2]))
        covm = {k: sorted(x["cov"][k] for x in rows)[n // 2] for k in FACTORS}
        print("F8 팩터별 «벤치 시총 커버리지» 중앙: " +
              " · ".join("%s %.0f%%" % (FLAB[k][:6], 100 * covm[k]) for k in FACTORS))

        # 팩터 스프레드 수익 (5분위 상−하, 동일가중) — ERC 공분산의 재료
        SPD = {k: [] for k in FACTORS}
        for x in rows:
            for k in FACTORS:
                z = x["Z"][k]
                srt = sorted(z, key=lambda t: -z[t])
                q = max(3, len(srt) // QT)
                hi = srt[:q]
                lo = srt[-q:]
                SPD[k].append(sum(x["r"][t] for t in hi) / len(hi)
                              - sum(x["r"][t] for t in lo) / len(lo))

        # ── 백테스트 ────────────────────────────────────────────────
        def run(te_target, mode):
            """mode: 'erc' | 'eq' | 단일 팩터명"""
            out, ercw, prevw, act, binds = [], [], None, [], [0, 0, 0]
            for j in range(WARM, n):
                x = rows[j]
                if mode == "erc":
                    C = [[0.0] * len(FACTORS) for _ in FACTORS]
                    for a_ in range(len(FACTORS)):
                        for b_ in range(len(FACTORS)):
                            va = SPD[FACTORS[a_]][j - WARM:j]
                            vb = SPD[FACTORS[b_]][j - WARM:j]
                            ma, mb = sum(va) / WARM, sum(vb) / WARM
                            C[a_][b_] = sum((va[q] - ma) * (vb[q] - mb)
                                            for q in range(WARM)) / (WARM - 1)
                    for a_ in range(len(FACTORS)):
                        for b_ in range(len(FACTORS)):
                            if a_ != b_:
                                C[a_][b_] *= (1 - SHRINK)
                    fw = erc(C)
                elif mode == "eq":
                    fw = [1.0 / len(FACTORS)] * len(FACTORS)
                else:
                    fw = [1.0 if k == mode else 0.0 for k in FACTORS]
                ercw.append(fw)
                # 합성 점수
                sc = {}
                for t in x["names"]:
                    s_, w_ = 0.0, 0.0
                    for a_, k in enumerate(FACTORS):
                        v = x["Z"][k].get(t)
                        if v is not None:
                            s_ += fw[a_] * v
                            w_ += fw[a_]
                    sc[t] = (s_ / w_) if w_ > 0 else 0.0
                # 벤치 비중가중 평균 0 으로
                mu = sum(x["wb"][t] * sc[t] for t in x["names"])
                tl = {t: sc[t] - mu for t in x["names"]}
                # 스케일 — 사전 TE 를 대략 맞춘다(단면 분산 기준). 그 뒤 실현 TE 로 보정.
                ss = math.sqrt(sum(x["wb"][t] * tl[t] ** 2 for t in x["names"])) or 1e-9
                lam = te_target / (ss * 0.18) / math.sqrt(12) * math.sqrt(12)
                w = {}
                for t in x["names"]:
                    a_ = lam * tl[t]
                    a_ = max(-CAP_NAME, min(CAP_NAME, a_))
                    if abs(a_) >= CAP_NAME - 1e-12:
                        binds[0] += 1
                    binds[2] += 1
                    w[t] = max(0.0, x["wb"][t] + a_)
                # 섹터 능동 한도
                bysec = collections.defaultdict(list)
                for t in x["names"]:
                    bysec[x["sec"][t]].append(t)
                for s, ts in bysec.items():
                    da = sum(w[t] - x["wb"][t] for t in ts)
                    if abs(da) > CAP_SEC:
                        binds[1] += 1
                        k_ = CAP_SEC / abs(da)
                        for t in ts:
                            w[t] = max(0.0, x["wb"][t] + (w[t] - x["wb"][t]) * k_)
                z = sum(w.values())
                w = {t: w[t] / z for t in w}
                act.append(0.5 * sum(abs(w[t] - x["wb"][t]) for t in x["names"]))
                rp = sum(w[t] * x["r"][t] for t in x["names"])
                rb = sum(x["wb"][t] * x["r"][t] for t in x["names"])
                c = 0.0
                if prevw is not None:
                    c = COST_RT * 0.5 * sum(abs(w.get(t, 0.0) - prevw.get(t, 0.0))
                                            for t in set(w) | set(prevw))
                prevw = w
                out.append(dict(m=x["m"], p=rp, b=rb, cost=c, cash=x["cash"]))
            return out, ercw, act, binds

        def ev(o):
            ex = [z["p"] - z["b"] for z in o]
            exn = [z["p"] - z["b"] - z["cost"] for z in o]
            te = sd(ex) * math.sqrt(12) * 100
            mu = sum(ex) / len(ex) * 12 * 100
            mun = sum(exn) / len(exn) * 12 * 100
            t = (sum(ex) / len(ex)) / (sd(ex) / math.sqrt(len(ex))) if sd(ex) else 0
            tn = (sum(exn) / len(exn)) / (sd(exn) / math.sqrt(len(exn))) if sd(exn) else 0
            def cg(key):
                p = 1.0
                for z in o:
                    p *= 1 + z[key]
                return (p ** (12 / len(o)) - 1) * 100
            return dict(ex=mu, ex_net=mun, te=te, ir=mu / te if te else 0,
                        ir_net=mun / te if te else 0, t=t, t_net=tn,
                        cagr=cg("p"), bcagr=cg("b"),
                        win=100 * sum(1 for z in o if z["p"] > z["b"]) / len(o))

        R = {}
        for te in TE_TARGETS:
            o, ercw, act, binds = run(te, "erc")
            R[("erc", te)] = (ev(o), o, ercw, act, binds)
        o, _, act2, b2 = run(TE_JUDGE, "eq")
        R[("eq", TE_JUDGE)] = (ev(o), o, None, act2, b2)
        for k in FACTORS:
            o, _, _, _ = run(TE_JUDGE, k)
            R[(k, TE_JUDGE)] = (ev(o), o, None, None, None)

        st, o, ercw, act, binds = R[("erc", TE_JUDGE)]
        print()
        print("표본 밖 %s ~ %s · %d개월 (warm %d)"
              % (o[0]["m"], o[-1]["m"], len(o), WARM))
        print()
        print("%-26s %8s %8s %8s %7s %7s" % ("", "초과수익", "추적오차", "IR", "t", "월승률"))
        for lab, key in (("ERC 합성 · TE 1%%", ("erc", 0.01)),
                         ("**ERC 합성 · TE 2%% (판정)**", ("erc", 0.02)),
                         ("ERC 합성 · TE 3%%", ("erc", 0.03)),
                         ("동일가중 1/7 · TE 2%%", ("eq", 0.02))):
            s = R[key][0]
            print("%-26s %+7.2f%%p %7.2f%% %8.3f %7.2f %6.1f%%"
                  % (lab, s["ex"], s["te"], s["ir"], s["t"], s["win"]))
        print("%-26s %+7.2f%%p %7.2f%% %8s %7s %6s"
              % ("벤치(시총가중 PIT)", 0.0, 0.0, "—", "—", "—"))
        print("   벤치 CAGR %.2f%% · 전략 CAGR %.2f%%" % (st["bcagr"], st["cagr"]))

        print()
        print("── 판정 ──────────────────────────────────────────────")
        print("F1 🚨 IR %.3f · t %.2f (문턱 1.5)                       → %s"
              % (st["ir"], st["t"], "통과" if (st["ir"] > 0 and st["t"] >= 1.5) else "기각"))
        seq = R[("eq", TE_JUDGE)][0]
        print("F2    ERC %.3f vs 동일가중 %.3f (Δ%+.3f)                → %s"
              % (st["ir"], seq["ir"], st["ir"] - seq["ir"],
                 "ERC 가 낫다" if st["ir"] > seq["ir"] else "🚨 ERC 가 값을 못 냈다"))
        print("F3    실현 추적오차 %.2f%% (목표 2.0%% ± 1.0)              → %s"
              % (st["te"], "통과" if abs(st["te"] - 2.0) <= 1.0 else "🚨 크기 조절 실패"))
        print("F4    비용 뒤 초과 %+.2f%%p · IR %.3f · t %.2f            → %s"
              % (st["ex_net"], st["ir_net"], st["t_net"],
                 "통과" if (st["ir_net"] > 0 and st["t_net"] >= 1.5) else "기각"))
        print("F5    개별 한도에 걸린 비율 %.1f%% · 섹터 한도 발동 %d회"
              % (100 * binds[0] / max(1, binds[2]), binds[1]))
        print("F6    능동비중(active share) 중앙 %.1f%% · 월 회전 중앙 %.1f%%"
              % (100 * sorted(act)[len(act) // 2],
                 100 * sorted(z["cost"] / COST_RT for z in o)[len(o) // 2]))
        print()
        print("팩터 단독 (같은 틸트 구조 · TE 2%)")
        for k in FACTORS:
            s = R[(k, TE_JUDGE)][0]
            print("   %-16s 초과 %+6.2f%%p · TE %5.2f%% · IR %+6.3f · t %5.2f"
                  % (FLAB[k], s["ex"], s["te"], s["ir"], s["t"]))
        wl = [sum(w[a_] for w in ercw) / len(ercw) for a_ in range(len(FACTORS))]
        print()
        print("ERC 평균 가중: " + " · ".join("%s %.1f%%" % (FLAB[FACTORS[a_]][:6], 100 * wl[a_])
                                             for a_ in range(len(FACTORS))))
        # ── 진단용 덤프 — 국면별 팩터 성적을 재려면 팩터별 월별 초과가 필요하다.
        #    🚨 판정 계산은 안 건드린다. 등록 뒤 «재기만» 하는 자료다.
        fac_rows = {}
        for k in FACTORS:
            oo = R[(k, TE_JUDGE)][1]
            fac_rows[k] = [round(z["p"] - z["b"], 6) for z in oo]
        RESULT[IDX] = {
            "label": IXLAB, "n_oos": len(o),
            "fac_excess": fac_rows,
            "spread": {k: [round(v, 6) for v in SPD[k][WARM:]] for k in FACTORS},
            "bench_ret": [round(z["b"], 6) for z in o],
            "window": [o[0]["m"], o[-1]["m"]],
            "cov": covm, "erc_w": wl,
            "main": st, "eq": seq,
            "te_levels": {("%.0f" % (te * 100)): R[("erc", te)][0] for te in TE_TARGETS},
            "single": {k: R[(k, TE_JUDGE)][0] for k in FACTORS},
            "binds": binds, "active_med": sorted(act)[len(act) // 2],
            "rows": [{"m": z["m"], "p": round(z["p"], 6), "b": round(z["b"], 6),
                      "cost": round(z["cost"], 6)} for z in o]}

    doc = {"note": "지수 강화 — 벤치 비중 + 팩터 틸트. 규약 PREREG-2026-09-09-IDXTILT.md. 얼린 측정.",
           "prereg": "bb21306c", "warm": WARM, "shrink": SHRINK,
           "cap_name": CAP_NAME, "cap_sec": CAP_SEC, "te_judge": TE_JUDGE,
           "factors": list(FACTORS), "by_index": RESULT}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
