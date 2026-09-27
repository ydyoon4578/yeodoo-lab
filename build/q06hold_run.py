# -*- coding: utf-8 -*-
"""build/q06hold_run.py — Q06 방어 스텝 방아쇠의 기전 검정 · 랩이 안 본 창(Q06HOLD) 한 번 굽기 러너.

사전등록: build/PREREG-<등록 날짜>-Q06HOLD.md 하나(이 러너는 날짜를 박지 않는다 · 결과 문서 = 그 이름 + «-RESULT»).
계산은 build/q06hold.py(엔진)가 핀 판 임시 뿌리 둘 안에서 한다 — 이 러너는 판 점검 · 뿌리 짓기 · 자식 과정 · 시작 표식 · 게시 칸 · 결과 문서만 맡는다.

🚨 질문: 방어 스텝의 방아쇠(Q06 상관 놀람)가 켜진 다음 달, 저베타 대형주 책은 시장보다 평소보다 더 나은가 — 랩이 잰 적 없는 창(보유 2006-09 ~ 2016-08) ·
   상태 = «Q06 긴 이력판»(얼린 q_corrsurp 함수 · 이력 상수만 원조 SPDR 상장일로) · 주 목적지 = French BIG LoBETA − Mkt(생존 편향 없는 기전 대리).
   주 통계는 총 Δ_timing(양 = 기전이 선다) · 판정은 점 추정의 부호만 읽는다 · 창의 켜진 달 < 6 이면 «측정 불가»(카드 Q06 F0 규칙) · 유의성 · 위약 · 순 판은 읽기다.
   주식 대리 P1(보유 2012-01 ~ 2016-08)은 [F0] 그 창의 긴 이력판 켜진 달 0 → 같은 규칙으로 «측정 불가»(수익 경로를 짓지 않는다 · 켜진 달 수만 싣는다).
   앞선 지시(모두 유효): ETF · 선물 · 옵션 · 공매도 보유 없음(SPDR 9종은 상태 입력으로만 · 보유는 French 포트폴리오 수익 계열뿐 — 기전 대리) · «백테스트 최대 20년» ·
   «미래 일정 다 꺼»(전방 원장 없음 — data/_q06holdfwd/ 가 있으면 멈춘다) · 사이트는 10년(2016-09 앞 창의 값은 저장소에 싣지 않는다).
🚨 등록 커밋이 origin 에 오르기 전에는 --selftest · --guard · --pins · --manifest · --precommit · --wire · --f0 · --smoke · --fetch-spdr 만 된다.
   --f0 는 상태 개수 · 맞는 달 수 · 시점 단언 · French 핀 · 값이 선 달 수만 · --smoke 는 눈가린 채(산출을 열지 않고 지운다 · 참/거짓 · 초만 싣는다).

  python -X utf8 build/q06hold_run.py --selftest           합성만(실자료 없음)
  python -X utf8 build/q06hold_run.py --guard              사이트 경계(site_guard_std — 참/거짓 · 이름만)
  python -X utf8 build/q06hold_run.py --pins               얼린 파일 · 핀 표(등록 문서 §10 표)
  python -X utf8 build/q06hold_run.py --fetch-spdr         원조 SPDR 9종 긴 이력 판을 저장소 밖 캐시에 한 번 뜬다(있으면 덮지 않는다 · 해시로 핀)
  python -X utf8 build/q06hold_run.py --f0                 등록 전 F0(핀 뿌리 둘 · 수익 없음) — 등록 문서 §10 F0 표 · 엔진 F0_EXPECT 의 출처
  python -X utf8 build/q06hold_run.py --manifest           data/_q06hold_manifest.json(해시만) 쓰기
  python -X utf8 build/q06hold_run.py --wire [--apply]     등록 커밋이 .gitignore · build/validate_site.py 끝에 덧붙일 덩이
  python -X utf8 build/q06hold_run.py --precommit          등록 커밋 직전 점검(참/거짓 · 이름만)
  python -X utf8 build/q06hold_run.py --smoke              러너 경로 전체 눈가린 연기(임시 폴더 · 열지 않고 지운다)
  Q06HOLD_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python -X utf8 build/q06hold_run.py --once     한 번 굽기(이 길 하나뿐)
  python -X utf8 build/q06hold_run.py --public-view        굽기 뒤: 산출 → 게시 칸 다시 쓰기(FINISHED 표식이 있을 때만)
  python -X utf8 build/q06hold_run.py --result-doc [<게시 칸 파일>] [--reg-err <글 파일>] [--write]   결과 문서(게시 칸 파일 하나만 읽는 얼린 렌더러)
  python -X utf8 build/q06hold_run.py --internal-doc       굽기 뒤: 창 값까지 담은 내부 판(저장소 밖 캐시에만 쓴다)

뿌리 둘(모두 저장소 밖 캐시 · git archive · 얼린 blob 단언 · 작업 트리의 data/ 를 읽지 않는다)
  root   얼린 V0 뿌리 = 얼린 x_adapter.build_root(배치 Q 등록 커밋 build/ + 가격 밖 입력 판 data/ + 가격 판 + P3) — 얼린 실운용 Q06 상태 · 긴 이력판 · 통계
  vroot  배치 V 핀 판 = 얼린 x_adapter.build_vroot — French 주 목적지 · 시장(얼린 v_data.l_proxy · ff3 · 배치 V 명세 SHA · CRSP 202608)
저장소 밖 입력(해시로 핀 · 값은 저장소에 없다): 원조 SPDR 긴 이력 판(<캐시>/raw/spdr_long · 묶음 해시) · French 판(배치 V 캐시 · vroot 명세 SHA)

한 번 굽기 규약(egstep_run · dstk_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(실패하면 멈춘다).
  · Q06HOLD_COMMIT = 사전등록 문서 · 러너 · 엔진 · 명세(data/_q06hold_manifest.json)를 **처음 더한** 커밋 · origin/main 의 조상 · 그 커밋의 등록 문서에 빈칸(⟨TBD)과 초안 괄호(U+3014)가 없다.
  · 얼린 파일(엔진 · 러너 · 명세 · 등록 문서 · 덧붙임 두 곳)이 그 커밋과 바이트 단위로 같다(CRLF 무시) · 러너가 부르는 재사용 파일(x_adapter) blob 이 핀과 같다.
  · 판 점검 → 배타 잠금 → F0(핀 뿌리 둘 · 수익 없음 · 등록 F0 개수와 같아야) → 시작 표식 셋(로컬 둘 · origin 태그 q06hold-started · 계산 전에 민다) →
    수익 계열 · 통계 자식 → 게시 칸(공개 안전 점검 · 산출보다 먼저) → 산출 · 게시 칸 · 실행 기록 → FINISHED → 잠금 풀기.
  · FINISHED 가 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤 · 산출 전 기술적 중단이면 이 컴퓨터의 같은 커밋 표식이 있을 때만 Q06HOLD_RERUN=사유 로 처음부터.
  · 앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 <캐시> 에 남은 작업 폴더(q06hold_work_* · q06hold_f0_* · q06hold_runner_smoke_*)는 굽기 · 연기 · F0 가
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
    c = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-Q06HOLD.md")))
    return ("build/" + c[0]) if len(c) == 1 else "build/PREREG-0000-00-00-Q06HOLD.md", len(c)


PREREG, _N_PREREG = _find_prereg()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"
ENGINE = "build/q06hold.py"
RUNNER = "build/q06hold_run.py"
MANIFEST_FILE = "data/_q06hold_manifest.json"
FIRST_ADDED = (PREREG, RUNNER, ENGINE, MANIFEST_FILE)
FROZEN = (ENGINE, RUNNER, MANIFEST_FILE, PREREG)
REPO_ALLOWED_Q06HOLD = (MANIFEST_FILE,)
FORWARD_DIR = "data/_q06holdfwd"                              # 있으면 멈춘다(전방 원장 없음 — 사용자 2026-09-27 «미래 일정 다 꺼»)
# 러너 · 뿌리가 부르는 재사용 파일(작업 트리 = 등록 커밋 판) — git blob(LF 바이트)이 이 값이어야 한다
REUSED_BLOBS = {"build/x_adapter.py": "897c4c94b22e415f38e32ac47bf8037025f28cb2"}      # 배치 X 등록 판(뿌리 짓기 · 배치 V 자료 핀 점검 _v_pins_full)
# 뿌리 핀(재사용 모듈의 상수와 같아야 한다 — pins_check 가 대조)
ROOT_PIN = {"code_pin": "1d81f083a404c68e23d15a649ef6f0a340d4d95c", "build_tree": "e221c9817b8baa4e225e0382ff4cf2c15fbcb8c8",
            "base": "bef4eea8c98572bd05815d44bd0744d9ce7ed370", "price": "940f0bda99ae1cc99299a43a06b30b9fa267d734"}
VROOT_PIN = "c6a35ff0168e5ea21c2ab2d18680550452511a3a"
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
CHILD_ENV_DROP = ("Q06HOLD_COMMIT", "Q06HOLD_RERUN", "Q06HOLD_SMOKE", "LAB_ASOF", "VBATCH_CACHE", "VBATCH_FRENCH_SEED", "EGSTEP_COMMIT", "DSTK_COMMIT")
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"
SMOKE_ENV_KEYS = ("Q06HOLD_SMOKE",)
TIMEOUT = 3 * 3600
# 등록 상수 — 엔진(q06hold)의 값과 같아야 굽는다(등록 문서 §3 ~ §9)
REGISTERED = {
    "HOLD": ("2006-09", "2016-08"), "FORM_FIRST": "2006-08", "FORM_LAST": "2016-07", "N_HOLD": 120,
    "REF_HOLD": ("2016-09", "2026-08"), "REF_FIRST": "2016-08", "REF_LAST": "2026-07", "N_REF": 120,
    "P1_FIRST": "2011-12", "P1_LAST": "2016-07", "N_P1": 56,
    "COST": 0.0010, "LEGS": 2, "HAC_LAG": 3, "K_PLACEBO": 10000, "SEED": 20260930, "PCT_READ": 95.0, "ALPHA_READ": 0.05, "F0_MIN_ON": 6,
    "SPDR_LONG_N": 9, "SPDR_LONG_FIRST": "1998-12-22", "SPDR_LONG_END": "2026-08-31",
    "SPDR_LONG_DIGEST": "4a01c8502dcf17fdf87f169fb7111046419b551b4a0699d9bf68e4be71fc4f2b",
    "COUNTED": ("F_HOLD", "T1_HOLD", "T2_HOLD", "KT_HOLD", "F_REF"), "N_ROWS_COUNTED": 5, "CUM_N_BEFORE": 1058,
    "EGSTEP_REF_STATES": {"n": 120, "on": 22, "switch": 23, "runs": 12, "t1": 35, "t2": 13},
    "Q06_EXPECT": {"SPDR": ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"), "D0": "2006-01-04", "S0": "2009-01-02",
                   "WMIN": 756, "WMAX": 2520, "PCT": 80, "NMIN_M": 36, "M0": "2009-01", "F0_MIN": 6},
    "ROOT_BLOBS": {"qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "q_switch": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
                   "q_corrsurp": "d32a270e2db0682f8b940ffe647607d15b57ba52", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
                   "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea"},
    "VROOT_BLOBS": {"v_cards": "aadaf24f173579d3f3146014aa150a4ca07eb0a5", "v_core": "bdba648f1d790748cd5008ceeea3c5eee9d733c8",
                    "v_data": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a", "v_pit": "5983b9902b106a2b234db05a397e9ce0b73fb689",
                    "v_fund": "2d8093f0009c09b05f597e07eea10f53c8d18b8e", "v_px_split": "c747ae4030c4f2f5bc97b8e634f3a80a36d04028",
                    "v_cond": "d25914deb89490410ea2dca56b5999356628821e", "pit_panel": "e207370369aaa2d71d92dcac4ecbcd79d0df9b38",
                    "pit_alias": "ead714d97c87c3588a8fdc2ca4b1c57c5a497c0b", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
                    "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea",
                    "pit_quarantine": "329e5d9ff15be4c07052921dfff9a41afbcc2513", "stoploss": "e2408e98d03216146cf809d6643c68947130c727",
                    "tech_backtest": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79", "x_adapter": "897c4c94b22e415f38e32ac47bf8037025f28cb2"},
    "F0_EXPECT": {"spdr_digest16": '4a01c8502dcf17fd', "spdr_n": 9, "spdr_first": '1998-12-22', "spdr_days": 6964, "long_d0": '1998-12-23', "long_s0": '2001-12-28',
                  "long_m0": '2001-12', "long_first_hi": '2004-11', "long_timing_ok": True, "hold_n": 120, "hold_on": 7, "hold_switch": 10,
                  "hold_runs": 5, "hold_t1": 29, "hold_t2": 22, "hold_pre": 0, "hold_post": 0, "hold_f0_rule_ok": True,
                  "p1win_on": 0, "p1win_switch": 0, "long_ref_on": 18, "long_ref_switch": 19, "agree_ref": 116, "agree_both_on": 18,
                  "frozen_timing_ok": True, "ref_on": 22, "ref_switch": 23, "ref_runs": 12, "ref_t1": 35, "ref_t2": 13,
                  "ref_pre": 0, "ref_same_as_record": True, "ref_same_as_egstep": True, "frozen_old_on": 5, "fr_pins_ok": True, "fr_months": 240,
                  "fr_crsp": '202608'},
}
FORBIDDEN_ENGINE_NAMES = ("ff1", "ff2", "ff0", "forward_ledger", "genesis")    # 전방 판정 · 원장 함수가 엔진에 없어야 한다


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록 · 임시 뿌리 · 뜬 판은 모두 저장소 밖(<캐시>)
# ══════════════════════════════════════════════════════════════════════════
CACHE = os.environ.get("Q06HOLD_CACHE") or os.path.join(tempfile.gettempdir(), "q06hold_cache")
GIT_MARK_NAME = "q06hold_started"
START_TAG = "q06hold-started"
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}
OUT_NAMES = {"out": "_q06holdout.json", "mark": "_q06holdout.started", "runlog": "_q06holdout.run.json", "public": "_q06holdout.public.json",
             "internal": "_q06holdout.internal.md"}
CACHE_ONLY_KEY = "__q06hold_cache_only__"
PUBLIC_FROM = "2016-09"
PUBLIC_FLOAT_KEYS = re.compile(r"(^|_)(coverage|frac|tol|min|max|thr|sec)(_|$)")
COUNT_KEYS = re.compile(r"(^n$|^n_|_n$|count|^k$|months?$|days?$|years?$|^rows$|bytes$|names|forms)")
OUTPUT_NAME_MARKS = ("_q06holdout",)
OUTPUT_CONTENT_MARKS = (CACHE_ONLY_KEY.encode(), b"_q06holdout.json", b"_q06holdout.public.json", b"_q06holdout.run.json", b'"q06hold_public_view"',
                        b"_q06holdout.internal.md")
SPDR_LONG = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")   # 원조 SPDR 9종(얼린 q_corrsurp.SPDR 와 같다 · 상태 입력으로만)
SPDR_END = "2026-08-31"                                                      # 뜬 판의 끝 날(표본 안 참고의 마지막 결정 2026-07 뒤 한 달 여유)
SPDR_DIR = os.path.join(CACHE, "raw", "spdr_long")
SPDR_DIGEST = "4a01c8502dcf17fdf87f169fb7111046419b551b4a0699d9bf68e4be71fc4f2b"   # 뜬 판 묶음 해시(2026-09-28 에 떴다 · 아홉 파일 · 1998-12-22 ~ 2026-08-31)
SPDR_N = 9


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
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith("_q06holdout") and (f.endswith(".json") or f.endswith(".part"))]
    return sorted({p for p in have if os.path.exists(p)})


STALE_PREFIXES = ("q06hold_work_", "q06hold_f0_", "q06hold_runner_smoke_")


def _stale_dirs(cache):
    if not os.path.isdir(cache):
        return []
    return sorted(os.path.join(cache, d) for d in os.listdir(cache)
                  if d.startswith(STALE_PREFIXES) and os.path.isdir(os.path.join(cache, d)))


def purge_stale(cache=None):
    """앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 <캐시> 바로 밑에 남은 작업 폴더를 열지 않고 지운다 — 개수만 돌려준다(이름 · 크기 · 값 없음).
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
        if f.startswith("data/_q06hold") and f not in REPO_ALLOWED_Q06HOLD:
            bad.append("허용 밖 파일: %s" % f)
        if f.startswith(FORWARD_DIR + "/") or f == FORWARD_DIR:
            bad.append("전방 원장 파일(사용자 2026-09-27 «미래 일정 다 꺼»): %s" % f)
        if "q06hold_cache" in f or "spdr_long" in f:
            bad.append("캐시 사본으로 보이는 파일: %s" % f)
    return bad


def site_guard_std(root=None):
    """Q06HOLD 사이트 경계 — git 이 추적 · 추가 예정인 파일 가운데 (가) 굽기 산출 이름(_q06holdout*) (나) 허용 밖 data/_q06hold* (다) 전방 원장 data/_q06holdfwd/*
    (라) 캐시 사본(q06hold_cache · 뜬 SPDR 판) (마) 명세(data/_q06hold_manifest.json)가 해시만인가 (바) 사이트 자료(뿌리 *.html · js/*.js · data/*.json)의 굽기 산출 표식."""
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
            bad.append("사이트 자료 %s 에 Q06HOLD 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


# ── 덧붙임 두 곳(.gitignore · validate_site) ─────────────────────────────
GITIGNORE_BLOCK = """
# Q06 방어 스텝 방아쇠 기전 검정(PREREG-*-Q06HOLD · 랩이 안 본 창) — 굽기 산출(_q06holdout.json · _q06holdout.public.json · _q06holdout.run.json ·
#   _q06holdout.started · _q06holdout.internal.md)이나 캐시 사본(q06hold_cache · 뜬 SPDR 긴 이력 판)이 작업 트리에 복사돼도 쓸려 들지 않게.
#   명세(data/_q06hold_manifest.json)는 «_q06hold_» 라 걸리지 않는다.
_q06holdout*
q06hold_cache/
"""
VALIDATE_BLOCK = """
# ── Q06 방어 스텝 방아쇠 기전 검정(PREREG-*-Q06HOLD · 랩이 안 본 창) 사이트 경계 ─────────────────────────────
# 굽기 산출(_q06holdout*)이 저장소 · 사이트 자료에 없어야 한다(창이 2016-09 앞이라 값은 캐시에만 · 사이트는 10년). data/_q06hold* 는 해시만 담은
#   명세(_q06hold_manifest) 하나뿐 · data/_q06holdfwd/ 없음(전방 원장 없음 · 사용자 2026-09-27 «미래 일정 다 꺼») · 사이트 자료에 굽기 산출 표식 없음.
#   build/q06hold_run.py 는 모듈 머리에서 표준 라이브러리만 불러온다(site_guard_std). 러너(q06hold_run.frozen_check)도 같은 함수를 부른다.
try:
    import importlib as _il_q06h
    _q6r = _il_q06h.import_module("q06hold_run")
    _gq6 = _q6r.site_guard_std(ROOT)
    if not _gq6["ok"]:
        errors.append("Q06 방아쇠 기전 검정 사이트 경계 위반 %d건 — %s. 굽기 산출(_q06holdout*)은 저장소 밖 캐시에만 둔다"
                      % (_gq6.get("n_bad", len(_gq6["bad"])), " · ".join(_gq6["bad"][:4])))
    else:
        print("  ~ Q06 방아쇠 기전 검정 사이트 경계 통과(파일 %d · 사이트 자료 %d 훑음)" % (_gq6["n_files"], _gq6["n_scanned"]))
except Exception as _e:
    # 닫힌 쪽 — 이 경계를 확인하지 못하면 통과시키지 않는다(EGSTEP · DSTK 와 같은 규약)
    errors.append("Q06 방아쇠 기전 검정 사이트 경계 검사가 예외로 죽었다 — %s (확인하지 못하면 통과시키지 않는다)" % str(_e)[:80])
"""
_VALIDATE_ANCHOR = 'print("사이트 검증:"'


def wire_texts(gitignore_txt, validate_txt):
    g = gitignore_txt
    if "_q06holdout*" not in g:
        g = g.rstrip("\n") + "\n" + GITIGNORE_BLOCK
    v = validate_txt
    if "Q06 방어 스텝 방아쇠 기전 검정(PREREG-*-Q06HOLD" not in v:
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
#  이름 · 등록 상수 · 재사용 blob · 핀 · 저장소 밖 입력 · 명세
# ══════════════════════════════════════════════════════════════════════════
def name_check():
    bad = []
    if _N_PREREG != 1:
        bad.append("build/PREREG-*-Q06HOLD.md 가 %d 개" % _N_PREREG)
    elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-Q06HOLD\.md", PREREG):
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
        import q06hold as E
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
    if SPDR_DIGEST != getattr(E, "SPDR_LONG_DIGEST", None) or SPDR_N != getattr(E, "SPDR_LONG_N", None) or tuple(SPDR_LONG) != tuple(E.Q06_EXPECT["SPDR"]):
        bad.append("러너의 SPDR 판 상수가 엔진과 다르다")
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


def pins_check():
    """뿌리 핀 둘 — 재사용 모듈의 상수와 같고 · 커밋이 있고 origin/main 의 조상이며 · 트리가 등록 값과 같다(git 개체만 · 자료를 열지 않는다)."""
    bad = reused_problems()
    if bad:
        return bad
    XA = _XA()
    if (XA.CODE_PIN, XA.BUILD_TREE, XA.P1_BASE, XA.P1_PRICE) != (ROOT_PIN["code_pin"], ROOT_PIN["build_tree"], ROOT_PIN["base"], ROOT_PIN["price"]):
        bad.append("x_adapter 뿌리 핀이 등록 값과 다르다")
    if XA.DATA_PIN != VROOT_PIN:
        bad.append("x_adapter 배치 V 핀이 등록 값과 다르다")
    want_v = dict(XA.V_FROZEN)
    want_v.update(XA.DBOOK_FROZEN)
    if any(REGISTERED["VROOT_BLOBS"].get(k) != v for k, v in want_v.items()):
        bad.append("vroot 얼린 blob 표가 x_adapter 의 V_FROZEN · DBOOK_FROZEN 과 다르다")
    for nm, c in (("root code", ROOT_PIN["code_pin"]), ("root base", ROOT_PIN["base"]), ("root price", ROOT_PIN["price"]), ("vroot", VROOT_PIN)):
        if _git("cat-file", "-e", c + "^{commit}").returncode != 0:
            bad.append("%s 핀 커밋 %s 가 없다" % (nm, c[:9]))
        elif _git("merge-base", "--is-ancestor", c, "origin/main").returncode != 0:
            bad.append("%s 핀 커밋 %s 가 origin/main 의 조상이 아니다" % (nm, c[:9]))
    if _git("rev-parse", "%s:build" % ROOT_PIN["code_pin"]).stdout.strip() != ROOT_PIN["build_tree"]:
        bad.append("root 코드 핀의 build 트리가 다르다")
    for m, b in REGISTERED["VROOT_BLOBS"].items():
        if m == "x_adapter":
            continue
        if _git("rev-parse", "%s:build/%s.py" % (VROOT_PIN, m)).stdout.strip() != b:
            bad.append("vroot 핀 커밋의 build/%s.py blob 이 등록 값과 다르다" % m)
    for m, b in REGISTERED["ROOT_BLOBS"].items():
        if _git("rev-parse", "%s:build/%s.py" % (ROOT_PIN["code_pin"], m)).stdout.strip() != b:
            bad.append("root 코드 핀의 build/%s.py blob 이 등록 값과 다르다" % m)
    return bad


def bundle_digest_std(tickers, d):
    """묶음 해시 — sha256(«티커\\t파일 sha256\\n» 을 티커 차례로 · 파일 이름은 «^» → «_» · 얼린 dstk.vd1_digest 와 같은 규칙) · 선 파일 수 · 없는 파일 수."""
    lines, miss = [], 0
    for t in sorted(tickers):
        p = os.path.join(d, t.replace("^", "_") + ".csv")
        if not os.path.exists(p):
            miss += 1
            continue
        lines.append("%s\t%s\n" % (t, _sha_file(p)))
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest(), len(lines), miss


def spdr_digest_std(d=None):
    """원조 SPDR 긴 이력 판 묶음 해시(V-D1 과 같은 규칙 · 파일 = <티커>.csv)."""
    return bundle_digest_std(list(SPDR_LONG), d or SPDR_DIR)


def fetch_spdr_long(dest=None):
    """🚨 입력 자료 한 번 뜨기(등록 전 · 수익 통계 아님) — 원조 SPDR 9종의 상장부터 SPDR_END 까지 일간 수정종가(yfinance Ticker.history
    period='max' · auto_adjust=True — 배당 · 분할 조정)를 저장소 밖 캐시에 CSV(Date,Close)로 쓴다. 이미 있으면 덮지 않는다(판 동결 · 해시로 핀).
    돌려주는 것: 파일 수 · 첫 날 · 끝 날 · 묶음 해시(값 없음)."""
    import yfinance as yf
    d = dest or SPDR_DIR
    if _inside(d, ROOT):
        raise SystemExit("🚨 SPDR 판 폴더가 저장소 안이다.")
    os.makedirs(d, exist_ok=True)
    have = [t for t in SPDR_LONG if os.path.exists(os.path.join(d, t + ".csv"))]
    if have:
        raise SystemExit("🚨 SPDR 판이 이미 있다(%s) — 판 동결 · 덮지 않는다." % ", ".join(have))
    meta = {}
    for t in SPDR_LONG:
        df = yf.Ticker(t).history(period="max", auto_adjust=True, actions=False)
        rows = []
        for ts, v in zip(df.index, df["Close"].tolist()):
            ds = ts.strftime("%Y-%m-%d")
            if ds <= SPDR_END and v == v:
                rows.append("%s,%r\n" % (ds, float(v)))
        txt = "Date,Close\n" + "".join(rows)
        with io.open(os.path.join(d, t + ".csv"), "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        meta[t] = {"n": len(rows), "first": rows[0][:10] if rows else None, "last": rows[-1][:10] if rows else None,
                   "sha256": hashlib.sha256(txt.encode("utf-8")).hexdigest()}
        time.sleep(0.6)
    dg, n, miss = spdr_digest_std(d)
    import yfinance
    _write_text(os.path.join(d, "_index.json"), json.dumps({"source": "yfinance Ticker.history(period='max', auto_adjust=True, actions=False) · Close",
                                                            "yfinance": yfinance.__version__, "fetched_at": _now(), "end": SPDR_END,
                                                            "files": meta, "digest": dg}, ensure_ascii=False, indent=1) + "\n")
    return {"n": n, "missing": miss, "digest": dg, "first": sorted({m["first"] for m in meta.values()}), "last": sorted({m["last"] for m in meta.values()})}


def ext_problems():
    """저장소 밖 입력 — 원조 SPDR 긴 이력 판 묶음 해시(주 통계의 상태 입력). French 판은 vroot 자식이 배치 V 명세 SHA 로 점검한다(F0 · 굽기)."""
    bad = []
    if _inside(SPDR_DIR, ROOT):
        bad.append("SPDR 판 폴더가 저장소 안이다")
    else:
        dg, n, miss = spdr_digest_std()
        if SPDR_DIGEST is None or dg != SPDR_DIGEST or n != SPDR_N or miss:
            bad.append("원조 SPDR 긴 이력 판 묶음 해시 · 파일 수가 등록 값과 다르다(--fetch-spdr 로 뜬 판 그대로여야)")
    return bad


def manifest_doc():
    """data/_q06hold_manifest.json — 해시만(값 없음)."""
    XA = _XA()

    def rp(c, spec):
        r = _git("rev-parse", "%s:%s" % (c, spec))
        return r.stdout.strip() if r.returncode == 0 else None
    return {"kind": "q06hold_manifest", "note": "Q06 방어 스텝 방아쇠 기전 검정(Q06HOLD) 명세 — 해시만(값 없음). 러너 판 점검이 이 파일을 등록 커밋 판과 대조한다.",
            "prereg": PREREG, "engine": ENGINE, "runner": RUNNER,
            "code_sha256_lf": {p: (_sha_lf(_bytes(os.path.join(ROOT, *p.split("/")))) if os.path.exists(os.path.join(ROOT, *p.split("/"))) else None)
                               for p in (ENGINE, RUNNER)},
            "reused_blobs": dict(REUSED_BLOBS),
            "spdr_long": {"source": "yfinance Ticker.history(period='max', auto_adjust=True, actions=False) · Close · 저장소 밖 캐시에만(값은 싣지 않는다)",
                          "tickers": list(SPDR_LONG), "end": SPDR_END, "digest_rule": "sha256(티커\\t파일 sha256\\n · 티커 차례)", "digest": SPDR_DIGEST,
                          "n_files": SPDR_N},
            "roots": {"root": {"code_pin": ROOT_PIN["code_pin"], "build_tree": ROOT_PIN["build_tree"], "base": ROOT_PIN["base"], "price": ROOT_PIN["price"],
                               "p3": dict(XA.P3), "frozen_blobs": dict(XA.ROOT_FROZEN), "engine_asserts": dict(REGISTERED["ROOT_BLOBS"]),
                               "builder": "x_adapter.build_root"},
                      "vroot": {"data_pin": VROOT_PIN, "v_frozen": dict(XA.V_FROZEN), "dbook_frozen": dict(XA.DBOOK_FROZEN),
                                "engine_asserts": dict(REGISTERED["VROOT_BLOBS"]), "builder": "x_adapter.build_vroot",
                                "children": "q06hold --child f0v · leg(French) — root 자식 st 가 vroot 의 data/_qbatch.json(배치 Q 기록 신호 달)을 읽는다",
                                "read_files_blob": {f: rp(VROOT_PIN, f) for f in ("data/_vb_manifest.json", "data/_qbatch.json")},
                                "french": "v_data.l_proxy(\"V02\") · ff3(\"m\") — French 판 SHA · CRSP 202608 은 data/_vb_manifest.json(위 blob)이 핀한다"}},
            "start_tag": START_TAG, "git_mark": GIT_MARK_NAME, "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼»"}


def write_manifest():
    doc = manifest_doc()
    bad = manifest_problems(doc)
    if bad:
        raise SystemExit("🚨 명세가 해시만이 아니다: %s" % bad[:3])
    miss = [k for k, v in doc["roots"]["vroot"]["read_files_blob"].items() if v is None]
    if miss:
        raise SystemExit("🚨 vroot 핀 커밋에 없는 파일: %s" % ", ".join(miss))
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
    for k in ("reused_blobs", "roots", "prereg", "start_tag", "spdr_long"):
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
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 Q06HOLD_RERUN=사유 로 처음부터." % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 Q06HOLD_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다.")
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
    """시작 태그를 민다. 이미 같은 커밋을 가리키면 Q06HOLD_RERUN(산출 전 기술적 중단의 다시 굽기)일 때만 «already» — 아니면 멈춘다(동시 굽기 막기)."""
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
            raise SystemExit("🚨 origin 시작 태그가 이미 이 커밋을 가리킨다 — 다른 굽기가 시작했다(Q06HOLD_RERUN 이 아니면 굽지 않는다).")
        return "already"
    if have is not None:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다." % have[:8])
    r1 = _git("tag", "-f", START_TAG, commit)
    r2 = _git("push", "--quiet", "origin", "refs/tags/%s:refs/tags/%s" % (START_TAG, START_TAG))
    if r1.returncode != 0 or r2.returncode != 0 or _remote_start_tag() != commit:
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다 — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 Q06HOLD_RERUN).")
    return "pushed"


LOCK_NAME = "_q06hold_bake.lock"


def _take_lock(P, commit):
    """배타 잠금(O_EXCL) — 판 점검 뒤 · 핀 뿌리 F0 전에 잡는다. 두 번째 --once 는 여기서 멈춘다(동시 굽기 막기).
    과정이 강제로 죽으면 잠금이 남는다 — 다른 굽기가 돌지 않음을 확인하고 지운 뒤 Q06HOLD_RERUN=사유 로."""
    lk = os.path.join(P["dir"], LOCK_NAME)
    try:
        fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("🚨 굽기 잠금이 있다(%s) — 다른 굽기가 돌고 있다. 돌고 있지 않으면 확인 뒤 지우고 Q06HOLD_RERUN=사유 로." % lk)
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
#  핀 판 임시 뿌리 둘 · 자식 과정
# ══════════════════════════════════════════════════════════════════════════
def build_roots(work):
    """뿌리 둘(저장소 밖) — root = 얼린 x_adapter.build_root · vroot = 얼린 x_adapter.build_vroot. 둘 모두에 엔진(등록 커밋 판 · 작업 트리)을 build/ 에 넣는다."""
    if _inside(work, ROOT):
        raise SystemExit("🚨 임시 뿌리가 저장소 안이다.")
    t0 = time.time()
    XA = _XA()
    rr = os.path.join(work, "r")
    vr = os.path.join(work, "v")
    os.makedirs(rr, exist_ok=True)
    os.makedirs(vr, exist_ok=True)
    root, _rep = XA.build_root(rr, ROOT, force=True)
    vroot, _vrep = XA.build_vroot(vr, ROOT, force=True)
    for tree in (root, vroot):
        shutil.copyfile(os.path.join(ROOT, *ENGINE.split("/")), os.path.join(tree, *ENGINE.split("/")))
    return {"root": root, "vroot": vroot, "sec": round(time.time() - t0, 1)}


def _child_env():
    env = dict(os.environ)
    for k in CHILD_ENV_DROP + SMOKE_ENV_KEYS:
        env.pop(k, None)
    env.update(ENV_PINS)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "MKL_NUM_THREADS": "1"})
    return env


def _run(cmd, cwd, out_path, what, timeout=TIMEOUT):
    t = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=_child_env(), capture_output=True, timeout=timeout)
    sec = round(time.time() - t, 1)
    if r.returncode != 0 or not os.path.exists(out_path):
        tail = _scrub(r.stderr.decode("utf-8", "replace"))[-2500:]
        raise SystemExit("🚨 자식 과정(%s) 실패 — 산출을 쓰지 않았다:\n%s" % (what, tail))
    return sec


def run_engine_child(tree, mode, job, work):
    """엔진 자식 — python -X utf8 <뿌리>/build/q06hold.py --child <mode> --job <작업> --out <산출>(작업 폴더 · 캐시)."""
    jp = os.path.join(work, "job_%s.json" % mode)
    op = os.path.join(work, "out_%s.json" % mode)
    _write_json(jp, job)
    sec = _run([sys.executable, "-X", "utf8", os.path.join(tree, *ENGINE.split("/")), "--child", mode, "--job", jp, "--out", op], tree, op, mode)
    return op, sec


F0_PUB_KEYS = ("ok", "bad", "st", "french", "signature", "expect_diff")


def merge_f0(st, fv):
    """F0 합치기(순수) — 상태(root · 긴 이력판 · 얼린 실운용) · French(vroot) · 서명 · 등록 F0 대조. 🚨 상태 날짜는 싣지 않는다(개수만)."""
    import q06hold as E
    R0 = {"st": {"long": st["long"], "frozen": st["frozen"]}, "french": fv["french"]}
    L, Fz = st["long"], st["frozen"]
    bad = []
    if L.get("digest") != E.SPDR_LONG_DIGEST or L.get("n_files") != E.SPDR_LONG_N:
        bad.append("뜬 SPDR 판 묶음 해시가 등록과 다르다")
    if not L.get("timing_ok") or not Fz.get("timing_ok"):
        bad.append("Q06 시점 단언 실패(긴 이력판 · 얼린 실운용)")
    if L.get("first_hi") is None or L["first_hi"] > E.mshift(E.FORM_FIRST, -1):
        bad.append("긴 이력판이 창 첫 결정 앞 달보다 늦게 선다(창을 늦춰야 한다)")
    if L.get("d_first") != E.SPDR_LONG_FIRST:
        bad.append("뜬 판 첫 날이 등록과 다르다")
    if not Fz.get("ref_same_as_record") or not Fz.get("ref_same_as_egstep"):
        bad.append("표본 안 얼린 실운용 상태가 배치 Q 기록 · EGSTEP F0 와 다르다")
    if (L.get("hold") or {}).get("n") != E.N_HOLD or (L.get("ref") or {}).get("n") != E.N_REF or (L.get("p1win") or {}).get("n") != E.N_P1:
        bad.append("긴 이력판 창 · 표본 안 · P1 창 달 수가 등록과 다르다")
    if not fv["french"]["pins_ok"] or fv["french"]["n_months"] != E.N_HOLD + E.N_REF:
        bad.append("French 핀 · 보유월 개수가 등록과 다르다")
    R0["signature"] = E.f0_signature(R0)
    if E.F0_EXPECT is not None:
        sig = R0["signature"]
        diff = sorted(k for k in set(sig) | set(E.F0_EXPECT) if sig.get(k) != E.F0_EXPECT.get(k))
        R0["expect_diff"] = diff
        if diff:
            bad.append("등록 F0 개수와 다름(%s)" % ", ".join(diff[:6]))
    R0["bad"] = bad
    R0["ok"] = not bad
    return R0


def preflight(work):
    """F0(핀 뿌리 둘 · 수익 없음 · 등록 F0 개수 대조) — 통과해야 표식을 쓴다. 상태 산출은 굽기가 그대로 이어 쓴다."""
    t0 = time.time()
    R = build_roots(work)
    sec = {"roots": R["sec"]}
    qb = os.path.join(R["vroot"], "data", "_qbatch.json")
    p_st, sec["st"] = run_engine_child(R["root"], "st", {"qbatch": qb, "spdr_dir": SPDR_DIR}, work)
    p_fv, sec["f0v"] = run_engine_child(R["vroot"], "f0v", {"root": R["vroot"]}, work)
    st, fv = _read_json(p_st), _read_json(p_fv)
    f0 = merge_f0(st, fv)
    if not f0.get("ok"):
        raise SystemExit("🚨 F0 실패 — %s (굽지 않는다)" % "; ".join(f0.get("bad") or ["?"]))
    sec["total"] = round(time.time() - t0, 1)
    return {"f0": f0, "roots": R, "st": p_st, "sec": sec}


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def frozen_check(env=None):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("Q06HOLD_COMMIT")
    if not c:
        raise SystemExit("🚨 Q06HOLD_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --pins · --f0 · --manifest · --precommit · --smoke 만 된다.")
    nb = name_check()
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_Q06HOLD_NO_FETCH"):
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
    rerun = env.get("Q06HOLD_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag() if (real or not env.get("_Q06HOLD_NO_FETCH")) else env.get("_Q06HOLD_REMOTE_TAG")
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
        raise SystemExit("🚨 덧붙임 두 곳이 붙지 않았다(.gitignore %s · validate_site %s) — `q06hold_run.py --wire --apply` 를 등록 커밋에." % (gw, vw))
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
    if smoke and not os.path.basename(os.path.dirname(os.path.abspath(P["dir"]))).startswith("q06hold_runner_smoke_"):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/q06hold_runner_smoke_*/out 이 아니다.")
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
    """굽기 자식 둘 — 수익 계열(vroot · leg: French 주 목적지 · 시장) → 통계(root · stat)."""
    import q06hold as E
    R = pf["roots"]
    sec = {}
    fx = E.F0_EXPECT or {}
    p_lg, sec["leg"] = run_engine_child(R["vroot"], "leg", {"root": R["vroot"]}, work)
    p_s, sec["stat"] = run_engine_child(R["root"], "stat", {"leg": p_lg, "st": pf["st"], "f0_expect": fx}, work)
    main = _read_json(p_s)
    series = main.pop("series", None)
    return main, series, sec


def _bake_locked(P, commit, rerun, smoke, t0, n_stale=0):
    work = tempfile.mkdtemp(prefix="q06hold_work_", dir=os.path.dirname(P["dir"]) if smoke else cache_guard_std())
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
            raise SystemExit("🚨 굽기 계산 실패 — 산출을 쓰지 않았다(산출 전 기술적 중단이면 Q06HOLD_RERUN=사유 로 처음부터 · 같은 얼린 코드로만):\n%s" % str(e)[-2000:])
        out = {CACHE_ONLY_KEY: True, "kind": "q06hold_bake", "prereg": PREREG, "prereg_commit": commit, "smoke": smoke,
               "pins": {"root": ROOT_PIN, "vroot": VROOT_PIN, "spdr_long": SPDR_DIGEST}, "f0": pf["f0"], "main": main, "series": series}
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
                  "pins": {"root": ROOT_PIN, "vroot": VROOT_PIN, "spdr_long": SPDR_DIGEST}, "code_sha": code_shas(), "registration_error": err,
                  "smoke": smoke, "stale_deleted": int(n_stale),
                  "note": "값 없음 — 결과는 _q06holdout.public.json 의 칸만 결과 문서로 옮긴다(등록 §7 공개 규칙 · 창 값은 캐시 내부 판에만)"}
        _write_text(P["runlog"], json.dumps(runlog, ensure_ascii=False, indent=1) + "\n")
        _mark_finished(P, sha)
        if not smoke:
            print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서 · 내부 판에서)" % (P["out"], sha[:16], runlog["sec"]))
        return runlog
    finally:
        shutil.rmtree(work, ignore_errors=True)


def once():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("Q06HOLD_RERUN"))


# ══════════════════════════════════════════════════════════════════════════
#  게시 칸 — 창(2006-09 ~ 2016-08)은 부호 · 참/거짓 · 개수 · 상태 날짜만 · 표본 안 참고(2016-09 ~)는 값까지(사이트 10년 규칙)
# ══════════════════════════════════════════════════════════════════════════
def _sign(x):
    return None if x is None else bool(x > 0)


def _row_pub(x):
    return {"sign_pos": _sign(x.get("delta")), "net_sign_pos": _sign(x.get("delta_net")), "n_on": x.get("n_on"), "n_off": x.get("n_off"),
            "n_entry": x.get("n_entry"), "n_exit": x.get("n_exit")}


def _hold_public(H):
    """창 칸(공개) — 실수 없음: 부호 · 문턱 넘음(참/거짓) · 개수 · 씨앗 · 상태 날짜만. 값은 캐시 내부 판에만."""
    import q06hold as E
    pr, pl, crit = H["primary"], H["placebo"], H.get("t_crit")
    kt, fa, p1 = H["kt"], H["fa"], H.get("p1") or {}
    p1p = {"window": list(p1.get("window") or []), "n": p1.get("n"), "n_on": p1.get("n_on"), "n_on_frozen": p1.get("n_on_frozen"),
           "measurable": p1.get("measurable")}
    return {"window": list(H["window"]), "n": H["n"], "states": H["states"], "pre": H["pre"], "post": H["post"], "f0_rule_ok": H["f0_rule_ok"],
            "on_months": list(H.get("on_months") or []),
            "primary": dict(_row_pub(pr), t_ge_crit=(None if (pr.get("t") is None or crit is None) else bool(pr["t"] >= crit)),
                            p_lt_alpha=(None if pr.get("p") is None else bool(pr["p"] < E.ALPHA_READ)), df=pr.get("df"), hac_b_eq_delta=pr.get("hac_b_eq_delta")),
            "placebo": {"k": pl["k"], "seed": pl["seed"], "n_distinct": pl["n_distinct"],
                        "pct_ge95": (None if pl.get("pct") is None else bool(pl["pct"] >= E.PCT_READ))},
            "kt": {"direction_ok": kt.get("direction_ok"), "n_on": kt.get("n_on"), "n_off": kt.get("n_off")},
            "fa": {"n": fa["n"], "n_up": fa["n_up"], "n_on": fa["n_on"], "n_on_up": fa["n_on_up"], "n_on_down": fa["n_on_down"],
                   "fa_cost_neg": fa.get("fa_cost_neg"), "ta_benefit_pos": fa.get("ta_benefit_pos"), "fa_share_lt_base": fa.get("fa_share_lt_base")},
            "t1": _row_pub(H["t1"]), "t2": _row_pub(H["t2"]), "p1": p1p,
            "t2_below_primary": (None if (H["t2"].get("delta") is None or pr.get("delta") is None) else bool(H["t2"]["delta"] < pr["delta"]))}


def _ref_public(Rf):
    keep = ("n", "n_on", "n_off", "delta", "mean_on", "mean_off", "delta_net", "mean_on_net", "t", "p", "df", "n_entry", "n_exit")
    return {"window": list(Rf["window"]), "n": Rf["n"], "states": Rf["states"], "f": {k: Rf["f"].get(k) for k in keep}, "kt": Rf["kt"], "fa": Rf["fa"],
            "on_months_frozen": list(Rf.get("on_months_frozen") or []), "on_months_long": list(Rf.get("on_months_long") or []),
            "agree": dict(Rf.get("agree") or {})}


def public_doc(out, sha=None, nbytes=None, rec=None):
    """게시 칸 — 결과 문서가 옮길 수 있는 칸만. public_safe_std 를 통과해야 쓴다(계열 · 창의 값은 싣지 않는다)."""
    rec = rec or {}
    f0, M = out.get("f0") or {}, out.get("main") or {}
    f0p = {k: f0.get(k) for k in F0_PUB_KEYS if k in f0}
    f0p["window"] = ["1998-12", "2016-08"]                     # F0 칸에는 창 앞 달의 실수가 없다(개수 · 참/거짓 · 해시 · 날짜)
    v = "보류" if M.get("stopped") else M.get("verdict")
    import q06hold as E
    pv = {"q06hold_public_view": True, "prereg": out.get("prereg"), "prereg_commit": rec.get("commit"), "out_sha256": sha, "out_bytes": nbytes,
          "smoke": bool(rec.get("smoke")), "registration_error": list(rec.get("registration_error") or []),
          "stale_deleted": int(rec.get("stale_deleted") or 0), "stopped": M.get("stopped"), "pins": out.get("pins"), "f0": f0p,
          "verdict": v, "verdict_line": E.verdict_line(v),
          "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼» (전방 원장 · 날짜가 박힌 미래 판정 없음)",
          "public_rule": "창(2006-09 ~ 2016-08)은 사이트 10년 창 앞이라 값을 싣지 않는다 — 부호 · 참/거짓 · 개수 · 상태 날짜만 · 값은 저장소 밖 캐시의 내부 판에만"}
    if not M.get("stopped"):
        pv.update({"hold": _hold_public(M["hold"]), "ref": _ref_public(M["ref"]), "predictions": M.get("predictions"),
                   "multiplicity": M.get("multiplicity")})
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
PRED_KO = {"P1_gross_pos": "P1 주 통계(창 · French · 총) 점 추정 > 0(Kinlaw–Turkington 기전)",
           "P2_not_significant": "P2 주 통계의 한쪽 p ≥ 0.05(힘이 모자란다)",
           "P3_kt_direction_ok": "P3 KT 시장 방향이 선다(켜진 뒤 시장 초과 < 꺼진 뒤)",
           "P4_t2_below_primary": "P4 쌍둥이 T2(HighMS ∧ CS ≤ 1)의 Δ < 주 통계(카드 기전 — 전형적 상관 동요 뒤는 반등)",
           "P5_net_same_sign": "P5 순 판(교체마다 20bp)의 부호 = 총 부호",
           "P6_fa_share_below_base": "P6 헛경보 몫(켜진 달 가운데 시장이 오른 몫) < 바탕(오른 달 몫)",
           "P7_ref_pos": "P7 표본 안 참고(French · 얼린 실운용 상태)의 총 Δ_timing > 0"}
ROW_KO = {"primary": "주 통계 · French BIG LoBETA − Mkt · 긴 이력판 상태 · 총(교체 비용 없음)", "t1": "쌍둥이 T1(HighMS 만)", "t2": "쌍둥이 T2(HighMS ∧ CS ≤ 1)",
          "p1": "주식 대리 P1(얼린 V02 규칙 · 넓힌 시점정확 명단 · T+1 · 보유 2012-01 ~ 2016-08)"}
SIGN_NOTE = ("판정은 주 통계(총 Δ_timing) 점 추정의 부호만 읽는다(양 = 기전이 선다 → «측정만» · ≤ 0 → «기각») · 창의 켜진 달이 6 보다 적으면 "
             "«측정 불가»(카드 Q06 자신의 F0 규칙 — 부호를 읽지 않는다). 유의성(NW t · p) · 위약 · 순 판 · 읽기는 판정을 바꾸지 않는다(등록 §4).")
LONG_NOTE = ("상태 = «Q06 긴 이력판» — 얼린 q_corrsurp 의 함수(scores · monthly · signals)를 그대로 부르고 이력 상수만 원조 SPDR 상장일로 옮겼다"
             "(창은 첫 수익일부터 · 최소 756 · 최대 2,520 · t − 1 에서 끝 · HighMS = 첫 점수 달부터의 확장 80 백분위 · 36개월 전엔 거짓). "
             "표본 안 창에서는 얼린 실운용 상태(배치 Q 등록 판 · 이력 2009-01 ~)와 달마다 같은지를 센다(같을 까닭은 없다 — 백분위 이력이 다르다).")
FRENCH_NOTE = ("주 목적지 L = French 25_Portfolios_ME_BETA_5x5 «BIG LoBETA»(시총가중 · 월) · M = French 시장(Mkt-RF + RF) — 배치 V 의 얼린 L 대리 "
               "v_data.l_proxy(\"V02\") 가 L − M 을 그대로 준다(생존 편향 없음 · 달력 달 · 결정 달 상태를 다음 달에 같은 종가 근사로 · 기전 대리 · 랩의 D 책이 아니다).")


def _fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%%.%df" % nd) % v
    return str(v)


def _sg(b):
    return "—" if b is None else ("양" if b else "음 또는 0")


def reg_err_lines(path):
    """굽기 뒤에 찾은 등록 오류(글과 얼린 코드의 어긋남)를 손으로 적은 UTF-8 글 파일 → (줄 목록, sha256 앞 16).
    줄마다 소수 · 지수꼴은 <num> 으로 지운다(값이 머리로 새지 않게 · 정수 · 날짜 · 절 번호는 남는다) · 빈 줄 · # 줄은 건너뛴다."""
    b = _bytes(path)
    out = [_scrub(l.strip())[:300] for l in b.decode("utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
    return out, hashlib.sha256(b).hexdigest()[:16]


def _f0_lines(f0):
    st = f0.get("st") or {}
    L, Fz = st.get("long") or {}, st.get("frozen") or {}
    fr = f0.get("french") or {}
    h, ag = L.get("hold") or {}, L.get("agree_ref") or {}
    R = ["## F0 관문(수익 없음 · 등록 개수 대조)", "", "| 관문 | 값 |", "|---|---|",
         "| F0 전체 | %s · 어긋남 %s |" % (_fmt(f0.get("ok")), "; ".join(f0.get("bad") or []) or "없음"),
         "| 뜬 원조 SPDR 판: 파일 · 첫 날 · 거래일 · 묶음 해시 앞 16 | %s · %s · %s · `%s` |" % (L.get("n_files"), L.get("d_first"), L.get("n_days"), (L.get("digest") or "")[:16]),
         "| 긴 이력판: 첫 수익일(D0) · 첫 점수 날(S0) · 첫 점수 달(M0) · HighMS 를 처음 셀 수 있는 달 · 시점 단언 | %s · %s · %s · %s · %s |" % (
             L.get("d0"), L.get("s0"), L.get("m0"), L.get("first_hi"), _fmt(L.get("timing_ok"))),
         "| 창(결정 2006-08 ~ 2016-07 · %s): 켜짐 · 교체 · 켜진 구간 · T1 · T2 · 창 앞(2006-07) · 뒤(2016-08) · F0 규칙(켜짐 ≥ 6) | %s · %s · %s · %s · %s · %s · %s · %s |" % (
             h.get("n"), h.get("on"), h.get("switch"), h.get("runs"), (L.get("hold_t1") or {}).get("on"), (L.get("hold_t2") or {}).get("on"),
             (L.get("pre") or {}).get("d"), (L.get("post") or {}).get("d"), _fmt(h.get("on") is not None and h.get("on") >= 6)),
         "| P1 읽기 창(결정 2011-12 ~ 2016-07): 긴 이력판 켜짐 · 교체 · (재설계 앞) 얼린 실운용 켜짐 | %s · %s · %s |" % (
             (L.get("p1win") or {}).get("on"), (L.get("p1win") or {}).get("switch"), (Fz.get("oldwin") or {}).get("on")),
         "| 표본 안(결정 2016-08 ~ 2026-07): 긴 이력판 켜짐 · 얼린 실운용 켜짐 · 두 상태가 같은 달 · 둘 다 켜짐 | %s · %s · %s/%s · %s |" % (
             (L.get("ref") or {}).get("on"), (Fz.get("ref") or {}).get("on"), ag.get("agree"), ag.get("n"), ag.get("both_on")),
         "| 얼린 실운용 상태(표본 안): 교체 · 켜진 구간 · T1 · T2 · 배치 Q 기록과 같음 · EGSTEP F0 와 같음 · 시점 단언 | %s · %s · %s · %s · %s · %s · %s |" % (
             (Fz.get("ref") or {}).get("switch"), (Fz.get("ref") or {}).get("runs"), (Fz.get("ref_t1") or {}).get("on"), (Fz.get("ref_t2") or {}).get("on"),
             _fmt(Fz.get("ref_same_as_record")), _fmt(Fz.get("ref_same_as_egstep")), _fmt(Fz.get("timing_ok"))),
         "| French 판: 핀(판 SHA · CRSP) · 값이 선 보유월(2006-09 ~ 2026-08) · CRSP 판 | %s · %s · %s |" % (_fmt(fr.get("pins_ok")), fr.get("n_months"), fr.get("crsp")), ""]
    return R


def result_doc(pub, reg_err=None):
    """결과 문서 본문(Markdown) — 게시 칸 파일(_q06holdout.public.json) 하나만 읽는다(손으로 옮기지 않는다)."""
    if not pub or not pub.get("q06hold_public_view"):
        raise SystemExit("🚨 게시 칸 파일이 아니다")
    stopped = pub.get("stopped")
    verdict = pub.get("verdict") or "보류"
    vline = pub.get("verdict_line") or verdict
    H = pub.get("hold") or {}
    pr = H.get("primary") or {}
    if stopped:
        tail = "멈춤(등록된 멈춤 조건)"
    elif verdict == "측정 불가":
        tail = "창의 켜진 달 %s < 6(카드 Q06 F0 규칙)" % H.get("n_on", (H.get("states") or {}).get("on"))
    else:
        tail = "주 점 추정 부호 %s" % _sg(pr.get("sign_pos"))
    title = ("# 결과 — Q06 방어 스텝 방아쇠 기전 검정(Q06HOLD · 랩이 안 본 창 보유 2006-09 ~ 2016-08 · Q06 긴 이력판 · French BIG LoBETA − Mkt · 총 Δ_timing): "
             "한 번 굽기 · %s · **%s**" % (tail, verdict))
    re_lines, re_sha = (reg_err or ([], None))
    reg_all = list(pub.get("registration_error") or []) + list(re_lines)
    mult = pub.get("multiplicity") or {}
    pins = pub.get("pins") or {}
    L = [title, "",
         "풀카드: 없음   <!-- 랩이 스스로 짠 방어 스텝의 방아쇠(배치 Q 카드 Q06)를 랩이 안 본 창에서 다시 잰 역할 검정이다 · build/pool_lab.py 가 이 줄을 읽는다 -->",
         "판정: %s   <!-- 주 통계(창 · French · 총 Δ_timing) 점 추정 > 0 이면 «측정만» · ≤ 0 이면 «기각» · 창의 켜진 달 < 6 이면 «보류(측정 불가)» · 등록된 멈춤이면 «보류» -->" % vline,
         "규칙: 없음   <!-- 랩 게시 sid 가 아니다 · 사이트 규칙 변경 없음 -->", "",
         "아래는 얼린 렌더러(`python -X utf8 build/q06hold_run.py --result-doc`)가 게시 칸 파일(`_q06holdout.public.json`) 하나에서 만든 것이다.", "",
         "## 머리", "",
         "- 등록 커밋 `%s` · 산출 sha256 `%s` · 뿌리 핀 root `%s` · vroot `%s` · 뜬 SPDR 판 `%s`" % (
             pub.get("prereg_commit"), (pub.get("out_sha256") or "—")[:16], ((pins.get("root") or {}).get("code_pin") or "")[:9], (pins.get("vroot") or "")[:9],
             (pins.get("spdr_long") or "")[:16]),
         "- 멈춤: %s · 등록 오류: %s%s" % (stopped or "없음", "; ".join(reg_all) or "없음",
                                       (" (굽기 뒤 손으로 적은 등록 오류 파일 sha256 `%s` · 값이 아니라 글과 얼린 코드의 어긋남)" % re_sha) if re_sha else ""),
         "- 앞선 과정(굽기 · 연기 · F0)이 강제로 죽어 남은 작업 폴더: %s (굽기 시작 때 열지 않고 지웠다 · 등록 §10-2)" % int(pub.get("stale_deleted") or 0),
         "- 창(보유월): 2006-09 ~ 2016-08 · 120개월(결정 2006-08 ~ 2016-07) · 달력 달 · 결정 달 상태를 다음 달에 · 주 통계는 교체 비용 없음(총) · 순 판(교체마다 20bp)은 읽기",
         "- 다중성: 누적 N %s → %s(센 줄 %s · 기저 = EGSTEP 뒤 보수적 맥락 합 · 등록 §9)" % (mult.get("cum_n_before"), mult.get("cum_n_after"), mult.get("rows_counted")),
         "- 공개 규칙: %s" % pub.get("public_rule"), "- 전방: %s" % pub.get("forward"), ""]
    L += _f0_lines(pub.get("f0") or {})
    if stopped:
        L += ["## 멈춤", "", "- 굽기가 멈췄다(%s) — 산출은 멈춤 기록이다. 판정은 «보류»(주 점 추정이 없다). 다시 굽기는 새 등록." % stopped, ""]
        return "\n".join(L) + "\n"
    pl, kt, fa, p1 = H.get("placebo") or {}, H.get("kt") or {}, H.get("fa") or {}, H.get("p1") or {}
    L += ["## 1. 주 통계(창 · 보유 2006-09 ~ 2016-08 · 값은 싣지 않는다 — 부호 · 참/거짓 · 개수)", "",
          "| 줄 | 켜짐 · 꺼짐 달 | F0 규칙(켜짐 ≥ 6) | 총 점 추정 부호(판정) | 순 부호(교체마다 20bp · 읽기) | 교체(들어감 · 나옴) | NW(3) t ≥ t₀.₉₅(%s) | 한쪽 p < 0.05 | 위약 ≥ 95 백분위(K · 씨앗 · 서로 다른 뽑기) |" % pr.get("df"),
          "|---|---|---|---|---|---|---|---|---|",
          "| %s | %s · %s | %s | **%s** | %s | %s · %s | %s | %s | %s(%s · %s · %s) |" % (
              ROW_KO["primary"], pr.get("n_on"), pr.get("n_off"), _fmt(H.get("f0_rule_ok")), _sg(pr.get("sign_pos")), _sg(pr.get("net_sign_pos")),
              pr.get("n_entry"), pr.get("n_exit"), _fmt(pr.get("t_ge_crit")), _fmt(pr.get("p_lt_alpha")), _fmt(pl.get("pct_ge95")), pl.get("k"), pl.get("seed"),
              pl.get("n_distinct")), "",
          "- 창의 켜진 결정 달: %s" % (" · ".join(H.get("on_months") or []) or "없음"),
          "- %s" % SIGN_NOTE, "- %s" % LONG_NOTE, "- %s" % FRENCH_NOTE,
          "- NW 켜짐 계수 = 켜진 평균 − 꺼진 평균(점검 %s) · p = t(n − 2) 위 꼬리 · 위약 = 얼린 q_switch.seg_shuffle(켜진 달 수 · 교체 수 보존)으로 섞은 상태의 같은 총 Δ." % _fmt(pr.get("hac_b_eq_delta")), ""]
    L += ["## 2. 읽기(창 · 보고만 · 판정을 바꾸지 않는다)", "", "| 읽기 | 값(부호 · 참/거짓 · 개수) |", "|---|---|",
          "| KT 시장 방향 — 켜진 뒤 보유월의 시장 초과(Mkt − RF) 평균 < 꺼진 뒤 | %s(켜짐 %s · 꺼짐 %s) |" % (_fmt(kt.get("direction_ok")), kt.get("n_on"), kt.get("n_off")),
          "| 헛경보 — 켜진 달 가운데 시장이 오른 달 · 바탕(모든 달 가운데 오른 달) · 헛경보 몫 < 바탕 | %s/%s · %s/%s · %s |" % (
              fa.get("n_on_up"), fa.get("n_on"), fa.get("n_up"), fa.get("n"), _fmt(fa.get("fa_share_lt_base"))),
          "| 헛경보 달의 (L − M) 총 평균 < 0(비용) · 참경보 달(켜짐 ∧ 시장 ≤ 0)의 평균 > 0(이득) · 참경보 달 수 | %s · %s · %s |" % (
              _fmt(fa.get("fa_cost_neg")), _fmt(fa.get("ta_benefit_pos")), fa.get("n_on_down"))]
    for k in ("t1", "t2"):
        x = H.get(k) or {}
        L.append("| %s — 총 부호 · 순 부호 · 켜짐 · 꺼짐 | %s · %s · %s · %s |" % (ROW_KO[k], _sg(x.get("sign_pos")), _sg(x.get("net_sign_pos")), x.get("n_on"), x.get("n_off")))
    L += ["| T2 의 Δ < 주 통계 | %s |" % _fmt(H.get("t2_below_primary")),
          "| %s | %s — 그 창의 긴 이력판 켜진 달 %s(얼린 실운용 %s) · 켜짐 < 6 이면 카드 Q06 F0 규칙으로 측정 불가 · 이 등록은 P1 수익 경로를 짓지 않는다(등록 §2-3) |" % (
              ROW_KO["p1"], "측정 불가" if not p1.get("measurable") else "읽지 않음", p1.get("n_on"), p1.get("n_on_frozen")), ""]
    Rf = pub.get("ref") or {}
    if Rf:
        x = Rf.get("f") or {}
        k2, f2 = Rf.get("kt") or {}, Rf.get("fa") or {}
        L += ["## 3. 참고 — 표본 안 창(보유 2016-09 ~ 2026-08 · 얼린 실운용 상태 · French · 이미 본 창 · 오염 · 값을 싣는다)", "",
              "| 줄 | 켜짐 · 꺼짐 | 총 Δ_timing(%p/월) | 켜진 평균 | 꺼진 평균 | 순 Δ | NW t | 한쪽 p | 교체(들어감 · 나옴) |", "|---|---|---|---|---|---|---|---|---|",
              "| French BIG LoBETA − Mkt · 얼린 실운용 상태 | %s · %s | %s | %s | %s | %s | %s | %s | %s · %s |" % (
                  x.get("n_on"), x.get("n_off"), _fmt(x.get("delta"), 3), _fmt(x.get("mean_on"), 3), _fmt(x.get("mean_off"), 3), _fmt(x.get("delta_net"), 3),
                  _fmt(x.get("t")), _fmt(x.get("p"), 3), x.get("n_entry"), x.get("n_exit")), "",
              "| 표본 안 읽기 | 값 |", "|---|---|",
              "| KT 시장 방향 — 켜진 뒤 시장 초과 평균 · 꺼진 뒤 · 차(%%p/월) · NW t · 방향 | %s · %s · %s · %s · %s |" % (
                  _fmt(k2.get("ex_on"), 3), _fmt(k2.get("ex_off"), 3), _fmt(k2.get("diff"), 3), _fmt(k2.get("t")), _fmt(k2.get("direction_ok"))),
              "| 헛경보 — 켜진 달 가운데 오른 달 · 바탕 · 헛경보 평균 · 참경보 평균(%%p/월) | %s/%s · %s/%s · %s · %s |" % (
                  f2.get("n_on_up"), f2.get("n_on"), f2.get("n_up"), f2.get("n"), _fmt(f2.get("fa_mean"), 3), _fmt(f2.get("ta_mean"), 3)), "",
              "- 표본 안 창의 켜진 결정 달 — 얼린 실운용 상태(%s): %s" % (len(Rf.get("on_months_frozen") or []), " · ".join(Rf.get("on_months_frozen") or []) or "없음"),
              "- 같은 창의 «Q06 긴 이력판»(%s): %s · 두 판이 같은 달 %s/%s · 둘 다 켜짐 %s(같을 까닭은 없다 — 백분위 이력과 가격 원천이 다르다 · 이 줄은 상태만 · 수익 없음)" % (
                  len(Rf.get("on_months_long") or []), " · ".join(Rf.get("on_months_long") or []) or "없음", (Rf.get("agree") or {}).get("agree"),
                  (Rf.get("agree") or {}).get("n"), (Rf.get("agree") or {}).get("both_on")),
              "- 이 창의 Q06 기록 · D 책의 모양 · 2019-02 헛경보는 설계 전에 봤다(등록 §0) — 확인이 아니다. 창 끝 다음 상태는 모르므로 순 판은 켜진 채 끝나면 나오는 비용을 문다.", ""]
    L += ["## 4. 미리 적은 예측(등록 §8)", "", "| 예측 | 맞음 |", "|---|---|"]
    for k, ko in PRED_KO.items():
        L.append("| %s | %s |" % (ko, _fmt((pub.get("predictions") or {}).get(k))))
    L += ["", "## 공개 규칙", "",
          "- 이 문서는 게시 칸 파일 하나에서 얼린 렌더러가 만들었다 · 창(2006-09 ~ 2016-08)은 사이트 10년 창 앞이라 값(평균 · t · p · 백분위)을 싣지 않는다 — "
          "부호 · 참/거짓 · 개수 · 상태 날짜만 · 값은 저장소 밖 캐시의 내부 판(`--internal-doc`)에만 둔다 · 표본 안 참고 창은 10년 창 안이라 값을 싣는다.",
          "- 판정은 주 점 추정의 부호만 읽는다 · 창의 켜진 달이 6 보다 적으면 부호를 읽지 않는다(«측정 불가»).",
          "- 산출 원본(_q06holdout.json)과 뜬 SPDR 판은 저장소 밖 캐시에만 둔다."]
    txt = "\n".join(L) + "\n"
    if CACHE_ONLY_KEY in txt:
        raise SystemExit("🚨 결과 문서에 캐시 표지가 있다")
    return txt


def internal_doc(out):
    """내부 판(🚨 저장소 밖 캐시에만) — 창의 값까지(평균 · t · p · 위약 분위 · 읽기 값). 렌더러는 산출 원본을 읽는다."""
    M = out.get("main") or {}
    if M.get("stopped"):
        return "# 내부 판 — Q06HOLD · 멈춤: %s\n" % M["stopped"]
    H, Rf = M["hold"], M["ref"]
    pr, pl, kt, fa = H["primary"], H["placebo"], H["kt"], H["fa"]
    L = ["# 내부 판 — Q06HOLD 창 값(🚨 저장소 밖 · 사이트 10년 창 앞 값 · 공개 금지)", "",
         "- 등록 커밋 `%s` · 판정 %s · 창 켜진 결정 달 %s" % (out.get("prereg_commit"), M.get("verdict"), " · ".join(H.get("on_months") or [])), "",
         "| 줄 | 켜짐 · 꺼짐 | 총 Δ(%p/월) | 켜진 평균 | 꺼진 평균 | 순 Δ | NW t | p | 들어감 · 나옴 |", "|---|---|---|---|---|---|---|---|---|"]
    rows = [("primary", pr), ("t1", H["t1"]), ("t2", H["t2"])]
    for k, x in rows:
        L.append("| %s | %s · %s | %s | %s | %s | %s | %s | %s | %s · %s |" % (ROW_KO[k], x.get("n_on"), x.get("n_off"), _fmt(x.get("delta"), 3), _fmt(x.get("mean_on"), 3),
                                                                  _fmt(x.get("mean_off"), 3), _fmt(x.get("delta_net"), 3), _fmt(x.get("t")), _fmt(x.get("p"), 3),
                                                                  x.get("n_entry"), x.get("n_exit")))
    q = pl.get("q") or {}
    L += ["", "- 위약: K %s · 씨앗 %s · 서로 다른 뽑기 %s · 백분위 %s · 뽑기 p05 · p50 · p95 = %s · %s · %s · t₀.₉₅ = %s" % (
              pl["k"], pl["seed"], pl["n_distinct"], _fmt(pl.get("pct"), 1), _fmt(q.get("p05"), 3), _fmt(q.get("p50"), 3), _fmt(q.get("p95"), 3), _fmt(H.get("t_crit"))),
          "- KT: 켜진 뒤 시장 초과 %s · 꺼진 뒤 %s · 차 %s · NW t %s · 방향 %s" % (_fmt(kt.get("ex_on"), 3), _fmt(kt.get("ex_off"), 3), _fmt(kt.get("diff"), 3),
                                                                      _fmt(kt.get("t")), _fmt(kt.get("direction_ok"))),
          "- 헛경보: %s/%s(바탕 %s/%s) · 헛경보 평균 %s · 참경보 평균 %s" % (fa["n_on_up"], fa["n_on"], fa["n_up"], fa["n"], _fmt(fa.get("fa_mean"), 3), _fmt(fa.get("ta_mean"), 3)),
          "- P1 창(보유 2012-01 ~ 2016-08): 긴 이력판 켜진 달 %s · 얼린 실운용 %s — 측정 불가(수익 경로 없음)" % ((H.get("p1") or {}).get("n_on"), (H.get("p1") or {}).get("n_on_frozen")),
          "- 표본 안 참고(French · 얼린 실운용): 총 Δ %s · 순 Δ %s(%%p/월)" % (_fmt(Rf["f"].get("delta"), 3), _fmt(Rf["f"].get("delta_net"), 3)), ""]
    return "\n".join(L) + "\n"


def result_doc_write_problems(pub, P=None):
    """--result-doc --write 문지기 — 연기 판이 아니고 · 두 로컬 표식에 FINISHED <산출 sha> 가 있고 · 캐시 산출 sha 가 게시 칸의 out_sha256 과 같아야 쓴다."""
    P = P or paths()
    bad = []
    if not pub or not pub.get("q06hold_public_view"):
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
    """등록 전 F0 — 핀 뿌리 둘(작업 트리 data/ 와 무관)로 F0 자식들을 돌려 개수 · 동일성만 돌려준다(수익 없음 · 창의 켜진 달 날짜는 찍지 않는다)."""
    c = cache_guard_std()
    os.makedirs(c, exist_ok=True)
    n_stale = purge_stale(c)                                  # 앞선 과정이 죽어 남은 작업 폴더 — 열지 않고 지운다(개수만)
    tmp = tempfile.mkdtemp(prefix="q06hold_f0_", dir=c)
    try:
        try:
            pf = preflight(tmp)
            f0, sec = pf["f0"], pf["sec"]
        except SystemExit as e:
            ps, pv = os.path.join(tmp, "out_st.json"), os.path.join(tmp, "out_f0v.json")
            if not (os.path.exists(ps) and os.path.exists(pv)):
                raise
            f0, sec = merge_f0(_read_json(ps), _read_json(pv)), {"note": _scrub(str(e))[:300]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    sg, sn, sm = spdr_digest_std()
    det = {k: f0.get(k) for k in F0_PUB_KEYS if k not in ("signature",)}
    return {"sec": sec, "ok": f0.get("ok"), "bad": f0.get("bad"), "stale_deleted": n_stale, "signature": f0.get("signature"),
            "spdr": {"digest": sg, "n": sn, "missing": sm}, "detail": det}


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
    tmp = tempfile.mkdtemp(prefix="q06hold_runner_smoke_", dir=cache)
    if _inside(tmp, ROOT):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    saved = dict(_OVR)
    res = {"ok": False, "steps": {}, "started": _now(), "stale_deleted": n_stale}
    t0 = time.time()
    sink = io.StringIO()
    real_out = os.path.join(cache, "out")
    before = sorted(f for f in os.listdir(real_out) if f.startswith("_q06holdout")) if os.path.isdir(real_out) else []
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
                itx = internal_doc(json.loads(_bytes(P["out"]).decode("utf-8")))
                files["internal_rendered"] = bool(itx)
                del itx
            files["result_doc_rendered"] = bool(txt)
            files["result_doc_has_cache_marker"] = CACHE_ONLY_KEY in txt
            del txt
        except BaseException:                                # noqa: BLE001
            files["result_doc_rendered"] = False
        res["files"] = files
        b = res["steps"].get("bake") or {}
        res["ok"] = bool(b.get("ok") and b.get("registration_error_empty") and all(files[k]["exists"] for k in ("out", "mark", "runlog", "public", "gitmark"))
                         and files["second_run_blocked"] and files["finished_marks"] and files["restart_blocked"] and files.get("public_safe")
                         and files.get("not_stopped") and files.get("result_doc_rendered") and files.get("internal_rendered")
                         and not files.get("result_doc_has_cache_marker"))
    finally:
        _OVR.clear()
        _OVR.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
        res["stdout_discarded_unread"] = True
        del sink
    res["deleted_unread"] = not os.path.exists(tmp)
    after = sorted(f for f in os.listdir(real_out) if f.startswith("_q06holdout")) if os.path.isdir(real_out) else []
    res["real_out_untouched"] = before == after == []
    res["real_gitmark_absent"] = not os.path.exists(_git_mark_path())
    res["sec"] = round(time.time() - t0, 1)
    res["ok"] = bool(res["ok"] and res["deleted_unread"] and res["real_out_untouched"] and res["real_gitmark_absent"])
    _write_text(os.path.join(cache, "meta", "_smoke_q06hold_run.json"), json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    return res


SMOKE_ALLOWED_KEYS = {"ok", "steps", "started", "stale_deleted", "files", "tag", "err", "stdout_discarded_unread", "deleted_unread", "real_out_untouched", "real_gitmark_absent", "sec",
                      "bake", "registration_error_empty", "start_tag", "stage", "exists", "nonempty", "second_run_blocked", "finished_marks", "tag_file",
                      "restart_blocked", "not_stopped", "public_safe", "result_doc_rendered", "result_doc_has_cache_marker", "internal_rendered", "out", "mark",
                      "runlog", "public", "gitmark"}


# ══════════════════════════════════════════════════════════════════════════
#  합성 점검(실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _st_state_counts():
    import q06hold as E
    c = E.state_counts([0, 1, 1, 0, 1, 0, 0, 1])
    ag = E.agreement([0, 1, 1, 0], [0, 1, 0, 1])
    return (c == {"n": 8, "on": 4, "switch": 5, "runs": 3} and E.state_counts([0, 0]) == {"n": 2, "on": 0, "switch": 0, "runs": 0}
            and ag == {"n": 4, "agree": 2, "both_on": 1, "a_on": 2, "b_on": 2})


def _st_net_series():
    """순 판 — 켜진 달만 문다(들어감: 앞이 꺼짐 · 나옴: 다음이 꺼짐 또는 모름 · 교체마다 20bp · 더하기 꼴) · 꺼진 달 그대로 · 들어감 · 나옴 개수."""
    import q06hold as E
    y = [0.01, 0.02, -0.01, 0.03, 0.00]
    s = [0, 1, 1, 0, 1]
    f = 0.002
    n = E.net_series(y, s, 0, 0)
    ok = abs(n[0] - 0.01) < 1e-15 and abs(n[3] - 0.03) < 1e-15
    ok &= abs(n[1] - (0.02 - f)) < 1e-15 and abs(n[2] - (-0.01 - f)) < 1e-15 and abs(n[4] - (0.0 - 2 * f)) < 1e-15
    ok &= abs(E.net_series(y, s, 0, 1)[4] - (0.0 - f)) < 1e-15                       # 창 뒤 켜짐 → 나오지 않는다
    ok &= abs(E.net_series(y, s, 0, None)[4] - (0.0 - 2 * f)) < 1e-15                # 모름 → 나오는 비용을 문다(보수적)
    ok &= abs(E.net_series(y, [1, 0, 0, 0, 0], 1, 0)[0] - (0.01 - f)) < 1e-15          # 창 앞 켜짐 → 들어가지 않는다
    ok &= E.net_series(y, s, 0, 0, c=0.0) == [float(v) for v in y]
    per, ent, ext = E.charged_switches(s, 0, 0)
    ok &= (ent, ext) == (2, 2) and per == [(0, 0), (1, 0), (0, 1), (0, 0), (1, 1)] and E.charged_switches(s, 0, 1)[1:] == (2, 1)
    ok &= E.charged_switches([1, 1], 1, 1)[1:] == (0, 0)
    return bool(ok)


def _st_on_off_and_hac():
    """켜짐 계수 = 켜진 평균 − 꺼진 평균(얼린 eg30plus.nw_ols) · NW t 를 손 공식과 대조 · p = t(n − 2) 꼬리 · 한쪽이 비면 t 없음 · timing 의 총 · 순."""
    import numpy as np
    import eg30plus as EP
    import q06hold as E
    from scipy.stats import t as _t
    rs = np.random.RandomState(3)
    n = 120
    s = np.zeros(n, int)
    s[[10, 11, 30, 55, 56, 57, 90]] = 1
    y = list(rs.normal(0.0, 0.02, n))
    oo = E.on_off(y, s)
    h = E.hac_diff(y, s, EP)
    ok = abs(h["b"] - oo["delta"]) < 1e-9 and h["df"] == n - 2 and abs(h["p"] - float(_t.sf(h["t"], n - 2))) < 1e-15
    X = np.column_stack([np.ones(n), s.astype(float)])
    yy = np.asarray(y) * 100
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ yy
    e = yy - X @ b
    g = X * e[:, None]
    S = g.T @ g
    for L in range(1, 4):
        G = g[L:].T @ g[:-L]
        S += (1 - L / 4.0) * (G + G.T)
    V = XtXi @ S @ XtXi
    ok &= abs(h["t"] - b[1] / math.sqrt(V[1, 1])) < 1e-9
    ok &= E.hac_diff(y, np.zeros(n, int), EP)["t"] is None and E.on_off(y, np.zeros(n, int))["delta"] is None
    tm = E.timing([0.01] * n, s, 0, 0, EP)
    ok &= tm["n_on"] == 7 and tm["n_entry"] == 4 and tm["n_exit"] == 4 and abs(tm["delta"]) < 1e-12 and tm["delta_net"] < 0
    ok &= abs(tm["delta_net"] - (-(4 + 4) * 0.002 / 7 * 100)) < 1e-9 and tm["hac_b_eq_delta"] in (True, None)
    return bool(ok)


def _st_placebo():
    """위약(총 Δ) — 얼린 q_switch.seg_shuffle 이 켜진 달 수 · 교체 수를 보존 · 같은 씨앗이면 같은 뽑기 · 백분위 = 참보다 작은 뽑기 몫."""
    import numpy as np
    import q_switch as SW
    import q06hold as E
    n = 60
    s = np.zeros(n, int)
    s[[5, 6, 20, 30, 44]] = 1
    rs = np.random.RandomState(9)
    y = list(rs.normal(0, 0.02, n))
    d1, k1 = E.placebo(SW, y, s, 300, 11)
    d2, k2 = E.placebo(SW, y, s, 300, 11)
    ok = d1 == d2 and k1 == k2 and 1 < k1 <= 300 and len(d1) == 300
    rng = np.random.default_rng(11)
    p = SW.seg_shuffle(np.asarray(s, np.int8), rng)
    ok &= abs(d1[0] - E.on_off(y, p)["delta"]) < 1e-15
    ok &= E.pct_rank([1.0, 2.0, 3.0, 4.0], 2.5) == 50.0 and E.pct_rank([1.0], None) is None and E.pct_rank([], 1.0) is None
    ok &= abs(E.quantiles([1.0, 2.0, 3.0])["p50"] - 2.0) < 1e-12
    return bool(ok)


def _st_kt_fa():
    """KT 시장 방향(켜진 뒤 시장 초과 < 꺼진 뒤면 참) · 헛경보(켜진 달 가운데 시장 > 0) · 바탕 · 헛경보 · 참경보 평균 · 헛경보 몫 < 바탕."""
    import numpy as np
    import eg30plus as EP
    import q06hold as E
    mex = [0.02, -0.03, 0.01, 0.04, -0.01, 0.02, 0.03, -0.02]
    s = [0, 1, 0, 1, 1, 0, 0, 0]
    kt = E.kt_direction(mex, s, EP)
    on, off = np.mean([mex[1], mex[3], mex[4]]), np.mean([mex[0], mex[2], mex[5], mex[6], mex[7]])
    ok = abs(kt["diff"] - (on - off) * 100) < 1e-9 and kt["direction_ok"] == bool(on < off)
    y = [0.0, 0.01, 0.0, -0.02, 0.005, 0.0, 0.0, 0.0]
    fa = E.false_alarm(mex, y, s)
    ok &= fa["n_on"] == 3 and fa["n_on_up"] == 1 and fa["n_on_down"] == 2 and fa["n_up"] == 5 and fa["n"] == 8
    ok &= abs(fa["fa_mean"] - (-2.0)) < 1e-12 and abs(fa["ta_mean"] - 0.75) < 1e-12 and fa["fa_cost_neg"] is True and fa["ta_benefit_pos"] is True
    ok &= fa["fa_share_lt_base"] is True                                             # 1/3 < 5/8
    fa0 = E.false_alarm(mex, y, [0] * 8)
    ok &= fa0["fa_mean"] is None and fa0["fa_cost_neg"] is None and fa0["fa_share_lt_base"] is None
    return bool(ok)


def _st_verdict_predictions():
    """판정 어휘 — 멈춤 · 켜짐 < 6 → 측정 불가(«판정:» 줄은 «보류(측정 불가)» — 랩 어휘를 품는다) · 총 > 0 → 측정만 · ≤ 0 → 기각 · 예측 일곱."""
    import q06hold as E
    ok = (E.verdict(0.1, 12) == "측정만" and E.verdict(0.0, 12) == "기각" and E.verdict(-0.1, 12) == "기각" and E.verdict(0.3, 5) == "측정 불가"
          and E.verdict(None, 12) == "보류" and E.verdict(0.2, 12, "멈춤") == "보류" and E.verdict(0.2, None) == "보류")
    ok &= E.verdict_line("측정 불가") == "보류(측정 불가)" and E.verdict_line("기각") == "기각"
    ok &= any(k in E.verdict_line("측정 불가") for k in ("기각", "게시", "측정만", "보류"))
    M = _fake_main()
    P = E.predictions(M)
    ok &= set(P) == set(PRED_KO) and all(isinstance(v, bool) for v in P.values())
    return bool(ok)


def _st_long_history_rules():
    """«Q06 긴 이력판»(합성 판) — 얼린 q_corrsurp 의 scores · monthly · signals 를 그대로 · D0 = 첫 수익일 · S0 = D0 + 756 거래일 · M0 = S0 의 달 ·
    HighMS 는 M0 부터 36번째 달 전엔 거짓 · 시점(결정 달의 마지막 점수 날 = 그달 마지막 거래일) · 날짜가 다른 파일 · 빈 값은 멈춘다 · 묶음 해시 규칙."""
    import numpy as np
    import datetime as dt
    import q_corrsurp as QC
    import q06hold as E
    tmp = tempfile.mkdtemp(prefix="q06hold_st_long_")
    try:
        d, dates = dt.date(2001, 1, 2), []
        while len(dates) < 1900:
            if d.weekday() < 5:
                dates.append(d.strftime("%Y-%m-%d"))
            d += dt.timedelta(days=1)
        rng = np.random.default_rng(4)
        tick = E.Q06_EXPECT["SPDR"]
        for t in tick:
            p = 20 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, len(dates))))
            with io.open(os.path.join(tmp, t + ".csv"), "w", encoding="utf-8", newline="\n") as f:
                f.write("Date,Close\n" + "".join("%s,%r\n" % (a, float(b)) for a, b in zip(dates, p)))
        last_m = dates[-40][:7]
        D, T1, T2, sc, ds, me, meta = E.q06_long(QC, tmp, tick, last_m)
        ok = meta["d0"] == dates[1] and meta["s0"] == dates[1 + QC.WMIN] and meta["m0"] == dates[1 + QC.WMIN][:7] and min(sc) == 1 + QC.WMIN
        ms = sorted(m for m in D if m >= meta["m0"])
        ok &= not any(T1[m] for m in ms[:QC.NMIN_M - 1]) and meta["first_hi"] == ms[QC.NMIN_M - 1]
        ok &= all(D[m] == int(T1[m] and not T2[m]) for m in ms)                          # D = HighMS ∧ CS > 1 · T2 = HighMS ∧ CS ≤ 1
        okt, badt = E._timing_long(sc, ds, me, ms[:-1])
        ok &= okt and not badt
        dg, n = E.spdr_digest(tmp, tick)
        want = "".join("%s\t%s\n" % (t, E.file_sha256(os.path.join(tmp, t + ".csv"))) for t in sorted(tick))
        ok &= n == 9 and dg == hashlib.sha256(want.encode("utf-8")).hexdigest()
        with io.open(os.path.join(tmp, "XLB.csv"), "w", encoding="utf-8", newline="\n") as f:
            f.write("Date,Close\n" + "".join("%s,%r\n" % (a, 20.0) for a in dates[1:]))
        try:
            E.spdr_load(tmp, tick)
            ok = False
        except E.StopBake:
            pass
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_q06_frozen():
    """Q06 등록 상수 = 얼린 q_corrsurp(F0_MIN 포함) · 얼린 합성 selftest 통과 · F0 규칙 = 얼린 F0_MIN · 창 길이."""
    import q06hold as E
    import q_corrsurp as QC
    ok = all(E._norm(getattr(QC, k)) == E._norm(v) for k, v in E.Q06_EXPECT.items()) and bool(QC.selftest()["ok"])
    ok &= E.F0_MIN_ON == QC.F0_MIN and len(E.forms()) == E.N_HOLD and len(E.ref_forms()) == E.N_REF and len(E.p1_forms()) == E.N_P1
    ok &= E.HOLD[0] >= "2006-09" and E.mshift(E.FORM_FIRST, 1) == E.HOLD[0] and E.mshift(E.FORM_LAST, 1) == E.HOLD[1]
    return bool(ok)


def _st_blob_guard():
    import q06hold as E
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
        ok &= _git("rev-parse", "%s:build/%s.py" % (ROOT_PIN["code_pin"], m)).stdout.strip() == b
    return bool(ok)


def _st_lock_and_tag():
    """동시 굽기 막기 — 배타 잠금은 두 번째를 멈추고 풀면 다시 잡힌다 · 시작 태그가 이미 있으면 Q06HOLD_RERUN 일 때만 «already»."""
    tmp = tempfile.mkdtemp(prefix="q06hold_st_lock_")
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
    tmp = tempfile.mkdtemp(prefix="q06hold_st_stale_")
    try:
        for d in ("q06hold_work_a1", "q06hold_f0_b2", "q06hold_runner_smoke_c3", "out", "meta", "raw"):
            os.makedirs(os.path.join(tmp, d, "x"), exist_ok=True)
            _write_text(os.path.join(tmp, d, "x", "out_s.json"), "{}\n")
        _write_text(os.path.join(tmp, "q06hold_work_file.txt"), "x\n")
        n = purge_stale(tmp)
        left = sorted(os.listdir(tmp))
        return bool(n == 3 and left == ["meta", "out", "q06hold_work_file.txt", "raw"] and purge_stale(tmp) == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _fake_row(mk, n_on=14, n_off=106, delta=None):
    return {"n": n_on + n_off, "n_on": n_on, "n_off": n_off, "delta": (-mk if delta is None else delta), "mean_on": mk, "mean_off": mk, "delta_net": mk,
            "mean_on_net": mk, "t": mk, "p": 0.6, "df": n_on + n_off - 2, "hac_b_eq_delta": True, "n_entry": 9, "n_exit": 9}


def _fake_main(stopped=None, n_on=14, delta=None):
    """게시 칸 · 결과 문서 시험용 합성 산출(창 값은 표지 수 0.5555 · 표본 안은 0.4444)."""
    if stopped:
        return {"kind": "q06hold_out", "stopped": stopped}
    mk, rk = 0.5555, 0.4444
    import q06hold as E
    hold = {"window": ["2006-09", "2016-08"], "n": 120, "states": {"n": 120, "on": n_on, "switch": 18, "runs": 9}, "pre": 0, "post": 0,
            "f0_rule_ok": bool(n_on >= 6), "on_months": ["2008-09", "2008-10"],
            "primary": _fake_row(mk, n_on, 120 - n_on, delta), "placebo": {"k": 10000, "seed": 20260930, "n_distinct": 9000, "true": -mk, "pct": 33.3,
                                                                            "q": {"p05": mk, "p50": mk, "p95": mk}},
            "t_crit": 1.658, "kt": {"n_on": n_on, "n_off": 120 - n_on, "ex_on": mk, "ex_off": mk, "diff": mk, "t": mk, "direction_ok": False},
            "fa": {"n": 120, "n_up": 75, "n_on": n_on, "n_on_up": 6, "n_on_down": n_on - 6, "fa_mean": mk, "ta_mean": mk, "fa_cost_neg": True,
                   "ta_benefit_pos": True, "fa_share_lt_base": True},
            "t1": _fake_row(mk, 20, 100), "t2": _fake_row(mk, 6, 114),
            "p1": {"window": ["2012-01", "2016-08"], "n": 56, "n_on": 3, "n_on_frozen": 4, "measurable": False}}
    ref = {"window": ["2016-09", "2026-08"], "n": 120, "states": {"n": 120, "on": 22, "switch": 23, "runs": 12},
           "f": dict(_fake_row(rk, 22, 98), delta=rk), "kt": {"n_on": 22, "n_off": 98, "ex_on": rk, "ex_off": rk, "diff": rk, "t": rk, "direction_ok": True},
           "fa": {"n": 120, "n_up": 80, "n_on": 22, "n_on_up": 12, "n_on_down": 10, "fa_mean": rk, "ta_mean": rk, "fa_cost_neg": True, "ta_benefit_pos": True,
                  "fa_share_lt_base": True},
           "on_months_frozen": ["2019-01", "2019-02", "2020-03"], "on_months_long": ["2019-02"],
           "agree": {"n": 120, "agree": 118, "both_on": 1, "a_on": 1, "b_on": 3}}
    M = {"kind": "q06hold_out", "hold": hold, "ref": ref, "verdict": E.verdict(hold["primary"]["delta"], n_on),
         "multiplicity": {"cum_n_before": 1058, "rows_counted": 5, "cum_n_after": 1063, "counted": ["F_HOLD"]}}
    M["predictions"] = E.predictions(M)
    return M


def _fake_f0():
    long = {"digest": "4a01c8502dcf17fd" + "0" * 48, "n_files": 9, "d_first": "1998-12-22", "n_days": 6964, "d0": "1998-12-23", "s0": "2001-12-26",
            "m0": "2001-12", "first_hi": "2004-11", "timing_ok": True, "timing_bad": [], "n_score_days": 6000, "n_months": 297,
            "hold": {"n": 120, "on": 14, "switch": 18, "runs": 9}, "hold_t1": {"n": 120, "on": 25}, "hold_t2": {"n": 120, "on": 11},
            "pre": {"m": "2006-07", "d": 0}, "post": {"m": "2016-08", "d": 0}, "p1win": {"n": 56, "on": 3, "switch": 6},
            "ref": {"n": 120, "on": 20, "switch": 21}, "agree_ref": {"n": 120, "agree": 110, "both_on": 15, "a_on": 20, "b_on": 22}}
    frozen = {"timing_ok": True, "timing_bad": [], "ref": {"n": 120, "on": 22, "switch": 23, "runs": 12}, "ref_t1": {"n": 120, "on": 35},
              "ref_t2": {"n": 120, "on": 13}, "ref_pre": 0, "ref_same_as_record": True, "ref_same_as_egstep": True, "oldwin": {"n": 56, "on": 4}}
    return {"ok": True, "bad": [], "st": {"long": long, "frozen": frozen}, "french": {"pins_ok": True, "bad": [], "n_months": 240, "crsp": "202608"},
            "signature": {"hold_on": 14}, "expect_diff": []}


def _st_public_and_result_doc():
    """게시 칸 — 캐시 표지 없음 · 공개 안전 · 창 칸에 실수 없음(표지 수 0.5555 가 게시 칸 · 결과 문서에 없다) · 표본 안 값(0.4444)은 싣는다 ·
    결과 문서 머리 세 줄(풀카드 · 판정 · 규칙) · «등록 커밋 `<40자>`» 가 문서의 첫 «커밋 <해시>» · 측정만 · 기각 · 측정 불가(«보류(측정 불가)») · 멈춤 판 ·
    등록 오류 글의 소수 지우기 · 내부 판은 창 값까지 · P1 은 켜진 달 수와 «측정 불가» 만 · 표본 안 두 판 상태 달."""
    full = "0123456789abcdef0123456789abcdef01234567"
    out = {CACHE_ONLY_KEY: True, "prereg": PREREG, "prereg_commit": full, "f0": _fake_f0(), "main": _fake_main(),
           "pins": {"root": ROOT_PIN, "vroot": VROOT_PIN, "spdr_long": SPDR_DIGEST}, "series": {"hold": {"y": [0.1] * 120}}}
    pub = public_doc(out, "0" * 64, 1, {"commit": full})
    blob = json.dumps(pub, ensure_ascii=False)
    txt = result_doc(pub)
    ok = CACHE_ONLY_KEY not in blob and '"series"' not in blob and "0.5555" not in blob and "0.555" not in txt
    ok &= "0.444" in txt and not public_safe_std(pub)
    ok &= all(re.search(r"^\s*%s\s*[:：]" % k, txt, re.M) for k in ("풀카드", "판정", "규칙"))
    ok &= re.search(r"^풀카드:\s*없음", txt, re.M) is not None and re.search(r"^규칙:\s*없음", txt, re.M) is not None
    ok &= re.search(r"^판정:\s*기각", txt, re.M) is not None and "**기각**" in txt.split("\n", 1)[0]
    hm = re.search(r"커밋\s*[`'\"]?([0-9a-f]{7,40})", txt)
    ok &= bool(hm) and hm.group(1) == full
    ok &= all(s in txt for s in ("2008-09 · 2008-10", "음 또는 0", "6/14 · 75/120", "누적 N 1058 → 1063(센 줄 5", "Q06 긴 이력판", "French 25_Portfolios_ME_BETA_5x5",
                                 "판정은 주 통계(총 Δ_timing) 점 추정의 부호만 읽는다", "## 3. 참고 — 표본 안 창", "P7 표본 안 참고", "등록 오류: 없음",
                                 "남은 작업 폴더: 0", "110/120", "1998-12-22", "2004-11", "측정 불가 — 그 창의 긴 이력판 켜진 달 3(얼린 실운용 4)",
                                 "얼린 실운용 상태(3): 2019-01 · 2019-02 · 2020-03", "«Q06 긴 이력판»(1): 2019-02 · 두 판이 같은 달 118/120 · 둘 다 켜짐 1",
                                 "| 3 · 6 · 4 |"))
    ok &= "P8" not in txt and "p1_same_sign" not in blob
    ok &= bool(public_safe_std({"hold": {"window": ["2006-09", "2016-08"], "delta": 0.5}})) and not public_safe_std({"hold": {"window": ["2006-09", "2016-08"], "n": 56}})
    bad = dict(pub)
    bad["hold"] = dict(pub["hold"], leak=[0.1] * 12)
    ok &= bool(public_safe_std(bad))
    tmpf = tempfile.mkdtemp(prefix="q06hold_st_re_")
    try:
        rp = os.path.join(tmpf, "re.txt")
        _write_text(rp, "# 주석\n§4 글은 0.25 라 했으나 코드는 다른 값\n\n두 번째 줄 2021-10\n")
        re_ = reg_err_lines(rp)
    finally:
        shutil.rmtree(tmpf, ignore_errors=True)
    txt_re = result_doc(pub, re_)
    ok &= re_[0] == ["§4 글은 <num> 라 했으나 코드는 다른 값", "두 번째 줄 2021-10"] and len(re_[1]) == 16
    ok &= ("등록 오류: §4 글은 <num> 라 했으나 코드는 다른 값; 두 번째 줄 2021-10" in txt_re) and re_[1] in txt_re and "0.25" not in txt_re
    pub_pos = public_doc(dict(out, main=_fake_main(delta=0.5555)), "0" * 64, 1, {"commit": full, "stale_deleted": 2})
    txt_pos = result_doc(pub_pos)
    ok &= re.search(r"^판정:\s*측정만", txt_pos, re.M) is not None and "주 점 추정 부호 양" in txt_pos and "남은 작업 폴더: 2" in txt_pos
    pub_nm = public_doc(dict(out, main=_fake_main(n_on=5, delta=0.5555)), "0" * 64, 1, {"commit": full})
    txt_nm = result_doc(pub_nm)
    ok &= re.search(r"^판정:\s*보류\(측정 불가\)", txt_nm, re.M) is not None and "**측정 불가**" in txt_nm.split("\n", 1)[0] and pub_nm["verdict"] == "측정 불가"
    out2 = dict(out, main=_fake_main(stopped="French 값이 없는 보유월"))
    pub2 = public_doc(out2, "0" * 64, 1, {"commit": full})
    txt2 = result_doc(pub2)
    ok &= "## 멈춤" in txt2 and re.search(r"^판정:\s*보류", txt2, re.M) is not None and "0.5555" not in json.dumps(pub2)
    itx = internal_doc(out)
    ok &= ("0.556" in itx or "0.555" in itx) and "공개 금지" in itx and "2008-09" in itx
    return bool(ok)


def _st_result_write_guard():
    tmp = tempfile.mkdtemp(prefix="q06hold_st_")
    try:
        P = {"out": os.path.join(tmp, "_q06holdout.json"), "mark": os.path.join(tmp, "_q06holdout.started"), "gitmark": os.path.join(tmp, "gm")}
        with open(P["out"], "wb") as f:
            f.write(b'{"x": 1}\n')
        sha = _sha_file(P["out"])
        for m in (P["mark"], P["gitmark"]):
            _write_text(m, "C · t\n%s %s t\n" % (FINISHED, sha))
        pub = {"q06hold_public_view": True, "smoke": False, "out_sha256": sha, "prereg_commit": "a" * 40}
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
    ok = True
    for env in ({}, {"Q06HOLD_COMMIT": "0" * 40, "_Q06HOLD_NO_FETCH": "1"}):
        try:
            frozen_check(env)
            ok = False
        except SystemExit:
            pass
    return ok


def _st_registered():
    import q06hold as E
    return not registered_constants_ok(E)


def _st_wire():
    g0, v0 = "a\n", 'x = 1\nprint("사이트 검증:", 1)\n'
    g1, v1 = wire_texts(g0, v0)
    g2, v2 = wire_texts(g1, v1)
    return bool(g1 == g2 and v1 == v2 and "_q06holdout*" in g1 and v1.index("Q06 방어 스텝 방아쇠 기전 검정") < v1.index('print("사이트 검증:"'))


def _st_names():
    want = ["data/_q06holdout.json", "data/_q06hold_other.json", "data/_q06holdfwd/genesis.json", "x/q06hold_cache/a", "_q06holdout.public.json",
            "data/raw/spdr_long/XLB.csv"]
    ok = all(scan_repo_names([f]) for f in want)
    return bool(ok and not scan_repo_names([MANIFEST_FILE, "data/style_top.json", "build/q06hold_run.py", "build/q06hold.py", "data/_egstep_manifest.json"]))


def _st_manifest_hashes_only():
    doc = manifest_doc()
    return bool(not manifest_problems(doc) and manifest_problems(dict(doc, leak=0.5)) and doc["spdr_long"]["digest"] == SPDR_DIGEST)


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
    import q06hold as E
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    return bool(not any(hasattr(E, n) for n in FORBIDDEN_ENGINE_NAMES) and "_q06holdfwd" not in src and not check_no_forward())


def _st_no_etf_holding():
    """보유는 없다 — 주 목적지 · 시장은 French 포트폴리오 수익 계열(기전 대리)뿐 · SPDR 은 Q06 상태 입력(얼린 상수 대조 · 뜬 판)으로만 이름이 나온다 ·
    엔진에 SPY · 다른 ETF · 선물 · 옵션 · 주식 경로가 없다."""
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    ok = src.count('"XLK"') == 1 and "IX_TR" not in src and '"SPY"' not in src and "stock_path" not in src
    ok &= not any(t in src for t in ('"IVE"', '"IVW"', '"QQQ"', '"SHY"', '"TLT"', "futures", "option_book"))
    ok &= 'VD.l_proxy("V02")' in src and "VD.ff3(\"m\")" in src
    body = src[src.index("def _leg_body(job):"):src.index("def stat_child(job):")]
    ok &= "french_months(VD, hm + rm)" in body and "World" not in body
    return bool(ok)


def _st_predictions_signature():
    """예측 칸 = 등록 §8 의 일곱(참/거짓만) · F0 서명은 정수 · 날짜 글자 · 참/거짓 · 짧은 해시만(실수 없음) · 창의 켜진 달 날짜가 서명에 없다."""
    import q06hold as E
    M = _fake_main()
    P = E.predictions(M)
    ok = set(P) == set(PRED_KO) and len(P) == 7 and all(isinstance(v, bool) for v in P.values())
    f0 = _fake_f0()
    R0 = {"st": f0["st"], "french": f0["french"]}
    sig = E.f0_signature(R0)
    ok &= all(v is None or (isinstance(v, (int, str, bool)) and not isinstance(v, float)) for v in sig.values())
    ok &= not any(isinstance(v, list) for v in sig.values()) and "on_months" not in json.dumps(sig)
    ok &= E.F0_EXPECT is None or set(sig) == set(E.F0_EXPECT)
    ok &= E.F0_EXPECT is None or all(not isinstance(v, float) for v in E.F0_EXPECT.values())
    return bool(ok)


def _st_merge_f0():
    """F0 합치기(순수) — 멈춤 조건(판 해시 · 첫 날 · 시점 · 긴 이력판 첫 달 · 표본 안 동일성 · 창 달 수 · French) · 상태 날짜는 싣지 않는다."""
    import q06hold as E
    f0 = _fake_f0()
    L = dict(f0["st"]["long"], digest=E.SPDR_LONG_DIGEST)
    st = {"long": L, "frozen": f0["st"]["frozen"], "states": {"long": {"D": {"2008-09": 1}}, "frozen": {"D": {}}}}
    fv = {"french": f0["french"]}
    R = merge_f0(st, fv)
    ok = (R["ok"] or bool(R.get("expect_diff"))) and "2008-09" not in json.dumps(R) and set(R) == {"st", "french", "signature", "bad", "ok"} | (
        {"expect_diff"} if E.F0_EXPECT is not None else set())
    ok &= any("늦게 선다" in b for b in merge_f0(dict(st, long=dict(L, first_hi="2006-08")), fv)["bad"])
    ok &= any("SPDR 판" in b for b in merge_f0(dict(st, long=dict(L, digest="0" * 64)), fv)["bad"])
    ok &= any("첫 날" in b for b in merge_f0(dict(st, long=dict(L, d_first="1998-12-21")), fv)["bad"])
    ok &= any("시점" in b for b in merge_f0(dict(st, frozen=dict(st["frozen"], timing_ok=False)), fv)["bad"])
    ok &= any("배치 Q 기록" in b for b in merge_f0(dict(st, frozen=dict(st["frozen"], ref_same_as_egstep=False)), fv)["bad"])
    ok &= any("달 수" in b for b in merge_f0(dict(st, long=dict(L, hold=dict(L["hold"], n=119))), fv)["bad"])
    ok &= any("French" in b for b in merge_f0(st, dict(fv, french=dict(fv["french"], n_months=239)))["bad"])
    return bool(ok)


def _st_bundle_digest():
    tmp = tempfile.mkdtemp(prefix="q06hold_st_bdl_")
    try:
        for t in ("AAA", "BBB", "^X"):
            with open(os.path.join(tmp, t.replace("^", "_") + ".csv"), "wb") as f:
                f.write(("Date,Close\n2020-01-02,%s\n" % t).encode())
        dg, n, miss = bundle_digest_std(["BBB", "AAA", "^X", "ZZZ"], tmp)
        want = "".join("%s\t%s\n" % (t, _sha_file(os.path.join(tmp, t.replace("^", "_") + ".csv"))) for t in sorted(["AAA", "BBB", "^X"]))
        return bool(n == 3 and miss == 1 and dg == hashlib.sha256(want.encode("utf-8")).hexdigest())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_git_blob():
    return git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391" and git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


SELFTESTS = (_st_state_counts, _st_net_series, _st_on_off_and_hac, _st_placebo, _st_kt_fa, _st_verdict_predictions, _st_long_history_rules,
             _st_q06_frozen, _st_blob_guard, _st_lock_and_tag, _st_purge_stale, _st_public_and_result_doc, _st_result_write_guard,
             _st_scrub, _st_start_guard, _st_frozen_refuses, _st_registered, _st_wire, _st_names, _st_manifest_hashes_only, _st_open_encoding, _st_std_head,
             _st_smoke_no_sizes, _st_no_forward, _st_no_etf_holding, _st_predictions_signature, _st_merge_f0, _st_bundle_digest, _st_git_blob)


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
    if "--fetch-spdr" in argv:
        print(json.dumps(fetch_spdr_long(), ensure_ascii=False))
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
    if "--internal-doc" in argv:
        P = paths()
        if not (os.path.exists(P["mark"]) and FINISHED in _read_text(P["mark"])):
            raise SystemExit("🚨 FINISHED 표식이 없다 — 내부 판은 끝난 굽기에서만.")
        _write_text(P["internal"], internal_doc(json.loads(_bytes(P["out"]).decode("utf-8"))))
        print("→ %s (저장소 밖 · 공개 금지)" % P["internal"])
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
