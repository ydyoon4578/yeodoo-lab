# -*- coding: utf-8 -*-
"""build/x_data.py — 배치 X 자료 층: 원천 판(SHA-256) · 가용 늦춤 표 · VXV 공표일 · 20년 창 단언 · 선견 점검 틀 · cache_guard.

설계 원본(구속): 설계 워크플로 산출 xbatch_research.json(저장소 밖 스크래치) — data_plan · build_plan(x_data) · evaluation.rule_20y_compliance ·
  signals[].data · decisions SN-1.1 ~ SN-1.5 · D-5 · D-8. 이 파일은 설계를 다시 짓지 않는다. 옮기는 것은 자료 입구와 그 규칙뿐이다.
  국외(I 층) 원천(국가 ETF · H.10 FX · OECD 금리)은 build/x_intl.py 가 받는다(캐시 raw/intl/) — 여기는 미국 시장 · 측정 팔 입력 · French 만.

🚨 사용자 규칙(2026-09-27) — 백테스트 · 평가 창은 최근 20년까지: 채점 보유월 2006-09 ~ 2026-08(240) · 입력은 2005-08-01 부터(워밍업 · 추정 전용 ·
   채점 안 함) · 1926+ · 1963+ · 1994+ 층 없음. 모든 로더는 기본으로 [2005-08-01, 굽기 끝 T+1] 로 잘라서 돌려준다(assert_input_floor 가 다시 본다).
   공개 사이트는 10년(MAX_YEARS 10) · 20년 수치는 캐시(%TEMP%/xbatch_cache/out)에만 — 저장소 파일에는 쓰지 않는다(쓰기 가드 · public_safe · site_guard).

🚨 랩 규율 — 등록 커밋 전에는 실자료로 수익 · 초과수익 · 타이밍 통계 · 관문 값을 하나도 계산해서 찍지 않는다.
   --selftest 는 합성 자료만 · --smoke 는 받기 · 모양(행 수 · 처음/끝 날짜 · 빈 칸 수 · 참/거짓 · 시간)만 · 선견 점검은 결정 해시가 같은지(참/거짓)만.
   자료 충실도 대조(SPY TR 대 ^SP500TR · DGS3MO 대 rf_monthly · VIX3M Cboe 대 yfinance · BAA10Y = DBAA − DGS10 · ALFRED 판)는 **허용오차 안 개수**만 돌려준다.

🚨 읽지 않는 것: tbatch_cache/out(특히 _tbatch.json — T01 C:bearonly 오염은 공개만 하고 쓰지 않는다) · EG30 산출(_qbatch · _qfwd · _eg_q5 …)은 신호 층에 없다.
   tbatch_cache · vbatch_cache · ubatch_cache 는 raw/ 원자료 사본만 SHA 로 들인다(읽기 전용 · 원 캐시는 고치지 않는다).

얼린 함수: French 파서는 build/v_data.parse_french_blob 를 **부르기만** 한다(깃 blob 단언 V_DATA_BLOB — 바뀌면 멈춘다).

  python build/x_data.py --selftest        합성 자료 시험(망 · 캐시 · 실자료를 읽지 않는다)
  python build/x_data.py --pin             원천 고정(캐시에 있으면 그대로 · 없으면 raw 사본 → 받기) · ALFRED 판 · 요약(모양만)
  python build/x_data.py --manifest        data/_xb_manifest.json(원천 URL · 받은 때 · SHA-256 · 행 수 · 처음/끝 · 규칙 — 값 계열 없음)
  python build/x_data.py --check           고정본 SHA == 명세(굽기 전 관문 — 틀리면 1)
  python build/x_data.py --smoke           받기/모양 연기 시험(통계 없음 · 개수 · 날짜 · 참/거짓 · 시간)
  python build/x_data.py --site            저장소 쪽 경계 점검(site_guard · 표준 라이브러리 쪽만)
"""
from __future__ import annotations

import csv
import datetime as _dt
import fnmatch
import hashlib
import inspect
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
import traceback
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
MANIFEST = os.path.join(DATA, "_xb_manifest.json")
TMP = tempfile.gettempdir()
CACHE = os.environ.get("XBATCH_CACHE") or os.path.join(TMP, "xbatch_cache")
SEED_T = os.path.join(TMP, "tbatch_cache", "raw")          # 읽기 전용 원자료 사본(raw 만 · out 금지)
SEED_T_META = os.path.join(TMP, "tbatch_cache", "meta")
SEED_V = os.path.join(TMP, "vbatch_cache", "raw")
SEED_V_META = os.path.join(TMP, "vbatch_cache", "meta")
SEED_U = os.path.join(TMP, "ubatch_cache", "raw")

# ══════════════════════════════════════════════════════════════════════════
#  창(사용자 20년 규칙 · evaluation.rule_20y_compliance) — 등록 상수
# ══════════════════════════════════════════════════════════════════════════
SCORE_FIRST, SCORE_LAST = "2006-09", "2026-08"              # 채점 보유월(M · I · G · 쌍둥이 · 측정 팔)
N_SCORE = 240
INPUT_MIN = "2005-08-01"                                    # 입력 최소 날짜(워밍업 · 추정 전용)
INPUT_MIN_MONTH = "2005-08"
WARMUP = ("2005-09", "2006-08")                             # BEAR 12개월 워밍업(채점 안 함)
HALVES = (("2006-09", "2016-08"), ("2016-09", "2026-08"))   # M-C4 두 10년 반쪽
OUT_OF_LIT = ("2019-01", "2026-08")                         # 문헌 밖 구간(M-C4 · I-C3 · 92개월)
GFC_EXCL = ("2007-10", "2009-06")                           # 보고만(GFC 제외 창)
FULL_YEARS = (2007, 2025)                                   # G-C3 온전한 해 19
S_WIN = ("2016-09", "2026-08")                              # S 층(EG30 V0 10년)
S_PIT_FROM = "2014-06"                                      # S 층 PIT 워밍업(20년 안)
PUBLIC_FROM = "2016-09"                                     # 공개(저장소 결과 문서 반쪽 수치 · 사이트 MAX_YEARS 10)
MAX_YEARS_PUBLIC = 10
MIN_WARMUP_BY_ELEMENT = {                                   # 러너 단언용 — 첫 결정(활성) 달의 하한(명세 signals · rule_20y_compliance)
    "X-BEAR": "2006-08", "X-GVTREND": "2006-12", "X-BLR": "2010-08", "X-JM": "2008-08",
}
VXV_PUB_DEFAULT = "2009-09-18"                              # SN-1.1 · D-5: Cboe 공식 VIX3M CSV 시작일 — 1차 공고로 더 이른 날을 증명할 때만 앞당긴다
SEED = 20260927
LOOKAHEAD_N = 200
MIN_FIRMS = 20
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
UA_PY = "Python-urllib/3.12"
HOST_GAP = 1.1                                              # 호스트마다 ≥ 1.1초 간격(≤ 1 요청/초)
V_DATA_BLOB = "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a"    # build/v_data.py 깃 blob(부르기만 · French 파서) — c6a35ff01 · e19341a7 에서 같다
CRSP_WANT = "202608"                                        # French 한 판(배치 U · V 와 같다) — 섞이면 멈춘다
ALFRED_VINTAGES = ("2010-01-04", "2016-09-01", "2021-01-04", "2026-09-25")   # SN-1.3: 세 날짜 이상 판 해시 대조
ALFRED_SERIES = ("DBAA", "DGS10", "BAA10Y")
EG_FILE_MARKS = ("_eg_q5", "_eg30plus", "_qfwd", "_eg_best", "_idxeg", "_qbatch", "_qg_", "v0_pin", "_fund_card")   # 신호 층 금지(EG30 입력)
FORBIDDEN_READ_MARKS = ("tbatch_cache/out", "_tbatch.json", "_tbatch.public", "_tbatch.run", "_tbatch.child")      # T01 C:bearonly 저장값 — 열지 않는다


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def sha256_file_lf(p):
    """줄 끝을 LF 로 맞춘 SHA-256 — 추적된 랩 텍스트 자료(JSON)는 새 사본에서 CRLF 로 꺼내질 수 있다(v_data 와 같은 규칙)."""
    with open(p, "rb") as f:
        return sha256_bytes(f.read().replace(b"\r\n", b"\n"))


# ══════════════════════════════════════════════════════════════════════════
#  cache_guard · 쓰기/읽기 가드 · 공개 안전 점검(20년 수치는 캐시 밖으로 나가지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _norm(p):
    return os.path.normcase(os.path.abspath(os.fspath(p)))


def _inside(p, root):
    a, r = _norm(p), _norm(root)
    return a == r or a.startswith(r + os.sep)


def cache_guard(cache=None, root=None):
    """캐시가 저장소 안이면 멈춘다 — 라이선스 원자료 · 20년 수치는 저장소 밖(%TEMP%/xbatch_cache)에만."""
    c, r = cache or CACHE, root or ROOT
    if _inside(c, r) or _inside(r, c):
        raise SystemExit("🚨 캐시(%s)가 저장소(%s) 안이다 — 원자료 · 20년 수치는 저장소 밖에만 둔다." % (c, r))
    return os.path.abspath(c)


CACHE_ONLY_KEY = "__xb_cache_only__"                        # 20년 산출 표지 — 이 키가 든 문서는 저장소에 쓰지 못한다
REPO_ALLOWED = ("data/_xb_manifest.json", "data/_xb_f0.json")   # 저장소에 쓰는 공개 안전 파일(더할 때 여기에) · 전방 창세 파일은 없다(사용자 갱신 2026-09-27 · 검토 반영)
REPO_ALLOWED_GLOBS = ("build/PREREG-*-XBATCH.md", "build/PREREG-*-XBATCH-RESULT.md")         # 등록 · 결과 문서(md 는 repo_write_text 가 표지를 본다)
# 20년 창(2016-09 앞 시작) 안에서 허용하는 실수 칸 — 자료 커버리지 몫 · 문턱 · 허용오차 · 초뿐(검토 반영 2026-09-27: 사용자 규칙 «20년 수치는 캐시에만» —
#   켜짐 비율 · 상태 일치율 · 충실도 corr 같은 20년 창 통계도 저장소에 싣지 않는다 · 값은 캐시 F0 전체판 · 굽기 산출에만)
PUBLIC_FLOAT_KEYS = re.compile(r"(^|_)(coverage|frac|tol|min|max|thr|sec)(_|$)")
COUNT_KEYS = re.compile(r"(^n$|^n_|_n$|count|^k$|switch|months?$|days?$|legs?$|episodes?$|years?$|^rows$|bytes$)")


def mark_cache_only(doc):
    """20년 산출(M · I · G 층 값 · 앞 10년 값)에 표지를 단다 — 이 문서는 캐시에만."""
    doc = dict(doc)
    doc[CACHE_ONLY_KEY] = True
    return doc


def value_lists(doc, path="", max_len=4):
    """값 계열 같은 숫자 목록(숫자 다섯 개 넘는 목록) 경로 — v_guard.value_lists 와 같은 문턱."""
    out = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            out += value_lists(v, path + "/" + str(k), max_len)
    elif isinstance(doc, (list, tuple)):
        nums = [x for x in doc if isinstance(x, (int, float)) and not isinstance(x, bool)]
        if len(nums) > max_len:
            out.append(path or "/")
        for x in doc:
            out += value_lists(x, path + "[]", max_len)
    return out


def _win_start(d):
    for k in ("window", "win", "span"):
        w = d.get(k)
        if isinstance(w, (list, tuple)) and w and isinstance(w[0], str):
            return w[0][:7]
        if isinstance(w, str) and re.match(r"\d{4}-\d{2}", w):
            return w[:7]
    return None


def public_safe(doc, path="", inherited=None):
    """저장소에 실어도 되는 문서인가 — 문제 목록(비면 안전).
      (가) 20년 표지(CACHE_ONLY_KEY)가 어디에도 없다 (나) 값 계열(숫자 다섯 개 넘는 목록)이 없다
      (다) 창(window · win · span)이 PUBLIC_FROM(2016-09) 앞에서 시작하는 절 안에는 실수(float) 값이 없다 —
           개수(int) · 참/거짓 · 문자열 · 커버리지 몫 · 문턱 · 허용오차 · 초(PUBLIC_FLOAT_KEYS)만 허용(명세 public_repo_rule · 사용자 20년 규칙 —
           켜짐 비율 · 일치율 · corr 같은 20년 창 통계는 2016-09 이후 창에서만)."""
    bad = []
    if isinstance(doc, dict):
        if doc.get(CACHE_ONLY_KEY):
            bad.append("%s: 20년 표지(%s)" % (path or "/", CACHE_ONLY_KEY))
        ws = _win_start(doc)
        here = inherited
        if ws is not None:
            here = ws
        for k, v in doc.items():
            p = path + "/" + str(k)
            if isinstance(v, float) and not isinstance(v, bool) and here is not None and here < PUBLIC_FROM:
                if not (PUBLIC_FLOAT_KEYS.search(str(k)) or (math.isfinite(v) and v == int(v) and COUNT_KEYS.search(str(k)))):
                    bad.append("%s: 창 %s(2016-09 앞 시작) 안의 실수 값" % (p, here))
            elif isinstance(v, (dict, list, tuple)):
                bad += public_safe(v, p, here)
    elif isinstance(doc, (list, tuple)):
        for x in doc:
            if isinstance(x, (dict, list, tuple)):
                bad += public_safe(x, path + "[]", inherited)
            elif isinstance(x, float) and inherited is not None and inherited < PUBLIC_FROM:
                bad.append("%s[]: 창 %s 안의 실수 값" % (path, inherited))
    if path == "":
        bad += ["%s: 값 계열 같은 숫자 목록" % p for p in value_lists(doc)]
    return bad


def _rel(p, root=None):
    try:
        return os.path.relpath(os.path.abspath(p), os.path.abspath(root or ROOT)).replace("\\", "/")
    except ValueError:                                        # 다른 드라이브 — 저장소 밖
        return "../" + os.path.basename(p)


def repo_path_allowed(p, root=None):
    rel = _rel(p, root)
    if rel.startswith(".."):
        return True                                           # 저장소 밖 — 이 점검의 대상 아님
    if "__pycache__" in rel.split("/"):
        return True                                           # 파이썬 바이트코드(가져오기 기계)
    base = rel[:-5] if rel.endswith(".part") else rel
    return base in REPO_ALLOWED or any(fnmatch.fnmatch(base, g) for g in REPO_ALLOWED_GLOBS)


def repo_write_json(rel, doc, root=None):
    """저장소 파일 쓰기(허용 목록 · 공개 안전 점검 통과만). 20년 수치는 여기로 못 나간다."""
    root = root or ROOT
    p = os.path.join(root, *rel.split("/"))
    if not repo_path_allowed(p, root):
        raise PermissionError("🚨 저장소 쓰기 허용 목록 밖: %s" % rel)
    bad = public_safe(doc)
    if bad:
        raise PermissionError("🚨 공개 안전 점검 실패(%s): %s" % (rel, "; ".join(bad[:5])))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    txt = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    if CACHE_ONLY_KEY in txt:
        raise PermissionError("🚨 %s 에 20년 표지 문자열이 있다" % rel)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    os.replace(p + ".part", p)
    return p


def repo_write_text(rel, text, root=None):
    """저장소 md 쓰기 — 20년 표지 문자열(CACHE_ONLY_KEY)이 들어 있으면 멈춘다(러너는 20년 수치를 이 표지로 감싼다)."""
    root = root or ROOT
    p = os.path.join(root, *rel.split("/"))
    if not repo_path_allowed(p, root):
        raise PermissionError("🚨 저장소 쓰기 허용 목록 밖: %s" % rel)
    if CACHE_ONLY_KEY in text:
        raise PermissionError("🚨 %s 에 20년 표지가 있다 — 20년 수치는 캐시에만" % rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(p + ".part", p)
    return p


def cache_out(name):
    d = os.path.join(cache_guard(), "out")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def write_cache_json(name, doc):
    """20년 산출은 캐시 out/ 에만(표지를 단다)."""
    p = cache_out(name)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(mark_cache_only(doc), ensure_ascii=False, indent=1, default=str) + "\n")
    os.replace(p + ".part", p)
    return p


# 감사 고리(sys.addaudithook — 지울 수 없어 한 번만 걸고 설정으로 켠다)
_GUARD = {"write_on": False, "write_root": None, "read_on": False, "read_marks": (), "opened": [], "hook": False}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def _is_write(mode, flags):
    if isinstance(mode, str):
        return any(c in mode for c in "wax+")
    if isinstance(flags, int):
        return bool(flags & _WRITE_FLAGS)
    return False


def _hook(ev, args):
    G = _GUARD
    if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        try:
            p = os.fsdecode(args[0])
        except Exception:
            return
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else None
        if G["read_on"]:
            if len(G["opened"]) < 200000:
                G["opened"].append(p)
            pl = p.replace("\\", "/").lower()
            for mk in G["read_marks"]:
                if mk.lower() in pl:
                    raise PermissionError("🚨 읽기 금지 경로(%s): %s" % (mk, p))
        if G["write_on"] and _is_write(mode, flags) and G["write_root"] and _inside(p, G["write_root"]):
            if not repo_path_allowed(p, G["write_root"]):
                raise PermissionError("🚨 저장소 쓰기 가드: %s — 20년 수치 · 원자료는 캐시에만" % p)
    elif ev in ("os.rename", "os.replace", "shutil.copyfile", "shutil.move") and G["write_on"] and len(args) >= 2:
        try:
            dst = os.fsdecode(args[1])
        except Exception:
            return
        if G["write_root"] and _inside(dst, G["write_root"]) and not repo_path_allowed(dst, G["write_root"]):
            raise PermissionError("🚨 저장소 쓰기 가드(%s): %s" % (ev, dst))


def _ensure_hook():
    if not _GUARD["hook"]:
        sys.addaudithook(_hook)
        _GUARD["hook"] = True


def install_write_guard(root=None):
    """이 과정에서 저장소(root) 안 허용 목록 밖 파일을 쓰기로 열면 PermissionError — 굽기 · F0 · 연기 과정에 건다."""
    _ensure_hook()
    _GUARD["write_root"] = os.path.abspath(root or ROOT)
    _GUARD["write_on"] = True


def install_read_guard(signal_layer=False, extra=()):
    """읽기 금지 경로(tbatch_cache/out · _tbatch.json …) — signal_layer=True 면 EG30 산출 표식도 막는다(신호 층에 EG30 입력 없음)."""
    _ensure_hook()
    marks = tuple(FORBIDDEN_READ_MARKS) + (tuple(EG_FILE_MARKS) if signal_layer else ()) + tuple(extra)
    _GUARD["read_marks"] = marks
    _GUARD["read_on"] = True


def guard_off():
    _GUARD["write_on"] = False
    _GUARD["read_on"] = False


def opened_paths():
    return list(_GUARD["opened"])


LICENSED_NAME_MARKS = ("F-F_Research_Data_Factors", "Portfolios_Formed_on_", "6_Portfolios_", "25_Portfolios_", "_History.csv",
                       "fredgraph", "alfredgraph", "xbatch_cache")
OUTPUT_NAME_MARKS = ("_xbatch",)
OUTPUT_CONTENT_MARKS = (CACHE_ONLY_KEY.encode(), b"_xbatch.json", b"_xbatch.public.json", b"_xbatch.run.json")


def site_guard(root=None):
    """저장소 쪽 점검(굽기 전 · 등록 전) — git 이 추적 · 추가 예정인 파일 가운데 (가) 라이선스 원자료 이름 (나) 굽기 산출 이름(_xbatch*)
    (다) 허용 밖 data/_xb* · data/_xfwd/* (라) 허용 파일의 공개 안전 점검 (마) 사이트 자료(뿌리 *.html · js/*.js · data/*.json)의 20년 표지가 없어야 한다."""
    root = root or ROOT
    p = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        return {"ok": False, "bad": ["git ls-files 실패"], "n_bad": 1, "n_files": 0, "n_scanned": 0}
    files = [x for x in p.stdout.splitlines() if x]
    bad = []
    for f in files:
        b = os.path.basename(f)
        if any(mk in f for mk in LICENSED_NAME_MARKS):
            bad.append("라이선스 원자료로 보이는 파일: %s" % f)
        if any(b.startswith(mk) for mk in OUTPUT_NAME_MARKS):
            bad.append("굽기 산출 이름: %s" % f)
        if (f.startswith("data/_xb") or f.startswith("data/_xfwd/")) and f not in REPO_ALLOWED:
            bad.append("허용 밖 파일: %s" % f)
        if f in REPO_ALLOWED and os.path.exists(os.path.join(root, f)):
            try:
                with io.open(os.path.join(root, f), encoding="utf-8") as fh:
                    probs = public_safe(json.load(fh))
            except Exception as e:                                # noqa: BLE001
                probs = ["읽지 못함(%s)" % type(e).__name__]
            bad += ["%s: %s" % (f, x) for x in probs[:3]]
    scan = [f for f in files if (("/" not in f and f.endswith(".html")) or (f.startswith("js/") and f.endswith(".js"))
                                 or (f.startswith("data/") and f.endswith(".json") and (f.count("/") == 1 or f.startswith("data/_xfwd/"))))]
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


# ══════════════════════════════════════════════════════════════════════════
#  얼린 함수 blob 단언 도우미(다른 x_ 모듈도 쓴다)
# ══════════════════════════════════════════════════════════════════════════
def git_blob_sha(path):
    """작업 파일의 깃 blob SHA-1(git hash-object — 저장소 필터 적용) · git 이 없으면 원 바이트로 계산."""
    try:
        p = subprocess.run(["git", "hash-object", os.path.abspath(path)], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(path)))
        if p.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", p.stdout.strip()):
            return p.stdout.strip()
    except Exception:
        pass
    with open(path, "rb") as f:
        b = f.read()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def assert_blob(module, want, root=None):
    """build/<module>.py 의 blob 이 등록값과 같아야 부른다(얼린 함수 — 고치지 않고 부르기만)."""
    p = os.path.join(root or HERE, module + ".py")
    got = git_blob_sha(p)
    if got != want:
        raise SystemExit("🚨 얼린 모듈 %s blob %s ≠ 등록 %s — 부르지 않는다" % (module, got[:12], want[:12]))
    return got


_VD = None


def _v_data():
    """French 파서(v_data.parse_french_blob) — blob 단언 뒤 한 번만 가져온다."""
    global _VD
    if _VD is None:
        assert_blob("v_data", V_DATA_BLOB)
        import v_data as _m                                      # noqa: E402 — blob 단언 뒤에만
        _VD = _m
    return _VD


# ══════════════════════════════════════════════════════════════════════════
#  원천 목록(data_plan.market_US · measurement_inputs · growth_proxy) — 국외는 x_intl
# ══════════════════════════════════════════════════════════════════════════
LIC = {
    "yf": "Yahoo Finance(yfinance) — 개인 · 캐시만 · 재게시 없음",
    "fred": "FRED(St. Louis Fed) — 공공 · BAA10Y/DBAA 는 Moody's 저작권 표기 · 원자료 재게시 없음",
    "alfred": "ALFRED(St. Louis Fed) — 판 이력 · 원자료 재게시 없음",
    "cboe": "Cboe Global Markets — 지수 이력 CSV · 원자료 재게시 없음",
    "french": "Kenneth R. French Data Library — 출처 표기 · 재게시 없음",
    "lab": "랩 저장소 data/ (이미 공개 · 해시만)",
}
FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
_FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
_CBOE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/%s_History.csv"


def _src(key, kind, sid, rel, url, seeds, use, lic, **kw):
    d = {"key": key, "kind": kind, "id": sid, "rel": rel, "url": url, "seeds": list(seeds), "use": use, "license": LIC[lic]}
    d.update(kw)
    return d


def registry():
    """키 → 원천 명세. 키 꼴 «출처/id». rel = 캐시 raw/ 아래 경로."""
    R = {}

    def add(d):
        R[d["key"]] = d
    yfu = "yfinance:Ticker(%r).history(period='max', auto_adjust=False, actions=True)"
    add(_src("yf/SPY", "yf", "SPY", "us/yf/SPY.csv", yfu % "SPY", [os.path.join(SEED_T, "yf", "SPY.csv")],
             "X-BEAR 주 수익(수정종가 = TR) · M 층 일간 T+1 · 결정일 달력", "yf", col="Adj Close", seed_meta=os.path.join(SEED_T_META, "yf_SPY.json")))
    add(_src("yf/^SP500TR", "yf", "^SP500TR", "us/yf/_SP500TR.csv", yfu % "^SP500TR", [os.path.join(SEED_T, "yf", "_SP500TR.csv")],
             "SPY TR 월 값 대조(개수만)", "yf", col="Close", seed_meta=os.path.join(SEED_T_META, "yf__SP500TR.json")))
    add(_src("yf/^GSPC", "yf", "^GSPC", "us/yf/_GSPC.csv", yfu % "^GSPC",
             [os.path.join(SEED_V, "yf", "_GSPC.csv"), os.path.join(SEED_T, "yf", "_GSPC.csv")],
             "지그재그(얼린 mech_episodes) · 하락월(S&P PR) · SMA200 쌍둥이", "yf", col="Close", seed_meta=os.path.join(SEED_V_META, "yf___GSPC.json")))
    for tk, use in (("IVW", "X-GVTREND 성장(TR)"), ("IVE", "X-GVTREND 가치(TR)"), ("IWF", "G 층 보고 코어 IWF TR")):
        add(_src("yf/" + tk, "yf", tk, "us/yf/%s.csv" % tk, yfu % tk, [os.path.join(SEED_T, "yf", tk + ".csv")], use, "yf",
                 col="Adj Close", seed_meta=os.path.join(SEED_T_META, "yf_%s.json" % tk)))
    for sid, use in (("DGS3MO", "rf 대조(주 원천은 rf_monthly 고정 사본) · 일간 rf"),
                     ("BAA10Y", "X-CRED · X-BLR CREDIT · X-COMP"),
                     ("DBAA", "BAA10Y 항등식 · Moody's 지속 · ALFRED 판 대조"),
                     ("DGS10", "BAA10Y 항등식 · ALFRED 판 대조"),
                     ("DFII10", "X-RRSHOCK(F_G 측정)")):
        add(_src("fred/" + sid, "fred", sid, "us/fred/%s.csv" % sid, _FRED + sid, [], use, "fred"))
    add(_src("cboe/VIX", "cboe", "VIX", "us/cboe/VIX_History.csv", _CBOE % "VIX", [os.path.join(SEED_T, "cboe", "VIX_History.csv")],
             "X-VTS · X-COMP · X-BLR FEAR(Cboe 1차)", "cboe", col="CLOSE", seed_meta=os.path.join(SEED_T_META, "cboe_VIX.json")))
    add(_src("cboe/VIX3M", "cboe", "VIX3M", "us/cboe/VIX3M_History.csv", _CBOE % "VIX3M", [], "X-VTS · X-COMP(공표일 뒤만 · Cboe 1차)",
             "cboe", col="CLOSE"))
    add(_src("lab/rf_monthly", "lab", "rf_monthly", "us/lab/rf_monthly.json", "data/rf_monthly.json", [os.path.join(DATA, "rf_monthly.json")],
             "r^e 의 rf = DGS3MO(u−1 월평균)/12(명세 signals X-BEAR data)", "lab"))
    add(_src("lab/assets", "lab", "assets", "us/lab/assets.json", "data/assets.json", [os.path.join(DATA, "assets.json")],
             "yfinance ^VIX3M 값 대조만(수익 계산 없음)", "lab"))
    for fid, fn, use, sd in (
            ("ff3_m", "F-F_Research_Data_Factors_CSV.zip", "Mkt · RF(G 층 펀드 Mkt · French Mkt-RF 판 상태 일치)", SEED_V),
            ("ff3_d", "F-F_Research_Data_Factors_daily_CSV.zip", "Mkt-RF 일간(보고)", SEED_V),
            ("p6_m", "6_Portfolios_2x3_CSV.zip", "LG 주 코어 BIG LoBM(VW 월)", SEED_U),
            ("p6_d", "6_Portfolios_2x3_daily_CSV.zip", "LG 코어 일간(보고)", SEED_U),
            ("me_beta", "25_Portfolios_ME_BETA_5x5_CSV.zip", "D 대리 ME5×β1 = BIG LoBETA", SEED_V),
            ("beta", "Portfolios_Formed_on_BETA_CSV.zip", "D 대리 대체 Lo 20(충실도 < 0.6 이면 · 기계적)", SEED_V),
            ("beme", "Portfolios_Formed_on_BE-ME_CSV.zip", "EXG = BE-ME Lo 10", SEED_V),
            ("me_prior12", "6_Portfolios_ME_Prior_12_2_CSV.zip", "MOM = BIG HiPRIOR", SEED_V),
            ("me_op", "6_Portfolios_ME_OP_2x3_CSV.zip", "QG = BIG HiOP", SEED_V)):
        add(_src("french/" + fid, "french", fid, "french/" + fn, FF + fn,
                 [os.path.join(sd, "french", fn), os.path.join(SEED_U if sd == SEED_V else SEED_V, "french", fn)], use, "french"))
    return R


GROWTH_PROXIES = {                                           # G 층 코어(evaluation.growth_proxy_20y.cores) — (파일, 칸)
    "LG": ("p6_m", "BIG LoBM"), "EXG": ("beme", "Lo 10"), "MOM": ("me_prior12", "BIG HiPRIOR"), "QG": ("me_op", "BIG HiOP"),
}
D_PROXY = ("me_beta", "BIG LoBETA")                          # ME5×β1
D_PROXY_FALLBACK = ("beta", "Lo 20")


def cache_raw(rel):
    return os.path.join(cache_guard(), "raw", *rel.split("/"))


def _meta_path(key):
    return os.path.join(cache_guard(), "meta", re.sub(r"[^A-Za-z0-9_.@-]+", "_", key) + ".json")


def read_meta(key):
    p = _meta_path(key)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _write_bytes(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "wb") as f:
        f.write(blob)
    os.replace(path + ".part", path)


def _write_meta(key, meta):
    _write_bytes(_meta_path(key), (json.dumps(meta, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


# ── 받기(호스트마다 ≥ HOST_GAP 초) ─────────────────────────────────────────
def _host_wait(host, gap=HOST_GAP):
    p = os.path.join(cache_guard(), "meta", "_hosts.json")
    try:
        with io.open(p, encoding="utf-8") as f:
            last = json.load(f)
    except Exception:
        last = {}
    dt = time.time() - float(last.get(host, 0))
    if dt < gap:
        time.sleep(gap - dt)
    last[host] = time.time()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(last, f)


def http_get(url, ua=UA_PY, timeout=90, tries=3):
    last = None
    host = urllib.parse.urlparse(url).netloc
    for k in range(tries):
        _host_wait(host)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), {"status": r.status, "last_modified": r.headers.get("Last-Modified"), "content_type": r.headers.get("Content-Type")}
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404, 410):
                raise
            last = e
        except Exception as e:                                   # noqa: BLE001 — 망 오류는 쉬고 다시
            last = e
        time.sleep(2.0 * (k + 1))
    raise last


def _yf_blob(ticker):
    import yfinance as yf
    _host_wait("query2.finance.yahoo.com", 1.5)
    df = yf.Ticker(ticker).history(period="max", auto_adjust=False, actions=True)
    if df is None or df.empty:
        raise RuntimeError("yfinance %s: 빈 응답" % ticker)
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "Date"
    cols = [c for c in ("Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits", "Capital Gains") if c in df.columns]
    txt = df[cols].to_csv(date_format="%Y-%m-%d", float_format="%.10g", lineterminator="\n")
    return txt.encode("utf-8"), {"status": 200, "yfinance": getattr(yf, "__version__", "?")}


def sniff(kind, blob):
    """받은 것이 기대한 꼴인가(오류 페이지 · 봇 검사 페이지를 고정본으로 삼지 않는다)."""
    if kind == "yf":
        ok = blob[:5] == b"Date,"
    elif kind in ("fred", "alfred"):
        ok = blob.lstrip(b"\xef\xbb\xbf")[:16].lower().startswith(b"observation_date")
    elif kind == "cboe":
        ok = blob[:4].upper() == b"DATE"
    elif kind == "french":
        ok = blob[:2] == b"PK"
    elif kind == "lab":
        try:
            json.loads(blob.decode("utf-8"))
            ok = True
        except Exception:
            ok = False
    else:
        ok = len(blob) > 0
    if not ok:
        raise ValueError("%s: 기대한 꼴이 아니다(앞 %r)" % (kind, blob[:40]))
    return True


def pin(key, fetch=True, R=None):
    """원천 하나를 캐시에 고정 — 있으면 그대로(판 동결) · 없으면 raw 사본(SHA 기록) → 받기. 돌려주는 것 상태 문자열."""
    R = R or registry()
    ds = R[key]
    p = cache_raw(ds["rel"])
    if os.path.exists(p) and read_meta(key):
        return "고정본 있음"
    blob, origin, extra = None, None, {}
    for s in ds["seeds"]:
        if s and os.path.exists(s):
            pl = s.replace("\\", "/").lower()
            if any(mk in pl for mk in FORBIDDEN_READ_MARKS):
                raise PermissionError("🚨 금지 경로 사본: %s" % s)
            with open(s, "rb") as f:
                blob = f.read()
            tag = "tbatch_cache/raw" if _inside(s, SEED_T) else ("vbatch_cache/raw" if _inside(s, SEED_V) else
                                                                  ("ubatch_cache/raw" if _inside(s, SEED_U) else "repo:" + _rel(s)))
            origin = "copy:" + tag
            extra = {"seed_path": s.replace("\\", "/"), "seed_mtime": _dt.datetime.fromtimestamp(os.path.getmtime(s), _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            if ds["kind"] == "lab":
                extra["repo_blob"] = git_blob_sha(s)                   # 저장소 판(자동 갱신 파일이라 들인 때의 blob 을 적는다)
                extra["repo_head"] = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            sm = ds.get("seed_meta")
            if sm and os.path.exists(sm):
                try:
                    with io.open(sm, encoding="utf-8") as f:
                        m0 = json.load(f)
                    extra["seed_meta"] = {k: m0.get(k) for k in ("fetched_at", "pinned_at", "origin", "sha256", "yfinance", "url") if k in m0}
                except Exception:
                    pass
            break
    info = {}
    if blob is None:
        if not fetch:
            return "사본 없음(받지 않음)"
        if ds["kind"] == "yf":
            blob, info = _yf_blob(ds["id"])
        else:
            blob, info = http_get(ds["url"], UA_PY if ds["kind"] in ("fred", "alfred", "cboe") else UA_BROWSER)
        origin = "live"
    sniff(ds["kind"], blob)
    if ds["kind"] == "french":
        fr = _v_data().parse_french_blob(blob)
        if fr["crsp"] != CRSP_WANT:
            return "🚨 CRSP %s ≠ %s — 들이지 않음" % (fr["crsp"], CRSP_WANT)
        extra["crsp"] = fr["crsp"]
    _write_bytes(p, blob)
    meta = {"key": key, "url": ds["url"], "origin": origin, "pinned_at": _now(), "sha256": sha256_bytes(blob), "bytes": len(blob),
            "last_modified": info.get("last_modified"), "license": ds["license"]}
    if "yfinance" in info:
        meta["yfinance"] = info["yfinance"]
    meta.update(extra)
    if extra.get("seed_meta", {}).get("sha256") and extra["seed_meta"]["sha256"] != meta["sha256"]:
        meta["seed_meta_sha_mismatch"] = True
    _write_meta(key, meta)
    return "들임(%s)" % origin


# ══════════════════════════════════════════════════════════════════════════
#  파서
# ══════════════════════════════════════════════════════════════════════════
def parse_yf_csv(blob):
    df = pd.read_csv(io.BytesIO(blob), index_col=0)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index, format="%Y-%m-%d"))
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def parse_fred_csv(blob):
    """FRED/ALFRED 그래프 CSV → 일 Series(DatetimeIndex) · «.» · 빈칸은 NaN · 여러 열이면 DataFrame."""
    txt = blob.decode("utf-8-sig")
    rows = [r for r in csv.reader(io.StringIO(txt)) if r]
    hdr = [h.strip() for h in rows[0]]
    body = [r for r in rows[1:] if r[0].strip()]
    idx = pd.DatetimeIndex(pd.to_datetime([r[0].strip() for r in body], format="%Y-%m-%d"))
    vals = [[(float(x) if x.strip() not in ("", ".") else np.nan) for x in (r[1:] + [""] * len(hdr))[:len(hdr) - 1]] for r in body]
    df = pd.DataFrame(vals, index=idx, columns=hdr[1:])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df.iloc[:, 0].rename(hdr[1]) if df.shape[1] == 1 else df


def parse_cboe_csv(blob):
    """Cboe 지수 이력 CSV(DATE MM/DD/YYYY) → 일 DataFrame(OPEN · HIGH · LOW · CLOSE)."""
    rows = [r for r in csv.reader(io.StringIO(blob.decode("utf-8-sig"))) if r]
    hdr = [h.strip().upper() for h in rows[0]]
    body = [r for r in rows[1:] if r[0].strip()]

    def iso(d):
        d = d.strip()
        if "/" in d:
            m, dd, y = d.split("/")
            return "%s-%02d-%02d" % (y, int(m), int(dd))
        return d
    idx = pd.DatetimeIndex(pd.to_datetime([iso(r[0]) for r in body], format="%Y-%m-%d"))
    vals = [[(float(x) if x.strip() not in ("", ".") else np.nan) for x in (r[1:] + [""] * len(hdr))[:len(hdr) - 1]] for r in body]
    df = pd.DataFrame(vals, index=idx, columns=hdr[1:])
    df.attrs["dup_dates"] = int(df.index.duplicated().sum())
    return df[~df.index.duplicated(keep="first")].sort_index()


# ══════════════════════════════════════════════════════════════════════════
#  로더 — 고정본만 읽는다 · 기본 창 [INPUT_MIN, bake_end()]
# ══════════════════════════════════════════════════════════════════════════
_MEM = {}


def _raw_blob(key):
    R = registry()
    p = cache_raw(R[key]["rel"])
    if not os.path.exists(p):
        raise FileNotFoundError("고정본 없음: %s — python build/x_data.py --pin" % key)
    with open(p, "rb") as f:
        return f.read()


def load_full(key):
    """원천 전체(창 자르기 전) — 요약 · 해시 · 커버리지 전용. 신호 · 평가는 창 로더를 쓴다."""
    if key in _MEM:
        return _MEM[key]
    R = registry()
    kind = R[key]["kind"]
    b = _raw_blob(key)
    if kind == "yf":
        obj = parse_yf_csv(b)
    elif kind == "fred":
        obj = parse_fred_csv(b)
    elif kind == "cboe":
        obj = parse_cboe_csv(b)
    elif kind == "french":
        fr = _v_data().parse_french_blob(b)
        if fr["crsp"] != CRSP_WANT:
            raise SystemExit("🚨 %s CRSP %s ≠ %s — French 판이 섞이면 멈춘다" % (key, fr["crsp"], CRSP_WANT))
        obj = fr
    elif kind == "lab":
        obj = json.loads(b.decode("utf-8"))
    else:
        raise KeyError(kind)
    _MEM[key] = obj
    return obj


def _last_complete_month(end):
    """날짜 end 까지 **다 끝난** 마지막 달(달 값은 그달 끝에야 선다) · 'YYYY-MM' 이면 그 달(포함)."""
    s = str(end)
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return pd.Period(s, "M")
    return (pd.Timestamp(end) + pd.Timedelta(days=1)).to_period("M") - 1


def clip(obj, start=INPUT_MIN, end=None):
    """창 자르기 — DatetimeIndex 는 날짜 · PeriodIndex(M) 는 달(끝 = end 까지 다 끝난 달 · 2026-09-01 이면 2026-08). end 기본 = bake_end()."""
    end = end if end is not None else bake_end()
    idx = obj.index
    if isinstance(idx, pd.PeriodIndex):
        a, z = pd.Period(str(start)[:7], "M"), _last_complete_month(end)
        return obj.loc[(idx >= a) & (idx <= z)]
    a, z = pd.Timestamp(start), pd.Timestamp(end)
    return obj.loc[(idx >= a) & (idx <= z)]


def _daily_col(key, col, start=INPUT_MIN, end=None):
    df = load_full(key)
    s = df[col] if isinstance(df, pd.DataFrame) else df
    s = pd.to_numeric(s, errors="coerce").dropna().astype(float)
    s.name = key.split("/", 1)[1] + ":" + col
    return clip(s, start, end)


def spy_tr(start=INPUT_MIN, end=None):
    """SPY 수정종가(분배 재투자 = TR) 일간 — X-BEAR 주 수익 · M 층 T+1."""
    return _daily_col("yf/SPY", "Adj Close", start, end)


def sp500tr(start=INPUT_MIN, end=None):
    return _daily_col("yf/^SP500TR", "Close", start, end)


def gspc_pr(start=INPUT_MIN, end=None):
    """^GSPC 종가(PR) 일간 — 하락월 · 지그재그(얼린 mech_episodes 에 넘긴다) · SMA200."""
    return _daily_col("yf/^GSPC", "Close", start, end)


def zigzag_inputs(start=INPUT_MIN, end=None):
    """얼린 mech_episodes.zigzag(D, P, hd, hu, start, end) · rebounds 에 넘길 (날짜 문자열 목록, 종가 목록) — ^GSPC PR 창 안.
    명세: zigzag 는 2006-08-31 부터 부른다(start 인자는 zigzag 쪽) · 이 목록은 2005-08-01 ~ bake_end(반등 끝이 창 끝에서 잘린다)."""
    s = gspc_pr(start, end)
    return [d.strftime("%Y-%m-%d") for d in s.index], [float(v) for v in s.to_numpy()]


def etf_tr(ticker, start=INPUT_MIN, end=None):
    if ticker not in ("IVW", "IVE", "IWF"):
        raise KeyError("미국 ETF 는 IVW · IVE · IWF 만(국가 ETF 는 x_intl)")
    return _daily_col("yf/" + ticker, "Adj Close", start, end)


def fred_daily(sid, start=INPUT_MIN, end=None):
    if sid not in ("DGS3MO", "BAA10Y", "DBAA", "DGS10", "DFII10"):
        raise KeyError(sid)
    return _daily_col("fred/" + sid, sid, start, end)


def vix(start=INPUT_MIN, end=None):
    """Cboe VIX 종가(16:15 ET) — T+1 주 행은 d_m 값 · D0 행은 d_m − 1(가용 표 'vix')."""
    return _daily_col("cboe/VIX", "CLOSE", start, end)


def vix3m(start=INPUT_MIN, end=None, published_only=False):
    """Cboe VIX3M 종가 — published_only=True 면 공표일(vxv_pub_date) 앞 관측을 뺀다(X-VTS: 공표 전 VTS = 0)."""
    s = _daily_col("cboe/VIX3M", "CLOSE", start, end)
    if published_only:
        s = s.loc[s.index >= pd.Timestamp(vxv_pub_date())]
    return s


def vxv_evidence_path():
    return os.path.join(cache_guard(), "meta", "vxv_pub_evidence.json")


def vxv_pub_date():
    """VIX3M(옛 VXV) 공표일 — 기본 2009-09-18(Cboe 공식 CSV 시작일 · SN-1.1). F0 가 Cboe 1차 공고(URL · SHA · 날짜)를
    meta/vxv_pub_evidence.json 에 두고 그 날이 더 이를 때만 앞당긴다(기계적 · 뒤로 미루지 않는다)."""
    d = VXV_PUB_DEFAULT
    p = vxv_evidence_path()
    if os.path.exists(p):
        with io.open(p, encoding="utf-8") as f:
            ev = json.load(f)
        e = ev.get("date")
        if e and ev.get("primary_cboe") and ev.get("sha256") and ev.get("url") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", e) and e < d:
            d = e
    return d


def vix3m_yf_lab(start=INPUT_MIN, end=None):
    """yfinance ^VIX3M(data/assets.json 고정 사본 px) — Cboe 값 대조만(수익 계산 없음)."""
    A = load_full("lab/assets")
    s = pd.Series([np.nan if v is None else float(v) for v in A["px"]["^VIX3M"]], index=pd.DatetimeIndex(pd.to_datetime(A["dates"])))
    return clip(s.dropna().sort_index(), start, end)


def rf_monthly_lab():
    """data/rf_monthly.json(고정 사본) monthly[m] = (1 + ȳ_m)^(1/12) − 1 · ȳ_m = 달 m 의 DGS3MO 일간 평균(소수 연율)."""
    R = load_full("lab/rf_monthly")["monthly"]
    ks = sorted(R)
    return pd.Series([float(R[k]) for k in ks], index=pd.PeriodIndex(ks, freq="M"), name="rf_monthly_lab")


def rf_us_monthly(start=INPUT_MIN_MONTH, end=None):
    """보유월 u 의 rf(소수 · 월) = DGS3MO(u−1 월평균)/12(명세 X-BEAR 정의) — rf_monthly 고정 사본을 ȳ 로 되돌려(ȳ = (1+m)^12 − 1) 한 달 민다.
    🚨 20년 규칙: 관측 달(u−1)을 먼저 [2005-08, 끝] 으로 자른다 → 첫 보유월 u = 2005-09(창 앞 2005-07 평균을 쓰지 않는다).
    가용: 결정월 t 에는 u ≤ t 만(가용 표 'rf_us_m')."""
    m = rf_monthly_lab()
    ybar = clip((1.0 + m) ** 12 - 1.0, start, end)             # 관측 달 창
    rf = (ybar / 12.0)
    rf.index = rf.index + 1                                    # 관측 달 u−1 → 보유월 u
    rf.name = "rf_us"
    return rf


def dgs3mo_month_mean():
    """FRED DGS3MO 일간의 달 평균(소수 연율 · 관측 달 색인 · 창 안) — rf_monthly 대조 전용."""
    s = fred_daily("DGS3MO", start=INPUT_MIN, end=None) / 100.0
    return s.groupby(s.index.to_period("M")).mean()


def french_block(fid, kind="vw_m"):
    fr = load_full("french/" + fid)
    return fr["blocks"][kind]


def french_leg(fid, col, start=INPUT_MIN_MONTH, end=None, daily=False):
    """French 칸 하나의 VW 수익(소수) · 그달 기업 수 < 20 이면 NaN(측정 불가). 평가 전용(신호 입력 금지 · 가용 표 'french')."""
    r = french_block(fid, "vw_m")[col] / 100.0
    if not daily:
        try:
            n = french_block(fid, "nfirms")
            if col in n.columns:
                r = r.where(n[col].reindex(r.index) >= MIN_FIRMS)
        except KeyError:
            pass
    r.name = "%s:%s" % (fid, col)
    if daily:
        return clip(r, start if len(str(start)) > 7 else str(start) + "-01", end)
    return clip(r, start, end)


def ff3(freq="m", start=INPUT_MIN_MONTH, end=None):
    """F-F 3팩터(소수) · Mkt = Mkt-RF + RF — 평가 전용."""
    df = french_block("ff3_m" if freq == "m" else "ff3_d", "m" if freq == "m" else "d") / 100.0
    df = df.copy()
    df["Mkt"] = df["Mkt-RF"] + df["RF"]
    if freq == "m":
        return clip(df, start, end)
    return clip(df, start if len(str(start)) > 7 else str(start) + "-01", end)


def growth_proxy(name, start=INPUT_MIN_MONTH, end=None):
    fid, col = GROWTH_PROXIES[name]
    return french_leg(fid, col, start, end)


def d_proxy(fallback=False, start=INPUT_MIN_MONTH, end=None):
    fid, col = D_PROXY_FALLBACK if fallback else D_PROXY
    return french_leg(fid, col, start, end)


def french_last_month():
    """French 판의 마지막 달(필요한 파일 가운데 가장 이른 끝) — G 층은 여기서 끝낸다(명세 growth_proxy_20y.frame)."""
    ends = []
    for fid in ("ff3_m", "p6_m", "me_beta", "beta", "beme", "me_prior12", "me_op"):
        ends.append(french_block(fid, "vw_m" if fid != "ff3_m" else "m").index.max())
    return str(min(ends))


# ══════════════════════════════════════════════════════════════════════════
#  달력 — NYSE 거래일(SPY 수정종가가 있는 날) · 결정일 d_m · T+1
# ══════════════════════════════════════════════════════════════════════════
_CAL = {"days": None}


def set_calendar(days):
    """합성 시험 · 다른 층이 달력을 주입할 때(None 이면 SPY 로 되돌린다)."""
    _CAL["days"] = None if days is None else pd.DatetimeIndex(pd.to_datetime(days)).sort_values()
    _CAL.pop("bake_end", None)


def trading_days():
    if _CAL["days"] is None:
        s = load_full("yf/SPY")["Adj Close"].dropna()
        _CAL["days"] = pd.DatetimeIndex(s.index).sort_values()
    return _CAL["days"]


def decision_days(first=INPUT_MIN_MONTH, last=SCORE_LAST):
    """달(PeriodIndex) → 그달 마지막 거래일(결정일 d_m 종가). 자료 끝 달이 그달 마지막 평일 전에 끝나면(진행 중) 싣지 않는다."""
    d = trading_days()
    s = pd.Series(d, index=d.to_period("M"))
    out = s.groupby(level=0).max()
    out = out.loc[(out.index >= pd.Period(first, "M")) & (out.index <= pd.Period(last, "M"))]
    if len(out):
        pm = d[-1].to_period("M")
        if out.index[-1] == pm and d[-1] < pd.bdate_range(pm.start_time, pm.end_time)[-1]:
            out = out.iloc[:-1]
    return out


def t_plus_1(d):
    """d 다음 거래일(달력 안) — 달력 밖이면 None(소급 · 추정 없음)."""
    days = trading_days()
    j = int(days.searchsorted(pd.Timestamp(d), side="right"))
    return days[j] if j < len(days) else None


def prev_session(d):
    days = trading_days()
    j = int(days.searchsorted(pd.Timestamp(d), side="left")) - 1
    return days[j] if j >= 0 else None


def bake_end():
    """굽기 입력의 끝 = 마지막 채점 보유월(2026-08)의 결정일 다음 거래일(T+1 체결) — 그 뒤 자료는 굽기에 쓰지 않는다."""
    if "bake_end" in _CAL:
        return _CAL["bake_end"]
    out = pd.Timestamp("2026-09-01")                           # 2026-08-31(월) 다음 NYSE 거래일 — 달력이 없을 때의 선언값
    try:
        dd = decision_days(SCORE_LAST, SCORE_LAST)
        if len(dd):
            t1 = t_plus_1(dd.iloc[-1])
            if t1 is not None:
                out = t1
        _CAL["bake_end"] = out
    except FileNotFoundError:
        pass
    return out


def holding_span(u, mode="T1"):
    """보유월 u 의 (시작 체결일, 끝 체결일) — T1: (T+1 of d_{u−1}, T+1 of d_u) · D0: (d_{u−1}, d_u). 수익은 이 두 종가 사이."""
    u = pd.Period(u, "M")
    dd = decision_days(str(u - 1), str(u))
    if len(dd) < 2:
        return None
    a, b = dd.iloc[0], dd.iloc[1]
    if mode == "D0":
        return a, b
    return t_plus_1(a), t_plus_1(b)


# ══════════════════════════════════════════════════════════════════════════
#  가용 늦춤 표(data_plan.availability_lags · SN-1.2) — 결정일 d_m 에 쓸 수 있는 마지막 관측
# ══════════════════════════════════════════════════════════════════════════
MODES = ("T1", "D0", "G")
AVAIL = {
    #  이름: {freq, 모드별 규칙, 설명} — 규칙: same_day(d_m 포함) · prev_session(d_m 앞 거래일) · prev_bday(d_m 앞 평일) · month_le(달 ≤ 결정월) · None(금지)
    "spy":     {"freq": "d", "T1": "same_day", "D0": "same_day", "G": "same_day", "note": "SPY 16:00 ET 종가(수정종가 TR)"},
    "gspc":    {"freq": "d", "T1": "same_day", "D0": "same_day", "G": "same_day", "note": "^GSPC 16:00 종가(PR)"},
    "sp500tr": {"freq": "d", "T1": None, "D0": None, "G": None, "note": "대조 전용 — 신호 입력 금지"},
    "etf":     {"freq": "d", "T1": "same_day", "D0": "same_day", "G": "same_day", "note": "IVW · IVE · IWF · 국가 ETF 종가"},
    "vix":     {"freq": "d", "T1": "same_day", "D0": "prev_session", "G": "same_day",
                "note": "Cboe VIX 16:15 ET > SPY 16:00 — D0 행(d_m 종가 체결)은 d_m − 1 거래일 VIX(SN-1.2) · T+1 주 행은 d_m"},
    "vix3m":   {"freq": "d", "T1": "same_day", "D0": "prev_session", "G": "same_day",
                "note": "VIX 와 같은 시각(16:15) · 공표일(VXV_PUB) 앞은 VTS = 0"},
    "fred_d":  {"freq": "d", "T1": "prev_bday", "D0": "prev_bday", "G": "prev_bday",
                "note": "FRED 일간(BAA10Y · DBAA · DGS10 · DFII10 · DGS3MO)은 다음 영업일 공표 — d_m − 1 영업일(보수)"},
    "fred_fx": {"freq": "d", "T1": "same_day", "D0": "same_day", "G": "same_day", "note": "H.10 정오(NY) d_m 값 · 없으면 직전 영업일(x_intl)"},
    "rf_us_m": {"freq": "m", "T1": "month_le", "D0": "month_le", "G": "month_le",
                "note": "보유월 u 의 rf = DGS3MO(u−1 월평균)/12 — 결정월 t 에는 u ≤ t 만(u = t 는 t−1 월평균)"},
    "oecd_m":  {"freq": "m", "T1": "month_le", "D0": "month_le", "G": "month_le",
                "note": "현지 3개월 금리 u−1 월평균/12 · 늦으면 마지막 공표값 유지(선언 · x_intl)"},
    "french":  {"freq": "m", "T1": None, "D0": None, "G": "month_le",
                "note": "French — 신호에 쓰지 않는다(평가 · G 층 전용 · 월말 근사 = 하루 선견은 M 의 D0−T+1 차이로 적는다 SN-1.4)"},
    "vix3m_yf": {"freq": "d", "T1": None, "D0": None, "G": None, "note": "yfinance ^VIX3M — Cboe 값 대조 전용"},
}


def avail_rule(name, mode="T1"):
    if mode not in MODES:
        raise ValueError("mode 는 T1 · D0 · G")
    if name not in AVAIL:
        raise KeyError("가용 늦춤이 선언되지 않은 입력: %s — AVAIL 에 먼저 적는다" % name)
    r = AVAIL[name][mode]
    if r is None:
        raise PermissionError("🚨 %s 는 %s 모드 입력으로 쓰지 않는다 — %s" % (name, mode, AVAIL[name]["note"]))
    return r


def cutoff(name, d, mode="T1"):
    """결정일 d(종가 판정)에 쓸 수 있는 마지막 관측 — 일 규칙이면 날짜(Timestamp) · 달 규칙이면 달(Period)."""
    r = avail_rule(name, mode)
    d = pd.Timestamp(d)
    if r == "same_day":
        return d
    if r == "prev_session":
        p = prev_session(d)
        return p if p is not None else d - pd.offsets.BDay(1)
    if r == "prev_bday":
        return (d - pd.offsets.BDay(1)).normalize()
    if r == "month_le":
        return d.to_period("M")
    raise ValueError(r)


def _after_mask(obj, name, d, mode):
    c = cutoff(name, d, mode)
    idx = obj.index
    if isinstance(c, pd.Period):
        if not isinstance(idx, pd.PeriodIndex):
            raise TypeError("%s: 달 규칙인데 색인이 달이 아니다" % name)
        return np.asarray(idx > c)
    if not isinstance(idx, pd.DatetimeIndex):
        raise TypeError("%s: 일 규칙인데 색인이 날짜가 아니다" % name)
    return np.asarray(idx > c)


def asof(obj, name, d, mode="T1"):
    """결정일 d 에 쓸 수 있는 부분만."""
    return obj.loc[~_after_mask(obj, name, d, mode)]


def last_value(obj, name, d, mode="T1"):
    s = asof(obj, name, d, mode)
    s = s.dropna() if isinstance(s, pd.Series) else s.dropna(how="all")
    return None if len(s) == 0 else s.iloc[-1]


# ══════════════════════════════════════════════════════════════════════════
#  20년 창 단언(러너 · 신호 · 평가가 부른다)
# ══════════════════════════════════════════════════════════════════════════
def assert_scored_months(months, first=SCORE_FIRST, last=SCORE_LAST, n_max=N_SCORE):
    """채점 보유월 최소 = 2006-09 · 최대 = 2026-08 · 개수 ≤ 240 · 중복 없음."""
    ms = [pd.Period(str(m), "M") for m in months]
    if not ms:
        raise AssertionError("채점 보유월이 없다")
    if min(ms) < pd.Period(first, "M"):
        raise AssertionError("🚨 채점 보유월 %s < %s — 20년 규칙 위반" % (min(ms), first))
    if max(ms) > pd.Period(last, "M"):
        raise AssertionError("🚨 채점 보유월 %s > %s — 굽기 창 밖" % (max(ms), last))
    if len(set(ms)) != len(ms):
        raise AssertionError("채점 보유월 중복")
    if len(ms) > n_max:
        raise AssertionError("채점 보유월 %d > %d" % (len(ms), n_max))
    return {"first": str(min(ms)), "last": str(max(ms)), "n": len(ms)}


def _min_index(obj):
    idx = obj.index
    if len(idx) == 0:
        return None
    return idx.min()


def assert_input_floor(inputs, floor=INPUT_MIN):
    """입력 최소 날짜 ≥ 2005-08-01(달 색인은 ≥ 2005-08) — inputs = {이름: Series/DataFrame} 또는 (obj, 가용 이름) 쌍."""
    f_d, f_m = pd.Timestamp(floor), pd.Period(floor[:7], "M")
    out = {}
    for k, v in inputs.items():
        obj = v[0] if isinstance(v, tuple) else v
        m = _min_index(obj)
        if m is None:
            continue
        if isinstance(m, pd.Period):
            if m < f_m:
                raise AssertionError("🚨 입력 %s 첫 달 %s < %s — 20년 규칙 위반" % (k, m, f_m))
        elif pd.Timestamp(m) < f_d:
            raise AssertionError("🚨 입력 %s 첫 날 %s < %s — 20년 규칙 위반" % (k, pd.Timestamp(m).date(), floor))
        out[k] = str(m)[:10]
    return out


def assert_first_active(element, first_month):
    """측정 팔 · 주 가설의 첫 활성(결정) 달이 명세 하한 이상 — 워밍업이 창 앞 자료를 쓰지 않았다는 기계적 확인."""
    want = MIN_WARMUP_BY_ELEMENT.get(element)
    if want and pd.Period(str(first_month), "M") < pd.Period(want, "M"):
        raise AssertionError("🚨 %s 첫 활성 %s < 명세 %s" % (element, first_month, want))
    return True


# ══════════════════════════════════════════════════════════════════════════
#  선견 점검 틀 — d_m 뒤 자료를 흔들어도(자르기 · 난수) 결정 해시가 같아야 한다
# ══════════════════════════════════════════════════════════════════════════
def _canon(x):
    if isinstance(x, (pd.Series, pd.DataFrame)):
        return {"i": [str(i) for i in x.index], "v": _canon(x.to_numpy().tolist())}
    if isinstance(x, np.ndarray):
        return _canon(x.tolist())
    if isinstance(x, dict):
        return {str(k): _canon(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        v = float(x)
        if not math.isfinite(v):
            return "nan" if v != v else ("inf" if v > 0 else "-inf")
        return float("%.12g" % v)
    if x is None:
        return None
    return str(x)


def decision_hash(x):
    """결정(수 · 목록 · dict · Series 한 행)의 정규화 해시(유효 12자리) — 값은 싣지 않고 해시만 비교한다."""
    return sha256_bytes(json.dumps(_canon(x), sort_keys=True, ensure_ascii=True).encode("ascii"))[:20]


def poison_after(obj, name, d, mode, rng):
    """d 에 쓸 수 없는 관측을 난수로 바꾼다(값은 원 값과 무관 · 양수 가격도 음수가 될 수 있다 — 읽으면 들킨다)."""
    bad = _after_mask(obj, name, d, mode)
    if not bad.any():
        return obj
    out = obj.copy()
    if isinstance(out, pd.Series):
        out = out.astype(float)
        vals = out.to_numpy().copy()
        vals[bad] = rng.normal(0.0, 37.0, int(bad.sum()))
        return pd.Series(vals, index=out.index, name=out.name)
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            col = out[c].astype(float).to_numpy().copy()
            col[bad] = rng.normal(0.0, 37.0, int(bad.sum()))
            out[c] = col
    return out


def _decide_at(decide, args, d):
    if "_d" in inspect.signature(decide).parameters:
        return decide(**args, _d=d)
    out = decide(**args)
    key = pd.Timestamp(d)
    if isinstance(out, (pd.Series, pd.DataFrame)):
        if isinstance(out.index, pd.PeriodIndex):
            key = key.to_period("M")
        try:
            return out.loc[key]
        except KeyError:
            return None
    return out


def lookahead_check(decide, inputs, dates, mode="T1", n=LOOKAHEAD_N, seed=SEED, poison=True):
    """선견 점검 — 결정일 n 개(씨앗 고정 무작위)에서 (1) 모든 입력을 가용 지평에서 자른 것 (2) 지평 뒤 값을 난수로 바꾼 것으로
    다시 낸 결정의 해시가 원 결정 해시와 같아야 한다.
      decide(**{인자: obj}, _d=d) → 결정일 d 의 결정(JSON 꼴) · 또는 _d 를 받지 않으면 결정일 색인 Series/DataFrame
      inputs = {인자: (obj, 가용 이름)} · dates = 결정일 목록(Timestamp)
    돌려주는 것 {"ok", "n", "n_bad", "bad"(≤ 5 · 날짜 · 시험 · 오류 이름 — 값 · 해시는 싣지 않는다), "mode", "seed"}."""
    dates = [pd.Timestamp(x) for x in dates]
    if not dates:
        return {"ok": False, "n": 0, "n_bad": 0, "bad": [], "mode": mode, "seed": seed, "err": "결정일이 없다"}
    for k, (o, nm) in inputs.items():
        avail_rule(nm, mode)                                        # 선언 없는 입력 · 금지 입력은 여기서 멈춘다
    rng = np.random.default_rng(seed)
    pick = np.sort(rng.choice(len(dates), size=min(n, len(dates)), replace=False))
    prng = np.random.default_rng(seed + 1)
    full = {k: o for k, (o, nm) in inputs.items()}
    bad = []
    for i in pick:
        d = dates[int(i)]
        try:
            h0 = decision_hash(_decide_at(decide, full, d))
        except Exception as e:                                      # noqa: BLE001
            bad.append({"d": str(d.date()), "test": "원본", "err": type(e).__name__})
            continue
        tests = [("자르기", {k: asof(o, nm, d, mode) for k, (o, nm) in inputs.items()})]
        if poison:
            tests.append(("난수", {k: poison_after(o, nm, d, mode, prng) for k, (o, nm) in inputs.items()}))
        for how, args in tests:
            try:
                with np.errstate(all="ignore"):
                    h = decision_hash(_decide_at(decide, args, d))
                err = None
            except Exception as e:                                  # noqa: BLE001
                h, err = None, type(e).__name__
            if h != h0:
                bad.append({"d": str(d.date()), "test": how, "err": err})
    return {"ok": not bad, "n": int(len(pick)), "n_bad": len(bad), "bad": bad[:5], "mode": mode, "seed": seed}


def require_no_lookahead(res, label=""):
    if not res.get("ok"):
        raise SystemExit("🚨 선견 점검 실패 %s — %d/%d · 첫 사례 %s · 굽지 않는다." % (label, res.get("n_bad", 0), res.get("n", 0),
                                                                      (res.get("bad") or [{}])[0].get("d")))
    return True


def signal_inputs(mode="T1"):
    """신호 층 입력 한 벌 {인자: (obj, 가용 이름)} — 모두 창 로더(≥ 2005-08-01 · ≤ bake_end). French · EG30 입력은 없다."""
    I = {
        "spy": (spy_tr(), "spy"), "gspc": (gspc_pr(), "gspc"), "rf": (rf_us_monthly(), "rf_us_m"),
        "vix": (vix(), "vix"), "vix3m": (vix3m(published_only=True), "vix3m"),
        "baa10y": (fred_daily("BAA10Y"), "fred_d"), "dfii10": (fred_daily("DFII10"), "fred_d"),
        "ivw": (etf_tr("IVW"), "etf"), "ive": (etf_tr("IVE"), "etf"),
    }
    assert_input_floor(I)
    for k, (o, nm) in I.items():
        avail_rule(nm, mode)
    return I


# ══════════════════════════════════════════════════════════════════════════
#  자료 충실도 대조(개수만 · 값 · 수익을 돌려주지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _month_ret(px):
    m = px.groupby(px.index.to_period("M")).last()
    return (m / m.shift(1) - 1.0).dropna()


def check_spy_vs_sp500tr(tol=0.0025):
    """SPY TR 월 수익 대 ^SP500TR 월 수익 — |차이| ≤ tol 인 달 수(창 안). 개수만."""
    a = _month_ret(spy_tr(end=bake_end()))
    b = _month_ret(sp500tr(end=bake_end()))
    idx = a.index.intersection(b.index)
    idx = idx[(idx >= pd.Period(SCORE_FIRST, "M") - 12) & (idx <= pd.Period(SCORE_LAST, "M"))]
    ok = int((np.abs(a.reindex(idx) - b.reindex(idx)) <= tol).sum())
    return {"n_months": int(len(idx)), "n_within_tol": ok, "tol": tol}


def check_rf_vs_fred(tol=1e-6):
    """rf_monthly 고정 사본의 ȳ_m 대 FRED DGS3MO 달 평균 — |차이| ≤ tol 인 달 수(2005-08 ~ 2026-08). 달 색인 뜻(같은 달 평균)도 이것으로 확인."""
    lab = rf_monthly_lab()
    ybar = (1.0 + lab) ** 12 - 1.0
    fr = dgs3mo_month_mean()
    idx = ybar.index.intersection(fr.index)
    idx = idx[(idx >= pd.Period(INPUT_MIN_MONTH, "M")) & (idx <= pd.Period(SCORE_LAST, "M"))]
    d0 = np.abs(ybar.reindex(idx) - fr.reindex(idx))
    lag = fr.copy()
    lag.index = lag.index + 1
    d1 = np.abs(ybar.reindex(idx) - lag.reindex(idx))
    return {"n_months": int(len(idx)), "n_within_tol_same_month": int((d0 <= tol).sum()), "n_within_tol_lag1": int((d1 <= tol).sum()), "tol": tol}


def check_vix3m_sources(tol=0.011):
    """VIX3M Cboe 1차 대 yfinance(assets.json) — 원천마다 첫 날(커버리지 · VXV 공표일 증빙) · 창 안 겹친 날 수 · |차이| ≤ tol 인 날 수."""
    cf = load_full("cboe/VIX3M")["CLOSE"].dropna()
    A = load_full("lab/assets")
    yv = [(d, v) for d, v in zip(A["dates"], A["px"]["^VIX3M"]) if v is not None]
    c = vix3m(end=bake_end())
    y = vix3m_yf_lab(end=bake_end())
    idx = c.index.intersection(y.index)
    ok = int((np.abs(c.reindex(idx) - y.reindex(idx)) <= tol).sum())
    return {"cboe_first": str(cf.index.min().date()), "cboe_last": str(cf.index.max().date()), "yf_first": yv[0][0] if yv else None,
            "cboe_first_equals_default_pub": str(cf.index.min().date()) == VXV_PUB_DEFAULT,
            "n_common_in_window": int(len(idx)), "n_within_tol": ok, "tol": tol}


def check_baa10y_identity(tol=0.011):
    """BAA10Y = DBAA − DGS10(FRED 정의) — 같은 날 수 · |차이| ≤ tol 인 날 수 · Moody's 계열 지속(마지막 관측 · 가장 긴 빈 평일 수)."""
    b = fred_daily("BAA10Y", end=bake_end())
    a = fred_daily("DBAA", end=bake_end())
    g = fred_daily("DGS10", end=bake_end())
    idx = b.index.intersection(a.index).intersection(g.index)
    ok = int((np.abs(b.reindex(idx) - (a.reindex(idx) - g.reindex(idx))) <= tol).sum())
    out = {"n_common": int(len(idx)), "n_within_tol": ok, "tol": tol}
    for nm, s in (("DBAA", a), ("BAA10Y", b)):
        bd = pd.bdate_range(s.index.min(), s.index.max())
        have = pd.Series(1, index=s.index).reindex(bd).fillna(0).to_numpy()
        run, best = 0, 0
        for v in have:
            run = run + 1 if v == 0 else 0
            best = max(best, run)
        out[nm] = {"first": str(s.index.min().date()), "last": str(s.index.max().date()), "n_obs": int(len(s)), "max_gap_bdays": int(best),
                   "covers_score_window": bool(s.index.min() <= pd.Timestamp(INPUT_MIN) + pd.Timedelta(days=7) and s.index.max() >= pd.Timestamp("2026-08-28"))}
    return out


# ── ALFRED 판(SN-1.3) ─────────────────────────────────────────────────────
def alfred_key(sid, vdate):
    return "alfred/%s@%s" % (sid, vdate)


def alfred_url(sid, vdate):
    return "https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=%s&vintage_date=%s" % (sid, vdate)


def alfred_pin(sid, vdate, fetch=True):
    key = alfred_key(sid, vdate)
    p = cache_raw("us/alfred/%s@%s.csv" % (sid, vdate))
    if os.path.exists(p) and read_meta(key):
        return "고정본 있음"
    m0 = read_meta(key)
    if m0 and m0.get("error"):
        return "🚨 %s(기록 · %s)" % (m0["error"], m0.get("tried_at"))   # 그 판 날짜에 계열이 없었다 — 다시 묻지 않는다
    if not fetch:
        return "없음(받지 않음)"
    try:
        blob, info = http_get(alfred_url(sid, vdate), UA_PY)
    except urllib.error.HTTPError as e:
        _write_meta(key, {"key": key, "url": alfred_url(sid, vdate), "error": "HTTP %d" % e.code, "tried_at": _now()})
        return "🚨 HTTP %d" % e.code
    sniff("alfred", blob)
    _write_bytes(p, blob)
    _write_meta(key, {"key": key, "url": alfred_url(sid, vdate), "origin": "live", "pinned_at": _now(), "sha256": sha256_bytes(blob),
                      "bytes": len(blob), "license": LIC["alfred"]})
    return "들임"


def _series_hash(s):
    lines = "".join("%s,%s\n" % (i.strftime("%Y-%m-%d"), ("%.6g" % v) if v == v else ".") for i, v in s.items())
    return sha256_bytes(lines.encode("ascii"))[:16]


def alfred_compare(vint_series, window_start=INPUT_MIN):
    """판 비교(개수 · 해시만) — vint_series = {판 날짜: Series}. 가장 이른 판 날짜 앞 창의 해시가 모든 판에서 같은가 ·
    이웃 판 쌍마다 겹친 관측(앞 판 날짜 앞)에서 값이 다른 날 수. 돌려주는 것 {window, sha_by_vintage, n_obs_common, n_diff_pairs, revised}."""
    vs = sorted(vint_series)
    v0 = vs[0]
    vint_series = {v: s.dropna() for v, s in vint_series.items()}      # «.»(휴장 표지)는 판마다 실리는 방식이 달라 비교에서 뺀다
    a = pd.Timestamp(window_start)
    z = min(pd.Timestamp(v0) - pd.Timedelta(days=1), vint_series[v0].index.max())
    shas, n_common = {}, None
    for v in vs:
        s = vint_series[v]
        w = s.loc[(s.index >= a) & (s.index <= z)]
        shas[v] = _series_hash(w)
        n_common = len(w) if n_common is None else min(n_common, len(w))
    pairs = {}
    for x, y in zip(vs[:-1], vs[1:]):
        sx, sy = vint_series[x], vint_series[y]
        zx = pd.Timestamp(x) - pd.Timedelta(days=1)
        idx = sx.index[(sx.index >= a) & (sx.index <= zx)].intersection(sy.index)
        dx, dy = sx.reindex(idx), sy.reindex(idx)
        diff = int(((np.abs(dx - dy) > 1e-9) | (dx.isna() != dy.isna())).sum())
        pairs["%s→%s" % (x, y)] = {"n_overlap": int(len(idx)), "n_diff": diff}
    revised = len(set(shas.values())) > 1 or any(p["n_diff"] for p in pairs.values())
    return {"window": [str(a.date()), str(z.date())], "sha_by_vintage": shas, "n_obs_common": int(n_common or 0), "n_diff_pairs": pairs,
            "revised": bool(revised)}


def alfred_check(series=ALFRED_SERIES, vintages=ALFRED_VINTAGES, fetch=True):
    """SN-1.3 — DBAA · DGS10 · BAA10Y 의 ALFRED 판(세 날짜 이상) 해시 대조 + 현재 FRED 판과 마지막 판의 겹친 관측 대조(개수만).
    개정이 보이면(revised) 등록 전 기계적 항목 «ALFRED 첫 공표 판» 으로 넘긴다(F0 · multiplicity.discipline)."""
    out = {}
    for sid in series:
        got = {}
        errs = {}
        for v in vintages:
            st = alfred_pin(sid, v, fetch=fetch)
            p = cache_raw("us/alfred/%s@%s.csv" % (sid, v))
            if os.path.exists(p):
                with open(p, "rb") as f:
                    s = parse_fred_csv(f.read())
                got[v] = s if isinstance(s, pd.Series) else s.iloc[:, 0]
            else:
                errs[v] = st
        res = {"n_vintages": len(got), "failed": errs}
        if len(got) >= 2:
            res.update(alfred_compare(got))
            cur = fred_daily(sid, start=INPUT_MIN, end=None) if sid in ("DBAA", "DGS10", "BAA10Y") else None
            if cur is not None:
                lv = max(got)
                sl = got[lv]
                zl = pd.Timestamp(lv) - pd.Timedelta(days=7)
                idx = sl.index[(sl.index >= pd.Timestamp(INPUT_MIN)) & (sl.index <= zl)].intersection(cur.index)
                res["current_vs_last_vintage"] = {"n_overlap": int(len(idx)),
                                                  "n_diff": int((np.abs(sl.reindex(idx) - cur.reindex(idx)) > 1e-9).sum())}
        res["ok_three_plus"] = len(got) >= 3
        out[sid] = res
    return out


# ══════════════════════════════════════════════════════════════════════════
#  요약 · 명세(data/_xb_manifest.json — 값 계열 없음) · 판 점검
# ══════════════════════════════════════════════════════════════════════════
def summarize(key):
    """원천 하나의 모양 — 행 수 · 처음/끝 · 창 안 행 수 · 빈 칸 수(값 없음)."""
    R = registry()
    ds = R[key]
    obj = load_full(key)
    k = ds["kind"]
    if k == "french":
        blk = obj["blocks"]["vw_m" if "vw_m" in obj["blocks"] else ("m" if "m" in obj["blocks"] else "d")]
        idx = blk.index
        return {"rows": int(len(idx)), "first": str(idx.min())[:10], "last": str(idx.max())[:10], "crsp": obj["crsp"], "blocks": len(obj["blocks"]),
                "rows_in_window": int(((idx >= (pd.Period(INPUT_MIN_MONTH, "M") if isinstance(idx, pd.PeriodIndex) else pd.Timestamp(INPUT_MIN)))).sum())}
    if k == "lab":
        if key == "lab/rf_monthly":
            ks = sorted(obj["monthly"])
            return {"rows": len(ks), "first": ks[0], "last": ks[-1], "source": obj.get("series_id"), "fetched": obj.get("fetched")}
        return {"rows": int(obj.get("n_days") or len(obj.get("dates", []))), "first": obj["dates"][0], "last": obj["dates"][-1],
                "as_of": obj.get("as_of")}
    s = obj[ds["col"]] if isinstance(obj, pd.DataFrame) else obj
    s = pd.to_numeric(s, errors="coerce")
    idx = s.index
    win = s.loc[(idx >= pd.Timestamp(INPUT_MIN))]
    return {"rows": int(len(s)), "first": str(idx.min().date()), "last": str(idx.max().date()), "n_nan": int(s.isna().sum()),
            "rows_in_window": int(len(win)), "n_nan_in_window": int(win.isna().sum())}


def build_manifest(write=True):
    """data/_xb_manifest.json — 원천 판(URL · 받은 때 · SHA-256 · 바이트 · 행 수 · 처음/끝) · 가용 표 · 창 · VXV 규칙 · ALFRED 판 해시.
    값 계열 · 수익 · 통계는 없다(public_safe 통과 · 20년 수치 없음)."""
    R = registry()
    src = {}
    for key, ds in R.items():
        m = read_meta(key)
        if not m:
            src[key] = {"pinned": False}
            continue
        try:
            summ = summarize(key)
        except Exception as e:                                        # noqa: BLE001
            summ = {"error": type(e).__name__}
        src[key] = {"url": ds["url"], "origin": m.get("origin"), "pinned_at": m.get("pinned_at"), "sha256": m.get("sha256"), "bytes": m.get("bytes"),
                    "seed_fetched_at": (m.get("seed_meta") or {}).get("fetched_at") or (m.get("seed_meta") or {}).get("pinned_at"),
                    "yfinance": m.get("yfinance") or (m.get("seed_meta") or {}).get("yfinance"), "license": ds["license"], "use": ds["use"],
                    "summary": summ}
    alf = {}
    for sid in ALFRED_SERIES:
        for v in ALFRED_VINTAGES:
            m = read_meta(alfred_key(sid, v))
            if m:
                alf[alfred_key(sid, v)] = {"url": m.get("url"), "sha256": m.get("sha256"), "pinned_at": m.get("pinned_at"), "error": m.get("error")}
    doc = {
        "note": ("배치 X 자료 명세(build/x_data.py --manifest) — 원천 판 · 해시 · 행 수 · 처음/끝 날짜 · 가용 늦춤 규칙 · 창만. 원자료 · 값 계열 · 수익 · "
                 "20년 수치는 없다(원자료는 저장소 밖 %TEMP%/xbatch_cache/raw · 20년 산출은 캐시 out/ 에만). 국외 원천은 x_intl 명세 절이 더한다."),
        "generated_at": _now(),
        "cache_root": "%TEMP%/xbatch_cache",
        "windows": {"score": [SCORE_FIRST, SCORE_LAST], "n_score": N_SCORE, "input_min": INPUT_MIN, "warmup": list(WARMUP),
                    "halves": [list(h) for h in HALVES], "out_of_literature": list(OUT_OF_LIT), "gfc_excluded_report": list(GFC_EXCL),
                    "full_years": list(FULL_YEARS), "s_layer": list(S_WIN), "s_pit_from": S_PIT_FROM, "public_from": PUBLIC_FROM,
                    "max_years_public": MAX_YEARS_PUBLIC, "first_active_min": dict(MIN_WARMUP_BY_ELEMENT), "bake_end_t1": str(bake_end().date())},
        "availability": {k: {m: v[m] for m in MODES} | {"freq": v["freq"], "note": v["note"]} for k, v in AVAIL.items()},
        "vxv_publication": {"default": VXV_PUB_DEFAULT, "in_force": vxv_pub_date(), "rule": "Cboe 공식 VIX3M CSV 시작일 · Cboe 1차 공고로 더 이른 날을 증명할 때만 앞당긴다(SN-1.1)"},
        "french": {"crsp": CRSP_WANT, "growth_proxies": {k: list(v) for k, v in GROWTH_PROXIES.items()}, "d_proxy": list(D_PROXY),
                   "d_proxy_fallback": list(D_PROXY_FALLBACK), "min_firms": MIN_FIRMS},
        "frozen_calls": {"v_data.parse_french_blob": V_DATA_BLOB},
        "sources": src,
        "alfred": {"series": list(ALFRED_SERIES), "vintages": list(ALFRED_VINTAGES), "files": alf},
        "guards": {"repo_allowed": list(REPO_ALLOWED), "repo_allowed_globs": list(REPO_ALLOWED_GLOBS), "cache_only_marker": "x_data.CACHE_ONLY_KEY(문자열은 여기 싣지 않는다 — site_guard 표식)",
                   "forbidden_read_marks": ("x_data.FORBIDDEN_READ_MARKS — 배치 T 산출 폴더(tbatch_cache/out)와 배치 T 산출 파일 넷(이름은 배치 T 사이트 경계 표식이라 "
                                            "여기 싣지 않는다 · T01 C:bearonly 저장값을 열지 않는다)"),
                   "signal_layer_forbidden_marks": list(EG_FILE_MARKS)},
    }
    if os.path.exists(MANIFEST):                                   # 다른 단계가 더한 절(x_intl «intl» 등)은 그대로 둔다
        try:
            with io.open(MANIFEST, encoding="utf-8") as f:
                old = json.load(f)
            for k, v in old.items():
                if k not in doc:
                    doc[k] = v
        except Exception:                                          # noqa: BLE001
            pass
    bad = public_safe(doc)
    if bad:
        raise SystemExit("🚨 명세가 공개 안전 점검에 걸렸다: %s" % bad[:3])
    if write:
        repo_write_json("data/_xb_manifest.json", doc)
    return doc


def check_pins():
    """굽기 전 관문 — 고정본 SHA == 명세 · French 판 CRSP 202608 한 판."""
    if not os.path.exists(MANIFEST):
        return {"ok": False, "bad": ["명세 없음 — --manifest"]}
    with io.open(MANIFEST, encoding="utf-8") as f:
        M = json.load(f)
    R = registry()
    bad = []
    for key, ent in M.get("sources", {}).items():
        if not ent.get("sha256"):
            bad.append("%s: 명세에 SHA 없음" % key)
            continue
        p = cache_raw(R[key]["rel"])
        if not os.path.exists(p):
            bad.append("%s: 고정본 없음" % key)
        elif sha256_file(p) != ent["sha256"]:
            bad.append("%s: SHA 가 명세와 다르다" % key)
    for key, ent in M.get("alfred", {}).get("files", {}).items():
        if ent.get("sha256"):
            sid, v = key.split("/", 1)[1].split("@")
            p = cache_raw("us/alfred/%s@%s.csv" % (sid, v))
            if not os.path.exists(p) or sha256_file(p) != ent["sha256"]:
                bad.append("%s: ALFRED 판 SHA 불일치" % key)
    crsp = {M["sources"][k].get("summary", {}).get("crsp") for k in M.get("sources", {}) if k.startswith("french/")}
    if crsp - {CRSP_WANT}:
        bad.append("French 판 섞임: %s" % sorted(map(str, crsp)))
    return {"ok": not bad, "bad": bad[:10], "n_sources": len(M.get("sources", {}))}


def pin_all(fetch=True):
    R = registry()
    out = {}
    for key in R:
        try:
            out[key] = pin(key, fetch=fetch, R=R)
        except Exception as e:                                        # noqa: BLE001
            out[key] = "🚨 %s: %s" % (type(e).__name__, str(e)[:120])
    return out


# ══════════════════════════════════════════════════════════════════════════
#  연기 시험(실자료 · 모양만) — 통계 · 값을 찍지 않는다
# ══════════════════════════════════════════════════════════════════════════
def _shape(x):
    if isinstance(x, (pd.Series, pd.DataFrame)):
        idx = x.index
        return {"n": int(len(x)), "first": str(idx.min())[:10] if len(idx) else None, "last": str(idx.max())[:10] if len(idx) else None,
                "n_nan": int(np.asarray(pd.isna(x)).sum())}
    return type(x).__name__


def _neutral_decide(spy, gspc, rf, vix, vix3m, baa10y, dfii10, ivw, ive, _d):
    """연기 전용 중립 결정(전략 · 신호가 아니다) — 각 입력의 가용 마지막 관측 · 365일 중앙 · 252일 비 · 12개월 창 원소 수.
    값은 해시로만 쓰고 찍지 않는다. 선견 틀이 자르기 · 난수에 흔들리지 않는지만 본다."""
    def lv(s, nm):
        return last_value(s, nm, _d, "T1")
    b = asof(baa10y, "fred_d", _d)
    b = b.loc[b.index > pd.Timestamp(_d) - pd.Timedelta(days=365)]
    g = asof(ivw, "etf", _d).tail(253)
    e = asof(ive, "etf", _d).tail(253)
    m = asof(spy, "spy", _d)
    mm = m.groupby(m.index.to_period("M")).last().tail(13)
    return {"spy": lv(spy, "spy"), "gspc": lv(gspc, "gspc"), "rf": lv(rf, "rf_us_m"), "vix": lv(vix, "vix"), "vix3m": lv(vix3m, "vix3m"),
            "baa": lv(baa10y, "fred_d"), "baa_med": float(b.median()) if len(b) else None, "dfii": lv(dfii10, "fred_d"),
            "gv": (float(g.iloc[-1] / g.iloc[0]) / float(e.iloc[-1] / e.iloc[0])) if len(g) > 1 and len(e) > 1 else None,
            "n12": int(len(mm))}


def smoke(n_lookahead=LOOKAHEAD_N, do_fetch=True, do_alfred=True):
    t0 = time.time()
    rep = {"started": _now(), "cache": cache_guard(), "timings": {}}
    install_read_guard(signal_layer=True)
    install_write_guard(ROOT)
    t = time.time()
    rep["pin"] = pin_all(fetch=do_fetch)
    rep["timings"]["pin_s"] = round(time.time() - t, 1)
    rep["summary"] = {}
    for key in registry():
        try:
            rep["summary"][key] = summarize(key)
        except Exception as e:                                        # noqa: BLE001
            rep["summary"][key] = {"error": "%s: %s" % (type(e).__name__, str(e)[:120])}
    t = time.time()
    dd = decision_days(INPUT_MIN_MONTH, SCORE_LAST)
    rep["calendar"] = {"n_trading_days_window": int(((trading_days() >= pd.Timestamp(INPUT_MIN)) & (trading_days() <= bake_end())).sum()),
                       "n_decision_days": int(len(dd)), "first_decision": str(dd.iloc[0].date()), "last_decision": str(dd.iloc[-1].date()),
                       "bake_end_t1": str(bake_end().date()), "t1_of_first_scored_decision": str(t_plus_1(dd.loc[pd.Period("2006-08", "M")]).date())}
    scored = [str(p) for p in dd.index if pd.Period(SCORE_FIRST, "M") <= p + 1 <= pd.Period(SCORE_LAST, "M")]
    rep["calendar"]["n_scored_holding_months"] = assert_scored_months([str(pd.Period(p, "M") + 1) for p in scored])["n"]
    I = signal_inputs("T1")
    rep["loaders"] = {k: _shape(o) for k, (o, nm) in I.items()}
    rep["loaders"].update({"sp500tr": _shape(sp500tr()), "iwf": _shape(etf_tr("IWF")), "dgs3mo": _shape(fred_daily("DGS3MO")),
                           "dbaa": _shape(fred_daily("DBAA")), "dgs10": _shape(fred_daily("DGS10")),
                           "vix3m_unpublished_too": _shape(vix3m()), "ff3_m": _shape(ff3("m")), "ff3_d": _shape(ff3("d")),
                           "french_last_month": french_last_month()})
    for nm in GROWTH_PROXIES:
        rep["loaders"]["G:" + nm] = _shape(growth_proxy(nm))
    rep["loaders"]["D_proxy"] = _shape(d_proxy())
    rep["loaders"]["D_proxy_fallback"] = _shape(d_proxy(True))
    rep["loaders"]["p6_d:BIG LoBM"] = _shape(french_leg("p6_d", "BIG LoBM", daily=True))
    rep["floor"] = assert_input_floor({**I, "ff3_m": ff3("m"), "D": d_proxy(), **{"G:" + k: growth_proxy(k) for k in GROWTH_PROXIES}})
    rep["timings"]["loaders_s"] = round(time.time() - t, 1)
    t = time.time()
    rep["fidelity_counts"] = {"spy_vs_sp500tr": check_spy_vs_sp500tr(), "rf_lab_vs_fred": check_rf_vs_fred(),
                              "vix3m_cboe_vs_yf": check_vix3m_sources(), "baa10y_identity_moodys": check_baa10y_identity(),
                              "vxv_pub_date_in_force": vxv_pub_date()}
    rep["timings"]["fidelity_s"] = round(time.time() - t, 1)
    if do_alfred:
        t = time.time()
        rep["alfred"] = alfred_check(fetch=do_fetch)
        rep["timings"]["alfred_s"] = round(time.time() - t, 1)
    t = time.time()
    dates = list(dd.loc[dd.index >= pd.Period("2006-08", "M")])

    def _neutral_d0(spy, vix, vix3m, _d):                     # D0 행 — VIX · VIX3M 은 d_m − 1 거래일
        return {"spy": last_value(spy, "spy", _d, "D0"), "vix": last_value(vix, "vix", _d, "D0"), "vix3m": last_value(vix3m, "vix3m", _d, "D0")}
    rep["lookahead"] = {"T1": lookahead_check(_neutral_decide, I, dates, mode="T1", n=n_lookahead),
                        "D0": lookahead_check(_neutral_d0, {k: I[k] for k in ("spy", "vix", "vix3m")}, dates, mode="D0", n=n_lookahead)}
    rep["timings"]["lookahead_s"] = round(time.time() - t, 1)
    _GUARD["read_on"] = False                                  # 사이트 점검은 data/*.json(EG30 파일 포함)의 표식만 훑는다 — 신호 층 밖
    rep["site_guard"] = {k: v for k, v in site_guard().items() if k in ("ok", "n_bad", "n_files", "n_scanned", "bad")}
    _GUARD["read_on"] = True
    rep["read_guard"] = {"n_opened": len(opened_paths()), "forbidden_opened": sorted({p for p in opened_paths()
                                                                                       if any(m.lower() in p.replace("\\", "/").lower() for m in FORBIDDEN_READ_MARKS + EG_FILE_MARKS)})[:5]}
    D, P = zigzag_inputs()
    rep["loaders"]["zigzag_inputs"] = {"n": len(D), "first": D[0], "last": D[-1], "n_none": sum(1 for p in P if p is None)}
    rep["timings"]["total_s"] = round(time.time() - t0, 1)
    guard_off()
    p = os.path.join(cache_guard(), "meta", "_smoke_x_data.json")          # 모양 · 개수 · 참/거짓 · 시간만(값 · 통계 없음)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rep, ensure_ascii=False, indent=1, default=str) + "\n")
    return rep


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험(망 · 캐시 · 실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _syn_days(a="2005-06-01", b="2026-09-10"):
    d = pd.bdate_range(a, b)
    hol = {pd.Timestamp(x) for x in ("2006-07-04", "2008-12-25", "2016-09-05", "2020-11-26", "2026-09-07")}
    return pd.DatetimeIndex([x for x in d if x not in hol])


def _st_guards():
    with tempfile.TemporaryDirectory() as td:
        repo = os.path.join(td, "repo")
        os.makedirs(os.path.join(repo, "data"))
        try:
            cache_guard(os.path.join(repo, "cache"), repo)
            raise AssertionError("저장소 안 캐시가 통과했다")
        except SystemExit:
            pass
        assert cache_guard(os.path.join(td, "cache"), repo)
        # 쓰기 가드(감사 고리) — 허용 밖 쓰기 · 이름 바꾸기 막음 · 허용 파일 · __pycache__ · 저장소 밖은 통과
        _ensure_hook()
        old = dict(_GUARD)
        try:
            _GUARD["write_root"], _GUARD["write_on"] = os.path.abspath(repo), True
            for bad in ("data/_xbatch_M.json", "data/x.json", "build/x_out.md"):
                try:
                    with open(os.path.join(repo, *bad.split("/")), "w", encoding="utf-8") as f:
                        f.write("1")
                    raise AssertionError("허용 밖 쓰기 통과: %s" % bad)
                except PermissionError:
                    pass
            ok_p = os.path.join(repo, "data", "_xb_f0.json")
            with open(ok_p, "w", encoding="utf-8") as f:
                f.write("{}")
            os.makedirs(os.path.join(repo, "build", "__pycache__"), exist_ok=True)
            with open(os.path.join(repo, "build", "__pycache__", "x.pyc"), "wb") as f:
                f.write(b"0")
            outside = os.path.join(td, "out.json")
            with open(outside, "w", encoding="utf-8") as f:
                f.write("{}")
            try:
                os.replace(outside, os.path.join(repo, "data", "leak.json"))
                raise AssertionError("이름 바꾸기 통과")
            except PermissionError:
                pass
            with open(ok_p, encoding="utf-8") as f:
                assert f.read() == "{}"
            # 읽기 가드
            _GUARD["read_marks"], _GUARD["read_on"] = FORBIDDEN_READ_MARKS + EG_FILE_MARKS, True
            fake = os.path.join(td, "tbatch_cache", "out")
            os.makedirs(fake)
            _GUARD["read_on"] = False
            with open(os.path.join(fake, "_tbatch.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            with open(os.path.join(td, "_qbatch.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            _GUARD["read_on"] = True
            for p in (os.path.join(fake, "_tbatch.json"), os.path.join(td, "_qbatch.json")):
                try:
                    open(p, encoding="utf-8").close()
                    raise AssertionError("금지 읽기 통과: %s" % p)
                except PermissionError:
                    pass
        finally:
            _GUARD.update({k: old[k] for k in ("write_on", "write_root", "read_on", "read_marks")})
            _GUARD["opened"] = [p for p in _GUARD["opened"] if not _inside(p, td)]
    # 공개 안전
    assert not public_safe({"window": ["2016-09", "2026-08"], "mean_delta": 0.123, "n": 120})
    assert public_safe({"window": ["2006-09", "2026-08"], "mean_delta": 0.123})
    assert not public_safe({"window": ["2006-09", "2026-08"], "n": 240, "pass": True, "label": "x", "tol": 0.0025, "coverage_min": 1.0})
    assert public_safe({"window": ["2006-09", "2026-08"], "n": 240, "on_share": 0.14})          # 20년 창 켜짐 비율은 저장소 밖(사용자 20년 규칙)
    assert public_safe({"window": ["2006-08", "2026-07"], "state_agree": 0.97})                # 20년 창 상태 일치율도
    assert not public_safe({"window": ["2016-09", "2026-08"], "on_share": 0.14, "mean_delta": 0.1})   # 뒤 10년 창은 허용
    assert public_safe({"x": {CACHE_ONLY_KEY: True}})
    assert public_safe({"s": [1, 2, 3, 4, 5]}) and not public_safe({"s": [1, 2, 3, 4]})
    assert public_safe({"M": {"window": ["2006-09", "2026-08"], "gates": {"M-C1": {"t": 1.9}}}})
    assert not public_safe({"M": {"window": ["2006-09", "2026-08"], "gates": {"M-C1": {"pass": False}}}})
    with tempfile.TemporaryDirectory() as td:
        try:
            repo_write_json("data/other.json", {"a": 1}, root=td)
            raise AssertionError("허용 밖 repo_write_json 통과")
        except PermissionError:
            pass
        try:
            repo_write_json("data/_xb_f0.json", mark_cache_only({"a": 1}), root=td)
            raise AssertionError("20년 표지 통과")
        except PermissionError:
            pass
        repo_write_json("data/_xb_f0.json", {"n": 3, "window": ["2006-09", "2026-08"]}, root=td)
        try:
            repo_write_text("build/PREREG-2026-10-16-XBATCH-RESULT.md", "x %s y" % CACHE_ONLY_KEY, root=td)
            raise AssertionError("md 표지 통과")
        except PermissionError:
            pass
        repo_write_text("build/PREREG-2026-10-16-XBATCH-RESULT.md", "ok", root=td)
    return "cache_guard · 쓰기 가드(허용 밖 · 이름 바꾸기 · __pycache__ · 저장소 밖) · 읽기 가드(tbatch out · EG30 표식) · public_safe(표지 · 값 계열 · 20년 창 실수) · repo_write"


def _st_windows():
    ok = assert_scored_months([str(p) for p in pd.period_range("2006-09", "2026-08", freq="M")])
    assert ok["n"] == 240 and ok["first"] == "2006-09"
    for bad in (["2006-08", "2006-09"], ["2026-09"], ["2010-01", "2010-01"]):
        try:
            assert_scored_months(bad)
            raise AssertionError("창 위반 통과 %s" % bad)
        except AssertionError as e:
            if "통과" in str(e):
                raise
    s_ok = pd.Series(1.0, index=pd.bdate_range("2005-08-01", "2006-01-01"))
    s_bad = pd.Series(1.0, index=pd.bdate_range("2005-07-29", "2006-01-01"))
    m_ok = pd.Series(1.0, index=pd.period_range("2005-08", "2006-01", freq="M"))
    m_bad = pd.Series(1.0, index=pd.period_range("2005-07", "2006-01", freq="M"))
    assert assert_input_floor({"a": s_ok, "b": (m_ok, "rf_us_m")})
    for bad in (s_bad, m_bad):
        try:
            assert_input_floor({"x": bad})
            raise AssertionError("입력 하한 위반 통과")
        except AssertionError as e:
            if "통과" in str(e):
                raise
    long = pd.Series(1.0, index=pd.bdate_range("2004-01-01", "2027-01-01"))
    c = clip(long, INPUT_MIN, "2026-09-01")
    assert c.index.min() >= pd.Timestamp(INPUT_MIN) and c.index.max() <= pd.Timestamp("2026-09-01")
    for e, want in (("2026-09-01", "2026-08"), ("2026-08-31", "2026-08"), ("2026-08-30", "2026-07"), ("2026-08", "2026-08")):
        assert str(_last_complete_month(e)) == want, (e, _last_complete_month(e))
    lm = pd.Series(1.0, index=pd.period_range("2004-01", "2027-01", freq="M"))
    cm = clip(lm, INPUT_MIN_MONTH, "2026-09-01")
    assert str(cm.index.min()) == "2005-08" and str(cm.index.max()) == "2026-08"      # 진행 중인 2026-09 달 값(9월 평균)은 굽기에 없다
    assert assert_first_active("X-GVTREND", "2006-12")
    try:
        assert_first_active("X-BLR", "2010-07")
        raise AssertionError("BLR 첫 활성 위반 통과")
    except AssertionError as e:
        if "통과" in str(e):
            raise
    return "채점 보유월 2006-09 ~ 2026-08(240) · 입력 하한 2005-08-01(일 · 달) · 자르기 · 첫 활성 하한"


def _st_calendar_avail():
    set_calendar(_syn_days())
    try:
        dd = decision_days("2005-08", "2026-08")
        assert len(dd) == 253 and str(dd.index[0]) == "2005-08" and str(dd.index[-1]) == "2026-08"
        assert dd.loc[pd.Period("2026-08", "M")] == pd.Timestamp("2026-08-31")
        assert t_plus_1("2026-08-31") == pd.Timestamp("2026-09-01")
        assert t_plus_1("2016-09-02") == pd.Timestamp("2016-09-06")              # 합성 휴장 2016-09-05
        assert prev_session("2016-09-06") == pd.Timestamp("2016-09-02")
        assert bake_end() == pd.Timestamp("2026-09-01")
        hs = holding_span("2006-09", "T1")
        assert hs == (pd.Timestamp("2006-09-01"), pd.Timestamp("2006-10-02"))
        assert holding_span("2006-09", "D0") == (pd.Timestamp("2006-08-31"), pd.Timestamp("2006-09-29"))
        # 가용: VIX D0 = 앞 거래일 · FRED = 앞 평일 · rf 달 · French 신호 금지
        assert cutoff("vix", "2016-09-06", "D0") == pd.Timestamp("2016-09-02")
        assert cutoff("vix", "2016-09-06", "T1") == pd.Timestamp("2016-09-06")
        assert cutoff("fred_d", "2020-06-01", "T1") == pd.Timestamp("2020-05-29")
        assert cutoff("rf_us_m", "2020-06-30", "T1") == pd.Period("2020-06", "M")
        for nm, md in (("french", "T1"), ("sp500tr", "T1"), ("vix3m_yf", "D0")):
            try:
                avail_rule(nm, md)
                raise AssertionError("금지 입력 통과 %s" % nm)
            except PermissionError:
                pass
        try:
            avail_rule("undeclared", "T1")
            raise AssertionError("선언 없는 입력 통과")
        except KeyError:
            pass
        assert avail_rule("french", "G") == "month_le"
        s = pd.Series(np.arange(10.0), index=pd.bdate_range("2020-05-25", periods=10))
        assert asof(s, "fred_d", "2020-06-01").index.max() == pd.Timestamp("2020-05-29")
    finally:
        set_calendar(None)
    return "결정일 253(2005-08 ~ 2026-08) · T+1 · 앞 거래일 · bake_end 2026-09-01 · 보유 구간 T1/D0 · 가용 규칙(VIX D0 = d_m−1 · FRED d_m−1 영업일 · rf 달) · 금지 · 미선언"


def _syn_world(seed=7):
    rng = np.random.default_rng(seed)
    days = _syn_days()
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(days)))), index=days)
    rf = pd.Series(0.002, index=pd.period_range("2005-08", "2026-09", freq="M"))
    fred = pd.Series(2.0 + np.cumsum(rng.normal(0, 0.02, len(days))), index=days)
    vx = pd.Series(18 + np.abs(np.cumsum(rng.normal(0, 0.3, len(days)))), index=days)
    return days, px, rf, fred, vx


def _st_lookahead():
    days, px, rf, fred, vx = _syn_world()
    set_calendar(days)
    try:
        dd = decision_days("2006-08", "2026-07")
        dates = list(dd)

        def bear(spy, rf, _d):                                 # BEAR 꼴(합성) — d_m 까지 자료만
            m = asof(spy, "spy", _d)
            mm = m.groupby(m.index.to_period("M")).last()
            r = (mm / mm.shift(1) - 1).dropna()
            r = r.loc[r.index <= pd.Timestamp(_d).to_period("M")]
            ex = r - asof(rf, "rf_us_m", _d).reindex(r.index)
            return int(ex.tail(12).mean() < 0 and ex.iloc[-1] < 0)

        def bear_leak(spy, rf, _d):                            # 선견: 결정일 다음 날 가격을 본다
            j = spy.index.searchsorted(pd.Timestamp(_d), side="right")
            nxt = float(spy.iloc[j]) if j < len(spy) else 0.0
            return int(nxt > float(asof(spy, "spy", _d).iloc[-1]))

        def cred(baa, _d):                                     # 365일 중앙 — FRED d_m − 1 영업일
            b = asof(baa, "fred_d", _d)
            w = b.loc[b.index > pd.Timestamp(_d) - pd.Timedelta(days=365)]
            return int(b.iloc[-1] > w.median())

        def cred_leak(baa, _d):                                # 선견: FRED 를 d_m 당일 값으로
            b = baa.loc[baa.index <= pd.Timestamp(_d)]
            return float(b.iloc[-1])

        def vts_d0(vix, _d):
            return float(last_value(vix, "vix", _d, "D0"))

        def vts_d0_leak(vix, _d):                               # D0 에서 d_m VIX(16:15)를 쓴다
            return float(vix.loc[vix.index <= pd.Timestamp(_d)].iloc[-1])

        def vec(spy, rf):                                        # 벡터판(_d 없음 · 결정일 색인 Series)
            mm = spy.groupby(spy.index.to_period("M")).last()
            r = (mm / mm.shift(1) - 1).dropna()
            ex = r - rf.reindex(r.index)
            sig = ((ex.rolling(12).mean() < 0) & (ex < 0)).astype(int)
            last = spy.groupby(spy.index.to_period("M")).apply(lambda s: s.index.max())
            return pd.Series(sig.to_numpy(), index=pd.DatetimeIndex(last.reindex(sig.index).to_numpy()))

        r1 = lookahead_check(bear, {"spy": (px, "spy"), "rf": (rf, "rf_us_m")}, dates, n=40)
        assert r1["ok"] and r1["n"] == 40, r1
        r2 = lookahead_check(bear_leak, {"spy": (px, "spy"), "rf": (rf, "rf_us_m")}, dates, n=40)
        assert not r2["ok"] and r2["n_bad"] > 0, r2
        r3 = lookahead_check(cred, {"baa": (fred, "fred_d")}, dates, n=40)
        assert r3["ok"], r3
        r4 = lookahead_check(cred_leak, {"baa": (fred, "fred_d")}, dates, n=40)
        assert not r4["ok"], r4
        r5 = lookahead_check(vts_d0, {"vix": (vx, "vix")}, dates, mode="D0", n=40)
        assert r5["ok"], r5
        r6 = lookahead_check(vts_d0_leak, {"vix": (vx, "vix")}, dates, mode="D0", n=40)
        assert not r6["ok"], r6
        r7 = lookahead_check(vts_d0_leak, {"vix": (vx, "vix")}, dates, mode="T1", n=40)
        assert r7["ok"], r7                                    # T1 에서는 d_m VIX 를 써도 된다
        r8 = lookahead_check(vec, {"spy": (px, "spy"), "rf": (rf, "rf_us_m")}, dates, n=30)
        assert r8["ok"], r8
        try:
            lookahead_check(cred, {"baa": (fred, "french")}, dates, n=3)
            raise AssertionError("French 신호 입력 통과")
        except PermissionError:
            pass
        assert decision_hash({"a": 0.1 + 0.2}) == decision_hash({"a": 0.3}) and decision_hash([1, 2]) != decision_hash([2, 1])
        assert decision_hash(float("nan")) == decision_hash(np.nan)
    finally:
        set_calendar(None)
    return "선견 틀 — BEAR 꼴 · CRED(365일 · d_m−1 영업일) · VTS D0(d_m−1) 통과 · 다음 날 가격 · FRED 당일 · D0 당일 VIX 선견 잡음 · 벡터판 · French 금지 · 결정 해시"


def _st_parsers_rf():
    fred = b"observation_date,BAA10Y\n2020-01-01,.\n2020-01-02,2.10\n2020-01-03,\n2020-01-06,2.12\n"
    s = parse_fred_csv(fred)
    assert len(s) == 4 and int(s.isna().sum()) == 2 and s.name == "BAA10Y"
    sniff("fred", fred)
    try:
        sniff("fred", b"<html>Just a moment...")
        raise AssertionError("봇 검사 페이지 통과")
    except ValueError:
        pass
    cb = b"DATE,OPEN,HIGH,LOW,CLOSE\n09/18/2009,26.1,26.9,25.2,25.9\n09/21/2009,26.0,26.5,25.1,26.2\n"
    c = parse_cboe_csv(cb)
    assert list(c.columns) == ["OPEN", "HIGH", "LOW", "CLOSE"] and c.index[0] == pd.Timestamp("2009-09-18")
    yf = b"Date,Open,High,Low,Close,Adj Close,Volume\n2020-01-02,1,1,1,1,0.9,5\n2020-01-03,1,1,1,1.1,1.0,5\n"
    y = parse_yf_csv(yf)
    assert y["Adj Close"].iloc[-1] == 1.0
    # rf 변환: ȳ → (1+ȳ)^(1/12) − 1 → 되돌림 ȳ/12 · 한 달 민다
    ybar = pd.Series([0.012, 0.024, 0.036], index=pd.PeriodIndex(["2005-07", "2005-08", "2005-09"], freq="M"))
    lab = (1 + ybar) ** (1 / 12) - 1
    back = ((1 + lab) ** 12 - 1) / 12
    back.index = back.index + 1
    assert abs(back.loc[pd.Period("2005-09", "M")] - 0.002) < 1e-12 and abs(back.loc[pd.Period("2005-10", "M")] - 0.003) < 1e-12
    # ALFRED 판 비교
    idx = pd.bdate_range("2005-08-01", "2016-12-30")
    base = pd.Series(np.linspace(5, 7, len(idx)), index=idx)
    v1 = base.loc[:"2009-12-31"]
    v2 = base.loc[:"2016-08-31"]
    r = alfred_compare({"2010-01-04": v1, "2016-09-01": v2, "2016-12-31": base})
    assert not r["revised"] and r["n_obs_common"] == len(v1), r
    v2b = v2.copy()
    v2b.iloc[3] += 0.01
    r = alfred_compare({"2010-01-04": v1, "2016-09-01": v2b, "2016-12-31": base})
    assert r["revised"] and r["n_diff_pairs"]["2010-01-04→2016-09-01"]["n_diff"] == 1, r
    return "FRED(«.» · 빈칸) · Cboe · yfinance 파서 · 봇 검사 페이지 거름 · rf 변환(ȳ/12 · u−1) · ALFRED 판 해시 · 개정 개수"


def _zip_text(name, txt):
    import zipfile
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(name, txt)
    return b.getvalue()


def _st_french_vxv():
    vd = _v_data()
    txt = ("This file was created using the 202608 CRSP database.\n\n"
           "  Average Value Weighted Returns -- Monthly\n,SMALL LoBM,BIG LoBM\n200508,  1.00,  2.00\n200509, -99.99,  3.00\n200510,  0.50, -1.00\n\n"
           "  Number of Firms in Portfolios\n,SMALL LoBM,BIG LoBM\n200508, 30, 25\n200509, 30, 19\n200510, 30, 40\n")
    fr = vd.parse_french_blob(_zip_text("x.CSV", txt))
    assert fr["crsp"] == "202608" and "vw_m" in fr["blocks"] and "nfirms" in fr["blocks"]
    r = fr["blocks"]["vw_m"]["BIG LoBM"] / 100
    n = fr["blocks"]["nfirms"]["BIG LoBM"]
    m = r.where(n.reindex(r.index) >= MIN_FIRMS)
    assert m.isna().sum() == 1 and abs(m.iloc[0] - 0.02) < 1e-12 and np.isnan(fr["blocks"]["vw_m"]["SMALL LoBM"].iloc[1])
    # VXV 공표일: 기본 2009-09-18 · 증빙이 더 이를 때만 앞당김 · 더 늦은 날 · 1차 아님은 무시
    assert VXV_PUB_DEFAULT == "2009-09-18"
    global CACHE
    old = CACHE
    with tempfile.TemporaryDirectory() as td:
        try:
            CACHE = td
            assert vxv_pub_date() == "2009-09-18"
            os.makedirs(os.path.join(td, "meta"), exist_ok=True)
            for ev, want in (({"date": "2008-01-02", "primary_cboe": True, "sha256": "ab", "url": "https://x"}, "2008-01-02"),
                             ({"date": "2010-01-04", "primary_cboe": True, "sha256": "ab", "url": "https://x"}, "2009-09-18"),
                             ({"date": "2008-01-02", "primary_cboe": False, "sha256": "ab", "url": "https://x"}, "2009-09-18")):
                with io.open(vxv_evidence_path(), "w", encoding="utf-8") as f:
                    json.dump(ev, f)
                assert vxv_pub_date() == want, (ev, vxv_pub_date())
        finally:
            CACHE = old
    return "French 파서(얼린 v_data · blob 단언) · 기업 수 < 20 NaN · −99.99 · CRSP 판 · VXV 공표일 규칙(앞당김만 · 1차 공고만)"


def _st_registry():
    R = registry()
    for k, ds in R.items():
        allp = [ds["url"], ds["rel"]] + list(ds["seeds"])
        assert not any(mk in str(p) for p in allp for mk in EG_FILE_MARKS), k
        assert not any(mk in str(p).replace("\\", "/") for p in allp for mk in FORBIDDEN_READ_MARKS), k
        for s in ds["seeds"]:
            if _inside(s, os.path.join(TMP, "tbatch_cache")):
                assert _inside(s, SEED_T), "tbatch_cache 는 raw/ 만: %s" % s
    assert "intl" not in " ".join(ds["rel"] for ds in R.values())       # 국외는 x_intl(캐시 raw/intl)
    sig = {"spy", "gspc", "rf_us_m", "vix", "vix3m", "fred_d", "etf"}
    assert all(AVAIL[n]["T1"] is not None for n in sig) and AVAIL["french"]["T1"] is None
    assert set(ALFRED_VINTAGES) and len(ALFRED_VINTAGES) >= 3
    assert git_blob_sha(os.path.join(HERE, "v_data.py")) == V_DATA_BLOB
    return "원천 목록(EG30 산출 · tbatch out 없음 · tbatch 는 raw 만 · 국외 없음) · 신호 입력 가용 선언 · ALFRED 판 ≥ 3 · v_data blob"


SELFTESTS = (_st_guards, _st_windows, _st_calendar_avail, _st_lookahead, _st_parsers_rf, _st_french_vxv, _st_registry)


def selftest():
    res, ok = [], True
    for fn in SELFTESTS:
        t = time.time()
        try:
            res.append(("통과", fn.__name__, fn(), time.time() - t))
        except Exception:                                             # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:], time.time() - t))
    for st, nm, msg, dt in res:
        print("  %s %-20s %5.2fs  %s" % ("✓" if st == "통과" else "✗", nm, dt, msg))
    print("x_data selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--site" in argv:
        g = site_guard()
        print(json.dumps(g, ensure_ascii=False, indent=1))
        return 0 if g["ok"] else 1
    if "--pin" in argv:
        install_read_guard(signal_layer=True)
        install_write_guard(ROOT)
        out = pin_all(fetch="--no-fetch" not in argv)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        if "--no-alfred" not in argv:
            print(json.dumps(alfred_check(fetch="--no-fetch" not in argv), ensure_ascii=False, indent=1))
        return 0 if not any(str(v).startswith("🚨") for v in out.values()) else 1
    if "--manifest" in argv:
        install_write_guard(ROOT)
        doc = build_manifest(write=True)
        print("명세 %s · 원천 %d · ALFRED 판 %d" % (MANIFEST, len(doc["sources"]), len(doc["alfred"]["files"])))
        return 0
    if "--check" in argv:
        r = check_pins()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    if "--smoke" in argv:
        rep = smoke(do_fetch="--no-fetch" not in argv, do_alfred="--no-alfred" not in argv)
        print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
