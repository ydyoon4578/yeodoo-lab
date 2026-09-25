# -*- coding: utf-8 -*-
"""build/t_run.py — 배치 T 한 번 굽기 러너: 얼린 판 점검 → 시작 표식 → t_cards.run_batch(write=True) → 저장소 밖 산출 · 실행 기록.

사전등록: build/PREREG-2026-09-26-TBATCH.md (§6 이 이 파일을 설명한다 · 글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).
카드 규칙 · 틀 · 신호 · 자료는 build/t_cards.py · t_core.py · t_signals.py · t_pit.py · t_data.py — 여기서는 판정 식을 하나도 새로 쓰지 않는다.

  python build/t_run.py --guard     # B8 사이트 경계 점검 — 파일 이름 · 문자열 표식만 본다(수익 없음)
  python build/t_run.py --f0        # B7 F0 셈 — 국면 · 상태 달 수 · 기업 수 · 유효 달 수 · 회전 τ · PIT 종목 수(정수 · 날짜 · 불리언 · τ 만 찍는다)
  python build/t_run.py --pins      # 얼린 파일 표(git blob · LF sha256) — 등록 문서 §6 표를 이 명령으로 만든다
  python build/t_run.py --smoke     # 러너 경로 전체 눈가린 연기 시험(qbatch_core.blind_smoke · 표준출력 버림 · 판 점검 우회 ·
                                    #   NPERM 작게 · 산출 · 표식 · 기록은 임시 폴더에 쓰고 열지 않고 지운다) — ok · 초 · 파일 존재만 돌려준다
  TBATCH_COMMIT=<등록 커밋> PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 python build/t_run.py      # 한 번 굽기

한 번 굽기 규약(QBATCH 러너와 같은 뜻)
  · git fetch origin 을 먼저 한다(낡은 로컬 origin/main 으로 판정하지 않는다 · 실패하면 멈춘다).
  · TBATCH_COMMIT = 사전등록 문서와 이 러너를 **처음 더한** 커밋 · origin/main 의 조상.
  · 얼린 파일(t_core.FROZEN + 이 러너 + t_guard + 엔진이 끌어오는 랩 모듈 — 연기 시험이 sys.modules 로 센 것)이 그 커밋과 바이트 단위로 같다(CRLF 무시).
  · S 층 랩 자료(t_core.S_FILES)가 그 커밋의 판과 같고 추적 안 된 파일도 없다 · 자료 고정본 SHA-256 = 명세(t_data.check_pins) ·
    캐시 표지 SHA = 명세(등록한 캐시 뿌리에서만) · xlrd .py 파일 SHA = 명세 pylib.
  · 산출물이 없다 — 저장소 밖 산출 · 실행 기록 · origin/main 의 결과 문서 어느 것이든 있으면 어떤 사유로도 다시 돌지 않는다(다시 굽기는 새 등록).
  · 시작 표식 둘(`<캐시>/out/_tbatch.started` · 저장소 git 공용 폴더의 `tbatch_started`)을 **무엇보다 먼저** 쓴다. 어느 하나라도 있으면 멈춘다 —
    산출 전 기술적 중단이면 TBATCH_RERUN=사유 로만 처음부터 다시 돈다(표식이 같은 커밋이어야 한다 · 사유는 실행 기록에 남는다). 이어하기는 없다.
  · PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 · numpy 2.5.3 · scipy 1.18.1 · pandas 3.0.6 · openpyxl 3.1.5 · xlrd 2.0.2.
  · 등록 상수(NPERM 1,000 · 선견 t 200 · 씨앗 20260925 · H_T0 구성원 · α 0.025 …)가 실행 때도 그대로다(연기 시험 덮어쓰기가 새지 않게).
  · t_cards.run_batch(write=True) 는 이 러너가 판 점검 뒤 건 표(C._RUNNER_TOKEN = 커밋)가 있어야만 연다 — 러너 밖 굽기 길이 없다.
  · 산출은 저장소 밖(D1 · D3): `<캐시>/out/_tbatch.json`(전부) · `_tbatch.public.json`(결과 문서가 옮길 수 있는 칸만 — §5 를 코드로) ·
    `_tbatch.run.json`(커밋 · 시각 · sha256 · 환경 · 판 · 불러온 build/ 모듈 · 얼리지 않은 모듈 = 등록 오류 — 값 없음).

🚨 랩 규율 — 등록 커밋 전에는 수익 · 초과수익 · IR · 신호-수익 통계를 하나도 계산해서 찍지 않는다.
   --f0 은 셈만 찍는다(카드의 f0() 와 기업 수 · 유효 달 · 회전 τ · PIT 종목 수 — _counts_only 가 실수를 모두 버린다 · τ 만 따로 허용).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

import t_core as C           # noqa: E402
import t_data as TD          # noqa: E402
import t_guard as TG         # noqa: E402  B8 경계(표준 라이브러리만 — validate_site 와 같은 함수)

PREREG = C.PREREG                                            # build/PREREG-2026-09-26-TBATCH.md
RESULT = "build/PREREG-2026-09-26-TBATCH-RESULT.md"
RUNNER = "build/t_run.py"
FIRST_ADDED = (PREREG, RUNNER)                               # 등록 커밋에서 처음 더해져야 하는 것
# 엔진이 끌어오는 랩 모듈 가운데 t_core.FROZEN 에 없는 것 — 러너 연기 시험이 굽기 경로 전체를 돌린 뒤 sys.modules 에서 센
#   build/ 모듈 전부(2026-09-26 · 등록 전 · smoke()["unfrozen_modules"] == [] 여야 한다). 굽기도 끝에 같은 셈을 실행 기록에 남긴다.
EXTRA_FROZEN = (RUNNER, "build/t_guard.py", "build/qg_lab.py", "build/index_members.py", "build/q_switch.py",
                "build/stoploss.py", "build/rally_pattern.py")
FROZEN = tuple(dict.fromkeys(tuple(C.FROZEN) + EXTRA_FROZEN))
VERSIONS = {"numpy": "2.5.3", "scipy": "1.18.1", "pandas": "3.0.6", "openpyxl": "3.1.5", "xlrd": "2.0.2"}
ENV_PINS = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1"}
# 등록 상수 — 얼린 코드의 값과 같아야 굽는다(실행 중 덮어쓰기 방지)
REGISTERED = {
    "C.NPERM": 1000, "C.NPERM_MIN": 1000, "C.SEED": 20260925, "TD.LOOKAHEAD_N": 200, "TD.MIN_FIRMS": 20,
    "C.SLEEVE": 0.10, "C.NW_LAG": 6, "C.NW_LAG_REPORT": 12, "C.S_WIN": ("2016-09", "2026-08"), "C.S_OVERLAP": ("2016-09", "2026-07"),
    "C.S_COST": 0.0010, "C.H_T0_MEMBERS": ("T01", "T02", "T03", "T04", "T05", "T08", "T13", "T15", "T16", "T17"),
    "C.H_T0_ALPHA": 0.025, "C.RHO_MIN_OVERLAP": 36, "C.BY_M": 10, "C.BY_Q": 0.10, "C.DSR_N": (12, 62, 816),
    "C.G6A_MIN": 0.55, "C.TURN_MAX": 10.0, "C.RANK_MIN": 0.90, "C.FID_RHO": 0.60, "C.REB_MISS_MIN": 3,
    "C.DEFENSIVE": ("T02", "T04", "T12", "T15", "T17"), "C.SWITCHING": ("T04", "T05", "T08", "T12", "T15", "T17"),
    "C.LAB_OOS_CARDS": ("T16", "T17", "T18"),
}
CARD_IDS = ("T01", "T02", "T03", "T04", "T05", "T08", "T12", "T13", "T15", "T16", "T17", "T18")


# ══════════════════════════════════════════════════════════════════════════
#  경로 — 산출 · 표식 · 실행 기록은 모두 저장소 밖(t_core.out_path 가 캐시 경계를 지킨다)
# ══════════════════════════════════════════════════════════════════════════
GIT_MARK_NAME = "tbatch_started"                             # 두 번째 시작 표식 — 저장소 git 공용 폴더(.git · 커밋되지 않는다 · %TEMP% 밖)
_GIT_MARK_OVERRIDE = None                                    # 연기 시험만 임시 폴더로 돌린다


def _git_mark_path():
    if _GIT_MARK_OVERRIDE:
        return _GIT_MARK_OVERRIDE
    r = _git("rev-parse", "--git-common-dir")
    g = r.stdout.strip()
    if r.returncode != 0 or not g:
        raise SystemExit("🚨 git 공용 폴더를 찾지 못했다.")
    if not os.path.isabs(g):
        g = os.path.join(ROOT, g)
    return os.path.join(os.path.abspath(g), GIT_MARK_NAME)


def paths():
    out = C.out_path()
    d = os.path.dirname(out)
    return {"dir": d, "out": out, "mark": os.path.join(d, "_tbatch.started"), "runlog": os.path.join(d, "_tbatch.run.json"),
            "public": os.path.join(d, "_tbatch.public.json"), "gitmark": _git_mark_path()}


def _inside_repo(p):
    a, r = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(ROOT))
    return a == r or a.startswith(r + os.sep)


def _existing_outputs(P):
    """산출 쪽 파일(표식 제외) — 있으면 한 번 굽기가 이미 쓰였다."""
    have = [P["out"], P["runlog"]] + [os.path.join(P["dir"], f) for f in (os.listdir(P["dir"]) if os.path.isdir(P["dir"]) else [])
                                      if f.startswith("_tbatch") and f.endswith(".json")]
    return sorted({p for p in have if os.path.exists(p)})


def _git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True, encoding="utf-8")


def _sha_lf(b):
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def _read_text(p):
    return io.open(p, encoding="utf-8").read()


# ══════════════════════════════════════════════════════════════════════════
#  B8 — 사이트 경계(D1 · D3): L 층 산출물 · 라이선스 원자료가 저장소 · 사이트 자료에 없다
# ══════════════════════════════════════════════════════════════════════════
def site_guard():
    """B8 경계 — build/t_guard.site_guard(표준 라이브러리만 · validate_site 가 매 푸시 · 매일 같은 함수를 부른다)."""
    return TG.site_guard(ROOT)


# ══════════════════════════════════════════════════════════════════════════
#  얼린 판 점검(한 번 굽기)
# ══════════════════════════════════════════════════════════════════════════
def _versions():
    import numpy, scipy, pandas, openpyxl
    v = {"numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__, "openpyxl": openpyxl.__version__,
         "python": sys.version.split()[0]}
    try:
        v["xlrd"] = TD._xlrd().__version__
    except Exception as e:                                   # noqa: BLE001
        v["xlrd"] = "없음(%s)" % type(e).__name__
    return v


def _resolve(name):
    mod, attr = name.split(".", 1)
    return getattr({"C": C, "TD": TD}[mod], attr)


def registered_constants_ok():
    bad = []
    for k, want in REGISTERED.items():
        have = _resolve(k)
        if isinstance(want, tuple):
            have = tuple(have)
        if have != want:
            bad.append("%s = %r (등록 %r)" % (k, have, want))
    return bad


def frozen_check(env=None):
    """굽기 전 관문 — 하나라도 어긋나면 SystemExit(아무것도 쓰지 않는다). 돌려주는 것: 등록 커밋 전체 해시."""
    real = env is None
    env = os.environ if env is None else env
    c = env.get("TBATCH_COMMIT")
    if not c:
        raise SystemExit("🚨 TBATCH_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --guard · --f0 · --pins · --smoke 만 된다.")
    if real or not env.get("_TBATCH_NO_FETCH"):              # (_TBATCH_NO_FETCH 는 selftest 가 넘기는 사전에서만 — 진짜 굽기는 늘 받는다)                      # origin/main 을 새로 본다 — 낡은 로컬 origin/main 으로 조상 · 결과 문서를 판정하지 않는다
        fr = _git("fetch", "--quiet", "origin")
        if fr.returncode != 0:
            raise SystemExit("🚨 git fetch origin 실패 — origin/main 을 새로 보지 못하면 굽지 않는다(%s)." % fr.stderr.strip()[:160])
    r = _git("rev-parse", "--verify", c + "^{commit}")
    full = r.stdout.strip()
    if r.returncode != 0 or not full:
        raise SystemExit("🚨 커밋 %s 을 찾지 못했다." % c)
    for p in FIRST_ADDED:
        added = _git("log", "--format=%H", "--diff-filter=A", full, "--", p).stdout.split()
        if not added or added[-1] != full:
            raise SystemExit("🚨 %s 는 %s 를 처음 더한 커밋이 아니다." % (full[:8], p))
    if _git("merge-base", "--is-ancestor", full, "origin/main").returncode != 0:
        raise SystemExit("🚨 사전등록 커밋이 origin/main 에 없다 — 먼저 푸시(git fetch 도).")
    P = paths()
    if _inside_repo(P["dir"]):
        raise SystemExit("🚨 산출 폴더가 저장소 안이다(D1 · D3): %s" % P["dir"])
    outs = _existing_outputs(P)
    if outs:
        raise SystemExit("🚨 산출물이 이미 있다(%s) — 한 번 굽는 측정이다(다시 굽기는 새 등록)." % ", ".join(os.path.basename(o) for o in outs))
    if _git("cat-file", "-e", "origin/main:" + RESULT).returncode == 0:
        raise SystemExit("🚨 origin/main 에 결과 문서가 이미 있다 — 다시 굽기는 새 등록.")
    ci, cmsg = TD.check_cache_identity()                     # 캐시 뿌리 = 등록한 캐시(표지 SHA = 명세) — 새 캐시로 돌려 다시 굽는 길을 막는다
    if not ci:
        raise SystemExit("🚨 %s." % cmsg)
    rerun = env.get("TBATCH_RERUN")
    marks = [m for m in (P["mark"], P["gitmark"]) if os.path.exists(m)]   # 시작 표식 둘 — 캐시 · 저장소 git 공용 폴더(캐시를 바꿔도 남는다)
    if marks and not rerun:
        raise SystemExit("🚨 시작 표식이 있다(%s) — 산출 전 기술적 중단이면 TBATCH_RERUN=사유 로 처음부터(이어하기는 없다)."
                         % ", ".join(os.path.basename(m) for m in marks))
    if rerun and not marks:
        raise SystemExit("🚨 TBATCH_RERUN 은 시작 표식(산출 전 중단)이 있을 때만이다.")
    if rerun and not all(_read_text(m).startswith(full) for m in marks):
        raise SystemExit("🚨 시작 표식이 다른 커밋의 것이다.")
    for p in FROZEN:
        fp = os.path.join(ROOT, p)
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True)
        if want.returncode != 0:
            raise SystemExit("🚨 %s 가 등록 커밋에 없다." % p)
        if not os.path.exists(fp) or _sha_lf(open(fp, "rb").read()) != _sha_lf(want.stdout):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    if _git("diff", "--quiet", full, "--", *C.S_FILES).returncode != 0:
        raise SystemExit("🚨 S 층 랩 자료가 등록 커밋의 판과 다르다(%s …)." % ", ".join(C.S_FILES[:4]))
    extra = _git("ls-files", "--others", "--", *C.S_FILES).stdout.split()
    if extra:
        raise SystemExit("🚨 S 층 랩 자료 폴더에 추적 안 된 파일이 있다(%s …) — load_world 가 읽을 수 있다." % ", ".join(extra[:3]))
    ok, bad = TD.check_pins()
    if not ok:
        raise SystemExit("🚨 자료 고정본이 명세와 다르다: %s" % "; ".join(bad[:5]))
    pl, pmsg = TD.check_pylib()                               # Shiller .xls 를 읽는 xlrd 의 코드 자체(판 문자열만이 아니라 파일 SHA)
    if not pl:
        raise SystemExit("🚨 %s." % pmsg)
    v = _versions()
    vb = ["%s %s(등록 %s)" % (k, v.get(k), want) for k, want in VERSIONS.items() if v.get(k) != want]
    if vb:
        raise SystemExit("🚨 라이브러리 판이 다르다: %s" % ", ".join(vb))
    eb = ["%s=%s" % (k, env.get(k)) for k, want in ENV_PINS.items() if env.get(k) != want]
    if eb:
        raise SystemExit("🚨 PYTHONHASHSEED=0 · OPENBLAS_NUM_THREADS=1 로 돌려라(지금 %s)." % ", ".join(eb))
    cb = registered_constants_ok()
    if cb:
        raise SystemExit("🚨 등록 상수가 다르다: %s" % "; ".join(cb))
    g = site_guard()
    if not g["ok"]:
        raise SystemExit("🚨 사이트 경계(B8) 실패: %s" % "; ".join(g["bad"][:5]))
    return full


# ══════════════════════════════════════════════════════════════════════════
#  굽기
# ══════════════════════════════════════════════════════════════════════════
def local_modules():
    """지금 불러온 build/ 모듈(저장소 상대 경로) — 굽기 경로가 실제로 쓴 코드. 값이 아니다."""
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


# ── 결과 문서가 옮길 수 있는 칸(§5 게시 표를 코드로) — 저장소 밖 캐시에만 쓴다(`_tbatch.public.json`) ─────────
PUBLIC_H1 = ("n", "mean", "ann", "te", "ir", "t", "t12", "p", "first", "last")


def _pub_h1(h):
    return None if not h else {k: h.get(k) for k in PUBLIC_H1}


def _pub_bundle(bd):
    if not bd:
        return None
    y = bd.get("years") or {}
    keep = {k: bd.get(k) for k in ("down", "up", "crash_m", "surge_m", "named", "roll36_neg", "blocks4")}
    keep["crash_legs"] = {k: (bd.get("crash_legs") or {}).get(k) for k in ("n", "mean", "won")}
    keep["rebounds"] = {k: (bd.get("rebounds") or {}).get(k) for k in ("n", "mean", "won")}
    keep["years"] = {k: y.get(k) for k in ("rate", "won", "lost", "ties", "partial", "n_full")}
    keep["h1"] = _pub_h1(bd.get("h1"))
    return keep


def _pub_gates(G):
    """관문은 불리언 · 라벨 글자만(L 층 수치는 싣지 않는다 · D1)."""
    g5 = G.get("G5") or {}
    return {"G2": {"ok": bool(G["G2"]["ok"]), "label": G["G2"]["label"],
                   "rebound_miss_ok": (bool((G["G2"].get("rebound_miss") or {}).get("ok")) if G["G2"].get("rebound_miss") else None)},
            "G3": {"ok": bool(G["G3"]["ok"]), "strict": bool(G["G3"]["strict"])},
            "G4": {"conds": {k: bool(v) for k, v in (G["G4"].get("conds") or {}).items()}, "ok": bool(G["G4"]["ok"])},
            "G5": {**{k: (None if g5.get(k) is None else bool(g5.get(k))) for k in C.G5_KEYS},
                   "f_vintage": {k: bool(v) for k, v in (g5.get("f_vintage") or {}).items()}, "ok": bool(g5.get("ok")),
                   "na": sorted((g5.get("na") or {}).keys())},
            "G6": {"a_ok": bool(G["G6"]["a_ok"])}, "all": bool(G["all"])}


def public_view(out, out_sha256=None, out_bytes=None):
    """§5 게시 표를 코드로 — 결과 문서는 이 사전의 칸만 옮긴다. T02 · T08(D3 · 설계 기본값 «스크래치에만»)은 이름과 «비공개» 뿐.
    L 층은 라벨 · 관문 불리언 · F0 셈 · 전방 자격만 · H_T0 는 z · p · 기각 · 구성원 · t 없는 구성원 · ρ 를 센 짝 수(개별 t · ρ 없음) ·
    D2 민감도(H_T0_sens_exT02) · DSR · L 층 평균 · t 는 싣지 않는다. S 층(10년)은 요약 통계 · 충실도 · 구현성."""
    cards = {}
    for cid, r in (out.get("cards") or {}).items():
        spec = r.get("spec") or {}
        if str(spec.get("publish") or r.get("publish") or "").startswith("비공개"):
            cards[cid] = {"name": spec.get("name"), "공개": "비공개(D3)", "forward_ok": bool(r.get("forward_ok"))}
            continue
        L = r.get("L") or {}
        f0, _ = _counts_only(L.get("f0") or {})
        S = r.get("S") or {}
        sarms = {}
        for nm, a in (S.get("arms") or {}).items():
            sarms[nm] = {"kind": (a.get("meta") or {}).get("kind"), "n": a.get("n"), "gross": _pub_h1(a.get("gross")),
                         "cost10": _pub_h1(a.get("cost10")), "cost10_switch_only": _pub_h1(a.get("cost10_switch_only")),
                         "bundle": _pub_bundle(a.get("bundle")), "turn_1w": a.get("turn_1w")}
        cards[cid] = {"name": spec.get("name"), "label": L.get("label"), "f0_ok": bool(L.get("f0_ok")), "f0": f0,
                      "gates": _pub_gates(L["gates"]) if L.get("gates") else None,
                      "forward_ok": bool(r.get("forward_ok")), "forward_note": r.get("forward_note"),
                      "S": {"arms": sarms, "fidelity": S.get("fidelity"), "pass": bool(S.get("pass")),
                            "provisional": S.get("provisional"), "realtime_note": S.get("realtime_note")}}
    h = out.get("H_T0") or {}
    by = out.get("BY_info") or {}
    return {"note": "결과 문서가 옮길 수 있는 칸만(§5) — 이 밖의 수치는 저장소 밖 _tbatch.json 에만 있다",
            "prereg_commit": out.get("prereg_commit"), "cards": cards,
            "H_T0": {"z": h.get("z"), "p": h.get("p"), "reject": bool(h.get("reject")), "alpha": h.get("alpha"), "z_crit": h.get("z_crit"),
                     "members": h.get("members"), "t_missing_as_zero": h.get("t_missing_as_zero"),
                     "n_rho_pairs": sum(1 for v in (h.get("rho") or {}).values() if (v.get("n") or 0) >= C.RHO_MIN_OVERLAP)},
            "BY_admitted": by.get("admitted"), "n_arms_L": out.get("n_arms_L"), "n_arms_S": out.get("n_arms_S"), "dsr_N": out.get("dsr_N"),
            "out_sha256": out_sha256, "out_bytes": out_bytes}


def bake(commit, rerun=None):
    """frozen_check 를 통과한 뒤에만 부른다(--smoke 는 가짜 커밋으로). 값은 찍지 않는다 — 경로 · sha256 · 초만."""
    t0 = time.time()
    P = paths()
    if rerun:
        started = _read_text(P["mark"] if os.path.exists(P["mark"]) else P["gitmark"]).strip()   # 처음 시작 시각을 그대로
    else:
        started = "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
    for m in (P["mark"], P["gitmark"]):                      # 무엇보다 먼저 — 도중에 죽어도 한 번 굽기가 지켜진다(캐시 · git 공용 폴더 둘)
        if not os.path.exists(m):
            io.open(m, "w", encoding="utf-8", newline="\n").write(started + "\n")
    import t_cards as K
    C._RUNNER_TOKEN = commit                                 # run_batch(write=True) 는 이 표가 있어야 연다(러너 밖 굽기 차단)
    try:
        out = K.run_batch(write=True)                        # 안에서 t_core.frozen_check · NPERM ≥ NPERM_MIN 을 다시 본다
    finally:
        C._RUNNER_TOKEN = None
    p = out.get("_path")
    if not p or not os.path.exists(p):
        raise SystemExit("🚨 산출이 쓰이지 않았다.")
    blob = open(p, "rb").read()
    sha = hashlib.sha256(blob).hexdigest()
    pub = public_view(out, sha, len(blob))
    io.open(P["public"], "w", encoding="utf-8", newline="\n").write(json.dumps(pub, ensure_ascii=False, indent=1, default=C.js_default) + "\n")
    mods = local_modules()
    unf = unfrozen_modules(mods)
    rec = {"prereg": PREREG, "prereg_commit": commit, "runner": RUNNER, "started": started, "rerun": rerun,
           "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "sec": round(time.time() - t0, 1),
           "out": os.path.basename(p), "out_sha256": sha, "out_bytes": len(blob),
           "public": os.path.basename(P["public"]), "public_sha256": hashlib.sha256(open(P["public"], "rb").read()).hexdigest(),
           "env": {k: os.environ.get(k) for k in ENV_PINS}, "versions": _versions(), "frozen": list(FROZEN),
           "local_modules": mods, "unfrozen_modules": unf,
           "registration_error": (["얼리지 않은 build/ 모듈을 불렀다: %s" % ", ".join(unf)] if unf else []),
           "nperm": C.NPERM, "lookahead_n": TD.LOOKAHEAD_N,
           "note": "값 없음 — 결과는 _tbatch.public.json 의 칸만 결과 문서(§5 게시 규칙)로 옮긴다"}
    io.open(P["runlog"], "w", encoding="utf-8", newline="\n").write(json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
    print("→ %s · sha256 %s… · %.0f초 (값은 결과 문서에서)" % (p, rec["out_sha256"][:16], rec["sec"]))
    return rec


def main():
    commit = frozen_check()
    return bake(commit, rerun=os.environ.get("TBATCH_RERUN"))


# ══════════════════════════════════════════════════════════════════════════
#  B7 — F0 셈(수익 없음)
# ══════════════════════════════════════════════════════════════════════════
def _counts_only(x, path="", dropped=None):
    """정수 · 불리언 · 문자열 · None 과 그 사전 · 목록만 남긴다. 실수는 값을 보지 않고 버리고 자리만 적는다."""
    if dropped is None:
        dropped = []
    import numpy as np
    if isinstance(x, (bool, np.bool_)):
        return bool(x), dropped
    if isinstance(x, (int, np.integer)):
        return int(x), dropped
    if x is None or isinstance(x, str):
        return x, dropped
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            vv, _ = _counts_only(v, "%s.%s" % (path, k), dropped)
            if not (isinstance(v, (float, np.floating)) and not isinstance(v, bool)):
                out[str(k)] = vv
        return out, dropped
    if isinstance(x, (list, tuple)):
        return [(_counts_only(v, "%s[]" % path, dropped)[0]) for v in x if not isinstance(v, (float, np.floating))], dropped
    dropped.append(path or "<뿌리>")
    return None, dropped


def _firm_table(D, legs, window):
    import pandas as pd
    out = {}
    for leg in legs:
        try:
            ok = D.f0_ok(leg)
        except Exception as e:                               # noqa: BLE001
            out[leg] = {"err": type(e).__name__}
            continue
        if ok is None:
            continue
        ok = pd.Series(ok).dropna().astype(bool)
        below = ok.index[~ok.to_numpy()]
        inw = ok.loc[C.in_win(ok.index, *window)] if window else ok
        out[leg] = {"months": int(len(ok)), "first": str(ok.index.min()) if len(ok) else None, "below20": int((~ok).sum()),
                    "last_below20": (str(below.max()) if len(below) else None),
                    "below20_in_LR": int((~inw).sum())}
    return out


def f0_table():
    """카드마다 L 층 팔을 지은 뒤 셈만 — card.f0() · 규칙 팔의 층별 유효 달 수 · 다리 기업 수 ≥ 20 · 팔 수.
    배치 공통: PIT 회전 τ(B5 · 편도 · 연) · PIT 바스켓 종목 수 · 커버리지(S 층 F0). 팔 계열은 버린다(값을 찍지 않는다)."""
    import warnings
    import numpy as np
    import t_cards as K
    import t_pit as TP
    D, S = K.Data(), K.SData()
    ctx = K.Ctx(D, S)
    res, sec = {}, {}
    for Kc in K.CARDS:
        t1 = time.time()
        card = Kc()
        with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore")
            arms, lazy = card.build_L(D, ctx)
            f0 = card.f0(D, arms)
            wins = C.layer_windows(card.spec)
            rule = arms["rule"]
            nv = {wn: (int(len(rule.sub(*wins[wn]).S)) if wins.get(wn) else None) for wn in ("L-R", "L-C", "out_of_lab", "lit_seen")}
            legs = sorted({c for a in arms.values() if getattr(a, "W", None) is not None for c in a.W.columns})
            firms = _firm_table(D, legs, wins.get("L-R"))
            rec = {"f0": f0, "n_valid": nv, "firms": firms, "n_arms_L": 1 + (len(arms) - 1) + len(lazy), "arms": sorted(arms) + sorted(lazy),
                   "f0_ok": bool((nv.get("L-R") or 0) >= 60)}
        res[card.id], drop = _counts_only(rec)
        if drop:
            res[card.id]["_dropped_float_keys"] = drop
        sec[card.id] = round(time.time() - t1, 1)
    with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        taus = ctx.taus
        pn = S.panel()
        bk = {}
        for sort in TP.SORTS:
            b = S.pit_bk(sort)
            ns = [n for m, n in b["n"].items() if C.S_WIN[0] <= m <= C.S_WIN[1]]
            bk[sort] = {"months": len(ns), "min_names": (int(min(ns)) if ns else 0), "median_names": (int(np.median(ns)) if ns else 0)}
        cv = [v for v in pn.coverage().values() if v is not None]
    tau = {s: {"tau": (round(float(v["tau"]), 2) if v.get("tau") is not None else None), "n_rebal": int(v.get("n_rebal") or 0)}
           for s, v in sorted(taus.items())}                 # 회전은 수익이 아니다(B5 · 비중 경로만)
    return {"cards": res, "sec": sec, "pit_tau_1w": tau, "pit_baskets_S": bk,
            "pit_coverage": {"months": len(cv), "min": (round(min(cv), 3) if cv else None)},
            "n_arms_L_total": int(sum(r.get("n_arms_L") or 0 for r in res.values()))}


# ══════════════════════════════════════════════════════════════════════════
#  얼린 파일 표 · 러너 연기 시험
# ══════════════════════════════════════════════════════════════════════════
def pins_table():
    rows = []
    for p in FROZEN:
        fp = os.path.join(ROOT, p)
        if not os.path.exists(fp):
            rows.append({"path": p, "blob": None, "sha256_lf": None, "note": "없음"})
            continue
        blob = _git("hash-object", "--", p).stdout.strip()
        rows.append({"path": p, "blob": blob[:12], "sha256_lf": _sha_lf(open(fp, "rb").read())[:16],
                     "tracked": _git("ls-files", "--error-unmatch", "--", p).returncode == 0})
    return rows


def smoke(nperm=3):
    """러너 경로 전체(표식 → run_batch(write=True) → 산출 → 실행 기록)를 눈가린 채 — 판 점검은 가짜 커밋으로 우회 · NPERM 은 작게 덮어쓴다.
    산출 · 표식 · 기록은 저장소 밖 임시 폴더에만 쓰고 **열지 않고** 지운다. 돌려주는 것: {ok, sec, files(존재 · 크기), err}."""
    import qbatch_core as Q
    tmp = tempfile.mkdtemp(prefix="tbatch_runner_smoke_")
    if _inside_repo(tmp):
        raise SystemExit("🚨 임시 폴더가 저장소 안이다.")
    global _GIT_MARK_OVERRIDE
    saved = (C.out_path, C.frozen_check, C.NPERM, C.NPERM_MIN, _GIT_MARK_OVERRIDE)

    def fake_out(name="_tbatch.json"):
        return os.path.join(tmp, name)
    C.out_path = fake_out
    C.frozen_check = lambda: "SMOKE"
    C.NPERM, C.NPERM_MIN = nperm, nperm
    _GIT_MARK_OVERRIDE = os.path.join(tmp, "gitdir_" + GIT_MARK_NAME)      # 진짜 .git 에 표식을 남기지 않는다
    files = {}
    mods = []
    try:
        def run():
            import warnings
            import numpy as np
            with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                warnings.simplefilter("ignore")
                try:
                    return bake("SMOKE")
                except SystemExit as e:
                    raise RuntimeError("SystemExit: %s" % e) from None
        r = Q.blind_smoke(run)
        mods = local_modules()                               # 굽기 경로가 실제로 부른 build/ 모듈(이름만)
        P = paths()
        for k in ("out", "mark", "runlog", "public", "gitmark"):
            files[k] = {"exists": os.path.exists(P[k]), "bytes": (os.path.getsize(P[k]) if os.path.exists(P[k]) else 0)}
        # 두 번째 굽기는 막혀야 한다(산출이 있으니) — 판 점검의 산출 검사만 따로 부른다
        files["second_run_blocked"] = bool(_existing_outputs(P))
        files["token_cleared"] = getattr(C, "_RUNNER_TOKEN", None) is None
    finally:
        C.out_path, C.frozen_check, C.NPERM, C.NPERM_MIN, _GIT_MARK_OVERRIDE = saved
        shutil.rmtree(tmp, ignore_errors=True)               # 열지 않고 지운다
    import t_cards as K
    return {"ok": r["ok"], "sec": r["sec"], "files": files, "deleted_unread": not os.path.exists(tmp),
            "local_modules": mods, "unfrozen_modules": unfrozen_modules(mods),
            "peak_mb": K._peak_mb(), "err": (r["err"] or "")[-2500:] or None}


def selftest():
    """합성 점검 — 판 점검이 빈 환경 · 가짜 커밋을 막는가 · _counts_only 가 실수를 버리는가 · 등록 상수 · 사이트 경계."""
    res = []
    try:
        frozen_check({})
        res.append(("✗", "TBATCH_COMMIT 없음을 막지 못했다"))
    except SystemExit:
        res.append(("✓", "TBATCH_COMMIT 없음 → 멈춤"))
    try:
        frozen_check({"TBATCH_COMMIT": "0000000", "_TBATCH_NO_FETCH": "1"})
        res.append(("✗", "없는 커밋을 막지 못했다"))
    except SystemExit:
        res.append(("✓", "없는 커밋 → 멈춤"))
    head = _git("rev-parse", "HEAD").stdout.strip()
    try:
        frozen_check({"TBATCH_COMMIT": head, "_TBATCH_NO_FETCH": "1"})
        res.append(("✗", "사전등록 문서를 더하지 않은 커밋을 막지 못했다"))
    except SystemExit:
        res.append(("✓", "등록 문서를 처음 더한 커밋이 아님 → 멈춤"))
    kept, drop = _counts_only({"a": 1, "b": 0.123, "c": {"d": True, "e": [1, 2.5, "x"]}, "f": "2020-01"})
    res.append(("✓" if (kept == {"a": 1, "c": {"d": True, "e": [1, "x"]}, "f": "2020-01"}) else "✗", "_counts_only 가 실수를 버린다"))
    cb = registered_constants_ok()
    res.append(("✓" if not cb else "✗", "등록 상수 = 얼린 코드" + ("" if not cb else " — %s" % cb)))
    ok_names = [p for p in FROZEN if not os.path.exists(os.path.join(ROOT, p)) and p != PREREG]
    res.append(("✓" if not ok_names else "✗", "얼린 파일이 작업 트리에 있다" + ("" if not ok_names else " — 없음 %s" % ok_names)))
    # B8 경계(t_guard · 표준 라이브러리만)가 지금 작업 트리에서 통과
    g = site_guard()
    res.append(("✓" if g["ok"] else "✗", "B8 경계(t_guard) 통과 — 파일 %d · 사이트 %d" % (g["n_files"], g["n_scanned"]) + ("" if g["ok"] else " — %s" % g["bad"][:3])))
    # 게시 칸(§5) — 합성 산출에서 L 층 수치 · 개별 t · ρ · D2 민감도 · 비공개 카드의 칸이 빠진다
    h1 = {"n": 120, "mean": 0.001, "ann": 0.012, "te": 0.02, "ir": 0.6, "t": 2.0, "t12": 1.9, "p": 0.02, "first": "2016-09", "last": "2026-08"}
    bd = {"h1": h1, "down": {"n": 40, "mean": 0.001, "win": 0.6}, "up": {"n": 80, "mean": 0.0}, "crash_m": {"n": 5, "mean": 0.002},
          "surge_m": {"n": 6, "mean": -0.001}, "crash_legs": {"n": 3, "mean": 0.01, "won": 2, "rows": [{"x": 0.01}]},
          "rebounds": {"n": 3, "mean": 0.0, "won": 1, "rows": []}, "named": {}, "years": {"rate": 0.6, "won": 6, "lost": 3, "ties": [],
          "partial": [2016, 2026], "n_full": 9, "years": {"2017": {"ex": 0.01}}}, "roll36_neg": 0.2, "blocks4": [1, 2, 3, 4]}
    G = {"G2": {"ok": True, "label": "양면", "crash_m": 0.123456}, "G3": {"ok": True, "strict": False, "down_mean": 0.123456},
         "G4": {"conds": {"x": True}, "ok": True}, "G5": {**{k: True for k in C.G5_KEYS}, "f_vintage": {"2024-12": True}, "ok": True, "na": {}},
         "G6": {"a_ok": True, "a_rate": 0.123456}, "all": True}
    fake = {"cards": {"T01": {"spec": {"name": "a"}, "L": {"label": "문헌 재현(전방 대기)", "f0_ok": True, "f0": {"m": 3, "x": 0.123456},
                                                        "gates": G, "LR": {"h1": {"mean": 0.123456}}},
                               "S": {"arms": {"rule": {"meta": {"kind": "k"}, "n": 120, "gross": h1, "cost10": h1, "cost10_switch_only": h1,
                                                       "bundle": bd, "turn_1w": 1.0}}, "fidelity": {"rho": 0.7, "gate": True}, "pass": True},
                               "forward_ok": True, "dsr": {"LR": [{"dsr": 0.123456}]}},
                      "T08": {"spec": {"name": "b", "publish": "비공개(D3)"}, "L": {"label": "x", "gates": G}, "S": {"arms": {}}, "forward_ok": False}},
            "H_T0": {"z": 1.1, "p": 0.13, "reject": False, "alpha": 0.025, "z_crit": 1.96, "members": ["T01", "T08"], "t": {"T01": 0.987654},
                     "rho": {"T01~T08": {"n": 40, "rho": 0.345678}}, "t_missing_as_zero": [], "sum_t": 0.987654, "den": 2.0},
            "H_T0_sens_exT02": {"z": 0.555555}, "BY_info": {"admitted": ["T01"], "k": 1}, "n_arms_L": 5, "n_arms_S": 2, "dsr_N": (12, 62, 816)}
    pv = public_view(fake, "ab" * 32, 10)
    js = json.dumps(pv, ensure_ascii=False, default=C.js_default)
    leaks = [v for v in ("0.123456", "0.987654", "0.345678", "0.555555", "H_T0_sens", "rows", '"t": {') if v in js]
    ok_pv = (not leaks and pv["H_T0"]["z"] == 1.1 and pv["H_T0"]["n_rho_pairs"] == 1 and set(pv["cards"]["T08"]) == {"name", "공개", "forward_ok"}
             and pv["cards"]["T01"]["S"]["arms"]["rule"]["cost10"]["t"] == 2.0 and pv["cards"]["T01"]["gates"]["G5"]["ok"] is True)
    res.append(("✓" if ok_pv else "✗", "게시 칸(§5): L 층 수치 · 개별 t · ρ · D2 민감도 · 비공개 카드 칸 제외" + ("" if ok_pv else " — 샌 것 %s" % leaks)))
    mods = local_modules()
    ok_m = ("build/t_run.py" in mods and "build/t_core.py" in mods and unfrozen_modules(["build/t_run.py", "build/zz_x.py"]) == ["build/zz_x.py"])
    res.append(("✓" if ok_m else "✗", "불러온 build/ 모듈 셈 · 얼리지 않은 모듈 거르개"))
    src = _read_text(os.path.abspath(__file__))
    import ast
    bad = []
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Call) and getattr(nd.func, "id", getattr(nd.func, "attr", None)) == "open":
            kw = {k.arg for k in nd.keywords}
            mode = nd.args[1].value if len(nd.args) > 1 and isinstance(nd.args[1], ast.Constant) else ""
            if "encoding" not in kw and "b" not in str(mode):
                bad.append(nd.lineno)
    res.append(("✓" if not bad else "✗", "open() encoding 정적 점검" + ("" if not bad else " — 줄 %s" % bad)))
    for st, msg in res:
        print("  %s %s" % (st, msg))
    n_ok = sum(1 for s, _ in res if s == "✓")
    print("t_run selftest %d/%d 통과" % (n_ok, len(res)))
    return 0 if n_ok == len(res) else 1


if __name__ == "__main__":
    a = sys.argv
    if "--selftest" in a:
        raise SystemExit(selftest())
    if "--guard" in a:
        g = site_guard()
        print(json.dumps(g, ensure_ascii=False, indent=1))
        raise SystemExit(0 if g["ok"] else 1)
    if "--pins" in a:
        print(json.dumps(pins_table(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    if "--f0" in a:
        print(json.dumps(f0_table(), ensure_ascii=False, indent=1))
        raise SystemExit(0)
    if "--smoke" in a:
        r = smoke()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        raise SystemExit(0 if r["ok"] else 1)
    if len(a) > 1:
        print(__doc__)
        raise SystemExit(2)
    main()
