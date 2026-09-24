# 사전등록 배치 Q — 카드 원문(영문 · 2026-09-25 · 조사 13 에이전트의 최종 종합 그대로)

본 문서는 build/PREREG-2026-09-25-QBATCH.md 와 같은 커밋에 얼린다. 규칙 · 파라미터 · 대조 · 위약의 정본이다(판정 · 관문 · 다중성은 본 문서 §4~§7 과 build/qbatch_run.py).
우선순위는 build/PREREG-2026-09-25-QBATCH.md 머리의 한 줄을 따른다(규칙 = 그 문서 §12 > 이 원문 > 그 문서 §3 · 관문 · 다중성 · 판정 = 그 문서 §4~§7 = 얼린 qbatch_run.py).

# BATCH DESIGN

BATCH Q (2026-09-25) — preregistration design. No performance has been computed for any candidate.

**0. COMPOSITION**
- 12 new built cards: Q01, Q02, Q03, Q05, Q06, Q07, Q08, Q09, Q10, Q12, Q13, Q16.
- 3 planned items: Q04 factor-ETF TSM, Q11 sector seasonality, and the library pair Q14 L2 / Q15 L4.
- At least 9 distinct mechanisms: quality composite, covariance-optimal sizing, regime-switch between engines, earnings-calendar premium, earnings seasonality, copula tail dependence, network periphery, covariance fragility (AR/CS), and variance-risk-premium beta timing (surge side).
- EG30-dependent confirmatory alpha is capped at 3 of 8 slots (B1, B2, S1).

**1. COMMON FRAME** (qbatch_core docstring = EG30PLUS §2)
- Fund = 0.9 SPY TR + 0.1 sleeve, reset monthly, reset cost 2 × 10bp × deviation.
- 10bp one-way on every traded leg; a 20bp row is reported for every rule.
- Holdings 2016-09..2026-08 (120 months); long-only, no leverage, no shorts; T-bills = rf_monthly DGS3MO.
- Judge line: SPY TR. S&P 500 PR versions are reported.
- DEFINITIONS:
  - X_t = fund_t − SPYTR_t.
  - H_t = X_t − 0.1(β̂_s − 1)(SPYTR_t − rf_t), where β̂_s is the 120-month OLS slope of the sleeve's monthly return on SPY TR (evaluate sleeve_beta).
  - Class B: Δβ_t = (X_rule,t − X_ref,t) − 0.1(β̂_rule − β̂_ref)(SPYTR_t − rf_t).
  - Switch class: Δ^D_t = X_rule,t − X_D,t. D = the static mix at the rule's realized share, rebalanced at month-ends, 10bp.
- DOWN = the 39 months with S&P 500 PR < 0 (EG30PLUS continuity). The 35-month SPY-TR-negative set is reported for every row. Both are frozen by sha.
- Both-side sets: mech_episodes.json CRASH-M (14), SURGE-M (26), crash legs and rebounds (sha 1c0bc5f1…). The 6 named crashes and 6 named surges are report-only.
- Statistics:
  - NW(3) t (evaluate nw_t);
  - down-month tests via eg30plus.down_t (calendar HAC, Bartlett 3, t(38));
  - dilution via eg30plus.dilution;
  - hedge_ctrl.
  - One evaluator (qbatch_core.evaluate); no re-implementation.

**2. DATA PINS AND PREREQUISITES** (all before the prereg commit)

(a) THREE-PART PIN, as eg30plus.py does (SNAP line 42, SNAP_BASE line 43, verified):
- P1: prices from 940f0bda (stocks.json, pit_px.json, sd/; equal 4457-date grids).
- P2: non-price inputs from bef4eea8: bench_px, rf_monthly, index_history, index_ledger, pit_universe, pit_reuse, fx, fx_pit, assets, splits, shares_yf and earn_dates. bef4eea8 assets.json is as_of 2026-09-23 and earn_dates.json exists there (verified).
- P3: blob hashes of post-bef4eea8 inputs: _eg_q5_scores_pitgics.json, pit_gics_sectors.json, mech_episodes.json, the published PIT x-bmrot series, eg30plus.py, qg_lab.py and qbatch_core.py.
- qbatch_core.py is UNTRACKED today (git status '??', verified) and must be committed first.
- Extend eg30plus's byte-equality check to the P3 hashes.
- The working tree cannot load stocks (pit_px 4458 dates vs stocks.json 4457), so all runs use the pins.

(b) V0 REGENERATION: data/_eg30plus.json does NOT hold per-formation V0 weights. Regenerate them with eg30plus.World.weights(EG_BASE, m), then assert:
- the monthly fund series reproduces the published V0 row (TR +0.76%/yr, IR 0.82, down −0.075, 8/11 years) with a month difference of 0;
- the target hash is frozen.

(c) x-bmrot LEG REPRODUCTION (Q03/Q10/Q06): max |Δ| ≤ 1bp/month against the published PIT series. If it fails, the prereg names the T-bill leg before the commit.

(d) P-FF: a first-filed rebuild of NI/EQ/CFO/CAPEX/ASSET/LIAB/SH from companyfacts (earliest 'filed' per period; as-of = max(period end + 90d, filed)). If it is not ready, Q01/Q12 use latest-filed values with the limitation stated, and the first-filed rerun is a mandatory G5 condition before any forward entry.

(e) COVERAGE-ONLY probes: the Q01 component freeze and the Q12 mapped share.

(f) UNIT TESTS:
- RIE on a synthetic Wishart;
- the 12 copula CDFs and densities, and λ_L at the bounds;
- centralities on star and path graphs;
- JM DP and coordinate descent on a synthetic 2-state series;
- CS ≡ 1 when Σ is diagonal;
- the CHSS mapping on AAPL, WMT and KO including Q4;
- the Bretz graph reproducing Holm in the equal-weight case.

(g) PIT asserts: every filing, period and fundamental used at m has a date < LTD(m) and respects the 90-day lag.

(h) Library prerequisites: the ledger, the pivot-NAV export, the SPHB loader, and frozen U2/U4 sids.

(i) networkx is absent, so the PMFG arms are reported as 'not run' unless it is installed before the commit.

**3. CLASSES AND PRIMARY ENDPOINTS**
- **Class A**, stand-alone sleeves (Q01, Q04, Q05, Q11): all-month X, NW(3) t, one-sided p from t(119).
- **Class B**, steps on V0 (Q02; Q07 and Q08): the down-month mean of Δβ(rule − V0), down_t, one-sided p from t(38).
- **Class S**, switches:
  - Q03 and Q10: EG30 ↔ x-bmrot.
  - Q16: SPY ↔ SPHB tranches.
  - Endpoint: the all-month mean of Δ^D.
  - p = (1 + #{t_perm ≥ t_obs})/10001 from a studentized segment-shuffle permutation (10,000 draws, seed 20260925). On and off run lengths are permuted separately and re-interleaved from the true initial state, which preserves the switch count and the realized share.
- **Class C**, children: Q12 is the paired all-month Δ vs Q05 (NW t); Q13 is the down-month Δβ vs Q02.
- **Class D**, library (Q14, Q15): forward-only in LIBMETA F-LIB (H2/H3; Holm m = 4 at 2.50/2.39/2.24/1.96). The in-sample rows are 오염 측정.
- **Class M**, measured only (Q06, Q09, and every neighbour, twin and arm): never promotable, never replaces a primary; counted in the trial tally and the DSR N.

**4. GATES**
All thresholds below are fixed before any computation; the verdict labels are defined after the gates.
- **G1 significance:** the tier rule in §5.
- **G2 both-side (criterion 2)**, on X:
  - CRASH-M mean > 0 AND SURGE-M mean > 0 gives the label '양면'.
  - One side only gives '급락형' or '급등형' → '한쪽형 — 측정만'. Such a rule is not forward-entered and is usable only as a component of a later registered combination.
  - Switches additionally carry the REBOUND-MISS condition: over SURGE-M months starting within 63 trading days of a switch-out, the mean Δ^D must be ≥ 0 when there are at least 3 such months. The pre-stated expected sign is negative for T-bill arms (VOLMOM lesson) and about 0 for engine legs.
- **G3 defense (criterion 3):**
  - Class A: down-month mean X ≥ 0 AND down-month mean H > 0 (the beta-matched hedge).
  - Class B: raw down-month Δ ≥ 0; M1 down-month mean X > V0 diluted to the rule's annual excess (point); efficiency floors vs SPY TR (IR ≥ 0.72, excess ≥ +0.38%/yr, TE ≤ 1.20%, turnover ≤ 272%/yr; a Q02 breach is 기각).
  - Q03 and Q10: down-month mean Δ^D > 0; M1 as for Class B; efficiency floors on IR, excess and TE; the turnover floor is replaced by sleeve cost drag ≤ 2 × V0's.
  - Q16: down-month mean X ≥ 0 AND down-month mean Δ^D > 0.
- **G4 mechanism:** each card's own control, placebo or twin, exactly as written on the card:
  - Q01: C1 t ≥ 1.0; C0 t ≥ 1.0 and 2019-09+ point > 0; C2 all-month and H-down ≥ 95th percentile.
  - Q02: C2 (Ξ = I) Δβ point > 0.
  - Q03: placebo down ≥ 95; sma200 and vol twins beaten on both means.
  - Q04: exposure-matched control t ≥ 1.0; count placebo ≥ 95; phi caps.
  - Q05: non-announcer t ≥ 1.0; run-up label rule.
  - Q07: C3 Δβ point > 0; placebo ≥ 95 on Δβ.
  - Q08: C3 (lowest R̄) Δβ point > 0; placebo ≥ 95 on Δβ.
  - Q10: placebo ≥ 95; vol twin beaten.
  - Q11: sleeve − EW9 point > 0; joint month-label placebo ≥ 95.
  - Q12 and Q13: placebo ≥ 95.
  - Q16: IV-only twin beaten; SURGE-M Δ^D > 0.
  - F0 unmeasurable conditions → 측정 불가.
- **G5 robustness**, on the class primary statistic:
  - it is > 0 in both halves (2016-09..2021-08 and 2021-09..2026-08) and in at least 3 of 4 thirty-month blocks;
  - Class B down-month counts per half are 15/24 and per block 7/8/13/11 (critic count, re-verified from the frozen set in the bake);
  - at 20bp, the primary point estimate stays > 0 and G2 stays true, with no second significance test;
  - one-way sleeve turnover ≤ 10x/yr, except switch trades, which fall under the cost floor;
  - Q01/Q12 without P-FF: the first-filed rerun has the same sign.
- **G6 years won (user principle 2):** 11 calendar periods (2016 Sep-Dec, 2017..2025, 2026 Jan-Aug) in which the fund beats SPY TR. At least 6/11 for Class A and Q16; at least 8/11 (V0's count) for Class B, Q03 and Q10. Each card pre-states the years it expects to change (EG30 loses 2016, 2022 and 2026).

**Verdict labels:**
- '전방 진입': forward-entry tier significance AND G2 '양면' AND G3-G6.
- 'in-sample 통과(측정만·전방 대기)': graphical-Holm rejection AND G2-G6. This implies forward entry.
- '한쪽형 — 측정만': significant but one-sided.
- '측정 불가': F0 fired.
- Otherwise '기각'.
- Label caps: repackaging flags (Q03 and Q10 twins, Q04 phi, Q05 run-up, Q16 IV twin, SEASEC-B attribution) cap the verdict at 측정만.
- '보류(유망)' is abolished. The DSR is never a gate.

**5. MULTIPLICITY** (F-Q)
- 8 slots holding 10 primary hypotheses plus 2 children.
- **LABEL TIER:** the Bretz-Maurer-Brannath-Posch 2009 graphical weighted-Bonferroni procedure, one-sided FWER α = 0.025, applied to p-values only; gates are applied afterwards.
  - Initial weights: Q01, Q04, Q05, Q11, Q16 and Q02 1/8 each; Q07, Q08, Q03 and Q10 1/16 each; Q12 and Q13 0.
  - Transition matrix, single slots: Q01, Q04, Q11 and Q16 each send 1/9 to each of the other 9 non-child primaries.
  - Transition matrix, parents: Q05 → Q12 = 1; Q02 → Q13 = 1.
  - Transition matrix, children: Q12 sends 1/9 to each of the 9 primaries other than Q05; Q13 sends 1/9 to each of the 9 primaries other than Q02.
  - Transition matrix, siblings: Q07 → Q08 = ½, with ½ split equally over the other 8 non-child primaries (1/16 each); Q08 → Q07 symmetric; Q03 ↔ Q10 the same.
  - Updated by Bretz Algorithm 1 (fixed matrix, no traps).
  - Approximate first-step one-sided t thresholds:

| Step | Normal | t(119) | t(38) |
|---|---|---|---|
| Weight 1/8 (α 0.003125) | 2.73 | 2.78 | 2.90 |
| Weight 1/16 (α 0.00156) | 2.96 | 3.02 | 3.16 |
| Last remaining hypothesis (α 0.025) | 1.96 | 1.98 | 2.02 |

  - Switch p-values come from the permutation directly.
- **FORWARD-ENTRY TIER:** Benjamini-Hochberg at q = 0.10 (one-sided) over the 10 primary p-values. Children enter only if the parent is admitted AND the child's p ≤ 0.10 AND the child passes its gates (fixed sequence).
  - BH step thresholds, the k-th smallest p ≤ 0.01k:

| k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| t(119) | 2.36 | 2.08 | 1.90 | 1.77 | 1.66 | 1.57 | 1.49 | 1.41 | 1.35 | 1.29 |
| t(38) | 2.43 | 2.13 | 1.94 | 1.80 | 1.69 | 1.59 | 1.51 | 1.43 | 1.37 | 1.30 |

- Romano-Wolf is NOT used: one device per tier avoids forking.
- F-LIB (Q14, Q15) is separate, as already registered.
- **FAMILY DISCLOSURES in the prereg header** (also used as the DSR N):
  - quality components ≥ 14;
  - EAP family ≥ 5 (incl. x-earngap);
  - factor momentum ≥ 6 (incl. CGATE-mom, STYLE8ROT);
  - de-risking / regime switches ≥ 6 prior plus Q03/Q06/Q10 (QGSIZE, c06, c11, VOLMOM, AEGIS, t-voltgt/t-volreg, M9);
  - VIX timing ≥ 7 (163, 164, 582, 607, 18/24/26) plus Q16;
  - sector axis ≥ 13 (incl. c04-season-sector keep:false) plus Q11;
  - calendar family (t-tom, Halloween sector, 248, x-season, E29);
  - low-corr / network (277, 53, 401) plus Q08/Q09;
  - tail / moment ≥ 6 plus Q07;
  - EG30 step family (EG30PLUS S1/B1/S2, EGBEST C1/C2, IDXEG) plus Q02/Q07/Q08/Q13;
  - library (UNION, LOWCORR, RRG) plus Q14/Q15.
- **DSR** (Bailey-López de Prado 2014, from the skew and kurtosis of monthly X): REPORT-ONLY, at N = 10, N ≈ 45 (plus children, neighbours, twins and arms) and N ≈ 700 (the lab's recorded trials).
- **Forward haircut:** in-sample excess × 0.5 (McLean-Pontiff).
- **POWER, stated in advance** (t ≈ IR·√10):
  - Class A needs a fund IR ≈ 0.88 for the label tier and ≈ 0.75 for BH's first step.
  - Class B: the SE of the down-month Δ is about 0.031%/mo (critic calibration from EG30PLUS S1/B1). The label needs about 0.09-0.10%/mo, more than V0's whole deficit of −0.075, so it is practically unreachable. BH needs about 0.075 at the first step and about 0.040 at the last.
  - Switches: for a down-side statistic the oracle ceiling is sqrt(k/(1 − k/39)); the all-month Δ^D is the primary for that reason.
  - Expected outcome: 0-1 in-sample label passes and 0-2 forward entries across the batch.
  - Priors on the cards = P(forward-entry tier) and are calibrated to this power.

**6. PROCESS**
- One prereg commit BEFORE any candidate computation. It contains:
  - all modules: build/q_qmj.py, q_riegk.py, q_jump.py, q_bmrot_leg.py, q_absorb.py, q_corrsurp.py, q_ltd.py, q_netper.py, q_eap.py, q_vrp.py, plus the ETF rules;
  - the frozen component list, sids, seeds and pins;
  - the V0 and x-bmrot reproduction hashes;
  - this gate table.
- An adversarial review of the prereg follows.
- Then one bake from the pins. No rerun or edit after seeing results; any edit is a new trial with a new registration.
- Result docs use build/fund_report.py (근본 이유 first; appendix only recent trades and limits) and report:
  - excess (TR and PR), TE, IR;
  - down/up means and captures, H, Δβ, Δ^D;
  - CRASH-M/SURGE-M and legs, named episodes;
  - years won, halves and blocks;
  - turnover, the 20bp row;
  - every control, placebo percentile and twin;
  - DSR at the three N values;
  - the graph and BH step reached.

**7. FORWARD RULE** (in-sample never adopts)
- Forward-entered rules go to an append-only ledger from the first month-end close after the commit (target 2026-10-30; forward month 1 = 2026-11), with the code hash frozen and the entry trade charged.
- earn_dates is refreshed before Q05/Q12 enter.
- FF1: at 24 forward months, cumulative forward X vs the rule's PRIMARY control (D for switches; V0 for Class B; the card's control for Class A) ≤ 0 → 기각.
- FF2 (adopt): at ≥ 36 forward months AND the event minimum (≥ 3 crash legs, ≥ 3 rebounds, ≥ 4 CRASH-M months), adopt only if ALL hold:
  - forward mean X > 0 with NW t ≥ 1.0;
  - beats its primary control with NW t ≥ 1.0;
  - the '양면' label holds forward;
  - forward down-month mean H > 0.
  - Disclosed: FF2's t ≥ 1.0 is looser than LIBMETA's forward bar (Holm 2.50).
- Otherwise 보류, with one re-test at 60 months, then publish or reject.
- Adoption means entering the fund satellite only through a new registered step or combination (the user's step principle). Any change resets the forward clock.
- L2/L4 follow LIBMETA FF1-FF4.
- 'Keep going until good results' is honoured by new preregistered batches, never by re-tuning a rejected rule. Next candidates:
  - E63 KNS SDF shrinkage, if a non-contaminated input set can be defined (critic warning: the lab's 200 measured rules would contaminate it);
  - a blend-size registration (EG30/x-bmrot at about 23% sleeve, noted in EGBEST §3) as a separate frame decision.

# CHANGES

**STRUCTURE**
- F-Q now has 8 slots holding 10 primaries (it was 11 single slots).
- Q06 and Q09 moved out of F-Q to measured-only (critiques 2 and 3). Both are still built, reported and counted.
- Q07 and Q08 share one slot at half weight each, as do Q03 and Q10 (critique 3: one alpha slot per mechanism; EG30-dependent slots capped at 3 of 8).
- New surge/rebound-side stand-alone card Q16 (VRP high-beta tranches; Bollerslev-Tauchen-Zhou, full FEDS text opened).
- REJECTED critique 3's suggested replacement (Nagel 2012 VIX-conditional monthly reversal). I opened Nagel's full text (NBER w17653):
  - it is a DAILY strategy (weights on day t−1..t−5 returns);
  - inventory half-lives are half a day to two days for the largest stocks;
  - so the monthly version has no support in the paper;
  - daily or weekly versions break the 10x cap;
  - and REVCOMP had already closed the reversal family (PIT weekly −2.71%p, monthly −7.33%p).

**MULTIPLICITY** (critique 2)
- DSR is report-only. It was the binding gate (t ≥ 3.78) and was undefined for the Class B endpoints.
- Holm with a vague rule for children is replaced by a fully specified Bretz graph: sibling edges, parent → child edges of weight 1, no traps.
- New two-tier verdict: BH q = 0.10 for forward entry; the graph at FWER 0.025 for the in-sample label.
- '보류(유망)' is abolished.
- Romano-Wolf is not adopted, to keep one device per tier.

**ENDPOINTS** (critique 2)
- Class B primary: the beta-hedged down-month Δβ (the raw Δ was mechanical for beta-reducing steps). The raw Δ, the dilution comparison (M1) and the efficiency floors become point gates. All Class B controls and placebos are evaluated on Δβ.
- Switches: the all-month Δ^D vs a monthly-rebalanced exposure-matched blend, with a studentized segment-shuffle p-value. The shuffle mechanics are pinned (segment lengths permuted separately).
- Switches also get:
  - an ē-matched vol-twin gate (replacing Q10's phi flag);
  - F0 of at least 12 off months and at least 6 off-state down months;
  - a cost-drag floor in place of the 272% turnover floor;
  - a rebound-miss condition (critique 3).
- Class A G3 and the Q01 placebo use the beta-hedged H.
- G5 has a named statistic and a defined 20bp rule.
- New G6 years-won gate (user principle 2; critique 3).
- The down-month set is declared (39 PR months) and the 35-month TR set is reported.

**PER CARD**
- **Q01:**
  - cash-flow and accrual components from one annual fiscal-year bucket (critique 1, high: the cfo/capex quarterly buckets hold only fiscal Q1);
  - 80% cap-coverage freeze, dropping the GP/REV items;
  - LIAB leverage; DISS dropped;
  - split-safe EISS;
  - first-filed rebuild or mandatory sensitivity for restatement look-ahead;
  - priced-universe co-benchmark C0;
  - disclosure of x-roe, x-gpa, other components and QG30;
  - pre-stated '급락형'; a no-safety-pillar row;
  - JKP rates re-labelled as all-factor.
- **Q02:**
  - α restricted to the Eg top-60 pool (critique 3: otherwise it becomes an IDXEG-style tilt);
  - κ_IW renamed and pinned;
  - log-κ bracket, SLSQP/trust-constr tolerances and fallback;
  - TE* sector-correlation fallback (critique 1);
  - C2 mechanism gate on Δβ;
  - IDXEG counted as a seen relative.
- **Q03:**
  - defensive leg changed from T-bills to x-bmrot (critique 3; the user's switching goal; EGBEST active correlation −0.52 verified at line 42). T-bills become a measured arm.
  - control D = the static EG30/x-bmrot blend at the realized share;
  - pre-commit x-bmrot reproduction gate, with a declared T-bill fallback decided before the commit;
  - sma200 and vol twin gates; family precedent disclosed.
- **Q04:**
  - primary signal now beta-adjusted (critique 3; stops the USMV slot acting as absolute momentum);
  - exposure-matched primary control (critique 2);
  - phi repackaging caps against SPY TSMOM and RSP−SPY (critique 1);
  - CGATE-mom and STYLE8ROT added to the tally;
  - the raw-sign version kept as a measured row.
- **Q05:**
  - strict before-LTD filing cutoff; earn_dates refresh (critique 1);
  - x-earngap family member and run-up label rule;
  - active-month mechanism row and power statement.
- **Q07:** copula bounds, softmax weights and seeds pinned; delta-method LTD SE; expected negative all-month sign pre-stated; realistic compute budget; Δβ controls.
- **Q08:** new C3 lowest-R̄ control; placebo on Δβ; Q09 folded in as an arm.
- **Q09:** consistent REIT exclusion using the 2016-12 classification.
- **Q06:**
  - legs aligned with Q03;
  - GICS breaks declared, with MS/CS for six months after each break and a post-2018-10 re-estimated sub-sample.
- **Q10:** legs aligned with Q03; vol twin; QGSIZE family disclosed.
- **Q11:** joint per-year month-label permutation fully specified; sector and calendar family counts; c04 keep:false disclosed; two pre-stated sector-month predictions.
- **Q12:** fiscal-Q4 mapping through annual period ends; restatement disclosure; relabelled 'CHSS 착안 랩 변형' because the full text was not opened.
- **Q13:** Δβ statistic; graph child.
- **Q14:**
  - L2-N declared a non-investable diagnostic; adoption requires the long-only L2-LO to pass as well (critique 3's option; critique 2's 'report-only L2-LO' was not adopted because it would leave no holdable path);
  - borrow fixed at a conservative declared 1.00%;
  - power line; prerequisites listed.
- **Q15:** U4 freeze only after the ledger exists; power line; RRG-family +1.

**BATCH**
- Three-part pin (P1 940f0bda prices / P2 bef4eea8 non-price / P3 blob hashes) in place of the unrunnable 'worktree at 940f0bda' (critique 1).
- V0 targets regenerated and reproduction-asserted (they are not stored in _eg30plus.json).
- qbatch_core.py must be committed first (verified untracked).
- Priors recalibrated to power, defined as P(forward entry).

# OPEN RISKS

**1. Power**
- Even with BH at q = 0.10, Class B steps need to remove almost all of V0's −0.075%/mo down-month deficit.
- Class A needs a fund IR of about 0.75 or more over 120 months.
- The realistic batch outcome is 0-2 forward entries and 0-1 in-sample labels. This is stated in advance and should be told to the user.

**2. x-bmrot leg**
- The published record is contaminated: the EG30/B-M blend was already measured (EGBEST: IR 1.20, d −0.44%/yr, t −2.15), and the 5/6 crash / 2/6 surge split comes from the lab's in-sample EGBEST notes.
- x-bmrot is itself a macro (DFII10) switch and is equal-weighted, so COVID-type EW crashes may make it a poor defender.
- If the pre-commit reproduction fails, Q03/Q10/Q06 fall back to T-bill legs, which the lab has repeatedly shown to be exposure reduction.

**3. Data**
- Fundamentals are latest-filed until the first-filed rebuild exists. Q01/Q12 then carry a restatement leak, and only a same-sign first-filed sensitivity guards against it.
- PIT price coverage of index companies is 84.5% in 2016-08, rising to about 97.5% by 2024, with large acquired names missing. The C0 co-benchmark and the 2019-09+ check mitigate this but do not remove the bias.
- earn_dates ends 2026-08-18 and must be refreshed.

**4. Q16 evidence**
- BTZ themselves report that predictability falls sharply without high-frequency realized variance: quarterly R² 8.08% with model-free IV and daily RV, versus 15.14% with 5-minute RV.
- The window may contain a calm month followed by a crash (2020-02) that puts the sleeve into SPHB at the worst time.
- SPHB carries the high-beta anomaly drag. The static control removes it from the timing test, but not from the fund's absolute excess.

**5. Switch-family dependence**
- Q03, Q10 and Q06 share both legs, so their results will be highly correlated. The half-weight slot handles FWER but not interpretation.
- JM's λ = 50 is the paper's typical value, not a validated one.
- AR at N ≈ T is noisy.

**6. Compute and implementation**
- Q07 needs several CPU-hours and 12 copula families.
- Q02/Q13 need 41 × about 30 QPs on 500 variables with solver fallbacks.
- Q08/Q09 need own-coded centralities.
- The unit tests are the only defence against coding errors, so reviewers should read them.

**7. Library cards**
- Q14/Q15 cannot be committed until the ledger, the pivot-NAV export and the SPHB loader exist.
- Their forward bar needs IR ≈ 1.44 at 36 months, so they give no verdict before about 2029-2031.
- L2's 1.00% borrow is an unsourced conservative assumption.

**8. Residual forking risk**
- The measured arms, twins and neighbours (about 35) could be read as alternatives after the fact.
- The rule that a better-looking arm never replaces its primary must be enforced in review. Any promising arm needs a fresh registration and forward clock.

**9. Contamination**
- EG30's crash profile motivated Q02, Q03, Q07, Q08, Q10 and Q13, and x-bmrot's crash record motivated Q03's leg.
- The in-sample window 2016-2026 has been examined repeatedly by the lab. Only the forward ledger is clean.

**10. Web research limits**
- The WebSearch budget for this session is exhausted (200/200), so sources were reached by direct fetch only.
- CHSS full text, the Kritzman AR original, Gupta-Kelly and Grinold were not opened. Their cards mark what was not transferred.



# Q01 SK14 — 퀄리티 마이너스 정크 롱온리 (AFP 4기둥 · 현금흐름은 같은 회계연도 창 · 상위 30% 시총가중 · 월간)

## why_keep
- Quality has the strongest post-publication record of any theme in the pool.
- The four-pillar composite has never been built: pool card 558 is marked underspec, and only single components were measured.
- It stands alone, so it adds diversity and does not depend on EG30.
- Revised for critique 1 and critique 3:
  - All cash-flow and accrual components now come from one fiscal-year annual bucket. The earlier version mixed a TTM window with an annual one; the critic found the cfo/capex quarterly buckets hold only fiscal Q1.
  - The component set is frozen by cap coverage. GP/REV-based items drop out because they appear mid-sample.
  - Leverage now uses total liabilities; debt-tag gaps would otherwise read as issuance.
  - Fundamentals are latest-filed, not first-filed, so restatements leak; a first-filed rebuild or a mandatory sensitivity addresses this.
  - The already-measured components (x-roe, x-gpa and the others) and QG30 are disclosed.
  - The expected label is '급락형', stated honestly in advance.
  - The G4 placebo is now judged on beta-hedged excess, so low-beta tilts cannot pass by construction.
  - A priced-universe co-benchmark handles coverage drift (84% of index companies priced in 2016).

## mechanism_ko
품질주(수익성·성장·안전·주주환원이 높은 주식)는 마땅히 더 비싸야 하지만, 실제 가격 프리미엄은 작아서 위험조정 수익이 높다(Asness·Frazzini·Pedersen 2019: 미국과 24개국 중 23개국).

근본 이유는 두 가지다.
- 투자자가 복권형·고성장 서사를 가진 정크주를 과대평가한다.
- 레버리지·벤치마크 제약 때문에 기관이 안전한 우량주를 덜 산다.

위기 때는 '품질로의 도피'가 일어나 품질주가 덜 빠진다. 시총가중 상위 30% 로 담으므로, 랩 라이브러리를 가라앉힌 동일가중−시총가중 격차가 없다.

약점도 분명하다. 급락 직후 정크 랠리(예: 2020-11~2021-02)에서 크게 뒤지고, 안전 기둥(−베타·−개별변동)이 저위험 계열의 강세장 부담을 안고 들어온다. 그래서 미리 적는 정직한 기대 라벨은 '급락형'이다. 안전 기둥을 뺀 판을 측정만으로 함께 보고해, 합성이 −베타 이상을 더하는지 드러낸다.

## rule
FORMATION: every month-end m in qbatch_core.monthly_forms() (2016-08..2026-07); reb=1; holdings 2016-09..2026-08.

UNIVERSE: eg30plus.World.universe(m,'union',ex_fin=False).

FUNDAMENTALS: tech_backtest.load_fund + asof_all with a 90-day lag.
- Primary input: the first-filed fact set P-FF, if it is built before the commit. For each period and form, keep the earliest 'filed' value; the as-of date is max(period end + 90d, first filed date).
- Otherwise: latest-filed values, with the limitation declared, and the first-filed rerun becomes a mandatory G5 sensitivity.

FLOW-WINDOW RULE: every flow (NI, CFO, CAPEX) is taken from the same latest fiscal-year annual bucket (ni_a, cfo_a, capex_a) available at m. Every stock variable (EQ, ASSET, LIAB) is taken at that same fiscal-year end. A component is missing if any input is missing for that fiscal year.

COMPONENTS: each is ranked cross-sectionally among universe names with data, and the ranks are z-scored.
- PROFITABILITY:
  - ROE = NI_a/EQ
  - ROA = NI_a/ASSET
  - CFOA = (CFO_a − CAPEX_a)/ASSET
  - ACC = −(NI_a − CFO_a)/ASSET
- GROWTH (same buckets 5 fiscal years earlier):
  - ΔROE = (NI_a,y − NI_a,y−5)/EQ_y−5
  - ΔROA = (NI_a,y − NI_a,y−5)/ASSET_y−5
  - ΔCFOA = (CF_y − CF_y−5)/ASSET_y−5, where CF = CFO_a − CAPEX_a
- SAFETY:
  - BAB = −World.fp_beta (lab FP constants)
  - IVOL = −sd of 252-day daily CAPM residuals vs SPY
  - LEV = −LIAB/ASSET
  - EVOL = −sd of quarterly ROE over up to the last 20 quarters (minimum 12; Q4 NI = annual NI − Q1 − Q2 − Q3)
- PAYOUT:
  - EISS = −ln(SH_t/SH_t−1y), on the split-safe x-shiss share series (sh_u + sh_seam)
  - NPOP = Σ5y(NI_a − ΔEQ)/Σ5y NI_a (missing if the denominator ≤ 0)
- DROPPED (declared): GPOA, GMAR, ΔGPOA, ΔGMAR, DISS, Ohlson O, Altman Z.

COVERAGE FREEZE (before the commit, coverage only): at 2016-08, compute each listed component's share of union market cap with a valid value. Drop any component below 80%. For LEV only: if LIAB is below 80%, use −DEBT/ASSET when DEBT is at or above 80%; otherwise drop LEV. The frozen list and the probe-script hash go into the prereg.

AGGREGATION:
- Pillar = z-score of the mean of its available component z's (at least 2 components; payout at least 1).
- Quality = z-score of the mean of the available pillar z's (at least 3 of 4 pillars).

SELECTION: the top ceil(0.30 × N_scored) names by Quality; ties go to the larger cap.

WEIGHTS: market cap at m, 10% single-name cap, proportional water-fill.

HOLD, COSTS AND FUND: 1 month with daily drift; 10bp one-way on traded value. Fund = 90% SPY TR + 10% sleeve, reset monthly; PR reported. evaluate().

MEASURED ONLY (never promotable):
- (a) the composite without the safety pillar (3 pillars, all required)
- (b) the QUAL ETF as the sleeve
- (c) four single-pillar sleeves, for attribution

## params
- Component definitions, rank-then-z construction, the 30% breakpoint and value weighting: AFP 2019 appendix (2013 draft opened by the earlier researcher).
- BAB beta: Frazzini-Pedersen, using the lab FP constants in eg30plus.
- 90-day lag: lab convention.
- Declared implementation choices (no grid, no alternative cut):
  - annual-bucket flow windows (critic-verified: the cfo/capex quarterly buckets hold fiscal Q1 only);
  - 80% cap-coverage freeze (KNS lesson: a high-coverage axis dominates a composite);
  - LIAB leverage, which differs from AFP's total-debt definition (the KO debt tag starts only in 2023-12);
  - DISS dropped (debt-tag gaps would read as issuance);
  - EVOL window of 20 quarters (AFP use 60 months, but lab data start in 2008);
  - 10% name cap;
  - at least 3 of 4 pillars;
  - first-filed rebuild as primary when available.
- JKP's mega-cap 77.3% and large-cap 81.5% are ALL-FACTOR replication rates by size group; they are cited as such, not as quality-specific evidence.

## data
- data/fx (518 names) + data/fx_pit (145 delisted), read via tech_backtest.load_fund/asof_all.
- Coverage probes:
  - Skeptic probe at 2016-08: ni 389/530, eq 403, asset 408, cfo_a 343, capex_a 326, debt 327, sh 411.
  - Critic probe on the pinned grid at 2016-08: rev 135/433, gp 144, debt 80.6% of cap.
  - 2026-08: ni 505/518, eq 516, cfo_a 508.
- Prices, shares and FP beta come from pins P1/P2/P3 (see batch design).
- QUAL comes from assets.json.
- Raw companyfacts are needed for P-FF (refresh_facts.pick keeps the latest filed value and drops the filed date — verified at build/refresh_facts.py lines 194-217).

## controls
- C1, primary mechanism control: the cap-weighted sleeve of ALL Quality-scored names (same 10% cap and schedule). Gate: sleeve − C1 all-month NW(3) t ≥ 1.0.
- C0, coverage co-benchmark: the cap-weighted sleeve of all priced union members (same cap). Gate: sleeve − C0 all-month NW t ≥ 1.0, AND point estimate > 0 over 2019-09..2026-08.
- C2, placebo: each month, permute Quality among names within the same PIT GICS sector (1000 draws, seed 20260925), then apply the same top-30% cap-weighted rule. Two requirements:
  - the true all-month mean X is at or above the 95th percentile;
  - the true down-month mean of H (each draw hedged with its OWN sleeve beta) is at or above the 95th percentile.
- Reported:
  - hedge_ctrl;
  - holdings overlap and sleeve correlation vs QG30, EG30 and QUAL;
  - pillar attribution;
  - coverage by year.

## lab_difference
- Measured before, and disclosed as seen components (family tally at least 14):
  - QUAL ETF proxy (111, 측정만)
  - x-roe '고ROE 상위 10' (열위, Δ샤프 −0.140)
  - x-gpa (−0.089)
  - x-npm, x-poacc, x-debtiss, x-payout, x-lowbeta, x-ivol, x-reta
  - x-fscore (측정 불가, coverage)
  - 이익 변동성 최하위 10, 저부채 상위 10, 순주식발행 회피
  - QG30 = (ROE pct + Eg pct)/2, cap-weighted top 30 (fund IR 1.03, so ROE's 2016-2026 record is known)
- Different constructions: PUREGP (value leg with a profitability gate, rejected) and KNS (eight-signal shrinkage, rejected for coverage imbalance).
- This card is the first build of the four-pillar composite (pool card 558).

## implementation_notes
- Class A primary (slot A1). New module build/q_qmj.py.
- Assert that every fundamental used at m has as-of ≤ m.
- Log per month: pillar composition, N per pillar, N_scored, N held, maximum weight and turnover (expected 2-4x/yr).
- Pre-stated expectations (not computed):
  - label '급락형';
  - win 2022;
  - lose the 2020-11..2021-02 junk rally;
  - years won likely 5-7/11.


# Q02 FE1-RIEGK — RMT 정제 공분산 최적 능동 Eg 슬리브 (알파는 Eg 상위 60 후보에만 · EG30 과 같은 사전 추적오차 · BBP RIE + Grinold-Kahn)

## why_keep
- This is the lab's first rule that sizes active weights with a stock covariance matrix. idxtilt/idxrev and IDXEG are heuristic tilts with no covariance.
- Tracking error is matched to EG30 ex ante, so there is no free risk parameter.
- RMT cleaning evidence is strong and was opened: BBP 2017 Table 4 shows lower out-of-sample risk for all four predictor types.
- Revised for critique 3: alpha is nonzero only on the Eg top-60 candidate pool (the same list as Q08). The optimizer therefore resizes EG30's bet instead of turning it into a broad IDXEG-style tilt over 400 names, and a pass can be attributed to covariance sizing, not breadth.
- Revised for critique 2:
  - the primary is the beta-hedged down-month difference Δβ (the raw Δ is mechanically positive for a step that lowers beta);
  - κ_IW is renamed and its estimator pinned;
  - the bisection bracket, solver tolerances and fallbacks are pinned;
  - the C2 mechanism gate is a point comparison on Δβ.
- Revised for critique 1: TE* has a declared fallback for EG30 names outside the risk set.

## mechanism_ko
EG30 은 Eg 상위 30 을 시가총액 비중(상한 20%)으로 담는다. 이 비중은 종목 간 상관을 보지 않는다. 그래서 바스켓 능동위험의 대부분이 Eg 신호가 아니라 시장 모드(바스켓 베타 1.22)와 초대형 성장주 한 덩어리에 쌓이고, 하락장에서 상관이 오르면(Longin-Solnik 2001) 그 덩어리가 한꺼번에 빠진다.

Grinold-Kahn 최적 능동비중 x ∝ Σ⁻¹α 는 같은 추적오차 예산을 보상받는 위험(Eg)에만 쓰고, 보상 근거가 없는 공통 모드 노출은 비싸게 쳐서 줄인다.

걸림돌은 약 500종 × 1000일 표본 상관행렬의 작은 고유값이 잡음이라는 점이다. 그래서 회전불변 추정(RIE)으로 정제한다. 알파는 EG30 과 같은 Eg 후보 60 에만 주고 나머지 종목은 벤치 비중에서 빼는 재원으로만 쓴다. 무엇을 사느냐(Eg 후보)는 그대로 두고, 얼마나 사느냐만 정제된 공분산으로 푸는 단계다.

## rule
BASE: identical to EG30 V0 (EG_BASE):
- Eg 'pitgics' scores, union universe, ex_fin=False;
- formations 2016-08 plus every quarter-end month (41 formations); holdings 2016-09..2026-08.

(1) U_t = World.universe(m,'union',ex_fin=False). Benchmark w_b = PIT S&P 500 cap weights inside U_t; NDX-only names get w_b = 0.

(2) R_t = names with at least 750 valid returns in the last 1000 days and at least 120 in the last 252.

(3) Y: T = 1000 daily returns ending at the formation date. Demean each series; divide by the cross-sectional daily scale sqrt(Σ_j r_jt²) over names with data that day; standardize each series; missing = 0. E = YY'/T, q = N/T.

(4) IWs-RIE (BBP Algorithm 1):
- z_i = λ_i − i·N^−1/2;
- g_i = (1/(N−1))·Σ_{j≠i} 1/(z_i − λ_j);
- ξ_i = λ_i/|1 − q + q·z_i·g_i|²;
- for λ_i < 1, apply the Γ_i correction with the inverse-Wishart transform at κ_IW = 2λ_N/((1 − q − λ_N)² − 4qλ_N), where λ_N is the smallest sample eigenvalue (BBP §8.1.2);
- isotonic-sort ξ into λ order ('IWs'); rescale to trace N.
- Ξ = U diag(ξ) U', renormalized to unit diagonal.

(5) σ_i = √252 × sd of the last 252 daily log returns; Σ = diag(σ) Ξ diag(σ).

(6) P60_t = the top 60 names by Eg under EG_BASE ranking and eligibility.
- z_i = cross-sectional z of Eg over scored R_t names, winsorized at ±3 and re-standardized.
- ω_i = √252 × residual sd from a 252-day OLS of r_i on S&P 500 PR daily returns.
- α_i = ω_i·z_i for i ∈ P60_t ∩ R_t; α_i = 0 otherwise.

(7) Maximize α'x − (κ/2)x'Σx subject to x_i ≥ −w_b,i, Σx = 0, and x_i = 0 for i ∉ R_t. w = w_b + x (long-only, fully invested).
- Solver: SLSQP with analytic gradient, ftol 1e-12, maxiter 2000.
- If that fails: trust-constr (gtol 1e-10, maxiter 5000).
- If both fail: hold EG30 targets at that formation and flag it.

(8) TE*_t = sqrt((w_EG30 − w_b)'Σ̃(w_EG30 − w_b)). Σ̃ extends Σ to EG30 names outside R_t:
- correlation = the mean off-diagonal Ξ among R_t names of the same PIT GICS sector (the market-wide mean if the sector has fewer than 5 names);
- σ from the available daily returns in the last 252 days (at least 60; otherwise the sector median σ).
- Bisect log10 κ ∈ [−4, 6] until |TE(x) − TE*| ≤ 1e-4 (at most 60 steps). If TE* is unreachable, use the smallest κ and flag it.

(9) Buy-and-hold drift between formations; 10bp one-way; fund 90/10 reset monthly vs SPY TR (PR reported).

MEASURED ONLY (never promotable): C3 uncleaned sample correlation; A1 Laloux clipping at (1+√q)²; A2 Ledoit-Wolf 2020 nonlinear shrinkage.

## params
- T = 1000, roughly 60-day holding, normalization (eq. 8.13), η = N^−1/2, IW regularization with κ_IW and sorting: BBP 2017 §8 (opened).
- Minimum observations 750/1000 and 120/252, and the 252-day vol: lab FP constants.
- Winsorize at ±3: lab EG30PLUS S1.
- α = ω·IC·z: Grinold 1994 (metadata only). IC cancels because TE is matched.
- Pool 60 = 2 × basket: the declared EG-step pool, shared with Q08 and not tuned.
- TE target: defined by the incumbent.
- Declared implementation choices: sector-mean correlation fallback; solver tolerances, bracket and fallbacks.
- No name cap: report maximum weight and the Herfindahl index.

## data
- Union members per formation: 443 (2016-08) to 515 (2026-07); 94-99% have at least 90% valid prices over 252-1260 days.
- data/_eg_q5_scores_pitgics.json covers 2016-08..2026-07 (about 398 scored names per month).
- bench_px spx daily from 2006.
- scipy 1.18.1 and numpy 2.5.3 installed; cvxpy not needed.
- Pins P1/P2/P3.
- EG30 V0 targets are regenerated (they are NOT stored in data/_eg30plus.json).

## controls
PRIMARY (G1): the down-month mean of Δβ_t = (X_FE1,t − X_V0,t) − 0.1·(β̂_FE1 − β̂_V0)·(SPYTR_t − rf_t), over the 39 PR-down months. Test with eg30plus.down_t (calendar HAC, Bartlett 3); p from t(38), one-sided.

G3 POINT CONDITIONS:
- raw down-month mean Δ ≥ 0;
- M1: FE1's down-month mean X > that of V0 diluted to FE1's annual excess (eg30plus.dilution);
- efficiency floors: IR ≥ 0.72, excess ≥ +0.38%/yr, TE ≤ 1.20%, turnover ≤ 272%/yr. A turnover breach means 기각 (a declared cost).

G4 MECHANISM: C2 is the same optimizer with Ξ = I. Required: the down-month mean of Δβ(FE1 − C2) > 0 (point).

REPORTED: IDXEG as an already-seen relative (IR 0.46-0.60); realized vs ex-ante TE; basket beta; maximum weight; overlap with EG30.

## lab_difference
- '149 축소 공분산 최소분산 (Ledoit-Wolf 목표) | 측정만' is absolute minimum variance over 8 assets with no alpha.
- '401 HRP' weights by risk and carries no signal.
- IDXEG and IDXTILT are heuristic w_b + λz tilts with no covariance (IDXEG: the same Eg signal, IR +0.46-0.60, already seen, counted as a relative).
- EG30PLUS B1 capped beta inside the same 30 names and lost to the cash hedge.
- FE1 is the first covariance-optimal sizing of the Eg bet in the lab.

## implementation_notes
- Class B step, slot B1 (initial weight 1/8). Parent of Q13 (graph edge weight 1).
- New module build/q_riegk.py: RIE is about 40 lines; a 500-variable QP runs inside the κ bisection.
- Unit test: RIE on a synthetic identity-population Wishart gives ξ ≈ 1.
- Pre-stated: the down-month Δβ must exceed about 0.075%/mo just to clear the first BH step. It is realistic only if the step removes most of V0's deficit (power line in the batch design).


# Q03 SF3-JM-ENGINE — 통계적 점프모형 공격·수비 엔진 교체 — S&P 500 하방위험·소르티노 국면이 하락이면 EG30 → B/M 금리 국면 로테이션(x-bmrot) (λ=50 · 1일 지연)

## why_keep
- Revised as critique 3 required: the defensive leg is now the lab's crash-side engine x-bmrot (B/M 금리 국면 로테이션; BMROT-RESULT, six conditions passed, 측정만), not T-bills.
- This directly tests the user's stated goal: switching strategies on a signal, with offense and defense.
- The EGBEST blend table shows active correlation −0.52 between EG30 and x-bmrot (verified, EGBEST-RESULT line 42).
- The lab's 2026-09-24 EGBEST notes record EG30 at surges 5/6 · crashes 0/6 and B/M rotation at crashes 5/6 · surges 2/6. These records are in-sample and contaminated, and this is disclosed.
- The cash leg only reproduced exposure reduction (EG30PLUS, VOLMOM). An engine switch asks the question that remains open: can a persistence-penalized regime model time two engines that both have positive expected returns?
- The jump model keeps the strongest out-of-sample evidence of the regime rules (Shu-Yu-Mulvey 2024, opened).
- Following critique 2, the primary is now the ALL-month difference vs the exposure-matched static blend, with a studentized segment-shuffle p-value. A down-month statistic would be mechanically favoured by any vol-correlated state.
- It shares one F-Q slot with Q10 at half weight, so the switch family spends one slot's alpha.

## mechanism_ko
주식시장 수익 분포는 몇 달에서 몇 년 지속되는 국면으로 나뉜다. 평온한 상승 국면과 고위험 하락 국면이고, 전환 뒤에는 새 행동이 여러 기간 이어진다(Ang·Timmermann 2012).

통계적 점프모형은 하방편차와 소르티노 비율로 두 국면을 군집한다. 국면이 바뀔 때마다 벌점 λ 를 매기므로 HMM 의 짧은 가짜 국면(휩쏘)을 억누르고, 연 1회 안팎으로만 전환한다.

랩 기록에서 두 엔진은 서로의 약점을 메운다.
- EG30(기대투자성장 상위 30, 바스켓 베타 1.22)은 급등 국면의 공격 엔진이다.
- x-bmrot(가치·성장 절반을 실질금리 변화로 기울인 동일가중 바스켓)는 하락 국면의 수비 엔진이다. 둘의 능동수익 상관은 −0.52 다.

하락 국면에서는 레버리지 축소와 위험예산 매도가 연쇄되어 고베타·고성장 바스켓이 가장 크게 잃는다. 그 구간에만 수비 엔진으로 옮기고 상승 국면에 공격 엔진으로 돌아오면, 섞어 두는 것(두 엔진의 약점을 늘 반씩 떠안는 것)보다 양쪽 구간에서 모두 낫다는 것이 이 교체 단계의 근거다. 판정은 같은 평균 비중의 고정 혼합 대비로 하므로, 오직 국면 판단의 정보만 잰다.

## rule
INPUT: R_t = SPY adjusted-close daily return − rf_t (rf_monthly DGS3MO for that month, prorated by trading days), from 2006-01-04.

FEATURES at close t (EWM with halflife h trading days, adjust=True):
- DD10 = sqrt(EWM_h10[R²·1{R<0}])
- SOR20 = EWM_h20[R]/sqrt(EWM_h20[R²·1{R<0}])
- SOR60 = the same with h = 60
- Features are used from 2007-01-03.

FITS: on the first trading day of each January and July from 2016-07-01.
- Training days = max(2007-01-03, 3000 trading days back) through the prior day.
- Standardize each feature by its training mean and sd.
- Minimize Σ½‖x_t − θ_{s_t}‖² + λΣ1{s_t ≠ s_t−1}, with λ = 50 and K = 2.
- Coordinate descent: the θ-step takes state means; the S-step is Viterbi DP.
- 10 k-means++ initializations (seeds 20260925+j); keep the lowest objective; stop when S is unchanged or after 100 iterations.
- BULL = the state with the higher cumulative training excess return.

ONLINE: each day t, with θ and the standardization fixed, run the DP over the last L feature days (L = the current training length) and take the final state.

LEGS: two shadow books run continuously on pins P1/P2/P3.
- OFFENSE = EG30 V0 (regenerated targets, daily drift).
- DEFENSE = x-bmrot PIT, regenerated in build/q_bmrot_leg.py exactly per PREREG-2026-09-03-BMROT §1:
  - each month-end, B/M = EQ/mcap over scorable union names;
  - split at the median; equal weight within each leg;
  - if the DFII10 3-month change is ≥ +0.20pp: value 70 / growth 30; if ≤ −0.20pp: 30/70; otherwise 50/50;
  - monthly rebalance, daily drift.

POSITION: the state at close t applies from close t+1 (1-day delay).
- BULL → the sleeve earns the OFFENSE book's daily return.
- BEAR → the sleeve earns the DEFENSE book's daily return.
- Each switch charges 10bp × sleeve value on the book sold plus 10bp on the book bought, plus the active book's own turnover.

FUND: 0.9 × SPY TR + 0.1 × sleeve, reset at month-ends. An intramonth switch acts on the sleeve's current value.

FALLBACK: OFFENSE before the first fit, or if a fit fails.

PRE-COMMIT REPRODUCTION GATE (not a candidate computation):
- The regenerated x-bmrot monthly returns must match the published PIT x-bmrot series (pinned by blob hash) within max |Δ| ≤ 1bp/month over 2016-09..2026-08.
- If they do not, the prereg names the T-bill leg as the DEFENSE leg before the commit.

MEASURED ONLY (never promotable):
- (a) T-bill DEFENSE leg
- (b) JM state sampled at month-ends (monthly switching)
- (c) the sma200 and vol twins (below)

## params
- Features, halflives, K = 2, loss, coordinate descent with 10 runs, bull labeling, 3000-day window, 6-month refits, online DP, 1-day delay and 10bp: Shu-Yu-Mulvey 2024 (opened), Table 2 and §3-4.
- λ = 50: the paper's stated typical value. The paper's validated λ needs 12y of training plus 8y of validation, which lab data from 2006 cannot supply (declared deviation, no grid).
- Window expands until 3000 days exist: forced by data.
- DD as the square root of the EWM negative second moment: implementation reading.
- x-bmrot rule, thresholds ±20bp and tilt ±20pp: PREREG-2026-09-03-BMROT (the pool card's numbers, lab-registered).
- Engine legs: lab design, sourced to the user's switching goal and to EGBEST.
- Round-trip 20bp per switch: the lab's 10bp one-way on each side.
- Nothing tuned.

## data
- assets.json SPY/^GSPC daily 2006-01-03..2026-09-23 (5213, verified); rf_monthly.
- EG30 V0 is regenerated via eg30plus.World.weights(EG_BASE, m) on pins P1/P2/P3.
- x-bmrot:
  - rule in tech_backtest.py lines 5353-5362 and 8081-8085 (B/M = eq/mcap);
  - PIT variant listed in pit_backtest.py line 275;
  - published series t-x-bmrot in strategy_charts.json (dates, nav);
  - DFII10 in assets.json macro.
- No JM or HMM code exists in build/; a numpy implementation (about 150 lines) is needed.

## controls
PRIMARY STATISTIC:
- Δ^D_t = X_rule,t − X_D,t over all 120 months.
- D = the static blend ē·OFFENSE + (1−ē)·DEFENSE, where ē is the rule's realized share of trading days in BULL. D is rebalanced at month-ends, with 10bp on traded value plus each leg's own turnover.
- p = (1 + #{t_perm ≥ t_obs})/10001, where t is the NW(3) t of mean Δ^D.
- Permutation (studentized segment shuffle, 10,000 draws, seed 20260925): permute the bull-segment lengths and the bear-segment lengths separately, then re-interleave them starting from the true initial state. This preserves alternation, switch count and ē.

GATES:
- (a) down-month mean Δ^D > 0;
- (b) the placebo percentile of the down-month Δ^D is at or above 95;
- (c) sma200 TWIN: the same legs switched by ^GSPC close < 200-day SMA (lab t-sma200), same delay and costs. The rule − twin must be > 0 on the all-month AND the down-month mean. Otherwise the label is '추세 게이트 재포장'.
- (d) ē-matched VOL TWIN: DEFENSE when SPY's 63-day realized vol is at or above its expanding quantile at level ē (from 2006-04). Same requirement as (c). Otherwise the label is '변동성 타이밍 재포장'.
- (e) down-month mean X > the down-month mean of V0 diluted to the rule's annual excess (eg30plus.dilution);
- (f) REBOUND-MISS: over SURGE-M months that begin within 63 trading days after a BULL→BEAR switch, the mean Δ^D must be ≥ 0 when there are at least 3 such months (otherwise reported only). The VOLMOM lesson predicts a negative value for the T-bill arm; for the engine leg the prediction is about 0.
- (g) F0: at least 12 months with ≥ 50% BEAR days and at least 6 such down months; otherwise 측정 불가.

ALSO REPORTED: V0 itself; the T-bill arm; the paper-comparable SPY/T-bill 0/1 statistics (reproduction check: fewer than 1 shift per year expected).

## lab_difference
- Timing gates measured so far: 200일 이동평균 (Faber), 200일선 + 확인 지연 5일, 하방 변동성 타깃 (K4 무의미), 이지스 1판, 풍향계.
- De-risking switch family (at least 6 prior trials plus this batch's 3):
  - QGSIZE '국면으로 비중을 줄이는 판(우량성장30)', rejected F1/F5 (caught 2 of 14 negative quarters);
  - c06-stress-fund and c11 SJM, both critic-dropped;
  - VOLMOM (placebo 2.6th percentile), AEGIS, t-voltgt/t-volreg;
  - unregistered M9, an sma200 switch between two engines.
- Pool card 591 actually measured a 6-month-winner switch (rotation_pool D6).
- EGBEST measured the static EG30½ + B/M½ blend: IR 1.20, d −0.44%/yr, t −2.15. That blend is this card's control, and its result is already seen.
- This is the first persistence-penalized regime model in the lab, and the first switch between two positive-expectation engines judged against their exposure-matched blend.

## implementation_notes
- Class S (switch), slot S1 shared with Q10 (initial weight 1/16 each).
- New modules build/q_jump.py and build/q_bmrot_leg.py.
- Unit-test the DP and coordinate descent on a synthetic 2-state series. Report all 10 objective values per fit.
- Log shifts per year, bear days, and the x-bmrot tilt state during bear spells.
- Pre-stated expectations (not computed):
  - it should fix 2022;
  - COVID is uncertain (x-bmrot is equal-weighted and value-tilted, and EW fell hard in 2020-03);
  - re-entry lag risks the 2020-04..06 and 2025-05 surges.
- Power: with ē about 0.8, off-state months are about 24.


# Q04 Q-TSFM12 — 팩터 ETF 시계열 모멘텀 (베타 조정 12개월 초과 부호 · 칸 고정 1/4 · 진 칸은 SPY)

## why_keep
- Planned strategy #1, and the first build of pool card E37 (649, underspec).
- The time-series claim has never been tested. STYLE8ROT (434/435) was a cross-sectional top-N/2 rule with a 12-1 skip.
- Ehsani-Linnainmaa (opened) show time-series momentum subsumes cross-sectional, not the reverse.
- Revised for critique 3: the signal is now the BETA-ADJUSTED 12-month active excess return, ETF − β̂·SPY in excess-return terms.
  - Reason: for β ≠ 1 ETFs (USMV β ≈ 0.7), the raw ETF − SPY sign mostly flips with the market's own 12-month return. That would repackage the rejected absolute-momentum family ('182', '59').
  - The adjustment makes the slot signal the long-only analogue of a market-neutral factor return.
- Revised for critique 2: the primary control is exposure-matched (f̄·EW4 + (1 − f̄)·SPY).
- Revised for critique 1: phi repackaging diagnostics against SPY TSMOM and the RSP−SPY sign are declared label caps.

## mechanism_ko
팩터 수익은 한 달로 끝나지 않고 몇 달에서 1년 가까이 이어진다(Ehsani·Linnainmaa: 지난 1년이 플러스였던 팩터의 다음 달 수익은 51bp, 마이너스였던 팩터는 6bp). 이유는 투자심리와 느린 자본 이동 때문에 생긴 가격 괴리가 천천히 되돌아오는 과정, 그리고 최근 잘한 팩터로 뒤늦게 몰리는 롱 편향 자금이다.

롱온리 ETF 에서 팩터 수익을 제대로 재려면 시장 베타 몫을 빼야 한다. 그래서 신호는 'ETF 초과수익 − β̂ × SPY 초과수익'의 12개월 합이다. 이것이 양인 팩터에만 칸을 주고, 음인 팩터의 칸은 지수로 돌린다. 패자의 이후 프리미엄은 0 근처(연 0.28%)라 진 칸을 SPY 로 두어도 잃는 것이 없다.

베타를 빼 두었으므로 '약세장 뒤 저베타 ETF 가 자동으로 켜지는' 절대 모멘텀 재포장이 아니라, 팩터 자체의 국면 지속성만 사는 규칙이다.

## rule
UNIVERSE: VLUE, SIZE, QUAL, USMV (the iShares MSCI USA single-factor family, minus MTUM). Base asset: SPY.

FORMATION: at each month-end m in monthly_forms() (2016-08..2026-07), using assets.json adjusted closes at A.me[].
- e_i,k = A.monthly(i,k) − rf_k and e_SPY,k = A.monthly(SPY,k) − rf_k (rf_monthly).
- β̂_i,m = OLS slope of e_i on e_SPY over months m−35..m (36 observations; the first formation uses 2013-09..2016-08, and all four ETFs are complete).
- S_i(m) = Σ_{k=m−11..m}[e_i,k − β̂_i,m·e_SPY,k] (includes month m; no skip).

WEIGHTS: w_i = 1/4 if S_i > 0, else 0; w_SPY = 1 − Σw_i. No cash, leverage or shorts.

EXECUTION: decide(m) returns the full target every month. qbatch_core.etf_path trades at the close of me[m], with cost 0.0010 on all traded value including SPY lines and drift resets.

FUND: fund_from_path, TR and PR; holdings 2016-09..2026-08; evaluate().

MEASURED ONLY (never promotable; counted in the trial tally):
- (a) Q-TSFM1: the same rule with a 1-month formation, S_i(m) = e_i,m − β̂_i,m·e_SPY,m;
- (b) the raw (unadjusted) 12-month ETF − SPY sign version.

## params
- Four ETFs by an external family rule. MTUM excluded because E&L exclude UMD.
- 12-month formation, sign at 0, monthly rebalance, 1-month hold: E&L 2019 Table 2/A2 (opened).
- No skip-month: E&L; Falck-Rej-Thesmar.
- β-adjusted excess active return: implementation, declared. It is the long-only analogue of E&L's long-short factor returns, answering critique 3.
- 36-month β window: implementation (the lab's 3-year fund-statistics convention).
- Fixed 1/4 slots: implementation (per-factor signs are independent).
- Loser slot → SPY: E&L, 'inconsequential'.
- No vol scaling: Gupta-Kelly specifics unverified.
- Nothing tuned.

## data
- assets.json first dates: VLUE 2013-04-18, SIZE 2013-04-18, QUAL 2013-07-18, USMV 2011-10-20, SPY 2006-01-03; all end 2026-09-23 with no gaps.
- The β window at the first formation needs 2013-09 onward, which is available for all four.
- rf_monthly from 1981-09.
- qbatch_core Assets, etf_path, fund_from_path and evaluate are verified.

## controls
PRIMARY (G1, Class A): the all-month fund excess X vs SPY TR, NW(3) t, p from t(119).

G4:
- (a) exposure-matched control: f̄·EW4 + (1 − f̄)·SPY reset monthly with 10bp, where f̄ = the rule's realized mean factor share. Required: rule − control all-month NW t ≥ 1.0.
- (b) count-matched random placebo: each month, hold the same number of ETFs chosen at random (1000 draws, seed 20260925). The all-month mean X must be at or above the 95th percentile.
- (c) REPACKAGING CAPS: for each slot, the phi correlation of its on-state with sign(SPY 12m − rf 12m) and with sign(RSP − SPY 12m). If any phi exceeds 0.8, the label is capped at 측정만.

G3: down-month mean X ≥ 0 AND down-month mean H > 0.

REPORTED: static EW4; hedge_ctrl; the distribution of winner counts; share of months at 100% SPY; turnover.

## lab_difference
- '434/435 스타일 8종 / 표준 8종 팩터 모멘텀 로테이션 | 기각' were cross-sectional (always 4 of 8, 12-1 skip, PIT rebuilt legs, judged vs EW).
- '139 국면 연동 팩터 로테이션 (A2)' and '18/26/27 팩터 전환' switch on macro, VIX or 200-day states.
- '59 섹터 시계열 모멘텀' and '182 절대 모멘텀 (SPY 12-1)' use absolute signs.
- CGATE-mom (EW−CW momentum; Δ +0.150, t 2.10 already seen) and STYLE8ROT are added to the family tally (at least 6).
- This rule is per factor, time-series, beta-adjusted, with SPY as the off state.

## implementation_notes
- Class A (planned), slot A2 (initial weight 1/8). About 40 lines on qbatch_core.
- Fund TE will be tiny, so power is disclosed (IR ≈ t/√10).
- Run the neighbor and the raw-sign row in the same bake.


# Q05 B-EAP1 — 실적발표 예정월 프리미엄 (Frazzini-Lamont 원문 규칙 · 시총가중 · 얇은 달은 지수)

## why_keep
- Event-calendar timing is orthogonal to every characteristic-sorted engine in the library.
- The rule follows the full text of FL (NBER w13090, opened): the t−12 month predictor, exactly 4 announcements, value weighting, and a 1-month hold.
- It resolves pool card 620 without inventing defaults.
- The data are PIT: earn_dates has 795 companies and 54,125 dates, including delisted CIKs; t−12 precision is 92.7%.
- Revised for critique 1:
  - only filings dated strictly before m's last trading day count;
  - earn_dates is refreshed before the forward clock starts;
  - x-earngap, the lab's PIT pre-announcement-window basket (gross Sharpe 0.936), is disclosed as a family member and used as a '런업 재포장' label check.
- Revised for critique 2: the active-month-only mechanism row and the power reduction (80 of 120 months active) are stated.

## mechanism_ko
실적발표가 예정된 달에는 주가가 체계적으로 오른다. 경로는 셋이다.
- 주의와 수급: 발표 무렵 개인 매수와 거래량이 몰리고, 대형 투자자가 이를 앞서 산다.
- 위험 보상: 발표가 시장 전체 이익 정보를 담으므로 그 달 발표 기업의 체계적 위험이 커진다(Savor-Wilson 2016: 연 9.9%).
- 불확실성 해소 보상: 발표 무렵 풀리는 정보 불확실성에 대한 보상이다(Barber 외 2013, 46개국).

모든 종목이 1년에 네 번 들어오고 나가므로 가치·규모·베타에 쏠리지 않고 발표 시점만 산다.

반대 증거도 무겁다. 2004년 8-K 개정 뒤 미국 프리미엄이 8-K 접수일로 옮겨가 사라졌다는 워킹페이퍼가 있다(Heitz 외). 이 슬리브는 그 논쟁을 2016~2026 S&P 500 대형주에서 가르는 검정이다.

## rule
UNIVERSE: at each month-end m (formation 2016-08..2026-07, holding t = m+1), the PIT S&P 500 list for m.
- pit_panel.union_members filtered to W['lists']['spx'][m]: one line per company, date-aware price key, all sectors.
- A name needs price > 0 on m's last trading day and PIT shares.

RECORD: data/earn_dates.json 'co', looked up by list ticker, then price key, then dotted form, then cik_spliced. A name with no record is never an expected announcer.

EXPECTED ANNOUNCER for month t requires both:
- (i) at least one 8-K Item 2.02 filing dated in calendar month t−12;
- (ii) exactly 4 distinct 2.02 filing dates in calendar months t−12..t−1.
- Only filings dated STRICTLY BEFORE the last trading day of m count.
- Assert that every date used is < LTD(m).

SELECTION: if there are at least 30 expected announcers, hold all of them. Otherwise the sleeve holds every universe member cap-weighted, which carries zero active bet (expected in Mar/Jun/Sep/Dec, 40 of 120 months).

WEIGHTS: market cap at m, 20% single-name cap, pro-rata water-fill (qg_lab.weights).

HOLD AND FUND: rebalance at the close of m (reb=1) and hold to the close of t; 10bp one-way. Fund 90/10 reset monthly vs SPY TR (PR reported).

DISCLOSE: active months; realized turnover vs the 10x cap; names per month; maximum weight before and after the cap; prediction precision.

## params
- t−12 predictor, exactly-4 restriction, value weighting, 1-month hold from the last trading day of t−1: FL 2007 §II and Table III (opened).
- 8-K 2.02 date as the announcement proxy: lab data constraint.
- Strict before-LTD cutoff: implementation, removes same-day look-ahead.
- S&P 500 universe: lab benchmark.
- Minimum 30 names, otherwise the cap-weighted universe: implementation (lab basket threshold; FL's diversification argument).
- 20% cap: qg_lab default.
- Nothing tuned.

## data
- data/earn_dates.json: EDGAR 8-K Item 2.02, 2008+, 795 companies, 54,125 dates, ending 2026-08-18. Also present in commit bef4eea8; pinned by blob hash.
- Coverage 96.9-97.5% of priced members per month. The critic found one missing at 2022-08 (SBNY).
- The exactly-4 filter keeps about 75-82%.
- Prices and shares from pins P1/P2.

## controls
PRIMARY (G1, Class A): all-month X vs SPY TR, NW(3) t.

G4 MECHANISM:
- the non-announcer basket: S&P 500 members NOT flagged, same cap weighting, cap and months (in thin months it equals the sleeve's universe). Required: sleeve − control mean > 0 with NW t ≥ 1.0.
- '런업 재포장' LABEL: build the month-end x-earngap snapshot basket (members at least 60 trading days after their last 2.02 filing at m, cap-weighted). Regress (sleeve − universe) on (snapshot − universe). If the intercept point estimate is ≤ 0, the label is capped at '발표 전 런업 재포장 — 측정만'.

G3: down-month mean X ≥ 0 AND down-month mean H > 0.

REPORTED:
- the active-month-only (80 months) sleeve − non-announcer mean and t (the power loss of about √(2/3) is stated);
- C0 = the all-member cap-weighted basket;
- hedge_ctrl.

## lab_difference
- '620 EXPLORATION POOL | 실적발표 프리미엄 | underspec' is this card.
- Family (tally at least 5):
  - x-earngap '실적 공백기 (발표 후 60일 지난 종목만)' — PIT, gross Sharpe 0.936, 122.7x turnover, results seen;
  - '301 PEAD 상위 십분위', 'PEAD 2판', '663 발표 타이밍 주의분산', EVENT E3 (unregistered).
- This rule is pre-event and uses only predicted months.

## implementation_notes
- Class A, slot A3 (initial weight 1/8). Parent of Q12 (graph edge weight 1). New module build/q_eap.py.
- Expected one-way turnover is about 9x/yr, so report the 20bp row prominently.
- Refresh earn_dates before the forward clock starts. A stale record means 측정 불가 for forward months.


# Q06 SF2-CORRSURP — 상관 놀람 교체 — 크기와 상관이 함께 놀란 달 뒤에만 EG30 → x-bmrot (Kinlaw-Turkington 2014) · 측정만

## why_keep
- Moved OUT of the confirmatory family (critiques 2 and 3). With about 11 signal months, about 4 of them down months, even an oracle's down-month t is about 2.1, and all-month power is capped by about 11 active months.
- Still built and reported: it is the sharpest falsifiable sign-pattern hypothesis in the switch family. The paper predicts joint high MS & CS > 1 is worst, then MS-only, then MS & CS ≤ 1.
- It is counted in the trial tally.
- It uses the same engine legs and exposure-matched control as Q03/Q10.

## mechanism_ko
터뷸런스(마할라노비스 거리)는 크기 놀람과 상관 놀람으로 나뉜다. 그러면 변동성 큰 달을 두 종류로 가를 수 있다. 모두 같이 떨어진 달(전형적 상관)과, 평소 같이 움직이던 업종이 갈라진 달(상관 붕괴)이다.

- 전형적 상관의 급락은 유동성 고갈·강제매도 성격이라 뒤에 반등 보상이 붙기 쉽다.
- 상관 붕괴는 정보가 업종 사이로 천천히 번지는 중이거나, 과거 상관을 믿은 위험모형이 깨져 추가 위험축소가 이어진다는 신호다.

Kinlaw·Turkington(2014)에서 둘이 함께 높은 달 다음 달 미국 주식은 연 2.5%, 크기만 높은 달 다음 달은 10.8% 였다. 이 규칙은 '갈라지며 흔들린 달' 뒤에만 수비 엔진으로 옮긴다.

## rule
ASSETS: the 9 original SPDRs (XLB XLE XLF XLI XLK XLP XLU XLV XLY), daily simple returns; n = 9.

ESTIMATION: for each day t ≥ 2009-01-02, equal-weighted μ and Σ over the window ending t−1. The window uses all days since 2006-01-04, at least 756 and at most 2520.

SCORES:
- TURB = (y−μ)'Σ⁻¹(y−μ)/n
- MS = (y−μ)'diag(Σ)⁻¹(y−μ)/n
- CS = TURB/MS

MONTHLY: MonthMS = mean MS over the month; MonthCS = Σ CS·MS / Σ MS.

SIGNAL: HighMS_m = MonthMS_m ≥ the 80th percentile of {MonthMS_k, 2009-01 ≤ k ≤ m} (expanding; false until 36 months exist). Signal_m = HighMS_m AND MonthCS_m > 1.

POSITION: if Signal_m, the sleeve for m+1 is the DEFENSE book (x-bmrot, or T-bills if the Q03 reproduction gate fails); otherwise OFFENSE (EG30 V0).

COSTS AND FUND: 10bp each side per switch; fund 90/10.

ARMS: T-bill DEFENSE; twin T1 = HighMS only; twin T2 = HighMS & CS ≤ 1.

## params
- Division by n, MS with diagonal Σ, CS = TURB/MS, the 3y→10y window excluding day t, monthly aggregation, the 80th percentile with CS > 1, 1-month hold: Kinlaw-Turkington 2014 (opened, open access).
- Expanding percentile and 36-month minimum: implementation.
- 9 SPDRs instead of 10 GICS indices: declared.

## data
- assets.json: 9 SPDRs, 5213 daily closes, 0 missing.
- About 213 monthly MS/CS values before 2026-08.
- EG30 and x-bmrot legs as in Q03.

## controls
All measured only; no gate decides anything:
- all-month and down-month Δ^D vs D (the same construction as Q10);
- T1 and T2 twins;
- segment-shuffle percentile.

GICS breaks (2016-09 XLRE, 2018-09 communication services, 2023-03 V/MA) are declared. Report MS/CS for the six months after each break, and a sub-sample re-estimated from 2018-10 data only.

F0: fewer than 6 signal months → 측정 불가.

## lab_difference
- Turbulence was never implemented (grep 0).
- t-disp is cross-sectional dispersion without covariance.
- The vol-timing family (저변동성 국면, VIX 게이트, 하방 변동성 타깃, VOLMOM) is reproduced by T1.
- Unregistered c05/c06 would be the same family.

## implementation_notes
- Measured only (class M; outside F-Q; counted in the trial tally and the DSR N). New module build/q_corrsurp.py.
- Unit test: CS ≡ 1 when Σ is diagonal.


# Q07 FE2-LTDSWAP — 코퓰러 폭락 민감도(LTD) 교체 — 베타로 설명되지 않는 하방 꼬리 동조가 큰 Eg 종목을 걸러낸다 (Eg 상위 45 → 30)

## why_keep
- Copula tail dependence has never been used in the lab.
- Residualizing LTD on beta answers DNBETA ('하방 베타는 베타의 다른 이름이다') directly.
- It has the strongest economic reason of the co-crash screens: CRW 2018, full working paper opened, show that crash sensitivity is priced. The lab window 2016-2026 is entirely after their sample.
- Kept as a confirmatory hypothesis, but critique 3 asked for only one slot between Q07 and Q08. It therefore shares slot B2 with Q08 at half weight each, so the two estimators of one idea spend one slot's alpha.
- Revised for critique 3: the expected sign is pre-stated. The all-month Δ vs V0 is expected to be < 0 because the step pays the LTD premium, so it must beat dilution on down months to pass.
- Revised for critique 2: the copula parameter bounds and the starting seeds are pinned, and the primary and every control are on Δβ.
- Revised for critique 1: the compute budget is realistic, the IAD is vectorized, and LTD standard errors are reported.

## mechanism_ko
보통 베타는 평소의 선형 동조만 잰다. 폭락일에만 시장과 함께 무너지는 성질(하방 꼬리 의존, LTD)은 코퓰러로 따로 잰다. CRW(2018)는 LTD 가 베타·하방베타·공왜도·공첨도와 구별되고, 직전 12개월 LTD 가 약했던 종목이 극단적 하락장에서 유의하게 덜 빠진다는 것을 보였다.

이 단계는 LTD 를 FP 베타에 회귀한 잔차, 곧 베타로 설명되지 않는 꼬리 동조만 쓴다. 바스켓 베타는 거의 그대로이므로 급등 포착은 지키고 폭락일 동반 붕괴만 줄인다. LTD 와 상방 꼬리 의존의 상관은 0.15 로 낮아, 급등의 원천인 상방 꼬리는 대체로 남는다.

대가는 분명하다. 강한 LTD 종목은 연 4.32% 를 더 번다. 이는 위기를 싫어하는 투자자가 치르는 보험료다. 그래서 전체 기간 평균은 V0 보다 낮을 것으로 미리 적고, 판정은 그 보험료가 '바스켓 덜 들기'보다 싼지로 한다.

## rule
BASE: EG30 V0 (EG_BASE: Eg pitgics, union, ex_fin=False, cap-weighted with 20% cap, reb=3, formations 2016-08 plus quarter-ends).

(1) At each formation m, pool P = the top 45 by Eg (qg_lab.score base mode, V0 eligibility).

(2) For each i in P: 252 daily simple returns of i and of M_−i, the PIT cap-weighted return of the union universe excluding i (prior-close weights). At least 200 valid pairs are required, otherwise LTD is missing.

(3) Margins: rank/(n+1).

(4) Fit all 64 mixtures w1·C_L + w2·C_N + w3·C_U by canonical MLE:
- C_L ∈ {Clayton, rotated Gumbel, rotated Joe, rotated Galambos};
- C_N ∈ {Gauss, Frank, FGM, Plackett};
- C_U ∈ {Gumbel, Joe, Galambos, rotated Clayton}.
- (w1, w2, w3) = softmax(a1, a2, 0).
- Bounds, applied through log/logit transforms:
  - Clayton and Galambos θ ∈ [1e-4, 50];
  - Gumbel and Joe θ ∈ [1, 50];
  - Frank θ ∈ [−50, 50] (series expansion for |θ| < 1e-6);
  - FGM θ ∈ [−1, 1];
  - Plackett θ ∈ [1e-3, 1e3];
  - Gauss ρ ∈ (−0.999, 0.999);
  - rotations take the same bounds.
- L-BFGS-B, 3 starts (seeds 20260925+s); keep the best log-likelihood; log any fit at a bound.

(5) Select the mixture with the smallest Integrated Anderson-Darling distance to the empirical copula on the n×n lattice (CRW eq. 9), vectorized.

(6) LTD_i = w1*·λ_L(θ1*), where λ_L = 2^(−1/θ) for Clayton and rotated Galambos, and 2 − 2^(1/θ) for rotated Gumbel and rotated Joe. The SE of LTD_i comes from the delta method on the inverse Hessian at the selected fit.

(7) β_i = World.fp_beta. OLS within P: LTD_i = a + b·β_i + e_i; LTD⊥ = e.

(8) Drop 15 names: first those missing LTD or β, then the highest LTD⊥, until 30 remain.

(9) Cap weights with 20% cap; buy-and-hold drift; 10bp. Fund 90/10 vs SPY TR (PR reported).

MEASURED ONLY: A1 raw LTD; A2 tail asymmetry (drop the lowest UTD⊥ − LTD⊥); A3 nonparametric LTD = Ĉ(u,u)/u at u = 0.05; A4 S&P 500 PR as the market.

## params
- 252-day window, empirical margins, the 64-mixture set, canonical MLE, IAD selection, the λ_L formulas and market excluding i: CRW 2018 §2.1 and fn. 13 (opened).
- Pool 45 / drop 15: lab precedent build/eg_best.py C2, not tuned.
- FP beta: lab constants.
- Parameter bounds, the softmax weights, minimum 200 pairs, 3 MLE starts and delta-method SEs: implementation, declared.

## data
- Union members with at least 90% valid prices over 252 days: 426/443 (2016-08) to 511/515 (2026-07), including delisted names via pit_px.json.
- Shares via pit_panel/qg_lab.mcap; FP beta code in eg30plus lines 196-215; Eg scores 2016-08..2026-07; pins P1/P2/P3.
- Compute: about 7.5e9 lattice-cell evaluations plus MLE. Budget several CPU-hours and run in the background.

## controls
PRIMARY (G1): the down-month mean of Δβ(V1 − V0), with down_t at t(38).

G4:
- (a) C3 pure beta screen: drop the 15 highest FP beta from P. Required: the down-month mean of Δβ(V1 − C3) > 0 (point), which shows that LTD⊥ adds something beyond beta.
- (b) C2 placebo: drop 15 uniformly at random from P (1000 draws, seed 20260925). The true down-month Δβ must be at or above the 95th percentile.

G3 POINT CONDITIONS:
- raw down-month Δ ≥ 0;
- M1: beat the return-matched dilution of V0 on the down-month mean X;
- efficiency floors.

REPORTED:
- ex-ante basket beta change (expected within ±0.05);
- the all-month Δ vs V0, whose sign is pre-stated as < 0.

## lab_difference
Tail/moment family (tally at least 6), all stand-alone top-N sleeves with no copula and no beta residualization:
- '19 공편왜도 최저 | 측정만'
- '265 꼬리지수 상위 10'
- '402/520 DNBETA 기각'
- '54 상하방 베타 비대칭'
- '277 시장 저상관'
- '실현 왜도 최하위 20'

EGBEST C2 has the same pool/drop shape with a momentum screen. This card is a screen step on the incumbent.

## implementation_notes
- Class B step, slot B2 shared with Q08 (initial weight 1/16 each). New module build/q_ltd.py.
- Unit-test the 12 copula CDFs and densities, and λ_L at the parameter bounds, against closed forms before the bake.


# Q08 MATH-EG30-NETSTEP — EG30 + 상관망 주변부 단계 (기대투자성장 후보 60 중 전 시장 상관 MST 주변부 30 · Pozzi 하이브리드 중심성)

## why_keep
- A graph-theory construction step on the incumbent. It changes the basket's co-crash STRUCTURE, not its exposure SIZE (the EG30PLUS failure mode).
- Filtered correlation networks are new to the lab: a grep for MST/Pozzi/주변 found nothing.
- Revised for critique 2:
  - the primary is Δβ (beta-hedged down-month difference), because periphery ≈ low market-mode correlation ≈ low beta;
  - new mechanism control C3: the 30 lowest row-mean R̄ names of the same 60, which must be beaten on Δβ;
  - the placebo is evaluated on Δβ.
- Revised for critique 3: it carries the network hypothesis for the batch. Q09 (the paper-as-written stand-alone) is folded in as a measured-only arm, and Q08 shares slot B2 with Q07 at half weight each. The two co-crash screens on the Eg pool therefore spend one slot's alpha.

## mechanism_ko
EG30 은 급등 구간에서 이기고 급락 구간에서 진다(급락 0/6, 바스켓 베타 1.22). 급락 손실의 원인은 Eg 신호가 아니다. 바스켓이 상관망의 중심, 곧 같은 요인으로 묶인 대형 성장주 군집에 몰려 있다는 구조가 원인이다.

공통 충격과 쏠림 매매는 상관망의 허브를 타고 퍼지고, 폭락 때 상관이 가장 크게 뛰는 곳도 여기다(Pozzi 2013). 주변부 종목은 자기만의 수익 동인에 묶여 있어 충격 경로에서 떨어져 있다(Onnela 2003: 최소위험 포트폴리오는 MST 바깥쪽에 있다).

이 단계는 Eg 후보 60 가운데 망의 중심에서 먼 30 을 고른다. 판정은 베타 차이를 헤지한 뒤의 하락월 차이로 하고, 단순 저상관 30 과도 겨루게 한다. 그래서 효과가 '베타 낮추기'나 '저상관 고르기'가 아니라 망의 위치에서 나오는지만 남긴다.

## rule
V0 = EG30 V0 (EG_BASE, regenerated). V1 = V0 + step N1, applied at every EG formation m (quarterly_forms: 2016-08 plus quarter-ends).

(1) P60 = the top 60 names by Eg under EG_BASE ranking and eligibility.

(2) NETWORK: every name in World.universe(m,'union',ex_fin=False) with a price on each day t−250..t (gaps of at most 4 days forward-filled).
- For each s = t−125..t, compute the exponentially weighted Pearson correlation over the 125 returns ending at s, with w_k = w0·exp((k−125)/125), k = 1..125, Σw = 1.
- R^a = the mean of the 126 matrices.
- R̄_ij = ½R^a_ij + ½ρ̄ for i ≠ j, where ρ̄ = the mean over s of the mean off-diagonal correlation; R̄_ii = 1.

(3) MST (scipy.sparse.csgraph.minimum_spanning_tree) on d = sqrt(2(1 − R̄)).

(4) HYBRID P = X + Y (a large P means peripheral):
- X = (cD^w + cD^u + cBC^w + cBC^u − 4)/(4(N−1))
- Y = (cE^w + cE^u + cC^w + cC^u + cEC^w + cEC^u − 6)/(6(N−1))
- Midranks, with rank 1 = most central (descending for D, BC, EC; ascending for E and C = farness).
- Edge weight 1 + R̄ for strength and EC; distance d for BC, E and C; the unweighted versions use hops.
- A candidate lacking 251 days gets the network median P.

(5) Keep the 30 candidates with the largest P (ties go to the higher Eg). Cap weights with a 20% cap and water-fill; buy-and-hold drift; qbatch_core.stock_path(reb=3); 10bp; fund 90/10 vs SPY TR (PR reported).

MEASURED ONLY (never promotable): pool 45; pool 90; PMFG in place of MST (only if networkx is installed, otherwise reported as not run); C3b = the lowest FP beta 30 of P60; and Q09.

## params
- EG_BASE unchanged.
- 250-day window, τ = θ = 125, the 126-day average with ½ shrinkage, d = sqrt(2(1−R)), weights 1+R, the X/Y hybrid and midranks: Pozzi-Di Matteo-Aste 2013 (formulas read from the article via Europe PMC).
- Pool 60 = 2 × basket: declared, shared with Q02.
- Network on the whole union, MST primary, median-P imputation: implementation.
- Gate constants: eg30plus.

## data
- _eg_q5_scores_pitgics.json: about 398 scored names per month, so a pool of 60 is always available.
- Union universe of about 520 names on pins P1/P2/P3.
- scipy csgraph installed; networkx absent.

## controls
PRIMARY (G1): the down-month mean of Δβ_t = (X_V1,t − X_V0,t) − 0.1(β̂_V1 − β̂_V0)(SPYTR_t − rf_t), tested with down_t at t(38).

G4 MECHANISM:
- (a) C3: the 30 lowest row-mean R̄ names of P60, cap-weighted with the 20% cap, same schedule. Required: the down-month mean of Δβ(V1 − C3) > 0 (point).
- (b) PLACEBO: permute P randomly among the 60 candidates (1000 draws, seed 20260925; still 30 names, same cap weighting). The true down-month Δβ must be at or above the 95th percentile.

G3 POINT CONDITIONS:
- raw down-month Δ ≥ 0;
- M1: down-month mean X > that of V0 diluted to V1's annual excess;
- efficiency floors IR ≥ 0.72, excess ≥ +0.38%/yr, TE ≤ 1.20%, turnover ≤ 272%/yr.

## lab_difference
- '618/EG30PLUS-RESULT | 기각': the S1 placebo gave the same defense with shuffled sector labels. N1 uses network position instead, and C3 plus the Δβ statistic close the S1 trap.
- '53 상관 클러스터 10개 × 각 1종' picks momentum winners per cluster.
- '401 HRP' uses the tree for weights.
- '277 시장 저상관' is the plain low-correlation neighbour, reproduced by C3.

## implementation_notes
- Class B step, slot B2 shared with Q07 (initial weight 1/16 each).
- Shared network module build/q_netper.py (with Q09). Own Brandes betweenness, eccentricity and farness via csgraph.shortest_path; eigenvector centrality by power iteration.
- Unit-test on star, path and small known graphs.
- Pre-stated: the down-month Δβ must be about 0.075%/mo just to clear the first BH step.


# Q09 MATH-NETPERIPH20 — 상관망 주변부 20 (Pozzi·Di Matteo·Aste 2013 원문 규칙) · Q08 의 측정만 팔

## why_keep
- Folded into Q08 as a measured-only replication arm (critiques 2 and 3).
- The card itself says its edge is diversification efficiency, not a priced premium.
- Its screen is trailing risk-adjusted momentum, and its nearest neighbour ('277 시장 저상관') collapsed in PIT.
- It keeps the literature replication visible without spending a slot, and it informs whether Q08's network position carries anything by itself.
- Revised for critique 1: the REIT exclusion is consistent across formations.

## mechanism_ko
금리 쇼크나 유동성 경색 같은 공통 충격과 쏠림 매매는 상관망의 중심을 타고 퍼진다. 주변부 종목은 규제 요금, 원자재, 지역 수요처럼 자기만의 수익 동인에 묶여 있어 위기에 분산이 오래 버틴다(Pozzi 2013, Onnela 2003).

원문 절차대로 과거 1년 평균/표준편차 상위 절반으로 먼저 걸러 '분산만 싼 부실주'를 막는다. 다만 이 이점은 가격이 매겨진 위험 프리미엄이 아니라 분산 효율에서 온다. 그래서 측정만으로 두고, 베타를 헤지한 하락월 성과와 단순 저상관 20 대비로 보고한다.

## rule
FORMATION: quarterly_forms().

UNIVERSE:
- World.universe(m, index='spx', ex_fin=False).
- Exclude names classified Real Estate in pit_gics_sectors.json at month max(m, 2016-12). Formations before 2016-12 use the 2016-12 classification, because REITs sit inside Financials through 2016-10.
- Require a price on every day t−250..t (gaps of at most 4 days forward-filled).

STEP 1: S_i = mean/std of the last 250 daily returns; keep the top ceil(N/2) (ties go to the larger cap).

STEPS 2-4: R̄, MST and the hybrid P exactly as Q08 (2)-(4), with N = the screened pool.

STEP 5: hold the 20 names with the largest P (ties go to the lower row-mean R̄), 5% each, drifting until the next formation. stock_path(reb=3), 10bp; delisting proceeds go to cash at rf.

FUND: 90/10.

## params
- Δt = 250, τ = θ = 125, the 126-day average, ½ shrinkage, distances and weights, the X/Y hybrid, midranks, the top-half mean/std screen, m = 20, uniform weights, gap fill, REIT exclusion: Pozzi et al. 2013 (opened).
- Declared: the PIT S&P 500 list instead of the top 600 by cap; MST; quarterly formation; tie rules; the paper's look-ahead filter NOT replicated; the 2016-12 REIT classification rule.

## data
- PIT S&P 500 lists, prices including delisted names (pins P1/P2), pit_gics_sectors.json (no Real Estate sector before 2016-12; verified by the critic).
- Screened pool of about 200-245 names.

## controls
All measured only:
- K1: the 20 most central names;
- K2: the 20 lowest row-mean R̄;
- K3: the screened pool, equal weight;
- K4: random 20-name draws (1000);
- K5: hedge_ctrl.

Each is reported on the all-month X and on the down-month mean of the beta-hedged H.

## lab_difference
- '277 시장 저상관' (PIT Sharpe 0.363 vs retro 1.047) is the nearest neighbour, which K2 reproduces.
- '53 상관 클러스터'.
- '401/518 HRP'.
- '149 축소 공분산 최소분산'.

## implementation_notes
- Measured only (class M; outside F-Q; counted in the tally). Shares build/q_netper.py with Q08.
- Report sector weights and beta (a tilt toward utilities and energy is expected).


# Q10 SF1-ARSHIFT — 흡수비율 급등 교체 — S&P 500 종목 공분산이 소수 요인에 묶이면 EG30 → x-bmrot (Kritzman-Li-Page-Rigobon 2011)

## why_keep
- The signal is new to the lab (a grep for 흡수 found nothing). It comes from the covariance of the very stocks the fund holds, not from macro labels, and it uses the paper's shift statistic rather than the level, which Pollet-Wilson's counter-evidence would undermine.
- Critique 3 wanted one switch slot. Q10 shares slot S1 with Q03 at half weight, using IDENTICAL legs (EG30 ↔ x-bmrot) and the same exposure-matched control. The two signals are two estimators of one fragility-switch hypothesis, and they spend one slot's alpha.
- Revised for critique 2:
  - the primary is the all-month Δ^D with a studentized segment-shuffle p-value;
  - the phi flag is replaced by an ē-matched vol-twin gate;
  - F0 now requires at least 12 off months and at least 6 off-state down months.
- Revised for critique 1: the family precedent (QGSIZE and the others) is disclosed.

## mechanism_ko
흡수비율(AR)은 종목 수익 분산 가운데 상위 1/5 고유벡터, 곧 소수 공통요인이 설명하는 몫이다. 이 몫이 한 해 평균보다 짧은 기간(15일)에 크게 뛰면 종목들이 하나의 위험(대개 시장·유동성 요인)에 묶이고 있다는 뜻이다. 그러면 한 곳의 충격이 분산되지 않고 전체로 빨리 번진다(Kritzman 외 2011 의 '취약성').

이 결합을 만드는 것은 레버리지, 공통 보유자, 위험예산(VaR) 기반 매도다. 결합이 강해질 때 가장 크게 잃는 것은 베타 1.22 인 고성장 바스켓 EG30 이다. 그래서 그때만 수비 엔진 x-bmrot 으로 옮기는 것이, 같은 평균 비중으로 늘 섞어 두는 것보다 나은지를 묻는다.

## rule
SIGNAL UNIVERSE on each trading day t from 2014-06-30:
- the PIT S&P 500 members of the latest month-end ≤ t (index_history 'spx'), one class per company (pit_panel CIK rule), date-aware price keys;
- a stock is included if it has valid returns on at least 95% of the 500 days ending t; missing returns = 0.

AR AND SHIFT:
- AR_t = (sum of the n_t largest eigenvalues)/trace of the equal-weighted 500-day sample covariance, with n_t = round(N_t/5).
- ΔAR_t = [mean AR(t−14..t) − mean AR(t−251..t)]/sd AR(t−251..t).

DECISION at each month-end m (2016-08..2026-07), at that close:
- if ΔAR_m > +1.0, the sleeve for m+1 = the DEFENSE book (x-bmrot, as in Q03);
- otherwise the OFFENSE book (EG30 V0).
- Both are shadow books; a switch costs 10bp on the book sold plus 10bp on the book bought.
- No hysteresis and no intramonth trigger.

FALLBACK: OFFENSE if N_m < 300 or if fewer than 252 AR values exist.

FUND: 90/10 monthly reset.

If the pre-commit x-bmrot reproduction fails (see Q03), the DEFENSE leg is T-bills (rf prorated daily), decided before the commit.

MEASURED ONLY:
- (a) T-bill DEFENSE arm;
- (b) the paper's 3-state map (OFFENSE share 1 / 0.5 / 0 for ΔAR < −1 / within ±1 / > 1, remainder DEFENSE);
- (c) AR on the 9 SPDRs with n = 2.

## params
- 500-day window, n ≈ N/5, ΔAR = (MA15 − MA1y)/σ1y, +1σ trigger: Kritzman et al. 2011 as described in OFR WP0001 §C.7 (opened) and by Portfolio Optimizer (opened). The original text was not opened.
- Equal-weighted covariance: OFR; KKT's EWMA not adopted (ambiguity declared).
- PIT stocks instead of 51 MSCI industries: forced.
- 95% coverage, missing = 0, N < 300 fallback, monthly decision, two-state map: implementation.
- Engine legs: lab design (the user's switching goal), shared with Q03.
- No grid.

## data
- stocks.json pxd_dates 2009-01-02..; index_history 2014-06..2026-09.
- Members with at least 95% of the 500-day history: 406 (2016-08) to 495 (2026-08).
- Pins P1/P2/P3; x-bmrot leg as in Q03.
- About 3000 daily eigendecompositions of roughly 450×450; minutes.

## controls
PRIMARY (G1): the all-month mean of Δ^D = X_rule − X_D, where D = ē·EG30 + (1−ē)·x-bmrot rebalanced at month-ends with 10bp. p from a studentized segment shuffle of the monthly state path (on and off run lengths permuted separately and re-interleaved from the true initial state; 10,000 draws, seed 20260925).

GATES:
- (a) down-month mean Δ^D > 0;
- (b) placebo percentile ≥ 95 on the down-month Δ^D;
- (c) ē-matched VOL TWIN (monthly): DEFENSE for m+1 when SPY's 63-day realized vol at m is at or above its expanding quantile at level ē. The rule − twin must be > 0 on both the all-month and the down-month mean; otherwise the label is '변동성 타이밍 재포장'.
- (d) M1: down-month mean X > V0 diluted to the rule's annual excess;
- (e) rebound-miss, as in Q03;
- (f) F0: at least 12 off months and at least 6 off-state down months;
- (g) cost drag ≤ 2 × V0's.

REPORTED: coverage drift (406 → 495) plotted against AR.

## lab_difference
- '591 레짐 기반 동적 배분 | measured' measured a 6-month-winner switch, not AR.
- '횡단면 분산도 게이트' is dispersion.
- '53 상관 클러스터' and '277 시장 저상관' use correlation for selection, not as a state.
- '지수 집중도 게이트' uses cap-weight concentration.
- De-risking switch family, disclosed (at least 6 prior trials plus Q03/Q06/Q10): QGSIZE '국면으로 비중을 줄이는 판(우량성장30) | 기각 F1/F5' (caught 2 of 14 negative quarters), c06, c11, VOLMOM, AEGIS, t-voltgt/t-volreg.

## implementation_notes
- Class S, slot S1 shared with Q03 (initial weight 1/16 each). New module build/q_absorb.py.
- Compute AR once; only the fund frame reruns for the placebo.
- The N ≈ T eigen-share noise is checked by twin (c).


# Q11 SEASEC-A — 섹터 동월 계절성 — 같은 달 과거 최대 20년 SPY 대비 평균 상위 3 (Heston·Sadka/KLN 원형)

## why_keep
- Planned strategy #2. The sector-ETF form is the only feasible seasonality test in the lab: the stock version is no_input at 20 years (627).
- SPDRs start in 2006, giving 10 same-month observations at the first formation and 20 at the last. ETFs avoid survivorship.
- Revised for critique 2: the month-label permutation placebo is fully specified (one joint permutation per calendar year, shared by all sectors, held fixed across formations within a draw).
- Revised for critique 1: the sector-axis count (at least 13, including critic c04-season-sector keep:false) and the calendar-family count are disclosed.
- Revised for critique 3: two falsifiable sector-month predictions derived from the cited mechanisms are pre-stated and reported.
- SEASEC-B stays inside as the attribution diagnostic.

## mechanism_ko
섹터 수익에는 해마다 같은 달에 되풀이되는 구조가 있다.
- 업종 공통의 계절 실적: 임의소비재의 연말 분기, 에너지·유틸리티의 수요 계절. 투자자는 직전의 낮은 분기 이익에 과하게 무게를 두어 예측 가능한 계절 이익을 매번 과소평가한다(CHSS 2017).
- 심리의 계절성: 무드 베타가 높은 섹터는 낙관적인 달에, 방어 섹터는 비관적인 달에 상대적으로 강하다(Hirshleifer 외 2020).
- 수급: 달력에 묶인 기관 리밸런싱이 같은 달에 같은 방향의 수급을 만든다(Bogousslavsky 2016).

KLN(2021)은 계절성과 계절 반전을 1년 동안 더하면 0이 된다고 보였다. 그래서 이 수익은 위험 보상이 아니라 일시적 오가격이고, 그 달에 강했던 섹터를 그 달에만 드는 것이 수확 방법이다. 이야기와 맞는지 확인하려고 두 가지 섹터-월 예측을 미리 적는다.

## rule
UNIVERSE: XLB XLE XLF XLI XLK XLP XLU XLV XLY (fixed; XLRE and XLC excluded because they have fewer than 10 same-month observations).

RETURNS: r(s,m) = px(me[m])/px(me[m−1]) − 1 from assets.json adjusted close; x(s,m) = r(s,m) − r(SPY,m).

FORMATION at each f in monthly_forms() (2016-08..2026-07), target month t = f+1:
- S(s,f) = the mean of x(s, t−12j), j = 1..J, where J = the number of past years with data (capped at 20);
- at least 10 observations are required (never binds).

SELECTION: the top 3 by S (ties alphabetical), 1/3 each, fully invested.

EXECUTION: qbatch_core.etf_path at the f close (cost 0.0010), held to t's month-end.

FUND: 90/10 vs SPY TR (PR reported).

ATTRIBUTION (SEASEC-B, measured only):
- N(s,f) = S − O, where O = the mean of x(s, t−k) over k = 13..12J with k mod 12 ≠ 0.
- If A passes and B fails, A's label becomes '섹터 드리프트, 계절성 아님'.

PRE-STATED STORY CHECKS (report only):
- P1: XLY is in the top 3 for target months November and December in at least half of the years.
- P2: the count of XLP/XLU/XLV picks in September-October targets exceeds the count in January + April targets.

## params
- Annual lags t−12..t−240, relative to market, monthly sorts: Heston-Sadka 2008/2010 via HXZ 2020 A.5.51 and OSAP SignalDoc (opened).
- Equal pooling of years: HXZ.
- Growing 10→20-year window: forced by data.
- Top 3 of 9 and equal weight: lab SECROT convention.
- 10bp and the 90/10 frame: lab.
- Nothing tuned.

## data
- assets.json: 9 SPDRs + SPY, 2006-01-03..2026-09-23, 0 nulls.
- Same-month observations: 10 at the 2016-08 formation, 20 at 2026-07 (count-only script $TEMP/qbatch/seas_cov.py).

## controls
PRIMARY (G1, Class A): all-month X, NW(3) t.

G4:
- (a) C1 = the 9-sector equal-weight sleeve, same frame. Required: sleeve − C1 all-month mean > 0 (point).
- (b) PLACEBO: one draw = for each calendar year y in 2006..2025, one uniform permutation π_y of that year's available month labels (11 in 2006), applied JOINTLY to all 9 sectors' and SPY's history x. The permuted history is held fixed across every formation in the draw; S is recomputed; realized holding returns stay true. 1000 draws, seed 20260925. The true all-month mean of (sleeve − C1) must be at or above the 95th percentile.

G3: down-month mean X ≥ 0 AND H > 0.

REPORTED: the 11 calendar-shift sleeves; P1/P2; SEASEC-B.

## lab_difference
- '267 동월 계절성 (같은 달 과거 2~5년 평균) (30종)' is stock-level, 4 observations, PIT Sharpe 0.393.
- 'LISTED 핼러윈 섹터 | 측정만' (t +0.28).
- 'SECROT-RESULT' rejected 10 rules and includes no same-month signal.
- '248 계절성 (11~4월만 보유)'.
- Disclosed families:
  - sector axis ≥ 13, including critic c04-season-sector keep:false (SECROT §6);
  - calendar family: t-tom, Halloween sector, 248, x-season, E29.

## implementation_notes
- Class A (planned), slot A4 (initial weight 1/8). About 60 lines.
- Turnover is about 8x/yr, so report the 20bp row.
- GICS breaks (2016-09, 2018-09, 2023-03) are disclosed and not patched.


# Q12 SK15 — 실적발표 프리미엄 + 이익 계절성 단계 (역사적으로 큰 분기를 발표하는 종목만 · CHSS 2017 착안 랩 변형)

## why_keep
- A step on Q05 (the user's step principle) that adds a separate information set: fundamental earnings seasonality, with a documented behavioural mechanism.
- It is a child in the graph: it is tested only if Q05's null is rejected, so it spends no extra alpha.
- Revised for critique 1:
  - fiscal-Q4 announcements are now mapped through annual-bucket period ends (the ni quarterly bucket has no fiscal-Q4 rows);
  - the share of announcers that can be mapped is reported;
  - the restatement leak is disclosed, and the first-filed rebuild or sensitivity applies.
- Revised for critique 3: the CHSS full text was not opened, so the card is labelled 'CHSS 착안 랩 변형'. The within-year rank and the S ≥ 3.0 cut are declared lab choices, and CHSS's evidence is marked as not transferred.

## mechanism_ko
기업 이익에는 계절성이 있어 특정 분기에 이익이 늘 크게 나온다. 그런데 투자자와 애널리스트는 직전의 (계절적으로 낮은) 분기 이익에 과하게 무게를 두어, 다음 '큰 분기'를 비관적으로 예측한다. CHSS(2017)에 따르면 그런 분기에는 애널리스트 예측오차가 더 양이다. 그래서 역사적으로 이익이 큰 분기를 발표하는 기업은 발표 시점에 높은 수익을 낸다.

발표 프리미엄(위험·주의 보상, Q05) 위에 예측 가능한 긍정적 서프라이즈(행동 편향)를 겹치는 구성이다. 섞기가 아니라 '어느 발표 종목을 담을지'를 좁히는 단계이며, 그 증분만 판정한다.

## rule
FRAME: identical to Q05 (universe, record, expected-announcer definition with the strict before-LTD cutoff, monthly timing, 20% cap, costs, fund).

UPCOMING FISCAL QUARTER f for announcer i and month t: the fiscal quarter whose results were announced by i's 2.02 filing in month t−12. It is identified as follows:
- a quarterly NI period-end falling 0-100 days before that filing maps to fiscal Q1-Q3;
- otherwise, an ANNUAL (ni_a) period-end falling 0-100 days before it maps to fiscal Q4.
- Unmapped announcers are excluded from the step.

SCORE: S_i = the mean, over the previous 5 fiscal years whose four quarters are all known by m under the 90-day lag (at least 3 years), of the within-fiscal-year rank (1..4, 4 = largest) of NI in quarter f among that year's four quarterly NI values. Q4 = annual NI − (Q1 + Q2 + Q3).

SELECTION: expected announcers with S_i ≥ 3.0. If fewer than 30 qualify, the sleeve holds Q05's basket that month (Q05's thin-month fallback then applies).

WEIGHTS: market cap, 20% cap, monthly, 10bp; fund 90/10.

PIT: every period end and filing date used is < LTD(m); NI values respect the 90-day lag.

## params
- Positive-seasonality quarter and holding over the announcement month: CHSS 2017 (abstract opened via IDEAS; full text NOT opened).
- Declared lab choices: the within-fiscal-year rank (in place of CHSS's rank, which was not verified); S ≥ 3.0; the 0-100-day period-end mapping, including annual period ends for fiscal Q4.
- Everything else as in Q05.

## data
- earn_dates as in Q05.
- Quarterly NI (Q1-Q3 buckets) plus annual ni_a via tech_backtest.
- At least 15 quarterly NI observations in the prior 6 years: 361/530 (2016-08) to 478/518 (2026-08).
- Non-calendar fiscal years (AAPL, WMT, KO) are handled by the period-end mapping.

## controls
PRIMARY (child): the paired all-month Δ(fund_Q12 − fund_Q05), NW(3) t, one-sided. Tested only when Q05's null has been rejected by the graph (label tier) or Q05 has been admitted (forward tier).

G4 PLACEBO: permute S among eligible expected announcers within each month (1000 draws, seed 20260925). The true Δ must be at or above the 95th percentile.

REPORTED: the mapped share of announcers per month; overlap with Q05; turnover.

## lab_difference
- '674 세금비용 서프라이즈 | measured' is a realized tax-expense change.
- 'SUE 상위 10', '301 PEAD' and 'PEAD 2판' are post-announcement.
- '267 동월 계절성' is stock-return seasonality.
- This step sorts on predictable fundamental seasonality BEFORE the announcement.

## implementation_notes
- Class C child of Q05 (graph edge weight 1 from Q05). Same module as Q05 (build/q_eap.py).
- Unit-test the mapping on AAPL (fiscal year ends September), WMT (January) and KO (calendar), including a Q4 10-K release for each.


# Q13 FE3-CRASHEIG — 폭락일 고유값 재추정 — FE1 위험모형의 고유값만 S&P 500 최악 10% 날의 2차 적률과 반씩 섞는다 (FE1 다음 단계)

## why_keep
- The natural next step on FE1: it attacks the bear-market correlation asymmetry (Longin-Solnik, opened) inside the risk model instead of by timing.
- Its incremental compute is trivial.
- It is a graph child of Q02, so it spends no extra alpha.
- Revised: the statistic is beta-hedged (Δβ vs FE1), and the placebo and dilution controls are evaluated on it.

## mechanism_ko
FE1 의 위험모형은 1000일을 모두 똑같이 본다. 그런데 상관은 하락장에서만 커진다. 그래서 평균 위험모형은 '폭락일에만 한꺼번에 무너지는 능동 베팅'의 위험을 과소평가하고, 바로 그 베팅이 펀드가 하락월에 지는 이유다.

이 단계는 FE1 의 고유벡터(위험의 방향)는 그대로 두고, 각 고유포트폴리오의 크기(고유값)만 다시 잰다. 지난 1000일 중 S&P 500 이 가장 나빴던 10% 날의 실현 2차 적률로 재고, RIE 값과 반씩 섞는다.

같은 위험 예산 안에서 최적화기는 폭락일에 커지는 모드의 능동 노출만 비싸게 치고, 상승일에만 요동치는 모드(급등 포착의 원천)는 싸게 남긴다.

## rule
Identical to Q02 (FE1, including the P60-restricted α, constraints, solver pins and TE* fallback). Only Σ changes.

(1) From FE1's standardized Y (N×1000), take the sample eigenvectors U and the IWs-RIE eigenvalues ξ̂.

(2) D_c = the 100 days (⌈0.10·T⌉) in the same window with the lowest S&P 500 PR daily return (bench_px spx).

(3) ξᶜ_k = (1/100)·Σ_{t∈D_c}(u_k'Y_t)² (second moment about zero).

(4) Ξ = ½·U diag(ξ̂) U' + ½·U diag(ξᶜ) U', renormalized to unit diagonal; Σ_blend = diag(σ) Ξ diag(σ).

(5) κ is chosen so that the ex-ante TE under Σ_blend equals EG30's ex-ante TE under Σ_blend (same bisection and solver).

(6) Quarterly with drift; 10bp; fund 90/10.

## params
- T = 1000, IWs-RIE and normalization: as FE1 (BBP 2017).
- Eigen-portfolio realized second moment: BBP eqs. 8.15-8.16 (opened).
- 10% crash-day share: lab CVAR_Q = 0.10.
- ½ blend: implementation following Chow et al. 1999 (metadata only), declared.
- Nothing tuned.

## data
- Same as Q02.
- bench_px spx daily from 2006; the first 1000-day window (about 2012-08..2016-08) lies inside the panel.
- Pins P1/P2/P3.

## controls
PRIMARY (child): the down-month mean of Δβ_t = (X_FE3 − X_FE1) − 0.1(β̂_FE3 − β̂_FE1)(SPYTR − rf), calendar HAC at t(38). Tested only if Q02's null is rejected (graph) or Q02 is admitted (forward tier).

G3: M1, a return-matched dilution of FE1 (down-month point comparison).

G4 PLACEBO: D_c replaced by 100 uniformly random days (1000 draws, seed 20260925). The true Δβ must be at or above the 95th percentile.

REPORTED: mirror C3 (D_c = the best 10% of days); the active market-mode loading vs FE1.

## lab_difference
- 591 (timing), '변동성 국면 섹터' and '주식-채권 상관 국면 게이트' switch exposures.
- DNBETA and the LIBMETA asymmetry measure strategy-level betas (split-half persistence 0.09-0.12).
- FE3 never switches exposure: the crash state only reshapes the risk metric.

## implementation_notes
- Class C child of Q02 (graph edge weight 1). Same module as Q02 (build/q_riegk.py); a few seconds per formation.


# Q14 L2-resid-n — 잔차 1/N (RESID-N) — 엔진 1/N 에서 시장·스타일 노출을 걷어낸 잔차 · 판정은 헤지 측정판 L2-N 과 롱온리 보유판 L2-LO 가 둘 다 통과해야 채택

## why_keep
- Planned library combination L2. It fills the pre-registered F-LIB slot H2 (PREREG-2026-09-24-LIBMETA line 49).
- It is the only construction whose excess can be positive by design in BOTH crash and surge months, because β = 1 and the style loadings are 0.
- Revised for critiques 1 and 3:
  - L2-N is explicitly a NON-INVESTABLE diagnostic (it needs shorts);
  - nothing is adopted unless the long-only L2-LO also passes the fund-frame gates, so a pass is always holdable;
  - borrow is fixed at a conservative declared 1.00%/yr and is no longer a free parameter.
- Revised for critique 2: the F-LIB power line (IR 1.44 at 36 months, 1.12 at 60) is stated.
- The user is told plainly that the only verdict now is 오염 측정; the first forward decision comes at FF1, 24 forward months after the start.

## mechanism_ko
랩 엔진의 초과수익은 대부분 공통 노출에서 나온다. 시장 베타 1 미만, 동일가중−시총가중(라이브러리 분산의 62%), 가치·저변동·모멘텀 틸트다. 이 노출들은 급락과 급등 가운데 한쪽에서만 이긴다.

구성상 급락월과 급등월에 동시에 양수일 수 있는 초과는 베타 1·스타일 0 의 잔차뿐이다. 각 엔진의 이상현상 프리미엄이 일부라도 진짜라면, 잔차 상관이 낮은 엔진 54개를 1/N 로 묶을 때 고유 잡음은 상쇄되고 프리미엄만 남는다(Treynor-Black, Kakushadze-Yu).

평균 수익을 쓰지 않는 1/N 이므로 추정오차와 생존편향의 첫째 모멘트 통로가 끊긴다. 반대 증거가 강하므로(Fama-French 2010, McLean-Pontiff) 미리 적는 기대값은 'SPY − 비용'이다.

## rule
DATA:
- in-sample: lib_loader.load(end='2026-08', rev='9e8ebd40') (sid sha 17314587…, panel sha fb636999…);
- forward: only the append-only ledger data/_lib_ledger.json;
- net return r̃_i = r_i − cost_drag_i/12.

UNIVERSE U2: role = 수익엔진, basis = pit, holds ∈ {종목, 없음}, cost_kill ≠ True (54 families; sids frozen with sha256 only after the ledger exists). U2_t = members with r̃ in all 36 months of W_t.

CALENDAR:
- W_t = months t−35..t, never before 2016-10.
- First decision 2019-09; the in-sample holding period 2019-10..2026-08 is 오염 측정 (report-only).
- Forward starts at the first month-end close after the prereg commit (target 2026-10-30), from 100% SPY with the entry trade charged.

FACTORS (assets.json TR): MKT = SPY − rf, EW = RSP − SPY, GV = IVW − IVE, LV = SPLV − SPY, MOM = SPMO − SPY.

STEP 1: OLS over W_t for each i (and for IVW, IVE, QQQ, SPHB) of r̃ − rf on the five factors.

STEP 2: w_i = 1/|U2_t|; the portfolio loadings L_P = Σw_i·loadings_i.

L2-N (the F-LIB H2 statistic; NON-INVESTABLE):
- positions: engines at w, plus RSP −e_P, IVW −g_P, IVE +g_P, SPLV −l_P, SPMO −m_P, SPY (1 − b_P) + e_P + l_P + m_P, and financing −(1 − b_P)·rf;
- X^N = R − SPY TR − 10bp × Σ|Δpos| − (1.00%/12) × short notional (rows at 0.25% and 0.50% reported).

L2-LO (holdable 10% sleeve):
- ½ × engines at 1/N, plus a completion c ≥ 0 over H = [SPY, IVW, IVE, QQQ, SPHB, T-bill] with Σc = ½;
- constraints: sleeve β = 1 and sleeve GV = 0; objective: minimize Σ non-SPY c;
- solve by exact enumeration of subsets of at most 3 members (ties by H order);
- if infeasible, drop GV (subsets of at most 2); if still infeasible, c = ½ SPY; log every such month.

FUND: 90% SPY + 10% L2-LO, reset monthly.

STOPPED SERIES: earns SPY that month, then moves to SPY. If |U2_t| < 30, the month is SPY.

## params
- U2 filter: 2026-09-24 design slate plus critics.
- W0 = 2016-10 and first decision 2019-09: LIBMETA §2.
- 36-month window, factor set (frame T6 minus BOND), 1/N (DeMiguel-Garlappi-Uppal 2009, opened), λ = ½ (LIBMETA L1 ANCHOR), completion set and enumeration: slate.
- Borrow 1.00%/yr: a declared conservative fixed assumption, NOT sourced. A cheaper sourced quote does not replace it; the rows at 0.25/0.50 are reported.
- Costs P9; NW lag 3; F-LIB Holm m = 4 (2.50/2.39/2.24/1.96): frame §1.
- F0 thresholds: slate.

## data
- lib_loader rev 9e8ebd40: 132 families, hashes match, U2 = 54.
- assets.json: SPY RSP IVW IVE QQQ from 2006; SPLV and SPHB from 2011-05; SPMO from 2015-10.
- rf_monthly; mech_episodes sigma_pre 0.042903.
- PREREQUISITES before commit (not built today; verified):
  - an SPHB loader in lib_loader.spy_tr_monthly;
  - the append-only ledger build/lib_ledger.py;
  - the pivot-date NAV export;
  - frozen U2 sids with sha256.

## controls
PRIMARY: SPY TR (equal to C2 because β = 1).

ALSO:
- decomposition vs P1 (unhedged 1/N, C1);
- K4 overlay-order permutation within runs of identical U2_t (1000 draws, seed 20260925);
- P4 leakage: joint Wald χ²(5) on NW(3);
- P5 conditional neutrality in CRASH-M and SURGE-M (MKT within 1 ± 0.1, styles within 0 ± 0.1).

ADOPTION requires BOTH:
- (i) L2-N passes F-LIB FF2;
- (ii) the L2-LO fund passes the fund-frame T1-T4, realized G1 ≤ 50%, and IR(L2-LO fund) > IR(P1-fund) with NW t of the difference ≥ 1.0.

REPORT-ONLY TWIN: L2-ERC.

## lab_difference
- '519 UNION-RESULT | 기각(F1·F2)': unhedged 1/N of 195 series, β 0.764.
- LOWCORR selects 6 by total-return correlation.
- 302/314/401/410/416 are risk or shrinkage weightings that never remove β or styles.
- 548 RRG used relative-strength trends.
- LIBMETA L1 only shifted β.
- The hedged factor-neutral core is new.

## implementation_notes
- Class D: judged ONLY forward, in F-LIB slot H2 (not part of F-Q). FF1 at 24 months, FF2 at ≥ 36 months plus the event minimum, FF3 at 60.
- Power line: F-LIB forward t 2.50 needs IR ≈ 1.44 at 36 months and 1.12 at 60, so a realistic outcome is 보류 until about 2031.
- Pre-stated expectation: L2-N ≈ SPY − costs; L2-LO's G1 fires, giving '공통요인 베팅 — 측정만'.


# Q15 L4-engine-tsm — 엔진 자기추세 교체 (메타 시계열 모멘텀) — 엔진별 12개월 순 상대부(SPY 총수익 대비)가 양이면 들고 아니면 그 칸을 SPY 로

## why_keep
- Planned library combination L4. It fills the pre-registered F-LIB slot H3.
- It is the first rule that switches engines on their own time-series trend, with SPY as the off state.
- It is judged against an exposure-matched static on-fraction placebo, and against the RRG and common-factor increments.
- It is disclosed as RRG-family +1.
- It is forward-only because the in-sample window is contaminated (critique 1), and it needs the same unbuilt ledger. U4 sids are frozen only after the ledger exists.
- The power line is stated (critique 2).

## mechanism_ko
요인·전략 수익은 양의 자기상관을 가진다. 직전 1년이 플러스였던 요인은 다음 달 평균 51bp, 마이너스였던 요인은 6bp 를 벌었다(Ehsani-Linnainmaa 2022). 롱온리로 옮기면 '승자는 들고 패자는 뺀다'가 된다.

근본 이유는 셋이다.
- 미스프라이싱·위험 프리미엄의 국면은 과소반응과 자본의 느린 이동 때문에 천천히 바뀐다(Moskowitz-Ooi-Pedersen 2012).
- 출판·혼잡으로 프리미엄이 사라진 전략은 한동안 계속 잃는다(McLean-Pontiff).
- 비용이 무거운 전략의 순손실은 지속된다(Carhart 1997).

진 엔진의 자리는 현금이 아니라 SPY 로 돌리므로 급등에서 베타를 잃지 않는다. 반대 증거(RRG t −0.11, 순위 지속 0.026)가 분명하므로 정적 켜짐비율 위약 대비로, 전방에서만 판정한다.

## rule
DATA:
- in-sample: lib_loader.load(end='2026-08', rev='9e8ebd40');
- forward: only the append-only ledger;
- r̃_i = r_i − cost_drag_i/12; s_m = SPY TR monthly.

UNIVERSE U4: role = 수익엔진, basis = pit, holds = 종목 (58 families; sids frozen with sha only after the ledger exists). U4_t = members with r̃ in all of t−11..t (months ≥ 2016-10).

SIGNAL at month-end t: RW_i = Π_{t−11..t}(1 + r̃_i/100)/Π(1 + s/100) − 1; z_i = 1 if RW_i > 0, else 0.

WEIGHTS for t+1: each slot gets 1/|U4_t|, holding engine i if z = 1 and SPY otherwise. Off weight is never redistributed and never goes to cash.

REBALANCE: monthly at the close, drift within the month.

COSTS: 10bp one-way × Σ|Δw| on the engine and SPY legs, plus cost_drag/12 while held.

STOPPED SERIES: the slot earns SPY that month, then moves to SPY.

CALENDAR:
- first decision 2017-09; in-sample 2017-10..2026-08 is 오염 측정;
- forward starts at the first month-end after the commit (target 2026-10-30), from 100% SPY.

FUND: 90% SPY + 10% L4, reset monthly.

## params
- U4 filter (58, verified).
- 12-month lookback and sign rule: MOP 2012 and E&L 2022 (opened); lab RRG n = 12.
- RW: frame M4.
- SPY off state: slate.
- 1/N slots; costs P9.
- Static on-fraction placebo and K4 shuffle (seed 20260814): AUDIT-2026-08-14-REGIME-K4 §2.
- Increments: RRG §1 and RSP/SPY 12-month.
- F0 thresholds (on-fraction outside [0.10, 0.90]; agreement > 0.80) and FF0 (≤ 6 switches): declared.

## data
- U4 = 58 at rev 9e8ebd40.
- Panels 2016-09/10 → 2026-08.
- SPY/RSP daily from 2006.
- Needs the ledger and the pivot-NAV export (not built).

## controls
PRIMARY: the static on-fraction placebo. Slot i holds f_i × engine + (1 − f_i) × SPY, where f_i is the slot's realized forward on-fraction.

ALSO:
- C1: always-on 1/N;
- K4: run-order shuffle (1000 draws);
- Increment 1: RRG RS-Ratio ≥ 100;
- Increment 2: one common switch on RSP/SPY 12-month relative wealth.
- The intercept of (L4 − SPY) on each increment must have NW t ≥ 1.0.

## lab_difference
- '548 RRG-RESULT | 기각(F3)': descriptive quadrants on 110 engines with no off state.
- '434/435' are cross-sectional.
- '59/182/241' are asset TSMOM with cash.
- '502 CGATE' is an EW↔CW switch, which Increment 2 and FF3 test.
- LIBMETA P5 is cross-sectional re-weighting.
- RRG-family +1 disclosed.

## implementation_notes
- Class D, forward-only, F-LIB slot H3.
- FF1 at 24 months: cumulative (L4 − placebo) ≤ 0 → 기각.
- FF2 at ≥ 36 months plus the event minimum.
- FF3: an Increment-2 intercept t < 0 → '공통요인 타이밍' 기각.
- Power line as in Q14.
- Pre-stated expectation: ≈ the on-fraction placebo.


# Q16 VRP-HIBETA — 분산위험 프리미엄 고베타 교체 — 내재분산(VIX²)이 실현분산을 평소보다 크게 웃돈 달부터 3개월은 슬리브를 고베타(SPHB)로 (Bollerslev-Tauchen-Zhou 2009)

## why_keep
- This is the new stand-alone, surge/rebound-side mechanism that critique 3 required. None of the other cards targets that side.
- It replaces critique 3's suggested card (VIX-conditional liquidity-provision reversal, Nagel 2012). I opened Nagel's full text (NBER w17653) and found:
  - the strategy is DAILY, with weights on the last 1-5 days' market-adjusted returns;
  - inventory half-lives run from half a day for the largest stocks to two days (lines 554-558);
  - so a monthly-hold version has no support in the paper;
  - daily or weekly versions breach the lab's 10x/yr cap;
  - and REVCOMP closed the family (PIT weekly −2.71%p, monthly −7.33%p).
- This card is VRP used as a predictor of index returns, with full text opened: BTZ, FEDS 2007-11.
- It never de-risks, because the off state is SPY. In a bull sample it avoids the cash drag that killed 22/22 overlays.
- It is lab-new: pool card 607 measured only short vol (SVXY 25%), not IV−RV timing.

## mechanism_ko
분산위험 프리미엄(VRP = 내재분산 − 실현분산)은 투자자가 변동성 급등을 피하려고 치르는 보험료다. 이것이 평소보다 크면 시장 전체의 위험회피가 실제 위험보다 크다는 뜻이고, 그만큼 주식의 기대수익도 높다. BTZ 는 1990~2005 년 분기 초과수익 변동의 15% 이상을 VRP 가 설명하고, 높은(낮은) 프리미엄이 높은(낮은) 미래 수익을 예측한다고 보였다. 근본 이유는 시간에 따라 변하는 위험과 위험회피다.

이 신호가 켜지는 때는 대개 두 경우다.
- 급락 직후: 실현변동은 가라앉는데 VIX 는 높게 남은 반등 초입.
- 평온하지만 불안이 가격에 남은 구간.

급락 한가운데서는 실현분산이 내재분산을 넘어 VRP 가 낮거나 음이라 켜지지 않는다. 그래서 급락에서는 지수(SPY)를 그대로 들고, 반등에서만 고베타로 기대수익을 더 받는 비대칭 구조다. 판정은 같은 평균 고베타 비중의 고정 혼합 대비로 하므로 고베타 자체의 성과(고베타 이상현상 불리함)는 빠지고 타이밍 정보만 남는다.

## rule
DATA:
- ^VIX month-end close (assets.json);
- ^GSPC daily close (bench_px spx, from 2006-01-03);
- rf_monthly;
- SPHB and SPY adjusted closes (assets.json).

SIGNAL: for each month k from 2006-02:
- IV_k = (VIX_k/100)²/12
- RV_k = Σ_{d∈k} [ln(P_d/P_{d−1})]² over ^GSPC trading days in month k
- VRP_k = IV_k − RV_k (BTZ eq. 3)
- High_m = 1 if VRP_m > median{VRP_k : 2006-02 ≤ k ≤ m} (expanding, inclusive), else 0.

WEIGHTS: at each month-end m in monthly_forms() (2016-08..2026-07), the sleeve for m+1 is h_m·SPHB + (1 − h_m)·SPY, with h_m = (High_m + High_m−1 + High_m−2)/3. The three overlapping monthly tranches match BTZ's quarterly horizon. No cash, no leverage.

EXECUTION: qbatch_core.etf_path trades at the close of me[m] and holds to the next month-end, with cost 0.0010 on all traded sleeve value (including drift resets).

FUND: fund_from_path, TR and PR; holdings 2016-09..2026-08; evaluate().

TWIN (a gate, not selectable): IV-only, i.e. High'_m = IV_m > the expanding median of IV, with the same tranches.

MEASURED ONLY: the RV-only twin (on when RV_m < its expanding median).

## params
- VRP = IV − RV at month end; model-free IV (the new VIX, as in BTZ); the high-versus-low premia reading; the quarterly horizon: Bollerslev-Tauchen-Zhou (FEDS 2007-11, full text opened; RFS 22(11):4463-4492, Crossref metadata opened).
- DAILY RV instead of 5-minute RV: forced, because the lab has no intraday data. BTZ report quarterly R² 8.08% for model-free IV with daily RV, against 15.14% with high-frequency RV (opened, §3.2.1). This weaker version is declared.
- Expanding-median split: implementation. It is the natural high/low split and needs no threshold choice.
- SPHB as the risk-on leg: implementation. It is the only pure high-beta S&P 500 instrument in the lab, from 2011-05-05.
- Three tranches: implementation of BTZ's quarterly horizon.
- Costs and frame: lab.
- Nothing tuned.

## data
Verified today, availability only:
- assets.json ^VIX 2006-01-03..2026-09-23 (5213 closes);
- SPHB 2011-05-05..2026-09-23 (3869);
- ^GSPC and SPY 5213 each;
- bench_px spx from 2006-01-03.

VRP history has 127 months before the first formation. rf_monthly. build/qbatch_core.py etf_path exists.

## controls
PRIMARY (G1, Class S):
- the all-month mean of Δ^D_t = X_rule,t − X_D,t, where D = f̄·SPHB + (1 − f̄)·SPY reset monthly and f̄ = the realized mean of h_m;
- p from a studentized permutation: permute the run lengths of High = 1 and High = 0 separately, re-interleave them from the true initial state, recompute the tranches, and recompute the NW(3) t (10,000 draws, seed 20260925).

GATES:
- (a) down-month mean Δ^D > 0 (timing adds no crash cost relative to the static mix);
- (b) the rule − IV-only twin all-month mean > 0; otherwise the label is '변동성 수준 재포장';
- (c) the SURGE-M mean Δ^D > 0 (the mechanism claim, pre-stated sign +);
- (d) G3: down-month mean X ≥ 0;
- (e) F0: the High path has at least 12 runs; otherwise 측정 불가.

REPORTED: SPHB static; hedge_ctrl; the RV-only twin; the months with h > 0 inside CRASH-M.

## lab_difference
- '164 VIX 수준 게이트 (25) | 측정만' de-risks when VIX is high, the opposite sign.
- '163 VIX 기간구조 신호 (VIX/VIX3M) | 측정만' and '582 VIX 기간구조 극단 역발상 게이트 | measured' use the term structure, not IV−RV.
- '607 변동성 리스크 프리미엄 (VRP / 숏볼) | measured' (vrp-shortvol: SVXY 25% + SHY 75%) harvests the premium by selling vol and does no timing.
- '18/24/26 고베타 ↔ 저변동 전환' switch SPHB↔USMV on macro axes.
- VIX-timing family: at least 7 trials, disclosed.
- This is the first rule that uses the IV−RV spread as a return predictor, and it can only add risk.

## implementation_notes
- Class S stand-alone, slot A5 (initial weight 1/8). New module build/q_vrp.py, about 60 lines on qbatch_core.
- SPHB β is about 1.4, so the fund's beta rises by about 0.04 when the sleeve is fully on. Fund TE is tiny, so a power disclosure is required.
- Pre-stated expectations (not computed):
  - on in post-crash calming months (2020-05..07, 2022-07/11, 2025-05/06);
  - main risk: being on going into a second crash leg after a calm month (2018-10, 2020-02). Gate (a) tests this.
  - years won expected 5-7/11.
