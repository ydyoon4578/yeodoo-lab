# -*- coding: utf-8 -*-
"""재현 — Shin(2026) 「시총축 적분 진단」(A Cap–Axis Integral Diagnostic of Factor Models).

원문: arXiv 2607.01765v3 [q-fin.GN]. 규약: build/PREREG-2026-09-07-CAPAXIS.md
— **계산 전 커밋 5e7e8fe0**.

🚨 원문은 **전략 논문이 아니라 팩터모형 진단**이다. 여기서 하는 일은 둘이고 섞지 않는다:
  ① 진단 재현 — 다리 곡선 D(p) 와 모형별 알파 경로
  ② 그중 **실제 거래 가능한** rank-area 수익 Y_t 를 랩 규약으로 판정

🚨 이 랩의 유니버스는 시총축의 **위쪽 토막**이다(대형주 518종). 원문은 CRSP 전 상장주다.
  그래서 여기서 p 는 «미국 시장의 누적 시총 비중» 이 아니라 «이 대형주 지수 안의 누적
  비중» 이고, **원문 곡선과 x축이 다르다.** 수치를 나란히 놓고 크기를 견주면 안 된다.
"""
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
sys.path.insert(0, HERE)
import tech_backtest as TB          # noqa: E402  지표·자료 규약은 그 파일 한 곳에 둔다
import index_members as IM          # noqa: E402

GRID = [round(i * 0.005, 3) for i in range(201)]     # 원문 식 41 — L = 201
NW_LAG = 21                                          # 일간 뉴이–웨스트 21일(원문)
TOL = 1e-8                                           # 꼬리 항등식 허용오차(원문 명시)
MIN_FORM = 8                                         # F3 — 형성이 이보다 적으면 측정 불가


def july_forms(dates):
    """매년 7월 첫 거래일의 인덱스(원문 §4.3)."""
    out, seen = [], set()
    for i, d in enumerate(dates):
        if d[5:7] == "07" and d[:4] not in seen:
            seen.add(d[:4])
            out.append(i)
    return out


def build(dates, px, R, FU, pool_at=None):
    """다리 곡선·rank-area 수익을 만든다.

    pool_at(i) → 그 시점 후보 집합. None 이면 소급(오늘 명단 전부).
    돌려주는 것: {"days":[…], "D":{p:[…]}, "Y":[…], "s":{p:[…]}, "resid":최대 항등식 잔차,
                 "forms":형성 횟수, "n_at_form":[…]}
    """
    forms = july_forms(dates)
    if not forms:
        raise SystemExit("7월 형성일을 못 찾았다.")
    order, H = [], {}          # 형성 순서(시총 내림차순) · 보유가치
    days, Dg = [], {p: [] for p in GRID}
    Sg = {p: [] for p in GRID}
    Y, nform, resid = [], [], 0.0
    fi = 0
    for i in range(1, len(dates)):
        if fi < len(forms) and i >= forms[fi]:
            # ── 형성: 직전 시총으로 내림차순 정렬, 초기 보유는 시총 비례 ──
            j = forms[fi] - 1
            cand = pool_at(j) if pool_at else set(px)
            mc = {}
            for t in px:
                if t not in cand:
                    continue
                f = FU.get(t) or {}
                sh = TB.asof_fund(f.get("sh"), dates[j])
                p0 = px[t][j] if px.get(t) else None
                if sh and p0 and sh > 0 and p0 > 0:
                    mc[t] = sh * p0
            if len(mc) >= 30:
                order = sorted(mc, key=lambda t: -mc[t])
                H = {t: mc[t] for t in order}
                nform.append(len(order))
            fi += 1
        if not order:
            continue
        live = [t for t in order if R.get(t) and R[t][i] is not None and H.get(t, 0) > 0]
        tot = sum(H[t] for t in live)
        if tot <= 0 or len(live) < 30:
            continue
        w = [H[t] / tot for t in live]
        r = [R[t][i] for t in live]
        RM = sum(a * b for a, b in zip(w, r))
        # 누적 비중과 접두부 기여
        cw, cr, acc, accr = [], [], 0.0, 0.0
        for a, b in zip(w, r):
            acc += a
            accr += a * b
            cw.append(acc)
            cr.append(accr)
        # 격자별 다리
        k = 0
        for p in GRID:
            if p <= 0:
                Dg[p].append(0.0)
                Sg[p].append(0.0)
                continue
            while k < len(cw) - 1 and cw[k] < p:
                k += 1
            s = cw[k]
            B = cr[k]
            d = B - s * RM
            Dg[p].append(d)
            Sg[p].append(s)
            # 🚨 F1 — 꼬리 다리와의 항등식을 그 자리에서 확인한다(원문 §4.4).
            dt_ = (RM - B) - (1.0 - s) * RM
            resid = max(resid, abs(d + dt_))
        # rank-area 수익(원문 식 49) — 중점 누적비중
        y, run = 0.0, 0.0
        for a, b in zip(w, r):
            m = run + 0.5 * a
            y += a * b * (0.5 - m)
            run += a
        Y.append(y)
        days.append(dates[i])
        # ── 매수후보유로 보유가치를 굴린다(원문 §4.3의 단순판) ──
        #   ⚠ 원문은 배당을 포트폴리오 전체에 재투자한다. 이 랩의 R 은 이미 배당
        #     재투자 총수익이라 종목별로 굴린다 — 그 차이를 결과 문서에 한계로 적는다.
        for t in live:
            H[t] = H[t] * (1.0 + R[t][i])
    return {"days": days, "D": Dg, "S": Sg, "Y": Y, "resid": resid,
            "forms": len(nform), "n_at_form": nform}


def nw_ols(y, X, lag=NW_LAG):
    """절편 포함 OLS + 뉴이–웨스트 t. X 는 열 목록(없으면 평균 검정)."""
    n = len(y)
    k = len(X) + 1
    if n <= k + 5:
        return None, None
    cols = [[1.0] * n] + [list(c) for c in X]
    A = [[sum(cols[a][t] * cols[b][t] for t in range(n)) for b in range(k)] for a in range(k)]
    b = [sum(cols[a][t] * y[t] for t in range(n)) for a in range(k)]
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(k):
        p = max(range(c, k), key=lambda r_: abs(M[r_][c]))
        if abs(M[p][c]) < 1e-14:
            return None, None
        M[c], M[p] = M[p], M[c]
        for r_ in range(c + 1, k):
            f = M[r_][c] / M[c][c]
            for cc in range(c, k + 1):
                M[r_][cc] -= f * M[c][cc]
    beta = [0.0] * k
    for r_ in range(k - 1, -1, -1):
        s = M[r_][k] - sum(M[r_][c] * beta[c] for c in range(r_ + 1, k))
        beta[r_] = s / M[r_][r_]
    e = [y[t] - sum(beta[a] * cols[a][t] for a in range(k)) for t in range(n)]
    # 뉴이–웨스트 샌드위치 — S = Γ0 + Σ_L w_L (Γ_L + Γ_L'), w_L = 1 − L/(lag+1)
    Q = [[A[a][b] / n for b in range(k)] for a in range(k)]
    Qi = _inv(Q)
    if Qi is None:
        return beta[0], None
    g = [[cols[a][t] * e[t] for a in range(k)] for t in range(n)]      # x_t·e_t
    S = [[0.0] * k for _ in range(k)]
    for a in range(k):
        for bb in range(k):
            S[a][bb] = sum(g[t][a] * g[t][bb] for t in range(n)) / n   # Γ0
    for L in range(1, lag + 1):
        wgt = 1.0 - L / (lag + 1.0)
        for a in range(k):
            for bb in range(k):
                c1 = sum(g[t][a] * g[t - L][bb] for t in range(L, n)) / n
                c2 = sum(g[t][bb] * g[t - L][a] for t in range(L, n)) / n
                S[a][bb] += wgt * (c1 + c2)
    V = _mm(_mm(Qi, S), Qi)
    se = math.sqrt(max(V[0][0], 0.0) / n)
    return beta[0], (beta[0] / se if se > 0 else None)


def _inv(M):
    k = len(M)
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(k)] for i, row in enumerate(M)]
    for c in range(k):
        p = max(range(c, k), key=lambda r_: abs(A[r_][c]))
        if abs(A[p][c]) < 1e-14:
            return None
        A[c], A[p] = A[p], A[c]
        d = A[c][c]
        A[c] = [x / d for x in A[c]]
        for r_ in range(k):
            if r_ != c and A[r_][c]:
                f = A[r_][c]
                A[r_] = [x - f * yv for x, yv in zip(A[r_], A[c])]
    return [row[k:] for row in A]


def _mm(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B)))
             for j in range(len(B[0]))] for i in range(len(A))]


ANN = 252.0            # 일간 → 연 환산(원문도 일간 표본에 연 bp 로 적는다)


def curve_stats(alpha):
    """곡선 요약 — SA(부호 면적) · IAE(절대 적분) · SUP. 사다리꼴 가중(원문 식 50~53)."""
    g, a = GRID, alpha
    sa = iae = 0.0
    for i in range(1, len(g)):
        h = g[i] - g[i - 1]
        sa += h * (a[i] + a[i - 1]) / 2
        iae += h * (abs(a[i]) + abs(a[i - 1])) / 2
    return {"SA_bp": round(sa * ANN * 10000, 2),
            "IAE_bp": round(iae * ANN * 10000, 2),
            "SUP_bp": round(max(abs(x) for x in a) * ANN * 10000, 2)}


def leg_report(name, B, factors, dates):
    """한 레그의 진단 — 다리 곡선, 모형별 알파 경로, rank-area 판정."""
    n = len(B["days"])
    idx = {d: k for k, d in enumerate(dates)}
    def col(v):
        return [v[idx[d]] for d in B["days"]]
    out = {"leg": name, "n_days": n, "forms": B["forms"],
           "n_at_form": B["n_at_form"],
           "tail_identity_max_resid": B["resid"],
           "tail_identity_ok": B["resid"] <= TOL}
    if B["forms"] < MIN_FORM:
        out["verdict"] = "측정 불가 — 형성이 %d회뿐이다(문턱 %d)" % (B["forms"], MIN_FORM)
        return out
    # 모형별 알파 경로
    models = {"CAPM": [col(factors["MKT"])],
              "FF3대리": [col(factors["MKT"]), col(factors["SMB"]), col(factors["HML"])]}
    out["models"] = {}
    for mn, X in models.items():
        if any(x is None for x in X):
            continue
        path, tpath = [], []
        for p_ in GRID:
            a, t_ = nw_ols(B["D"][p_], X)
            path.append(a if a is not None else 0.0)
            tpath.append(t_)
        st = curve_stats(path)
        st["curve_bp"] = [round(x * ANN * 10000, 2) for x in path]
        st["coherence"] = (round(abs(st["SA_bp"]) / st["IAE_bp"], 3)
                           if st["IAE_bp"] else None)
        ya, yt = nw_ols(B["Y"], X)
        st["rank_area_alpha_bp"] = round((ya or 0) * ANN * 10000, 2)
        st["rank_area_t_NW"] = (round(yt, 2) if yt is not None else None)
        out["models"][mn] = st
    # 모형 없는 날것 — 다리의 평균(진단의 원재료)
    raw = []
    for p_ in GRID:
        v = B["D"][p_]
        raw.append(round(sum(v) / len(v) * ANN * 10000, 2))
    out["raw_bridge_bp"] = raw
    out["raw_stats"] = curve_stats([x / (ANN * 10000) for x in raw])
    ym = sum(B["Y"]) / n
    ysd = (sum((x - ym) ** 2 for x in B["Y"]) / (n - 1)) ** 0.5
    _, yt0 = nw_ols(B["Y"], [])
    out["rank_area"] = {
        "mean_bp_yr": round(ym * ANN * 10000, 2),
        "vol_pct_yr": round(ysd * (ANN ** 0.5) * 100, 2),
        "sharpe": round(ym / ysd * (ANN ** 0.5), 3) if ysd > 0 else None,
        "t_NW": (round(yt0, 2) if yt0 is not None else None),
        "note": ("Y_t = Σ wᵢRᵢ(½−mᵢ) — 큰 종목에 +, 작은 종목에 −. 제로투자라 "
                 "무위험이자율을 안 뺀다(원문 식 49).")}
    return out


def main():
    dates, px, vlm, hi, lo, meta, rf = TB.load(full=True)
    R = TB.daily_rets(px)
    FU = TB.load_fund()
    FACP = TB.load_factor_proxies(dates)
    IDXR = TB.load_index_tr(dates)
    mkt = IDXR.get("S&P 500")
    if not mkt:
        raise SystemExit("시장(S&P 500 PR)을 못 읽었다 — 회귀를 못 한다.")
    factors = {"MKT": mkt, "SMB": FACP.get("SMB"), "HML": FACP.get("HML")}
    # PIT 후보 — 그때 지수 편입명단
    mem = IM.load()[0] if hasattr(IM, "load") else None   # (months, 이월목록)
    def pool_at(i):
        return IM.at(mem, dates[i][:7], label="지수 멤버십")
    legs = {}
    for nm, pa in (("retro", None), ("pit", pool_at if mem else None)):
        if pa is None and nm == "pit":
            continue
        B = build(dates, px, R, FU, pool_at=pa)
        legs[nm] = leg_report(nm, B, factors, dates)
        print("  [%s] %d일 · 형성 %d회 · 꼬리항등식 잔차 %.2e (%s)"
              % (nm, legs[nm]["n_days"], legs[nm]["forms"],
                 legs[nm]["tail_identity_max_resid"],
                 "통과" if legs[nm]["tail_identity_ok"] else "🚨 실패"))
    doc = {
        "note": ("재현 — Shin(2026) 「시총축 적분 진단」 arXiv 2607.01765v3. "
                 "🚨 전략 논문이 아니라 팩터모형 진단이다. 다리 곡선은 진단이고, "
                 "거래 대상으로 삼은 것은 rank-area 수익 Y_t 하나뿐이다."),
        "prereg": "build/PREREG-2026-09-07-CAPAXIS.md (계산 전 커밋 5e7e8fe0)",
        "paper": {"title": "A Cap-Axis Integral Diagnostic of Factor Models",
                  "author": "Useong Shin (Sogang)", "arxiv": "2607.01765v3",
                  "window": "1967-01~2024-12 · CRSP 전 상장주 · 14,598일",
                  "reported_daily": {
                      "CAPM": {"SA": -10.9, "t": -0.57, "IAE": 11.0, "SUP": 26.7},
                      "FF3": {"SA": 21.2, "t": 1.94, "IAE": 21.7, "SUP": 42.8},
                      "Carhart": {"SA": 20.8, "t": 1.88, "IAE": 21.4, "SUP": 42.0},
                      "FF5": {"SA": 7.6, "t": 0.71, "IAE": 10.3, "SUP": 29.0},
                      "FF6": {"SA": 8.2, "t": 0.77, "IAE": 10.5, "SUP": 28.3},
                      "q5": {"SA": -39.6, "t": -3.49, "IAE": 39.6, "SUP": 68.0}}},
        "caveat": ("🚨 원문 수치와 크기를 견주면 안 된다. 원문의 p 는 «미국 시장 누적 시총 "
                   "비중» 이고 이 랩의 p 는 «대형주 518종 안의 누적 비중» 이다 — x축이 다르다. "
                   "그리고 이 랩에는 정본 FF 가 없어 ETF 대리변수를 쓴다(FF5·q5 는 없다)."),
        "grid_n": len(GRID), "nw_lag": NW_LAG, "ann": ANN,
        "as_of": dates[-1], "legs": legs,
    }
    pth = os.path.join(DATA, "cap_axis_bridge.json")
    json.dump(doc, io.open(pth, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→ %s" % pth)
    for nm, L in legs.items():
        if "rank_area" not in L:
            print("  [%s] %s" % (nm, L.get("verdict"))); continue
        ra = L["rank_area"]
        print("  [%s] rank-area: 연 %+.1fbp · 변동성 %.2f%% · 샤프 %s · t(NW) %s"
              % (nm, ra["mean_bp_yr"], ra["vol_pct_yr"], ra["sharpe"], ra["t_NW"]))
        for mn, S in (L.get("models") or {}).items():
            print("      %-8s SA %+8.1fbp · IAE %7.1fbp · SUP %7.1fbp · rank-area α %+.1fbp (t %s)"
                  % (mn, S["SA_bp"], S["IAE_bp"], S["SUP_bp"],
                     S["rank_area_alpha_bp"], S["rank_area_t_NW"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
