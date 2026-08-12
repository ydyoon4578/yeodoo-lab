#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""페어 트레이딩 — **형성 단계만** 잰다 → build/_probe_pairs.json

사전등록 문서가 아니다. 백테스트도 아니다. 사용자 질문이 *"518종목으로 페어를 어떻게
엮을지부터 보고 싶다"* 였고, 이 파일은 **엮는 규칙을 실제 자료에 대고 돌려 무엇이
나오는지**만 본다. 수익률은 한 줄도 계산하지 않는다 — 그건 사전등록 뒤의 일이다.

── 무엇으로 도는가 ─────────────────────────────────────────────────────
data/sd/<티커>.json 의 `pxd`(분할·배당 조정 종가) · `hd`/`ld`(고가·저가),
data/stocks.json 의 `pxd_dates` 4,428거래일(2009-01-02 ~ 2026-08-11) × 518종목.

🚨 **이 유니버스는 오늘의 생존자다.** 페어 트레이딩에서 이 편향은 다른 규칙보다 나쁘게
   작동한다 — 한쪽 다리가 상장폐지·피인수로 사라진 페어는 **애초에 후보에 안 뜬다.**
   즉 '수렴하지 않는 페어(nonconverging pair)'가 표본에서 구조적으로 빠지는데, Do·Faff(2010)
   가 성과 감쇠의 주원인으로 지목한 것이 정확히 그 비중의 증가다. 이 랩의 PIT 배관
   (index_history + 편출 가격 캐시, build/pit_backtest.py)으로 갈아탈 수 있고, 그건
   백테스트 단계에서 반드시 해야 한다. 형성 규칙을 보는 이 단계에서는 518종으로 둔다.

🚨 **이중클래스를 먼저 처리한다**(DATA-FACTS #5). 유니버스에 GOOG/GOOGL · FOX/FOXA ·
   NWS/NWSA 세 쌍이 있고, 거리법을 그냥 돌리면 이 셋이 상위를 그대로 차지한다.
   같은 회사의 두 클래스는 페어가 아니라 **한 종목의 두 가격표**다. 판정은 티커 모양이
   아니라 CIK 로 한다(BRK.B·BF.B 같은 남남을 묶지 않기 위해).

── 형성 규칙(돌리기 전에 확정했다) ──────────────────────────────────────
GGR(2006) 거리법을 원문 그대로 옮긴다.
  · 형성창 12개월(252거래일) · 거래창 6개월(126거래일, 이 파일에선 안 씀)
  · 정규화 누적수익 경로 p_t = px_t / px_0 (배당조정 종가라 총수익 지수와 같다)
  · 거리 = Σ_t (p_i,t − p_j,t)²  — 최소 상위 5·20 페어
공적분은 실무 필터로 덧댄다.
  · Engle-Granger: log 가격 회귀 → 잔차에 ADF(상수 없음, 시차 1)
  · **양방향(i~j, j~i) 중 더 음수인 t 를 쓴다** — 관행이고, 그만큼 선택 편의가 낀다.
    그래서 임계값을 교과서 값으로 쓰지 않고 **위약(placebo)으로 실측**한다(§4).
  · 반감기 5~30일(OU 적합) · 0교차 횟수
비용 문턱은 이 랩의 자료로만 만든다.
  · Corwin-Schultz(2012) 고저가 유효스프레드. DATA-FACTS #7 이 막아 세운 함정
    (미국 상장분 거래대금 vs 전 시장 시총)을 정의상 밟지 않는 유일한 길이다(#11).

⚠ 여기서 고른 상수(252 · 126 · 상위20 · ±2σ · 반감기 5~30)는 전부 **원논문과 실무 관행의
  값**이고, 결과를 보고 고르지 않았다. 이 파일이 끝난 뒤에 이 값을 움직이면 그게 자유도다.
"""
from __future__ import annotations

import datetime as dt
import io
import itertools
import json
import os
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe_pairs.json")

FORM = 252          # 형성창 — GGR 12개월
TRADE = 126         # 거래창 — GGR 6개월(형성 단계에선 안 쓴다. 기록용)
TOPN = 20           # GGR 상위 20페어
HL_LO, HL_HI = 5, 30    # 실무 반감기 필터(일)
ENTRY_SIGMA = 2.0       # 진입 문턱 ±2σ
BORROW_APY = 0.003      # 대차 일반담보 연 0.3% — 대형주 가정. 하드투보로우는 따로 표시
RNG = np.random.default_rng(20260812)   # 위약 재현성. 결과를 보고 고르지 않는다


# ══ 자료 ═══════════════════════════════════════════════════════════════
def load():
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    n = len(dates)
    ts, px, hi, lo, sec, nm, si = [], [], [], [], {}, {}, {}
    for s in st["stocks"]:
        t = s["t"]
        p = os.path.join(DATA, "sd", t + ".json")
        if not os.path.exists(p):
            continue
        j = json.load(io.open(p, encoding="utf-8"))
        a, h, l = j.get("pxd") or [], j.get("hd") or [], j.get("ld") or []
        if len(a) != n or len(h) != n or len(l) != n:
            continue
        ts.append(t)
        px.append([np.nan if v is None else v for v in a])
        hi.append([np.nan if v is None else v for v in h])
        lo.append([np.nan if v is None else v for v in l])
        sec[t] = s.get("sector") or "?"
        nm[t] = s.get("name") or t
        sg = j.get("sig") or {}
        si[t] = ((sg.get("sipct") or {}).get("v"), (sg.get("dtc") or {}).get("v"))
    return (dates, ts, np.array(px, float).T, np.array(hi, float).T,
            np.array(lo, float).T, sec, nm, si)


def load_same_company(ts):
    """CIK 가 같은 티커 묶음 → 이중클래스. 티커 모양으로 판정하지 않는다(DATA-FACTS #5)."""
    p = os.path.join(DATA, "cik_map.json")
    if not os.path.exists(p):
        return set(), {}
    m = json.load(io.open(p, encoding="utf-8"))
    # ⚠ 지도는 `co` 아래에 있다(형제 키는 n_co 뿐). 최상위를 훑으면 조용히 0쌍이 나오고,
    #   그러면 GOOG/GOOGL 이 '가장 좋은 페어'로 표 맨 위에 앉는다 — 실제로 그렇게 났다.
    cik = {k: str(v).lstrip("0") for k, v in (m.get("co") or {}).items() if v}
    byc = {}
    for t in ts:
        c = cik.get(t)
        if c:
            byc.setdefault(c, []).append(t)
    dual = set()
    groups = {}
    for c, g in byc.items():
        if len(g) > 1:
            groups[c] = sorted(g)
            for a, b in itertools.combinations(sorted(g), 2):
                dual.add((a, b))
    return dual, groups


# ══ 거리법 ═════════════════════════════════════════════════════════════
def ssd_matrix(P):
    """정규화 경로 P(T×N, 각 열 p_0=1) → 모든 쌍의 SSD 거리(N×N).

    Σ_t (p_i−p_j)² = ‖p_i‖² + ‖p_j‖² − 2 p_i·p_j — 그램 행렬 한 번으로 133,903쌍이 끝난다.
    쌍마다 루프를 돌면 같은 값이 수백 배 느리게 나온다.
    """
    G = P.T @ P
    d = np.diag(G)
    D = d[:, None] + d[None, :] - 2 * G
    np.fill_diagonal(D, np.inf)
    return np.maximum(D, 0.0)


# ══ 공적분 — Engle-Granger 를 전 쌍에 대해 벡터화 ═════════════════════
def eg_tstat_all(Y):
    """log 가격 Y(T×N) → EG 잔차 ADF(시차1) t 통계량 행렬 t[i,j] (i 를 j 로 회귀).

    쌍마다 lstsq 를 두 번 도는 대신, 잔차가 **두 중심화 계열의 선형결합**이라는 점을 쓴다.
        e_ij = u_i − b_ij·u_j,   b_ij = (u_i·u_j)/(u_j·u_j),  u = 중심화 log가격
    ADF 회귀에 필요한 내적은 전부 (u_i,u_j) 의 이차형식이라 그램 행렬 아홉 개로 닫힌다.
    ⚠ 상수항은 공적분 회귀에만 있다(중심화가 그 역할). ADF 회귀에는 안 넣는다 —
      잔차의 표본평균이 정의상 0 이라 넣으면 자유도만 버린다.
    """
    T, N = Y.shape
    U = Y - Y.mean(0)                      # 중심화 log 가격
    dU = np.diff(U, axis=0)                # Δ
    A = dU[1:]                             # y  : Δe_t      (t=2..T-1)
    B = U[1:T - 1]                         # x1 : e_{t-1}
    C = dU[:-1]                            # x2 : Δe_{t-1}
    m = A.shape[0]

    def gram(F, G):
        return F.T @ G

    M = {}
    for kf, F in (("A", A), ("B", B), ("C", C)):
        for kg, G in (("A", A), ("B", B), ("C", C)):
            M[kf + kg] = gram(F, G)

    Guu = U.T @ U
    d = np.diag(Guu)
    b = Guu / d[None, :]                   # b[i,j] = (u_i·u_j)/(u_j·u_j)

    def bil(k):
        """(F_i − b F_j)·(G_i − b G_j) — F,G 는 두 글자 키의 앞·뒤."""
        Mk = M[k]
        di = np.diag(Mk)
        return di[:, None] - b * (Mk + Mk.T) + b * b * di[None, :]

    # 정규방정식 X'X (2×2) 와 X'y
    s11 = bil("BB")          # e_lag · e_lag
    s12 = bil("BC")          # e_lag · Δe_lag
    s22 = bil("CC")          # Δe_lag · Δe_lag
    r1 = bil("BA")           # e_lag · Δe
    r2 = bil("CA")           # Δe_lag · Δe
    yy = bil("AA")           # Δe · Δe

    det = s11 * s22 - s12 * s12
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = (s22 * r1 - s12 * r2) / det                 # e_lag 계수 = ADF 의 ρ
        g2 = (s11 * r2 - s12 * r1) / det
        rss = yy - (rho * r1 + g2 * r2)
        s2 = rss / (m - 2)
        var_rho = s2 * s22 / det
        t = rho / np.sqrt(var_rho)
    t[~np.isfinite(t)] = 0.0
    np.fill_diagonal(t, 0.0)
    return t


def half_life(s):
    """OU 적합 반감기(거래일). Δs_t = α + β s_{t-1} + u → HL = −ln2/ln(1+β)."""
    x, y = s[:-1], np.diff(s)
    x = x - x.mean()
    yb = y - y.mean()
    vb = float(x @ x)
    if vb <= 0:
        return np.nan
    beta = float(x @ yb) / vb
    k = 1.0 + beta
    if not (0 < k < 1):
        return np.nan
    return float(-np.log(2) / np.log(k))


# ══ 비용 — Corwin-Schultz 고저가 유효스프레드 ══════════════════════════
def corwin_schultz(H, L):
    """H,L(T×N) → 종목별 유효스프레드(비율) 평균. 음수 추정치는 0 으로 접는다(원논문 관행).

    ⚠ 야간 갭 보정을 안 넣은 단순형이다. 갭이 크면 과대추정 쪽으로 치우친다 —
      비용을 재는 자리에서 과대는 보수적이라 그대로 둔다.
    """
    k = 3 - 2 * np.sqrt(2)
    lh, ll = np.log(H), np.log(L)
    b = (lh - ll) ** 2
    beta = b[:-1] + b[1:]
    H2 = np.maximum(H[:-1], H[1:])
    L2 = np.minimum(L[:-1], L[1:])
    gamma = (np.log(H2) - np.log(L2)) ** 2
    with np.errstate(invalid="ignore"):
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
        S = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    S = np.where(np.isfinite(S), S, np.nan)
    S = np.maximum(S, 0.0)
    return np.nanmean(S, axis=0)


# ══ 한 형성창을 통째로 재는 함수 ═══════════════════════════════════════
def form_window(PX, HI, LO, ts, i1, dual):
    """[i1−FORM, i1) 구간으로 형성. 돌려주는 것은 거리·EG·정규화경로·유효스프레드."""
    W = PX[i1 - FORM:i1]
    ok = np.isfinite(W).all(0) & (W > 0).all(0)
    idx = np.where(ok)[0]
    Wk = W[:, idx]
    P = Wk / Wk[0]                       # 정규화 누적수익 경로 (GGR)
    D = ssd_matrix(P)
    Tt = eg_tstat_all(np.log(Wk))
    Hw, Lw = HI[i1 - FORM:i1][:, idx], LO[i1 - FORM:i1][:, idx]
    S = corwin_schultz(Hw, Lw)
    names = [ts[i] for i in idx]
    # 이중클래스는 형성 단계에서 제외 — 같은 회사의 두 가격표는 페어가 아니다
    pos = {t: k for k, t in enumerate(names)}
    for a, b in dual:
        if a in pos and b in pos:
            D[pos[a], pos[b]] = D[pos[b], pos[a]] = np.inf
    return names, P, D, Tt, S


def top_pairs(D, names, k, sec=None, same_sector=None):
    """거리 최소 k쌍. same_sector=True 면 동일섹터만, False 면 이종섹터만."""
    n = len(names)
    iu = np.triu_indices(n, 1)
    d = D[iu]
    if same_sector is not None and sec is not None:
        sm = np.array([sec[t] for t in names])
        eq = sm[iu[0]] == sm[iu[1]]
        keep = eq if same_sector else ~eq
        d = np.where(keep, d, np.inf)
    order = np.argsort(d)[:k]
    return [(names[iu[0][o]], names[iu[1][o]], float(d[o])) for o in order if np.isfinite(d[o])]


# ══ 위약 — '내가 고른 페어 중 몇 쌍이 잡음에서 나오나' ══════════════════
def placebo_paths(R, kind, rng, RFULL=None):
    """위약 수익률(T×N) 생성.

    🚨 **끝점을 묶는 위약을 쓰면 안 된다.** 처음에 ⓑ를 순환이동, ⓒ를 잔차 순열로 만들었는데
      둘 다 수익률의 **합을 보존**한다 — 누적경로가 원래와 같은 끝점에 못박힌 브라운 브리지가
      되고, 브리지는 자유 랜덤워크보다 훨씬 정상적으로 보인다. 그래서 위약이 실제 자료보다
      더 자주 공적분 판정을 받았다(9.5% vs 7.1%). 위약이 영가설을 재는 게 아니라 자기
      인공물을 재고 있었다. 아래는 셋 다 합을 보존하지 않는다.

    A 교정확인 : 종목별 실제 변동성의 독립 정규 랜덤워크. **이 절차 자체의 크기**를 잰다
                 (양방향 최소 t 를 쓰는 선택 편의가 여기서 그대로 드러난다).
    B 동시성파괴: 각 종목의 창을 **자기 이력의 무작위 다른 시점**에서 뽑는다. 팻테일·변동성
                 군집 같은 실제 동학은 유지되고 동시 공변만 사라진다.
    C 시장보존  : r_i = β_i·r_mkt(같은 창 실제) + 잔차 **복원추출**. 시장 베타 때문에 같이
                 움직이는 부분은 남기고 페어 고유의 관계만 없앤다. 진짜 문턱은 이쪽이다.
    """
    T, N = R.shape
    if kind == "A":
        sd = R.std(0, ddof=1)
        return rng.normal(0.0, 1.0, (T, N)) * sd[None, :]
    if kind == "B":
        out = np.empty_like(R)
        TT = RFULL.shape[0]
        for j in range(N):
            col = RFULL[:, j]
            ok = np.where(np.isfinite(col))[0]
            ok = ok[ok <= TT - 1]
            lo_ = ok[0] if len(ok) else 0
            hi_ = max(lo_ + 1, TT - T)
            s0 = int(rng.integers(lo_, hi_)) if hi_ > lo_ else lo_
            seg = col[s0:s0 + T]
            if len(seg) < T or not np.isfinite(seg).all():
                seg = R[:, j][rng.integers(0, T, T)]      # 물러섬: 복원추출
            out[:, j] = seg
        return out
    mkt = R.mean(1)
    mc = mkt - mkt.mean()
    vm = float(mc @ mc)
    out = np.empty_like(R)
    for j in range(N):
        rj = R[:, j]
        beta = float(mc @ (rj - rj.mean())) / vm if vm > 0 else 0.0
        res = rj - beta * mkt
        out[:, j] = beta * mkt + res[rng.integers(0, T, T)]   # 복원추출 — 합을 보존하지 않는다
    return out


# ══ 본체 ═══════════════════════════════════════════════════════════════
def main() -> int:
    dates, ts, PX, HI, LO, sec, nm, si = load()
    N = len(ts)
    pos_ts = {t: k for k, t in enumerate(ts)}
    dual, dgroups = load_same_company(ts)
    print("자료 — %d종목 × %d거래일 (%s ~ %s)" % (N, len(dates), dates[0], dates[-1]))
    print("이중클래스(CIK 동일) %d쌍: %s"
          % (len(dual), " · ".join("/".join(g) for g in dgroups.values())))

    i1 = len(dates)                                   # 최신 형성창의 끝(배타)
    names, P, D, Tt, S = form_window(PX, HI, LO, ts, i1, dual)
    n = len(names)
    print("\n[형성창] %s ~ %s (%d거래일) · 결측 없는 종목 %d종 · 쌍 %s"
          % (dates[i1 - FORM], dates[i1 - 1], FORM, n, format(n * (n - 1) // 2, ",")))

    iu = np.triu_indices(n, 1)
    dv = D[iu]
    fin = dv[np.isfinite(dv)]
    print("SSD 분포 — 최소 %.4f · 1%% %.3f · 중앙 %.2f · 최대 %.1f"
          % (fin.min(), np.percentile(fin, 1), np.median(fin), fin.max()))

    # ── 페어별 진단 ────────────────────────────────────────────────────
    pos = {t: k for k, t in enumerate(names)}

    def trips(s, mu, sd):
        """형성창에서 ±2σ 진입 → 0 수렴이 몇 번 일어났나.

        ⚠ **표본 안 서술이지 예측이 아니다.** 형성창의 μ·σ 로 그 형성창을 다시 채점하므로
          정의상 후하다. 그래도 필요하다 — 왕복이 0~1회뿐인 페어는 거래창에서 기대할 수
          있는 것도 그만큼이라, '거리가 가깝다'만으로는 안 보이는 축이다.
        """
        z = (s - mu) / (sd if sd > 0 else 1e-12)
        done = open_ = 0
        side = 0
        for v in z:
            if side == 0:
                if abs(v) >= ENTRY_SIGMA:
                    side = 1 if v > 0 else -1
            elif (side > 0 and v <= 0) or (side < 0 and v >= 0):
                done += 1
                side = 0
        if side != 0:
            open_ = 1
        return done, open_

    def diag(a, b):
        ia, ib = pos[a], pos[b]
        s = P[:, ia] - P[:, ib]                  # GGR 스프레드(정규화 지수 단위)
        mu, sd = float(s.mean()), float(s.std(ddof=1))
        hl = half_life(s)
        zc = int(((s[:-1] - mu) * (s[1:] - mu) < 0).sum())
        nt, op = trips(s, mu, sd)
        tmin = float(min(Tt[ia, ib], Tt[ib, ia]))
        cost = float(S[ia] + S[ib])              # 왕복 4레그 = 각 다리 스프레드 1회분씩
        hold = hl if np.isfinite(hl) else 21.0
        borrow = BORROW_APY * hold / 252.0
        gross = ENTRY_SIGMA * sd                 # 2σ → 0 수렴 시 총이익(다리당 $1 기준)
        return {
            "a": a, "b": b, "na": nm[a], "nb": nm[b],
            "seca": sec[a], "secb": sec[b], "same_sec": sec[a] == sec[b],
            "ssd": float(D[ia, ib]), "sd": sd, "hl": None if not np.isfinite(hl) else round(hl, 1),
            "zc": zc, "trips": nt, "open": op, "eg_t": round(tmin, 2),
            "cost": cost, "borrow": borrow,
            "gross": gross, "net": gross - cost - borrow,
            "si_a": si.get(a, (None, None))[0], "si_b": si.get(b, (None, None))[0],
        }

    cand = top_pairs(D, names, 400)
    dg = [diag(a, b) for a, b, _ in cand]

    print("\n=== ① 거리법 상위 20 (섹터 무제약 · 이중클래스 제외) ===")
    print("%-3s %-11s %-24s %7s %6s %5s %4s %6s %6s %6s"
          % ("#", "페어", "섹터", "SSD", "2σ%", "반감기", "왕복", "EG t", "비용%", "순%"))
    for k, r in enumerate(dg[:TOPN], 1):
        sct = (r["seca"][:11] + "=" + r["secb"][:11]) if r["same_sec"] \
            else (r["seca"][:11] + "≠" + r["secb"][:11])
        print("%-3d %-11s %-24s %7.3f %6.2f %5s %3d%s %6.2f %6.2f %6.2f"
              % (k, r["a"] + "/" + r["b"], sct, r["ssd"], 100 * ENTRY_SIGMA * r["sd"],
                 r["hl"] if r["hl"] is not None else "—", r["trips"],
                 "+" if r["open"] else " ", r["eg_t"], 100 * r["cost"], 100 * r["net"]))

    same = [r for r in dg if r["same_sec"]]
    print("\n=== ② 같은 섹터만 상위 10 ===")
    for k, r in enumerate(same[:10], 1):
        print("%-3d %-11s %-22s SSD %7.3f · 2σ %5.2f%% · 반감기 %4s · EG t %6.2f · 순 %6.2f%%"
              % (k, r["a"] + "/" + r["b"], r["seca"][:22], r["ssd"],
                 100 * ENTRY_SIGMA * r["sd"], r["hl"] if r["hl"] is not None else "—",
                 r["eg_t"], 100 * r["net"]))
    print("   상위 400쌍 중 동일섹터 %d쌍(%.0f%%)" % (len(same), 100 * len(same) / len(dg)))

    # ── ③ 거리 기준과 이익 여지가 정면으로 어긋난다 ────────────────────
    print("\n=== ③ 거리를 좁힐수록 벌 것이 줄어든다 — 이 맞바꿈이 형성 규칙의 핵심 ===")
    Pc = P - P.mean(0)
    Gp = Pc.T @ Pc / (FORM - 1)
    dvar = np.diag(Gp)
    SIG = np.sqrt(np.maximum(dvar[:, None] + dvar[None, :] - 2 * Gp, 0.0))   # 전 쌍 스프레드 σ
    sig_all, ssd_all = SIG[iu], D[iu]
    ok = np.isfinite(ssd_all)

    def rk(x):
        o = np.argsort(x)
        r = np.empty(len(x))
        r[o] = np.arange(len(x))
        return r
    sp = float(np.corrcoef(rk(ssd_all[ok]), rk(sig_all[ok]))[0, 1])
    print("전 %s쌍 — SSD 순위 vs 스프레드σ 순위 상관(스피어만) **%.3f**" % (format(int(ok.sum()), ","), sp))
    print("  거리 최소 = 벌 것 최소다. 두 기준이 같은 축을 반대 방향으로 잰다.")
    cs = S[:, None] + S[None, :]
    net_all = ENTRY_SIGMA * sig_all - cs[iu]
    print("  10분위별(SSD 오름차순) 2σ · 비용 · 순:")
    qs = np.argsort(ssd_all[ok])
    v_sig, v_net, v_cost = sig_all[ok], net_all[ok], cs[iu][ok]
    for q in range(10):
        s0, s1 = q * len(qs) // 10, (q + 1) * len(qs) // 10
        sel = qs[s0:s1]
        print("   D%-2d  SSD %9.2f  2σ %6.2f%%  비용 %5.2f%%  순 %6.2f%%"
              % (q + 1, np.median(ssd_all[ok][sel]), 100 * ENTRY_SIGMA * np.median(v_sig[sel]),
                 100 * np.median(v_cost[sel]), 100 * np.median(v_net[sel])))
    print("Corwin-Schultz 유효스프레드 — 중앙 %.3f%% · 90%% %.3f%% (종목 기준)"
          % (100 * np.nanmedian(S), 100 * np.nanpercentile(S, 90)))
    print("⚠ CS 는 야간갭 미보정 단순형이라 대형주 실제 스프레드(수 bp)보다 한 자릿수 크다.")
    print("  그런데도 전 쌍의 %.1f%% 가 2σ > 비용 이다 — **비용은 형성 단계의 구속조건이 아니다.**"
          % (100 * float((net_all[ok] > 0).mean())))
    print("  구속하는 것은 왕복 횟수와 수렴 여부이고, 그건 거래창에서만 잰다.")
    rank_all = sorted(dg, key=lambda r: -r["net"])

    # ── ④ 공적분 다중검정 — 위약으로 임계 실측 ────────────────────────
    print("\n=== ④ 공적분을 %s쌍에 돌리면 몇 쌍이 잡음인가 ===" % format(n * (n - 1) // 2, ","))
    tmin_all = np.minimum(Tt, Tt.T)[iu]
    kidx = [pos_ts[t] for t in names]
    Wk = PX[i1 - FORM:i1][:, kidx]
    R = np.diff(np.log(Wk), axis=0)
    RFULL = np.diff(np.log(np.where(PX[:, kidx] > 0, PX[:, kidx], np.nan)), axis=0)
    obs = {}
    for thr, lbl in ((-3.34, "5%(-3.34)"), (-3.90, "1%(-3.90)")):
        obs[lbl] = float((tmin_all < thr).mean())
    pl = {}
    for kind in ("A", "B", "C"):
        Rp = placebo_paths(R, kind, RNG, RFULL)
        Pp = np.vstack([np.zeros((1, Rp.shape[1])), np.cumsum(Rp, 0)])   # log 가격
        Tp = eg_tstat_all(Pp)
        pl[kind] = np.minimum(Tp, Tp.T)[np.triu_indices(Pp.shape[1], 1)]
    print("%-14s %9s %9s %9s %9s" % ("교과서 임계", "실제자료", "A 랜덤워크", "B 동시성X", "C 시장보존"))
    for thr, lbl in ((-3.34, "5%(-3.34)"), (-3.90, "1%(-3.90)")):
        print("%-14s %8.2f%% %8.2f%% %8.2f%% %8.2f%%"
              % (lbl, 100 * obs[lbl], 100 * (pl["A"] < thr).mean(),
                 100 * (pl["B"] < thr).mean(), 100 * (pl["C"] < thr).mean()))
    print("→ A 가 명목 1% 를 넘는 만큼이 **양방향 최소 t 를 쓰는 선택 편의**다(교과서 임계는 단방향 값).")
    q_a = float(np.percentile(pl["A"], 1))
    q_b = float(np.percentile(pl["B"], 1))
    q_c = float(np.percentile(pl["C"], 1))
    print("위약이 정하는 실측 1%% 임계 — A %.2f · B %.2f · **C %.2f** (교과서 −3.90)" % (q_a, q_b, q_c))
    n_pass_c = int((tmin_all < q_c).sum())
    print("실제자료에서 C 임계를 넘는 쌍 %s개 (%.2f%%) — 시장 공변으로 설명 안 되는 몫"
          % (format(n_pass_c, ","), 100 * float((tmin_all < q_c).mean())))

    # ── ⑤ 세 기준이 같은 페어를 고르는가 ──────────────────────────────
    print("\n=== ⑤ 실무의 세 기준이 고르는 상위20 이 얼마나 겹치나 ===")
    Rc = R - R.mean(0)
    rs = np.sqrt((Rc * Rc).sum(0))
    CORR = (Rc.T @ Rc) / np.outer(rs, rs)
    np.fill_diagonal(CORR, -np.inf)
    for a, b in dual:                       # 이중클래스는 여기서도 뺀다
        if a in pos and b in pos:
            CORR[pos[a], pos[b]] = CORR[pos[b], pos[a]] = -np.inf
    corr_all = CORR[iu]
    tmin_masked = np.where(np.isfinite(ssd_all), tmin_all, 0.0)   # 이중클래스 제외를 승계
    crit = {
        "① 거리 최소(GGR)": np.argsort(ssd_all)[:TOPN],
        "② 공적분 t 최소": np.argsort(tmin_masked)[:TOPN],
        "③ 수익률 상관 최대": np.argsort(-corr_all)[:TOPN],
    }
    keys = list(crit)
    sets = {k: set(map(int, v)) for k, v in crit.items()}
    print("%-20s %s" % ("", "  ".join("%-18s" % k for k in keys)))
    for k in keys:
        print("%-20s %s" % (k, "  ".join("%-18s" % ("%d/20" % len(sets[k] & sets[j])) for j in keys)))
    for k in keys:
        top5 = [(names[iu[0][o]], names[iu[1][o]]) for o in crit[k][:5]]
        ssec = sum(1 for o in crit[k] if sec[names[iu[0][o]]] == sec[names[iu[1][o]]])
        print("  %-18s 동일섹터 %2d/20 · 상위5 %s"
              % (k, ssec, " ".join(a + "/" + b for a, b in top5)))

    # ── ⑥ 형성 안정성 — 창을 굴리면 같은 페어가 남나 ──────────────────
    print("\n=== ⑥ 형성 안정성 — 6개월마다 다시 엮으면 상위20이 얼마나 남나 ===")
    ends, k = [], len(dates)
    while k - FORM >= 0 and len(ends) < 26:
        ends.append(k)
        k -= TRADE
    ends = sorted(ends)
    hist, prev = [], None
    tick_ct, sec_ct = {}, {}
    for e in ends:
        nmz, Pz, Dz, Tz, Sz = form_window(PX, HI, LO, ts, e, dual)
        tp = top_pairs(Dz, nmz, TOPN)
        cur = set((a, b) for a, b, _ in tp)
        keep = None if prev is None else len(cur & prev)
        iuz = np.triu_indices(len(nmz), 1)
        med = float(np.median(Dz[iuz]))
        # 🚨 창마다 위약 C 를 다시 만든다 — '실제가 잡음보다 공적분이 많은가'가 이 창 하나의
        #   우연인지 보려면 임계도 창마다 다시 뽑아야 한다. 한 창의 임계를 돌려쓰면 안 된다.
        kz = [pos_ts[t] for t in nmz]
        Rz = np.diff(np.log(PX[e - FORM:e][:, kz]), axis=0)
        Rpz = placebo_paths(Rz, "C", RNG)
        Ppz = np.vstack([np.zeros((1, Rpz.shape[1])), np.cumsum(Rpz, 0)])
        Tpz = eg_tstat_all(Ppz)
        tpz = np.minimum(Tpz, Tpz.T)[iuz]
        qz = float(np.percentile(tpz, 1))
        obs_z = float((np.minimum(Tz, Tz.T)[iuz] < qz).mean())
        for a, b, _ in tp:
            for t_ in (a, b):
                tick_ct[t_] = tick_ct.get(t_, 0) + 1
            for s_ in (sec[a], sec[b]):
                sec_ct[s_] = sec_ct.get(s_, 0) + 1
        hist.append({"end": dates[e - 1], "n": len(nmz), "med_ssd": med,
                     "min_ssd": float(min(d for _, _, d in tp)), "carry": keep,
                     "same_sec": sum(1 for a, b, _ in tp if sec[a] == sec[b]),
                     "coint_q1": qz, "coint_obs": obs_z,
                     "top": [(a, b) for a, b, _ in tp[:5]]})
        prev = cur
    print("%-12s %5s %8s %8s %7s %7s %7s  %s"
          % ("형성창 끝", "종목", "중앙SSD", "최소SSD", "직전유지", "동일섹터", "공적분", "상위3"))
    for h in hist:
        print("%-12s %5d %8.2f %8.4f %7s %6d %6.2f%%  %s"
              % (h["end"], h["n"], h["med_ssd"], h["min_ssd"],
                 "—" if h["carry"] is None else "%d/20" % h["carry"], h["same_sec"],
                 100 * h["coint_obs"],
                 " ".join(a + "/" + b for a, b in h["top"][:3])))
    cs_ = [h["carry"] for h in hist if h["carry"] is not None]
    print("직전 코호트 대비 상위20 유지 — 평균 %.1f쌍 / 20 (중앙 %.0f)"
          % (np.mean(cs_), np.median(cs_)))
    ex = np.array([h["coint_obs"] for h in hist])
    print("공적분 초과분 — 창별 실제 통과율(위약C 1%% 임계 기준) 평균 %.2f%% · 중앙 %.2f%% · 최대 %.2f%%"
          % (100 * ex.mean(), 100 * np.median(ex), 100 * ex.max()))
    print("  ⚠ 임계가 위약의 1%% 분위라 **초과가 없으면 1.00%% 가 나온다.** 창 %d개 중 "
          "1.5%% 를 넘은 창 %d개." % (len(ex), int((ex > 0.015).sum())))
    print("\n상위20 페어가 몰리는 곳(26개 창 누적 %d 페어 · 종목 등장 횟수):" % (26 * TOPN))
    tot = sum(sec_ct.values())
    print("  섹터 " + " · ".join("%s %.0f%%" % (k[:12], 100 * v / tot)
                                for k, v in sorted(sec_ct.items(), key=lambda x: -x[1])[:6]))
    print("  종목 " + " · ".join("%s %d" % (k, v)
                                for k, v in sorted(tick_ct.items(), key=lambda x: -x[1])[:12]))

    # ── ⑦ 세 기준을 합치면 무엇이 남나 — 출발용 페어북 ─────────────────
    # ⚠ 조합 규칙은 **결과를 보기 전에** 이렇게 적었다. 문턱을 움직이면 그게 자유도다.
    #   ⓐ 같은 섹터(경제적 대체재라는 근거를 사람이 댈 수 있어야 한다)
    #   ⓑ 수익률 상관 상위 1%(공변) · ⓒ SSD 상위 1%(수준 근접) — 둘 다 넘어야 한다
    #   ⓓ 반감기 5~30일 · ⓔ 형성창 ±2σ 왕복 ≥2회(한 번도 안 돌아온 페어는 안 쓴다)
    print("\n=== ⑦ 셋을 모두 걸면 — 출발용 페어북(형성창 %s ~ %s) ==="
          % (dates[i1 - FORM], dates[i1 - 1]))
    c_cut = float(np.percentile(corr_all[np.isfinite(corr_all)], 99))
    d_cut = float(np.percentile(ssd_all[ok], 1))
    print("문턱 — 상관 ≥ %.3f(상위1%%) · SSD ≤ %.3f(상위1%%) · 반감기 %d~%d일 · 왕복 ≥2회 · 동일섹터"
          % (c_cut, d_cut, HL_LO, HL_HI))
    sel = np.where(np.isfinite(ssd_all) & (corr_all >= c_cut) & (ssd_all <= d_cut))[0]
    print("① 상관·② 거리 문턱을 동시에 넘는 쌍 %d개 (각각 1%%씩이면 독립일 때 기대 13개)" % len(sel))
    book = []
    for o in sel:
        a, b = names[iu[0][o]], names[iu[1][o]]
        if sec[a] != sec[b]:
            continue
        r = diag(a, b)
        r["corr"] = float(corr_all[o])
        if r["hl"] is None or not (HL_LO <= r["hl"] <= HL_HI) or r["trips"] < 2:
            continue
        book.append(r)
    book.sort(key=lambda r: r["ssd"])
    print("모두 통과 %d쌍:" % len(book))
    print("%-3s %-11s %-20s %6s %6s %6s %5s %4s %6s %6s"
          % ("#", "페어", "섹터", "SSD", "상관", "2σ%", "반감기", "왕복", "EG t", "순%"))
    for k, r in enumerate(book, 1):
        print("%-3d %-11s %-20s %6.3f %6.3f %6.2f %5.1f %4d %6.2f %6.2f"
              % (k, r["a"] + "/" + r["b"], r["seca"][:20], r["ssd"], r["corr"],
                 100 * ENTRY_SIGMA * r["sd"], r["hl"], r["trips"], r["eg_t"], 100 * r["net"]))
    if book:
        bs = {}
        for r in book:
            bs[r["seca"]] = bs.get(r["seca"], 0) + 1
        print("  섹터 분포 — " + " · ".join("%s %d" % (k[:14], v)
                                          for k, v in sorted(bs.items(), key=lambda x: -x[1])))
        nu = bs.get("Utilities", 0)
        print("  🚨 유틸리티 %d/%d = %.0f%% — 거리만 쓴 26개 창 누적 62%% 에서 여기까지 내려온다."
              % (nu, len(book), 100 * nu / len(book)))

    doc = {
        "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "note": "페어 형성 단계 진단. 수익률 백테스트가 아니다.",
        "universe": {"n": N, "days": len(dates), "from": dates[0], "to": dates[-1],
                     "dual_class": {c: g for c, g in dgroups.items()}},
        "params": {"form": FORM, "trade": TRADE, "topn": TOPN,
                   "hl": [HL_LO, HL_HI], "entry_sigma": ENTRY_SIGMA, "borrow_apy": BORROW_APY},
        "window": {"from": dates[i1 - FORM], "to": dates[i1 - 1], "n_stocks": n,
                   "n_pairs": n * (n - 1) // 2},
        "top": dg[:60],
        "by_net": rank_all[:30],
        "coint": {"obs": obs, "placebo_q1_A": q_a, "placebo_q1_B": q_b, "placebo_q1_C": q_c,
                  "n_pass_C": n_pass_c},
        "tradeoff": {"spearman_ssd_sigma": sp,
                     "pct_pairs_2sigma_over_cost": float((net_all[ok] > 0).mean()),
                     "cs_spread_median": float(np.nanmedian(S))},
        "criteria_overlap": {k: sorted(("%s/%s" % (names[iu[0][o]], names[iu[1][o]]))
                                       for o in crit[k]) for k in keys},
        "book": book, "book_cuts": {"corr": c_cut, "ssd": d_cut,
                                    "hl": [HL_LO, HL_HI], "min_trips": 2},
        "stability": hist,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"), default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
