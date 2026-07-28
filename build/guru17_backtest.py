# -*- coding: utf-8 -*-
"""build/guru17_backtest.py — 운용사별 13F 복제 17종을 **진단물**로 굽는다 → data/guru17.json

## 이것은 전략이 아니라 진단물이다

묻는 것은 하나다 — **"유명 헤지펀드를 따라 사면 되는가."** 답은 아래 세 줄로 낸다.
개별 운용사 순위표는 그 아래 부록으로만 둔다. 순서를 뒤집으면 "누가 이겼나" 하이라이트가
되고, 그 순간 이 표는 사후선택된 명단에서 최고를 골라 자랑하는 물건이 된다.

## 왜 알파 발굴로 쓰면 안 되는가 — 사전에 못 박는다

**① 운용사 명단이 100% 사후 선택이다.** build/refresh_13f.py 의 GURUS 는 규칙이 아니라
   손으로 쓴 CIK 표이고, 그 기준은 '2026년 시점의 유명세'다. 실제로 18곳 중 17곳이 지금도
   영업 중이고 13년 구간에서 폐업·청산한 곳은 0곳이다. 어떤 대조군·어떤 다중검정 보정도
   "2026년에 누구를 복제할지 골랐다"는 사실을 상쇄하지 못한다.
   → '17종 = 전수'라고 쓰지 않는다. 13F 제출인 수천 곳 중 손으로 고른 18곳의 전수일 뿐이다.

**② 유니버스도 오늘 스냅샷이다.** 518종목은 현재 구성이고 CUSIP→티커 매핑도 현재 기준이라,
   과거 보유 중 '지금 대형주로 살아남은 것'만 남는다. 방향이 명확히 상방이며 크기는 이
   저장소 안에서 정량화할 수 없다(유니버스 밖 보유액이라는 분모가 파일에 없다).
   → 대조군을 같은 풀 동일가중으로 두어 유니버스 편향을 양쪽에서 상쇄한다. 상쇄되지 않는
     부분(티커 변경·상장폐지로 사라진 보유)은 측정 불가라고 명시한다.

**③ 표본에 판정 능력이 없다.** 추적오차 중앙 12.7%·13년이면 알파 표준오차가 3.55%p다.
   Bonferroni(m=17) 문턱을 80% 검정력으로 넘으려면 연 13.5%p 알파가 필요한데, 13F 복제의
   현실적 알파(연 1~3%)에서 검출확률은 1~2%다. **유의 0건은 예상된 결과이며 알파 부재의
   증거가 아니다.** 이 문장을 결과 보기 전에 적어 둔다 — 사후에 쓰면 변명이 된다.

## 사전 등록 사양 (결과를 보기 전에 고정한다)

  리밸런스   분기말 + 2개월의 월말. 13F 제출 마감이 분기말+45일이므로 최소 14일 여유다.
             (3/31→5/31 · 6/30→8/31 · 9/30→11/30 · 12/31→2/28)
             ⚠ 공시일(filed)이 리밸런스일보다 뒤면 그 셀은 버린다 — 룩어헤드 직접 차단.
  비중       주식수 고정 환산(share-drift). 분기말 가치 v 를 체결월 가격으로 환산한다:
             v × P[체결월] / P[분기말]. 분기말 가치를 그대로 쓰면 그 사이 오른 종목을 팔고
             내린 종목을 사는 2개월짜리 역발상 매매를 공짜로 주입하게 된다(실측 평균 +0.44%p).
  보유       리밸런스 사이에는 표류시킨다(매수후보유). 고정비중 재조정은 하지 않는다.
  대조군     같은 풀 동일가중(월 리밸). 유니버스 편향을 양쪽에 똑같이 태우기 위해서다.
             베타 차이는 CAPM 알파로 처리한다 — 베타 1.17 포트폴리오를 베타 1 벤치와
             수익률로 겨뤄 '이겼다'고 하는 것이 이 랩이 가장 경계하는 오독이다.
  무위험     rf_monthly.json(FRED DGS3MO) 월율. 초과수익 기준으로 잰다.
  부분월     진행 중인 달은 버린다.

## 게이트 (사전 고정)

  · 체결월 가격이 없는 보유는 버리고 남은 것으로 재정규화한다. 버린 비중이 20%를 넘으면
    그 (운용사,분기)는 산출하지 않는다.
  · 유니버스내 보유가 3종목 이하인 분기도 산출하지 않는다.
  · 결측 분기는 직전 분기를 이월한다(미제출은 청산이 아니다). 단 연속 4분기(1년)를 넘으면
    그 구간은 전략 정지 — 2년 묵은 포트폴리오는 더 이상 그 운용사를 대표하지 않는다.
  · top1 비중 > 50% 이거나 유효종목수(1/HHI) < 3 인 분기가 전체의 20%를 넘는 운용사는
    **복제 불가**로 선언하고 성과를 내지 않는다. 유니버스로 잘라낸 뒤 재정규화하면
    원래 포트폴리오와 다른 것이 되기 때문이다(실측 오크트리: 단일종목>50% 인 달 75%).
  · 최신 분기 겹침이 낮은 곳은 '복제'라 부르지 않고 '대형주 익스포저 복제'로 표기한다.

  python build/guru17_backtest.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru17.json")

LAG_MONTHS = 2          # 분기말 → 체결월(그 달 말일)
DROP_W_MAX = 0.20       # 체결월 가격 결측으로 버린 비중이 이보다 크면 그 분기 산출 안 함
MIN_HOLD = 4            # 유니버스내 보유가 이 미만이면 그 분기 산출 안 함
CARRY_MAX = 4           # 연속 결측 이월 상한(분기). 넘으면 전략 정지
CONC_TOP1 = 0.50        # 집중도 게이트 — top1 비중
CONC_EFFN = 3.0         # 집중도 게이트 — 유효종목수(1/HHI)
CONC_FRAC = 0.20        # 위 둘 중 하나에 걸린 분기 비율이 이보다 크면 복제 불가
MIN_MONTHS = 60         # 성과를 낼 최소 개월(5년). 미만이면 표에 싣되 판정하지 않는다


def load(fn):
    return json.load(io.open(os.path.join(DATA, fn), encoding="utf-8"))


def add_months(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m += k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def month_end(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return (dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)).isoformat()


def ann_from_monthly(rets, rf):
    """월 초과수익 배열 → (CAGR, 변동성, 샤프, MDD). 전부 연율."""
    r = np.asarray(rets, float)
    if r.size == 0:
        return None
    nav = np.cumprod(1.0 + r)
    yrs = r.size / 12.0
    cagr = (nav[-1] ** (1.0 / yrs) - 1.0) * 100 if nav[-1] > 0 else None
    vol = float(np.std(r, ddof=1)) * np.sqrt(12) * 100 if r.size > 1 else None
    ex = r - np.asarray(rf, float)
    sh = (float(np.mean(ex)) / float(np.std(ex, ddof=1)) * np.sqrt(12)) if r.size > 1 and np.std(ex, ddof=1) > 0 else None
    peak = np.maximum.accumulate(nav)
    mdd = float(np.min(nav / peak - 1.0)) * 100
    return {"cagr": None if cagr is None else round(cagr, 2),
            "vol": None if vol is None else round(vol, 2),
            "sharpe": None if sh is None else round(sh, 3),
            "mdd": round(mdd, 2)}


def capm(r, b, rf):
    """초과수익 회귀 r-rf = a + β(b-rf). 반환 (연 알파%, 베타, t(알파), 잔차)."""
    y = np.asarray(r, float) - np.asarray(rf, float)
    x = np.asarray(b, float) - np.asarray(rf, float)
    n = y.size
    if n < 24:
        return None, None, None, None
    X = np.column_stack([np.ones(n), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    s2 = float(resid @ resid) / (n - 2)
    xtx_inv = np.linalg.inv(X.T @ X)
    se_a = float(np.sqrt(s2 * xtx_inv[0, 0]))
    a_m = float(coef[0])
    t = a_m / se_a if se_a > 0 else None
    return (round(((1 + a_m) ** 12 - 1) * 100, 2), round(float(coef[1]), 3),
            None if t is None else round(t, 2), resid)


def grs(resid_mat, alphas_m, bench_ex):
    """Gibbons-Ross-Shanken — '알파가 전부 0'을 한 번에 검정한다.

    상관된 N개의 알파를 개별로 N번 검정하면 무엇을 보정해도 답이 흐려진다. GRS는 그 N개를
    한 통계량으로 묶어 질문에 직접 답한다. 저장소에 구현이 없어 여기서 만든다.
    """
    from scipy import stats
    A = np.asarray(alphas_m, float)                 # 월 알파
    E = np.asarray(resid_mat, float)                # (N, T) 잔차
    N, T = E.shape
    if T <= N + 1:
        return None
    Sigma = (E @ E.T) / (T - 2)
    try:
        Si = np.linalg.inv(Sigma)
    except np.linalg.LinAlgError:
        return None
    mu = float(np.mean(bench_ex))
    sd = float(np.std(bench_ex, ddof=1))
    sr2 = (mu / sd) ** 2 if sd > 0 else 0.0
    f = ((T - N - 1) / N) * (A @ Si @ A) / (1 + sr2)
    p = 1 - stats.f.cdf(f, N, T - N - 1)
    return {"F": round(float(f), 3), "df1": int(N), "df2": int(T - N - 1),
            "p": round(float(p), 4)}


def holm_bh(pvals):
    """Holm(FWER)·BH(FDR) 통과 개수. 어느 쪽을 쓰든 답이 같다는 것을 보이기 위해 둘 다 낸다."""
    p = sorted((v, i) for i, v in enumerate(pvals) if v is not None)
    m = len(p)
    if not m:
        return {"m": 0, "bonferroni": 0, "holm": 0, "bh10": 0}
    bonf = sum(1 for v, _ in p if v < 0.05 / m)
    holm = 0
    for k, (v, _) in enumerate(p):
        if v < 0.05 / (m - k):
            holm += 1
        else:
            break
    bh = 0
    for k in range(m - 1, -1, -1):
        if p[k][0] <= 0.10 * (k + 1) / m:
            bh = k + 1
            break
    return {"m": m, "bonferroni": bonf, "holm": holm, "bh10": bh}


def build_manager(cik, G, mi, P, months):
    """한 운용사의 월별 비중 시계열을 만든다. 반환 (weights_by_month, 진단 dict)."""
    H, FILED = G["holdings"], G.get("filed") or {}
    qs = sorted(q for q in H if cik in H[q])
    diag = {"n_quarters": len(qs), "skipped": [], "carried": 0, "paused": [],
            "lookahead": [], "conc_bad": 0, "conc_total": 0}
    if not qs:
        return {}, diag

    # 분기 → 체결월. 같은 체결월에 둘이 겹치면 나중 분기가 이긴다.
    plan = {}
    for q in qs:
        qm = q[:7]
        rm = add_months(qm, LAG_MONTHS)
        if rm not in mi or qm not in mi:
            continue
        # ── 룩어헤드 직접 차단 ── 공시일이 체결일보다 뒤면 그때는 알 수 없던 정보다.
        fd = (FILED.get(q) or {}).get(cik)
        if fd and fd > month_end(rm):
            diag["lookahead"].append({"q": q, "filed": fd, "rebal": month_end(rm)})
            continue
        raw = H[q][cik]
        i_q, i_r = mi[qm], mi[rm]
        # 주식수 고정 환산 — 분기말 가치를 체결월 가격으로 옮긴다
        w, dropped = {}, 0.0
        tot = sum(v for v in raw.values() if v and v > 0) or 1.0
        for t, v in raw.items():
            if not v or v <= 0:
                continue
            pq, pr = P.get(t, [None] * len(months))[i_q], P.get(t, [None] * len(months))[i_r]
            if pq is None or pr is None or pq <= 0:
                dropped += v / tot
                continue
            w[t] = (v / tot) * (pr / pq)
        # 집중도 진단은 게이트 통과 여부와 무관하게 전 분기에 대해 센다
        if w:
            s = sum(w.values())
            ww = np.array([x / s for x in w.values()])
            diag["conc_total"] += 1
            if float(ww.max()) > CONC_TOP1 or (1.0 / float((ww ** 2).sum())) < CONC_EFFN:
                diag["conc_bad"] += 1
        if dropped > DROP_W_MAX:
            diag["skipped"].append({"q": q, "why": "체결월 가격 결측 %.0f%%" % (dropped * 100)})
            continue
        if len(w) < MIN_HOLD:
            diag["skipped"].append({"q": q, "why": "유니버스내 %d종목" % len(w)})
            continue
        s = sum(w.values())
        plan[rm] = {t: x / s for t, x in w.items()}

    if not plan:
        return {}, diag

    # 체결월부터 월별로 전개 — 리밸런스 사이에는 표류(매수후보유)시킨다.
    W, cur, since = {}, None, 0
    start = mi[min(plan)]
    for i in range(start, len(months)):
        m = months[i]
        if m in plan:
            cur, since = dict(plan[m]), 0
        elif cur is not None:
            # 분기(3개월)마다 새 정보가 와야 한다. 안 오면 이월하되 상한을 둔다.
            if i > start and (i - start) % 3 == 0:
                since += 1
                diag["carried"] += 1
                if since > CARRY_MAX:
                    diag["paused"].append(m)
                    cur = None
                    continue
            # 표류: 직전 달 수익률만큼 비중이 자란다
            nxt, tot = {}, 0.0
            for t, x in cur.items():
                p0, p1 = P.get(t, [None] * len(months))[i - 1], P.get(t, [None] * len(months))[i]
                if p0 is None or p1 is None or p0 <= 0:
                    continue
                v = x * (p1 / p0)
                nxt[t] = v
                tot += v
            cur = {t: v / tot for t, v in nxt.items()} if tot > 0 else cur
        if cur:
            W[m] = dict(cur)
    return W, diag


def monthly_returns(W, P, mi, months):
    """비중 시계열 → 월 수익률. 비중은 그 달 **말**에 정해지고 다음 달 수익을 받는다."""
    out = {}
    for m, w in W.items():
        i = mi[m]
        if i + 1 >= len(months):
            continue
        nm = months[i + 1]
        num, den = 0.0, 0.0
        for t, x in w.items():
            p0, p1 = P.get(t, [None] * len(months))[i], P.get(t, [None] * len(months))[i + 1]
            if p0 is None or p1 is None or p0 <= 0:
                continue
            num += x * (p1 / p0 - 1.0)
            den += x
        if den > 0.5:                      # 절반 이상 값이 살아 있어야 그 달을 인정한다
            out[nm] = num / den
    return out


def compute():
    G = load("guru_history.json")
    RF = (load("rf_monthly.json") or {}).get("monthly") or {}
    months, P = G["months"], G["mpx"]
    # 부분월 제거 — 진행 중인 달은 버린다(값이 있어도 그 달은 아직 끝나지 않았다).
    now_m = dt.date.today().strftime("%Y-%m")
    while months and months[-1] >= now_m:
        months = months[:-1]
    P = {t: v[:len(months)] for t, v in P.items()}
    mi = {m: i for i, m in enumerate(months)}
    print("구간 %s ~ %s (%d개월) · 가격 %d종목" % (months[0], months[-1], len(months), len(P)))

    # ── 대조군: 같은 풀 동일가중(월 리밸) ──────────────────────────────────
    bench = {}
    for i in range(1, len(months)):
        rs = [P[t][i] / P[t][i - 1] - 1.0 for t in P
              if P[t][i] is not None and P[t][i - 1] not in (None, 0)]
        if rs:
            bench[months[i]] = float(np.mean(rs))

    cov = G["coverage"]
    rows, series = [], {}
    for cik, c in cov.items():
        if not c.get("n_q"):
            continue
        W, diag = build_manager(cik, G, mi, P, months)
        rets = monthly_returns(W, P, mi, months)
        conc_frac = (diag["conc_bad"] / diag["conc_total"]) if diag["conc_total"] else 0.0
        row = {"cik": cik, "name": c["name"], "n_quarters": diag["n_quarters"],
               "n_months": len(rets),
               "conc_frac": round(conc_frac, 3), "carried": diag["carried"],
               "skipped": len(diag["skipped"]), "lookahead": len(diag["lookahead"]),
               "paused_months": len(diag["paused"])}
        if conc_frac > CONC_FRAC:
            row["verdict"] = "복제 불가"
            row["why"] = ("유니버스로 잘라내면 남는 것이 너무 집중된다 — top1>50%% 또는 "
                          "유효종목수<3 인 분기가 %.0f%%다. 이건 그 운용사가 아니라 "
                          "그 운용사에서 잘라낸 몇 종목이다." % (conc_frac * 100))
            rows.append(row)
            continue
        if len(rets) < MIN_MONTHS:
            row["verdict"] = "표본 부족"
            row["why"] = "%d개월 — 판정에 필요한 %d개월에 못 미친다." % (len(rets), MIN_MONTHS)
            rows.append(row)
            continue
        ms = sorted(rets)
        r = np.array([rets[m] for m in ms])
        b = np.array([bench.get(m, 0.0) for m in ms])
        rf = np.array([RF.get(m, 0.0) for m in ms])
        row["start"], row["end"] = ms[0], ms[-1]
        row["metrics"] = ann_from_monthly(r, rf)
        row["bench"] = ann_from_monthly(b, rf)
        a, beta, t, resid = capm(r, b, rf)
        row["alpha"], row["beta"], row["t"] = a, beta, t
        # ── 연도 집중도 ── 알파가 몇 해에 몰려 있나. 한 해를 빼서 부호가 뒤집히면
        #   13년 표본처럼 보여도 실제 정보량은 사건 한둘이다.
        yrs = sorted({m[:4] for m in ms})
        if a is not None and len(yrs) >= 5:
            drops = []
            for y in yrs:
                sel = [i for i, m in enumerate(ms) if m[:4] != y]
                if len(sel) < 36:
                    continue
                a2, _, _, _ = capm(r[sel], b[sel], rf[sel])
                if a2 is not None:
                    drops.append((a2, y))
            if drops:
                drops.sort()                     # 가장 많이 깎이는 해가 앞
                row["drop_worst_year"] = {"year": drops[0][1], "alpha": drops[0][0]}
                sel3 = [i for i, m in enumerate(ms) if m[:4] not in {d[1] for d in drops[:3]}]
                if len(sel3) >= 36:
                    a3, _, _, _ = capm(r[sel3], b[sel3], rf[sel3])
                    row["drop_worst3_years"] = {"years": [d[1] for d in drops[:3]], "alpha": a3}
        rows.append(row)
        series[cik] = {"months": ms, "r": r, "b": b, "rf": rf, "resid": resid,
                       "alpha_m": float(np.mean(r - rf) - (beta or 0) * np.mean(b - rf))}

    rows.sort(key=lambda x: (-(x.get("alpha") if x.get("alpha") is not None else -1e9)))
    return rows, series, bench, RF, months


def headline(rows, series, bench, RF):
    """헤드라인 세 줄 — 이 진단물이 실제로 답하는 것."""
    from scipy import stats
    live = [r for r in rows if r.get("alpha") is not None]
    ciks = [r["cik"] for r in live]
    if not ciks:
        return {}

    # 공통 구간에서만 결합검정을 한다(잔차 공분산에 결측이 있으면 GRS가 성립하지 않는다)
    common = set(series[ciks[0]]["months"])
    for c in ciks[1:]:
        common &= set(series[c]["months"])
    common = sorted(common)
    out = {}

    # ── ① 결합검정(GRS) — "알파가 전부 0인가" ─────────────────────────────
    if len(common) > len(ciks) + 2:
        R = np.array([[series[c]["r"][series[c]["months"].index(m)] for m in common] for c in ciks])
        B = np.array([bench.get(m, 0.0) for m in common])
        F = np.array([RF.get(m, 0.0) for m in common])
        resid, alph = [], []
        for i, c in enumerate(ciks):
            a, be, t, e = capm(R[i], B, F)
            if e is None:
                resid, alph = [], []
                break
            resid.append(e)
            alph.append(float(np.mean((R[i] - F) - (be or 0) * (B - F))))
        if resid:
            out["grs"] = grs(np.array(resid), alph, B - F)
            if out["grs"]:
                out["grs"]["n_managers"] = len(ciks)
                out["grs"]["months"] = len(common)

    # ── ② 지속성 — 전반기 알파가 후반기를 예고하는가 ────────────────────────
    half = len(common) // 2
    if half >= 30:
        h1, h2 = common[:half], common[half:]
        a1, a2 = [], []
        for c in ciks:
            S = series[c]
            idx = {m: i for i, m in enumerate(S["months"])}
            for tgt, acc in ((h1, a1), (h2, a2)):
                sel = [idx[m] for m in tgt if m in idx]
                if len(sel) < 24:
                    acc.append(None); continue
                a, _, _, _ = capm(S["r"][sel], np.array([bench.get(m, 0.0) for m in tgt if m in idx]),
                                  np.array([RF.get(m, 0.0) for m in tgt if m in idx]))
                acc.append(a)
        pair = [(x, y) for x, y in zip(a1, a2) if x is not None and y is not None]
        if len(pair) >= 6:
            xs, ys = np.array([p[0] for p in pair]), np.array([p[1] for p in pair])
            sp = stats.spearmanr(xs, ys)
            pe = stats.pearsonr(xs, ys)
            k = max(1, len(pair) // 5)
            top = np.argsort(-xs)[:k]
            bot = np.argsort(xs)[:k]
            out["persistence"] = {
                "n": len(pair), "split": [h1[0], h1[-1], h2[0], h2[-1]],
                "spearman": round(float(sp.statistic), 3), "spearman_p": round(float(sp.pvalue), 4),
                "pearson": round(float(pe.statistic), 3),
                "top_k": int(k),
                "top_next": round(float(np.mean(ys[top])), 2),
                "bottom_next": round(float(np.mean(ys[bot])), 2)}

    # ── ③ 사전 규칙 — "재서 좋은 곳을 고른다"가 실제로 되는가 ─────────────────
    # 이 진단물의 유일한 실사용 가설이다. 매년 말에 **그 시점까지의** 직전 36개월 알파로
    # 상위 3곳을 뽑아 다음 해에 동일가중으로 든다. 사후에 좋은 곳을 아는 것이 아니라
    # 그때 알 수 있던 정보만 쓴다 — 이게 성립해야 순위표에 쓸모가 생긴다.
    allm = sorted({m for c in ciks for m in series[c]["months"]})
    picks, prets = {}, {}
    for yr in range(int(allm[0][:4]) + 3, int(allm[-1][:4]) + 1):
        cut = "%d-12" % (yr - 1)
        win = [m for m in allm if add_months(cut, -35) <= m <= cut]
        if len(win) < 36:
            continue
        sc = []
        for c in ciks:
            S = series[c]
            idx = {m: i for i, m in enumerate(S["months"])}
            sel = [idx[m] for m in win if m in idx]
            if len(sel) < 30:
                continue
            mm = [m for m in win if m in idx]
            a, _, _, _ = capm(S["r"][sel], np.array([bench.get(m, 0.0) for m in mm]),
                              np.array([RF.get(m, 0.0) for m in mm]))
            if a is not None:
                sc.append((a, c))
        if len(sc) < 3:
            continue
        sc.sort(reverse=True)
        top3 = [c for _, c in sc[:3]]
        picks["%d" % yr] = [next(r["name"] for r in rows if r["cik"] == c) for c in top3]
        for m in [x for x in allm if x[:4] == "%d" % yr]:
            vals = []
            for c in top3:
                S = series[c]
                if m in S["months"]:
                    vals.append(S["r"][S["months"].index(m)])
            if vals:
                prets[m] = float(np.mean(vals))
    if len(prets) >= 36:
        pm = sorted(prets)
        a, be, t, _ = capm(np.array([prets[m] for m in pm]),
                           np.array([bench.get(m, 0.0) for m in pm]),
                           np.array([RF.get(m, 0.0) for m in pm]))
        out["prereg_rule"] = {
            "rule": "매년 말 직전 36개월 알파 상위 3곳을 다음 해에 동일가중",
            "start": pm[0], "end": pm[-1], "n_months": len(pm),
            "alpha": a, "beta": be, "t": t,
            "picks": picks,
            "verdict": "작동하지 않는다" if (t is None or abs(t) < 1.96) else "이 표본에서는 유의",
        }
    return out


def main() -> int:
    rows, series, bench, RF, months = compute()
    head = headline(rows, series, bench, RF)
    live = [r for r in rows if r.get("alpha") is not None]

    # 다중검정 — 어느 보정을 쓰든 답이 같다는 것을 보인다
    from scipy import stats
    pv = []
    for r in live:
        t, n = r.get("t"), r.get("n_months")
        pv.append(None if t is None or not n else float(2 * (1 - stats.t.cdf(abs(t), n - 2))))
    for r, p in zip(live, pv):
        r["p"] = None if p is None else round(p, 4)
    head["multiplicity"] = holm_bh(pv)

    doc = {
        "note": "운용사별 13F 복제 — **진단물이다. 전략이 아니다.** 묻는 것은 '유명 헤지펀드를 "
                "따라 사면 되는가' 하나이고, 답은 헤드라인 세 줄이다. 개별 순위표는 부록이다.",
        "not_alpha": [
            "운용사 명단이 사후 선택이다 — 2026년 시점의 유명세로 손으로 고른 18곳이고, "
            "그중 17곳이 지금도 영업 중이다(13년 구간에서 폐업·청산 0곳). 어떤 대조군도 "
            "어떤 다중검정 보정도 이 편향을 상쇄하지 못한다.",
            "'17종 = 전수'가 아니다. 13F 제출인 수천 곳 중 손으로 고른 18곳의 전수일 뿐이다.",
            "유니버스(518종목)와 CUSIP→티커 매핑이 모두 오늘 스냅샷이라, 과거 보유 중 "
            "'지금 대형주로 살아남은 것'만 남는다. 방향은 상방이고 크기는 이 저장소 안에서 "
            "측정할 수 없다. 대조군을 같은 풀 동일가중으로 두어 일부를 상쇄할 뿐이다.",
            "표본에 판정 능력이 없다 — 추적오차 12.7%·13년이면 Bonferroni 문턱을 80% "
            "검정력으로 넘는 데 연 13.5%p 알파가 필요하다. **유의 0건은 예상된 결과이며 "
            "알파 부재의 증거가 아니다.**",
        ],
        "spec": {
            "rebalance": "분기말 + 2개월의 월말 (3/31→5/31 · 6/30→8/31 · 9/30→11/30 · 12/31→2/28)",
            "lookahead_guard": "공시일(13F filed)이 체결일보다 뒤인 셀은 버린다",
            "weights": "주식수 고정 환산 — 분기말 가치 × P[체결월]/P[분기말], 유니버스 안에서 재정규화",
            "between": "리밸런스 사이 표류(매수후보유)",
            "bench": "같은 풀 동일가중(월 리밸) · 베타 차이는 CAPM 알파로 처리",
            "rf": "FRED DGS3MO 월율, 초과수익 기준",
            "gates": "가격결측 비중>20% 또는 유니버스내 <4종목 분기 제외 · 결측은 이월(연속 4분기 초과 시 정지) "
                     "· top1>50% 또는 유효종목수<3 인 분기가 20% 초과면 복제 불가",
        },
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "span": {"start": months[0], "end": months[-1], "n_months": len(months)},
        "headline": head,
        "managers": rows,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s (%dKB)" % (OUT, os.path.getsize(OUT) // 1024))

    g = head.get("grs") or {}
    ps = head.get("persistence") or {}
    mp = head.get("multiplicity") or {}
    print()
    print("■ 헤드라인")
    if g:
        print("  결합검정(GRS)  F(%d,%d)=%.3f · p=%.4f  → '%d곳의 알파가 전부 0'을 %s"
              % (g["df1"], g["df2"], g["F"], g["p"], g["n_managers"],
                 "기각 못 함" if g["p"] >= 0.05 else "기각"))
    if ps:
        print("  지속성        전반기↔후반기 알파 Spearman %.3f (p=%.4f) · Pearson %.3f"
              % (ps["spearman"], ps["spearman_p"], ps["pearson"]))
        print("                전반 상위%d의 후반 알파 %.2f%%  vs  전반 하위%d의 후반 %.2f%%"
              % (ps["top_k"], ps["top_next"], ps["top_k"], ps["bottom_next"]))
    pr = head.get("prereg_rule") or {}
    if pr:
        print("  사전 규칙      %s" % pr["rule"])
        print("                %s~%s(%d개월) α %+.2f%%/yr · t %+.2f · β %.2f → %s"
              % (pr["start"], pr["end"], pr["n_months"], pr["alpha"] or 0,
                 pr["t"] or 0, pr["beta"] or 0, pr["verdict"]))
    if mp:
        print("  다중검정      m=%d · Bonferroni %d건 · Holm %d건 · BH(q=.10) %d건 통과"
              % (mp["m"], mp["bonferroni"], mp["holm"], mp["bh10"]))
    print()
    print("■ 운용사별(부록) — 알파 내림차순")
    for r in rows:
        if r.get("alpha") is None:
            print("  %-26s %s — %s" % (r["name"][:26], r.get("verdict", "?"), (r.get("why") or "")[:52]))
            continue
        print("  %-26s α %+6.2f%%/yr (t %+5.2f) · β %.2f · %d개월 · CAGR %5.2f%% vs 벤치 %5.2f%%"
              % (r["name"][:26], r["alpha"], r["t"] or 0, r["beta"] or 0, r["n_months"],
                 (r["metrics"] or {}).get("cagr") or 0, (r["bench"] or {}).get("cagr") or 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
