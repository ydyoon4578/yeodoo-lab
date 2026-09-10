# -*- coding: utf-8 -*-
"""고르지 않는다 — 측정한 195종을 전부 동일가중으로 담는다.

규약 build/PREREG-2026-09-11-UNION.md · 계산 전 커밋 f990d83b9.

🚨 이 파일은 «선택» 을 한 곳도 하지 않는다. 성적·판정·게시 여부를 읽는 코드가 없다.
   그것이 이 등록의 전부이므로, 나중에 누가 여기에 필터를 더하면 등록이 무효가 된다.

산출 data/_union.json (얼린 측정 · 커밋 안 함).
"""
import json
import math
import os
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

START, END = "2018-07", "2026-08"
DIV_ADJ = 0.0200          # ^GSPC 배당보정 연 2.00%p — winrate_of · asset_backtest.alpha_adj 와 같은 수
COST_RT = 0.0020          # 왕복 20bp
T_GATE = 2.5              # F1 — 랩 귀무분포(최고 t 2.493 · 널 중앙값 2.259)에서 온 수
BETA_GATE = 1.3           # F5


def load(fn):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ── 모집단 195종 ────────────────────────────────────────────────
# 등록 §1-1 그대로. 접두는 _winrate_audit 의 sid 규약과 맞춘다.
SOURCES = (("tech_strategies.json", "t-"),
           ("asset_strategies.json", "a-"),
           ("pairs_strategies.json", "p-"))


def gather():
    """(sid → {dates, nav, turnover, name}) — 성적을 한 줄도 안 본다."""
    out = {}
    for fn, pref in SOURCES:
        d = load(fn) or {}
        for s in d.get("strategies") or []:
            if not isinstance(s, dict):
                continue
            if not s.get("nav") or not s.get("dates"):
                continue
            sid = s["sid"]
            # 🚨 startswith 가드를 쓰면 안 된다(2026-09-11 실측 버그). tech 에는 sid 가
            #   't-' 로 시작하는 규칙이 셋 있고(t-chan · t-ddgate · t-chand), 가드가
            #   그것들을 't-t-chan' 이 아니라 't-chan' 으로 남겨 게시/숨김 대조군
            #   분리에서 3종이 숨김으로 잘못 갔다. 접두는 «출처» 를 뜻하므로 조건 없이 붙인다.
            #   ⚠ pairs 만 예외다 — 그 파일의 sid 가 이미 'p-ggr-top5' 형태다.
            key = sid if pref == "p-" else pref + sid
            out[key] = {"dates": s["dates"], "nav": s["nav"],
                        "turnover": s.get("turnover"), "name": s.get("name") or sid}
    return out


def monthly(dates, nav):
    """월말 수익률 — 그 달의 «마지막 관측». winrate_of 와 같은 규약.

    ⚠ 인접한 달끼리만 짝짓는다. 달을 건너뛴 구간은 안 센다(그 달을 0 으로 안 채운다).
    """
    ends = {}
    for i, d in enumerate(dates):
        ends[str(d)[:7]] = i
    ms = sorted(ends)
    out = {}
    for a, b in zip(ms, ms[1:]):
        y, mo = int(a[:4]), int(a[5:7])
        nxt = "%04d-%02d" % ((y + 1, 1) if mo == 12 else (y, mo + 1))
        if b != nxt:
            continue                       # 건너뛴 달
        p0, p1 = nav[ends[a]], nav[ends[b]]
        if p0 and p0 > 0:
            out[b] = p1 / p0 - 1.0
    return out


def bench_monthly():
    """^GSPC 월말 수익률 + 배당보정. 등록 §1-2.

    ⚠ 원천을 strategy_index._ix_load 와 같은 곳으로 둔다 — assets.json 의
      공용 dates 배열 + px['^GSPC'].  같은 자를 쓰지 않으면 승률 열과 어긋난다.
    """
    A = load("assets.json") or {}
    d, spx = A.get("dates") or [], (A.get("px") or {}).get("^GSPC")
    if not d or not spx:
        raise SystemExit("^GSPC 계열을 못 찾았다 — assets.json 구조 확인 필요")
    m = monthly(d, spx)
    return {k: v + DIV_ADJ / 12.0 for k, v in m.items()}


def months_between(a, b):
    out, cur = [], a
    while cur <= b:
        out.append(cur)
        y, mo = int(cur[:4]), int(cur[5:7])
        cur = "%04d-%02d" % ((y + 1, 1) if mo == 12 else (y, mo + 1))
    return out


def combo(M, sids, grid):
    """그 달에 관측이 있는 규칙만 동일가중. 등록 §1-2."""
    r, n = [], []
    for mth in grid:
        vs = [M[s][mth] for s in sids if mth in M[s]]
        n.append(len(vs))
        r.append(st.mean(vs) if vs else 0.0)
    return r, n


def reg(y, x):
    """y = a + b·x. (알파_연, t_알파, 베타, t_베타, 잔차변동성_연)"""
    k = len(y)
    mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    a0 = my - b * mx
    res = [c - (a0 + b * a) for a, c in zip(x, y)]
    s2 = sum(v * v for v in res) / (k - 2)
    se_b = math.sqrt(s2 / sxx)
    se_a = math.sqrt(s2 * (1.0 / k + mx * mx / sxx))
    return (a0 * 12, a0 / se_a, b, b / se_b, st.stdev(res) * math.sqrt(12))


def eff_bets(M, sids, grid):
    """유효 독립 베팅 수 = n / (1 + (n−1)·평균쌍상관). F4."""
    cols = {s: [M[s].get(m) for m in grid] for s in sids}
    keep = [s for s in sids if sum(1 for v in cols[s] if v is not None) >= 24]
    cs = []
    for i, a in enumerate(keep):
        for bb in keep[i + 1:]:
            pair = [(x, y) for x, y in zip(cols[a], cols[bb]) if x is not None and y is not None]
            if len(pair) < 24:
                continue
            xs = [p[0] for p in pair]
            ys = [p[1] for p in pair]
            mx, my = st.mean(xs), st.mean(ys)
            dx = math.sqrt(sum((v - mx) ** 2 for v in xs))
            dy = math.sqrt(sum((v - my) ** 2 for v in ys))
            if dx > 0 and dy > 0:
                cs.append(sum((v - mx) * (w - my) for v, w in zip(xs, ys)) / (dx * dy))
    if not cs:
        return None, None, 0
    avg = st.mean(cs)
    n = len(keep)
    return n / (1 + (n - 1) * avg), avg, len(cs)


def main():
    raw = gather()
    B = bench_monthly()
    grid = [m for m in months_between(START, END) if m in B]
    bx = [B[m] for m in grid]

    M = {s: monthly(v["dates"], v["nav"]) for s, v in raw.items()}
    M = {s: v for s, v in M.items() if v}
    sids = sorted(M)

    # 게시 여부는 «대조군을 나누기 위해서만» 읽는다(등록 §2). 모집단은 안 건드린다.
    wa = load("_winrate_audit.json") or {"rows": []}
    pub = {r["sid"] for r in wa["rows"] if not r.get("hidden")}
    A = [s for s in sids if s in pub]          # ② 게시
    Hd = [s for s in sids if s not in pub]     # ③ 숨김

    # 비용 — 각 규칙 수익에서 먼저 뺀다(F2)
    no_to = [s for s in sids if not isinstance(raw[s].get("turnover"), (int, float))]
    Mn = {}
    for s in sids:
        to = raw[s].get("turnover")
        drag = (to * COST_RT / 12.0) if isinstance(to, (int, float)) else 0.0
        Mn[s] = {m: v - drag for m, v in M[s].items()}

    res = {"note": "고르지 않는다 — 측정 195종 동일가중. 규약 PREREG-2026-09-11-UNION.md. 얼린 측정.",
           "prereg": "f990d83b9", "start": START, "end": END, "n_months": len(grid),
           "pop": {"total": len(sids), "published": len(A), "hidden": len(Hd)},
           "no_turnover": sorted(no_to), "div_adj": DIV_ADJ, "cost_rt": COST_RT}

    legs = {}
    for lab, ss, MM in (("union", sids, M), ("pub47", A, M), ("hid", Hd, M),
                        ("union_net", sids, Mn)):
        r, n = combo(MM, ss, grid)
        a, ta, b, tb, rv = reg(r, bx)
        legs[lab] = {"n_rules": len(ss),
                     "cagr": (math.prod(1 + v for v in r) ** (12.0 / len(r)) - 1) * 100,
                     "vol": st.stdev(r) * math.sqrt(12) * 100,
                     "alpha": a * 100, "t_alpha": ta, "beta": b, "t_beta": tb,
                     "resid_vol": rv * 100,
                     "win": 100.0 * sum(1 for x, y in zip(r, bx) if x > y) / len(r),
                     "n_in_first": n[0], "n_in_last": n[-1],
                     "n_in_min": min(n), "n_in_max": max(n)}
        if lab == "union":
            res["n_in_by_month"] = list(zip(grid, n))
    bm = math.prod(1 + v for v in bx) ** (12.0 / len(bx)) - 1
    legs["bench"] = {"cagr": bm * 100, "vol": st.stdev(bx) * math.sqrt(12) * 100}
    res["legs"] = legs

    eb, avgc, npair = eff_bets(M, sids, grid)
    res["f4"] = {"eff_bets": eb, "avg_corr": avgc, "n_pairs": npair}
    res["f1"] = legs["union"]["t_alpha"] >= T_GATE
    res["f2"] = legs["union_net"]["t_alpha"] >= T_GATE
    res["f3_selection_gain"] = {"alpha": legs["pub47"]["alpha"] - legs["union"]["alpha"],
                                "t": legs["pub47"]["t_alpha"] - legs["union"]["t_alpha"]}
    res["f5"] = legs["union"]["beta"] > BETA_GATE
    res["f6"] = legs["union"]["n_in_first"] < 30

    with open(os.path.join(DATA, "_union.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    print("모집단 %d종(게시 %d · 숨김 %d) · 월 %d개 · 회전율 없음 %d종"
          % (len(sids), len(A), len(Hd), len(grid), len(no_to)))
    print("%-11s %7s %7s %8s %7s %7s %7s %7s" %
          ("", "CAGR", "변동성", "알파", "t알파", "베타", "잔차변동", "월승률"))
    for lab in ("union", "pub47", "hid", "union_net"):
        g = legs[lab]
        print("%-11s %6.2f%% %6.2f%% %+7.2f%%p %7.2f %7.3f %6.2f%% %6.1f%%"
              % (lab, g["cagr"], g["vol"], g["alpha"], g["t_alpha"], g["beta"],
                 g["resid_vol"], g["win"]))
    print("%-11s %6.2f%% %6.2f%%" % ("bench", legs["bench"]["cagr"], legs["bench"]["vol"]))
    print("\nF1 t≥2.5  %s (t %.2f)" % ("통과" if res["f1"] else "기각", legs["union"]["t_alpha"]))
    print("F2 비용 뒤 %s (t %.2f)" % ("통과" if res["f2"] else "기각", legs["union_net"]["t_alpha"]))
    print("F3 선택이 벌어준 몫 알파 %+.2f%%p · t %+.2f"
          % (res["f3_selection_gain"]["alpha"], res["f3_selection_gain"]["t"]))
    print("F4 유효 베팅 %.2f (평균 쌍상관 %.3f · %d쌍)" % (eb, avgc, npair))
    print("F5 베타 %.3f %s" % (legs["union"]["beta"], "🚨 1.3 초과" if res["f5"] else "(1.3 이내)"))
    print("F6 첫 달 편입 %d종 %s" % (legs["union"]["n_in_first"], "🚨 30 미만" if res["f6"] else ""))


if __name__ == "__main__":
    main()
