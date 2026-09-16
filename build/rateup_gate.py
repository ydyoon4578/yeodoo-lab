# -*- coding: utf-8 -*-
"""금리 상승 국면 방어 다리 게이트 — PREREG-2026-09-16-RATEUP.md (계산 전 커밋 38226b6d3)

standalone 측정이다. 엔진(asset_backtest.py)에 등록하지 않는다 — 등록의 §1-1 이 랩의
10년 표시 상한을 쓰지 않기로 했기 때문이다(상승 국면이 2022 하나만 남아 질문이 성립하지 않는다).

산출: data/_rateup_gate.json (얼린 측정 · 커밋하지 않는다) + 표준출력 리포트
"""
from __future__ import annotations

import datetime as dt
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tech_backtest as TB                      # ann_stats·tstat·maxdd·risk_bootstrap 정본

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

COST_RT = 0.0005          # 랩 규약(왕복 5bp) — 판정은 이것으로
COST_STRESS = 0.0020      # 스트레스(왕복 20bp) — 싣기만 한다
CORR_WIN = 63             # g-sbcorr 창(한 분기)   ← 등록 §1, 바꾸지 않는다
RATE_WIN = 126            # g-rateup 창(반년)      ← 등록 §1, 바꾸지 않는다

A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
DTS = A["dates"]
PX = A["px"]
MAC = A["macro"]
RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))["monthly"]
RF = {k: v for k, v in RF.items() if k >= DTS[0][:7]}      # 패널 구간으로 자른다(랩 규약)

N = len(DTS)


def ser(t):
    return PX.get(t)


def first_ok(tickers, pad=0):
    """전 티커가 동시에 값을 갖는 첫 칸 + pad."""
    for i in range(N):
        if all((ser(t) or [None] * N)[i] is not None for t in tickers):
            return i + pad
    raise SystemExit("❌ 공통 시작점 없음: %s" % tickers)


def macro_asof(sid, d):
    """발표일 기준 최신값 — 미래를 끌어오지 않는다(asset_backtest 와 같은 산식)."""
    m = MAC.get(sid) or {}
    k = None
    for key in sorted(m):
        if key <= d:
            k = key
        else:
            break
    return m.get(k) if k else None


# 거시 계열은 매 호출 정렬하면 느리다 — 한 번만 정렬해 이분탐색한다.
_MK = {s: sorted(MAC[s]) for s in ("DGS10", "DFII10")}


def macro_fast(sid, d):
    import bisect
    ks = _MK[sid]
    j = bisect.bisect_right(ks, d) - 1
    return MAC[sid][ks[j]] if j >= 0 else None


def month_ends(lo):
    return [i for i in range(lo, N - 1) if DTS[i][:7] != DTS[i + 1][:7]]


# ── 상태변수 ──────────────────────────────────────────────────────────────
def _dret(t):
    s = ser(t)
    out = [None] * N
    for i in range(1, N):
        a, b = s[i - 1], s[i]
        if a and b:
            out[i] = b / a - 1
    return out


RSPY, RIEF = _dret("SPY"), _dret("IEF")


def corr_at(i, win=CORR_WIN):
    """DTS[i] 까지의 win 일 SPY·IEF 일간수익 상관. 결측 20% 초과면 None."""
    if i < win:
        return None
    p = [(RSPY[j], RIEF[j]) for j in range(i - win + 1, i + 1)
         if RSPY[j] is not None and RIEF[j] is not None]
    if len(p) < win * 0.8:
        return None
    n = len(p)
    mx = sum(a for a, _ in p) / n
    my = sum(b for _, b in p) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a, _ in p))
    sy = math.sqrt(sum((b - my) ** 2 for _, b in p))
    if sx <= 0 or sy <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in p) / (sx * sy)


def d10_at(i, win=RATE_WIN):
    """DTS[i] 까지 알려진 10년물 − win 거래일 전에 알려졌던 10년물."""
    if i < win:
        return None
    a, b = macro_fast("DGS10", DTS[i - win]), macro_fast("DGS10", DTS[i])
    return None if (a is None or b is None) else b - a


_CORR = {}
_D10 = {}


def st_sbcorr(i):
    if i not in _CORR:
        _CORR[i] = corr_at(i)
    c = _CORR[i]
    return None if c is None else (c >= 0.0)        # True = 위험(채권이 보험이 아니다)


def st_rateup(i):
    if i not in _D10:
        _D10[i] = d10_at(i)
    d = _D10[i]
    return None if d is None else (d > 0.0)         # True = 위험(금리가 6개월 전보다 높다)


# ── 엔진 ─────────────────────────────────────────────────────────────────
def walk(wfn, start, ends, cost=0.0):
    """asset_backtest.run_weights.walk 와 같은 산식.
    i-1 까지의 자료로 정한 비중을 i 일 수익에 적용한다 — 미래를 안 본다."""
    hold, nav, rets, turn = {}, [100.0], [], 0.0
    for i in range(start + 1, N):
        tc = 0.0
        if (i - 1) in ends or not hold:
            w = wfn(i - 1) or {}
            tot = sum(w.values())
            if tot > 0:
                w = {k: v / tot for k, v in w.items() if v > 0}
                d = sum(abs(w.get(k, 0) - hold.get(k, 0)) for k in set(w) | set(hold))
                turn += d
                tc = d / 2 * cost
                hold = w
        r = 0.0
        for t, wt in hold.items():
            s = ser(t)
            if s and s[i] is not None and s[i - 1]:
                r += wt * (s[i] / s[i - 1] - 1)
        r -= tc
        rets.append(r)
        nav.append(nav[-1] * (1 + r))
    return nav, rets, turn


def gate_w(state_fn, risk_leg="SHY", safe_leg="IEF", eq=0.60):
    def w(i):
        s = state_fn(i)
        leg = safe_leg if s is False else risk_leg      # 판정 불가(None)면 보수적으로 짧게
        return {"SPY": eq, leg: 1.0 - eq}
    return w


def const_w(d):
    return lambda i: dict(d)


def monthly(nav, dates):
    """일간 NAV → {YYYY-MM: 그 달 수익}."""
    out, last = {}, {}
    for v, d in zip(nav, dates):
        last[d[:7]] = v
    ks = sorted(last)
    prev = nav[0]
    for k in ks:
        out[k] = last[k] / prev - 1
        prev = last[k]
    return out


def fmt(m):
    return "%7.2f%% %7.2f%% %7.3f %8.2f%%" % (
        m.get("cagr") or 0, m.get("vol") or 0, m.get("sharpe") or 0, m.get("mdd") or 0)


def main():
    start = max(first_ok(["SPY", "IEF", "SHY", "GLD", "DBC", "TIP"]),
                CORR_WIN + 1, RATE_WIN + 1)
    ends = set(month_ends(start))
    dd = DTS[start:]
    print("격자 %s ~ %s (%d일) · 월말 %d회" % (dd[0], dd[-1], len(dd), len(ends)))
    print("비용 판정 왕복 %.0fbp · 스트레스 %.0fbp\n" % (COST_RT * 1e4, COST_STRESS * 1e4))

    RULES = {
        "g-sbcorr": gate_w(st_sbcorr),
        "g-rateup": gate_w(st_rateup),
    }
    CTRL = {
        "② 60/40 SPY·IEF 상시": const_w({"SPY": .6, "IEF": .4}),
        "③ 60/40 SPY·SHY 상시": const_w({"SPY": .6, "SHY": .4}),
        "④ SPY 100%": const_w({"SPY": 1.0}),
        "⑤ ^GSPC(PR)": const_w({"^GSPC": 1.0}),
    }
    # §3-1 측정만 — 방어 다리 변형(g-rateup 상태 고정)
    VAR = {
        "g-rateup→GLD": gate_w(st_rateup, risk_leg="GLD"),
        "g-rateup→DBC": gate_w(st_rateup, risk_leg="DBC"),
        "g-rateup→TIP": gate_w(st_rateup, risk_leg="TIP"),
        "g-rateup→SHY+GLD": (lambda i: {"SPY": .6, "SHY": .2, "GLD": .2}
                             if st_rateup(i) is not False else {"SPY": .6, "IEF": .4}),
        "AND(둘 다 위험일 때만)": (lambda i: {"SPY": .6, "SHY": .4}
                                  if (st_sbcorr(i) and st_rateup(i)) else {"SPY": .6, "IEF": .4}),
        "OR(하나라도 위험이면)": (lambda i: {"SPY": .6, "SHY": .4}
                                 if (st_sbcorr(i) or st_rateup(i)) else {"SPY": .6, "IEF": .4}),
    }

    R = {}
    for name, fn in list(RULES.items()) + list(CTRL.items()) + list(VAR.items()):
        nav, rets, turn = walk(fn, start, ends)
        navc, retsc, _ = walk(fn, start, ends, COST_RT)
        navs, _, _ = walk(fn, start, ends, COST_STRESS)
        R[name] = {"nav": nav, "rets": rets, "turn": turn,
                   "navc": navc, "retsc": retsc, "navs": navs,
                   "m": TB.ann_stats(nav, dd, RF), "mc": TB.ann_stats(navc, dd, RF),
                   "ms": TB.ann_stats(navs, dd, RF),
                   "mon": monthly(nav, dd)}

    yrs = (dt.date.fromisoformat(dd[-1]) - dt.date.fromisoformat(dd[0])).days / 365.25
    print("── 성적 (비용 전) " + "─" * 46)
    print("%-24s %8s %8s %7s %9s %7s" % ("", "CAGR", "변동성", "샤프", "MDD", "회전/년"))
    for name in list(RULES) + list(CTRL) + list(VAR):
        print("%-24s %s %6.2f회" % (name, fmt(R[name]["m"]), R[name]["turn"] / 2 / yrs))

    base = "② 60/40 SPY·IEF 상시"
    print("\n── 판정 (대조군 = %s) " % base + "─" * 30)
    hdr = ("%-12s %8s %8s %7s %7s %7s %7s %7s"
           % ("", "Δ샤프", "Δ샤프후", "t", "전환", "최대월", "MDDΔ", "p"))
    print(hdr)
    verdicts = {}
    for name in RULES:
        a, b = R[name], R[base]
        ds = (a["m"]["sharpe"] or 0) - (b["m"]["sharpe"] or 0)
        dsc = (a["mc"]["sharpe"] or 0) - (b["mc"]["sharpe"] or 0)
        t = TB.tstat(a["rets"], b["rets"])
        # 전환 횟수
        sf = st_sbcorr if name == "g-sbcorr" else st_rateup
        seq = [sf(i) for i in sorted(ends)]
        sw = sum(1 for x, y in zip(seq, seq[1:]) if x != y)
        on = sum(1 for x in seq if x is True)
        # F5 — 월간 초과의 한 달 쏠림
        ex = {k: a["mon"][k] - b["mon"][k] for k in a["mon"]}
        tot = sum(ex.values())
        top_k = max(ex, key=lambda k: ex[k])
        share = (ex[top_k] / tot * 100) if tot > 0 else None
        # F7 — 위험 축
        rb = TB.risk_bootstrap(a["rets"], b["rets"]) or {}
        mdd_d = (a["m"]["mdd"] or 0) - (b["m"]["mdd"] or 0)
        print("%-12s %+8.3f %+8.3f %7s %5d회 %6s %+6.2f%%p %6s  [누적초과 %+.2f%%p · 최대월 %s %+.2f%%p]"
              % (name, ds, dsc, t, sw,
                 ("%.0f%%" % share) if share is not None else "—",
                 mdd_d, rb.get("p_mdd", "—"), tot * 100, top_k, ex[top_k] * 100))
        verdicts[name] = {"d_sharpe": round(ds, 3), "d_sharpe_cost": round(dsc, 3),
                          "t": t, "switches": sw, "months_on": on, "months": len(seq),
                          "cum_excess_pp": round(tot * 100, 2),
                          "top_month": top_k, "top_month_pp": round(ex[top_k] * 100, 2),
                          "top_share": share,
                          "mdd_delta": round(mdd_d, 2), "risk": rb}

    print("\n── F6 두 규칙이 같은 것인가 " + "─" * 35)
    ma = R["g-sbcorr"]["mon"]
    mb = R["g-rateup"]["mon"]
    ks = sorted(set(ma) & set(mb))
    xs, ys = [ma[k] for k in ks], [mb[k] for k in ks]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((v - mx) ** 2 for v in xs))
    sy = math.sqrt(sum((v - my) ** 2 for v in ys))
    rho = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
    seqa = [st_sbcorr(i) for i in sorted(ends)]
    seqb = [st_rateup(i) for i in sorted(ends)]
    agree = sum(1 for x, y in zip(seqa, seqb) if x == y) / len(seqa) * 100
    print("  월간 수익 상관 %.4f · 상태 일치율 %.1f%% (%d개월)" % (rho, agree, len(seqa)))

    print("\n── 연도별 초과 (규칙 − ②, %p) " + "─" * 30)
    yset = sorted({k[:4] for k in R[base]["mon"]})
    print("%-6s %9s %9s %9s" % ("", "g-sbcorr", "g-rateup", "② 자체"))
    for y in yset:
        mk = [k for k in R[base]["mon"] if k[:4] == y]
        def cum(name):
            v = 1.0
            for k in sorted(mk):
                v *= 1 + R[name]["mon"][k]
            return (v - 1) * 100
        cb = cum(base)
        print("%-6s %+8.2f %+8.2f %8.2f" % (y, cum("g-sbcorr") - cb, cum("g-rateup") - cb, cb))

    print("\n── 상태 이력 (게이트가 켜진 구간) " + "─" * 28)
    for name, sf in (("g-sbcorr", st_sbcorr), ("g-rateup", st_rateup)):
        runs, cur = [], None
        for i in sorted(ends):
            s = sf(i)
            if s and cur is None:
                cur = DTS[i][:7]
            elif not s and cur is not None:
                runs.append((cur, DTS[i][:7]))
                cur = None
        if cur is not None:
            runs.append((cur, "진행중"))
        print("  %-9s %d구간: %s" % (name, len(runs),
                                     " · ".join("%s~%s" % r for r in runs)))

    print("\n── 진단 D (판정 아님) · 금리 상승 국면 vs 그 밖 " + "─" * 16)
    print("  상승 국면 = Δ%d일 DGS10 > 0 인 날. 일간수익을 갈라 연율화한다." % RATE_WIN)
    up = [i for i in range(start + 1, N) if st_rateup(i - 1) is True]
    dn = [i for i in range(start + 1, N) if st_rateup(i - 1) is False]
    print("  상승 %d일(%.0f%%) · 그 밖 %d일" % (len(up), len(up) / (len(up) + len(dn)) * 100, len(dn)))
    rows = []
    for t in sorted(PX):
        s = ser(t)
        def ann(idx):
            v = [s[i] / s[i - 1] - 1 for i in idx
                 if s[i] is not None and s[i - 1]]
            if len(v) < 250:
                return None, None
            m = sum(v) / len(v)
            sd = math.sqrt(sum((x - m) ** 2 for x in v) / max(1, len(v) - 1))
            return m * 252 * 100, sd * math.sqrt(252) * 100
        ru, vu = ann(up)
        rd, vd = ann(dn)
        if ru is None or rd is None:
            continue
        rows.append((t, ru, vu, rd, vd, ru - rd))
    rows.sort(key=lambda z: -z[5])          # 차이(상승 − 그밖) 내림차순
    print("  차이 순 · %d자산 전부" % len(rows))
    print("  %-8s %10s %8s %10s %8s %10s" % ("", "상승연율", "변동성", "그밖연율", "변동성", "차이"))
    for r in rows:
        print("  %-8s %+9.1f%% %7.1f%% %+9.1f%% %7.1f%% %+9.1f%%p" % r)

    # ── 결과를 보고 추가한 진단(판정에 안 쓴다) — 이 레버의 상한은 얼마인가 ──
    print("\n── 진단 O · 완벽예지 상한 (판정 아님 · 결과를 보고 추가했다) " + "─" * 5)
    print("  다음 달 IEF·SHY 중 더 나은 쪽을 «미리 알고» 40% 다리에 넣는다. 불가능한 규칙이다.")
    mE = monthly(walk(const_w({"IEF": 1.0}), start, ends)[0], dd)
    mS = monthly(walk(const_w({"SHY": 1.0}), start, ends)[0], dd)
    mq = monthly(walk(const_w({"SPY": 1.0}), start, ends)[0], dd)
    ks2 = sorted(set(mE) & set(mS) & set(mq))
    orc = base_m = 1.0
    orc_leg = 0
    for k in ks2:
        best = max(mE[k], mS[k])
        orc *= 1 + 0.6 * mq[k] + 0.4 * best
        base_m *= 1 + 0.6 * mq[k] + 0.4 * mE[k]
        orc_leg += 1 if mS[k] > mE[k] else 0
    yrs2 = (dt.date.fromisoformat(ks2[-1] + "-28") - dt.date.fromisoformat(ks2[0] + "-01")).days / 365.25
    print("  완벽예지 60/40  CAGR %.2f%%   ·  ② 60/40 CAGR %.2f%%   →  상한 %+.2f%%p/년"
          % ((orc ** (1 / yrs2) - 1) * 100, (base_m ** (1 / yrs2) - 1) * 100,
             ((orc ** (1 / yrs2)) - (base_m ** (1 / yrs2))) * 100))
    print("  그 예지가 SHY 를 고른 달 %d/%d (%.0f%%)" % (orc_leg, len(ks2), orc_leg / len(ks2) * 100))

    print("\n── 오늘 " + "─" * 55)
    i = N - 1
    c, d = corr_at(i), d10_at(i)
    print("  %s · SPY·IEF %d일 상관 %+.3f → g-sbcorr %s" %
          (DTS[i], CORR_WIN, c, "위험(SHY)" if c >= 0 else "안전(IEF)"))
    print("  %s · DGS10 %d일 변화 %+.2f%%p → g-rateup %s" %
          (DTS[i], RATE_WIN, d, "위험(SHY)" if d > 0 else "안전(IEF)"))

    out = {"prereg": "build/PREREG-2026-09-16-RATEUP.md", "prereg_commit": "38226b6d3",
           "as_of": DTS[-1], "start": dd[0], "cost_rt": COST_RT,
           "metrics": {k: {"gross": R[k]["m"], "net": R[k]["mc"], "stress20bp": R[k]["ms"],
                           "turnover_yr": round(R[k]["turn"] / 2 / yrs, 2)} for k in R},
           "verdicts": verdicts, "rho_rules": round(rho, 4), "state_agree_pct": round(agree, 1),
           "diag": [{"t": r[0], "up": round(r[1], 2), "up_vol": round(r[2], 2),
                     "other": round(r[3], 2), "other_vol": round(r[4], 2),
                     "diff": round(r[5], 2)} for r in rows],
           "today": {"corr63": round(c, 4), "d10_126": round(d, 3)}}
    p = os.path.join(DATA, "_rateup_gate.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n→ %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
