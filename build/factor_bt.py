# -*- coding: utf-8 -*-
"""S&P Global 팩터 Top10 백테스트(factorbt.html) 생성기.

2026-09-22 사용자 «factors.html 에서 S&P Global Factor 점수별로 top10 종목들 고르고 월간 리밸런싱 백테스팅해서
style.html#s=lowvol 이런식으로 구성해. S&P Global 314개 팩터에 대해서 다 해야함 … 종목은 S&P500, 나스닥100 종목
대상으로만 해서 10종목 뽑으면됨».

입력  build/factor_bt_src/ — 🚨 사내 자료 추출물(반입 금지 · .gitignore). 저장소 밖 추출 스크립트가 만든다.
        vals.parquet(ym·g·f·val — 월말 팩터값) · members.parquet(ym·gvkeyiid·ticker·in_spx·in_ndx·sec — 그 달 멤버)
        ret.parquet(ym·gvkeyiid·ret — 달러 가격수익 PR, 그 달에 실현) · map.json(월말 날짜·필드·사전 행 → 필드)
      build/factors_src.json — 사전 원표(이름·소분류·설명·순위 방향). 🚨 반입 금지.
      data/bench_px.json(S&P 500·NASDAQ 100 가격지수 일간) · data/rf_monthly.json(FRED 3개월물 월복리)
      data/stocks.json(종목명·섹터) · data/sd/<T>.json · data/pit_px.json(일간 종가 — 이번 달 수익 MTD)
출력  data/factor_bt.json

규칙  매월 말, 그 달 S&P 500 ∪ NASDAQ 100 멤버(시점정합 — 그 뒤 편출된 종목 포함) 중 팩터값이 있는 종목을 사전의
      «순위 방향»으로 줄 세워 상위 10종목(내림차순 = 값이 큰 것부터, 오름차순 = 작은 것부터). 동점은 gvkeyiid 순.
      동일가중으로 다음 달 한 달 보유 · 월말 리밸런스 · 비용 0.
      수익은 **가격수익(PR)** — 대조군 S&P 500(PR)·NASDAQ 100(PR)과 같은 기준이다(배당을 넣은 쪽만 유리해지지 않게).
      보유 종목의 다음 달 수익이 팩터 자료에 없으면(유니버스 이탈) 랩 일간 종가(sd·pit_px — 배당조정)로 그달 수익을
      메우고, 그래도 없으면 보정표(build/factor_bt_src/ret_fill.json — 시세 공급사·yfinance 월말 종가 · 합병·재분류 승계 · 사건 보정)를 쓰고,
      그래도 없으면 0 으로 둔다(대부분 인수로 상장폐지된 달) — 세 건수를 산출물 fill 에 적는다.
      0 으로 남은 (티커, 월) 목록은 build/factor_bt_src/missing.json 에 떨군다(보정 스크립트의 입력).
      후보가 10 미만인 달은 있는 만큼, 0 이면 그달 0%(현금).
      사전 안의 중복 행(같은 필드를 가리키는 두 줄)은 결과가 같다 — same_as 로 표시한다.
지표  샤프 = 월 초과수익(무위험 차감) 평균 ÷ 표준편차 × √12 · 변동성 = 월 표준편차 × √12 · MDD = 월말 기준
      이긴 달 = 그달 전략 수익 > 지수 수익 인 달 수 / 전체 달 수.
실행  python build/factor_bt.py
      ⚠ 로컬 전용 — 입력이 반입 금지라 CI 러너에는 없다. 팩터 월말 자료가 들어오는 월초에 손으로 굽는다
        (audit_unbuilt KNOWN 에 사유를 적어 두었다).
"""
import io, json, math, os, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "build", "factor_bt_src")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "factor_bt.json")
TOPN = 10
SEC_KO = {"Information Technology": "IT", "Financials": "금융", "Industrials": "산업재", "Health Care": "헬스케어",
          "Consumer Discretionary": "경기소비재", "Consumer Staples": "필수소비재", "Communication Services": "커뮤니케이션",
          "Energy": "에너지", "Utilities": "유틸리티", "Materials": "소재", "Real Estate": "부동산"}
GROUP_KO = {"Earnings Quality": "이익의 질", "Historical Growth": "과거 성장", "Price Momentum": "가격 모멘텀",
            "Valuation": "밸류에이션", "Capital Efficiency": "자본 효율", "Analyst Expectations": "애널리스트 전망",
            "Volatility": "변동성", "Size": "사이즈"}


def rd(p):
    return json.load(io.open(p, encoding="utf-8"))


def r1(v, d=1):
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else round(float(v), d)


def fmt_val(v):
    """팩터값 표시 — 크기가 제각각이라 유효숫자 4자리.
    아주 작은 값(Amihud 비유동성 ~1e-12 등)은 고정 소수점이면 전부 0.0000 이 돼 순위가 안 보인다 → 지수 표기."""
    if v is None or not math.isfinite(v):
        return "—"
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 1e6 or a < 1e-3:
        return "%.3g" % v
    if a >= 100:
        return "%.1f" % v
    if a >= 1:
        return "%.3f" % v
    return "%.4f" % v


def month_end_px(dates, px):
    """일간 → 월말 종가(그 달 마지막 거래일). {YYYY-MM: px}"""
    out = {}
    for d, p in zip(dates, px):
        if p is not None:
            out[d[:7]] = p
    return out


def perf(r, rf, bench=None):
    """r: 월수익(np.array) · rf: 같은 길이 무위험 · 반환 지표(%)"""
    n = len(r)
    if n == 0:
        return {}
    nav = np.cumprod(1 + r)
    cagr = nav[-1] ** (12 / n) - 1
    ex = r - rf
    sd = r.std(ddof=1) if n > 1 else float("nan")
    sde = ex.std(ddof=1) if n > 1 else float("nan")
    peak = np.maximum.accumulate(np.concatenate([[1.0], nav]))
    mdd = (np.concatenate([[1.0], nav]) / peak - 1).min()
    return {"cagr": r1(cagr * 100, 2), "cum": r1((nav[-1] - 1) * 100, 1), "vol": r1(sd * math.sqrt(12) * 100, 2),
            "sharpe": r1(ex.mean() / sde * math.sqrt(12), 2) if sde > 0 else None, "mdd": r1(mdd * 100, 2)}


def trails(r, months):
    """기간별 수익률(%) — 1년까지는 누적, 3·5·10년은 연율."""
    n = len(r)
    def cum(k):
        return None if n < k else r1((np.prod(1 + r[-k:]) - 1) * 100, 1)
    def ann(k):
        return None if n < k else r1((np.prod(1 + r[-k:]) ** (12 / k) - 1) * 100, 1)
    ytd_k = sum(1 for m in months if m[:4] == months[-1][:4])
    return {"1개월": cum(1), "3개월": cum(3), "6개월": cum(6), "YTD": cum(ytd_k), "1년": cum(12),
            "3년(연)": ann(36), "5년(연)": ann(60), "10년(연)": ann(120)}


def yearly(r, months):
    out = {}
    for y in sorted({m[:4] for m in months}):
        idx = [i for i, m in enumerate(months) if m[:4] == y]
        out[y] = r1((np.prod(1 + r[idx]) - 1) * 100, 1)
    return out


def main() -> int:
    t0 = time.time()
    for f in ("vals.parquet", "members.parquet", "ret.parquet", "map.json"):
        if not os.path.exists(os.path.join(SRC, f)):
            print("❌ 입력 없음: build/factor_bt_src/%s — 저장소 밖 추출 스크립트를 먼저 돌릴 것" % f)
            return 1
    MAP = rd(os.path.join(SRC, "map.json"))
    V = pd.read_parquet(os.path.join(SRC, "vals.parquet"))
    MEM = pd.read_parquet(os.path.join(SRC, "members.parquet"))
    RET = pd.read_parquet(os.path.join(SRC, "ret.parquet"))
    DICT = rd(os.path.join(ROOT, "build", "factors_src.json"))["rows"]
    GV = MAP["gv"]
    dates = MAP["dates"]                                    # 월말 135개
    yms = [int(d[:4]) * 100 + int(d[5:7]) for d in dates]
    ymstr = [d[:7] for d in dates]
    print("입력: 월말 %d개(%s~%s) · 값 %s행 · 필드 %d · 종목 %d" % (len(dates), dates[0], dates[-1], format(len(V), ","), len(MAP["flds"]), len(GV)))

    # ── 멤버·수익을 배열로 ────────────────────────────────────────────────
    gidx = {g: i for i, g in enumerate(GV)}
    MEM = MEM.drop_duplicates(["ym", "gvkeyiid"])
    MEM["g"] = MEM["gvkeyiid"].map(gidx)
    memb = {ym: grp for ym, grp in MEM.groupby("ym")}       # ym 'YYYY-MM'
    RET["g"] = RET["gvkeyiid"].map(gidx)
    R = {}                                                   # (ym_int) → {g: ret}
    for ym, grp in RET.dropna(subset=["g", "ret"]).groupby("ym"):
        R[int(ym)] = dict(zip(grp["g"].astype(int), grp["ret"].astype(float)))
    # 지수·무위험
    B = rd(os.path.join(DATA, "bench_px.json"))
    bme = {k: month_end_px(B["dates"], B["series"][k]["px"]) for k in ("spx", "ndx")}
    RF = rd(os.path.join(DATA, "rf_monthly.json"))["monthly"]
    hold_months = ymstr[1:]                                   # 수익월 2015-07 ~ 2026-08
    def bret(k, m):
        prev = (pd.Period(m, "M") - 1).strftime("%Y-%m")
        return bme[k][m] / bme[k][prev] - 1
    BR = {k: np.array([bret(k, m) for m in hold_months]) for k in ("spx", "ndx")}
    RFA = np.array([float(RF.get(m, 0.0)) for m in hold_months])

    # 이번 달(보유 중) MTD — 랩 일간 종가
    ST = rd(os.path.join(DATA, "stocks.json"))
    pxd = ST["pxd_dates"]; px_asof = pxd[-1]
    last_me = dates[-1]
    i_me = max(i for i, d in enumerate(pxd) if d <= last_me)
    NAME = {s["t"]: s for s in ST["stocks"]}
    PIT = rd(os.path.join(DATA, "pit_px.json"))
    def mtd(t):
        p = os.path.join(DATA, "sd", "%s.json" % t)
        v = None
        if os.path.exists(p):
            try:
                v = rd(p).get("pxd")
            except Exception:
                v = None
        if v and len(v) == len(pxd) and v[i_me] and v[-1]:
            return (v[-1] / v[i_me] - 1) * 100
        q = (PIT.get("px") or {}).get(t)
        if isinstance(q, dict) and q.get("p"):
            i0 = q.get("i0", 0); arr = q["p"]
            a, b = i_me - i0, len(arr) - 1
            if 0 <= a < len(arr) and arr[a] and arr[b] and i0 + b == len(pxd) - 1:
                return (arr[b] / arr[a] - 1) * 100
        return None
    bmtd = {k: (B["series"][k]["px"][-1] / bme[k][last_me[:7]] - 1) * 100 for k in ("spx", "ndx")}
    # 월말 인덱스(그 달 마지막 거래일) — 빠진 월수익을 랩 일간 종가로 메울 때 쓴다
    me_idx = {}
    for i, d in enumerate(pxd):
        me_idx[d[:7]] = i
    _lab = {}
    def labpx(t):
        """(i0, 배열) — sd/<T>.json(현재 종목, i0=0) → pit_px.json(편출 종목). 없으면 None."""
        if t in _lab:
            return _lab[t]
        out = None
        p = os.path.join(DATA, "sd", "%s.json" % t)
        if os.path.exists(p):
            try:
                v = rd(p).get("pxd")
                if v and len(v) == len(pxd):
                    out = (0, v)
            except Exception:
                out = None
        if out is None:
            q = (PIT.get("px") or {}).get(t)
            if isinstance(q, dict) and q.get("p"):
                out = (int(q.get("i0", 0)), q["p"])
        _lab[t] = out
        return out
    def lab_mret(t, ym):
        """ym(YYYY-MM) 한 달 수익 — 전월말 → 그달 말 종가. 랩 종가는 배당조정(총수익)이라 PR 과 배당만큼 다르다."""
        lp = labpx(t) if t else None
        pv = (pd.Period(ym, "M") - 1).strftime("%Y-%m")
        if not lp or pv not in me_idx or ym not in me_idx:
            return None
        i0, arr = lp; a, b = me_idx[pv] - i0, me_idx[ym] - i0
        if 0 <= a < len(arr) and 0 <= b < len(arr) and arr[a] and arr[b]:
            return arr[b] / arr[a] - 1
        return None
    tick_of = {ys: dict(zip(grp["g"].astype(int), grp["ticker"])) for ys, grp in memb.items()}
    # 빠진 월수익 보정표(반입 금지 폴더) — 저장소 밖 보정 스크립트가 만든다: {"TICKER|YYYY-MM": {"r": 수익, "src": 출처}}
    #   시세 공급사·yfinance 월말 종가(가격수익) · 합병·재분류 승계(교환비율·특별 현금) · 사건 보정(예: 2023-03 은행 폐쇄 −100%).
    #   🚨 보정 스크립트는 기존 표에 병합한다 — missing.json 은 «아직 0 인 자리»만 담기 때문(덮어쓰면 지난 보정이 사라진다).
    FIXP = os.path.join(SRC, "ret_fill.json")
    FIX = rd(FIXP) if os.path.exists(FIXP) else {}

    # ── 값 → (fcode, ym) 별 배열 ──────────────────────────────────────────
    V = V.sort_values(["f", "ym"])
    byf = {f: grp for f, grp in V.groupby("f")}
    fl_norm = {re.sub(r"\s+", " ", f).strip().lower(): i for i, f in enumerate(MAP["flds"])}

    factors, n_fill, n_lab, n_fix, n_slots, done_fld = [], 0, 0, 0, 0, {}
    MISS = {}                                                # (티커, 수익월) → 0 으로 둔 횟수(진단용)
    for fm in MAP["factors"]:
        row = DICT[fm["id"] - 1]
        assert row["factor"] == fm["name"], (row["factor"], fm["name"])
        rec = {"id": fm["id"], "name": row["factor"], "sub": row["subgroup"], "desc": row["description"],
               "dir": "desc" if row["rank_order"] == "내림차순" else "asc"}
        if not fm.get("fld"):
            rec["na"] = "자료 없음 — 이 팩터는 팩터 자료에 값이 없다"
            factors.append(rec); continue
        fc = fl_norm[re.sub(r"\s+", " ", fm["fld"]).strip().lower()]
        key = (fc, rec["dir"])
        if key in done_fld:                                   # 사전 중복 행 — 같은 결과
            base = dict(done_fld[key])
            base.update({"id": rec["id"], "name": rec["name"], "sub": rec["sub"], "desc": rec["desc"], "same_as": done_fld[key]["id"]})
            factors.append(base); continue
        G = byf.get(fc)
        GM = {int(y): sub for y, sub in G.groupby("ym")} if G is not None else {}   # 월별로 한 번만 나눈다
        rets, picks, cands = [], [], []
        vals_last = {}
        for k, (ym, ys) in enumerate(zip(yms, ymstr)):
            m = memb.get(ys)
            gv = GM.get(ym)
            if m is None or gv is None or gv.empty:
                pick = []; cands.append(0)
            else:
                elig = set(m["g"].dropna().astype(int))
                x = gv[gv["g"].isin(elig)][["g", "val"]]
                x = x[np.isfinite(x["val"])]
                cands.append(len(x))
                x = x.sort_values(["val", "g"], ascending=[rec["dir"] == "asc", True])
                pick = x.head(TOPN)
                vals_last[ys] = dict(zip(pick["g"].astype(int), pick["val"].astype(float)))
                pick = pick["g"].astype(int).tolist()
            picks.append(pick)
            if k + 1 < len(yms):                              # 다음 달 수익
                nx = yms[k + 1]
                rr = []
                for g in pick:
                    v = R.get(nx, {}).get(g)
                    if v is None or not math.isfinite(v):
                        v = lab_mret(tick_of[ys].get(g), ymstr[k + 1])
                        fx = FIX.get("%s|%s" % (tick_of[ys].get(g), ymstr[k + 1]))
                        if v is None and fx is not None and fx.get("r") is not None:
                            v = float(fx["r"]); n_fix += 1
                        elif v is not None:
                            n_lab += 1
                        else:
                            n_fill += 1
                            MISS[(tick_of[ys].get(g), ymstr[k + 1])] = MISS.get((tick_of[ys].get(g), ymstr[k + 1]), 0) + 1
                    rr.append(v)
                n_slots += len(rr)
                rets.append(float(np.mean([0.0 if (v is None or not math.isfinite(v)) else v for v in rr])) if rr else 0.0)
        r = np.array(rets)
        nav = np.concatenate([[100.0], 100 * np.cumprod(1 + r)])
        turn = [len(set(picks[k]) - set(picks[k - 1])) / max(len(picks[k]), 1) for k in range(1, len(picks)) if picks[k]]
        def rows_of(k, other, isin, mret):
            ys = ymstr[k]; m = memb[ys].set_index("g"); out = []
            for i, g in enumerate(picks[k], 1):
                t = m.at[g, "ticker"] if g in m.index else None
                s = NAME.get(t or "", {})
                sec = s.get("sector") or (m.at[g, "sec"] if g in m.index else None)
                idx = "·".join(n for n, f in (("S&P", "in_spx"), ("NDX", "in_ndx")) if g in m.index and bool(m.at[g, f]))
                out.append({"r": i, "t": t or GV[g], "n": (s.get("name") or "")[:28], "s": SEC_KO.get(sec, sec or "—"), "idx": idx,
                            "new": g not in other, "ret": r1(mret(g, t), 1), "v": fmt_val(vals_last.get(ys, {}).get(g))})
            return out
        K = len(picks) - 1
        prev_ret = lambda g, t: (R.get(yms[K], {}).get(g) * 100) if R.get(yms[K], {}).get(g) is not None else None
        cur_ret = lambda g, t: mtd(t) if t else None
        rec.update({
            "metrics": perf(r, RFA), "win": {k: [int((r > BR[k]).sum()), len(r)] for k in ("spx", "ndx")},
            "trails": trails(r, hold_months), "yearly": yearly(r, hold_months), "monthly": [r1(v * 100, 1) for v in r[-12:]],
            "nav": [r1(v, 1) for v in nav], "turn": r1(float(np.mean(turn)) * 100, 0) if turn else None,
            "cov": {"med": int(np.median(cands)), "last": cands[-1], "thin": int(sum(c < TOPN for c in cands))},
            "prev": {"d": dates[K - 1], "hold": ymstr[K], "rows": rows_of(K - 1, set(picks[K]), False, prev_ret)},
            "today": {"d": dates[K], "hold": "%s 보유 중" % px_asof[:7], "rows": rows_of(K, set(picks[K - 1]), True, cur_ret)},
        })
        done_fld[key] = rec
        factors.append(rec)
        if len(factors) % 40 == 0:
            print("  %d/%d · %.0fs" % (len(factors), len(MAP["factors"]), time.time() - t0), flush=True)

    # ── 대조군 ────────────────────────────────────────────────────────────
    bench = {}
    for k, lab in (("spx", "S&P 500(PR)"), ("ndx", "NASDAQ 100(PR)")):
        r = BR[k]
        bench[k] = {"label": lab, "metrics": perf(r, RFA), "trails": trails(r, hold_months), "yearly": yearly(r, hold_months),
                    "monthly": [r1(v * 100, 1) for v in r[-12:]], "nav": [r1(v, 1) for v in np.concatenate([[100.0], 100 * np.cumprod(1 + r)])],
                    "mtd": r1(bmtd[k], 1)}
    groups = []
    for g in dict.fromkeys(f["sub"] for f in factors):
        groups.append({"key": g, "ko": GROUP_KO.get(g, g), "n": sum(1 for f in factors if f["sub"] == g)})
    out = {
        "generated": time.strftime("%Y-%m-%d"),
        "as_of": dates[-1], "px_as_of": px_asof, "start": dates[0], "end_ret": hold_months[-1],
        "n_months": len(hold_months), "nav_months": ymstr, "months": hold_months[-12:], "years": sorted({m[:4] for m in hold_months}),
        "rule": "매월 말 그 달 S&P 500 ∪ NASDAQ 100 멤버(시점정합) 중 팩터값이 있는 종목을 사전의 순위 방향으로 줄 세워 상위 10종목 · "
                "동일가중 · 다음 달 한 달 보유(월말 리밸런스) · 비용 0",
        "basis": "가격수익(PR) — 대조군 S&P 500(PR)·NASDAQ 100(PR)과 같은 기준. 샤프는 무위험(FRED 3개월물)을 뺀 월 초과수익으로 잰다.",
        "fill": {"n": n_fill, "lab": n_lab, "fix": n_fix, "slots": n_slots,
                 "top": [[k[0], k[1], v] for k, v in sorted(MISS.items(), key=lambda kv: (-kv[1], kv[0]))[:8]],
                 "note": "보유 종목의 다음 달 수익이 팩터 자료에 없던 자리(전 팩터 합) — lab 은 랩 일간 종가(배당조정)로 메운 수, "
                         "fix 는 보정표(시세 공급사·yfinance 월말 종가 · 합병·재분류 승계 · 사건 보정)로 메운 수, "
                         "n 은 그래도 없어 0 으로 둔 수(대부분 인수로 상장폐지된 달 · 일부는 시세를 못 구한 편출 종목) · top 은 0 으로 둔 자리가 많은 (티커, 수익월, 횟수)"},
        "groups": groups, "bench": bench, "factors": factors,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    ok = [f for f in factors if "metrics" in f]
    json.dump(sorted("%s|%s" % k for k in MISS), io.open(os.path.join(SRC, "missing.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if MISS:
        top = sorted(MISS.items(), key=lambda kv: -kv[1])[:12]
        print("  0 으로 둔 자리 상위(티커·수익월·횟수): " + " · ".join("%s %s %d" % (k[0], k[1], v) for k, v in top)
              + " — 고유 %d건" % len(MISS))
    print("팩터 %d개(결과 %d · 자료 없음 %d · 중복 행 %d) · 빠진 월수익 — 랩 종가 %d · 보정표 %d · 0 으로 둠 %d / 전체 %d(%.2f%%) · %s %.0fKB · %.0fs"
          % (len(factors), len(ok), sum("na" in f for f in factors), sum("same_as" in f for f in factors),
             n_lab, n_fix, n_fill, n_slots, 100 * n_fill / max(n_slots, 1), os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
