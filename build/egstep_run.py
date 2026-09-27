# -*- coding: utf-8 -*-
"""build/egstep_run.py — EG30 상태 조건 스텝 역할 검정(EGSTEP) 한 번 굽기 러너.

사전등록: build/PREREG-<등록 날짜>-EGSTEP.md 하나(이 러너는 날짜를 박지 않는다 · 결과 문서 = 그 이름 + «-RESULT»).
계산은 build/egstep.py(엔진)가 핀 판 임시 뿌리 셋 안에서 한다 — 이 러너는 판 점검 · 뿌리 짓기 · 자식 과정 · 시작 표식 · 게시 칸 · 결과 문서만 맡는다.

🚨 사용자 질문(2026-09-27): «EG30 코어 + 금리 스텝(DSTK 가치 다리) + 방어 스텝(방아쇠 → V02 저베타) 성과 괜찮아?» — 이 조합은 잰 적이 없다.
   랩 규율: 먼저 등록 · 한 번 계산. 역할 검정: 두 상태 조건 스텝이 EG30 의 약점(급락 달 · 실질금리 상승)을 고치는가 · 수익과 반등을 내주지 않고.
   앞선 지시(모두 유효): ETF · 선물 · 옵션 · 공매도 보유 없음 · «백테스트 최대 20년» · «미래 일정 다 꺼»(전방 원장 없음 — data/_egstepfwd/ 가 있으면 멈춘다).
🚨 등록 커밋이 origin 에 오르기 전에는 --selftest · --guard · --pins · --manifest · --precommit · --wire · --f0 · --smoke 만 된다.
   --f0 는 개수 · 날짜 · 동일성(해시 · 얼린 V0 경로와의 최대 절대 차)만 · --smoke 는 눈가린 채(산출을 열지 않고 지운다 · 참/거짓 · 초만 싣는다).

  python -X utf8 build/egstep_run.py --selftest           합성만(실자료 없음)
  python -X utf8 build/egstep_run.py --guard              사이트 경계(site_guard_std — 참/거짓 · 이름만)
  python -X utf8 build/egstep_run.py --pins               얼린 파일 · 핀 표(등록 문서 §10 표)
  python -X utf8 build/egstep_run.py --f0                 등록 전 F0(핀 뿌리 셋 · 수익 없음) — 등록 문서 §10 F0 표 · 엔진 F0_EXPECT 의 출처
  python -X utf8 build/egstep_run.py --manifest           data/_egstep_manifest.json(해시만) 쓰기
  python -X utf8 build/egstep_run.py --wire [--apply]     등록 커밋이 .gitignore · build/validate_site.py 끝에 덧붙일 덩이
  python -X utf8 build/egstep_run.py --precommit          등록 커밋 직전 점검(참/거짓 · 이름만)
  python -X utf8 build/egstep_run.py --smoke              러너 경로 전체 눈가린 연기(임시 폴더 · 열지 않고 지운다)
  EGSTEP_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python -X utf8 build/egstep_run.py --once     한 번 굽기(이 길 하나뿐)
  python -X utf8 build/egstep_run.py --public-view        굽기 뒤: 산출 → 게시 칸 다시 쓰기(FINISHED 표식이 있을 때만)
  python -X utf8 build/egstep_run.py --result-doc [<게시 칸 파일>] [--reg-err <글 파일>] [--write]   결과 문서(게시 칸 파일 하나만 읽는 얼린 렌더러)

뿌리 셋(모두 저장소 밖 캐시 · git archive · 얼린 blob 단언 · 작업 트리의 data/ 를 읽지 않는다)
  root   얼린 V0 뿌리 = 얼린 x_adapter.build_root(배치 Q 등록 커밋 build/ + 가격 밖 입력 판 data/ + 가격 판 + P3) — C0 · Q06 상태 · 팔 · 평가
  vroot  배치 V 핀 판 = 얼린 x_adapter.build_vroot — D 목표(--d-child · 짝맞춤 A) · D 책(--dbook-child) · 커버리지(--s-cov-child)
  droot  DSTK 핀 판 = 얼린 dstk_run.materialize(DSTK 자료 핀) — 가치 다리 V30 · 금리 상태 R · DSTK F0 · 판정(v_tests.holm)

한 번 굽기 규약(dstk_run · x_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(실패하면 멈춘다).
  · EGSTEP_COMMIT = 사전등록 문서 · 러너 · 엔진 · 명세(data/_egstep_manifest.json)를 **처음 더한** 커밋 · origin/main 의 조상 · 그 커밋의 등록 문서에 빈칸(⟨TBD)과 초안 괄호(U+3014)가 없다.
  · 얼린 파일(엔진 · 러너 · 명세 · 등록 문서 · 덧붙임 두 곳)이 그 커밋과 바이트 단위로 같다(CRLF 무시) · 러너가 부르는 재사용 파일(x_adapter · dstk · dstk_run) blob 이 핀과 같다.
  · 판 점검 → 배타 잠금 → F0(핀 뿌리 셋 · 수익 없음 · 등록 F0 개수와 같아야) → 시작 표식 셋(로컬 둘 · origin 태그 egstep-started · 계산 전에 민다) →
    가치 다리 · D 책 · S · 판정 자식 → 게시 칸(공개 안전 점검 · 산출보다 먼저) → 산출 · 게시 칸 · 실행 기록 → FINISHED → 잠금 풀기.
  · FINISHED 가 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤 · 산출 전 기술적 중단이면 이 컴퓨터의 같은 커밋 표식이 있을 때만 EGSTEP_RERUN=사유 로 처음부터.
  · 앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 <캐시> 에 남은 작업 폴더(egstep_work_* · egstep_f0_* · egstep_runner_smoke_*)는 굽기 · 연기 · F0 가
    시작할 때 열지 않고 지우고 개수만 적는다(굽기는 실행 기록 · 게시 칸 · 결과 문서 머리에 싣는다).
  · PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 · numpy 2.5.3 · scipy 1.18.1 · pandas 3.0.6. 표준출력은 경로 · sha256 앞 16자 · 초만.
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
    c = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-EGSTEP.md")))
    return ("build/" + c[0]) if len(c) == 1 else "build/PREREG-0000-00-00-EGSTEP.md", len(c)


PREREG, _N_PREREG = _find_prereg()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"
ENGINE = "build/egstep.py"
RUNNER = "build/egstep_run.py"
MANIFEST_FILE = "data/_egstep_manifest.json"
FIRST_ADDED = (PREREG, RUNNER, ENGINE, MANIFEST_FILE)
FROZEN = (ENGINE, RUNNER, MANIFEST_FILE, PREREG)
REPO_ALLOWED_EGSTEP = (MANIFEST_FILE,)
FORWARD_DIR = "data/_egstepfwd"                               # 있으면 멈춘다(전방 원장 없음 — 사용자 2026-09-27 «미래 일정 다 꺼»)
# 러너 · 뿌리가 부르는 재사용 파일(작업 트리 = 등록 커밋 판) — git blob(LF 바이트)이 이 값이어야 한다
REUSED_BLOBS = {"build/x_adapter.py": "897c4c94b22e415f38e32ac47bf8037025f28cb2",      # 배치 X 등록 판(S 층 어댑터)
                "build/dstk.py": "60e634875df6a42f191b6ce91fd391dffc721d4f",           # DSTK 등록 판(엔진)
                "build/dstk_run.py": "4bc0306e1b0aa638fa13574751d098bb9590f991"}       # DSTK 등록 판(러너 · materialize · 핀)
# 뿌리 핀(재사용 모듈의 상수와 같아야 한다 — pins_check 가 대조)
ROOT_PIN = {"code_pin": "1d81f083a404c68e23d15a649ef6f0a340d4d95c", "build_tree": "e221c9817b8baa4e225e0382ff4cf2c15fbcb8c8",
            "base": "bef4eea8c98572bd05815d44bd0744d9ce7ed370", "price": "940f0bda99ae1cc99299a43a06b30b9fa267d734"}
VROOT_PIN = "c6a35ff0168e5ea21c2ab2d18680550452511a3a"
DROOT_PIN = "44c1a26f6a8fd9f64a3a76de9334e1a37aef403b"
DROOT_TREES = {"data": "d72aec6dd1e268d66144ed8d21e05deb11950b98", "build": "fe772a6fde82d618833c9f4be0c9851d343318b1"}
VB_BOOKS_SHA = "c1aeff7df4d02c03742f224623f109e89bb6873ea8e18eaf6ff6f53862784c1b"
VB_BOOKS = os.environ.get("EGSTEP_VB_BOOKS") or os.path.join(tempfile.gettempdir(), "vbatch_cache", "f0", "vb_books.json.gz")
VD1_DIR = os.environ.get("DSTK_VD1") or os.path.join(tempfile.gettempdir(), "vbatch_cache", "raw", "vd1")
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
CHILD_ENV_DROP = ("EGSTEP_COMMIT", "EGSTEP_RERUN", "EGSTEP_SMOKE", "LAB_ASOF", "VBATCH_CACHE", "VBATCH_FRENCH_SEED", "DSTK_COMMIT", "DSTK_RERUN")
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"
SMOKE_ENV_KEYS = ("EGSTEP_SMOKE",)
TIMEOUT = 3 * 3600
# 등록 상수 — 엔진(egstep)의 값과 같아야 굽는다(등록 문서 §4 ~ §9)
REGISTERED = {
    "F_R": 0.5, "F_D": 0.5, "F_TWIN": 1.0, "STEP_CAP": 0.5, "HOLD": ("2016-09", "2026-08"), "N_HOLD": 120, "FORM_FIRST": "2016-08", "FORM_LAST": "2026-07",
    "COST": 0.0010, "COST20": 0.0020, "TURN_MAX": 10.0, "REB_SLACK": 1, "HOLM_ALPHA": 0.05, "DOWN_LAG": 3, "K_PLACEBO": 1000, "SEED": 20260927,
    "SEED_STRAT": 20260929, "N_STRAT_PROBE": 20000, "STRAT_MAX_TRIES": 200000,
    "PCT_TIMING": 95.0, "LATE_FROM": "2019-06", "NV": 30, "PRIMARY": ("R", "D", "RD"), "ROLE": {"R": "r_on", "D": "down", "RD": "down"},
    "CUT_ARMS": ("R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT"),
    "CUT_KEYS": ("r_on", "d_on", "d_and_r", "d_not_r", "r_not_d", "neither"),
    "STATE_KEYS": ("r_on", "d_on", "both", "r_only", "d_only", "neither", "r_switch", "d_switch", "r_on_runs", "d_on_runs", "t1_on", "t2_on"),
    "DIL_OF": {"R": "R_SPY", "D": "D_SPY", "RD": "RD_SPY"}, "STAT_OF": {"R": "R_STAT", "D": "D_STAT", "RD": "RD_STAT"},
    "ARMS": ("C0", "R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT", "R1", "D1", "RD1", "D_T1", "D_T2", "V_ALONE", "D_ALONE"),
    "COUNTED": ("R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT", "R1", "D1", "RD1", "D_T1", "D_T2"),
    "CUM_N_BEFORE": 1044, "N_ROWS_COUNTED": 14, "V0_FRESH_TOL": 1e-10, "V0_STORED_TOL": 5e-7 + 1e-10,
    "DSTK_EXPECT": {"THR": 0.20, "W_V": {"value": 0.70, "neutral": 0.50, "growth": 0.30}, "LAG_M": 3, "CAP": 0.25, "NMAX": 30, "EXEC_LAG": 1,
                    "HOLD": ("2016-09", "2026-08"), "FORM_WARM": "2016-07", "FORM_FIRST": "2016-08", "FORM_LAST": "2026-07",
                    "STYLE_KEYS": {"V": "val", "G": "grow"}, "MIN_NAMES": 100, "LATE_FROM": "2019-06",
                    "VD1_DIGEST": "1f552d177d0699c7aa4c9f7779e2c0c463e2f2057e3663b623b00e4adf6ffd4c"},
    "Q06_EXPECT": {"SPDR": ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"), "D0": "2006-01-04", "S0": "2009-01-02",
                   "WMIN": 756, "WMAX": 2520, "PCT": 80, "NMIN_M": 36, "M0": "2009-01"},
    "ROOT_BLOBS": {"qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "q_switch": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
                   "q_corrsurp": "d32a270e2db0682f8b940ffe647607d15b57ba52", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
                   "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2"},
    "DROOT_BLOBS": {"dstk": "60e634875df6a42f191b6ce91fd391dffc721d4f", "v_tests": "2f1ec4db1cd7458564da73ec5ad88cef8a0b2f2f",
                    "t_signals": "35e2407d8f80c81aacec5a62128dd78a73b68c0b", "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d",
                    "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628"},
    "F0_EXPECT": {'dstk_ok': True, 'dstk_valid': 121, 'r_value': 36, 'r_same_as_t17': True, 'q06_timing_ok': True, 'q06_same_as_recorded': True, 'n_forms': 120, 'r_on': 36, 'd_on': 22, 'both': 12, 'r_only': 24, 'd_only': 10, 'neither': 74, 'r_switch': 25, 'd_switch': 23, 'r_on_runs': 13, 'd_on_runs': 12, 't1_on': 35, 't2_on': 13, 'v0_hash_ok': True, 'v0_identity_ok': True, 'grid_same': True, 'n_win_dates': 2513, 'down_frozen': 35, 'down_frozen_late': 29, 'late_months': 87, 'down_pr': 39, 'd_pairing_A': True, 'd_forms': 120, 'd_names_min': 106, 'd_names_max': 130, 'd_cov_ok': 120, 'd_sel_hash16': '24f37379ab36e2f8', 'd_strat_acc': 637},
}
FORBIDDEN_ENGINE_NAMES = ("ff1", "ff2", "ff0", "forward_ledger", "genesis")    # 전방 판정 · 원장 함수가 엔진에 없어야 한다


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록 · 임시 뿌리는 모두 저장소 밖(<캐시>)
# ══════════════════════════════════════════════════════════════════════════
CACHE = os.environ.get("EGSTEP_CACHE") or os.path.join(tempfile.gettempdir(), "egstep_cache")
GIT_MARK_NAME = "egstep_started"
START_TAG = "egstep-started"
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}
OUT_NAMES = {"out": "_egstepout.json", "mark": "_egstepout.started", "runlog": "_egstepout.run.json", "public": "_egstepout.public.json"}
CACHE_ONLY_KEY = "__egstep_cache_only__"
PUBLIC_FROM = "2016-09"
PUBLIC_FLOAT_KEYS = re.compile(r"(^|_)(coverage|frac|tol|min|max|thr|sec)(_|$)")
COUNT_KEYS = re.compile(r"(^n$|^n_|_n$|count|^k$|months?$|days?$|years?$|^rows$|bytes$|names|forms)")
OUTPUT_NAME_MARKS = ("_egstepout",)
OUTPUT_CONTENT_MARKS = (CACHE_ONLY_KEY.encode(), b"_egstepout.json", b"_egstepout.public.json", b"_egstepout.run.json", b'"egstep_public_view"')


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
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith("_egstepout") and (f.endswith(".json") or f.endswith(".part"))]
    return sorted({p for p in have if os.path.exists(p)})


STALE_PREFIXES = ("egstep_work_", "egstep_f0_", "egstep_runner_smoke_")


def _stale_dirs(cache):
    if not os.path.isdir(cache):
        return []
    return sorted(os.path.join(cache, d) for d in os.listdir(cache)
                  if d.startswith(STALE_PREFIXES) and os.path.isdir(os.path.join(cache, d)))


def purge_stale(cache=None):
    """앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 <캐시> 바로 밑에 남은 작업 폴더를 열지 않고 지운다 — 개수만 돌려준다(이름 · 크기 · 값 없음).
    그 폴더에는 자식 산출(팔 월 계열 · 판정)이 있을 수 있다 — 다시 굽기 전에 누가 열어 보는 일을 막을 수는 없으므로, 지운 개수를 실행 기록 · 게시 칸 ·
    결과 문서 머리에 싣는다(등록 §10-2). 🚨 굽기 · 연기 · F0 를 동시에 돌리지 않는다(서로의 작업 폴더를 지운다)."""
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
        if f.startswith("data/_egstep") and f not in REPO_ALLOWED_EGSTEP:
            bad.append("허용 밖 파일: %s" % f)
        if f.startswith(FORWARD_DIR + "/") or f == FORWARD_DIR:
            bad.append("전방 원장 파일(사용자 2026-09-27 «미래 일정 다 꺼»): %s" % f)
        if "egstep_cache" in f:
            bad.append("캐시 사본으로 보이는 파일: %s" % f)
    return bad


def site_guard_std(root=None):
    """EGSTEP 사이트 경계 — git 이 추적 · 추가 예정인 파일 가운데 (가) 굽기 산출 이름(_egstepout*) (나) 허용 밖 data/_egstep* (다) 전방 원장 data/_egstepfwd/*
    (라) 명세(data/_egstep_manifest.json)가 해시만인가 (마) 사이트 자료(뿌리 *.html · js/*.js · data/*.json)의 굽기 산출 표식."""
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
            bad.append("사이트 자료 %s 에 EGSTEP 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


# ── 덧붙임 두 곳(.gitignore · validate_site) ─────────────────────────────
GITIGNORE_BLOCK = """
# EG30 상태 조건 스텝 역할 검정(PREREG-*-EGSTEP · 사용자 2026-09-27 «EG30 코어 + 금리 스텝 + 방어 스텝 성과 괜찮아?») — 굽기 산출(_egstepout.json ·
#   _egstepout.public.json · _egstepout.run.json · _egstepout.started)이나 캐시 사본(egstep_cache)이 작업 트리에 복사돼도 쓸려 들지 않게.
#   명세(data/_egstep_manifest.json)는 «_egstep_» 라 걸리지 않는다.
_egstepout*
egstep_cache/
"""
VALIDATE_BLOCK = """
# ── EG30 상태 조건 스텝 역할 검정(PREREG-*-EGSTEP · 사용자 2026-09-27) 사이트 경계 ─────────────────────────────
# 굽기 산출(_egstepout*)이 저장소 · 사이트 자료에 없어야 한다. data/_egstep* 는 해시만 담은 명세(_egstep_manifest) 하나뿐 ·
#   data/_egstepfwd/ 없음(전방 원장 없음 · 사용자 2026-09-27 «미래 일정 다 꺼») · 사이트 자료에 굽기 산출 표식 없음.
#   build/egstep_run.py 는 모듈 머리에서 표준 라이브러리만 불러온다(site_guard_std). 러너(egstep_run.frozen_check)도 같은 함수를 부른다.
try:
    import importlib as _il_egstep
    _egr = _il_egstep.import_module("egstep_run")
    _gge = _egr.site_guard_std(ROOT)
    if not _gge["ok"]:
        errors.append("EG30 스텝 역할 검정 사이트 경계 위반 %d건 — %s. 굽기 산출(_egstepout*)은 저장소 밖 캐시에만 둔다"
                      % (_gge.get("n_bad", len(_gge["bad"])), " · ".join(_gge["bad"][:4])))
    else:
        print("  ~ EG30 스텝 역할 검정 사이트 경계 통과(파일 %d · 사이트 자료 %d 훑음)" % (_gge["n_files"], _gge["n_scanned"]))
except Exception as _e:
    # 닫힌 쪽 — 이 경계를 확인하지 못하면 통과시키지 않는다(DSTK · GURUFUND 와 같은 규약)
    errors.append("EG30 스텝 역할 검정 사이트 경계 검사가 예외로 죽었다 — %s (확인하지 못하면 통과시키지 않는다)" % str(_e)[:80])
"""
_VALIDATE_ANCHOR = 'print("사이트 검증:"'


def wire_texts(gitignore_txt, validate_txt):
    g = gitignore_txt
    if "_egstepout*" not in g:
        g = g.rstrip("\n") + "\n" + GITIGNORE_BLOCK
    v = validate_txt
    if "EG30 상태 조건 스텝 역할 검정(PREREG-*-EGSTEP" not in v:
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
#  이름 · 등록 상수 · 재사용 blob · 핀 · 명세
# ══════════════════════════════════════════════════════════════════════════
def name_check():
    bad = []
    if _N_PREREG != 1:
        bad.append("build/PREREG-*-EGSTEP.md 가 %d 개" % _N_PREREG)
    elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-EGSTEP\.md", PREREG):
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
        import egstep as E
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


def _XA():
    import x_adapter as XA
    return XA


def _DR():
    import dstk_run as DR
    return DR


def pins_check():
    """뿌리 핀 셋 — 재사용 모듈의 상수와 같고 · 커밋이 있고 origin/main 의 조상이며 · 트리가 등록 값과 같다(git 개체만 · 자료를 열지 않는다)."""
    bad = reused_problems()
    if bad:
        return bad
    XA, DR = _XA(), _DR()
    if (XA.CODE_PIN, XA.BUILD_TREE, XA.P1_BASE, XA.P1_PRICE) != (ROOT_PIN["code_pin"], ROOT_PIN["build_tree"], ROOT_PIN["base"], ROOT_PIN["price"]):
        bad.append("x_adapter 뿌리 핀이 등록 값과 다르다")
    if XA.DATA_PIN != VROOT_PIN or XA.VB_BOOKS_SHA != VB_BOOKS_SHA:
        bad.append("x_adapter 배치 V 핀 · VB 넘김 sha 가 등록 값과 다르다")
    if DR.DATA_PIN != DROOT_PIN or dict(DR.DATA_PIN_TREES) != DROOT_TREES:
        bad.append("dstk_run 자료 핀 · 트리가 등록 값과 다르다")
    for nm, c in (("root code", ROOT_PIN["code_pin"]), ("root base", ROOT_PIN["base"]), ("root price", ROOT_PIN["price"]),
                  ("vroot", VROOT_PIN), ("droot", DROOT_PIN)):
        if _git("cat-file", "-e", c + "^{commit}").returncode != 0:
            bad.append("%s 핀 커밋 %s 가 없다" % (nm, c[:9]))
        elif _git("merge-base", "--is-ancestor", c, "origin/main").returncode != 0:
            bad.append("%s 핀 커밋 %s 가 origin/main 의 조상이 아니다" % (nm, c[:9]))
    if _git("rev-parse", "%s:build" % ROOT_PIN["code_pin"]).stdout.strip() != ROOT_PIN["build_tree"]:
        bad.append("root 코드 핀의 build 트리가 다르다")
    for spec, sha in DROOT_TREES.items():
        r = _git("rev-parse", "%s:%s" % (DROOT_PIN, spec))
        if r.returncode != 0 or r.stdout.strip() != sha:
            bad.append("droot 핀 %s:%s 가 등록 값과 다르다" % (DROOT_PIN[:9], spec))
    return bad


def ext_problems():
    """저장소 밖 입력 — V-D1 묶음 해시(얼린 dstk_run.vd1_problems · 핀 판 이름) · 배치 V F0 넘김 파일 sha(짝맞춤 A 의 기준)."""
    bad = []
    if _inside(VB_BOOKS, ROOT):
        bad.append("VB 넘김 파일이 저장소 안이다")
    elif not os.path.exists(VB_BOOKS):
        bad.append("VB 넘김 파일 없음(%s)" % os.path.basename(VB_BOOKS))
    elif _sha_file(VB_BOOKS) != VB_BOOKS_SHA:
        bad.append("VB 넘김 파일 sha256 이 등록 값과 다르다")
    try:
        bad += ["V-D1: %s" % x for x in _DR().vd1_problems()]
    except SystemExit as e:
        bad.append("V-D1 점검 실패: %s" % str(e)[:120])
    return bad


def manifest_doc():
    """data/_egstep_manifest.json — 해시만(값 없음)."""
    XA, DR = _XA(), _DR()

    def rp(c, spec):
        r = _git("rev-parse", "%s:%s" % (c, spec))
        return r.stdout.strip() if r.returncode == 0 else None
    return {"kind": "egstep_manifest", "note": "EG30 상태 조건 스텝 역할 검정(EGSTEP) 명세 — 해시만(값 없음). 러너 판 점검이 이 파일을 등록 커밋 판과 대조한다.",
            "prereg": PREREG, "engine": ENGINE, "runner": RUNNER,
            "code_sha256_lf": {p: (_sha_lf(_bytes(os.path.join(ROOT, *p.split("/")))) if os.path.exists(os.path.join(ROOT, *p.split("/"))) else None)
                               for p in (ENGINE, RUNNER)},
            "reused_blobs": dict(REUSED_BLOBS),
            "roots": {"root": {"code_pin": ROOT_PIN["code_pin"], "build_tree": ROOT_PIN["build_tree"], "base": ROOT_PIN["base"], "price": ROOT_PIN["price"],
                               "p3": dict(XA.P3), "frozen_blobs": dict(XA.ROOT_FROZEN), "engine_asserts": dict(REGISTERED["ROOT_BLOBS"]),
                               "builder": "x_adapter.build_root"},
                      "vroot": {"data_pin": VROOT_PIN, "v_frozen": dict(XA.V_FROZEN), "dbook_frozen": dict(XA.DBOOK_FROZEN), "vb_books_sha256": VB_BOOKS_SHA,
                                "builder": "x_adapter.build_vroot", "children": "x_adapter --d-child · --dbook-child · --s-cov-child"},
                      "droot": {"data_pin": DROOT_PIN, "trees": dict(DROOT_TREES), "read_files_blob": {f: rp(DROOT_PIN, f) for f in DR.DATA_PIN_FILES},
                                "engine_asserts": dict(REGISTERED["DROOT_BLOBS"]), "vd1_digest": REGISTERED["DSTK_EXPECT"]["VD1_DIGEST"],
                                "builder": "dstk_run.materialize"}},
            "start_tag": START_TAG, "git_mark": GIT_MARK_NAME, "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼»"}


def write_manifest():
    doc = manifest_doc()
    bad = manifest_problems(doc)
    if bad:
        raise SystemExit("🚨 명세가 해시만이 아니다: %s" % bad[:3])
    miss = [k for k, v in doc["roots"]["droot"]["read_files_blob"].items() if v is None]
    if miss:
        raise SystemExit("🚨 droot 핀 커밋에 없는 파일: %s" % ", ".join(miss))
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
    for k in ("reused_blobs", "roots", "prereg", "start_tag"):
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
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 EGSTEP_RERUN=사유 로 처음부터." % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 EGSTEP_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다.")
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
    """시작 태그를 민다. 이미 같은 커밋을 가리키면 EGSTEP_RERUN(산출 전 기술적 중단의 다시 굽기)일 때만 «already» — 아니면 멈춘다(동시 굽기 막기)."""
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
            raise SystemExit("🚨 origin 시작 태그가 이미 이 커밋을 가리킨다 — 다른 굽기가 시작했다(EGSTEP_RERUN 이 아니면 굽지 않는다).")
        return "already"
    if have is not None:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다." % have[:8])
    r1 = _git("tag", "-f", START_TAG, commit)
    r2 = _git("push", "--quiet", "origin", "refs/tags/%s:refs/tags/%s" % (START_TAG, START_TAG))
    if r1.returncode != 0 or r2.returncode != 0 or _remote_start_tag() != commit:
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다 — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 EGSTEP_RERUN).")
    return "pushed"


LOCK_NAME = "_egstep_bake.lock"


def _take_lock(P, commit):
    """배타 잠금(O_EXCL) — 판 점검 뒤 · 핀 뿌리 F0 전에 잡는다. 두 번째 --once 는 여기서 멈춘다(동시 굽기 막기).
    과정이 강제로 죽으면 잠금이 남는다 — 다른 굽기가 돌지 않음을 확인하고 지운 뒤 EGSTEP_RERUN=사유 로."""
    lk = os.path.join(P["dir"], LOCK_NAME)
    try:
        fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("🚨 굽기 잠금이 있다(%s) — 다른 굽기가 돌고 있다. 돌고 있지 않으면 확인 뒤 지우고 EGSTEP_RERUN=사유 로." % lk)
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
#  핀 판 임시 뿌리 셋 · 자식 과정
# ══════════════════════════════════════════════════════════════════════════
def build_roots(work):
    """뿌리 셋(저장소 밖) — root = 얼린 x_adapter.build_root · vroot = 얼린 x_adapter.build_vroot · droot = 얼린 dstk_run.materialize(DSTK 자료 핀 ·
    읽는 자료 blob 대조 · dstk.py 를 등록 판으로 넣는다). 셋 모두에 엔진(등록 커밋 판 · 작업 트리)을 build/ 에 넣는다."""
    if _inside(work, ROOT):
        raise SystemExit("🚨 임시 뿌리가 저장소 안이다.")
    t0 = time.time()
    XA, DR = _XA(), _DR()
    rr = os.path.join(work, "r")
    vr = os.path.join(work, "v")
    os.makedirs(rr, exist_ok=True)
    os.makedirs(vr, exist_ok=True)
    root, _rep = XA.build_root(rr, ROOT, force=True)
    vroot, _vrep = XA.build_vroot(vr, ROOT, force=True)
    droot = DR.materialize(os.path.join(work, "d"), DROOT_PIN, DR.pin_blobs())
    for tree in (root, vroot, droot):
        shutil.copyfile(os.path.join(ROOT, *ENGINE.split("/")), os.path.join(tree, *ENGINE.split("/")))
    return {"root": root, "vroot": vroot, "droot": droot, "sec": round(time.time() - t0, 1)}


def _child_env():
    env = dict(os.environ)
    for k in CHILD_ENV_DROP + SMOKE_ENV_KEYS:
        env.pop(k, None)
    env.update(ENV_PINS)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "MKL_NUM_THREADS": "1", "DSTK_VD1": VD1_DIR})
    return env


def _run(cmd, cwd, out_path, what, timeout=TIMEOUT):
    t = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=_child_env(), capture_output=True, timeout=timeout)
    sec = round(time.time() - t, 1)
    if r.returncode != 0 or not os.path.exists(out_path):
        tail = _scrub(r.stderr.decode("utf-8", "replace"))[-2500:]
        raise SystemExit("🚨 자식 과정(%s) 실패 — 산출을 쓰지 않았다:\n%s" % (what, tail))
    return sec


def run_egstep_child(tree, mode, job, work):
    """엔진 자식 — python -X utf8 <뿌리>/build/egstep.py --child <mode> --job <작업> --out <산출>(작업 폴더 · 캐시)."""
    jp = os.path.join(work, "job_%s.json" % mode)
    op = os.path.join(work, "out_%s.json" % mode)
    _write_json(jp, job)
    sec = _run([sys.executable, "-X", "utf8", os.path.join(tree, *ENGINE.split("/")), "--child", mode, "--job", jp, "--out", op], tree, op, mode)
    return op, sec


def run_xa_child(vroot, flag, job, work, name):
    """얼린 x_adapter 자식(vroot) — python -X utf8 <vroot>/build/x_adapter.py <flag> <작업>(작업의 "out" 에 쓴다)."""
    jp = os.path.join(work, "job_%s.json" % name)
    _write_json(jp, job)
    sec = _run([sys.executable, "-X", "utf8", os.path.join(vroot, "build", "x_adapter.py"), flag, jp], vroot, job["out"], name)
    return job["out"], sec


def preflight(work):
    """F0(핀 뿌리 셋 · 수익 없음 · 등록 F0 개수 대조) — 통과해야 표식을 쓴다. D 목표(비중 · β̂ · 짝맞춤 A — 수익 없음)는 굽기가 그대로 이어 쓴다."""
    t0 = time.time()
    R = build_roots(work)
    sec = {"roots": R["sec"]}
    p_fv, sec["f0v"] = run_egstep_child(R["droot"], "f0v", {}, work)
    p_dt, sec["d_targets"] = run_xa_child(R["vroot"], "--d-child", {"out": os.path.join(work, "d_targets.json"), "vb_books": VB_BOOKS,
                                                                    "fidelity": None, "root": R["vroot"]}, work, "d")
    p_sc, sec["s_cov"] = run_xa_child(R["vroot"], "--s-cov-child", {"out": os.path.join(work, "s_cov.json"), "d_targets": p_dt, "world": "dbook",
                                                                    "root": R["vroot"]}, work, "scov")
    p_f0, sec["f0s"] = run_egstep_child(R["root"], "f0s", {"f0v": p_fv, "d_targets": p_dt, "s_cov": p_sc,
                                                           "qbatch": os.path.join(R["droot"], "data", "_qbatch.json")}, work)
    f0 = _read_json(p_f0)
    if not f0.get("ok"):
        raise SystemExit("🚨 F0 실패 — %s (굽지 않는다)" % "; ".join(f0.get("bad") or ["?"]))
    sec["total"] = round(time.time() - t0, 1)
    return {"f0": f0, "roots": R, "d_targets": p_dt, "sec": sec}


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def frozen_check(env=None):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("EGSTEP_COMMIT")
    if not c:
        raise SystemExit("🚨 EGSTEP_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --pins · --f0 · --manifest · --precommit · --smoke 만 된다.")
    nb = name_check()
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_EGSTEP_NO_FETCH"):
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
    rerun = env.get("EGSTEP_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag() if (real or not env.get("_EGSTEP_NO_FETCH")) else env.get("_EGSTEP_REMOTE_TAG")
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
        raise SystemExit("🚨 덧붙임 두 곳이 붙지 않았다(.gitignore %s · validate_site %s) — `egstep_run.py --wire --apply` 를 등록 커밋에." % (gw, vw))
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
    if smoke and not os.path.basename(os.path.dirname(os.path.abspath(P["dir"]))).startswith("egstep_runner_smoke_"):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/egstep_runner_smoke_*/out 이 아니다.")
    if not smoke and _OVR["out"]:
        raise SystemExit("🚨 진짜 굽기에 연기 경로가 켜져 있다.")
    lk = _take_lock(P, commit)                                # 배타 잠금 — 동시 --once 는 여기서 멈춘다
    try:
        outs = _existing_outputs(P)
        if outs:
            raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다." % ", ".join(os.path.basename(o) for o in outs))
        start_guard(commit, rerun, [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)], _tag_now())
        n_stale = 0 if smoke else purge_stale()               # 진짜 굽기: 앞선 과정이 죽어 남은 작업 폴더를 열지 않고 지운다(개수만 싣는다) · 연기는 smoke() 가 먼저 지운다
        return _bake_locked(P, commit, rerun, smoke, t0, n_stale)
    finally:
        _release_lock(lk)


def _main_children(pf, work):
    """굽기 자식 넷 — 가치 다리(droot) → D 책(vroot) → S(root) → 판정(droot). 멈춤(가치 다리 · S)은 판정이 «stopped» 로 돌려준다."""
    R = pf["roots"]
    sec = {}
    p_v, sec["vleg"] = run_egstep_child(R["droot"], "vleg", {}, work)
    head = _read_json(p_v)
    if head.get("stopped"):
        return {"kind": "egstep_out", "stopped": head["stopped"]}, None, sec
    del head
    p_db, sec["d_book"] = run_xa_child(R["vroot"], "--dbook-child", {"out": os.path.join(work, "d_book.json"), "d_targets": pf["d_targets"],
                                                                     "root": R["vroot"]}, work, "dbook")
    p_s, sec["s"] = run_egstep_child(R["root"], "s", {"v_book": p_v, "d_book": p_db, "qbatch": os.path.join(R["droot"], "data", "_qbatch.json")}, work)
    p_j, sec["judge"] = run_egstep_child(R["droot"], "judge", {"s_out": p_s}, work)
    main = _read_json(p_j)
    S = _read_json(p_s)
    series = S.get("series")
    del S
    return main, series, sec


def _bake_locked(P, commit, rerun, smoke, t0, n_stale=0):
    work = tempfile.mkdtemp(prefix="egstep_work_", dir=os.path.dirname(P["dir"]) if smoke else cache_guard_std())
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
            raise SystemExit("🚨 굽기 계산 실패 — 산출을 쓰지 않았다(산출 전 기술적 중단이면 EGSTEP_RERUN=사유 로 처음부터 · 같은 얼린 코드로만):\n%s" % str(e)[-2000:])
        out = {CACHE_ONLY_KEY: True, "kind": "egstep_bake", "prereg": PREREG, "prereg_commit": commit, "smoke": smoke,
               "pins": {"root": ROOT_PIN, "vroot": VROOT_PIN, "droot": DROOT_PIN}, "f0": pf["f0"], "main": main, "series": series}
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
                  "pins": {"root": ROOT_PIN, "vroot": VROOT_PIN, "droot": DROOT_PIN}, "code_sha": code_shas(), "registration_error": err, "smoke": smoke,
                  "stale_deleted": int(n_stale),
                  "note": "값 없음 — 결과는 _egstepout.public.json 의 칸만 결과 문서로 옮긴다(등록 §9 공개 규칙)"}
        _write_text(P["runlog"], json.dumps(runlog, ensure_ascii=False, indent=1) + "\n")
        _mark_finished(P, sha)
        if not smoke:
            print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)" % (P["out"], sha[:16], runlog["sec"]))
        return runlog
    finally:
        shutil.rmtree(work, ignore_errors=True)


def once():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("EGSTEP_RERUN"))


# ══════════════════════════════════════════════════════════════════════════
#  게시 칸(10년 창 · 전부 공개 창 안)
# ══════════════════════════════════════════════════════════════════════════
PUB_METRIC_KEYS = ("n", "ann_ex", "te", "ir", "t_iid", "nw_t", "win", "years", "years_won", "n_years", "down_n", "down_mean", "down_win", "up_mean",
                   "down_capture", "up_capture", "sleeve_beta", "episodes", "crash_won", "surge_won", "mech", "roll12", "halves", "blocks")
PUB_DELTA_KEYS = ("n", "n_down", "down_mean", "down_t", "p", "up_mean", "all_mean_ann", "all_nw_t", "win", "all20_mean_ann", "down20_mean",
                  "crash_m_mean", "surge_m_mean", "years", "episodes")
F0_PUB_KEYS = ("ok", "bad", "dstk", "q06_dry", "q06_same_as_recorded", "states", "r_codes", "strat", "v0_identity", "grid", "down", "d_book", "expect_diff")


def _pick(d, keys):
    return {k: d.get(k) for k in keys if k in (d or {})}


def public_doc(out, sha=None, nbytes=None, rec=None):
    """게시 칸 — 결과 문서가 옮길 수 있는 칸만(10년 창 값 · F0 개수 · 날짜 · 참/거짓). public_safe_std 를 통과해야 쓴다(계열 · 몫 배열은 싣지 않는다)."""
    rec = rec or {}
    f0, M = out.get("f0") or {}, out.get("main") or {}
    pv = {"egstep_public_view": True, "prereg": out.get("prereg"), "prereg_commit": rec.get("commit"), "out_sha256": sha, "out_bytes": nbytes,
          "smoke": bool(rec.get("smoke")), "registration_error": list(rec.get("registration_error") or []),
          "stale_deleted": int(rec.get("stale_deleted") or 0),
          "stopped": M.get("stopped"), "pins": out.get("pins"), "f0": _pick(f0, F0_PUB_KEYS),
          "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼» (전방 원장 · 날짜가 박힌 미래 판정 없음)"}
    if not M.get("stopped"):
        arms = {}
        for k, v in (M.get("arms") or {}).items():
            arms[k] = {"m": _pick(v.get("m") or {}, PUB_METRIC_KEYS), "m20": v.get("m20"), "down_frozen": v.get("down_frozen"),
                       "turn": v.get("turn"), "cost_drag": v.get("cost_drag")}
        pv.update({"window": M.get("window"), "n_hold": M.get("n_hold"), "states": M.get("states"), "down": M.get("down"), "arms": arms,
                   "delta": {k: _pick(v, PUB_DELTA_KEYS) for k, v in (M.get("delta") or {}).items()}, "primary": M.get("primary"),
                   "family": M.get("family"), "gates": M.get("gates"), "adopt": M.get("adopt"), "verdict": M.get("verdict"),
                   "readings": M.get("readings"), "reading_flags": M.get("reading_flags"), "cuts": M.get("cuts"), "dil": M.get("dil"),
                   "placebo": M.get("placebo"), "late": M.get("late"), "pairing": M.get("pairing"),
                   "mean_share": M.get("mean_share"), "predictions": M.get("predictions"), "multiplicity": M.get("multiplicity"), "refs": M.get("refs")})
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
ARM_KO = {"C0": "C0 · EG30 V0(코어 · 기준)", "R": "R · 금리 스텝 → 가치 다리 V30 · ½", "D": "D · 방어 스텝(Q06) → V02 책 D · ½",
          "RD": "RD · 두 스텝(방어 먼저 · 스텝 몫 합 ≤ ½)", "R_SPY": "R→SPY · 지수 레버 대조", "D_SPY": "D→SPY · 지수 레버 대조", "RD_SPY": "RD→SPY · 지수 레버 대조",
          "R_STAT": "R 정적 혼합(같은 평균 몫)", "D_STAT": "D 정적 혼합(같은 평균 몫)", "RD_STAT": "RD 정적 혼합(같은 평균 몫)",
          "R1": "R 1.0 쌍둥이", "D1": "D 1.0 쌍둥이", "RD1": "RD 1.0 쌍둥이(겹친 달 D 먼저)", "D_T1": "D 쌍둥이 T1(HighMS 만)",
          "D_T2": "D 쌍둥이 T2(HighMS ∧ CS ≤ 1)", "V_ALONE": "참고 · V30 홀로", "D_ALONE": "참고 · D 홀로"}
ARM_ORDER = ("C0", "R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT", "R1", "D1", "RD1", "D_T1", "D_T2", "V_ALONE", "D_ALONE")
ARM_SHORT = {"C0": "C0", "R": "R", "D": "D", "RD": "RD", "R_SPY": "R→SPY", "D_SPY": "D→SPY", "RD_SPY": "RD→SPY", "R_STAT": "R 정적", "D_STAT": "D 정적",
             "RD_STAT": "RD 정적", "R1": "R1", "D1": "D1", "RD1": "RD1", "D_T1": "D-T1", "D_T2": "D-T2", "V_ALONE": "V30 홀로", "D_ALONE": "D 홀로"}
CUT_KO = {"r_on": "R 켜짐", "d_on": "D 켜짐", "d_and_r": "D∧R", "d_not_r": "D∧¬R", "r_not_d": "R∧¬D", "neither": "둘 다 꺼짐"}
STAT_KO = {"r_on": "R 켜진 달 Δ_R", "down": "얼린 하락월 Δ_down"}       # 확증 통계(팔마다 제 역할 · 등록 §6-1)
PRED_KO = {"P1_no_rejection": "P1 Holm 기각 0/3", "P2_no_adoption": "P2 채택 표시 0",
           "P3_d_small": "P3 D 팔 |전 월 Δ| < 0.15%p/년(10bp)", "P4_d_placebo_lt95": "P4 D 위약 백분위(하락월 Δ) < 95",
           "P5_r_beats_spy_down": "P5 R 의 Δ_down > R→SPY 의 Δ_down(가치 다리가 같은 달 지수 바구니보다 하락월에 낫다)",
           "P6_r_step_gt_static": "P6 R 의 전 월 Δ > R 정적 혼합의 전 월 Δ(국면 시점이 바구니보다 보탠다)",
           "P7_rd_rebounds_ok": "P7 RD 반등 다리 이긴 수 ≥ C0 − 1",
           "P8_d_rmatched_lt95": "P8 D 의 R 겹침 맞춘 위약 백분위(하락월 Δ) < 95",
           "P9_r_rate_role": "P9 R 의 Δ_R(R 켜진 달) > 0 · > 같은 달 R→SPY 의 Δ_R(점 추정 · 첫 판의 금리 역할 읽기와 같은 조건)"}
A30_FROZEN = ("DSTK A30(PREREG-2026-09-27-DSTK-RESULT §1 · §2 · 같은 펀드 틀 · 10bp · T+1 · 금리 틸트 가치 · 성장 상위 30 시총가중 25%): 연 초과 +0.59%p · "
              "IR 0.68 · NW t 2.14 · 해마다 5/9(완전 연도 2017 ~ 2025 · DSTK 규약 — 이 문서의 다른 줄은 부분 연도 2016 · 2026 을 넣은 11해) · "
              "하락월(PR) −0.024 · 얼린 35 −0.029 · 급락 다리 4/8 · 반등 4/8 · 슬리브 β 1.18 · 회전 3.30 · "
              "Holm 기각 참 · 무해 거짓(하락월 20bp −0.034) · 채택 표시 거짓 — EGSTEP 의 V30 은 그 줄의 가치 다리 하나만이다(성장 다리 · 틸트 없음)")
D_BOOK_NOTE = ("D = 배치 X 의 D 책(얼린 V02 선정 — GICS 섹터마다 FP β̂ 하위 20% · 섹터 이름 수는 섹터 시총 몫에 비례 · 시총가중 · 이름당 20% 상한 · "
               "섹터 띠 · 능동 상한 · θ 섞기 없음 — 선정만 섹터 안이고 섹터 비중은 중립이 아니다). VBATCH 결과 문서의 V02 줄(급락 다리 8/8 · 반등 4/8)은 "
               "S 층 W 책(벤치마크 섞기 · 섹터 띠)의 모양이라 이 D 의 모양이 아니다 — 이 D 의 단독 모양은 §3 의 «참고 · D 홀로» 줄이다.")
IDX_NOTE = ("지수 레버선(d1 · d2)은 같은 달 · 같은 크기를 지수 바구니로 옮긴 것과의 비교다(배치 X 의 IDX 레버 꼴 · 오케스트레이터가 «희석 대조» 라 부른 것) — "
            "d1 은 팔마다 확증 통계로 잰다(R: R 켜진 달 Δ_R · D · RD: 얼린 하락월 Δ_down). 목적지를 재지 방아쇠 시점을 재지 않는다(β 가 낮은 D 는 하락월에 구조적으로 유리하다). "
            "시점은 위약 읽기가, 같은 초과 희석(배치 X 의 «희석선»)은 효율 읽기가 본다(§1-2 · §6).")
R_ROLE_NOTE = ("R 의 확증 통계는 제 역할의 통계다 — R 켜진 보유월(가치 국면 36)의 (R − C0) 평균 Δ_R · t(35) 이고, d1 도 같은 달 R→SPY 의 Δ_R 과 견준다"
               "(오케스트레이터 결정 · 계산 전 · 첫 판의 금리 역할 읽기가 이 관문이 됐다). R 의 비기각은 «R 이 실패했다» 가 아니고, "
               "2022 · 금리형 급락 구간의 이득은 설계 전에 본 해(DSTK A30 2022 +1.19 대 EG30 −0.57)라 확인이 아니다 — 실질금리가 급등한 2022 의 달이 "
               "R 켜진 달에 들면 R 의 기각 · 표시도 그 이미 본 해에 기댄다. R 의 하락월 Δ 는 §2 에 보고만 한다(사용자 첫 원칙 · 예측 P5 · 판정 아님).")
OVERLAP_NOTE = ("R 과 D 는 독립이 아니다 — D 켜진 달 22 가운데 12 가 R 켜진 달이다(독립이면 약 6.6 · F0). RD 는 스텝 몫 합을 ½ 로 묶고 방어를 먼저 둔다"
                "(오케스트레이터 결정 · 계산 전): 그 12달 RD 슬리브는 EG30 ½ · D ½(V30 없음) · R 만 켜진 24달은 EG30 ½ · V30 ½ · D 만 켜진 10달은 EG30 ½ · D ½ — "
                "EG30 코어는 늘 ½ 이상이고 RD 안의 금리 스텝은 R∧¬D 24달에만 켜진다. "
                "D 의 몫 가운데 금리 상태의 몫은 §5 의 D∧R · D∧¬R 자르기와 §4 의 R 겹침 맞춘 위약이 가른다.")


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


def _pcts(ps):
    return " · ".join(_fmt(p, 1) for p in (ps or [])) or "—"


def _read_cells(a, r):
    """§1-2 읽기 칸(계산 전 고정 · 표시를 바꾸지 않는다 · 읽기 다섯 · 팔의 확증 통계로)."""
    b = r.get("static_basket")
    basket = "—" if b is None else ("**정적 혼합 몫 — 상태 스텝 증거 아님**" if b else "스텝이 정적 혼합보다 낫다")
    timing = ("**시점 증거 약함**(%s)" if r.get("timing_weak") else "위약 ≥ 95 백분위(%s)") % _pcts(r.get("placebo_pct"))
    tr = r.get("timing_weak_r")
    timing_r = "—" if tr is None else (("**R 겹침과 가려지지 않는다**(%s)" if tr else "R 겹침 맞춘 위약 ≥ 95(%s)") % _pcts([r.get("placebo_pct_r")]))
    sl = r.get("steady_lost")
    steady = "—" if sl is None else (("**꾸준함 내줌**(%s/%s)" if sl else "내주지 않음(%s/%s)") % (r.get("years_won"), r.get("years_won_c0")))
    ew = r.get("eff_weak")
    eff = "—" if ew is None else (("**희석선 밑**(희석 %s · 팔 %s)" if ew else "희석선 위(희석 %s · 팔 %s)") % (_fmt(r.get("eff_dil"), 4), _fmt(r.get("eff_arm"), 4)))
    return basket, timing, timing_r, steady, eff


def result_doc(pub, reg_err=None):
    """결과 문서 본문(Markdown) — 게시 칸 파일(_egstepout.public.json) 하나만 읽는다(손으로 옮기지 않는다)."""
    if not pub or not pub.get("egstep_public_view"):
        raise SystemExit("🚨 게시 칸 파일이 아니다")
    stopped = pub.get("stopped")
    fam = pub.get("family") or {}
    rej = fam.get("reject") or {}
    adopt = pub.get("adopt") or {}
    n_rej, n_ad = sum(1 for v in rej.values() if v), sum(1 for v in adopt.values() if v)
    verdict = pub.get("verdict") or ("보류" if stopped else "—")
    title = ("# 결과 — EG30 상태 조건 스텝 역할 검정(EGSTEP · C0 EG30 V0 + 금리 스텝 R(D13 가치 국면 → 가치 다리 V30) + 방어 스텝 D(Q06 상관 놀람 → V02 책 D) · "
             "스텝 ½ · 몫 합 ≤ ½ · 팔마다 제 역할의 통계): 한 번 굽기 · %s · **%s**"
             % ("멈춤(등록된 멈춤 조건)" if stopped else "Holm 기각 %d/3 · 채택 표시 %d" % (n_rej, n_ad), verdict))
    re_lines, re_sha = (reg_err or ([], None))
    reg_all = list(pub.get("registration_error") or []) + list(re_lines)
    mult = pub.get("multiplicity") or {}
    pins = pub.get("pins") or {}
    L = [title, "",
         "풀카드: 없음   <!-- 랩이 스스로 짠 EG30 운용 스텝 조합이다 · 금리 스텝은 D13 규칙을 그대로 쓰지만 D13 카드의 판정은 DSTK 결과 문서가 적는다 · build/pool_lab.py 가 이 줄을 읽는다 -->",
         "판정: %s   <!-- 확증 가족 R · D · RD(팔마다 제 역할의 통계 — R: R 켜진 달 Δ_R · D · RD: 하락월 Δ · 한쪽 Holm α 0.05) · 채택 표시 = 기각 ∧ 무해 ∧ 지수 레버선 · 표시가 있으면 «보류»(펀드에 붙이기는 사용자 결정) · 기각은 있고 표시가 없으면 «측정만» · 기각 0 이면 «기각» -->" % verdict,
         "규칙: 없음   <!-- 랩 게시 sid 가 아니다 · 운용 · 사이트 규칙 변경 없음 -->", "",
         "아래는 얼린 렌더러(`python -X utf8 build/egstep_run.py --result-doc`)가 게시 칸 파일(`_egstepout.public.json`) 하나에서 만든 것이다.", "",
         "## 머리", "",
         "- 등록 커밋 `%s` · 산출 sha256 `%s` · 뿌리 핀 root `%s` · vroot `%s` · droot `%s`" % (
             pub.get("prereg_commit"), (pub.get("out_sha256") or "—")[:16], ((pins.get("root") or {}).get("code_pin") or "")[:9],
             (pins.get("vroot") or "")[:9], (pins.get("droot") or "")[:9]),
         "- 멈춤: %s · 등록 오류: %s%s" % (stopped or "없음", "; ".join(reg_all) or "없음",
                                       (" (굽기 뒤 손으로 적은 등록 오류 파일 sha256 `%s` · 값이 아니라 글과 얼린 코드의 어긋남)" % re_sha) if re_sha else ""),
         "- 앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 남은 작업 폴더: %s (굽기 시작 때 열지 않고 지웠다 · 등록 §10-2)" % int(pub.get("stale_deleted") or 0),
         "- 창(보유월): %s · %s개월 · 펀드 F = 0.9 × SPY TR + 0.1 × 슬리브 대 SPY TR · 편도 10bp(20bp 판) · 월말 결정 · 스텝 몫 교체 T+1 · 각 장부 자기 되맞춤은 등록 그대로" % (
             "~".join(pub.get("window") or ["—"]), pub.get("n_hold") or "—"),
         "- 다중성: 확증 가족 m = %s(α %s · 한쪽 · R: R 켜진 달 Δ_R · D · RD: 하락월 Δ_down) · 누적 N %s → %s(센 줄 %s · 기저 = 배치마다 갈린 계수기의 증분을 모두 더한 보수적 맥락 합 · 등록 §9)" % (
             mult.get("m_confirmatory"), mult.get("alpha"), mult.get("cum_n_before"), mult.get("cum_n_after"), mult.get("rows_counted")),
         "- 전방: %s" % pub.get("forward"), ""]
    f0 = pub.get("f0") or {}
    st = f0.get("states") or {}
    dk = f0.get("d_book") or {}
    ds = f0.get("dstk") or {}
    vi = f0.get("v0_identity") or {}
    dn = f0.get("down") or {}
    sp = f0.get("strat") or {}
    L += ["## F0 관문(수익 없음 · 등록 개수 대조)", "",
          "| 관문 | 값 |", "|---|---|",
          "| F0 전체 | %s · 어긋남 %s |" % (_fmt(f0.get("ok")), "; ".join(f0.get("bad") or []) or "없음"),
          "| DSTK 핀 판 F0(얼린 dstk.f0_child · 등록 서명) · 결정 · 다리 채움 | %s · %s/%s |" % (_fmt(ds.get("dstk_ok")), (ds.get("dstk_forms") or {}).get("n_valid"),
                                                                                 (ds.get("dstk_forms") or {}).get("n")),
          "| 금리 국면(보유 120 결정) 가치 · 중립 · 성장 · 전환 · T17 함수와 같음 | %s · %s · %s · %s · %s |" % (
              (ds.get("dstk_regime") or {}).get("value"), (ds.get("dstk_regime") or {}).get("neutral"), (ds.get("dstk_regime") or {}).get("growth"),
              (ds.get("dstk_regime") or {}).get("switches"), _fmt((ds.get("dstk_regime") or {}).get("same_as_t17"))),
          "| Q06 시점(결정 달의 MonthMS · CS 가 그달 마지막 거래일 종가에서 닫힌다 · 얼린 dry 단언) · 배치 Q 기록 신호 달과 같음 | %s · %s |" % (
              _fmt((f0.get("q06_dry") or {}).get("ok")), _fmt(f0.get("q06_same_as_recorded"))),
          "| 상태 달: R 켜짐 · D 켜짐 · 둘 다 · R 만 · D 만 · 둘 다 아님 | %s · %s · %s · %s · %s · %s |" % (st.get("r_on"), st.get("d_on"), st.get("both"),
                                                                                     st.get("r_only"), st.get("d_only"), st.get("neither")),
          "| 교체 수 R · D · 켜진 구간 수 R · D · Q06 쌍둥이 T1 · T2 켜짐 | %s · %s · %s · %s · %s · %s |" % (st.get("r_switch"), st.get("d_switch"),
                                                                                       st.get("r_on_runs"), st.get("d_on_runs"), st.get("t1_on"), st.get("t2_on")),
          "| R 겹침 맞춘 D 위약(상태 개수만): 참 겹침 · 첫 뽑기 수 가운데 받아들인 수 | %s · %s/%s |" % (sp.get("overlap"), sp.get("accepted"), sp.get("probe")),
          "| C0 = 얼린 V0(목표 해시 · 몫 ≡ 1 경로 대 새로 지은 Ctx.V0() 최대 절대 차 ≤ 1e−10 · 대 data/_qbatch.json V0.ex(소수 여섯째 자리 저장) ≤ ½·10⁻⁶) | %s · %s · %s · %s |" % (
              _fmt(vi.get("hash_ok")), _fmt(vi.get("ok")), ("%.1e" % vi["fresh_max_abs_diff"]) if isinstance(vi.get("fresh_max_abs_diff"), float) else "—",
              ("%.1e" % vi["max_abs_diff"]) if isinstance(vi.get("max_abs_diff"), float) else "—"),
          "| 뿌리 창 거래일 = DSTK 핀 판 창 거래일 · 거래일 수 | %s · %s |" % (_fmt((f0.get("grid") or {}).get("same_as_droot")), (f0.get("grid") or {}).get("n_win_dates")),
          "| D 목표 짝맞춤 A(배치 V F0 넘김) · 목표 선 결정 · 이름 수 최소 · 최대 · 옮긴 몫 ≥ 0.90 인 달 · 선정 해시 | %s · %s · %s · %s · %s/%s · `%s` |" % (
              _fmt(dk.get("pairing_A")), dk.get("n_forms_with_target"), dk.get("names_min"), dk.get("names_max"), dk.get("cov_ok_months"), dk.get("cov_months"),
              dk.get("sel_hash16")),
          "| 얼린 하락월(SPY TR < 0 확인) · 부분 창 안 · 하락월(PR < 0) | %s(%s) · %s · %s |" % (dn.get("n_frozen"), _fmt(dn.get("frozen_eq_spytr")), dn.get("n_frozen_late"),
                                                                              dn.get("n_pr")), ""]
    if stopped:
        L += ["## 멈춤", "", "- 굽기가 멈췄다(%s) — 산출은 멈춤 기록이다. 다시 굽기는 새 등록." % stopped, ""]
        return "\n".join(L) + "\n"
    arms, delta, gates = pub.get("arms") or {}, pub.get("delta") or {}, pub.get("gates") or {}
    thr = fam.get("threshold") or {}
    rd = pub.get("readings") or {}
    flags = pub.get("reading_flags") or {}
    dil = pub.get("dil") or {}
    prim = pub.get("primary") or {}
    L += ["## 1. 확증 가족 · Holm · 무해 · 지수 레버선 · 채택 표시(한쪽 · H1 확증 통계 > 0 · 팔마다 제 역할 — R: R 켜진 달 Δ_R · D · RD: 얼린 하락월 Δ_down)", "",
          "| 팔 | 확증 통계(가면 · 달 수 · t 자유도) | 평균(%p/월) | 달력 NW(3) t | 한쪽 p | Holm 문턱 | 기각 | 20bp 전 월 Δ ≥ 0 | 반등 ≥ C0 − 1(팔/C0 이긴 수) | 회전 ≤ 10 | 무해 | 지수 레버의 같은 통계 | 통계 > 지수 레버(d1) | 지수 레버 20bp 전 월 Δ | 20bp 전 월 Δ ≥ 지수 레버(d2) | **채택 표시** |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in ("R", "D", "RD"):
        pa, g = prim.get(a) or {}, gates.get(a) or {}
        hm, dl = g.get("harmless") or {}, g.get("dilution") or {}
        c = hm.get("conds") or {}
        n = pa.get("n")
        L.append("| %s | %s · %s달 · t(%s) | %s | %s | %s | %s | %s | %s(%s) | %s(%s/%s) | %s(%s) | %s | %s | %s | %s | %s | **%s** |" % (
            ARM_KO[a], STAT_KO.get(pa.get("stat"), "—"), n, (n - 1) if isinstance(n, int) else "—", _fmt(pa.get("mean"), 4), _fmt(pa.get("t")),
            _fmt((fam.get("p") or {}).get(a), 4), _fmt(thr.get(a), 4), _fmt(rej.get(a)),
            _fmt(c.get("all20_ge0")), _fmt(hm.get("all20_mean_ann"), 3), _fmt(c.get("rebounds_ok")), hm.get("rebounds_win"), hm.get("rebounds_c0"),
            _fmt(c.get("turn_le10")), _fmt(hm.get("turn")), _fmt(hm.get("harmless")), _fmt(dl.get("dil_prim_mean"), 4), _fmt(dl.get("prim_gt_dil")),
            _fmt(dl.get("dil_all20_mean_ann"), 3), _fmt(dl.get("all20_ge_dil")), _fmt(adopt.get(a))))
    L += ["", "- 채택 표시는 «펀드 슬리브 스텝 후보» 라는 뜻뿐이다 — 펀드에 붙이는 것은 사용자 결정이고 날짜가 박힌 일정은 없다(등록 §6).",
          "- 확증 통계는 팔마다 제 역할이다(오케스트레이터 결정 · 계산 전): R 은 R 켜진 보유월(가치 국면)의 (R − C0) 평균 · D · RD 는 얼린 하락월 35 의 평균 · "
          "달력 t = 얼린 eg30plus.down_t 를 그 가면으로(Bartlett 3) · p = t(가면 달 수 − 1) 위 꼬리 · 무해 셋은 셋 모두 같다.",
          "- %s" % IDX_NOTE, "- %s" % R_ROLE_NOTE, "- %s" % OVERLAP_NOTE, "",
          "### 1-2. 읽기(계산 전 고정 · 표시를 바꾸지 않는다 · 읽기 다섯 · 팔의 확증 통계로 · 등록 §6-6)", "",
          "| 팔 | 바구니(정적 혼합 — D · RD 는 두 Δ 모두 · R 은 전 월 Δ 가 이상) | 시점(위약 백분위 · R 은 Δ_R) | R 겹침 시점(맞춘 위약 백분위) | 꾸준함(해마다 이긴 수 팔/C0) | 효율(같은 초과 희석의 같은 통계 대 팔) | 표시에 붙는 읽기 |",
          "|---|---|---|---|---|---|---|"]
    for a in ("R", "D", "RD"):
        cells = _read_cells(a, rd.get(a) or {})
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % ((ARM_KO[a],) + cells + (" · ".join(flags.get(a) or []) or "없음",)))
    L += [""]
    for a in ("R", "D", "RD"):
        if adopt.get(a):
            fl = flags.get(a) or []
            L.append(("- **%s 의 채택 표시에 읽기(%s)가 붙었다 — 이 표시를 «스텝이 약점을 고쳤다» 로 읽지 않는다(등록 §6-6).**" % (ARM_KO[a], " · ".join(fl))) if fl
                     else "- %s 의 채택 표시에 붙은 읽기는 없다 — 그래도 표본 안 · 오염된 측정이다(등록 §0)." % ARM_KO[a])
    L += ["- 읽기 뜻: 바구니 = 같은 평균 몫을 늘 옮긴 정적 혼합이 D · RD 는 전 월 Δ 와 Δ_down 둘 다, R 은 전 월 Δ 가 스텝 이상(R 의 Δ_R 은 켜진 달에 ½ 을 모으는 스텝 쪽으로 "
          "구성상 기울어 바구니와 시점을 가르지 못한다) · 시점 = 그 상태의 구간 섞기 위약 백분위 < 95(R 은 Δ_R — 뽑기마다 그 뽑기의 켜진 달 평균 · D 는 Δ_down · "
          "RD 는 R · D 위약의 Δ_down 가운데 하나라도) · R 겹침 시점 = R 과의 겹침까지 맞춘 D 위약 < 95(또는 뽑기가 K 에 못 닿음) · 꾸준함 = 해마다 이긴 수가 C0 보다 적다 · "
          "효율 = 확증 통계가 같은 초과 희석의 같은 통계보다 크지 않다. 첫 판의 금리 역할 읽기는 R 의 확증 통계 · d1 이 됐다(§1).", ""]
    L += ["## 2. 팔 − C0(월 펀드 초과 차 · 10bp · 모든 팔)", "",
          "| 팔 | 전 월 Δ(%p/년) | NW t | 월 승률(%) | Δ_down(%p/월) | 달력 t | 상승월 Δ | 20bp 전 월 Δ | CRASH-M Δ | SURGE-M Δ | 2022 Δ(%p) | 평균 몫(E · V · D · S) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    ms = pub.get("mean_share") or {}
    for a in ARM_ORDER:
        if a == "C0" or a not in delta:
            continue
        d = delta[a]
        sh = ms.get(a) or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            ARM_KO[a], _fmt(d.get("all_mean_ann"), 3), _fmt(d.get("all_nw_t")), _fmt(d.get("win"), 1), _fmt(d.get("down_mean"), 4), _fmt(d.get("down_t")),
            _fmt(d.get("up_mean"), 4), _fmt(d.get("all20_mean_ann"), 3), _fmt(d.get("crash_m_mean"), 3), _fmt(d.get("surge_m_mean"), 3),
            _fmt((d.get("years") or {}).get("2022")), " · ".join(_fmt(sh.get(k), 3) for k in ("E", "V", "D", "S"))))
    L += ["", "- Δ_down = 얼린 하락월 35(data/mech_episodes.json down_m · SPY TR < 0) 평균 · 달력 t = 얼린 eg30plus.down_t(Bartlett 3 · n_d/(n_d − 1)) · CRASH-M · SURGE-M = 얼린 mech_episodes 달. "
          "R 가족(R · R→SPY · R 정적)의 확증 통계는 §1 의 Δ_R(R 켜진 달)이다 — 이 표의 R 가족 Δ_down 은 보고 칸이다(사용자 첫 원칙 · 예측 P5).", ""]
    L += ["## 3. 펀드 틀 — 모든 팔 대 SPY TR(10년 · 편도 10bp)", "",
          "| 팔 | 연 초과(%p) | TE | IR | NW t | 월 승률(%) | 해마다 승 | 12개월 굴림 승률(%) | 두 반(연 %p) | 하락월(PR) 평균 | 하락월(얼린 35) 평균 | 급락 다리 | 반등 다리 | 이름 붙은 급락 · 급등 승 | 슬리브 β | 편도 회전/년 | 비용 끌림(%/년) | 20bp 연 초과 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in ARM_ORDER:
        v = arms.get(a) or {}
        m = v.get("m") or {}
        hv = m.get("halves") or [None, None]
        L.append("| %s | %s | %s | %s | %s | %s | %s/%s | %s | %s · %s | %s | %s | %s | %s | %s · %s | %s | %s | %s | %s |" % (
            ARM_KO[a], _fmt(m.get("ann_ex")), _fmt(m.get("te")), _fmt(m.get("ir")), _fmt(m.get("nw_t")), _fmt(m.get("win"), 1), m.get("years_won"), m.get("n_years"),
            _fmt((m.get("roll12") or {}).get("hit"), 0), _fmt(hv[0] if len(hv) > 0 else None), _fmt(hv[1] if len(hv) > 1 else None),
            _fmt(m.get("down_mean"), 3), _fmt((v.get("down_frozen") or {}).get("mean"), 3), _mech(m, "crash_legs"), _mech(m, "rebounds"),
            m.get("crash_won"), m.get("surge_won"), _fmt(m.get("sleeve_beta")), _fmt(v.get("turn")), _fmt(v.get("cost_drag")), _fmt((v.get("m20") or {}).get("ann_ex"))))
    L += [""]
    pl = pub.get("placebo") or {}
    L += ["## 4. 위약 — 상태의 구간 섞기(켜진 달 수 · 교체 수 보존 · 같은 크기 · 같은 목적지)", "",
          "| 상태 | 뽑기 · 씨앗 | 참 Δ_down | 백분위(뽑기 < 참) | 뽑기 Δ_down p05 · p50 · p95 | 참 전 월 Δ | 백분위 | 뽑기 전 월 Δ p05 · p50 · p95 |", "|---|---|---|---|---|---|---|---|"]
    for nm, ko in (("D", "D(Q06) → V02 책 D"), ("R", "R(D13 가치 국면) → V30"), ("D_R", "D(Q06) · R 겹침 맞춤")):
        p = pl.get(nm) or {}
        dq, aq = p.get("down_q") or {}, p.get("all_q") or {}
        if nm == "D_R":
            ko = "%s(참 겹침 %s · 뽑기 %s 가운데 받음 %s/%s)" % (ko, p.get("overlap"), p.get("tries"), p.get("k"), p.get("k_target"))
        L.append("| %s | %s · %s | %s | %s | %s · %s · %s | %s | %s | %s · %s · %s |" % (
            ko, p.get("k"), p.get("seed"), _fmt(p.get("true_down"), 4), _fmt(p.get("pct_down"), 1), _fmt(dq.get("p05"), 4), _fmt(dq.get("p50"), 4), _fmt(dq.get("p95"), 4),
            _fmt(p.get("true_all"), 3), _fmt(p.get("pct_all"), 1), _fmt(aq.get("p05"), 3), _fmt(aq.get("p50"), 3), _fmt(aq.get("p95"), 3)))
    prr = pl.get("R") or {}
    rq = prr.get("role_q") or {}
    L += ["", "- R 겹침 맞춤 = 같은 구간 섞기 뽑기 가운데 R 켜진 달과의 겹침이 참과 같은 것만 받는다(켜진 달 수 · 교체 수 · R 겹침 보존) — D 의 시점이 금리 상태 겹침 너머를 보태는지 본다.", "",
          "R 의 확증 통계 위약(같은 R 뽑기 · 뽑기마다 그 뽑기의 켜진 달 평균 Δ_R · 읽기 ② 의 R):", "",
          "| 상태 | 뽑기 · 씨앗 | 참 Δ_R | 백분위(뽑기 < 참) | 뽑기 Δ_R p05 · p50 · p95 |", "|---|---|---|---|---|",
          "| R(D13 가치 국면) → V30 | %s · %s | %s | %s | %s · %s · %s |" % (
              prr.get("k"), prr.get("seed"), _fmt(prr.get("true_role"), 4), _fmt(prr.get("pct_role"), 1), _fmt(rq.get("p05"), 4), _fmt(rq.get("p50"), 4),
              _fmt(rq.get("p95"), 4)), ""]
    cuts = pub.get("cuts") or {}
    if cuts:
        ck = [k for k in ("r_on", "d_on", "d_and_r", "d_not_r", "r_not_d", "neither")]
        first = next(iter(cuts.values()))
        head = " | ".join("%s(%s)" % (CUT_KO[k], (first.get(k) or {}).get("n")) for k in ck)
        L += ["## 5. 상태별 자르기(팔 − C0 월 펀드 초과 차 · 10bp · %p/월 · 보고만 · 판정 아님)", "",
              "전 월 평균(달력 HAC t):", "", "| 팔 | " + head + " |", "|---|" + "---|" * len(ck)]
        for a in [x for x in ARM_ORDER if x in cuts]:
            L.append("| %s | %s |" % (ARM_KO[a], " | ".join("%s (%s)" % (_fmt((cuts[a].get(k) or {}).get("mean"), 4), _fmt((cuts[a].get(k) or {}).get("t")))
                                                          for k in ck)))
        L += ["", "그 가운데 얼린 하락월 평균(하락월 수):", "", "| 팔 | " + " | ".join(CUT_KO[k] for k in ck) + " |", "|---|" + "---|" * len(ck)]
        for a in [x for x in ARM_ORDER if x in cuts]:
            L.append("| %s | %s |" % (ARM_KO[a], " | ".join("%s (%s)" % (_fmt((cuts[a].get(k) or {}).get("down_mean"), 4), (cuts[a].get(k) or {}).get("n_down"))
                                                          for k in ck)))
        L += ["", "- 상태는 결정 달 m 의 것이고 보유월 m+1 에 붙는다 · 달력 t = 얼린 eg30plus.down_t 를 그 가면으로(5달 미만이면 없음) · "
              "R 줄 · R→SPY 줄의 «R 켜짐» 칸은 R 의 확증 통계 Δ_R · d1 과 같은 값이다(판정은 §1).", ""]
    if dil:
        L += ["## 6. 같은 초과 희석(배치 X 의 DIL 규칙 · 보고 · 효율 읽기 · 표시 조건 아님)", "",
              "| 팔 | 팔 전 월 Δ e(%p/년) | c(EG30 몫 · 나머지 SPY) | 희석 전 월 Δ(%p/년) | 희석 20bp 전 월 Δ | 희석 Δ_down | 확증 통계(가면) | 희석의 같은 통계 | 팔의 통계 | 팔 > 희석 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for a in ("R", "D", "RD"):
            x = dil.get(a) or {}
            xd, xp = x.get("delta") or {}, x.get("prim") or {}
            ap = (prim.get(a) or {}).get("mean")
            gt = None if (ap is None or xp.get("mean") is None) else bool(ap > xp["mean"])
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                ARM_KO[a], _fmt(x.get("e_ann"), 3), _fmt(x.get("c"), 3), _fmt(xd.get("all_mean_ann"), 3), _fmt(xd.get("all20_mean_ann"), 3),
                _fmt(xd.get("down_mean"), 4), STAT_KO.get(xp.get("stat"), "—"), _fmt(xp.get("mean"), 4), _fmt(ap, 4), _fmt(gt)))
        L += ["", "- 슬리브 = c·EG30 V0 + (1 − c)·SPY(상수 몫 · T+1 · 10bp) · c = 1 + e/x_V0 를 [0, 1] 로 자른다(x_V0 = C0 연 초과) · e ≥ 0 이면 c = 1(= C0 · 희석 Δ 0). "
              "같은 연 초과를 «EG30 을 덜 드는 것» 으로 냈을 때의 확증 통계(같은 가면 — R: R 켜진 달 Δ_R · D · RD: 하락월 Δ_down)가 기준이다(배치 X 의 «희석선» · 효율 읽기 ⑤).", ""]
    ep_cols = [a for a in ("R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "V_ALONE", "D_ALONE") if a in delta]
    c0m = (arms.get("C0") or {}).get("m") or {}
    eps = c0m.get("episodes") or []
    if eps:
        L += ["## 7. 이름 붙은 급락 · 급등 구간(qbatch_core.EPIS · C0 는 펀드 초과 %p · 나머지는 팔 − C0 %p)", "",
              "| 구간 | C0 | " + " | ".join(ARM_SHORT[a] for a in ep_cols) + " |", "|---|---|" + "---|" * len(ep_cols)]
        for e in eps:
            vals = []
            for a in ep_cols:
                hit = [x.get("d") for x in ((delta.get(a) or {}).get("episodes") or []) if x.get("name") == e.get("name") and x.get("kind") == e.get("kind")]
                vals.append(_fmt(hit[0]) if hit else "—")
            L.append("| %s · %s | %s | %s |" % (e.get("kind"), e.get("name"), _fmt(e.get("ex")), " | ".join(vals)))
        L += [""]
    yrs = sorted((c0m.get("years") or {}).keys())
    if yrs:
        ycols = [a for a in ("R", "D", "RD", "R_SPY", "D_SPY", "R_STAT", "V_ALONE", "D_ALONE") if a in delta]
        L += ["## 8. 해마다(C0 는 펀드 초과 %p · 나머지는 팔 − C0 %p · 창 첫 해 · 끝 해는 부분)", "",
              "| 해 | C0 | " + " | ".join(ARM_SHORT[a] for a in ycols) + " |", "|---|---|" + "---|" * len(ycols)]
        for y in yrs:
            L.append("| %s | %s | %s |" % (y, _fmt((c0m.get("years") or {}).get(y)), " | ".join(_fmt(((delta.get(a) or {}).get("years") or {}).get(y)) for a in ycols)))
        L += [""]
    late = pub.get("late") or {}
    if late.get("rows"):
        L += ["## 9. 부분 창(보유 %s ~ %s · %s개월 · 얼린 하락월 %s · 보고만 · 판정에 쓰지 않는다)" % (late.get("from"), (late.get("window") or ["", ""])[1], late.get("n"), late.get("n_down")), "",
              "| 팔 | Δ_down | 달력 t | 전 월 Δ(%p/년) | NW t | 확증 통계(가면 · 달 수) | 평균 | 달력 t |", "|---|---|---|---|---|---|---|---|"]
        for a, v in late["rows"].items():
            vp = v.get("prim") or {}
            L.append("| %s | %s | %s | %s | %s | %s · %s달 | %s | %s |" % (
                ARM_KO.get(a, a), _fmt(v.get("down_mean"), 4), _fmt(v.get("down_t")), _fmt(v.get("all_mean_ann"), 3), _fmt(v.get("all_nw_t")),
                STAT_KO.get(vp.get("stat"), "—"), vp.get("n"), _fmt(vp.get("mean"), 4), _fmt(vp.get("t"))))
        L += [""]
    pr = pub.get("pairing") or {}
    L += ["## 10. 짝맞춤(구현 점검 · 수익 판정 아님)", "",
          "- E0: C0(몫 ≡ 1) = 얼린 V0 — %s(대 새로 지은 Ctx.V0() %s · 대 저장 V0.ex %s)" % (
              _fmt(((pr.get("E0_v0") or {}).get("ok"))),
              ("%.1e" % pr["E0_v0"]["fresh_max_abs_diff"]) if isinstance((pr.get("E0_v0") or {}).get("fresh_max_abs_diff"), float) else "—",
              ("%.1e" % pr["E0_v0"]["max_abs_diff"]) if isinstance((pr.get("E0_v0") or {}).get("max_abs_diff"), float) else "—"),
          "- E1: 두 장부 팔을 N 장부 식(mix_t1_multi)으로 다시 잰 값 = 얼린 x_adapter.mix_t1 — %s(최대 %s)" % (
              _fmt(pr.get("E1_ok")), ("%.1e" % max((pr.get("E1_max_abs_diff") or {"x": 0.0}).values())) if pr.get("E1_max_abs_diff") else "—"), ""]
    ref = (pub.get("refs") or {})
    fe = ref.get("eg30_frozen") or {}
    L += ["## 11. 참고 줄(값만 옮긴다 · 판정에 들지 않는다)", "",
          "- EG30 V0(얼린 data/_qbatch.json V0.eval · 운용 기준): 연 초과 %s%%p · IR %s · NW t %s · 해마다 %s/%s · 하락월 평균 %s · 슬리브 β %s" % (
              _fmt(fe.get("ann_ex")), _fmt(fe.get("ir")), _fmt(fe.get("nw_t")), fe.get("years_won"), fe.get("n_years"), _fmt(fe.get("down_mean"), 3), _fmt(fe.get("sleeve_beta"))),
          "- %s" % A30_FROZEN, "- %s" % D_BOOK_NOTE, ""]
    L += ["## 12. 미리 적은 예측(등록 §8)", "", "| 예측 | 맞음 |", "|---|---|"]
    for k, ko in PRED_KO.items():
        L.append("| %s | %s |" % (ko, _fmt((pub.get("predictions") or {}).get(k))))
    L += ["", "## 공개 규칙", "",
          "- 이 문서는 게시 칸 파일 하나에서 얼린 렌더러가 만들었다 · 창이 10년이라 값은 모두 공개 창 안이다 · 산출 원본(_egstepout.json)은 저장소 밖 캐시에만 둔다.",
          "- 채택 표시가 있어도 펀드에 붙이는 것은 사용자 결정이다(날짜 없음 · 전방 원장 없음). 표시가 없으면 운용은 그대로다(EG30 V0).",
          "- 표본 안 수치는 오염된 측정이다(등록 §0) — 조합은 DSTK · V02 · Q06 · X-BEAR 기록을 본 뒤 제안됐고 방아쇠는 Q06 기록을 아는 채 골랐다. "
          "배치 Q 는 Q06 을 «전방만 판정 · 표본 안 행은 오염 측정» 후보로 적었고 사용자가 전방 일정을 껐다 — D · RD 의 표시는 Q06 시점의 확인이 아니다."]
    txt = "\n".join(L) + "\n"
    if CACHE_ONLY_KEY in txt:
        raise SystemExit("🚨 결과 문서에 캐시 표지가 있다")
    return txt


def result_doc_write_problems(pub, P=None):
    """--result-doc --write 문지기 — 연기 판이 아니고 · 두 로컬 표식에 FINISHED <산출 sha> 가 있고 · 캐시 산출 sha 가 게시 칸의 out_sha256 과 같아야 쓴다."""
    P = P or paths()
    bad = []
    if not pub or not pub.get("egstep_public_view"):
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
    """등록 전 F0 — 핀 뿌리 셋(작업 트리 data/ 와 무관)으로 F0 자식들을 돌려 개수 · 동일성만 돌려준다(수익 없음). 결과를 엔진 F0_EXPECT · 등록 문서 §10 에 옮긴다."""
    import egstep as E
    c = cache_guard_std()
    os.makedirs(c, exist_ok=True)
    n_stale = purge_stale(c)                                  # 앞선 과정이 죽어 남은 작업 폴더 — 열지 않고 지운다(개수만)
    tmp = tempfile.mkdtemp(prefix="egstep_f0_", dir=c)
    try:
        try:
            pf = preflight(tmp)
            f0, sec = pf["f0"], pf["sec"]
        except SystemExit as e:
            p = os.path.join(tmp, "out_f0s.json")
            if not os.path.exists(p):
                raise
            f0, sec = _read_json(p), {"note": _scrub(str(e))[:300]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"sec": sec, "ok": f0.get("ok"), "bad": f0.get("bad"), "stale_deleted": n_stale, "signature": E.f0_signature(f0),
            "detail": {k: f0.get(k) for k in F0_PUB_KEYS}}


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
    ready = bool(not name_check() and not n_ph and not n_dm and g["ok"] and gw and vw and not mb and not pb and not cb and not xb and not missing
                 and not check_no_forward())
    return {"ready": ready, "prereg": PREREG, "prereg_n": _N_PREREG, "name_ok": not name_check(), "placeholders": n_ph, "draft_marks": n_dm,
            "site_guard": g["ok"], "site_guard_bad": g["bad"][:5], "wired_gitignore": gw, "wired_validate_site": vw,
            "manifest_problems": mb, "pins_problems": pb, "registered_constants_bad": cb, "external_problems": xb, "frozen_missing": missing,
            "no_forward": not check_no_forward(), "head": _git("rev-parse", "HEAD").stdout.strip()}


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기(러너 경로 전체 · 산출은 열지 않고 지운다 · 참/거짓 · 초만)
# ══════════════════════════════════════════════════════════════════════════
def smoke():
    import contextlib
    cache = cache_guard_std()
    os.makedirs(cache, exist_ok=True)
    n_stale = purge_stale(cache)                              # 앞선 과정이 죽어 남은 작업 폴더(실자료 산출이 있을 수 있다) — 열지 않고 지운다(개수만)
    tmp = tempfile.mkdtemp(prefix="egstep_runner_smoke_", dir=cache)
    if _inside(tmp, ROOT):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    saved = dict(_OVR)
    res = {"ok": False, "steps": {}, "started": _now(), "stale_deleted": n_stale}
    t0 = time.time()
    sink = io.StringIO()
    real_out = os.path.join(cache, "out")
    before = sorted(f for f in os.listdir(real_out) if f.startswith("_egstepout")) if os.path.isdir(real_out) else []
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
    after = sorted(f for f in os.listdir(real_out) if f.startswith("_egstepout")) if os.path.isdir(real_out) else []
    res["real_out_untouched"] = before == after == []
    res["real_gitmark_absent"] = not os.path.exists(_git_mark_path())
    res["sec"] = round(time.time() - t0, 1)
    res["ok"] = bool(res["ok"] and res["deleted_unread"] and res["real_out_untouched"] and res["real_gitmark_absent"])
    _write_text(os.path.join(cache, "meta", "_smoke_egstep_run.json"), json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    return res


SMOKE_ALLOWED_KEYS = {"ok", "steps", "started", "stale_deleted", "files", "tag", "err", "stdout_discarded_unread", "deleted_unread", "real_out_untouched", "real_gitmark_absent", "sec",
                      "bake", "registration_error_empty", "start_tag", "stage", "exists", "nonempty", "second_run_blocked", "finished_marks", "tag_file",
                      "restart_blocked", "not_stopped", "public_safe", "result_doc_rendered", "result_doc_has_cache_marker", "out", "mark", "runlog",
                      "public", "gitmark"}


# ══════════════════════════════════════════════════════════════════════════
#  합성 점검(실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _st_shares():
    """몫 규칙 — RD: 스텝 몫 합 ≤ ½ · 방어 먼저(겹친 달 EG30 ½ · D ½ · R 만 EG30 ½ · V ½ · D 만 EG30 ½ · D ½ · EG30 은 늘 ½ 이상 · 오케스트레이터 결정 ②) ·
    1.0 쌍둥이 RD1 은 상한 1(s_D = 1·D · s_V = min(1·R, 1 − s_D) · 겹친 달은 D 가 다 든다) · 지수 레버 대조 = 같은 달 같은 크기(RD→SPY = ½·1[R ∨ D]) ·
    정적 = 평균 몫 · 합 1 · 음수 없음 · rd_shares 의 상한 갈래."""
    import numpy as np
    import egstep as E
    R = np.array([1, 1, 0, 0, 1, 0, 0, 0])
    D = np.array([1, 0, 1, 0, 0, 0, 1, 0])
    T1 = np.array([1, 1, 1, 0, 0, 0, 1, 0])
    T2 = np.array([0, 1, 0, 0, 0, 0, 0, 0])
    S = E.arm_shares(R, D, T1, T2)
    ok = set(S) == set(E.ARMS) and E.STEP_CAP == 0.5
    ok &= np.allclose(S["RD"]["D"], 0.5 * D) and np.allclose(S["RD"]["V"], 0.5 * R * (1 - D))
    ok &= np.allclose(S["RD"]["E"], np.array([0.5, 0.5, 0.5, 1.0, 0.5, 1.0, 0.5, 1.0])) and float(S["RD"]["E"].min()) >= 0.5
    ok &= abs(S["RD"]["V"][0]) < 1e-15 and abs(S["RD"]["D"][0] - 0.5) < 1e-15 and abs(S["RD"]["E"][0] - 0.5) < 1e-15   # 겹친 달: EG30 ½ · D ½ · V 0
    ok &= np.allclose(S["RD1"]["D"], D) and np.allclose(S["RD1"]["V"], np.array([0, 1, 0, 0, 1, 0, 0, 0])) and abs(S["RD1"]["E"][0]) < 1e-15
    ok &= np.allclose(S["RD_SPY"]["S"], S["RD"]["V"] + S["RD"]["D"]) and np.allclose(S["RD_SPY"]["S"], 0.5 * np.maximum(R, D))
    ok &= np.allclose(S["R_SPY"]["S"], S["R"]["V"]) and np.allclose(S["D_SPY"]["S"], S["D"]["D"])
    ok &= np.allclose(S["R_STAT"]["V"], np.mean(0.5 * R)) and np.allclose(S["D_STAT"]["D"], np.mean(0.5 * D))
    ok &= np.allclose(S["RD_STAT"]["V"], np.mean(S["RD"]["V"])) and np.allclose(S["RD_STAT"]["D"], np.mean(S["RD"]["D"]))
    ok &= abs(float(S["RD_STAT"]["V"][0]) - 0.5 * 2 / 8) < 1e-15                                  # R∧¬D 2달 × ½ ÷ 8(겹친 달은 V 가 없다)
    ok &= np.allclose(S["D_T1"]["D"], 0.5 * T1) and np.allclose(S["D_T2"]["D"], 0.5 * T2) and set(S["C0"]) == {"E"} and np.allclose(S["C0"]["E"], 1)
    for a, sh in S.items():
        tot = sum(sh.values())
        ok &= bool(np.allclose(tot, 1.0, atol=1e-12) and min(float(v.min()) for v in sh.values()) >= 0)
    ok &= [k for k in E.ARMS if "S" in S[k]] == ["R_SPY", "D_SPY", "RD_SPY"]
    v, d = E.rd_shares(np.array([1.0]), np.array([1.0]), 0.7, 0.6, 1.0)
    ok &= abs(d[0] - 0.6) < 1e-15 and abs(v[0] - 0.4) < 1e-12
    v, d = E.rd_shares(np.array([1.0, 1.0, 0.0, 0.0]), np.array([1.0, 0.0, 1.0, 0.0]), 0.5, 0.5, 0.5)
    ok &= np.allclose(v, [0.0, 0.5, 0.0, 0.0]) and np.allclose(d, [0.5, 0.0, 0.5, 0.0])
    v, d = E.rd_shares(np.array([1.0]), np.array([1.0]), 0.3, 0.2, 0.4)                         # 상한이 f_R + f_D 보다 작으면 V 만 줄어든다
    ok &= abs(d[0] - 0.2) < 1e-15 and abs(v[0] - 0.2) < 1e-12
    try:
        E.rd_shares(np.array([1.0]), np.array([1.0]), 0.5, 0.6, 0.5)                             # f_D > 상한은 등록 규칙 밖
        ok = False
    except AssertionError:
        pass
    return bool(ok)


def _st_mix_multi():
    """N 장부 T+1 혼합 — 두 장부면 얼린 x_adapter.mix_t1 과 같다(|차| < 1e−12 · 무작위 몫 · 현금 장부) · 세 장부에 0 인 열을 더해도 같다 ·
    몫 ≡ (1, 0, 0) 이면 첫 장부 경로 · 세 장부가 켜지면 달라진다(시험이 이빨이 있다)."""
    import numpy as np
    import qbatch_core as Q
    import q_switch as SW
    import x_adapter as XA
    import egstep as E
    ctx = XA._syn_ctx(n_months=30, seed=7)
    SW._CACHE.clear()
    try:
        F = SW.frame(ctx)
        me_days = [int(F.mstart[k] - 1) for k in range(1, len(F.months))]
        bO = XA._syn_book(SW, F, "O", 0.0005, 0.012, 3, cost_days=tuple(me_days[2::3]))
        bV = XA._syn_book(SW, F, "V", 0.0003, 0.010, 4, cost_days=tuple(int(F.mstart[k]) for k in range(1, len(F.months))))
        bD = XA._syn_book(SW, F, "D", 0.0002, 0.007, 5, cost_days=tuple(me_days))
        bT = XA._syn_book(SW, F, "T", 0.0001, 0.0, 6, cash=True)
        nM = len(F.months)
        rng = np.random.default_rng(3)
        ok = True
        for trial in range(3):
            s = rng.choice([0.0, 0.5, 1.0, 0.25], nM)
            for bk in (bV, bT):
                for c in (SW.COST, SW.COST20):
                    a = XA.mix_t1(F, s, bO, bk, c, Q.fund_from_path)
                    b = E.mix_t1_multi(F, np.column_stack([s, 1 - s]), [bO, bk], c, Q.fund_from_path)
                    b3 = E.mix_t1_multi(F, np.column_stack([s, 1 - s, np.zeros(nM)]), [bO, bk, bD], c, Q.fund_from_path)
                    ok &= float(np.max(np.abs(a["ex"] - b["ex"]))) < 1e-12 and float(np.max(np.abs(a["ex"] - b3["ex"]))) < 1e-12
                    ok &= abs(a["turn"] - b["turn"]) < 1e-12 and abs(a["cost_drag"] - b["cost_drag"]) < 1e-12
        one = E.mix_t1_multi(F, np.column_stack([np.ones(nM), np.zeros(nM), np.zeros(nM)]), [bO, bV, bD], SW.COST, Q.fund_from_path)
        ref = XA.mix_t1(F, np.ones(nM), bO, bV, SW.COST, Q.fund_from_path)
        ok &= float(np.max(np.abs(one["ex"] - ref["ex"]))) < 1e-12
        M3 = np.column_stack([np.full(nM, 0.5), np.full(nM, 0.25), np.full(nM, 0.25)])
        three = E.mix_t1_multi(F, M3, [bO, bV, bD], SW.COST, Q.fund_from_path)
        ok &= float(np.max(np.abs(three["ex"] - ref["ex"]))) > 1e-6
        try:
            E.mix_t1_multi(F, np.column_stack([np.full(nM, 0.6), np.full(nM, 0.6)]), [bO, bV], SW.COST, Q.fund_from_path)
            ok = False
        except AssertionError:
            pass
        return bool(ok)
    finally:
        SW._CACHE.clear()


def _st_run_arm_routes():
    """팔 경로 — 다른 장부 하나면 얼린 mix_t1 · 둘이면 mix_t1_multi · C0 는 mix_t1(1, E, S) · 두 길이 같은 합성 몫에서 같은 값."""
    import numpy as np
    import qbatch_core as Q
    import q_switch as SW
    import x_adapter as XA
    import egstep as E
    ctx = XA._syn_ctx(n_months=14, seed=9)
    SW._CACHE.clear()
    try:
        F = SW.frame(ctx)
        books = {k: XA._syn_book(SW, F, k, 0.0003, 0.01, q) for q, k in enumerate("EVDS")}
        nM = len(F.months)
        R = (np.arange(nM) % 3 == 0).astype(int)
        D = (np.arange(nM) % 4 == 1).astype(int)
        SH = E.arm_shares(R, D, D, np.zeros(nM, int))
        a = E.run_arm(F, SH["R"], books, SW.COST, XA, Q)
        b = XA.mix_t1(F, SH["R"]["E"], books["E"], books["V"], SW.COST, Q.fund_from_path)
        c0 = E.run_arm(F, SH["C0"], books, SW.COST, XA, Q)
        c0b = XA.mix_t1(F, np.ones(nM), books["E"], books["S"], SW.COST, Q.fund_from_path)
        rd = E.run_arm(F, SH["RD"], books, SW.COST, XA, Q)
        rdb = E.mix_t1_multi(F, np.column_stack([SH["RD"]["E"], SH["RD"]["V"], SH["RD"]["D"]]), [books["E"], books["V"], books["D"]], SW.COST, Q.fund_from_path)
        return bool(np.max(np.abs(a["ex"] - b["ex"])) < 1e-15 and np.max(np.abs(c0["ex"] - c0b["ex"])) < 1e-15 and np.max(np.abs(rd["ex"] - rdb["ex"])) < 1e-15)
    finally:
        SW._CACHE.clear()


def _st_delta_and_p():
    """Δ 통계 — 하락월 평균 · 얼린 down_t · t(n_d − 1) 한쪽 p · 전 월 연율 · 20bp 판 · CRASH-M/SURGE-M 가면 · t 없음 → p 없음."""
    import numpy as np
    import eg30plus as EP
    import egstep as E
    from scipy.stats import t as _t
    rs = np.random.RandomState(1)
    n = 120
    ex0 = rs.normal(0.05, 0.3, n)
    ex = ex0 + rs.normal(0.01, 0.05, n)
    fz = np.zeros(n, bool)
    fz[::4] = True
    cr = np.zeros(n, bool)
    cr[::10] = True
    su = np.zeros(n, bool)
    d = E.delta_stats(ex, ex0, ex - 0.001, ex0, fz, cr, su, EP)
    dd = ex - ex0
    ok = abs(d["down_mean"] - dd[fz].mean()) < 1e-15 and abs(d["all_mean_ann"] - dd.mean() * 12) < 1e-12 and d["n_down"] == 30
    ok &= abs(d["down_t"] - EP.down_t(dd, fz, 3)) < 1e-15 and abs(d["p"] - float(_t.sf(d["down_t"], 29))) < 1e-15
    ok &= abs(d["all20_mean_ann"] - (dd.mean() - 0.001) * 12) < 1e-12 and d["surge_m_mean"] is None and abs(d["crash_m_mean"] - dd[cr].mean()) < 1e-15
    ok &= E.p_one_sided(None, 30) is None and abs(E.p_one_sided(1.7, 35) - float(_t.sf(1.7, 34))) < 1e-15
    # 확증 통계(팔마다 제 가면) — R: 켜진 달 36 위 평균 · 얼린 down_t 를 그 가면으로 · t(35) · D · RD: 얼린 하락월 가면이면 delta_stats 와 같다
    rm = np.zeros(n, bool)
    rm[3:39] = True
    ps = E.primary_stat(dd, rm, EP)
    ok &= ps["n"] == 36 and abs(ps["mean"] - dd[rm].mean()) < 1e-15 and abs(ps["t"] - EP.down_t(dd, rm, 3)) < 1e-15
    ok &= abs(ps["p"] - float(_t.sf(ps["t"], 35))) < 1e-15 and abs(ps["p"] - float(_t.sf(ps["t"], 34))) > 1e-9
    pz = E.primary_stat(dd, fz, EP)
    ok &= pz["mean"] == d["down_mean"] and pz["t"] == d["down_t"] and pz["p"] == d["p"] and pz["n"] == d["n_down"]
    ok &= E.primary_stat(dd, np.zeros(n, bool), EP)["mean"] is None and E.primary_stat(dd, np.zeros(n, bool), EP)["p"] is None
    return bool(ok)


def _st_gates_verdict():
    """Holm(얼린 v_tests.holm) · 무해 세 조건 · 지수 레버선 두 조건 · 채택 표시 · 판정 어휘."""
    import egstep as E
    h = E.holm_family({"R": 0.01, "D": 0.02, "RD": 0.3})
    ok = h["reject"] == {"R": True, "D": True, "RD": False} and h["m"] == 3
    h2 = E.holm_family({"R": 0.03, "D": 0.01, "RD": None})
    ok &= h2["reject"] == {"R": False, "D": True, "RD": False}               # 0.01 ≤ 0.0167 · 0.03 > 0.025 에서 멈춘다
    h3 = E.holm_family({"R": 0.017, "D": 0.02, "RD": 0.03})
    ok &= h3["reject"] == {"R": False, "D": False, "RD": False}               # 첫 단계에서 멈춘다
    good = {"all20_mean_ann": 0.01, "down_mean": 0.02}
    ok &= E.harmless(good, 7, 8, 3.0)["harmless"] is True and E.harmless(good, 6, 8, 3.0)["harmless"] is False
    ok &= E.harmless(dict(good, all20_mean_ann=-0.001), 8, 8, 3.0)["conds"]["all20_ge0"] is False and E.harmless(good, 8, 8, 10.5)["harmless"] is False
    dil = {"all20_mean_ann": 0.005, "down_mean": 0.019}
    pg, pdl = {"stat": "r_on", "mean": 0.02}, {"stat": "r_on", "mean": 0.019}       # d1 은 확증 통계(같은 가면)로 — Δ_down 이 아니다
    ok &= E.beats_dilution(pg, pdl, good, dil)["ok"] is True and E.beats_dilution(pg, dict(pdl, mean=0.02), good, dil)["ok"] is False
    ok &= E.beats_dilution(pg, pdl, good, dict(dil, all20_mean_ann=0.011))["ok"] is False and E.beats_dilution(pg, pdl, good, dict(dil, all20_mean_ann=0.01))["ok"] is True
    ok &= E.beats_dilution(pg, pdl, dict(good, down_mean=-1.0), dict(dil, down_mean=5.0))["ok"] is True       # Δ_down 은 d1 에 들지 않는다
    ok &= E.beats_dilution(pg, pdl, good, dil)["stat"] == "r_on" and E.beats_dilution(pg, {"mean": None}, good, dil)["prim_gt_dil"] is False
    hm = E.harmless(good, 8, 8, 3.0)
    ok &= E.adopt_mark(True, hm, E.beats_dilution(pg, pdl, good, dil)) is True and E.adopt_mark(False, hm, E.beats_dilution(pg, pdl, good, dil)) is False
    ok &= E.verdict({"R": True}, {"R": True}) == "보류" and E.verdict({"R": False}, {"R": True}) == "측정만" and E.verdict({"R": False}, {"R": False}) == "기각"
    return bool(ok)


def _st_role_family():
    """팔마다 제 역할(오케스트레이터 결정 ①) — Holm 은 확증 통계(M["primary"])의 p 로 한다(R 의 Δ_down p 가 커도 Δ_R p 로 기각) · d1 은 지수 레버의
    같은 통계(같은 가면) · d2 · 무해는 셋 모두 같다 · 가면이 등록(ROLE)과 다르면 멈춘다 · 위약 뽑기의 셋째 값 = 그 뽑기의 켜진 달 평균."""
    import numpy as np
    import egstep as E
    arm = {"m": {"mech": {"rebounds": {"win": 8}}}, "turn": 2.0}
    M = {"arms": {a: arm for a in ("C0", "R", "D", "RD")},
         "delta": {a: {"all20_mean_ann": 0.01, "down_mean": -0.5, "p": 0.9} for a in ("R", "D", "RD")},
         "primary": {"R": {"stat": "r_on", "n": 36, "mean": 0.03, "t": 3.0, "p": 0.002}, "R_SPY": {"stat": "r_on", "n": 36, "mean": 0.01},
                     "D": {"stat": "down", "n": 35, "mean": 0.01, "t": 1.0, "p": 0.16}, "D_SPY": {"stat": "down", "n": 35, "mean": 0.02},
                     "RD": {"stat": "down", "n": 35, "mean": 0.02, "t": 2.5, "p": 0.008}, "RD_SPY": {"stat": "down", "n": 35, "mean": 0.01}}}
    M["delta"].update({x: {"all20_mean_ann": 0.0, "down_mean": 9.0} for x in ("R_SPY", "D_SPY", "RD_SPY")})
    fam, gates, adopt, vd = E.judge_core(M)
    ok = fam["reject"] == {"R": True, "D": False, "RD": True} and fam["stat"] == {"R": "r_on", "D": "down", "RD": "down"} and fam["n"]["R"] == 36
    ok &= gates["R"]["dilution"]["prim_gt_dil"] is True and gates["D"]["dilution"]["prim_gt_dil"] is False and gates["R"]["dilution"]["dil_prim_mean"] == 0.01
    ok &= adopt == {"R": True, "D": False, "RD": True} and vd == "보류" and all(gates[a]["harmless"]["harmless"] for a in ("R", "D", "RD"))
    M2 = dict(M, primary=dict(M["primary"], R_SPY={"stat": "down", "n": 35, "mean": 0.0}))
    try:
        E.judge_core(M2)
        ok = False
    except E.StopBake:
        pass
    M3 = dict(M, primary=dict(M["primary"], R=dict(M["primary"]["R"], p=0.9)))
    f3, _g3, a3, v3 = E.judge_core(M3)
    ok &= f3["reject"]["R"] is False and a3["R"] is False and v3 == "보류"
    dp = np.array([0.1, -0.2, 0.3, 0.0, 0.4, -0.1])
    fz = np.array([0, 1, 0, 0, 1, 0], bool)
    own = np.array([1, 0, 1, 1, 0, 0], bool)
    x1, x2, x3 = E.placebo_stats(dp, fz, own)
    ok &= abs(x1 - (-0.2 + 0.4) / 2) < 1e-15 and abs(x2 - dp.mean() * 12) < 1e-12 and abs(x3 - (0.1 + 0.3 + 0.0) / 3) < 1e-15
    ok &= E.placebo_stats(dp, fz, np.zeros(6, bool))[2] is None and E.ROLE == {"R": "r_on", "D": "down", "RD": "down"}
    return bool(ok)


def _st_readings():
    """읽기 다섯(팔의 확증 통계로) — ① 바구니: D · RD 는 정적 혼합이 전 월 Δ 와 Δ_down 둘 다 이상 · R 은 전 월 Δ 만(Δ_down 을 보지 않는다)
    ② 시점: R 은 R 위약의 Δ_R 백분위(pct_role) · D 는 D 위약 · RD 는 R · D 위약의 Δ_down 가운데 하나라도 < 95 ③ R 겹침 맞춘 위약(D · RD · 없으면 약함 · R 은 없음)
    ④ 해마다 이긴 수 < C0 면 꾸준함 내줌(여유 없음) ⑤ 확증 통계 ≤ 같은 초과 희석의 같은 통계면 효율 약함 · 금리 역할 읽기는 없다(R 의 확증 통계 · d1 이 됐다) ·
    표시에 붙는 읽기 이름."""
    import egstep as E
    dl = {"R": {"all_mean_ann": 0.1, "down_mean": 0.01}, "R_STAT": {"all_mean_ann": 0.1, "down_mean": 0.0},
          "RD": {"all_mean_ann": 0.1, "down_mean": 0.02}, "RD_STAT": {"all_mean_ann": 0.2, "down_mean": 0.01},
          "D": {"all_mean_ann": 0.0, "down_mean": 0.0}, "D_STAT": {"all_mean_ann": 1.0, "down_mean": 1.0}}
    pl = {"R": {"pct_down": 50.0, "pct_role": 96.0}, "D": {"pct_down": 50.0}, "D_R": {"pct_down": 97.0}}
    yw = {"C0": 8, "R": 8, "D": 7, "RD": 9}
    prim = {"R": {"stat": "r_on", "mean": 0.02}, "D": {"stat": "down", "mean": 0.0}, "RD": {"stat": "down", "mean": 0.02}}
    dil = {"R": {"prim": {"mean": 0.01}}, "D": {"prim": {"mean": 0.0}}, "RD": {"prim": {"mean": 0.03}}}
    r = E.readings(dl, pl, yw, dil, prim)
    ok = r["R"]["static_basket"] is True and r["RD"]["static_basket"] is False and r["D"]["static_basket"] is True   # R: 전 월 같음(Δ_down 은 안 본다)
    ok &= r["R"]["timing_weak"] is False and r["D"]["timing_weak"] is True and r["RD"]["timing_weak"] is True     # R 은 pct_role 96 · RD 는 R 의 pct_down 50
    ok &= r["R"]["placebo_pct"] == [96.0] and r["RD"]["placebo_pct"] == [50.0, 50.0]
    ok &= r["R"]["timing_weak_r"] is None and r["D"]["timing_weak_r"] is False and r["RD"]["timing_weak_r"] is False
    ok &= r["R"]["steady_lost"] is False and r["D"]["steady_lost"] is True and r["RD"]["steady_lost"] is False
    ok &= r["R"]["eff_weak"] is False and r["D"]["eff_weak"] is True and r["RD"]["eff_weak"] is True        # 0.02 > 0.01 · 0 ≤ 0 · 0.02 ≤ 0.03
    ok &= r["R"]["eff_arm"] == 0.02 and r["R"]["eff_dil"] == 0.01 and r["R"]["stat"] == "r_on" and r["RD"]["stat"] == "down"
    ok &= all("rate_role" not in r[a] for a in r)
    ok &= E.reading_flags(r["R"]) == ["바구니"] and E.reading_flags(r["D"]) == ["바구니", "시점", "꾸준함", "효율"]
    r2 = E.readings(dict(dl, R_STAT={"all_mean_ann": 0.09, "down_mean": 5.0}), {"R": {"pct_down": 99.0, "pct_role": 50.0}, "D": {"pct_down": 97.0}}, yw, dil, prim)
    ok &= r2["R"]["static_basket"] is False and r2["R"]["timing_weak"] is True and r2["RD"]["timing_weak"] is False and r2["D"]["timing_weak_r"] is True
    ok &= E.reading_flags(r2["R"]) == ["시점"]
    r3 = E.readings(dl, {})
    ok &= r3["R"]["timing_weak"] is True and r3["D"]["timing_weak_r"] is True and r3["R"]["steady_lost"] is None and r3["R"]["eff_weak"] is None
    return bool(ok)


def _st_dil_rule():
    """같은 초과 희석 — 엔진 dil_share 가 배치 X 의 식(얼린 x_adapter._s_child 의 한 줄 · 글자 대조)과 같다 · e ≥ 0 이나 x_V0 ≤ 0 이면 1 · [0, 1] 로 자른다."""
    import egstep as E
    xa = _read_text(os.path.join(HERE, "x_adapter.py"))
    ok = "cdil = 1.0 if (x_v0 <= 0 or e_ann >= 0) else float(np.clip(1 + e_ann / x_v0, 0.0, 1.0))" in xa
    ok &= "return 1.0 if (x_v0 <= 0 or e_ann >= 0) else float(np.clip(1 + e_ann / x_v0, 0.0, 1.0))" in _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    ok &= E.dil_share(0.1, 0.76) == 1.0 and E.dil_share(0.0, 0.76) == 1.0 and E.dil_share(-0.1, -0.2) == 1.0 and E.dil_share(-0.1, 0.0) == 1.0
    ok &= abs(E.dil_share(-0.19, 0.76) - 0.75) < 1e-15 and E.dil_share(-2.0, 0.76) == 0.0
    return bool(ok)


def _st_cuts_state_strat():
    """상태별 자르기(가면 · 평균 · 얼린 down_t · 하락월) · 굽기 상태 개수 대조(다르면 StopBake) · R 겹침 맞춘 위약(켜진 달 · 교체 · 겹침 보존 · 같은 씨앗이면 같다 ·
    F0 받아들임 셈 = 굽기 첫 뽑기들)."""
    import numpy as np
    import eg30plus as EP
    import q_switch as SW
    import egstep as E
    rs = np.random.RandomState(5)
    n = 120
    aR = np.zeros(n, np.int8)
    aR[10:20] = 1
    aR[40:52] = 1
    aR[80:94] = 1
    aD = np.zeros(n, np.int8)
    aD[12:15] = 1
    aD[45:47] = 1
    aD[60:62] = 1
    aD[90:93] = 1
    d = rs.normal(0.0, 0.1, n)
    fz = np.zeros(n, bool)
    fz[::3] = True
    mk = E.state_masks(aR, aD)
    ok = int(mk["d_and_r"].sum()) == 8 and int(mk["d_not_r"].sum()) == 2 and int(mk["r_not_d"].sum()) == 28 and int(mk["neither"].sum()) == 82
    c = E.state_cuts(d, mk, fz, EP)
    ok &= set(c) == set(E.CUT_KEYS) and c["d_on"]["n"] == 10 and abs(c["d_on"]["mean"] - d[aD > 0].mean()) < 1e-15
    ok &= abs(c["r_on"]["t"] - EP.down_t(d, aR > 0, 3)) < 1e-15 and c["d_not_r"]["t"] is None and c["d_on"]["n_down"] == int(((aD > 0) & fz).sum())
    sc = E.state_counts(aR, aD, aD, np.zeros(n, np.int8))
    exp = {"n_forms": n}
    exp.update({k: sc[k] for k in E.STATE_KEYS})
    ok &= E.check_state_counts(sc, exp) is True and E.check_state_counts(sc, None) is True
    try:
        E.check_state_counts(sc, dict(exp, both=sc["both"] + 1))
        ok = False
    except E.StopBake:
        pass
    got, tries, ov = E.strat_placebo(SW, aR, aD, 11, 50, 5000, lambda p: p.copy())
    ok &= ov == 8 and len(got) == 50 and tries >= 50
    ok &= all(int(p.sum()) == int(aD.sum()) and int(np.sum(p[1:] != p[:-1])) == int(np.sum(aD[1:] != aD[:-1])) and int(np.sum((p > 0) & (aR > 0))) == ov for p in got)
    got2, tries2, _ = E.strat_placebo(SW, aR, aD, 11, 50, 5000, lambda p: p.copy())
    ok &= tries2 == tries and all(np.array_equal(a, b) for a, b in zip(got, got2)) and any(not np.array_equal(p, aD) for p in got)
    acc, tr3, _ = E.strat_placebo(SW, aR, aD, 11, 10 ** 9, tries)          # F0 꼴(받아들인 수만 · 같은 뽑기 수) = 굽기 꼴의 받은 수
    ok &= len(acc) == 50 and tr3 == tries
    return bool(ok)


def _st_purge_stale():
    """남은 작업 폴더 — egstep_work_* · egstep_f0_* · egstep_runner_smoke_* 폴더만 열지 않고 지우고 개수를 돌려준다(out · meta · 같은 이름의 파일은 그대로)."""
    tmp = tempfile.mkdtemp(prefix="egstep_st_stale_")
    try:
        for d in ("egstep_work_a1", "egstep_f0_b2", "egstep_runner_smoke_c3", "out", "meta", "vbatch_cache"):
            os.makedirs(os.path.join(tmp, d, "x"), exist_ok=True)
            _write_text(os.path.join(tmp, d, "x", "out_s.json"), "{}\n")
        _write_text(os.path.join(tmp, "egstep_work_file.txt"), "x\n")
        n = purge_stale(tmp)
        left = sorted(os.listdir(tmp))
        ok = n == 3 and left == ["egstep_work_file.txt", "meta", "out", "vbatch_cache"] and purge_stale(tmp) == 0
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_placebo_shuffle():
    """위약 — 얼린 q_switch.seg_shuffle 이 켜진 달 수 · 교체 수를 보존 · 같은 씨앗이면 같은 뽑기 · 백분위 = 참보다 작은 뽑기 몫(랩 규약)."""
    import numpy as np
    import q_switch as SW
    import egstep as E
    x = np.array([0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0] * 5, np.int8)
    r1, r2 = np.random.default_rng(E.SEED), np.random.default_rng(E.SEED)
    ok = True
    diff = 0
    for _ in range(50):
        a, b = SW.seg_shuffle(x, r1), SW.seg_shuffle(x, r2)
        ok &= bool(np.array_equal(a, b) and a.sum() == x.sum() and np.sum(a[1:] != a[:-1]) == np.sum(x[1:] != x[:-1]))
        diff += int(not np.array_equal(a, x))
    ok &= diff > 0 and E.pct_rank([1.0, 2.0, 3.0, 4.0], 2.5) == 50.0 and E.pct_rank([1.0, 2.0], 0.0) == 0.0
    return bool(ok)


def _st_state_counts():
    import egstep as E
    c = E.state_counts([1, 1, 0, 0, 1], [1, 0, 1, 0, 0], [1, 0, 1, 1, 0], [0, 0, 0, 1, 0])
    return c == {"n": 5, "r_on": 3, "d_on": 2, "both": 1, "r_only": 2, "d_only": 1, "neither": 1, "r_switch": 2, "d_switch": 3, "r_on_runs": 2, "d_on_runs": 2,
                 "t1_on": 3, "t2_on": 1}


def _st_regime_q06_frozen():
    """재사용 규칙 — 금리 상태는 얼린 dstk.regimes 의 «value»(문턱 경계 부동소수 · T17 과 같다) · Q06 은 얼린 q_corrsurp 합성 selftest 통과(CS ≡ 1 · 창 t−1 · 월 가중 · 백분위) ·
    엔진의 재사용 상수 기대값이 작업 트리 모듈과 같다."""
    import egstep as E
    import dstk as DS
    import q_corrsurp as QC

    class _A(dict):
        pass
    ser = {}
    import datetime as dt
    d = dt.date(2016, 1, 1)
    v = 1.0
    k = 0
    while d <= dt.date(2026, 8, 31):
        if d.weekday() < 5:
            k += 1
            ser[d.strftime("%Y-%m-%d")] = round(1.0 + 0.4 * math.sin(k / 90.0), 2)
        d += dt.timedelta(days=1)
    R, codes = E.r_states(DS, {"macro": {"DFII10": ser}})
    ok = len(R) == 120 and all(R[m] == int(codes[m] == "value") for m in R) and set(codes.values()) <= {"value", "neutral", "growth"}
    ok &= DS.regime_at({"2020-01": 1.0, "2020-04": 1.2}, "2020-04")["code"] == "neutral"
    ok &= all(E._norm(getattr(DS, k2)) == E._norm(v2) for k2, v2 in E.DSTK_EXPECT.items())
    ok &= all(E._norm(getattr(QC, k2)) == E._norm(v2) for k2, v2 in E.Q06_EXPECT.items())
    ok &= bool(QC.selftest()["ok"])
    return bool(ok)


def _st_blob_guard():
    import egstep as E
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
    for m, b in E.ROOT_BLOBS.items():
        ok &= _git("rev-parse", "%s:build/%s.py" % (ROOT_PIN["code_pin"], m)).stdout.strip() in (b, "") or m == "x_adapter"
    return bool(ok)


def _st_lock_and_tag():
    """동시 굽기 막기 — 배타 잠금은 두 번째를 멈추고 풀면 다시 잡힌다 · 시작 태그가 이미 있으면 EGSTEP_RERUN 일 때만 «already»."""
    tmp = tempfile.mkdtemp(prefix="egstep_st_lock_")
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


def _fake_main(stopped=None):
    """게시 칸 · 결과 문서 시험용 합성 산출(값은 표지 수 0.5555)."""
    if stopped:
        return {"kind": "egstep_out", "stopped": stopped}
    mk = 0.5555
    m = {"n": 120, "ann_ex": mk, "te": mk, "ir": mk, "t_iid": mk, "nw_t": mk, "win": 55.5, "years": {"2021": mk, "2022": mk}, "years_won": 5, "n_years": 11,
         "down_n": 39, "down_mean": mk, "down_win": 50.0, "up_mean": mk, "down_capture": mk, "up_capture": mk, "sleeve_beta": 1.1,
         "episodes": [{"kind": "급락", "name": "코로나19 팬데믹", "ex": mk}], "crash_won": 1, "surge_won": 5,
         "mech": {"crash_legs": {"n": 8, "mean": mk, "win": 3}, "rebounds": {"n": 8, "mean": mk, "win": 7}, "crash_m": {"n": 14, "mean": mk, "win": 3},
                  "surge_m": {"n": 26, "mean": mk, "win": 3}}, "roll12": {"n": 109, "hit": 55.5}, "halves": [mk, mk], "blocks": [mk, mk, mk, mk],
         "series_leak": None}
    arm = {"m": m, "m20": {"ann_ex": mk, "nw_t": mk}, "down_frozen": {"n": 35, "mean": mk, "win": 50.0}, "turn": 3.3, "cost_drag": mk}
    arms = {a: dict(arm) for a in ARM_ORDER}
    dl = {"n": 120, "n_down": 35, "down_mean": mk, "down_t": mk, "p": 0.29, "up_mean": mk, "all_mean_ann": mk, "all_nw_t": mk, "win": 50.0,
          "all20_mean_ann": mk, "down20_mean": mk, "crash_m_mean": mk, "surge_m_mean": mk, "years": {"2022": mk},
          "episodes": [{"kind": "급락", "name": "코로나19 팬데믹", "d": mk}]}
    delta = {a: dict(dl) for a in ARM_ORDER if a != "C0"}
    hm = {"harmless": True, "conds": {"all20_ge0": True, "rebounds_ok": True, "turn_le10": True}, "all20_mean_ann": mk, "rebounds_win": 7, "rebounds_c0": 8, "turn": 3.3}
    dil = {"prim_gt_dil": True, "all20_ge_dil": False, "ok": False, "dil_prim_mean": mk, "dil_all20_mean_ann": mk}
    fam_of = {"R": "R", "R_SPY": "R", "R_STAT": "R", "D": "D", "D_SPY": "D", "D_STAT": "D", "RD": "RD", "RD_SPY": "RD", "RD_STAT": "RD"}
    role = {"R": "r_on", "D": "down", "RD": "down"}
    prim = {x: {"stat": role[f], "n": (36 if role[f] == "r_on" else 35), "mean": mk, "t": mk, "p": 0.29} for x, f in fam_of.items()}
    return {"kind": "egstep_out", "window": ["2016-09", "2026-08"], "n_hold": 120, "primary": prim,
            "states": {"n": 120, "r_on": 36, "d_on": 22, "both": 7, "r_only": 29, "d_only": 15, "neither": 69, "r_switch": 20, "d_switch": 30,
                       "r_on_runs": 10, "d_on_runs": 15, "t1_on": 30, "t2_on": 8},
            "down": {"n_frozen": 35, "n_pr": 39, "n_crash_m": 14, "n_surge_m": 26}, "arms": arms, "delta": delta,
            "family": {"p": {"R": 0.29, "D": 0.29, "RD": 0.29}, "reject": {"R": False, "D": False, "RD": False}, "threshold": {"R": 0.0167, "D": None, "RD": None},
                       "order": ["R", "D", "RD"], "m": 3, "alpha": 0.05, "stat": dict(role), "n": {"R": 36, "D": 35, "RD": 35}},
            "gates": {a: {"harmless": dict(hm), "dilution": dict(dil, stat=role[a])} for a in ("R", "D", "RD")}, "adopt": {"R": False, "D": False, "RD": False}, "verdict": "기각",
            "readings": {"R": {"stat": "r_on", "static_basket": True, "timing_weak": True, "placebo_pct": [50.0], "timing_weak_r": None, "placebo_pct_r": None,
                               "steady_lost": False, "years_won": 8, "years_won_c0": 8, "eff_weak": False, "eff_arm": mk, "eff_dil": 0.4444},
                         "D": {"stat": "down", "static_basket": False, "timing_weak": False, "placebo_pct": [96.0], "timing_weak_r": True, "placebo_pct_r": 60.0,
                               "steady_lost": True, "years_won": 7, "years_won_c0": 8, "eff_weak": True, "eff_arm": mk, "eff_dil": mk},
                         "RD": {"stat": "down", "static_basket": False, "timing_weak": True, "placebo_pct": [50.0, 96.0], "timing_weak_r": True, "placebo_pct_r": 60.0,
                                "steady_lost": False, "years_won": 8, "years_won_c0": 8, "eff_weak": False, "eff_arm": mk, "eff_dil": 0.4444}},
            "reading_flags": {"R": ["바구니", "시점"], "D": ["R 겹침 시점", "꾸준함", "효율"], "RD": ["시점", "R 겹침 시점"]},
            "cuts": {a: {k: {"n": 12, "mean": mk, "t": mk, "n_down": 4, "down_mean": mk} for k in ("r_on", "d_on", "d_and_r", "d_not_r", "r_not_d", "neither")}
                     for a in ("R", "D", "RD", "R_SPY", "D_SPY", "RD_SPY", "R_STAT", "D_STAT", "RD_STAT")},
            "dil": {a: {"c": 0.9, "e_ann": -0.05, "turn": 0.1, "delta": {"down_mean": mk, "down_t": mk, "up_mean": mk, "all_mean_ann": mk, "all20_mean_ann": mk,
                                                                          "crash_m_mean": mk, "surge_m_mean": mk},
                        "prim": {"stat": role[a], "n": (36 if a == "R" else 35), "mean": mk, "t": mk, "p": 0.29}} for a in ("R", "D", "RD")},
            "placebo": dict({nm: {"k": 1000, "seed": 20260927, "true_down": mk, "pct_down": 50.0, "true_all": mk, "pct_all": 50.0,
                                  "down_q": {"p05": mk, "p50": mk, "p95": mk}, "all_q": {"p05": mk, "p50": mk, "p95": mk}} for nm in ("D",)},
                            R={"k": 1000, "seed": 20260928, "true_down": mk, "pct_down": 50.0, "true_all": mk, "pct_all": 50.0,
                               "down_q": {"p05": mk, "p50": mk, "p95": mk}, "all_q": {"p05": mk, "p50": mk, "p95": mk},
                               "role_stat": "r_on", "true_role": mk, "pct_role": 77.7, "role_q": {"p05": mk, "p50": mk, "p95": mk}},
                            D_R={"k": 1000, "k_target": 1000, "seed": 20260929, "tries": 25000, "overlap": 12, "true_down": mk, "pct_down": 60.0, "true_all": mk,
                                 "pct_all": 50.0, "down_q": {"p05": mk, "p50": mk, "p95": mk}, "all_q": {"p05": mk, "p50": mk, "p95": mk}}),
            "late": {"from": "2019-06", "window": ["2019-06", "2026-08"], "n": 87, "n_down": 25,
                     "rows": {"R": {"down_mean": mk, "down_t": mk, "all_mean_ann": mk, "all_nw_t": mk, "prim": {"stat": "r_on", "n": 26, "mean": mk, "t": mk}}}},
            "pairing": {"E0_v0": {"hash_ok": True, "same_hold": True, "fresh_max_abs_diff": 0.0, "max_abs_diff": 0.0, "ok": True}, "E1_max_abs_diff": {"R": 0.0, "D": 0.0}, "E1_ok": True},
            "mean_share": {a: {"E": 0.85, "V": 0.15} for a in ARM_ORDER},
            "predictions": {k: True for k in PRED_KO},
            "multiplicity": {"m_confirmatory": 3, "alpha": 0.05, "cum_n_before": 1044, "rows_counted": 14, "cum_n_after": 1058, "counted": ["R"]},
            "refs": {"eg30_frozen": {"ann_ex": mk, "ir": mk, "nw_t": mk, "years_won": 8, "n_years": 11, "down_mean": mk, "sleeve_beta": 1.2}}}


def _fake_f0():
    return {"ok": True, "bad": [], "dstk": {"dstk_ok": True, "dstk_forms": {"n": 121, "n_valid": 121}, "dstk_regime": {"value": 36, "neutral": 53, "growth": 31,
                                                                                                                  "switches": 41, "same_as_t17": True}},
            "q06_dry": {"ok": True}, "q06_same_as_recorded": True,
            "states": {"n": 120, "r_on": 36, "d_on": 22, "both": 7, "r_only": 29, "d_only": 15, "neither": 69, "r_switch": 20, "d_switch": 30, "r_on_runs": 10,
                       "d_on_runs": 15, "t1_on": 30, "t2_on": 8},
            "strat": {"overlap": 7, "probe": 20000, "accepted": 1500},
            "v0_identity": {"hash_ok": True, "ok": True, "fresh_max_abs_diff": 0.0, "max_abs_diff": 0.0}, "grid": {"same_as_droot": True, "n_win_dates": 2515},
            "down": {"n_frozen": 35, "frozen_eq_spytr": True, "n_frozen_late": 25, "n_late_months": 87, "n_pr": 39},
            "d_book": {"pairing_A": True, "n_forms_with_target": 120, "names_min": 80, "names_max": 110, "cov_ok_months": 120, "cov_months": 120, "sel_hash16": "ab" * 8}}


def _st_public_and_result_doc():
    """게시 칸 — 캐시 표지 없음 · 공개 안전 · 값 계열 없음 · 결과 문서 머리 세 줄(풀카드 · 판정 · 규칙) · «등록 커밋 `<40자>`» 가 문서의 첫 «커밋 <해시>» ·
    심은 값 계열 · 2016-09 앞 창 실수는 public_safe_std 가 잡는다 · 멈춤 판도 그린다 · 등록 오류 글의 소수 지우기."""
    full = "0123456789abcdef0123456789abcdef01234567"
    out = {CACHE_ONLY_KEY: True, "prereg": PREREG, "f0": _fake_f0(), "main": _fake_main(), "pins": {"root": ROOT_PIN, "vroot": VROOT_PIN, "droot": DROOT_PIN},
           "series": {"ex": {"R": [0.1] * 120}}}
    pub = public_doc(out, "0" * 64, 1, {"commit": full})
    blob = json.dumps(pub, ensure_ascii=False)
    txt = result_doc(pub)
    ok = CACHE_ONLY_KEY not in blob and "series_leak" not in blob and '"series"' not in blob and "0.56" in txt
    ok &= all(re.search(r"^\s*%s\s*[:：]" % k, txt, re.M) for k in ("풀카드", "판정", "규칙"))
    ok &= re.search(r"^풀카드:\s*없음", txt, re.M) is not None and re.search(r"^규칙:\s*없음", txt, re.M) is not None
    hm = re.search(r"커밋\s*[`'\"]?([0-9a-f]{7,40})", txt)
    ok &= bool(hm) and hm.group(1) == full
    ok &= re.search(r"^판정:\s*기각", txt, re.M) is not None
    ok &= bool(public_safe_std({"x": {"window": ["2014-09", "2026-08"], "v": 0.5}})) and not public_safe_std({"x": {"window": ["2014-09", "2026-08"], "n": 144}})
    ok &= bool(public_safe_std({"s": [0.1, 0.2, 0.3, 0.4, 0.5]}))
    bad = dict(pub)
    bad["arms"] = dict(pub["arms"], leak=[0.1] * 12)
    ok &= bool(public_safe_std(bad))
    tmpf = tempfile.mkdtemp(prefix="egstep_st_re_")
    try:
        rp = os.path.join(tmpf, "re.txt")
        _write_text(rp, "# 주석\n§4 글은 0.25 라 했으나 코드는 다른 값\n\n두 번째 줄 2021-10\n")
        re_ = reg_err_lines(rp)
    finally:
        shutil.rmtree(tmpf, ignore_errors=True)
    txt_re = result_doc(pub, re_)
    ok &= re_[0] == ["§4 글은 <num> 라 했으나 코드는 다른 값", "두 번째 줄 2021-10"] and len(re_[1]) == 16
    ok &= ("등록 오류: §4 글은 <num> 라 했으나 코드는 다른 값; 두 번째 줄 2021-10" in txt_re) and re_[1] in txt_re and "0.25" not in txt_re
    ok &= "등록 오류: 없음" in txt and "정적 혼합 몫 — 상태 스텝 증거 아님" in txt and "시점 증거 약함" in txt and "DSTK A30" in txt
    ok &= all(s in txt for s in ("지수 레버 대조", "지수 레버선", "## 5. 상태별 자르기", "## 6. 같은 초과 희석", "R 겹침 맞춤(참 겹침 12", "꾸준함 내줌**(7/8)", "희석선 밑",
                                 "섹터 비중은 중립이 아니다", "R 의 확증 통계는 제 역할의 통계다", "D 켜진 달 22 가운데 12", "완전 연도 2017 ~ 2025",
                                 "남은 작업 폴더: 0", "7 · 1500/20000", "P8 D 의 R 겹침", "P9 R 의 Δ_R", "R 켜진 달 Δ_R · 36달 · t(35)",
                                 "얼린 하락월 Δ_down · 35달 · t(34)", "그 12달 RD 슬리브는 EG30 ½ · D ½", "2022 · 금리형 급락 구간의 이득은 설계 전에 본 해",
                                 "누적 N 1044 → 1058(센 줄 14", "R 의 확증 통계 위약", "| 77.7 |", "희석선 위(희석 0.4444 · 팔 0.5555)",
                                 "스텝 몫 합 ≤ ½", "R 켜진 달 Δ_R · 26달"))
    ok &= "금리 역할 증거 없음" not in txt and "| 금리 역할(R 켜진 달) |" not in txt                 # 첫 판의 금리 역할 읽기 칸은 없다(R 의 확증 통계 · d1 이 됐다)
    ok &= "의 채택 표시에 읽기" not in txt                                      # 표시가 없으면 표시 읽기 줄도 없다
    pub3 = public_doc(dict(out, main=dict(_fake_main(), adopt={"R": True, "D": False, "RD": False}, verdict="보류")), "0" * 64, 1, {"commit": full, "stale_deleted": 2})
    txt3 = result_doc(pub3)
    ok &= "**R · 금리 스텝 → 가치 다리 V30 · ½ 의 채택 표시에 읽기(바구니 · 시점)가 붙었다" in txt3 and "남은 작업 폴더: 2" in txt3
    ok &= re.search(r"^판정:\s*보류", txt3, re.M) is not None and not public_safe_std(pub3)
    out2 = dict(out, main=_fake_main(stopped="장부 날짜가 뿌리 격자와 다르다"))
    pub2 = public_doc(out2, "0" * 64, 1, {"commit": full})
    txt2 = result_doc(pub2)
    ok &= "## 멈춤" in txt2 and "0.5555" not in json.dumps(pub2) and re.search(r"^판정:\s*보류", txt2, re.M) is not None
    return bool(ok)


def _st_result_write_guard():
    """--result-doc --write 문지기 — 연기 판 · FINISHED 없음 · 산출 sha 불일치 · 커밋이 40자 해시가 아니면 거절 · 모두 맞으면 통과."""
    tmp = tempfile.mkdtemp(prefix="egstep_st_")
    try:
        P = {"out": os.path.join(tmp, "_egstepout.json"), "mark": os.path.join(tmp, "_egstepout.started"), "gitmark": os.path.join(tmp, "gm")}
        with open(P["out"], "wb") as f:
            f.write(b'{"x": 1}\n')
        sha = _sha_file(P["out"])
        for m in (P["mark"], P["gitmark"]):
            _write_text(m, "C · t\n%s %s t\n" % (FINISHED, sha))
        pub = {"egstep_public_view": True, "smoke": False, "out_sha256": sha, "prereg_commit": "a" * 40}
        ok = not result_doc_write_problems(pub, P)
        ok &= bool(result_doc_write_problems(dict(pub, smoke=True), P))
        ok &= bool(result_doc_write_problems(dict(pub, out_sha256="0" * 64), P))
        ok &= bool(result_doc_write_problems(dict(pub, prereg_commit="SMOKE"), P))
        _write_text(P["gitmark"], "C · t\n")
        ok &= bool(result_doc_write_problems(pub, P))
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_scrub():
    a = _scrub("값 0.1234 · 1e-05 · 2.5E+03 · -.5 · 2014-08 · 3 개\n  File \"x.py\", line 12")
    return a == "값 <num> · <num> · <num> · <num> · 2014-08 · 3 개\n  File \"x.py\", line 12"


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
    """EGSTEP_COMMIT 없이 · 모르는 커밋으로는 판 점검이 멈춘다(아무것도 쓰지 않는다)."""
    ok = True
    for env in ({}, {"EGSTEP_COMMIT": "0" * 40, "_EGSTEP_NO_FETCH": "1"}):
        try:
            frozen_check(env)
            ok = False
        except SystemExit:
            pass
    return ok


def _st_registered():
    import egstep as E
    return not registered_constants_ok(E)


def _st_wire():
    g0, v0 = "a\n", 'x = 1\nprint("사이트 검증:", 1)\n'
    g1, v1 = wire_texts(g0, v0)
    g2, v2 = wire_texts(g1, v1)
    return bool(g1 == g2 and v1 == v2 and "_egstepout*" in g1 and v1.index("EG30 상태 조건 스텝 역할 검정") < v1.index('print("사이트 검증:"'))


def _st_names():
    want = ["data/_egstepout.json", "data/_egstep_other.json", "data/_egstepfwd/genesis.json", "x/egstep_cache/a", "_egstepout.public.json"]
    ok = all(scan_repo_names([f]) for f in want)
    return bool(ok and not scan_repo_names([MANIFEST_FILE, "data/style_top.json", "build/egstep_run.py", "build/egstep.py", "data/_dstk_manifest.json"]))


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
    """연기 기록 칸은 허용 목록뿐 — 크기 · 길이 · 형 · 키 목록 · 값이 들어갈 칸이 없다(배치 X §0.3)."""
    src = _read_text(os.path.join(ROOT, *RUNNER.split("/")))
    body = src[src.index("def smoke():"):src.index("SMOKE_ALLOWED_KEYS")]
    keys = set(re.findall(r'\[\s*"([a-z_]+)"\s*\]\s*=', body)) | set(re.findall(r'"([a-z_]+)"\s*:', body))
    return bool(keys and keys <= SMOKE_ALLOWED_KEYS and "getsize(P[k]) > 0" in body and "len(" not in body.replace("len(tmp)", ""))


def _st_no_forward():
    import egstep as E
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    return bool(not any(hasattr(E, n) for n in FORBIDDEN_ENGINE_NAMES) and "_egstepfwd" not in src and not check_no_forward())


def _st_no_etf_holding():
    """어떤 팔의 목적지도 ETF 가 아니다 — 장부는 EG30 V0 · DSTK 가치 다리 · V02 책 D(모두 개별 주식) · SPY TR 은 지수 레버 대조 셋 · 같은 초과 희석 셋
    (과 C0 의 몫 0 자리)에서만 «90% 지수 바구니의 수익 대리» 로 쓴다 · 엔진에 IVE/IVW 가 없다 · SPDR 은 Q06 상태 입력(얼린 상수 대조)으로만 이름이 나온다."""
    import numpy as np
    import egstep as E
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    S = E.arm_shares(np.array([1, 0]), np.array([0, 1]), np.array([0, 1]), np.array([0, 0]))
    ok = [a for a in E.ARMS if "S" in S[a]] == ["R_SPY", "D_SPY", "RD_SPY"] and all(k in ("E", "V", "D", "S") for a in S for k in S[a])
    ok &= '"IVE"' not in src and '"IVW"' not in src and src.count('"XLK"') == 1 and "spy_book" in src
    body = src[src.index("def _s_body(job):"):src.index("def child_main(argv):")]
    ok &= body.count("bE, bS, COST") == 2 and "np.full(len(months), cd), bE, bS, COST, " in body     # SPY 장부를 직접 넘기는 곳은 같은 초과 희석(10 · 20bp)뿐 · 나머지는 몫 S 로(지수 레버)
    return bool(ok)


def _st_predictions_signature():
    """예측 칸 = 등록 §8 의 아홉(참/거짓만) · F0 서명은 정수 · 날짜 글자 · 참/거짓 · 짧은 해시만(실수 없음)."""
    import egstep as E
    M = _fake_main()
    P = E.predictions(M)
    ok = set(P) == set(PRED_KO) and all(isinstance(v, bool) for v in P.values())
    f0 = dict(_fake_f0(), q06_same_as_recorded=True)
    f0["v0_identity"] = {"hash_ok": True, "ok": True, "max_abs_diff": 0.0}
    sig = E.f0_signature(f0)
    ok &= all(v is None or (isinstance(v, (int, str, bool)) and not isinstance(v, float)) for v in sig.values())
    ok &= "max_abs_diff" not in sig and (E.F0_EXPECT is None or set(sig) == set(E.F0_EXPECT))
    ok &= E.F0_EXPECT is None or all(not isinstance(v, float) for v in E.F0_EXPECT.values())
    return bool(ok)


def _st_git_blob():
    return git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391" and git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


SELFTESTS = (_st_shares, _st_mix_multi, _st_run_arm_routes, _st_delta_and_p, _st_gates_verdict, _st_role_family, _st_readings, _st_dil_rule, _st_cuts_state_strat,
             _st_placebo_shuffle, _st_state_counts, _st_regime_q06_frozen, _st_blob_guard, _st_lock_and_tag, _st_purge_stale, _st_public_and_result_doc,
             _st_result_write_guard, _st_scrub, _st_start_guard, _st_frozen_refuses, _st_registered, _st_wire, _st_names, _st_manifest_hashes_only,
             _st_open_encoding, _st_std_head, _st_smoke_no_sizes, _st_no_forward, _st_no_etf_holding, _st_predictions_signature, _st_git_blob)


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
