# -*- coding: utf-8 -*-
"""build/g_fund_run.py — 거장 슬리브 측정(GURUFUND) 한 번 굽기 러너.

사전등록: build/PREREG-<등록 날짜>-GURUFUND.md 하나(이 러너는 날짜를 박지 않는다 · 결과 문서 = 그 이름 + «-RESULT»).
계산은 build/g_fund.py(엔진)가 한다 — 이 러너는 판 점검 · 핀 판 임시 뿌리 · 자식 과정 · 시작 표식 · 게시 칸 · 결과 문서만 맡는다.

🚨 사용자 결정(2026-09-27): 목적 «혹시 펀드에 깔고갈만한 거장 포트가 있을까해서» · 명단 «c»(밸류 + 성장 27) · «이런 불필요한 미래 일정들은 다 꺼»
   (전방 원장 · 날짜가 박힌 미래 판정 없음 — data/_gffwd/ 가 있으면 멈춘다) · «백테스트 최대 기간은 최근 20년»(측정 창 2014-09 ~ 2026-08 · 144개월) ·
   펀드 틀 S&P 500 90% + 슬리브 10% 대 SPY TR · 편도 10bp · EG30 V0 은 참고 줄만.
🚨 랩 규율: 등록 커밋이 origin 에 오르기 전에는 --selftest · --guard · --pins · --manifest · --precommit · --wire · --smoke 만 된다.
   --smoke 는 눈가린 채(산출을 열지 않고 지운다 · 참/거짓 · 초만 싣는다 · 크기 · 길이 · 형은 싣지 않는다 — 배치 X §0.3 교훈).
   공개(저장소 · 사이트)에는 10년 창(2016-09 ~ 2026-08) 값만 · 144개월 창 값은 저장소 밖 캐시(%TEMP%/gfund_cache/out)에만(MAX_YEARS 10).

  python -X utf8 build/g_fund_run.py --selftest           합성만(실자료 없음)
  python -X utf8 build/g_fund_run.py --guard              사이트 경계(site_guard_std — 참/거짓 · 이름만)
  python -X utf8 build/g_fund_run.py --pins               얼린 파일 · 핀 표(등록 문서 §7 표)
  python -X utf8 build/g_fund_run.py --manifest           data/_gf_manifest.json(해시만) 쓰기
  python -X utf8 build/g_fund_run.py --wire [--apply]     등록 커밋이 .gitignore · build/validate_site.py 끝에 덧붙일 덩이
  python -X utf8 build/g_fund_run.py --precommit          등록 커밋 직전 점검(참/거짓 · 이름만)
  python -X utf8 build/g_fund_run.py --smoke              러너 경로 전체 눈가린 연기(임시 폴더 · 열지 않고 지운다)
  GFUND_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python -X utf8 build/g_fund_run.py --once     한 번 굽기(이 길 하나뿐)
  python -X utf8 build/g_fund_run.py --public-view        굽기 뒤: 산출 → 게시 칸 다시 쓰기(FINISHED 표식이 있을 때만)
  python -X utf8 build/g_fund_run.py --result-doc [<게시 칸 파일>] [--write]   결과 문서(게시 칸 파일 하나만 읽는 얼린 렌더러)

한 번 굽기 규약(x_run · v_run 과 같은 뜻)
  · git fetch origin 을 먼저 한다(실패하면 멈춘다).
  · GFUND_COMMIT = 사전등록 문서 · 러너 · 엔진 · 명세(data/_gf_manifest.json)를 **처음 더한** 커밋 · origin/main 의 조상 · 그 커밋의 등록 문서에 빈칸(⟨TBD)과 초안 괄호(U+3014)가 없다.
  · 얼린 파일(엔진 · 러너 · 명세 · 등록 문서 · 덧붙임 두 곳)이 그 커밋과 바이트 단위로 같다(CRLF 무시).
  · 그 커밋의 data/guru_history.json · build/refresh_13f_history.py 가 등록 blob(HIST_BLOB · HIST_BUILDER_BLOB)과 같다 — 옛 CUSIP 지도로 다시 푼 이력.
  · 자료 핀 — 굽기는 작업 트리의 data/ 를 읽지 않는다. DATA_PIN(760df724b)의 build/ · data/ 를 git archive 로 저장소 밖 임시 뿌리에 풀고
    (트리 sha 대조) data/guru_history.json 하나만 **등록 커밋 판**(옛 CUSIP 지도로 다시 푼 이력 · blob 21afd320…)으로 덧씌우고, 엔진 하나만
    등록 커밋 판으로 넣어 자식 과정으로 돈다. F0-b 는 build/ @ 3bbe5ca1d +
    data/ @ b03694352 + 동결 기록 data/_guru_cmp.json @ 3bbe5ca1d 뿌리에서(아래 F0B_* 주석 — 3bbe5ca1d 의 data/ 는 리베이스로 뒤 자료가 섞였다).
  · 판 점검 → F0-b(얼린 GURUCMP 재현 · 1e-9) · F0(수익 없음) → 시작 표식 셋(로컬 둘 · origin 태그 gfund-started) → 굽기 → 산출 · 게시 칸 · 실행 기록 → FINISHED.
    F0-b · F0 가 실패하면 표식을 쓰기 전에 멈춘다(한 번 굽기를 쓰지 않는다). 등록된 멈춤 조건은 F0 가 표식 전에 먼저 보고(측정 창 · 대체 창),
    굽기 자식 안에서 걸리면(StopBake) {"stopped": 사유} 가 산출이 된다 — 멈춤 기록 · 결과 문서를 쓰고 FINISHED(다시 굽기 없음).
    게시 칸(공개 안전 점검)을 산출보다 먼저 짓는다 — 걸리면 아무 산출도 쓰지 않는다. --result-doc --write 는 연기 판 · FINISHED 없음 · sha 불일치면 거절.
  · FINISHED 가 있으면 무조건 멈춤 · origin 태그가 있으면 멈춤 · 산출 전 기술적 중단이면 이 컴퓨터의 같은 커밋 표식이 있을 때만 GFUND_RERUN=사유 로 처음부터.
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
    c = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "PREREG-*-GURUFUND.md")))
    return ("build/" + c[0]) if len(c) == 1 else "build/PREREG-0000-00-00-GURUFUND.md", len(c)


PREREG, _N_PREREG = _find_prereg()
RESULT = PREREG[:-len(".md")] + "-RESULT.md"
ENGINE = "build/g_fund.py"
RUNNER = "build/g_fund_run.py"
MANIFEST_FILE = "data/_gf_manifest.json"
FIRST_ADDED = (PREREG, RUNNER, ENGINE, MANIFEST_FILE)
FROZEN = (ENGINE, RUNNER, MANIFEST_FILE, PREREG)
REPO_ALLOWED_GF = (MANIFEST_FILE,)
FORWARD_DIR = "data/_gffwd"                                  # 있으면 멈춘다(전방 원장 없음 — 사용자 2026-09-27)
DATA_PIN = "760df724ba97e3c9345a9eba81ac31118c6c4bb3"       # 13F 자료 버그 5건 수정 뒤(origin/main 2026-09-27)
DATA_PIN_TREES = {"data": "38b1e108f40c7a36833e3c1eee8722cb480b4fc9", "build": "0249dcf324f8e8ea3497d898613b840d633853d1"}
DATA_PIN_BLOBS = {"data/guru_history.json": "105ee67ac5841e3704ee3766123d90ac9afb2329",
                  "data/_guru_cmp.json": "a45deddc2ff6607615b0bb0be3a7e3c88a64f567",
                  "data/_qbatch.json": "01fefbf447fc699c8b4c9578a0ce9c2e0ca780f7",
                  "data/mech_episodes.json": "d67a2a74b486aff7f3a46d0f2a9bebe104df669f"}
# F0-b 핀 — 얼린 GURUCMP(가격 키 정정판) 기록은 커밋 3bbe5ca1d 에 있지만 그 커밋의 data/ 는 리베이스로 뒤 CI 자료가 섞였다(stocks · sd · pit_px ·
#   strategy_charts · index_ledger — pit_panel.load_world 가 «pit_px.json 격자가 stocks.json 과 다르다» 로 멈춘다 · 2026-09-27 눈가린 연기에서 찾음).
#   기록을 실제로 구운 트리는 리베이스 전 원본 77e31bc39(로컬 reflog · origin 에 없다)이고, 그 입력은 origin/main 의 조상 b03694352 의 data/ 와 같다
#   (다른 것은 출력 셋 _guru_cmp · _idxeg · strategy_index 뿐) · build/ 트리는 3bbe5ca1d 와 77e31bc39 가 같다(230d95cd). 그래서 F0-b 뿌리 =
#   build/ @ 3bbe5ca1d + data/ @ b03694352 + 동결 기록 data/_guru_cmp.json @ 3bbe5ca1d(blob a45deddc).
# 이력 덧씌우기 — 2026-09-27 등록 전 자료 수선(검토 지적 · 옛 CUSIP 지도가 없어 CUSIP 이 바뀐 종목의 옛 분기가 이력에서 빠졌다 ·
#   체결월 2014-08 에 시점정확 멤버 38종을 명단 전원 아무도 안 든 것으로 셌다). build/refresh_13f_history.py 에 옛 CUSIP 지도(CUSIP_HIST ·
#   74개)를 더해 **같은 SEC 응답 · 같은 월봉**으로 다시 푼 이력을 등록 커밋에 넣는다(바뀐 것은 보유 칸 더하기뿐 — 6,152칸 · (분기, 운용사) 17쌍 ·
#   빠지거나 값이 바뀐 칸 0 · 월봉 · 공시일 그대로). 굽기 뿌리는 DATA_PIN 판에 이 파일 하나만 등록 커밋 판으로 덧씌운다.
HIST_FILE = "data/guru_history.json"
HIST_BLOB = "21afd320740547a82da71978583305d1b43c78a0"          # 등록 커밋 판(수선 뒤)
HIST_BASE_BLOB = "105ee67ac5841e3704ee3766123d90ac9afb2329"     # DATA_PIN 판(수선 전)
HIST_BUILDER = "build/refresh_13f_history.py"
HIST_BUILDER_BLOB = "f46483fad315174cf2f72d934dd9ee529197adfa"  # 그 이력을 만든 빌더(CUSIP_HIST 74개) — 등록 커밋 판과 같아야 한다
MAIN_TREE_BLOBS = dict(DATA_PIN_BLOBS, **{HIST_FILE: HIST_BLOB})
WORKTREE = "WORKTREE"                                           # 연기 전용 덧씌우기 출처(작업 트리 파일 · blob 대조는 같다)
F0B_CODE_PIN = "3bbe5ca1d496bfb14648502fedb59f06a2e3d171"
F0B_DATA_PIN = "b036943529af797ebe5e5f0287959824d959ad00"
F0B_PIN = F0B_CODE_PIN
F0B_PIN_TREES = {"build": (F0B_CODE_PIN, "230d95cd203e69ba5b90fe8a939de3a3cf28be57"), "data": (F0B_DATA_PIN, "53d1c2ec21937c27f5334a70c50fdb98f28402cc")}
F0B_OVERLAY = {"data/_guru_cmp.json": F0B_CODE_PIN}
F0B_PIN_BLOBS = {"data/_guru_cmp.json": "a45deddc2ff6607615b0bb0be3a7e3c88a64f567",
                 "data/guru_history.json": "6ac2910963e2dde3cd667cebe094dbb3395afaf9"}
F0B_PROVENANCE = {"record_commit": F0B_CODE_PIN, "pre_rebase_original": "77e31bc395f10f699f226b780cca65945bedb8af", "inputs_equal_to": F0B_DATA_PIN,
                  "build_tree_same_as_pre_rebase": "230d95cd203e69ba5b90fe8a939de3a3cf28be57",
                  "pre_rebase_parent": F0B_DATA_PIN, "pre_rebase_data_tree": "856fdc98a10f7dd7135c5588f9639be9f85c07ac",
                  "data_files_differing_from_parent": {"data/_guru_cmp.json": "a45deddc2ff6607615b0bb0be3a7e3c88a64f567",
                                                       "data/_idxeg.json": "793c0903e1511c7673fd9e2e85b3782f867fc2cd", "data/strategy_index.json": "404bc554055c4129295cdb4ba42e89d3998458b2"}}
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
PLACEHOLDER, DRAFT_MARK = "⟨TBD", "〔"
SMOKE_ENV_KEYS = ("GFUND_SMOKE",)
# 등록 상수 — 엔진(g_fund)의 값과 같아야 굽는다(등록 문서 §2 · §3 · §4)
REGISTERED = {
    "K": 2, "MIN_HOLD": 5, "COST": 0.001, "SLEEVE": 0.1, "TE": 0.02, "CAP_MODE": "prop",
    "WIN": ("2014-09", "2026-08"), "PUB": ("2016-09", "2026-08"), "SIG": ("2014-08", "2026-07"), "AS_OF": "2026-09", "N_WIN": 144,
    "F0A_CORR": 0.98, "F0A_GAP": 0.30, "F0E_MIN_MGR": 5, "F0E_MIN_NAMES": 10, "F0E_FRAC": 0.90, "NW_LAG": 3, "ROLL_N": 36,
    "FF_FACTORS": ("mkt_rf", "smb", "hml", "mom"), "TOL_F0B": 1e-9, "F0B_TODAY": (2026, 9, 24), "F0B_SIG": ("2016-08", "2026-07"),
    "F0B_END": "2026-08", "F0B_JUDGE0": "2018-07",
    "CAND": {"nw_t_min": 2.0, "style_alpha_t_min": 1.5, "years_won_frac": 0.70, "min_full_years": 9, "roll36_hit_min": 60.0,
             "ctrl_nw_t_min": 1.5, "ctrl_alpha_t_min": 1.5},
    "F0F_MAX_SPX": 3, "F0F_MAX_UNION": 5, "LAG_Q": 2,
    "F0D_OLD_CUSIP": (("GOOGL", "2014-08", 2), ("AVGO", "2017-08", 2), ("LRCX", "2018-08", 2)),
    "CUM_N_BEFORE": 968, "N_ROWS_COUNTED": 8, "PRIMARY": "VG", "ARM_NAMES": ("VG", "C", "C-BW"), "SIGNALS": ("S1", "S2"),
    "BRIDGEWATER": 1350694, "QUANT": (1037389, 1167557, 1510387), "HIST_ONLY_VALUE": (1649339,),
    "VALUE": (1067983, 1061768, 1709323, 1112520, 1358706, 1056831, 1720792, 1096343, 1549575, 860643, 1036325, 813917, 807985, 1697868, 915191, 1569205),
    "GROWTH": (1167483, 1061165, 1103804, 1135730, 1697748, 1747057, 1541617, 1798849, 934639, 1602189, 1088875),
    "ACTIVIST": (2026053, 1040273, 1791786, 1345471, 1418814, 921669, 1517137, 1998597, 1489933),
    "MACRO": (1350694, 1029160, 1536411), "CREDIT": (1656456, 949509, 1035674), "ENDOW": (1166559,),
}
FORBIDDEN_ENGINE_NAMES = ("ff1", "ff2", "ff0", "forward_ledger", "genesis")    # 전방 판정 · 원장 함수가 엔진에 없어야 한다


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록 · 임시 뿌리는 모두 저장소 밖(<캐시>)
# ══════════════════════════════════════════════════════════════════════════
CACHE = os.environ.get("GFUND_CACHE") or os.path.join(tempfile.gettempdir(), "gfund_cache")
GIT_MARK_NAME = "gfund_started"
START_TAG = "gfund-started"
FINISHED = "FINISHED"
_OVR = {"out": None, "gitmark": None, "tag": None}
OUT_NAMES = {"out": "_gfund.json", "mark": "_gfund.started", "runlog": "_gfund.run.json", "public": "_gfund.public.json"}
CACHE_ONLY_KEY = "__gf_cache_only__"
PUBLIC_FROM = "2016-09"
PUBLIC_FLOAT_KEYS = re.compile(r"(^|_)(coverage|frac|tol|min|max|thr|sec)(_|$)")
COUNT_KEYS = re.compile(r"(^n$|^n_|_n$|count|^k$|months?$|days?$|years?$|^rows$|bytes$|names|managers|forms|leaves|reb|holders)")
OUTPUT_NAME_MARKS = ("_gfund",)
OUTPUT_CONTENT_MARKS = (CACHE_ONLY_KEY.encode(), b"_gfund.json", b"_gfund.public.json", b"_gfund.run.json", b'"gfund_public_view"')


def _norm(p):
    return os.path.normcase(os.path.abspath(os.fspath(p)))


def _inside(p, root):
    a, r = _norm(p), _norm(root)
    return a == r or a.startswith(r + os.sep)


def cache_guard_std(cache=None, root=None):
    c, r = cache or CACHE, root or ROOT
    if _inside(c, r) or _inside(r, c):
        raise SystemExit("🚨 캐시(%s)가 저장소(%s) 안이다 — 144개월 수치 · 임시 뿌리는 저장소 밖에만." % (c, r))
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
        have += [os.path.join(P["dir"], f) for f in os.listdir(P["dir"]) if f.startswith("_gfund") and (f.endswith(".json") or f.endswith(".part"))]
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
    """오류 꼬리에서 소수 · 지수꼴(1e-05 · 2.5E+03)을 <num> 으로(값이 새지 않게). 정수는 남긴다 — 줄 번호 · 개수 · 날짜라서다."""
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
        if f.startswith("data/_gf") and f not in REPO_ALLOWED_GF:
            bad.append("허용 밖 파일: %s" % f)
        if f.startswith(FORWARD_DIR + "/") or f == FORWARD_DIR:
            bad.append("전방 원장 파일(사용자 2026-09-27 «미래 일정은 다 꺼»): %s" % f)
        if "gfund_cache" in f:
            bad.append("캐시 사본으로 보이는 파일: %s" % f)
    return bad


def site_guard_std(root=None):
    """GURUFUND 사이트 경계 — git 이 추적 · 추가 예정인 파일 가운데 (가) 굽기 산출 이름(_gfund*) (나) 허용 밖 data/_gf* (다) 전방 원장 data/_gffwd/*
    (라) 명세(data/_gf_manifest.json)가 해시만인가 (마) 사이트 자료(뿌리 *.html · js/*.js · data/*.json)의 굽기 산출 표식."""
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
            bad.append("사이트 자료 %s 에 GURUFUND 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


# ── 덧붙임 두 곳(.gitignore · validate_site) ─────────────────────────────
GITIGNORE_BLOCK = """
# 거장 슬리브 측정(PREREG-*-GURUFUND · 사용자 20년 규칙 2026-09-27) — 144개월 산출(_gfund.json · _gfund.public.json · _gfund.run.json · _gfund.started)이나
#   캐시 사본(gfund_cache)이 작업 트리에 복사돼도 쓸려 들지 않게. 명세(data/_gf_manifest.json)는 «_gf_» 라 걸리지 않는다.
_gfund*
gfund_cache/
"""
VALIDATE_BLOCK = """
# ── 거장 슬리브 측정(PREREG-*-GURUFUND · 사용자 20년 규칙 2026-09-27) 사이트 경계 ─────────────────────────────
# 144개월 산출(_gfund*)이 저장소 · 사이트 자료에 없어야 한다(사이트는 10년 · MAX_YEARS 10). data/_gf* 는 해시만 담은 명세(_gf_manifest) 하나뿐 ·
#   data/_gffwd/ 없음(전방 원장 없음 · 사용자 2026-09-27) · 사이트 자료에 굽기 산출 표식 없음.
#   build/g_fund_run.py 는 모듈 머리에서 표준 라이브러리만 불러온다(site_guard_std). 러너(g_fund_run.frozen_check)도 같은 함수를 부른다.
try:
    import importlib as _il_gf
    _gfr = _il_gf.import_module("g_fund_run")
    _ggf = _gfr.site_guard_std(ROOT)
    if not _ggf["ok"]:
        errors.append("거장 슬리브 측정 사이트 경계 위반 %d건 — %s. 144개월 산출(_gfund*)은 저장소 밖 캐시에만 둔다"
                      % (_ggf.get("n_bad", len(_ggf["bad"])), " · ".join(_ggf["bad"][:4])))
    else:
        print("  ~ 거장 슬리브 측정 사이트 경계 통과(파일 %d · 사이트 자료 %d 훑음)" % (_ggf["n_files"], _ggf["n_scanned"]))
except Exception as _e:
    # 닫힌 쪽 — 이 경계를 확인하지 못하면 통과시키지 않는다(144개월 산출이 새는지 모른 채 게시하지 않는다 · 2026-09-27 검토 지적)
    errors.append("거장 슬리브 측정 사이트 경계 검사가 예외로 죽었다 — %s (확인하지 못하면 통과시키지 않는다)" % str(_e)[:80])
"""
_VALIDATE_ANCHOR = 'print("사이트 검증:"'


def wire_texts(gitignore_txt, validate_txt):
    g = gitignore_txt
    if "_gfund*" not in g:
        g = g.rstrip("\n") + "\n" + GITIGNORE_BLOCK
    v = validate_txt
    if "거장 슬리브 측정(PREREG-*-GURUFUND" not in v:
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
        bad.append("build/PREREG-*-GURUFUND.md 가 %d 개" % _N_PREREG)
    elif not re.fullmatch(r"build/PREREG-20\d\d-[01]\d-[0-3]\d-GURUFUND\.md", PREREG):
        bad.append("이름 꼴: %s" % PREREG)
    return bad


def placeholder_counts(text):
    return text.count(PLACEHOLDER), text.count(DRAFT_MARK)


def _normv(x):
    if isinstance(x, (list, tuple)):
        return tuple(_normv(v) for v in x)
    if isinstance(x, dict):
        return {k: _normv(v) for k, v in x.items()}
    if isinstance(x, float):
        return round(x, 15)
    return x


def registered_constants_ok(E=None):
    if E is None:
        import g_fund as E
    bad = []
    for k, want in REGISTERED.items():
        have = getattr(E, k, "<없음>")
        if _normv(have) != _normv(want):
            bad.append("%s = %r (등록 %r)" % (k, have, want))
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
    """data/_gf_manifest.json — 해시만(값 없음)."""
    def rp(c, spec):
        r = _git("rev-parse", "%s:%s" % (c, spec))
        return r.stdout.strip() if r.returncode == 0 else None
    engine_imports = ("guru17_backtest", "guru_overlap_backtest", "guru_cmp", "idxrev", "idxtilt", "pit_panel", "pit_alias", "pit_quarantine",
                      "tech_backtest", "refresh_13f", "qbatch_core", "eg30plus", "qg_lab", "stoploss")
    return {"kind": "gfund_manifest", "note": "거장 슬리브 측정(GURUFUND) 명세 — 해시만(값 없음). 러너 판 점검이 이 파일을 등록 커밋 판과 대조한다.",
            "prereg": PREREG, "engine": ENGINE, "runner": RUNNER,
            "code_sha256_lf": {p: (_sha_lf(_bytes(os.path.join(ROOT, *p.split("/")))) if os.path.exists(os.path.join(ROOT, *p.split("/"))) else None)
                               for p in (ENGINE, RUNNER)},
            "data_pin": {"commit": DATA_PIN, "trees": dict(DATA_PIN_TREES), "blobs": dict(DATA_PIN_BLOBS),
                         "reused_modules_blob": {("build/%s.py" % m): rp(DATA_PIN, "build/%s.py" % m) for m in engine_imports},
                         "read_files_blob": {f: rp(DATA_PIN, f) for f in ("data/stocks.json", "data/pit_px.json", "data/index_history.json",
                                                                         "data/assets.json", "data/bench_px.json", "data/rf_monthly.json",
                                                                         "data/ff_daily.json", "data/pit_universe.json", "data/pit_reuse.json",
                                                                         "data/index_ledger.json")}},
            "f0b_pin": {"code_commit": F0B_CODE_PIN, "data_commit": F0B_DATA_PIN, "trees": {k: list(v) for k, v in F0B_PIN_TREES.items()},
                        "overlay": dict(F0B_OVERLAY), "blobs": dict(F0B_PIN_BLOBS), "provenance": dict(F0B_PROVENANCE),
                        "reused_modules_blob": {("build/%s.py" % m): rp(F0B_CODE_PIN, "build/%s.py" % m)
                                                for m in ("guru_cmp", "guru_overlap_backtest", "guru17_backtest", "idxrev", "idxtilt", "pit_panel",
                                                          "pit_quarantine", "tech_backtest", "refresh_13f")}},
            "hist_overlay": hist_overlay_doc(),
            "start_tag": START_TAG, "git_mark": GIT_MARK_NAME, "forward": "없음 — 사용자 2026-09-27 «이런 불필요한 미래 일정들은 다 꺼»"}


def hist_overlay_doc():
    return {"file": HIST_FILE, "blob": HIST_BLOB, "base_blob_at_data_pin": HIST_BASE_BLOB, "source": "등록 커밋(GFUND_COMMIT) 판",
            "builder": HIST_BUILDER, "builder_blob": HIST_BUILDER_BLOB, "smoke_source": "작업 트리(같은 blob 이어야)"}


def hist_problems(commit=None):
    """이력 덧씌우기 — commit 이 없으면 작업 트리 파일(등록 커밋 직전) · 있으면 그 커밋 판 · blob 이 등록 값과 같은가(빌더도)."""
    bad = []
    for f, want in ((HIST_FILE, HIST_BLOB), (HIST_BUILDER, HIST_BUILDER_BLOB)):
        if commit is None:
            fp = os.path.join(ROOT, *f.split("/"))
            have = git_blob_sha(_bytes(fp)) if os.path.exists(fp) else None
        else:
            r = _git("rev-parse", "%s:%s" % (commit, f))
            have = r.stdout.strip() if r.returncode == 0 else None
        if have != want:
            bad.append("%s blob %s (등록 %s)" % (f, (have or "없음")[:8], want[:8]))
    return bad


def write_manifest():
    doc = manifest_doc()
    bad = manifest_problems(doc)
    if bad:
        raise SystemExit("🚨 명세가 해시만이 아니다: %s" % bad[:3])
    miss = [k for k, v in doc["data_pin"]["reused_modules_blob"].items() if v is None] + [k for k, v in doc["f0b_pin"]["reused_modules_blob"].items() if v is None]
    if miss:
        raise SystemExit("🚨 핀 커밋에 없는 모듈: %s" % ", ".join(miss))
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
    for k in ("data_pin", "f0b_pin", "prereg", "start_tag", "hist_overlay"):
        if doc.get(k) != want.get(k):
            bad.append("명세 %s 가 러너 상수와 다르다" % k)
    bad += manifest_problems(doc)
    return bad


def pins_check():
    """핀 커밋 · 트리 · blob 이 등록 값과 같은가(git 개체만 · 자료를 열지 않는다)."""
    bad = []
    for c in (DATA_PIN, F0B_CODE_PIN, F0B_DATA_PIN):
        if _git("cat-file", "-e", c + "^{commit}").returncode != 0:
            bad.append("핀 커밋 %s 가 없다" % c[:9])
        elif _git("merge-base", "--is-ancestor", c, "origin/main").returncode != 0:
            bad.append("핀 커밋 %s 가 origin/main 의 조상이 아니다" % c[:9])
    want = [(DATA_PIN, spec, sha) for spec, sha in list(DATA_PIN_TREES.items()) + list(DATA_PIN_BLOBS.items())]
    want += [(c, spec, sha) for spec, (c, sha) in F0B_PIN_TREES.items()]
    want += [(F0B_OVERLAY.get(f, F0B_DATA_PIN), f, sha) for f, sha in F0B_PIN_BLOBS.items()]
    for c, spec, sha in want:
        r = _git("rev-parse", "%s:%s" % (c, spec))
        if r.returncode != 0 or r.stdout.strip() != sha:
            bad.append("핀 %s:%s 가 등록 값과 다르다" % (c[:9], spec))
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
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 GFUND_RERUN=사유 로 처음부터." % ", ".join(os.path.basename(m) for m, _ in marks))
    if rerun and not marks:
        raise SystemExit("🚨 GFUND_RERUN 은 이 컴퓨터의 시작 표식(산출 전 중단)이 있을 때만이다.")
    if rerun and not all(txt.startswith(full) for _, txt in marks):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    if remote_tag is not None and not rerun:
        raise SystemExit("🚨 origin 에 시작 태그(%s)가 있다 — 한 번 굽기가 이미 시작됐다." % START_TAG)
    return True


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
        raise SystemExit("🚨 시작 태그를 origin 에 밀지 못했다 — 계산하지 않는다(로컬 표식은 남는다 · 고친 뒤 GFUND_RERUN).")
    return "pushed"


def _mark_finished(P, sha):
    line = "%s %s %s\n" % (FINISHED, sha, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):
        with io.open(m, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)


# ══════════════════════════════════════════════════════════════════════════
#  핀 판 임시 뿌리 · 자식 과정
# ══════════════════════════════════════════════════════════════════════════
def materialize(dest, build_commit, data_commit, blobs, overlay=None):
    """git archive <build_commit> build + <data_commit> data → dest(저장소 밖) · 덧씌울 파일(overlay: 경로 → 커밋) · 핀 blob 대조 ·
    엔진 하나만 작업 트리(= 등록 커밋 판) 것으로 바꿔 넣는다."""
    if _inside(dest, ROOT):
        raise SystemExit("🚨 임시 뿌리가 저장소 안이다.")
    os.makedirs(dest, exist_ok=True)
    for commit, part in ((build_commit, "build"), (data_commit, "data")):
        pr = subprocess.Popen(["git", "-C", ROOT, "archive", "--format=tar", commit, part], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        with tarfile.open(fileobj=pr.stdout, mode="r|") as tf:
            tf.extractall(dest, filter="data")
        pr.stdout.close()
        if pr.wait() != 0:
            raise SystemExit("🚨 git archive %s %s 실패" % (commit[:9], part))
    for f, commit in (overlay or {}).items():
        if commit == WORKTREE:
            data_ = _bytes(os.path.join(ROOT, *f.split("/"))).replace(b"\r\n", b"\n")
        else:
            b = _git_bytes("show", "%s:%s" % (commit, f))
            if b.returncode != 0:
                raise SystemExit("🚨 덧씌울 파일 %s:%s 가 없다" % (commit[:9], f))
            data_ = b.stdout
        with open(os.path.join(dest, *f.split("/")), "wb") as fh:
            fh.write(data_)
    bad = []
    for f, want in blobs.items():
        fp = os.path.join(dest, *f.split("/"))
        if not os.path.exists(fp) or git_blob_sha(_bytes(fp)) != want:
            bad.append(f)
    if bad:
        raise SystemExit("🚨 임시 뿌리 %s 의 핀 파일이 등록 값과 다르다: %s" % (data_commit[:9], ", ".join(bad)))
    shutil.copyfile(os.path.join(ROOT, *ENGINE.split("/")), os.path.join(dest, *ENGINE.split("/")))
    return dest


def run_child(tree, mode, out_path, timeout=6 * 3600):
    env = dict(os.environ)
    env.update(ENV_PINS)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
    for k in SMOKE_ENV_KEYS + ("GFUND_COMMIT", "GFUND_RERUN"):
        env.pop(k, None)
    t = time.time()
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(tree, *ENGINE.split("/")), "--child", mode, "--out", out_path],
                       cwd=tree, env=env, capture_output=True, timeout=timeout)
    sec = round(time.time() - t, 1)
    if r.returncode != 0 or not os.path.exists(out_path):
        tail = _scrub(r.stderr.decode("utf-8", "replace"))[-2500:]
        raise SystemExit("🚨 자식 과정(%s) 실패 — 산출을 쓰지 않았다:\n%s" % (mode, tail))
    return sec


def preflight(work, hist_src):
    """F0-b(3bbe5ca1d 뿌리) · F0(760df724b 뿌리 + 등록 커밋 판 이력) — 수익 없음 · 값 없음(참/거짓 · 개수 · 날짜). 둘 다 통과해야 표식을 쓴다."""
    t0 = time.time()
    tb = materialize(os.path.join(work, "tree_f0b"), F0B_CODE_PIN, F0B_DATA_PIN, F0B_PIN_BLOBS, F0B_OVERLAY)
    p_b = os.path.join(work, "child_f0b.json")
    sec_b = run_child(tb, "f0b", p_b)
    f0b = _read_json(p_b)
    shutil.rmtree(tb, ignore_errors=True)
    if not f0b.get("ok"):
        raise SystemExit("🚨 F0-b 재현 실패 — 얼린 GURUCMP 기록 재현 %s · 엔진 셈 %s · 엔진 행 %s (구현 결함 · 굽지 않는다) · 어긋난 곳 %s"
                         % (f0b.get("record_reproduced"), f0b.get("engine_counts_same"), f0b.get("engine_rows_same"),
                            (f0b.get("bad_leaves") or []) + (f0b.get("rows_bad") or [])))
    tm = materialize(os.path.join(work, "tree_main"), DATA_PIN, DATA_PIN, MAIN_TREE_BLOBS, {HIST_FILE: hist_src})
    p_0 = os.path.join(work, "child_f0.json")
    sec_0 = run_child(tm, "f0", p_0)
    f0 = _read_json(p_0)
    if not f0.get("ok"):
        raise SystemExit("🚨 F0 실패 — 팔 %s · F0-c %s · F0-d %s · 창 %s · F0-f 옛 CUSIP %s · 멈춤 조건 %s (굽지 않는다)"
                         % ((f0.get("arms") or {}).get("ok"), (f0.get("f0c") or {}).get("ok"), (f0.get("f0d") or {}).get("ok"),
                            (f0.get("window") or {}).get("ok"), (f0.get("f0f") or {}).get("ok"), (f0.get("stops") or {}).get("ok")))
    return {"f0b": f0b, "f0": f0, "tree_main": tm, "sec": {"f0b": sec_b, "f0": sec_0, "total": round(time.time() - t0, 1)}}


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기 전 · 하나라도 어긋나면 SystemExit — 아무것도 쓰지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _versions():
    import numpy, scipy, pandas
    return {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "python": sys.version.split()[0]}


def frozen_check(env=None):
    real = env is None
    env = os.environ if env is None else env
    c = env.get("GFUND_COMMIT")
    if not c:
        raise SystemExit("🚨 GFUND_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --selftest · --guard · --pins · --manifest · --precommit · --smoke 만 된다.")
    nb = name_check()
    if nb:
        raise SystemExit("🚨 등록 문서: %s" % "; ".join(nb))
    if real or not env.get("_GFUND_NO_FETCH"):
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
    rerun = env.get("GFUND_RERUN")
    marks = [(m, _read_text(m)) for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    remote = _remote_start_tag() if (real or not env.get("_GFUND_NO_FETCH")) else env.get("_GFUND_REMOTE_TAG")
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
        raise SystemExit("🚨 덧붙임 두 곳이 붙지 않았다(.gitignore %s · validate_site %s) — `g_fund_run.py --wire --apply` 를 등록 커밋에." % (gw, vw))
    hb = hist_problems(full)
    if hb:
        raise SystemExit("🚨 등록 커밋의 이력 덧씌우기: %s" % "; ".join(hb))
    pb = pins_check()
    if pb:
        raise SystemExit("🚨 자료 핀: %s" % "; ".join(pb[:4]))
    mb = manifest_check()
    if mb:
        raise SystemExit("🚨 명세: %s" % "; ".join(mb[:4]))
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
    if smoke and not os.path.basename(os.path.dirname(os.path.abspath(P["dir"]))).startswith("gfund_runner_smoke_"):
        raise SystemExit("🚨 연기 굽기 폴더가 <캐시>/gfund_runner_smoke_*/out 이 아니다.")
    if not smoke and _OVR["out"]:
        raise SystemExit("🚨 진짜 굽기에 연기 경로가 켜져 있다.")
    work = tempfile.mkdtemp(prefix="gfund_work_", dir=os.path.dirname(P["dir"]) if smoke else cache_guard_std())
    try:
        pf = preflight(work, WORKTREE if smoke else commit)      # 표식 전 — 실패하면 한 번 굽기를 쓰지 않는다
        started = (_read_text(P["mark"] if os.path.exists(P["mark"]) else P["gitmark"]).strip() if rerun
                   else "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S")))
        for m in (P["mark"], P["gitmark"]):
            if not os.path.exists(m):
                _write_text(m, started + "\n")
        tag = _push_start_tag(commit)
        p_m = os.path.join(work, "child_main.json")
        err = []
        try:
            sec_m = run_child(pf["tree_main"], "main", p_m)
        except SystemExit as e:
            raise SystemExit("🚨 굽기 계산 실패 — 산출을 쓰지 않았다(산출 전 기술적 중단이면 GFUND_RERUN=사유 로 처음부터 · 같은 얼린 코드로만):\n%s" % str(e)[-2000:])
        main = _read_json(p_m)
        out = {CACHE_ONLY_KEY: True, "kind": "gfund_bake", "prereg": PREREG, "prereg_commit": commit, "smoke": smoke,
               "data_pin": DATA_PIN, "f0b_pin": F0B_CODE_PIN, "f0b_data_pin": F0B_DATA_PIN, "f0b": pf["f0b"], "f0": pf["f0"], "main": main}
        blob = (json.dumps(out, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        sha = hashlib.sha256(blob).hexdigest()
        rec = {"commit": commit, "registration_error": err, "smoke": smoke}
        pub = public_doc(out, sha, len(blob), rec)               # 공개 안전에 걸리면 여기서 멈춘다 — 산출을 쓰기 전(끝나지 않은 산출이 남지 않게)
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
                  "data_pin": DATA_PIN, "f0b_pin": F0B_CODE_PIN, "f0b_data_pin": F0B_DATA_PIN, "code_sha": code_shas(), "registration_error": err, "smoke": smoke,
                  "note": "값 없음 — 결과는 _gfund.public.json 의 칸만 결과 문서로 옮긴다(등록 §6 공개 규칙)"}
        _write_text(P["runlog"], json.dumps(runlog, ensure_ascii=False, indent=1) + "\n")
        _mark_finished(P, sha)
        if not smoke:
            print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)" % (P["out"], sha[:16], runlog["sec"]))
        return runlog
    finally:
        shutil.rmtree(work, ignore_errors=True)


def once():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("GFUND_RERUN"))


# ══════════════════════════════════════════════════════════════════════════
#  게시 칸(10년 창 값 · 144개월 창은 참/거짓 · 개수만)
# ══════════════════════════════════════════════════════════════════════════
PUB_METRIC_KEYS = ("n", "ann_ex", "cagr_ex", "cagr_fund", "cagr_index", "te", "ir", "t_iid", "nw_t", "win", "years", "years_won_full", "n_full_years",
                   "down_n", "down_mean", "down_t", "down_win", "up_mean", "up_win", "down_capture", "up_capture", "sleeve_beta",
                   "episodes", "crash_won", "surge_won", "mech", "roll12", "roll36", "style", "mdd_fund", "mdd_index", "halves")   # turn 은 전 창 값이라 뺀다
PUB_DIFF_KEYS = ("n", "mean_ann", "nw_t", "t_iid", "win", "down_mean", "up_mean", "years_won_full", "n_full_years", "d_ir", "style")
PUB_NATIVE_KEYS = ("n", "ex", "ex_net", "te", "ir", "ir_net", "t", "t_net", "win", "placebo_ir")


def _pick(d, keys, window):
    out = {k: d.get(k) for k in keys if k in (d or {})}
    out["window"] = list(window)
    return out


def _bool_view(full, window):
    """144개월 창 칸 → 참/거짓 · 개수만(공개)."""
    st = full.get("style") or {}
    return {"window": list(window), "n": full.get("n"), "ann_ex_pos": bool((full.get("ann_ex") or 0) > 0),
            "nw_t_ge_2": bool((full.get("nw_t") or 0) >= 2.0), "nw_t_ge_1_5": bool((full.get("nw_t") or 0) >= 1.5),
            "style_alpha_pos": bool((st.get("alpha_ann") or 0) > 0), "style_alpha_t_ge_1_5": bool((st.get("alpha_t") or 0) >= 1.5),
            "down_mean_ge_0": bool((full.get("down_mean") if full.get("down_mean") is not None else -1) >= 0),
            "years_won_full": full.get("years_won_full"), "n_full_years": full.get("n_full_years")}


def public_doc(out, sha=None, nbytes=None, rec=None):
    """게시 칸 — 결과 문서가 옮길 수 있는 칸만(10년 창 값 · 144개월 창 참/거짓 · 개수 · F0 참/거짓 · 개수 · 날짜). public_safe_std 를 통과해야 쓴다."""
    rec = rec or {}
    f0b, f0, M = out.get("f0b") or {}, out.get("f0") or {}, out.get("main") or {}
    pv = {"gfund_public_view": True, "prereg": out.get("prereg"), "prereg_commit": rec.get("commit"), "out_sha256": sha, "out_bytes": nbytes,
          "smoke": bool(rec.get("smoke")), "registration_error": list(rec.get("registration_error") or []),
          "stopped": M.get("stopped"), "data_pin": out.get("data_pin"), "f0b_pin": out.get("f0b_pin"), "f0b_data_pin": out.get("f0b_data_pin"),
          "f0b": {k: f0b.get(k) for k in ("ok", "record_reproduced", "engine_counts_same", "engine_rows_same", "n_leaves", "n_bad_leaves", "n_reb", "n_allow")},
          "f0": {"ok": f0.get("ok"), "arms": {k: (f0.get("arms") or {}).get(k) for k in ("ok", "n_current", "n_history")},
                 "f0c_ok": (f0.get("f0c") or {}).get("ok"), "f0d": f0.get("f0d"), "window": f0.get("window"), "panel": f0.get("panel"),
                 "f0e": f0.get("f0e"), "composition": f0.get("composition"), "f0f": f0.get("f0f"), "stops": f0.get("stops")},
          "forward": "없음 — 사용자 2026-09-27 «이런 불필요한 미래 일정들은 다 꺼» (전방 원장 · 날짜가 박힌 미래 판정 없음)"}
    if not M.get("stopped"):
        win_full = M.get("window_used") or []
        pub_w = ["2016-09", "2026-08"]
        cells, full_b = {}, {}
        for a, sd in (M.get("cells") or {}).items():
            cells[a], full_b[a] = {}, {}
            for s, c in sd.items():
                cells[a][s] = _pick(c["pub"], PUB_METRIC_KEYS, pub_w)
                full_b[a][s] = _bool_view(c["full"], win_full)
        ctrl = {k: _pick(v["pub"], PUB_METRIC_KEYS, pub_w) for k, v in (M.get("controls") or {}).items()}
        diffs = {nm: {s: _pick(v["pub"], PUB_DIFF_KEYS, pub_w) for s, v in d.items()} for nm, d in (M.get("diffs") or {}).items()}
        cdiffs = {a: {s: _pick(v["pub"], PUB_DIFF_KEYS, pub_w) for s, v in d.items()} for a, d in (M.get("ctrl_diffs") or {}).items()}
        dfull = {nm: {s: {"window": list(win_full), "mean_pos": bool((v["full"].get("mean_ann") or 0) > 0),
                          "abs_nw_t_lt_1_5": bool(abs(v["full"].get("nw_t") or 0) < 1.5), "nw_t_ge_1_5": bool((v["full"].get("nw_t") or 0) >= 1.5),
                          "nw_t_ge_2": bool((v["full"].get("nw_t") or 0) >= 2.0),
                          "style_alpha_pos": bool(((v["full"].get("style") or {}).get("alpha_ann") or 0) > 0),
                          "style_alpha_t_ge_1_5": bool(((v["full"].get("style") or {}).get("alpha_t") or 0) >= 1.5)}
                      for s, v in d.items()} for nm, d in list((M.get("diffs") or {}).items()) + [("ctrl|" + a, d) for a, d in (M.get("ctrl_diffs") or {}).items()]}
        nat = {a: _pick(v["pub"], PUB_NATIVE_KEYS, pub_w) for a, v in (M.get("native") or {}).items()}
        nat_full = {a: {"window": list(win_full), "ir_pos": bool((v["full"].get("ir") or 0) > 0), "t_ge_1_5": bool((v["full"].get("t") or 0) >= 1.5),
                        "placebo_opposite": bool((v["full"].get("ir") or 0) * (v["full"].get("placebo_ir") or 0) < 0),
                        "saturated": bool(v["full"].get("saturated"))} for a, v in (M.get("native") or {}).items()}
        ref = M.get("eg30_ref") or {}
        s2m = {a: {k: v.get(k) for k in ("n_forms", "n_skipped", "names_min", "names_med", "names_max")} for a, v in (M.get("s2_meta") or {}).items()}
        u_meta = {k: ((M.get("controls") or {}).get("U") or {}).get("meta", {}).get(k) for k in ("names_min", "names_med", "names_max")}
        pv.update({"window_used": win_full, "fallback": bool(M.get("fallback")), "f0a_ok": (M.get("f0a") or {}).get("ok"),
                   "pub": {"window": pub_w, "cells": cells, "controls": ctrl, "diffs": diffs, "ctrl_diffs": cdiffs, "native": nat,
                           "eg30_ref": {"window": ref.get("window") or pub_w, "frozen_eval": ref.get("frozen_eval"), "corr_fund_ex": ref.get("corr_fund_ex")}},
                   "full_bool": {"window": list(win_full), "cells": full_b, "diffs": dfull, "native": nat_full,
                                 "candidates": M.get("candidates"), "candidates_compare": M.get("candidates_compare"),
                                 "predictions": M.get("predictions")},
                   "counts": {"window": list(win_full), "s2": s2m, "u": u_meta},
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
                     {"commit": out.get("prereg_commit"), "registration_error": rl.get("registration_error"), "smoke": out.get("smoke")})
    _write_text(P["public"], json.dumps(pub, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    return {"public": P["public"], "sha256_16": _sha_file(P["public"])[:16]}


# ══════════════════════════════════════════════════════════════════════════
#  결과 문서 렌더러(얼린 · 게시 칸 파일 하나만 읽는다)
# ══════════════════════════════════════════════════════════════════════════
ARM_KO = {"VG": "VG 밸류+성장 27(+사이언 이력 · 주 팔)", "C": "C 옛 겹침 명단 43(+사이언 · 2026-09-27 전 정의)", "C-BW": "C−BW 옛 명단 − 브리지워터"}
SIG_KO = {"S1": "S1 합의 점수 틸트(S&P 500 · TE 2%)", "S2": "S2 K≥2 겹침 바스켓(동일가중)"}
CAND_KO = {"c1_excess_pos_both": "펀드 초과 > 0(144개월 · 10년 둘 다)", "c2_nw_t": "NW t ≥ 2.0(144개월)",
           "c3_style_alpha": "4요인 통제 α > 0 · t ≥ 1.5(144개월)", "c4_years": "온전한 해 70% 이상 승(144개월)",
           "c5_defense": "하락월 평균 초과 ≥ 0(144개월) · 급락 다리 평균 ≥ 0(10년)",
           "c6_control": "대조 넘음 — 팔 − 대조(S1 − B0 · S2 − U) 연 평균 > 0 · NW t ≥ 1.5(144개월) · S1 은 위약 부호 반대도",
           "c7_roll36": "36개월 굴림 승률 ≥ 60%(144개월)",
           "c8_control_style": "대조 차의 4요인 통제 α > 0 · t ≥ 1.5(144개월)",
           "c9_surge": "상승월 평균 초과 ≥ 0(144개월) · 기계적 반등 평균 ≥ 0(10년)", "all": "모두(후속 등록 후보)"}
PRED_KO = {"P1_vg_minus_c_indistinct": "P1 VG − C 는 두 신호 모두 |NW t| < 1.5", "P2_bw_half_of_vg_gap_s2": "P2 S2 에서 |C−BW − C| ≥ ½·|VG − C|",
           "P3_style_alpha_small": "P3 여섯 칸 모두 4요인 α |t| < 1.5", "P4_fund_excess_small": "P4 여섯 칸 모두 펀드 |연 초과| < 0.5%p",
           "P5_s2_not_beyond_u": "P5 S2 − U 의 NW t < 1.5(세 팔)", "P6_no_candidate": "P6 후속 등록 후보 없음"}


def _fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%%.%df" % nd) % v
    return str(v)


def _cell_row(name, c):
    st = c.get("style") or {}
    mech = c.get("mech") or {}
    cl, rb = mech.get("crash_legs") or {}, mech.get("rebounds") or {}
    r36 = c.get("roll36") or {}
    return "| %s | %s | %s | %s | %s | %s | %s/%s | %s · %s%% | %s/%s | %s/%s | %s%% | %s (%s) | %s |" % (
        name, _fmt(c.get("ann_ex")), _fmt(c.get("cagr_ex")), _fmt(c.get("ir")), _fmt(c.get("nw_t")), _fmt(c.get("win"), 1),
        c.get("years_won_full"), c.get("n_full_years"), _fmt(c.get("down_mean"), 3), _fmt(c.get("down_win"), 0),
        cl.get("win"), cl.get("n"), rb.get("win"), rb.get("n"), _fmt(r36.get("hit"), 0), _fmt(st.get("alpha_ann")), _fmt(st.get("alpha_t")),
        _fmt(c.get("sleeve_beta")))


CELL_HEAD = ["| 줄 | 연 초과(%p) | CAGR 차(%p) | IR | NW t | 월 승률(%) | 해마다 승 | 하락월 평균(%p/월) · 승률 | 급락 다리 승 | 반등 승 | 36개월 굴림 승률 | 4요인 α(%p/년) (t) | 슬리브 β |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]


def result_doc(pub):
    """결과 문서 본문(Markdown) — 게시 칸 파일(_gfund.public.json) 하나만 읽는다(손으로 옮기지 않는다)."""
    if not pub or not pub.get("gfund_public_view"):
        raise SystemExit("🚨 게시 칸 파일이 아니다")
    P = pub.get("pub") or {}
    FB = pub.get("full_bool") or {}
    cand = FB.get("candidates") or {}
    any_cand = any((v or {}).get("all") for v in cand.values())
    L = ["# 결과 — 거장 슬리브 측정(GURUFUND · 밸류+성장 27(+ 사이언 이력) · 옛 겹침 명단 43(+ 사이언) · 브리지워터 제외 42(+ 사이언)): 한 번 굽기 · 측정만 · %s"
         % ("후속 등록 후보 있음(채택 없음)" if any_cand else "후속 등록 후보 없음"), "",
         "풀카드: 없음   <!-- 거장 슬리브 측정 — 펀드 후보 찾기(사용자 2026-09-27) · 랩 게시 sid 가 아니다 -->",
         "판정: 측정만   <!-- 확증 가족 없음(m = 0) · 채택 없음 · 명단은 이 결과로 바꾸거나 되돌리지 않는다 -->",
         "규칙: 없음", "",
         "아래는 얼린 렌더러(`python -X utf8 build/g_fund_run.py --result-doc`)가 게시 칸 파일(`_gfund.public.json`) 하나에서 만든 것이다.", "",
         "## 머리", "",
         "- 등록 커밋 `%s` · 산출 sha256 `%s` · 자료 핀 `%s` · F0-b 핀 코드 · 기록 `%s` + 자료 `%s`" % (
             pub.get("prereg_commit"), (pub.get("out_sha256") or "—")[:16], (pub.get("data_pin") or "")[:9], (pub.get("f0b_pin") or "")[:9],
             (pub.get("f0b_data_pin") or "")[:9]),
         "- 멈춤: %s · 등록 오류: %s" % (pub.get("stopped") or "없음", "; ".join(pub.get("registration_error") or []) or "없음"),
         "- 측정 창(보유월): %s · 대체 창 씀: %s · F0-a 패널 관문: %s · 공개 값은 10년 창(2016-09 ~ 2026-08)만 — 144개월 창 값은 저장소 밖 캐시에만(등록 §6)"
         % ("~".join(pub.get("window_used") or []), _fmt(pub.get("fallback")), _fmt(pub.get("f0a_ok"))),
         "- 다중성: 확증 가족 없음(m = %s) · 누적 N %s → %s(센 줄 %s)" % ((pub.get("multiplicity") or {}).get("m_confirmatory"),
                                                                (pub.get("multiplicity") or {}).get("cum_n_before"),
                                                                (pub.get("multiplicity") or {}).get("cum_n_after"),
                                                                (pub.get("multiplicity") or {}).get("rows_counted")),
         "- 전방: %s" % pub.get("forward"), ""]
    fb, f0 = pub.get("f0b") or {}, pub.get("f0") or {}
    L += ["## F0 관문(수익 없음)", "",
          "| 관문 | 값 |", "|---|---|",
          "| F0-b 얼린 GURUCMP 기록 재현(3bbe5ca1d · 잎 %s · 1e-9) | %s |" % (fb.get("n_leaves"), _fmt(fb.get("record_reproduced"))),
          "| F0-b 엔진 C 팔 셈 = GURUCMP 셈 | %s |" % _fmt(fb.get("engine_counts_same")),
          "| F0-b 엔진 S1 행 = GURUCMP 가 idxrev.solve 에 넘긴 행 | %s |" % _fmt(fb.get("engine_rows_same")),
          "| 팔 상수 = refresh_13f 축 규칙 | %s |" % _fmt((f0.get("arms") or {}).get("ok")),
          "| F0-c C 팔 셈 = counts_by_quarter | %s |" % _fmt(f0.get("f0c_ok")),
          "| F0-d 수선 확인(BRK.B · 해리스 · EQIX · KKR) | %s |" % _fmt((f0.get("f0d") or {}).get("ok")),
          "| 창(첫 보유월 %s · 끝 %s · %s개월 · 이어짐) | %s |" % ((f0.get("window") or {}).get("s1_first_hold"), (f0.get("window") or {}).get("s1_last_hold"),
                                                         (f0.get("window") or {}).get("s1_n"), _fmt((f0.get("window") or {}).get("ok"))),
          "| F0-d 옛 CUSIP 수선 확인(C 팔 보유 곳 수 %s) | %s |" % (
              " · ".join("%s %s" % (k, (v or {}).get("holders")) for k, v in (((f0.get("f0d") or {}).get("old_cusip")) or {}).items()) or "—",
              _fmt((f0.get("f0d") or {}).get("old_cusip_ok"))),
          "| F0-f 명단 전원 아무도 안 든 시점정확 멤버(체결월 최대 S&P 500 %s · ∪ %s · 한도 %s · %s · 합 %s) | %s |" % (
              (f0.get("f0f") or {}).get("max_spx"), (f0.get("f0f") or {}).get("max_union"), (f0.get("f0f") or {}).get("limit_spx"),
              (f0.get("f0f") or {}).get("limit_union"), (f0.get("f0f") or {}).get("total_union"), _fmt((f0.get("f0f") or {}).get("ok"))),
          "| 멈춤 조건 앞당김(측정 창 · 대체 창의 S1 행 · S2 첫 체결 · 최소 종목) | %s |" % _fmt((f0.get("stops") or {}).get("ok")), ""]
    fe = f0.get("f0e") or {}
    if fe:
        L += ["| 팔 | 보고 곳(최소~최대) | K≥2 바스켓 종목(최소 · 중앙 · 최대) | 10종목 이상 체결 비율 | F0-e |", "|---|---|---|---|---|"]
        L += ["| %s | %s~%s | %s · %s · %s | %s | %s |" % (ARM_KO.get(a, a), v.get("managers_min"), v.get("managers_max"), v.get("basket_min"),
                                                     v.get("basket_med"), v.get("basket_max"), _fmt(v.get("n_forms_ge10_frac")), _fmt(v.get("ok")))
              for a, v in fe.items()] + [""]
    comp = f0.get("composition") or {}
    if comp:
        L += ["- 구성(수익 없음): C 의 K≥2 가운데 브리지워터가 든 몫 %s · «브리지워터 + 한 곳» 몫 %s · VG 의 K≥2 가운데 «매버릭 또는 베일리 기포드 + 한 곳» 몫 %s" % (
            _fmt(comp.get("c_k2_bw_frac"), 3), _fmt(comp.get("c_k2_bw_plus_one_frac"), 3), _fmt(comp.get("vg_k2_mav_bg_plus_one_frac"), 3)), ""]
    if pub.get("stopped"):
        L += ["## 멈춤", "", "- 굽기가 멈췄다(%s) — 산출은 멈춤 기록이다. 다시 굽기는 새 등록." % pub.get("stopped"), ""]
        return "\n".join(L) + "\n"
    cells, ctrl = P.get("cells") or {}, P.get("controls") or {}
    for s in ("S1", "S2"):
        L += ["## %s — 펀드 틀(0.9 × SPY TR + 0.1 × 슬리브 대 SPY TR · 편도 10bp · 10년 2016-09 ~ 2026-08)" % SIG_KO[s], ""] + CELL_HEAD
        for a in ("VG", "C", "C-BW"):
            if s in (cells.get(a) or {}):
                L.append(_cell_row(ARM_KO[a], cells[a][s]))
        c_ = "B0" if s == "S1" else "U"
        if c_ in ctrl:
            L.append(_cell_row("대조 %s" % ("B0 패널 시총가중 S&P 500" if c_ == "B0" else "U 매핑 유니버스 동일가중"), ctrl[c_]))
        L += [""]
    ep_cols = [(a, s) for a in ("VG", "C") for s in ("S1", "S2") if s in (cells.get(a) or {})]
    ep_names = [(e.get("kind"), e.get("name")) for e in ((cells.get("VG") or {}).get("S1") or {}).get("episodes") or []]
    if ep_names:
        L += ["## 이름 붙은 급락 · 급등 구간(qbatch_core.EPIS · 펀드 초과 %p · 10년)", "",
              "| 구간 | " + " | ".join("%s %s" % (a, s) for a, s in ep_cols) + " |", "|---|" + "---|" * len(ep_cols)]
        for kind, nm in ep_names:
            vals = []
            for a, s in ep_cols:
                hit = [e.get("ex") for e in (cells[a][s].get("episodes") or []) if e.get("name") == nm and e.get("kind") == kind]
                vals.append(_fmt(hit[0]) if hit else "—")
            L.append("| %s · %s | %s |" % (kind, nm, " | ".join(vals)))
        L += [""]
    ref = P.get("eg30_ref") or {}
    fe_ = ref.get("frozen_eval") or {}
    L += ["## 참고 줄 — EG30 V0(얼린 `data/_qbatch.json` · 입력 · 대조 · 구성 요소가 아니다)", "",
          "- 얼린 지표(10년): 연 초과 %s%%p · IR %s · NW t %s · 월 승률 %s%% · 해마다 %s/%s · 하락월 평균 %s · 급락 이김 %s · 급등 이김 %s · 슬리브 β %s" % (
              _fmt(fe_.get("ann_ex")), _fmt(fe_.get("ir")), _fmt(fe_.get("nw_t")), _fmt(fe_.get("win"), 1), fe_.get("years_won"), fe_.get("n_years"),
              _fmt(fe_.get("down_mean"), 3), fe_.get("crash_won"), fe_.get("surge_won"), _fmt(fe_.get("sleeve_beta"))),
          "- 거장 줄 펀드 월 초과와의 상관(10년): %s" % (" · ".join("%s %s" % (k, _fmt(v)) for k, v in (ref.get("corr_fund_ex") or {}).items()) or "—"), ""]
    L += ["## 팔 차이 · 대조 차(10년 · 월 펀드 초과의 차)", "",
          "| 차 | 신호 | 연 평균(%p) | NW t | 월 승률(%) | 하락월 평균(%p) | 해마다 승 | ΔIR | 차의 4요인 α(%p/년) (t) |", "|---|---|---|---|---|---|---|---|---|"]
    for nm, d in (P.get("diffs") or {}).items():
        for s, v in d.items():
            st_ = v.get("style") or {}
            L.append("| %s | %s | %s | %s | %s | %s | %s/%s | %s | %s (%s) |" % ("VG − C" if nm == "VG-C" else "C−BW − C", s, _fmt(v.get("mean_ann"), 3), _fmt(v.get("nw_t")),
                                                                  _fmt(v.get("win"), 1), _fmt(v.get("down_mean"), 3), v.get("years_won_full"), v.get("n_full_years"), _fmt(v.get("d_ir")),
                                                                  _fmt(st_.get("alpha_ann")), _fmt(st_.get("alpha_t"))))
    for a, d in (P.get("ctrl_diffs") or {}).items():
        for s, v in d.items():
            st_ = v.get("style") or {}
            L.append("| %s − %s | %s | %s | %s | %s | %s | %s/%s | %s | %s (%s) |" % (a, "B0" if s == "S1" else "U", s, _fmt(v.get("mean_ann"), 3), _fmt(v.get("nw_t")),
                                                                       _fmt(v.get("win"), 1), _fmt(v.get("down_mean"), 3), v.get("years_won_full"), v.get("n_full_years"), _fmt(v.get("d_ir")),
                                                                       _fmt(st_.get("alpha_ann")), _fmt(st_.get("alpha_t"))))
    L += ["", "## S1 고유 틀(GURUCMP 의 idxrev.ev · 10년 부분 창 · 같은 굽기)", "", "| 팔 | 연 초과(%p) | TE(%) | IR | t | 비용 뒤 IR | 월 승률(%) | 위약 IR |", "|---|---|---|---|---|---|---|---|"]
    for a, v in (P.get("native") or {}).items():
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (ARM_KO.get(a, a), _fmt(v.get("ex")), _fmt(v.get("te")), _fmt(v.get("ir"), 3), _fmt(v.get("t")),
                                                        _fmt(v.get("ir_net"), 3), _fmt(v.get("win"), 1), _fmt(v.get("placebo_ir"), 3)))
    L += ["", "## 144개월 창(%s) — 참/거짓 · 개수만" % "~".join(pub.get("window_used") or []), "",
          "| 줄 | 신호 | 초과 > 0 | NW t ≥ 1.5 | NW t ≥ 2 | 4요인 α > 0 | α t ≥ 1.5 | 하락월 평균 ≥ 0 | 해마다 승 |", "|---|---|---|---|---|---|---|---|---|"]
    for a, sd in (FB.get("cells") or {}).items():
        for s, v in sd.items():
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s/%s |" % (ARM_KO.get(a, a), s, _fmt(v.get("ann_ex_pos")), _fmt(v.get("nw_t_ge_1_5")), _fmt(v.get("nw_t_ge_2")),
                                                                     _fmt(v.get("style_alpha_pos")), _fmt(v.get("style_alpha_t_ge_1_5")), _fmt(v.get("down_mean_ge_0")),
                                                                     v.get("years_won_full"), v.get("n_full_years")))
    dfb = FB.get("diffs") or {}
    L += ["", "## 144개월 창 — 팔 − 대조(참/거짓만)", "", "| 차 | 신호 | 평균 > 0 | NW t ≥ 1.5 | NW t ≥ 2 | 차의 α > 0 | 차의 α t ≥ 1.5 |", "|---|---|---|---|---|---|---|"]
    for nm, d in dfb.items():
        if not nm.startswith("ctrl|"):
            continue
        for s, v in d.items():
            L.append("| %s − %s | %s | %s | %s | %s | %s | %s |" % (nm[5:], "B0" if s == "S1" else "U", s, _fmt(v.get("mean_pos")), _fmt(v.get("nw_t_ge_1_5")),
                                                              _fmt(v.get("nw_t_ge_2")), _fmt(v.get("style_alpha_pos")), _fmt(v.get("style_alpha_t_ge_1_5"))))
    L += ["", "## 후속 등록 후보 규칙(주 팔 VG 칸만 · 계산 전 고정 · 이 등록에서 채택 없음)", "",
          "- c1 ~ c5 · c7 · c9 는 펀드 대 SPY TR 초과 — 패널 가격 기준(편출 종목 일부 가격 수익)과 매핑 생존 편향이 섞인다. c6 · c8 은 같은 편향을 공유하는 대조(S1 − B0 · S2 − U)를 넘어야 한다(등록 §5-2 · §10).", "",
          "| 조건 | S1 | S2 |", "|---|---|---|"]
    for k, ko in CAND_KO.items():
        L.append("| %s | %s | %s |" % (ko, _fmt((cand.get("S1") or {}).get(k)), _fmt((cand.get("S2") or {}).get(k))))
    cc = FB.get("candidates_compare") or {}
    if cc:
        L += ["", "- 비교 팔(같은 규칙 · 서술만 — 명단을 결과로 고르지 않는다): %s" % " · ".join(
            "%s %s %s" % (a, s, _fmt((v or {}).get("all"))) for a, d in cc.items() for s, v in d.items())]
    L += ["", "## 미리 적은 예측(등록 §5)", "", "| 예측 | 맞음 |", "|---|---|"]
    for k, ko in PRED_KO.items():
        L.append("| %s | %s |" % (ko, _fmt((FB.get("predictions") or {}).get(k))))
    L += ["", "## 공개 규칙", "", "- 이 문서는 게시 칸 파일 하나에서 얼린 렌더러가 만들었다 · 144개월 창 값(연 초과 · IR · t · 해마다 값)은 저장소 밖 캐시에만 · 사이트에는 싣지 않는다(MAX_YEARS 10).",
          "- 10년 창 S1 줄은 같은 굽기의 부분 창이다 — λ 는 144개월 창에서 실현 TE 2% 로 풀었으므로 10년 창의 TE 는 2% 가 아니고 GURUCMP(자기 창 풀이)와 일대일로 견주지 않는다(등록 §2).",
          "- 이 결과로 명단(«c» 밸류 + 성장)을 바꾸거나 되돌리지 않는다. 채택은 없다 — 후보 칸이 참이어도 다음 등록의 입구일 뿐이다.",
          "- 굽기 뒤 결과와 무관하게 refresh_13f.NO_OVERLAP 묶음을 풀어 사이트 겹침 백테스트를 «c» 로 다시 굽는다(등록 §5-1)."]
    txt = "\n".join(L) + "\n"
    if CACHE_ONLY_KEY in txt:
        raise SystemExit("🚨 결과 문서에 캐시 표지가 있다")
    return txt


# ══════════════════════════════════════════════════════════════════════════
#  핀 표 · 등록 커밋 직전 점검
# ══════════════════════════════════════════════════════════════════════════
def result_doc_write_problems(pub, P=None):
    """--result-doc --write 문지기 — 연기 판이 아니고 · 두 로컬 표식에 FINISHED <산출 sha> 가 있고 · 캐시 산출 sha 가 게시 칸의 out_sha256 과 같아야 쓴다."""
    P = P or paths()
    bad = []
    if not pub or not pub.get("gfund_public_view"):
        return ["게시 칸 파일이 아니다"]
    if pub.get("smoke"):
        bad.append("연기 판 게시 칸이다")
    sha = pub.get("out_sha256") or ""
    marks = [m for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]
    if len(marks) != 2 or not all(("%s %s" % (FINISHED, sha)) in _read_text(m) for m in marks) or not sha:
        bad.append("두 로컬 표식에 FINISHED <산출 sha> 줄이 없다")
    if not os.path.exists(P["out"]) or _sha_file(P["out"]) != sha:
        bad.append("캐시 산출의 sha256 이 게시 칸 out_sha256 과 다르다")
    return bad


def pins_table():
    rows = []
    for p in FROZEN:
        fp = os.path.join(ROOT, *p.split("/"))
        if not os.path.exists(fp):
            rows.append({"path": p, "blob": None, "sha256_lf": None})
            continue
        rows.append({"path": p, "blob": git_blob_sha(_bytes(fp))[:12], "sha256_lf": _sha_lf(_bytes(fp))[:16]})
    return rows


def precommit():
    pp = os.path.join(ROOT, *PREREG.split("/"))
    txt = _read_text(pp) if os.path.exists(pp) else ""
    n_ph, n_dm = placeholder_counts(txt)
    g = site_guard_std()
    gw, vw = wired_state()
    mb = manifest_check()
    pb = pins_check()
    cb = registered_constants_ok()
    hb = hist_problems()
    missing = [p for p in FROZEN if not os.path.exists(os.path.join(ROOT, *p.split("/")))]
    ready = bool(not name_check() and not n_ph and not n_dm and g["ok"] and gw and vw and not mb and not pb and not cb and not missing
                 and not check_no_forward() and not hb)
    return {"ready": ready, "prereg": PREREG, "prereg_n": _N_PREREG, "name_ok": not name_check(), "placeholders": n_ph, "draft_marks": n_dm,
            "site_guard": g["ok"], "site_guard_bad": g["bad"][:5], "wired_gitignore": gw, "wired_validate_site": vw,
            "manifest_problems": mb, "pins_problems": pb, "registered_constants_bad": cb, "frozen_missing": missing, "hist_overlay_problems": hb,
            "no_forward": not check_no_forward(), "head": _git("rev-parse", "HEAD").stdout.strip()}


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기(러너 경로 전체 · 산출은 열지 않고 지운다 · 참/거짓 · 초만)
# ══════════════════════════════════════════════════════════════════════════
def smoke():
    import contextlib
    cache = cache_guard_std()
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="gfund_runner_smoke_", dir=cache)
    if _inside(tmp, ROOT):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    saved = dict(_OVR)
    res = {"ok": False, "steps": {}, "started": _now()}
    t0 = time.time()
    sink = io.StringIO()
    real_out = os.path.join(cache, "out")
    before = sorted(f for f in os.listdir(real_out) if f.startswith("_gfund")) if os.path.isdir(real_out) else []
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
                                    "stage": ("F0-b" if "F0-b" in msg else "F0" if "F0 실패" in msg else "자식" if "자식 과정" in msg else "기타"),
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
    after = sorted(f for f in os.listdir(real_out) if f.startswith("_gfund")) if os.path.isdir(real_out) else []
    res["real_out_untouched"] = before == after == []
    res["real_gitmark_absent"] = not os.path.exists(_git_mark_path())
    res["sec"] = round(time.time() - t0, 1)
    res["ok"] = bool(res["ok"] and res["deleted_unread"] and res["real_out_untouched"] and res["real_gitmark_absent"])
    _write_text(os.path.join(cache, "meta", "_smoke_gfund_run.json"), json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")
    return res


SMOKE_ALLOWED_KEYS = {"ok", "steps", "started", "files", "tag", "err", "stdout_discarded_unread", "deleted_unread", "real_out_untouched", "real_gitmark_absent", "sec",
                      "bake", "registration_error_empty", "start_tag", "stage", "exists", "nonempty", "second_run_blocked", "finished_marks", "tag_file",
                      "restart_blocked", "not_stopped", "public_safe", "result_doc_rendered", "result_doc_has_cache_marker", "out", "mark", "runlog",
                      "public", "gitmark"}


# ══════════════════════════════════════════════════════════════════════════
#  합성 점검(실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _syn_world(n_days=260, names=("AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG"), seed=7):
    import numpy as np
    rs = np.random.RandomState(seed)
    dates, d = [], 0
    y, m = 2020, 1
    while len(dates) < n_days:
        for dd in range(1, 22):
            dates.append("%04d-%02d-%02d" % (y, m, dd))
            if len(dates) >= n_days:
                break
        m += 1
        if m > 12:
            y, m = y + 1, 1
    PX = {t: 100 * np.cumprod(1 + rs.normal(0.0004, 0.01, len(dates))) for t in names}
    me = {}
    for i, dt_ in enumerate(dates):
        me[dt_[:7]] = i
    return {"dates": dates, "PX": PX, "me": me, "today": set(names)}


def _st_arm_counts():
    """팔 셈 = counts_by_quarter(합성 이력 · NO_OVERLAP 을 바꿔 끼워) · 공시일 · 가격 결측 거르기."""
    import g_fund as E
    import guru_overlap_backtest as GO
    months = ["2020-%02d" % k for k in range(1, 13)]
    P = {"AAA": [1.0] * 12, "BBB": [1.0] * 12, "CCC": [None] * 5 + [1.0] * 7}
    G = {"months": months, "mpx": P,
         "holdings": {"2020-03-31": {"1": {"AAA": 5, "BBB": 1}, "2": {"AAA": 2, "CCC": 3}, "9": {"AAA": 1, "BBB": 1}},
                      "2020-06-30": {"1": {"AAA": 5}, "2": {"BBB": 0, "CCC": 1}, "9": {"CCC": 1}}},
         "filed": {"2020-06-30": {"2": "2020-09-15"}}}
    mi = {m: i for i, m in enumerate(months)}
    old = GO.NO_OVERLAP_S
    try:
        GO.NO_OVERLAP_S = {"9"}
        want, wd = GO.counts_by_quarter(G, mi, P, months)
    finally:
        GO.NO_OVERLAP_S = old
    have, hd = E.arm_counts(G, mi, P, months, frozenset({"1", "2"}))
    ok = have == want and hd == wd
    ok &= have["2020-05"] == {"AAA": 2, "BBB": 1}                # CCC 는 2020-05 가격 없음
    ok &= have["2020-08"] == {"AAA": 1}                          # 2 는 공시가 체결월 말 뒤
    return ok


def _st_attach_z():
    """중립 맞춤 — 매핑 있는 종목의 z 를 벤치 가중 평균 0 · 매핑 없는 종목은 z 없음 · 신호 없는 달은 빈 Z."""
    import g_fund as E
    names = ["A%d" % q for q in range(12)] + ["ZZZ"]
    wb = {t: 1.0 / len(names) for t in names}
    sec = {t: ("S1" if q % 2 else "S2") for q, t in enumerate(names)}
    key = {t: t for t in names}
    rows = [{"m": "2020-06", "sig": "2020-05", "names": names, "wb": wb, "sec": sec, "r": {t: 0.0 for t in names}, "key": key}]
    counts = {"2020-02": {t: (q % 3) for q, t in enumerate(names[:-1])}, "2020-05": {t: (q % 4) for q, t in enumerate(names[:-1])}}
    out = E.attach_z(rows, counts, set(names[:-1]))
    z = out[0]["Z"]["rev"]
    ok = "ZZZ" not in z and abs(sum(wb[t] * z[t] for t in z)) < 1e-12 and "Z" not in rows[0]
    early = E.attach_z([dict(rows[0], sig="2020-01")], counts, set(names[:-1]))
    return bool(ok and early[0]["Z"] == {"rev": {}})


def _st_tilt_weights():
    """tilt_weights 의 달 p · b · cost = idxrev.run(prop · rev) — 합성 행 · λ 배수 둘."""
    import numpy as np
    import g_fund as E
    import idxrev as IR
    rs = np.random.RandomState(3)
    rows = []
    names = ["T%02d" % q for q in range(30)]
    for j in range(14):
        w = rs.uniform(0.2, 2.0, len(names))
        w = w / w.sum()
        rows.append({"m": "2021-%02d" % (j % 12 + 1), "sig": "x", "names": names, "wb": dict(zip(names, w)),
                     "sec": {t: "S%d" % (q % 4) for q, t in enumerate(names)}, "r": dict(zip(names, rs.normal(0, 0.05, len(names)))),
                     "Z": {"rev": {t: float(v) for t, v in zip(names, rs.normal(0, 1, len(names))) if t != "T05"}}})
    ok = True
    for mult in (0.7, 3.0):
        o = IR.run(rows, 2, "rev", "prop", 0.02, False, mult)[0]
        b = E.tilt_weights(rows, 2, 0.02, mult)
        ok &= len(o) == len(b) and max(max(abs(x["p"] - y["p"]), abs(x["b"] - y["b"]), abs(x["cost"] - y["cost"])) for x, y in zip(o, b)) < 1e-12
        ok &= all(abs(sum(x["w"].values()) - 1) < 1e-12 for x in b)
    return bool(ok)


def _st_paths():
    """weights_path 의 달 수익 = (1 − c)·(1 + p) 꼴(체결 날 비용 뒤 값 규약) · basket_path 의 비용 = 10bp × 거래액 · 최소 종목 규칙."""
    import numpy as np
    import g_fund as E
    W = _syn_world()
    ms = sorted(W["me"])
    names = sorted(W["PX"])
    rows, books = [], []
    for j in range(1, len(ms)):
        sig, m = ms[j - 1], ms[j]
        i, i1 = W["me"][sig], W["me"][m]
        r = {t: W["PX"][t][i1] / W["PX"][t][i] - 1 for t in names}
        wv = np.linspace(1, 2, len(names))
        wv = wv / wv.sum()
        rows.append({"m": m, "sig": sig, "names": names, "key": {t: t for t in names}, "r": r})
        books.append({"w": dict(zip(names, wv)), "cost": 0.001 * (j % 3)})
    path = E.weights_path(W, rows, 0, books)
    ok = True
    for j in range(len(rows) - 1):
        i, i1 = W["me"][rows[j]["sig"]], W["me"][rows[j]["m"]]
        p = sum(books[j]["w"][t] * rows[j]["r"][t] for t in names)
        want = (1 + p) * (1 - books[j + 1]["cost"])             # 다음 체결의 비용이 달 끝 값에 들어간다(체결 날 비용 뒤 값)
        ok &= abs(path[i1] / path[i] - want) < 1e-12
    reb = [ms[0], ms[3], ms[6]]
    tg = {ms[0]: names[:5], ms[3]: names[:3], ms[6]: names[2:7]}
    bp = E.basket_path(W, reb, tg, ms[-1], cost=0.001, min_hold=5)
    ok &= bp["skipped"] == [ms[3]] and bp["n_names"] == [5, None, 5]
    i0 = W["me"][ms[0]]
    ok &= abs(bp["path"][i0] - (1 - 0.001)) < 1e-15            # 첫 체결 = 현금 1 → 거래액 1 × 10bp
    try:
        E.basket_path(W, reb, {ms[0]: names[:2]}, ms[-1])
        ok = False
    except RuntimeError:
        pass
    return bool(ok)


def _syn_grid(W, seed=5):
    import numpy as np
    import qbatch_core as QC
    rs = np.random.RandomState(seed)
    g = QC.Grid.__new__(QC.Grid)
    g.dates = list(W["dates"])
    g.di = {d: i for i, d in enumerate(g.dates)}
    g.IX_TR = 100 * np.cumprod(1 + rs.normal(0.0004, 0.01, len(g.dates)))
    g.IX_PR = g.IX_TR * 0.99
    g.me = dict(W["me"])
    g.RF = {}
    return g


def _st_fund_and_metrics():
    """펀드 틀: 슬리브 = 지수면 월 초과 0 · roll36 · 스타일 회귀가 심은 α 를 찾는다 · diff_stats 대칭 · sub_fr 창."""
    import numpy as np
    import g_fund as E
    W = _syn_world(n_days=21 * 60)
    G = _syn_grid(W)
    ms = sorted(W["me"])
    forms = ms[:-1]
    path = {d: G.IX_TR[d] for d in range(W["me"][ms[0]], W["me"][ms[-1]] + 1)}
    fr = E.fund(G, path, forms)
    ok = bool(np.max(np.abs(fr["ex"])) < 1e-10)
    rs = np.random.RandomState(11)
    ex, ix = rs.normal(0.05, 0.3, 60), rs.normal(0.8, 4, 60)
    r = E.roll36(ex, ix)
    ok &= r["n"] == 25 and 0 <= r["hit"] <= 100
    hold = ["%04d-%02d" % (2015 + k // 12, k % 12 + 1) for k in range(60)]
    ffm = {h: {f: float(v) for f, v in zip(E.FF_FACTORS, rs.normal(0, 3, 4))} for h in hold}
    y = np.array([0.1 + 0.05 * ffm[h]["mkt_rf"] - 0.02 * ffm[h]["hml"] for h in hold]) + rs.normal(0, 0.01, 60)
    st = E.style({"hold": hold, "ex": y}, ffm)
    ok &= abs(st["alpha_ann"] - 1.2) < 0.1 and abs(st["b_mkt_rf"] - 0.05) < 0.01 and abs(st["b_hml"] + 0.02) < 0.01
    path2 = {d: v * (1 + 0.0001 * (d % 7)) for d, v in path.items()}
    fr2 = E.fund(G, path2, forms)
    d1, d2 = E.diff_stats(G, fr2, fr), E.diff_stats(G, fr, fr2)
    ok &= abs(d1["mean_ann"] + d2["mean_ann"]) < 1e-12
    sf = E.sub_fr(G, fr2, ms[13])
    ok &= sf["hold"][0] == ms[13] and len(sf["ex"]) == len(sf["hold"]) and sf["days"][0] == W["me"][ms[12]]
    return bool(ok)


def _st_leaf_compare():
    import g_fund as E
    a = {"x": 1.0, "y": [1, 2, {"z": 0.5}], "s": "a", "b": True, "n": None}
    b = {"x": 1.0 + 5e-10, "y": [1, 2, {"z": 0.5}], "s": "a", "b": True, "n": None}
    c = {"x": 1.0 + 2e-9, "y": [1, 2, {"z": 0.5}], "s": "a", "b": True, "n": None}
    d = {"x": 1.0, "y": [1, 2], "s": "a", "b": True, "n": None}
    return bool(not E.leaf_compare(a, b)[0] and E.leaf_compare(a, c)[0] == ["/x"] and E.leaf_compare(a, d)[0] and E.leaf_compare(a, dict(a, b=1))[0])


def _st_candidate():
    """후속 등록 후보 규칙 — 아홉 조건이 모두 참일 때만 all · 하나라도 거짓이면 all 거짓 · 대조(c6 · c8)는 두 신호 모두 팔 − 대조를 넘어야 ·
    S1 은 위약 부호도 · c9 는 상승월 · 기계적 반등."""
    import g_fund as E
    full = {"ann_ex": 0.3, "nw_t": 2.2, "style": {"alpha_ann": 0.2, "alpha_t": 1.8}, "years_won_full": 8, "n_full_years": 11, "down_mean": 0.01,
            "up_mean": 0.02, "roll36": {"hit": 70.0}}
    pub = {"ann_ex": 0.2, "mech": {"crash_legs": {"mean": 0.1}, "rebounds": {"mean": 0.1}}}
    ctrl = {"mean_ann": 0.1, "nw_t": 1.6, "style": {"alpha_ann": 0.1, "alpha_t": 1.6}}
    c = E.candidate(full, pub, {"placebo_ir": -0.3}, ctrl, "S2")
    ok = c["all"] is True and set(c) == set(CAND_KO)
    for k, v in (("nw_t", 1.9), ("years_won_full", 7), ("down_mean", -0.01), ("up_mean", -0.01)):
        ok &= E.candidate(dict(full, **{k: v}), pub, {"placebo_ir": -0.3}, ctrl, "S2")["all"] is False
    ok &= E.candidate(full, dict(pub, mech={"crash_legs": {"mean": 0.1}, "rebounds": {"mean": -0.1}}), {}, ctrl, "S2")["c9_surge"] is False
    for cc in (dict(ctrl, mean_ann=-0.1), dict(ctrl, nw_t=1.4), dict(ctrl, style={"alpha_ann": 0.1, "alpha_t": 1.4}), dict(ctrl, style={"alpha_ann": -0.1, "alpha_t": 1.6})):
        for sig in ("S1", "S2"):
            ok &= E.candidate(full, pub, {"placebo_ir": -0.3}, cc, sig)["all"] is False
    ok &= E.candidate(full, pub, {"placebo_ir": 0.3}, ctrl, "S1")["c6_control"] is False
    ok &= E.candidate(full, pub, {"placebo_ir": -0.3}, ctrl, "S1")["all"] is True
    ok &= E.candidate(full, pub, {"placebo_ir": 0.3}, ctrl, "S2")["c6_control"] is True       # S2 는 위약을 보지 않는다
    ok &= E.candidate(dict(full, n_full_years=9, years_won_full=7), pub, {}, ctrl, "S2")["c4_years"] is True
    ok &= E.candidate(dict(full, n_full_years=9, years_won_full=6), pub, {}, ctrl, "S2")["c4_years"] is False
    return bool(ok)


def _fake_out():
    """게시 칸 누수 시험용 합성 산출 — 144개월 칸에 표지 수 0.123456 을 심는다(게시 칸 · 결과 문서에 나오면 샌 것)."""
    mk = 0.123456
    m_full = {"n": 144, "ann_ex": mk, "nw_t": mk, "ir": mk, "win": mk, "years": {"2015": mk}, "years_won_full": 5, "n_full_years": 11,
              "down_mean": mk, "style": {"alpha_ann": mk, "alpha_t": mk}, "roll36": {"hit": mk}, "mech": {"crash_legs": {"n": 8, "mean": mk, "win": 3}},
              "window": ["2014-09", "2026-08"]}
    m_pub = {"n": 120, "ann_ex": 0.5555, "cagr_ex": 0.5555, "ir": 0.5555, "nw_t": 0.5555, "win": 55.55, "years": {"2017": 0.5555},
             "years_won_full": 5, "n_full_years": 9, "down_mean": 0.5555, "down_win": 55.5, "style": {"alpha_ann": 0.5555, "alpha_t": 0.5555},
             "roll36": {"hit": 55.5}, "mech": {"crash_legs": {"n": 8, "mean": 0.5555, "win": 3}, "rebounds": {"n": 8, "mean": 0.5555, "win": 4}},
             "sleeve_beta": 1.1, "window": ["2016-09", "2026-08"]}
    d_full = {"mean_ann": mk, "nw_t": mk, "window": ["2014-09", "2026-08"], "style": {"alpha_ann": mk, "alpha_t": mk, "n": 143}}
    d_pub = {"mean_ann": 0.5555, "nw_t": 0.5555, "win": 50.0, "window": ["2016-09", "2026-08"], "style": {"alpha_ann": 0.5555, "alpha_t": 0.5555, "n": 119}}
    cells = {a: {s: {"full": dict(m_full), "pub": dict(m_pub)} for s in ("S1", "S2")} for a in ("VG", "C", "C-BW")}
    cand = {k: False for k in CAND_KO}
    main = {"window_used": ["2014-09", "2026-08"], "fallback": False, "f0a": {"ok": True, "corr": mk, "gap_pm": mk, "window": ["2014-09", "2026-08"]},
            "cells": cells, "controls": {"B0": {"full": dict(m_full), "pub": dict(m_pub)}, "U": {"full": dict(m_full), "pub": dict(m_pub), "meta": {"names_min": 300}}},
            "diffs": {"VG-C": {s: {"full": d_full, "pub": d_pub} for s in ("S1", "S2")}, "C-BW-C": {s: {"full": d_full, "pub": d_pub} for s in ("S1", "S2")}},
            "ctrl_diffs": {a: {s: {"full": d_full, "pub": d_pub} for s in ("S1", "S2")} for a in ("VG", "C", "C-BW")},
            "native": {a: {"full": {"ir": mk, "t": mk, "placebo_ir": -mk, "saturated": False, "window": ["2014-09", "2026-08"]},
                           "pub": {"ex": 0.5555, "ir": 0.5555, "placebo_ir": -0.5555, "window": ["2016-09", "2026-08"]}} for a in ("VG", "C", "C-BW")},
            "candidates": {"S1": dict(cand), "S2": dict(cand)}, "candidates_compare": {"C": {"S1": dict(cand)}},
            "predictions": {k: True for k in PRED_KO}, "s2_meta": {"VG": {"n_forms": 48, "n_skipped": 0, "names_min": 100, "names_med": 150, "names_max": 200, "turn": mk}},
            "eg30_ref": {"window": ["2016-09", "2026-08"], "frozen_eval": {"ann_ex": 0.5555}, "corr_fund_ex": {"VG|S1": 0.5555}},
            "multiplicity": {"m_confirmatory": 0, "cum_n_before": 968, "rows_counted": 8, "cum_n_after": 976},
            "series": {"VG|S1": {"hold": ["2014-09"], "ex": [mk] * 144}}}
    f0 = {"ok": True, "arms": {"ok": True, "n_current": {"VG": 27}, "n_history": {"VG": 28}}, "f0c": {"ok": True},
          "f0d": {"ok": True, "brkb_holders_2026_08": 12}, "window": {"ok": True, "s1_first_hold": "2014-09", "s1_n": 144},
          "panel": {"coverage_min": 0.97}, "f0e": {"VG": {"managers_min": 20, "n_forms_ge10_frac": 1.0, "ok": True}},
          "composition": {"c_k2_bw_frac": 0.8},
          "f0f": {"n_forms": 48, "max_spx": 3, "max_union": 4, "total_union": 41, "total_spx": 30, "limit_spx": 3, "limit_union": 5,
                  "worst_union": {"n": 4, "form": "2020-05", "keys": ["ASML", "CARR", "OTIS", "WYNN"]}, "worst_spx": {"n": 3, "form": "2020-05", "keys": ["CARR"]}, "ok": True},
          "stops": {"win": {"window": ["2014-09", "2026-08"], "s1_rows_ok": True, "first_form_names": {"VG": 60, "U": 450}}, "ok": True}}
    return {CACHE_ONLY_KEY: True, "prereg": PREREG, "prereg_commit": "SMOKE", "f0b": {"ok": True, "n_leaves": 500}, "f0": f0, "main": main,
            "data_pin": DATA_PIN, "f0b_pin": F0B_CODE_PIN, "f0b_data_pin": F0B_DATA_PIN}


def _st_public_leak():
    """게시 칸 · 결과 문서에 144개월 표지 수(0.123456)가 없고 · 10년 값(0.5555)은 있다 · 심은 누수는 public_safe_std 가 잡는다."""
    out = _fake_out()
    pub = public_doc(out, "0" * 64, 1, {"commit": "SMOKE"})
    blob = json.dumps(pub, ensure_ascii=False)
    txt = result_doc(pub)
    ok = "0.123456" not in blob and "0.12" not in txt and "0.5555" in blob and "0.56" in txt and CACHE_ONLY_KEY not in blob
    bad = dict(pub)
    bad["full_bool"] = dict(pub["full_bool"], leak=0.123456)
    ok &= bool(public_safe_std(bad))
    ok &= bool(public_safe_std({"x": {"window": ["2014-09", "2026-08"], "v": 0.5}})) and not public_safe_std({"x": {"window": ["2014-09", "2026-08"], "n": 144}})
    ok &= bool(public_safe_std({"s": [0.1, 0.2, 0.3, 0.4, 0.5]}))
    ok &= "풀카드:" in txt and "판정:" in txt and "규칙:" in txt and re.search(r"커밋\s*`SMOKE`", txt) is not None
    return bool(ok)


def _st_nobody_gate():
    """F0-f — 명단 전원 아무도 안 든 시점정확 멤버 수: 든 종목 · 분기말 뒤 상장(첫 가격 > 13F 분기말) · 가격 키가 오늘 유니버스 밖인 종목은 세지 않는다 ·
    S&P 500 과 합집합을 따로 센다 · 한도를 넘으면 ok 거짓."""
    import numpy as np
    import g_fund as E
    dates, me = [], {}
    for mo in range(1, 7):
        for dd in range(1, 22):
            dates.append("2020-%02d-%02d" % (mo, dd))
        me["2020-%02d" % mo] = len(dates) - 1
    n = len(dates)
    full = np.ones(n)
    late = np.full(n, np.nan)
    late[me["2020-03"] + 5:] = 1.0                         # 2020-04 첫 가격 — 2020-03-31 13F 에 있을 수 없다
    W = {"dates": dates, "me": me, "PX": {"AAA": full, "BBB": full, "CCC": late, "DDD": full, "EEE": full},
         "today": {"AAA", "BBB", "CCC", "DDD"}, "lists": {"spx": {"2020-05": ["AAA", "BBB", "CCC", "EEE"]}, "ndx": {"2020-05": ["DDD"]}},
         "cikmap": {}, "splice": {}, "reassigned": {}}
    months = ["2020-%02d" % mo for mo in range(1, 7)]
    G = {"months": months, "mpx": {t: [1.0] * 6 for t in ("AAA", "BBB", "CCC", "DDD", "EEE")},
         "holdings": {"2020-03-31": {"1": {"AAA": 5.0}, "9": {"AAA": 1.0, "BBB": 0.0}}}, "filed": {}}
    mi = {m: i for i, m in enumerate(months)}
    r1 = E.nobody_gate(W, G, months, G["mpx"], mi, ["2020-05"], max_spx=1, max_union=1)
    r2 = E.nobody_gate(W, G, months, G["mpx"], mi, ["2020-05"], max_spx=1, max_union=2)
    return bool(r1["max_spx"] == 1 and r1["max_union"] == 2 and r1["ok"] is False and r2["ok"] is True
                and r1["worst_union"]["keys"] == ["BBB", "DDD"] and r1["worst_spx"]["keys"] == ["BBB"])


def _st_stop_record():
    """등록된 멈춤(StopBake)은 굽기 자식이 {"stopped": 사유} 로 돌려주고 · 게시 칸 · 결과 문서가 «멈춤» 으로 그린다 · basket_path 의 첫 체결 부족은 StopBake."""
    import numpy as np
    import g_fund as E
    real = E._main_body

    def boom():
        raise E.StopBake("첫 체결 2014-08 의 종목이 3 개(최소 5)")
    try:
        E._main_body = boom
        r = E.main_child()
    finally:
        E._main_body = real
    ok = r.get("stopped", "").startswith("첫 체결")
    out = _fake_out()
    out["main"] = r
    pub = public_doc(out, "0" * 64, 1, {"commit": "SMOKE"})
    txt = result_doc(pub)
    ok &= pub.get("stopped") == r["stopped"] and "## 멈춤" in txt and "0.5555" not in json.dumps(pub)
    W = _syn_world()
    ms = sorted(W["me"])
    try:
        E.basket_path(W, [ms[0], ms[3]], {ms[0]: ["AAA", "BBB"]}, ms[-1])
        ok = False
    except E.StopBake:
        pass
    return bool(ok)


def _st_result_write_guard():
    """--result-doc --write 문지기 — 연기 판 · FINISHED 없음 · 산출 sha 불일치면 거절 · 셋 다 맞으면 통과."""
    tmp = tempfile.mkdtemp(prefix="gfund_st_")
    try:
        P = {"out": os.path.join(tmp, "_gfund.json"), "mark": os.path.join(tmp, "_gfund.started"), "gitmark": os.path.join(tmp, "gm")}
        with open(P["out"], "wb") as f:
            f.write(b'{"x": 1}\n')
        sha = _sha_file(P["out"])
        for m in (P["mark"], P["gitmark"]):
            _write_text(m, "C · t\n%s %s t\n" % (FINISHED, sha))
        pub = {"gfund_public_view": True, "smoke": False, "out_sha256": sha}
        ok = not result_doc_write_problems(pub, P)
        ok &= bool(result_doc_write_problems(dict(pub, smoke=True), P))
        ok &= bool(result_doc_write_problems(dict(pub, out_sha256="0" * 64), P))
        _write_text(P["gitmark"], "C · t\n")
        ok &= bool(result_doc_write_problems(pub, P))
        return bool(ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _st_scrub():
    """오류 꼬리 지우기 — 소수 · 지수꼴(1e-05 · 2.5E+03 · .5)은 <num> · 날짜 · 정수 · File 줄은 그대로."""
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
    """GFUND_COMMIT 없이 · 모르는 커밋으로는 판 점검이 멈춘다(아무것도 쓰지 않는다)."""
    ok = True
    for env in ({}, {"GFUND_COMMIT": "0" * 40, "_GFUND_NO_FETCH": "1"}):
        try:
            frozen_check(env)
            ok = False
        except SystemExit:
            pass
    return ok


def _st_registered():
    import g_fund as E
    return not registered_constants_ok(E)


def _st_arms_consistent():
    """팔 상수 = 작업 트리 refresh_13f 의 축 규칙(VG 27 + 사이언 · C 43 + 사이언 · C−BW 42 + 사이언)."""
    import g_fund as E
    r = E._arms_check()
    return bool(r["ok"] and r["n_current"] == {"VG": 27, "C": 43, "C-BW": 42} and r["n_history"] == {"VG": 28, "C": 44, "C-BW": 43})


def _st_wire():
    g0, v0 = "a\n", 'x = 1\nprint("사이트 검증:", 1)\n'
    g1, v1 = wire_texts(g0, v0)
    g2, v2 = wire_texts(g1, v1)
    return bool(g1 == g2 and v1 == v2 and "_gfund*" in g1 and v1.index("거장 슬리브 측정") < v1.index('print("사이트 검증:"'))


def _st_names():
    want = ["data/_gfund.json", "data/_gf_other.json", "data/_gffwd/genesis.json", "x/gfund_cache/a"]
    ok = all(scan_repo_names([f]) for f in want)
    return bool(ok and not scan_repo_names([MANIFEST_FILE, "data/guru.json", "data/guru_history.json", "build/g_fund_run.py"]))


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
    """러너 · 엔진 모듈 머리의 import 가 표준 라이브러리뿐(validate_site · 3bbe5ca1d 뿌리에서 불러도 죽지 않게)."""
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
    import g_fund as E
    src = _read_text(os.path.join(ROOT, *ENGINE.split("/")))
    return bool(not any(hasattr(E, n) for n in FORBIDDEN_ENGINE_NAMES) and "_gffwd" not in src and not check_no_forward())


def _st_git_blob():
    return git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391" and git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


SELFTESTS = (_st_arm_counts, _st_attach_z, _st_tilt_weights, _st_paths, _st_fund_and_metrics, _st_leaf_compare, _st_candidate, _st_public_leak,
             _st_nobody_gate, _st_stop_record, _st_result_write_guard, _st_scrub,
             _st_start_guard, _st_frozen_refuses, _st_registered, _st_arms_consistent, _st_wire, _st_names, _st_manifest_hashes_only,
             _st_open_encoding, _st_std_head, _st_smoke_no_sizes, _st_no_forward, _st_git_blob)


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
        rest = [a for a in argv[argv.index("--result-doc") + 1:] if not a.startswith("--")]
        p = rest[0] if rest else paths()["public"]
        pub = _read_json(p)
        txt = result_doc(pub)
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
