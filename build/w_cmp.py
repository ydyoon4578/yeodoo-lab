# -*- coding: utf-8 -*-
"""build/w_cmp.py — 배치 W 비교 모듈(허용 목록 유일 · 별도 과정): G-EGD 정의 관문(EG30 · QG30 대 W 카드 θ = 1 책 · F0 · 수익 없음 · fail-closed) ·
V G-EGD 표 재현(짝맞춤 감사) · EG30 비교선(굽기 뒤 보고만).

설계 원본(구속): wbatch_research.json final.slate.common_frame.G_EGD(«V 정의 관문 그대로 … 계산은 w_cmp(v_cmp 논리의 복사본 · 별도 과정 ·
  EG 파일을 여는 유일한 W 과정) · 넘으면 «EG30-근접» → 측정만») · evaluation.pairing_audits(«w_cmp 가 V 의 F0 입력으로 V G-EGD 표를 그대로 재현») ·
  build_plan.modules[w_cmp] · slate.eg_exclusion(«EG30 은 결과 표의 비교선으로만 · 보고»).
  산수는 build/v_cmp.py(V 등록 커밋 ada1e16ae · blob 핀은 w_audit 가 대조)의 G-EGD 함수를 **복사**했다 — v_cmp 는 W 금지 목록이라 부르지 않는다.

경계(G-NoEG): 이 모듈만 EG 계보(eg30plus · qg_lab — 그 안에서 _eg_q5_scores* 를 읽는다)를 부른다(함수 안에서만). 이 모듈은 어떤 w_ · v_ 모듈도
  부르지 않는다(w_guard 가 전이적으로 본다 · 등록 확인 · 달 산수도 여기서 따로 짠다). W 쪽 책 · 신호는 W 과정이 캐시에 쓴 파일
  (cmp/wb_books.json.gz · V 의 vb_books 와 같은 모양 {cards, months{달: {wB, books{sid}, signals{sid}, keys}}})로만 건너온다.

G-EGD(달마다 · 명세 V 정의 그대로 · 문턱 0.30 · 0.10 · 0.30): (1) 능동 비중 상관 corr(w_f − w_B, w_EG − w_B) 달별 중앙값 ≤ 0.30(EG30 · QG30 각각)
  (2) 겹침 초과 Σmin(w_f, w_EG) − Σmin(w_B, w_EG) 달별 중앙값 ≤ 0.10 (3) |Spearman(신호, Eg)| 달별 중앙값 ≤ 0.30 — 하나라도 넘거나 값이 없으면 «EG30-근접».
  산수 선언 C1 ~ C3 는 v_cmp 그대로(형성 달 목표 유지 · 키 → 티커 · 이름 ≥ 10).

V 재현(--repro-v): V F0 입력(%TEMP%/vbatch_cache/f0/vb_books.json.gz · 읽기 전용)으로 G-EGD 를 다시 풀어 V 표(f0/gegd.json)의 카드 여덟 칸 전부와
  EG 쪽 입력 핀(eg_inputs)을 대조한다 — 산출은 W 캐시(audit/gegd_repro_v.json)에만. 값은 이미 공개된 V F0 표의 재현이다(새 시행 아님).
🚨 EG30 비교선(수익)은 W 등록 커밋 뒤에만 — WBATCH_COMMIT 가 origin/main 조상이고 그 트리에 build/PREREG-*-WBATCH.md 가 있어야 한다.

  python build/w_cmp.py --selftest
  python build/w_cmp.py --repro-v [--out <W 캐시 파일>]               V G-EGD 표 재현(짝맞춤 감사 · w_audit 가 부른다)
  python build/w_cmp.py --gegd --in <W 책 파일> [--out <W 캐시 파일>]  W 카드 G-EGD(F0 · 비중만)
  WBATCH_COMMIT=<등록 커밋> python build/w_cmp.py --compare --out <W 캐시 파일>   EG30 비교선(굽기 뒤 · 요약 한 줄)
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
CACHE = os.environ.get("WBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "wbatch_cache")
VB_CACHE = os.environ.get("VBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "vbatch_cache")
V_IN = os.path.join(VB_CACHE, "f0", "vb_books.json.gz")          # V F0 입력(읽기 전용)
V_GEGD = os.path.join(VB_CACHE, "f0", "gegd.json")               # V G-EGD 표(읽기 전용)
V_IN_SHA = "c1aeff7df4d02c03742f224623f109e89bb6873ea8e18eaf6ff6f53862784c1b"   # V 표의 in_sha(재현 전 대조)
IN_FILE = os.path.join(CACHE, "cmp", "wb_books.json.gz")
OUT_FILE = os.path.join(CACHE, "cmp", "wb_gegd.json")
MAX_ACTIVE_CORR, MAX_OVERLAP_EXCESS, MAX_SPEARMAN = 0.30, 0.10, 0.30
REF_QG = {"signals": ["roe", "eg"], "weights": {"roe": 1, "eg": 1}, "smooth": 6, "n": 30, "wt": "cap", "cap": 0.20, "reb": 3, "index": "spx",
          "ex_fin": True, "mode": "base"}                                    # = v_cmp.REF_QG(= eg_best.REF["REF_QG"]) — QG30 비교 책
REPRO_TOL = 1e-12
CMP_WIN = ("2016-09", "2026-08")

_OPENED = []


def _install_input_audit():
    if getattr(_install_input_audit, "_on", False):
        return
    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            try:
                _OPENED.append(os.fsdecode(args[0]))
            except Exception:                                               # noqa: BLE001
                pass
    sys.addaudithook(hook)
    _install_input_audit._on = True


def input_pins():
    """열린 저장소 파일의 LF sha256 앞 16자(v_cmp.input_pins 와 같은 규칙 — 경로는 normcase · data/<폴더>/ 아래는 폴더 digest) · EG 코드 sha."""
    root = os.path.normcase(os.path.abspath(ROOT)) + os.sep
    files, dirs = {}, {}
    for p in sorted(set(_OPENED)):
        a = os.path.normcase(os.path.abspath(p))
        if not a.startswith(root) or not os.path.isfile(p):
            continue
        rel = os.path.relpath(a, os.path.normcase(os.path.abspath(ROOT))).replace(os.sep, "/")
        if rel.startswith(".git/") or "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        with open(p, "rb") as f:
            sh = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()[:16]
        parts = rel.split("/")
        if parts[0] == "data" and len(parts) > 2:
            dirs.setdefault("/".join(parts[:2]) + "/", {})[rel] = sh
        else:
            files[rel] = sh
    for mod in ("eg30plus", "qg_lab"):
        m = sys.modules.get(mod)
        fp = getattr(m, "__file__", None) if m else None
        if fp and os.path.isfile(fp) and fp.endswith(".py"):
            with open(fp, "rb") as f:
                files["build/%s.py" % mod] = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()[:16]
    for d, fs in sorted(dirs.items()):
        lines = "".join("%s\t%s\n" % (k, v) for k, v in sorted(fs.items()))
        files[d] = "%s · 파일 %d" % (hashlib.sha256(lines.encode("utf-8")).hexdigest()[:16], len(fs))
    return files


def _inside(p, root):
    a, r = os.path.normcase(os.path.abspath(p)), os.path.normcase(os.path.abspath(root))
    return a == r or a.startswith(r + os.sep)


def out_guard(p):
    """산출은 W 캐시에만 — 저장소 · V 캐시(읽기 전용) 안이면 멈춘다."""
    if _inside(CACHE, ROOT) or not _inside(p, CACHE) or _inside(p, VB_CACHE):
        raise SystemExit("🚨 w_cmp 산출은 저장소 밖 W 캐시에만: %s" % p)
    return p


def read_json(p):
    if p.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(p, doc):
    out_guard(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


# ══════════════════════════════════════════════════════════════════════════
#  G-EGD 산수(복사: v_cmp · 순수 함수)
# ══════════════════════════════════════════════════════════════════════════
def _avg_rank(x):
    x = np.asarray(x, float)
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=float)
    u, inv = np.unique(x, return_inverse=True)
    for j in range(len(u)):
        m = inv == j
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r


def spearman(a, b, min_n=10):
    ks = [k for k in a if k in b and a[k] is not None and b[k] is not None and np.isfinite(a[k]) and np.isfinite(b[k])]
    if len(ks) < min_n:
        return None
    x = _avg_rank([a[k] for k in ks])
    y = _avg_rank([b[k] for k in ks])
    if x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def active_corr(wf, wB, wE):
    ks = sorted(set(wf) | set(wB) | set(wE))
    a = np.array([wf.get(k, 0.0) - wB.get(k, 0.0) for k in ks])
    e = np.array([wE.get(k, 0.0) - wB.get(k, 0.0) for k in ks])
    if a.std() == 0 or e.std() == 0:
        return None
    return float(np.corrcoef(a, e)[0, 1])


def overlap_excess(wf, wB, wE):
    ks = set(wE)
    return float(sum(min(wf.get(k, 0.0), wE[k]) for k in ks) - sum(min(wB.get(k, 0.0), wE[k]) for k in ks))


def eg_exposure(w, wB, eg):
    ks = [k for k in eg if eg[k] is not None and np.isfinite(eg[k])]
    if len(ks) < 10:
        return None
    r = _avg_rank([eg[k] for k in ks]) / (len(ks) - 1)
    pc = dict(zip(ks, r))

    def avg(x):
        num = sum(v * pc[k] for k, v in x.items() if k in pc)
        den = sum(v for k, v in x.items() if k in pc)
        return num / den if den > 0 else None
    a, b = avg(w), avg(wB)
    return None if a is None or b is None else a - b


def gegd_one(months_doc, eg_books, qg_books, eg_scores, sid):
    rows = []
    for m in sorted(months_doc):
        d = months_doc[m]
        wf = (d.get("books") or {}).get(sid)
        if not wf:
            continue
        wB = d["wB"]
        r = {"m": m}
        for tag, books in (("EG30", eg_books), ("QG30", qg_books)):
            wE = books.get(m)
            if wE:
                r["corr_" + tag] = active_corr(wf, wB, wE)
                r["ovx_" + tag] = overlap_excess(wf, wB, wE)
        sc = eg_scores.get(m)
        sig = (d.get("signals") or {}).get(sid)
        if sc and sig:
            r["spear"] = spearman(sig, sc)
            r["spear_abs"] = abs(r["spear"]) if r["spear"] is not None else None
            r["eg_expo"] = eg_exposure(wf, wB, sc)
        rows.append(r)
    med = lambda k: (float(np.median([r[k] for r in rows if r.get(k) is not None])) if any(r.get(k) is not None for r in rows) else None)
    s = {"n_months": len(rows), "corr_EG30": med("corr_EG30"), "corr_QG30": med("corr_QG30"), "ovx_EG30": med("ovx_EG30"),
         "ovx_QG30": med("ovx_QG30"), "spear": med("spear"), "spear_abs": med("spear_abs"), "eg_expo": med("eg_expo")}
    ok = True
    for k in ("corr_EG30", "corr_QG30"):
        ok &= s[k] is not None and s[k] <= MAX_ACTIVE_CORR
    for k in ("ovx_EG30", "ovx_QG30"):
        ok &= s[k] is not None and s[k] <= MAX_OVERLAP_EXCESS
    ok &= s["spear_abs"] is not None and s["spear_abs"] <= MAX_SPEARMAN
    s["pass"] = bool(ok)
    s["label"] = None if ok else "EG30-근접"
    return s


def hold_between(form, months):
    ks = sorted(form)
    out = {}
    j = -1
    for m in sorted(months):
        while j + 1 < len(ks) and ks[j + 1] <= m:
            j += 1
        if j >= 0:
            out[m] = form[ks[j]]
    return out


# ══════════════════════════════════════════════════════════════════════════
#  EG 쪽 실자료(허용 목록 — 이 모듈 안 · 함수 안에서만)
# ══════════════════════════════════════════════════════════════════════════
def eg_side(months, keys_by_month):
    """복사: v_cmp.eg_side — EG30(eg30plus.v0_targets · 합집합) · QG30(qg_lab.World.weights · REF_QG) 형성 달 목표 → C1 · Eg 점수(pitgics) → 티커(C2)."""
    import eg30plus as E                                                    # 허용 목록(w_cmp 만)
    import qg_lab as QL
    Wd = E.World()
    v0 = E.v0_targets(Wd, "union")
    eg_form = {m: v["w"] for m, v in v0.items()}
    qg_form = {}
    for m in sorted(eg_form):
        w, _names = QL.World.weights(Wd, dict(REF_QG), m)
        qg_form[m] = w
    scores = Wd.eg_scores("pitgics")

    def to_t(book, m):
        inv = {k: t for t, k in (keys_by_month.get(m) or {}).items()}
        return {inv.get(k, "k:" + k): float(v) for k, v in book.items()}
    egm = hold_between(eg_form, months)
    qgm = hold_between(qg_form, months)
    sc_m = hold_between(scores, months)
    return ({m: to_t(b, m) for m, b in egm.items()}, {m: to_t(b, m) for m, b in qgm.items()},
            {m: {t: sc_m[m].get(t, sc_m[m].get(k)) for t, k in (keys_by_month.get(m) or {}).items()
                 if (sc_m[m].get(t) is not None or sc_m[m].get(k) is not None)} for m in sc_m})


def run_gegd(in_path, out_path):
    """G-EGD 실행(F0 · 비중만) — 결과를 W 캐시에 쓴다. 돌려주는 것 {카드: 요약}."""
    out_guard(out_path)
    doc = read_json(in_path)
    months = doc["months"]
    keys = {m: d.get("keys") or {} for m, d in months.items()}
    _install_input_audit()
    egb, qgb, egs = eg_side(sorted(months), keys)
    res = {sid: gegd_one(months, egb, qgb, egs, sid) for sid in doc.get("cards") or []}
    write_json(out_path, {"rule": "명세 slate.common_frame.G_EGD(V 정의 그대로) · 중앙값 문턱 0.30 · 0.10 · 0.30", "cards": res,
                          "in_sha": _sha(in_path), "eg_inputs": input_pins(),
                          "note": "eg_inputs = 이 과정이 연 저장소 파일(EG30 · QG30 책 · 규칙 카드 · Eg 점수 · EG 코드)의 LF sha 앞 16자"})
    return res


def _cmp_cards(a, b, tol=REPRO_TOL):
    """두 G-EGD 카드 표의 칸마다 대조 — (같다, 최대 절대 차, 다른 칸)."""
    worst, diff = 0.0, []
    if set(a) != set(b):
        return False, None, ["카드 집합 %s ≠ %s" % (sorted(a), sorted(b))]
    for sid in sorted(a):
        for k in sorted(set(a[sid]) | set(b[sid])):
            x, y = a[sid].get(k), b[sid].get(k)
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
                d = abs(float(x) - float(y))
                worst = max(worst, d)
                if d > tol:
                    diff.append("%s.%s %.3e" % (sid, k, d))
            elif x != y:
                diff.append("%s.%s %r ≠ %r" % (sid, k, x, y))
    return not diff, worst, diff


def repro_v(out_path=None):
    """V G-EGD 표 재현 — V F0 입력(in_sha 대조) → G-EGD → V 표 카드 · EG 입력 핀 대조. 돌려주는 것 요약(참/거짓 · 최대 차 · 수)."""
    out_path = out_path or os.path.join(CACHE, "audit", "gegd_repro_v.json")
    if _sha(V_IN) != V_IN_SHA:
        raise SystemExit("🚨 V F0 입력 sha 가 V 표의 in_sha 와 다르다")
    ref = read_json(V_GEGD)
    if ref.get("in_sha") != V_IN_SHA:
        raise SystemExit("🚨 V G-EGD 표의 in_sha 가 다르다")
    res = run_gegd(V_IN, out_path)
    got = read_json(out_path)
    same, worst, diff = _cmp_cards(res, ref["cards"])
    gi, ri = got["eg_inputs"], ref["eg_inputs"]
    pin_diff = sorted(k for k in ri if gi.get(k) != ri[k])                  # V 가 적은 입력 핀은 모두 같아야 한다
    extra = sorted(k for k in gi if k not in ri)
    # V 표에 없는 칸은 이 과정이 .pyc 없이 모듈 원본(.py)을 읽어 생긴 코드 파일뿐이어야 한다(자료 · EG 파일이면 실패)
    bad_extra = [k for k in extra if not (k.startswith("build/") and k.endswith(".py"))]
    pins_same = not pin_diff and not bad_extra
    return {"ok": bool(same and pins_same), "cards_same": same, "max_abs_diff": worst, "n_cards": len(res), "diff": diff[:10],
            "eg_inputs_same": pins_same, "eg_inputs_diff": pin_diff[:10], "n_eg_inputs": len(ri), "import_reads": extra,
            "bad_extra": bad_extra, "tol": REPRO_TOL, "labels": {k: v.get("label") for k, v in sorted(res.items())}, "out": out_path}


# ══════════════════════════════════════════════════════════════════════════
#  EG30 비교선(굽기 뒤 · 보고만)
# ══════════════════════════════════════════════════════════════════════════
def w_registered(env=None):
    """WBATCH_COMMIT = W 등록 커밋(40자 · origin/main 조상 · 트리에 build/PREREG-*-WBATCH.md) — 아니면 None(w_core 를 부르지 않고 따로 짠다)."""
    c = (env or os.environ).get("WBATCH_COMMIT")
    if not c or not re.fullmatch(r"[0-9a-f]{40}", c):
        return None
    if subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", c, "origin/main"], capture_output=True).returncode != 0:
        return None
    p = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", c, "build/"], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0 or not any(re.fullmatch(r"build/PREREG-\d{4}-\d{2}-\d{2}-WBATCH\.md", x) for x in p.stdout.splitlines()):
        return None
    return c


def compare_line():
    """EG30 비교선(수익) — W 등록 커밋 뒤에만(복사: v_cmp.compare_line 의 계산)."""
    if w_registered() is None:
        raise SystemExit("🚨 EG30 비교선은 W 등록 커밋 뒤에만(WBATCH_COMMIT 없음 · origin 조상 아님 · 등록 문서 없음)")
    _install_input_audit()
    import eg30plus as E
    Wd = E.World()
    return E.quick(Wd, E.v0_targets(Wd, "union"))


def cmp_summary(hold, ex_pct, win=CMP_WIN):
    """복사: v_cmp.cmp_summary — S 창 요약 한 줄(월 계열은 W 과정으로 건너가지 않는다)."""
    xs = [(str(h), x / 100.0) for h, x in zip(hold, ex_pct) if x is not None and x == x and win[0] <= str(h)[:7] <= win[1]]
    if len(xs) < 12:
        return {"n": len(xs), "role": "EG30 비교선(보고만)"}
    x = [v for _, v in xs]
    n = len(x)
    mu = sum(x) / n
    e = [v - mu for v in x]
    sv = sum(v * v for v in e) / n
    for L in range(1, min(6, n - 1) + 1):
        sv += 2.0 * (1.0 - L / 7.0) * sum(e[i] * e[i - L] for i in range(L, n)) / n
    t = mu / math.sqrt(sv / n) if sv > 0 else None
    return {"n": n, "mean": mu, "ann": mu * 12, "t": t, "first": xs[0][0][:7], "last": xs[-1][0][:7],
            "role": "EG30 비교선(보고만 · 어떤 관문 · 귀무 · 대조에도 없다)"}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 · 경계)
# ══════════════════════════════════════════════════════════════════════════
def _st_math():
    wB = {"a": 0.4, "b": 0.3, "c": 0.2, "d": 0.1}
    wE = {"a": 0.5, "b": 0.5}
    same = dict(wE)
    assert abs(active_corr(same, wB, wE) - 1.0) < 1e-12 and abs(overlap_excess(same, wB, wE) - (1.0 - 0.7)) < 1e-12
    anti = {"c": 0.6, "d": 0.4}
    assert active_corr(anti, wB, wE) < 0 and abs(overlap_excess(anti, wB, wE) - (0.0 - 0.7)) < 1e-12
    assert active_corr(wB, wB, wE) is None
    rng = np.random.default_rng(1)
    a = {str(i): float(v) for i, v in enumerate(rng.normal(0, 1, 50))}
    b = {k: 2 * v + 1 for k, v in a.items()}
    assert abs(spearman(a, b) - 1.0) < 1e-12 and abs(spearman(a, {k: -v for k, v in a.items()}) + 1.0) < 1e-12
    assert spearman({"x": 1.0}, {"x": 2.0}) is None
    form = {"2016-09": {"a": 1.0}, "2016-12": {"b": 1.0}}
    hb = hold_between(form, ["2016-08", "2016-09", "2016-11", "2016-12", "2017-02"])
    assert "2016-08" not in hb and hb["2016-11"] == {"a": 1.0} and hb["2017-02"] == {"b": 1.0}
    months = {"2016-09": {"wB": wB, "books": {"W01": same, "W04": anti}, "signals": {"W01": a, "W04": a}},
              "2016-10": {"wB": wB, "books": {"W01": same, "W04": anti}, "signals": {"W01": a, "W04": a}}}
    egs = {m: {k: -v for k, v in a.items()} for m in months}
    r1 = gegd_one(months, {m: wE for m in months}, {m: wE for m in months}, egs, "W01")
    assert not r1["pass"] and r1["label"] == "EG30-근접"
    egs0 = {m: {k: float(rng.normal()) for k in a} for m in months}
    r2 = gegd_one(months, {m: wE for m in months}, {m: wE for m in months}, egs0, "W04")
    assert r2["corr_EG30"] < 0.3 and r2["ovx_EG30"] <= 0.1
    r3 = gegd_one({"2016-09": {"wB": wB, "books": {"W10m": same}}}, {}, {}, {}, "W10m")      # 값이 없으면 fail-closed
    assert not r3["pass"] and r3["label"] == "EG30-근접"
    ok, worst, diff = _cmp_cards({"V01": {"x": 1.0, "label": None}}, {"V01": {"x": 1.0 + 1e-13, "label": None}})
    assert ok and worst < 1e-12
    ok2, _, diff2 = _cmp_cards({"V01": {"x": 1.0}}, {"V01": {"x": 1.1}})
    assert not ok2 and diff2
    return "G-EGD 산수(v_cmp 복사) · 같은 책 «EG30-근접» · 값 없음 fail-closed · 표 대조(1e−12)"


def _st_boundary():
    import ast
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    top, inner = set(), set()
    for nd in tree.body:
        if isinstance(nd, (ast.Import, ast.ImportFrom)):
            for a in getattr(nd, "names", []):
                top.add((nd.module if isinstance(nd, ast.ImportFrom) else a.name) or "")
    for nd in ast.walk(tree):
        if isinstance(nd, ast.Import):
            inner.update(a.name for a in nd.names)
        elif isinstance(nd, ast.ImportFrom) and nd.module:
            inner.add(nd.module)
    assert not any(n.split(".")[0].startswith(("v_", "w_")) for n in inner), inner
    assert not any(n.split(".")[0] in ("eg30plus", "qg_lab") for n in top)
    assert {"eg30plus", "qg_lab"} <= inner
    for p in (V_GEGD, os.path.join(ROOT, "x.json")):
        try:
            out_guard(p)
            raise AssertionError("캐시 밖 산출 허용")
        except SystemExit:
            pass
    assert out_guard(os.path.join(CACHE, "audit", "x.json"))
    return "경계: v_ · w_ 모듈 import 없음(함수 안 포함) · EG 모듈은 함수 안에서만 · 산출은 W 캐시에만(V 캐시 · 저장소 거부)"


def _st_guard_compare():
    old = os.environ.pop("WBATCH_COMMIT", None)
    try:
        for bad in (None, "0" * 40, "ada1e16ae9772a95246198407acb2f1e51a1906f"):
            if bad is not None:
                os.environ["WBATCH_COMMIT"] = bad
            try:
                compare_line()
                raise AssertionError("등록 전 비교선이 돌았다")
            except SystemExit:
                pass
    finally:
        os.environ.pop("WBATCH_COMMIT", None)
        if old is not None:
            os.environ["WBATCH_COMMIT"] = old
    hold = ["2016-%02d" % i for i in range(1, 13)] + ["2017-%02d" % i for i in range(1, 13)]
    ex = [0.1 * ((-1) ** i) + 0.05 for i in range(24)]
    ex[20] = None
    sm = cmp_summary(hold, ex)
    assert sm["n"] == 15 and sm["first"] == "2016-09"
    return "EG30 비교선은 W 등록 커밋 없이 · 없는 커밋 · 등록 문서 없는 조상(V 등록 커밋)이면 멈춘다 · 요약 한 줄"


def selftest():
    res, ok = [], True
    for fn in (_st_math, _st_boundary, _st_guard_compare):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                   # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-18s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_cmp selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--repro-v" in sys.argv:
        op = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
        r = repro_v(op)
        print("W_CMP_REPRO " + json.dumps(r, ensure_ascii=False))
        raise SystemExit(0 if r["ok"] else 1)
    if "--gegd" in sys.argv:
        ip = sys.argv[sys.argv.index("--in") + 1] if "--in" in sys.argv else IN_FILE
        op = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else OUT_FILE
        res = run_gegd(ip, op)
        print("G-EGD → %s (카드 %d · 라벨 %s)" % (op, len(res), {k: v["label"] for k, v in res.items()}))
        raise SystemExit(0)
    if "--compare" in sys.argv:
        op = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(CACHE, "out", "_wbatch_cmp.json")
        q = compare_line()
        ex = [float(v) for v in np.asarray(q["ex"], float).ravel()]
        sm = cmp_summary([str(h) for h in q["hold"]], ex)
        write_json(op, {"what": "EG30(V0 · union) 비교선 — eg30plus.quick · S 창 요약 한 줄 · 보고만", "summary": sm,
                        "registered": os.environ.get("WBATCH_COMMIT"), "eg_inputs": input_pins()})
        print("EG30 비교선 → %s" % op)
        raise SystemExit(0)
    print(__doc__)
