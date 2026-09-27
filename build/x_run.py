# -*- coding: utf-8 -*-
"""build/x_run.py — 배치 X 한 번 굽기 러너: 얼린 판 점검(frozen_check) → 시작 표식 셋 → 굽기(선견 점검 → S 층 어댑터 → M · I · G · S 평가) →
저장소 밖 산출 · 게시 칸 · 실행 기록 → FINISHED. F0(개수 · 날짜 · 라벨 · 커버리지 · 해시만 — 수익 없음)도 이 파일이 만든다.

사전등록: build/PREREG-<등록 날짜>-XBATCH.md 하나(이 러너는 날짜를 박지 않는다 · 결과 문서 = 그 이름 + «-RESULT» · §6 이 이 파일을 설명한다 ·
  글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).
설계 원본(구속): xbatch_research.json(저장소 밖 스크래치) build_plan(x_run «--f0 · --once · --public-view · --selftest · --backup») · registration ·
  evaluation.rule_20y_compliance(«러너 단언 · 채점 보유월 최소 = 2006-09 · 입력 최소 날짜 ≥ 2005-08-01») · data_plan.F0_counts_only · user_answers(U1 a_op ½ · U2 경로 B).
  판정 식은 여기서 새로 쓰지 않는다 — build/x_eval · x_signals · x_blr · x_intl · x_adapter 의 함수를 명세 차례대로 부를 뿐이다.
🚨 사용자 갱신(2026-09-27 · 계산 전): «이런 불필요한 미래 일정들은 다 꺼 · QFWD까지 모두 끄라» — 전방 원장(XFWD) · 창세 파일(data/_xfwd/genesis.json) ·
   FF1 · FF2 · 날짜가 박힌 전방 판정을 만들지 않는다. 채택은 이 한 번 굽기의 표본 안 판정으로만 · 경로 B(보험 채택 후보면 결과 문서 다음 월말에 a_op ½ 로
   EG30 슬리브에 붙인다) · 보험료 한도(뒤 24개월 −0.40%p NAV · 누적 −0.60%p NAV)는 운용에서 감시하는 조건형 멈춤 규칙(x_eval.premium_cap_kill · 원장 없음).
   판 점검은 data/_xfwd/ 가 있으면 멈춘다(fail closed).
🚨 사용자 규칙(2026-09-27): 평가 창은 최근 20년까지 — 채점 보유월 2006-09 ~ 2026-08(240) · 입력 ≥ 2005-08-01(워밍업 · 추정 전용) · 공개 사이트 10년 ·
   20년 수치는 캐시(%TEMP%/xbatch_cache/out)에만 — 저장소 파일에는 쓰지 않는다(쓰기 가드 · public_safe · site_guard_std).
🚨 랩 규율: 등록 커밋 전에는 수익 · 초과수익 · 타이밍 통계 · 관문 값을 계산해서 찍지 않는다. --f0 은 개수 · 날짜 · 라벨 · 커버리지 · 해시 · 자료 충실도
   (명세 data_plan.F0_counts_only 가 허용한 상태 일치율 · D 대리 corr)만 · --smoke 는 눈가린 채(산출을 열지 않고 지운다 · 키 · 개수 · 참/거짓 · 초만).
   T01 C:bearonly 저장값(tbatch_cache/out · _tbatch.json)은 읽지 않는다(x_data 읽기 가드) · 신호 층에 EG30 입력 없음(x_eval.signal_guard).

  python -X utf8 build/x_run.py --selftest          합성만 — 판 점검 갈래 · 시작 표식 규칙 · 등록 상수 · 게시 칸 누수 · F0 거르개 · 빈칸 셈 · 폐포 ⊆ 얼린 파일 ·
                                                    경계(표준 라이브러리 판 = x_data 판) · 전방 원장 없음 · 20년 단언 · 직렬화 · 결과 문서 렌더러 · 덧붙임 덩이 · open() 인코딩
  python -X utf8 build/x_run.py --guard             사이트 경계(site_guard_std · x_data.site_guard · t_guard · v_guard — 참/거짓 · 이름만)
  python -X utf8 build/x_run.py --pins              얼린 파일 표(git blob · LF sha256) — 등록 문서 §6 표를 이 명령으로 만든다
  python -X utf8 build/x_run.py --init-cache-id     캐시 표지(<캐시>/meta/cache_id.txt · 없을 때만)
  python -X utf8 build/x_run.py --manifest [--lit <lit_open.json>]   data/_xb_manifest.json 에 «registration» 절(캐시 표지 · 문헌 기록 sha · 얼린 호출 핀 · 사용자 답 ·
                                                    전방 취소) — x_data --manifest · x_intl --manifest 뒤에(다른 절은 그대로)
  python -X utf8 build/x_run.py --f0                F0 → data/_xb_f0.json(공개 안전 · 등록 커밋이 더한다) + <캐시>/f0/xb_f0_full.json · 🚨 수익 · 켜짐 비율 없음
  python -X utf8 build/x_run.py --f0-table          data/_xb_f0.json → 등록 문서 §3.6 표(Markdown · 표준출력)
  python -X utf8 build/x_run.py --precommit         등록 커밋 직전 점검(참/거짓 · 이름만)
  python -X utf8 build/x_run.py --wire [--apply]    등록 커밋이 기존 파일(.gitignore · build/validate_site.py) 끝에 덧붙일 덩이(기본은 보이기만)
  python -X utf8 build/x_run.py --backup | --restore <캐시 뿌리>    고정본(캐시 raw · meta · f0 · lit)을 %TEMP% 밖 사적 폴더로
  python -X utf8 build/x_run.py --smoke             러너 경로 전체 눈가린 연기(F0 → 표식 → 굽기 → 게시 칸 → 실행 기록 → FINISHED · 산출은 임시 폴더에만 쓰고 열지 않고 지운다)
  XBATCH_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python -X utf8 build/x_run.py --once     한 번 굽기(이 길 하나뿐)
  python -X utf8 build/x_run.py --public-view       굽기 뒤: <캐시>/out/_xbatch.json → _xbatch.public.json 다시 쓰기(FINISHED 표식이 있을 때만 · 경로 · sha 만 찍는다)
  python -X utf8 build/x_run.py --result-doc [<_xbatch.public.json>] [--write]   결과 문서 본문(게시 칸 파일 하나만 읽는 얼린 렌더러 · --write 면 저장소 결과 문서로)

한 번 굽기 규약(v_run · t_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(실패하면 멈춘다).
  · XBATCH_COMMIT = 사전등록 문서 · 이 러너 · F0 문서(data/_xb_f0.json)를 **처음 더한** 커밋 · origin/main 의 조상 · 그 커밋의 등록 문서에 빈칸(⟨TBD)과 초안 괄호(U+3014)가 없다.
  · 얼린 파일(새 x_* · 명세 둘 + x_* 가 부르는 랩 모듈 폐포 + 경계 t_guard)이 그 커밋과 바이트 단위로 같다(CRLF 무시) · 굽기가 작업 트리에서 읽는 자료
    (X_LAB_FILES = 명세 둘뿐)가 그 커밋의 판과 같다 · 명세 SHA(x_data.check_pins · x_intl.check_pins) · 문헌 기록 sha · 캐시 표지 = 명세 ·
    배치 V 핀 판 임시 뿌리(x_adapter.vroot_check — 자료 핀 커밋 DATA_PIN 의 build/ + data/ · 파일 핀 20 · 폴더 요약 4 · 핀 커밋 넷이 origin/main 조상)가 선다 ·
    덧붙임 두 곳(.gitignore · validate_site)이 붙어 있다. 🔧 굽기는 작업 트리의 랩 자료(data/stocks · pit_px · rf_monthly …)를 읽지 않는다 —
    D 쪽은 vroot · V0 쪽은 코드 핀 뿌리 · 미국 · 국외 원자료는 캐시 고정본이라 등록 뒤 CI 가 data/ 를 갈아도 굽기 판이 같다(검토 반영 2026-09-27).
  · F0 문서가 끝났다(결정 칸 · 켜짐 비율 칸 없음 · F0 를 만든 코드 sha = 얼린 코드 · 명세 sha = 지금 명세).
  · 전방 원장이 없다(data/_xfwd/ 없음 — 사용자 갱신 2026-09-27).
  · 산출물이 없다 — 저장소 밖 산출 · 실행 기록 · origin/main 의 결과 문서 어느 것이든 있으면 다시 돌지 않는다(다시 굽기는 새 등록).
  · 시작 표식 셋 — 로컬 둘(<캐시>/out/_xbatch.started · git 공용 폴더의 xbatch_started)을 **무엇보다 먼저** 쓰고 origin 태그 refs/tags/xbatch-started(= 등록 커밋)를
    계산 **전에** 민다. 끝나면 두 로컬 표식에 «FINISHED <산출 sha256>». FINISHED 가 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤 · 산출 전 기술적 중단이면
    이 컴퓨터의 같은 커밋 표식이 있을 때만 XBATCH_RERUN=사유 로 처음부터(이어하기 없음).
  · PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 · numpy 2.5.3 · scipy 1.18.1 · pandas 3.0.6 · 등록 상수(REGISTERED)가 실행 때도 그대로.
  · 굽기는 이 과정 하나에서 돈다(작업자 ≤ 2 — 이 과정 + x_adapter 자식 하나씩 차례로 · 메모리 ≤ 3 GB). 산출은 저장소 밖(<캐시>/out):
    _xbatch.json(전부 · 20년 · 캐시 전용 표지) · _xbatch.public.json(결과 문서가 옮길 수 있는 칸만 — x_eval.public_view + 러너 칸 · public_safe) ·
    _xbatch.run.json(커밋 · 시각 · sha · 환경 · 판 · 불러온 build/ 모듈 · 열린 data/ 파일 · 등록 오류 — 값 없음).
    표준출력은 경로 · sha256 앞 16자 · 초만.
"""
from __future__ import annotations

import ast
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
# 🔒 모듈 머리에서는 표준 라이브러리만 — build/validate_site.py 가 site_guard_std 를 부른다(numpy · pandas 없이). x_* 는 함수 안에서만 불러온다.


# ══════════════════════════════════════════════════════════════════════════
#  등록 문서 · 얼린 파일 · 등록 상수
# ══════════════════════════════════════════════════════════════════════════
def _find_prereg():
    """등록 문서 — build/PREREG-<날짜>-XBATCH.md 하나(RESULT 는 이 글에 맞지 않는다). 둘 이상이거나 없으면 이름 점검이 멈춘다."""
    c = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-XBATCH.md")))
    return ("build/" + c[0]) if len(c) == 1 else "build/PREREG-0000-00-00-XBATCH.md", len(c)


PREREG, _N_PREREG = _find_prereg()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"                 # 결과 문서 = 등록 문서 이름 + «-RESULT»
RUNNER = "build/x_run.py"
F0_FILE = "data/_xb_f0.json"
MANIFEST_FILE = "data/_xb_manifest.json"
FIRST_ADDED = (PREREG, RUNNER, F0_FILE)                      # 🚨 전방 창세 없음(사용자 갱신 2026-09-27)
REPO_ALLOWED_X = (MANIFEST_FILE, F0_FILE)                    # 저장소 data/ 쪽 배치 X 파일은 이 둘뿐(x_data.REPO_ALLOWED 의 창세 칸은 쓰지 않는다 — 판 점검이 막는다)
FORWARD_DIR = "data/_xfwd"                                   # 있으면 멈춘다(전방 원장 취소)
NEW_FROZEN = ("build/x_data.py", "build/x_intl.py", "build/x_signals.py", "build/x_blr.py", "build/x_eval.py", "build/x_adapter.py", RUNNER,
              MANIFEST_FILE, F0_FILE)
# 가져다 쓰는 랩 모듈(고치지 않는다) — x_* 의 정적 import 폐포(함수 안 import · __import__ 상수 포함 · selftest 가 «폐포 ⊆ 얼린 파일» 을 본다) + 경계 t_guard.
#   S 자식은 코드 핀 1d81f083 의 build/ 를 임시 뿌리에서 쓴다(x_adapter.ROOT_FROZEN blob 단언 · 여기 표와 별개).
REUSED_MODULES = ("edgar", "eg30plus", "index_members", "ml_core", "ml_strats", "pit_alias", "pit_backtest", "pit_panel", "pit_quarantine", "q_bmrot_leg",
                  "q_jump", "q_switch", "qbatch_core", "qg_lab", "rally_pattern", "shares_clean", "shares_split", "stoploss", "t_pit", "tech_backtest",
                  "v_cards", "v_cond", "v_core", "v_data", "v_ear", "v_fund", "v_guard", "v_ins", "v_pit", "v_px_split", "t_guard",
                  "mech_episodes")                           # 마지막 = x_eval._frozen(이름) 의 변수 __import__(정적 폐포가 못 보는 것 · FROZEN_BLOBS 열쇠 — selftest 가 본다)
REUSED_FROZEN = tuple("build/%s.py" % m for m in REUSED_MODULES)
FROZEN = tuple(dict.fromkeys(NEW_FROZEN + REUSED_FROZEN))
X_MODULES = ("x_data", "x_intl", "x_signals", "x_blr", "x_eval", "x_adapter", "x_run")
# 굽기가 저장소 작업 트리에서 읽는 랩 자료 — x_data · x_intl · x_eval 이 읽는 것 + D 자식(v_data 명세 목록 · 배치 V F0 · 명세) + 이 배치의 명세 둘.
V_DATA_LAB_FILES = ("data/stocks.json", "data/pit_px.json", "data/_px_raw.json", "data/splits.json", "data/index_history.json", "data/index_ledger.json",
                    "data/pit_universe.json", "data/pit_reuse.json", "data/pit_gics_sectors.json", "data/earn_dates.json", "data/_ins_pit/cikmonth.json",
                    "data/_ins_pit/routine.json", "data/_ins_pit/manifest.json", "data/_tenq_rf.json", "data/_issuer_map.json", "data/_fxv/index.json",
                    "data/_fxv/manifest.json", "data/assets.json", "data/rf_monthly.json", "data/shares_yf.json")   # = v_data.LAB_FILES(selftest 대조)
V_DATA_LAB_DIRS = ("data/sd", "data/fx", "data/fx_pit", "data/_fxv")                                           # = v_data.LAB_DIRS
# 🔧 굽기가 작업 트리 data/ 에서 읽는 것은 이 배치 명세 둘뿐이다(검토 반영 2026-09-27 — CI 가 data/ 를 매일 가는 데 기대지 않는다):
#   rf_monthly · assets = x_data 캐시 고정본 · x_intl USD rf = 같은 고정본 · D 쪽(v_data 자료 목록 · 배치 V 명세) = x_adapter vroot(DATA_PIN) ·
#   V0 · mech_episodes = 코드 핀 뿌리(P3). 다른 data/ 파일을 열면 러너가 «판 점검 밖 랩 자료» 등록 오류로 적는다.
X_LAB_FILES = (MANIFEST_FILE, F0_FILE)
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"                    # 등록 문서 빈칸 · 초안 괄호 — 등록 커밋 판에 하나라도 있으면 굽지 않는다
LOOKAHEAD_MAIN, LOOKAHEAD_ARM = 200, 80                      # 굽기 앞 실자료 선견 점검(x_signals.lookahead_real · 엔진 단계와 같은 수)
SMOKE_CAPS = {"lookahead_main": 12, "lookahead_arm": 4}      # 연기 전용(굽기 판은 위 수 — 연기 경로로 온 약한 굽기를 막는다)
LIT_OPEN_CACHE = ("lit", "lit_open.json")                    # 문헌 열기 기록(저장소 밖 · 명세 registration 절에 sha)
SMOKE_ENV_KEYS = ("XBATCH_SMOKE",)
CUM_N_BEFORE = 945
# 등록 상수 — 얼린 코드의 값과 같아야 굽는다(명세 signals · evaluation · power.fixed_b_critical_values · user_answers · 자료 · 엔진 단계 선언)
REGISTERED = {
    "XD.SCORE_FIRST": "2006-09", "XD.SCORE_LAST": "2026-08", "XD.N_SCORE": 240, "XD.INPUT_MIN": "2005-08-01", "XD.INPUT_MIN_MONTH": "2005-08",
    "XD.WARMUP": ("2005-09", "2006-08"), "XD.HALVES": (("2006-09", "2016-08"), ("2016-09", "2026-08")), "XD.OUT_OF_LIT": ("2019-01", "2026-08"),
    "XD.GFC_EXCL": ("2007-10", "2009-06"), "XD.FULL_YEARS": (2007, 2025), "XD.S_WIN": ("2016-09", "2026-08"), "XD.S_PIT_FROM": "2014-06",
    "XD.PUBLIC_FROM": "2016-09", "XD.MAX_YEARS_PUBLIC": 10, "XD.VXV_PUB_DEFAULT": "2009-09-18", "XD.SEED": 20260927, "XD.LOOKAHEAD_N": 200,
    "XD.MIN_FIRMS": 20, "XD.CRSP_WANT": "202608", "XD.V_DATA_BLOB": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a",
    "XD.D_PROXY": ("me_beta", "BIG LoBETA"), "XD.D_PROXY_FALLBACK": ("beta", "Lo 20"),
    "XD.GROWTH_PROXIES": {"LG": ("p6_m", "BIG LoBM"), "EXG": ("beme", "Lo 10"), "MOM": ("me_prior12", "BIG HiPRIOR"), "QG": ("me_op", "BIG HiOP")},
    "XD.MIN_WARMUP_BY_ELEMENT": {"X-BEAR": "2006-08", "X-GVTREND": "2006-12", "X-BLR": "2010-08", "X-JM": "2008-08"},
    "XD.FORBIDDEN_READ_MARKS": ("tbatch_cache/out", "_tbatch.json", "_tbatch.public", "_tbatch.run", "_tbatch.child"),
    "XD.EG_FILE_MARKS": ("_eg_q5", "_eg30plus", "_qfwd", "_eg_best", "_idxeg", "_qbatch", "_qg_", "v0_pin", "_fund_card"),
    "XS.BEAR_SLOW": 12, "XS.BEAR_FAST": 1, "XS.BEAR_THR": 0.0, "XS.APP_MIN": 0.1, "XS.CRED_DAYS": 365, "XS.VTS_THR": 1.0, "XS.RR_TD": 63, "XS.RR_THR": 0.2,
    "XS.GV_TD": 252, "XS.GV_FIRST": "2006-12", "XS.SMA_N": 200, "XS.VOL_N": 63, "XS.VOL_MIN_OBS": 12, "XS.CW_SLOW": 252, "XS.CW_FAST": 21,
    "XS.JM_MIN": 756, "XS.JM_MAX": 3000, "XS.JM_FIT_MONTHS": ("01", "07"), "XS.Q_JUMP_BLOB": "b55652b5bf2db83e28e9e54480aa6254d20ffb95",
    "XS.ARM_STATUS": {"X-BEAR": "primary", "X-COMP": "measure", "X-CRED": "measure", "X-BLR": "measure", "X-JM": "measure", "X-COMP-W": "measure",
                      "X-VTS": "dropped", "X-GVTREND": "measure_FG", "X-RRSHOCK": "twin"},
    "XS.M_BY_FAMILY": ("X-COMP", "X-CRED", "X-BLR", "X-JM", "X-COMP-W"), "XS.FG_FAMILY": ("X-GVTREND",),
    "XB.FEATURES": ("TREND", "FAST", "CREDIT", "FEAR"), "XB.SIGNS": {"TREND": 1, "FAST": 1, "CREDIT": -1, "FEAR": 1}, "XB.PRIOR_SLOPE_SD": 0.25,
    "XB.PRIOR_INT_MEAN": 0.5, "XB.PRIOR_INT_SD": 0.5, "XB.MIN_TRAIN": 60, "XB.FIRST_ACTIVE_FLOOR": "2010-08",
    "XE.CRIT": {"T240_L6": 1.706, "T92_L3": 1.738, "T36_L3": 1.892, "T24_L3": 2.037}, "XE.NW_LAG": 6, "XE.KAPPA10": 0.004, "XE.KAPPA20": 0.008,
    "XE.COST10": 0.001, "XE.COST20": 0.002, "XE.D_REF": 0.05, "XE.SIGMA_PRE": 0.042903, "XE.MECH_EPISODES_BLOB": "d67a2a74b486aff7f3a46d0f2a9bebe104df669f",
    "XE.ZZ_HD": 0.1, "XE.ZZ_HU": 0.1, "XE.ZZ_REB": 63, "XE.ZZ_START": "2006-08-31", "XE.ZZ_END": "2026-08-31", "XE.EPISODE_GAP_TD": 126,
    "XE.RG_MAX": 0.5, "XE.I_BREADTH": 6, "XE.NI_LB": -0.3, "XE.Z80": 0.8416, "XE.S_TURN_MAX": 10.0, "XE.BY_Q": 0.1, "XE.PLACEBO_N": 1000,
    "XE.PLACEBO_SEED": 20260927, "XE.PLACEBO_BLOCK": 12, "XE.DIL_DOWN": 0.0982, "XE.DIL_CRASH": 0.233, "XE.LAB_T": 3.0, "XE.BONF_Z": 2.94,
    "XE.A_OP": 0.5, "XE.PATH": "B", "XE.PREMIUM_TRAIL_M": 24, "XE.PREMIUM_TRAIL_CAP": -0.4, "XE.PREMIUM_CUM_CAP": -0.6,
    "XE.DISCLOSE_B": "오염 창에서 고름 · 전방 미확인 · 보험 결정", "XE.CUM_N_BEFORE": 945, "XE.S_YEARS": (2017, 2025),
    "XE.FROZEN_BLOBS": {"eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628", "mech_episodes": "161080fd9244c060a7a94c559044de3e3ddcc27c"},
    "XE.LABELS": ("M 일관성 통과(오염 창)", "I 국외 재현", "방어 재현", "보험 채택 후보", "랩 발견(맥락)"),
    "XI.PRIMARY": ["JP", "GB", "DE", "FR", "IT", "CH", "SE", "CA", "AU", "KR"], "XI.SUBSTITUTES": ["NL", "ES"], "XI.RATE_TAIL_MAX": None,
    "XI.USD_SWITCH_AT": 3, "XI.PX_STALE_DAYS": 5, "XI.FX_STALE_DAYS": 7, "XI.SCORE": ("2006-09", "2026-08"), "XI.INPUT_MIN": "2005-08-01",
    "XA.CODE_PIN": "1d81f083a404c68e23d15a649ef6f0a340d4d95c", "XA.BUILD_TREE": "e221c9817b8baa4e225e0382ff4cf2c15fbcb8c8",
    "XA.VB_BOOKS_SHA": "c1aeff7df4d02c03742f224623f109e89bb6873ea8e18eaf6ff6f53862784c1b",
    "XA.V0_HASH_PIN": {"V0_LT": "ec0a2aa43f1efffa3d59b5d5b78268153a2bf7f36947ab2ed6345c61c0370202",
                       "V0_BL": "132008e66ddf2ef85ea3acf408ae213641f92a0a0a4f7ea3118b6963d2a3c077"},
    "XA.A_OP": 0.5, "XA.D_CAP": 0.2, "XA.D_MAP_MIN": 0.9, "XA.APP_MIN": 0.1, "XA.D_FIRST_DECISION": "2014-05", "XA.S_FORM": ("2016-08", "2026-07"),
    "XA.DBOOK_COSTS": (0.0, 0.001, 0.002), "XA.DATA_PIN": "c6a35ff0168e5ea21c2ab2d18680550452511a3a", "XA.VROOT_PATHS": ("build/", "data/"),
    "XE.LABEL_G_REF": "G 참고(대리 충실도 강등)", "XE.OP_M_FAIL": "그대로(EG30 V0)", "XD.REPO_ALLOWED": ("data/_xb_manifest.json", "data/_xb_f0.json"),
    "R.LOOKAHEAD_MAIN": 200, "R.LOOKAHEAD_ARM": 80, "R.CUM_N_BEFORE": 945,
}
REGISTERED_FUNCS = {"XE": ("run_all", "m_layer", "i_layer", "g_layer", "s_layer", "labels", "public_view", "premium_cap_kill", "delta_series", "m_arm"),
                    "XS": ("bear_state", "signal_frame", "lookahead_real"),
                    "XA": ("s_series", "bear_a_s_window", "d_check", "build_vroot", "vroot_check", "beta_c_rows")}


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록은 모두 저장소 밖(<캐시>/out)
# ══════════════════════════════════════════════════════════════════════════
CACHE = os.environ.get("XBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "xbatch_cache")
GIT_MARK_NAME = "xbatch_started"                             # 두 번째 시작 표식 — 저장소 git 공용 폴더(.git · 커밋되지 않는다)
START_TAG = "xbatch-started"                                 # 세 번째 시작 표식 — origin 태그(등록 커밋) · 계산 전에 민다
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}           # 연기 시험만 임시 폴더로 돌린다(진짜 캐시 · .git · origin 에 아무것도 남기지 않는다)
OUT_NAMES = {"out": "_xbatch.json", "mark": "_xbatch.started", "runlog": "_xbatch.run.json", "public": "_xbatch.public.json"}


def _norm(p):
    return os.path.normcase(os.path.abspath(os.fspath(p)))


def _inside(p, root):
    a, r = _norm(p), _norm(root)
    return a == r or a.startswith(r + os.sep)


def cache_guard_std(cache=None, root=None):
    c, r = cache or CACHE, root or ROOT
    if _inside(c, r) or _inside(r, c):
        raise SystemExit("🚨 캐시(%s)가 저장소(%s) 안이다 — 20년 수치 · 원자료는 저장소 밖에만." % (c, r))
    return os.path.abspath(c)


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
    d = _OVR["out"] or os.path.join(cache_guard_std(), "out")
    os.makedirs(d, exist_ok=True)
    return d


def paths(d=None):
    d = d or out_dir()
    P = {k: os.path.join(d, v) for k, v in OUT_NAMES.items()}
    P["dir"] = d
    P["gitmark"] = _git_mark_path()
    return P


def _existing_outputs(P):
    """산출 쪽 파일(표식 제외) — 있으면 한 번 굽기가 이미 쓰였다(`_xbatch*.json` 전부 · 잘린 · .part 파일도 «쓰였다»)."""
    have = [P["out"], P["runlog"], P["public"]]
    if os.path.isdir(P["dir"]):
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith("_xbatch") and (f.endswith(".json") or f.endswith(".part"))]
    return sorted({p for p in have if os.path.exists(p)})


def _sha_lf(b):
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def _bytes(p):
    return pathlib.Path(p).read_bytes()


def _read_text(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def _write_text(p, txt):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    os.replace(p + ".part", p)


def _read_json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def peak_mb():
    """최대 작업 메모리(MB · Windows) — v_run.peak_mb 와 같다(값이 아니다)."""
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
#  사이트 경계(표준 라이브러리만 — build/validate_site.py 가 부른다) · 공개 안전 점검 사본
# ══════════════════════════════════════════════════════════════════════════
CACHE_ONLY_KEY = "__xb_cache_only__"                        # = x_data.CACHE_ONLY_KEY(selftest 대조)
PUBLIC_FROM = "2016-09"
PUBLIC_FLOAT_KEYS = re.compile(r"(^|_)(coverage|frac|tol|min|max|thr|sec)(_|$)")      # = x_data(검토 반영 — 20년 창 켜짐 비율 · 일치율 · corr 은 캐시에만)
COUNT_KEYS = re.compile(r"(^n$|^n_|_n$|count|^k$|switch|months?$|days?$|legs?$|episodes?$|years?$|^rows$|bytes$)")
LICENSED_NAME_MARKS = ("F-F_Research_Data_Factors", "Portfolios_Formed_on_", "6_Portfolios_", "25_Portfolios_", "_History.csv",
                       "fredgraph", "alfredgraph", "xbatch_cache", "F-F_International_Countries", "IR3TIB01", "OECD.SDD")
OUTPUT_NAME_MARKS = ("_xbatch",)
OUTPUT_CONTENT_MARKS = (CACHE_ONLY_KEY.encode(), b"_xbatch.json", b"_xbatch.public.json", b"_xbatch.run.json", b'"xbatch_public_view"')


def _value_lists(doc, path="", max_len=4):
    out = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            out += _value_lists(v, path + "/" + str(k), max_len)
    elif isinstance(doc, (list, tuple)):
        nums = [x for x in doc if isinstance(x, (int, float)) and not isinstance(x, bool)]
        if len(nums) > max_len:
            out.append(path or "/")
        for x in doc:
            out += _value_lists(x, path + "[]", max_len)
    return out


def _win_start(d):
    for k in ("window", "win", "span"):
        w = d.get(k)
        if isinstance(w, (list, tuple)) and w and isinstance(w[0], str):
            return w[0][:7]
        if isinstance(w, str) and re.match(r"\d{4}-\d{2}", w):
            return w[:7]
    return None


def public_safe_std(doc, path="", inherited=None):
    """x_data.public_safe 의 표준 라이브러리 사본(selftest 가 같은 답을 내는지 본다)."""
    bad = []
    if isinstance(doc, dict):
        if doc.get(CACHE_ONLY_KEY):
            bad.append("%s: 20년 표지(%s)" % (path or "/", CACHE_ONLY_KEY))
        ws = _win_start(doc)
        here = ws if ws is not None else inherited
        for k, v in doc.items():
            p = path + "/" + str(k)
            if isinstance(v, float) and not isinstance(v, bool) and here is not None and here < PUBLIC_FROM:
                if not (PUBLIC_FLOAT_KEYS.search(str(k)) or (math.isfinite(v) and v == int(v) and COUNT_KEYS.search(str(k)))):
                    bad.append("%s: 창 %s(2016-09 앞 시작) 안의 실수 값" % (p, here))
            elif isinstance(v, (dict, list, tuple)):
                bad += public_safe_std(v, p, here)
    elif isinstance(doc, (list, tuple)):
        for x in doc:
            if isinstance(x, (dict, list, tuple)):
                bad += public_safe_std(x, path + "[]", inherited)
            elif isinstance(x, float) and inherited is not None and inherited < PUBLIC_FROM:
                bad.append("%s[]: 창 %s 안의 실수 값" % (path, inherited))
    if path == "":
        bad += ["%s: 값 계열 같은 숫자 목록" % p for p in _value_lists(doc)]
    return bad


def scan_repo_names(files):
    """파일 이름 규칙(순수 · selftest 대상) — 라이선스 원자료 이름 · 굽기 산출 이름 · 허용 밖 data/_xb* · 전방 원장(data/_xfwd/)."""
    bad = []
    for f in files:
        b = os.path.basename(f)
        if any(mk in f for mk in LICENSED_NAME_MARKS):
            bad.append("라이선스 원자료로 보이는 파일: %s" % f)
        if any(b.startswith(mk) for mk in OUTPUT_NAME_MARKS):
            bad.append("굽기 산출 이름: %s" % f)
        if f.startswith("data/_xb") and f not in REPO_ALLOWED_X:
            bad.append("허용 밖 파일: %s" % f)
        if f.startswith(FORWARD_DIR + "/") or f == FORWARD_DIR:
            bad.append("전방 원장 파일(사용자 갱신 2026-09-27 로 취소): %s" % f)
    return bad


def site_guard_std(root=None):
    """배치 X 사이트 경계(표준 라이브러리만) — git 이 추적 · 추가 예정인 파일 가운데 (가) 라이선스 원자료 이름 (나) 굽기 산출 이름(_xbatch*)
    (다) 허용 밖 data/_xb* (라) 전방 원장 data/_xfwd/* (마) 허용 파일 둘의 공개 안전 점검 (바) 사이트 자료(뿌리 *.html · js/*.js · data/*.json)의 굽기 산출 표식."""
    root = root or ROOT
    p = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return {"ok": False, "bad": ["git ls-files 실패"], "n_bad": 1, "n_files": 0, "n_scanned": 0}
    files = [x for x in p.stdout.splitlines() if x]
    bad = scan_repo_names(files)
    if os.path.isdir(os.path.join(root, *FORWARD_DIR.split("/"))):
        bad.append("전방 원장 폴더 %s 가 있다(무시 파일 포함 · 사용자 갱신으로 취소)" % FORWARD_DIR)
    for f in REPO_ALLOWED_X:
        fp = os.path.join(root, *f.split("/"))
        if f in files and os.path.exists(fp):
            try:
                probs = public_safe_std(_read_json(fp))
            except Exception as e:                            # noqa: BLE001
                probs = ["읽지 못함(%s)" % type(e).__name__]
            bad += ["%s: %s" % (f, x) for x in probs[:3]]
    scan = [f for f in files if (("/" not in f and f.endswith(".html")) or (f.startswith("js/") and f.endswith(".js"))
                                 or (f.startswith("data/") and f.endswith(".json") and f.count("/") == 1))]
    n_scanned = 0
    for f in scan:
        fp = os.path.join(root, f)
        if not os.path.isfile(fp):
            continue
        with open(fp, "rb") as fh:
            blob = fh.read()
        n_scanned += 1
        hit = [m.decode() for m in OUTPUT_CONTENT_MARKS if m in blob]
        if hit:
            bad.append("사이트 자료 %s 에 배치 X 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


def site_guard():
    """러너 경계 — 표준 라이브러리 판 + x_data.site_guard + 배치 T · V 경계(같은 저장소)."""
    import t_guard as TG
    import v_guard as VG
    XD = _mods()["XD"]
    g0, g1, gt, gv = site_guard_std(ROOT), XD.site_guard(ROOT), TG.site_guard(ROOT), VG.site_guard(ROOT)
    bad = list(g0["bad"]) + ["[x_data] " + b for b in g1["bad"]] + ["[T] " + b for b in gt["bad"]] + ["[V] " + b for b in gv["bad"]]
    return {"ok": bool(g0["ok"] and g1["ok"] and gt["ok"] and gv["ok"]), "bad": bad, "n_files": g0.get("n_files"), "n_scanned": g0.get("n_scanned")}


def wired_state(root=None):
    """덧붙임 두 곳(.gitignore 배치 X 덩이 · validate_site 배치 X 경계)이 붙어 있는가 — (gitignore, validate_site)."""
    root = root or ROOT
    gt, vt = _read_text(os.path.join(root, ".gitignore")), _read_text(os.path.join(root, "build", "validate_site.py"))
    g1, v1 = wire_texts(gt, vt)
    return g1 == gt, v1 == vt


def check_no_forward(root=None):
    """전방 원장 없음(사용자 갱신 2026-09-27) — data/_xfwd/ 폴더 · 창세 파일이 있으면 문제."""
    root = root or ROOT
    d = os.path.join(root, *FORWARD_DIR.split("/"))
    return (["전방 원장 폴더가 있다: %s" % FORWARD_DIR] if os.path.exists(d) else [])


# ══════════════════════════════════════════════════════════════════════════
#  모듈 · 등록 상수 · 판
# ══════════════════════════════════════════════════════════════════════════
_M = {}


def _mods():
    if not _M:
        import x_data as XD
        import x_signals as XS
        import x_blr as XB
        import x_eval as XE
        import x_intl as XI
        import x_adapter as XA
        _M.update({"XD": XD, "XS": XS, "XB": XB, "XE": XE, "XI": XI, "XA": XA, "R": sys.modules[__name__]})
    return _M


def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def _normv(x):
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            x = x.tolist()
    except Exception:                                        # noqa: BLE001
        pass
    if isinstance(x, (list, tuple)):
        return tuple(_normv(v) for v in x)
    if isinstance(x, dict):
        return {k: _normv(v) for k, v in x.items()}
    if isinstance(x, float):
        return round(x, 15)
    return x


def registered_constants_ok():
    M = _mods()
    bad = []
    for k, want in REGISTERED.items():
        mod, attr = k.split(".", 1)
        have = getattr(M[mod], attr, "<없음>")
        if _normv(have) != _normv(want):
            bad.append("%s = %r (등록 %r)" % (k, have, want))
    same = lambda a, b: _norm(a or "") == _norm(b or "")
    for mod, names in REGISTERED_FUNCS.items():
        m = M[mod]
        for nm in names:
            fn = getattr(m, nm, None)
            if getattr(fn, "__qualname__", "") != nm or not same(getattr(getattr(fn, "__code__", None), "co_filename", ""), m.__file__):
                bad.append("%s.%s 이 덮어쓰였다" % (mod, nm))
    XE = M["XE"]
    for nm in ("ff1", "ff2", "ff0", "xfwd_genesis"):
        if hasattr(XE, nm):
            bad.append("x_eval.%s 가 있다(전방 판정 취소)" % nm)
    for k in SMOKE_ENV_KEYS:
        if os.environ.get(k):
            bad.append("연기 전용 환경 변수 %s 가 켜져 있다" % k)
    return bad


def placeholder_counts(text):
    return text.count(PLACEHOLDER), text.count(DRAFT_MARK)


def name_check():
    bad = []
    if _N_PREREG != 1:
        bad.append("build/PREREG-*-XBATCH.md 가 %d 개" % _N_PREREG)
    elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-XBATCH\.md", PREREG):
        bad.append("이름 꼴: %s" % PREREG)
    return bad


def _manifest():
    p = os.path.join(ROOT, *MANIFEST_FILE.split("/"))
    return _read_json(p) if os.path.exists(p) else {}


def check_cache_identity():
    want = ((_manifest().get("registration") or {}).get("cache_identity") or {}).get("sha256")
    p = os.path.join(cache_guard_std(), "meta", "cache_id.txt")
    have = _sha_file(p) if os.path.exists(p) else None
    if not want or not have:
        return False, "캐시 표지가 없다(명세 %s · 캐시 %s — --init-cache-id 뒤 --manifest)" % (bool(want), bool(have))
    return have == want, ("캐시 표지 = 명세" if have == want else "캐시 표지가 명세와 다르다 — 등록한 캐시 뿌리에서만 굽는다")


def init_cache_identity():
    p = os.path.join(cache_guard_std(), "meta", "cache_id.txt")
    if os.path.exists(p):
        return {"created": False, "sha256_16": _sha_file(p)[:16]}
    _write_text(p, "xbatch_cache %s %s\n" % (secrets.token_hex(32), time.strftime("%Y-%m-%dT%H:%M:%S")))
    return {"created": True, "sha256_16": _sha_file(p)[:16], "next": "python -X utf8 build/x_run.py --manifest"}


def lit_open_path():
    return os.path.join(cache_guard_std(), *LIT_OPEN_CACHE)


def check_lit_open():
    """문헌 열기 기록(캐시 · 저장소 밖) sha = 명세 · 팔 판정이 x_signals.ARM_STATUS 와 같은가(쌍둥이 · 삭제 · 유지)."""
    bad = []
    reg = (_manifest().get("registration") or {}).get("lit_open") or {}
    p = lit_open_path()
    if not os.path.exists(p):
        return ["문헌 열기 기록이 캐시에 없다(--manifest --lit <경로>)"]
    if _sha_file(p) != reg.get("sha256"):
        bad.append("문헌 열기 기록 sha 가 명세와 다르다")
    doc = _read_json(p)
    ad = doc.get("arm_decisions") or {}
    XS = _mods()["XS"]
    want = {"X-RRSHOCK": "twin", "X-VTS": "dropped", "X-GVTREND": "measure_FG", "X-COMP": "measure"}
    for arm, st in want.items():
        if XS.ARM_STATUS.get(arm) != st:
            bad.append("ARM_STATUS[%s] = %s(등록 %s)" % (arm, XS.ARM_STATUS.get(arm), st))
        if arm not in ad:
            bad.append("문헌 기록에 %s 판정이 없다" % arm)
    return bad


def code_shas(paths_=None):
    """F0 · 굽기가 쓰는 코드의 LF sha(앞 16자) — F0 문서가 «얼린 코드로 만들어졌는가» 를 판 점검이 본다."""
    out = {}
    for p in (paths_ or [x for x in FROZEN if x.startswith("build/")]):
        fp = os.path.join(ROOT, *p.split("/"))
        out[p] = _sha_lf(_bytes(fp))[:16] if os.path.exists(fp) else None
    return out


def manifest_sha():
    p = os.path.join(ROOT, *MANIFEST_FILE.split("/"))
    return _sha_lf(_bytes(p))[:16] if os.path.exists(p) else None


F0_DECISION_KEYS = ("d_proxy", "g_binding", "vxv_pub_in_force", "vxv_evidence", "intl_mode", "intl_markets", "alfred_first_release", "french_last_month",
                    "d_sel_hash", "d_pairing_A", "s_cov_ok", "state_agree_pass", "lookahead_real_prior", "d_data_pin")


def f0_check(doc, code_now=None, man_now=None):
    """F0 문서 거르개(순수 · selftest 대상) — 결정 칸이 모두 있고 · 켜짐 비율 칸이 없고 · I 층 판정이 보류가 아니고 · 만든 코드 = 지금 코드. 돌려주는 것 문제 목록."""
    bad = []
    if not isinstance(doc, dict) or doc.get("kind") != "xbatch_f0":
        return ["F0 문서 꼴이 아니다"]
    dec = doc.get("decisions") or {}
    miss = [k for k in F0_DECISION_KEYS if k not in dec]
    if miss:
        bad.append("F0 결정 칸 없음: %s" % ", ".join(miss))
    if dec.get("d_proxy") not in ("main", "fallback"):
        bad.append("D 대리 결정이 main · fallback 이 아니다(%r)" % dec.get("d_proxy"))
    if dec.get("intl_mode") not in ("local", "usd"):
        bad.append("I 층 판정이 local · usd 가 아니다(%r)" % dec.get("intl_mode"))
    if not (isinstance(dec.get("intl_markets"), list) and len(dec.get("intl_markets")) == 10):
        bad.append("I 층 시장이 10 개가 아니다")
    if dec.get("alfred_first_release") is not False:
        bad.append("ALFRED 판 개정이 보였다(첫 공표 판 규칙) — 러너에 그 갈래가 없어 굽지 않는다(새 등록)")
    if not (isinstance(dec.get("d_sel_hash"), str) and re.fullmatch(r"[0-9a-f]{64}", dec.get("d_sel_hash") or "")):
        bad.append("D 선정 해시가 없다")
    if dec.get("d_pairing_A") is not True:
        bad.append("D 짝맞춤 A(배치 V F0 넘김과 같음)가 참이 아니다")
    for k in ("g_binding", "vxv_evidence", "s_cov_ok", "state_agree_pass"):
        if k in dec and not isinstance(dec[k], bool):
            bad.append("%s 가 참/거짓이 아니다" % k)
    if not isinstance(doc.get("intl"), dict) or (doc["intl"].get("decision") or {}).get("mode") != dec.get("intl_mode"):
        bad.append("I 층 F0 블록(intl)이 없거나 판정이 결정 칸과 다르다")
    txt = json.dumps(doc, ensure_ascii=False)
    if re.search(r'"[^"]*(on_share|share_on|on_ratio|ratio_on)[^"]*"\s*:', txt):
        bad.append("F0 에 켜짐 비율 칸이 있다(명세 «무조건 켜짐 비율은 싣지 않는다 · 굽기에서만»)")
    probs = public_safe_std(doc)
    if probs:
        bad.append("F0 가 공개 안전 점검에 걸렸다: %s" % "; ".join(probs[:3]))
    if code_now is not None:
        diff = sorted(p for p, s in (doc.get("code_sha") or {}).items() if code_now.get(p) != s)
        miss_c = sorted(set(code_now) - set(doc.get("code_sha") or {}))
        if diff or miss_c or not doc.get("code_sha"):
            bad.append("F0 를 만든 코드가 지금 코드와 다르다(%s …) — 얼린 코드로 --f0 를 다시" % ", ".join((diff + miss_c)[:3]))
    if man_now is not None and doc.get("manifest_sha16") != man_now:
        bad.append("F0 를 만든 때의 명세가 지금 명세와 다르다 — --f0 를 다시")
    return bad


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
    """marks = [(경로, 글)] · remote_tag = origin 시작 태그의 커밋 | None — v_run.start_guard 와 같은 갈래."""
    if any(FINISHED in txt for _, txt in marks):
        raise SystemExit("🚨 굽기가 이미 끝났다(시작 표식에 %s 줄) — 산출을 지웠어도 · XBATCH_RERUN 이어도 다시 돌지 않는다(다시 굽기는 새 등록)." % FINISHED)
    if remote_tag is not None and remote_tag != full:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다 — 다시 굽기는 새 등록." % remote_tag[:8])
    if marks and not rerun:
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 XBATCH_RERUN=사유 로 처음부터(이어하기는 없다)."
                         % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 XBATCH_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다.")
    if rerun and not all(txt.startswith(full) for _, txt in marks):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    if remote_tag is not None and not rerun:
        raise SystemExit("🚨 origin 에 시작 태그(%s)가 있다 — 한 번 굽기가 이미 시작됐다(이 컴퓨터의 산출 전 중단이면 XBATCH_RERUN)." % START_TAG)
    return True


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def frozen_check(env=None):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("XBATCH_COMMIT")
    if not c:
        raise SystemExit("🚨 XBATCH_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --pins · --f0 · --precommit · --smoke 만 된다.")
    nb = name_check()
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_XBATCH_NO_FETCH"):
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
    if n_ph or n_dm or not txt:
        raise SystemExit("🚨 등록 커밋의 사전등록 문서에 빈칸 %s⟩ %d · 초안 괄호(U+3014) %d 가 남았다(또는 문서 없음)." % (PLACEHOLDER, n_ph, n_dm))
    if _git("cat-file", "-e", "%s:%s" % (full, FORWARD_DIR)).returncode == 0:
        raise SystemExit("🚨 등록 커밋에 전방 원장(%s)이 있다 — 사용자 갱신(2026-09-27)으로 취소됐다." % FORWARD_DIR)
    fw = check_no_forward()
    if fw:
        raise SystemExit("🚨 %s" % "; ".join(fw))
    P = paths()
    if _inside(P["dir"], ROOT):
        raise SystemExit("🚨 산출 폴더가 저장소 안이다: %s" % P["dir"])
    outs = _existing_outputs(P)
    if outs:
        raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다(다시 굽기는 새 등록)." % ", ".join(os.path.basename(o) for o in outs))
    if _git("cat-file", "-e", "origin/main:" + RESULT).returncode == 0:
        raise SystemExit("🚨 origin/main 에 결과 문서가 이미 있다 — 다시 굽기는 새 등록.")
    ci, cmsg = check_cache_identity()
    if not ci:
        raise SystemExit("🚨 %s." % cmsg)
    rerun = env.get("XBATCH_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag() if (real or not env.get("_XBATCH_NO_FETCH")) else env.get("_XBATCH_REMOTE_TAG")
    start_guard(full, rerun, marks, remote)
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True)
        if want.returncode != 0:
            raise SystemExit("🚨 %s 가 등록 커밋에 없다." % p)
        if not os.path.exists(fp) or _sha_lf(_bytes(fp)) != _sha_lf(want.stdout):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    if _git("diff", "--quiet", full, "--", *X_LAB_FILES).returncode != 0:
        raise SystemExit("🚨 굽기가 읽는 명세 둘이 등록 커밋의 판과 다르다 — 등록 커밋을 꺼낸 작업 트리에서 굽는다.")
    gw, vw = wired_state()
    if not (gw and vw):
        raise SystemExit("🚨 덧붙임 두 곳이 붙지 않았다(.gitignore %s · validate_site %s) — `x_run.py --wire --apply` 를 등록 커밋에." % (gw, vw))
    for p in (".gitignore", "build/validate_site.py"):
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True)
        if want.returncode != 0 or _sha_lf(_bytes(os.path.join(ROOT, *p.split("/")))) != _sha_lf(want.stdout):
            raise SystemExit("🚨 %s 가 등록 커밋과 다르다(덧붙임이 등록 커밋에 들어가야 한다)." % p)
    M = _mods()
    pd_ = M["XD"].check_pins()
    if not pd_["ok"]:
        raise SystemExit("🚨 자료 고정본이 명세와 다르다(x_data): %s" % "; ".join(pd_["bad"][:5]))
    pi = M["XI"].check_pins()
    if not pi["ok"]:
        raise SystemExit("🚨 국외 고정본이 명세와 다르다(x_intl): %s" % "; ".join(pi["bad"][:5]))
    vr = M["XA"].vroot_check()                               # 배치 V 핀 판 임시 뿌리 — 시작 태그 전에(검토 반영 · CI 의 data/ 갱신과 무관한지)
    if not vr["ok"]:
        raise SystemExit("🚨 배치 V 핀 판 임시 뿌리(vroot) 점검 실패: %s" % "; ".join(vr["bad"][:3]))
    lb = check_lit_open()
    if lb:
        raise SystemExit("🚨 문헌 열기 기록: %s" % "; ".join(lb[:3]))
    f0d = load_f0()
    fb = f0_check(f0d, code_shas(), manifest_sha())
    if fb:
        raise SystemExit("🚨 F0 문서: %s" % "; ".join(fb[:4]))
    if ((f0d or {}).get("decisions") or {}).get("d_data_pin") != M["XA"].DATA_PIN:
        raise SystemExit("🚨 F0 의 D 자료 핀이 x_adapter.DATA_PIN 과 다르다.")
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
    return full


# ══════════════════════════════════════════════════════════════════════════
#  직렬화 · 모듈 셈
# ══════════════════════════════════════════════════════════════════════════
def _clean(o, depth=0):
    """산출 → 올바른 JSON(NaN · inf → None · 계열 {"__series__"} · 표 {"__frame__"} · 기간 · 날짜 → 글자 · 사전 열쇠 → 글자) — v_run._clean 과 같다."""
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


def data_files_opened(opened):
    base = _norm(os.path.join(ROOT, "data")) + os.sep
    out = set()
    for p in opened:
        a = _norm(p)
        if a.startswith(base):
            out.add("data/" + os.path.relpath(a, os.path.join(ROOT, "data")).replace(os.sep, "/"))
    return sorted(out)


def unregistered_data(files):
    reg = [x.lower() for x in X_LAB_FILES]
    return [f for f in files if not any(f.lower() == r or f.lower().startswith(r.rstrip("/") + "/") for r in reg)]


def static_closure(roots=X_MODULES):
    """x_* 의 정적 import 폐포(build/ 안 모듈 · 함수 안 import · __import__ 상수 · importlib.import_module 상수 포함)."""
    def imps(m):
        with io.open(os.path.join(HERE, m + ".py"), encoding="utf-8") as f:
            src = f.read()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            t = ast.parse(src)
        out = set()
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                out |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                out.add(n.module.split(".")[0])
            elif isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                fn = n.func
                nm = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if nm in ("__import__", "import_module"):
                    out.add(n.args[0].value.split(".")[0])
        return {x for x in out if os.path.exists(os.path.join(HERE, x + ".py"))}
    seen, st = set(), list(roots)
    while st:
        m = st.pop()
        if m in seen:
            continue
        seen.add(m)
        st += list(imps(m))
    return sorted(seen)


# ══════════════════════════════════════════════════════════════════════════
#  굽기(🚨 수익 통계 — 등록 커밋 뒤 굽기와 눈가린 연기에서만 · 값은 찍지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _decisions(doc):
    d = dict((doc or {}).get("decisions") or {})
    return {"dproxy_fallback": d.get("d_proxy") == "fallback", "d_sel_hash": d.get("d_sel_hash"), "intl_mode": d.get("intl_mode"),
            "intl_markets": d.get("intl_markets")}


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
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다(%s) — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 XBATCH_RERUN)."
                         % (r2.stderr or r1.stderr).strip()[:160])
    return "pushed"


def _mark_finished(P, sha):
    line = "%s %s %s\n" % (FINISHED, sha, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):
        with io.open(m, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)


def compute(dec, smoke=False, clock=None):
    """굽기 본체 — 선견 점검(실자료 · 참/거짓) → S 층(x_adapter 자식 · 얼린 V0 · D 책) → M · I · G · S(x_eval.run_all · 신호 층은 signal_guard 안).
    돌려주는 것 dict(20년 · 캐시 전용). 멈춤이면 {"stopped": 사유, …}."""
    M = _mods()
    XS, XE, XA = M["XS"], M["XE"], M["XA"]
    clock = clock if clock is not None else {}
    t = time.time()
    nm, na = (SMOKE_CAPS["lookahead_main"], SMOKE_CAPS["lookahead_arm"]) if smoke else (LOOKAHEAD_MAIN, LOOKAHEAD_ARM)
    with XE.signal_guard():
        la = XS.lookahead_real(n_main=nm, n_arm=na)
    clock["lookahead"] = round(time.time() - t, 1)
    la_ok = all(v.get("ok") for v in la.values())
    if not la_ok:
        return {"stopped": "lookahead", "lookahead": la}
    t = time.time()
    p = os.path.join(XA.s_dir(), "_s_series.bake.tmp.json")
    with XE.signal_guard():                                  # S 층 a 도 신호 층 가드 안에서(EG30 산출 열기 차단 · 검토 반영) — M 층 a 와 같음은 x_eval.run_all 이 단언
        a_s = XA.bear_a_s_window()
    rep = XA.s_series(a_s, p)
    S = XA._rjson(p)
    os.remove(p)                                             # S 계열은 메모리로만(값은 x_eval 이 관문에 쓴다)
    clock["S_adapter"] = round(time.time() - t, 1)
    sel = (rep.get("d_check") or {}).get("sel_hash")
    if dec.get("d_sel_hash") and sel != dec["d_sel_hash"]:
        return {"stopped": "d_sel_hash", "lookahead": la, "s_adapter": {"sel_hash_same_as_f0": False}}
    t = time.time()
    out = XE.run_all(dproxy_fallback=bool(dec.get("dproxy_fallback")), intl=True, S=S)
    clock["evaluate"] = round(time.time() - t, 1)
    out["lookahead"] = la
    out["s_adapter"] = {"pairing": rep.get("pairing"), "d_check": {k: v for k, v in (rep.get("d_check") or {}).items() if k != "sel_hash"},
                        "sel_hash_same_as_f0": (sel == dec.get("d_sel_hash")) if dec.get("d_sel_hash") else None}
    if out.get("I") and dec.get("intl_markets") and list(out["I"].get("markets") or []) != list(dec["intl_markets"]):
        out["registration_note_intl"] = "I 층 시장이 F0 판정과 다르다"
    del S
    return out


def public_doc(out, sha=None, nbytes=None, rec=None):
    """게시 칸(결과 문서가 옮길 수 있는 칸만) — x_eval.public_view(라벨 · 관문 불리언 · 창 · n · 켜짐 비율 · 2016-09 ~ 2026-08 반쪽 · S 요약) + 러너 칸.
    20년 수치 · G 값 · 계열 없음(public_safe_std · x_data.public_safe 둘 다 통과해야 쓴다)."""
    XD, XE = _mods()["XD"], _mods()["XE"]
    rec = rec or {}
    if out.get("stopped"):
        pv = {"stopped": out["stopped"], "labels": {k: False for k in tuple(XE.LABELS) + (XE.LABEL_G_REF,)},
              "operating": "그대로 · 굽기 멈춤(%s) — 산출이 쓰였으므로 다시 굽지 않는다(새 등록)" % out["stopped"], "a_op": XE.A_OP, "path": XE.PATH,
              "forward": XE.FORWARD_CANCELLED}
    else:
        pv = XE.public_view(out)
    la = out.get("lookahead") or {}
    pv.update({"xbatch_public_view": True, "prereg": PREREG, "prereg_commit": rec.get("commit"), "out_sha256": sha, "out_bytes": nbytes,
               "stopped": out.get("stopped"), "lookahead_ok": bool(la) and all(v.get("ok") for v in la.values()),
               "lookahead_n": {k: {"n": v.get("n"), "n_bad": v.get("n_bad")} for k, v in la.items()},
               "s_pairing": (out.get("s_adapter") or {}).get("pairing"), "s_sel_hash_same_as_f0": (out.get("s_adapter") or {}).get("sel_hash_same_as_f0"),
               "arm_status": dict(out.get("arm_status") or {}), "n_episodes_label": out.get("n_episodes_label"),
               "registration_error": list(rec.get("registration_error") or []), "smoke": bool(rec.get("smoke")),
               "contamination_incident": "등록 전 눈가린 연기 보고(옛 판)가 X-BEAR 의 ΣΔ ≤ 0(M 층 · 240개월 · T+1 · 10bp)을 드러냈다 — 등록 §0.3"})
    import copy
    pv = XE._strip(copy.deepcopy(pv))
    bad = public_safe_std(pv) + XD.public_safe(pv)
    if bad:
        raise SystemExit("🚨 게시 칸이 공개 안전 점검에 걸렸다: %s" % bad[:3])
    return pv


def bake(commit, rerun=None, smoke=False, f0_path=None):
    """frozen_check 를 통과한 뒤에만 부른다(--smoke 는 가짜 커밋 SMOKE · 임시 폴더). 값은 찍지 않는다 — 경로 · sha256 · 초만."""
    t0 = time.time()
    P = paths()
    if smoke and not (os.path.basename(os.path.dirname(os.path.abspath(P["dir"]))).startswith("xbatch_runner_smoke_")):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/xbatch_runner_smoke_*/out 이 아니다.")
    if not smoke and _OVR["out"]:
        raise SystemExit("🚨 진짜 굽기에 연기 경로가 켜져 있다.")
    if rerun:
        started = _read_text(P["mark"] if os.path.exists(P["mark"]) else P["gitmark"]).strip()
    else:
        started = "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):                      # 무엇보다 먼저 — 도중에 죽어도 한 번 굽기가 지켜진다
        if not os.path.exists(m):
            _write_text(m, started + "\n")
    tag = _push_start_tag(commit)                            # 셋째 표식 — 계산 전에
    M = _mods()
    XD = M["XD"]
    doc = load_f0(f0_path)
    if not smoke:
        fb = f0_check(doc, code_shas(), manifest_sha())
        if fb:
            raise SystemExit("🚨 F0 문서: %s" % "; ".join(fb[:3]))
    dec = _decisions(doc)
    XD.install_write_guard(ROOT)
    XD.install_read_guard(signal_layer=False)
    clock = {}
    import warnings
    import numpy as np
    try:
        with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            warnings.simplefilter("ignore")
            out = compute(dec, smoke=smoke, clock=clock)
    except BaseException:                                    # noqa: BLE001
        tb = traceback.format_exc()[-2500:]
        XD.guard_off()
        tail = "\n".join(l if l.strip().startswith("File ") else re.sub(r"(?<![A-Za-z_])[-+]?\d+\.\d+(e[-+]?\d+)?", "<num>", l) for l in tb.splitlines())
        raise SystemExit("🚨 굽기 계산 실패 — 산출을 쓰지 않았다(산출 전 기술적 중단이면 XBATCH_RERUN 으로 처음부터):\n%s" % tail)
    opened = XD.opened_paths()
    XD.guard_off()
    out.update({"prereg": PREREG, "prereg_commit": commit, "smoke": smoke, "clock": clock,
                "windows_asserted": {"scored": [XD.SCORE_FIRST, XD.SCORE_LAST], "input_min": XD.INPUT_MIN}})
    blob = (json.dumps(_clean(XD.mark_cache_only(out)), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with open(P["out"] + ".part", "wb") as f:                # 한 번에 끝에서 쓴다 — 잘린 파일도 «쓰였다» 로 친다
        f.write(blob)
    os.replace(P["out"] + ".part", P["out"])
    sha = hashlib.sha256(blob).hexdigest()
    mods = local_modules()
    files_opened = data_files_opened(opened)
    err = []
    unf = unfrozen_modules(mods)
    if unf:
        err.append("얼리지 않은 build/ 모듈을 불렀다: %s" % ", ".join(unf))
    ur = unregistered_data(files_opened)
    if ur:
        err.append("판 점검 밖 랩 자료를 읽었다: %s" % ", ".join(ur[:5]))
    forbidden = [p for p in opened if any(mk.lower() in p.replace("\\", "/").lower() for mk in XD.FORBIDDEN_READ_MARKS)]
    if forbidden:
        err.append("읽기 금지 경로를 열었다(%d)" % len(forbidden))
    if out.get("registration_note_intl"):
        err.append(out["registration_note_intl"])
    rec = {"commit": commit, "registration_error": err, "smoke": smoke}
    pub = public_doc(out, sha, len(blob), rec)
    _write_text(P["public"], json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    del out
    runlog = {"prereg": PREREG, "prereg_commit": commit, "runner": RUNNER, "started": started, "rerun": rerun, "start_tag": tag,
              "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "sec": round(time.time() - t0, 1), "clock": clock,
              "out": os.path.basename(P["out"]), "out_sha256": sha, "out_bytes": len(blob),
              "public": os.path.basename(P["public"]), "public_sha256": _sha_file(P["public"]),
              "env": {k: os.environ.get(k) for k in ENV_PINS}, "versions": _versions(), "frozen": list(FROZEN),
              "local_modules": mods, "unfrozen_modules": unf, "data_files_opened": files_opened, "n_opened": len(opened),
              "n_forbidden_reads": len(forbidden), "peak_mb": peak_mb(), "registration_error": err, "smoke": smoke,
              "f0_sha256": (_sha_file(f0_path) if f0_path else _sha_file(os.path.join(ROOT, *F0_FILE.split("/")))) if (f0_path or os.path.exists(os.path.join(ROOT, *F0_FILE.split("/")))) else None,
              "note": "값 없음 — 결과는 _xbatch.public.json 의 칸만 결과 문서(등록 §5 게시 규칙)로 옮긴다"}
    _write_text(P["runlog"], json.dumps(runlog, ensure_ascii=False, indent=1) + "\n")
    _mark_finished(P, sha)
    if smoke:
        M["XA"].cleanup_smoke()
    else:
        print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)" % (P["out"], sha[:16], runlog["sec"]))
    return runlog


def once():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("XBATCH_RERUN"))


def public_view_writer(out_path=None):
    """굽기 뒤 — 산출(_xbatch.json) → 게시 칸(_xbatch.public.json)을 다시 쓴다(FINISHED 표식이 있을 때만 · 값은 찍지 않는다)."""
    P = paths()
    op = out_path or P["out"]
    if not (os.path.exists(P["mark"]) and FINISHED in _read_text(P["mark"])):
        raise SystemExit("🚨 FINISHED 표식이 없다 — 게시 칸은 끝난 굽기에서만 다시 쓴다.")
    blob = _bytes(op)
    out = json.loads(blob.decode("utf-8"))
    rl = _read_json(P["runlog"]) if os.path.exists(P["runlog"]) else {}
    pub = public_doc(out, hashlib.sha256(blob).hexdigest(), len(blob),
                     {"commit": out.get("prereg_commit"), "registration_error": rl.get("registration_error"), "smoke": out.get("smoke")})
    _write_text(P["public"], json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    return {"public": P["public"], "sha256_16": _sha_file(P["public"])[:16]}


# ══════════════════════════════════════════════════════════════════════════
#  결과 문서 렌더러(얼린 · 게시 칸 파일 하나만 읽는다)
# ══════════════════════════════════════════════════════════════════════════
def _fmt(v, nd=4):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%%.%df" % nd) % v
    return str(v)


def result_doc(pub):
    """결과 문서 본문(Markdown) — 게시 칸 파일(_xbatch.public.json) 하나만 읽어 등록 §5 표의 칸을 옮긴다(손으로 옮기지 않는다 · 무조건 쓴다)."""
    if not pub or not pub.get("xbatch_public_view"):
        raise SystemExit("🚨 게시 칸 파일이 아니다")
    mu = pub.get("multiplicity") or {}
    lab = pub.get("labels") or {}
    L = ["# 결과 — 배치 X(%s)" % pub.get("prereg"), "",
         "- 등록 커밋 `%s` · 산출 sha256 `%s` · %s 바이트 · 20년 수치는 저장소 밖 캐시에만(등록 §5)" % (pub.get("prereg_commit"), (pub.get("out_sha256") or "—")[:16], pub.get("out_bytes")),
         "- 멈춤: %s · 선견 점검: %s · S 짝맞춤: %s · D 선정 해시 = F0: %s" % (pub.get("stopped") or "없음", _fmt(pub.get("lookahead_ok")),
                                                                    " · ".join("%s %s" % (k, _fmt(v)) for k, v in (pub.get("s_pairing") or {}).items()) or "—",
                                                                    _fmt(pub.get("s_sel_hash_same_as_f0"))),
         "- 등록 오류: %s" % ("; ".join(pub.get("registration_error") or []) or "없음"),
         "- 누적 N: %s → %s (이 배치 팔 %s · %s)" % (mu.get("cumulative_before"), mu.get("cumulative_after"), mu.get("total"),
                                                  " · ".join("%s %s" % (k, v) for k, v in (mu.get("counts") or {}).items())),
         "- 운용(경로 %s · a_op %s): %s" % (pub.get("path"), pub.get("a_op"), pub.get("operating")),
         "- 전방: %s" % pub.get("forward"),
         "- 🚨 오염 사고(등록 §0.3): %s" % pub.get("contamination_incident"), ""]
    L += ["## 라벨", "", "| 라벨 | 값 |", "|---|---|"] + ["| %s | %s |" % (k, _fmt(v)) for k, v in lab.items()] + [""]
    m = pub.get("M")
    if m:
        L += ["## M 층(시장 20년 · 일관성 점검 · 오염 창 — 관문 불리언 · n · 뒤 10년 반쪽 수치만)", "",
              "- 창 %s · n %s · 모두 통과 %s · 잭나이프 %s/%s" % ("~".join(m.get("window") or []), m.get("n"),
                                                        _fmt(m.get("pass_all")), (m.get("jackknife") or {}).get("n_ok"), (m.get("jackknife") or {}).get("n_e")),
              "- 뒤 10년 반쪽(%s): 평균 Δ %s(단위 d · 월) · 켜짐 비율 %s · n %s" % (
                  "~".join((m.get("half2") or {}).get("window") or []), _fmt((m.get("half2") or {}).get("mean_delta"), 5),
                  _fmt((m.get("half2") or {}).get("on_share"), 3), (m.get("half2") or {}).get("n")), "",
              "| 관문 | 값 |", "|---|---|"] + ["| %s | %s |" % (k, _fmt(v)) for k, v in (m.get("gates") or {}).items()]
        L += ["", "- 측정 팔 BY(q 0.10 · 보고 · 채택 경로 없음): %s" % (" · ".join("%s %s" % (k, _fmt(v)) for k, v in (m.get("measurement_by_reject") or {}).items()) or "—"), ""]
    i = pub.get("I")
    if i:
        L += ["## I 층(국외 10개 시장 재현)", "",
              "- 창 %s · 시장 %s(%s · 판 %s) · 평균 Δ > 0 시장 %s · 모두 통과 %s" % ("~".join(i.get("window") or []), i.get("n_markets"), " · ".join(i.get("markets") or []),
                                                                     i.get("mode"), i.get("n_markets_pos"), _fmt(i.get("pass_all"))),
              "- 뒤 10년 반쪽: %s" % " · ".join("%s %s" % (k, _fmt(v, 5)) for k, v in (i.get("half2") or {}).items() if k != "window"), "",
              "| 관문 | 값 |", "|---|---|"] + ["| %s | %s |" % (k, _fmt(v)) for k, v in (i.get("gates") or {}).items()] + [""]
    g = pub.get("G")
    if g:
        L += ["## G 층(성장 코어 대리 20년 — 관문 불리언만 · 값 · 켜짐 비율은 캐시)", "",
              "- 창 %s · LG 관문 구속 %s · 모두 통과 %s" % ("~".join(g.get("window") or []), _fmt(g.get("LG_binding")), _fmt(g.get("pass_LG"))),
              "", "| 관문 | 값 |", "|---|---|"] + ["| %s | %s |" % (k, _fmt(v)) for k, v in (g.get("gates_LG") or {}).items()] + [""]
    s = pub.get("S")
    if s:
        L += ["## S 층(EG30 V0 10년 · 무해 · 구현성 · 주 행 T+1 · 10bp · a 1)", "",
              "- 창 %s · n %s · 켜짐 비율 %s · 연 단계 효과 %s%%p · 80%% 한쪽 하한 %s%%p · 하락월 변화 %s · CRASH-M 변화 %s · 회전 %s · 모두 통과 %s" % (
                  "~".join(s.get("window") or []), s.get("n"), _fmt(s.get("on_share"), 3), _fmt(s.get("e_ann")), _fmt(s.get("e_lb80")), _fmt(s.get("g_down"), 5),
                  _fmt(s.get("g_crash"), 5), _fmt(s.get("turn"), 2), _fmt(s.get("pass_all"))),
              "- 팔 연 초과(보고): %s" % " · ".join("%s %s" % (k, _fmt(v)) for k, v in (s.get("arms_ann_ex") or {}).items()), "",
              "| 관문 | 값 |", "|---|---|"] + ["| %s | %s |" % (k, _fmt(v)) for k, v in (s.get("gates") or {}).items()] + [""]
    L += ["## 팔 상태(문헌 열기 판정 · 등록 §3.7)", "", " · ".join("%s %s" % (k, v) for k, v in (pub.get("arm_status") or {}).items()) or "—", "",
          "## 공개 규칙", "", "- 이 문서는 게시 칸 파일 하나에서 얼린 렌더러(`python -X utf8 build/x_run.py --result-doc`)가 만들었다 · 20년 수치(M · I · G 층 값 · "
          "20년 켜짐 비율 · 앞 10년 값)는 저장소 밖 캐시에만 · 사이트에는 싣지 않는다(MAX_YEARS 10)."]
    txt = "\n".join(L) + "\n"
    if CACHE_ONLY_KEY in txt:
        raise SystemExit("🚨 결과 문서에 20년 표지가 있다")
    return txt


# ══════════════════════════════════════════════════════════════════════════
#  F0 — 개수 · 날짜 · 라벨 · 커버리지 · 해시 · 자료 충실도(🚨 수익 · 켜짐 비율 · 신호-수익 통계 없음)
# ══════════════════════════════════════════════════════════════════════════
def _ds(x):
    return str(x)[:10] if x is not None else None


def label_counts(MF, XD):
    """하락월 · CRASH-M · SURGE-M · 급락 다리 · 반등 · 에피소드 — 개수와 날짜(수익 아님 · 라벨 · 명세 data_plan.F0_counts_only)."""
    import pandas as pd
    hold = MF.hold
    h1 = (hold >= pd.Period(XD.HALVES[0][0], "M")) & (hold <= pd.Period(XD.HALVES[0][1], "M"))
    down = MF.down.reindex(hold).fillna(False).astype(bool)
    crash, surge = MF.crash.reindex(hold).fillna(False).astype(bool), MF.surge.reindex(hold).fillna(False).astype(bool)
    ci, si = MF.crash_in.reindex(hold).fillna(False).astype(bool), MF.surge_in.reindex(hold).fillna(False).astype(bool)
    legs = [[_ds(a), _ds(b)] for a, b in MF.crash_legs]
    rebs = [[_ds(r["a"]), _ds(r["b"])] for r in MF.rebs]
    eps = [{"span": [str(e["span"][0]), str(e["span"][1])], "n_legs": len(e["legs"])} for e in MF.episodes]
    return {"window": [str(hold[0]), str(hold[-1])], "n_months": int(len(hold)),
            "down_months": {"n": int(down.sum()), "n_first_half": int(down[h1].sum()), "n_second_half": int(down[~h1].sum()),
                            "rule": "S&P 500 PR(^GSPC) 달 수익 < 0"},
            "crash_m": {"n": int(crash.sum()), "months": [str(p) for p in hold[crash.to_numpy()]], "rule": "SPY TR 달력 달 ≤ −σ_pre(0.042903)"},
            "surge_m": {"n": int(surge.sum()), "months": [str(p) for p in hold[surge.to_numpy()]], "rule": "SPY TR 달력 달 ≥ +σ_pre"},
            "crash_m_in_window_sd": {"n": int(ci.sum()), "rule": "창 안 240개월 SD(민감도 · D-9)"},
            "surge_m_in_window_sd": {"n": int(si.sum())},
            "crash_legs": {"n": len(legs), "legs": legs, "rule": "^GSPC PR 일간 10%/10% 지그재그(얼린 mech_episodes · 2006-08-31 ~ 2026-08-31)"},
            "rebounds": {"n": len(rebs), "spans": rebs, "rule": "[저점, min(저점 + 63거래일, 다음 상승 다리 끝)]"},
            "episodes": {"n": len(eps), "items": eps, "rule": "앞 다리 저점 ~ 다음 다리 고점 ≤ 126거래일이면 한 에피소드"}}


def f0(out=None, write_repo=True, smoke=False):
    """F0 — 명세 data_plan.F0_counts_only 칸만. 🚨 수익 · 초과 · 타이밍 통계 · 관문 값 · 무조건 켜짐 비율 · 켜진 달 수는 싣지 않는다.
    저장소(data/_xb_f0.json)엔 공개 안전 칸만 · 캐시(<캐시>/f0/xb_f0_full.json)엔 같은 문서(값 계열 없음)."""
    import pandas as pd
    M = _mods()
    XD, XS, XB, XE, XI, XA = M["XD"], M["XS"], M["XB"], M["XE"], M["XI"], M["XA"]
    t0 = time.time()
    clock = {}
    XD.install_write_guard(ROOT)
    XD.install_read_guard(signal_layer=False)
    try:
        t = time.time()
        pins, ipins = XD.check_pins(), XI.check_pins()
        dd = XD.decision_days(XD.INPUT_MIN_MONTH, XD.SCORE_LAST)
        hold = pd.period_range(XD.SCORE_FIRST, XD.SCORE_LAST, freq="M")
        XD.assert_scored_months([str(h) for h in hold])
        dec_idx = hold - 1
        t1_first = XD.t_plus_1(dd.loc[pd.Period("2006-08", "M")])
        cal = {"n_decision_months_loaded": int(len(dd)), "first_decision_month": str(dd.index[0]), "last_decision_month": str(dd.index[-1]),
               "first_scored_decision": str(dec_idx[0]), "last_scored_decision": str(dec_idx[-1]), "n_scored_months": int(len(hold)),
               "first_t1": _ds(t1_first), "bake_end_t1": _ds(XD.bake_end())}
        clock["pins_calendar"] = round(time.time() - t, 1)
        # 라벨(수익 아님)
        t = time.time()
        MF = XE.MFrame.real()
        labels = label_counts(MF, XD)
        clock["labels"] = round(time.time() - t, 1)
        # 신호 층 — 첫 결정(정의된) 달 · 정의된 결정 달 수(켜짐 수 아님) · 상태 일치율(SPY 판 대 French 판 · 명세 signals[X-BEAR].fidelity)
        t = time.time()
        with XE.signal_guard():
            I_ = XD.signal_inputs("T1")
            F = XS.signal_frame(I_)
            blr = XB.blr_path(F)
            pos, _ = XS.comp_w_positions(I_["spy"][0], I_["rf"][0], I_["baa10y"][0], I_["vix"][0], I_["vix3m"][0], XD.trading_days(),
                                         str(MF.daily.index[0].date()), str(MF.daily.index[-1].date()))
            ff = XD.ff3("m")
            aF = XS.bear_state(pd.Series(ff["Mkt-RF"], dtype=float))
        clock["signals"] = round(time.time() - t, 1)
        arms = {"X-BEAR": F["X-BEAR"], "X-COMP": F["X-COMP"], "X-CRED": F["X-CRED"], "X-JM": F.get("X-JM"), "X-BLR": blr["a"], "X-GVTREND": F["X-GVTREND"],
                "X-RRSHOCK": F["X-RRSHOCK"], "T-SMA200": F["T-SMA200"], "vol63": F["vol63"], "nagel_z": F["nagel_z"]}
        act = {}
        for nm, s in arms.items():
            if s is None:
                act[nm] = {"first_decision": None, "n_defined_scored": 0}
                continue
            s = pd.Series(s).reindex(dec_idx)
            fv = s.first_valid_index()
            act[nm] = {"first_decision": str(fv) if fv is not None else None, "n_defined_scored": int(s.notna().sum())}
        pa = pd.Series(pos, dtype=float).dropna()
        act["X-COMP-W"] = {"first_day": _ds(pa.index[0]) if len(pa) else None, "n_days_defined": int(len(pa))}
        for nm, floor in XD.MIN_WARMUP_BY_ELEMENT.items():
            fd = (act.get(nm) or {}).get("first_decision")
            if fd is not None and fd < floor:
                raise SystemExit("🚨 %s 첫 결정 %s < 등록 하한 %s" % (nm, fd, floor))
        a = F["X-BEAR"].reindex(dec_idx)
        common = aF.reindex(dec_idx).notna() & a.notna()
        agree = float((aF.reindex(dec_idx)[common] == a[common]).mean()) if common.any() else None
        fidelity = {"bear_state_spy_vs_french": {"window": [str(dec_idx[0]), str(dec_idx[-1])], "n_common": int(common.sum()), "state_agree": agree,
                                                  "min_agree": 0.95, "pass": bool(agree is not None and agree >= 0.95),
                                                  "rule": "상태 일치율(SPY TR − DGS3MO 판 대 French Mkt-RF 판) · 수익 비교가 아니다"}}
        t = time.time()
        fidelity.update({"spy_vs_sp500tr": XD.check_spy_vs_sp500tr(), "rf_vs_fred": XD.check_rf_vs_fred(), "vix3m_sources": XD.check_vix3m_sources(),
                         "baa10y_identity": XD.check_baa10y_identity()})
        alf = XD.alfred_check(fetch=False)
        alfred = {sid: {"n_vintages": r.get("n_vintages"), "failed_vintages": sorted((r.get("failed") or {}).keys()), "revised": r.get("revised"),
                        "ok_three_plus": r.get("ok_three_plus"), "sha_by_vintage": r.get("sha_by_vintage"),
                        "current_vs_last_vintage": r.get("current_vs_last_vintage")} for sid, r in alf.items()}
        revised = any(bool(v.get("revised")) for v in alfred.values())
        clock["fidelity_alfred"] = round(time.time() - t, 1)
        # I 층 커버리지 · 판정 · 시장별 라벨 개수
        t = time.time()
        cov = XI.coverage()
        iblk = XI.f0_block(cov)
        frames, meta = XI.build_panel(cov=cov)
        views = XI.primary_view(frames, meta)
        cl = XI.crash_labels(views)
        il = {}
        for cc, v in views.items():
            dn = v["down"].reindex(hold)
            il[cc] = {"n_down": int((dn == True).sum()), "n_crash_m_in_window_sd": int(cl[cc]["crash"].sum()),  # noqa: E712
                      "n_surge_m_in_window_sd": int(cl[cc]["surge"].sum()), "n_hold_rows": int(v["re_hold"].reindex(hold).notna().sum())}
        iblk["labels_by_market"] = {"window": [str(hold[0]), str(hold[-1])], "markets": il}
        del frames, views
        clock["intl"] = round(time.time() - t, 1)
        # D 목표 · S 커버리지 · D 대리 충실도(명세 action.D_proxy_G «corr(D_S, 대리) ≥ 0.6 (2014-06 ~ 2026-08 월)» — 자료 충실도)
        t = time.time()
        fid = os.path.join(XA.s_dir(), "_d_path.f0.tmp.json")
        dpath, rd = XA.d_targets(force=True, fidelity_out=fid)
        dc = XA.d_check(dpath)
        try:
            dfid = XE.d_proxy_fidelity(fid)
        finally:
            if os.path.exists(fid):
                os.remove(fid)                               # D 월 수익 파일 — 상관만 쓰고 지운다(찍지 않는다)
        clock["d_child"] = round(time.time() - t, 1)
        t = time.time()
        vroot = XA.vroot_check()
        if not vroot["ok"]:
            raise SystemExit("🚨 vroot 점검 실패: %s" % vroot["bad"][:3])
        scov = XA.s_coverage(world="dbook")
        rows = [r for r in (scov.get("months") or {}).values() if r.get("target")]
        s_cov = {"window": list(XA.S_FORM), "n_months": scov.get("n_months"), "n_ok": scov.get("n_ok"),
                 "coverage_min": min((r.get("moved") for r in rows), default=None), "n_mapped_min": min((r.get("n_mapped") for r in rows), default=None),
                 "rule": "그달 World(배치 V 핀 판 vroot · K6 · K7)에 값이 선 이름 ≥ 1 이고 D 목표 비중의 ≥ 0.90 이 옮겨졌다(K1)"}
        vb = XA.v0_beta_coverage()                           # K3 커버리지(검토 반영) — V0 흘린 비중 가운데 β̂ 가 선 몫(수익 없음)
        s_cov["v0_beta"] = {k: vb.get(k) for k in ("window", "n_months", "coverage_beta_min", "coverage_beta_median", "n_beta_names_min", "n_names_min",
                                                   "n_names_max", "rule")}
        clock["s_coverage"] = round(time.time() - t, 1)
        vx = XD.vxv_pub_date()
        vx_ev = os.path.exists(XD.vxv_evidence_path())
        d_proxy = "fallback" if dfid.get("fallback") else "main"
        decisions = {"d_proxy": d_proxy, "g_binding": d_proxy == "main", "vxv_pub_in_force": vx, "vxv_evidence": bool(vx_ev),
                     "intl_mode": iblk["decision"]["mode"], "intl_markets": list(iblk["decision"]["markets"]),
                     "intl_substituted": dict(iblk["decision"]["substituted"]), "alfred_first_release": bool(revised),
                     "french_last_month": XD.french_last_month(), "d_sel_hash": dc.get("sel_hash"), "d_pairing_A": bool(dc.get("pairing_A_pass")),
                     "s_cov_ok": bool(scov.get("n_ok") == scov.get("n_months") == 120), "state_agree_pass": bool(fidelity["bear_state_spy_vs_french"]["pass"]),
                     "lookahead_real_prior": "엔진 단계 x_signals --lookahead-real 모두 참(BEAR 200/200 · 성분 80/80) — 굽기가 다시 돈다",
                     "d_data_pin": XA.DATA_PIN}
        doc = {"kind": "xbatch_f0", "generated_at": _now(), "prereg": PREREG, "smoke": bool(smoke),
               "note": ("배치 X F0(build/x_run.py --f0) — 개수 · 날짜 · 라벨 · 커버리지 · 해시 · 자료 충실도(상태 일치율 · D 대리 corr)만. "
                        "수익 · 초과수익 · 타이밍 통계 · 관문 값 · 무조건 켜짐 비율 · 켜진 달 수는 없다(명세 data_plan.F0_counts_only · 굽기에서만)."),
               "windows": {"scored": [XD.SCORE_FIRST, XD.SCORE_LAST], "input_min": XD.INPUT_MIN, "warmup": list(XD.WARMUP), "s_layer": list(XD.S_WIN)},
               "calendar": cal, "labels": labels, "activation": act, "fidelity": fidelity, "alfred": alfred,
               "vxv": {"default": XD.VXV_PUB_DEFAULT, "in_force": vx, "evidence_file": bool(vx_ev),
                       "rule": "Cboe 공식 VIX3M CSV 시작일 · Cboe 1차 공고로 더 이른 날을 증명할 때만 앞당긴다(SN-1.1 · 증빙 찾지 않음)"},
               "d_target": {"pairing_A_pass": dc.get("pairing_A_pass"), "vb_books_sha_ok": dc.get("vb_books_sha_ok"), "n_months_A": dc.get("n_months_A"),
                            "n_match_A": dc.get("n_match_A"), "n_with_target": dc.get("n_with_target"), "first": dc.get("first"), "last": dc.get("last"),
                            "max_w_le_cap": dc.get("max_w_le_cap"), "v_blobs_ok": dc.get("v_blobs_ok"), "sel_hash": dc.get("sel_hash"),
                            "d_child_sec": rd.get("sec")},
               "d_proxy_fidelity": {"window": dfid.get("window"), "n": dfid.get("n"), "corr_fid": dfid.get("corr_fid"), "corr_fid_min": 0.6,
                                    "pass": dfid.get("pass"), "fallback": dfid.get("fallback"),
                                    "rule": "corr(D_S 월 D0 수익 · French ME5×β1) < 0.6 이면 Portfolios_Formed_on_BETA Lo 20 · G 관문 «참고»(기계적)"},
               "s_coverage": s_cov, "intl": iblk,
               "vroot": {"ok": bool(vroot["ok"]), "data_pin": XA.DATA_PIN, "paths": list(XA.VROOT_PATHS),
                         "rule": "D 자식 · D 책 · S 커버리지는 자료 핀 커밋의 build/ + data/(git archive · 캐시 s/vroot) — 파일 핀 20 · 폴더 요약 4 = data/_vb_manifest.json"},
               "pins": {"x_data_ok": pins["ok"], "x_data_n_sources": pins.get("n_sources"), "x_intl_ok": ipins["ok"], "x_intl_n_sources": ipins.get("n_sources")},
               "decisions": decisions, "code_sha": code_shas(), "manifest_sha16": manifest_sha(), "clock": clock,
               "sec": round(time.time() - t0, 1)}
        doc = _clean(doc)
        full_doc = doc
        doc = f0_public(full_doc)                            # 저장소 판 — 20년 창 실수(상태 일치율 · D 대리 corr)는 캐시 전체판에만(사용자 20년 규칙 · 검토 반영)
        probs = public_safe_std(doc) + XD.public_safe(doc) + foreign_marks(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
        if probs:
            raise SystemExit("🚨 F0 가 공개 안전 · 다른 배치 경계 점검에 걸렸다: %s" % probs[:3])
        fb = [b for b in f0_check(doc) if "코드" not in b]
        if fb:
            raise SystemExit("🚨 F0 거르개: %s" % "; ".join(fb[:4]))
        od = out or os.path.join(cache_guard_std(), "f0")
        os.makedirs(od, exist_ok=True)
        full_p = os.path.join(od, "xb_f0_full.json")
        _write_text(full_p, json.dumps(full_doc, ensure_ascii=False, indent=1) + "\n")
        repo_p = None
        if write_repo:
            repo_p = XD.repo_write_json(F0_FILE, doc)
        else:
            _write_text(os.path.join(od, "_xb_f0.json"), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        return {"path": repo_p or os.path.join(od, "_xb_f0.json"), "full": full_p, "sec": doc["sec"], "clock": clock, "doc": doc}
    finally:
        XD.guard_off()


F0_CACHE_ONLY = (("fidelity", "bear_state_spy_vs_french", "state_agree"), ("d_proxy_fidelity", "corr_fid"))


def f0_public(doc):
    """(순수) F0 저장소 판 — 20년 창 실수(상태 일치율 · D 대리 corr)를 빼고 «캐시 전체판» 표지를 단다(통과 참/거짓 · n · 문턱은 남긴다)."""
    d = json.loads(json.dumps(doc, ensure_ascii=False))
    for path in F0_CACHE_ONLY:
        cur = d
        for k in path[:-1]:
            cur = cur.get(k) if isinstance(cur, dict) else None
        if isinstance(cur, dict) and path[-1] in cur:
            cur[path[-1]] = "캐시 전체판(<캐시>/f0/xb_f0_full.json)에만 — 20년 창 수치(사용자 20년 규칙)"
    return d


def f0_table(doc=None):
    """data/_xb_f0.json → 등록 문서 §3.6 표(Markdown)."""
    d = doc or load_f0()
    if not d:
        raise SystemExit("🚨 F0 문서 없음")
    L, dec, lab = [], d["decisions"], d["labels"]
    L += ["| 칸 | 값 |", "|---|---|"]
    L.append("| 채점 보유월 · 결정 달 | %s ~ %s (%s) · 결정 %s ~ %s · 첫 T+1 %s · 굽기 끝 T+1 %s |" % (
        d["windows"]["scored"][0], d["windows"]["scored"][1], d["calendar"]["n_scored_months"], d["calendar"]["first_scored_decision"],
        d["calendar"]["last_scored_decision"], d["calendar"]["first_t1"], d["calendar"]["bake_end_t1"]))
    L.append("| 하락월(^GSPC PR < 0) | %s (앞 10년 %s · 뒤 10년 %s) |" % (lab["down_months"]["n"], lab["down_months"]["n_first_half"], lab["down_months"]["n_second_half"]))
    L.append("| CRASH-M / SURGE-M(σ_pre) | %s / %s |" % (lab["crash_m"]["n"], lab["surge_m"]["n"]))
    L.append("| CRASH-M 달 | %s |" % " · ".join(lab["crash_m"]["months"]))
    L.append("| SURGE-M 달 | %s |" % " · ".join(lab["surge_m"]["months"]))
    L.append("| CRASH-M / SURGE-M(창 안 SD · 민감도) | %s / %s |" % (lab["crash_m_in_window_sd"]["n"], lab["surge_m_in_window_sd"]["n"]))
    L.append("| 급락 다리(고점 → 저점) | %s — %s |" % (lab["crash_legs"]["n"], " · ".join("%s→%s" % tuple(x) for x in lab["crash_legs"]["legs"])))
    L.append("| 에피소드(보유월 구간 · 다리 수) | %s — %s |" % (lab["episodes"]["n"], " · ".join("%s~%s(%s)" % (e["span"][0], e["span"][1], e["n_legs"]) for e in lab["episodes"]["items"])))
    L.append("| 첫 결정(정의된 달) · 정의된 채점 결정 수 | %s |" % " · ".join(
        "%s %s(%s)" % (k, v.get("first_decision"), v.get("n_defined_scored")) for k, v in d["activation"].items() if "first_decision" in v))
    cw = d["activation"].get("X-COMP-W") or {}
    L.append("| X-COMP-W 첫 날 · 정의된 날 수 | %s · %s |" % (cw.get("first_day"), cw.get("n_days_defined")))
    fb = d["fidelity"]["bear_state_spy_vs_french"]
    L.append("| 상태 일치율 SPY 판 대 French 판(≥ 0.95) | %s (n %s · 값은 캐시 전체판에만) |" % ("통과" if fb["pass"] else "미달", fb["n_common"]))
    f = d["fidelity"]
    L.append("| 자료 충실도(개수) | SPY 대 ^SP500TR 0.25%% 안 %s/%s 달 · rf_monthly 대 FRED 같은 달 %s/%s(한 달 늦춤 %s) · VIX3M Cboe 대 yf 0.011 안 %s/%s 날 · BAA10Y = DBAA − DGS10 %s/%s 날 |" % (
        f["spy_vs_sp500tr"]["n_within_tol"], f["spy_vs_sp500tr"]["n_months"], f["rf_vs_fred"]["n_within_tol_same_month"], f["rf_vs_fred"]["n_months"],
        f["rf_vs_fred"]["n_within_tol_lag1"], f["vix3m_sources"]["n_within_tol"], f["vix3m_sources"]["n_common_in_window"],
        f["baa10y_identity"]["n_within_tol"], f["baa10y_identity"]["n_common"]))
    L.append("| VIX3M 공표일(적용) | %s (기본 %s · 증빙 파일 %s) |" % (d["vxv"]["in_force"], d["vxv"]["default"], "있음" if d["vxv"]["evidence_file"] else "없음"))
    L.append("| ALFRED 판(DBAA · DGS10 · BAA10Y) | %s · 개정 보임 %s |" % (" · ".join("%s %s판(실패 %s)" % (k, v["n_vintages"], ",".join(v["failed_vintages"]) or "없음")
                                                                     for k, v in d["alfred"].items()), "참" if dec["alfred_first_release"] else "거짓"))
    L.append("| French 마지막 달 | %s |" % dec["french_last_month"])
    df = d["d_proxy_fidelity"]
    L.append("| D 대리 충실도 corr(D_S · ME5×β1 · %s ~ %s · ≥ 0.6) | %s (n %s · 값은 캐시 전체판에만) → D 대리 %s · G 관문 %s |" % (
        df["window"][0], df["window"][1], "통과" if df.get("pass") else "미달", df["n"], dec["d_proxy"],
        "구속" if dec["g_binding"] else "참고"))
    dt = d["d_target"]
    L.append("| D 목표(얼린 V02 LBS · 20%% 상한) | 짝맞춤 A %s/%s · 목표 선 달 %s(%s ~ %s) · 상한 %s · 선정 해시 `%s` |" % (
        dt["n_match_A"], dt["n_months_A"], dt["n_with_target"], dt["first"], dt["last"], "참" if dt["max_w_le_cap"] else "거짓", (dt["sel_hash"] or "")[:16]))
    sc = d["s_coverage"]
    L.append("| S 층 D 목표 커버리지(K1 · K6 · K7) | %s/%s 달 · 옮긴 몫 최소 %s · 옮긴 이름 최소 %s |" % (sc["n_ok"], sc["n_months"], sc["coverage_min"], sc["n_mapped_min"]))
    vb = sc.get("v0_beta") or {}
    L.append("| S 층 V0 비중의 β̂ 커버리지(K3 · %s ~ %s) | 최소 %s · 중앙 %s · β̂ 선 이름 최소 %s · V0 이름 %s ~ %s |" % (
        (vb.get("window") or ["—", "—"])[0], (vb.get("window") or ["—", "—"])[1],
        ("%.3f" % vb["coverage_beta_min"]) if isinstance(vb.get("coverage_beta_min"), float) else "—",
        ("%.3f" % vb["coverage_beta_median"]) if isinstance(vb.get("coverage_beta_median"), float) else "—",
        vb.get("n_beta_names_min"), vb.get("n_names_min"), vb.get("n_names_max")))
    vr = d.get("vroot") or {}
    L.append("| D 자료 판(K7 · vroot) | 자료 핀 커밋 `%s` · 점검 %s |" % ((vr.get("data_pin") or "")[:12], "참" if vr.get("ok") else "거짓"))
    ib = d["intl"]["decision"]
    L.append("| I 층 판정 | %s · %s · 대체 %s · 빈 시장 %s |" % (ib["mode"], " · ".join(ib["markets"]), ib["substituted"] or "없음", ib["empty"] or "없음"))
    lm = (d["intl"].get("labels_by_market") or {}).get("markets") or {}
    L.append("| I 층 시장별 하락월 · CRASH-M · SURGE-M(창 안 SD) | %s |" % " · ".join("%s %s·%s·%s" % (k, v["n_down"], v["n_crash_m_in_window_sd"], v["n_surge_m_in_window_sd"]) for k, v in lm.items()))
    L.append("| 명세 · 고정본 | x_data %s(%s 원천) · x_intl %s(%s 원천) · 명세 sha16 `%s` |" % (
        "참" if d["pins"]["x_data_ok"] else "거짓", d["pins"]["x_data_n_sources"], "참" if d["pins"]["x_intl_ok"] else "거짓", d["pins"]["x_intl_n_sources"], d["manifest_sha16"]))
    return "\n".join(L) + "\n"


# ══════════════════════════════════════════════════════════════════════════
#  명세 registration 절 · 얼린 파일 표 · 등록 직전 점검 · 덧붙임 덩이 · 백업
# ══════════════════════════════════════════════════════════════════════════
def manifest_registration(lit_src=None):
    """data/_xb_manifest.json 에 «registration» 절을 넣는다(다른 절은 그대로 · 값 계열 없음)."""
    M = _mods()
    XD, XE, XA, XS = M["XD"], M["XE"], M["XA"], M["XS"]
    lp = lit_open_path()
    if lit_src:
        if not os.path.exists(lit_src):
            raise SystemExit("🚨 문헌 기록 원본이 없다: %s" % lit_src)
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        shutil.copyfile(lit_src, lp)
    if not os.path.exists(lp):
        raise SystemExit("🚨 캐시에 문헌 열기 기록이 없다 — --manifest --lit <lit_open.json>")
    lit = _read_json(lp)
    cid = os.path.join(cache_guard_std(), "meta", "cache_id.txt")
    if not os.path.exists(cid):
        raise SystemExit("🚨 캐시 표지가 없다 — --init-cache-id 먼저")
    p = os.path.join(ROOT, *MANIFEST_FILE.split("/"))
    if not os.path.exists(p):
        raise SystemExit("🚨 %s 가 없다 — x_data --manifest · x_intl --manifest 먼저" % MANIFEST_FILE)
    man = _read_json(p)
    man["registration"] = {
        "note": "배치 X 등록 절(build/x_run.py --manifest) — 캐시 표지 · 문헌 열기 기록 · 얼린 호출 핀 · 사용자 답 · 전방 취소. 값 계열 · 수익 없음.",
        "generated_at": _now(),
        "cache_identity": {"file": "%TEMP%/xbatch_cache/meta/cache_id.txt", "sha256": _sha_file(cid)},
        "lit_open": {"file": "%TEMP%/xbatch_cache/lit/lit_open.json(저장소 밖)", "sha256": _sha_file(lp), "attempted_at": lit.get("attempted_at"),
                     "arm_decisions": {k: v.get("after") for k, v in (lit.get("arm_decisions") or {}).items()},
                     "pdf_sha256": dict(lit.get("files_outside_repo") or {})},
        "frozen_calls": {"x_eval": dict(XE.FROZEN_BLOBS), "x_signals.q_jump": XS.Q_JUMP_BLOB, "x_data.v_data": XD.V_DATA_BLOB,
                         "x_adapter.code_pin": XA.CODE_PIN, "x_adapter.build_tree": XA.BUILD_TREE, "x_adapter.root_frozen": dict(XA.ROOT_FROZEN),
                         "x_adapter.v_frozen": dict(XA.V_FROZEN), "x_adapter.dbook_frozen": dict(XA.DBOOK_FROZEN), "x_adapter.vb_books_sha": XA.VB_BOOKS_SHA,
                         "x_adapter.v0_hash_pin": dict(XA.V0_HASH_PIN), "x_adapter.p3": dict(XA.P3), "x_adapter.price": XA.P1_PRICE, "x_adapter.base": XA.P1_BASE,
                         "x_adapter.data_pin": XA.DATA_PIN, "x_adapter.vroot_paths": list(XA.VROOT_PATHS)},
        "user_answers": {"U1_a_op": "½", "U2_path": "B", "premium_trail": "뒤 24개월 −0.40%p NAV", "premium_cum": "붙인 뒤 누적 −0.60%p NAV",
                         "disclose": XE.DISCLOSE_B, "answered_at": "2026-09-27"},
        "spec_rules": {"premium_trail_exemption": "뒤 24개월 한도는 그 24개월 창에 완료된 급락 다리가 없을 때만 선다 — 명세 규칙(x_eval.premium_cap_kill) · 사용자 답에는 없다",
                       "premium_shadow_v0": ("경로 B 로 붙였을 때만: 운용 담당이 매달 운용 펀드(@ a_op) − 같은 달 V0 그림자 펀드(얼린 V0 규칙 · 같은 비용)의 월 차를 "
                                             "x_eval.premium_cap_kill 에 넣어 조건을 본다 · QFWD 원장은 멈췄으므로 그림자 V0 는 운용 기록에서 따로 계산한다(원장 · 예정 판정일 없음)")},
        "forward": {"cancelled": True, "text": XE.FORWARD_CANCELLED, "no_dir": FORWARD_DIR},
        "runner": {"file": RUNNER, "env_pins": dict(ENV_PINS), "versions": dict(VERSIONS), "first_added": list(FIRST_ADDED),
                   "lookahead_real": {"n_main": LOOKAHEAD_MAIN, "n_arm": LOOKAHEAD_ARM}},
    }
    g = man.get("guards") or {}
    if isinstance(g.get("forbidden_read_marks"), list):         # 배치 T 사이트 경계(t_guard)의 내용 표식을 싣지 않는다(이름 대신 설명 · 코드 x_data.FORBIDDEN_READ_MARKS 가 정본)
        g["forbidden_read_marks"] = ("x_data.FORBIDDEN_READ_MARKS — 배치 T 산출 폴더(tbatch_cache/out)와 배치 T 산출 파일 넷(이름은 배치 T 사이트 경계 표식이라 "
                                     "여기 싣지 않는다 · T01 C:bearonly 저장값을 열지 않는다)")
        man["guards"] = g
    bad = public_safe_std(man) + XD.public_safe(man)
    bad += foreign_marks(json.dumps(man, ensure_ascii=False).encode("utf-8"))
    if bad:
        raise SystemExit("🚨 명세 registration 절이 공개 안전 · 다른 배치 경계 점검에 걸렸다: %s" % bad[:3])
    return XD.repo_write_json(MANIFEST_FILE, man)


def foreign_marks(blob):
    """다른 배치 사이트 경계(t_guard · v_guard)의 내용 표식이 이 배치 저장소 JSON 에 들어 있으면 이름 목록(validate_site 가 막는다)."""
    import t_guard as TG
    import v_guard as VG
    return ["다른 배치 경계 표식 %s" % m.decode() for m in tuple(TG.OUTPUT_CONTENT_MARKS) + tuple(VG.OUTPUT_CONTENT_MARKS) if m in blob]


def pins_table():
    rows = []
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        if not os.path.exists(fp):
            rows.append({"path": p, "blob": None, "sha256_lf": None, "tracked": None})
            continue
        blob = _git("hash-object", "--", p).stdout.strip()
        rows.append({"path": p, "blob": blob[:12], "sha256_lf": _sha_lf(_bytes(fp))[:16],
                     "tracked": _git("ls-files", "--error-unmatch", "--", p).returncode == 0})
    return rows


GITIGNORE_BLOCK = """
# 배치 X(PREREG-*-XBATCH · 사용자 20년 규칙 2026-09-27) — 20년 산출(_xbatch.json · _xbatch.public.json · _xbatch.run.json · _xbatch.started)이나
#   캐시 사본(xbatch_cache)이 작업 트리에 복사돼도 쓸려 들지 않게. 명세 둘(data/_xb_manifest.json · data/_xb_f0.json)은 «_xb_» 라 걸리지 않는다.
_xbatch*
xbatch_cache/
"""
VALIDATE_BLOCK = """
# ── 배치 X(PREREG-*-XBATCH · 사용자 20년 규칙 2026-09-27) 사이트 경계 ─────────────────────────────
# 20년 수치(_xbatch*) · French · Cboe · FRED · OECD · yfinance 원자료가 저장소 · 사이트 자료에 없어야 한다(사이트는 10년 · MAX_YEARS 10).
#   data/_xb* 는 공개 안전 명세 둘(_xb_manifest · _xb_f0)뿐 · data/_xfwd/ 없음(전방 원장 취소 · 사용자 갱신 2026-09-27) · 값 계열 목록 없음 · 사이트 자료에 굽기 산출 표식 없음.
#   build/x_run.py 는 모듈 머리에서 표준 라이브러리만 불러온다(site_guard_std). 러너(x_run.frozen_check)도 같은 함수를 부른다.
try:
    import importlib as _il_xb
    _xr = _il_xb.import_module("x_run")
    _gx = _xr.site_guard_std(ROOT)
    if not _gx["ok"]:
        errors.append("배치 X 사이트 경계 위반 %d건 — %s. 20년 산출(_xbatch*) · 라이선스 원자료는 저장소 밖 캐시에만 둔다"
                      % (_gx.get("n_bad", len(_gx["bad"])), " · ".join(_gx["bad"][:4])))
    else:
        print("  ~ 배치 X 사이트 경계 통과(파일 %d · 사이트 자료 %d 훑음)" % (_gx["n_files"], _gx["n_scanned"]))
except Exception as _e:
    print("  ~ 배치 X 사이트 경계 검사가 예외로 죽었다 — %s (미검증)" % str(_e)[:80])
"""
_VALIDATE_ANCHOR = 'print("사이트 검증:"'


def wire_texts(gitignore_txt, validate_txt):
    """(순수) 덧붙인 뒤의 두 글 — 이미 있으면 그대로(멱등). validate_site 덩이는 마지막 요약 줄 바로 앞에."""
    g = gitignore_txt
    if "_xbatch*" not in g:
        g = g.rstrip("\n") + "\n" + GITIGNORE_BLOCK
    v = validate_txt
    if "배치 X(PREREG-*-XBATCH" not in v:
        i = v.rfind(_VALIDATE_ANCHOR)
        if i < 0:
            raise SystemExit("🚨 validate_site.py 의 마지막 요약 줄을 찾지 못했다")
        v = v[:i] + VALIDATE_BLOCK.lstrip("\n") + "\n" + v[i:]
    return g, v


def wire(apply=False):
    gp, vp = os.path.join(ROOT, ".gitignore"), os.path.join(ROOT, "build", "validate_site.py")
    g0, v0 = _read_text(gp), _read_text(vp)
    g1, v1 = wire_texts(g0, v0)
    res = {"gitignore_changed": g1 != g0, "validate_changed": v1 != v0, "applied": False}
    if apply:
        if g1 != g0:
            with io.open(gp, "w", encoding="utf-8", newline="\n") as f:
                f.write(g1)
        if v1 != v0:
            with io.open(vp, "w", encoding="utf-8", newline="\n") as f:
                f.write(v1)
        res["applied"] = True
    return res


def precommit():
    """등록 커밋 직전 점검 — 참/거짓 · 이름만(값 없음)."""
    M = _mods()
    pdx, pix = M["XD"].check_pins(), M["XI"].check_pins()
    ci, cmsg = check_cache_identity()
    f0d = load_f0()
    fb = f0_check(f0d, code_shas(), manifest_sha()) if f0d else ["F0 문서 없음"]
    pp = os.path.join(ROOT, *PREREG.split("/"))
    txt = _read_text(pp) if os.path.exists(pp) else ""
    n_ph, n_dm = placeholder_counts(txt)
    g = site_guard()
    missing = [p for p in FROZEN if not os.path.exists(os.path.join(ROOT, *p.split("/")))]
    clo = ["build/%s.py" % m for m in static_closure() if "build/%s.py" % m not in FROZEN]
    gw, vw = wired_state()
    vr = M["XA"].vroot_check()
    f0_pin_ok = bool(f0d and (f0d.get("decisions") or {}).get("d_data_pin") == M["XA"].DATA_PIN)
    ready = bool(not name_check() and not n_ph and not n_dm and pdx["ok"] and pix["ok"] and ci and not check_lit_open() and f0d and not fb
                 and not check_no_forward() and g["ok"] and not missing and not clo and not registered_constants_ok() and gw and vw and vr["ok"] and f0_pin_ok)
    return {"ready": ready, "prereg": PREREG, "prereg_n": _N_PREREG, "name_ok": not name_check(), "placeholders": n_ph, "draft_marks": n_dm,
            "x_data_pins_ok": pdx["ok"], "x_data_pins_bad": pdx["bad"][:5], "x_intl_pins_ok": pix["ok"], "x_intl_pins_bad": pix["bad"][:5],
            "cache_identity": ci, "cache_identity_msg": cmsg, "lit_open_problems": check_lit_open(), "f0_present": bool(f0d), "f0_problems": fb,
            "no_forward": not check_no_forward(), "site_guard": g["ok"], "site_guard_bad": g["bad"][:5], "frozen_missing": missing,
            "closure_not_frozen": clo, "registered_constants_bad": registered_constants_ok(),
            "wired_gitignore": gw, "wired_validate_site": vw, "vroot_ok": vr["ok"], "vroot_bad": vr["bad"][:3], "f0_data_pin_ok": f0_pin_ok,
            "head": _git("rev-parse", "HEAD").stdout.strip()}


BACKUP_ROOT = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "yeodoo_private", "xbatch_cache_backup")
BACKUP_PARTS = ("raw", "meta", "f0", "lit")
BACKUP_S_FILES = ("d_targets.json", "s_coverage_dbook.json", "s_coverage_root.json", "v0_beta_cov.json", "vcheck.json", "vroot.json", "root.json")   # s/ 의 값 없는 F0 파일(수익 경로 · 뿌리 폴더는 넣지 않는다 — 다시 짓는다)


def backup(dst=BACKUP_ROOT):
    """고정본(캐시 raw · meta · f0 · lit + s/ 의 값 없는 F0 파일)을 %TEMP% 밖 사적 폴더로 — SHA 대조(커밋 · 게시하지 않는다 · out/ · s/ 의 수익 경로 · 뿌리는 넣지 않는다)."""
    if _inside(dst, ROOT) or _norm(dst).startswith(_norm(tempfile.gettempdir())):
        raise SystemExit("🚨 백업은 저장소 밖 · %TEMP% 밖에만")
    src = cache_guard_std()
    idx, n = {}, 0
    items = []
    for part in BACKUP_PARTS:
        for dp, _, fns in os.walk(os.path.join(src, part)):
            items += [os.path.join(dp, fn) for fn in fns]
    items += [os.path.join(src, "s", fn) for fn in BACKUP_S_FILES if os.path.isfile(os.path.join(src, "s", fn))]
    for a in items:
        rel = os.path.relpath(a, src).replace(os.sep, "/")
        b = os.path.join(dst, "cache", *rel.split("/"))
        sha = _sha_file(a)
        if not (os.path.exists(b) and _sha_file(b) == sha):
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(a, b)
            n += 1
        idx[rel] = sha
    _write_text(os.path.join(dst, "_index.json"), json.dumps({"at": _now(), "files": idx}, ensure_ascii=False) + "\n")
    bad = [r for r, s in idx.items() if _sha_file(os.path.join(dst, "cache", *r.split("/"))) != s]
    return {"dst": dst, "files": len(idx), "copied": n, "verify_bad": len(bad)}


def restore(cache_root, src=BACKUP_ROOT):
    if _inside(cache_root, ROOT):
        raise SystemExit("🚨 캐시 뿌리가 저장소 안이다")
    idx = _read_json(os.path.join(src, "_index.json"))["files"]
    bad = 0
    for rel, sha in idx.items():
        a = os.path.join(src, "cache", *rel.split("/"))
        b = os.path.join(cache_root, *rel.split("/"))
        os.makedirs(os.path.dirname(b), exist_ok=True)
        shutil.copy2(a, b)
        bad += int(_sha_file(b) != sha)
    return {"restored": len(idx), "verify_bad": bad}


# ══════════════════════════════════════════════════════════════════════════
#  러너 연기 시험(눈가린 · 산출은 열지 않고 지운다)
# ══════════════════════════════════════════════════════════════════════════
def _scrub(s):
    return "\n".join(l if l.strip().startswith("File ") else re.sub(r"(?<![A-Za-z_])[-+]?\d+\.\d+(e[-+]?\d+)?", "<num>", l) for l in (s or "").splitlines())


def smoke(with_f0=True):
    """러너 경로 전체 — F0(임시 폴더 · 저장소에 쓰지 않음) → 판 점검 우회(가짜 커밋 SMOKE) → 표식 → 굽기(선견 작게 · S 어댑터 · M · I · G · S) →
    게시 칸 → 실행 기록 → FINISHED → 결과 문서 렌더(됐는가 참/거짓만). 산출 · F0 는 임시 폴더에만 쓰고 **열지 않고** 지운다(실행 기록의 값 없는 칸 —
    모듈 이름 · 참/거짓 · 초 · 메모리 — 만 읽는다). 돌려주는 것: {ok, sec, steps, files(존재 · 비지 않음 참/거짓), err}.
    🚨 산출 · 게시 칸 · 결과 문서의 바이트 수 · 글자 수 · 게시 칸 키 목록 · 표준출력 길이는 싣지 않는다 — «참»/«거짓» · 음수 부호 · 빈 값이
    길이를 바꿔 관문 결과의 합을 흘린다(검토 반영 2026-09-27 · 옛 판의 러너 연기 기록은 열지 않고 지웠다 · 등록 §0.3)."""
    import contextlib
    cache = cache_guard_std()
    tmp = tempfile.mkdtemp(prefix="xbatch_runner_smoke_", dir=cache)
    if _inside(tmp, ROOT):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    saved = dict(_OVR)
    res = {"ok": False, "steps": {}, "started": _now()}
    t0 = time.time()
    sink = io.StringIO()
    real_out_before = sorted(f for f in os.listdir(os.path.join(cache, "out")) if f.startswith("_xbatch")) if os.path.isdir(os.path.join(cache, "out")) else []
    try:
        f0file = None
        if with_f0:
            t1 = time.time()
            try:
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    r = f0(out=os.path.join(tmp, "f0"), write_repo=False, smoke=True)
                f0file = r["path"]
                res["steps"]["f0"] = {"ok": os.path.exists(f0file), "sec": round(time.time() - t1, 1), "clock": r["clock"],
                                      "files": sorted(os.listdir(os.path.join(tmp, "f0"))), "decision_keys": sorted(r["doc"]["decisions"])}
                del r
            except BaseException as e:                       # noqa: BLE001
                res["steps"]["f0"] = {"ok": False, "sec": round(time.time() - t1, 1), "err": _scrub("%s: %s" % (type(e).__name__, str(e)))[-1500:]}
        _OVR.update({"out": os.path.join(tmp, "out"), "gitmark": os.path.join(tmp, "gitdir_" + GIT_MARK_NAME), "tag": tmp})
        P = paths()
        t1 = time.time()
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                rec = bake("SMOKE", smoke=True, f0_path=f0file)
            res["steps"]["bake"] = {"ok": True, "sec": round(time.time() - t1, 1), "clock": rec["clock"], "peak_mb": rec["peak_mb"],
                                    "unfrozen_modules": rec["unfrozen_modules"], "registration_error": rec["registration_error"],
                                    "local_modules": rec["local_modules"], "n_data_files_opened": len(rec["data_files_opened"] or []),
                                    "n_opened": rec["n_opened"], "n_forbidden_reads": rec["n_forbidden_reads"], "start_tag": rec["start_tag"]}
        except BaseException as e:                           # noqa: BLE001
            res["steps"]["bake"] = {"ok": False, "sec": round(time.time() - t1, 1), "err": _scrub("%s: %s" % (type(e).__name__, str(e)))[-2500:]}
        files = {k: {"exists": os.path.exists(P[k]), "nonempty": bool(os.path.exists(P[k]) and os.path.getsize(P[k]) > 0)}
                 for k in ("out", "mark", "runlog", "public", "gitmark")}
        files["second_run_blocked"] = bool(_existing_outputs(P))
        files["finished_marks"] = all(os.path.exists(P[k]) and FINISHED in _read_text(P[k]) for k in ("mark", "gitmark"))
        files["tag_file"] = os.path.exists(os.path.join(tmp, START_TAG))
        try:
            start_guard("SMOKE", None, [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)], None)
            files["restart_blocked"] = False
        except SystemExit:
            files["restart_blocked"] = True
        try:                                                 # 결과 문서 렌더러가 게시 칸 파일에서 도는가(글은 열지 않는다 — 됐는가 · 표지만 · 길이 없음)
            with contextlib.redirect_stdout(sink):
                pub = _read_json(P["public"])
                txt = result_doc(pub)
                files["public_safe"] = not (public_safe_std(pub) + _mods()["XD"].public_safe(pub))
                del pub
            files["result_doc_rendered"] = bool(txt)
            files["result_doc_has_cache_marker"] = CACHE_ONLY_KEY in txt
            del txt
        except BaseException as e:                           # noqa: BLE001
            files["result_doc_err"] = _scrub("%s: %s" % (type(e).__name__, str(e)))[-800:]
        res["files"] = files
        b = res["steps"].get("bake") or {}
        res["ok"] = bool((res["steps"].get("f0") or {"ok": True})["ok"] and b.get("ok") and not b.get("unfrozen_modules")
                         and not b.get("registration_error") and not b.get("n_forbidden_reads")
                         and all(files[k]["exists"] for k in ("out", "mark", "runlog", "public", "gitmark"))
                         and files["second_run_blocked"] and files["finished_marks"] and files["restart_blocked"] and files.get("public_safe")
                         and files.get("result_doc_rendered") and not files.get("result_doc_has_cache_marker"))
    finally:
        _OVR.clear()
        _OVR.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)               # 열지 않고 지운다
        res["stdout_discarded_unread"] = True                 # 길이도 싣지 않는다
        del sink
    res["deleted_unread"] = not os.path.exists(tmp)
    real_out_after = sorted(f for f in os.listdir(os.path.join(cache, "out")) if f.startswith("_xbatch")) if os.path.isdir(os.path.join(cache, "out")) else []
    res["real_out_untouched"] = real_out_before == real_out_after == []
    res["real_gitmark_absent"] = not os.path.exists(_git_mark_path())
    res["sec"] = round(time.time() - t0, 1)
    res["ok"] = bool(res["ok"] and res["deleted_unread"] and res["real_out_untouched"] and res["real_gitmark_absent"])
    p = os.path.join(cache, "meta", "_smoke_x_run.json")
    _write_text(p, json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    return res


# ══════════════════════════════════════════════════════════════════════════
#  합성 점검(망 · 실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _fake_out():
    """게시 칸 누수 시험용 합성 산출 — 20년 칸마다 표지 수(0.123456 · 0.987654 · 0.345678 · 0.777777)를 심는다 · 뒤 10년 반쪽 · S 요약 칸은 0.5555."""
    import pandas as pd
    s = pd.Series([0.123456, 0.987654], index=pd.period_range("2006-09", periods=2, freq="M"))
    bear = {"window": ["2006-09", "2026-08"], "n": 240, "abar": 0.123456, "mean_delta": 0.123456, "nw_t": 0.987654, "down_mean": 0.345678,
            "crash_mean": 0.345678, "rg_abs": 0.777777, "half1_mean": 0.123456, "half2_mean": 0.5555, "ool_mean": 0.123456, "n_ool": 92,
            "jackknife": {"n_e": 10, "n_ok": 9, "need": 9, "pass": True, "means": [0.123456] * 10}, "mean_delta_20bp": 0.123456,
            "gates": {"M-C1": False, "M-C2": True, "M-C3": True, "M-C4": False, "M-C5": True, "M-C6": False}, "pass_all": False,
            "p_one_sided_normal": 0.345678, "reports": {"turnover": {"on_share": 0.14, "n_switch": 30}, "concentration_50pct_months": None,
                                                         "yearly_delta_dref": {"2007": 0.123456}, "d0_row": {"mean_delta": 0.123456, "d0_minus_t1": 0.987654}}}
    Mo = {"X-BEAR": bear, "twins": {"T-SMA200": {"mean_delta": 0.123456}}, "measurement": {"X-COMP": {"mean_delta": 0.123456, "p": 0.345678, "by_reject_q10": False},
                                                                                           "X-VTS": {"status": "dropped"}},
          "by_family": ["X-COMP"], "_series": {"delta": s}}
    Io = {"window": ["2006-09", "2026-08"], "n_markets": 10, "markets": ["JP", "NL", "DE", "FR", "IT", "CH", "SE", "CA", "AU", "KR"], "mode": "local",
          "gates": {"I-C1": False, "I-C2": True, "I-C3": True, "I-C4": True}, "pass_all": False, "n_markets_pos": 6,
          "half2": {"window": ["2016-09", "2026-08"], "pooled_mean": 0.5555, "n": 120}, "dk_t": 0.987654, "pooled_mean": 0.123456}
    Go = {"window": ["2006-09", "2026-08"], "LG": {"gates": {"G-C1": False, "G-C2": True, "G-C3": True, "G-C4": True}, "on_share": 0.13, "e_ann": 0.123456},
          "pass_LG": False, "LG_binding": True, "F_G": {"X-GVTREND": {"p": 0.345678}}}
    So = {"window": ["2016-09", "2026-08"], "n": 120, "gates": {"S-C1": True, "S-C2": False, "S-C3": True, "S-C4": False}, "pass_all": False,
          "on_share": 0.1, "e_ann": 0.5555, "e_lb80": 0.5555, "g_down": 0.5555, "g_crash": 0.5555, "turn": 2.5,
          "arms": {"X": {"ann_ex": 0.5555}, "STATIC": {"ann_ex": 0.5555}}}
    return {"M": Mo, "I": Io, "G": Go, "S": So, "labels": {"M 일관성 통과(오염 창)": False, "I 국외 재현": False, "방어 재현": False, "보험 채택 후보": False,
                                                          "랩 발견(맥락)": False},
            "operating": "그대로(EG30 V0)", "multiplicity": {"counts": {"M_primary": 1}, "total": 23,
                                                                                            "cumulative_before": 945, "cumulative_after": 968},
            "lookahead": {"X-BEAR": {"ok": True, "n": 200, "n_bad": 0}}, "s_adapter": {"pairing": {"pairing_B": True}, "sel_hash_same_as_f0": True},
            "arm_status": {"X-VTS": "dropped"}, "n_episodes_label": 10}


def _fake_f0():
    return {"kind": "xbatch_f0", "decisions": {"d_proxy": "main", "g_binding": True, "vxv_pub_in_force": "2009-09-18", "vxv_evidence": False,
                                               "intl_mode": "local", "intl_markets": ["JP", "NL", "DE", "FR", "IT", "CH", "SE", "CA", "AU", "KR"],
                                               "alfred_first_release": False, "french_last_month": "2026-08", "d_sel_hash": "a" * 64, "d_pairing_A": True,
                                               "s_cov_ok": True, "state_agree_pass": True, "lookahead_real_prior": "x",
                                               "d_data_pin": "c6a35ff0168e5ea21c2ab2d18680550452511a3a"},
            "intl": {"decision": {"mode": "local"}}, "labels": {"window": ["2006-09", "2026-08"], "down_months": {"n": 83}},
            "fidelity": {"bear_state_spy_vs_french": {"window": ["2006-08", "2026-07"], "state_agree": "캐시 전체판에만", "n_common": 240, "pass": True}},
            "code_sha": {"build/x_run.py": "0" * 16}, "manifest_sha16": "1" * 16}


def _st_names():
    assert placeholder_counts("a ⟨TBD⟩ b 〔x〕 ⟨TBD") == (2, 1)
    assert placeholder_counts("없음") == (0, 0)
    assert re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-XBATCH\.md", "build/PREREG-2026-09-27-XBATCH.md")
    assert RESULT.endswith("-XBATCH-RESULT.md") and FIRST_ADDED == (PREREG, RUNNER, F0_FILE)
    assert not any("_xfwd" in p for p in FIRST_ADDED + FROZEN)
    return "빈칸 셈 · 이름 꼴 · 처음 더한 파일 셋(전방 창세 없음)"


def _st_start_guard():
    full = "c" * 40
    ok = lambda *a: start_guard(*a) is True
    assert ok(full, None, [], None)
    for args in ((full, None, [("m", full + " x\nFINISHED y")], None), (full, "r", [("m", full + " x\nFINISHED y")], None),
                 (full, None, [], "d" * 40), (full, None, [("m", full + " x")], None), (full, "r", [], None),
                 (full, "r", [("m", "e" * 40 + " x")], None), (full, None, [], full)):
        try:
            start_guard(*args)
            raise AssertionError("시작 표식 갈래가 막히지 않았다: %r" % (args,))
        except SystemExit:
            pass
    assert ok(full, "r", [("m", full + " x")], full) and ok(full, "r", [("m", full + " x")], None)
    return "시작 표식 아홉 갈래(FINISHED · RERUN · 다른 커밋 · 태그)"


def _st_frozen_refuses():
    for env in ({}, {"XBATCH_COMMIT": "0" * 40, "_XBATCH_NO_FETCH": "1"}, {"XBATCH_COMMIT": "HEAD~0000notacommit", "_XBATCH_NO_FETCH": "1"}):
        try:
            frozen_check(env)
            raise AssertionError("판 점검이 통과했다: %r" % env)
        except SystemExit:
            pass
    return "판 점검: 커밋 없음 · 가짜 커밋 · 없는 커밋을 막는다"


def _st_registered():
    bad = registered_constants_ok()
    assert not bad, bad
    XE = _mods()["XE"]
    keep = XE.CRIT
    try:
        XE.CRIT = dict(keep, T240_L6=1.645)
        assert any("XE.CRIT" in b for b in registered_constants_ok())
    finally:
        XE.CRIT = keep
    keep_f = XE.labels
    try:
        XE.labels = lambda *a: None
        assert any("labels" in b for b in registered_constants_ok())
    finally:
        XE.labels = keep_f
    XD = _mods()["XD"]
    assert XD.CACHE_ONLY_KEY == CACHE_ONLY_KEY and XD.PUBLIC_FROM == PUBLIC_FROM
    assert XD.PUBLIC_FLOAT_KEYS.pattern == PUBLIC_FLOAT_KEYS.pattern and XD.COUNT_KEYS.pattern == COUNT_KEYS.pattern
    return "등록 상수 %d · 함수 덮어쓰기 감지 · x_data 공개 규칙 사본 같음" % len(REGISTERED)


def _st_public_leak():
    out = _fake_out()
    pub = public_doc(out, "f" * 64, 123, {"commit": "c" * 40, "registration_error": [], "smoke": False})
    txt = json.dumps(pub, ensure_ascii=False)
    for mk in ("0.123456", "0.987654", "0.345678", "0.777777"):
        assert mk not in txt, "20년 칸 누수 %s" % mk
    assert "0.5555" in txt and pub["M"]["gates"]["M-C1"] is False and pub["xbatch_public_view"]
    assert not public_safe_std(pub) and not _mods()["XD"].public_safe(pub)
    doc = result_doc(pub)
    for mk in ("0.123456", "0.987654", "0.345678", "0.777777", CACHE_ONLY_KEY):
        assert mk not in doc
    assert "## 라벨" in doc and "M-C1" in doc and "누적 N: 945 → 968" in doc and "오염 사고" in doc
    assert "on_share" not in pub["M"] and "on_share_LG" not in pub["G"] and "희석" not in doc     # 20년 켜짐 비율 · G 켜짐 비율 · 희석 메뉴 없음
    st = public_doc({"stopped": "lookahead", "lookahead": {"X-BEAR": {"ok": False, "n": 200, "n_bad": 1}}}, "f" * 64, 1, {"commit": "c" * 40})
    assert st["stopped"] == "lookahead" and not any(st["labels"].values()) and st["lookahead_ok"] is False
    assert _mods()["XE"].LABEL_G_REF in st["labels"] and len(st["labels"]) == 6
    return "게시 칸 · 결과 문서에 20년 표지 수 넷이 새지 않는다 · 멈춤 게시 칸"


def _st_f0_check():
    good = _fake_f0()
    assert f0_check(good) == [], f0_check(good)
    assert f0_check(good, {"build/x_run.py": "0" * 16}, "1" * 16) == []
    assert f0_check(good, {"build/x_run.py": "9" * 16}, "1" * 16)
    assert f0_check(good, {"build/x_run.py": "0" * 16}, "2" * 16)
    b = json.loads(json.dumps(good))
    del b["decisions"]["d_proxy"]
    assert f0_check(b)
    b = json.loads(json.dumps(good))
    b["labels"]["bear_on_share"] = 0.14
    assert any("켜짐 비율" in x for x in f0_check(b))
    b = json.loads(json.dumps(good))
    b["decisions"]["alfred_first_release"] = True
    assert f0_check(b)
    b = json.loads(json.dumps(good))
    b["labels"]["mean_ret"] = 0.0123
    assert any("공개 안전" in x for x in f0_check(b))
    b = json.loads(json.dumps(good))
    b["intl"]["decision"]["mode"] = "pending"
    assert f0_check(b)
    assert f0_check({"kind": "x"}) == ["F0 문서 꼴이 아니다"]
    b = json.loads(json.dumps(good))
    del b["decisions"]["d_data_pin"]
    assert any("d_data_pin" in x for x in f0_check(b))
    full = json.loads(json.dumps(good))                                  # 20년 창 실수(일치율 · corr)는 저장소 판에서 빠진다(캐시 전체판에만)
    full["d_proxy_fidelity"] = {"window": ["2014-06", "2026-08"], "n": 147, "corr_fid": 0.7123, "corr_fid_min": 0.6, "pass": True}
    full["fidelity"]["bear_state_spy_vs_french"]["state_agree"] = 0.97
    assert public_safe_std(full) and _mods()["XD"].public_safe(full)
    pubf = f0_public(full)
    assert f0_check(pubf) == [] and not public_safe_std(pubf) and not _mods()["XD"].public_safe(pubf)
    js = json.dumps(pubf)
    assert "0.7123" not in js and "0.97" not in js and pubf["d_proxy_fidelity"]["pass"] is True and pubf["d_proxy_fidelity"]["n"] == 147
    assert full["d_proxy_fidelity"]["corr_fid"] == 0.7123                # 원본(캐시 전체판)은 그대로
    return "F0 거르개: 결정 칸(D 자료 핀 포함) · 켜짐 비율 칸 · ALFRED 개정 · 20년 창 실수 · I 판정 · 코드 · 명세 sha · 저장소 판은 일치율 · corr 을 뺀다"


def _st_closure():
    clo = static_closure()
    miss = ["build/%s.py" % m for m in clo if "build/%s.py" % m not in FROZEN]
    assert not miss, miss
    assert all(os.path.exists(os.path.join(ROOT, *p.split("/"))) for p in FROZEN if p.startswith("build/"))
    import v_data as VD
    assert tuple(VD.LAB_FILES) == V_DATA_LAB_FILES and tuple(VD.LAB_DIRS) == V_DATA_LAB_DIRS
    assert all(("build/%s.py" % m) in FROZEN for m in X_MODULES)
    XE = _mods()["XE"]
    assert set(XE.FROZEN_BLOBS) <= set(REUSED_MODULES), set(XE.FROZEN_BLOBS) - set(REUSED_MODULES)
    return "정적 폐포 %d 모듈 ⊆ 얼린 파일 %d · v_data 자료 목록 사본 같음" % (len(clo), len(FROZEN))


def _st_guard_copy():
    XD = _mods()["XD"]
    cases = [{"a": 1}, {"window": ["2006-09", "2026-08"], "x": 0.1}, {"window": ["2006-09", "2026-08"], "on_share": 0.1, "n": 3.0},
             {"window": ["2016-09", "2026-08"], "x": 0.1}, {"k": [1, 2, 3, 4, 5]}, {"k": [1, 2, 3, 4]}, XD.mark_cache_only({"a": 1}),
             {"M": {"window": ["2006-09", "2026-08"], "half2": {"window": ["2016-09", "2026-08"], "mean_delta": 0.1}, "mean": 0.2}},
             {"span": ["2007-10", "2009-06"], "n_legs": 2}, {"w": {"window": "2010-01", "v": [0.1]}}]
    for c in cases:
        assert bool(public_safe_std(c)) == bool(XD.public_safe(c)), c
    bad = scan_repo_names(["data/_xfwd/genesis.json", "data/_xbatch.json", "build/F-F_Research_Data_Factors.csv", "data/_xb_other.json",
                           "data/_xb_manifest.json", "data/_xb_f0.json", "build/x_run.py", "raw/VIX_History.csv"])
    assert len(bad) == 6 and not any("_xb_manifest" in b or "_xb_f0.json" in b or "x_run" in b for b in bad), bad
    with tempfile.TemporaryDirectory() as td:
        assert check_no_forward(td) == []
        os.makedirs(os.path.join(td, "data", "_xfwd"))
        assert check_no_forward(td)
    return "공개 안전 표준 사본 = x_data 판(%d 경우) · 이름 규칙(전방 원장 · 산출 · 원자료 · 허용 밖) · 전방 폴더" % len(cases)


def _st_one_shot():
    with tempfile.TemporaryDirectory() as td:
        P = {k: os.path.join(td, v) for k, v in OUT_NAMES.items()}
        P["dir"] = td
        assert _existing_outputs(P) == []
        with io.open(os.path.join(td, "_xbatch.json.part"), "w", encoding="utf-8") as f:
            f.write("{")
        assert _existing_outputs(P)
    return "한 번 굽기: 잘린 산출(.part)도 «쓰였다»"


def _st_windows():
    XD = _mods()["XD"]
    import pandas as pd
    ok = [str(p) for p in pd.period_range("2006-09", "2026-08", freq="M")]
    XD.assert_scored_months(ok)
    for bad in ([str(p) for p in pd.period_range("2006-08", "2026-08", freq="M")], [str(p) for p in pd.period_range("2006-09", "2026-09", freq="M")]):
        passed = False
        try:
            XD.assert_scored_months(bad)
            passed = True
        except (SystemExit, AssertionError):
            pass
        assert not passed, "20년 창 밖 채점 통과"
    passed = False
    try:
        XD.assert_input_floor({"x": pd.Series([1.0], index=pd.DatetimeIndex(["2005-07-29"]))})
        passed = True
    except (SystemExit, AssertionError):
        pass
    assert not passed, "입력 하한 통과"
    assert REGISTERED["XD.SCORE_FIRST"] == "2006-09" and REGISTERED["XD.INPUT_MIN"] == "2005-08-01"
    return "채점 보유월 2006-09 ~ 2026-08 단언 · 입력 ≥ 2005-08-01 단언"


def _st_serialize():
    import numpy as np
    import pandas as pd
    o = {"a": np.float64("nan"), "b": np.int64(3), "c": pd.Series([1.0, np.inf], index=pd.period_range("2020-01", periods=2, freq="M")),
         ("x", 1): np.bool_(True), "d": pd.Period("2020-01", "M"), "e": [np.float32(0.5)]}
    j = json.dumps(_clean(o), allow_nan=False)
    back = json.loads(j)
    assert back["a"] is None and back["b"] == 3 and back["c"]["__series__"]["2020-02"] is None and back["x|1"] is True and back["d"] == "2020-01"
    return "직렬화(NaN · inf · 계열 · 기간 · 튜플 열쇠)"


def _st_wire():
    g0 = "node_modules/\n"
    v0 = "x = 1\nprint(\"사이트 검증:\", 1)\nsys.exit(0)\n"
    g1, v1 = wire_texts(g0, v0)
    assert "_xbatch*" in g1 and "xbatch_cache/" in g1 and g1.startswith(g0)
    assert v1.index("배치 X(PREREG-*-XBATCH") < v1.index('print("사이트 검증:"') and "site_guard_std" in v1
    assert wire_texts(g1, v1) == (g1, v1)
    compile(v1, "validate_site_test", "exec")
    return "덧붙임 덩이(.gitignore · validate_site) 멱등 · 요약 줄 앞 · 문법"


def _st_backup_guard():
    for bad in (os.path.join(ROOT, "x"), os.path.join(tempfile.gettempdir(), "x")):
        try:
            backup(bad)
            raise AssertionError("백업 경로 통과")
        except SystemExit:
            pass
    return "백업: 저장소 · %TEMP% 거부"


def _st_open_encoding():
    with io.open(os.path.abspath(__file__), encoding="utf-8") as f:
        t = ast.parse(f.read())
    bad = []
    for n in ast.walk(t):
        if isinstance(n, ast.Call):
            fn = n.func
            nm = (fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None))
            if nm != "open":
                continue
            if isinstance(fn, ast.Attribute) and getattr(fn.value, "id", None) not in ("io",):
                continue
            mode = n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else next(
                (k.value.value for k in n.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)), "r")
            if "b" in str(mode):
                continue
            if not any(k.arg == "encoding" for k in n.keywords):
                bad.append(n.lineno)
    assert not bad, "encoding 없는 open(): 줄 %s" % bad
    return "open() 텍스트 모드마다 encoding"


def _st_smoke_no_sizes():
    """러너 연기 기록에 값에 따라 달라지는 셈(바이트 · 글자 수 · 게시 칸 키 · 표준출력 길이)이 없다(검토 반영 2026-09-27)."""
    import inspect
    src = inspect.getsource(smoke)
    body = src.split('"""', 2)[-1]                                       # 설명 글 밖(코드)만
    for bad in ('"bytes"', "result_doc_chars", "public_keys", "stdout_chars", "len(txt)", "len(sink"):
        assert bad not in body, bad
    assert '"nonempty"' in body and "result_doc_rendered" in body
    return "러너 연기 기록: 크기 · 길이 · 키 목록 없음(참/거짓만)"


def _st_std_import():
    """모듈 머리(함수 밖) import 는 표준 라이브러리만 — validate_site 가 numpy 없이 불러도 된다."""
    with io.open(os.path.abspath(__file__), encoding="utf-8") as f:
        t = ast.parse(f.read())
    top = set()
    for n in t.body:
        if isinstance(n, ast.Import):
            top |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            top.add(n.module.split(".")[0])
    std = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    assert top <= std, top - std
    return "모듈 머리 import 표준 라이브러리만(%d)" % len(top)


SELFTESTS = (_st_names, _st_start_guard, _st_frozen_refuses, _st_registered, _st_public_leak, _st_f0_check, _st_closure, _st_guard_copy, _st_one_shot,
             _st_windows, _st_serialize, _st_wire, _st_backup_guard, _st_open_encoding, _st_std_import, _st_smoke_no_sizes)


def selftest():
    t0 = time.time()
    ok = 0
    for fn in SELFTESTS:
        try:
            msg = fn()
            ok += 1
            print("  ✅ %s — %s" % (fn.__name__, msg))
        except Exception as e:                               # noqa: BLE001
            print("  ❌ %s — %s: %s" % (fn.__name__, type(e).__name__, str(e)[:300]))
            traceback.print_exc(limit=3)
    print("x_run selftest %d/%d · %.1f초" % (ok, len(SELFTESTS), time.time() - t0))
    return 0 if ok == len(SELFTESTS) else 1


# ══════════════════════════════════════════════════════════════════════════
def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--guard" in argv:
        g = site_guard()
        print(json.dumps(g, ensure_ascii=False, indent=1))
        return 0 if g["ok"] else 1
    if "--pins" in argv:
        rows = pins_table()
        print("| 파일 | git blob(앞 12자) | LF SHA-256(앞 16자) | 추적 |")
        print("|---|---|---|---|")
        for r in rows:
            print("| `%s` | `%s` | `%s` | %s |" % (r["path"], r["blob"], r["sha256_lf"], "origin/main" if r["tracked"] else "새 파일(이 커밋)"))
        return 0
    if "--init-cache-id" in argv:
        print(json.dumps(init_cache_identity(), ensure_ascii=False))
        return 0
    if "--manifest" in argv:
        lit = argv[argv.index("--lit") + 1] if "--lit" in argv else None
        print("→ %s" % manifest_registration(lit))
        return 0
    if "--f0" in argv:
        r = f0()
        print("→ %s · %s · %.0f초" % (r["path"], r["full"], r["sec"]))
        print(f0_table(r["doc"]))
        return 0
    if "--f0-table" in argv:
        print(f0_table())
        return 0
    if "--precommit" in argv:
        r = precommit()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if "--wire" in argv:
        print(json.dumps(wire(apply="--apply" in argv), ensure_ascii=False))
        return 0
    if "--backup" in argv:
        print(json.dumps(backup(), ensure_ascii=False))
        return 0
    if "--restore" in argv:
        print(json.dumps(restore(argv[argv.index("--restore") + 1]), ensure_ascii=False))
        return 0
    if "--smoke" in argv:
        r = smoke(with_f0="--no-f0" not in argv)
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        return 0 if r.get("ok") else 1
    if "--public-view" in argv:
        print(json.dumps(public_view_writer(), ensure_ascii=False))
        return 0
    if "--result-doc" in argv:
        rest = [a for a in argv if not a.startswith("--")]
        pub = _read_json(rest[0] if rest else paths()["public"])
        txt = result_doc(pub)
        if "--write" in argv:
            print("→ %s" % _mods()["XD"].repo_write_text(RESULT, txt))
        else:
            print(txt)
        return 0
    if "--once" in argv:
        once()
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
