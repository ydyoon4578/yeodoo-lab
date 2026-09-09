# -*- coding: utf-8 -*-
"""build/facrot.py — 상태 조건부 팩터 로테이션 → data/_facrot.json

규약: build/PREREG-2026-09-09-FACROT.md (계산 전 커밋 b9ca4737).

  IDXTILT 의 구조를 그대로 쓰고 **팩터 가중 한 곳만** 바꾼다 —
      상태 s(t) 의 과거(0…t−1) 표본이 12개월 이상이면,
      그 상태에서 조건부 평균 초과 > 0 인 팩터만 ERC 가중으로 쓰고 나머지는 0.
      전부 0 이면 그 달은 틸트 없음(벤치 그대로).
  문턱이 0 이다 — 손잡이를 안 만든다.

  상태 여섯 = 금리 국면 3(DFII10 3개월 ±20bp · D13 카드) × VIX 확장창 중앙값 위아래 2.
  🚨 중앙값은 확장창이다. 전 표본 중앙값은 선견이다.
  🚨 「지수 상승월/하락월」은 상태로 안 쓴다 — 끝나야 아는 것이다(등록 §0-1).

🚨 판정은 F3 이다 — 무작위 상태 셔플 200회(블록 6개월) IR 분포의 상위 5%.
   선례: PREREG-2026-09-07-REGIME0-RESULT.md 가 같은 방식으로 A7 국면을 기각했다.
🚨 계산을 복사하지 않는다 — idxtilt.py 가 얼려 낸 패널(_idxtilt_panel_*.json)을 읽는다.
🚨 얼린 측정. 자동 재굽기 금지.

    python build/facrot.py
"""
from __future__ import annotations
import collections
import io
import json
import math
import os
import random
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_facrot.json")

WARM = 48                 # IDXTILT 와 같다
SHRINK = 0.2
CAP_NAME = 0.010
CAP_SEC = 0.030
TE = 0.02                 # 판정은 2.0% 판 — IDXTILT §1-4
COST_RT = 0.0020
QT = 5
MIN_STATE = 12            # 상태별 최소 표본 — 등록 §2-1. 유일한 상수다
NSHUF = 200               # 셔플 횟수 — 등록 §3
BLOCK = 6                 # 블록 셔플 길이(개월) — 등록 §3
TH_RATE = 0.20            # D13 카드
SEED = 20260909           # 🚨 재현을 위해 고정. 결과 보고 안 바꾼다

FACTORS = ("bm", "gp", "ag", "mom", "lvol", "acc", "shiss")
FLAB = {"bm": "가치", "gp": "수익성", "ag": "투자", "mom": "모멘텀",
        "lvol": "저변동", "acc": "발생액", "shiss": "주식발행"}


def sd(v):
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def erc(C, iters=500):
    n = len(C)
    w = [1.0 / n] * n
    for _ in range(iters):
        Cw = [sum(C[i][j] * w[j] for j in range(n)) for i in range(n)]
        nw = [(w[i] / math.sqrt(Cw[i]) if Cw[i] > 1e-14 else w[i]) for i in range(n)]
        z = sum(nw)
        if z <= 0:
            return [1.0 / n] * n
        nw = [x / z for x in nw]
        if max(abs(nw[i] - w[i]) for i in range(n)) < 1e-10:
            return nw
        w = nw
    return w


def main():
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))

    def mser(k):
        m = {x: v for x, v in (A["macro"].get(k) or {}).items() if v is not None}
        return m, sorted(m)

    RY, _rk = mser("DFII10")
    VX, _vk = mser("VIXCLS")

    def asof(m, ks, d):
        last = None
        for x in ks:
            if x <= d:
                last = x
            else:
                break
        return m.get(last) if last else None

    def shift(d, mo):
        y, mm = int(d[:4]), int(d[5:7]) - mo
        y += (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        return "%04d-%02d-28" % (y, mm)

    RESULT = {}
    for IDX, IXLAB in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        P = json.load(io.open(os.path.join(DATA, "_idxtilt_panel_%s.json" % IDX),
                              encoding="utf-8"))
        rows = P["rows"]
        n = len(rows)
        print("\n" + "=" * 78)
        print("══ %s ══  패널 %d개월 %s ~ %s" % (IXLAB, n, rows[0]["m"], rows[-1]["m"]))

        # ── 상태 — 그 달 «시작» 시점(전월말)에 알 수 있는 것만 ─────────────
        rate, vix = [], []
        for x in rows:
            d = shift(x["m"], 1)
            r0, r3 = asof(RY, _rk, d), asof(RY, _rk, shift(d, 3))
            ch = (r0 - r3) if (r0 is not None and r3 is not None) else None
            rate.append("상승" if (ch is not None and ch >= TH_RATE) else
                        "하락" if (ch is not None and ch <= -TH_RATE) else "중립")
            vix.append(asof(VX, _vk, d))
        # 🚨 확장창 중앙값 — 전 표본 중앙값을 쓰면 선견이다
        vhi = []
        for j in range(n):
            past = sorted(v for v in vix[:j] if v is not None)
            m_ = past[len(past) // 2] if len(past) >= 12 else None
            vhi.append(None if (m_ is None or vix[j] is None) else (vix[j] >= m_))
        state = [("%s·%s" % (rate[j], "고변동" if vhi[j] else "저변동"))
                 if vhi[j] is not None else ("%s·—" % rate[j]) for j in range(n)]

        # ── 팩터별 단독 틸트 초과 (전 구간) — 게이트의 재료 ────────────────
        def one_month(x, fw):
            """팩터 가중 fw 로 그 달 포트를 짓고 (수익, 벤치, 비중) 을 낸다."""
            wb, Z, sec, r = x["wb"], x["Z"], x["sec"], x["r"]
            names = list(wb)
            sc = {}
            for t in names:
                s_, w_ = 0.0, 0.0
                for a_, k in enumerate(FACTORS):
                    v = Z[k].get(t)
                    if v is not None and fw[a_] > 0:
                        s_ += fw[a_] * v
                        w_ += fw[a_]
                sc[t] = (s_ / w_) if w_ > 0 else 0.0
            mu = sum(wb[t] * sc[t] for t in names)
            tl = {t: sc[t] - mu for t in names}
            ss = math.sqrt(sum(wb[t] * tl[t] ** 2 for t in names)) or 1e-9
            lam = TE / (ss * 0.18)
            w, nb = {}, 0
            for t in names:
                a_ = max(-CAP_NAME, min(CAP_NAME, lam * tl[t]))
                if abs(a_) >= CAP_NAME - 1e-12:
                    nb += 1
                w[t] = max(0.0, wb[t] + a_)
            bysec = collections.defaultdict(list)
            for t in names:
                bysec[sec[t]].append(t)
            for s_, ts in bysec.items():
                da = sum(w[t] - wb[t] for t in ts)
                if abs(da) > CAP_SEC:
                    kk = CAP_SEC / abs(da)
                    for t in ts:
                        w[t] = max(0.0, wb[t] + (w[t] - wb[t]) * kk)
            z = sum(w.values())
            w = {t: w[t] / z for t in w}
            rp = sum(w[t] * r[t] for t in names)
            rb = sum(wb[t] * r[t] for t in names)
            return rp, rb, w, nb, len(names)

        FEX = {k: [] for k in FACTORS}       # 팩터 단독 초과 — 전 구간
        for x in rows:
            for a_, k in enumerate(FACTORS):
                fw = [1.0 if b_ == a_ else 0.0 for b_ in range(len(FACTORS))]
                rp, rb, _w, _nb, _nn = one_month(x, fw)
                FEX[k].append(rp - rb)

        # ── 팩터 스프레드(ERC 공분산 재료) ────────────────────────────────
        SPD = {k: [] for k in FACTORS}
        for x in rows:
            for k in FACTORS:
                z = x["Z"][k]
                srt = sorted(z, key=lambda t: -z[t])
                q = max(3, len(srt) // QT)
                SPD[k].append(sum(x["r"][t] for t in srt[:q]) / q
                              - sum(x["r"][t] for t in srt[-q:]) / q)

        def ercw_at(j):
            C = [[0.0] * len(FACTORS) for _ in FACTORS]
            for a_ in range(len(FACTORS)):
                for b_ in range(len(FACTORS)):
                    va, vb = SPD[FACTORS[a_]][j - WARM:j], SPD[FACTORS[b_]][j - WARM:j]
                    ma, mb = sum(va) / WARM, sum(vb) / WARM
                    C[a_][b_] = sum((va[q] - ma) * (vb[q] - mb)
                                    for q in range(WARM)) / (WARM - 1)
            for a_ in range(len(FACTORS)):
                for b_ in range(len(FACTORS)):
                    if a_ != b_:
                        C[a_][b_] *= (1 - SHRINK)
            return erc(C)

        ERCW = {j: ercw_at(j) for j in range(WARM, n)}

        # ── 백테스트 ────────────────────────────────────────────────────
        def run(states, gate=True, keep=None):
            out, prevw, offs, ons = [], None, 0, []
            for j in range(WARM, n):
                fw = list(ERCW[j])
                onlist = list(FACTORS)
                if gate:
                    s = states[j]
                    past = [q for q in range(j) if states[q] == s]
                    if len(past) >= MIN_STATE:
                        onlist = []
                        for a_, k in enumerate(FACTORS):
                            mu = sum(FEX[k][q] for q in past) / len(past)
                            if mu > 0:
                                onlist.append(k)
                            else:
                                fw[a_] = 0.0
                        z = sum(fw)
                        if z <= 0:
                            offs += 1
                            x = rows[j]
                            rb = sum(x["wb"][t] * x["r"][t] for t in x["wb"])
                            out.append(dict(m=x["m"], p=rb, b=rb, cost=0.0, on=[]))
                            prevw = dict(x["wb"])
                            ons.append([])
                            continue
                        fw = [v / z for v in fw]
                ons.append(onlist)
                rp, rb, w, nb, _nn = one_month(rows[j], fw)
                c = 0.0
                if prevw is not None:
                    c = COST_RT * 0.5 * sum(abs(w.get(t, 0.0) - prevw.get(t, 0.0))
                                            for t in set(w) | set(prevw))
                prevw = w
                out.append(dict(m=rows[j]["m"], p=rp, b=rb, cost=c, on=onlist))
            return out, offs, ons

        def ev(o):
            ex = [z["p"] - z["b"] for z in o]
            exn = [z["p"] - z["b"] - z["cost"] for z in o]
            te = sd(ex) * math.sqrt(12) * 100
            mu, mun = sum(ex) / len(ex) * 12 * 100, sum(exn) / len(exn) * 12 * 100
            t = (sum(ex) / len(ex)) / (sd(ex) / math.sqrt(len(ex))) if sd(ex) else 0
            tn = (sum(exn) / len(exn)) / (sd(exn) / math.sqrt(len(exn))) if sd(exn) else 0
            return dict(ex=mu, ex_net=mun, te=te, ir=(mu / te if te else 0),
                        ir_net=(mun / te if te else 0), t=t, t_net=tn,
                        win=100 * sum(1 for z in o if z["p"] > z["b"]) / len(o))

        o_g, offs, ons = run(state, True)
        o_u, _, _ = run(state, False)
        sg, su = ev(o_g), ev(o_u)

        # ── F3 무작위 상태 셔플 (블록 6개월) ──────────────────────────────
        rnd = random.Random(SEED)
        blocks = [state[i:i + BLOCK] for i in range(0, n, BLOCK)]
        shuf = []
        for _ in range(NSHUF):
            b = blocks[:]
            rnd.shuffle(b)
            ss = [x for blk in b for x in blk][:n]
            oo, _, _ = run(ss, True)
            shuf.append(ev(oo)["ir"])
        shuf.sort()
        pct = 100.0 * sum(1 for x in shuf if x < sg["ir"]) / len(shuf)

        cnt = collections.Counter(state)
        top = cnt.most_common(1)[0]
        print()
        print("F5 상태 분포 (%d개 상태 · 최대 %s %d개월 = %.0f%%)"
              % (len(cnt), top[0], top[1], 100 * top[1] / n))
        for s_, c in cnt.most_common():
            print("     %-14s %3d개월 (%.0f%%)" % (s_, c, 100 * c / n))
        print()
        print("%-28s %9s %8s %9s %7s %7s" % ("", "초과수익", "추적오차", "IR", "t", "월승률"))
        print("%-28s %+8.2f%%p %7.2f%% %9.3f %7.2f %6.1f%%"
              % ("조건부 게이트 (전략)", sg["ex"], sg["te"], sg["ir"], sg["t"], sg["win"]))
        print("%-28s %+8.2f%%p %7.2f%% %9.3f %7.2f %6.1f%%"
              % ("무조건 ERC (대조군 1)", su["ex"], su["te"], su["ir"], su["t"], su["win"]))
        print("%-28s %+8.2f%%p %7.2f%% %9s %7s %7s" % ("벤치(시총가중 PIT)", 0, 0, "—", "—", "—"))
        print()
        print("── 판정 ────────────────────────────────────────────────")
        print("F1 🚨 조건부 − 무조건  ΔIR %+.3f (%.3f vs %.3f)          → %s"
              % (sg["ir"] - su["ir"], sg["ir"], su["ir"],
                 "통과" if sg["ir"] > su["ir"] else "기각"))
        print("F2 🚨 IR %.3f · t %.2f (문턱 IR>0 & t≥1.5)                → %s"
              % (sg["ir"], sg["t"], "통과" if (sg["ir"] > 0 and sg["t"] >= 1.5) else "기각"))
        print("F3 🚨 셔플 %d회 IR 분포에서 백분위 %.1f%% (문턱 95%%)        → %s"
              % (NSHUF, pct, "통과" if pct >= 95 else "기각"))
        print("      셔플 IR  중앙 %.3f · 5%% %.3f · 95%% %.3f · 최고 %.3f | 실측 %.3f"
              % (shuf[NSHUF // 2], shuf[int(NSHUF * .05)], shuf[int(NSHUF * .95)],
                 shuf[-1], sg["ir"]))
        print("F4    비용 뒤 IR %.3f · t %.2f                            → %s"
              % (sg["ir_net"], sg["t_net"],
                 "통과" if (sg["ir_net"] > su["ir_net"] and sg["ir_net"] > 0
                            and sg["t_net"] >= 1.5) else "기각"))
        chg = sum(1 for j in range(1, len(ons)) if set(ons[j]) != set(ons[j - 1]))
        print("F6    틸트를 끈 달 %d/%d (%.0f%%) · 켜진 팩터 조합이 바뀐 달 %d회"
              % (offs, len(o_g), 100 * offs / len(o_g), chg))
        print()
        print("F7 상태별로 켜진 팩터 (표본 밖 구간 · 마지막 달 기준)")
        seen = {}
        for j in range(WARM, n):
            seen[state[j]] = ons[j - WARM]
        for s_ in sorted(seen, key=lambda z: -cnt[z]):
            v = seen[s_]
            print("     %-14s %s" % (s_, (" · ".join(FLAB[k] for k in v)) if v else "«전부 끔»"))

        RESULT[IDX] = {"label": IXLAB, "n_oos": len(o_g),
                       "window": [o_g[0]["m"], o_g[-1]["m"]],
                       "gated": sg, "uncond": su,
                       "shuffle": {"n": NSHUF, "pct": pct, "med": shuf[NSHUF // 2],
                                   "p95": shuf[int(NSHUF * .95)], "max": shuf[-1]},
                       "state_dist": dict(cnt), "off_months": offs, "combo_changes": chg,
                       "last_on": {k: v for k, v in seen.items()},
                       "rows": [{"m": z["m"], "p": round(z["p"], 6), "b": round(z["b"], 6),
                                 "cost": round(z["cost"], 6), "on": z["on"]} for z in o_g]}

    doc = {"note": "상태 조건부 팩터 로테이션. 규약 PREREG-2026-09-09-FACROT.md. 얼린 측정.",
           "prereg": "b9ca4737", "warm": WARM, "min_state": MIN_STATE,
           "nshuf": NSHUF, "block": BLOCK, "seed": SEED, "te": TE,
           "factors": list(FACTORS), "by_index": RESULT}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
