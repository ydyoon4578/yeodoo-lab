# -*- coding: utf-8 -*-
"""build/r_run.py — 배치 R(RBATCH) 한 번 굽기 러너: Stage M 주 통계 · 한쪽 p · Holm(m 은 등록 커밋에 고정) · 관문 i~iii · 판정
· F0 재현 · 얼린 판 점검(SNAP/BASE 핀 · 새 자료 고정표) · 검문점 → data/_rbatch.json

사전등록: build/PREREG-2026-09-2x-RBATCH.md(뼈대 — 등록 때 날짜를 채워 이름을 바꾸고 PREREG · PREREG_CARDS · RESULT 를 같은 커밋에서 고친다).
카드 원문: scratchpad rbatch_research.json «final»(slate R1-OPPSELL · R2-LAZYRF · R3-8KNE · R5-ALARM · batch_design_changes 1~12 ·
data_build_plan §E «러너는 qbatch_run 처럼»). 우선순위는 사전등록 문서가 정한다 — 글과 이 코드가 어긋나면 **얼린 코드가 돌고**
그 어긋남은 결과 문서에 «등록 오류» 로 적는다.

근본 이유(왜 이렇게 나눴나).
  배치 Q 러너처럼 «엔진은 계열만 내고 판정은 러너가 한 벌로» 한다. 엔진은 build/r_stagem.py(월별 횡단면 회귀 · FWL · JT · 관문 변형)다.
  이 파일은 엔진이 낸 γ 월 계열에서 주 통계 · p · Holm · 관문을 **다시 계산**해 엔진의 요약·관문과 대조한다 — 어긋나면 멈춘다
  (같은 판정을 두 곳이 저마다 하면 반드시 갈린다. 이 저장소가 되풀이 밟은 결함을 굽기 전에 잡는다).

주 통계(batch_design_changes 3 · 카드 R1 (8) · R2 (10)).
  γ_focal(OS · CH) 월 계열의 평균 · NW(3) t · 한쪽 H1 γ < 0 · p = P(t(T−1) ≤ t).
  NW t 는 달력 위치를 지킨다(엔진 r_stagem.summarize 와 한 정의) — 쓴 달(γ 가 선 달)이 달력으로 이어지면 eg30plus.nw_t 그대로,
  빈 달(흩어진 커버리지 실패 달 · 자유도로 건너뛴 달 · 주 표지가 어느 시차에서 0 이라 γ 가 서지 않은 달)이 끼면 r_stagem.nw_t_gap
  (같은 식 · 빈 달 편차 0 · 시차 곱은 달력으로 L 달 떨어진 두 달이 모두 선 쌍만). 둘 다 복제하지 않고 부른다. 압축 계열 값도 함께 싣는다.
  T 는 계수가 선 달 수다(커버리지 F0 를 넘은 신호월 2016-08..2026-07 가운데) — T = 120 이면 t(119) 이고 문턱은 m=2: 2.27 → 1.98 · m=1: 1.98.
  t 가 서지 않으면(달 < 5 · 분산 0) p = 1(닫힌 실패).
Holm(batch_design_changes 1 · 2).
  가족 = 등록 커밋에 적은 1차 카드(REG["primary"] — P0 = q·π + (1−q)·α₁ ≥ 0.15 · T ≥ 84 · 밀도 F0 · 카드 외부 F0 를 모두 넘은 카드).
  m ∈ {0, 1, 2} 은 등록 커밋에 고정한다 — 등록 뒤 어떤 사건에도 바뀌지 않는다(R3 조건부 승격 없음 · 가족 안 카드는 p 가 없어도 p = 1 로 남는다).
  한쪽 가족 α 0.025 · 작은 p 부터 α/(m − j) · 처음 떨어진 곳에서 멈춘다.
관문(모두 점 추정 · 불리언이 아니면 멈춘다).
  R1 (i) 같은 달 γ_OS − γ_RS 평균 < 0 — 단 월 RS 종목 수 중앙값 ≥ 10(카드 F0 «관문 i 의 조건») 이 아니면 거짓(닫힌 실패)
     (ii) 52주 고점 괴리 + 12개월 수익을 더 통제해도 γ_OS 평균 < 0 · (iii) 시총가중 WLS 에서도 γ_OS 평균 < 0.
  R2 (i) WLS 에서도 γ_CH < 0 · (ii) Δlog(1A 단어수) 통제에도 γ_CH < 0 · 보고만: 결측 더미 계수 < γ_CH → «분리 실패 오염».
판정(카드마다 · 표본 안 통과는 채택이 아니다).
  가족 밖(P0 < 0.15 등) → «측정만»(단계 팔은 측정 팔) · 가족 안 → Holm 통과 ∧ 관문 전부 → «Stage M 통과 — 단계는 전방 판정»,
  Holm 통과 ∧ 관문 실패 → «기각 — 관문 … 미달», Holm 실패 → «기각». R3 → «측정만(가족 밖)» · R5 → «사건 수만».
  단계 팔의 채택 경로는 Stage M 통과 ∧ Stage S F0(편입당 교체 수 중앙값 2~15) 참일 때만 연다(forward_plan). 그 밖은 측정 팔.
  R1 팔은 §G 일치 시험, R2 팔은 §C 파서 검증을 통과해야 전방에서 연다(여기서는 상태만 싣는다).
F0(수익 없음 · 등록 전 --f0 가 data/_r_f0.json 에 쓰고 커밋 · 굽기 때 같은 판으로 다시 세어 바이트 수준으로 같아야 한다).
  커버리지(§F · 개수 ≥ 0.90 · 시총 ≥ 0.95 · 지도 위반 ≤ 2% · T ≥ 84) · 밀도(OS 중앙값 ≥ 20 · 최소 ≥ 5 · RS 중앙값 ≥ 10 · CH 중앙값 ≥ 30)
  · R2 외부(연간 유효 짝 ≥ 900 · 연도별 분리 실패 ≤ 20% · §C 파서 검증) · Stage S(교체 수 중앙값 2~15) · §G(행 일치 ≥ 99.5% · OS 불일치 ≤ 1%).

🚨 방화벽 — 이 파일은 등록 전에 실제 표지와 실제 미래 수익의 관계를 계산하지 않는다.
  굽기(main)는 frozen_check 를 넘어야만 돈다(RBATCH_COMMIT = 사전등록 문서를 처음 더한 커밋 · origin/main 조상 · 등록 값 빈칸 없음 ·
  ⟨TBD⟩ 없음 · 얼린 파일(가져오기 닫힘 전부) · 핀 · 고정표 · 판 · 환경). 등록 전에 되는 것은 다섯뿐이다 —
    --selftest     합성 자료만(판정 논리 · Holm · p · 관문 · F0 · 핀 · 검문점 · 끝에서 끝까지)
    --dry          구조 점검(상수 한 벌 · 얼린 파일 · 가져오기 닫힘 핀 · 등록 빈칸 · 새 자료 · 고정표 링크 · --check-reg) — 수익 없음 ·
                   하나라도 어긋나거나 빠지면 종료 코드 1
    --check-reg    REG = data/_r_p0.json = data/_r_f0.json(= _r_p0_counts.json 경계 세계) 대조를 등록 커밋 전에(양방향 · 수익 없음) ·
                   --rebuild 를 더하면 snap_wt 에서 F0 를 다시 세어 커밋할 F0 문서와 바이트 대조
    --f0           PIT 세계로 F0 표를 쓴다 — 패널을 짓자마자 y 를 NaN 으로 지운다(수익 없음) → data/_r_f0.json
    --smoke-real   눈가린 연기 시험 — 실제 표지 · 실제 통제에 **y 를 씨앗 고정 잡음으로 바꾼** 패널로 Stage M 전체를 돌리고,
                   Stage S 는 실제 세계 위에 **합성 표지**로 r_stages.run 을 qbatch_core.blind_smoke 에 넣는다(실제 표지 × 실제 가격은 계산하지 않는다).
                   산출물 · 검문점은 임시 폴더에 두고 열지 않고 지우며 수치는 찍지 않는다(구조 · 예외 · 초만).
  --smoke-synth 은 합성 세계로 러너 전체를 돌리고 결과를 찍는다(실제 자료 없음).

자료 어댑터 — 아직 빌드 중인 새 자료(발행사 지도 · 내부자 PIT · 10-Q 위험요인 · §D 사건 · §G 일치 · §C 검증)의 파일·필드 이름은
  RF 한 곳에만 적는다(표지 자체의 필드는 r_stagem.FIELDS · r_p0_adapt.FIELDS 가 맡는다). 이름이 바뀌면 여기만 고친다.
  R1 쌍둥이 T1~T6 은 정본 cikmonth.json 한 파일의 칸(r_r1_flags.cikmonth_doc · r_stagem.FIELDS["ins"]["twins"])이고 엔진 stage_m_r1 이
  돌린다(따로 파일을 두지 않는다 · 시도를 두 번 세지 않는다). R2 대조(SimDoc · iXBRL · 코로나)는 r_stagem.r2_variants 로 지어 stage_m_r2 에 넘긴다.
  R2 경계 분포의 세계 = r_stagem.boundary_world(2015-01 부터 · 가격 무관) — Stage M 표지 · 대조 · F0 외부 · Stage S 묶음이 모두 이 한 벌을 쓴다.
  R5 이름-월은 Stage S 모듈이 연결되면 그 묶음의 ALARM(r_r2flags.r5_events 정본) 하나에서 센다(§D _ev_flags 의 R5 는 모듈이 없을 때만).

  python build/r_run.py --selftest
  python build/r_run.py --dry
  python build/r_run.py --check-reg          (등록 커밋 전 · ④ 뒤 ⑦ 전 — PREREG §12)
  cd $TEMP/snap_wt && RBATCH_DATA=<저장소 data> python -X utf8 build/r_run.py --check-reg --rebuild
  cd $TEMP/snap_wt && RBATCH_DATA=<저장소 data> python -X utf8 build/r_run.py --f0 [--out 경로]
  cd $TEMP/snap_wt && RBATCH_DATA=<저장소 data> RBATCH_REPO=<저장소> RBATCH_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 \\
      python -X utf8 build/r_run.py
  (저장소 작업 트리는 가격 격자가 어긋나 pit_panel.load_world 가 멈춘다 — 자료 판 작업 사본 snap_wt 로 돌린다.
   얼린 파일은 실행 뿌리(snap_wt) 쪽을 등록 커밋과 대조하고, 새 자료는 RBATCH_DATA 쪽을 대조한다.)
"""
from __future__ import annotations
import hashlib, importlib, io, json, math, os, pickle, shutil, stat, subprocess, sys, tempfile, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from qbatch_core import mshift, months_between, quarterly_forms   # noqa: E402  달 산수 · 분기 편입(EG30 과 같다)

ROOT = os.path.dirname(HERE)                               # 실행 뿌리 — 얼린 코드 · 가격 세계(snap_wt 면 그 트리)
REPO = os.environ.get("RBATCH_REPO") or ROOT               # 등록 커밋이 있는 git 저장소(작업 사본이면 같은 객체를 본다)
RDATA = os.environ.get("RBATCH_DATA") or os.path.join(ROOT, "data")   # 배치 R 새 자료 · 산출물(r_stagem.RDATA 와 같은 뜻)

PREREG = "build/PREREG-2026-09-2x-RBATCH.md"               # 🚨 자리표시자 — 등록 때 날짜로 바꾼다(frozen_check 가 '2x' 를 막는다)
PREREG_CARDS = "build/PREREG-2026-09-2x-RBATCH-CARDS.md"   # 카드 원문(slate · data_build_plan · batch_design_changes 그대로)
RESULT = "build/PREREG-2026-09-2x-RBATCH-RESULT.md"
OUT_NAME, MARK_NAME, F0_NAME = "_rbatch.json", "_rbatch.started", "_r_f0.json"
PLACEHOLDER = "⟨TBD"                                       # 사전등록 문서의 빈칸 표시 — 등록 커밋 판에 하나라도 있으면 굽지 않는다

# ── 등록 규칙의 수(카드 원문 · batch_design_changes — 여기서 바꾸지 않는다 · --dry 가 r_stagem · r_p0 와 같은지 본다) ─────
M0, M1 = "2016-08", "2026-07"          # 신호월 t(보유 t+1 = 2016-09 ~ 2026-08)
T_NOMINAL, T_MIN = 120, 84
ALPHA = 0.025                          # Holm 가족 α(한쪽)
P0_GATE = 0.15
LAG = 3                                # NW(3)
F0_FLAG = {"OS": (20, 5), "RS": (10, None), "CH": (30, None)}   # 월 종목 수 (중앙값 ≥ · 최소 ≥)
F0_R2 = {"pairs_year": 900, "fail_rate": 0.20}
R2_PAIR_YEARS = tuple(str(y) for y in range(2015, 2026))   # 경계 분포가 쓰이는 해(신호월 Y 는 Y−1 분포 · 2016-08..2026-07 → 2015..2025)
R2_FAIL_YEARS = tuple(str(y) for y in range(2016, 2027))   # 표지가 쓰이는 공개 연도
F0_S = (2, 15)                         # Stage S 편입당 교체 수 중앙값
F0_G = {"row_match": 0.995, "os_mismatch": 0.01}
STAGE_S_N, STAGE_S_WIN = 30, {"R1": 3, "R2": 1}          # R1 OS 활성 = r−2..r · R2 CH_active 는 이미 t−2..t 창이다
SENS_2020 = "2020-07"                  # 미리 등록한 민감도(측정 · 엔진 SENS_FROM[1] 과 같다)
T2_SPLIT = "2023-04"                   # T2 10b5-1 판 전후 분할 보고(엔진 SPLIT_T2 와 같다 · 분할은 한 시도 안)
EPS = 1e-9                             # 엔진 요약 대조 허용
BOUND_FROM = "2015-01"                 # R2 경계 세계 첫 달(r_stagem.BOUND_FROM · r_p0.BW0 와 같다)
P0_Q, P0_A1, P0_TCRIT, P0_SCALE = 0.4, 0.0125, 2.27, 0.5   # P0 식의 상수(batch_design_changes 1 · 러너가 P0 를 다시 유도한다)
# 🔒 P0 바닥(2026-09-26 등록 전 결정 · META-2) — P0 = min(σ 규칙, 문헌 규칙) · t_alt_lit = 0.5·t_lit·√(T/T_lit) · r_p0.LIT 와 같아야 한다
P0_LIT = {"R1-OPPSELL": (3.44, 264), "R2-LAZYRF": (2.22, 240)}
P0_TOL = 1e-6                          # P0 재유도 허용(문서 값은 소수 6자리)
# 등록 전에 선언한 «돌리지 않는 시도»(엔진 trials 의 run=False 가운데 굽기를 막지 않는 것) — 그 밖의 못 돌린 시도는 등록 오류로 멈춘다
DECLARED_NOT_RUN = {"R1.sens2014": "2014-07 넓힌 창 — 편출 가격 복구 전에는 P_wide 가 없다(PREREG §4)",
                    "R2.sens2014": "2014-07 넓힌 창 — 편출 가격 복구 전에는 P_wide 가 없다(PREREG §4)"}
# Stage S 측정 팔(카드 controls) — 돌지 않으면 못 돌린 시도로 싣는다(조용히 잃지 않는다). R3 는 Stage S 모듈에 팔이 없다(선언).
S_ARMS = {"R1-OPPSELL": ("rule", "C1", "C2", "C3", "C4", "placebo"), "R2-LAZYRF": ("rule", "C2", "C3", "C4", "C5", "placebo"),
          "R12-STACK": ("rule",), "R3-8KNE": ("rule_monthly", "placebo", "hibeta")}
P0_DENS = {"R1": ("OS", "RS"), "R2": ("CH",)}   # r_p0.CARDS density_f0 가 보는 표지(OS 중앙값·최소 · RS 중앙값 | CH 중앙값)

CODES = {"R1": "R1-OPPSELL", "R2": "R2-LAZYRF", "R3": "R3-8KNE", "R5": "R5-ALARM"}
CANDIDATES = ("R1", "R2")              # 1차 후보(같은 자료 가족에 하나)
FAMILY = {"R1": "insider", "R2": "text"}
FOCAL = {"R1": "OS", "R2": "CH", "R3": "FL", "R5": "AL"}

V_PASS = "Stage M 통과 — 단계는 전방 판정"
V_REJ = "기각"
V_MEAS = "측정만"
V_R3 = "측정만(Holm 가족 밖 · 승격 없음)"
V_R5 = "사건 수만(수익 계산 없음 · 시도 수에 넣지 않는다)"
ARM_ADOPT = "채택 경로(전방 FF1 · FF2)"
ARM_MEAS = "측정 팔"

# ══ 등록 값 — 등록 커밋에서 채운다. None 이 하나라도 남으면 굽지 않는다 ═══════════════════════════════
REG = {
    "m": None,             # Holm 가족 크기 0 · 1 · 2 — data/_r_p0.json holm.m 과 같아야 한다
    "primary": None,       # 1차 카드(짧은 코드 · 길이 m) — 예 ["R1", "R2"] · ["R2"] · []
    "p0": None,            # {"R1": 0.xxxxxx 또는 None, "R2": …} — _r_p0.json 의 값(소수 6자리)
    "snap": None,          # P1 가격 핀 — stocks.json · pit_px.json 두 격자가 같고 검증을 통과한 가장 이른 커밋(§F)
    "base": None,          # P2 가격 밖 입력 핀
    "n_lab_prior": None,   # 등록 때 랩 누적 시도 수(forward_plan 약 716)
    "stage_s": None,       # Stage S 모듈 이름(build · run 을 가진 것 · 실제 굽기는 "r_stages" 만) — "none" 은 합성 · 연기 시험 전용
    "frozen_extra": None,  # 자료 빌더 등 등록 때 확정하는 얼린 파일(튜플 · 없으면 ())
}

# ══ 얼린 파일 · 핀 ═════════════════════════════════════════════════════════════════════════════
# 굽기 경로가 가져오는 build/ 모듈 전부(import_closure 가 정적으로 세어 대조한다 — 여기 없는 모듈이 닫힘에 있으면 --dry · 굽기가 멈춘다).
#   qbatch_run(Stage S Δβ · β̂ · 위약 · both_side) · refresh_events(NYSE 휴장 · 조기폐장 달력 → 가용일) · q_bmrot_leg(qbatch_run) ·
#   q_ltd(r_stages Q07 명단 — 굽기 경로 밖이어도 닫힘에 있어 얼린다) · edgar · ml_core · ml_strats · pit_backtest(tech_backtest 가 가져온다)
CODE_FROZEN = ("build/r_run.py", "build/r_stagem.py", "build/r_stages.py", "build/r_p0.py", "build/r_p0_adapt.py", "build/r_r1_flags.py", "build/r_r2flags.py",
               "build/issuer_map.py", "build/qbatch_core.py", "build/eg30plus.py", "build/qg_lab.py", "build/pit_panel.py",
               "build/pit_quarantine.py", "build/stoploss.py", "build/tech_backtest.py", "build/rally_pattern.py", "build/index_members.py",
               "build/qbatch_run.py", "build/refresh_events.py", "build/q_bmrot_leg.py", "build/q_ltd.py",
               "build/edgar.py", "build/ml_core.py", "build/ml_strats.py", "build/pit_backtest.py",
               "build/pit_alias.py",           # 2026-09-26 — pit_panel 이 가져오는 날짜 인식 별칭(가격 키 · 명단 고치기) · 닫힘에 든다
               PREREG, PREREG_CARDS)
P3_FROZEN = ("data/pit_gics_sectors.json", "data/_eg_q5_scores_pitgics.json", "data/_eg_q5_scores_pitgics_pre.json",
             "data/_eg_q5_scores.json", "data/mech_episodes.json", "data/_eg30plus.json")
SNAP_FILES = ("data/stocks.json", "data/pit_px.json", "data/sd")
BASE_FILES = ("data/bench_px.json", "data/rf_monthly.json", "data/index_history.json", "data/index_ledger.json", "data/pit_universe.json",
              "data/pit_reuse.json", "data/fx", "data/fx_pit", "data/assets.json", "data/splits.json", "data/shares_yf.json",
              "data/cik_map.json")
# 새 자료(RBATCH_DATA 기준 · 저장소 경로는 data/<이것>) — 등록 커밋과 blob 이 같아야 한다.
#   R1 쌍둥이 T1~T6 은 cikmonth.json 안의 칸이다(따로 파일 없음 · r_r1_flags.cikmonth_doc).
#   2026-09-26 — 실제 파일 이름으로 고쳤다(§G 일치 시험 = _ins_daily/test_2026q2.json · §C 검증 = _tenq_rf/validation.json) ·
#   r_stagem 이 읽는 둘을 더했다(_issuer_map_sector_manual.json = SectorAt 섹터 더미 · _r_ytrunc.json = 보유월 y 이름별 판정).
NEW_DATA = ("_issuer_map.json", "_issuer_map_manifest.json", "_issuer_map_manual.json", "_issuer_map_sector_manual.json",
            "_ins_pit/manifest.json", "_ins_pit/cikmonth.json", "_ins_pit/routine.json", "_ins_daily/test_2026q2.json",
            "_sub_pit.json.gz", "_tenq_rf.json", "_tenq_rf/validation.json", "_ev_flags.json", "_r_ytrunc.json",
            "_r_p0.json", "_r_p0_counts.json", F0_NAME)
# 있으면 읽히는 입력(선택) — 커밋과 로컬 모두에 없으면 «없음» 으로 싣고, 어느 한쪽에만 있거나 내용이 다르면 멈춘다.
#   _px_raw.json = r_stagem 시총 가격(원 종가 · 없으면 배당조정 판) · _t401.json = R5 4.01 본문(r_stages · r_r2flags.load_t401) ·
#   _r_coverage.json = r_stages · r_p0_adapt 가 읽는 §F 달 관문
NEW_DATA_OPT = ("_px_raw.json", "_t401.json", "_r_coverage.json")
# 굽기에서 있으면 안 되는 파일 — 덮어쓰기 표지(r_stages · r_p0_adapt 옵트인 · 정식 빌더를 가린다)
FORBID_DATA = ("_r_flags.json",)

# ══ 자료 어댑터 — 파일 · 필드 이름은 여기 한 곳(빌더가 이름을 정하면 여기만 고친다) ═══════════════════════════
RF = {
    # r_p0.py run 의 문서(data/_r_p0.json · r_p0.decide/run 이 정한 모양 — 2026-09-25 판)
    "p0": {"file": "_r_p0.json", "cards": "cards", "holm": "holm", "m": "m", "members": "members", "p0": "p0", "T": "T",
           "eligible": "eligible", "density_pass": "density_pass", "external": "external_f0", "status": "status",
           "keep": ("p0", "pi", "t_alt", "sigma_analytic", "sigma_placebo", "sigma_plan", "binding", "T", "p0_pass", "T_pass",
                    "density_pass", "external_f0", "eligible", "sigma_max_for_gate", "gamma_lit", "status", "dropped", "count_src"),
           "sha": "result_sha",
           "sha_keys": ("formula", "constants", "universe", "cards", "holm")},   # r_p0.run 의 result_sha 식(json.dumps · sort_keys)
    # §C 파서 검증(손 라벨 100 · LM 순위상관 · JNJ ix:header …) — 합격 불리언
    "parser_c": {"file": "_tenq_rf/validation.json", "pass": ("registered_pass", "pass", "ok", "passed")},   # 2026-09-26 실제 파일 · 등록 판(v3) 합격
    # r_r2flags.r2_density(R) 결과의 연도별 칸
    "r2_density": {"by_year": "by_year", "pairs": "valid_world", "fail": "fail_rate"},
    # §G 일간 XML 대 DERA 일치 시험(2026Q2) — R1 전방 팔을 여는 조건
    "g_check": {"file": "_ins_daily/test_2026q2.json", "row_match": ("row_match", "row_match_rate"),         # 2026-09-26 실제 파일
                "os_mismatch": ("os_flag_mismatch", "os_mismatch", "os_mismatch_rate")},
    # §D 사건 표지 — 값은 [[그룹, 달], …] 또는 {판: [[그룹, 달], …]} (그룹-월 = 그달 말 표지가 켜짐)
    "ev": {"file": "_ev_flags.json", "R3": ("r3", "R3", "fl"), "R5": ("r5", "R5", "alarm"), "primary": ("primary", "main")},
    # 대조 표지 — R2 는 r_stagem.r2_variants 의 키(stage_m_r2 fp_doc · fp_ixbrl · fp_covid) · R3 는 §D _ev_flags 의 판 이름
    "variants_r2": {"doc": "fp_doc", "ixbrl": "fp_ixbrl", "covid": "fp_covid"},
    "twins_r3": ("long", "good", "bad", "w5"),
    # R1 쌍둥이 · 표본 칸(cikmonth 안 · r_stagem.ins_flags 가 옮긴 이름) — 하나라도 없으면 실제 굽기는 Stage M 전에 멈춘다
    "need_r1": ("OS", "RS", "SALL", "CLS", "OS_T1", "OS_T1C", "OS_T2", "RS_T2", "OS_T4", "RS_T4", "OS_T6", "RS_T6"),
    # P0 개수 표(r_p0 build_counts) — R2 경계 세계 요약(r_p0.member_world) · 표지 출처
    "p0_counts": {"file": "_r_p0_counts.json", "bworld": "r2_boundary_world", "first": "first", "n": "n", "ok": "ok"},
    # 고정표(원본은 저장소 밖 RBATCH_RAW) — 항목 모음 키 · sha 칸 · 원본 상대 경로 칸(없으면 키 + gz_default)
    "manifests": {"_ins_pit/manifest.json": {"root": "zips", "sha": "sha256", "path": "path", "gz_default": None},
                  "_issuer_map_manifest.json": {"root": "files", "sha": "sha256", "path": "path", "gz_default": ".gz"}},
    # 파생 파일이 적은 고정표 sha256(키 경로) → 대상 · 확정 = 빌더 판에서 맞춰 본 이름 · 잠정 = 빌더가 정하면 고친다
    "links": (("_issuer_map.json", ("pins", "ins_manifest"), "data/_ins_pit/manifest.json", "확정"),
              ("_issuer_map.json", ("pins", "im_manifest"), "data/_issuer_map_manifest.json", "확정"),
              ("_issuer_map.json", ("pins", "manual"), "data/_issuer_map_manual.json", "확정"),
              ("_issuer_map.json", ("pins", "script"), "build/issuer_map.py", "확정"),
              # 2026-09-26 — 빌더 판에 맞췄다: cikmonth 의 내부자 고정표 sha 는 pins.panel_pins.ins_manifest(ins_pit_build 가
              #   패널을 만든 판 · density.json pins 를 옮긴 것 — pins 바로 아래에는 없다) · _tenq_rf 는 pins 가 없고 inputs.issuer_map
              #   (tenq_rf_build 가 입력 sha 를 inputs 에 적는다). 둘 다 지금 파일과 «일치» 를 확인하고 확정으로 올렸다.
              ("_ins_pit/cikmonth.json", ("pins", "panel_pins", "ins_manifest"), "data/_ins_pit/manifest.json", "확정"),
              ("_ins_pit/cikmonth.json", ("pins", "issuer_map"), "data/_issuer_map.json", "확정"),
              ("_tenq_rf.json", ("inputs", "issuer_map"), "data/_issuer_map.json", "확정")),
    # Stage S 모듈 계약(REG["stage_s"] = 모듈 이름) — build/r_stages.py(2026-09-25 판): 교체 수는 build(View, bundle) 의 cards[코드].f0.n_r
    # ({편입: n_r} · 수익 없음), 측정 팔은 run(ctx, bundle) 의 {코드: CardResult}(등록 커밋 뒤 · 실제 표지면 RBATCH_COMMIT 필요)
    "stage_s": {"load_bundle": "load_bundle", "view": "View", "build": "build", "run": "run", "cards": "cards", "f0": "f0", "n_r": "n_r",
                "excluded": "excluded", "ok": "ok", "hash": "hash", "v0_hash": "v0_hash", "synth_bundle": "synth_bundle",
                "issuer_map": "IssuerMap", "months": "months",
                "codes": {"R1": "R1-OPPSELL", "R2": "R2-LAZYRF"}, "extra": ("R12-STACK", "R5-ALARM"), "consts": ("F0_NR", "N_TOP", "WINDOW"),
                # Stage M 표지 이름 ↔ 묶음 표지 이름(같은 칸이 켜졌는지 대조) · R5 경보
                "agree": {"R1": ("OS", "OS"), "R2": ("CH", "CH")}, "alarm": "ALARM"},
}


def _S():
    import r_stagem as S                     # 엔진 — 처음 쓸 때 읽는다(합성 시험도 같은 엔진을 탄다)
    return S


def _E():
    import eg30plus as E                     # nw_t — 복제하지 않는다
    return E


def _rel(p):
    return os.path.join(*p.split("/"))


def _rj(path):
    if not path or not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def _js(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if hasattr(o, "item"):
        return o.item()
    if isinstance(o, set):
        return sorted(o)
    if isinstance(o, tuple):
        return list(o)
    return str(o)


def _canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_js)


def _roundtrip(o):
    return json.loads(_canon(o))


def _sha_json(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()


def _sha_lf(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def _sha_file(path, gz=False):
    h = hashlib.sha256()
    if gz:
        import gzip
        f = gzip.open(path, "rb")
    else:
        f = open(path, "rb")
    with f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _dig(J, keys):
    for k in keys:
        if not isinstance(J, dict) or k not in J:
            return None
        J = J[k]
    return J


def _pick(rec, names):
    for n in names:
        if isinstance(rec, dict) and n in rec:
            return rec[n]
    return None


def _rmtree(p):
    def onerr(func, path, _exc):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    if os.path.isdir(p):
        shutil.rmtree(p, onerror=onerr)


def _imports_of(path, bdir):
    """파일 하나가 가져오는 build/ 모듈(정적 — import · from · __import__("x") · importlib.import_module("x") · _canon_mod("x")).
    함수 안 늦은 import 도 센다(sys.modules 로는 부른 적 없는 늦은 import 를 놓친다)."""
    import ast
    with io.open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            out.add(n.module.split(".")[0])
        elif isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
            f = n.func
            nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if nm in ("__import__", "import_module", "_canon_mod"):
                out.add(n.args[0].value.split(".")[0])
    return {m for m in out if os.path.isfile(os.path.join(bdir, m + ".py"))}


_CLOSURE = {}


def import_closure(roots=("r_run",), bdir=None):
    """굽기 경로의 build/ 모듈 닫힘 → ["build/<모듈>.py", …](정렬). roots 에 REG["stage_s"] 모듈을 더해 부른다(한 프로세스 안에서 한 번 센다)."""
    bdir = bdir or HERE
    key = (tuple(r for r in roots if r), bdir)
    if key in _CLOSURE:
        return list(_CLOSURE[key])
    seen, todo = set(), [r for r in roots if r and os.path.isfile(os.path.join(bdir, r + ".py"))]
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        todo.extend(sorted(_imports_of(os.path.join(bdir, m + ".py"), bdir) - seen))
    _CLOSURE[key] = sorted("build/%s.py" % m for m in seen)
    return list(_CLOSURE[key])


def closure_unpinned(reg=None, bdir=None):
    """가져오기 닫힘 가운데 얼린 목록(CODE_FROZEN + REG frozen_extra)에 없는 파일 — 비어야 굽는다."""
    reg = REG if reg is None else reg
    roots = ("r_run",) + ((reg.get("stage_s"),) if reg.get("stage_s") not in (None, "none") else ())
    frozen = set(CODE_FROZEN) | set(reg.get("frozen_extra") or ())
    return [p for p in import_closure(roots, bdir) if p not in frozen]


def name_check(prereg=None, cards=None, result=None):
    """사전등록 · 카드 원문 · 결과 문서 이름 — 셋 모두 자리표시자('2x')가 아니고 같은 날짜 줄기(build/PREREG-<날짜>-RBATCH…)인가. 문제 목록."""
    names = {"PREREG": prereg or PREREG, "PREREG_CARDS": cards or PREREG_CARDS, "RESULT": result or RESULT}
    bad = ["%s 이름이 자리표시자다(%s)" % (k, v) for k, v in names.items() if "2x" in v]
    stem = names["PREREG"][:-len("-RBATCH.md")] if names["PREREG"].endswith("-RBATCH.md") else None
    if stem is None:
        bad.append("PREREG 이름이 …-RBATCH.md 모양이 아니다(%s)" % names["PREREG"])
    else:
        for k, suf in (("PREREG_CARDS", "-RBATCH-CARDS.md"), ("RESULT", "-RBATCH-RESULT.md")):
            if names[k] != stem + suf:
                bad.append("%s 이름 %s 가 PREREG 날짜 줄기(%s%s)와 다르다" % (k, names[k], stem, suf))
    return bad


# ══ 통계 — p · 문턱 · 주 통계 ═════════════════════════════════════════════════════════════════════
def one_sided_p(t, T):
    """H1 γ < 0 의 한쪽 p = P(t(T−1) ≤ t). t 가 서지 않으면 1(닫힌 실패)."""
    from scipy.stats import t as td
    if t is None or T is None or T < 2 or not np.isfinite(t):
        return 1.0
    return float(td.cdf(t, T - 1))


def crit_t(alpha, T):
    """한쪽 문턱 크기 — t ≤ −crit 이면 α 에서 기각. T = 120 · α 0.0125 → 2.27 · 0.025 → 1.98."""
    from scipy.stats import t as td
    return float(td.ppf(1 - alpha, T - 1))


def _vals(series):
    return [float(v) for v in (series or []) if v is not None and np.isfinite(v)]


def _mno(ym):
    return int(ym[:4]) * 12 + int(ym[5:7]) - 1


def primary_stat(series, months=None):
    """γ 월 계열(None = 계수가 서지 않은 달) → T · 평균 · SD · NW(3) t · 자유도 · 한쪽 p · 빈 달 수.
    months(계열과 같은 길이의 신호월 — 엔진 fm 의 res["months"])를 주면 달력 위치를 지킨다: 쓴 달이 이어지면 eg30plus.nw_t,
    빈 달이 끼면 r_stagem.nw_t_gap(엔진 summarize 와 한 정의 · 복제하지 않고 부른다). months 가 없으면 이어진 계열로 본다(시험용).
    🚨 굽기는 늘 months 를 준다 — 압축 계열 NW t 를 주 통계로 쓰면 빈 달이 낀 달력에서 엔진과 갈린다."""
    ser = list(series or [])
    if months is not None and len(months) != len(ser):
        raise SystemExit("🚨 γ 계열 길이 %d 가 달 목록 길이 %d 와 다르다." % (len(ser), len(months)))
    keys = list(months) if months is not None else list(range(len(ser)))
    pr = sorted((m, float(v)) for m, v in zip(keys, ser) if v is not None and np.isfinite(v))
    T = len(pr)
    if T < 5:
        return {"T": T, "mean": None, "sd": None, "nw_t": None, "nw_t_compressed": None, "contiguous": None, "gaps": None,
                "df": max(T - 1, 0), "p_one": 1.0}
    x = np.array([v for _, v in pr], float)
    gaps = 0 if months is None else _mno(pr[-1][0]) - _mno(pr[0][0]) + 1 - T
    t_c = _E().nw_t(x, LAG)
    t = t_c if gaps == 0 else _S().nw_t_gap([m for m, _ in pr], x, LAG)
    return {"T": T, "mean": float(x.mean()), "sd": float(x.std(ddof=1)), "nw_t": t, "nw_t_compressed": None if gaps == 0 else t_c,
            "contiguous": gaps == 0, "gaps": int(gaps), "first": pr[0][0] if months is not None else None,
            "last": pr[-1][0] if months is not None else None, "df": T - 1, "p_one": one_sided_p(t, T)}


def holm_fixed(stats, m, family, alpha=ALPHA):
    """Holm(한쪽) — stats = {카드: primary_stat} · family = 등록한 1차 카드(길이 m · 등록 커밋에 고정).
    🚨 m 은 받은 그대로 쓴다. 가족과 통계 카드가 다르면 멈춘다(등록 뒤 사건으로 가족이 줄거나 늘지 않게)."""
    family = list(family or [])
    if m not in (0, 1, 2):
        raise SystemExit("🚨 Holm m = %r — 0 · 1 · 2 만 된다(등록 커밋에 고정)." % (m,))
    if len(family) != m or len(set(family)) != m:
        raise SystemExit("🚨 가족 %s 의 크기가 고정 m %d 과 다르다." % (family, m))
    if set(stats) != set(family):
        raise SystemExit("🚨 Holm 에 들어온 카드 %s 가 가족 %s 와 다르다." % (sorted(stats), sorted(family)))
    rows, alive = {}, True
    order = sorted(family, key=lambda c: (stats[c]["p_one"], c))
    for j, c in enumerate(order):
        a = alpha / (m - j)
        s = stats[c]
        ok = bool(alive and s["p_one"] <= a + 1e-15)
        rows[c] = {"rank": j + 1, "p": s["p_one"], "alpha": a, "t": s["nw_t"], "T": s["T"],
                   "crit_t": crit_t(a, s["T"]) if s["T"] and s["T"] >= 2 else None, "pass": ok}
        alive = ok
    return {"m": m, "family": family, "alpha": alpha, "order": order, "rows": rows}


# ══ 관문 ═══════════════════════════════════════════════════════════════════════════════════════
def _mean(series):
    v = _vals(series)
    return float(np.mean(v)) if v else None


def _mean_diff(a, b):
    d = [float(u) - float(v) for u, v in zip(a or [], b or []) if u is not None and v is not None and np.isfinite(u) and np.isfinite(v)]
    return float(np.mean(d)) if d else None


def gates_r1(rec, rs_f0_ok):
    """R1 관문(점) — (i) 같은 달 γ_OS − γ_RS · (ii) 추가 통제판 γ_OS · (iii) WLS 판 γ_OS. raw = F0 조건 전의 값(엔진 대조용)."""
    v = {"i": _mean_diff(rec["main"]["OS"], rec["main"]["RS"]), "ii": _mean(rec["extra"]["OS"]), "iii": _mean(rec["wls"]["OS"])}
    raw = {k: bool(x is not None and x < 0) for k, x in v.items()}
    g, notes = dict(raw), {}
    if rs_f0_ok is not True:
        g["i"] = False
        notes["i"] = "월 RS 종목 수 중앙값 < 10(또는 미확인) — 관문 i 를 판정할 수 없다(닫힌 실패)"
    return {"gates": g, "raw": raw, "all": all(g.values()), "vals": v, "notes": notes}


def gates_r2(rec):
    """R2 관문(점) — (i) WLS 판 γ_CH · (ii) Δlog(1A 단어수) 통제판 γ_CH · 보고만: 결측 더미 < γ_CH → 분리 실패 오염."""
    v = {"i": _mean(rec["wls"]["CH"]), "ii": _mean(rec["len"]["CH"]), "miss": _mean(rec["main"]["CH_miss"]), "ch": _mean(rec["main"]["CH"])}
    g = {k: bool(v[k] is not None and v[k] < 0) for k in ("i", "ii")}
    contam = bool(v["miss"] is not None and v["ch"] is not None and v["miss"] < v["ch"])
    return {"gates": g, "raw": dict(g), "all": all(g.values()), "vals": v, "contam": contam, "notes": {}}


def engine_check(card, rec, stat, gates):
    """러너가 다시 낸 주 통계 · 관문이 엔진(r_stagem)의 요약 · 관문과 같은가 — 다르면 멈춘다(두 벌이 갈리지 않게).
    주 통계는 T · 평균 · NW t(달력 위치) · 한쪽 p · 빈 달 수를, 관문은 F0 조건을 건 뒤의 값(엔진에 rs_f0_ok 를 넘긴다)과 오염 보고를 본다."""
    es = rec.get("engine_sum")
    if es:
        for k in ("T", "mean", "nw_t", "p_one", "gaps"):
            if k not in es:
                continue
            a, b = es.get(k), stat.get(k)
            if k == "p_one" and a is None:
                a = 1.0
            if (a is None) != (b is None) or (a is not None and abs(float(a) - float(b)) > EPS * max(1.0, abs(float(b)))):
                raise SystemExit("🚨 %s 주 통계 %s 가 엔진(%r)과 러너(%r)에서 다르다." % (card, k, a, b))
    eg = rec.get("engine_gates")
    if eg and gates:
        keys = list(gates["gates"]) + (["contam"] if "contam" in gates else [])
        for k in keys:
            if type(eg.get(k)) is not bool:
                raise SystemExit("🚨 %s 엔진 관문 %s 가 불리언이 아니다(%r)." % (card, k, eg.get(k)))
            mine = gates["contam"] if k == "contam" else gates["gates"][k]
            if eg[k] != mine:
                raise SystemExit("🚨 %s 관문 %s 가 엔진(%s)과 러너(%s)에서 다르다." % (card, k, eg[k], mine))


# ══ F0 규칙(순수 함수 · 수익 없음) ════════════════════════════════════════════════════════════════
def f0_flag_ok(flag, counts):
    rule = F0_FLAG.get(flag)
    if rule is None:
        return None
    v = list(counts)
    if not v:
        return False
    return bool(float(np.median(v)) >= rule[0] and (rule[1] is None or min(v) >= rule[1]))


def f0_r2_external(ext):
    """R2 카드 외부 F0 — 연간 유효 짝 ≥ 900(R2_PAIR_YEARS) · 연도별 분리 실패 ≤ 20%(R2_FAIL_YEARS) · §C 파서 검증."""
    if ext is None:
        return {"ok": None, "why": "자료 없음"}
    py = {y: n for y, n in (ext.get("pairs_year") or {}).items() if y in R2_PAIR_YEARS}
    fr = {y: r for y, r in (ext.get("fail_rate") or {}).items() if y in R2_FAIL_YEARS}
    miss_p = [y for y in R2_PAIR_YEARS if y not in py]
    miss_f = [y for y in R2_FAIL_YEARS if y not in fr]
    ok_p = not miss_p and all(n is not None and n >= F0_R2["pairs_year"] for n in py.values())
    ok_f = not miss_f and all(r is not None and r <= F0_R2["fail_rate"] for r in fr.values())
    pc = ext.get("parser_c")
    ok = False if (not ok_p or not ok_f or pc is False) else (None if pc is None else True)
    return {"ok": ok, "pairs_ok": ok_p, "fail_ok": ok_f, "parser_c": pc, "pairs_year": py, "fail_rate": fr,
            "missing_years": {"pairs": miss_p, "fail": miss_f}, "rule": dict(F0_R2)}


def f0_stage_s(nr, unmapped=0):
    """Stage S F0 — 편입당 교체 수 중앙값 2~15(벗어나면 측정 불가). 셈 규칙(모듈 · 잠정 여부)은 F0 문서의 stage_s_rule 에 따로 적는다
    (등록 전 판과 등록 뒤 판이 규칙 표기만으로 갈리지 않게 — 규칙이 바뀌면 교체 수가 바뀌어 대조가 잡는다)."""
    if nr is None:
        return {"ok": None, "why": "표지 없음 또는 Stage S 미연결"}
    if not len(nr):
        return {"ok": None, "why": "편입 없음"}
    med = float(np.median(nr))
    return {"median": med, "min": int(min(nr)), "max": int(max(nr)), "n_forms": len(nr), "unmapped": int(unmapped),
            "ok": bool(F0_S[0] <= med <= F0_S[1]), "rule": list(F0_S), "n_r": [int(x) for x in nr]}


def f0_g(g):
    """§G 일치 시험 — 행 일치 ≥ 99.5% · 회사-월 OS 불일치 ≤ 1%. 없으면 None(R1 전방 팔을 열 수 없다)."""
    if not g:
        return {"ok": None, "why": "일치 시험 없음"}
    rm, om = g.get("row_match"), g.get("os_mismatch")
    ok = None if (rm is None or om is None) else bool(rm >= F0_G["row_match"] and om <= F0_G["os_mismatch"])
    return {"ok": ok, "row_match": rm, "os_mismatch": om, "rule": dict(F0_G)}


def count_nr(P, fp, flag, win, forms, group_of, n=STAGE_S_N):
    """러너 기본 Stage S 교체 수 — 편입 r 의 Eg 상위 n 가운데 가용월 r−win+1..r 에 표지가 켜진 그룹 수(수익 없음).
    그룹을 풀 수 없는 이름(표본 밖 · 지도 미해결)은 세지 않고 unmapped 로 센다."""
    out, unm = [], 0
    for r in forms:
        top = (P["eg_rank"].get(r) or [])[:n]
        c = 0
        for k in top:
            g = group_of(k, r)
            if g is None:
                unm += 1
                continue
            if any(((fp.get((g, mshift(r, -j))) or {}).get(flag) or 0) >= 1 for j in range(win)):
                c += 1
        out.append(c)
    return out, unm


def fp_digest(fp):
    """표지 판 지문 — (그룹, 달, 칸, 값) 정렬 + months_ok."""
    if fp is None:
        return None
    h = hashlib.sha256()
    for k in sorted(fp, key=lambda x: (str(x[0]), str(x[1]))):
        rec = fp[k] or {}
        items = sorted((str(a), (None if b is None else (round(float(b), 12) if isinstance(b, (int, float, np.floating)) else str(b))))
                       for a, b in rec.items())
        h.update(json.dumps([str(k[0]), str(k[1]), items], ensure_ascii=False).encode("utf-8"))
    mo = getattr(fp, "months_ok", None)
    h.update(json.dumps(sorted(mo) if mo is not None else None).encode("utf-8"))
    return h.hexdigest()


def world_info(world, stats=None):
    """R2 경계 세계 {(그룹, 달)} → 지문 · 크기 · 첫 달 · 끝 달 · 연도별 그룹-월 수(F0 문서에 싣고 굽기가 바이트로 대조)."""
    by = {}
    for _, m in world:
        by[m[:4]] = by.get(m[:4], 0) + 1
    ms = sorted({m for _, m in world})
    return {"sha": hashlib.sha256(json.dumps(sorted([str(g), m] for g, m in world)).encode("utf-8")).hexdigest(), "n": len(world),
            "first": ms[0] if ms else None, "last": ms[-1] if ms else None, "by_year": dict(sorted(by.items())),
            "rule": "r_stagem.boundary_world(%s..%s · 비금융 · FPI 아님 · 지도가 푼 그룹 · 가격 무관)" % (BOUND_FROM, M1),
            "stats": {k: v for k, v in (stats or {}).items() if k != "by_year"}}


def r2_world_check(info):
    """경계 세계가 BOUND_FROM(2015-01)부터 M1 해까지 해마다 그룹-월을 담는가 — 아니면 멈춘다(패널 세계로 재면 2016 경계가 없다)."""
    if not info or not info.get("n"):
        raise SystemExit("🚨 R2 경계 세계가 비었다 — r_stagem.boundary_world 로 지어라.")
    miss = [str(y) for y in range(int(BOUND_FROM[:4]), int(M1[:4]) + 1) if not (info.get("by_year") or {}).get(str(y))]
    if info["first"] > BOUND_FROM or miss:
        raise SystemExit("🚨 R2 경계 세계가 %s 부터다(필요 %s) · 빈 해 %s — 패널 행 세계가 아니라 boundary_world 를 넘겨라." % (info["first"], BOUND_FROM, miss))
    return True


def r2_bounds_check(R, window=(M0, M1)):
    """정본 경계(r_r2flags.boundaries)가 창 안 공개연도마다 호출자 세계(경계 세계) 12달로 섰는가 — 'uncovered_all'(세계가 덮지 않은 달을
    §C 전체로 메운 것)이나 'all' 이 섞이면 멈춘다(반쪽 세계의 경계 · 카드 (7) «직전 달력연도 세계 전체 짝» 이 아니다)."""
    bad = []
    for y in range(int(mshift(window[0], -2)[:4]), int(window[1][:4]) + 1):
        b = R["bounds"].get(y, R["bounds"].get(str(y)))
        if not isinstance(b, dict) or b.get("cut") is None:
            bad.append((y, "경계 없음"))
            continue
        src = b.get("src") or {}
        odd = sorted(k for k in src if not str(k).startswith("caller"))
        if odd or b.get("world_months") != 12:
            bad.append((y, "출처 %s · 세계 달 %s" % (odd or sorted(src), b.get("world_months"))))
    if bad:
        raise SystemExit("🚨 R2 경계가 경계 세계 12달로 서지 않은 공개연도 %s — boundary_world(%s 부터)를 넘겨라." % (bad[:6], BOUND_FROM))
    return True


def r2_flag_set(world, path=None, im_path=None, window=(M0, M1)):
    """R2 표지 한 벌(정본 r_r2flags 경로 · 경계 세계 = world) → ({'rf','doc','ixbrl','covid'} FlagPanel, R 1차 판).
    r_stagem.r2_variants(stage_m_r2 가 받는 네 판) 그대로 · 1차 판 R(밀도 · 경계)은 tenq_canonical 로 한 번 더 지어 같은 표지인지 대조한다."""
    S = _S()
    got = S.tenq_canonical(path, world=world, im_path=im_path, window=window)
    var = S.r2_variants(path, world=world, im_path=im_path, window=window)
    if got is None or var is None:
        raise SystemExit("🚨 r_r2flags(정본)를 가져올 수 없다 — 잠정 tenq_flags 로는 굽지 않는다.")
    if fp_digest(var["rf"]) != fp_digest(got[0]):
        raise SystemExit("🚨 r2_variants 1차 판이 tenq_canonical 과 다르다.")
    r2_bounds_check(got[1], window)
    return var, got[1]


def f0_all(S, prov, P, fps, months):
    """F0 표 한 벌(수익 없음) — 커버리지 · 밀도 · R2 외부 · R2 경계 세계 · Stage S · §G · 지도. --f0 과 굽기가 같은 함수를 부른다."""
    ms = set(months)
    cov = {"T": len(months), "ok": len(months) >= T_MIN, "first": months[0] if months else None, "last": months[-1] if months else None,
           "months_sha": _sha_json(list(months)), "fail": [m for m in P["months"] if m not in ms]}
    rw = prov.r2_world_info()
    r2_world_check(rw)
    dens = {}
    for flag, c in (("OS", "R1"), ("RS", "R1"), ("SALL", "R1"), ("CH", "R2"), ("FL", "R3")):
        fp = fps.get(c)
        if fp is None:
            dens[flag] = {"ok": None, "why": "표지 없음"}
            continue
        d = S.f0_density(P, fp, flag, months)
        mine = f0_flag_ok(flag, list(d["by_month"].values()))
        if flag in F0_FLAG and d["ok"] is not None and bool(d["ok"]) != mine:
            raise SystemExit("🚨 밀도 F0(%s) 가 엔진(%s)과 러너(%s)에서 다르다." % (flag, d["ok"], mine))
        dens[flag] = {"median": d["median"], "min": d["min"], "ok": mine, "rule": F0_FLAG.get(flag), "by_month": d["by_month"]}
    ss = {}
    for c in CANDIDATES:
        nr, unm = prov.stage_s_nr(c, fps.get(c), FOCAL[c], STAGE_S_WIN[c])
        ss[c] = f0_stage_s(nr, unm)
        ex = prov.stage_s_card(c, fps.get(c)) if hasattr(prov, "stage_s_card") else None
        if ex is not None:                                  # 모듈 판 — 모듈 자신의 판정 · 뺀 편입 · 목표 해시 · 표지 일치
            if ss[c].get("ok") is not None and ex.get("ok") is not None and bool(ex["ok"]) != ss[c]["ok"]:
                raise SystemExit("🚨 Stage S F0(%s) 가 모듈(%s)과 러너(%s)에서 다르다." % (c, ex["ok"], ss[c]["ok"]))
            ss[c].update({k: ex[k] for k in ("module_ok", "excluded", "targets_hash", "flag_agree") if k in ex})
    im = {"bad_months": [m for m in P["months"] if (P["stat"].get(m) or {}).get("im_ok") is False]}
    out = {"coverage": cov, "density": dens, "r2_external": f0_r2_external(prov.r2_external()), "r2_world": rw, "stage_s": ss,
           "g_concord": f0_g(prov.g_concord()), "issuer_map": im}
    if hasattr(prov, "stage_s_hashes"):
        out["stage_s_hashes"] = prov.stage_s_hashes()      # 등록에 얼릴 Stage S 목표 해시(수익 없음) — 굽기의 targets_hash 와 같아야 한다
    return out


# ══ 자격(P0 문서) · 등록 값 대조 ════════════════════════════════════════════════════════════════════
def p0_rederive(r, const, code=None):
    """P0 문서 카드 한 장의 식을 다시 푼다 — σ_plan = max(σ_analytic, σ_placebo) · t_alt = 0.5·|γ_lit|·√T / σ_plan ·
    π = 1 − Φ(2.27 − t_alt) · P0_σ = q·π + (1 − q)·α₁ · (2026-09-26 바닥) t_alt_lit = 0.5·t_lit·√(T/T_lit) · π_lit · P0_lit ·
    P0 = min(P0_σ, P0_lit)(문헌 입력은 러너의 P0_LIT — 카드 code 가 없으면 바닥 없이). 돌려주는 것 {sigma_plan, t_alt, pi, p0, …}."""
    from scipy.stats import norm
    sa, sp = r.get("sigma_analytic"), r.get("sigma_placebo")
    splan = max(sa, sp) if sa is not None else sp
    ta = const["alt_scale"] * abs(r["gamma_lit"]) * math.sqrt(r["T"]) / splan
    pi = float(norm.sf(const["t_crit"] - ta))
    ps = const["q"] * pi + (1 - const["q"]) * const["alpha1"]
    out = {"sigma_plan": splan, "t_alt": ta, "pi": pi, "p0_sigma": ps, "p0": ps}
    if code in P0_LIT:
        tl, Tl = P0_LIT[code]
        tal = const["alt_scale"] * abs(tl) * math.sqrt(r["T"] / Tl)
        pil = float(norm.sf(const["t_crit"] - tal))
        pl = const["q"] * pil + (1 - const["q"]) * const["alpha1"]
        out.update(t_alt_lit=tal, pi_lit=pil, p0_lit=pl, p0=min(ps, pl))
    return out


def qualification(p0doc, strict=False):
    """data/_r_p0.json → ({카드: 자격 기록}, m, 가족). 식(P0 ≥ 0.15 · T ≥ 84 · 밀도 · 외부 F0)과 문서의 eligible 이 다르면 멈춘다.
    자격의 P0 · T 관문은 문서의 p0_pass · T_pass(r_p0 가 반올림 전 값으로 낸 것)를 쓰고, 반올림 값과 경계(±1e-6) 밖에서 어긋나면 멈춘다.
    strict(실제 문서 · 굽기 · --check-reg) — result_sha 칸이 모두 있어야 하고, 상수가 카드 식과 같아야 하며, 카드마다 σ_plan · t_alt · π · P0 를
    다시 풀어 1e-6 안에서 같아야 한다. 표지 출처가 덮어쓰기 · 간이판이면 멈춘다."""
    if not p0doc:
        raise SystemExit("🚨 P0 문서(data/_r_p0.json)가 없다 — 등록 전에 r_p0.py run 으로 만들고 커밋한다.")
    F = RF["p0"]
    have_sha = all(k in p0doc for k in F["sha_keys"]) and p0doc.get(F["sha"])
    if strict and not have_sha:
        raise SystemExit("🚨 P0 문서에 result_sha 식 칸(%s) 또는 result_sha 가 없다 — r_p0.py run 이 쓴 판이 아니다." % (F["sha_keys"],))
    if have_sha:                                                # 실제 P0 문서 — 손으로 고친 판을 막는다(합성 문서는 식 칸이 없다)
        sha = hashlib.sha256(json.dumps({k: p0doc[k] for k in F["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if sha != p0doc.get(F["sha"]):
            raise SystemExit("🚨 P0 문서의 result_sha 가 내용과 다르다 — r_p0.py run 이 쓴 판이 아니다.")
    const = p0doc.get("constants") or {}
    if strict:
        want = {"q": P0_Q, "alpha1": P0_A1, "t_crit": P0_TCRIT, "alt_scale": P0_SCALE, "gate": P0_GATE, "T_min": T_MIN, "holm_alpha": ALPHA}
        bad = {k: (const.get(k), v) for k, v in want.items() if const.get(k) is None or abs(float(const[k]) - v) > 1e-12}
        fl = ((const.get("p0_floor") or {}).get("lit") or {})
        for code, (tl, Tl) in P0_LIT.items():                   # 🔒 P0 바닥의 문헌 입력(2026-09-26) — 러너 값과 같아야 한다
            got = fl.get(code) or {}
            if got.get("t_lit") != tl or got.get("T_lit") != Tl:
                bad["p0_floor:" + code] = (got, {"t_lit": tl, "T_lit": Tl})
        if bad:
            raise SystemExit("🚨 P0 문서 상수가 카드 식과 다르다: %s" % bad)
    cards = p0doc.get(F["cards"]) or {}
    out = {}
    for c in CANDIDATES:
        r = cards.get(CODES[c]) or {}
        p0, T = r.get(F["p0"]), r.get(F["T"])
        ext = r.get(F["external"]) or {}
        why = []
        if p0 is not None:
            pp = r.get("p0_pass")
            mine = bool(p0 >= P0_GATE)
            if pp is None:
                pp = mine
            elif bool(pp) != mine and abs(p0 - P0_GATE) > P0_TOL:
                raise SystemExit("🚨 P0 문서 %s p0_pass(%r) 가 p0 %.6f ≥ %.2f 와 다르다." % (c, pp, p0, P0_GATE))
            tp = r.get("T_pass")
            if tp is not None and bool(tp) != bool(T is not None and T >= T_MIN):
                raise SystemExit("🚨 P0 문서 %s T_pass(%r) 가 T %s ≥ %d 와 다르다." % (c, tp, T, T_MIN))
            if strict:
                src = r.get("count_src") or {}
                odd = {d: s for d, s in src.items() if not str(s).startswith("canonical")}
                if odd:
                    raise SystemExit("🚨 P0 문서 %s 개수 출처가 정본이 아니다(덮어쓰기 · 간이판) %s — 굽지 않는다." % (c, odd))
                d = p0_rederive(r, const, CODES[c])
                # 문서 값은 소수 6자리 — σ 반올림이 t_alt · π 로 번지는 몫을 감안해 t_alt · π 는 5e-6 · σ_plan · P0 는 1e-6
                tol = {"sigma_plan": P0_TOL, "t_alt": 5 * P0_TOL, "pi": 5 * P0_TOL, "p0": P0_TOL,
                       "p0_sigma": P0_TOL, "t_alt_lit": P0_TOL, "pi_lit": P0_TOL, "p0_lit": P0_TOL}
                diff = {k: (r.get(k), d[k]) for k in tol if r.get(k) is None or abs(float(r[k]) - d[k]) > tol[k]}
                if diff:
                    raise SystemExit("🚨 P0 문서 %s 의 식을 다시 풀면 다르다 %s(문서, 재유도)." % (c, diff))
        if p0 is None:
            why.append("P0 없음(%s)" % (r.get(F["status"]) or "자료 없음"))
        elif not pp:
            why.append("P0 %.4f < %.2f" % (p0, P0_GATE))
        if T is None or T < T_MIN:
            why.append("T %s < %d(커버리지 F0)" % (T, T_MIN))
        if r.get(F["density_pass"]) is not True:
            why.append("카드 밀도 F0 미달")
        bad = sorted(k for k, v in ext.items() if v is not True)
        if bad:
            why.append("카드 외부 F0 미달·미확인 %s" % bad)
        elig = not why
        if bool(r.get(F["eligible"])) != elig:
            raise SystemExit("🚨 P0 문서의 %s eligible(%r) 이 식(P0 ≥ 0.15 · T ≥ 84 · 밀도 · 외부 F0)과 다르다." % (c, r.get(F["eligible"])))
        out[c] = dict({k: r.get(k) for k in F["keep"]}, eligible=elig, reasons=why)
    H = p0doc.get(F["holm"]) or {}
    m, mem = H.get(F["m"]), H.get(F["members"])
    if m is None or mem is None:
        raise SystemExit("🚨 P0 문서의 m 이 미정(pending)이다 — 달 관문 · 카드 외부 F0 를 확정하고 다시 계산하라.")
    inv = {v: k for k, v in CODES.items()}
    fam = sorted(inv.get(x, x) for x in mem)
    if m != len(fam):
        raise SystemExit("🚨 P0 문서 m %s 가 가족 %s 의 크기와 다르다." % (m, fam))
    if fam != sorted(c for c in CANDIDATES if out[c]["eligible"]):
        raise SystemExit("🚨 P0 문서 가족 %s 가 자격 카드와 다르다." % fam)
    fams = [FAMILY[c] for c in fam]
    if len(set(fams)) != len(fams):
        raise SystemExit("🚨 같은 자료 가족에 1차가 둘이다(규칙 2).")
    return out, m, fam


def reg_consistency(reg, qual, m, fam, f0doc, counts=None):
    """등록 값(REG) = P0 문서 = F0 문서(= P0 개수 표의 경계 세계)인가. 하나라도 다르면 멈춘다(등록 뒤에 m · 가족이 움직이지 않게).
    reg 가 None 이면(--check-reg 에서 REG 가 아직 비었을 때) 문서끼리만 본다."""
    if reg is not None:
        if reg["m"] != m:
            raise SystemExit("🚨 REG m %r ≠ P0 문서 m %r." % (reg["m"], m))
        if sorted(reg["primary"] or []) != fam:
            raise SystemExit("🚨 REG 1차 %s ≠ P0 문서 가족 %s." % (reg["primary"], fam))
        for c in CANDIDATES:
            a, b = (reg["p0"] or {}).get(c), qual[c]["p0"]
            if (a is None) != (b is None) or (a is not None and abs(float(a) - float(b)) > 5e-7):
                raise SystemExit("🚨 REG P0[%s] %r ≠ P0 문서 %r." % (c, a, b))
    if f0doc is not None:
        docs_consistency(qual, m, fam, f0doc, counts)


def docs_consistency(qual, m, fam, f0doc, counts=None):
    """P0 문서 ↔ F0 문서 — 가족 안팎 모두(양방향 · 가족에서 잘못 빠진 카드도 잡는다).
    T: 자격 관문의 T 는 P0 카드 T(γ 가 설 수 있는 달 = F0 쓸 달 − P0 가 뺀 «정의 밖» · «주 표지 0» 달)다 — P0 카드 T 가
       F0 T − (그 뺀 달 가운데 F0 쓸 달) 과 같아야 하고, P0 가 달 관문 · 행 부족으로 뺀 달에 F0 쓸 달이 있으면 안 된다.
    밀도: P0 density_pass = F0 문서의 (R1: OS · RS | R2: CH) 밀도 F0 모두 참. 외부(R2): §C 파서 · 연간 짝 · 분리 실패 칸이 서로 같다.
    경계 세계: P0 개수 표(r_p0.member_world)의 첫 달 · 크기가 F0 문서(r_stagem.boundary_world)와 같다(R2 개수가 있을 때)."""
    f0 = f0doc["f0"]
    T0, fm = f0doc["T"], set(f0doc.get("months") or [])
    if T0 < T_MIN and m != 0:
        raise SystemExit("🚨 F0 문서 T %d < %d 인데 m = %d 이다." % (T0, T_MIN, m))
    for c in CANDIDATES:
        q = qual[c]
        if q["p0"] is None:
            continue                                        # P0 가 없는 카드 — 사유는 reasons(가족 밖)
        drop = q.get("dropped") or {}
        lost = sorted(set(x for k in ("gate", "window_no_rows") for x in (drop.get(k) or []) if x in fm))
        if lost:
            raise SystemExit("🚨 %s P0 가 F0 쓸 달 %s… 를 달 관문 · 행 부족으로 뺐다 — P0 의 달 관문이 F0 문서의 쓸 달이 아니다." % (c, lost[:3]))
        gone = set(x for k in ("undefined", "zero_focal") for x in (drop.get(k) or []) if x in fm)
        if q["T"] != T0 - len(gone):
            raise SystemExit("🚨 %s P0 T(%s) ≠ F0 T %d − P0 가 뺀 정의 밖 · 주 표지 0 달 %d." % (c, q["T"], T0, len(gone)))
        dens = all((f0["density"].get(f) or {}).get("ok") is True for f in P0_DENS[c])
        if bool(q["density_pass"]) != dens:
            raise SystemExit("🚨 %s 밀도 F0 가 P0 문서(%s)와 F0 문서(%s)에서 다르다(%s)." % (c, q["density_pass"], dens, "·".join(P0_DENS[c])))
        if c == "R2":
            ext, r2e = q.get("external_f0") or {}, f0["r2_external"]
            pair = {"parser_c_validation": r2e.get("parser_c"), "annual_pairs_ge_900": r2e.get("pairs_ok"), "split_fail_le_20pct": r2e.get("fail_ok")}
            if set(ext) != set(pair):
                raise SystemExit("🚨 R2 외부 F0 칸이 P0 문서(%s)와 러너(%s)에서 다르다." % (sorted(ext), sorted(pair)))
            diff = {k: (ext[k], pair[k]) for k in pair if ext[k] != pair[k]}
            if diff:
                raise SystemExit("🚨 R2 외부 F0 가 P0 문서와 F0 문서에서 다르다 %s(P0, F0)." % diff)
            if counts is not None:
                F = RF["p0_counts"]
                bw, rw = counts.get(F["bworld"]) or {}, f0.get("r2_world") or {}
                if bw.get(F["ok"]) is not True or (bw.get(F["first"]) or "9999") > BOUND_FROM:
                    raise SystemExit("🚨 P0 개수 표의 R2 경계 세계가 %s 부터다(필요 %s)." % (bw.get(F["first"]), BOUND_FROM))
                if bw.get(F["n"]) != rw.get("n") or bw.get(F["first"]) != rw.get("first"):
                    raise SystemExit("🚨 R2 경계 세계가 P0(r_p0.member_world n %s · %s)와 F0(r_stagem.boundary_world n %s · %s)에서 다르다 — "
                                     "σ_placebo 를 잰 CH 와 굽기의 CH 가 다른 경계로 선다. 등록 전에 한 벌로 맞춘다."
                                     % (bw.get(F["n"]), bw.get(F["first"]), rw.get("n"), rw.get("first")))
    for c in fam:
        if f0["density"][FOCAL[c]].get("ok") is not True:
            raise SystemExit("🚨 1차 %s 의 밀도 F0(%s) 가 등록 F0 문서에서 참이 아니다." % (c, FOCAL[c]))
    if "R2" in fam and f0["r2_external"].get("ok") is not True:
        raise SystemExit("🚨 1차 R2 의 외부 F0 가 등록 F0 문서에서 참이 아니다.")


def f0_selfcheck(f0doc, real=True):
    """F0 문서가 제 칸끼리 맞는가(손으로 고친 판을 잡는다 · 수익 없음) — 밀도 판정 = 달별 수의 규칙 · T = 쓸 달 수 · 달 sha ·
    커버리지 판정 = T ≥ 84 · R2 외부 판정 = 연도별 값의 규칙 · Stage S 판정 = 교체 수의 규칙 · §G 판정 · 경계 세계 규칙 · 방화벽 칸."""
    bad = []
    f0 = f0doc.get("f0") or {}
    ms = list(f0doc.get("months") or [])
    if f0doc.get("T") != len(ms) or f0doc.get("months_sha") != _sha_json(ms):
        bad.append("T · 달 sha 가 달 목록과 다르다")
    cov = f0.get("coverage") or {}
    if cov.get("T") != len(ms) or cov.get("ok") != (len(ms) >= T_MIN):
        bad.append("커버리지 판정이 T 와 다르다")
    for k, d in (f0.get("density") or {}).items():
        if k in F0_FLAG and "by_month" in d and d.get("ok") != f0_flag_ok(k, list(d["by_month"].values())):
            bad.append("밀도 %s 판정이 달별 수와 다르다" % k)
    e = f0.get("r2_external") or {}
    if "pairs_year" in e:
        again = f0_r2_external({"pairs_year": e["pairs_year"], "fail_rate": e["fail_rate"], "parser_c": e["parser_c"]})
        if again["ok"] != e.get("ok"):
            bad.append("R2 외부 판정이 연도별 값과 다르다")
    for c, s in (f0.get("stage_s") or {}).items():
        if "n_r" in s and f0_stage_s(s["n_r"]).get("ok") != s.get("ok"):
            bad.append("Stage S %s 판정이 교체 수와 다르다" % c)
    g = f0.get("g_concord") or {}
    if "row_match" in g and f0_g(g)["ok"] != g.get("ok"):
        bad.append("§G 판정이 값과 다르다")
    try:
        r2_world_check(f0.get("r2_world"))
    except SystemExit as ex:
        bad.append(str(ex))
    fw = f0doc.get("firewall") or {}
    if real and (fw.get("y_stripped") is not True or fw.get("returns_used") is not False):
        bad.append("방화벽 칸(y_stripped · returns_used)이 등록 판이 아니다")
    return bad


def reg_missing(reg):
    return [k for k, v in reg.items() if v is None]


# ══ 판정 ═══════════════════════════════════════════════════════════════════════════════════════
def verdicts(qual, family, holm, gates, f0):
    """카드 판정 · 단계 팔 — 표본 안 통과는 채택이 아니다(batch_design_changes 7)."""
    out = {}
    for c in CANDIDATES:
        why = []
        g = gates.get(c)
        if g is not None:
            for k, val in g["gates"].items():
                if type(val) is not bool:
                    raise SystemExit("🚨 %s 관문 %s 가 불리언이 아니다(%r) — 닫힌 실패." % (c, k, val))
        if c not in family:
            v = V_MEAS
            why = list(qual[c]["reasons"]) or ["등록 때 1차 자격 없음"]
        else:
            row = holm["rows"][c]
            if not row["pass"]:
                v = V_REJ
                why.append("Holm 미달 — p %.4f > α %.4f(순위 %d)" % (row["p"], row["alpha"], row["rank"])
                           if row["p"] > row["alpha"] else "Holm 미달 — 앞 순위가 떨어져 멈췄다")
            elif not g["all"]:
                bad = [k for k, ok in g["gates"].items() if not ok]
                v = "%s — 관문 %s 미달" % (V_REJ, "·".join(bad))
                why += [g["notes"][k] for k in bad if k in g.get("notes", {})]
            else:
                v = V_PASS
        ss = (f0.get("stage_s") or {}).get(c) or {}
        if v == V_PASS:
            if ss.get("ok") is True and not ss.get("provisional"):
                arm = ARM_ADOPT
            elif ss.get("ok") is False:
                arm = "%s(Stage S F0 미달 — 교체 수 중앙값 %s 가 %d~%d 밖 · 측정 불가)" % (ARM_MEAS, ss.get("median"), F0_S[0], F0_S[1])
            else:
                arm = "%s(Stage S F0 미확인 — 채택 경로를 열 수 없다)" % ARM_MEAS
        else:
            arm = ARM_MEAS
        cond = {"§G 일치 시험": f0["g_concord"].get("ok")} if c == "R1" else {"§C 파서 검증": f0["r2_external"].get("parser_c")}
        if arm == ARM_ADOPT and not all(x is True for x in cond.values()):
            arm += " — 조건 %s 를 통과하기 전에는 전방 팔을 열지 않는다" % "·".join(k for k, x in cond.items() if x is not True)
        rec = {"stage_m": v, "why": why, "stage_s_arm": arm, "arm_open_conditions": cond, "in_family": c in family}
        if c == "R2" and g is not None and g.get("contam"):
            rec["report"] = "분리 실패 오염 — 결측 더미 계수(%.4f) < γ_CH(%.4f) · 결과 문서에 적는다" % (g["vals"]["miss"], g["vals"]["ch"])
        out[c] = rec
    out["R3"] = {"stage_m": V_R3, "why": ["측정 전용 카드(조건부 승격을 없앴다 · 표본 안에서 한 번 재면 이 창은 R3 에 오염된다)"],
                 "stage_s_arm": "원장 밖(R3 는 원장에 넣지 않는다)", "in_family": False}
    out["R5"] = {"stage_m": V_R5, "why": ["사건이 드물어 표본 안 검정력이 0 — 사건 수와 업종 분포만"],
                 "stage_s_arm": "전방 기록 팔(V0 + 경보 제외 · 채택 경로 없음)", "in_family": False}
    return out


def headline(V, m):
    """결과 문서 머리 줄 — 풀카드 · 판정 · 규칙."""
    passed = [c for c in CANDIDATES if V[c]["stage_m"] == V_PASS]
    if passed:
        j = "Stage M 통과(%s) — 채택 아님 · 단계는 전방 판정" % "·".join(passed)
    elif m == 0:
        j = "측정만"
    else:
        j = "기각"
    return {"풀카드": "없음", "판정": j, "규칙": "없음"}


# ══ git · 핀 · 고정표 ═════════════════════════════════════════════════════════════════════════════
def _git(repo, *a):
    return subprocess.run(["git", "-C", repo] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree_blobs(repo, commit, paths):
    """commit 의 paths(파일 · 폴더) 아래 blob — {저장소 경로: sha1}."""
    r = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "-z", commit, "--"] + list(paths), capture_output=True)
    if r.returncode != 0:
        raise SystemExit("🚨 git ls-tree %s 실패: %s" % (commit, r.stderr.decode("utf-8", "replace")[:200]))
    out = {}
    for ent in r.stdout.decode("utf-8", "replace").split("\0"):
        if not ent:
            continue
        meta, path = ent.split("\t", 1)
        _, typ, sha = meta.split()
        if typ == "blob":
            out[path] = sha
    return out


def pin_check(repo, commit, paths, local):
    """paths 의 로컬 판(local(저장소 경로) → 디스크 경로)이 commit 의 blob 과 같은가(CRLF → LF 판도 받는다).
    폴더면 커밋에 없는 로컬 파일도 어긋남으로 센다. 돌려주는 것 [(경로, 사유)]."""
    want = tree_blobs(repo, commit, paths)
    bad = []
    for p in paths:
        pp = p.rstrip("/")
        sub = {f: s for f, s in want.items() if f == pp or f.startswith(pp + "/")}
        if not sub:
            bad.append((p, "커밋에 없다"))
            continue
        for f, s in sorted(sub.items()):
            lp = local(f)
            if not os.path.isfile(lp):
                bad.append((f, "로컬에 없다"))
                continue
            with open(lp, "rb") as fh:
                d = fh.read()
            if blob_sha1(d) != s and blob_sha1(d.replace(b"\r\n", b"\n")) != s:
                bad.append((f, "내용이 다르다"))
        lp0 = local(pp)
        if os.path.isdir(lp0):
            for dp, _, fs in os.walk(lp0):
                for fn in fs:
                    rel = pp + "/" + os.path.relpath(os.path.join(dp, fn), lp0).replace(os.sep, "/")
                    if rel not in sub:
                        bad.append((rel, "커밋에 없는 로컬 파일"))
    return bad


def first_add_is(repo, full, path):
    """path 를 처음 더한 커밋이 full 인가(qbatch_run 과 같은 규칙)."""
    added = _git(repo, "log", "--format=%H", "--diff-filter=A", full, "--", path).stdout.split()
    return bool(added) and added[-1] == full


def is_ancestor(repo, full, ref):
    return _git(repo, "merge-base", "--is-ancestor", full, ref).returncode == 0


def _local_repo_path(p, rdata=None):
    """저장소 경로 → 디스크 경로. data/<새 자료> 는 RBATCH_DATA, 나머지는 실행 뿌리."""
    rdata = rdata or RDATA
    if p.startswith("data/") and p[5:] in NEW_DATA:
        return os.path.join(rdata, _rel(p[5:]))
    return os.path.join(ROOT, _rel(p))


def manifest_shas(rdata=None):
    rdata = rdata or RDATA
    out = {}
    for rel in list(RF["manifests"]) + ["_issuer_map.json", "_r_p0.json", F0_NAME]:
        p = os.path.join(rdata, _rel(rel))
        out["data/" + rel] = _sha_lf(p) if os.path.exists(p) else None
    return out


def link_check(strict=False, rdata=None):
    """파생 파일이 적은 고정표 sha256 이 지금 파일과 같은가. 불일치는 늘 멈추고, strict(굽기)면 확인 못 한 링크도 멈춘다."""
    rdata = rdata or RDATA
    rows = []
    for src, keyp, tgt, status in RF["links"]:
        row = {"src": "data/" + src, "key": ".".join(keyp), "target": tgt, "status": status}
        J = _rj(os.path.join(rdata, _rel(src)))
        v = _dig(J, keyp) if J is not None else None
        tp = _local_repo_path(tgt, rdata)
        if J is None:
            row["result"] = "파일 없음"
        elif v is None:
            row["result"] = "필드 없음"
        elif not os.path.exists(tp):
            row["result"] = "대상 없음"
        else:
            with open(tp, "rb") as f:
                b = f.read()
            row["result"] = "일치" if v in (hashlib.sha256(b).hexdigest(), hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()) else "불일치"
        rows.append(row)
    bad = [r for r in rows if r["result"] == "불일치"]
    if bad:
        raise SystemExit("🚨 고정표 링크가 어긋났다: %s" % [(r["src"], r["key"]) for r in bad])
    if strict:
        und = [r for r in rows if r["result"] != "일치"]
        if und:
            raise SystemExit("🚨 고정표 링크를 확인하지 못했다: %s — RF['links'] 를 빌더 판에 맞춰라." % [(r["src"], r["key"], r["result"]) for r in und])
    return rows


def raw_check(raw, rdata=None):
    """RBATCH_RAW 가 있으면 고정표의 원본 sha256 을 다시 잰다(없는 원본은 센다 · 어긋나면 멈춘다)."""
    rdata = rdata or RDATA
    if not raw:
        return {"checked": False, "why": "RBATCH_RAW 없음 — 파생 파일의 blob 고정만 본다"}
    out = {"checked": True, "raw": raw}
    for mf, sp in RF["manifests"].items():
        J = _rj(os.path.join(rdata, _rel(mf)))
        if J is None:
            out[mf] = {"result": "고정표 없음"}
            continue
        n = miss = skip = 0
        bad = []
        for key, e in sorted((J.get(sp["root"]) or {}).items()):
            want = e.get(sp["sha"])
            if want is None:
                skip += 1                                    # 404 등 — 원본이 없다고 고정된 항목
                continue
            rel = e.get(sp["path"]) or (key + (sp["gz_default"] or ""))
            p = os.path.join(raw, _rel(rel))
            n += 1
            if not os.path.exists(p):
                miss += 1
                continue
            if _sha_file(p, gz=rel.endswith(".gz")) != want:
                bad.append(key)
        out[mf] = {"n": n, "missing": miss, "skipped": skip, "bad": bad[:20], "n_bad": len(bad)}
        if bad:
            raise SystemExit("🚨 원본이 고정표 해시와 다르다(%s): %s" % (mf, bad[:5]))
    return out


def pin_check_optional(repo, commit, paths, local):
    """선택 입력 핀 — 커밋과 로컬 모두에 없으면 «없음»(문제 아님) · 한쪽에만 있거나 내용이 다르면 어긋남. 돌려주는 것 ([(경로, 사유)], {경로: 상태})."""
    want = tree_blobs(repo, commit, paths)
    bad, state = [], {}
    for p in paths:
        lp = local(p)
        if p not in want and not os.path.exists(lp):
            state[p] = "없음(커밋 · 로컬)"
            continue
        if p not in want:
            bad.append((p, "로컬에만 있다(커밋에 없다)"))
            continue
        state[p] = "있음"
        bad += pin_check(repo, commit, [p], local)
    return bad, state


def forbidden_present(rdata=None):
    """굽기에서 있으면 안 되는 파일(덮어쓰기 표지) 가운데 있는 것."""
    rdata = rdata or RDATA
    return [p for p in FORBID_DATA if os.path.exists(os.path.join(rdata, _rel(p)))]


def frozen_check(reg=None):
    """굽기 전 점검 — 하나라도 어긋나면 돌지 않는다. 돌려주는 것 {commit, pins …}(JSON 에 싣는다)."""
    reg = REG if reg is None else reg
    nb = name_check()
    if nb:
        raise SystemExit("🚨 문서 이름: %s — 등록 날짜로 바꾸고 PREREG · PREREG_CARDS · RESULT 를 같은 커밋에서 고쳐라." % "; ".join(nb))
    miss = reg_missing(reg)
    if miss:
        raise SystemExit("🚨 등록 값이 비었다: %s — 등록 커밋에서 REG 를 채운다." % miss)
    if reg["stage_s"] in (None, "none"):
        raise SystemExit("🚨 실제 굽기는 Stage S 모듈(REG['stage_s'] = 'r_stages')이 있어야 한다 — 'none' 은 합성 · 연기 시험 전용"
                         "(카드의 Stage S 측정 C1~C5 · 위약 1000 · 쌓은 팔을 조용히 잃지 않는다).")
    fb = forbidden_present()
    if fb:
        raise SystemExit("🚨 덮어쓰기 표지 파일 %s 가 있다 — 정식 빌더를 가린다. 굽기 전에 치운다(r_stages · r_p0_adapt 옵트인)." % fb)
    unp = closure_unpinned(reg)
    if unp:
        raise SystemExit("🚨 굽기 경로가 가져오는 build/ 모듈 %s 가 얼린 목록에 없다 — CODE_FROZEN 또는 REG['frozen_extra'] 에 더한다." % unp)
    c = os.environ.get("RBATCH_COMMIT")
    if not c:
        raise SystemExit("🚨 RBATCH_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --dry · --f0 · --smoke-* 만 된다.")
    full = _git(REPO, "rev-parse", c + "^{commit}").stdout.strip()
    if not full:
        raise SystemExit("🚨 %s 를 커밋으로 풀 수 없다(%s)." % (c, REPO))
    for p in (PREREG, PREREG_CARDS):
        if not first_add_is(REPO, full, p):
            raise SystemExit("🚨 %s 는 %s 를 처음 더한 커밋이 아니다." % (full[:8], p))
    if not is_ancestor(REPO, full, "origin/main"):
        raise SystemExit("🚨 사전등록 커밋이 origin/main 에 없다 — 먼저 푸시.")
    doc = _git(REPO, "show", "%s:%s" % (full, PREREG)).stdout
    if PLACEHOLDER in doc:
        raise SystemExit("🚨 등록 커밋의 사전등록 문서에 %s⟩ 빈칸이 남았다." % PLACEHOLDER)
    out, mark = os.path.join(RDATA, OUT_NAME), os.path.join(RDATA, MARK_NAME)
    rerun = os.environ.get("RBATCH_RERUN") or os.environ.get("RBATCH_RESUME")
    if os.path.exists(out):
        raise SystemExit("🚨 산출물이 이미 있다 — 한 번 굽는 측정이다(다시 굽기는 새 등록).")
    for ref in ("origin/main:data/" + OUT_NAME, "origin/main:" + RESULT):
        if _git(REPO, "cat-file", "-e", ref).returncode == 0:
            raise SystemExit("🚨 %s 가 이미 커밋돼 있다 — 다시 굽기는 새 등록." % ref)
    if os.path.exists(mark) and not rerun:
        raise SystemExit("🚨 시작 표식이 있다 — 산출 전 중단이면 RBATCH_RESUME(검문점 이어하기) 또는 RBATCH_RERUN(처음부터)=사유.")
    if rerun and not os.path.exists(mark):
        raise SystemExit("🚨 재실행 · 이어하기는 시작 표식(산출 전 중단)이 있을 때만이다.")
    if rerun and not io.open(mark, encoding="utf-8").read().startswith(full):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    frozen = tuple(CODE_FROZEN) + tuple(P3_FROZEN) + tuple(reg["frozen_extra"])
    loc = lambda f: os.path.join(ROOT, _rel(f))
    dloc = lambda f: os.path.join(RDATA, _rel(f[5:]))
    for nm, com, paths, lf in (("얼린 파일", full, frozen, loc), ("P1 가격(%s)" % reg["snap"], reg["snap"], SNAP_FILES, loc),
                               ("P2 가격 밖(%s)" % reg["base"], reg["base"], BASE_FILES, loc),
                               ("새 자료", full, tuple("data/" + p for p in NEW_DATA), dloc)):
        bad = pin_check(REPO, com, paths, lf)
        if bad:
            raise SystemExit("🚨 %s 가 고정 판과 다르다: %s%s" % (nm, bad[:8], " …" if len(bad) > 8 else ""))
    bad, opt = pin_check_optional(REPO, full, tuple("data/" + p for p in NEW_DATA_OPT), dloc)
    if bad:
        raise SystemExit("🚨 선택 입력이 고정 판과 다르다: %s" % bad)
    links = link_check(strict=True)
    raw = raw_check(os.environ.get("RBATCH_RAW"))
    import scipy
    if scipy.__version__ != "1.18.1" or np.__version__ != "2.5.3":
        raise SystemExit("🚨 scipy/numpy 판이 다르다(%s · %s)." % (scipy.__version__, np.__version__))
    if os.environ.get("PYTHONHASHSEED") != "0" or os.environ.get("OPENBLAS_NUM_THREADS") != "1":
        raise SystemExit("🚨 PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 로 돌려라(부동소수 합 순서 · BLAS 스레드 고정).")
    return {"commit": full, "snap": reg["snap"], "base": reg["base"], "n_frozen": len(frozen), "links": links, "raw": raw,
            "manifests": manifest_shas(), "new_data_blobs": tree_blobs(REPO, full, ["data/" + p for p in NEW_DATA]), "optional": opt,
            "closure": import_closure(("r_run", reg["stage_s"]))}


# ══ 검문점 ═════════════════════════════════════════════════════════════════════════════════════
def ck_code(extra=()):
    """검문점 머리의 코드 지문 — 굽기 경로 가져오기 닫힘 전부(qbatch_run · refresh_events 포함)."""
    out = {}
    for p in import_closure(("r_run",) + tuple(x for x in extra if x and x != "none")):
        fp = os.path.join(ROOT, _rel(p))
        out[p] = _sha_lf(fp) if os.path.exists(fp) else None
    return out


def ck_header(commit, card, kind, digest, msha, fp, twins, stage_s=None):
    return {"commit": commit, "card": card, "kind": kind, "code": ck_code((stage_s,)),
            "panel": digest, "months": msha, "flags": fp_digest(fp), "twins": {k: fp_digest(v) for k, v in sorted((twins or {}).items())},
            "hashseed": os.environ.get("PYTHONHASHSEED"), "blas": os.environ.get("OPENBLAS_NUM_THREADS")}


def ck_run(ck_dir, card, hdr, fn, resume):
    """카드 결과 검문점 — 산출 전 기술적 중단에서만 이어 쓴다(머리가 다르면 멈춘다)."""
    f = os.path.join(ck_dir, card + ".pkl")
    if resume and os.path.exists(f):
        with open(f, "rb") as fh:
            blob = pickle.load(fh)
        if blob.get("hdr") != hdr:
            raise SystemExit("🚨 %s 검문점 머리가 지금과 다르다 — 다른 판 · 코드 · 환경에서 만든 검문점이다." % card)
        return blob["R"], True
    R = fn()
    with open(f + ".tmp", "wb") as fh:
        pickle.dump({"hdr": hdr, "R": R}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(f + ".tmp", f)
    return R, False


# ══ Stage M 계산(엔진 호출) ══════════════════════════════════════════════════════════════════════
def _r3_measure(S, P, fp, variants, months):
    """R3 측정 한 벌 — 엔진에 R3 카드 함수가 없어 러너가 fm 을 부르고, 시도 목록(trials)을 엔진 _Trials 와 같은 모양으로 적는다."""
    SP = S.SPECS["R3"]
    rows, out = [], {}

    def run(key, what, fp_, mm):
        if fp_ is None:
            rows.append({"id": "R3.%s" % key, "what": what, "run": False, "missing": ["§D 판 없음"]})
            return
        out[key] = S.fm(P, fp_, SP, mm)
        rows.append({"id": "R3.%s" % key, "what": what, "run": True})
    run("main", "FL JT k=0..2", fp, months)
    run("sens2020", "민감도 — 신호월 %s 부터" % SENS_2020, fp, [m for m in months if m >= SENS_2020])
    for nm in RF["twins_r3"]:
        run("tw_" + nm, "쌍둥이 %s(§D 판)" % nm, (variants or {}).get(nm), months)
    out["trials"] = rows
    return out


def stage_m(S, P, fps, variants, months, card, rs_f0_ok=None):
    """카드 한 장의 Stage M 한 벌 — 엔진(r_stagem) 카드 함수 그대로(주 · 관문 변형 · 측정 · 쌍둥이 · 민감도 · 시도 목록).
    R1 = stage_m_r1(쌍둥이 T1~T6 은 cikmonth 한 판의 칸 · T2 분할은 한 시도 안 · rs_f0_ok → 관문 i) ·
    R2 = stage_m_r2(fp_doc · fp_ixbrl · fp_covid = r2_variants) · R3 = _r3_measure."""
    if card == "R1":
        return S.stage_m_r1(P, fps["R1"], months, rs_f0_ok=rs_f0_ok)
    if card == "R2":
        kw = {RF["variants_r2"][k]: v for k, v in (variants or {}).items() if k in RF["variants_r2"]}
        return S.stage_m_r2(P, fps["R2"], months, **kw)
    if card == "R3":
        return _r3_measure(S, P, fps["R3"], variants, months)
    raise ValueError(card)


def required_inputs(S, fps, variants):
    """등록된 측정 입력 가운데 없는 것(Stage M 을 돌리기 전에 본다) — R1 쌍둥이 · 표본 칸 · R2 대조 판 · R3 §D 판."""
    miss = []
    if fps.get("R1") is not None:
        miss += ["R1:%s" % n for n in RF["need_r1"] if not S._has(fps["R1"], n)]
    miss += ["R2:%s" % k for k in RF["variants_r2"] if (variants.get("R2") or {}).get(k) is None]
    miss += ["R3:%s" % k for k in RF["twins_r3"] if (variants.get("R3") or {}).get(k) is None]
    return miss


def _g(res, name):
    return list(((res or {}).get("g") or {}).get(name) or [])


def rec_of(card, o):
    """엔진 결과 → 러너 판정 입력(γ 월 계열 · 그 달 목록) + 측정 요약(모든 fm 판 · 이름마다 primary_stat(달력 위치) · 보고만) + 시도 목록."""
    if "main" not in o:
        raise SystemExit("🚨 %s 주 회귀가 돌지 않았다 — 엔진 시도 목록 %s" % (card, [r for r in o.get("trials") or [] if not r.get("run")]))
    if card == "R1":
        rec = {"main": {"OS": _g(o["main"], "OS"), "RS": _g(o["main"], "RS")}, "extra": {"OS": _g(o.get("extra"), "OS")},
               "wls": {"OS": _g(o.get("wls"), "OS")}, "engine_gates": o.get("gates")}
    elif card == "R2":
        rec = {"main": {"CH": _g(o["main"], "CH"), "CH_miss": _g(o["main"], "CH_miss")}, "wls": {"CH": _g(o.get("wls"), "CH")},
               "len": {"CH": _g(o.get("len"), "CH")}, "engine_gates": o.get("gates")}
    else:
        rec = {"main": {"FL": _g(o["main"], "FL")}}
    rec["months"] = list(o["main"].get("months") or [])
    rec["engine_sum"] = ((o["main"].get("sum") or {}).get(FOCAL[card]))
    meas, series = {}, {}
    for key, res in sorted(o.items()):
        if isinstance(res, dict) and "g" in res:
            ms = res.get("months") or []
            meas[key] = {"stats": {nm: primary_stat(v, ms) for nm, v in res["g"].items()}, "n_months": len(ms),
                         "skip": len(res.get("skip") or {}), "drop": res.get("drop"), "variant": res.get("variant")}
            if res.get("split"):
                meas[key]["split"] = res["split"]            # T2 2023-04 전후(엔진 summarize · 한 시도 안의 보고)
            series[key] = {"months": ms, "g": res["g"]}
    rec["measures"] = meas
    rec["series"] = series
    rec["pooled"] = o.get("t5")
    rec["trials"] = [dict(r) for r in (o.get("trials") or [])]
    return rec


def r5_counts(P, fp5, top=STAGE_S_N, source=None):
    """R5 — 걸린 이름-월 수 · EG30(Eg 상위 30) 안 수 · 업종 분포 · 연도별(수익 없음 · 시도 수에 넣지 않는다)."""
    if fp5 is None:
        return {"ok": None, "why": "경보 표지 없음", "source": source}
    per, per_top, sec, yr = {}, {}, {}, {}
    for m in P["months"]:
        D = P["m"][m]
        hit = [j for j, g in enumerate(D["grp"]) if ((fp5.get((g, m)) or {}).get(FOCAL["R5"]) or 0) >= 1]
        tk = set((P["eg_rank"].get(m) or [])[:top])
        per[m] = len(hit)
        per_top[m] = sum(1 for j in hit if D["k"][j] in tk)
        for j in hit:
            sec[D["sec"][j]] = sec.get(D["sec"][j], 0) + 1
        y = yr.setdefault(m[:4], [0, 0])
        y[0] += per[m]
        y[1] += per_top[m]
    return {"ok": True, "name_months": int(sum(per.values())), "eg30_name_months": int(sum(per_top.values())),
            "by_year": {y: {"name_months": a, "eg30": b} for y, (a, b) in sorted(yr.items())},
            "sector": dict(sorted(sec.items(), key=lambda kv: -kv[1])), "source": source, "note": "수익 계산 없음 · 시도 수에 넣지 않는다"}


def stage_s_rows(stage_s):
    """Stage S 시도 목록 — 카드 controls 의 팔(S_ARMS)마다 돌았으면 run, 아니면 못 돌린 사유와 함께(R3 는 모듈에 팔이 없다 · 선언).
    stage_s = None 이면(모듈 없음 · 'none') 모든 팔이 못 돌린 시도로 실린다."""
    rows = []
    for code, arms in S_ARMS.items():
        s = (stage_s or {}).get(code) if stage_s is not None else None
        have = list((s or {}).get("arms") or [])
        if stage_s is None:
            why = "Stage S 모듈 없음(REG stage_s = none · 합성 · 연기 시험)"
        elif code == "R3-8KNE" or s is None:
            why = "Stage S 모듈에 %s 팔이 없다 — 결과 문서에 «등록 오류(미구현 측정)» 로 적는다" % code
        else:
            why = s.get("skipped") or ((s.get("f0") or {}).get("why")) or "측정 안 됨"
        for a in arms:
            rid = "%s.S.%s" % (code, a)
            rows.append({"id": rid, "what": "Stage S %s" % a, "run": True} if a in have else
                        {"id": rid, "what": "Stage S %s" % a, "run": False, "missing": [str(why)]})
        rows += [{"id": "%s.S.%s" % (code, a), "what": "Stage S %s(등록 목록 밖)" % a, "run": True} for a in have if a not in arms]
    return rows


def trials(recs, s_rows, n_prior):
    """이 배치의 시도 수 — 엔진 · 러너 시도 목록(run = True 인 줄 · 주 · 관문 변형 · 측정 · 쌍둥이 · 민감도 · 합동 회귀) + Stage S 팔.
    못 돌린 시도(run = False)는 사유와 함께 따로 싣는다. R5 는 넣지 않는다."""
    rows = [r for c in sorted(recs) for r in recs[c]["trials"]] + list(s_rows or [])
    run = [r["id"] for r in rows if r.get("run")]
    return {"batch": len(run), "names": run, "not_run": [r for r in rows if not r.get("run")], "lab_prior": n_prior,
            "cumulative": (n_prior + len(run)) if n_prior is not None else None}


def stage_s_hash_check(stage_s, f0):
    """굽기의 Stage S 목표 해시 = 등록 F0 문서에 얼린 해시(forward_plan «규칙과 해시를 등록 커밋에서 얼린다»). 다르면 멈춘다."""
    H = f0.get("stage_s_hashes") or {}
    for code, h in sorted(H.items()):
        if code.startswith("_") or h is None:
            continue
        got = ((stage_s or {}).get(code) or {}).get("targets_hash")
        if got != h:
            raise SystemExit("🚨 Stage S %s 목표 해시 %s 가 등록 F0 문서 %s 와 다르다." % (code, (got or "없음")[:16], h[:16]))
    v0 = H.get("_v0")
    got = ((stage_s or {}).get("_meta") or {}).get("v0_hash")
    if v0 is not None and got != v0:
        raise SystemExit("🚨 Stage S V0 해시가 등록 F0 문서와 다르다.")


def px_overlay_of(prov):
    """선언된 내부 가격 오버레이(r_stagem.load_world · RBATCH_PX_OVERLAY)의 적용 요약 — sha256 · 수(경로 · 값 없음) · None = 공개 판."""
    return getattr(getattr(prov, "Wd", None), "px_overlay", None)


def overlay_out_guard(path):
    """내부 가격 오버레이 판(RBATCH_PX_OVERLAY)의 산출물은 실행 뿌리(저장소 작업 사본) 밖에만 쓴다 — 내부 종가에서 나온 수다.
    공개 판(변수 없음)은 그대로다. 오버레이 판은 RBATCH_DATA(와 --out)를 저장소 밖 사본으로 준다."""
    if not _S().px_overlay_path():
        return
    try:
        inside = os.path.commonpath([os.path.abspath(path).lower(), ROOT.lower()]) == ROOT.lower()
    except ValueError:                                     # 다른 드라이브 — 밖
        inside = False
    if inside:
        raise SystemExit("🚨 RBATCH_PX_OVERLAY 가 있다 — 산출물 %s 가 저장소 안이다. RBATCH_DATA · --out 을 저장소 밖으로 준다." % path)


def f0_doc(prov):
    """F0 문서(등록 전 커밋 · 수익 없음) — 굽기가 같은 판으로 다시 세어 같아야 한다."""
    S = _S()
    P = prov.P
    cov = S.f0_coverage(P)
    months = cov["months"]
    fps = {c: prov.flags(c) for c in ("R1", "R2", "R3", "R5")}
    f0 = f0_all(S, prov, P, fps, months)
    return _roundtrip({"kind": "r_run.f0", "version": 2, "provider": prov.kind,
                       "note": "배치 R F0(수익 없음) — 커버리지 · 밀도 · R2 외부 · R2 경계 세계 · Stage S(교체 수 · 목표 해시) · §G · 지도. "
                               "패널의 y 는 짓자마자 지웠다.",
                       "window": [M0, M1], "T": len(months), "months": months, "months_sha": _sha_json(list(months)),
                       "panel_digest": S.panel_digest(P), "coverage_by_month": cov["by_month"], "f0": f0,
                       "px_overlay": px_overlay_of(prov),          # 선언된 내부 가격 오버레이 sha256 · 수(None = 공개 판)
                       "flags_sha": {c: fp_digest(fps[c]) for c in sorted(fps)}, "r5": r5_counts(P, fps["R5"], source=prov.r5_source()),
                       "stage_s_rule": prov.stage_s_rule(), "sanity": prov.sanity() if hasattr(prov, "sanity") else None,
                       "firewall": {"y_stripped": bool(getattr(prov, "y_stripped", False)), "returns_used": False}})


# ══ 굽기 한 벌(공급자와 무관) ═══════════════════════════════════════════════════════════════════════
def bake_core(prov, reg, p0doc, f0doc, commit, started, ck_dir, resume=False, out_path=None, meta=None, counts=None):
    """등록 값 대조 → 세계 · 커버리지 · F0 재현 → 입력 점검 → 카드별 Stage M(검문점) → 주 통계 · 엔진 대조 → Holm → 관문 → 판정
    → Stage S(검문점 · 목표 해시 대조) → JSON."""
    t0 = time.time()
    S = _S()
    real = prov.kind == "real"
    qual, m, fam = qualification(p0doc, strict=real)
    if f0doc is None:
        raise SystemExit("🚨 F0 문서(data/_r_f0.json)가 없다 — 등록 전에 --f0 로 만들고 커밋한다.")
    reg_consistency(reg, qual, m, fam, f0doc, counts)
    if real:
        bad = f0_selfcheck(f0doc, real=True)
        if bad:
            raise SystemExit("🚨 F0 문서가 제 칸끼리 맞지 않는다: %s" % bad)
    P = prov.P
    cov = S.f0_coverage(P)
    months = cov["months"]
    msha = _sha_json(list(months))
    digest = S.panel_digest(P)
    if f0doc.get("months_sha") != msha or f0doc.get("T") != len(months):
        raise SystemExit("🚨 쓸 달이 등록 F0 문서와 다르다(T %s ≠ %s)." % (len(months), f0doc.get("T")))
    if f0doc.get("panel_digest") != digest:
        raise SystemExit("🚨 통제 패널 지문이 등록 F0 문서와 다르다.")
    ovr = px_overlay_of(prov)
    if (f0doc.get("px_overlay") or {}).get("sha256") != (ovr or {}).get("sha256"):
        raise SystemExit("🚨 가격 오버레이(RBATCH_PX_OVERLAY)가 등록 F0 문서와 다르다 — 같은 파일(sha256)로 굽거나 둘 다 없이(공개 판).")
    san = _roundtrip(prov.sanity()) if hasattr(prov, "sanity") else None
    if san is not None and not san["shares_ok"]:
        raise SystemExit("🚨 시총 핀(AUDIT-2026-09-20-SHARES2)이 맞지 않는다: %s" % san["shares_pin"])
    fps = {c: prov.flags(c) for c in ("R1", "R2", "R3", "R5")}
    for c in ("R1", "R2", "R3"):
        if fps[c] is None:
            raise SystemExit("🚨 %s 표지가 없다 — 등록된 입력이 빠졌다." % c)
    fsha = {c: fp_digest(fps[c]) for c in sorted(fps)}
    if fsha != f0doc.get("flags_sha"):
        raise SystemExit("🚨 표지 지문이 등록 F0 문서와 다르다: %s" % [c for c in fsha if fsha[c] != (f0doc.get("flags_sha") or {}).get(c)])
    f0 = _roundtrip(f0_all(S, prov, P, fps, months))
    if _canon(f0) != _canon(f0doc["f0"]):
        raise SystemExit("🚨 F0 가 등록 판과 다르다(같은 판 · 같은 코드면 바이트까지 같아야 한다).")
    variants = {c: prov.variants(c) for c in ("R1", "R2", "R3")}
    miss_in = required_inputs(S, fps, variants)
    if miss_in and real:
        raise SystemExit("🚨 등록된 측정(쌍둥이 · 대조) 입력이 없다: %s — Stage M 을 돌리기 전에 멈춘다(등록 오류)." % miss_in)
    variants = {c: {k: v for k, v in tw.items() if v is not None} for c, tw in variants.items()}
    rs_ok = f0["density"]["RS"].get("ok")
    os.makedirs(ck_dir, exist_ok=True)
    recs, ck_log = {}, {}
    for c in ("R1", "R2", "R3"):
        t1 = time.time()
        hdr = dict(ck_header(commit, c, prov.kind, digest, msha, fps[c], variants[c], reg.get("stage_s")),
                   rs_f0_ok=rs_ok if c == "R1" else None)
        o, resumed = ck_run(ck_dir, c, hdr, lambda c=c: stage_m(S, P, fps, variants[c], months, c, rs_f0_ok=rs_ok), resume)
        recs[c] = rec_of(c, o)
        ck_log[c] = {"resumed": resumed, "sec": round(time.time() - t1, 1)}
        print("  %s Stage M %s(%.0f초)" % (c, "검문점에서 이어받음 " if resumed else "", time.time() - t1), flush=True)
    undeclared = [r for c in recs for r in recs[c]["trials"] if not r.get("run") and r["id"] not in DECLARED_NOT_RUN]
    if undeclared and real:
        raise SystemExit("🚨 선언하지 않은 못 돌린 시도가 있다: %s(등록 오류)." % [(r["id"], r.get("missing")) for r in undeclared])
    stats = {c: primary_stat(recs[c]["main"][FOCAL[c]], recs[c]["months"]) for c in recs}
    gates = {"R1": gates_r1(recs["R1"], rs_ok), "R2": gates_r2(recs["R2"])}
    for c in recs:
        engine_check(c, recs[c], stats[c], gates.get(c))
    holm = holm_fixed({c: stats[c] for c in fam}, m, fam)
    f0v = _roundtrip(f0)                                   # 판정용 사본 — 등록 값에 Stage S 규칙이 없으면(연기 시험) 교체 수는 잠정이다
    for c in CANDIDATES:
        f0v["stage_s"][c]["provisional"] = reg.get("stage_s") is None
    V = verdicts(qual, fam, holm, gates, f0v)
    stage_s = None
    if hasattr(prov, "stage_s_all") and (reg.get("stage_s") not in (None, "none")):
        hdr = dict(ck_header(commit, "S", prov.kind, digest, msha, fps["R1"], {"R2": fps["R2"], "R5": fps["R5"]}, reg.get("stage_s")),
                   module=reg["stage_s"], hashes=f0.get("stage_s_hashes"))
        stage_s, resumed = ck_run(ck_dir, "S", hdr, prov.stage_s_all, resume)
        ck_log["S"] = {"resumed": resumed}
        if stage_s is not None:
            stage_s_hash_check(stage_s, f0)
    s_rows = stage_s_rows(stage_s)
    r5 = r5_counts(P, fps["R5"], source=prov.r5_source())
    import scipy
    doc = {"kind": "rbatch", "prereg": PREREG, "prereg_commit": commit, "started": started, "provider": prov.kind,
           "rerun": os.environ.get("RBATCH_RERUN"), "resume": os.environ.get("RBATCH_RESUME"),
           "versions": {"numpy": np.__version__, "scipy": scipy.__version__, "python": sys.version.split()[0]},
           "env": {"PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"), "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS")},
           "pins": (meta or {}).get("pins"), "reg": reg, "p0": qual, "holm_m": m, "family": fam,
           "p0_doc_sha": (p0doc or {}).get(RF["p0"]["sha"]), "f0": f0, "sanity": san, "px_overlay": ovr,
           "panel": {"digest": digest, "months_sha": msha, "T": len(months), "first": months[0] if months else None,
                     "last": months[-1] if months else None, "coverage_fail": cov["fail"]},
           "inputs_missing": miss_in,
           "stage_m": {c: {"primary": stats[c], "gates": gates.get(c), "measures": recs[c]["measures"], "pooled": recs[c]["pooled"],
                           "series": recs[c]["series"], "trials": recs[c]["trials"]} for c in recs},
           "holm": holm, "verdicts": V, "headline": headline(V, m), "r5": r5, "stage_s": stage_s,
           "trials": trials(recs, s_rows, reg.get("n_lab_prior")), "checkpoint": ck_log,
           "notes": {"df": "한쪽 p = P(t(T−1) ≤ t) · T = γ 가 선 달 수(T = 120 이면 t(119))",
                     "nw": "NW(3) t 는 달력 위치를 지킨다 — 쓴 달이 이어지면 eg30plus.nw_t · 빈 달이 끼면 r_stagem.nw_t_gap(압축 계열 값 nw_t_compressed 를 함께)",
                     "declared_not_run": DECLARED_NOT_RUN,
                     "stage_arms": "R1 · R2 단계 팔은 Stage M 결과와 무관하게 등록 커밋에서 얼려 원장에 든다(forward_plan) — 여기 판정은 채택 경로만 정한다",
                     "in_sample": "표본 안 통과는 채택이 아니다 · 떨어진 규칙을 고쳐 다시 굽지 않는다"},
           "elapsed": round(time.time() - t0, 1)}
    if out_path:
        tmp = out_path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":"), default=_js) + "\n")
        os.replace(tmp, out_path)
    return doc


def print_table(doc):
    print("\n카드 | 1차 | P0 | T | γ 평균 | NW t | p(한쪽) | Holm α | 관문 | 판정 | 단계 팔")
    for c in ("R1", "R2", "R3"):
        s = doc["stage_m"][c]["primary"]
        q = doc["p0"].get(c) or {}
        h = (doc["holm"]["rows"] or {}).get(c)
        g = doc["stage_m"][c].get("gates")
        gs = "·".join("%s%s" % (k, "✓" if v else "✗") for k, v in g["gates"].items()) if g else "—"
        print("%s | %s | %s | %d | %s | %s | %.4f | %s | %s | %s | %s" % (
            c, "예" if c in doc["family"] else "아니오", ("%.3f" % q["p0"]) if q.get("p0") is not None else "—", s["T"],
            "%+.4f" % s["mean"] if s["mean"] is not None else "—", "%.2f" % s["nw_t"] if s["nw_t"] is not None else "—", s["p_one"],
            "%.4f" % h["alpha"] if h else "—", gs, doc["verdicts"][c]["stage_m"], doc["verdicts"][c]["stage_s_arm"]))
    print("R5 | 사건 수만 | 이름-월 %s · EG30 안 %s" % (doc["r5"].get("name_months"), doc["r5"].get("eg30_name_months")))
    hl = doc["headline"]
    print("머리 줄: 풀카드: %s · 판정: %s · 규칙: %s · 시도 %d(누적 %s) · %.0f초" % (
        hl["풀카드"], hl["판정"], hl["규칙"], doc["trials"]["batch"], doc["trials"]["cumulative"], doc["elapsed"]))


# ══ 공급자 — 실제(PIT 세계 · snap_wt) ═════════════════════════════════════════════════════════════
def _ev_pairs(card, variant="primary", rdata=None):
    """§D 사건 표지 → [(그룹, 달)] 또는 None."""
    F = RF["ev"]
    J = _rj(os.path.join(rdata or RDATA, _rel(F["file"])))
    if J is None:
        return None
    X = _pick(J, F[card])
    if X is None:
        return None
    if isinstance(X, dict):
        X = _pick(X, F["primary"]) if variant == "primary" else X.get(variant)
        if X is None:
            return None
    return [(str(g), m) for g, m in X]


def stage_s_summary(C):
    """r_stages CardResult → 싣는 모양(f0 · 목표 해시 · measured · 월 초과 계열(TR 10bp · TR 20bp · PR) · 시도 수로 셀 팔 이름).
    20bp 행(fr20 · V0_20)과 PR 행(fr_pr)은 카드 «편도 10bp · 20bp 행을 함께 기록한다» 의 기록이다(팔 수에는 넣지 않는다)."""
    if C is None:
        return None
    lg = C.get("log") or {}
    out = {"code": C.get("code"), "cls": C.get("cls"), "f0": C.get("f0"), "targets_hash": C.get("targets_hash"),
           "measured": lg.get("measured"), "skipped": lg.get("skipped_returns"), "arms": []}
    fr = C.get("fr")
    if fr is not None:
        ctl = C.get("controls") or {}
        out["series"] = {"hold": fr.get("hold"), "rule": [float(v) for v in fr["ex"]]}
        for nm, key in (("fr20", "rule_20bp"), ("fr_pr", "rule_pr")):
            x = C.get(nm)
            if x is not None and x.get("ex") is not None:
                out["series"][key] = [float(v) for v in x["ex"]]
        for k, v in ctl.items():
            if isinstance(v, dict) and v.get("ex") is not None:
                out["series"][k] = [float(x) for x in v["ex"]]
        out["arms"] = ["rule"] + sorted(k for k in ctl if k not in ("V0", "V0_20")) + (["placebo"] if C.get("placebo") else [])
    if C.get("cls") == "count":
        out["counts"] = lg.get("counts")
    return out


class StageSAdapter:
    """REG["stage_s"] 모듈(build/r_stages.py) 연결 — 교체 수 · 목표 해시(F0)는 build(수익 없음), 측정 팔은 run(등록 뒤 · 검문점).
    이름은 RF["stage_s"]. 묶음은 Stage M 과 같은 R2 경계 세계(boundary_world)로 짓고 덮어쓰기 표지는 쓰지 않는다(옵트인 안 함).
    Stage M 표지와 묶음 표지가 같은 칸에서 켜졌는지(OS · CH) 대조하고, R5 이름-월도 이 묶음의 ALARM 하나에서 센다."""

    def __init__(self, prov, modname):
        self.M, self.prov = importlib.import_module(modname), prov
        self.F = RF["stage_s"]
        self._bundle = self._B = None

    def _view(self, im):
        return getattr(self.M, self.F["view"])(self.prov.Wd, im)

    def bundle(self):
        if self._bundle is None:
            B = getattr(self.M, self.F["load_bundle"])(self._view(None), r2_world=self.prov.bworld())
            if (((B.get("src") or {}) if isinstance(B, dict) else {}).get("override") or {}).get("used"):
                raise SystemExit("🚨 Stage S 묶음이 덮어쓰기 표지를 썼다 — 굽기는 정본만.")
            self._bundle = B
        return self._bundle

    def built(self):
        if self._B is None:
            b = self.bundle()
            self._B = getattr(self.M, self.F["build"])(self._view(b["im"]), b)
        return self._B

    def card(self, c):
        return (self.built().get(self.F["cards"]) or {}).get(self.F["codes"][c])

    def n_r(self, c):
        """잴 수 있는 편입(모듈이 뺀 편입 excluded 밖)의 교체 수 — 모듈 F0 와 같은 모집단."""
        C = self.card(c)
        if C is None:
            return None
        f0 = C.get(self.F["f0"]) or {}
        d, ex = f0.get(self.F["n_r"]) or {}, f0.get(self.F["excluded"]) or {}
        return [int(d[r]) for r in sorted(d) if r not in ex]

    def f0_card(self, c, fp=None):
        C = self.card(c)
        if C is None:
            return None
        f0 = C.get(self.F["f0"]) or {}
        ex = f0.get(self.F["excluded"]) or {}
        out = {"ok": f0.get(self.F["ok"]), "module_ok": f0.get(self.F["ok"]), "excluded": {r: list(w) for r, w in sorted(ex.items())},
               "targets_hash": C.get(self.F["hash"])}
        if fp is not None:
            out["flag_agree"] = self.flag_agree(c, fp)
        return out

    def flag_agree(self, c, fp):
        """Stage M 표지(OS · CH = 1 인 (그룹, 달))와 Stage S 묶음(on)이 같은가 — 다르면 멈춘다(두 단계가 다른 표지로 돌지 않게)."""
        nm_m, nm_s = self.F["agree"][c]
        fs = self.bundle().get(nm_s)
        if fs is None:
            return None
        a = {(str(g), m) for (g, m), rec in fp.items() if (rec or {}).get(nm_m) == 1}
        b = {(str(g), m) for m, gs in fs.on.items() for g in gs}
        out = {"stage_m": len(a), "stage_s": len(b), "only_m": len(a - b), "only_s": len(b - a)}
        if a != b:
            raise SystemExit("🚨 %s 표지 %s 가 Stage M(%d)과 Stage S 묶음(%d)에서 다르다 — 한쪽에만 %d · %d(예 %s)."
                             % (c, nm_m, len(a), len(b), len(a - b), len(b - a), sorted(a ^ b)[:3]))
        return out

    def hashes(self):
        B = self.built()
        out = {code: (C or {}).get(self.F["hash"]) for code, C in sorted((B.get(self.F["cards"]) or {}).items())}
        out["_v0"] = B.get(self.F["v0_hash"])
        return out

    def alarm_pairs(self):
        fs = self.bundle().get(self.F["alarm"])
        if fs is None:
            return None
        return sorted((str(g), m) for m, gs in fs.on.items() for g in gs)

    def summarize(self, R):
        codes = list(self.F["codes"].values()) + list(self.F["extra"])
        return {k: stage_s_summary(R.get(k)) for k in codes} | {"_meta": R.get("_meta")}

    def run_all(self, bundle=None, nperm=None, ctx=None):
        import qbatch_core as QC
        if ctx is None:
            ctx = QC.Ctx()
            ctx._Wd = self.prov.Wd                          # 세계를 두 번 짓지 않는다(같은 eg30plus.World)
        kw = {} if nperm is None else {"nperm": nperm}
        return self.summarize(getattr(self.M, self.F["run"])(ctx, bundle if bundle is not None else self.bundle(), **kw))

    def smoke(self, nperm=2, seed=11):
        """눈가린 연기 시험 — 실제 세계 · 실제 지도 위 **합성 표지**(r_stages.synth_bundle)로 run → 요약까지(qbatch_core.blind_smoke ·
        값은 버리고 예외 · 모양 · 초만). 실제 표지 × 실제 가격은 계산하지 않는다(r_stages --construct 의 연기 시험과 같은 규약)."""
        import qbatch_core as QC
        M, F = self.M, self.F
        im = getattr(M, F["issuer_map"]).load()
        ms = list(getattr(self._view(im), F["months"]))
        B = getattr(M, F["synth_bundle"])(im, months_between(mshift(ms[0], -3), ms[-1]), seed=seed)
        return QC.blind_smoke(lambda: self.run_all(bundle=B, nperm=nperm))


class RealProvider:
    """시점정확 세계(eg30plus.World · r_stagem.build_panel) + 새 자료. strip_y → y 를 NaN 으로(--f0) · blind_seed → y 를 잡음으로(연기 시험).
    R2 경계 세계 = r_stagem.boundary_world(2015-01 부터 · 가격 무관) 한 벌 — 표지 · 대조 · 외부 F0 · Stage S 묶음이 모두 이것을 쓴다."""
    kind = "real"

    def __init__(self, reg=None, strip_y=False, blind_seed=None):
        S = _S()
        self.reg = reg or REG
        self.Wd = S.load_world()
        self.IM = S.IssuerMap()
        self.P = S.build_panel(self.Wd, self.IM, months_between(S.M0, S.M1))
        self.y_stripped = False
        if strip_y or blind_seed is not None:
            rng = np.random.default_rng(blind_seed if blind_seed is not None else 0)
            for mm in self.P["months"]:
                D = self.P["m"][mm]
                n = len(D["y"])
                D["y"] = rng.normal(0.0, 8.0, n) if blind_seed is not None else np.full(n, np.nan)
            self.y_stripped = True
            if blind_seed is not None:
                self.P["kind"] = self.kind = "blind"
        self._bw = self._bw_st = self._r2v = self._R2 = self._ss = None
        self._rowmap = {}

    def bworld(self):
        if self._bw is None:
            self._bw, self._bw_st = _S().boundary_world(self.Wd, self.IM, BOUND_FROM, M1)
        return self._bw

    def r2_world_info(self):
        return world_info(self.bworld(), self._bw_st)

    def _have(self, key):
        return os.path.exists(os.path.join(RDATA, _rel(_S().FIELDS[key]["file"])))

    def _r2(self):
        if self._r2v is None:
            if not self._have("tenq"):
                return None
            self._r2v, self._R2 = r2_flag_set(self.bworld())
        return self._r2v

    def r5_source(self):
        return "Stage S 묶음 ALARM(r_r2flags.r5_events · %s)" % self.reg.get("stage_s") if self._ssmod() is not None else "§D %s" % RF["ev"]["file"]

    def flags(self, c):
        """카드 표지 — 자료가 아직 없으면 None(--f0 은 «표지 없음» 으로 싣고, 굽기는 멈춘다)."""
        S = _S()
        if c == "R1":
            return S.ins_flags() if self._have("ins") else None
        if c == "R2":
            v = self._r2()
            return None if v is None else v["rf"]
        if c == "R5" and self._ssmod() is not None:           # R5 는 한 원천 — Stage S 묶음의 ALARM(정본 r5_events)
            pairs = self._ssmod().alarm_pairs()
            return None if pairs is None else S.flags_from_pairs(pairs, FOCAL["R5"])
        pairs = _ev_pairs(c)
        return None if pairs is None else S.flags_from_pairs(pairs, FOCAL[c])

    def variants(self, c):
        """대조 판 — R1 은 없다(쌍둥이는 cikmonth 칸 · 엔진) · R2 = r2_variants 의 doc · ixbrl · covid · R3 = §D 판."""
        if c == "R1":
            return {}
        if c == "R2":
            v = self._r2() or {}
            return {k: v.get(k) for k in RF["variants_r2"]}
        out = {}
        for nm in RF["twins_r3"]:
            pairs = _ev_pairs("R3", nm)
            out[nm] = None if pairs is None else _S().flags_from_pairs(pairs, FOCAL["R3"])
        return out

    def r2_external(self):
        if self._r2() is None:
            return None
        import r_r2flags as R2
        F = RF["r2_density"]
        by = (R2.r2_density(self._R2) or {}).get(F["by_year"]) or {}
        J = _rj(os.path.join(RDATA, _rel(RF["parser_c"]["file"])))
        pc = _pick(J, RF["parser_c"]["pass"]) if J is not None else None
        return {"pairs_year": {y: r.get(F["pairs"]) for y, r in by.items()}, "fail_rate": {y: r.get(F["fail"]) for y, r in by.items()},
                "parser_c": (bool(pc) if pc is not None else None)}

    def g_concord(self):
        F = RF["g_check"]
        J = _rj(os.path.join(RDATA, _rel(F["file"])))
        return None if J is None else {"row_match": _pick(J, F["row_match"]), "os_mismatch": _pick(J, F["os_mismatch"])}

    def group_of(self, k, r):
        if r not in self._rowmap:
            D = self.P["m"].get(r)
            self._rowmap[r] = dict(zip(D["k"], D["grp"])) if D is not None else {}
        g = self._rowmap[r].get(k)
        if g is None:
            a = self.IM.at(k, r)
            g = a["grp"] if a else None
        return g

    def sanity(self):
        """구조 점검(수익 없음) — 시총 핀(AUDIT-2026-09-20-SHARES2 분할 되맞춤 판 · r_stagem.SHARES_PIN) · V0 명단 = Eg 순위 앞 30(보고)."""
        S, E = _S(), _E()
        pin = {}
        for (t, mm), (lo, hi) in S.SHARES_PIN.items():
            v = self.Wd.mcap(t, t, self.Wd.me[mm])
            pin["%s@%s" % (t, mm)] = {"mcap": v, "ok": bool(v and lo <= v <= hi)}
        T0 = E.v0_targets(self.Wd)
        mis = [mm for mm in T0 if mm in self.P["eg_rank"] and set(self.P["eg_rank"][mm][:30]) != set(T0[mm]["w"])]
        return {"shares_pin": pin, "shares_ok": all(v["ok"] for v in pin.values()), "v0_mismatch": mis, "v0_forms": len(T0)}

    def stage_s_rule(self):
        mod = self.reg.get("stage_s")
        return {"module": mod, "provisional": mod is None,
                "rule": "편입 r 의 Eg 상위 30 가운데 표지 활성(R1 가용월 r−2..r OS · R2 CH_active) 그룹 수 — 모듈이면 잴 수 있는 편입만"
                        "(모듈 excluded 밖) · 러너 기본 셈이면 그룹을 못 풀 때 unmapped"}

    def _ssmod(self):
        mod = self.reg.get("stage_s")
        if not mod or mod == "none":
            return None
        if self._ss is None:
            self._ss = StageSAdapter(self, mod)
        return self._ss

    def stage_s_nr(self, c, fp, flag, win):
        if fp is None:
            return None, 0
        ad = self._ssmod()
        if ad is not None:
            return ad.n_r(c), 0
        forms = [r for r in quarterly_forms() if r in self.P["eg_rank"]]
        return count_nr(self.P, fp, flag, win, forms, self.group_of)

    def stage_s_card(self, c, fp):
        ad = self._ssmod()
        return None if (ad is None or fp is None) else ad.f0_card(c, fp)

    def stage_s_hashes(self):
        ad = self._ssmod()
        return None if ad is None else ad.hashes()

    def stage_s_all(self):
        """Stage S 측정 팔 전부(등록 뒤 한 번) — 모듈이 없으면 None."""
        ad = self._ssmod()
        return None if ad is None else ad.run_all()


# ══ 공급자 — 합성(실제 자료 없음) ═════════════════════════════════════════════════════════════════
class SynthProvider:
    """합성 세계 — r_stagem 패널과 같은 모양 · 표지는 그룹-월 베르누이 · y = 섹터 + 크기 + 효과 + 잡음(σ 8).
    eff = {"R1": OS 가 t−2..t 에 켜진 이름의 다음 달 효과(%p), "R2": CH_t 효과, "R3": FL t−2..t 효과}.
    R1 표지는 정본 cikmonth 모양대로 쌍둥이 칸(OS_T1 · OS_T2/RS_T2 · OS_T4/RS_T4 · OS_T6/RS_T6)과 CLS 를 한 판에 싣는다(따로 씨앗 줄기)."""
    kind = "synth"

    def __init__(self, seed=5, T=T_NOMINAL, N=300, nsec=10, eff=None, m0=M0):
        eff = dict(eff or {})
        rng = np.random.default_rng(seed)
        rtw = np.random.default_rng(seed * 7919 + 13)          # 쌍둥이 칸 줄기(주 줄기를 흔들지 않는다)
        months = months_between(m0, mshift(m0, T - 1))
        pre = [mshift(m0, -j) for j in (2, 1)]
        base = rng.normal(23.0, 1.2, N)
        sec = np.array(["s%02d" % (j % nsec) for j in range(N)], object)
        grp = ["g%d" % j for j in range(N)]
        prob = {"O": 0.08, "R": 0.05, "U": 0.02, "CH": 0.12, "CH_miss": 0.05, "FL": 0.05, "AL": 0.01}
        H = {nm: {} for nm in prob}
        for mm in pre + months:
            for nm, pr in prob.items():
                H[nm][mm] = rng.random(N) < pr
        H["CH_miss"] = {mm: v & ~H["CH"][mm] for mm, v in H["CH_miss"].items()}
        f1, f2, f3, f5 = {}, {}, {}, {}
        for mm in pre + months:
            for j in range(N):
                o, r_, u = bool(H["O"][mm][j]), bool(H["R"][mm][j]), bool(H["U"][mm][j])
                if o or r_ or u:
                    t = rtw.random(3)
                    f1[(grp[j], mm)] = {"OS": float(o), "RS": float(r_), "OSW": float(o or u), "SALL": 1.0, "CLS": float(o or r_),
                                        "OS_T1": float(o and t[0] < 0.5), "OS_T1C": float(o and t[0] < 0.5), "OS_T2": float(o and t[1] < 0.8),
                                        "RS_T2": float(r_),
                                        "OS_T4": float(o or u), "RS_T4": float(r_), "OS_T6": float(o or t[2] < 0.05), "RS_T6": float(r_)}
                ch, mi = bool(H["CH"][mm][j]), bool(H["CH_miss"][mm][j])
                if ch or mi:
                    f2[(grp[j], mm)] = {"CH": float(ch), "CH_miss": float(mi), "dlog": float(rng.normal(0, 0.1))}
                if H["FL"][mm][j]:
                    f3[(grp[j], mm)] = {"FL": 1.0}
                if H["AL"][mm][j]:
                    f5[(grp[j], mm)] = {"AL": 1.0}
        self.fp = {"R1": f1, "R2": f2, "R3": f3, "R5": f5}
        anyk = lambda nm, mm, j: any(bool(H[nm][mshift(mm, -k)][j]) for k in (0, 1, 2))
        P = {"kind": "synth", "months": [], "m": {}, "stat": {}, "eg_rank": {}}
        for mm in months:
            keep = np.flatnonzero(rng.random(N) > 0.03)
            n = len(keep)
            size = base[keep] + rng.normal(0, 0.1, n)
            lbm = rng.normal(-1.0, 0.8, n)
            lbm[rng.random(n) < 0.05] = np.nan
            mom = rng.normal(8, 25, n)
            mom[rng.random(n) < 0.02] = np.nan
            egs = rng.random(n)
            order = np.argsort(-egs, kind="mergesort")
            top = np.zeros(n)
            top[order[:40]] = 1
            y = np.array([0.3 * int(s[1:]) - 1.0 for s in sec[keep]]) + 0.4 * (size - 23) + rng.normal(0, 8.0, n)
            if eff.get("R1"):
                y += eff["R1"] * np.array([anyk("O", mm, j) for j in keep], float)
            if eff.get("R2"):
                y += eff["R2"] * H["CH"][mm][keep].astype(float)
            if eff.get("R3"):
                y += eff["R3"] * np.array([anyk("FL", mm, j) for j in keep], float)
            keys = ["T%03d" % j for j in keep]
            P["m"][mm] = {"t": keys, "k": list(keys), "grp": [grp[j] for j in keep], "glag": [(grp[j],) * 3 for j in keep],
                          "sec": list(sec[keep]), "y": y, "mc": np.exp(size), "size": size, "logbm": lbm, "r1": rng.normal(1, 7, n),
                          "mom": mom, "r12": rng.normal(10, 30, n), "h52": rng.uniform(0.5, 1.0, n), "top40": top, "eg": egs}
            P["months"].append(mm)
            P["stat"][mm] = {"cov_n": 0.97, "cov_cap": 0.99, "im_ok": True}
            P["eg_rank"][mm] = [keys[i] for i in order[:40]]
        self.P = P
        self.y_stripped = False
        self._seed = seed
        self._N = N
        self.world_from = BOUND_FROM                           # 시험이 바꿔 경계 세계 점검을 본다

    def flags(self, c):
        return self.fp.get(c)

    def _thin(self, fp, frac, salt):
        rng = np.random.default_rng(self._seed * 1000 + salt)
        return {k: v for k, v in sorted(fp.items()) if rng.random() < frac}

    def variants(self, c):
        if c == "R1":
            return {}
        if c == "R2":
            return {nm: self._thin(self.fp["R2"], 0.9, 10 + i) for i, nm in enumerate(RF["variants_r2"])}
        return {nm: self._thin(self.fp["R3"], 0.7, 20 + i) for i, nm in enumerate(RF["twins_r3"])}

    def r2_world_info(self):
        return world_info({("g%d" % j, mm) for mm in months_between(self.world_from, M1) for j in range(self._N)})

    def r2_external(self):
        return {"pairs_year": {y: 1000 for y in R2_PAIR_YEARS}, "fail_rate": {y: 0.05 for y in R2_FAIL_YEARS}, "parser_c": True}

    def g_concord(self):
        return {"row_match": 0.999, "os_mismatch": 0.002}

    def group_of(self, k, r):
        return "g%d" % int(k[1:])

    def r5_source(self):
        return "합성"

    def stage_s_rule(self):
        return {"module": "none", "provisional": False, "rule": "합성 — 러너 기본 교체 수 셈"}

    def stage_s_nr(self, c, fp, flag, win):
        if fp is None:
            return None, 0
        forms = [r for r in quarterly_forms() if r in self.P["eg_rank"]]
        return count_nr(self.P, fp, flag, win, forms, self.group_of)

    def stage_s_all(self):
        return None


def synth_p0doc(T, p0, density=True, external=True):
    """합성 P0 문서(r_p0 문서 모양) — p0 = {"R1": 값 또는 None, "R2": …}."""
    cards = {}
    for c in CANDIDATES:
        v = p0.get(c)
        ext = {"parser_c_validation": external, "annual_pairs_ge_900": external, "split_fail_le_20pct": external} if c == "R2" else {}
        elig = v is not None and v >= P0_GATE and T >= T_MIN and density and all(x is True for x in ext.values())
        cards[CODES[c]] = {"p0": v, "T": T, "sigma_plan": 1.2, "pi": 0.4, "p0_pass": v is not None and v >= P0_GATE,
                           "T_pass": T >= T_MIN, "density_pass": density, "external_f0": ext, "eligible": elig}
    mem = [CODES[c] for c in CANDIDATES if cards[CODES[c]]["eligible"]]
    return {"kind": "r_p0", "cards": cards, "holm": {"m": len(mem), "members": mem}, "result_sha": "synthetic"}


def real_like_p0doc(T, sig, density=True, external=True):
    """r_p0.run 모양 그대로의 합성 P0 문서(식 칸 · 상수 · result_sha · 카드마다 σ → t_alt · π · P0 를 r_p0 식으로) — strict 시험용.
    sig = {"R1": σ_plan, "R2": …}."""
    from scipy.stats import norm
    const = {"q": P0_Q, "alpha1": P0_A1, "t_crit": P0_TCRIT, "alt_scale": P0_SCALE, "gate": P0_GATE, "T_min": T_MIN, "holm_alpha": ALPHA,
             "p0_floor": {"rule": "P0 = min(P0_σ, P0_lit)", "lit_scale": P0_SCALE,
                          "lit": {k: {"t_lit": v[0], "T_lit": v[1]} for k, v in P0_LIT.items()}}}
    lit = {"R1": -0.55, "R2": -0.80}
    cards, mem = {}, []
    for c in CANDIDATES:
        s = sig[c]
        ta = P0_SCALE * abs(lit[c]) * math.sqrt(T) / s
        pi = float(norm.sf(P0_TCRIT - ta))
        Ps = P0_Q * pi + (1 - P0_Q) * P0_A1
        tl, Tl = P0_LIT[CODES[c]]
        tal = P0_SCALE * tl * math.sqrt(T / Tl)
        pil = float(norm.sf(P0_TCRIT - tal))
        Pl = P0_Q * pil + (1 - P0_Q) * P0_A1
        P0 = min(Ps, Pl)
        ext = {"parser_c_validation": external, "annual_pairs_ge_900": external, "split_fail_le_20pct": external} if c == "R2" else {}
        elig = bool(P0 >= P0_GATE and T >= T_MIN and density and all(x is True for x in ext.values()))
        cards[CODES[c]] = {"status": "ok", "gamma_lit": lit[c], "T": T, "sigma_analytic": round(s * 0.9, 6), "sigma_placebo": round(s, 6),
                           "sigma_plan": round(s, 6), "binding": "placebo", "t_alt": round(ta, 6), "pi": round(pi, 6), "p0": round(P0, 6),
                           "p0_sigma": round(Ps, 6), "t_alt_lit": round(tal, 6), "pi_lit": round(pil, 6), "p0_lit": round(Pl, 6),
                           "p0_binding": "sigma" if Ps <= Pl else "lit",
                           "p0_pass": bool(P0 >= P0_GATE), "T_pass": T >= T_MIN, "density_pass": density, "external_f0": ext,
                           "eligible": elig, "count_src": {"x": "canonical:synthetic"}, "dropped": {"undefined": [], "zero_focal": []}}
        if elig:
            mem.append(CODES[c])
    doc = {"kind": "r_p0", "formula": "P0 = q·π + (1−q)·α₁", "constants": const, "universe": {"hash": "u"}, "cards": cards,
           "holm": {"m": len(mem), "members": mem}}
    doc["result_sha"] = hashlib.sha256(json.dumps({k: doc[k] for k in RF["p0"]["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return doc


def synth_reg(p0doc, stage_s="none"):
    qual, m, fam = qualification(p0doc)
    return {"m": m, "primary": fam, "p0": {c: qual[c]["p0"] for c in CANDIDATES}, "snap": "synthetic", "base": "synthetic",
            "n_lab_prior": 716, "stage_s": stage_s, "frozen_extra": ()}


# ══ 명령 ═══════════════════════════════════════════════════════════════════════════════════════
def const_check():
    """상수 한 벌 — 러너 · 엔진(r_stagem) · P0(r_p0) · 표지 빌더(r_r2flags)가 같은 수를 쓰는가."""
    rows = []

    def eq(name, a, b):
        rows.append((name, a, b, a == b))
    S = _S()
    eq("r_stagem.M0/M1", (S.M0, S.M1), (M0, M1))
    eq("r_stagem.ALPHA", S.ALPHA, ALPHA)
    eq("r_stagem.P0_GATE", S.P0_GATE, P0_GATE)
    eq("r_stagem.T_MIN", S.T_MIN, T_MIN)
    eq("r_stagem.LAG", S.LAG, LAG)
    eq("r_stagem.F0_FLAG", S.F0_FLAG, F0_FLAG)
    eq("r_stagem.SPECS focal", tuple(S.SPECS[c]["focal"] for c in ("R1", "R2", "R3")), (FOCAL["R1"], FOCAL["R2"], FOCAL["R3"]))
    eq("r_stagem.JT R1/R2/R3", tuple(tuple(S.SPECS[c]["jt"]) for c in ("R1", "R2", "R3")), ((0, 1, 2), (0,), (0, 1, 2)))
    eq("r_stagem.BOUND_FROM", S.BOUND_FROM, BOUND_FROM)
    eq("r_stagem.SENS_FROM[1] · SPLIT_T2", (S.SENS_FROM[1], S.SPLIT_T2), (SENS_2020, T2_SPLIT))
    eq("r_stagem P0 식 상수(q · α₁ · 2.27)", (S.Q_PRIOR, S.ALPHA1, S.T_P0), (P0_Q, P0_A1, P0_TCRIT))
    try:
        import r_p0 as P0
        eq("r_p0.GATE", P0.GATE, P0_GATE)
        eq("r_p0.T_MIN", P0.T_MIN, T_MIN)
        eq("r_p0.HOLM_ALPHA", P0.HOLM_ALPHA, ALPHA)
        eq("r_p0.ALPHA1 = α/2", P0.ALPHA1, ALPHA / 2)
        eq("r_p0.T_CRIT = t(119) 0.0125", round(P0.T_CRIT, 2), round(crit_t(ALPHA / 2, T_NOMINAL), 2))
        eq("r_p0 창", (P0.SIG0, P0.SIG1), (M0, M1))
        eq("r_p0 P0 식 상수(q · α₁ · 2.27 · 0.5)", (P0.Q_PRIOR, P0.ALPHA1, P0.T_CRIT, P0.ALT_SCALE), (P0_Q, P0_A1, P0_TCRIT, P0_SCALE))
        eq("r_p0.BW0(경계 세계 첫 달)", P0.BW0, BOUND_FROM)
        eq("r_p0 P0 바닥 문헌 입력(t_lit · T_lit)", {k: (v["t_lit"], v["T_lit"]) for k, v in P0.LIT.items()}, P0_LIT)
    except Exception as e:
        rows.append(("r_p0 가져오기", str(e)[:60], "", False))
    try:
        import r_r2flags as R2
        eq("r_r2flags F0", (R2.F0_PAIRS_YEAR, R2.F0_FAIL_RATE, R2.F0_CH_MEDIAN), (F0_R2["pairs_year"], F0_R2["fail_rate"], F0_FLAG["CH"][0]))
    except Exception as e:
        rows.append(("r_r2flags 가져오기", str(e)[:60], "", False))
    try:
        import r_stages as RS
        eq("r_stages F0 · N · 창", (tuple(RS.F0_NR), RS.N_TOP, RS.WINDOW["OS"], RS.WINDOW["CH"]), (F0_S, STAGE_S_N, STAGE_S_WIN["R1"], STAGE_S_WIN["R2"]))
    except Exception as e:
        rows.append(("r_stages 가져오기", str(e)[:60], "", False))
    try:
        import r_r1_flags as R1
        eq("r_r1_flags Stage S", (R1.STAGE_S_N, R1.STAGE_S_WINDOW), (STAGE_S_N, STAGE_S_WIN["R1"]))
    except Exception as e:
        rows.append(("r_r1_flags 가져오기", str(e)[:60], "", False))
    return rows


def reg_problems(rebuild=False, rdata=None, reg=None):
    """등록 커밋 전 대조(--check-reg · --dry) — REG = P0 문서 = F0 문서(= P0 개수 표 경계 세계) · 양방향 · F0 문서 자기 점검 · P0 재유도.
    rebuild 면 PIT 세계로 F0 를 다시 세어(수익 없음) 커밋할 F0 문서와 바이트 대조한다(snap_wt 에서). 돌려주는 것 문제 목록(빈 목록 = 통과)."""
    rdata = rdata or RDATA
    reg = REG if reg is None else reg
    probs = []
    p0doc = _rj(os.path.join(rdata, _rel(RF["p0"]["file"])))
    f0doc = _rj(os.path.join(rdata, F0_NAME))
    counts = _rj(os.path.join(rdata, _rel(RF["p0_counts"]["file"])))
    blanks = reg_missing(reg)
    if blanks:
        probs.append("REG 빈칸 %s(등록 커밋에서 채운다 — 그때까지 문서끼리만 본다)" % blanks)
    if f0doc is None:
        probs.append("F0 문서(data/%s) 없음 — --f0 로 만든다" % F0_NAME)
    else:
        probs += ["F0 문서: %s" % x for x in f0_selfcheck(f0doc, real=True)]
        mod = (f0doc.get("stage_s_rule") or {}).get("module")
        if not blanks and mod != reg.get("stage_s"):
            probs.append("F0 문서의 Stage S 셈 규칙(%s)이 REG stage_s(%s)와 다르다 — REG 를 정한 뒤 --f0 를 다시" % (mod, reg.get("stage_s")))
        if f0doc.get("provider") != "real":
            probs.append("F0 문서 공급자가 %s 다(실제 판이 아니다)" % f0doc.get("provider"))
    if counts is None:
        probs.append("P0 개수 표(data/%s) 없음" % RF["p0_counts"]["file"])
    try:
        qual, m, fam = qualification(p0doc, strict=True)
        reg_consistency(None if blanks else reg, qual, m, fam, f0doc, counts)
    except SystemExit as e:
        probs.append(str(e))
    if rebuild and f0doc is not None:
        new = f0_doc(RealProvider(reg=reg, strip_y=True))
        for k in ("months_sha", "T", "panel_digest", "flags_sha", "stage_s_rule"):
            if _canon(new.get(k)) != _canon(f0doc.get(k)):
                probs.append("다시 센 F0 의 %s 가 커밋할 F0 문서와 다르다" % k)
        if _canon(new["f0"]) != _canon(f0doc.get("f0")):
            probs.append("다시 센 F0 표가 커밋할 F0 문서와 바이트로 다르다")
    return probs


def check_reg(argv=()) -> int:
    """--check-reg [--rebuild] — 등록 커밋 전(PREREG §12 ④ 뒤 ⑦ 전) REG · P0 · F0 대조. 수익 없음."""
    t0 = time.time()
    probs = reg_problems(rebuild="--rebuild" in argv)
    print("r_run --check-reg%s (수익 없음) · %.0f초" % (" --rebuild" if "--rebuild" in argv else "", time.time() - t0))
    for p in probs:
        print("  ✗ %s" % p)
    print("  %s" % ("통과 — REG = P0 문서 = F0 문서" if not probs else "문제 %d — 등록 커밋 전에 고친다" % len(probs)))
    return 0 if not probs else 1


def dry() -> int:
    """구조 점검 — 수익 없음. 상수 한 벌 · 얼린 파일 존재 · 가져오기 닫힘 핀 · 등록 빈칸 · 문서 이름 · 새 자료 · 선택 입력 · 덮어쓰기 ·
    고정표 링크(느슨) · 사전등록 빈칸 수 · --check-reg(문서 대조). 굽기 준비가 안 된 것이 하나라도 있으면 종료 코드 1."""
    probs = []
    print("r_run --dry (수익 없음)")
    for name, a, b, same in const_check():
        if not same:
            probs.append("상수 %s" % name)
        print("  %s %s%s" % ("✓" if same else "✗", name, "" if same else " — %r ≠ %r" % (a, b)))
    miss = [p for p in tuple(CODE_FROZEN) + tuple(P3_FROZEN) if not os.path.exists(os.path.join(ROOT, _rel(p)))]
    print("  얼린 파일 %d 가운데 없는 것 %d: %s" % (len(CODE_FROZEN) + len(P3_FROZEN), len(miss), miss))
    if miss:
        probs.append("얼린 파일 없음 %s" % miss)
    unp = closure_unpinned(dict(REG, stage_s=REG.get("stage_s") or "r_stages", frozen_extra=REG.get("frozen_extra") or ()))
    clo = import_closure(("r_run", REG.get("stage_s") or "r_stages"))
    print("  가져오기 닫힘 %d 모듈 · 얼린 목록 밖 %s" % (len(clo), unp or "없음"))
    if unp:
        probs.append("얼린 목록 밖 모듈 %s" % unp)
    blanks = reg_missing(REG)
    print("  등록 빈칸(REG): %s" % (blanks or "없음"))
    if blanks:
        probs.append("REG 빈칸 %s" % blanks)
    nb = name_check()
    print("  문서 이름: %s" % ("; ".join(nb) if nb else "날짜 줄기 한 벌"))
    probs += nb
    pp = os.path.join(ROOT, _rel(PREREG))
    if os.path.exists(pp):
        n = io.open(pp, encoding="utf-8").read().count(PLACEHOLDER)
        print("  사전등록 문서 %s 빈칸 %d" % (PLACEHOLDER + "⟩", n))
        if n:
            probs.append("사전등록 문서 빈칸 %d" % n)
    have = [p for p in NEW_DATA if os.path.exists(os.path.join(RDATA, _rel(p)))]
    lack = [p for p in NEW_DATA if p not in have]
    print("  새 자료 %d/%d 있음 · 없음 %s" % (len(have), len(NEW_DATA), lack))
    if lack:
        probs.append("새 자료 없음 %d" % len(lack))
    print("  선택 입력 %s" % {p: os.path.exists(os.path.join(RDATA, _rel(p))) for p in NEW_DATA_OPT})
    fb = forbidden_present()
    if fb:
        print("  ✗ 덮어쓰기 표지 %s 가 있다(굽기 전에 치운다)" % fb)
        probs.append("덮어쓰기 표지 %s" % fb)
    try:
        for r in link_check(strict=False):
            print("  링크 %-24s %-18s → %-32s %s(%s)" % (r["src"], r["key"], r["target"], r["result"], r["status"]))
    except SystemExit as e:
        probs.append(str(e))
        print("  ✗ %s" % e)
    for k, v in manifest_shas().items():
        print("  고정표 %s sha256 %s" % (k, (v or "없음")[:16]))
    rp = reg_problems()
    print("  --check-reg: %s" % ("통과" if not rp else "문제 %d" % len(rp)))
    for p in rp:
        print("    ✗ %s" % p)
    probs += rp
    print("r_run --dry: %s" % ("굽기 준비 끝" if not probs else "굽기 준비 안 됨 — 사유 %d(종료 코드 1)" % len(probs)))
    return 0 if not probs else 1


def f0_main(argv) -> int:
    """PIT 세계로 F0 문서를 쓴다(수익 없음 · y 는 짓자마자 NaN)."""
    t0 = time.time()
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(RDATA, F0_NAME)
    overlay_out_guard(out)
    prov = RealProvider(strip_y=True)
    doc = f0_doc(prov)
    with io.open(out + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1, default=_js) + "\n")
    os.replace(out + ".tmp", out)
    f0 = doc["f0"]
    print("r_run --f0 · T=%d(%s..%s) · 지도 나쁜 달 %d · %.0f초 → %s" % (doc["T"], f0["coverage"]["first"], f0["coverage"]["last"],
                                                                 len(f0["issuer_map"]["bad_months"]), time.time() - t0, out))
    for k, d in f0["density"].items():
        print("  밀도 %-4s 중앙값 %s · 최소 %s · F0 %s" % (k, d.get("median"), d.get("min"), d.get("ok")))
    rw = f0["r2_world"]
    print("  R2 경계 세계 %s..%s · 그룹-월 %d · sha %s" % (rw["first"], rw["last"], rw["n"], rw["sha"][:16]))
    print("  R2 외부 %s · Stage S %s · §G %s" % (f0["r2_external"].get("ok"), {c: f0["stage_s"][c].get("ok") for c in f0["stage_s"]},
                                              f0["g_concord"].get("ok")))
    bad = f0_selfcheck(doc, real=True)
    if bad:
        print("  ✗ F0 자기 점검: %s" % bad)
    return 0


def smoke_real(seed=20261020, nperm=2) -> int:
    """눈가린 연기 시험 — Stage M: 실제 표지 · 통제 + 잡음 y 로 러너 전체(Stage S 는 끈다). Stage S: 실제 세계 · 실제 지도 위 합성 표지로
    r_stages.run 을 qbatch_core.blind_smoke 에(REG["stage_s"] 또는 r_stages · 값은 버린다). 산출물 · 검문점은 임시 폴더에서 열지 않고 지운다 ·
    수치는 찍지 않는다. 🚨 실제 표지 × 실제 가격(Stage S 수익)은 계산하지 않는다."""
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="rbatch_smoke_")
    rc = 0
    try:
        prov = RealProvider(blind_seed=seed)
        f0d = f0_doc(prov)
        p0d = _rj(os.path.join(RDATA, _rel(RF["p0"]["file"])))
        if p0d is None or (p0d.get("holm") or {}).get("m") is None:
            p0d = synth_p0doc(f0d["T"], {"R1": None, "R2": None})
        reg = synth_reg(p0d, stage_s="none")
        doc = bake_core(prov, reg, p0d, f0d, "smoke", "smoke", os.path.join(tmp, "ck"), out_path=os.path.join(tmp, OUT_NAME))
        print("연기 시험(눈가림) Stage M: 예외 없음 · 키 %s · 카드 %s · 시도 %d · 못 돌린 시도 %d · %.0f초" % (
            sorted(doc)[:8], sorted(doc["stage_m"]), doc["trials"]["batch"], len(doc["trials"]["not_run"]), time.time() - t0))
        mod = REG.get("stage_s") if REG.get("stage_s") not in (None, "none") else "r_stages"
        t1 = time.time()
        sm = StageSAdapter(prov, mod).smoke(nperm=nperm)
        print("연기 시험(합성 표지) Stage S(%s · nperm %d): %s · 카드 %s · %.0f초" % (
            mod, nperm, "예외 없음" if sm["ok"] else "예외", sorted(k for k in (sm["shape"] or {}) if not k.startswith("_")), time.time() - t1))
        if not sm["ok"]:
            print((sm.get("err") or "")[-1500:])
            rc = 1
        return rc
    finally:
        _rmtree(tmp)


def smoke_synth() -> int:
    """합성 세계 끝에서 끝까지(실제 자료 없음 · 결과를 찍는다)."""
    prov = SynthProvider(seed=5, eff={"R1": -1.2})
    f0d = f0_doc(prov)
    p0d = synth_p0doc(f0d["T"], {"R1": 0.20, "R2": 0.18})
    tmp = tempfile.mkdtemp(prefix="rbatch_synth_")
    try:
        doc = bake_core(prov, synth_reg(p0d), p0d, f0d, "synthetic", "synthetic", os.path.join(tmp, "ck"), out_path=os.path.join(tmp, OUT_NAME))
        print_table(doc)
        return 0
    finally:
        _rmtree(tmp)


# ══ 합성 시험 ═══════════════════════════════════════════════════════════════════════════════════
def _synth_tenq(dirpath, n_groups=30, years=(2014, 2015, 2016, 2017), seed=44):
    """합성 10-Q 문서(§C 모양 · 정본 r_r2flags.load_tenq 가 읽는다) — 경계 세계 시험용(수익 없음)."""
    rng = np.random.default_rng(seed)
    docs = []
    for gi in range(n_groups):
        for y in years:
            for qm, rdd in ((5, "03-31"), (8, "06-30"), (11, "09-30")):
                docs.append({"acc": "%010d-%02d-%06d" % (gi, y % 100, qm), "gid": "g%d" % gi, "form": "10-Q", "rd": "%d-%s" % (y, rdd),
                             "acceptanceDateTime": "%d-%02d-10T14:00:00Z" % (y, qm), "shape": "F", "parse_status": "ok",
                             "SimRF": float(rng.uniform(0.6, 1.0)), "SimDoc": float(rng.uniform(0.8, 1.0)), "n_words_rf": 1000 + gi,
                             "shape_v3": "F", "parse_status_v3": "ok"})      # 등록 형태 판 v3 열(r_r2flags.REG_SHAPE_VER · 2026-09-26)
    tp = os.path.join(dirpath, "tenq.json")
    with io.open(tp, "w", encoding="utf-8") as fh:
        json.dump({"docs": docs}, fh)
    return tp


class _FakeFS:
    """시험용 FlagSource 모양(on = {달: {그룹}})."""

    def __init__(self, on):
        self.on = {m: set(v) for m, v in on.items()}


def selftest() -> int:
    fails, n_ok = [], 0

    def check(name, cond, info=""):
        nonlocal n_ok
        if cond:
            n_ok += 1
        else:
            fails.append(name)
            print("  ✗ %s %s" % (name, info))

    def raises(fn):
        try:
            fn()
        except SystemExit:
            return True
        except Exception as e:
            print("    (예외 %s: %s)" % (type(e).__name__, e))
            return False
        return False
    t0 = time.time()
    S, E = _S(), _E()
    # 1 문턱 · p · 주 통계(달력 위치)
    check("t(119) 0.0125 → 2.27", round(crit_t(0.0125, 120), 2) == 2.27, crit_t(0.0125, 120))
    check("t(119) 0.025 → 1.98", round(crit_t(0.025, 120), 2) == 1.98, crit_t(0.025, 120))
    check("p(t = −2.27, T = 120) ≈ 0.0125", abs(one_sided_p(-crit_t(0.0125, 120), 120) - 0.0125) < 1e-12)
    check("p(t 없음) = 1", one_sided_p(None, 120) == 1.0 and one_sided_p(float("nan"), 120) == 1.0)
    check("p 양의 t 는 크다", one_sided_p(2.5, 120) > 0.99)
    st = primary_stat([None] * 3 + [0.1, -0.2])
    check("주 통계 — 달 < 5 면 p = 1", st["p_one"] == 1.0 and st["nw_t"] is None)
    rng = np.random.default_rng(1)
    x = list(rng.normal(-0.5, 1.5, 120))
    st = primary_stat(x[:60] + [None] + x[60:])
    check("주 통계 — None 을 건너뛴 T · df", st["T"] == 120 and st["df"] == 119)
    check("주 통계 — 달 없으면 eg30plus.nw_t(압축)", abs(st["nw_t"] - E.nw_t(np.array(x), 3)) < 1e-12)
    ms = months_between(M0, mshift(M0, 119))
    st = primary_stat(x, ms)
    check("주 통계 — 이어진 달력 = eg30plus.nw_t · 빈 달 0", st["contiguous"] and st["gaps"] == 0 and abs(st["nw_t"] - E.nw_t(np.array(x), 3)) < 1e-12)
    xg = x[:60] + [None] + x[61:]
    st = primary_stat(xg, ms)
    eng = S.summarize({"months": ms, "g": {"a": xg}}, "a")
    xs = np.array(x[:60] + x[61:])
    check("주 통계 — 빈 달이 끼면 nw_t_gap(엔진 summarize 와 같다)", st["gaps"] == 1 and not st["contiguous"]
          and abs(st["nw_t"] - eng["nw_t"]) < 1e-12 and abs(st["p_one"] - eng["p_one"]) < 1e-12
          and abs(st["nw_t_compressed"] - E.nw_t(xs, 3)) < 1e-12 and abs(st["nw_t"] - st["nw_t_compressed"]) > 1e-9, (st, eng))
    ms2 = ms[:60] + ms[61:]
    st2 = primary_stat(x[:60] + x[61:], ms2)
    check("주 통계 — 달이 빠진 달 목록도 같은 값(엔진 fm 모양)", st2["gaps"] == 1 and abs(st2["nw_t"] - st["nw_t"]) < 1e-12)
    check("주 통계 — 계열 · 달 길이 다르면 멈춤", raises(lambda: primary_stat(x, ms[:-1])))

    # 2 Holm
    mk = lambda p, T=120: {"p_one": p, "nw_t": -1.0, "T": T}
    h = holm_fixed({"R1": mk(0.010), "R2": mk(0.020)}, 2, ["R1", "R2"])
    check("Holm m=2 둘 다", h["rows"]["R1"]["pass"] and h["rows"]["R2"]["pass"] and h["rows"]["R1"]["alpha"] == 0.0125)
    h = holm_fixed({"R1": mk(0.013), "R2": mk(0.014)}, 2, ["R1", "R2"])
    check("Holm m=2 첫 칸에서 멈춤", not h["rows"]["R1"]["pass"] and not h["rows"]["R2"]["pass"])
    h = holm_fixed({"R1": mk(0.030), "R2": mk(0.001)}, 2, ["R1", "R2"])
    check("Holm m=2 하나(순서는 p)", h["order"] == ["R2", "R1"] and h["rows"]["R2"]["pass"] and not h["rows"]["R1"]["pass"])
    check("Holm m=2 문턱 t 2.27 → 1.98", round(h["rows"]["R2"]["crit_t"], 2) == 2.27 and round(h["rows"]["R1"]["crit_t"], 2) == 1.98)
    h = holm_fixed({"R2": mk(0.024)}, 1, ["R2"])
    check("Holm m=1 α 0.025", h["rows"]["R2"]["pass"] and h["rows"]["R2"]["alpha"] == 0.025)
    h = holm_fixed({"R1": mk(0.0125), "R2": mk(0.0125)}, 2, ["R1", "R2"])
    check("Holm 같은 p — 이름순 · 경계 포함", h["order"] == ["R1", "R2"] and h["rows"]["R1"]["pass"] and h["rows"]["R2"]["pass"])
    check("Holm m=0 빈 가족", holm_fixed({}, 0, [])["rows"] == {})
    check("Holm 가족 크기 ≠ m → 멈춤", raises(lambda: holm_fixed({"R1": mk(0.01)}, 2, ["R1"])))
    check("Holm m=3 → 멈춤", raises(lambda: holm_fixed({}, 3, [])))
    check("Holm 통계 카드 ≠ 가족 → 멈춤", raises(lambda: holm_fixed({"R1": mk(0.01), "R3": mk(0.01)}, 2, ["R1", "R2"])))
    check("Holm p 없음(1) 도 가족에 남는다", not holm_fixed({"R1": mk(1.0), "R2": mk(0.001)}, 2, ["R1", "R2"])["rows"]["R1"]["pass"])

    # 3 관문
    ser = lambda v, n=120: [v] * n
    r1 = {"main": {"OS": ser(-0.3), "RS": ser(0.1)}, "extra": {"OS": ser(-0.2)}, "wls": {"OS": ser(-0.1)}}
    g = gates_r1(r1, True)
    check("R1 관문 모두 참", g["all"] and g["gates"] == {"i": True, "ii": True, "iii": True})
    g = gates_r1(r1, False)
    check("R1 관문 i — RS 밀도 F0 미달이면 닫힌 실패", not g["gates"]["i"] and g["raw"]["i"] and not g["all"] and "i" in g["notes"])
    g = gates_r1(dict(r1, wls={"OS": ser(0.05)}), True)
    check("R1 관문 iii — WLS 양수면 거짓", not g["gates"]["iii"] and not g["all"])
    g = gates_r1(dict(r1, main={"OS": ser(-0.3), "RS": ser(-0.5)}), True)
    check("R1 관문 i — γ_OS − γ_RS ≥ 0 이면 거짓", not g["gates"]["i"])
    g = gates_r1(dict(r1, extra={"OS": [None] * 120}), True)
    check("R1 관문 ii — 값이 없으면 거짓", not g["gates"]["ii"] and g["vals"]["ii"] is None)
    r2 = {"main": {"CH": ser(-0.4), "CH_miss": ser(-0.9)}, "wls": {"CH": ser(-0.3)}, "len": {"CH": ser(-0.2)}}
    g = gates_r2(r2)
    check("R2 관문 · 오염 보고", g["all"] and g["contam"])
    check("R2 관문 ii — 길이 통제에서 0 이면 거짓", not gates_r2(dict(r2, len={"CH": ser(0.0)}))["all"])

    # 4 F0 · R2 경계 세계
    check("F0 OS 중앙값 20 · 최소 5 통과", f0_flag_ok("OS", [20] * 60 + [5] + [30] * 59))
    check("F0 OS 최소 4 실패", not f0_flag_ok("OS", [25] * 119 + [4]))
    check("F0 OS 중앙값 19.5 실패", not f0_flag_ok("OS", [19] * 60 + [20] * 60))
    check("F0 RS 중앙값 10 통과 · 최소 무관", f0_flag_ok("RS", [10] * 100 + [0] * 20))
    check("F0 CH 중앙값 29 실패", not f0_flag_ok("CH", [29] * 120))
    check("F0 빈 달 실패", f0_flag_ok("OS", []) is False)
    check("Stage S 2 · 15 통과", f0_stage_s([2, 2, 3])["ok"] and f0_stage_s([15, 15, 14])["ok"])
    check("Stage S 1.5 · 16 실패", not f0_stage_s([1, 2])["ok"] and not f0_stage_s([16, 17, 15])["ok"])
    check("Stage S 미연결 = None", f0_stage_s(None)["ok"] is None)
    good = {"pairs_year": {y: 900 for y in R2_PAIR_YEARS}, "fail_rate": {y: 0.20 for y in R2_FAIL_YEARS}, "parser_c": True}
    check("R2 외부 경계 통과", f0_r2_external(good)["ok"] is True)
    check("R2 외부 짝 899 실패", f0_r2_external(dict(good, pairs_year=dict(good["pairs_year"], **{"2019": 899})))["ok"] is False)
    check("R2 외부 실패율 0.21 실패", f0_r2_external(dict(good, fail_rate=dict(good["fail_rate"], **{"2021": 0.21})))["ok"] is False)
    check("R2 외부 해 빠짐 실패", f0_r2_external(dict(good, pairs_year={y: 950 for y in R2_PAIR_YEARS[1:]}))["ok"] is False)
    check("R2 외부 파서 미확인 = None", f0_r2_external(dict(good, parser_c=None))["ok"] is None)
    check("R2 외부 창 밖 해는 보지 않는다", f0_r2_external(dict(good, pairs_year=dict(good["pairs_year"], **{"2026": 10})))["ok"] is True)
    check("§G 경계", f0_g({"row_match": 0.995, "os_mismatch": 0.01})["ok"] and not f0_g({"row_match": 0.99, "os_mismatch": 0.0})["ok"])
    check("§G 없음 = None", f0_g(None)["ok"] is None)
    wfull = world_info({("g1", m) for m in months_between(BOUND_FROM, M1)})
    wpan = world_info({("g1", m) for m in months_between(M0, M1)})
    check("경계 세계 2015-01 부터면 통과", r2_world_check(wfull) is True and wfull["first"] == BOUND_FROM)
    check("경계 세계가 패널 달(2016-08)부터면 멈춤", raises(lambda: r2_world_check(wpan)))
    check("경계 세계 빈 해가 있으면 멈춤", raises(lambda: r2_world_check(world_info({("g1", m) for m in months_between(BOUND_FROM, M1) if m[:4] != "2019"}))))
    tq = tempfile.mkdtemp(prefix="rrun_tq_")
    try:
        tp, nim = _synth_tenq(tq), os.path.join(tq, "no_map.json")
        win = ("2016-08", "2017-07")
        W_bound = {("g%d" % gi, mm) for gi in range(30) for mm in months_between(BOUND_FROM, "2017-12")}
        W_panel = {("g%d" % gi, mm) for gi in range(30) for mm in months_between("2016-08", "2017-12")}
        var, R = r2_flag_set(W_bound, tp, nim, win)
        check("R2 표지 한 벌 — 경계 세계면 네 판 · 경계는 세계 12달", sorted(var) == ["covid", "doc", "ixbrl", "rf"]
              and R["bounds"][2016]["world_months"] == 12 and set(R["bounds"][2016]["src"]) == {"caller"}, R["bounds"].get(2016))
        check("R2 표지 한 벌 — 패널 세계(2015 짝 없음)면 멈춤(uncovered_all 섞임)", raises(lambda: r2_flag_set(W_panel, tp, nim, win)))
    finally:
        _rmtree(tq)

    # 5 자격 · 등록 대조 · 판정
    p0d = synth_p0doc(120, {"R1": 0.20, "R2": 0.18})
    qual, m, fam = qualification(p0d)
    check("자격 m=2", m == 2 and fam == ["R1", "R2"])
    p0low = synth_p0doc(120, {"R1": 0.12, "R2": 0.149999})
    qual0, m0, fam0 = qualification(p0low)
    check("P0 < 0.15 → m=0 · 사유", m0 == 0 and fam0 == [] and any("< 0.15" in w for w in qual0["R2"]["reasons"]))
    p0T = synth_p0doc(83, {"R1": 0.30, "R2": 0.30})
    check("T < 84 → m=0", qualification(p0T)[1] == 0)
    p0ext = synth_p0doc(120, {"R1": 0.20, "R2": 0.30}, external=None)
    q_, m_, f_ = qualification(p0ext)
    check("R2 외부 미확인 → 가족 밖", f_ == ["R1"] and not q_["R2"]["eligible"])
    bad = json.loads(json.dumps(p0d))
    bad["cards"]["R2-LAZYRF"]["eligible"] = False
    check("eligible 이 식과 다르면 멈춤", raises(lambda: qualification(bad)))
    real = dict(json.loads(json.dumps(p0d)), formula="f", constants={"q": 0.4}, universe={"hash": "u"})
    real["result_sha"] = hashlib.sha256(json.dumps({k: real[k] for k in RF["p0"]["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    check("P0 문서 result_sha 맞음", not raises(lambda: qualification(json.loads(json.dumps(real)))))
    real["cards"]["R1-OPPSELL"]["p0"] = 0.21
    check("P0 문서를 손으로 고치면 멈춤(result_sha)", raises(lambda: qualification(real)))
    bad = json.loads(json.dumps(p0d))
    bad["holm"]["m"] = None
    check("m 미정이면 멈춤", raises(lambda: qualification(bad)))
    bad = json.loads(json.dumps(p0d))
    bad["holm"] = {"m": 1, "members": ["R1-OPPSELL"]}
    check("가족이 자격 카드와 다르면 멈춤", raises(lambda: qualification(bad)))
    edge = synth_p0doc(120, {"R1": 0.20, "R2": 0.15})
    edge["cards"]["R2-LAZYRF"].update(p0_pass=False, eligible=False)       # r_p0: 반올림 전 0.1499996 → p0_pass 거짓 · 반올림 0.15
    edge["holm"] = {"m": 1, "members": ["R1-OPPSELL"]}
    check("P0 경계(반올림 0.15 · p0_pass 거짓)는 문서 p0_pass 를 따른다", not raises(lambda: qualification(edge))
          and qualification(edge)[2] == ["R1"])
    bad = synth_p0doc(120, {"R1": 0.20, "R2": 0.30})
    bad["cards"]["R2-LAZYRF"]["p0_pass"] = False
    check("p0_pass 가 경계 밖에서 p0 와 어긋나면 멈춤", raises(lambda: qualification(bad)))
    rl = real_like_p0doc(120, {"R1": 1.2, "R2": 1.5})
    qs, ms_, fs_ = qualification(rl, strict=True)
    check("strict — r_p0 모양 문서 통과 · 재유도 일치 · P0 바닥(문헌 t)이 묶어 T = 120 에서 자격 없음(m = 0)",
          fs_ == [] and ms_ == 0 and not raises(lambda: qualification(rl, strict=True))
          and all(rl["cards"][CODES[c]]["p0_binding"] == "lit" and rl["cards"][CODES[c]]["p0_sigma"] >= P0_GATE for c in CANDIDATES))
    bad = json.loads(json.dumps(rl))
    bad["cards"]["R1-OPPSELL"]["p0_lit"] = round(bad["cards"]["R1-OPPSELL"]["p0_lit"] + 0.01, 6)
    bad["result_sha"] = hashlib.sha256(json.dumps({k: bad[k] for k in RF["p0"]["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    check("strict — P0 바닥 값을 고치면 재유도가 멈춤", raises(lambda: qualification(bad, strict=True)))
    bad = json.loads(json.dumps(rl))
    bad["constants"]["p0_floor"]["lit"]["R2-LAZYRF"]["T_lit"] = 108
    bad["result_sha"] = hashlib.sha256(json.dumps({k: bad[k] for k in RF["p0"]["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    check("strict — P0 바닥의 문헌 입력이 러너와 다르면 멈춤", raises(lambda: qualification(bad, strict=True)))
    bad = json.loads(json.dumps(rl))
    bad["cards"]["R1-OPPSELL"]["p0"] = round(bad["cards"]["R1-OPPSELL"]["p0"] + 0.01, 6)
    bad["result_sha"] = hashlib.sha256(json.dumps({k: bad[k] for k in RF["p0"]["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    check("strict — P0 를 고치고 result_sha 까지 다시 쓰면 재유도가 멈춤", raises(lambda: qualification(bad, strict=True))
          and not raises(lambda: qualification(bad)))
    check("strict — result_sha 없는 문서 멈춤", raises(lambda: qualification(p0d, strict=True)))
    bad = json.loads(json.dumps(rl))
    bad["cards"]["R2-LAZYRF"]["count_src"] = {"CH": "override:_r_flags.json"}
    bad["result_sha"] = hashlib.sha256(json.dumps({k: bad[k] for k in RF["p0"]["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    check("strict — 덮어쓰기 출처 개수면 멈춤", raises(lambda: qualification(bad, strict=True)))
    bad = json.loads(json.dumps(rl))
    bad["constants"]["q"] = 0.5
    bad["result_sha"] = hashlib.sha256(json.dumps({k: bad[k] for k in RF["p0"]["sha_keys"]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    check("strict — 상수가 카드 식과 다르면 멈춤", raises(lambda: qualification(bad, strict=True)))
    reg = synth_reg(p0d)
    check("등록 대조 통과", not raises(lambda: reg_consistency(reg, qual, m, fam, None)))
    check("REG m 다르면 멈춤", raises(lambda: reg_consistency(dict(reg, m=1), qual, m, fam, None)))
    check("REG 가족 다르면 멈춤", raises(lambda: reg_consistency(dict(reg, primary=["R1"]), qual, m, fam, None)))
    check("REG P0 다르면 멈춤", raises(lambda: reg_consistency(dict(reg, p0={"R1": 0.21, "R2": 0.18}), qual, m, fam, None)))
    check("REG 빈칸 목록", reg_missing(REG) == list(REG) and reg_missing(reg) == [])
    f0 = {"stage_s": {"R1": {"ok": True}, "R2": {"ok": True}}, "g_concord": {"ok": True}, "r2_external": {"parser_c": True}}
    gt = {"R1": {"gates": {"i": True, "ii": True, "iii": True}, "all": True, "notes": {}},
          "R2": {"gates": {"i": True, "ii": False}, "all": False, "notes": {}, "contam": False, "vals": {}}}
    hh = holm_fixed({"R1": mk(0.001), "R2": mk(0.02)}, 2, ["R1", "R2"])
    V = verdicts(qual, fam, hh, gt, f0)
    check("판정 — 통과 · 채택 경로", V["R1"]["stage_m"] == V_PASS and V["R1"]["stage_s_arm"] == ARM_ADOPT)
    check("판정 — Holm 통과 · 관문 ii 미달 → 기각", V["R2"]["stage_m"] == V_REJ + " — 관문 ii 미달" and V["R2"]["stage_s_arm"] == ARM_MEAS)
    check("판정 — R3 · R5 고정 라벨", V["R3"]["stage_m"] == V_R3 and V["R5"]["stage_m"] == V_R5)
    check("머리 줄 — 통과", headline(V, 2)["판정"].startswith("Stage M 통과(R1)") and headline(V, 2)["풀카드"] == "없음")
    hh = holm_fixed({"R1": mk(0.02), "R2": mk(0.03)}, 2, ["R1", "R2"])
    V = verdicts(qual, fam, hh, gt, f0)
    check("판정 — Holm 미달 → 기각 · 머리 줄 기각", V["R1"]["stage_m"] == V_REJ and headline(V, 2)["판정"] == "기각")
    V = verdicts(qual0, fam0, holm_fixed({}, 0, []), gt, f0)
    check("판정 — m=0 → 둘 다 측정만(사유 P0)", V["R1"]["stage_m"] == V_MEAS and V["R2"]["stage_m"] == V_MEAS
          and V["R1"]["stage_s_arm"] == ARM_MEAS and any("P0" in w for w in V["R1"]["why"]) and headline(V, 0)["판정"] == "측정만")
    hh = holm_fixed({"R1": mk(0.001), "R2": mk(0.02)}, 2, ["R1", "R2"])
    V = verdicts(qual, fam, hh, gt, dict(f0, stage_s={"R1": {"ok": False, "median": 1.0}, "R2": {"ok": True}}))
    check("판정 — Stage S F0 미달 → 측정 팔", V["R1"]["stage_m"] == V_PASS and V["R1"]["stage_s_arm"].startswith(ARM_MEAS + "(Stage S F0 미달"))
    V = verdicts(qual, fam, hh, gt, dict(f0, stage_s={"R1": {"ok": True, "provisional": True}, "R2": {"ok": True}}))
    check("판정 — 잠정 Stage S 는 채택 경로를 열지 않는다", V["R1"]["stage_s_arm"].startswith(ARM_MEAS + "(Stage S F0 미확인"))
    V = verdicts(qual, fam, hh, gt, dict(f0, g_concord={"ok": None}))
    check("판정 — §G 전에는 팔을 열지 않는다(표시)", V["R1"]["stage_s_arm"].startswith(ARM_ADOPT + " — 조건 §G"))
    gbad = {"R1": {"gates": {"i": np.bool_(True), "ii": True, "iii": True}, "all": True, "notes": {}}, "R2": gt["R2"]}
    check("관문 불리언 아님 → 멈춤(닫힌 실패)", raises(lambda: verdicts(qual, fam, hh, gbad, f0)))

    # 6 엔진 대조
    st = primary_stat(x, ms)
    rec = {"engine_sum": {"T": 120, "mean": st["mean"], "nw_t": st["nw_t"], "p_one": st["p_one"], "gaps": 0}}
    check("엔진 대조 같음", not raises(lambda: engine_check("R1", rec, st, None)))
    rec2 = {"engine_sum": dict(rec["engine_sum"], nw_t=st["nw_t"] + 1e-6)}
    check("엔진 대조 다르면 멈춤", raises(lambda: engine_check("R1", rec2, st, None)))
    check("엔진 대조 — 빈 달 수가 다르면 멈춤", raises(lambda: engine_check("R1", {"engine_sum": dict(rec["engine_sum"], gaps=1)}, st, None)))
    g1 = gates_r1(r1, True)
    check("엔진 관문 다르면 멈춤", raises(lambda: engine_check("R1", {"engine_gates": {"i": True, "ii": True, "iii": False}}, st, g1)))
    check("엔진 관문 불리언 아님 → 멈춤", raises(lambda: engine_check("R1", {"engine_gates": {"i": 1, "ii": True, "iii": True}}, st, g1)))
    g0 = gates_r1(r1, False)
    check("엔진 관문 — F0 조건 뒤 값끼리 대조(i 닫힌 실패)", not raises(lambda: engine_check("R1", {"engine_gates": {"i": False, "ii": True, "iii": True}}, st, g0))
          and raises(lambda: engine_check("R1", {"engine_gates": {"i": True, "ii": True, "iii": True}}, st, g0)))

    # 7 굽기 문 · 자리표시자 · 이름 · 가져오기 닫힘
    old = os.environ.pop("RBATCH_COMMIT", None)
    try:
        check("frozen_check — 자리표시자 이름 · 빈칸 · 커밋 없음이면 멈춤", raises(lambda: frozen_check()))
        check("frozen_check — 등록 값이 차도 커밋 없으면 멈춤(이름 자리표시자 포함)", raises(lambda: frozen_check(reg)))
    finally:
        if old is not None:
            os.environ["RBATCH_COMMIT"] = old
    nm_ok = ("build/PREREG-2026-10-02-RBATCH.md", "build/PREREG-2026-10-02-RBATCH-CARDS.md", "build/PREREG-2026-10-02-RBATCH-RESULT.md")
    check("이름 — 한 날짜 줄기면 문제 없음", name_check(*nm_ok) == [])
    check("이름 — RESULT 만 자리표시자여도 잡는다", any("RESULT" in b for b in name_check(nm_ok[0], nm_ok[1], "build/PREREG-2026-09-2x-RBATCH-RESULT.md")))
    check("이름 — 날짜 줄기가 다르면 잡는다", any("줄기" in b for b in name_check(nm_ok[0], "build/PREREG-2026-10-03-RBATCH-CARDS.md", nm_ok[2])))
    check("이름 — 지금 판은 자리표시자", len(name_check()) >= 3)
    clo = import_closure(("r_run", "r_stages"))
    check("가져오기 닫힘 — qbatch_run · refresh_events · r_stagem 포함", all(p in clo for p in ("build/qbatch_run.py", "build/refresh_events.py",
                                                                                   "build/r_stagem.py", "build/r_r2flags.py")), clo)
    check("가져오기 닫힘 — 모두 얼린 목록 안", closure_unpinned(dict(REG, stage_s="r_stages", frozen_extra=())) == [],
          closure_unpinned(dict(REG, stage_s="r_stages", frozen_extra=())))

    # 8 검문점 · 9 핀
    tmp = tempfile.mkdtemp(prefix="rrun_st_")
    try:
        hdr = {"commit": "x", "card": "R1", "v": 1}
        R, res = ck_run(tmp, "R1", hdr, lambda: {"a": 1}, False)
        R2_, res2 = ck_run(tmp, "R1", hdr, lambda: {"a": 2}, True)
        check("검문점 이어받기", R == {"a": 1} and R2_ == {"a": 1} and res2 and not res)
        check("검문점 머리 다르면 멈춤", raises(lambda: ck_run(tmp, "R1", dict(hdr, v=2), lambda: {}, True)))
        check("검문점 머리 — 코드 지문에 qbatch_run · refresh_events", all(p in ck_code(("r_stages",)) for p in ("build/qbatch_run.py", "build/refresh_events.py")))
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, "d"))
        with open(os.path.join(repo, "a.txt"), "wb") as f:
            f.write(b"x\ny\n")
        with open(os.path.join(repo, "d", "b.bin"), "wb") as f:
            f.write(b"\x00\x01")
        gi = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.name=r_run", "-c", "user.email=r_run@selftest.invalid",
                                        "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false"] + list(a), capture_output=True, text=True)
        gi("init", "-q")
        gi("add", "-A")
        gi("commit", "-q", "-m", "c1")
        c1 = gi("rev-parse", "HEAD").stdout.strip()
        loc = lambda f: os.path.join(repo, _rel(f))
        check("핀 같음", pin_check(repo, c1, ["a.txt", "d"], loc) == [], pin_check(repo, c1, ["a.txt", "d"], loc))
        check("선택 핀 — 커밋 · 로컬 모두 없음은 문제 아님 · 있으면 대조",
              pin_check_optional(repo, c1, ["zz.json", "a.txt"], loc) == ([], {"zz.json": "없음(커밋 · 로컬)", "a.txt": "있음"}))
        with open(os.path.join(repo, "zz.json"), "wb") as f:
            f.write(b"{}")
        check("선택 핀 — 로컬에만 있으면 어긋남", pin_check_optional(repo, c1, ["zz.json"], loc)[0] == [("zz.json", "로컬에만 있다(커밋에 없다)")])
        os.remove(os.path.join(repo, "zz.json"))
        with open(os.path.join(repo, "a.txt"), "wb") as f:
            f.write(b"x\r\ny\r\n")
        check("핀 CRLF 판도 같음", pin_check(repo, c1, ["a.txt"], loc) == [])
        with open(os.path.join(repo, "a.txt"), "wb") as f:
            f.write(b"x\nz\n")
        check("핀 내용 다름", pin_check(repo, c1, ["a.txt"], loc) == [("a.txt", "내용이 다르다")])
        check("선택 핀 — 내용이 다르면 어긋남", pin_check_optional(repo, c1, ["a.txt"], loc)[0] == [("a.txt", "내용이 다르다")])
        with open(os.path.join(repo, "d", "c.bin"), "wb") as f:
            f.write(b"new")
        check("핀 폴더에 커밋 없는 파일", ("d/c.bin", "커밋에 없는 로컬 파일") in pin_check(repo, c1, ["d"], loc))
        check("핀 커밋에 없는 경로", pin_check(repo, c1, ["zz.json"], loc) == [("zz.json", "커밋에 없다")])
        gi("add", "-A")
        gi("commit", "-q", "-m", "c2")
        c2 = gi("rev-parse", "HEAD").stdout.strip()
        check("처음 더한 커밋", first_add_is(repo, c2, "d/c.bin") and not first_add_is(repo, c2, "a.txt") and first_add_is(repo, c1, "a.txt"))
        gi("update-ref", "refs/remotes/origin/main", c1)
        check("origin/main 조상", is_ancestor(repo, c1, "origin/main") and not is_ancestor(repo, c2, "origin/main"))
        dd = os.path.join(tmp, "data")
        os.makedirs(dd)
        check("덮어쓰기 표지 없음", forbidden_present(dd) == [])
        with open(os.path.join(dd, FORBID_DATA[0]), "w", encoding="utf-8") as f:
            f.write("{}")
        check("덮어쓰기 표지가 있으면 잡는다", forbidden_present(dd) == [FORBID_DATA[0]])
    finally:
        _rmtree(tmp)

    # 10 끝에서 끝까지(합성 세계 · 실제 엔진 r_stagem)
    t1 = time.time()
    prov = SynthProvider(seed=5, eff={"R1": -1.2})
    f0d = f0_doc(prov)
    check("합성 F0 — T 120 · 밀도 통과", f0d["T"] == 120 and all(f0d["f0"]["density"][k]["ok"] for k in ("OS", "RS", "CH")),
          {k: (v.get("median"), v.get("min")) for k, v in f0d["f0"]["density"].items()})
    check("합성 F0 — Stage S 교체 수 중앙값 2~15", all(f0d["f0"]["stage_s"][c]["ok"] for c in CANDIDATES),
          {c: f0d["f0"]["stage_s"][c].get("median") for c in CANDIDATES})
    check("합성 F0 — 수익을 쓰지 않았다고 적는다 · 경계 세계 2015-01", f0d["f0"]["r2_world"]["first"] == BOUND_FROM and f0d["firewall"]["returns_used"] is False)
    check("합성 F0 — 자기 점검 통과", f0_selfcheck(f0d, real=False) == [], f0_selfcheck(f0d, real=False))
    bad = json.loads(json.dumps(f0d))
    bad["f0"]["density"]["CH"]["ok"] = not bad["f0"]["density"]["CH"]["ok"]
    check("F0 자기 점검 — 손으로 고친 밀도 판정을 잡는다", len(f0_selfcheck(bad, real=False)) == 1)
    check("F0 자기 점검 — 실제 판은 방화벽 칸을 본다", any("방화벽" in b for b in f0_selfcheck(f0d, real=True)))
    pw = SynthProvider(seed=5, eff={"R1": -1.2})
    pw.world_from = M0
    check("끝에서 끝 — 경계 세계가 패널 달부터면 F0 가 멈춤", raises(lambda: f0_doc(pw)))
    p0d = synth_p0doc(f0d["T"], {"R1": 0.20, "R2": 0.18})
    qd, md, fd = qualification(p0d)
    check("양방향 — 합성 문서끼리 통과", not raises(lambda: docs_consistency(qd, md, fd, f0d)))
    p0x = synth_p0doc(f0d["T"], {"R1": 0.20, "R2": 0.10}, density=True)
    p0x["cards"]["R2-LAZYRF"]["density_pass"] = False
    qx, mx, fx = qualification(p0x)
    check("양방향 — 가족 밖 카드의 밀도가 F0 와 다르면 멈춤", fx == ["R1"] and raises(lambda: docs_consistency(qx, mx, fx, f0d)))
    p0x = synth_p0doc(f0d["T"] - 1, {"R1": 0.20, "R2": 0.18})
    qx, mx, fx = qualification(p0x)
    check("양방향 — P0 T 가 F0 T 와 다르면 멈춤", raises(lambda: docs_consistency(qx, mx, fx, f0d)))
    p0x = synth_p0doc(f0d["T"] - 2, {"R1": 0.20, "R2": 0.18})
    p0x["cards"]["R1-OPPSELL"]["dropped"] = {"zero_focal": f0d["months"][:2], "undefined": [], "gate": [], "window_no_rows": []}
    p0x["cards"]["R2-LAZYRF"]["dropped"] = {"zero_focal": [], "undefined": f0d["months"][-2:], "gate": [], "window_no_rows": []}
    qx, mx, fx = qualification(p0x)
    check("양방향 — P0 가 뺀 주 표지 0 · 정의 밖 달만큼 T 가 작으면 통과", not raises(lambda: docs_consistency(qx, mx, fx, f0d)))
    p0x["cards"]["R1-OPPSELL"]["dropped"]["gate"] = [f0d["months"][5]]
    qx, mx, fx = qualification(p0x)
    check("양방향 — P0 가 F0 쓸 달을 달 관문으로 뺐으면 멈춤", raises(lambda: docs_consistency(qx, mx, fx, f0d)))
    p0x = synth_p0doc(f0d["T"], {"R1": 0.20, "R2": 0.18}, external=None)
    qx, mx, fx = qualification(p0x)
    check("양방향 — R2 외부 F0 가 P0 · F0 에서 다르면 멈춤", raises(lambda: docs_consistency(qx, mx, fx, f0d)))
    cnt = {"r2_boundary_world": {"first": BOUND_FROM, "n": f0d["f0"]["r2_world"]["n"], "ok": True}}
    check("양방향 — 경계 세계 크기 같으면 통과", not raises(lambda: docs_consistency(qd, md, fd, f0d, cnt)))
    cnt = {"r2_boundary_world": {"first": BOUND_FROM, "n": f0d["f0"]["r2_world"]["n"] - 7, "ok": True}}
    check("양방향 — 경계 세계(r_p0 member_world ≠ boundary_world)가 다르면 멈춤", raises(lambda: docs_consistency(qd, md, fd, f0d, cnt)))
    tmp = tempfile.mkdtemp(prefix="rrun_e2e_")
    try:
        ck = os.path.join(tmp, "ck")
        outp = os.path.join(tmp, OUT_NAME)
        doc = bake_core(prov, synth_reg(p0d), p0d, f0d, "synthetic", "t", ck, out_path=outp)
        J = _rj(outp)
        check("끝에서 끝 — JSON 이 쓰이고 읽힌다", J is not None and J["headline"] == doc["headline"])
        check("끝에서 끝 — 심은 R1 효과 통과", doc["verdicts"]["R1"]["stage_m"] == V_PASS, (doc["stage_m"]["R1"]["primary"], doc["stage_m"]["R1"]["gates"]))
        check("끝에서 끝 — R1 은 첫 칸 α 0.0125", doc["holm"]["order"][0] == "R1" and doc["holm"]["rows"]["R1"]["alpha"] == 0.0125)
        check("끝에서 끝 — 효과 없는 R2 기각", doc["verdicts"]["R2"]["stage_m"].startswith(V_REJ), doc["stage_m"]["R2"]["primary"])
        check("끝에서 끝 — R3 측정만 · 가족 밖", doc["verdicts"]["R3"]["stage_m"] == V_R3 and "R3" not in doc["holm"]["rows"])
        check("끝에서 끝 — 단계 팔 채택 경로(R1)", doc["verdicts"]["R1"]["stage_s_arm"] == ARM_ADOPT)
        check("끝에서 끝 — R5 이름-월 > 0", (doc["r5"].get("name_months") or 0) > 0)
        nm = doc["trials"]["names"]
        r1n = [x for x in nm if x.startswith("R1.")]
        check("끝에서 끝 — R1 시도 13(엔진 한 벌 · 쌍둥이 T1~T6 한 번씩 · 선언된 민감도 T1C · tw_ 없음)", len(r1n) == 13
              and all("R1.t%d" % k in r1n for k in range(1, 7)) and "R1.t1c" in r1n and not any("tw_" in x for x in r1n), r1n)
        r2n = [x for x in nm if x.startswith("R2.")]
        check("끝에서 끝 — R2 시도 7(대조 SimDoc · iXBRL · 코로나를 엔진이 돌렸다)", len(r2n) == 7 and all(k in r2n for k in ("R2.simdoc", "R2.diag_ixbrl", "R2.diag_covid")), r2n)
        check("끝에서 끝 — R3 시도 6", len([x for x in nm if x.startswith("R3.")]) == 6, [x for x in nm if x.startswith("R3.")])
        nr = {r["id"] for r in doc["trials"]["not_run"]}
        check("끝에서 끝 — 못 돌린 시도(선언 sens2014 · Stage S 모듈 없음 · R3 Stage S)를 싣는다",
              {"R1.sens2014", "R2.sens2014", "R1-OPPSELL.S.rule", "R3-8KNE.S.placebo"} <= nr, sorted(nr)[:8])
        check("끝에서 끝 — 시도 수 26 · 누적", doc["trials"]["batch"] == 26 and doc["trials"]["cumulative"] == 716 + 26, doc["trials"]["batch"])
        check("끝에서 끝 — df = T − 1 · 이어진 달력", doc["stage_m"]["R1"]["primary"]["df"] == doc["stage_m"]["R1"]["primary"]["T"] - 1
              and doc["stage_m"]["R1"]["primary"]["gaps"] == 0)
        check("끝에서 끝 — T2 분할 보고는 한 시도 안", "split" in doc["stage_m"]["R1"]["measures"]["t2"])
        doc2 = bake_core(prov, synth_reg(p0d), p0d, f0d, "synthetic", "t", ck, resume=True)
        check("끝에서 끝 — 검문점 이어받기 · 같은 결과", all(doc2["checkpoint"][c]["resumed"] for c in ("R1", "R2", "R3"))
              and _canon(doc2["stage_m"]["R1"]["primary"]) == _canon(doc["stage_m"]["R1"]["primary"]))
        p0z = synth_p0doc(f0d["T"], {"R1": 0.10, "R2": 0.12})
        doc3 = bake_core(prov, synth_reg(p0z), p0z, f0d, "synthetic", "t", ck, resume=True)
        check("끝에서 끝 — m=0 이면 효과가 있어도 측정만", doc3["verdicts"]["R1"]["stage_m"] == V_MEAS and doc3["headline"]["판정"] == "측정만"
              and doc3["holm"]["rows"] == {})
        p01 = synth_p0doc(f0d["T"], {"R1": 0.10, "R2": 0.40})
        doc4 = bake_core(prov, synth_reg(p01), p01, f0d, "synthetic", "t", ck, resume=True)
        check("끝에서 끝 — m=1(R2 만) α 0.025", doc4["holm"]["family"] == ["R2"] and doc4["holm"]["rows"]["R2"]["alpha"] == 0.025
              and doc4["verdicts"]["R1"]["stage_m"] == V_MEAS)
        bad = json.loads(json.dumps(f0d))
        k0 = sorted(bad["f0"]["density"]["OS"]["by_month"])[0]
        bad["f0"]["density"]["OS"]["by_month"][k0] += 1
        check("끝에서 끝 — F0 가 등록 판과 다르면 멈춤", raises(lambda: bake_core(prov, synth_reg(p0d), p0d, bad, "synthetic", "t", ck, resume=True)))
        bad = dict(f0d, panel_digest="0" * 64)
        check("끝에서 끝 — 패널 지문이 다르면 멈춤", raises(lambda: bake_core(prov, synth_reg(p0d), p0d, bad, "synthetic", "t", ck, resume=True)))
        check("끝에서 끝 — F0 문서 없으면 멈춤", raises(lambda: bake_core(prov, synth_reg(p0d), p0d, None, "synthetic", "t", ck, resume=True)))
        check("끝에서 끝 — 다른 판 검문점이면 멈춤", raises(lambda: bake_core(SynthProvider(seed=6, eff={"R1": -1.2}), synth_reg(p0d), p0d,
                                                                        f0_doc(SynthProvider(seed=6, eff={"R1": -1.2})), "synthetic", "t", ck, resume=True)))
        # 빈 달 세 갈래 — 흩어진 커버리지 실패 달 · 자유도로 건너뛴 달 · 주 표지 0 달(R3 · m = 0) — 엔진과 러너가 같은 NW t 로 굽는다
        pa = SynthProvider(seed=5, eff={"R1": -1.2})
        pa.P["stat"][pa.P["months"][60]]["cov_n"] = 0.5
        fa = f0_doc(pa)
        pa0 = synth_p0doc(fa["T"], {"R1": 0.20, "R2": 0.18})
        da = None
        try:
            da = bake_core(pa, synth_reg(pa0), pa0, fa, "synthetic", "t", os.path.join(tmp, "cka"))
        except SystemExit as e:
            print("    (멈춤 %s)" % e)
        check("빈 달 — 흩어진 커버리지 실패 달이 있어도 굽는다(nw_t_gap)", da is not None and fa["T"] == 119
              and da["stage_m"]["R1"]["primary"]["gaps"] == 1 and da["stage_m"]["R1"]["primary"]["nw_t_compressed"] is not None)
        pb = SynthProvider(seed=5, eff={"R1": -1.2})
        mb = pb.P["months"][40]
        Db = pb.P["m"][mb]
        for key in list(Db):
            Db[key] = Db[key][:12]
        fb_ = f0_doc(pb)
        pb0 = synth_p0doc(fb_["T"], {"R1": 0.10, "R2": 0.10})               # 그달 행 12 → OS 최소 < 5(밀도 F0 거짓) — P0 문서도 같게
        for c in CANDIDATES:
            pb0["cards"][CODES[c]]["density_pass"] = all(fb_["f0"]["density"][f]["ok"] for f in P0_DENS[c])
        db = None
        try:
            db = bake_core(pb, synth_reg(pb0), pb0, fb_, "synthetic", "t", os.path.join(tmp, "ckb"))
        except SystemExit as e:
            print("    (멈춤 %s)" % e)
        check("빈 달 — 자유도로 건너뛴 달이 있어도 굽는다", db is not None and db["stage_m"]["R1"]["primary"]["gaps"] >= 1
              and db["stage_m"]["R2"]["primary"]["gaps"] >= 1, db and db["stage_m"]["R1"]["primary"])
        pc = SynthProvider(seed=5, eff={"R1": -1.2})
        mc_ = pc.P["months"][50]
        pc.fp["R3"] = {k: v for k, v in pc.fp["R3"].items() if k[1] != mc_}
        fc = f0_doc(pc)
        pc0 = synth_p0doc(fc["T"], {"R1": 0.10, "R2": 0.10})
        dc = None
        try:
            dc = bake_core(pc, synth_reg(pc0), pc0, fc, "synthetic", "t", os.path.join(tmp, "ckc"))
        except SystemExit as e:
            print("    (멈춤 %s)" % e)
        check("빈 달 — R3 주 표지 0 달(JT 세 달)이 있어도 m = 0 굽기가 돈다", dc is not None and dc["stage_m"]["R3"]["primary"]["gaps"] == 3
              and dc["headline"]["판정"] == "측정만", dc and dc["stage_m"]["R3"]["primary"])
    finally:
        _rmtree(tmp)
    print("  (끝에서 끝 %.0f초)" % (time.time() - t1))

    # 11 Stage S 모듈 연결(가짜 모듈 — 계약 이름만 본다)
    import types
    fake = types.ModuleType("_rrun_fake_stages")
    fake.View = lambda Wd, im: types.SimpleNamespace(Wd=Wd, im=im, months=["2016-08", "2016-09"])
    fake.load_bundle = lambda view, r2_world=None: {"im": "IM", "w": len(r2_world or ()), "src": {},
                                                    "OS": _FakeFS({"2016-08": {"g1"}}), "CH": _FakeFS({"2016-09": {"g2"}}),
                                                    "ALARM": _FakeFS({"2016-09": {"g3", "g4"}})}
    fake.build = lambda view, b: {"v0_hash": "v0h", "cards": {
        "R1-OPPSELL": {"hash": "h1", "f0": {"n_r": {"2016-12": 4, "2016-08": 3, "2017-03": 40}, "excluded": {"2017-03": ["OS 창 밖"]}, "ok": True}},
        "R2-LAZYRF": None, "R12-STACK": None, "R5-ALARM": {"hash": "h5"}}}
    fake.run = lambda ctx, b, nperm=1000: {
        "R1-OPPSELL": {"code": "R1-OPPSELL", "cls": "M", "f0": {"ok": True}, "targets_hash": "h1", "fr": {"hold": ["2016-09"], "ex": [0.1]},
                       "fr20": {"ex": [0.09]}, "fr_pr": {"ex": [0.08]}, "controls": {"V0": {"ex": [0.0]}, "V0_20": {"ex": [0.0]}, "C3": {"ex": [0.2]}},
                       "placebo": {"random": {}}, "log": {"measured": {"x": 1}}},
        "R5-ALARM": {"code": "R5-ALARM", "cls": "count", "f0": {"ok": True}, "targets_hash": "h5", "log": {"counts": {"n": 3}}},
        "_meta": {"sec": 0, "v0_hash": "v0h", "nperm": nperm}}
    sys.modules["_rrun_fake_stages"] = fake
    fprov = types.SimpleNamespace(Wd="WD", bworld=lambda: {("g1", "2015-01")})
    ad = StageSAdapter(fprov, "_rrun_fake_stages")
    check("Stage S 연결 — 교체 수는 잴 수 있는 편입만 · 편입 순서", ad.n_r("R1") == [3, 4] and ad.n_r("R2") is None, ad.n_r("R1"))
    fc1 = ad.f0_card("R1", {("g1", "2016-08"): {"OS": 1.0}, ("g9", "2016-08"): {"OS": 0.0}})
    check("Stage S 연결 — 모듈 F0 · 뺀 편입 · 목표 해시 · 표지 일치", fc1["module_ok"] is True and fc1["targets_hash"] == "h1"
          and fc1["excluded"] == {"2017-03": ["OS 창 밖"]} and fc1["flag_agree"]["only_m"] == 0, fc1)
    check("Stage S 연결 — Stage M 과 묶음 표지가 다르면 멈춤", raises(lambda: ad.flag_agree("R1", {("g1", "2016-08"): {"OS": 1.0}, ("g2", "2016-08"): {"OS": 1.0}})))
    check("Stage S 연결 — 목표 해시 · V0 해시", ad.hashes() == {"R1-OPPSELL": "h1", "R2-LAZYRF": None, "R12-STACK": None, "R5-ALARM": "h5", "_v0": "v0h"})
    check("Stage S 연결 — R5 는 묶음 ALARM 하나에서", ad.alarm_pairs() == [("g3", "2016-09"), ("g4", "2016-09")])
    import qbatch_core as _QC
    _old_ctx = _QC.Ctx
    _QC.Ctx = lambda: types.SimpleNamespace()
    try:
        allr = ad.run_all(nperm=7)
    finally:
        _QC.Ctx = _old_ctx
    check("Stage S 연결 — 측정 팔 요약 · 20bp · PR 행", allr["R1-OPPSELL"]["arms"] == ["rule", "C3", "placebo"] and allr["R2-LAZYRF"] is None
          and allr["R5-ALARM"]["counts"] == {"n": 3} and allr["R5-ALARM"]["arms"] == [] and allr["_meta"]["nperm"] == 7
          and allr["R1-OPPSELL"]["series"]["rule_20bp"] == [0.09] and allr["R1-OPPSELL"]["series"]["rule_pr"] == [0.08]
          and allr["R1-OPPSELL"]["series"]["V0_20"] == [0.0], allr["R1-OPPSELL"])
    rows = stage_s_rows(allr)
    run_ids = [r["id"] for r in rows if r["run"]]
    check("Stage S 시도 — 돈 팔만 세고 등록 팔의 빈칸은 못 돌린 시도로", run_ids == ["R1-OPPSELL.S.rule", "R1-OPPSELL.S.C3", "R1-OPPSELL.S.placebo"]
          and {"R1-OPPSELL.S.C1", "R2-LAZYRF.S.rule", "R3-8KNE.S.hibeta"} <= {r["id"] for r in rows if not r["run"]}, run_ids)
    check("Stage S 시도 — 모듈이 없으면 모든 팔이 못 돌린 시도", all(not r["run"] for r in stage_s_rows(None)) and len(stage_s_rows(None)) == sum(len(v) for v in S_ARMS.values()))
    fz = {"stage_s_hashes": ad.hashes()}
    check("Stage S 목표 해시 — 등록 F0 와 같으면 통과", not raises(lambda: stage_s_hash_check(allr, fz)))
    check("Stage S 목표 해시 — 다르면 멈춤", raises(lambda: stage_s_hash_check(dict(allr, **{"R1-OPPSELL": dict(allr["R1-OPPSELL"], targets_hash="zz")}), fz)))
    check("Stage S 목표 해시 — V0 해시가 다르면 멈춤", raises(lambda: stage_s_hash_check(dict(allr, _meta={"v0_hash": "x"}), fz)))
    del sys.modules["_rrun_fake_stages"]

    # 12 상수 한 벌
    rows = const_check()
    bad = [r for r in rows if not r[3]]
    check("상수 한 벌(r_stagem · r_stages · r_p0 · r_r2flags · r_r1_flags)", not bad, bad)
    print("r_run --selftest: %d 통과 · %d 실패%s · %.0f초" % (n_ok, len(fails), (" — " + ", ".join(fails)) if fails else "", time.time() - t0))
    return 1 if fails else 0


# ══ 굽기 ═══════════════════════════════════════════════════════════════════════════════════════
def main() -> int:
    t0 = time.time()
    overlay_out_guard(os.path.join(RDATA, OUT_NAME))          # 내부 가격 오버레이 판은 저장소 밖 RBATCH_DATA 에만 굽는다
    fz = frozen_check()
    commit = fz["commit"]
    resume = os.environ.get("RBATCH_RESUME")
    mark = os.path.join(RDATA, MARK_NAME)
    p0doc = _rj(os.path.join(RDATA, _rel(RF["p0"]["file"])))
    f0doc = _rj(os.path.join(RDATA, F0_NAME))
    counts = _rj(os.path.join(RDATA, _rel(RF["p0_counts"]["file"])))
    qual, m, fam = qualification(p0doc, strict=True)                                  # 긴 계산 · 시작 표식 전에 등록 대조(수익 없음)
    if f0doc is None:
        raise SystemExit("🚨 F0 문서(data/_r_f0.json)가 없다.")
    reg_consistency(REG, qual, m, fam, f0doc, counts)
    bad = f0_selfcheck(f0doc, real=True)
    if bad:
        raise SystemExit("🚨 F0 문서가 제 칸끼리 맞지 않는다: %s" % bad)
    if os.environ.get("RBATCH_RERUN") or resume:
        started = io.open(mark, encoding="utf-8").read().strip()                     # 처음 시작 시각을 그대로
    else:
        started = "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
        with io.open(mark, "w", encoding="utf-8", newline="\n") as f:               # 수익을 건드리기 전에 — 도중에 죽어도 한 번 굽기가 지켜진다
            f.write(started + "\n")
    ck = os.environ.get("RBATCH_CKPT_DIR") or os.path.join(os.environ.get("TEMP") or tempfile.gettempdir(), "rbatch_ckpt", commit[:12])
    if not resume and os.path.isdir(ck):
        _rmtree(ck)
    prov = RealProvider(REG)
    doc = bake_core(prov, REG, p0doc, f0doc, commit, started, ck, resume=bool(resume), out_path=os.path.join(RDATA, OUT_NAME),
                    meta={"pins": {k: v for k, v in fz.items() if k != "commit"}}, counts=counts)
    print_table(doc)
    print("→ %s (%.0f초)" % (os.path.join(RDATA, OUT_NAME), time.time() - t0))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--selftest" in a:
        sys.exit(selftest())
    if "--dry" in a:
        sys.exit(dry())
    if "--check-reg" in a:
        sys.exit(check_reg(a))
    if "--f0" in a:
        sys.exit(f0_main(a))
    if "--smoke-real" in a:
        sys.exit(smoke_real())
    if "--smoke-synth" in a:
        sys.exit(smoke_synth())
    sys.exit(main())
