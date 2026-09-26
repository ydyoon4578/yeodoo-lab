# -*- coding: utf-8 -*-
"""build/v_run.py — 배치 V 한 번 굽기 러너: 얼린 판 점검 → 시작 표식 셋 → 굽기 자식 과정(run_batch) → EG30 비교 줄(v_cmp · 별도 과정) →
저장소 밖 산출 · 게시 칸 · 실행 기록. F0(비중 · 개수 · 날짜 · 라벨만 — 수익 없음)도 이 파일이 만든다.

사전등록: build/PREREG-<등록 날짜>-VBATCH.md 하나(이 러너는 날짜를 박지 않는다 · 결과 문서 = 그 이름 + «-RESULT» · §6 이 이 파일을 설명한다 ·
  글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).
설계 원본(구속): vbatch_research.json final(slate · allocator · conditions · estimator · tests · multiplicity · data_plan · build_plan · registration ·
  forward_plan · honest_outlook · decisions) + 오케스트레이터 결정 8 변경(V08 «NI — 순자사주» 전방 전용). 판정 식은 여기서 새로 쓰지 않는다 —
  build/v_core · v_cards · v_alloc · v_tests 의 함수를 명세 차례대로 부를 뿐이다(명세 build_plan.modules[v_run] «한 번 굽기 · frozen_check ·
  L 산출은 저장소 밖 캐시 · S 는 결과 문서»).

  python -X utf8 build/v_run.py --selftest        판 점검이 빈 환경 · 없는 커밋 · 등록 안 된 커밋을 막는가 · 시작 표식 규칙 · 등록 상수 · 게시 칸 누수 ·
                                                  직렬화 · 모듈 셈 · 경계 · F0 결정 거르개 · 빈칸 셈 · open() 인코딩(합성만)
  python -X utf8 build/v_run.py --guard           사이트 경계(v_guard · t_guard) + G-NoEG 정적 전이(참/거짓 · 이름만)
  python -X utf8 build/v_run.py --pins            얼린 파일 표(git blob · LF sha256) — 등록 문서 §6 표를 이 명령으로 만든다
  python -X utf8 build/v_run.py --init-cache-id   캐시 표지(<캐시>/meta/cache_id.txt · 없을 때만) — 그 뒤 v_data.py --manifest --with-anchors
  python -X utf8 build/v_run.py --f0              F0(비중 · 개수 · 날짜 · 라벨 · 커버리지 · 앵커 · 군 배정 · G-EGD · G-COMMON · LIQ τ) → data/_vb_f0.json
                                                  (공개 안전 · 등록 커밋이 더한다) + 저장소 밖 <캐시>/f0/ 전부 · 🚨 수익 · 신호-수익 통계 없음
  python -X utf8 build/v_run.py --f0-table        data/_vb_f0.json → 등록 문서 §3.6 표(Markdown · 표준출력)
  python -X utf8 build/v_run.py --vfwd-genesis    VFWD 창세(data/_vfwd/genesis.json · 카드 · 규칙 참조 · 진입 · FF0~FF2 상수 · 코드 핀 — 등록 커밋이 더한다)
  python -X utf8 build/v_run.py --result-doc [<_vbatch.public.json>]   결과 문서 본문(Markdown · 표준출력) — 게시 칸 파일 하나만 읽는다(얼린 렌더러 · 굽기 뒤)
  python -X utf8 build/v_run.py --precommit       등록 커밋 직전 점검(참/거짓 · 이름만): 고정본 · 캐시 핀 · 캐시 표지 · F0 · 빈칸 · 경계 · 얼린 파일 · 복사 짝맞춤
  python -X utf8 build/v_run.py --backup | --restore <캐시 뿌리>   고정본(캐시 raw · meta · derived · lit)과 짝맞춤 원본(u_core · u_tests)을 %TEMP% 밖 사적 폴더로
  python -X utf8 build/v_run.py --smoke           러너 경로 전체 눈가린 연기(F0 → 굽기 자식 → 비교 줄 거부 → 게시 칸 → 실행 기록 · 위약 3 · 선견 작게) —
                                                  산출 · 표식은 저장소 밖 임시 폴더에만 쓰고 열지 않고 지운다 · ok · 초 · 파일 존재 · 모듈 이름만 돌려준다
  VBATCH_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python -X utf8 build/v_run.py      한 번 굽기(이 길 하나뿐)

한 번 굽기 규약(t_run · u_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(낡은 로컬 origin/main 으로 판정하지 않는다 · 실패하면 멈춘다).
  · VBATCH_COMMIT = 사전등록 문서 · 이 러너 · F0 문서(data/_vb_f0.json) · VFWD 창세(data/_vfwd/genesis.json)를 **처음 더한** 커밋 · origin/main 의 조상.
  · 그 커밋의 사전등록 문서에 빈칸(⟨TBD)과 초안 괄호(U+3014)가 하나도 없다.
  · 얼린 파일(새 v_* 파일 · 명세 셋 + 굽기 경로가 부르는 랩 모듈 — 연기 시험이 sys.modules 로 센 것의 상위 집합)이 그 커밋과 바이트 단위로 같다(CRLF 무시).
  · 굽기가 읽는 랩 자료(V_LAB_FILES)가 그 커밋의 판과 같고 추적 안 된 파일도 없다 · 명세 SHA(v_data.check_pins) · 캐시 핀(V-D1 · companyfacts ·
    ^GSPC · 넓힌 원장 · 문헌 열기 기록) = 명세 · 캐시 표지 SHA = 명세(등록한 캐시 뿌리에서만).
  · F0 문서가 끝났다(결정 칸이 모두 있고 · 시총 앵커 관문이 참이고(pass · repaired — 명세 «실패면 굽지 않고 고친다») · G-EGD 칸이 여덟 카드 모두 있고 ·
    F0 자식 G-NoEG 가 참이고 · F0 를 만든 코드 sha = 얼린 코드) · VFWD 창세(data/_vfwd/genesis.json)의 코드 핀 = 얼린 코드.
  · 산출물이 없다 — 저장소 밖 산출 · 실행 기록 · origin/main 의 결과 문서 어느 것이든 있으면 어떤 사유로도 다시 돌지 않는다(다시 굽기는 새 등록).
  · 시작 표식 셋 — 로컬 둘(<캐시>/out/_vbatch.started · 저장소 git 공용 폴더의 vbatch_started)을 **무엇보다 먼저** 쓰고, 이어 origin 에 태그
    refs/tags/vbatch-started(= 등록 커밋)를 계산 **전에** 민다(밀지 못하면 멈춘다). 굽기가 끝나면 두 로컬 표식에 «FINISHED <산출 sha256>» 줄을 덧붙인다.
    FINISHED 줄이 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤(다른 사본 · 복원한 캐시 · 새 clone) · 산출 전 기술적 중단이면 **이 컴퓨터의**
    같은 커밋 표식이 있을 때만 VBATCH_RERUN=사유 로 처음부터(이어하기는 없다).
  · PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 · numpy 2.5.3 · scipy 1.18.1 · pandas 3.0.6.
  · 등록 상수(추정기 · 틀 · 창 · 위약 1,000 · 선견 200 · 씨앗 20260925 …)가 실행 때도 그대로다.
  · 🔒 G-NoEG 굽기 때(명세 build_plan.guards): (1) 판 점검이 v_guard.noeg_static(전이 · 함수 안 import 포함)을 다시 돈다 (2) 계산은 **자식 과정**에서 돌고
    끝에 sys.modules 에 금지 모듈이 없어야 한다 (3) 자식 과정의 open 감사에 EG 파일이 없어야 한다 (4) 명세에 EG 파일이 없다(v_data.assert_no_eg_files).
    하나라도 거짓이면 실행 기록에 «등록 오류(G-NoEG)» — 산출은 쓰였으므로 다시 굽지 않는다(결과 문서가 그 오류를 머리에 적는다).
    EG30 비교 줄은 v_cmp(허용 목록 유일 · 별도 과정 · VBATCH_REGISTERED = 등록 커밋)만 만들고, 어떤 Δ · 관문 · 귀무에도 들지 않는다.
  · 산출은 저장소 밖(D1): <캐시>/out/_vbatch.json(전부 · L 층 포함) · _vbatch.public.json(결과 문서가 옮길 수 있는 칸만 — 등록 §5 를 코드로 ·
    L 층 수치 없음) · _vbatch.run.json(커밋 · 시각 · sha256 · 환경 · 판 · 불러온 build/ 모듈(부모 · 자식) · G-NoEG 셋 · 얼리지 않은 모듈 = 등록 오류 — 값 없음) ·
    _vbatch.child.json(자식 과정 기록 · 값 없음) · _vbatch.cmp.json(EG30 비교 줄 · v_cmp 가 쓴다).
  · 🔓 배치 R 굽기의 자물쇠: 이 등록 커밋이 origin/main 에 오르면 그 커밋이 RBATCH_AFTER_V 다(build/r_run.py after_v_check — VBATCH_GLOB
    «build/PREREG-*-VBATCH*.md» · RESULT · CARDS 제외 · 그 문서를 처음 더한 커밋 · origin/main 조상). 배치 R 은 그 뒤에만 굽는다(RBATCH §5.4).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산해서 찍지 않는다. --f0 은 비중 · 개수 · 날짜 · 라벨 · 커버리지 ·
   앵커(자료 타당성) · 회전(비중 경로)만 · --smoke 는 눈가린 채(산출을 열지 않고 지운다). 위생 상관(w_B 월수익 대 SPY)은 수익 통계라 F0 가 아니라 굽기에서 잰다(선언).
"""
from __future__ import annotations

import glob
import hashlib
import io
import json
import math
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import v_guard as VG         # noqa: E402  G-NoEG · 사이트 경계(표준 라이브러리만)
import v_data as VD          # noqa: E402  캐시 경계 · 명세 · 고정본


# ══════════════════════════════════════════════════════════════════════════
#  등록 문서 · 얼린 파일 · 등록 상수
# ══════════════════════════════════════════════════════════════════════════
def _find_prereg():
    """등록 문서 — build/PREREG-<날짜>-VBATCH.md 하나(RESULT · CARDS 는 이 글에 맞지 않는다). 둘 이상이거나 없으면 자리 이름 · 판 점검이 멈춘다."""
    c = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-VBATCH.md")))
    return ("build/" + c[0]) if len(c) == 1 else "build/PREREG-0000-00-00-VBATCH.md", len(c)


PREREG, _N_PREREG = _find_prereg()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"                 # 결과 문서 = 등록 문서 이름 + «-RESULT»
RUNNER = "build/v_run.py"
F0_FILE = "data/_vb_f0.json"                                 # F0 결정 · 셈(공개 안전 · 등록 커밋이 더한다 · v_guard.VB_ALLOWED)
VFWD_GENESIS = "data/_vfwd/genesis.json"                      # VFWD 창세(검토 고침 · 명세 registration.commit_order «VFWD 창세를 함께» · v_guard.VFWD_ALLOWED)
FIRST_ADDED = (PREREG, RUNNER, F0_FILE, VFWD_GENESIS)
NEW_FROZEN = ("build/v_data.py", "build/v_cond.py", "build/v_fund.py", "build/v_px_split.py", "build/v_pit.py", "build/v_ins.py", "build/v_ear.py",
              "build/v_guard.py", "build/v_core.py", "build/v_cards.py", "build/v_alloc.py", "build/v_tests.py", "build/v_cmp.py", "build/v_audit.py",
              RUNNER, "data/_vb_manifest.json", "data/_vb_lit_open.json", F0_FILE, VFWD_GENESIS)
# 가져다 쓰는 랩 모듈(고치지 않는다) — 굽기 자식 과정의 전이 폐포(v_guard.reach) + v_cmp 폐포(EG30 비교 줄 · 별도 과정) + 경계 t_guard.
#   selftest 가 «폐포 ⊆ 얼린 파일» 을 확인하고 · 연기 시험 · 굽기가 sys.modules 로 센 build/ 모듈이 여기 없으면 «등록 오류».
REUSED_FROZEN = ("build/t_pit.py", "build/pit_panel.py", "build/pit_alias.py", "build/pit_quarantine.py", "build/tech_backtest.py",
                 "build/index_members.py", "build/ml_strats.py", "build/ml_core.py", "build/pit_backtest.py", "build/edgar.py", "build/shares_split.py",
                 "build/shares_clean.py", "build/mech_episodes.py", "build/t_guard.py",
                 "build/eg30plus.py", "build/qg_lab.py", "build/stoploss.py", "build/rally_pattern.py")     # 마지막 넷 = v_cmp 폐포(비교 줄 · 별도 과정)
FROZEN = tuple(dict.fromkeys(NEW_FROZEN + REUSED_FROZEN))
# 굽기 자식 과정이 저장소 작업 트리에서 읽는 랩 자료 — v_data 명세 목록 + 사건 동결본. 연기 시험이 open 감사로 센 data/ 파일이 이 안에 있어야 한다.
V_LAB_FILES = tuple(VD.LAB_FILES) + tuple(VD.LAB_DIRS) + ("data/mech_episodes.json", "data/_vb_manifest.json", "data/_vb_lit_open.json", F0_FILE)
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"                    # 등록 문서 빈칸 · 초안 괄호(r_run 과 같은 표) — 등록 커밋 판에 하나라도 있으면 굽지 않는다
PIT_LOOKAHEAD_N = 200                                        # 명세 parameters_table LOOKAHEAD_T — PIT 입력 독 넣기(결정 달 200 개 · 달이 모자라면 전부)
COND_LOOKAHEAD_N = 200                                       # 조건(L · S) 선견 점검 무작위 t
PIT_LA_FROM, PIT_LA_TO = "2010-06", "2026-07"                # PIT 선견 점검 결정 달 범위(S-E ~ 마지막 결정)
BOOK_LOOKAHEAD_N = 24                                        # 파생 조각 PIT 선견(θ = 1 책 · 책 G2own · Σ̂_A 합동 TE) 결정 달 수(검토 고침 · 선언)
SMOKE_CAPS = {"nperm": 3, "pit_n": 4, "cond_n": 20}          # 연기 자식의 상한(검토 고침 — 연기 경로로 온 강도 굽기를 막는다)
DSR_N = (6, 85, 963)                                         # DSR 보고의 N(H_V m · V 팔 약 85 · 누적 약 963 — 명세 multiplicity.cumulative_N)
AUDIT_SRC_SHA = {"u_core.py": "00ff313b4b770cfa8357033b2312650d9d1a3efa433a6efb542ef2e92f42debd",   # 복사 짝맞춤 원본(배치 U 작업 사본 · 저장소에 없다)
                 "u_tests.py": "475cf74d02f0c9608634ddab9ea8374e3593478f032cd11583909b15b763fdbe"}  #   — v_audit 이 이 파일로 짝맞춤(등록 §6 · --backup 이 사적 폴더로)
F0_DECISION_KEYS = ("clusters", "use_sp", "prof", "gcommon", "liq_emergency", "gegd_pass", "gegd_label", "anchor_ok", "anchor_resolution",
                    "osap", "strand_status")
ANCHOR_RESOLUTIONS = ("pass", "repaired")                   # 🔧 검토 고침: accepted_failed 없음(명세 «실패면 굽지 않고 고친다») · repaired = V 소유 앵커 표를 고친 뒤 다시 잰 관문 참
SMOKE_DEFAULT_DEC = {"use_sp": True, "prof": "op", "gcommon": False, "liq_emergency": False, "anchor_ok": None, "anchor_resolution": "smoke",
                     "osap": False}
# 등록 상수 — 얼린 코드의 값과 같아야 굽는다(실행 중 덮어쓰기 · 연기 덮어쓰기 방지 · 명세 parameters_table · tests · multiplicity)
REGISTERED = {
    "C.RHO": 0.0025, "C.PAIRS_MIN": 120, "C.PAIRS_MIN_BSPRD": 240, "C.NW_SLOPE": 6, "C.NW_SLOPE_BSPRD": 12, "C.WLS_N": 60, "C.WLS_MIN": 36,
    "C.Y_LAG": 2, "C.RHAT_N": 120, "C.RHAT_MIN": 60, "C.Z_MIN": 60, "C.DEAD": 0.5, "C.BAND_END": 2.0, "C.R2_MIN_CLUSTERS": 2,
    "C.SINGLE_CLUSTER_SCALE": 0.5, "C.THETA0": 0.75, "C.DTHETA": 0.25, "C.THETA0_LIQ": 0.5, "C.DTHETA_LIQ": 0.3, "C.THETA0_LIQ_EMERG": 0.4,
    "C.DTHETA_LIQ_EMERG": 0.2, "C.DTHETA_STEP_MAX": 0.1, "C.BETA_BAND": 0.03, "C.BETA_BAND_ITERS": 20, "C.ISSUER_ACTIVE_CAP": 0.05,
    "C.SECTOR_BAND": 0.1, "C.SECTOR_BAND_LBS": 0.05, "C.SECTOR_BAND_SN": 0.03, "C.NDX_ONLY_MAX": 0.1, "C.FILL": 0.5, "C.FILL_LIQ": 1.0,
    "C.BAND_FRAC": 0.1, "C.BUFFER": 1.5, "C.A_B_FRAC": 0.25, "C.A_BOX_FRAC": 0.5, "C.A_FLOOR_FRAC": 0.5, "C.A_TRADE_MAX": 0.2,
    "C.NET_ISSUER_CAP": 0.1, "C.NET_TE_MAX": 0.05, "C.SIG_N": 60, "C.SIG_MIN": 36, "C.G_COMMON_MAX": 0.3, "C.LIQ_TURN_EMERGENCY": 9.0,
    "C.SEED": 20260925, "C.NPERM": 1000, "C.LOOKAHEAD_T": 200, "C.CLUSTER_RHO": 0.5, "C.IBL_ONEWAY_MAX": 1.0 / 3.0, "C.GAMMA_A": 2.75,
    "C.ATTN_FRIDAY_P": 0.082,
    "C.SLEEVE": 0.1, "C.S_COST": 0.001, "C.S_COST_ROBUST": 0.002, "C.LIQ_SIG_N": 21,
    "C.COST_ERAS": (("1975-04", 0.005), ("2000-12", 0.002), ("9999-12", 0.001)), "C.TURN_MAX": 10.0,
    "VT.SEED": 20260925, "VT.NPERM": 1000, "VT.NPERM_MIN": 1000, "VT.NW_LAG": 6, "VT.NW_LAG_REPORT": 12, "VT.HOLM_ALPHA": 0.05,
    "VT.H_V": ("V01", "V02", "V03", "V06", "V07", "V-A"), "VT.HOLM_Z": (2.394, 2.326, 2.241, 2.128, 1.96, 1.645), "VT.L_END": "2026-07",
    "VT.L_C": ("2020-02", "2026-07"), "VT.S_WIN": ("2016-09", "2026-08"), "VT.S_OVERLAP": ("2016-09", "2026-07"),
    "VT.SYNC_EXCL": (("1932-07", "1933-07"), ("2008-10", "2009-08"), ("2020-02", "2020-08")), "VT.UNIVERSE_BREAKS": ("1963-07", "1973-01"),
    "VT.SIGMA_L_WIN": ("1927-01", "2026-07"), "VT.ZZ_HD": 0.1, "VT.ZZ_HU": 0.1, "VT.ZZ_REB_TD": 63, "VT.TIE": 5e-05, "VT.G6A_MIN": 0.55,
    "VT.TURN_MAX": 10.0, "VT.REB_MISS_MIN": 3, "VT.REB_MISS_MONTHS": 3, "VT.RANK_MIN": 0.9, "VT.FID_RHO": 0.6, "VT.RHO_MIN_OVERLAP": 36,
    "VT.BY_Q": 0.1, "VT.CUM_N": (878, 85), "VT.ADOPT_WEB": ("V01", "V03", "V06", "V07"), "VT.FORWARD_ONLY": ("V08",),
    "VT.FF": {"FF1_months": 24, "FF1_t": -1.0, "FF2_months": 36, "FF2_t": 1.0, "late_window": 36, "late_max": 3, "publish_months": 60,
              "events_min": {"crash_legs": 3, "rebounds": 3, "crash_m": 4, "surge_m": 4, "down": 10}},
    "VK.LAST_DECISION": "2026-07", "VK.S_ARM_FROM": "2014-05", "VK.S_EST_FROM": "2010-01", "VK.L_AXIS": ("1926-07", "2026-08"),
    "VK.CARD_IDS": ("V01", "V02", "V03", "V04", "V05", "V06", "V07", "V08"), "VK.WEB_CARDS": ("V01", "V02", "V03", "V06", "V07"),
    "VK.F0_COVER_MIN": 0.85, "VK.F0_MONTH_SHARE": 0.95,
    "VD.CRSP_WANT": "202608", "VD.FIZ": "2024-12", "VD.SEED": 20260925, "VD.LOOKAHEAD_N": 200, "VD.MIN_FIRMS": 20, "VD.Z_MIN": 60,
    "VD.Z_ROLL": 240, "VD.Z_CLIP": 2.0, "VD.LATE_TOL": 1, "VD.S_WIN": ("2016-09", "2026-08"), "VD.SE_FROM": "2010-01",
    "VA.MEMBERS5": ("V01", "V02", "V03", "V06", "V07"), "VA.MEMBERS7": ("V01", "V02", "V03", "V06", "V07", "V04", "V05"),
    "VA.ARMS": ("FULL", "C0", "C-A", "C-W", "C-β", "C-R2S", "C-R2off", "C-NoShrink", "C-7", "C-CAP80"), "VA.L_ALLOC_FROM": "1963-07", "VA.LIQ": "V03",
    "VC.S_FROM": "2006-03",
    "R.PIT_LOOKAHEAD_N": 200, "R.COND_LOOKAHEAD_N": 200, "R.DSR_N": (6, 85, 963), "R.BOOK_LOOKAHEAD_N": 24,
    "R.SMOKE_CAPS": {"nperm": 3, "pit_n": 4, "cond_n": 20},
}


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록은 모두 저장소 밖(캐시 out/ · v_data.cache_guard 가 저장소 안 캐시를 거부한다)
# ══════════════════════════════════════════════════════════════════════════
GIT_MARK_NAME = "vbatch_started"                             # 두 번째 시작 표식 — 저장소 git 공용 폴더(.git · 커밋되지 않는다)
START_TAG = "vbatch-started"                                 # 세 번째 시작 표식 — origin 태그(등록 커밋) · 계산 전에 민다
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}           # 연기 시험만 임시 폴더로 돌린다(진짜 캐시 · .git · origin 에 아무것도 남기지 않는다)


def _git(*a, root=None):
    return subprocess.run(["git", "-C", root or ROOT] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")


def _git_mark_path():
    if _OVR["gitmark"]:
        return _OVR["gitmark"]
    r = _git("rev-parse", "--git-common-dir")
    g = r.stdout.strip()
    if r.returncode != 0 or not g:
        raise SystemExit("🚨 git 공용 폴더를 찾지 못했다.")
    if not os.path.isabs(g):
        g = os.path.join(ROOT, g)
    return os.path.join(os.path.abspath(g), GIT_MARK_NAME)


def out_dir():
    d = _OVR["out"] or os.path.join(VD.cache_guard(), "out")
    os.makedirs(d, exist_ok=True)
    return d


def paths(d=None):
    d = d or out_dir()
    j = lambda n: os.path.join(d, n)
    return {"dir": d, "out": j("_vbatch.json"), "mark": j("_vbatch.started"), "runlog": j("_vbatch.run.json"), "public": j("_vbatch.public.json"),
            "child": j("_vbatch.child.json"), "cmp": j("_vbatch.cmp.json"), "gitmark": _git_mark_path()}


def _inside_repo(p):
    a, r = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(ROOT))
    return a == r or a.startswith(r + os.sep)


def _existing_outputs(P):
    """산출 쪽 파일(표식 제외) — 있으면 한 번 굽기가 이미 쓰였다(`_vbatch*.json` 전부 · 잘린 파일도 «쓰였다»)."""
    have = [P["out"], P["runlog"], P["public"], P["child"], P["cmp"]]
    if os.path.isdir(P["dir"]):
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith("_vbatch") and f.endswith(".json")]
    return sorted({p for p in have if os.path.exists(p)})


def _sha_lf(b):
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def _bytes(p):
    return pathlib.Path(p).read_bytes()


def _read_text(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def _write_text(p, txt):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


def _read_json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def peak_mb():
    """최대 작업 메모리(MB · Windows) — 복사: u_data.peak_mb(값이 아니다)."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return round(pmc.PeakWorkingSetSize / 2 ** 20)
    except Exception:                                        # noqa: BLE001
        return None


# ══════════════════════════════════════════════════════════════════════════
#  경계 · 판
# ══════════════════════════════════════════════════════════════════════════
def site_guard():
    """사이트 경계 — v_guard.site_guard(배치 V · 표준 라이브러리만) + t_guard.site_guard(배치 T · 같은 저장소)."""
    import t_guard as TG
    g, gt = VG.site_guard(ROOT), TG.site_guard(ROOT)
    return {"ok": bool(g["ok"] and gt["ok"]), "bad": list(g["bad"]) + ["[T] " + b for b in gt["bad"]],
            "n_files": g.get("n_files"), "n_scanned": g.get("n_scanned")}


def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def _mods():
    import v_core as C
    import v_tests as VT
    import v_cards as VK
    import v_alloc as VA
    import v_cond as VC
    return {"C": C, "VT": VT, "VK": VK, "VD": VD, "VA": VA, "VC": VC, "R": sys.modules[__name__]}


def _norm(x):
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            x = x.tolist()
    except Exception:                                        # noqa: BLE001
        pass
    if isinstance(x, (list, tuple)):
        return tuple(_norm(v) for v in x)
    if isinstance(x, dict):
        return {k: _norm(v) for k, v in x.items()}
    if isinstance(x, float):
        return round(x, 15)
    return x


def registered_constants_ok():
    M = _mods()
    bad = []
    for k, want in REGISTERED.items():
        mod, attr = k.split(".", 1)
        have = getattr(M[mod], attr, "<없음>")
        if _norm(have) != _norm(want):
            bad.append("%s = %r (등록 %r)" % (k, have, want))
    VT = M["VT"]
    same = lambda a, b: os.path.normcase(os.path.abspath(a or "")) == os.path.normcase(os.path.abspath(b or ""))
    for nm in ("l_card_eval", "l_alloc_eval", "beta_adj_alpha", "hv_family", "adoption_marks", "gates_w", "s_tests"):
        fn = getattr(VT, nm, None)
        if getattr(fn, "__qualname__", "") != nm or not same(getattr(getattr(fn, "__code__", None), "co_filename", ""), VT.__file__):
            bad.append("v_tests.%s 이 덮어쓰였다" % nm)
    for k in ("VBATCH_SMOKE", "VBATCH_SMOKE_NPERM", "VBATCH_F0_FILE"):
        if os.environ.get(k):
            bad.append("연기 전용 환경 변수 %s 가 켜져 있다" % k)
    return bad


def placeholder_counts(text):
    """등록 문서의 빈칸 — (⟨TBD 수, 초안 괄호 U+3014 수). 둘 다 0 이어야 굽는다."""
    return text.count(PLACEHOLDER), text.count(DRAFT_MARK)


def name_check():
    """등록 문서 이름 — 하나뿐 · PREREG-YYYY-MM-DD-VBATCH.md."""
    bad = []
    if _N_PREREG != 1:
        bad.append("build/PREREG-*-VBATCH.md 가 %d 개" % _N_PREREG)
    elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-VBATCH\.md", PREREG):
        bad.append("이름 꼴: %s" % PREREG)
    return bad


def check_cache_identity():
    try:
        man = VD.read_json(VD.MANIFEST)
        want = (man.get("cache_identity") or {}).get("sha256")
    except Exception as e:                                   # noqa: BLE001
        return False, "명세를 읽지 못했다(%s)" % type(e).__name__
    p = os.path.join(VD.cache_guard(), "meta", "cache_id.txt")
    have = VD.sha256_file(p) if os.path.exists(p) else None
    if not want or not have:
        return False, "캐시 표지가 없다(명세 %s · 캐시 %s — --init-cache-id 뒤 v_data.py --manifest)" % (bool(want), bool(have))
    return have == want, ("캐시 표지 = 명세" if have == want else "캐시 표지가 명세와 다르다 — 등록한 캐시 뿌리에서만 굽는다")


def init_cache_identity():
    p = os.path.join(VD.cache_guard(), "meta", "cache_id.txt")
    if os.path.exists(p):
        return {"created": False, "sha256_16": VD.sha256_file(p)[:16]}
    _write_text(p, "vbatch_cache %s %s\n" % (secrets.token_hex(32), time.strftime("%Y-%m-%dT%H:%M:%S")))
    return {"created": True, "sha256_16": VD.sha256_file(p)[:16], "next": "python -X utf8 build/v_data.py --manifest --with-anchors"}


def check_cache_pins(full=True):
    """캐시 핀 = 명세 — V-D1(파일마다 sha · 묶음 digest) · companyfacts(묶음 digest · full 이면 파일마다 내용 sha) · ^GSPC · 넓힌 원장 · 문헌 열기 기록.
    돌려주는 것 (ok, 문제 목록 — 이름만)."""
    import gzip
    bad = []
    try:
        man = VD.read_json(VD.MANIFEST)
    except Exception as e:                                   # noqa: BLE001
        return False, ["명세 없음(%s)" % type(e).__name__]
    cache = VD.cache_guard()
    # V-D1
    vi = os.path.join(cache, "raw", "vd1", "_index.json")
    if not os.path.exists(vi):
        bad.append("V-D1 목록 없음")
    else:
        idx = VD.read_json(vi)["files"]
        lines = "".join("%s\t%s\n" % (k, v["sha256"]) for k, v in sorted(idx.items()))
        if VD.sha256_bytes(lines.encode("utf-8")) != (man.get("vd1") or {}).get("digest"):
            bad.append("V-D1 묶음 digest 가 명세와 다르다")
        if full:
            import v_px_split as VX
            nb = [k for k, v in idx.items() if not os.path.exists(VX.vd1_path(k)) or VD.sha256_file(VX.vd1_path(k)) != v["sha256"]]
            if nb:
                bad.append("V-D1 파일 %d 개 sha 다름(%s …)" % (len(nb), ", ".join(sorted(nb)[:3])))
    # companyfacts
    ci = os.path.join(cache, "raw", "companyfacts", "_pin_index.json")
    if not os.path.exists(ci):
        bad.append("companyfacts 핀 목록 없음")
    else:
        idx = VD.read_json(ci)["files"]
        lines = "".join("%s\t%s\n" % (k, v.get("sha256")) for k, v in sorted(idx.items()))
        if VD.sha256_bytes(lines.encode("utf-8")) != (man.get("companyfacts_pin") or {}).get("digest"):
            bad.append("companyfacts 묶음 digest 가 명세와 다르다")
        if full:
            nb = []
            for k, v in idx.items():
                if not v.get("sha256"):
                    continue
                fp = os.path.join(cache, "raw", "companyfacts", k + ".json.gz")
                if not os.path.exists(fp):
                    nb.append(k)
                    continue
                with open(fp, "rb") as f:
                    if VD.sha256_bytes(gzip.decompress(f.read())) != v["sha256"]:
                        nb.append(k)
            if nb:
                bad.append("companyfacts 파일 %d 개 내용 sha 다름" % len(nb))
    for key, rel in (("gspc_pin", ("raw", "yf", "_GSPC.csv")), ("wide_ledger", ("derived", "wide_ledger.json.gz"))):
        want = (man.get(key) or {}).get("sha256")
        fp = os.path.join(cache, *rel)
        if not want:
            bad.append("명세에 %s 없음(v_data.py --manifest 를 다시)" % key)
        elif not os.path.exists(fp) or VD.sha256_file(fp) != want:
            bad.append("%s sha 가 명세와 다르다" % key)
    lp = os.path.join(VD.DATA, "_vb_lit_open.json")
    if not os.path.exists(lp) or VD.sha256_file_lf(lp) != (man.get("lit_open") or {}).get("sha256"):
        bad.append("문헌 열기 기록(data/_vb_lit_open.json) sha 가 명세와 다르다")
    return not bad, bad


def code_shas(paths_=None):
    """F0 · 굽기가 쓰는 코드의 LF sha(앞 16자) — F0 문서가 «얼린 코드로 만들어졌는가» 를 판 점검이 본다."""
    out = {}
    for p in (paths_ or [x for x in NEW_FROZEN if x.startswith("build/")] + list(REUSED_FROZEN)):
        fp = os.path.join(ROOT, *p.split("/"))
        out[p] = _sha_lf(_bytes(fp))[:16] if os.path.exists(fp) else None
    return out


def f0_check(doc, code_now=None):
    """F0 문서 거르개(순수 · selftest 대상) — 결정 칸이 모두 있고 · 앵커 결정이 있고 · F0 를 만든 코드 = 지금 코드. 돌려주는 것 문제 목록."""
    bad = []
    if not isinstance(doc, dict) or doc.get("kind") != "vbatch_f0":
        return ["F0 문서 꼴이 아니다"]
    dec = doc.get("decisions") or {}
    miss = [k for k in F0_DECISION_KEYS if k not in dec]
    if miss:
        bad.append("F0 결정 칸 없음: %s" % ", ".join(miss))
    if dec.get("anchor_ok") is not True:
        bad.append("시총 앵커 관문이 참이 아니다(anchor_ok = %r) — 명세 «실패면 굽지 않고 고친다»: v_px_split 의 V 소유 앵커 표를 출처 있는 값으로 고치고 --f0 를 다시"
                   % dec.get("anchor_ok"))
    if dec.get("anchor_resolution") not in ANCHOR_RESOLUTIONS:
        bad.append("시총 앵커 결정 칸이 pass · repaired 가 아니다(%r)" % dec.get("anchor_resolution"))
    miss_g = [c for c in ALL_CARDS if c not in (dec.get("gegd_pass") or {}) or c not in (dec.get("gegd_label") or {})]
    if miss_g:
        bad.append("G-EGD 칸이 없는 카드: %s(fail closed — 검토 고침)" % ", ".join(miss_g))
    cl = dec.get("clusters")
    if not (isinstance(cl, dict) and isinstance(cl.get("edges"), list) and isinstance(cl.get("S_edges"), dict) and "rho" not in cl):
        bad.append("군 등록물(clusters · edges · S_edges — ρ 값 없음)이 없다")
    nc = doc.get("noeg_child") or {}
    if nc.get("runtime") is not True or nc.get("open_audit") is not True:
        bad.append("F0 자식 과정의 G-NoEG(실행 · open 감사)가 참이 아니다")
    if dec.get("prof") not in ("op", "roa"):
        bad.append("QLT PROF 결정이 op · roa 가 아니다")
    for k in ("use_sp", "gcommon", "liq_emergency", "osap"):
        if k in dec and not isinstance(dec[k], bool):
            bad.append("%s 가 참/거짓이 아니다" % k)
    if code_now is not None:
        diff = sorted(p for p, s in (doc.get("code_sha") or {}).items() if code_now.get(p) != s)
        if diff or not doc.get("code_sha"):
            bad.append("F0 를 만든 코드가 지금 코드와 다르다(%s …) — 얼린 코드로 --f0 를 다시" % ", ".join(diff[:3]))
    return bad


ALL_CARDS = ("V01", "V02", "V03", "V04", "V05", "V06", "V07", "V08")


def load_f0(path=None):
    p = path or os.path.join(ROOT, *F0_FILE.split("/"))
    return _read_json(p) if os.path.exists(p) else None


# ══════════════════════════════════════════════════════════════════════════
#  시작 표식(순수 규칙 · selftest 가 모든 갈래를 본다)
# ══════════════════════════════════════════════════════════════════════════
def _remote_start_tag():
    r = _git("ls-remote", "--tags", "origin", "refs/tags/" + START_TAG)
    if r.returncode != 0:
        raise SystemExit("🚨 origin 시작 태그를 확인하지 못했다(git ls-remote 실패 · %s) — 모르면 굽지 않는다." % r.stderr.strip()[:120])
    lines = [x.split() for x in r.stdout.splitlines() if x.strip()]
    return lines[0][0] if lines else None


def start_guard(full, rerun, marks, remote_tag):
    """marks = [(경로, 글)] · remote_tag = origin 시작 태그의 커밋 | None — u_run.start_guard 와 같은 갈래."""
    if any(FINISHED in txt for _, txt in marks):
        raise SystemExit("🚨 굽기가 이미 끝났다(시작 표식에 %s 줄) — 산출을 지웠어도 · VBATCH_RERUN 이어도 다시 돌지 않는다(다시 굽기는 새 등록)." % FINISHED)
    if remote_tag is not None and remote_tag != full:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다 — 다시 굽기는 새 등록." % remote_tag[:8])
    if marks and not rerun:
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 VBATCH_RERUN=사유 로 처음부터(이어하기는 없다)."
                         % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 VBATCH_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다 — 다른 사본 · 복원한 캐시로는 다시 돌지 않는다.")
    if rerun and not all(txt.startswith(full) for _, txt in marks):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    if remote_tag is not None and not rerun:
        raise SystemExit("🚨 origin 에 시작 태그(%s)가 있다 — 한 번 굽기가 이미 시작됐다(이 컴퓨터의 산출 전 중단이면 VBATCH_RERUN)." % START_TAG)
    return True


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def frozen_check(env=None):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("VBATCH_COMMIT")
    if not c:
        raise SystemExit("🚨 VBATCH_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --pins · --f0 · --precommit · --smoke 만 된다.")
    nb = name_check()
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_VBATCH_NO_FETCH"):              # (_VBATCH_NO_FETCH 는 selftest 가 넘기는 사전에서만 — 진짜 굽기는 늘 받는다)
        fr = _git("fetch", "--quiet", "origin")
        if fr.returncode != 0:
            raise SystemExit("🚨 git fetch origin 실패 — origin/main 을 새로 보지 못하면 굽지 않는다(%s)." % fr.stderr.strip()[:160])
    r = _git("rev-parse", "--verify", "-q", c + "^{commit}")
    full = r.stdout.strip()
    if r.returncode != 0 or not full:
        raise SystemExit("🚨 커밋 %s 을 찾지 못했다." % c)
    for p in FIRST_ADDED:
        added = _git("log", "--format=%H", "--diff-filter=A", full, "--", p).stdout.split()
        if not added or added[-1] != full:
            raise SystemExit("🚨 %s 는 %s 를 처음 더한 커밋이 아니다." % (full[:8], p))
    if _git("merge-base", "--is-ancestor", full, "origin/main").returncode != 0:
        raise SystemExit("🚨 사전등록 커밋이 origin/main 에 없다 — 먼저 푸시(git fetch 도).")
    txt = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, PREREG)], capture_output=True).stdout.decode("utf-8", "replace")
    n_ph, n_dm = placeholder_counts(txt)
    if n_ph or n_dm:
        raise SystemExit("🚨 등록 커밋의 사전등록 문서에 빈칸 %s⟩ %d · 초안 괄호(U+3014) %d 가 남았다 — F0 표를 채운 판을 등록한다." % (PLACEHOLDER, n_ph, n_dm))
    P = paths()
    if _inside_repo(P["dir"]):
        raise SystemExit("🚨 산출 폴더가 저장소 안이다(D1): %s" % P["dir"])
    outs = _existing_outputs(P)
    if outs:
        raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다(다시 굽기는 새 등록)." % ", ".join(os.path.basename(o) for o in outs))
    if _git("cat-file", "-e", "origin/main:" + RESULT).returncode == 0:
        raise SystemExit("🚨 origin/main 에 결과 문서가 이미 있다 — 다시 굽기는 새 등록.")
    ci, cmsg = check_cache_identity()
    if not ci:
        raise SystemExit("🚨 %s." % cmsg)
    rerun = env.get("VBATCH_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag() if (real or not env.get("_VBATCH_NO_FETCH")) else env.get("_VBATCH_REMOTE_TAG")
    start_guard(full, rerun, marks, remote)
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True)
        if want.returncode != 0:
            raise SystemExit("🚨 %s 가 등록 커밋에 없다." % p)
        if not os.path.exists(fp) or _sha_lf(_bytes(fp)) != _sha_lf(want.stdout):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    if _git("diff", "--quiet", full, "--", *V_LAB_FILES).returncode != 0:
        raise SystemExit("🚨 굽기가 읽는 랩 자료가 등록 커밋의 판과 다르다(%s …) — 등록 커밋을 꺼낸 작업 트리에서 굽는다." % ", ".join(V_LAB_FILES[:3]))
    extra = _git("ls-files", "--others", "--", *V_LAB_FILES).stdout.split()
    if extra:
        raise SystemExit("🚨 랩 자료 폴더에 추적 안 된 파일이 있다(%s …)." % ", ".join(extra[:3]))
    ok, bad = VD.check_pins()
    if not ok:
        raise SystemExit("🚨 자료 고정본이 명세와 다르다: %s" % "; ".join(bad[:5]))
    ok, bad = check_cache_pins(full=True)
    if not ok:
        raise SystemExit("🚨 캐시 핀이 명세와 다르다: %s" % "; ".join(bad[:5]))
    fb = f0_check(load_f0(), code_shas())
    if fb:
        raise SystemExit("🚨 F0 문서: %s" % "; ".join(fb[:4]))
    gp = os.path.join(ROOT, *VFWD_GENESIS.split("/"))
    vb = vfwd_check(_read_json(gp)) if os.path.exists(gp) else ["VFWD 창세 문서 없음"]
    if vb:
        raise SystemExit("🚨 VFWD 창세: %s" % "; ".join(vb[:3]))
    try:
        VD.assert_no_derivatives()
        VD.assert_no_eg_files(list(VD.read_json(VD.MANIFEST).get("lab_files") or {}))
    except SystemExit as e:
        raise SystemExit("🚨 %s" % e)
    v = _versions()
    vb = ["%s %s(등록 %s)" % (k, v.get(k), want) for k, want in VERSIONS.items() if v.get(k) != want]
    if vb:
        raise SystemExit("🚨 라이브러리 판이 다르다: %s" % ", ".join(vb))
    eb = ["%s=%s" % (k, env.get(k)) for k, want in ENV_PINS.items() if env.get(k) != want]
    if eb:
        raise SystemExit("🚨 PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 로 돌려라(지금 %s)." % ", ".join(eb))
    cb = registered_constants_ok()
    if cb:
        raise SystemExit("🚨 등록 상수가 다르다: %s" % "; ".join(cb[:6]))
    g = site_guard()
    if not g["ok"]:
        raise SystemExit("🚨 사이트 경계 실패: %s" % "; ".join(g["bad"][:5]))
    ne = VG.noeg_static()
    if not ne["ok"] or "v_run" not in ne["targets"]:
        raise SystemExit("🚨 G-NoEG 정적 전이 점검 실패: 적중 %s · 경계 %s" % (ne["hits"][:3], ne["separate_violations"][:3]))
    return full


# ══════════════════════════════════════════════════════════════════════════
#  직렬화 · 모듈 셈
# ══════════════════════════════════════════════════════════════════════════
def _clean(o, depth=0):
    """산출 → 올바른 JSON(NaN · inf → None · 계열 {"__series__"} · 표 {"__frame__"} · 기간 · 날짜 → 글자 · 사전 열쇠 → 글자) — 복사: u_run._clean."""
    import numpy as np
    import pandas as pd
    if depth > 60:
        return str(o)
    if o is None or isinstance(o, (str, bool)):
        return o
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, pd.Series):
        return {"__series__": {str(k): _clean(v, depth + 1) for k, v in o.items()}}
    if isinstance(o, pd.DataFrame):
        return {"__frame__": {str(c): {str(k): _clean(v, depth + 1) for k, v in o[c].items()} for c in o.columns}}
    if isinstance(o, np.ndarray):
        return _clean(o.tolist(), depth + 1)
    if isinstance(o, dict):
        return {("|".join(map(str, k)) if isinstance(k, tuple) else str(k)): _clean(v, depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_clean(v, depth + 1) for v in o]
    if isinstance(o, (pd.Period, pd.Timestamp)):
        return str(o)
    return str(o)


def local_modules():
    out = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        f = os.path.abspath(f)
        if os.path.dirname(f) == os.path.abspath(HERE) and f.endswith(".py"):
            out.add("build/" + os.path.basename(f))
    return sorted(out)


def unfrozen_modules(mods=None):
    return [m for m in (mods if mods is not None else local_modules()) if m not in FROZEN]


def data_files_opened():
    """자식 과정 open 감사에서 저장소 data/ 아래 열린 파일(저장소 상대 경로 · 이름만)."""
    base = os.path.normcase(os.path.abspath(VD.DATA)) + os.sep
    out = set()
    for p in VG._OPENED:
        a = os.path.normcase(os.path.abspath(p))
        if a.startswith(base):
            out.add("data/" + os.path.relpath(a, os.path.abspath(VD.DATA)).replace(os.sep, "/"))
    return sorted(out)


def unregistered_data(files):
    """열린 data/ 파일 가운데 V_LAB_FILES(파일 · 폴더) 밖 — 판 점검이 판을 보지 않는 자료."""
    reg = [x.lower() for x in V_LAB_FILES]
    bad = []
    for f in files:
        fl = f.lower()
        if not any(fl == r or fl.startswith(r.rstrip("/") + "/") for r in reg):
            bad.append(f)
    return bad


# ══════════════════════════════════════════════════════════════════════════
#  굽기 본체(자식 과정 · 🚨 수익 통계 — 등록 커밋 뒤 굽기와 눈가린 연기에서만)
# ══════════════════════════════════════════════════════════════════════════
def _decisions(doc):
    """F0 문서 → 굽기 선택(spec over · gcommon · 군 · G-EGD · 앵커)."""
    d = dict(doc.get("decisions") or {})
    return {"use_sp": bool(d.get("use_sp", True)), "prof": d.get("prof") or "op", "gcommon": bool(d.get("gcommon", False)),
            "liq_emergency": bool(d.get("liq_emergency", False)), "clusters": d.get("clusters"),
            "gegd_pass": {k: (v is True) for k, v in (d.get("gegd_pass") or {}).items()}, "anchor_ok": d.get("anchor_ok"),
            "anchor_resolution": d.get("anchor_resolution"), "osap": bool(d.get("osap", False)), "strand_status": d.get("strand_status")}


def run_batch(dec, nperm, pit_la_n=PIT_LOOKAHEAD_N, cond_la_n=COND_LOOKAHEAD_N, twins=True, smoke=False, clock=None, book_la_n=BOOK_LOOKAHEAD_N):
    """명세 차례대로 한 번 — 선견 점검 → 층 · 사건 → S 카드 → L 평가(H_V 다섯 + 배분기) → L 쌍둥이 → S 쌍둥이 → S 평가 → S 배분기 팔 → 위생 →
    H_V Holm · 공동 조건 · 채택 표시 · 부 가족 BY · Stouffer · DSR(보고) → F0 재현 셈. 돌려주는 것 산출 사전(값 포함 — 저장소 밖에만 쓴다)."""
    import numpy as np
    import pandas as pd
    import v_core as C
    import v_cond as VC
    import v_cards as VK
    import v_alloc as VA
    import v_tests as VT
    clock = clock if clock is not None else {}
    tic = lambda k, t0: clock.__setitem__(k, round(time.time() - t0, 1))
    over = {"use_sp": dec["use_sp"], "prof": dec["prof"], "liq_emergency": dec["liq_emergency"]}
    gcom = dec["gcommon"]
    out = {"vbatch_full_out": True, "decisions": dec, "stopped": None, "smoke": bool(smoke), "nperm": nperm,
           "lookahead_n": {"pit": pit_la_n, "cond": cond_la_n}}
    # ── 0 선견 점검(명세 guards.lookahead · 하나라도 틀리면 멈춘다) ───────────────
    t0 = time.time()
    Lr = VD.Layer.real()
    lc = VC.run_lookahead(n=cond_la_n)
    ms = [m for m in Lr.pit.months if PIT_LA_FROM <= m <= PIT_LA_TO]
    lp = VD.pit_lookahead(lambda X, m: VD._flat_inputs(X, m), Lr, ms, lambda X, m, rg: X.poison_after(m, rg), n=min(pit_la_n, len(ms)))
    june = [m for m in ms if m[5:7] == "06"]

    def comp_june(X, m):
        U = X.pit
        sm = U.spy_month()
        o = {}
        for r in U.members(m):
            ni = U.ni_v08(r, m) or {}
            sw = U.beta_sw(r["k"], m, _spy_m=sm)
            o[r["t"]] = (np.nan if ni.get("ni") is None else ni["ni"], np.nan if sw is None else sw)
        return o
    lj = VD.pit_lookahead(comp_june, Lr, june, lambda X, m, rg: X.poison_after(m, rg), n=(len(june) if not smoke else min(2, len(june))))
    # 파생 조각(🔧 검토 고침 · 등록 전 — 명세 guards.lookahead 를 조건 · 원 입력 너머로): (가) G1rel L(대리 y · French t−2 · 늦춤 2)
    #   (나) LIQ 상태 의존 비용(SPY 일간 · 결정 달 말까지) (다) PIT 독 넣기로 θ = 1 책 다섯 · 책 G2own(V01 · V03) · Σ̂_A 합동 TE(같은 비중)
    #   — S 쪽 G1rel(책 y · 늦춤 0)은 S 카드 뒤에 잰다(아래 2b).
    Yl = pd.DataFrame(Lr.l_proxy())[list(VA.MEMBERS5)]
    lg1 = VD.lookahead_check(lambda Y: VC.g1rel(Y, lag=VD.AVAIL["french:lag2"][0]), {"Y": (Yl, "french:lag2")}, n=cond_la_n, mode="L")
    spy_d = VD.lab_spy_daily()

    def liq_fn(spy):
        sp_ = pd.Series(spy, dtype=float).dropna()
        r = C.liq_cost_rate(sp_.to_numpy(float), [d.strftime("%Y-%m-%d") for d in sp_.index])
        return pd.Series({pd.Period(k, "M"): v for k, v in r.items()}, dtype=float).sort_index()
    lliq = VD.lookahead_check(liq_fn, {"spy": (spy_d, "lab:spy_d")}, n=cond_la_n, mode="S")

    def comp_book(X, m):
        SLx = VK.SLayer(X, months=[m])
        o, bks = {}, {}
        for sid in VA.MEMBERS5:
            b, _ = SLx.books(VK.spec_of(sid, **over), theta=1.0)
            if m in b:
                bks[sid] = b[m]
                o["book:" + sid] = tuple(v for _, v in sorted(b[m].items()))
        for sid in ("V01", "V03"):
            if sid in bks:
                g = SLx.g2own_x({m: bks[sid]})
                o["g2own:" + sid] = float(g.iloc[0]) if len(g) else None
        if len(bks) == len(VA.MEMBERS5):
            te, _n = VA.joint_te(SLx, m, [bks[x] for x in VA.MEMBERS5], np.full(len(VA.MEMBERS5), 1.0 / len(VA.MEMBERS5)))
            o["te"] = te
        return o
    lbk = VD.pit_lookahead(comp_book, Lr, ms, lambda X, m, rg: X.poison_after(m, rg), n=min(book_la_n, len(ms)))
    out["lookahead"] = {"cond": {k: {"ok": bool(v["ok"]), "n": v["n"], "n_bad": v["n_bad"]} for k, v in lc.items()},
                        "pit": {k: lp.get(k) for k in ("ok", "n", "n_bad", "seed")}, "pit_june": {k: lj.get(k) for k in ("ok", "n", "n_bad", "seed")},
                        "derived": {"g1rel_L": {k: lg1.get(k) for k in ("ok", "n", "n_bad")}, "liq_cost": {k: lliq.get(k) for k in ("ok", "n", "n_bad")},
                                    "books_g2own_te": {k: lbk.get(k) for k in ("ok", "n", "n_bad", "seed")}}}
    out["lookahead"]["ok"] = bool(all(v["ok"] for v in lc.values()) and lp.get("ok") and lj.get("ok") and lg1.get("ok") and lliq.get("ok")
                                  and lbk.get("ok"))
    tic("lookahead", t0)
    if not out["lookahead"]["ok"]:
        out["stopped"] = "선견 점검 실패 — 굽기 멈춤(등록 §3 · 결과 문서는 이 한 줄)"
        return out
    # ── 1 층 · 군 · 사건 ─────────────────────────────────────────────────────
    t0 = time.time()
    zL = Lr.cond_L()
    cl_now = VK.l_clusters(zL)
    cl = dec.get("clusters") or cl_now                                              # 등록 F0 군 등록물(edges · S_edges) — 굽기는 이것을 쓴다
    out["clusters"] = {"registered": cl, "recomputed_same_L": cl_now["edges"] == cl.get("edges")}
    LL = VK.LLayer.real(Lr, clusters=cl)
    f3 = VD.ff3("m")
    regsL = VT.dm_regressors(f3["Mkt"], f3["RF"])
    evL = VT.events_L(f3["Mkt"], VT.sigma_L(f3["Mkt"]), VT.gspc_daily())
    evS = VT.events_S()
    SL = VK.SLayer(Lr, clusters=cl)
    rfm = VD.lab_rf_monthly()
    spy_tr_m = pd.Series({VD.mshift(m, 1): SL.spy_hold(m) for m in SL.months if VD.mshift(m, 1) in Lr.pit.me_idx}, dtype=float)
    spy_tr_m.index = pd.PeriodIndex(spy_tr_m.index, freq="M")
    regsS = VT.dm_regressors(spy_tr_m, rfm)
    tic("setup", t0)
    # ── 2 S 카드 V01~V08(F · S0 · W) ─────────────────────────────────────────
    t0 = time.time()
    comps = {}
    for sid in VK.CARD_IDS:
        sp = VK.spec_of(sid, **over)
        Lw = LL.web_slopes(sp) if sp["web"] else None
        comps[sid] = VK.s_card_arms(SL, sp, Lw, gcommon=gcom, keep_books=True)
    taus = {sid: comps[sid]["tau_w"].get("F") for sid in comps}
    LL.taus = taus
    # 2b 파생 선견(S) — G1rel S(책 y · 늦춤 0 · 검토 고침) · 군 등록물 S 쪽 재현(책 G2own ρ — 보고)
    YS = pd.DataFrame({s_: comps[s_]["y_S"] for s_ in VA.MEMBERS5})
    YS.index = pd.PeriodIndex(YS.index, freq="M")
    lg1s = VD.lookahead_check(lambda Y: VC.g1rel(Y, lag=0), {"Y": (YS, "v:book_y")}, n=cond_la_n, mode="S")
    out["lookahead"]["derived"]["g1rel_S"] = {k: lg1s.get(k) for k in ("ok", "n", "n_bad")}
    out["lookahead"]["ok"] = bool(out["lookahead"]["ok"] and lg1s.get("ok"))
    out["clusters"]["recomputed_same_S"] = {sid: VK.s_g2own_edges(VK.s_g2own_rho(SL, comps[sid]["books"]["F"], sid)) == ((cl.get("S_edges") or {}).get(sid) or [])
                                            for sid in ("V01", "V03")}
    tic("S_cards", t0)
    if not out["lookahead"]["ok"]:
        out["stopped"] = "선견 점검 실패(파생 S) — 굽기 멈춤(등록 §3 · 결과 문서는 이 한 줄)"
        return out
    # ── 3 L 평가 — H_V 다섯(W − S0) + 배분기(C-A − C0) ─────────────────────────
    t0 = time.time()
    members = tuple(s for s in VA.MEMBERS5 if dec["gegd_pass"].get(s, False) is True)            # G-EGD 칸이 없으면 뺀다(fail closed · 검토 고침)
    Lres = {}
    for sid in VK.WEB_CARDS:
        Lres[sid] = VT.l_card_eval(LL, sid, evL, regsL, tau=taus.get(sid), nperm=nperm, over=over)
    th_s = {s: pd.Series(VK.spec_of(s, **over)["theta0"], index=LL.axis) for s in members}
    th_w = {s: LL.theta(VK.spec_of(s, **over), LL.web(VK.spec_of(s, **over))["v"]) for s in members}
    Lres["V-A"] = VT.l_alloc_eval(LL, evL, regsL, th_s, th_w, taus=taus, nperm=nperm, members=members) if len(members) >= 3 else None
    tic("L_eval", t0)
    # ── 4 L 쌍둥이(보고 · 위약 없음) ──────────────────────────────────────────
    t0 = time.time()
    Ltw = {}
    if twins:
        for t, d in VK.TWINS.items():
            sp = VK.spec_of(d["card"], t, **over)
            if sp["status"] != "built" or "L" not in sp["layers"]:
                continue
            Ltw[t] = VT.l_card_eval(LL, d["card"], evL, regsL, tau=taus.get(d["card"]), nperm=0, twin=t, over=over)
    tic("L_twins", t0)
    # ── 4b French 판 민감도(보고만 · 명세 tests.L_layer.windows «French 빈티지(2024-12 고정 사본)» · 검토 고침) — 같은 규칙 · 같은 군 · 위약 없음 ·
    #   같은 부호인가(베타 조정 α̂ 의 부호)만 게시 칸에 · 값은 저장소 밖
    t0 = time.time()
    Lvin = {}
    try:
        LV = VK.LLayer.vintage(VD.FIZ, clusters=cl)
        LV.taus = taus
        f3v = VD.ff3("m", vintage=VD.FIZ)
        regsV = VT.dm_regressors(f3v["Mkt"], f3v["RF"])
        for sid in VK.WEB_CARDS:
            rv = VT.l_card_eval(LV, sid, evL, regsV, tau=taus.get(sid), nperm=0, over=over)
            a0, a1 = (Lres.get(sid) or {}).get("alpha", {}).get("a"), rv["alpha"].get("a")
            Lvin[sid] = {"window": rv["window"], "alpha": rv["alpha"], "same_sign": bool(a0 is not None and a1 is not None and (a0 > 0) == (a1 > 0))}
        Lvin["_note"] = "French %s 판(CRSP 202412) · 보고만 · 창은 그 판의 끝까지" % VD.FIZ
    except Exception as e:                                   # noqa: BLE001
        Lvin = {"_error": "%s: %s" % (type(e).__name__, str(e)[:120])}
    tic("L_vintage", t0)
    # ── 5 S 평가(카드 팔마다 · 구현성 · FID) ──────────────────────────────────
    t0 = time.time()
    Sres, Sarms, Sdelta = {}, {}, {}
    win = lambda P: P.loc[VT.in_win(P.index, *VT.S_WIN)]
    for sid in VK.CARD_IDS:
        r = comps[sid]
        yL = LL.P.get(sid)
        Sarms[sid] = {}
        for arm, P in r["paths"].items():
            if P is None or not len(P):
                continue
            turn = C.turnover_annual(win(P)["traded"].tolist())
            Sarms[sid][arm] = VT.s_tests(P, turn, r["y_S"], yL, sid, rf=rfm, ev=evS)
        main = "W" if "W" in r["paths"] else "S0"
        Sres[sid] = Sarms[sid].get(main)
        if "W" in r["paths"] and "S0" in r["paths"]:
            Pw, P0 = win(r["paths"]["W"]), win(r["paths"]["S0"])
            D = (VT.s_x(Pw) - VT.s_x(P0)).dropna()                                 # 주 행 T+1(검토 고침)
            Sdelta[sid] = {"h1": VT.h1(D), "alpha_beta_adj": VT.beta_adj_alpha(D, regsS)}
    tic("S_eval", t0)
    # ── 6 S 쌍둥이(보고) ───────────────────────────────────────────────────────
    t0 = time.time()
    Stw = {}
    if twins:
        for t, d in VK.TWINS.items():
            sp = VK.spec_of(d["card"], t, **over)
            if sp["status"] != "built" or "S" not in sp["layers"]:
                continue
            Lw = LL.web_slopes(sp) if (sp["web"] or sp.get("web_add")) else None
            rr = VK.s_card_arms(SL, sp, Lw, gcommon=gcom, keep_books=False)
            main = "W" if "W" in rr["paths"] else "S0"
            P = rr["paths"][main]
            turn = C.turnover_annual(win(P)["traded"].tolist()) if P is not None and len(P) else None
            Stw[t] = {"arm": main, "S": (VT.s_tests(P, turn, rf=rfm, ev=evS) if P is not None and len(P) else None), "diag": rr["diag"],
                      "tau_w": rr["tau_w"]}
    tic("S_twins", t0)
    # ── 7 S 배분기 팔(10 · 구성원 = G-EGD 를 넘은 다섯 가운데) ─────────────────
    t0 = time.time()
    Ares, ASt = {}, {}
    if len(members) >= 3:
        fmL = VA.l_fm(LL, members)
        fmL_ns = VA.l_fm(LL, members, shrink=False)                                # C-NoShrink — 배분기 FM 도 축소를 뺀다(검토 고침)
        m7 = members + tuple(s for s in ("V04", "V05"))
        for arm, (on, web, wopt, beta_net, mem, cap80) in VA.ARM_DEF.items():
            mem = m7 if mem == VA.MEMBERS7 else members
            cs = comps
            if wopt or cap80:
                cs = dict(comps)
                for sid in mem:
                    if sid not in VA.MEMBERS5:
                        continue
                    sp = VK.spec_of(sid, ("T-%s-CAP80" % VK.CARDS[sid]["key"]) if cap80 else None, **over)
                    Lw = LL.web_slopes(sp, shrink=wopt.get("shrink", True))
                    cs[sid] = VK.s_card_arms(SL, sp, Lw, web_opt=wopt, gcommon=gcom, keep_books=True, paths=False)
            A = VA.s_allocator(SL, cs, mem, on=on, fm_L=(fmL_ns if wopt.get("shrink") is False else fmL), beta_net=beta_net, cap80=cap80,
                               arm_key=("W" if web else "S0"))
            Ares[arm] = {"path": A["path"], "w": A["w"]}
            if A["path"] is not None and len(A["path"]):
                turn = C.turnover_annual(win(A["path"])["traded"].tolist())
                ASt[arm] = VT.s_tests(A["path"], turn, rf=rfm, ev=evS)
        dA = None
        if Ares.get("C-A", {}).get("path") is not None and Ares.get("C0", {}).get("path") is not None:
            pa, p0 = win(Ares["C-A"]["path"]), win(Ares["C0"]["path"])
            dA = (VT.s_x(pa) - VT.s_x(p0)).dropna()                                  # 주 행 T+1(검토 고침)
        ASd = {"h1": VT.h1(dA), "alpha_beta_adj": VT.beta_adj_alpha(dA, regsS)} if dA is not None else None
    else:
        ASd = None
    tic("S_alloc", t0)
    # ── 8 위생(w_B 월수익 대 SPY — 수익 통계라 F0 가 아니라 여기서 · 보고 · 명세 coverage_gates_F0) ─────────
    t0 = time.time()
    hyg_ms = [m for m in SL.months if VT.S_WIN[0] <= VD.mshift(m, 1) <= VT.S_WIN[1]]
    hyg = Lr.pit.hygiene(hyg_ms)
    hyg["gate"] = bool(hyg.get("rho") is not None and hyg["rho"] >= 0.98)
    tic("hygiene", t0)
    # ── 9 H_V · 공동 조건 · 관문 · 채택 표시 · 부 가족 · Stouffer · DSR ─────────
    t0 = time.time()
    hv_stats = {k: (Lres[k]["alpha"] if Lres.get(k) else {"n": 0, "a": None, "t": None, "p": None}) for k in VT.H_V}
    hv = VT.hv_family(hv_stats)
    joint = {k: (bool(Lres[k]["joint"]) if Lres.get(k) else False) for k in VT.H_V}
    gL = {k: Lres[k]["gates"] for k in VK.WEB_CARDS if Lres.get(k)}
    fidg = {k: bool(((Sres.get(k) or {}).get("fid") or {}).get("gate")) for k in VK.WEB_CARDS}
    g5e_alloc = (ASt.get("FULL") or {}).get("g5e")
    anchor_ok = bool(dec.get("anchor_ok")) if dec.get("anchor_ok") is not None else False
    am = VT.adoption_marks({k: hv["holm"]["reject"][k] for k in VT.H_V}, joint, gL, Sres, fidg,
                           {k: dec["gegd_pass"].get(k, False) is True for k in VK.WEB_CARDS}, anchor_ok,
                           alloc={"gates_L": (Lres["V-A"] or {}).get("gates") if Lres.get("V-A") else None, "g5e": g5e_alloc})
    static_L = {k: Lres[k]["static_h1"] for k in VK.WEB_CARDS if Lres.get(k)}
    s_layer = {("X:" + k): (v or {}).get("h1_10") for k, v in Sres.items() if k not in VT.FORWARD_ONLY}     # V08 은 BY 밖(등록 §1.8 · 검토 고침)
    s_layer.update({("D:" + k): v["h1"] for k, v in Sdelta.items()})
    if ASt.get("FULL"):
        s_layer["X:VFA"] = ASt["FULL"]["h1_10"]
    if ASd:
        s_layer["D:V-A"] = ASd["h1"]
    sec = VT.secondary_family(static_L, s_layer)
    stf = VT.stouffer({k: hv_stats[k].get("t") for k in VT.H_V}, {k: (Lres[k]["delta"] if Lres.get(k) else None) for k in VT.H_V})
    dsr = {k: {str(n): VT.dsr(Lres[k]["delta"], n).get("dsr") for n in DSR_N} for k in VT.H_V if Lres.get(k)}
    tic("tests", t0)
    # ── 10 F0 재현 셈(비중만 · 등록 F0 와 같은가 — 보고) ───────────────────────
    mS = [m for m in SL.months if m >= VK.S_ARM_FROM]
    sc = []
    for m in mS:
        X = SL.cross(m)
        A = []
        for sid in members:
            b = (comps[sid].get("books") or {}).get("F", {}).get(m)
            if b is None:
                break
            A.append(X.arr(b) - X.wB)
        if len(A) == len(members) and A:
            v = C.common_share(np.vstack(A))
            if v is not None:
                sc.append(v)
    out["f0_repro"] = {"g_common_median": (float(np.median(sc)) if sc else None)}
    # ── 산출 조립(책 원본은 싣지 않는다 — 진단 · τ · 경로 · 계열만) ──────────────
    for sid, r in comps.items():
        r.pop("books", None)
    out.update({"members_alloc": list(members), "anchor_ok": anchor_ok, "comps": comps, "S": {"cards": Sres, "arms": Sarms, "delta": Sdelta,
                "twins": Stw, "alloc": ASt, "alloc_delta": ASd, "alloc_paths": Ares, "hygiene": hyg},
                "L": {"cards": {k: v for k, v in Lres.items() if k != "V-A"}, "alloc": Lres.get("V-A"), "twins": Ltw, "vintage": Lvin},
                "H_V": hv, "joint": joint, "fid": fidg, "adoption": am, "secondary_BY": sec, "stouffer": stf, "dsr": dsr,
                "n_arms": {"S_cards": sum(len(v) for v in Sarms.values()), "S_twins": len(Stw), "S_alloc": len(ASt), "L_cards": len(Lres),
                           "L_twins": len(Ltw)}})
    return out


# ══════════════════════════════════════════════════════════════════════════
#  결과 문서가 옮길 수 있는 칸(등록 §5 게시 표를 코드로) — 저장소 밖 캐시에만 쓴다(_vbatch.public.json)
#  싣는다: S 층(10년) 요약 통계 · 관문 불리언 · H_V 기각 여부 · 공동 조건 불리언 · 채택 표시 · 창 · 첫 활성 달 · F0 결정 · 선견 셈 · 위생 · EG30 비교 줄 요약
#  싣지 않는다: L 층 평균 · t · p · α̂ · 위약 순위 값 · 사건 · 해마다 · 쌍둥이 L 값 · FID 상관 값 · Stouffer · DSR 값 · 경로 · 계열(D1)
# ══════════════════════════════════════════════════════════════════════════
PUBLIC_H1 = ("n", "mean", "ann", "te", "ir", "t", "t12", "p", "first", "last")


def _pub_h1(h):
    return None if not h else {k: h.get(k) for k in PUBLIC_H1}


def _b(v):
    if v is None:
        return None
    try:
        if v != v:
            return None
    except Exception:                                        # noqa: BLE001
        pass
    return bool(v)


def _pub_bundle(bd):
    if not bd:
        return None
    y = bd.get("years") or {}
    keep = {k: bd.get(k) for k in ("down", "up", "crash_m", "surge_m", "roll36_neg", "blocks4")}
    keep["crash_legs"] = {k: (bd.get("crash_legs") or {}).get(k) for k in ("n", "mean", "won")}
    keep["rebounds"] = {k: (bd.get("rebounds") or {}).get(k) for k in ("n", "mean", "won")}
    keep["years"] = {k: y.get(k) for k in ("rate", "won", "lost", "ties", "partial", "n_full")}
    keep["named"] = {k: {"x": (v or {}).get("x"), "n": (v or {}).get("n")} for k, v in (bd.get("named") or {}).items()}
    keep["h1"] = _pub_h1(bd.get("h1"))
    return keep


def _pub_s(st):
    """S 층 한 팔(10년 · 공개 가능) — FID 는 참/거짓만(L 대리와의 상관이라 값은 싣지 않는다)."""
    if not st:
        return None
    return {"n": st.get("n"), "row": st.get("row"), "h1_10": _pub_h1(st.get("h1_10")), "h1_20": _pub_h1(st.get("h1_20")), "h1_d0": _pub_h1(st.get("h1_d0")),
            "h1_ew": _pub_h1(st.get("h1_ew")), "h1_H": _pub_h1(st.get("h1_H")), "g5e": _b(st.get("g5e")), "turn_1w": st.get("turn_1w"),
            "G3_down_mean": st.get("G3_down_mean"), "G3_H_down_mean": st.get("G3_H_down_mean"),
            "fid_gate": _b((st.get("fid") or {}).get("gate")) if st.get("fid") is not None else None,
            "s_point_pos_report": _b(st.get("s_point_pos_report")), "bundle": _pub_bundle(st.get("bundle"))}


def _pub_gates(G):
    """L 층 관문은 불리언 · 라벨만(D1)."""
    if not G:
        return None
    g5 = G.get("G5") or {}
    rm = (G.get("G2") or {}).get("rebound_miss") or {}
    return {"G2": {"ok": _b(G["G2"]["ok"]), "rebound_miss_ok": _b(rm.get("ok")) if rm else None, "rebound_miss_applies": _b(rm.get("applies")) if rm else None},
            "G3": {"ok": _b(G["G3"]["ok"])}, "G5": {k: (None if v is None else _b(v)) for k, v in g5.items()},
            "G6": {"a_ok": _b((G.get("G6") or {}).get("a_ok"))}, "adopt_gates": _b(G.get("adopt_gates"))}


def _pub_L(r, holm_reject=None):
    if not r:
        return None
    a = r.get("alpha") or {}
    return {"window": r.get("window"), "n": a.get("n"), "first_active": r.get("first_active"), "strands": r.get("strands"),
            "holm_reject": _b(holm_reject), "joint": _b(r.get("joint")),
            "joint_parts": {"alpha_LC_pos": _b((r.get("alpha_LC") or {}).get("a") is not None and (r.get("alpha_LC") or {}).get("a") > 0),
                            "placebo_rank_ge_min": _b(r.get("placebo_rank") is not None and r.get("placebo_rank") >= 0.90),
                            "rebound_miss_ok": _b((r.get("rebound_miss") or {}).get("ok"))},
            "gates": _pub_gates(r.get("gates"))}


PUBLIC_CMP = ("n", "mean", "ann", "t", "first", "last", "role")


def _pub_cmp(cmp):
    """EG30 비교 줄 요약(S 창 · 보고만) — 🔧 검토 고침: v_cmp 가 셈한 요약 한 줄(cmp["summary"])의 칸만 옮긴다(EG30 월 계열은 V 과정에 없다)."""
    sm = (cmp or {}).get("summary")
    if not sm:
        return None
    return {k: sm.get(k) for k in PUBLIC_CMP if k in sm}


def public_view(out, out_sha256=None, out_bytes=None, cmp=None):
    """§5 게시 표를 코드로 — 결과 문서는 이 사전의 칸만 옮긴다."""
    S = out.get("S") or {}
    L = out.get("L") or {}
    hv = out.get("H_V") or {}
    rej = (hv.get("holm") or {}).get("reject") or {}
    cards = {}
    for sid, arms in (S.get("arms") or {}).items():
        comp = (out.get("comps") or {}).get(sid) or {}
        cards[sid] = {"name": (comp.get("spec") or {}).get("name"), "S": {a: _pub_s(v) for a, v in arms.items()},
                      "S_delta_W_S0": _pub_h1(((S.get("delta") or {}).get(sid) or {}).get("h1")),
                      "diag": comp.get("diag"), "tau_w": comp.get("tau_w"), "attn": comp.get("attn"),
                      "L": _pub_L((L.get("cards") or {}).get(sid), rej.get(sid)) if sid in (L.get("cards") or {}) else None}
    twins = {t: {"arm": v.get("arm"), "S": _pub_s(v.get("S")), "diag": v.get("diag")} for t, v in (S.get("twins") or {}).items()}
    for t, v in (L.get("twins") or {}).items():
        twins.setdefault(t, {})["L_built"] = True
        twins[t]["L_window"] = (v or {}).get("window")
    la = out.get("lookahead") or {}
    return {"vbatch_public_view": True, "note": "결과 문서가 옮길 수 있는 칸만(등록 §5) — 이 밖의 수치는 저장소 밖 _vbatch.json 에만 있다",
            "prereg": out.get("prereg"), "prereg_commit": out.get("prereg_commit"), "stopped": out.get("stopped"), "decisions": out.get("decisions"),
            "lookahead": {"ok": _b(la.get("ok")), "cond": la.get("cond"), "pit": la.get("pit"), "pit_june": la.get("pit_june")},
            "clusters": out.get("clusters"), "members_alloc": out.get("members_alloc"), "anchor_ok": out.get("anchor_ok"),
            "cards": cards, "twins": twins,
            "allocator": {"S": {a: _pub_s(v) for a, v in (S.get("alloc") or {}).items()}, "S_delta_CA_C0": _pub_h1((S.get("alloc_delta") or {}).get("h1")),
                          "L": _pub_L(L.get("alloc"), rej.get("V-A"))},
            "H_V": {"members": hv.get("members"), "reject": {k: _b(v) for k, v in rej.items()}, "alpha": (hv.get("holm") or {}).get("alpha"),
                    "m": (hv.get("holm") or {}).get("m"), "z_thresholds": hv.get("z_thresholds")},
            "joint": {k: _b(v) for k, v in (out.get("joint") or {}).items()}, "fid_gate": {k: _b(v) for k, v in (out.get("fid") or {}).items()},
            "adoption": out.get("adoption"), "secondary_BY_admitted": (out.get("secondary_BY") or {}).get("admitted"),
            "secondary_BY_excluded": (out.get("secondary_BY") or {}).get("excluded"),
            "L_vintage_same_sign": {k: _b((v or {}).get("same_sign")) for k, v in ((L.get("vintage") or {}).items()) if not k.startswith("_")},
            "hygiene": (S.get("hygiene") or None), "eg30_compare": _pub_cmp(cmp), "n_arms": out.get("n_arms"), "dsr_N": list(DSR_N),
            "f0_repro": out.get("f0_repro"), "out_sha256": out_sha256, "out_bytes": out_bytes}


# ══════════════════════════════════════════════════════════════════════════
#  굽기(부모 과정) — 표식 → 태그 → 자식 → 비교 줄 → 게시 칸 → 실행 기록 → FINISHED
# ══════════════════════════════════════════════════════════════════════════
def _push_start_tag(commit):
    if _OVR["tag"]:
        _write_text(os.path.join(_OVR["tag"], START_TAG), commit + "\n")
        return "override"
    have = _remote_start_tag()
    if have == commit:
        return "already"
    if have is not None:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다." % have[:8])
    r1 = _git("tag", "-f", START_TAG, commit)
    r2 = _git("push", "--quiet", "origin", "refs/tags/%s:refs/tags/%s" % (START_TAG, START_TAG))
    if r1.returncode != 0 or r2.returncode != 0 or _remote_start_tag() != commit:
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다(%s) — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 VBATCH_RERUN)."
                         % (r2.stderr or r1.stderr).strip()[:160])
    return "pushed"


def _mark_finished(P, sha):
    line = "%s %s %s\n" % (FINISHED, sha, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):
        with io.open(m, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)


def _child_env(extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.update(extra)
    return env


def _run_compare(commit, P, smoke=False):
    """EG30 비교 줄 — v_cmp 별도 과정(VBATCH_REGISTERED = 등록 커밋). 연기에서는 등록 커밋이 없어 멈춰야 한다(거부가 곧 통과)."""
    env = _child_env({"VBATCH_CACHE": VD.cache_guard()})
    if smoke:
        env.pop("VBATCH_REGISTERED", None)
    else:
        env["VBATCH_REGISTERED"] = commit
    t0 = time.time()
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "v_cmp.py"), "--compare", "--out", P["cmp"]], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return {"rc": r.returncode, "sec": round(time.time() - t0, 1), "written": os.path.exists(P["cmp"]),
            "refused_without_registration": (smoke and r.returncode != 0 and not os.path.exists(P["cmp"]))}


def bake(commit, rerun=None, smoke_env=None):
    """frozen_check 를 통과한 뒤에만 부른다(--smoke 는 가짜 커밋으로). 값은 찍지 않는다 — 경로 · sha256 · 초만."""
    t0 = time.time()
    P = paths()
    if rerun:
        started = _read_text(P["mark"] if os.path.exists(P["mark"]) else P["gitmark"]).strip()
    else:
        started = "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):                      # 무엇보다 먼저 — 도중에 죽어도 한 번 굽기가 지켜진다
        if not os.path.exists(m):
            _write_text(m, started + "\n")
    tag = _push_start_tag(commit)                            # 셋째 표식 — 계산 전에
    env = _child_env(dict({"VBATCH_RUNNER_TOKEN": commit, "VBATCH_OUT_DIR": P["dir"]}, **(smoke_env or {})))
    tc = time.time()
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__), "--_bake-child"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    sec_child = round(time.time() - tc, 1)
    if r.returncode != 0 or not os.path.exists(P["out"]):
        tail = (r.stderr or "")[-1200:] if smoke_env else (r.stderr or "")[-600:]
        raise SystemExit("🚨 굽기 자식 과정 실패(rc %s · 산출 %s) — 산출이 없으면 VBATCH_RERUN 으로 처음부터: %s"
                         % (r.returncode, os.path.exists(P["out"]), tail))
    child = _read_json(P["child"]) if os.path.exists(P["child"]) else {}
    cm = _run_compare(commit, P, smoke=bool(smoke_env))
    cmp_doc = _read_json(P["cmp"]) if cm["written"] else None
    blob = _bytes(P["out"])
    sha = hashlib.sha256(blob).hexdigest()
    out = json.loads(blob.decode("utf-8"))                   # 게시 칸을 짓는 데만(찍지 않는다)
    pub = public_view(out, sha, len(blob), cmp_doc)
    _write_text(P["public"], json.dumps(_clean(pub), ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    del out
    mods = local_modules()
    unf = sorted(set(unfrozen_modules(mods)) | set(unfrozen_modules(child.get("local_modules") or [])))
    err = []
    if unf:
        err.append("얼리지 않은 build/ 모듈을 불렀다: %s" % ", ".join(unf))
    for k in ("runtime", "open_audit", "static"):
        if not (child.get("noeg") or {}).get(k, {}).get("ok"):
            err.append("G-NoEG(%s) 거짓" % k)
    if child.get("unregistered_data"):
        err.append("판 점검 밖 랩 자료를 읽었다: %s" % ", ".join(child["unregistered_data"][:5]))
    if not smoke_env and cm["rc"] != 0:
        err.append("EG30 비교 줄(v_cmp) 실패 rc %s — 보고 줄만 빠진다" % cm["rc"])
    rec = {"prereg": PREREG, "prereg_commit": commit, "runner": RUNNER, "started": started, "rerun": rerun, "start_tag": tag,
           "stopped": child.get("stopped"), "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "sec": round(time.time() - t0, 1), "sec_child": sec_child,
           "out": os.path.basename(P["out"]), "out_sha256": sha, "out_bytes": len(blob),
           "public": os.path.basename(P["public"]), "public_sha256": hashlib.sha256(_bytes(P["public"])).hexdigest(),
           "cmp": cm, "env": {k: os.environ.get(k) for k in ENV_PINS}, "versions": _versions(), "frozen": list(FROZEN),
           "local_modules_parent": mods, "local_modules_child": child.get("local_modules"), "unfrozen_modules": unf,
           "noeg": child.get("noeg"), "data_files_opened": child.get("data_files_opened"), "peak_mb_parent": peak_mb(),
           "peak_mb_child": child.get("peak_mb"), "clock_child": child.get("clock"), "registration_error": err, "smoke": bool(smoke_env),
           "note": "값 없음 — 결과는 _vbatch.public.json 의 칸만 결과 문서(등록 §5 게시 규칙)로 옮긴다"}
    _write_text(P["runlog"], json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
    _mark_finished(P, sha)
    print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)%s" % (P["out"], sha[:16], rec["sec"],
                                                          (" · 멈춤: %s" % child.get("stopped")) if child.get("stopped") else ""))
    return rec


def _same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def child_gate(token, d, remote_tag=None, gitmark=None):
    """🔧 검토 고침(등록 전) — 진짜 굽기 자식이 스스로 다시 보는 판(부모 frozen_check 를 건너뛴 직접 실행을 막는다): 러너 표 = 이 문서 · 러너 · F0 · VFWD 창세를
    처음 더한 커밋(40자) · origin/main 의 조상 · 그 커밋의 등록 문서에 빈칸 없음 · 산출 폴더 = <캐시>/out · git 공용 폴더 표식이 같은 커밋 · origin 시작 태그 = 그 커밋.
    remote_tag · gitmark 는 selftest 가 넘긴다(없으면 실제로 본다). 하나라도 어긋나면 SystemExit."""
    if not re.fullmatch(r"[0-9a-f]{40}", token or ""):
        raise SystemExit("🚨 러너 표가 등록 커밋(40자)이 아니다 — 굽기는 v_run.py(판 점검 → 시작 표식)로만.")
    r = _git("rev-parse", "--verify", "-q", token + "^{commit}")
    if r.returncode != 0 or r.stdout.strip() != token:
        raise SystemExit("🚨 러너 표 커밋을 찾지 못했다.")
    for p_ in FIRST_ADDED:
        added = _git("log", "--format=%H", "--diff-filter=A", token, "--", p_).stdout.split()
        if not added or added[-1] != token:
            raise SystemExit("🚨 러너 표 커밋이 %s 를 처음 더한 커밋이 아니다." % p_)
    if _git("merge-base", "--is-ancestor", token, "origin/main").returncode != 0:
        raise SystemExit("🚨 러너 표 커밋이 origin/main 에 없다.")
    txt = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (token, PREREG)], capture_output=True).stdout.decode("utf-8", "replace")
    if any(placeholder_counts(txt)):
        raise SystemExit("🚨 러너 표 커밋의 등록 문서에 빈칸이 남았다.")
    if not _same_path(d, os.path.join(VD.cache_guard(), "out")):
        raise SystemExit("🚨 진짜 굽기의 산출 폴더는 <캐시>/out 뿐이다.")
    gm = gitmark or _git_mark_path()
    if not os.path.exists(gm) or not _read_text(gm).startswith(token):
        raise SystemExit("🚨 git 공용 폴더 시작 표식이 러너 표와 다르다.")
    tag = remote_tag if remote_tag is not None else _remote_start_tag()
    if tag != token:
        raise SystemExit("🚨 origin 시작 태그가 러너 표 커밋이 아니다(계산 전에 밀지 않은 굽기).")
    return True


def smoke_gate(d, nperm, pit_n, cond_n):
    """🔧 검토 고침 — 연기 자식은 <캐시>/vbatch_runner_smoke_*/out 에서만 · 위약 · 선견 수는 SMOKE_CAPS 이하(연기 경로로 온 강도 굽기 차단)."""
    parent = os.path.dirname(os.path.abspath(d))
    if _same_path(d, os.path.join(VD.cache_guard(), "out")):
        raise SystemExit("🚨 연기 굽기가 진짜 산출 폴더를 쓰려 한다.")
    if not (os.path.basename(parent).startswith("vbatch_runner_smoke_") and _same_path(os.path.dirname(parent), VD.cache_guard())
            and os.path.basename(os.path.abspath(d)) == "out"):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/vbatch_runner_smoke_*/out 이 아니다.")
    if nperm > SMOKE_CAPS["nperm"] or pit_n > SMOKE_CAPS["pit_n"] or cond_n > SMOKE_CAPS["cond_n"]:
        raise SystemExit("🚨 연기 굽기의 위약 · 선견 수가 상한(%s)을 넘는다." % SMOKE_CAPS)
    return True


def _bake_child():
    """굽기 자식 과정 — 러너 표(VBATCH_RUNNER_TOKEN = 시작 표식의 커밋)가 있어야만 연다. 산출 · 자식 기록을 쓰고 값은 찍지 않는다.
    진짜 굽기는 child_gate(등록 커밋 · origin · 빈칸 · 산출 폴더 · 표식 · 태그)를 스스로 다시 본다 · 연기는 smoke_gate(폴더 · 상한)."""
    token, d = os.environ.get("VBATCH_RUNNER_TOKEN"), os.environ.get("VBATCH_OUT_DIR")
    smoke = token == "SMOKE"
    if not token or not d:
        raise SystemExit("🚨 러너 표가 없다 — 굽기는 v_run.py(판 점검 → 시작 표식) 로만.")
    P = paths(d)
    if not os.path.exists(P["mark"]) or not _read_text(P["mark"]).startswith(token):
        raise SystemExit("🚨 시작 표식이 러너 표와 다르다 — 러너 밖 굽기 차단.")
    if smoke:
        nperm = int(os.environ.get("VBATCH_SMOKE_NPERM") or 3)
        pit_n, cond_n = int(os.environ.get("VBATCH_SMOKE_PIT_N") or 4), int(os.environ.get("VBATCH_SMOKE_COND_N") or 20)
        smoke_gate(d, nperm, pit_n, cond_n)
        f0p = os.environ.get("VBATCH_F0_FILE")
        doc = load_f0(f0p) if f0p else None
        dec = _decisions(doc) if doc else dict(SMOKE_DEFAULT_DEC, clusters=None, gegd_pass={}, strand_status=None)
    else:
        for k in ("VBATCH_SMOKE", "VBATCH_SMOKE_NPERM", "VBATCH_F0_FILE"):
            if os.environ.get(k):
                raise SystemExit("🚨 연기 전용 환경 변수 %s 가 진짜 굽기에 켜져 있다." % k)
        child_gate(token, d)
        doc = load_f0()
        fb = f0_check(doc, code_shas())
        if fb:
            raise SystemExit("🚨 F0 문서: %s" % "; ".join(fb[:3]))
        dec = _decisions(doc)
        import v_tests as VT
        nperm, pit_n, cond_n = VT.NPERM, PIT_LOOKAHEAD_N, COND_LOOKAHEAD_N
        if nperm < VT.NPERM_MIN:
            raise SystemExit("🚨 NPERM %d < 등록 %d" % (nperm, VT.NPERM_MIN))
    VG.install_open_audit()
    t0 = time.time()
    clock = {}
    import warnings
    import numpy as np
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        warnings.simplefilter("ignore")
        out = run_batch(dec, nperm, pit_n, cond_n, twins=True, smoke=smoke, clock=clock, book_la_n=(min(pit_n, BOOK_LOOKAHEAD_N) if smoke else BOOK_LOOKAHEAD_N))
    out["prereg"], out["prereg_commit"] = PREREG, token
    txt = json.dumps(_clean(out), ensure_ascii=False, allow_nan=False) + "\n"
    _write_text(P["out"], txt)                               # 한 번에 끝에서 쓴다 — 잘린 파일도 «쓰였다» 로 친다
    opened = data_files_opened()
    rt, oa, st = VG.runtime_check(), VG.open_audit_check(), VG.noeg_static()
    rec = {"stopped": out.get("stopped"), "local_modules": local_modules(), "data_files_opened": opened, "unregistered_data": unregistered_data(opened),
           "noeg": {"runtime": {"ok": rt["ok"], "loaded_forbidden": rt["loaded_forbidden"]},
                    "open_audit": {"ok": oa["ok"], "n_opened": oa["n_opened"], "eg_files_opened": oa["eg_files_opened"]},
                    "static": {"ok": st["ok"], "n_reached": st["n_reached"], "hits": st["hits"], "separate_violations": st["separate_violations"]}},
           "peak_mb": peak_mb(), "sec": round(time.time() - t0, 1), "clock": clock, "n_arms": out.get("n_arms"), "smoke": smoke,
           "note": "자식 과정 기록 — 값 없음"}
    _write_text(P["child"], json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
    print("자식 굽기 끝 · %.0f초" % rec["sec"])
    return 0


def main():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("VBATCH_RERUN"))


# ══════════════════════════════════════════════════════════════════════════
#  F0 — 비중 · 개수 · 날짜 · 라벨 · 커버리지 · 앵커 · 군 · G-EGD(🚨 수익 · 신호-수익 통계 없음)
# ══════════════════════════════════════════════════════════════════════════
def f0_first_active(zL, proxies, strands):
    """L 가닥 첫 활성 결정 달(셈만) — slope_path 의 유효 쌍 마스크(z(s) · y(s+1) · σ̂(s) · z(s+1) 가 선 s)를 값 없이 세어
    결정 i 에 쌍(s ≤ i − 3) ≥ 최소 쌍 · z(i) 가 선 첫 달. σ̂(s) 가 서는가 = y 의 [s−2−59, s−2] 에 선 값 ≥ 36(값은 보지 않는다)."""
    import numpy as np
    import pandas as pd
    import v_core as C
    out = {}
    for c, proxy in strands:
        if c not in zL.columns or proxy not in proxies:
            out[c] = None
            continue
        z = np.isfinite(pd.Series(zL[c]).to_numpy(float))
        yv = np.isfinite(pd.Series(proxies[proxy]).reindex(zL.index).to_numpy(float))
        T = len(z)
        cnt = pd.Series(yv.astype(float)).rolling(C.WLS_N, min_periods=1).sum().to_numpy()
        sig = np.zeros(T, bool)
        sig[C.Y_LAG:] = cnt[:T - C.Y_LAG] >= C.WLS_MIN
        y1 = np.zeros(T, bool)
        y1[:-1] = yv[1:]
        z1 = np.zeros(T, bool)
        z1[:-1] = z[1:]
        val = z & y1 & sig & z1
        cum = np.cumsum(val)
        need = C.PAIRS_MIN_BSPRD if c == "BSPRD" else C.PAIRS_MIN
        first = None
        for i in range(3, T):
            if cum[i - 3] >= need and z[i]:
                first = str(zL.index[i])
                break
        out[c] = first
    return out


def _yearly(rows, keys):
    """달 행 {m: {k: 수}} → 해마다 {해: {k: 최소 · 최대}}(목록 없이 · 공개 안전)."""
    agg = {}
    for m, r in rows.items():
        y = m[:4]
        a = agg.setdefault(y, {})
        for k in keys:
            v = r.get(k)
            if v is None:
                continue
            lo, hi = a.get(k + "_min"), a.get(k + "_max")
            a[k + "_min"] = v if lo is None else min(lo, v)
            a[k + "_max"] = v if hi is None else max(hi, v)
    return {y: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()} for y, a in sorted(agg.items())}


def _f0_child(d):
    """F0 자식 과정 — 비중 · 개수만. 쓰는 것: <d>/f0_v.json(공개 안전 칸 + 달 행) · <d>/vb_books.json.gz(G-EGD 넘김 · v_cmp 가 읽는다)."""
    import numpy as np
    import pandas as pd
    import v_core as C
    import v_cond as VC
    import v_cards as VK
    import v_px_split as VX
    VG.install_open_audit()
    t0 = time.time()
    clock = {}
    Lr = VD.Layer.real()
    zL = Lr.cond_L()
    cl = VK.l_clusters(zL)                                                          # 군 등록물(합칠 L 쌍 · 전체 폐포 보고) — S 쪽은 아래 책에서
    rho_internal = {"L": VK.l_cluster_rho(zL), "S": {}}                             # ρ 값 — 저장소 밖 F0 캐시(_vb_f0_full.json)에만(D1)
    zA = pd.DataFrame(zL).reindex(pd.period_range(VK.L_AXIS[0], VK.L_AXIS[1], freq="M"))      # LLayer 축(1926-07 ~ 2026-08)
    st = VC.strand_status()
    share, viol = VC.share_matrix(st)
    webs = {}
    prox = dict(Lr.l_proxy())
    for sid in VK.WEB_CARDS:
        prim, twin = VC.web(sid, st)
        Ls = [(c, sid) for c, sg, layer in prim if c in VC.CONDS and "L" in layer]
        fa = f0_first_active(zA, prox, Ls)
        cls = sorted(set(VK.web_cluster_labels(cl, [c for c, _ in Ls], sid)))
        act = [v for v in fa.values() if v]
        webs[sid] = {"primary": [c for c, _, _ in prim], "twin_strands": [c for c, _, _, _ in twin], "L_strands": [c for c, _ in Ls],
                     "L_clusters": [str(x) for x in cls], "n_L_clusters": len(cls),
                     "L_strength": ("정적(가닥 없음)" if not cls else ("절반(군 하나 · D09)" if len(cls) == 1 else "온 강도(군 ≥ 2 · 같은 쪽 요구)")),
                     "first_active_L": fa, "first_active_card": (min(act) if act else None)}
    clock["clusters_webs"] = round(time.time() - t0, 1)
    t1 = time.time()
    SL = VK.SLayer(Lr, clusters=cl)
    cov_rows, dec_cov = VK.f0_signal_coverage(SL)
    over = {"use_sp": bool(dec_cov["use_sp"]), "prof": dec_cov["prof"]}
    clock["signal_coverage"] = round(time.time() - t1, 1)
    # G-COMMON(θ = 1 능동 벡터 공통 몫 · 크기 중립 끔 상태에서) → 결정
    t1 = time.time()
    Fb, diag, taus = {}, {}, {}
    for sid in VK.CARD_IDS:
        sp = VK.spec_of(sid, **over)
        F, fi = SL.books(sp, theta=1.0)
        Fb[sid] = F
        diag[sid] = {"F": VK.book_diag(fi)}
    mS = [m for m in SL.months if m >= VK.S_ARM_FROM]
    sc = []
    for m in mS:
        X = SL.cross(m)
        A = [X.arr(Fb[s][m]) - X.wB for s in VK.ALLOC5 if m in Fb[s]]
        if len(A) == 5:
            v = C.common_share(np.vstack(A))
            if v is not None:
                sc.append(v)
    gmed = float(np.median(sc)) if sc else None
    gcom = bool(gmed is not None and gmed > C.G_COMMON_MAX)
    clock["g_common"] = round(time.time() - t1, 1)
    # K7 검토 고침 — S 전용 책 G2own z 대 S 시장 가닥 z 의 ρ(책 · 장부가 · 시총 · 시장 수준 계열만) → 군 등록물 · 웹마다 S 군
    t1 = time.time()
    rho_internal["S"] = {sid: VK.s_g2own_rho(SL, Fb[sid], sid) for sid in ("V01", "V03")}
    cl["S_edges"] = {sid: VK.s_g2own_edges(r) for sid, r in rho_internal["S"].items()}
    for sid in VK.WEB_CARDS:
        prim, _tw = VC.web(sid, st)
        Ss = [("G2own:%s" % sid if (c.startswith("G2own") and "G2own:%s" % sid in VC.CONDS) else c) for c, sg, layer in prim if "S" in layer]
        scl = sorted(set(VK.web_cluster_labels(cl, Ss, sid)))
        webs[sid].update({"S_strands": Ss, "S_clusters": [str(x) for x in scl], "n_S_clusters": len(scl),
                          "S_strength": ("정적(가닥 없음)" if not scl else ("절반(군 하나 · D09)" if len(scl) == 1 else "온 강도(군 ≥ 2 · 같은 쪽 요구)"))})
    clock["s_clusters"] = round(time.time() - t1, 1)
    # LIQ τ(θ = 0.8 · 비중만) → 비상 규칙
    t1 = time.time()
    e = VK.spec_of("V03", **over)
    b8, _ = SL.books(e, theta=0.8, gcommon=gcom)
    tau08 = C.tau_weights_only([b8.get(m) for m in mS])
    liq_em = bool(tau08 is not None and tau08 > C.LIQ_TURN_EMERGENCY)
    clock["liq_tau"] = round(time.time() - t1, 1)
    over["liq_emergency"] = liq_em
    # 결정을 건 책(θ = 1 · G-COMMON 반영) — G-EGD 넘김 · 책 진단 · τ(비중만)
    t1 = time.time()
    comps = {}
    for sid in VK.CARD_IDS:
        sp = VK.spec_of(sid, **over)
        F, fi = (SL.books(sp, theta=1.0, gcommon=gcom) if gcom else (Fb[sid], None))
        S0, i0 = SL.books(sp, theta=sp["theta0"], gcommon=gcom)
        comps[sid] = {"spec": {k: v for k, v in sp.items() if not callable(v)}, "books": {"F": F}}
        if fi is not None:
            diag[sid]["F"] = VK.book_diag(fi)
        diag[sid]["S0"] = VK.book_diag(i0)
        taus[sid] = {"F": C.tau_weights_only([F.get(m) for m in mS]), "S0": C.tau_weights_only([S0.get(m) for m in mS])}
    VK.export_for_cmp(SL, comps, os.path.join(d, "vb_books.json.gz"))
    clock["books_export"] = round(time.time() - t1, 1)
    # 커버리지 · 생존편향 · 밀도(개수만)
    t1 = time.time()
    U = Lr.pit
    cov = {}
    surv = {}
    dens = {}
    for m in SL.months:
        c = U.coverage(m)
        cov[m] = {"n": c["n"], "n_spx": c["n_spx"], "n_ndx_only": c["n_ndx_only"], "share_names_me": c["share_names_me"],
                  "fallback_me_share": c["fallback_me_share"], "me_extreme": c["me_extreme"], "no_gid": c["no_gid"],
                  "no_sector": int((c.get("sector_src") or {}).get("none", 0)), "sector_today": int((c.get("sector_src") or {}).get("today(선견)", 0))}
        X = SL.cross(m)
        ins = X.ins
        dens[m] = {"OB": sum(1 for f in ins if f == "OB"), "OS": sum(1 for f in ins if f == "OS"), "INS_unk": sum(1 for f in ins if f == "unk"),
                   "EAR_eligible": int(X.ear_ok.sum()), "CH": int(X.ch.sum()), "V08_NI_neg": (int(np.nansum(X.niv < 0)) if m[5:7] == "06" else None),
                   "beta_fp": int(np.isfinite(X.beta).sum())}
    for m in [x for x in SL.months if x[5:7] == "06"]:
        sv = U.survivorship(m)
        rows = {}
        for grp, cc in sv.items():
            n = max(cc["n"], 1)
            rows[grp] = {"n": cc["n"], **{k: round(cc[k] / n, 4) for k in ("me", "E", "S", "OP", "ROA", "LEV", "sigROA", "BE")}}
        surv[m[:4]] = rows
    clock["coverage"] = round(time.time() - t1, 1)
    t1 = time.time()
    an = VX.anchors(U)
    clock["anchors"] = round(time.time() - t1, 1)
    in_S = lambda m: "2016-08" <= m <= VK.LAST_DECISION
    s_ms = [m for m in SL.months if in_S(m)]
    name_ok = [m for m in s_ms if (cov[m]["share_names_me"] or 0) >= 0.90]
    fb_ok = [m for m in s_ms if (cov[m]["fallback_me_share"] or 0) <= 0.05]
    lat_min = {}
    for y, rows in surv.items():
        ld = rows.get("later_delisted")
        if ld:
            lat_min[y] = min(ld[k] for k in ("E", "S", "OP", "ROA", "LEV", "BE"))
    surv_risk = sorted(y for y, v in lat_min.items() if v < 0.75)
    res = {"kind": "vbatch_f0_part", "clusters": cl, "clusters_rho_internal": rho_internal, "strand_status": {k: v["status"] for k, v in st.items()},
           "share_matrix": {c: {s: sg for s, sg in d_.items()} for c, d_ in share.items()}, "share_violations": viol, "webs": webs,
           "signal_coverage": {"decision": {"use_sp": bool(dec_cov["use_sp"]), "prof": dec_cov["prof"]},
                               "month_share_ge_085": {k: round(v, 4) for k, v in dec_cov["month_share"].items()},
                               "yearly": _yearly(cov_rows, ("ep", "sp", "op", "roa", "qlt2", "beta"))},
           "g_common": {"median": (round(gmed, 4) if gmed is not None else None), "n_months": len(sc), "threshold": C.G_COMMON_MAX, "on": gcom},
           "liq_tau_08": {"tau": (round(tau08, 3) if tau08 is not None else None), "threshold": C.LIQ_TURN_EMERGENCY, "emergency": liq_em},
           "book_diag": diag, "tau_weights_only": {s: {a: (round(v, 3) if v is not None else None) for a, v in t.items()} for s, t in taus.items()},
           "coverage": {"yearly": _yearly(cov, ("n", "n_spx", "n_ndx_only", "share_names_me", "fallback_me_share", "me_extreme", "no_gid", "no_sector", "sector_today")),
                        "S_months": len(s_ms), "S_months_name_share_ge_090": len(name_ok), "S_months_fallback_le_005": len(fb_ok),
                        "val_provisional": len(fb_ok) < len(s_ms)},
           "density": {"yearly": _yearly(dens, ("OB", "OS", "INS_unk", "EAR_eligible", "CH", "V08_NI_neg", "beta_fp"))},
           "survivorship": {"june": surv, "later_delisted_min_share": {y: round(v, 4) for y, v in lat_min.items()}, "risk_years": surv_risk,
                            "label": (["VAL", "QLT"] if surv_risk else [])},
           "anchor": {"gate_ok": bool(an["gate_ok"]), "mae": an["mae"], "sec_cover_reference_ok": bool(an["sec_ref_ok"]),
                      "sec_cover_reference_mae": an["sec_ref_mae"], "table": an.get("table"), "repairs": an.get("repairs"),
                      "rows": [{k: r.get(k) for k in ("t", "m", "known_T", "spec_T", "repaired", "calc_T", "err", "kind", "sec_ref_T", "err_vs_sec")}
                               for r in an["rows"]]},
           "noeg": {"runtime": VG.runtime_check()["ok"], "open_audit": VG.open_audit_check()["ok"]},
           "data_files_opened": data_files_opened(), "clock": clock, "peak_mb": peak_mb(), "sec": round(time.time() - t0, 1)}
    _write_text(os.path.join(d, "f0_v.json"), json.dumps(_clean(res), ensure_ascii=False, indent=1) + "\n")
    print("F0 자식 끝 · %.0f초" % res["sec"])
    return 0


def f0(out=None, write_repo=True):
    """F0 부모 — 자식(V 셈) → v_cmp(G-EGD · 별도 과정) → 합쳐 F0 문서. write_repo=False 면 out 폴더에만(연기)."""
    d = out or os.path.join(VD.cache_guard(), "f0")
    if _inside_repo(d):
        raise SystemExit("🚨 F0 작업 폴더가 저장소 안이다.")
    os.makedirs(d, exist_ok=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__), "--_f0-child", d], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=_child_env({}))
    if r.returncode != 0 or not os.path.exists(os.path.join(d, "f0_v.json")):
        raise SystemExit("🚨 F0 자식 과정 실패(rc %s): %s" % (r.returncode, (r.stderr or "")[-1200:]))
    sec_child = round(time.time() - t0, 1)
    t1 = time.time()
    g = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "v_cmp.py"), "--gegd", "--in", os.path.join(d, "vb_books.json.gz"),
                        "--out", os.path.join(d, "gegd.json")], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=_child_env({"VBATCH_CACHE": VD.cache_guard()}))
    if g.returncode != 0 or not os.path.exists(os.path.join(d, "gegd.json")):
        raise SystemExit("🚨 G-EGD(v_cmp) 실패(rc %s): %s" % (g.returncode, (g.stderr or "")[-1200:]))
    sec_cmp = round(time.time() - t1, 1)
    part = _read_json(os.path.join(d, "f0_v.json"))
    if not ((part.get("noeg") or {}).get("runtime") and (part.get("noeg") or {}).get("open_audit")):
        raise SystemExit("🚨 F0 자식 과정의 G-NoEG(실행 · open 감사)가 거짓 — F0 문서를 쓰지 않는다(검토 고침)")
    gdoc = _read_json(os.path.join(d, "gegd.json"))
    gd = gdoc.get("cards") or {}
    gegd = {s: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in (gd.get(s) or {}).items()} for s in sorted(gd)}
    dec = {"clusters": part["clusters"], "use_sp": part["signal_coverage"]["decision"]["use_sp"], "prof": part["signal_coverage"]["decision"]["prof"],
           "gcommon": part["g_common"]["on"], "liq_emergency": part["liq_tau_08"]["emergency"],
           "gegd_pass": {s: bool((gegd.get(s) or {}).get("pass")) for s in gegd}, "gegd_label": {s: (gegd.get(s) or {}).get("label") for s in gegd},
           "anchor_ok": part["anchor"]["gate_ok"],
           "anchor_resolution": (("repaired" if part["anchor"].get("repairs") else "pass") if part["anchor"]["gate_ok"] else None),
           "osap": False, "strand_status": part["strand_status"]}
    doc = {"kind": "vbatch_f0", "note": ("배치 V F0(등록 전 · 비중 · 개수 · 날짜 · 라벨 · 커버리지 · 앵커(자료 타당성) · 회전(비중 경로)만 — 수익 · 신호-수익 통계 없음). "
                                         "build/v_run.py --f0 가 쓴다 · 등록 커밋이 더한다 · 굽기는 decisions 칸만 읽는다(등록 §3.6 · §8)."),
           "generated_at": VD._now(), "decisions": dec,
           "decision_rules": {"clusters": "웹마다 그 웹 가닥끼리 (기전 가족 ∪ |ρ| ≥ 0.5 인 쌍) 전이적 폐포 · 쌍 = L 층 조건 z 역사(edges) · S 전용 책 G2own 은 S 층 ρ(S_edges) · ρ 값은 캐시에만 — "
                                           "명세 clusters_R2 · 검토 고침(웹 하나의 폐포 · K7)",
                              "use_sp": "S/P 몫 ≥ 0.85 인 달이 S 창 결정 달의 95% 이상 — 명세 V06", "prof": "OP 몫이 같은 규칙이면 op · 아니면 roa — 명세 V07",
                              "gcommon": "θ = 1 능동 공통 몫 달별 중앙값 > 0.30 — 명세 g_common_rule",
                              "liq_emergency": "τ(θ 0.8 · 비중만) > 9.0 → [0.2, 0.6] · θ0 0.4 — 명세 V03 theta",
                              "gegd": "능동 상관 · 겹침 초과 · |Spearman(신호, Eg)| 달별 중앙값 ≤ 0.30 · 0.10 · 0.30 — 하나라도 넘으면 «EG30-근접» → 배분기 · 채택에서 뺌",
                              "anchor": "각 |ME/알려진 값 − 1| ≤ 0.10 · MAE ≤ 0.05 — 실패면 굽지 않고 고친다(명세) · 알려진 값 = V 소유 앵커 표(v_px_split.anchor_table) · "
                                        "repaired = 그 표의 출처 있는 고침 뒤 다시 잰 관문 참 · pass = 고침 없이 참 · 거짓이면 굽지 않는다",
                              "osap": "쓰지 않는다(F0 라이선스 · 파일 확인 없음 — 명세 V05 L_proxy 선택)"},
           "webs": part["webs"], "share_matrix": part["share_matrix"], "share_violations": part["share_violations"],
           "signal_coverage": part["signal_coverage"], "g_common": part["g_common"], "liq_tau_08": part["liq_tau_08"], "gegd": gegd,
           "book_diag": part["book_diag"], "tau_weights_only": part["tau_weights_only"], "coverage": part["coverage"], "density": part["density"],
           "survivorship": part["survivorship"], "anchor": part["anchor"], "noeg_child": part["noeg"],
           "gegd_pins": {"in_sha": gdoc.get("in_sha"), "eg_inputs": gdoc.get("eg_inputs")},
           "code_sha": code_shas(), "sec": {"child": sec_child, "gegd": sec_cmp}, "peak_mb_child": part.get("peak_mb")}
    vl = VG.value_lists(doc)
    if vl:
        raise SystemExit("🚨 F0 문서에 값 계열 같은 숫자 목록: %s" % vl[:3])
    target = os.path.join(ROOT, *F0_FILE.split("/")) if write_repo else os.path.join(d, "_vb_f0.json")
    _write_text(target, json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    full = dict(part, gegd_full=gd)
    _write_text(os.path.join(d, "_vb_f0_full.json"), json.dumps(full, ensure_ascii=False) + "\n")
    return {"path": target, "sec": round(time.time() - t0, 1), "sec_child": sec_child, "sec_gegd": sec_cmp}


def f0_resolve_anchor(choice=None):
    """🔧 검토 고침(등록 전): 손으로 적는 앵커 결정은 없다 — 명세 «실패면 굽지 않고 고친다». repaired 는 V 소유 앵커 표(v_px_split.anchor_table)를
    출처 있는 값으로 고친 뒤 --f0 를 다시 돌려 관문이 참일 때만 F0 가 스스로 적는다(accepted_failed 는 없다)."""
    raise SystemExit("🚨 --f0-resolve-anchor 는 없앴다 — 앵커 표(v_px_split.ANCHOR_REPAIRS)를 출처 있는 값으로 고치고 python -X utf8 build/v_run.py --f0 를 다시 돌린다")


def f0_table(doc=None):
    """F0 문서 → 등록 문서 §3.6 Markdown(값 · 비중 · 개수 · 날짜 · 라벨만)."""
    doc = doc or load_f0()
    if not doc:
        return "F0 문서 없음 — python -X utf8 build/v_run.py --f0"
    d = doc["decisions"]
    L = ["F0 문서 `%s` · 만든 때 %s · sha256 `%s`" % (F0_FILE, doc.get("generated_at"),
                                                   VD.sha256_file(os.path.join(ROOT, *F0_FILE.split("/")))[:16]
                                                   if os.path.exists(os.path.join(ROOT, *F0_FILE.split("/"))) else "—"), ""]
    L.append("| 결정 | 값 | 규칙 |")
    L.append("|---|---|---|")
    for k in ("use_sp", "prof", "gcommon", "liq_emergency", "anchor_ok", "anchor_resolution", "osap"):
        L.append("| %s | %s | %s |" % (k, d.get(k), (doc.get("decision_rules") or {}).get(k.split("_")[0] if k.startswith("anchor") else k, "")))
    L.append("")
    L.append("| 카드 | 주 가닥 | 쌍둥이 가닥 | L 가닥 | L 군 | L 강도 | S 군 | S 강도 | 첫 활성(L) | G-EGD | 라벨 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for sid, w in (doc.get("webs") or {}).items():
        g = (doc.get("gegd") or {}).get(sid) or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            sid, " · ".join(w["primary"]) or "—", " · ".join(w["twin_strands"]) or "—", " · ".join(w["L_strands"]) or "—",
            " · ".join(w["L_clusters"]) or "—", w["L_strength"], " · ".join(w.get("S_clusters") or []) or "—", w.get("S_strength") or "—",
            w.get("first_active_card") or "—", "통과" if g.get("pass") else "거짓", g.get("label") or "—"))
    for sid in ("V04", "V05", "V08"):
        g = (doc.get("gegd") or {}).get(sid) or {}
        L.append("| %s | (정적 · 측정만/전방 전용) | — | — | — | — | — | — | — | %s | %s |" % (sid, "통과" if g.get("pass") else "거짓", g.get("label") or "—"))
    L.append("")
    cr = d.get("clusters") or {}
    L.append("군 등록물: 규칙 — %s" % (cr.get("rule") or "—"))
    L.append("합칠 L 조건 쌍(|ρ| ≥ 0.5): %s" % (", ".join(cr.get("edges") or []) or "없음"))
    L.append("S 전용 책 G2own 과 합칠 시장 가닥(|ρ| ≥ 0.5): %s" % "; ".join("%s: %s" % (sid, ", ".join(ee) or "없음")
                                                                  for sid, ee in sorted((cr.get("S_edges") or {}).items())))
    L.append("전체 폐포(아홉 조건 · 보고만): %s" % ", ".join("%s → %s" % (k, v) for k, v in sorted((cr.get("global") or {}).items())))
    gc, lq = doc.get("g_common") or {}, doc.get("liq_tau_08") or {}
    L.append("G-COMMON 공통 몫 달별 중앙값 %s(달 %s · 문턱 %s) → 크기 중립 %s · LIQ τ(θ 0.8) %s(문턱 %s) → 비상 %s"
             % (gc.get("median"), gc.get("n_months"), gc.get("threshold"), "켬" if gc.get("on") else "끔", lq.get("tau"), lq.get("threshold"),
                "켬" if lq.get("emergency") else "끔"))
    sc = doc.get("signal_coverage") or {}
    L.append("신호 커버리지(몫 ≥ 0.85 인 달 몫): %s" % ", ".join("%s %s" % (k, v) for k, v in (sc.get("month_share_ge_085") or {}).items()))
    cv = doc.get("coverage") or {}
    L.append("명단 커버리지: S 결정 달 %s · 이름 몫 ≥ 0.90 인 달 %s · 대체 시총 몫 ≤ 5%% 인 달 %s → VAL 잠정 %s"
             % (cv.get("S_months"), cv.get("S_months_name_share_ge_090"), cv.get("S_months_fallback_le_005"), cv.get("val_provisional")))
    sv = doc.get("survivorship") or {}
    L.append("생존편향: 뒤에 편출된 이름의 재무 커버리지가 0.75 아래인 해 %s → 라벨 %s" % (sv.get("risk_years") or "없음", sv.get("label") or "없음"))
    an = doc.get("anchor") or {}
    L.append("시총 앵커: 관문 %s · MAE %s · SEC 표지 대조 %s(MAE %s) · 표 %s" % (an.get("gate_ok"), an.get("mae"), an.get("sec_cover_reference_ok"),
                                                                        an.get("sec_cover_reference_mae"), an.get("table") or "—"))
    for rp in an.get("repairs") or []:
        L.append("  고친 앵커 %s %s: 명세 표 %s → %s(출처: %s)" % (rp.get("t"), rp.get("m"), rp.get("spec_T"), rp.get("known_T"), rp.get("source")))
    L.append("")
    L.append("| 카드 | τ F | τ S0 | β 띠 못 맞춘 달(F) | 투영 줄임(F) | 불가능(F) | 선정 이름 중앙(F) |")
    L.append("|---|---|---|---|---|---|---|")
    for sid, dg in (doc.get("book_diag") or {}).items():
        t = (doc.get("tau_weights_only") or {}).get(sid) or {}
        F = dg.get("F") or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (sid, t.get("F"), t.get("S0"), F.get("beta_fail"), F.get("shrink"), F.get("infeasible"),
                                                          F.get("n_sel_median")))
    return "\n".join(L)


# ══════════════════════════════════════════════════════════════════════════
#  VFWD 창세(🔧 검토 고침 — 명세 registration.commit_order «이 커밋에 … VFWD 창세를 함께») · 결과 문서 렌더러(얼림)
# ══════════════════════════════════════════════════════════════════════════
VFWD_ENTRY = {"decision": "2026-10", "d0_close": "2026-10-30T20:00:00Z", "t1_close": "2026-11-02", "primary_row": "T+1", "measure_row": "D0",
              "cost_primary": 0.001, "cost_alt": 0.002, "late": "10-28 까지 VFWD 원장을 올리지 못하면 2026-11-30 종가에 같은 절차(소급 결정 없음 · 카드 수를 줄이지 않는다)"}
# D29 사용자 확인(등록 §8.4-6) — 설계가 «사용자 확인» 으로 남긴 항목을 오케스트레이터가 바꿨고(V08 전방 전용 카드) 사용자가 등록 전에 확인했다(결과를 본 사람 없음).
D29_CONFIRMATION = {"confirmed": True, "date": "2026-09-27", "by": "사용자(오케스트레이터가 전달)",
                    "decision": "V08 순자사주 카드는 전방 채택 경로(VF08S · FF1 · FF2)를 유지한다", "recorded_in": "build/PREREG-2026-09-27-VBATCH.md §8.4-6"}


def vfwd_genesis():
    """VFWD 창세 문서(기계 판독 · 공개 안전 · 값 계열 없음) — 카드 목록 · 책 규칙 참조 · 주 대조 · 진입 · 행 · 비용 · FF0~FF2 상수(v_tests.FF)와 판정 함수 이름 ·
    얼린 코드 핀(LF sha 앞 16자) · G-EGD 실패 규칙 · V08 조건. 원장 코드(월 행을 쌓는 쪽)는 VFWD 등록이 짓되 이 문서를 바꾸지 않는다(더 좁히는 것만)."""
    import v_tests as VT
    cards = {}
    for sid in ("V01", "V02", "V03", "V06", "V07"):
        n = sid[1:]
        cards["VF%sW" % n] = {"card": sid, "arm": "W", "kind": "W", "main_contrast": "VF%sS" % n,
                              "adoption": ("web_alone" if sid in VT.ADOPT_WEB else "none(배분기 구성원만 · D11)")}
        cards["VF%sS" % n] = {"card": sid, "arm": "S0", "kind": "static", "main_contrast": "w_B", "adoption": "measure_only"}
    cards["VF04S"] = {"card": "V04", "arm": "S0", "kind": "static", "main_contrast": "w_B", "adoption": "measure_only"}
    cards["VF05W"] = {"card": "V05", "arm": "W(CH 제외 + ATTN)", "kind": "W", "main_contrast": "VF05S", "adoption": "measure_only"}
    cards["VF05S"] = {"card": "V05", "arm": "S0(CH 제외)", "kind": "static", "main_contrast": "w_B", "adoption": "measure_only"}
    cards["VF08S"] = {"card": "V08", "arm": "S0", "kind": "N", "main_contrast": "w_B", "adoption": "forward_only",
                      "conditions": ["G-EGD 통과(F0 «EG30-근접» 이면 측정만 · 채택 경로 없음)",
                                     "D29 사용자 확인 — 2026-09-27 확인됨(V08 전방 채택 경로 유지 · 등록 §8.4-6 · §8.2): 이 창세가 확인 기록이다 · "
                                     "VFWD 원장은 다시 확인받지 않고 이 조건을 참으로 읽는다(더 좁히는 것만 할 수 있다)"],
                      "d29": D29_CONFIRMATION}
    cards["VFA"] = {"arm": "FULL", "kind": "A", "members": "등록 F0 의 G-EGD 를 넘은 MOM · LBS · LIQ · VAL · QLT(K ≥ 3)", "main_contrast": "VFE", "adoption": "allocator"}
    cards["VFE"] = {"arm": "C0", "kind": "static", "main_contrast": "w_B", "adoption": "measure_only(귀무)"}
    cards["VFW"] = {"arm": "C-W", "kind": "static", "main_contrast": "VFE", "adoption": "measure_only"}
    cards["VFA7"] = {"arm": "C-7", "kind": "A", "main_contrast": "VFE", "adoption": "measure_only"}
    code = {k: v for k, v in code_shas().items() if k.startswith("build/v_")}
    return {"kind": "vfwd_genesis", "registration": PREREG, "cards": cards, "entry": VFWD_ENTRY,
            "book_rules": {"cards": "build/v_cards.py spec_of · SLayer.books · SLayer.path(T+1 행 · ½ 체결 · LIQ 전량) — 등록 F0 결정(data/_vb_f0.json decisions)을 건다",
                           "web": "build/v_cards.py SLayer.web(L 기울기 · S-E 쌍 · 군 등록물) · build/v_core.py direction_eval · theta_path",
                           "allocator": "build/v_alloc.py s_allocator(FM 기울기 = L · 두 소매 체결 A5)"},
            "gates": {"constants": VT.FF, "functions": ["build/v_tests.py ff_late_fill(FF0)", "build/v_tests.py ff1(FF1)", "build/v_tests.py ff2(FF2)"],
                      "FF0": "늦은 결정 · 핀 어긋남 · 대체 판 달 = 주 대조의 X(W → S · VFA → VFE · VF08S → 0) · 첫 36개월 늦음 ≥ 3 이면 FF2 막힘",
                      "FF1": "24개월(2028-11) · Δ 의 NW(6) t ≤ −1.0 이면 기각(측정 계속)",
                      "FF2": "≥ 36개월 · 사건 최소 · (a)~(g) · 통과 = «전방 일치»(확인 아님) · 60개월(2031-11)에 한 번 더 넘어야 게시"},
            "gegd_fail": "F0 G-EGD «EG30-근접» 카드는 측정만(모든 채택 경로 없음 · VF08S 포함)",
            "code_pins": code, "note": "배치 V 등록 커밋이 더한다(판 점검이 이 파일 · 코드 핀을 얼린 코드와 대조) — 원장 파일은 VFWD 등록이 data/_vfwd/ 에 더한다"}


def vfwd_check(doc, code_now=None):
    """VFWD 창세 거르개(순수) — 꼴 · 카드 · 관문 상수 = 얼린 v_tests.FF · 코드 핀 = 지금 코드. 문제 목록."""
    import v_tests as VT
    bad = []
    if not isinstance(doc, dict) or doc.get("kind") != "vfwd_genesis":
        return ["VFWD 창세 문서 꼴이 아니다"]
    want = vfwd_genesis() if code_now is None else None
    if (doc.get("gates") or {}).get("constants") != VT.FF:
        bad.append("VFWD 관문 상수가 얼린 v_tests.FF 와 다르다")
    need = {"VF01W", "VF01S", "VF02W", "VF02S", "VF03W", "VF03S", "VF04S", "VF05W", "VF05S", "VF06W", "VF06S", "VF07W", "VF07S", "VF08S", "VFA", "VFE", "VFW",
            "VFA7"}
    if set(doc.get("cards") or {}) != need:
        bad.append("VFWD 카드 목록이 등록과 다르다")
    cn = code_now if code_now is not None else {k: v for k, v in code_shas().items() if k.startswith("build/v_")}
    diff = sorted(k for k, v in (doc.get("code_pins") or {}).items() if cn.get(k) != v)
    if diff or not doc.get("code_pins"):
        bad.append("VFWD 창세의 코드 핀이 지금 코드와 다르다(%s …) — --vfwd-genesis 를 다시" % ", ".join(diff[:3]))
    if want is not None and doc.get("entry") != want["entry"]:
        bad.append("VFWD 진입 칸이 등록과 다르다")
    if ((doc.get("cards") or {}).get("VF08S") or {}).get("d29") != D29_CONFIRMATION:
        bad.append("VFWD 창세의 VF08S D29 확인 기록이 등록(§8.4-6)과 다르다")
    return bad


def _fmt(v, nd=4):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%." + str(nd) + "f") % v
    return str(v)


def result_doc(pub):
    """결과 문서 본문(Markdown) — 🔧 검토 고침(얼린 렌더러): 게시 칸 파일(_vbatch.public.json) 하나만 읽어 등록 §5 표의 칸을 옮긴다(손으로 옮기지 않는다)."""
    if not pub or not pub.get("vbatch_public_view"):
        raise SystemExit("🚨 게시 칸 파일이 아니다")
    L = ["# 결과 — 배치 V(%s)" % pub.get("prereg"), "",
         "- 등록 커밋 `%s` · 산출 sha256 `%s` · %s 바이트" % (pub.get("prereg_commit"), (pub.get("out_sha256") or "—")[:16], pub.get("out_bytes")),
         "- 멈춤: %s" % (pub.get("stopped") or "없음"),
         "- 선견 점검: %s" % _fmt((pub.get("lookahead") or {}).get("ok")),
         "- 시총 앵커: %s · 배분기 구성원: %s" % (_fmt(pub.get("anchor_ok")), " · ".join(pub.get("members_alloc") or []) or "—"),
         "- V08: 전방 전용(H_V · BY · 배분기 밖 · 등록 §1.8) — (1) 순발행은 투자 CAPM(HXZ 투자 범주)의 이웃이다 (2) 설계 원본은 이 가족을 뺐다(D29 · 구속 사용자 규칙의 예외) "
         "(3) 오케스트레이터가 더했고 사용자가 등록 전(2026-09-27)에 확인했다(D29 · 전방 채택 경로 유지 · VFWD 창세에 기록) (4) NI 는 취소된 배치 U 판 A 의 소매였다 "
         "(5) S 층 기록(T18)을 본 뒤에 더한 카드다 — 선택에 오염되지 않은 증거는 전방 FF2 뿐", ""]
    hv = pub.get("H_V") or {}
    L += ["## H_V(Holm m %s · 한쪽 α %s)" % (hv.get("m"), hv.get("alpha")), "", "| 구성원 | 기각 | 공동 조건 |", "|---|---|---|"]
    for k in hv.get("members") or []:
        L.append("| %s | %s | %s |" % (k, _fmt((hv.get("reject") or {}).get(k)), _fmt((pub.get("joint") or {}).get(k))))
    L += ["", "## 채택 표시(전방 후보 · 운용 교체 아님)", "", "| 경로 | 표시 | 조건 |", "|---|---|---|"]
    for k, v in (pub.get("adoption") or {}).items():
        L.append("| %s | %s | %s |" % (k, _fmt((v or {}).get("adopt")), " · ".join("%s %s" % (a, _fmt(b)) for a, b in ((v or {}).get("conds") or {}).items()) or (v or {}).get("path")))
    L += ["", "## S 층(10년 · 구현성 · 부호만 · 주 행 T+1 · 10bp)", "", "| 카드 | 팔 | n | 평균 | 연 | t | 20bp 평균 | D0 평균 | 회전 | G5e | 하락월 X | FID |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for sid, c in (pub.get("cards") or {}).items():
        for arm, st in ((c or {}).get("S") or {}).items():
            st = st or {}
            h, h20, hd = st.get("h1_10") or {}, st.get("h1_20") or {}, st.get("h1_d0") or {}
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (sid, arm, h.get("n"), _fmt(h.get("mean"), 5), _fmt(h.get("ann")), _fmt(h.get("t"), 2),
                                                                                   _fmt(h20.get("mean"), 5), _fmt(hd.get("mean"), 5), _fmt(st.get("turn_1w"), 2),
                                                                                   _fmt(st.get("g5e")), _fmt(st.get("G3_down_mean"), 5), _fmt(st.get("fid_gate"))))
    L += ["", "## 배분기 S 팔", "", "| 팔 | n | 평균 | 연 | t | 회전 | G5e |", "|---|---|---|---|---|---|---|"]
    for arm, st in (((pub.get("allocator") or {}).get("S")) or {}).items():
        h = (st or {}).get("h1_10") or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (arm, h.get("n"), _fmt(h.get("mean"), 5), _fmt(h.get("ann")), _fmt(h.get("t"), 2), _fmt((st or {}).get("turn_1w"), 2),
                                                          _fmt((st or {}).get("g5e"))))
    L += ["", "## L 층(불리언 · 창만 — 수치 없음 · D1)", "", "| 카드 | 창 | 첫 활성 | 기각 | 공동 | L-C α>0 | 위약 ≥ 0.90 | 반등 놓침 | G2 | G3 | G6a | 판 민감도 같은 부호 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    vin = pub.get("L_vintage_same_sign") or {}
    for sid, c in (pub.get("cards") or {}).items():
        l_ = (c or {}).get("L")
        if not l_:
            continue
        jp, g = l_.get("joint_parts") or {}, l_.get("gates") or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            sid, "~".join(l_.get("window") or []) or "—", l_.get("first_active") or "—", _fmt(l_.get("holm_reject")), _fmt(l_.get("joint")),
            _fmt(jp.get("alpha_LC_pos")), _fmt(jp.get("placebo_rank_ge_min")), _fmt(jp.get("rebound_miss_ok")), _fmt((g.get("G2") or {}).get("ok")),
            _fmt((g.get("G3") or {}).get("ok")), _fmt((g.get("G6") or {}).get("a_ok")), _fmt(vin.get(sid))))
    L += ["", "## 부 가족 BY(q 0.10 · 보고)", "", "- 문턱을 넘은 이름: %s" % (" · ".join(pub.get("secondary_BY_admitted") or []) or "없음"),
          "- 가족 밖(전방 전용): %s" % (" · ".join(pub.get("secondary_BY_excluded") or []) or "없음"), ""]
    hyg = pub.get("hygiene") or {}
    L.append("## 위생 · 비교 줄")
    L.append("")
    L.append("- 위생(w_B 대 SPY ≥ 0.98): %s" % _fmt(hyg.get("gate")))
    cmp_ = pub.get("eg30_compare") or {}
    L.append("- EG30 비교 줄(보고만 · 어떤 관문 · 귀무에도 없다): n %s · 평균 %s · 연 %s · t %s" % (cmp_.get("n"), _fmt(cmp_.get("mean"), 5), _fmt(cmp_.get("ann")),
                                                                               _fmt(cmp_.get("t"), 2)))
    L.append("- 팔 수: %s" % json.dumps(pub.get("n_arms"), ensure_ascii=False))
    return "\n".join(L) + "\n"


# ══════════════════════════════════════════════════════════════════════════
#  얼린 파일 표 · 등록 직전 점검 · 백업
# ══════════════════════════════════════════════════════════════════════════
def pins_table():
    rows = []
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        if not os.path.exists(fp):
            rows.append({"path": p, "blob": None, "sha256_lf": None, "note": "없음"})
            continue
        blob = _git("hash-object", "--", p).stdout.strip()
        rows.append({"path": p, "blob": blob[:12], "sha256_lf": _sha_lf(_bytes(fp))[:16],
                     "tracked": _git("ls-files", "--error-unmatch", "--", p).returncode == 0})
    return rows


def _audit_src():
    for cand in (os.environ.get("VBATCH_U_SRC"), os.path.join(tempfile.gettempdir(), "ubatch_wt", "build"),
                 os.path.join(os.environ.get("LOCALAPPDATA") or "", "yeodoo_private", "vbatch_cache_backup", "audit_src")):
        if cand and os.path.exists(os.path.join(cand, "u_core.py")) and os.path.exists(os.path.join(cand, "u_tests.py")):
            return cand
    return None


def precommit(run_audit=True):
    """등록 커밋 직전 점검 — 참/거짓 · 이름만(값 없음)."""
    ok_p, bad_p = VD.check_pins()
    ok_c, bad_c = check_cache_pins(full=True)
    ci, cmsg = check_cache_identity()
    f0d = load_f0()
    fb = f0_check(f0d, code_shas()) if f0d else ["F0 문서 없음"]
    gp = os.path.join(ROOT, *VFWD_GENESIS.split("/"))
    gb = vfwd_check(_read_json(gp)) if os.path.exists(gp) else ["VFWD 창세 문서 없음"]
    txt = _read_text(os.path.join(ROOT, *PREREG.split("/"))) if os.path.exists(os.path.join(ROOT, *PREREG.split("/"))) else ""
    n_ph, n_dm = placeholder_counts(txt)
    g = site_guard()
    ne = VG.noeg_static()
    missing = [p for p in FROZEN if not os.path.exists(os.path.join(ROOT, *p.split("/")))]
    reach = sorted(VG.reach(VG.v_targets()) | VG.reach(["v_cmp"]))
    not_frozen = ["build/%s.py" % m for m in reach if "build/%s.py" % m not in FROZEN]
    au = None
    src = _audit_src()
    if run_audit and src:
        a = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "v_audit.py")], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=_child_env({"VBATCH_U_SRC": src}))
        last = [ln for ln in (a.stdout or "").splitlines() if "짝맞춤" in ln]
        sh = {n: VD.sha256_file(os.path.join(src, n)) for n in AUDIT_SRC_SHA}
        au = {"rc": a.returncode, "summary": last[-1].strip() if last else None, "src": src,
              "src_same_as_registered": all(sh[n] == AUDIT_SRC_SHA[n] for n in AUDIT_SRC_SHA)}
    return {"prereg": PREREG, "prereg_n": _N_PREREG, "name_ok": not name_check(), "placeholders": n_ph, "draft_marks": n_dm,
            "pins_ok": ok_p, "pins_bad": bad_p[:5], "cache_pins_ok": ok_c, "cache_pins_bad": bad_c[:5], "cache_identity": ci, "cache_identity_msg": cmsg,
            "f0_present": bool(f0d), "f0_problems": fb, "vfwd_genesis_problems": gb, "site_guard": g["ok"], "site_guard_bad": g["bad"][:5], "noeg_static": ne["ok"],
            "noeg_targets_has_v_run": "v_run" in ne["targets"], "frozen_missing": missing, "closure_not_frozen": not_frozen,
            "registered_constants_bad": registered_constants_ok(), "audit": au, "head": _git("rev-parse", "HEAD").stdout.strip()}


BACKUP_ROOT = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "yeodoo_private", "vbatch_cache_backup")
BACKUP_PARTS = ("raw", "meta", "derived", "lit")


def backup(dst=BACKUP_ROOT):
    """고정본(캐시 raw · meta · derived · lit)과 짝맞춤 원본(u_core · u_tests)을 %TEMP% 밖 사적 폴더로 — SHA 대조(커밋 · 게시하지 않는다)."""
    if _inside_repo(dst) or os.path.normcase(os.path.abspath(dst)).startswith(os.path.normcase(os.path.abspath(tempfile.gettempdir()))):
        raise SystemExit("🚨 백업은 저장소 밖 · %TEMP% 밖에만")
    src = VD.cache_guard()
    idx, n = {}, 0
    for part in BACKUP_PARTS:
        for dp, _, fns in os.walk(os.path.join(src, part)):
            for fn in fns:
                a = os.path.join(dp, fn)
                rel = os.path.relpath(a, src).replace(os.sep, "/")
                b = os.path.join(dst, "cache", *rel.split("/"))
                sha = VD.sha256_file(a)
                if not (os.path.exists(b) and VD.sha256_file(b) == sha):
                    os.makedirs(os.path.dirname(b), exist_ok=True)
                    shutil.copy2(a, b)
                    n += 1
                idx[rel] = sha
    au = _audit_src()
    if au:
        for nm in AUDIT_SRC_SHA:
            b = os.path.join(dst, "audit_src", nm)
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(os.path.join(au, nm), b)
            idx["audit_src/" + nm] = VD.sha256_file(b)
    _write_text(os.path.join(dst, "_index.json"), json.dumps({"at": VD._now(), "files": idx}, ensure_ascii=False) + "\n")
    bad = [r for r, s in idx.items() if VD.sha256_file(os.path.join(dst, "cache", *r.split("/")) if not r.startswith("audit_src/")
                                                        else os.path.join(dst, *r.split("/"))) != s]
    return {"dst": dst, "files": len(idx), "copied": n, "verify_bad": len(bad)}


def restore(cache_root, src=BACKUP_ROOT):
    """백업 → 캐시 뿌리(SHA 대조 · 저장소 안이면 거부)."""
    if _inside_repo(cache_root):
        raise SystemExit("🚨 캐시 뿌리가 저장소 안이다")
    idx = _read_json(os.path.join(src, "_index.json"))["files"]
    bad = 0
    for rel, sha in idx.items():
        if rel.startswith("audit_src/"):
            continue
        a = os.path.join(src, "cache", *rel.split("/"))
        b = os.path.join(cache_root, *rel.split("/"))
        os.makedirs(os.path.dirname(b), exist_ok=True)
        shutil.copy2(a, b)
        bad += int(VD.sha256_file(b) != sha)
    return {"restored": len(idx), "verify_bad": bad}


# ══════════════════════════════════════════════════════════════════════════
#  러너 연기 시험(눈가린 · 산출은 열지 않고 지운다)
# ══════════════════════════════════════════════════════════════════════════
def smoke(nperm=3, pit_n=4, cond_n=20, with_f0=True):
    """러너 경로 전체 — F0(임시 폴더) → 판 점검 우회(가짜 커밋 SMOKE) → 표식 → 자식 굽기(run_batch · 위약 3 · 선견 작게) → 비교 줄 거부 확인 →
    게시 칸 → 실행 기록 → FINISHED. 산출(수익 통계 포함) · F0 결과는 임시 폴더에만 쓰고 **열지 않고** 지운다(실행 기록 · 자식 기록의
    값 없는 칸 — 모듈 이름 · 참/거짓 · 초 · 메모리 — 만 읽는다). 돌려주는 것: {ok, sec, files(존재 · 크기), 모듈 이름, err}."""
    import contextlib
    tmp = tempfile.mkdtemp(prefix="vbatch_runner_smoke_", dir=VD.cache_guard())
    if _inside_repo(tmp):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    saved = dict(_OVR)
    res = {"ok": False, "steps": {}, "err": None}
    t0 = time.time()
    sink = io.StringIO()
    try:
        f0dir = os.path.join(tmp, "f0")
        f0file = None
        if with_f0:
            t1 = time.time()
            try:
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    r = f0(out=f0dir, write_repo=False)
                f0file = r["path"]
                res["steps"]["f0"] = {"ok": os.path.exists(f0file), "sec": round(time.time() - t1, 1),
                                      "files": sorted(os.listdir(f0dir)), "sec_child": r["sec_child"], "sec_gegd": r["sec_gegd"]}
            except BaseException as e:                       # noqa: BLE001
                res["steps"]["f0"] = {"ok": False, "sec": round(time.time() - t1, 1), "err": ("%s: %s" % (type(e).__name__, str(e)))[-1500:]}
        _OVR.update({"out": os.path.join(tmp, "out"), "gitmark": os.path.join(tmp, "gitdir_" + GIT_MARK_NAME), "tag": tmp})
        P = paths()
        t1 = time.time()
        senv = {"VBATCH_SMOKE": "1", "VBATCH_SMOKE_NPERM": str(nperm), "VBATCH_SMOKE_PIT_N": str(pit_n), "VBATCH_SMOKE_COND_N": str(cond_n)}
        if f0file:
            senv["VBATCH_F0_FILE"] = f0file
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                rec = bake("SMOKE", smoke_env=senv)
            res["steps"]["bake"] = {"ok": True, "sec": round(time.time() - t1, 1), "sec_child": rec["sec_child"], "clock_child": rec["clock_child"],
                                    "peak_mb_child": rec["peak_mb_child"], "peak_mb_parent": rec["peak_mb_parent"],
                                    "unfrozen_modules": rec["unfrozen_modules"], "registration_error": rec["registration_error"],
                                    "noeg": rec["noeg"], "cmp": rec["cmp"], "local_modules_child": rec["local_modules_child"],
                                    "data_files_opened_n": len(rec["data_files_opened"] or []),
                                    "stopped": rec["stopped"], "start_tag": rec["start_tag"]}
        except BaseException as e:                           # noqa: BLE001
            res["steps"]["bake"] = {"ok": False, "sec": round(time.time() - t1, 1), "err": ("%s: %s" % (type(e).__name__, str(e)))[-2500:]}
        files = {k: {"exists": os.path.exists(P[k]), "bytes": (os.path.getsize(P[k]) if os.path.exists(P[k]) else 0)}
                 for k in ("out", "mark", "runlog", "public", "child", "gitmark")}
        files["cmp_written"] = os.path.exists(P["cmp"])
        files["second_run_blocked"] = bool(_existing_outputs(P))
        files["finished_marks"] = all(os.path.exists(P[k]) and FINISHED in _read_text(P[k]) for k in ("mark", "gitmark"))
        files["tag_file"] = os.path.exists(os.path.join(tmp, START_TAG))
        try:                                                 # 끝난 뒤 두 번째 시작은 표식 규칙이 막아야 한다(FINISHED)
            start_guard("SMOKE", None, [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)], None)
            files["restart_blocked"] = False
        except SystemExit:
            files["restart_blocked"] = True
        res["files"] = files
        b = res["steps"].get("bake") or {}
        res["ok"] = bool((res["steps"].get("f0") or {"ok": True})["ok"] and b.get("ok") and not b.get("unfrozen_modules")
                         and not b.get("registration_error") and all(files[k]["exists"] for k in ("out", "mark", "runlog", "public", "child", "gitmark"))
                         and files["second_run_blocked"] and files["finished_marks"] and files["restart_blocked"] and not files["cmp_written"]
                         and (b.get("cmp") or {}).get("refused_without_registration"))
    finally:
        _OVR.clear()
        _OVR.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)               # 열지 않고 지운다
        del sink
    res["deleted_unread"] = not os.path.exists(tmp)
    res["real_gitmark_absent"] = not os.path.exists(_git_mark_path())
    res["sec"] = round(time.time() - t0, 1)
    return res


# ══════════════════════════════════════════════════════════════════════════
#  합성 점검
# ══════════════════════════════════════════════════════════════════════════
def _fake_out():
    """게시 칸 누수 시험용 합성 산출 — L 층 칸마다 표지 수(0.123456 · 0.987654 · 0.345678 · 0.555555 · 0.777777)를 심는다."""
    import pandas as pd
    h1 = {"n": 120, "mean": 0.001, "ann": 0.012, "te": 0.02, "ir": 0.6, "t": 2.0, "t12": 1.9, "p": 0.02, "first": "2016-09", "last": "2026-08"}
    bd = {"h1": h1, "down": {"n": 40, "mean": 0.001, "win": 0.6}, "up": {"n": 80, "mean": 0.0}, "crash_m": {"n": 5, "mean": 0.002},
          "surge_m": {"n": 6, "mean": -0.001}, "crash_legs": {"n": 3, "mean": 0.01, "won": 2, "rows": [{"x": 0.01}]},
          "rebounds": {"n": 3, "mean": 0.0, "won": 1}, "named": {"crash 2020-02~2020-03": {"x": 0.003, "n": 2}},
          "years": {"rate": 0.6, "won": 6, "lost": 3, "ties": [], "partial": [2016, 2026], "n_full": 9, "years": {"2017": {"ex": 0.01}}},
          "roll36_neg": 0.2, "blocks4": [1, 2, 3, 4], "universe_breaks": {"1963-07": [0.123456, 0.1]}}
    st = {"n": 120, "h1_10": h1, "h1_20": h1, "h1_d0": h1, "h1_ew": h1, "g5e": True, "turn_1w": 2.5, "fid": {"n": 119, "rho": 0.345678, "gate": True},
          "s_point_pos_report": True, "bundle": bd, "G3_down_mean": 0.001}
    G = {"G2": {"crash_m": 0.123456, "surge_m": 0.123456, "ok": True, "rebound_miss": {"ok": True, "applies": True, "mean_dD": 0.123456, "months": ["1975-01"]}},
         "G3": {"down_mean": 0.123456, "ok": True}, "G5": {"a_blocks": True, "d_cost2x": True, "e_turn": True, "h_sync": True, "t1": None, "ok": True},
         "G6": {"a_rate": 0.123456, "a_ok": True, "ties": [], "partial": []}, "adopt_gates": True}
    Lr = {"window": ("1942-05", "2026-07"), "alpha": {"n": 1000, "a": 0.123456, "t": 0.987654, "p": 0.555555, "coef": [0.123456]},
          "alpha_LC": {"a": 0.123456, "t": 0.987654}, "placebo_rank": 0.777777, "rebound_miss": {"ok": True, "mean_dD": 0.123456}, "joint": True, "gates": G,
          "first_active": "1942-04", "strands": ["SLOW"], "static_h1": {"mean": 0.123456, "t": 0.987654},
          "delta": pd.Series([0.123456, 0.987654], index=pd.period_range("2000-01", periods=2, freq="M"))}
    return {"vbatch_full_out": True, "prereg": PREREG, "prereg_commit": "c" * 40, "decisions": {"use_sp": True}, "stopped": None,
            "lookahead": {"ok": True, "cond": {"SLOW": {"ok": True, "n": 200, "n_bad": 0}}, "pit": {"ok": True, "n": 194, "n_bad": 0, "seed": 1}},
            "comps": {"V01": {"spec": {"name": "MOM"}, "diag": {"F": {"n": 1}}, "tau_w": {"F": 3.0}}},
            "S": {"arms": {"V01": {"W": st, "S0": st}}, "delta": {"V01": {"h1": h1, "alpha_beta_adj": {"a": 0.001, "t": 1.0}}}, "twins": {"T-MOM-SN": {"arm": "W", "S": st}},
                  "alloc": {"FULL": st}, "alloc_delta": {"h1": h1}, "hygiene": {"rho": 0.99, "te_m": 0.002, "n": 120, "gate": True}},
            "L": {"cards": {"V01": Lr}, "alloc": Lr, "twins": {"T-MOM-PANIC": Lr},
                  "vintage": {"V01": {"window": ("1942-05", "2024-10"), "alpha": {"a": 0.123456, "t": 0.987654}, "same_sign": True}, "_note": "x"}},
            "H_V": {"members": ["V01", "V-A"], "holm": {"reject": {"V01": True, "V-A": False}, "threshold": {"V01": 0.555555}, "order": ["V01", "V-A"],
                                                        "alpha": 0.05, "m": 6}, "z_thresholds": [2.394, 2.326], "t": {"V01": 0.987654}},
            "joint": {"V01": True}, "fid": {"V01": True}, "adoption": {"V01": {"adopt": False}},
            "secondary_BY": {"admitted": ["X:V01"], "k": 1, "excluded": ["X:V08"]},
            "stouffer": {"z": 0.555555}, "dsr": {"V01": {"6": 0.777777}}, "n_arms": {"S_cards": 2}, "members_alloc": ["V01"], "anchor_ok": True}


def selftest():
    """합성 점검 — 판 점검이 빈 환경 · 가짜 커밋을 막는가 · 시작 표식 규칙 · 등록 상수 · 게시 칸 누수 · 직렬화 · 모듈 셈 · 경계 · F0 거르개 · 빈칸 · open() 인코딩."""
    res = []

    def chk(ok, msg):
        res.append(("✓" if ok else "✗", msg))

    def raises(fn):
        try:
            fn()
            return False
        except SystemExit:
            return True
    chk(raises(lambda: frozen_check({})), "VBATCH_COMMIT 없음 → 멈춤")
    if _N_PREREG == 1:
        chk(raises(lambda: frozen_check({"VBATCH_COMMIT": "0000000", "_VBATCH_NO_FETCH": "1"})), "없는 커밋 → 멈춤")
        head = _git("rev-parse", "HEAD").stdout.strip()
        chk(raises(lambda: frozen_check({"VBATCH_COMMIT": head, "_VBATCH_NO_FETCH": "1"})), "등록 문서를 처음 더한 커밋이 아님 → 멈춤")
    else:
        chk(raises(lambda: frozen_check({"VBATCH_COMMIT": "0000000", "_VBATCH_NO_FETCH": "1"})), "등록 문서가 하나가 아님 → 멈춤")
    # 시작 표식 규칙(모든 갈래)
    F = "f" * 40
    cases = [(lambda: start_guard(F, None, [], None), False), (lambda: start_guard(F, None, [("m", F + " t\n")], None), True),
             (lambda: start_guard(F, "사유", [("m", F + " t\n")], None), False), (lambda: start_guard(F, "사유", [], None), True),
             (lambda: start_guard(F, "사유", [("m", "e" * 40 + " t\n")], None), True), (lambda: start_guard(F, None, [], F), True),
             (lambda: start_guard(F, "사유", [("m", F + " t\n")], F), False), (lambda: start_guard(F, None, [], "e" * 40), True),
             (lambda: start_guard(F, "사유", [("m", F + " t\nFINISHED x\n")], None), True)]
    chk(all(raises(fn) == want for fn, want in cases), "시작 표식 규칙 9 갈래(FINISHED · 태그 · RERUN · 다른 커밋)")
    cb = registered_constants_ok()
    chk(not cb, "등록 상수 = 얼린 코드" + ("" if not cb else " — %s" % cb[:3]))
    # 게시 칸 누수
    pv = public_view(_fake_out(), "ab" * 32, 10, {"summary": {"n": 16, "mean": 0.001, "ann": 0.012, "t": 1.1, "first": "2016-09", "last": "2017-12",
                                                              "role": "x"}, "eg_inputs": {"data/x.json": "0.123456"}})
    js = json.dumps(_clean(pv), ensure_ascii=False)
    leaks = [v for v in ("0.123456", "0.987654", "0.345678", "0.555555", "0.777777", "__series__", '"rows"', "universe_breaks") if v in js]
    ok_pv = (not leaks and pv["vbatch_public_view"] and pv["H_V"]["reject"]["V01"] is True and pv["cards"]["V01"]["L"]["joint_parts"]["placebo_rank_ge_min"] is False
             and pv["cards"]["V01"]["S"]["W"]["h1_10"]["t"] == 2.0 and pv["cards"]["V01"]["S"]["W"]["fid_gate"] is True
             and pv["eg30_compare"]["n"] == 16 and pv["cards"]["V01"]["L"]["gates"]["G2"]["ok"] is True)
    ok_pv = ok_pv and pv["L_vintage_same_sign"] == {"V01": True} and pv["secondary_BY_excluded"] == ["X:V08"] and set(pv["eg30_compare"]) <= set(PUBLIC_CMP)
    chk(ok_pv, "게시 칸: L 층 α · t · p · 위약 순위 · 사건 · 계열 · FID 상관 · Stouffer · DSR · 판 민감도 값 · EG 입력 핀이 빠진다 · 비교 줄은 v_cmp 요약 칸만"
        + ("" if ok_pv else " — 샌 것 %s" % leaks))
    rd = result_doc(json.loads(js))
    leaks_rd = [v for v in ("0.123456", "0.987654", "0.345678", "0.555555", "0.777777") if v in rd]
    chk(not leaks_rd and "## H_V" in rd and "## L 층" in rd and "X:V08" in rd and "V08: 전방 전용" in rd,
        "결과 문서 렌더러(얼림): 게시 칸만 읽는다 · L 층 수치 누수 없음" + ("" if not leaks_rd else " — 샌 것 %s" % leaks_rd))
    try:
        result_doc({"x": 1})
        chk(False, "결과 문서 렌더러가 게시 칸이 아닌 파일을 받았다")
    except SystemExit:
        pass
    # 직렬화
    import numpy as np
    import pandas as pd
    s = _clean({"a": np.float64("nan"), "b": pd.Series([1.0], index=pd.period_range("2020-01", periods=1, freq="M")), ("x", 1): np.bool_(True)})
    chk(s == {"a": None, "b": {"__series__": {"2020-01": 1.0}}, "x|1": True}, "직렬화(NaN → None · 계열 · 튜플 열쇠)")
    # 모듈 셈 · 폐포 ⊆ 얼린 파일
    reach = sorted(VG.reach(VG.v_targets()) | VG.reach(["v_cmp"]))
    nf = ["build/%s.py" % m for m in reach if "build/%s.py" % m not in FROZEN]
    chk(not nf and unfrozen_modules(["build/v_run.py", "build/zz_x.py"]) == ["build/zz_x.py"], "전이 폐포(굽기 · v_cmp) ⊆ 얼린 파일 · 얼리지 않은 모듈 거르개"
        + ("" if not nf else " — 빠짐 %s" % nf))
    chk(unregistered_data(["data/stocks.json", "data/sd/AAPL.json", "data/zz.json"]) == ["data/zz.json"], "판 점검 밖 자료 거르개")
    # 경계
    g = site_guard()
    chk(g["ok"], "사이트 경계(v_guard · t_guard) 통과 — 파일 %s · 사이트 자료 %s" % (g.get("n_files"), g.get("n_scanned")) + ("" if g["ok"] else " — %s" % g["bad"][:3]))
    ne = VG.noeg_static()
    chk(ne["ok"] and "v_run" in ne["targets"], "G-NoEG 정적 전이(v_run 포함) — 닿은 로컬 %d · 적중 %d · 경계 %d" % (ne["n_reached"], len(ne["hits"]),
                                                                                                   len(ne["separate_violations"])))
    # F0 거르개
    good = {"kind": "vbatch_f0", "decisions": {k: None for k in F0_DECISION_KEYS}, "code_sha": {"build/v_x.py": "a"},
            "noeg_child": {"runtime": True, "open_audit": True}}
    good["decisions"].update({"prof": "op", "use_sp": True, "gcommon": False, "liq_emergency": False, "osap": False, "anchor_ok": True,
                              "anchor_resolution": "repaired", "gegd_pass": {c: True for c in ALL_CARDS}, "gegd_label": {c: None for c in ALL_CARDS},
                              "clusters": {"edges": [], "S_edges": {}, "global": {}}})
    bads = []
    for mut in (lambda d: d["decisions"].update(anchor_ok=False, anchor_resolution=None),                      # 앵커 거짓 → 굽지 않는다(accepted_failed 없음)
                lambda d: d["decisions"].update(anchor_ok=False, anchor_resolution="repaired"),                # 거짓인데 repaired 라벨 → 거부
                lambda d: d["decisions"].update(anchor_resolution="accepted_failed"),
                lambda d: d["decisions"].pop("clusters"),
                lambda d: d["decisions"]["gegd_pass"].pop("V08"),                                               # G-EGD 칸 없는 카드 → 거부(fail closed)
                lambda d: d["decisions"].update(clusters={"x": 1}),
                lambda d: d.update(noeg_child={"runtime": True, "open_audit": False})):
        b = json.loads(json.dumps(good))
        mut(b)
        bads.append(bool(f0_check(b)))
    chk(not f0_check(good, {"build/v_x.py": "a"}) and f0_check(good, {"build/v_x.py": "b"}) and all(bads) and f0_check({"kind": "x"}),
        "F0 거르개(결정 칸 · 앵커 관문 참만 · accepted_failed 없음 · G-EGD 칸 여덟 · 군 등록물 · 자식 G-NoEG · F0 코드 = 얼린 코드)")
    _decs = _decisions({"decisions": {"gegd_pass": {"V01": True}}})
    chk(_decs["gegd_pass"].get("V02", False) is False and _decs["gegd_pass"]["V01"] is True, "G-EGD 칸 없음 = 거짓(fail closed)")
    # 굽기 자식 판(검토 고침) — 러너 밖 직접 실행 · 가짜 표 · 등록 커밋이 아닌 커밋 · 연기 상한
    head = _git("rev-parse", "HEAD").stdout.strip()
    _od = os.path.join(VD.cache_guard(), "out")
    cg = [raises(lambda: child_gate("SMOKE", _od)), raises(lambda: child_gate("abc", _od)),
          raises(lambda: child_gate(head, _od, remote_tag=head, gitmark=os.path.abspath(__file__)))]
    sg_tmp = tempfile.mkdtemp(prefix="vbatch_runner_smoke_", dir=VD.cache_guard())
    try:
        so = os.path.join(sg_tmp, "out")
        sg = [not raises(lambda: smoke_gate(so, 3, 4, 20)), raises(lambda: smoke_gate(so, 1000, 4, 20)), raises(lambda: smoke_gate(so, 3, 200, 200)),
              raises(lambda: smoke_gate(os.path.join(VD.cache_guard(), "out"), 3, 4, 20)), raises(lambda: smoke_gate(os.path.join(sg_tmp, "elsewhere"), 3, 4, 20))]
    finally:
        shutil.rmtree(sg_tmp, ignore_errors=True)
    chk(all(cg) and all(sg), "굽기 자식 판: 연기 표 · 가짜 표 · 등록 문서를 처음 더하지 않은 커밋 → 멈춤 · 연기 폴더 · 위약 · 선견 상한")
    # VFWD 창세(검토 고침)
    gd = vfwd_genesis()
    cn = {k: v for k, v in code_shas().items() if k.startswith("build/v_")}
    g2 = json.loads(json.dumps(gd))
    g2["gates"]["constants"]["FF1_t"] = -0.5
    g3 = json.loads(json.dumps(gd))
    g3["cards"].pop("VF08S")
    chk(not vfwd_check(gd, cn) and vfwd_check(g2, cn) and vfwd_check(g3, cn) and vfwd_check(gd, dict(cn, **{"build/v_core.py": "x"}))
        and not VG.value_lists(gd) and gd["cards"]["VF08S"]["adoption"] == "forward_only" and "D29" in " ".join(gd["cards"]["VF08S"]["conditions"])
        and gd["cards"]["VF08S"].get("d29") == D29_CONFIRMATION and D29_CONFIRMATION["confirmed"] is True,
        "VFWD 창세: 카드 18 · 관문 상수 = v_tests.FF · 코드 핀 = 지금 코드 · 값 계열 없음 · VF08S 조건(G-EGD · D29 확인 2026-09-27 기록)")
    # 빈칸 셈 · 이름
    chk(placeholder_counts("a ⟨TBD⟩ b 〔초록〕 ⟨TBD") == (2, 1) and placeholder_counts("깨끗") == (0, 0), "등록 문서 빈칸 · 초안 괄호 셈")
    # F0 첫 활성(셈만) 합성
    idx = pd.period_range("1900-01", periods=400, freq="M")
    z = pd.DataFrame({"A": np.r_[np.full(100, np.nan), np.ones(300)]}, index=idx)
    y = {"S": pd.Series(np.ones(400), index=idx)}
    fa = f0_first_active(z, y, [("A", "S")])
    # 쌍 s: z(s) · z(s+1) 선 s ≥ 100 · σ̂(s) 선 s ≥ 37(값 36 ≥ 36 은 s−2 ≥ 35) · y(s+1) → 첫 유효 쌍 s = 100 · 누적 120 은 s = 219 → i = 222
    chk(fa["A"] == str(idx[222]), "F0 첫 활성 달(셈만 · 쌍 ≥ 120 · s ≤ i − 3)")
    # open() 인코딩 정적 점검
    import ast
    bad = []
    for nd in ast.walk(ast.parse(_read_text(os.path.abspath(__file__)))):
        if isinstance(nd, ast.Call) and getattr(nd.func, "id", getattr(nd.func, "attr", None)) == "open":
            kw = {k.arg for k in nd.keywords}
            mode = nd.args[1].value if len(nd.args) > 1 and isinstance(nd.args[1], ast.Constant) else ""
            if "encoding" not in kw and "b" not in str(mode):
                bad.append(nd.lineno)
    chk(not bad, "open() encoding 정적 점검" + ("" if not bad else " — 줄 %s" % bad))
    for st, msg in res:
        print("  %s %s" % (st, msg))
    n_ok = sum(1 for s_, _ in res if s_ == "✓")
    print("v_run selftest %d/%d 통과" % (n_ok, len(res)))
    return 0 if n_ok == len(res) else 1


if __name__ == "__main__":
    a = sys.argv
    if "--_bake-child" in a:
        raise SystemExit(_bake_child())
    if "--_f0-child" in a:
        raise SystemExit(_f0_child(a[a.index("--_f0-child") + 1]))
    if "--selftest" in a:
        raise SystemExit(selftest())
    if "--guard" in a:
        g = site_guard()
        ne = VG.noeg_static()
        print(json.dumps({"site": g, "noeg": {k: ne[k] for k in ("ok", "n_reached", "hits", "separate_violations", "dynamic_imports")}}, ensure_ascii=False, indent=1))
        raise SystemExit(0 if (g["ok"] and ne["ok"]) else 1)
    if "--pins" in a:
        print(json.dumps(pins_table(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    if "--init-cache-id" in a:
        print(json.dumps(init_cache_identity(), ensure_ascii=False))
        raise SystemExit(0)
    if "--f0" in a:
        r = f0()
        print(json.dumps(r, ensure_ascii=False))
        print(f0_table())
        raise SystemExit(0)
    if "--f0-table" in a:
        print(f0_table())
        raise SystemExit(0)
    if "--f0-resolve-anchor" in a:
        f0_resolve_anchor()
    if "--vfwd-genesis" in a:
        doc = vfwd_genesis()
        vl = VG.value_lists(doc)
        if vl:
            raise SystemExit("🚨 VFWD 창세에 값 계열 같은 숫자 목록: %s" % vl[:3])
        _write_text(os.path.join(ROOT, *VFWD_GENESIS.split("/")), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps({"path": VFWD_GENESIS, "cards": len(doc["cards"]), "code_pins": len(doc["code_pins"])}, ensure_ascii=False))
        raise SystemExit(0)
    if "--result-doc" in a:
        j = a.index("--result-doc")
        pp = a[j + 1] if len(a) > j + 1 and not a[j + 1].startswith("--") else paths()["public"]
        sys.stdout.write(result_doc(_read_json(pp)))
        raise SystemExit(0)
    if "--precommit" in a:
        print(json.dumps(precommit(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    if "--backup" in a:
        print(json.dumps(backup(), ensure_ascii=False))
        raise SystemExit(0)
    if "--restore" in a:
        print(json.dumps(restore(a[a.index("--restore") + 1]), ensure_ascii=False))
        raise SystemExit(0)
    if "--smoke" in a:
        r = smoke(with_f0="--no-f0" not in a)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        raise SystemExit(0 if r["ok"] else 1)
    if len(a) > 1:
        print(__doc__)
        raise SystemExit(2)
    main()
