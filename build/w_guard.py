# -*- coding: utf-8 -*-
"""build/w_guard.py — 배치 W 가드: G-NoEG 세 겹(정적 전이 · 실행 중 sys.modules · 연 파일 감사) + 입력 단위 블랙리스트(이름 · 원천 파일 · 개념 태그)
· 사이트 가드(공개 저장소 쪽) · G-DER 도우미. 표준 라이브러리만 쓴다(validate_site 같은 가벼운 호출자가 부를 수 있게).

설계 원본(구속): wbatch_research.json final.build_plan(no_import_rule · may_import · guards.blacklist) · final.slate.common_frame(G_NoEG_inputs · G_EGD ·
  no_derivatives) · final.needs_user U3(«Eg 입력 어디에도 없다»의 엄격 해석 — B/M 을 통제 · 잔차 요인에서도 뺀다) · U4(SEC 연락처는 공개 저장소에 없다) ·
  final.decisions D09 · D10. 설계를 다시 짓지 않는다.

(1) 정적(noeg_static): W 모듈(build/w_*.py · 별도 과정 w_cmp · w_audit 제외)과 그것이 닿는 로컬 모듈 전부의 AST 를 전이적으로(함수 · 메서드 · 조건 안 import ·
    importlib.import_module / __import__ 의 상수 인자까지) 훑어 금지 목록이 없어야 한다. 금지 = 명세 no_import_rule 그대로
    (eg30plus · t_core · t_data · t_signals · u_data · qfwd_* · qg_lab · qbatch_* · q_switch · eg_q5* · idxeg · eg_best · r_stages · r_stagem · r_r1_flags ·
    r_r2flags · v_cmp · v_run) + 배치 U 모듈(취소된 EG30 계보 · V 선례) + v_audit(원본 짝맞춤 과정 — 원본을 부른다).
    별도 과정 경계: W 대상 폐포에 w_cmp · w_audit 가 없다 · w_cmp 는 어떤 w_ 모듈에도 닿지 않는다(EG 파일을 여는 유일한 W 과정) ·
    w_audit 는 w_ 엔진을 불러도 되지만(짝맞춤) 대상 쪽이 w_audit 를 부르면 안 된다.
    더해서(명세 guards.blacklist «입력 이름» 단위의 정적 판): 대상 모듈 소스의 짧은 문자열 상수가 금지 입력 이름과 같으면 위반(literal_scan) ·
    noeg=False 키워드는 w_audit 밖에서 쓰면 위반(블랙리스트 우회는 허용 목록 재현 과정만).
(2) 실행 중(runtime_check): 굽기 · 연기 · F0 과정 끝에 sys.modules 에 금지 모듈이 없어야 한다.
(3) 연 파일 감사(install_open_audit · open_audit_check): sys.addaudithook 으로 연 경로를 모아 EG 파일(V 표식 그대로) · EG 원 캐시 폴더(egff) ·
    B/M · 투자 · 수익성 정렬 French 파일과 FF3/FF5 요인 파일(HML · SMB(2×3 B/M 정렬) · CMA · RMW 가 든 원천)을 열지 않았는지 본다. w_cmp 는 범위 밖(별도 과정).
(4) 입력 단위 블랙리스트(check_units · assert_units): 모든 신호 · 책 · Stage M-W 통제 · 잔차화 요인이 제 입력을 InputUnit(이름 · 원천 · 개념 · 쓰임)으로
    밝히고 셋 중 하나라도 금지면 멈춘다. 금지(명세 G_NoEG_inputs 그대로): EG30 · Eg · QG30 · eg_q5 · 자산성장 Δasset · I/A · capex · cfo 와 cfo 기반 비율
    (CF/P · Cop) · 발생액(ni − cfo) · 순발행 Δsh · 자사주 · B/M · log q · HML(B/M 정렬) · ROE · ROA 수준 · dRoe.
    🔎 선언(명세가 이름을 적지 않은 같은 원칙의 적용 — 보수 · U3 엄격 해석): French CMA(자산성장 정렬 = I/A) · RMW(영업수익성 = 장부 대비 수익성 수준 ≈ ROE)도
    HML 과 같은 이유로 막는다.
    허용 예외(명세 그대로): sh · sho 는 시총 분모(me_denominator) · 13F 보유 비율 분모(holding_ratio_denominator)로만 · 총자산 수준(log asset)은
    KPS 크기 특성(kps_size)으로만(성장률 아님) — 그 밖의 쓰임이면 멈춘다. G-EGD(w_cmp)가 닮음을 따로 잰다.
    🔎 선언(보수 · U3): 장부 자본 eq(v_fund 칸)은 허용 쓰임이 없다 — W 카드 어디에도 쓰이지 않고, 쓰면 B/M · ROE 수준 · 레버리지(KPS8 에서 뺐다)
    가운데 하나가 된다.
G-DER: 보유 표식에 파생(선물 · 옵션 · 변동성 ETF) 없음(v_guard 표식과 같은 정규식 — 주식 중심).
사이트 가드(site_guard): git 이 추적 · 추가 예정인 파일 가운데 라이선스 원자료 이름(French · companyfacts · 13F 정보표 · FSDS · ZIP–CBSA 교차표) ·
  L 층 산출 이름(_wbatch* …) · 허용 밖 data/_wb* · 🚨 data/_wfwd/* 는 하나도(사용자 갱신 2026-09-27 «미래 일정은 다 꺼» — 전방 원장 WFWD · 창세 ·
  FF1/FF2 없음) · 허용 파일의 값 계열(숫자 다섯 개 넘는 목록) · 사이트 자료의 굽기 산출 표식 ·
  W 파일 안의 전자우편 모양 문자열(U4 — SEC 연락처는 SEC_UA 환경변수로만)이 없어야 한다.
정적 점검은 w_core.frozen("모듈") 의 상수 인자도 import 로 따라간다(얼린 V 모듈을 핀 대조 뒤 부르는 길).

  python build/w_guard.py --noeg        대상 w_ 모듈 전부 정적 전이 점검(참/거짓 · 닿은 로컬 모듈 · 동적 import · 문자열 상수 · noeg 우회)
  python build/w_guard.py --site        사이트 가드(저장소 쪽)
  python build/w_guard.py --selftest
"""
from __future__ import annotations

import ast
import fnmatch
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ══════════════════════════════════════════════════════════════════════════
#  (1) 정적 — 금지 모듈 · 별도 과정
# ══════════════════════════════════════════════════════════════════════════
FORBIDDEN_MODULES = ("eg30plus", "t_core", "t_data", "t_signals", "u_data", "qfwd_*", "qg_lab", "qbatch_*", "q_switch", "eg_q5*", "idxeg",
                     "eg_best", "r_stages", "r_stagem", "r_r1_flags", "r_r2flags", "v_cmp", "v_run",
                     "u_core", "u_cards", "u_run", "u_web", "u_tests", "u_guard", "v_audit")
SEPARATE_PROCESS = ("w_cmp", "w_audit")          # 허용 목록 별도 과정 — 대상 폐포에 들면 안 된다
NOEG_BYPASS_OK = ("w_audit",)                     # noeg=False(블랙리스트 우회)를 쓸 수 있는 유일한 모듈 — R 공개 값 재현(log B/M 통제)
LITERAL_EXEMPT = ("w_guard",) + SEPARATE_PROCESS  # 금지 이름을 정의(w_guard) · 재현(w_audit) · 비교(w_cmp)하는 곳


def forbidden(name):
    base = str(name).split(".")[0]
    return any(fnmatch.fnmatch(base, pat) for pat in FORBIDDEN_MODULES)


def _parse(path):
    import warnings
    with io.open(path, encoding="utf-8") as f:
        src = f.read()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(src)


def imports_of(path):
    """파일 하나의 import 이름 전부(깊이 무관 · 함수 안 포함 · 상대 import 는 모듈 이름) · 상수가 아닌 동적 import 의 줄 번호."""
    tree = _parse(path)
    names, dyn = set(), []
    for nd in ast.walk(tree):
        if isinstance(nd, ast.Import):
            names.update(a.name for a in nd.names)
        elif isinstance(nd, ast.ImportFrom):
            if nd.module:
                names.add(nd.module)
        elif isinstance(nd, ast.Call):
            fn = nd.func
            fname = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else None)
            if fname == "frozen" and nd.args and isinstance(nd.args[0], ast.Constant) and isinstance(nd.args[0].value, str):
                names.add(nd.args[0].value)                                    # w_core.frozen("v_tests") — 핀 대조 뒤 import
            elif fname in ("import_module", "__import__"):
                a0 = nd.args[0] if nd.args else None
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    names.add(a0.value)
                else:
                    dyn.append(nd.lineno)
    return names, dyn


def local_module(name, root=HERE):
    p = os.path.join(root, str(name).split(".")[0] + ".py")
    return p if os.path.isfile(p) else None


def closure(targets, root=HERE, stop_forbidden=True):
    """대상 모듈 이름들에서 닿는 로컬 모듈 — {reached, hits(금지 경로 문자열), dynamic{모듈: [줄]}, via{모듈: 경로}}."""
    seen, hits, dyn, via = set(), set(), {}, {}
    stack = [(t, (t,)) for t in targets]
    while stack:
        name, path = stack.pop()
        base = name.split(".")[0]
        if base in seen:
            continue
        if forbidden(base):
            hits.add(" → ".join(path))
            if stop_forbidden:
                continue
        p = local_module(base, root)
        if p is None:
            continue                                            # 표준 · 제3자 라이브러리
        seen.add(base)
        via[base] = path
        names, d = imports_of(p)
        if d:
            dyn[base] = d
        for n in sorted(names):
            b = n.split(".")[0]
            if b not in seen:
                stack.append((b, path + (b,)))
    return {"reached": sorted(seen), "hits": sorted(hits), "dynamic": dyn, "via": via}


def w_targets(root=HERE):
    return sorted(fn[:-3] for fn in os.listdir(root)
                  if fn.startswith("w_") and fn.endswith(".py") and fn[:-3] not in SEPARATE_PROCESS)


# 입력 이름 단위의 정적 판 — 소스의 문자열 상수가 이 이름(정규화)과 **같으면** 위반(긴 문서 문자열은 같지 않으니 걸리지 않는다)
BLACK_FIELD_LITERALS = ("cfo", "capex", "logbm", "log_bm", "bm", "btm", "b/m", "b_m", "beme", "be_me", "booktomarket", "eg", "eg30", "qg30", "eg_q5",
                        "egq5", "roe", "roa", "droe", "d_roe", "hml", "cma", "rmw", "accrual", "accruals", "ia", "i/a", "i_a", "dasset", "d_asset",
                        "asset_growth", "assetgrowth", "logq", "log_q", "tobinq", "cop", "cfp", "cf_p", "cf/p", "net_issue", "netissue",
                        "net_issuance", "dsh", "d_sh", "buyback", "buybacks", "repurchase", "repurchases")
_BLACK_LIT = {re.sub(r"\s+", "", s.lower()) for s in BLACK_FIELD_LITERALS}


def literal_scan(path):
    """모듈 하나의 문자열 상수 가운데 금지 입력 이름과 같은 것 [(줄, 값)] — dict 열쇠 · 함수 인자 · 목록 원소 모두."""
    bad = []
    for nd in ast.walk(_parse(path)):
        if isinstance(nd, ast.Constant) and isinstance(nd.value, str) and len(nd.value) <= 24:
            v = re.sub(r"\s+", "", nd.value.lower())
            if v in _BLACK_LIT:
                bad.append((getattr(nd, "lineno", 0), nd.value))
    return bad


def noeg_bypass_scan(path):
    """noeg=False 키워드(블랙리스트 우회) 사용 줄 — 상수 False 뿐 아니라 상수가 아닌 값도 우회로 본다(참이 아니면 우회)."""
    bad = []
    for nd in ast.walk(_parse(path)):
        if isinstance(nd, ast.Call):
            for kw in nd.keywords:
                if kw.arg == "noeg" and not (isinstance(kw.value, ast.Constant) and kw.value.value is True):
                    bad.append(getattr(nd, "lineno", 0))
    return bad


def _frozen_pin_names(root):
    """실제 트리면 w_core.FROZEN_PINS(얼린 V 모듈 · may_import 폐포) 이름 — 임시 합성 트리면 None(점검 생략)."""
    if os.path.normcase(os.path.abspath(root)) != os.path.normcase(HERE) or not os.path.isfile(os.path.join(HERE, "w_core.py")):
        return None
    import w_core                                                                  # 표준 라이브러리만(모듈 머리)
    return set(w_core.FROZEN_PINS)


def noeg_static(root=HERE, targets=None, pins=None):
    """G-NoEG (1) — 대상 w_ 모듈 폐포에 금지 모듈 없음 · 별도 과정 경계 · 문자열 상수 · noeg 우회 · 닿은 로컬 비-w 모듈이 모두 얼린 V 핀 안
    (명세 may_import · 실제 트리에서만). 돌려주는 것 {ok, …}."""
    targets = list(targets or w_targets(root))
    C = closure(targets, root)
    pins = _frozen_pin_names(root) if pins is None else set(pins)
    unpinned = sorted(m for m in C["reached"] if not m.startswith("w_") and pins is not None and m not in pins)
    sep = ["대상 폐포 ⇢ %s(전이)" % x for x in C["reached"] if x in SEPARATE_PROCESS]
    if local_module("w_cmp", root):
        R = closure(["w_cmp"], root, stop_forbidden=False)                  # w_cmp 는 EG 계보를 부른다 — w_ 모듈에 닿는지만 본다
        sep += ["w_cmp ⇢ %s(전이)" % x for x in R["reached"] if x.startswith("w_") and x != "w_cmp"]
    lit, byp = {}, {}
    for m in sorted(set(C["reached"]) | set(targets)):
        if not m.startswith("w_"):
            continue
        p = local_module(m, root)
        if p is None:
            continue
        if m not in LITERAL_EXEMPT:
            b = literal_scan(p)
            if b:
                lit[m] = b[:10]
        if m not in NOEG_BYPASS_OK:
            b = noeg_bypass_scan(p)
            if b:
                byp[m] = b[:10]
    ok = not C["hits"] and not sep and not lit and not byp and not unpinned
    return {"ok": ok, "targets": targets, "n_reached": len(C["reached"]), "reached": C["reached"], "hits": C["hits"],
            "separate_violations": sep, "literal_hits": lit, "noeg_bypass": byp, "unpinned": unpinned, "pins_checked": pins is not None,
            "dynamic_imports": C["dynamic"]}


# ══════════════════════════════════════════════════════════════════════════
#  (2) 실행 중 — sys.modules
# ══════════════════════════════════════════════════════════════════════════
def runtime_check(mods=None):
    mods = list(sys.modules) if mods is None else list(mods)
    bad = sorted({m.split(".")[0] for m in mods if forbidden(m.split(".")[0])})
    return {"ok": not bad, "loaded_forbidden": bad}


# ══════════════════════════════════════════════════════════════════════════
#  (3) 연 파일 감사
# ══════════════════════════════════════════════════════════════════════════
EG_FILE_MARKS = ("_eg_q5", "_eg30plus", "_qfwd", "_eg_best", "_idxeg", "_qbatch", "_qg_", "v0_pin", "_fund_card")   # v_guard 표식 그대로
EG_DIR_MARKS = ("egff",)
# 원천 파일 단위 금지(French) — B/M · 투자 · 수익성 정렬 포트와 FF3/FF5 요인(HML · 2×3 B/M 정렬 SMB · CMA · RMW 가 든 원천)
FRENCH_BLACK_MARKS = ("be-me", "beme", "book-to-market", "f-f_research_data_factors", "f-f_research_data_5_factors", "6_portfolios_2x3",
                      "25_portfolios_5x5", "100_portfolios_10x10", "portfolios_formed_on_inv", "portfolios_formed_on_op", "__ff3", "__ff5",
                      "__me_op", "__me_inv", "__inv", "_hml", "_cma", "_rmw")
_OPENED = []


def install_open_audit():
    """G-NoEG (3) — open 감사 고리(과정마다 한 번). 연 경로를 모은다."""
    if getattr(install_open_audit, "_on", False):
        return
    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            try:
                _OPENED.append(os.fsdecode(args[0]))
            except Exception:                                   # noqa: BLE001 — 감사 고리는 절대 과정을 죽이지 않는다
                pass
    sys.addaudithook(hook)
    install_open_audit._on = True


def black_path(p):
    """이 경로가 금지 원천 파일인가 — (참/거짓, 이유)."""
    s = str(p)
    base = os.path.basename(s)
    low = base.lower()
    parts = [x.lower() for x in re.split(r"[\\/]+", s) if x]
    if any(mk in base for mk in EG_FILE_MARKS):
        return True, "EG 파일"
    if any(d in parts[:-1] for d in EG_DIR_MARKS):
        return True, "EG 원 캐시 폴더"
    if any(mk in low for mk in FRENCH_BLACK_MARKS):
        return True, "B/M · 투자 · 수익성 정렬 또는 FF 요인 원천"
    return False, None


def open_audit_check():
    bad = sorted({p for p in _OPENED if black_path(p)[0]})
    return {"ok": not bad, "n_opened": len(_OPENED), "black_opened": bad[:5], "n_black": len(bad)}


def opened_paths():
    return list(_OPENED)


def noeg_report(root=HERE):
    """G-NoEG 세 겹 한 묶음(굽기 · 연기 · F0 과정 끝에 부른다) — 정적(대상 폐포) · 실행 중(sys.modules) · 연 파일 감사(고리가 걸려 있어야 한다) ·
    입력 단위 통과 기록 수. 하나라도 거짓이면 ok 거짓(fail-closed · 고리가 없으면 연 파일 감사는 거짓)."""
    st = noeg_static(root)
    rt = runtime_check()
    oa = open_audit_check() if getattr(install_open_audit, "_on", False) else {"ok": False, "why": "open 감사 고리가 걸리지 않았다"}
    return {"ok": bool(st["ok"] and rt["ok"] and oa["ok"]), "static": {k: st[k] for k in ("ok", "n_reached", "hits", "unpinned")},
            "runtime": rt, "open_audit": oa, "units_registered": len(_REGISTRY)}


# ══════════════════════════════════════════════════════════════════════════
#  (4) 입력 단위 블랙리스트
# ══════════════════════════════════════════════════════════════════════════
BLACK_NAMES = {        # 정규화(소문자 · 영숫자만) 이름 전체가 이것이면 금지
    "eg30", "eg", "qg30", "egq5", "egq5scores", "egscore", "egrank", "dasset", "assetgrowth", "ia", "investment", "capex", "cfo", "cfp", "cashflowtoprice",
    "cop", "cashop", "cashbasedop", "accrual", "accruals", "nicfo", "netissue", "netissuance", "dsh", "shareissuance", "buyback", "buybacks",
    "repurchase", "repurchases", "bm", "btm", "beme", "booktomarket", "logbm", "logbtm", "logq", "tobinq", "hml", "roe", "roa", "droe", "cma", "rmw"}
BLACK_TOKENS = {       # 이름을 낱말로 쪼갠 조각에 이것이 있으면 금지(모호하지 않은 것만)
    "eg30", "eg", "qg30", "egq5", "capex", "cfo", "cop", "accrual", "accruals", "hml", "roe", "roa", "droe", "cma", "rmw", "bm", "btm", "beme",
    "logbm", "logq", "tobinq", "buyback", "buybacks", "repurchase", "repurchases", "dasset", "netissue", "assetgrowth"}
BLACK_CONCEPTS = {     # 개념 태그(정규화)
    "eg30", "eg", "qg30", "egq5", "expectedgrowth", "assetgrowth", "dasset", "ia", "investment", "capex", "cfo", "cfp", "cashflowtoprice", "cop",
    "cashbasedoperatingprofitability", "accruals", "accrual", "netissuance", "netissue", "buyback", "repurchase", "bm", "booktomarket", "logq",
    "tobinq", "hml", "roe", "roa", "roelevel", "roalevel", "droe", "cma", "rmw", "operatingprofitabilitybook"}
RESTRICTED = {         # 쓰임이 정해진 원장 칸(명세 허용 예외) · 빈 쓰임 = 어떤 쓰임도 안 된다(선언)
    "sh": ("me_denominator", "holding_ratio_denominator"),
    "sho": ("me_denominator", "holding_ratio_denominator"),
    "asset": ("kps_size",),
    "logasset": ("kps_size",),
    "eq": (),
    "bookequity": (),
    "be": (),
}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _tokens(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(s or ""))
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]


def unit(name, source=None, concept=None, use=None):
    """InputUnit — 입력 하나(이름 · 원천 파일/모듈 · 개념 태그 · 쓰임)."""
    return {"name": str(name), "source": (None if source is None else str(source)), "concept": (None if concept is None else str(concept)),
            "use": (None if use is None else str(use))}


def unit_violation(u):
    """입력 하나의 위반 이유(없으면 None)."""
    if isinstance(u, str):
        u = unit(u)
    nm, src, cc, use = u.get("name"), u.get("source"), u.get("concept"), u.get("use")
    n = _norm(nm)
    if n in RESTRICTED:
        if not RESTRICTED[n]:
            return "%s(장부 자본)는 W 에서 쓰지 않는다(B/M · ROE · 레버리지 입력 — 선언)" % nm
        if use not in RESTRICTED[n]:
            return "%s 는 %s 로만 쓴다(쓰임 %s)" % (nm, "/".join(RESTRICTED[n]), use)
        if n in ("asset", "logasset") and cc is not None and _norm(cc) not in ("logassetlevel", "assetlevel", "kpssize"):
            return "총자산은 수준(log asset · KPS 크기)으로만 — 개념 %s" % cc
    if n in BLACK_NAMES:
        return "금지 입력 이름 %s" % nm
    hit = [t for t in _tokens(nm) if t in BLACK_TOKENS]
    if hit:
        return "금지 낱말 %s(이름 %s)" % (hit[0], nm)
    if cc is not None:
        c = _norm(cc)
        if c in BLACK_CONCEPTS or any(t in BLACK_TOKENS for t in _tokens(cc)):
            return "금지 개념 %s" % cc
        if "growth" in c and ("asset" in c or "invest" in c):
            return "금지 개념(투자 · 자산 성장) %s" % cc
    if src is not None:
        b, why = black_path(src)
        if b:
            return "금지 원천 %s(%s)" % (src, why)
        if any(t in ("cfo", "capex", "eg30", "qg30", "egq5") for t in _tokens(os.path.basename(src))):
            return "금지 원천 이름 %s" % src
    return None


_REGISTRY = []


def check_units(units, where=""):
    out = []
    for u in units or ():
        why = unit_violation(u)
        if why:
            out.append({"where": where, "unit": (u if isinstance(u, dict) else unit(u)), "why": why})
    return out


def assert_units(units, where=""):
    """입력 단위 블랙리스트 — 하나라도 금지면 멈춘다(fail-closed). 통과한 입력은 기록한다(manifest 에 싣는다)."""
    bad = check_units(units, where)
    if bad:
        raise SystemExit("🚨 G-NoEG 입력 단위 위반(%s): %s" % (where, "; ".join(b["why"] for b in bad[:5])))
    for u in units or ():
        _REGISTRY.append(dict(u if isinstance(u, dict) else unit(u), where=where))
    return True


def registry():
    return list(_REGISTRY)


def main_script():
    m = sys.modules.get("__main__")
    f = getattr(m, "__file__", None) or (sys.argv[0] if sys.argv else "")
    return os.path.basename(str(f))


def assert_bypass_allowed(what=""):
    """noeg=False 는 허용 목록 재현 과정(w_audit 가 주 스크립트)에서만 — 정적 검사(noeg_bypass_scan)와 짝인 실행 중 자물쇠."""
    if main_script() != "w_audit.py":
        raise SystemExit("🚨 G-NoEG 우회(noeg=False)는 w_audit(허용 목록 별도 과정)에서만 — 주 스크립트 %s · %s" % (main_script(), what))
    return True


# ══════════════════════════════════════════════════════════════════════════
#  G-DER
# ══════════════════════════════════════════════════════════════════════════
DERIV_HOLD = re.compile(r"(?i)(=F$|\bES[HMUZ]\d|\bMES\b|\bVIX|VXX|UVXY|SVXY|VIXY|VXZ|\bXYLD\b|\bQYLD\b|\bBXM|_PUT\b|\bOPT:|option|future|\d{6}[CP]\d{8})")


def no_derivative_positions(book):
    bad = [k for k in book if DERIV_HOLD.search(str(k))]
    if bad:
        raise SystemExit("🚨 파생 보유 표식(주식 중심 위반): %s" % ", ".join(map(str, bad[:5])))
    return True


# ══════════════════════════════════════════════════════════════════════════
#  사이트 가드(저장소 쪽)
# ══════════════════════════════════════════════════════════════════════════
WB_ALLOWED = {"data/_wb_manifest.json", "data/_wb_f0.json"}     # 공개 안전 파일(더할 때 여기에 적는다)
WFWD_ALLOWED = set()                                            # 🚨 전방 원장 없음(사용자 갱신 2026-09-27) — data/_wfwd/* 는 하나도 허용하지 않는다
LICENSED_NAME_MARKS = ("F-F_Research_Data_Factors", "Portfolios_Formed_on_", "6_Portfolios_", "25_Portfolios_", "10_Portfolios_",
                       "_Industry_Portfolios", "companyfacts", "CIK00", "vd1/", "wide_ledger", "INFOTABLE", "infotable", "form13f", "FORM13F",
                       "fsds", "FSDS", "ZIP_CBSA", "zip_cbsa", "ZCTA", "zcta", "_sub.txt", "_num.txt")
L_OUTPUT_MARKS = ("_wbatch", "_wb_L", "_wb_f0_L")
OUTPUT_CONTENT_MARKS = (b"_wbatch.json", b"_wbatch.public.json", b"_wbatch.run.json", b'"wbatch_public_view"', b'"wbatch_full_out"')
EMAIL_RX = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMAIL_OK = (b"noreply" + b"\x40" + b"anthropic.com",)          # 커밋 꼬리 줄(저장소 규약) — SEC 연락처가 아니다 · W 파일에 메일 꼴 글자를 두지 않으려 조각으로 쓴다


def value_lists(doc, path="", max_len=4):
    out = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            out += value_lists(v, path + "/" + str(k), max_len)
    elif isinstance(doc, list):
        nums = [x for x in doc if isinstance(x, (int, float)) and not isinstance(x, bool)]
        if len(nums) > max_len:
            out.append(path or "/")
        for x in doc:
            out += value_lists(x, path + "[]", max_len)
    return out


def _w_file(f):
    b = os.path.basename(f)
    return (f.startswith("build/") and b.startswith("w_") and b.endswith(".py")) or f.startswith("data/_wb") or f.startswith("data/_wfwd/") \
        or (f.startswith("build/PREREG-") and "WBATCH" in b)


def site_guard(root=None):
    """저장소 쪽 점검(표준 라이브러리만) — 돌려주는 것 {ok, bad[], n_bad, n_files, n_scanned}."""
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
        if any(b.startswith(mk) for mk in L_OUTPUT_MARKS):
            bad.append("L 층 산출 이름: %s" % f)
        if f.startswith("data/_wb") and f not in WB_ALLOWED:
            bad.append("허용 밖 data/_wb*: %s" % f)
        if f.startswith("data/_wfwd/") and f not in WFWD_ALLOWED:
            bad.append("전방 원장 파일 data/_wfwd/*(사용자 갱신 — 전방 원장 없음): %s" % f)
        fp = os.path.join(root, f)
        if (f in WB_ALLOWED or f in WFWD_ALLOWED) and os.path.isfile(fp):
            try:
                with io.open(fp, encoding="utf-8") as fh:
                    vl = value_lists(json.load(fh))
            except Exception as e:                                        # noqa: BLE001
                vl = ["읽지 못함(%s)" % type(e).__name__]
            if vl:
                bad.append("%s: 값 계열 같은 숫자 목록 %s" % (f, vl[:3]))
        if _w_file(f) and os.path.isfile(fp):
            with open(fp, "rb") as fh:
                blob = fh.read()
            em = [m.group(0) for m in EMAIL_RX.finditer(blob) if m.group(0) not in EMAIL_OK]
            if em:
                bad.append("%s: 전자우편 모양 문자열 %d개(SEC 연락처는 SEC_UA 환경변수로만 · U4)" % (f, len(em)))
    scan = [f for f in files if (("/" not in f and f.endswith(".html")) or (f.startswith("js/") and f.endswith(".js"))
                                 or (f.startswith("data/") and f.count("/") == 1 and f.endswith(".json")))]
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
            bad.append("사이트 자료 %s 에 배치 W 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성)
# ══════════════════════════════════════════════════════════════════════════
def _w(td, name, src):
    with io.open(os.path.join(td, name + ".py"), "w", encoding="utf-8") as f:
        f.write(src)


def _st_static():
    with tempfile.TemporaryDirectory() as td:
        _w(td, "w_a", "import w_b\n")
        _w(td, "w_b", "def f():\n    import helper\n")
        _w(td, "helper", "def g():\n    if True:\n        import t_core\n")
        _w(td, "t_core", "")
        _w(td, "w_c", "import importlib\ndef h():\n    importlib.import_module('qbatch_core')\n")
        _w(td, "w_d", "import numpy\nimport pit_like\n")
        _w(td, "pit_like", "import os\n")
        _w(td, "w_e", "import importlib\ndef h(x):\n    importlib.import_module(x)\n")
        r = noeg_static(td, ["w_a"])
        assert not r["ok"] and r["hits"] == ["w_a → w_b → helper → t_core"], r
        r2 = noeg_static(td, ["w_c"])
        assert not r2["ok"] and any("qbatch_core" in h for h in r2["hits"])
        r3 = noeg_static(td, ["w_d"])
        assert r3["ok"] and set(r3["reached"]) == {"w_d", "pit_like"}
        r4 = noeg_static(td, ["w_e"])
        assert r4["ok"] and r4["dynamic_imports"] == {"w_e": [3]}, r4             # 동적 import 는 보고(목록)
        _w(td, "w_f", "import w_cmp\n")
        _w(td, "w_cmp", "import eg30plus\nimport w_d\n")
        r5 = noeg_static(td, ["w_f"])
        assert not r5["ok"] and any("w_cmp" in s for s in r5["separate_violations"]), r5
        assert any("w_cmp ⇢ w_d" in s for s in r5["separate_violations"]), r5     # w_cmp 가 w_ 모듈에 닿으면 위반
        os.remove(os.path.join(td, "w_cmp.py"))
        _w(td, "w_g", "def f(D):\n    return D['cfo'] + D.get('logbm', 0)\n")
        r6 = noeg_static(td, ["w_g"])
        assert not r6["ok"] and [v for _, v in r6["literal_hits"]["w_g"]] == ["cfo", "logbm"], r6
        _w(td, "w_h", "import w_i\ndef f(p):\n    return w_i.fm(p, noeg=False)\n")
        _w(td, "w_i", "def fm(p, noeg=True):\n    return p\n")
        r7 = noeg_static(td, ["w_h"])
        assert not r7["ok"] and r7["noeg_bypass"] == {"w_h": [3]}, r7
        _w(td, "w_audit", "import w_i\ndef f(p):\n    return w_i.fm(p, noeg=False)\n")
        r8 = noeg_static(td, ["w_i"])
        assert r8["ok"], r8                                                     # w_audit 는 대상 밖 · 우회 허용
        _w(td, "w_j", "DOC = '''B/M 과 cfo 를 쓰지 않는다 — 긴 문서 문자열은 이름이 아니다'''\n")
        assert noeg_static(td, ["w_j"])["ok"]
        _w(td, "w_k", "import w_core as WC\ndef f():\n    return WC.frozen('eg_q5_x')\n")
        _w(td, "w_core", "def frozen(n):\n    return n\n")
        r9 = noeg_static(td, ["w_k"])
        assert not r9["ok"] and any("eg_q5_x" in h for h in r9["hits"]), r9                # frozen("…") 상수 인자도 따라간다
        r10 = noeg_static(td, ["w_d"], pins={"other"})
        assert not r10["ok"] and r10["unpinned"] == ["pit_like"], r10                     # 얼린 핀 밖 로컬 모듈에 닿으면 위반
        assert noeg_static(td, ["w_d"], pins={"pit_like"})["ok"]
    assert forbidden("eg_q5_vintage") and forbidden("qfwd_adapter") and forbidden("r_stagem") and forbidden("v_cmp") and forbidden("v_run")
    assert not forbidden("pit_panel") and not forbidden("v_tests") and not forbidden("w_stagem")
    assert runtime_check(["numpy", "pit_panel"])["ok"] and not runtime_check(["numpy", "eg30plus.x"])["ok"]
    assert not runtime_check(["r_stagem"])["ok"]
    return "전이(함수 · 조건 · import_module 상수 · 동적 보고) · 별도 과정 경계(w_cmp 양방향) · 문자열 상수 · noeg 우회 · sys.modules"


def _st_audit():
    install_open_audit()
    td = tempfile.mkdtemp(prefix="wg_probe_")
    try:
        paths = {"eg": os.path.join(td, "x_eg_q5_scores.json"), "fr": os.path.join(td, "Portfolios_Formed_on_BE-ME_CSV.zip"),
                 "ok": os.path.join(td, "pit_px.json")}
        for p in paths.values():
            with io.open(p, "w", encoding="utf-8") as f:
                f.write("x")
        _OPENED.clear()
        with io.open(paths["ok"], encoding="utf-8") as f:
            f.read()
        assert open_audit_check()["ok"]
        with io.open(paths["eg"], encoding="utf-8") as f:
            f.read()
        r = open_audit_check()
        assert not r["ok"] and r["n_black"] == 1
        _OPENED.clear()
        with io.open(paths["fr"], encoding="utf-8") as f:
            f.read()
        assert not open_audit_check()["ok"]
        _OPENED.clear()
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    assert black_path("C:/Temp/egff/raw/CIK1.json.gz")[0] and black_path("data/_fund_card.json")[0]
    assert black_path("C:/x/vbatch_cache/meta/french@2024-12__beme.json")[0] and black_path("F-F_Research_Data_Factors_CSV.zip")[0]
    assert not black_path("C:/x/vbatch_cache/meta/french@2024-12__ind49.json")[0] and not black_path("data/pit_px.json")[0]
    assert not black_path("C:/x/vbatch_cache/raw/companyfacts/CIK1.json.gz")[0]
    return "open 감사(EG 파일 · egff 폴더 · French B/M 정렬 · FF 요인 원천 · 깨끗한 파일 통과)"


def _st_units():
    bad_names = ["EG30", "Eg", "eg_rank", "QG30", "eg_q5", "dAsset", "asset_growth", "I/A", "capex", "cfo", "CF/P", "cf_p", "Cop", "accruals",
                 "ni_minus_cfo", "net_issuance", "dSh", "buyback", "B/M", "log_bm", "logBM", "BtM", "log q", "HML", "hml_loading", "ROE", "roa",
                 "dRoe", "CMA", "RMW"]
    for n in bad_names:
        assert unit_violation(unit(n)) is not None, n
    ok_names = ["log_me", "r1", "mom", "val", "ep", "sp", "beta", "segment", "regime", "leg", "rev", "ni", "tail_q10", "hi52", "ltr", "iqr",
                "ciq_beta", "frag", "geo_g", "b_dn", "ltd", "fomc_day"]
    for n in ok_names:
        assert unit_violation(unit(n)) is None, n
    # 개념 · 원천 단위
    assert unit_violation(unit("x", concept="B/M")) and unit_violation(unit("x", concept="ROE level")) and unit_violation(unit("x", concept="HML"))
    assert unit_violation(unit("x", concept="asset growth")) and unit_violation(unit("f", concept="investment_growth"))
    assert unit_violation(unit("x", source="data/_eg_q5_scores.json")) and unit_violation(unit("x", source="cache/french__beme.json"))
    assert unit_violation(unit("x", source="v_fund:cfo_ttm.json"))
    assert unit_violation(unit("x", concept="value_ep_sp")) is None and unit_violation(unit("x", source="data/pit_px.json")) is None
    # 허용 예외
    assert unit_violation(unit("sh", use="me_denominator")) is None and unit_violation(unit("sho", use="holding_ratio_denominator")) is None
    assert unit_violation(unit("sh", use="signal")) and unit_violation(unit("sho")) and unit_violation(unit("dsh", use="me_denominator"))
    assert unit_violation(unit("asset", concept="log_asset_level", use="kps_size")) is None
    assert unit_violation(unit("asset", use="signal")) and unit_violation(unit("asset", concept="asset growth", use="kps_size"))
    assert unit_violation(unit("log_asset", concept="log_asset_level", use="kps_size")) is None
    assert unit_violation(unit("eq", use="signal")) and unit_violation(unit("book_equity", use="control"))
    # assert_units
    try:
        assert_units([unit("log_me"), unit("logbm")], "st")
        raise AssertionError("logbm 통과")
    except SystemExit:
        pass
    n0 = len(_REGISTRY)
    assert assert_units([unit("log_me"), unit("val", concept="value_ep_sp")], "st") and len(_REGISTRY) == n0 + 2
    try:
        assert_bypass_allowed("selftest")
        raise AssertionError("w_guard 에서 우회 통과")
    except SystemExit:
        pass
    return "이름 %d · 개념 · 원천 · 허용 예외(sh · sho · log asset) · 통과 기록 · 우회 자물쇠" % len(bad_names)


def _st_site():
    assert value_lists({"a": [1, 2, 3, 4], "b": {"c": [1.0, 2, 3, 4, 5]}}) == ["/b/c"] and value_lists({"rows": [{"x": 1}, {"x": 2}]}) == []
    try:
        no_derivative_positions({"ESZ6": 1.0})
        raise AssertionError("ESZ6 통과")
    except SystemExit:
        pass
    for bad in ({"VIXY": 1.0}, {"SPX_PUT": 1.0}, {"MES": 1.0}, {"SPY251219C00600000": 1.0}):
        try:
            no_derivative_positions(bad)
            raise AssertionError("%s 통과" % bad)
        except SystemExit:
            pass
    assert no_derivative_positions({"AAPL": 0.5, "BRK.B": 0.5})
    td = tempfile.mkdtemp(prefix="wg_site_")
    try:
        if subprocess.run(["git", "init", "-q", td], capture_output=True).returncode != 0:
            return "값 계열 · G-DER(git 없음 — 저장소 판 생략)"
        os.makedirs(os.path.join(td, "data", "_wfwd"))
        os.makedirs(os.path.join(td, "build"))
        with io.open(os.path.join(td, "data", "_wb_f0.json"), "w", encoding="utf-8") as f:
            json.dump({"n": 3, "months": ["2016-08"]}, f)
        assert site_guard(td)["ok"], site_guard(td)
        with io.open(os.path.join(td, "data", "_wb_extra.json"), "w", encoding="utf-8") as f:
            json.dump({}, f)
        with io.open(os.path.join(td, "build", "w_x.py"), "w", encoding="utf-8") as f:
            f.write("UA = 'someone" + "@" + "example.org'\n")
        with io.open(os.path.join(td, "data", "_wb_f0.json"), "w", encoding="utf-8") as f:
            json.dump({"x": [0.1, 0.2, 0.3, 0.4, 0.5]}, f)
        with io.open(os.path.join(td, "data", "_wfwd", "genesis.json"), "w", encoding="utf-8") as f:
            json.dump({"cards": ["WF01S"]}, f)
        g = site_guard(td)
        kinds = " ".join(g["bad"])
        assert not g["ok"] and "허용 밖 data/_wb*" in kinds and "전자우편" in kinds and "값 계열" in kinds and "전방 원장" in kinds, g
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    return "값 계열 거르개 · G-DER · 사이트 가드(허용 밖 _wb · 값 계열 · 전자우편 모양 · 전방 원장 파일 없음)"


def _st_real_tree():
    r = noeg_static()
    if not r["ok"]:
        raise AssertionError("실제 W 모듈 정적 점검 실패: %s" % json.dumps({k: r[k] for k in ("hits", "separate_violations", "literal_hits",
                                                                                              "noeg_bypass", "unpinned")}, ensure_ascii=False)[:800])
    assert r["pins_checked"]
    install_open_audit()
    nr = noeg_report()
    assert nr["ok"] and nr["static"]["ok"] and nr["runtime"]["ok"], nr
    return "noeg_report 세 겹 참 · 실제 build/w_*.py %d개 · 닿은 로컬 모듈 %d(비-w 모두 얼린 V 핀 안) · 동적 import %s" % (len(r["targets"]), r["n_reached"],
                                                                                    r["dynamic_imports"] or "없음")


def selftest():
    res, ok = [], True
    for fn in (_st_static, _st_audit, _st_units, _st_site, _st_real_tree):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                        # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-14s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_guard selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--site" in sys.argv:
        g = site_guard()
        print(json.dumps(g, ensure_ascii=False))
        raise SystemExit(0 if g["ok"] else 1)
    if "--noeg" in sys.argv:
        r = noeg_static()
        print(json.dumps({k: r[k] for k in ("ok", "targets", "n_reached", "hits", "separate_violations", "literal_hits", "noeg_bypass",
                                            "unpinned", "pins_checked", "dynamic_imports")}, ensure_ascii=False))
        print("닿은 로컬 모듈: %s" % ", ".join(r["reached"]))
        raise SystemExit(0 if r["ok"] else 1)
    print(__doc__)
