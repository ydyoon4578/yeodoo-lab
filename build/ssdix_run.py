# -*- coding: utf-8 -*-
"""build/ssdix_run.py — 확률지배(SSD) 지수 강화 책 역할 검정(SSDIX) 한 번 굽기 러너.

사전등록: build/PREREG-<등록 날짜>-SSDIX.md 하나(이 러너는 날짜를 박지 않는다 · 결과 문서 = 그 이름 + «-RESULT»).
계산은 build/ssdix.py(엔진)가 핀 판 임시 뿌리 셋(EGSTEP 과 같은 뿌리 · 얼린 build/egstep_run.preflight 가 짓는다) 안에서 한다 —
이 러너는 판 점검 · 뿌리(얼린 EGSTEP 판) · 자식 과정 · 시작 표식 · 게시 칸 · 결과 문서만 맡는다.

🚨 사용자 질문(2026-09-28): «퀀트는 대부분 전략보다는 검증 검정용으로 쓰이고있네. 전략은 없나» → 1순위 SSD 책(랩이 한 번도 안 쓴 수학).
   역할 검정 둘(확증 가족 = (A) 하나 · m 1 · 한쪽 α 0.05 · (B) 는 등록 읽기 — 판정 밖): (A) 독립 엔진 — 하락월에 같은 사전 β̂ 의 희석 쌍둥이보다 덜 잃는가 ·
   (B) 방어 스텝 목적지 — 얼린 EGSTEP RD 의 D 자리를 SSD 책으로 바꾸면 하락월에 RD 보다 나은가.
   앞선 지시(모두 유효): ETF · 선물 · 옵션 · 공매도 보유 없음 · «백테스트 최대 20년» · «미래 일정 다 꺼»(전방 원장 없음 — data/_ssdixfwd/ 가 있으면 멈춘다) ·
   새 독립 전략은 EG30 을 쓰지 않는다(SSD 책은 EG30 을 입력으로 쓰지 않는다 · EG30 은 G0 비교 · (B) 의 얼린 RD 코어로만).
🚨 등록 커밋이 origin 에 오르기 전에는 --selftest · --guard · --pins · --manifest · --precommit · --wire · --f0 · --smoke 만 된다.
   --f0 는 개수 · 날짜 · 해시 · 참/거짓 · 비중 통계(G0)만 · --smoke 는 눈가린 채(산출을 열지 않고 지운다 · 참/거짓 · 초만 싣는다).

  python -X utf8 build/ssdix_run.py --selftest           합성만(실자료 없음)
  python -X utf8 build/ssdix_run.py --guard              사이트 경계(site_guard_std — 참/거짓 · 이름만)
  python -X utf8 build/ssdix_run.py --pins               얼린 파일 · 핀 표(등록 문서 §10 표)
  python -X utf8 build/ssdix_run.py --f0                 등록 전 F0(핀 뿌리 셋 · 수익 없음) — 등록 문서 §10 F0 표 · 엔진 F0_EXPECT 의 출처
  python -X utf8 build/ssdix_run.py --manifest           data/_ssdix_manifest.json(해시만) 쓰기
  python -X utf8 build/ssdix_run.py --wire [--apply]     등록 커밋이 .gitignore · build/validate_site.py 끝에 덧붙일 덩이
  python -X utf8 build/ssdix_run.py --precommit          등록 커밋 직전 점검(참/거짓 · 이름만)
  python -X utf8 build/ssdix_run.py --smoke              러너 경로 전체 눈가린 연기(임시 폴더 · 열지 않고 지운다)
  SSDIX_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python -X utf8 build/ssdix_run.py --once     한 번 굽기(이 길 하나뿐)
  python -X utf8 build/ssdix_run.py --public-view        굽기 뒤: 산출 → 게시 칸 다시 쓰기(FINISHED 표식이 있을 때만)
  python -X utf8 build/ssdix_run.py --result-doc [<게시 칸 파일>] [--reg-err <글 파일>] [--write]   결과 문서(게시 칸 파일 하나만 읽는 얼린 렌더러)

뿌리 셋(모두 저장소 밖 캐시 · git archive · 얼린 blob 단언 · 작업 트리의 data/ 를 읽지 않는다 — 얼린 egstep_run.preflight 가 짓고 EGSTEP F0 서명을 대조한다)
  root   얼린 V0 뿌리(x_adapter.build_root) — (A) · (B) 펀드 틀 · EGSTEP RD · C0 · Q06 상태 · 평가 · G0(얼린 V0 목표)
  vroot  배치 V 핀 판(x_adapter.build_vroot) — SSD 책 · 대조 책 · G5 위약 · 앞 창(v_pit.Universe) · D 책(얼린 x_adapter 자식) · 판정(v_tests)
  droot  DSTK 핀 판(dstk_run.materialize) — 가치 다리 V30 · 금리 상태 R(얼린 EGSTEP vleg 자식)
  French 49 산업 일간 · 3요인 일간(202608 CRSP 판 · sha256 핀 · 저장소 밖 캐시) — G6 기전 층(vroot 나무에서)

한 번 굽기 규약(egstep_run · dstk_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(실패하면 멈춘다).
  · SSDIX_COMMIT = 사전등록 문서 · 러너 · 엔진 · 명세(data/_ssdix_manifest.json)를 **처음 더한** 커밋 · origin/main 의 조상 · 그 커밋의 등록 문서에 빈칸(⟨TBD)과 초안 괄호(U+3014)가 없다.
  · 얼린 파일(엔진 · 러너 · 명세 · 등록 문서 · 덧붙임 두 곳)이 그 커밋과 바이트 단위로 같다(CRLF 무시) · 러너가 부르는 재사용 파일(egstep · egstep_run · x_adapter · dstk · dstk_run) blob 이 핀과 같다.
  · 판 점검 → 배타 잠금 → F0(얼린 EGSTEP F0 + SSDIX F0 · 수익 없음 · 등록 F0 서명과 같아야) → 시작 표식 셋(로컬 둘 · origin 태그 ssdix-started · 계산 전에 민다) →
    EGSTEP 가치 다리 · D 책 · SSDIX 책 · G6 · S · 판정 자식 → 게시 칸(공개 안전 점검 · 산출보다 먼저) → 산출 · 게시 칸 · 실행 기록 → FINISHED → 잠금 풀기.
  · FINISHED 가 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤 · 산출 전 기술적 중단이면 이 컴퓨터의 같은 커밋 표식이 있을 때만 SSDIX_RERUN=사유 로 처음부터.
  · 앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 <캐시> 에 남은 작업 폴더(ssdix_work_* · ssdix_f0_* · ssdix_runner_smoke_*)는 굽기 · 연기 · F0 가
    시작할 때 열지 않고 지우고 개수만 적는다(굽기는 실행 기록 · 게시 칸 · 결과 문서 머리에 싣는다).
  · PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 · numpy 2.5.3 · scipy 1.18.1(HiGHS 내장) · pandas 3.0.6. 표준출력은 경로 · sha256 앞 16자 · 초만.
"""
from __future__ import annotations

import ast
import glob
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
# 🔒 모듈 머리에서는 표준 라이브러리만 — build/validate_site.py 가 site_guard_std 를 부른다(numpy 없이). 엔진 · 재사용 모듈은 함수 안에서만 불러온다.


# ══════════════════════════════════════════════════════════════════════════
#  등록 문서 · 얼린 파일 · 핀
# ══════════════════════════════════════════════════════════════════════════
def _find_prereg():
    c = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-SSDIX.md")))
    return ("build/" + c[0]) if len(c) == 1 else "build/PREREG-0000-00-00-SSDIX.md", len(c)


PREREG, _N_PREREG = _find_prereg()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"
ENGINE = "build/ssdix.py"
RUNNER = "build/ssdix_run.py"
MANIFEST_FILE = "data/_ssdix_manifest.json"
FIRST_ADDED = (PREREG, RUNNER, ENGINE, MANIFEST_FILE)
FROZEN = (ENGINE, RUNNER, MANIFEST_FILE, PREREG)
REPO_ALLOWED_SSDIX = (MANIFEST_FILE,)
FORWARD_DIR = "data/_ssdixfwd"                                # 있으면 멈춘다(전방 원장 없음 — 사용자 2026-09-27 «미래 일정 다 꺼»)
# 러너 · 뿌리가 부르는 재사용 파일(작업 트리 = 등록 커밋 판) — git blob(LF 바이트)이 이 값이어야 한다
REUSED_BLOBS = {"build/egstep.py": "2749cbe238910e78e5ab4e36a98969b1553a7444",           # EGSTEP 등록 판(엔진 · RD 몫 · 상태 · mix_t1_multi)
                "build/egstep_run.py": "71a8bdd9f1f080a887b54f66c18bf44251030c5f",       # EGSTEP 등록 판(러너 · preflight · 뿌리 셋 · 자식 부르기)
                "build/x_adapter.py": "897c4c94b22e415f38e32ac47bf8037025f28cb2",        # 배치 X 등록 판(S 층 어댑터)
                "build/dstk.py": "60e634875df6a42f191b6ce91fd391dffc721d4f",             # DSTK 등록 판(엔진 · 선택 점검의 book_path 원본)
                "build/dstk_run.py": "4bc0306e1b0aa638fa13574751d098bb9590f991",         # DSTK 등록 판(러너 · materialize · 핀)
                "build/v_cmp.py": "0ef32e81a4c97283e8d0e945cee234955025e88d"}           # 배치 V 등록 판(G-EGD 식 — 합성 점검에서 엔진 식과 대조)
EGSTEP_OUT_SHA = "28234607383080a6e00f8ad1e7d1310067a59b6122eebf46becbaab4399dce3f"     # EGSTEP 굽기 산출(_egstepout.json · 결과 문서 머리의 sha 앞 16 과 같다) — 짝맞춤 E-RD
EGSTEP_OUT = os.environ.get("SSDIX_EGSTEP_OUT") or os.path.join(tempfile.gettempdir(), "egstep_cache", "out", "_egstepout.json")
FRENCH_DIR = os.environ.get("SSDIX_FRENCH") or os.path.join(tempfile.gettempdir(), "ssdix_cache", "raw", "french")
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
CHILD_ENV_DROP = ("SSDIX_COMMIT", "SSDIX_RERUN", "SSDIX_SMOKE", "EGSTEP_COMMIT", "EGSTEP_RERUN", "EGSTEP_SMOKE", "LAB_ASOF", "VBATCH_CACHE",
                  "VBATCH_FRENCH_SEED", "DSTK_COMMIT", "DSTK_RERUN")
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"
SMOKE_ENV_KEYS = ("SSDIX_SMOKE",)
TIMEOUT = 4 * 3600
FORBIDDEN_ENGINE_NAMES = ("ff1", "ff2", "ff0", "forward_ledger", "genesis")    # 전방 판정 · 원장 함수가 엔진에 없어야 한다
# 등록 상수 — 엔진(ssdix)의 값과 같아야 굽는다(등록 문서 §3 ~ §9)
REGISTERED = {
    "S_WIN": 200, "CAP": 0.20, "TIE_EPS": 1e-6, "CUT_TOL": 1e-9, "CUT_ROUND": 30, "CUT_MAX_IT": 400, "W_ZERO": 1e-6, "LP_METHOD": "highs-ds",
    "LP_OPTS": {"presolve": True, "time_limit": 600.0, "primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9},
    "SEED_LEVELS": (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144), "CVAR_S": 10, "SECTOR_BAND": 0.05,
    "HOLD": ("2016-09", "2026-08"), "N_HOLD": 120, "FORM_WARM": "2016-07", "FORM_FIRST": "2016-08", "FORM_LAST": "2026-07",
    "PRE_HOLD": ("2015-04", "2016-08"), "PRE_WARM": "2015-02", "PRE_FIRST": "2015-03", "PRE_LAST": "2016-07",
    "G6_HOLD": ("2006-09", "2026-08"), "G6_WARM": "2006-07", "G6_FIRST": "2006-08", "G6_LAST": "2026-07",
    "COST": 0.0010, "COST20": 0.0020, "PRIMARY": ("A",), "READING_ARMS": ("B",), "HOLM_ALPHA": 0.05, "DOWN_LAG": 3, "K_PLACEBO": 1000, "SEED_PLACEBO": 20260930,
    "BETA_BAND": 0.01, "PLACEBO_TRIES": 50, "PLACEBO_LAMBDA": 60.0, "G0_CORR_MAX": 0.30, "G0_OVX_MAX": 0.10, "G2_LB": -0.15, "Z80": 0.8416,
    "G4_MIN": 3, "BLOCK_LEN": 30, "G5_PCT": 95.0, "G6_T_MIN": 1.0, "TURN_MAX": 10.0, "REB_SLACK": 1,
    "FP_WIN": 252, "FP_MIN": 200, "FP_K": 5, "FP_W": 0.5, "LP_VARIANTS": ("SSD", "C10", "C4", "C3", "C5"), "BASKETS": ("C7A", "C7B"),
    "CHAINS": ("SSD", "PRE", "C10", "C4", "C3", "C5"), "CUM_N_BEFORE": 1063, "COUNTED": ("A", "B", "C3", "C4", "C5", "C7A", "C10", "G6"),
    "N_ROWS_COUNTED": 8, "EGSTEP_ENGINE_BLOB": "2749cbe238910e78e5ab4e36a98969b1553a7444",
    "ROOT_BLOBS": {"qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "q_switch": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
                   "q_corrsurp": "d32a270e2db0682f8b940ffe647607d15b57ba52", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
                   "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2",
                   "egstep": "2749cbe238910e78e5ab4e36a98969b1553a7444"},
    "VROOT_BLOBS": {"v_pit": "5983b9902b106a2b234db05a397e9ce0b73fb689", "v_data": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a",
                    "v_fund": "2d8093f0009c09b05f597e07eea10f53c8d18b8e", "v_px_split": "c747ae4030c4f2f5bc97b8e634f3a80a36d04028",
                    "pit_panel": "e207370369aaa2d71d92dcac4ecbcd79d0df9b38", "pit_alias": "ead714d97c87c3588a8fdc2ca4b1c57c5a497c0b",
                    "pit_quarantine": "329e5d9ff15be4c07052921dfff9a41afbcc2513", "tech_backtest": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79",
                    "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628", "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d",
                    "v_tests": "2f1ec4db1cd7458564da73ec5ad88cef8a0b2f2f", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2"},
    "FRENCH_FILES": {"ind49_d": ("49_Industry_Portfolios_daily_CSV.zip", "8f394fe34bea54d41b9aafed410425ee8f8e252ede3c71a7c1cd20bab83040de"),
                     "ff3_d": ("F-F_Research_Data_Factors_daily_CSV.zip", "2f29e22546069914890a712680a6f81f3680ebc3543b52864484d209ca13a7db")},
    "FRENCH_VINTAGE": "202608",
    "F0_EXPECT": {'egstep_f0_ok': True, 'g0_corr_x1000': -14, 'g0_months': 120, 'g0_ovx_x1000': -89, 'g0_pass': True, 'g6_carried': 0, 'g6_drops': 0, 'g6_elig_max': 49, 'g6_elig_min': 49, 'g6_first': '2005-01-03', 'g6_forms': 241, 'g6_hash16': 'ab1d973c4f8910b0', 'g6_last': '2026-08-31', 'g6_n_missing_cells': 0, 'g6_names_max': 15, 'g6_names_min': 6, 'g6_ok1': 241, 'g6_ok2': 241, 'g6_ties_gt5pct': 6, 'g6_vintage_ok': True, 'grid_same': True, 'n_eg_forms': 41, 'n_win_dates': 2513, 'spy_same': False, 't_C10_carried': 0, 't_C10_drops': 6, 't_C10_hash16': '93b695d15088abc5', 't_C10_names_max': 39, 't_C10_names_min': 13, 't_C10_ok1': 121, 't_C10_ok2': 121, 't_C10_tie_max_x1000': 52, 't_C10_tie_med_x1000': 11, 't_C10_ties_gt5pct': 1, 't_C3_carried': 0, 't_C3_drops': 6, 't_C3_hash16': 'da745ccf2970068e', 't_C3_names_max': 69, 't_C3_names_min': 17, 't_C3_ok1': 121, 't_C3_ok2': 121, 't_C3_tie_max_x1000': 87, 't_C3_tie_med_x1000': 15, 't_C3_ties_gt5pct': 7, 't_C4_carried': 0, 't_C4_drops': 7, 't_C4_hash16': '421ec4c0e8d91648', 't_C4_names_max': 42, 't_C4_names_min': 8, 't_C4_ok1': 121, 't_C4_ok2': 121, 't_C4_tie_max_x1000': 302, 't_C4_tie_med_x1000': 79, 't_C4_ties_gt5pct': 84, 't_C5_carried': 0, 't_C5_drops': 4, 't_C5_hash16': 'e290e106772e8d7f', 't_C5_names_max': 46, 't_C5_names_min': 10, 't_C5_ok1': 121, 't_C5_ok2': 121, 't_C5_tie_max_x1000': 147, 't_C5_tie_med_x1000': 2, 't_C5_ties_gt5pct': 3, 't_C7A_carried': 0, 't_C7A_drops': 51, 't_C7A_hash16': '19e2f00855d94653', 't_C7A_names_max': 511, 't_C7A_names_min': 461, 't_C7B_carried': 0, 't_C7B_drops': 50, 't_C7B_hash16': 'b70bc68c2d5c696b', 't_C7B_names_max': 511, 't_C7B_names_min': 459, 't_PRE_carried': 0, 't_PRE_drops': 1, 't_PRE_hash16': '466d36d9de0868c8', 't_PRE_names_max': 21, 't_PRE_names_min': 6, 't_PRE_ok1': 18, 't_PRE_ok2': 18, 't_PRE_tie_max_x1000': 36, 't_PRE_tie_med_x1000': 13, 't_PRE_ties_gt5pct': 0, 't_SSD_carried': 0, 't_SSD_drops': 4, 't_SSD_hash16': '376eb2b46e2174b0', 't_SSD_names_max': 35, 't_SSD_names_min': 6, 't_SSD_ok1': 121, 't_SSD_ok2': 121, 't_SSD_tie_max_x1000': 41, 't_SSD_tie_med_x1000': 10, 't_SSD_ties_gt5pct': 0, 't_beta_missing_elig_max': 0, 't_cov_med_x1000': 973, 't_cov_min_x1000': 895, 't_covw_min_x1000': 985, 't_elig_max': 511, 't_elig_med': 501, 't_elig_min': 461, 't_exec_bad_max': 37, 't_members_max': 521, 't_members_min': 509, 't_months_cov_lt90': 1, 't_n_forms_main': 121, 't_n_forms_pre': 18, 't_placebo_fallback': 2576, 't_placebo_hash16': '680f7bb04eab2d7f', 't_sec_none_max': 10, 'v0_hash_ok': True},
}


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록 · 임시 뿌리는 모두 저장소 밖(<캐시>)
# ══════════════════════════════════════════════════════════════════════════
CACHE = os.environ.get("SSDIX_CACHE") or os.path.join(tempfile.gettempdir(), "ssdix_cache")
GIT_MARK_NAME = "ssdix_started"
START_TAG = "ssdix-started"
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}
OUT_NAMES = {"out": "_ssdixout.json", "mark": "_ssdixout.started", "runlog": "_ssdixout.run.json", "public": "_ssdixout.public.json"}
CACHE_ONLY_KEY = "__ssdix_cache_only__"
PUBLIC_FROM = "2016-09"
PUBLIC_FLOAT_KEYS = re.compile(r"(^|_)(coverage|frac|tol|min|max|thr|sec)(_|$)")
COUNT_KEYS = re.compile(r"(^n$|^n_|_n$|count|^k$|months?$|days?$|years?$|^rows$|bytes$|names|forms)")
OUTPUT_NAME_MARKS = ("_ssdixout",)
OUTPUT_CONTENT_MARKS = (CACHE_ONLY_KEY.encode(), b"_ssdixout.json", b"_ssdixout.public.json", b"_ssdixout.run.json", b'"ssdix_public_view"')
STALE_PREFIXES = ("ssdix_work_", "ssdix_f0_", "ssdix_runner_smoke_")


def _norm(p):
    return os.path.normcase(os.path.abspath(os.fspath(p)))


def _inside(p, root):
    a, r = _norm(p), _norm(root)
    return a == r or a.startswith(r + os.sep)


def cache_guard_std(cache=None, root=None):
    c, r = cache or CACHE, root or ROOT
    if _inside(c, r) or _inside(r, c):
        raise SystemExit("🚨 캐시(%s)가 저장소(%s) 안이다 — 산출 · 임시 뿌리는 저장소 밖에만." % (c, r))
    return os.path.abspath(c)


def _git(*a, root=None):
    return subprocess.run(["git", "-C", root or ROOT] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")


def _git_bytes(*a, root=None):
    return subprocess.run(["git", "-C", root or ROOT] + list(a), capture_output=True)


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
    have = [P["out"], P["runlog"], P["public"]]
    if os.path.isdir(P["dir"]):
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith("_ssdixout") and (f.endswith(".json") or f.endswith(".part"))]
    return sorted({p for p in have if os.path.exists(p)})


def _stale_dirs(cache):
    if not os.path.isdir(cache):
        return []
    return sorted(os.path.join(cache, d) for d in os.listdir(cache)
                  if d.startswith(STALE_PREFIXES) and os.path.isdir(os.path.join(cache, d)))


def purge_stale(cache=None):
    """앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 <캐시> 바로 밑에 남은 작업 폴더를 열지 않고 지운다 — 개수만 돌려준다(이름 · 크기 · 값 없음).
    그 폴더에는 자식 산출(팔 월 계열 · 판정)이 있을 수 있다 — 지운 개수를 실행 기록 · 게시 칸 · 결과 문서 머리에 싣는다(등록 §10-2).
    🚨 굽기 · 연기 · F0 를 동시에 돌리지 않는다(서로의 작업 폴더를 지운다)."""
    c = cache or cache_guard_std()
    ds = _stale_dirs(c)
    for d in ds:
        shutil.rmtree(d, ignore_errors=True)
    left = _stale_dirs(c)
    if left:
        raise SystemExit("🚨 남은 작업 폴더 %d 개를 지우지 못했다 — 굽지 않는다." % len(left))
    return len(ds)


def _sha_lf(b):
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def git_blob_sha(b):
    """git hash-object 와 같은 blob sha1(바이트 그대로)."""
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def _bytes(p):
    with open(p, "rb") as f:
        return f.read()


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


def _write_json(p, obj):
    _write_text(p, json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_NUM = re.compile(r"(?<![A-Za-z_0-9.])[-+]?(?:\d+\.\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+)")


def _scrub(s):
    """오류 꼬리에서 소수 · 지수꼴을 <num> 으로(값이 새지 않게). 정수는 남긴다 — 줄 번호 · 개수 · 날짜라서다."""
    return "\n".join(l if l.strip().startswith("File ") else _NUM.sub("<num>", l) for l in (s or "").splitlines())


# ══════════════════════════════════════════════════════════════════════════
#  공개 안전 · 사이트 경계(표준 라이브러리만 — validate_site 가 부른다)
# ══════════════════════════════════════════════════════════════════════════
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
    """공개 안전 — (가) 캐시 표지 (나) 창이 2016-09 앞에서 시작하는 칸의 실수(커버리지 · 비율 · 개수 칸 제외) (다) 값 계열 같은 숫자 목록(> 4)."""
    bad = []
    if isinstance(doc, dict):
        if doc.get(CACHE_ONLY_KEY):
            bad.append("%s: 캐시 표지(%s)" % (path or "/", CACHE_ONLY_KEY))
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


def manifest_problems(doc):
    """명세는 해시만 — 실수 · 긴 숫자 목록 · 캐시 표지 · 굽기 산출 표식이 없어야 한다."""
    bad = []

    def walk(x, p):
        if isinstance(x, float):
            bad.append("%s: 실수" % p)
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, p + "/" + str(k))
        elif isinstance(x, (list, tuple)):
            for q, v in enumerate(x):
                walk(v, "%s[%d]" % (p, q))
    walk(doc, "")
    bad += public_safe_std(doc)
    blob = json.dumps(doc, ensure_ascii=False).encode("utf-8")
    bad += ["굽기 산출 표식 %s" % m.decode() for m in OUTPUT_CONTENT_MARKS if m in blob]
    return bad


def scan_repo_names(files):
    bad = []
    for f in files:
        b = os.path.basename(f)
        if any(b.startswith(mk) for mk in OUTPUT_NAME_MARKS):
            bad.append("굽기 산출 이름: %s" % f)
        if f.startswith("data/_ssdix") and f not in REPO_ALLOWED_SSDIX:
            bad.append("허용 밖 파일: %s" % f)
        if f.startswith(FORWARD_DIR + "/") or f == FORWARD_DIR:
            bad.append("전방 원장 파일(사용자 2026-09-27 «미래 일정 다 꺼»): %s" % f)
        if "ssdix_cache" in f:
            bad.append("캐시 사본으로 보이는 파일: %s" % f)
        if b.endswith(".zip") and ("Industry_Portfolios" in b or "F-F_Research" in b):
            bad.append("French 원자료 사본(저장소 밖 캐시에만): %s" % f)
    return bad


def site_guard_std(root=None):
    """SSDIX 사이트 경계 — git 이 추적 · 추가 예정인 파일 가운데 (가) 굽기 산출 이름(_ssdixout*) (나) 허용 밖 data/_ssdix* (다) 전방 원장 data/_ssdixfwd/*
    (라) 명세(data/_ssdix_manifest.json)가 해시만인가 (마) 사이트 자료(뿌리 *.html · js/*.js · data/*.json)의 굽기 산출 표식 (바) French 원자료 사본."""
    root = root or ROOT
    p = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return {"ok": False, "bad": ["git ls-files 실패"], "n_bad": 1, "n_files": 0, "n_scanned": 0}
    files = [x for x in p.stdout.splitlines() if x]
    bad = scan_repo_names(files)
    if os.path.isdir(os.path.join(root, *FORWARD_DIR.split("/"))):
        bad.append("전방 원장 폴더 %s 가 있다(무시 파일 포함)" % FORWARD_DIR)
    fp = os.path.join(root, *MANIFEST_FILE.split("/"))
    if MANIFEST_FILE in files and os.path.exists(fp):
        try:
            bad += ["%s: %s" % (MANIFEST_FILE, x) for x in manifest_problems(_read_json(fp))[:3]]
        except Exception as e:                                # noqa: BLE001
            bad.append("%s: 읽지 못함(%s)" % (MANIFEST_FILE, type(e).__name__))
    scan = [f for f in files if (("/" not in f and f.endswith(".html")) or (f.startswith("js/") and f.endswith(".js"))
                                 or (f.startswith("data/") and f.endswith(".json") and f.count("/") == 1))]
    n_scanned = 0
    for f in scan:
        fq = os.path.join(root, f)
        if not os.path.isfile(fq):
            continue
        blob = _bytes(fq)
        n_scanned += 1
        hit = [m.decode() for m in OUTPUT_CONTENT_MARKS if m in blob]
        if hit:
            bad.append("사이트 자료 %s 에 SSDIX 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


# ── 덧붙임 두 곳(.gitignore · validate_site) ─────────────────────────────
GITIGNORE_BLOCK = """
# 확률지배(SSD) 지수 강화 책 역할 검정(PREREG-*-SSDIX · 사용자 2026-09-28 «퀀트 전략은 없나») — 굽기 산출(_ssdixout.json ·
#   _ssdixout.public.json · _ssdixout.run.json · _ssdixout.started)이나 캐시 사본(ssdix_cache)이 작업 트리에 복사돼도 쓸려 들지 않게.
#   명세(data/_ssdix_manifest.json)는 «_ssdix_» 라 걸리지 않는다.
_ssdixout*
ssdix_cache/
"""
VALIDATE_BLOCK = """
# ── 확률지배(SSD) 지수 강화 책 역할 검정(PREREG-*-SSDIX · 사용자 2026-09-28) 사이트 경계 ─────────────────────────────
# 굽기 산출(_ssdixout*)이 저장소 · 사이트 자료에 없어야 한다. data/_ssdix* 는 해시만 담은 명세(_ssdix_manifest) 하나뿐 ·
#   data/_ssdixfwd/ 없음(전방 원장 없음 · 사용자 2026-09-27 «미래 일정 다 꺼») · 사이트 자료에 굽기 산출 표식 없음 · French 원자료 사본 없음.
#   build/ssdix_run.py 는 모듈 머리에서 표준 라이브러리만 불러온다(site_guard_std). 러너(ssdix_run.frozen_check)도 같은 함수를 부른다.
try:
    import importlib as _il_ssdix
    _ssr = _il_ssdix.import_module("ssdix_run")
    _gss = _ssr.site_guard_std(ROOT)
    if not _gss["ok"]:
        errors.append("SSD 지수 강화 역할 검정 사이트 경계 위반 %d건 — %s. 굽기 산출(_ssdixout*)은 저장소 밖 캐시에만 둔다"
                      % (_gss.get("n_bad", len(_gss["bad"])), " · ".join(_gss["bad"][:4])))
    else:
        print("  ~ SSD 지수 강화 역할 검정 사이트 경계 통과(파일 %d · 사이트 자료 %d 훑음)" % (_gss["n_files"], _gss["n_scanned"]))
except Exception as _e:
    # 닫힌 쪽 — 이 경계를 확인하지 못하면 통과시키지 않는다(EGSTEP · DSTK · GURUFUND 와 같은 규약)
    errors.append("SSD 지수 강화 역할 검정 사이트 경계 검사가 예외로 죽었다 — %s (확인하지 못하면 통과시키지 않는다)" % str(_e)[:80])
"""
_VALIDATE_ANCHOR = 'print("사이트 검증:"'


def wire_texts(gitignore_txt, validate_txt):
    g = gitignore_txt
    if "_ssdixout*" not in g:
        g = g.rstrip("\n") + "\n" + GITIGNORE_BLOCK
    v = validate_txt
    if "확률지배(SSD) 지수 강화 책 역할 검정(PREREG-*-SSDIX" not in v:
        i = v.rfind(_VALIDATE_ANCHOR)
        if i < 0:
            raise SystemExit("🚨 validate_site.py 의 마지막 요약 줄을 찾지 못했다")
        v = v[:i] + VALIDATE_BLOCK.lstrip("\n") + "\n" + v[i:]
    return g, v


def wired_state(root=None):
    root = root or ROOT
    gt, vt = _read_text(os.path.join(root, ".gitignore")), _read_text(os.path.join(root, "build", "validate_site.py"))
    g1, v1 = wire_texts(gt, vt)
    return g1 == gt, v1 == vt


def wire(apply=False):
    gp, vp = os.path.join(ROOT, ".gitignore"), os.path.join(ROOT, "build", "validate_site.py")
    g0, v0 = _read_text(gp), _read_text(vp)
    g1, v1 = wire_texts(g0, v0)
    res = {"gitignore_changed": g1 != g0, "validate_changed": v1 != v0, "applied": False}
    if apply:
        for p, a, b in ((gp, g0, g1), (vp, v0, v1)):
            if a != b:
                with io.open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(b)
        res["applied"] = True
    return res


def check_no_forward(root=None):
    root = root or ROOT
    return (["전방 원장 폴더가 있다: %s" % FORWARD_DIR] if os.path.exists(os.path.join(root, *FORWARD_DIR.split("/"))) else [])


# ══════════════════════════════════════════════════════════════════════════
#  이름 · 등록 상수 · 재사용 blob · 핀 · 명세 · 저장소 밖 입력
# ══════════════════════════════════════════════════════════════════════════
def name_check():
    bad = []
    if _N_PREREG != 1:
        bad.append("build/PREREG-*-SSDIX.md 가 %d 개" % _N_PREREG)
    elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-SSDIX\.md", PREREG):
        bad.append("이름 꼴: %s" % PREREG)
    return bad


def placeholder_counts(text):
    return text.count(PLACEHOLDER), text.count(DRAFT_MARK)


def _normv(x):
    if isinstance(x, (list, tuple)):
        return tuple(_normv(v) for v in x)
    if isinstance(x, dict):
        return {str(k): _normv(v) for k, v in x.items()}
    if isinstance(x, bool):
        return x
    if isinstance(x, float):
        return round(x, 15)
    return x


def registered_constants_ok(E=None):
    if E is None:
        import ssdix as E
    bad = []
    for k, want in REGISTERED.items():
        have = getattr(E, k, "<없음>")
        if _normv(have) != _normv(want):
            bad.append("%s = %r (등록 %r)" % (k, have if not isinstance(have, dict) or len(str(have)) < 120 else "{…}", want if not isinstance(want, dict) or len(str(want)) < 120 else "{…}"))
    for nm in FORBIDDEN_ENGINE_NAMES:
        if hasattr(E, nm):
            bad.append("엔진에 %s 가 있다(전방 판정 · 원장 없음)" % nm)
    for k in SMOKE_ENV_KEYS:
        if os.environ.get(k):
            bad.append("연기 전용 환경 변수 %s 가 켜져 있다" % k)
    return bad


def reused_problems(root=None):
    """러너 · 뿌리가 부르는 재사용 파일의 blob(LF 바이트) — 핀과 같아야 한다."""
    root = root or ROOT
    bad = []
    for f, b in REUSED_BLOBS.items():
        fp = os.path.join(root, *f.split("/"))
        got = git_blob_sha(_bytes(fp).replace(b"\r\n", b"\n")) if os.path.exists(fp) else None
        if got != b:
            bad.append("%s blob %s(핀 %s)" % (f, (got or "없음")[:12], b[:12]))
    return bad


def code_shas():
    return {p: (_sha_lf(_bytes(os.path.join(ROOT, *p.split("/"))))[:16] if os.path.exists(os.path.join(ROOT, *p.split("/"))) else None)
            for p in (ENGINE, RUNNER)}


def _ER():
    """얼린 EGSTEP 러너(등록 판 · blob 핀) — 뿌리 셋 · EGSTEP F0 · 자식 부르기를 그대로 쓴다."""
    import egstep_run as ER
    return ER


def pins_check():
    """뿌리 핀 셋 — 얼린 egstep_run.pins_check(EGSTEP 핀 · 재사용 blob · 커밋 조상 · 트리) + 이 러너의 재사용 blob."""
    bad = reused_problems()
    if bad:
        return bad
    return list(_ER().pins_check())


def french_paths():
    return {fid: os.path.join(FRENCH_DIR, fn) for fid, (fn, _sha) in REGISTERED["FRENCH_FILES"].items()}


def ext_problems():
    """저장소 밖 입력 — 얼린 egstep_run.ext_problems(VB 넘김 sha · V-D1 묶음) · French 두 파일 sha256 · EGSTEP 굽기 산출 sha256(짝맞춤 E-RD)."""
    bad = list(_ER().ext_problems())
    for fid, p in french_paths().items():
        if _inside(p, ROOT):
            bad.append("French %s 가 저장소 안이다" % fid)
        elif not os.path.exists(p):
            bad.append("French 파일 없음(%s)" % os.path.basename(p))
        elif _sha_file(p) != REGISTERED["FRENCH_FILES"][fid][1]:
            bad.append("French %s sha256 이 등록 값과 다르다" % fid)
    if _inside(EGSTEP_OUT, ROOT):
        bad.append("EGSTEP 굽기 산출이 저장소 안이다")
    elif not os.path.exists(EGSTEP_OUT):
        bad.append("EGSTEP 굽기 산출 없음(짝맞춤 E-RD)")
    elif _sha_file(EGSTEP_OUT) != EGSTEP_OUT_SHA:
        bad.append("EGSTEP 굽기 산출 sha256 이 등록 값과 다르다")
    return bad


def manifest_doc():
    """data/_ssdix_manifest.json — 해시만(값 없음)."""
    ER = _ER()
    eg = ER.manifest_doc()
    return {"kind": "ssdix_manifest", "note": "확률지배(SSD) 지수 강화 책 역할 검정(SSDIX) 명세 — 해시만(값 없음). 러너 판 점검이 이 파일을 등록 커밋 판과 대조한다.",
            "prereg": PREREG, "engine": ENGINE, "runner": RUNNER,
            "code_sha256_lf": {p: (_sha_lf(_bytes(os.path.join(ROOT, *p.split("/")))) if os.path.exists(os.path.join(ROOT, *p.split("/"))) else None)
                               for p in (ENGINE, RUNNER)},
            "reused_blobs": dict(REUSED_BLOBS),
            "roots": {"builder": "egstep_run.preflight(얼린 EGSTEP 판 — x_adapter.build_root · build_vroot · dstk_run.materialize)",
                      "egstep_roots": eg["roots"], "egstep_manifest_code_sha256_lf": eg["code_sha256_lf"],
                      "engine_asserts": {"root": dict(REGISTERED["ROOT_BLOBS"]), "vroot": dict(REGISTERED["VROOT_BLOBS"])}},
            "external": {"french": {fid: {"file": fn, "sha256": sha} for fid, (fn, sha) in REGISTERED["FRENCH_FILES"].items()},
                         "french_vintage_crsp": REGISTERED["FRENCH_VINTAGE"], "egstep_out_sha256": EGSTEP_OUT_SHA,
                         "vb_books_sha256": ER.VB_BOOKS_SHA, "vd1_digest": ER.REGISTERED["DSTK_EXPECT"]["VD1_DIGEST"]},
            "start_tag": START_TAG, "git_mark": GIT_MARK_NAME, "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼»"}


def write_manifest():
    doc = manifest_doc()
    bad = manifest_problems(doc)
    if bad:
        raise SystemExit("🚨 명세가 해시만이 아니다: %s" % bad[:3])
    _write_text(os.path.join(ROOT, *MANIFEST_FILE.split("/")), json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    return {"path": MANIFEST_FILE, "sha256_16": _sha_file(os.path.join(ROOT, *MANIFEST_FILE.split("/")))[:16]}


def manifest_check():
    p = os.path.join(ROOT, *MANIFEST_FILE.split("/"))
    if not os.path.exists(p):
        return ["명세 없음(--manifest)"]
    doc = _read_json(p)
    want = manifest_doc()
    bad = []
    if doc.get("code_sha256_lf") != want["code_sha256_lf"]:
        bad.append("명세의 코드 sha 가 지금 엔진 · 러너와 다르다(--manifest 다시)")
    for k in ("reused_blobs", "roots", "external", "prereg", "start_tag"):
        if doc.get(k) != want.get(k):
            bad.append("명세 %s 가 러너 상수와 다르다" % k)
    bad += manifest_problems(doc)
    return bad


# ══════════════════════════════════════════════════════════════════════════
#  시작 표식(순수 규칙 · selftest 가 모든 갈래를 본다)
# ══════════════════════════════════════════════════════════════════════════
def _remote_start_tag():
    r = _git("ls-remote", "--tags", "origin", "refs/tags/" + START_TAG)
    if r.returncode != 0:
        raise SystemExit("🚨 origin 시작 태그를 확인하지 못했다(git ls-remote 실패) — 모르면 굽지 않는다.")
    lines = [x.split() for x in r.stdout.splitlines() if x.strip()]
    return lines[0][0] if lines else None


def start_guard(full, rerun, marks, remote_tag):
    if any(FINISHED in txt for _, txt in marks):
        raise SystemExit("🚨 굽기가 이미 끝났다(시작 표식에 %s 줄) — 다시 굽기는 새 등록." % FINISHED)
    if remote_tag is not None and remote_tag != full:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다 — 다시 굽기는 새 등록." % remote_tag[:8])
    if marks and not rerun:
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 SSDIX_RERUN=사유 로 처음부터." % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 SSDIX_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다.")
    if rerun and not all(txt.startswith(full) for _, txt in marks):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    if remote_tag is not None and not rerun:
        raise SystemExit("🚨 origin 에 시작 태그(%s)가 있다 — 한 번 굽기가 이미 시작됐다." % START_TAG)
    return True


def _tag_now():
    """지금의 origin 시작 태그(연기 판이면 대리 파일) — 잠근 뒤 다시 본다."""
    if _OVR["tag"]:
        p = os.path.join(_OVR["tag"], START_TAG)
        return _read_text(p).strip() if os.path.exists(p) else None
    return _remote_start_tag()


def _push_start_tag(commit, rerun=None):
    """시작 태그를 민다. 이미 같은 커밋을 가리키면 SSDIX_RERUN(산출 전 기술적 중단의 다시 굽기)일 때만 «already» — 아니면 멈춘다(동시 굽기 막기)."""
    if _OVR["tag"]:
        p = os.path.join(_OVR["tag"], START_TAG)
        if os.path.exists(p):
            if not rerun:
                raise SystemExit("🚨 시작 태그(대리)가 이미 있다 — 다른 굽기가 시작했다.")
            return "already"
        _write_text(p, commit + "\n")
        return "override"
    have = _remote_start_tag()
    if have == commit:
        if not rerun:
            raise SystemExit("🚨 origin 시작 태그가 이미 이 커밋을 가리킨다 — 다른 굽기가 시작했다(SSDIX_RERUN 이 아니면 굽지 않는다).")
        return "already"
    if have is not None:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다." % have[:8])
    r1 = _git("tag", "-f", START_TAG, commit)
    r2 = _git("push", "--quiet", "origin", "refs/tags/%s:refs/tags/%s" % (START_TAG, START_TAG))
    if r1.returncode != 0 or r2.returncode != 0 or _remote_start_tag() != commit:
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다 — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 SSDIX_RERUN).")
    return "pushed"


LOCK_NAME = "_ssdix_bake.lock"


def _take_lock(P, commit):
    """배타 잠금(O_EXCL) — 판 점검 뒤 · 핀 뿌리 F0 전에 잡는다. 두 번째 --once 는 여기서 멈춘다(동시 굽기 막기).
    과정이 강제로 죽으면 잠금이 남는다 — 다른 굽기가 돌지 않음을 확인하고 지운 뒤 SSDIX_RERUN=사유 로."""
    lk = os.path.join(P["dir"], LOCK_NAME)
    try:
        fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("🚨 굽기 잠금이 있다(%s) — 다른 굽기가 돌고 있다. 돌고 있지 않으면 확인 뒤 지우고 SSDIX_RERUN=사유 로." % lk)
    try:
        os.write(fd, ("%d %s %s\n" % (os.getpid(), commit, time.strftime("%Y-%m-%d %H:%M:%S"))).encode("utf-8"))
    finally:
        os.close(fd)
    return lk


def _release_lock(lk):
    try:
        os.remove(lk)
    except OSError:
        pass


def _mark_finished(P, sha):
    line = "%s %s %s\n" % (FINISHED, sha, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):
        with io.open(m, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)


# ══════════════════════════════════════════════════════════════════════════
#  뿌리 셋(얼린 EGSTEP preflight) · 자식 과정 · F0
# ══════════════════════════════════════════════════════════════════════════
def _child_env():
    env = dict(os.environ)
    for k in CHILD_ENV_DROP + SMOKE_ENV_KEYS:
        env.pop(k, None)
    env.update(ENV_PINS)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "MKL_NUM_THREADS": "1", "DSTK_VD1": _ER().VD1_DIR})
    return env


def _run(cmd, cwd, out_path, what, timeout=TIMEOUT):
    t = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=_child_env(), capture_output=True, timeout=timeout)
    sec = round(time.time() - t, 1)
    if r.returncode != 0 or not os.path.exists(out_path):
        tail = _scrub(r.stderr.decode("utf-8", "replace"))[-2500:]
        raise SystemExit("🚨 자식 과정(%s) 실패 — 산출을 쓰지 않았다:\n%s" % (what, tail))
    return sec


def run_child(tree, mode, job, work):
    """SSDIX 엔진 자식 — python -X utf8 <뿌리>/build/ssdix.py --child <mode> --job <작업> --out <산출>(작업 폴더 · 캐시)."""
    jp = os.path.join(work, "job_ssdix_%s.json" % mode)
    op = os.path.join(work, "out_ssdix_%s.json" % mode)
    _write_json(jp, job)
    sec = _run([sys.executable, "-X", "utf8", os.path.join(tree, *ENGINE.split("/")), "--child", mode, "--job", jp, "--out", op], tree, op, mode)
    return op, sec


EG_F0_KEYS = ("ok", "bad", "expect_diff", "states", "q06_same_as_recorded", "v0_identity", "grid", "down", "d_book")


def f0_signature(F0):
    """등록 커밋에 박는 F0 개수(정수 · 날짜 · 참/거짓 · 짧은 해시만 · 실수 없음) — 굽기 F0 가 같아야 표식을 쓴다."""
    eg = F0.get("egstep") or {}
    r = F0.get("f0r") or {}
    g0 = r.get("g0") or {}
    sig = {"egstep_f0_ok": bool(eg.get("ok") and not eg.get("expect_diff"))}
    sig.update({"t_" + k: v for k, v in (F0.get("targets") or {}).items()})
    sig.update({"grid_same": bool(r.get("grid_same")), "spy_same": bool(r.get("spy_same")), "v0_hash_ok": bool(r.get("v0_hash_ok")),
                "n_win_dates": r.get("n_win_dates"), "n_eg_forms": r.get("n_eg_forms"), "g0_pass": bool(g0.get("pass")), "g0_months": g0.get("n_months"),
                "g0_corr_x1000": (int(round(g0["corr_med"] * 1000)) if isinstance(g0.get("corr_med"), (int, float)) else None),
                "g0_ovx_x1000": (int(round(g0["ovx_med"] * 1000)) if isinstance(g0.get("ovx_med"), (int, float)) else None)})
    sig.update(dict(F0.get("g6") or {}))
    return sig


def preflight(work):
    """F0(핀 뿌리 셋 · 수익 없음 · 등록 F0 서명 대조) — 통과해야 표식을 쓴다. ① 얼린 EGSTEP preflight(뿌리 셋 짓기 · EGSTEP F0 서명 대조 · D 목표) ·
    ② 엔진을 뿌리 셋에 넣고 SSDIX F0 자식 셋(vroot 목표 · root G0 · French G6 목표). 목표(비중 · 개수)는 굽기가 그대로 이어 쓴다."""
    t0 = time.time()
    ER = _ER()
    pf = ER.preflight(work)                                   # 얼린 EGSTEP F0 — 실패하면 SystemExit(굽지 않는다)
    R = pf["roots"]
    for tree in (R["root"], R["vroot"], R["droot"]):
        shutil.copyfile(os.path.join(ROOT, *ENGINE.split("/")), os.path.join(tree, *ENGINE.split("/")))
    sec = {"egstep_preflight": pf["sec"]}
    p_t, sec["targets"] = run_child(R["vroot"], "targets", {"root": R["vroot"], "work": os.path.join(work, "t")}, work)
    p_r, sec["f0r"] = run_child(R["root"], "f0r", {"targets": p_t}, work)
    p_g, sec["g6"] = run_child(R["vroot"], "g6", {"mode": "f0", "french": french_paths(), "work": os.path.join(work, "g")}, work)
    T = _read_json(p_t)
    fr = _read_json(p_r)
    g6 = _read_json(p_g)
    egf = pf["f0"]
    F0 = {"egstep": {k: egf.get(k) for k in EG_F0_KEYS}, "targets": T["counts"], "targets_sec": T.get("sec"), "grid": {"first": T.get("grid_first"), "last": T.get("grid_last")},
          "window": {k: T["window"][k] for k in ("first", "last", "n_dates")}, "f0r": fr, "g6": g6["counts"], "g6_sec": g6.get("sec")}
    del T
    bad = []
    if not egf.get("ok") or egf.get("expect_diff"):
        bad.append("EGSTEP F0 가 등록 서명과 다르다")
    if not fr.get("grid_same"):
        bad.append("vroot 창 날짜가 root 창 날짜와 다르다")
    if not fr.get("v0_hash_ok"):
        bad.append("얼린 V0 목표 해시가 QFWD 짝맞춤 표와 다르다")
    import ssdix as E
    sig = f0_signature(F0)
    F0["signature"] = sig
    if E.F0_EXPECT is not None:
        diff = sorted(k for k in set(sig) | set(E.F0_EXPECT) if sig.get(k) != E.F0_EXPECT.get(k))
        F0["expect_diff"] = diff
        if diff:
            bad.append("등록 F0 개수와 다름(%s)" % ", ".join(diff[:6]))
    F0["bad"] = bad
    F0["ok"] = not bad
    sec["total"] = round(time.time() - t0, 1)
    if not F0["ok"]:
        raise SystemExit("🚨 F0 실패 — %s (굽지 않는다)" % "; ".join(bad))
    return {"f0": F0, "roots": R, "egstep": pf, "targets": p_t, "sec": sec}


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def frozen_check(env=None):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("SSDIX_COMMIT")
    if not c:
        raise SystemExit("🚨 SSDIX_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --pins · --f0 · --manifest · --precommit · --smoke 만 된다.")
    nb = name_check()
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_SSDIX_NO_FETCH"):
        fr = _git("fetch", "--quiet", "origin")
        if fr.returncode != 0:
            raise SystemExit("🚨 git fetch origin 실패 — origin/main 을 새로 보지 못하면 굽지 않는다.")
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
    txt = _git_bytes("show", "%s:%s" % (full, PREREG)).stdout.decode("utf-8", "replace")
    n_ph, n_dm = placeholder_counts(txt)
    if n_ph or n_dm or not txt:
        raise SystemExit("🚨 등록 커밋의 사전등록 문서에 빈칸 %d · 초안 괄호 %d 가 남았다(또는 문서 없음)." % (n_ph, n_dm))
    if _git("cat-file", "-e", "%s:%s" % (full, FORWARD_DIR)).returncode == 0:
        raise SystemExit("🚨 등록 커밋에 전방 원장(%s)이 있다." % FORWARD_DIR)
    fw = check_no_forward()
    if fw:
        raise SystemExit("🚨 %s" % "; ".join(fw))
    P = paths()
    if _inside(P["dir"], ROOT):
        raise SystemExit("🚨 산출 폴더가 저장소 안이다: %s" % P["dir"])
    outs = _existing_outputs(P)
    if outs:
        raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다." % ", ".join(os.path.basename(o) for o in outs))
    if _git("cat-file", "-e", "origin/main:" + RESULT).returncode == 0:
        raise SystemExit("🚨 origin/main 에 결과 문서가 이미 있다 — 다시 굽기는 새 등록.")
    rerun = env.get("SSDIX_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag() if (real or not env.get("_SSDIX_NO_FETCH")) else env.get("_SSDIX_REMOTE_TAG")
    start_guard(full, rerun, marks, remote)
    for p in FROZEN + (".gitignore", "build/validate_site.py") + tuple(REUSED_BLOBS):
        fp = os.path.join(ROOT, *p.split("/"))
        want = _git_bytes("show", "%s:%s" % (full, p))
        if want.returncode != 0:
            raise SystemExit("🚨 %s 가 등록 커밋에 없다." % p)
        if not os.path.exists(fp) or _sha_lf(_bytes(fp)) != _sha_lf(want.stdout):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    gw, vw = wired_state()
    if not (gw and vw):
        raise SystemExit("🚨 덧붙임 두 곳이 붙지 않았다(.gitignore %s · validate_site %s) — `ssdix_run.py --wire --apply` 를 등록 커밋에." % (gw, vw))
    pb = pins_check()
    if pb:
        raise SystemExit("🚨 핀 · 재사용 blob: %s" % "; ".join(pb[:4]))
    mb = manifest_check()
    if mb:
        raise SystemExit("🚨 명세: %s" % "; ".join(mb[:4]))
    xb = ext_problems()
    if xb:
        raise SystemExit("🚨 저장소 밖 입력: %s" % "; ".join(xb[:4]))
    v = _versions()
    vbad = ["%s %s(등록 %s)" % (k, v.get(k), want) for k, want in VERSIONS.items() if v.get(k) != want]
    if vbad:
        raise SystemExit("🚨 라이브러리 판이 다르다: %s" % ", ".join(vbad))
    eb = ["%s=%s" % (k, env.get(k)) for k, want in ENV_PINS.items() if env.get(k) != want]
    if eb:
        raise SystemExit("🚨 PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 로 돌려라(지금 %s)." % ", ".join(eb))
    cb = registered_constants_ok()
    if cb:
        raise SystemExit("🚨 등록 상수가 다르다: %s" % "; ".join(cb[:6]))
    g = site_guard_std()
    if not g["ok"]:
        raise SystemExit("🚨 사이트 경계 실패: %s" % "; ".join(g["bad"][:5]))
    return full


# ══════════════════════════════════════════════════════════════════════════
#  굽기(🚨 수익 — 등록 커밋 뒤 한 번 굽기와 눈가린 연기에서만 · 값은 찍지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def bake(commit, rerun=None, smoke=False):
    t0 = time.time()
    P = paths()
    if smoke and not os.path.basename(os.path.dirname(os.path.abspath(P["dir"]))).startswith("ssdix_runner_smoke_"):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/ssdix_runner_smoke_*/out 이 아니다.")
    if not smoke and _OVR["out"]:
        raise SystemExit("🚨 진짜 굽기에 연기 경로가 켜져 있다.")
    lk = _take_lock(P, commit)                                # 배타 잠금 — 동시 --once 는 여기서 멈춘다
    try:
        outs = _existing_outputs(P)
        if outs:
            raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다." % ", ".join(os.path.basename(o) for o in outs))
        start_guard(commit, rerun, [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)], _tag_now())
        n_stale = 0 if smoke else purge_stale()               # 진짜 굽기: 앞선 과정이 죽어 남은 작업 폴더를 열지 않고 지운다(개수만 싣는다)
        return _bake_locked(P, commit, rerun, smoke, t0, n_stale)
    finally:
        _release_lock(lk)


def _main_children(pf, work):
    """굽기 자식 — EGSTEP 가치 다리(droot) → D 책(vroot · 얼린 x_adapter) → SSDIX 책(vroot) → G6(French) → S(root) → 판정(vroot)."""
    R = pf["roots"]
    ER = _ER()
    sec = {}
    p_v, sec["vleg"] = ER.run_egstep_child(R["droot"], "vleg", {}, work)
    head = _read_json(p_v)
    if head.get("stopped"):
        return {"kind": "ssdix_out", "stopped": "EGSTEP 가치 다리: %s" % head["stopped"]}, None, sec
    del head
    p_db, sec["d_book"] = ER.run_xa_child(R["vroot"], "--dbook-child", {"out": os.path.join(work, "d_book.json"), "d_targets": pf["egstep"]["d_targets"],
                                                                        "root": R["vroot"]}, work, "dbook")
    p_b, sec["books"] = run_child(R["vroot"], "books", {"targets": pf["targets"], "root": R["vroot"]}, work)
    p_g, sec["g6"] = run_child(R["vroot"], "g6", {"mode": "bake", "french": french_paths(), "work": os.path.join(work, "g6b")}, work)
    p_s, sec["s"] = run_child(R["root"], "s", {"books": p_b, "targets": pf["targets"], "v_book": p_v, "d_book": p_db, "d_targets": pf["egstep"]["d_targets"],
                                                "qbatch": os.path.join(R["droot"], "data", "_qbatch.json"), "egstep_out": EGSTEP_OUT}, work)
    f0p = os.path.join(work, "f0_record.json")
    _write_json(f0p, pf["f0"])
    p_j, sec["judge"] = run_child(R["vroot"], "judge", {"s_out": p_s, "books_out": p_b, "g6_out": p_g, "f0": f0p}, work)
    main = _read_json(p_j)
    S = _read_json(p_s)
    B = _read_json(p_b)
    G6 = _read_json(p_g)
    series = {"s": S.get("series"), "books_v": B.get("series_v"), "g6_cache": G6.get("cache_only"), "pre_cache": (B.get("pre") or {}).get("cache_only")}
    del S, B, G6
    return main, series, sec


def _bake_locked(P, commit, rerun, smoke, t0, n_stale=0):
    work = tempfile.mkdtemp(prefix="ssdix_work_", dir=os.path.dirname(P["dir"]) if smoke else cache_guard_std())
    try:
        pf = preflight(work)                                  # 표식 전 — 실패하면 한 번 굽기를 쓰지 않는다
        started = (_read_text(P["mark"] if os.path.exists(P["mark"]) else P["gitmark"]).strip() if rerun
                   else "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S")))
        for m in (P["mark"], P["gitmark"]):
            if not os.path.exists(m):
                _write_text(m, started + "\n")
        tag = _push_start_tag(commit, rerun)
        err = []
        try:
            main, series, sec_m = _main_children(pf, work)
        except SystemExit as e:
            raise SystemExit("🚨 굽기 계산 실패 — 산출을 쓰지 않았다(산출 전 기술적 중단이면 SSDIX_RERUN=사유 로 처음부터 · 같은 얼린 코드로만):\n%s" % str(e)[-2000:])
        ER = _ER()
        out = {CACHE_ONLY_KEY: True, "kind": "ssdix_bake", "prereg": PREREG, "prereg_commit": commit, "smoke": smoke,
               "pins": {"root": ER.ROOT_PIN, "vroot": ER.VROOT_PIN, "droot": ER.DROOT_PIN}, "f0": pf["f0"], "main": main, "series": series}
        blob = (json.dumps(out, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        sha = hashlib.sha256(blob).hexdigest()
        rec = {"commit": commit, "registration_error": err, "smoke": smoke, "stale_deleted": int(n_stale)}
        pub = public_doc(out, sha, len(blob), rec)               # 공개 안전에 걸리면 여기서 멈춘다 — 산출을 쓰기 전
        pub_txt = json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n"
        with open(P["out"] + ".part", "wb") as f:
            f.write(blob)
        os.replace(P["out"] + ".part", P["out"])
        _write_text(P["public"], pub_txt)
        del out, main, series
        runlog = {"prereg": PREREG, "prereg_commit": commit, "runner": RUNNER, "engine": ENGINE, "started": started, "rerun": rerun, "start_tag": tag,
                  "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "sec": round(time.time() - t0, 1),
                  "clock": {"preflight": pf["sec"], "main": sec_m}, "out": os.path.basename(P["out"]), "out_sha256": sha,
                  "public": os.path.basename(P["public"]), "public_sha256": _sha_file(P["public"]),
                  "env": {k: os.environ.get(k) for k in ENV_PINS}, "versions": _versions(), "frozen": list(FROZEN), "reused": dict(REUSED_BLOBS),
                  "code_sha": code_shas(), "registration_error": err, "smoke": smoke, "stale_deleted": int(n_stale),
                  "note": "값 없음 — 결과는 _ssdixout.public.json 의 칸만 결과 문서로 옮긴다(등록 §9 공개 규칙)"}
        _write_text(P["runlog"], json.dumps(runlog, ensure_ascii=False, indent=1) + "\n")
        _mark_finished(P, sha)
        if not smoke:
            print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)" % (P["out"], sha[:16], runlog["sec"]))
        return runlog
    finally:
        shutil.rmtree(work, ignore_errors=True)


def once():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("SSDIX_RERUN"))


# ══════════════════════════════════════════════════════════════════════════
#  게시 칸(10년 창 값 · 20년 층과 앞 창은 참/거짓 · 개수만)
# ══════════════════════════════════════════════════════════════════════════
PUB_METRIC_KEYS = ("n", "ann_ex", "te", "ir", "t_iid", "nw_t", "win", "years", "years_won", "n_years", "down_n", "down_mean", "down_win", "up_mean",
                   "down_capture", "up_capture", "sleeve_beta", "episodes", "crash_won", "surge_won", "mech", "roll12", "halves", "blocks")
F0_PUB_KEYS = ("ok", "bad", "expect_diff", "egstep", "targets", "grid", "window", "f0r", "g6")


def _pick(d, keys):
    return {k: d.get(k) for k in keys if k in (d or {})}


def strip_cache_only(o):
    """«cache_only» 칸(20년 층 · 앞 창의 실수)을 게시 칸에서 뺀다 — 캐시 산출에만 남는다."""
    if isinstance(o, dict):
        return {k: strip_cache_only(v) for k, v in o.items() if k != "cache_only"}
    if isinstance(o, list):
        return [strip_cache_only(v) for v in o]
    return o


def public_doc(out, sha=None, nbytes=None, rec=None):
    """게시 칸 — 결과 문서가 옮길 수 있는 칸만(10년 창 값 · F0 개수 · 날짜 · 참/거짓 · 20년 층 · 앞 창은 참/거짓 · 개수 · 2016-09 ~ 반쪽).
    public_safe_std 를 통과해야 쓴다(계열 · 몫 배열 · cache_only 칸은 싣지 않는다)."""
    rec = rec or {}
    f0, M = out.get("f0") or {}, out.get("main") or {}
    pv = {"ssdix_public_view": True, "prereg": out.get("prereg"), "prereg_commit": rec.get("commit"), "out_sha256": sha, "out_bytes": nbytes,
          "smoke": bool(rec.get("smoke")), "registration_error": list(rec.get("registration_error") or []),
          "stale_deleted": int(rec.get("stale_deleted") or 0), "stopped": M.get("stopped"), "pins": out.get("pins"), "f0": _pick(f0, F0_PUB_KEYS),
          "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼» (전방 원장 · 날짜가 박힌 미래 판정 없음)"}
    if not M.get("stopped"):
        arms = {}
        for k, v in (M.get("arms") or {}).items():
            arms[k] = {"m": _pick(v.get("m") or {}, PUB_METRIC_KEYS), "m20": v.get("m20"), "down_frozen": v.get("down_frozen"),
                       "turn": v.get("turn"), "cost_drag": v.get("cost_drag")}
        pv.update({"window": M.get("window"), "n_hold": M.get("n_hold"), "arms": arms, "primary": M.get("primary"), "family": M.get("family"),
                   "gates": M.get("gates"), "gates_in": M.get("gates_in"), "adopt": M.get("adopt"), "verdict": M.get("verdict"), "detail": M.get("detail"),
                   "controls": M.get("controls"), "years_delta": M.get("years_delta"), "pairing": M.get("pairing"), "books_pairing": M.get("books_pairing"),
                   "down": M.get("down"), "g5": M.get("g5"), "g0": M.get("g0"), "g6": M.get("g6"), "pre": M.get("pre"), "dsr": M.get("dsr"),
                   "readings": M.get("readings"), "predictions": M.get("predictions"), "multiplicity": M.get("multiplicity")})
    pv = strip_cache_only(pv)
    bad = public_safe_std(pv)
    if bad:
        raise SystemExit("🚨 게시 칸이 공개 안전 점검에 걸렸다: %s" % bad[:3])
    return pv


def public_view_writer(out_path=None):
    P = paths()
    op = out_path or P["out"]
    if not (os.path.exists(P["mark"]) and FINISHED in _read_text(P["mark"])):
        raise SystemExit("🚨 FINISHED 표식이 없다 — 게시 칸은 끝난 굽기에서만 다시 쓴다.")
    blob = _bytes(op)
    out = json.loads(blob.decode("utf-8"))
    rl = _read_json(P["runlog"]) if os.path.exists(P["runlog"]) else {}
    pub = public_doc(out, hashlib.sha256(blob).hexdigest(), len(blob),
                     {"commit": out.get("prereg_commit"), "registration_error": rl.get("registration_error"), "smoke": out.get("smoke"),
                      "stale_deleted": rl.get("stale_deleted")})
    _write_text(P["public"], json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    return {"public": P["public"], "sha256_16": _sha_file(P["public"])[:16]}


# ══════════════════════════════════════════════════════════════════════════
#  결과 문서 렌더러(얼린 · 게시 칸 파일 하나만 읽는다)
# ══════════════════════════════════════════════════════════════════════════
ARM_KO = {"SSD": "SSD 책(척도 SSD · 200일 · 상한 20%)", "DIL_SSD": "희석 쌍둥이(SSD 의 사전 β̂ · SPY + T-bill 항등식)", "C2": "C2 V02 D 책 홀로",
          "C3": "C3 평균 맞춘 최소 MAD", "C4": "C4 비척도 SSD", "C5": "C5 평균 제약 5% CVaR", "C7A": "C7a 동일가중 우주", "C7B": "C7b 시총가중 우주",
          "C10": "C10 섹터 ±5% SSD", "RD": "RD(얼린 EGSTEP · D 자리 = V02 D 책)", "RDSSD": "RD-SSD(D 자리 = SSD 책)",
          "RDTWIN": "RD-TWIN(D 자리 = SSD 의 β̂ 쌍둥이)", "C0": "C0 EG30 V0(참고)"}
ARM_ORDER = ("SSD", "DIL_SSD", "C2", "C3", "C4", "C5", "C7A", "C7B", "C10", "RD", "RDSSD", "RDTWIN", "C0")
CTRL_ORDER = ("SSD", "C2", "C3", "C4", "C5", "C7A", "C7B", "C10")
GATE_KO = {"G0": "G0 EG30 독립(G-EGD 수 둘 · 수익 전)", "G1": "G1 반등 청구(Σ급등월 X ≥ −½·Σ급락월 X ∧ Σ급락월 X > 0)",
           "G2": "G2 연 X 80% 한쪽 하한 > −0.15%p", "G3": "G3 20bp 에서 Δ_A > 0", "G4": "G4 30개월 토막 넷 가운데 Δ_A > 0 이 셋 이상",
           "G5": "G5 무작위 포트 위약 백분위 ≥ 95", "G6": "G6 French 49 산업 20년 기전 층 Δ > 0 ∧ t ≥ 1",
           "h1": "h1 20bp 전 월 Δ_B ≥ 0", "h2": "h2 반등 다리 이긴 수 ≥ RD − 1", "h3": "h3 슬리브 편도 연 회전 ≤ 10",
           "d1": "d1 하락월 Δ_B > RD-TWIN 의 하락월 Δ(β̂ 몫 너머)", "d2": "d2 20bp 전 월 Δ_B ≥ RD-TWIN 의 것"}
PRED_KO = {"P1_no_rejection": "P1 (A) 기각 없음(Holm 0/1)", "P2_no_adoption": "P2 채택 표시 0", "P3_beta_below1": "P3 SSD 책 사전 β̂ 중앙값 < 1",
           "P4_down_x_pos": "P4 SSD 슬리브 펀드의 얼린 하락월 X 평균 > 0(지수보다 덜 잃는다)", "P5_delta_a_pos": "P5 Δ_A 점 추정 > 0(β̂ 몫 너머의 방어)",
           "P6_up_x_neg": "P6 SSD 의 하락월 밖 X 평균 < 0(강세 · 반등에서 뒤진다)", "P7_rebound_claim_fails": "P7 G1 반등 청구 거짓",
           "P8_delta_b_pos": "P8 Δ_B 점 추정 > 0(방어 스텝 목적지로 V02 D 책보다 낫다)", "P9_g6_delta_pos": "P9 G6 French 층 Δ > 0"}
READ_KO = {"bull_lag": "강세 뒤짐(하락월 밖 X < 0)", "variance_like": "분산 대리(C3 의 Δ ≥ SSD 의 Δ)", "sector_bet": "섹터 베팅 몫(C10 의 Δ < SSD 의 ½)",
           "size_like": "크기 몫(C7a 의 Δ ≥ SSD 의 Δ)", "pre_window_weak": "앞 창 Δ ≤ 0", "half10_g6_weak": "French 층 2016-09 ~ 반쪽 Δ ≤ 0",
           "beta_only": "β̂ 몫뿐(d1 거짓)", "surge_cost": "급등월 Δ_B < 0", "few_months": "D 켜진 하락월 < 10"}
DATA_NOTE = ("SSD 책은 EG30 을 입력으로 쓰지 않는다(우주 · 가격 · SPY 분포만) — EG30 은 G0 의 비교 책과 (B) 의 얼린 RD 코어로만 든다. "
             "우주 = PIT S&P 500 ∪ NASDAQ 100(얼린 v_pit.Universe · 배치 V 핀 판) · 편출 이름의 일부 계열은 가격수익(배당 없음) 판이라 그 이름의 시나리오 수익이 조금 낮다(랩 자료 한계 · 공개).")


def _fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%%.%df" % nd) % v
    return str(v)


def _mech(m, key):
    x = ((m or {}).get("mech") or {}).get(key) or {}
    return "%s/%s" % (x.get("win"), x.get("n"))


def reg_err_lines(path):
    """굽기 뒤에 찾은 등록 오류(글과 얼린 코드의 어긋남)를 손으로 적은 UTF-8 글 파일 → (줄 목록, sha256 앞 16).
    줄마다 소수 · 지수꼴은 <num> 으로 지운다(값이 머리로 새지 않게 · 정수 · 날짜 · 절 번호는 남는다) · 빈 줄 · # 줄은 건너뛴다."""
    b = _bytes(path)
    out = [_scrub(l.strip())[:300] for l in b.decode("utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
    return out, hashlib.sha256(b).hexdigest()[:16]


def result_doc(pub, reg_err=None):
    """결과 문서 본문(Markdown) — 게시 칸 파일(_ssdixout.public.json) 하나만 읽는다(손으로 옮기지 않는다)."""
    if not pub or not pub.get("ssdix_public_view"):
        raise SystemExit("🚨 게시 칸 파일이 아니다")
    stopped = pub.get("stopped")
    fam = pub.get("family") or {}
    rej = fam.get("reject") or {}
    adopt = pub.get("adopt") or {}
    n_rej, n_ad = sum(1 for v in rej.values() if v), sum(1 for v in adopt.values() if v)
    verdict = pub.get("verdict") or ("보류" if stopped else "—")
    title = ("# 결과 — 확률지배(SSD) 지수 강화 책 역할 검정(SSDIX · 척도 SSD · 200일 · 월 교체 · 상한 20%% · (A) 독립 엔진 · (B) 방어 스텝 목적지): 한 번 굽기 · %s · **%s**"
             % ("멈춤(등록된 멈춤 조건)" if stopped else "Holm 기각 %d/1 · 채택 표시 %d" % (n_rej, n_ad), verdict))
    re_lines, re_sha = (reg_err or ([], None))
    reg_all = list(pub.get("registration_error") or []) + list(re_lines)
    mult = pub.get("multiplicity") or {}
    pins = pub.get("pins") or {}
    L = [title, "",
         "풀카드: 없음   <!-- 랩이 한 번도 쓰지 않은 수학(확률지배)이라 탐색 풀 카드가 없다 · build/pool_lab.py 가 이 줄을 읽는다 -->",
         "판정: %s   <!-- 확증 가족 = (A) 하나(얼린 하락월 35 의 Δ · 한쪽 α 0.05 · Holm m 1) · (B) 는 등록 읽기(판정 밖) · 채택 표시 = 기각 ∧ 그 팔의 관문 모두 · 표시가 있으면 «보류»(펀드에 붙이기는 사용자 결정) · 기각은 있고 표시가 없으면 «측정만» · 기각 0 이면 «기각» -->" % verdict,
         "규칙: 없음   <!-- 랩 게시 sid 가 아니다 · 운용 · 사이트 규칙 변경 없음 -->", "",
         "아래는 얼린 렌더러(`python -X utf8 build/ssdix_run.py --result-doc`)가 게시 칸 파일(`_ssdixout.public.json`) 하나에서 만든 것이다.", "",
         "## 머리", "",
         "- 등록 커밋 `%s` · 산출 sha256 `%s` · 뿌리 핀 root `%s` · vroot `%s` · droot `%s`" % (
             pub.get("prereg_commit"), (pub.get("out_sha256") or "—")[:16], ((pins.get("root") or {}).get("code_pin") or "")[:9],
             (pins.get("vroot") or "")[:9], (pins.get("droot") or "")[:9]),
         "- 멈춤: %s · 등록 오류: %s%s" % (stopped or "없음", "; ".join(reg_all) or "없음",
                                       (" (굽기 뒤 손으로 적은 등록 오류 파일 sha256 `%s` · 값이 아니라 글과 얼린 코드의 어긋남)" % re_sha) if re_sha else ""),
         "- 앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 남은 작업 폴더: %s (굽기 시작 때 열지 않고 지웠다 · 등록 §10-2)" % int(pub.get("stale_deleted") or 0),
         "- 창(보유월): %s · %s개월 · 펀드 F = 0.9 × SPY TR + 0.1 × 슬리브 대 SPY TR · 편도 10bp(20bp 판) · 월말 결정 · T+1 체결" % (
             "~".join(pub.get("window") or ["—"]), pub.get("n_hold") or "—"),
         "- 다중성: 확증 가족 m = %s((A) 하나 · α %s · 한쪽 · 얼린 하락월 35 의 Δ · (B) 는 등록 읽기) · 누적 N %s → %s(센 줄 %s · 기저 = Q06HOLD 결과 문서의 누적 N 1,063 · 등록 §9)" % (
             mult.get("m_confirmatory"), mult.get("alpha"), mult.get("cum_n_before"), mult.get("cum_n_after"), mult.get("rows_counted")),
         "- 전방: %s" % pub.get("forward"), ""]
    f0 = pub.get("f0") or {}
    tg = f0.get("targets") or {}
    fr = f0.get("f0r") or {}
    g0 = fr.get("g0") or {}
    g6c = f0.get("g6") or {}
    eg = f0.get("egstep") or {}
    L += ["## F0 관문(수익 없음 · 등록 개수 대조)", "",
          "| 관문 | 값 |", "|---|---|",
          "| F0 전체 · 어긋남 | %s · %s |" % (_fmt(f0.get("ok")), "; ".join(f0.get("bad") or []) or "없음"),
          "| 얼린 EGSTEP F0(뿌리 셋 · 상태 · V0 · D 목표 — EGSTEP 등록 서명) | %s · 어긋남 %s |" % (_fmt(eg.get("ok")), ", ".join(eg.get("expect_diff") or []) or "없음"),
          "| 우주(결정 2016-08 ~ 2026-07): 명단 이름 최소 · 최대 · 자격(201 가격) 최소 · 중앙 · 최대 | %s · %s · %s · %s · %s |" % (
              tg.get("members_min"), tg.get("members_max"), tg.get("elig_min"), tg.get("elig_med"), tg.get("elig_max")),
          "| 시나리오 커버리지(자격 ÷ 명단) 최소 · 중앙(‰) · S&P 500 시총 몫 최소(‰) · 0.90 미만 달 | %s · %s · %s · %s |" % (
              tg.get("cov_min_x1000"), tg.get("cov_med_x1000"), tg.get("covw_min_x1000"), tg.get("months_cov_lt90")),
          "| LP(SSD 주 사슬): 1단계 최적 · 2단계 최적 · 이은 달 · 동률 해소가 옮긴 ℓ1 중앙 · 최대(‰) · 5%% 넘게 옮긴 달 · 이름 수 최소 · 최대 · 체결 날 뺀 이름 | %s · %s · %s · %s · %s · %s · %s · %s · %s |" % (
              tg.get("SSD_ok1"), tg.get("SSD_ok2"), tg.get("SSD_carried"), tg.get("SSD_tie_med_x1000"), tg.get("SSD_tie_max_x1000"), tg.get("SSD_ties_gt5pct"),
              tg.get("SSD_names_min"), tg.get("SSD_names_max"), tg.get("SSD_drops")),
          "| LP 대조(C10 · C4 · C3 · C5 · 앞 창): 1단계 최적 | %s · %s · %s · %s · %s |" % (
              tg.get("C10_ok1"), tg.get("C4_ok1"), tg.get("C3_ok1"), tg.get("C5_ok1"), tg.get("PRE_ok1")),
          "| 목표 해시(SSD · 앞 창 · C10) | `%s` · `%s` · `%s` |" % (tg.get("SSD_hash16"), tg.get("PRE_hash16"), tg.get("C10_hash16")),
          "| 위약 뽑기(1,000 × 121 · β̂ 띠 ±0.01): 대체 수 · 해시 | %s · `%s` |" % (tg.get("placebo_fallback"), tg.get("placebo_hash16")),
          "| 창 날짜 vroot = root · SPY 일간 수익 같음 · 얼린 V0 목표 해시 | %s · %s · %s |" % (_fmt(fr.get("grid_same")), _fmt(fr.get("spy_same")), _fmt(fr.get("v0_hash_ok"))),
          "| G0(수익 전 · 비중만): 달 · 능동비중 상관 중앙 · 겹침 초과 중앙 · 통과 | %s · %s · %s · %s |" % (
              g0.get("n_months"), _fmt(g0.get("corr_med"), 3), _fmt(g0.get("ovx_med"), 3), _fmt(g0.get("pass"))),
          "| G6 French(202608 CRSP · sha256 핀): 판 확인 · 결정 · 자격 산업 최소 · 최대 · 1단계 최적 · 해시 | %s · %s · %s · %s · %s · `%s` |" % (
              _fmt(g6c.get("g6_vintage_ok")), g6c.get("g6_forms"), g6c.get("g6_elig_min"), g6c.get("g6_elig_max"), g6c.get("g6_ok1"), g6c.get("g6_hash16")), ""]
    if stopped:
        L += ["## 멈춤", "", "- 굽기가 멈췄다(%s) — 산출은 멈춤 기록이다. 다시 굽기는 새 등록." % stopped, ""]
        return "\n".join(L) + "\n"
    prim = pub.get("primary") or {}
    thr = fam.get("threshold") or {}
    gates = pub.get("gates") or {}
    arms = pub.get("arms") or {}
    rB = fam.get("reading_B") or {}
    nB = (((pub.get("detail") or {}).get("B") or {}).get("d_on_down") or {}).get("n")
    L += ["## 1. 확증 가족((A) 하나) · 관문 · 채택 표시 · (B) 등록 읽기(한쪽 · H1 Δ > 0 · 얼린 하락월 35 · 달력 NW(3) t · t(34))", "",
          "| 팔 | 통계 | Δ(%p/월) | 달력 t | 한쪽 p | Holm 문턱 | 기각 | 관문 모두 | **채택 표시** |", "|---|---|---|---|---|---|---|---|---|",
          "| (A) SSD 독립 엔진 · 확증 | 하락월 평균(X_SSD − X_희석쌍둥이) | %s | %s | %s | %s | %s | %s | **%s** |" % (
              _fmt((prim.get("A") or {}).get("mean"), 4), _fmt((prim.get("A") or {}).get("t")), _fmt((fam.get("p") or {}).get("A"), 4), _fmt(thr.get("A"), 4),
              _fmt(rej.get("A")), _fmt((gates.get("A") or {}).get("ok")), _fmt(adopt.get("A"))),
          "| (B) 방어 스텝 목적지 · 읽기 | 하락월 평균(X_RD-SSD − X_RD) | %s | %s | %s | 판정 밖 | 명목 %s | %s | 판정 밖 |" % (
              _fmt((prim.get("B") or {}).get("mean"), 4), _fmt((prim.get("B") or {}).get("t")), _fmt(rB.get("p"), 4),
              _fmt(rB.get("nominal_reject")), _fmt((gates.get("B") or {}).get("ok"))), "",
          "- (B) 는 등록 읽기다 — 판정을 바꾸지 못한다: RD 와 D 자리의 책이 달라지는 하락월이 %s 개뿐이라 참 효과가 있어도 검정력이 약 0.05 다(등록 §6-1). "
          "«명목» 은 α 0.05 를 홀로 쓴 참/거짓일 뿐 기각이 아니다." % (nB if nB is not None else "—"),
          "- 채택 표시는 «펀드 후보» 라는 뜻뿐이다 — 펀드에 붙이는 것은 사용자 결정이고 날짜가 박힌 일정은 없다(등록 §6).",
          "- %s" % DATA_NOTE, "",
          "### 1-2. 관문(계산 전 고정)", "", "| 관문 | 참/거짓 |", "|---|---|"]
    for a in ("A", "B"):
        for k, v in sorted(((gates.get(a) or {}).get("conds") or {}).items()):
            L.append("| (%s) %s | %s |" % (a if a == "A" else "B 읽기", GATE_KO.get(k, k), _fmt(v)))
    dA = (pub.get("detail") or {}).get("A") or {}
    dB = (pub.get("detail") or {}).get("B") or {}
    g5 = pub.get("g5") or {}
    g6 = pub.get("g6") or {}
    rb = dA.get("rebound") or {}
    L += ["", "- G1 급락월 X 합 %s · 급등월 X 합 %s · G2 80%% 하한 %s%%p/년 · G3 20bp 하락월 Δ %s · G4 토막 Δ %s · G5 백분위 %s(참 %s · 뽑기 p05 %s · p50 %s · p95 %s · 대체 %s) · "
          "G6 20년 판정 %s(하락월 %s · 2016-09 ~ 반쪽 Δ %s · t %s)" % (
              _fmt(rb.get("crash_sum"), 3), _fmt(rb.get("surge_sum"), 3), _fmt(dA.get("lb80"), 3), _fmt(dA.get("delta20_down"), 4),
              " · ".join(_fmt(x, 4) for x in (dA.get("blocks") or [])), _fmt(g5.get("pct"), 1), _fmt(g5.get("true"), 4),
              _fmt((g5.get("q") or {}).get("p05"), 4), _fmt((g5.get("q") or {}).get("p50"), 4), _fmt((g5.get("q") or {}).get("p95"), 4), g5.get("n_fallback"),
              _fmt(g6.get("pass")), g6.get("n_down"), _fmt((g6.get("half10") or {}).get("mean"), 4), _fmt((g6.get("half10") or {}).get("t"))),
          "- (B) 전 월 Δ %s%%p/년 · 20bp %s · RD-TWIN 하락월 Δ %s · 20bp %s · 반등 다리 RD-SSD/RD %s/%s · 회전 %s · D 켜진 하락월 %s달(Δ %s) · 급락월 Δ %s · 급등월 Δ %s" % (
              _fmt(dB.get("all_ann"), 3), _fmt(dB.get("all20_ann"), 3), _fmt(dB.get("twin_down"), 4), _fmt(dB.get("twin_all20_ann"), 3),
              (dB.get("rebounds") or {}).get("RDSSD"), (dB.get("rebounds") or {}).get("RD"), _fmt(dB.get("turn")),
              (dB.get("d_on_down") or {}).get("n"), _fmt((dB.get("d_on_down") or {}).get("mean"), 4), _fmt(dB.get("crash_m"), 3), _fmt(dB.get("surge_m"), 3)), ""]
    L += ["## 2. 펀드 틀 — 팔마다 대 SPY TR(10년 · 편도 10bp)", "",
          "| 팔 | 연 초과(%p) | TE | IR | NW t | 월 승률(%) | 해마다 승 | 하락월(PR) 평균 | 하락월(얼린 35) 평균 | 급락 다리 | 반등 다리 | 이름 붙은 급락 · 급등 승 | 슬리브 β | 편도 회전/년 | 20bp 연 초과 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in ARM_ORDER:
        v = arms.get(a) or {}
        m = v.get("m") or {}
        if not m:
            continue
        L.append("| %s | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s | %s · %s | %s | %s | %s |" % (
            ARM_KO.get(a, a), _fmt(m.get("ann_ex")), _fmt(m.get("te")), _fmt(m.get("ir")), _fmt(m.get("nw_t")), _fmt(m.get("win"), 1), m.get("years_won"),
            m.get("n_years"), _fmt(m.get("down_mean"), 3), _fmt((v.get("down_frozen") or {}).get("mean"), 3), _mech(m, "crash_legs"), _mech(m, "rebounds"),
            m.get("crash_won"), m.get("surge_won"), _fmt(m.get("sleeve_beta")), _fmt(v.get("turn")), _fmt((v.get("m20") or {}).get("ann_ex"))))
    ctl = pub.get("controls") or {}
    L += ["", "## 3. 대조(측정만 · 채택에 쓰지 않는다) — 슬리브 전부 · 팔마다 제 사전 β̂ 쌍둥이 대비", "",
          "| 줄 | 하락월 Δ(대 제 쌍둥이) | 달력 t | 연 X | 하락월 X | 하락월 밖 X | 20bp 연 X | 하락월 X − SSD 하락월 X |", "|---|---|---|---|---|---|---|---|"]
    for c in CTRL_ORDER:
        x = ctl.get(c) or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (ARM_KO.get(c, c), _fmt(x.get("delta_down"), 4), _fmt(x.get("t")), _fmt(x.get("x_ann"), 3),
                                                          _fmt(x.get("x_down"), 4), _fmt(x.get("x_up"), 4), _fmt(x.get("x20_ann"), 3), _fmt(x.get("vs_ssd_down"), 4)))
    L += ["", "- 만들지 않은 대조(계산 전 결정 · 등록 §7): C6 MSD(혼합 정수 · 무겁다) · 재성형 기준(원문 규칙의 매개변수를 확인하지 못했다) · C9 강건 SSD(와서스타인 반지름이 자유 모수) · "
          "C10 부분집합 SSD(원문 식을 확인하지 못했다). C8(목적지 교체 미리 보기)은 확증 팔 (B) 가 됐다.", ""]
    pre = pub.get("pre") or {}
    L += ["## 4. 앞 창 · 기전 층(20년 규칙 · 공개 규칙: 참/거짓 · 개수만)", "",
          "- 앞 창(보유 %s · %s달 · 하락월 %s · vroot 틀): Δ > 0 %s · SSD 하락월 X > 0 %s — 값은 캐시에만(10년 공개 창 밖)" % (
              "~".join(pre.get("window") or ["—"]), pre.get("n"), pre.get("n_down"), _fmt(pre.get("delta_pos")), _fmt(pre.get("x_down_pos"))),
          "- G6 French 49 산업(보유 %s · %s달 · 하락월 %s): Δ > 0 %s · t ≥ 1 %s · 판정 %s — 20년 값은 캐시에만 · 2016-09 ~ 반쪽(%s달 · 하락월 %s) Δ %s · t %s" % (
              "~".join(g6.get("window") or ["—"]), g6.get("n"), g6.get("n_down"), _fmt(g6.get("delta_pos")), _fmt(g6.get("t_ge1")), _fmt(g6.get("pass")),
              (g6.get("half10") or {}).get("n"), (g6.get("half10") or {}).get("n_down"), _fmt((g6.get("half10") or {}).get("mean"), 4), _fmt((g6.get("half10") or {}).get("t"))), ""]
    yd = pub.get("years_delta") or {}
    ys = sorted(set((yd.get("A") or {})) | set((yd.get("B") or {})))
    if ys:
        L += ["## 5. 해마다(펀드 초과 차 %p · 창 첫 해 · 끝 해는 부분)", "", "| 해 | A: SSD − 쌍둥이 | B: RD-SSD − RD |", "|---|---|---|"]
        for y in ys:
            L.append("| %s | %s | %s |" % (y, _fmt((yd.get("A") or {}).get(y)), _fmt((yd.get("B") or {}).get(y))))
        L += [""]
    c0 = (arms.get("SSD") or {}).get("m") or {}
    eps = c0.get("episodes") or []
    if eps:
        L += ["## 6. 이름 붙은 급락 · 급등 구간(qbatch_core.EPIS · 펀드 초과 %p)", "", "| 구간 | SSD | 희석 쌍둥이 | RD | RD-SSD |", "|---|---|---|---|---|"]
        for e in eps:
            def ep(a):
                hit = [x.get("ex") for x in (((arms.get(a) or {}).get("m") or {}).get("episodes") or []) if x.get("name") == e.get("name") and x.get("kind") == e.get("kind")]
                return _fmt(hit[0]) if hit else "—"
            L.append("| %s · %s | %s | %s | %s | %s |" % (e.get("kind"), e.get("name"), ep("SSD"), ep("DIL_SSD"), ep("RD"), ep("RDSSD")))
        L += [""]
    pr = pub.get("pairing") or {}
    bp = pub.get("books_pairing") or {}
    dsr = pub.get("dsr") or {}
    L += ["## 7. 짝맞춤(구현 점검 · 수익 판정 아님)", "",
          "- E0: C0 = 얼린 V0 — %s · E-RD: 이 굽기의 RD · C0 = EGSTEP 굽기 산출 — %s(RD %s · C0 %s)" % (
              _fmt((pr.get("E0") or {}).get("ok")), _fmt((pr.get("E_RD") or {}).get("ok")),
              ("%.1e" % pr["E_RD"]["rd_max_abs"]) if isinstance((pr.get("E_RD") or {}).get("rd_max_abs"), float) else "—",
              ("%.1e" % pr["E_RD"]["c0_max_abs"]) if isinstance((pr.get("E_RD") or {}).get("c0_max_abs"), float) else "—"),
          "- P1: 벡터 책 = 얼린 dstk.book_path 옮김 — %s · P2: 월 닫힌 식 = 얼린 qbatch_core.fund_from_path — %s" % (_fmt(bp.get("P1_ok")), _fmt(bp.get("P2_ok"))),
          "- DSR(보고 · 얼린 v_tests.dsr · SSD 펀드 월 X · N %s): %s" % (dsr.get("N"), _fmt(dsr.get("dsr"), 3)), ""]
    rd = pub.get("readings") or {}
    L += ["## 8. 읽기(계산 전 고정 · 표시를 바꾸지 않는다)", "", "| 팔 | 읽기 | 참/거짓 |", "|---|---|---|"]
    for a in ("A", "B"):
        for k, v in (rd.get(a) or {}).items():
            L.append("| (%s) | %s | %s |" % (a, READ_KO.get(k, k), _fmt(v)))
    for a in ("A", "B"):
        if adopt.get(a):
            fl = [READ_KO.get(k, k) for k, v in (rd.get(a) or {}).items() if v]
            L.append("")
            L.append(("- **(%s) 의 채택 표시에 읽기(%s)가 붙었다 — 이 표시를 «약점을 고쳤다» 로 읽지 않는다(등록 §6-6).**" % (a, " · ".join(fl))) if fl
                     else "- (%s) 의 채택 표시에 붙은 읽기는 없다 — 그래도 표본 안 · 오염된 측정이다(등록 §0)." % a)
    L += ["", "## 9. 미리 적은 예측(등록 §8)", "", "| 예측 | 맞음 |", "|---|---|"]
    for k, ko in PRED_KO.items():
        L.append("| %s | %s |" % (ko, _fmt((pub.get("predictions") or {}).get(k))))
    L += ["", "## 공개 규칙", "",
          "- 이 문서는 게시 칸 파일 하나에서 얼린 렌더러가 만들었다 · 10년 창 값만 싣는다 — 20년 French 층과 앞 창(2015-04 ~ 2016-08)의 값은 캐시에만(참/거짓 · 개수만 여기) · "
          "산출 원본(_ssdixout.json)은 저장소 밖 캐시에만 둔다.",
          "- 채택 표시가 있어도 펀드에 붙이는 것은 사용자 결정이다(날짜 없음 · 전방 원장 없음). 표시가 없으면 운용은 그대로다.",
          "- 표본 안 수치는 오염된 측정이다(등록 §0) — 2016 ~ 2026 은 랩이 가장 많이 본 창이고 (B) 의 RD 구조와 결과는 설계 전에 알려져 있었다."]
    txt = "\n".join(L) + "\n"
    if CACHE_ONLY_KEY in txt:
        raise SystemExit("🚨 결과 문서에 캐시 표지가 있다")
    return txt


def result_doc_write_problems(pub, P=None):
    """--result-doc --write 문지기 — 연기 판이 아니고 · 두 로컬 표식에 FINISHED <산출 sha> 가 있고 · 캐시 산출 sha 가 게시 칸의 out_sha256 과 같아야 쓴다."""
    P = P or paths()
    bad = []
    if not pub or not pub.get("ssdix_public_view"):
        return ["게시 칸 파일이 아니다"]
    if pub.get("smoke"):
        bad.append("연기 판 게시 칸이다")
    sha = pub.get("out_sha256") or ""
    marks = [m for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    if len(marks) != 2 or not all(("%s %s" % (FINISHED, sha)) in _read_text(m) for m in marks) or not sha:
        bad.append("두 로컬 표식에 FINISHED <산출 sha> 줄이 없다")
    if not os.path.exists(P["out"]) or _sha_file(P["out"]) != sha:
        bad.append("캐시 산출의 sha256 이 게시 칸 out_sha256 과 다르다")
    if not re.fullmatch(r"[0-9a-f]{40}", str(pub.get("prereg_commit") or "")):
        bad.append("게시 칸의 등록 커밋이 40자 해시가 아니다")
    return bad


# ══════════════════════════════════════════════════════════════════════════
#  핀 표 · 등록 전 F0 · 등록 커밋 직전 점검
# ══════════════════════════════════════════════════════════════════════════
def pins_table():
    rows = []
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        if not os.path.exists(fp):
            rows.append({"path": p, "blob": None, "sha256_lf": None})
            continue
        rows.append({"path": p, "blob": git_blob_sha(_bytes(fp))[:12], "sha256_lf": _sha_lf(_bytes(fp))[:16]})
    return rows


def f0_now():
    """등록 전 F0 — 핀 뿌리 셋(작업 트리 data/ 와 무관)으로 F0 자식들을 돌려 개수 · 동일성 · G0 만 돌려준다(수익 없음). 결과를 엔진 F0_EXPECT · 등록 문서 §10 에 옮긴다."""
    c = cache_guard_std()
    os.makedirs(c, exist_ok=True)
    n_stale = purge_stale(c)                                  # 앞선 과정이 죽어 남은 작업 폴더 — 열지 않고 지운다(개수만)
    tmp = tempfile.mkdtemp(prefix="ssdix_f0_", dir=c)
    note = None
    try:
        try:
            pf = preflight(tmp)
            f0, sec = pf["f0"], pf["sec"]
        except SystemExit as e:
            note = _scrub(str(e))[:600]
            f0, sec = None, {}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if f0 is None:
        return {"ok": False, "note": note, "stale_deleted": n_stale}
    return {"sec": sec, "ok": f0.get("ok"), "bad": f0.get("bad"), "stale_deleted": n_stale, "signature": f0.get("signature"),
            "detail": {k: f0.get(k) for k in F0_PUB_KEYS if k in f0}, "targets_sec": f0.get("targets_sec"), "g6_sec": f0.get("g6_sec")}


def precommit():
    pp = os.path.join(ROOT, *PREREG.split("/"))
    txt = _read_text(pp) if os.path.exists(pp) else ""
    n_ph, n_dm = placeholder_counts(txt)
    g = site_guard_std()
    gw, vw = wired_state()
    mb = manifest_check()
    pb = pins_check()
    cb = registered_constants_ok()
    xb = ext_problems()
    missing = [p for p in FROZEN if not os.path.exists(os.path.join(ROOT, *p.split("/")))]
    import ssdix as E
    f0set = E.F0_EXPECT is not None and REGISTERED.get("F0_EXPECT") == E.F0_EXPECT
    ready = bool(not name_check() and not n_ph and not n_dm and g["ok"] and gw and vw and not mb and not pb and not cb and not xb and not missing
                 and not check_no_forward() and f0set)
    return {"ready": ready, "prereg": PREREG, "prereg_n": _N_PREREG, "name_ok": not name_check(), "placeholders": n_ph, "draft_marks": n_dm,
            "site_guard": g["ok"], "site_guard_bad": g["bad"][:5], "wired_gitignore": gw, "wired_validate_site": vw,
            "manifest_problems": mb, "pins_problems": pb, "registered_constants_bad": cb, "external_problems": xb, "frozen_missing": missing,
            "no_forward": not check_no_forward(), "f0_expect_set": f0set, "head": _git("rev-parse", "HEAD").stdout.strip()}


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기(러너 경로 전체 · 산출은 열지 않고 지운다 · 참/거짓 · 초만)
# ══════════════════════════════════════════════════════════════════════════
def smoke():
    import contextlib
    cache = cache_guard_std()
    os.makedirs(cache, exist_ok=True)
    n_stale = purge_stale(cache)                              # 앞선 과정이 죽어 남은 작업 폴더(실자료 산출이 있을 수 있다) — 열지 않고 지운다(개수만)
    tmp = tempfile.mkdtemp(prefix="ssdix_runner_smoke_", dir=cache)
    if _inside(tmp, ROOT):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    saved = dict(_OVR)
    res = {"ok": False, "steps": {}, "started": _now(), "stale_deleted": n_stale}
    t0 = time.time()
    sink = io.StringIO()
    real_out = os.path.join(cache, "out")
    before = sorted(f for f in os.listdir(real_out) if f.startswith("_ssdixout")) if os.path.isdir(real_out) else []
    try:
        _OVR.update({"out": os.path.join(tmp, "out"), "gitmark": os.path.join(tmp, "gitdir_" + GIT_MARK_NAME), "tag": tmp})
        P = paths()
        t1 = time.time()
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                rec = bake("SMOKE", smoke=True)
            res["steps"]["bake"] = {"ok": True, "sec": round(time.time() - t1, 1), "registration_error_empty": not rec.get("registration_error"),
                                    "start_tag": rec.get("start_tag")}
        except BaseException as e:                           # noqa: BLE001
            msg = _scrub("%s: %s" % (type(e).__name__, str(e)))
            res["steps"]["bake"] = {"ok": False, "sec": round(time.time() - t1, 1),
                                    "stage": ("F0" if "F0 실패" in msg else "자식" if "자식 과정" in msg else "기타"),
                                    "err": msg[-1500:]}               # 소수는 <num> 으로 지운 오류 꼬리(값 없음 — 참/거짓 · 경로 · 이름만)
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
        try:
            with contextlib.redirect_stdout(sink):
                pub = _read_json(P["public"])
                files["not_stopped"] = not pub.get("stopped")
                txt = result_doc(pub)
                files["public_safe"] = not public_safe_std(pub)
                del pub
            files["result_doc_rendered"] = bool(txt)
            files["result_doc_has_cache_marker"] = CACHE_ONLY_KEY in txt
            del txt
        except BaseException:                                # noqa: BLE001
            files["result_doc_rendered"] = False
        res["files"] = files
        b = res["steps"].get("bake") or {}
        res["ok"] = bool(b.get("ok") and b.get("registration_error_empty") and all(files[k]["exists"] for k in ("out", "mark", "runlog", "public", "gitmark"))
                         and files["second_run_blocked"] and files["finished_marks"] and files["restart_blocked"] and files.get("public_safe")
                         and files.get("not_stopped") and files.get("result_doc_rendered") and not files.get("result_doc_has_cache_marker"))
    finally:
        _OVR.clear()
        _OVR.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
        res["stdout_discarded_unread"] = True
        del sink
    res["deleted_unread"] = not os.path.exists(tmp)
    after = sorted(f for f in os.listdir(real_out) if f.startswith("_ssdixout")) if os.path.isdir(real_out) else []
    res["real_out_untouched"] = before == after == []
    res["real_gitmark_absent"] = not os.path.exists(_git_mark_path())
    res["sec"] = round(time.time() - t0, 1)
    res["ok"] = bool(res["ok"] and res["deleted_unread"] and res["real_out_untouched"] and res["real_gitmark_absent"])
    _write_text(os.path.join(cache, "meta", "_smoke_ssdix_run.json"), json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    return res


SMOKE_ALLOWED_KEYS = {"ok", "steps", "started", "stale_deleted", "files", "tag", "err", "stdout_discarded_unread", "deleted_unread", "real_out_untouched", "real_gitmark_absent", "sec",
                      "bake", "registration_error_empty", "start_tag", "stage", "exists", "nonempty", "second_run_blocked", "finished_marks", "tag_file",
                      "restart_blocked", "not_stopped", "public_safe", "result_doc_rendered", "result_doc_has_cache_marker", "out", "mark", "runlog",
                      "public", "gitmark"}


# ══════════════════════════════════════════════════════════════════════════
#  합성 점검(실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _direct_small(E, R, b, cap, scaled):
    """참 풀이(작은 S 만) — 절단면 없이 수준마다 η_s · S 개 부족분을 다 둔 LP(Rockafellar · Uryasev 꼴) · 절단면 풀이와 대조."""
    import numpy as np
    import scipy.sparse as sp
    R = np.asarray(R, float)
    b = np.asarray(b, float)
    S, N = R.shape
    a = E.level_coef(S, scaled)
    bsum = np.cumsum(np.sort(b))
    iw, iy, ie, idd, iV = 0, N, N + S, N + 2 * S, N + 2 * S + S * S
    nv = iV + 1
    c = np.zeros(nv)
    c[iV] = -1.0
    Aeq, beq = E._eq_block(R, nv, iw, iy)
    q = np.arange(S * S)
    si, ti = np.repeat(np.arange(S), S), np.tile(np.arange(S), S)
    r1, c1 = np.concatenate([q, q, q]), np.concatenate([ie + si, iy + ti, idd + q])
    v1 = np.concatenate([np.ones(S * S), -np.ones(S * S), -np.ones(S * S)])
    sg = np.arange(1, S + 1, dtype=float)
    r2 = np.concatenate([S * S + np.arange(S), S * S + si, S * S + np.arange(S)])
    c2 = np.concatenate([ie + np.arange(S), idd + q, np.full(S, iV)])
    v2 = np.concatenate([-sg, np.ones(S * S), a])
    A = sp.csr_matrix((np.concatenate([v1, v2]), (np.concatenate([r1, r2]), np.concatenate([c1, c2]))), shape=(S * S + S, nv))
    bu = np.concatenate([np.zeros(S * S), -bsum])
    bnd = [(0.0, cap)] * N + [(None, None)] * (2 * S) + [(0.0, None)] * (S * S) + [(None, None)]
    res = E._lp(c, A, bu, Aeq, beq, bnd)
    return res.x[:N], float(res.x[iV]), int(res.status)


def _st_lp_planted():
    """심은 지배 자산 복원(등록 §3-9) — 기준 + 0.05%/일 인 자산 다섯(나머지는 그보다 못하다) · 상한 20% → 다섯에 20% 씩 · V = 0.05 정확히."""
    import numpy as np
    import ssdix as E
    rng = np.random.default_rng(5)
    S, N = 60, 40
    b = rng.standard_t(4, S) * 0.8
    R = np.column_stack([b + 0.05] * 5 + [b + 0.05 - np.abs(rng.normal(0, 0.5, S)) for _ in range(N - 5)])
    s1 = E.ssd_stage1(R, b)
    s2 = E.ssd_stage2(R, b, s1["V"], np.full(N, 1.0 / N), seed_cuts=s1["cuts"], w1=s1["w"])
    w = E.clean_weights(s2["w"])
    # 2단계는 V ≥ V* − 1e−6(%/일) 안에서 회전을 줄이므로 1e−6 수준의 비중이 다른 이름으로 샐 수 있다(등록 TIE_EPS) — 허용 폭은 그 크기의 몇 배
    ok = s1["status"] == 0 and s2["status"] == 0 and abs(s1["V"] - 0.05) < 1e-8 and np.allclose(w[:5], 0.2, atol=1e-5) and float(w[5:].sum()) < 1e-5
    ok &= abs(E.ssd_value(R @ w, b) - 0.05) < 5e-6 and s2["V"] >= s1["V"] - E.TIE_EPS - 1e-9
    # 상한 1 이면 심은 자산 하나로도 된다 — 한 자산 b + 0.07 이 있으면 그것이 전부
    R2 = np.column_stack([b + 0.07] + [b + 0.05] * 3 + [b - np.abs(rng.normal(0, 0.5, S)) for _ in range(6)])
    t1 = E.ssd_stage1(R2, b, cap=1.0)
    ok &= t1["status"] == 0 and abs(t1["V"] - 0.07) < 1e-8 and t1["w"][0] > 1 - 1e-6
    return bool(ok)


def _st_lp_vs_direct():
    """절단면 풀이 = 참 LP(수준마다 부족분을 다 둔 판 · 작은 S) — 척도 · 비척도 모두 V 가 같고 해의 V 를 정렬로 다시 재도 같다."""
    import numpy as np
    import ssdix as E
    rng = np.random.default_rng(7)
    ok = True
    for trial in range(2):
        S, N = 40, 25
        b = rng.standard_t(4, S)
        R = b[:, None] * rng.uniform(0.4, 1.5, N) + rng.standard_t(4, (S, N)) * 0.8 + rng.normal(0.02, 0.05, N)
        for sc in (True, False):
            s1 = E.ssd_stage1(R, b, 0.2, scaled=sc)
            wd, Vd, st = _direct_small(E, R, b, 0.2, sc)
            ok &= s1["status"] == 0 and st == 0 and abs(s1["V"] - Vd) < 1e-8 and abs(E.ssd_value(R @ s1["w"], b, sc) - Vd) < 1e-7
            ok &= s1["viol"] <= E.CUT_TOL
    return bool(ok)


def _st_lp_tiebreak():
    """동률 해소(랩 선택) — 똑같은 자산 둘이면 2단계는 직전 보유 쪽을 고른다(두 방향 모두) · V 는 V* − 1e−6 안."""
    import numpy as np
    import ssdix as E
    rng = np.random.default_rng(3)
    S = 50
    b = rng.standard_t(4, S)
    base = b + 0.03
    R = np.column_stack([base, base.copy()] + [b + 0.03 - np.abs(rng.normal(0, 0.4, S)) for _ in range(8)])
    ok = True
    for keep in (0, 1):
        prev = np.zeros(10)
        prev[keep] = 1.0
        s1 = E.ssd_stage1(R, b, cap=1.0)
        s2 = E.ssd_stage2(R, b, s1["V"], prev, seed_cuts=s1["cuts"], w1=s1["w"], cap=1.0)
        ok &= s2["status"] == 0 and abs(s2["w"][keep] - 1.0) < 1e-6 and s2["V"] >= s1["V"] - E.TIE_EPS - 1e-9
    return bool(ok)


def _st_lp_band():
    """C10 섹터 띠 — 무리 비중이 [0.95 b_g, 1.05 b_g] 안 · _band_of 가 시총 없는 이름을 b_g 에 넣지 않는다."""
    import numpy as np
    import ssdix as E
    rng = np.random.default_rng(9)
    S, N = 80, 30
    b = rng.standard_t(4, S)
    R = b[:, None] * rng.uniform(0.4, 1.5, N) + rng.standard_t(4, (S, N)) * 0.8
    groups = ["g%d" % (i % 3) for i in range(N)]
    caps = [float(i + 1) if i != 7 else None for i in range(N)]
    M = {"caps": caps, "sectors": groups}
    band = E._band_of(M)
    s1 = E.ssd_stage1(R, b, band=band)
    s2 = E.ssd_stage2(R, b, s1["V"], np.full(N, 1.0 / N), seed_cuts=s1["cuts"], w1=s1["w"], band=band)
    tot = sum(c for c in caps if c)
    ok = s1["status"] == 0 and s2["status"] == 0
    for g in ("g0", "g1", "g2"):
        bg = sum(c for c, gg in zip(caps, groups) if gg == g and c) / tot
        wg = float(sum(s2["w"][i] for i in range(N) if groups[i] == g))
        ok &= (0.95 * bg - 1e-7) <= wg <= (1.05 * bg + 1e-7) and abs(band[1][g] - 0.95 * bg) < 1e-12
    return bool(ok)


def _st_cvar_mad():
    """C5 · C3 — 목적 값 = 정렬 · 절댓값으로 잰 참값 · 평균 제약 · 상한 · 2단계는 목적을 허용 폭 안에 지키며 ℓ1 을 줄인다 · 무작위 포트가 1단계를 못 넘는다."""
    import numpy as np
    import ssdix as E
    rng = np.random.default_rng(11)
    S, N = 60, 8
    b = rng.standard_t(4, S)
    R = b[:, None] * rng.uniform(0.3, 1.6, N) + rng.standard_t(4, (S, N)) * 0.7 + 0.05
    o = E.cvar_solve(R, b, s_level=6)
    y = R @ o["w"]
    ok = o["status"] == 0 and abs(o["obj"] - np.sort(y)[:6].sum()) < 1e-7 and y.sum() >= b.sum() - 1e-7 and o["w"].max() <= 0.2 + 1e-9
    o2 = E.cvar_solve(R, b, prev=np.full(N, 1.0 / N), s_level=6, obj_star=o["obj"])
    ok &= o2["status"] == 0 and np.sort(R @ o2["w"])[:6].sum() >= o["obj"] - 6 * E.TIE_EPS - 1e-7
    best = max(np.sort(R @ E.cap_norm(rng.dirichlet(np.ones(N))))[:6].sum() for _ in range(500))
    ok &= o["obj"] >= best - 1e-9
    m = E.mad_solve(R, b)
    ym = R @ m["w"]
    ok &= m["status"] == 0 and abs(m["obj"] - np.abs(ym - ym.mean()).sum()) < 1e-7 and ym.sum() >= b.sum() - 1e-7
    m2 = E.mad_solve(R, b, prev=np.full(N, 1.0 / N), obj_star=m["obj"])
    y2 = R @ m2["w"]
    ok &= m2["status"] == 0 and np.abs(y2 - y2.mean()).sum() <= m["obj"] + S * E.TIE_EPS + 1e-7
    return bool(ok)


def _st_clean_cap():
    """부스러기 정리 · 상한 되맞춤 · cap_norm(합 1 · 상한) · exec_drop(가격 없는 이름 빼고 비례로)."""
    import numpy as np
    import ssdix as E
    w = E.clean_weights(np.array([0.2000004, 0.2, 0.2, 0.2, 0.1999996, 5e-7]))
    ok = abs(w.sum() - 1) < 1e-12 and w.max() <= 0.2 + 1e-12 and w[5] == 0.0
    c = E.cap_norm(np.array([100.0, 1, 1, 1, 1, 1, 1]), 0.2)
    ok &= abs(c.sum() - 1) < 1e-12 and abs(c[0] - 0.2) < 1e-12 and c.max() <= 0.2 + 1e-12
    we, nd = E.exec_drop([True, False, True], np.array([0.5, 0.3, 0.2]))
    ok &= nd == 1 and np.allclose(we, [0.5 / 0.7, 0.0, 0.2 / 0.7])            # 남은 이름 < 5 — 상한을 다시 맞출 수 없어 비례만
    we6, nd6 = E.exec_drop([True] * 5 + [False] + [True], np.array([0.2, 0.2, 0.2, 0.1, 0.1, 0.2, 0.0]))
    ok &= nd6 == 1 and abs(we6.sum() - 1) < 1e-12 and we6.max() <= 0.2 + 1e-12 and we6[5] == 0.0 and we6[6] == 0.0   # 상한 되맞춤
    try:
        E.exec_drop([False, False], np.array([0.5, 0.5]))
        ok = False
    except E.StopBake:
        pass
    return bool(ok)


def _syn_prices(rng, D=300, K=12):
    import numpy as np
    P = np.cumprod(1 + rng.normal(0.0004, 0.015, (D, K)), axis=0) * rng.uniform(10, 100, K)
    P[150:170, 3] = np.nan
    P[220:, 5] = np.nan
    P[:40, 7] = np.nan
    return P


def _st_book_vs_dstk():
    """책 경로 — 벡터 판(여럿 한 번에) = 얼린 dstk.book_path(등록 판 · 0 · 10 · 20bp · 틈 · 상장폐지 · 늦은 상장) = 엔진의 한 줄씩 옮김 · 여럿 = 하나씩."""
    import numpy as np
    import ssdix as E
    import dstk as DS
    rng = np.random.default_rng(11)
    P = _syn_prices(rng)
    K = P.shape[1]
    ex_d, ex_v = [], []
    for i in range(45, 290, 21):
        cols = np.sort(rng.choice([c for c in range(K) if np.isfinite(P[i, c])], 5, replace=False))
        w = rng.dirichlet(np.ones(5))
        ex_d.append((i, {("k%d" % c): float(x) for c, x in zip(cols, w)}))
        ex_v.append((i, cols, w[None, :]))
    PX = {("k%d" % c): P[:, c] for c in range(K)}
    ok = True
    Pff = E.ffill_cols(P)
    for c in (0.0, 0.001, 0.002):
        ref = DS.book_path(PX, ex_d, 295, c, i_window=60)
        i_first, path, turn = E.book_paths(Pff, P, ex_v, 295, c, i_window=60)
        mine = E.book_path_ref(PX, ex_d, 295, c, i_window=60)
        ok &= max(abs(ref["path"][d] - path[0][d - i_first]) for d in ref["path"]) < 1e-12 and abs(ref["turn"] - turn[0]) < 1e-12
        ok &= all(ref["path"][d] == mine["path"][d] for d in ref["path"]) and ref["turn"] == mine["turn"]
    W3 = [(i, cols, np.vstack([w, w[:, ::-1], np.full_like(w, 0.2)])) for (i, cols, w) in ex_v]
    i_first, p3, t3 = E.book_paths(Pff, P, W3, 295, 0.001, i_window=60)
    for d in range(3):
        _, p1, t1 = E.book_paths(Pff, P, [(i, cols, Wm[d:d + 1]) for (i, cols, Wm) in W3], 295, 0.001, i_window=60)
        ok &= float(np.nanmax(np.abs(p1[0] - p3[d]))) < 1e-12 and abs(t1[0] - t3[d]) < 1e-12
    return bool(ok)


def _st_fund_closed():
    """월 닫힌 식 = 얼린 qbatch_core.fund_from_path(합성 격자 · 10bp) · 쌍둥이 β 1 = SPY 장부 · β 0 = T-bill 장부 · 교체는 체결 다음 날부터(T+1)."""
    import numpy as np
    import ssdix as E
    import qbatch_core as Q
    import q_switch as SW
    import x_adapter as XA
    rng = np.random.default_rng(3)
    ctx = XA._syn_ctx(n_months=30, seed=3)
    SW._CACHE.clear()
    try:
        F = SW.frame(ctx)
        G = ctx.G
        path = {F.i0: 1.0}
        v = 1.0
        for d in F.day:
            v *= 1 + rng.normal(0.0003, 0.01)
            path[int(d)] = v
        fr = Q.fund_from_path(G, {"path": path, "turn": None}, F.months, cost=0.001, basis="TR")
        mends = list(F.mends)
        gI = np.array([G.IX_TR[mends[k + 1]] / G.IX_TR[mends[k]] for k in range(len(F.months))])
        gS = np.array([path[mends[k + 1]] / path[mends[k]] for k in range(len(F.months))])
        ok = float(np.max(np.abs(E.fund_ex_closed(gI, gS, 0.001) - fr["ex"]))) < 1e-10
        bS, bT = SW.spy_book(ctx), SW.tbill_book(ctx)
        ex_i = [int(F.i0 - 5)] + [int(F.mends[k] + 1) for k in range(1, len(F.months))]
        ok &= float(np.max(np.abs(E.twin_growth(F.day, bS.g0, bT.g0, ex_i, [1.0] * len(ex_i)) - bS.g0))) == 0.0
        ok &= float(np.max(np.abs(E.twin_growth(F.day, bS.g0, bT.g0, ex_i, [0.0] * len(ex_i)) - bT.g0))) == 0.0
        bet = [0.5 if k % 2 else 1.5 for k in range(len(ex_i))]
        g = E.twin_growth(F.day, bS.g0, bT.g0, ex_i, bet)
        j = int(np.flatnonzero(F.day == ex_i[3])[0])
        ok &= abs(g[j] - (1 + bet[2] * (bS.g0[j] - 1) + (1 - bet[2]) * (bT.g0[j] - 1))) < 1e-15
        ok &= abs(g[j + 1] - (1 + bet[3] * (bS.g0[j + 1] - 1) + (1 - bet[3]) * (bT.g0[j + 1] - 1))) < 1e-15
        try:
            E.twin_growth(F.day, bS.g0, bT.g0, [int(F.i0 + 3)], [1.0])
            ok = False
        except E.StopBake:
            pass
        # 항등식 장부를 mix_t1(몫 ≡ 1 · 비용 0)에 넣으면 펀드 월 초과 = 닫힌 식(c 0)
        tw = E._twin_book(SW, F, "T", E.twin_growth(F.day, bS.g0, bT.g0, ex_i, bet))
        frt = XA.mix_t1(F, np.ones(len(F.months)), tw, bS, 0.0, Q.fund_from_path)
        cum = np.concatenate([[1.0], np.cumprod(tw.g0)])
        gT = np.array([cum[mends[k + 1] - F.i0] / cum[mends[k] - F.i0] for k in range(len(F.months))])
        ok &= float(np.max(np.abs(E.fund_ex_closed(gI, gT, 0.0) - frt["ex"]))) < 1e-10
        return bool(ok)
    finally:
        SW._CACHE.clear()


def _st_stats():
    """통계 — 가면 평균 · 얼린 eg30plus.down_t · t(n − 1) 한쪽 p · 80% 하한(배치 X E4 식) · 반등 청구(G-C2 꼴) · 30개월 토막."""
    import numpy as np
    import ssdix as E
    import eg30plus as EP
    from scipy.stats import t as _t
    rs = np.random.RandomState(1)
    d = rs.normal(0.01, 0.1, 120)
    fz = np.zeros(120, bool)
    fz[::4] = True
    st = E.down_delta(d, fz, EP)
    ok = st["n"] == 30 and abs(st["mean"] - d[fz].mean()) < 1e-15 and abs(st["t"] - EP.down_t(d, fz, 3)) < 1e-15
    ok &= abs(st["p"] - float(_t.sf(st["t"], 29))) < 1e-15 and E.p_one_sided(None, 30) is None
    ok &= E.down_delta(d, np.zeros(120, bool), EP)["t"] is None
    x = rs.normal(0.02, 0.3, 120)
    ok &= abs(E.lb80(x) - (x.mean() * 12 - 0.8416 * x.std(ddof=1) * math.sqrt(12) / math.sqrt(10.0))) < 1e-12
    cr = np.zeros(120, bool)
    cr[[3, 10]] = True
    su = np.zeros(120, bool)
    su[[4, 11, 20]] = True
    xx = np.zeros(120)
    xx[[3, 10]] = [0.4, 0.2]
    xx[[4, 11, 20]] = [-0.1, -0.1, -0.05]
    rb = E.rebound_claim(xx, cr, su)
    ok &= rb["ok"] and abs(rb["crash_sum"] - 0.6) < 1e-12
    xx[20] = -0.2
    ok &= not E.rebound_claim(xx, cr, su)["ok"]
    ok &= not E.rebound_claim(-np.abs(xx), cr, su)["ok"]
    bl = E.block_deltas(np.arange(120, dtype=float), fz)
    ok &= len(bl) == 4 and abs(bl[0] - np.arange(0, 30)[::4].mean()) < 1e-12
    return bool(ok)


def _st_holm_gates_judge():
    """확증 가족 = (A) 하나(얼린 v_tests.holm · m 1 · 문턱 0.05) · (B) 는 읽기(명목 참/거짓 · 판정 밖) · (A) 관문 일곱 · (B) 관문 다섯 · 채택 표시 ·
    판정 어휘 · (B) 가 판정을 바꾸지 못한다 · 가면이 등록과 다르면 멈춘다."""
    import ssdix as E
    h = E.holm_family({"A": 0.04})
    ok = h["reject"] == {"A": True} and h["m"] == 1 and abs(h["threshold"]["A"] - 0.05) < 1e-12
    ok &= E.holm_family({"A": 0.06})["reject"] == {"A": False} and E.holm_family({"A": None})["reject"] == {"A": False}
    ok &= E.PRIMARY == ("A",) and E.READING_ARMS == ("B",)
    allA = {k: True for k in ("G0", "G1", "G2", "G3", "G4", "G5", "G6")}
    allB = {k: True for k in ("h1", "h2", "h3", "d1", "d2")}
    M = {"primary": {"A": {"mask": "down_frozen", "n": 35, "p": 0.01}, "B": {"mask": "down_frozen", "n": 35, "p": 0.3}}, "gates_in": {"A": allA, "B": allB}}
    fam, g, ad, vd = E.judge_core(M)
    ok &= fam["reject"] == {"A": True} and ad == {"A": True} and vd == "보류" and fam["m"] == 1
    ok &= fam["reading_B"]["nominal_reject"] is False and fam["reading_B"]["gates_ok"] is True and fam["reading_B"]["in_verdict"] is False
    M2 = dict(M, gates_in={"A": dict(allA, G5=False), "B": allB})
    _f, g2, ad2, vd2 = E.judge_core(M2)
    ok &= ad2 == {"A": False} and vd2 == "측정만" and g2["A"]["conds"]["G5"] is False
    M3 = dict(M, primary={"A": {"mask": "down_frozen", "n": 35, "p": 0.5}, "B": {"mask": "down_frozen", "n": 35, "p": 0.001}})
    f3, _g3, ad3, vd3 = E.judge_core(M3)
    ok &= vd3 == "기각" and ad3 == {"A": False} and f3["reading_B"]["nominal_reject"] is True and E.verdict({}, {}, stopped=True) == "보류"
    M4 = dict(M, gates_in={"A": dict(allA, G6=None), "B": allB})
    ok &= E.judge_core(M4)[2]["A"] is False
    try:
        E.judge_core(dict(M, primary={"A": M["primary"]["A"], "B": {"mask": "all", "n": 120, "p": 0.01}}))
        ok = False
    except E.StopBake:
        pass
    try:
        E.judge_core(dict(M, primary={"A": {"mask": "all", "n": 120, "p": 0.01}, "B": M["primary"]["B"]}))
        ok = False
    except E.StopBake:
        pass
    return bool(ok)


def _st_g0_vs_vcmp():
    """G0 — 엔진의 능동비중 상관 · 겹침 초과 · 사이 달 잇기 = 얼린 v_cmp 식 · 중앙값 문턱(0.30 · 0.10) · 같은 책 → «EG30 닮은 책»."""
    import ssdix as E
    import v_cmp as VC
    wf = {"A": 0.3, "B": 0.2, "C": 0.5}
    wB = {"A": 0.1, "B": 0.4, "C": 0.3, "D": 0.2}
    wE = {"A": 0.5, "D": 0.5}
    ok = E.active_corr(wf, wB, wE) == VC.active_corr(wf, wB, wE) and E.overlap_excess(wf, wB, wE) == VC.overlap_excess(wf, wB, wE)
    ok &= E.hold_between({"2016-08": 1, "2016-09": 2}, ["2016-08", "2016-10"]) == VC.hold_between({"2016-08": 1, "2016-09": 2}, ["2016-08", "2016-10"])
    ok &= E.active_corr(wB, wB, wE) is None
    same = E.g0_summary({"m": wE}, {"m": wB}, {"m": wE})
    ok &= same["pass"] is False and same["label"] == "EG30 닮은 책"
    anti = E.g0_summary({"m": {"B": 0.6, "C": 0.4}}, {"m": wB}, {"m": wE})
    ok &= anti["pass"] is True and anti["corr_med"] < 0
    return bool(ok)


def _st_placebo():
    """G5 뽑기 — 이름 수 · 합 1 · 상한 20% · β̂ 띠 ±0.01 · 같은 씨앗이면 같은 뽑기 · 뽑기끼리 독립 · 이름 5 미만이면 5 로 · 닿지 못하면 대체(개수)."""
    import numpy as np
    import ssdix as E
    rng0 = np.random.default_rng(2)
    betas = rng0.uniform(0.4, 1.8, 400)
    cols, w, bt, tries, fb = E.placebo_draw(E.placebo_rng(0), 400, 25, betas, 0.8)
    ok = len(cols) == 25 and abs(w.sum() - 1) < 1e-12 and w.max() <= 0.2 + 1e-12 and abs(bt - 0.8) <= E.BETA_BAND and not fb
    c2, w2, _b2, _, _ = E.placebo_draw(E.placebo_rng(0), 400, 25, betas, 0.8)
    ok &= np.array_equal(cols, c2) and np.array_equal(w, w2)
    c3, _w3, _b3, _, _ = E.placebo_draw(E.placebo_rng(1), 400, 25, betas, 0.8)
    ok &= not np.array_equal(cols, c3)
    c4, w4, _b4, _, _ = E.placebo_draw(E.placebo_rng(3), 400, 3, betas, 1.2)
    ok &= len(c4) == 5 and w4.max() <= 0.2 + 1e-12
    c5, w5, b5, t5, fb5 = E.placebo_draw(E.placebo_rng(4), 50, 10, np.full(50, 1.0), 0.5)
    ok &= fb5 and t5 == E.PLACEBO_TRIES and abs(b5 - 1.0) < 1e-12
    return bool(ok)


def _st_french():
    """French 일간 CSV 읽기 — 가치가중 절 · 동일가중 절 따로 · −99.99 는 NaN · 날짜 꼴."""
    import numpy as np
    import ssdix as E
    txt = ("This file was created using the 202608 CRSP database.\n\n  Average Value Weighted Returns -- Daily\n,Agric,Food\n20050103,   0.56,  -0.07\n"
           "20050104, -99.99,   1.00\n\n  Average Equal Weighted Returns -- Daily\n,Agric,Food\n20050103,   9.0,  9.0\n")
    d, h, X = E.parse_french_daily(txt)
    ok = d == ["2005-01-03", "2005-01-04"] and h == ["Agric", "Food"] and X[0, 0] == 0.56 and np.isnan(X[1, 0]) and X[1, 1] == 1.0
    d2, _h2, X2 = E.parse_french_daily(txt, section="Average Equal Weighted Returns -- Daily")
    ok &= d2 == ["2005-01-03"] and X2[0, 0] == 9.0
    ff = "x 202608 CRSP\n\n,Mkt-RF,SMB,HML,RF\n20050103,  -1.0, 0.1, 0.2, 0.01\n\nCopyright\n"
    d3, h3, X3 = E.parse_french_daily(ff, section=None)
    ok &= h3 == ["Mkt-RF", "SMB", "HML", "RF"] and d3 == ["2005-01-03"] and X3[0, 3] == 0.01
    return bool(ok)


def _st_fp_beta():
    """French 층 β̂ = 얼린 v_pit.beta_fp 식(252 · ≥ 200 · Dimson 5 · 0.5 축소 — v_pit.dimson_ols 로 다시 잰 값과 같다) · 관측이 모자라면 NaN."""
    import numpy as np
    import ssdix as E
    import v_pit as VP
    rng = np.random.default_rng(4)
    n = 400
    mex = rng.normal(0.0003, 0.01, n)
    y = np.column_stack([1.2 * mex + rng.normal(0, 0.01, n), 0.6 * mex + rng.normal(0, 0.005, n)])
    y[:250, 1] = np.nan
    got = E.fp_beta_block(y, mex, 380)
    XL = VP._lagmat(mex, 5)
    p0 = 380 - 252 + 1
    ok_ = np.isfinite(y[p0:381, 0]) & np.isfinite(XL[p0:381]).all(axis=1)
    bts, _sd, _n = VP.dimson_ols(y[p0:381, 0][ok_], XL[p0:381][ok_])
    ok = abs(got[0] - (0.5 * bts + 0.5)) < 1e-12 and np.isnan(got[1])
    return bool(ok)


def _st_chain_logic():
    """사슬(합성 달 둘) — 첫 달 기준 = 우주 시총가중 · 2단계 · 체결 날 가격 없는 이름 빼기 · 흘린 비중이 다음 달 기준 · 1단계가 실패한 달은 잇는다."""
    import numpy as np
    import pickle
    import ssdix as E
    rng = np.random.default_rng(8)
    tmp = tempfile.mkdtemp(prefix="ssdix_st_chain_")
    try:
        S, N = 50, 12
        paths_, S1 = {}, {}
        for q, m in enumerate(("2016-07", "2016-08", "2016-09")):
            b = rng.standard_t(4, S)
            R = b[:, None] * rng.uniform(0.5, 1.4, N) + rng.standard_t(4, (S, N)) * 0.6 + 0.02
            M = {"m": m, "i": 100 + 21 * q, "keys": ["k%d" % j for j in range(N)], "tickers": ["T%d" % j for j in range(N)], "R": R, "b": b,
                 "caps": [float(j + 1) for j in range(N)], "sectors": ["s"] * N, "beta": [1.0] * N, "exec_ok": [j != 3 for j in range(N)],
                 "drift": [1.0 + 0.01 * j for j in range(N)], "cw": list(E.cap_norm(np.arange(1, N + 1, dtype=float))), "exec_d": "2016-%02d-01" % (8 + q)}
            p_ = os.path.join(tmp, "m_%s.pkl" % m)
            with open(p_, "wb") as f:
                pickle.dump(M, f, protocol=5)
            paths_[m] = p_
            S1[("SSD", m)] = E._task_stage1(("SSD", m, p_)) if m != "2016-09" else {"status": 99, "rounds": 400}
        s1p = os.path.join(tmp, "s1.pkl")
        with open(s1p, "wb") as f:
            pickle.dump(S1, f, protocol=5)
        _c, out = E._task_chain(("SSD", ["2016-07", "2016-08", "2016-09"], paths_, s1p))
        ok = out["2016-07"]["status1"] == 0 and out["2016-07"]["status2"] == 0 and not out["2016-07"]["carried"]
        ok &= "k3" not in out["2016-07"]["keys"] and abs(sum(out["2016-07"]["w"]) - 1) < 1e-12
        ok &= out["2016-09"]["carried"] is True and abs(sum(out["2016-09"]["w"]) - 1) < 1e-12 and out["2016-09"]["exec_d"] == "2016-10-01"
        ok &= max(out["2016-08"]["w"]) <= E.CAP + 1e-9
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_pool_determinism():
    """과정 풀(spawn · 둘) 로 푼 1단계 = 한 과정에서 푼 것(바이트 같음) — 해는 과정 수 · 차례와 무관하다."""
    import numpy as np
    import pickle
    import ssdix as E
    rng = np.random.default_rng(12)
    tmp = tempfile.mkdtemp(prefix="ssdix_st_pool_")
    try:
        tasks = []
        for q in range(3):
            S, N = 60, 20
            b = rng.standard_t(4, S)
            R = b[:, None] * rng.uniform(0.5, 1.4, N) + rng.standard_t(4, (S, N)) * 0.6
            M = {"R": R, "b": b, "caps": [1.0] * N, "sectors": ["s"] * N}
            p_ = os.path.join(tmp, "m%d.pkl" % q)
            with open(p_, "wb") as f:
                pickle.dump(M, f, protocol=5)
            tasks.append(("SSD", "m%d" % q, p_))
        serial = [E._task_stage1(t) for t in tasks]
        with E._pool(2) as pool:
            par = list(pool.imap(E._task_stage1, tasks, chunksize=1))
        ok = all(np.array_equal(a["w"], b["w"]) and a["V"] == b["V"] for a, b in zip(serial, par))
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_no_eg30_in_ssd():
    """SSD 책은 EG30 을 입력으로 쓰지 않는다 — 목표 · 풀이 · 사슬 · 위약 · 책 함수의 원천에 EG30 식별자가 없다(EG30 은 G0 · (B) 의 얼린 RD 코어로만)."""
    import inspect
    import ssdix as E
    bad_words = ("V0_targets", "v0_targets", "EG_BASE", "offense_v0", "eg_q5", "_eg30", "egstep", "eg_scores")
    ok = True
    for fn in (E.targets_child, E._task_stage1, E._task_chain, E._stage2_one, E.placebo_plan, E._books_body, E.ssd_stage1, E.ssd_stage2, E._g6_body):
        src = inspect.getsource(fn)
        ok &= not any(w in src for w in bad_words)
    return bool(ok)


def _st_blob_guard():
    import ssdix as E
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "wb") as f:
            f.write(b"x = 1\n")
        good = git_blob_sha(b"x = 1\n")
        ok = E.assert_blobs(td, {"m": good})
        try:
            E.assert_blobs(td, {"m": "0" * 40})
            ok = False
        except E.StopBake:
            pass
        with open(os.path.join(td, "m.py"), "wb") as f:
            f.write(b"x = 1\r\n")
        ok &= E.assert_blobs(td, {"m": good})
    ok &= not reused_problems()
    ok &= E.ROOT_BLOBS["egstep"] == REUSED_BLOBS["build/egstep.py"] and E.VROOT_BLOBS["x_adapter"] == REUSED_BLOBS["build/x_adapter.py"]
    return bool(ok)


def _st_lock_and_tag():
    """동시 굽기 막기 — 배타 잠금은 두 번째를 멈추고 풀면 다시 잡힌다 · 시작 태그가 이미 있으면 SSDIX_RERUN 일 때만 «already»."""
    tmp = tempfile.mkdtemp(prefix="ssdix_st_lock_")
    saved = dict(_OVR)
    try:
        P = {"dir": tmp}
        lk = _take_lock(P, "C")
        try:
            _take_lock(P, "C")
            ok = False
        except SystemExit:
            ok = True
        _release_lock(lk)
        lk2 = _take_lock(P, "C")
        _release_lock(lk2)
        ok &= not os.path.exists(lk2)
        _OVR["tag"] = tmp
        ok &= _push_start_tag("C") == "override" and _tag_now() == "C"
        try:
            _push_start_tag("C")
            ok = False
        except SystemExit:
            pass
        ok &= _push_start_tag("C", rerun="r") == "already"
        return bool(ok)
    finally:
        _OVR.clear()
        _OVR.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)


def _st_purge_stale():
    """남은 작업 폴더 — ssdix_work_* · ssdix_f0_* · ssdix_runner_smoke_* 폴더만 열지 않고 지우고 개수를 돌려준다(out · meta · 같은 이름의 파일은 그대로)."""
    tmp = tempfile.mkdtemp(prefix="ssdix_st_stale_")
    try:
        for d in ("ssdix_work_a1", "ssdix_f0_b2", "ssdix_runner_smoke_c3", "out", "meta", "raw"):
            os.makedirs(os.path.join(tmp, d, "x"), exist_ok=True)
            _write_text(os.path.join(tmp, d, "x", "out_s.json"), "{}\n")
        _write_text(os.path.join(tmp, "ssdix_work_file.txt"), "x\n")
        n = purge_stale(tmp)
        left = sorted(os.listdir(tmp))
        return bool(n == 3 and left == ["meta", "out", "raw", "ssdix_work_file.txt"] and purge_stale(tmp) == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_start_guard():
    ok = True
    for full, rerun, marks, remote, want_ok in (("A", None, [], None, True), ("A", None, [("m", "A · t\nFINISHED x")], None, False),
                                                ("A", "r", [("m", "A · t")], None, True), ("A", None, [("m", "A · t")], None, False),
                                                ("A", "r", [], None, False), ("A", "r", [("m", "B · t")], None, False),
                                                ("A", None, [], "B", False), ("A", None, [], "A", False), ("A", "r", [("m", "A · t")], "A", True)):
        try:
            start_guard(full, rerun, marks, remote)
            got = True
        except SystemExit:
            got = False
        ok &= got == want_ok
    return bool(ok)


def _st_frozen_refuses():
    """SSDIX_COMMIT 없이 · 모르는 커밋으로는 판 점검이 멈춘다(아무것도 쓰지 않는다)."""
    ok = True
    for env in ({}, {"SSDIX_COMMIT": "0" * 40, "_SSDIX_NO_FETCH": "1"}):
        try:
            frozen_check(env)
            ok = False
        except SystemExit:
            pass
    return ok


def _st_scrub():
    a = _scrub("값 0.1234 · 1e-05 · 2.5E+03 · -.5 · 2014-08 · 3 개\n  File \"x.py\", line 12")
    return a == "값 <num> · <num> · <num> · <num> · 2014-08 · 3 개\n  File \"x.py\", line 12"


def _st_registered():
    import ssdix as E
    return not registered_constants_ok(E)


def _st_wire():
    g0, v0 = "a\n", 'x = 1\nprint("사이트 검증:", 1)\n'
    g1, v1 = wire_texts(g0, v0)
    g2, v2 = wire_texts(g1, v1)
    return bool(g1 == g2 and v1 == v2 and "_ssdixout*" in g1 and v1.index("확률지배(SSD) 지수 강화 책 역할 검정") < v1.index('print("사이트 검증:"'))


def _st_names():
    want = ["data/_ssdixout.json", "data/_ssdix_other.json", "data/_ssdixfwd/genesis.json", "x/ssdix_cache/a", "_ssdixout.public.json",
            "data/49_Industry_Portfolios_daily_CSV.zip"]
    ok = all(scan_repo_names([f]) for f in want)
    return bool(ok and not scan_repo_names([MANIFEST_FILE, "data/style_top.json", "build/ssdix_run.py", "build/ssdix.py", "data/_egstep_manifest.json"]))


def _st_manifest_hashes_only():
    doc = manifest_doc()
    return bool(not manifest_problems(doc) and manifest_problems(dict(doc, leak=0.5)))


def _st_open_encoding():
    """새 두 파일의 open() · io.open() 이 모두 encoding= 을 주거나 바이트 모드다."""
    ok = True
    for p in (ENGINE, RUNNER):
        t = ast.parse(_read_text(os.path.join(ROOT, *p.split("/"))))
        for n in ast.walk(t):
            if isinstance(n, ast.Call):
                f = n.func
                nm = (f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None))
                own = isinstance(f, ast.Name) or (isinstance(f, ast.Attribute) and getattr(f.value, "id", None) == "io")
                if nm == "open" and own:
                    kw = {k.arg for k in n.keywords}
                    mode = n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else next(
                        (k.value.value for k in n.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)), "r")
                    if "encoding" not in kw and "b" not in str(mode):
                        ok = False
    return ok


def _st_std_head():
    """러너 · 엔진 모듈 머리의 import 가 표준 라이브러리뿐(validate_site 가 numpy 없이 불러도 죽지 않게)."""
    std = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    ok = True
    for p in (ENGINE, RUNNER):
        t = ast.parse(_read_text(os.path.join(ROOT, *p.split("/"))))
        for n in t.body:
            if isinstance(n, ast.Import):
                ok &= all(a.name.split(".")[0] in std for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.level == 0:
                ok &= (n.module or "").split(".")[0] in std
    return bool(ok)


def _st_smoke_no_sizes():
    """연기 기록 칸은 허용 목록뿐 — 크기 · 길이 · 형 · 키 목록 · 값이 들어갈 칸이 없다."""
    src = _read_text(os.path.join(ROOT, *RUNNER.split("/")))
    body = src[src.index("def smoke():"):src.index("SMOKE_ALLOWED_KEYS")]
    keys = set(re.findall(r'\[\s*"([a-z_]+)"\s*\]\s*=', body)) | set(re.findall(r'"([a-z_]+)"\s*:', body))
    return bool(keys and keys <= SMOKE_ALLOWED_KEYS and "getsize(P[k]) > 0" in body and "len(" not in body.replace("len(tmp)", ""))


def _st_no_forward():
    import ssdix as E
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    return bool(not any(hasattr(E, n) for n in FORBIDDEN_ENGINE_NAMES) and "_ssdixfwd" not in src and not check_no_forward())


def _st_no_etf_holding():
    """어떤 팔의 목적지도 ETF · 선물 · 옵션이 아니다 — SSD · 대조 책은 v_pit 명단 주식에서만 고른다 · SPY TR 은 기준 분포 · 쌍둥이 항등식(현금 표지) · 펀드 90% 지수 다리의
    수익 대리로만 · 엔진에 ETF 이름 없음 · 쌍둥이 장부는 cash=True(보유하지 않는 항등식)."""
    import ssdix as E
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    ok = not any(('"%s"' % t) in src for t in ("IVE", "IVW", "RSP", "SPLV", "USMV", "QQQ", "SPHB", "XLK"))
    body = src[src.index("def targets_child(job):"):src.index("def placebo_plan(")]
    ok &= "U.members(m)" in body and "spy" in body
    tb = src[src.index("def _twin_book("):src.index("def s_child(")]
    ok &= "bk.cash = " in tb and "True" in tb
    return bool(ok)


def _fake_main(stopped=None):
    """게시 칸 · 결과 문서 시험용 합성 산출(값은 표지 수 0.5555)."""
    if stopped:
        return {"kind": "ssdix_out", "stopped": stopped}
    mk = 0.5555
    m = {"n": 120, "ann_ex": mk, "te": mk, "ir": mk, "t_iid": mk, "nw_t": mk, "win": 55.5, "years": {"2021": mk, "2022": mk}, "years_won": 5, "n_years": 11,
         "down_n": 39, "down_mean": mk, "down_win": 50.0, "up_mean": mk, "down_capture": mk, "up_capture": mk, "sleeve_beta": 0.9,
         "episodes": [{"kind": "급락", "name": "코로나19 팬데믹", "ex": mk}], "crash_won": 1, "surge_won": 5,
         "mech": {"crash_legs": {"n": 8, "mean": mk, "win": 3}, "rebounds": {"n": 8, "mean": mk, "win": 7}}, "roll12": {"n": 109, "hit": 55.5},
         "halves": [mk, mk], "blocks": [mk, mk, mk, mk], "series_leak": None}
    arm = {"m": m, "m20": {"ann_ex": mk, "nw_t": mk}, "down_frozen": {"n": 35, "mean": mk, "win": 50.0}, "turn": 3.3, "cost_drag": mk}
    arms = {a: dict(arm) for a in ARM_ORDER}
    prim = {a: {"n": 35, "mean": mk, "t": mk, "p": 0.29, "mask": "down_frozen"} for a in ("A", "B")}
    ctl = {c: {"delta_down": mk, "t": mk, "x_ann": mk, "x_down": mk, "x_up": mk, "x20_ann": mk, "vs_ssd_down": mk} for c in CTRL_ORDER}
    return {"kind": "ssdix_out", "window": ["2016-09", "2026-08"], "n_hold": 120, "arms": arms, "primary": prim,
            "family": {"p": {"A": 0.29}, "reject": {"A": False}, "threshold": {"A": 0.05}, "order": ["A"], "m": 1, "alpha": 0.05,
                       "reading_B": {"p": 0.29, "nominal_reject": False, "gates_ok": True, "in_verdict": False}},
            "gates": {"A": {"conds": {k: False for k in ("G0", "G1", "G2", "G3", "G4", "G5", "G6")}, "ok": False},
                      "B": {"conds": {k: True for k in ("h1", "h2", "h3", "d1", "d2")}, "ok": True}},
            "gates_in": {"A": {"G0": False}, "B": {"h1": True}}, "adopt": {"A": False}, "verdict": "기각",
            "detail": {"A": {"rebound": {"crash_sum": mk, "surge_sum": mk, "ok": False}, "lb80": mk, "delta20_down": mk, "blocks": [mk, mk, mk, mk],
                             "halves": [mk, mk], "x_down": mk, "x_up": mk, "dil_down": mk, "beta_med": 0.8},
                       "B": {"all_ann": mk, "all20_ann": mk, "twin_down": mk, "twin_all20_ann": mk, "rebounds": {"RDSSD": 8, "RD": 8}, "turn": 3.4,
                             "d_on_down": {"n": 7, "mean": mk}, "crash_m": mk, "surge_m": mk, "states": {"n": 120}}},
            "controls": ctl, "years_delta": {"A": {"2021": mk}, "B": {"2021": mk}},
            "pairing": {"E0": {"ok": True}, "E_RD": {"rd_max_abs": 0.0, "c0_max_abs": 0.0, "ok": True}},
            "books_pairing": {"P1_ok": True, "P2_ok": True, "P1_max_abs": 0.0, "P2_max_abs": 0.0}, "down": {"n_frozen": 35},
            "g5": {"window": ["2016-09", "2026-08"], "k": 1000, "true": mk, "pct": 77.7, "pass": False, "q": {"p05": mk, "p50": mk, "p95": mk}, "n_fallback": 0},
            "g0": {"n_months": 120, "corr_med": 0.1, "ovx_med": 0.02, "pass": True},
            "g6": {"window": ["2006-09", "2026-08"], "n": 240, "n_down": 80, "pass": False, "delta_pos": True, "t_ge1": False, "sec": 12.5,
                   "cache_only": {"window": ["2006-09", "2026-08"], "mean": 0.4444, "t": 0.9},
                   "half10": {"window": ["2016-09", "2026-08"], "n": 120, "n_down": 35, "mean": mk, "t": mk}},
            "pre": {"window": ["2015-04", "2016-08"], "n": 17, "n_down": 6, "delta_pos": True, "x_down_pos": False,
                    "cache_only": {"window": ["2015-04", "2016-08"], "mean": 0.4444}},
            "dsr": {"N": 1071, "sr_m": mk, "sr0": mk, "dsr": 0.1234},
            "readings": {"A": {"bull_lag": True, "variance_like": False}, "B": {"beta_only": False}},
            "predictions": {k: True for k in PRED_KO},
            "multiplicity": {"m_confirmatory": 1, "alpha": 0.05, "cum_n_before": 1063, "rows_counted": 8, "cum_n_after": 1071, "counted": ["A"]}}


def _fake_f0():
    return {"ok": True, "bad": [], "egstep": {"ok": True, "expect_diff": []},
            "targets": {"members_min": 500, "members_max": 520, "elig_min": 470, "elig_med": 490, "elig_max": 510, "cov_min_x1000": 930, "cov_med_x1000": 960,
                        "covw_min_x1000": 950, "months_cov_lt90": 0, "SSD_ok1": 121, "SSD_ok2": 121, "SSD_carried": 0, "SSD_tie_med_x1000": 12, "SSD_tie_max_x1000": 90, "SSD_ties_gt5pct": 2, "SSD_names_min": 7,
                        "SSD_names_max": 30, "SSD_drops": 1, "SSD_hash16": "ab" * 8, "PRE_hash16": "cd" * 8, "C10_hash16": "ef" * 8, "placebo_fallback": 0,
                        "placebo_hash16": "12" * 8},
            "f0r": {"grid_same": True, "spy_same": True, "v0_hash_ok": True, "spy_max_abs_diff": 0.0, "n_win_dates": 2513,
                    "g0": {"n_months": 120, "corr_med": 0.1, "ovx_med": 0.02, "pass": True}},
            "g6": {"g6_vintage_ok": True, "g6_forms": 241, "g6_elig_min": 49, "g6_elig_max": 49, "g6_ok1": 241, "g6_hash16": "99" * 8}}


def _st_public_and_result_doc():
    """게시 칸 — 캐시 표지 · cache_only · 계열 없음 · 공개 안전 · 결과 문서 머리 세 줄 · «등록 커밋 `<40자>`» 가 첫 «커밋 <해시>» · 20년 층 · 앞 창 값은 게시 칸에 없다 ·
    심은 값 계열 · 2016-09 앞 창 실수는 public_safe_std 가 잡는다 · 멈춤 판 · 표시 판의 읽기 줄 · 등록 오류 글의 소수 지우기."""
    full = "0123456789abcdef0123456789abcdef01234567"
    out = {CACHE_ONLY_KEY: True, "prereg": PREREG, "f0": _fake_f0(), "main": _fake_main(), "pins": {"root": {"code_pin": "1d81f083a404"}, "vroot": "c6a35ff0", "droot": "44c1a26f6"},
           "series": {"s": {"ex": {"SSD": [0.1] * 120}}}}
    pub = public_doc(out, "0" * 64, 1, {"commit": full})
    blob = json.dumps(pub, ensure_ascii=False)
    txt = result_doc(pub)
    ok = CACHE_ONLY_KEY not in blob and "series_leak" not in blob and '"series"' not in blob and "cache_only" not in blob and "0.4444" not in blob and "0.56" in txt
    ok &= all(re.search(r"^\s*%s\s*[:：]" % k, txt, re.M) for k in ("풀카드", "판정", "규칙"))
    ok &= re.search(r"^풀카드:\s*없음", txt, re.M) is not None and re.search(r"^규칙:\s*없음", txt, re.M) is not None
    hm = re.search(r"커밋\s*[`'\"]?([0-9a-f]{7,40})", txt)
    ok &= bool(hm) and hm.group(1) == full and re.search(r"^판정:\s*기각", txt, re.M) is not None
    ok &= bool(public_safe_std({"x": {"window": ["2014-09", "2026-08"], "v": 0.5}})) and not public_safe_std({"x": {"window": ["2014-09", "2026-08"], "n": 144}})
    ok &= bool(public_safe_std({"s": [0.1, 0.2, 0.3, 0.4, 0.5]}))
    bad = dict(pub)
    bad["arms"] = dict(pub["arms"], leak=[0.1] * 12)
    ok &= bool(public_safe_std(bad))
    ok &= bool(public_safe_std(dict(pub, pre=dict(pub["pre"], mean=0.4))))
    tmpf = tempfile.mkdtemp(prefix="ssdix_st_re_")
    try:
        rp = os.path.join(tmpf, "re.txt")
        _write_text(rp, "# 주석\n§4 글은 0.25 라 했으나 코드는 다른 값\n\n두 번째 줄 2021-10\n")
        re_ = reg_err_lines(rp)
    finally:
        shutil.rmtree(tmpf, ignore_errors=True)
    txt_re = result_doc(pub, re_)
    ok &= re_[0] == ["§4 글은 <num> 라 했으나 코드는 다른 값", "두 번째 줄 2021-10"] and len(re_[1]) == 16
    ok &= ("등록 오류: §4 글은 <num> 라 했으나 코드는 다른 값; 두 번째 줄 2021-10" in txt_re) and "0.25" not in txt_re
    ok &= all(s in txt for s in ("## 1. 확증 가족", "G5 무작위 포트 위약 백분위 ≥ 95", "## 3. 대조", "만들지 않은 대조", "앞 창(보유 2015-04~2016-08",
                                 "20년 값은 캐시에만", "## 7. 짝맞춤", "E-RD", "P9 G6 French 층", "누적 N 1063 → 1071(센 줄 8", "남은 작업 폴더: 0", "(B) 는 등록 읽기다 — 판정을 바꾸지 못한다", "| (B) 방어 스텝 목적지 · 읽기 |", "Holm 기각 0/1",
                                 "SSD 책은 EG30 을 입력으로 쓰지 않는다"))
    ok &= "의 채택 표시에 읽기" not in txt
    pub3 = public_doc(dict(out, main=dict(_fake_main(), adopt={"A": True}, verdict="보류")), "0" * 64, 1, {"commit": full, "stale_deleted": 2})
    txt3 = result_doc(pub3)
    ok &= "**(A) 의 채택 표시에 읽기(강세 뒤짐(하락월 밖 X < 0))가 붙었다" in txt3 and "남은 작업 폴더: 2" in txt3
    ok &= re.search(r"^판정:\s*보류", txt3, re.M) is not None and not public_safe_std(pub3)
    pub2 = public_doc(dict(out, main=_fake_main(stopped="장부 날짜가 뿌리 격자와 다르다")), "0" * 64, 1, {"commit": full})
    txt2 = result_doc(pub2)
    ok &= "## 멈춤" in txt2 and "0.5555" not in json.dumps(pub2) and re.search(r"^판정:\s*보류", txt2, re.M) is not None
    return bool(ok)


def _st_result_write_guard():
    """--result-doc --write 문지기 — 연기 판 · FINISHED 없음 · 산출 sha 불일치 · 커밋이 40자 해시가 아니면 거절 · 모두 맞으면 통과."""
    tmp = tempfile.mkdtemp(prefix="ssdix_st_")
    try:
        P = {"out": os.path.join(tmp, "_ssdixout.json"), "mark": os.path.join(tmp, "_ssdixout.started"), "gitmark": os.path.join(tmp, "gm")}
        with open(P["out"], "wb") as f:
            f.write(b'{"x": 1}\n')
        sha = _sha_file(P["out"])
        for m in (P["mark"], P["gitmark"]):
            _write_text(m, "C · t\n%s %s t\n" % (FINISHED, sha))
        pub = {"ssdix_public_view": True, "smoke": False, "out_sha256": sha, "prereg_commit": "a" * 40}
        ok = not result_doc_write_problems(pub, P)
        ok &= bool(result_doc_write_problems(dict(pub, smoke=True), P))
        ok &= bool(result_doc_write_problems(dict(pub, out_sha256="0" * 64), P))
        ok &= bool(result_doc_write_problems(dict(pub, prereg_commit="SMOKE"), P))
        _write_text(P["gitmark"], "C · t\n")
        ok &= bool(result_doc_write_problems(pub, P))
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_predictions_signature():
    """예측 칸 = 등록 §8 의 아홉(참/거짓만) · F0 서명은 정수 · 날짜 글자 · 참/거짓 · 짧은 해시만(실수 없음)."""
    import ssdix as E
    M = _fake_main()
    S = {"detail": M["detail"], "primary": M["primary"], "gates_in": {"A": {"G1": False}}}
    P = E.predictions({"S": S, "family": M["family"], "adopt": M["adopt"], "G6": M["g6"]})
    ok = set(P) == set(PRED_KO) and all(isinstance(v, bool) for v in P.values())
    sig = f0_signature(_fake_f0())
    ok &= all(v is None or (isinstance(v, (int, str, bool)) and not isinstance(v, float)) for v in sig.values())
    if E.F0_EXPECT is not None:
        X = E.F0_EXPECT                                     # 되짓기: 등록 서명에서 F0 기록을 다시 지으면 서명 함수가 등록 서명을 그대로 낸다
        f0 = {"egstep": {"ok": X["egstep_f0_ok"], "expect_diff": []}, "targets": {k[2:]: v for k, v in X.items() if k.startswith("t_")},
              "f0r": {"grid_same": X["grid_same"], "spy_same": X["spy_same"], "v0_hash_ok": X["v0_hash_ok"], "n_win_dates": X["n_win_dates"],
                      "n_eg_forms": X["n_eg_forms"], "g0": {"pass": X["g0_pass"], "n_months": X["g0_months"], "corr_med": X["g0_corr_x1000"] / 1000.0,
                                                           "ovx_med": X["g0_ovx_x1000"] / 1000.0}},
              "g6": {k: v for k, v in X.items() if k.startswith("g6_")}}
        ok &= f0_signature(f0) == X and REGISTERED.get("F0_EXPECT") == X
        ok &= all(not isinstance(v, float) for v in X.values())
    return bool(ok)


def _st_git_blob():
    return git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391" and git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


SELFTESTS = (_st_lp_planted, _st_lp_vs_direct, _st_lp_tiebreak, _st_lp_band, _st_cvar_mad, _st_clean_cap, _st_book_vs_dstk, _st_fund_closed, _st_stats,
             _st_holm_gates_judge, _st_g0_vs_vcmp, _st_placebo, _st_french, _st_fp_beta, _st_chain_logic, _st_pool_determinism, _st_no_eg30_in_ssd,
             _st_blob_guard, _st_lock_and_tag, _st_purge_stale, _st_start_guard, _st_frozen_refuses, _st_scrub, _st_registered, _st_wire, _st_names,
             _st_manifest_hashes_only, _st_open_encoding, _st_std_head, _st_smoke_no_sizes, _st_no_forward, _st_no_etf_holding, _st_public_and_result_doc,
             _st_result_write_guard, _st_predictions_signature, _st_git_blob)


def selftest():
    import contextlib
    res, t0 = {}, time.time()
    for f in SELFTESTS:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                res[f.__name__] = bool(f())
        except BaseException as e:                           # noqa: BLE001
            res[f.__name__] = "예외 %s: %s" % (type(e).__name__, _scrub(str(e))[:200])
    ok = all(v is True for v in res.values())
    return {"ok": ok, "n": len(res), "n_ok": sum(1 for v in res.values() if v is True), "tests": res, "sec": round(time.time() - t0, 1)}


# ══════════════════════════════════════════════════════════════════════════
def main(argv):
    if "--selftest" in argv:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    if "--guard" in argv:
        g = site_guard_std()
        print(json.dumps(g, ensure_ascii=False, indent=1))
        return 0 if g["ok"] else 1
    if "--pins" in argv:
        print("| 파일 | git blob | sha256(LF) 앞 16 |")
        print("|---|---|---|")
        for r in pins_table():
            print("| `%s` | `%s` | `%s` |" % (r["path"], r["blob"], r["sha256_lf"]))
        return 0
    if "--f0" in argv:
        r = f0_now()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    if "--manifest" in argv:
        print(json.dumps(write_manifest(), ensure_ascii=False))
        return 0
    if "--wire" in argv:
        print(json.dumps(wire(apply="--apply" in argv), ensure_ascii=False))
        return 0
    if "--precommit" in argv:
        r = precommit()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ready"] else 1
    if "--smoke" in argv:
        r = smoke()
        print(json.dumps({"ok": r["ok"], "sec": r["sec"], "deleted_unread": r["deleted_unread"]}, ensure_ascii=False))
        return 0 if r["ok"] else 1
    if "--once" in argv:
        once()
        return 0
    if "--public-view" in argv:
        print(json.dumps(public_view_writer(), ensure_ascii=False))
        return 0
    if "--result-doc" in argv:
        tail = argv[argv.index("--result-doc") + 1:]
        re_path = None
        if "--reg-err" in tail:
            q = tail.index("--reg-err")
            if q + 1 >= len(tail) or tail[q + 1].startswith("--"):
                raise SystemExit("🚨 --reg-err 뒤에 등록 오류 글 파일을 준다")
            re_path = tail[q + 1]
            tail = tail[:q] + tail[q + 2:]
        rest = [a for a in tail if not a.startswith("--")]
        p = rest[0] if rest else paths()["public"]
        pub = _read_json(p)
        txt = result_doc(pub, reg_err_lines(re_path) if re_path else None)
        if "--write" in argv:
            wb = result_doc_write_problems(pub)
            if wb:
                raise SystemExit("🚨 결과 문서를 쓰지 않는다: %s" % "; ".join(wb))
            _write_text(os.path.join(ROOT, *RESULT.split("/")), txt)
            print("→ %s" % RESULT)
        else:
            print(txt)
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
