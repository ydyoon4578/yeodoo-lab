# -*- coding: utf-8 -*-
"""build/w_audit.py — 배치 W 허용 목록 짝맞춤 감사(별도 과정 · 굽기 전 한 번): (1) 합성 짝맞춤 w_stagem ↔ r_stagem(1e−12)
(2) R1 · R2 Stage M 공개 값 재현(R 의 동결 입력 · R 통제 설정 · 1e−9) (3) R1 표지 지문(R 등록 OS 15,070 · CH 9,062) (4) V G-EGD 표 재현(w_cmp · 별도 과정).

설계 원본(구속): wbatch_research.json final.evaluation.pairing_audits —
  «w_stagem 이 R 의 동결 입력과 R 통제 설정으로 R1 · R2 Stage M 공개 값(γ −0.1723 · t −2.05 / −0.1538 · −1.04)을 1e−9 로 재현
   (이미 공개된 값의 재현 · 새 시행 아님 · 허용 목록 별도 과정)» · «w_r1 표지 지문 = R 등록 지문(R1 OS 15,070)» ·
  «w_cmp 가 V 의 F0 입력으로 V G-EGD 표를 그대로 재현» · build_plan.modules[w_audit] · no_import_rule(원본은 허용 목록 별도 과정에서만).

이 과정만 배치 R 원본(r_stagem · r_run — 그 안에서 eg30plus · qbatch_core)을 부른다(함수 안 · 합성 짝맞춤은 이 과정 · 실자료 재현은 자식 과정).
  W 굽기 · 연기 과정은 이 모듈을 부르지 않는다(w_guard 가 대상 폐포에서 본다). noeg=False(B/M 통제 우회)도 이 모듈만 — R 공개 값 재현에 R 통제
  (크기 · log B/M(결측 더미) · r_t · 12-2 · 섹터)가 필요해서다. 재현 결과는 **공개된 값과의 차**(참/거짓 · 최대 절대 차)만 적는다 — 새 통계를 찍지 않는다.
R 재현 자식 과정(--child-r): 배치 R 결과 커밋 958557496 의 깨끗한 작업 사본(기본 %TEMP%/wbatch_raudit_wt · $WBATCH_R_TREE)을 sys.path 맨 앞에 두고
  RBATCH_DATA = 그 트리의 data/(등록 커밋 168a072ff 의 자료 판 · 결과 뒤 바뀐 것은 V 파일 · _rbatch.json 뿐) · R 러너의 RealProvider 로 세계 · 패널 · 표지를
  다시 짓고 → 통제 패널 지문 · 쓸 달 sha · 표지 지문이 R 등록 F0 문서(data/_r_f0.json) · 결과(data/_rbatch.json)와 같은지 먼저 본다 →
  (가) R 설계(r_stagem._design) → w_stagem.fm · (나) w_stagem.design(R 통제 설정) → w_stagem.fm 두 길로 γ 월 계열 · 주 통계를 공개 값과 1e−9 로 대조.
  R 트리의 R 코드는 R 등록 커밋 blob 과 같아야 하고 트리는 깨끗해야 한다(git status).
🔎 R1 표지 지문: W13 은 사용자 갱신(가)으로 뺐다 → w_r1(EG 없는 재구현)은 짓지 않았다. 감사는 R 동결 입력의 표지 지문(OS = 1 인 (그룹, 달) 15,070 ·
  CH = 1 9,062 · fp_digest = R F0 문서)을 대조하고, build/w_r1.py 가 생기면 그 표지 집합도 같은지 본다.

  python build/w_audit.py                 짝맞춤 전부(합성 → R 재현 자식 → G-EGD 재현 자식)
  python build/w_audit.py --synthetic     합성 짝맞춤만(실자료 없음)
  python build/w_audit.py --r-repro       R1 · R2 재현만(자식 과정)
  python build/w_audit.py --gegd          V G-EGD 재현만(w_cmp 자식 과정)
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
PY = sys.executable
R_TREE = os.environ.get("WBATCH_R_TREE") or os.path.join(tempfile.gettempdir(), "wbatch_raudit_wt")
R_RESULT_COMMIT = "958557496fbb5935f3c93a05ea47dc0fdd7255a3"
R_REG_COMMIT = "168a072ff0b0ba8f895a79fd8dabaf34b35d8ed6"
R_CODE = ("build/r_run.py", "build/r_stagem.py", "build/r_r1_flags.py", "build/r_r2flags.py", "build/eg30plus.py", "build/pit_panel.py",
          "build/qbatch_core.py", "build/tech_backtest.py")
PUBLISHED = {"R1": {"mean": -0.1723, "nw_t": -2.05, "T": 116}, "R2": {"mean": -0.1538, "nw_t": -1.04, "T": 117}}   # 결과 문서 머리(반올림)
FINGERPRINT = {"R1": ("OS", 15070), "R2": ("CH", 9062)}
TOL_REPRO = 1e-9
TOL_SYN = 1e-12
PRIMARY_FIELDS = ("T", "mean", "sd", "nw_t", "nw_t_compressed", "gaps", "contiguous", "first", "last", "p_one")


def _cache(*parts):
    import w_core as WC
    return WC.cache_dir("audit", *parts)


def _git(tree, *a):
    return subprocess.run(["git", "-C", tree] + list(a), capture_output=True, text=True, encoding="utf-8")


def _eqv(a, b, tol):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str) or isinstance(b, str):
        return a == b
    return abs(float(a) - float(b)) <= tol


def _series_cmp(ms_a, g_a, ms_b, g_b, tol):
    """두 γ 월 계열 대조 — (같다, 최대 절대 차, 다른 곳 목록)."""
    if list(ms_a) != list(ms_b):
        return False, None, ["달 목록 다름(%d ≠ %d)" % (len(ms_a), len(ms_b))]
    worst, bad = 0.0, []
    for m, x, y in zip(ms_a, g_a, g_b):
        if x is None or y is None:
            if not (x is None and y is None):
                bad.append("%s None 짝 어긋남" % m)
            continue
        d = abs(float(x) - float(y))
        worst = max(worst, d)
        if d > tol:
            bad.append("%s %.3e" % (m, d))
    return not bad, worst, bad[:5]


# ══════════════════════════════════════════════════════════════════════════
#  (1) 합성 짝맞춤 — w_stagem ↔ r_stagem(이 과정 · 합성 입력만)
# ══════════════════════════════════════════════════════════════════════════
def synthetic():
    import r_stagem as RS                                                    # 허용 목록(이 과정만)
    import r_run as RR
    import w_stagem as WS
    import eg30plus as E
    rows = []

    def chk(name, fn):
        try:
            rows.append((name, bool(fn()), None))
        except Exception as e:                                               # noqa: BLE001
            rows.append((name, False, "%s: %s" % (type(e).__name__, str(e)[:200])))
    rng = np.random.default_rng(20260927)
    n = 200
    cols = [("const", np.ones(n)), ("a", rng.normal(0, 1, n)), ("b", rng.normal(0, 1, n))]
    cols.append(("ab", cols[1][1] + 2 * cols[2][1]))                          # 종속 열
    cols.append(("zero", np.zeros(n)))
    cols += [("s%d" % j, (rng.integers(0, 4, n) == j).astype(float)) for j in range(4)]   # 섹터 합 = 절편

    def c_basis():
        Qa, ka, da = WS.basis(cols)
        Qb, kb, db = RS._gs(cols)
        return ka == kb and da == db and np.allclose(Qa, Qb, atol=TOL_SYN, rtol=0)
    chk("basis ↔ _gs(종속 · 영 · 섹터)", c_basis)
    y = rng.normal(0, 5, n)
    fl = [("f1", (rng.random(n) < 0.2).astype(float)), ("f2", rng.normal(0, 1, n)), ("f3", cols[1][1] * 3.0)]   # f3 은 통제에 걸린다
    w = np.exp(rng.normal(0, 1, n))

    def c_solve():
        for ww in (None, w):
            a, b = WS.solve(y, cols, fl, ww), RS._solve(y, cols, fl, ww)
            if a["dof"] != b["dof"] or a["drop"] != b["drop"] or set(a["b"]) != set(b["b"]):
                return False
            for k in a["b"]:
                if not _eqv(a["b"][k], b["b"][k], TOL_SYN):
                    return False
            if abs(a["s"] - b["s"]) > TOL_SYN or abs(a["s_ctrl"] - b["s_ctrl"]) > TOL_SYN:
                return False
        return WS.solve(y[:12], [(nm, v[:12]) for nm, v in cols], [(nm, v[:12]) for nm, v in fl]) is None and \
            RS._solve(y[:12], [(nm, v[:12]) for nm, v in cols], [(nm, v[:12]) for nm, v in fl]) is None
    chk("solve ↔ _solve(OLS · WLS · 종속 신호 None · 자유도)", c_solve)
    months = RS.months_between("2016-08", "2026-07")
    x = rng.normal(-0.1, 0.8, len(months))
    ms2 = [m for j, m in enumerate(months) if j not in (18, 21)]
    x2 = np.delete(x, [18, 21])
    chk("nw_t ↔ eg30plus.nw_t", lambda: all(abs(WS.nw_t(x, L) - E.nw_t(x, L)) <= TOL_SYN for L in (3, 6)))
    chk("nw_t_gap ↔ r_stagem.nw_t_gap", lambda: abs(WS.nw_t_gap(ms2, x2) - RS.nw_t_gap(ms2, x2)) <= TOL_SYN and
        abs(WS.nw_t_gap(months, x) - RS.nw_t_gap(months, x)) <= TOL_SYN)

    def c_sum():
        g = [float(v) for v in x2]
        g[5] = None
        res = {"months": ms2, "g": {"OS": g}}
        a, b = WS.summarize(ms2, g, -1), RS.summarize(res, "OS")
        return all(_eqv(a.get(k), b.get(k), TOL_SYN) for k in PRIMARY_FIELDS)
    chk("summarize(방향 −1) ↔ r_stagem.summarize", c_sum)
    # 합성 R 패널 전체: r_stagem.fm ↔ w_stagem.fm(가 R 설계 · 나 W 설계 + R 통제 설정)
    prov = RR.SynthProvider(seed=11, eff={"R1": -0.6, "R2": -0.8})
    P = prov.P
    ms = list(P["months"])
    for card in ("R1", "R2"):
        spec = RS.SPECS[card]
        fp = prov.flags(card)

        def c_fm(card=card, spec=spec, fp=fp):
            r = RS.fm(P, fp, spec, ms)
            a = WS.fm(ms, lambda m: _r_designs(RS, P, fp, spec, m), list(spec["flags"]), "synth")
            b = WS.fm(ms, lambda m: _w_designs(RS, WS, P, fp, spec, m), list(spec["flags"]), "synth")
            ok = True
            for nm in spec["flags"]:
                ok &= _series_cmp(r["months"], r["g"][nm], a["months"], a["g"][nm], TOL_SYN)[0]
                ok &= _series_cmp(r["months"], r["g"][nm], b["months"], b["g"][nm], TOL_SYN)[0]
            sa = WS.summarize(a["months"], a["g"][spec["focal"]], -1)
            sr = r["sum"][spec["focal"]]
            return ok and all(_eqv(sa.get(k), sr.get(k), TOL_SYN) for k in PRIMARY_FIELDS)
        chk("fm 전체 %s(합성 R 패널 · 두 길)" % card, c_fm)
    return rows


def _r_designs(RS, P, fp, spec, m):
    """(가) R 설계 그대로(r_stagem._design) → w_stagem 설계 모양."""
    D = P["m"].get(m)
    if D is None:
        return None
    out = []
    for k in spec["jt"]:
        y, cols, fl, _, _ = RS._design(D, fp, m, k, spec)
        out.append({"y": y, "ctrl": cols, "focal": fl, "w": None})
    return out


def _w_designs(RS, WS, P, fp, spec, m):
    """(나) w_stagem.design 에 R 통제 설정(크기 · log B/M 결측 더미 · r_t · 12-2 · 섹터 · 표지 모름 더미)을 넣는다 — B/M 이 들어 G-NoEG 우회(noeg=False ·
    이 모듈만 허용 · 실행 중 자물쇠는 주 스크립트가 w_audit 인지 본다)."""
    D = P["m"].get(m)
    if D is None:
        return None
    ctrl = [(c, D[c]) for c in RS.BASE_CTRL]
    miss = {c: RS.MISS.get(c, "dummy") for c in RS.BASE_CTRL}
    out = []
    for k in spec["jt"]:
        fl = [(f, RS._flag_vec(D, fp, m, k, f)) for f in spec["flags"]]
        out.append(WS.design(D["y"], fl, ctrl, miss, sectors=D["sec"], focal_miss="dummy", noeg=False, where="R 공개 값 재현(w_audit)"))
    return out


# ══════════════════════════════════════════════════════════════════════════
#  (2)(3) R1 · R2 재현 — 자식 과정(R 트리 · RBATCH_DATA)
# ══════════════════════════════════════════════════════════════════════════
def r_tree_check(tree=R_TREE):
    """R 트리: HEAD = R 결과 커밋 · 추적 파일 변경 없음 · R 코드 blob = R 등록 커밋 판."""
    bad = []
    h = _git(tree, "rev-parse", "HEAD").stdout.strip()
    if h != R_RESULT_COMMIT:
        bad.append("HEAD %s ≠ R 결과 커밋" % h[:12])
    st = [x for x in _git(tree, "status", "--porcelain", "--untracked-files=no").stdout.splitlines() if x.strip()]
    if st:
        bad.append("추적 파일 변경 %d" % len(st))
    for p in R_CODE:
        a = _git(tree, "rev-parse", "%s:%s" % (R_REG_COMMIT, p)).stdout.strip()
        b = _git(tree, "hash-object", os.path.join(tree, p)).stdout.strip()
        if not a or a != b:
            bad.append("%s ≠ R 등록 판" % p)
    return {"ok": not bad, "bad": bad, "head": h}


def child_r(tree, out_path):
    """자식 과정 본체 — R 동결 입력을 다시 짓고 두 길로 재현 · 결과 파일에는 대조(참/거짓 · 차)만."""
    t0 = time.time()
    rb, rdata = os.path.join(tree, "build"), os.path.join(tree, "data")
    os.environ["RBATCH_DATA"] = rdata
    os.environ["RBATCH_REPO"] = tree
    sys.path.insert(0, rb)
    import w_core as WC
    import w_stagem as WS
    import w_guard as WG
    WG.install_open_audit()
    import r_run as RR                                                      # R 트리(허용 목록 · 이 과정만)
    RS = RR._S()
    if os.path.normcase(os.path.dirname(os.path.abspath(RS.__file__))) != os.path.normcase(os.path.abspath(rb)):
        raise SystemExit("🚨 r_stagem 이 R 트리에서 오지 않았다")
    with io.open(os.path.join(rdata, "_rbatch.json"), encoding="utf-8") as f:
        doc = json.load(f)
    with io.open(os.path.join(rdata, "_r_f0.json"), encoding="utf-8") as f:
        f0doc = json.load(f)
    rep = {"kind": "w_audit.r_repro", "tree": tree, "tol": TOL_REPRO, "checks": {}, "cards": {}}
    prov = RR.RealProvider()
    P = prov.P
    cov = RS.f0_coverage(P)
    months = cov["months"]
    msha, digest = RR._sha_json(list(months)), RS.panel_digest(P)
    rep["checks"]["months_sha"] = msha == doc["panel"]["months_sha"] == f0doc["months_sha"]
    rep["checks"]["panel_digest"] = digest == doc["panel"]["digest"] == f0doc["panel_digest"]
    rep["checks"]["T"] = len(months) == doc["panel"]["T"] == 117
    fps = {c: prov.flags(c) for c in ("R1", "R2")}
    rep["checks"]["flags_sha"] = {c: RR.fp_digest(fps[c]) == f0doc["flags_sha"][c] for c in fps}
    fpr = {}
    for c, (flag, want) in FINGERPRINT.items():
        n1 = sum(1 for _, rec in fps[c].items() if (rec or {}).get(flag) == 1)
        agree = ((doc["f0"]["stage_s"].get(c) or {}).get("flag_agree") or {}).get("stage_m")
        fpr[c] = {"flag": flag, "n_active": n1, "registered": want, "doc_stage_m": agree, "ok": n1 == want == agree}
    rep["fingerprint"] = fpr
    w_r1 = os.path.join(HERE, "w_r1.py")
    rep["w_r1"] = "없음 — W13 을 뺐다(사용자 갱신 가) · R 동결 입력 지문만 대조" if not os.path.isfile(w_r1) else "있음 — 아래 w_r1_same"
    if os.path.isfile(w_r1):
        import w_r1 as W1                                                   # noqa: F401 — 표지 집합 대조(있을 때만)
        a = {(str(g), m) for (g, m), rec in fps["R1"].items() if (rec or {}).get("OS") == 1}
        b = set(W1.r1_os_set()) if hasattr(W1, "r1_os_set") else None
        rep["w_r1_same"] = (b is not None and a == b)
    if not all([rep["checks"]["months_sha"], rep["checks"]["panel_digest"], rep["checks"]["T"]] + list(rep["checks"]["flags_sha"].values())):
        rep["ok"] = False
        rep["why"] = "R 동결 입력을 다시 짓지 못했다(지문 어긋남) — 재현을 돌리지 않는다"
        _write(out_path, rep)
        return rep
    for card in ("R1", "R2"):
        spec = RS.SPECS[card]
        focal = RR.FOCAL[card]
        names = list(spec["flags"])
        fp = fps[card]
        ref_s = doc["stage_m"][card]["series"]["main"]
        ref_p = doc["stage_m"][card]["primary"]
        out = {}
        for path, fn in (("A_r_design", lambda m: _r_designs(RS, P, fp, spec, m)),
                         ("B_w_design", lambda m: _w_designs(RS, WS, P, fp, spec, m))):
            res = WS.fm(months, fn, names, "r_repro")
            ser = {nm: _series_cmp(ref_s["months"], ref_s["g"][nm], res["months"], res["g"][nm], TOL_REPRO) for nm in names}
            s = WS.summarize(res["months"], res["g"][focal], -1)
            prim = {k: {"ok": _eqv(s.get(k), ref_p.get(k), TOL_REPRO), "diff": (abs(s[k] - ref_p[k]) if isinstance(s.get(k), float)
                                                                            and isinstance(ref_p.get(k), float) else None)}
                    for k in PRIMARY_FIELDS}
            out[path] = {"series_ok": all(v[0] for v in ser.values()), "series_max_abs": max((v[1] or 0.0) for v in ser.values()),
                         "series_bad": {nm: v[2] for nm, v in ser.items() if v[2]}, "primary_ok": all(v["ok"] for v in prim.values()),
                         "primary_max_abs": max((v["diff"] or 0.0) for v in prim.values()),
                         "primary_bad": [k for k, v in prim.items() if not v["ok"]], "n_months": len(res["months"])}
        pub = PUBLISHED[card]
        out["published"] = {"mean": ref_p["mean"], "nw_t": ref_p["nw_t"], "T": ref_p["T"],
                            "head_ok": round(ref_p["mean"], 4) == pub["mean"] and round(ref_p["nw_t"], 2) == pub["nw_t"] and ref_p["T"] == pub["T"]}
        out["ok"] = all(out[p]["series_ok"] and out[p]["primary_ok"] for p in ("A_r_design", "B_w_design")) and out["published"]["head_ok"]
        rep["cards"][card] = out
    rep["loaded_w_frozen"] = WC.loaded_frozen_check(dirs=(HERE,))
    rep["open_audit_note"] = "허용 목록 과정 — R 재현이 EG 계보 파일을 연다(보고만 · 굽기 과정 감사와 다름)"
    rep["n_opened"] = len(WG.opened_paths())
    rep["ok"] = all(v["ok"] for v in rep["cards"].values()) and all(v["ok"] for v in fpr.values()) and rep["loaded_w_frozen"]["ok"]
    rep["sec"] = round(time.time() - t0, 1)
    _write(out_path, rep)
    return rep


def _write(p, doc):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, default=str)


def r_repro(tree=R_TREE):
    """R 재현 — R 트리 점검 → 자식 과정(스레드 1 · 해시 씨앗 0) → 결과 파일 요약."""
    import w_core as WC
    tc = r_tree_check(tree)
    if not tc["ok"]:
        return {"ok": False, "why": "R 트리 점검 실패", "tree_check": tc}
    out = _cache("r_repro.json")
    if os.path.exists(out):
        os.remove(out)
    env = WC.pin_env()
    env.pop("RBATCH_COMMIT", None)
    env.pop("RBATCH_P0", None)
    t0 = time.time()
    p = subprocess.run([PY, "-X", "utf8", os.path.abspath(__file__), "--child-r", "--tree", tree, "--out", out], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    if p.returncode != 0 or not os.path.exists(out):
        return {"ok": False, "why": "자식 과정 실패(종료 %s)" % p.returncode, "stderr": p.stderr[-1500:], "tree_check": tc}
    with io.open(out, encoding="utf-8") as f:
        rep = json.load(f)
    rep["tree_check"] = tc
    rep["wall_sec"] = round(time.time() - t0, 1)
    return rep


# ══════════════════════════════════════════════════════════════════════════
#  (4) V G-EGD 재현 — w_cmp 자식 과정
# ══════════════════════════════════════════════════════════════════════════
def gegd_repro():
    import w_core as WC
    vcmp = _git(ROOT, "rev-parse", "%s:build/v_cmp.py" % WC.V_COMMIT).stdout.strip()
    vcmp_now = WC.blob_sha1(os.path.join(HERE, "v_cmp.py")) if os.path.isfile(os.path.join(HERE, "v_cmp.py")) else None
    out = _cache("gegd_repro_v.json")
    p = subprocess.run([PY, "-X", "utf8", os.path.join(HERE, "w_cmp.py"), "--repro-v", "--out", out], env=WC.pin_env(),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    line = [x for x in p.stdout.splitlines() if x.startswith("W_CMP_REPRO ")]
    if not line:
        return {"ok": False, "why": "w_cmp 자식 실패(종료 %s)" % p.returncode, "stderr": p.stderr[-1200:]}
    r = json.loads(line[-1][len("W_CMP_REPRO "):])
    r["v_cmp_blob_at_v_commit"] = vcmp
    r["v_cmp_blob_same"] = (vcmp == vcmp_now)
    r["ok"] = bool(r.get("ok") and p.returncode == 0)
    return r


# ══════════════════════════════════════════════════════════════════════════
#  주 흐름
# ══════════════════════════════════════════════════════════════════════════
def main(argv):
    if "--child-r" in argv:
        tree = argv[argv.index("--tree") + 1]
        out = argv[argv.index("--out") + 1]
        rep = child_r(tree, out)
        print("W_AUDIT_R ok=%s sec=%s" % (rep.get("ok"), rep.get("sec")))
        return 0
    do_all = not any(a in argv for a in ("--synthetic", "--r-repro", "--gegd"))
    summary, ok = {}, True
    if do_all or "--synthetic" in argv:
        rows = synthetic()
        for nm, good, err in rows:
            print("  %s %-44s %s" % ("✓" if good else "✗", nm, err or ""))
        summary["synthetic"] = {"ok": all(r[1] for r in rows), "n": len(rows), "n_ok": sum(1 for r in rows if r[1])}
        ok &= summary["synthetic"]["ok"]
        print("합성 짝맞춤 %d/%d(1e−12)" % (summary["synthetic"]["n_ok"], len(rows)))
    if do_all or "--r-repro" in argv:
        r = r_repro()
        summary["r_repro"] = r
        ok &= bool(r.get("ok"))
        if r.get("cards"):
            for c, v in r["cards"].items():
                print("  %s %s 재현 — 가 R 설계: 계열 %s(최대 차 %.1e) · 주 통계 %s(최대 차 %.1e) · 나 W 설계: 계열 %s(%.1e) · 주 통계 %s(%.1e) · "
                      "공개 γ %.4f · t %.2f · T %d"
                      % ("✓" if v["ok"] else "✗", c, v["A_r_design"]["series_ok"], v["A_r_design"]["series_max_abs"], v["A_r_design"]["primary_ok"],
                         v["A_r_design"]["primary_max_abs"], v["B_w_design"]["series_ok"], v["B_w_design"]["series_max_abs"],
                         v["B_w_design"]["primary_ok"], v["B_w_design"]["primary_max_abs"], v["published"]["mean"], v["published"]["nw_t"],
                         v["published"]["T"]))
            for c, v in (r.get("fingerprint") or {}).items():
                print("  %s %s 표지 지문 %s = %d(등록 %d · 결과 문서 %s)" % ("✓" if v["ok"] else "✗", c, v["flag"], v["n_active"], v["registered"],
                                                                     v["doc_stage_m"]))
            print("  R 동결 입력 지문: %s" % json.dumps(r.get("checks"), ensure_ascii=False))
        else:
            print("  ✗ R 재현 실패: %s" % json.dumps({k: r.get(k) for k in ("why", "tree_check", "stderr")}, ensure_ascii=False)[:1500])
    if do_all or "--gegd" in argv:
        g = gegd_repro()
        summary["gegd"] = g
        ok &= bool(g.get("ok"))
        print("  %s V G-EGD 재현(w_cmp) — 카드 %s · 최대 차 %s · EG 입력 핀 %s · v_cmp blob V 판 같음 %s"
              % ("✓" if g.get("ok") else "✗", g.get("n_cards"), g.get("max_abs_diff"), g.get("eg_inputs_same"), g.get("v_cmp_blob_same")))
    p = _cache("w_audit_summary.json")
    _write(p, summary)
    print("w_audit %s → %s" % ("통과" if ok else "실패", p))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
