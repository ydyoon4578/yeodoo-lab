# -*- coding: utf-8 -*-
"""build/r_p0_test.py — r_p0.py(배치 R P0 자격 계산기)·r_p0_adapt.py 단위 시험. **합성 자료만** 쓴다.

무엇을 본다.
  ① 닫힌 꼴 — π = 1 − Φ(2.27 − t_alt) 를 scipy 없이 erfc 로 다시 풀어 맞추고, 카드 문구의 수치
     (σ* 1.58 · 2.30 · 1.32 · 1.93 · P0 0.245 · 0.118 · 0.37 · 0.23 · 0.14 · π* 0.356 · t_alt* 1.90)를 재현한다.
     t_alt = 2.27 이면 π = ½ · σ → ∞ 이면 π → 1 − Φ(2.27) · 역함수 p0(σ*) = 0.15 · 비중심 t 정확값·몬테카를로와의 거리.
  ② Holm 임계 — T=120 에서 m=2: 2.27 → 1.98 · m=1: 1.98.
  ③ lrv_nw 가 eg30plus.nw_t 의 분산과 같다(랩 판정 통계를 복제하지 않았는지).
  ④ FWL 계수 = 전체 OLS 계수(동반 더미 있을 때·없을 때).
  ⑤ 위약 생성기 — 칸별 개수 정확 · 칸 안 균등 · 씨앗 결정성 · 인자에 플래그 자리가 없다.
  ⑥ σ — 칸 구조가 없으면 위약 SD 중앙 ≈ 분석적 σ · 선형 통제로 안 잡히는 칸 충격이 있으면 위약 > 분석적.
  ⑦ 방화벽 — run 뒤 flag_sets 는 멈춘다 · 이름 목록·비정수 개수 표는 거부 · 세계 지문이 다르면 멈춘다 · 덮어쓰기 출처는
     --allow-override 없이 거부 · 표지 키가 세계 키와 어긋나면(몫 < 0.30) 멈춘다.
  ⑧ 자격·Holm m 결정(외부 F0 모름 · 카드 자료 없음 · 달 관문 없음 → m 미정 · 같은 가족 둘 → 멈춤).
  ⑨ 어댑터 — 발행사 지도 점/대시 표기 · 내부자 집계 세 배치 · 10-Q 전년도 하위 20% + t−2..t 창 · 덮어쓰기 우선 ·
     원천이 정의한 달(months_ok · 공개월 범위).
  ⑩ 창 끝·경계 세계 — cikmonth months_ok 가 끝 신호월 앞에서 끝나면 그 달은 0 이 아니라 «정의 안 됨»(기본 멈춤 · 빼기로 정하면
     T 에서 빠지고 문서에 남는다) · R2 경계 세계가 2015-01 부터면 2016 달에 경계가 있고, 짧으면 카운트 단계가 멈춘다
     (짧은 세계의 덮지 않은 달은 r_r2flags ⑦ 가 in_world · uncovered_all 로 메우고 출처를 적는다 — 러너 r2_bounds_check 가 거절).
  ⑪ 끝에서 끝까지 — 문서 모양 · 위약 평균 없음 · 같은 입력이면 result_sha 같음 · JT 카드 σ_placebo 는 시차별 한 회귀 기준.

  python build/r_p0_test.py        (약 10~25초 · 대부분 scipy import)
"""
from __future__ import annotations
import inspect, io, json, math, os, shutil, sys, tempfile, unittest

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")   # unittest 는 stderr 로 찍는다
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r_p0 as R          # noqa: E402
import r_p0_adapt as AD   # noqa: E402


def _phi_sf(x):
    """1 − Φ(x) — scipy 를 쓰지 않는 닫힌 꼴(erfc)."""
    return 0.5 * math.erfc(x / math.sqrt(2.0))


_SMALL = {}


def small_panel(**kw):
    key = tuple(sorted(kw.items()))
    if key not in _SMALL:
        base = dict(seed=5, n_names=240, months=R.QC.months_between(R.QC.mshift(R.SIG0, -14), R.QC.mshift(R.SIG0, 71)))
        base.update(kw)
        _SMALL[key] = R.synth_panel(**base)
    return _SMALL[key]


def reg_months(P):
    return [m for m in P.months if R.SIG0 <= m <= R.SIG1 and int(P.xs[m].row.sum()) >= 40]


class ClosedForm(unittest.TestCase):
    def test_pi_matches_erfc(self):
        for g, T, s in [(-0.55, 120, 1.2), (-0.8, 84, 2.0), (-0.55, 60, 0.7), (0.3, 120, 3.0)]:
            ta = 0.5 * abs(g) * math.sqrt(T) / s
            self.assertAlmostEqual(R.power_pi(g, T, s), _phi_sf(2.27 - ta), places=12)
            self.assertAlmostEqual(R.p0(g, T, s), 0.4 * _phi_sf(2.27 - ta) + 0.6 * 0.0125, places=12)

    def test_half_at_crit_and_limit(self):
        g, T = -0.55, 120
        s_half = 0.5 * 0.55 * math.sqrt(T) / 2.27            # t_alt = 2.27 → π = ½
        self.assertAlmostEqual(R.power_pi(g, T, s_half), 0.5, places=12)
        self.assertAlmostEqual(R.power_pi(g, T, 1e9), _phi_sf(2.27), places=9)   # σ → ∞
        self.assertAlmostEqual(R.p0(g, T, 1e9), 0.4 * _phi_sf(2.27) + 0.0075, places=9)
        self.assertEqual(R.power_pi(-0.55, T, 1.3), R.power_pi(0.55, T, 1.3))      # 크기만 쓴다
        ps = [R.power_pi(g, T, s) for s in (0.8, 1.2, 1.6, 2.0)]
        self.assertTrue(all(a > b for a, b in zip(ps, ps[1:])))                      # σ 에 감소
        self.assertLess(R.power_pi(g, 84, 1.3), R.power_pi(g, 120, 1.3))              # T 에 증가

    def test_gate_equivalences(self):
        self.assertAlmostEqual(R.pi_needed(), (0.15 - 0.6 * 0.0125) / 0.4, places=15)
        self.assertAlmostEqual(round(R.pi_needed(), 3), 0.356, places=12)            # 카드 문구 «π ≥ 0.356»
        self.assertAlmostEqual(round(R.t_alt_needed(), 2), 1.90, places=12)           # «t_alt ≥ 1.90»
        self.assertAlmostEqual(_phi_sf(2.27 - R.t_alt_needed()), R.pi_needed(), places=10)
        for g in (-0.55, -0.80):
            for T in (84, 120):
                self.assertAlmostEqual(R.p0(g, T, R.sigma_max(g, T)), 0.15, places=10)  # 역함수
                self.assertGreater(R.p0(g, T, R.sigma_max(g, T) * 0.999), 0.15)
                self.assertLess(R.p0(g, T, R.sigma_max(g, T) * 1.001), 0.15)

    def test_card_numbers(self):
        """batch_design_changes 1 · R1/R2 why 의 수치(반올림 자리까지)."""
        self.assertLess(abs(R.sigma_max(-0.55, 120) - 1.58), 0.01)
        self.assertLess(abs(R.sigma_max(-0.80, 120) - 2.30), 0.01)
        self.assertLess(abs(R.sigma_max(-0.55, 84) - 1.32), 0.01)   # 식 값 1.3255(문구는 1.32 로 잘랐다)
        self.assertLess(abs(R.sigma_max(-0.80, 84) - 1.93), 0.01)
        self.assertAlmostEqual(round(R.p0(-0.55, 120, 1.2), 3), 0.245)
        self.assertAlmostEqual(round(R.p0(-0.55, 120, 1.8), 3), 0.118)
        self.assertAlmostEqual(round(R.p0(-0.80, 120, 1.2), 2), 0.37)
        self.assertAlmostEqual(round(R.p0(-0.80, 120, 1.8), 2), 0.23)
        self.assertAlmostEqual(round(R.p0(-0.80, 120, 2.4), 2), 0.14)

    def test_nct_and_monte_carlo(self):
        """정규 근사 π 와 정확값(비중심 t)·몬테카를로의 거리 — iid 정규 γ_t, T=120."""
        g, T, s = -0.55, 120, 1.4
        pi, pn = R.power_pi(g, T, s), R.power_pi_nct(g, T, s)
        self.assertLess(abs(pi - pn), 0.01)
        rng = np.random.default_rng(1)
        n = 40000
        X = rng.normal(0.5 * g, s, size=(n, T))
        t = X.mean(1) / (X.std(1, ddof=1) / math.sqrt(T))
        mc = float((t <= -2.27).mean())
        se = math.sqrt(pn * (1 - pn) / n)
        self.assertLess(abs(mc - pn), 4 * se)
        self.assertLess(abs(mc - pi), 0.015)
        for s2 in (1.0, 1.8, 2.6):
            self.assertLess(abs(R.power_pi(-0.8, 120, s2) - R.power_pi_nct(-0.8, 120, s2)), 0.01)

    def test_holm(self):
        self.assertEqual([round(x, 2) for x in R.holm_crit(2, 120)], [2.27, 1.98])
        self.assertEqual([round(x, 2) for x in R.holm_crit(1, 120)], [1.98])
        self.assertEqual(R.holm_crit(0, 120), [])
        self.assertAlmostEqual(R.holm_crit(2, 120)[0], R.T_CRIT, places=2)            # 식의 상수 2.27 과 같은 칸

    def test_lrv_matches_nw_t(self):
        import eg30plus as E
        rng = np.random.default_rng(3)
        for n in (30, 120):
            x = rng.normal(0.1, 1.0, n) + 0.3 * np.sin(np.arange(n))
            self.assertAlmostEqual(x.mean() / math.sqrt(R.lrv_nw(x) / n), E.nw_t(x), places=10)

    def test_constants_match_lab(self):
        import qbatch_core as QC
        self.assertEqual((R.SEED, R.SIG0, R.SIG1), (QC.SEED, "2016-08", "2026-07"))
        self.assertEqual(len(QC.months_between(R.SIG0, R.SIG1)), 120)


class Regression(unittest.TestCase):
    def test_fwl_equals_full_ols(self):
        rng = np.random.default_rng(9)
        n, B = 300, 5
        Z = np.column_stack([np.ones(n), rng.normal(size=(n, 4)), (rng.random(n) < 0.3).astype(float)])
        D = (rng.random((n, B)) < 0.1).astype(float)
        C = (rng.random((n, B)) < 0.05).astype(float)
        y = rng.normal(size=n) + Z @ rng.normal(size=Z.shape[1])
        Q, _ = R.basis(Z)
        yt = R.resid(Q, y)
        g1 = R.fwl_gamma(yt, R.resid(Q, D))
        g2 = R.fwl_gamma(yt, R.resid(Q, D), R.resid(Q, C))
        for b in range(B):
            b1 = np.linalg.lstsq(np.column_stack([D[:, b], Z]), y, rcond=None)[0][0]
            b2 = np.linalg.lstsq(np.column_stack([D[:, b], C[:, b], Z]), y, rcond=None)[0][0]
            self.assertAlmostEqual(g1[b], b1, places=9)
            self.assertAlmostEqual(g2[b], b2, places=9)

    def test_rank_deficient_controls(self):
        rng = np.random.default_rng(2)
        n = 100
        a = rng.normal(size=n)
        Z = np.column_stack([np.ones(n), a, 2 * a, np.zeros(n)])              # 겹친 열 · 빈 열
        Q, r = R.basis(Z)
        self.assertEqual(r, 2)
        d = np.zeros((n, 1))
        self.assertTrue(np.isnan(R.fwl_gamma(R.resid(Q, rng.normal(size=n)), R.resid(Q, d))[0]))   # 분산 0 → NaN

    def test_companion_degenerate_falls_back(self):
        """동반 더미가 분산 0(개수 0 · 모든 이름) 이거나 첫 더미와 같으면 버리고 첫 더미만으로 푼다(r_stagem._solve 와 같은 처리)."""
        rng = np.random.default_rng(12)
        n = 200
        Z = np.column_stack([np.ones(n), rng.normal(size=n)])
        Q, _ = R.basis(Z)
        y = R.resid(Q, rng.normal(size=n))
        D = (rng.random((n, 3)) < 0.2).astype(float)
        C = np.column_stack([np.zeros(n), np.ones(n), D[:, 2]])           # 0 개 · 전부 · 첫 더미와 같음
        g1 = R.fwl_gamma(y, R.resid(Q, D))
        g2 = R.fwl_gamma(y, R.resid(Q, D), R.resid(Q, C))
        self.assertFalse(np.isnan(g2).any())
        np.testing.assert_allclose(g2, g1, rtol=1e-9, atol=1e-12)


class Placebo(unittest.TestCase):
    def setUp(self):
        self.P = small_panel()
        self.C = R.synth_counts_doc(self.P, seed=4)

    def test_signature_has_no_flag_slot(self):
        ps = list(inspect.signature(R.placebo_draws).parameters)
        self.assertEqual(ps, ["panel", "counts", "months", "dummies", "B", "seed"])

    def test_counts_exact_and_deterministic(self):
        P = self.P
        cnt = self.C["cards"]["R1-OPPSELL"]
        cnt = {d: v["months"] for d, v in cnt.items()}
        ms = P.months[20:26]
        A, short = R.placebo_draws(P, cnt, ms, ["OS", "RS"], B=7, seed=100)
        A2, _ = R.placebo_draws(P, cnt, ms, ["OS", "RS"], B=7, seed=100)
        A3, _ = R.placebo_draws(P, cnt, ms, ["OS", "RS"], B=7, seed=101)
        self.assertEqual(short, 0)
        diff = False
        for d in ("OS", "RS"):
            for s in ms:
                cs = P.xs[s]
                self.assertTrue(np.array_equal(A[d][s], A2[d][s]))
                diff |= not np.array_equal(A[d][s], A3[d][s])
                want = cnt[d].get(s) or {}
                for b in range(7):
                    got = np.bincount(cs.cell[A[d][s][b]], minlength=len(P.cell_labels))
                    for j, lab in enumerate(P.cell_labels):
                        self.assertEqual(int(got[j]), int(want.get(lab, 0)))
        self.assertTrue(diff)
        # 회 b 는 default_rng(seed + b) 하나 — 회 1 만 따로 뽑아도 같다(회 사이 독립 · 랩 규약)
        B1, _ = R.placebo_draws(P, cnt, ms, ["OS", "RS"], B=1, seed=101)
        self.assertTrue(np.array_equal(B1["OS"][ms[0]][0], A["OS"][ms[0]][1]))

    def test_uniform_within_cell(self):
        P = self.P
        s = P.months[30]
        cs = P.xs[s]
        j = int(np.bincount(cs.cell).argmax())
        lab = P.cell_labels[j]
        members = np.where(cs.cell == j)[0]
        k = max(1, len(members) // 4)
        cnt = {"OS": {s: {lab: k}}}
        B = 3000
        A, _ = R.placebo_draws(P, cnt, [s], ["OS"], B=B, seed=7)
        f = A["OS"][s][:, members].mean(0)
        p = k / len(members)
        self.assertLess(np.abs(f - p).max(), 5 * math.sqrt(p * (1 - p) / B))
        self.assertEqual(int(A["OS"][s][:, np.setdiff1d(np.arange(cs.n), members)].sum()), 0)

    def test_capping(self):
        P = self.P
        s = P.months[30]
        cs = P.xs[s]
        lab = P.cell_labels[int(cs.cell[0])]
        size = int((cs.cell == cs.cell[0]).sum())
        A, short = R.placebo_draws(P, {"OS": {s: {lab: size + 5}}}, [s], ["OS"], B=2, seed=1)
        self.assertEqual(short, 5)
        self.assertEqual(int(A["OS"][s][0].sum()), size)

    def test_unknown_cell_rejected(self):
        with self.assertRaises(SystemExit):
            R.placebo_draws(self.P, {"OS": {self.P.months[0]: {"없는칸|9": 1}}}, [self.P.months[0]], ["OS"], B=1)


class Sigma(unittest.TestCase):
    def test_placebo_matches_analytic_without_cell_structure(self):
        P = small_panel(churn=0.0, cell_shock=0.0)
        C = R.synth_counts_doc(P, seed=8)
        cnt = {"CH": C["cards"]["R2-LAZYRF"]["CH"]["months"]}
        card = {"target": "CH", "companions": [], "lags": [0]}
        ms = reg_months(P)
        sa, _ = R.sigma_analytic(P, cnt["CH"], ms)
        G, _, _ = R.placebo_gamma(P, cnt, card, ms, B=60, seed=R.SEED)
        med = R.placebo_sigma(G)["sd_quantiles"]["p50"]
        self.assertLess(abs(med / sa - 1.0), 0.08, (med, sa))

    def test_cell_shock_raises_placebo(self):
        P = small_panel(churn=0.0, cell_shock=20.0, shock_cell=("S0", 2), n_sec=4)      # 칸이 넉넉하게(씨앗 5~9 에서 비 1.46~1.80)
        C = R.synth_counts_doc(P, seed=8, bias_cell="S0|2", bias=5.0)
        cnt = {"CH": C["cards"]["R2-LAZYRF"]["CH"]["months"]}
        card = {"target": "CH", "companions": [], "lags": [0]}
        ms = reg_months(P)
        sa, _ = R.sigma_analytic(P, cnt["CH"], ms)
        G, _, _ = R.placebo_gamma(P, cnt, card, ms, B=60, seed=R.SEED)
        med = R.placebo_sigma(G)["sd_quantiles"]["p50"]
        self.assertGreater(med, 1.25 * sa, (med, sa))

    def test_jt_average_shrinks(self):
        """R1 JT(k=0..2) — 달마다 독립 위약이면 평균의 SD 가 한 회귀보다 작다(약 1/√3) · 그래서 σ_placebo 는 한 회귀 기준으로 잰다."""
        P = small_panel(churn=0.0)
        C = R.synth_counts_doc(P, seed=8)
        cnt = {d: C["cards"]["R1-OPPSELL"][d]["months"] for d in ("OS", "RS")}
        ms = reg_months(P)
        G, _, Gk = R.placebo_gamma(P, cnt, R.CARDS["R1-OPPSELL"], ms, B=40)
        jt = R.placebo_sigma(G)["sd_quantiles"]["p50"]
        one = R.placebo_sigma(Gk[0])["sd_quantiles"]["p50"]
        pooled = R.placebo_sigma([Gk[k] for k in (0, 1, 2)])["sd_quantiles"]["p50"]
        self.assertLess(jt, 0.75 * one)
        self.assertLess(abs(pooled / one - 1.0), 0.15)
        for k in (0, 1, 2):                                                    # JT 는 세 시차가 다 있을 때만
            self.assertTrue(np.all(np.isnan(G) >= np.isnan(Gk[k])))

    def test_card_uses_single_regression_basis(self):
        P = small_panel()
        C = R.synth_counts_doc(P, seed=21)
        cnt = {d: C["cards"]["R1-OPPSELL"][d]["months"] for d in ("OS", "RS")}
        ms = reg_months(P)
        r = R.eval_card(P, "R1-OPPSELL", R.CARDS["R1-OPPSELL"], cnt, ms, B=30)
        G, _, Gk = R.placebo_gamma(P, cnt, R.CARDS["R1-OPPSELL"], ms, B=30)
        self.assertAlmostEqual(r["sigma_placebo"], round(R.placebo_sigma([Gk[k] for k in (0, 1, 2)])["sigma_placebo"], 6), places=9)
        self.assertLess(r["placebo"]["diag_jt_sd_p90"], r["sigma_placebo"])
        self.assertIn("시차별", r["sigma_placebo_basis"])
        self.assertEqual(len(r["analytic_by_month"]), 3 * len(ms))                # (t, k) 마다 한 항

    def test_nan_placebo_sigma_stops(self):
        P = small_panel()
        C = R.synth_counts_doc(P, seed=21)
        cnt = {d: C["cards"]["R2-LAZYRF"][d]["months"] for d in ("CH", "CH_MISS")}
        with self.assertRaises(SystemExit):
            R.eval_card(P, "R2-LAZYRF", R.CARDS["R2-LAZYRF"], cnt, reg_months(P)[:1], B=5)


class Firewall(unittest.TestCase):
    def tearDown(self):
        AD.GUARD["run"] = False

    def test_guard_after_run(self):
        P = small_panel()
        C = R.synth_counts_doc(P)
        R.run(P, C, B=5)
        with self.assertRaises(RuntimeError):
            AD.flag_sets("R1-OPPSELL", "OS")

    def test_validate_counts(self):
        P = small_panel()
        C = R.synth_counts_doc(P)
        self.assertTrue(R.validate_counts(C))
        bad = json.loads(json.dumps(C))
        m = next(iter(bad["cards"]["R1-OPPSELL"]["OS"]["months"]))
        bad["cards"]["R1-OPPSELL"]["OS"]["months"][m] = ["g1", "g2"]             # 이름 목록
        with self.assertRaises(SystemExit):
            R.validate_counts(bad)
        bad2 = json.loads(json.dumps(C))
        byc = bad2["cards"]["R1-OPPSELL"]["OS"]["months"][m]
        byc[next(iter(byc))] = 1.5
        with self.assertRaises(SystemExit):
            R.validate_counts(bad2)

    def test_universe_drift(self):
        P = small_panel()
        C = R.synth_counts_doc(P)
        C["universe"]["hash"] = "0" * 64
        with self.assertRaises(SystemExit):
            R.run(P, C, B=3)

    def test_counts_step_refuses_returns(self):
        with self.assertRaises(SystemExit):
            R.build_counts(small_panel())


class Decide(unittest.TestCase):
    def _cards(self, p1=0.2, p2=0.3):
        mk = lambda p: {"p0": p, "p0_pass": p >= 0.15, "T_pass": True, "density_pass": True, "T": 120}
        return {"R1-OPPSELL": mk(p1), "R2-LAZYRF": mk(p2)}

    def _ext(self, v1=True, v2=True):
        return {"R1-OPPSELL": {k: v1 for k in R.CARDS["R1-OPPSELL"]["external_f0"]},
                "R2-LAZYRF": {k: v2 for k in R.CARDS["R2-LAZYRF"]["external_f0"]}}

    def test_m(self):
        h = R.decide(self._cards(), self._ext())
        self.assertEqual((h["m"], h["members"]), (2, ["R1-OPPSELL", "R2-LAZYRF"]))
        self.assertEqual([round(x, 2) for x in h["crit_t"]], [2.27, 1.98])
        h = R.decide(self._cards(p1=0.12), self._ext())
        self.assertEqual((h["m"], h["members"]), (1, ["R2-LAZYRF"]))
        self.assertEqual([round(x, 2) for x in h["crit_t"]], [1.98])
        h = R.decide(self._cards(), self._ext(v2=False))
        self.assertEqual(h["m"], 1)
        h = R.decide(self._cards(0.1, 0.1), self._ext())
        self.assertEqual((h["m"], h["crit_t"]), (0, []))

    def test_pending_external(self):
        h = R.decide(self._cards(), None)
        self.assertIsNone(h["m"])                                                 # R2 외부 F0 모름 → 미정
        self.assertTrue(h["pending"])
        self.assertTrue(any("외부 F0" in w and "R2-LAZYRF" in w for w in h["pending_why"]))
        self.assertEqual(h["m_if_external_pass"], 2)
        h = R.decide(self._cards(p2=0.1), None)                                   # R1 은 카드 외부 F0 가 없다 → 확정
        self.assertEqual((h["m"], h["members"]), (1, ["R1-OPPSELL"]))
        h = R.decide(self._cards(p2=0.1), None, months_final=False)              # 달 관문 목록이 없으면 T 가 잠정 → 미정
        self.assertIsNone(h["m"])
        self.assertTrue(any("달 관문" in w for w in h["pending_why"]))
        h = R.decide(self._cards(0.1, 0.1), None, months_final=False)            # 달을 빼면 P0 가 오를 수도 있다 → 0 도 미정
        self.assertIsNone(h["m"])
        self.assertEqual(h["m_if_external_pass"], 0)

    def test_missing_card_is_pending(self):
        """카드 자료가 없으면(개수 표 None) 가족에서 조용히 빠지지 않고 m 이 미정이다."""
        cs = self._cards()
        cs["R2-LAZYRF"] = {"p0": None, "status": "absent", "T": None}
        h = R.decide(cs, self._ext())
        self.assertIsNone(h["m"])
        self.assertTrue(any("카드 자료 없음" in w and "R2-LAZYRF" in w for w in h["pending_why"]))
        del cs["R2-LAZYRF"]
        self.assertIsNone(R.decide(cs, self._ext())["m"])                         # 아예 없어도 같다
        cs["R2-LAZYRF"] = {"p0": None, "status": "no_months", "T": 0, "T_pass": False, "p0_pass": False, "density_pass": False}
        h = R.decide(cs, self._ext())                                            # 쓸 달 0 은 명시적 실패 → 확정
        self.assertEqual((h["m"], h["members"]), (1, ["R1-OPPSELL"]))

    def test_crit_uses_member_T(self):
        cs = self._cards()
        cs["R1-OPPSELL"]["T"] = 119
        h = R.decide(cs, self._ext())
        self.assertEqual(h["crit_t"], [round(x, 4) for x in R.holm_crit(2, 119)])
        cs["R2-LAZYRF"]["p0"], cs["R2-LAZYRF"]["p0_pass"], cs["R2-LAZYRF"]["T"] = 0.1, False, 60
        h = R.decide(cs, self._ext())                                            # 구성원이 아닌 카드의 T 는 임계에 안 쓴다
        self.assertEqual(h["crit_t"], [round(x, 4) for x in R.holm_crit(1, 119)])

    def test_same_family_clash(self):
        old = R.CARDS["R2-LAZYRF"]["family"]
        R.CARDS["R2-LAZYRF"]["family"] = "insider"
        try:
            with self.assertRaises(SystemExit):
                R.decide(self._cards(), self._ext())
        finally:
            R.CARDS["R2-LAZYRF"]["family"] = old


class _TmpData:
    """임시 자료 폴더(AD.DATA_R) 틀 — 시험마다 새 폴더 · 끝나면 되돌린다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="r_p0_ad_")
        self.old = AD.DATA_R
        AD.DATA_R = self.tmp
        AD.GUARD["run"] = False
        AD._CACHE.clear()
        os.makedirs(os.path.join(self.tmp, "_ins_pit"))

    def tearDown(self):
        AD.DATA_R = self.old
        AD.GUARD["run"] = False
        AD._CACHE.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _w(self, rel, obj):
        with io.open(os.path.join(self.tmp, rel), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)


def tenq_docs(gids, years=(2015, 2016, 2017), seed=4):
    """합성 10-Q 문서(r_r2flags 정본 모양) — 그룹마다 해마다 5·8·11월 공개 세 건."""
    rng = np.random.default_rng(seed)
    V = ["w%d" % j for j in range(40)]
    rows = []
    for gi, g in enumerate(gids):
        base = {w: int(rng.integers(1, 9)) for w in V}
        for y in years:
            for q, (rd, ac) in enumerate((("03-31", "05-02"), ("06-30", "08-01"), ("09-30", "11-01"))):
                tf = {w: max(0, c + int(rng.integers(-3, 4)) * (1 if rng.random() < 0.3 else 0)) for w, c in base.items()}
                rows.append({"acc": "000000%04d-%02d-%06d" % (gi, y % 100, q), "gid": g, "form": "10-Q",
                             "rd": "%d-%s" % (y, rd), "acceptanceDateTime": "%d-%sT14:00:00Z" % (y, ac),
                             "shape": "F", "n_words_rf": 800, "tf_rf": tf,
                             "shape_v3": "F", "parse_status_v3": "ok"})             # 등록 형태 판 v3 열(r_r2flags.REG_SHAPE_VER · 2026-09-26)
    return rows


class Adapter(_TmpData, unittest.TestCase):
    def test_issuer_map(self):
        self._w("_issuer_map.json", {"tm": {"BRK.B": [["2016-01", "2016-03", "g1067983", 1067983, [1067983], 0, "dera", 0]],
                                            "XYZ": [["2016-02", "2016-02", None, None, [], None, "none", None]]}})
        im = AD.IssuerMap()
        self.assertTrue(im.ok)
        self.assertEqual(im.get("BRK-B", "2016-02")["gid"], "g1067983")
        self.assertIsNone(im.get("BRK-B", "2016-04"))
        self.assertIsNone(im.get("XYZ", "2016-02")["gid"])
        self.assertFalse(AD.IssuerMap(os.path.join(self.tmp, "없음.json")).ok)

    def test_ins_layouts(self):
        F = AD.FIELDS["ins_cikmonth"]
        self._w(F["file"], {"months": {"2017-01": {"g1": {"os_n": 2, "rs_n": 0}, "g2": {"os_n": 0, "rs_n": 1}}}})
        os_, src = AD.flag_sets("R1-OPPSELL", "OS")
        rs_, _ = AD.flag_sets("R1-OPPSELL", "RS")
        self.assertEqual((os_, rs_, src), ({"2017-01": {"g1"}}, {"2017-01": {"g2"}}, "canonical:cikmonth(r_r1_flags.export)"))
        self._w(F["file"], {"rows": [{F["g"]: "g3", F["m"]: "2017-02", "O": 1}]})
        self.assertEqual(AD.flag_sets("R1-OPPSELL", "OS")[0], {"2017-02": {"g3"}})

    def test_tenq_rule(self):
        F = AD.FIELDS["tenq_rf"]
        rows = [{F["g"]: "a%d" % j, F["avail"]: "2018-%02d-15" % (1 + j % 12), F["sim"]: 0.80 + 0.01 * j, F["status"]: "ok"}
                for j in range(20)]                                                   # 2018 경계 = 하위 20%
        cut = float(np.quantile([r[F["sim"]] for r in rows], 0.2))
        rows += [{F["g"]: "x", F["avail"]: "2019-05-02", F["sim"]: cut - 0.01, F["status"]: "ok"},
                 {F["g"]: "y", F["avail"]: "2019-05-03", F["sim"]: cut + 0.01, F["status"]: "ok"},
                 {F["g"]: "z", F["accepted"]: "2019-06-30T16:30:00", F["status"]: "no_pair"},   # 16:00 뒤 → 7월 공개
                 {F["g"]: "x", F["avail"]: "2019-06-10", F["status"]: "split_fail"}]
        self._w(F["file"], {"rows": rows})
        ch, miss, defined = AD._tenq()                                                # 간이판(정식 r_r2flags 를 못 읽을 때만 쓰인다)
        self.assertEqual((defined[0], defined[-1]), ("2018-03", "2019-07"))           # 공개월 2018-01..2019-07 → t−2..t 가 자료 안
        for m in ("2019-05", "2019-06", "2019-07"):
            self.assertIn("x", ch[m])
        self.assertNotIn("2019-08", {m for m, v in ch.items() if "x" in v})
        self.assertFalse(any("y" in v for v in ch.values()))
        self.assertFalse(any(m.startswith("2018") for m in ch))                         # 전년도 경계가 없는 해는 없다
        self.assertEqual({m for m, v in miss.items() if "z" in v}, {"2019-07", "2019-08", "2019-09"})
        self.assertFalse(any("x" in v for m, v in miss.items() if m <= "2019-07"))      # CH 가 켜진 달은 결측 더미가 아니다
        self.assertIn("x", miss["2019-08"])

    def test_ins_group_major(self):
        """r_r1_flags.Flags.export 모양 — 그룹 → 가용월 → {"O","R","U","N",…}. OS = O > 0 · RS = R > 0(N 만 있으면 0 이 아니라 표지 없음)."""
        self._w(AD.FIELDS["ins_cikmonth"]["file"], {"g1": {"2017-01": {"O": 1, "all": 1, "O$": 5.0}, "2017-02": {"N": 2, "all": 2}},
                                                    "g2": {"2017-01": {"R": 3, "all": 3}}, "note": "메타"})
        os_, src = AD.flag_sets("R1-OPPSELL", "OS")
        rs_, _ = AD.flag_sets("R1-OPPSELL", "RS")
        self.assertEqual((os_, rs_), ({"2017-01": {"g1"}}, {"2017-01": {"g2"}}))
        self.assertTrue(src.startswith("canonical:"))

    def test_tenq_canonical_routing(self):
        """R2 는 정식 빌더(r_r2flags.r2_build)를 그대로 부른다 — 어댑터가 낸 집합 = r2_build 의 gm 에서 곧바로 뽑은 집합."""
        import r_r2flags as R2
        rng = np.random.default_rng(4)
        V = ["w%d" % j for j in range(40)]
        rows = []
        for g in range(30):
            base = {w: int(rng.integers(1, 9)) for w in V}
            for y in (2017, 2018, 2019):
                for q, (rd, ac) in enumerate((("03-31", "05-02"), ("06-30", "08-01"), ("09-30", "11-01"))):
                    tf = {w: max(0, c + int(rng.integers(-3, 4)) * (1 if rng.random() < 0.3 else 0)) for w, c in base.items()}
                    rows.append({"acc": "000000%04d-%02d-%06d" % (g, y % 100, q), "gid": "G%d" % g, "form": "10-Q",
                                 "rd": "%d-%s" % (y, rd), "acceptanceDateTime": "%d-%sT14:00:00Z" % (y, ac),
                                 "shape": "F", "n_words_rf": 800, "tf_rf": tf,
                                 "shape_v3": "F", "parse_status_v3": "ok"})         # 등록 형태 판 v3 열(2026-09-26)
        self._w(AD.FIELDS["tenq_rf"]["file"], {"docs": rows})
        ch, src = AD.flag_sets("R2-LAZYRF", "CH")
        miss, _ = AD.flag_sets("R2-LAZYRF", "CH_MISS")
        self.assertEqual(src, "canonical:r_r2flags.r2_build")
        R = R2.r2_build(R2.load_tenq(os.path.join(self.tmp, AD.FIELDS["tenq_rf"]["file"])), R2.Cal())
        want_ch, want_miss = {}, {}
        for (g, t), row in R["gm"].items():
            if row["ch"]:
                want_ch.setdefault(t, set()).add(g)
            if row["miss"]:
                want_miss.setdefault(t, set()).add(g)
        self.assertEqual((ch, miss), (want_ch, want_miss))
        self.assertTrue(ch)                                                           # 합성이 한 건도 안 켜지면 시험이 빈다

    def test_provisional_gate(self):
        P = small_panel(with_returns=False)
        F = AD.FIELDS["tenq_rf"]
        self._w(F["file"], {"rows": [{F["g"]: "s0001", F["avail"]: "2017-05-01", F["sim"]: 0.5, F["status"]: "ok"}]})
        old = AD._tenq_canonical
        AD._tenq_canonical = lambda world=None: None                                  # 정식 빌더를 못 읽는 경우를 흉내
        try:
            doc0 = R.build_counts(P)                                                  # 기본: 간이판을 받지 않는다 → 자료 없음
            self.assertEqual((doc0["cards"]["R2-LAZYRF"]["CH"]["src"], doc0["cards"]["R2-LAZYRF"]["CH"]["months"]),
                             ("canonical_unavailable", None))
            doc = R.build_counts(P, allow_provisional=True)
            self.assertTrue(doc["cards"]["R2-LAZYRF"]["CH"]["src"].startswith("provisional"))
        finally:
            AD._tenq_canonical = old

    def test_override_first(self):
        F = AD.FIELDS["ins_cikmonth"]
        self._w(F["file"], {"months": {"2017-01": {"g1": {"O": 2}}}})
        self._w(AD.FIELDS["flags_override"]["file"], {"cards": {"R1-OPPSELL": {"OS": {"2017-03": ["g9"]}}}})
        s, src = AD.flag_sets("R1-OPPSELL", "OS")
        self.assertEqual((s, src.split(":")[0]), ({"2017-03": {"g9"}}, "override"))

    def test_absent(self):
        st = AD.status()                                                              # 파일이 따로 없는 FIELDS 칸(issuer_f0)에서 죽지 않는다
        self.assertNotIn("issuer_f0", st)
        self.assertFalse(any(v["exists"] for v in st.values()))
        self.assertEqual(AD.flag_sets("R1-OPPSELL", "OS"), (None, "absent"))
        self.assertIsNone(AD.coverage_months())
        self.assertIsNone(AD.month_gate()[0])

    def test_month_gate(self):
        self._w(AD.FIELDS["coverage"]["file"], {"months": ["2016-08", "2016-12"], "coverage": {"T": 3, "fail": ["2016-09", "2016-11"]}})
        self._w(AD.FIELDS["issuer_map"]["file"], {"tm": {}, "f0": {"bad_months": ["2016-10"]}})
        self.assertEqual(AD.coverage_months(), ["2016-08", "2016-10", "2016-12"])
        self.assertEqual(AD.month_gate()[0], ["2016-08", "2016-12"])
        self._w(AD.FIELDS["coverage"]["file"], {"months_ok": ["2016-10", "2016-08"]})
        self.assertEqual(AD.month_gate()[0], ["2016-08"])

    def test_counts_from_sets(self):
        P = small_panel()
        s = P.months[3]
        ks = list(P.xs[s].keys[:5])
        cm, outside, total = R.counts_from_sets(P, {s: set(ks) | {"없는키"}})
        self.assertEqual((outside, total), (1, 6))
        self.assertEqual(sum(cm[s].values()), 5)
        self.assertEqual(set(cm), {s})


class WindowEnd(_TmpData, unittest.TestCase):
    """검토 #1 — 정본 cikmonth(r_r1_flags.cikmonth_doc) 의 months_ok 가 끝 신호월 앞에서 끝난다(실자료: 2026-06 · 끝 신호월 2026-07).
    그 달은 «0 개» 가 아니라 «정의 안 됨» — 기본은 멈추고, 빼기로 정하면 T 에서 빠지며 밀도 F0 도 거짓 0 을 보지 않는다."""

    def _cikmonth(self, Pc, end_ok, key=str):
        rng = np.random.default_rng(3)
        groups, mo = {}, [m for m in Pc.months if m <= end_ok]
        for m in mo:
            for k in Pc.xs[m].keys.tolist():
                u = rng.random()
                if u < 0.12:
                    groups.setdefault(key(k), {})[m] = {"O": 1, "R": 0, "all": 1, "os_na": 0, "rs_na": 0}
                elif u < 0.20:
                    groups.setdefault(key(k), {})[m] = {"O": 0, "R": 1, "all": 1, "os_na": 0, "rs_na": 0}
        self._w(AD.FIELDS["ins_cikmonth"]["file"], {"note": "합성", "months_ok": ["2011-02"] + mo, "groups": groups})

    def test_undefined_end_month(self):
        Pc, P = small_panel(with_returns=False), small_panel()
        sig = reg_months(P)
        last = sig[-1]
        self._cikmonth(Pc, R.QC.mshift(last, -1))
        C = R.build_counts(Pc)
        rec = C["cards"]["R1-OPPSELL"]["OS"]
        self.assertEqual((rec["defined_months"][0], rec["defined_months"][-1]), (Pc.months[0], R.QC.mshift(last, -1)))
        self.assertNotIn(last, rec["months"])                                         # 정의 밖 달은 개수가 없다(0 이 아니다)
        self.assertEqual(rec["in_universe_share"], 1.0)
        self.assertIsNone(C["cards"]["R2-LAZYRF"]["CH"]["months"])
        with self.assertRaises(SystemExit):                                          # 기본: 멈춤
            R.run(P, C, months_ok=sig, B=5)
        AD.GUARD["run"] = False
        d = R.run(P, C, months_ok=sig, B=10, drop_undefined=True)
        r1 = d["cards"]["R1-OPPSELL"]
        self.assertEqual((r1["T"], r1["dropped"]["undefined"]), (len(sig) - 1, [last]))
        self.assertEqual(d["window_decision"]["undefined_dropped"]["R1-OPPSELL"], [last])
        os_min = [x for x in r1["density_f0"] if x["dummy"] == "OS" and x["stat"] == "min"][0]
        self.assertGreaterEqual(os_min["value"], 5)                                   # 거짓 0 이 없다
        self.assertTrue(r1["density_pass"])
        self.assertIsNone(d["holm"]["m"])                                             # R2 자료 없음 → 미정
        self.assertTrue(any("카드 자료 없음" in w and "R2-LAZYRF" in w for w in d["holm"]["pending_why"]))

    def test_key_mismatch_stops(self):
        """표지 키가 세계 키와 어긋나면(예: int CIK 대 'g…') 개수가 0 에 가깝게 되어 m 이 조용히 0 이 된다 — 카운트 단계가 멈춘다."""
        Pc = small_panel(with_returns=False)
        self._cikmonth(Pc, Pc.months[-1], key=lambda k: "cik" + k)
        with self.assertRaises(SystemExit):
            R.build_counts(Pc)

    def test_override_needs_flag(self):
        Pc = small_panel(with_returns=False)
        s = Pc.months[3]
        self._w(AD.FIELDS["flags_override"]["file"], {"cards": {"R1-OPPSELL": {"OS": {s: Pc.xs[s].keys[:3].tolist()}}},
                                                      "months_ok": Pc.months})
        with self.assertRaises(SystemExit):
            R.build_counts(Pc)
        C = R.build_counts(Pc, allow_override=True)
        rec = C["cards"]["R1-OPPSELL"]["OS"]
        self.assertTrue(rec["src"].startswith("override"))
        self.assertEqual((sum(rec["months"][s].values()), rec["defined_months"]), (3, Pc.months))


class R2Boundary(_TmpData, unittest.TestCase):
    """검토 #3 — R2 경계(전년도 하위 20%)의 세계가 2016-06 에서 시작하면 2016 경계를 호출자 세계로 세울 수 없다.

    2026-09-26 결정(r_p0_test 95 ≠ 0 을 푼 쪽 — 시험이 낡았다 · _bw 는 그대로): 호출자 세계가 덮지 않은 달의 짝은 'out' 이 아니라
    r_r2flags ⑦ 대로 in_world(§C 칸 · 없으면 §C 전체 = 'uncovered_all')로 메우고 출처를 bounds[연도].src · world_months 에 적는다.
    근거 = 배치 R 계획(PREREG-2026-09-2x-RBATCH «R2 경계 분포의 세계» — 정본 경계가 그 세계 12달로 서지 않으면(uncovered_all 섞임)
    러너가 멈춘다: 섞임은 라이브러리가 드러내고 러너가 거절한다) · r_r2flags 자체 시험 boundary_world_midyear · r_run 자체 시험
    «패널 세계(2015 짝 없음)면 멈춤(uncovered_all 섞임)». 그래서 짧은 세계의 표지는 서지만 러너(r_run.r2_bounds_check)가 거절하고,
    카운트 단계는 짧은 세계를 받지 않는다(test_counts_needs_boundary_world). 2015-01(BW0) 부터의 세계는 출처가 caller 뿐이다."""

    def test_adapter_boundary_world(self):
        import r_r2flags as R2
        import r_run as RR
        gids = ["G%d" % g for g in range(60)]
        self._w(AD.FIELDS["tenq_rf"]["file"], {"docs": tenq_docs(gids)})
        wa = {(g, m) for g in gids for m in R.QC.months_between("2016-06", "2017-12")}
        wb = {(g, m) for g in gids for m in R.QC.months_between(R.BW0, "2017-12")}
        a, b = AD.flag_source("R2-LAZYRF", "CH", world=wa), AD.flag_source("R2-LAZYRF", "CH", world=wb)
        ma = AD.flag_source("R2-LAZYRF", "CH_MISS", world=wa)["sets"]
        m16 = R.QC.months_between("2016-05", "2016-12")
        p = os.path.join(self.tmp, AD.FIELDS["tenq_rf"]["file"])
        Ra = R2.r2_build(R2.load_tenq(p), R2.Cal(), world=wa)
        Rb = R2.r2_build(R2.load_tenq(p), R2.Cal(), world=wb)
        # 짧은 세계: 2016 경계는 호출자 세계 밖(2015) 짝으로만 섰다 · 2017 경계는 7달 세계 + 메움 — 출처가 드러난다
        self.assertEqual((Ra["bounds"][2016]["src"], Ra["bounds"][2016]["world_months"]), ({"uncovered_all": 120}, 0))
        self.assertEqual(Ra["bounds"][2017]["world_months"], 7)
        self.assertIn("uncovered_all", Ra["bounds"][2017]["src"])
        with self.assertRaises(SystemExit):                                          # 러너는 이 판을 굽지 않는다
            RR.r2_bounds_check(Ra, window=("2016-08", "2017-11"))
        # 긴 세계(BW0 부터): 출처 caller 뿐 · 12달 — 러너가 받는다
        self.assertEqual((Rb["bounds"][2016]["src"], Rb["bounds"][2016]["world_months"]), ({"caller": 120}, 12))
        self.assertEqual((Rb["bounds"][2017]["src"], Rb["bounds"][2017]["world_months"]), ({"caller": 180}, 12))
        self.assertTrue(RR.r2_bounds_check(Rb, window=("2016-08", "2017-11")))
        # 어댑터 표지 — 메움 덕에 짧은 세계도 2016 CH 가 선다(합성 §C = 세계라 긴 세계와 같은 판 · no_boundary 결측 없음)
        self.assertGreater(sum(len(a["sets"].get(m, ())) for m in m16), 0)
        self.assertEqual({m: a["sets"].get(m) for m in m16}, {m: b["sets"].get(m) for m in m16})
        self.assertEqual(len(ma.get("2016-08", ())), 0)
        self.assertGreater(min(len(b["sets"].get(m, ())) for m in ("2016-05", "2016-08", "2016-11")), 0)
        self.assertEqual((b["defined"][0], b["defined"][-1]), ("2015-07", "2017-11"))  # 공개월 2015-05..2017-11

    def test_counts_needs_boundary_world(self):
        Pc = small_panel(churn=0.0, with_returns=False)
        keys = Pc.xs[Pc.months[0]].keys.tolist()
        self._w(AD.FIELDS["tenq_rf"]["file"], {"docs": tenq_docs(keys[:60])})
        with self.assertRaises(SystemExit):                                          # 패널 세계는 2015-06 부터 > 2015-01
            R.build_counts(Pc)
        bw = R.panel_world(Pc) | {(k, m) for k in keys for m in R.QC.months_between(R.BW0, Pc.months[0])}
        C = R.build_counts(Pc, bworld=bw)
        self.assertTrue(C["r2_boundary_world"]["ok"])
        ch = C["cards"]["R2-LAZYRF"]["CH"]
        self.assertTrue(ch["src"].startswith("canonical"))
        self.assertGreater(sum(sum(v.values()) for m, v in ch["months"].items() if m.startswith("2016")), 0)
        self.assertEqual(ch["defined_months"][0], "2015-07")


class LagKeys(unittest.TestCase):
    def test_lag_index_uses_group_at_t_minus_k(self):
        """지주사 재편으로 그룹이 바뀐 이름 — 달 t 키 'new' · t−1 의 같은 티커 그룹 'old' → t−1 횡단면의 'old' 자리를 본다."""
        a = R.CS(["old", "x"], [0, 0])
        b = R.CS(["new", "x"], [0, 0], lag_keys={1: ["old", "x"]})
        r = np.array([True, True])
        self.assertEqual(R.lag_index(b, a, r, 1).tolist(), [0, 1])
        self.assertEqual(R.lag_index(b, b, r, 0).tolist(), [0, 1])
        c = R.CS(["new", "x"], [0, 0])                                                # lag_keys 가 없으면 지금 키 → 없음(−1)
        self.assertEqual(R.lag_index(c, a, r, 1).tolist(), [-1, 1])


class EndToEnd(unittest.TestCase):
    def tearDown(self):
        AD.GUARD["run"] = False

    def test_doc(self):
        P = small_panel()
        C = R.synth_counts_doc(P, seed=21)
        d1 = R.run(P, C, B=20)
        AD.GUARD["run"] = False
        d2 = R.run(P, C, B=20)
        self.assertEqual(d1["result_sha"], d2["result_sha"])
        for code, r in d1["cards"].items():
            self.assertEqual(r["sigma_plan"], max(r["sigma_analytic"], r["sigma_placebo"]))
            self.assertAlmostEqual(r["pi"], round(_phi_sf(2.27 - 0.5 * abs(r["gamma_lit"]) * math.sqrt(r["T"]) / r["sigma_plan"]), 6), places=6)
            self.assertAlmostEqual(r["p0_sigma"], round(0.4 * r["pi"] + 0.0075, 6), places=5)   # σ 규칙 P0
            self.assertAlmostEqual(r["p0"], round(min(r["p0_sigma"], r["p0_lit"]), 6), places=6)  # 2026-09-26 P0 바닥(META-2)
            tl = R.LIT[code]
            self.assertAlmostEqual(r["t_alt_lit"], round(0.5 * tl["t_lit"] * math.sqrt(r["T"] / tl["T_lit"]), 6), places=6)
            self.assertEqual(len(r["placebo"]["sd_each"]), 20)
        blob = json.dumps(d1, ensure_ascii=False)
        self.assertNotIn('"mean', blob)                                               # 위약 평균을 싣지 않는다
        self.assertIsNone(d1["holm"]["m"])            # 달 관문 목록이 없으면 m 미정(합성 72개월 < 84 라도)
        self.assertTrue(any("달 관문" in w for w in d1["holm"]["pending_why"]))
        self.assertTrue(all(r["dropped"]["undefined"] == [] for r in d1["cards"].values()))
        ms = [m for m in P.months if R.SIG0 <= m]
        d3 = R.run(P, C, months_ok=ms[:30], B=5)                                      # 커버리지 F0 달만 · T < 84
        self.assertTrue(all(r["T"] == 30 and not r["T_pass"] for r in d3["cards"].values()))
        self.assertEqual((d3["holm"]["m"], d3["holm"]["pending"]), (0, False))       # 모든 카드 자료 · 달 관문 · 명시적 T 실패 → 0 확정
        self.assertEqual(len(d3["cards"]["R1-OPPSELL"]["dropped"]["gate"]), len(reg_months(P)) - 30)

    def test_absent_counts(self):
        P = small_panel()
        C = R.synth_counts_doc(P)
        C["cards"]["R2-LAZYRF"]["CH"]["months"] = None
        ms = reg_months(P)
        d = R.run(P, C, months_ok=ms, B=3)
        self.assertIsNone(d["cards"]["R2-LAZYRF"]["p0"])
        self.assertEqual(d["cards"]["R2-LAZYRF"]["status"], "absent")
        self.assertIsNotNone(d["cards"]["R1-OPPSELL"]["p0"])
        self.assertIsNone(d["holm"]["m"])                                             # 자료 없는 카드 → 미정(조용히 빠지지 않는다)
        self.assertTrue(any("카드 자료 없음" in w for w in d["holm"]["pending_why"]))

    def test_undeclared_defined_months_stop(self):
        P = small_panel()
        C = R.synth_counts_doc(P)
        C["cards"]["R1-OPPSELL"]["RS"]["defined_months"] = None
        with self.assertRaises(SystemExit):
            R.run(P, C, B=3)

    def test_zero_focal_month_leaves_T_not_density(self):
        P = small_panel()
        C = R.synth_counts_doc(P, seed=21)
        ms = reg_months(P)
        C["cards"]["R2-LAZYRF"]["CH"]["months"][ms[5]] = {}                            # 그달 CH 0 개(정의된 달)
        d = R.run(P, C, months_ok=ms, B=3)
        r = d["cards"]["R2-LAZYRF"]
        self.assertEqual((r["T"], r["dropped"]["zero_focal"]), (len(ms) - 1, [ms[5]]))
        self.assertEqual(r["density_f0"][0]["value"], float(np.median(
            [R.n1_of(P, C["cards"]["R2-LAZYRF"]["CH"]["months"], t) for t in ms])))    # 밀도는 0 인 달도 센다

    def test_member_world_ignores_prices(self):
        """R2 경계 세계 = 날것 월말 명단(가격 무관) · 금융·섹터 모름·FPI·못 푼 그룹·재배정 티커 마지막 멤버월은 뺀다."""
        class FW:
            W = {"lists": {"spx": {"2015-01": ["AAA", "BBB", "FIN", "FPI"]}, "ndx": {"2015-01": ["AAA", "CCC", "NOS", "RE"]}},
                 "reassigned": {"RE": {"last": "2015-01"}}}
            me = {}                                                                   # 가격 달이 하나도 없어도 된다

            def sector(self, t, k, m):
                return {"FIN": R.FIN, "NOS": "?"}.get(t, "IT")

        class IM:
            ok = True

            def get(self, t, ym, k=None):
                return {"AAA": {"gid": "g1", "fpi": 0}, "BBB": {"gid": "g2", "fpi": None}, "FPI": {"gid": "g3", "fpi": 1},
                        "RE": {"gid": "g4", "fpi": 0}}.get(t)
        w, tl = R.member_world(FW(), IM(), ["2015-01"])
        self.assertEqual(w, {("g1", "2015-01"), ("g2", "2015-01")})
        self.assertEqual((tl["fin"], tl["nosec"], tl["fpi"], tl["unresolved"], tl["reassigned_last"]), (1, 1, 1, 1, 1))

    def test_provenance(self):
        pv = R.module_provenance([R.ROOT])
        self.assertIn("r_p0", pv)
        self.assertEqual(pv["r_p0"]["sha256"], R._sha_lf(os.path.join(HERE, "r_p0.py")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
