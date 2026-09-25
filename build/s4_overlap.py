# -*- coding: utf-8 -*-
"""build/s4_overlap.py — EGFF 1단계(사전등록 PREREG-2026-09-25-EGFF §4 · §5): 수익 없음 → data/_s4_overlap.json

무엇을 재나(편입마다 · P-V · P-FF · P-VS 각각 공개 판 LF 대비):
  (a) 시총가중 겹침 Σ_k min(w_LF,k , w_X,k)          — 목표 비중(가격 키 k) 그대로
  (b) 이름 겹침 |A ∩ B| (30 중)
  (c) Eg 점수 스피어만(편입 세계 전체 = 그달 V0 유니버스 중 두 판 모두 점수가 선 이름 · 평균 순위)
  척도(보고만): V0(LF) 자신의 편입 대 편입 시총가중 겹침 — **분기 간격 쌍 39개**(2016-09→12 ~ 2026-03→06)의 중앙값
    («정상 교체 한 분기» 의 크기 · 2016-08→09 는 한 달 간격이라 행에는 싣되 척도에서 뺀다 — 2026-09-26 겹침 전 선언).
편입 = V0 규칙 그대로(qg_lab.World.weights(EG_BASE) · Eg 상위 30 · 시총가중 · 20% 상한) · 2016-08 과 그 뒤 분기말 ~ 2026-06 = 41회.
  qg_lab.World 는 P1 뿌리(배치 Q 와 같은 판)의 얼린 코드로 짓는다 · Eg 판만 공급자별 점수 파일로 바꾼다(eg = "v" · "ff" · "vs").
결정(미리 고정 · 다른 문턱은 시험하지 않는다 · P-V 만 · P-FF · P-VS 는 보고만):
  (a) 중앙값 ≥ 0.90 · 10분위 ≥ 0.75 그리고 (b) 중앙값 ≥ 27 · 10분위 ≥ 24 → «재작성 둔감»(여기서 끝 · 수익 계산 없음) · 하나라도 어긋나면 «2단계».
  [선언] 중앙값 · 10분위 = numpy.percentile(선형 보간 · 기본값) · 41 편입 전부.
  [선언 2026-09-26 · 겹침 전] P-V = 형제 태그 메움 읽기(eg_q5_vintage.vintage_pick) · P-VS = 최신판 태그만(엄격) — 보고만.
🚨 돌기 전 관문(하나라도 어긋나면 돌지 않는다):
  ⓪ 저장소 = 이 스크립트의 랩 저장소(다른 저장소 불가 · --repo 없음) · 등록 커밋(REG_COMMIT)이 HEAD 의 조상 · 사전등록 문서가 HEAD 와 같다
  ① data/_s4_f0.json 이 있고 pass = true (F0 셋 모두 통과) · stage1_plan 이 이 스크립트의 결정 기준 · 쌍둥이와 같다
  ② 그 파일이 HEAD 에 커밋돼 있고(git ls-files) 작업 사본이 HEAD 와 같다(git diff --quiet HEAD --)
  ③ data/_eg_q5_scores_pitgics_v.json · _ff.json · _vs.json 이 F0 에 적힌 sha256 과 같고 모두 HEAD 에 커밋돼 있다(작업 사본 = HEAD)
  ④ 뿌리: 얼린 Eg 파일(_eg_q5_scores_pitgics.json) sha256 = F0 의 ref_sha256 = 배치 Q 의 값(BATCHQ_REF) 그리고
     뿌리 전체(build · data 의 모든 파일 · __pycache__ 제외)의 나무 해시 = F0 가 적은 root.tree_sha256 (다른 World 입력으로 열리지 않게)
  ⑤ data/_s4_overlap.json 이 아직 없다(한 번 굽기 — 있으면 어떤 사유로도 다시 돌지 않는다)
목표 이름 목록은 찍지도 쓰지도 않는다 — 편입마다 수치만.

  python build/s4_overlap.py --root <P1 뿌리>        # 관문 → 41 편입 → data/_s4_overlap.json
  python build/s4_overlap.py --selftest               # 합성 자료만(겹침 · 스피어만 · 분위 · 결정 · 척도 쌍 · 관문 — 임시 git 저장소)
"""
from __future__ import annotations
import datetime as dt, hashlib, io, json, math, os, shutil, subprocess, sys, tempfile, time

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PREREG = "build/PREREG-2026-09-25-EGFF.md"
REG_COMMIT = "98889aeb82bd35fb3c06e3e8ff731c12a1c670a0"             # 사전등록 커밋
BATCHQ_REF = "03ab2737f45a9fb4b670a8e3484c88a7fedb210625c4df246fdcc4437b1f41c8"   # 배치 Q 가 쓴 _eg_q5_scores_pitgics.json(P1 판)
F0_REL = "data/_s4_f0.json"
OUT_REL = "data/_s4_overlap.json"
SCORE_REL = {"v": "data/_eg_q5_scores_pitgics_v.json", "ff": "data/_eg_q5_scores_pitgics_ff.json",
             "vs": "data/_eg_q5_scores_pitgics_vs.json"}
BASIS, TWINS = "v", ("ff", "vs")                                     # 결정 기준 · 보고만 쌍둥이(F0 stage1_plan 과 같아야 한다)
FORM0, FORM1 = "2016-08", "2026-06"
TH = {"a_median": 0.90, "a_p10": 0.75, "b_median": 27, "b_p10": 24}
EG_BASE_REG = {"signals": ["eg"], "weights": {"eg": 1}, "smooth": 1, "n": 30, "wt": "cap", "cap": 0.20, "reb": 3,
               "index": "union", "ex_fin": False, "eg": "pitgics", "mode": "base"}   # PREREG-2026-09-24-EGBEST 의 EG_BASE(eg30plus.py)
TREE_DIRS = ("build", "data")


# ── 순수 함수(자체 점검 대상) ─────────────────────────────────────────────
def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def mgap(a, b):
    return (int(b[:4]) * 12 + int(b[5:7])) - (int(a[:4]) * 12 + int(a[5:7]))


def formations(f0=FORM0, f1=FORM1):
    """qg_lab.World.sleeve 의 편입 달(reb=3): 첫 달 + 분기말(3·6·9·12월)."""
    out, m = [], f0
    while m <= f1:
        if m == f0 or int(m[5:7]) % 3 == 0:
            out.append(m)
        m = mshift(m, 1)
    return out


def anchor_pairs(fs):
    """척도 쌍 — 앞뒤 편입 가운데 **분기(3개월) 간격**인 것만(2016-08→09 한 달 쌍은 뺀다)."""
    return [(a, b) for a, b in zip(fs, fs[1:]) if mgap(a, b) == 3]


def cap_overlap(wa, wb):
    return float(sum(min(wa.get(k, 0.0), wb.get(k, 0.0)) for k in set(wa) | set(wb)))


def name_overlap(wa, wb):
    return len(set(wa) & set(wb))


def avg_rank(x):
    x = np.asarray(x, float)
    order = x.argsort(kind="mergesort")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=float)
    u, inv = np.unique(x, return_inverse=True)
    for j in range(len(u)):
        m = inv == j
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r


def spearman(a, b):
    if len(a) < 3:
        return None
    ra, rb = avg_rank(a), avg_rank(b)
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def summary(vals):
    v = np.asarray(vals, float)
    return {"n": int(len(v)), "median": float(np.percentile(v, 50)), "p10": float(np.percentile(v, 10)),
            "min": float(v.min()), "max": float(v.max()), "mean": float(v.mean())}


def decide(a_vals, b_vals):
    """사전등록 §5 — P-V 의 (a)(b) 편입별 값 → (판정, 넷의 참거짓)."""
    sa, sb = summary(a_vals), summary(b_vals)
    chk = {"a_median": sa["median"] >= TH["a_median"], "a_p10": sa["p10"] >= TH["a_p10"],
           "b_median": sb["median"] >= TH["b_median"], "b_p10": sb["p10"] >= TH["b_p10"]}
    return ("재작성 둔감" if all(chk.values()) else "2단계"), chk


def _git(args, repo):
    return subprocess.run(["git", "-C", repo] + args, capture_output=True)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def tree_digest(root, dirs=TREE_DIRS):
    """뿌리의 build · data 아래 모든 파일(__pycache__ 제외)의 «상대경로 sha256» 줄(정렬)의 sha256 → (해시, 파일 수, 바이트).
    World 가 읽는 입력(stocks · sd · pit_px · pit_universe · index_* · pit_gics* · fx · fx_pit · splits …)과 얼린 코드를 빠짐없이 덮는다."""
    lines, nb = [], 0
    for top in dirs:
        base = os.path.join(root, top)
        for dp, dns, fns in os.walk(base):
            dns[:] = sorted(d for d in dns if d != "__pycache__")
            for fn in sorted(fns):
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                lines.append("%s %s" % (rel, sha_file(p)))
                nb += os.path.getsize(p)
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(), len(lines), nb


def committed_clean(repo, rel):
    """rel 이 HEAD 에 커밋돼 있고 작업 사본(스테이지 포함)이 HEAD 와 같은가."""
    if _git(["ls-files", "--error-unmatch", rel], repo).returncode != 0:
        return False, "HEAD 에 커밋되지 않았다(git ls-files)"
    if _git(["cat-file", "-e", "HEAD:%s" % rel], repo).returncode != 0:
        return False, "HEAD 트리에 없다"
    if _git(["diff", "--quiet", "HEAD", "--", rel], repo).returncode != 0:
        return False, "작업 사본이 HEAD 와 다르다"
    return True, "ok"


def repo_gate(repo, lab=REPO, reg=REG_COMMIT):
    """관문 ⓪ — 이 스크립트의 랩 저장소인가 · 등록 커밋이 HEAD 의 조상인가 · 사전등록 문서가 HEAD 와 같은가."""
    why = []
    try:
        same = os.path.samefile(repo, lab)
    except OSError:
        same = False
    if not same:
        why.append("⓪ 저장소 %s 는 이 스크립트의 랩 저장소(%s)가 아니다" % (repo, lab))
        return why
    if _git(["merge-base", "--is-ancestor", reg, "HEAD"], repo).returncode != 0:
        why.append("⓪ 등록 커밋 %s 가 HEAD 의 조상이 아니다" % reg[:9])
    ok, msg = committed_clean(repo, PREREG)
    if not ok:
        why.append("⓪ %s — %s" % (PREREG, msg))
    return why


def gate(repo, root, ref_pin=BATCHQ_REF):
    """관문 ①~⑤ → (통과 여부, 사유 목록, F0 문서)."""
    why = []
    f0p = os.path.join(repo, *F0_REL.split("/"))
    if not os.path.exists(f0p):
        return False, ["① %s 가 없다" % F0_REL], None
    f0 = json.load(io.open(f0p, encoding="utf-8"))
    if f0.get("pass") is not True:
        why.append("① F0 가 통과하지 않았다(pass = %r)" % f0.get("pass"))
    for key in ("f0_i_filing_match", "f0_ii_sh_split", "f0_iii_repro"):
        if not (f0.get(key) or {}).get("pass"):
            why.append("① F0 %s 불통과" % key)
    plan = f0.get("stage1_plan") or {}
    if plan.get("decision_basis") != BASIS or tuple(plan.get("report_only") or ()) != TWINS:
        why.append("① F0 stage1_plan(결정 %r · 보고만 %r)이 이 스크립트(%r · %r)와 다르다"
                   % (plan.get("decision_basis"), plan.get("report_only"), BASIS, TWINS))
    ok, msg = committed_clean(repo, F0_REL)
    if not ok:
        why.append("② %s — %s" % (F0_REL, msg))
    want = ((f0.get("f0_iii_repro") or {}).get("scores_sha256")) or {}
    for s, rel in SCORE_REL.items():
        p = os.path.join(repo, *rel.split("/"))
        if not os.path.exists(p):
            why.append("③ %s 가 없다" % rel)
            continue
        if sha_file(p) != want.get(s):
            why.append("③ %s sha256 이 F0 에 적힌 것과 다르다" % rel)
        ok, msg = committed_clean(repo, rel)
        if not ok:
            why.append("③ %s — %s" % (rel, msg))
    ref = (f0.get("f0_iii_repro") or {}).get("ref_sha256")
    if ref != ref_pin:
        why.append("④ F0 의 ref_sha256 이 배치 Q 의 얼린 파일 해시와 다르다")
    if root is not None:
        rp = os.path.join(root, "data", "_eg_q5_scores_pitgics.json")
        if not os.path.exists(rp) or sha_file(rp) != ref:
            why.append("④ 뿌리의 얼린 Eg 파일이 F0 의 ref_sha256 과 다르다")
        want_tree = ((f0.get("inputs") or {}).get("root") or {}).get("tree_sha256")
        if not want_tree:
            why.append("④ F0 에 뿌리 나무 해시(inputs.root.tree_sha256)가 없다")
        elif tree_digest(root)[0] != want_tree:
            why.append("④ 뿌리 나무 해시가 F0 에 적힌 것과 다르다(World 입력 · 얼린 코드가 F0 때의 P1 뿌리와 다르다)")
    if os.path.exists(os.path.join(repo, *OUT_REL.split("/"))) or _git(["cat-file", "-e", "HEAD:%s" % OUT_REL], repo).returncode == 0:
        why.append("⑤ %s 가 이미 있다(한 번 굽기)" % OUT_REL)
    return (not why), why, f0


# ── 본 계산 ──────────────────────────────────────────────────────────────
def run(root, repo=REPO):
    t0 = time.time()
    why0 = repo_gate(repo)
    ok, why, f0 = gate(repo, root)
    if why0 or not ok:
        raise SystemExit("🚨 1단계 관문 불통과 — 돌지 않는다:\n  " + "\n  ".join(why0 + why))
    sys.path.insert(0, os.path.join(root, "build"))
    import qg_lab as QL                    # noqa: E402  (P1 뿌리의 얼린 판)
    import eg30plus as E                   # noqa: E402  EG_BASE(사전등록 EGBEST)
    if E.EG_BASE != EG_BASE_REG:
        raise SystemExit("🚨 eg30plus.EG_BASE 가 등록된 V0 와 다르다")
    W = QL.World()
    for s, rel in SCORE_REL.items():
        W._EGV[s] = json.load(io.open(os.path.join(repo, *rel.split("/")), encoding="utf-8"))["months"]
    FS = formations()
    if len(FS) != 41:
        raise SystemExit("🚨 편입 %d회(41 이어야)" % len(FS))
    AP = set(anchor_pairs(FS))
    rows, prev = [], None
    for m in FS:
        w_lf, _n = QL.World.weights(W, dict(E.EG_BASE), m)
        row = {"f": m, "n_lf": len(w_lf)}
        univ = W.universe(m, E.EG_BASE["index"], E.EG_BASE["ex_fin"])
        s_lf = W.raw("eg", m, E.EG_BASE["index"], E.EG_BASE["ex_fin"], "pitgics")
        for s in (BASIS,) + TWINS:
            w_x, _nx = QL.World.weights(W, dict(E.EG_BASE, eg=s), m)
            s_x = W.raw("eg", m, E.EG_BASE["index"], E.EG_BASE["ex_fin"], s)
            both = [x for x in univ if x in s_lf and x in s_x]
            row.update({"a_" + s: cap_overlap(w_lf, w_x), "b_" + s: name_overlap(w_lf, w_x),
                        "c_" + s: spearman([s_lf[x] for x in both], [s_x[x] for x in both]),
                        "n_c_" + s: len(both), "n_" + s: len(w_x)})
        row["anchor_prev"] = cap_overlap(w_lf, prev[1]) if prev is not None else None
        row["anchor_in_scale"] = prev is not None and (prev[0], m) in AP
        prev = (m, w_lf)
        rows.append(row)
        print("  %s · (a) V %.3f FF %.3f VS %.3f · (b) V %d FF %d VS %d · (c) V %.3f"
              % (m, row["a_v"], row["a_ff"], row["a_vs"], row["b_v"], row["b_ff"], row["b_vs"],
                 row["c_v"] if row["c_v"] is not None else float("nan")), flush=True)
    res = {}
    for s in (BASIS,) + TWINS:
        res[s] = {"a": summary([r["a_" + s] for r in rows]), "b": summary([r["b_" + s] for r in rows]),
                  "c": summary([r["c_" + s] for r in rows if r["c_" + s] is not None])}
    anchor = summary([r["anchor_prev"] for r in rows if r["anchor_in_scale"]])
    verdict, chk = decide([r["a_" + BASIS] for r in rows], [r["b_" + BASIS] for r in rows])
    head = _git(["rev-parse", "HEAD"], repo).stdout.decode().strip()
    doc = {"note": "EGFF 1단계(사전등록 %s §4 · §5) — 수익 없음. 편입마다 P-V · P-FF · P-VS 대 공개 판(LF) (a) 시총가중 겹침 (b) 이름 겹침(30 중) "
                   "(c) Eg 점수 스피어만 · V0 자기 교체 척도(분기 간격 39쌍). 결정은 P-V 만(P-FF · P-VS 는 보고만)." % PREREG,
           "prereg": PREREG, "reg_commit": REG_COMMIT, "head": head, "f0_sha256": sha_file(os.path.join(repo, *F0_REL.split("/"))),
           "scores_sha256": {s: sha_file(os.path.join(repo, *rel.split("/"))) for s, rel in SCORE_REL.items()},
           "ref_sha256": f0["f0_iii_repro"]["ref_sha256"], "root_tree_sha256": f0["inputs"]["root"]["tree_sha256"],
           "v0": E.EG_BASE, "formations": FS, "anchor_pairs": sorted(AP),
           "thresholds": TH, "percentile": "numpy.percentile 선형 보간(기본값) · 41 편입",
           "rows": rows, "summary": res, "anchor_v0_self_overlap": anchor,
           "decision": {"basis": "P-V", "report_only": ["P-FF", "P-VS"], "checks": chk, "verdict": verdict,
                        "next": "여기서 끝 — 수익은 계산하지 않는다" if verdict == "재작성 둔감" else "2단계(§6) — 등록 커밋 뒤 한 번"},
           "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "sec": round(time.time() - t0, 1)}
    out = os.path.join(repo, *OUT_REL.split("/"))
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("→ %s · P-V (a) 중앙 %.3f · 10분위 %.3f · (b) 중앙 %.1f · 10분위 %.1f · 척도 %.3f → %s"
          % (OUT_REL, res["v"]["a"]["median"], res["v"]["a"]["p10"], res["v"]["b"]["median"], res["v"]["b"]["p10"],
             anchor["median"], verdict))
    return 0


# ── 자체 점검(합성) ───────────────────────────────────────────────────────
def selftest():
    ok = []

    def chk(name, cond):
        ok.append((name, bool(cond)))
        print("  %s %s" % ("통과" if cond else "실패", name))

    FS = formations()
    chk("편입 41회 · 2016-08 첫 달 · 2026-06 끝 · 그 사이는 분기말", len(FS) == 41 and FS[0] == "2016-08" and FS[-1] == "2026-06"
        and all(int(m[5:7]) % 3 == 0 for m in FS[1:]))
    AP = anchor_pairs(FS)
    chk("척도 쌍 = 분기 간격 39개 · 2016-08→09 제외", len(AP) == 39 and ("2016-08", "2016-09") not in AP
        and AP[0] == ("2016-09", "2016-12") and AP[-1] == ("2026-03", "2026-06"))
    wa = {"A": 0.2, "B": 0.5, "C": 0.3}
    wb = {"A": 0.1, "B": 0.5, "D": 0.4}
    chk("시총가중 겹침 = Σ min", abs(cap_overlap(wa, wb) - 0.6) < 1e-12 and abs(cap_overlap(wa, wa) - 1.0) < 1e-12)
    chk("이름 겹침", name_overlap(wa, wb) == 2 and name_overlap(wa, {}) == 0)
    chk("스피어만 · 단조 = 1 · 역순 = −1", abs(spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1) < 1e-12
        and abs(spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1) < 1e-12)
    chk("스피어만 · 동점은 평균 순위", abs(spearman([1, 2, 2, 3], [1, 2, 3, 4]) - np.corrcoef([0, 1.5, 1.5, 3], [0, 1, 2, 3])[0, 1]) < 1e-12)
    chk("스피어만 · 표본 셋 미만은 None", spearman([1, 2], [1, 2]) is None)
    rng = np.random.default_rng(20260925)
    a = list(np.clip(rng.normal(0.93, 0.03, 41), 0, 1))
    b = list(rng.integers(26, 31, 41))
    v, c = decide(a, b)
    chk("결정 · 넷 모두 넘으면 재작성 둔감", v == "재작성 둔감" and all(c.values()))
    v2, c2 = decide([0.90] * 41, [27] * 41)
    chk("결정 · 문턱 그 자체는 통과(≥)", v2 == "재작성 둔감")
    v3, c3 = decide([0.95] * 36 + [0.5] * 5, [30] * 41)
    chk("결정 · 10분위 하나만 어긋나도 2단계", v3 == "2단계" and not c3["a_p10"] and c3["a_median"])
    v4, c4 = decide([0.95] * 41, [26] * 41)
    chk("결정 · 이름 중앙값 26 이면 2단계", v4 == "2단계" and not c4["b_median"])
    chk("10분위 = numpy 선형 보간", abs(summary(list(range(41)))["p10"] - 4.0) < 1e-12)
    # 관문 — 임시 git 저장소 · 임시 뿌리
    tmp = tempfile.mkdtemp(prefix="s4sel_")
    troot = tempfile.mkdtemp(prefix="s4root_")
    try:
        def w(rel, obj, base=tmp):
            p = os.path.join(base, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with io.open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(obj) + "\n")
            return p
        _git(["init", "-q"], tmp)
        _git(["config", "user.email", "selftest@example.invalid"], tmp)
        _git(["config", "user.name", "selftest"], tmp)
        _git(["config", "core.autocrlf", "false"], tmp)
        rf = w("data/_eg_q5_scores_pitgics.json", {"frozen": 1}, troot)
        w("build/qg_lab.py", {"code": 1}, troot)
        w("data/stocks.json", {"px": [1, 2]}, troot)
        os.makedirs(os.path.join(troot, "build", "__pycache__"), exist_ok=True)
        tree0 = tree_digest(troot)[0]
        pv = w(SCORE_REL["v"], {"months": {}})
        pf = w(SCORE_REL["ff"], {"months": {"x": 1}})
        ps = w(SCORE_REL["vs"], {"months": {"y": 1}})
        f0 = {"pass": True, "f0_i_filing_match": {"pass": True}, "f0_ii_sh_split": {"pass": True},
              "stage1_plan": {"decision_basis": BASIS, "report_only": list(TWINS)},
              "inputs": {"root": {"tree_sha256": tree0}},
              "f0_iii_repro": {"pass": True, "ref_sha256": sha_file(rf),
                               "scores_sha256": {"v": sha_file(pv), "ff": sha_file(pf), "vs": sha_file(ps)}}}
        pin = sha_file(rf)
        chk("관문 · F0 파일 없음 → 막힘", not gate(tmp, troot, pin)[0])
        w(F0_REL, f0)
        chk("관문 · 커밋 전 → 막힘", not gate(tmp, troot, pin)[0])
        _git(["add", "-A"], tmp)
        _git(["commit", "-q", "-m", "t"], tmp)
        g_ok, g_why, _ = gate(tmp, troot, pin)
        chk("관문 · 커밋 · 통과 · 깨끗 · 뿌리 같음 → 열림", g_ok)
        chk("관문 · 배치 Q 해시가 아닌 ref → 막힘", not gate(tmp, troot, "f" * 64)[0])
        w(F0_REL, dict(f0, generated="x"))
        chk("관문 · 작업 사본이 HEAD 와 다름 → 막힘", not gate(tmp, troot, pin)[0])
        _git(["checkout", "--", F0_REL], tmp)
        bad = json.loads(json.dumps(f0))
        bad["pass"] = False
        w(F0_REL, bad)
        _git(["commit", "-qam", "fail"], tmp)
        chk("관문 · F0 불통과(커밋돼 있어도) → 막힘", not gate(tmp, troot, pin)[0])
        bad = json.loads(json.dumps(f0))
        bad["stage1_plan"]["decision_basis"] = "vs"
        w(F0_REL, bad)
        _git(["commit", "-qam", "plan-changed"], tmp)
        chk("관문 · F0 결정 기준이 스크립트와 다름 → 막힘", not gate(tmp, troot, pin)[0])
        w(F0_REL, f0)
        w(SCORE_REL["vs"], {"months": {"changed": 1}})
        _git(["commit", "-qam", "ok-but-scores-changed"], tmp)
        chk("관문 · 쌍둥이 점수 파일 해시가 F0 와 다름 → 막힘", not gate(tmp, troot, pin)[0])
        w(SCORE_REL["vs"], {"months": {"y": 1}})
        _git(["commit", "-qam", "restore"], tmp)
        chk("관문 · 되돌리면 다시 열림", gate(tmp, troot, pin)[0])
        w("build/__pycache__/x.pyc", {"cache": 1}, troot)
        chk("관문 · 뿌리의 __pycache__ 는 나무 해시에 들지 않는다", gate(tmp, troot, pin)[0])
        w("data/stocks.json", {"px": [1, 3]}, troot)
        chk("관문 · 뿌리 World 입력이 바뀌면 막힘(얼린 Eg 파일은 같아도)", not gate(tmp, troot, pin)[0])
        w("data/stocks.json", {"px": [1, 2]}, troot)
        w("data/fx_pit/NEW.json", {"cik": 1}, troot)
        chk("관문 · 뿌리에 파일이 늘면 막힘", not gate(tmp, troot, pin)[0])
        os.remove(os.path.join(troot, "data", "fx_pit", "NEW.json"))
        chk("관문 · 뿌리를 되돌리면 다시 열림", gate(tmp, troot, pin)[0])
        chk("관문 ⓪ · 랩 저장소가 아닌 저장소 → 막힘", bool(repo_gate(tmp)))
        chk("관문 ⓪ · 등록 커밋이 조상이 아닌 저장소 → 막힘", bool(repo_gate(tmp, lab=tmp)))
        w(OUT_REL, {"x": 1})
        chk("관문 · 결과가 이미 있으면 막힘(한 번 굽기)", not gate(tmp, troot, pin)[0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(troot, ignore_errors=True)
    bad = [x for x, c in ok if not c]
    print("selftest: %d/%d 통과" % (len(ok) - len(bad), len(ok)))
    return 1 if bad else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--repo" in argv:
        raise SystemExit("🚨 --repo 는 없다 — 1단계는 이 스크립트의 랩 저장소에서만 돈다(한 번 굽기 관문 ⑤ 우회 방지)")
    if "--root" not in argv:
        print(__doc__)
        return 2
    root = os.path.abspath(argv[argv.index("--root") + 1])
    return run(root)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
