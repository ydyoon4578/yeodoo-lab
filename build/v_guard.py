# -*- coding: utf-8 -*-
"""build/v_guard.py — 배치 V 가드: G-NoEG(정적 전이 · 함수 안 import 포함 · 실행 sys.modules · 파일 열기 감사) · G-DER · G-TURN 도우미.

설계 원본(구속): vbatch_research.json final.build_plan.guards(G-NoEG (1)~(4) · G-DER · G-TURN) · no_import_rule · may_import · D22.
  (1) 정적: 대상 v_ 모듈과 그것이 부르는 랩 모듈 전부의 AST 를 전이적으로(함수 · 메서드 · 조건 안 import 까지) 훑어 금지 목록이 없어야 한다.
      금지 = t_core · t_data · t_signals · u_data · qfwd_* · eg30plus · qg_lab · qbatch_* · q_switch · eg_q5* · idxeg · eg_best · r_stages · r_r1_flags · r_r2flags
      + 배치 U 모듈(u_core · u_cards · u_run · u_web · u_tests · u_guard — 취소된 EG30 계보 · 소스 복사만 허용).
      v_cmp(EG30 · QG30 비교 줄 · G-EGD)는 어떤 v_ 모듈도 부르지 않고, v_cmp 도 v_ 모듈을 부르지 않는다(별도 프로세스). v_audit 도 대상 밖(허용 목록 · 별도 프로세스).
      importlib.import_module · __import__ 의 상수 인자도 따라간다 · 상수가 아닌 동적 import 는 목록으로 보고한다.
  (2) 실행: 연기 · 굽기 프로세스 끝에 sys.modules 에 금지 모듈이 없어야 한다(runtime_check).
  (3) 파일: open 감사(sys.addaudithook)로 _eg_q5* · _eg30plus · _qfwd · V0 핀 파일을 읽지 않았는지(v_cmp 제외).
  (4) 명세: data/_vb_manifest.json 에 그 파일이 없다(v_data.assert_no_eg_files).
  G-DER: 모든 보유 표식에 파생(선물 · 옵션 · 변동성 ETF) 없음 · G-TURN: 편도 연 10 이하.

  python build/v_guard.py --noeg            대상 v_ 모듈 전부 정적 전이 점검(참/거짓 · 닿은 로컬 모듈 수 · 동적 import 목록)
  python build/v_guard.py --selftest
"""
from __future__ import annotations

import ast
import fnmatch
import io
import json
import os
import re
import sys
import traceback

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
FORBIDDEN_MODULES = ("t_core", "t_data", "t_signals", "u_data", "qfwd_*", "eg30plus", "qg_lab", "qbatch_*", "q_switch", "eg_q5*", "idxeg",
                     "eg_best", "r_stages", "r_r1_flags", "r_r2flags", "u_core", "u_cards", "u_run", "u_web", "u_tests", "u_guard")
SEPARATE_PROCESS = ("v_cmp", "v_audit")                     # 허용 목록 별도 프로세스 — 다른 v_ 모듈과 서로 부르지 않는다
EG_FILE_MARKS = ("_eg_q5", "_eg30plus", "_qfwd", "_eg_best", "_idxeg", "_qbatch", "_qg_", "v0_pin", "_fund_card")   # _fund_card = QG30 규칙 카드(검토 고침)
EG_DIR_MARKS = ("egff",)                                     # EG 계보 빌드의 원 캐시 폴더(%TEMP%/egff) — V 는 핀 사본(캐시 raw/companyfacts)만 읽는다(검토 고침)
DERIV_HOLD = re.compile(r"(?i)(=F$|\bES[HMUZ]\d|\bMES\b|\bVIX|VXX|UVXY|SVXY|VIXY|VXZ|\bXYLD\b|\bQYLD\b|\bBXM|_PUT\b|\bOPT:|option|future)")
TURN_MAX = 10.0


def forbidden(name):
    base = name.split(".")[0]
    return any(fnmatch.fnmatch(base, pat) for pat in FORBIDDEN_MODULES)


def _imports_of(path):
    """파일 하나의 import 이름 전부(깊이 무관 · 함수 안 포함) · 동적 import(상수 아님) 목록."""
    import warnings
    src = io.open(path, encoding="utf-8").read()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)                  # 랩 모듈 문자열의 잘못된 이스케이프 경고 — 점검과 무관
        tree = ast.parse(src)
    names, dyn = set(), []
    for nd in ast.walk(tree):
        if isinstance(nd, ast.Import):
            for a in nd.names:
                names.add(a.name)
        elif isinstance(nd, ast.ImportFrom):
            if nd.level == 0 and nd.module:
                names.add(nd.module)
            elif nd.level and nd.module:
                names.add(nd.module)
        elif isinstance(nd, ast.Call):
            fn = nd.func
            fname = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else None)
            if fname in ("import_module", "__import__"):
                if nd.args and isinstance(nd.args[0], ast.Constant) and isinstance(nd.args[0].value, str):
                    names.add(nd.args[0].value)
                else:
                    dyn.append(nd.lineno)
    return names, dyn


def local_module(name, root=HERE):
    p = os.path.join(root, name.split(".")[0] + ".py")
    return p if os.path.exists(p) else None


def transitive(targets, root=HERE):
    """대상 모듈(이름 목록)에서 닿는 로컬 모듈 전부 — {이름: (부른 쪽 이름 경로)} · 금지 적중 · 동적 import."""
    seen, hits, dyn, via = set(), [], {}, {}
    stack = [(t, (t,)) for t in targets]
    while stack:
        name, path = stack.pop()
        base = name.split(".")[0]
        if base in seen:
            continue
        if forbidden(base):
            hits.append(" → ".join(path))
            continue
        p = local_module(base, root)
        if p is None:
            continue                                            # 표준 · 제3자 라이브러리
        seen.add(base)
        via[base] = path
        names, d = _imports_of(p)
        if d:
            dyn[base] = d
        for n in sorted(names):
            b = n.split(".")[0]
            if b not in seen:
                stack.append((b, path + (b,)))
    return {"reached": sorted(seen), "hits": sorted(set(hits)), "dynamic": dyn, "via": via}


def reach(targets, root=HERE):
    """금지 목록과 무관하게 대상에서 닿는 로컬 모듈 전부(전이 · 함수 안 import 포함) — 별도 프로세스 경계 점검용."""
    seen, stack = set(), list(targets)
    while stack:
        base = stack.pop().split(".")[0]
        if base in seen:
            continue
        p = local_module(base, root)
        if p is None:
            continue
        seen.add(base)
        names, _ = _imports_of(p)
        stack += [n.split(".")[0] for n in names if n.split(".")[0] not in seen]
    return seen


def v_targets(root=HERE):
    return sorted(fn[:-3] for fn in os.listdir(root) if fn.startswith("v_") and fn.endswith(".py") and fn[:-3] not in SEPARATE_PROCESS)


def noeg_static(root=HERE, targets=None):
    """G-NoEG (1) — 대상 v_ 모듈 전부의 전이 폐포에 금지 모듈이 없고 · 별도 프로세스 모듈을 서로 부르지 않는다."""
    targets = targets or v_targets(root)
    T = transitive(targets, root)
    sep = []
    for m in targets:
        names, _ = _imports_of(os.path.join(root, m + ".py"))
        sep += ["%s → %s" % (m, n) for n in names if n.split(".")[0] in SEPARATE_PROCESS]
    for m in ("v_cmp",):                                         # v_audit 는 짝맞춤을 위해 v_ 복사본과 원본을 함께 부른다(허용 목록 · 별도 프로세스) — 반대 방향만 막는다
        p = local_module(m, root)
        if p:
            names, _ = _imports_of(p)
            sep += ["%s → %s" % (m, n) for n in names if n.split(".")[0].startswith("v_") and n.split(".")[0] not in SEPARATE_PROCESS]
    # v_cmp 는 전이적으로도 v_ 모듈에 닿지 않는다(EG 계보를 부르는 유일한 모듈 · 함수 안 import 포함) — 반대 방향은 위 T(대상 폐포)에 v_cmp 가 없어야 한다
    p = local_module("v_cmp", root)
    if p:
        bad = sorted(x for x in reach(["v_cmp"], root) if x.startswith("v_") and x != "v_cmp")
        sep += ["v_cmp ⇢ %s(전이)" % x for x in bad]
    sep += ["%s ⇢ %s(전이)" % ("대상 폐포", x) for x in T["reached"] if x in SEPARATE_PROCESS]
    ok = not T["hits"] and not sep
    return {"ok": ok, "targets": targets, "n_reached": len(T["reached"]), "reached": T["reached"], "hits": T["hits"], "separate_violations": sep,
            "dynamic_imports": T["dynamic"]}


def runtime_check(mods=None):
    """G-NoEG (2) — sys.modules 에 금지 모듈이 없어야 한다."""
    mods = list(sys.modules) if mods is None else list(mods)
    bad = sorted({m.split(".")[0] for m in mods if forbidden(m.split(".")[0])})
    return {"ok": not bad, "loaded_forbidden": bad}


_OPENED = []


def install_open_audit():
    """G-NoEG (3) — open 감사 고리(한 번만). 열린 경로를 모은다."""
    if getattr(install_open_audit, "_on", False):
        return
    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            _OPENED.append(os.fsdecode(args[0]))
    sys.addaudithook(hook)
    install_open_audit._on = True


def _eg_path(p):
    parts = [x.lower() for x in re.split(r"[\\/]+", str(p)) if x]
    return any(mk in os.path.basename(p) for mk in EG_FILE_MARKS) or any(d in parts[:-1] for d in EG_DIR_MARKS)


def open_audit_check():
    """G-NoEG (3) — 이 과정에서 열린 파일 가운데 EG 파일(이름 표식) · EG 원 캐시 폴더(경로 조각) — 범위는 고리를 건 과정(굽기 · F0 자식)뿐이다."""
    bad = sorted({p for p in _OPENED if _eg_path(p)})
    return {"ok": not bad, "n_opened": len(_OPENED), "eg_files_opened": bad[:5]}


def no_derivative_positions(book):
    """G-DER — 보유 표식(키)에 파생 표식이 없다. book = {보유 표식: 비중}."""
    bad = [k for k in book if DERIV_HOLD.search(str(k))]
    if bad:
        raise SystemExit("🚨 파생 보유 표식(주식 중심 위반): %s" % ", ".join(map(str, bad[:5])))
    return True


def turnover_ok(tau_annual):
    """G-TURN — 편도 연 회전 ≤ 10(사용자 규칙 2026-08-24 · G5e)."""
    return tau_annual is not None and tau_annual <= TURN_MAX


VB_ALLOWED = {"data/_vb_manifest.json", "data/_vb_lit_open.json", "data/_vb_f0.json"}   # 저장소 data/_vb* 에 허용하는 공개 안전 파일(더할 때 여기에 적는다)
VFWD_ALLOWED = {"data/_vfwd/genesis.json"}                   # VFWD 창세(등록 커밋이 더한다 · 카드 · 규칙 · 관문 · 핀 — 값 계열 없음) — 원장 파일은 VFWD 등록이 여기에 더한다
#   data/_vb_f0.json = v_run --f0 이 쓰는 F0 결정 · 셈(비중 · 개수 · 날짜 · 라벨만 · L 층 수치 없음 · 등록 커밋이 더한다)
LICENSED_NAME_MARKS = ("F-F_Research_Data_Factors", "Portfolios_Formed_on_", "6_Portfolios_", "25_Portfolios_", "10_Portfolios_",
                       "_Industry_Portfolios", "companyfacts", "CIK00", "vd1/", "wide_ledger")
L_OUTPUT_MARKS = ("_vbatch", "_vb_L", "_vb_f0_L")
# 굽기 산출 표식(v_run — 산출 파일 이름 · 게시 칸 표지) — 사이트 자료(뿌리 *.html · js/*.js · data/*.json)에 있으면 산출이 새어 든 것이다
OUTPUT_CONTENT_MARKS = (b"_vbatch.json", b"_vbatch.public.json", b"_vbatch.run.json", b'"vbatch_public_view"', b'"vbatch_full_out"')


def value_lists(doc, path="", max_len=4):
    """공개 명세의 값 계열 같은 숫자 목록(숫자 다섯 개 넘는 목록) 경로 — 표준 라이브러리만(validate_site 가 부른다 · v_data._no_value_series 와 같은 문턱)."""
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


def site_guard(root=None):
    """D1 저장소 쪽 점검(표준 라이브러리만 — build/validate_site.py 가 매 푸시 · 매일 부른다 · v_run.frozen_check 도 부른다) —
    git 이 추적 · 추가 예정인 파일 가운데 (가) 라이선스 원자료로 보이는 이름 (나) L 층 산출 이름(_vbatch* …) (다) 허용 밖 data/_vb* ·
    (라) data/_vb* 공개 명세의 값 계열(숫자 다섯 개 넘는 목록) (마) 사이트 자료의 굽기 산출 표식이 없어야 한다. 돌려주는 것 {ok, bad[], n_files, n_scanned}."""
    import subprocess
    root = root or os.path.dirname(HERE)
    p = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        return {"ok": False, "bad": ["git ls-files 실패"], "n_files": 0, "n_scanned": 0}
    bad = []
    files = [x for x in p.stdout.splitlines() if x]
    for f in files:
        b = os.path.basename(f)
        if any(mk in f for mk in LICENSED_NAME_MARKS):
            bad.append("라이선스 원자료로 보이는 파일: %s" % f)
        if any(b.startswith(mk) for mk in L_OUTPUT_MARKS):
            bad.append("L 층 산출 이름: %s" % f)
        if f.startswith("data/_vb") and f not in VB_ALLOWED:
            bad.append("허용 밖 data/_vb*: %s" % f)
        if f.startswith("data/_vfwd/") and f not in VFWD_ALLOWED:
            bad.append("허용 밖 data/_vfwd/*: %s" % f)
        if (f in VB_ALLOWED or f in VFWD_ALLOWED) and os.path.exists(os.path.join(root, f)):
            try:
                with io.open(os.path.join(root, f), encoding="utf-8") as fh:
                    vl = value_lists(json.load(fh))
            except Exception as e:                                        # noqa: BLE001
                vl = ["읽지 못함(%s)" % type(e).__name__]
            if vl:
                bad.append("%s: 값 계열 같은 숫자 목록 %s" % (f, vl[:3]))
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
            bad.append("사이트 자료 %s 에 배치 V 굽기 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:20], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


def _st_static():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        def w(n, s):
            io.open(os.path.join(td, n + ".py"), "w", encoding="utf-8").write(s)
        w("v_a", "import v_b\n")
        w("v_b", "def f():\n    import helper\n")
        w("helper", "def g():\n    if True:\n        import t_core\n")
        w("t_core", "")
        w("v_c", "import importlib\ndef h():\n    importlib.import_module('qbatch_core')\n")
        w("v_d", "import numpy\nimport pit_like\n")
        w("pit_like", "import os\n")
        w("v_cmp", "import eg30plus\n")
        r = noeg_static(td, ["v_a"])
        assert not r["ok"] and any("t_core" in h for h in r["hits"]), r
        assert "v_a → v_b → helper → t_core" in r["hits"][0]
        r2 = noeg_static(td, ["v_c"])
        assert not r2["ok"] and any("qbatch_core" in h for h in r2["hits"])
        r3 = noeg_static(td, ["v_d"])
        assert r3["ok"] and set(r3["reached"]) == {"v_d", "pit_like"}
        w("v_e", "import v_cmp\n")
        r4 = noeg_static(td, ["v_e"])
        assert not r4["ok"] and r4["separate_violations"]
    assert forbidden("eg_q5_vintage") and forbidden("qfwd_adapter") and forbidden("qbatch_run") and not forbidden("pit_panel") and not forbidden("t_pit")
    assert runtime_check(["numpy", "pit_panel"])["ok"] and not runtime_check(["numpy", "eg30plus.x"])["ok"]
    assert no_derivative_positions({"AAPL": 0.5, "BRK.B": 0.5})
    for bad in ({"ESZ6": 1.0}, {"VIXY": 1.0}, {"SPX_PUT": 1.0}, {"MES": 1.0}):
        try:
            no_derivative_positions(bad)
            raise AssertionError("%s 통과" % bad)
        except SystemExit:
            pass
    assert turnover_ok(9.9) and not turnover_ok(10.1) and not turnover_ok(None)
    assert value_lists({"a": [1, 2, 3, 4], "b": {"c": [1.0, 2, 3, 4, 5]}}) == ["/b/c"] and value_lists({"rows": [{"x": 1}, {"x": 2}]}) == []
    return ("전이 점검(함수 · 조건 안 import · import_module 상수) · 별도 프로세스 경계(v_cmp 전이 · 대상 폐포에 v_cmp 없음) · 실행 sys.modules · G-DER · G-TURN · "
            "값 계열 거르개(표준 라이브러리)")


def _st_audit():
    install_open_audit()
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "vb_guard_probe_eg30plus_x.txt")
    io.open(p, "w", encoding="utf-8").write("x")
    io.open(p, encoding="utf-8").read()
    r = open_audit_check()
    assert not r["ok"]
    _OPENED.clear()
    os.remove(p)
    assert open_audit_check()["ok"]
    assert _eg_path("C:/Temp/egff/raw/CIK0000000001.json.gz") and _eg_path(r"C:\Temp\egff\raw\CIK1.json.gz") and _eg_path("data/_fund_card.json") and not _eg_path("C:/x/vbatch_cache/raw/companyfacts/CIK1.json.gz")
    return "open 감사 고리(EG 파일 열기 잡음 · _fund_card · egff 원 캐시 폴더)"


def selftest():
    res, ok = [], True
    for fn in (_st_static, _st_audit):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-10s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_guard selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
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
        print(json.dumps({k: r[k] for k in ("ok", "targets", "n_reached", "hits", "separate_violations", "dynamic_imports")}, ensure_ascii=False))
        print("닿은 로컬 모듈: %s" % ", ".join(r["reached"]))
        raise SystemExit(0 if r["ok"] else 1)
    print(__doc__)
