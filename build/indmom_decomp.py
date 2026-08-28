# -*- coding: utf-8 -*-
"""build/indmom_decomp.py — 산업 모멘텀과 그 잔차 → data/indmom.json

규약: build/PREREG-2026-08-28-INDMOM.md (계산 전 커밋 32348042 · 규칙·예상·실패 조건).

  세 벌을 같은 격자·같은 비용으로 나란히 돌린다.
    S 종목 12-1        — 랩의 x-mom12 와 같은 신호
    I 산업 12-1        — 산업그룹 시총가중 12-1 상위 3, 뽑힌 그룹 전 종목 동일가중
    R 산업잔차 12-1     — 종목 12-1 − 자기 산업그룹 12-1, 그 잔차로 상위 N
  S 가 크고 R 이 작으면 «모멘텀은 산업을 사는 것» 이고, R 이 살아 있으면 아니다.

🚨 엔진(tech_backtest.py)을 고치지 않는다. 그 안의 load·ret·metrics 를 **불러 쓴다** —
  채점·수익 계산 규칙을 베끼면 두 벌이 되고 한쪽만 고쳐지는 날이 온다.
🚨 상수는 전부 사전등록 §1 에서 왔다. 결과를 보고 하나도 바꾸지 않는다.

    python build/indmom_decomp.py
"""
from __future__ import annotations
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
OUT = os.path.join(DATA, "indmom.json")
sys.path.insert(0, HERE)

# ── 사전등록 §1 — 여섯 상수. 결과를 보고 바꾸지 않는다 ──────────────────────
LONG, SKIP = 252, 21      # 12-1
MIN_N = 8                 # 산업그룹 최소 종목 수
TOP_G = 3                 # 상위 산업그룹 수
COST = 0.0005             # 편도 5bp
MIN_GROUPS = 12           # §4-2 — 후보 그룹이 이보다 적은 달은 «순위» 가 아니다


def main():
    import tech_backtest as TB
    dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
    FU = TB.load_fund()
    me = TB.month_ends(dates)
    print("격자 %s ~ %s (%d일) · 월말 %d회" % (dates[0], dates[-1], len(dates), len(me)))

    # 산업그룹은 members.json 의 grp — home_perf 의 일간판이 쓰는 바로 그 값이다.
    MB = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))
    # ⚠ members 는 **티커를 키로 하는 딕셔너리**다(레코드 안에 티커 필드가 없다).
    #   list(values()) 로 펴면 티커를 잃는다 — 한 번 밟았다.
    rows = MB.get("members") or {}
    assert isinstance(rows, dict) and len(rows) > 100, "members 모양이 바뀌었다"
    GRP = {t: (r.get("grp") or "") for t, r in rows.items()}
    SEC = {t: (r.get("sector") or "") for t, r in rows.items()}
    print("산업그룹 자료 %d종목 · %d그룹" % (len(GRP), len(set(GRP.values()) - {""})))

    def mom(t, i):
        """12-1. ⚠ 랩의 x-mom12 와 **같은 식**이다 — 사본을 만들지 않으려 같은 꼴로 쓴다."""
        P = px.get(t)
        if not P:
            return None
        a = TB.ret(P, i, LONG)
        if a is None:
            return None
        return a - (TB.ret(P, i, SKIP) or 0)

    def mcap(t, i):
        f = FU.get(t) or {}
        sh = TB.asof_fund(f.get("sh"), dates[i])
        p = px[t][i] if px.get(t) and i < len(px[t]) else None
        return (sh * p) if (sh and p and sh > 0 and p > 0) else None

    diag = {"groups": [], "thin_dropped": [], "sec_conc": 0, "months": 0,
            "thin_names": {}}
    # X — 현행 x-indmom 명세 그대로(섹터 11 · 6개월 **무이격** · 상위 2 · 동일가중).
    #   사전등록 §5 가 요구한 대조다: 이격이 얼마를 만들었나.
    picks = {"S": [], "I": [], "R": [], "X": []}   # (i0, i1, [티커])

    for k in range(len(me) - 1):
        i0, i1 = me[k], me[k + 1]
        if i0 < LONG + 5:
            continue
        # 종목 12-1
        sm = {}
        for t in px:
            v = mom(t, i0)
            if v is not None and v == v:
                sm[t] = v
        if len(sm) < 100:
            continue
        # 산업그룹 시총가중 12-1
        by = {}
        for t, v in sm.items():
            g = GRP.get(t)
            if not g:
                continue
            m = mcap(t, i0)
            if m:
                by.setdefault(g, []).append((t, v, m))
        # ⚠ 최소 종목 수 문턱 — 얇은 그룹이 뽑히면 «몇 종목 베팅» 이 된다(사전등록 §1)
        thin = [g for g, v in by.items() if len(v) < MIN_N]
        for g in thin:
            diag["thin_names"][g] = diag["thin_names"].get(g, 0) + 1
        ok = {g: v for g, v in by.items() if len(v) >= MIN_N}
        diag["groups"].append(len(ok))
        diag["thin_dropped"].append(len(thin))
        if len(ok) < 3:
            continue
        diag["months"] += 1
        gret = {g: sum(v * m for _t, v, m in vs) / sum(m for _t, _v, m in vs)
                for g, vs in ok.items()}
        win = [g for g, _r in sorted(gret.items(), key=lambda x: -x[1])[:TOP_G]]
        # §4-3 — 상위 3이 한 섹터에서 2개 이상인 달을 센다
        _s = [SEC.get(ok[g][0][0], "") for g in win]
        if len(set(_s)) < len(_s):
            diag["sec_conc"] += 1
        # I — 뽑힌 그룹 전 종목 동일가중(산업 안에서 안 고른다)
        picks["I"].append((i0, i1, [t for g in win for t, _v, _m in ok[g]]))
        # S — 종목 12-1 상위 N. ⚠ N 은 I 의 그 달 보유 수와 같게 맞춘다(바스켓 크기가
        #   다르면 분산 차이가 성적 차이로 새어 든다).
        n = len(picks["I"][-1][2])
        picks["S"].append((i0, i1, [t for t, _v in
                                    sorted(sm.items(), key=lambda x: -x[1])[:n]]))
        # R — 산업잔차 = 종목 12-1 − 자기 그룹 12-1
        res = {t: sm[t] - gret[GRP[t]] for t in sm
               if GRP.get(t) in gret}
        picks["R"].append((i0, i1, [t for t, _v in
                                    sorted(res.items(), key=lambda x: -x[1])[:n]]))
        # X — 현행 명세. ⚠ 신호가 다르므로 여기서 따로 계산한다(6개월 무이격 · 섹터).
        bys = {}
        for t in px:
            _r6 = TB.ret(px[t], i0, 126)
            _sc = SEC.get(t)
            if _r6 is not None and _sc:
                bys.setdefault(_sc, []).append((t, _r6))
        if len(bys) >= 2:
            _sr = {g: sum(r for _t, r in v) / len(v) for g, v in bys.items() if v}
            _w2 = [g for g, _r in sorted(_sr.items(), key=lambda x: -x[1])[:2]]
            picks["X"].append((i0, i1, [t for g in _w2 for t, _r in bys[g]]))

    # ── 수익 ─────────────────────────────────────────────────────────────────
    def run(seq):
        r, turn, prev = [], [], None
        for i0, i1, names in seq:
            g = []
            for t in names:
                P = px.get(t)
                if P and i0 < len(P) and i1 < len(P) and P[i0] and P[i1]:
                    g.append(P[i1] / P[i0] - 1)
            if not g:
                continue
            cur = set(names)
            tv = 1.0 if prev is None else len(cur - prev) / max(1, len(cur))
            prev = cur
            turn.append(tv)
            r.append(sum(g) / len(g) - tv * COST)
        return r, turn

    def stat(xs, per=12.0):
        if not xs:
            return {}
        g = 1.0
        for x in xs:
            g *= (1 + x)
        yrs = len(xs) / per
        cagr = (g ** (1 / yrs) - 1) * 100
        m = sum(xs) / len(xs)
        vol = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs)) * math.sqrt(per) * 100
        gg, pk, w = 1.0, 1.0, 0.0
        for x in xs:
            gg *= (1 + x)
            pk = max(pk, gg)
            w = min(w, gg / pk - 1)
        return {"cagr": round(cagr, 2), "vol": round(vol, 2),
                "sharpe": round(cagr / vol, 3) if vol else None, "mdd": round(w * 100, 1)}

    # 대조군 — 랩 동일가중 유니버스(실제 매매 대상). 지수 대비만 보면 착시가 난다.
    uni = []
    for k in range(len(me) - 1):
        i0, i1 = me[k], me[k + 1]
        if i0 < LONG + 5:
            continue
        g = [px[t][i1] / px[t][i0] - 1 for t in px
             if px.get(t) and i1 < len(px[t]) and px[t][i0] and px[t][i1]]
        if g:
            uni.append(sum(g) / len(g))
    n0 = min(len(uni), min(len(picks[k]) for k in picks))
    uni = uni[-n0:]

    res, series = {}, {}
    for k in ("S", "I", "R", "X"):
        r, turn = run(picks[k])
        r = r[-n0:]
        series[k] = [round(x, 6) for x in r]
        s = stat(r)
        s["turnover"] = round(sum(turn) / len(turn) * 12, 2)
        d = [a - b for a, b in zip(r, uni)]
        s["vs_uni_excess"] = round(stat(r)["cagr"] - stat(uni)["cagr"], 2)
        s["vs_uni_dsharpe"] = round((stat(r)["sharpe"] or 0) - (stat(uni)["sharpe"] or 0), 3)
        s["n_months"] = len(r)
        res[k] = s

    def corr(a, b):
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = math.sqrt(sum((x - ma) ** 2 for x in a))
        db = math.sqrt(sum((y - mb) ** 2 for y in b))
        return round(num / (da * db), 3) if da and db else None

    ex = {k: [a - b for a, b in zip(series[k], uni)] for k in series}
    cm = {"%s-%s" % (a, b): corr(ex[a], ex[b])
          for a, b in (("S", "I"), ("S", "R"), ("I", "R"))}

    gmin = sum(1 for g in diag["groups"] if g < MIN_GROUPS)
    doc = {
        "note": ("산업 모멘텀과 그 잔차. 규약 build/PREREG-2026-08-28-INDMOM.md. "
                 "S 종목 12-1 · I 산업 12-1 · R 산업잔차 12-1 을 같은 격자·같은 바스켓 "
                 "크기·같은 비용으로 나란히 돌린 값이다."),
        "spec": {"formation": "12-1 (ret252 - ret21)", "level": "GICS 산업그룹",
                 "min_names": MIN_N, "top_groups": TOP_G, "cost_bp_oneway": COST * 1e4,
                 "group_return": "시총가중", "hold": "뽑힌 그룹 전 종목 동일가중 · 월말"},
        "bench": {"label": "랩 동일가중 유니버스 매수후보유", **stat(uni)},
        "legs": res, "excess_corr": cm,
        "skip_effect": {"note": ("X 는 현행 x-indmom 명세 그대로다(섹터 11 · 6개월 무이격 · "
                                 "상위 2 · 동일가중 산업수익). I 와의 차가 «이격 + 계층 + "
                                 "가중 + 상위 N» 을 합친 효과이지 이격만의 효과가 아니다 — "
                                 "그 넷을 분리하려면 등록을 더 쪼개야 한다."),
                        "I_minus_X_sharpe": None},
        "diag": {
            "months": diag["months"],
            "groups_mean": round(sum(diag["groups"]) / len(diag["groups"]), 1),
            "groups_min": min(diag["groups"]), "groups_max": max(diag["groups"]),
            "months_below_%d" % MIN_GROUPS: gmin,
            "months_below_pct": round(gmin / len(diag["groups"]) * 100, 1),
            "thin_dropped_mean": round(sum(diag["thin_dropped"]) / len(diag["thin_dropped"]), 1),
            "thin_names": dict(sorted(diag["thin_names"].items(), key=lambda x: -x[1])[:10]),
            "sector_concentrated_months": diag["sec_conc"],
            "sector_concentrated_pct": round(diag["sec_conc"] / max(1, diag["months"]) * 100, 1),
        },
        "series": {"dates": [dates[i1][:7] for _i0, i1, _n in picks["I"]][-n0:],
                   **series, "uni": [round(x, 6) for x in uni]},
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("\n%-3s %-22s %7s %7s %7s %7s %9s %9s" %
          ("", "", "CAGR", "Vol", "샤프", "MDD", "유니초과", "유니dS"))
    nm = {"S": "종목 12-1", "I": "산업 12-1", "R": "산업잔차 12-1",
          "X": "현행 x-indmom(6M 무이격)"}
    for k in ("S", "I", "R", "X"):
        s = res[k]
        print("%-3s %-22s %7.2f %7.2f %7.3f %7.1f %9.2f %9.3f" %
              (k, nm[k], s["cagr"], s["vol"], s["sharpe"] or 0, s["mdd"],
               s["vs_uni_excess"], s["vs_uni_dsharpe"]))
    b = doc["bench"]
    print("%-3s %-22s %7.2f %7.2f %7.3f %7.1f" % ("", "동일가중 유니버스", b["cagr"], b["vol"], b["sharpe"], b["mdd"]))
    print("\n초과수익 상관:", cm)
    d = doc["diag"]
    print("후보 그룹 평균 %.1f (%d~%d) · %d 미만인 달 %d (%.1f%%) · 얇아서 뺀 그룹 평균 %.1f"
          % (d["groups_mean"], d["groups_min"], d["groups_max"], MIN_GROUPS,
             d["months_below_%d" % MIN_GROUPS], d["months_below_pct"], d["thin_dropped_mean"]))
    print("상위 3이 한 섹터에 겹친 달 %d / %d (%.1f%%)"
          % (d["sector_concentrated_months"], d["months"], d["sector_concentrated_pct"]))
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
