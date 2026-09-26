# -*- coding: utf-8 -*-
"""build/v_cmp.py — 배치 V 비교 모듈(허용 목록 유일 · 별도 프로세스): G-EGD 정의 관문(EG30 · QG30 대 V 카드 θ = 1 책) · EG30 비교 줄(굽기 뒤만).

설계 원본(구속): vbatch_research.json final.registration.G_EGD(what · tests · report · fail · why_not_control) · final.slate.eg_exclusion ·
  final.build_plan.modules[v_cmp](«허용 목록 유일: EG30 · QG30 비교 줄 · G-EGD · 어떤 v_ 모듈도 import 하지 않고 v_ 모듈도 이것을 import 하지 않는다 · 별도 프로세스») ·
  final.tests.fund_frame(«EG30 은 표의 비교 줄로만(v_cmp) — 어떤 Δ · 관문 · 귀무에도 들지 않는다»).

경계(G-NoEG): 이 모듈만 EG 계보(eg30plus · qg_lab — 그 안에서 _eg_q5_scores* 를 읽는다)를 부른다. v_ 모듈은 이 모듈을 부르지 않고(v_guard 가 전이적으로 본다),
  이 모듈도 v_ 모듈을 부르지 않는다 — V 쪽 책 · 신호는 V 프로세스가 캐시에 쓴 파일(cmp/vb_books.json.gz · v_cards.export_for_cmp)로만 건너온다.

G-EGD(정의 관문 · 수익 없음 · F0): θ = 1 책(전략 책 그대로)을 EG30 · QG30 두 책에 대해 잰다. 달마다
  (1) 능동 비중 상관 corr(w_f − w_B, w_EG − w_B)(두 책 이름의 합집합 · 피어슨) — 달별 중앙값 ≤ 0.30(EG30 · QG30 각각)
  (2) 비중 겹침 초과 Σmin(w_f, w_EG) − Σmin(w_B, w_EG) — 달별 중앙값 ≤ 0.10
  (3) |Spearman(전략 신호, Eg 점수)| 의 달별 중앙값 ≤ 0.30(Eg 점수는 이 모듈만 읽는다)
  하나라도 넘으면 «EG30-근접» 라벨 → 배분기 슬레이트와 채택에서 빠지고 측정만.
  보고: 책 가중 Eg 백분위 노출(책 − w_B) · 겹침 표. 🔎 Eg 축 특성(log q · Cop · dRoe · I/A) 넷의 노출은 eg_q5 가 특성을 함수로 내보내지 않아
  (main 안의 닫힌 계산) 이번 판에서 짓지 않았다 — 공개(등록 전 eg_q5 에 내보내기 함수를 더하거나 보고에서 뺀다).

명세가 정하지 않은 산수(선언)
  C1 EG30 · QG30 은 형성 달(분기) 목표 비중 — 그 사이 달은 가장 최근 형성 달의 목표를 쓴다(흘러감 없음 · 정의 관문이라 비중 모양만).
  C2 가격 키 → V 명단 티커는 V 쪽 파일의 그달 keys 표로 잇는다 · 잇지 못한 EG 이름은 «k:키» 로 따로 둔다(w_f = w_B = 0).
  C3 Spearman = 두 값이 선 이름끼리 평균 순위 상관 · 이름 < 10 인 달은 뺀다.

🚨 EG30 비교 줄(수익)은 등록 커밋 뒤 굽기에서만 — compare_line 은 VBATCH_REGISTERED(등록 커밋 · 그 트리에 build/PREREG-*-VBATCH.md · origin/main 의 조상)가
   없으면 멈춘다. 🔧 검토 고침(등록 전): 비교 줄 파일에는 S 창 요약 한 줄(cmp_summary)만 싣고 월 계열은 싣지 않는다(EG30 파생 자료가 V 과정으로 건너가지 않는다) ·
   G-EGD 결과와 비교 줄 파일에 이 과정이 연 EG 쪽 입력(EG30 · QG30 책 · data/_fund_card.json · Eg 점수 · EG 코드)의 sha 핀(eg_inputs)을 싣는다(재현).

  python build/v_cmp.py --selftest
  python build/v_cmp.py --gegd [--in <cmp 파일>] [--out <결과 파일>]     G-EGD(F0 · 비중만) — 결과는 저장소 밖 캐시에
  python build/v_cmp.py --blind-smoke                                   G-EGD 를 실자료로 끝까지 · 산출을 열지 않고 지운다(참/거짓 · 모양만)
  VBATCH_REGISTERED=<등록 커밋> python build/v_cmp.py --compare --out <캐시 파일>   EG30 비교 줄(수익 · 굽기 뒤 v_run 만 · 등록 커밋 없이는 멈춘다)
"""
from __future__ import annotations

import gzip
import io
import json
import math
import os
import shutil
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
CACHE = os.environ.get("VBATCH_CACHE") or os.path.join(tempfile.gettempdir(), "vbatch_cache")
IN_FILE = os.path.join(CACHE, "cmp", "vb_books.json.gz")
OUT_FILE = os.path.join(CACHE, "cmp", "vb_gegd.json")
MAX_ACTIVE_CORR, MAX_OVERLAP_EXCESS, MAX_SPEARMAN = 0.30, 0.10, 0.30
EG_BASE_UNION = {"signals": ["eg"], "weights": {"eg": 1}, "smooth": 1, "n": 30, "wt": "cap", "cap": 0.20, "reb": 3, "index": "union",
                 "ex_fin": False, "eg": "pitgics", "mode": "base"}            # = eg30plus.EG_BASE(index union) — 비교용 사본(판정은 원 모듈이 낸 목표)
REF_QG = {"signals": ["roe", "eg"], "weights": {"roe": 1, "eg": 1}, "smooth": 6, "n": 30, "wt": "cap", "cap": 0.20, "reb": 3, "index": "spx",
          "ex_fin": True, "mode": "base"}                                    # = eg_best.REF["REF_QG"](우량성장선별 30 · data/_fund_card.json 규칙)


_OPENED = []


def _install_input_audit():
    """EG 쪽 입력 기록(검토 고침) — 이 과정이 연 저장소 파일을 모은다(G-EGD · 비교 줄의 EG30 · QG30 책 · QG30 규칙 카드 · Eg 점수 파일 핀)."""
    if getattr(_install_input_audit, "_on", False):
        return
    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            _OPENED.append(os.fsdecode(args[0]))
    sys.addaudithook(hook)
    _install_input_audit._on = True


def input_pins():
    """열린 저장소 파일의 LF sha256 앞 16자 — build/*.py · data/*(맨 윗단)는 파일마다, data/<폴더>/ 아래 파일은 폴더마다 한 digest(이름 · sha 줄의 sha · 파일 수) ·
    __pycache__ · .git 은 뺀다. 값은 싣지 않는다(해시 · 이름 · 개수만)."""
    import hashlib
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
    for mod in ("eg30plus", "qg_lab"):                                          # EG 쪽 코드(모듈로 불러 open 감사에 .py 가 안 잡힌다) — 소스 파일 sha 를 따로
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


def cache_guard():
    if _inside(CACHE, ROOT):
        raise SystemExit("🚨 캐시가 저장소 안이다(D1)")
    return os.path.abspath(CACHE)


def read_json(p):
    if p.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(p, doc):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


# ══════════════════════════════════════════════════════════════════════════
#  G-EGD 산수(순수 함수 · 합성 시험 대상)
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
    """C3 — 두 dict(이름 → 값)의 선 이름끼리 평균 순위 상관 · 이름 < min_n 이면 None."""
    ks = [k for k in a if k in b and a[k] is not None and b[k] is not None and np.isfinite(a[k]) and np.isfinite(b[k])]
    if len(ks) < min_n:
        return None
    x = _avg_rank([a[k] for k in ks])
    y = _avg_rank([b[k] for k in ks])
    if x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def active_corr(wf, wB, wE):
    """(1) corr(w_f − w_B, w_EG − w_B) — 세 책 이름의 합집합 위 피어슨(하나라도 분산 0 이면 None)."""
    ks = sorted(set(wf) | set(wB) | set(wE))
    a = np.array([wf.get(k, 0.0) - wB.get(k, 0.0) for k in ks])
    e = np.array([wE.get(k, 0.0) - wB.get(k, 0.0) for k in ks])
    if a.std() == 0 or e.std() == 0:
        return None
    return float(np.corrcoef(a, e)[0, 1])


def overlap_excess(wf, wB, wE):
    """(2) Σmin(w_f, w_EG) − Σmin(w_B, w_EG)."""
    ks = set(wE)
    return float(sum(min(wf.get(k, 0.0), wE[k]) for k in ks) - sum(min(wB.get(k, 0.0), wE[k]) for k in ks))


def eg_exposure(w, wB, eg):
    """보고 — 책 가중 Eg 백분위 − w_B 가중 Eg 백분위(Eg 가 선 이름끼리 비례 맞춤)."""
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
    """전략 하나의 G-EGD — months_doc = V 쪽 파일 months · eg_books/qg_books = {달: {티커: 비중}} · eg_scores = {달: {티커: 점수}}."""
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
    ok &= s["spear_abs"] is not None and s["spear_abs"] <= MAX_SPEARMAN              # |Spearman| 의 달별 중앙값
    s["pass"] = bool(ok)
    s["label"] = None if ok else "EG30-근접"
    return s


def hold_between(form, months):
    """C1 — 형성 달 목표 {달: 책} → 달마다 가장 최근 형성 달의 목표."""
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
#  EG 쪽 실자료(허용 목록 — 이 모듈 안에서만 · 함수 안)
# ══════════════════════════════════════════════════════════════════════════
def eg_side(months, keys_by_month):
    """EG30(eg30plus.v0_targets · 합집합) · QG30(qg_lab.World.weights · REF_QG) 형성 달 목표 → 달마다 C1 · Eg 점수(pitgics) → V 티커로(C2)."""
    import eg30plus as E                                                    # 허용 목록(v_cmp 만)
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


def run_gegd(in_path=IN_FILE, out_path=OUT_FILE):
    """G-EGD 실행(F0 · 비중만) — 결과를 캐시에 쓴다. 돌려주는 것 {전략: 요약}."""
    cache_guard()
    doc = read_json(in_path)
    months = doc["months"]
    keys = {m: d.get("keys") or {} for m, d in months.items()}
    _install_input_audit()
    egb, qgb, egs = eg_side(sorted(months), keys)
    res = {sid: gegd_one(months, egb, qgb, egs, sid) for sid in doc.get("cards") or []}
    write_json(out_path, {"rule": "명세 registration.G_EGD · 중앙값 문턱 0.30 · 0.10 · 0.30", "cards": res, "in_sha": _sha(in_path),
                          "eg_inputs": input_pins(),
                          "note": "eg_inputs = 이 과정이 연 저장소 파일(EG30 · QG30 책 · 규칙 카드 · Eg 점수 · EG 코드)의 LF sha 앞 16자 — 재현 핀"})
    return res


def _sha(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def compare_line(*a, **k):
    """EG30 비교 줄(수익) — 등록 커밋 뒤 굽기에서만. VBATCH_REGISTERED 가 origin 조상이고 그 트리에 build/PREREG-*-VBATCH.md 가 있어야 한다."""
    c = os.environ.get("VBATCH_REGISTERED")
    if not c:
        raise SystemExit("🚨 EG30 비교 줄은 등록 커밋 뒤에만(VBATCH_REGISTERED 없음)")
    p = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", c, "build/"], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0 or not any(x.startswith("build/PREREG-") and x.endswith("-VBATCH.md") for x in p.stdout.splitlines()):
        raise SystemExit("🚨 VBATCH_REGISTERED 트리에 등록 문서가 없다")
    if subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", c, "origin/main"], capture_output=True).returncode != 0:
        raise SystemExit("🚨 VBATCH_REGISTERED 가 origin/main 의 조상이 아니다(검토 고침 — 등록 커밋이 올라간 뒤에만)")
    _install_input_audit()
    import eg30plus as E
    Wd = E.World()
    return E.quick(Wd, E.v0_targets(Wd, "union"))


CMP_WIN = ("2016-09", "2026-08")


def cmp_summary(hold, ex_pct, win=CMP_WIN):
    """EG30 비교 줄 요약(S 창 · 보고만) — 월 초과(%p → 소수) 평균 · 연 · NW(6) t · 첫 · 끝 달(표준 라이브러리 셈 · v_tests.nw_t 와 같은 식).
    🔧 검토 고침(등록 전): 요약은 이 과정이 셈하고 v_run 은 이 한 줄만 옮긴다 — EG30 파생 월 계열은 V 과정으로 건너가지 않는다."""
    xs = [(str(h), x / 100.0) for h, x in zip(hold, ex_pct) if x is not None and x == x and win[0] <= str(h)[:7] <= win[1]]
    if len(xs) < 12:
        return {"n": len(xs), "role": "EG30 비교 줄(보고만)"}
    x = [v for _, v in xs]
    n = len(x)
    mu = sum(x) / n
    e = [v - mu for v in x]
    sv = sum(v * v for v in e) / n
    for L in range(1, min(6, n - 1) + 1):
        sv += 2.0 * (1.0 - L / 7.0) * sum(e[i] * e[i - L] for i in range(L, n)) / n
    t = mu / math.sqrt(sv / n) if sv > 0 else None
    return {"n": n, "mean": mu, "ann": mu * 12, "t": t, "first": xs[0][0][:7], "last": xs[-1][0][:7], "role": "EG30 비교 줄(보고만 · 어떤 관문 · 귀무에도 없다)"}


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험 · 경계 점검 · 연기
# ══════════════════════════════════════════════════════════════════════════
def _st_math():
    wB = {"a": 0.4, "b": 0.3, "c": 0.2, "d": 0.1}
    wE = {"a": 0.5, "b": 0.5}
    same = dict(wE)
    assert abs(active_corr(same, wB, wE) - 1.0) < 1e-12 and abs(overlap_excess(same, wB, wE) - (1.0 - 0.7)) < 1e-12
    anti = {"c": 0.6, "d": 0.4}
    assert active_corr(anti, wB, wE) < 0 and abs(overlap_excess(anti, wB, wE) - (0.0 - 0.7)) < 1e-12
    assert active_corr(wB, wB, wE) is None                                      # 능동 0 → 정의 안 됨
    rng = np.random.default_rng(1)
    a = {str(i): float(v) for i, v in enumerate(rng.normal(0, 1, 50))}
    b = {k: 2 * v + 1 for k, v in a.items()}
    assert abs(spearman(a, b) - 1.0) < 1e-12 and abs(spearman(a, {k: -v for k, v in a.items()}) + 1.0) < 1e-12
    assert spearman({"x": 1.0}, {"x": 2.0}) is None
    form = {"2016-09": {"a": 1.0}, "2016-12": {"b": 1.0}}
    hb = hold_between(form, ["2016-08", "2016-09", "2016-11", "2016-12", "2017-02"])
    assert "2016-08" not in hb and hb["2016-11"] == {"a": 1.0} and hb["2017-02"] == {"b": 1.0}
    months = {"2016-09": {"wB": wB, "books": {"V01": same, "V02": anti}, "signals": {"V01": a, "V02": a}},
              "2016-10": {"wB": wB, "books": {"V01": same, "V02": anti}, "signals": {"V01": a, "V02": a}}}
    egs = {m: {k: -v for k, v in a.items()} for m in months}
    r1 = gegd_one(months, {m: wE for m in months}, {m: wE for m in months}, egs, "V01")
    assert not r1["pass"] and r1["label"] == "EG30-근접"
    egs0 = {m: {k: float(rng.normal()) for k in a} for m in months}
    r2 = gegd_one(months, {m: wE for m in months}, {m: wE for m in months}, egs0, "V02")
    assert r2["corr_EG30"] < 0.3 and r2["ovx_EG30"] <= 0.1
    return "G-EGD 산수: 능동 상관 · 겹침 초과 손 확인 · Spearman ±1 · 형성 달 사이 유지 · 같은 책 → «EG30-근접» · 반대 책 통과 조건"


def _st_boundary():
    """경계 — 이 모듈은 v_ 모듈을 부르지 않는다(AST · 함수 안 포함) · EG 모듈은 함수 안에서만."""
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
    assert not any(n.split(".")[0].startswith("v_") for n in inner), inner
    assert not any(n.split(".")[0] in ("eg30plus", "qg_lab") for n in top)
    assert {"eg30plus", "qg_lab"} <= inner
    return "경계: v_ 모듈 import 없음(함수 안 포함) · EG 모듈은 함수 안에서만(허용 목록)"


def _st_guard_compare():
    old = os.environ.pop("VBATCH_REGISTERED", None)
    try:
        try:
            compare_line()
            raise AssertionError("등록 전 비교 줄이 돌았다")
        except SystemExit:
            pass
        head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
        for bad in ("0" * 40, head):                                            # 없는 커밋 · 등록 문서가 트리에 없는 커밋(HEAD = 등록 전) → 멈춤
            os.environ["VBATCH_REGISTERED"] = bad
            try:
                compare_line()
                raise AssertionError("등록 안 된 커밋으로 비교 줄이 돌았다")
            except SystemExit:
                pass
    finally:
        os.environ.pop("VBATCH_REGISTERED", None)
        if old is not None:
            os.environ["VBATCH_REGISTERED"] = old
    # 요약(합성) — 표준 라이브러리 NW(6) 손 계산 · 창 밖 달 · 결측은 빠진다 · 12달 미만은 n 만
    hold = ["2016-%02d" % i for i in range(1, 13)] + ["2017-%02d" % i for i in range(1, 13)]
    ex = [0.1 * ((-1) ** i) + 0.05 for i in range(24)]
    ex[20] = None
    sm = cmp_summary(hold, ex)
    xs = [v / 100.0 for h, v in zip(hold, ex) if v is not None and h >= "2016-09"]
    mu = sum(xs) / len(xs)
    e = [v - mu for v in xs]
    sv = sum(v * v for v in e) / len(xs) + sum(2.0 * (1 - L / 7.0) * sum(e[i] * e[i - L] for i in range(L, len(xs))) / len(xs) for L in range(1, 7))
    assert sm["n"] == len(xs) == 15 and abs(sm["mean"] - mu) < 1e-15 and abs(sm["t"] - mu / math.sqrt(sv / len(xs))) < 1e-12 and sm["first"] == "2016-09"
    assert cmp_summary(hold[:10], ex[:10]) == {"n": 2, "role": "EG30 비교 줄(보고만)"}
    return ("EG30 비교 줄(수익)은 등록 커밋 없이 · 없는 커밋 · 등록 문서 없는 트리 · origin 조상 아님이면 멈춘다 · "
            "요약 한 줄(NW(6) 손 계산 · 창 · 결측)만 V 로 건너간다")


def selftest():
    res, ok = [], True
    for fn in (_st_math, _st_boundary, _st_guard_compare):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-18s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_cmp selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


def blind_smoke(in_path=IN_FILE):
    """G-EGD 실자료 연기 — 결과를 임시 파일에 쓰고 열지 않고 지운다. 찍는 것은 참/거짓 · 전략 수 · 경계 참/거짓."""
    import contextlib
    t0 = time.time()
    td = tempfile.mkdtemp(prefix="vb_cmp_smoke_", dir=cache_guard())
    out = os.path.join(td, "gegd.json")
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            res = run_gegd(in_path, out)
        r = {"ok": True, "sec": round(time.time() - t0, 1), "n_cards": len(res), "all_have_months": all(v["n_months"] > 100 for v in res.values()),
             "err": None}
    except Exception as e:
        r = {"ok": False, "sec": round(time.time() - t0, 1), "err": "%s: %s" % (type(e).__name__, str(e)[:160])}
    finally:
        shutil.rmtree(td, ignore_errors=True)
    r["no_v_modules_loaded"] = not any(m.split(".")[0].startswith("v_") for m in sys.modules)
    r["outputs_deleted"] = not os.path.exists(td)
    return r


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--gegd" in sys.argv:
        ip = sys.argv[sys.argv.index("--in") + 1] if "--in" in sys.argv else IN_FILE
        op = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else OUT_FILE
        res = run_gegd(ip, op)
        print("G-EGD → %s (전략 %d)" % (op, len(res)))
        raise SystemExit(0)
    if "--compare" in sys.argv:
        # EG30 비교 줄(수익 · 보고서 표의 비교 줄로만 — 어떤 Δ · 관문 · 귀무에도 들지 않는다) — 등록 커밋 뒤 v_run 굽기만 부른다(VBATCH_REGISTERED)
        op = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(CACHE, "out", "_vbatch_cmp.json")
        if not _inside(op, cache_guard()):
            raise SystemExit("🚨 비교 줄 산출은 저장소 밖 캐시에만(D1)")
        q = compare_line()
        ex = [float(v) for v in np.asarray(q["ex"], float).ravel()]
        sm = cmp_summary([str(h) for h in q["hold"]], ex)
        tv = q.get("turn")
        write_json(op, {"what": "EG30(V0 · 공개 판 · union) 비교 줄 — eg30plus.quick · S 창 요약 한 줄 · 보고만(월 계열은 싣지 않는다 — 검토 고침)",
                        "summary": sm, "turn": (float(tv) if tv is not None and np.ndim(tv) == 0 else None), "registered": os.environ.get("VBATCH_REGISTERED"),
                        "eg_inputs": input_pins()})
        print("EG30 비교 줄 → %s" % op)
        raise SystemExit(0)
    if "--blind-smoke" in sys.argv:
        ip = sys.argv[sys.argv.index("--in") + 1] if "--in" in sys.argv else IN_FILE
        r = blind_smoke(ip)
        if "--delete-in" in sys.argv and os.path.exists(ip) and _inside(ip, CACHE):
            os.remove(ip)                                                  # 넘김 파일도 열지 않고 지운다(연기 전용 사본)
            r["in_deleted"] = not os.path.exists(ip)
        print(json.dumps(r, ensure_ascii=False))
        raise SystemExit(0 if r["ok"] and r["no_v_modules_loaded"] else 1)
    print(__doc__)
