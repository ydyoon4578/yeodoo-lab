# -*- coding: utf-8 -*-
"""build/w_stagem.py — 배치 W Tier-1 엔진(종목 단면 · 주 측정): FWL 월별 횡단면 회귀(FM) · 방향 인자 · NW(3)(frozen v_tests.nw_t · 달력 틈 판) ·
연속 z 의 σ_analytic(NaN 멈춤) · 칸 안 위약 · 순위 IC · 10분위 롱숏 · 상태 교차항(시계열 2단) · DM · 표본 밖 R² · PBO/CSCV · BY · P0 기록.

설계 원본(구속): wbatch_research.json final.evaluation.tier1(engine · regression · reported_with · sigma_analytic_continuous · placebo) ·
  slate.common_frame.stage_m_w_controls · G_NoEG_inputs · multiplicity(P0_record · secondary_BY · PBO) · build_plan.modules[w_stagem] · D10 · D11.
  r_stagem 을 복사하지 않고 새로 짰다(D10 — r_stagem 은 H1 γ < 0 이 박혀 있고 · 머리에서 qbatch_core · 함수 안에서 eg30plus 를 부르고 · σ 가 이진 표지용이고 ·
  상수 ALPHA 0.025 · N_PLACEBO 200 이 다르다). 이 모듈은 r_stagem · eg30plus · qbatch_* 를 부르지 않는다(w_guard G-NoEG 정적 점검).
  수학 규칙은 배치 R 과 같다(FWL · 순차 그람–슈미트 두 번 직교화 · 상대 허용 1e−8 · 최소 잔여 자유도 10 · 달력 틈 NW) — 그래서 허용 목록
  별도 과정(w_audit)이 R 의 동결 입력 · R 통제 설정으로 R1 · R2 공개 값(γ −0.1723 · t −2.05 / −0.1538 · −1.04)을 1e−9 로 재현한다.

회귀(달 t 마다): r_{i,t+1} = a_t + γ_t·z_{i,t} + c_t′X_{i,t} + e — X = Stage M-W 통제(FWL 로 먼저 잔차화): log ME(분할만 조정) · r_t · r_{t−12..t−2} ·
  GICS 섹터 더미 · V06 VAL 점수(E/P · S/P 섹터 안 z · 결측 더미). 🚨 B/M 없음(G-NoEG 입력 단위 · U3 엄격 해석 · 배치 R Stage M 의 log B/M 에서 이탈 공개).
  통제 이름은 w_guard 입력 단위 블랙리스트를 지난다(noeg=True 기본) — 우회(noeg=False)는 w_audit 주 스크립트만(R 공개 값 재현).
  결측: 통제별 "drop"(행 제외 — log ME · r_t · 모멘텀) · "dummy"(0 으로 채우고 _na 더미 — VAL) · 신호 결측은 카드가 고른다(focal_miss "drop" · "dummy").
  종속 열은 순서대로 버린다(절편 → 통제 → 결측 더미 → 섹터 → 덧붙인 통제 → 신호). 신호가 통제에 걸려 풀리지 않는 달은 None.

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  S1 방향: summarize · 한쪽 p 는 카드 방향 d(±1)를 인자로 받는다 — 보고 칸 p = P(t(T−1) ≥ d·t)(w_core.one_sided_p) · 가족 판정 칸은 S11.
  S2 σ_analytic(연속 z) = √mean_t[s_t² / (n_t·var(z_res,t))] · s_t = 그달 «통제만» 회귀 잔차 SD(자유도 n − k_c · 배치 R 과 같은 보수 쪽) ·
     var(z_res,t) = z_res′z_res / n_t(통제로 잔차화한 z · 평균 0). 달이 없거나 NaN · 0 · 무한이 끼면 멈춘다.
  S3 칸 안 위약: 달마다 섹터 × 시총 3분위 칸 안에서 z 를 섞는다(칸 크기 ≥ 2) · 같은 통제 기저로 γ_t = z̃_res′y_res / z̃_res′z̃_res · 씨앗 default_rng(seed + i) ·
     돌려주는 것 = 위약 t 와 γ 월 계열 SD(σ_plan 의 위약 90분위) — 보고만(명세 D11 · 채택 표시 밖 · 예외 W02 CBSA 는 카드 모듈).
  S4 상태 교차항(W10m · W11): 달 안에서 상태 s_t 는 상수라 z·s_t 는 z 와 같은 열이 되어 달별 FM 으로 풀리지 않는다 → 교차항 γ =
     «달별 γ_t(z) 를 s_t 에 회귀한 시계열 기울기»(조건부 FM · γ_t = γ0 + γ1·s_t + u_t) · t 는 달력 틈 NW(3)(모멘트 u_t·x_t 를 달력 자리에 · 빈 달 0) ·
     보고 p 는 t(n − 2)(모수 둘 · 등록 전 고침 — 비평 1 L2) · 가족 판정 p 는 S11 · scale{달: c_t} 를 주면 γ_t / c_t 판(W10m 척도 없는 쌍둥이).
  S5 순위 IC = 그달 평균 순위(동률 평균) 피어슨 · 이름 < 10 이면 None · 목표 = 섹터 평균을 뺀 r_{t+1}.
  S6 10분위 롱숏 = 안정 정렬(kind="stable") 위 아래 ⌊n/10⌋ 이름 · EW 또는 시총가중 · 이름 < 20 이면 None.
  S7 DM: d_t = 손실(기준) − 손실(모형) · 평균의 달력 틈 NW(3) t · 양수면 모형이 낫다(W01: 기준 = 같은 KPS8 의 선형 · 능형 · 모형 = IPCA).
  S8 표본 밖 R² = 1 − ΣΣ(y − ŷ)² / ΣΣ y²(0 예측 대비 · 같은 목표 · 달을 모은 판과 달별 판).
  S9 PBO/CSCV(Bailey 외): 행을 S 16 개 연속 토막으로 · C(16, 8) = 12,870 분할 · 표본 안 샤프 최대 설정의 표본 밖 순위 ω = r/(N+1) ·
     λ = ln(ω/(1 − ω)) · PBO = P(λ ≤ 0) — 보고만(명세 multiplicity.PBO).
  S10 P0 기록(바뀌지 않은 랩 규칙 · 가족과 무관 · 기록만): P0 = q·π + (1 − q)·α₁ · π = 1 − Φ(2.27 − ½·|효과_lit|·√T / σ_plan) ·
     σ_plan = max(σ_analytic, 위약 90분위) · q 0.4 · α₁ 0.0125(r_stagem.p0 과 같은 식 — 효과 · σ 는 같은 단위).
  S11 🔁 가족 p(등록 전 보정 · 비평 1 C1 · H3 · M4): **제약 야생 부트스트랩**(Davidson–MacKinnon · Rademacher) — H0 계수 = 0 아래 제약 적합(평균 검정은
     ŷ_r = 0 · 교차항은 절편만)의 잔차에 부호를 곱해 y* 를 B 벌 만들고 같은 설계 · 같은 NW(3) t 를 잰다 · p_one = (1 + #{d·t* ≥ d·t})/(B + 1) ·
     p_two = (1 + #{|t*| ≥ |t|})/(B + 1). 이유: NW(3) t 를 t(T−1) 로 읽으면 T 119 에서 크기가 부풀고(합성 FM 두쪽 6.2%) 영이 많은 상태(W11 s_t 가 0 인 달 73/119 ·
     최대 지렛대 0.18)에서는 두쪽 11.6 ~ 17.3% 로 부푼다 — 부트스트랩은 같은 상태 · 같은 |잔차| 를 써 지렛대 · 이분산을 귀무 분포에 싣는다(selftest 합성 5.3% 대 12.0%).
     가족 B = 9,999(w_core.WILD_B · 씨앗 SEED + FAMILY_SEED_OFF) · 위생 라벨 섞기 회마다 B = 999(w_hygiene).

🚨 랩 규율 — 등록 커밋 전에는 실자료로 γ · IC · 신호-수익 통계를 계산하지 않는다. 수익을 만지는 공개 함수(fm · placebo · ic_series ·
   decile_series)는 자료 종류 kind 를 받고 w_core.assert_kind_allowed 를 지난다: synth · blind 는 언제나 · real 은 WBATCH_COMMIT(등록 커밋) 뒤 ·
   r_repro(배치 R 공개 값 재현)는 w_audit 주 스크립트만. --selftest 는 합성 자료만.

  python build/w_stagem.py --selftest
"""
from __future__ import annotations

import itertools
import math
import os
import sys
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import w_core as WC          # noqa: E402
import w_guard as WG         # noqa: E402

LAG = 3                      # NW(3)
MIN_DOF = 10                 # 달 회귀의 최소 잔여 자유도
TOL = 1e-8                   # 종속 열 판정(잔차 크기 ÷ 원래 크기)
P0_Q, P0_ALPHA1, P0_TCRIT, P0_GATE = 0.4, 0.0125, 2.27, 0.15   # 바뀌지 않은 랩 규칙(기록만)
PLACEBO_Q = 0.90

# Stage M-W 통제(명세 common_frame.stage_m_w_controls) — 이름 · 결측 정책 · 입력 단위(개념 · 원천)
STAGE_M_W = (
    ("log_me", "drop", "log market cap (split-only ME = P_raw × S_filed × Π split)", "v_px_split.me_value"),
    ("r1", "drop", "short-term reversal r_t", "pit_px"),
    ("mom", "drop", "momentum r_{t-12..t-2}", "pit_px"),
    ("val", "dummy", "V06 value score (E/P, S/P within-sector z)", "v_cards.V06"),
)
SECTOR_KEY = "sec"
STAGE_M_W_UNITS = [WG.unit(nm, source=src, concept=cc, use="control") for nm, _, cc, src in STAGE_M_W] + \
    [WG.unit(SECTOR_KEY, source="data/pit_gics_sectors.json", concept="GICS sector dummies", use="control")]
WG.assert_units(STAGE_M_W_UNITS, "w_stagem Stage M-W 통제(모듈 적재)")


def _VT():
    return WC.frozen("v_tests")


# ══════════════════════════════════════════════════════════════════════════
#  FWL 풀이
# ══════════════════════════════════════════════════════════════════════════
def basis(cols, tol=TOL, ref=None):
    """열 [(이름, 벡터)] → (Q 직교 기저, 남긴 이름, 버린 이름). 순서대로 두 번 직교화 — 앞 열로 설명되는 열(잔차 ≤ tol × 원래 크기 ·
    ref 가 있으면 그 크기)은 버린다."""
    n = len(cols[0][1]) if cols else 0
    Qs, kept, drop = [], [], []
    for j, (nm, v) in enumerate(cols):
        v = np.asarray(v, float)
        r0 = float(ref[j]) if ref is not None else float(np.sqrt(v @ v))
        if not r0 > 0:
            drop.append(nm)
            continue
        r = v.copy()
        if Qs:
            Qm = np.column_stack(Qs)
            for _ in range(2):
                r -= Qm @ (Qm.T @ r)
        nr = float(np.sqrt(r @ r))
        if nr <= tol * r0:
            drop.append(nm)
            continue
        Qs.append(r / nr)
        kept.append(nm)
    return (np.column_stack(Qs) if Qs else np.zeros((n, 0))), kept, drop


def solve(y, ctrl, focal, w=None, tol=TOL, min_dof=MIN_DOF):
    """FWL — 통제 기저로 y · 신호를 잔차화하고 신호 계수를 푼다(전체 OLS/WLS 와 같은 계수). 자유도가 모자라면 None.
    w = 가중(시총 WLS) → √(w / 평균 w) 를 곱한다. 돌려주는 것 {b, n, kc, kf, dof, s, s_ctrl, zvar, drop}."""
    y = np.asarray(y, float)
    if w is not None:
        w = np.asarray(w, float)
        sw = np.sqrt(w / w.mean())
        y = y * sw
        ctrl = [(nm, np.asarray(v, float) * sw) for nm, v in ctrl]
        focal = [(nm, np.asarray(v, float) * sw) for nm, v in focal]
    else:
        focal = [(nm, np.asarray(v, float)) for nm, v in focal]
    n = len(y)
    if n == 0:
        return None
    Q, kc, dc = basis(ctrl, tol)
    yr = y - Q @ (Q.T @ y)
    fr = [(nm, v - Q @ (Q.T @ v)) for nm, v in focal]
    _, kf, df = basis(fr, tol, ref=[float(np.sqrt(v @ v)) for _, v in focal])
    dof = n - len(kc) - len(kf)
    if dof < min_dof:
        return None
    b = {nm: None for nm, _ in focal}
    e = yr
    if kf:
        F = np.column_stack([v for nm, v in fr if nm in kf])
        coef = np.linalg.lstsq(F, yr, rcond=None)[0]
        for nm, c in zip(kf, coef):
            b[nm] = float(c)
        e = yr - F @ coef
    zvar = {nm: float(v @ v) / n for nm, v in fr}
    return {"b": b, "n": n, "kc": len(kc), "kf": len(kf), "dof": dof, "s": float(np.sqrt(e @ e / dof)),
            "s_ctrl": float(np.sqrt(yr @ yr / max(1, n - len(kc)))), "zvar": zvar, "drop": dc + df}


def _units_or_bypass(names, noeg, where, use):
    if noeg is True:
        WG.assert_units([WG.unit(nm, use=use) for nm in names], where)
    else:
        WG.assert_bypass_allowed(where)


def design(y, focal, controls=(), miss=None, sectors=None, extra=(), fill=0.0, focal_miss="drop", w=None, sample=None,
           noeg=True, where="design"):
    """달 하나의 설계 — y(다음 달 수익) · focal [(이름, 벡터)](첫 이름이 주 신호) · controls [(이름, 벡터)] · miss{이름: "drop"|"dummy"} ·
    sectors(섹터 표식 배열 → 더미) · extra(섹터 뒤 덧붙인 통제 · 결측은 더미) · w(가중 · 결측 · 0 이하 행 제외) · sample(참인 행만).
    통제 · 신호 이름은 G-NoEG 입력 단위를 지난다(noeg=True) — 우회는 w_audit 만. 돌려주는 것 {y, ctrl, focal, idx, w}."""
    miss = dict(miss or {})
    _units_or_bypass([nm for nm, _ in controls] + [nm for nm, _ in extra], noeg, where, "control")
    _units_or_bypass([nm for nm, _ in focal], noeg, where, "signal")
    y = np.asarray(y, float)
    keep = np.isfinite(y)
    ctrl_v = [(nm, np.asarray(v, float)) for nm, v in controls]
    for nm, v in ctrl_v:
        if miss.get(nm, "dummy") == "drop":
            keep &= np.isfinite(v)
    foc_v = [(nm, np.asarray(v, float)) for nm, v in focal]
    if focal_miss == "drop":
        for _, v in foc_v:
            keep &= np.isfinite(v)
    elif focal_miss != "dummy":
        raise ValueError("focal_miss 는 drop · dummy")
    if w is not None:
        w = np.asarray(w, float)
        keep &= np.isfinite(w) & (w > 0)
    if sample is not None:
        keep &= np.asarray(sample, bool)
    idx = np.flatnonzero(keep)
    cols = [("const", np.ones(len(idx)))]

    def add(nm, v):
        v = v[idx]
        m = ~np.isfinite(v)
        if m.any():
            cols.append((nm, np.where(m, fill, v)))
            cols.append((nm + "_na", m.astype(float)))
        else:
            cols.append((nm, v))
    for nm, v in ctrl_v:
        add(nm, v)
    if sectors is not None:
        sec = np.asarray(sectors, object)[idx]
        for s in sorted(set(sec), key=str):
            cols.append(("sec:" + str(s), (sec == s).astype(float)))
    for nm, v in extra:
        add(nm, np.asarray(v, float))
    fl = []
    for nm, v in foc_v:
        v = v[idx]
        m = ~np.isfinite(v)
        if m.any():
            v = np.where(m, 0.0, v)
            cols.append((nm + "_na", m.astype(float)))
        fl.append((nm, v))
    return {"y": y[idx], "ctrl": cols, "focal": fl, "idx": idx, "w": (w[idx] if w is not None else None)}


def stage_m_w_design(D, focal, extra=(), focal_miss="drop", wls=False, sample=None, where="Stage M-W"):
    """Stage M-W 설계 — 패널 달 dict D(열쇠 y · log_me · r1 · mom · val · sec · me[WLS 가중])에서 통제를 꺼내 design 을 부른다."""
    controls = [(nm, D[nm]) for nm, _, _, _ in STAGE_M_W]
    miss = {nm: pol for nm, pol, _, _ in STAGE_M_W}
    return design(D["y"], focal, controls, miss, sectors=D[SECTOR_KEY], extra=extra, focal_miss=focal_miss,
                  w=(D["me"] if wls else None), sample=sample, where=where)


# ══════════════════════════════════════════════════════════════════════════
#  FM(월별 횡단면) · 요약
# ══════════════════════════════════════════════════════════════════════════
def fm(months, designs_of, names, kind, require_all=True, min_dof=MIN_DOF):
    """월별 횡단면 회귀 — designs_of(m) → 그달 설계 목록(여러 개면 계수를 달마다 평균 · JT) 또는 None(패널 없음).
    돌려주는 것 {months, g{이름: [계수|None]}, n[], skip{달: 사유}, parts[(달, s_ctrl, n, zvar{이름})]}(parts 는 첫 설계 · σ_analytic 용)."""
    WC.assert_kind_allowed(kind, "w_stagem.fm")
    months = list(months)
    WC.assert_window(months, "w_stagem.fm 결정월", basis="decision")        # 사용자 규칙 — 평가 창은 최근 20년(결정월 ≥ 2006-08)
    res = {"months": [], "g": {nm: [] for nm in names}, "n": [], "skip": {}, "parts": [], "drop": {}, "kind": kind}
    for m in months:
        ds = designs_of(m)
        if ds is None:
            res["skip"][m] = "no_panel"
            continue
        rk = []
        for d in ds:
            r = solve(d["y"], d["ctrl"], d["focal"], d.get("w"), min_dof=min_dof)
            if r is None:
                break
            rk.append(r)
        if len(rk) < len(ds) or not rk:
            res["skip"][m] = "dof"
            continue
        res["months"].append(m)
        res["n"].append(int(round(np.mean([r["n"] for r in rk]))))
        for r in rk:
            for nm in r["drop"]:
                res["drop"][nm] = res["drop"].get(nm, 0) + 1
        for nm in names:
            v = [r["b"].get(nm) for r in rk]
            vv = [x for x in v if x is not None]
            res["g"][nm].append(None if ((require_all and len(vv) < len(v)) or not vv) else float(np.mean(vv)))
        res["parts"].append((m, rk[0]["s_ctrl"], rk[0]["n"], dict(rk[0]["zvar"])))
    return res


def nw_t(x, lag=LAG):
    """frozen v_tests.nw_t(바틀렛 · n = 선 관측 수 · 자유도 보정 없음) — 달이 이어진 계열."""
    return _VT().nw_t(np.asarray(x, float), lag)


def nw_t_gap(months, x, lag=LAG):
    """달력 위치를 지킨 NW t — v_tests.nw_t 와 같은 식에 빈 달의 편차를 0 으로 둔다(시차 L 곱은 달력으로 L 달 떨어진 두 달이 모두 선 쌍만)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 5:
        return None
    pos = np.array([WC.mno(m) for m in months], int)
    pos = pos - pos.min()
    e = np.zeros(int(pos.max()) + 1)
    e[pos] = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lag, len(e) - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else None


def summarize(months, x, direction, lag=LAG):
    """계수 월 계열 → T · 평균 · SD · NW(lag) t(쓴 달이 이어지면 v_tests.nw_t · 빈 달이 끼면 nw_t_gap) · 한쪽 p(방향 d · t(T−1))."""
    if direction not in (+1, -1):
        raise SystemExit("🚨 방향은 +1 · −1(카드 H1 을 인자로)")
    pr = sorted((m, v) for m, v in zip(months, x) if v is not None and v == v)
    ms = [m for m, _ in pr]
    v = np.array([b for _, b in pr], float)
    T = len(v)
    if T < 5:
        return {"T": T, "mean": None, "sd": None, "nw_t": None, "p_one": None, "direction": direction, "contiguous": None, "gaps": None}
    gaps = WC.mno(ms[-1]) - WC.mno(ms[0]) + 1 - T
    t_c = nw_t(v, lag)
    t = t_c if gaps == 0 else nw_t_gap(ms, v, lag)
    sd = float(v.std(ddof=1))
    return {"T": T, "mean": float(v.mean()), "sd": sd, "nw_t": t, "nw_t_compressed": None if gaps == 0 else t_c,
            "contiguous": gaps == 0, "gaps": int(gaps), "first": ms[0], "last": ms[-1], "df": T - 1, "direction": direction,
            "t_iid": float(v.mean() / (sd / math.sqrt(T))) if sd > 0 else None, "p_one": WC.one_sided_p(t, T, direction)}


def sigma_analytic(parts, focal):
    """S2 — σ_analytic = √mean_t[s_t² / (n_t·var(z_res,t))](fm 의 parts · 주 신호 이름). 달이 없거나 NaN · 0 · 무한이면 멈춘다."""
    acc = []
    for m, s, n, zv in parts:
        v = zv.get(focal)
        if v is None or not (s == s) or not (v == v) or v <= 0 or n <= 0 or not math.isfinite(s) or not math.isfinite(v):
            raise SystemExit("🚨 σ_analytic — %s 달의 s · var(z_res) 가 정의되지 않는다(s %s · var %s · n %s)" % (m, s, v, n))
        acc.append(s * s / (n * v))
    if not acc:
        raise SystemExit("🚨 σ_analytic — 달이 없다")
    out = float(math.sqrt(np.mean(acc)))
    if not math.isfinite(out):
        raise SystemExit("🚨 σ_analytic 가 NaN · 무한이다")
    return out


# ══════════════════════════════════════════════════════════════════════════
#  칸 안 위약(S3)
# ══════════════════════════════════════════════════════════════════════════
def cells(sector, size, nq=3):
    """섹터 × 시총 nq 분위 칸 표식(그달 표본 안)."""
    sz = np.asarray(size, float)
    qs = np.quantile(sz, [k / nq for k in range(1, nq)])
    ter = np.zeros(len(sz), int)
    for q in qs:
        ter += (sz > q).astype(int)
    sec = np.asarray(sector, object)
    return np.array(["%s|%d" % (s, t) for s, t in zip(sec, ter)], object)


def placebo_block(d, cell, focal_name):
    """설계 d 와 칸 표식(d["idx"] 행 기준) → (Q, y_res, z, 칸 멤버 목록) — 위약 반복마다 통제 기저를 다시 풀지 않게."""
    if d.get("w") is not None:
        raise SystemExit("🚨 위약은 동일가중 주 판에만(가중 판은 위약하지 않는다)")
    Q, _, _ = basis(d["ctrl"])
    y = np.asarray(d["y"], float)
    z = dict(d["focal"])[focal_name]
    cell = np.asarray(cell, object)
    if len(cell) != len(z):
        raise SystemExit("🚨 위약 칸 표식 길이가 설계 행과 다르다")
    mem = [np.flatnonzero(cell == c) for c in sorted(set(cell), key=str)]
    return Q, y - Q @ (Q.T @ y), np.asarray(z, float), [x for x in mem if len(x) > 1]


def placebo(blocks, kind, n_placebo, seed, direction, lag=LAG):
    """칸 안 z 섞기 위약 — blocks = [(달, Q, y_res, z, 칸 멤버)] · n_placebo · seed 는 명시 인자(기본값 없음). 돌려주는 것 {t[], sd_gamma[]}.
    🔎 위약 γ 의 평균은 돌려주지 않는다(t · SD 만)."""
    WC.assert_kind_allowed(kind, "w_stagem.placebo")
    if not isinstance(n_placebo, int) or n_placebo < 1:
        raise SystemExit("🚨 n_placebo 는 명시 정수")
    ts, sds = [], []
    for i in range(n_placebo):
        rng = np.random.default_rng(seed + i)
        ms, g = [], []
        for m, Q, yr, z, mem in blocks:
            perm = np.arange(len(z))
            for c in mem:
                perm[c] = c[rng.permutation(len(c))]
            zp = z[perm]
            zr = zp - Q @ (Q.T @ zp)
            den = float(zr @ zr)
            if den > 1e-12:
                ms.append(m)
                g.append(float(zr @ yr) / den)
        s = summarize(ms, g, direction, lag)
        ts.append(s["nw_t"] if s["nw_t"] is not None else float("nan"))
        sds.append(s["sd"] if s["sd"] is not None else float("nan"))
    return {"t": np.array(ts, float), "sd_gamma": np.array(sds, float), "n": n_placebo, "seed": seed, "scheme": "섹터 × 시총 3분위 칸 안 z 섞기"}


def placebo_rank(t_obs, t_perm, direction):
    """방향 쪽 백분위 = #{d·t_perm < d·t_obs} / 유효 반복 수(보고)."""
    tp = np.asarray(t_perm, float)
    tp = tp[np.isfinite(tp)]
    if t_obs is None or not len(tp):
        return None
    return float(np.mean(direction * tp < direction * float(t_obs)))


def sigma_plan(sig_analytic, placebo_sd, q=PLACEBO_Q):
    """σ_plan = max(σ_analytic, 위약 γ SD 의 q 분위)(바뀌지 않은 랩 규칙 · 기록만)."""
    sd = np.asarray(placebo_sd, float)
    sd = sd[np.isfinite(sd)]
    sp = float(np.quantile(sd, q)) if len(sd) else None
    return {"sigma_plan": max(x for x in (sig_analytic, sp) if x is not None), "sigma_analytic": sig_analytic, "sigma_placebo": sp,
            "binding": "placebo" if (sp is not None and sp > sig_analytic) else "analytic"}


def p0_record(eff_lit, sig_plan, T, q=P0_Q, alpha1=P0_ALPHA1, tcrit=P0_TCRIT):
    """S10 — P0 기록(가족 · 판정과 무관). 돌려주는 것 {p0, pi, t_alt, gate_pass(보고)}."""
    from scipy.stats import norm
    t_alt = 0.5 * abs(eff_lit) * math.sqrt(T) / sig_plan
    pi = float(1 - norm.cdf(tcrit - t_alt))
    p0 = q * pi + (1 - q) * alpha1
    return {"p0": p0, "pi": pi, "t_alt": t_alt, "gate_report": p0 >= P0_GATE, "role": "기록만(가족은 사용자 갱신으로 고정)"}


# ══════════════════════════════════════════════════════════════════════════
#  보고 통계 — 순위 IC · 10분위 · 상태 교차항 · DM · 표본 밖 R² · PBO · BY
# ══════════════════════════════════════════════════════════════════════════
def avg_rank(x):
    x = np.asarray(x, float)
    order = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=float)
    u, inv = np.unique(x, return_inverse=True)
    if len(u) < len(x):
        s = np.bincount(inv, weights=r)
        c = np.bincount(inv)
        r = (s / c)[inv]
    return r


def sector_demean(y, sector):
    y = np.asarray(y, float)
    sec = np.asarray(sector, object)
    out = y.copy()
    for s in set(sec):
        m = (sec == s) & np.isfinite(y)
        if m.any():
            out[sec == s] = y[sec == s] - y[m].mean()
    return out


def rank_ic(z, y, min_n=10):
    """S5 — 한 달의 순위 IC(선 이름끼리)."""
    z, y = np.asarray(z, float), np.asarray(y, float)
    ok = np.isfinite(z) & np.isfinite(y)
    if ok.sum() < min_n:
        return None
    a, b = avg_rank(z[ok]), avg_rank(y[ok])
    if a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def decile_ls(z, y, w=None, min_n=20):
    """S6 — 위 10% − 아래 10%(EW · w 가 있으면 가중)."""
    z, y = np.asarray(z, float), np.asarray(y, float)
    ok = np.isfinite(z) & np.isfinite(y)
    if w is not None:
        w = np.asarray(w, float)
        ok &= np.isfinite(w) & (w > 0)
    idx = np.flatnonzero(ok)
    n = len(idx)
    if n < min_n:
        return None
    order = idx[np.argsort(z[idx], kind="stable")]
    k = n // 10
    lo, hi = order[:k], order[-k:]
    if w is None:
        return float(y[hi].mean() - y[lo].mean())
    return float((w[hi] @ y[hi]) / w[hi].sum() - (w[lo] @ y[lo]) / w[lo].sum())


def ic_series(months, z_of, y_of, kind):
    """달마다 순위 IC 계열 — z_of(m) · y_of(m)(섹터 평균을 뺀 다음 달 수익) → {months, ic[]}."""
    WC.assert_kind_allowed(kind, "w_stagem.ic_series")
    ms, v = [], []
    for m in months:
        r = rank_ic(z_of(m), y_of(m))
        if r is not None:
            ms.append(m)
            v.append(r)
    return {"months": ms, "ic": v}


def decile_series(months, z_of, y_of, kind, w_of=None):
    WC.assert_kind_allowed(kind, "w_stagem.decile_series")
    ms, v = [], []
    for m in months:
        r = decile_ls(z_of(m), y_of(m), None if w_of is None else w_of(m))
        if r is not None:
            ms.append(m)
            v.append(r)
    return {"months": ms, "ls": v}


def nw_ols_gap(months, y, X, lag=LAG):
    """OLS + 달력 틈 NW(lag) 공분산(모멘트 x_t·e_t 를 달력 자리에 · 빈 달 0 · 바틀렛 · 자유도 보정 없음) → (계수, se, n)."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n = len(y)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    pos = np.array([WC.mno(m) for m in months], int)
    pos = pos - pos.min()
    G = np.zeros((int(pos.max()) + 1, X.shape[1]))
    G[pos] = X * e[:, None]
    S = G.T @ G
    for L in range(1, min(lag, len(G) - 1) + 1):
        C = G[L:].T @ G[:-L]
        S += (1.0 - L / (lag + 1.0)) * (C + C.T)
    Ainv = np.linalg.inv(X.T @ X)
    V = Ainv @ S @ Ainv
    return b, np.sqrt(np.diag(V)), n


def state_interaction(months, gamma, state, direction, lag=LAG, B=None, seed=None, scale=None):
    """S4 — 조건부 FM: γ_t = γ0 + γ1·s_t + u_t · 교차항 γ1 의 달력 틈 NW(lag) t · 한쪽 p(방향). months · gamma 는 fm 산출(None 은 뺀다) · state{달: s_t}.
    p_one = t(n − 2)(모수 둘 · S4 · 보고 칸) · B · seed 를 주면 S11 제약 야생 부트스트랩 p(p_wild_one · p_wild_two — 가족 판정 칸)를 더한다 ·
    scale{달: c_t} 를 주면 γ_t / c_t 를 회귀한다(W10m 척도 없는 쌍둥이 — 단면 표준화가 만드는 기계적 교차항을 뺀 판 · 보고)."""
    rows = [(m, g, state.get(m)) for m, g in zip(months, gamma) if g is not None and state.get(m) is not None and state.get(m) == state.get(m)]
    if scale is not None:
        rows = [(m, g / scale[m], s) for m, g, s in rows if scale.get(m) is not None and scale.get(m) == scale.get(m) and scale.get(m) > 0]
    rows.sort()
    if len(rows) < 12:
        return {"T": len(rows), "gamma1": None, "t": None, "p_one": None, "direction": direction}
    ms = [r[0] for r in rows]
    y = np.array([r[1] for r in rows], float)
    s = np.array([r[2] for r in rows], float)
    if s.std() == 0:
        return {"T": len(rows), "gamma1": None, "t": None, "p_one": None, "why": "상태 분산 0", "direction": direction}
    X = np.column_stack([np.ones(len(s)), s])
    b, se, n = nw_ols_gap(ms, y, X, lag)
    t = float(b[1] / se[1]) if se[1] > 0 else None
    out = {"T": n, "df": n - 2, "gamma0": float(b[0]), "gamma1": float(b[1]), "se": float(se[1]), "t": t, "direction": direction,
           "p_one": WC.one_sided_p(t, n, direction, df=n - 2), "first": ms[0], "last": ms[-1], "scaled": scale is not None}
    if B is not None and t is not None:
        w = wild_p(ms, y, X, 1, direction, int(B), int(seed), lag)
        out.update({"p_wild_one": w["p_one"], "p_wild_two": w["p_two"], "B": w["B"], "seed": w["seed"], "t_check": w["t"]})
    return out


# ══════════════════════════════════════════════════════════════════════════
#  S11 제약 야생 부트스트랩 p(가족 판정 · 위생 라벨 섞기) — 등록 전 보정(비평 1 C1 · H3 · M4)
# ══════════════════════════════════════════════════════════════════════════
def _nw_var_cols(H, pos, lag=LAG):
    """모멘트 H(n × B) · 달력 자리 pos → 열마다 바틀렛 NW 분산 Σ_L w_L Σ_t h_t h_{t−L}(빈 달 0 · nw_ols_gap 의 계수 j 대각과 같은 식)."""
    G = np.zeros((int(pos.max()) + 1, H.shape[1]))
    G[pos] = H
    s = np.einsum("ij,ij->j", G, G)
    for L in range(1, min(lag, len(G) - 1) + 1):
        s = s + 2.0 * (1.0 - L / (lag + 1.0)) * np.einsum("ij,ij->j", G[L:], G[:-L])
    return s


def nw_coef_t(months, y, X, j, lag=LAG):
    """OLS 계수 j 의 달력 틈 NW(lag) t — (b_j, t). X 가 절편뿐이면 nw_t_gap(이어진 달이면 frozen v_tests.nw_t)과 같은 값."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    pos = np.array([WC.mno(m) for m in months], int)
    pos = pos - pos.min()
    A = np.linalg.inv(X.T @ X)
    c = X @ A[j]
    b = A @ (X.T @ y)
    e = y - X @ b
    v = float(_nw_var_cols((c * e)[:, None], pos, lag)[0])
    return float(b[j]), (float(b[j] / math.sqrt(v)) if v > 0 else None)


def wild_p(months, y, X, j, direction, B, seed, lag=LAG):
    """S11 — H0 β_j = 0 의 **제약 야생 부트스트랩**(Davidson–MacKinnon WRE · Rademacher 부호): 제약 적합(열 j 를 뺀 OLS · 절편뿐인 평균 검정이면 ŷ_r = 0)의
    잔차 e_r 에 부호 η(±1 · 씨앗 default_rng(seed))를 곱해 y* = ŷ_r + e_r·η 를 B 벌 만들고 같은 설계 · 같은 NW(lag) t 를 다시 잰다.
    p_one = (1 + #{d·t* ≥ d·t}) / (B + 1) · p_two = (1 + #{|t*| ≥ |t|}) / (B + 1). 같은 상태 · 같은 |잔차| 를 쓰므로 지렛대 · 이분산이 귀무 분포에 실린다."""
    if direction not in (+1, -1):
        raise SystemExit("🚨 방향은 +1 · −1")
    if not isinstance(B, int) or B < 99:
        raise SystemExit("🚨 부트스트랩 반복 B 는 99 이상 정수(명시)")
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n = len(y)
    pos = np.array([WC.mno(m) for m in months], int)
    pos = pos - pos.min()
    A = np.linalg.inv(X.T @ X)
    c = X @ A[j]
    b_j, t = nw_coef_t(months, y, X, j, lag)
    if t is None:
        return {"t": None, "p_one": None, "p_two": None, "B": B, "seed": seed}
    Xr = np.delete(X, j, axis=1)
    fr = Xr @ np.linalg.lstsq(Xr, y, rcond=None)[0] if Xr.shape[1] else np.zeros(n)
    er = y - fr
    rng = np.random.default_rng(seed)
    ge, ls = 0, 0
    for k0 in range(0, B, 2000):                                         # 메모리 — 2,000 벌씩
        k = min(2000, B - k0)
        eta = rng.integers(0, 2, size=(n, k)).astype(float) * 2.0 - 1.0
        Ys = fr[:, None] + er[:, None] * eta
        Bc = A @ (X.T @ Ys)
        Es = Ys - X @ Bc
        V = _nw_var_cols(c[:, None] * Es, pos, lag)
        with np.errstate(invalid="ignore", divide="ignore"):
            ts = np.where(V > 0, Bc[j] / np.sqrt(np.where(V > 0, V, 1.0)), 0.0)
        ge += int(np.sum(direction * ts >= direction * t))
        ls += int(np.sum(np.abs(ts) >= abs(t)))
    return {"t": t, "b": b_j, "p_one": (1.0 + ge) / (B + 1.0), "p_two": (1.0 + ls) / (B + 1.0), "B": B, "seed": seed,
            "scheme": "S11 제약 야생 부트스트랩(Rademacher · 같은 NW(%d) t)" % lag}


def family_fm(months, x, direction, B, seed, lag=LAG):
    """가족 FM 통계(S11) — 계수 월 계열의 평균 NW(lag) t(summarize 와 같은 값) + 제약 야생 부트스트랩 p(평균 검정 · 부호 뒤집기)."""
    sm = summarize(months, x, direction, lag)
    pr = sorted((m, v) for m, v in zip(months, x) if v is not None and v == v)
    if sm["nw_t"] is None or len(pr) < 5:
        return dict(sm, t=sm["nw_t"], p_wild_one=None, p_wild_two=None, B=B, seed=seed)
    ms = [m for m, _ in pr]
    v = np.array([b for _, b in pr], float)
    w = wild_p(ms, v, np.ones((len(v), 1)), 0, direction, int(B), int(seed), lag)
    return dict(sm, t=sm["nw_t"], p_wild_one=w["p_one"], p_wild_two=w["p_two"], B=w["B"], seed=w["seed"], t_check=w["t"])


def dm_test(months, loss_bench, loss_model, lag=LAG):
    """S7 — d_t = 손실(기준) − 손실(모형) · 평균 · 달력 틈 NW t(양수 = 모형이 낫다)."""
    rows = sorted((m, a - b) for m, a, b in zip(months, loss_bench, loss_model) if a is not None and b is not None)
    ms = [r[0] for r in rows]
    d = np.array([r[1] for r in rows], float)
    if len(d) < 5:
        return {"T": len(d), "mean": None, "t": None}
    gaps = WC.mno(ms[-1]) - WC.mno(ms[0]) + 1 - len(d)
    t = nw_t(d, lag) if gaps == 0 else nw_t_gap(ms, d, lag)
    return {"T": len(d), "mean": float(d.mean()), "t": t, "gaps": int(gaps)}


def oos_r2(y_by_month, yhat_by_month):
    """S8 — 달을 모은 표본 밖 R²(0 예측 대비) · 달별 R²."""
    sse = sst = 0.0
    per = {}
    for m in sorted(y_by_month):
        y, f = np.asarray(y_by_month[m], float), np.asarray(yhat_by_month[m], float)
        ok = np.isfinite(y) & np.isfinite(f)
        if not ok.any():
            continue
        a, b = float(((y[ok] - f[ok]) ** 2).sum()), float((y[ok] ** 2).sum())
        sse += a
        sst += b
        per[m] = (1 - a / b) if b > 0 else None
    return {"r2": (1 - sse / sst) if sst > 0 else None, "by_month": per}


def pbo_cscv(R, S=16):
    """S9 — R(T × N 설정 월 성과 · 결측 없음) → PBO · λ 분포 요약. 토막 S(짝수) · C(S, S/2) 분할."""
    R = np.asarray(R, float)
    if R.ndim != 2 or R.shape[1] < 2 or not np.isfinite(R).all() or S % 2:
        raise SystemExit("🚨 PBO — 결측 없는 T × N(N ≥ 2) · 짝수 S")
    T, N = R.shape
    blocks = np.array_split(np.arange(T), S)
    lam = []
    for comb in itertools.combinations(range(S), S // 2):
        ins = np.concatenate([blocks[j] for j in comb])
        oos = np.concatenate([blocks[j] for j in range(S) if j not in comb])

        def sharpe(rows):
            X = R[rows]
            sd = X.std(0, ddof=1)
            return np.where(sd > 0, X.mean(0) / np.where(sd > 0, sd, 1.0), 0.0)
        si, so = sharpe(ins), sharpe(oos)
        nstar = int(np.argmax(si))
        rk = avg_rank(so)[nstar] + 1.0
        w = rk / (N + 1.0)
        lam.append(math.log(w / (1.0 - w)))
    lam = np.array(lam)
    return {"pbo": float(np.mean(lam <= 0)), "n_splits": len(lam), "lambda_median": float(np.median(lam)), "S": S, "N": N, "T": T,
            "role": "보고만"}


def by_info(pvals, q=0.10):
    """부 가족 BY(q 0.10 · 보고) — frozen v_tests.by_info."""
    return _VT().by_info(pvals, q)


def dsr(x, n_trials):
    """표본 안 머리 줄 DSR(보고만 · 판정에 쓰지 않는다 · 명세 multiplicity.DSR) — frozen v_tests.dsr."""
    return _VT().dsr(x, n_trials)


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 자료만)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _synth_month(rng, n=300, nsec=8, beta=0.0, collinear=False):
    sec = np.array(["S%d" % (i % nsec) for i in range(n)], object)
    log_me = rng.normal(10, 1.2, n)
    r1 = rng.normal(0, 8, n)
    mom = rng.normal(5, 25, n)
    val = rng.normal(0, 1, n)
    val[rng.random(n) < 0.1] = np.nan
    z = rng.normal(0, 1, n) + 0.3 * (log_me - 10)
    y = beta * z + 0.2 * r1 - 0.01 * mom + rng.normal(0, 8, n)
    D = {"y": y, "log_me": log_me, "r1": r1, "mom": mom, "val": val, "sec": sec, "me": np.exp(log_me), "z": z}
    if collinear:
        D["z"] = 2.0 * log_me
    return D


def _st_solve():
    rng = np.random.default_rng(WC.SEED)
    D = _synth_month(rng)
    d = stage_m_w_design(D, [("z", D["z"])])
    r = solve(d["y"], d["ctrl"], d["focal"])
    X = np.column_stack([v for _, v in d["ctrl"]] + [v for _, v in d["focal"]])
    b_full = np.linalg.lstsq(X, d["y"], rcond=None)[0]
    assert abs(r["b"]["z"] - b_full[-1]) < 1e-10, (r["b"], b_full[-1])
    assert "sec:S0" in r["drop"] or any(x.startswith("sec:") for x in r["drop"])      # 섹터 더미 합 = 절편 → 하나 버림
    assert "val_na" in [nm for nm, _ in d["ctrl"]] and len(d["y"]) == 300              # VAL 결측 = 더미 · 행 유지
    # WLS = 가중 전체 OLS
    dw = stage_m_w_design(D, [("z", D["z"])], wls=True)
    rw = solve(dw["y"], dw["ctrl"], dw["focal"], dw["w"])
    sw = np.sqrt(dw["w"] / dw["w"].mean())
    Xw = np.column_stack([v * sw for _, v in dw["ctrl"]] + [v * sw for _, v in dw["focal"]])
    bw = np.linalg.lstsq(Xw, dw["y"] * sw, rcond=None)[0]
    assert abs(rw["b"]["z"] - bw[-1]) < 1e-10
    # 신호가 통제에 걸리면 None
    Dc = _synth_month(rng, collinear=True)
    dc = stage_m_w_design(Dc, [("z", Dc["z"])])
    rc = solve(dc["y"], dc["ctrl"], dc["focal"])
    assert rc["b"]["z"] is None and "z" in rc["drop"]
    # 자유도 부족 → None · 행 제외(drop 통제 결측)
    Ds = {k: (v[:15] if hasattr(v, "__len__") else v) for k, v in _synth_month(rng).items()}
    ds = stage_m_w_design(Ds, [("z", Ds["z"])])
    assert solve(ds["y"], ds["ctrl"], ds["focal"]) is None
    D2 = _synth_month(rng)
    D2["mom"][:7] = np.nan
    assert len(stage_m_w_design(D2, [("z", D2["z"])])["y"]) == 293
    # 신호 결측 dummy
    D3 = _synth_month(rng)
    zz = D3["z"].copy()
    zz[:5] = np.nan
    d3 = stage_m_w_design(D3, [("z", zz)], focal_miss="dummy")
    assert len(d3["y"]) == 300 and "z_na" in [nm for nm, _ in d3["ctrl"]]
    # 결측 더미가 있으면 채운 상수는 계수에 영향 없음
    a1 = solve(d3["y"], d3["ctrl"], d3["focal"])["b"]["z"]
    d3b = design(D3["y"], [("z", zz)], [(nm, D3[nm]) for nm, _, _, _ in STAGE_M_W], {nm: p for nm, p, _, _ in STAGE_M_W},
                 sectors=D3["sec"], fill=5.0, focal_miss="dummy")
    a2 = solve(d3b["y"], d3b["ctrl"], d3b["focal"])["b"]["z"]
    assert abs(a1 - a2) < 1e-9
    # G-NoEG 입력 단위 — 금지 통제 · 신호 이름은 멈춘다 · 우회는 w_audit 만
    assert _raises(lambda: design(D["y"], [("z", D["z"])], [("lo" + "gbm", D["val"])], {}))
    assert _raises(lambda: design(D["y"], [("r" + "oe", D["z"])], [("log_me", D["log_me"])], {}))
    assert _raises(lambda: design(D["y"], [("z", D["z"])], [("hml_beta", D["val"])], {}))
    assert _raises(lambda: design(D["y"], [("z", D["z"])], [("log_me", D["log_me"])], {}, **{"noeg": False}))   # 실행 중 자물쇠 시험
    return "FWL = 전체 OLS · WLS(1e−10) · 섹터 종속 버림 · 신호 종속 None · 자유도 · 결측 정책(drop · dummy · 채움 무관) · G-NoEG 통제 이름 · 우회 자물쇠"


def _st_fm_summary():
    rng = np.random.default_rng(WC.SEED + 1)
    months = WC.months_between("2016-08", "2026-07")
    panel = {m: _synth_month(rng, beta=0.4) for m in months}
    panel.pop("2018-02")
    res = fm(months, lambda m: None if m not in panel else [stage_m_w_design(panel[m], [("z", panel[m]["z"])])], ["z"], "synth")
    assert res["skip"] == {"2018-02": "no_panel"} and len(res["months"]) == 119
    s = summarize(res["months"], res["g"]["z"], +1)
    assert s["T"] == 119 and s["gaps"] == 1 and not s["contiguous"] and s["nw_t"] > 5 and s["p_one"] < 1e-6
    s_dn = summarize(res["months"], res["g"]["z"], -1)
    assert abs(s_dn["p_one"] - (1 - s["p_one"])) < 1e-12 and s_dn["nw_t"] == s["nw_t"]
    # 이어진 계열에서 nw_t_gap = frozen v_tests.nw_t
    x = rng.normal(0.1, 1.0, 60)
    ms = WC.months_between("2016-09", "2021-08")
    assert abs(nw_t_gap(ms, x) - nw_t(x)) < 1e-12
    ms2 = ms[:10] + ms[11:] + ["2021-09"]
    t_gap = nw_t_gap(ms2, x)
    assert t_gap is not None and abs(t_gap - nw_t(x)) > 1e-6        # 틈이 끼면 달라진다
    # 손으로 푼 틈 판(빈 달 편차 0)
    pos = np.array([WC.mno(m) for m in ms2]) - WC.mno(ms2[0])
    e = np.zeros(pos.max() + 1)
    e[pos] = x - x.mean()
    sv = e @ e / 60 + sum(2 * (1 - L / 4) * (e[L:] @ e[:-L]) / 60 for L in (1, 2, 3))
    assert abs(t_gap - x.mean() / math.sqrt(sv / 60)) < 1e-12
    # JT 평균 · require_all
    res2 = fm(months[:30], lambda m: None if m not in panel else [stage_m_w_design(panel[m], [("z", panel[m]["z"])]),
                                                                    stage_m_w_design(panel[m], [("z", panel[m]["z"] * 0 + 1.0)])],
              ["z"], "synth")
    assert all(v is None for v in res2["g"]["z"])                    # 둘째 판의 신호가 절편에 걸려 None → 평균 없음
    assert _raises(lambda: fm(months[:3], lambda m: None, ["z"], "real"))            # 등록 전 실자료 자물쇠
    assert _raises(lambda: fm(months[:3], lambda m: None, ["z"], "r_repro"))         # 주 스크립트가 w_audit 아님
    assert _raises(lambda: summarize(months, [0.1] * len(months), 0))
    assert _raises(lambda: fm(["2006-07", "2006-08"], lambda m: None, ["z"], "synth"))           # 20년 창 밖 결정월
    assert fm(["2006-08"], lambda m: None, ["z"], "synth")["skip"] == {"2006-08": "no_panel"}
    return "FM(빈 달 · 자유도 건너뜀 · JT 평균 · None · 20년 창) · 방향 인자 요약(p 대칭) · NW gap = v_tests.nw_t(이어짐) · 손풀이 · 실자료 자물쇠"


def _st_sigma():
    rng = np.random.default_rng(WC.SEED + 2)
    months = WC.months_between("2016-08", "2025-07")
    panel = {m: _synth_month(rng, beta=0.0) for m in months}
    res = fm(months, lambda m: [stage_m_w_design(panel[m], [("z", panel[m]["z"])])], ["z"], "synth")
    sa = sigma_analytic(res["parts"], "z")
    sd = float(np.std([v for v in res["g"]["z"] if v is not None], ddof=1))
    assert 0.7 < sd / sa < 1.3, (sd, sa)                               # 귀무 아래 월 γ SD ≈ σ_analytic
    bad = list(res["parts"])
    bad[3] = (bad[3][0], float("nan"), bad[3][2], bad[3][3])
    assert _raises(lambda: sigma_analytic(bad, "z")) and _raises(lambda: sigma_analytic([], "z"))
    bad0 = list(res["parts"])
    bad0[0] = (bad0[0][0], 1.0, 10, {"z": 0.0})
    assert _raises(lambda: sigma_analytic(bad0, "z"))
    # 위약 — 칸 섞기 · 귀무에서 SD ≈ σ_analytic · 씨앗 재현
    blocks = []
    for m in months:
        d = stage_m_w_design(panel[m], [("z", panel[m]["z"])])
        cl = cells(panel[m]["sec"][d["idx"]], panel[m]["log_me"][d["idx"]])
        Q, yr, z, mem = placebo_block(d, cl, "z")
        blocks.append((m, Q, yr, z, mem))
    P1 = placebo(blocks, "synth", n_placebo=40, seed=WC.SEED, direction=+1)
    P2 = placebo(blocks, "synth", n_placebo=40, seed=WC.SEED, direction=+1)
    assert np.array_equal(P1["t"], P2["t"]) and len(P1["t"]) == 40
    assert 0.6 < np.median(P1["sd_gamma"]) / sa < 1.4
    assert abs(np.mean(P1["t"])) < 0.6 and 0.5 < np.std(P1["t"]) < 1.6
    assert _raises(lambda: placebo(blocks, "synth", n_placebo=None, seed=1, direction=1))
    assert _raises(lambda: placebo(blocks, "real", n_placebo=2, seed=1, direction=1))
    assert placebo_rank(10.0, P1["t"], +1) == 1.0 and placebo_rank(-10.0, P1["t"], -1) == 1.0
    sp = sigma_plan(sa, P1["sd_gamma"])
    assert sp["sigma_plan"] >= sa
    # P0 기록(r_stagem.p0 식) — R1 등록 P0 문서의 π · t_alt 재유도(배치 R 의 P0 는 그 뒤 문헌 t 바닥 min(P0_σ, P0_lit) 를 더 걸었다 —
    #   W 는 IC_lit 만 있어 바닥 없이 식 그대로 기록만) · 명세 P0_record_synthetic W01 0.082(σ 0.047) · 0.043(σ 0.07) 재유도(T 117)
    r = p0_record(-0.55, 1.160877, 116)
    assert abs(r["pi"] - 0.610792) < 3e-6 and abs(r["t_alt"] - 2.551383) < 5e-6, r   # 입력 σ 가 6자리 반올림
    assert abs(r["p0"] - (0.4 * r["pi"] + 0.6 * 0.0125)) < 1e-15
    r2 = p0_record(-0.80, 1.564689, 117)
    assert abs(r2["pi"] - 0.689767) < 3e-6 and abs(r2["t_alt"] - 2.76519) < 5e-6, r2
    assert abs(p0_record(0.012, 0.047, 117)["p0"] - 0.082) < 5e-4 and abs(p0_record(0.012, 0.07, 117)["p0"] - 0.043) < 5e-4
    # 칸 표식 · 셋
    c = cells(["a"] * 9, np.arange(9.0))
    assert sorted(set(c)) == ["a|0", "a|1", "a|2"] and list(c).count("a|0") == 3
    return "σ_analytic(연속 · 귀무 SD 일치 · NaN · 0 · 빈 멈춤) · 칸 위약(씨앗 재현 · 귀무 크기 · 명시 인자 · 자물쇠) · σ_plan · P0 재유도(R1 · R2 등록 값)"


def _st_reports():
    rng = np.random.default_rng(WC.SEED + 3)
    # 순위 IC(동률 평균) = scipy spearman
    from scipy.stats import spearmanr
    z = rng.integers(0, 5, 200).astype(float)
    y = rng.normal(0, 1, 200) + 0.1 * z
    assert abs(rank_ic(z, y) - spearmanr(z, y).correlation) < 1e-12
    assert rank_ic(z[:5], y[:5]) is None
    assert np.allclose(avg_rank([3, 1, 1, 2]), [3, 0.5, 0.5, 2])
    # 10분위
    zz = np.arange(100.0)
    yy = np.where(zz >= 90, 2.0, np.where(zz < 10, -1.0, 0.0))
    assert decile_ls(zz, yy) == 3.0 and decile_ls(zz[:10], yy[:10]) is None
    assert abs(decile_ls(zz, yy, w=np.ones(100)) - 3.0) < 1e-12
    sdm = sector_demean([1.0, 3.0, 10.0, np.nan], ["a", "a", "b", "b"])
    assert np.allclose(sdm[:3], [-1, 1, 0]) and np.isnan(sdm[3])
    # 상태 교차항: γ_t = 0.1 + 0.5·s_t + u — 기울기 복원 · 이어진 계열에서 v_tests.nw_ols 와 같다
    ms = WC.months_between("2016-09", "2026-08")
    s = {m: float(v) for m, v in zip(ms, rng.normal(0, 1, len(ms)))}
    g = [0.1 + 0.5 * s[m] + rng.normal(0, 0.3) for m in ms]
    si = state_interaction(ms, g, s, +1)
    assert abs(si["gamma1"] - 0.5) < 0.15 and si["t"] > 5 and si["p_one"] < 1e-6
    X = np.column_stack([np.ones(len(ms)), [s[m] for m in ms]])
    b1, se1, _ = nw_ols_gap(ms, np.array(g), X, 3)
    b2, se2, _ = _VT().nw_ols(np.array(g), X, 3)
    assert np.allclose(b1, b2, atol=1e-12) and np.allclose(se1, se2, atol=1e-12), (se1, se2)
    si_dn = state_interaction(ms, g, s, -1)
    assert abs(si_dn["p_one"] - (1 - si["p_one"])) < 1e-12
    assert state_interaction(ms[:5], g[:5], s, +1)["gamma1"] is None
    # DM
    lb = list(rng.normal(1.0, 0.2, 60))
    lm = [a - 0.1 for a in lb]
    dm = dm_test(ms[:60], lb, lm)
    assert abs(dm["mean"] - 0.1) < 1e-12 and dm["T"] == 60
    lm2 = list(np.array(lb) - 0.1 + rng.normal(0, 0.05, 60))
    assert dm_test(ms[:60], lb, lm2)["t"] > 5
    # 표본 밖 R²
    o = oos_r2({"a": [1.0, -1.0], "b": [2.0]}, {"a": [1.0, -1.0], "b": [0.0]})
    assert abs(o["r2"] - (1 - 4.0 / 6.0)) < 1e-12 and o["by_month"]["a"] == 1.0
    # PBO — 모두 같은 참 샤프 · 섞인 잡음 → PBO ≈ 0.5 근처 · 하나만 참 우위 → PBO 작음
    R0 = rng.normal(0, 1, (160, 6))
    pb0 = pbo_cscv(R0)
    assert pb0["n_splits"] == 12870 and 0.2 <= pb0["pbo"] <= 0.8, pb0
    R1 = R0.copy()
    R1[:, 2] += 0.8
    assert pbo_cscv(R1)["pbo"] < 0.05
    assert _raises(lambda: pbo_cscv(R0[:, :1])) and _raises(lambda: pbo_cscv(np.where(R0 > 2, np.nan, R0)))
    bi = by_info({"a": 0.001, "b": 0.2, "c": None})
    assert bi["admitted"] == ["a"]
    d0 = dsr(rng.normal(0.0, 1.0, 120), 977)
    d1 = dsr(rng.normal(1.0, 1.0, 120), 977)
    assert d0["N"] == 977 and d0["dsr"] < 0.5 < d1["dsr"]
    assert _raises(lambda: ic_series(["2020-01"], lambda m: z, lambda m: y, "real"))
    ics = ic_series(["2020-01", "2020-02"], lambda m: z, lambda m: y, "synth")
    assert len(ics["ic"]) == 2
    return "순위 IC = spearman · 10분위(EW · 가중) · 섹터 평균 빼기 · 상태 교차항(복원 · NW gap = v_tests.nw_ols · 방향) · DM · 표본 밖 R² · PBO 12,870 · BY · DSR"


def _st_static():
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    mods = set()
    for nd in ast.walk(tree):
        if isinstance(nd, ast.Import):
            mods |= {a.name.split(".")[0] for a in nd.names}
        elif isinstance(nd, ast.ImportFrom) and nd.module:
            mods.add(nd.module.split(".")[0])
    bad = [m for m in mods if WG.forbidden(m)]
    assert not bad, bad
    assert not (mods & {"r_stagem", "eg30plus", "qbatch_core", "r_run"}), mods
    names = [nm for nm, _, _, _ in STAGE_M_W]
    assert names == ["log_me", "r1", "mom", "val"] and not WG.check_units(STAGE_M_W_UNITS)
    return "금지 import 없음(r_stagem · eg30plus · qbatch_*) · Stage M-W 통제 넷 + 섹터 · 입력 단위 통과"


def _st_wild():
    """S11 — 야생 부트스트랩: 관측 t 가 NW 식과 같다 · 영이 많은 상태에서 크기가 명목에 가깝다(t(n−2) 판은 부푼다) · 심은 기울기 복원 · 방향 · 반복 명시."""
    from scipy.stats import t as td
    rng = np.random.default_rng(WC.SEED + 7)
    ms = WC.months_between("2016-08", "2026-07")
    ms_g = [m for m in ms if m != "2018-05"]
    x = rng.normal(0.1, 1.0, len(ms_g))
    one = np.ones((len(ms_g), 1))
    assert abs(nw_coef_t(ms_g, x, one, 0)[1] - nw_t_gap(ms_g, x)) < 1e-12
    xc = rng.normal(0.1, 1.0, len(ms))
    assert abs(nw_coef_t(ms, xc, np.ones((len(ms), 1)), 0)[1] - nw_t(xc)) < 1e-12
    sv = np.zeros(len(ms_g))                                                     # 영이 많은 상태(W11 모양: 0 이 약 60% · 큰 값 몇 달)
    hot = rng.choice(len(ms_g), 45, replace=False)
    sv[hot] = np.clip(rng.gamma(0.6, 0.35, len(hot)), 0, 1.0)
    sv[hot[:4]] = 1.0
    X = np.column_stack([np.ones(len(ms_g)), sv])
    gg = rng.normal(0, 1, len(ms_g))
    b, se, _ = nw_ols_gap(ms_g, gg, X)
    assert abs(nw_coef_t(ms_g, gg, X, 1)[1] - b[1] / se[1]) < 1e-12
    st = dict(zip(ms_g, sv))
    rej_w, rej_t, R = 0, 0, 300
    crit = td.isf(0.025, len(ms_g) - 2)
    for r in range(R):
        g = list(rng.normal(0, 1, len(ms_g)) * (1.0 + (sv >= 0.5)))              # 이분산(상태 큰 달 분산 ×4)
        si = state_interaction(ms_g, g, st, -1, B=199, seed=WC.SEED + r)
        assert abs(si["t_check"] - si["t"]) < 1e-12
        rej_w += int(si["p_wild_two"] <= 0.05)
        rej_t += int(abs(si["t"]) >= crit)
    assert 0.015 <= rej_w / R <= 0.09, (rej_w, rej_t)
    assert rej_t > rej_w, (rej_w, rej_t)                                        # t(n−2) 판이 더 자주 기각(부푼 크기)
    g1 = [0.2 - 1.0 * v + e for v, e in zip(sv, rng.normal(0, 0.5, len(ms_g)))]
    s1 = state_interaction(ms_g, g1, st, -1, B=999, seed=WC.SEED)
    assert s1["p_wild_one"] <= 0.01 and s1["t"] < -2.5, s1
    s1u = state_interaction(ms_g, g1, st, +1, B=999, seed=WC.SEED)
    assert s1u["p_wild_one"] > 0.9
    f0 = family_fm(ms_g, list(rng.normal(0.0, 1.0, len(ms_g))), +1, 999, WC.SEED)
    f1 = family_fm(ms_g, list(rng.normal(0.6, 1.0, len(ms_g))), +1, 999, WC.SEED)
    assert f1["p_wild_one"] <= 0.002 and 0.0 < f0["p_wild_one"] <= 1.0 and abs(f1["t_check"] - f1["nw_t"]) < 1e-12
    assert _raises(lambda: wild_p(ms_g, gg, X, 1, +1, 50, 1)) and _raises(lambda: wild_p(ms_g, gg, X, 1, 0, 199, 1))
    ws = state_interaction(ms_g, list(np.array(g1) * 2.0), st, -1, scale={m: 2.0 for m in ms_g})
    assert abs(ws["t"] - s1["t"]) < 1e-9 and ws["scaled"]                         # 척도 쌍둥이(γ_t / c_t)
    return "관측 t = NW 식(평균 · gap · 기울기 1e−12) · 영 많은 이분산 상태에서 두쪽 크기 %.3f(t(n−2) 판 %.3f) · 심은 기울기 p ≤ 0.01 · 방향 · 척도 쌍둥이 · 반복 명시" % (rej_w / R, rej_t / R)


def selftest():
    res, ok = [], True
    for fn in (_st_solve, _st_fm_summary, _st_sigma, _st_reports, _st_wild, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-16s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_stagem selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
