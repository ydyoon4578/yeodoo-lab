# -*- coding: utf-8 -*-
"""build/dstk_run.py — D13 주식판(DSTK) 한 번 굽기 러너.

사전등록: build/PREREG-<등록 날짜>-DSTK.md 하나(이 러너는 날짜를 박지 않는다 · 결과 문서 = 그 이름 + «-RESULT»).
계산은 build/dstk.py(엔진)가 한다 — 이 러너는 판 점검 · 핀 판 임시 뿌리 · 자식 과정 · 시작 표식 · 게시 칸 · 결과 문서만 맡는다.

🚨 사용자 지시(2026-09-27): «내가 뽑은 스타일 top10 종목 있잖아 그걸로 진행해봐. 10종목이 너무 적으면 20 30 등 변경해서도 확인해보고»
   — D13(실질금리 스타일 로테이션)을 ETF 없이 랩 스타일 명단(spval · grow)으로 · N = 10 · 20 · 30 · 펀드 어디에도 ETF 없음 · 선물 · 옵션 없음 ·
   «백테스트 최대 20년» · «미래 일정 다 꺼»(전방 원장 · 날짜가 박힌 미래 판정 없음 — data/_dstkfwd/ 가 있으면 멈춘다).
🚨 랩 규율: 등록 커밋이 origin 에 오르기 전에는 --selftest · --guard · --pins · --manifest · --precommit · --wire · --f0 · --smoke 만 된다.
   --f0 는 개수 · 날짜 · 동일성 · 시장 상태 개수(DFII10 국면 · 하락월)만 · --smoke 는 눈가린 채(산출을 열지 않고 지운다 · 참/거짓 · 초만 싣는다).
   창이 10년(보유 2016-09 ~ 2026-08)이라 모든 값이 공개 창 안이다(MAX_YEARS 10) — 그래도 산출 원본은 저장소 밖 캐시에만 두고 게시 칸만 결과 문서로 옮긴다.

  python -X utf8 build/dstk_run.py --selftest           합성만(실자료 없음)
  python -X utf8 build/dstk_run.py --guard              사이트 경계(site_guard_std — 참/거짓 · 이름만)
  python -X utf8 build/dstk_run.py --pins               얼린 파일 · 핀 표(등록 문서 §7 표)
  python -X utf8 build/dstk_run.py --f0                 등록 전 F0(작업 트리 · 수익 없음 · 개수만) — 등록 문서 §7 의 F0 표 · 엔진 F0_EXPECT 의 출처
  python -X utf8 build/dstk_run.py --manifest           data/_dstk_manifest.json(해시만) 쓰기
  python -X utf8 build/dstk_run.py --wire [--apply]     등록 커밋이 .gitignore · build/validate_site.py 끝에 덧붙일 덩이
  python -X utf8 build/dstk_run.py --precommit          등록 커밋 직전 점검(참/거짓 · 이름만)
  python -X utf8 build/dstk_run.py --smoke              러너 경로 전체 눈가린 연기(임시 폴더 · 열지 않고 지운다)
  DSTK_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python -X utf8 build/dstk_run.py --once     한 번 굽기(이 길 하나뿐)
  python -X utf8 build/dstk_run.py --public-view        굽기 뒤: 산출 → 게시 칸 다시 쓰기(FINISHED 표식이 있을 때만)
  python -X utf8 build/dstk_run.py --result-doc [<게시 칸 파일>] [--reg-err <글 파일>] [--write]   결과 문서(게시 칸 파일 하나만 읽는 얼린 렌더러 ·
                                                     --reg-err = 굽기 뒤 찾은 등록 오류 글(소수는 <num> 으로 지운다 · 파일 sha 를 머리에 싣는다))

한 번 굽기 규약(g_fund_run · x_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(실패하면 멈춘다).
  · DSTK_COMMIT = 사전등록 문서 · 러너 · 엔진 · 명세(data/_dstk_manifest.json)를 **처음 더한** 커밋 · origin/main 의 조상 · 그 커밋의 등록 문서에 빈칸(⟨TBD)과 초안 괄호(U+3014)가 없다.
  · 얼린 파일(엔진 · 러너 · 명세 · 등록 문서 · 덧붙임 두 곳)이 그 커밋과 바이트 단위로 같다(CRLF 무시).
  · 자료 핀 — 굽기는 작업 트리의 data/ 를 읽지 않는다. DATA_PIN 의 build/ · data/ 를 git archive 로 저장소 밖 임시 뿌리에 풀고(트리 sha 대조)
    엔진 하나만 등록 커밋 판으로 넣어 자식 과정으로 돈다. 채점 가격(V-D1 · 저장소 밖 캐시)은 묶음 해시(엔진 VD1_DIGEST)가 같아야 쓴다.
  · 판 점검 → F0(수익 없음 · 등록 F0 개수와 같아야) → 시작 표식 셋(로컬 둘 · origin 태그 dstk-started) → 굽기 → 산출 · 게시 칸 · 실행 기록 → FINISHED.
    F0 가 실패하면 표식을 쓰기 전에 멈춘다(한 번 굽기를 쓰지 않는다). 굽기 자식 안의 등록된 멈춤(StopBake · 가격 위생 관문 등)은 {"stopped": 사유} 가 산출이 된다.
    게시 칸(공개 안전 점검)을 산출보다 먼저 짓는다 — 걸리면 아무 산출도 쓰지 않는다. --result-doc --write 는 연기 판 · FINISHED 없음 · sha 불일치면 거절.
  · FINISHED 가 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤 · 산출 전 기술적 중단이면 이 컴퓨터의 같은 커밋 표식이 있을 때만 DSTK_RERUN=사유 로 처음부터.
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
import tarfile
import tempfile
import time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
# 🔒 모듈 머리에서는 표준 라이브러리만 — build/validate_site.py 가 site_guard_std 를 부른다(numpy 없이). 엔진은 함수 안에서만 불러온다.


# ══════════════════════════════════════════════════════════════════════════
#  등록 문서 · 얼린 파일 · 핀
# ══════════════════════════════════════════════════════════════════════════
def _find_prereg():
    c = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-DSTK.md")))
    return ("build/" + c[0]) if len(c) == 1 else "build/PREREG-0000-00-00-DSTK.md", len(c)


PREREG, _N_PREREG = _find_prereg()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"
ENGINE = "build/dstk.py"
RUNNER = "build/dstk_run.py"
MANIFEST_FILE = "data/_dstk_manifest.json"
FIRST_ADDED = (PREREG, RUNNER, ENGINE, MANIFEST_FILE)
FROZEN = (ENGINE, RUNNER, MANIFEST_FILE, PREREG)
REPO_ALLOWED_DSTK = (MANIFEST_FILE,)
FORWARD_DIR = "data/_dstkfwd"                                 # 있으면 멈춘다(전방 원장 없음 — 사용자 2026-09-27 «미래 일정 다 꺼»)
DATA_PIN = "44c1a26f6a8fd9f64a3a76de9334e1a37aef403b"       # origin/main 2026-09-27(배치 W 결과 갱신 피드) — 이 설계가 F0 를 센 판
DATA_PIN_TREES = {"data": "d72aec6dd1e268d66144ed8d21e05deb11950b98", "build": "fe772a6fde82d618833c9f4be0c9851d343318b1"}
# 엔진이 읽는 자료 파일(핀 판 blob — 임시 뿌리에서 다시 대조한다 · 트리 sha 가 이미 전부를 묶지만 읽는 것을 이름으로 적는다)
DATA_PIN_FILES = ("data/stocks.json", "data/pit_px.json", "data/_pit_px_cache.json", "data/index_history.json", "data/assets.json",
                  "data/bench_px.json", "data/rf_monthly.json", "data/ff_daily.json", "data/pit_universe.json", "data/pit_reuse.json",
                  "data/index_ledger.json", "data/splits.json", "data/style_top.json", "data/style_perf.json", "data/_qbatch.json",
                  "data/_fund_mix.json", "data/mech_episodes.json")
ENGINE_IMPORTS = ("style_top_pdf", "style_pit_panel", "pit_panel", "pit_alias", "pit_quarantine", "tech_backtest", "index_members",
                  "qbatch_core", "eg30plus", "qg_lab", "g_fund", "v_tests", "t_signals", "t_data")
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"
SMOKE_ENV_KEYS = ("DSTK_SMOKE",)
VD1_DIR = os.environ.get("DSTK_VD1") or os.path.join(tempfile.gettempdir(), "vbatch_cache", "raw", "vd1")
# 등록 상수 — 엔진(dstk)의 값과 같아야 굽는다(등록 문서 §1 ~ §6)
REGISTERED = {
    "NS": (10, 20, 30), "NMAX": 30, "CAP": 0.25, "STYLE_KEYS": {"V": "val", "G": "grow"}, "SCREEN_KEYS": {"V": "spval", "G": "grow"},
    "STYLE_REFS": {"V": "S&P 500 Value (S&P U.S. Style)", "G": "S&P 500 Growth (S&P U.S. Style)"},
    "MIN_NAMES": 100, "LAG_DAYS": 45, "ANN_LAG_DAYS": 90, "THR": 0.20, "W_V": {"value": 0.70, "neutral": 0.50, "growth": 0.30}, "LAG_M": 3,
    "SLEEVE": 0.10, "COST": 0.0010, "COST20": 0.0020, "TURN_MAX": 10.0, "HOLD": ("2016-09", "2026-08"), "N_HOLD": 120,
    "FORM_WARM": "2016-07", "FORM_FIRST": "2016-08", "FORM_LAST": "2026-07", "ANCHOR_FORM": "2026-08", "ANCHOR_MIN": 8, "EXEC_LAG": 1,
    "HOLM_ALPHA": 0.05, "NW_LAG": 3, "DIRECTION": 1, "F0A_CORR": 0.98, "F0A_GAP": 0.30, "COV_LATE": 0.80, "VD1_N": 518,
    "VD1_ROUND": 0.0051, "VD1_TOL": 0.002, "VD1_END_TOL": 0.005, "SPLIT_TOL": 0.002,
    "PRIMARY": ("A10", "A20", "A30"), "CUM_N_BEFORE": 985, "N_ROWS_COUNTED": 13,
    "VD1_DIGEST": '1f552d177d0699c7aa4c9f7779e2c0c463e2f2057e3663b623b00e4adf6ffd4c', "LATE_FROM": '2019-06',
    "F0_EXPECT": {'n_forms': 121, 'n_valid': 121, 'first_valid': '2016-07', 'cov_late_from': '2019-06', 'n_pool_min': 464, 'n_pool_max': 521, 'v_scored_min': 144, 'v_scored_max': 483, 'g_scored_min': 462, 'n_asis_min': 400, 'regime_value': 36, 'regime_neutral': 53, 'regime_growth': 31, 'regime_switches': 41, 'regime_warm': 'neutral', 'regime_edge': 5, 'down_n': 39, 'down_frozen_n': 35, 'vd1_n': 518, 'vd1_used': 518, 'vd1_fallback': 0, 'anchor_val_adj': 10, 'anchor_grow_adj': 10, 'anchor_val_wrap': 10, 'anchor_grow_wrap': 10, 'asis_missing_n_names': 140, 'split_rev_rows': 37, 'split_rev_names': 31, 'split_rev_cells': 1538, 'splits_json_not_vd1': 0, 'lvl_adj_first': 123, 'lvl_adj_min': 5, 'lvl_adj_max': 123, 'lvl_pr_first': 34, 'reassigned_cells': 10, 'seam_cut_names': 93, 'home_val_overlap': 8, 'home_grow_overlap': 9},
}
FORBIDDEN_ENGINE_NAMES = ("ff1", "ff2", "ff0", "forward_ledger", "genesis")    # 전방 판정 · 원장 함수가 엔진에 없어야 한다


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록 · 임시 뿌리는 모두 저장소 밖(<캐시>)
# ══════════════════════════════════════════════════════════════════════════
CACHE = os.environ.get("DSTK_CACHE") or os.path.join(tempfile.gettempdir(), "dstk_cache")
GIT_MARK_NAME = "dstk_started"
START_TAG = "dstk-started"
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}
OUT_NAMES = {"out": "_dstkout.json", "mark": "_dstkout.started", "runlog": "_dstkout.run.json", "public": "_dstkout.public.json"}
CACHE_ONLY_KEY = "__dstk_cache_only__"
PUBLIC_FROM = "2016-09"
PUBLIC_FLOAT_KEYS = re.compile(r"(^|_)(coverage|frac|tol|min|max|thr|sec)(_|$)")
COUNT_KEYS = re.compile(r"(^n$|^n_|_n$|count|^k$|months?$|days?$|years?$|^rows$|bytes$|names|forms)")
OUTPUT_NAME_MARKS = ("_dstkout",)
OUTPUT_CONTENT_MARKS = (CACHE_ONLY_KEY.encode(), b"_dstkout.json", b"_dstkout.public.json", b"_dstkout.run.json", b'"dstk_public_view"')


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
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith("_dstkout") and (f.endswith(".json") or f.endswith(".part"))]
    return sorted({p for p in have if os.path.exists(p)})


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
        if f.startswith("data/_dstk") and f not in REPO_ALLOWED_DSTK:
            bad.append("허용 밖 파일: %s" % f)
        if f.startswith(FORWARD_DIR + "/") or f == FORWARD_DIR:
            bad.append("전방 원장 파일(사용자 2026-09-27 «미래 일정 다 꺼»): %s" % f)
        if "dstk_cache" in f:
            bad.append("캐시 사본으로 보이는 파일: %s" % f)
    return bad


def site_guard_std(root=None):
    """DSTK 사이트 경계 — git 이 추적 · 추가 예정인 파일 가운데 (가) 굽기 산출 이름(_dstkout*) (나) 허용 밖 data/_dstk* (다) 전방 원장 data/_dstkfwd/*
    (라) 명세(data/_dstk_manifest.json)가 해시만인가 (마) 사이트 자료(뿌리 *.html · js/*.js · data/*.json)의 굽기 산출 표식."""
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
            bad.append("사이트 자료 %s 에 DSTK 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


# ── 덧붙임 두 곳(.gitignore · validate_site) ─────────────────────────────
GITIGNORE_BLOCK = """
# D13 주식판(PREREG-*-DSTK · 사용자 2026-09-27 «스타일 top10 으로 · 20 30 도») — 굽기 산출(_dstkout.json · _dstkout.public.json · _dstkout.run.json · _dstkout.started)이나
#   캐시 사본(dstk_cache)이 작업 트리에 복사돼도 쓸려 들지 않게. 명세(data/_dstk_manifest.json)는 «_dstk_» 라 걸리지 않는다.
_dstkout*
dstk_cache/
"""
VALIDATE_BLOCK = """
# ── D13 주식판(PREREG-*-DSTK · 사용자 2026-09-27) 사이트 경계 ─────────────────────────────
# 굽기 산출(_dstkout*)이 저장소 · 사이트 자료에 없어야 한다. data/_dstk* 는 해시만 담은 명세(_dstk_manifest) 하나뿐 ·
#   data/_dstkfwd/ 없음(전방 원장 없음 · 사용자 2026-09-27 «미래 일정 다 꺼») · 사이트 자료에 굽기 산출 표식 없음.
#   build/dstk_run.py 는 모듈 머리에서 표준 라이브러리만 불러온다(site_guard_std). 러너(dstk_run.frozen_check)도 같은 함수를 부른다.
try:
    import importlib as _il_dstk
    _dsr = _il_dstk.import_module("dstk_run")
    _gds = _dsr.site_guard_std(ROOT)
    if not _gds["ok"]:
        errors.append("D13 주식판 사이트 경계 위반 %d건 — %s. 굽기 산출(_dstkout*)은 저장소 밖 캐시에만 둔다"
                      % (_gds.get("n_bad", len(_gds["bad"])), " · ".join(_gds["bad"][:4])))
    else:
        print("  ~ D13 주식판 사이트 경계 통과(파일 %d · 사이트 자료 %d 훑음)" % (_gds["n_files"], _gds["n_scanned"]))
except Exception as _e:
    # 닫힌 쪽 — 이 경계를 확인하지 못하면 통과시키지 않는다(GURUFUND 와 같은 규약)
    errors.append("D13 주식판 사이트 경계 검사가 예외로 죽었다 — %s (확인하지 못하면 통과시키지 않는다)" % str(_e)[:80])
"""
_VALIDATE_ANCHOR = 'print("사이트 검증:"'


def wire_texts(gitignore_txt, validate_txt):
    g = gitignore_txt
    if "_dstkout*" not in g:
        g = g.rstrip("\n") + "\n" + GITIGNORE_BLOCK
    v = validate_txt
    if "D13 주식판(PREREG-*-DSTK" not in v:
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
#  이름 · 등록 상수 · 명세
# ══════════════════════════════════════════════════════════════════════════
def name_check():
    bad = []
    if _N_PREREG != 1:
        bad.append("build/PREREG-*-DSTK.md 가 %d 개" % _N_PREREG)
    elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-DSTK\.md", PREREG):
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
        import dstk as E
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


def code_shas():
    return {p: (_sha_lf(_bytes(os.path.join(ROOT, *p.split("/"))))[:16] if os.path.exists(os.path.join(ROOT, *p.split("/"))) else None)
            for p in (ENGINE, RUNNER)}


def manifest_doc():
    """data/_dstk_manifest.json — 해시만(값 없음)."""
    def rp(c, spec):
        r = _git("rev-parse", "%s:%s" % (c, spec))
        return r.stdout.strip() if r.returncode == 0 else None
    return {"kind": "dstk_manifest", "note": "D13 주식판(DSTK) 명세 — 해시만(값 없음). 러너 판 점검이 이 파일을 등록 커밋 판과 대조한다.",
            "prereg": PREREG, "engine": ENGINE, "runner": RUNNER,
            "code_sha256_lf": {p: (_sha_lf(_bytes(os.path.join(ROOT, *p.split("/")))) if os.path.exists(os.path.join(ROOT, *p.split("/"))) else None)
                               for p in (ENGINE, RUNNER)},
            "data_pin": {"commit": DATA_PIN, "trees": dict(DATA_PIN_TREES),
                         "reused_modules_blob": {("build/%s.py" % m): rp(DATA_PIN, "build/%s.py" % m) for m in ENGINE_IMPORTS},
                         "read_files_blob": {f: rp(DATA_PIN, f) for f in DATA_PIN_FILES}},
            "vd1": {"digest": REGISTERED["VD1_DIGEST"], "n": str(REGISTERED["VD1_N"]),
                    "source": "yfinance history(period='max', auto_adjust=False, actions=True) · Close(야후 분할 행으로 나눈 값 — 분사를 분할로 적은 비정수 행 포함 · 배당 없음) · Dividends · Stock Splits · 배치 V 캐시(vbatch_cache/raw/vd1 · 저장소 밖)",
                    "rule": "sha256(«티커\\t파일 sha256\\n» 을 stocks.json 오늘 이름 차례로)", "license": "yfinance — 개인 사용 · 캐시만 · 값은 싣지 않는다"},
            "start_tag": START_TAG, "git_mark": GIT_MARK_NAME, "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼»"}


def write_manifest():
    doc = manifest_doc()
    bad = manifest_problems(doc)
    if bad:
        raise SystemExit("🚨 명세가 해시만이 아니다: %s" % bad[:3])
    miss = [k for k, v in doc["data_pin"]["reused_modules_blob"].items() if v is None] + [k for k, v in doc["data_pin"]["read_files_blob"].items() if v is None]
    if miss:
        raise SystemExit("🚨 핀 커밋에 없는 파일: %s" % ", ".join(miss))
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
    for k in ("data_pin", "vd1", "prereg", "start_tag"):
        if doc.get(k) != want.get(k):
            bad.append("명세 %s 가 러너 상수와 다르다" % k)
    bad += manifest_problems(doc)
    return bad


def pins_check():
    """핀 커밋 · 트리가 등록 값과 같은가(git 개체만 · 자료를 열지 않는다)."""
    bad = []
    if _git("cat-file", "-e", DATA_PIN + "^{commit}").returncode != 0:
        bad.append("핀 커밋 %s 가 없다" % DATA_PIN[:9])
    elif _git("merge-base", "--is-ancestor", DATA_PIN, "origin/main").returncode != 0:
        bad.append("핀 커밋 %s 가 origin/main 의 조상이 아니다" % DATA_PIN[:9])
    for spec, sha in DATA_PIN_TREES.items():
        r = _git("rev-parse", "%s:%s" % (DATA_PIN, spec))
        if r.returncode != 0 or r.stdout.strip() != sha:
            bad.append("핀 %s:%s 가 등록 값과 다르다" % (DATA_PIN[:9], spec))
    return bad


def pin_blobs():
    """임시 뿌리 대조용 — 핀 커밋의 읽는 자료 파일 blob."""
    out = {}
    for f in DATA_PIN_FILES:
        r = _git("rev-parse", "%s:%s" % (DATA_PIN, f))
        if r.returncode != 0:
            raise SystemExit("🚨 핀 커밋에 %s 가 없다" % f)
        out[f] = r.stdout.strip()
    return out


def vd1_problems():
    """V-D1 묶음 해시(등록 값) — 캐시가 저장소 밖 · 이름 수 · 해시(엔진 vd1_digest 와 같은 규칙)."""
    import dstk as E
    if _inside(VD1_DIR, ROOT):
        return ["V-D1 폴더가 저장소 안이다"]
    # 오늘 이름 목록은 **핀 판** stocks.json 에서 읽는다(등록 뒤 CI 가 작업 트리 stocks.json 을 갈아도 굽기 자식이 읽는 판과 같게)
    b = _git_bytes("show", "%s:data/stocks.json" % DATA_PIN)
    if b.returncode != 0:
        return ["핀 판 data/stocks.json 을 읽지 못했다"]
    S = json.loads(b.stdout.decode("utf-8"))
    dg, n, miss = E.vd1_digest([s["t"] for s in S["stocks"]], VD1_DIR)
    bad = []
    if n != REGISTERED["VD1_N"]:
        bad.append("V-D1 이름 %d(등록 %d)" % (n, REGISTERED["VD1_N"]))
    if REGISTERED["VD1_DIGEST"] is None or dg != REGISTERED["VD1_DIGEST"]:
        bad.append("V-D1 묶음 해시가 등록 값과 다르다")
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
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 DSTK_RERUN=사유 로 처음부터." % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 DSTK_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다.")
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
    """시작 태그를 민다. 이미 같은 커밋을 가리키면 DSTK_RERUN(산출 전 기술적 중단의 다시 굽기)일 때만 «already» — 아니면 멈춘다(동시 굽기 막기)."""
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
            raise SystemExit("🚨 origin 시작 태그가 이미 이 커밋을 가리킨다 — 다른 굽기가 시작했다(DSTK_RERUN 이 아니면 굽지 않는다).")
        return "already"
    if have is not None:
        raise SystemExit("🚨 origin 시작 태그가 다른 커밋(%s)을 가리킨다." % have[:8])
    r1 = _git("tag", "-f", START_TAG, commit)
    r2 = _git("push", "--quiet", "origin", "refs/tags/%s:refs/tags/%s" % (START_TAG, START_TAG))
    if r1.returncode != 0 or r2.returncode != 0 or _remote_start_tag() != commit:
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다 — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 DSTK_RERUN).")
    return "pushed"


LOCK_NAME = "_dstk_bake.lock"


def _take_lock(P, commit):
    """배타 잠금(O_EXCL) — 판 점검 뒤 · 핀 뿌리 F0 전에 잡는다. 두 번째 --once 는 여기서 멈춘다(동시 굽기 막기).
    과정이 강제로 죽으면 잠금이 남는다 — 다른 굽기가 돌지 않음을 확인하고 지운 뒤 DSTK_RERUN=사유 로."""
    lk = os.path.join(P["dir"], LOCK_NAME)
    try:
        fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("🚨 굽기 잠금이 있다(%s) — 다른 굽기가 돌고 있다. 돌고 있지 않으면 확인 뒤 지우고 DSTK_RERUN=사유 로." % lk)
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
#  핀 판 임시 뿌리 · 자식 과정
# ══════════════════════════════════════════════════════════════════════════
def materialize(dest, commit, blobs):
    """git archive <commit> build + data → dest(저장소 밖) · 핀 blob 대조 · 엔진 하나만 작업 트리(= 등록 커밋 판) 것으로 넣는다."""
    if _inside(dest, ROOT):
        raise SystemExit("🚨 임시 뿌리가 저장소 안이다.")
    os.makedirs(dest, exist_ok=True)
    for part in ("build", "data"):
        pr = subprocess.Popen(["git", "-C", ROOT, "archive", "--format=tar", commit, part], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        with tarfile.open(fileobj=pr.stdout, mode="r|") as tf:
            tf.extractall(dest, filter="data")
        pr.stdout.close()
        if pr.wait() != 0:
            raise SystemExit("🚨 git archive %s %s 실패" % (commit[:9], part))
    bad = [f for f, want in blobs.items() if not os.path.exists(os.path.join(dest, *f.split("/"))) or git_blob_sha(_bytes(os.path.join(dest, *f.split("/")))) != want]
    if bad:
        raise SystemExit("🚨 임시 뿌리 %s 의 핀 파일이 등록 값과 다르다: %s" % (commit[:9], ", ".join(bad)))
    shutil.copyfile(os.path.join(ROOT, *ENGINE.split("/")), os.path.join(dest, *ENGINE.split("/")))
    return dest


def run_child(tree, mode, out_path, timeout=6 * 3600):
    env = dict(os.environ)
    env.update(ENV_PINS)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "DSTK_VD1": VD1_DIR})
    for k in SMOKE_ENV_KEYS + ("DSTK_COMMIT", "DSTK_RERUN"):
        env.pop(k, None)
    t = time.time()
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(tree, *ENGINE.split("/")), "--child", mode, "--out", out_path],
                       cwd=tree, env=env, capture_output=True, timeout=timeout)
    sec = round(time.time() - t, 1)
    if r.returncode != 0 or not os.path.exists(out_path):
        tail = _scrub(r.stderr.decode("utf-8", "replace"))[-2500:]
        raise SystemExit("🚨 자식 과정(%s) 실패 — 산출을 쓰지 않았다:\n%s" % (mode, tail))
    return sec


def preflight(work):
    """F0(핀 뿌리 · 수익 없음 · 등록 F0 개수 대조) — 통과해야 표식을 쓴다."""
    t0 = time.time()
    tm = materialize(os.path.join(work, "tree_main"), DATA_PIN, pin_blobs())
    p_0 = os.path.join(work, "child_f0.json")
    sec_0 = run_child(tm, "f0", p_0)
    f0 = _read_json(p_0)
    if not f0.get("ok"):
        raise SystemExit("🚨 F0 실패 — %s (굽지 않는다)" % "; ".join(f0.get("bad") or ["?"]))
    return {"f0": f0, "tree_main": tm, "sec": {"f0": sec_0, "total": round(time.time() - t0, 1)}}


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def frozen_check(env=None):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("DSTK_COMMIT")
    if not c:
        raise SystemExit("🚨 DSTK_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --pins · --f0 · --manifest · --precommit · --smoke 만 된다.")
    nb = name_check()
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_DSTK_NO_FETCH"):
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
    rerun = env.get("DSTK_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag() if (real or not env.get("_DSTK_NO_FETCH")) else env.get("_DSTK_REMOTE_TAG")
    start_guard(full, rerun, marks, remote)
    for p in FROZEN + (".gitignore", "build/validate_site.py"):
        fp = os.path.join(ROOT, *p.split("/"))
        want = _git_bytes("show", "%s:%s" % (full, p))
        if want.returncode != 0:
            raise SystemExit("🚨 %s 가 등록 커밋에 없다." % p)
        if not os.path.exists(fp) or _sha_lf(_bytes(fp)) != _sha_lf(want.stdout):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    gw, vw = wired_state()
    if not (gw and vw):
        raise SystemExit("🚨 덧붙임 두 곳이 붙지 않았다(.gitignore %s · validate_site %s) — `dstk_run.py --wire --apply` 를 등록 커밋에." % (gw, vw))
    pb = pins_check()
    if pb:
        raise SystemExit("🚨 자료 핀: %s" % "; ".join(pb[:4]))
    mb = manifest_check()
    if mb:
        raise SystemExit("🚨 명세: %s" % "; ".join(mb[:4]))
    vb = vd1_problems()
    if vb:
        raise SystemExit("🚨 채점 가격(V-D1): %s" % "; ".join(vb))
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
    if smoke and not os.path.basename(os.path.dirname(os.path.abspath(P["dir"]))).startswith("dstk_runner_smoke_"):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/dstk_runner_smoke_*/out 이 아니다.")
    if not smoke and _OVR["out"]:
        raise SystemExit("🚨 진짜 굽기에 연기 경로가 켜져 있다.")
    lk = _take_lock(P, commit)                                # 배타 잠금 — 동시 --once 는 여기서 멈춘다
    try:
        # 잠근 뒤 다시 본다(판 점검과 잠금 사이에 다른 굽기가 끝났거나 시작했을 수 있다): 산출 · 표식 · 시작 태그
        outs = _existing_outputs(P)
        if outs:
            raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다." % ", ".join(os.path.basename(o) for o in outs))
        start_guard(commit, rerun, [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)], _tag_now())
        return _bake_locked(P, commit, rerun, smoke, t0)
    finally:
        _release_lock(lk)


def _bake_locked(P, commit, rerun, smoke, t0):
    work = tempfile.mkdtemp(prefix="dstk_work_", dir=os.path.dirname(P["dir"]) if smoke else cache_guard_std())
    try:
        pf = preflight(work)                                  # 표식 전 — 실패하면 한 번 굽기를 쓰지 않는다
        started = (_read_text(P["mark"] if os.path.exists(P["mark"]) else P["gitmark"]).strip() if rerun
                   else "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S")))
        for m in (P["mark"], P["gitmark"]):
            if not os.path.exists(m):
                _write_text(m, started + "\n")
        tag = _push_start_tag(commit, rerun)
        p_m = os.path.join(work, "child_main.json")
        err = []
        try:
            sec_m = run_child(pf["tree_main"], "main", p_m)
        except SystemExit as e:
            raise SystemExit("🚨 굽기 계산 실패 — 산출을 쓰지 않았다(산출 전 기술적 중단이면 DSTK_RERUN=사유 로 처음부터 · 같은 얼린 코드로만):\n%s" % str(e)[-2000:])
        main = _read_json(p_m)
        out = {CACHE_ONLY_KEY: True, "kind": "dstk_bake", "prereg": PREREG, "prereg_commit": commit, "smoke": smoke,
               "data_pin": DATA_PIN, "f0": pf["f0"], "main": main}
        blob = (json.dumps(out, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        sha = hashlib.sha256(blob).hexdigest()
        rec = {"commit": commit, "registration_error": err, "smoke": smoke}
        pub = public_doc(out, sha, len(blob), rec)               # 공개 안전에 걸리면 여기서 멈춘다 — 산출을 쓰기 전
        pub_txt = json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n"
        with open(P["out"] + ".part", "wb") as f:
            f.write(blob)
        os.replace(P["out"] + ".part", P["out"])
        _write_text(P["public"], pub_txt)
        del out, main
        runlog = {"prereg": PREREG, "prereg_commit": commit, "runner": RUNNER, "engine": ENGINE, "started": started, "rerun": rerun, "start_tag": tag,
                  "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "sec": round(time.time() - t0, 1),
                  "clock": {"preflight": pf["sec"], "main": sec_m}, "out": os.path.basename(P["out"]), "out_sha256": sha,
                  "public": os.path.basename(P["public"]), "public_sha256": _sha_file(P["public"]),
                  "env": {k: os.environ.get(k) for k in ENV_PINS}, "versions": _versions(), "frozen": list(FROZEN),
                  "data_pin": DATA_PIN, "code_sha": code_shas(), "registration_error": err, "smoke": smoke,
                  "note": "값 없음 — 결과는 _dstkout.public.json 의 칸만 결과 문서로 옮긴다(등록 §6 공개 규칙)"}
        _write_text(P["runlog"], json.dumps(runlog, ensure_ascii=False, indent=1) + "\n")
        _mark_finished(P, sha)
        if not smoke:
            print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)" % (P["out"], sha[:16], runlog["sec"]))
        return runlog
    finally:
        shutil.rmtree(work, ignore_errors=True)


def once():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("DSTK_RERUN"))


# ══════════════════════════════════════════════════════════════════════════
#  게시 칸(10년 창 · 전부 공개 창 안)
# ══════════════════════════════════════════════════════════════════════════
PUB_METRIC_KEYS = ("n", "ann_ex", "cagr_ex", "cagr_fund", "cagr_index", "te", "ir", "t_iid", "nw_t", "win", "years", "years_won", "n_years",
                   "years_won_full", "n_full_years", "down_n", "down_mean", "down_t", "down_win", "up_mean", "up_win", "down_capture", "up_capture",
                   "sleeve_beta", "episodes", "crash_won", "surge_won", "mech", "roll12", "roll36", "style", "mdd_fund", "mdd_index", "halves",
                   "blocks", "turn", "shift", "window")
PUB_DIFF_KEYS = ("n", "mean_ann", "nw_t", "t_iid", "win", "down_mean", "up_mean", "years_won_full", "n_full_years", "d_ir", "style", "window")
F0_PUB_KEYS = ("ok", "bad", "builder", "screen", "ps", "regime", "down", "forms", "anchor", "asis_missing_top", "asis_missing_n_names", "expect_diff",
               "home", "inherited")


def _pick(d, keys):
    return {k: d.get(k) for k in keys if k in (d or {})}


def public_doc(out, sha=None, nbytes=None, rec=None):
    """게시 칸 — 결과 문서가 옮길 수 있는 칸만(10년 창 값 · F0 개수 · 날짜 · 참/거짓). public_safe_std 를 통과해야 쓴다."""
    rec = rec or {}
    f0, M = out.get("f0") or {}, out.get("main") or {}
    f0v = _pick(f0, F0_PUB_KEYS)
    f0v["vd1"] = {"n": (f0.get("vd1") or {}).get("n"), "digest16": ((f0.get("vd1") or {}).get("digest") or "")[:16]}
    pv = {"dstk_public_view": True, "prereg": out.get("prereg"), "prereg_commit": rec.get("commit"), "out_sha256": sha, "out_bytes": nbytes,
          "smoke": bool(rec.get("smoke")), "registration_error": list(rec.get("registration_error") or []),
          "stopped": M.get("stopped"), "data_pin": out.get("data_pin"), "f0": f0v,
          "forward": "없음 — 사용자 2026-09-27 «미래 일정 다 꺼» (전방 원장 · 날짜가 박힌 미래 판정 없음)"}
    if not M.get("stopped"):
        rows = {}
        for k, v in (M.get("rows") or {}).items():
            rows[k] = {"m": _pick(v.get("m") or {}, PUB_METRIC_KEYS), "m20": v.get("m20"), "down_frozen": v.get("down_frozen"), "harmless": v.get("harmless")}
        late = None
        if M.get("late"):
            late = {"from": M["late"]["from"], "window": [M["late"]["from"], "2026-08"],
                    "rows": {k: _pick(v, PUB_METRIC_KEYS) for k, v in M["late"]["rows"].items()},
                    "mech": {n: _pick(v, PUB_DIFF_KEYS) for n, v in M["late"]["mech"].items()}}
        pv.update({"window": M.get("window"), "n_hold": M.get("n_hold"), "down": M.get("down"), "f0a": M.get("f0a"), "rows": rows,
                   "holm": M.get("holm"), "adopt": M.get("adopt"), "verdict": M.get("verdict"),
                   "mech": {n: {"fund": _pick(v["fund"], PUB_DIFF_KEYS), "sleeve": v["sleeve"]} for n, v in (M.get("mech") or {}).items()},
                   "diffs": {nm: {n: _pick(v, PUB_DIFF_KEYS) for n, v in d.items()} for nm, d in (M.get("diffs") or {}).items()},
                   "fidelity": M.get("fidelity"), "late": late, "composition": M.get("composition"), "regime": M.get("regime"),
                   "eg30_ref": M.get("eg30_ref"), "xbmrot_ref": M.get("xbmrot_ref"), "predictions": M.get("predictions"),
                   "multiplicity": M.get("multiplicity"), "ps_info": M.get("ps_info"), "tilt_read": M.get("tilt_read")})
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
                     {"commit": out.get("prereg_commit"), "registration_error": rl.get("registration_error"), "smoke": out.get("smoke")})
    _write_text(P["public"], json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    return {"public": P["public"], "sha256_16": _sha_file(P["public"])[:16]}


# ══════════════════════════════════════════════════════════════════════════
#  결과 문서 렌더러(얼린 · 게시 칸 파일 하나만 읽는다)
# ══════════════════════════════════════════════════════════════════════════
ROW_KO = {"A": "A · 금리 틸트 · 시총가중(상한 25%) · 주", "S": "S · 정적 50/50 · 시총가중 · 대조", "E": "E · 금리 틸트 · 동일가중 · 쌍둥이",
          "P": "P · 금리 틸트 · 시총가중 · 빌더 가격 그대로 채점 · 민감도", "RETF": "RETF · IVE/IVW 같은 규칙 · T+1 · 참고 줄(보유 아님)"}
PRED_KO = {"P1_no_rejection": "P1 Holm 기각 0/3", "P2_fund_excess_small": "P2 A 세 줄 모두 펀드 |연 초과| < 0.5%p",
           "P3_tilt_positive_2of3": "P3 기전(A − S) 연 평균 > 0 이 N 셋 중 둘 이상", "P4_spread_corr_lt_0_9": "P4 가치 − 성장 다리 스프레드와 IVE − IVW 의 상관 < 0.9(N 셋 모두)",
           "P5_ew_below_cap_2of3": "P5 동일가중 쌍둥이 연 초과 < 시총가중 주 줄(N 셋 중 둘 이상)", "P6_no_adoption": "P6 채택 표시 0",
           "P7_price_wrap_small": "P7 채점 가격 감싸기 효과 |A − P| 연 평균 < 0.05%p(N 셋 모두)"}
T17_FROZEN = "T17 `etf:IVE_IVW_DFII10`(PREREG-2026-09-26-TBATCH-RESULT §4 · 결정 달 말 종가 체결 · 월 수익): 10bp 펀드 연 초과 +0.09%p(t 2.07) · 비용 전 +0.11(t 2.50) · IR 0.54 · TE 0.17% · 하락월 +0.017%p · 6승 3패 · 회전 0.94"


def _fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%%.%df" % nd) % v
    return str(v)


def _row_ko(k):
    return ROW_KO["RETF"] if k == "RETF" else "%s · N %s" % (ROW_KO[k[0]], k[1:])


ROW_HEAD = ["| 줄 | 연 초과(%p) | CAGR 차(%p) | TE(%p) | IR | NW t | 월 승률(%) | 해마다 승 | 하락월(PR) 평균 · 승률 | 하락월(얼린 35) 평균 | 급락 다리 승 | 반등 승 | 36개월 굴림 승률 | 4요인 α(%p/년) (t) | 슬리브 β | 편도 회전/년 | 20bp 연 초과 |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]


def _row_line(k, v):
    m, st = v.get("m") or {}, (v.get("m") or {}).get("style") or {}
    mech = m.get("mech") or {}
    cl, rb = mech.get("crash_legs") or {}, mech.get("rebounds") or {}
    r36 = m.get("roll36") or {}
    return "| %s | %s | %s | %s | %s | %s | %s | %s/%s | %s · %s%% | %s | %s/%s | %s/%s | %s%% | %s (%s) | %s | %s | %s |" % (
        _row_ko(k), _fmt(m.get("ann_ex")), _fmt(m.get("cagr_ex")), _fmt(m.get("te")), _fmt(m.get("ir")), _fmt(m.get("nw_t")), _fmt(m.get("win"), 1),
        m.get("years_won_full"), m.get("n_full_years"), _fmt(m.get("down_mean"), 3), _fmt(m.get("down_win"), 0),
        _fmt((v.get("down_frozen") or {}).get("mean"), 3), cl.get("win"), cl.get("n"), rb.get("win"), rb.get("n"), _fmt(r36.get("hit"), 0),
        _fmt(st.get("alpha_ann")), _fmt(st.get("alpha_t")), _fmt(m.get("sleeve_beta")), _fmt(m.get("turn")), _fmt((v.get("m20") or {}).get("ann_ex")))


def reg_err_lines(path):
    """굽기 뒤에 찾은 등록 오류(글과 얼린 코드의 어긋남)를 손으로 적은 UTF-8 글 파일 → (줄 목록, sha256 앞 16).
    줄마다 소수 · 지수꼴은 <num> 으로 지운다(값이 머리로 새지 않게 · 정수 · 날짜 · 절 번호는 남는다) · 빈 줄 · # 줄은 건너뛴다."""
    b = _bytes(path)
    out = [_scrub(l.strip())[:300] for l in b.decode("utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
    return out, hashlib.sha256(b).hexdigest()[:16]


def result_doc(pub, reg_err=None):
    """결과 문서 본문(Markdown) — 게시 칸 파일(_dstkout.public.json) 하나만 읽는다(손으로 옮기지 않는다).
    reg_err = (줄 목록, 파일 sha256 앞 16) — `--reg-err <파일>` 로 넘긴 굽기 뒤 등록 오류(있을 때만 · 값이 아니라 글과 코드의 어긋남)."""
    if not pub or not pub.get("dstk_public_view"):
        raise SystemExit("🚨 게시 칸 파일이 아니다")
    stopped = pub.get("stopped")
    H = pub.get("holm") or {}
    rej = H.get("reject") or {}
    adopt = pub.get("adopt") or {}
    tread = pub.get("tilt_read") or {}
    n_rej, n_ad = sum(1 for v in rej.values() if v), sum(1 for v in adopt.values() if v)
    n_basket = sum(1 for k, v in adopt.items() if v and (tread.get(k) or {}).get("static_basket"))
    verdict = pub.get("verdict") or ("보류" if stopped else "—")
    title = ("# 결과 — D13 주식판(DSTK · 실질금리 스타일 로테이션 · 랩 스타일 명단 spval · grow · N 10 · 20 · 30): 한 번 굽기 · %s · **%s**"
             % ("멈춤(등록된 멈춤 조건)" if stopped else "Holm 기각 %d/3 · 채택 표시 %d%s" % (n_rej, n_ad, (" (그중 정적 바스켓 몫 %d)" % n_basket) if n_ad else ""), verdict))
    re_lines, re_sha = (reg_err or ([], None))
    reg_all = list(pub.get("registration_error") or []) + list(re_lines)
    L = [title, "",
         "풀카드: D13   <!-- 탐색 풀 D13(듀레이션 스타일 로테이션) 주식판 — build/pool_lab.py 가 이 줄을 읽는다 -->",
         "판정: %s   <!-- 확증 가족 A10 · A20 · A30(한쪽 Holm α 0.05) · 채택 표시 = 기각 ∧ 무해 · 표시가 있으면 «보류»(펀드에 붙이기는 사용자 결정) · 기각은 있고 표시가 없으면 «측정만» · 기각 0 이면 «기각» -->" % verdict,
         "규칙: 없음   <!-- 랩 게시 sid 가 아니다 · 운용 · 사이트 규칙 변경 없음 -->", "",
         "아래는 얼린 렌더러(`python -X utf8 build/dstk_run.py --result-doc`)가 게시 칸 파일(`_dstkout.public.json`) 하나에서 만든 것이다.", "",
         "## 머리", "",
         "- 등록 커밋 `%s` · 산출 sha256 `%s` · 자료 핀 `%s`" % (pub.get("prereg_commit"), (pub.get("out_sha256") or "—")[:16], (pub.get("data_pin") or "")[:9]),
         "- 멈춤: %s · 등록 오류: %s%s" % (stopped or "없음", "; ".join(reg_all) or "없음",
                                       (" (굽기 뒤 손으로 적은 등록 오류 파일 sha256 `%s` · 값이 아니라 글과 얼린 코드의 어긋남)" % re_sha) if re_sha else ""),
         "- 창(보유월): %s · %s개월 · 펀드 F = 0.9 × SPY TR + 0.1 × 슬리브 대 SPY TR · 편도 10bp · 월말 결정 · T+1 체결" % ("~".join(pub.get("window") or ["—"]), pub.get("n_hold") or "—"),
         "- 다중성: 확증 가족 m = %s(α %s) · 누적 N %s → %s(센 줄 %s)" % ((pub.get("multiplicity") or {}).get("m_confirmatory"), (pub.get("multiplicity") or {}).get("alpha"),
                                                                (pub.get("multiplicity") or {}).get("cum_n_before"), (pub.get("multiplicity") or {}).get("cum_n_after"),
                                                                (pub.get("multiplicity") or {}).get("rows_counted")),
         "- 전방: %s" % pub.get("forward"), ""]
    f0 = pub.get("f0") or {}
    fo, rg, ps = f0.get("forms") or {}, f0.get("regime") or {}, f0.get("ps") or {}
    L += ["## F0 관문(수익 없음 · 등록 개수 대조)", "",
          "| 관문 | 값 |", "|---|---|",
          "| F0 전체 | %s · 어긋남 %s |" % (_fmt(f0.get("ok")), "; ".join(f0.get("bad") or []) or "없음"),
          "| 빌더 대응(화면 spval ↔ 빌더 val · grow ↔ grow · MIN_NAMES %s · 공시 지연 %s일 · 연간 주식수 %s일) | %s · %s |" % (
              (f0.get("builder") or {}).get("min_names"), (f0.get("builder") or {}).get("lag_days"), (f0.get("builder") or {}).get("ann_lag_days"),
              _fmt((f0.get("builder") or {}).get("val_fn_is_sc_val")), _fmt((f0.get("builder") or {}).get("grow_fn_is_sc_grow"))),
          "| 결정 월(첫 결정 %s) · 다리 채움 | %s/%s |" % (fo.get("first_valid"), fo.get("n_valid"), fo.get("n")),
          "| 명단(가격 선 · 날짜 인식 키) 최소 · 중앙 · 최대 | %s · %s · %s |" % ((fo.get("n_pool") or {}).get("min"), (fo.get("n_pool") or {}).get("med"), (fo.get("n_pool") or {}).get("max")),
          "| 빌더 그대로(티커 그대로) 명단 최소 · 중앙 | %s · %s(빠지는 이름 %s) |" % ((fo.get("n_asis") or {}).get("min"), (fo.get("n_asis") or {}).get("med"), f0.get("asis_missing_n_names")),
          "| 가치 채점 수(최소 · 중앙 · 최대) · 명단 대비 | %s · %s · %s · %s ~ %s |" % ((fo.get("v_scored") or {}).get("min"), (fo.get("v_scored") or {}).get("med"), (fo.get("v_scored") or {}).get("max"),
                                                                 _fmt((fo.get("v_cov") or {}).get("min"), 3), _fmt((fo.get("v_cov") or {}).get("max"), 3)),
          "| 성장 채점 수(최소 · 중앙) · 명단 대비 최소 | %s · %s · %s |" % ((fo.get("g_scored") or {}).get("min"), (fo.get("g_scored") or {}).get("med"), _fmt((fo.get("g_cov") or {}).get("min"), 3)),
          "| 커버리지 부분 창 첫 보유월(가치 채점 ≥ 80%% 가 끝까지) | %s |" % fo.get("cov_late_from"),
          "| 채점 가격 V-D1 쓴 이름 · 대체(랩 가격 · 배당으로 설명 못 하는 계단) | %s · %s %s |" % (ps.get("vd1_used"), ps.get("n_fallback"), ", ".join(ps.get("fallback") or [])),
          "| 빌더가 모르는 V-D1 분할 행(splits.json 밖 · 되돌림) 행 · 이름 · 명단 결정 칸 · splits.json 인데 V-D1 에 없는 행 | %s · %s · %s · %s |" % (
              ps.get("n_split_rev_rows"), ps.get("n_split_rev_names"), fo.get("split_rev_cells"), ps.get("n_splits_json_not_vd1")),
          "| 명단 가운데 채점 가격 수준이 배당조정(편출 · 별칭 키 · 추정) 첫 결정 · 최소 · 최대 · 배당 없는 가격 계열 첫 결정 | %s · %s · %s · %s |" % (
              fo.get("lvl_adj_first"), (fo.get("lvl_adj") or {}).get("min"), (fo.get("lvl_adj") or {}).get("max"), fo.get("lvl_pr_first")),
          "| 물려받은 선견 자격 규칙: 재배정 티커 마지막 달 제외(명단 티커-달) · 편출 이름 단절 앞 자르기(이름) | %s · %s |" % (
              (f0.get("inherited") or {}).get("reassigned_cells"), (f0.get("inherited") or {}).get("seam_cut_names")),
          "| 홈 화면 칩(style_top.json · 벤더 스냅샷) 대 빌더 명단(style_perf today · %s) 가치 · 성장 | %s/10 · %s/10 |" % (
              ((f0.get("home") or {}).get("spval") or {}).get("builder_today_d"), ((f0.get("home") or {}).get("spval") or {}).get("overlap"), ((f0.get("home") or {}).get("grow") or {}).get("overlap")),
          "| DFII10 국면(보유 120 결정) 가치 · 중립 · 성장 · 전환 · 문턱 경계(|d| = 0.20 ± 1e-9) | %s · %s · %s · %s · %s |" % (rg.get("value"), rg.get("neutral"), rg.get("growth"), rg.get("switches"), rg.get("edge_1e9")),
          "| 국면 = T17 t_signals.dfii10_regime | %s |" % _fmt(rg.get("same_as_t17")),
          "| 하락월 S&P 500 PR < 0 · 얼린 35(SPY TR < 0 확인) | %s · %s(%s) |" % ((f0.get("down") or {}).get("n"), (f0.get("down") or {}).get("n_frozen"), _fmt((f0.get("down") or {}).get("frozen_eq_spytr"))),
          "| 명단 대조 2026-08-31(빌더 가격판 N=10 · 게시 style_perf prev) 가치 · 성장 | %s/10 · %s/10 |" % (((f0.get("anchor") or {}).get("val") or {}).get("overlap_adj"), ((f0.get("anchor") or {}).get("grow") or {}).get("overlap_adj")),
          ""]
    if stopped:
        L += ["## 멈춤", "", "- 굽기가 멈췄다(%s) — 산출은 멈춤 기록이다. 다시 굽기는 새 등록." % stopped, ""]
        return "\n".join(L) + "\n"
    f0a = pub.get("f0a") or {}
    L += ["- 가격 위생 관문(패널 시총가중 S&P 500 대 S&P 500 PR · 결정 %s달): 통과 %s · 상관 %s · 월 평균 차 %s%%p" % (f0a.get("n"), _fmt(f0a.get("ok")), _fmt(f0a.get("corr"), 4), _fmt(f0a.get("gap_pm"), 3)), ""]
    rows = pub.get("rows") or {}
    thr = H.get("threshold") or {}
    L += ["## 1. 확증 가족 · Holm · 무해 · 채택 표시(한쪽 · H1 펀드 월 초과 평균 > 0)", "",
          "| 줄 | 연 초과(%p) | NW(3) t | 한쪽 p | Holm 문턱 | 기각 | 20bp 연 X ≥ 0 | 하락월(얼린 35) X(20bp) ≥ 0 | 회전 ≤ 10 | 무해 | **채택 표시** | 같은 N 정적 S NW t | 기전 A − S 펀드 연 평균(%p) | 표시의 읽기(등록 §5-2) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("A10", "A20", "A30"):
        v = rows.get(k) or {}
        hm = v.get("harmless") or {}
        c = hm.get("conds") or {}
        tr = tread.get(k) or {}
        rd = ("—(표시 없음)" if not adopt.get(k) else
              ("**정적 바스켓 몫 — 금리 틸트 증거 아님**" if tr.get("static_basket") else "금리 틸트 몫이 받친다(A − S > 0 ∧ A 의 t > S 의 t)"))
        L.append("| %s | %s | %s | %s | %s | %s | %s(%s) | %s(%s) | %s(%s) | %s | **%s** | %s | %s | %s |" % (
            _row_ko(k), _fmt((v.get("m") or {}).get("ann_ex")), _fmt((v.get("m") or {}).get("nw_t")), _fmt((H.get("p") or {}).get(k), 4),
            _fmt(thr.get(k), 4), _fmt(rej.get(k)), _fmt(c.get("ann_x20_ge0")), _fmt(hm.get("ann_x20")), _fmt(c.get("down_x20_ge0")),
            _fmt(hm.get("down_mean_x20"), 3), _fmt(c.get("turn_le10")), _fmt(hm.get("turn")), _fmt(hm.get("harmless")), _fmt(adopt.get(k)),
            _fmt(tr.get("s_nw_t")), _fmt(tr.get("mech_mean_ann"), 3), rd))
    for k in ("E10", "E20", "E30"):
        v = rows.get(k) or {}
        L.append("| %s — **확증 가족 밖**(사용자 화면 가중) | %s | %s | — | — | — | %s | — | %s | %s | — | — | — | — |" % (
            _row_ko(k), _fmt((v.get("m") or {}).get("ann_ex")), _fmt((v.get("m") or {}).get("nw_t")),
            _fmt(((v.get("harmless") or {}).get("conds") or {}).get("ann_x20_ge0")), _fmt(((v.get("harmless") or {}).get("conds") or {}).get("turn_le10")),
            _fmt((v.get("harmless") or {}).get("harmless"))))
    L += ["", "- 채택 표시는 «펀드 슬리브 후보» 라는 뜻뿐이다 — 펀드에 붙이는 것은 사용자 결정이고 날짜가 박힌 일정은 없다(등록 §5).",
          "- 사용자 화면(style.html · style_perf)의 명단 곡선은 동일가중이다 — 동일가중 E 줄은 확증 가족 밖이고 판정은 시총가중 주 줄(A)에만 걸린다.",
          "- 표시의 읽기(계산 전 고정 · 표시를 바꾸지 않는다): 같은 N 의 기전(A − S) 펀드 연 평균 ≤ 0 이거나 S 의 NW t ≥ A 의 NW t 이면 «정적 바스켓 몫 — 금리 틸트 증거 아님».", ""]
    L += ["## 2. 펀드 틀 — 모든 줄(10년 · 편도 10bp · T+1)", ""] + ROW_HEAD
    order = [p + str(n) for p in ("A", "S", "E", "P") for n in (10, 20, 30)] + ["RETF"]
    for k in order:
        if k in rows:
            L.append(_row_line(k, rows[k]))
    L += ["", "- 하락월(PR) = S&P 500 가격수익 < 0(qbatch_core.evaluate · %s달) · 하락월(얼린 35) = data/mech_episodes.json down_m(SPY TR < 0 · 무해 판정의 목록)" % ((pub.get("down") or {}).get("n_pr")), ""]
    L += ["## 3. 기전 — 금리 틸트 몫(A − 같은 N 정적 50/50)", "",
          "| N | 펀드 월 초과 차 연 평균(%p) | NW t | 월 승률(%) | 하락월 평균(%p) | 해마다 승 | ΔIR | 차의 4요인 α (t) | 슬리브 차 연 평균(%p) | 슬리브 차 NW t |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for n, v in (pub.get("mech") or {}).items():
        fd, sl = v.get("fund") or {}, v.get("sleeve") or {}
        st = fd.get("style") or {}
        L.append("| %s | %s | %s | %s | %s | %s/%s | %s | %s (%s) | %s | %s |" % (n, _fmt(fd.get("mean_ann"), 3), _fmt(fd.get("nw_t")), _fmt(fd.get("win"), 1), _fmt(fd.get("down_mean"), 3),
                                                                    fd.get("years_won_full"), fd.get("n_full_years"), _fmt(fd.get("d_ir")), _fmt(st.get("alpha_ann")),
                                                                    _fmt(st.get("alpha_t")), _fmt(sl.get("mean_ann")), _fmt(sl.get("nw_t"))))
    L += ["", "- 비교(얼린 기록): x-bmrot 대 틸트 없는 짝 +0.99%p · t 2.80(슬리브 단독 · PREREG-2026-09-03-BMROT-RESULT §1) — 여기 «슬리브 차» 칸과 같은 뜻의 자리다.", ""]
    L += ["## 4. 차이 — 가중 · 채점 가격 · ETF 판(10년 · 펀드 월 초과 차)", "",
          "| 차 | N | 연 평균(%p) | NW t | 월 승률(%) | 하락월 평균(%p) | 해마다 승 | ΔIR |", "|---|---|---|---|---|---|---|---|"]
    dko = {"A-E": "A − E(시총가중 − 동일가중)", "A-P": "A − P(채점 가격 감싸기 효과)", "A-RETF": "A − RETF(주식판 − ETF 판)"}
    for nm, d in (pub.get("diffs") or {}).items():
        for n, v in d.items():
            L.append("| %s | %s | %s | %s | %s | %s | %s/%s | %s |" % (dko.get(nm, nm), n, _fmt(v.get("mean_ann"), 3), _fmt(v.get("nw_t")), _fmt(v.get("win"), 1),
                                                              _fmt(v.get("down_mean"), 3), v.get("years_won_full"), v.get("n_full_years"), _fmt(v.get("d_ir"))))
    L += ["", "## 5. 충실도 — 주식 다리가 IVE/IVW 를 얼마나 닮았나(월 수익 상관 · 10년)", "",
          "| N | 가치 − 성장 스프레드 대 IVE − IVW | 가치 다리 대 IVE | 성장 다리 대 IVW | 펀드 월 초과 대 RETF | 가치 다리 회전 | 성장 다리 회전 |", "|---|---|---|---|---|---|---|"]
    for n, v in (pub.get("fidelity") or {}).items():
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (n, _fmt(v.get("spread_corr"), 3), _fmt(v.get("v_corr"), 3), _fmt(v.get("g_corr"), 3), _fmt(v.get("fund_ex_corr_retf"), 3),
                                                   _fmt(v.get("v_turn")), _fmt(v.get("g_turn"))))
    L += ["", "- 비교(얼린 기록): 랩 복제 STYLESCORE 의 스프레드 상관 0.685(PREREG-2026-09-03-STYLESCORE-RESULT §3).", ""]
    ep_cols = [k for k in ("A10", "A20", "A30", "S10", "RETF") if k in rows]
    ep_names = [(e.get("kind"), e.get("name")) for e in ((rows.get("A10") or {}).get("m") or {}).get("episodes") or []]
    if ep_names:
        L += ["## 6. 이름 붙은 급락 · 급등 구간(qbatch_core.EPIS · 펀드 초과 %p)", "", "| 구간 | " + " | ".join(ep_cols) + " |", "|---|" + "---|" * len(ep_cols)]
        for kind, nm in ep_names:
            vals = []
            for k in ep_cols:
                hit = [e.get("ex") for e in ((rows[k].get("m") or {}).get("episodes") or []) if e.get("name") == nm and e.get("kind") == kind]
                vals.append(_fmt(hit[0]) if hit else "—")
            L.append("| %s · %s | %s |" % (kind, nm, " | ".join(vals)))
        L += [""]
    yrs = sorted({y for k in ep_cols for y in (((rows[k].get("m") or {}).get("years")) or {})})
    if yrs:
        L += ["## 7. 해마다(펀드 초과 %p · 창 첫 해 · 끝 해는 부분)", "", "| 해 | " + " | ".join(ep_cols) + " |", "|---|" + "---|" * len(ep_cols)]
        for y in yrs:
            L.append("| %s | %s |" % (y, " | ".join(_fmt(((rows[k].get("m") or {}).get("years") or {}).get(y)) for k in ep_cols)))
        L += [""]
    late = pub.get("late")
    if late:
        L += ["## 8. 커버리지 부분 창(보유 %s ~ 2026-08 · 가치 채점이 명단의 80%% 이상인 달만 · 보고만)" % late.get("from"), "",
              "| 줄 | 연 초과(%p) | IR | NW t | 월 승률(%) | 하락월 평균(%p) |", "|---|---|---|---|---|---|"]
        for k, v in (late.get("rows") or {}).items():
            L.append("| %s | %s | %s | %s | %s | %s |" % (_row_ko(k), _fmt(v.get("ann_ex")), _fmt(v.get("ir")), _fmt(v.get("nw_t")), _fmt(v.get("win"), 1), _fmt(v.get("down_mean"), 3)))
        for n, v in (late.get("mech") or {}).items():
            L.append("| 기전 A − S · N %s | %s | %s | %s | %s | %s |" % (n, _fmt(v.get("mean_ann"), 3), _fmt(v.get("d_ir")), _fmt(v.get("nw_t")), _fmt(v.get("win"), 1), _fmt(v.get("down_mean"), 3)))
        L += [""]
    comp = pub.get("composition") or {}
    if comp:
        L += ["## 9. 구성(개수 · 수익 아님)", "", "| 줄 | 결정 | 평균 종목 수 | NASDAQ 100 전용 몫(‰) | 편출(오늘 유니버스 밖) 몫(‰) | 채점 수준 배당조정 몫(‰) | 채점 수준 배당 없는 가격 계열 몫(‰) | 분할 행 되돌림 몫(‰) | 두 다리 겹침(합) | 체결 날 가격 없어 뺀 수(합) | 최대 종목 비중(‰) |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for k in [x for x in order if x in comp]:
            c = comp[k]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (_row_ko(k), c.get("forms"), _fmt((c.get("mean_names_x10") or 0) / 10.0, 1), c.get("ndx_only_share_x1000"),
                                                                         c.get("not_today_share_x1000"), c.get("lvl_adj_share_x1000"), c.get("lvl_pr_share_x1000"), c.get("split_rev_share_x1000"),
                                                                         c.get("both_legs_total"), c.get("exec_drop_total"), c.get("max_w_x1000")))
        L += ["", "- 채점 수준 배당조정 몫 = 결정일 채점 가격 수준이 뒤 배당만큼 낮은 이름(편출 · 별칭 키의 yfinance auto_adjust=True · 스테이징 tr 계열 · P 줄의 오늘 이름) — 그만큼 B/P · E/P · S/P 가 부풀고 시총이 작다(등록 §2-3 · 편출될 배당주 쪽 선견)."]
        L += [""]
    ref, xb = pub.get("eg30_ref") or {}, pub.get("xbmrot_ref") or {}
    fe_ = ref.get("frozen_eval") or {}
    xf = xb.get("frozen") or {}
    L += ["## 10. 참고 줄(입력 · 대조 · 구성 요소가 아니다)", "",
          "- %s" % T17_FROZEN,
          "- RETF(이 굽기 · 같은 규칙 · T+1 · 같은 펀드 틀): 연 초과 %s%%p · NW t %s · IR %s(§2 표 마지막 줄)" % (_fmt(((rows.get("RETF") or {}).get("m") or {}).get("ann_ex")),
                                                                                   _fmt(((rows.get("RETF") or {}).get("m") or {}).get("nw_t")), _fmt(((rows.get("RETF") or {}).get("m") or {}).get("ir"))),
          "- EG30 V0(얼린 data/_qbatch.json · 운용 기준 줄): 연 초과 %s%%p · IR %s · NW t %s · 해마다 %s/%s · 하락월 평균 %s · 슬리브 β %s · 펀드 월 초과 상관 %s" % (
              _fmt(fe_.get("ann_ex")), _fmt(fe_.get("ir")), _fmt(fe_.get("nw_t")), fe_.get("years_won"), fe_.get("n_years"), _fmt(fe_.get("down_mean"), 3), _fmt(fe_.get("sleeve_beta")),
              " · ".join("%s %s" % (k, _fmt(v)) for k, v in (ref.get("corr_fund_ex") or {}).items()) or "—"),
          "- x-bmrot(얼린 data/_fund_mix.json · %s · 잣대 %s): 연 초과 %s%%p · t %s · IR %s" % ("~".join(xb.get("window") or []), xb.get("basis"), _fmt(xf.get("ann_ex")), _fmt(xf.get("t")), _fmt(xf.get("ir"))), ""]
    L += ["## 11. 미리 적은 예측(등록 §5-3)", "", "| 예측 | 맞음 |", "|---|---|"]
    for k, ko in PRED_KO.items():
        L.append("| %s | %s |" % (ko, _fmt((pub.get("predictions") or {}).get(k))))
    L += ["", "## 공개 규칙", "",
          "- 이 문서는 게시 칸 파일 하나에서 얼린 렌더러가 만들었다 · 창이 10년이라 값은 모두 공개 창 안이다 · 산출 원본(_dstkout.json)은 저장소 밖 캐시에만 둔다.",
          "- 채택 표시가 있어도 펀드에 붙이는 것은 사용자 결정이다(날짜 없음 · 전방 원장 없음). 표시가 없으면 운용은 그대로다(EG30 V0).",
          "- 표본 안 수치는 오염된 측정이다(등록 §0) — 사용자는 설계 검토(d13q)를 본 뒤 N 을 골랐다."]
    txt = "\n".join(L) + "\n"
    if CACHE_ONLY_KEY in txt:
        raise SystemExit("🚨 결과 문서에 캐시 표지가 있다")
    return txt


def result_doc_write_problems(pub, P=None):
    """--result-doc --write 문지기 — 연기 판이 아니고 · 두 로컬 표식에 FINISHED <산출 sha> 가 있고 · 캐시 산출 sha 가 게시 칸의 out_sha256 과 같아야 쓴다."""
    P = P or paths()
    bad = []
    if not pub or not pub.get("dstk_public_view"):
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
    """등록 전 F0 — 작업 트리 자료(= 핀 판이어야)로 엔진 f0 자식을 돌려 개수만 돌려준다(수익 없음). 결과를 엔진 F0_EXPECT · 등록 문서 §7 에 옮긴다."""
    import dstk as E
    pb = []
    for f in DATA_PIN_FILES:
        fp = os.path.join(ROOT, *f.split("/"))
        r = _git("rev-parse", "%s:%s" % (DATA_PIN, f))
        if not os.path.exists(fp) or r.returncode != 0 or git_blob_sha(_bytes(fp)) != r.stdout.strip():
            pb.append(f)
    if pb:
        raise SystemExit("🚨 작업 트리 자료가 핀 판과 다르다(%s) — 등록 전 F0 는 핀 판 자료로만 센다" % ", ".join(pb[:4]))
    c = cache_guard_std()
    os.makedirs(c, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="dstk_f0_", dir=c)
    try:
        p = os.path.join(tmp, "f0.json")
        sec = run_child(ROOT, "f0", p)
        f0 = _read_json(p)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"sec": sec, "ok": f0.get("ok"), "bad": f0.get("bad"), "signature": E._f0_signature(f0), "vd1_digest": (f0.get("vd1") or {}).get("digest"),
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
    vb = vd1_problems()
    missing = [p for p in FROZEN if not os.path.exists(os.path.join(ROOT, *p.split("/")))]
    ready = bool(not name_check() and not n_ph and not n_dm and g["ok"] and gw and vw and not mb and not pb and not cb and not vb and not missing
                 and not check_no_forward())
    return {"ready": ready, "prereg": PREREG, "prereg_n": _N_PREREG, "name_ok": not name_check(), "placeholders": n_ph, "draft_marks": n_dm,
            "site_guard": g["ok"], "site_guard_bad": g["bad"][:5], "wired_gitignore": gw, "wired_validate_site": vw,
            "manifest_problems": mb, "pins_problems": pb, "registered_constants_bad": cb, "vd1_problems": vb, "frozen_missing": missing,
            "no_forward": not check_no_forward(), "head": _git("rev-parse", "HEAD").stdout.strip()}


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기(러너 경로 전체 · 산출은 열지 않고 지운다 · 참/거짓 · 초만)
# ══════════════════════════════════════════════════════════════════════════
def smoke():
    import contextlib
    cache = cache_guard_std()
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="dstk_runner_smoke_", dir=cache)
    if _inside(tmp, ROOT):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    saved = dict(_OVR)
    res = {"ok": False, "steps": {}, "started": _now()}
    t0 = time.time()
    sink = io.StringIO()
    real_out = os.path.join(cache, "out")
    before = sorted(f for f in os.listdir(real_out) if f.startswith("_dstkout")) if os.path.isdir(real_out) else []
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
    after = sorted(f for f in os.listdir(real_out) if f.startswith("_dstkout")) if os.path.isdir(real_out) else []
    res["real_out_untouched"] = before == after == []
    res["real_gitmark_absent"] = not os.path.exists(_git_mark_path())
    res["sec"] = round(time.time() - t0, 1)
    res["ok"] = bool(res["ok"] and res["deleted_unread"] and res["real_out_untouched"] and res["real_gitmark_absent"])
    _write_text(os.path.join(cache, "meta", "_smoke_dstk_run.json"), json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    return res


SMOKE_ALLOWED_KEYS = {"ok", "steps", "started", "files", "tag", "err", "stdout_discarded_unread", "deleted_unread", "real_out_untouched", "real_gitmark_absent", "sec",
                      "bake", "registration_error_empty", "start_tag", "stage", "exists", "nonempty", "second_run_blocked", "finished_marks", "tag_file",
                      "restart_blocked", "not_stopped", "public_safe", "result_doc_rendered", "result_doc_has_cache_marker", "out", "mark", "runlog",
                      "public", "gitmark"}


# ══════════════════════════════════════════════════════════════════════════
#  합성 점검(실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _st_regime():
    """D13 국면 — 월말 마지막 관측 · 3개월 전 월말 · 문턱 양끝 · 결측 · T17 t_signals.dfii10_regime 과 같은 뜻(합성 일간 계열)."""
    import numpy as np
    import pandas as pd
    import dstk as E
    import t_signals as TS
    rs = np.random.RandomState(4)
    days = pd.bdate_range("2019-01-01", "2021-12-31")
    vals = np.round(np.cumsum(rs.normal(0, 0.05, len(days))), 2)
    ser = {d.strftime("%Y-%m-%d"): float(v) for d, v in zip(days, vals)}
    ser[days[5].strftime("%Y-%m-%d")] = None                   # 결측은 건너뛴다
    forms = ["%04d-%02d" % (y, m) for y in (2019, 2020, 2021) for m in range(1, 13)]
    rg = E.regimes(ser, forms)
    ok = all(rg[f] is None for f in forms[:3]) and all(rg[f] is not None for f in forms[3:])
    s = pd.Series({pd.Timestamp(k): v for k, v in ser.items() if v is not None}, dtype=float).sort_index()
    df = TS.dfii10_regime(s)
    cm = {TS.VALUE_TILT: "value", TS.NEUTRAL: "neutral", TS.GROWTH_TILT: "growth"}
    ok &= all(cm[int(df["regime"].loc[pd.Period(f, "M")])] == rg[f]["code"] for f in forms[3:])
    ok &= E.regime_at({"2020-01": 1.0, "2020-04": 1.25}, "2020-04")["code"] == "value"
    ok &= E.regime_at({"2020-01": 1.0, "2020-04": 0.75}, "2020-04")["code"] == "growth"
    ok &= E.regime_at({"2020-01": 1.0, "2020-04": 1.19}, "2020-04")["code"] == "neutral"
    ok &= E.regime_at({"2020-01": 1.0, "2020-04": 1.25}, "2020-04")["w_v"] == 0.70 and E.regime_at({"2020-01": 1.0}, "2020-04") is None
    # 문턱 경계 — 부동소수 그대로 비교(T17 _regime 과 같다): 1.20 − 1.00 = 0.19999999999999996 → 중립 · 0.52 − 0.32 = 0.2 → 가치
    ok &= E.regime_at({"2020-01": 1.0, "2020-04": 1.2}, "2020-04")["code"] == "neutral"
    ok &= E.regime_at({"2020-01": 0.32, "2020-04": 0.52}, "2020-04")["code"] == ("value" if 0.52 - 0.32 >= 0.20 else "neutral")
    ok &= E.W_V == {"value": 0.70, "neutral": 0.50, "growth": 0.30}
    return bool(ok)


def _st_cap_weights():
    """시총가중 상한 — 합 1 · 상한 넘는 이름 없음 · 안 걸린 이름은 시총 비례 · 상한 안 걸리면 그대로 · 못 채우면 멈춤."""
    import dstk as E
    mc = {"A": 1000.0, "B": 300.0, "C": 100.0, "D": 50.0, "E": 50.0}
    w = E.cap_weights(mc, 0.25)
    free = [t for t in mc if w[t] < 0.25 - 1e-12]
    ok = abs(sum(w.values()) - 1) < 1e-12 and max(w.values()) <= 0.25 + 1e-12
    ok &= all(abs(w[a] / w[b] - mc[a] / mc[b]) < 1e-9 for a in free for b in free)
    w2 = E.cap_weights({"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0}, 0.25)
    ok &= all(abs(x - 0.2) < 1e-12 for x in w2.values())
    try:
        E.cap_weights({"A": 1.0, "B": 2.0, "C": 3.0}, 0.25)
        ok = False
    except E.StopBake:
        pass
    lg = {"names": ["A", "B", "C", "D", "E"], "mcap": mc}
    ok &= E.leg_weights(lg, 5, "ew") == {t: 0.2 for t in mc} and E.leg_weights(lg, 6, "cap") is None
    return bool(ok)


class _SynP:
    """빌더 백테스트를 돌릴 수 있는 합성 패널(가격 · 명단 · 월말)."""

    def __init__(self, n_names=130, n_days=300, seed=2):
        import numpy as np
        rs = np.random.RandomState(seed)
        self.dates, d = [], 0
        y, m = 2021, 1
        while len(self.dates) < n_days:
            for dd in range(1, 22):
                self.dates.append("%04d-%02d-%02d" % (y, m, dd))
                if len(self.dates) >= n_days:
                    break
            m += 1
            if m > 12:
                y, m = y + 1, 1
        self.me = [i for i in range(len(self.dates) - 1) if self.dates[i][:7] != self.dates[i + 1][:7]]
        names = ["T%03d" % q for q in range(n_names)] + ["DUALA", "DUALC"]
        self.px = {t: 100 * np.cumprod(1 + rs.normal(0.0003, 0.01, n_days)) for t in names}
        self.uni = {t: {"t": t, "name": ("DUAL CORP-CL A" if t == "DUALA" else "DUAL CORP-CL C" if t == "DUALC" else "CO %s" % t), "idx": []} for t in names}
        self.px["T005"][150] = float("nan")


def _st_ranked_equals_builder():
    """ranked()[:10] = style_top_pdf.backtest 의 pick(오늘 · prev) — 같은 점수 · 동점가르개 · 발행사 하나(클래스 A 우선)."""
    import numpy as np
    import dstk as E
    import style_top_pdf as ST
    P = _SynP()
    rs = np.random.RandomState(9)
    sc = {t: float(np.round(rs.normal(), 1)) for t in P.px}             # 반올림 — 동점을 만든다
    sc["DUALC"], sc["DUALA"] = 9.0, 8.0                                   # C 가 점수는 높아도 A 가 실린다
    tie = {t: float(rs.normal()) for t in P.px}
    fn = lambda P_, i: (dict(sc), dict(tie))
    R = ST.backtest(P, fn)
    ok = R is not None
    end = len(P.dates) - 1
    mine = E.ranked(P, sc, tie, list(P.px), end)[:10]
    ok &= [t for t, _s, _u in R["today"]] == mine and mine[0] == "DUALA"
    pi = R["prev_i"]
    ok &= [t for t, _s, _u in R["prev"]] == E.ranked(P, sc, tie, list(P.px), pi)[:10]
    return bool(ok)


def _st_priced_and_score():
    """priced() 는 부르는 동안만 P.px[t] 를 «랩가 × CF[t][i]» 로 바꾸고 되돌린다 — 결정일 수준 = 채점 가격 · 두 날 비율(모멘텀) = 랩가 비율 ·
    CF 없는 이름은 그대로 · score() 는 채점 모집단을 명단으로 좁힌다(narrowed) · mcaps() 도 같은 수준을 쓴다."""
    import numpy as np
    import dstk as E
    P = _SynP(n_names=30)
    seen = {}
    lab = P.px["T001"].copy()

    def fn(P_, i):
        seen["n_uni"], seen["n_px"] = len(P_.uni), len(P_.px)
        seen["v"] = float(P_.px["T001"][i])
        seen["ratio"] = float(P_.px["T001"][i] / P_.px["T001"][i - 5])
        seen["other"] = float(P_.px["T002"][i])
        return {t: 1.0 for t in P_.uni}, {}
    CF = {"T001": np.linspace(1.5, 1.0, len(P.dates))}
    before = P.px
    E.priced(fn, CF)(P, 10)
    ok = abs(seen["v"] - lab[10] * CF["T001"][10]) < 1e-9 and abs(seen["ratio"] - lab[10] / lab[5]) < 1e-12
    ok &= seen["other"] == float(P.px["T002"][10]) and P.px is before and bool(np.all(P.px["T001"] == lab))
    import style_pit_panel as SPP
    pool = ["T001", "T002", "T003"]
    SPP.narrowed(E.priced(fn, CF), lambda _i: set(pool))(P, 10)
    ok &= seen["n_uni"] == 3 and seen["n_px"] == 3 and len(P.uni) == 32
    return bool(ok)


def _st_scoring_prices():
    """채점 가격 규칙 — 배당 모형(V-D1 자신의 Dividends 열)이 랩가를 설명하면 V-D1(특별배당도) · 설명 못 하는 계단 · 끝 ≠ 1 · 파일 없음은 대체 ·
    splits.json 밖 분할 행은 되돌려(그날 거래 가격) · splits.json 안 분할 행은 그대로 · 랩가가 없는 날은 수준도 없다 · splits.json 인데 V-D1 에 없는 행은 센다."""
    import numpy as np
    import dstk as E
    tmp = tempfile.mkdtemp(prefix="dstk_st_vd1_")
    try:
        dates = ["2020-%02d-%02d" % (m, d) for m in range(1, 13) for d in range(1, 21)]
        n = len(dates)
        traded = 50 + np.arange(n) * 0.1                            # 그날 거래 가격

        def write(t, close, div=None, spl=None):
            div, spl = div or {}, spl or {}
            with io.open(os.path.join(tmp, t + ".csv"), "w", encoding="utf-8", newline="") as f:
                f.write("Date,Close,Dividends,Stock Splits\n" + "".join("%s,%.10g,%s,%s\n" % (d, v, div.get(j, 0), spl.get(j, 0))
                                                                         for j, (d, v) in enumerate(zip(dates, close))))

        def adj(close, div):
            M = np.ones(n)
            for j in sorted(div):
                M[:j] *= 1.0 - div[j] / close[j - 1]
            return np.round(close * M, 2)
        lab, want = {}, {}
        dv = {40: 0.5, 100: 0.5, 160: 0.5}
        write("GOOD", traded, dv)
        lab["GOOD"] = adj(traded, dv)
        lab["GOOD"][7] = np.nan
        want["GOOD"] = traded
        sp = {30: 0.5, 150: 30.0}                                    # 특별배당 1% · 60%
        write("SPECIAL", traded, sp)
        lab["SPECIAL"] = adj(traded, sp)
        want["SPECIAL"] = traded
        c_spin = traded.copy()
        c_spin[:120] /= 1.15                                         # 야후가 분사를 분할 행 1.15 로 적고 과거를 나눴다(빌더는 모른다)
        c_spin[:60] /= 2.0                                           # 2:1 실제 분할(splits.json 에 있다 — 빌더가 주식수를 되맞춘다)
        write("SPIN", c_spin, {}, {120: 1.15, 60: 2.0})
        lab["SPIN"] = np.round(c_spin, 2)
        want["SPIN"] = c_spin * np.where(np.arange(n) < 120, 1.15, 1.0)
        write("STEP", traded)
        lab["STEP"] = np.round(traded * np.where(np.arange(n) < 100, 0.9, 1.0), 2)   # 배당 행 없는 10% 계단
        write("END", traded)
        lab["END"] = np.round(traded * 0.97, 2)
        lab["NOFILE"] = np.round(traded, 2)
        splits = {"SPIN": [[dates[60], 2.0]], "GOOD": [[dates[50], 3.0]]}          # GOOD 의 행은 V-D1 에 없다(센다)
        CF, SR, info = E.scoring_prices(dates, lab, set(lab), 0, n - 1, d=tmp, splits=splits)
        ok = set(CF) == {"GOOD", "SPECIAL", "SPIN"} and sorted(info["fallback"]) == ["END", "NOFILE", "STEP"]
        for t in ("GOOD", "SPECIAL", "SPIN"):
            lvl = lab[t] * CF[t]
            m = ~np.isnan(lvl)
            ok &= bool(np.max(np.abs(lvl[m] - want[t][m]) / want[t][m]) < 2e-3)
        ok &= bool(np.isnan((lab["GOOD"] * CF["GOOD"])[7]))
        ok &= set(SR) == {"SPIN"} and info["split_rev"] == [["SPIN", dates[120], 1.15]] and info["splits_json_not_vd1"] == [["GOOD", dates[50]]]
        ok &= info["n_split_rev_rows"] == 1 and info["n_split_rev_names"] == 1 and info["vd1_used"] == 3
        dg, nn, miss = E.vd1_digest(["GOOD", "STEP", "NOFILE"], tmp)
        dg2, _n2, _m2 = E.vd1_digest(["STEP", "GOOD"], tmp)
        ok &= nn == 2 and miss == ["NOFILE"] and dg == dg2 and len(dg) == 64
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_lock_and_tag():
    """동시 굽기 막기 — 배타 잠금은 두 번째를 멈추고 풀면 다시 잡힌다 · 시작 태그가 이미 있으면 DSTK_RERUN 일 때만 «already»."""
    tmp = tempfile.mkdtemp(prefix="dstk_st_lock_")
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


def _st_tilt_read():
    """채택 표시의 읽기 — 기전 ≤ 0 · S 의 t ≥ A 의 t · 값 없음이면 정적 바스켓 몫(참) · 기전 > 0 ∧ A 의 t > S 의 t 면 거짓."""
    import dstk as E
    ok = E.tilt_read(0.02, 2.5, 1.0)["static_basket"] is False
    ok &= E.tilt_read(0.0, 2.5, 1.0)["static_basket"] is True and E.tilt_read(-0.01, 2.5, 1.0)["static_basket"] is True
    ok &= E.tilt_read(0.02, 2.5, 2.5)["static_basket"] is True and E.tilt_read(0.02, 2.5, 2.7)["static_basket"] is True
    ok &= E.tilt_read(None, 2.5, 1.0)["static_basket"] is True and E.tilt_read(0.02, None, 1.0)["static_basket"] is True
    return bool(ok)


def _st_book_path():
    """경로 규약 — 첫 체결 전 현금 1 · 체결 날 값 = 비용 뒤 값 · 회전 = 창 뒤 체결의 거래액 합 ÷ 2 ÷ 10년 · 값 없는 날은 마지막 값 · 비중 합 1 아니면 멈춤."""
    import numpy as np
    import dstk as E
    n = 60
    PX = {"A": 100 * np.cumprod(np.r_[1.0, np.full(n - 1, 1.01)]), "B": 50.0 + np.arange(n, dtype=float)}
    PX["B"][30:35] = np.nan
    ex = [(5, {"A": 0.5, "B": 0.5}), (20, {"A": 1.0}), (40, {"A": 0.5, "B": 0.5})]
    bp = E.book_path(PX, ex, n - 1, 0.001, i_window=10)
    p = bp["path"]
    ok = abs(p[5] - (1 - 0.001)) < 1e-15 and 5 in p and 4 not in p and (n - 1) in p          # 첫 체결 = 현금 1 × 편도 10bp
    uA, uB = p[5] * 0.5 / PX["A"][5], p[5] * 0.5 / PX["B"][5]
    ok &= abs(p[19] - (uA * PX["A"][19] + uB * PX["B"][19])) < 1e-12                          # 체결 사이 = 단위 × 가격(표류)
    V20_pre = uA * PX["A"][20] + uB * PX["B"][20]
    tr20 = abs(V20_pre - uA * PX["A"][20]) + uB * PX["B"][20]
    ok &= abs(p[20] - (V20_pre - 0.001 * tr20)) < 1e-12                                        # 체결 날 값 = 비용 뒤 값
    V40_pre = p[39] * PX["A"][40] / PX["A"][39]
    tr40 = V40_pre
    ok &= abs(bp["turn"] - (tr20 / V20_pre + tr40 / V40_pre) / 2 / 10.0) < 1e-12              # 창 뒤 체결 둘 · ÷ 2 ÷ 10년
    bp2 = E.book_path(PX, [(5, {"A": 0.5, "B": 0.5})], n - 1, 0.0)
    vA, vB = bp2["path"][5] * 0.5 / PX["A"][5], bp2["path"][5] * 0.5 / PX["B"][5]
    ok &= abs(bp2["path"][32] - (vA * PX["A"][32] + vB * PX["B"][29])) < 1e-9                  # B 가격 없는 날 = 마지막 값(29일)
    ok &= abs(bp2["path"][36] - (vA * PX["A"][36] + vB * PX["B"][36])) < 1e-9                  # 가격이 다시 서면 그 값
    try:
        E.book_path(PX, [(5, {"A": 0.6, "B": 0.5})], n - 1, 0.001)
        ok = False
    except E.StopBake:
        pass
    return bool(ok)


def _st_exec_target():
    """체결 날 목표 — 가격 없는 이름은 다리 안에서 빼고 비례로 다시 나눈다 · w_V 로 섞는다 · 합 1."""
    import numpy as np
    import dstk as E
    PX = {"V1": np.array([1.0, 1.0]), "V2": np.array([1.0, np.nan]), "G1": np.array([1.0, 2.0]), "G2": np.array([1.0, 3.0])}
    tgt, drop = E.exec_target(PX, 1, {"V1": 0.5, "V2": 0.5}, {"G1": 0.25, "G2": 0.75}, 0.7)
    ok = drop == 1 and abs(tgt["V1"] - 0.7) < 1e-12 and abs(tgt["G1"] - 0.075) < 1e-12 and abs(tgt["G2"] - 0.225) < 1e-12
    tgt2, _d = E.exec_target(PX, 1, {"V1": 1.0}, {"G1": 1.0}, 1.0)
    ok &= tgt2 == {"V1": 1.0} and abs(sum(tgt.values()) - 1) < 1e-12
    return bool(ok)


def _syn_grid(n_months=40, seed=5):
    import numpy as np
    import qbatch_core as QC
    rs = np.random.RandomState(seed)
    g = QC.Grid.__new__(QC.Grid)
    g.dates = []
    for k in range(n_months):
        y, m = 2016 + (7 + k) // 12, (7 + k) % 12 + 1
        for dd in range(1, 22):
            g.dates.append("%04d-%02d-%02d" % (y, m, dd))
    g.di = {d: i for i, d in enumerate(g.dates)}
    g.IX_TR = 100 * np.cumprod(1 + rs.normal(0.0004, 0.01, len(g.dates)))
    g.IX_PR = g.IX_TR * 0.99
    g.me = {}
    for i, d in enumerate(g.dates):
        g.me[d[:7]] = i
    g.RF = {}
    return g


def _st_fund_identity():
    """펀드 틀 — 슬리브 = 지수(비용 0 경로)면 월 초과 0 · T+1 체결로 지은 경로도 fund_from_path 가 받는다."""
    import numpy as np
    import dstk as E
    G = _syn_grid()
    ms = sorted(G.me)
    forms = ms[1:-1]
    path = {d: G.IX_TR[d] for d in range(G.me[ms[0]], G.me[ms[-1]] + 1)}
    fr = E.fund(G, path, forms, 0.001)
    ok = bool(np.max(np.abs(fr["ex"])) < 1e-10) and fr["hold"][0] == ms[2]
    PX = {"X": G.IX_TR}
    ex = [(G.me[f] + 1, {"X": 1.0}) for f in [ms[0]] + forms]
    bp = E.book_path(PX, ex, G.me[ms[-1]], 0.0, i_window=G.me[forms[0]])
    fr2 = E.fund(G, bp["path"], forms, 0.0)
    ok &= bool(np.max(np.abs(fr2["ex"])) < 1e-9) and abs(bp["turn"]) < 1e-12
    return bool(ok)


def _st_holm_harmless_verdict():
    """Holm(한쪽 · 정규 꼬리) · 무해 세 조건 · 판정 어휘(보류 · 측정만 · 기각)."""
    import dstk as E
    h = E.holm_family({"A10": 2.5, "A20": 2.1, "A30": 0.3})
    ok = h["reject"] == {"A10": True, "A20": True, "A30": False} and abs(h["p"]["A10"] - E.norm_sf(2.5)) < 1e-15 and h["m"] == 3
    h2 = E.holm_family({"A10": 2.0, "A20": 1.0, "A30": None})
    ok &= h2["reject"] == {"A10": False, "A20": False, "A30": False}             # p 0.0228 > 0.05/3 — 첫 단계에서 멈춘다
    h3 = E.holm_family({"A10": 2.2, "A20": 1.0, "A30": None})
    ok &= h3["reject"] == {"A10": True, "A20": False, "A30": False}               # p 0.0139 ≤ 0.0167 · 둘째 0.159 > 0.025
    hold = ["2020-%02d" % m for m in range(1, 13)]
    down = {"2020-02", "2020-03"}
    ex = [0.1] * 12
    ok &= E.harmless(ex, hold, down, 3.0)["harmless"] is True
    ok &= E.harmless(ex, hold, down, 10.5)["harmless"] is False
    ok &= E.harmless([0.1, -0.2, -0.1] + [0.1] * 9, hold, down, 3.0)["conds"]["down_x20_ge0"] is False
    ok &= E.harmless([-0.1] * 12, hold, set(), 1.0)["harmless"] is False
    ok &= E.verdict({"A10": True}, {"A10": True}) == "보류" and E.verdict({"A10": False}, {"A10": True}) == "측정만" and E.verdict({"A10": False}, {"A10": False}) == "기각"
    return bool(ok)


def _fake_main(stopped=None):
    """게시 칸 · 결과 문서 시험용 합성 산출(값은 표지 수 0.5555)."""
    if stopped:
        return {"kind": "dstk_out", "stopped": stopped}
    mk = 0.5555
    m = {"n": 120, "ann_ex": mk, "cagr_ex": mk, "te": mk, "ir": mk, "nw_t": mk, "t_iid": mk, "win": 55.5, "years": {"2017": mk, "2018": mk},
         "years_won_full": 5, "n_full_years": 9, "down_mean": mk, "down_win": 50.0, "up_mean": mk, "style": {"alpha_ann": mk, "alpha_t": mk, "n": 119},
         "roll36": {"hit": 55.5, "n": 85}, "mech": {"crash_legs": {"n": 8, "mean": mk, "win": 3}, "rebounds": {"n": 8, "mean": mk, "win": 4}},
         "episodes": [{"kind": "급락", "name": "코로나19 팬데믹", "ex": mk}], "sleeve_beta": 1.1, "turn": 3.3, "halves": [mk, mk], "blocks": [mk, mk, mk, mk],
         "window": ["2016-09", "2026-08"], "series_leak": None}
    row = {"m": m, "m20": {"ann_ex": mk, "nw_t": mk, "down_mean": mk}, "down_frozen": {"n": 35, "mean": mk, "win": 50.0},
           "harmless": {"harmless": True, "conds": {"ann_x20_ge0": True, "down_x20_ge0": True, "turn_le10": True}, "ann_x20": mk, "down_mean_x20": mk, "n_down": 35, "turn": 3.3}}
    rows = {k: dict(row) for k in [p + str(n) for p in "ASEP" for n in (10, 20, 30)] + ["RETF"]}
    d = {"n": 120, "mean_ann": mk, "nw_t": mk, "win": 50.0, "down_mean": mk, "years_won_full": 5, "n_full_years": 9, "d_ir": mk, "style": {"alpha_ann": mk, "alpha_t": mk},
         "window": ["2016-09", "2026-08"]}
    return {"kind": "dstk_out", "window": ["2016-09", "2026-08"], "n_hold": 120, "down": {"n_pr": 39, "n_frozen": 35},
            "f0a": {"ok": True, "corr": 0.99, "gap_pm": 0.01, "n": 120}, "rows": rows,
            "holm": {"p": {"A10": 0.3, "A20": 0.3, "A30": 0.3}, "reject": {"A10": False, "A20": False, "A30": False}, "threshold": {"A10": 0.0167, "A20": None, "A30": None},
                     "order": ["A10", "A20", "A30"], "m": 3, "alpha": 0.05},
            "adopt": {"A10": False, "A20": False, "A30": False}, "verdict": "기각",
            "mech": {str(n): {"fund": dict(d), "sleeve": {"mean_ann": mk, "nw_t": mk, "win": 50.0}} for n in (10, 20, 30)},
            "diffs": {nm: {str(n): dict(d) for n in (10, 20, 30)} for nm in ("A-E", "A-P", "A-RETF")},
            "fidelity": {str(n): {"spread_corr": mk, "v_corr": mk, "g_corr": mk, "fund_ex_corr_retf": mk, "v_turn": 3.0, "g_turn": 5.0} for n in (10, 20, 30)},
            "late": {"from": "2019-06", "rows": {"A10": dict(m, window=["2019-06", "2026-08"])}, "mech": {"10": dict(d, window=["2019-06", "2026-08"])}},
            "composition": {"A10": {"forms": 120, "mean_names_x10": 200, "ndx_only_share_x1000": 30, "not_today_share_x1000": 40, "lvl_adj_share_x1000": 5,
                                    "lvl_pr_share_x1000": 2, "split_rev_share_x1000": 1,
                                    "both_legs_total": 3, "exec_drop_total": 0, "max_w_x1000": 180}},
            "regime": {"value": 36, "neutral": 53, "growth": 31},
            "eg30_ref": {"window": ["2016-09", "2026-08"], "frozen_eval": {"ann_ex": mk}, "corr_fund_ex": {"A10": mk}},
            "xbmrot_ref": {"window": ["2016-09", "2026-08"], "basis": "S&P 500 PR", "frozen": {"ann_ex": mk, "t": mk, "ir": mk}},
            "predictions": {k: True for k in PRED_KO}, "multiplicity": {"m_confirmatory": 3, "alpha": 0.05, "cum_n_before": 985, "rows_counted": 13, "cum_n_after": 998},
            "ps_info": {"vd1_used": 515, "n_fallback": 3},
            "tilt_read": {"A10": {"static_basket": True, "mech_mean_ann": mk, "a_nw_t": mk, "s_nw_t": mk},
                          "A20": {"static_basket": False, "mech_mean_ann": mk, "a_nw_t": mk, "s_nw_t": mk}}}


def _fake_f0():
    return {"ok": True, "bad": [], "builder": {"min_names": 100, "lag_days": 45, "ann_lag_days": 90, "val_fn_is_sc_val": True, "grow_fn_is_sc_grow": True},
            "screen": {}, "ps": {"vd1_used": 515, "n_fallback": 3, "fallback": ["X"]}, "vd1": {"n": 518, "digest": "ab" * 32},
            "regime": {"value": 36, "neutral": 53, "growth": 31, "switches": 41, "edge_1e9": 5, "same_as_t17": True},
            "down": {"n": 39, "n_frozen": 35, "frozen_eq_spytr": True}, "anchor": {"val": {"overlap_adj": 10}, "grow": {"overlap_adj": 10}},
            "forms": {"n": 121, "n_valid": 121, "first_valid": "2016-07", "n_pool": {"min": 464, "med": 504, "max": 521}, "v_cov": {"min": 0.282, "max": 0.942},
                      "cov_late_from": "2019-06", "lvl_adj": {"min": 1, "med": 2, "max": 3}, "lvl_adj_first": 3, "lvl_pr_first": 1, "split_rev_cells": 9},
            "asis_missing_top": [["AVB", 121]], "asis_missing_n_names": 140,
            "home": {"spval": {"overlap": 8, "builder_today_d": "2026-09-25"}, "grow": {"overlap": 9}}, "inherited": {"reassigned_cells": 16, "seam_cut_names": 5}}


def _st_public_and_result_doc():
    """게시 칸 — 캐시 표지 없음 · 공개 안전 · 값 계열 없음 · 결과 문서 머리 세 줄(풀카드 · 판정 · 규칙) · «등록 커밋 `<40자>`» 가 문서의 첫 «커밋 <해시>» ·
    심은 값 계열 · 2016-09 앞 창 실수는 public_safe_std 가 잡는다 · 멈춤 판도 그린다."""
    full = "0123456789abcdef0123456789abcdef01234567"
    out = {CACHE_ONLY_KEY: True, "prereg": PREREG, "f0": _fake_f0(), "main": _fake_main(), "data_pin": DATA_PIN}
    pub = public_doc(out, "0" * 64, 1, {"commit": full})
    blob = json.dumps(pub, ensure_ascii=False)
    txt = result_doc(pub)
    ok = CACHE_ONLY_KEY not in blob and "series_leak" not in blob and "0.56" in txt
    ok &= all(re.search(r"^\s*%s\s*[:：]" % k, txt, re.M) for k in ("풀카드", "판정", "규칙"))
    hm = re.search(r"커밋\s*[`'\"]?([0-9a-f]{7,40})", txt)
    ok &= bool(hm) and hm.group(1) == full
    ok &= re.search(r"^판정:\s*기각", txt, re.M) is not None
    ok &= bool(public_safe_std({"x": {"window": ["2014-09", "2026-08"], "v": 0.5}})) and not public_safe_std({"x": {"window": ["2014-09", "2026-08"], "n": 144}})
    ok &= bool(public_safe_std({"s": [0.1, 0.2, 0.3, 0.4, 0.5]}))
    bad = dict(pub)
    bad["rows"] = dict(pub["rows"], leak=[0.1] * 12)
    ok &= bool(public_safe_std(bad))
    tmpf = tempfile.mkdtemp(prefix="dstk_st_re_")
    try:
        rp = os.path.join(tmpf, "re.txt")
        _write_text(rp, "# 주석\n§2-3 글은 0.25 라 했으나 코드는 다른 값\n\n두 번째 줄 2021-10\n")
        re_ = reg_err_lines(rp)
    finally:
        shutil.rmtree(tmpf, ignore_errors=True)
    txt_re = result_doc(pub, re_)
    ok &= re_[0] == ["§2-3 글은 <num> 라 했으나 코드는 다른 값", "두 번째 줄 2021-10"] and len(re_[1]) == 16
    ok &= ("등록 오류: §2-3 글은 <num> 라 했으나 코드는 다른 값; 두 번째 줄 2021-10" in txt_re) and re_[1] in txt_re and "0.25" not in txt_re
    ok &= "등록 오류: 없음" in txt and "확증 가족 밖" in txt and "정적 바스켓 몫 — 금리 틸트 증거 아님" in txt
    out2 = dict(out, main=_fake_main(stopped="가격 위생 관문 실패"))
    pub2 = public_doc(out2, "0" * 64, 1, {"commit": full})
    txt2 = result_doc(pub2)
    ok &= "## 멈춤" in txt2 and "0.5555" not in json.dumps(pub2) and re.search(r"^판정:\s*보류", txt2, re.M) is not None
    return bool(ok)


def _st_result_write_guard():
    """--result-doc --write 문지기 — 연기 판 · FINISHED 없음 · 산출 sha 불일치 · 커밋이 40자 해시가 아니면 거절 · 모두 맞으면 통과."""
    tmp = tempfile.mkdtemp(prefix="dstk_st_")
    try:
        P = {"out": os.path.join(tmp, "_dstkout.json"), "mark": os.path.join(tmp, "_dstkout.started"), "gitmark": os.path.join(tmp, "gm")}
        with open(P["out"], "wb") as f:
            f.write(b'{"x": 1}\n')
        sha = _sha_file(P["out"])
        for m in (P["mark"], P["gitmark"]):
            _write_text(m, "C · t\n%s %s t\n" % (FINISHED, sha))
        pub = {"dstk_public_view": True, "smoke": False, "out_sha256": sha, "prereg_commit": "a" * 40}
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
    """DSTK_COMMIT 없이 · 모르는 커밋으로는 판 점검이 멈춘다(아무것도 쓰지 않는다)."""
    ok = True
    for env in ({}, {"DSTK_COMMIT": "0" * 40, "_DSTK_NO_FETCH": "1"}):
        try:
            frozen_check(env)
            ok = False
        except SystemExit:
            pass
    return ok


def _st_registered():
    import dstk as E
    return not registered_constants_ok(E)


def _st_wire():
    g0, v0 = "a\n", 'x = 1\nprint("사이트 검증:", 1)\n'
    g1, v1 = wire_texts(g0, v0)
    g2, v2 = wire_texts(g1, v1)
    return bool(g1 == g2 and v1 == v2 and "_dstkout*" in g1 and v1.index("D13 주식판") < v1.index('print("사이트 검증:"'))


def _st_names():
    want = ["data/_dstkout.json", "data/_dstk_other.json", "data/_dstkfwd/genesis.json", "x/dstk_cache/a", "_dstkout.public.json"]
    ok = all(scan_repo_names([f]) for f in want)
    return bool(ok and not scan_repo_names([MANIFEST_FILE, "data/style_top.json", "build/dstk_run.py", "build/dstk.py"]))


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
    import dstk as E
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    return bool(not any(hasattr(E, n) for n in FORBIDDEN_ENGINE_NAMES) and "_dstkfwd" not in src and not check_no_forward())


def _st_no_etf_holding():
    """어떤 줄(A · S · E · P)의 목표도 ETF 를 담지 않는다 — 엔진이 ETF 가격을 여는 곳은 RETF 참고 줄 한 곳뿐이다(소스 대조)."""
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    body = src[src.index("def _main_body():"):src.index("def child_main(")]
    return bool(body.count('("IVE", "IVW")') == 1 and body.count("PXE") >= 3 and "specs[" in body and '"IVE"' not in body[:body.index("# RETF")])


def _st_predictions_signature():
    """예측 칸 = 등록 §5-3 의 일곱(참/거짓만) · F0 서명은 정수 · 날짜 글자 · None 만(실수 없음 — 등록 커밋에 박는 값) · 등록 F0 기대값과 같은 키."""
    import dstk as E
    R = _fake_main()
    P = E.predictions(R)
    ok = set(P) == set(PRED_KO) and all(isinstance(v, bool) for v in P.values())
    f0 = {"forms": {"n": 121, "n_valid": 121, "first_valid": "2016-07", "cov_late_from": "2019-06", "n_pool": {"min": 1, "max": 2}, "v_scored": {"min": 1, "max": 2},
                    "g_scored": {"min": 1}, "n_asis": {"min": 1}, "split_rev_cells": 1, "lvl_adj_first": 1, "lvl_adj": {"min": 1, "max": 2}, "lvl_pr_first": 1},
          "regime": {"value": 1, "neutral": 1, "growth": 1, "switches": 1, "warm": "neutral", "edge_1e9": 0}, "down": {"n": 1, "n_frozen": 1},
          "vd1": {"n": 518}, "ps": {"vd1_used": 1, "n_fallback": 0, "n_split_rev_rows": 1, "n_split_rev_names": 1, "n_splits_json_not_vd1": 0},
          "anchor": {"val": {"overlap_adj": 10, "overlap_wrap": 10}, "grow": {"overlap_adj": 10, "overlap_wrap": 10}}, "asis_missing_n_names": 1,
          "inherited": {"reassigned_cells": 1, "seam_cut_names": 1}, "home": {"spval": {"overlap": 8}, "grow": {"overlap": 9}}}
    sig = E._f0_signature(f0)
    ok &= all(v is None or isinstance(v, (int, str, bool)) and not isinstance(v, float) for v in sig.values())
    ok &= set(sig) == set(E.F0_EXPECT) and all(not isinstance(v, float) for v in E.F0_EXPECT.values())
    return bool(ok)


def _st_git_blob():
    return git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391" and git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


SELFTESTS = (_st_regime, _st_cap_weights, _st_ranked_equals_builder, _st_priced_and_score, _st_scoring_prices, _st_lock_and_tag, _st_tilt_read,
             _st_book_path, _st_exec_target,
             _st_fund_identity, _st_holm_harmless_verdict, _st_public_and_result_doc, _st_result_write_guard, _st_scrub,
             _st_start_guard, _st_frozen_refuses, _st_registered, _st_wire, _st_names, _st_manifest_hashes_only,
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
