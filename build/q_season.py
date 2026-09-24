# -*- coding: utf-8 -*-
"""build/q_season.py — 배치 Q 카드 Q11 SEASEC-A · 섹터 동월 계절성(같은 달 과거 최대 20년 SPY 대비 평균 상위 3 · Heston·Sadka/KLN 원형).

근본 이유: 섹터 수익에는 해마다 같은 달에 되풀이되는 구조가 있다 — ① 업종 공통의 계절 실적(임의소비재의 연말 분기 · 에너지·유틸리티의
수요 계절)을 투자자가 직전의 낮은 분기에 무게를 두어 매번 과소평가하고(CHSS 2017) ② 무드 베타가 높은 섹터는 낙관적인 달에, 방어
섹터는 비관적인 달에 상대적으로 강하며(Hirshleifer 외 2020) ③ 달력에 묶인 기관 리밸런싱이 같은 달에 같은 방향 수급을 만든다
(Bogousslavsky 2016). KLN(2021)은 계절성과 계절 반전을 1년 동안 더하면 0 이 된다고 보였다 — 위험 보상이 아니라 일시적 오가격이라
그 달에 강했던 섹터를 그 달에만 드는 것이 수확 방법이다.

규칙(사전등록 카드 원문 — scratchpad/qbatch_final.md «# Q11»):
  자산 XLB XLE XLF XLI XLK XLP XLU XLV XLY(고정 · XLRE · XLC 는 같은 달 관측 10개 미만이라 뺀다)
  r(s,m) = px(me[m])/px(me[m−1]) − 1(assets.json 수정종가) · x(s,m) = r(s,m) − r(SPY,m)
  편입 f(2016-08 ~ 2026-07) · 목표 달 t = f+1: S(s,f) = x(s, t−12j) 의 평균(j = 1..J · J = 자료가 있는 지난 해 수 · 20 상한 · 10 이상)
  상위 3(동점은 알파벳) · 1/3 씩 전액 · f 종가 매매(10bp) · t 말까지 보유 · 펀드 90/10 대 SPY TR(PR 도)
  G4 (a) C1 = 9 섹터 동일가중(같은 틀) — 전 월 평균(슬리브 − C1) > 0(점)
     (b) 위약: 2006..2025 해마다 그해 있는 달 이름의 균등 순열 π_y(2006 은 11개) 하나를 9 섹터 · SPY 의 x 이력에 함께 걸고
         한 번 뽑기 안의 모든 편입에 고정 · S 만 다시 · 실제 보유 수익은 그대로 · 1000번(씨앗 SEED + i) — 참 (슬리브 − C1) ≥ 95 백분위
  측정만: SEASEC-B(N = S − O · O = x(s, t−k) 평균, k = 13..12J, k mod 12 ≠ 0) · 달력 이동 11개(목표 t 를 t+k 달의 S 로) · P1/P2 이야기 점검
  귀속 상한(카드 «A 가 통과하고 B 가 실패하면 '섹터 드리프트, 계절성 아님'»): B 에 러너의 A 관문(judge_card · gates_pass)을 그대로 걸고
    G1 은 t_B ≥ t_A — B 가 통과하지 못하면 label_caps['seasec_b_attrib'] = True(러너는 A 가 통과할 때만 상한을 건다)
출처: Heston & Sadka(2008 JFE · 2010) · HXZ 2020 부록 A.5.51 · OSAP SignalDoc · Keloharju·Linnainmaa·Nyberg(2021) · CHSS(2017).
GICS 개편(2016-09 · 2018-09 · 2023-03)은 알리고 고치지 않는다(카드).

🚨 selftest · dry 는 규칙 · 대조 · 팔 · 위약의 수익을 계산하거나 찍지 않는다. run 은 한 번 굽기(러너)에서만 부른다.

  python build/q_season.py --selftest
  python build/q_season.py --dry
"""
from __future__ import annotations
import hashlib, json, os, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q               # noqa: E402

CARDS = {"Q11": {"cls": "A", "slot": "A4"}}
NPERM = 1000                           # 달 이름 순열 위약 — 연기 시험에서 작게 덮어쓴다
SECS = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")   # 알파벳 = 동점 순서
BASE = "SPY"
JMAX, JMIN, TOPN = 20, 10, 3
PY0, PY1 = 2006, 2025                  # 위약 순열을 거는 해
NSHIFT = 11
PCT = 95
COST20 = 0.0020
DEF = ("XLP", "XLU", "XLV")            # P2 방어 섹터
INTERP = [
    "'슬리브 − C1' = 펀드 월 초과 차 X_A − X_C1(카드 'same frame' = 같은 90/10 틀 · TR · 10bp) — 바스켓 수익 차가 아니다. 두 판의 부호가 늘 같지는 않다: "
    "월말 펀드 되돌림 비용(2 × 10bp × |슬리브 몫 − 0.1|)이 집중된 상위 3 슬리브에서 EW9 보다 커서 펀드 판이 약 1e-4 %/월 아래로 치우친다. "
    "G4 점 관문과 위약 통계는 펀드 판 · 바스켓 판 평균은 log['sleeve_minus_C1_basket'] 에 보고만.",
    "J = 목표 t 의 같은 달(t−12j, j = 1..20) 중 자료가 있는 해 수 — 2006-01 은 전달 종가가 없어 빠진다(1월 목표는 J 가 하나 적다).",
    "달력 이동 팔 k(1..11) = 목표 t 를 달 t+k 의 S(규칙 정의 그대로: (t+k)−12j, j = 1..20 중 있는 것 · J ≥ 10)로 순위 — 비판 원문 '(rank the target month t by the S of month t+k)'.",
    "SEASEC-B: O 의 J 는 같은 편입의 S 의 J · k = 13..12J 중 12 배수 제외 · N = S − O 상위 3.",
    "SEASEC-B '실패'(카드에 수치 정의가 없다 — 카드 수정 필요): B 통과 = G1 t_B ≥ t_A(같은 NW(3) · t(119) 이므로 p_B ≤ p_A) ∧ G2 '양면' ∧ "
    "러너 gates_pass(G3 · G4 · G5 · G6) — G4 는 B 의 점 관문(X_B − X_C1 평균 > 0)만(위약은 B 에 돌리지 않는다 · 카드에 없다) · G5 20bp 는 팔 'SEASEC-B@20bp'. "
    "실패 = 통과가 아님 → label_caps['seasec_b_attrib'] = True. 러너 verdicts 는 A 가 통과할 때만 상한을 거므로 '(A 통과) ∧ (B 실패)' 가 된다.",
    "G1 을 t_B ≥ t_A 로 둔 까닭: A 가 통과했다면 A 가 넘은 문턱 τ_A(Bretz 단계 · BH k 번째)는 p_A 이상이다 — 그래서 p_B ≤ p_A 이면 p_B ≤ τ_A. "
    "모듈은 τ_A 를 모르므로(다른 카드의 p 가 정한다) 이 읽기는 'A 가 넘은 G1 단계를 B 도 넘는가' 보다 느슨하지 않다: 그 읽기가 거는 상한은 모두 걸고, "
    "p_A < p_B ≤ τ_A 인 경우에만 더 건다(보수 쪽). t_A · p_A · t_B · p_B · 관문 조각은 log['seasec_b'] 에 싣는다.",
    "상한이 걸리면 카드 이름은 '섹터 드리프트, 계절성 아님'(log['label_if_capped']) — 러너의 판정 문자열은 '측정만(재포장 표시)'. A 가 통과하지 않으면 이 불리언은 뜻이 없다.",
    "위약 순열 방향: 해 y 의 있는 달 행 rows_y 에 X̃[rows_y] = X[rows_y[π_y]] · 9 섹터 열에 같은 π_y · 2026 행과 2006-01 은 건드리지 않는다(S 가 쓰지 않는다).",
    "위약 관문: 참값 ≥ np.percentile(draws, 95)(선형 보간 · '이상' — q_qmj · q_eap · q_riegk · q_ltd · q_netper 와 같다). "
    "q_switch.pct_rank(참값보다 작은 뽑기의 백분율) 판은 log['placebo_pct_rank'] 에 보고만.",
    "C1 = 9 섹터 1/9 씩 매달 되돌림(10bp).",
    "P1 = 목표 11월 · 12월 둘 다 XLY 가 상위 3 인 해가 절반 이상(2016..2025 의 10해 중 ≥ 5) — 'pass'. 다른 읽기(11월 ≥ 5/10 이고 12월 ≥ 5/10 'pass_each' · "
    "합친 20 중 ≥ 10 'pass_pooled')와 센 수도 싣는다(보고만).",
    "P2 = 목표 9·10월의 XLP/XLU/XLV 뽑힘 수 > 목표 1월 + 4월의 뽑힘 수(보유 창 2016-09..2026-08 안의 목표 달).",
    "달력 이동 11개는 기술만: 참 k=0 이 k = 0..11 의 12개 중 몇 위인지(전 월 평균 X_k − X_C1 · 1 = 가장 큼 · 같으면 k 가 작은 쪽이 위) — log['shift_rank'].",
    "PYTHONHASHSEED: qbatch_core.etf_path 가 매매액을 문자열 집합 순서로 더해 경로가 마지막 비트에서 갈릴 수 있다(≤ 4.4e-16 상대) — 굽기 때 값은 log['hashseed'].",
]
LABEL_IF_CAPPED = "섹터 드리프트, 계절성 아님"


# ── 이력 ─────────────────────────────────────────────────────────────────
class Hist:
    """월 x 행렬(행 = 달 2006-01..last · 열 = SECS) — x(s,m) = r(s,m) − r(SPY,m) · 자료가 없는 행은 NaN(전 열 함께)."""

    def __init__(self, A, last):
        self.A = A
        self.months = [m for m in sorted(A.me) if m <= last]
        self.row = {m: j for j, m in enumerate(self.months)}
        X = np.full((len(self.months), len(SECS)), np.nan)
        for j, m in enumerate(self.months):
            rs = A.monthly(BASE, m)
            vals = [A.monthly(s, m) for s in SECS]
            if rs is None and all(v is None for v in vals):
                continue
            if rs is None or any(v is None for v in vals):
                raise RuntimeError("%s 에 섹터 · SPY 월 수익이 일부만 있다" % m)
            X[j] = np.array(vals) - rs
        self.X = X
        self.ok = ~np.isnan(X).any(axis=1)

    def lag_rows(self, f, k=0):
        """목표 t = f+1 을 달 u = t+k 의 이름으로 — u−12j(j = 1..JMAX) 중 자료 있는 행. 모두 f 이하(단언)."""
        t = Q.mshift(f, 1)
        u = Q.mshift(t, k)
        rows = []
        for j in range(1, JMAX + 1):
            mm = Q.mshift(u, -12 * j)
            assert mm <= f, (f, k, mm)
            r = self.row.get(mm)
            if r is not None and self.ok[r]:
                assert self.A.me[mm] <= self.A.me[f]
                rows.append(r)
        return rows

    def o_rows(self, f, J):
        """SEASEC-B 의 O — x(s, t−k), k = 13..12J, k mod 12 ≠ 0(모두 있어야 한다)."""
        t = Q.mshift(f, 1)
        rows = []
        for k in range(13, 12 * J + 1):
            if k % 12 == 0:
                continue
            mm = Q.mshift(t, -k)
            assert mm <= f
            r = self.row.get(mm)
            if r is None or not self.ok[r]:
                raise RuntimeError("SEASEC-B %s 의 O 에 %s 가 없다" % (f, mm))
            rows.append(r)
        return rows

    def index(self, forms, k=0):
        """편입 × JMAX 행 번호(빈 칸은 덧댄 0 행) · J."""
        R = np.full((len(forms), JMAX), len(self.months), dtype=np.int64)
        J = np.zeros(len(forms))
        for a, f in enumerate(forms):
            rows = self.lag_rows(f, k)
            if len(rows) < JMIN:
                raise RuntimeError("%s(k=%d) 같은 달 관측 %d < %d" % (f, k, len(rows), JMIN))
            R[a, :len(rows)] = rows
            J[a] = len(rows)
        return R, J

    def year_rows(self):
        """위약 순열 단위 — 해 y(2006..2025)의 자료 있는 행(달 순)."""
        out = []
        for y in range(PY0, PY1 + 1):
            rows = [self.row[m] for m in self.months if int(m[:4]) == y and self.ok[self.row[m]]]
            out.append(np.array(rows, dtype=np.int64))
        return out


def scores(X, R, J):
    Xp = np.vstack([X, np.zeros((1, X.shape[1]))])
    return Xp[R].sum(axis=1) / J[:, None]


def top(Smat):
    """상위 TOPN 열(동점은 알파벳 = 열 순 — 안정 정렬)."""
    return np.argsort(-Smat, axis=1, kind="stable")[:, :TOPN]


def targets(order, forms):
    return {f: {SECS[c]: 1.0 / TOPN for c in sorted(order[a])} for a, f in enumerate(forms)}


def permute(X, yrows, rng):
    """한 번 뽑기 — 해마다 순열 하나를 모든 열에 함께."""
    Xt = X.copy()
    for rows in yrows:
        Xt[rows] = X[rows[rng.permutation(len(rows))]]
    return Xt


def thash(T):
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def seasec_b(H, forms, S0, J0):
    N = np.empty_like(S0)
    nO = []
    for a, f in enumerate(forms):
        rows = H.o_rows(f, int(J0[a]))
        nO.append(len(rows))
        N[a] = S0[a] - H.X[rows].mean(axis=0)
    return N, nO


def stories(order, forms):
    """P1/P2 — 뽑힘만 센다(수익 없음)."""
    pick = {Q.mshift(f, 1): {SECS[c] for c in order[a]} for a, f in enumerate(forms)}
    yrs = sorted({t[:4] for t in pick if t[5:] == "11"} & {t[:4] for t in pick if t[5:] == "12"})
    nov = sum(1 for y in yrs if "XLY" in pick[y + "-11"])
    dec = sum(1 for y in yrs if "XLY" in pick[y + "-12"])
    both = sum(1 for y in yrs if "XLY" in pick[y + "-11"] and "XLY" in pick[y + "-12"])
    c_so = sum(len(pick[t] & set(DEF)) for t in pick if t[5:] in ("09", "10"))
    c_ja = sum(len(pick[t] & set(DEF)) for t in pick if t[5:] in ("01", "04"))
    return {"P1": {"years": len(yrs), "nov": nov, "dec": dec, "both": both, "pooled": nov + dec, "pass": both * 2 >= len(yrs),
                   "pass_each": nov * 2 >= len(yrs) and dec * 2 >= len(yrs), "pass_pooled": nov + dec >= len(yrs)},
            "P2": {"sep_oct": c_so, "jan_apr": c_ja, "n_sep_oct_months": sum(1 for t in pick if t[5:] in ("09", "10")),
                   "n_jan_apr_months": sum(1 for t in pick if t[5:] in ("01", "04")), "pass": c_so > c_ja}}


def attrib_decision(jA, jB, gates_ok):
    """SEASEC-B 가 «실패» 인가 — 통과 = G1(t_B ≥ t_A) ∧ G2 '양면' ∧ G3–G6(러너 gates_pass) · 실패 = 통과가 아님(INTERP 4·5)."""
    tA, tB = jA.get("t"), jB.get("t")
    g1 = tA is not None and tB is not None and tB >= tA
    g2 = jB["G2"]["label"] == "양면"
    ok = bool(gates_ok)
    return (not (g1 and g2 and ok)), {"g1_tB_ge_tA": bool(g1), "g2_both_sides": bool(g2), "g3_g6_gates_pass": ok}


def seasec_b_attrib(ctx, fr, fr20, B, B20, c1):
    """러너의 A 관문을 SEASEC-B 에 그대로 건다(judge_card · gates_pass — 다시 짜지 않는다). 돌려준다: (실패 불리언, 진단)."""
    import qbatch_run as QR
    V0h = {"hold": [Q.mshift(m, 1) for m in Q.monthly_forms()]}     # 부류 A 판정은 V0 의 보유월만 쓴다
    jA = QR.judge_card("Q11", {"fr": fr, "fr20": fr20, "g4": {}, "f0": {"ok": True}}, ctx, V0h, None, {})
    g4B = {"sleeve_minus_C1_point_gt_0": bool(float(np.mean(np.asarray(B["ex"]) - np.asarray(c1["ex"]))) > 0)}
    jB = QR.judge_card("Q11", {"fr": B, "fr20": B20, "g4": g4B, "f0": {"ok": True}}, ctx, V0h, None, {})
    assert jA["cls"] == "A" and jB["cls"] == "A" and jA["df"] == jB["df"] == len(fr["ex"]) - 1
    fail, parts = attrib_decision(jA, jB, QR.gates_pass(jB))
    g6 = jB["G6"]
    return fail, {"fails": fail, "parts": parts, "t_A": jA["t"], "p_A": jA["p"], "t_B": jB["t"], "p_B": jB["p"],
                  "B_G2": jB["G2"], "B_G3": jB["G3"], "B_G4": g4B, "B_G5": jB["G5"],
                  "B_G6": {"won": g6["won"], "n": g6["n"], "need": g6["need"], "ok": g6["ok"]}}


def shift_rank(stats):
    """stats[k], k = 0..11 — 참 k=0 의 순위(1 = 가장 큼 · 같으면 k 가 작은 쪽이 위)."""
    return 1 + sum(1 for v in stats[1:] if v > stats[0])


def pct_rank(draws, true):
    """q_switch.pct_rank 와 같은 식 — 참값보다 작은 뽑기의 백분율(보고만)."""
    return float(np.mean(np.asarray(draws, float) < true) * 100)


def _check_w(w, n):
    s = sum(w.values())
    assert abs(s - 1.0) < 1e-9, s
    assert len(w) == n and set(w) <= set(SECS) and all(0 < x <= 1 for x in w.values())
    return s


def ew9(m):
    return {s: 1.0 / len(SECS) for s in SECS}


# ── 계약 함수 ─────────────────────────────────────────────────────────────
def dry(ctx) -> dict:
    """랩 자료로 구성만 — 커버리지 · J · O 개수 · 비중 합 · 개수 · PIT · 위약 순열 구조. 수익 · 뽑힘 분포 · 이야기 점검은 찍지 않는다."""
    A = ctx.A
    forms = Q.monthly_forms()
    assert len(forms) == 120 and forms[0] == "2016-08" and forms[-1] == "2026-07"
    for m in forms + [Q.mshift(forms[-1], 1)]:
        i = A.me[m]
        assert A.dates[i][:7] == m and A.dates[i + 1][:7] > m
    H = Hist(A, forms[-1])
    first_ok = H.months[int(np.argmax(H.ok))]
    assert H.ok[H.row[first_ok]:].all()
    R0, J0 = H.index(forms, 0)
    S0 = scores(H.X, R0, J0)
    o0 = top(S0)
    T = targets(o0, forms)
    dev = max(abs(_check_w(T[f], TOPN) - 1) for f in forms)
    ties = int(sum(1 for a in range(len(forms)) if np.sort(S0[a])[::-1][TOPN - 1] == np.sort(S0[a])[::-1][TOPN]))
    _, nO = seasec_b(H, forms, S0, J0)
    Jk = {}
    for k in range(1, NSHIFT + 1):
        _, Jx = H.index(forms, k)
        Jk[k] = [int(Jx.min()), int(Jx.max())]
    yrows = H.year_rows()
    for i in range(2):                                                # 위약 두 번 — 구조만
        Xt = permute(H.X, yrows, np.random.default_rng(Q.SEED + i))
        for rows in yrows:
            a, b = np.sort(H.X[rows], axis=0), np.sort(Xt[rows], axis=0)
            assert np.array_equal(a, b)                                # 해 안 값 묶음은 그대로
            for r in rows:                                             # 행 통째로(모든 섹터 같은 π)
                assert any(np.array_equal(Xt[r], H.X[q]) for q in rows)
        assert np.array_equal(Xt[H.row["2026-01"]:], H.X[H.row["2026-01"]:])
        Tt = targets(top(scores(Xt, R0, J0)), forms)
        assert all(len(Tt[f]) == TOPN for f in forms)
    _check_w(ew9(None), len(SECS))
    return {"n_forms": len(forms), "tickers": list(SECS) + [BASE], "first_x_month": first_ok, "x_rows_complete_after_first": True,
            "J_primary": [int(J0.min()), int(J0.max())], "J_first_last": [int(J0[0]), int(J0[-1])],
            "O_count": [min(nO), max(nO)], "J_shift": Jk, "names_per_form": TOPN, "w_sum_max_dev": dev,
            "ties_at_cut": ties, "perm_years": [PY0, PY1], "perm_labels_2006": int(len(yrows[0])),
            "perm_labels_other": sorted({int(len(r)) for r in yrows[1:]}), "pit_asserts": "ok (x 행 ≤ f · me ≤ me[f])",
            "placebo_structure": "ok (2 draws: 해 안 묶음 보존 · 행 통째 · 2026 행 고정)"}


def run(ctx) -> dict:
    A = ctx.A
    forms = Q.monthly_forms()
    H = Hist(A, forms[-1])
    R0, J0 = H.index(forms, 0)
    S0 = scores(H.X, R0, J0)
    o0 = top(S0)
    T = targets(o0, forms)
    dec = lambda TT: (lambda m: dict(TT[m]))
    fr = ctx.etf_fr(dec(T), forms, "TR", Q.COST)
    fr_pr = ctx.etf_fr(dec(T), forms, "PR", Q.COST)
    fr20 = ctx.etf_fr(dec(T), forms, "TR", COST20)
    c1 = ctx.etf_fr(ew9, forms, "TR", Q.COST)
    N, nO = seasec_b(H, forms, S0, J0)
    TB = targets(top(N), forms)
    arms = {"SEASEC-B": ctx.etf_fr(dec(TB), forms, "TR", Q.COST),
            "SEASEC-B@20bp": ctx.etf_fr(dec(TB), forms, "TR", COST20)}          # 러너가 B 에 A 와 같은 관문(G5 20bp 포함)을 걸 수 있게
    shash, Jk = {}, {}
    for k in range(1, NSHIFT + 1):
        Rk, Jx = H.index(forms, k)
        Tk = targets(top(scores(H.X, Rk, Jx)), forms)
        arms["SHIFT+%d" % k] = ctx.etf_fr(dec(Tk), forms, "TR", Q.COST)
        shash[k], Jk[k] = thash(Tk), [int(Jx.min()), int(Jx.max())]
    c1x = np.asarray(c1["ex"])
    yrows = H.year_rows()
    draws = []
    for i in range(NPERM):
        Xt = permute(H.X, yrows, np.random.default_rng(Q.SEED + i))
        Tt = targets(top(scores(Xt, R0, J0)), forms)
        draws.append(float(np.mean(np.asarray(ctx.etf_fr(dec(Tt), forms, "TR", Q.COST)["ex"]) - c1x)))
    true = float(np.mean(np.asarray(fr["ex"]) - c1x))
    p95 = float(np.percentile(draws, PCT))
    freq = {s: int(sum(1 for f in forms if s in T[f])) for s in SECS}
    b_fail, b_log = seasec_b_attrib(ctx, fr, fr20, arms["SEASEC-B"], arms["SEASEC-B@20bp"], c1)
    sk = [true] + [float(np.mean(np.asarray(arms["SHIFT+%d" % k]["ex"]) - c1x)) for k in range(1, NSHIFT + 1)]
    res = {"code": "Q11", "cls": "A", "slot": "A4",
           "fr": fr, "fr_pr": fr_pr, "fr20": fr20,
           "controls": {"C1": c1},
           "arms": arms,
           "placebo": {"month_label_joint": {"stat": "전 월 평균(X_A − X_C1)(펀드 TR · 10bp · %/월) — 해마다 달 이름 순열 하나를 9 섹터 x 이력에 함께 · 보유 수익은 참",
                                             "draws": draws, "true": true}},
           "g4": {"sleeve_minus_C1_point_gt_0": bool(true > 0), "month_label_placebo_ge_p95": bool(true >= p95)},
           "label_caps": {"seasec_b_attrib": bool(b_fail)},
           "f0": {"ok": bool(J0.min() >= JMIN), "why": "같은 달 관측 J 최소 %d(≥ %d 필요 · 카드 '묶이지 않는다')" % (int(J0.min()), JMIN)},
           "targets_hash": thash(T),
           "log": {"interpretation": INTERP, "J": [int(J0.min()), int(J0.max())], "O_count": [min(nO), max(nO)], "J_shift": Jk,
                   "stories": stories(o0, forms), "pick_freq": freq,
                   "turn": {"rule": fr.get("turn"), "rule20": fr20.get("turn"), "C1": c1.get("turn")},
                   "placebo_p95": p95, "placebo_pct_rank": pct_rank(draws, true), "nperm": NPERM, "seed": Q.SEED,
                   "label_rule": "A 가 통과하고 SEASEC-B 가 실패하면 A 의 이름은 '%s' · 측정만 상한 — B 실패 = INTERP 4·5 의 규칙" % LABEL_IF_CAPPED,
                   "label_if_capped": LABEL_IF_CAPPED, "seasec_b": b_log,
                   "sleeve_minus_C1_basket": float(np.mean(np.asarray(fr["basket"]) - np.asarray(c1["basket"]))),
                   "shift_rank": {"stat": "전 월 평균(X_k − X_C1) · k = 0..11 · 1 = 가장 큼", "k0_rank": shift_rank(sk), "n": len(sk), "values": sk},
                   "hashseed": os.environ.get("PYTHONHASHSEED"),
                   "gics_breaks": ["2016-09", "2018-09", "2023-03"],
                   "arm_hashes": dict({"SEASEC-B": thash(TB)}, **{"SHIFT+%d" % k: h for k, h in shash.items()}),
                   "per_formation": {f: {"J": int(J0[a]), "pick": sorted(T[f])} for a, f in enumerate(forms)}}}
    return {"Q11": res}


# ── 단위 시험(합성 자료만) ─────────────────────────────────────────────────
def _fake_assets(monthly, rf=0.001, nd=20, y0=2006, y1=2026, m1=9):
    """합성 격자 — monthly = {티커: {달: 월 수익}} 를 달 안에서 기하 균등으로 펼친 가격. qbatch_core.Assets 의 메서드를 그대로 쓴다."""
    months = Q.months_between("%04d-01" % y0, "%04d-%02d" % (y1, m1))
    dates = ["%s-%02d" % (m, d + 1) for m in months for d in range(nd)]
    A = object.__new__(Q.Assets)
    A.dates = dates
    A.di = {d: i for i, d in enumerate(dates)}
    A.me = {m: (j + 1) * nd - 1 for j, m in enumerate(months)}
    A.RF = {m: rf for m in months}
    A.px = {}
    for tk, mm in monthly.items():
        p, v = [], 100.0
        for j, m in enumerate(months):
            g = (1 + (mm.get(m, 0.0) if j > 0 else 0.0)) ** (1.0 / nd)
            for d in range(nd):
                if j > 0:
                    v *= g
                p.append(v)
        A.px[tk] = np.array(p)
    A.IX_TR = A.px[BASE].copy()
    A.IX_PR = A.px[BASE].copy()
    A.macro = {}
    return A, months


def selftest() -> dict:
    tests = {}
    rng = np.random.default_rng(11)
    months = Q.months_between("2006-01", "2026-09")
    spy = {m: float(rng.normal(0.007, 0.04)) for m in months}
    ret = {BASE: spy}
    for s in SECS:
        ret[s] = {m: spy[m] + float(rng.normal(0, 0.001)) for m in months}
    for m in months:                                                  # 계획: XLY 11·12월 +2% · XLP 9월 +1% · XLE 3월 +1.5%
        if m[5:] in ("11", "12"):
            ret["XLY"][m] += 0.02
        if m[5:] == "09":
            ret["XLP"][m] += 0.01
        if m[5:] == "03":
            ret["XLE"][m] += 0.015
    A, _ = _fake_assets(ret)
    forms = Q.monthly_forms()
    H = Hist(A, forms[-1])
    tests["x_first_row_nan_only_2006_01"] = (not H.ok[0]) and bool(H.ok[1:].all())
    R0, J0 = H.index(forms, 0)
    tests["J_first_10_last_20"] = int(J0[0]) == 10 and int(J0[-1]) == 20 and int(J0.min()) >= 10
    tests["J_january_one_less"] = int(J0[forms.index("2025-12")]) == 19
    S0 = scores(H.X, R0, J0)
    a = forms.index("2020-10")                                        # 목표 11월 → XLY 1위
    tests["planted_nov_XLY"] = SECS[int(np.argmax(S0[a]))] == "XLY"
    a = forms.index("2020-08")                                        # 목표 9월 → XLP 1위
    tests["planted_sep_XLP"] = SECS[int(np.argmax(S0[a]))] == "XLP"
    a = forms.index("2021-02")                                        # 목표 3월 → XLE 1위
    tests["planted_mar_XLE"] = SECS[int(np.argmax(S0[a]))] == "XLE"
    # 직접 평균과 같다
    f = "2019-06"; t = Q.mshift(f, 1)
    br = [np.mean([A.monthly(s, Q.mshift(t, -12 * j)) - A.monthly(BASE, Q.mshift(t, -12 * j)) for j in range(1, 14)]) for s in SECS]
    tests["S_bruteforce"] = np.allclose(S0[forms.index(f)], br, atol=1e-14) and int(J0[forms.index(f)]) == 13
    # 동점은 알파벳
    tie = np.array([[0.0, 1.0, 1.0, 0.5, 1.0, 0.0, 0.0, 0.0, 1.0]])
    tests["ties_alphabetical"] = [SECS[c] for c in top(tie)[0]] == ["XLE", "XLF", "XLK"]
    Tn = targets(top(S0), forms)
    tests["weights_three_thirds"] = all(abs(sum(Tn[f].values()) - 1) < 1e-15 and len(Tn[f]) == 3 for f in forms)
    # SEASEC-B O 직접 계산
    N, nO = seasec_b(H, forms, S0, J0)
    a = forms.index(f)
    Ob = [np.mean([A.monthly(s, Q.mshift(t, -k)) - A.monthly(BASE, Q.mshift(t, -k)) for k in range(13, 12 * 13 + 1) if k % 12]) for s in SECS]
    tests["seasec_b_bruteforce"] = np.allclose(N[a], S0[a] - np.array(Ob), atol=1e-14) and nO[a] == 12 * 11
    # 달력 이동 k: 편입 f 의 S_k = 편입 f+k 의 S_0(같은 J 일 때)
    ok = True
    for k in (1, 5, 11):
        Rk, Jk = H.index(forms, k)
        Sk = scores(H.X, Rk, Jk)
        for a, f2 in enumerate(forms[:-k]):
            b = forms.index(Q.mshift(f2, k))
            if Jk[a] == J0[b]:
                ok = ok and np.allclose(Sk[a], S0[b], atol=1e-15)
    tests["shift_equals_future_label"] = bool(ok)
    # 앞보기 막기 — f 뒤 가격을 바꿔도 S · N · 이동 S 가 같다
    A2, _ = _fake_assets(ret)
    f = "2021-05"
    for tk in A2.px:
        A2.px[tk][A2.me[f] + 1:] *= np.linspace(1, 2, len(A2.px[tk]) - A2.me[f] - 1)
    H2 = Hist(A2, forms[-1])
    ff = forms[:forms.index(f) + 1]
    Ra, Ja = H.index(ff, 0); Rb, Jb = H2.index(ff, 0)
    Sa, Sb = scores(H.X, Ra, Ja), scores(H2.X, Rb, Jb)
    Na, _ = seasec_b(H, ff, Sa, Ja); Nb, _ = seasec_b(H2, ff, Sb, Jb)
    Rc, Jc = H.index(ff, 11); Rd, Jd = H2.index(ff, 11)
    tests["no_lookahead"] = (np.array_equal(Sa, Sb) and np.array_equal(Na, Nb)
                             and np.array_equal(scores(H.X, Rc, Jc), scores(H2.X, Rd, Jd))
                             and not np.array_equal(H.X[H.row[f] + 1:], H2.X[H.row[f] + 1:]))    # 뒤는 실제로 바뀌었다
    # 위약 순열 구조
    yrows = H.year_rows()
    X1 = permute(H.X, yrows, np.random.default_rng(Q.SEED))
    X1b = permute(H.X, yrows, np.random.default_rng(Q.SEED))
    X2 = permute(H.X, yrows, np.random.default_rng(Q.SEED + 1))
    tests["perm_2006_11_labels"] = len(yrows[0]) == 11 and all(len(r) == 12 for r in yrows[1:]) and len(yrows) == 20
    tests["perm_within_year_multiset"] = all(np.array_equal(np.sort(H.X[r], 0), np.sort(X1[r], 0)) for r in yrows)
    tests["perm_joint_rows"] = all(any(np.array_equal(X1[r], H.X[q]) for q in rows) for rows in yrows for r in rows)
    tests["perm_reproducible"] = np.array_equal(X1, X1b, equal_nan=True) and not np.array_equal(X1, X2, equal_nan=True)
    tests["perm_2026_fixed"] = np.array_equal(X1[H.row["2026-01"]:], H.X[H.row["2026-01"]:])
    st = stories(top(S0), forms)
    tests["story_P1_planted"] = st["P1"]["pass"] and st["P1"]["years"] == 10
    tests["story_P2_counts"] = st["P2"]["n_sep_oct_months"] == 20 and st["P2"]["n_jan_apr_months"] == 20
    tests["story_P1_alt_readings"] = (st["P1"]["pass_each"] == (st["P1"]["nov"] >= 5 and st["P1"]["dec"] >= 5)
                                      and st["P1"]["pass_pooled"] == (st["P1"]["nov"] + st["P1"]["dec"] >= 10))
    tests["hash_stable"] = thash({"b": {"x": 1.0}, "a": {"y": 0.5}}) == thash({"a": {"y": 0.5}, "b": {"x": 1.0}})
    # SEASEC-B 귀속 판정표 — 통과는 셋 다 참일 때만
    jA = {"t": 2.5}
    jb = lambda t, lab: {"t": t, "G2": {"label": lab}}
    tests["attrib_pass_all"] = attrib_decision(jA, jb(2.5, "양면"), True)[0] is False
    tests["attrib_fail_weaker_t"] = attrib_decision(jA, jb(2.49, "양면"), True)[0] is True
    tests["attrib_fail_one_sided"] = attrib_decision(jA, jb(3.0, "급락형"), True)[0] is True
    tests["attrib_fail_gates"] = attrib_decision(jA, jb(3.0, "양면"), False)[0] is True
    tests["attrib_fail_t_none"] = attrib_decision(jA, jb(None, "양면"), True)[0] is True and attrib_decision({"t": None}, jb(3.0, "양면"), True)[0] is True
    tests["shift_rank"] = shift_rank([0.2] + [0.1] * 11) == 1 and shift_rank([0.0, 0.1, 0.2] + [-1] * 9) == 3 and shift_rank([0.1] * 12) == 1
    tests["pct_rank"] = pct_rank(list(range(100)), 95) == 95.0 and pct_rank([1, 2, 3], 1) == 0.0
    # 끝까지 — 합성 ctx 로 run(수익은 합성 · 모양만)
    global NPERM
    old = NPERM
    NPERM = 3
    try:
        ctx = Q.Ctx()
        ctx._A = A
        out = run(ctx)["Q11"]
        tests["run_synthetic_shape"] = (len(out["placebo"]["month_label_joint"]["draws"]) == 3 and len(out["arms"]) == 13
                                        and len(out["fr"]["ex"]) == 120 and isinstance(out["g4"]["month_label_placebo_ge_p95"], bool)
                                        and out["fr"]["hold"][0] == "2016-09" and out["fr"]["hold"][-1] == "2026-08")
        lg = out["log"]
        tests["run_label_caps_all_bool"] = (set(out["label_caps"]) == {"seasec_b_attrib"}
                                            and all(type(v) is bool for v in out["label_caps"].values()))
        tests["run_attrib_consistent"] = (out["label_caps"]["seasec_b_attrib"] == lg["seasec_b"]["fails"]
                                          and lg["seasec_b"]["fails"] == (not all(lg["seasec_b"]["parts"].values()))
                                          and lg["label_if_capped"] == LABEL_IF_CAPPED)
        tests["run_shift_rank_12"] = lg["shift_rank"]["n"] == 12 and 1 <= lg["shift_rank"]["k0_rank"] <= 12
        try:
            json.dumps(out["log"], ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
            tests["run_log_json"] = True
        except Exception:
            tests["run_log_json"] = False
    finally:
        NPERM = old
    return {"ok": all(bool(v) for v in tests.values()), "tests": tests}


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0 if r["ok"] else 1)
    if "--dry" in sys.argv:
        print(json.dumps(dry(Q.Ctx()), ensure_ascii=False, indent=1))
        sys.exit(0)
    print(__doc__)
